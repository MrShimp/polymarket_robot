#!/usr/bin/env python3
"""
智能交易机器人
根据概率阈值自动执行交易策略：
- 75%概率以上入场
- 90%止盈
- 55%止损
- 超过86%后等待330秒
- 超过3个点止盈
"""

import sys
import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from threading import Thread, Event
import signal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from py_clob_client.clob_types import OrderArgs
from trading.polymarket_clob_client import PolymarketCLOBClient
from trading.order_manager import OrderManager


class TradingBot:
    """智能交易机器人"""
    
    def __init__(self, use_testnet: bool = False):
        self.clob_wrapper = PolymarketCLOBClient(use_testnet=use_testnet)
        self.clob_client = self.clob_wrapper.get_client()
        self.order_manager = OrderManager(use_testnet=use_testnet)
        self.gamma_api_base = "https://gamma-api.polymarket.com"
        
        # 交易参数
        self.entry_threshold = 0.75  # 75%概率入场
        self.take_profit = 0.90      # 90%止盈
        self.stop_loss = 0.55        # 55%止损
        self.high_prob_threshold = 0.86  # 86%高概率阈值
        self.high_prob_wait_time = 330   # 330秒等待时间
        self.profit_points_threshold = 3  # 3个点止盈
        
        # 状态跟踪
        self.positions = {}  # 持仓记录
        self.running = False
        self.stop_event = Event()
        
        # 日志
        self.log_file = f"data/trading_logs/bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        os.makedirs("data/trading_logs", exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """获取市场信息"""
        try:
            url = f"{self.gamma_api_base}/markets/{market_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            market_data = response.json()
            
            if market_data:
                outcomes = market_data.get('outcomes', '[]')
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                
                outcome_prices = market_data.get('outcomePrices', '[]')
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)
                
                clob_token_ids = market_data.get('clobTokenIds', '[]')
                if isinstance(clob_token_ids, str):
                    clob_token_ids = json.loads(clob_token_ids)
                
                return {
                    'id': market_data.get('id'),
                    'question': market_data.get('question'),
                    'outcomes': outcomes,
                    'outcomePrices': outcome_prices,
                    'clobTokenIds': clob_token_ids,
                    'active': market_data.get('active', True),
                    'acceptingOrders': market_data.get('acceptingOrders', True)
                }
            
            return None
            
        except Exception as e:
            self.log(f"获取市场信息失败: {e}", "ERROR")
            return None
    
    def get_current_price(self, token_id: str) -> Optional[float]:
        """获取当前价格"""
        try:
            midpoint = self.clob_client.get_midpoint(token_id)
            if midpoint:
                return float(midpoint)
            return None
        except Exception as e:
            self.log(f"获取价格失败 {token_id}: {e}", "ERROR")
            return None
    
    def calculate_probability(self, price: float) -> float:
        """将价格转换为概率百分比"""
        return price * 100
    
    def should_enter_position(self, probability: float) -> bool:
        """判断是否应该入场"""
        return probability >= self.entry_threshold * 100
    
    def should_take_profit(self, probability: float) -> bool:
        """判断是否应该止盈"""
        return probability >= self.take_profit * 100
    
    def should_stop_loss(self, probability: float) -> bool:
        """判断是否应该止损"""
        return probability <= self.stop_loss * 100
    
    def should_wait_for_high_prob(self, probability: float) -> bool:
        """判断是否需要等待高概率"""
        return probability >= self.high_prob_threshold * 100
    
    def calculate_profit_points(self, entry_price: float, current_price: float) -> float:
        """计算盈利点数"""
        return (current_price - entry_price) * 100
    
    def place_buy_order(self, token_id: str, amount: float, price: Optional[float] = None) -> Dict:
        """下买单"""
        try:
            if price is None:
                # 市价单
                current_price = self.get_current_price(token_id)
                if not current_price:
                    return {'success': False, 'error': '无法获取当前价格'}
                
                shares = amount / current_price
                result = self.clob_client.create_market_order(
                    token_id=token_id,
                    size=round(shares, 2),
                    side="BUY"
                )
            else:
                # 限价单
                shares = amount / price
                args = OrderArgs(
                    token_id=token_id,
                    price=round(price, 3),
                    size=round(shares, 2),
                    side="BUY"
                )
                signed_order = self.clob_client.create_order(args)
                result = self.clob_client.post_order(signed_order)
            
            return {
                'success': True,
                'order_id': result.get('orderId'),
                'result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def place_sell_order(self, token_id: str, shares: float, price: Optional[float] = None) -> Dict:
        """下卖单"""
        try:
            if price is None:
                # 市价单
                result = self.clob_client.create_market_order(
                    token_id=token_id,
                    size=round(shares, 2),
                    side="SELL"
                )
            else:
                # 限价单
                args = OrderArgs(
                    token_id=token_id,
                    price=round(price, 3),
                    size=round(shares, 2),
                    side="SELL"
                )
                signed_order = self.clob_client.create_order(args)
                result = self.clob_client.post_order(signed_order)
            
            return {
                'success': True,
                'order_id': result.get('orderId'),
                'result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def monitor_position(self, market_id: str, outcome_choice: str, amount: float):
        """监控单个持仓"""
        position_key = f"{market_id}_{outcome_choice}"
        
        # 获取市场信息
        market_info = self.get_market_info(market_id)
        if not market_info:
            self.log(f"无法获取市场信息: {market_id}", "ERROR")
            return
        
        # 确定token_id
        outcomes = market_info.get('outcomes', [])
        token_ids = market_info.get('clobTokenIds', [])
        
        if outcome_choice.lower() == 'yes':
            outcome_index = 0
        elif outcome_choice.lower() == 'no':
            outcome_index = 1
        else:
            self.log(f"无效的选择: {outcome_choice}", "ERROR")
            return
        
        if outcome_index >= len(token_ids):
            self.log(f"Token ID不存在: {outcome_index}", "ERROR")
            return
        
        token_id = token_ids[outcome_index]
        outcome_name = outcomes[outcome_index] if outcome_index < len(outcomes) else outcome_choice
        
        self.log(f"开始监控持仓: {market_info.get('question')} - {outcome_name}")
        self.log(f"Token ID: {token_id}")
        
        # 等待入场信号
        entry_price = None
        entry_time = None
        shares = 0
        high_prob_start_time = None
        
        while self.running and not self.stop_event.is_set():
            try:
                current_price = self.get_current_price(token_id)
                if not current_price:
                    time.sleep(10)
                    continue
                
                probability = self.calculate_probability(current_price)
                
                # 如果还没有持仓
                if entry_price is None:
                    # 检查是否达到入场条件
                    if self.should_enter_position(probability):
                        # 检查是否需要等待高概率
                        if self.should_wait_for_high_prob(probability):
                            if high_prob_start_time is None:
                                high_prob_start_time = datetime.now()
                                self.log(f"概率达到{probability:.1f}%，开始等待{self.high_prob_wait_time}秒")
                            
                            # 检查等待时间
                            wait_time = (datetime.now() - high_prob_start_time).total_seconds()
                            if wait_time < self.high_prob_wait_time:
                                self.log(f"高概率等待中... {wait_time:.0f}/{self.high_prob_wait_time}秒")
                                time.sleep(10)
                                continue
                        
                        # 执行入场
                        self.log(f"入场信号: 概率{probability:.1f}% >= {self.entry_threshold*100}%")
                        
                        result = self.place_buy_order(token_id, amount)
                        if result['success']:
                            entry_price = current_price
                            entry_time = datetime.now()
                            shares = amount / current_price
                            
                            # 记录持仓
                            self.positions[position_key] = {
                                'market_id': market_id,
                                'token_id': token_id,
                                'outcome': outcome_name,
                                'entry_price': entry_price,
                                'entry_time': entry_time,
                                'shares': shares,
                                'amount': amount,
                                'order_id': result.get('order_id')
                            }
                            
                            self.log(f"✅ 入场成功: 价格${entry_price:.3f}, 份额{shares:.2f}")
                            high_prob_start_time = None  # 重置等待时间
                        else:
                            self.log(f"❌ 入场失败: {result.get('error')}", "ERROR")
                    else:
                        if high_prob_start_time:
                            high_prob_start_time = None
                        self.log(f"等待入场信号: 当前概率{probability:.1f}% < {self.entry_threshold*100}%")
                
                else:
                    # 已有持仓，检查止盈止损
                    profit_points = self.calculate_profit_points(entry_price, current_price)
                    
                    self.log(f"持仓监控: 价格${current_price:.3f} ({probability:.1f}%), "
                           f"盈利{profit_points:.1f}点")
                    
                    should_exit = False
                    exit_reason = ""
                    
                    # 检查止盈条件
                    if self.should_take_profit(probability):
                        should_exit = True
                        exit_reason = f"概率止盈: {probability:.1f}% >= {self.take_profit*100}%"
                    
                    # 检查点数止盈
                    elif profit_points >= self.profit_points_threshold:
                        should_exit = True
                        exit_reason = f"点数止盈: {profit_points:.1f}点 >= {self.profit_points_threshold}点"
                    
                    # 检查止损条件
                    elif self.should_stop_loss(probability):
                        should_exit = True
                        exit_reason = f"概率止损: {probability:.1f}% <= {self.stop_loss*100}%"
                    
                    if should_exit:
                        self.log(f"平仓信号: {exit_reason}")
                        
                        result = self.place_sell_order(token_id, shares)
                        if result['success']:
                            final_amount = shares * current_price
                            profit = final_amount - amount
                            profit_pct = (profit / amount) * 100
                            
                            self.log(f"✅ 平仓成功: 盈利${profit:.2f} ({profit_pct:.1f}%)")
                            
                            # 保存交易记录
                            self.save_trade_record(position_key, entry_price, current_price, 
                                                 profit, exit_reason)
                            
                            # 清除持仓
                            if position_key in self.positions:
                                del self.positions[position_key]
                            
                            break
                        else:
                            self.log(f"❌ 平仓失败: {result.get('error')}", "ERROR")
                
                time.sleep(10)  # 10秒检查一次
                
            except Exception as e:
                self.log(f"监控过程出错: {e}", "ERROR")
                time.sleep(30)
        
        self.log(f"停止监控持仓: {position_key}")
    
    def save_trade_record(self, position_key: str, entry_price: float, exit_price: float, 
                         profit: float, exit_reason: str):
        """保存交易记录"""
        try:
            position = self.positions.get(position_key, {})
            
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'market_id': position.get('market_id'),
                'outcome': position.get('outcome'),
                'entry_time': position.get('entry_time').isoformat() if position.get('entry_time') else None,
                'exit_time': datetime.now().isoformat(),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'shares': position.get('shares'),
                'amount': position.get('amount'),
                'profit': profit,
                'profit_pct': (profit / position.get('amount', 1)) * 100,
                'exit_reason': exit_reason,
                'entry_order_id': position.get('order_id')
            }
            
            # 保存到文件
            trades_dir = "data/trades"
            os.makedirs(trades_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{trades_dir}/trade_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(trade_record, f, indent=2, ensure_ascii=False)
            
            self.log(f"交易记录已保存: {filename}")
            
        except Exception as e:
            self.log(f"保存交易记录失败: {e}", "ERROR")
    
    def start_trading(self, market_id: str, outcome_choice: str, amount: float):
        """开始交易"""
        self.log(f"🚀 启动交易机器人")
        self.log(f"市场ID: {market_id}")
        self.log(f"选择: {outcome_choice}")
        self.log(f"金额: ${amount}")
        self.log(f"入场阈值: {self.entry_threshold*100}%")
        self.log(f"止盈阈值: {self.take_profit*100}%")
        self.log(f"止损阈值: {self.stop_loss*100}%")
        self.log(f"高概率等待: {self.high_prob_threshold*100}% / {self.high_prob_wait_time}秒")
        self.log(f"点数止盈: {self.profit_points_threshold}点")
        
        self.running = True
        
        # 启动监控线程
        monitor_thread = Thread(
            target=self.monitor_position,
            args=(market_id, outcome_choice, amount),
            daemon=True
        )
        monitor_thread.start()
        
        try:
            # 等待线程完成或用户中断
            monitor_thread.join()
        except KeyboardInterrupt:
            self.log("收到中断信号，正在停止...")
            self.stop()
    
    def stop(self):
        """停止交易"""
        self.log("🛑 停止交易机器人")
        self.running = False
        self.stop_event.set()
    
    def get_status(self) -> Dict:
        """获取机器人状态"""
        return {
            'running': self.running,
            'positions': len(self.positions),
            'position_details': self.positions
        }


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    if 'bot' in globals():
        bot.stop()
    sys.exit(0)


def main():
    """主函数"""
    print("🤖 Polymarket 智能交易机器人")
    print("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 获取输入参数
        market_id = input("📝 请输入市场ID: ").strip()
        if not market_id:
            print("❌ 市场ID不能为空")
            return
        
        outcome_choice = input("🎯 请选择方向 (yes/no): ").strip().lower()
        if outcome_choice not in ['yes', 'no']:
            print("❌ 请输入 yes 或 no")
            return
        
        try:
            amount = float(input("💰 请输入交易金额 (USDC): ").strip())
            if amount <= 0:
                print("❌ 金额必须大于0")
                return
        except ValueError:
            print("❌ 金额格式错误")
            return
        
        # 创建机器人
        global bot
        bot = TradingBot(use_testnet=False)
        
        # 验证市场
        market_info = bot.get_market_info(market_id)
        if not market_info:
            print(f"❌ 未找到市场: {market_id}")
            return
        
        print(f"\n📊 市场信息:")
        print(f"   问题: {market_info.get('question')}")
        print(f"   选择: {outcome_choice.upper()}")
        print(f"   金额: ${amount}")
        
        confirm = input(f"\n❓ 确认启动交易机器人? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ 已取消")
            return
        
        # 启动交易
        bot.start_trading(market_id, outcome_choice, amount)
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        if 'bot' in globals():
            bot.stop()


if __name__ == "__main__":
    main()