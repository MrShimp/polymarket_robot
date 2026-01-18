#!/usr/bin/env python3
"""
运行紧急高置信度策略的简单脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.urgent_high_confidence_strategy import UrgentHighConfidenceStrategy

def main():
    print("🚀 启动紧急高置信度策略...")
    print("📊 策略参数:")
    print("   - 时间阈值: 10分钟内结束")
    print("   - 胜率范围: 90% - 95%")
    print("   - 目标: Yes或No选项的高置信度机会")
    print("-" * 60)
    
    # 创建策略实例
    strategy = UrgentHighConfidenceStrategy(data_dir="./data")
    
    # 运行策略
    result = strategy.run_strategy(save_to_file=True)
    
    if result["success"]:
        print(f"\n🎉 策略执行成功!")
        
        if result["qualifying_markets_count"] > 0:
            print(f"\n💡 发现 {result['qualifying_markets_count']} 个符合条件的交易机会")
            print(f"📁 数据已保存到: {result.get('csv_file', 'N/A')}")
            
            # 显示前几个最佳机会的详细信息
            markets = result.get("markets", [])
            if markets:
                print(f"\n🔥 最佳机会详情:")
                for i, market in enumerate(markets[:3], 1):  # 显示前3个
                    print(f"\n{i}. {market.get('question', 'Unknown Question')}")
                    print(f"   ID: {market.get('id', 'N/A')}")
                    print(f"   胜率: {market.get('strategy_confidence', 0):.3f} ({market.get('strategy_winning_option', 'N/A')})")
                    print(f"   剩余时间: {market.get('strategy_time_remaining_minutes', 0)} 分钟")
                    print(f"   交易量: ${market.get('volumeNum', 0):,.0f}")
                    print(f"   流动性: ${market.get('liquidityNum', 0):,.0f}")
                    print(f"   结束时间: {market.get('endDate', 'N/A')}")
        else:
            print(f"\n📭 当前没有发现符合条件的交易机会")
            print("💡 建议:")
            print("   - 稍后再次运行策略")
            print("   - 调整胜率范围参数")
            print("   - 增加时间阈值")
        
        print(f"\n⏱️  执行耗时: {result['duration_seconds']:.1f} 秒")
        
    else:
        print(f"\n❌ 策略执行失败: {result.get('error', 'Unknown error')}")
        print("💡 可能的原因:")
        print("   - 网络连接问题")
        print("   - API访问限制")
        print("   - 数据格式变化")

if __name__ == "__main__":
    main()