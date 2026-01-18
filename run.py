#!/usr/bin/env python3
"""
Polymarket Robot 统一启动脚本
"""

import sys
import os
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Polymarket Robot 统一启动脚本")
    parser.add_argument("module", choices=[
        "manager", "sync", "dashboard", "export", "agents", "tests"
    ], help="要启动的模块")
    
    # 解析已知参数，其余传递给子模块
    args, unknown = parser.parse_known_args()
    
    if args.module == "manager":
        from utils.polymarket_manager import main as manager_main
        # 重新设置sys.argv以传递参数
        sys.argv = ["polymarket_manager.py"] + (unknown or ["help"])
        manager_main()
        
    elif args.module == "sync":
        from sync.enhanced_sync import main as sync_main
        sys.argv = ["enhanced_sync.py"] + (unknown or [])
        sync_main()
        
    elif args.module == "dashboard":
        from dashboard.live_dashboard import main as dashboard_main
        sys.argv = ["live_dashboard.py"] + (unknown or [])
        dashboard_main()
        
    elif args.module == "export":
        from export.data_exporter import main as export_main
        sys.argv = ["data_exporter.py"] + (unknown or [])
        export_main()
        
    elif args.module == "agents":
        from main import main as agents_main
        sys.argv = ["main.py"] + (unknown or [])
        agents_main()
        
    elif args.module == "tests":
        test_name = unknown[0] if unknown else "help"
        if test_name == "scheduler":
            from tests.simple_scheduler_test import main as test_main
            test_main()
        elif test_name == "performance":
            from tests.sync_performance_test import main as test_main
            sys.argv = ["sync_performance_test.py"] + (unknown[1:] if len(unknown) > 1 else [])
            test_main()
        else:
            print("可用测试:")
            print("  scheduler   - 调度器测试")
            print("  performance - 性能测试")

if __name__ == "__main__":
    main()