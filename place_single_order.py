#!/usr/bin/env python3
"""
单一市场下单工具
支持交互式输入市场ID、选择结果、指定金额进行下单
基于Polymarket API实时获取市场数据
"""

import sys
import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType, OrderArgs
from trading.polymarket_clob_client import PolymarketCLOBClient
from trading.order_manager import OrderManager

class SingleOrderPlacer:
    """单一市场下单器"""
    
    def __init__(self):
        self.clob_wrapper = PolymarketCLOBClient()
        self.clob_client = self.clob_wrapper.get_client()  # 获取原生ClobClient
        self.order_manager = OrderManager()  # 添加订单管理器
        self.gamma_api_base = "https://gamma-api.polymarket.com"
    
    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """通过Gamma API获取市场信息"""
        try:
            url = f"{self.gamma_api_base}/markets/{market_id}"
            print(f"📡 正在获取市场信息: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            market_data = response.json()
            
            # 解析市场数据
            if market_data:
                # 解析JSON字符串字段
                outcomes = market_data.get('outcomes', '[]')
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except json.JSONDecodeError:
                        outcomes = []
                
                outcome_prices = market_data.get('outcomePrices', '[]')
                if isinstance(outcome_prices, str):
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except json.JSONDecodeError:
                        outcome_prices = []
                
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
                    'outcomePrices': outcome_prices,
                    'clobTokenIds': clob_token_ids,
                    'conditionId': market_data.get('conditionId'),
                    'endDate': market_data.get('endDate'),
                    'volume': market_data.get('volume'),
                    'liquidity': market_data.get('liquidity'),
                    'active': market_data.get('active', True),
                    'closed': market_data.get('closed', False),
                    'acceptingOrders': market_data.get('acceptingOrders', True),
                    'orderMinSize': market_data.get('orderMinSize', 1),
                    'orderPriceMinTickSize': market_data.get('orderPriceMinTickSize', 0.01)
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取市场信息失败: {e}")
            return None
    
    def display_market_info(self, market_info: Dict):
        """显示市场信息"""
        print(f"\n📊 市场信息:")
        print(f"   ID: {market_info.get('id')}")
        print(f"   问题: {market_info.get('question')}")
        print(f"   结束时间: {market_info.get('endDate')}")
        
        # 安全处理数值字段
        volume = market_info.get('volume')
        if volume is not None:
            print(f"   交易量: ${float(volume):,.0f}")
        
        liquidity = market_info.get('liquidity')
        if liquidity is not None:
            print(f"   流动性: ${float(liquidity):,.0f}")
        
        print(f"   状态: {'活跃' if market_info.get('active') else '非活跃'}")
        print(f"   接受订单: {'是' if market_info.get('acceptingOrders') else '否'}")
        print(f"   最小订单: ${market_info.get('orderMinSize', 1)}")
        print(f"   价格精度: {market_info.get('orderPriceMinTickSize', 0.01)}")
        print(f"   clobTokenIds: {market_info.get('clobTokenIds')}")
        
        # 显示结果选项和价格
        outcomes = market_info.get('outcomes', [])
        prices = market_info.get('outcomePrices', [])
        
        print(f"\n🎯 结果选项和当前价格:")
        for i, (outcome, price) in enumerate(zip(outcomes, prices)):
            try:
                price_float = float(price)
                probability = price_float * 100
                print(f"   {i+1}. {outcome}: ${price_float:.3f} ({probability:.1f}%)")
            except (ValueError, TypeError):
                print(f"   {i+1}. {outcome}: 价格无效")
    
    def validate_token_id(self, token_id: str) -> bool:
        """验证Token ID格式"""
        if not token_id:
            return False
        
        # Token ID通常是大整数字符串 (可能很长)
        try:
            # 检查是否为纯数字字符串
            int(token_id)
            return len(token_id) > 10  # 至少10位数字
        except ValueError:
            pass
        
        # 或者是64位十六进制字符串
        if len(token_id) == 64:
            try:
                int(token_id, 16)
                return True
            except ValueError:
                return False
        
        # 或者是带0x前缀的66位字符串
        if len(token_id) == 66 and token_id.startswith('0x'):
            try:
                int(token_id, 16)
                return True
            except ValueError:
                return False
        
        return False
    
    def get_orderbook_info(self, token_id: str) -> Dict:
        """获取订单簿信息"""
        try:
            print(f"🔍 获取Token {token_id} 的订单簿...")
            orderbook = self.clob_client.get_order_book(token_id)
            
            # 检查订单簿是否为空
            if not orderbook:
                return {
                    'bids': 0,
                    'asks': 0,
                    'best_bid': None,
                    'best_ask': None,
                    'spread': None,
                    'error': 'Empty orderbook response'
                }
            
            # 获取最佳价格和价差
            try:
                midpoint = self.clob_client.get_midpoint(token_id)
                spread = self.clob_client.get_spread(token_id)
                
                # 从订单簿中获取最佳买卖价
                bids = orderbook.bids
                asks = orderbook.asks
                
                best_bid = float(bids[0]['price']) if bids else None
                best_ask = float(asks[0]['price']) if asks else None
                
            except Exception:
                best_bid = None
                best_ask = None
                spread = None
            
            return {
                'bids': len(bids),
                'asks': len(asks),
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': spread,
                'midpoint': midpoint
            }
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是404错误（订单簿不存在）
            if "404" in error_msg and "No orderbook exists" in error_msg:
                return {
                    'bids': 0,
                    'asks': 0,
                    'best_bid': None,
                    'best_ask': None,
                    'spread': None,
                    'error': 'No orderbook exists for this token'
                }
            
            return {
                'bids': 0,
                'asks': 0,
                'best_bid': None,
                'best_ask': None,
                'spread': None,
                'error': error_msg
            }
    
    def get_user_balance(self) -> Optional[float]:
        """获取用户USDC余额"""
        try:
            # 检查客户端是否可用
            if not self.clob_client:
                print(f"⚠️ CLOB客户端未初始化")
                return None
            
            # 获取USDC余额
            balance_info = self.clob_client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )
            if balance_info:
                # 尝试不同的余额字段
                balance = balance_info.get('balance') or balance_info.get('usdcBalance')
                if balance is not None:
                    return float(balance)/1000000
            
            print(f"⚠️ 余额信息为空或格式不正确: {balance_info}")
            return None
            
        except Exception as e:
            print(f"⚠️ 获取余额失败: {e}")
            # 如果是认证相关错误，提供更具体的提示
            if "signature_type" in str(e) or "NoneType" in str(e):
                print(f"   这通常表示需要配置有效的私钥或API密钥")
            return None
    
    def validate_inputs(self, market_info: Dict, outcome_index: int, amount: float):
        """验证输入参数"""
        errors = []
        
        # 验证市场状态
        if not market_info.get('active'):
            errors.append("市场未激活")
        
        if market_info.get('closed'):
            errors.append("市场已关闭")
        
        if not market_info.get('acceptingOrders'):
            errors.append("市场不接受订单")
        
        # 验证结果选择
        outcomes = market_info.get('outcomes', [])
        if outcome_index < 0 or outcome_index >= len(outcomes):
            errors.append(f"无效的结果选择，请选择 1-{len(outcomes)}")
        
        # 验证Token ID
        token_ids = market_info.get('clobTokenIds', [])
        if outcome_index < len(token_ids):
            token_id = token_ids[outcome_index]
            if not self.validate_token_id(token_id):
                errors.append(f"Token ID格式无效: {token_id}")
        else:
            errors.append("Token ID数据不完整")
        
        # 验证金额
        min_order_size = float(market_info.get('orderMinSize', 1))
        if amount < min_order_size:
            errors.append(f"金额低于最小订单要求: ${min_order_size}")
        
        if amount > 1000:  # 设置一个合理的上限
            errors.append("金额过大，请使用小于$1000的金额")
        
        # 检查用户余额
        balance = self.get_user_balance()
        if balance is not None:
            if amount > balance:
                errors.append(f"余额不足: 需要${amount:.2f}, 可用${balance:.2f}")
        else:
            errors.append("无法获取账户余额，请检查API配置")
        
        return errors
    
    def interactive_order(self):
        """交互式下单"""
        print("🎯 Polymarket 实时下单工具")
        print("=" * 60)
        
        # 检查客户端配置
        address = self.clob_client.get_address()
        signer = self.clob_client.signer.address()
        if not address:
            print("❌ 错误: 未配置私钥或API密钥")
            print("请在 config/sys_config.json 中配置认证信息")
            return False
        
        print(f"📊 当前配置:")
        print(f"   网络: {'测试网' if self.clob_wrapper.use_testnet else '主网'}")
        print(f"   地址: {address}")
        print(f"   签名地址: {signer}")
        # 显示余额
        balance = self.get_user_balance()
        if balance is not None:
            print(f"   USDC余额: ${balance:.2f}")
        else:
            print(f"   USDC余额: 无法获取")
        print()
        
        try:
            # 输入市场ID
            market_id = input("📝 请输入市场ID: ").strip()
            if not market_id:
                print("❌ 市场ID不能为空")
                return False
            
            # 获取市场信息
            print(f"\n� 查询市场:信息...")
            market_info = self.get_market_info(market_id)
            
            if not market_info:
                print(f"❌ 未找到市场ID: {market_id}")
                return False
            
            # 显示市场信息
            self.display_market_info(market_info)
            
            # 选择结果
            outcomes = market_info.get('outcomes', [])
            if len(outcomes) == 0:
                print("❌ 市场没有可用的结果选项")
                return False
            
            try:
                choice_input = input(f"\n🎲 请选择结果 (1-{len(outcomes)}): ").strip()
                outcome_index = int(choice_input) - 1
            except ValueError:
                print("❌ 请输入有效的数字")
                return False
            
            if outcome_index < 0 or outcome_index >= len(outcomes):
                print(f"❌ 无效选择，请选择 1-{len(outcomes)}")
                return False
            
            selected_outcome = outcomes[outcome_index]
            prices = market_info.get('outcomePrices', [])
            
            if outcome_index >= len(prices):
                print("❌ 价格数据不完整")
                return False
            
            try:
                current_price = float(prices[outcome_index])
            except (ValueError, TypeError):
                print("❌ 价格数据无效")
                return False
            
            token_ids = market_info.get('clobTokenIds', [])
            if outcome_index >= len(token_ids):
                print("❌ Token ID数据不完整")
                return False
            
            token_id = token_ids[outcome_index]
            
            print(f"\n✅ 已选择: {selected_outcome}")
            print(f"   当前价格: ${current_price:.3f}")
            print(f"   Token ID: {token_id}")
            
            # 获取订单簿信息
            print(f"\n📖 获取订单簿信息...")
            
            # 先测试API连接
            try:
                # 使用包装器的连接测试方法
                if self.clob_wrapper.test_connection():
                    orderbook_info = self.get_orderbook_info(token_id)
                else:
                    raise Exception("API连接测试失败")
            except Exception as e:
                print(f"⚠️ API连接测试失败: {e}")
                orderbook_info = {'error': 'API connection failed'}
            
            if orderbook_info.get('error'):
                print(f"   ⚠️ 订单簿获取失败: {orderbook_info['error']}")
                print(f"   这可能是因为:")
                print(f"   - Token ID无效或不存在")
                print(f"   - 市场暂时不可用")
                print(f"   - API认证问题")
                print(f"   - CLOB API响应格式问题")
                
                # 询问是否继续
                continue_choice = input(f"\n❓ 订单簿不可用，是否继续下单? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes']:
                    print("❌ 用户取消下单")
                    return False
            else:
                print(f"   买单数量: {orderbook_info.get('bids', 0)}")
                print(f"   卖单数量: {orderbook_info.get('asks', 0)}")
                if orderbook_info.get('best_bid'):
                    print(f"   最佳买价: ${orderbook_info['best_bid']}")
                if orderbook_info.get('best_ask'):
                    print(f"   最佳卖价: ${orderbook_info['best_ask']}")
                if orderbook_info.get('spread'):
                    print(f"   价差: ${orderbook_info['spread']}")
                if orderbook_info.get('midpoint'):
                    print(f"   中间价: ${orderbook_info['midpoint']}")
            
            # 输入金额
            try:
                amount_input = input(f"\n💰 请输入金额 (USDC): ").strip()
                amount = float(amount_input)
            except ValueError:
                print("❌ 金额格式错误，请输入数字")
                return False
            
            # 验证输入
            errors = self.validate_inputs(market_info, outcome_index, amount)
            if errors:
                print("❌ 输入验证失败:")
                for error in errors:
                    print(f"   - {error}")
                return False
            
            # 计算预期份额
            expected_shares = amount / current_price
            
            # 显示订单摘要
            print(f"\n📋 订单摘要:")
            print(f"   市场: {market_info.get('question')}")
            print(f"   选择: {selected_outcome}")
            print(f"   金额: ${amount:.2f} USDC")
            print(f"   当前价格: ${current_price:.3f}")
            print(f"   预期份额: {expected_shares:.2f}")
            print(f"   Token ID: {token_id}")
            
            # 选择订单类型
            print(f"\n📝 订单类型:")
            print(f"   1. 市价单 (立即成交)")
            print(f"   2. 限价单 (指定价格)")
            
            order_type_input = input("请选择订单类型 (1/2): ").strip()
            
            if order_type_input == "1":
                order_type = "MARKET"
                order_price = None
            elif order_type_input == "2":
                order_type = "LIMIT"
                try:
                    price_input = input(f"请输入限价 (当前价格: ${current_price:.3f}): ").strip()
                    order_price = float(price_input)
                    
                    # 验证价格范围
                    tick_size_from_api = None
                    try:
                        tick_size_from_api = self.clob_client.get_tick_size(token_id)
                    except Exception:
                        pass
                    
                    tick_size = tick_size_from_api or float(market_info.get('orderPriceMinTickSize', 0.01))
                    
                    if order_price <= 0 or order_price >= 1:
                        print("❌ 价格必须在 0 到 1 之间")
                        return False
                    
                    # 检查价格精度
                    # --- 修改后的逻辑 ---
                    try:
                        raw_tick_size = self.clob_client.get_tick_size(token_id)
                        # 强制转换为 float，因为 API 可能返回字符串
                        tick_size = float(raw_tick_size) 
                    except Exception:
                        # 如果接口失败，从 market_info 获取并确保是 float
                        tick_size = float(market_info.get('orderPriceMinTickSize', 0.01))

                    if order_price <= 0 or order_price >= 1:
                        print("❌ 价格必须在 0 到 1 之间")
                        return False

                    # 现在 tick_size 确定是 float，运算不会报错
                    remainder = round(order_price % tick_size, 6)
                    if remainder != 0 and remainder != tick_size:
                        print(f"❌ 价格精度必须是 {tick_size} 的倍数")
                        return False
                    
                    expected_shares = amount / order_price
                    print(f"   限价订单预期份额: {expected_shares:.2f}")
                    
                except ValueError:
                    print("❌ 价格格式错误")
                    return False
            else:
                print("❌ 无效选择")
                return False
            
            # 最终确认
            print(f"\n📋 最终订单确认:")
            print(f"   市场: {market_info.get('question')}")
            print(f"   选择: {selected_outcome}")
            print(f"   类型: {'市价单' if order_type == 'MARKET' else f'限价单 @ ${order_price:.3f}'}")
            print(f"   金额: ${amount:.2f} USDC")
            print(f"   预期份额: {expected_shares:.2f}")
            
            confirm = input(f"\n❓ 确认下单? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ 订单已取消")
                return False
            
            # 执行下单
            print(f"\n🚀 正在下单...")
            result = self.place_order(token_id, amount, order_type, order_price, expected_shares)
            
            if result['success']:
                print(f"✅ 下单成功!")
                if result.get('order_id'):
                    print(f"   订单ID: {result['order_id']}")
                
                # 保存订单记录
                self.save_order_record(market_info, selected_outcome, amount, order_type, order_price, result)
                
            else:
                print(f"❌ 下单失败: {result.get('error', 'Unknown error')}")
                return False
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n\n❌ 用户取消操作")
            return False
        except Exception as e:
            print(f"❌ 下单过程出错: {e}")
            return False
    
    def place_order(self, token_id: str, amount: float, order_type: str, price: Optional[float], shares: float):
        """执行下单"""
        try:
            clean_price = (round(float(price), 2))
            clean_shares = (round(float(shares), 2))
            if order_type == "MARKET":
                # 市价单 - 使用create_market_order
                result = self.clob_client.create_market_order(
                    token_id=token_id,
                    size=clean_shares,
                    side="BUY"
                )
            else:
                # 限价单 - 使用create_order
                args = OrderArgs (
                    token_id=token_id,
                    price=clean_price,
                    size=clean_shares,
                    side="BUY"
                )
                signed_order = self.clob_client.create_order(
                    args
                )
                order_dict = signed_order.order.dict()

                resp = self.clob_client.post_order(signed_order)
                print(resp)
            return {
                'success': True,
                'order_id': resp.get("orderId"),
                'raw_data': resp
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_order_record(self, market_info: Dict, outcome: str, amount: float, 
                         order_type: str, price: Optional[float], result: Dict):
        """保存订单记录"""
        try:
            # 创建订单记录
            order_record = {
                'timestamp': datetime.now().isoformat(),
                'market_id': market_info.get('id'),
                'question': market_info.get('question'),
                'outcome': outcome,
                'amount': amount,
                'order_type': order_type,
                'price': price,
                'success': result['success'],
                'order_id': result.get('order_id'),
                'error': result.get('error'),
                'clob_result': result.get('result')
            }
            
            # 保存到文件
            orders_dir = "data/orders"
            os.makedirs(orders_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{orders_dir}/clob_order_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(order_record, f, indent=2, ensure_ascii=False)
            
            print(f"📁 订单记录已保存: {filename}")
            
        except Exception as e:
            print(f"⚠️  保存订单记录失败: {e}")

def main():
    """主函数"""
    print("🎯 Polymarket 交易工具")
    print("1. 单一市场下单")
    print("2. 订单管理 (取消订单、Split订单等)")
    
    choice = input("请选择功能 (1/2): ").strip()
    
    if choice == "1":
        placer = SingleOrderPlacer()
        success = placer.interactive_order()
        
        if success:
            print(f"\n🎉 操作完成!")
        else:
            print(f"\n❌ 操作失败")
            sys.exit(1)
    
    elif choice == "2":
        # 启动订单管理工具
        from order_management_tool import OrderManagementTool
        tool = OrderManagementTool()
        tool.run()
    
    else:
        print("❌ 无效选择")
        sys.exit(1)

if __name__ == "__main__":
    main()