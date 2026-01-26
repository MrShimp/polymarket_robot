#!/usr/bin/env python3
"""
订单管理工具 - 交互式界面
支持取消订单、Split订单、梯形订单等高级功能
"""

import sys
import os
import requests
import json
from typing import Dict, List, Optional, Tuple
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.order_manager import OrderManager
from trading.polymarket_clob_client import PolymarketCLOBClient


class OrderManagementTool:
    """订单管理工具"""
    
    def __init__(self):
        self.order_manager = OrderManager(use_testnet=False)
        self.clob_client = self.order_manager.clob_client
        self.gamma_api_base = "https://gamma-api.polymarket.com"
    
    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """获取市场信息"""
        try:
            url = f"{self.gamma_api_base}/markets/{market_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            market_data = response.json()
            
            if market_data:
                # 解析JSON字符串字段
                outcomes = market_data.get('outcomes', '[]')
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except json.JSONDecodeError:
                        outcomes = []
                
                clob_token_ids = market_data.get('clobTokenIds', '[]')
                if isinstance(clob_token_ids, str):
                    try:
                        clob_token_ids = json.loads(clob_token_ids)
                    except json.JSONDecodeError:
                        clob_token_ids = []
                
                return {
                    'id': market_data.get('id'),
                    'question': market_data.get('question'),
                    'outcomes': outcomes,
                    'clobTokenIds': clob_token_ids,
                    'orderMinSize': market_data.get('orderMinSize', 1),
                    'orderPriceMinTickSize': market_data.get('orderPriceMinTickSize', 0.01)
                }
            
            return None
            
        except Exception as e:
            print(f"❌ 获取市场信息失败: {e}")
            return None
    
    def display_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("🎯 Polymarket 订单管理工具")
        print("="*60)
        print("1. 查看未成交订单")
        print("2. 取消订单")
        print("3. Split订单 (分割大订单)")
        print("4. 梯形订单 (Ladder Orders)")
        print("5. 查看订单簿深度")
        print("6. 批量取消订单")
        print("0. 退出")
        print("-"*60)
    
    def view_open_orders(self):
        """查看未成交订单"""
        print("\n📋 查看未成交订单")
        print("-"*40)
        
        # 选择查看范围
        print("1. 查看所有未成交订单")
        print("2. 查看特定Token的订单")
        
        choice = input("请选择 (1/2): ").strip()
        
        if choice == "1":
            orders = self.order_manager.get_open_orders()
            self.order_manager.display_open_orders(orders)
        elif choice == "2":
            token_id = input("请输入Token ID: ").strip()
            if token_id:
                orders = self.order_manager.get_open_orders(token_id)
                self.order_manager.display_open_orders(orders)
            else:
                print("❌ Token ID不能为空")
        else:
            print("❌ 无效选择")
    
    def cancel_orders_menu(self):
        """取消订单菜单"""
        print("\n🗑️ 取消订单")
        print("-"*40)
        print("1. 取消单个订单")
        print("2. 取消特定Token的所有订单")
        print("3. 取消所有订单")
        
        choice = input("请选择 (1/2/3): ").strip()
        
        if choice == "1":
            self.cancel_single_order()
        elif choice == "2":
            self.cancel_orders_by_token()
        elif choice == "3":
            self.cancel_all_orders()
        else:
            print("❌ 无效选择")
    
    def cancel_single_order(self):
        """取消单个订单"""
        # 先显示当前订单
        orders = self.order_manager.get_open_orders()
        if not orders:
            print("📋 没有未成交的订单")
            return
        
        self.order_manager.display_open_orders(orders)
        
        order_id = input("\n请输入要取消的订单ID: ").strip()
        if not order_id:
            print("❌ 订单ID不能为空")
            return
        
        # 确认取消
        confirm = input(f"❓ 确认取消订单 {order_id}? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            result = self.order_manager.cancel_order(order_id)
            if result['success']:
                print(f"✅ 订单取消成功")
            else:
                print(f"❌ 订单取消失败: {result.get('error')}")
        else:
            print("❌ 取消操作已取消")
    
    def cancel_orders_by_token(self):
        """取消特定Token的所有订单"""
        token_id = input("请输入Token ID: ").strip()
        if not token_id:
            print("❌ Token ID不能为空")
            return
        
        # 先显示该Token的订单
        orders = self.order_manager.get_open_orders(token_id)
        if not orders:
            print(f"📋 Token {token_id} 没有未成交的订单")
            return
        
        print(f"\n📋 Token {token_id} 的未成交订单:")
        self.order_manager.display_open_orders(orders)
        
        # 确认取消
        confirm = input(f"❓ 确认取消Token {token_id} 的所有订单? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            result = self.order_manager.cancel_orders_by_token(token_id)
            if result['success']:
                print(f"✅ Token {token_id} 的所有订单取消成功")
            else:
                print(f"❌ 取消失败: {result.get('error')}")
        else:
            print("❌ 取消操作已取消")
    
    def cancel_all_orders(self):
        """取消所有订单"""
        # 先显示所有订单
        orders = self.order_manager.get_open_orders()
        if not orders:
            print("📋 没有未成交的订单")
            return
        
        print(f"\n📋 所有未成交订单:")
        self.order_manager.display_open_orders(orders)
        
        # 确认取消
        print("⚠️ 警告: 这将取消您的所有未成交订单!")
        confirm = input("❓ 确认取消所有订单? (输入 'YES' 确认): ").strip()
        if confirm == 'YES':
            result = self.order_manager.cancel_all_orders()
            if result['success']:
                print(f"✅ 所有订单取消成功")
            else:
                print(f"❌ 取消失败: {result.get('error')}")
        else:
            print("❌ 取消操作已取消")
    
    def split_order_menu(self):
        """Split订单菜单"""
        print("\n🔄 Split订单 (分割大订单)")
        print("-"*40)
        
        try:
            # 输入市场ID
            market_id = input("请输入市场ID: ").strip()
            if not market_id:
                print("❌ 市场ID不能为空")
                return
            
            # 获取市场信息
            market_info = self.get_market_info(market_id)
            if not market_info:
                print(f"❌ 未找到市场: {market_id}")
                return
            
            print(f"\n📊 市场: {market_info['question']}")
            
            # 选择结果
            outcomes = market_info.get('outcomes', [])
            token_ids = market_info.get('clobTokenIds', [])
            
            if not outcomes or not token_ids:
                print("❌ 市场数据不完整")
                return
            
            print(f"\n🎯 结果选项:")
            for i, outcome in enumerate(outcomes):
                print(f"   {i+1}. {outcome}")
            
            try:
                choice = int(input(f"请选择结果 (1-{len(outcomes)}): ").strip()) - 1
                if choice < 0 or choice >= len(outcomes):
                    print("❌ 无效选择")
                    return
            except ValueError:
                print("❌ 请输入有效数字")
                return
            
            selected_outcome = outcomes[choice]
            token_id = token_ids[choice]
            
            print(f"✅ 已选择: {selected_outcome}")
            print(f"   Token ID: {token_id}")
            
            # 获取订单簿信息
            orderbook_info = self.order_manager.get_orderbook_levels(token_id)
            if not orderbook_info.get('error'):
                print(f"\n📖 当前订单簿:")
                bids = orderbook_info.get('bids', [])
                asks = orderbook_info.get('asks', [])
                
                if bids:
                    print(f"   最佳买价: ${bids[0]['price']:.3f}")
                if asks:
                    print(f"   最佳卖价: ${asks[0]['price']:.3f}")
            
            # 输入Split参数
            print(f"\n📝 Split订单参数:")
            
            try:
                total_amount = float(input("总金额 (USDC): ").strip())
                total_size = float(input("总数量 (shares): ").strip())
                num_splits = int(input("分割数量: ").strip())
                min_price = float(input("最低价格: ").strip())
                max_price = float(input("最高价格: ").strip())
                
                # 选择订单方向
                print("\n订单方向:")
                print("1. BUY (买入)")
                print("2. SELL (卖出)")
                side_choice = input("请选择 (1/2): ").strip()
                side = "BUY" if side_choice == "1" else "SELL"
                
            except ValueError:
                print("❌ 输入格式错误")
                return
            
            # 验证参数
            if total_amount <= 0 or total_size <= 0 or num_splits <= 0:
                print("❌ 参数必须大于0")
                return
            
            if min_price >= max_price:
                print("❌ 最低价格必须小于最高价格")
                return
            
            if min_price <= 0 or max_price >= 1:
                print("❌ 价格必须在0到1之间")
                return
            
            # 显示Split计划
            print(f"\n📋 Split订单计划:")
            print(f"   市场: {market_info['question']}")
            print(f"   选择: {selected_outcome}")
            print(f"   总金额: ${total_amount:.2f}")
            print(f"   总数量: {total_size:.2f}")
            print(f"   分割数: {num_splits}")
            print(f"   价格范围: ${min_price:.3f} - ${max_price:.3f}")
            print(f"   方向: {side}")
            
            # 确认执行
            confirm = input(f"\n❓ 确认执行Split订单? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ Split订单已取消")
                return
            
            # 执行Split订单
            results = self.order_manager.split_order(
                token_id=token_id,
                total_amount=total_amount,
                total_size=total_size,
                num_splits=num_splits,
                price_range=(min_price, max_price),
                side=side
            )
            
            # 保存记录
            metadata = {
                'market_id': market_id,
                'market_question': market_info['question'],
                'selected_outcome': selected_outcome,
                'token_id': token_id,
                'total_amount': total_amount,
                'total_size': total_size,
                'num_splits': num_splits,
                'price_range': [min_price, max_price],
                'side': side
            }
            
            self.order_manager.save_order_batch_record('split_order', results, metadata)
            
        except KeyboardInterrupt:
            print(f"\n❌ 用户取消操作")
        except Exception as e:
            print(f"❌ Split订单失败: {e}")
    
    def ladder_order_menu(self):
        """梯形订单菜单"""
        print("\n🪜 梯形订单 (Ladder Orders)")
        print("-"*40)
        
        try:
            # 输入市场ID和选择结果 (与split_order_menu类似的逻辑)
            market_id = input("请输入市场ID: ").strip()
            if not market_id:
                print("❌ 市场ID不能为空")
                return
            
            market_info = self.get_market_info(market_id)
            if not market_info:
                print(f"❌ 未找到市场: {market_id}")
                return
            
            print(f"\n📊 市场: {market_info['question']}")
            
            outcomes = market_info.get('outcomes', [])
            token_ids = market_info.get('clobTokenIds', [])
            
            if not outcomes or not token_ids:
                print("❌ 市场数据不完整")
                return
            
            print(f"\n🎯 结果选项:")
            for i, outcome in enumerate(outcomes):
                print(f"   {i+1}. {outcome}")
            
            try:
                choice = int(input(f"请选择结果 (1-{len(outcomes)}): ").strip()) - 1
                if choice < 0 or choice >= len(outcomes):
                    print("❌ 无效选择")
                    return
            except ValueError:
                print("❌ 请输入有效数字")
                return
            
            selected_outcome = outcomes[choice]
            token_id = token_ids[choice]
            
            print(f"✅ 已选择: {selected_outcome}")
            
            # 输入梯形订单参数
            print(f"\n📝 梯形订单参数:")
            
            try:
                base_price = float(input("基准价格: ").strip())
                total_size = float(input("总数量 (shares): ").strip())
                num_orders = int(input("订单数量: ").strip())
                price_increment = float(input("价格增量: ").strip())
                
                print("\n订单方向:")
                print("1. BUY (买入) - 价格递减")
                print("2. SELL (卖出) - 价格递增")
                side_choice = input("请选择 (1/2): ").strip()
                side = "BUY" if side_choice == "1" else "SELL"
                
            except ValueError:
                print("❌ 输入格式错误")
                return
            
            # 验证参数
            if base_price <= 0 or base_price >= 1:
                print("❌ 基准价格必须在0到1之间")
                return
            
            if total_size <= 0 or num_orders <= 0 or price_increment <= 0:
                print("❌ 参数必须大于0")
                return
            
            # 显示梯形订单计划
            print(f"\n📋 梯形订单计划:")
            print(f"   基准价格: ${base_price:.3f}")
            print(f"   总数量: {total_size:.2f}")
            print(f"   订单数量: {num_orders}")
            print(f"   价格增量: ${price_increment:.3f}")
            print(f"   方向: {side}")
            
            # 预览价格分布
            print(f"\n📊 价格分布预览:")
            for i in range(min(5, num_orders)):  # 最多显示5个
                if side == "BUY":
                    price = base_price - (price_increment * i)
                else:
                    price = base_price + (price_increment * i)
                
                size = total_size / num_orders
                print(f"   订单 {i+1}: ${price:.3f} x {size:.2f}")
            
            if num_orders > 5:
                print(f"   ... (还有 {num_orders - 5} 个订单)")
            
            # 确认执行
            confirm = input(f"\n❓ 确认执行梯形订单? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ 梯形订单已取消")
                return
            
            # 执行梯形订单
            results = self.order_manager.ladder_orders(
                token_id=token_id,
                base_price=base_price,
                total_size=total_size,
                num_orders=num_orders,
                price_increment=price_increment,
                side=side
            )
            
            # 保存记录
            metadata = {
                'market_id': market_id,
                'market_question': market_info['question'],
                'selected_outcome': selected_outcome,
                'token_id': token_id,
                'base_price': base_price,
                'total_size': total_size,
                'num_orders': num_orders,
                'price_increment': price_increment,
                'side': side
            }
            
            self.order_manager.save_order_batch_record('ladder_order', results, metadata)
            
        except KeyboardInterrupt:
            print(f"\n❌ 用户取消操作")
        except Exception as e:
            print(f"❌ 梯形订单失败: {e}")
    
    def view_orderbook_depth(self):
        """查看订单簿深度"""
        print("\n📖 查看订单簿深度")
        print("-"*40)
        
        token_id = input("请输入Token ID: ").strip()
        if not token_id:
            print("❌ Token ID不能为空")
            return
        
        try:
            depth = int(input("深度层数 (默认5): ").strip() or "5")
        except ValueError:
            depth = 5
        
        print(f"\n🔍 获取Token {token_id} 的订单簿深度...")
        
        orderbook_info = self.order_manager.get_orderbook_levels(token_id, depth)
        
        if orderbook_info.get('error'):
            print(f"❌ 获取订单簿失败: {orderbook_info['error']}")
            return
        
        bids = orderbook_info.get('bids', [])
        asks = orderbook_info.get('asks', [])
        
        print(f"\n📊 订单簿深度 (前{depth}层):")
        print("-" * 50)
        print(f"{'卖盘 (Asks)':^25} | {'买盘 (Bids)':^25}")
        print("-" * 50)
        
        max_len = max(len(asks), len(bids))
        
        for i in range(max_len):
            ask_str = ""
            bid_str = ""
            
            if i < len(asks):
                ask = asks[i]
                ask_str = f"${ask['price']:.3f} x {ask['size']:.1f}"
            
            if i < len(bids):
                bid = bids[i]
                bid_str = f"${bid['price']:.3f} x {bid['size']:.1f}"
            
            print(f"{ask_str:>25} | {bid_str:<25}")
        
        # 显示价差
        if bids and asks:
            spread = asks[0]['price'] - bids[0]['price']
            midpoint = (asks[0]['price'] + bids[0]['price']) / 2
            print("-" * 50)
            print(f"价差: ${spread:.4f} | 中间价: ${midpoint:.3f}")
    
    def run(self):
        """运行主程序"""
        print("🎯 Polymarket 订单管理工具")
        
        # 检查客户端配置
        try:
            address = self.clob_client.get_address()
            if not address:
                print("❌ 错误: 未配置私钥或API密钥")
                print("请在 config/sys_config.json 中配置认证信息")
                return False
            
            print(f"📊 当前配置:")
            print(f"   地址: {address}")
            print(f"   网络: {'测试网' if self.order_manager.use_testnet else '主网'}")
            
        except Exception as e:
            print(f"❌ 客户端初始化失败: {e}")
            return False
        
        while True:
            try:
                self.display_menu()
                choice = input("请选择操作 (0-6): ").strip()
                
                if choice == "0":
                    print("👋 再见!")
                    break
                elif choice == "1":
                    self.view_open_orders()
                elif choice == "2":
                    self.cancel_orders_menu()
                elif choice == "3":
                    self.split_order_menu()
                elif choice == "4":
                    self.ladder_order_menu()
                elif choice == "5":
                    self.view_orderbook_depth()
                elif choice == "6":
                    self.cancel_orders_menu()  # 批量取消订单使用相同菜单
                else:
                    print("❌ 无效选择，请重新输入")
                
                # 等待用户按键继续
                if choice != "0":
                    input("\n按回车键继续...")
                
            except KeyboardInterrupt:
                print(f"\n\n👋 用户退出")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")
                input("按回车键继续...")
        
        return True


def main():
    """主函数"""
    tool = OrderManagementTool()
    tool.run()


if __name__ == "__main__":
    main()