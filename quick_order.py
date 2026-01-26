#!/usr/bin/env python3
"""
快速下单测试 - 使用推荐的测试市场
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from place_single_order import SingleOrderPlacer

def quick_test():
    """快速测试下单功能"""
    print("🚀 快速下单测试")
    print("使用推荐的测试市场")
    print("="*50)
    
    placer = SingleOrderPlacer()
    
    # 使用我们之前找到的测试市场
    test_market_id = "1206415"  # LoL电竞比赛
    
    print(f"📝 测试市场ID: {test_market_id}")
    
    # 获取市场信息
    market_info = placer.get_market_info(test_market_id)
    
    if market_info:
        placer.display_market_info(market_info)
        
        # 显示Token IDs
        token_ids = market_info.get('clobTokenIds', [])
        outcomes = market_info.get('outcomes', [])
        
        print(f"\n🔧 CLOB Token IDs:")
        for i, (outcome, token_id) in enumerate(zip(outcomes, token_ids)):
            print(f"   {i+1}. {outcome}: {token_id}")
        
        # 检查订单簿
        if token_ids:
            print(f"\n📖 检查订单簿...")
            for i, (outcome, token_id) in enumerate(zip(outcomes, token_ids)):
                print(f"\n   {outcome}:")
                orderbook_info = placer.get_orderbook_info(token_id)
                if orderbook_info:
                    if orderbook_info.get('error'):
                        if 'No orderbook exists' in orderbook_info['error']:
                            print(f"     状态: 无订单簿 (市场可能不接受订单)")
                        else:
                            print(f"     状态: 获取失败 - {orderbook_info['error']}")
                    else:
                        print(f"     买单: {orderbook_info.get('bids', 0)}")
                        print(f"     卖单: {orderbook_info.get('asks', 0)}")
                        print(f"     最佳买价: {orderbook_info.get('best_bid', 'N/A')}")
                        print(f"     最佳卖价: {orderbook_info.get('best_ask', 'N/A')}")
        
        # 检查市场是否接受订单
        accepting_orders = market_info.get('acceptingOrders', True)
        if not accepting_orders:
            print(f"\n⚠️  注意: 此市场当前不接受订单")
            print(f"   这可能是因为:")
            print(f"   - 市场已结束或暂停")
            print(f"   - 正在等待结果确认")
            print(f"   - 技术维护中")
        
        print(f"\n💡 使用方法:")
        if accepting_orders:
            print(f"   python3 place_single_order.py")
            print(f"   输入市场ID: {test_market_id}")
            print(f"   选择结果: 1 或 2")
            print(f"   输入金额: 10 (建议小额测试)")
        else:
            print(f"   此市场当前不可交易，请选择其他市场")
            print(f"   可以运行 python3 sync/polymarket_sync.py 查找活跃市场")
        
    else:
        print("❌ 无法获取市场信息")

if __name__ == "__main__":
    quick_test()