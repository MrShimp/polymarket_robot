#!/usr/bin/env python3
"""
Polymarket 同步调度器
自动化定时同步，支持多种调度策略
"""

import os
import time
import json
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import logging
from sync.polymarket_sync import PolymarketSynchronizer
from sync.sync_monitor import SyncMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncScheduler:
    """同步调度器"""
    
    def __init__(self, config_file: str = "sync_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.synchronizer = PolymarketSynchronizer(
            base_url=self.config['sync_settings']['base_url'],
            data_dir=self.config['sync_settings']['data_dir'],
            use_mock_data=self.config['sync_settings']['use_mock_data']
        )
        self.monitor = SyncMonitor(data_dir=self.config['sync_settings']['data_dir'])
        
        self.is_running = False
        self.scheduler_thread = None
        self.last_sync_result = None
        self.sync_history = []
        
        # 回调函数
        self.on_sync_success: Optional[Callable] = None
        self.on_sync_failure: Optional[Callable] = None
        self.on_schedule_start: Optional[Callable] = None
        self.on_schedule_stop: Optional[Callable] = None
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {self.config_file} 不存在，使用默认配置")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "sync_settings": {
                "base_url": "https://gamma-api.polymarket.com",
                "data_dir": "./data",
                "use_mock_data": True,
                "batch_size": 100,
                "request_delay": 0.5,
                "timeout": 10,
                "max_retries": 3
            },
            "sync_schedule": {
                "enabled": True,
                "interval_hours": 6,
                "specific_times": ["06:00", "12:00", "18:00", "00:00"],
                "timezone": "UTC"
            },
            "notification_settings": {
                "email_alerts": False,
                "slack_webhook": "",
                "discord_webhook": "",
                "alert_on_sync_failure": True,
                "alert_on_large_changes": True,
                "change_threshold_percent": 20
            }
        }
    
    def setup_schedule(self):
        """设置调度任务"""
        schedule.clear()  # 清除现有任务
        
        schedule_config = self.config.get('sync_schedule', {})
        
        if not schedule_config.get('enabled', False):
            logger.info("调度功能已禁用")
            return
        
        # 按间隔调度
        interval_hours = schedule_config.get('interval_hours')
        if interval_hours:
            schedule.every(interval_hours).hours.do(self.run_sync_job)
            logger.info(f"设置间隔调度: 每 {interval_hours} 小时执行一次")
        
        # 按特定时间调度
        specific_times = schedule_config.get('specific_times', [])
        for time_str in specific_times:
            schedule.every().day.at(time_str).do(self.run_sync_job)
            logger.info(f"设置定时调度: 每天 {time_str} 执行")
        
        logger.info(f"调度设置完成，共 {len(schedule.jobs)} 个任务")
    
    def run_sync_job(self):
        """执行同步任务"""
        job_start_time = datetime.now()
        logger.info("开始执行调度同步任务...")
        
        try:
            # 检查数据质量
            quality_before = self.monitor.check_data_quality()
            
            # 执行同步
            sync_result = self.synchronizer.sync_all_markets()
            
            # 检查同步后的数据质量
            quality_after = self.monitor.check_data_quality()
            
            # 记录同步历史
            sync_record = {
                'timestamp': job_start_time.isoformat(),
                'duration_seconds': (datetime.now() - job_start_time).total_seconds(),
                'success': True,
                'quality_before': quality_before['quality_score'],
                'quality_after': quality_after['quality_score'],
                'events_synced': self.synchronizer.sync_stats.get('total_events', 0),
                'markets_synced': self.synchronizer.sync_stats.get('total_markets', 0),
                'tags_processed': self.synchronizer.sync_stats.get('total_tags', 0)
            }
            
            self.sync_history.append(sync_record)
            self.last_sync_result = sync_record
            
            # 检查是否有大幅变化
            self.check_for_significant_changes(quality_before, quality_after)
            
            # 成功回调
            if self.on_sync_success:
                self.on_sync_success(sync_record)
            
            logger.info(f"调度同步任务完成，耗时: {sync_record['duration_seconds']:.1f} 秒")
            
        except Exception as e:
            # 记录失败
            sync_record = {
                'timestamp': job_start_time.isoformat(),
                'duration_seconds': (datetime.now() - job_start_time).total_seconds(),
                'success': False,
                'error': str(e),
                'events_synced': 0,
                'markets_synced': 0,
                'tags_processed': 0
            }
            
            self.sync_history.append(sync_record)
            self.last_sync_result = sync_record
            
            # 失败回调
            if self.on_sync_failure:
                self.on_sync_failure(sync_record)
            
            logger.error(f"调度同步任务失败: {e}")
            
            # 发送失败通知
            self.send_failure_notification(sync_record)
    
    def check_for_significant_changes(self, quality_before: Dict, quality_after: Dict):
        """检查是否有显著变化"""
        threshold = self.config.get('notification_settings', {}).get('change_threshold_percent', 20)
        
        # 检查质量分数变化
        quality_change = abs(quality_after['quality_score'] - quality_before['quality_score'])
        
        if quality_change > threshold:
            logger.warning(f"数据质量发生显著变化: {quality_before['quality_score']} -> {quality_after['quality_score']}")
            self.send_change_notification(quality_before, quality_after)
    
    def send_failure_notification(self, sync_record: Dict):
        """发送失败通知"""
        if not self.config.get('notification_settings', {}).get('alert_on_sync_failure', False):
            return
        
        message = f"""
🚨 Polymarket 同步失败

时间: {sync_record['timestamp']}
错误: {sync_record.get('error', 'Unknown error')}
持续时间: {sync_record['duration_seconds']:.1f} 秒

请检查日志文件获取详细信息。
        """.strip()
        
        self.send_notification("同步失败警报", message)
    
    def send_change_notification(self, quality_before: Dict, quality_after: Dict):
        """发送变化通知"""
        if not self.config.get('notification_settings', {}).get('alert_on_large_changes', False):
            return
        
        message = f"""
📊 Polymarket 数据质量变化

同步前质量分数: {quality_before['quality_score']}/100
同步后质量分数: {quality_after['quality_score']}/100

变化详情:
- 问题数量: {len(quality_before.get('issues', []))} -> {len(quality_after.get('issues', []))}
- 警告数量: {len(quality_before.get('warnings', []))} -> {len(quality_after.get('warnings', []))}
        """.strip()
        
        self.send_notification("数据质量变化", message)
    
    def send_notification(self, title: str, message: str):
        """发送通知"""
        notification_config = self.config.get('notification_settings', {})
        
        # Slack 通知
        slack_webhook = notification_config.get('slack_webhook')
        if slack_webhook:
            self.send_slack_notification(slack_webhook, title, message)
        
        # Discord 通知
        discord_webhook = notification_config.get('discord_webhook')
        if discord_webhook:
            self.send_discord_notification(discord_webhook, title, message)
        
        # 邮件通知
        if notification_config.get('email_alerts', False):
            self.send_email_notification(title, message)
    
    def send_slack_notification(self, webhook_url: str, title: str, message: str):
        """发送 Slack 通知"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://polymarket.com/"
            }
            
            payload = {
                "text": f"*{title}*\n```{message}```"
            }
            
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("Slack 通知发送成功")
            else:
                logger.error(f"Slack 通知发送失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"发送 Slack 通知失败: {e}")
    
    def send_discord_notification(self, webhook_url: str, title: str, message: str):
        """发送 Discord 通知"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://polymarket.com/"
            }
            
            payload = {
                "content": f"**{title}**\n```{message}```"
            }
            
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 204:
                logger.info("Discord 通知发送成功")
            else:
                logger.error(f"Discord 通知发送失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"发送 Discord 通知失败: {e}")
    
    def send_email_notification(self, title: str, message: str):
        """发送邮件通知"""
        # 这里可以集成邮件发送功能
        logger.info(f"邮件通知: {title}")
        logger.info(message)
    
    def start_scheduler(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行")
            return
        
        self.setup_schedule()
        self.is_running = True
        
        def run_scheduler():
            logger.info("调度器已启动")
            if self.on_schedule_start:
                self.on_schedule_start()
            
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
            
            logger.info("调度器已停止")
            if self.on_schedule_stop:
                self.on_schedule_stop()
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("调度器线程已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        if not self.is_running:
            logger.warning("调度器未在运行")
            return
        
        self.is_running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("调度器已停止")
    
    def get_schedule_status(self) -> Dict:
        """获取调度状态"""
        return {
            'is_running': self.is_running,
            'jobs_count': len(schedule.jobs),
            'jobs': [
                {
                    'job': str(job.job_func),
                    'next_run': job.next_run.isoformat() if job.next_run else None,
                    'interval': str(job.interval) if hasattr(job, 'interval') else None
                }
                for job in schedule.jobs
            ],
            'last_sync_result': self.last_sync_result,
            'sync_history_count': len(self.sync_history)
        }
    
    def get_sync_statistics(self) -> Dict:
        """获取同步统计"""
        if not self.sync_history:
            return {'message': '暂无同步历史'}
        
        successful_syncs = [s for s in self.sync_history if s['success']]
        failed_syncs = [s for s in self.sync_history if not s['success']]
        
        stats = {
            'total_syncs': len(self.sync_history),
            'successful_syncs': len(successful_syncs),
            'failed_syncs': len(failed_syncs),
            'success_rate': len(successful_syncs) / len(self.sync_history) * 100,
            'average_duration': sum(s['duration_seconds'] for s in successful_syncs) / len(successful_syncs) if successful_syncs else 0,
            'total_events_synced': sum(s.get('events_synced', 0) for s in successful_syncs),
            'total_markets_synced': sum(s.get('markets_synced', 0) for s in successful_syncs),
            'last_24h_syncs': len([s for s in self.sync_history if 
                                 datetime.fromisoformat(s['timestamp']) > datetime.now() - timedelta(days=1)])
        }
        
        return stats
    
    def manual_sync(self) -> Dict:
        """手动触发同步"""
        logger.info("手动触发同步...")
        
        try:
            sync_result = self.synchronizer.sync_all_markets()
            
            manual_record = {
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'manual': True,
                'events_synced': self.synchronizer.sync_stats.get('total_events', 0),
                'markets_synced': self.synchronizer.sync_stats.get('total_markets', 0),
                'tags_processed': self.synchronizer.sync_stats.get('total_tags', 0)
            }
            
            self.sync_history.append(manual_record)
            self.last_sync_result = manual_record
            
            logger.info("手动同步完成")
            return manual_record
            
        except Exception as e:
            manual_record = {
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'manual': True,
                'error': str(e)
            }
            
            self.sync_history.append(manual_record)
            self.last_sync_result = manual_record
            
            logger.error(f"手动同步失败: {e}")
            return manual_record
    
    def save_sync_history(self, filepath: str = None):
        """保存同步历史"""
        if not filepath:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(self.config['sync_settings']['data_dir'], 
                                  "reports", f"sync_history_{timestamp}.json")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        history_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_records': len(self.sync_history),
            'statistics': self.get_sync_statistics(),
            'history': self.sync_history
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"同步历史已保存到: {filepath}")
        return filepath

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Polymarket同步调度器')
    parser.add_argument('--action', choices=['start', 'stop', 'status', 'sync', 'stats', 'history'], 
                       default='status', help='执行的操作')
    parser.add_argument('--config', default='sync_config.json', help='配置文件路径')
    parser.add_argument('--daemon', action='store_true', help='以守护进程模式运行')
    
    args = parser.parse_args()
    
    scheduler = SyncScheduler(config_file=args.config)
    
    if args.action == 'start':
        scheduler.start_scheduler()
        
        if args.daemon:
            logger.info("以守护进程模式运行，按 Ctrl+C 停止")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                scheduler.stop_scheduler()
        else:
            logger.info("调度器已启动，使用 'stop' 命令停止")
    
    elif args.action == 'stop':
        scheduler.stop_scheduler()
    
    elif args.action == 'status':
        status = scheduler.get_schedule_status()
        print(f"调度器状态: {'运行中' if status['is_running'] else '已停止'}")
        print(f"调度任务数: {status['jobs_count']}")
        
        if status['jobs']:
            print("\n调度任务:")
            for i, job in enumerate(status['jobs'], 1):
                print(f"  {i}. {job['job']}")
                print(f"     下次运行: {job['next_run'] or 'N/A'}")
        
        if status['last_sync_result']:
            result = status['last_sync_result']
            print(f"\n最后同步:")
            print(f"  时间: {result['timestamp']}")
            print(f"  状态: {'成功' if result['success'] else '失败'}")
            if result['success']:
                print(f"  事件: {result.get('events_synced', 0)}")
                print(f"  市场: {result.get('markets_synced', 0)}")
    
    elif args.action == 'sync':
        result = scheduler.manual_sync()
        if result['success']:
            print("手动同步成功")
            print(f"  事件: {result.get('events_synced', 0)}")
            print(f"  市场: {result.get('markets_synced', 0)}")
        else:
            print(f"手动同步失败: {result.get('error', 'Unknown error')}")
    
    elif args.action == 'stats':
        stats = scheduler.get_sync_statistics()
        print("同步统计:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    elif args.action == 'history':
        filepath = scheduler.save_sync_history()
        print(f"同步历史已导出到: {filepath}")

if __name__ == "__main__":
    main()