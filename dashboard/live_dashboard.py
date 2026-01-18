#!/usr/bin/env python3
"""
实时监控仪表板 - 展示Polymarket数据的实时状态
"""

import os
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

class LiveDashboard:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        
    def get_latest_sync_data(self) -> Dict[str, Any]:
        """获取最新的同步数据"""
        reports_dir = os.path.join(self.data_dir, "reports")
        if not os.path.exists(reports_dir):
            return {}
            
        # 找到最新的报告文件
        report_files = [f for f in os.listdir(reports_dir) if f.startswith("sync_report_") and f.endswith(".json")]
        if not report_files:
            return {}
            
        latest_file = sorted(report_files)[-1]
        with open(os.path.join(reports_dir, latest_file), "r") as f:
            return json.load(f)
    
    def get_tag_summaries(self) -> Dict[str, Dict[str, Any]]:
        """获取所有标签的最新摘要"""
        tag_dir = os.path.join(self.data_dir, "tag")
        if not os.path.exists(tag_dir):
            return {}
            
        summaries = {}
        for tag_name in os.listdir(tag_dir):
            tag_path = os.path.join(tag_dir, tag_name)
            if not os.path.isdir(tag_path):
                continue
                
            # 找到最新的摘要文件
            summary_files = [f for f in os.listdir(tag_path) if f.startswith("summary_") and f.endswith(".json")]
            if summary_files:
                latest_summary = sorted(summary_files)[-1]
                with open(os.path.join(tag_path, latest_summary), "r") as f:
                    summaries[tag_name] = json.load(f)
                    
        return summaries
    
    def calculate_system_health(self, sync_data: Dict, tag_summaries: Dict) -> Dict[str, Any]:
        """计算系统健康状态"""
        if not sync_data:
            return {"status": "unknown", "score": 0, "issues": ["无同步数据"]}
            
        issues = []
        score = 100
        
        # 检查数据新鲜度
        if "end_time" in sync_data:
            sync_time = datetime.fromisoformat(sync_data["end_time"])
            age_hours = (datetime.now() - sync_time).total_seconds() / 3600
            
            if age_hours > 24:
                issues.append(f"数据过期 ({age_hours:.1f}小时前)")
                score -= 30
            elif age_hours > 6:
                issues.append(f"数据较旧 ({age_hours:.1f}小时前)")
                score -= 15
        
        # 检查数据完整性
        if sync_data.get("events_count", 0) < 10:
            issues.append("事件数量过少")
            score -= 20
            
        if sync_data.get("markets_count", 0) < 50:
            issues.append("市场数量过少")
            score -= 20
            
        if len(tag_summaries) < 5:
            issues.append("标签分类不足")
            score -= 15
        
        # 确定状态
        if score >= 90:
            status = "excellent"
        elif score >= 70:
            status = "good"
        elif score >= 50:
            status = "warning"
        else:
            status = "critical"
            
        return {
            "status": status,
            "score": max(0, score),
            "issues": issues
        }
    
    def format_currency(self, amount: int) -> str:
        """格式化货币显示"""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        else:
            return f"${amount}"
    
    def print_dashboard(self):
        """打印仪表板"""
        # 清屏
        os.system('clear' if os.name == 'posix' else 'cls')
        
        sync_data = self.get_latest_sync_data()
        tag_summaries = self.get_tag_summaries()
        health = self.calculate_system_health(sync_data, tag_summaries)
        
        # 标题
        print("╔" + "="*78 + "╗")
        print("║" + " "*25 + "🚀 Polymarket 实时监控仪表板" + " "*25 + "║")
        print("╠" + "="*78 + "╣")
        
        # 系统状态
        status_icons = {
            "excellent": "🟢",
            "good": "🟡", 
            "warning": "🟠",
            "critical": "🔴",
            "unknown": "⚪"
        }
        
        status_icon = status_icons.get(health["status"], "⚪")
        print(f"║ 🖥️  系统状态: {status_icon} {health['status'].upper()} ({health['score']}/100)" + " "*(78-len(f"🖥️  系统状态: {status_icon} {health['status'].upper()} ({health['score']}/100)")) + "║")
        
        if health["issues"]:
            for issue in health["issues"][:3]:  # 最多显示3个问题
                print(f"║    ⚠️  {issue}" + " "*(78-len(f"    ⚠️  {issue}")) + "║")
        
        print("║" + " "*78 + "║")
        
        # 数据概览
        if sync_data:
            sync_mode = sync_data.get("sync_mode", "unknown")
            events_count = sync_data.get("events_count", 0)
            markets_count = sync_data.get("markets_count", 0)
            tags_count = len(tag_summaries)
            
            if "end_time" in sync_data:
                sync_time = datetime.fromisoformat(sync_data["end_time"])
                time_ago = datetime.now() - sync_time
                if time_ago.total_seconds() < 3600:
                    time_str = f"{int(time_ago.total_seconds()/60)}分钟前"
                else:
                    time_str = f"{int(time_ago.total_seconds()/3600)}小时前"
            else:
                time_str = "未知"
            
            print(f"║ 📊 数据概览 ({sync_mode}模式)" + " "*(78-len(f"📊 数据概览 ({sync_mode}模式)")) + "║")
            print(f"║    标签: {tags_count:3d} | 事件: {events_count:3d} | 市场: {markets_count:3d} | 更新: {time_str}" + " "*(78-len(f"    标签: {tags_count:3d} | 事件: {events_count:3d} | 市场: {markets_count:3d} | 更新: {time_str}")) + "║")
        else:
            print("║ 📊 数据概览: 无数据" + " "*59 + "║")
        
        print("║" + " "*78 + "║")
        
        # 热门标签
        if tag_summaries:
            print("║ 🏷️  热门标签 (按交易量)" + " "*51 + "║")
            
            # 按交易量排序
            sorted_tags = sorted(
                tag_summaries.items(),
                key=lambda x: x[1].get("total_volume", 0),
                reverse=True
            )
            
            for i, (tag_name, summary) in enumerate(sorted_tags[:8]):
                volume = summary.get("total_volume", 0)
                events = summary.get("events_count", 0)
                markets = summary.get("markets_count", 0)
                
                volume_str = self.format_currency(volume)
                line = f"    {i+1:2d}. {tag_name:12s} - {volume_str:>8s} ({events:2d}事件, {markets:2d}市场)"
                print(f"║{line}" + " "*(78-len(line)) + "║")
        else:
            print("║ 🏷️  热门标签: 无数据" + " "*55 + "║")
        
        print("║" + " "*78 + "║")
        
        # 实时统计
        if tag_summaries:
            total_volume = sum(s.get("total_volume", 0) for s in tag_summaries.values())
            total_events = sum(s.get("events_count", 0) for s in tag_summaries.values())
            total_markets = sum(s.get("markets_count", 0) for s in tag_summaries.values())
            avg_volume = total_volume / len(tag_summaries) if tag_summaries else 0
            
            print("║ 💰 交易统计" + " "*64 + "║")
            print(f"║    总交易量: {self.format_currency(total_volume):>10s} | 平均: {self.format_currency(int(avg_volume)):>8s}" + " "*(78-len(f"    总交易量: {self.format_currency(total_volume):>10s} | 平均: {self.format_currency(int(avg_volume)):>8s}")) + "║")
            print(f"║    总事件数: {total_events:>10d} | 总市场: {total_markets:>8d}" + " "*(78-len(f"    总事件数: {total_events:>10d} | 总市场: {total_markets:>8d}")) + "║")
        
        print("╚" + "="*78 + "╝")
        
        # 底部信息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"最后刷新: {current_time} | 按 Ctrl+C 退出监控模式")
    
    def run_monitor(self, interval: int = 30):
        """运行监控模式"""
        print("🚀 启动实时监控模式...")
        print(f"📊 刷新间隔: {interval} 秒")
        print("⌨️  按 Ctrl+C 退出\n")
        
        try:
            while True:
                self.print_dashboard()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
    
    def print_static_report(self):
        """打印静态报告"""
        self.print_dashboard()
        
        # 额外的详细信息
        sync_data = self.get_latest_sync_data()
        tag_summaries = self.get_tag_summaries()
        
        if sync_data and "tag_data" in sync_data:
            print("\n📈 详细标签统计:")
            print("-" * 80)
            
            for tag_name, tag_info in sync_data["tag_data"].items():
                if tag_info.get("events"):
                    events_count = len(tag_info["events"])
                    markets_count = len(tag_info["markets"])
                    volume = tag_info.get("total_volume", 0)
                    liquidity = tag_info.get("total_liquidity", 0)
                    
                    print(f"{tag_name:15s} | {events_count:3d} 事件 | {markets_count:3d} 市场 | "
                          f"交易量: {self.format_currency(volume):>8s} | "
                          f"流动性: {self.format_currency(liquidity):>8s}")

def main():
    parser = argparse.ArgumentParser(description="Polymarket实时监控仪表板")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--monitor", action="store_true", help="启动监控模式")
    parser.add_argument("--interval", type=int, default=30, help="监控刷新间隔(秒)")
    
    args = parser.parse_args()
    
    dashboard = LiveDashboard(args.data_dir)
    
    if args.monitor:
        dashboard.run_monitor(args.interval)
    else:
        dashboard.print_static_report()

if __name__ == "__main__":
    main()