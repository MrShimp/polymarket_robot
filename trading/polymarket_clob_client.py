#!/usr/bin/env python3
"""
Polymarket CLOB (Central Limit Order Book) 交易客户端
基于私钥签名的认证方式，类似于JavaScript版本的实现
"""

import json
import time
import hmac
import hashlib
import base64
from typing import Dict, List, Optional, Any
from decimal import Decimal
import requests
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_defunct

class PolymarketCLOBClient:
    """Polymarket CLOB API 客户端 - 使用私钥认证"""
    
    def __init__(self, 
                 host: str = "https://clob.polymarket.com",
                 chain_id: int = 137,
                 private_key: str = "",
                 use_testnet: bool = False):
        """
        初始化CLOB客户端
        
        Args:
            host: API主机地址
            chain_id: 链ID (137=Polygon主网, 80002=Polygon Amoy测试网)
            private_key: 私钥 (0x开头的十六进制字符串)
            use_testnet: 是否使用测试网
        """
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key
        self.use_testnet = use_testnet
        
        # 如果是测试网但没有指定host，使用默认测试网地址
        if use_testnet and host == "https://clob.polymarket.com":
            self.host = "https://clob-staging.polymarket.com"
            self.chain_id = 80002  # Polygon Amoy testnet
        
        # 创建账户对象
        if self.private_key:
            try:
                # 确保私钥格式正确
                if not self.private_key.startswith('0x'):
                    self.private_key = '0x' + self.private_key
                
                self.account = Account.from_key(self.private_key)
                self.address = self.account.address
            except Exception as e:
                raise ValueError(f"无效的私钥: {e}")
        else:
            self.account = None
            self.address = None
        
        self.session = requests.Session()
        
    def _create_signature(self, message: str) -> str:
        """创建消息签名"""
        if not self.account:
            raise ValueError("未配置私钥，无法创建签名")
        
        # 创建以太坊消息
        message_hash = encode_defunct(text=message)
        
        # 使用私钥签名
        signed_message = self.account.sign_message(message_hash)
        
        # 返回签名的十六进制表示
        return signed_message.signature.hex()
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """获取认证头"""
        if not self.account:
            return {'Content-Type': 'application/json'}
        
        timestamp = str(int(time.time() * 1000))  # 毫秒时间戳
        
        # 创建签名消息
        message = f"{method}{path}{body}{timestamp}"
        signature = self._create_signature(message)
        
        return {
            'Content-Type': 'application/json',
            'POLY-ADDRESS': self.address,
            'POLY-SIGNATURE': signature,
            'POLY-TIMESTAMP': timestamp,
            'POLY-NONCE': timestamp  # 使用时间戳作为nonce
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """发送API请求"""
        url = f"{self.host}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_auth_headers(method, endpoint, body)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, data=body)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, data=body)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            
            # 处理空响应
            if not response.content:
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            raise
    
    # ========== 账户相关 ==========
    
    def get_balance(self) -> Dict:
        """获取账户余额"""
        return self._make_request('GET', '/balance')
    
    def get_positions(self) -> List[Dict]:
        """获取持仓信息"""
        result = self._make_request('GET', '/positions')
        return result if isinstance(result, list) else result.get('positions', [])
    
    # ========== 市场数据 ==========
    
    def get_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取市场列表"""
        params = {'limit': limit, 'offset': offset}
        result = self._make_request('GET', '/markets', params=params)
        return result if isinstance(result, list) else result.get('data', [])
    
    def get_market(self, condition_id: str) -> Dict:
        """获取特定市场信息"""
        return self._make_request('GET', f'/markets/{condition_id}')
    
    def get_orderbook(self, token_id: str) -> Dict:
        """获取订单簿"""
        return self._make_request('GET', f'/book', params={'token_id': token_id})
    
    def get_trades(self, token_id: str, limit: int = 100) -> List[Dict]:
        """获取交易历史"""
        params = {'token_id': token_id, 'limit': limit}
        result = self._make_request('GET', f'/trades', params=params)
        return result if isinstance(result, list) else result.get('data', [])
    
    # ========== 订单管理 ==========
    
    def create_order(self,
                    token_id: str,
                    side: str,  # 'BUY' or 'SELL'
                    size: str,  # 订单数量
                    price: str,  # 订单价格
                    order_type: str = 'LIMIT',  # 'LIMIT' or 'MARKET'
                    time_in_force: str = 'GTC',  # 'GTC', 'IOC', 'FOK'
                    reduce_only: bool = False,
                    client_order_id: Optional[str] = None) -> Dict:
        """
        创建订单
        
        Args:
            token_id: 代币ID
            side: 买卖方向 ('BUY' or 'SELL')
            size: 订单数量
            price: 订单价格
            order_type: 订单类型 ('LIMIT' or 'MARKET')
            time_in_force: 时间有效性 ('GTC', 'IOC', 'FOK')
            reduce_only: 是否仅减仓
            client_order_id: 客户端订单ID
        """
        data = {
            'tokenID': token_id,
            'side': side.upper(),
            'size': str(size),
            'price': str(price),
            'type': order_type.upper(),
            'timeInForce': time_in_force.upper(),
            'reduceOnly': reduce_only
        }
        
        if client_order_id:
            data['clientOrderID'] = client_order_id
        
        return self._make_request('POST', '/order', data)
    
    def cancel_order(self, order_id: str) -> Dict:
        """取消订单"""
        data = {'orderID': order_id}
        return self._make_request('DELETE', '/order', data)
    
    def cancel_all_orders(self, token_id: Optional[str] = None) -> Dict:
        """取消所有订单"""
        data = {}
        if token_id:
            data['tokenID'] = token_id
        return self._make_request('DELETE', '/orders', data)
    
    def get_orders(self, token_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """获取订单列表"""
        params = {}
        if token_id:
            params['tokenID'] = token_id
        if status:
            params['status'] = status
        
        result = self._make_request('GET', '/orders', params=params)
        return result if isinstance(result, list) else result.get('data', [])
    
    def get_order(self, order_id: str) -> Dict:
        """获取特定订单信息"""
        return self._make_request('GET', f'/order/{order_id}')
    
    # ========== 高级交易功能 ==========
    
    def create_market_order(self, token_id: str, side: str, size: str) -> Dict:
        """创建市价单"""
        return self.create_order(
            token_id=token_id,
            side=side,
            size=size,
            price='0',  # 市价单价格设为0
            order_type='MARKET'
        )
    
    def create_limit_order(self, token_id: str, side: str, size: str, price: str) -> Dict:
        """创建限价单"""
        return self.create_order(
            token_id=token_id,
            side=side,
            size=size,
            price=price,
            order_type='LIMIT'
        )
    
    def buy_market(self, token_id: str, size: str) -> Dict:
        """市价买入"""
        return self.create_market_order(token_id, 'BUY', size)
    
    def sell_market(self, token_id: str, size: str) -> Dict:
        """市价卖出"""
        return self.create_market_order(token_id, 'SELL', size)
    
    def buy_limit(self, token_id: str, size: str, price: str) -> Dict:
        """限价买入"""
        return self.create_limit_order(token_id, 'BUY', size, price)
    
    def sell_limit(self, token_id: str, size: str, price: str) -> Dict:
        """限价卖出"""
        return self.create_limit_order(token_id, 'SELL', size, price)
    
    # ========== 工具方法 ==========
    
    def get_token_balance(self, token_id: str) -> Decimal:
        """获取特定代币余额"""
        try:
            balance_info = self.get_balance()
            balances = balance_info.get('balances', [])
            
            for balance in balances:
                if balance.get('tokenID') == token_id:
                    return Decimal(balance.get('balance', '0'))
            return Decimal('0')
        except Exception:
            return Decimal('0')
    
    def get_usdc_balance(self) -> Decimal:
        """获取USDC余额"""
        try:
            balance_info = self.get_balance()
            return Decimal(balance_info.get('usdcBalance', '0'))
        except Exception:
            return Decimal('0')
    
    def calculate_order_value(self, size: str, price: str) -> Decimal:
        """计算订单价值"""
        return Decimal(size) * Decimal(price)
    
    def get_best_bid_ask(self, token_id: str) -> Dict[str, Optional[str]]:
        """获取最佳买卖价"""
        try:
            orderbook = self.get_orderbook(token_id)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            best_bid = bids[0]['price'] if bids else None
            best_ask = asks[0]['price'] if asks else None
            
            spread = None
            if best_bid and best_ask:
                spread = str(Decimal(best_ask) - Decimal(best_bid))
            
            return {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': spread
            }
        except Exception:
            return {
                'best_bid': None,
                'best_ask': None,
                'spread': None
            }
    
    def estimate_market_impact(self, token_id: str, side: str, size: str) -> Dict:
        """估算市场冲击"""
        try:
            orderbook = self.get_orderbook(token_id)
            
            if side.upper() == 'BUY':
                orders = orderbook.get('asks', [])
            else:
                orders = orderbook.get('bids', [])
            
            remaining_size = Decimal(size)
            total_cost = Decimal('0')
            filled_orders = []
            
            for order in orders:
                order_size = Decimal(order['size'])
                order_price = Decimal(order['price'])
                
                if remaining_size <= order_size:
                    # 部分成交这个订单
                    filled_orders.append({
                        'price': str(order_price),
                        'size': str(remaining_size),
                        'cost': str(remaining_size * order_price)
                    })
                    total_cost += remaining_size * order_price
                    remaining_size = Decimal('0')
                    break
                else:
                    # 完全成交这个订单
                    filled_orders.append({
                        'price': str(order_price),
                        'size': str(order_size),
                        'cost': str(order_size * order_price)
                    })
                    total_cost += order_size * order_price
                    remaining_size -= order_size
            
            avg_price = total_cost / Decimal(size) if total_cost > 0 else Decimal('0')
            
            return {
                'total_cost': str(total_cost),
                'average_price': str(avg_price),
                'filled_orders': filled_orders,
                'unfilled_size': str(remaining_size),
                'can_fill_completely': remaining_size == 0
            }
        except Exception as e:
            return {
                'error': str(e),
                'total_cost': '0',
                'average_price': '0',
                'filled_orders': [],
                'unfilled_size': size,
                'can_fill_completely': False
            }


class PolymarketTrader:
    """Polymarket交易器 - 高级交易功能封装"""
    
    def __init__(self, clob_client: PolymarketCLOBClient):
        self.client = clob_client
    
    def execute_strategy_trade(self, 
                             market_data: Dict,
                             trade_amount: str,
                             max_slippage: float = 0.02,
                             dry_run: bool = True) -> Dict:
        """
        执行策略交易
        
        Args:
            market_data: 市场数据（来自策略扫描结果）
            trade_amount: 交易金额（USDC）
            max_slippage: 最大滑点
            dry_run: 是否为模拟交易
        """
        try:
            # 解析市场数据
            token_ids = json.loads(market_data.get('clobTokenIds', '[]'))
            outcomes = json.loads(market_data.get('outcomes', '[]'))
            prices = json.loads(market_data.get('outcomePrices', '[]'))
            
            winning_option = market_data.get('strategy_winning_option', '')
            confidence = float(market_data.get('strategy_confidence', 0))
            
            # 确定要交易的代币
            if winning_option == 'Yes' and len(token_ids) > 0:
                token_id = token_ids[0]
                expected_price = float(prices[0]) if prices else 0
            elif winning_option == 'No' and len(token_ids) > 1:
                token_id = token_ids[1]
                expected_price = float(prices[1]) if len(prices) > 1 else 0
            else:
                return {
                    'success': False,
                    'error': 'Invalid winning option or token IDs'
                }
            
            # 计算交易数量
            if expected_price <= 0:
                return {
                    'success': False,
                    'error': 'Invalid expected price'
                }
            
            trade_size = str(Decimal(trade_amount) / Decimal(str(expected_price)))
            
            # 获取当前市场状况
            orderbook = self.client.get_orderbook(token_id)
            best_prices = self.client.get_best_bid_ask(token_id)
            
            # 估算市场冲击
            market_impact = self.client.estimate_market_impact(token_id, 'BUY', trade_size)
            
            # 检查滑点
            current_price = Decimal(best_prices['best_ask'] or '0')
            expected_price_decimal = Decimal(str(expected_price))
            
            if current_price > 0:
                slippage = abs(current_price - expected_price_decimal) / expected_price_decimal
                if slippage > max_slippage:
                    return {
                        'success': False,
                        'error': f'Slippage too high: {slippage:.2%} > {max_slippage:.2%}',
                        'current_price': str(current_price),
                        'expected_price': str(expected_price_decimal),
                        'slippage': f"{slippage:.2%}"
                    }
            
            # 准备交易结果
            trade_result = {
                'success': True,
                'market_id': market_data.get('id'),
                'market_question': market_data.get('question'),
                'token_id': token_id,
                'winning_option': winning_option,
                'confidence': confidence,
                'trade_amount': trade_amount,
                'trade_size': trade_size,
                'expected_price': str(expected_price_decimal),
                'current_price': str(current_price),
                'market_impact': market_impact,
                'orderbook_depth': {
                    'bids': len(orderbook.get('bids', [])),
                    'asks': len(orderbook.get('asks', []))
                },
                'dry_run': dry_run
            }
            
            if not dry_run:
                # 执行实际交易
                if market_impact['can_fill_completely']:
                    # 使用市价单
                    order_result = self.client.buy_market(token_id, trade_size)
                else:
                    # 使用限价单
                    limit_price = str(current_price * Decimal('1.01'))  # 稍高于当前价格
                    order_result = self.client.buy_limit(token_id, trade_size, limit_price)
                
                trade_result['order_result'] = order_result
                trade_result['order_id'] = order_result.get('orderID')
            
            return trade_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Trade execution failed: {str(e)}'
            }
    
    def monitor_order(self, order_id: str, timeout_seconds: int = 300) -> Dict:
        """监控订单状态"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                order = self.client.get_order(order_id)
                status = order.get('status', 'UNKNOWN')
                
                if status in ['FILLED', 'CANCELLED', 'REJECTED']:
                    return {
                        'success': True,
                        'final_status': status,
                        'order': order,
                        'monitoring_time': time.time() - start_time
                    }
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Order monitoring failed: {str(e)}'
                }
        
        return {
            'success': False,
            'error': 'Order monitoring timeout',
            'monitoring_time': timeout_seconds
        }
    
    def get_trading_summary(self) -> Dict:
        """获取交易摘要"""
        try:
            balance = self.client.get_balance()
            positions = self.client.get_positions()
            orders = self.client.get_orders()
            
            # 计算总价值
            total_value = Decimal(balance.get('usdcBalance', '0'))
            for position in positions:
                # 这里需要根据实际API响应格式调整
                position_value = Decimal(position.get('value', '0'))
                total_value += position_value
            
            return {
                'success': True,
                'usdc_balance': balance.get('usdcBalance', '0'),
                'total_positions': len(positions),
                'active_orders': len([o for o in orders if o.get('status') == 'OPEN']),
                'total_portfolio_value': str(total_value),
                'positions': positions,
                'recent_orders': orders[:10]  # 最近10个订单
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get trading summary: {str(e)}'
            }


def create_test_client() -> PolymarketCLOBClient:
    """创建测试客户端（需要填入实际的私钥）"""
    return PolymarketCLOBClient(
        host="https://clob-staging.polymarket.com",
        chain_id=80002,  # Polygon Amoy testnet
        private_key="your_private_key_here",
        use_testnet=True
    )


if __name__ == "__main__":
    # 示例用法
    print("Polymarket CLOB客户端示例")
    print("注意: 需要先配置私钥才能使用")
    
    # 创建客户端（测试网）
    # client = create_test_client()
    # trader = PolymarketTrader(client)
    
    # 示例：获取账户信息
    # try:
    #     balance = client.get_balance()
    #     print(f"账户余额: {balance}")
    # except Exception as e:
    #     print(f"获取余额失败: {e}")