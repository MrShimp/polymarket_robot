#!/usr/bin/env python3
"""
BTC智能自动交易器演示脚本
展示时间判断逻辑和决策过程，不执行实际交易
"""

import datetime
import pytz
import time
from typing import Tuple

class SmartTraderDemo:
    """智能交易器演示类"""
    
    def __init__(self):
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.et_winter_tz = pytz.FixedOffset(-5 * 60)  # UTC-5
        self.time_threshold = 5  # 5分钟阈值
    
    def get_15min_timestamps(self) -> Tuple[int, int, datetime.datetime, datetime.datetime]:
        """获取上一个和下一个15分钟整点的时间戳"""
        now_beijing = datetime.datetime.now(self.beijing_tz)
        
        # 计算当前15分钟区间的开始时间
        current_minute = now_beijing.minute
        interval_start_minute = (current_minute // 15) * 15
        
        # 当前15分钟区间的开始时间（上一个整点）
        prev_15min_beijing = now_beijing.replace(
            minute=interval_start_minute, 
            second=0, 
            microsecond=0
        )
        
        # 下一个15分钟整点
        next_15min_beijing = prev_15min_beijing + datetime.timedelta(minutes=15)
        
        # 转换为美东时间并获取时间戳
        prev_15min_et = prev_15min_beijing.astimezone(self.et_winter_tz)
        next_15min_et = next_15min_beijing.astimezone(self.et_winter_tz)
        
        prev_timestamp = int(prev_15min_et.timestamp())
        next_timestamp = int(next_15min_et.timestamp())
        
        return prev_timestamp, next_timestamp, prev_15min_beijing, next_15min_beijing
    
    def get_time_to_interval_start(self, target_beijing_time: datetime.datetime) -> float:
        """计算到目标时间的分钟数"""
        now_beijing = datetime.datetime.now(self.beijing_tz)
        time_diff = target_beijing_time - now_beijing
        return time_diff.total_seconds() / 60
    
    def simulate_market_query(self, timestamp: int) -> bool:
        """模拟市场查询（随机返回结果）"""
        import random
        # 80%概率找到市场
        return random.random() < 0.8
    
    def demo_decision_process(self):
        """演示决策过程"""
        print("🎭 BTC智能自动交易器 - 决策过程演示")
        print("=" * 60)
        print("📝 注意：这是演示模式，不会执行实际交易")
        print()
        
        # 获取时间信息
        prev_timestamp, next_timestamp, prev_beijing_time, next_beijing_time = self.get_15min_timestamps()
        
        # 计算时间差
        time_since_prev = self.get_time_to_interval_start(prev_beijing_time)
        time_to_next = self.get_time_to_interval_start(next_beijing_time)
        
        minutes_since_prev = abs(time_since_prev)
        minutes_to_next = time_to_next
        
        # 显示当前时间信息
        now_beijing = datetime.datetime.now(self.beijing_tz)
        
        print(f"🕐 当前时间信息:")
        print(f"   当前北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   当前分钟: {now_beijing.minute}")
        print()
        
        print(f"⏰ 15分钟区间分析:")
        print(f"   上一个15分钟整点: {prev_beijing_time.strftime('%H:%M')} (时间戳: {prev_timestamp})")
        print(f"   下一个15分钟整点: {next_beijing_time.strftime('%H:%M')} (时间戳: {next_timestamp})")
        print(f"   距离上一个整点: {minutes_since_prev:.1f}分钟")
        print(f"   距离下一个整点: {minutes_to_next:.1f}分钟")
        print()
        
        # 决策过程
        print(f"🤖 智能决策过程 (阈值: {self.time_threshold}分钟):")
        print()
        
        if minutes_since_prev <= self.time_threshold:
            print(f"✅ 决策: 尝试参与上一个市场")
            print(f"   原因: 间隔{minutes_since_prev:.1f}分钟 <= {self.time_threshold}分钟")
            print(f"   目标时间戳: {prev_timestamp}")
            print()
            
            print("🔍 模拟市场查询...")
            time.sleep(1)  # 模拟网络延迟
            
            market_available = self.simulate_market_query(prev_timestamp)
            
            if market_available:
                print("✅ 找到可用市场！")
                print(f"   市场URL: https://gamma-api.polymarket.com/markets/slug/btc-updown-15m-{prev_timestamp}")
                print("🎯 决定：立即参与上一个市场")
                print()
                print("📊 模拟BTC价格获取...")
                time.sleep(0.5)
                print("✅ BTC价格: $95,234.56")
                print()
                print("🚀 模拟启动交易策略...")
                print("   [演示模式] 实际运行时会启动 btc_15min_strategy.py")
                print("   [演示模式] 策略会执行具体的交易逻辑")
                print("✅ 智能交易周期启动成功（演示）")
            else:
                print("❌ 上一个市场不可用")
                print("🔄 改为等待下一个市场")
                print(f"   等待时间: {minutes_to_next:.1f}分钟")
                print(f"   目标时间戳: {next_timestamp}")
                print()
                self.simulate_wait_for_next_market(minutes_to_next, next_timestamp)
        else:
            print(f"⏳ 决策: 等待下一个市场")
            print(f"   原因: 间隔{minutes_since_prev:.1f}分钟 > {self.time_threshold}分钟")
            print(f"   等待时间: {minutes_to_next:.1f}分钟")
            print(f"   目标时间戳: {next_timestamp}")
            print()
            self.simulate_wait_for_next_market(minutes_to_next, next_timestamp)
    
    def simulate_wait_for_next_market(self, wait_minutes: float, target_timestamp: int):
        """模拟等待下一个市场"""
        print("⏰ 模拟等待过程...")
        
        if wait_minutes > 2:
            print(f"   [演示模式] 实际会等待 {wait_minutes:.1f} 分钟")
            print("   [演示模式] 程序会每30秒检查一次时间")
            print("   [演示模式] 接近目标时间时开始查询市场")
        else:
            print("   [演示模式] 即将到达目标时间")
        
        print()
        print("🔍 模拟下一个市场查询...")
        time.sleep(1)
        
        market_available = self.simulate_market_query(target_timestamp)
        
        if market_available:
            print("✅ 找到下一个可用市场！")
            print(f"   市场URL: https://gamma-api.polymarket.com/markets/slug/btc-updown-15m-{target_timestamp}")
            print()
            print("📊 模拟BTC价格获取...")
            time.sleep(0.5)
            print("✅ BTC价格: $95,456.78")
            print()
            print("🚀 模拟启动交易策略...")
            print("   [演示模式] 实际运行时会启动 btc_15min_strategy.py")
            print("   [演示模式] 策略会执行具体的交易逻辑")
            print("✅ 智能交易周期启动成功（演示）")
        else:
            print("❌ 下一个市场也不可用")
            print("🔄 实际运行时会继续等待或重试")
    
    def show_comparison(self):
        """显示与原版的对比"""
        print()
        print("🆚 与原版 btc_auto_trader.py 的对比:")
        print("=" * 60)
        
        print("📊 原版交易器 (btc_auto_trader.py):")
        print("   - 启动后等待下一个15分钟整点")
        print("   - 固定的等待模式")
        print("   - 可能错过刚开始的市场")
        print("   - 适合定时启动")
        print()
        
        print("🧠 智能交易器 (btc_smart_auto_trader.py):")
        print("   - 启动后智能判断参与时机")
        print("   - 基于5分钟阈值的动态决策")
        print("   - 最大化市场参与机会")
        print("   - 适合随时启动")
        print()
        
        print("💡 推荐使用场景:")
        print("   - 刚过15分钟整点时启动 → 智能交易器")
        print("   - 定时任务启动 → 原版交易器")
        print("   - 随时手动启动 → 智能交易器")
    
    def run_demo(self):
        """运行完整演示"""
        try:
            self.demo_decision_process()
            self.show_comparison()
            
            print()
            print("=" * 60)
            print("🎭 演示完成！")
            print()
            print("🚀 要运行实际的智能交易器，请使用:")
            print("   python3 start_smart_trader.py")
            print("   或")
            print("   python3 btc_smart_auto_trader.py [交易金额]")
            
        except KeyboardInterrupt:
            print("\n👋 演示已停止")

def main():
    """主函数"""
    demo = SmartTraderDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()