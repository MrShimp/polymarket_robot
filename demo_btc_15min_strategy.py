#!/usr/bin/env python3
"""
Demo script for BTC 15min Strategy
Shows how to use the strategy with example parameters
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from btc_15min_strategy import BTC15MinStrategy


async def demo_strategy():
    """Demo the BTC 15min strategy"""
    print("🚀 BTC 15分钟策略演示")
    print("=" * 50)

    # Example parameters
    baseline_price = 95000.0  # Example baseline price
    trade_amount = 5.0  # Small amount for demo

    print(f"📊 演示参数:")
    print(f"   基准价格: ${baseline_price:,.2f}")
    print(f"   交易金额: ${trade_amount}")
    print(f"   模式: 演示模式 (不执行真实交易)")

    try:
        # Create strategy instance
        strategy = BTC15MinStrategy(use_testnet=True, baseline_price=baseline_price)

        # Show current status
        status = strategy.get_status()
        print(f"\n⏰ 当前状态:")
        print(f"   北京时间: {status['beijing_time']}")
        print(f"   交易时段: {'✅ 开放' if status['trading_hours'] else '❌ 关闭'}")
        print(
            f"   当前区间: {status['current_interval']['start']}-{status['current_interval']['end']}"
        )

        # Test price monitoring for a short time
        print(f"\n📈 开始价格监控测试 (30秒)...")

        # Start price monitoring
        strategy.running = True

        # Monitor for 30 seconds
        import time

        start_time = time.time()
        while time.time() - start_time < 30:
            price = await strategy.get_btc_price_binance()
            if price:
                print(f"📊 BTC价格: ${price:,.2f}")
            await asyncio.sleep(5)

        strategy.stop()
        print("✅ 演示完成!")

    except Exception as e:
        print(f"❌ 演示错误: {e}")
        return False

    return True


def show_usage():
    """Show usage information"""
    print("📖 BTC 15分钟策略使用说明")
    print("=" * 50)
    print()
    print("🎯 策略特点:")
    print("   • 双向交易: YES/NO 概率>75%均可入场")
    print("   • 时间窗口: 10:00-19:00 北京时间")
    print("   • 买入限制: 区间开始5分钟后才能买入")
    print("   • 卖出自由: 任何时间都可以卖出")
    print("   • 价格阈值: 基准价格±32刀触发入场")
    print()
    print("📋 使用方法:")
    print("   1. 直接运行: python3 btc_15min_strategy.py")
    print(
        "   2. 命令行参数: python3 btc_15min_strategy.py <market_id> <amount> <baseline_price>"
    )
    print()
    print("💡 示例:")
    print("   python3 btc_15min_strategy.py 0x1234...abcd 10.0 95000")
    print()
    print("⚠️  注意事项:")
    print("   • 需要有效的Polymarket市场ID")
    print("   • 确保账户有足够的USDC余额")
    print("   • 基准价格应该接近当前BTC价格")
    print("   • 建议先用小金额测试")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        show_usage()
    else:
        print("运行演示模式...")
        try:
            asyncio.run(demo_strategy())
        except KeyboardInterrupt:
            print("\n用户中断演示")
        except Exception as e:
            print(f"演示错误: {e}")
