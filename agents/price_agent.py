from typing import Dict, Any
from .base_agent import BaseAgent
import statistics

class PriceAnalysisAgent(BaseAgent):
    """价格分析Agent"""
    
    def __init__(self):
        super().__init__(
            name="PriceAnalyzer",
            description="分析市场价格趋势和波动性"
        )
        self.price_history = {}
    
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析价格数据"""
        if not self.validate_market_data(market_data):
            return {"error": "Invalid market data", "confidence": 0}
        
        condition_id = market_data['condition_id']
        prices = market_data.get('prices', {})
        
        # 存储价格历史
        if condition_id not in self.price_history:
            self.price_history[condition_id] = []
        
        if prices:
            self.price_history[condition_id].append(prices)
            # 保持最近20个价格点
            if len(self.price_history[condition_id]) > 20:
                self.price_history[condition_id] = self.price_history[condition_id][-20:]
        
        analysis_result = {
            "agent": self.name,
            "market_id": condition_id,
            "analysis_type": "price_trend",
            "current_prices": prices,
            "trend": self._analyze_trend(condition_id),
            "volatility": self._calculate_volatility(condition_id),
            "price_momentum": self._calculate_momentum(condition_id),
            "recommendation": "",
            "confidence": 0.0,
            "reasoning": ""
        }
        
        # 生成推荐和置信度
        analysis_result["recommendation"] = self._generate_recommendation(analysis_result)
        analysis_result["confidence"] = self._calculate_confidence(analysis_result)
        analysis_result["reasoning"] = self._generate_reasoning(analysis_result)
        
        self.log_analysis(market_data, analysis_result)
        self.store_analysis(analysis_result)
        return analysis_result
    
    def _analyze_trend(self, condition_id: str) -> str:
        """分析价格趋势"""
        history = self.price_history.get(condition_id, [])
        if len(history) < 3:
            return "insufficient_data"
        
        # 提取价格序列
        prices = []
        for price_data in history[-5:]:  # 最近5个数据点
            if isinstance(price_data, dict) and price_data:
                first_price = list(price_data.values())[0] if price_data else 0
                try:
                    prices.append(float(first_price))
                except (ValueError, TypeError):
                    prices.append(0)
        
        if len(prices) < 3:
            return "insufficient_data"
        
        # 简单趋势分析
        recent_avg = statistics.mean(prices[-3:])
        earlier_avg = statistics.mean(prices[:-3]) if len(prices) > 3 else prices[0]
        
        if recent_avg > earlier_avg * 1.02:  # 2%以上增长
            return "strong_upward"
        elif recent_avg > earlier_avg * 1.005:  # 0.5%以上增长
            return "upward"
        elif recent_avg < earlier_avg * 0.98:  # 2%以上下降
            return "strong_downward"
        elif recent_avg < earlier_avg * 0.995:  # 0.5%以上下降
            return "downward"
        else:
            return "sideways"
    
    def _calculate_volatility(self, condition_id: str) -> float:
        """计算价格波动性"""
        history = self.price_history.get(condition_id, [])
        if len(history) < 2:
            return 0.0
        
        prices = []
        for price_data in history:
            if isinstance(price_data, dict) and price_data:
                first_price = list(price_data.values())[0] if price_data else 0
                try:
                    prices.append(float(first_price))
                except (ValueError, TypeError):
                    continue
        
        if len(prices) < 2:
            return 0.0
        
        # 计算收益率的标准差
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return 0.0
        
        return statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    def _calculate_momentum(self, condition_id: str) -> float:
        """计算价格动量"""
        history = self.price_history.get(condition_id, [])
        if len(history) < 2:
            return 0.0
        
        prices = []
        for price_data in history[-10:]:  # 最近10个数据点
            if isinstance(price_data, dict) and price_data:
                first_price = list(price_data.values())[0] if price_data else 0
                try:
                    prices.append(float(first_price))
                except (ValueError, TypeError):
                    continue
        
        if len(prices) < 2:
            return 0.0
        
        # 简单动量计算：最新价格相对于平均价格的偏离
        avg_price = statistics.mean(prices)
        current_price = prices[-1]
        
        if avg_price == 0:
            return 0.0
        
        return (current_price - avg_price) / avg_price
    
    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        """生成交易推荐"""
        trend = analysis.get("trend", "")
        volatility = analysis.get("volatility", 0)
        momentum = analysis.get("price_momentum", 0)
        
        if trend in ["strong_upward", "upward"] and momentum > 0.02 and volatility < 0.1:
            return "STRONG_BUY"
        elif trend in ["strong_upward", "upward"] and momentum > 0:
            return "BUY"
        elif trend in ["strong_downward", "downward"] and momentum < -0.02 and volatility < 0.1:
            return "STRONG_SELL"
        elif trend in ["strong_downward", "downward"] and momentum < 0:
            return "SELL"
        elif volatility > 0.2:
            return "HOLD - 高波动"
        else:
            return "HOLD"
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """计算推荐置信度"""
        trend = analysis.get("trend", "")
        volatility = analysis.get("volatility", 0)
        momentum = abs(analysis.get("price_momentum", 0))
        
        base_confidence = 0.5
        
        # 趋势明确性加分
        if trend in ["strong_upward", "strong_downward"]:
            base_confidence += 0.3
        elif trend in ["upward", "downward"]:
            base_confidence += 0.2
        
        # 动量强度加分
        if momentum > 0.05:
            base_confidence += 0.2
        elif momentum > 0.02:
            base_confidence += 0.1
        
        # 低波动性加分
        if volatility < 0.05:
            base_confidence += 0.1
        elif volatility > 0.2:
            base_confidence -= 0.2
        
        # 数据充足性
        market_id = analysis.get("market_id", "")
        history_length = len(self.price_history.get(market_id, []))
        if history_length >= 10:
            base_confidence += 0.1
        elif history_length < 3:
            base_confidence -= 0.2
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_reasoning(self, analysis: Dict[str, Any]) -> str:
        """生成推理说明"""
        trend = analysis.get("trend", "")
        volatility = analysis.get("volatility", 0)
        momentum = analysis.get("price_momentum", 0)
        
        reasoning_parts = []
        
        # 趋势说明
        trend_desc = {
            "strong_upward": "强烈上升趋势",
            "upward": "上升趋势", 
            "strong_downward": "强烈下降趋势",
            "downward": "下降趋势",
            "sideways": "横盘整理",
            "insufficient_data": "数据不足"
        }
        reasoning_parts.append(f"趋势: {trend_desc.get(trend, trend)}")
        
        # 动量说明
        if momentum > 0.02:
            reasoning_parts.append("强劲上涨动量")
        elif momentum > 0:
            reasoning_parts.append("正向动量")
        elif momentum < -0.02:
            reasoning_parts.append("强劲下跌动量")
        elif momentum < 0:
            reasoning_parts.append("负向动量")
        else:
            reasoning_parts.append("动量中性")
        
        # 波动性说明
        if volatility > 0.2:
            reasoning_parts.append("高波动性")
        elif volatility < 0.05:
            reasoning_parts.append("低波动性")
        else:
            reasoning_parts.append("中等波动性")
        
        return " | ".join(reasoning_parts)