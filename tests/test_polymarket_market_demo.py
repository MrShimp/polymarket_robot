#!/usr/bin/env python3
"""
Polymarket Market API 客户端演示
由于gamma-api.polymarket.com可能不可访问，使用模拟数据演示功能
"""

import json
from datetime import datetime, timedelta
from polymarket_market_client import PolymarketMarketClient

# 模拟数据
MOCK_EVENTS = [
    {
        "id": "event_001",
        "slug": "2024-us-presidential-election",
        "title": "2024 US Presidential Election",
        "description": "Who will win the 2024 United States Presidential Election?",
        "image": "https://example.com/election.jpg",
        "active": True,
        "closed": False,
        "archived": False,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-11-05T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z",
        "category": "Politics",
        "tags": ["election", "politics", "usa"],
        "volume": 15000000,
        "liquidity": 2500000,
        "markets": [
            {
                "id": "market_001",
                "slug": "trump-vs-biden-2024",
                "question": "Will Donald Trump win the 2024 Presidential Election?",
                "active": True,
                "closed": False,
                "volume": 8000000
            }
        ]
    },
    {
        "id": "event_002",
        "slug": "bitcoin-price-prediction-2024",
        "title": "Bitcoin Price Prediction 2024",
        "description": "Will Bitcoin reach $100,000 by the end of 2024?",
        "image": "https://example.com/bitcoin.jpg",
        "active": True,
        "closed": False,
        "archived": False,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z",
        "category": "Crypto",
        "tags": ["bitcoin", "crypto", "price"],
        "volume": 5000000,
        "liquidity": 800000
    },
    {
        "id": "event_003",
        "slug": "super-bowl-2024",
        "title": "Super Bowl 2024",
        "description": "Which team will win Super Bowl LVIII?",
        "image": "https://example.com/superbowl.jpg",
        "active": False,
        "closed": True,
        "archived": False,
        "start_date": "2024-02-01T00:00:00Z",
        "end_date": "2024-02-11T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-02-12T12:00:00Z",
        "category": "Sports",
        "tags": ["football", "nfl", "superbowl"],
        "volume": 12000000,
        "liquidity": 0
    }
]

MOCK_MARKETS = [
    {
        "id": "market_001",
        "slug": "trump-wins-2024-election",
        "question": "Will Donald Trump win the 2024 Presidential Election?",
        "description": "This market resolves to 'Yes' if Donald Trump wins the 2024 US Presidential Election.",
        "event_slug": "2024-us-presidential-election",
        "active": True,
        "closed": False,
        "archived": False,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-11-05T23:59:59Z",
        "end_date_iso": "2024-11-05T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z",
        "category": "Politics",
        "tags": ["trump", "election", "politics"],
        "volume": 8000000,
        "liquidity": 1200000,
        "outcomes": [
            {
                "id": "outcome_001_yes",
                "slug": "yes",
                "name": "Yes",
                "price": 0.52
            },
            {
                "id": "outcome_001_no",
                "slug": "no", 
                "name": "No",
                "price": 0.48
            }
        ]
    },
    {
        "id": "market_002",
        "slug": "bitcoin-100k-2024",
        "question": "Will Bitcoin reach $100,000 by end of 2024?",
        "description": "This market resolves to 'Yes' if Bitcoin price reaches or exceeds $100,000 USD by December 31, 2024.",
        "event_slug": "bitcoin-price-prediction-2024",
        "active": True,
        "closed": False,
        "archived": False,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "end_date_iso": "2024-12-31T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z",
        "category": "Crypto",
        "tags": ["bitcoin", "crypto", "price"],
        "volume": 5000000,
        "liquidity": 800000,
        "outcomes": [
            {
                "id": "outcome_002_yes",
                "slug": "yes",
                "name": "Yes",
                "price": 0.35
            },
            {
                "id": "outcome_002_no",
                "slug": "no",
                "name": "No", 
                "price": 0.65
            }
        ]
    }
]

MOCK_CATEGORIES = [
    {
        "id": "politics",
        "name": "Politics",
        "slug": "politics",
        "description": "Political events and elections",
        "image": "https://example.com/politics.jpg",
        "event_count": 25,
        "market_count": 45
    },
    {
        "id": "crypto",
        "name": "Crypto",
        "slug": "crypto",
        "description": "Cryptocurrency and blockchain events",
        "image": "https://example.com/crypto.jpg",
        "event_count": 18,
        "market_count": 32
    },
    {
        "id": "sports",
        "name": "Sports",
        "slug": "sports",
        "description": "Sports events and competitions",
        "image": "https://example.com/sports.jpg",
        "event_count": 42,
        "market_count": 78
    }
]

class MockPolymarketMarketClient(PolymarketMarketClient):
    """模拟的Polymarket Market客户端，用于演示"""
    
    def __init__(self, save_data: bool = True):
        super().__init__(save_data=save_data)
        print("🔧 使用模拟数据演示 Polymarket Market 客户端功能")
    
    def get_events(self, active=None, closed=None, limit=None, offset=None, order=None, order_by=None, slug=None):
        """返回模拟事件数据"""
        events = MOCK_EVENTS.copy()
        
        # 应用筛选
        if active is not None:
            events = [e for e in events if e['active'] == active]
        if closed is not None:
            events = [e for e in events if e['closed'] == closed]
        if slug:
            events = [e for e in events if e['slug'] == slug]
        
        # 应用排序
        if order_by == 'volume':
            events.sort(key=lambda x: x.get('volume', 0), reverse=(order == 'desc'))
        
        # 应用分页
        if offset:
            events = events[offset:]
        if limit:
            events = events[:limit]
        
        # 保存数据
        if self.save_data and self.data_saver and events:
            self.data_saver.save_polymarket_events_data(events)
        
        return events
    
    def get_event_by_slug(self, slug):
        """根据slug返回模拟事件数据"""
        for event in MOCK_EVENTS:
            if event['slug'] == slug:
                if self.save_data and self.data_saver:
                    self.data_saver.save_polymarket_event_detail(event)
                return event
        return None
    
    def get_markets(self, active=None, closed=None, limit=None, offset=None, order=None, order_by=None, event_slug=None):
        """返回模拟市场数据"""
        markets = MOCK_MARKETS.copy()
        
        # 应用筛选
        if active is not None:
            markets = [m for m in markets if m['active'] == active]
        if closed is not None:
            markets = [m for m in markets if m['closed'] == closed]
        if event_slug:
            markets = [m for m in markets if m['event_slug'] == event_slug]
        
        # 应用排序
        if order_by == 'volume':
            markets.sort(key=lambda x: x.get('volume', 0), reverse=(order == 'desc'))
        
        # 应用分页
        if offset:
            markets = markets[offset:]
        if limit:
            markets = markets[:limit]
        
        # 保存数据
        if self.save_data and self.data_saver and markets:
            self.data_saver.save_polymarket_markets_data(markets)
        
        return markets
    
    def get_market_by_slug(self, slug):
        """根据slug返回模拟市场数据"""
        for market in MOCK_MARKETS:
            if market['slug'] == slug:
                if self.save_data and self.data_saver:
                    self.data_saver.save_polymarket_market_detail(market)
                return market
        return None
    
    def search_events(self, query, limit=20):
        """搜索模拟事件数据"""
        results = []
        query_lower = query.lower()
        
        for event in MOCK_EVENTS:
            title = event.get('title', '').lower()
            description = event.get('description', '').lower()
            tags = [tag.lower() for tag in event.get('tags', [])]
            
            if (query_lower in title or 
                query_lower in description or 
                any(query_lower in tag for tag in tags)):
                results.append(event)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_categories(self):
        """返回模拟分类数据"""
        if self.save_data and self.data_saver:
            self.data_saver.save_polymarket_categories_data(MOCK_CATEGORIES)
        return MOCK_CATEGORIES
    
    def get_events_by_category(self, category, limit=20):
        """根据分类返回模拟事件数据"""
        results = []
        
        for event in MOCK_EVENTS:
            if event.get('category', '').lower() == category.lower():
                results.append(event)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_market_statistics(self, market_slug):
        """返回模拟市场统计数据"""
        return {
            "market_slug": market_slug,
            "total_volume": 5000000,
            "daily_volume": 250000,
            "total_trades": 15420,
            "unique_traders": 3250,
            "price_change_24h": 0.02,
            "volatility": 0.15
        }
    
    def get_market_history(self, market_slug, start_date=None, end_date=None):
        """返回模拟市场历史数据"""
        # 生成一些模拟历史数据
        history = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(30):
            date = base_date + timedelta(days=i)
            history.append({
                "timestamp": date.isoformat(),
                "price": 0.50 + (i * 0.001),
                "volume": 100000 + (i * 1000),
                "outcome_id": "outcome_001_yes",
                "outcome_name": "Yes"
            })
        
        if self.save_data and self.data_saver and history:
            self.data_saver.save_polymarket_market_history(market_slug, history)
        
        return history

def demo_basic_usage():
    """演示基本用法"""
    print("\n" + "="*60)
    print("📊 Polymarket Market 客户端基本用法演示")
    print("="*60)
    
    # 创建模拟客户端
    client = MockPolymarketMarketClient(save_data=True)
    
    # 1. 获取活跃事件 (基于提供的API端点)
    print("\n🔍 获取活跃事件 (active=true&closed=false&limit=5):")
    events = client.get_active_events(limit=5)
    for i, event in enumerate(events, 1):
        print(f"  {i}. {event['title']}")
        print(f"     Slug: {event['slug']}")
        print(f"     Category: {event['category']}")
        print(f"     Volume: ${event['volume']:,}")
        print(f"     Active: {event['active']}, Closed: {event['closed']}")
    
    # 2. 获取活跃市场
    print(f"\n🔍 获取活跃市场:")
    markets = client.get_markets(active=True, closed=False, limit=3)
    for i, market in enumerate(markets, 1):
        print(f"  {i}. {market['question']}")
        print(f"     Slug: {market['slug']}")
        print(f"     Volume: ${market['volume']:,}")
        print(f"     Liquidity: ${market['liquidity']:,}")
    
    # 3. 获取事件详情
    if events:
        event_slug = events[0]['slug']
        print(f"\n📋 获取事件详情 (slug: {event_slug}):")
        event_detail = client.get_event_by_slug(event_slug)
        if event_detail:
            print(f"  标题: {event_detail['title']}")
            print(f"  描述: {event_detail['description']}")
            print(f"  开始时间: {event_detail['start_date']}")
            print(f"  结束时间: {event_detail['end_date']}")
            print(f"  标签: {', '.join(event_detail['tags'])}")
    
    # 4. 获取市场详情
    if markets:
        market_slug = markets[0]['slug']
        print(f"\n📊 获取市场详情 (slug: {market_slug}):")
        market_detail = client.get_market_by_slug(market_slug)
        if market_detail:
            print(f"  问题: {market_detail['question']}")
            print(f"  描述: {market_detail['description']}")
            print(f"  结束时间: {market_detail['end_date_iso']}")
            
            outcomes = market_detail.get('outcomes', [])
            if outcomes:
                print(f"  结果选项:")
                for outcome in outcomes:
                    print(f"    - {outcome['name']}: ${outcome['price']:.2f}")
    
    return events, markets

def demo_search_and_categories():
    """演示搜索和分类功能"""
    print("\n" + "="*60)
    print("🔍 搜索和分类功能演示")
    print("="*60)
    
    client = MockPolymarketMarketClient(save_data=True)
    
    # 1. 搜索功能
    search_terms = ["election", "bitcoin", "sports"]
    for term in search_terms:
        print(f"\n🔍 搜索 '{term}':")
        results = client.search_events(term, limit=3)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']}")
            print(f"     Category: {result['category']}")
    
    # 2. 获取分类
    print(f"\n📂 获取所有分类:")
    categories = client.get_categories()
    for i, category in enumerate(categories, 1):
        print(f"  {i}. {category['name']}")
        print(f"     描述: {category['description']}")
        print(f"     事件数: {category['event_count']}, 市场数: {category['market_count']}")
    
    # 3. 按分类获取事件
    if categories:
        category_slug = categories[0]['slug']
        print(f"\n📋 获取分类 '{category_slug}' 的事件:")
        category_events = client.get_events_by_category(category_slug, limit=3)
        for i, event in enumerate(category_events, 1):
            print(f"  {i}. {event['title']}")

def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "="*60)
    print("🚀 高级功能演示")
    print("="*60)
    
    client = MockPolymarketMarketClient(save_data=True)
    
    # 1. 获取热门事件
    print("🔥 获取热门事件:")
    trending = client.get_trending_events(limit=3)
    for i, event in enumerate(trending, 1):
        print(f"  {i}. {event['title']}")
        print(f"     Volume: ${event['volume']:,}")
    
    # 2. 获取高交易量市场
    print(f"\n💰 获取高交易量市场:")
    high_volume = client.get_high_volume_markets(min_volume=1000000, limit=3)
    for i, market in enumerate(high_volume, 1):
        print(f"  {i}. {market['question']}")
        print(f"     Volume: ${market['volume']:,}")
    
    # 3. 获取即将到期的市场
    print(f"\n⏰ 获取即将到期的市场:")
    near_expiry = client.get_near_expiry_markets(days=365, limit=3)
    for i, market in enumerate(near_expiry, 1):
        print(f"  {i}. {market['question']}")
        print(f"     结束时间: {market['end_date_iso']}")
    
    # 4. 获取市场统计
    if high_volume:
        market_slug = high_volume[0]['slug']
        print(f"\n📊 获取市场统计 (slug: {market_slug}):")
        stats = client.get_market_statistics(market_slug)
        if stats:
            print(f"  总交易量: ${stats['total_volume']:,}")
            print(f"  日交易量: ${stats['daily_volume']:,}")
            print(f"  总交易数: {stats['total_trades']:,}")
            print(f"  独立交易者: {stats['unique_traders']:,}")
            print(f"  24h价格变化: {stats['price_change_24h']:.2%}")
    
    # 5. 获取市场历史
    if high_volume:
        market_slug = high_volume[0]['slug']
        print(f"\n📈 获取市场历史 (slug: {market_slug}):")
        history = client.get_market_history(market_slug)
        if history:
            print(f"  历史数据点: {len(history)} 个")
            print(f"  最早数据: {history[0]['timestamp'][:10]}")
            print(f"  最新数据: {history[-1]['timestamp'][:10]}")
            print(f"  价格范围: ${history[0]['price']:.3f} - ${history[-1]['price']:.3f}")

def demo_data_analysis():
    """演示数据分析功能"""
    print("\n" + "="*60)
    print("📈 数据分析演示")
    print("="*60)
    
    client = MockPolymarketMarketClient(save_data=True)
    
    # 获取所有数据
    events = client.get_events()
    markets = client.get_markets()
    
    # 统计分析
    total_volume = sum(event['volume'] for event in events)
    total_liquidity = sum(event['liquidity'] for event in events)
    active_events = len([e for e in events if e['active']])
    
    print(f"📊 总体统计:")
    print(f"  总事件数: {len(events)}")
    print(f"  活跃事件: {active_events}")
    print(f"  总交易量: ${total_volume:,}")
    print(f"  总流动性: ${total_liquidity:,}")
    
    # 按分类分组
    category_stats = {}
    for event in events:
        category = event['category']
        if category not in category_stats:
            category_stats[category] = {'count': 0, 'volume': 0}
        category_stats[category]['count'] += 1
        category_stats[category]['volume'] += event['volume']
    
    print(f"\n📂 按分类统计:")
    for category, stats in category_stats.items():
        print(f"  {category}: {stats['count']} 个事件, ${stats['volume']:,} 交易量")
    
    # 市场分析
    market_volume = sum(market['volume'] for market in markets)
    avg_market_volume = market_volume / len(markets) if markets else 0
    
    print(f"\n💹 市场分析:")
    print(f"  总市场数: {len(markets)}")
    print(f"  市场总交易量: ${market_volume:,}")
    print(f"  平均市场交易量: ${avg_market_volume:,.0f}")

def main():
    """主演示函数"""
    print("🚀 Polymarket Market API 客户端演示")
    print("基于 Gamma API: https://gamma-api.polymarket.com")
    print("注意: 由于实际API可能不可访问，这里使用模拟数据进行演示")
    
    try:
        # 基本用法演示
        events, markets = demo_basic_usage()
        
        # 搜索和分类演示
        demo_search_and_categories()
        
        # 高级功能演示
        demo_advanced_features()
        
        # 数据分析演示
        demo_data_analysis()
        
        print("\n" + "="*60)
        print("✅ 演示完成！")
        print("📁 所有模拟数据已保存到 ./data/ 目录")
        print("💡 实际使用时，请确保API端点正确并可访问")
        print("🔗 API文档: https://gamma-api.polymarket.com")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")

if __name__ == "__main__":
    main()