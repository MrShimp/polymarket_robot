# 🚀 Polymarket Robot 使用指南

## 📁 新的项目结构

项目已重新组织为模块化结构，各功能分类存放：

```
polymarket_robot/
├── 📦 core/           # API客户端
├── 🔄 sync/           # 数据同步
├── 📊 dashboard/      # 监控仪表板
├── 📤 export/         # 数据导出分析
├── 🤖 agents/         # 智能代理
├── 🛠️ utils/          # 系统管理
├── 🧪 tests/          # 测试文件
├── ⚙️ config/         # 配置文件
├── 📚 docs/           # 文档
└── 📁 data/           # 数据存储
```

## 🎯 快速开始

### 方式1: 使用统一启动脚本 (推荐)

```bash
# 系统管理
python3 run.py manager quickstart

# 数据同步
python3 run.py sync --args --offline

# 实时监控
python3 run.py dashboard --args --monitor

# 数据导出
python3 run.py export --args --format excel

# 智能代理
python3 run.py agents

# 运行测试
python3 run.py tests scheduler
```

### 方式2: 直接调用模块

```bash
# 系统管理
python3 -m utils.polymarket_manager quickstart

# 数据同步
python3 -m sync.enhanced_sync --offline

# 实时监控
python3 -m dashboard.live_dashboard --monitor

# 数据导出
python3 -m export.data_exporter --format excel

# 智能代理
python3 main.py

# 运行测试
python3 -m tests.simple_scheduler_test
```

### 方式3: 传统方式 (需要在对应目录)

```bash
# 进入对应目录后运行
cd sync && python3 enhanced_sync.py --offline
cd dashboard && python3 live_dashboard.py --monitor
cd export && python3 data_exporter.py --format excel
```

## 📋 各模块详细使用

### 🔄 数据同步模块 (sync/)

```bash
# 离线模式同步
python3 run.py sync --args --offline

# API模式同步
python3 run.py sync

# 生成离线数据
python3 run.py sync --args --generate-offline

# 启动调度器
python3 -m sync.sync_scheduler --action start --daemon

# 查看同步状态
python3 -m sync.sync_monitor --action status
```

### 📊 监控仪表板 (dashboard/)

```bash
# 静态仪表板
python3 run.py dashboard

# 实时监控 (30秒刷新)
python3 run.py dashboard --args --monitor

# 自定义刷新间隔
python3 run.py dashboard --args --monitor --interval 60
```

### 📤 数据导出分析 (export/)

```bash
# 导出Excel
python3 run.py export --args --format excel

# 导出JSON
python3 run.py export --args --format json

# 导出CSV包
python3 run.py export --args --format csv

# 生成分析报告
python3 run.py export --args --format report

# 指定标签导出
python3 run.py export --args --format excel --tags crypto politics

# 数据分析
python3 -m export.data_analyzer --output text
```

### 🤖 智能代理 (agents/)

```bash
# 启动主代理系统
python3 run.py agents

# 命令行模式
python3 main.py start                    # 启动监控
python3 main.py analyze <condition_id>   # 分析单个市场
```

### 🛠️ 系统管理 (utils/)

```bash
# 系统状态
python3 run.py manager status

# 快速开始
python3 run.py manager quickstart

# 初始化系统
python3 run.py manager init

# 清理旧数据
python3 run.py manager clean

# 各种操作
python3 run.py manager sync --args --offline
python3 run.py manager dashboard --args --monitor
python3 run.py manager export --args --format excel
```

### 🧪 测试模块 (tests/)

```bash
# 调度器测试
python3 run.py tests scheduler

# 性能测试
python3 run.py tests performance

# API测试
python3 -m tests.test_api_endpoint

# CLOB测试
python3 -m tests.test_clob
```

## 🔧 开发指南

### 导入模块

```python
# 核心API客户端
from core.polymarket_client import PolymarketClient
from core.polymarket_market_client import PolymarketMarketClient

# 数据同步
from sync.enhanced_sync import EnhancedPolymarketSync
from sync.sync_scheduler import SyncScheduler

# 仪表板
from dashboard.live_dashboard import LiveDashboard

# 数据导出
from export.data_exporter import DataExporter
from export.data_analyzer import DataAnalyzer

# 智能代理
from agents.main_agent import MainAgent
from agents.decision_engine import DecisionEngine

# 系统管理
from utils.polymarket_manager import PolymarketManager
```

### 配置文件

配置文件现在位于 `config/` 目录：

- `config/sync_config.json` - 同步配置
- `config/hf_config.json` - 高频策略配置

### 数据存储

数据继续存储在 `data/` 目录：

- `data/tag/` - 按标签分类的数据
- `data/reports/` - 同步报告
- `data/offline/` - 离线测试数据
- `data/analysis/` - 分析结果

## 🚨 迁移注意事项

1. **更新导入语句**: 所有的导入都需要加上模块前缀
2. **配置文件路径**: 配置文件移动到了 `config/` 目录
3. **脚本路径**: 使用新的启动方式或更新脚本路径
4. **测试文件**: 测试文件移动到了 `tests/` 目录

## 💡 推荐工作流

1. **开发阶段**: 使用 `python3 run.py` 统一启动脚本
2. **生产环境**: 使用 `python3 -m` 模块调用方式
3. **测试**: 使用 `tests/` 目录下的测试文件
4. **管理**: 使用 `utils/polymarket_manager.py` 进行系统管理

## 🔍 故障排除

如果遇到导入错误：

1. 确保在项目根目录运行命令
2. 检查 `__init__.py` 文件是否存在
3. 使用 `python3 -m` 方式调用模块
4. 检查 Python 路径设置

如果遇到文件路径错误：

1. 使用相对于项目根目录的路径
2. 检查配置文件是否在正确位置
3. 确保数据目录结构正确