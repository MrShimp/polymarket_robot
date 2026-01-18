#!/usr/bin/env python3
"""
测试SyncScheduler调度一次的时间
"""

import time
import json
from datetime import datetime
from sync.sync_scheduler import SyncScheduler

def test_scheduler_single_run():
    """测试调度器执行一次同步的时间"""
    print("🔄 测试SyncScheduler调度一次的时间...")
    print("=" * 50)
    
    # 创建调度器实例
    scheduler = SyncScheduler()
    
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()
    
    print(f"⏰ 开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 执行手动同步...")
    
    try:
        # 执行手动同步
        result = scheduler.manual_sync()
        
        # 记录结束时间
        end_time = time.time()
        end_datetime = datetime.now()
        duration = end_time - start_time
        
        print(f"⏰ 结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总耗时: {duration:.3f} 秒")
        print()
        
        # 显示同步结果
        if result['success']:
            print("✅ 同步成功!")
            print(f"   📅 事件数量: {result.get('events_synced', 0)}")
            print(f"   💹 市场数量: {result.get('markets_synced', 0)}")
            print(f"   🏷️  标签数量: {result.get('tags_processed', 0)}")
        else:
            print("❌ 同步失败!")
            print(f"   错误信息: {result.get('error', 'Unknown error')}")
        
        print()
        print("📊 性能分析:")
        
        if result['success']:
            events_count = result.get('events_synced', 0)
            markets_count = result.get('markets_synced', 0)
            tags_count = result.get('tags_processed', 0)
            total_items = events_count + markets_count
            
            if duration > 0:
                print(f"   处理速度: {total_items / duration:.1f} 条记录/秒")
                print(f"   事件处理: {events_count / duration:.1f} 事件/秒")
                print(f"   市场处理: {markets_count / duration:.1f} 市场/秒")
            
            print(f"   平均每个标签: {duration / tags_count:.3f} 秒" if tags_count > 0 else "   标签处理: N/A")
        
        # 获取调度器统计信息
        stats = scheduler.get_sync_statistics()
        print()
        print("📈 调度器统计:")
        print(f"   总同步次数: {stats.get('total_syncs', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
        print(f"   平均耗时: {stats.get('average_duration', 0):.3f} 秒")
        
        return {
            'duration': duration,
            'success': result.get('success', False),
            'events_synced': result.get('events_synced', 0),
            'markets_synced': result.get('markets_synced', 0),
            'tags_processed': result.get('tags_processed', 0),
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat()
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ 测试失败: {str(e)}")
        print(f"⏱️  耗时: {duration:.3f} 秒")
        
        return {
            'duration': duration,
            'success': False,
            'error': str(e),
            'start_time': start_datetime.isoformat(),
            'end_time': datetime.now().isoformat()
        }

def test_scheduler_job_execution():
    """测试调度器任务执行时间"""
    print("🔄 测试调度器任务执行时间...")
    print("=" * 50)
    
    scheduler = SyncScheduler()
    
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()
    
    print(f"⏰ 开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 执行调度任务...")
    
    try:
        # 直接调用调度任务方法
        scheduler.run_sync_job()
        
        # 记录结束时间
        end_time = time.time()
        end_datetime = datetime.now()
        duration = end_time - start_time
        
        print(f"⏰ 结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总耗时: {duration:.3f} 秒")
        
        # 获取最后的同步结果
        last_result = scheduler.last_sync_result
        
        if last_result and last_result['success']:
            print("✅ 调度任务执行成功!")
            print(f"   📅 事件数量: {last_result.get('events_synced', 0)}")
            print(f"   💹 市场数量: {last_result.get('markets_synced', 0)}")
            print(f"   🏷️  标签数量: {last_result.get('tags_processed', 0)}")
            print(f"   📊 同步前质量: {last_result.get('quality_before', 'N/A')}")
            print(f"   📊 同步后质量: {last_result.get('quality_after', 'N/A')}")
        else:
            print("❌ 调度任务执行失败!")
            if last_result:
                print(f"   错误信息: {last_result.get('error', 'Unknown error')}")
        
        return {
            'duration': duration,
            'success': last_result['success'] if last_result else False,
            'result': last_result,
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat()
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ 调度任务执行失败: {str(e)}")
        print(f"⏱️  耗时: {duration:.3f} 秒")
        
        return {
            'duration': duration,
            'success': False,
            'error': str(e),
            'start_time': start_datetime.isoformat(),
            'end_time': datetime.now().isoformat()
        }

def compare_sync_methods():
    """比较不同同步方法的性能"""
    print("🔄 比较不同同步方法的性能...")
    print("=" * 60)
    
    results = {}
    
    # 测试1: 手动同步
    print("1️⃣  测试手动同步...")
    manual_result = test_scheduler_single_run()
    results['manual_sync'] = manual_result
    
    print("\n" + "-" * 60 + "\n")
    
    # 测试2: 调度任务执行
    print("2️⃣  测试调度任务执行...")
    job_result = test_scheduler_job_execution()
    results['scheduled_job'] = job_result
    
    print("\n" + "=" * 60)
    print("📊 性能对比总结:")
    print("=" * 60)
    
    for method, result in results.items():
        method_name = "手动同步" if method == "manual_sync" else "调度任务"
        status = "✅ 成功" if result['success'] else "❌ 失败"
        
        print(f"{method_name}:")
        print(f"   状态: {status}")
        print(f"   耗时: {result['duration']:.3f} 秒")
        
        if result['success'] and 'events_synced' in result:
            print(f"   事件: {result.get('events_synced', 0)}")
            print(f"   市场: {result.get('markets_synced', 0)}")
        
        print()
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scheduler_timing_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 测试结果已保存到: {filename}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试SyncScheduler调度时间")
    parser.add_argument("--mode", choices=["manual", "job", "compare"], 
                       default="compare", help="测试模式")
    
    args = parser.parse_args()
    
    if args.mode == "manual":
        test_scheduler_single_run()
    elif args.mode == "job":
        test_scheduler_job_execution()
    else:
        compare_sync_methods()