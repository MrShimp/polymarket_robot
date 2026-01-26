#!/usr/bin/env python3
"""
BTC 15分钟策略监控面板
实时显示策略状态、价格变化、持仓信息等
"""

import os
import json
import time
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz


class BTCStrategyMonitor:
    """BTC策略监控器"""
    
    def __init__(self):
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.data_dir = "data"
        self.refresh_interval = 5  # 5秒刷新一次
        
        # 监控数据
        self.btc_price = None
        self.price_history = []
        self.current_trades = []
        self.daily_stats = {}
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_beijing_time(self) -> datetime:
        """获取北京时间"""
        return datetime.now(self.beijing_tz)
    
    def get_current_interval(self) -> tuple:
        """获取当前15分钟区间"""
        beijing_time = self.get_beijing_time()
        minute = beijing_time.minute
        interval_start_minute = (minute // 15) * 15
        
        interval_start = beijing_time.replace(
            minute=interval_start_minute, 
            second=0, 
            microsecond=0
        )
        interval_end = interval_start + timedelta(minutes=15)
        
        return interval_start, interval_end
    
    async def get_btc_price(self) -> Optional[float]:
        """获取BTC价格"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            price = float(data['price'])
            
            # 更新价格历史
            self.price_history.append({
                'timestamp': time.time(),
                'price': price,
                'datetime': datetime.now()
            })
            
            # 保持历史记录在合理范围内
            if len(self.price_history) > 60:  # 保留5分钟历史
                self.price_history = self.price_history[-60:]
            
            self.btc_price = price
            return price
            
        except Exception as e:
            print(f"获取BTC价格失败: {e}")
            return None
    
    def load_recent_trades(self) -> List[Dict]:
        """加载最近的交易记录"""
        trades = []
        trades_dir = os.path.join(self.data_dir, "btc_trades")
        
        if not os.path.exists(trades_dir):
            return trades
        
        try:
            # 获取最近的交易文件
            trade_files = [f for f in os.listdir(trades_dir) if f.endswith('.json')]
            trade_files.sort(reverse=True)  # 最新的在前
            
            # 读取最近10个交易记录
            for filename in trade_files[:10]:
                filepath = os.path.join(trades_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    trade_data = json.load(f)
                    trades.append(trade_data)
            
        except Exception as e:
            print(f"加载交易记录失败: {e}")
        
        return trades
    
    def calculate_daily_stats(self, trades: List[Dict]) -> Dict:
        """计算今日统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [
            t for t in trades 
            if t.get('timestamp', '').startswith(today)
        ]
        
        if not today_trades:
            return {
                'total_trades': 0,
                'total_profit': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        profits = [t.get('profit', 0) for t in today_trades]
        winning_trades = [p for p in profits if p > 0]
        
        return {
            'total_trades': len(today_trades),
            'total_profit': sum(profits),
            'win_rate': (len(winning_trades) / len(today_trades)) * 100 if today_trades else 0,
            'avg_profit': sum(profits) / len(profits) if profits else 0,
            'best_trade': max(profits) if profits else 0,
            'worst_trade': min(profits) if profits else 0
        }
    
    def get_price_change_info(self) -> Dict:
        """获取价格变化信息"""
        if len(self.price_history) < 2:
            return {'change': 0, 'change_pct': 0, 'trend': 'stable'}
        
        current_price = self.price_history[-1]['price']
        
        # 1分钟前价格
        one_min_ago = time.time() - 60
        recent_prices = [
            p for p in self.price_history 
            if p['timestamp'] >= one_min_ago
        ]
        
        if not recent_prices:
            return {'change': 0, 'change_pct': 0, 'trend': 'stable'}
        
        old_price = recent_prices[0]['price']
        change = current_price - old_price
        change_pct = (change / old_price) * 100 if old_price > 0 else 0
        
        if change > 5:
            trend = 'up_strong'
        elif change > 1:
            trend = 'up'
        elif change < -5:
            trend = 'down_strong'
        elif change < -1:
            trend = 'down'
        else:
            trend = 'stable'
        
        return {
            'change': change,
            'change_pct': change_pct,
            'trend': trend,
            'old_price': old_price
        }
    
    def format_trend_indicator(self, trend: str) -> str:
        """格式化趋势指示器"""
        indicators = {
            'up_strong': '🚀📈',
            'up': '📈',
            'stable': '➡️',
            'down': '📉',
            'down_strong': '💥📉'
        }
        return indicators.get(trend, '➡️')
    
    def display_header(self):
        """显示头部信息"""
        beijing_time = self.get_beijing_time()
        interval_start, interval_end = self.get_current_interval()
        
        print("🤖 BTC 15分钟策略监控面板")
        print("=" * 80)
        print(f"📅 北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 当前区间: {interval_start.strftime('%H:%M')} - {interval_end.strftime('%H:%M')}")
        
        # 交易时段状态
        hour = beijing_time.hour
        is_trading_hours = 10 <= hour < 19
        status = "🟢 交易时段" if is_trading_hours else "🔴 非交易时段"
        print(f"🕐 交易状态: {status}")
        print()
    
    def display_price_info(self):
        """显示价格信息"""
        if not self.btc_price:
            print("📊 BTC价格: 获取中...")
            return
        
        price_info = self.get_price_change_info()
        trend_icon = self.format_trend_indicator(price_info['trend'])
        
        print("📊 BTC价格信息")
        print("-" * 40)
        print(f"💰 当前价格: ${self.btc_price:,.2f} {trend_icon}")
        
        if price_info['change'] != 0:
            change_color = "🟢" if price_info['change'] > 0 else "🔴"
            print(f"📈 1分钟变化: {change_color} ${price_info['change']:+.2f} ({price_info['change_pct']:+.2f}%)")
        
        # 显示最近价格历史
        if len(self.price_history) >= 5:
            recent_prices = self.price_history[-5:]
            print("📋 最近价格:")
            for p in recent_prices:
                time_str = p['datetime'].strftime('%H:%M:%S')
                print(f"   {time_str}: ${p['price']:,.2f}")
        
        print()
    
    def display_strategy_status(self):
        """显示策略状态"""
        print("🎯 策略状态")
        print("-" * 40)
        
        # 检查是否有活跃的策略进程
        # 这里可以通过检查日志文件或进程来判断
        print("📊 策略参数:")
        print("   入场阈值: 75% 概率")
        print("   止盈目标: 90% 概率")
        print("   止损阈值: 55% 概率")
        print("   特殊止盈: 85% + 30秒横盘")
        print("   价格阈值: ±$30 (缓冲$32)")
        print()
    
    def display_trades_info(self):
        """显示交易信息"""
        trades = self.load_recent_trades()
        stats = self.calculate_daily_stats(trades)
        
        print("💼 交易统计")
        print("-" * 40)
        print(f"📈 今日交易: {stats['total_trades']} 笔")
        print(f"💰 今日盈亏: ${stats['total_profit']:+.2f}")
        print(f"🎯 胜率: {stats['win_rate']:.1f}%")
        
        if stats['total_trades'] > 0:
            print(f"📊 平均盈利: ${stats['avg_profit']:+.2f}")
            print(f"🏆 最佳交易: ${stats['best_trade']:+.2f}")
            print(f"💔 最差交易: ${stats['worst_trade']:+.2f}")
        
        print()
        
        # 显示最近交易
        if trades:
            print("📋 最近交易:")
            for i, trade in enumerate(trades[:3]):
                timestamp = trade.get('timestamp', '')
                if timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                else:
                    time_str = "未知"
                
                outcome = trade.get('outcome', '未知')
                profit = trade.get('profit', 0)
                profit_pct = trade.get('profit_pct', 0)
                exit_reason = trade.get('exit_reason', '未知')
                
                profit_color = "🟢" if profit > 0 else "🔴"
                print(f"   {i+1}. {time_str} {outcome} {profit_color}${profit:+.2f} ({profit_pct:+.1f}%) - {exit_reason}")
        
        print()
    
    def display_footer(self):
        """显示底部信息"""
        print("-" * 80)
        print("🔄 自动刷新中... (Ctrl+C 退出)")
        print(f"⏱️ 刷新间隔: {self.refresh_interval} 秒")
    
    async def run_monitor(self):
        """运行监控"""
        print("🚀 启动BTC策略监控面板...")
        
        try:
            while True:
                # 清屏
                self.clear_screen()
                
                # 获取最新数据
                await self.get_btc_price()
                
                # 显示各个部分
                self.display_header()
                self.display_price_info()
                self.display_strategy_status()
                self.display_trades_info()
                self.display_footer()
                
                # 等待刷新
                await asyncio.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
        except Exception as e:
            print(f"\n❌ 监控错误: {e}")


async def main():
    """主函数"""
    monitor = BTCStrategyMonitor()
    await monitor.run_monitor()


if __name__ == "__main__":
    asyncio.run(main())