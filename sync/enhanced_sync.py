#!/usr/bin/env python3
"""
增强版Polymarket同步器 - 真实API模式
参照example.py的模式，添加更好的错误处理和重试机制
"""

import json
import os
import csv
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedPolymarketSync:
    def __init__(self, data_dir: str = "./data", batch_size: int = 100, max_retries: int = 3):
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # 标准请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://polymarket.com/"
        }
        
        # 确保目录存在
        for subdir in ["tag", "sync_logs", "reports", "analysis", "markets", "events"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

    def count_csv_lines(self, filename: str) -> int:
        """计算CSV文件的行数（不包括标题行）"""
        if not os.path.exists(filename):
            return 0
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return sum(1 for line in f) - 1  # 减去标题行
        except Exception:
            return 0

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

    def update_markets(self, tag_id: Optional[int] = None, csv_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        批量获取市场数据并保存到CSV，基于完整的market数据结构
        
        Args:
            tag_id: 可选的标签ID，用于筛选特定标签的市场
            csv_filename: 可选的CSV文件名，如果不提供则自动生成带日期的文件名
        """
        base_url = "https://gamma-api.polymarket.com/markets"
        
        # 生成带日期后缀的文件名
        if csv_filename is None:
            date_suffix = datetime.now().strftime("%Y-%m-%d")
            if tag_id is not None:
                csv_filename = f"markets_tag_{tag_id}_{date_suffix}.csv"
            else:
                csv_filename = f"markets_{date_suffix}.csv"
        
        full_path = os.path.join(self.data_dir, "markets", csv_filename)
        
        # 精简的CSV标题 - 只保留指定的核心字段
        headers = [
            'id', 'question', 'slug', 'category', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest'
        ]
        
        # 根据现有记录动态设置偏移量
        current_offset = self.count_csv_lines(full_path)
        file_exists = os.path.exists(full_path) and current_offset > 0
        
        if file_exists:
            if tag_id is not None:
                logger.info(f"发现 {current_offset} 条现有记录 (标签ID: {tag_id})，从偏移量 {current_offset} 继续")
            else:
                logger.info(f"发现 {current_offset} 条现有记录，从偏移量 {current_offset} 继续")
            mode = 'a'
        else:
            if tag_id is not None:
                logger.info(f"创建新的CSV文件 (标签ID: {tag_id}): {full_path}")
            else:
                logger.info(f"创建新的CSV文件: {full_path}")
            mode = 'w'
        
        total_fetched = 0
        start_time = datetime.now()
        
        with open(full_path, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 只有新文件才写入标题
            if mode == 'w':
                writer.writerow(headers)
            
            while True:
                if tag_id is not None:
                    logger.info(f"获取偏移量 {current_offset} 的批次数据 (标签ID: {tag_id})...")
                else:
                    logger.info(f"获取偏移量 {current_offset} 的批次数据...")
                
                params = {
                    'order': 'createdAt',
                    'closed': 'false',
                    'ascending': 'true',
                    'limit': self.batch_size,
                    'offset': current_offset
                }
                
                # 添加tag_id查询条件
                if tag_id is not None:
                    params['tag_id'] = tag_id
                
                data = self.make_api_request(base_url, params)
                
                if not data:
                    logger.error(f"无法获取偏移量 {current_offset} 的数据")
                    break
                
                markets = data if isinstance(data, list) else data.get('data', [])
                
                if not markets:
                    logger.info(f"在偏移量 {current_offset} 没有找到更多市场，完成！")
                    break
                
                batch_count = 0
                
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
                        
                        # 创建精简的数据行，按照headers顺序
                        row = [
                            market.get('id', ''),
                            market.get('question', ''),
                            market.get('slug', ''),
                            market.get('category', ''),
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
                            market.get('openInterest', '')
                        ]
                        
                        writer.writerow(row)
                        batch_count += 1
                        
                    except (ValueError, KeyError, json.JSONDecodeError) as e:
                        logger.error(f"处理市场 {market.get('id', 'unknown')} 时出错: {e}")
                        continue
                
                total_fetched += batch_count
                current_offset += batch_count
                
                logger.info(f"处理了 {batch_count} 个市场。总新增: {total_fetched}。下一个偏移量: {current_offset}")
                
                # 如果获取的市场数少于批次大小，说明到达末尾
                if len(markets) < self.batch_size:
                    logger.info(f"只收到 {len(markets)} 个市场（少于批次大小），已到达末尾")
                    break
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "total_fetched": total_fetched,
            "final_offset": current_offset,
            "duration_seconds": duration,
            "csv_file": full_path,
            "csv_filename": csv_filename,
            "tag_id": tag_id
        }

    def update_events(self, csv_filename: str = "events.csv") -> Dict[str, Any]:
        """
        批量获取事件数据并保存到CSV
        """
        base_url = "https://gamma-api.polymarket.com/events"
        full_path = os.path.join(self.data_dir, "events", csv_filename)
        
        # CSV标题
        headers = [
            'id', 'slug', 'title', 'resolutionSource', 'startDate', 'endDate',
             'category', 'active', 'closed', 'volume', 'volumn24hr','volume1wk','liquidity',
             'liquidityAmm','liquidityClob', 'commnentCount','tags', 'ticker', 'image'
        ]
        
        # 根据现有记录动态设置偏移量
        current_offset = self.count_csv_lines(full_path)
        file_exists = os.path.exists(full_path) and current_offset > 0
        
        if file_exists:
            logger.info(f"发现 {current_offset} 条现有事件记录，从偏移量 {current_offset} 继续")
            mode = 'a'
        else:
            logger.info(f"创建新的事件CSV文件: {full_path}")
            mode = 'w'
        
        total_fetched = 0
        start_time = datetime.now()
        
        with open(full_path, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 只有新文件才写入标题
            if mode == 'w':
                writer.writerow(headers)
            
            while True:
                logger.info(f"获取事件偏移量 {current_offset} 的批次数据...")
                
                params = {
                    'limit': self.batch_size,
                    'offset': current_offset
                }
                
                data = self.make_api_request(base_url, params)
                
                if not data:
                    logger.error(f"无法获取偏移量 {current_offset} 的事件数据")
                    break
                
                events = data if isinstance(data, list) else data.get('data', [])
                
                if not events:
                    logger.info(f"在偏移量 {current_offset} 没有找到更多事件，完成！")
                    break
                
                batch_count = 0
                
                for event in events:
                    try:
                        # 处理标签
                        tags = event.get('tags', [])
                        tags_str = ','.join(tags) if isinstance(tags, list) else str(tags)
                        
                        row = [
                            event.get('id', ''),
                            event.get('slug', ''),
                            event.get('title', ''),
                            event.get('description', ''),
                            event.get('createdAt', ''),
                            event.get('startDate', ''),
                            event.get('endDate', ''),
                            event.get('volume', ''),
                            event.get('liquidity', ''),
                            event.get('active', ''),
                            event.get('closed', ''),
                            tags_str,
                            event.get('ticker', ''),
                            event.get('image', '')
                        ]
                        
                        writer.writerow(row)
                        batch_count += 1
                        
                    except Exception as e:
                        logger.error(f"处理事件 {event.get('id', 'unknown')} 时出错: {e}")
                        continue
                
                total_fetched += batch_count
                current_offset += batch_count
                
                logger.info(f"处理了 {batch_count} 个事件。总新增: {total_fetched}。下一个偏移量: {current_offset}")
                
                # 如果获取的事件数少于批次大小，说明到达末尾
                if len(events) < self.batch_size:
                    logger.info(f"只收到 {len(events)} 个事件（少于批次大小），已到达末尾")
                    break
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "total_fetched": total_fetched,
            "final_offset": current_offset,
            "duration_seconds": duration,
            "csv_file": full_path
        }

    def update_markets_by_tag(self, tag_id: int, csv_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        根据标签ID获取市场数据的便捷方法
        
        Args:
            tag_id: 标签ID
            csv_filename: 可选的CSV文件名
            
        Returns:
            同步结果字典
        """
        logger.info(f"开始同步标签ID {tag_id} 的市场数据...")
        return self.update_markets(tag_id=tag_id, csv_filename=csv_filename)

    def get_available_filename_formats(self) -> Dict[str, str]:
        """
        获取可用的文件名格式示例
        
        Returns:
            文件名格式示例字典
        """
        date_suffix = datetime.now().strftime("%Y-%m-%d")
        return {
            "default": f"markets_{date_suffix}.csv",
            "with_tag": f"markets_tag_123_{date_suffix}.csv",
            "custom": "custom_markets_name.csv"
        }
        
    def test_market_csv_structure(self) -> bool:
        logger.info("测试市场CSV结构...")
        
        # 模拟市场数据
        sample_market = {
            "id": "test_market_123",
            "question": "Will this test pass?",
            "conditionId": "0x123abc",
            "slug": "test-market",
            "volume": "1000.50",
            "active": True,
            "closed": False,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["token1", "token2"],
            "createdAt": "2023-11-07T05:31:56Z"
        }
        
        # 测试safe_json_field函数
        def safe_json_field(field_value):
            if isinstance(field_value, (list, dict)):
                return json.dumps(field_value)
            elif isinstance(field_value, str):
                return field_value
            else:
                return str(field_value) if field_value is not None else ''
        
        # 测试数据处理
        outcomes_json = safe_json_field(sample_market.get('outcomes'))
        tokens_json = safe_json_field(sample_market.get('clobTokenIds'))
        
        print(f"✅ 测试结果:")
        print(f"   Outcomes JSON: {outcomes_json}")
        print(f"   Tokens JSON: {tokens_json}")
        print(f"   市场ID: {sample_market.get('id')}")
        print(f"   问题: {sample_market.get('question')}")
        
        logger.info("市场CSV结构测试完成")
        return True

    def get_market_csv_headers(self) -> List[str]:
        """
        获取市场CSV表头列表，用于外部引用
        """
        return [
            'id', 'question', 'slug', 'category', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest'
        ]

    def test_market_csv_structure(self) -> bool:
        """
        测试新的市场CSV结构
        """
        logger.info("测试市场CSV结构...")
        
        # 模拟市场数据
        sample_market = {
            "id": "test_market_123",
            "question": "Will this test pass?",
            "conditionId": "0x123abc",
            "slug": "test-market",
            "volume": "1000.50",
            "active": True,
            "closed": False,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["token1", "token2"],
            "createdAt": "2023-11-07T05:31:56Z"
        }
        
        # 测试safe_json_field函数
        def safe_json_field(field_value):
            if isinstance(field_value, (list, dict)):
                return json.dumps(field_value)
            elif isinstance(field_value, str):
                return field_value
            else:
                return str(field_value) if field_value is not None else ''
        
        # 测试数据处理
        outcomes_json = safe_json_field(sample_market.get('outcomes'))
        tokens_json = safe_json_field(sample_market.get('clobTokenIds'))
        
        print(f"✅ 测试结果:")
        print(f"   Outcomes JSON: {outcomes_json}")
        print(f"   Tokens JSON: {tokens_json}")
        print(f"   市场ID: {sample_market.get('id')}")
        print(f"   问题: {sample_market.get('question')}")
        
        logger.info("市场CSV结构测试完成")
        return True

    def test_api_endpoints(self) -> Dict[str, Any]:
        """
        测试API端点连通性
        """
        endpoints = {
            "markets": "https://gamma-api.polymarket.com/markets",
            "events": "https://gamma-api.polymarket.com/events"
        }
        
        results = {}
        
        for name, url in endpoints.items():
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                results[name] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(response.text),
                    "has_json": False,
                    "data_type": None,
                    "error": None
                }
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        results[name]["has_json"] = True
                        results[name]["data_type"] = type(data).__name__
                        if isinstance(data, list):
                            results[name]["data_count"] = len(data)
                        elif isinstance(data, dict):
                            results[name]["data_keys"] = list(data.keys())
                    except json.JSONDecodeError:
                        results[name]["error"] = "Invalid JSON"
                else:
                    results[name]["error"] = f"HTTP {response.status_code}"
                    
            except Exception as e:
                results[name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 打印测试结果
        print("\n" + "="*60)
        print("🔍 API端点测试结果")
        print("="*60)
        
        for name, result in results.items():
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {name.upper()}: {endpoints[name]}")
            
            if result.get("success"):
                print(f"   状态码: {result['status_code']}")
                print(f"   内容类型: {result['content_type']}")
                print(f"   数据类型: {result.get('data_type', 'N/A')}")
                if 'data_count' in result:
                    print(f"   数据数量: {result['data_count']}")
                elif 'data_keys' in result:
                    print(f"   数据键: {result['data_keys']}")
            else:
                print(f"   错误: {result.get('error', 'Unknown')}")
            print()
        
        return results

    def sync_all_data(self) -> Dict[str, Any]:
        """
        执行完整的数据同步，包括市场和事件
        """
        start_time = datetime.now()
        logger.info("开始完整数据同步...")
        
        results = {
            "start_time": start_time.isoformat(),
            "markets": None,
            "events": None,
            "errors": []
        }
        
        try:
            # 同步市场数据
            logger.info("开始同步市场数据...")
            markets_result = self.update_markets()
            results["markets"] = markets_result
            logger.info(f"市场同步完成: {markets_result['total_fetched']} 条记录")
            
        except Exception as e:
            error_msg = f"市场同步失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        try:
            # 同步事件数据
            logger.info("开始同步事件数据...")
            events_result = self.update_events()
            results["events"] = events_result
            logger.info(f"事件同步完成: {events_result['total_fetched']} 条记录")
            
        except Exception as e:
            error_msg = f"事件同步失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "success": len(results["errors"]) == 0
        })
        
        # 生成报告
        self._save_sync_report(results)
        self._print_sync_summary(results)
        
        return results

    def _save_sync_report(self, results: Dict[str, Any]):
        """保存同步报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON报告
        json_file = os.path.join(self.data_dir, "reports", f"sync_report_{timestamp}.json")
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"同步报告已保存: {json_file}")

    def _print_sync_summary(self, results: Dict[str, Any]):
        """打印同步摘要"""
        print("\n" + "="*80)
        print("🎉 Polymarket数据同步完成")
        print("="*80)
        print(f"⏱️  总耗时: {results['duration_seconds']:.1f} 秒")
        
        if results.get("markets"):
            markets = results["markets"]
            print(f"💹 市场: {markets['total_fetched']} 条新记录")
            print(f"   文件: {markets['csv_file']}")
        
        if results.get("events"):
            events = results["events"]
            print(f"📅 事件: {events['total_fetched']} 条新记录")
            print(f"   文件: {events['csv_file']}")
        
        if results.get("errors"):
            print(f"❌ 错误: {len(results['errors'])} 个")
            for error in results["errors"]:
                print(f"   - {error}")
        
def main():
    parser = argparse.ArgumentParser(description="增强版Polymarket同步器")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--test", action="store_true", help="测试API端点")
    parser.add_argument("--test-csv", action="store_true", help="测试CSV结构")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    parser.add_argument("--mode", choices=["markets", "events", "all"], default="all", help="同步模式")
    parser.add_argument("--batch-size", type=int, default=100, help="批次大小")
    parser.add_argument("--tag-id", type=int, help="标签ID，用于筛选特定标签的市场")
    parser.add_argument("--filename", help="自定义CSV文件名（不包含路径）")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    syncer = EnhancedPolymarketSync(data_dir=args.data_dir, batch_size=args.batch_size)
    
    if args.test:
        syncer.test_api_endpoints()
    elif args.test_csv:
        syncer.test_market_csv_structure()
        headers = syncer.get_market_csv_headers()
        print(f"\n📊 市场CSV包含 {len(headers)} 个字段:")
        for i, header in enumerate(headers, 1):
            print(f"  {i:2d}. {header}")
    elif args.mode == "markets":
        result = syncer.update_markets(tag_id=args.tag_id, csv_filename=args.filename)
        print(f"✅ 市场同步完成: {result['total_fetched']} 条记录")
        print(f"📁 文件: {result['csv_filename']}")
        if result['tag_id']:
            print(f"🏷️  标签ID: {result['tag_id']}")
    elif args.mode == "events":
        result = syncer.update_events()
        print(f"✅ 事件同步完成: {result['total_fetched']} 条记录")
    else:
        syncer.sync_all_data()

if __name__ == "__main__":
    main()