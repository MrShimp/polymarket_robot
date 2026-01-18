from typing import Dict, Any
from datetime import datetime, timedelta
from .base_agent import BaseAgent

class RiskAnalysisAgent(BaseAgent):
    """风险分析Agent"""
    
    def __init__(self):
        super().__init__(
            name="RiskAnalyzer",
            description="评估市场风险和交易风险"
        )
    
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析风险因素"""
        if not self.validate_market_data(market_data):
            return {"error": "Invalid market data", "confidence": 0}
        
        condition_id = market_data['condition_id']
        
        analysis_result = {
            "agent": self.name,
            "market_id": condition_id,
            "analysis_type": "risk_assessment",
            "liquidity_risk": self._assess_liquidity_risk(market_data),
            "time_risk": self._assess_time_risk(market_data),
            "volatility_risk": self._assess_volatility_risk(market_data),
            "market_risk": self._assess_market_risk(market_data),
            "overall_risk_score": 0.0,
            "risk_level": "",
            "recommendation": "",
            "confidence": 0.0,
            "reasoning": ""
        }
        
        analysis_result["overall_risk_score"] = self._calculate_overall_risk(analysis_result)
        analysis_result["risk_level"] = self._categorize_risk_level(analysis_result["overall_risk_score"])
        analysis_result["recommendation"] = self._generate_recommendation(analysis_result)
        analysis_result["confidence"] = self._calculate_confidence(analysis_result)
        analysis_result["reasoning"] = self._generate_reasoning(analysis_result)
        
        self.log_analysis(market_data, analysis_result)
        self.store_analysis(analysis_result)
        return analysis_result
    
    def _assess_liquidity_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估流动性风险"""
        orderbook = market_data.get('orderbook', {})
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        # 计算买卖价差
        spread = 0.0
        if bids and asks:
            try:
                best_bid = float(bids[0].get('price', 0))
                best_ask = float(asks[0].get('price', 0))
                spread = abs(best_ask - best_bid) if best_bid and best_ask else 1.0
            except (ValueError, TypeError):
                spread = 1.0
        else:
            spread = 1.0
        
        # 计算订单深度
        total_orders = len(bids) + len(asks)
        
        # 计算前5档总量
        top5_volume = 0
        for order in (bids[:5] + asks[:5]):
            try:
                top5_volume += float(order.get('size', 0))
            except (ValueError, TypeError):
                continue
        
        # 风险评估
        risk_score = 0.0
        if spread > 0.1:  # 价差超过10%
            risk_score += 0.4
        elif spread > 0.05:  # 价差超过5%
            risk_score += 0.2
        
        if total_orders < 5:  # 订单数量太少
            risk_score += 0.3
        elif total_orders < 15:
            risk_score += 0.1
        
        if top5_volume < 100:  # 前5档流动性不足
            risk_score += 0.3
        elif top5_volume < 500:
            risk_score += 0.1
        
        return {
            "spread": spread,
            "total_orders": total_orders,
            "top5_volume": top5_volume,
            "risk_score": min(risk_score, 1.0),
            "risk_level": "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low"
        }
    
    def _assess_time_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估时间风险"""
        end_date_str = market_data.get('end_date_iso')
        
        if not end_date_str:
            return {
                "days_remaining": None,
                "risk_score": 0.5,
                "risk_level": "unknown"
            }
        
        try:
            # 解析结束时间
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            now = datetime.now(end_date.tzinfo)
            days_remaining = (end_date - now).days
            
            # 风险评估
            risk_score = 0.0
            if days_remaining < 0:  # 已过期
                risk_score = 1.0
            elif days_remaining < 1:  # 不到1天
                risk_score = 0.8
            elif days_remaining < 3:  # 不到3天
                risk_score = 0.6
            elif days_remaining < 7:  # 不到1周
                risk_score = 0.4
            elif days_remaining < 30:  # 不到1月
                risk_score = 0.2
            else:  # 超过1月
                risk_score = 0.1
            
            risk_level = "very_high" if risk_score > 0.7 else "high" if risk_score > 0.5 else "medium" if risk_score > 0.3 else "low"
            
            return {
                "days_remaining": days_remaining,
                "risk_score": risk_score,
                "risk_level": risk_level
            }
            
        except Exception:
            return {
                "days_remaining": None,
                "risk_score": 0.5,
                "risk_level": "unknown"
            }
    
    def _assess_volatility_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估波动性风险"""
        prices = market_data.get('prices', {})
        
        if not prices:
            return {
                "price_range": 0.0,
                "risk_score": 0.3,
                "risk_level": "medium"
            }
        
        try:
            price_values = [float(p) for p in prices.values() if p]
            if not price_values:
                return {
                    "price_range": 0.0,
                    "risk_score": 0.3,
                    "risk_level": "medium"
                }
            
            price_range = max(price_values) - min(price_values)
            avg_price = sum(price_values) / len(price_values)
            
            # 相对波动性
            relative_volatility = price_range / avg_price if avg_price > 0 else 0
            
            # 风险评估
            risk_score = 0.0
            if relative_volatility > 0.3:  # 30%以上波动
                risk_score = 0.8
            elif relative_volatility > 0.2:  # 20%以上波动
                risk_score = 0.6
            elif relative_volatility > 0.1:  # 10%以上波动
                risk_score = 0.4
            elif relative_volatility > 0.05:  # 5%以上波动
                risk_score = 0.2
            else:
                risk_score = 0.1
            
            risk_level = "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low"
            
            return {
                "price_range": price_range,
                "relative_volatility": relative_volatility,
                "risk_score": risk_score,
                "risk_level": risk_level
            }
            
        except (ValueError, TypeError):
            return {
                "price_range": 0.0,
                "risk_score": 0.5,
                "risk_level": "medium"
            }
    
    def _assess_market_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估市场风险"""
        # 检查市场状态
        active = market_data.get('active', False)
        closed = market_data.get('closed', False)
        resolution = market_data.get('resolution')
        
        risk_score = 0.0
        
        if closed:
            risk_score = 1.0  # 已关闭市场风险最高
        elif not active:
            risk_score = 0.8  # 非活跃市场风险很高
        elif resolution:
            risk_score = 0.6  # 已有结果但未关闭
        
        # 检查市场问题的复杂性（简单启发式）
        question = market_data.get('question', '').lower()
        if any(word in question for word in ['will', 'when', 'how many', 'what']):
            risk_score += 0.1  # 预测性问题风险稍高
        
        risk_level = "very_high" if risk_score > 0.8 else "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low"
        
        return {
            "active": active,
            "closed": closed,
            "has_resolution": bool(resolution),
            "risk_score": min(risk_score, 1.0),
            "risk_level": risk_level
        }
    
    def _calculate_overall_risk(self, analysis: Dict[str, Any]) -> float:
        """计算综合风险分数"""
        liquidity_risk = analysis.get("liquidity_risk", {}).get("risk_score", 0.5)
        time_risk = analysis.get("time_risk", {}).get("risk_score", 0.5)
        volatility_risk = analysis.get("volatility_risk", {}).get("risk_score", 0.5)
        market_risk = analysis.get("market_risk", {}).get("risk_score", 0.5)
        
        # 加权平均
        weights = {
            "liquidity": 0.3,
            "time": 0.25,
            "volatility": 0.25,
            "market": 0.2
        }
        
        overall_risk = (
            liquidity_risk * weights["liquidity"] +
            time_risk * weights["time"] +
            volatility_risk * weights["volatility"] +
            market_risk * weights["market"]
        )
        
        return min(max(overall_risk, 0.0), 1.0)
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """风险等级分类"""
        if risk_score >= 0.8:
            return "very_high"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "very_low"
    
    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        """生成风险管理推荐"""
        risk_level = analysis.get("risk_level", "medium")
        overall_risk_score = analysis.get("overall_risk_score", 0.5)
        
        if risk_level == "very_high":
            return "AVOID - 风险极高，强烈建议避免"
        elif risk_level == "high":
            return "CAUTION - 高风险，仅限小额试探"
        elif risk_level == "medium":
            return "MODERATE - 中等风险，适度参与"
        elif risk_level == "low":
            return "ACCEPTABLE - 低风险，可正常参与"
        else:
            return "SAFE - 风险很低，相对安全"
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """计算风险评估置信度"""
        base_confidence = 0.7
        
        # 检查数据完整性
        liquidity_data = analysis.get("liquidity_risk", {})
        time_data = analysis.get("time_risk", {})
        volatility_data = analysis.get("volatility_risk", {})
        market_data = analysis.get("market_risk", {})
        
        # 有完整的流动性数据
        if liquidity_data.get("total_orders", 0) > 0:
            base_confidence += 0.1
        
        # 有明确的时间信息
        if time_data.get("days_remaining") is not None:
            base_confidence += 0.1
        
        # 有价格数据
        if volatility_data.get("price_range", 0) > 0:
            base_confidence += 0.1
        
        # 市场状态明确
        if market_data.get("active") is not None:
            base_confidence += 0.1
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_reasoning(self, analysis: Dict[str, Any]) -> str:
        """生成推理说明"""
        reasoning_parts = []
        
        # 各项风险描述
        liquidity_risk = analysis.get("liquidity_risk", {})
        time_risk = analysis.get("time_risk", {})
        volatility_risk = analysis.get("volatility_risk", {})
        market_risk = analysis.get("market_risk", {})
        
        reasoning_parts.append(f"流动性风险: {liquidity_risk.get('risk_level', 'unknown')}")
        reasoning_parts.append(f"时间风险: {time_risk.get('risk_level', 'unknown')}")
        reasoning_parts.append(f"波动性风险: {volatility_risk.get('risk_level', 'unknown')}")
        reasoning_parts.append(f"市场风险: {market_risk.get('risk_level', 'unknown')}")
        
        # 关键风险因素
        if time_risk.get("days_remaining", 999) < 7:
            reasoning_parts.append("临近到期")
        
        if liquidity_risk.get("spread", 0) > 0.1:
            reasoning_parts.append("价差过大")
        
        if not market_risk.get("active", True):
            reasoning_parts.append("市场非活跃状态")
        
        return " | ".join(reasoning_parts)