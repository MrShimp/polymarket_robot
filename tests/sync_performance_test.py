#!/usr/bin/env python3
"""
同步性能测试工具 - 测试不同模式下的同步时间和性能
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from sync.enhanced_sync import EnhancedPolymarketSync
from sync.offline_data_generator import OfflineDataGenerator

class SyncPerformanceTest:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.results = []
    
    def test_offline_sync(self, iterations: int = 3) -> Dict[str, Any]:
        """测试离线模式同步性能"""
        print("🔄 测试离线模式同步性能...")
        
        times = []
        data_stats = []
        
        for i in range(iterations):
            print(f"   第 {i+1}/{iterations} 次测试...")
            
            syncer = EnhancedPolymarketSync(self.data_dir, offline_mode=True)
            
            start_time = time.time()
            report = syncer.sync_all_data()
            end_time = time.time()
            
            duration = end_time - start_time
            times.append(duration)
            
            data_stats.append({
                "events": report.get("events_count", 0),
                "markets": report.get("markets_count", 0),
                "tags": report.get("tags_count", 0)
            })
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        # 获取数据统计
        last_stats = data_stats[-1] if data_stats else {}
        
        result = {
            "mode": "offline",
            "iterations": iterations,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "times": times,
            "events_count": last_stats.get("events", 0),
            "markets_count": last_stats.get("markets", 0),
            "tags_count": last_stats.get("tags", 0),
            "throughput": {
                "events_per_second": last_stats.get("events", 0) / avg_time,
                "markets_per_second": last_stats.get("markets", 0) / avg_time
            }
        }
        
        self.results.append(result)
        return result
    
    def test_api_sync(self, timeout: int = 60) -> Dict[str, Any]:
        """测试API模式同步性能"""
        print("🔄 测试API模式同步性能...")
        
        syncer = EnhancedPolymarketSync(self.data_dir, offline_mode=False)
        
        try:
            start_time = time.time()
            report = syncer.sync_all_data()
            end_time = time.time()
            
            duration = end_time - start_time
            
            result = {
                "mode": "api",
                "success": True,
                "duration": duration,
                "events_count": report.get("events_count", 0),
                "markets_count": report.get("markets_count", 0),
                "tags_count": report.get("tags_count", 0),
                "throughput": {
                    "events_per_second": report.get("events_count", 0) / duration if duration > 0 else 0,
                    "markets_per_second": report.get("markets_count", 0) / duration if duration > 0 else 0
                }
            }
            
        except Exception as e:
            result = {
                "mode": "api",
                "success": False,
                "error": str(e),
                "duration": 0
            }
        
        self.results.append(result)
        return result
    
    def test_data_generation(self) -> Dict[str, Any]:
        """测试离线数据生成性能"""
        print("🔄 测试离线数据生成性能...")
        
        generator = OfflineDataGenerator()
        
        start_time = time.time()
        tags, events, markets = generator.save_offline_data(f"{self.data_dir}/offline")
        end_time = time.time()
        
        duration = end_time - start_time
        
        result = {
            "mode": "data_generation",
            "duration": duration,
            "tags_generated": len(tags),
            "events_generated": len(events),
            "markets_generated": len(markets),
            "throughput": {
                "events_per_second": len(events) / duration,
                "markets_per_second": len(markets) / duration
            }
        }
        
        self.results.append(result)
        return result
    
    def benchmark_file_operations(self) -> Dict[str, Any]:
        """测试文件操作性能"""
        print("🔄 测试文件操作性能...")
        
        # 测试数据读取速度
        tag_dir = os.path.join(self.data_dir, "tag")
        if not os.path.exists(tag_dir):
            return {"mode": "file_ops", "error": "No data to test"}
        
        start_time = time.time()
        
        file_count = 0
        total_size = 0
        
        for tag_name in os.listdir(tag_dir):
            tag_path = os.path.join(tag_dir, tag_name)
            if os.path.isdir(tag_path):
                for file_name in os.listdir(tag_path):
                    file_path = os.path.join(tag_path, file_name)
                    if os.path.isfile(file_path):
                        file_count += 1
                        total_size += os.path.getsize(file_path)
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "mode": "file_operations",
            "duration": duration,
            "files_scanned": file_count,
            "total_size_mb": total_size / (1024 * 1024),
            "throughput": {
                "files_per_second": file_count / duration if duration > 0 else 0,
                "mb_per_second": (total_size / (1024 * 1024)) / duration if duration > 0 else 0
            }
        }
        
        self.results.append(result)
        return result
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整的性能基准测试"""
        print("🚀 开始完整性能基准测试...")
        print("=" * 60)
        
        benchmark_start = time.time()
        
        # 1. 测试数据生成
        gen_result = self.test_data_generation()
        
        # 2. 测试离线同步 (多次)
        offline_result = self.test_offline_sync(iterations=5)
        
        # 3. 测试API同步 (如果可用)
        api_result = self.test_api_sync()
        
        # 4. 测试文件操作
        file_result = self.benchmark_file_operations()
        
        benchmark_end = time.time()
        total_benchmark_time = benchmark_end - benchmark_start
        
        # 汇总结果
        summary = {
            "benchmark_time": total_benchmark_time,
            "timestamp": datetime.now().isoformat(),
            "results": {
                "data_generation": gen_result,
                "offline_sync": offline_result,
                "api_sync": api_result,
                "file_operations": file_result
            }
        }
        
        return summary
    
    def print_results(self, summary: Dict[str, Any]):
        """打印性能测试结果"""
        print("\n" + "="*80)
        print("📊 Polymarket 同步性能测试报告")
        print("="*80)
        print(f"🕐 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总测试耗时: {summary['benchmark_time']:.2f} 秒")
        print()
        
        results = summary["results"]
        
        # 数据生成性能
        if "data_generation" in results:
            gen = results["data_generation"]
            print("🔧 离线数据生成性能:")
            print(f"   耗时: {gen['duration']:.3f} 秒")
            print(f"   生成: {gen['tags_generated']} 标签, {gen['events_generated']} 事件, {gen['markets_generated']} 市场")
            print(f"   速度: {gen['throughput']['events_per_second']:.1f} 事件/秒, {gen['throughput']['markets_per_second']:.1f} 市场/秒")
            print()
        
        # 离线同步性能
        if "offline_sync" in results:
            offline = results["offline_sync"]
            print("🔄 离线模式同步性能:")
            print(f"   测试次数: {offline['iterations']} 次")
            print(f"   平均耗时: {offline['avg_time']:.3f} 秒")
            print(f"   最快: {offline['min_time']:.3f} 秒, 最慢: {offline['max_time']:.3f} 秒")
            print(f"   数据量: {offline['events_count']} 事件, {offline['markets_count']} 市场, {offline['tags_count']} 标签")
            print(f"   吞吐量: {offline['throughput']['events_per_second']:.1f} 事件/秒, {offline['throughput']['markets_per_second']:.1f} 市场/秒")
            print()
        
        # API同步性能
        if "api_sync" in results:
            api = results["api_sync"]
            print("🌐 API模式同步性能:")
            if api.get("success"):
                print(f"   耗时: {api['duration']:.3f} 秒")
                print(f"   数据量: {api['events_count']} 事件, {api['markets_count']} 市场, {api['tags_count']} 标签")
                print(f"   吞吐量: {api['throughput']['events_per_second']:.1f} 事件/秒, {api['throughput']['markets_per_second']:.1f} 市场/秒")
            else:
                print(f"   ❌ 同步失败: {api.get('error', '未知错误')}")
            print()
        
        # 文件操作性能
        if "file_operations" in results:
            file_ops = results["file_operations"]
            if "error" not in file_ops:
                print("📁 文件操作性能:")
                print(f"   扫描耗时: {file_ops['duration']:.3f} 秒")
                print(f"   文件数量: {file_ops['files_scanned']} 个")
                print(f"   总大小: {file_ops['total_size_mb']:.2f} MB")
                print(f"   速度: {file_ops['throughput']['files_per_second']:.1f} 文件/秒, {file_ops['throughput']['mb_per_second']:.1f} MB/秒")
            print()
        
        # 性能总结
        print("🎯 性能总结:")
        if "offline_sync" in results:
            offline = results["offline_sync"]
            events_count = offline['events_count']
            markets_count = offline['markets_count']
            avg_time = offline['avg_time']
            
            print(f"   ⚡ 离线同步: {avg_time:.2f}秒 处理 {events_count}事件 + {markets_count}市场")
            print(f"   📈 处理速度: {(events_count + markets_count) / avg_time:.1f} 条记录/秒")
            
            # 预估不同数据量的同步时间
            print(f"   📊 预估同步时间:")
            for scale, multiplier in [("小规模(100事件)", 4), ("中规模(500事件)", 20), ("大规模(1000事件)", 40)]:
                estimated_time = avg_time * multiplier
                print(f"      {scale}: ~{estimated_time:.1f}秒")
        
        print("="*80)
    
    def save_results(self, summary: Dict[str, Any], filename: str = None):
        """保存测试结果到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sync_performance_{timestamp}.json"
        
        os.makedirs(os.path.join(self.data_dir, "performance"), exist_ok=True)
        filepath = os.path.join(self.data_dir, "performance", filename)
        
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"💾 性能测试结果已保存到: {filepath}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket同步性能测试")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--mode", choices=["offline", "api", "generation", "files", "full"], 
                       default="full", help="测试模式")
    parser.add_argument("--iterations", type=int, default=3, help="离线测试迭代次数")
    parser.add_argument("--save", action="store_true", help="保存结果到文件")
    
    args = parser.parse_args()
    
    tester = SyncPerformanceTest(args.data_dir)
    
    if args.mode == "offline":
        result = tester.test_offline_sync(args.iterations)
        summary = {"results": {"offline_sync": result}}
    elif args.mode == "api":
        result = tester.test_api_sync()
        summary = {"results": {"api_sync": result}}
    elif args.mode == "generation":
        result = tester.test_data_generation()
        summary = {"results": {"data_generation": result}}
    elif args.mode == "files":
        result = tester.benchmark_file_operations()
        summary = {"results": {"file_operations": result}}
    else:
        summary = tester.run_full_benchmark()
    
    tester.print_results(summary)
    
    if args.save:
        tester.save_results(summary)

if __name__ == "__main__":
    main()