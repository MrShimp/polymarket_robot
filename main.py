#!/usr/bin/env python3
"""
Polymarket自动交易系统 - 精简版
功能：数据拉取 + 交易执行 + 日志展示
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from dateutil import parser as date_parser
from eth_account import Account
from eth_account.messages import encode_defunct
from decimal import Decimal

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading.log')
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """配置管理"""
    def __init__(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = self._create_default_config()
        
        # Polymarket配置
        polymarket = config.get('polymarket', {})
        self.host = polymarket.get('host', 'https://clob.polymarket.com')
        self.chain_id = polymarket.get('chain_id', 137)
        self.private_key = polymarket.get('private_key', '')
        
        # 策略配置
        strategy = config.get('strategy', {})
        self.time_threshold_minutes = strategy.get('time_threshold_minutes', 30)
        self.min_confidence = strategy.get('min_confidence', 0.85)
        self.max_confidence = strategy.get('max_confidence', 0.95)
        
        # 交易配置
        trading = config.get('trading', {})
        self.trade_amount = trading.get('trade_amount', 10.0)
        self.max_slippage = trading.get('max_slippage', 0.02)
        self.dry_run = trading.get('dry_run', True)
    
    def _create_default_config(self):
        """创建默认配置"""
        config = {
            "polymarket": {
                "host": "https://clob.polymarket.com",
                "chain_id": 137,
                "private_key": ""
            },
            "strategy": {
                "time_threshold_minutes": 30,
                "min_confidence": 0.85,
                "max_confidence": 0.95
            },
            "trading": {
                "trade_amount": 10.0,
                "max_slippage": 0.02,
                "dry_run": True
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("已创建默认配置文件 config.json，请填入你的私钥")
        return config

class MarketDataFetcher:
    """市场数据拉取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def fetch_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """拉取市场数据"""
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'order': 'endDate',
            'closed': 'false',
            'ascending': 'true',
            'limit': limit,
            'offset': offset
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get('data', [])
        except Exception as e:
            logger.error(f"拉取市场数据失败: {e}")
            return []
    
    def scan_opportunities(self, config: Config) -> List[Dict]:
        """扫描交易机会"""
        logger.info(f"🔍 开始扫描交易机会...")
        logger.info(f"📊 参数: 时间阈值={config.time_threshold_minutes}分钟, 胜率={config.min_confidence:.1%}-{config.max_confidence:.1%}")
        
        opportunities = []
        offset = 0
        total_checked = 0
        
        while total_checked < 1000:  # 限制扫描数量
            markets = self.fetch_markets(limit=100, offset=offset)
            if not markets:
                break
            
            for market in markets:
                total_checked += 1
                
                # 检查时间条件
                if not self._is_ending_soon(market.get('endDate', ''), config.time_threshold_minutes):
                    continue
                
                # 检查胜率条件
                opportunity = self._check_confidence(market, config)
                if opportunity:
                    opportunities.append(opportunity)
                    logger.info(f"⚡ 发现机会: {market.get('question', 'Unknown')[:50]}... "
                              f"胜率={opportunity['confidence']:.3f} ({opportunity['winning_option']})")
            
            offset += len(markets)
            if len(markets) < 100:
                break
        
        logger.info(f"🎯 扫描完成: 检查了{total_checked}个市场，发现{len(opportunities)}个机会")
        return opportunities
    
    def _is_ending_soon(self, end_date_str: str, minutes_threshold: int) -> bool:
        """检查是否即将结束"""
        if not end_date_str:
            return False
        
        try:
            end_time = date_parser.parse(end_date_str)
            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            time_diff = end_time - current_time
            return 0 < time_diff.total_seconds() <= (minutes_threshold * 60)
        except:
            return False
    
    def _check_confidence(self, market: Dict, config: Config) -> Optional[Dict]:
        """检查胜率条件"""
        try:
            prices_str = market.get('outcomePrices', '')
            if not prices_str or not prices_str.startswith('['):
                return None
            
            prices = json.loads(prices_str)
            if len(prices) < 2:
                return None
            
            max_price = max(float(p) for p in prices if p)
            if config.min_confidence <= max_price <= config.max_confidence:
                max_index = prices.index(str(max_price))
                outcomes = json.loads(market.get('outcomes', '[]'))
                winning_option = outcomes[max_index] if max_index < len(outcomes) else 'Unknown'
                
                return {
                    'market': market,
                    'confidence': max_price,
                    'winning_option': winning_option,
                    'time_remaining': self._get_time_remaining(market.get('endDate', ''))
                }
        except:
            pass
        
        return None
    
    def _get_time_remaining(self, end_date_str: str) -> int:
        """获取剩余时间（分钟）"""
        try:
            end_time = date_parser.parse(end_date_str)
            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            time_diff = end_time - current_time
            return max(0, int(time_diff.total_seconds() / 60))
        except:
            return 0

class TradingClient:
    """交易客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        
        if config.private_key:
            try:
                if not config.private_key.startswith('0x'):
                    config.private_key = '0x' + config.private_key
                
                self.account = Account.from_key(config.private_key)
                self.address = self.account.address
                logger.info(f"✅ 交易客户端初始化成功，地址: {self.address}")
            except Exception as e:
                logger.error(f"❌ 私钥无效: {e}")
                self.account = None
                self.address = None
        else:
            logger.warning("⚠️  未配置私钥，仅模拟交易")
            self.account = None
            self.address = None
    
    def _create_signature(self, message: str) -> str:
        """创建签名"""
        if not self.account:
            return ""
        
        message_hash = encode_defunct(text=message)
        signed_message = self.account.sign_message(message_hash)
        return signed_message.signature.hex()
    
    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """获取请求头"""
        headers = {'Content-Type': 'application/json'}
        
        if self.account:
            timestamp = str(int(time.time() * 1000))
            message = f"{method}{path}{body}{timestamp}"
            signature = self._create_signature(message)
            
            headers.update({
                'POLY-ADDRESS': self.address,
                'POLY-SIGNATURE': signature,
                'POLY-TIMESTAMP': timestamp,
                'POLY-NONCE': timestamp
            })
        
        return headers
    
    def get_balance(self) -> Dict:
        """获取余额"""
        try:
            headers = self._get_headers('GET', '/balance')
            response = self.session.get(f"{self.config.host}/balance", headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return {}
    
    def get_orderbook(self, token_id: str) -> Dict:
        """获取订单簿"""
        try:
            headers = self._get_headers('GET', '/book')
            params = {'token_id': token_id}
            response = self.session.get(f"{self.config.host}/book", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            return {}
    
    def create_order(self, token_id: str, side: str, size: str, price: str) -> Dict:
        """创建订单"""
        data = {
            'tokenID': token_id,
            'side': side.upper(),
            'size': size,
            'price': price,
            'type': 'LIMIT',
            'timeInForce': 'GTC'
        }
        
        try:
            body = json.dumps(data)
            headers = self._get_headers('POST', '/order', body)
            response = self.session.post(f"{self.config.host}/order", headers=headers, data=body)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return {}
    
    def execute_trade(self, opportunity: Dict) -> Dict:
        """执行交易"""
        market = opportunity['market']
        confidence = opportunity['confidence']
        winning_option = opportunity['winning_option']
        
        logger.info(f"🚀 {'模拟' if self.config.dry_run else '实盘'}交易:")
        logger.info(f"   市场: {market.get('question', 'Unknown')[:50]}...")
        logger.info(f"   选项: {winning_option} (置信度: {confidence:.3f})")
        logger.info(f"   金额: ${self.config.trade_amount} USDC")
        logger.info(f"   剩余时间: {opportunity['time_remaining']} 分钟")
        
        if self.config.dry_run:
            logger.info("✅ 模拟交易完成")
            return {
                'success': True,
                'simulated': True,
                'market_id': market.get('id'),
                'confidence': confidence,
                'winning_option': winning_option
            }
        
        # 实盘交易逻辑
        try:
            # 获取代币ID
            token_ids = json.loads(market.get('clobTokenIds', '[]'))
            if not token_ids:
                logger.error("❌ 无法获取代币ID")
                return {'success': False, 'error': 'No token IDs'}
            
            # 选择对应的代币
            outcomes = json.loads(market.get('outcomes', '[]'))
            token_index = 0
            for i, outcome in enumerate(outcomes):
                if outcome == winning_option:
                    token_index = i
                    break
            
            if token_index >= len(token_ids):
                logger.error("❌ 代币索引超出范围")
                return {'success': False, 'error': 'Invalid token index'}
            
            token_id = token_ids[token_index]
            
            # 获取订单簿
            orderbook = self.get_orderbook(token_id)
            asks = orderbook.get('asks', [])
            
            if not asks:
                logger.error("❌ 没有卖单")
                return {'success': False, 'error': 'No asks available'}
            
            # 计算交易参数
            best_ask = float(asks[0]['price'])
            trade_size = str(self.config.trade_amount / best_ask)
            
            # 创建买单
            result = self.create_order(token_id, 'BUY', trade_size, str(best_ask))
            
            if result:
                logger.info("✅ 订单创建成功")
                return {
                    'success': True,
                    'order_id': result.get('orderID'),
                    'market_id': market.get('id'),
                    'token_id': token_id,
                    'size': trade_size,
                    'price': str(best_ask)
                }
            else:
                logger.error("❌ 订单创建失败")
                return {'success': False, 'error': 'Order creation failed'}
                
        except Exception as e:
            logger.error(f"❌ 交易执行失败: {e}")
            return {'success': False, 'error': str(e)}

class TradingBot:
    """交易机器人主类"""
    
    def __init__(self):
        self.config = Config()
        self.data_fetcher = MarketDataFetcher()
        self.trading_client = TradingClient(self.config)
        self.stats = {
            'total_scans': 0,
            'opportunities_found': 0,
            'trades_executed': 0,
            'successful_trades': 0
        }
    
    def run_single_scan(self) -> Dict:
        """执行单次扫描和交易"""
        logger.info("="*60)
        logger.info(f"🤖 开始交易扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        self.stats['total_scans'] += 1
        
        # 1. 扫描机会
        opportunities = self.data_fetcher.scan_opportunities(self.config)
        self.stats['opportunities_found'] += len(opportunities)
        
        if not opportunities:
            logger.info("📭 未发现符合条件的交易机会")
            return {'success': True, 'opportunities': 0, 'trades': 0}
        
        # 2. 显示账户信息
        if not self.config.dry_run:
            balance = self.trading_client.get_balance()
            usdc_balance = balance.get('usdcBalance', '0')
            logger.info(f"💰 USDC余额: ${usdc_balance}")
        
        # 3. 执行交易
        trade_results = []
        for i, opportunity in enumerate(opportunities[:3], 1):  # 最多交易前3个
            logger.info(f"\n💡 处理机会 {i}/{len(opportunities[:3])}")
            
            result = self.trading_client.execute_trade(opportunity)
            trade_results.append(result)
            
            if result.get('success'):
                self.stats['successful_trades'] += 1
            
            self.stats['trades_executed'] += 1
            
            # 交易间隔
            if i < len(opportunities[:3]):
                time.sleep(2)
        
        # 4. 显示结果
        successful = sum(1 for r in trade_results if r.get('success'))
        logger.info(f"\n📊 本次结果:")
        logger.info(f"   发现机会: {len(opportunities)} 个")
        logger.info(f"   执行交易: {len(trade_results)} 笔")
        logger.info(f"   成功交易: {successful} 笔")
        
        return {
            'success': True,
            'opportunities': len(opportunities),
            'trades': len(trade_results),
            'successful': successful,
            'results': trade_results
        }
    
    def run_continuous(self, interval_minutes: int = 10, max_iterations: int = None):
        """连续运行模式"""
        logger.info("🚀 启动连续交易模式")
        logger.info(f"⏰ 扫描间隔: {interval_minutes} 分钟")
        logger.info(f"🎭 模式: {'模拟交易' if self.config.dry_run else '实盘交易'}")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                if max_iterations and iteration > max_iterations:
                    logger.info(f"🏁 达到最大迭代次数: {max_iterations}")
                    break
                
                # 执行扫描
                result = self.run_single_scan()
                
                # 显示统计
                if iteration % 5 == 0:
                    self.print_stats()
                
                # 等待下次扫描
                if max_iterations is None or iteration < max_iterations:
                    logger.info(f"\n💤 等待 {interval_minutes} 分钟后进行下次扫描...")
                    time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 用户中断，交易已停止")
        except Exception as e:
            logger.error(f"❌ 运行异常: {e}")
        finally:
            self.print_stats()
    
    def print_stats(self):
        """打印统计信息"""
        logger.info("\n" + "="*60)
        logger.info("📈 交易统计")
        logger.info("="*60)
        logger.info(f"总扫描次数: {self.stats['total_scans']}")
        logger.info(f"发现机会: {self.stats['opportunities_found']}")
        logger.info(f"执行交易: {self.stats['trades_executed']}")
        logger.info(f"成功交易: {self.stats['successful_trades']}")
        
        if self.stats['trades_executed'] > 0:
            success_rate = self.stats['successful_trades'] / self.stats['trades_executed']
            logger.info(f"成功率: {success_rate:.1%}")
        
        logger.info("="*60)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket自动交易系统")
    parser.add_argument("--mode", choices=['single', 'continuous'], default='single',
                       help="运行模式: single(单次) 或 continuous(连续)")
    parser.add_argument("--interval", type=int, default=10,
                       help="连续模式的扫描间隔（分钟）")
    parser.add_argument("--max-iter", type=int,
                       help="最大迭代次数")
    
    args = parser.parse_args()
    
    # 创建交易机器人
    bot = TradingBot()
    
    # 显示配置信息
    logger.info("🔧 当前配置:")
    logger.info(f"   时间阈值: {bot.config.time_threshold_minutes} 分钟")
    logger.info(f"   胜率范围: {bot.config.min_confidence:.1%} - {bot.config.max_confidence:.1%}")
    logger.info(f"   交易金额: ${bot.config.trade_amount} USDC")
    logger.info(f"   模拟模式: {bot.config.dry_run}")
    
    # 执行交易
    if args.mode == 'single':
        bot.run_single_scan()
    else:
        bot.run_continuous(args.interval, args.max_iter)

if __name__ == "__main__":
    main()