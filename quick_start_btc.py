#!/usr/bin/env python3
"""
BTC策略快速启动脚本
一键启动常用配置
"""

import sys
import os
import asyncio
import json
import requests
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from start_btc_15min_strategy import BTCStrategyLauncher

# 快速配置预设
QUICK_CONFIGS = {
    "small": {
        "name": "小额测试",
        "amount": 5.0,
        "description": "适合新手测试，小额交易"
    },
    "normal": {
        "name": "标准交易",
        "amount": 10.0,
        "description": "标准交易金额，平衡风险收益"
    },
    "large": {
        "name": "大额交易",
        "amount": 25.0,
        "description": "较大金额，适合有经验的交易者"
    }
}

def get_current_btc_price():
    """获取当前BTC价格"""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception:
        return 95000.0  # 默认价格

def show_quick_menu():
    """显示快速菜单"""
    current_price = get_current_btc_price()
    
    print("⚡ BTC策略快速启动")
    print("=" * 40)
    print(f"📊 当前BTC价格: ${current_price:,.2f}")
    print(f"⏰ 当前时间: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    print("🚀 快速配置:")
    for key, config in QUICK_CONFIGS.items():
        print(f"   {key}: {config['name']} (${config['amount']}) - {config['description']}")
    
    print("\n💡 使用方法:")
    print("   python3 quick_start_btc.py <market_id> [config]")
    print()
    print("📋 示例:")
    print("   python3 quick_start_btc.py 0x1234...abcd small")
    print("   python3 quick_start_btc.py 0x1234...abcd normal")
    print("   python3 quick_start_btc.py 0x1234...abcd large")

async def quick_start(market_id: str, config_name: str = "normal"):
    """快速启动"""
    if config_name not in QUICK_CONFIGS:
        print(f"❌ 无效配置: {config_name}")
        print(f"可用配置: {', '.join(QUICK_CONFIGS.keys())}")
        return
    
    config = QUICK_CONFIGS[config_name]
    current_price = get_current_btc_price()
    
    print("⚡ BTC策略快速启动")
    print("=" * 40)
    print(f"🎯 配置: {config['name']}")
    print(f"💰 金额: ${config['amount']}")
    print(f"📊 基准价格: ${current_price:,.2f}")
    print(f"🆔 市场ID: {market_id[:10]}...{market_id[-8:]}")
    print("=" * 40)
    
    # 快速确认
    confirm = input("❓ 立即启动? (y/n) [默认y]: ").strip().lower()
    if confirm and confirm not in ['y', 'yes', '是', '']:
        print("❌ 已取消")
        return
    
    # 创建启动器并启动
    launcher = BTCStrategyLauncher()
    
    params = {
        'amount': config['amount'],
        'require_confirm': False
    }
    
    print(f"\n🚀 启动 {config['name']} 配置...")
    await launcher.start_strategy(market_id, current_price, params)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_quick_menu()
        return
    
    if sys.argv[1] in ['--help', '-h', 'help']:
        show_quick_menu()
        return
    
    market_id = sys.argv[1]
    config_name = sys.argv[2] if len(sys.argv) > 2 else "normal"
    
    # 验证市场ID
    if not market_id or len(market_id) < 10:
        print("❌ 无效的市场ID")
        return
    
    try:
        asyncio.run(quick_start(market_id, config_name))
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 启动错误: {e}")

if __name__ == "__main__":
    main()