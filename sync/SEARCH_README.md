# 市场搜索工具使用说明

## 概述

`market_search.py` 是一个通过关键词搜索 Polymarket 市场的工具，使用 Polymarket 的公共搜索API。**默认只返回活跃的、未结束的市场**。

## 功能特点

- 🔍 通过关键词搜索市场
- ✅ **默认过滤**: 只返回活跃的、未结束的市场
- 💾 自动保存搜索结果到CSV文件
- 📊 生成详细的搜索报告
- 🎯 显示市场统计信息
- 📈 按交易量排序显示热门市场

## 使用方法

### 基本用法

```bash
# 搜索包含"bitcoin"的活跃市场
python3 sync/market_search.py bitcoin

# 搜索包含"trump"的活跃市场，限制返回5个结果
python3 sync/market_search.py trump --limit 5

# 搜索包含所有市场（包括已关闭的）
python3 sync/market_search.py election --include-closed

# 搜索但不保存文件，仅显示结果
python3 sync/market_search.py climate --no-save
```

### 命令行选项

```bash
python3 sync/market_search.py <关键词> [选项]

参数:
  关键词                搜索关键词

选项:
  --data-dir DIR       数据目录 (默认: ./data)
  --limit N            返回结果数量限制 (默认: 100)
  --include-closed     包含已关闭的市场 (默认: 只返回活跃市场)
  --no-save            不保存到文件，仅显示结果
  --debug              启用调试日志
```

## 活跃市场过滤

**默认行为**: 脚本会自动过滤掉以下市场：
- ❌ 已关闭的市场 (`closed: true`)
- ❌ 非活跃的市场 (`active: false`)
- ❌ 已过期的市场 (结束时间早于当前时间)

**包含所有市场**: 使用 `--include-closed` 选项可以包含所有市场。

### 过滤示例

```bash
# 只返回活跃市场（默认）
python3 sync/market_search.py trump --limit 5
# 输出: 🔄 过滤后剩余 3 个活跃市场（原始: 5 个）

# 返回所有市场
python3 sync/market_search.py trump --limit 5 --include-closed
# 输出: 找到 5 个市场（包含已关闭的）
```

## 输出文件

### CSV数据文件

搜索结果会保存在 `data/markets/` 目录下，文件名格式：
```
{关键词}_markets_{时间戳}.csv
```

例如：
- `climate_markets_20260121_195440.csv`
- `trump_markets_20260121_215410.csv`

### JSON报告文件

详细报告会保存在 `data/reports/` 目录下，文件名格式：
```
search_report_{关键词}_{时间戳}.json
```

## CSV文件字段说明

| 字段名 | 说明 |
|--------|------|
| id | 市场ID |
| question | 市场问题/标题 |
| slug | URL slug |
| category | 分类 |
| tags | 标签列表（JSON格式） |
| clobTokenIds | CLOB代币ID |
| outcomes | 结果选项 |
| outcomePrices | 结果价格 |
| conditionId | 条件ID |
| active | 是否活跃 |
| closed | 是否已关闭 |
| volumeNum | 交易量（数值） |
| volume24hr | 24小时交易量 |
| liquidity | 流动性 |
| liquidityNum | 流动性（数值） |
| endDate | 结束时间 |
| description | 市场描述 |
| createdAt | 创建时间 |
| updatedAt | 更新时间 |

## 使用示例

### 示例1：搜索活跃的比特币市场

```bash
python3 sync/market_search.py bitcoin --limit 5
```

输出：
```
🔍 搜索关键词 'bitcoin' 的市场...
🔄 过滤后剩余 2 个活跃市场（原始: 5 个）

🔍 市场搜索报告 - 'bitcoin'
🎯 发现市场: 2 个
✅ 活跃市场: 2 个
❌ 已关闭: 0 个

🔥 交易量最大的市场:
1. 🟢 [9天22小时] What price will Bitcoin hit in January?
   ID: 137338 | 交易量: $0
```

### 示例2：搜索所有政治相关市场（包括已关闭）

```bash
python3 sync/market_search.py trump --limit 5 --include-closed
```

### 示例3：快速查看结果不保存文件

```bash
python3 sync/market_search.py climate --no-save
```

## API说明

工具使用的API端点：
```
https://gamma-api.polymarket.com/public-search?q={关键词}&limit={数量}
```

API返回的数据结构：
```json
{
  "events": [
    {
      "id": "131397",
      "title": "Natural Disaster in 2026?",
      "slug": "natural-disaster-in-2026",
      "description": "市场描述...",
      "endDate": "2026-12-31T00:00:00Z",
      "active": true,
      "closed": false,
      "volumeNum": "380.076616",
      "tags": [...],
      ...
    }
  ]
}
```

## 注意事项

1. **网络连接**: 确保网络连接稳定，工具会自动重试失败的请求
2. **API限制**: 遵守Polymarket的API使用限制
3. **数据格式**: 某些字段可能为空或格式不一致
4. **文件管理**: 定期清理旧的搜索结果文件

## 故障排除

### 常见问题

1. **"网络错误"**
   - 检查网络连接
   - 等待几分钟后重试

2. **"未找到市场"**
   - 尝试使用不同的关键词
   - 检查关键词拼写

3. **"JSON解析失败"**
   - 可能是API响应格式变化
   - 启用调试模式查看详细信息

### 调试模式

启用调试模式获取更详细的日志：

```bash
python3 sync/market_search.py climate --debug
```

## 与其他工具的配合使用

### 与标签搜索工具配合

```bash
# 1. 先通过关键词搜索找到相关市场
python3 sync/market_search.py climate

# 2. 查看搜索结果中的标签信息
# 3. 使用标签ID进行更精确的搜索
python3 sync/tag_markets_sync.py --tag-ids 87 84
```

### 数据分析

生成的CSV文件可以用于：
- Excel/Google Sheets分析
- Python pandas数据分析
- 数据可视化
- 市场趋势分析

## 更新日志

- **v1.0** - 初始版本，支持关键词搜索
- **v1.1** - 修复标题显示问题，优化数据结构处理
- **v1.2** - 添加详细报告和统计功能
- **v1.3** - **重要更新**: 默认只返回活跃的、未结束的市场，添加 `--include-closed` 选项