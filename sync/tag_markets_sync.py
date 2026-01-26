#!/usr/bin/env python3
"""
标签市场同步器 - 通用的标签市场搜索和同步工具
支持通过标签ID搜索任何标签下的未关闭市场数据
支持通过关键词搜索 event，然后找到对应的 market
"""

import json
import os
import csv
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from dateutil import parser as date_parser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TagMarketsSync:
    def __init__(self, data_dir: str = "./data", max_retries: int = 5):
        self.data_dir = data_dir
        self.max_retries = max_retries
        
        # 标准请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://polymarket.com/",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
        
        # 确保目录存在
        for subdir in ["tags", "sync_logs", "reports"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)
    
    def check_network_connectivity(self) -> bool:
        """
        检查网络连接性
        """
        try:
            # 尝试连接到一个简单的端点
            response = requests.get("https://httpbin.org/status/200", timeout=10)
            return response.status_code == 200
        except:
            try:
                # 备用检查
                response = requests.get("https://www.google.com", timeout=10)
                return response.status_code == 200
            except:
                return False
    
    def handle_connection_error(self, error: Exception, attempt: int) -> bool:
        """
        处理连接错误并决定是否重试
        
        Returns:
            bool: 是否应该重试
        """
        error_str = str(error).lower()
        
        if "connection reset by peer" in error_str or "connection aborted" in error_str:
            logger.warning(f"🔌 连接被重置 (第{attempt + 1}次尝试)")
            logger.info("💡 这通常是由于:")
            logger.info("   - 网络不稳定")
            logger.info("   - 服务器临时限制")
            logger.info("   - 防火墙或代理设置")
            
            if not self.check_network_connectivity():
                logger.error("❌ 网络连接检查失败，请检查网络设置")
                return False
            else:
                logger.info("✅ 基础网络连接正常，继续重试...")
                return attempt < self.max_retries - 1
        
        elif "timeout" in error_str:
            logger.warning(f"⏱️  请求超时 (第{attempt + 1}次尝试)")
            return attempt < self.max_retries - 1
        
        elif "ssl" in error_str or "certificate" in error_str:
            logger.error("🔒 SSL证书错误，请检查系统时间和证书设置")
            return False
        
    def print_connection_troubleshooting(self):
        """
        打印连接问题的故障排除建议
        """
        print("\n" + "="*60)
        print("🔧 连接问题故障排除建议")
        print("="*60)
        print("1. 🌐 检查网络连接:")
        print("   - 确保互联网连接正常")
        print("   - 尝试访问其他网站确认网络状态")
        print()
        print("2. 🔥 检查防火墙设置:")
        print("   - 确保Python程序可以访问外网")
        print("   - 检查公司/学校网络是否有限制")
        print()
        print("3. 🕐 调整请求参数:")
        print("   - 减少并发请求数量")
        print("   - 增加请求间隔时间")
        print("   - 使用 --debug 参数查看详细日志")
        print()
        print("4. 🔄 重试策略:")
        print("   - 程序会自动重试失败的请求")
        print("   - 可以稍后再次运行程序")
        print("   - 使用 --no-save 参数仅测试连接")
        print()
        print("5. 📞 如果问题持续:")
        print("   - 检查 Polymarket API 服务状态")
        print("   - 尝试使用VPN或更换网络环境")
        print("="*60)

    def run_connection_test(self) -> bool:
        """
        运行连接测试
        """
        print("🔍 开始连接测试...")
        
        # 测试基础网络连接
        print("1. 测试基础网络连接...")
        if self.check_network_connectivity():
            print("   ✅ 基础网络连接正常")
        else:
            print("   ❌ 基础网络连接失败")
            return False
        
        # 测试 Polymarket API 连接
        print("2. 测试 Polymarket API 连接...")
        test_url = "https://gamma-api.polymarket.com/tags"
        result = self.make_api_request(test_url)
        
        if result:
            print("   ✅ Polymarket API 连接成功")
            print(f"   📊 获取到 {len(result) if isinstance(result, list) else 'N/A'} 条数据")
            return True
        else:
            print("   ❌ Polymarket API 连接失败")
            self.print_connection_troubleshooting()
            return False

    def get_available_tags(self) -> List[Dict]:
        """
        获取可用的标签列表
        
        Returns:
            List[Dict]: 标签列表，包含id和name
        """
        url = "https://gamma-api.polymarket.com/tags"
        
        logger.info("🏷️  获取可用标签列表...")
        
        data = self.make_api_request(url)
        
        if not data:
            logger.warning("无法获取标签列表")
            return []
        
        tags = data if isinstance(data, list) else data.get('data', [])
        
        logger.info(f"✅ 获取到 {len(tags)} 个可用标签")
        
        # 打印前20个标签作为示例
        if tags:
            print("\n📋 可用标签示例 (前20个):")
            print("   标签结构示例:", json.dumps(tags[0], indent=2) if tags else "无数据")
            
            for i, tag in enumerate(tags[:20]):
                # 尝试不同的字段名
                tag_id = tag.get('id', tag.get('tagId', 'N/A'))
                tag_name = tag.get('name', tag.get('label', tag.get('title', tag.get('slug', 'N/A'))))
                tag_count = tag.get('count', tag.get('marketCount', ''))
                
                count_str = f" ({tag_count} 市场)" if tag_count else ""
                print(f"   {i+1:2d}. ID: {tag_id:<20} 名称: {tag_name}{count_str}")
            
            if len(tags) > 20:
                print(f"   ... 还有 {len(tags) - 20} 个标签")
        
        return tags

    def save_tags_to_file(self, tags: List[Dict]) -> str:
        """
        将标签列表保存到文件
        
        Args:
            tags: 标签列表
            
        Returns:
            str: 保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存为CSV格式
        csv_filename = f"available_tags_{timestamp}.csv"
        csv_path = os.path.join(self.data_dir, "tags", csv_filename)
        
        # CSV标题
        csv_headers = ['id', 'label', 'slug', 'createdAt', 'updatedAt', 'requiresTranslation']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_headers)
            
            for tag in tags:
                row = [
                    tag.get('id', ''),
                    tag.get('label', ''),
                    tag.get('slug', ''),
                    tag.get('createdAt', ''),
                    tag.get('updatedAt', ''),
                    tag.get('requiresTranslation', '')
                ]
                writer.writerow(row)
        
        logger.info(f"💾 标签CSV数据已保存到: {csv_path}")
        
        # 保存为JSON格式
        json_filename = f"available_tags_{timestamp}.json"
        json_path = os.path.join(self.data_dir, "tags", json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(tags, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 标签JSON数据已保存到: {json_path}")
        
        # 创建一个简化的标签映射文件，方便查找
        mapping_filename = f"tag_id_mapping_{timestamp}.json"
        mapping_path = os.path.join(self.data_dir, "tags", mapping_filename)
        
        tag_mapping = {}
        for tag in tags:
            tag_id = tag.get('id', '')
            tag_label = tag.get('label', '')
            tag_slug = tag.get('slug', '')
            if tag_id:
                tag_mapping[tag_id] = {
                    'label': tag_label,
                    'slug': tag_slug
                }
        
        with open(mapping_path, 'w', encoding='utf-8') as mappingfile:
            json.dump(tag_mapping, mappingfile, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 标签映射文件已保存到: {mapping_path}")
        
        return csv_path

    def sync_all_tags(self) -> Dict[str, Any]:
        """
        同步所有可用标签到文件
        
        Returns:
            Dict: 同步结果
        """
        start_time = datetime.now()
        logger.info("🚀 开始同步所有可用标签")
        
        try:
            # 获取所有标签
            tags = self.get_available_tags()
            
            if not tags:
                return {
                    "success": False,
                    "error": "无法获取标签列表",
                    "tags_count": 0
                }
            
            # 保存到文件
            csv_file = self.save_tags_to_file(tags)
            
            # 生成统计报告
            print("\n" + "="*80)
            print("🏷️  标签同步报告")
            print("="*80)
            print(f"🕐 同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🎯 同步标签: {len(tags)} 个")
            
            # 按标签名称长度分组统计
            length_stats = {}
            for tag in tags:
                label = tag.get('label', '')
                length = len(label) if label else 0
                if length == 0:
                    key = "无标签名"
                elif length <= 5:
                    key = "短标签(≤5字符)"
                elif length <= 15:
                    key = "中等标签(6-15字符)"
                else:
                    key = "长标签(>15字符)"
                
                length_stats[key] = length_stats.get(key, 0) + 1
            
            if length_stats:
                print(f"\n📊 标签长度分布:")
                for category, count in sorted(length_stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {category}: {count} 个")
            
            # 显示最新的标签
            recent_tags = sorted(tags, key=lambda x: x.get('createdAt', ''), reverse=True)[:10]
            if recent_tags:
                print(f"\n🆕 最新创建的标签 (前10个):")
                for i, tag in enumerate(recent_tags):
                    created_at = tag.get('createdAt', '')
                    if created_at:
                        try:
                            created_time = date_parser.parse(created_at)
                            time_str = created_time.strftime('%Y-%m-%d')
                        except:
                            time_str = created_at[:10]
                    else:
                        time_str = "未知"
                    
                    print(f"   {i+1:2d}. [{time_str}] ID: {tag.get('id', 'N/A'):<10} 名称: {tag.get('label', 'N/A')}")
            
            print("="*80)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "tags_count": len(tags),
                "csv_file": csv_file,
                "duration_seconds": duration
            }
            
        except Exception as e:
            logger.error(f"标签同步失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "tags_count": 0
            }

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
                    
            except requests.exceptions.ConnectionError as e:
                if not self.handle_connection_error(e, attempt):
                    return None
                wait_time = min(10 * (attempt + 1), 30)  # 递增等待时间，最多30秒
                logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            except requests.exceptions.Timeout as e:
                logger.error(f"请求超时 (第{attempt + 1}次): {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"增加超时时间并重试...")
                    timeout = min(timeout * 1.5, 60)  # 增加超时时间
                    time.sleep(5)
                    continue
                else:
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

    def search_markets_by_tag(self, tag_id: str, batch_size: int = 100, max_markets: int = 1000) -> List[Dict]:
        """
        通过标签ID搜索市场
        
        Args:
            tag_id: 标签ID
            batch_size: 批次大小
            max_markets: 最大搜索市场数量
            
        Returns:
            List[Dict]: 匹配的市场列表
        """
        base_url = "https://gamma-api.polymarket.com/markets"
        markets = []
        offset = 0
        
        logger.info(f"🏷️  搜索标签ID '{tag_id}' 的市场...")
        
        while len(markets) < max_markets:
            params = {
                'tagId': tag_id,     # 使用tagId而不是tag
                'closed': 'false',   # 只获取未关闭的市场
                'active': 'true',    # 只获取活跃市场
                'limit': batch_size,
                'offset': offset,
                'order': 'volumeNum',  # 按交易量排序
                'ascending': 'false'   # 降序排列
            }
            
            data = self.make_api_request(base_url, params)
            
            if not data:
                logger.warning(f"无法获取标签ID '{tag_id}' 偏移量 {offset} 的数据")
                break
            
            batch_markets = data if isinstance(data, list) else data.get('data', [])
            
            if not batch_markets:
                logger.info(f"标签ID '{tag_id}' 在偏移量 {offset} 没有找到更多市场")
                break
            
            markets.extend(batch_markets)
            logger.info(f"标签ID '{tag_id}' 获取了 {len(batch_markets)} 个市场，总计 {len(markets)} 个")
            
            offset += len(batch_markets)
            
            # 如果这批数据少于批次大小，说明到达末尾
            if len(batch_markets) < batch_size:
                break
        
        logger.info(f"✅ 标签ID '{tag_id}' 搜索完成: 找到 {len(markets)} 个市场")
        return markets

    def search_markets_by_multiple_tags(self, tag_ids: List[str], batch_size: int = 100) -> List[Dict]:
        """
        搜索多个标签ID的市场并去重
        
        Args:
            tag_ids: 标签ID列表
            batch_size: 批次大小
            
        Returns:
            List[Dict]: 去重后的市场列表
        """
        all_markets = []
        seen_ids = set()
        
        for tag_id in tag_ids:
            logger.info(f"🔍 搜索标签ID: {tag_id}")
            tag_markets = self.search_markets_by_tag(tag_id, batch_size)
            
            # 去重添加
            for market in tag_markets:
                market_id = market.get('id')
                if market_id and market_id not in seen_ids:
                    all_markets.append(market)
                    seen_ids.add(market_id)
                    logger.debug(f"添加市场: {market.get('question', 'Unknown')[:60]}...")
        
        logger.info(f"🎯 多标签ID搜索完成: 总共找到 {len(all_markets)} 个唯一市场")
        return all_markets

    def search_events_by_keyword(self, keyword: str, batch_size: int = 100, max_events: int = 500) -> List[Dict]:
        """
        通过关键词搜索 events
        
        Args:
            keyword: 搜索关键词
            batch_size: 批次大小
            max_events: 最大搜索事件数量
            
        Returns:
            List[Dict]: 匹配的事件列表
        """
        base_url = "https://gamma-api.polymarket.com/events"
        matching_events = []
        offset = 0
        total_checked = 0
        
        logger.info(f"🔍 搜索关键词 '{keyword}' 的事件...")
        
        while total_checked < max_events:
            params = {
                'closed': 'false',
                'active': 'true',
                'limit': batch_size,
                'offset': offset,
                'order': 'startDate',
                'ascending': 'false'
            }
            
            data = self.make_api_request(base_url, params)
            
            if not data:
                break
            
            events = data if isinstance(data, list) else data.get('data', [])
            
            if not events:
                break
            
            # 检查每个事件的标题和描述是否包含关键词
            for event in events:
                total_checked += 1
                title = str(event.get('title', '')).lower()
                description = str(event.get('description', '')).lower()
                slug = str(event.get('slug', '')).lower()
                
                if (keyword.lower() in title or 
                    keyword.lower() in description or 
                    keyword.lower() in slug):
                    matching_events.append(event)
                    logger.debug(f"找到匹配事件: {event.get('title', 'Unknown')[:60]}...")
            
            offset += len(events)
            
            if len(events) < batch_size:
                break
        
        logger.info(f"✅ 关键词 '{keyword}' 事件搜索完成: 检查了 {total_checked} 个事件，找到 {len(matching_events)} 个匹配")
        return matching_events
    
    def get_markets_by_event_id(self, event_id: str) -> List[Dict]:
        """
        通过事件ID获取相关的市场
        
        Args:
            event_id: 事件ID
            
        Returns:
            List[Dict]: 该事件下的市场列表
        """
        base_url = "https://gamma-api.polymarket.com/markets"
        
        params = {
            'eventId': event_id,
            'closed': 'false',
            'active': 'true',
            'limit': 100,
            'order': 'volumeNum',
            'ascending': 'false'
        }
        
        logger.info(f"🎯 获取事件ID '{event_id}' 的市场...")
        
        data = self.make_api_request(base_url, params)
        
        if not data:
            logger.warning(f"无法获取事件ID '{event_id}' 的市场数据")
            return []
        
        markets = data if isinstance(data, list) else data.get('data', [])
        
        logger.info(f"✅ 事件ID '{event_id}' 找到 {len(markets)} 个市场")
        return markets
    
    def search_markets_by_event_keyword(self, keyword: str, max_events: int = 100) -> List[Dict]:
        """
        通过关键词搜索事件，然后获取这些事件下的所有市场
        
        Args:
            keyword: 搜索关键词
            max_events: 最大搜索事件数量
            
        Returns:
            List[Dict]: 所有匹配事件下的市场列表
        """
        logger.info(f"🚀 开始通过关键词 '{keyword}' 搜索事件和市场...")
        
        # 1. 先搜索匹配的事件
        events = self.search_events_by_keyword(keyword, max_events=max_events)
        
        if not events:
            logger.warning(f"关键词 '{keyword}' 没有找到匹配的事件")
            return []
        
        # 2. 为每个事件获取市场
        all_markets = []
        seen_market_ids = set()
        
        for i, event in enumerate(events):
            event_id = event.get('id')
            event_title = event.get('title', 'Unknown')
            
            if not event_id:
                logger.warning(f"事件 '{event_title}' 没有ID，跳过")
                continue
            
            logger.info(f"📊 处理事件 {i+1}/{len(events)}: {event_title[:50]}...")
            
            # 获取该事件的市场
            event_markets = self.get_markets_by_event_id(event_id)
            
            # 去重添加市场
            for market in event_markets:
                market_id = market.get('id')
                if market_id and market_id not in seen_market_ids:
                    # 添加事件信息到市场数据中
                    market['event_info'] = {
                        'event_id': event_id,
                        'event_title': event_title,
                        'event_slug': event.get('slug', ''),
                        'event_description': event.get('description', '')
                    }
                    all_markets.append(market)
                    seen_market_ids.add(market_id)
        
        logger.info(f"🎯 关键词 '{keyword}' 事件搜索完成: 从 {len(events)} 个事件中找到 {len(all_markets)} 个唯一市场")
        return all_markets
    
    def search_markets_by_keyword_direct(self, keyword: str, batch_size: int = 100, max_markets: int = 1000) -> List[Dict]:
        """
        通过关键词直接搜索市场（在问题内容中搜索）
        
        Args:
            keyword: 搜索关键词
            batch_size: 批次大小
            max_markets: 最大搜索市场数量
            
        Returns:
            List[Dict]: 匹配的市场列表
        """
        base_url = "https://gamma-api.polymarket.com/markets"
        matching_markets = []
        offset = 0
        total_checked = 0
        
        logger.info(f"🔍 直接搜索关键词 '{keyword}' 的市场...")
        
        while total_checked < max_markets:
            params = {
                'closed': 'false',
                'active': 'true',
                'limit': batch_size,
                'offset': offset,
                'order': 'volumeNum',
                'ascending': 'false'
            }
            
            data = self.make_api_request(base_url, params)
            
            if not data:
                break
            
            markets = data if isinstance(data, list) else data.get('data', [])
            
            if not markets:
                break
            
            # 检查每个市场的问题是否包含关键词
            for market in markets:
                total_checked += 1
                question = str(market.get('question', '')).lower()
                
                if keyword.lower() in question:
                    matching_markets.append(market)
                    logger.debug(f"找到匹配市场: {market.get('question', 'Unknown')[:60]}...")
            
            offset += len(markets)
            
            if len(markets) < batch_size:
                break
        
        logger.info(f"✅ 关键词 '{keyword}' 直接市场搜索完成: 检查了 {total_checked} 个市场，找到 {len(matching_markets)} 个匹配")
        return matching_markets
    
    def search_markets_by_keyword(self, keyword: str, search_method: str = 'both', **kwargs) -> List[Dict]:
        """
        通过关键词搜索市场的统一接口
        
        Args:
            keyword: 搜索关键词
            search_method: 搜索方法 ('event', 'direct', 'both')
            **kwargs: 其他参数
            
        Returns:
            List[Dict]: 匹配的市场列表
        """
        all_markets = []
        seen_market_ids = set()
        
        if search_method in ['event', 'both']:
            # 通过事件搜索
            logger.info(f"🎯 通过事件搜索关键词 '{keyword}'...")
            event_markets = self.search_markets_by_event_keyword(keyword, **kwargs)
            
            for market in event_markets:
                market_id = market.get('id')
                if market_id and market_id not in seen_market_ids:
                    all_markets.append(market)
                    seen_market_ids.add(market_id)
        
        if search_method in ['direct', 'both']:
            # 直接搜索市场
            logger.info(f"🔍 直接搜索关键词 '{keyword}'...")
            direct_markets = self.search_markets_by_keyword_direct(keyword, **kwargs)
            
            for market in direct_markets:
                market_id = market.get('id')
                if market_id and market_id not in seen_market_ids:
                    all_markets.append(market)
                    seen_market_ids.add(market_id)
        
        logger.info(f"🎯 关键词 '{keyword}' 综合搜索完成: 找到 {len(all_markets)} 个唯一市场")
        return all_markets

    def save_markets_data(self, markets: List[Dict], tag_name: str) -> str:
        """
        保存市场数据到CSV文件
        
        Args:
            markets: 市场列表
            tag_name: 标签名称或ID（用于文件命名）
            
        Returns:
            str: 保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_tag_name = "".join(c for c in tag_name if c.isalnum() or c in ('-', '_')).lower()
        filename = f"{safe_tag_name}_markets_{timestamp}.csv"
        full_path = os.path.join(self.data_dir, "tags", filename)
        
        # CSV标题 - 添加事件相关字段
        headers = [
            'id', 'question', 'slug', 'category', 'tags', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest', 'createdAt', 'updatedAt',
            # 事件相关字段
            'event_id', 'event_title', 'event_slug', 'event_description'
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
                            return json.dumps(field_value)
                        elif isinstance(field_value, str):
                            return field_value
                        else:
                            return str(field_value) if field_value is not None else ''
                    
                    # 获取事件信息
                    event_info = market.get('event_info', {})
                    
                    # 创建数据行
                    row = [
                        market.get('id', ''),
                        market.get('question', ''),
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
                        # 事件信息
                        event_info.get('event_id', ''),
                        event_info.get('event_title', ''),
                        event_info.get('event_slug', ''),
                        event_info.get('event_description', '')
                    ]
                    
                    writer.writerow(row)
                    
                except Exception as e:
                    logger.error(f"处理市场 {market.get('id', 'unknown')} 时出错: {e}")
                    continue
        
        logger.info(f"💾 市场数据已保存到: {full_path}")
        return full_path

    def generate_markets_report(self, markets: List[Dict], search_term: str) -> Dict[str, Any]:
        """
        生成市场报告
        
        Args:
            markets: 市场列表
            search_term: 搜索词（标签或关键词）
            
        Returns:
            Dict: 报告数据
        """
        current_time = datetime.now()
        
        # 按交易量排序
        sorted_markets = sorted(markets, key=lambda x: float(x.get('volumeNum', 0) or 0), reverse=True)
        
        # 分离有事件信息和无事件信息的市场
        markets_with_events = []
        markets_without_events = []
        events_info = {}
        
        for market in markets:
            event_info = market.get('event_info', {})
            if event_info.get('event_id'):
                markets_with_events.append(market)
                event_id = event_info['event_id']
                if event_id not in events_info:
                    events_info[event_id] = {
                        'event_title': event_info.get('event_title', ''),
                        'event_slug': event_info.get('event_slug', ''),
                        'event_description': event_info.get('event_description', ''),
                        'markets': []
                    }
                events_info[event_id]['markets'].append(market)
            else:
                markets_without_events.append(market)
        
        # 统计信息
        total_volume = 0
        total_liquidity = 0
        categories = {}
        
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
        
        # 生成事件统计
        events_stats = []
        for event_id, event_data in events_info.items():
            event_markets = event_data['markets']
            event_volume = sum(float(m.get('volumeNum', 0) or 0) for m in event_markets)
            event_liquidity = sum(float(m.get('liquidityNum', 0) or 0) for m in event_markets)
            
            events_stats.append({
                'event_id': event_id,
                'event_title': event_data['event_title'],
                'event_slug': event_data['event_slug'],
                'markets_count': len(event_markets),
                'total_volume': event_volume,
                'total_liquidity': event_liquidity,
                'markets': sorted(event_markets, key=lambda x: float(x.get('volumeNum', 0) or 0), reverse=True)
            })
        
        # 按事件交易量排序
        events_stats.sort(key=lambda x: x['total_volume'], reverse=True)
        
        report = {
            "timestamp": current_time.isoformat(),
            "search_term": search_term,
            "total_markets": len(markets),
            "markets_with_events": len(markets_with_events),
            "markets_without_events": len(markets_without_events),
            "total_events": len(events_info),
            "total_volume": total_volume,
            "total_liquidity": total_liquidity,
            "categories": categories,
            "time_ranges": time_ranges,
            "events_stats": events_stats,
            "top_markets": [],
            "standalone_markets": []
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
            
            # 获取事件信息
            event_info = market.get('event_info', {})
            
            report["top_markets"].append({
                "rank": i + 1,
                "id": market.get('id', ''),
                "question": market.get('question', '')[:100],
                "category": market.get('category', ''),
                "endDate": end_date,
                "time_remaining": time_remaining,
                "volume": market.get('volumeNum', 0),
                "liquidity": market.get('liquidityNum', 0),
                "event_id": event_info.get('event_id', ''),
                "event_title": event_info.get('event_title', '')[:50] if event_info.get('event_title') else ''
            })
        
        # 添加独立市场（无事件信息的市场）
        sorted_standalone = sorted(markets_without_events, key=lambda x: float(x.get('volumeNum', 0) or 0), reverse=True)
        for i, market in enumerate(sorted_standalone[:10]):
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
            
            report["standalone_markets"].append({
                "rank": i + 1,
                "id": market.get('id', ''),
                "question": market.get('question', '')[:100],
                "category": market.get('category', ''),
                "endDate": end_date,
                "time_remaining": time_remaining,
                "volume": market.get('volumeNum', 0),
                "liquidity": market.get('liquidityNum', 0)
            })
        
        return report

    def print_markets_summary(self, markets: List[Dict], search_term: str):
        """
        打印市场摘要 - 分别展示事件和独立市场
        """
        report = self.generate_markets_report(markets, search_term)
        
        print("\n" + "="*80)
        print(f"🏷️  标签市场报告 - '{search_term}'")
        print("="*80)
        print(f"🕐 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 发现市场: {report['total_markets']} 个")
        print(f"   └─ 关联事件的市场: {report['markets_with_events']} 个")
        print(f"   └─ 独立市场: {report['markets_without_events']} 个")
        print(f"🎪 发现事件: {report['total_events']} 个")
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
        
        # 显示事件部分
        if report['events_stats']:
            print(f"\n" + "="*60)
            print(f"🎪 事件部分 - 共 {len(report['events_stats'])} 个事件")
            print("="*60)
            
            for i, event in enumerate(report['events_stats'][:10]):  # 显示前10个事件
                print(f"\n📅 事件 {i+1}: {event['event_title']}")
                print(f"   事件ID: {event['event_id']}")
                print(f"   市场数量: {event['markets_count']} 个")
                print(f"   总交易量: ${event['total_volume']:,.2f}")
                print(f"   总流动性: ${event['total_liquidity']:,.2f}")
                
                # 显示该事件下的前3个市场
                top_event_markets = event['markets'][:3]
                if top_event_markets:
                    print(f"   🔥 热门市场:")
                    for j, market in enumerate(top_event_markets):
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
                        
                        volume = float(market.get('volumeNum', 0) or 0)
                        question = market.get('question', '')[:80]
                        print(f"      {j+1}. [{time_remaining}] {question}")
                        print(f"         ID: {market.get('id', '')} | 交易量: ${volume:,.0f}")
            
            if len(report['events_stats']) > 10:
                print(f"\n   ... 还有 {len(report['events_stats']) - 10} 个事件")
        
        # 显示独立市场部分
        if report['standalone_markets']:
            print(f"\n" + "="*60)
            print(f"🏪 独立市场部分 - 共 {len(report['standalone_markets'])} 个市场")
            print("="*60)
            
            for market in report['standalone_markets']:
                print(f"   {market['rank']:2d}. [{market['time_remaining']}] {market['question']}")
                print(f"       ID: {market['id']} | 交易量: ${market['volume']:,.0f}")
        
        # 显示总体排名（所有市场混合）
        if report['top_markets']:
            print(f"\n" + "="*60)
            print(f"🏆 总体交易量排名 (前{min(10, len(report['top_markets']))}个)")
            print("="*60)
            for market in report['top_markets'][:10]:
                event_info = f" [事件: {market['event_title']}]" if market.get('event_title') else " [独立市场]"
                print(f"   {market['rank']:2d}. [{market['time_remaining']}] {market['question']}{event_info}")
                print(f"       ID: {market['id']} | 交易量: ${market['volume']:,.0f}")
        
        print("="*80)

    def run_tag_sync(self, tag_ids: List[str] = None, keywords: List[str] = None, 
                     save_to_file: bool = True, search_method: str = 'both') -> Dict[str, Any]:
        """
        运行标签市场同步
        
        Args:
            tag_ids: 标签ID列表
            keywords: 关键词列表
            save_to_file: 是否保存到文件
            search_method: 关键词搜索方法 ('event', 'direct', 'both')
            
        Returns:
            Dict: 同步结果
        """
        start_time = datetime.now()
        logger.info(f"🚀 开始标签市场同步")
        
        try:
            all_markets = []
            search_terms = []
            
            # 通过标签ID搜索
            if tag_ids:
                tag_markets = self.search_markets_by_multiple_tags(tag_ids)
                all_markets.extend(tag_markets)
                search_terms.extend(tag_ids)
            
            # 通过关键词搜索
            if keywords:
                seen_ids = {m.get('id') for m in all_markets}
                for keyword in keywords:
                    keyword_markets = self.search_markets_by_keyword(keyword, search_method=search_method)
                    # 去重添加
                    for market in keyword_markets:
                        if market.get('id') not in seen_ids:
                            all_markets.append(market)
                            seen_ids.add(market.get('id'))
                    search_terms.append(keyword)
            
            # 如果没有指定搜索条件，返回错误
            if not tag_ids and not keywords:
                return {
                    "success": False,
                    "error": "必须指定至少一个标签ID或关键词",
                    "markets_count": 0
                }
            
            # 保存到文件
            csv_file = None
            if save_to_file and all_markets:
                search_name = "_".join(search_terms[:3])  # 最多使用前3个搜索词
                csv_file = self.save_markets_data(all_markets, search_name)
            
            # 生成报告
            search_term_str = ", ".join(search_terms)
            report = self.generate_markets_report(all_markets, search_term_str)
            
            # 保存JSON报告
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_search_name = "".join(c for c in search_term_str if c.isalnum() or c in ('-', '_', ' ')).replace(' ', '_')
                json_file = os.path.join(self.data_dir, "reports", f"tag_report_{safe_search_name}_{timestamp}.json")
                with open(json_file, "w", encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"📊 报告已保存到: {json_file}")
            
            # 打印摘要
            self.print_markets_summary(all_markets, search_term_str)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "markets_count": len(all_markets),
                "csv_file": csv_file,
                "duration_seconds": duration,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"标签市场同步失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "markets_count": 0
            }

def main():
    parser = argparse.ArgumentParser(description="标签市场同步器 - 通用的标签ID和关键词市场搜索工具")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--tag-ids", nargs='+', help="要搜索的标签ID列表")
    parser.add_argument("--keywords", nargs='+', help="要搜索的关键词列表")
    parser.add_argument("--search-method", choices=['event', 'direct', 'both'], default='both',
                       help="关键词搜索方法: event=通过事件搜索, direct=直接搜索市场, both=两种方法都用")
    parser.add_argument("--list-tags", action="store_true", help="列出所有可用的标签ID")
    parser.add_argument("--sync-tags", action="store_true", help="同步所有可用标签到文件")
    parser.add_argument("--test-connection", action="store_true", help="测试网络连接")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件，仅显示结果")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    syncer = TagMarketsSync(data_dir=args.data_dir)
    
    # 如果用户要求测试连接
    if args.test_connection:
        success = syncer.run_connection_test()
        if success:
            print("\n✅ 连接测试通过，可以正常使用程序")
        else:
            print("\n❌ 连接测试失败，请检查网络设置")
        return
    
    # 如果用户要求同步所有标签
    if args.sync_tags:
        result = syncer.sync_all_tags()
        if result["success"]:
            print(f"\n✅ 标签同步完成!")
            print(f"   同步标签: {result['tags_count']} 个")
            print(f"   耗时: {result['duration_seconds']:.1f} 秒")
            print(f"   数据文件: {result['csv_file']}")
        else:
            print(f"\n❌ 标签同步失败: {result.get('error', 'Unknown error')}")
            if "Connection" in str(result.get('error', '')):
                syncer.print_connection_troubleshooting()
        return
    
    # 如果用户要求列出标签
    if args.list_tags:
        syncer.get_available_tags()
        return
    
    # 检查参数
    if not args.tag_ids and not args.keywords:
        print("❌ 错误: 必须指定至少一个 --tag-ids 或 --keywords 参数")
        print("\n示例用法:")
        print("  python3 sync/tag_markets_sync.py --test-connection  # 测试网络连接")
        print("  python3 sync/tag_markets_sync.py --list-tags        # 查看可用标签ID")
        print("  python3 sync/tag_markets_sync.py --sync-tags        # 同步所有标签到文件")
        print("  python3 sync/tag_markets_sync.py --tag-ids 180 241")
        print("  python3 sync/tag_markets_sync.py --keywords bitcoin crypto")
        print("  python3 sync/tag_markets_sync.py --keywords bitcoin --search-method event")
        print("  python3 sync/tag_markets_sync.py --tag-ids 180 --keywords football --search-method both")
        return
    
    result = syncer.run_tag_sync(
        tag_ids=args.tag_ids,
        keywords=args.keywords,
        save_to_file=not args.no_save,
        search_method=args.search_method
    )
    
    if result["success"]:
        print(f"\n✅ 标签市场同步完成!")
        print(f"   发现市场: {result['markets_count']} 个")
        print(f"   搜索方法: {args.search_method}")
        print(f"   耗时: {result['duration_seconds']:.1f} 秒")
        if result.get("csv_file"):
            print(f"   数据文件: {result['csv_file']}")
    else:
        print(f"\n❌ 标签市场同步失败: {result.get('error', 'Unknown error')}")
        if "Connection" in str(result.get('error', '')):
            syncer.print_connection_troubleshooting()

if __name__ == "__main__":
    main()