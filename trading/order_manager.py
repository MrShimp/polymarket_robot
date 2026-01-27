#!/usr/bin/env python3
"""
订单管理器 - 处理取消订单和split挂单功能
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from py_clob_client.clob_types import OrderArgs
from trading.polymarket_clob_client import PolymarketCLOBClient


class OrderManager:
    """订单管理器 - 处理高级订单操作"""
    
    def __init__(self):
        self.clob_wrapper = PolymarketCLOBClient()
        self.clob_client = self.clob_wrapper.get_client()
    
    def get_open_orders(self, token_id: Optional[str] = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            if token_id:
                # 获取特定token的订单
                orders = self.clob_client.get_orders(token_id=token_id)
            else:
                # 获取所有订单
                orders = self.clob_client.get_orders()
            
            # 过滤出未成交的订单
            open_orders = []
            if orders:
                for order in orders:
                    # 检查订单状态
                    status = order.get('status', '').upper()
                    if status in ['OPEN', 'PARTIAL']:
                        open_orders.append(order)
            
            return open_orders
            
        except Exception as e:
            print(f"❌ 获取订单失败: {e}")
            return []
    
    def display_open_orders(self, orders: List[Dict]):
        """显示未成交订单"""
        if not orders:
            print("📋 没有未成交的订单")
            return
        
        print(f"📋 未成交订单 ({len(orders)}个):")
        print("-" * 80)
        
        for i, order in enumerate(orders, 1):
            order_id = order.get('id', 'N/A')
            token_id = order.get('asset_id', order.get('token_id', 'N/A'))
            side = order.get('side', 'N/A')
            price = order.get('price', 'N/A')
            size = order.get('size', 'N/A')
            filled_size = order.get('size_matched', order.get('filled_size', 0))
            status = order.get('status', 'N/A')
            created_at = order.get('created_at', 'N/A')
            
            try:
                remaining_size = float(size) - float(filled_size)
            except (ValueError, TypeError):
                remaining_size = 'N/A'
            
            print(f"{i:2d}. 订单ID: {order_id}")
            print(f"    Token: {token_id}")
            print(f"    方向: {side} | 价格: ${price} | 数量: {size}")
            print(f"    已成交: {filled_size} | 剩余: {remaining_size}")
            print(f"    状态: {status} | 创建时间: {created_at}")
            print()
    
    def cancel_order(self, order_id: str) -> Dict:
        """取消单个订单"""
        try:
            print(f"🗑️ 正在取消订单: {order_id}")
            
            # 直接使用order_id字符串调用cancel方法
            result = self.clob_client.cancel(order_id)
            
            if result:
                print(f"✅ 订单取消成功: {order_id}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'result': result
                }
            else:
                print(f"❌ 订单取消失败: {order_id}")
                return {
                    'success': False,
                    'order_id': order_id,
                    'error': 'Cancel operation returned empty result'
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 取消订单失败: {error_msg}")
            return {
                'success': False,
                'order_id': order_id,
                'error': error_msg
            }
    
    def cancel_orders_by_token(self, token_id: str) -> Dict:
        """取消特定token的所有订单"""
        try:
            print(f"🗑️ 正在取消Token {token_id} 的所有订单")
            
            # 使用asset_id参数调用cancel_all方法
            result = self.clob_client.cancel_all(asset_id=token_id)
            
            if result:
                print(f"✅ Token {token_id} 的所有订单取消成功")
                return {
                    'success': True,
                    'token_id': token_id,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'token_id': token_id,
                    'error': 'Cancel all operation returned empty result'
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 取消Token订单失败: {error_msg}")
            return {
                'success': False,
                'token_id': token_id,
                'error': error_msg
            }
    
    def cancel_all_orders(self) -> Dict:
        """取消所有订单"""
        try:
            print(f"🗑️ 正在取消所有订单")
            
            # 不指定asset_id来取消所有订单
            result = self.clob_client.cancel_all()
            
            if result:
                print(f"✅ 所有订单取消成功")
                return {
                    'success': True,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'error': 'Cancel all operation returned empty result'
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 取消所有订单失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_orderbook_levels(self, token_id: str, depth: int = 5) -> Dict:
        """获取订单簿深度数据"""
        try:
            orderbook = self.clob_client.get_order_book(token_id)
            
            if not orderbook:
                return {'error': 'Empty orderbook'}
            
            # 获取买卖盘数据
            bids = orderbook.bids[:depth] if orderbook.bids else []
            asks = orderbook.asks[:depth] if orderbook.asks else []
            
            return {
                'bids': [{'price': float(bid['price']), 'size': float(bid['size'])} for bid in bids],
                'asks': [{'price': float(ask['price']), 'size': float(ask['size'])} for ask in asks],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def split_order(self, token_id: str, total_amount: float, total_size: float, 
                   num_splits: int, price_range: Tuple[float, float], 
                   side: str = "BUY") -> List[Dict]:
        """
        Split订单 - 将大订单分割成多个小订单
        
        Args:
            token_id: Token ID
            total_amount: 总金额 (USDC)
            total_size: 总数量 (shares)
            num_splits: 分割数量
            price_range: 价格范围 (min_price, max_price)
            side: 订单方向 ("BUY" 或 "SELL")
        """
        results = []
        min_price, max_price = price_range
        
        print(f"🔄 开始Split订单:")
        print(f"   Token: {token_id}")
        print(f"   总金额: ${total_amount:.2f}")
        print(f"   总数量: {total_size:.2f}")
        print(f"   分割数: {num_splits}")
        print(f"   价格范围: ${min_price:.3f} - ${max_price:.3f}")
        print(f"   方向: {side}")
        print()
        
        try:
            # 计算每个订单的参数
            size_per_order = total_size / num_splits
            price_step = (max_price - min_price) / (num_splits - 1) if num_splits > 1 else 0
            
            for i in range(num_splits):
                # 计算当前订单的价格
                if num_splits == 1:
                    current_price = (min_price + max_price) / 2
                else:
                    current_price = min_price + (price_step * i)
                
                # 四舍五入到合适的精度
                current_price = round(current_price, 3)
                current_size = round(size_per_order, 2)
                
                print(f"📝 创建订单 {i+1}/{num_splits}: 价格=${current_price:.3f}, 数量={current_size:.2f}")
                
                try:
                    # 创建订单参数
                    order_args = OrderArgs(
                        token_id=token_id,
                        price=current_price,
                        size=current_size,
                        side=side
                    )
                    
                    # 创建并提交订单
                    signed_order = self.clob_client.create_order(order_args)
                    result = self.clob_client.post_order(signed_order)
                    
                    order_result = {
                        'success': True,
                        'order_index': i + 1,
                        'price': current_price,
                        'size': current_size,
                        'order_id': result.get('orderId'),
                        'result': result
                    }
                    
                    print(f"   ✅ 订单 {i+1} 创建成功: {result.get('orderId')}")
                    
                except Exception as e:
                    order_result = {
                        'success': False,
                        'order_index': i + 1,
                        'price': current_price,
                        'size': current_size,
                        'error': str(e)
                    }
                    print(f"   ❌ 订单 {i+1} 创建失败: {e}")
                
                results.append(order_result)
                
                # 添加延迟避免API限制
                if i < num_splits - 1:
                    time.sleep(0.5)
            
            # 统计结果
            successful_orders = sum(1 for r in results if r['success'])
            print(f"\n📊 Split订单完成:")
            print(f"   成功: {successful_orders}/{num_splits}")
            print(f"   失败: {num_splits - successful_orders}/{num_splits}")
            
            return results
            
        except Exception as e:
            print(f"❌ Split订单失败: {e}")
            return [{'success': False, 'error': str(e)}]
    
    def ladder_orders(self, token_id: str, base_price: float, total_size: float,
                     num_orders: int, price_increment: float, side: str = "BUY") -> List[Dict]:
        """
        梯形订单 - 在基准价格周围创建梯形分布的订单
        
        Args:
            token_id: Token ID
            base_price: 基准价格
            total_size: 总数量
            num_orders: 订单数量
            price_increment: 价格增量
            side: 订单方向
        """
        results = []
        size_per_order = total_size / num_orders
        
        print(f"🪜 创建梯形订单:")
        print(f"   基准价格: ${base_price:.3f}")
        print(f"   价格增量: ${price_increment:.3f}")
        print(f"   订单数量: {num_orders}")
        print()
        
        try:
            for i in range(num_orders):
                # 计算当前订单价格
                if side == "BUY":
                    # 买单：价格递减
                    current_price = base_price - (price_increment * i)
                else:
                    # 卖单：价格递增
                    current_price = base_price + (price_increment * i)
                
                current_price = round(current_price, 3)
                current_size = round(size_per_order, 2)
                
                # 验证价格范围
                if current_price <= 0 or current_price >= 1:
                    print(f"   ⚠️ 跳过无效价格: ${current_price:.3f}")
                    continue
                
                print(f"📝 创建梯形订单 {i+1}: 价格=${current_price:.3f}, 数量={current_size:.2f}")
                
                try:
                    order_args = OrderArgs(
                        token_id=token_id,
                        price=current_price,
                        size=current_size,
                        side=side
                    )
                    
                    signed_order = self.clob_client.create_order(order_args)
                    result = self.clob_client.post_order(signed_order)
                    
                    order_result = {
                        'success': True,
                        'order_index': i + 1,
                        'price': current_price,
                        'size': current_size,
                        'order_id': result.get('orderId'),
                        'result': result
                    }
                    
                    print(f"   ✅ 梯形订单 {i+1} 创建成功")
                    
                except Exception as e:
                    order_result = {
                        'success': False,
                        'order_index': i + 1,
                        'price': current_price,
                        'size': current_size,
                        'error': str(e)
                    }
                    print(f"   ❌ 梯形订单 {i+1} 创建失败: {e}")
                
                results.append(order_result)
                time.sleep(0.5)
            
            successful_orders = sum(1 for r in results if r['success'])
            print(f"\n📊 梯形订单完成: {successful_orders}/{len(results)} 成功")
            
            return results
            
        except Exception as e:
            print(f"❌ 梯形订单失败: {e}")
            return [{'success': False, 'error': str(e)}]
    
    def save_order_batch_record(self, operation_type: str, results: List[Dict], 
                               metadata: Dict = None):
        """保存批量订单记录"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'total_orders': len(results),
                'successful_orders': sum(1 for r in results if r.get('success')),
                'failed_orders': sum(1 for r in results if not r.get('success')),
                'metadata': metadata or {},
                'results': results
            }
            
            # 保存到文件
            orders_dir = "data/orders"
            import os
            os.makedirs(orders_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{orders_dir}/{operation_type}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            
            print(f"📁 批量订单记录已保存: {filename}")
            
        except Exception as e:
            print(f"⚠️ 保存批量订单记录失败: {e}")


def main():
    """测试订单管理器功能"""
    print("🔧 订单管理器测试")
    
    manager = OrderManager()
    
    # 测试获取订单
    print("\n1. 获取未成交订单:")
    orders = manager.get_open_orders()
    manager.display_open_orders(orders)
    
    print("\n订单管理器功能:")
    print("- get_open_orders(): 获取未成交订单")
    print("- cancel_order(order_id): 取消单个订单")
    print("- cancel_orders_by_token(token_id): 取消特定token的所有订单")
    print("- cancel_all_orders(): 取消所有订单")
    print("- split_order(): Split大订单为多个小订单")
    print("- ladder_orders(): 创建梯形分布订单")


if __name__ == "__main__":
    main()