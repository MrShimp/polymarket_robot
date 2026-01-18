#!/usr/bin/env python3
"""
Polymarket系统管理器 - 统一管理所有功能
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any

class PolymarketManager:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.scripts = {
            "sync": "sync/enhanced_sync.py",
            "dashboard": "dashboard/live_dashboard.py", 
            "export": "export/data_exporter.py",
            "monitor": "sync/sync_monitor.py",
            "analyze": "export/data_analyzer.py"
        }
    
    def run_command(self, script: str, args: List[str] = None) -> int:
        """运行指定的脚本命令"""
        if script not in self.scripts:
            print(f"❌ 未知脚本: {script}")
            return 1
            
        script_file = self.scripts[script]
        if not os.path.exists(script_file):
            print(f"❌ 脚本文件不存在: {script_file}")
            return 1
        
        cmd = ["python3", script_file]
        if args:
            cmd.extend(args)
            
        print(f"🚀 执行命令: {' '.join(cmd)}")
        return subprocess.call(cmd)
    
    def show_status(self):
        """显示系统状态"""
        print("╔" + "="*60 + "╗")
        print("║" + " "*18 + "Polymarket 系统状态" + " "*18 + "║")
        print("╠" + "="*60 + "╣")
        
        # 检查数据目录
        if os.path.exists(self.data_dir):
            print(f"║ 📁 数据目录: {self.data_dir:<40} ✅ ║")
            
            # 检查子目录
            subdirs = ["tag", "reports", "offline", "analysis"]
            for subdir in subdirs:
                path = os.path.join(self.data_dir, subdir)
                status = "✅" if os.path.exists(path) else "❌"
                print(f"║    └─ {subdir}/" + " "*(35-len(subdir)) + f"{status} ║")
        else:
            print(f"║ 📁 数据目录: {self.data_dir:<40} ❌ ║")
        
        print("║" + " "*60 + "║")
        
        # 检查脚本文件
        print("║ 🔧 系统组件:" + " "*44 + "║")
        for name, script in self.scripts.items():
            status = "✅" if os.path.exists(script) else "❌"
            print(f"║    {name:10s} - {script:<30s} {status} ║")
        
        print("║" + " "*60 + "║")
        
        # 检查最新数据
        reports_dir = os.path.join(self.data_dir, "reports")
        if os.path.exists(reports_dir):
            report_files = [f for f in os.listdir(reports_dir) if f.startswith("sync_report_")]
            if report_files:
                latest_report = sorted(report_files)[-1]
                timestamp = latest_report.replace("sync_report_", "").replace(".json", "")
                print(f"║ 📊 最新同步: {timestamp:<40} ✅ ║")
            else:
                print("║ 📊 最新同步: 无数据" + " "*40 + "❌ ║")
        else:
            print("║ 📊 最新同步: 无数据" + " "*40 + "❌ ║")
        
        print("╚" + "="*60 + "╝")
    
    def show_help(self):
        """显示帮助信息"""
        print("🚀 Polymarket 系统管理器")
        print("=" * 50)
        print()
        print("📋 可用命令:")
        print()
        print("🔄 数据同步:")
        print("  sync --offline              # 离线模式同步")
        print("  sync                         # API模式同步")
        print("  sync --generate-offline      # 生成新的离线数据")
        print()
        print("📊 监控和分析:")
        print("  dashboard                    # 显示静态仪表板")
        print("  dashboard --monitor          # 启动实时监控")
        print("  monitor --action status      # 查看同步状态")
        print("  analyze --output text        # 数据分析报告")
        print()
        print("📤 数据导出:")
        print("  export --format excel        # 导出Excel文件")
        print("  export --format json         # 导出JSON文件")
        print("  export --format csv          # 导出CSV包")
        print("  export --format report       # 生成摘要报告")
        print()
        print("🛠️  系统管理:")
        print("  status                       # 显示系统状态")
        print("  init                         # 初始化系统")
        print("  clean                        # 清理旧数据")
        print("  help                         # 显示此帮助")
        print()
        print("💡 使用示例:")
        print("  python3 polymarket_manager.py sync --offline")
        print("  python3 polymarket_manager.py dashboard --monitor")
        print("  python3 polymarket_manager.py export --format excel --tags crypto bitcoin")
    
    def init_system(self):
        """初始化系统"""
        print("🔧 初始化Polymarket系统...")
        
        # 创建目录结构
        dirs = [
            self.data_dir,
            os.path.join(self.data_dir, "tag"),
            os.path.join(self.data_dir, "reports"),
            os.path.join(self.data_dir, "offline"),
            os.path.join(self.data_dir, "analysis"),
            os.path.join(self.data_dir, "exports"),
            os.path.join(self.data_dir, "sync_logs")
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 创建目录: {dir_path}")
        
        # 生成初始离线数据
        print("📊 生成初始离线数据...")
        result = self.run_command("sync", ["--generate-offline"])
        
        if result == 0:
            print("✅ 系统初始化完成!")
            print("💡 运行 'python3 polymarket_manager.py sync --offline' 开始同步")
        else:
            print("❌ 系统初始化失败")
    
    def clean_old_data(self):
        """清理旧数据"""
        print("🧹 清理旧数据...")
        
        # 清理策略：保留最新的3个文件
        dirs_to_clean = [
            os.path.join(self.data_dir, "reports"),
            os.path.join(self.data_dir, "analysis")
        ]
        
        total_cleaned = 0
        
        for dir_path in dirs_to_clean:
            if not os.path.exists(dir_path):
                continue
                
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
            if len(files) <= 3:
                continue
                
            # 按修改时间排序，删除旧文件
            files_with_time = [(f, os.path.getmtime(os.path.join(dir_path, f))) for f in files]
            files_with_time.sort(key=lambda x: x[1], reverse=True)
            
            files_to_delete = files_with_time[3:]  # 保留最新的3个
            
            for file_name, _ in files_to_delete:
                file_path = os.path.join(dir_path, file_name)
                try:
                    os.remove(file_path)
                    print(f"🗑️  删除: {file_path}")
                    total_cleaned += 1
                except Exception as e:
                    print(f"❌ 删除失败 {file_path}: {e}")
        
        # 清理标签目录中的旧文件
        tag_dir = os.path.join(self.data_dir, "tag")
        if os.path.exists(tag_dir):
            for tag_name in os.listdir(tag_dir):
                tag_path = os.path.join(tag_dir, tag_name)
                if not os.path.isdir(tag_path):
                    continue
                    
                # 每种类型保留最新的2个文件
                file_types = ["events_", "markets_", "summary_"]
                
                for file_type in file_types:
                    files = [f for f in os.listdir(tag_path) if f.startswith(file_type)]
                    if len(files) <= 2:
                        continue
                        
                    files_with_time = [(f, os.path.getmtime(os.path.join(tag_path, f))) for f in files]
                    files_with_time.sort(key=lambda x: x[1], reverse=True)
                    
                    files_to_delete = files_with_time[2:]  # 保留最新的2个
                    
                    for file_name, _ in files_to_delete:
                        file_path = os.path.join(tag_path, file_name)
                        try:
                            os.remove(file_path)
                            total_cleaned += 1
                        except Exception as e:
                            print(f"❌ 删除失败 {file_path}: {e}")
        
        print(f"✅ 清理完成，删除了 {total_cleaned} 个文件")
    
    def quick_start(self):
        """快速开始"""
        print("🚀 Polymarket 快速开始")
        print("=" * 40)
        print()
        print("1️⃣  初始化系统...")
        self.init_system()
        print()
        
        print("2️⃣  运行离线同步...")
        result = self.run_command("sync", ["--offline"])
        if result != 0:
            print("❌ 同步失败")
            return
        print()
        
        print("3️⃣  显示仪表板...")
        self.run_command("dashboard")
        print()
        
        print("4️⃣  生成摘要报告...")
        self.run_command("export", ["--format", "report"])
        print()
        
        print("✅ 快速开始完成!")
        print("💡 运行 'python3 polymarket_manager.py dashboard --monitor' 启动实时监控")

def main():
    parser = argparse.ArgumentParser(description="Polymarket系统管理器")
    parser.add_argument("command", nargs="?", default="help",
                       choices=["sync", "dashboard", "export", "monitor", "analyze", 
                               "status", "init", "clean", "help", "quickstart"],
                       help="要执行的命令")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    
    # 解析已知参数，其余传递给子命令
    args, unknown = parser.parse_known_args()
    
    manager = PolymarketManager(args.data_dir)
    
    if args.command == "help":
        manager.show_help()
    elif args.command == "status":
        manager.show_status()
    elif args.command == "init":
        manager.init_system()
    elif args.command == "clean":
        manager.clean_old_data()
    elif args.command == "quickstart":
        manager.quick_start()
    elif args.command in manager.scripts:
        # 传递额外参数给子脚本
        exit_code = manager.run_command(args.command, unknown)
        sys.exit(exit_code)
    else:
        print(f"❌ 未知命令: {args.command}")
        manager.show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()