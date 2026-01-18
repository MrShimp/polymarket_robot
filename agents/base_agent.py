from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"Agent.{name}")
        self.analysis_history = []
    
    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析市场数据并返回结果
        
        Args:
            market_data: 市场数据
            
        Returns:
            分析结果字典
        """
        pass
    
    def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """验证市场数据完整性"""
        required_fields = ['condition_id', 'question']
        return all(field in market_data for field in required_fields)
    
    def log_analysis(self, market_data: Dict[str, Any], result: Dict[str, Any]):
        """记录分析日志"""
        market_id = market_data.get('condition_id', 'Unknown')
        confidence = result.get('confidence', 0)
        recommendation = result.get('recommendation', 'N/A')
        self.logger.info(f"分析市场 {market_id}: {recommendation} (置信度: {confidence:.2f})")
    
    def store_analysis(self, result: Dict[str, Any]):
        """存储分析历史"""
        result['timestamp'] = datetime.now().isoformat()
        self.analysis_history.append(result)
        
        # 保持最近50条记录
        if len(self.analysis_history) > 50:
            self.analysis_history = self.analysis_history[-50:]