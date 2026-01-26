#!/usr/bin/env python3
"""
市场搜索工具 - 通过关键词搜索Polymarket市场
使用公共搜索API: https://gamma-api.polymarket.com/public-search
"""

import json
import os
import csv
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from dateutil import parser as date_parser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketSearcher:
    def __init__(self, data_dir: str = "./data", max_retries: int = 3):
        self.data_dir = data_dir
        self.max_retries = max_retries
        
        # 标准请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://polymarket.com/"
        }
        
        # 确保目录存在
        for subdir in ["markets", "search_logs", "reports"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

    def make_api_request(self, url: str, params: Optional[Dict] = None, timeout: int = 30) -> Optional[Dict]:
        """
        发送API请求，包含重试机制和错误处理
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=timeout)
                
                # 处理不同的HTTP状态码
                if response.status_code == 500:
                    logger.warning(f"服务器错误 (500) - 第{attempt + 1}次重试，等待5秒...")
                    time.sleep(5)
                    continue
                elif response.status_code == 429:
                    logger.warning(f"请求限制 (429) - 第{attempt + 1}次重试，等待10秒...")
                    time.sleep(10)
                    continue
                elif response.status_code == 404:
                    logger.warning(f"资源未找到 (404): {url}")
                    return None
                elif response.status_code != 200:
                    logger.error(f"API错误 {response.status_code}: {response.text[:200]}")
                    if attempt < self.max_retries - 1:
                        logger.info(f"第{attempt + 1}次重试，等待3秒...")
                        time.sleep(3)
                        continue
                    else:
                        return None
                
                # 尝试解析JSON
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    if response.text.strip():
                        logger.error(f"响应内容: {response.text[:500]}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"网络错误 (第{attempt + 1}次): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return None
            except Exception as e:
                logger.error(f"意外错误 (第{attempt + 1}次): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    return None
        
        return None

    def filter_active_markets(self, markets: List[Dict]) -> List[Dict]:
        """
        过滤出活跃的、未结束的市场
        
        Args:
            markets: 原始市场列表
            
        Returns:
            List[Dict]: 过滤后的活跃市场列表
        """
        active_markets = []
        current_time = datetime.now()
        
        for market in markets:
            # 检查市场是否已关闭
            if market.get('closed', False):
                continue
            
            # 检查市场是否活跃
            if not market.get('active', True):
                continue
            
            # 检查结束时间
            end_date = market.get('endDate', '')
            if end_date:
                try:
                    end_time = date_parser.parse(end_date)
                    current_time_tz = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                    
                    # 如果市场已经过期，跳过
                    if end_time <= current_time_tz:
                        continue
                except:
                    # 如果无法解析时间，保留市场（可能是永久市场）
                    pass
            
            active_markets.append(market)
        
        return active_markets

    def search_markets(self, query: str, limit: int = 100, active_only: bool = True) -> List[Dict]:
        """
        通过关键词搜索市场
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            active_only: 是否只返回活跃市场
            
        Returns:
            List[Dict]: 匹配的市场列表
        """
        base_url = "https://gamma-api.polymarket.com/public-search"
        
        logger.info(f"🔍 搜索关键词 '{query}' 的市场...")
        
        # 增加搜索限制以获得更多结果，然后过滤
        search_limit = limit * 3 if active_only else limit
        
        params = {
            'q': query,
            'limit': search_limit
        }
        
        data = self.make_api_request(base_url, params)
        
        if not data:
            logger.warning(f"无法获取关键词 '{query}' 的搜索结果")
            return []
        
        # 检查响应结构
        if isinstance(data, dict):
            markets = data.get('events', [])  # 使用 'events' 而不是 'markets'
            if not markets:
                # 尝试其他可能的字段名
                markets = data.get('markets', [])
                if not markets:
                    markets = data.get('data', [])
                    if not markets:
                        markets = data.get('results', [])
        elif isinstance(data, list):
            markets = data
        else:
            logger.error(f"意外的响应格式: {type(data)}")
            return []
        
        original_count = len(markets)
        
        # 如果只要活跃市场，进行过滤
        if active_only:
            markets = self.filter_active_markets(markets)
            logger.info(f"🔄 过滤后剩余 {len(markets)} 个活跃市场（原始: {original_count} 个）")
            
            # 限制返回数量
            markets = markets[:limit]
        
        logger.info(f"✅ 关键词 '{query}' 搜索完成: 找到 {len(markets)} 个市场")
        return markets

    def save_markets_data(self, markets: List[Dict], keyword: str) -> str:
        """
        保存市场数据到CSV文件
        
        Args:
            markets: 市场列表
            keyword: 搜索关键词（用于文件命名）
            
        Returns:
            str: 保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in ('-', '_')).lower()
        filename = f"{safe_keyword}_markets_{timestamp}.csv"
        full_path = os.path.join(self.data_dir, "markets", filename)
        
        # CSV标题
        headers = [
            'id', 'question', 'slug', 'category', 'tags', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest', 'createdAt', 'updatedAt',
            'description', 'image', 'icon', 'enableOrderBook', 'marketMakerAddress',
            'funded', 'groupItemTitle', 'groupItemThreshold'
        ]
        
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for market in markets:
                try:
                    # 处理JSON字段
                    def safe_json_field(field_value):
                        """安全处理JSON字段，转换为字符串"""
                        if isinstance(field_value, (list, dict)):
                            return json.dumps(field_value, ensure_ascii=False)
                        elif isinstance(field_value, str):
                            return field_value
                        else:
                            return str(field_value) if field_value is not None else ''
                    
                    # 创建数据行
                    row = [
                        market.get('id', ''),
                        market.get('title', market.get('question', '')),  # 优先使用title字段
                        market.get('slug', ''),
                        market.get('category', ''),
                        safe_json_field(market.get('tags', '')),
                        safe_json_field(market.get('clobTokenIds', '')),
                        safe_json_field(market.get('outcomes', '')),
                        safe_json_field(market.get('outcomePrices', '')),
                        market.get('conditionId', ''),
                        market.get('active', ''),
                        market.get('closed', ''),
                        market.get('volumeNum', ''),
                        market.get('volume24hr', ''),
                        market.get('liquidity', ''),
                        market.get('liquidityNum', ''),
                        market.get('endDate', ''),
                        market.get('orderPriceMinTickSize', ''),
                        market.get('orderMinSize', ''),
                        market.get('resolutionSource', ''),
                        market.get('acceptingOrders', ''),
                        market.get('openInterest', ''),
                        market.get('createdAt', ''),
                        market.get('updatedAt', ''),
                        market.get('description', ''),
                        market.get('image', ''),
                        market.get('icon', ''),
                        market.get('enableOrderBook', ''),
                        market.get('marketMakerAddress', ''),
                        market.get('funded', ''),
                        market.get('groupItemTitle', ''),
                        market.get('groupItemThreshold', '')
                    ]
                    
                    writer.writerow(row)
                    
                except Exception as e:
                    logger.error(f"处理市场 {market.get('id', 'unknown')} 时出错: {e}")
                    continue
        
        logger.info(f"💾 市场数据已保存到: {full_path}")
        return full_path

    def generate_search_report(self, markets: List[Dict], keyword: str) -> Dict[str, Any]:
        """
        生成搜索报告
        
        Args:
            markets: 市场列表
            keyword: 搜索关键词
            
        Returns:
            Dict: 报告数据
        """
        current_time = datetime.now()
        
        # 按交易量排序
        sorted_markets = sorted(markets, key=lambda x: float(x.get('volumeNum', 0) or 0), reverse=True)
        
        # 统计信息
        total_volume = 0
        total_liquidity = 0
        categories = {}
        active_count = 0
        closed_count = 0
        
        for market in markets:
            # 统计交易量
            try:
                volume = float(market.get('volumeNum', 0) or 0)
                total_volume += volume
            except:
                pass
                
            # 统计流动性
            try:
                liquidity = float(market.get('liquidityNum', 0) or 0)
                total_liquidity += liquidity
            except:
                pass
                
            # 统计分类
            category = market.get('category', 'Unknown')
            if category:
                categories[category] = categories.get(category, 0) + 1
            
            # 统计状态
            if market.get('active'):
                active_count += 1
            if market.get('closed'):
                closed_count += 1
        
        # 时间分析
        time_ranges = {
            '1天内': 0, '1周内': 0, '1月内': 0, '3月内': 0, '6月内': 0, '1年内': 0, '1年以上': 0
        }
        
        for market in markets:
            end_date = market.get('endDate', '')
            if end_date:
                try:
                    end_time = date_parser.parse(end_date)
                    current_time_tz = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                    time_diff = end_time - current_time_tz
                    days = time_diff.days
                    
                    if days <= 1:
                        time_ranges['1天内'] += 1
                    elif days <= 7:
                        time_ranges['1周内'] += 1
                    elif days <= 30:
                        time_ranges['1月内'] += 1
                    elif days <= 90:
                        time_ranges['3月内'] += 1
                    elif days <= 180:
                        time_ranges['6月内'] += 1
                    elif days <= 365:
                        time_ranges['1年内'] += 1
                    else:
                        time_ranges['1年以上'] += 1
                except:
                    pass
        
        report = {
            "timestamp": current_time.isoformat(),
            "keyword": keyword,
            "total_markets": len(markets),
            "active_markets": active_count,
            "closed_markets": closed_count,
            "total_volume": total_volume,
            "total_liquidity": total_liquidity,
            "categories": categories,
            "time_ranges": time_ranges,
            "top_markets": []
        }
        
        # 添加前20个交易量最大的市场
        for i, market in enumerate(sorted_markets[:20]):
            end_date = market.get('endDate', '')
            time_remaining = "Unknown"
            
            if end_date:
                try:
                    end_time = date_parser.parse(end_date)
                    current_time_tz = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                    time_diff = end_time - current_time_tz
                    
                    if time_diff.total_seconds() > 0:
                        days = time_diff.days
                        hours = time_diff.seconds // 3600
                        if days > 0:
                            time_remaining = f"{days}天{hours}小时"
                        else:
                            time_remaining = f"{hours}小时"
                    else:
                        time_remaining = "已过期"
                except:
                    pass
            
            report["top_markets"].append({
                "rank": i + 1,
                "id": market.get('id', ''),
                "question": market.get('title', market.get('question', ''))[:100],  # 优先使用title字段
                "category": market.get('category', ''),
                "endDate": end_date,
                "time_remaining": time_remaining,
                "volume": market.get('volumeNum', 0),
                "liquidity": market.get('liquidityNum', 0),
                "active": market.get('active', False),
                "closed": market.get('closed', False)
            })
        
        return report

    def print_search_summary(self, markets: List[Dict], keyword: str):
        """
        打印搜索摘要
        """
        report = self.generate_search_report(markets, keyword)
        
        print("\n" + "="*80)
        print(f"🔍 市场搜索报告 - '{keyword}'")
        print("="*80)
        print(f"🕐 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 发现市场: {report['total_markets']} 个")
        print(f"✅ 活跃市场: {report['active_markets']} 个")
        print(f"❌ 已关闭: {report['closed_markets']} 个")
        print(f"💰 总交易量: ${report['total_volume']:,.2f}")
        print(f"💧 总流动性: ${report['total_liquidity']:,.2f}")
        
        if report['categories']:
            print(f"\n📊 分类统计:")
            for category, count in sorted(report['categories'].items(), key=lambda x: x[1], reverse=True):
                if category and category != 'Unknown':
                    print(f"   {category}: {count} 个市场")
        
        if report['time_ranges']:
            print(f"\n⏰ 结束时间分布:")
            for time_range, count in report['time_ranges'].items():
                if count > 0:
                    print(f"   {time_range}: {count} 个市场")
        
        if report['top_markets']:
            print(f"\n🔥 交易量最大的市场 (前{min(10, len(report['top_markets']))}个):")
            for market in report['top_markets'][:10]:
                status = "🟢" if market['active'] else "🔴" if market['closed'] else "⚪"
                print(f"   {market['rank']:2d}. {status} [{market['time_remaining']}] {market['question']}")
                print(f"       ID: {market['id']} | 交易量: ${market['volume']:,.0f}")
        
        print("="*80)

    def run_search(self, keyword: str, limit: int = 100, save_to_file: bool = True, active_only: bool = True) -> Dict[str, Any]:
        """
        运行市场搜索
        
        Args:
            keyword: 搜索关键词
            limit: 结果数量限制
            save_to_file: 是否保存到文件
            active_only: 是否只返回活跃市场
            
        Returns:
            Dict: 搜索结果
        """
        start_time = datetime.now()
        logger.info(f"🚀 开始搜索关键词: {keyword}")
        
        try:
            # 搜索市场
            markets = self.search_markets(keyword, limit, active_only)
            
            if not markets:
                return {
                    "success": False,
                    "error": f"未找到关键词 '{keyword}' 的{'活跃' if active_only else ''}市场",
                    "markets_count": 0
                }
            
            # 保存到文件
            csv_file = None
            if save_to_file:
                csv_file = self.save_markets_data(markets, keyword)
            
            # 生成报告
            report = self.generate_search_report(markets, keyword)
            
            # 保存JSON报告
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_keyword = "".join(c for c in keyword if c.isalnum() or c in ('-', '_')).lower()
                json_file = os.path.join(self.data_dir, "reports", f"search_report_{safe_keyword}_{timestamp}.json")
                with open(json_file, "w", encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"📊 报告已保存到: {json_file}")
            
            # 打印摘要
            self.print_search_summary(markets, keyword)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "markets_count": len(markets),
                "csv_file": csv_file,
                "duration_seconds": duration,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"市场搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "markets_count": 0
            }

def main():
    parser = argparse.ArgumentParser(description="市场搜索工具 - 通过关键词搜索Polymarket市场")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--limit", type=int, default=100, help="返回结果数量限制")
    parser.add_argument("--include-closed", action="store_true", help="包含已关闭的市场")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件，仅显示结果")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    searcher = MarketSearcher(data_dir=args.data_dir)
    
    result = searcher.run_search(
        keyword=args.keyword,
        limit=args.limit,
        save_to_file=not args.no_save,
        active_only=not args.include_closed
    )
    
    if result["success"]:
        print(f"\n✅ 市场搜索完成!")
        print(f"   发现市场: {result['markets_count']} 个")
        print(f"   耗时: {result['duration_seconds']:.1f} 秒")
        if result.get("csv_file"):
            print(f"   数据文件: {result['csv_file']}")
    else:
        print(f"\n❌ 市场搜索失败: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()