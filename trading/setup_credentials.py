#!/usr/bin/env python3
"""
Polymarket私钥设置工具
"""

import os
import json
import getpass
from typing import Dict

def setup_credentials():
    """交互式设置私钥"""
    print("🔐 Polymarket私钥设置")
    print("="*50)
    print("请准备你的以太坊私钥用于Polymarket交易")
    print("⚠️  私钥将用于签名交易，请确保安全保存")
    print()
    
    # 获取私钥
    private_key = getpass.getpass("请输入私钥 (0x开头): ").strip()
    
    if not private_key:
        print("❌ 私钥是必需的")
        return False
    
    # 验证私钥格式
    if not private_key.startswith('0x'):
        print("⚠️  私钥应以0x开头，自动添加前缀")
        private_key = '0x' + private_key
    

    
    # 选择网络
    print("\n网络选择:")
    print("1. 测试网 (Polygon Amoy - 推荐用于测试)")
    print("2. 主网 (Polygon - 实际交易)")
    
    while True:
        choice = input("请选择网络 (1/2): ").strip()
        if choice == '1':
            use_testnet = True
            break
        elif choice == '2':
            use_testnet = False
            print("⚠️  警告: 你选择了主网，这将使用真实资金进行交易!")
            confirm = input("确认使用主网? (yes/no): ").strip().lower()
            if confirm == 'yes':
                break
            else:
                continue
        else:
            print("请输入 1 或 2")
    
    # 交易参数设置
    print("\n📊 交易参数设置:")
    
    try:
        default_trade_amount = float(input("默认交易金额 (USDC) [10.0]: ") or "10.0")
        max_slippage = float(input("最大滑点 (0.02 = 2%) [0.02]: ") or "0.02")
        max_position_size = float(input("最大仓位大小 (USDC) [100.0]: ") or "100.0")
        min_confidence = float(input("最小置信度 (0.85 = 85%) [0.85]: ") or "0.85")
    except ValueError:
        print("❌ 参数格式错误，使用默认值")
        default_trade_amount = 10.0
        max_slippage = 0.02
        max_position_size = 100.0
        min_confidence = 0.85
    
    # 安全设置
    print("\n🛡️  安全设置:")
    auto_trade = input("启用自动交易? (y/n) [n]: ").strip().lower() == 'y'
    dry_run = input("默认使用模拟模式? (y/n) [y]: ").strip().lower() != 'n'
    require_confirmation = input("交易前需要确认? (y/n) [y]: ").strip().lower() != 'n'
    
    # 创建配置
    config = {
        "polymarket": {
            "host": "https://clob.polymarket.com",
            "chain_id": 137,
            "private_key": "" if not use_testnet else "",
            "testnet": {
                "host": "https://clob-staging.polymarket.com",
                "chain_id": 80002,
                "private_key": ""
            }
        },
        "trading": {
            "default_trade_amount": default_trade_amount,
            "max_slippage": max_slippage,
            "order_timeout": 300,
            "max_position_size": max_position_size,
            "max_daily_trades": 10,
            "min_confidence": min_confidence,
            "auto_trade_enabled": auto_trade,
            "dry_run_mode": dry_run
        },
        "strategy": {
            "time_threshold_minutes": 30,
            "min_confidence": 0.85,
            "max_confidence": 0.95,
            "batch_size": 100,
            "max_retries": 3
        },
        "security": {
            "use_testnet": use_testnet,
            "require_confirmation": require_confirmation,
            "max_gas_price": "50000000000"
        }
    }
    
    # 设置私钥到对应网络
    if use_testnet:
        config["polymarket"]["testnet"]["private_key"] = private_key
    else:
        config["polymarket"]["private_key"] = private_key
    
    # 保存配置
    config_file = "config/sys_config.json"
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ 配置已保存到: {config_file}")
        print(f"🌐 网络: {'测试网 (Polygon Amoy)' if use_testnet else '主网 (Polygon)'}")
        print(f"💰 默认交易金额: ${default_trade_amount} USDC")
        print(f"🎭 模拟模式: {'启用' if dry_run else '禁用'}")
        print(f"🤖 自动交易: {'启用' if auto_trade else '禁用'}")
        print(f"🛡️  需要确认: {'是' if require_confirmation else '否'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False


def setup_environment_variables():
    """设置环境变量"""
    print("\n🌍 环境变量设置")
    print("你也可以通过环境变量来配置私钥:")
    print()
    print("export POLYMARKET_PRIVATE_KEY='0x1234567890abcdef...'")
    print("export DEFAULT_TRADE_AMOUNT='10.0'")
    print("export MAX_SLIPPAGE='0.02'")
    print("export DRY_RUN_MODE='true'")
    print()
    print("将这些命令添加到你的 ~/.bashrc 或 ~/.zshrc 文件中")


def test_credentials():
    """测试私钥配置"""
    print("\n🧪 测试私钥配置...")
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from trading.polymarket_clob_client import PolymarketCLOBClient
        from trading.config import TradingConfig
        
        config = TradingConfig()
        
        if not config.is_configured():
            print("❌ 私钥未配置")
            return False
        
        # 创建客户端
        client = PolymarketCLOBClient(**config.get_client_config())
        
        print(f"✅ 客户端创建成功!")
        print(f"🌐 网络: {'测试网' if config.use_testnet else '主网'}")
        print(f"📍 地址: {client.address}")
        print(f"🔗 主机: {client.host}")
        print(f"⛓️  链ID: {client.chain_id}")
        
        # 测试连接（获取余额）
        try:
            balance = client.get_balance()
            print("✅ API连接成功!")
            print(f"💰 USDC余额: ${balance.get('usdcBalance', '0')}")
        except Exception as e:
            print(f"⚠️  API连接测试失败: {e}")
            print("这可能是因为账户没有余额或网络问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def validate_private_key(private_key: str) -> bool:
    """验证私钥格式"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from eth_account import Account
        
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # 尝试创建账户
        account = Account.from_key(private_key)
        print(f"✅ 私钥有效，对应地址: {account.address}")
        return True
        
    except Exception as e:
        print(f"❌ 私钥无效: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket私钥设置工具")
    parser.add_argument("--test", action="store_true", help="测试现有配置")
    parser.add_argument("--env", action="store_true", help="显示环境变量设置方法")
    parser.add_argument("--validate", help="验证私钥格式")
    
    args = parser.parse_args()
    
    if args.test:
        test_credentials()
    elif args.env:
        setup_environment_variables()
    elif args.validate:
        validate_private_key(args.validate)
    else:
        success = setup_credentials()
        
        if success:
            print("\n🎉 设置完成! 现在你可以:")
            print("1. 运行策略交易器: python3 trading/strategy_trader.py")
            print("2. 测试配置: python3 trading/setup_credentials.py --test")
            print("3. 查看使用指南: cat TRADING_GUIDE.md")
            print("\n⚠️  重要提醒:")
            print("- 私钥已保存到配置文件，请确保文件安全")
            print("- 建议先在测试网验证功能")
            print("- 不要将包含私钥的配置文件提交到版本控制")


if __name__ == "__main__":
    main()