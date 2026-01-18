#!/usr/bin/env python3
"""
策略交易执行器 - 集成策略扫描和自动交易
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.flexible_urgent_strategy import FlexibleUrgentStrategy
from trading.polymarket_clob_client import PolymarketCLOBClient, PolymarketTrader
from trading.config import TradingConfig

# 创建配置实例
config = TradingConfig()

class StrategyTrader:
    """策略交易执行器"""
    
    def __init__(self, 
                 strategy_config: Dict = None,
                 trading_config: Dict = None,
                 dry_run: bool = True):
        """
        初始化策略交易器
        
        Args:
            strategy_config: 策略配置
            trading_config: 交易配置
            dry_run: 是否为模拟交易
        """
        # 策略配置
        self.strategy_config = strategy_config or {
            'time_threshold_minutes': 30,
            'min_confidence': 0.85,
            'max_confidence': 0.95
        }
        
        # 交易配置
        self.trading_config = trading_config or {
            'trade_amount': config.default_trade_amount,
            'max_slippage': config.max_slippage,
            'order_timeout': config.order_timeout
        }
        
        self.dry_run = dry_run or config.dry_run_mode
        
        # 初始化策略
        self.strategy = FlexibleUrgentStrategy(
            data_dir="./data",
            time_threshold_minutes=self.strategy_config['time_threshold_minutes'],
            min_confidence=self.strategy_config['min_confidence'],
            max_confidence=self.strategy_config['max_confidence']
        )
        
        # 初始化交易客户端
        self.clob_client = None
        self.trader = None
        
        if config.is_configured():
            try:
                client_config = config.get_client_config()
                self.clob_client = PolymarketCLOBClient(
                    host=client_config['host'],
                    chain_id=client_config['chain_id'],
                    private_key=client_config['private_key'],
                    use_testnet=client_config['use_testnet']
                )
                self.trader = PolymarketTrader(self.clob_client)
                print(f"✅ 交易客户端已初始化 ({'测试网' if config.use_testnet else '主网'})")
                print(f"📍 钱包地址: {self.clob_client.address}")
            except Exception as e:
                print(f"❌ 交易客户端初始化失败: {e}")
        else:
            print("⚠️  私钥未配置，仅运行策略扫描")
        
        # 交易统计
        self.trade_stats = {
            'total_scans': 0,
            'opportunities_found': 0,
            'trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0
        }
    
    def scan_and_trade(self) -> Dict:
        """扫描市场并执行交易"""
        scan_start_time = datetime.now()
        
        print(f"\n🔍 开始策略扫描 - {scan_start_time.strftime('%H:%M:%S')}")
        print("-" * 50)
        
        try:
            # 执行策略扫描
            strategy_result = self.strategy.run_strategy(save_to_file=True)
            self.trade_stats['total_scans'] += 1
            
            if not strategy_result['success']:
                return {
                    'success': False,
                    'error': f"策略扫描失败: {strategy_result.get('error', 'Unknown error')}",
                    'scan_time': scan_start_time.isoformat()
                }
            
            opportunities = strategy_result.get('markets', [])
            self.trade_stats['opportunities_found'] += len(opportunities)
            
            print(f"📊 扫描结果: 发现 {len(opportunities)} 个交易机会")
            
            if not opportunities:
                return {
                    'success': True,
                    'message': '未发现符合条件的交易机会',
                    'scan_time': scan_start_time.isoformat(),
                    'scan_duration': strategy_result.get('duration_seconds', 0)
                }
            
            # 执行交易
            trade_results = []
            
            for i, opportunity in enumerate(opportunities[:3], 1):  # 最多交易前3个机会
                print(f"\n💡 处理机会 {i}: {opportunity.get('question', 'Unknown')[:60]}...")
                
                # 验证交易参数
                confidence = float(opportunity.get('strategy_confidence', 0))
                validation = config.validate_trade_params(
                    self.trading_config['trade_amount'], 
                    confidence
                )
                
                if not validation['valid']:
                    print(f"❌ 交易参数验证失败: {', '.join(validation['errors'])}")
                    trade_results.append({
                        'opportunity_id': opportunity.get('id'),
                        'success': False,
                        'error': 'Parameter validation failed',
                        'validation_errors': validation['errors']
                    })
                    continue
                
                # 执行交易
                if self.trader:
                    trade_result = self.execute_trade(opportunity)
                    trade_results.append(trade_result)
                else:
                    # 模拟交易
                    trade_result = self.simulate_trade(opportunity)
                    trade_results.append(trade_result)
            
            # 更新统计
            successful_trades = sum(1 for r in trade_results if r.get('success', False))
            self.trade_stats['trades_executed'] += len(trade_results)
            self.trade_stats['successful_trades'] += successful_trades
            self.trade_stats['failed_trades'] += len(trade_results) - successful_trades
            
            return {
                'success': True,
                'scan_time': scan_start_time.isoformat(),
                'scan_duration': strategy_result.get('duration_seconds', 0),
                'opportunities_found': len(opportunities),
                'trades_attempted': len(trade_results),
                'successful_trades': successful_trades,
                'trade_results': trade_results,
                'strategy_result': strategy_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"扫描和交易过程失败: {str(e)}",
                'scan_time': scan_start_time.isoformat()
            }
    
    def execute_trade(self, opportunity: Dict) -> Dict:
        """执行实际交易"""
        try:
            print(f"🚀 执行交易 ({'模拟' if self.dry_run else '实盘'})")
            
            # 执行交易
            trade_result = self.trader.execute_strategy_trade(
                market_data=opportunity,
                trade_amount=str(self.trading_config['trade_amount']),
                max_slippage=self.trading_config['max_slippage'],
                dry_run=self.dry_run
            )
            
            if trade_result['success']:
                print(f"✅ 交易成功提交")
                print(f"   市场: {trade_result.get('market_question', 'Unknown')[:50]}...")
                print(f"   选项: {trade_result.get('winning_option')} (置信度: {trade_result.get('confidence', 0):.3f})")
                print(f"   金额: ${trade_result.get('trade_amount')} USDC")
                
                if not self.dry_run and 'order_id' in trade_result:
                    # 监控订单状态
                    print(f"📊 监控订单: {trade_result['order_id']}")
                    monitor_result = self.trader.monitor_order(
                        trade_result['order_id'],
                        self.trading_config['order_timeout']
                    )
                    trade_result['monitor_result'] = monitor_result
                
                # 更新统计
                self.trade_stats['total_volume'] += float(trade_result.get('trade_amount', 0))
                
            else:
                print(f"❌ 交易失败: {trade_result.get('error', 'Unknown error')}")
            
            return trade_result
            
        except Exception as e:
            error_msg = f"交易执行异常: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'opportunity_id': opportunity.get('id')
            }
    
    def simulate_trade(self, opportunity: Dict) -> Dict:
        """模拟交易"""
        print(f"🎭 模拟交易")
        
        confidence = float(opportunity.get('strategy_confidence', 0))
        winning_option = opportunity.get('strategy_winning_option', '')
        trade_amount = self.trading_config['trade_amount']
        
        print(f"   市场: {opportunity.get('question', 'Unknown')[:50]}...")
        print(f"   选项: {winning_option} (置信度: {confidence:.3f})")
        print(f"   金额: ${trade_amount} USDC")
        print(f"   剩余时间: {opportunity.get('strategy_time_remaining_minutes', 0)} 分钟")
        
        # 模拟交易结果
        return {
            'success': True,
            'simulated': True,
            'opportunity_id': opportunity.get('id'),
            'market_question': opportunity.get('question'),
            'winning_option': winning_option,
            'confidence': confidence,
            'trade_amount': trade_amount,
            'time_remaining': opportunity.get('strategy_time_remaining_minutes', 0)
        }
    
    def get_account_status(self) -> Dict:
        """获取账户状态"""
        if not self.trader:
            return {
                'success': False,
                'error': '交易客户端未初始化'
            }
        
        try:
            return self.trader.get_trading_summary()
        except Exception as e:
            return {
                'success': False,
                'error': f'获取账户状态失败: {str(e)}'
            }
    
    def print_statistics(self):
        """打印交易统计"""
        print("\n" + "="*60)
        print("📈 交易统计")
        print("="*60)
        print(f"总扫描次数: {self.trade_stats['total_scans']}")
        print(f"发现机会: {self.trade_stats['opportunities_found']}")
        print(f"执行交易: {self.trade_stats['trades_executed']}")
        print(f"成功交易: {self.trade_stats['successful_trades']}")
        print(f"失败交易: {self.trade_stats['failed_trades']}")
        print(f"总交易量: ${self.trade_stats['total_volume']:.2f} USDC")
        
        if self.trade_stats['trades_executed'] > 0:
            success_rate = self.trade_stats['successful_trades'] / self.trade_stats['trades_executed']
            print(f"成功率: {success_rate:.1%}")
        
        print("="*60)
    
    def run_continuous_trading(self, 
                             interval_minutes: int = 10,
                             max_iterations: Optional[int] = None):
        """连续交易模式"""
        print(f"🚀 启动连续交易模式")
        print(f"📊 策略参数: 时间阈值={self.strategy_config['time_threshold_minutes']}分钟, "
              f"胜率范围={self.strategy_config['min_confidence']:.1%}-{self.strategy_config['max_confidence']:.1%}")
        print(f"💰 交易参数: 金额=${self.trading_config['trade_amount']} USDC, "
              f"最大滑点={self.trading_config['max_slippage']:.1%}")
        print(f"⏰ 扫描间隔: {interval_minutes}分钟")
        print(f"🎭 模式: {'模拟交易' if self.dry_run else '实盘交易'}")
        print("="*60)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                if max_iterations and iteration > max_iterations:
                    print(f"\n🏁 达到最大迭代次数: {max_iterations}")
                    break
                
                print(f"\n🔄 第{iteration}次扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 执行扫描和交易
                result = self.scan_and_trade()
                
                if result['success']:
                    opportunities = result.get('opportunities_found', 0)
                    trades = result.get('trades_attempted', 0)
                    successful = result.get('successful_trades', 0)
                    
                    print(f"✅ 扫描完成: 发现{opportunities}个机会, 执行{trades}笔交易, 成功{successful}笔")
                else:
                    print(f"❌ 扫描失败: {result.get('error', 'Unknown error')}")
                
                # 显示统计
                if iteration % 5 == 0:  # 每5次显示一次统计
                    self.print_statistics()
                
                # 等待下次扫描
                if max_iterations is None or iteration < max_iterations:
                    print(f"\n💤 等待 {interval_minutes} 分钟后进行下次扫描...")
                    time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 用户中断，交易已停止")
        except Exception as e:
            print(f"\n❌ 连续交易异常: {e}")
        finally:
            self.print_statistics()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="策略交易执行器")
    parser.add_argument("--mode", choices=['single', 'continuous'], default='single', 
                       help="运行模式: single(单次) 或 continuous(连续)")
    parser.add_argument("--interval", type=int, default=10, help="连续模式的扫描间隔（分钟）")
    parser.add_argument("--max-iter", type=int, help="最大迭代次数")
    parser.add_argument("--time", type=int, default=30, help="策略时间阈值（分钟）")
    parser.add_argument("--min-conf", type=float, default=0.85, help="最小胜率")
    parser.add_argument("--max-conf", type=float, default=0.95, help="最大胜率")
    parser.add_argument("--trade-amount", type=float, default=10.0, help="交易金额（USDC）")
    parser.add_argument("--max-slippage", type=float, default=0.02, help="最大滑点")
    parser.add_argument("--real-trade", action="store_true", help="执行实盘交易（默认为模拟）")
    parser.add_argument("--account-status", action="store_true", help="显示账户状态")
    
    args = parser.parse_args()
    
    # 策略配置
    strategy_config = {
        'time_threshold_minutes': args.time,
        'min_confidence': args.min_conf,
        'max_confidence': args.max_conf
    }
    
    # 交易配置
    trading_config = {
        'trade_amount': args.trade_amount,
        'max_slippage': args.max_slippage,
        'order_timeout': 300
    }
    
    # 创建交易器
    trader = StrategyTrader(
        strategy_config=strategy_config,
        trading_config=trading_config,
        dry_run=not args.real_trade
    )
    
    # 显示账户状态
    if args.account_status:
        print("📊 账户状态:")
        status = trader.get_account_status()
        if status['success']:
            print(f"  USDC余额: ${status.get('usdc_balance', '0')}")
            print(f"  持仓数量: {status.get('total_positions', 0)}")
            print(f"  活跃订单: {status.get('active_orders', 0)}")
            print(f"  总资产价值: ${status.get('total_portfolio_value', '0')}")
        else:
            print(f"  获取失败: {status.get('error', 'Unknown error')}")
        print()
    
    # 执行交易
    if args.mode == 'single':
        print("🎯 单次扫描和交易")
        result = trader.scan_and_trade()
        
        if result['success']:
            print(f"\n✅ 执行完成!")
            print(f"   发现机会: {result.get('opportunities_found', 0)} 个")
            print(f"   执行交易: {result.get('trades_attempted', 0)} 笔")
            print(f"   成功交易: {result.get('successful_trades', 0)} 笔")
        else:
            print(f"\n❌ 执行失败: {result.get('error', 'Unknown error')}")
    
    elif args.mode == 'continuous':
        trader.run_continuous_trading(
            interval_minutes=args.interval,
            max_iterations=args.max_iter
        )


if __name__ == "__main__":
    main()