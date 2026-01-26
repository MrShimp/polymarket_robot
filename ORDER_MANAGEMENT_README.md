# Polymarket 订单管理功能

这个模块为Polymarket交易提供了高级订单管理功能，包括取消订单、Split订单和梯形订单等。

## 功能特性

### 1. 订单查看和取消
- 查看所有未成交订单
- 查看特定Token的订单
- 取消单个订单
- 取消特定Token的所有订单
- 取消所有订单

### 2. Split订单 (订单分割)
- 将大订单分割成多个小订单
- 在指定价格范围内均匀分布
- 支持自定义分割数量
- 减少市场冲击，提高成交率

### 3. 梯形订单 (Ladder Orders)
- 在基准价格周围创建梯形分布的订单
- 支持买入和卖出方向
- 自定义价格增量和订单数量
- 适合做市和流动性提供

### 4. 订单簿深度查看
- 实时查看订单簿买卖盘深度
- 支持自定义深度层数
- 显示价差和中间价

## 文件结构

```
├── trading/
│   ├── order_manager.py          # 核心订单管理类
│   └── polymarket_clob_client.py # CLOB客户端包装器
├── order_management_tool.py      # 交互式订单管理工具
├── place_single_order.py         # 增强的下单工具 (包含订单管理选项)
├── test_order_management.py      # 功能测试脚本
└── ORDER_MANAGEMENT_README.md    # 本文档
```

## 使用方法

### 1. 启动订单管理工具

```bash
python order_management_tool.py
```

这将启动交互式菜单，提供以下选项：
- 查看未成交订单
- 取消订单
- Split订单 (分割大订单)
- 梯形订单 (Ladder Orders)
- 查看订单簿深度
- 批量取消订单

### 2. 通过增强的下单工具

```bash
python place_single_order.py
```

选择选项2进入订单管理功能。

### 3. 编程方式使用

```python
from trading.order_manager import OrderManager

# 创建订单管理器
manager = OrderManager(use_testnet=False)

# 查看未成交订单
orders = manager.get_open_orders()
manager.display_open_orders(orders)

# 取消订单
result = manager.cancel_order("order_id_here")

# Split订单
results = manager.split_order(
    token_id="token_id_here",
    total_amount=100.0,
    total_size=200.0,
    num_splits=5,
    price_range=(0.45, 0.55),
    side="BUY"
)

# 梯形订单
results = manager.ladder_orders(
    token_id="token_id_here",
    base_price=0.50,
    total_size=100.0,
    num_orders=5,
    price_increment=0.01,
    side="BUY"
)
```

## 配置要求

确保在 `config/sys_config.json` 中配置了正确的认证信息：

```json
{
  "polymarket": {
    "private_key": "0x...",
    "api_key": "...",
    "api_secret": "...",
    "passphrase": "...",
    "funder_address": "0x..."
  }
}
```

## 功能测试

运行测试脚本验证功能：

```bash
python test_order_management.py
```

## Split订单详解

Split订单将大订单分割成多个小订单，在指定价格范围内均匀分布：

### 参数说明
- `token_id`: 目标Token ID
- `total_amount`: 总金额 (USDC)
- `total_size`: 总数量 (shares)
- `num_splits`: 分割数量
- `price_range`: 价格范围 (最低价, 最高价)
- `side`: 订单方向 ("BUY" 或 "SELL")

### 示例
假设要买入100 USDC的某个结果，分成5个订单，价格范围0.45-0.55：

```
订单1: 价格 $0.450, 数量 20.0
订单2: 价格 $0.475, 数量 20.0  
订单3: 价格 $0.500, 数量 20.0
订单4: 价格 $0.525, 数量 20.0
订单5: 价格 $0.550, 数量 20.0
```

### 优势
- 减少市场冲击
- 提高成交概率
- 分散风险
- 更好的平均成交价格

## 梯形订单详解

梯形订单在基准价格周围创建梯形分布的订单：

### 参数说明
- `token_id`: 目标Token ID
- `base_price`: 基准价格
- `total_size`: 总数量
- `num_orders`: 订单数量
- `price_increment`: 价格增量
- `side`: 订单方向

### 示例
基准价格0.50，5个买单，价格增量0.01：

```
订单1: 价格 $0.500, 数量 20.0
订单2: 价格 $0.490, 数量 20.0
订单3: 价格 $0.480, 数量 20.0
订单4: 价格 $0.470, 数量 20.0
订单5: 价格 $0.460, 数量 20.0
```

### 适用场景
- 做市策略
- 流动性提供
- 区间交易
- 价格发现

## 安全注意事项

1. **测试环境**: 建议先在测试网环境测试
2. **资金管理**: 合理设置订单金额，避免过度风险
3. **价格验证**: 确保价格范围合理，避免异常订单
4. **网络延迟**: 批量订单可能受网络影响，建议分批执行
5. **API限制**: 注意API调用频率限制

## 故障排除

### 常见问题

1. **认证失败**
   - 检查 `config/sys_config.json` 中的认证信息
   - 确保私钥和API密钥正确

2. **订单创建失败**
   - 检查余额是否充足
   - 验证价格范围是否合理 (0-1之间)
   - 确认Token ID是否正确

3. **取消订单失败**
   - 订单可能已经成交
   - 检查订单ID是否正确
   - 网络连接问题

4. **订单簿获取失败**
   - Token ID可能无效
   - 市场可能暂时不可用
   - API连接问题

### 调试方法

1. 运行测试脚本：`python test_order_management.py`
2. 检查日志输出中的错误信息
3. 验证网络连接和API状态
4. 确认配置文件格式正确

## 更新日志

### v1.0.0
- 初始版本
- 支持基本订单管理功能
- Split订单功能
- 梯形订单功能
- 订单簿深度查看

## 贡献

欢迎提交问题和改进建议！

## 许可证

本项目遵循MIT许可证。