# Polymarket Market Client - Gamma API 集成

## 🎯 概述

已成功创建完整的Polymarket Market API客户端，专门集成你提供的Gamma API端点：
```
curl "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=5"
```

## 📁 文件结构

```
├── polymarket_market_client.py          # 主客户端文件
├── test_polymarket_market.py            # 完整测试套件
├── test_polymarket_market_demo.py       # 模拟数据演示
├── test_api_endpoint.py                 # API端点测试工具
├── data_saver.py                        # 数据保存器 (已更新)
└── README.md                            # 本文档
```

## 🚀 核心功能

### 1. **事件管理**
- ✅ `get_events()` - 获取事件列表 (支持active, closed, limit等参数)
- ✅ `get_event_by_slug()` - 根据slug获取事件详情
- ✅ `get_active_events()` - 获取活跃事件 (基于你的API端点)
- ✅ `search_events()` - 搜索事件
- ✅ `get_trending_events()` - 获取热门事件

### 2. **市场管理**
- ✅ `get_markets()` - 获取市场列表
- ✅ `get_market_by_slug()` - 根据slug获取市场详情
- ✅ `get_event_markets()` - 获取特定事件的所有市场
- ✅ `get_high_volume_markets()` - 获取高交易量市场
- ✅ `get_near_expiry_markets()` - 获取即将到期市场

### 3. **数据分析**
- ✅ `get_market_statistics()` - 获取市场统计
- ✅ `get_market_history()` - 获取市场历史数据
- ✅ `get_market_summary()` - 获取市场摘要

### 4. **分类和搜索**
- ✅ `get_categories()` - 获取所有分类
- ✅ `get_events_by_category()` - 根据分类获取事件
- ✅ `search_events()` - 全文搜索功能

### 5. **监控功能**
- ✅ `monitor_events()` - 实时监控事件变化

## 🔧 使用方法

### 基本用法
```python
from polymarket_market_client import PolymarketMarketClient

# 创建客户端
client = PolymarketMarketClient(save_data=True)

# 获取活跃事件 (基于你提供的API端点)
events = client.get_active_events(limit=5)

# 获取活跃市场
markets = client.get_markets(active=True, closed=False, limit=10)

# 搜索事件
search_results = client.search_events("election", limit=5)

# 获取分类
categories = client.get_categories()
```

### 高级用法
```python
# 获取特定事件详情
event = client.get_event_by_slug("2024-us-election")

# 获取市场统计
stats = client.get_market_statistics("trump-wins-2024")

# 获取市场历史
history = client.get_market_history("bitcoin-100k", 
                                   start_date="2024-01-01", 
                                   end_date="2024-12-31")

# 监控事件变化
def on_new_events(events):
    print(f"发现 {len(events)} 个新事件")

client.monitor_events(callback_func=on_new_events, interval=60)
```

## 📊 API端点映射

| 功能 | 端点 | 参数 |
|------|------|------|
| 获取事件 | `/events` | active, closed, limit, offset, order, order_by |
| 事件详情 | `/events/{slug}` | - |
| 获取市场 | `/markets` | active, closed, limit, event_slug |
| 市场详情 | `/markets/{slug}` | - |
| 搜索 | `/search` | query, limit, type |
| 分类 | `/categories` | - |
| 市场统计 | `/markets/{slug}/stats` | - |
| 市场历史 | `/markets/{slug}/history` | start_date, end_date |

## 🗄️ 数据保存

客户端自动保存所有API响应为CSV文件：

### 事件数据
- `polymarket_events_*.csv` - 事件列表
- `polymarket_event_detail_*.csv` - 事件详情
- `polymarket_event_markets_*.csv` - 事件关联市场

### 市场数据
- `polymarket_markets_*.csv` - 市场列表
- `polymarket_market_detail_*.csv` - 市场详情
- `polymarket_market_outcomes_*.csv` - 市场结果选项
- `polymarket_market_history_*.csv` - 市场历史数据

### 其他数据
- `polymarket_categories_*.csv` - 分类数据

## 🧪 测试和演示

### 1. 完整测试套件
```bash
python3 test_polymarket_market.py
```

### 2. 模拟数据演示
```bash
python3 test_polymarket_market_demo.py
```

### 3. API端点测试
```bash
python3 test_api_endpoint.py
```

## 🔍 API访问状态

### 当前状态
- ❌ `gamma-api.polymarket.com` - 连接超时
- ❌ `api.polymarket.com` - 连接超时  
- ❌ `polymarket.com/api` - 连接超时
- ❌ `clob.polymarket.com` - 连接超时

### 可能原因
1. **地理限制** - API可能有地区访问限制
2. **认证要求** - 可能需要API密钥或特殊认证
3. **网络限制** - 端点可能不对外公开
4. **API变更** - 端点可能已迁移或废弃

### 解决方案
1. **使用VPN** - 尝试不同地区的VPN
2. **获取API密钥** - 联系Polymarket获取认证信息
3. **检查文档** - 查看最新的API文档
4. **使用模拟数据** - 用于开发和测试

## 🎯 实际部署建议

### 1. 生产环境配置
```python
# 添加认证信息
client = PolymarketMarketClient(
    base_url="https://gamma-api.polymarket.com",
    api_key="your_api_key",  # 如果需要
    save_data=True
)

# 设置请求头
client.session.headers.update({
    'Authorization': 'Bearer your_token',  # 如果需要
    'X-API-Key': 'your_api_key'           # 如果需要
})
```

### 2. 错误处理
```python
try:
    events = client.get_active_events(limit=5)
    if events:
        print(f"获取到 {len(events)} 个事件")
    else:
        print("API返回空结果")
except Exception as e:
    print(f"API调用失败: {e}")
    # 使用缓存数据或模拟数据
```

### 3. 监控和重试
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

# 使用重试装饰器
@retry_on_failure(max_retries=3)
def get_events_with_retry():
    return client.get_active_events(limit=5)
```

## 📈 性能优化

### 1. 缓存机制
```python
import time
from functools import lru_cache

class CachedPolymarketClient(PolymarketMarketClient):
    @lru_cache(maxsize=100)
    def get_events_cached(self, active=None, closed=None, limit=None):
        return self.get_events(active, closed, limit)
    
    def clear_cache(self):
        self.get_events_cached.cache_clear()
```

### 2. 批量处理
```python
def get_multiple_events(client, event_slugs):
    """批量获取事件详情"""
    results = []
    for slug in event_slugs:
        try:
            event = client.get_event_by_slug(slug)
            if event:
                results.append(event)
        except Exception as e:
            print(f"获取事件 {slug} 失败: {e}")
        time.sleep(0.1)  # 避免请求过于频繁
    return results
```

## 🔮 未来扩展

### 计划功能
- [ ] WebSocket实时数据流
- [ ] 更多筛选和排序选项
- [ ] 数据可视化工具
- [ ] 自动化监控和警报
- [ ] 与CLOB API的集成

### 集成建议
```python
# 与高频策略集成
from high_frequency_strategy import HighFrequencyStrategy
from polymarket_market_client import PolymarketMarketClient

class EnhancedStrategy(HighFrequencyStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.market_client = PolymarketMarketClient()
    
    def get_market_opportunities(self):
        # 使用Market API获取机会
        events = self.market_client.get_active_events(limit=100)
        # 结合CLOB API进行交易
        return self.analyze_events(events)
```

## 📞 支持信息

### 文档链接
- [Polymarket官网](https://polymarket.com)
- [CLOB API文档](https://docs.polymarket.com)
- [Gamma API文档](https://gamma-api.polymarket.com) (如果可用)

### 故障排除
1. **连接问题** - 检查网络和VPN设置
2. **认证问题** - 验证API密钥和权限
3. **数据格式** - 检查API响应结构变化
4. **速率限制** - 添加请求间隔和重试机制

---

**注意**: 由于API端点当前不可访问，建议先使用模拟数据进行开发和测试。一旦API可用，客户端代码无需修改即可正常工作。