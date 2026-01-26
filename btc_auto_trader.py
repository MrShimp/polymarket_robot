#!/usr/bin/env python3
"""
BTC 15分钟自动交易定时器
在每个15分钟整点自动执行交易策略：
1. 获取最新BTC价格
2. 查找可用的市场
3. 启动交易策略
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
from typing import Optional, List, Dict

class BTCAutoTrader:
    """BTC自动交易器"""
    
    def __init__(self, trade_amount: float = 5.0):
        self.trade_amount = trade_amount
        self.running = True
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 日志设置
        self.setup_logging()
        
        # 当前运行的策略进程
        self.current_strategy_process = None
        
        self.log("🤖 BTC自动交易器初始化完成")
        self.log(f"💰 交易金额: ${trade_amount}")
    
    def setup_logging(self):
        """设置日志"""
        self.log_dir = "data/auto_trader_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"auto_trader_{timestamp}.log")
    
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
            
            seconds_to_next = (minutes_to_next * 60) - current_second
            
            if seconds_to_next <= 30:  # 如果在30秒内，认为已经到了
                break
            
            self.log(f"⏰ 等待下一个15分钟整点，还需 {minutes_to_next}分{60-current_second}秒")
            
            # 每分钟检查一次
            time.sleep(min(60, seconds_to_next))
    
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
    
    def get_available_markets(self) -> List[Dict]:
        """获取可用的BTC 15分钟市场"""
        try:
            self.log("🔍 查找可用市场...")
            
            # 调用test_trading_bot.py获取JSON格式数据
            result = subprocess.run([
                sys.executable, "test_trading_bot.py", "--json"
            ], capture_output=True, text=True, timeout=60)
            
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
                if isinstance(markets_data, dict) and 'error' in markets_data:
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
                    if (isinstance(market, dict) and 
                        market.get('market_id') and 
                        market.get('yes_token') and 
                        market.get('no_token')):
                        valid_markets.append(market)
                        self.log(f"✅ 有效市场: {market.get('question', 'Unknown')[:50]}...")
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
    
    def start_trading_strategy(self, market_id: str, btc_price: float) -> bool:
        """启动交易策略"""
        try:
            self.log(f"🚀 启动交易策略")
            self.log(f"   市场ID: {market_id}")
            self.log(f"   BTC价格: ${btc_price:,.2f}")
            self.log(f"   交易金额: ${self.trade_amount}")
            
            # 停止之前的策略进程（如果有）
            if self.current_strategy_process and self.current_strategy_process.poll() is None:
                self.log("⚠️ 停止之前的策略进程")
                self.current_strategy_process.terminate()
                try:
                    self.current_strategy_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.current_strategy_process.kill()
            
            # 启动新的策略进程
            cmd = [
                sys.executable, "btc_15min_strategy.py",
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
            
            self.log(f"✅ 策略进程已启动 (PID: {self.current_strategy_process.pid})")
            return True
            
        except Exception as e:
            self.log(f"❌ 启动策略失败: {e}", "ERROR")
            return False
    
    def check_strategy_status(self):
        """检查策略运行状态"""
        if self.current_strategy_process:
            if self.current_strategy_process.poll() is None:
                # 策略仍在运行，显示运行时间
                import psutil
                try:
                    process = psutil.Process(self.current_strategy_process.pid)
                    create_time = datetime.datetime.fromtimestamp(process.create_time())
                    running_time = datetime.datetime.now() - create_time
                    self.log(f"📊 策略正在运行中... (运行时间: {running_time})")
                    
                    # 显示内存使用情况
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    self.log(f"💾 内存使用: {memory_mb:.1f} MB")
                    
                except Exception as e:
                    self.log("📊 策略正在运行中...")
            else:
                return_code = self.current_strategy_process.returncode
                if return_code == 0:
                    self.log("✅ 策略正常结束")
                else:
                    self.log(f"❌ 策略异常结束 (返回码: {return_code})", "ERROR")
                    # 获取错误输出
                    try:
                        stdout, stderr = self.current_strategy_process.communicate(timeout=5)
                        if stderr:
                            self.log(f"错误信息: {stderr[:500]}...", "ERROR")
                        if stdout:
                            self.log(f"输出信息: {stdout[-500:]}...", "INFO")
                    except:
                        pass
                
                self.current_strategy_process = None
    
    def run_trading_cycle(self):
        """执行一次完整的交易周期"""
        self.log("🔄 开始新的交易周期")
        
        # 1. 获取BTC价格
        btc_price = self.get_btc_price()
        if not btc_price:
            self.log("❌ 无法获取BTC价格，跳过本次交易", "ERROR")
            return
        
        # 2. 获取可用市场
        markets = self.get_available_markets()
        if not markets:
            self.log("❌ 没有找到可用市场，跳过本次交易", "ERROR")
            return
        
        # 3. 选择第一个可用市场
        selected_market = markets[0]
        market_id = selected_market.get('market_id')
        
        if not market_id:
            self.log("❌ 市场ID无效，跳过本次交易", "ERROR")
            return
        
        self.log(f"🎯 选择市场: {selected_market.get('question', 'Unknown')}")
        
        # 4. 启动交易策略
        success = self.start_trading_strategy(market_id, btc_price)
        if not success:
            self.log("❌ 启动交易策略失败", "ERROR")
            return
        
        self.log("✅ 交易周期启动成功")
    
    def run(self):
        """主运行循环"""
        self.log("🚀 BTC自动交易器启动")
        
        try:
            while self.running:
                # 等待下一个15分钟整点
                self.wait_for_next_15min_interval()
                
                if not self.running:
                    break
                
                # 检查当前策略状态
                self.check_strategy_status()
                
                # 如果没有运行中的策略，启动新的交易周期
                if not self.current_strategy_process or self.current_strategy_process.poll() is not None:
                    self.run_trading_cycle()
                else:
                    self.log("⏸️ 策略仍在运行中，跳过本次周期")
                
                # 等待一分钟再检查
                time.sleep(60)
                
        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
        except Exception as e:
            self.log(f"运行错误: {e}", "ERROR")
        finally:
            self.stop()
    
    def stop(self):
        """停止自动交易器"""
        self.log("🛑 停止BTC自动交易器")
        self.running = False
        
        # 停止当前策略进程
        if self.current_strategy_process and self.current_strategy_process.poll() is None:
            self.log("⚠️ 停止策略进程")
            self.current_strategy_process.terminate()
            try:
                self.current_strategy_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.current_strategy_process.kill()
                self.log("⚠️ 强制终止策略进程")


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if 'trader' in globals():
        trader.stop()
    sys.exit(0)


def main():
    """主函数"""
    print("🤖 BTC 15分钟自动交易定时器")
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
        
        # 创建自动交易器
        global trader
        trader = BTCAutoTrader(trade_amount=trade_amount)
        
        # 启动自动交易
        trader.run()
        
    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        if 'trader' in globals():
            trader.stop()


if __name__ == "__main__":
    main()