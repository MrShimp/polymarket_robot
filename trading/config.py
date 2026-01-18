#!/usr/bin/env python3
"""
Polymarket交易配置文件
"""

import os
import json
from typing import Dict, Optional

class TradingConfig:
    """交易配置类"""
    
    def __init__(self, config_file: str = "config/sys_config.json"):
        self.config_file = config_file
        self.config_data = self._load_config()
        
        # Polymarket配置
        polymarket_config = self.config_data.get('polymarket', {})
        security_config = self.config_data.get('security', {})
        
        # 网络配置
        self.use_testnet = security_config.get('use_testnet', True)
        
        if self.use_testnet:
            testnet_config = polymarket_config.get('testnet', {})
            self.host = testnet_config.get('host', 'https://clob-staging.polymarket.com')
            self.chain_id = testnet_config.get('chain_id', 80002)  # Polygon Amoy testnet
            self.private_key = testnet_config.get('private_key', '')
        else:
            self.host = polymarket_config.get('host', 'https://clob.polymarket.com')
            self.chain_id = polymarket_config.get('chain_id', 137)  # Polygon mainnet
            self.private_key = polymarket_config.get('private_key', '')
        
        # 从环境变量覆盖私钥（如果存在）
        env_private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        if env_private_key:
            self.private_key = env_private_key
        
        # 交易参数
        trading_config = self.config_data.get('trading', {})
        self.default_trade_amount = float(trading_config.get('default_trade_amount', 10.0))
        self.max_slippage = float(trading_config.get('max_slippage', 0.02))
        self.order_timeout = int(trading_config.get('order_timeout', 300))
        
        # 风险管理
        self.max_position_size = float(trading_config.get('max_position_size', 100.0))
        self.max_daily_trades = int(trading_config.get('max_daily_trades', 10))
        self.min_confidence = float(trading_config.get('min_confidence', 0.85))
        
        # 策略参数
        self.auto_trade_enabled = trading_config.get('auto_trade_enabled', False)
        self.dry_run_mode = trading_config.get('dry_run_mode', True)
        
        # 安全配置
        self.require_confirmation = security_config.get('require_confirmation', True)
        self.max_gas_price = security_config.get('max_gas_price', '50000000000')
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  配置文件 {self.config_file} 不存在，使用默认配置")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式错误: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "polymarket": {
                "host": "https://clob.polymarket.com",
                "chain_id": 137,
                "private_key": "",
                "testnet": {
                    "host": "https://clob-staging.polymarket.com",
                    "chain_id": 80002,
                    "private_key": ""
                }
            },
            "trading": {
                "default_trade_amount": 10.0,
                "max_slippage": 0.02,
                "order_timeout": 300,
                "max_position_size": 100.0,
                "max_daily_trades": 10,
                "min_confidence": 0.85,
                "auto_trade_enabled": False,
                "dry_run_mode": True
            },
            "security": {
                "use_testnet": True,
                "require_confirmation": True,
                "max_gas_price": "50000000000"
            }
        }
    
    def is_configured(self) -> bool:
        """检查是否已配置私钥"""
        return bool(self.private_key and self.private_key.strip())
    
    def get_client_config(self) -> Dict:
        """获取客户端配置"""
        return {
            'host': self.host,
            'chain_id': self.chain_id,
            'private_key': self.private_key,
            'use_testnet': self.use_testnet
        }
    
    def validate_trade_params(self, trade_amount: float, confidence: float) -> Dict:
        """验证交易参数"""
        errors = []
        
        if trade_amount <= 0:
            errors.append("交易金额必须大于0")
        
        if trade_amount > self.max_position_size:
            errors.append(f"交易金额超过最大仓位限制: {self.max_position_size} USDC")
        
        if confidence < self.min_confidence:
            errors.append(f"置信度低于最小要求: {self.min_confidence}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def update_private_key(self, private_key: str, testnet: bool = None):
        """更新私钥"""
        if testnet is None:
            testnet = self.use_testnet
        
        if testnet:
            self.config_data.setdefault('polymarket', {}).setdefault('testnet', {})['private_key'] = private_key
        else:
            self.config_data.setdefault('polymarket', {})['private_key'] = private_key
        
        # 更新当前实例的私钥
        if testnet == self.use_testnet:
            self.private_key = private_key
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'private_key_configured': self.is_configured(),
            'use_testnet': self.use_testnet,
            'host': self.host,
            'chain_id': self.chain_id,
            'default_trade_amount': self.default_trade_amount,
            'max_slippage': self.max_slippage,
            'order_timeout': self.order_timeout,
            'max_position_size': self.max_position_size,
            'max_daily_trades': self.max_daily_trades,
            'min_confidence': self.min_confidence,
            'auto_trade_enabled': self.auto_trade_enabled,
            'dry_run_mode': self.dry_run_mode,
            'require_confirmation': self.require_confirmation
        }


# 全局配置实例
config = TradingConfig()


def load_config_from_file(config_file: str = "config/sys_config.json") -> Optional[Dict]:
    """从文件加载配置"""
    import json
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        return None


def save_config_to_file(config_data: Dict, config_file: str = "config/sys_config.json"):
    """保存配置到文件"""
    import json
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"配置已保存到: {config_file}")
    except Exception as e:
        print(f"保存配置失败: {e}")


def create_sample_config():
    """创建示例配置文件"""
    sample_config = {
        "polymarket": {
            "host": "https://clob.polymarket.com",
            "chain_id": 137,
            "private_key": "your_mainnet_private_key_here",
            "testnet": {
                "host": "https://clob-staging.polymarket.com",
                "chain_id": 80002,
                "private_key": "your_testnet_private_key_here"
            }
        },
        "trading": {
            "default_trade_amount": 10.0,
            "max_slippage": 0.02,
            "order_timeout": 300,
            "max_position_size": 100.0,
            "max_daily_trades": 10,
            "min_confidence": 0.85,
            "auto_trade_enabled": False,
            "dry_run_mode": True
        },
        "strategy": {
            "time_threshold_minutes": 30,
            "min_confidence": 0.85,
            "max_confidence": 0.95,
            "batch_size": 100,
            "max_retries": 3
        },
        "security": {
            "use_testnet": True,
            "require_confirmation": True,
            "max_gas_price": "50000000000"
        }
    }
    
    save_config_to_file(sample_config, "config/sys_config_sample.json")
    print("示例配置文件已创建: config/sys_config_sample.json")
    print("请复制并重命名为 config/sys_config.json，然后填入你的私钥")


if __name__ == "__main__":
    print("Polymarket交易配置")
    print("=" * 40)
    
    print(f"当前配置:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    
    print(f"\nAPI已配置: {config.is_configured()}")
    
    if not config.is_configured():
        print("\n创建示例配置文件...")
        create_sample_config()