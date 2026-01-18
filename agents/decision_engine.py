from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DecisionEngine:
    """决策引擎 - 综合所有Agent的分析结果做出最终决策"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 决策参数
        self.min_confidence_threshold = self.config.get('min_confidence', 0.6)
        self.risk_tolerance = self.config.get('risk_tolerance', 'medium')  # low, medium, high
        
        # Agent权重配置
        self.agent_weights = self.config.get('agent_weights', {
            'PriceAnalyzer': 0.4,
            'SentimentAnalyzer': 0.3,
            'RiskAnalyzer': 0.3
        })
        
        logger.info("决策引擎初始化完成")
    
    def make_decision(self, 
                     market_data: Dict[str, Any], 
                     agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于所有Agent分析结果做出交易决策
        
        Args:
            market_data: 市场数据
            agent_results: 各Agent的分析结果
            
        Returns:
            决策结果字典
        """
        try:
            # 验证输入数据
            if not self._validate_inputs(market_data, agent_results):
                return self._create_hold_decision("输入数据无效")
            
            # 提取各Agent的推荐
            recommendations = self._extract_recommendations(agent_results)
            
            # 计算综合置信度
            overall_confidence = self._calculate_overall_confidence(agent_results)
            
            # 风险评估
            risk_assessment = self._assess_overall_risk(agent_results)
            
            # 生成决策
            decision = self._generate_decision(
                recommendations, 
                overall_confidence, 
                risk_assessment,
                market_data
            )
            
            logger.info(f"决策生成完成: {decision.get('action')} (置信度: {decision.get('confidence', 0):.2f})")
            return decision
            
        except Exception as e:
            logger.error(f"决策生成失败: {e}")
            return self._create_hold_decision(f"决策生成错误: {str(e)}")
    
    def _validate_inputs(self, market_data: Dict[str, Any], agent_results: Dict[str, Any]) -> bool:
        """验证输入数据"""
        if not market_data or not agent_results:
            return False
        
        # 检查必要的市场数据
        required_fields = ['condition_id', 'question']
        if not all(field in market_data for field in required_fields):
            return False
        
        # 检查至少有一个Agent的结果
        valid_results = [r for r in agent_results.values() if not r.get('error')]
        return len(valid_results) > 0
    
    def _extract_recommendations(self, agent_results: Dict[str, Any]) -> Dict[str, str]:
        """提取各Agent的推荐"""
        recommendations = {}
        
        for agent_name, result in agent_results.items():
            if not result.get('error'):
                recommendation = result.get('recommendation', 'HOLD')
                recommendations[agent_name] = recommendation
        
        return recommendations
    
    def _calculate_overall_confidence(self, agent_results: Dict[str, Any]) -> float:
        """计算综合置信度"""
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for agent_name, result in agent_results.items():
            if result.get('error'):
                continue
                
            confidence = result.get('confidence', 0)
            weight = self.agent_weights.get(agent_name, 0.33)
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_confidence / total_weight
    
    def _assess_overall_risk(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估综合风险"""
        risk_result = agent_results.get('RiskAnalyzer', {})
        
        if risk_result.get('error'):
            return {
                'risk_level': 'unknown',
                'risk_score': 0.5,
                'risk_factors': []
            }
        
        return {
            'risk_level': risk_result.get('risk_level', 'medium'),
            'risk_score': risk_result.get('overall_risk_score', 0.5),
            'risk_factors': [
                risk_result.get('liquidity_risk', {}),
                risk_result.get('time_risk', {}),
                risk_result.get('volatility_risk', {}),
                risk_result.get('market_risk', {})
            ]
        }
    
    def _generate_decision(self, 
                          recommendations: Dict[str, str],
                          overall_confidence: float,
                          risk_assessment: Dict[str, Any],
                          market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终决策"""
        
        # 统计推荐动作
        action_votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for agent_name, recommendation in recommendations.items():
            weight = self.agent_weights.get(agent_name, 0.33)
            
            if 'BUY' in recommendation.upper():
                if 'STRONG' in recommendation.upper():
                    action_votes['BUY'] += weight * 1.5  # 强烈推荐加权
                else:
                    action_votes['BUY'] += weight
            elif 'SELL' in recommendation.upper():
                if 'STRONG' in recommendation.upper():
                    action_votes['SELL'] += weight * 1.5
                else:
                    action_votes['SELL'] += weight
            else:
                action_votes['HOLD'] += weight
        
        # 确定主要动作
        primary_action = max(action_votes, key=action_votes.get)
        action_strength = action_votes[primary_action]
        
        # 风险调整
        risk_level = risk_assessment.get('risk_level', 'medium')
        risk_score = risk_assessment.get('risk_score', 0.5)
        
        # 应用风险容忍度
        adjusted_action, adjusted_confidence = self._apply_risk_tolerance(
            primary_action, action_strength, overall_confidence, risk_level, risk_score
        )
        
        # 最终置信度检查
        should_execute = (
            adjusted_confidence >= self.min_confidence_threshold and
            adjusted_action != 'HOLD' and
            risk_level not in ['very_high'] or self.risk_tolerance == 'high'
        )
        
        decision = {
            'action': adjusted_action,
            'confidence': adjusted_confidence,
            'should_execute': should_execute,
            'reasoning': self._generate_reasoning(
                recommendations, risk_assessment, action_votes
            ),
            'risk_assessment': risk_assessment,
            'agent_recommendations': recommendations,
            'market_id': market_data.get('condition_id'),
            'timestamp': datetime.now().isoformat()
        }
        
        return decision
    
    def _apply_risk_tolerance(self, 
                            action: str, 
                            action_strength: float,
                            confidence: float, 
                            risk_level: str, 
                            risk_score: float) -> tuple:
        """根据风险容忍度调整决策"""
        
        # 风险惩罚系数
        risk_penalties = {
            'low': {'very_high': 0.1, 'high': 0.3, 'medium': 0.7, 'low': 1.0, 'very_low': 1.0},
            'medium': {'very_high': 0.3, 'high': 0.6, 'medium': 0.8, 'low': 1.0, 'very_low': 1.0},
            'high': {'very_high': 0.6, 'high': 0.8, 'medium': 0.9, 'low': 1.0, 'very_low': 1.0}
        }
        
        penalty = risk_penalties.get(self.risk_tolerance, {}).get(risk_level, 0.5)
        adjusted_confidence = confidence * penalty
        
        # 如果风险过高且容忍度低，强制HOLD
        if (risk_level == 'very_high' and self.risk_tolerance == 'low') or risk_score > 0.9:
            return 'HOLD', adjusted_confidence * 0.5
        
        # 如果置信度太低，改为HOLD
        if adjusted_confidence < 0.3:
            return 'HOLD', adjusted_confidence
        
        return action, adjusted_confidence
    
    def _generate_reasoning(self, 
                          recommendations: Dict[str, str],
                          risk_assessment: Dict[str, Any],
                          action_votes: Dict[str, float]) -> str:
        """生成决策推理"""
        reasoning_parts = []
        
        # Agent推荐总结
        reasoning_parts.append("Agent推荐:")
        for agent, rec in recommendations.items():
            reasoning_parts.append(f"{agent}: {rec}")
        
        # 投票结果
        max_vote = max(action_votes.values())
        winning_action = [k for k, v in action_votes.items() if v == max_vote][0]
        reasoning_parts.append(f"投票结果: {winning_action} ({max_vote:.2f})")
        
        # 风险评估
        risk_level = risk_assessment.get('risk_level', 'unknown')
        reasoning_parts.append(f"风险等级: {risk_level}")
        
        return " | ".join(reasoning_parts)
    
    def _create_hold_decision(self, reason: str) -> Dict[str, Any]:
        """创建HOLD决策"""
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'should_execute': False,
            'reasoning': reason,
            'timestamp': datetime.now().isoformat()
        }