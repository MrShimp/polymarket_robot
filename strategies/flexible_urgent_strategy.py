#!/usr/bin/env python3
"""
灵活的紧急策略 - 可调整时间阈值和胜率范围的策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.urgent_high_confidence_strategy import UrgentHighConfidenceStrategy

class FlexibleUrgentStrategy(UrgentHighConfidenceStrategy):
    """灵活的紧急策略类，继承自紧急高置信度策略"""
    
    def __init__(self, data_dir: str = "./data", max_retries: int = 3, 
                 time_threshold_minutes: int = 15, 
                 min_confidence: float = 0.85, 
                 max_confidence: float = 0.95):
        super().__init__(data_dir, max_retries)
        
        # 可调整的策略参数
        self.time_threshold_minutes = time_threshold_minutes
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        
        print(f"📊 策略参数:")
        print(f"   时间阈值: {self.time_threshold_minutes} 分钟")
        print(f"   胜率范围: {self.min_confidence:.1%} - {self.max_confidence:.1%}")

def main():
    """主函数，支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="灵活的紧急策略 - 可调整参数")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--time", type=int, default=15, help="时间阈值（分钟），默认15分钟")
    parser.add_argument("--min-conf", type=float, default=0.85, help="最小胜率，默认0.85")
    parser.add_argument("--max-conf", type=float, default=0.95, help="最大胜率，默认0.95")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件，仅显示结果")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    
    args = parser.parse_args()
    
    # 参数验证
    if args.min_conf >= args.max_conf:
        print("❌ 错误: 最小胜率必须小于最大胜率")
        return
    
    if args.min_conf < 0.5 or args.max_conf > 1.0:
        print("❌ 错误: 胜率范围必须在0.5-1.0之间")
        return
    
    if args.time <= 0:
        print("❌ 错误: 时间阈值必须大于0")
        return
    
    # 设置日志级别
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🚀 启动灵活紧急策略...")
    print("-" * 60)
    
    # 创建策略实例
    strategy = FlexibleUrgentStrategy(
        data_dir=args.data_dir,
        time_threshold_minutes=args.time,
        min_confidence=args.min_conf,
        max_confidence=args.max_conf
    )
    
    # 运行策略
    result = strategy.run_strategy(save_to_file=not args.no_save)
    
    if result["success"]:
        print(f"\n🎉 策略执行成功!")
        
        if result["qualifying_markets_count"] > 0:
            print(f"\n💡 发现 {result['qualifying_markets_count']} 个符合条件的交易机会")
            print(f"📁 数据已保存到: {result.get('csv_file', 'N/A')}")
            
            # 显示前几个最佳机会的详细信息
            markets = result.get("markets", [])
            if markets:
                print(f"\n🔥 最佳机会详情:")
                for i, market in enumerate(markets[:5], 1):  # 显示前5个
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
            print(f"   - 增加时间阈值 (当前: {args.time}分钟)")
            print(f"   - 调整胜率范围 (当前: {args.min_conf:.1%}-{args.max_conf:.1%})")
            print("   - 稍后再次运行策略")
        
        print(f"\n⏱️  执行耗时: {result['duration_seconds']:.1f} 秒")
        
    else:
        print(f"\n❌ 策略执行失败: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()