# Polymarket Robot 项目结构

## 目录结构

```
polymarket_robot/
├── core/                           # 核心模块
│   ├── __init__.py
│   ├── polymarket_client.py        # Polymarket API客户端
│   └── polymarket_market_client.py # 市场数据客户端
├── data/                           # 数据存储
│   ├── markets/                    # 市场数据
│   ├── events/                     # 事件数据
│   ├── urgent/                     # 紧急市场数据
│   ├── strategies/                 # 策略结果数据
│   ├── reports/                    # 分析报告
│   └── sync_logs/                  # 同步日志
├── sync/                           # 数据同步模块
│   ├── __init__.py
│   ├── enhanced_sync.py            # 增强同步器
│   ├── polymarket_sync.py          # Polymarket同步器
│   └── urgent_markets_sync.py      # 紧急市场同步器
├── strategies/                     # 交易策略模块
│   ├── __init__.py
│   ├── urgent_high_confidence_strategy.py  # 紧急高置信度策略
│   └── flexible_urgent_strategy.py         # 灵活参数策略
├── trading/                        # 交易模块
│   ├── __init__.py
│   ├── polymarket_clob_client.py   # CLOB API客户端
│   ├── config.py                   # 交易配置
│   ├── strategy_trader.py          # 策略交易执行器
│   ├── setup_credentials.py        # API凭证设置工具
│   └── test_trading.py             # 交易功能测试
├── tests/                          # 测试文件
│   ├── __init__.py
│   └── test.py                     # 基础测试
├── run_urgent_strategy.py          # 策略运行脚本
├── run_strategy_loop.py            # 策略循环运行脚本
├── requirements.txt                # Python依赖
├── README.md                       # 项目说明
├── PROJECT_STRUCTURE.md            # 原项目结构文档
├── PROJECT_STRUCTURE_UPDATED.md    # 更新的项目结构文档
├── URGENT_STRATEGY_GUIDE.md        # 策略使用指南
├── STRATEGY_SUMMARY.md             # 策略总结文档
└── TRADING_GUIDE.md                # 交易系统使用指南
```

## 模块说明

### core/ - 核心模块
- **polymarket_client.py**: 基础的Polymarket API客户端，提供基本的API调用功能
- **polymarket_market_client.py**: 专门用于市场数据获取的客户端，包含市场、事件相关的API调用

### sync/ - 数据同步模块
- **enhanced_sync.py**: 增强版同步器，支持多种数据源和同步策略
- **polymarket_sync.py**: Polymarket数据同步器，按标签分类同步市场数据
- **urgent_markets_sync.py**: 紧急市场同步器，专门获取即将结束的市场

### strategies/ - 交易策略模块
- **urgent_high_confidence_strategy.py**: 核心策略引擎，扫描10分钟内结束且胜率在0.9-0.95之间的市场
- **flexible_urgent_strategy.py**: 灵活参数版本，支持自定义时间阈值和胜率范围

### trading/ - 交易模块
- **polymarket_clob_client.py**: 完整的CLOB API客户端，支持订单管理、市场数据、账户信息
- **config.py**: 交易配置管理，支持环境变量和配置文件
- **strategy_trader.py**: 策略交易执行器，集成策略扫描和自动交易
- **setup_credentials.py**: API凭证设置工具，交互式配置API密钥
- **test_trading.py**: 交易功能测试脚本

### data/ - 数据存储
- **markets/**: 存储市场数据的CSV文件
- **events/**: 存储事件数据
- **urgent/**: 存储紧急市场数据
- **strategies/**: 存储策略扫描结果
- **reports/**: 存储分析报告（JSON格式）
- **sync_logs/**: 存储同步过程的日志文件

### tests/ - 测试模块
- **test.py**: 包含各种功能的测试用例

## 使用方法

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 设置API凭证（用于交易功能）
```bash
python3 trading/setup_credentials.py
```

### 3. 运行策略
```bash
# 基础策略（10分钟，90%-95%胜率）
python3 run_urgent_strategy.py

# 灵活策略（30分钟，80%-95%胜率）
python3 strategies/flexible_urgent_strategy.py --time 30 --min-conf 0.8 --max-conf 0.95

# 策略循环运行
python3 run_strategy_loop.py --interval 10 --time 30 --min-conf 0.8 --max-conf 0.95
```

### 4. 运行交易系统
```bash
# 单次扫描和交易（模拟模式）
python3 trading/strategy_trader.py --mode single

# 连续交易模式
python3 trading/strategy_trader.py --mode continuous --interval 10

# 实盘交易（谨慎使用）
python3 trading/strategy_trader.py --mode single --real-trade
```

### 5. 运行同步器
```bash
# 运行增强同步器
python3 sync/enhanced_sync.py

# 运行Polymarket同步器
python3 sync/polymarket_sync.py

# 运行紧急市场同步器
python3 sync/urgent_markets_sync.py --minutes 15
```

### 6. 运行测试
```bash
# 基础功能测试
python3 tests/test.py

# 交易功能测试
python3 trading/test_trading.py
```

## 数据格式

### 市场数据格式
CSV文件包含以下字段：
- id: 市场ID
- question: 市场问题
- slug: URL slug
- category: 分类
- outcomes: 结果选项
- outcomePrices: 结果价格
- volume: 交易量
- liquidity: 流动性
- endDate: 结束时间

### 策略结果格式
包含原始市场数据和策略分析结果：
- strategy_confidence: 策略置信度
- strategy_winning_option: 胜出选项
- strategy_time_remaining_minutes: 剩余时间
- strategy_scan_timestamp: 扫描时间戳

### 交易配置格式
```json
{
  "api_credentials": {
    "api_key": "your_api_key",
    "api_secret": "your_api_secret", 
    "passphrase": "your_passphrase"
  },
  "network": {
    "testnet": true
  },
  "trading": {
    "default_trade_amount": 10.0,
    "max_slippage": 0.02,
    "dry_run_mode": true
  }
}
```

## 核心功能

### 1. 策略扫描
- 自动扫描Polymarket市场
- 筛选即将结束的高置信度机会
- 支持灵活的参数配置
- 生成详细的分析报告

### 2. 自动交易
- 集成CLOB API进行实际交易
- 支持限价单和市价单
- 滑点保护和风险管理
- 订单状态监控

### 3. 风险管理
- 参数验证和限制
- 模拟交易模式
- 仓位大小控制
- 实时监控和统计

### 4. 数据管理
- 多格式数据存储（CSV、JSON）
- 历史数据追踪
- 详细的执行日志
- 性能统计分析

## 扩展说明

项目采用模块化设计，便于扩展和维护：
- 可以轻松添加新的交易策略
- 支持不同的风险管理规则
- 数据格式标准化，便于分析和处理
- 完整的测试覆盖和文档支持

## 安全注意事项

1. **API凭证安全**: 
   - 使用环境变量或加密配置文件
   - 不要将凭证提交到版本控制系统

2. **交易安全**:
   - 始终从测试网开始
   - 使用小额资金进行初始测试
   - 启用模拟模式进行策略验证

3. **风险控制**:
   - 设置合理的仓位限制
   - 监控交易频率和总量
   - 定期检查策略表现