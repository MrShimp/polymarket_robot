# 标签市场同步工具

这个工具集帮助你同步和搜索 Polymarket 的标签和市场数据。

## 文件说明

- `tag_markets_sync.py` - 主要的标签市场同步工具
- `find_tag_id.py` - 标签ID查找工具
- `README.md` - 本文档

## 快速开始

### 1. 同步所有可用标签

首先，同步所有可用的标签到本地文件：

```bash
python3 sync/tag_markets_sync.py --sync-tags
```

这会在 `data/tags/` 目录下生成三个文件：
- `available_tags_YYYYMMDD_HHMMSS.csv` - CSV格式的标签数据
- `available_tags_YYYYMMDD_HHMMSS.json` - JSON格式的标签数据
- `tag_id_mapping_YYYYMMDD_HHMMSS.json` - 标签ID到名称的映射文件

### 2. 查找标签ID

使用标签查找工具来找到你感兴趣的标签ID：

```bash
# 搜索包含"israel"的标签
python3 sync/find_tag_id.py israel

# 搜索包含"nba"的标签
python3 sync/find_tag_id.py nba

# 列出所有标签（前20个）
python3 sync/find_tag_id.py --list-all

# 列出所有标签（前50个）
python3 sync/find_tag_id.py --list-all --limit 50
```

### 3. 使用标签ID搜索市场

找到标签ID后，使用它们来搜索相关市场：

```bash
# 搜索单个标签的市场
python3 sync/tag_markets_sync.py --tag-ids 180

# 搜索多个标签的市场
python3 sync/tag_markets_sync.py --tag-ids 180 241 803

# 结合标签和关键词搜索
python3 sync/tag_markets_sync.py --tag-ids 180 --keywords bitcoin

# 只显示结果，不保存文件
python3 sync/tag_markets_sync.py --tag-ids 180 --no-save
```

## 命令行选项

### tag_markets_sync.py

```bash
python3 sync/tag_markets_sync.py [选项]

选项:
  --data-dir DIR        数据目录 (默认: ./data)
  --tag-ids ID [ID...]  要搜索的标签ID列表
  --keywords WORD [WORD...] 要搜索的关键词列表
  --list-tags          列出所有可用的标签ID
  --sync-tags          同步所有可用标签到文件
  --no-save            不保存到文件，仅显示结果
  --debug              启用调试日志
```

### find_tag_id.py

```bash
python3 sync/find_tag_id.py [查询] [选项]

参数:
  查询                  搜索查询（标签名称、slug或ID）

选项:
  --data-dir DIR       数据目录 (默认: ./data)
  --list-all           列出所有标签
  --limit N            显示结果数量限制 (默认: 20)
```

## 输出文件

### 市场数据文件

搜索到的市场数据会保存在 `data/tags/` 目录下，文件名格式：
- `{标签名}_markets_{时间戳}.csv`

包含的字段：
- `id` - 市场ID
- `question` - 市场问题
- `slug` - URL slug
- `category` - 分类
- `tags` - 标签列表
- `clobTokenIds` - CLOB代币ID
- `outcomes` - 结果选项
- `outcomePrices` - 结果价格
- `volumeNum` - 交易量
- `liquidity` - 流动性
- `endDate` - 结束时间
- 等等...

### 报告文件

详细的JSON报告会保存在 `data/reports/` 目录下，包含：
- 市场统计信息
- 分类分布
- 时间分布
- 交易量最大的市场列表

## 使用示例

### 示例1：搜索以色列相关市场

```bash
# 1. 查找以色列相关的标签ID
python3 sync/find_tag_id.py israel
# 输出: ID: 180, 名称: Israel

# 2. 搜索该标签的市场
python3 sync/tag_markets_sync.py --tag-ids 180
```

### 示例2：搜索体育相关市场

```bash
# 1. 查找体育相关标签
python3 sync/find_tag_id.py nba
python3 sync/find_tag_id.py nfl

# 2. 搜索多个体育标签的市场
python3 sync/tag_markets_sync.py --tag-ids 100240 100241
```

### 示例3：定期更新标签列表

```bash
# 每天运行一次，更新标签列表
python3 sync/tag_markets_sync.py --sync-tags
```

## 注意事项

1. **API限制**: Polymarket API有请求频率限制，工具内置了重试机制和延迟处理
2. **数据量**: 某些热门标签可能有大量市场，搜索可能需要一些时间
3. **文件管理**: 定期清理旧的数据文件以节省磁盘空间
4. **网络连接**: 确保网络连接稳定，工具会自动重试失败的请求

## 故障排除

### 常见问题

1. **"未找到标签映射文件"**
   - 解决方案: 先运行 `python3 sync/tag_markets_sync.py --sync-tags`

2. **"API错误 429"**
   - 解决方案: 等待几分钟后重试，这是请求频率限制

3. **"网络错误"**
   - 解决方案: 检查网络连接，工具会自动重试

4. **搜索结果为空**
   - 解决方案: 尝试使用不同的关键词或检查标签ID是否正确

### 调试模式

启用调试模式获取更详细的日志：

```bash
python3 sync/tag_markets_sync.py --tag-ids 180 --debug
```

## 更新日志

- **v1.0** - 初始版本，支持标签搜索
- **v1.1** - 修复使用tagId参数的问题
- **v1.2** - 添加标签同步和查找功能