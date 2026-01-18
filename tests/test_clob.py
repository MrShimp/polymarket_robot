#!/usr/bin/env python3
"""
Polymarket CLOB API 客户端测试脚本
测试各种CLOB API端点的功能
"""

import sys
import time
import os
from polymarket_clob_client import PolymarketCLOBClient
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_public_markets():
    """测试获取公开市场数据"""
    print("\n" + "="*50)
    print("测试: 获取公开市场数据")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    # 测试获取市场列表
    markets_data = client.get_markets(limit=5)
    if markets_data:
        markets = markets_data.get('data', [])
        print(f"✅ 成功获取 {len(markets)} 个市场")
        for i, market in enumerate(markets[:3], 1):
            print(f"  {i}. {market.get('question', 'N/A')[:50]}...")
            print(f"     条件ID: {market.get('condition_id', 'N/A')}")
            print(f"     活跃: {market.get('active', 'N/A')}")
            print(f"     接受订单: {market.get('accepting_orders', 'N/A')}")
        return markets
    else:
        print("❌ 获取市场列表失败")
        return []

def test_market_detail(condition_id: str):
    """测试获取市场详情"""
    print("\n" + "="*50)
    print(f"测试: 获取市场详情 (条件ID: {condition_id})")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    market = client.get_market(condition_id)
    if market:
        print("✅ 成功获取市场详情")
        print(f"  问题: {market.get('question', 'N/A')}")
        print(f"  描述: {market.get('description', 'N/A')[:100]}...")
        print(f"  结束时间: {market.get('end_date_iso', 'N/A')}")
        print(f"  做市商费用: {market.get('maker_base_fee', 'N/A')}")
        print(f"  接受者费用: {market.get('taker_base_fee', 'N/A')}")
        
        # 显示代币信息
        tokens = market.get('tokens', [])
        if tokens:
            print(f"  代币数量: {len(tokens)}")
            for i, token in enumerate(tokens[:2], 1):
                print(f"    {i}. {token.get('outcome', 'N/A')}")
                print(f"       代币ID: {token.get('token_id', 'N/A')}")
        
        return market
    else:
        print("❌ 获取市场详情失败")
        return None

def test_orderbook(token_id: str):
    """测试获取订单簿"""
    print("\n" + "="*50)
    print(f"测试: 获取订单簿 (代币ID: {token_id})")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    orderbook = client.get_orderbook(token_id)
    if orderbook:
        print("✅ 成功获取订单簿")
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        print(f"  买单数量: {len(bids)}")
        if bids:
            print("  最佳买单:")
            for i, bid in enumerate(bids[:3], 1):
                print(f"    {i}. 价格: {bid.get('price', 'N/A')}, 数量: {bid.get('size', 'N/A')}")
        
        print(f"  卖单数量: {len(asks)}")
        if asks:
            print("  最佳卖单:")
            for i, ask in enumerate(asks[:3], 1):
                print(f"    {i}. 价格: {ask.get('price', 'N/A')}, 数量: {ask.get('size', 'N/A')}")
        
        return orderbook
    else:
        print("❌ 获取订单簿失败")
        return None

def test_trades(market_condition_id: str = None):
    """测试获取交易历史"""
    print("\n" + "="*50)
    print("测试: 获取交易历史")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    trades_data = client.get_trades(market=market_condition_id, limit=5)
    if trades_data:
        trades = trades_data.get('data', [])
        print(f"✅ 成功获取 {len(trades)} 条交易记录")
        for i, trade in enumerate(trades[:3], 1):
            print(f"  {i}. 市场: {trade.get('market', 'N/A')}")
            print(f"     价格: {trade.get('price', 'N/A')}")
            print(f"     数量: {trade.get('size', 'N/A')}")
            print(f"     方向: {trade.get('side', 'N/A')}")
            print(f"     时间: {trade.get('match_time', 'N/A')}")
        return trades
    else:
        print("❌ 获取交易历史失败")
        return []

def test_prices(market_condition_id: str = None):
    """测试获取价格信息"""
    print("\n" + "="*50)
    print("测试: 获取价格信息")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    prices = client.get_prices(market=market_condition_id)
    if prices:
        print("✅ 成功获取价格信息")
        if isinstance(prices, dict):
            for token_id, price in list(prices.items())[:5]:
                print(f"  代币 {token_id}: {price}")
        else:
            print(f"  价格数据: {prices}")
        return prices
    else:
        print("❌ 获取价格信息失败")
        return None

def test_price_utilities(token_id: str):
    """测试价格工具函数"""
    print("\n" + "="*50)
    print(f"测试: 价格工具函数 (代币ID: {token_id})")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    # 测试最后交易价格
    last_price = client.get_last_trade_price(token_id)
    if last_price:
        print(f"✅ 最后交易价格: {last_price}")
    else:
        print("❌ 获取最后交易价格失败")
    
    # 测试中间价
    midpoint = client.get_midpoint(token_id)
    if midpoint:
        print(f"✅ 中间价: {midpoint}")
    else:
        print("❌ 获取中间价失败")
    
    # 测试价差
    spread = client.get_spread(token_id)
    if spread:
        print(f"✅ 价差: {spread}")
    else:
        print("❌ 获取价差失败")

def test_authenticated_apis():
    """测试需要认证的API (如果有API密钥)"""
    print("\n" + "="*50)
    print("测试: 认证API")
    print("="*50)
    
    # 检查环境变量中是否有API密钥
    api_key = os.getenv('POLYMARKET_API_KEY')
    api_secret = os.getenv('POLYMARKET_API_SECRET')
    passphrase = os.getenv('POLYMARKET_PASSPHRASE')
    
    if not api_key:
        print("⚠️  未找到API密钥，跳过认证API测试")
        print("   如需测试认证API，请设置环境变量:")
        print("   export POLYMARKET_API_KEY=your_api_key")
        print("   export POLYMARKET_API_SECRET=your_api_secret")
        print("   export POLYMARKET_PASSPHRASE=your_passphrase")
        return
    
    client = PolymarketCLOBClient(
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        save_data=True
    )
    
    # 测试获取余额
    balance = client.get_balance()
    if balance:
        print("✅ 成功获取账户余额")
        print(f"  余额信息: {balance}")
    else:
        print("❌ 获取账户余额失败")
    
    # 测试获取用户订单
    orders = client.get_orders(limit=5)
    if orders:
        orders_list = orders.get('data', [])
        print(f"✅ 成功获取 {len(orders_list)} 个用户订单")
        for i, order in enumerate(orders_list[:3], 1):
            print(f"  {i}. 订单ID: {order.get('id', 'N/A')}")
            print(f"     状态: {order.get('status', 'N/A')}")
            print(f"     价格: {order.get('price', 'N/A')}")
            print(f"     数量: {order.get('size', 'N/A')}")
    else:
        print("❌ 获取用户订单失败")
    
    # 测试获取用户交易历史
    user_trades = client.get_user_trades(limit=5)
    if user_trades:
        trades_list = user_trades.get('data', [])
        print(f"✅ 成功获取 {len(trades_list)} 条用户交易记录")
        for i, trade in enumerate(trades_list[:3], 1):
            print(f"  {i}. 交易ID: {trade.get('id', 'N/A')}")
            print(f"     价格: {trade.get('price', 'N/A')}")
            print(f"     数量: {trade.get('size', 'N/A')}")
            print(f"     时间: {trade.get('match_time', 'N/A')}")
    else:
        print("❌ 获取用户交易历史失败")

def test_convenience_methods():
    """测试便利方法"""
    print("\n" + "="*50)
    print("测试: 便利方法")
    print("="*50)
    
    client = PolymarketCLOBClient(save_data=True)
    
    # 测试获取所有市场 (限制数量避免请求过多)
    print("获取所有市场数据 (限制前20个)...")
    all_markets = []
    markets_data = client.get_markets(limit=20)
    if markets_data:
        all_markets = markets_data.get('data', [])
        print(f"✅ 获取到 {len(all_markets)} 个市场")
    else:
        print("❌ 获取所有市场失败")
    
    # 如果有市场数据，测试获取市场摘要
    if all_markets:
        condition_id = all_markets[0].get('condition_id')
        if condition_id:
            print(f"\n获取市场摘要 (条件ID: {condition_id})...")
            summary = client.get_market_summary(condition_id)
            if summary:
                print("✅ 成功获取市场摘要")
                print(f"  市场问题: {summary['market'].get('question', 'N/A')[:50]}...")
                print(f"  价格数据: {len(summary.get('prices') or {})} 个代币价格")
            else:
                print("❌ 获取市场摘要失败")

def main():
    """主测试函数"""
    print("🚀 开始测试 Polymarket CLOB API 客户端")
    print("=" * 60)
    
    try:
        # 1. 测试获取公开市场数据
        markets = test_public_markets()
        
        if not markets:
            print("\n❌ 无法获取市场数据，跳过后续测试")
            return
        
        # 获取第一个市场的信息用于后续测试
        first_market = markets[0] if markets else None
        condition_id = first_market.get('condition_id') if first_market else None
        
        if condition_id:
            print(f"\n📋 使用条件ID '{condition_id}' 进行后续测试")
            
            # 2. 测试获取市场详情
            market_detail = test_market_detail(condition_id)
            
            # 获取第一个代币ID用于测试
            token_id = None
            if market_detail and market_detail.get('tokens'):
                token_id = market_detail['tokens'][0].get('token_id')
            
            if token_id:
                print(f"\n📋 使用代币ID '{token_id}' 进行后续测试")
                
                # 3. 测试获取订单簿
                test_orderbook(token_id)
                
                # 4. 测试价格工具函数
                test_price_utilities(token_id)
            
            # 5. 测试获取交易历史
            test_trades(condition_id)
            
            # 6. 测试获取价格信息
            test_prices(condition_id)
        
        # 7. 测试认证API
        test_authenticated_apis()
        
        # 8. 测试便利方法
        test_convenience_methods()
        
        print("\n" + "="*60)
        print("🎉 所有测试完成！")
        print("📁 数据已保存到 ./data/ 目录")
        print("💡 如需测试认证功能，请设置相应的环境变量")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        logger.exception("测试失败")

if __name__ == "__main__":
    main()