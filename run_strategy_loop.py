#!/usr/bin/env python3
"""
定时运行紧急高置信度策略的循环脚本
"""

import time
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.flexible_urgent_strategy import FlexibleUrgentStrategy

def run_strategy_loop(interval_minutes=10, time_threshold=30, min_conf=0.8, max_conf=0.95):
    """
    定时循环运行策略
    
    Args:
        interval_minutes: 运行间隔（分钟）
        time_threshold: 时间阈值（分钟）
        min_conf: 最小胜率
        max_conf: 最大胜率
    """
    print("🚀 启动紧急策略定时循环")
    print(f"📊 策略参数: 时间阈值={time_threshold}分钟, 胜率范围={min_conf:.1%}-{max_conf:.1%}")
    print(f"⏰ 运行间隔: {interval_minutes}分钟")
    print("=" * 60)
    
    strategy = FlexibleUrgentStrategy(
        data_dir="./data",
        time_threshold_minutes=time_threshold,
        min_confidence=min_conf,
        max_confidence=max_conf
    )
    
    run_count = 0
    total_opportunities = 0
    
    try:
        while True:
            run_count += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n🔄 第{run_count}次运行 - {current_time}")
            print("-" * 40)
            
            try:
                result = strategy.run_strategy(save_to_file=True)
                
                if result["success"]:
                    opportunities = result["qualifying_markets_count"]
                    total_opportunities += opportunities
                    
                    if opportunities > 0:
                        print(f"✅ 发现 {opportunities} 个机会！")
                        
                        # 显示最佳机会
                        markets = result.get("markets", [])
                        if markets:
                            best_market = markets[0]
                            print(f"🔥 最佳机会:")
                            print(f"   {best_market.get('question', 'Unknown')}")
                            print(f"   胜率: {best_market.get('strategy_confidence', 0):.3f} ({best_market.get('strategy_winning_option', 'N/A')})")
                            print(f"   剩余: {best_market.get('strategy_time_remaining_minutes', 0)}分钟")
                    else:
                        print("📭 暂无符合条件的机会")
                    
                    print(f"⏱️  耗时: {result['duration_seconds']:.1f}秒")
                    print(f"📈 累计发现: {total_opportunities} 个机会")
                    
                else:
                    print(f"❌ 运行失败: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ 运行异常: {e}")
            
            # 等待下次运行
            print(f"\n💤 等待 {interval_minutes} 分钟后进行下次扫描...")
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 用户中断，策略循环已停止")
        print(f"📊 运行统计:")
        print(f"   总运行次数: {run_count}")
        print(f"   累计发现机会: {total_opportunities} 个")
        print(f"   平均每次发现: {total_opportunities/run_count:.2f} 个")

def main():
    """主函数，支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="定时运行紧急高置信度策略")
    parser.add_argument("--interval", type=int, default=10, help="运行间隔（分钟），默认10分钟")
    parser.add_argument("--time", type=int, default=30, help="时间阈值（分钟），默认30分钟")
    parser.add_argument("--min-conf", type=float, default=0.8, help="最小胜率，默认0.8")
    parser.add_argument("--max-conf", type=float, default=0.95, help="最大胜率，默认0.95")
    
    args = parser.parse_args()
    
    # 参数验证
    if args.interval <= 0:
        print("❌ 错误: 运行间隔必须大于0")
        return
    
    if args.min_conf >= args.max_conf:
        print("❌ 错误: 最小胜率必须小于最大胜率")
        return
    
    if args.min_conf < 0.5 or args.max_conf > 1.0:
        print("❌ 错误: 胜率范围必须在0.5-1.0之间")
        return
    
    if args.time <= 0:
        print("❌ 错误: 时间阈值必须大于0")
        return
    
    run_strategy_loop(
        interval_minutes=args.interval,
        time_threshold=args.time,
        min_conf=args.min_conf,
        max_conf=args.max_conf
    )

if __name__ == "__main__":
    main()