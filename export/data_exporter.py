#!/usr/bin/env python3
"""
数据导出工具 - 将Polymarket数据导出为各种格式
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

class DataExporter:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        
    def get_all_tag_data(self) -> Dict[str, Dict[str, Any]]:
        """获取所有标签的数据"""
        tag_dir = os.path.join(self.data_dir, "tag")
        if not os.path.exists(tag_dir):
            return {}
            
        all_data = {}
        
        for tag_name in os.listdir(tag_dir):
            tag_path = os.path.join(tag_dir, tag_name)
            if not os.path.isdir(tag_path):
                continue
                
            # 获取最新的文件
            events_files = [f for f in os.listdir(tag_path) if f.startswith("events_") and f.endswith(".csv")]
            markets_files = [f for f in os.listdir(tag_path) if f.startswith("markets_") and f.endswith(".csv")]
            summary_files = [f for f in os.listdir(tag_path) if f.startswith("summary_") and f.endswith(".json")]
            
            if not (events_files and markets_files and summary_files):
                continue
                
            latest_events = sorted(events_files)[-1]
            latest_markets = sorted(markets_files)[-1]
            latest_summary = sorted(summary_files)[-1]
            
            try:
                # 读取数据
                events_df = pd.read_csv(os.path.join(tag_path, latest_events))
                markets_df = pd.read_csv(os.path.join(tag_path, latest_markets))
                
                with open(os.path.join(tag_path, latest_summary), "r") as f:
                    summary = json.load(f)
                
                all_data[tag_name] = {
                    "events": events_df,
                    "markets": markets_df,
                    "summary": summary
                }
                
            except Exception as e:
                print(f"⚠️  读取标签 {tag_name} 数据失败: {e}")
                continue
                
        return all_data
    
    def export_to_excel(self, output_file: str, tags: Optional[List[str]] = None):
        """导出到Excel文件"""
        all_data = self.get_all_tag_data()
        
        if tags:
            all_data = {k: v for k, v in all_data.items() if k in tags}
        
        if not all_data:
            print("❌ 没有数据可导出")
            return
            
        print(f"📊 导出 {len(all_data)} 个标签的数据到Excel...")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 创建概览表
            overview_data = []
            for tag_name, data in all_data.items():
                summary = data["summary"]
                overview_data.append({
                    "标签": tag_name,
                    "标签名称": summary.get("tag_label", tag_name),
                    "事件数量": summary.get("events_count", 0),
                    "市场数量": summary.get("markets_count", 0),
                    "总交易量": summary.get("total_volume", 0),
                    "总流动性": summary.get("total_liquidity", 0),
                    "同步时间": summary.get("sync_timestamp", "")
                })
            
            overview_df = pd.DataFrame(overview_data)
            overview_df.to_excel(writer, sheet_name="概览", index=False)
            
            # 为每个标签创建工作表
            for tag_name, data in all_data.items():
                # 限制工作表名称长度
                sheet_name = tag_name[:30] if len(tag_name) > 30 else tag_name
                
                # 事件数据
                events_df = data["events"].copy()
                if not events_df.empty:
                    events_df.to_excel(writer, sheet_name=f"{sheet_name}_事件", index=False)
                
                # 市场数据
                markets_df = data["markets"].copy()
                if not markets_df.empty:
                    markets_df.to_excel(writer, sheet_name=f"{sheet_name}_市场", index=False)
        
        print(f"✅ Excel文件已保存: {output_file}")
    
    def export_to_json(self, output_file: str, tags: Optional[List[str]] = None):
        """导出到JSON文件"""
        all_data = self.get_all_tag_data()
        
        if tags:
            all_data = {k: v for k, v in all_data.items() if k in tags}
        
        if not all_data:
            print("❌ 没有数据可导出")
            return
            
        print(f"📊 导出 {len(all_data)} 个标签的数据到JSON...")
        
        # 转换DataFrame为字典
        export_data = {}
        for tag_name, data in all_data.items():
            export_data[tag_name] = {
                "summary": data["summary"],
                "events": data["events"].to_dict("records"),
                "markets": data["markets"].to_dict("records")
            }
        
        # 添加元数据
        export_data["_metadata"] = {
            "export_time": datetime.now().isoformat(),
            "tags_count": len(all_data),
            "total_events": sum(len(data["events"]) for data in all_data.values()),
            "total_markets": sum(len(data["markets"]) for data in all_data.values())
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON文件已保存: {output_file}")
    
    def export_to_csv_bundle(self, output_dir: str, tags: Optional[List[str]] = None):
        """导出到CSV文件包"""
        all_data = self.get_all_tag_data()
        
        if tags:
            all_data = {k: v for k, v in all_data.items() if k in tags}
        
        if not all_data:
            print("❌ 没有数据可导出")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        print(f"📊 导出 {len(all_data)} 个标签的数据到CSV包...")
        
        # 创建概览文件
        overview_data = []
        all_events = []
        all_markets = []
        
        for tag_name, data in all_data.items():
            summary = data["summary"]
            overview_data.append({
                "tag_slug": tag_name,
                "tag_label": summary.get("tag_label", tag_name),
                "events_count": summary.get("events_count", 0),
                "markets_count": summary.get("markets_count", 0),
                "total_volume": summary.get("total_volume", 0),
                "total_liquidity": summary.get("total_liquidity", 0),
                "sync_timestamp": summary.get("sync_timestamp", "")
            })
            
            # 添加标签信息到事件和市场数据
            events_df = data["events"].copy()
            if not events_df.empty:
                events_df["tag_slug"] = tag_name
                all_events.append(events_df)
            
            markets_df = data["markets"].copy()
            if not markets_df.empty:
                markets_df["tag_slug"] = tag_name
                all_markets.append(markets_df)
        
        # 保存概览
        overview_df = pd.DataFrame(overview_data)
        overview_df.to_csv(os.path.join(output_dir, "overview.csv"), index=False)
        
        # 保存合并的事件和市场数据
        if all_events:
            combined_events = pd.concat(all_events, ignore_index=True)
            combined_events.to_csv(os.path.join(output_dir, "all_events.csv"), index=False)
        
        if all_markets:
            combined_markets = pd.concat(all_markets, ignore_index=True)
            combined_markets.to_csv(os.path.join(output_dir, "all_markets.csv"), index=False)
        
        # 为每个标签创建单独的CSV文件
        for tag_name, data in all_data.items():
            tag_dir = os.path.join(output_dir, "by_tag", tag_name)
            os.makedirs(tag_dir, exist_ok=True)
            
            if not data["events"].empty:
                data["events"].to_csv(os.path.join(tag_dir, "events.csv"), index=False)
            
            if not data["markets"].empty:
                data["markets"].to_csv(os.path.join(tag_dir, "markets.csv"), index=False)
            
            # 保存摘要
            with open(os.path.join(tag_dir, "summary.json"), "w", encoding="utf-8") as f:
                json.dump(data["summary"], f, indent=2, ensure_ascii=False)
        
        print(f"✅ CSV包已保存到: {output_dir}")
    
    def export_summary_report(self, output_file: str):
        """导出摘要报告"""
        all_data = self.get_all_tag_data()
        
        if not all_data:
            print("❌ 没有数据可导出")
            return
            
        print(f"📊 生成摘要报告...")
        
        # 计算统计数据
        total_events = sum(len(data["events"]) for data in all_data.values())
        total_markets = sum(len(data["markets"]) for data in all_data.values())
        total_volume = sum(data["summary"].get("total_volume", 0) for data in all_data.values())
        total_liquidity = sum(data["summary"].get("total_liquidity", 0) for data in all_data.values())
        
        # 按交易量排序标签
        sorted_tags = sorted(
            all_data.items(),
            key=lambda x: x[1]["summary"].get("total_volume", 0),
            reverse=True
        )
        
        # 生成报告
        report = []
        report.append("Polymarket 数据摘要报告")
        report.append("=" * 50)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("📊 总体统计:")
        report.append(f"  标签数量: {len(all_data)}")
        report.append(f"  事件数量: {total_events}")
        report.append(f"  市场数量: {total_markets}")
        report.append(f"  总交易量: ${total_volume:,}")
        report.append(f"  总流动性: ${total_liquidity:,}")
        report.append("")
        report.append("🏷️  标签排行 (按交易量):")
        
        for i, (tag_name, data) in enumerate(sorted_tags[:20]):
            summary = data["summary"]
            volume = summary.get("total_volume", 0)
            events_count = summary.get("events_count", 0)
            markets_count = summary.get("markets_count", 0)
            
            report.append(f"  {i+1:2d}. {tag_name:15s} - ${volume:>12,} ({events_count:2d} 事件, {markets_count:3d} 市场)")
        
        report.append("")
        report.append("📈 详细标签信息:")
        report.append("-" * 80)
        
        for tag_name, data in sorted_tags:
            summary = data["summary"]
            report.append(f"\n🏷️  {tag_name} ({summary.get('tag_label', tag_name)})")
            report.append(f"   事件数量: {summary.get('events_count', 0)}")
            report.append(f"   市场数量: {summary.get('markets_count', 0)}")
            report.append(f"   交易量: ${summary.get('total_volume', 0):,}")
            report.append(f"   流动性: ${summary.get('total_liquidity', 0):,}")
            
            # 显示热门事件
            top_events = summary.get("top_events", [])
            if top_events:
                report.append("   热门事件:")
                for event in top_events[:3]:
                    report.append(f"     - {event.get('title', 'N/A')} (${event.get('volume', 0):,})")
        
        # 保存报告
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        
        print(f"✅ 摘要报告已保存: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Polymarket数据导出工具")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--format", choices=["excel", "json", "csv", "report"], 
                       default="excel", help="导出格式")
    parser.add_argument("--output", help="输出文件/目录")
    parser.add_argument("--tags", nargs="+", help="指定要导出的标签")
    
    args = parser.parse_args()
    
    exporter = DataExporter(args.data_dir)
    
    # 生成默认输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format == "excel":
        output_file = args.output or f"polymarket_data_{timestamp}.xlsx"
        exporter.export_to_excel(output_file, args.tags)
        
    elif args.format == "json":
        output_file = args.output or f"polymarket_data_{timestamp}.json"
        exporter.export_to_json(output_file, args.tags)
        
    elif args.format == "csv":
        output_dir = args.output or f"polymarket_csv_{timestamp}"
        exporter.export_to_csv_bundle(output_dir, args.tags)
        
    elif args.format == "report":
        output_file = args.output or f"polymarket_report_{timestamp}.txt"
        exporter.export_summary_report(output_file)

if __name__ == "__main__":
    main()