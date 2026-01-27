#!/usr/bin/env python3
"""
BTC 15min Polymarket V2 策略
基于新的策略要求实现：
- 时间：10:00–12:00 / 15:30–19:00
- 频次：15min 最多 1 单
- 过滤：15min 波动 ≥ 30, EMA9 > EMA21（多）/ EMA9 < EMA21（空）
- 入场：突破后回踩确认, 入场区间：0.60～0.62
- 止盈：第一目标 0.90 或 RR ≥ 1.5
- 止损：最近 5min 结构点 - buffer
- 风控：连续 2 笔止损 → 冷却 45min
"""
import math
import sys
import os
import json
import time
import asyncio
import websockets
import requests
import csv
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from threading import Thread, Event, Lock
import signal
import pytz
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from py_clob_client.clob_types import (
    OrderArgs,
    OrderType,
    MarketOrderArgs,
    BalanceAllowanceParams,
    AssetType,
)
from trading.polymarket_clob_client import PolymarketCLOBClient
from trading.order_manager import OrderManager
from trading.buy_strategy import BuyStrategy
from trading.sell_strategy import SellStrategy


class BTC15MinStrategyV2:
    """BTC 15分钟策略 V2"""

    def __init__(self, baseline_price: float = 95000.0):
        self.clob_wrapper = PolymarketCLOBClient()
        self.clob_client = self.clob_wrapper.get_client()
        self.order_manager = OrderManager()

        # 初始化买卖策略
        self.buy_strategy = BuyStrategy(self.clob_client, self.log)
        self.sell_strategy = SellStrategy(self.clob_client, self.log)

        self.gamma_api_base = "https://gamma-api.polymarket.com"

        # 设置基准价格
        self.baseline_price = baseline_price

        # V2 策略参数 - 新的交易时段
        self.trading_sessions = [
            {"start": 10, "end": 12},  # 10:00-12:00
            {"start": 15.5, "end": 19},  # 15:30-19:00 (15.5 = 15:30)
        ]

        # V2 过滤条件
        self.min_volatility = 30  # 15min 波动 ≥ 30
        self.ema_periods = {"fast": 9, "slow": 21}  # EMA9 和 EMA21

        # V2 入场参数
        self.entry_range = {"min": 0.60, "max": 0.62}  # 入场区间 0.60-0.62
        self.pullback_confirmation_time = 300  # 5分钟回踩确认

        # V2 止盈止损参数
        self.take_profit_target = 0.90  # 第一目标 0.90
        self.min_risk_reward = 1.5  # 最小风险回报比 1.5
        self.structure_lookback = 5  # 最近5分钟结构点
        self.stop_buffer = 0.02  # 止损缓冲 2%

        # V2 风控参数
        self.max_consecutive_losses = 2  # 连续止损次数
        self.cooldown_period = 45  # 冷却时间 45分钟

        # 状态跟踪
        self.current_interval = None
        self.position = None
        self.price_history = []
        self.ema_data = {"fast": [], "slow": []}
        self.running = False
        self.stop_event = Event()
        self.data_lock = Lock()
        self.default_amount = 5.0

        # V2 新增状态
        self.consecutive_losses = 0
        self.last_loss_time = None
        self.traded_intervals = set()
        self.volatility_buffer = []
        self.structure_points = []

        # BTC价格监控
        self.btc_price = None
        self.price_update_time = None

        # 北京时区
        self.beijing_tz = pytz.timezone("Asia/Shanghai")

        # 日志设置
        self.setup_logging()

        self.log(f"📋 BTC 15min Strategy V2 初始化完成")
        self.log(f"📋 基准价格: ${self.baseline_price:,.2f}")

    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/btc_strategy_v2_logs"
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"btc_15min_v2_{timestamp}.log")

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"写入日志失败: {e}")

    def get_beijing_time(self) -> datetime:
        """获取北京时间"""
        return datetime.now(self.beijing_tz)

    def is_trading_hours(self) -> bool:
        """检查是否在交易时段 - V2 双时段"""
        beijing_time = self.get_beijing_time()
        hour_decimal = beijing_time.hour + beijing_time.minute / 60.0

        for session in self.trading_sessions:
            if session["start"] <= hour_decimal < session["end"]:
                return True
        return False

    def get_current_session(self) -> Optional[Dict]:
        """获取当前交易时段"""
        beijing_time = self.get_beijing_time()
        hour_decimal = beijing_time.hour + beijing_time.minute / 60.0

        for session in self.trading_sessions:
            if session["start"] <= hour_decimal < session["end"]:
                return session
        return None

    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """计算EMA"""
        if len(prices) < period:
            return None

        # 简单移动平均作为初始EMA
        if len(prices) == period:
            return sum(prices) / period

        # EMA计算
        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def update_ema_data(self, price: float):
        """更新EMA数据"""
        # 添加价格到历史数据
        self.price_history.append({"timestamp": time.time(), "price": price})

        # 保持最近100个价格点
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]

        # 提取价格列表
        prices = [p["price"] for p in self.price_history]

        # 计算EMA
        ema_fast = self.calculate_ema(prices, self.ema_periods["fast"])
        ema_slow = self.calculate_ema(prices, self.ema_periods["slow"])

        if ema_fast and ema_slow:
            self.ema_data["fast"] = ema_fast
            self.ema_data["slow"] = ema_slow
            return True
        return False

    def check_ema_trend(self) -> Tuple[bool, str]:
        """检查EMA趋势"""
        if not self.ema_data["fast"] or not self.ema_data["slow"]:
            return (
                False,
                f"EMA数据不足 (需要至少{max(self.ema_periods['fast'], self.ema_periods['slow'])}个价格点)",
            )

        ema_fast = self.ema_data["fast"]
        ema_slow = self.ema_data["slow"]

        difference = abs(ema_fast - ema_slow)
        percentage_diff = (difference / ema_slow) * 100

        if ema_fast > ema_slow:
            return (
                True,
                f"多头趋势 ✅ (EMA9: {ema_fast:.2f} > EMA21: {ema_slow:.2f}, 差距: {percentage_diff:.3f}%)",
            )
        elif ema_fast < ema_slow:
            return (
                True,
                f"空头趋势 ✅ (EMA9: {ema_fast:.2f} < EMA21: {ema_slow:.2f}, 差距: {percentage_diff:.3f}%)",
            )
        else:
            return (
                False,
                f"趋势不明确 (EMA9: {ema_fast:.2f} ≈ EMA21: {ema_slow:.2f}, 差距: {percentage_diff:.3f}%)",
            )

    def calculate_15min_volatility(self) -> Optional[float]:
        """计算15分钟波动率"""
        if len(self.price_history) < 2:
            return None

        # 获取最近15分钟的价格数据
        recent_time = time.time() - 900  # 15分钟 = 900秒
        recent_prices = [p for p in self.price_history if p["timestamp"] >= recent_time]

        if len(recent_prices) < 2:
            return None

        prices = [p["price"] for p in recent_prices]
        volatility = max(prices) - min(prices)

        return volatility

    def check_volatility_filter(self) -> Tuple[bool, str]:
        """检查波动率过滤条件"""
        volatility = self.calculate_15min_volatility()

        if volatility is None:
            return False, "波动率数据不足 (需要至少2个价格点)"

        if volatility >= self.min_volatility:
            return True, f"波动率 ${volatility:.2f} >= ${self.min_volatility} ✅"
        else:
            return (
                False,
                f"波动率 ${volatility:.2f} < ${self.min_volatility} (差距: ${self.min_volatility - volatility:.2f})",
            )

    def detect_breakout_and_pullback(self, current_price: float) -> Tuple[bool, str]:
        """检测突破和回踩"""
        if len(self.price_history) < 10:
            return False, f"价格历史不足 (当前: {len(self.price_history)}, 需要: 10)"

        # 获取最近的价格数据
        recent_prices = [p["price"] for p in self.price_history[-10:]]

        # 简单的突破检测：当前价格是否突破了最近的高点或低点
        recent_high = max(recent_prices[:-1])  # 排除当前价格
        recent_low = min(recent_prices[:-1])

        price_range = recent_high - recent_low
        breakout_threshold = price_range * 0.001  # 0.1% 的突破阈值

        # 检测突破
        if current_price > recent_high + breakout_threshold:
            # 向上突破，检查是否有回踩
            pullback_time = time.time() - self.pullback_confirmation_time
            pullback_prices = [
                p for p in self.price_history if p["timestamp"] >= pullback_time
            ]

            if len(pullback_prices) >= 3:
                pullback_values = [p["price"] for p in pullback_prices]
                pullback_low = min(pullback_values)
                pullback_threshold = current_price * 0.995  # 0.5%回踩

                if pullback_low < pullback_threshold:
                    return (
                        True,
                        f"向上突破后回踩确认 ✅ (突破: ${current_price:.2f} > ${recent_high:.2f}, 回踩至: ${pullback_low:.2f})",
                    )
                else:
                    return (
                        False,
                        f"向上突破但回踩不足 (突破: ${current_price:.2f}, 最低回踩: ${pullback_low:.2f}, 需要 < ${pullback_threshold:.2f})",
                    )
            else:
                return (
                    False,
                    f"向上突破但回踩数据不足 (当前: {len(pullback_prices)}, 需要: 3)",
                )

        elif current_price < recent_low - breakout_threshold:
            # 向下突破，检查是否有回踩
            pullback_time = time.time() - self.pullback_confirmation_time
            pullback_prices = [
                p for p in self.price_history if p["timestamp"] >= pullback_time
            ]

            if len(pullback_prices) >= 3:
                pullback_values = [p["price"] for p in pullback_prices]
                pullback_high = max(pullback_values)
                pullback_threshold = current_price * 1.005  # 0.5%回踩

                if pullback_high > pullback_threshold:
                    return (
                        True,
                        f"向下突破后回踩确认 ✅ (突破: ${current_price:.2f} < ${recent_low:.2f}, 回踩至: ${pullback_high:.2f})",
                    )
                else:
                    return (
                        False,
                        f"向下突破但回踩不足 (突破: ${current_price:.2f}, 最高回踩: ${pullback_high:.2f}, 需要 > ${pullback_threshold:.2f})",
                    )
            else:
                return (
                    False,
                    f"向下突破但回踩数据不足 (当前: {len(pullback_prices)}, 需要: 3)",
                )
        else:
            # 没有突破
            upward_distance = (recent_high + breakout_threshold) - current_price
            downward_distance = current_price - (recent_low - breakout_threshold)

            return (
                False,
                f"未突破关键位 (当前: ${current_price:.2f}, 需突破: ${recent_high + breakout_threshold:.2f}↑ 或 ${recent_low - breakout_threshold:.2f}↓, 距离: +${upward_distance:.2f}/-${downward_distance:.2f})",
            )

    def is_in_cooldown(self) -> Tuple[bool, str]:
        """检查是否在冷却期"""
        if self.consecutive_losses < self.max_consecutive_losses:
            return (
                False,
                f"连续止损 {self.consecutive_losses}/{self.max_consecutive_losses}",
            )

        if not self.last_loss_time:
            return False, "无冷却记录"

        cooldown_end = self.last_loss_time + (self.cooldown_period * 60)
        current_time = time.time()

        if current_time < cooldown_end:
            remaining = (cooldown_end - current_time) / 60
            return True, f"冷却中，剩余 {remaining:.1f} 分钟"
        else:
            # 冷却期结束，重置连续止损计数
            self.consecutive_losses = 0
            return False, "冷却期结束"

    def find_structure_point(self) -> Optional[float]:
        """寻找最近5分钟的结构点"""
        if len(self.price_history) < 5:
            return None

        # 获取最近5分钟的价格数据
        recent_time = time.time() - 300  # 5分钟 = 300秒
        recent_prices = [p for p in self.price_history if p["timestamp"] >= recent_time]

        if len(recent_prices) < 3:
            return None

        prices = [p["price"] for p in recent_prices]

        # 简单的结构点检测：最近的支撑或阻力位
        # 这里使用最近的局部高点或低点作为结构点
        if len(prices) >= 3:
            mid_idx = len(prices) // 2
            if mid_idx > 0 and mid_idx < len(prices) - 1:
                # 检查是否是局部高点或低点
                if (
                    prices[mid_idx] > prices[mid_idx - 1]
                    and prices[mid_idx] > prices[mid_idx + 1]
                ) or (
                    prices[mid_idx] < prices[mid_idx - 1]
                    and prices[mid_idx] < prices[mid_idx + 1]
                ):
                    return prices[mid_idx]

        # 如果没有明显的结构点，返回最近的最低点作为支撑
        return min(prices)

    async def get_btc_price_binance(self) -> Optional[float]:
        """从Binance获取BTC价格"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            price = float(data["price"])

            with self.data_lock:
                self.btc_price = price
                self.price_update_time = time.time()

                # 更新EMA数据
                self.update_ema_data(price)

            return price

        except Exception as e:
            self.log(f"获取Binance BTC价格失败: {e}", "ERROR")
            return None

    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """获取市场信息"""
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

                return {
                    "id": market_data.get("id"),
                    "question": market_data.get("question"),
                    "outcomes": outcomes,
                    "outcomePrices": outcome_prices,
                    "clobTokenIds": clob_token_ids,
                    "active": market_data.get("active", True),
                    "acceptingOrders": market_data.get("acceptingOrders", True),
                }

            return None

        except Exception as e:
            self.log(f"获取市场信息失败: {e}", "ERROR")
            return None

    def get_both_probabilities(
        self, market_id: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """获取双向概率"""
        try:
            market_info = self.get_market_info(market_id)
            token_ids = market_info.get("clobTokenIds", [])
            yes_token_id = token_ids[0]

            book = self.clob_client.get_order_book(yes_token_id)

            if book and book.bids and book.asks:
                best_bid = float(book.bids[-1].price)
                best_ask = float(book.asks[-1].price)
                yes_prob = (best_bid + best_ask) / 2
                no_prob = 1 - yes_prob

                return yes_prob, no_prob

            elif hasattr(book, "last_trade_price"):
                yes_prob = float(book.last_trade_price)
                return yes_prob, 1 - yes_prob

            return None, None
        except Exception as e:
            self.log(f"获取概率失败: {e}", "ERROR")
            return None, None

    def should_enter_position(
        self, yes_prob: float, no_prob: float
    ) -> Tuple[bool, str, float]:
        """判断是否应该入场 - V2 入场区间检查"""
        # 检查YES方向入场区间
        if self.entry_range["min"] <= yes_prob <= self.entry_range["max"]:
            return True, "yes", yes_prob

        # 检查NO方向入场区间
        if self.entry_range["min"] <= no_prob <= self.entry_range["max"]:
            return True, "no", no_prob

        return False, "none", 0.0

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """计算止损价格 - 基于结构点"""
        structure_point = self.find_structure_point()

        if structure_point:
            if side == "yes":
                # 多头止损：结构点下方
                stop_price = structure_point * (1 - self.stop_buffer)
            else:
                # 空头止损：结构点上方
                stop_price = structure_point * (1 + self.stop_buffer)
        else:
            # 如果没有结构点，使用固定百分比
            if side == "yes":
                stop_price = entry_price * 0.90  # 10%止损
            else:
                stop_price = entry_price * 1.10

        return max(0.01, min(0.99, stop_price))  # 确保在有效范围内

    def calculate_risk_reward(
        self, entry_price: float, stop_loss: float, side: str
    ) -> float:
        """计算风险回报比"""
        if side == "yes":
            risk = entry_price - stop_loss
            reward = self.take_profit_target - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - (1 - self.take_profit_target)

        if risk <= 0:
            return 0

        return reward / risk

    async def start_price_monitoring(self):
        """启动价格监控"""
        self.log("🚀 启动BTC价格监控 V2")

        while self.running and not self.stop_event.is_set():
            try:
                price = await self.get_btc_price_binance()
                if price:
                    # 每分钟显示状态
                    await self.log_status()

                await asyncio.sleep(0.5)

            except Exception as e:
                self.log(f"价格监控错误: {e}", "ERROR")
                await asyncio.sleep(5)

    async def log_status(self):
        """记录状态信息"""
        current_time = datetime.now()
        if not hasattr(self, "last_status_log"):
            self.last_status_log = current_time.replace(second=0, microsecond=0)

        current_minute = current_time.replace(second=0, microsecond=0)

        if current_minute != self.last_status_log:
            self.last_status_log = current_minute

            # 检查各种条件
            trading_hours = self.is_trading_hours()
            session = self.get_current_session()
            volatility_ok, vol_msg = self.check_volatility_filter()
            ema_ok, ema_msg = self.check_ema_trend()
            cooldown_active, cooldown_msg = self.is_in_cooldown()

            status_msg = f"📊 [{current_time.strftime('%H:%M')}] "
            status_msg += f"BTC: ${self.btc_price:,.2f} | "
            status_msg += f"交易时段: {'✅' if trading_hours else '❌'} | "
            status_msg += f"波动率: {'✅' if volatility_ok else '❌'} | "
            status_msg += f"EMA: {'✅' if ema_ok else '❌'} | "
            status_msg += f"风控: {'🚫' if cooldown_active else '✅'}"

            self.log(status_msg)

            if trading_hours and session:
                session_end = session["end"]
                if session_end == int(session_end):
                    end_str = f"{int(session_end)}:00"
                else:
                    end_str = f"{int(session_end)}:30"
                self.log(f"   当前时段: {session['start']}:00-{end_str}")

            # 详细记录不满足条件的原因
            if not trading_hours:
                beijing_time = self.get_beijing_time()
                hour_decimal = beijing_time.hour + beijing_time.minute / 60.0
                self.log(
                    f"   ❌ 非交易时段: 当前时间 {hour_decimal:.2f}, 交易时段: 10:00-12:00 / 15:30-19:00"
                )

            if not volatility_ok:
                self.log(f"   ❌ {vol_msg}")

            if not ema_ok:
                self.log(f"   ❌ {ema_msg}")
                if self.ema_data["fast"] and self.ema_data["slow"]:
                    self.log(
                        f"      EMA9: {self.ema_data['fast']:.2f}, EMA21: {self.ema_data['slow']:.2f}"
                    )

            if cooldown_active:
                self.log(f"   🚫 {cooldown_msg}")

            # 如果所有基础条件都满足，记录更详细的信息
            if trading_hours and volatility_ok and ema_ok and not cooldown_active:
                self.log(f"   ✅ 所有基础条件满足，等待入场信号...")

                # 记录当前价格历史长度
                self.log(f"   📈 价格历史: {len(self.price_history)} 个数据点")

                # 记录突破回踩状态
                if self.btc_price:
                    breakout_ok, breakout_msg = self.detect_breakout_and_pullback(
                        self.btc_price
                    )
                    if not breakout_ok:
                        self.log(f"   ⏳ {breakout_msg}")
                    else:
                        self.log(f"   ✅ {breakout_msg}")

    async def execute_trade(self, market_id: str):
        """执行V2交易策略"""
        self.log(f"🎯 开始执行BTC 15分钟策略 V2")

        # 获取市场信息
        market_info = self.get_market_info(market_id)
        if not market_info:
            self.log("❌ 无法获取市场信息", "ERROR")
            return False

        self.log(f"📊 市场: {market_info.get('question')}")

        # 获取token_ids
        outcomes = market_info.get("outcomes", [])
        token_ids = market_info.get("clobTokenIds", [])

        if len(token_ids) < 2:
            self.log(f"❌ Token ID不足", "ERROR")
            return False

        yes_token_id = token_ids[0]
        no_token_id = token_ids[1]
        yes_outcome = outcomes[0] if len(outcomes) > 0 else "YES"
        no_outcome = outcomes[1] if len(outcomes) > 1 else "NO"

        # 开始监控循环
        while self.running and not self.stop_event.is_set():
            try:
                # 检查是否在交易时段
                if not self.is_trading_hours():
                    # 每5分钟记录一次非交易时段信息
                    current_time = time.time()
                    if (
                        not hasattr(self, "last_trading_hours_log")
                        or current_time - self.last_trading_hours_log > 300
                    ):
                        self.last_trading_hours_log = current_time
                        beijing_time = self.get_beijing_time()
                        hour_decimal = beijing_time.hour + beijing_time.minute / 60.0
                        self.log(
                            f"⏰ 非交易时段: 当前 {hour_decimal:.2f}, 交易时段: 10:00-12:00 / 15:30-19:00"
                        )

                        # 计算距离下一个交易时段的时间
                        next_session_start = None
                        for session in self.trading_sessions:
                            if hour_decimal < session["start"]:
                                next_session_start = session["start"]
                                break

                        if next_session_start is None:
                            # 如果当前时间晚于所有交易时段，计算到明天第一个时段的时间
                            next_session_start = self.trading_sessions[0]["start"] + 24

                        hours_to_wait = next_session_start - hour_decimal
                        self.log(f"   距离下一个交易时段还有 {hours_to_wait:.1f} 小时")

                    await asyncio.sleep(10)
                    continue

                # 检查冷却期
                cooldown_active, cooldown_msg = self.is_in_cooldown()
                if cooldown_active:
                    # 每分钟记录一次冷却期信息
                    current_time = time.time()
                    if (
                        not hasattr(self, "last_cooldown_log")
                        or current_time - self.last_cooldown_log > 60
                    ):
                        self.last_cooldown_log = current_time
                        self.log(f"🚫 {cooldown_msg}")
                    await asyncio.sleep(60)  # 冷却期中每分钟检查一次
                    continue

                # 获取双向概率
                yes_prob, no_prob = self.get_both_probabilities(market_id)
                if not yes_prob or not no_prob:
                    # 每30秒记录一次概率获取失败
                    current_time = time.time()
                    if (
                        not hasattr(self, "last_prob_error_log")
                        or current_time - self.last_prob_error_log > 30
                    ):
                        self.last_prob_error_log = current_time
                        self.log(f"❌ 无法获取市场概率，重试中...")
                    await asyncio.sleep(1)
                    continue

                # 如果还没有持仓
                if not self.position:
                    # 检查所有过滤条件并记录详细原因
                    all_conditions_met = True
                    failed_conditions = []

                    # 检查波动率过滤
                    volatility_ok, vol_msg = self.check_volatility_filter()
                    if not volatility_ok:
                        all_conditions_met = False
                        failed_conditions.append(f"波动率: {vol_msg}")
                        await asyncio.sleep(5)
                        continue

                    # 检查EMA趋势
                    ema_ok, ema_msg = self.check_ema_trend()
                    if not ema_ok:
                        all_conditions_met = False
                        failed_conditions.append(f"EMA趋势: {ema_msg}")
                        await asyncio.sleep(5)
                        continue

                    # 检查突破回踩
                    breakout_ok, breakout_msg = self.detect_breakout_and_pullback(
                        self.btc_price
                    )
                    if not breakout_ok:
                        all_conditions_met = False
                        failed_conditions.append(f"突破回踩: {breakout_msg}")
                        await asyncio.sleep(5)
                        continue

                    # 检查入场区间
                    should_enter, entry_side, entry_prob = self.should_enter_position(
                        yes_prob, no_prob
                    )

                    if not should_enter:
                        all_conditions_met = False
                        failed_conditions.append(
                            f"入场区间: YES={yes_prob:.3f}, NO={no_prob:.3f}, "
                            f"需要在 {self.entry_range['min']:.2f}-{self.entry_range['max']:.2f} 区间内"
                        )

                        # 每30秒记录一次入场区间不满足的详细信息
                        current_time = time.time()
                        if (
                            not hasattr(self, "last_entry_log")
                            or current_time - self.last_entry_log > 30
                        ):
                            self.last_entry_log = current_time
                            self.log(
                                f"⏳ 等待入场区间: YES={yes_prob:.3f}, NO={no_prob:.3f}"
                            )
                            self.log(
                                f"   需要概率在 {self.entry_range['min']:.2f}-{self.entry_range['max']:.2f} 区间内"
                            )

                            # 显示距离入场区间的差距
                            yes_distance_min = abs(yes_prob - self.entry_range["min"])
                            yes_distance_max = abs(yes_prob - self.entry_range["max"])
                            no_distance_min = abs(no_prob - self.entry_range["min"])
                            no_distance_max = abs(no_prob - self.entry_range["max"])

                            self.log(
                                f"   YES距离入场区间: {min(yes_distance_min, yes_distance_max):.3f}"
                            )
                            self.log(
                                f"   NO距离入场区间: {min(no_distance_min, no_distance_max):.3f}"
                            )

                        await asyncio.sleep(5)
                        continue

                    if should_enter:
                        self.log(
                            f"🚀 入场信号: {entry_side.upper()} 概率{entry_prob:.3f}"
                        )
                        self.log(f"   ✅ {vol_msg}")
                        self.log(f"   ✅ {ema_msg}")
                        self.log(f"   ✅ {breakout_msg}")

                        # 选择对应的token_id
                        if entry_side == "yes":
                            target_token_id = yes_token_id
                            target_outcome = yes_outcome
                        else:
                            target_token_id = no_token_id
                            target_outcome = no_outcome

                        # 计算止损价格
                        stop_loss_price = self.calculate_stop_loss(
                            entry_prob, entry_side
                        )

                        # 检查风险回报比
                        risk_reward = self.calculate_risk_reward(
                            entry_prob, stop_loss_price, entry_side
                        )

                        if risk_reward >= self.min_risk_reward:
                            # 执行入场
                            success, actual_amount = (
                                await self.buy_strategy.enter_position(
                                    target_token_id, self.default_amount, entry_prob
                                )
                            )

                            if success:
                                self.position = {
                                    "token_id": target_token_id,
                                    "outcome": target_outcome,
                                    "side": entry_side,
                                    "entry_price": entry_prob,
                                    "entry_time": time.time(),
                                    "amount": actual_amount,
                                    "stop_loss": stop_loss_price,
                                    "risk_reward": risk_reward,
                                    "btc_entry_price": self.btc_price,
                                }

                                self.log(
                                    f"✅ 入场成功: {entry_side.upper()} 概率{entry_prob:.3f}"
                                )
                                self.log(
                                    f"📋 止损: {stop_loss_price:.3f}, RR: {risk_reward:.2f}"
                                )
                            else:
                                self.log(f"❌ 入场失败: 订单执行失败")
                        else:
                            self.log(
                                f"❌ 风险回报比不足: {risk_reward:.2f} < {self.min_risk_reward}"
                            )
                            self.log(
                                f"   入场价: {entry_prob:.3f}, 止损价: {stop_loss_price:.3f}"
                            )
                            self.log(
                                f"   需要RR ≥ {self.min_risk_reward}, 当前RR: {risk_reward:.2f}"
                            )

                else:
                    # 已有持仓，检查出场条件
                    entry_prob = self.position["entry_price"]
                    stop_loss = self.position["stop_loss"]

                    # 获取当前持仓的概率
                    if self.position["side"] == "yes":
                        current_prob = yes_prob
                    else:
                        current_prob = no_prob

                    profit_points = (current_prob - entry_prob) * 100

                    should_exit = False
                    exit_reason = ""

                    # 检查止盈条件
                    if current_prob >= self.take_profit_target:
                        should_exit = True
                        exit_reason = (
                            f"目标止盈: {current_prob:.3f} >= {self.take_profit_target}"
                        )

                    # 检查风险回报比止盈
                    elif profit_points >= (
                        self.position["risk_reward"] * abs(entry_prob - stop_loss) * 100
                    ):
                        should_exit = True
                        exit_reason = f"RR止盈: 盈利{profit_points:.1f}点"

                    # 检查止损条件
                    elif current_prob <= stop_loss:
                        should_exit = True
                        exit_reason = f"止损: {current_prob:.3f} <= {stop_loss:.3f}"

                        # 记录止损
                        self.consecutive_losses += 1
                        self.last_loss_time = time.time()

                    if should_exit:
                        self.log(f"📉 出场信号: {exit_reason}")

                        success = await self.sell_strategy.exit_position(
                            self.position["token_id"], self.position["amount"]
                        )

                        if success:
                            # 计算盈利
                            profit = (current_prob - entry_prob) * self.position[
                                "amount"
                            ]
                            profit_pct = (
                                (current_prob - entry_prob) / entry_prob
                            ) * 100

                            self.log(
                                f"✅ 出场成功: 盈利${profit:.2f} ({profit_pct:.1f}%)"
                            )

                            # 保存交易记录
                            self.save_trade_record(
                                market_id,
                                self.position,
                                current_prob,
                                profit,
                                exit_reason,
                            )

                            # 清除持仓
                            self.position = None

                await asyncio.sleep(1)

            except Exception as e:
                self.log(f"交易循环错误: {e}", "ERROR")
                await asyncio.sleep(5)

        self.log("🛑 策略执行结束")
        return True

    def save_trade_record(
        self,
        market_id: str,
        position: Dict,
        exit_price: float,
        profit: float,
        exit_reason: str,
    ):
        """保存交易记录"""
        try:
            trade_record = {
                "timestamp": datetime.now().isoformat(),
                "market_id": market_id,
                "outcome": position.get("outcome"),
                "side": position.get("side"),
                "entry_time": datetime.fromtimestamp(
                    position.get("entry_time")
                ).isoformat(),
                "exit_time": datetime.now().isoformat(),
                "entry_price": position.get("entry_price"),
                "exit_price": exit_price,
                "stop_loss": position.get("stop_loss"),
                "amount": position.get("amount"),
                "profit": profit,
                "profit_pct": (profit / position.get("amount", 1)) * 100,
                "risk_reward": position.get("risk_reward"),
                "exit_reason": exit_reason,
                "btc_entry_price": position.get("btc_entry_price"),
                "btc_exit_price": self.btc_price,
                "duration_minutes": (time.time() - position.get("entry_time", 0)) / 60,
                "consecutive_losses": self.consecutive_losses,
            }

            # 保存到文件
            trades_dir = "data/btc_trades_v2"
            os.makedirs(trades_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{trades_dir}/btc_trade_v2_{timestamp}.json"

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(trade_record, f, indent=2, ensure_ascii=False)

            self.log(f"📁 交易记录已保存: {filename}")

        except Exception as e:
            self.log(f"保存交易记录失败: {e}", "ERROR")

    async def start_strategy(self, market_id: str, amount: float = 10.0):
        """启动V2策略"""
        self.log("🚀 启动BTC 15分钟策略 V2")
        self.log("=" * 60)
        self.log(f"📊 V2 策略参数:")
        self.log(f"   交易时段: 10:00-12:00 / 15:30-19:00 (北京时间)")
        self.log(f"   波动率过滤: ≥ ${self.min_volatility}")
        self.log(
            f"   EMA趋势: EMA{self.ema_periods['fast']} vs EMA{self.ema_periods['slow']}"
        )
        self.log(
            f"   入场区间: {self.entry_range['min']:.2f} - {self.entry_range['max']:.2f}"
        )
        self.log(f"   突破回踩: {self.pullback_confirmation_time/60:.0f}分钟确认")
        self.log(f"   止盈目标: {self.take_profit_target:.2f}")
        self.log(f"   最小RR: {self.min_risk_reward:.1f}")
        self.log(f"   结构点: 最近{self.structure_lookback}分钟")
        self.log(
            f"   风控: 连续{self.max_consecutive_losses}笔止损 → 冷却{self.cooldown_period}分钟"
        )
        self.log(f"   交易金额: ${amount}")
        self.log("=" * 60)

        self.default_amount = amount
        self.running = True

        # 启动价格监控任务
        price_task = asyncio.create_task(self.start_price_monitoring())

        # 启动交易任务
        trade_task = asyncio.create_task(self.execute_trade(market_id))

        try:
            # 等待任务完成
            await asyncio.gather(price_task, trade_task)
        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
            self.stop()
        except Exception as e:
            self.log(f"策略执行错误: {e}", "ERROR")
            self.stop()

    def stop(self):
        """停止策略"""
        self.log("🛑 停止BTC 15分钟策略 V2")
        self.running = False
        self.stop_event.set()

    def get_status(self) -> Dict:
        """获取策略状态"""
        beijing_time = self.get_beijing_time()
        current_session = self.get_current_session()

        return {
            "running": self.running,
            "beijing_time": beijing_time.strftime("%Y-%m-%d %H:%M:%S"),
            "trading_hours": self.is_trading_hours(),
            "current_session": current_session,
            "btc_price": self.btc_price,
            "baseline_price": self.baseline_price,
            "ema_data": self.ema_data,
            "position": self.position is not None,
            "position_details": self.position,
            "consecutive_losses": self.consecutive_losses,
            "cooldown_active": self.is_in_cooldown()[0],
            "volatility": self.calculate_15min_volatility(),
        }


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(
            "用法: python btc_15min_strategy_v2.py <market_id> [amount] [baseline_price]"
        )
        print("示例: python btc_15min_strategy_v2.py 0x123... 10.0 95000")
        return

    market_id = sys.argv[1]
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    baseline_price = float(sys.argv[3]) if len(sys.argv) > 3 else 95000.0

    # 创建策略实例
    strategy = BTC15MinStrategyV2(baseline_price=baseline_price)

    # 设置信号处理
    def signal_handler(signum, frame):
        print("\n收到停止信号，正在安全退出...")
        strategy.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 启动策略
        await strategy.start_strategy(market_id, amount)
    except Exception as e:
        print(f"策略执行失败: {e}")
    finally:
        strategy.stop()


if __name__ == "__main__":
    asyncio.run(main())
