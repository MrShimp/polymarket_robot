#!/usr/bin/env python3
"""
BTC自动交易器监控脚本
实时监控btc_auto_trader.py的运行状态和策略执行情况
"""

import os
import time
import json
import subprocess
import glob
from datetime import datetime
from typing import Optional, Dict, List

class AutoTraderMonitor:
    """自动交易器监控器"""
    
    def __init__(self):
        self.log_dirs = {
            'auto_trader': 'data/auto_trader_logs',
            'strategy': 'data/btc_strategy_logs',
            'trades': 'data/btc_trades',
            'intervals': 'data/btc_intervals'
        }
    
    def get_latest_log_file(self, log_type: str) -> Optional[str]:
        """获取最新的日志文件"""
        log_dir = self.log_dirs.get(log_type)
        if not log_dir or not os.path.exists(log_dir):
            return None
        
        if log_type == 'auto_trader':
            pattern = f"{log_dir}/auto_trader_*.log"
        elif log_type == 'strategy':
            pattern = f"{log_dir}/btc_15min_*.log"
        else:
            return None
        
        files = glob.glob(pattern)
        if not files:
            return None
        
        # 返回最新的文件
        return max(files, key=os.path.getctime)
    
    def get_running_processes(self) -> List[Dict]:
        """获取运行中的相关进程"""
        processes = []
        
        try:
            # 查找btc_auto_trader.py进程
            result = subprocess.run([
                'pgrep', '-f', 'btc_auto_trader.py'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        processes.append({
                            'type': 'auto_trader',
                            'pid': pid,
                            'name': 'btc_auto_trader.py'
                        })
            
            # 查找btc_15min_strategy.py进程
            result = subprocess.run([
                'pgrep', '-f', 'btc_15min_strategy.py'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        processes.append({
                            'type': 'strategy',
                            'pid': pid,
                            'name': 'btc_15min_strategy.py'
                        })
        
        except Exception as e:
            print(f"获取进程信息失败: {e}")
        
        return processes
    
    def get_latest_trades(self, limit: int = 5) -> List[Dict]:
        """获取最新的交易记录"""
        trades_dir = self.log_dirs['trades']
        if not os.path.exists(trades_dir):
            return []
        
        trade_files = glob.glob(f"{trades_dir}/btc_trade_*.json")
        if not trade_files:
            return []
        
        # 按修改时间排序
        trade_files.sort(key=os.path.getmtime, reverse=True)
        
        trades = []
        for file_path in trade_files[:limit]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    trade_data = json.load(f)
                    trades.append(trade_data)
            except Exception as e:
                print(f"读取交易文件失败 {file_path}: {e}")
        
        return trades
    
    def tail_log_file(self, file_path: str, lines: int = 10) -> List[str]:
        """获取日志文件的最后几行"""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) >= lines else all_lines
        except Exception as e:
            return [f"读取日志失败: {e}"]
    
    def display_status(self):
        """显示当前状态"""
        print("🤖 BTC自动交易器监控面板")
        print("=" * 80)
        print(f"📅 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. 进程状态
        print("🔄 进程状态:")
        processes = self.get_running_processes()
        if processes:
            for proc in processes:
                print(f"   ✅ {proc['name']} (PID: {proc['pid']})")
        else:
            print("   ❌ 没有发现运行中的进程")
        print()
        
        # 2. 自动交易器日志
        print("📊 自动交易器状态:")
        auto_trader_log = self.get_latest_log_file('auto_trader')
        if auto_trader_log:
            print(f"   日志文件: {os.path.basename(auto_trader_log)}")
            recent_logs = self.tail_log_file(auto_trader_log, 5)
            for log_line in recent_logs:
                print(f"   {log_line.strip()}")
        else:
            print("   ❌ 未找到自动交易器日志")
        print()
        
        # 3. 策略执行状态
        print("🎯 策略执行状态:")
        strategy_log = self.get_latest_log_file('strategy')
        if strategy_log:
            print(f"   日志文件: {os.path.basename(strategy_log)}")
            recent_logs = self.tail_log_file(strategy_log, 5)
            for log_line in recent_logs:
                print(f"   {log_line.strip()}")
        else:
            print("   ❌ 未找到策略执行日志")
        print()
        
        # 4. 最新交易记录
        print("💰 最新交易记录:")
        trades = self.get_latest_trades(3)
        if trades:
            for i, trade in enumerate(trades, 1):
                timestamp = trade.get('timestamp', 'Unknown')
                outcome = trade.get('outcome', 'Unknown')
                profit = trade.get('profit', 0)
                profit_pct = trade.get('profit_pct', 0)
                exit_reason = trade.get('exit_reason', 'Unknown')
                
                print(f"   {i}. {timestamp}")
                print(f"      方向: {outcome}, 盈利: ${profit:.2f} ({profit_pct:.1f}%)")
                print(f"      退出原因: {exit_reason}")
        else:
            print("   ❌ 未找到交易记录")
        print()
    
    def monitor_continuously(self, interval: int = 30):
        """持续监控模式"""
        print("🚀 启动持续监控模式")
        print(f"⏰ 刷新间隔: {interval}秒")
        print("💡 按 Ctrl+C 停止监控")
        print()
        
        try:
            while True:
                # 清屏
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # 显示状态
                self.display_status()
                
                # 等待
                print(f"⏰ {interval}秒后刷新... (Ctrl+C 停止)")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
    
    def show_detailed_logs(self, log_type: str, lines: int = 50):
        """显示详细日志"""
        log_file = self.get_latest_log_file(log_type)
        if not log_file:
            print(f"❌ 未找到 {log_type} 日志文件")
            return
        
        print(f"📋 {log_type} 详细日志 (最后{lines}行):")
        print("=" * 80)
        
        log_lines = self.tail_log_file(log_file, lines)
        for line in log_lines:
            print(line.strip())
    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print("\n🤖 BTC自动交易器监控菜单")
            print("=" * 40)
            print("1. 显示当前状态")
            print("2. 持续监控模式")
            print("3. 查看自动交易器详细日志")
            print("4. 查看策略执行详细日志")
            print("5. 查看最新交易记录")
            print("6. 查看进程状态")
            print("0. 退出")
            print()
            
            try:
                choice = input("请选择操作 (0-6): ").strip()
                
                if choice == '0':
                    print("👋 再见！")
                    break
                elif choice == '1':
                    self.display_status()
                elif choice == '2':
                    interval = input("请输入刷新间隔(秒，默认30): ").strip()
                    interval = int(interval) if interval.isdigit() else 30
                    self.monitor_continuously(interval)
                elif choice == '3':
                    lines = input("显示行数(默认50): ").strip()
                    lines = int(lines) if lines.isdigit() else 50
                    self.show_detailed_logs('auto_trader', lines)
                elif choice == '4':
                    lines = input("显示行数(默认50): ").strip()
                    lines = int(lines) if lines.isdigit() else 50
                    self.show_detailed_logs('strategy', lines)
                elif choice == '5':
                    trades = self.get_latest_trades(10)
                    if trades:
                        print("\n💰 最新10笔交易记录:")
                        print("=" * 80)
                        for i, trade in enumerate(trades, 1):
                            print(f"{i}. {trade.get('timestamp', 'Unknown')}")
                            print(f"   方向: {trade.get('outcome', 'Unknown')}")
                            print(f"   盈利: ${trade.get('profit', 0):.2f} ({trade.get('profit_pct', 0):.1f}%)")
                            print(f"   退出原因: {trade.get('exit_reason', 'Unknown')}")
                            print()
                    else:
                        print("❌ 未找到交易记录")
                elif choice == '6':
                    processes = self.get_running_processes()
                    print("\n🔄 进程状态:")
                    print("=" * 40)
                    if processes:
                        for proc in processes:
                            print(f"✅ {proc['name']} (PID: {proc['pid']})")
                    else:
                        print("❌ 没有发现运行中的进程")
                else:
                    print("❌ 无效选择，请重试")
                    
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

def main():
    """主函数"""
    import sys
    
    monitor = AutoTraderMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            monitor.display_status()
        elif sys.argv[1] == 'monitor':
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            monitor.monitor_continuously(interval)
        elif sys.argv[1] == 'logs':
            log_type = sys.argv[2] if len(sys.argv) > 2 else 'auto_trader'
            lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            monitor.show_detailed_logs(log_type, lines)
        else:
            print("用法:")
            print("  python3 monitor_auto_trader.py status          # 显示状态")
            print("  python3 monitor_auto_trader.py monitor [间隔]   # 持续监控")
            print("  python3 monitor_auto_trader.py logs [类型] [行数] # 查看日志")
    else:
        monitor.interactive_menu()

if __name__ == "__main__":
    main()