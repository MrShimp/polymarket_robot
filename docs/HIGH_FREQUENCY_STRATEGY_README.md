# 高频微型仓位策略 - 90¢-99¢近乎确定性合约

## 🎯 策略概述

这是一个专门针对90¢-99¢价格区间的近乎确定性合约的高频交易策略，旨在通过大量微型仓位捕获小幅但稳定的利润。

### 核心特点
- **目标价格区间**: 90¢-99¢ (高概率事件)
- **交易频率**: 每天27,000+次微型交易
- **仓位大小**: $1-10 微型仓位
- **目标利润**: 每笔交易2%利润
- **风险控制**: 严格的止损和风险管理

## 📁 文件结构

```
├── high_frequency_strategy.py    # 主策略文件
├── polymarket_clob_client.py     # Polymarket CLOB API客户端
├── risk_manager.py               # 风险管理模块
├── strategy_monitor.py           # 策略监控面板
├── backtest_engine.py           # 回测引擎
├── deploy_strategy.py           # 部署脚本
├── data_saver.py                # 数据保存器
├── hf_config.json              # 策略配置文件
└── README.md                   # 本文档
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆或下载所有文件到工作目录
# 确保Python 3.8+已安装

# 设置环境变量 (生产环境必需)
export POLYMARKET_API_KEY="your_api_key"
export POLYMARKET_API_SECRET="your_api_secret"
export POLYMARKET_PASSPHRASE="your_passphrase"
```

### 2. 自动部署

```bash
# 运行部署脚本 (推荐)
python3 deploy_strategy.py

# 或手动安装依赖
pip3 install requests pandas numpy python-dotenv matplotlib seaborn
```

### 3. 运行回测

```bash
# 运行历史数据回测
python3 backtest_engine.py
```

### 4. 启动策略

```bash
# 使用启动脚本
./start_strategy.sh

# 或直接运行
python3 high_frequency_strategy.py
```

### 5. 监控策略

```bash
# 实时监控
./monitor_strategy.sh

# 或查看报告
python3 strategy_monitor.py --mode report
```

## ⚙️ 策略配置

### 核心参数 (hf_config.json)

```json
{
  "min_price": 0.90,              // 最低价格 90¢
  "max_price": 0.99,              // 最高价格 99¢
  "min_confidence": 0.95,         // 最低置信度 95%
  "position_size": 1,             // 微型仓位大小 $1
  "max_positions": 100,           // 最大同时持仓数
  "target_profit_pct": 0.02,      // 目标利润 2%
  "stop_loss_pct": 0.05,          // 止损 5%
  "scan_interval": 3,             // 扫描间隔 3秒
  "max_daily_trades": 27000,      // 每日最大交易次数
  "trades_per_minute": 30         // 每分钟最大交易次数
}
```

### 风险控制参数

```json
{
  "max_daily_loss": 500,          // 每日最大亏损 $500
  "max_consecutive_losses": 10,   // 最大连续亏损次数
  "max_position_loss": 10,        // 单仓位最大亏损 $10
  "min_volume": 1000,             // 最小交易量要求
  "max_spread": 0.05              // 最大价差 5%
}
```

## 🎯 策略逻辑

### 1. 市场扫描
- 每3秒扫描所有活跃市场
- 筛选90¢-99¢价格区间的合约
- 评估流动性和价差

### 2. 机会评估
- 计算置信度 (基于价格、价差、流动性)
- 分析结果确定性
- 排除测试/模拟市场

### 3. 交易执行
- 创建微型买单 ($1-10)
- 设置2%目标利润
- 设置5%止损

### 4. 仓位管理
- 实时监控价格变化
- 自动止盈/止损
- 时间限制 (24小时)

### 5. 风险控制
- 每日亏损限制
- 连续亏损限制
- 仓位集中度控制
- 实时风险评估

## 📊 性能指标

### 预期表现
- **日交易量**: 27,000+ 笔
- **胜率**: 85-95%
- **平均利润**: 每笔 $0.02-0.20
- **日收益**: $500-2,000
- **最大回撤**: <5%

### 风险指标
- **VaR (95%)**: <$50
- **夏普比率**: >2.0
- **最大单日亏损**: $500
- **最大连续亏损**: 10笔

## 🔍 监控面板

### 实时监控
```bash
python3 strategy_monitor.py --mode monitor
```

显示内容:
- 实时交易统计
- 当前仓位状态
- 风险指标
- 盈亏情况

### 每日报告
```bash
python3 strategy_monitor.py --mode report --date 2024-01-15
```

包含内容:
- 交易汇总
- 收益分析
- 风险评估
- 价格分布

## 🛡️ 风险管理

### 多层风险控制

1. **交易前风险评估**
   - 市场风险评分
   - 流动性检查
   - 价差分析

2. **仓位级风险控制**
   - 单仓位止损
   - 时间止损
   - 集中度限制

3. **账户级风险管理**
   - 每日亏损限制
   - 连续亏损保护
   - 总仓位限制

4. **系统级风险监控**
   - 实时风险指标
   - 自动交易暂停
   - 风险警报

### 风险等级

- **LOW**: 正常交易
- **MEDIUM**: 提高警惕
- **HIGH**: 减少仓位
- **CRITICAL**: 暂停交易

## 🔧 技术架构

### 异步架构
- 使用asyncio实现高并发
- 非阻塞API调用
- 并行市场扫描

### 数据管理
- 实时数据保存
- CSV格式存储
- 自动数据清理

### 错误处理
- 网络异常重试
- API限制处理
- 优雅降级

## 📈 回测系统

### 回测功能
```bash
python3 backtest_engine.py
```

特性:
- 历史数据回测
- 合成数据生成
- 多指标分析
- 可视化图表

### 回测指标
- 总收益率
- 夏普比率
- 最大回撤
- 胜率分析
- 交易分布

## 🚦 部署选项

### 开发环境
```bash
# 直接运行
python3 high_frequency_strategy.py
```

### 生产环境 (Linux)
```bash
# 创建systemd服务
sudo cp hf-strategy.service /etc/systemd/system/
sudo systemctl enable hf-strategy
sudo systemctl start hf-strategy
```

### Docker部署
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "high_frequency_strategy.py"]
```

## 📋 日常操作

### 启动策略
```bash
./start_strategy.sh
```

### 监控状态
```bash
./monitor_strategy.sh
```

### 查看日志
```bash
tail -f ./logs/strategy.log
```

### 生成报告
```bash
python3 strategy_monitor.py --mode export --date 2024-01-15
```

### 紧急停止
```bash
# 发送SIGINT信号
pkill -f high_frequency_strategy.py
```

## ⚠️ 重要提醒

### 风险警告
1. **高频交易风险**: 技术故障可能导致大量损失
2. **市场风险**: 即使是高概率事件也可能失败
3. **流动性风险**: 市场流动性不足可能影响退出
4. **技术风险**: 网络延迟、API限制等技术问题

### 最佳实践
1. **小额开始**: 先用小资金测试
2. **持续监控**: 定期检查策略表现
3. **参数调优**: 根据市场变化调整参数
4. **风险控制**: 严格遵守风险管理规则

### 合规要求
1. **API限制**: 遵守Polymarket API使用条款
2. **监管合规**: 确保符合当地金融监管要求
3. **税务申报**: 正确申报交易收益

## 🔧 故障排除

### 常见问题

**Q: 策略无法启动**
A: 检查环境变量和API密钥设置

**Q: 交易频率过低**
A: 调整扫描间隔和筛选条件

**Q: 风险警报频繁**
A: 检查市场环境，考虑调整风险参数

**Q: 数据保存失败**
A: 检查磁盘空间和文件权限

### 日志分析
```bash
# 查看错误日志
grep "ERROR" ./logs/strategy.log

# 查看交易统计
grep "执行交易" ./logs/strategy.log | wc -l

# 查看风险警报
grep "风险警报" ./logs/strategy.log
```

## 📞 支持与维护

### 更新策略
1. 备份当前配置
2. 停止运行中的策略
3. 更新代码文件
4. 重新启动策略

### 性能优化
1. 监控系统资源使用
2. 优化数据库查询
3. 调整并发参数
4. 升级硬件配置

### 联系支持
- 查看日志文件获取详细错误信息
- 检查API文档了解最新变更
- 参考Polymarket官方文档

---

**免责声明**: 本策略仅供教育和研究目的。实际交易存在风险，可能导致资金损失。使用前请充分了解相关风险并谨慎决策。