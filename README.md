# Polymarket自动交易系统

## 项目结构

```
polymarket_robot/
├── sync/                           # 数据同步模块
│   ├── enhanced_sync.py            # 增强同步器
│   ├── polymarket_sync.py          # Polymarket同步器
│   ├── urgent_markets_sync.py      # 紧急市场同步器
│   ├── tag_markets_sync.py         # 标签市场同步器
│   ├── market_search.py            # 市场搜索工具
│   └── find_tag_id.py              # 标签ID查找工具
├── trading/                        # 交易模块
│   ├── polymarket_clob_client.py   # CLOB API客户端
│   ├── order_manager.py            # 订单管理器
│   ├── config.py                   # 交易配置
│   ├── strategy_trader.py          # 策略交易执行器
│   └── setup_credentials.py        # API凭证设置工具
├── strategies/                     # 交易策略模块
│   ├── urgent_high_confidence_strategy.py  # 紧急高置信度策略
│   ├── flexible_urgent_strategy.py         # 灵活参数策略
│   ├── btc_15min_strategy.py       # BTC 15分钟策略
│   └── trading_bot.py              # 智能交易机器人
├── core/                           # 核心模块
│   ├── polymarket_client.py        # Polymarket API客户端
│   └── polymarket_market_client.py # 市场数据客户端
├── config/                         # 配置文件
│   ├── sys_config.json             # 系统配置
│   ├── sync_config.json            # 同步配置
│   └── btc_strategy_config.json    # BTC策略配置
├── data/                           # 数据存储
│   ├── markets/                    # 市场数据
│   ├── urgent/                     # 紧急市场数据
│   ├── tags/                       # 标签市场数据
│   ├── strategies/                 # 策略结果数据
│   ├── orders/                     # 订单记录
│   ├── reports/                    # 分析报告
│   ├── btc/                        # BTC价格数据
│   ├── btc_strategy_logs/          # BTC策略日志
│   ├── btc_trades/                 # BTC交易记录
│   ├── btc_intervals/              # BTC 15分钟区间数据
│   ├── trading_logs/               # 交易日志
│   ├── quick_trades/               # 快速交易记录
│   └── test_reports/               # 测试报告
├── 🎯 BTC 15分钟策略系统
│   ├── btc_15min_strategy.py       # 主策略实现
│   ├── run_btc_strategy.py         # 快速启动脚本
│   ├── btc_strategy_monitor.py     # 实时监控面板
│   ├── test_btc_strategy.py        # 策略测试套件
│   ├── start_btc_monitor.py        # 策略管理器
│   ├── BTC_STRATEGY_GUIDE.md       # 详细使用指南
│   └── QUICK_START_GUIDE.md        # 快速开始指南
├── 🤖 BTC自动交易器
│   ├── btc_auto_trader.py          # 定时自动交易器
│   ├── btc_smart_auto_trader.py    # 智能自动交易器（新）
│   ├── start_smart_trader.py       # 智能交易器启动脚本
│   ├── test_smart_trader_logic.py  # 时间判断逻辑测试
│   ├── BTC_AUTO_TRADER_README.md   # 定时交易器说明
│   └── BTC_SMART_AUTO_TRADER_README.md # 智能交易器说明
├── 🤖 通用交易机器人
│   ├── trading_bot.py              # 智能交易机器人
│   ├── quick_trading_bot.py        # 快速交易机器人
│   ├── run_bot.py                  # 机器人启动器
│   └── test_trading_bot.py         # 机器人测试
├── 🔍 市场搜索和分析工具
│   ├── market_finder.py            # 市场查找器
│   ├── improved_market_search.py   # 改进的市场搜索
│   ├── find_ending_markets.py      # 即将结束市场查找
│   ├── analyze_tag_markets.py      # 标签市场分析
│   └── tag_search_demo.py          # 标签搜索演示
├── 📋 下单和管理工具
│   ├── place_single_order.py       # 单一市场交互式下单
│   ├── quick_order.py              # 快速下单工具
│   ├── demo_order.py               # 下单演示脚本
│   ├── order_management_tool.py    # 订单管理工具
│   └── setup_polymarket_config.py  # 配置设置工具
├── 📖 文档和指南
│   ├── README.md                   # 项目说明
│   ├── MARKET_SEARCH_GUIDE.md      # 市场搜索指南
│   ├── BTC_STRATEGY_GUIDE.md       # BTC策略详细指南
│   └── QUICK_START_GUIDE.md        # 快速开始指南
└── requirements.txt                # Python依赖
```

## 启动方式

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置私钥
```bash
python3 trading/setup_credentials.py
# 或使用配置工具
python3 setup_polymarket_config.py
```

## 🎯 BTC 15分钟策略系统

### 快速开始
```bash
# 1. 测试策略
python3 test_btc_strategy.py

# 2. 一键启动（监控面板 + 策略）
python3 start_btc_monitor.py full <market_id> <yes|no> [amount]

# 示例
python3 start_btc_monitor.py full 123456 yes 10
```

### 分别启动
```bash
# 启动实时监控面板
python3 btc_strategy_monitor.py

# 启动策略（新终端窗口）
python3 run_btc_strategy.py <market_id> <yes|no> [amount]

# 示例
python3 run_btc_strategy.py 123456 yes 15
```

### 管理器模式
```bash
# 交互式管理器
python3 start_btc_monitor.py

# 命令行模式
python3 start_btc_monitor.py test                    # 运行测试
python3 start_btc_monitor.py monitor                 # 只启动监控
python3 start_btc_monitor.py strategy <id> <yes|no> [amount]  # 只启动策略
```

### 策略特性
- **交易时段**: 10:00-19:00 北京时间
- **入场条件**: 75%概率 + BTC波动±30刀 + 方向匹配
- **止盈**: 90%概率
- **止损**: 55%概率
- **特殊止盈**: 85%概率 + 连续30秒横盘

## 🤖 BTC自动交易器

### 智能自动交易器（推荐）
```bash
# 快速启动（交互式界面）
python3 start_smart_trader.py

# 直接启动
python3 btc_smart_auto_trader.py [交易金额]

# 测试时间判断逻辑
python3 test_smart_trader_logic.py
```

**智能特性**：
- 启动后自动判断与上一个15分钟市场的间隔
- **< 5分钟**：直接参与上一个市场
- **≥ 5分钟**：等待下一个市场
- 最大化交易机会，随时启动

### 定时自动交易器
```bash
# 启动定时交易器
python3 btc_auto_trader.py [交易金额]
```

**定时特性**：
- 等待下一个15分钟整点启动
- 适合定时任务和计划启动

## 🤖 通用交易机器人

### 智能交易机器人
```bash
# 交互式启动
python3 trading_bot.py

# 测试机器人
python3 test_trading_bot.py
```

### 快速交易机器人
```bash
# 命令行模式
python3 quick_trading_bot.py <market_id> <yes|no> [amount]

# 示例
python3 quick_trading_bot.py 123456 yes 20
```

### 机器人启动器
```bash
# 启动机器人
python3 run_bot.py
```

## 🔍 市场搜索和分析

### 市场搜索工具
```bash
# 基础市场查找
python3 market_finder.py

# 改进的市场搜索
python3 improved_market_search.py

# 查找即将结束的市场
python3 find_ending_markets.py

# 市场搜索（同步模块）
python3 sync/market_search.py
```

### 标签和关键词搜索
```bash
# 查找标签ID
python3 sync/find_tag_id.py

# 标签市场分析
python3 analyze_tag_markets.py --tag-pattern sports

# 标签搜索演示
python3 tag_search_demo.py

# 通过事件搜索市场（新功能）
python3 sync/tag_markets_sync.py --keywords bitcoin --search-method event

# 直接搜索市场
python3 sync/tag_markets_sync.py --keywords bitcoin --search-method direct

# 综合搜索（事件+直接）
python3 sync/tag_markets_sync.py --keywords bitcoin --search-method both

# 测试事件搜索功能
python3 test_event_search.py
```

## 📋 下单和订单管理

### 单一市场下单
```bash
# 交互式下单
python3 place_single_order.py

# 快速下单
python3 quick_order.py <market_id> <yes/no> <amount>

# 示例
python3 quick_order.py 0x1234567890abcdef yes 10.5
python3 quick_order.py 0x1234567890abcdef no 25.0

# 跳过确认直接下单
python3 quick_order.py 0x1234567890abcdef yes 10.5 --confirm

# 查看下单演示
python3 demo_order.py
```

### 订单管理
```bash
# 订单管理工具
python3 order_management_tool.py
```

## 📊 数据同步

### 市场数据同步
```bash
# 同步市场数据
python3 sync/polymarket_sync.py

# 同步紧急市场数据
python3 sync/urgent_markets_sync.py --minutes 15

# 增强同步器
python3 sync/enhanced_sync.py
```

### 标签市场同步
```bash
# 按标签同步
python3 sync/tag_markets_sync.py --tags sports NFL NBA
python3 sync/tag_markets_sync.py --tags politics --keywords election

# 按关键词同步
python3 sync/tag_markets_sync.py --keywords bitcoin crypto

# 通过事件搜索（新功能）
python3 sync/tag_markets_sync.py --keywords bitcoin --search-method event

# 综合搜索方法
python3 sync/tag_markets_sync.py --keywords bitcoin --search-method both
```

## 🎯 策略交易

### 紧急策略
```bash
# 单次策略执行
python3 run_urgent_strategy.py

# 循环策略执行
python3 run_strategy_loop.py --interval 10

# 灵活参数策略
python3 strategies/flexible_urgent_strategy.py --time 30 --min-conf 0.8 --max-conf 0.95
```

### 策略交易系统
```bash
# 策略交易器
python3 trading/strategy_trader.py --mode single
```
## 🚀 快速
命令参考

### BTC 15分钟策略
```bash
# 完整启动
python3 start_btc_monitor.py full <market_id> <yes|no> [amount]

# 测试策略
python3 test_btc_strategy.py

# 监控面板
python3 btc_strategy_monitor.py

# 策略执行
python3 run_btc_strategy.py <market_id> <yes|no> [amount]
```

### BTC自动交易器
```bash
# 智能自动交易器（推荐）
python3 start_smart_trader.py

# 直接启动智能交易器
python3 btc_smart_auto_trader.py [交易金额]

# 定时自动交易器
python3 btc_auto_trader.py [交易金额]

# 测试时间逻辑
python3 test_smart_trader_logic.py
```

### 通用交易
```bash
# 智能机器人
python3 trading_bot.py

# 快速交易
python3 quick_trading_bot.py <market_id> <yes|no> [amount]

# 单次下单
python3 quick_order.py <market_id> <yes|no> <amount>
```

### 市场搜索
```bash
# 市场查找
python3 market_finder.py

# 即将结束市场
python3 find_ending_markets.py

# 标签搜索
python3 sync/find_tag_id.py
```

## 📖 详细文档

- **[BTC策略详细指南](BTC_STRATEGY_GUIDE.md)** - BTC 15分钟策略完整说明
- **[BTC智能交易器指南](BTC_SMART_AUTO_TRADER_README.md)** - 智能自动交易器详细说明
- **[BTC定时交易器指南](BTC_AUTO_TRADER_README.md)** - 定时自动交易器说明
- **[快速开始指南](QUICK_START_GUIDE.md)** - 智能交易器快速启动
- **[市场搜索指南](MARKET_SEARCH_GUIDE.md)** - 市场搜索工具使用说明

## ⚠️ 重要提醒

### 使用前准备
1. **配置API**: 确保正确配置Polymarket API凭证
2. **测试优先**: 首次使用请先运行相关测试脚本
3. **网络稳定**: 确保网络连接稳定，策略依赖实时数据

### 风险管理
1. **资金控制**: 建议单笔交易金额控制在合理范围内
2. **监控重要**: 使用监控面板实时跟踪策略状态
3. **及时止损**: 注意市场风险，及时止损

### 技术要求
- Python 3.8+
- 稳定的网络连接
- 足够的API调用配额

## 🛠️ 故障排除

### 常见问题
1. **API错误**: 检查配置文件中的API凭证
2. **网络超时**: 检查网络连接，可能需要重试
3. **价格获取失败**: 检查数据源API是否正常
4. **策略不入场**: 检查时间窗口、价格阈值、概率条件

### 日志查看
- BTC策略日志: `data/btc_strategy_logs/`
- 交易记录: `data/btc_trades/`, `data/quick_trades/`
- 测试报告: `data/test_reports/`

### 获取帮助
1. 查看相关日志文件
2. 运行测试脚本检查状态
3. 查看详细文档和指南

## 📊 数据目录说明

```
data/
├── markets/              # 市场数据
├── urgent/              # 紧急市场数据
├── tags/                # 标签市场数据
├── btc/                 # BTC价格数据
├── btc_strategy_logs/   # BTC策略日志
├── btc_trades/          # BTC交易记录
├── btc_intervals/       # BTC 15分钟区间数据
├── trading_logs/        # 通用交易日志
├── quick_trades/        # 快速交易记录
├── orders/              # 订单记录
├── strategies/          # 策略结果
├── reports/             # 分析报告
└── test_reports/        # 测试报告
```

## 🔧 配置文件

- `config/sys_config.json` - 系统主配置
- `config/sync_config.json` - 数据同步配置
- `config/btc_strategy_config.json` - BTC策略配置

## 📈 策略类型

1. **BTC 15分钟策略** - 专门针对BTC预测市场的高频策略
2. **紧急高置信度策略** - 基于时间和置信度的快速策略
3. **灵活参数策略** - 可自定义参数的通用策略
4. **智能交易机器人** - 多条件综合判断的自动交易

---

**免责声明**: 本系统仅供学习和研究使用，不构成投资建议。使用者需自行承担交易风险。