#!/usr/bin/env python3
"""
BTC 智能自动交易器 - 集成WebSocket实时价格监控
启动后判断跟上一个15分钟市场的间隔：
- 如果间隔小于5分钟，则直接获取并参与上一个15分钟的市场
- 如果间隔超过5分钟，则等待并参与下一个市场

新特性：
- 集成BTCWebSocketMonitorV2Fixed实时价格同步
- BTCHighOddsSniperStrategy使用共享的WebSocket价格数据
- 异步架构支持实时交易决策
"""

import time
import datetime
import pytz
import requests
import json
import subprocess
import sys
import os
import signal
import asyncio
from typing import Optional, List, Dict, Tuple

# 导入WebSocket监控和策略
from btc_websocket_price_monitor_v2_fixed import BTCWebSocketMonitorV2Fixed
from btc_15min_strategy_v2 import BTCHighOddsSniperStrategy
from websocket_price_provider import WebSocketPriceProvider


class BTCSmartAutoTrader:
    """BTC智能自动交易器 - 集成WebSocket实时价格监控"""

    def __init__(self, trade_amount: float = 5.0, strategy_version: str = "v1"):
        # 确保交易金额符合Polymarket最小要求
        if trade_amount < 1.0:
            print(f"⚠️ 交易金额 ${trade_amount} 低于最小要求 $1.0，自动调整为 $1.0")
            trade_amount = 1.0
            
        self.trade_amount = trade_amount
        self.strategy_version = strategy_version
        self.running = True
        self.beijing_tz = pytz.timezone("Asia/Shanghai")
        self.et_winter_tz = pytz.FixedOffset(-5 * 60)  # UTC-5，美东冬季时间

        # 时间判断阈值（分钟）
        self.time_threshold = 5  # 5分钟阈值

        # WebSocket价格监控
        self.price_provider = None
        self.current_btc_price = 0.0
        self.price_update_time = 0

        # 当前运行的策略实例
        self.current_strategy = None
        self.strategy_task = None
        
        # 周期跟踪 - 防止重复启动
        self.current_cycle_timestamp = None
        self.last_cycle_check = 0

        # 根据策略版本确定策略类型
        if strategy_version.lower() == "sniper":
            self.strategy_type = "sniper"
        elif strategy_version.lower() == "v2":
            self.strategy_type = "v2"
        else:
            self.strategy_type = "v1"

        # 日志设置
        self.setup_logging()

        self.log("🤖 BTC智能自动交易器初始化完成")
        self.log(f"💰 交易金额: ${trade_amount}")
        self.log(f"📋 策略版本: {strategy_version}")
        self.log(f"⏰ 时间阈值: {self.time_threshold}分钟")

        # 显示策略特性
        if strategy_version.lower() == "sniper":
            self.log("🎯 Sniper策略特性:")
            self.log("   - 高赔率狙击者策略")
            self.log("   - 核心敏感度: 50 USDT (激进)")
            self.log("   - 动态系数: 1.8 (高敏感)")
            self.log("   - WebSocket实时价格 (<500ms)")
            self.log("   - 概率滞后判定 (>12%)")
            self.log("   - 动态波动率调整")
        elif strategy_version.lower() == "v2":
            self.log("🔧 V2策略特性:")
            self.log("   - 保守型高赔率策略")
            self.log("   - 核心敏感度: 40 USDT (保守)")
            self.log("   - 动态系数: 1.5 (低敏感)")
            self.log("   - WebSocket实时价格 (<500ms)")
            self.log("   - 概率滞后判定 (>12%)")
            self.log("   - 动态波动率调整")
        else:
            self.log("🔧 V1策略特性:")
            self.log("   - 传统15分钟区间策略")
            self.log("   - 双时段交易 (10:00-12:00 / 15:30-19:00)")
            self.log("   - EMA趋势过滤 (EMA9 vs EMA21)")
            self.log("   - 波动率阈值过滤")
            self.log("   - 突破回踩确认机制")

    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/auto_trader_logs"
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_suffix = (
            f"_{self.strategy_version}" if hasattr(self, "strategy_version") else ""
        )
        self.log_file = os.path.join(
            self.log_dir, f"smart_auto_trader{strategy_suffix}_{timestamp}.log"
        )

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"写入日志失败: {e}")

    def get_beijing_time(self) -> datetime.datetime:
        """获取北京时间"""
        return datetime.datetime.now(self.beijing_tz)

    def get_15min_timestamps(
        self,
    ) -> Tuple[int, int, datetime.datetime, datetime.datetime]:
        """
        获取上一个和下一个15分钟整点的时间戳
        返回: (上一个时间戳, 下一个时间戳, 上一个北京时间, 下一个北京时间)
        """
        now_beijing = self.get_beijing_time()

        # 计算当前15分钟区间的开始时间
        current_minute = now_beijing.minute
        interval_start_minute = (current_minute // 15) * 15

        # 当前15分钟区间的开始时间（上一个整点）
        prev_15min_beijing = now_beijing.replace(
            minute=interval_start_minute, second=0, microsecond=0
        )

        # 下一个15分钟整点
        next_15min_beijing = prev_15min_beijing + datetime.timedelta(minutes=15)

        # 转换为美东时间并获取时间戳
        prev_15min_et = prev_15min_beijing.astimezone(self.et_winter_tz)
        next_15min_et = next_15min_beijing.astimezone(self.et_winter_tz)

        prev_timestamp = int(prev_15min_et.timestamp())
        next_timestamp = int(next_15min_et.timestamp())

        return prev_timestamp, next_timestamp, prev_15min_beijing, next_15min_beijing

    def get_time_to_interval_start(
        self, target_beijing_time: datetime.datetime
    ) -> float:
        """计算到目标时间的分钟数"""
        now_beijing = self.get_beijing_time()
        time_diff = target_beijing_time - now_beijing
        return time_diff.total_seconds() / 60

    def get_btc_price(self) -> Optional[float]:
        """获取当前BTC价格 - 优先使用WebSocket数据"""
        # 如果有WebSocket价格数据且是新鲜的，优先使用
        if (
            self.price_provider
            and self.price_provider.is_price_fresh(max_age_seconds=10)
            and self.price_provider.get_current_price() > 0
        ):

            price = self.price_provider.get_current_price()
            self.log(f"📊 获取BTC价格(WebSocket): ${price:,.2f}")
            return price

        # 否则使用REST API获取
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = float(data["price"])

            self.log(f"📊 获取BTC价格(REST API): ${price:,.2f}")
            return price

        except Exception as e:
            self.log(f"❌ 获取BTC价格失败: {e}", "ERROR")
            return None

    async def setup_websocket_price_monitor(self):
        """设置WebSocket价格监控"""
        try:
            self.log("🔗 设置WebSocket价格监控...")

            # 创建价格提供器
            self.price_provider = WebSocketPriceProvider("btcusdt")

            # 添加价格更新回调
            self.price_provider.add_price_callback(self.on_price_update)

            self.log("✅ WebSocket价格监控设置完成")

        except Exception as e:
            self.log(f"❌ 设置WebSocket价格监控失败: {e}", "ERROR")

    async def on_price_update(self, price: float, timestamp: float):
        """价格更新回调"""
        self.current_btc_price = price
        self.price_update_time = timestamp

        # 每30秒记录一次价格更新
        if (
            not hasattr(self, "_last_price_log")
            or timestamp - self._last_price_log >= 30
        ):
            self.log(f"💹 价格更新: ${price:,.2f}")
            self._last_price_log = timestamp

    async def start_websocket_monitor(self):
        """启动WebSocket价格监控"""
        if not self.price_provider:
            await self.setup_websocket_price_monitor()

        try:
            self.log("🚀 启动WebSocket价格监控...")
            await self.price_provider.start()
        except Exception as e:
            self.log(f"❌ WebSocket价格监控启动失败: {e}", "ERROR")

    def get_market_by_timestamp(self, timestamp: int) -> Optional[Dict]:
        """根据时间戳获取特定的BTC 15分钟市场"""
        try:
            gamma_base = "https://gamma-api.polymarket.com"
            url = f"{gamma_base}/markets/slug/btc-updown-15m-{timestamp}"

            self.log(f"🔍 查询市场: {url}")

            response = requests.get(url, timeout=30)

            if response.status_code == 404:
                self.log(f"❌ 未找到时间戳 {timestamp} 对应的市场")
                return None

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                # 检查市场是否可用
                if data.get("closed") is False and data.get("acceptingOrders", True):

                    # 获取token IDs
                    clob_token_ids = data.get("clobTokenIds", "[]")
                    if isinstance(clob_token_ids, str):
                        token_ids = json.loads(clob_token_ids)
                    else:
                        token_ids = clob_token_ids

                    if len(token_ids) >= 2:
                        market_info = {
                            "question": data.get("question", "").strip(),
                            "ends_at": data.get("endDate", ""),
                            "market_id": data.get("id", ""),
                            "yes_token": token_ids[0],
                            "no_token": token_ids[1],
                            "accepting_order": data.get("acceptingOrders", True),
                        }

                        self.log(f"✅ 找到可用市场: {market_info['question']}")
                        return market_info
                    else:
                        self.log(f"❌ 市场token数量不足: {len(token_ids)}")
                else:
                    self.log(
                        f"❌ 市场不可用: closed={data.get('closed')}, acceptingOrders={data.get('acceptingOrders')}"
                    )

            return None

        except Exception as e:
            self.log(f"❌ 获取市场失败: {e}", "ERROR")
            return None

    async def terminate_current_strategy(self):
        """强制终止当前运行的策略"""
        if self.current_strategy and self.strategy_task:
            self.log("🛑 终止上一个15分钟周期的策略")
            try:
                # 停止策略
                if hasattr(self.current_strategy, "stop"):
                    await self.current_strategy.stop()

                # 取消任务
                if not self.strategy_task.done():
                    self.strategy_task.cancel()
                    try:
                        await self.strategy_task
                    except asyncio.CancelledError:
                        pass

                self.log("✅ 策略已优雅停止")

            except Exception as e:
                self.log(f"❌ 终止策略时出错: {e}", "ERROR")
            finally:
                self.current_strategy = None
                self.strategy_task = None
        else:
            self.log("📝 没有运行中的策略需要终止")

    async def start_trading_strategy(self, market_id: str, btc_price: float) -> bool:
        """启动交易策略"""
        try:
            beijing_time = self.get_beijing_time()
            self.log(f"🚀 启动新的15分钟交易策略 ({self.strategy_version})")
            self.log(f"   时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"   市场ID: {market_id}")
            self.log(f"   BTC价格: ${btc_price:,.2f}")
            self.log(f"   交易金额: ${self.trade_amount}")

            # 根据策略版本创建不同的策略实例
            if self.strategy_type == "sniper":
                # 创建Sniper策略实例
                self.current_strategy = BTCHighOddsSniperStrategy(
                    market_id=market_id,
                    baseline_price=btc_price,
                    core_sensitivity=50.0,
                    mu_factor=1.8,
                )

                # 如果有WebSocket价格提供器，共享给策略
                if self.price_provider:
                    self.current_strategy.price_provider = self.price_provider
                    self.log("✅ 已共享WebSocket价格数据给策略")

                # 启动策略
                self.strategy_task = asyncio.create_task(self.current_strategy.run())

            elif self.strategy_type == "v2":
                # V2策略 - 集成异步方式，共享WebSocket数据
                self.log("🔧 启动V2策略 (集成模式)")

                try:
                    # 创建V2策略实例 (实际上V2和Sniper使用相同的类，但参数不同)
                    self.current_strategy = BTCHighOddsSniperStrategy(
                        market_id=market_id,
                        baseline_price=btc_price,
                        core_sensitivity=40.0,  # V2使用较低的敏感度
                        mu_factor=1.5,  # V2使用较保守的系数
                    )

                    # 如果有WebSocket价格提供器，共享给策略
                    if self.price_provider:
                        self.current_strategy.price_provider = self.price_provider
                        self.log("✅ 已共享WebSocket价格数据给V2策略")

                    # 启动策略
                    self.strategy_task = asyncio.create_task(
                        self.current_strategy.run(amount=self.trade_amount)
                    )

                except Exception as e:
                    self.log(f"❌ 无法创建V2策略实例: {e}", "ERROR")
                    # 回退到子进程方式
                    cmd = [
                        sys.executable,
                        "btc_15min_strategy_v2.py",  # 修正文件名
                        market_id,
                        str(self.trade_amount),
                        str(btc_price),
                    ]

                    self.log(f"📝 回退到子进程模式: {' '.join(cmd)}")

                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                    )

                    self.strategy_task = asyncio.create_task(
                        self._monitor_subprocess(process)
                    )

            else:
                # V1策略 - 使用子进程方式（保持兼容性）
                cmd = [
                    sys.executable,
                    "btc_15min_strategy.py",
                    market_id,
                    str(self.trade_amount),
                    str(btc_price),
                ]

                self.log(f"📝 执行V1策略命令: {' '.join(cmd)}")

                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                self.strategy_task = asyncio.create_task(
                    self._monitor_subprocess(process)
                )

            self.log(f"✅ 新策略已启动")
            return True

        except Exception as e:
            self.log(f"❌ 启动策略失败: {e}", "ERROR")
            return False

    async def _monitor_subprocess(self, process):
        """监控子进程"""
        try:
            # 等待进程完成
            returncode = await asyncio.get_event_loop().run_in_executor(
                None, process.wait
            )

            if returncode == 0:
                self.log("✅ 策略进程正常结束")
            else:
                self.log(f"⚠️ 策略进程异常结束 (返回码: {returncode})")

        except Exception as e:
            self.log(f"❌ 监控子进程时出错: {e}", "ERROR")

    def decide_market_participation(self) -> Tuple[Optional[Dict], str]:
        """
        决定参与哪个市场
        返回: (市场信息, 决策原因)
        """
        prev_timestamp, next_timestamp, prev_beijing_time, next_beijing_time = (
            self.get_15min_timestamps()
        )

        # 计算到上一个15分钟整点的时间差
        time_since_prev = self.get_time_to_interval_start(prev_beijing_time)
        time_to_next = self.get_time_to_interval_start(next_beijing_time)

        # 注意：time_since_prev 应该是负数（已经过去的时间）
        minutes_since_prev = abs(time_since_prev)
        minutes_to_next = time_to_next

        self.log(f"⏰ 时间分析:")
        self.log(
            f"   上一个15分钟整点: {prev_beijing_time.strftime('%H:%M')} (时间戳: {prev_timestamp})"
        )
        self.log(
            f"   下一个15分钟整点: {next_beijing_time.strftime('%H:%M')} (时间戳: {next_timestamp})"
        )
        self.log(f"   距离上一个整点: {minutes_since_prev:.1f}分钟")
        self.log(f"   距离下一个整点: {minutes_to_next:.1f}分钟")

        # 决策逻辑
        if minutes_since_prev <= self.time_threshold:
            # 间隔小于5分钟，尝试参与上一个市场
            self.log(
                f"🎯 决策: 参与上一个市场 (间隔{minutes_since_prev:.1f}分钟 <= {self.time_threshold}分钟)"
            )

            market = self.get_market_by_timestamp(prev_timestamp)
            if market:
                return market, f"参与上一个市场 (间隔{minutes_since_prev:.1f}分钟)"
            else:
                self.log(f"❌ 上一个市场不可用，改为等待下一个市场")
                return (
                    None,
                    f"上一个市场不可用，等待下一个市场 (还需{minutes_to_next:.1f}分钟)",
                )
        else:
            # 间隔超过5分钟，等待下一个市场
            self.log(
                f"⏳ 决策: 等待下一个市场 (间隔{minutes_since_prev:.1f}分钟 > {self.time_threshold}分钟)"
            )
            return None, f"等待下一个市场 (还需{minutes_to_next:.1f}分钟)"

    async def wait_for_next_15min_interval(self):
        """等待下一个15分钟整点"""
        while self.running:
            beijing_time = self.get_beijing_time()
            current_minute = beijing_time.minute
            current_second = beijing_time.second

            # 计算到下一个15分钟整点的等待时间
            minutes_to_next = 15 - (current_minute % 15)
            if minutes_to_next == 15:
                minutes_to_next = 0

            # 计算总的等待秒数
            total_seconds_to_next = (minutes_to_next * 60) - current_second

            if total_seconds_to_next <= 30:  # 如果在30秒内，认为已经到了
                break

            # 正确计算显示的分钟和秒数
            display_minutes = total_seconds_to_next // 60
            display_seconds = total_seconds_to_next % 60

            self.log(
                f"⏰ 等待下一个15分钟整点，还需 {display_minutes}分{display_seconds}秒"
            )

            # 每分钟检查一次，但不超过剩余时间
            sleep_time = min(60, total_seconds_to_next)
            await asyncio.sleep(sleep_time)

    async def run_15min_trading_cycle(self):
        """执行15分钟交易周期 - 获取最新数据并启动策略"""
        beijing_time = self.get_beijing_time()
        
        # 获取当前15分钟市场的时间戳
        prev_timestamp, next_timestamp, prev_beijing_time, next_beijing_time = (
            self.get_15min_timestamps()
        )
        
        # 检查是否已经为这个周期启动过策略
        if self.current_cycle_timestamp == next_timestamp:
            self.log(f"⏭️ 当前周期 ({next_timestamp}) 已经启动过策略，跳过")
            return True
            
        self.log(
            f"🔄 开始新的15分钟交易周期 - {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.log(f"📅 周期时间戳: {next_timestamp}")

        # 1. 重新获取BTC价格
        self.log("📊 重新获取最新BTC价格...")
        btc_price = self.get_btc_price()
        if not btc_price:
            self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
            return False

        # 3. 尝试获取当前15分钟市场
        self.log(f"🔍 重新查询15分钟市场 (时间戳: {next_timestamp})...")
        market = self.get_market_by_timestamp(next_timestamp)

        if not market:
            self.log("❌ 没有找到可用的15分钟市场，跳过本次交易", "ERROR")
            return False

        self.log(f"🎯 找到市场: {market.get('question', 'Unknown')}")

        # 4. 启动交易策略
        success = await self.start_trading_strategy(market["market_id"], btc_price)
        if not success:
            self.log("❌ 启动交易策略失败", "ERROR")
            return False

        # 5. 记录当前周期时间戳，防止重复启动
        self.current_cycle_timestamp = next_timestamp
        self.log("✅ 新的15分钟交易周期启动成功")
        return True

    async def run_smart_trading_cycle(self):
        """执行智能交易周期"""
        self.log("🔄 开始智能交易周期")

        # 1. 获取BTC价格
        btc_price = self.get_btc_price()
        if not btc_price:
            self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
            return False

        # 2. 决定参与哪个市场
        market, reason = self.decide_market_participation()

        if market:
            # 直接参与找到的市场
            self.log(f"🎯 立即参与市场: {reason}")
            self.log(f"📊 市场: {market.get('question')}")

            success = await self.start_trading_strategy(market["market_id"], btc_price)
            if success:
                self.log("✅ 智能交易周期启动成功")
                return True
            else:
                self.log("❌ 启动交易策略失败", "ERROR")
                return False
        else:
            # 需要等待下一个市场
            self.log(f"⏳ {reason}")

            # 等待下一个15分钟整点
            await self.wait_for_next_15min_interval()

            if not self.running:
                return False

            # 获取下一个市场
            _, next_timestamp, _, _ = self.get_15min_timestamps()
            market = self.get_market_by_timestamp(next_timestamp)

            if market and self.running:
                # 重新获取BTC价格
                btc_price = self.get_btc_price()
                if not btc_price:
                    self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
                    return False

                self.log(f"🎯 参与下一个市场")
                self.log(f"📊 市场: {market.get('question')}")

                success = await self.start_trading_strategy(
                    market["market_id"], btc_price
                )
                if success:
                    self.log("✅ 智能交易周期启动成功")
                    return True
                else:
                    self.log("❌ 启动交易策略失败", "ERROR")
                    return False
            else:
                self.log("❌ 等待市场失败或被中断", "ERROR")
                return False

    def check_strategy_status(self):
        """检查策略运行状态"""
        if self.strategy_task and not self.strategy_task.done():
            return True
        elif self.strategy_task and self.strategy_task.done():
            try:
                result = self.strategy_task.result()
                self.log("✅ 策略正常结束")
            except Exception as e:
                self.log(f"❌ 策略异常结束: {e}", "ERROR")

            # 策略结束时重置周期跟踪
            self.strategy_task = None
            self.current_strategy = None
            # 注意：不重置 current_cycle_timestamp，让它保持到下一个15分钟周期
            return False
        return False

    async def run(self):
        """主运行循环 - 每15分钟重新开始"""
        self.log("🚀 BTC智能自动交易器启动")

        try:
            # 首先启动WebSocket价格监控
            websocket_task = None
            if self.strategy_type in ["sniper", "v2"]:  # 为V2策略也启用WebSocket
                self.log("🔗 启动WebSocket价格监控...")
                websocket_task = asyncio.create_task(self.start_websocket_monitor())

                # 等待WebSocket连接建立
                await asyncio.sleep(5)
                self.log("✅ WebSocket价格监控已启动")

            # 首次启动时的智能决策
            if self.running:
                success = await self.run_smart_trading_cycle()
                if not success:
                    self.log("❌ 首次交易周期失败", "ERROR")

            # 主循环：每15分钟重新开始
            while self.running:
                # --- 实时数据推送 (每秒执行) ---
                if self.price_provider and self.current_strategy:
                    current_price = self.price_provider.get_current_price()
                    if (
                        hasattr(self.current_strategy, "update_market_state")
                        and current_price > 0
                    ):
                        await self.current_strategy.update_market_state(current_price)

                # 检查策略状态
                self.check_strategy_status()

                # 检查是否到了下一个15分钟整点
                beijing_time = self.get_beijing_time()
                current_minute = beijing_time.minute
                current_second = beijing_time.second

                # 计算到下一个15分钟整点的时间
                minutes_to_next = 15 - (current_minute % 15)
                if minutes_to_next == 15:
                    minutes_to_next = 0
                total_seconds_to_next = (minutes_to_next * 60) - current_second

                # 获取当前周期的时间戳用于比较
                _, next_timestamp, _, _ = self.get_15min_timestamps()

                # 如果在30秒内到达下一个15分钟整点，且还没有为这个周期启动过策略
                if total_seconds_to_next <= 30 and self.current_cycle_timestamp != next_timestamp:
                    self.log(f"🕐 准备启动新周期 - 当前: {self.current_cycle_timestamp}, 目标: {next_timestamp}")
                    
                    # 等待到达整点
                    if total_seconds_to_next > 0:
                        self.log(f"⏰ 等待 {total_seconds_to_next} 秒到达15分钟整点...")
                        await asyncio.sleep(total_seconds_to_next)

                    if not self.running:
                        break

                    # 每个新的15分钟周期都要：
                    # 1. 强制终止上一个策略（如果存在）
                    await self.terminate_current_strategy()

                    # 2. 启动新的15分钟交易周期（重新获取市场和价格）
                    await self.run_15min_trading_cycle()
                else:
                    # 等待5秒再检查，减少CPU占用
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
        except Exception as e:
            self.log(f"运行错误: {e}", "ERROR")
        finally:
            await self.stop()

    async def stop(self):
        """停止智能自动交易器"""
        self.log("🛑 停止BTC智能自动交易器")
        self.running = False

        # 停止当前策略
        await self.terminate_current_strategy()

        # 清理WebSocket连接
        if self.price_provider:
            try:
                if (
                    hasattr(self.price_provider, "ws_monitor")
                    and self.price_provider.ws_monitor
                ):
                    self.price_provider.ws_monitor.cleanup()
            except Exception as e:
                self.log(f"清理WebSocket连接时出错: {e}", "ERROR")


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if "trader" in globals():
        # 设置停止标志，让异步循环自然退出
        trader.running = False
    sys.exit(0)


async def main():
    """主函数"""
    print("🤖 BTC 智能自动交易器 - 集成WebSocket实时价格监控")
    print("=" * 70)
    print("启动后判断跟上一个15分钟市场的间隔：")
    print("- 如果间隔小于5分钟，则直接获取并参与上一个15分钟的市场")
    print("- 如果间隔超过5分钟，则等待并参与下一个市场")
    print()
    print("新特性：")
    print("- 集成BTCWebSocketMonitorV2Fixed实时价格同步")
    print("- BTCHighOddsSniperStrategy使用共享的WebSocket价格数据")
    print("- 异步架构支持实时交易决策")
    print("=" * 70)
    print("使用方法:")
    print("  python3 btc_smart_auto_trader.py [交易金额] [策略版本]")
    print("  例如: python3 btc_smart_auto_trader.py 1 sniper  # 使用$1执行sniper策略")
    print("  例如: python3 btc_smart_auto_trader.py 5 v2     # 使用$5执行v2策略")
    print("  例如: python3 btc_smart_auto_trader.py 5        # 使用$5执行v1策略")
    print("=" * 70)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 解析命令行参数
        trade_amount = 5.0
        strategy_version = "v1"

        if len(sys.argv) > 1:
            try:
                trade_amount = float(sys.argv[1])
                if trade_amount <= 0:
                    print("❌ 交易金额必须大于0")
                    return
                elif trade_amount < 1.0:
                    print(f"⚠️ 交易金额 ${trade_amount} 低于Polymarket最小要求 $1.0，自动调整为 $1.0")
                    trade_amount = 1.0
            except ValueError:
                print("❌ 交易金额格式错误")
                return

        if len(sys.argv) > 2:
            strategy_version = sys.argv[2].lower()
            if strategy_version not in ["v1", "v2", "sniper"]:
                print("❌ 策略版本只支持 v1, v2 或 sniper")
                return

        print(f"💰 交易金额: ${trade_amount}")
        print(f"📋 策略版本: {strategy_version}")

        if strategy_version.lower() == "sniper":
            print("🎯 Sniper策略特性: 激进高赔率狙击 + WebSocket实时 + 高敏感度")
        elif strategy_version.lower() == "v2":
            print("🔧 V2策略特性: 保守高赔率策略 + WebSocket实时 + 低敏感度")
        else:
            print("🔧 V1策略特性: 传统15分钟区间策略")

        # 创建智能自动交易器
        global trader
        trader = BTCSmartAutoTrader(
            trade_amount=trade_amount, strategy_version=strategy_version
        )

        # 启动智能自动交易
        await trader.run()

    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        if "trader" in globals():
            await trader.stop()


def run_main():
    """运行主函数的同步包装器"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")


if __name__ == "__main__":
    run_main()
