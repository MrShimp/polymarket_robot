#!/usr/bin/env python3
"""
紧急市场同步器 - 获取15分钟内结束的市场数据
基于enhanced_sync.py的能力，专门用于获取即将结束的市场
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

class UrgentMarketsSync:
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
        for subdir in ["urgent", "sync_logs", "reports"]:
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

    def is_ending_soon(self, end_date_str: str, minutes_threshold: int = 15) -> bool:
        """
        检查市场是否在指定分钟内结束
        
        Args:
            end_date_str: 结束日期字符串
            minutes_threshold: 分钟阈值，默认15分钟
            
        Returns:
            bool: 是否即将结束
        """
        if not end_date_str:
            return False
            
        try:
            # 解析结束时间
            end_time = date_parser.parse(end_date_str)
            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            
            # 计算时间差
            time_diff = end_time - current_time
            
            # 检查是否在阈值内且未过期
            return 0 < time_diff.total_seconds() <= (minutes_threshold * 60)
            
        except Exception as e:
            logger.error(f"解析日期失败 {end_date_str}: {e}")
            return False

    def get_urgent_markets(self, minutes_threshold: int = 15, batch_size: int = 100) -> List[Dict]:
        """
        获取即将结束的市场数据
        
        Args:
            minutes_threshold: 分钟阈值，默认15分钟
            batch_size: 批次大小
            
        Returns:
            List[Dict]: 即将结束的市场列表
        """
        base_url = "https://gamma-api.polymarket.com/markets"
        urgent_markets = []
        offset = 0
        total_checked = 0
        
        logger.info(f"🔍 开始搜索{minutes_threshold}分钟内结束的市场...")
        
        while True:
            logger.info(f"检查偏移量 {offset} 的批次数据...")
            
            params = {
                'order': 'endDate',  # 按结束时间排序
                'closed': 'false',   # 只获取未关闭的市场
                'ascending': 'true', # 升序排列，最快结束的在前面
                'limit': batch_size,
                'offset': offset
            }
            
            data = self.make_api_request(base_url, params)
            
            if not data:
                logger.error(f"无法获取偏移量 {offset} 的数据")
                break
            
            markets = data if isinstance(data, list) else data.get('data', [])
            
            if not markets:
                logger.info(f"在偏移量 {offset} 没有找到更多市场")
                break
            
            # 检查每个市场
            found_in_batch = 0
            for market in markets:
                total_checked += 1
                end_date = market.get('endDate', '')
                
                if self.is_ending_soon(end_date, minutes_threshold):
                    urgent_markets.append(market)
                    found_in_batch += 1
                    logger.info(f"⚡ 发现紧急市场: {market.get('question', 'Unknown')[:60]}... (结束时间: {end_date})")
                elif end_date:
                    # 如果当前市场的结束时间已经超过阈值，且是按时间排序的，可以考虑停止
                    try:
                        end_time = date_parser.parse(end_date)
                        current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                        time_diff = end_time - current_time
                        
                        # 如果时间差超过阈值太多，可能不需要继续检查了
                        if time_diff.total_seconds() > (minutes_threshold * 60 * 2):  # 超过阈值2倍
                            logger.info(f"市场结束时间过远，停止搜索 (当前市场结束时间: {end_date})")
                            break
                    except:
                        pass
            
            logger.info(f"批次检查完成: 检查了 {len(markets)} 个市场，发现 {found_in_batch} 个紧急市场")
            
            offset += len(markets)
            
            # 如果这批数据少于批次大小，说明到达末尾
            if len(markets) < batch_size:
                logger.info(f"已检查完所有市场")
                break
                
            # 防止无限循环，设置最大检查数量
            if total_checked > 10000:
                logger.warning(f"已检查 {total_checked} 个市场，停止搜索")
                break
        
        logger.info(f"🎯 搜索完成: 总共检查了 {total_checked} 个市场，发现 {len(urgent_markets)} 个紧急市场")
        return urgent_markets

    def save_urgent_markets(self, urgent_markets: List[Dict], minutes_threshold: int = 15) -> str:
        """
        保存紧急市场数据到CSV文件
        
        Args:
            urgent_markets: 紧急市场列表
            minutes_threshold: 分钟阈值
            
        Returns:
            str: 保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"urgent_markets_{minutes_threshold}min_{timestamp}.csv"
        full_path = os.path.join(self.data_dir, "urgent", filename)
        
        # CSV标题 - 使用与enhanced_sync相同的20个核心字段
        headers = [
            'id', 'question', 'slug', 'category', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest'
        ]
        
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for market in urgent_markets:
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
                    
                    # 创建数据行，按照headers顺序
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
                    
                except Exception as e:
                    logger.error(f"处理市场 {market.get('id', 'unknown')} 时出错: {e}")
                    continue
        
        logger.info(f"💾 紧急市场数据已保存到: {full_path}")
        return full_path

    def generate_urgent_report(self, urgent_markets: List[Dict], minutes_threshold: int = 15) -> Dict[str, Any]:
        """
        生成紧急市场报告
        
        Args:
            urgent_markets: 紧急市场列表
            minutes_threshold: 分钟阈值
            
        Returns:
            Dict: 报告数据
        """
        current_time = datetime.now()
        
        # 按结束时间排序
        sorted_markets = sorted(urgent_markets, key=lambda x: x.get('endDate', ''))
        
        # 统计信息
        total_volume = 0
        total_liquidity = 0
        categories = {}
        
        for market in urgent_markets:
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
        
        report = {
            "timestamp": current_time.isoformat(),
            "minutes_threshold": minutes_threshold,
            "total_urgent_markets": len(urgent_markets),
            "total_volume": total_volume,
            "total_liquidity": total_liquidity,
            "categories": categories,
            "top_markets": []
        }
        
        # 添加前10个最紧急的市场
        for i, market in enumerate(sorted_markets[:10]):
            end_date = market.get('endDate', '')
            time_remaining = "Unknown"
            
            if end_date:
                try:
                    end_time = date_parser.parse(end_date)
                    current_time_tz = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                    time_diff = end_time - current_time_tz
                    minutes_remaining = int(time_diff.total_seconds() / 60)
                    time_remaining = f"{minutes_remaining}分钟"
                except:
                    pass
            
            report["top_markets"].append({
                "rank": i + 1,
                "id": market.get('id', ''),
                "question": market.get('question', '')[:100],
                "endDate": end_date,
                "time_remaining": time_remaining,
                "volume": market.get('volumeNum', 0),
                "liquidity": market.get('liquidityNum', 0)
            })
        
        return report

    def print_urgent_summary(self, urgent_markets: List[Dict], minutes_threshold: int = 15):
        """
        打印紧急市场摘要
        """
        report = self.generate_urgent_report(urgent_markets, minutes_threshold)
        
        print("\n" + "="*80)
        print(f"⚡ 紧急市场报告 - {minutes_threshold}分钟内结束")
        print("="*80)
        print(f"🕐 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 发现紧急市场: {report['total_urgent_markets']} 个")
        print(f"💰 总交易量: ${report['total_volume']:,.2f}")
        print(f"💧 总流动性: ${report['total_liquidity']:,.2f}")
        
        if report['categories']:
            print(f"\n📊 分类统计:")
            for category, count in sorted(report['categories'].items(), key=lambda x: x[1], reverse=True):
                if category and category != 'Unknown':
                    print(f"   {category}: {count} 个市场")
        
        if report['top_markets']:
            print(f"\n🔥 最紧急的市场 (前{len(report['top_markets'])}个):")
            for market in report['top_markets']:
                print(f"   {market['rank']:2d}. [{market['time_remaining']}] {market['question']}")
                print(f"       ID: {market['id']} | 交易量: ${market['volume']:,.0f}")
        
        print("="*80)

    def run_urgent_sync(self, minutes_threshold: int = 15, save_to_file: bool = True) -> Dict[str, Any]:
        """
        运行紧急市场同步
        
        Args:
            minutes_threshold: 分钟阈值
            save_to_file: 是否保存到文件
            
        Returns:
            Dict: 同步结果
        """
        start_time = datetime.now()
        logger.info(f"🚀 开始紧急市场同步 (阈值: {minutes_threshold}分钟)")
        
        try:
            # 获取紧急市场
            urgent_markets = self.get_urgent_markets(minutes_threshold)
            
            # 保存到文件
            csv_file = None
            if save_to_file and urgent_markets:
                csv_file = self.save_urgent_markets(urgent_markets, minutes_threshold)
            
            # 生成报告
            report = self.generate_urgent_report(urgent_markets, minutes_threshold)
            
            # 保存JSON报告
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_file = os.path.join(self.data_dir, "reports", f"urgent_report_{minutes_threshold}min_{timestamp}.json")
                with open(json_file, "w", encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"📊 报告已保存到: {json_file}")
            
            # 打印摘要
            self.print_urgent_summary(urgent_markets, minutes_threshold)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "urgent_markets_count": len(urgent_markets),
                "csv_file": csv_file,
                "duration_seconds": duration,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"紧急市场同步失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "urgent_markets_count": 0
            }

def main():
    parser = argparse.ArgumentParser(description="紧急市场同步器 - 获取即将结束的市场")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--minutes", type=int, default=15, help="分钟阈值 (默认15分钟)")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件，仅显示结果")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    syncer = UrgentMarketsSync(data_dir=args.data_dir)
    
    result = syncer.run_urgent_sync(
        minutes_threshold=args.minutes,
        save_to_file=not args.no_save
    )
    
    if result["success"]:
        print(f"\n✅ 紧急市场同步完成!")
        print(f"   发现紧急市场: {result['urgent_markets_count']} 个")
        print(f"   耗时: {result['duration_seconds']:.1f} 秒")
        if result.get("csv_file"):
            print(f"   数据文件: {result['csv_file']}")
    else:
        print(f"\n❌ 紧急市场同步失败: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()