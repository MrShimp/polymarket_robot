#!/usr/bin/env python3
"""
Polymarket 数据分析器
分析同步的市场数据，生成洞察报告
"""

import os
import json
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.tag_dir = os.path.join(data_dir, "tag")
        self.reports_dir = os.path.join(data_dir, "reports")
        self.analysis_dir = os.path.join(data_dir, "analysis")
        
        # 确保分析目录存在
        os.makedirs(self.analysis_dir, exist_ok=True)
    
    def load_all_events_data(self) -> pd.DataFrame:
        """加载所有事件数据"""
        all_events = []
        
        if not os.path.exists(self.tag_dir):
            logger.warning("标签目录不存在")
            return pd.DataFrame()
        
        # 遍历所有标签目录
        for tag_name in os.listdir(self.tag_dir):
            tag_path = os.path.join(self.tag_dir, tag_name)
            if not os.path.isdir(tag_path):
                continue
            
            # 查找最新的事件文件
            events_files = glob.glob(os.path.join(tag_path, "events_*.csv"))
            if not events_files:
                continue
            
            latest_file = max(events_files, key=os.path.getmtime)
            
            try:
                df = pd.read_csv(latest_file)
                df['tag'] = tag_name  # 添加标签信息
                all_events.append(df)
            except Exception as e:
                logger.error(f"读取文件 {latest_file} 失败: {e}")
        
        if all_events:
            combined_df = pd.concat(all_events, ignore_index=True)
            logger.info(f"加载了 {len(combined_df)} 个事件数据")
            return combined_df
        else:
            logger.warning("没有找到事件数据")
            return pd.DataFrame()
    
    def load_all_markets_data(self) -> pd.DataFrame:
        """加载所有市场数据"""
        all_markets = []
        
        if not os.path.exists(self.tag_dir):
            logger.warning("标签目录不存在")
            return pd.DataFrame()
        
        # 遍历所有标签目录
        for tag_name in os.listdir(self.tag_dir):
            tag_path = os.path.join(self.tag_dir, tag_name)
            if not os.path.isdir(tag_path):
                continue
            
            # 查找最新的市场文件
            markets_files = glob.glob(os.path.join(tag_path, "markets_*.csv"))
            if not markets_files:
                continue
            
            latest_file = max(markets_files, key=os.path.getmtime)
            
            try:
                df = pd.read_csv(latest_file)
                df['tag'] = tag_name  # 添加标签信息
                all_markets.append(df)
            except Exception as e:
                logger.error(f"读取文件 {latest_file} 失败: {e}")
        
        if all_markets:
            combined_df = pd.concat(all_markets, ignore_index=True)
            logger.info(f"加载了 {len(combined_df)} 个市场数据")
            return combined_df
        else:
            logger.warning("没有找到市场数据")
            return pd.DataFrame()
    
    def analyze_market_distribution(self, events_df: pd.DataFrame) -> Dict:
        """分析市场分布"""
        if events_df.empty:
            return {}
        
        analysis = {
            'total_events': int(len(events_df)),
            'total_volume': float(events_df['volume'].sum()),
            'total_liquidity': float(events_df['liquidity'].sum()),
            'average_volume': float(events_df['volume'].mean()),
            'median_volume': float(events_df['volume'].median()),
            'volume_std': float(events_df['volume'].std()),
            
            # 按标签分布
            'distribution_by_tag': {},
            'top_tags_by_volume': [],
            'top_tags_by_count': [],
            
            # 按类别分布
            'distribution_by_category': {},
            
            # 时间分析
            'time_analysis': {}
        }
        
        # 按标签分析
        tag_stats = events_df.groupby('tag').agg({
            'volume': ['count', 'sum', 'mean'],
            'liquidity': 'sum'
        }).round(2)
        
        for tag in tag_stats.index:
            analysis['distribution_by_tag'][tag] = {
                'count': int(tag_stats.loc[tag, ('volume', 'count')]),
                'total_volume': float(tag_stats.loc[tag, ('volume', 'sum')]),
                'avg_volume': float(tag_stats.loc[tag, ('volume', 'mean')]),
                'total_liquidity': float(tag_stats.loc[tag, ('liquidity', 'sum')])
            }
        
        # 热门标签
        analysis['top_tags_by_volume'] = sorted(
            analysis['distribution_by_tag'].items(),
            key=lambda x: x[1]['total_volume'],
            reverse=True
        )[:10]
        
        analysis['top_tags_by_count'] = sorted(
            analysis['distribution_by_tag'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]
        
        # 按类别分析
        if 'category' in events_df.columns:
            category_stats = events_df.groupby('category').agg({
                'volume': ['count', 'sum', 'mean'],
                'liquidity': 'sum'
            }).round(2)
            
            for category in category_stats.index:
                analysis['distribution_by_category'][category] = {
                    'count': int(category_stats.loc[category, ('volume', 'count')]),
                    'total_volume': float(category_stats.loc[category, ('volume', 'sum')]),
                    'avg_volume': float(category_stats.loc[category, ('volume', 'mean')]),
                    'total_liquidity': float(category_stats.loc[category, ('liquidity', 'sum')])
                }
        
        # 时间分析
        if 'end_date' in events_df.columns:
            try:
                events_df['end_date_parsed'] = pd.to_datetime(events_df['end_date'], utc=True)
                now = pd.Timestamp.now(tz='UTC')
                
                # 按到期时间分组
                events_df['days_to_expiry'] = (events_df['end_date_parsed'] - now).dt.days
                
                analysis['time_analysis'] = {
                    'expiring_soon': int(len(events_df[events_df['days_to_expiry'] <= 7])),
                    'expiring_this_month': int(len(events_df[events_df['days_to_expiry'] <= 30])),
                    'expiring_this_year': int(len(events_df[events_df['days_to_expiry'] <= 365])),
                    'average_days_to_expiry': float(events_df['days_to_expiry'].mean()),
                    'median_days_to_expiry': float(events_df['days_to_expiry'].median())
                }
            except Exception as e:
                logger.error(f"时间分析失败: {e}")
                analysis['time_analysis'] = {'error': str(e)}
        
        return analysis
    
    def analyze_market_trends(self, events_df: pd.DataFrame) -> Dict:
        """分析市场趋势"""
        if events_df.empty:
            return {}
        
        trends = {
            'volume_trends': {},
            'liquidity_trends': {},
            'growth_analysis': {},
            'correlation_analysis': {}
        }
        
        # 交易量趋势
        volume_percentiles = np.percentile(events_df['volume'], [25, 50, 75, 90, 95])
        trends['volume_trends'] = {
            'q25': float(volume_percentiles[0]),
            'median': float(volume_percentiles[1]),
            'q75': float(volume_percentiles[2]),
            'p90': float(volume_percentiles[3]),
            'p95': float(volume_percentiles[4]),
            'high_volume_events': len(events_df[events_df['volume'] > volume_percentiles[3]]),
            'low_volume_events': len(events_df[events_df['volume'] < volume_percentiles[0]])
        }
        
        # 流动性趋势
        liquidity_percentiles = np.percentile(events_df['liquidity'], [25, 50, 75, 90, 95])
        trends['liquidity_trends'] = {
            'q25': float(liquidity_percentiles[0]),
            'median': float(liquidity_percentiles[1]),
            'q75': float(liquidity_percentiles[2]),
            'p90': float(liquidity_percentiles[3]),
            'p95': float(liquidity_percentiles[4]),
            'high_liquidity_events': len(events_df[events_df['liquidity'] > liquidity_percentiles[3]]),
            'low_liquidity_events': len(events_df[events_df['liquidity'] < liquidity_percentiles[0]])
        }
        
        # 增长分析
        if len(events_df) > 1:
            volume_growth = events_df['volume'].pct_change().dropna()
            trends['growth_analysis'] = {
                'volume_volatility': float(volume_growth.std()),
                'positive_growth_events': len(volume_growth[volume_growth > 0]),
                'negative_growth_events': len(volume_growth[volume_growth < 0])
            }
        
        # 相关性分析
        numeric_columns = ['volume', 'liquidity']
        if all(col in events_df.columns for col in numeric_columns):
            correlation_matrix = events_df[numeric_columns].corr()
            trends['correlation_analysis'] = {
                'volume_liquidity_correlation': float(correlation_matrix.loc['volume', 'liquidity'])
            }
        
        return trends
    
    def identify_opportunities(self, events_df: pd.DataFrame, markets_df: pd.DataFrame) -> Dict:
        """识别交易机会"""
        opportunities = {
            'high_volume_low_liquidity': [],
            'emerging_trends': [],
            'undervalued_markets': [],
            'arbitrage_opportunities': [],
            'risk_warnings': []
        }
        
        if events_df.empty:
            return opportunities
        
        # 高交易量低流动性机会
        volume_threshold = events_df['volume'].quantile(0.8)
        liquidity_threshold = events_df['liquidity'].quantile(0.3)
        
        high_vol_low_liq = events_df[
            (events_df['volume'] > volume_threshold) & 
            (events_df['liquidity'] < liquidity_threshold)
        ]
        
        for _, event in high_vol_low_liq.iterrows():
            opportunities['high_volume_low_liquidity'].append({
                'title': event.get('title', 'N/A'),
                'tag': event.get('tag', 'N/A'),
                'volume': float(event['volume']),
                'liquidity': float(event['liquidity']),
                'volume_to_liquidity_ratio': float(event['volume'] / max(event['liquidity'], 1))
            })
        
        # 新兴趋势识别
        tag_volumes = events_df.groupby('tag')['volume'].sum().sort_values(ascending=False)
        emerging_tags = tag_volumes.head(5)
        
        for tag, volume in emerging_tags.items():
            tag_events = events_df[events_df['tag'] == tag]
            opportunities['emerging_trends'].append({
                'tag': tag,
                'total_volume': float(volume),
                'event_count': len(tag_events),
                'avg_volume': float(tag_events['volume'].mean()),
                'growth_potential': 'high' if volume > events_df['volume'].mean() * 2 else 'medium'
            })
        
        # 风险警告
        # 低流动性警告
        very_low_liquidity = events_df[events_df['liquidity'] < events_df['liquidity'].quantile(0.1)]
        for _, event in very_low_liquidity.head(5).iterrows():
            opportunities['risk_warnings'].append({
                'type': 'low_liquidity',
                'title': event.get('title', 'N/A'),
                'tag': event.get('tag', 'N/A'),
                'liquidity': float(event['liquidity']),
                'warning': '流动性极低，可能难以退出'
            })
        
        # 异常高交易量警告
        very_high_volume = events_df[events_df['volume'] > events_df['volume'].quantile(0.95)]
        for _, event in very_high_volume.head(3).iterrows():
            opportunities['risk_warnings'].append({
                'type': 'high_volume',
                'title': event.get('title', 'N/A'),
                'tag': event.get('tag', 'N/A'),
                'volume': float(event['volume']),
                'warning': '交易量异常高，可能存在市场操纵'
            })
        
        return opportunities
    
    def generate_insights_report(self, events_df: pd.DataFrame, markets_df: pd.DataFrame) -> Dict:
        """生成洞察报告"""
        logger.info("生成数据洞察报告...")
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'data_summary': {
                'events_count': len(events_df),
                'markets_count': len(markets_df),
                'unique_tags': events_df['tag'].nunique() if not events_df.empty else 0,
                'data_freshness': self.calculate_data_freshness(events_df)
            },
            'market_distribution': self.analyze_market_distribution(events_df),
            'market_trends': self.analyze_market_trends(events_df),
            'opportunities': self.identify_opportunities(events_df, markets_df),
            'recommendations': self.generate_recommendations(events_df, markets_df)
        }
        
        return report
    
    def calculate_data_freshness(self, events_df: pd.DataFrame) -> Dict:
        """计算数据新鲜度"""
        if events_df.empty or 'sync_timestamp' not in events_df.columns:
            return {'status': 'unknown', 'message': '无法确定数据新鲜度'}
        
        try:
            latest_sync = pd.to_datetime(events_df['sync_timestamp']).max()
            age_hours = (pd.Timestamp.now() - latest_sync).total_seconds() / 3600
            
            if age_hours < 1:
                status = 'very_fresh'
                message = f'{age_hours:.1f} 小时前更新'
            elif age_hours < 6:
                status = 'fresh'
                message = f'{age_hours:.1f} 小时前更新'
            elif age_hours < 24:
                status = 'stale'
                message = f'{age_hours:.1f} 小时前更新'
            else:
                status = 'old'
                message = f'{age_hours/24:.1f} 天前更新'
            
            return {
                'status': status,
                'age_hours': age_hours,
                'message': message,
                'last_sync': latest_sync.isoformat()
            }
        except Exception as e:
            return {'status': 'error', 'message': f'计算失败: {e}'}
    
    def generate_recommendations(self, events_df: pd.DataFrame, markets_df: pd.DataFrame) -> List[Dict]:
        """生成推荐建议"""
        recommendations = []
        
        if events_df.empty:
            return [{'type': 'warning', 'message': '没有数据可供分析'}]
        
        # 基于交易量的建议
        high_volume_tags = events_df.groupby('tag')['volume'].sum().nlargest(3)
        for tag, volume in high_volume_tags.items():
            recommendations.append({
                'type': 'opportunity',
                'category': 'high_volume',
                'message': f'标签 "{tag}" 交易量较高 (${volume:,.0f})，值得关注',
                'priority': 'high',
                'action': f'深入分析 {tag} 相关市场'
            })
        
        # 基于流动性的建议
        low_liquidity_count = len(events_df[events_df['liquidity'] < events_df['liquidity'].quantile(0.2)])
        if low_liquidity_count > len(events_df) * 0.3:
            recommendations.append({
                'type': 'warning',
                'category': 'liquidity',
                'message': f'{low_liquidity_count} 个事件流动性较低，交易时需谨慎',
                'priority': 'medium',
                'action': '避免大额交易，或等待流动性改善'
            })
        
        # 基于多样性的建议
        tag_diversity = events_df['tag'].nunique()
        if tag_diversity < 5:
            recommendations.append({
                'type': 'suggestion',
                'category': 'diversification',
                'message': f'当前只有 {tag_diversity} 个标签，建议扩大关注范围',
                'priority': 'low',
                'action': '关注更多类别的市场以分散风险'
            })
        
        # 基于时间的建议
        if 'end_date' in events_df.columns:
            try:
                events_df['end_date_parsed'] = pd.to_datetime(events_df['end_date'], utc=True)
                expiring_soon = len(events_df[
                    (events_df['end_date_parsed'] - pd.Timestamp.now(tz='UTC')).dt.days <= 7
                ])
                
                if expiring_soon > 0:
                    recommendations.append({
                        'type': 'urgent',
                        'category': 'timing',
                        'message': f'{expiring_soon} 个事件将在一周内到期',
                        'priority': 'high',
                        'action': '尽快决定是否参与即将到期的市场'
                    })
            except Exception:
                pass
        
        return recommendations
    
    def save_analysis_report(self, report: Dict, filename: str = None) -> str:
        """保存分析报告"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"analysis_report_{timestamp}.json"
        
        filepath = os.path.join(self.analysis_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"分析报告已保存到: {filepath}")
        return filepath
    
    def generate_text_report(self, report: Dict) -> str:
        """生成文本格式报告"""
        summary = report['data_summary']
        distribution = report['market_distribution']
        trends = report['market_trends']
        opportunities = report['opportunities']
        recommendations = report['recommendations']
        
        text_report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    Polymarket 数据分析报告                   ║
╠══════════════════════════════════════════════════════════════╣
║ 📊 数据概览                                                  ║
║   事件数量: {summary['events_count']:,}                     ║
║   市场数量: {summary['markets_count']:,}                    ║
║   标签数量: {summary['unique_tags']}                        ║
║   数据新鲜度: {summary['data_freshness']['message']}        ║
║                                                              ║
║ 💰 市场分布                                                  ║
║   总交易量: ${distribution.get('total_volume', 0):,.0f}     ║
║   总流动性: ${distribution.get('total_liquidity', 0):,.0f}  ║
║   平均交易量: ${distribution.get('average_volume', 0):,.0f} ║
║                                                              ║
║ 🏷️  热门标签 (按交易量)                                      ║"""
        
        for i, (tag, stats) in enumerate(distribution.get('top_tags_by_volume', [])[:5], 1):
            text_report += f"""
║   {i}. {tag}: ${stats['total_volume']:,.0f}                 ║"""
        
        text_report += f"""
║                                                              ║
║ 📈 市场趋势                                                  ║
║   交易量中位数: ${trends.get('volume_trends', {}).get('median', 0):,.0f} ║
║   高交易量事件: {trends.get('volume_trends', {}).get('high_volume_events', 0)} 个 ║
║   流动性中位数: ${trends.get('liquidity_trends', {}).get('median', 0):,.0f} ║
║                                                              ║
║ 🎯 交易机会                                                  ║
║   高量低流动性: {len(opportunities.get('high_volume_low_liquidity', []))} 个 ║
║   新兴趋势: {len(opportunities.get('emerging_trends', []))} 个     ║
║   风险警告: {len(opportunities.get('risk_warnings', []))} 个       ║
║                                                              ║
║ 💡 推荐建议                                                  ║"""
        
        for i, rec in enumerate(recommendations[:3], 1):
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            text_report += f"""
║   {i}. {priority_icon} {rec['message'][:40]}...              ║"""
        
        text_report += f"""
╚══════════════════════════════════════════════════════════════╝
        """
        
        return text_report.strip()
    
    def run_full_analysis(self) -> Tuple[Dict, str]:
        """运行完整分析"""
        logger.info("开始完整数据分析...")
        
        # 加载数据
        events_df = self.load_all_events_data()
        markets_df = self.load_all_markets_data()
        
        # 生成报告
        report = self.generate_insights_report(events_df, markets_df)
        
        # 保存报告
        report_file = self.save_analysis_report(report)
        
        # 生成文本报告
        text_report = self.generate_text_report(report)
        
        # 保存文本报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        text_file = os.path.join(self.analysis_dir, f"analysis_report_{timestamp}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        logger.info("数据分析完成")
        return report, text_report

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Polymarket数据分析器')
    parser.add_argument('--data-dir', default='./data', help='数据目录路径')
    parser.add_argument('--output', choices=['json', 'text', 'both'], default='both', help='输出格式')
    parser.add_argument('--save', action='store_true', help='保存报告到文件')
    
    args = parser.parse_args()
    
    analyzer = DataAnalyzer(data_dir=args.data_dir)
    
    # 运行分析
    report, text_report = analyzer.run_full_analysis()
    
    # 输出结果
    if args.output in ['text', 'both']:
        print(text_report)
    
    if args.output in ['json', 'both']:
        print(f"\n详细JSON报告已保存到分析目录")
    
    if not args.save:
        print(f"\n📁 分析结果已保存到: {analyzer.analysis_dir}")

if __name__ == "__main__":
    main()