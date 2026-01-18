import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DataSaver:
    """数据保存器 - 将获取的数据保存为CSV文件"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"创建数据目录: {self.data_dir}")
    
    def save_markets_data(self, markets: List[Dict[str, Any]]) -> str:
        """
        保存市场列表数据
        
        Args:
            markets: 市场数据列表
            
        Returns:
            保存的文件路径
        """
        if not markets:
            logger.warning("没有市场数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for market in markets:
            processed_data.append({
                'condition_id': market.get('condition_id', ''),
                'question': market.get('question', ''),
                'description': market.get('description', ''),
                'active': market.get('active', False),
                'closed': market.get('closed', False),
                'end_date_iso': market.get('end_date_iso', ''),
                'resolution': market.get('resolution', ''),
                'tags': ','.join(market.get('tags', [])),
                'created_at': market.get('created_at', ''),
                'updated_at': market.get('updated_at', ''),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存市场数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_market_detail(self, market_data: Dict[str, Any]) -> str:
        """
        保存单个市场详细数据
        
        Args:
            market_data: 市场详细数据
            
        Returns:
            保存的文件路径
        """
        if not market_data:
            logger.warning("没有市场详细数据需要保存")
            return ""
        
        condition_id = market_data.get('condition_id', 'unknown')
        
        # 准备基础市场数据
        basic_data = {
            'condition_id': condition_id,
            'question': market_data.get('question', ''),
            'description': market_data.get('description', ''),
            'active': market_data.get('active', False),
            'closed': market_data.get('closed', False),
            'end_date_iso': market_data.get('end_date_iso', ''),
            'resolution': market_data.get('resolution', ''),
            'tags': ','.join(market_data.get('tags', [])),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存基础数据
        df_basic = pd.DataFrame([basic_data])
        basic_filename = f"market_detail_{condition_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        basic_filepath = os.path.join(self.data_dir, basic_filename)
        df_basic.to_csv(basic_filepath, index=False, encoding='utf-8')
        
        logger.info(f"保存市场详细数据到: {basic_filepath}")
        return basic_filepath
    
    def save_prices_data(self, condition_id: str, prices: Dict[str, Any]) -> str:
        """
        保存价格数据
        
        Args:
            condition_id: 市场条件ID
            prices: 价格数据
            
        Returns:
            保存的文件路径
        """
        if not prices:
            logger.warning("没有价格数据需要保存")
            return ""
        
        # 准备价格数据
        processed_data = []
        timestamp = datetime.now().isoformat()
        
        if isinstance(prices, dict):
            for token_id, price in prices.items():
                processed_data.append({
                    'condition_id': condition_id,
                    'token_id': token_id,
                    'price': price,
                    'timestamp': timestamp
                })
        
        if not processed_data:
            logger.warning("价格数据格式不正确")
            return ""
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"prices_{condition_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存价格数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_orderbook_data(self, token_id: str, orderbook: Dict[str, Any]) -> str:
        """
        保存订单簿数据
        
        Args:
            token_id: 代币ID
            orderbook: 订单簿数据
            
        Returns:
            保存的文件路径
        """
        if not orderbook:
            logger.warning("没有订单簿数据需要保存")
            return ""
        
        timestamp = datetime.now().isoformat()
        
        # 处理买单数据
        bids_data = []
        for bid in orderbook.get('bids', []):
            bids_data.append({
                'token_id': token_id,
                'side': 'bid',
                'price': bid.get('price', ''),
                'size': bid.get('size', ''),
                'timestamp': timestamp
            })
        
        # 处理卖单数据
        asks_data = []
        for ask in orderbook.get('asks', []):
            asks_data.append({
                'token_id': token_id,
                'side': 'ask',
                'price': ask.get('price', ''),
                'size': ask.get('size', ''),
                'timestamp': timestamp
            })
        
        # 合并所有订单数据
        all_orders = bids_data + asks_data
        
        if not all_orders:
            logger.warning("订单簿数据为空")
            return ""
        
        # 保存为CSV
        df = pd.DataFrame(all_orders)
        filename = f"orderbook_{token_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存订单簿数据到: {filepath} ({len(all_orders)} 条记录)")
        
        return filepath
    
    def save_trades_data(self, trades: List[Dict[str, Any]]) -> str:
        """
        保存交易数据
        
        Args:
            trades: 交易数据列表
            
        Returns:
            保存的文件路径
        """
        if not trades:
            logger.warning("没有交易数据需要保存")
            return ""
        
        # 准备交易数据
        processed_data = []
        for trade in trades:
            processed_data.append({
                'market': trade.get('market', ''),
                'asset_id': trade.get('asset_id', ''),
                'price': trade.get('price', ''),
                'size': trade.get('size', ''),
                'side': trade.get('side', ''),
                'maker': trade.get('maker', ''),
                'taker': trade.get('taker', ''),
                'timestamp': trade.get('timestamp', ''),
                'saved_at': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存交易数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def append_to_daily_file(self, data_type: str, data: List[Dict[str, Any]]):
        """
        追加数据到日文件
        
        Args:
            data_type: 数据类型 (markets, prices, trades等)
            data: 要追加的数据
        """
        if not data:
            return
        
        today = datetime.now().strftime('%Y%m%d')
        filename = f"{data_type}_daily_{today}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df_new = pd.DataFrame(data)
        
        # 如果文件存在，追加数据；否则创建新文件
        if os.path.exists(filepath):
            df_new.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8')
        else:
            df_new.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"追加 {len(data)} 条 {data_type} 数据到: {filepath}")
    
    def get_saved_files(self) -> List[str]:
        """获取已保存的文件列表"""
        if not os.path.exists(self.data_dir):
            return []
        
        files = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(self.data_dir, filename)
                files.append(filepath)
        
        return sorted(files)
    
    def save_probable_markets_data(self, markets: List[Dict[str, Any]]) -> str:
        """
        保存Probable Markets市场列表数据
        
        Args:
            markets: 市场数据列表
            
        Returns:
            保存的文件路径
        """
        if not markets:
            logger.warning("没有Probable Markets市场数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for market in markets:
            processed_data.append({
                'id': market.get('id', ''),
                'title': market.get('title', ''),
                'description': market.get('description', ''),
                'status': market.get('status', ''),
                'category': market.get('category', ''),
                'created_at': market.get('created_at', ''),
                'updated_at': market.get('updated_at', ''),
                'close_date': market.get('close_date', ''),
                'resolve_date': market.get('resolve_date', ''),
                'volume': market.get('volume', 0),
                'liquidity': market.get('liquidity', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"probable_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Probable Markets市场数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_probable_market_detail(self, market_data: Dict[str, Any]) -> str:
        """
        保存Probable Markets单个市场详细数据
        
        Args:
            market_data: 市场详细数据
            
        Returns:
            保存的文件路径
        """
        if not market_data:
            logger.warning("没有Probable Markets市场详细数据需要保存")
            return ""
        
        market_id = market_data.get('id', 'unknown')
        
        # 准备基础市场数据
        basic_data = {
            'id': market_id,
            'title': market_data.get('title', ''),
            'description': market_data.get('description', ''),
            'status': market_data.get('status', ''),
            'category': market_data.get('category', ''),
            'created_at': market_data.get('created_at', ''),
            'updated_at': market_data.get('updated_at', ''),
            'close_date': market_data.get('close_date', ''),
            'resolve_date': market_data.get('resolve_date', ''),
            'volume': market_data.get('volume', 0),
            'liquidity': market_data.get('liquidity', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存基础数据
        df_basic = pd.DataFrame([basic_data])
        basic_filename = f"probable_market_detail_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        basic_filepath = os.path.join(self.data_dir, basic_filename)
        df_basic.to_csv(basic_filepath, index=False, encoding='utf-8')
        
        logger.info(f"保存Probable Markets市场详细数据到: {basic_filepath}")
        return basic_filepath
    
    def save_probable_outcomes_data(self, market_id: str, outcomes: List[Dict[str, Any]]) -> str:
        """
        保存Probable Markets结果选项数据
        
        Args:
            market_id: 市场ID
            outcomes: 结果选项数据列表
            
        Returns:
            保存的文件路径
        """
        if not outcomes:
            logger.warning("没有结果选项数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for outcome in outcomes:
            processed_data.append({
                'market_id': market_id,
                'id': outcome.get('id', ''),
                'title': outcome.get('title', ''),
                'description': outcome.get('description', ''),
                'probability': outcome.get('probability', 0),
                'price': outcome.get('price', 0),
                'volume': outcome.get('volume', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"probable_outcomes_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Probable Markets结果选项数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_probable_prices_data(self, market_id: str, prices: Dict[str, Any]) -> str:
        """
        保存Probable Markets价格数据
        
        Args:
            market_id: 市场ID
            prices: 价格数据
            
        Returns:
            保存的文件路径
        """
        if not prices:
            logger.warning("没有Probable Markets价格数据需要保存")
            return ""
        
        # 准备价格数据
        processed_data = []
        timestamp = datetime.now().isoformat()
        
        if isinstance(prices, dict):
            for outcome_id, price_info in prices.items():
                if isinstance(price_info, dict):
                    processed_data.append({
                        'market_id': market_id,
                        'outcome_id': outcome_id,
                        'price': price_info.get('price', 0),
                        'bid': price_info.get('bid', 0),
                        'ask': price_info.get('ask', 0),
                        'volume': price_info.get('volume', 0),
                        'timestamp': timestamp
                    })
                else:
                    processed_data.append({
                        'market_id': market_id,
                        'outcome_id': outcome_id,
                        'price': price_info,
                        'bid': 0,
                        'ask': 0,
                        'volume': 0,
                        'timestamp': timestamp
                    })
        
        if not processed_data:
            logger.warning("Probable Markets价格数据格式不正确")
            return ""
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"probable_prices_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Probable Markets价格数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_probable_trades_data(self, market_id: str, trades: List[Dict[str, Any]]) -> str:
        """
        保存Probable Markets交易数据
        
        Args:
            market_id: 市场ID
            trades: 交易数据列表
            
        Returns:
            保存的文件路径
        """
        if not trades:
            logger.warning("没有Probable Markets交易数据需要保存")
            return ""
        
        # 准备交易数据
        processed_data = []
        for trade in trades:
            processed_data.append({
                'market_id': market_id,
                'id': trade.get('id', ''),
                'outcome_id': trade.get('outcome_id', ''),
                'price': trade.get('price', ''),
                'size': trade.get('size', ''),
                'side': trade.get('side', ''),
                'user_id': trade.get('user_id', ''),
                'created_at': trade.get('created_at', ''),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"probable_trades_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Probable Markets交易数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_probable_categories_data(self, categories: List[Dict[str, Any]]) -> str:
        """
        保存Probable Markets类别数据
        
        Args:
            categories: 类别数据列表
            
        Returns:
            保存的文件路径
        """
        if not categories:
            logger.warning("没有Probable Markets类别数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for category in categories:
            processed_data.append({
                'id': category.get('id', ''),
                'name': category.get('name', ''),
                'description': category.get('description', ''),
                'market_count': category.get('market_count', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"probable_categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Probable Markets类别数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath

    def save_clob_markets_data(self, markets: List[Dict[str, Any]]) -> str:
        """
        保存CLOB市场列表数据
        
        Args:
            markets: 市场数据列表
            
        Returns:
            保存的文件路径
        """
        if not markets:
            logger.warning("没有CLOB市场数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for market in markets:
            processed_data.append({
                'condition_id': market.get('condition_id', ''),
                'question': market.get('question', ''),
                'description': market.get('description', ''),
                'market_slug': market.get('market_slug', ''),
                'end_date_iso': market.get('end_date_iso', ''),
                'game_start_time': market.get('game_start_time', ''),
                'seconds_delay': market.get('seconds_delay', 0),
                'fpmm': market.get('fpmm', ''),
                'maker_base_fee': market.get('maker_base_fee', 0),
                'taker_base_fee': market.get('taker_base_fee', 0),
                'active': market.get('active', False),
                'closed': market.get('closed', False),
                'archived': market.get('archived', False),
                'accepting_orders': market.get('accepting_orders', False),
                'minimum_order_size': market.get('minimum_order_size', 0),
                'minimum_tick_size': market.get('minimum_tick_size', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"clob_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存CLOB市场数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_clob_market_detail(self, market_data: Dict[str, Any]) -> str:
        """
        保存CLOB单个市场详细数据
        
        Args:
            market_data: 市场详细数据
            
        Returns:
            保存的文件路径
        """
        if not market_data:
            logger.warning("没有CLOB市场详细数据需要保存")
            return ""
        
        condition_id = market_data.get('condition_id', 'unknown')
        
        # 准备基础市场数据
        basic_data = {
            'condition_id': condition_id,
            'question': market_data.get('question', ''),
            'description': market_data.get('description', ''),
            'market_slug': market_data.get('market_slug', ''),
            'end_date_iso': market_data.get('end_date_iso', ''),
            'game_start_time': market_data.get('game_start_time', ''),
            'seconds_delay': market_data.get('seconds_delay', 0),
            'fpmm': market_data.get('fpmm', ''),
            'maker_base_fee': market_data.get('maker_base_fee', 0),
            'taker_base_fee': market_data.get('taker_base_fee', 0),
            'active': market_data.get('active', False),
            'closed': market_data.get('closed', False),
            'archived': market_data.get('archived', False),
            'accepting_orders': market_data.get('accepting_orders', False),
            'minimum_order_size': market_data.get('minimum_order_size', 0),
            'minimum_tick_size': market_data.get('minimum_tick_size', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存基础数据
        df_basic = pd.DataFrame([basic_data])
        basic_filename = f"clob_market_detail_{condition_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        basic_filepath = os.path.join(self.data_dir, basic_filename)
        df_basic.to_csv(basic_filepath, index=False, encoding='utf-8')
        
        # 保存代币信息
        tokens = market_data.get('tokens', [])
        if tokens:
            token_data = []
            for token in tokens:
                token_data.append({
                    'condition_id': condition_id,
                    'token_id': token.get('token_id', ''),
                    'outcome': token.get('outcome', ''),
                    'winner': token.get('winner', False),
                    'timestamp': datetime.now().isoformat()
                })
            
            df_tokens = pd.DataFrame(token_data)
            tokens_filename = f"clob_market_tokens_{condition_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            tokens_filepath = os.path.join(self.data_dir, tokens_filename)
            df_tokens.to_csv(tokens_filepath, index=False, encoding='utf-8')
            logger.info(f"保存CLOB市场代币数据到: {tokens_filepath}")
        
        logger.info(f"保存CLOB市场详细数据到: {basic_filepath}")
        return basic_filepath
    
    def save_clob_orderbook_data(self, token_id: str, orderbook: Dict[str, Any]) -> str:
        """
        保存CLOB订单簿数据
        
        Args:
            token_id: 代币ID
            orderbook: 订单簿数据
            
        Returns:
            保存的文件路径
        """
        if not orderbook:
            logger.warning("没有CLOB订单簿数据需要保存")
            return ""
        
        timestamp = datetime.now().isoformat()
        
        # 处理买单数据
        bids_data = []
        for bid in orderbook.get('bids', []):
            bids_data.append({
                'token_id': token_id,
                'side': 'bid',
                'price': bid.get('price', ''),
                'size': bid.get('size', ''),
                'timestamp': timestamp
            })
        
        # 处理卖单数据
        asks_data = []
        for ask in orderbook.get('asks', []):
            asks_data.append({
                'token_id': token_id,
                'side': 'ask',
                'price': ask.get('price', ''),
                'size': ask.get('size', ''),
                'timestamp': timestamp
            })
        
        # 合并所有订单数据
        all_orders = bids_data + asks_data
        
        if not all_orders:
            logger.warning("CLOB订单簿数据为空")
            return ""
        
        # 保存为CSV
        df = pd.DataFrame(all_orders)
        filename = f"clob_orderbook_{token_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存CLOB订单簿数据到: {filepath} ({len(all_orders)} 条记录)")
        
        return filepath
    
    def save_clob_trades_data(self, trades: List[Dict[str, Any]]) -> str:
        """
        保存CLOB交易数据
        
        Args:
            trades: 交易数据列表
            
        Returns:
            保存的文件路径
        """
        if not trades:
            logger.warning("没有CLOB交易数据需要保存")
            return ""
        
        # 准备交易数据
        processed_data = []
        for trade in trades:
            processed_data.append({
                'id': trade.get('id', ''),
                'market': trade.get('market', ''),
                'asset_id': trade.get('asset_id', ''),
                'side': trade.get('side', ''),
                'size': trade.get('size', ''),
                'price': trade.get('price', ''),
                'fee_rate_bps': trade.get('fee_rate_bps', 0),
                'fee': trade.get('fee', ''),
                'status': trade.get('status', ''),
                'match_time': trade.get('match_time', ''),
                'last_update': trade.get('last_update', ''),
                'maker_address': trade.get('maker_address', ''),
                'taker_address': trade.get('taker_address', ''),
                'maker_order_id': trade.get('maker_order_id', ''),
                'taker_order_id': trade.get('taker_order_id', ''),
                'transaction_hash': trade.get('transaction_hash', ''),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"clob_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存CLOB交易数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_clob_prices_data(self, prices: Dict[str, Any]) -> str:
        """
        保存CLOB价格数据
        
        Args:
            prices: 价格数据
            
        Returns:
            保存的文件路径
        """
        if not prices:
            logger.warning("没有CLOB价格数据需要保存")
            return ""
        
        # 准备价格数据
        processed_data = []
        timestamp = datetime.now().isoformat()
        
        for token_id, price_info in prices.items():
            if isinstance(price_info, dict):
                processed_data.append({
                    'token_id': token_id,
                    'price': price_info.get('price', ''),
                    'timestamp': timestamp
                })
            else:
                processed_data.append({
                    'token_id': token_id,
                    'price': price_info,
                    'timestamp': timestamp
                })
        
        if not processed_data:
            logger.warning("CLOB价格数据格式不正确")
            return ""
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"clob_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存CLOB价格数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath

    def save_polymarket_events_data(self, events: List[Dict[str, Any]]) -> str:
        """
        保存Polymarket事件数据
        
        Args:
            events: 事件数据列表
            
        Returns:
            保存的文件路径
        """
        if not events:
            logger.warning("没有Polymarket事件数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for event in events:
            processed_data.append({
                'id': event.get('id', ''),
                'slug': event.get('slug', ''),
                'title': event.get('title', event.get('name', '')),
                'description': event.get('description', ''),
                'image': event.get('image', ''),
                'active': event.get('active', False),
                'closed': event.get('closed', False),
                'archived': event.get('archived', False),
                'start_date': event.get('start_date', ''),
                'end_date': event.get('end_date', ''),
                'created_at': event.get('created_at', ''),
                'updated_at': event.get('updated_at', ''),
                'category': event.get('category', ''),
                'tags': ','.join([str(tag) if isinstance(tag, str) else tag.get('name', str(tag)) for tag in event.get('tags', [])]) if event.get('tags') else '',
                'volume': event.get('volume', 0),
                'liquidity': event.get('liquidity', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"polymarket_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Polymarket事件数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_polymarket_event_detail(self, event_data: Dict[str, Any]) -> str:
        """
        保存Polymarket单个事件详细数据
        
        Args:
            event_data: 事件详细数据
            
        Returns:
            保存的文件路径
        """
        if not event_data:
            logger.warning("没有Polymarket事件详细数据需要保存")
            return ""
        
        event_id = event_data.get('id', event_data.get('slug', 'unknown'))
        
        # 准备基础事件数据
        basic_data = {
            'id': event_data.get('id', ''),
            'slug': event_data.get('slug', ''),
            'title': event_data.get('title', event_data.get('name', '')),
            'description': event_data.get('description', ''),
            'image': event_data.get('image', ''),
            'active': event_data.get('active', False),
            'closed': event_data.get('closed', False),
            'archived': event_data.get('archived', False),
            'start_date': event_data.get('start_date', ''),
            'end_date': event_data.get('end_date', ''),
            'created_at': event_data.get('created_at', ''),
            'updated_at': event_data.get('updated_at', ''),
            'category': event_data.get('category', ''),
            'tags': ','.join([str(tag) if isinstance(tag, str) else tag.get('name', str(tag)) for tag in event_data.get('tags', [])]) if event_data.get('tags') else '',
            'volume': event_data.get('volume', 0),
            'liquidity': event_data.get('liquidity', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存基础数据
        df_basic = pd.DataFrame([basic_data])
        basic_filename = f"polymarket_event_detail_{event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        basic_filepath = os.path.join(self.data_dir, basic_filename)
        df_basic.to_csv(basic_filepath, index=False, encoding='utf-8')
        
        # 保存市场信息
        markets = event_data.get('markets', [])
        if markets:
            market_data = []
            for market in markets:
                market_data.append({
                    'event_id': event_id,
                    'market_id': market.get('id', ''),
                    'market_slug': market.get('slug', ''),
                    'question': market.get('question', ''),
                    'description': market.get('description', ''),
                    'active': market.get('active', False),
                    'closed': market.get('closed', False),
                    'volume': market.get('volume', 0),
                    'timestamp': datetime.now().isoformat()
                })
            
            df_markets = pd.DataFrame(market_data)
            markets_filename = f"polymarket_event_markets_{event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            markets_filepath = os.path.join(self.data_dir, markets_filename)
            df_markets.to_csv(markets_filepath, index=False, encoding='utf-8')
            logger.info(f"保存Polymarket事件市场数据到: {markets_filepath}")
        
        logger.info(f"保存Polymarket事件详细数据到: {basic_filepath}")
        return basic_filepath
    
    def save_polymarket_markets_data(self, markets: List[Dict[str, Any]]) -> str:
        """
        保存Polymarket市场数据
        
        Args:
            markets: 市场数据列表
            
        Returns:
            保存的文件路径
        """
        if not markets:
            logger.warning("没有Polymarket市场数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for market in markets:
            processed_data.append({
                'id': market.get('id', ''),
                'slug': market.get('slug', ''),
                'question': market.get('question', ''),
                'description': market.get('description', ''),
                'event_slug': market.get('event_slug', ''),
                'active': market.get('active', False),
                'closed': market.get('closed', False),
                'archived': market.get('archived', False),
                'start_date': market.get('start_date', ''),
                'end_date': market.get('end_date', ''),
                'end_date_iso': market.get('end_date_iso', ''),
                'created_at': market.get('created_at', ''),
                'updated_at': market.get('updated_at', ''),
                'category': market.get('category', ''),
                'tags': ','.join([str(tag) if isinstance(tag, str) else tag.get('name', str(tag)) for tag in market.get('tags', [])]) if market.get('tags') else '',
                'volume': market.get('volume', 0),
                'liquidity': market.get('liquidity', 0),
                'outcome_prices': market.get('outcome_prices', ''),
                'outcomes': market.get('outcomes', ''),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"polymarket_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Polymarket市场数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_polymarket_market_detail(self, market_data: Dict[str, Any]) -> str:
        """
        保存Polymarket单个市场详细数据
        
        Args:
            market_data: 市场详细数据
            
        Returns:
            保存的文件路径
        """
        if not market_data:
            logger.warning("没有Polymarket市场详细数据需要保存")
            return ""
        
        market_id = market_data.get('id', market_data.get('slug', 'unknown'))
        
        # 准备基础市场数据
        basic_data = {
            'id': market_data.get('id', ''),
            'slug': market_data.get('slug', ''),
            'question': market_data.get('question', ''),
            'description': market_data.get('description', ''),
            'event_slug': market_data.get('event_slug', ''),
            'active': market_data.get('active', False),
            'closed': market_data.get('closed', False),
            'archived': market_data.get('archived', False),
            'start_date': market_data.get('start_date', ''),
            'end_date': market_data.get('end_date', ''),
            'end_date_iso': market_data.get('end_date_iso', ''),
            'created_at': market_data.get('created_at', ''),
            'updated_at': market_data.get('updated_at', ''),
            'category': market_data.get('category', ''),
            'tags': ','.join([str(tag) if isinstance(tag, str) else tag.get('name', str(tag)) for tag in market_data.get('tags', [])]) if market_data.get('tags') else '',
            'volume': market_data.get('volume', 0),
            'liquidity': market_data.get('liquidity', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存基础数据
        df_basic = pd.DataFrame([basic_data])
        basic_filename = f"polymarket_market_detail_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        basic_filepath = os.path.join(self.data_dir, basic_filename)
        df_basic.to_csv(basic_filepath, index=False, encoding='utf-8')
        
        # 保存结果选项信息
        outcomes = market_data.get('outcomes', [])
        if outcomes:
            outcome_data = []
            for outcome in outcomes:
                outcome_data.append({
                    'market_id': market_id,
                    'outcome_id': outcome.get('id', ''),
                    'outcome_slug': outcome.get('slug', ''),
                    'name': outcome.get('name', ''),
                    'price': outcome.get('price', 0),
                    'timestamp': datetime.now().isoformat()
                })
            
            df_outcomes = pd.DataFrame(outcome_data)
            outcomes_filename = f"polymarket_market_outcomes_{market_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            outcomes_filepath = os.path.join(self.data_dir, outcomes_filename)
            df_outcomes.to_csv(outcomes_filepath, index=False, encoding='utf-8')
            logger.info(f"保存Polymarket市场结果选项数据到: {outcomes_filepath}")
        
        logger.info(f"保存Polymarket市场详细数据到: {basic_filepath}")
        return basic_filepath
    
    def save_polymarket_market_history(self, market_slug: str, history_data: List[Dict[str, Any]]) -> str:
        """
        保存Polymarket市场历史数据
        
        Args:
            market_slug: 市场slug
            history_data: 历史数据列表
            
        Returns:
            保存的文件路径
        """
        if not history_data:
            logger.warning("没有Polymarket市场历史数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for record in history_data:
            processed_data.append({
                'market_slug': market_slug,
                'timestamp': record.get('timestamp', ''),
                'price': record.get('price', 0),
                'volume': record.get('volume', 0),
                'outcome_id': record.get('outcome_id', ''),
                'outcome_name': record.get('outcome_name', ''),
                'saved_at': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"polymarket_market_history_{market_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Polymarket市场历史数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath
    
    def save_polymarket_categories_data(self, categories: List[Dict[str, Any]]) -> str:
        """
        保存Polymarket分类数据
        
        Args:
            categories: 分类数据列表
            
        Returns:
            保存的文件路径
        """
        if not categories:
            logger.warning("没有Polymarket分类数据需要保存")
            return ""
        
        # 准备数据
        processed_data = []
        for category in categories:
            processed_data.append({
                'id': category.get('id', ''),
                'name': category.get('name', ''),
                'slug': category.get('slug', ''),
                'description': category.get('description', ''),
                'image': category.get('image', ''),
                'event_count': category.get('event_count', 0),
                'market_count': category.get('market_count', 0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 保存为CSV
        df = pd.DataFrame(processed_data)
        filename = f"polymarket_categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"保存Polymarket分类数据到: {filepath} ({len(processed_data)} 条记录)")
        
        return filepath

    def cleanup_old_files(self, days: int = 7):
        """清理旧文件"""
        if not os.path.exists(self.data_dir):
            return
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(self.data_dir, filename)
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    logger.info(f"删除旧文件: {filepath}")