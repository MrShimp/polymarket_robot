#!/usr/bin/env python3
import math
import sys
import os
import json
import time
import asyncio
import requests
import csv
import pytz
import websockets
import numpy as np
import ssl
import aiohttp
from datetime import datetime, timedelta
from threading import Lock
from decimal import Decimal
from collections import deque
from typing import Dict, Optional

# 导入必要的交易库
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from trading.polymarket_clob_client import PolymarketCLOBClient
from trading.buy_strategy import BuyStrategy
from trading.sell_strategy import SellStrategy
from btc_websocket_price_monitor_v2_fixed import BTCWebSocketMonitorV2Fixed
from websocket_price_provider import WebSocketPriceProvider


class BTCHighOddsSniperStrategy:
    """
    BTC 高赔率狙击者策略 V3
    核心逻辑：价格敏感度 + 概率滞后套利 + 动态波动率调整

    策略特点：
    1. 核心敏感度阈值：40-60 USDT 偏离触发
    2. 时间敏感度：<500ms WebSocket实时响应
    3. 动态敏感度：基于10分钟波动率自适应调整
    4. 概率滞后判定：理论概率与市场概率差>12%才下单
    """

    def __init__(
        self,
        market_id: str,
        baseline_price: float = 95000.0,
        core_sensitivity: float = 50.0,
        mu_factor: float = 1.8,
    ):
        self.market_id = market_id
        self.clob_wrapper = PolymarketCLOBClient()
        self.clob_client = self.clob_wrapper.get_client()

        # 初始化执行器
        self.buy_strategy = BuyStrategy(self.clob_client, self.log)
        self.sell_strategy = SellStrategy(self.clob_client, self.log)
        self.gamma_api_base = "https://gamma-api.polymarket.com"

        # --- 高赔率狙击者核心参数 ---
        self.baseline_price = baseline_price
        self.core_sensitivity = core_sensitivity  # 核心敏感度阈值 (40-60 USDT)
        self.mu_factor = mu_factor  # 动态敏感度系数 (1.5-2.0)
        self.prob_lag_threshold = 0.12  # 概率滞后阈值 (12%)
        self.max_response_time = 0.5  # 最大响应时间 (500ms)
        self.no_entry_window = 180  # 最后3分钟不入场限制 (180秒)

        # --- 新增优化参数 ---
        self.atr_period = 600  # 10分钟ATR计算周期
        self.liquidity_cache = {}  # 流动性缓存
        self.max_slippage_ratio = 0.4  # 最大滑点比例 (40%)
        self.buyer_maker_weight = 0.7  # 主动买盘权重阈值

        # --- V3 新增优化参数 ---
        self.ema_alpha = 2 / (300 + 1)  # 5分钟EMA平滑系数 (300个数据点)
        self.volatility_multiplier = 2.5  # 波动率阈值倍数
        self.prob_boundary_low = 0.2  # 概率下边界
        self.prob_boundary_high = 0.8  # 概率上边界
        self.extreme_prob_protection = True  # 极端概率保护开关

        # --- 价格数据缓存 (用于计算波动率和EMA) ---
        self.price_history = deque(maxlen=600)  # 10分钟 * 60秒 = 600个数据点
        self.ema_5min_history = deque(maxlen=300)  # 5分钟EMA历史 = 300个数据点
        self.trade_data_history = deque(maxlen=100)  # 存储交易数据用于买卖盘分析
        self.last_price_update = 0
        self.current_price = baseline_price
        self.ema_5min = baseline_price  # 5分钟EMA初始值

        # --- WebSocket 价格提供器 ---
        self.price_provider = WebSocketPriceProvider("btcusdt")
        self.price_provider.add_price_callback(self.on_price_update)
        self.price_provider.add_trade_callback(self.on_trade_update)

        # --- 状态管理 ---
        self.position = {
            "side": None,
            "amount": 0,
            "token_id": None,
            "entry_price": 0,
            "entry_prob": 0,
            "entry_time": 0,
        }
        self.start_time = time.time()

        # --- 新的日志系统 ---
        self.log_dir = "data/btc_strategy_v2_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(
            self.log_dir,
            f"sniper_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )

        # 日志计时器
        self.last_market_log_time = 0  # 市场状态日志 (10秒间隔)
        self.last_position_log_time = 0  # 持仓状态日志 (3秒间隔)

    def log(self, message, level="INFO"):
        """统一日志记录方法"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        # 写入日志文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"写入日志失败: {e}")

    def log_market_status(
        self, current_price, market_prob, price_deviation, should_enter, reason=""
    ):
        """记录市场状态日志 (每5秒)"""
        current_time = time.time()
        if current_time - self.last_market_log_time >= 5:  # 改为5秒间隔
            volatility = self.calculate_10min_volatility()
            dynamic_threshold = self.get_dynamic_threshold()

            status_msg = (
                f"📊 市场状态 | "
                f"价格: ${current_price:,.2f} | "
                f"概率: {market_prob:.3f} | "
                f"偏移: {price_deviation:+.1f} USDT | "
                f"波动率: {volatility:.1f} | "
                f"阈值: {dynamic_threshold:.1f} | "
                f"入场: {'✅' if should_enter else '❌'}"
            )

            if reason:
                status_msg += f" | 原因: {reason}"

            self.log(status_msg)
            self.last_market_log_time = current_time

    def log_position_status(self, current_prob, current_price):
        """记录持仓状态日志 (每3秒)"""
        if not self.position["side"]:
            return

        current_time = time.time()
        if current_time - self.last_position_log_time >= 3:  # 3秒间隔
            # 计算当前盈利额 (简化计算)
            entry_prob = self.position["entry_prob"]
            position_amount = self.position["amount"]

            # 简化的盈利计算：基于概率变化
            if self.position["side"] == "BUY_YES":
                prob_change = current_prob - entry_prob
                estimated_profit = prob_change * position_amount
            elif self.position["side"] == "BUY_NO":
                prob_change = (1 - current_prob) - (1 - entry_prob)
                estimated_profit = prob_change * position_amount
            else:
                estimated_profit = 0

            # 持仓时间
            hold_time = int(current_time - self.position["entry_time"])

            profit_msg = (
                f"💰 持仓状态 | "
                f"仓位: {self.position['side']} | "
                f"当前概率: {current_prob:.3f} | "
                f"入场概率: {entry_prob:.3f} | "
                f"预估盈利: ${estimated_profit:+.2f} | "
                f"持仓时间: {hold_time}s"
            )

            self.log(profit_msg)
            self.last_position_log_time = current_time

    def calculate_5min_ema(self, new_price):
        """
        计算5分钟EMA (指数移动平均线)
        优化逻辑1: 替代固定基准价格，捕捉短线异常脉冲
        """
        if len(self.ema_5min_history) == 0:
            # 初始化EMA为当前价格
            self.ema_5min = new_price
        else:
            # EMA公式: EMA_new = α × Price_new + (1-α) × EMA_old
            self.ema_5min = (self.ema_alpha * new_price) + (
                (1 - self.ema_alpha) * self.ema_5min
            )

        # 记录EMA历史
        self.ema_5min_history.append(self.ema_5min)

        return self.ema_5min

    def calculate_price_offset_from_ema(self, current_price):
        """
        计算价格相对于5分钟EMA的偏移量
        Offset = Price_current - EMA_5min
        """
        if not hasattr(self, "ema_5min") or self.ema_5min == 0:
            return 0

        return current_price - self.ema_5min

    def calculate_10min_volatility(self):
        """计算10分钟价格波动率"""
        if len(self.price_history) < 10:
            return 20.0  # 默认波动率

        prices = list(self.price_history)
        price_changes = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
        return np.mean(price_changes) if price_changes else 20.0

    def calculate_atr(self, period=None):
        """计算平均真实波动率 (ATR)"""
        if period is None:
            period = min(self.atr_period, len(self.price_history))

        if len(self.price_history) < 14:
            return self.calculate_10min_volatility()  # 回退到简单波动率

        prices = list(self.price_history)[-period:]

        # 计算真实波动率
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = abs(prices[i] - prices[i - 1])  # 简化：当前价格与前一价格差
            true_ranges.append(high_low)

        # 计算ATR (简单移动平均)
        if true_ranges:
            return np.mean(true_ranges)
        return 20.0

    def get_adaptive_threshold_v3(self):
        """
        V3优化: 波动率深度绑定的自适应阈值
        优化逻辑2: Threshold = Core_Sensitivity + (Volatility × 2.5)
        """
        volatility = self.calculate_10min_volatility()

        # 新公式: 基础敏感度 + 波动率加成
        volatility_adjustment = volatility * self.volatility_multiplier
        adaptive_threshold = self.core_sensitivity + volatility_adjustment

        # 应用mu_factor
        final_threshold = self.mu_factor * adaptive_threshold

        # 设置合理的边界 (最小30, 最大200)
        final_threshold = max(30.0, min(200.0, final_threshold))

        return final_threshold

    def check_probability_boundaries(self, market_prob):
        """
        V3优化: 概率边界保护
        优化逻辑3: 当概率进入 <0.2 或 >0.8 区域时，强制停止操作
        """
        if not self.extreme_prob_protection:
            return False, "概率边界保护已关闭"

        if market_prob < self.prob_boundary_low:
            return (
                True,
                f"概率过低 ({market_prob:.3f} < {self.prob_boundary_low}), 进入垃圾时间",
            )

        if market_prob > self.prob_boundary_high:
            return (
                True,
                f"概率过高 ({market_prob:.3f} > {self.prob_boundary_high}), 强趋势无法阻挡",
            )

        return (
            False,
            f"概率在安全区间 ({self.prob_boundary_low} < {market_prob:.3f} < {self.prob_boundary_high})",
        )

    def get_adaptive_prob_threshold(self, liquidity_score=None):
        """基于流动性的自适应概率阈值"""
        base_threshold = self.prob_lag_threshold

        if liquidity_score is None:
            return base_threshold

        # 流动性评分: 0-1, 1表示最高流动性
        if liquidity_score < 0.3:  # 低流动性
            # 要求更大的概率差 (15%-18%)
            return min(0.18, base_threshold * 1.5)
        elif liquidity_score > 0.7:  # 高流动性
            # 可以缩减要求 (8%-10%)
            return max(0.08, base_threshold * 0.7)
        else:  # 中等流动性
            return base_threshold

    def analyze_buyer_maker_ratio(self, trade_data):
        """
        分析主动买盘比例 - 仅使用真实交易数据

        Binance字段含义：
        - is_buyer_maker = true: 买方是挂单方(maker)，实际是卖单被执行
        - is_buyer_maker = false: 买方是吃单方(taker)，实际是买单被执行

        所以我们要统计的是 is_buyer_maker = false 的比例（主动买盘）
        """
        if not trade_data or len(trade_data) < 3:  # 降低最小要求到3笔
            # 添加调试信息
            data_count = len(trade_data) if trade_data else 0
            if (
                hasattr(self, "_last_buyer_ratio_debug")
                and time.time() - self._last_buyer_ratio_debug > 60
            ):
                self.log(
                    f"🔍 买卖盘数据不足: 当前{data_count}笔交易 (需要至少3笔)，返回中性比例",
                    "DEBUG",
                )
                self._last_buyer_ratio_debug = time.time()
            return 0.5  # 默认中性

        # 统计主动买盘的比例 (is_buyer_maker = false 表示买方是taker，即主动买盘)
        active_buy_count = 0
        total_trades = len(trade_data)

        # 添加详细的数据分析
        for trade in trade_data:
            is_buyer_maker = trade.get("is_buyer_maker", False)
            # 主动买盘：买方是taker (is_buyer_maker = false)
            if not is_buyer_maker:
                active_buy_count += 1

        buyer_ratio = active_buy_count / total_trades if total_trades > 0 else 0.5

        # 定期记录买卖盘分析结果 (每60秒，降低日志频率)
        current_time = time.time()
        if (
            not hasattr(self, "_last_buyer_ratio_log")
            or current_time - self._last_buyer_ratio_log > 60
        ):
            self.log(
                f"📊 买卖盘分析: 主动买盘{active_buy_count}/{total_trades} = {buyer_ratio:.3f} | 最近交易: {total_trades}笔",
                "DEBUG",
            )
            self._last_buyer_ratio_log = current_time

            # 显示最近几笔交易的详细信息（仅在有足够数据时）
            if len(trade_data) >= 3:
                recent_trades_info = []
                for i, trade in enumerate(trade_data[-5:]):  # 显示最近5笔
                    is_buyer_maker = trade.get("is_buyer_maker", False)
                    # 修正逻辑：is_buyer_maker=false表示主动买盘
                    trade_type = "主动买" if not is_buyer_maker else "主动卖"
                    price = trade.get("price", 0)
                    qty = trade.get("quantity", 0)
                    recent_trades_info.append(f"{trade_type}@{price:.0f}({qty:.3f})")

                self.log(f"📊 最近交易详情: {' | '.join(recent_trades_info)}", "DEBUG")

        return buyer_ratio

    def classify_breakout_type(self, price_deviation, buyer_maker_ratio):
        """判断突破类型：真突破 vs 假突破"""
        abs_deviation = abs(price_deviation)

        # 真突破判定条件
        if (
            buyer_maker_ratio > self.buyer_maker_weight
            and abs_deviation > self.get_adaptive_threshold()
        ):
            return "TRUE_BREAKOUT", 1.0  # 满仓信号
        elif (
            buyer_maker_ratio < (1 - self.buyer_maker_weight)
            and abs_deviation > self.get_adaptive_threshold()
        ):
            return "TRUE_BREAKDOWN", 1.0  # 满仓信号
        elif abs_deviation > self.get_adaptive_threshold() * 0.5:
            return "WEAK_SIGNAL", 0.5  # 减仓信号
        else:
            return "FALSE_SIGNAL", 0.0  # 观望

    async def simulate_order_impact(self, token_id, amount):
        """模拟订单对价格的影响 (滑点计算)"""
        try:
            # 获取订单簿数据
            order_book = await self.get_order_book(token_id)
            if not order_book:
                return None, "无法获取订单簿"

            # 模拟市价买入的滑点
            remaining_amount = amount
            total_cost = 0
            weighted_price = 0

            asks = order_book.get("asks", [])
            for price_str, size_str in asks:
                price = float(price_str)
                size = float(size_str)

                if remaining_amount <= 0:
                    break

                fill_amount = min(remaining_amount, size)
                total_cost += fill_amount * price
                remaining_amount -= fill_amount

            if remaining_amount > 0:
                return None, f"流动性不足，还需{remaining_amount}"

            avg_fill_price = total_cost / amount if amount > 0 else 0

            # 计算滑点
            best_ask = float(asks[0][0]) if asks else 0
            slippage = (avg_fill_price - best_ask) / best_ask if best_ask > 0 else 0

            return {
                "avg_fill_price": avg_fill_price,
                "slippage": slippage,
                "total_cost": total_cost,
            }, None

        except Exception as e:
            return None, f"滑点计算失败: {e}"

    async def get_order_book(self, token_id):
        """获取订单簿数据"""
        try:
            # 这里需要调用实际的订单簿API
            # 暂时返回模拟数据
            return {
                "asks": [["0.45", "100"], ["0.46", "200"], ["0.47", "300"]],
                "bids": [["0.44", "100"], ["0.43", "200"], ["0.42", "300"]],
            }
        except Exception as e:
            self.log(f"获取订单簿失败: {e}", "ERROR")
            return None

    def calculate_liquidity_score(self, order_book, volume_24hr=0):
        """计算流动性评分 (0-1)"""
        if not order_book:
            return 0.3  # 默认低流动性

        try:
            asks = order_book.get("asks", [])
            bids = order_book.get("bids", [])

            # 计算买卖盘深度
            ask_depth = sum(float(size) for _, size in asks[:5])  # 前5档
            bid_depth = sum(float(size) for _, size in bids[:5])
            total_depth = ask_depth + bid_depth

            # 计算价差
            best_ask = float(asks[0][0]) if asks else 1.0
            best_bid = float(bids[0][0]) if bids else 0.0
            spread = (best_ask - best_bid) / best_ask if best_ask > 0 else 1.0

            # 综合评分
            depth_score = min(1.0, total_depth / 1000)  # 假设1000为满分深度
            spread_score = max(0.0, 1.0 - spread * 100)  # 价差越小分数越高
            volume_score = min(1.0, volume_24hr / 10000)  # 假设10000为满分成交量

            # 加权平均
            liquidity_score = (
                depth_score * 0.4 + spread_score * 0.4 + volume_score * 0.2
            )

            return max(0.1, min(1.0, liquidity_score))

        except Exception as e:
            self.log(f"流动性评分计算失败: {e}", "ERROR")
            return 0.3

    def get_dynamic_threshold(self):
        """动态敏感度阈值计算 - V3版本，使用新的自适应阈值"""
        return self.get_adaptive_threshold_v3()

    def get_adaptive_threshold(self):
        """保持向后兼容的方法，调用V3版本"""
        return self.get_adaptive_threshold_v3()

    def check_market_end_time(self, market_data):
        """检查市场结束时间，判断是否在禁止入场窗口内"""
        try:
            # 从市场数据中获取结束时间
            # 注意：这里需要根据实际的市场数据结构调整
            if not market_data:
                return False, "无市场数据"

            # 如果是模拟数据，跳过时间检查
            if market_data.get("is_simulated", False):
                return False, "模拟数据模式"

            # 尝试从不同字段获取结束时间
            end_time_str = None
            for field in ["endDate", "end_date", "closesAt", "closes_at", "endTime"]:
                if field in market_data:
                    end_time_str = market_data[field]
                    break

            if not end_time_str:
                # 如果没有结束时间信息，默认允许交易
                self.log("⚠️ 无法获取市场结束时间，默认允许入场", "WARN")
                return False, "无结束时间信息"

            # 解析结束时间
            try:
                # 尝试不同的时间格式
                if isinstance(end_time_str, (int, float)):
                    # Unix时间戳
                    end_time = datetime.fromtimestamp(end_time_str)
                else:
                    # ISO格式或其他字符串格式
                    from dateutil import parser

                    end_time = parser.parse(end_time_str)

            except Exception as e:
                self.log(f"⚠️ 解析结束时间失败: {e}", "WARN")
                return False, "时间解析失败"

            # 计算距离结束的时间
            current_time = (
                datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            )
            time_to_end = (end_time - current_time).total_seconds()

            # 检查是否在禁止入场窗口内
            if time_to_end <= self.no_entry_window:
                minutes_left = time_to_end / 60
                return True, f"距离结束仅剩 {minutes_left:.1f} 分钟，禁止入场"

            return False, f"距离结束还有 {time_to_end/60:.1f} 分钟，允许入场"

        except Exception as e:
            self.log(f"检查市场结束时间异常: {e}", "ERROR")
            return False, "时间检查异常"

    def calculate_theoretical_probability(self, current_price, target_price=None):
        """
        基于价格偏离计算理论概率
        简化模型：假设15分钟内价格回归均值的概率
        """
        if target_price is None:
            target_price = self.baseline_price

        price_deviation = current_price - target_price

        # 使用正态分布模型估算概率
        # 假设15分钟内价格标准差约为当前波动率的1.5倍
        volatility = self.calculate_10min_volatility()
        std_dev = volatility * 1.5

        if std_dev == 0:
            return 0.5

        # 计算价格高于目标价格的概率
        z_score = price_deviation / std_dev
        # 使用简化的正态分布近似
        theoretical_prob = 0.5 + (z_score / (2 * math.pi)) * math.exp(-(z_score**2) / 2)

        return max(0.01, min(0.99, theoretical_prob))

    async def on_price_update(self, price: float, timestamp: float):
        """价格更新回调 - 由WebSocketPriceProvider调用，增加EMA计算"""
        try:
            # 更新价格历史
            self.price_history.append(price)

            # V3优化: 计算5分钟EMA
            self.calculate_5min_ema(price)

            # 记录价格变化（调试用）
            old_price = self.current_price
            self.current_price = price
            self.last_price_update = timestamp

            # 每当价格有显著变化时记录
            price_change = abs(price - old_price)
            if price_change > 1.0:  # 价格变化超过1 USDT时记录
                ema_offset = self.calculate_price_offset_from_ema(price)
                self.log(
                    f"💹 价格更新: ${price:,.2f} (变化: {price - old_price:+.2f}) | EMA偏移: {ema_offset:+.2f}",
                    "DEBUG",
                )

            # 触发策略分析
            response_time = (time.time() - timestamp) * 1000  # 计算延迟
            await self.analyze_sniper_opportunity(response_time)

        except Exception as e:
            self.log(f"价格更新处理错误: {e}", "ERROR")

    async def on_trade_update(self, trade_data: dict):
        """交易数据更新回调 - 由WebSocketPriceProvider调用，增强版"""
        try:
            # 更新交易数据历史 (用于买卖盘分析)
            trade_info = {
                "price": trade_data["price"],
                "quantity": trade_data["quantity"],
                "is_buyer_maker": trade_data.get("is_buyer_maker", False),
                "timestamp": trade_data["timestamp"],
            }
            self.trade_data_history.append(trade_info)

            # 定期记录交易数据接收情况 (每60秒)
            current_time = time.time()
            if (
                not hasattr(self, "_last_trade_log")
                or current_time - self._last_trade_log > 60
            ):
                total_trades = len(self.trade_data_history)
                # 修正逻辑：is_buyer_maker=false表示主动买盘
                active_buy_count = sum(
                    1
                    for t in self.trade_data_history
                    if not t.get("is_buyer_maker", True)
                )
                self.log(
                    (
                        f"📈 交易数据统计: 总计{total_trades}笔 | 主动买盘{active_buy_count}笔 | 比例{active_buy_count/total_trades:.3f}"
                        if total_trades > 0
                        else "📈 交易数据统计: 暂无数据"
                    ),
                    "DEBUG",
                )
                self._last_trade_log = current_time

        except Exception as e:
            self.log(f"交易数据更新处理错误: {e}", "ERROR")

    async def update_market_state(self, current_price: float):
        """
        更新市场状态 - 由智能交易器调用，增加EMA更新
        这个方法确保价格和概率数据实时更新
        """
        try:
            # 更新当前价格
            old_price = self.current_price
            self.current_price = current_price
            self.last_price_update = time.time()

            # 添加到价格历史
            self.price_history.append(current_price)

            # V3优化: 更新5分钟EMA
            self.calculate_5min_ema(current_price)

            # 强制刷新市场数据缓存（每5秒刷新一次）
            current_time = time.time()
            if (
                not hasattr(self, "_last_market_refresh")
                or current_time - self._last_market_refresh > 5
            ):

                # 清除缓存，强制重新获取
                if hasattr(self, "_cached_market_data"):
                    delattr(self, "_cached_market_data")
                if hasattr(self, "_cache_timestamp"):
                    delattr(self, "_cache_timestamp")

                self._last_market_refresh = current_time
                self.log(f"🔄 强制刷新市场数据缓存", "DEBUG")

            # 触发策略分析
            await self.analyze_sniper_opportunity(0)  # 响应时间设为0，因为是主动调用

        except Exception as e:
            self.log(f"更新市场状态错误: {e}", "ERROR")

    async def analyze_sniper_opportunity(self, response_time_ms):
        """
        高赔率狙击机会分析 - V3优化版
        新增：EMA偏移计算 + 波动率深度绑定阈值 + 概率边界保护
        """
        # 添加详细的调试日志
        # self.log(f"🔍 开始分析狙击机会 - 当前持仓: {self.position['side']}", "DEBUG")

        # 1. V3优化: 计算价格相对于5分钟EMA的偏移量 (替代固定基准价格)
        ema_offset = self.calculate_price_offset_from_ema(self.current_price)

        # 2. V3优化: 获取波动率深度绑定的自适应阈值
        adaptive_threshold_v3 = self.get_adaptive_threshold_v3()

        # 3. 获取市场概率数据
        market_data = await self.fetch_market_sentiment()
        if not market_data:
            self.log("⚠️ 无法获取市场数据，跳过本次分析", "WARN")
            return

        market_prob = market_data["yes_prob"]
        is_simulated = market_data.get("is_simulated", False)

        if is_simulated:
            self.log("⚠️ 使用模拟市场数据，降低交易风险", "WARN")

        # 3.1 V3优化: 概率边界保护检查
        is_extreme_prob, prob_reason = self.check_probability_boundaries(market_prob)
        if is_extreme_prob:
            self.log(f"🚫 {prob_reason}，强制停止所有操作", "WARN")
            # 记录市场状态但不执行交易
            self.log_enhanced_market_status_v3(
                self.current_price,
                market_prob,
                ema_offset,  # 使用EMA偏移替代price_deviation
                False,  # should_enter = False
                f"概率边界保护: {prob_reason}",
                adaptive_threshold_v3,
                0.5,  # buyer_maker_ratio
                "PROB_BOUNDARY_PROTECTION",  # breakout_type
                self.get_adaptive_prob_threshold(),
            )
            return

        # 3.2 检查市场结束时间限制
        is_near_end, time_reason = self.check_market_end_time(market_data)
        if is_near_end:
            self.log(f"🚫 {time_reason}，跳过交易", "WARN")
            # 记录市场状态但不执行交易
            self.log_enhanced_market_status_v3(
                self.current_price,
                market_prob,
                ema_offset,
                False,  # should_enter = False
                f"时间限制: {time_reason}",
                adaptive_threshold_v3,
                0.5,  # buyer_maker_ratio
                "TIME_RESTRICTED",  # breakout_type
                self.get_adaptive_prob_threshold(),
            )
            return

        # 4. 分析买卖盘强度 (基于最近交易数据)
        recent_trades = list(self.trade_data_history)[-20:]  # 最近20笔交易
        buyer_maker_ratio = self.analyze_buyer_maker_ratio(recent_trades)

        # 5. 判断突破类型 (使用EMA偏移)
        breakout_type, position_size_multiplier = self.classify_breakout_type(
            ema_offset, buyer_maker_ratio
        )

        # 6. V3优化: 价格敏感度过滤 (使用EMA偏移 + 波动率深度绑定阈值)
        should_enter = abs(ema_offset) >= adaptive_threshold_v3

        # 7. 计算概率相关参数（无论价格条件是否满足都需要计算，用于日志）
        theoretical_prob = self.calculate_theoretical_probability(self.current_price)
        liquidity_score = self.liquidity_cache.get(self.market_id, 0.5)
        adaptive_prob_threshold = self.get_adaptive_prob_threshold(liquidity_score)
        prob_diff = abs(theoretical_prob - market_prob)

        # 8. 记录市场状态日志 (每10秒)
        reason = ""
        if not should_enter:
            reason = (
                f"EMA偏移不够显著 ({abs(ema_offset):.1f} < {adaptive_threshold_v3:.1f})"
            )
        else:
            # 概率滞后判定 - 使用自适应阈值
            if prob_diff < adaptive_prob_threshold:
                should_enter = False
                reason = (
                    f"概率差异太小 ({prob_diff:.3f} < {adaptive_prob_threshold:.3f})"
                )
            else:
                # 生成交易信号 (使用EMA偏移)
                signal, signal_reason = self._generate_sniper_signal_v3(
                    ema_offset,
                    market_prob,
                    theoretical_prob,
                    adaptive_threshold_v3,
                    breakout_type,
                    buyer_maker_ratio,
                )

                if signal and breakout_type != "FALSE_SIGNAL":
                    # 保持should_enter = True，因为已经通过了价格和概率检查
                    reason = f"触发信号: {signal} - {signal_reason} - 突破类型: {breakout_type}"

                    # 执行交易前的滑点校验
                    current_position_side = self.position["side"]
                    self.log(f"🔍 检查持仓状态: {current_position_side}", "DEBUG")

                    if not current_position_side:
                        self.log(f"✅ 无持仓，准备执行交易: {signal}", "INFO")
                        if is_simulated:
                            self.log("⚠️ 模拟数据模式，跳过实际交易", "WARN")
                        else:
                            await self.execute_sniper_trade_with_validation(
                                signal,
                                market_data,
                                signal_reason,
                                position_size_multiplier,
                                getattr(self, "trade_amount", 100.0),  # 传入交易金额
                            )
                    else:
                        self.log(
                            f"⚠️ 已有持仓 {current_position_side}，跳过新交易", "WARN"
                        )
                        should_enter = False
                        reason = f"已有持仓 {current_position_side}，跳过新交易"
                else:
                    should_enter = False
                    reason = f"无明确信号或假突破 - 突破类型: {breakout_type}"

        # 记录V3增强的市场状态日志
        self.log_enhanced_market_status_v3(
            self.current_price,
            market_prob,
            ema_offset,  # 使用EMA偏移
            should_enter,
            reason,
            adaptive_threshold_v3,
            buyer_maker_ratio,
            breakout_type,
            adaptive_prob_threshold,  # 传递正确的概率阈值
        )

        # 记录持仓状态日志 (如果有持仓)
        self.log_position_status(market_prob, self.current_price)

    def _generate_detailed_monitor_reason(
        self,
        price_deviation,
        dynamic_threshold,
        prob_diff,
        adaptive_prob_threshold,
        theoretical_prob,
        market_prob,
        buyer_maker_ratio,
        breakout_type,
        should_enter,
    ):
        """生成详细的监控原因分析"""
        reasons = []

        # 1. 价格偏离分析
        abs_deviation = abs(price_deviation)
        if abs_deviation < dynamic_threshold:
            reasons.append(
                f"价格偏离不足 ({abs_deviation:.1f} < {dynamic_threshold:.1f})"
            )
        else:
            direction = "上涨" if price_deviation > 0 else "下跌"
            reasons.append(
                f"价格{direction}达标 ({abs_deviation:.1f} >= {dynamic_threshold:.1f})"
            )

        # 2. 概率滞后分析
        if prob_diff < adaptive_prob_threshold:
            reasons.append(
                f"概率差异不足 ({prob_diff:.3f} < {adaptive_prob_threshold:.3f})"
            )
        else:
            prob_direction = (
                "理论>市场" if theoretical_prob > market_prob else "理论<市场"
            )
            reasons.append(f"概率滞后明显 ({prob_direction}, 差异{prob_diff:.3f})")

        # 3. 买卖盘强度分析
        if buyer_maker_ratio > 0.7:
            reasons.append(f"买盘主导 ({buyer_maker_ratio:.2f})")
        elif buyer_maker_ratio < 0.3:
            reasons.append(f"卖盘主导 ({buyer_maker_ratio:.2f})")
        else:
            reasons.append(f"买卖平衡 ({buyer_maker_ratio:.2f})")

        # 4. 突破类型分析
        breakout_desc = {
            "TRUE_BREAKOUT": "真突破",
            "TRUE_BREAKDOWN": "真下破",
            "WEAK_SIGNAL": "弱信号",
            "FALSE_SIGNAL": "假信号",
            "TIME_RESTRICTED": "时间限制",
        }
        reasons.append(f"突破类型: {breakout_desc.get(breakout_type, breakout_type)}")

        # 5. 综合判断
        if should_enter:
            reasons.append("✅ 满足入场条件")
        else:
            reasons.append("❌ 不满足入场条件")

        # 6. 添加当前持仓状态
        if self.position["side"]:
            hold_time = int(time.time() - self.position["entry_time"])
            reasons.append(f"持仓中: {self.position['side']} ({hold_time}s)")
        else:
            reasons.append("空仓观望")

        return " | ".join(reasons)

    def _generate_sniper_signal_v3(
        self,
        ema_offset,  # 使用EMA偏移替代price_deviation
        market_prob,
        theoretical_prob,
        threshold,
        breakout_type,
        buyer_maker_ratio,
    ):
        """
        V3优化: 生成狙击信号 - 基于EMA偏移的增强版
        """

        # 策略1: EMA偏移大幅上涨，但市场概率滞后 (买Yes)
        if (
            ema_offset > threshold
            and theoretical_prob > market_prob + self.get_adaptive_prob_threshold()
        ):
            # 根据突破类型调整信号强度
            if breakout_type == "TRUE_BREAKOUT":
                return (
                    "BUY_YES",
                    f"强势EMA突破 +{ema_offset:.1f}, 买盘主导 {buyer_maker_ratio:.2f}, Prob lag {theoretical_prob:.3f}>{market_prob:.3f}",
                )
            else:
                return (
                    "BUY_YES",
                    f"EMA偏移 +{ema_offset:.1f}, Prob lag {theoretical_prob:.3f}>{market_prob:.3f}",
                )

        # 策略2: EMA偏移大幅下跌，但市场概率滞后 (买Yes，因为市场反应过度)
        if (
            ema_offset < -threshold
            and theoretical_prob > market_prob + self.get_adaptive_prob_threshold()
        ):
            if breakout_type == "TRUE_BREAKDOWN":
                return (
                    "BUY_YES",
                    f"强势EMA下破但市场过度反应 {ema_offset:.1f}, 理论概率 {theoretical_prob:.3f} > 市场概率 {market_prob:.3f}",
                )
            else:
                return (
                    "BUY_YES",
                    f"EMA偏移 {ema_offset:.1f}, 市场过度反应 {theoretical_prob:.3f}>{market_prob:.3f}",
                )

        # 策略2B: EMA偏移大幅下跌，理论概率也确实更低 (买No)
        if (
            ema_offset < -threshold
            and theoretical_prob < market_prob - self.get_adaptive_prob_threshold()
        ):
            if breakout_type == "TRUE_BREAKDOWN":
                return (
                    "BUY_NO",
                    f"强势EMA下破 {ema_offset:.1f}, 理论概率 {theoretical_prob:.3f} < 市场概率 {market_prob:.3f}",
                )
            else:
                return (
                    "BUY_NO",
                    f"EMA偏移 {ema_offset:.1f}, 理论概率滞后 {theoretical_prob:.3f}<{market_prob:.3f}",
                )

        # 策略3: EMA偏移与概率严重背离 (反向操作) - 仅在真突破时执行
        if (
            ema_offset > threshold
            and market_prob > 0.70
            and breakout_type in ["TRUE_BREAKOUT", "WEAK_SIGNAL"]
        ):
            return "BUY_NO", f"EMA上涨但概率过高: {market_prob:.3f}, 反向操作"

        if (
            ema_offset < -threshold
            and market_prob < 0.30
            and breakout_type in ["TRUE_BREAKDOWN", "WEAK_SIGNAL"]
        ):
            return (
                "BUY_YES",
                f"EMA下跌但概率过低: {market_prob:.3f}, 反向操作",
            )

        return None, "No clear EMA-based signal"

    async def execute_sniper_trade_with_validation(
        self, signal, market_data, reason, position_size_multiplier, amount=None
    ):
        """执行狙击交易 - 增加滑点校验和动态仓位管理"""
        if signal == "BUY_YES":
            token_id = market_data["token_id_yes"]
        elif signal == "BUY_NO":
            token_id = market_data["token_id_no"]
        else:
            return

        # 计算动态交易金额
        if amount is None:
            # 如果没有传入金额，使用实例属性作为后备
            base_amount = getattr(self, "trade_amount", 100.0)
        else:
            # 使用传入的金额，但确保最小值为1
            base_amount = max(1.0, amount)
        adjusted_amount = base_amount * position_size_multiplier

        self.log(f"🎯 SNIPER TRADE: {signal} | {reason}")
        self.log(
            f"💰 调整后金额: ${adjusted_amount:.2f} (倍数: {position_size_multiplier})"
        )

        # 步骤1: 滑点预校验
        impact_result, error = await self.simulate_order_impact(
            token_id, adjusted_amount
        )

        if error:
            self.log(f"⚠️ 滑点校验失败: {error}", "WARN")
            return

        if impact_result:
            slippage = impact_result["slippage"]
            expected_profit_ratio = 0.05  # 假设期望利润率5%

            # 如果滑点超过期望利润的40%，则拒绝交易或分批
            if slippage > expected_profit_ratio * self.max_slippage_ratio:
                self.log(
                    f"⚠️ 滑点过高 ({slippage:.3f}), 超过阈值 ({expected_profit_ratio * self.max_slippage_ratio:.3f})",
                    "WARN",
                )

                # 尝试分批交易 (TWAP)
                batch_count = 3  # 分3批
                batch_size = max(1.0, adjusted_amount / batch_count)  # 确保每批至少$1

                # 如果单批金额太小，减少批次数量
                if batch_size < 1.0:
                    batch_count = max(1, int(adjusted_amount))  # 按整数美元分批
                    batch_size = max(1.0, adjusted_amount / batch_count)

                self.log(f"🔄 启用分批交易: {batch_count}批，每批 ${batch_size:.2f}")

                success_count = 0
                total_filled = 0

                for i in range(batch_count):
                    try:
                        success, result = await self.buy_strategy.create_buy_order(
                            token_id=token_id,
                            amount=batch_size,
                            side="BUY",
                        )

                        if success:
                            success_count += 1
                            # 使用batch_size作为实际金额，因为create_buy_order返回的是dict
                            actual_amount = batch_size
                            total_filled += actual_amount
                            self.log(
                                f"✅ 分批交易 {i+1}/{batch_count} 成功: ${actual_amount:.2f}"
                            )
                            await asyncio.sleep(1)  # 分批间隔1秒
                        else:
                            self.log(f"❌ 分批交易 {i+1}/{batch_count} 失败")
                            break

                    except Exception as e:
                        self.log(f"❌ 分批交易 {i+1}/3 异常: {e}", "ERROR")
                        break

                if success_count > 0:
                    self.log(
                        f"✅ 分批交易完成: {success_count}/3 成功, 总金额: ${total_filled:.2f}"
                    )

                    # 记录仓位
                    self.position = {
                        "side": signal,
                        "token_id": token_id,
                        "entry_price": self.current_price,
                        "entry_prob": market_data["yes_prob"],
                        "entry_time": time.time(),
                        "amount": total_filled,
                    }

                    # 确认持仓记录成功
                    self.log(
                        f"📊 分批持仓已记录: {self.position['side']} | Token: {token_id} | 总金额: ${total_filled:.2f}",
                        "INFO",
                    )
                else:
                    self.log(f"❌ 分批交易全部失败")

                return

        # 步骤2: 正常单笔交易
        # 确保金额符合最小要求
        final_amount = max(1.0, adjusted_amount)
        if final_amount != adjusted_amount:
            self.log(
                f"⚠️ 调整交易金额: ${adjusted_amount:.2f} -> ${final_amount:.2f} (最小要求)"
            )

        try:
            success, result = await self.buy_strategy.create_buy_order(
                token_id=token_id,
                amount=final_amount,
                side="BUY",
            )

            if success:
                # 从result字典中提取实际金额，如果没有则使用final_amount
                actual_amount = final_amount  # 默认使用请求的金额
                if isinstance(result, dict):
                    # 如果result包含实际成交信息，可以在这里提取
                    # actual_amount = result.get('filled_amount', final_amount)
                    pass

                self.log(f"✅ 狙击交易成功: {signal} | 金额: ${actual_amount:.2f}")

                # 记录仓位
                self.position = {
                    "side": signal,
                    "token_id": token_id,
                    "entry_price": self.current_price,
                    "entry_prob": market_data["yes_prob"],
                    "entry_time": time.time(),
                    "amount": actual_amount,
                }

                # 确认持仓记录成功
                self.log(
                    f"📊 持仓已记录: {self.position['side']} | Token: {token_id} | 金额: ${actual_amount:.2f}",
                    "INFO",
                )
            else:
                self.log(f"❌ 狙击交易失败: {signal}")

        except Exception as e:
            self.log(f"❌ 狙击交易异常: {e}", "ERROR")

    def log_enhanced_market_status_v3(
        self,
        current_price,
        market_prob,
        ema_offset,  # 使用EMA偏移替代price_deviation
        should_enter,
        reason,
        adaptive_threshold_v3,
        buyer_maker_ratio,
        breakout_type,
        adaptive_prob_threshold=None,
    ):
        """记录V3增强的市场状态日志 - 基于EMA偏移"""
        current_time = time.time()
        if current_time - self.last_market_log_time >= 10:  # 10秒间隔
            volatility = self.calculate_10min_volatility()
            theoretical_prob = self.calculate_theoretical_probability(current_price)
            prob_diff = abs(theoretical_prob - market_prob)

            # 使用传入的adaptive_prob_threshold，如果没有则计算
            if adaptive_prob_threshold is None:
                adaptive_prob_threshold = self.get_adaptive_prob_threshold()

            # V3优化: 显示EMA相关信息
            ema_5min = getattr(self, "ema_5min", current_price)

            status_msg = (
                f"📊 V3增强监控 | "
                f"当前价格: ${current_price:,.2f} | "
                f"5分钟EMA: ${ema_5min:,.2f} | "
                f"EMA偏移: {ema_offset:+.1f} USDT | "
                f"市场概率: {market_prob:.3f} | "
                f"理论概率: {theoretical_prob:.3f} | "
                f"概率差: {prob_diff:.3f} | "
                f"波动率: {volatility:.1f} | "
                f"V3阈值: {adaptive_threshold_v3:.1f} | "
                f"概率阈值: {adaptive_prob_threshold:.3f} | "
                f"买盘比例: {buyer_maker_ratio:.2f} | "
                f"突破类型: {breakout_type} | "
                f"入场: {'✅' if should_enter else '❌'}"
            )

            # V3优化: 添加概率边界保护状态
            if self.extreme_prob_protection:
                if market_prob < self.prob_boundary_low:
                    status_msg += (
                        f" | ⚠️概率过低({market_prob:.3f}<{self.prob_boundary_low})"
                    )
                elif market_prob > self.prob_boundary_high:
                    status_msg += (
                        f" | ⚠️概率过高({market_prob:.3f}>{self.prob_boundary_high})"
                    )
                else:
                    status_msg += f" | ✅概率安全区间"

            if reason:
                status_msg += f" | 详情: {reason}"

            self.log(status_msg)
            self.last_market_log_time = current_time

    async def execute_sniper_trade(self, signal, market_data, reason):
        """执行狙击交易 - 使用BuyStrategy的市价策略"""
        if signal == "BUY_YES":
            token_id = market_data["token_id_yes"]
        elif signal == "BUY_NO":
            token_id = market_data["token_id_no"]
        else:
            return

        self.log(f"🎯 SNIPER TRADE: {signal} | {reason}")

        # 使用BuyStrategy执行市价买入
        # 确保金额符合最小要求
        trade_amount = max(1.0, getattr(self, "trade_amount", 100.0))

        try:
            success, result = await self.buy_strategy.create_buy_order(
                token_id=token_id,
                amount=trade_amount,  # 使用验证后的交易金额
                side="BUY",
            )

            if success:
                # 使用trade_amount作为实际金额，因为create_buy_order返回的是dict
                actual_amount = trade_amount
                self.log(f"✅ 狙击交易成功: {signal} | 金额: ${actual_amount:.2f}")

                # 记录仓位
                self.position = {
                    "side": signal,
                    "token_id": token_id,
                    "entry_price": self.current_price,
                    "entry_prob": market_data["yes_prob"],
                    "entry_time": time.time(),
                    "amount": actual_amount,
                }

                # 确认持仓记录成功 - execute_sniper_trade方法
                self.log(
                    f"📊 [简单交易] 持仓已记录: {self.position['side']} | Token: {token_id} | 金额: ${actual_amount:.2f}",
                    "INFO",
                )
            else:
                self.log(f"❌ 狙击交易失败: {signal}")

        except Exception as e:
            self.log(f"❌ 狙击交易异常: {e}", "ERROR")

    def update_baseline_price(self):
        """更新基准价格 - 修复版：使用更长周期的移动平均，避免过度跟踪"""
        if len(self.price_history) >= 300:  # 至少需要5分钟数据
            # 使用5分钟移动平均作为基准价格，更新频率降低
            recent_prices = list(self.price_history)[-300:]  # 最近5分钟
            five_min_avg = sum(recent_prices) / len(recent_prices)

            # 使用非常小的alpha值，让基准价格变化缓慢
            alpha = 0.01  # 从2/21=0.095降低到0.01
            self.baseline_price = (five_min_avg * alpha) + (
                self.baseline_price * (1 - alpha)
            )

            # 记录基准价格更新（调试用）
            if (
                hasattr(self, "_last_baseline_log")
                and time.time() - self._last_baseline_log > 300
            ):  # 5分钟记录一次
                self.log(
                    f"📊 基准价格更新: ${self.baseline_price:.2f} (5分钟均价: ${five_min_avg:.2f})",
                    "DEBUG",
                )
                self._last_baseline_log = time.time()

    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """获取市场信息 - 参照btc_15min_strategy.py的实现"""
        try:
            url = f"{self.gamma_api_base}/markets/{market_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            market_data = response.json()

            if market_data:
                outcomes = market_data.get("outcomes", "[]")
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)

                outcome_prices = market_data.get("outcomePrices", "[]")
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)

                clob_token_ids = market_data.get("clobTokenIds", "[]")
                if isinstance(clob_token_ids, str):
                    clob_token_ids = json.loads(clob_token_ids)
                    book = self.clob_client.get_order_book(clob_token_ids[0])

                    if book and book.bids and book.asks:
                        best_bid = float(book.bids[-1].price)
                        best_ask = float(book.asks[-1].price)
                        yes_prob = (best_bid + best_ask) / 2
                        no_prob = 1 - yes_prob

                        outcome_prices[0] = yes_prob
                        outcome_prices[1] = no_prob

                return {
                    "id": market_data.get("id"),
                    "question": market_data.get("question"),
                    "outcomes": outcomes,
                    "outcomePrices": outcome_prices,
                    "clobTokenIds": clob_token_ids,
                    "active": market_data.get("active", True),
                    "acceptingOrders": market_data.get("acceptingOrders", True),
                    "endDate": market_data.get("endDate"),
                    "closesAt": market_data.get("closesAt"),
                    "endTime": market_data.get("endTime"),
                }

            return None

        except Exception as e:
            self.log(f"获取市场信息失败: {e}", "ERROR")
            return None

    async def fetch_market_sentiment(self):
        """
        从 Gamma API 获取最新的市场概率数据
        基于btc_15min_strategy.py的get_market_info方法，增强网络容错性
        """
        # 如果有缓存数据且时间不超过5秒，直接返回缓存
        current_time = time.time()
        if (
            hasattr(self, "_cached_market_data")
            and hasattr(self, "_cache_timestamp")
            and current_time - self._cache_timestamp < 5  # 改为5秒缓存
            and self._cached_market_data is not None
        ):
            return self._cached_market_data

        # 重试配置
        max_retries = 3
        retry_delays = [1, 2, 3]  # 递增延迟

        for attempt in range(max_retries):
            try:
                # 使用同步方法获取市场信息
                market_info = self.get_market_info(self.market_id)
                if not market_info:
                    raise Exception("无法获取市场信息")

                # 检查市场状态
                is_active = market_info.get("active", False)
                accepting_orders = market_info.get("acceptingOrders", False)

                if not is_active or not accepting_orders:
                    self.log("⚠️ 市场已关闭或不接受订单", "WARN")
                    return None  # 市场不可交易

                # 解析概率数据
                outcome_prices = market_info.get("outcomePrices", [])
                yes_prob = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5

                # 解析token IDs
                clob_token_ids = market_info.get("clobTokenIds", [])

                result = {
                    "yes_prob": yes_prob,
                    "token_id_yes": (
                        clob_token_ids[0] if len(clob_token_ids) > 0 else ""
                    ),
                    "token_id_no": clob_token_ids[1] if len(clob_token_ids) > 1 else "",
                    "volume_24hr": 0,  # 这个字段在原始API中可能不存在
                    "liquidity": 0,  # 这个字段在原始API中可能不存在
                    "question": market_info.get("question", ""),
                    "outcomes": market_info.get("outcomes", []),
                    "endDate": market_info.get("endDate"),
                    "closesAt": market_info.get("closesAt"),
                    "endTime": market_info.get("endTime"),
                }

                # 缓存成功的结果
                self._cached_market_data = result
                self._cache_timestamp = current_time

                # 如果之前有错误，记录恢复日志
                if attempt > 0:
                    self.log(f"✅ API连接恢复 (重试{attempt+1}次后成功)", "INFO")

                return result

            except Exception as e:
                self.log(
                    f"⚠️ API请求异常 (尝试 {attempt + 1}/{max_retries}): {e}", "WARN"
                )

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delays[attempt])

        # 所有重试都失败，尝试备用方法
        self.log("🔄 主API失败，尝试备用数据源...", "WARN")
        fallback_data = await self.fetch_market_sentiment_fallback()
        if fallback_data:
            return fallback_data

        # 如果备用方法也失败，返回缓存数据
        if hasattr(self, "_cached_market_data"):
            self.log("🔄 使用缓存的市场数据 (所有数据源不可用)", "WARN")
            return self._cached_market_data

        self.log(f"❌ 所有数据源都失败，已重试{max_retries}次", "ERROR")
        return None

    async def fetch_market_sentiment_fallback(self):
        """
        备用市场数据获取方法
        当主API不可用时，使用模拟数据或其他数据源
        """
        try:
            # 方案1: 尝试使用不同的超时设置重新调用主方法
            try:
                # 降低超时时间，快速失败
                url = f"{self.gamma_api_base}/markets/{self.market_id}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                market_data = response.json()
                if market_data:
                    # 使用相同的解析逻辑
                    outcome_prices = market_data.get("outcomePrices", "[]")
                    if isinstance(outcome_prices, str):
                        outcome_prices = json.loads(outcome_prices)

                    clob_token_ids = market_data.get("clobTokenIds", "[]")
                    if isinstance(clob_token_ids, str):
                        clob_token_ids = json.loads(clob_token_ids)

                    yes_prob = (
                        float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
                    )

                    result = {
                        "yes_prob": yes_prob,
                        "token_id_yes": (
                            clob_token_ids[0] if len(clob_token_ids) > 0 else ""
                        ),
                        "token_id_no": (
                            clob_token_ids[1] if len(clob_token_ids) > 1 else ""
                        ),
                        "volume_24hr": 0,
                        "liquidity": 0,
                        "question": market_data.get("question", ""),
                        "outcomes": market_data.get("outcomes", []),
                    }

                    self.log("🔄 备用API调用成功", "INFO")
                    return result
            except:
                pass

            # 方案2: 基于价格偏离生成模拟概率
            if hasattr(self, "current_price") and self.current_price > 0:
                price_deviation = self.current_price - self.baseline_price
                volatility = self.calculate_10min_volatility()

                # 简单的价格-概率映射
                if abs(price_deviation) > volatility * 2:
                    # 大幅偏离时，概率偏向价格方向
                    simulated_prob = 0.6 if price_deviation > 0 else 0.4
                else:
                    # 小幅偏离时，概率接近中性
                    simulated_prob = 0.5 + (price_deviation / (volatility * 10))

                simulated_prob = max(0.1, min(0.9, simulated_prob))

                self.log(
                    f"🔄 使用模拟市场数据: 概率={simulated_prob:.3f} (基于价格偏离)",
                    "WARN",
                )

                result = {
                    "yes_prob": simulated_prob,
                    "token_id_yes": "simulated_yes_token",
                    "token_id_no": "simulated_no_token",
                    "volume_24hr": 0,
                    "liquidity": 0,
                    "is_simulated": True,
                    "question": "Simulated Market",
                    "outcomes": ["YES", "NO"],
                }

                # 缓存模拟数据（较短的缓存时间）
                self._cached_market_data = result
                self._cache_timestamp = time.time()

                return result

        except Exception as e:
            self.log(f"备用数据获取也失败: {e}", "ERROR")

        return None

    async def check_network_health(self):
        """检查网络连接健康状态"""
        try:
            # 测试基本的网络连接
            test_urls = [
                "https://api.binance.com/api/v3/ping",
                "https://gamma-api.polymarket.com",
                "https://httpbin.org/get",
            ]

            healthy_connections = 0
            for url in test_urls:
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=5)  # 增加超时时间到5秒
                    ) as session:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                healthy_connections += 1
                except:
                    continue

            health_ratio = healthy_connections / len(test_urls)

            # 调整健康状态判定标准，降低敏感度
            if health_ratio >= 0.5:  # 从0.67降低到0.5
                return "GOOD"
            elif health_ratio >= 0.33:
                return "POOR"
            else:
                return "BAD"

        except Exception as e:
            self.log(f"网络健康检查失败: {e}", "ERROR")
            return "UNKNOWN"

    async def periodic_network_check(self):
        """定期网络健康检查"""
        while True:
            try:
                health = "HEALTH"
                current_time = time.time()

                # 每5分钟记录一次网络状态
                if (
                    not hasattr(self, "_last_network_log")
                    or current_time - self._last_network_log > 300
                ):
                    self.log(f"🌐 网络健康状态: {health}", "INFO")
                    self._last_network_log = current_time

                # 如果网络状态差，调整策略参数
                if health == "BAD":
                    self.log("⚠️ 网络状态差，暂停新交易", "WARN")
                elif health == "POOR":
                    self.log("⚠️ 网络状态一般，降低交易频率", "WARN")

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                self.log(f"网络检查异常: {e}", "ERROR")
                await asyncio.sleep(60)

    async def monitor_position(self):
        """监控持仓，15分钟强制平仓"""
        while True:
            if self.position["side"]:
                elapsed = time.time() - self.position["entry_time"]

                # 14分钟后开始寻找平仓机会
                if elapsed > 840:  # 14分钟
                    self.log("⏰ Position near expiry, preparing to close...")

                # 15分钟强制平仓
                if elapsed > 900:  # 15分钟
                    self.log("🔴 FORCE CLOSE: 15min expiry reached")
                    await self.close_position("TIME_EXPIRY")

            await asyncio.sleep(10)  # 每10秒检查一次

    async def close_position(self, reason):
        """平仓操作 - 使用SellStrategy的市价卖出策略"""
        if not self.position["side"]:
            return

        self.log(f"📤 Closing position: {reason}")

        # 获取当前持仓的token_id
        current_token_id = self.position["token_id"]
        position_amount = self.position["amount"]

        try:
            # 使用SellStrategy执行市价卖出
            self.log(f"🔄 平仓策略: 直接卖出持仓token")
            self.log(
                f"📊 持仓信息: token_id={current_token_id}, amount={position_amount}"
            )

            # 使用SellStrategy的exit_position方法
            success = await self.sell_strategy.exit_position(
                token_id=current_token_id, amount=position_amount
            )

            if success:
                self.log(f"✅ 平仓成功: 已卖出持仓token | token_id: {current_token_id}")
            else:
                self.log(f"❌ 平仓失败: 卖出操作未成功")

        except Exception as e:
            self.log(f"❌ 平仓异常: {e}", "ERROR")

        # 重置仓位（无论平仓是否成功）
        self.position = {
            "side": None,
            "amount": 0,
            "token_id": None,
            "entry_price": 0,
            "entry_prob": 0,
            "entry_time": 0,
        }

    async def periodic_market_monitor(self):
        """定期市场监控 - 确保每10秒记录一次市场状态"""
        while True:
            try:
                if self.current_price > 0:  # 确保已经有价格数据
                    # 获取市场数据
                    market_data = await self.fetch_market_sentiment()
                    if market_data:
                        price_deviation = self.current_price - self.baseline_price
                        dynamic_threshold = self.get_dynamic_threshold()
                        should_enter = abs(price_deviation) >= dynamic_threshold

                        # 计算理论概率和概率差异
                        theoretical_prob = self.calculate_theoretical_probability(
                            self.current_price
                        )
                        prob_diff = abs(theoretical_prob - market_data["yes_prob"])
                        adaptive_prob_threshold = self.get_adaptive_prob_threshold()

                        # 分析买卖盘强度
                        recent_trades = list(self.trade_data_history)[-20:]
                        buyer_maker_ratio = self.analyze_buyer_maker_ratio(
                            recent_trades
                        )
                        breakout_type, _ = self.classify_breakout_type(
                            price_deviation, buyer_maker_ratio
                        )

                        # 生成详细的监控原因
                        detailed_reason = self._generate_detailed_monitor_reason(
                            price_deviation,
                            dynamic_threshold,
                            prob_diff,
                            adaptive_prob_threshold,
                            theoretical_prob,
                            market_data["yes_prob"],
                            buyer_maker_ratio,
                            breakout_type,
                            should_enter,
                        )

                        # 记录市场状态
                        self.log_market_status(
                            self.current_price,
                            market_data["yes_prob"],
                            price_deviation,
                            should_enter,
                            detailed_reason,
                        )

                        # 记录持仓状态 (如果有持仓)
                        self.log_position_status(
                            market_data["yes_prob"], self.current_price
                        )

                await asyncio.sleep(5)  # 改为每5秒执行一次

            except Exception as e:
                self.log(f"定期监控异常: {e}", "ERROR")
                await asyncio.sleep(5)

    async def run(self, amount: float = 100):
        """主运行循环 - V3优化版"""
        self.log("🎯 BTC High Odds Sniper Strategy V3 - 三重优化版")
        self.log("=" * 70)
        self.log("� V3核心优a化:")
        self.log("  1️⃣ EMA偏移替代固定基准 - 捕捉短线异常脉冲")
        self.log("  2️⃣ 波动率深度绑定阈值 - 动态风险控制")
        self.log("  3️⃣ 概率边界保护 - 避开垃圾时间和强趋势")
        self.log("=" * 70)
        self.log(f"📊 Market ID: {self.market_id}")
        self.log(f"💰 Trade Amount: ${amount}")
        self.log(f"📊 Initial Baseline Price: ${self.baseline_price:,.2f}")
        self.log(f"📊 Core Sensitivity: {self.core_sensitivity} USDT")
        self.log(f"📊 Volatility Multiplier: {self.volatility_multiplier}x")
        self.log(f"📊 Mu Factor: {self.mu_factor}")
        self.log(
            f"📊 Probability Boundaries: {self.prob_boundary_low:.1f} - {self.prob_boundary_high:.1f}"
        )
        self.log(f"📊 EMA Alpha: {self.ema_alpha:.4f} (5分钟)")
        self.log(f"📊 Base Probability Lag Threshold: {self.prob_lag_threshold:.1%}")
        self.log(f"⚡ Max Response Time: {self.max_response_time*1000:.0f}ms")
        self.log(f"🛡️ Max Slippage Ratio: {self.max_slippage_ratio:.0%}")
        self.log(f"🚫 No Entry Window: {self.no_entry_window/60:.1f} 分钟")
        self.log(
            "🔧 Trading Mode: V3 Enhanced with EMA + Volatility + Probability Protection"
        )
        self.log("=" * 70)

        # 验证并调整交易金额 - 确保符合Polymarket最小订单要求
        min_order_amount = 1.0  # Polymarket最小订单金额
        if amount < min_order_amount:
            self.log(
                f"⚠️ 交易金额 ${amount} 低于最小要求 ${min_order_amount}，自动调整为 ${min_order_amount}"
            )
            amount = min_order_amount

        # 设置交易金额
        self.trade_amount = amount

        # 启动并发任务
        tasks = [
            asyncio.create_task(self.price_provider.start()),  # 使用价格提供器
            asyncio.create_task(self.monitor_position()),
            asyncio.create_task(self.update_baseline_periodically()),
            asyncio.create_task(self.periodic_market_monitor()),  # 定期监控
            asyncio.create_task(self.periodic_network_check()),  # 网络监控
            asyncio.create_task(self.update_liquidity_cache()),  # 流动性监控
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.log("🛑 Strategy stopped by user")
        except Exception as e:
            self.log(f"🔴 Strategy error: {e}", "ERROR")

    async def update_liquidity_cache(self):
        """定期更新流动性缓存"""
        while True:
            try:
                # 获取市场数据
                market_data = await self.fetch_market_sentiment()
                if market_data and not market_data.get("is_simulated", False):
                    # 获取Yes token的订单簿
                    token_id_yes = market_data.get("token_id_yes")
                    if token_id_yes:
                        order_book = await self.get_order_book(token_id_yes)
                        if order_book:
                            volume_24hr = market_data.get("volume_24hr", 0)
                            liquidity_score = self.calculate_liquidity_score(
                                order_book, volume_24hr
                            )
                            self.liquidity_cache[self.market_id] = liquidity_score

                            self.log(f"🌊 流动性更新: {liquidity_score:.3f}", "DEBUG")

                await asyncio.sleep(60)  # 每分钟更新一次流动性缓存

            except Exception as e:
                self.log(f"流动性缓存更新失败: {e}", "ERROR")
                await asyncio.sleep(60)

    async def update_baseline_periodically(self):
        """定期更新基准价格 - 修复版：降低更新频率"""
        while True:
            self.update_baseline_price()
            await asyncio.sleep(300)  # 从30秒改为5分钟更新一次基准价格


if __name__ == "__main__":
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="BTC高赔率狙击者策略 V3 - 三重优化版")
    parser.add_argument("market_id", nargs="?", default="0x...", help="市场ID")
    parser.add_argument("amount", nargs="?", type=float, default=100.0, help="交易金额")
    parser.add_argument(
        "baseline_price", nargs="?", type=float, default=82500.0, help="基准价格"
    )

    # 如果没有参数，使用默认配置
    if len(sys.argv) == 1:
        # 使用默认配置
        config = {
            "market_id": "0x...",  # 替换为实际的市场ID
            "baseline_price": 82500.0,  # 基于当前BTC价格
            "core_sensitivity": 50.0,  # 核心敏感度阈值 (40-60 USDT)
            "mu_factor": 1.2,  # 动态敏感度系数 (降低到1.2，使阈值更合理)
        }
        trade_amount = 100.0
    else:
        args = parser.parse_args()
        config = {
            "market_id": args.market_id,
            "baseline_price": args.baseline_price,
            "core_sensitivity": 50.0,  # 核心敏感度阈值 (40-60 USDT)
            "mu_factor": 1.2,  # 动态敏感度系数 (降低到1.2，使阈值更合理)
        }
        trade_amount = args.amount

    print("🎯 BTC High Odds Sniper Strategy V3 - 三重优化版")
    print("=" * 70)
    print("🔧 V3核心优化:")
    print("  1️⃣ EMA偏移替代固定基准 - 捕捉短线异常脉冲，过滤牛市波段")
    print("  2️⃣ 波动率深度绑定阈值 - Threshold = Core + (Volatility × 2.5)")
    print("  3️⃣ 概率边界保护 - 避开<0.2或>0.8的垃圾时间和强趋势")
    print("=" * 70)
    print("🔧 技术特性:")
    print("  • ATR自适应阈值 (30-200 USDT)")
    print("  • 流动性自适应概率阈值 (8%-18%)")
    print("  • 订单簿滑点校验 + TWAP分批")
    print("  • 买卖盘强度分析 (真假突破判定)")
    print("  • 5分钟EMA实时跟踪")
    print("  • 概率边界自动保护")
    print("=" * 70)
    print(f"📊 Market ID: {config['market_id']}")
    print(f"� Trad e Amount: ${trade_amount}")
    print(f"📊 Baseline Price: ${config['baseline_price']:,.2f}")
    print(f"� Core Senpsitivity: {config['core_sensitivity']} USDT")
    print(f"📊 Dynamic Factor: {config['mu_factor']} (优化后)")
    print(f"📊 Volatility Multiplier: 2.5x (新增)")
    print(f"📊 Probability Boundaries: 0.2 - 0.8 (新增)")
    print(
        f"📊 Expected Base Threshold: ~{config['core_sensitivity'] * config['mu_factor']:.1f} USDT"
    )
    print(
        f"📊 Expected Max Threshold: ~{(config['core_sensitivity'] + 50 * 2.5) * config['mu_factor']:.1f} USDT (高波动时)"
    )
    print(f"📊 Base Probability Lag Threshold: 12%")
    print(f"⚡ Max Response Time: 500ms")
    print(f"🛡️ Max Slippage Ratio: 40%")
    print("🔧 Trading Mode: V3 Enhanced with Triple Optimization")
    print("=" * 70)

    strategy = BTCHighOddsSniperStrategy(**config)

    try:
        asyncio.run(strategy.run(amount=trade_amount))
    except KeyboardInterrupt:
        print("\n🛑 Strategy stopped by user")
    except Exception as e:
        print(f"\n🔴 Strategy error: {e}")
