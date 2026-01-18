#!/usr/bin/env python3
"""
高频策略监控面板
Strategy Monitoring Dashboard for High-Frequency Trading
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyMonitor:
    """策略监控器"""
    
    def __init__(self, data_dir: str = "./hf_data"):
        self.data_dir = data_dir
        
    def load_daily_stats(self, date: str = None) -> Dict:
        """加载每日统计"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        filename = f"daily_stats_{date}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}
    
    def load_trades(self, date: str = None) -> List[Dict]:
        """加载交易记录"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        filename = f"trades_{date}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return []
    
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """计算性能指标"""
        if not trades:
            return {}
        
        total_trades = len(trades)
        profitable_trades = 0
        total_profit = 0.0
        max_drawdown = 0.0
        current_drawdown = 0.0
        peak_profit = 0.0
        
        running_profit = 0.0
        
        for trade in trades:
            # 这里需要根据实际的交易结果计算PnL
            # 暂时使用模拟数据
            pnl = (trade.get('target_price', 0) - trade.get('entry_price', 0)) * trade.get('size', 1)
            
            if pnl > 0:
                profitable_trades += 1
            
            total_profit += pnl
            running_profit += pnl
            
            # 计算回撤
            if running_profit > peak_profit:
                peak_profit = running_profit
                current_drawdown = 0
            else:
                current_drawdown = peak_profit - running_profit
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
        
        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit_per_trade,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': self.calculate_sharpe_ratio(trades)
        }
    
    def calculate_sharpe_ratio(self, trades: List[Dict]) -> float:
        """计算夏普比率"""
        if len(trades) < 2:
            return 0.0
        
        # 计算每笔交易的收益率
        returns = []
        for trade in trades:
            entry_price = trade.get('entry_price', 0)
            target_price = trade.get('target_price', 0)
            if entry_price > 0:
                returns.append((target_price - entry_price) / entry_price)
        
        if not returns:
            return 0.0
        
        # 计算平均收益率和标准差
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        # 夏普比率 (假设无风险利率为0)
        return avg_return / std_dev if std_dev > 0 else 0.0
    
    def analyze_price_distribution(self, trades: List[Dict]) -> Dict:
        """分析价格分布"""
        price_ranges = {
            '0.90-0.92': 0,
            '0.92-0.94': 0,
            '0.94-0.96': 0,
            '0.96-0.98': 0,
            '0.98-0.99': 0
        }
        
        for trade in trades:
            price = trade.get('entry_price', 0)
            if 0.90 <= price < 0.92:
                price_ranges['0.90-0.92'] += 1
            elif 0.92 <= price < 0.94:
                price_ranges['0.92-0.94'] += 1
            elif 0.94 <= price < 0.96:
                price_ranges['0.94-0.96'] += 1
            elif 0.96 <= price < 0.98:
                price_ranges['0.96-0.98'] += 1
            elif 0.98 <= price <= 0.99:
                price_ranges['0.98-0.99'] += 1
        
        return price_ranges
    
    def generate_report(self, date: str = None) -> str:
        """生成监控报告"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 加载数据
        daily_stats = self.load_daily_stats(date)
        trades = self.load_trades(date.replace('-', ''))
        
        # 计算指标
        performance = self.calculate_performance_metrics(trades)
        price_dist = self.analyze_price_distribution(trades)
        
        # 生成报告
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    高频策略监控报告                          ║
║                  日期: {date}                           ║
╠══════════════════════════════════════════════════════════════╣
║ 📊 交易统计                                                  ║
║   总交易次数: {performance.get('total_trades', 0):,}                                    ║
║   盈利交易: {performance.get('profitable_trades', 0):,}                                      ║
║   胜率: {performance.get('win_rate', 0):.2f}%                                        ║
║   总利润: ${performance.get('total_profit', 0):.2f}                                    ║
║   平均每笔利润: ${performance.get('avg_profit_per_trade', 0):.4f}                        ║
║                                                              ║
║ 📈 风险指标                                                  ║
║   最大回撤: ${performance.get('max_drawdown', 0):.2f}                                    ║
║   夏普比率: {performance.get('sharpe_ratio', 0):.3f}                                     ║
║                                                              ║
║ 💰 价格分布                                                  ║
║   90¢-92¢: {price_dist.get('0.90-0.92', 0):,} 笔                                      ║
║   92¢-94¢: {price_dist.get('0.92-0.94', 0):,} 笔                                      ║
║   94¢-96¢: {price_dist.get('0.94-0.96', 0):,} 笔                                      ║
║   96¢-98¢: {price_dist.get('0.96-0.98', 0):,} 笔                                      ║
║   98¢-99¢: {price_dist.get('0.98-0.99', 0):,} 笔                                      ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        return report.strip()
    
    def monitor_real_time(self, interval: int = 60):
        """实时监控"""
        logger.info("启动实时监控...")
        
        while True:
            try:
                # 生成报告
                report = self.generate_report()
                
                # 清屏并显示报告
                os.system('clear' if os.name == 'posix' else 'cls')
                print(report)
                print(f"\n最后更新: {datetime.now().strftime('%H:%M:%S')}")
                print("按 Ctrl+C 退出监控")
                
                # 等待
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控错误: {e}")
                time.sleep(10)
    
    def export_report(self, date: str = None, format: str = 'txt'):
        """导出报告"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        report = self.generate_report(date)
        
        filename = f"strategy_report_{date}.{format}"
        filepath = os.path.join(self.data_dir, filename)
        
        os.makedirs(self.data_dir, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"报告已导出到: {filepath}")
        return filepath

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='高频策略监控')
    parser.add_argument('--mode', choices=['report', 'monitor', 'export'], 
                       default='report', help='运行模式')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', type=int, default=60, 
                       help='监控刷新间隔 (秒)')
    
    args = parser.parse_args()
    
    monitor = StrategyMonitor()
    
    if args.mode == 'report':
        print(monitor.generate_report(args.date))
    elif args.mode == 'monitor':
        monitor.monitor_real_time(args.interval)
    elif args.mode == 'export':
        monitor.export_report(args.date)

if __name__ == "__main__":
    main()