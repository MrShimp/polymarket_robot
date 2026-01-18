from typing import Dict, Any
from .base_agent import BaseAgent

class SentimentAnalysisAgent(BaseAgent):
    """市场情绪分析Agent"""
    
    def __init__(self):
        super().__init__(
            name="SentimentAnalyzer",
            description="分析市场情绪和交易活动"
        )
    
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场情绪"""
        if not self.validate_market_data(market_data):
            return {"error": "Invalid market data", "confidence": 0}
        
        condition_id = market_data['condition_id']
        orderbook = market_data.get('orderbook', {})
        
        analysis_result = {
            "agent": self.name,
            "market_id": condition_id,
            "analysis_type": "sentiment",
            "trading_volume": self._analyze_volume(orderbook),
            "market_depth": self._analyze_market_depth(orderbook),
            "bid_ask_ratio": self._calculate_bid_ask_ratio(orderbook),
            "sentiment_score": self._calculate_sentiment_score(orderbook),
            "market_activity": self._assess_market_activity(orderbook),
            "recommendation": "",
            "confidence": 0.0,
            "reasoning": ""
        }
        
        analysis_result["recommendation"] = self._generate_recommendation(analysis_result)
        analysis_result["confidence"] = self._calculate_confidence(analysis_result)
        analysis_result["reasoning"] = self._generate_reasoning(analysis_result)
        
        self.log_analysis(market_data, analysis_result)
        self.store_analysis(analysis_result)
        return analysis_result
    
    def _analyze_volume(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """分析交易量"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        bid_volume = sum(float(bid.get('size', 0)) for bid in bids[:10])
        ask_volume = sum(float(ask.get('size', 0)) for ask in asks[:10])
        total_volume = bid_volume + ask_volume
        
        volume_level = "low"
        if total_volume > 10000:
            volume_level = "very_high"
        elif total_volume > 5000:
            volume_level = "high"
        elif total_volume > 1000:
            volume_level = "medium"
        
        return {
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "total_volume": total_volume,
            "volume_level": volume_level
        }
    
    def _analyze_market_depth(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场深度"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        bid_levels = len(bids)
        ask_levels = len(asks)
        total_levels = bid_levels + ask_levels
        
        # 计算价差
        spread = 0.0
        if bids and asks:
            try:
                best_bid = float(bids[0].get('price', 0))
                best_ask = float(asks[0].get('price', 0))
                spread = abs(best_ask - best_bid) if best_bid and best_ask else 0
            except (ValueError, TypeError):
                spread = 0.0
        
        depth_quality = "poor"
        if total_levels > 50 and spread < 0.02:
            depth_quality = "excellent"
        elif total_levels > 30 and spread < 0.05:
            depth_quality = "good"
        elif total_levels > 10 and spread < 0.1:
            depth_quality = "fair"
        
        return {
            "bid_levels": bid_levels,
            "ask_levels": ask_levels,
            "total_levels": total_levels,
            "spread": spread,
            "depth_quality": depth_quality
        }
    
    def _calculate_bid_ask_ratio(self, orderbook: Dict[str, Any]) -> float:
        """计算买卖比例"""
        volume_data = self._analyze_volume(orderbook)
        bid_volume = volume_data["bid_volume"]
        ask_volume = volume_data["ask_volume"]
        
        if ask_volume == 0:
            return 1.0 if bid_volume > 0 else 0.5
        
        return bid_volume / (bid_volume + ask_volume)
    
    def _calculate_sentiment_score(self, orderbook: Dict[str, Any]) -> float:
        """计算情绪分数 (-1到1，-1最悲观，1最乐观)"""
        bid_ask_ratio = self._calculate_bid_ask_ratio(orderbook)
        
        # 将比例转换为情绪分数
        # 0.5 = 中性，> 0.5 = 乐观，< 0.5 = 悲观
        sentiment = (bid_ask_ratio - 0.5) * 2
        return max(min(sentiment, 1.0), -1.0)
    
    def _assess_market_activity(self, orderbook: Dict[str, Any]) -> str:
        """评估市场活跃度"""
        volume_data = self._analyze_volume(orderbook)
        depth_data = self._analyze_market_depth(orderbook)
        
        volume_level = volume_data["volume_level"]
        total_levels = depth_data["total_levels"]
        
        if volume_level in ["high", "very_high"] and total_levels > 30:
            return "very_active"
        elif volume_level == "medium" and total_levels > 15:
            return "active"
        elif volume_level != "low" or total_levels > 5:
            return "moderate"
        else:
            return "inactive"
    
    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        """生成基于情绪的推荐"""
        sentiment_score = analysis.get("sentiment_score", 0)
        market_activity = analysis.get("market_activity", "")
        depth_data = analysis.get("market_depth", {})
        
        # 基于情绪和活跃度的推荐
        if sentiment_score > 0.3 and market_activity in ["active", "very_active"]:
            return "BUY - 市场情绪乐观且活跃"
        elif sentiment_score < -0.3 and market_activity in ["active", "very_active"]:
            return "SELL - 市场情绪悲观且活跃"
        elif market_activity == "inactive":
            return "HOLD - 市场不活跃，等待机会"
        elif depth_data.get("depth_quality") == "poor":
            return "HOLD - 市场深度不足"
        elif abs(sentiment_score) < 0.1:
            return "HOLD - 市场情绪中性"
        else:
            return "HOLD - 观望"
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """计算情绪分析置信度"""
        market_activity = analysis.get("market_activity", "")
        sentiment_score = abs(analysis.get("sentiment_score", 0))
        depth_data = analysis.get("market_depth", {})
        volume_data = analysis.get("trading_volume", {})
        
        base_confidence = 0.4
        
        # 活跃度加分
        activity_bonus = {
            "very_active": 0.3,
            "active": 0.2,
            "moderate": 0.1,
            "inactive": -0.1
        }
        base_confidence += activity_bonus.get(market_activity, 0)
        
        # 情绪强度加分
        if sentiment_score > 0.5:
            base_confidence += 0.2
        elif sentiment_score > 0.2:
            base_confidence += 0.1
        
        # 市场深度加分
        depth_quality = depth_data.get("depth_quality", "poor")
        depth_bonus = {
            "excellent": 0.2,
            "good": 0.15,
            "fair": 0.1,
            "poor": -0.1
        }
        base_confidence += depth_bonus.get(depth_quality, 0)
        
        # 交易量加分
        volume_level = volume_data.get("volume_level", "low")
        volume_bonus = {
            "very_high": 0.15,
            "high": 0.1,
            "medium": 0.05,
            "low": -0.05
        }
        base_confidence += volume_bonus.get(volume_level, 0)
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_reasoning(self, analysis: Dict[str, Any]) -> str:
        """生成推理说明"""
        sentiment_score = analysis.get("sentiment_score", 0)
        market_activity = analysis.get("market_activity", "")
        volume_data = analysis.get("trading_volume", {})
        depth_data = analysis.get("market_depth", {})
        
        reasoning_parts = []
        
        # 情绪描述
        if sentiment_score > 0.3:
            reasoning_parts.append("市场情绪乐观")
        elif sentiment_score < -0.3:
            reasoning_parts.append("市场情绪悲观")
        else:
            reasoning_parts.append("市场情绪中性")
        
        # 活跃度描述
        activity_desc = {
            "very_active": "非常活跃",
            "active": "活跃",
            "moderate": "中等活跃",
            "inactive": "不活跃"
        }
        reasoning_parts.append(f"市场活跃度: {activity_desc.get(market_activity, market_activity)}")
        
        # 交易量描述
        volume_level = volume_data.get("volume_level", "low")
        reasoning_parts.append(f"交易量: {volume_level}")
        
        # 市场深度描述
        depth_quality = depth_data.get("depth_quality", "poor")
        reasoning_parts.append(f"市场深度: {depth_quality}")
        
        return " | ".join(reasoning_parts)