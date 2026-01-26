import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolymarketMarketClient:
    """
    Polymarket Market API客户端
    基于Gamma API: https://gamma-api.polymarket.com
    """
    
    def __init__(self, 
                 base_url: str = "https://gamma-api.polymarket.com",
                 save_data: bool = True):
        self.base_url = base_url
        self.save_data = save_data
        self.session = requests.Session()
        
        # 设置基础请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://polymarket.com/'
        })
    
    def _save_to_csv(self, data: List[Dict], filename: str):
        """简单的CSV保存功能"""
        if not data or not self.save_data:
            return
        
        try:
            os.makedirs("data/api_cache", exist_ok=True)
            filepath = f"data/api_cache/{filename}"
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        except Exception as e:
            logger.warning(f"Failed to save data to {filename}: {e}")
    
    def get_events(self, 
                   active: Optional[bool] = None,
                   closed: Optional[bool] = None,
                   limit: Optional[int] = None,
                   offset: Optional[int] = None,
                   order: Optional[str] = None,
                   order_by: Optional[str] = None,
                   slug: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        获取事件列表
        
        Args:
            active: 是否只返回活跃事件
            closed: 是否只返回已关闭事件
            limit: 返回结果数量限制
            offset: 偏移量
            order: 排序方向 (asc/desc)
            order_by: 排序字段
            slug: 事件slug筛选
            
        Returns:
            事件列表或None
        """
        try:
            url = f"{self.base_url}/events"
            params = {}
            
            if active is not None:
                params['active'] = str(active).lower()
            if closed is not None:
                params['closed'] = str(closed).lower()
            if limit is not None:
                params['limit'] = limit
            if offset is not None:
                params['offset'] = offset
            if order:
                params['order'] = order
            if order_by:
                params['order_by'] = order_by
            if slug:
                params['slug'] = slug
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events_data = response.json()
            
            logger.info(f"成功获取 {len(events_data)} 个事件")
            
            # 保存数据到CSV
            if self.save_data and events_data:
                self._save_to_csv(events_data, "events_list.csv")
            
            return events_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取事件列表失败: {e}")
            return None
    
    def get_event_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        根据slug获取特定事件
        
        Args:
            slug: 事件slug
            
        Returns:
            事件数据或None
        """
        try:
            url = f"{self.base_url}/events/{slug}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            event_data = response.json()
            logger.info(f"成功获取事件: {slug}")
            
            # 保存数据到CSV
            if self.save_data and event_data:
                self._save_to_csv([event_data], f"event_{event_slug}.csv")
            
            return event_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取事件详情失败: {e}")
            return None
    
    def get_markets(self,
                   active: Optional[bool] = None,
                   closed: Optional[bool] = None,
                   limit: Optional[int] = None,
                   offset: Optional[int] = None,
                   order: Optional[str] = None,
                   order_by: Optional[str] = None,
                   event_slug: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        获取市场列表
        
        Args:
            active: 是否只返回活跃市场
            closed: 是否只返回已关闭市场
            limit: 返回结果数量限制
            offset: 偏移量
            order: 排序方向 (asc/desc)
            order_by: 排序字段
            event_slug: 事件slug筛选
            
        Returns:
            市场列表或None
        """
        try:
            url = f"{self.base_url}/markets"
            params = {}
            
            if active is not None:
                params['active'] = str(active).lower()
            if closed is not None:
                params['closed'] = str(closed).lower()
            if limit is not None:
                params['limit'] = limit
            if offset is not None:
                params['offset'] = offset
            if order:
                params['order'] = order
            if order_by:
                params['order_by'] = order_by
            if event_slug:
                params['event_slug'] = event_slug
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            markets_data = response.json()
            
            logger.info(f"成功获取 {len(markets_data)} 个市场")
            
            # 保存数据到CSV
            if self.save_data and markets_data:
                self._save_to_csv(markets_data, "markets_list.csv")
            
            return markets_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场列表失败: {e}")
            return None
    
    def get_market_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        根据slug获取特定市场
        
        Args:
            slug: 市场slug
            
        Returns:
            市场数据或None
        """
        try:
            url = f"{self.base_url}/markets/{slug}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            market_data = response.json()
            logger.info(f"成功获取市场: {slug}")
            
            # 保存数据到CSV
            if self.save_data and market_data:
                self._save_to_csv([market_data], f"market_{market_slug}.csv")
            
            return market_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场详情失败: {e}")
            return None
    
    def search_events(self, query: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        搜索事件
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            搜索结果列表或None
        """
        try:
            url = f"{self.base_url}/search"
            params = {
                'query': query,
                'limit': limit,
                'type': 'events'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            search_results = response.json()
            
            logger.info(f"搜索 '{query}' 找到 {len(search_results)} 个结果")
            
            return search_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索事件失败: {e}")
            return None
    
    def get_trending_events(self, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        获取热门事件
        
        Args:
            limit: 返回结果数量限制
            
        Returns:
            热门事件列表或None
        """
        return self.get_events(active=True, closed=False, limit=limit, order_by='volume', order='desc')
    
    def get_active_events(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取活跃事件 (基于你提供的API端点)
        
        Args:
            limit: 返回结果数量限制
            
        Returns:
            活跃事件列表或None
        """
        return self.get_events(active=True, closed=False, limit=limit)
    
    def get_event_markets(self, event_slug: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取特定事件的所有市场
        
        Args:
            event_slug: 事件slug
            
        Returns:
            市场列表或None
        """
        return self.get_markets(event_slug=event_slug, active=True)
    
    def get_market_statistics(self, market_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取市场统计信息
        
        Args:
            market_slug: 市场slug
            
        Returns:
            统计信息或None
        """
        try:
            url = f"{self.base_url}/markets/{market_slug}/stats"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            stats_data = response.json()
            logger.info(f"成功获取市场统计: {market_slug}")
            
            return stats_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场统计失败: {e}")
            return None
    
    def get_market_history(self, market_slug: str, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        获取市场历史数据
        
        Args:
            market_slug: 市场slug
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            历史数据列表或None
        """
        try:
            url = f"{self.base_url}/markets/{market_slug}/history"
            params = {}
            
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            history_data = response.json()
            logger.info(f"成功获取市场历史: {market_slug}")
            
            # 保存数据到CSV
            if self.save_data and history_data:
                self._save_to_csv(history_data, f"history_{market_slug}.csv")
            
            return history_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场历史失败: {e}")
            return None
    
    def get_categories(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取事件分类
        
        Returns:
            分类列表或None
        """
        try:
            url = f"{self.base_url}/categories"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            categories_data = response.json()
            logger.info(f"成功获取 {len(categories_data)} 个分类")
            
            # 保存数据到CSV
            if self.save_data and categories_data:
                self._save_to_csv(categories_data, "categories_list.csv")
            
            return categories_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取分类失败: {e}")
            return None
    
    def get_events_by_category(self, category: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        根据分类获取事件
        
        Args:
            category: 分类名称
            limit: 返回结果数量限制
            
        Returns:
            事件列表或None
        """
        try:
            url = f"{self.base_url}/categories/{category}/events"
            params = {'limit': limit}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events_data = response.json()
            logger.info(f"成功获取分类 '{category}' 下的 {len(events_data)} 个事件")
            
            return events_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取分类事件失败: {e}")
            return None
    
    def get_high_volume_markets(self, min_volume: float = 1000, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        获取高交易量市场
        
        Args:
            min_volume: 最小交易量
            limit: 返回结果数量限制
            
        Returns:
            高交易量市场列表或None
        """
        markets = self.get_markets(active=True, limit=100, order_by='volume', order='desc')
        
        if not markets:
            return None
        
        # 筛选高交易量市场
        high_volume_markets = []
        for market in markets:
            volume = market.get('volume', 0)
            if isinstance(volume, (int, float)) and volume >= min_volume:
                high_volume_markets.append(market)
            
            if len(high_volume_markets) >= limit:
                break
        
        logger.info(f"找到 {len(high_volume_markets)} 个高交易量市场")
        return high_volume_markets
    
    def get_near_expiry_markets(self, days: int = 7, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        获取即将到期的市场
        
        Args:
            days: 天数范围
            limit: 返回结果数量限制
            
        Returns:
            即将到期市场列表或None
        """
        markets = self.get_markets(active=True, limit=100)
        
        if not markets:
            return None
        
        from datetime import datetime, timedelta
        
        near_expiry_markets = []
        cutoff_date = datetime.now() + timedelta(days=days)
        
        for market in markets:
            end_date_str = market.get('end_date_iso') or market.get('end_date')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    if end_date <= cutoff_date:
                        near_expiry_markets.append(market)
                except ValueError:
                    continue
            
            if len(near_expiry_markets) >= limit:
                break
        
        logger.info(f"找到 {len(near_expiry_markets)} 个即将到期的市场")
        return near_expiry_markets
    
    def get_market_summary(self, market_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取市场摘要信息
        
        Args:
            market_slug: 市场slug
            
        Returns:
            市场摘要或None
        """
        market_detail = self.get_market_by_slug(market_slug)
        if not market_detail:
            return None
        
        market_stats = self.get_market_statistics(market_slug)
        
        summary = {
            'market': market_detail,
            'statistics': market_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def monitor_events(self, callback_func=None, interval: int = 60):
        """
        监控事件变化
        
        Args:
            callback_func: 回调函数，接收事件数据
            interval: 监控间隔(秒)
        """
        import time
        
        logger.info(f"开始监控事件，间隔 {interval} 秒")
        
        last_events = set()
        
        while True:
            try:
                current_events = self.get_active_events(limit=100)
                
                if current_events:
                    current_event_ids = {event.get('id') or event.get('slug') for event in current_events}
                    
                    # 检测新事件
                    new_events = current_event_ids - last_events
                    if new_events and callback_func:
                        new_event_data = [e for e in current_events if (e.get('id') or e.get('slug')) in new_events]
                        callback_func(new_event_data)
                    
                    last_events = current_event_ids
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                time.sleep(10)

def main():
    """测试函数"""
    client = PolymarketMarketClient(save_data=True)
    
    print("🔍 测试Polymarket Market API客户端")
    print("=" * 50)
    
    # 测试获取活跃事件 (基于你提供的API)
    print("\n1. 获取活跃事件 (active=true&closed=false&limit=5):")
    events = client.get_active_events(limit=5)
    if events:
        print(f"✅ 成功获取 {len(events)} 个活跃事件")
        for i, event in enumerate(events[:3], 1):
            title = event.get('title') or event.get('name', 'N/A')
            slug = event.get('slug', 'N/A')
            print(f"  {i}. {title[:50]}...")
            print(f"     Slug: {slug}")
    else:
        print("❌ 获取活跃事件失败")
    
    # 测试获取市场
    print("\n2. 获取活跃市场:")
    markets = client.get_markets(active=True, closed=False, limit=5)
    if markets:
        print(f"✅ 成功获取 {len(markets)} 个市场")
        for i, market in enumerate(markets[:3], 1):
            question = market.get('question') or market.get('title', 'N/A')
            slug = market.get('slug', 'N/A')
            print(f"  {i}. {question[:50]}...")
            print(f"     Slug: {slug}")
    else:
        print("❌ 获取市场失败")
    
    # 测试搜索功能
    print("\n3. 搜索事件:")
    search_results = client.search_events("election", limit=3)
    if search_results:
        print(f"✅ 搜索到 {len(search_results)} 个结果")
        for i, result in enumerate(search_results[:2], 1):
            title = result.get('title') or result.get('name', 'N/A')
            print(f"  {i}. {title[:50]}...")
    else:
        print("❌ 搜索失败")
    
    # 测试获取分类
    print("\n4. 获取分类:")
    categories = client.get_categories()
    if categories:
        print(f"✅ 成功获取 {len(categories)} 个分类")
        for i, category in enumerate(categories[:3], 1):
            name = category.get('name', 'N/A')
            print(f"  {i}. {name}")
    else:
        print("❌ 获取分类失败")
    
    print(f"\n📁 数据已保存到 ./data/ 目录")

if __name__ == "__main__":
    main()