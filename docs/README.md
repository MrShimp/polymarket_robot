# Polymarket智能交易Agent系统

一个基于多Agent架构的Polymarket智能交易决策系统，通过实时监控市场数据，使用多个专业化Agent进行分析，并通过决策引擎做出最终交易决策。

## 🏗️ 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Polymarket    │───▶│    主Agent       │───▶│   决策执行      │
│   数据源        │    │  (MainAgent)     │    │  (模拟交易)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    决策引擎      │
                    │ (DecisionEngine) │
                    └──────────────────┘
                              ▲
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 价格分析    │    │ 情绪分析    │    │ 风险分析    │
│ Agent       │    │ Agent       │    │ Agent       │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🤖 核心组件

### 1. 主Agent (MainAgent)
- **职责**: 协调整个系统，管理数据流和决策流程
- **功能**: 
  - 实时监控Polymarket市场
  - 协调子Agent分析
  - 管理决策历史
  - 数据保存到CSV

### 2. 价格分析Agent (PriceAnalysisAgent)
- **职责**: 分析价格趋势和波动性
- **功能**:
  - 价格趋势识别（强烈上升/上升/横盘/下降/强烈下降）
  - 波动性计算
  - 价格动量分析
  - 生成BUY/SELL/HOLD推荐

### 3. 情绪分析Agent (SentimentAnalysisAgent)
- **职责**: 分析市场情绪和交易活动
- **功能**:
  - 交易量分析
  - 市场深度评估
  - 买卖比例计算
  - 市场活跃度评估

### 4. 风险分析Agent (RiskAnalysisAgent)
- **职责**: 评估各种风险因素
- **功能**:
  - 流动性风险评估
  - 时间风险分析（距离到期时间）
  - 波动性风险计算
  - 市场状态风险评估

### 5. 决策引擎 (DecisionEngine)
- **职责**: 综合所有分析结果做出最终决策
- **功能**:
  - 多Agent结果融合
  - 风险调整
  - 置信度计算
  - 执行决策判断

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动系统

#### 交互模式
```bash
python main.py
```

#### 命令行模式
```bash
# 启动实时监控
python main.py start

# 分析单个市场
python main.py analyze <condition_id>
```

## 📊 使用示例

### 交互式菜单
```
=== Polymarket智能交易Agent系统 ===
1. 启动实时监控系统
2. 分析单个市场
3. 查看系统状态
4. 查看决策历史
5. 退出
```

### 分析结果示例
```
=== 市场分析结果 ===
市场ID: 0x1234...
问题: Will Trump win the 2024 election?
状态: 活跃

=== Agent分析结果 ===

PriceAnalyzer:
  推荐: BUY
  置信度: 0.75
  推理: 上升趋势 | 正向动量 | 低波动性

SentimentAnalyzer:
  推荐: BUY - 市场情绪乐观且活跃
  置信度: 0.68
  推理: 市场情绪乐观 | 市场活跃度: 活跃 | 交易量: high

RiskAnalyzer:
  推荐: MODERATE - 中等风险，适度参与
  置信度: 0.82
  推理: 流动性风险: low | 时间风险: medium | 波动性风险: low

=== 最终决策 ===
动作: BUY
置信度: 0.73
是否执行: true
推理: Agent推荐: PriceAnalyzer: BUY | SentimentAnalyzer: BUY | RiskAnalyzer: MODERATE | 投票结果: BUY (1.1) | 风险等级: medium
```

## ⚙️ 配置说明

### 系统配置
```python
config = {
    'update_interval': 120,     # 监控间隔（秒）
    'max_markets': 3,           # 同时监控的最大市场数
    'min_confidence': 0.6,      # 最小执行置信度
    'decision_config': {
        'risk_tolerance': 'medium',  # 风险容忍度: low/medium/high
        'agent_weights': {           # Agent权重
            'PriceAnalyzer': 0.4,
            'SentimentAnalyzer': 0.3,
            'RiskAnalyzer': 0.3
        }
    }
}
```

### 市场过滤器
```python
market_filters = {
    'tags': ['politics', 'crypto', 'sports'],
    'keywords': ['trump', 'bitcoin', 'election']
}
```

## 📁 数据保存

系统自动将所有数据保存到 `./data` 目录：

- `markets_*.csv` - 市场列表数据
- `market_detail_*.csv` - 市场详情数据
- `prices_*.csv` - 价格数据
- `orderbook_*.csv` - 订单簿数据
- `trades_*.csv` - 交易数据
- `decisions_daily_*.csv` - 决策历史数据

## 🔒 风险管理

### 多层风险控制
- **置信度阈值**: 只有高置信度的决策才会执行
- **风险等级评估**: 综合评估流动性、时间、波动性等风险
- **风险容忍度调整**: 根据设定的风险偏好调整决策
- **模拟交易**: 默认为模拟模式，避免真实资金风险

### Agent权重平衡
- **价格分析**: 40% 权重，关注技术面
- **情绪分析**: 30% 权重，关注市场情绪
- **风险分析**: 30% 权重，关注风险控制

## 📈 决策逻辑

### 推荐生成
每个Agent基于自己的专业领域生成推荐：
- **价格Agent**: BUY/STRONG_BUY/SELL/STRONG_SELL/HOLD
- **情绪Agent**: BUY/SELL/HOLD + 具体原因
- **风险Agent**: AVOID/CAUTION/MODERATE/ACCEPTABLE/SAFE

### 最终决策
决策引擎综合考虑：
1. 各Agent推荐的加权投票
2. 综合置信度计算
3. 风险等级调整
4. 最终执行判断

## 🔧 扩展开发

### 添加新Agent
```python
from agents.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__("NewAgent", "新Agent描述")
    
    def analyze(self, market_data):
        # 实现分析逻辑
        return {
            "recommendation": "BUY",
            "confidence": 0.8,
            "reasoning": "分析推理"
        }
```

### 自定义决策权重
```python
agent_weights = {
    'PriceAnalyzer': 0.5,      # 增加价格分析权重
    'SentimentAnalyzer': 0.2,  # 降低情绪分析权重
    'RiskAnalyzer': 0.3        # 保持风险分析权重
}
```

## ⚠️ 注意事项

1. **模拟模式**: 系统默认运行在模拟模式，不会执行真实交易
2. **API限制**: 注意Polymarket API的调用频率限制
3. **数据质量**: 决策质量依赖于数据的完整性和准确性
4. **风险提示**: 本系统仅供学习研究，实际交易需谨慎

## 🐛 故障排除

### 常见问题
1. **API连接失败**: 检查网络连接
2. **数据获取异常**: 验证市场ID有效性
3. **Agent分析失败**: 检查数据格式完整性
4. **决策不执行**: 检查置信度阈值设置

### 日志查看
```bash
tail -f agent_system.log
```

## 📄 许可证

本项目仅供学习和研究使用，请勿用于实际交易，风险自负。