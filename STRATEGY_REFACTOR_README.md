# 策略重构说明

## 概述

本次重构将 `btc_15min_strategy.py` 中的 `enter_position` 和 `exit_position` 功能提取到独立的模块中，提高代码的可维护性和复用性。

## 重构内容

### 新增文件

1. **`trading/buy_strategy.py`** - 买入策略模块
   - `BuyStrategy` 类：处理所有买入相关操作
   - `enter_position()` 方法：执行入场操作
   - `create_buy_order()` 方法：创建买入订单的通用方法
   - `validate_buy_parameters()` 方法：验证买入参数

2. **`trading/sell_strategy.py`** - 卖出策略模块
   - `SellStrategy` 类：处理所有卖出相关操作
   - `exit_position()` 方法：执行出场操作（带重试机制）
   - `get_position_balance()` 方法：获取持仓余额
   - `create_sell_order()` 方法：创建卖出订单的通用方法
   - `exit_position_with_retry()` 方法：带自定义重试参数的出场操作
   - `validate_sell_parameters()` 方法：验证卖出参数

### 修改文件

1. **`btc_15min_strategy.py`**
   - 导入新的买卖策略模块
   - 在 `__init__` 方法中初始化买卖策略实例
   - 将原有的 `enter_position` 和 `exit_position` 调用替换为策略模块调用
   - 移除了原有的 `enter_position`、`exit_position` 和 `format_amount_for_api` 方法

## 使用方法

### 在现有策略中使用

```python
from trading.buy_strategy import BuyStrategy
from trading.sell_strategy import SellStrategy

class YourStrategy:
    def __init__(self, clob_client):
        self.buy_strategy = BuyStrategy(clob_client, self.log)
        self.sell_strategy = SellStrategy(clob_client, self.log)
    
    async def execute_trade(self):
        # 买入
        success, amount = await self.buy_strategy.enter_position(
            token_id, price, current_prob
        )
        
        # 卖出
        success = await self.sell_strategy.exit_position(
            token_id, amount
        )
```

### 独立使用买入策略

```python
from trading.buy_strategy import BuyStrategy

buy_strategy = BuyStrategy(clob_client, logger)

# 参数验证
valid, msg = buy_strategy.validate_buy_parameters(token_id, amount, prob)

# 执行买入
success, actual_amount = await buy_strategy.enter_position(
    token_id, amount, current_prob
)
```

### 独立使用卖出策略

```python
from trading.sell_strategy import SellStrategy

sell_strategy = SellStrategy(clob_client, logger)

# 查询持仓
balance = await sell_strategy.get_position_balance(token_id)

# 执行卖出
success = await sell_strategy.exit_position(token_id, amount)

# 带自定义重试的卖出
success = await sell_strategy.exit_position_with_retry(
    token_id, max_retries=3, retry_delay=2.0
)
```

## 主要优势

### 1. 模块化设计
- 买入和卖出逻辑分离，职责清晰
- 每个模块可以独立测试和维护
- 便于在不同策略中复用

### 2. 增强的功能
- 添加了参数验证方法
- 提供了更灵活的重试机制
- 支持自定义日志记录器

### 3. 向后兼容
- 原有的 `btc_15min_strategy.py` 功能保持不变
- 现有调用方式无需修改
- 平滑过渡到新架构

### 4. 扩展性
- 易于添加新的交易策略
- 支持不同的订单类型和参数
- 便于集成到其他交易系统

## 测试

### 运行重构测试
```bash
python3 test_strategy_refactor.py
```

### 运行演示程序
```bash
python3 demo_strategy_modules.py
```

## 文件结构

```
trading/
├── __init__.py
├── buy_strategy.py          # 新增：买入策略模块
├── sell_strategy.py         # 新增：卖出策略模块
├── polymarket_clob_client.py
├── order_manager.py
└── ...

btc_15min_strategy.py        # 修改：使用新的策略模块
test_strategy_refactor.py    # 新增：重构测试脚本
demo_strategy_modules.py     # 新增：使用演示脚本
```

## 注意事项

1. **日志记录器**：策略类接受可选的日志记录器函数，如果不提供则使用 `print`
2. **错误处理**：所有方法都包含完整的异常处理
3. **重试机制**：卖出操作包含智能重试机制，确保交易可靠性
4. **参数验证**：提供了完整的参数验证功能，提高代码健壮性

## 后续计划

1. 可以进一步提取市场数据获取功能
2. 添加更多的订单类型支持
3. 实现更复杂的风险管理策略
4. 添加性能监控和统计功能