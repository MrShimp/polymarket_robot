# 🏗️ Polymarket Robot 项目结构

## 📁 目录结构

```
polymarket_robot/
├── 📦 core/                          # 核心API客户端
│   ├── __init__.py                   # 模块初始化
│   ├── polymarket_client.py          # 基础API客户端
│   ├── polymarket_market_client.py   # 市场数据客户端 (Gamma API)
│   └── polymarket_clob_client.py     # CLOB交易客户端
│
├── 🔄 sync/                          # 数据同步模块
│   ├── __init__.py                   # 模块初始化
│   ├── enhanced_sync.py              # 增强版同步器 (主要)
│   ├── polymarket_sync.py            # 原始同步器
│   ├── sync_scheduler.py             # 同步调度器
│   └── sync_monitor.py               # 同步监控器
│
├── 🤖 agents/                        # 智能代理
│   ├── __init__.py                   # 模块初始化
│   ├── base_agent.py                 # 基础代理类
│   ├── main_agent.py                 # 主代理
│   ├── decision_engine.py            # 决策引擎
│   ├── price_agent.py                # 价格代理
│   ├── risk_agent.py                 # 风险代理
│   └── sentiment_agent.py            # 情感分析代理
│
├── 📊 dashboard/                     # 仪表板和监控
│   ├── __init__.py                   # 模块初始化
│   └── live_dashboard.py             # 实时监控仪表板
│
├── 📤 export/                        # 数据导出和分析
│   ├── __init__.py                   # 模块初始化
│   ├── data_analyzer.py              # 数据分析器
│   ├── data_exporter.py              # 数据导出器
│   └── data_saver.py                 # 数据保存器
│
├── 💹 trading/                       # 交易策略
│   └── __init__.py                   # 模块初始化
│
├── 🛠️ utils/                         # 工具和管理
│   └── polymarket_manager.py         # 系统统一管理器
│
├── 🧪 tests/                         # 测试文件
│   ├── test.py                       # 基础测试
│   ├── sync_performance_test.py      # 同步性能测试
│   └── test_api_endpoint.py          # API端点测试
│
├── ⚙️ config/                        # 配置文件
│   ├── sync_config.json              # 同步配置
│   └── hf_config.json                # 高频策略配置
│
├── 📚 docs/                          # 文档
│   ├── README.md                     # 主要文档
│   ├── COMPLETE_SYSTEM_README.md     # 完整系统文档
│   ├── POLYMARKET_SYNC_SYSTEM_README.md # 同步系统文档
│   ├── POLYMARKET_MARKET_CLIENT_README.md # 市场客户端文档
│   ├── API_CLIENTS_README.md         # API客户端文档
│   └── HIGH_FREQUENCY_STRATEGY_README.md # 高频策略文档
│
├── 📁 data/                          # 数据存储
│   ├── tag/                          # 按标签分类的数据
│   ├── markets/                      # 市场数据CSV
│   ├── events/                       # 事件数据CSV
│   ├── reports/                      # 同步报告
│   ├── offline/                      # 离线测试数据
│   └── analysis/                     # 分析结果
│
├── main.py                           # 主入口文件
├── run.py                            # 运行脚本
├── requirements.txt                  # 依赖包列表
├── .env.example                      # 环境变量示例
├── PROJECT_STRUCTURE.md              # 项目结构文档 (本文件)
└── USAGE_GUIDE.md                    # 使用指南
```

## 🔧 模块功能说明

### 📦 Core (核心模块)
- **polymarket_client.py**: 基础的Polymarket API客户端，支持CLOB API
- **polymarket_market_client.py**: 专门处理市场数据的客户端 (Gamma API)
- **polymarket_clob_client.py**: CLOB (Central Limit Order Book) 交易客户端

### 🔄 Sync (同步模块)
- **enhanced_sync.py**: 🌟 主要同步器，支持批量数据获取和CSV保存
- **polymarket_sync.py**: 原始同步器，支持离线和API模式
- **sync_scheduler.py**: 定时同步调度器，支持多种调度策略
- **sync_monitor.py**: 同步状态监控器

### 🤖 Agents (智能代理模块)
- **base_agent.py**: 基础代理类，提供通用功能
- **main_agent.py**: 主智能代理，协调其他代理
- **decision_engine.py**: 决策引擎，处理复杂决策逻辑
- **price_agent.py**: 价格分析代理
- **risk_agent.py**: 风险管理代理
- **sentiment_agent.py**: 情感分析代理

### 📊 Dashboard (仪表板模块)
- **live_dashboard.py**: 实时监控仪表板，支持Web界面

### 📤 Export (导出模块)
- **data_exporter.py**: 多格式数据导出 (Excel/JSON/CSV)
- **data_analyzer.py**: 深度数据分析工具
- **data_saver.py**: 数据保存工具，统一数据存储格式

### 🛠️ Utils (工具模块)
- **polymarket_manager.py**: 系统统一管理器，提供命令行界面

### 🧪 Tests (测试模块)
- **test.py**: 基础功能测试
- **sync_performance_test.py**: 同步性能测试
- **test_api_endpoint.py**: API端点连通性测试

### ⚙️ Config (配置模块)
- **sync_config.json**: 同步系统配置
- **hf_config.json**: 高频策略配置

### 📚 Docs (文档模块)
- 完整的项目文档和使用说明

## 🚀 使用方式

### 快速开始
```bash
# 使用统一管理器
python utils/polymarket_manager.py quickstart

# 或者直接运行主程序
python main.py

# 或者使用运行脚本
python run.py
```

### 数据同步 (推荐使用enhanced_sync.py)
```bash
# 测试API端点
python sync/enhanced_sync.py --test

# 测试CSV结构
python sync/enhanced_sync.py --test-csv

# 批量同步市场数据 (自动生成带日期的文件名)
python sync/enhanced_sync.py --mode markets --batch-size 500

# 同步特定标签的市场数据
python sync/enhanced_sync.py --mode markets --tag-id 123 --batch-size 500

# 使用自定义文件名
python sync/enhanced_sync.py --mode markets --filename "custom_markets.csv"

# 同步特定标签并使用自定义文件名
python sync/enhanced_sync.py --mode markets --tag-id 456 --filename "politics_markets.csv"

# 批量同步事件数据
python sync/enhanced_sync.py --mode events --batch-size 100

# 完整同步 (市场+事件)
python sync/enhanced_sync.py --mode all

# 启用调试模式
python sync/enhanced_sync.py --debug

# 自定义数据目录
python sync/enhanced_sync.py --data-dir ./custom_data

# 组合使用多个参数
python sync/enhanced_sync.py --mode markets --tag-id 789 --batch-size 200 --debug --data-dir ./special_data
```

### 实时监控
```bash
# 启动实时仪表板
python dashboard/live_dashboard.py --monitor
```

### 数据导出和分析
```bash
# 导出Excel格式
python export/data_exporter.py --format excel

# 导出JSON格式
python export/data_exporter.py --format json

# 运行数据分析
python export/data_analyzer.py
```

### 运行测试
```bash
# API端点测试
python tests/test_api_endpoint.py

# 基础功能测试
python tests/test.py

# 同步性能测试
python tests/sync_performance_test.py
```

### 智能代理
```bash
# 启动主代理
python agents/main_agent.py

# 运行价格分析
python agents/price_agent.py

# 运行风险分析
python agents/risk_agent.py
```

## 📋 引用关系

各模块之间的引用关系已经更新，支持新的目录结构。主要的引用模式：

```python
# 核心API客户端
from core.polymarket_client import PolymarketClient
from core.polymarket_market_client import PolymarketMarketClient
from core.polymarket_clob_client import PolymarketCLOBClient

# 数据同步
from sync.enhanced_sync import EnhancedPolymarketSync
from sync.polymarket_sync import PolymarketSynchronizer
from sync.sync_scheduler import SyncScheduler

# 仪表板
from dashboard.live_dashboard import LiveDashboard

# 数据导出
from export.data_exporter import DataExporter
from export.data_analyzer import DataAnalyzer
from export.data_saver import DataSaver

# 智能代理
from agents.main_agent import MainAgent
from agents.price_agent import PriceAgent
from agents.risk_agent import RiskAgent
```

## 🔄 迁移说明

如果你有现有的脚本引用了旧的文件路径，请按照以下方式更新：

```python
# 旧的引用方式
from polymarket_client import PolymarketClient
from enhanced_sync import EnhancedPolymarketSync

# 新的引用方式
from core.polymarket_client import PolymarketClient
from sync.enhanced_sync import EnhancedPolymarketSync
```

## 📊 数据存储结构

```
data/
├── markets/                    # 市场数据
│   ├── markets_2024-01-15.csv        # 按日期命名的市场数据
│   ├── markets_tag_123_2024-01-15.csv # 特定标签的市场数据
│   └── custom_markets.csv            # 自定义文件名
├── events/                     # 事件数据
│   └── events.csv             # 批量事件数据CSV
├── tag/                       # 按标签分类的数据
│   └── [tag_name]/
│       ├── events_*.csv       # 标签相关事件
│       ├── markets_*.csv      # 标签相关市场
│       └── summary_*.json     # 标签摘要
├── reports/                   # 同步报告
│   ├── sync_report_*.json     # JSON格式报告
│   └── sync_report_*.txt      # 文本格式报告
├── offline/                   # 离线测试数据
└── analysis/                  # 分析结果
```

### 📝 文件命名规则

#### 市场数据文件命名：
- **默认格式**: `markets_YYYY-MM-DD.csv` (例: `markets_2024-01-15.csv`)
- **带标签**: `markets_tag_{tag_id}_YYYY-MM-DD.csv` (例: `markets_tag_123_2024-01-15.csv`)
- **自定义**: 用户指定的任意文件名

#### 查询参数：
- **tag_id**: 整数类型，用于筛选特定标签的市场
- **closed**: 默认为 'false'，只获取活跃市场
- **order**: 按 'createdAt' 排序
- **ascending**: 'true'，按时间升序排列

## 🌟 主要特性

### Enhanced Sync (增强同步器)
- ✅ 批量数据获取，支持大规模数据同步
- ✅ 断点续传，基于现有CSV文件自动计算偏移量
- ✅ 智能重试机制，处理网络异常和API限制
- ✅ 多种同步模式：markets、events、all
- ✅ 🆕 标签筛选功能，支持按tag_id获取特定市场
- ✅ 🆕 自动日期文件命名，便于数据管理
- ✅ 🆕 自定义文件名支持
- ✅ 标准化请求头，模拟真实浏览器行为
- ✅ 详细的错误处理和日志记录

### API客户端
- ✅ 支持Polymarket官方API端点
- ✅ 统一的请求头配置
- ✅ 自动重试和错误处理
- ✅ CLOB和Gamma API支持

### 智能代理系统
- ✅ 模块化代理架构
- ✅ 决策引擎支持
- ✅ 价格和风险分析
- ✅ 情感分析功能

## 🔧 配置说明

### 环境变量
复制 `.env.example` 到 `.env` 并配置必要的API密钥和设置。

### 同步配置
编辑 `config/sync_config.json` 来自定义同步行为：
- 批次大小
- 重试次数
- 超时设置
- 通知配置

## 📝 开发指南

### 添加新的API客户端
1. 在 `core/` 目录下创建新的客户端文件
2. 继承基础客户端类或实现标准接口
3. 添加到 `core/__init__.py` 中

### 添加新的同步器
1. 在 `sync/` 目录下创建新的同步器
2. 参考 `enhanced_sync.py` 的模式
3. 实现标准的同步接口

### 添加新的代理
1. 在 `agents/` 目录下创建新的代理
2. 继承 `base_agent.py` 中的基础代理类
3. 实现特定的代理逻辑