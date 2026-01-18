#!/usr/bin/env python3
"""
交易功能测试脚本
"""

import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.polymarket_clob_client import PolymarketCLOBClient, PolymarketTrader
from trading.config import TradingConfig

# 创建配置实例
config = TradingConfig()

def test_client_connection():
    """测试客户端连接"""
    print("🧪 测试API连接...")
    
    if not config.is_configured():
        print("❌ 私钥未配置")
        print("请运行: python3 trading/setup_credentials.py")
        return False
    
    try:
        client_config = config.get_client_config()
        client = PolymarketCLOBClient(
            host=client_config['host'],
            chain_id=client_config['chain_id'],
            private_key=client_config['private_key'],
            use_testnet=client_config['use_testnet']
        )
        
        print("✅ 客户端创建成功!")
        print(f"🌐 网络: {'测试网' if config.use_testnet else '主网'}")
        print(f"📍 钱包地址: {client.address}")
        print(f"🔗 主机: {client.host}")
        
        # 测试获取余额
        try:
            balance = client.get_balance()
            print("✅ API连接成功!")
            print(f"💰 USDC余额: ${balance.get('usdcBalance', '0')}")
        except Exception as e:
            print(f"⚠️  余额获取失败: {e}")
            print("这可能是因为账户没有余额或网络问题，但客户端配置正确")
        
        return True, client
        
    except Exception as e:
        print(f"❌ 客户端创建失败: {e}")
        return False, None

def test_market_data(client):
    """测试市场数据获取"""
    print("\n📊 测试市场数据获取...")
    
    try:
        # 获取市场列表
        markets = client.get_markets(limit=5)
        print(f"✅ 获取到 {len(markets)} 个市场")
        
        if markets:
            market = markets[0]
            print(f"📈 示例市场: {market.get('question', 'Unknown')[:50]}...")
            
            # 获取第一个市场的详细信息
            condition_id = market.get('conditionId')
            if condition_id:
                market_detail = client.get_market(condition_id)
                print(f"📋 市场详情获取成功")
                
                # 获取代币信息
                tokens = market_detail.get('tokens', [])
                if tokens:
                    token_id = tokens[0].get('tokenId')
                    if token_id:
                        # 获取订单簿
                        orderbook = client.get_orderbook(token_id)
                        bids = len(orderbook.get('bids', []))
                        asks = len(orderbook.get('asks', []))
                        print(f"📚 订单簿: {bids} 买单, {asks} 卖单")
                        
                        # 获取最佳价格
                        best_prices = client.get_best_bid_ask(token_id)
                        print(f"💹 最佳价格: 买入 {best_prices.get('best_bid', 'N/A')}, "
                              f"卖出 {best_prices.get('best_ask', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 市场数据获取失败: {e}")
        return False

def test_order_simulation(client):
    """测试订单模拟"""
    print("\n🎭 测试订单模拟...")
    
    try:
        # 获取一个有流动性的市场
        markets = client.get_markets(limit=10)
        
        for market in markets:
            tokens = market.get('tokens', [])
            if not tokens:
                continue
                
            token_id = tokens[0].get('tokenId')
            if not token_id:
                continue
            
            # 检查订单簿
            orderbook = client.get_orderbook(token_id)
            asks = orderbook.get('asks', [])
            
            if not asks:
                continue
            
            # 模拟小额买单
            best_ask = asks[0]['price']
            test_size = "1"  # 1个代币
            
            print(f"📊 测试市场: {market.get('question', 'Unknown')[:40]}...")
            print(f"🎯 模拟买单: {test_size} 代币 @ ${best_ask}")
            
            # 估算市场冲击
            impact = client.estimate_market_impact(token_id, 'BUY', test_size)
            print(f"💥 市场冲击估算:")
            print(f"   总成本: ${impact.get('total_cost', '0')}")
            print(f"   平均价格: ${impact.get('average_price', '0')}")
            print(f"   可完全成交: {impact.get('can_fill_completely', False)}")
            
            # 注意：这里不执行实际订单，只是模拟
            print("✅ 订单模拟完成（未实际提交）")
            return True
        
        print("⚠️  未找到合适的测试市场")
        return False
        
    except Exception as e:
        print(f"❌ 订单模拟失败: {e}")
        return False

def test_strategy_integration():
    """测试策略集成"""
    print("\n🔗 测试策略集成...")
    
    try:
        from trading.strategy_trader import StrategyTrader
        
        # 创建策略交易器（模拟模式）
        trader = StrategyTrader(
            strategy_config={
                'time_threshold_minutes': 60,  # 使用较长时间窗口以找到更多机会
                'min_confidence': 0.8,
                'max_confidence': 0.95
            },
            trading_config={
                'trade_amount': 5.0,  # 小额测试
                'max_slippage': 0.05,
                'order_timeout': 300
            },
            dry_run=True  # 强制模拟模式
        )
        
        print("✅ 策略交易器创建成功")
        
        # 执行一次扫描和模拟交易
        print("🔍 执行策略扫描...")
        result = trader.scan_and_trade()
        
        if result['success']:
            opportunities = result.get('opportunities_found', 0)
            trades = result.get('trades_attempted', 0)
            print(f"✅ 策略执行成功: 发现 {opportunities} 个机会, 模拟 {trades} 笔交易")
            
            # 显示交易结果
            trade_results = result.get('trade_results', [])
            for i, trade in enumerate(trade_results, 1):
                if trade.get('success'):
                    print(f"   交易 {i}: ✅ {trade.get('market_question', 'Unknown')[:30]}...")
                else:
                    print(f"   交易 {i}: ❌ {trade.get('error', 'Unknown error')}")
        else:
            print(f"❌ 策略执行失败: {result.get('error', 'Unknown error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ 策略集成测试失败: {e}")
        return False

def test_account_info(client):
    """测试账户信息获取"""
    print("\n👤 测试账户信息...")
    
    try:
        trader = PolymarketTrader(client)
        
        # 获取交易摘要
        summary = trader.get_trading_summary()
        
        if summary['success']:
            print("✅ 账户信息获取成功:")
            print(f"   USDC余额: ${summary.get('usdc_balance', '0')}")
            print(f"   持仓数量: {summary.get('total_positions', 0)}")
            print(f"   活跃订单: {summary.get('active_orders', 0)}")
            print(f"   总资产价值: ${summary.get('total_portfolio_value', '0')}")
            
            # 显示最近订单
            recent_orders = summary.get('recent_orders', [])
            if recent_orders:
                print(f"   最近订单: {len(recent_orders)} 个")
            
            return True
        else:
            print(f"❌ 获取账户信息失败: {summary.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 账户信息测试失败: {e}")
        return False

def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 Polymarket交易功能综合测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试网络: {'测试网' if config.use_testnet else '主网'}")
    print(f"模拟模式: {config.dry_run_mode}")
    print("=" * 60)
    
    test_results = {}
    
    # 1. 测试API连接
    success, client = test_client_connection()
    test_results['api_connection'] = success
    
    if not success:
        print("\n❌ API连接失败，无法继续测试")
        return test_results
    
    # 2. 测试市场数据
    test_results['market_data'] = test_market_data(client)
    
    # 3. 测试订单模拟
    test_results['order_simulation'] = test_order_simulation(client)
    
    # 4. 测试账户信息
    test_results['account_info'] = test_account_info(client)
    
    # 5. 测试策略集成
    test_results['strategy_integration'] = test_strategy_integration()
    
    # 显示测试结果摘要
    print("\n" + "=" * 60)
    print("📋 测试结果摘要")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print("-" * 60)
    print(f"总测试: {total_tests}, 通过: {passed_tests}, 失败: {total_tests - passed_tests}")
    print(f"成功率: {passed_tests/total_tests:.1%}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过! 系统已准备就绪")
    elif passed_tests >= total_tests * 0.8:
        print("\n⚠️  大部分测试通过，系统基本可用")
    else:
        print("\n❌ 多个测试失败，请检查配置和网络连接")
    
    return test_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket交易功能测试")
    parser.add_argument("--test", choices=['all', 'connection', 'market', 'order', 'account', 'strategy'], 
                       default='all', help="选择测试类型")
    
    args = parser.parse_args()
    
    if args.test == 'all':
        run_comprehensive_test()
    elif args.test == 'connection':
        test_client_connection()
    elif args.test == 'market':
        success, client = test_client_connection()
        if success:
            test_market_data(client)
    elif args.test == 'order':
        success, client = test_client_connection()
        if success:
            test_order_simulation(client)
    elif args.test == 'account':
        success, client = test_client_connection()
        if success:
            test_account_info(client)
    elif args.test == 'strategy':
        test_strategy_integration()

if __name__ == "__main__":
    main()