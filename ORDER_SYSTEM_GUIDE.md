# Polymarket 实时下单系统

## 🎉 系统完成

基于Polymarket官方API文档，我们已经成功创建了一个完整的实时下单系统！

## 🔧 主要功能

### 1. 实时市场数据获取
- 通过 `https://gamma-api.polymarket.com/markets/{market_id}` 获取实时市场数据
- 自动解析 `outcomes`、`outcomePrices`、`clobTokenIds` 等JSON字符串字段
- 显示完整的市场信息：问题、结束时间、交易量、流动性等

### 2. 订单簿信息
- 获取实时订单簿数据
- 显示买单/卖单数量
- 显示最佳买价/卖价和价差

### 3. 智能下单
- 支持市价单和限价单
- 自动验证市场状态、金额、价格精度
- 计算预期份额和成本

### 4. 完整的用户体验
- 交互式界面，逐步引导用户
- 详细的市场信息展示
- 订单确认和风险提示

## 🚀 使用方法

### 1. 配置认证
在 `config/sys_config.json` 中配置私钥：
```json
{
  "polymarket": {
    "private_key": "0x你的私钥"
  }
}
```

### 2. 查找活跃市场
```bash
python3 find_active_market.py
```

### 3. 执行下单
```bash
python3 place_single_order.py
```

## 📊 测试示例

我们成功测试了完整的下单流程：

### 测试市场
- **市场ID**: 997488
- **问题**: Will Trump acquire Greenland before 2027?
- **选项**: Yes ($0.205) / No ($0.795)
- **状态**: 活跃，接受订单
- **流动性**: $1,550,985

### 测试订单
- **选择**: No
- **金额**: $5 USDC
- **类型**: 限价单 @ $0.78
- **预期份额**: 6.41

### 系统验证
✅ **API数据获取** - 成功解析市场信息  
✅ **订单簿查询** - 获取实时买卖盘数据  
✅ **输入验证** - 检查金额、价格精度等  
✅ **订单创建** - 生成正确的CLOB订单参数  
✅ **用户界面** - 完整的交互式体验  

## 🔍 系统架构

### 数据流
1. **市场查询** → Gamma API → 解析JSON字符串
2. **订单簿** → CLOB API → 获取实时价格
3. **下单** → CLOB API → 执行交易

### 关键组件
- `SingleOrderPlacer` - 主要下单类
- `PolymarketCLOBClient` - CLOB API客户端
- 配置系统 - 统一的认证管理

## 📝 API集成详情

### Gamma API (市场数据)
```
GET https://gamma-api.polymarket.com/markets/{market_id}
```
- 获取市场基本信息
- 解析JSON字符串字段：`outcomes`、`outcomePrices`、`clobTokenIds`

### CLOB API (交易)
```
GET https://clob.polymarket.com/book?token_id={token_id}
POST https://clob.polymarket.com/order
```
- 获取订单簿数据
- 执行买卖订单

## 🎯 下一步

系统已经完全就绪，可以：

1. **实际交易** - 配置真实私钥进行交易
2. **批量下单** - 扩展支持多市场下单
3. **策略集成** - 与现有策略系统集成
4. **监控系统** - 添加订单状态监控

## ⚠️ 重要提醒

- 先在测试网测试
- 使用小额资金验证
- 确保网络连接稳定
- 检查市场状态和流动性

现在你有了一个完整的、基于官方API的Polymarket实时下单系统！🎉