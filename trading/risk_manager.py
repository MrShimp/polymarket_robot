#!/usr/bin/env python3
"""
风险管理模块
Risk Management Module for High-Frequency Strategy
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class RiskMetrics:
    """风险指标"""
    daily_pnl: float
    daily_loss: float
    consecutive_losses: int
    max_drawdown: float
    position_count: int
    concentration_risk: float
    volatility: float
    var_95: float  # 95% VaR
    risk_level: RiskLevel

class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trade_history: List[Dict] = []
        self.position_history: List[Dict] = []
        self.risk_alerts: List[Dict] = []
        
    def assess_market_risk(self, opportunity: Dict) -> Tuple[float, str]:
        """评估市场风险"""
        risk_score = 0.0
        risk_factors = []
        
        # 价格风险 - 价格越接近边界，风险越高
        price = opportunity.get('current_price', 0)
        if price > 0.98:
            risk_score += 0.3
            risk_factors.append("价格接近上限")
        elif price < 0.91:
            risk_score += 0.2
            risk_factors.append("价格较低")
        
        # 价差风险
        spread = opportunity.get('spread', 0)
        if spread > 0.03:
            risk_score += 0.2
            risk_factors.append("价差较大")
        
        # 流动性风险
        volume = opportunity.get('volume', 0)
        if volume < self.config.get('min_volume', 1000):
            risk_score += 0.3
            risk_factors.append("流动性不足")
        
        # 时间风险 - 接近市场关闭时间
        now = datetime.now()
        if now.hour >= 16:  # 接近17:00关闭
            risk_score += 0.1
            risk_factors.append("接近收盘")
        
        # 置信度风险
        confidence = opportunity.get('confidence', 0)
        if confidence < 0.97:
            risk_score += 0.2
            risk_factors.append("置信度不足")
        
        risk_description = "; ".join(risk_factors) if risk_factors else "风险较低"
        
        return min(1.0, risk_score), risk_description
    
    def calculate_position_size(self, opportunity: Dict, account_balance: float) -> int:
        """计算仓位大小"""
        base_size = self.config.get('position_size', 1)
        
        # 基于风险调整仓位
        risk_score, _ = self.assess_market_risk(opportunity)
        
        # 风险越高，仓位越小
        risk_multiplier = max(0.1, 1.0 - risk_score)
        
        # 基于账户余额调整
        max_risk_per_trade = account_balance * 0.001  # 每笔交易最大风险0.1%
        max_size = int(max_risk_per_trade / (opportunity.get('current_price', 1) * 0.05))  # 假设5%止损
        
        adjusted_size = min(int(base_size * risk_multiplier), max_size)
        
        return max(1, adjusted_size)
    
    def check_position_limits(self, current_positions: Dict) -> bool:
        """检查仓位限制"""
        max_positions = self.config.get('max_positions', 100)
        
        if len(current_positions) >= max_positions:
            logger.warning(f"达到最大仓位限制: {len(current_positions)}/{max_positions}")
            return False
        
        # 检查单一市场集中度
        market_concentration = {}
        for position in current_positions.values():
            market_id = position.get('market_id', 'unknown')
            market_concentration[market_id] = market_concentration.get(market_id, 0) + 1
        
        max_per_market = max(5, max_positions // 10)  # 单一市场最多10%仓位
        for market_id, count in market_concentration.items():
            if count >= max_per_market:
                logger.warning(f"市场 {market_id} 仓位过于集中: {count}")
                return False
        
        return True
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """计算风险价值 (VaR)"""
        if len(returns) < 10:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        
        return abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
    
    def calculate_risk_metrics(self, positions: Dict, trades: List[Dict]) -> RiskMetrics:
        """计算风险指标"""
        # 计算当日PnL
        daily_pnl = sum(pos.get('pnl', 0) for pos in positions.values())
        
        # 计算当日亏损
        daily_loss = sum(abs(pos.get('pnl', 0)) for pos in positions.values() if pos.get('pnl', 0) < 0)
        
        # 计算连续亏损
        consecutive_losses = 0
        for trade in reversed(trades[-20:]):  # 检查最近20笔交易
            if trade.get('pnl', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        # 计算最大回撤
        max_drawdown = self.calculate_max_drawdown(trades)
        
        # 计算集中度风险
        concentration_risk = self.calculate_concentration_risk(positions)
        
        # 计算波动率
        returns = [trade.get('return', 0) for trade in trades[-100:]]  # 最近100笔交易
        volatility = self.calculate_volatility(returns)
        
        # 计算VaR
        var_95 = self.calculate_var(returns, 0.95)
        
        # 确定风险等级
        risk_level = self.determine_risk_level(daily_loss, consecutive_losses, max_drawdown, volatility)
        
        return RiskMetrics(
            daily_pnl=daily_pnl,
            daily_loss=daily_loss,
            consecutive_losses=consecutive_losses,
            max_drawdown=max_drawdown,
            position_count=len(positions),
            concentration_risk=concentration_risk,
            volatility=volatility,
            var_95=var_95,
            risk_level=risk_level
        )
    
    def calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """计算最大回撤"""
        if not trades:
            return 0.0
        
        running_pnl = 0.0
        peak_pnl = 0.0
        max_drawdown = 0.0
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            running_pnl += pnl
            
            if running_pnl > peak_pnl:
                peak_pnl = running_pnl
            
            drawdown = peak_pnl - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def calculate_concentration_risk(self, positions: Dict) -> float:
        """计算集中度风险"""
        if not positions:
            return 0.0
        
        # 按市场分组
        market_exposure = {}
        total_exposure = 0.0
        
        for position in positions.values():
            market_id = position.get('market_id', 'unknown')
            exposure = position.get('size', 0) * position.get('current_price', 0)
            market_exposure[market_id] = market_exposure.get(market_id, 0) + exposure
            total_exposure += exposure
        
        if total_exposure == 0:
            return 0.0
        
        # 计算赫芬达尔指数 (Herfindahl Index)
        hhi = sum((exposure / total_exposure) ** 2 for exposure in market_exposure.values())
        
        return hhi
    
    def calculate_volatility(self, returns: List[float]) -> float:
        """计算波动率"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        
        return variance ** 0.5
    
    def determine_risk_level(self, daily_loss: float, consecutive_losses: int, 
                           max_drawdown: float, volatility: float) -> RiskLevel:
        """确定风险等级"""
        risk_score = 0
        
        # 每日亏损风险
        max_daily_loss = self.config.get('max_daily_loss', 500)
        if daily_loss > max_daily_loss * 0.8:
            risk_score += 3
        elif daily_loss > max_daily_loss * 0.5:
            risk_score += 2
        elif daily_loss > max_daily_loss * 0.3:
            risk_score += 1
        
        # 连续亏损风险
        max_consecutive = self.config.get('max_consecutive_losses', 10)
        if consecutive_losses > max_consecutive * 0.8:
            risk_score += 3
        elif consecutive_losses > max_consecutive * 0.5:
            risk_score += 2
        elif consecutive_losses > max_consecutive * 0.3:
            risk_score += 1
        
        # 回撤风险
        if max_drawdown > 200:
            risk_score += 3
        elif max_drawdown > 100:
            risk_score += 2
        elif max_drawdown > 50:
            risk_score += 1
        
        # 波动率风险
        if volatility > 0.1:
            risk_score += 2
        elif volatility > 0.05:
            risk_score += 1
        
        # 确定风险等级
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def should_halt_trading(self, risk_metrics: RiskMetrics) -> Tuple[bool, str]:
        """判断是否应该暂停交易"""
        reasons = []
        
        # 每日亏损限制
        if risk_metrics.daily_loss >= self.config.get('max_daily_loss', 500):
            reasons.append("达到每日最大亏损限制")
        
        # 连续亏损限制
        if risk_metrics.consecutive_losses >= self.config.get('max_consecutive_losses', 10):
            reasons.append("达到连续亏损限制")
        
        # 风险等级过高
        if risk_metrics.risk_level == RiskLevel.CRITICAL:
            reasons.append("风险等级过高")
        
        # 波动率过高
        if risk_metrics.volatility > 0.15:
            reasons.append("市场波动率过高")
        
        # VaR过高
        if risk_metrics.var_95 > 50:
            reasons.append("风险价值过高")
        
        should_halt = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else ""
        
        return should_halt, reason
    
    def generate_risk_alert(self, risk_metrics: RiskMetrics) -> Optional[Dict]:
        """生成风险警报"""
        alert = None
        
        if risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'level': risk_metrics.risk_level.value,
                'message': f"风险等级: {risk_metrics.risk_level.value}",
                'metrics': {
                    'daily_loss': risk_metrics.daily_loss,
                    'consecutive_losses': risk_metrics.consecutive_losses,
                    'max_drawdown': risk_metrics.max_drawdown,
                    'volatility': risk_metrics.volatility,
                    'var_95': risk_metrics.var_95
                }
            }
            
            self.risk_alerts.append(alert)
            logger.warning(f"风险警报: {alert['message']}")
        
        return alert
    
    def get_trading_recommendations(self, risk_metrics: RiskMetrics) -> List[str]:
        """获取交易建议"""
        recommendations = []
        
        if risk_metrics.risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "减少仓位大小",
                "提高止损标准",
                "增加筛选条件严格程度"
            ])
        
        elif risk_metrics.risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "立即暂停交易",
                "平仓所有亏损仓位",
                "重新评估策略参数"
            ])
        
        if risk_metrics.concentration_risk > 0.3:
            recommendations.append("降低仓位集中度")
        
        if risk_metrics.consecutive_losses > 5:
            recommendations.append("检查市场环境变化")
        
        if risk_metrics.volatility > 0.1:
            recommendations.append("等待市场稳定")
        
        return recommendations
    
    def save_risk_report(self, risk_metrics: RiskMetrics, filepath: str):
        """保存风险报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'risk_metrics': {
                'daily_pnl': risk_metrics.daily_pnl,
                'daily_loss': risk_metrics.daily_loss,
                'consecutive_losses': risk_metrics.consecutive_losses,
                'max_drawdown': risk_metrics.max_drawdown,
                'position_count': risk_metrics.position_count,
                'concentration_risk': risk_metrics.concentration_risk,
                'volatility': risk_metrics.volatility,
                'var_95': risk_metrics.var_95,
                'risk_level': risk_metrics.risk_level.value
            },
            'recommendations': self.get_trading_recommendations(risk_metrics),
            'recent_alerts': self.risk_alerts[-10:]  # 最近10个警报
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"风险报告已保存到: {filepath}")

def main():
    """测试风险管理器"""
    config = {
        'position_size': 1,
        'max_positions': 100,
        'max_daily_loss': 500,
        'max_consecutive_losses': 10,
        'min_volume': 1000
    }
    
    risk_manager = RiskManager(config)
    
    # 模拟交易数据
    trades = [
        {'pnl': 2.5, 'return': 0.025},
        {'pnl': -1.2, 'return': -0.012},
        {'pnl': 3.1, 'return': 0.031},
        {'pnl': -2.8, 'return': -0.028},
        {'pnl': 1.9, 'return': 0.019}
    ]
    
    positions = {
        'token1': {'pnl': 2.5, 'size': 10, 'current_price': 0.95, 'market_id': 'market1'},
        'token2': {'pnl': -1.2, 'size': 5, 'current_price': 0.92, 'market_id': 'market2'}
    }
    
    # 计算风险指标
    risk_metrics = risk_manager.calculate_risk_metrics(positions, trades)
    
    print(f"风险等级: {risk_metrics.risk_level.value}")
    print(f"每日PnL: ${risk_metrics.daily_pnl:.2f}")
    print(f"波动率: {risk_metrics.volatility:.4f}")
    print(f"VaR 95%: ${risk_metrics.var_95:.2f}")
    
    # 检查是否应该暂停交易
    should_halt, reason = risk_manager.should_halt_trading(risk_metrics)
    if should_halt:
        print(f"建议暂停交易: {reason}")
    
    # 获取交易建议
    recommendations = risk_manager.get_trading_recommendations(risk_metrics)
    if recommendations:
        print("交易建议:")
        for rec in recommendations:
            print(f"  - {rec}")

if __name__ == "__main__":
    main()