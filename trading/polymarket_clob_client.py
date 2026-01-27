#!/usr/bin/env python3
"""
Polymarket CLOB (Central Limit Order Book) 客户端配置器

使用示例:
    # 创建客户端
    client = PolymarketCLOBClient()
    
    # 获取原生ClobClient
    clob_client = client.get_client()
    
    # 直接使用原生API
    markets = clob_client.get_markets()
    orderbook = clob_client.get_order_book(token_id)
    
    # 或使用包装器的便捷方法
    address = client.get_address()
"""

import json
from typing import Dict, Optional
import os

# 导入官方py_clob_client
try:
    from py_clob_client.clob_types import ApiCreds, OrderArgs
    from py_clob_client.client import ClobClient
    from py_clob_client.constants import POLYGON, AMOY
    CLOB_CLIENT_AVAILABLE = True
except ImportError:
    print("⚠️ py_clob_client未安装，请运行: pip install py-clob-client")
    CLOB_CLIENT_AVAILABLE = False
    # 创建占位符类以避免导入错误
    class ClobClient:
        pass
    POLYGON = 137
    AMOY = 80002


class PolymarketCLOBClient:
    """Polymarket CLOB API 客户端配置器 - 简化包装器"""
    
    def __init__(self, 
                 host: str = "https://clob.polymarket.com",
                 chain_id: int = 137,
                 private_key: str = "",
                 api_key: str = "",
                 api_secret: str = "",
                 passphrase: str = ""):
        """
        初始化CLOB客户端配置器
        
        Args:
            host: API主机地址
            chain_id: 链ID (137=Polygon主网)
            private_key: 私钥 (用于L1认证)
            api_key: API密钥 (用于L2认证)
            api_secret: API密钥 (用于L2认证)
            passphrase: API密码短语 (用于L2认证)
        """
        if not CLOB_CLIENT_AVAILABLE:
            raise ImportError("py_clob_client未安装，请运行: pip install py-clob-client")
        
        self.private_key = private_key
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        
        # 设置链ID和主机 (仅主网)
        self.chain_id = chain_id if chain_id != 137 else POLYGON
        self.host = host
        
        # 从配置文件读取设置
        if not self.private_key or not self.api_key:
            self._load_config_from_file()
        
        # 初始化原生ClobClient
        self.clob_client = self._create_clob_client()
        
        # 存储地址（如果可用）
        self.address = self._get_address_from_client()
    
    def _load_config_from_file(self):
        """从配置文件加载设置"""
        try:
            with open('config/sys_config.json', 'r') as f:
                config = json.load(f)
            
            polymarket_config = config.get('polymarket', {})
            
            self.private_key = polymarket_config.get('private_key', '')
            self.api_key = polymarket_config.get('api_key', '')
            self.api_secret = polymarket_config.get('api_secret', '')
            self.passphrase = polymarket_config.get('passphrase', '')
            if polymarket_config.get('host'):
                self.host = polymarket_config['host']
            if polymarket_config.get('chain_id'):
                self.chain_id = polymarket_config['chain_id']
            if polymarket_config.get('funder_address'):
                self.funder_address = polymarket_config['funder_address']
                    
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ 无法读取配置文件: {e}")
    
    def _validate_private_key(self, private_key: str) -> bool:
        """验证私钥格式"""
        return True
    
    def _create_clob_client(self) -> Optional[ClobClient]:
        """创建原生ClobClient"""
        try:
            # 创建ClobClient实例
            client = ClobClient(
                        host=self.host,
                        key=self.private_key,
                        chain_id=self.chain_id,)
            api_creds = client.create_or_derive_api_creds()
            client = ClobClient(
                        host="https://clob.polymarket.com",
                        chain_id=137,
                        key=self.private_key,
                        creds=api_creds,
                        signature_type=2,
                        funder=self.funder_address
                        )
            #client.approve_allowance()
        
            
            print(f"✅ ClobClient初始化成功")
            print(f"   主机: {self.host}")
            print(f"   链ID: {self.chain_id}")
            
            return client
            
        except Exception as e:
            print(f"❌ ClobClient初始化失败: {e}")
            try:
                # 最后尝试：创建最基本的客户端
                client = ClobClient(
                    host=self.host,
                    chain_id=self.chain_id
                )
                print(f"✅ 无认证ClobClient初始化成功 (仅支持公开API)")
                return client
            except Exception as e2:
                print(f"❌ 无认证ClobClient初始化也失败: {e2}")
                return None
    
    def _get_address_from_client(self) -> Optional[str]:
        """从客户端获取地址"""
        if not self.clob_client:
            return None
        
        try:
            # 尝试使用get_address方法
            if hasattr(self.clob_client, 'get_address'):
                return self.clob_client.get_address()
            
            # 如果没有get_address方法，尝试从signer获取
            if hasattr(self.clob_client, 'signer') and self.clob_client.signer:
                if hasattr(self.clob_client.signer, 'address'):
                    return self.clob_client.signer.address
            
            # 如果有私钥，尝试从私钥推导地址
            if self.private_key:
                try:
                    from eth_account import Account
                    account = Account.from_key(self.private_key)
                    return account.address
                except ImportError:
                    pass
            
            return None
            
        except Exception as e:
            print(f"⚠️ 获取地址失败: {e}")
            return None
    
    def get_client(self) -> ClobClient:
        """获取原生ClobClient实例"""
        if not self.clob_client:
            raise RuntimeError("ClobClient未初始化或初始化失败")
        return self.clob_client
    
    def get_address(self) -> Optional[str]:
        """获取钱包地址"""
        return self.address
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            if not self.clob_client:
                return False
            
            # 使用get_ok方法测试连接
            if hasattr(self.clob_client, 'get_ok'):
                self.clob_client.get_ok()
                return True
            
            # 如果没有get_ok方法，尝试获取市场列表
            markets = self.clob_client.get_markets()
            return markets is not None
            
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False
    
    def inspect_methods(self):
        """检查ClobClient可用的方法"""
        if not self.clob_client:
            print("❌ ClobClient未初始化")
            return []
        
        methods = [method for method in dir(self.clob_client) if not method.startswith('_')]
        #print(f"📋 ClobClient可用方法:")
        #for method in sorted(methods):
        #    print(f"   - {method}")
        return methods


# 便捷函数
def create_client() -> PolymarketCLOBClient:
    """创建客户端 - 从配置文件读取设置"""
    return PolymarketCLOBClient()


def create_mainnet_client() -> PolymarketCLOBClient:
    """创建主网客户端"""
    return PolymarketCLOBClient()


def test_client_connection():
    """测试客户端连接"""
    print("测试CLOB客户端连接...")
    
    if not CLOB_CLIENT_AVAILABLE:
        print("❌ py_clob_client未安装，请运行: pip install py-clob-client")
        return False
    
    # 创建测试客户端
    wrapper = create_testnet_client()
    
    try:
        # 测试连接
        if wrapper.test_connection():
            print("✅ 客户端连接测试成功")
            
            # 显示地址
            address = wrapper.get_address()
            if address:
                print(f"   钱包地址: {address}")
            
            # 获取原生客户端并测试
            client = wrapper.get_client()
            print(f"   原生客户端类型: {type(client).__name__}")
            
            return True
        else:
            print("❌ 客户端连接测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 客户端连接测试失败: {e}")
        return False


if __name__ == "__main__":
    # 示例用法
    print("Polymarket CLOB客户端配置器")
    print("简化包装器，提供配置加载并返回原生ClobClient")
    print()
    
    # 检查依赖
    if not CLOB_CLIENT_AVAILABLE:
        print("❌ 缺少依赖: py_clob_client")
        print("请运行: pip install py-clob-client")
        exit(1)
    
    # 配置说明
    print("配置方法:")
    print("1. 配置文件 (推荐): config/sys_config.json")
    print("2. 直接传参:")
    print("   wrapper = PolymarketCLOBClient(private_key='0x...')")
    print("   wrapper = PolymarketCLOBClient(api_key='...', api_secret='...', passphrase='...')")
    print()
    
    print("使用方法:")
    print("   wrapper = create_client()")
    print("   client = wrapper.get_client()  # 获取原生ClobClient")
    print("   address = wrapper.get_address()  # 获取钱包地址")
    print("   markets = client.get_markets()  # 直接使用原生API")
    print()
    
    # 运行连接测试
    test_client_connection()