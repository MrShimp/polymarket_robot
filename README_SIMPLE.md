# Polymarket自动交易系统 - 精简版

## 🎯 功能

- **数据拉取**: 自动扫描Polymarket市场数据
- **交易执行**: 基于策略自动执行交易
- **日志展示**: 详细的执行日志和统计信息

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements_simple.txt
```

### 2. 配置私钥
编辑 `config.json` 文件，填入你的私钥：
```json
{
  "polymarket": {
    "private_key": "0x你的私钥"
  }
}
```

### 3. 运行系统
```bash
# 单次扫描和交易
python3 main.py --mode single

# 连续交易模式（每10分钟扫描一次）
python3 main.py --mode continuous --interval 10
```

## ⚙️ 配置说明

### config.json
```json
{
  "polymarket": {
    "host": "https://clob.polymarket.com",  // API地址
    "chain_id": 137,                        // 链ID (137=主网)
    "private_key": ""                       // 你的私钥
  },
  "strategy": {
    "time_threshold_minutes": 30,           // 时间阈值（分钟）
    "min_confidence": 0.85,                 // 最小胜率
    "max_confidence": 0.95                  // 最大胜率
  },
  "trading": {
    "trade_amount": 10.0,                   // 交易金额（USDC）
    "max_slippage": 0.02,                   // 最大滑点
    "dry_run": true                         // 模拟模式
  }
}
```

## 📊 日志输出

系统会输出详细的执行日志：

```
2026-01-18 15:30:00 - INFO - 🤖 开始交易扫描 - 2026-01-18 15:30:00
2026-01-18 15:30:01 - INFO - 🔍 开始扫描交易机会...
2026-01-18 15:30:01 - INFO - 📊 参数: 时间阈值=30分钟, 胜率=85.0%-95.0%
2026-01-18 15:30:05 - INFO - ⚡ 发现机会: Bitcoin Up or Down - January 18... 胜率=0.920 (No)
2026-01-18 15:30:10 - INFO - 🎯 扫描完成: 检查了500个市场，发现1个机会
2026-01-18 15:30:10 - INFO - 🚀 模拟交易:
2026-01-18 15:30:10 - INFO -    市场: Bitcoin Up or Down - January 18...
2026-01-18 15:30:10 - INFO -    选项: No (置信度: 0.920)
2026-01-18 15:30:10 - INFO -    金额: $10.0 USDC
2026-01-18 15:30:10 - INFO - ✅ 模拟交易完成
```

## 🛡️ 安全提醒

1. **私钥安全**: 私钥控制你的资金，请妥善保管
2. **测试优先**: 建议先使用 `"dry_run": true` 进行模拟测试
3. **小额开始**: 实盘交易时建议从小额开始
4. **监控日志**: 定期检查 `trading.log` 文件

## 📈 核心逻辑

1. **数据拉取**: 从Polymarket API获取市场数据
2. **机会筛选**: 根据时间和胜率条件筛选交易机会
3. **交易执行**: 自动创建买单执行交易
4. **日志记录**: 记录所有操作和结果

## 🔧 自定义参数

- `time_threshold_minutes`: 只交易N分钟内结束的市场
- `min_confidence/max_confidence`: 胜率范围筛选
- `trade_amount`: 每笔交易的USDC金额
- `dry_run`: true=模拟交易，false=实盘交易

---

**免责声明**: 本系统仅供学习和研究使用，交易有风险，请谨慎操作。