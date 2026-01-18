import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.polymarket_client import PolymarketClient
from agents import PriceAnalysisAgent, SentimentAnalysisAgent, RiskAnalysisAgent
from agents.decision_engine import DecisionEngine
from export.data_saver import DataSaver

logger = logging.getLogger(__name__)

class MainAgent:
    """主Agent - 协调所有子Agent并做出最终决策"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化组件
        self.polymarket_client = PolymarketClient(save_data=True)
        self.decision_engine = DecisionEngine(self.config.get('decision_config', {}))
        self.data_saver = DataSaver()
        
        # 初始化子Agent
        self.sub_agents = {
            'PriceAnalyzer': PriceAnalysisAgent(),
            'SentimentAnalyzer': SentimentAnalysisAgent(), 
            'RiskAnalyzer': RiskAnalysisAgent()
        }
        
        # 运行状态
        self.is_running = False
        self.monitored_markets = []
        self.decision_history = []
        
        # 配置参数
        self.update_interval = self.config.get('update_interval', 60)  # 秒
        self.max_markets = self.config.get('max_markets', 3)
        self.min_confidence_threshold = self.config.get('min_confidence', 0.6)
        
        logger.info("主Agent初始化完成")
    
    def start_monitoring(self, market_filters: Optional[Dict[str, Any]] = None):
        """开始监控市场"""
        self.is_running = True
        logger.info("开始市场监控...")
        
        try:
            # 获取要监控的市场
            self._update_monitored_markets(market_filters)
            
            # 主监控循环
            while self.is_running:
                try:
                    self._monitoring_cycle()
                    
                    logger.info(f"等待 {self.update_interval} 秒后进行下次监控...")
                    time.sleep(self.update_interval)
                    
                except KeyboardInterrupt:
                    logger.info("收到中断信号")
                    break
                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    time.sleep(30)  # 出错后等待30秒
        
        finally:
            self.stop_monitoring()
    
    def _monitoring_cycle(self):
        """单次监控循环"""
        logger.info(f"开始新的监控循环 - 监控 {len(self.monitored_markets)} 个市场")
        
        for i, market in enumerate(self.monitored_markets):
            try:
                logger.info(f"处理市场 {i+1}/{len(self.monitored_markets)}: {market.get('question', 'Unknown')}")
                self._process_market(market)
                
                # 短暂延迟避免API限制
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"处理市场 {market.get('condition_id')} 时出错: {e}")
    
    def _process_market(self, market: Dict[str, Any]):
        """处理单个市场"""
        condition_id = market.get('condition_id')
        if not condition_id:
            return
        
        # 获取完整的市场数据
        market_data = self._collect_market_data(condition_id, market)
        if not market_data:
            logger.warning(f"无法获取市场 {condition_id} 的完整数据")
            return
        
        # 运行所有子Agent分析
        agent_results = {}
        for agent_name, agent in self.sub_agents.items():
            try:
                logger.info(f"运行 {agent_name} 分析...")
                result = agent.analyze(market_data)
                agent_results[agent_name] = result
            except Exception as e:
                logger.error(f"Agent {agent_name} 分析失败: {e}")
                agent_results[agent_name] = {"error": str(e), "confidence": 0}
        
        # 决策引擎处理
        logger.info("生成最终决策...")
        decision = self.decision_engine.make_decision(market_data, agent_results)
        
        # 存储决策历史
        self._store_decision_history(condition_id, {
            'market_data': market_data,
            'agent_results': agent_results,
            'decision': decision
        })
        
        # 执行决策（如果需要）
        if decision.get('should_execute', False):
            self._execute_decision(condition_id, decision)
        
        # 记录结果
        self._log_cycle_result(condition_id, agent_results, decision)
    
    def _collect_market_data(self, condition_id: str, base_market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """收集市场的完整数据"""
        try:
            # 获取市场详情
            market_detail = self.polymarket_client.get_market(condition_id)
            if not market_detail:
                return None
            
            # 获取价格信息
            prices = self.polymarket_client.get_market_prices(condition_id)
            
            # 获取订单簿（如果有代币信息）
            orderbook = None
            tokens = market_detail.get('tokens', [])
            if tokens:
                token_id = tokens[0].get('token_id')
                if token_id:
                    orderbook = self.polymarket_client.get_orderbook(token_id)
            
            # 组合完整的市场数据
            market_data = {
                **base_market,
                **market_detail,
                'prices': prices or {},
                'orderbook': orderbook or {},
                'timestamp': datetime.now().isoformat()
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"收集市场数据失败 {condition_id}: {e}")
            return None
    
    def _update_monitored_markets(self, filters: Optional[Dict[str, Any]] = None):
        """更新监控的市场列表"""
        try:
            # 获取活跃市场
            markets = self.polymarket_client.get_markets(
                limit=self.max_markets * 2,  # 获取更多市场以便筛选
                active=True
            )
            
            if not markets:
                logger.warning("未能获取市场列表")
                return
            
            # 应用过滤器
            if filters:
                markets = self._apply_market_filters(markets, filters)
            
            # 限制数量
            self.monitored_markets = markets[:self.max_markets]
            
            logger.info(f"更新监控市场列表: {len(self.monitored_markets)} 个市场")
            for market in self.monitored_markets:
                logger.info(f"  - {market.get('question', 'Unknown')} ({market.get('condition_id')})")
                
        except Exception as e:
            logger.error(f"更新监控市场失败: {e}")
    
    def _apply_market_filters(self, markets: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用市场过滤器"""
        filtered_markets = []
        
        for market in markets:
            # 标签过滤
            if 'tags' in filters:
                market_tags = market.get('tags', [])
                if not any(tag in market_tags for tag in filters['tags']):
                    continue
            
            # 关键词过滤
            if 'keywords' in filters:
                question = market.get('question', '').lower()
                if not any(keyword.lower() in question for keyword in filters['keywords']):
                    continue
            
            filtered_markets.append(market)
        
        return filtered_markets
    
    def _store_decision_history(self, condition_id: str, decision_data: Dict[str, Any]):
        """存储决策历史"""
        history_entry = {
            'condition_id': condition_id,
            'timestamp': datetime.now().isoformat(),
            **decision_data
        }
        
        self.decision_history.append(history_entry)
        
        # 保持最近100条记录
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-100:]
        
        # 保存到CSV
        try:
            decision_summary = {
                'condition_id': condition_id,
                'timestamp': history_entry['timestamp'],
                'action': decision_data['decision'].get('action', 'HOLD'),
                'confidence': decision_data['decision'].get('confidence', 0),
                'should_execute': decision_data['decision'].get('should_execute', False),
                'reasoning': decision_data['decision'].get('reasoning', ''),
                'risk_level': decision_data['decision'].get('risk_assessment', {}).get('risk_level', 'unknown')
            }
            
            self.data_saver.append_to_daily_file('decisions', [decision_summary])
        except Exception as e:
            logger.error(f"保存决策历史失败: {e}")
    
    def _execute_decision(self, condition_id: str, decision: Dict[str, Any]):
        """执行交易决策（模拟）"""
        try:
            action = decision.get('action', 'HOLD')
            confidence = decision.get('confidence', 0)
            
            logger.info(f"=== 模拟执行交易决策 ===")
            logger.info(f"市场: {condition_id}")
            logger.info(f"动作: {action}")
            logger.info(f"置信度: {confidence:.2f}")
            logger.info(f"推理: {decision.get('reasoning', 'N/A')}")
            logger.info("=== 交易执行完成 ===")
            
            # 这里可以集成真实的交易API
            # 目前只是模拟执行
            
        except Exception as e:
            logger.error(f"执行决策时出错: {e}")
    
    def _log_cycle_result(self, condition_id: str, agent_results: Dict[str, Any], decision: Dict[str, Any]):
        """记录循环结果"""
        logger.info(f"=== 市场 {condition_id} 分析完成 ===")
        
        for agent_name, result in agent_results.items():
            if not result.get('error'):
                confidence = result.get('confidence', 0)
                recommendation = result.get('recommendation', 'N/A')
                logger.info(f"  {agent_name}: {recommendation} (置信度: {confidence:.2f})")
            else:
                logger.warning(f"  {agent_name}: 分析失败 - {result.get('error')}")
        
        if decision:
            action = decision.get('action', 'HOLD')
            confidence = decision.get('confidence', 0)
            should_execute = decision.get('should_execute', False)
            logger.info(f"  最终决策: {action} (置信度: {confidence:.2f}, 执行: {should_execute})")
        
        logger.info("=" * 50)
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        logger.info("监控已停止")
    
    def analyze_single_market(self, condition_id: str) -> Dict[str, Any]:
        """分析单个市场（用于测试或手动分析）"""
        try:
            market = self.polymarket_client.get_market(condition_id)
            if not market:
                return {"error": "Market not found"}
            
            market_data = self._collect_market_data(condition_id, market)
            if not market_data:
                return {"error": "Failed to collect market data"}
            
            # 运行所有分析
            agent_results = {}
            for agent_name, agent in self.sub_agents.items():
                try:
                    result = agent.analyze(market_data)
                    agent_results[agent_name] = result
                except Exception as e:
                    agent_results[agent_name] = {"error": str(e)}
            
            # 生成决策
            decision = self.decision_engine.make_decision(market_data, agent_results)
            
            return {
                "market_data": market_data,
                "agent_results": agent_results,
                "decision": decision
            }
            
        except Exception as e:
            logger.error(f"分析单个市场失败: {e}")
            return {"error": str(e)}
    
    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取决策历史"""
        return self.decision_history[-limit:]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        status = {
            'is_running': self.is_running,
            'monitored_markets_count': len(self.monitored_markets),
            'decision_history_count': len(self.decision_history),
            'agents': {}
        }
        
        for agent_name, agent in self.sub_agents.items():
            status['agents'][agent_name] = {
                'name': agent.name,
                'description': agent.description,
                'analysis_history_count': len(agent.analysis_history)
            }
        
        return status