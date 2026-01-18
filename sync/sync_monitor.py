#!/usr/bin/env python3
"""
Polymarket 同步监控器
监控同步状态，生成报告，管理数据文件
"""

import os
import json
import time
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncMonitor:
    """同步监控器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.tag_dir = os.path.join(data_dir, "tag")
        self.reports_dir = os.path.join(data_dir, "reports")
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        status = {
            'last_sync_time': None,
            'total_tags': 0,
            'total_events': 0,
            'total_markets': 0,
            'tag_details': {},
            'data_freshness': None,
            'disk_usage': self.get_disk_usage()
        }
        
        if not os.path.exists(self.tag_dir):
            return status
        
        # 统计标签目录
        tag_dirs = [d for d in os.listdir(self.tag_dir) 
                   if os.path.isdir(os.path.join(self.tag_dir, d))]
        
        status['total_tags'] = len(tag_dirs)
        
        latest_sync_time = None
        
        # 分析每个标签目录
        for tag_name in tag_dirs:
            tag_path = os.path.join(self.tag_dir, tag_name)
            tag_info = self.analyze_tag_directory(tag_path)
            status['tag_details'][tag_name] = tag_info
            
            # 更新总计数
            status['total_events'] += tag_info['events_count']
            status['total_markets'] += tag_info['markets_count']
            
            # 找到最新的同步时间
            if tag_info['last_update'] and (not latest_sync_time or tag_info['last_update'] > latest_sync_time):
                latest_sync_time = tag_info['last_update']
        
        status['last_sync_time'] = latest_sync_time.isoformat() if latest_sync_time else None
        
        # 计算数据新鲜度
        if latest_sync_time:
            age_hours = (datetime.now() - latest_sync_time).total_seconds() / 3600
            status['data_freshness'] = {
                'age_hours': age_hours,
                'status': 'fresh' if age_hours < 6 else 'stale' if age_hours < 24 else 'old'
            }
        
        return status
    
    def analyze_tag_directory(self, tag_path: str) -> Dict:
        """分析标签目录"""
        info = {
            'events_count': 0,
            'markets_count': 0,
            'last_update': None,
            'file_count': 0,
            'total_size_mb': 0
        }
        
        if not os.path.exists(tag_path):
            return info
        
        files = os.listdir(tag_path)
        info['file_count'] = len(files)
        
        # 计算总大小
        total_size = 0
        latest_time = None
        
        for filename in files:
            file_path = os.path.join(tag_path, filename)
            if os.path.isfile(file_path):
                # 文件大小
                total_size += os.path.getsize(file_path)
                
                # 最后修改时间
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if not latest_time or mtime > latest_time:
                    latest_time = mtime
                
                # 统计事件和市场数量（从最新文件）
                if filename.startswith('events_') and filename.endswith('.csv'):
                    try:
                        df = pd.read_csv(file_path)
                        info['events_count'] = len(df)
                    except:
                        pass
                elif filename.startswith('markets_') and filename.endswith('.csv'):
                    try:
                        df = pd.read_csv(file_path)
                        info['markets_count'] = len(df)
                    except:
                        pass
        
        info['total_size_mb'] = total_size / (1024 * 1024)
        info['last_update'] = latest_time
        
        return info
    
    def get_disk_usage(self) -> Dict:
        """获取磁盘使用情况"""
        usage = {
            'total_size_mb': 0,
            'tag_dir_size_mb': 0,
            'reports_dir_size_mb': 0
        }
        
        # 计算标签目录大小
        if os.path.exists(self.tag_dir):
            usage['tag_dir_size_mb'] = self.get_directory_size(self.tag_dir)
        
        # 计算报告目录大小
        if os.path.exists(self.reports_dir):
            usage['reports_dir_size_mb'] = self.get_directory_size(self.reports_dir)
        
        usage['total_size_mb'] = usage['tag_dir_size_mb'] + usage['reports_dir_size_mb']
        
        return usage
    
    def get_directory_size(self, directory: str) -> float:
        """获取目录大小（MB）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)
    
    def get_latest_sync_report(self) -> Optional[Dict]:
        """获取最新的同步报告"""
        if not os.path.exists(self.reports_dir):
            return None
        
        # 查找最新的报告文件
        report_files = glob.glob(os.path.join(self.reports_dir, "sync_report_*.json"))
        if not report_files:
            return None
        
        latest_file = max(report_files, key=os.path.getmtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取报告文件失败: {e}")
            return None
    
    def generate_status_report(self) -> str:
        """生成状态报告"""
        status = self.get_sync_status()
        latest_report = self.get_latest_sync_report()
        
        freshness_text = 'N/A'
        if status['data_freshness']:
            age_hours = status['data_freshness']['age_hours']
            freshness_text = f"{status['data_freshness']['status']} ({age_hours:.1f}h前)"
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    同步状态监控报告                          ║
╠══════════════════════════════════════════════════════════════╣
║ 📊 当前状态                                                  ║
║   最后同步: {status['last_sync_time'] or 'N/A'}             ║
║   数据新鲜度: {freshness_text}                               ║
║   标签数量: {status['total_tags']}                          ║
║   事件总数: {status['total_events']:,}                      ║
║   市场总数: {status['total_markets']:,}                     ║
║                                                              ║
║ 💾 存储使用                                                  ║
║   总大小: {status['disk_usage']['total_size_mb']:.1f} MB     ║
║   标签数据: {status['disk_usage']['tag_dir_size_mb']:.1f} MB ║
║   报告数据: {status['disk_usage']['reports_dir_size_mb']:.1f} MB ║
║                                                              ║
║ 🏷️  热门标签                                                 ║"""
        
        # 按事件数量排序标签
        sorted_tags = sorted(
            status['tag_details'].items(),
            key=lambda x: x[1]['events_count'],
            reverse=True
        )
        
        for i, (tag_name, tag_info) in enumerate(sorted_tags[:5], 1):
            report += f"""
║   {i}. {tag_name}: {tag_info['events_count']} 事件, {tag_info['markets_count']} 市场 ║"""
        
        if latest_report:
            sync_info = latest_report.get('sync_info', {})
            report += f"""
║                                                              ║
║ 📈 最近同步统计                                              ║
║   同步耗时: {sync_info.get('duration_seconds', 0):.1f} 秒    ║
║   处理事件: {sync_info.get('total_events', 0):,}            ║
║   处理市场: {sync_info.get('total_markets', 0):,}           ║"""
        
        report += f"""
╚══════════════════════════════════════════════════════════════╝
        """
        
        return report.strip()
    
    def check_data_quality(self) -> Dict:
        """检查数据质量"""
        issues = []
        warnings = []
        
        status = self.get_sync_status()
        
        # 检查数据新鲜度
        if status['data_freshness']:
            age_hours = status['data_freshness']['age_hours']
            if age_hours > 24:
                issues.append(f"数据过期: {age_hours:.1f} 小时未更新")
            elif age_hours > 12:
                warnings.append(f"数据较旧: {age_hours:.1f} 小时未更新")
        
        # 检查标签数量
        if status['total_tags'] == 0:
            issues.append("没有找到任何标签数据")
        elif status['total_tags'] < 5:
            warnings.append(f"标签数量较少: 只有 {status['total_tags']} 个标签")
        
        # 检查事件数量
        if status['total_events'] == 0:
            issues.append("没有找到任何事件数据")
        elif status['total_events'] < 10:
            warnings.append(f"事件数量较少: 只有 {status['total_events']} 个事件")
        
        # 检查磁盘使用
        total_size = status['disk_usage']['total_size_mb']
        if total_size > 1000:  # 1GB
            warnings.append(f"磁盘使用较大: {total_size:.1f} MB")
        
        # 检查标签分布
        tag_details = status['tag_details']
        if tag_details:
            event_counts = [info['events_count'] for info in tag_details.values()]
            max_events = max(event_counts)
            min_events = min(event_counts)
            
            if max_events > min_events * 10:  # 分布不均
                warnings.append("标签事件分布不均匀")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'quality_score': max(0, 100 - len(issues) * 30 - len(warnings) * 10)
        }
    
    def cleanup_old_data(self, days: int = 7) -> Dict:
        """清理旧数据"""
        cleaned_files = 0
        freed_space_mb = 0
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 清理标签目录
        if os.path.exists(self.tag_dir):
            for tag_name in os.listdir(self.tag_dir):
                tag_path = os.path.join(self.tag_dir, tag_name)
                if os.path.isdir(tag_path):
                    for filename in os.listdir(tag_path):
                        file_path = os.path.join(tag_path, filename)
                        if os.path.isfile(file_path):
                            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if mtime < cutoff_time:
                                file_size = os.path.getsize(file_path) / (1024 * 1024)
                                os.remove(file_path)
                                cleaned_files += 1
                                freed_space_mb += file_size
        
        # 清理报告目录
        if os.path.exists(self.reports_dir):
            for filename in os.listdir(self.reports_dir):
                file_path = os.path.join(self.reports_dir, filename)
                if os.path.isfile(file_path):
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mtime < cutoff_time:
                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                        os.remove(file_path)
                        cleaned_files += 1
                        freed_space_mb += file_size
        
        return {
            'cleaned_files': cleaned_files,
            'freed_space_mb': freed_space_mb
        }
    
    def export_tag_summary(self, tag_name: str) -> Optional[str]:
        """导出标签摘要"""
        tag_path = os.path.join(self.tag_dir, tag_name)
        if not os.path.exists(tag_path):
            return None
        
        # 查找最新的摘要文件
        summary_files = glob.glob(os.path.join(tag_path, "summary_*.json"))
        if not summary_files:
            return None
        
        latest_summary = max(summary_files, key=os.path.getmtime)
        
        try:
            with open(latest_summary, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # 生成可读的摘要
            report = f"""
标签: {tag_name}
事件数量: {summary_data.get('events_count', 0)}
市场数量: {summary_data.get('markets_count', 0)}
总交易量: ${summary_data.get('total_volume', 0):,}
总流动性: ${summary_data.get('total_liquidity', 0):,}
同步时间: {summary_data.get('sync_timestamp', 'N/A')}

热门事件:
"""
            
            for i, event in enumerate(summary_data.get('top_events', []), 1):
                report += f"{i}. {event.get('title', 'N/A')} (${event.get('volume', 0):,})\n"
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"读取摘要文件失败: {e}")
            return None
    
    def monitor_real_time(self, interval: int = 300):
        """实时监控"""
        logger.info(f"开始实时监控，刷新间隔: {interval} 秒")
        
        while True:
            try:
                # 清屏并显示状态
                os.system('clear' if os.name == 'posix' else 'cls')
                
                print(self.generate_status_report())
                
                # 检查数据质量
                quality = self.check_data_quality()
                if quality['issues']:
                    print(f"\n❌ 发现问题:")
                    for issue in quality['issues']:
                        print(f"   - {issue}")
                
                if quality['warnings']:
                    print(f"\n⚠️  警告:")
                    for warning in quality['warnings']:
                        print(f"   - {warning}")
                
                print(f"\n📊 数据质量评分: {quality['quality_score']}/100")
                print(f"\n最后更新: {datetime.now().strftime('%H:%M:%S')}")
                print("按 Ctrl+C 退出监控")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控错误: {e}")
                time.sleep(10)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Polymarket同步监控器')
    parser.add_argument('--action', choices=['status', 'monitor', 'cleanup', 'quality', 'export'], 
                       default='status', help='执行的操作')
    parser.add_argument('--data-dir', default='./data', help='数据目录路径')
    parser.add_argument('--interval', type=int, default=300, help='监控刷新间隔(秒)')
    parser.add_argument('--cleanup-days', type=int, default=7, help='清理N天前的文件')
    parser.add_argument('--tag', help='导出特定标签的摘要')
    
    args = parser.parse_args()
    
    monitor = SyncMonitor(data_dir=args.data_dir)
    
    if args.action == 'status':
        print(monitor.generate_status_report())
    
    elif args.action == 'monitor':
        monitor.monitor_real_time(interval=args.interval)
    
    elif args.action == 'cleanup':
        result = monitor.cleanup_old_data(days=args.cleanup_days)
        print(f"清理完成:")
        print(f"  删除文件: {result['cleaned_files']} 个")
        print(f"  释放空间: {result['freed_space_mb']:.1f} MB")
    
    elif args.action == 'quality':
        quality = monitor.check_data_quality()
        print(f"数据质量评分: {quality['quality_score']}/100")
        
        if quality['issues']:
            print(f"\n❌ 问题:")
            for issue in quality['issues']:
                print(f"   - {issue}")
        
        if quality['warnings']:
            print(f"\n⚠️  警告:")
            for warning in quality['warnings']:
                print(f"   - {warning}")
    
    elif args.action == 'export':
        if not args.tag:
            print("请指定要导出的标签名称 (--tag)")
            return
        
        summary = monitor.export_tag_summary(args.tag)
        if summary:
            print(summary)
        else:
            print(f"未找到标签 '{args.tag}' 的摘要数据")

if __name__ == "__main__":
    main()