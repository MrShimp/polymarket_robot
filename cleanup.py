#!/usr/bin/env python3
"""
项目精简清理脚本
保留：数据拉取、交易、日志展示的核心功能
"""

import os
import shutil

def cleanup_project():
    """清理项目，保留核心功能"""
    
    # 要删除的文件和目录
    files_to_remove = [
        # 复杂的策略文件
        'strategies/',
        'run_urgent_strategy.py',
        'run_strategy_loop.py',
        
        # 复杂的同步文件
        'sync/enhanced_sync.py',
        'sync/polymarket_sync.py',
        'sync/urgent_markets_sync.py',
        
        # 复杂的交易文件
        'trading/strategy_trader.py',
        'trading/test_trading.py',
        'trading/setup_credentials.py',
        'trading/polymarket_clob_client.py',
        'trading/config.py',
        
        # 文档文件
        'demo.py',
        'TRADING_GUIDE.md',
        'URGENT_STRATEGY_GUIDE.md',
        'STRATEGY_SUMMARY.md',
        'PRIVATE_KEY_SETUP_GUIDE.md',
        'PROJECT_STRUCTURE_UPDATED.md',
        
        # 配置文件
        'config/sys_config.json',
        'config/sys_config_sample.json',
        'config/sync_config.json',
        
        # 其他文件
        'requirements.txt',  # 保留 requirements_simple.txt
        'run.py',
    ]
    
    print("🧹 开始清理项目...")
    
    removed_count = 0
    for item in files_to_remove:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"📁 删除目录: {item}")
                else:
                    os.remove(item)
                    print(f"📄 删除文件: {item}")
                removed_count += 1
            except Exception as e:
                print(f"❌ 删除失败 {item}: {e}")
    
    print(f"\n✅ 清理完成，删除了 {removed_count} 个文件/目录")
    
    # 显示保留的核心文件
    core_files = [
        'main.py',           # 核心主程序
        'config.json',       # 简化配置
        'requirements_simple.txt',  # 简化依赖
        'README_SIMPLE.md',  # 简化说明
        'cleanup.py',        # 本清理脚本
        'data/',            # 数据目录
        'core/',            # 核心模块（如果需要）
        'tests/test.py',    # 基础测试
    ]
    
    print("\n📋 保留的核心文件:")
    for file in core_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"⚠️  {file} (不存在)")
    
    print("\n🎯 精简后的项目结构:")
    print("├── main.py                 # 主程序（数据拉取+交易+日志）")
    print("├── config.json             # 配置文件")
    print("├── requirements_simple.txt # 依赖文件")
    print("├── README_SIMPLE.md        # 使用说明")
    print("├── trading.log             # 交易日志（运行后生成）")
    print("└── data/                   # 数据目录")
    
    print("\n🚀 现在你可以使用精简版系统:")
    print("1. pip install -r requirements_simple.txt")
    print("2. 编辑 config.json 填入私钥")
    print("3. python3 main.py --mode single")

if __name__ == "__main__":
    cleanup_project()