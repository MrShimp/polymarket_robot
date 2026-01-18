import requests
import json
import time
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from export.data_saver import DataSaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolymarketCLOBClient:
    """
    Polymarket CLOB (Central Limit Order Book) API客户端
    基于官方文档: https://docs.polymarket.com/developers/CLOB/quickstart
    """
    
    def __init__(self, 
                 base_url: str = "https://clob.polymarket.com",
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 save_data: bool = True):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.save_data = save_data
        self.data_saver = DataSaver() if save_data else None
        self.session = requests.Session()
        
        # 设置基础请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://polymarket.com/'
        })
        
        # 如果提供了API密钥，添加认证头
        if self.api_key:
            self.session.headers.update({
                'POLY-ADDRESS': self.api_key,
                'POLY-SIGNATURE': '',  # 将在每个请求中动态设置
                'POLY-TIMESTAMP': '',  # 将在每个请求中动态设置
                'POLY-NONCE': '',      # 将在每个请求中动态设置
            })
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = '') -> str:
        """
        生成API签名
        
        Args:
            timestamp: 时间戳
            method: HTTP方法
            path: API路径
            body: 请求体
            
        Returns:
            签名字符串
        """
        if not self.api_secret:
            return ''
        
        message = timestamp + method.upper() + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_authenticated_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送认证请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: 请求数据
            
        Returns:
            响应数据或None
        """
        url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        nonce = str(int(time.time() * 1000000))
        
        # 准备请求体
        body = json.dumps(data) if data else ''
        
        # 生成签名
        signature = self._generate_signature(timestamp, method, endpoint, body)
        
        # 设置认证头
        headers = {
            'POLY-ADDRESS': self.api_key or '',
            'POLY-SIGNATURE': signature,
            'POLY-TIMESTAMP': timestamp,
            'POLY-NONCE': nonce,
        }
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"认证请求失败: {e}")
            return None
    
    def _make_public_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送公开请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            
        Returns:
            响应数据或None
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=10)
            else:
                raise ValueError(f"公开API不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"公开请求失败: {e}")
            return None
    
    # ========== 公开市场数据API ==========
    
    def get_markets(self, next_cursor: Optional[str] = None, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取市场列表
        
        Args:
            next_cursor: 分页游标
            limit: 返回结果数量限制
            
        Returns:
            市场数据或None
        """
        params = {'limit': limit}
        if next_cursor:
            params['next_cursor'] = next_cursor
        
        data = self._make_public_request('GET', '/markets', params)
        
        if data and self.save_data and self.data_saver:
            markets = data.get('data', [])
            if markets:
                self.data_saver.save_clob_markets_data(markets)
        
        return data
    
    def get_market(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定市场信息
        
        Args:
            condition_id: 市场条件ID
            
        Returns:
            市场数据或None
        """
        data = self._make_public_request('GET', f'/markets/{condition_id}')
        
        if data and self.save_data and self.data_saver:
            self.data_saver.save_clob_market_detail(data)
        
        return data
    
    def get_orderbook(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单簿
        
        Args:
            token_id: 代币ID
            
        Returns:
            订单簿数据或None
        """
        params = {'token_id': token_id}
        data = self._make_public_request('GET', '/book', params)
        
        if data and self.save_data and self.data_saver:
            self.data_saver.save_clob_orderbook_data(token_id, data)
        
        return data
    
    def get_trades(self, 
                  market: Optional[str] = None,
                  asset_id: Optional[str] = None,
                  maker: Optional[str] = None,
                  next_cursor: Optional[str] = None,
                  limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取交易历史
        
        Args:
            market: 市场ID
            asset_id: 资产ID
            maker: 做市商地址
            next_cursor: 分页游标
            limit: 返回结果数量限制
            
        Returns:
            交易数据或None
        """
        params = {'limit': limit}
        if market:
            params['market'] = market
        if asset_id:
            params['asset_id'] = asset_id
        if maker:
            params['maker'] = maker
        if next_cursor:
            params['next_cursor'] = next_cursor
        
        data = self._make_public_request('GET', '/trades', params)
        
        if data and self.save_data and self.data_saver:
            trades = data.get('data', [])
            if trades:
                self.data_saver.save_clob_trades_data(trades)
        
        return data
    
    def get_prices(self, market: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取价格信息
        
        Args:
            market: 市场ID
            
        Returns:
            价格数据或None
        """
        params = {}
        if market:
            params['market'] = market
        
        data = self._make_public_request('GET', '/prices', params)
        
        if data and self.save_data and self.data_saver:
            self.data_saver.save_clob_prices_data(data)
        
        return data
    
    def get_last_trade_price(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最后交易价格
        
        Args:
            token_id: 代币ID
            
        Returns:
            价格数据或None
        """
        params = {'token_id': token_id}
        return self._make_public_request('GET', '/last-trade-price', params)
    
    def get_midpoint(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        获取中间价
        
        Args:
            token_id: 代币ID
            
        Returns:
            中间价数据或None
        """
        params = {'token_id': token_id}
        return self._make_public_request('GET', '/midpoint', params)
    
    def get_spread(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        获取买卖价差
        
        Args:
            token_id: 代币ID
            
        Returns:
            价差数据或None
        """
        params = {'token_id': token_id}
        return self._make_public_request('GET', '/spread', params)
    
    # ========== 认证用户API ==========
    
    def get_balance(self, asset_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取账户余额
        
        Args:
            asset_type: 资产类型筛选
            
        Returns:
            余额数据或None
        """
        if not self.api_key:
            logger.error("获取余额需要API密钥")
            return None
        
        params = {}
        if asset_type:
            params['asset_type'] = asset_type
        
        return self._make_authenticated_request('GET', '/balance', params)
    
    def get_orders(self, 
                  market: Optional[str] = None,
                  asset_id: Optional[str] = None,
                  next_cursor: Optional[str] = None,
                  limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取用户订单
        
        Args:
            market: 市场ID
            asset_id: 资产ID
            next_cursor: 分页游标
            limit: 返回结果数量限制
            
        Returns:
            订单数据或None
        """
        if not self.api_key:
            logger.error("获取订单需要API密钥")
            return None
        
        params = {'limit': limit}
        if market:
            params['market'] = market
        if asset_id:
            params['asset_id'] = asset_id
        if next_cursor:
            params['next_cursor'] = next_cursor
        
        return self._make_authenticated_request('GET', '/orders', params)
    
    def create_order(self, 
                    token_id: str,
                    price: str,
                    size: str,
                    side: str,
                    fee_rate_bps: Optional[int] = None,
                    nonce: Optional[int] = None,
                    expiration: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        创建订单
        
        Args:
            token_id: 代币ID
            price: 价格
            size: 数量
            side: 买卖方向 (BUY/SELL)
            fee_rate_bps: 手续费率(基点)
            nonce: 随机数
            expiration: 过期时间
            
        Returns:
            订单创建结果或None
        """
        if not self.api_key:
            logger.error("创建订单需要API密钥")
            return None
        
        data = {
            'token_id': token_id,
            'price': price,
            'size': size,
            'side': side.upper()
        }
        
        if fee_rate_bps is not None:
            data['fee_rate_bps'] = fee_rate_bps
        if nonce is not None:
            data['nonce'] = nonce
        if expiration is not None:
            data['expiration'] = expiration
        
        return self._make_authenticated_request('POST', '/order', data=data)
    
    def cancel_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            取消结果或None
        """
        if not self.api_key:
            logger.error("取消订单需要API密钥")
            return None
        
        return self._make_authenticated_request('DELETE', f'/order/{order_id}')
    
    def cancel_all_orders(self, market: Optional[str] = None, asset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        取消所有订单
        
        Args:
            market: 市场ID (可选，用于筛选)
            asset_id: 资产ID (可选，用于筛选)
            
        Returns:
            取消结果或None
        """
        if not self.api_key:
            logger.error("取消订单需要API密钥")
            return None
        
        params = {}
        if market:
            params['market'] = market
        if asset_id:
            params['asset_id'] = asset_id
        
        return self._make_authenticated_request('DELETE', '/orders', params)
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单状态或None
        """
        if not self.api_key:
            logger.error("获取订单状态需要API密钥")
            return None
        
        return self._make_authenticated_request('GET', f'/order/{order_id}')
    
    def get_user_trades(self, 
                       market: Optional[str] = None,
                       asset_id: Optional[str] = None,
                       next_cursor: Optional[str] = None,
                       limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取用户交易历史
        
        Args:
            market: 市场ID
            asset_id: 资产ID
            next_cursor: 分页游标
            limit: 返回结果数量限制
            
        Returns:
            交易数据或None
        """
        if not self.api_key:
            logger.error("获取用户交易历史需要API密钥")
            return None
        
        params = {'limit': limit}
        if market:
            params['market'] = market
        if asset_id:
            params['asset_id'] = asset_id
        if next_cursor:
            params['next_cursor'] = next_cursor
        
        return self._make_authenticated_request('GET', '/user-trades', params)
    
    # ========== 便利方法 ==========
    
    def get_all_markets(self) -> List[Dict[str, Any]]:
        """
        获取所有市场数据 (处理分页)
        
        Returns:
            所有市场数据列表
        """
        all_markets = []
        next_cursor = None
        
        while True:
            data = self.get_markets(next_cursor=next_cursor, limit=100)
            if not data:
                break
            
            markets = data.get('data', [])
            all_markets.extend(markets)
            
            next_cursor = data.get('next_cursor')
            if not next_cursor:
                break
            
            time.sleep(0.1)  # 避免请求过于频繁
        
        logger.info(f"获取到总共 {len(all_markets)} 个市场")
        return all_markets
    
    def get_all_trades(self, market: Optional[str] = None, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有交易数据 (处理分页)
        
        Args:
            market: 市场ID
            asset_id: 资产ID
            
        Returns:
            所有交易数据列表
        """
        all_trades = []
        next_cursor = None
        
        while True:
            data = self.get_trades(market=market, asset_id=asset_id, next_cursor=next_cursor, limit=100)
            if not data:
                break
            
            trades = data.get('data', [])
            all_trades.extend(trades)
            
            next_cursor = data.get('next_cursor')
            if not next_cursor:
                break
            
            time.sleep(0.1)  # 避免请求过于频繁
        
        logger.info(f"获取到总共 {len(all_trades)} 条交易记录")
        return all_trades
    
    def get_market_summary(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        获取市场摘要信息
        
        Args:
            condition_id: 市场条件ID
            
        Returns:
            市场摘要数据或None
        """
        market = self.get_market(condition_id)
        if not market:
            return None
        
        # 获取价格信息
        prices = self.get_prices(market=condition_id)
        
        # 组合摘要信息
        summary = {
            'market': market,
            'prices': prices,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary