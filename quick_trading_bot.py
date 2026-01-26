#!/usr/bin/env python3
"""
快速交易机器人 - 简化版本
输入marketId和yes/no，自动执行交易策略
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from py_clob_client.clob_types import OrderArgs
from trading.polymarket_clob_client import PolymarketCLOBClient


class QuickTradingBot:
    """快速交易机器人"""
    
    def __init__(self):
        self.clob_wrapper = PolymarketCLOBClient(use_testnet=False)
        self.clob_client = self.clob_wrapper.get_client()
        self.gamma_api_base = "https://gamma-api.polymarket.com"
        
        # 交易参数 (根据你的需求)
        self.entry_threshold = 75    # 75%概率入场
        self.take_profit = 90        # 90%止盈
        self.stop_loss = 55          # 55%止损
        self.high_prob_threshold = 86  # 86%高概率阈值
        self.high_prob_wait_time = 330 # 330秒等待时间
        self.profit_points = 3       # 3个点止盈
        
        # 默认交易金额
        self.default_amount = 10.0
    
    def log(self, message: str):
        """简单日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """获取市场信息"""
        try:
            url = f"{self.gamma_api_base}/markets/{market_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            market_data = response.json()
            
            # 解析数据
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
                'question': market_data.get('question'),
                'outcomes': outcomes,
                'prices': outcome_prices,
                'token_ids': clob_token_ids
            }
            
        except Exception as e:
            self.log(f"❌ 获取市场信息失败: {e}")
            return None
    
    def get_current_price(self, token_id: str) -> Optional[float]:
        """获取当前价格"""
        try:
            midpoint = self.clob_client.get_midpoint(token_id)
            return float(midpoint) if midpoint else None
        except:
            return None
    
    def place_order(self, token_id: str, amount: float, side: str = "BUY", price: Optional[float] = None) -> Dict:
        """下单"""
        try:
            if price is None:
                # 市价单
                current_price = self.get_current_price(token_id)
                if not current_price:
                    return {'success': False, 'error': '无法获取价格'}
                shares = amount / current_price
            else:
                shares = amount / price
            
            if price is None:
                # 市价单
                result = self.clob_client.create_market_order(
                    token_id=token_id,
                    size=round(shares, 2),
                    side=side
                )
            else:
                # 限价单
                args = OrderArgs(
                    token_id=token_id,
                    price=round(price, 3),
                    size=round(shares, 2),
                    side=side
                )
                signed_order = self.clob_client.create_order(args)
                result = self.clob_client.post_order(signed_order)
            
            return {
                'success': True,
                'order_id': result.get('orderId'),
                'shares': shares,
                'price': price or current_price
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def run_strategy(self, market_id: str, choice: str, amount: float = None):
        """运行交易策略"""
        if amount is None:
            amount = self.default_amount
        
        self.log(f"🚀 启动交易策略")
        self.log(f"市场: {market_id}")
        self.log(f"选择: {choice.upper()}")
        self.log(f"金额: ${amount}")
        
        # 获取市场信息
        market_info = self.get_market_info(market_id)
        if not market_info:
            return False
        
        self.log(f"📊 {market_info['question']}")
        
        # 确定token_id
        if choice.lower() == 'yes':
            token_index = 0
        elif choice.lower() == 'no':
            token_index = 1
        else:
            self.log("❌ 选择必须是 yes 或 no")
            return False
        
        if token_index >= len(market_info['token_ids']):
            self.log("❌ Token ID不存在")
            return False
        
        token_id = market_info['token_ids'][token_index]
        outcome_name = market_info['outcomes'][token_index]
        
        self.log(f"🎯 交易标的: {outcome_name}")
        self.log(f"Token ID: {token_id}")
        
        # 开始监控和交易
        position = None
        high_prob_start = None
        
        try:
            while True:
                # 获取当前价格
                current_price = self.get_current_price(token_id)
                if not current_price:
                    self.log("⚠️ 无法获取价格，等待...")
                    time.sleep(10)
                    continue
                
                probability = current_price * 100
                
                if position is None:
                    # 还没有持仓，检查入场条件
                    if probability >= self.entry_threshold:
                        # 检查是否需要等待高概率
                        if probability >= self.high_prob_threshold:
                            if high_prob_start is None:
                                high_prob_start = time.time()
                                self.log(f"🔥 高概率{probability:.1f}%，等待{self.high_prob_wait_time}秒")
                            
                            elapsed = time.time() - high_prob_start
                            if elapsed < self.high_prob_wait_time:
                                remaining = self.high_prob_wait_time - elapsed
                                self.log(f"⏳ 等待中... {remaining:.0f}秒")
                                time.sleep(10)
                                continue
                        
                        # 执行入场
                        self.log(f"📈 入场信号: {probability:.1f}% >= {self.entry_threshold}%")
                        
                        result = self.place_order(token_id, amount, "BUY")
                        if result['success']:
                            position = {
                                'entry_price': result['price'],
                                'shares': result['shares'],
                                'entry_time': time.time(),
                                'order_id': result['order_id']
                            }
                            self.log(f"✅ 入场成功: ${result['price']:.3f}, {result['shares']:.2f}份额")
                            high_prob_start = None
                        else:
                            self.log(f"❌ 入场失败: {result['error']}")
                    else:
                        self.log(f"⏸️ 等待入场: {probability:.1f}% < {self.entry_threshold}%")
                        high_prob_start = None
                
                else:
                    # 已有持仓，检查出场条件
                    entry_price = position['entry_price']
                    profit_points = (current_price - entry_price) * 100
                    
                    self.log(f"📊 持仓: {probability:.1f}%, 盈利{profit_points:.1f}点")
                    
                    should_exit = False
                    exit_reason = ""
                    
                    # 检查各种出场条件
                    if probability >= self.take_profit:
                        should_exit = True
                        exit_reason = f"概率止盈 {probability:.1f}%"
                    elif profit_points >= self.profit_points:
                        should_exit = True
                        exit_reason = f"点数止盈 {profit_points:.1f}点"
                    elif probability <= self.stop_loss:
                        should_exit = True
                        exit_reason = f"概率止损 {probability:.1f}%"
                    
                    if should_exit:
                        self.log(f"📉 出场信号: {exit_reason}")
                        
                        result = self.place_order(token_id, 0, "SELL", None)  # 市价卖出
                        if result['success']:
                            final_amount = position['shares'] * current_price
                            profit = final_amount - amount
                            profit_pct = (profit / amount) * 100
                            
                            self.log(f"✅ 出场成功: 盈利${profit:.2f} ({profit_pct:.1f}%)")
                            
                            # 保存交易记录
                            self.save_trade_record(market_id, choice, position, current_price, profit, exit_reason)
                            
                            return True
                        else:
                            self.log(f"❌ 出场失败: {result['error']}")
                
                time.sleep(10)  # 10秒检查一次
                
        except KeyboardInterrupt:
            self.log("🛑 用户中断")
            if position:
                self.log("⚠️ 注意: 仍有持仓，请手动处理")
            return False
        except Exception as e:
            self.log(f"❌ 策略执行错误: {e}")
            return False
    
    def save_trade_record(self, market_id: str, choice: str, position: Dict, exit_price: float, profit: float, exit_reason: str):
        """保存交易记录"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'market_id': market_id,
                'choice': choice,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'shares': position['shares'],
                'profit': profit,
                'profit_pct': (profit / self.default_amount) * 100,
                'exit_reason': exit_reason,
                'duration_minutes': (time.time() - position['entry_time']) / 60
            }
            
            os.makedirs("data/quick_trades", exist_ok=True)
            filename = f"data/quick_trades/trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            
            self.log(f"📁 交易记录: {filename}")
            
        except Exception as e:
            self.log(f"⚠️ 保存记录失败: {e}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python quick_trading_bot.py <market_id> <yes|no> [amount]")
        print("示例: python quick_trading_bot.py 123456 yes 20")
        return
    
    market_id = sys.argv[1]
    choice = sys.argv[2].lower()
    amount = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    
    if choice not in ['yes', 'no']:
        print("❌ 选择必须是 yes 或 no")
        return
    
    print("🤖 快速交易机器人")
    print(f"策略: 75%入场, 90%止盈, 55%止损, 86%等待330s, 3点止盈")
    print("=" * 60)
    
    bot = QuickTradingBot()
    success = bot.run_strategy(market_id, choice, amount)
    
    if success:
        print("🎉 交易完成!")
    else:
        print("❌ 交易失败或中断")


if __name__ == "__main__":
    main()