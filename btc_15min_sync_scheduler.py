#!/usr/bin/env python3
"""
BTC 15分钟策略同步调度器
每整15分钟自动启动新的策略实例，关闭上一个实例
类似btc_auto_trader的逻辑，但使用同步调用
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
import threading
from typing import Optional, List, Dict, Tuple


class BTC15MinSyncScheduler:
    """BTC 15分钟策略同步调度器"""

    def __init__(self, trade_amount: float = 5.0):
        self.trade_amount = trade_amount
        self.running = True
        self.beijing_tz = pytz.timezone("Asia/Shanghai")

        # 日志设置
        self.setup_logging()

        # 当前运行的策略实例
        self.current_strategy = None
        self.current_strategy_thread = None
        self.strategy_stop_event = threading.Event()

        self.log("🤖 BTC 15分钟同步调度器初始化完成")
        self.log(f"💰 交易金额: ${trade_amount}")

    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/sync_scheduler_logs"
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"sync_scheduler_{timestamp}.log")

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

    def is_15min_interval(self) -> bool:
        """检查当前是否是15分钟整点"""
        beijing_time = self.get_beijing_time()
        return beijing_time.minute % 15 == 0 and beijing_time.second < 30

    def wait_for_next_15min_interval(self):
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
            time.sleep(sleep_time)

    def get_btc_price(self) -> Optional[float]:
        """获取当前BTC价格"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = float(data["price"])

            self.log(f"📊 获取BTC价格: ${price:,.2f}")
            return price

        except Exception as e:
            self.log(f"❌ 获取BTC价格失败: {e}", "ERROR")
            return None

    def get_available_markets(self) -> List[Dict]:
        """获取可用的BTC 15分钟市场"""
        try:
            self.log("🔍 查找可用市场...")

            # 调用btc_market_query.py获取JSON格式数据
            result = subprocess.run(
                [sys.executable, "btc_market_query.py", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                self.log(f"❌ 市场查询失败 (返回码: {result.returncode})", "ERROR")
                if result.stderr:
                    self.log(f"错误输出: {result.stderr}", "ERROR")
                if result.stdout:
                    self.log(f"标准输出: {result.stdout[:500]}...", "ERROR")
                return []

            # 解析JSON输出
            try:
                if not result.stdout.strip():
                    self.log("❌ 市场查询返回空结果", "ERROR")
                    return []

                markets_data = json.loads(result.stdout)

                # 检查是否有错误
                if isinstance(markets_data, dict) and "error" in markets_data:
                    self.log(f"❌ 市场查询错误: {markets_data['error']}", "ERROR")
                    return []

                # 确保是列表格式
                if not isinstance(markets_data, list):
                    self.log(f"❌ 市场数据格式错误: {type(markets_data)}", "ERROR")
                    return []

                self.log(f"📋 找到 {len(markets_data)} 个可用市场")

                # 验证市场数据完整性
                valid_markets = []
                for market in markets_data:
                    if (
                        isinstance(market, dict)
                        and market.get("market_id")
                        and market.get("yes_token")
                        and market.get("no_token")
                    ):
                        valid_markets.append(market)
                        self.log(
                            f"✅ 有效市场: {market.get('question', 'Unknown')[:50]}..."
                        )
                    else:
                        self.log(f"⚠️ 跳过无效市场数据: {market}")

                self.log(f"✅ 验证通过的市场: {len(valid_markets)} 个")
                return valid_markets

            except json.JSONDecodeError as e:
                self.log(f"❌ JSON解析失败: {e}", "ERROR")
                self.log(f"原始输出: {result.stdout[:500]}...")
                return []

        except subprocess.TimeoutExpired:
            self.log("❌ 市场查询超时", "ERROR")
            return []
        except Exception as e:
            self.log(f"❌ 获取市场列表失败: {e}", "ERROR")
            import traceback

            self.log(f"详细错误: {traceback.format_exc()}", "ERROR")
            return []

    def stop_current_strategy(self):
        """停止当前运行的策略"""
        if self.current_strategy:
            self.log("🛑 停止上一个15分钟周期的策略")
            try:
                # 设置停止事件
                self.strategy_stop_event.set()
                
                # 停止策略
                self.current_strategy.running = False
                self.current_strategy.stop_event.set()
                
                # 等待线程结束
                if self.current_strategy_thread and self.current_strategy_thread.is_alive():
                    self.current_strategy_thread.join(timeout=5)
                    if self.current_strategy_thread.is_alive():
                        self.log("⚠️ 策略线程未能在5秒内结束", "WARNING")
                    else:
                        self.log("✅ 策略已优雅停止")
                
            except Exception as e:
                self.log(f"❌ 停止策略时出错: {e}", "ERROR")
            finally:
                self.current_strategy = None
                self.current_strategy_thread = None
                self.strategy_stop_event.clear()
        else:
            self.log("📝 没有运行中的策略需要停止")

    def start_new_strategy(self, market_id: str, btc_price: float) -> bool:
        """启动新的策略实例"""
        try:
            beijing_time = self.get_beijing_time()
            self.log(f"🚀 启动新的15分钟策略实例")
            self.log(f"   时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"   市场ID: {market_id}")
            self.log(f"   BTC价格: ${btc_price:,.2f}")
            self.log(f"   交易金额: ${self.trade_amount}")

            # 导入策略类
            from btc_15min_strategy import BTC15MinStrategy

            # 创建新的策略实例
            self.current_strategy = BTC15MinStrategy(baseline_price=btc_price)
            self.current_strategy.default_amount = self.trade_amount
            
            # 设置BTC价格
            self.current_strategy.btc_price = btc_price
            self.current_strategy.baseline_price = btc_price

            # 创建策略运行线程
            def run_strategy():
                try:
                    self.log("📈 策略线程开始执行")
                    # 启动策略的异步执行
                    import asyncio
                    
                    # 创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # 启动价格监控和交易执行
                        self.current_strategy.running = True
                        
                        # 同时运行价格监控和交易执行
                        loop.run_until_complete(asyncio.gather(
                            self.current_strategy.start_price_monitoring(),
                            self.current_strategy.execute_trade(market_id)
                        ))
                        
                    finally:
                        loop.close()
                        
                except Exception as e:
                    self.log(f"❌ 策略执行异常: {e}", "ERROR")
                    import traceback
                    self.log(f"详细错误: {traceback.format_exc()}", "ERROR")

            # 启动策略线程
            self.current_strategy_thread = threading.Thread(target=run_strategy, daemon=True)
            self.current_strategy_thread.start()

            self.log(f"✅ 新策略实例已启动")
            return True

        except Exception as e:
            self.log(f"❌ 启动策略失败: {e}", "ERROR")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}", "ERROR")
            return False

    def check_strategy_status(self):
        """检查策略运行状态"""
        if self.current_strategy and self.current_strategy_thread:
            if self.current_strategy_thread.is_alive():
                self.log("📊 策略正在运行中...")
            else:
                self.log("⚠️ 策略线程已结束")
                self.current_strategy = None
                self.current_strategy_thread = None
        elif self.current_strategy:
            self.log("📊 策略实例存在但无线程")
        else:
            self.log("📝 当前无运行中的策略")

    def run_trading_cycle(self):
        """执行一次完整的交易周期"""
        beijing_time = self.get_beijing_time()
        self.log(f"🔄 开始新的交易周期 - {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. 获取BTC价格
        self.log("📊 获取最新BTC价格...")
        btc_price = self.get_btc_price()
        if not btc_price:
            self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
            return

        # 2. 获取可用市场
        self.log("🔍 查询可用市场...")
        markets = self.get_available_markets()
        if not markets:
            self.log("❌ 没有找到可用市场，跳过本次交易", "ERROR")
            return

        # 3. 选择第一个可用市场
        selected_market = markets[0]
        market_id = selected_market.get("market_id")

        if not market_id:
            self.log("❌ 市场ID无效，跳过本次交易", "ERROR")
            return

        self.log(f"🎯 选择市场: {selected_market.get('question', 'Unknown')}")

        # 4. 启动新的策略实例
        success = self.start_new_strategy(market_id, btc_price)
        if not success:
            self.log("❌ 启动策略实例失败", "ERROR")
            return

        self.log("✅ 新的15分钟交易周期启动成功")

    def run(self):
        """主运行循环"""
        self.log("🚀 BTC 15分钟同步调度器启动")

        try:
            while self.running:
                # 等待下一个15分钟整点
                self.wait_for_next_15min_interval()

                if not self.running:
                    break

                # 每个新的15分钟周期都要：
                # 1. 停止上一个策略实例
                self.stop_current_strategy()

                # 2. 启动新的交易周期
                self.run_trading_cycle()

                # 等待一分钟再检查
                time.sleep(60)

        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
        except Exception as e:
            self.log(f"运行错误: {e}", "ERROR")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}", "ERROR")
        finally:
            self.stop()

    def stop(self):
        """停止调度器"""
        self.log("🛑 停止BTC 15分钟同步调度器")
        self.running = False

        # 停止当前策略实例
        self.stop_current_strategy()


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if "scheduler" in globals():
        scheduler.stop()
    sys.exit(0)


def main():
    """主函数"""
    print("🤖 BTC 15分钟策略同步调度器")
    print("=" * 60)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 获取交易金额参数
        trade_amount = 5.0
        if len(sys.argv) > 1:
            try:
                trade_amount = float(sys.argv[1])
                if trade_amount <= 0:
                    print("❌ 交易金额必须大于0")
                    return
            except ValueError:
                print("❌ 交易金额格式错误")
                return

        print(f"💰 交易金额: ${trade_amount}")

        # 创建同步调度器
        global scheduler
        scheduler = BTC15MinSyncScheduler(trade_amount=trade_amount)

        # 启动调度器
        scheduler.run()

    except Exception as e:
        print(f"❌ 程序错误: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
    finally:
        if "scheduler" in globals():
            scheduler.stop()


if __name__ == "__main__":
    main()