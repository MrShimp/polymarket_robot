#!/usr/bin/env python3
"""
BTC 15分钟策略启动脚本
快速启动指定市场的BTC策略交易
"""

import sys
import os
import asyncio
import json
import requests
from datetime import datetime
import signal

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from btc_15min_strategy import BTC15MinStrategy

# 预设的BTC市场配置
BTC_MARKETS = {
    "btc_100k": {
        "name": "BTC达到$100,000",
        "description": "Bitcoin价格是否会达到$100,000",
        "baseline_price": 95000.0,
        "market_id": ""  # 需要填入实际的market_id
    },
    "btc_weekly": {
        "name": "BTC本周涨跌",
        "description": "Bitcoin本周是否上涨",
        "baseline_price": 95000.0,
        "market_id": ""  # 需要填入实际的market_id
    },
    "btc_daily": {
        "name": "BTC今日涨跌",
        "description": "Bitcoin今日是否上涨",
        "baseline_price": 95000.0,
        "market_id": ""  # 需要填入实际的market_id
    }
}

class BTCStrategyLauncher:
    """BTC策略启动器"""
    
    def __init__(self):
        self.strategy = None
        self.running = False
    
    def show_banner(self):
        """显示启动横幅"""
        print("🚀 BTC 15分钟策略启动器")
        print("=" * 60)
        print("📊 双向交易策略 | 智能止盈止损 | 实时价格监控")
        print("⏰ 交易时段: 10:00-19:00 北京时间")
        print("💡 买入限制: 区间开始5分钟后 | 卖出无限制")
        print("=" * 60)
    
    def get_current_btc_price(self) -> float:
        """获取当前BTC价格"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except Exception as e:
            print(f"⚠️ 获取BTC价格失败: {e}")
            return None
    
    def validate_market_id(self, market_id: str) -> bool:
        """验证市场ID格式"""
        if not market_id:
            return False
        
        # 检查是否是有效的十六进制地址格式
        if market_id.startswith('0x') and len(market_id) == 42:
            return True
        
        # 或者其他有效格式
        if len(market_id) > 10:
            return True
        
        return False
    
    def show_market_options(self):
        """显示市场选项"""
        print("\n📋 预设BTC市场:")
        for key, market in BTC_MARKETS.items():
            status = "✅ 已配置" if market["market_id"] else "❌ 需配置"
            print(f"   {key}: {market['name']} - {status}")
        print("   custom: 自定义市场ID")
    
    def get_market_selection(self) -> tuple:
        """获取市场选择"""
        self.show_market_options()
        
        while True:
            choice = input("\n🎯 选择市场 (输入key或custom): ").strip().lower()
            
            if choice in BTC_MARKETS:
                market = BTC_MARKETS[choice]
                if not market["market_id"]:
                    print(f"❌ {choice} 市场ID未配置，请选择custom输入")
                    continue
                return market["market_id"], market["baseline_price"], market["name"]
            
            elif choice == "custom":
                market_id = input("📝 输入市场ID: ").strip()
                if not self.validate_market_id(market_id):
                    print("❌ 市场ID格式无效")
                    continue
                
                # 获取基准价格
                current_price = self.get_current_btc_price()
                if current_price:
                    default_baseline = int(current_price)
                    baseline_input = input(f"📊 输入基准价格 [默认{default_baseline}]: ").strip()
                    baseline_price = float(baseline_input) if baseline_input else default_baseline
                else:
                    baseline_price = float(input("📊 输入基准价格: ").strip())
                
                return market_id, baseline_price, "自定义市场"
            
            else:
                print("❌ 无效选择，请重新输入")
    
    def get_trading_params(self) -> dict:
        """获取交易参数"""
        print("\n💰 交易参数设置:")
        
        # 交易金额
        while True:
            try:
                amount_input = input("💵 交易金额 (USDC) [默认10]: ").strip()
                amount = float(amount_input) if amount_input else 10.0
                if amount <= 0:
                    print("❌ 金额必须大于0")
                    continue
                break
            except ValueError:
                print("❌ 金额格式错误")
        
        # 测试模式
        testnet_input = input("🧪 使用测试网络? (y/n) [默认n]: ").strip().lower()
        use_testnet = testnet_input in ['y', 'yes', '是']
        
        # 确认模式
        confirm_input = input("⚠️ 需要交易确认? (y/n) [默认n]: ").strip().lower()
        require_confirm = confirm_input in ['y', 'yes', '是']
        
        return {
            'amount': amount,
            'use_testnet': use_testnet,
            'require_confirm': require_confirm
        }
    
    def show_strategy_summary(self, market_id: str, market_name: str, baseline_price: float, params: dict):
        """显示策略摘要"""
        current_price = self.get_current_btc_price()
        
        print("\n📊 策略配置摘要:")
        print("=" * 50)
        print(f"🎯 市场: {market_name}")
        print(f"🆔 Market ID: {market_id[:10]}...{market_id[-8:]}")
        print(f"💰 交易金额: ${params['amount']}")
        print(f"📈 基准价格: ${baseline_price:,.2f}")
        if current_price:
            diff = current_price - baseline_price
            print(f"📊 当前价格: ${current_price:,.2f} ({diff:+.2f})")
        print(f"🌐 网络: {'测试网' if params['use_testnet'] else '主网'}")
        print(f"✅ 确认模式: {'开启' if params['require_confirm'] else '关闭'}")
        print("=" * 50)
        
        print("\n🎯 策略规则:")
        print("   📈 入场: YES/NO概率≥75% + 价格波动≥$32")
        print("   🎯 止盈: 概率≥90%")
        print("   🛑 止损: 概率≤55%")
        print("   ⚡ 特殊止盈: 85%+横盘30秒")
        print("   ⏰ 买入窗口: 区间开始5分钟后")
        print("   💸 卖出窗口: 无限制")
    
    async def start_strategy(self, market_id: str, baseline_price: float, params: dict):
        """启动策略"""
        try:
            # 创建策略实例
            self.strategy = BTC15MinStrategy(
                use_testnet=params['use_testnet'],
                baseline_price=baseline_price
            )
            
            print(f"\n🚀 启动BTC 15分钟策略...")
            print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 启动策略
            self.running = True
            await self.strategy.start_strategy(market_id, params['amount'])
            
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断策略")
            self.stop_strategy()
        except Exception as e:
            print(f"\n❌ 策略执行错误: {e}")
            self.stop_strategy()
    
    def stop_strategy(self):
        """停止策略"""
        if self.strategy:
            self.strategy.stop()
        self.running = False
        print("🛑 策略已停止")
    
    async def run_interactive(self):
        """交互式运行"""
        self.show_banner()
        
        try:
            # 获取市场选择
            market_id, baseline_price, market_name = self.get_market_selection()
            
            # 获取交易参数
            params = self.get_trading_params()
            
            # 显示摘要
            self.show_strategy_summary(market_id, market_name, baseline_price, params)
            
            # 最终确认
            if not params['require_confirm']:
                confirm = input(f"\n❓ 确认启动策略? (y/n): ").strip().lower()
                if confirm not in ['y', 'yes', '是']:
                    print("❌ 已取消")
                    return
            
            # 启动策略
            await self.start_strategy(market_id, baseline_price, params)
            
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断")
        except Exception as e:
            print(f"\n❌ 启动错误: {e}")
    
    def run_with_args(self, args):
        """使用命令行参数运行"""
        if len(args) < 2:
            print("❌ 参数不足")
            print("用法: python3 start_btc_15min_strategy.py <market_id> [amount] [baseline_price] [--testnet]")
            return
        
        market_id = args[1]
        amount = float(args[2]) if len(args) > 2 else 10.0
        baseline_price = float(args[3]) if len(args) > 3 else self.get_current_btc_price() or 95000.0
        use_testnet = '--testnet' in args
        
        if not self.validate_market_id(market_id):
            print("❌ 市场ID格式无效")
            return
        
        params = {
            'amount': amount,
            'use_testnet': use_testnet,
            'require_confirm': False
        }
        
        self.show_banner()
        self.show_strategy_summary(market_id, "命令行指定", baseline_price, params)
        
        # 启动策略
        asyncio.run(self.start_strategy(market_id, baseline_price, params))


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在安全退出...")
    sys.exit(0)


def show_help():
    """显示帮助信息"""
    print("🚀 BTC 15分钟策略启动器")
    print("=" * 50)
    print()
    print("📋 使用方法:")
    print("   1. 交互模式: python3 start_btc_15min_strategy.py")
    print("   2. 命令行模式: python3 start_btc_15min_strategy.py <market_id> [amount] [baseline_price] [--testnet]")
    print()
    print("💡 示例:")
    print("   # 交互模式")
    print("   python3 start_btc_15min_strategy.py")
    print()
    print("   # 命令行模式")
    print("   python3 start_btc_15min_strategy.py 0x1234...abcd 15.0 95000")
    print("   python3 start_btc_15min_strategy.py 0x1234...abcd 10.0 95000 --testnet")
    print()
    print("📊 参数说明:")
    print("   market_id: Polymarket市场ID (必需)")
    print("   amount: 交易金额USDC (可选，默认10)")
    print("   baseline_price: 基准价格 (可选，默认当前价格)")
    print("   --testnet: 使用测试网络 (可选)")
    print()
    print("🎯 策略特点:")
    print("   • 双向交易: YES/NO概率>75%均可入场")
    print("   • 智能止盈: 90%概率或85%+横盘30秒")
    print("   • 风险控制: 55%概率止损")
    print("   • 时间管理: 买入有窗口限制，卖出无限制")


async def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
        return
    
    # 创建启动器
    launcher = BTCStrategyLauncher()
    
    # 根据参数决定运行模式
    if len(sys.argv) > 1:
        # 命令行模式
        launcher.run_with_args(sys.argv)
    else:
        # 交互模式
        await launcher.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 程序错误: {e}")