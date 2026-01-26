#!/usr/bin/env python3
"""
BTC智能自动交易器快速启动脚本
提供简单的交互式启动界面
"""

import sys
import os
import subprocess

def main():
    print("🤖 BTC智能自动交易器 - 快速启动")
    print("=" * 50)
    print()
    
    # 检查必要文件
    required_files = [
        'btc_smart_auto_trader.py',
        'btc_15min_strategy.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"   - {file}")
        print()
        print("请确保所有必要文件都在当前目录中。")
        return
    
    print("✅ 所有必要文件检查通过")
    print()
    
    # 获取交易金额
    while True:
        try:
            amount_input = input("💰 请输入交易金额 (默认 $5.0): ").strip()
            
            if not amount_input:
                trade_amount = 5.0
                break
            
            trade_amount = float(amount_input)
            if trade_amount <= 0:
                print("❌ 交易金额必须大于0，请重新输入")
                continue
            
            break
            
        except ValueError:
            print("❌ 请输入有效的数字")
            continue
        except KeyboardInterrupt:
            print("\n👋 已取消启动")
            return
    
    print(f"✅ 交易金额设置为: ${trade_amount}")
    print()
    
    # 显示启动信息
    print("🚀 即将启动BTC智能自动交易器")
    print("📋 功能说明:")
    print("   - 启动后自动判断与上一个15分钟市场的间隔")
    print("   - 间隔 < 5分钟：参与上一个市场")
    print("   - 间隔 ≥ 5分钟：等待下一个市场")
    print("   - 自动执行BTC 15分钟交易策略")
    print()
    
    # 确认启动
    try:
        confirm = input("🤔 确认启动? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("👋 已取消启动")
            return
    except KeyboardInterrupt:
        print("\n👋 已取消启动")
        return
    
    print()
    print("🎯 正在启动智能交易器...")
    print("💡 使用 Ctrl+C 可以安全停止程序")
    print("=" * 50)
    print()
    
    # 启动主程序
    try:
        cmd = [sys.executable, 'btc_smart_auto_trader.py', str(trade_amount)]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 程序已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()