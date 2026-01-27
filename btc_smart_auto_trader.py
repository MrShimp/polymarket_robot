#!/usr/bin/env python3
"""
BTC 智能自动交易器
启动后判断跟上一个15分钟市场的间隔：
- 如果间隔小于5分钟，则直接获取并参与上一个15分钟的市场
- 如果间隔超过5分钟，则等待并参与下一个市场
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
from typing import Optional, List, Dict, Tuple

class BTCSmartAutoTrader:
    """BTC智能自动交易器"""
    
    def __init__(self, trade_amount: float = 5.0, strategy_version: str = "v1"):
        self.trade_amount = trade_amount
        self.strategy_version = strategy_version
        self.running = True
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.et_winter_tz = pytz.FixedOffset(-5 * 60)  # UTC-5，美东冬季时间
        
        # 时间判断阈值（分钟）
        self.time_threshold = 5  # 5分钟阈值
        
        # 根据策略版本确定策略文件
        if strategy_version.lower() == "v2":
            self.strategy_script = "btc_15min_strategy_v2.py"
        else:
            self.strategy_script = "btc_15min_strategy.py"
        
        # 日志设置
        self.setup_logging()
        
        # 当前运行的策略进程
        self.current_strategy_process = None
        
        self.log("🤖 BTC智能自动交易器初始化完成")
        self.log(f"💰 交易金额: ${trade_amount}")
        self.log(f"📋 策略版本: {strategy_version}")
        self.log(f"📄 策略脚本: {self.strategy_script}")
        self.log(f"⏰ 时间阈值: {self.time_threshold}分钟")
    
    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/auto_trader_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_suffix = f"_{self.strategy_version}" if hasattr(self, 'strategy_version') else ""
        self.log_file = os.path.join(self.log_dir, f"smart_auto_trader{strategy_suffix}_{timestamp}.log")
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def get_beijing_time(self) -> datetime.datetime:
        """获取北京时间"""
        return datetime.datetime.now(self.beijing_tz)
    
    def get_15min_timestamps(self) -> Tuple[int, int, datetime.datetime, datetime.datetime]:
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
            minute=interval_start_minute, 
            second=0, 
            microsecond=0
        )
        
        # 下一个15分钟整点
        next_15min_beijing = prev_15min_beijing + datetime.timedelta(minutes=15)
        
        # 转换为美东时间并获取时间戳
        prev_15min_et = prev_15min_beijing.astimezone(self.et_winter_tz)
        next_15min_et = next_15min_beijing.astimezone(self.et_winter_tz)
        
        prev_timestamp = int(prev_15min_et.timestamp())
        next_timestamp = int(next_15min_et.timestamp())
        
        return prev_timestamp, next_timestamp, prev_15min_beijing, next_15min_beijing
    
    def get_time_to_interval_start(self, target_beijing_time: datetime.datetime) -> float:
        """计算到目标时间的分钟数"""
        now_beijing = self.get_beijing_time()
        time_diff = target_beijing_time - now_beijing
        return time_diff.total_seconds() / 60
    
    def get_btc_price(self) -> Optional[float]:
        """获取当前BTC价格"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            price = float(data['price'])
            
            self.log(f"📊 获取BTC价格: ${price:,.2f}")
            return price
            
        except Exception as e:
            self.log(f"❌ 获取BTC价格失败: {e}", "ERROR")
            return None
    
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
                if (data.get('closed') is False and 
                    data.get('acceptingOrders', True)):
                    
                    # 获取token IDs
                    clob_token_ids = data.get('clobTokenIds', '[]')
                    if isinstance(clob_token_ids, str):
                        token_ids = json.loads(clob_token_ids)
                    else:
                        token_ids = clob_token_ids
                    
                    if len(token_ids) >= 2:
                        market_info = {
                            "question": data.get('question', '').strip(),
                            "ends_at": data.get('endDate', ''),
                            "market_id": data.get('id', ''),
                            "yes_token": token_ids[0],
                            "no_token": token_ids[1],
                            "accepting_order": data.get('acceptingOrders', True)
                        }
                        
                        self.log(f"✅ 找到可用市场: {market_info['question']}")
                        return market_info
                    else:
                        self.log(f"❌ 市场token数量不足: {len(token_ids)}")
                else:
                    self.log(f"❌ 市场不可用: closed={data.get('closed')}, acceptingOrders={data.get('acceptingOrders')}")
            
            return None
            
        except Exception as e:
            self.log(f"❌ 获取市场失败: {e}", "ERROR")
            return None
    
    def terminate_current_strategy(self):
        """强制终止当前运行的策略"""
        if self.current_strategy_process and self.current_strategy_process.poll() is None:
            self.log("🛑 终止上一个15分钟周期的策略")
            try:
                self.current_strategy_process.terminate()
                # 等待进程优雅退出
                try:
                    self.current_strategy_process.wait(timeout=5)
                    self.log("✅ 策略进程已优雅退出")
                except subprocess.TimeoutExpired:
                    # 如果5秒内没有退出，强制杀死
                    self.current_strategy_process.kill()
                    self.current_strategy_process.wait()
                    self.log("⚠️ 策略进程已强制终止")
            except Exception as e:
                self.log(f"❌ 终止策略进程时出错: {e}", "ERROR")
            finally:
                self.current_strategy_process = None
        elif self.current_strategy_process:
            # 进程已经结束
            return_code = self.current_strategy_process.returncode
            if return_code == 0:
                self.log("✅ 上一个策略已正常结束")
            else:
                self.log(f"⚠️ 上一个策略异常结束 (返回码: {return_code})")
            self.current_strategy_process = None
        else:
            self.log("📝 没有运行中的策略需要终止")

    def start_trading_strategy(self, market_id: str, btc_price: float) -> bool:
        """启动交易策略"""
        try:
            beijing_time = self.get_beijing_time()
            self.log(f"🚀 启动新的15分钟交易策略 ({self.strategy_version})")
            self.log(f"   时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"   市场ID: {market_id}")
            self.log(f"   BTC价格: ${btc_price:,.2f}")
            self.log(f"   交易金额: ${self.trade_amount}")
            self.log(f"   策略脚本: {self.strategy_script}")
            
            # 启动新的策略进程
            cmd = [
                sys.executable, self.strategy_script,
                market_id,
                str(self.trade_amount),
                str(btc_price)
            ]
            
            self.log(f"📝 执行命令: {' '.join(cmd)}")
            
            self.current_strategy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.log(f"✅ 新策略进程已启动 (PID: {self.current_strategy_process.pid})")
            return True
            
        except Exception as e:
            self.log(f"❌ 启动策略失败: {e}", "ERROR")
            return False
    
    def decide_market_participation(self) -> Tuple[Optional[Dict], str]:
        """
        决定参与哪个市场
        返回: (市场信息, 决策原因)
        """
        prev_timestamp, next_timestamp, prev_beijing_time, next_beijing_time = self.get_15min_timestamps()
        
        # 计算到上一个15分钟整点的时间差
        time_since_prev = self.get_time_to_interval_start(prev_beijing_time)
        time_to_next = self.get_time_to_interval_start(next_beijing_time)
        
        # 注意：time_since_prev 应该是负数（已经过去的时间）
        minutes_since_prev = abs(time_since_prev)
        minutes_to_next = time_to_next
        
        self.log(f"⏰ 时间分析:")
        self.log(f"   上一个15分钟整点: {prev_beijing_time.strftime('%H:%M')} (时间戳: {prev_timestamp})")
        self.log(f"   下一个15分钟整点: {next_beijing_time.strftime('%H:%M')} (时间戳: {next_timestamp})")
        self.log(f"   距离上一个整点: {minutes_since_prev:.1f}分钟")
        self.log(f"   距离下一个整点: {minutes_to_next:.1f}分钟")
        
        # 决策逻辑
        if minutes_since_prev <= self.time_threshold:
            # 间隔小于5分钟，尝试参与上一个市场
            self.log(f"🎯 决策: 参与上一个市场 (间隔{minutes_since_prev:.1f}分钟 <= {self.time_threshold}分钟)")
            
            market = self.get_market_by_timestamp(prev_timestamp)
            if market:
                return market, f"参与上一个市场 (间隔{minutes_since_prev:.1f}分钟)"
            else:
                self.log(f"❌ 上一个市场不可用，改为等待下一个市场")
                return None, f"上一个市场不可用，等待下一个市场 (还需{minutes_to_next:.1f}分钟)"
        else:
            # 间隔超过5分钟，等待下一个市场
            self.log(f"⏳ 决策: 等待下一个市场 (间隔{minutes_since_prev:.1f}分钟 > {self.time_threshold}分钟)")
            return None, f"等待下一个市场 (还需{minutes_to_next:.1f}分钟)"
    
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
            
            self.log(f"⏰ 等待下一个15分钟整点，还需 {display_minutes}分{display_seconds}秒")
            
            # 每分钟检查一次，但不超过剩余时间
            sleep_time = min(60, total_seconds_to_next)
            time.sleep(sleep_time)

    def run_15min_trading_cycle(self):
        """执行15分钟交易周期 - 获取最新数据并启动策略"""
        beijing_time = self.get_beijing_time()
        self.log(f"🔄 开始新的15分钟交易周期 - {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 重新获取BTC价格
        self.log("📊 重新获取最新BTC价格...")
        btc_price = self.get_btc_price()
        if not btc_price:
            self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
            return False
        
        # 2. 获取当前15分钟市场的时间戳
        prev_timestamp, next_timestamp, prev_beijing_time, next_beijing_time = self.get_15min_timestamps()
        
        # 3. 尝试获取当前15分钟市场
        self.log(f"🔍 重新查询15分钟市场 (时间戳: {next_timestamp})...")
        market = self.get_market_by_timestamp(next_timestamp)
        
        if not market:
            self.log("❌ 没有找到可用的15分钟市场，跳过本次交易", "ERROR")
            return False
        
        self.log(f"🎯 找到市场: {market.get('question', 'Unknown')}")
        
        # 4. 启动交易策略
        success = self.start_trading_strategy(market['market_id'], btc_price)
        if not success:
            self.log("❌ 启动交易策略失败", "ERROR")
            return False
        
        self.log("✅ 新的15分钟交易周期启动成功")
        return True
    
    def run_smart_trading_cycle(self):
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
            
            success = self.start_trading_strategy(market['market_id'], btc_price)
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
            self.wait_for_next_15min_interval()
            
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
                
                success = self.start_trading_strategy(market['market_id'], btc_price)
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
        if self.current_strategy_process:
            if self.current_strategy_process.poll() is None:
                self.log("📊 策略正在运行中...")
                return True
            else:
                return_code = self.current_strategy_process.returncode
                if return_code == 0:
                    self.log("✅ 策略正常结束")
                else:
                    self.log(f"❌ 策略异常结束 (返回码: {return_code})", "ERROR")
                    # 获取错误输出
                    try:
                        _, stderr = self.current_strategy_process.communicate(timeout=5)
                        if stderr:
                            self.log(f"错误信息: {stderr}", "ERROR")
                    except:
                        pass
                
                self.current_strategy_process = None
                return False
        return False
    
    def run(self):
        """主运行循环 - 每15分钟重新开始"""
        self.log("🚀 BTC智能自动交易器启动")
        
        try:
            # 首次启动时的智能决策
            if self.running:
                success = self.run_smart_trading_cycle()
                if not success:
                    self.log("❌ 首次交易周期失败", "ERROR")
            
            # 主循环：每15分钟重新开始
            while self.running:
                # 等待下一个15分钟整点
                self.wait_for_next_15min_interval()
                
                if not self.running:
                    break
                
                # 每个新的15分钟周期都要：
                # 1. 强制终止上一个策略（如果存在）
                self.terminate_current_strategy()
                
                # 2. 启动新的15分钟交易周期（重新获取市场和价格）
                self.run_15min_trading_cycle()
                
                # 等待一分钟再检查
                time.sleep(60)
                
        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
        except Exception as e:
            self.log(f"运行错误: {e}", "ERROR")
        finally:
            self.stop()
    
    def stop(self):
        """停止智能自动交易器"""
        self.log("🛑 停止BTC智能自动交易器")
        self.running = False
        
        # 停止当前策略进程
        self.terminate_current_strategy()


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if 'trader' in globals():
        trader.stop()
    sys.exit(0)


def main():
    """主函数"""
    print("🤖 BTC 智能自动交易器")
    print("=" * 60)
    print("启动后判断跟上一个15分钟市场的间隔：")
    print("- 如果间隔小于5分钟，则直接获取并参与上一个15分钟的市场")
    print("- 如果间隔超过5分钟，则等待并参与下一个市场")
    print("=" * 60)
    print("使用方法:")
    print("  python3 btc_smart_auto_trader.py [交易金额] [策略版本]")
    print("  例如: python3 btc_smart_auto_trader.py 1 v2  # 使用$1执行v2策略")
    print("  例如: python3 btc_smart_auto_trader.py 5     # 使用$5执行v1策略")
    print("=" * 60)
    
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
            except ValueError:
                print("❌ 交易金额格式错误")
                return
        
        if len(sys.argv) > 2:
            strategy_version = sys.argv[2].lower()
            if strategy_version not in ["v1", "v2"]:
                print("❌ 策略版本只支持 v1 或 v2")
                return
        
        print(f"💰 交易金额: ${trade_amount}")
        print(f"📋 策略版本: {strategy_version}")
        
        # 创建智能自动交易器
        global trader
        trader = BTCSmartAutoTrader(trade_amount=trade_amount, strategy_version=strategy_version)
        
        # 启动智能自动交易
        trader.run()
        
    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        if 'trader' in globals():
            trader.stop()


if __name__ == "__main__":
    main()