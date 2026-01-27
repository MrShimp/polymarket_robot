# BTC 15分钟自动交易系统

这是一个完整的BTC 15分钟自动交易系统，能够在每个15分钟整点自动执行交易策略。

## 🚀 快速开始

### 方法1: 使用启动助手（推荐）
```bash
python start_auto_trader.py
```

### 方法2: 直接启动
```bash
# 使用默认金额 $5
python btc_auto_trader.py

# 指定交易金额
python btc_auto_trader.py 10
```

## 📋 系统组件

### 1. `btc_auto_trader.py` - 主控制器
- **功能**: 定时器和流程控制
- **职责**: 
  - 在每个15分钟整点触发交易
  - 获取BTC价格
  - 查找可用市场
  - 启动交易策略

### 2. `btc_market_query.py` - 市场查询器
- **功能**: 查找可用的BTC 15分钟市场
- **用法**: 
  ```bash
  python btc_market_query.py          # 人类可读输出
  python btc_market_query.py --json   # JSON格式输出
  ```

### 3. `btc_15min_strategy.py` - 交易策略
- **功能**: 执行具体的交易逻辑
- **参数**: `market_id` `amount` `baseline_price`

### 4. `start_auto_trader.py` - 启动助手
- **功能**: 简化启动流程，提供交互式配置

## ⏰ 工作流程

```
每15分钟整点 (00:15, 00:30, 00:45, 01:00...)
    ↓
1. 获取最新BTC价格 (Binance API)
    ↓
2. 查找可用市场 (Polymarket API)
    ↓
3. 启动交易策略
    ↓
4. 监控策略运行状态
    ↓
等待下一个15分钟整点...
```

## 📊 交易策略参数

- **交易时段**: 10:00 AM - 11:00 PM (北京时间)
- **入场条件**: 
  - 时间窗口: 区间开始5分钟后
  - 价格波动: ±$32 (相对基准价格)
  - 概率阈值: 75% (YES或NO)
- **出场条件**:
  - 止盈: 90%
  - 止损: 55%
  - 特殊止盈: 85% + 30秒横盘

## 📁 文件结构

```
.
├── btc_auto_trader.py          # 主控制器
├── btc_market_query.py         # 市场查询器
├── btc_15min_strategy.py       # 交易策略
├── start_auto_trader.py        # 启动助手
├── BTC_AUTO_TRADER_README.md   # 说明文档
└── data/                       # 数据目录
    ├── auto_trader_logs/       # 自动交易器日志
    ├── btc_strategy_logs/      # 策略日志
    ├── btc_intervals/          # 区间数据
    └── btc_trades/             # 交易记录
```

## 🔧 配置选项

### 交易金额
```bash
# 默认 $5
python btc_auto_trader.py

# 自定义金额
python btc_auto_trader.py 15
```

### 环境设置
- **测试网**: 修改策略文件中的 `use_testnet=True`
- **日志级别**: 修改日志输出详细程度

## 📈 监控和日志

### 日志文件位置
- **主控制器**: `data/auto_trader_logs/auto_trader_YYYYMMDD_HHMMSS.log`
- **交易策略**: `data/btc_strategy_logs/btc_15min_YYYYMMDD_HHMMSS.log`

### 交易记录
- **位置**: `data/btc_trades/btc_trade_YYYYMMDD_HHMMSS.json`
- **内容**: 完整的交易详情和盈亏记录

### 实时监控
```bash
# 查看主控制器日志
tail -f data/auto_trader_logs/auto_trader_*.log

# 查看策略日志
tail -f data/btc_strategy_logs/btc_15min_*.log
```

## ⚠️ 注意事项

### 风险提示
1. **市场风险**: 加密货币交易存在高风险
2. **技术风险**: 网络延迟、API故障等
3. **资金管理**: 建议使用小额资金测试

### 安全建议
1. **私钥安全**: 确保私钥文件安全存储
2. **网络安全**: 使用安全的网络环境
3. **定期备份**: 备份重要的配置和日志文件

### 系统要求
- **Python**: 3.7+
- **网络**: 稳定的互联网连接
- **依赖**: 所有必要的Python包已安装

## 🛑 停止系统

### 安全停止
```bash
# 在运行的终端中按 Ctrl+C
# 系统会安全停止所有进程
```

### 强制停止
```bash
# 查找进程
ps aux | grep btc_auto_trader

# 终止进程
kill -TERM <PID>
```

## 🔍 故障排除

### 常见问题

1. **无法找到市场**
   - 检查网络连接
   - 确认市场时间是否正确

2. **策略启动失败**
   - 检查私钥配置
   - 确认账户余额充足

3. **价格获取失败**
   - 检查Binance API连接
   - 尝试使用VPN

### 调试模式
```bash
# 单独测试市场查询
python btc_market_query.py

# 单独测试策略
python btc_15min_strategy.py <market_id> 5 95000
```

## 📞 支持

如有问题，请检查：
1. 日志文件中的错误信息
2. 网络连接状态
3. API密钥配置
4. 系统时间同步

---

**免责声明**: 本系统仅供学习和研究使用，使用者需自行承担交易风险。