# BTC 15分钟策略启动器

## 📋 概述

这是一套完整的BTC 15分钟策略启动工具，提供多种启动方式，适合不同使用场景。

## 🚀 启动脚本

### 1. 主启动器 - `start_btc_15min_strategy.py`

**功能**: 完整的策略启动器，支持交互式和命令行模式

#### 交互模式
```bash
python3 start_btc_15min_strategy.py
```
- 🎯 选择预设市场或输入自定义市场ID
- 💰 设置交易金额和参数
- 📊 自动获取当前BTC价格作为基准
- ✅ 完整的参数验证和确认

#### 命令行模式
```bash
# 基本用法
python3 start_btc_15min_strategy.py <market_id> [amount] [baseline_price] [--testnet]

# 示例
python3 start_btc_15min_strategy.py 0x1234567890abcdef 15.0 95000
python3 start_btc_15min_strategy.py 0x1234567890abcdef 10.0 95000 --testnet
```

### 2. 快速启动器 - `quick_start_btc.py`

**功能**: 一键启动，预设配置，快速上手

```bash
# 快速启动
python3 quick_start_btc.py <market_id> [config]

# 配置选项
python3 quick_start_btc.py 0x1234567890abcdef small   # 小额测试 ($5)
python3 quick_start_btc.py 0x1234567890abcdef normal  # 标准交易 ($10)
python3 quick_start_btc.py 0x1234567890abcdef large   # 大额交易 ($25)
```

### 3. 原始策略 - `btc_15min_strategy.py`

**功能**: 核心策略文件，直接启动

```bash
# 交互模式
python3 btc_15min_strategy.py

# 命令行模式
python3 btc_15min_strategy.py <market_id> <amount> <baseline_price>
```

## 📊 策略参数

### 核心参数
- **交易时段**: 10:00-19:00 北京时间
- **入场概率**: YES/NO ≥ 75%
- **价格阈值**: 基准价格 ± $32
- **止盈概率**: 90%
- **止损概率**: 55%
- **特殊止盈**: 85% + 横盘30秒

### 时间窗口
- **买入限制**: 区间开始5分钟后才能买入
- **卖出自由**: 任何时间都可以卖出
- **区间长度**: 15分钟

## 🎯 使用场景

### 场景1: 新手测试
```bash
# 使用小额配置测试
python3 quick_start_btc.py 0x1234567890abcdef small
```

### 场景2: 日常交易
```bash
# 使用交互模式，完整配置
python3 start_btc_15min_strategy.py
```

### 场景3: 自动化部署
```bash
# 使用命令行模式，脚本化部署
python3 start_btc_15min_strategy.py 0x1234567890abcdef 15.0 95000
```

### 场景4: 测试网络
```bash
# 在测试网络上验证策略
python3 start_btc_15min_strategy.py 0x1234567890abcdef 10.0 95000 --testnet
```

## 📁 配置文件

### `config/btc_markets.json`
预设的BTC市场配置，包含：
- 市场名称和描述
- 默认基准价格
- 市场分类（日度/周度/月度）
- 激活状态

### `config/btc_strategy_config.json`
策略详细配置参数

## 🔧 参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| market_id | Polymarket市场ID | 必需 | 0x1234...abcd |
| amount | 交易金额(USDC) | 10.0 | 15.0 |
| baseline_price | 基准价格 | 当前价格 | 95000 |
| --testnet | 使用测试网络 | false | --testnet |

## 📊 实时监控

策略运行时会显示：
- 📈 实时BTC价格
- 📊 与基准价格的差额
- ⏰ 当前交易区间
- 🎯 持仓状态
- 💰 盈亏情况

## ⚠️ 注意事项

1. **市场ID**: 确保使用有效的Polymarket BTC市场ID
2. **余额检查**: 确保账户有足够的USDC余额
3. **网络连接**: 需要稳定的网络连接获取价格数据
4. **时间同步**: 确保系统时间准确（北京时间）
5. **风险管理**: 建议先用小额测试策略

## 🛑 停止策略

- **键盘中断**: Ctrl+C 安全停止
- **信号处理**: 支持SIGTERM信号
- **自动清理**: 停止时自动清理资源

## 📝 日志记录

策略会自动记录：
- 📁 `data/btc_strategy_logs/`: 运行日志
- 📁 `data/btc_trades/`: 交易记录
- 📁 `data/btc_intervals/`: 区间数据

## 🔍 故障排除

### 常见问题

1. **导入错误**: 确保安装所有依赖 `pip3 install -r requirements.txt`
2. **网络错误**: 检查网络连接和API访问
3. **市场ID无效**: 验证市场ID格式和有效性
4. **余额不足**: 检查USDC余额是否充足
5. **时间窗口**: 确认当前是否在交易时段

### 调试模式
```bash
# 查看详细日志
tail -f data/btc_strategy_logs/btc_15min_*.log

# 测试依赖
python3 test_btc_strategy_deps.py

# 测试初始化
python3 test_btc_strategy_init.py
```

## 📞 支持

如有问题，请检查：
1. 日志文件中的错误信息
2. 网络连接状态
3. 账户余额和权限
4. 市场ID的有效性

---

**祝交易顺利！** 🚀📈