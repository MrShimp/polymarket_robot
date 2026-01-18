#!/usr/bin/env python3
"""
高频微型仓位策略 - 专门针对90¢-99¢的近乎确定性合约
High-Frequency Micro-Position Strategy for Near-Certainty Contracts (90¢-99¢)

策略特点:
- 专注于90¢-99¢价格区间的高概率合约
- 每天执行27,000+次微型交易
- 风险控制严格，单笔损失限制
- 自动化执行，无需人工干预
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import dataclass
from polymarket_clob_client import PolymarketCLOBClient
from data_saver import DataSaver

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hf_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingOpportunity:
    """交易机会数据结构"""
    token_id: str
    market_id: str
    current_price: float
    target_price: float
    confidence: float
    volume: int
    spread: float
    last_update: datetime
    market_question: str
    outcome: str

@dataclass
class Position:
    """仓位数据结构"""
    token_id: str
    side: str  # BUY/SELL
    size: int
    entry_price: float
    current_price: float
    pnl: float
    timestamp: datetime
    target_profit: float
    stop_loss: float

class HighFrequencyStrategy:
    """高频微型仓位交易策略"""
    
    def __init__(self, 
                 api_key: str,
                 api_secret: str, 
                 passphrase: str,
                 config_file: str = "hf_config.json"):
        
        self.client = PolymarketCLOBClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            save_data=True
        )
        
        self.data_saver = DataSaver(data_dir="./hf_data")
        self.config_file = config_file
        self.load_config()
        
        # 交易状态
        self.active_positions: Dict[str, Position] = {}
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()
        
        # 性能统计
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        
        # 风控状态
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.is_trading_halted = False
        
    def load_config(self):
        """加载策略配置"""
        default_config = {
            # 价格筛选参数
            "min_price": 0.90,           # 最低价格 90¢
            "max_price": 0.99,           # 最高价格 99¢
            "min_confidence": 0.95,      # 最低置信度
            
            # 交易参数
            "position_size": 1,          # 微型仓位大小 ($1)
            "max_positions": 100,        # 最大同时持仓数
            "target_profit_pct": 0.02,   # 目标利润 2%
            "stop_loss_pct": 0.05,       # 止损 5%
            
            # 频率控制
            "scan_interval": 3,          # 扫描间隔 (秒)
            "max_daily_trades": 27000,   # 每日最大交易次数
            "trades_per_minute": 30,     # 每分钟最大交易次数
            
            # 风控参数
            "max_daily_loss": 500,       # 每日最大亏损 $500
            "max_consecutive_losses": 10, # 最大连续亏损次数
            "max_position_loss": 10,     # 单仓位最大亏损 $10
            
            # 市场筛选
            "min_volume": 1000,          # 最小交易量
            "max_spread": 0.05,          # 最大价差 5%
            "exclude_keywords": ["test", "demo", "practice"],
            
            # 时间控制
            "trading_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC"
            }
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """保存策略配置"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def is_trading_time(self) -> bool:
        """检查是否在交易时间内"""
        now = datetime.now()
        start_time = datetime.strptime(self.config["trading_hours"]["start"], "%H:%M").time()
        end_time = datetime.strptime(self.config["trading_hours"]["end"], "%H:%M").time()
        
        return start_time <= now.time() <= end_time
    
    def reset_daily_stats(self):
        """重置每日统计"""
        today = datetime.now().date()
        if today != self.last_reset:
            logger.info(f"重置每日统计 - 昨日交易: {self.daily_trades}, 昨日PnL: ${self.daily_pnl:.2f}")
            
            # 保存昨日统计
            daily_stats = {
                'date': self.last_reset.isoformat(),
                'trades': self.daily_trades,
                'pnl': self.daily_pnl,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades
            }
            self.save_daily_stats(daily_stats)
            
            # 重置统计
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.daily_loss = 0.0
            self.consecutive_losses = 0
            self.is_trading_halted = False
            self.last_reset = today
    
    def save_daily_stats(self, stats: Dict):
        """保存每日统计"""
        filename = f"daily_stats_{stats['date']}.json"
        filepath = os.path.join("./hf_data", filename)
        
        os.makedirs("./hf_data", exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
    
    async def scan_markets(self) -> List[TradingOpportunity]:
        """扫描市场寻找交易机会"""
        opportunities = []
        
        try:
            # 获取活跃市场
            markets_data = self.client.get_markets(limit=1000)
            if not markets_data:
                return opportunities
            
            markets = markets_data.get('data', [])
            logger.info(f"扫描 {len(markets)} 个市场")
            
            for market in markets:
                if not market.get('active') or not market.get('accepting_orders'):
                    continue
                
                # 跳过包含排除关键词的市场
                question = market.get('question', '').lower()
                if any(keyword in question for keyword in self.config['exclude_keywords']):
                    continue
                
                # 获取市场详情和代币
                condition_id = market.get('condition_id')
                market_detail = self.client.get_market(condition_id)
                
                if not market_detail or not market_detail.get('tokens'):
                    continue
                
                # 分析每个代币
                for token in market_detail['tokens']:
                    opportunity = await self.analyze_token(token, market_detail)
                    if opportunity:
                        opportunities.append(opportunity)
                
                # 避免请求过于频繁
                await asyncio.sleep(0.1)
            
            # 按置信度排序
            opportunities.sort(key=lambda x: x.confidence, reverse=True)
            logger.info(f"发现 {len(opportunities)} 个交易机会")
            
        except Exception as e:
            logger.error(f"扫描市场失败: {e}")
        
        return opportunities
    
    async def analyze_token(self, token: Dict, market: Dict) -> Optional[TradingOpportunity]:
        """分析代币是否符合交易条件"""
        token_id = token.get('token_id')
        if not token_id:
            return None
        
        try:
            # 获取最后交易价格
            last_price_data = self.client.get_last_trade_price(token_id)
            if not last_price_data:
                return None
            
            current_price = float(last_price_data.get('price', 0))
            
            # 价格筛选 - 只关注90¢-99¢的合约
            if not (self.config['min_price'] <= current_price <= self.config['max_price']):
                return None
            
            # 获取订单簿计算价差
            orderbook = self.client.get_orderbook(token_id)
            spread = self.calculate_spread(orderbook) if orderbook else 0.1
            
            # 价差筛选
            if spread > self.config['max_spread']:
                return None
            
            # 计算置信度 (基于价格、价差、市场活跃度等)
            confidence = self.calculate_confidence(current_price, spread, market, token)
            
            if confidence < self.config['min_confidence']:
                return None
            
            # 计算目标价格
            target_price = min(0.99, current_price * (1 + self.config['target_profit_pct']))
            
            return TradingOpportunity(
                token_id=token_id,
                market_id=market.get('condition_id', ''),
                current_price=current_price,
                target_price=target_price,
                confidence=confidence,
                volume=self.estimate_volume(orderbook),
                spread=spread,
                last_update=datetime.now(),
                market_question=market.get('question', ''),
                outcome=token.get('outcome', '')
            )
            
        except Exception as e:
            logger.error(f"分析代币 {token_id} 失败: {e}")
            return None
    
    def calculate_spread(self, orderbook: Dict) -> float:
        """计算买卖价差"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 0.1  # 默认价差
            
            best_bid = float(bids[0].get('price', 0))
            best_ask = float(asks[0].get('price', 0))
            
            if best_ask > 0:
                return (best_ask - best_bid) / best_ask
            
        except Exception:
            pass
        
        return 0.1
    
    def estimate_volume(self, orderbook: Dict) -> int:
        """估算交易量"""
        try:
            if not orderbook:
                return 0
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            total_volume = 0
            for bid in bids[:5]:  # 前5档
                total_volume += float(bid.get('size', 0))
            for ask in asks[:5]:  # 前5档
                total_volume += float(ask.get('size', 0))
            
            return int(total_volume)
            
        except Exception:
            return 0
    
    def calculate_confidence(self, price: float, spread: float, market: Dict, token: Dict) -> float:
        """计算交易置信度"""
        confidence = 0.0
        
        # 基于价格的置信度 (价格越接近1.0，置信度越高)
        price_confidence = price
        confidence += price_confidence * 0.4
        
        # 基于价差的置信度 (价差越小，置信度越高)
        spread_confidence = max(0, 1 - spread * 10)
        confidence += spread_confidence * 0.2
        
        # 基于市场活跃度的置信度
        activity_confidence = 1.0 if market.get('accepting_orders') else 0.5
        confidence += activity_confidence * 0.2
        
        # 基于结果确定性的置信度
        outcome_confidence = self.analyze_outcome_certainty(market, token)
        confidence += outcome_confidence * 0.2
        
        return min(1.0, confidence)
    
    def analyze_outcome_certainty(self, market: Dict, token: Dict) -> float:
        """分析结果确定性"""
        # 这里可以添加更复杂的逻辑来分析市场结果的确定性
        # 例如：时间到期、事件已发生、官方确认等
        
        question = market.get('question', '').lower()
        outcome = token.get('outcome', '').lower()
        
        # 简单的关键词分析
        certain_keywords = ['winner', 'confirmed', 'official', 'final']
        uncertain_keywords = ['will', 'might', 'could', 'possible']
        
        certainty_score = 0.5  # 基础分数
        
        for keyword in certain_keywords:
            if keyword in question or keyword in outcome:
                certainty_score += 0.1
        
        for keyword in uncertain_keywords:
            if keyword in question or keyword in outcome:
                certainty_score -= 0.1
        
        return max(0.0, min(1.0, certainty_score))
    
    async def execute_trade(self, opportunity: TradingOpportunity) -> bool:
        """执行交易"""
        if not self.can_trade():
            return False
        
        try:
            # 创建买单
            order_result = self.client.create_order(
                token_id=opportunity.token_id,
                price=str(opportunity.current_price),
                size=str(self.config['position_size']),
                side='BUY'
            )
            
            if not order_result:
                logger.error(f"创建订单失败: {opportunity.token_id}")
                return False
            
            # 记录仓位
            position = Position(
                token_id=opportunity.token_id,
                side='BUY',
                size=self.config['position_size'],
                entry_price=opportunity.current_price,
                current_price=opportunity.current_price,
                pnl=0.0,
                timestamp=datetime.now(),
                target_profit=opportunity.target_price,
                stop_loss=opportunity.current_price * (1 - self.config['stop_loss_pct'])
            )
            
            self.active_positions[opportunity.token_id] = position
            
            # 更新统计
            self.daily_trades += 1
            self.total_trades += 1
            
            logger.info(f"执行交易: {opportunity.market_question[:50]}... "
                       f"价格: ${opportunity.current_price:.3f}, "
                       f"目标: ${opportunity.target_price:.3f}")
            
            # 保存交易记录
            self.save_trade_record(opportunity, order_result)
            
            return True
            
        except Exception as e:
            logger.error(f"执行交易失败: {e}")
            return False
    
    def can_trade(self) -> bool:
        """检查是否可以交易"""
        # 检查交易时间
        if not self.is_trading_time():
            return False
        
        # 检查是否被暂停
        if self.is_trading_halted:
            return False
        
        # 检查每日交易次数限制
        if self.daily_trades >= self.config['max_daily_trades']:
            return False
        
        # 检查仓位数量限制
        if len(self.active_positions) >= self.config['max_positions']:
            return False
        
        # 检查每日亏损限制
        if self.daily_loss >= self.config['max_daily_loss']:
            logger.warning("达到每日亏损限制，暂停交易")
            self.is_trading_halted = True
            return False
        
        # 检查连续亏损限制
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            logger.warning("达到连续亏损限制，暂停交易")
            self.is_trading_halted = True
            return False
        
        return True
    
    def save_trade_record(self, opportunity: TradingOpportunity, order_result: Dict):
        """保存交易记录"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'token_id': opportunity.token_id,
            'market_question': opportunity.market_question,
            'outcome': opportunity.outcome,
            'entry_price': opportunity.current_price,
            'target_price': opportunity.target_price,
            'confidence': opportunity.confidence,
            'order_id': order_result.get('id'),
            'size': self.config['position_size']
        }
        
        # 保存到文件
        filename = f"trades_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join("./hf_data", filename)
        
        os.makedirs("./hf_data", exist_ok=True)
        
        # 追加到文件
        trades = []
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                trades = json.load(f)
        
        trades.append(trade_record)
        
        with open(filepath, 'w') as f:
            json.dump(trades, f, indent=2)
    
    async def manage_positions(self):
        """管理现有仓位"""
        positions_to_close = []
        
        for token_id, position in self.active_positions.items():
            try:
                # 获取当前价格
                current_price_data = self.client.get_last_trade_price(token_id)
                if not current_price_data:
                    continue
                
                current_price = float(current_price_data.get('price', 0))
                position.current_price = current_price
                
                # 计算PnL
                position.pnl = (current_price - position.entry_price) * position.size
                
                # 检查止盈条件
                if current_price >= position.target_profit:
                    logger.info(f"达到止盈目标: {token_id}, PnL: ${position.pnl:.2f}")
                    positions_to_close.append((token_id, 'PROFIT'))
                
                # 检查止损条件
                elif current_price <= position.stop_loss:
                    logger.warning(f"触发止损: {token_id}, PnL: ${position.pnl:.2f}")
                    positions_to_close.append((token_id, 'LOSS'))
                
                # 检查单仓位最大亏损
                elif position.pnl <= -self.config['max_position_loss']:
                    logger.warning(f"达到单仓位最大亏损: {token_id}, PnL: ${position.pnl:.2f}")
                    positions_to_close.append((token_id, 'MAX_LOSS'))
                
            except Exception as e:
                logger.error(f"管理仓位 {token_id} 失败: {e}")
        
        # 平仓
        for token_id, reason in positions_to_close:
            await self.close_position(token_id, reason)
    
    async def close_position(self, token_id: str, reason: str):
        """平仓"""
        if token_id not in self.active_positions:
            return
        
        position = self.active_positions[token_id]
        
        try:
            # 创建卖单
            order_result = self.client.create_order(
                token_id=token_id,
                price=str(position.current_price),
                size=str(position.size),
                side='SELL'
            )
            
            if order_result:
                # 更新统计
                self.daily_pnl += position.pnl
                self.total_profit += position.pnl
                
                if position.pnl > 0:
                    self.winning_trades += 1
                    self.consecutive_losses = 0
                else:
                    self.losing_trades += 1
                    self.consecutive_losses += 1
                    self.daily_loss += abs(position.pnl)
                
                logger.info(f"平仓完成: {token_id}, 原因: {reason}, PnL: ${position.pnl:.2f}")
                
                # 移除仓位
                del self.active_positions[token_id]
            
        except Exception as e:
            logger.error(f"平仓失败 {token_id}: {e}")
    
    async def run_strategy(self):
        """运行策略主循环"""
        logger.info("启动高频微型仓位策略")
        
        while True:
            try:
                # 重置每日统计
                self.reset_daily_stats()
                
                # 管理现有仓位
                await self.manage_positions()
                
                # 扫描新的交易机会
                opportunities = await self.scan_markets()
                
                # 执行交易
                for opportunity in opportunities[:10]:  # 限制每次处理的机会数量
                    if await self.execute_trade(opportunity):
                        # 控制交易频率
                        await asyncio.sleep(60 / self.config['trades_per_minute'])
                
                # 打印状态
                self.print_status()
                
                # 等待下次扫描
                await asyncio.sleep(self.config['scan_interval'])
                
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在安全退出...")
                break
            except Exception as e:
                logger.error(f"策略运行错误: {e}")
                await asyncio.sleep(10)  # 错误后等待10秒
    
    def print_status(self):
        """打印策略状态"""
        win_rate = (self.winning_trades / max(1, self.total_trades)) * 100
        
        logger.info(f"策略状态 - "
                   f"今日交易: {self.daily_trades}, "
                   f"今日PnL: ${self.daily_pnl:.2f}, "
                   f"活跃仓位: {len(self.active_positions)}, "
                   f"胜率: {win_rate:.1f}%, "
                   f"总利润: ${self.total_profit:.2f}")

async def main():
    """主函数"""
    # 从环境变量获取API密钥
    api_key = os.getenv('POLYMARKET_API_KEY')
    api_secret = os.getenv('POLYMARKET_API_SECRET')
    passphrase = os.getenv('POLYMARKET_PASSPHRASE')
    
    if not all([api_key, api_secret, passphrase]):
        logger.error("请设置环境变量: POLYMARKET_API_KEY, POLYMARKET_API_SECRET, POLYMARKET_PASSPHRASE")
        return
    
    # 创建策略实例
    strategy = HighFrequencyStrategy(api_key, api_secret, passphrase)
    
    # 运行策略
    await strategy.run_strategy()

if __name__ == "__main__":
    asyncio.run(main())