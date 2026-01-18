#!/usr/bin/env python3
"""
Polymarket 市场同步器
同步所有活跃事件，按照GET /tags进行分类，并根据tag分组保存在/data/tag目录下
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from collections import defaultdict
import pandas as pd
from core.polymarket_market_client import PolymarketMarketClient

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polymarket_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PolymarketSynchronizer:
    """Polymarket市场同步器"""
    
    def __init__(self, 
                 base_url: str = "https://gamma-api.polymarket.com",
                 data_dir: str = "./data",
                 use_mock_data: bool = False):
        
        self.client = PolymarketMarketClient(base_url=base_url, save_data=False)
        self.data_dir = data_dir
        self.tag_dir = os.path.join(data_dir, "tag")
        self.use_mock_data = use_mock_data
        
        # 创建目录结构
        self.ensure_directories()
        
        # 统计信息
        self.sync_stats = {
            'total_events': 0,
            'total_markets': 0,
            'total_tags': 0,
            'events_by_tag': defaultdict(int),
            'markets_by_tag': defaultdict(int),
            'sync_start_time': None,
            'sync_end_time': None
        }
    
    def ensure_directories(self):
        """确保目录结构存在"""
        directories = [
            self.data_dir,
            self.tag_dir,
            os.path.join(self.data_dir, "sync_logs"),
            os.path.join(self.data_dir, "reports")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"确保目录存在: {directory}")
    
    def get_all_tags(self) -> List[Dict]:
        """获取所有标签 - GET /tags"""
        logger.info("获取所有标签...")
        
        if self.use_mock_data:
            return self.get_mock_tags()
        
        try:
            # 尝试获取标签端点
            url = f"{self.client.base_url}/tags"
            response = self.client.session.get(url, timeout=10)
            
            if response.status_code == 200:
                tags_data = response.json()
                logger.info(f"成功获取 {len(tags_data)} 个标签")
                return tags_data
            else:
                logger.warning(f"获取标签失败，状态码: {response.status_code}")
                return self.get_mock_tags()
                
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return self.get_mock_tags()
    
    def get_mock_tags(self) -> List[Dict]:
        """获取模拟标签数据"""
        return [
            {"id": "politics", "name": "Politics", "slug": "politics", "description": "Political events and elections"},
            {"id": "crypto", "name": "Crypto", "slug": "crypto", "description": "Cryptocurrency and blockchain"},
            {"id": "sports", "name": "Sports", "slug": "sports", "description": "Sports events and competitions"},
            {"id": "economics", "name": "Economics", "slug": "economics", "description": "Economic indicators and markets"},
            {"id": "technology", "name": "Technology", "slug": "technology", "description": "Technology and innovation"},
            {"id": "entertainment", "name": "Entertainment", "slug": "entertainment", "description": "Entertainment and media"},
            {"id": "science", "name": "Science", "slug": "science", "description": "Scientific discoveries and research"},
            {"id": "weather", "name": "Weather", "slug": "weather", "description": "Weather and climate events"},
            {"id": "business", "name": "Business", "slug": "business", "description": "Business and corporate events"},
            {"id": "social", "name": "Social", "slug": "social", "description": "Social trends and phenomena"}
        ]
    
    def get_all_active_events(self) -> List[Dict]:
        """获取所有活跃事件"""
        logger.info("获取所有活跃事件...")
        
        if self.use_mock_data:
            return self.get_mock_events()
        
        all_events = []
        offset = 0
        limit = 100
        
        while True:
            try:
                # 获取一批事件
                events = self.client.get_events(
                    active=True, 
                    closed=False, 
                    limit=limit, 
                    offset=offset
                )
                
                if not events or len(events) == 0:
                    break
                
                all_events.extend(events)
                logger.info(f"已获取 {len(all_events)} 个事件...")
                
                # 如果返回的事件数量少于limit，说明已经到最后一页
                if len(events) < limit:
                    break
                
                offset += limit
                time.sleep(0.5)  # 避免请求过于频繁
                
            except Exception as e:
                logger.error(f"获取事件失败 (offset={offset}): {e}")
                break
        
        logger.info(f"总共获取到 {len(all_events)} 个活跃事件")
        return all_events
    
    def get_mock_events(self) -> List[Dict]:
        """获取模拟事件数据"""
        return [
            {
                "id": "event_001",
                "slug": "2024-us-presidential-election",
                "title": "2024 US Presidential Election",
                "description": "Who will win the 2024 United States Presidential Election?",
                "active": True,
                "closed": False,
                "tags": ["politics", "elections", "usa"],
                "category": "Politics",
                "volume": 15000000,
                "liquidity": 2500000,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-11-05T23:59:59Z"
            },
            {
                "id": "event_002",
                "slug": "bitcoin-price-100k-2024",
                "title": "Bitcoin Price $100K in 2024",
                "description": "Will Bitcoin reach $100,000 by the end of 2024?",
                "active": True,
                "closed": False,
                "tags": ["crypto", "bitcoin", "price"],
                "category": "Crypto",
                "volume": 8000000,
                "liquidity": 1200000,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            },
            {
                "id": "event_003",
                "slug": "super-bowl-2025-winner",
                "title": "Super Bowl 2025 Winner",
                "description": "Which team will win Super Bowl LIX?",
                "active": True,
                "closed": False,
                "tags": ["sports", "nfl", "football"],
                "category": "Sports",
                "volume": 5000000,
                "liquidity": 800000,
                "start_date": "2024-09-01T00:00:00Z",
                "end_date": "2025-02-09T23:59:59Z"
            },
            {
                "id": "event_004",
                "slug": "fed-rate-cut-2024",
                "title": "Federal Reserve Rate Cut 2024",
                "description": "Will the Federal Reserve cut interest rates in 2024?",
                "active": True,
                "closed": False,
                "tags": ["economics", "fed", "interest-rates"],
                "category": "Economics",
                "volume": 3000000,
                "liquidity": 500000,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            },
            {
                "id": "event_005",
                "slug": "ai-breakthrough-2024",
                "title": "Major AI Breakthrough 2024",
                "description": "Will there be a major AI breakthrough announced in 2024?",
                "active": True,
                "closed": False,
                "tags": ["technology", "ai", "innovation"],
                "category": "Technology",
                "volume": 2000000,
                "liquidity": 300000,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            }
        ]
    
    def get_markets_for_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """获取事件对应的市场"""
        logger.info("获取事件对应的市场...")
        
        event_markets = {}
        
        for i, event in enumerate(events):
            event_slug = event.get('slug')
            if not event_slug:
                continue
            
            try:
                # 获取事件的市场
                markets = self.client.get_event_markets(event_slug)
                if markets:
                    event_markets[event_slug] = markets
                    logger.info(f"事件 {event_slug} 有 {len(markets)} 个市场")
                else:
                    event_markets[event_slug] = []
                
                # 进度显示
                if (i + 1) % 10 == 0:
                    logger.info(f"已处理 {i + 1}/{len(events)} 个事件")
                
                time.sleep(0.2)  # 避免请求过于频繁
                
            except Exception as e:
                logger.error(f"获取事件 {event_slug} 的市场失败: {e}")
                event_markets[event_slug] = []
        
        total_markets = sum(len(markets) for markets in event_markets.values())
        logger.info(f"总共获取到 {total_markets} 个市场")
        
        return event_markets
    
    def categorize_by_tags(self, events: List[Dict], event_markets: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """按标签分类事件和市场"""
        logger.info("按标签分类事件和市场...")
        
        tag_data = defaultdict(lambda: {
            'events': [],
            'markets': [],
            'tag_info': None
        })
        
        # 处理每个事件
        for event in events:
            event_tags = event.get('tags', [])
            event_slug = event.get('slug', '')
            
            # 确保tags是列表格式
            if isinstance(event_tags, str):
                event_tags = [event_tags]
            elif not isinstance(event_tags, list):
                event_tags = []
            
            # 如果没有标签，归类到"uncategorized"
            if not event_tags:
                event_tags = ['uncategorized']
            
            # 为每个标签添加事件
            for tag in event_tags:
                tag_slug = str(tag).lower().replace(' ', '-')
                tag_data[tag_slug]['events'].append(event)
                
                # 添加对应的市场
                markets = event_markets.get(event_slug, [])
                tag_data[tag_slug]['markets'].extend(markets)
        
        logger.info(f"按 {len(tag_data)} 个标签分类完成")
        return dict(tag_data)
    
    def save_tag_data(self, tag_slug: str, tag_data: Dict):
        """保存单个标签的数据"""
        tag_directory = os.path.join(self.tag_dir, tag_slug)
        os.makedirs(tag_directory, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存事件数据
        events = tag_data['events']
        if events:
            events_df = pd.DataFrame([
                {
                    'id': event.get('id', ''),
                    'slug': event.get('slug', ''),
                    'title': event.get('title', ''),
                    'description': event.get('description', ''),
                    'active': event.get('active', False),
                    'closed': event.get('closed', False),
                    'category': event.get('category', ''),
                    'tags': ','.join([str(t) for t in event.get('tags', [])]),
                    'volume': event.get('volume', 0),
                    'liquidity': event.get('liquidity', 0),
                    'start_date': event.get('start_date', ''),
                    'end_date': event.get('end_date', ''),
                    'sync_timestamp': datetime.now().isoformat()
                }
                for event in events
            ])
            
            events_file = os.path.join(tag_directory, f"events_{timestamp}.csv")
            events_df.to_csv(events_file, index=False, encoding='utf-8')
            logger.info(f"保存 {len(events)} 个事件到: {events_file}")
        
        # 保存市场数据
        markets = tag_data['markets']
        if markets:
            markets_df = pd.DataFrame([
                {
                    'id': market.get('id', ''),
                    'slug': market.get('slug', ''),
                    'question': market.get('question', ''),
                    'description': market.get('description', ''),
                    'event_slug': market.get('event_slug', ''),
                    'active': market.get('active', False),
                    'closed': market.get('closed', False),
                    'category': market.get('category', ''),
                    'volume': market.get('volume', 0),
                    'liquidity': market.get('liquidity', 0),
                    'end_date_iso': market.get('end_date_iso', ''),
                    'sync_timestamp': datetime.now().isoformat()
                }
                for market in markets
            ])
            
            markets_file = os.path.join(tag_directory, f"markets_{timestamp}.csv")
            markets_df.to_csv(markets_file, index=False, encoding='utf-8')
            logger.info(f"保存 {len(markets)} 个市场到: {markets_file}")
        
        # 保存标签摘要
        summary = {
            'tag_slug': tag_slug,
            'events_count': len(events),
            'markets_count': len(markets),
            'total_volume': sum(event.get('volume', 0) for event in events),
            'total_liquidity': sum(event.get('liquidity', 0) for event in events),
            'sync_timestamp': datetime.now().isoformat(),
            'top_events': [
                {
                    'title': event.get('title', ''),
                    'volume': event.get('volume', 0)
                }
                for event in sorted(events, key=lambda x: x.get('volume', 0), reverse=True)[:5]
            ]
        }
        
        summary_file = os.path.join(tag_directory, f"summary_{timestamp}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"保存标签摘要到: {summary_file}")
        
        return {
            'events_file': events_file if events else None,
            'markets_file': markets_file if markets else None,
            'summary_file': summary_file
        }
    
    def generate_sync_report(self, categorized_data: Dict[str, Dict]) -> str:
        """生成同步报告"""
        report_data = {
            'sync_info': {
                'start_time': self.sync_stats['sync_start_time'],
                'end_time': self.sync_stats['sync_end_time'],
                'duration_seconds': (
                    datetime.fromisoformat(self.sync_stats['sync_end_time']) - 
                    datetime.fromisoformat(self.sync_stats['sync_start_time'])
                ).total_seconds() if self.sync_stats['sync_end_time'] else 0,
                'total_events': self.sync_stats['total_events'],
                'total_markets': self.sync_stats['total_markets'],
                'total_tags': len(categorized_data)
            },
            'tag_statistics': {},
            'top_tags_by_events': [],
            'top_tags_by_volume': []
        }
        
        # 统计每个标签
        tag_stats = []
        for tag_slug, tag_data in categorized_data.items():
            events = tag_data['events']
            markets = tag_data['markets']
            
            total_volume = sum(event.get('volume', 0) for event in events)
            total_liquidity = sum(event.get('liquidity', 0) for event in events)
            
            stat = {
                'tag': tag_slug,
                'events_count': len(events),
                'markets_count': len(markets),
                'total_volume': total_volume,
                'total_liquidity': total_liquidity
            }
            
            tag_stats.append(stat)
            report_data['tag_statistics'][tag_slug] = stat
        
        # 排序统计
        report_data['top_tags_by_events'] = sorted(
            tag_stats, key=lambda x: x['events_count'], reverse=True
        )[:10]
        
        report_data['top_tags_by_volume'] = sorted(
            tag_stats, key=lambda x: x['total_volume'], reverse=True
        )[:10]
        
        # 保存报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.data_dir, "reports", f"sync_report_{timestamp}.json")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"同步报告已保存到: {report_file}")
        
        # 生成文本报告
        text_report = self.generate_text_report(report_data)
        text_report_file = os.path.join(self.data_dir, "reports", f"sync_report_{timestamp}.txt")
        
        with open(text_report_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        logger.info(f"文本报告已保存到: {text_report_file}")
        
        return text_report
    
    def generate_text_report(self, report_data: Dict) -> str:
        """生成文本格式的报告"""
        sync_info = report_data['sync_info']
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    Polymarket 同步报告                       ║
╠══════════════════════════════════════════════════════════════╣
║ 📊 同步统计                                                  ║
║   开始时间: {sync_info['start_time']}                        ║
║   结束时间: {sync_info['end_time']}                          ║
║   耗时: {sync_info['duration_seconds']:.1f} 秒               ║
║   总事件数: {sync_info['total_events']:,}                   ║
║   总市场数: {sync_info['total_markets']:,}                  ║
║   标签数量: {sync_info['total_tags']}                       ║
║                                                              ║
║ 🏷️  热门标签 (按事件数)                                      ║"""
        
        for i, tag_stat in enumerate(report_data['top_tags_by_events'][:5], 1):
            report += f"""
║   {i}. {tag_stat['tag']}: {tag_stat['events_count']} 个事件   ║"""
        
        report += f"""
║                                                              ║
║ 💰 热门标签 (按交易量)                                       ║"""
        
        for i, tag_stat in enumerate(report_data['top_tags_by_volume'][:5], 1):
            volume_str = f"${tag_stat['total_volume']:,}"
            report += f"""
║   {i}. {tag_stat['tag']}: {volume_str}                       ║"""
        
        report += f"""
╚══════════════════════════════════════════════════════════════╝
        """
        
        return report.strip()
    
    def sync_all_markets(self) -> str:
        """同步所有市场的主方法"""
        logger.info("开始同步Polymarket所有活跃市场...")
        self.sync_stats['sync_start_time'] = datetime.now().isoformat()
        
        try:
            # 1. 获取所有标签
            tags = self.get_all_tags()
            self.sync_stats['total_tags'] = len(tags)
            
            # 2. 获取所有活跃事件
            events = self.get_all_active_events()
            self.sync_stats['total_events'] = len(events)
            
            if not events:
                logger.warning("没有获取到活跃事件")
                return "同步失败: 没有获取到活跃事件"
            
            # 3. 获取事件对应的市场
            event_markets = self.get_markets_for_events(events)
            total_markets = sum(len(markets) for markets in event_markets.values())
            self.sync_stats['total_markets'] = total_markets
            
            # 4. 按标签分类
            categorized_data = self.categorize_by_tags(events, event_markets)
            
            # 5. 保存分类数据
            logger.info("保存分类数据到各个标签目录...")
            saved_files = {}
            
            for tag_slug, tag_data in categorized_data.items():
                try:
                    files = self.save_tag_data(tag_slug, tag_data)
                    saved_files[tag_slug] = files
                    
                    # 更新统计
                    self.sync_stats['events_by_tag'][tag_slug] = len(tag_data['events'])
                    self.sync_stats['markets_by_tag'][tag_slug] = len(tag_data['markets'])
                    
                except Exception as e:
                    logger.error(f"保存标签 {tag_slug} 数据失败: {e}")
            
            # 6. 生成同步报告
            self.sync_stats['sync_end_time'] = datetime.now().isoformat()
            report = self.generate_sync_report(categorized_data)
            
            logger.info("同步完成!")
            print(report)
            
            return report
            
        except Exception as e:
            logger.error(f"同步过程中发生错误: {e}")
            self.sync_stats['sync_end_time'] = datetime.now().isoformat()
            return f"同步失败: {e}"
    
    def cleanup_old_files(self, days: int = 7):
        """清理旧的同步文件"""
        logger.info(f"清理 {days} 天前的旧文件...")
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        cleaned_count = 0
        
        # 清理标签目录下的旧文件
        for tag_dir in os.listdir(self.tag_dir):
            tag_path = os.path.join(self.tag_dir, tag_dir)
            if os.path.isdir(tag_path):
                for filename in os.listdir(tag_path):
                    file_path = os.path.join(tag_path, filename)
                    if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
        
        # 清理报告目录下的旧文件
        reports_dir = os.path.join(self.data_dir, "reports")
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                file_path = os.path.join(reports_dir, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
        
        logger.info(f"清理完成，删除了 {cleaned_count} 个旧文件")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Polymarket市场同步器')
    parser.add_argument('--mock', action='store_true', help='使用模拟数据')
    parser.add_argument('--cleanup', type=int, help='清理N天前的旧文件')
    parser.add_argument('--data-dir', default='./data', help='数据目录路径')
    
    args = parser.parse_args()
    
    # 创建同步器
    synchronizer = PolymarketSynchronizer(
        data_dir=args.data_dir,
        use_mock_data=args.mock
    )
    
    if args.cleanup:
        # 清理旧文件
        synchronizer.cleanup_old_files(days=args.cleanup)
    else:
        # 执行同步
        if args.mock:
            print("🔧 使用模拟数据进行同步演示")
        
        report = synchronizer.sync_all_markets()
        
        print(f"\n📁 数据已保存到目录结构:")
        print(f"  {args.data_dir}/tag/[tag_name]/events_*.csv")
        print(f"  {args.data_dir}/tag/[tag_name]/markets_*.csv")
        print(f"  {args.data_dir}/tag/[tag_name]/summary_*.json")
        print(f"  {args.data_dir}/reports/sync_report_*.json")

if __name__ == "__main__":
    main()