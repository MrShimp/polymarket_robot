# 🚨 紧急市场同步器使用指南

## 📖 概述

紧急市场同步器 (`urgent_markets_sync.py`) 是一个专门用于获取即将结束的Polymarket市场数据的工具。它可以帮助你快速识别和跟踪在指定时间内即将结束的市场。

## 🎯 主要功能

- ✅ **智能时间筛选** - 精确识别指定分钟内结束的市场
- ✅ **批量数据获取** - 高效扫描大量市场数据
- ✅ **断点续传** - 智能优化搜索，避免重复检查
- ✅ **详细报告** - 生成完整的紧急市场分析报告
- ✅ **CSV导出** - 保存数据到标准CSV格式
- ✅ **实时监控** - 显示搜索进度和发现的紧急市场

## 🚀 快速开始

### 基本用法

```bash
# 获取15分钟内结束的市场（默认）
python3 sync/urgent_markets_sync.py

# 获取5分钟内结束的市场
python3 sync/urgent_markets_sync.py --minutes 5

# 获取30分钟内结束的市场
python3 sync/urgent_markets_sync.py --minutes 30
```

### 高级选项

```bash
# 只显示结果，不保存文件
python3 sync/urgent_markets_sync.py --minutes 10 --no-save

# 自定义数据目录
python3 sync/urgent_markets_sync.py --data-dir ./custom_data

# 启用调试模式
python3 sync/urgent_markets_sync.py --minutes 15 --debug
```

## 📊 输出文件

### CSV数据文件
- **位置**: `./data/urgent/urgent_markets_{minutes}min_{timestamp}.csv`
- **格式**: 包含20个核心字段的标准市场数据
- **字段**: id, question, slug, category, clobTokenIds, outcomes, outcomePrices, conditionId, active, closed, volumeNum, volume24hr, liquidity, liquidityNum, endDate, orderPriceMinTickSize, orderMinSize, resolutionSource, acceptingOrders, openInterest

### JSON报告文件
- **位置**: `./data/reports/urgent_report_{minutes}min_{timestamp}.json`
- **内容**: 详细的统计分析和市场排名

## 📈 实际使用案例

### 案例1: 快速交易机会识别
```bash
# 获取5分钟内结束的市场，用于快速交易决策
python3 sync/urgent_markets_sync.py --minutes 5
```

**结果示例**:
- 发现39个紧急市场
- 总交易量: $767,904.55
- 包含加密货币价格预测、电竞比赛等高活跃度市场

### 案例2: 风险管理监控
```bash
# 获取15分钟内结束的市场，用于风险管理
python3 sync/urgent_markets_sync.py --minutes 15
```

**结果示例**:
- 发现47个紧急市场
- 总交易量: $593,438.34
- 帮助识别需要关注的即将结算市场

### 案例3: 市场研究分析
```bash
# 获取60分钟内结束的市场，进行市场趋势分析
python3 sync/urgent_markets_sync.py --minutes 60 --debug
```

## 🔧 参数说明

| 参数 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `--minutes` | 时间阈值（分钟） | 15 | `--minutes 30` |
| `--data-dir` | 数据存储目录 | ./data | `--data-dir ./custom` |
| `--no-save` | 不保存文件，仅显示结果 | False | `--no-save` |
| `--debug` | 启用调试日志 | False | `--debug` |

## 📋 输出报告解读

### 控制台输出
```
⚡ 紧急市场报告 - 15分钟内结束
🕐 报告时间: 2026-01-16 22:55:05
🎯 发现紧急市场: 47 个
💰 总交易量: $593,438.34
💧 总流动性: $365,748.16

🔥 最紧急的市场 (前10个):
   1. [0分钟] Solana Up or Down - January 16, 9:50AM-9:55AM ET
      ID: 1190379 | 交易量: $0
```

### 字段说明
- **[X分钟]**: 距离结束的剩余时间
- **ID**: 市场唯一标识符
- **交易量**: 该市场的总交易量
- **流动性**: 该市场的可用流动性

## ⚡ 性能优化

### 智能搜索策略
- 按结束时间排序搜索，优先找到最紧急的市场
- 当发现市场结束时间过远时自动停止搜索
- 批量处理减少API调用次数

### 网络优化
- 自动重试机制处理网络异常
- 智能延迟避免API限制
- 标准浏览器请求头提高成功率

## 🛠️ 故障排除

### 常见问题

**Q: 没有找到紧急市场怎么办？**
A: 这是正常情况，说明当前时间段内没有即将结束的市场。可以尝试增加时间阈值。

**Q: 网络错误如何处理？**
A: 脚本内置重试机制，会自动处理临时网络问题。如果持续出错，请检查网络连接。

**Q: 如何提高搜索速度？**
A: 可以减少时间阈值，或者在网络较好的环境下运行。

### 调试模式
```bash
python3 sync/urgent_markets_sync.py --minutes 15 --debug
```
启用调试模式可以看到详细的搜索过程和网络请求信息。

## 🔄 与其他工具集成

### 与enhanced_sync.py配合使用
```bash
# 先获取紧急市场
python3 sync/urgent_markets_sync.py --minutes 10

# 然后同步完整市场数据
python3 sync/enhanced_sync.py --mode markets --batch-size 100
```

### 数据分析
```bash
# 分析紧急市场数据
python3 data_analysis.py
```

## 📝 最佳实践

1. **定期监控**: 建议每5-10分钟运行一次，及时发现新的紧急市场
2. **合理设置阈值**: 根据交易策略选择合适的时间阈值
3. **数据备份**: 重要的紧急市场数据应及时备份
4. **结合其他数据**: 配合完整市场数据进行综合分析

## 🎯 使用技巧

- **快速扫描**: 使用较小的时间阈值（5-15分钟）进行快速机会识别
- **风险管理**: 使用较大的时间阈值（30-60分钟）进行风险预警
- **批量分析**: 定期运行并保存数据，用于历史趋势分析
- **实时监控**: 结合其他监控工具，构建完整的市场监控系统

---

## 🤝 支持

如果遇到问题或需要新功能，请查看项目文档或提交issue。

**Happy Trading! 🚀**