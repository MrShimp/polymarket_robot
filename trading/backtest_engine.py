#!/usr/bin/env python3
"""
回测引擎
Backtesting Engine for High-Frequency Strategy
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    """回测结果"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_trade_duration: float
    daily_returns: List[float]
    equity_curve: List[float]
    trade_log: List[Dict]

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trade_log = []
        self.daily_pnl = []
        self.equity_curve = [initial_capital]
        
    def load_historical_data(self, filepath: str) -> pd.DataFrame:
        """加载历史数据"""
        try:
            # 假设数据格式为CSV，包含时间戳、代币ID、价格等信息
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df.sort_values('timestamp')
        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
            return pd.DataFrame()
    
    def generate_synthetic_data(self, days: int = 30) -> pd.DataFrame:
        """生成合成数据用于测试"""
        np.random.seed(42)
        
        # 生成时间序列
        start_date = datetime.now() - timedelta(days=days)
        timestamps = pd.date_range(start_date, periods=days*24*60, freq='1min')  # 每分钟一个数据点
        
        data = []
        
        # 生成多个代币的价格数据
        for token_id in range(100):  # 100个代币
            base_price = np.random.uniform(0.90, 0.99)  # 基础价格在90¢-99¢之间
            
            for i, timestamp in enumerate(timestamps):
                # 添加随机波动
                price_change = np.random.normal(0, 0.001)  # 小幅波动
                current_price = max(0.85, min(0.995, base_price + price_change))
                
                # 模拟订单簿数据
                spread = np.random.uniform(0.001, 0.01)
                volume = np.random.randint(100, 5000)
                
                # 模拟市场问题和结果
                market_questions = [
                    f"Will Team A beat Team B in match {token_id}?",
                    f"Will stock XYZ close above $100 on date {token_id}?",
                    f"Will candidate win election {token_id}?",
                    f"Will event happen before deadline {token_id}?"
                ]
                
                data.append({
                    'timestamp': timestamp,
                    'token_id': f'token_{token_id}',
                    'market_id': f'market_{token_id // 2}',  # 每个市场2个代币
                    'price': current_price,
                    'spread': spread,
                    'volume': volume,
                    'market_question': market_questions[token_id % len(market_questions)],
                    'outcome': 'Yes' if token_id % 2 == 0 else 'No'
                })
                
                # 更新基础价格（随机游走）
                base_price += np.random.normal(0, 0.0001)
                base_price = max(0.85, min(0.995, base_price))
        
        return pd.DataFrame(data)
    
    def simulate_strategy(self, data: pd.DataFrame, config: Dict) -> BacktestResult:
        """模拟策略执行"""
        logger.info("开始回测模拟...")
        
        # 重置状态
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trade_log = []
        self.daily_pnl = []
        self.equity_curve = [self.initial_capital]
        
        # 按时间分组处理数据
        grouped_data = data.groupby(data['timestamp'].dt.date)
        
        for date, day_data in grouped_data:
            daily_trades = 0
            daily_pnl = 0.0
            
            # 按时间顺序处理每天的数据
            for _, row in day_data.iterrows():
                # 检查交易限制
                if daily_trades >= config.get('max_daily_trades', 27000):
                    break
                
                # 筛选交易机会
                opportunity = self.evaluate_opportunity(row, config)
                if opportunity:
                    # 执行交易
                    trade_result = self.execute_backtest_trade(opportunity, config)
                    if trade_result:
                        daily_trades += 1
                        daily_pnl += trade_result.get('pnl', 0)
                        self.trade_log.append(trade_result)
                
                # 管理现有仓位
                self.manage_backtest_positions(row, config)
            
            # 记录每日PnL
            self.daily_pnl.append(daily_pnl)
            self.current_capital += daily_pnl
            self.equity_curve.append(self.current_capital)
        
        # 计算回测结果
        return self.calculate_backtest_results()
    
    def evaluate_opportunity(self, row: pd.Series, config: Dict) -> Optional[Dict]:
        """评估交易机会"""
        price = row['price']
        spread = row['spread']
        volume = row['volume']
        
        # 价格筛选
        if not (config.get('min_price', 0.90) <= price <= config.get('max_price', 0.99)):
            return None
        
        # 价差筛选
        if spread > config.get('max_spread', 0.05):
            return None
        
        # 流动性筛选
        if volume < config.get('min_volume', 1000):
            return None
        
        # 计算置信度（简化版本）
        confidence = self.calculate_simple_confidence(price, spread, volume)
        if confidence < config.get('min_confidence', 0.95):
            return None
        
        return {
            'token_id': row['token_id'],
            'market_id': row['market_id'],
            'timestamp': row['timestamp'],
            'current_price': price,
            'target_price': min(0.99, price * (1 + config.get('target_profit_pct', 0.02))),
            'confidence': confidence,
            'volume': volume,
            'spread': spread,
            'market_question': row['market_question'],
            'outcome': row['outcome']
        }
    
    def calculate_simple_confidence(self, price: float, spread: float, volume: int) -> float:
        """计算简化的置信度"""
        # 基于价格的置信度
        price_conf = price
        
        # 基于价差的置信度
        spread_conf = max(0, 1 - spread * 20)
        
        # 基于流动性的置信度
        volume_conf = min(1.0, volume / 5000)
        
        return (price_conf * 0.5 + spread_conf * 0.3 + volume_conf * 0.2)
    
    def execute_backtest_trade(self, opportunity: Dict, config: Dict) -> Optional[Dict]:
        """执行回测交易"""
        token_id = opportunity['token_id']
        
        # 检查是否已有该代币的仓位
        if token_id in self.positions:
            return None
        
        # 检查资金充足
        position_size = config.get('position_size', 1)
        required_capital = position_size * opportunity['current_price']
        
        if required_capital > self.current_capital * 0.1:  # 单笔交易不超过10%资金
            return None
        
        # 创建仓位
        entry_time = opportunity['timestamp']
        entry_price = opportunity['current_price']
        target_price = opportunity['target_price']
        stop_loss = entry_price * (1 - config.get('stop_loss_pct', 0.05))
        
        position = {
            'token_id': token_id,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'size': position_size,
            'market_question': opportunity['market_question']
        }
        
        self.positions[token_id] = position
        
        return {
            'type': 'ENTRY',
            'token_id': token_id,
            'timestamp': entry_time,
            'price': entry_price,
            'size': position_size,
            'side': 'BUY',
            'pnl': 0
        }
    
    def manage_backtest_positions(self, row: pd.Series, config: Dict):
        """管理回测仓位"""
        current_time = row['timestamp']
        current_price = row['price']
        token_id = row['token_id']
        
        if token_id not in self.positions:
            return
        
        position = self.positions[token_id]
        
        # 计算持仓时间
        hold_duration = (current_time - position['entry_time']).total_seconds() / 3600  # 小时
        
        # 检查退出条件
        exit_reason = None
        exit_price = current_price
        
        # 止盈
        if current_price >= position['target_price']:
            exit_reason = 'PROFIT'
        
        # 止损
        elif current_price <= position['stop_loss']:
            exit_reason = 'STOP_LOSS'
        
        # 时间止损（持仓超过24小时）
        elif hold_duration > 24:
            exit_reason = 'TIME_LIMIT'
        
        # 随机退出（模拟市场解决）
        elif np.random.random() < 0.001:  # 0.1%概率随机解决
            exit_reason = 'RESOLVED'
            # 根据价格确定最终结果
            if current_price > 0.95:
                exit_price = 1.0  # 获胜
            else:
                exit_price = 0.0  # 失败
        
        if exit_reason:
            # 平仓
            pnl = (exit_price - position['entry_price']) * position['size']
            
            trade_result = {
                'type': 'EXIT',
                'token_id': token_id,
                'timestamp': current_time,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'size': position['size'],
                'side': 'SELL',
                'pnl': pnl,
                'hold_duration': hold_duration,
                'exit_reason': exit_reason,
                'market_question': position['market_question']
            }
            
            self.trade_log.append(trade_result)
            del self.positions[token_id]
    
    def calculate_backtest_results(self) -> BacktestResult:
        """计算回测结果"""
        if not self.trade_log:
            return BacktestResult(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_return=0, max_drawdown=0,
                sharpe_ratio=0, sortino_ratio=0, profit_factor=0,
                avg_trade_duration=0, daily_returns=[], equity_curve=[],
                trade_log=[]
            )
        
        # 筛选平仓交易
        exit_trades = [t for t in self.trade_log if t['type'] == 'EXIT']
        
        total_trades = len(exit_trades)
        winning_trades = len([t for t in exit_trades if t['pnl'] > 0])
        losing_trades = len([t for t in exit_trades if t['pnl'] < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in exit_trades)
        total_return = (total_pnl / self.initial_capital) * 100
        
        # 计算最大回撤
        max_drawdown = self.calculate_max_drawdown()
        
        # 计算夏普比率
        daily_returns = self.calculate_daily_returns()
        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns)
        
        # 计算索提诺比率
        sortino_ratio = self.calculate_sortino_ratio(daily_returns)
        
        # 计算盈亏比
        profit_factor = self.calculate_profit_factor(exit_trades)
        
        # 计算平均持仓时间
        avg_duration = np.mean([t['hold_duration'] for t in exit_trades]) if exit_trades else 0
        
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_trade_duration=avg_duration,
            daily_returns=daily_returns,
            equity_curve=self.equity_curve,
            trade_log=self.trade_log
        )
    
    def calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        peak = self.equity_curve[0]
        max_dd = 0.0
        
        for value in self.equity_curve[1:]:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def calculate_daily_returns(self) -> List[float]:
        """计算每日收益率"""
        if len(self.equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
            returns.append(ret)
        
        return returns
    
    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        return (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
    
    def calculate_sortino_ratio(self, returns: List[float]) -> float:
        """计算索提诺比率"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return float('inf')
        
        downside_std = np.std(negative_returns)
        
        return (mean_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
    
    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """计算盈亏比"""
        gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def generate_report(self, result: BacktestResult) -> str:
        """生成回测报告"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                        回测报告                              ║
╠══════════════════════════════════════════════════════════════╣
║ 📊 交易统计                                                  ║
║   总交易次数: {result.total_trades:,}                                        ║
║   盈利交易: {result.winning_trades:,}                                          ║
║   亏损交易: {result.losing_trades:,}                                          ║
║   胜率: {result.win_rate:.2f}%                                       ║
║                                                              ║
║ 💰 收益指标                                                  ║
║   总收益率: {result.total_return:.2f}%                                      ║
║   最大回撤: {result.max_drawdown:.2f}%                                      ║
║   夏普比率: {result.sharpe_ratio:.3f}                                       ║
║   索提诺比率: {result.sortino_ratio:.3f}                                     ║
║   盈亏比: {result.profit_factor:.2f}                                        ║
║                                                              ║
║ ⏱️  时间指标                                                  ║
║   平均持仓时间: {result.avg_trade_duration:.2f} 小时                          ║
║   初始资金: ${self.initial_capital:,.2f}                                   ║
║   最终资金: ${self.equity_curve[-1]:,.2f}                                   ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        return report.strip()
    
    def plot_results(self, result: BacktestResult, save_path: str = None):
        """绘制回测结果图表"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 资金曲线
        ax1.plot(result.equity_curve)
        ax1.set_title('资金曲线')
        ax1.set_xlabel('天数')
        ax1.set_ylabel('资金 ($)')
        ax1.grid(True)
        
        # 每日收益分布
        ax2.hist(result.daily_returns, bins=50, alpha=0.7)
        ax2.set_title('每日收益分布')
        ax2.set_xlabel('收益率')
        ax2.set_ylabel('频次')
        ax2.grid(True)
        
        # 交易PnL分布
        exit_trades = [t for t in result.trade_log if t['type'] == 'EXIT']
        pnls = [t['pnl'] for t in exit_trades]
        
        ax3.hist(pnls, bins=50, alpha=0.7)
        ax3.set_title('交易PnL分布')
        ax3.set_xlabel('PnL ($)')
        ax3.set_ylabel('频次')
        ax3.grid(True)
        
        # 胜率随时间变化
        cumulative_wins = []
        cumulative_total = []
        win_rates = []
        
        wins = 0
        total = 0
        
        for trade in exit_trades:
            total += 1
            if trade['pnl'] > 0:
                wins += 1
            
            cumulative_wins.append(wins)
            cumulative_total.append(total)
            win_rates.append(wins / total * 100)
        
        ax4.plot(win_rates)
        ax4.set_title('胜率随时间变化')
        ax4.set_xlabel('交易次数')
        ax4.set_ylabel('胜率 (%)')
        ax4.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {save_path}")
        
        plt.show()

def main():
    """主函数 - 运行回测示例"""
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=10000)
    
    # 生成测试数据
    logger.info("生成合成数据...")
    data = engine.generate_synthetic_data(days=7)  # 7天数据
    
    # 策略配置
    config = {
        'min_price': 0.90,
        'max_price': 0.99,
        'min_confidence': 0.95,
        'position_size': 10,
        'max_positions': 100,
        'target_profit_pct': 0.02,
        'stop_loss_pct': 0.05,
        'max_daily_trades': 1000,  # 降低用于测试
        'min_volume': 1000,
        'max_spread': 0.05
    }
    
    # 运行回测
    logger.info("开始回测...")
    result = engine.simulate_strategy(data, config)
    
    # 生成报告
    report = engine.generate_report(result)
    print(report)
    
    # 保存详细结果
    with open('backtest_result.json', 'w') as f:
        json.dump({
            'config': config,
            'results': {
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': result.win_rate,
                'total_return': result.total_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'sortino_ratio': result.sortino_ratio,
                'profit_factor': result.profit_factor,
                'avg_trade_duration': result.avg_trade_duration
            }
        }, f, indent=2)
    
    logger.info("回测完成，结果已保存到 backtest_result.json")
    
    # 绘制图表（需要matplotlib）
    try:
        engine.plot_results(result, 'backtest_charts.png')
    except ImportError:
        logger.warning("matplotlib未安装，跳过图表生成")

if __name__ == "__main__":
    main()