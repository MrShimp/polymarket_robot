#!/usr/bin/env python3
"""
简化的调度器时间测试
"""

import time
from datetime import datetime
from sync.sync_scheduler import SyncScheduler

def test_scheduler_timing():
    """测试调度器执行时间"""
    print("🔄 测试SyncScheduler调度一次的时间")
    print("=" * 50)
    
    # 创建调度器
    scheduler = SyncScheduler()
    
    # 测试手动同步
    print("📊 执行手动同步...")
    start_time = time.time()
    
    try:
        result = scheduler.manual_sync()
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  同步耗时: {duration:.3f} 秒")
        
        if result.get('success'):
            print("✅ 同步成功")
            print(f"   事件: {result.get('events_synced', 0)}")
            print(f"   市场: {result.get('markets_synced', 0)}")
            print(f"   标签: {result.get('tags_processed', 0)}")
            
            # 计算处理速度
            total_items = result.get('events_synced', 0) + result.get('markets_synced', 0)
            if duration > 0:
                print(f"   处理速度: {total_items / duration:.1f} 条记录/秒")
        else:
            print("❌ 同步失败")
            print(f"   错误: {result.get('error', 'Unknown')}")
        
        return duration, result.get('success', False)
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ 执行失败: {e}")
        print(f"⏱️  耗时: {duration:.3f} 秒")
        return duration, False

def test_multiple_runs(count=3):
    """测试多次运行的平均时间"""
    print(f"\n🔄 测试 {count} 次运行的平均时间")
    print("=" * 50)
    
    times = []
    successes = 0
    
    for i in range(count):
        print(f"\n第 {i+1}/{count} 次测试:")
        duration, success = test_scheduler_timing()
        times.append(duration)
        if success:
            successes += 1
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 统计结果:")
        print(f"   平均时间: {avg_time:.3f} 秒")
        print(f"   最快时间: {min_time:.3f} 秒")
        print(f"   最慢时间: {max_time:.3f} 秒")
        print(f"   成功率: {successes}/{count} ({successes/count*100:.1f}%)")
        
        return {
            'average': avg_time,
            'min': min_time,
            'max': max_time,
            'success_rate': successes/count*100,
            'times': times
        }
    
    return None

if __name__ == "__main__":
    # 单次测试
    test_scheduler_timing()
    
    # 多次测试
    stats = test_multiple_runs(3)
    
    if stats:
        print(f"\n🎯 结论:")
        print(f"   SyncScheduler调度一次平均耗时: {stats['average']:.3f} 秒")
        print(f"   时间范围: {stats['min']:.3f} - {stats['max']:.3f} 秒")
        print(f"   系统稳定性: {stats['success_rate']:.1f}% 成功率")