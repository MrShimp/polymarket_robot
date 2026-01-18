#!/usr/bin/env python3
"""
紧急高置信度策略 - 扫描10分钟内结束且胜率在0.9-0.95之间的市场
"""

import json
import os
import csv
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
from dateutil import parser as date_parser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UrgentHighConfidenceStrategy:
    """紧急高置信度策略类"""
    
    def __init__(self, data_dir: str = "./data", max_retries: int = 3):
        self.data_dir = data_dir
        self.max_retries = max_retries
        
        # 策略参数
        self.time_threshold_minutes = 10  # 10分钟内结束
        self.min_confidence = 0.90  # 最小胜率90%
        self.max_confidence = 0.95  # 最大胜率95%
        
        # 标准请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://polymarket.com/"
        }
        
        # 确保目录存在
        for subdir in ["strategies", "urgent", "reports"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

    def make_api_request(self, url: str, params: Optional[Dict] = None, timeout: int = 30) -> Optional[Dict]:
        """发送API请求，包含重试机制和错误处理"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=timeout)
                
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
                        time.sleep(3)
                        continue
                    else:
                        return None
                
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
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

    def is_ending_soon(self, end_date_str: str, minutes_threshold: int = 10) -> bool:
        """检查市场是否在指定分钟内结束"""
        if not end_date_str:
            return False
            
        try:
            end_time = date_parser.parse(end_date_str)
            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            time_diff = end_time - current_time
            
            # 检查是否在阈值内且未过期
            return 0 < time_diff.total_seconds() <= (minutes_threshold * 60)
            
        except Exception as e:
            logger.error(f"解析日期失败 {end_date_str}: {e}")
            return False

    def parse_outcome_prices(self, outcome_prices_str: str) -> List[float]:
        """解析结果价格字符串"""
        if not outcome_prices_str:
            return []
        
        try:
            # 尝试解析JSON格式的价格
            if outcome_prices_str.startswith('[') and outcome_prices_str.endswith(']'):
                prices = json.loads(outcome_prices_str)
                return [float(price) for price in prices if price]
            else:
                # 如果不是JSON格式，尝试其他解析方式
                return []
        except Exception as e:
            logger.error(f"解析价格失败 {outcome_prices_str}: {e}")
            return []

    def check_confidence_range(self, outcome_prices: List[float]) -> Tuple[bool, float, str]:
        """
        检查胜率是否在目标范围内
        
        Returns:
            Tuple[bool, float, str]: (是否符合条件, 最高胜率, 胜出选项)
        """
        if not outcome_prices or len(outcome_prices) < 2:
            return False, 0.0, ""
        
        try:
            # 找到最高胜率
            max_price = max(outcome_prices)
            max_index = outcome_prices.index(max_price)
            
            # 检查是否在目标范围内
            if self.min_confidence <= max_price <= self.max_confidence:
                winning_option = "Yes" if max_index == 0 else "No"
                return True, max_price, winning_option
            
            return False, max_price, ""
            
        except Exception as e:
            logger.error(f"检查置信度失败: {e}")
            return False, 0.0, ""

    def parse_outcomes(self, outcomes_str: str) -> List[str]:
        """解析结果选项字符串"""
        if not outcomes_str:
            return []
        
        try:
            if outcomes_str.startswith('[') and outcomes_str.endswith(']'):
                outcomes = json.loads(outcomes_str)
                return [str(outcome) for outcome in outcomes]
            else:
                return []
        except Exception as e:
            logger.error(f"解析结果选项失败 {outcomes_str}: {e}")
            return []

    def scan_urgent_markets(self, batch_size: int = 100) -> List[Dict]:
        """扫描紧急市场"""
        base_url = "https://gamma-api.polymarket.com/markets"
        qualifying_markets = []
        offset = 0
        total_checked = 0
        
        logger.info(f"🔍 开始扫描{self.time_threshold_minutes}分钟内结束且胜率在{self.min_confidence}-{self.max_confidence}之间的市场...")
        
        while True:
            logger.info(f"检查偏移量 {offset} 的批次数据...")
            
            params = {
                'order': 'endDate',
                'closed': 'false',
                'ascending': 'true',
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
                
                # 首先检查是否即将结束
                if not self.is_ending_soon(end_date, self.time_threshold_minutes):
                    # 如果当前市场结束时间过远，可能需要停止搜索
                    if end_date:
                        try:
                            end_time = date_parser.parse(end_date)
                            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
                            time_diff = end_time - current_time
                            
                            if time_diff.total_seconds() > (self.time_threshold_minutes * 60 * 3):
                                logger.info(f"市场结束时间过远，停止搜索 (当前市场结束时间: {end_date})")
                                break
                        except:
                            pass
                    continue
                
                # 检查胜率范围
                outcome_prices_str = market.get('outcomePrices', '')
                outcome_prices = self.parse_outcome_prices(outcome_prices_str)
                
                is_qualified, confidence, winning_option = self.check_confidence_range(outcome_prices)
                
                if is_qualified:
                    # 解析结果选项
                    outcomes = self.parse_outcomes(market.get('outcomes', ''))
                    
                    # 添加策略相关信息
                    market_info = market.copy()
                    market_info.update({
                        'strategy_confidence': confidence,
                        'strategy_winning_option': winning_option,
                        'strategy_outcomes': outcomes,
                        'strategy_time_remaining_minutes': self._calculate_time_remaining(end_date),
                        'strategy_scan_timestamp': datetime.now().isoformat()
                    })
                    
                    qualifying_markets.append(market_info)
                    found_in_batch += 1
                    
                    logger.info(f"⚡ 发现符合条件的市场: {market.get('question', 'Unknown')[:60]}...")
                    logger.info(f"   胜率: {confidence:.3f} ({winning_option}) | 剩余时间: {self._calculate_time_remaining(end_date)}分钟")
            
            logger.info(f"批次检查完成: 检查了 {len(markets)} 个市场，发现 {found_in_batch} 个符合条件的市场")
            
            offset += len(markets)
            
            if len(markets) < batch_size:
                logger.info(f"已检查完所有市场")
                break
                
            if total_checked > 5000:  # 限制搜索范围
                logger.warning(f"已检查 {total_checked} 个市场，停止搜索")
                break
        
        logger.info(f"🎯 扫描完成: 总共检查了 {total_checked} 个市场，发现 {len(qualifying_markets)} 个符合条件的市场")
        return qualifying_markets

    def _calculate_time_remaining(self, end_date_str: str) -> int:
        """计算剩余时间（分钟）"""
        if not end_date_str:
            return 0
        
        try:
            end_time = date_parser.parse(end_date_str)
            current_time = datetime.now(end_time.tzinfo) if end_time.tzinfo else datetime.now()
            time_diff = end_time - current_time
            return max(0, int(time_diff.total_seconds() / 60))
        except:
            return 0

    def save_qualifying_markets(self, markets: List[Dict]) -> str:
        """保存符合条件的市场数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"urgent_high_confidence_markets_{timestamp}.csv"
        full_path = os.path.join(self.data_dir, "strategies", filename)
        
        # 扩展的CSV标题，包含策略信息
        headers = [
            'id', 'question', 'slug', 'category', 'clobTokenIds', 'outcomes', 
            'outcomePrices', 'conditionId', 'active', 'closed', 'volumeNum', 
            'volume24hr', 'liquidity', 'liquidityNum', 'endDate', 
            'orderPriceMinTickSize', 'orderMinSize', 'resolutionSource', 
            'acceptingOrders', 'openInterest',
            # 策略相关字段
            'strategy_confidence', 'strategy_winning_option', 'strategy_outcomes',
            'strategy_time_remaining_minutes', 'strategy_scan_timestamp'
        ]
        
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for market in markets:
                try:
                    def safe_json_field(field_value):
                        if isinstance(field_value, (list, dict)):
                            return json.dumps(field_value)
                        elif isinstance(field_value, str):
                            return field_value
                        else:
                            return str(field_value) if field_value is not None else ''
                    
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
                        market.get('openInterest', ''),
                        # 策略字段
                        market.get('strategy_confidence', ''),
                        market.get('strategy_winning_option', ''),
                        safe_json_field(market.get('strategy_outcomes', '')),
                        market.get('strategy_time_remaining_minutes', ''),
                        market.get('strategy_scan_timestamp', '')
                    ]
                    
                    writer.writerow(row)
                    
                except Exception as e:
                    logger.error(f"处理市场 {market.get('id', 'unknown')} 时出错: {e}")
                    continue
        
        logger.info(f"💾 符合条件的市场数据已保存到: {full_path}")
        return full_path

    def generate_strategy_report(self, markets: List[Dict]) -> Dict[str, Any]:
        """生成策略报告"""
        current_time = datetime.now()
        
        # 按置信度排序
        sorted_markets = sorted(markets, key=lambda x: x.get('strategy_confidence', 0), reverse=True)
        
        # 统计信息
        total_volume = 0
        total_liquidity = 0
        confidence_distribution = {'0.90-0.91': 0, '0.91-0.92': 0, '0.92-0.93': 0, '0.93-0.94': 0, '0.94-0.95': 0}
        winning_options = {'Yes': 0, 'No': 0, 'Other': 0}
        
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
            
            # 统计置信度分布
            confidence = market.get('strategy_confidence', 0)
            if 0.90 <= confidence < 0.91:
                confidence_distribution['0.90-0.91'] += 1
            elif 0.91 <= confidence < 0.92:
                confidence_distribution['0.91-0.92'] += 1
            elif 0.92 <= confidence < 0.93:
                confidence_distribution['0.92-0.93'] += 1
            elif 0.93 <= confidence < 0.94:
                confidence_distribution['0.93-0.94'] += 1
            elif 0.94 <= confidence <= 0.95:
                confidence_distribution['0.94-0.95'] += 1
            
            # 统计胜出选项
            winning_option = market.get('strategy_winning_option', '')
            if winning_option in ['Yes', 'No']:
                winning_options[winning_option] += 1
            else:
                winning_options['Other'] += 1
        
        report = {
            "timestamp": current_time.isoformat(),
            "strategy_name": "紧急高置信度策略",
            "strategy_parameters": {
                "time_threshold_minutes": self.time_threshold_minutes,
                "min_confidence": self.min_confidence,
                "max_confidence": self.max_confidence
            },
            "total_qualifying_markets": len(markets),
            "total_volume": total_volume,
            "total_liquidity": total_liquidity,
            "confidence_distribution": confidence_distribution,
            "winning_options_distribution": winning_options,
            "top_opportunities": []
        }
        
        # 添加前10个最佳机会
        for i, market in enumerate(sorted_markets[:10]):
            report["top_opportunities"].append({
                "rank": i + 1,
                "id": market.get('id', ''),
                "question": market.get('question', '')[:100],
                "confidence": market.get('strategy_confidence', 0),
                "winning_option": market.get('strategy_winning_option', ''),
                "time_remaining_minutes": market.get('strategy_time_remaining_minutes', 0),
                "volume": market.get('volumeNum', 0),
                "liquidity": market.get('liquidityNum', 0),
                "endDate": market.get('endDate', '')
            })
        
        return report

    def print_strategy_summary(self, markets: List[Dict]):
        """打印策略摘要"""
        report = self.generate_strategy_report(markets)
        
        print("\n" + "="*80)
        print(f"⚡ 紧急高置信度策略报告")
        print("="*80)
        print(f"🕐 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 策略参数:")
        print(f"   时间阈值: {self.time_threshold_minutes} 分钟")
        print(f"   胜率范围: {self.min_confidence:.1%} - {self.max_confidence:.1%}")
        print(f"🎯 发现机会: {report['total_qualifying_markets']} 个")
        print(f"💰 总交易量: ${report['total_volume']:,.2f}")
        print(f"💧 总流动性: ${report['total_liquidity']:,.2f}")
        
        if report['confidence_distribution']:
            print(f"\n📈 置信度分布:")
            for range_str, count in report['confidence_distribution'].items():
                if count > 0:
                    print(f"   {range_str}: {count} 个市场")
        
        if report['winning_options_distribution']:
            print(f"\n🎲 胜出选项分布:")
            for option, count in report['winning_options_distribution'].items():
                if count > 0:
                    print(f"   {option}: {count} 个市场")
        
        if report['top_opportunities']:
            print(f"\n🔥 最佳机会 (前{len(report['top_opportunities'])}个):")
            for opp in report['top_opportunities']:
                print(f"   {opp['rank']:2d}. [{opp['time_remaining_minutes']:2d}分钟] {opp['confidence']:.3f} ({opp['winning_option']})")
                print(f"       {opp['question']}")
                print(f"       ID: {opp['id']} | 交易量: ${opp['volume']:,.0f}")
        
        print("="*80)

    def run_strategy(self, save_to_file: bool = True) -> Dict[str, Any]:
        """运行策略"""
        start_time = datetime.now()
        logger.info(f"🚀 开始运行紧急高置信度策略")
        
        try:
            # 扫描符合条件的市场
            qualifying_markets = self.scan_urgent_markets()
            
            # 保存到文件
            csv_file = None
            if save_to_file and qualifying_markets:
                csv_file = self.save_qualifying_markets(qualifying_markets)
            
            # 生成报告
            report = self.generate_strategy_report(qualifying_markets)
            
            # 保存JSON报告
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_file = os.path.join(self.data_dir, "reports", f"urgent_high_confidence_report_{timestamp}.json")
                with open(json_file, "w", encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"📊 策略报告已保存到: {json_file}")
            
            # 打印摘要
            self.print_strategy_summary(qualifying_markets)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "qualifying_markets_count": len(qualifying_markets),
                "csv_file": csv_file,
                "duration_seconds": duration,
                "report": report,
                "markets": qualifying_markets
            }
            
        except Exception as e:
            logger.error(f"策略运行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "qualifying_markets_count": 0
            }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="紧急高置信度策略 - 扫描10分钟内结束且胜率在0.9-0.95之间的市场")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件，仅显示结果")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    strategy = UrgentHighConfidenceStrategy(data_dir=args.data_dir)
    
    result = strategy.run_strategy(save_to_file=not args.no_save)
    
    if result["success"]:
        print(f"\n✅ 策略运行完成!")
        print(f"   发现机会: {result['qualifying_markets_count']} 个")
        print(f"   耗时: {result['duration_seconds']:.1f} 秒")
        if result.get("csv_file"):
            print(f"   数据文件: {result['csv_file']}")
    else:
        print(f"\n❌ 策略运行失败: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()