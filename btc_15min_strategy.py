#!/usr/bin/env python3
"""
Polymarket BTC 15分钟策略
完整实现你描述的策略逻辑：
- 时段：10:00 AM – 07:00 PM (北京时间)
- 频次：每个15分钟区间只下1单
- 入场过滤：时间窗口、价格波动阈值(±30刀)
- 交易执行：0.75入场、0.90止盈、0.55止损
- 特殊止盈：0.85+连续30秒涨幅<3刀
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


class BTC15MinStrategy:
    """BTC 15分钟策略"""

    def __init__(self, use_testnet: bool = False, baseline_price: float = 95000.0):
        self.clob_wrapper = PolymarketCLOBClient(use_testnet=use_testnet)
        self.clob_client = self.clob_wrapper.get_client()
        self.order_manager = OrderManager(use_testnet=use_testnet)
        self.gamma_api_base = "https://gamma-api.polymarket.com"

        # 设置基准价格
        self.baseline_price = baseline_price

        # 策略参数
        self.trading_hours = {
            "start": 10,  # 10:00 AM 北京时间
            "end": 15,  # 07:00 PM 北京时间
        }

        # 入场过滤条件
        self.min_time_after_start = 5  # 区间开始n分钟后才能下单
        self.min_time_before_end = 1  # 结算前1分钟禁止下单
        self.price_threshold = 30  # ±30刀价格波动阈值

        # 交易执行参数
        self.entry_probability = 0.60  # 60%概率入场 (降低门槛)
        self.take_profit = 0.90  # 90%止盈
        self.stop_loss = 0.55  # 55%止损

        # 特殊止盈参数
        self.special_tp_threshold = 0.85  # 85%触发特殊止盈检测
        self.stagnant_time = 30  # 30秒横盘检测
        self.stagnant_price_change = 3  # 3刀涨幅阈值

        # 数据源优化参数
        self.buffer_threshold = 30  # 缓冲阈值：$32-35
        self.momentum_check_time = 15  # 动量确认时间：15秒

        # 状态跟踪
        self.current_interval = None
        self.interval_start_price = None
        self.position = None
        self.price_history = []
        self.running = False
        self.stop_event = Event()
        self.data_lock = Lock()
        self.default_amount = 5.0  # 默认交易金额
        self.last_minute_log = None  # 上次分钟日志时间
        self.traded_intervals = set()  # 记录已交易的15分钟区间

        # BTC价格监控
        self.btc_price = None
        self.price_update_time = None
        self.ws_connection = None

        # 北京时区
        self.beijing_tz = pytz.timezone("Asia/Shanghai")

        # 日志设置
        self.setup_logging()

        # 记录基准价格
        self.log(f"📋 基准价格设置: ${self.baseline_price:,.2f}")

    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/btc_strategy_logs"
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"btc_15min_{timestamp}.log")

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
        """检查是否在交易时段"""
        beijing_time = self.get_beijing_time()
        hour = beijing_time.hour
        return self.trading_hours["start"] <= hour < self.trading_hours["end"]

    def get_current_interval(self) -> Tuple[datetime, datetime]:
        """获取当前15分钟区间"""
        beijing_time = self.get_beijing_time()

        # 计算当前15分钟区间的开始时间
        minute = beijing_time.minute
        interval_start_minute = (minute // 15) * 15

        interval_start = beijing_time.replace(
            minute=interval_start_minute, second=0, microsecond=0
        )
        interval_end = interval_start + timedelta(minutes=15)

        return interval_start, interval_end

    def is_valid_entry_time(self) -> Tuple[bool, str]:
        """检查是否是有效的入场时间 - 只限制买入，卖出无限制"""
        beijing_time = self.get_beijing_time()
        interval_start, interval_end = self.get_current_interval()

        # 检查是否在交易时段
        if not self.is_trading_hours():
            return (
                False,
                f"不在交易时段 ({self.trading_hours['start']}:00-{self.trading_hours['end']}:00)",
            )

        # 检查当前15分钟区间是否已经交易过
        interval_key = interval_start.strftime("%Y%m%d_%H%M")
        if interval_key in self.traded_intervals:
            return (
                False,
                f"当前15分钟区间 ({interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}) 已交易过",
            )

        # 检查是否在区间开始5分钟后
        min_entry_time = interval_start + timedelta(minutes=self.min_time_after_start)
        if beijing_time < min_entry_time:
            remaining = (min_entry_time - beijing_time).total_seconds()
            return (
                False,
                f"距离可入场时间还有 {remaining:.0f} 秒 (需等待{self.min_time_after_start}分钟)",
            )

        # 检查是否在结算前1分钟内
        max_entry_time = interval_end - timedelta(minutes=self.min_time_before_end)
        if beijing_time > max_entry_time:
            return False, "距离结算时间太近，禁止入场"

        return True, "时间窗口有效"

    def check_price_movement(self, current_price: float) -> Tuple[bool, str, str]:
        """检查价格波动是否满足入场条件"""
        if not self.baseline_price:
            return False, "缺少基准价格", "none"

        price_diff = current_price - self.baseline_price
        abs_diff = abs(price_diff)

        # 使用缓冲阈值来抵消数据延迟
        effective_threshold = self.buffer_threshold

        if abs_diff >= effective_threshold:
            direction = "up" if price_diff > 0 else "down"
            return (
                True,
                f"价格波动 ${abs_diff:.2f} >= ${effective_threshold} (基准${self.baseline_price:,.0f})",
                direction,
            )
        else:
            return (
                False,
                f"价格波动 ${abs_diff:.2f} < ${effective_threshold} (基准${self.baseline_price:,.0f})",
                "none",
            )

    def check_momentum_confirmation(self) -> bool:
        """检查动量确认（VAP逻辑）"""
        if len(self.price_history) < 3:
            return False

        # 检查最近15秒的价格变化频率
        recent_time = time.time() - self.momentum_check_time
        recent_prices = [p for p in self.price_history if p["timestamp"] >= recent_time]

        if len(recent_prices) < 2:
            return False

        # 检查价格变化的密集程度
        price_changes = []
        for i in range(1, len(recent_prices)):
            change = abs(recent_prices[i]["price"] - recent_prices[i - 1]["price"])
            price_changes.append(change)

        # 如果平均变化幅度较大，说明有动量
        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
        return avg_change > 5  # 平均变化超过5刀认为有动量

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

                # 添加到价格历史
                self.price_history.append(
                    {"timestamp": time.time(), "price": price, "source": "binance"}
                )

                # 保持历史记录在合理范围内
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-50:]

            # 每分钟打印价格差额
            self.log_minute_price_difference(price)

            return price

        except Exception as e:
            self.log(f"获取Binance BTC价格失败: {e}", "ERROR")
            return None

    def log_minute_price_difference(self, current_price: float):
        """每分钟打印价格差额"""
        current_time = datetime.now()
        current_minute = current_time.replace(second=0, microsecond=0)

        # 检查是否是新的分钟
        if self.last_minute_log != current_minute:
            self.last_minute_log = current_minute

            if self.baseline_price:
                price_diff = current_price - self.baseline_price
                abs_diff = abs(price_diff)
                direction = "↗️" if price_diff > 0 else "↘️" if price_diff < 0 else "➡️"

                # 检查是否满足入场阈值
                threshold_status = (
                    "✅ 满足" if abs_diff >= self.buffer_threshold else "❌ 不满足"
                )

                self.log(
                    f"📊 [{current_time.strftime('%H:%M')}] BTC: ${current_price:,.2f} | "
                    f"基准: ${self.baseline_price:,.2f} | "
                    f"差额: {direction}${abs_diff:.2f} | "
                    f"阈值${self.buffer_threshold}: {threshold_status}"
                )
            else:
                self.log(
                    f"📊 [{current_time.strftime('%H:%M')}] BTC: ${current_price:,.2f} | 基准价格未设置"
                )

    async def start_price_monitoring(self):
        """启动价格监控"""
        self.log("🚀 启动BTC价格监控")

        while self.running and not self.stop_event.is_set():
            try:
                price = await self.get_btc_price_binance()
                if price:
                    # 检查是否是新的15分钟区间
                    await self.check_new_interval()

                await asyncio.sleep(1)  # 1秒更新一次价格

            except Exception as e:
                self.log(f"价格监控错误: {e}", "ERROR")
                await asyncio.sleep(5)

    async def check_new_interval(self):
        """检查是否进入新的15分钟区间"""
        interval_start, interval_end = self.get_current_interval()

        if self.current_interval != interval_start:
            self.log(
                f"📅 新的15分钟区间: {interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}"
            )

            # 更新区间信息
            self.current_interval = interval_start

            # 记录区间开始价格（用于记录，但不用于计算）
            if self.btc_price:
                self.interval_start_price = self.btc_price
                self.log(f"📊 区间开始价格: ${self.interval_start_price:,.2f}")
                self.log(f"📊 基准价格: ${self.baseline_price:,.2f}")

                # 保存区间数据
                self.save_interval_data(interval_start, self.interval_start_price)

            # 重置持仓状态（每个区间只下一单）
            if self.position and self.position.get("interval") != interval_start:
                self.log("⚠️ 新区间开始，重置持仓状态")
                self.position = None

            # 显示已交易区间统计
            interval_key = interval_start.strftime("%Y%m%d_%H%M")
            if interval_key not in self.traded_intervals:
                self.log(
                    f"🆕 新区间可交易: {interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}"
                )
            else:
                self.log(
                    f"🚫 区间已交易过: {interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}"
                )

            self.log(f"📈 今日已交易区间数: {len(self.traded_intervals)}")

    def save_interval_data(self, interval_start: datetime, start_price: float):
        """保存区间数据"""
        try:
            data_dir = "data/btc_intervals"
            os.makedirs(data_dir, exist_ok=True)

            filename = os.path.join(
                data_dir, f"intervals_{datetime.now().strftime('%Y%m%d')}.csv"
            )

            # 检查文件是否存在，不存在则创建头部
            file_exists = os.path.exists(filename)

            with open(filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if not file_exists:
                    writer.writerow(["interval_start", "start_price", "beijing_time"])

                writer.writerow(
                    [
                        interval_start.isoformat(),
                        start_price,
                        interval_start.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )

        except Exception as e:
            self.log(f"保存区间数据失败: {e}", "ERROR")

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
        try:
            # 1. 确保获取了正确的 Token ID
            market_info = self.get_market_info(market_id)
            token_ids = market_info.get("clobTokenIds", [])
            yes_token_id = token_ids[0]

            # 2. 获取 YES 的订单簿
            book = self.clob_client.get_order_book(yes_token_id)

            # 3. 使用买一和卖一的平均值，这才是市场公认的“当前概率”
            if book and book.bids and book.asks:
                best_bid = float(book.bids[-1].price)
                best_ask = float(book.asks[-1].price)
                yes_prob = (best_bid + best_ask) / 2
                no_prob = 1 - yes_prob

                self.log(f"📊 订单簿: YES概率={yes_prob:.1%}")
                return yes_prob, no_prob

            # 如果订单簿只有单边，再退而求其次用 last_trade_price
            elif hasattr(book, "last_trade_price"):
                yes_prob = float(book.last_trade_price)
                return yes_prob, 1 - yes_prob

            return None, None
        except Exception as e:
            self.log(f"获取概率失败: {e}", "ERROR")
            return None, None

    def should_enter_position(
        self, yes_prob_pct: float, no_prob_pct: float, price_direction: str
    ) -> Tuple[bool, str, float]:
        """判断是否应该入场 - 双向检测"""
        # 转换为小数形式进行比较
        yes_prob = yes_prob_pct / 100.0
        no_prob = no_prob_pct / 100.0
        entry_threshold = self.entry_probability  # 0.75

        # 检查YES方向
        if yes_prob >= entry_threshold and price_direction == "up":
            return True, "yes", yes_prob_pct

        # 检查NO方向
        if no_prob >= entry_threshold and price_direction == "down":
            return True, "no", no_prob_pct

        # 也可以在概率极高时忽略价格方向
        if yes_prob >= 0.80:  # 80%以上概率可以忽略价格方向
            return True, "yes", yes_prob_pct
        if no_prob >= 0.80:
            return True, "no", no_prob_pct

        return False, "none", 0.0

    def check_stagnant_condition(self) -> Tuple[bool, str]:
        """检查30秒衰减条件"""
        if len(self.price_history) < 2:
            return False, "价格历史不足"

        # 检查最近30秒的价格变化
        recent_time = time.time() - self.stagnant_time
        recent_prices = [p for p in self.price_history if p["timestamp"] >= recent_time]

        if len(recent_prices) < 2:
            return False, "最近30秒数据不足"

        # 计算最大价格变化
        prices = [p["price"] for p in recent_prices]
        max_change = max(prices) - min(prices)

        if max_change < self.stagnant_price_change:
            return (
                True,
                f"30秒内最大变化 ${max_change:.2f} < ${self.stagnant_price_change}",
            )

        return (
            False,
            f"30秒内最大变化 ${max_change:.2f} >= ${self.stagnant_price_change}",
        )

    async def execute_trade(self, market_id: str):
        """执行双向交易策略"""
        self.log(f"🎯 开始执行BTC 15分钟双向策略")
        self.log(f"市场ID: {market_id}")

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

        self.log(f"🎲 YES Token: {yes_token_id} ({yes_outcome})")
        self.log(f"🎲 NO Token: {no_token_id} ({no_outcome})")

        # 开始监控循环
        while self.running and not self.stop_event.is_set():
            try:
                # 检查是否在交易时段
                if not self.is_trading_hours():
                    self.log("⏰ 不在交易时段，等待...")
                    await asyncio.sleep(10)
                    continue

                # 获取双向概率 - 每次都获取最新数据
                yes_prob, no_prob = self.get_both_probabilities(market_id)
                if not yes_prob or not no_prob:
                    await asyncio.sleep(1)
                    continue

                yes_prob_pct = yes_prob * 100
                no_prob_pct = no_prob * 100

                # 如果还没有持仓
                if not self.position:
                    # 检查入场条件 - 只限制买入时间
                    time_valid, time_msg = self.is_valid_entry_time()
                    if not time_valid:
                        self.log(f"⏳ 买入限制: {time_msg}")
                        await asyncio.sleep(1)
                        continue

                    # 检查价格波动
                    if not self.btc_price or not self.baseline_price:
                        self.log("� 等待价格数据...n")
                        await asyncio.sleep(1)
                        continue

                    price_valid, price_msg, direction = self.check_price_movement(
                        self.btc_price
                    )
                    if not price_valid:
                        self.log(f"📈 {price_msg}")
                        await asyncio.sleep(1)
                        continue

                    # 检查双向入场信号
                    should_enter, entry_side, entry_prob = self.should_enter_position(
                        yes_prob_pct, no_prob_pct, direction
                    )

                    if should_enter:
                        self.log(
                            f"🚀 入场信号: {entry_side.upper()} 概率{entry_prob:.1f}%, 方向{direction}, {price_msg}"
                        )

                        # 选择对应的token_id和金额
                        if entry_side == "yes":
                            target_token_id = yes_token_id
                            target_outcome = yes_outcome
                            target_prob = yes_prob
                        else:
                            target_token_id = no_token_id
                            target_outcome = no_outcome
                            target_prob = no_prob

                        # 执行入场
                        success, actual_amount = await self.enter_position(
                            target_token_id, self.default_amount, target_prob
                        )
                        if success:
                            interval_start, _ = self.get_current_interval()

                            # 记录已交易的区间
                            interval_key = interval_start.strftime("%Y%m%d_%H%M")
                            self.traded_intervals.add(interval_key)

                            self.position = {
                                "token_id": target_token_id,
                                "outcome": target_outcome,
                                "side": entry_side,
                                "entry_price": target_prob,
                                "entry_time": time.time(),
                                "amount": actual_amount,  # 使用实际购买的金额
                                "original_amount": self.default_amount,
                                "interval": interval_start,
                                "btc_entry_price": self.btc_price,
                                "direction": direction,
                            }
                            self.log(
                                f"✅ 入场成功: {entry_side.upper()} 概率{entry_prob:.1f}%, BTC${self.btc_price:,.2f}"
                            )
                            self.log(f"📋 实际购买: ${actual_amount}")
                            self.log(
                                f"🔒 区间 {interval_start.strftime('%H:%M')}-{(interval_start + timedelta(minutes=15)).strftime('%H:%M')} 已锁定，15分钟内不再交易"
                            )
                    else:
                        self.log(
                            f"⏸️ 等待入场: YES{yes_prob_pct:.1f}% NO{no_prob_pct:.1f}%, 方向{direction}"
                        )

                else:
                    # 已有持仓，检查出场条件 - 卖出无时间限制
                    entry_prob = self.position["entry_price"]

                    # 获取当前持仓的概率
                    if self.position["side"] == "yes":
                        current_prob = yes_prob
                        current_prob_pct = yes_prob_pct
                    else:
                        current_prob = no_prob
                        current_prob_pct = no_prob_pct

                    profit_points = (current_prob - entry_prob) * 100

                    self.log(
                        f"📊 持仓监控: {self.position['side'].upper()} 概率{current_prob_pct:.1f}%, 盈利{profit_points:.1f}点"
                    )

                    should_exit = False
                    exit_reason = ""

                    # 检查止盈条件
                    if current_prob_pct >= self.take_profit * 100:
                        should_exit = True
                        exit_reason = f"概率止盈: {current_prob_pct:.1f}% >= {self.take_profit*100}%"

                    # 检查止损条件
                    elif current_prob_pct <= self.stop_loss * 100:
                        should_exit = True
                        exit_reason = f"概率止损: {current_prob_pct:.1f}% <= {self.stop_loss*100}%"

                    # 检查特殊止盈条件
                    elif current_prob_pct >= self.special_tp_threshold * 100:
                        stagnant, stagnant_msg = self.check_stagnant_condition()
                        if stagnant:
                            should_exit = True
                            exit_reason = f"特殊止盈: {current_prob_pct:.1f}% >= {self.special_tp_threshold*100}%, {stagnant_msg}"

                    if should_exit:
                        self.log(f"📉 出场信号: {exit_reason}")

                        success = await self.exit_position(
                            self.position["token_id"], self.position["amount"]
                        )
                        if success:
                            # 计算盈利基于概率变化
                            entry_amount = self.position["amount"]
                            estimated_exit_value = entry_amount * (
                                current_prob / entry_prob
                            )
                            profit = estimated_exit_value - entry_amount
                            profit_pct = (profit / entry_amount) * 100

                            self.log(
                                f"✅ 出场成功: 预估盈利${profit:.2f} ({profit_pct:.1f}%)"
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

                await asyncio.sleep(1)  # 5秒检查一次

            except Exception as e:
                self.log(f"交易循环错误: {e}", "ERROR")
                await asyncio.sleep(5)

        self.log("🛑 策略执行结束")
        return True

    def format_amount_for_api(self, amount: int, is_taker: bool = True) -> float:
        """
        格式化金额以符合API精度要求（关键修复）
        :param amount: 传入的整数金额
        :param is_taker: 是否是taker订单（市场订单默认是taker）
        :return: 符合精度要求的浮点数金额
        """
        # 转换为Decimal以精确处理小数
        decimal_amount = Decimal(str(amount))

        # 根据订单类型设置小数位数
        decimals = self.taker_decimals if is_taker else self.maker_decimals

        # 格式化（截断而非四舍五入，避免超出精度）
        formatted = decimal_amount.quantize(
            Decimal("1." + "0" * decimals), rounding=ROUND_DOWN
        )

        # 转换回浮点数
        return float(formatted)

    async def enter_position(
        self, token_id: str, price: float, current_prob: float
    ) -> Tuple[bool, float]:
        """入场操作"""
        try:
            self.log(f"🎯 准备入场: token_id={token_id}, 金额=${price}")

            # 直接使用命令行参数中的金额，不进行任何格式化
            shares_rounded = price  # 直接使用传入的价格值

            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=shares_rounded,
                side="BUY",
            )
            self.log(f"💰 交易金额: {shares_rounded} (直接使用命令行参数)")

            signed_order = self.clob_client.create_market_order(order_args)
            result = self.clob_client.post_order(signed_order, orderType=OrderType.FOK)

            if result and result.get("orderID"):
                self.log(f"✅ 入场订单提交成功: {result}")
                self.log(f"📋 订单详情: {shares_rounded} @ 概率{current_prob:.3f}")
                return True, shares_rounded  # 返回实际购买的金额
            else:
                self.log(f"❌ 入场订单失败: {result}", "ERROR")
                return False, 0.0

        except Exception as e:
            self.log(f"❌ 入场操作失败: {e}", "ERROR")
            return False, 0.0

    async def exit_position(self, token_id: str, amount: float) -> bool:
        """出场操作 - 持续重试直到成功"""
        max_retries = 10  # 最大重试次数，防止无限循环
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 获取实际持仓
                actual_balance = self.clob_client.get_balance_allowance(
                    params=BalanceAllowanceParams(
                        asset_type=AssetType.CONDITIONAL,
                        token_id=token_id,
                    )
                )

                # 确保余额是数字类型
                balance_value = actual_balance.get("balance", "0")
                if isinstance(balance_value, str):
                    balance_value = float(balance_value)
                balance_value = balance_value/ 1000000
                # 如果没有持仓，直接返回成功
                if balance_value <= 0:
                    self.log("✅ 没有持仓，出场完成")
                    return True

                retry_count += 1
                self.log(
                    f"🎯 出场尝试 #{retry_count}: token_id={token_id}, 持仓={balance_value}份"
                )

                # 创建市场卖出订单
                order_args = MarketOrderArgs(
                    token_id=token_id,
                    amount=balance_value,
                    side="SELL",
                )
                signed_order = self.clob_client.create_market_order(order_args)
                result = self.clob_client.post_order(
                    signed_order, orderType=OrderType.FOK
                )

                if result and result.get("orderID"):
                    self.log(
                        f"✅ 出场成功 (第{retry_count}次尝试): {result.get('orderID')}"
                    )
                    self.log(f"📋 成功卖出: {balance_value}份")
                    return True
                else:
                    error_msg = str(result) if result else "无响应"
                    self.log(f"⚠️ 出场失败 (第{retry_count}次): {error_msg}")

                    # 等待2秒后重试
                    await asyncio.sleep(1)

            except Exception as e:
                error_msg = str(e)
                self.log(f"⚠️ 出场异常 (第{retry_count}次): {error_msg}")

                # 等待2秒后重试
                await asyncio.sleep(1)

        # 如果达到最大重试次数仍未成功
        self.log(f"❌ 出场失败: 已重试{max_retries}次，放弃操作")
        return False

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
                "interval": (
                    position.get("interval").isoformat()
                    if position.get("interval")
                    else None
                ),
                "entry_time": datetime.fromtimestamp(
                    position.get("entry_time")
                ).isoformat(),
                "exit_time": datetime.now().isoformat(),
                "entry_price": position.get("entry_price"),
                "exit_price": exit_price,
                "shares": position.get("amount"),  # 现在amount就是交易金额
                "amount": position.get("original_amount", position.get("amount")),
                "profit": profit,
                "profit_pct": (profit / position.get("amount", 1)) * 100,
                "exit_reason": exit_reason,
                "btc_entry_price": position.get("btc_entry_price"),
                "btc_exit_price": self.btc_price,
                "direction": position.get("direction"),
                "duration_minutes": (time.time() - position.get("entry_time", 0)) / 60,
            }

            # 保存到文件
            trades_dir = "data/btc_trades"
            os.makedirs(trades_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{trades_dir}/btc_trade_{timestamp}.json"

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(trade_record, f, indent=2, ensure_ascii=False)

            self.log(f"📁 交易记录已保存: {filename}")

        except Exception as e:
            self.log(f"保存交易记录失败: {e}", "ERROR")

    async def start_strategy(self, market_id: str, amount: float = 10.0):
        """启动双向策略"""
        self.log("🚀 启动BTC 15分钟双向策略")
        self.log("=" * 60)
        self.log(f"📊 策略参数:")
        self.log(
            f"   交易时段: {self.trading_hours['start']}:00-{self.trading_hours['end']}:00 (北京时间)"
        )
        self.log(f"   基准价格: ${self.baseline_price:,.2f} (入参设置)")
        self.log(
            f"   价格阈值: ±${self.price_threshold} (缓冲: ${self.buffer_threshold})"
        )
        self.log(
            f"   买入窗口: 区间开始{self.min_time_after_start}分钟后 至 结束前{self.min_time_before_end}分钟"
        )
        self.log(f"   卖出窗口: 无限制 (任何时间可卖出)")
        self.log(f"   交易频次: 每15分钟区间最多1次交易 (严格限制)")
        self.log(f"   入场概率: {self.entry_probability*100}% (双向检测)")
        self.log(f"   止盈概率: {self.take_profit*100}%")
        self.log(f"   止损概率: {self.stop_loss*100}%")
        self.log(
            f"   特殊止盈: {self.special_tp_threshold*100}% + {self.stagnant_time}秒横盘"
        )
        self.log(f"   交易金额: ${amount}")
        self.log(f"   价格监控: 每分钟显示与基准价格差额")
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
        self.log("🛑 停止BTC 15分钟策略")
        self.running = False
        self.stop_event.set()

    def get_status(self) -> Dict:
        """获取策略状态"""
        beijing_time = self.get_beijing_time()
        interval_start, interval_end = self.get_current_interval()
        interval_key = interval_start.strftime("%Y%m%d_%H%M")

        return {
            "running": self.running,
            "beijing_time": beijing_time.strftime("%Y-%m-%d %H:%M:%S"),
            "trading_hours": self.is_trading_hours(),
            "current_interval": {
                "start": interval_start.strftime("%H:%M"),
                "end": interval_end.strftime("%H:%M"),
                "traded": interval_key in self.traded_intervals,
            },
            "btc_price": self.btc_price,
            "baseline_price": self.baseline_price,
            "interval_start_price": self.interval_start_price,
            "position": self.position is not None,
            "position_details": self.position,
            "traded_intervals_today": len(self.traded_intervals),
            "traded_intervals_list": sorted(list(self.traded_intervals)),
        }


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if "strategy" in globals():
        strategy.stop()
    sys.exit(0)


async def main():
    """主函数"""
    print("🤖 Polymarket BTC 15分钟双向策略")
    print("=" * 60)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 获取输入参数
        if len(sys.argv) >= 2:
            market_id = sys.argv[1]
            amount = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
            baseline_price = float(sys.argv[3]) if len(sys.argv) > 3 else 95000.0
        else:
            market_id = input("📝 请输入BTC 15分钟市场ID: ").strip()
            if not market_id:
                print("❌ 市场ID不能为空")
                return

            try:
                amount = float(
                    input("💰 请输入交易金额 (USDC) [默认10]: ").strip() or "10"
                )
                if amount <= 0:
                    print("❌ 金额必须大于0")
                    return
            except ValueError:
                print("❌ 金额格式错误")
                return

            try:
                baseline_input = input("📊 请输入基准价格 (USDC) [默认95000]: ").strip()
                baseline_price = float(baseline_input) if baseline_input else 95000.0
                if baseline_price <= 0:
                    print("❌ 基准价格必须大于0")
                    return
            except ValueError:
                print("❌ 基准价格格式错误")
                return

        # 创建策略实例
        global strategy
        strategy = BTC15MinStrategy(use_testnet=False, baseline_price=baseline_price)

        # 验证市场
        market_info = strategy.get_market_info(market_id)
        if not market_info:
            print(f"❌ 未找到市场: {market_id}")
            return

        print(f"\n📊 市场信息:")
        print(f"   问题: {market_info.get('question')}")
        print(f"   模式: 双向交易 (YES/NO 概率>75%均可入场)")
        print(f"   金额: ${amount}")
        print(f"   基准价格: ${baseline_price:,.2f}")

        # 显示当前状态
        status = strategy.get_status()
        print(f"\n⏰ 当前状态:")
        print(f"   北京时间: {status['beijing_time']}")
        print(f"   交易时段: {'✅' if status['trading_hours'] else '❌'}")
        print(
            f"   当前区间: {status['current_interval']['start']}-{status['current_interval']['end']}"
        )
        print(
            f"   区间状态: {'🚫 已交易' if status['current_interval']['traded'] else '🆕 可交易'}"
        )
        print(f"   今日已交易区间: {status['traded_intervals_today']} 个")

        if len(sys.argv) < 2:
            confirm = input(f"\n❓ 确认启动BTC 15分钟双向策略? (y/n): ").strip().lower()
            if confirm not in ["y", "yes"]:
                print("❌ 已取消")
                return

        # 启动策略
        await strategy.start_strategy(market_id, amount)

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        if "strategy" in globals():
            strategy.stop()


if __name__ == "__main__":
    asyncio.run(main())
