# Polymarket & Probable Markets API 客户端

本项目包含两个完整的预测市场API客户端，用于获取和分析预测市场数据。

## 📁 文件结构

```
├── polymarket_clob_client.py      # Polymarket CLOB API 客户端
├── probable_markets_client.py     # Probable Markets API 客户端
├── data_saver.py                  # 数据保存器 (已更新支持两个平台)
├── test_clob.py                   # CLOB 客户端测试脚本
├── test.py                        # Probable Markets 测试脚本
├── clob_example.py                # CLOB 客户端使用示例
├── probable_markets_example.py    # Probable Markets 使用示例
├── probable_markets_demo.py       # Probable Markets 模拟数据演示
└── data/                          # 数据存储目录
```

## 🚀 Polymarket CLOB 客户端

基于官方文档 [https://docs.polymarket.com/developers/CLOB/quickstart](https://docs.polymarket.com/developers/CLOB/quickstart) 实现的完整CLOB API客户端。

### 主要功能

#### 公开市场数据API
- ✅ `get_markets()` - 获取市场列表 (支持分页)
- ✅ `get_market()` - 获取特定市场详情
- ✅ `get_orderbook()` - 获取订单簿数据
- ✅ `get_trades()` - 获取交易历史
- ✅ `get_prices()` - 获取价格信息
- ✅ `get_last_trade_price()` - 获取最后交易价格
- ✅ `get_midpoint()` - 获取中间价
- ✅ `get_spread()` - 获取买卖价差

#### 认证用户API (需要API密钥)
- ✅ `get_balance()` - 获取账户余额
- ✅ `get_orders()` - 获取用户订单
- ✅ `create_order()` - 创建订单
- ✅ `cancel_order()` - 取消订单
- ✅ `cancel_all_orders()` - 取消所有订单
- ✅ `get_order_status()` - 获取订单状态
- ✅ `get_user_trades()` - 获取用户交易历史

#### 便利方法
- ✅ `get_all_markets()` - 获取所有市场 (自动处理分页)
- ✅ `get_all_trades()` - 获取所有交易 (自动处理分页)
- ✅ `get_market_summary()` - 获取市场摘要信息

### 使用示例

```python
from polymarket_clob_client import PolymarketCLOBClient

# 创建客户端 (只读模式)
client = PolymarketCLOBClient(save_data=True)

# 获取市场列表
markets_data = client.get_markets(limit=10)
markets = markets_data.get('data', [])

# 获取市场详情
if markets:
    condition_id = markets[0].get('condition_id')
    market_detail = client.get_market(condition_id)
    
    # 获取代币信息
    tokens = market_detail.get('tokens', [])
    if tokens:
        token_id = tokens[0].get('token_id')
        
        # 获取订单簿
        orderbook = client.get_orderbook(token_id)
        
        # 获取最后交易价格
        last_price = client.get_last_trade_price(token_id)

# 认证功能 (需要API密钥)
auth_client = PolymarketCLOBClient(
    api_key="your_api_key",
    api_secret="your_api_secret", 
    passphrase="your_passphrase"
)

# 获取账户余额
balance = auth_client.get_balance()

# 创建买单
order = auth_client.create_order(
    token_id="token_id",
    price="0.50",
    size="10",
    side="BUY"
)
```

### 测试和示例

```bash
# 运行完整测试
python3 test_clob.py

# 运行使用示例
python3 clob_example.py
```

## 🌐 Probable Markets 客户端

基于 Probable Markets API 实现的客户端，支持获取预测市场数据。

### 主要功能

- ✅ `get_markets()` - 获取市场列表 (支持筛选和分页)
- ✅ `get_market_by_id()` - 获取特定市场详情
- ✅ `get_market_outcomes()` - 获取市场结果选项
- ✅ `get_market_prices()` - 获取市场价格信息
- ✅ `get_market_trades()` - 获取市场交易历史
- ✅ `get_categories()` - 获取市场类别
- ✅ `search_markets()` - 搜索市场

### 使用示例

```python
from probable_markets_client import ProbableMarketsClient

# 创建客户端
client = ProbableMarketsClient(save_data=True)

# 获取活跃市场
markets = client.get_markets(page=1, limit=10, active=True)

# 搜索市场
election_markets = client.search_markets("election", limit=5)

# 获取市场详情
if markets:
    market_id = markets[0].get('id')
    market_detail = client.get_market_by_id(market_id)
    
    # 获取结果选项
    outcomes = client.get_market_outcomes(market_id)
    
    # 获取价格信息
    prices = client.get_market_prices(market_id)
```

### 测试和示例

```bash
# 运行完整测试
python3 test.py

# 运行使用示例
python3 probable_markets_example.py

# 运行模拟数据演示
python3 probable_markets_demo.py
```

## 📊 数据保存功能

两个客户端都支持自动数据保存功能，所有API响应都会保存为CSV文件。

### 数据文件类型

#### Polymarket CLOB 数据
- `clob_markets_*.csv` - 市场列表数据
- `clob_market_detail_*.csv` - 市场详情数据
- `clob_market_tokens_*.csv` - 市场代币信息
- `clob_orderbook_*.csv` - 订单簿数据
- `clob_trades_*.csv` - 交易数据
- `clob_prices_*.csv` - 价格数据

#### Probable Markets 数据
- `probable_markets_*.csv` - 市场列表数据
- `probable_market_detail_*.csv` - 市场详情数据
- `probable_outcomes_*.csv` - 结果选项数据
- `probable_prices_*.csv` - 价格数据
- `probable_trades_*.csv` - 交易数据
- `probable_categories_*.csv` - 类别数据

### 数据管理

```python
from data_saver import DataSaver

# 创建数据保存器
saver = DataSaver(data_dir="./custom_data")

# 获取已保存的文件列表
files = saver.get_saved_files()

# 清理7天前的旧文件
saver.cleanup_old_files(days=7)
```

## 🔧 安装和配置

### 依赖安装

```bash
pip3 install requests pandas python-dotenv
```

### 环境变量配置 (可选)

如需使用Polymarket CLOB的认证功能，请设置以下环境变量：

```bash
export POLYMARKET_API_KEY=your_api_key
export POLYMARKET_API_SECRET=your_api_secret
export POLYMARKET_PASSPHRASE=your_passphrase
```

## 📈 实际测试结果

### Polymarket CLOB
- ✅ 成功获取1000个市场数据
- ✅ 获取市场详情和代币信息
- ✅ 获取最后交易价格
- ✅ 自动保存所有数据到CSV文件
- ⚠️ 部分端点需要认证或特定参数

### Probable Markets
- ✅ 成功获取市场列表
- ✅ 支持搜索和筛选功能
- ✅ 获取市场详情
- ✅ 自动保存所有数据到CSV文件
- ⚠️ 部分端点返回500错误 (可能是API限制)

## 🔍 错误处理

两个客户端都包含完善的错误处理机制：

- 网络请求超时处理
- HTTP状态码错误处理
- JSON解析错误处理
- 详细的日志记录
- 优雅的失败处理

## 📝 日志记录

所有客户端都使用Python标准logging模块记录操作日志：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 🚦 速率限制

为避免API速率限制，客户端包含以下机制：

- 请求间隔控制
- 自动重试机制
- 分页处理优化
- 错误后的延迟处理

## 💡 最佳实践

1. **数据保存**: 启用自动数据保存功能，便于后续分析
2. **错误处理**: 始终检查API响应是否为None
3. **速率限制**: 在循环请求中添加适当延迟
4. **认证安全**: 使用环境变量存储API密钥
5. **数据清理**: 定期清理旧的数据文件

## 🔮 未来扩展

- [ ] 添加WebSocket实时数据流支持
- [ ] 实现更多认证API功能
- [ ] 添加数据分析和可视化工具
- [ ] 支持更多预测市场平台
- [ ] 添加自动交易策略框架

## 📞 支持

如有问题或建议，请查看：
- [Polymarket CLOB 文档](https://docs.polymarket.com/developers/CLOB/quickstart)
- [Probable Markets API 文档](https://developer.probable.markets/)

---

**注意**: 使用这些客户端进行实际交易前，请确保充分理解相关风险，并在测试环境中验证所有功能。