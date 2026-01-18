#!/usr/bin/env python3
"""
Polymarket Market API 客户端测试脚本
测试Gamma API端点的功能
"""

import sys
import time
from polymarket_market_client import PolymarketMarketClient
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_get_active_events():
    """测试获取活跃事件 (基于提供的API端点)"""
    print("\n" + "="*50)
    print("测试: 获取活跃事件 (active=true&closed=false&limit=5)")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 测试基本的活跃事件获取
    events = client.get_active_events(limit=5)
    if events:
        print(f"✅ 成功获取 {len(events)} 个活跃事件")
        for i, event in enumerate(events[:3], 1):
            title = event.get('title') or event.get('name', 'N/A')
            slug = event.get('slug', 'N/A')
            active = event.get('active', 'N/A')
            closed = event.get('closed', 'N/A')
            volume = event.get('volume', 'N/A')
            
            print(f"  {i}. {title[:50]}...")
            print(f"     Slug: {slug}")
            print(f"     Active: {active}, Closed: {closed}")
            print(f"     Volume: {volume}")
        return events
    else:
        print("❌ 获取活跃事件失败")
        return []

def test_get_events_with_params():
    """测试带参数的事件获取"""
    print("\n" + "="*50)
    print("测试: 带参数的事件获取")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 测试不同参数组合
    test_cases = [
        {"active": True, "closed": False, "limit": 3, "description": "活跃且未关闭的事件"},
        {"active": False, "closed": True, "limit": 3, "description": "非活跃且已关闭的事件"},
        {"limit": 10, "order_by": "volume", "order": "desc", "description": "按交易量降序排列"}
    ]
    
    for case in test_cases:
        description = case.pop("description")
        print(f"\n🔍 {description}:")
        
        events = client.get_events(**case)
        if events:
            print(f"  ✅ 获取到 {len(events)} 个事件")
            for i, event in enumerate(events[:2], 1):
                title = event.get('title') or event.get('name', 'N/A')
                volume = event.get('volume', 0)
                print(f"    {i}. {title[:40]}... (Volume: {volume})")
        else:
            print(f"  ❌ 获取失败或无结果")
        
        time.sleep(1)  # 避免请求过于频繁

def test_get_markets():
    """测试获取市场"""
    print("\n" + "="*50)
    print("测试: 获取市场")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 测试获取活跃市场
    markets = client.get_markets(active=True, closed=False, limit=5)
    if markets:
        print(f"✅ 成功获取 {len(markets)} 个活跃市场")
        for i, market in enumerate(markets[:3], 1):
            question = market.get('question') or market.get('title', 'N/A')
            slug = market.get('slug', 'N/A')
            volume = market.get('volume', 'N/A')
            
            print(f"  {i}. {question[:50]}...")
            print(f"     Slug: {slug}")
            print(f"     Volume: {volume}")
        return markets
    else:
        print("❌ 获取市场失败")
        return []

def test_get_event_detail(events):
    """测试获取事件详情"""
    if not events:
        print("\n⚠️  跳过事件详情测试 - 没有可用事件")
        return
    
    print("\n" + "="*50)
    print("测试: 获取事件详情")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 获取第一个事件的详情
    first_event = events[0]
    event_slug = first_event.get('slug')
    
    if event_slug:
        print(f"🔍 获取事件详情: {event_slug}")
        event_detail = client.get_event_by_slug(event_slug)
        
        if event_detail:
            print("✅ 成功获取事件详情")
            title = event_detail.get('title') or event_detail.get('name', 'N/A')
            description = event_detail.get('description', 'N/A')
            category = event_detail.get('category', 'N/A')
            
            print(f"  标题: {title}")
            print(f"  描述: {description[:100]}...")
            print(f"  分类: {category}")
            
            # 检查是否有关联市场
            markets = event_detail.get('markets', [])
            if markets:
                print(f"  关联市场: {len(markets)} 个")
        else:
            print("❌ 获取事件详情失败")
    else:
        print("⚠️  事件没有slug，跳过详情测试")

def test_get_market_detail(markets):
    """测试获取市场详情"""
    if not markets:
        print("\n⚠️  跳过市场详情测试 - 没有可用市场")
        return
    
    print("\n" + "="*50)
    print("测试: 获取市场详情")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 获取第一个市场的详情
    first_market = markets[0]
    market_slug = first_market.get('slug')
    
    if market_slug:
        print(f"🔍 获取市场详情: {market_slug}")
        market_detail = client.get_market_by_slug(market_slug)
        
        if market_detail:
            print("✅ 成功获取市场详情")
            question = market_detail.get('question', 'N/A')
            description = market_detail.get('description', 'N/A')
            end_date = market_detail.get('end_date_iso', market_detail.get('end_date', 'N/A'))
            
            print(f"  问题: {question}")
            print(f"  描述: {description[:100]}...")
            print(f"  结束时间: {end_date}")
            
            # 检查结果选项
            outcomes = market_detail.get('outcomes', [])
            if outcomes:
                print(f"  结果选项: {len(outcomes)} 个")
                for i, outcome in enumerate(outcomes[:2], 1):
                    name = outcome.get('name', 'N/A')
                    price = outcome.get('price', 'N/A')
                    print(f"    {i}. {name} - 价格: {price}")
        else:
            print("❌ 获取市场详情失败")
    else:
        print("⚠️  市场没有slug，跳过详情测试")

def test_search_functionality():
    """测试搜索功能"""
    print("\n" + "="*50)
    print("测试: 搜索功能")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 测试搜索
    search_terms = ["election", "trump", "bitcoin", "sports", "AI"]
    
    for term in search_terms:
        print(f"\n🔍 搜索关键词: '{term}'")
        results = client.search_events(term, limit=3)
        
        if results:
            print(f"  ✅ 找到 {len(results)} 个相关结果")
            for i, result in enumerate(results[:2], 1):
                title = result.get('title') or result.get('name', 'N/A')
                print(f"    {i}. {title[:40]}...")
        else:
            print(f"  ❌ 搜索 '{term}' 失败或无结果")
        
        time.sleep(1)  # 避免请求过于频繁

def test_categories():
    """测试分类功能"""
    print("\n" + "="*50)
    print("测试: 分类功能")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 获取所有分类
    categories = client.get_categories()
    if categories:
        print(f"✅ 成功获取 {len(categories)} 个分类")
        for i, category in enumerate(categories[:5], 1):
            name = category.get('name', 'N/A')
            slug = category.get('slug', 'N/A')
            event_count = category.get('event_count', 'N/A')
            
            print(f"  {i}. {name} (Slug: {slug})")
            print(f"     事件数量: {event_count}")
        
        # 测试获取特定分类的事件
        if categories:
            first_category = categories[0]
            category_slug = first_category.get('slug')
            
            if category_slug:
                print(f"\n🔍 获取分类 '{category_slug}' 的事件:")
                category_events = client.get_events_by_category(category_slug, limit=3)
                
                if category_events:
                    print(f"  ✅ 找到 {len(category_events)} 个事件")
                    for i, event in enumerate(category_events[:2], 1):
                        title = event.get('title') or event.get('name', 'N/A')
                        print(f"    {i}. {title[:40]}...")
                else:
                    print(f"  ❌ 获取分类事件失败")
    else:
        print("❌ 获取分类失败")

def test_advanced_features():
    """测试高级功能"""
    print("\n" + "="*50)
    print("测试: 高级功能")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 测试获取热门事件
    print("🔥 获取热门事件:")
    trending = client.get_trending_events(limit=3)
    if trending:
        print(f"  ✅ 获取到 {len(trending)} 个热门事件")
        for i, event in enumerate(trending, 1):
            title = event.get('title') or event.get('name', 'N/A')
            volume = event.get('volume', 0)
            print(f"    {i}. {title[:40]}... (Volume: {volume})")
    else:
        print("  ❌ 获取热门事件失败")
    
    # 测试获取高交易量市场
    print(f"\n💰 获取高交易量市场:")
    high_volume = client.get_high_volume_markets(min_volume=1000, limit=3)
    if high_volume:
        print(f"  ✅ 获取到 {len(high_volume)} 个高交易量市场")
        for i, market in enumerate(high_volume, 1):
            question = market.get('question', 'N/A')
            volume = market.get('volume', 0)
            print(f"    {i}. {question[:40]}... (Volume: {volume})")
    else:
        print("  ❌ 获取高交易量市场失败")
    
    # 测试获取即将到期的市场
    print(f"\n⏰ 获取即将到期的市场:")
    near_expiry = client.get_near_expiry_markets(days=30, limit=3)
    if near_expiry:
        print(f"  ✅ 获取到 {len(near_expiry)} 个即将到期的市场")
        for i, market in enumerate(near_expiry, 1):
            question = market.get('question', 'N/A')
            end_date = market.get('end_date_iso', market.get('end_date', 'N/A'))
            print(f"    {i}. {question[:40]}...")
            print(f"       结束时间: {end_date}")
    else:
        print("  ❌ 获取即将到期市场失败")

def test_market_statistics():
    """测试市场统计功能"""
    print("\n" + "="*50)
    print("测试: 市场统计功能")
    print("="*50)
    
    client = PolymarketMarketClient(save_data=True)
    
    # 先获取一些市场
    markets = client.get_markets(active=True, limit=3)
    
    if markets:
        first_market = markets[0]
        market_slug = first_market.get('slug')
        
        if market_slug:
            print(f"📊 获取市场统计: {market_slug}")
            
            # 获取市场统计
            stats = client.get_market_statistics(market_slug)
            if stats:
                print("  ✅ 成功获取市场统计")
                print(f"    统计数据: {stats}")
            else:
                print("  ❌ 获取市场统计失败")
            
            # 获取市场摘要
            print(f"\n📋 获取市场摘要: {market_slug}")
            summary = client.get_market_summary(market_slug)
            if summary:
                print("  ✅ 成功获取市场摘要")
                market_info = summary.get('market', {})
                question = market_info.get('question', 'N/A')
                print(f"    问题: {question[:50]}...")
            else:
                print("  ❌ 获取市场摘要失败")
    else:
        print("⚠️  没有可用市场进行统计测试")

def main():
    """主测试函数"""
    print("🚀 开始测试 Polymarket Market API 客户端")
    print("基于 Gamma API: https://gamma-api.polymarket.com")
    print("=" * 60)
    
    try:
        # 1. 测试获取活跃事件 (基于提供的API端点)
        events = test_get_active_events()
        
        # 2. 测试带参数的事件获取
        test_get_events_with_params()
        
        # 3. 测试获取市场
        markets = test_get_markets()
        
        # 4. 测试获取事件详情
        test_get_event_detail(events)
        
        # 5. 测试获取市场详情
        test_get_market_detail(markets)
        
        # 6. 测试搜索功能
        test_search_functionality()
        
        # 7. 测试分类功能
        test_categories()
        
        # 8. 测试高级功能
        test_advanced_features()
        
        # 9. 测试市场统计功能
        test_market_statistics()
        
        print("\n" + "="*60)
        print("🎉 所有测试完成！")
        print("📁 数据已保存到 ./data/ 目录")
        print("💡 查看生成的CSV文件了解数据结构")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        logger.exception("测试失败")

if __name__ == "__main__":
    main()