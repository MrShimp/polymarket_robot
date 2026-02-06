#!/usr/bin/env python3
"""
Polymarket 买入策略模块
从 btc_15min_strategy.py 中提取的入场操作功能
"""
import asyncio
from typing import Tuple
from py_clob_client.clob_types import (
    MarketOrderArgs,
    OrderType,
    OrderArgs,
)


class BuyStrategy:
    """买入策略类"""

    def __init__(self, clob_client, logger=None):
        """
        初始化买入策略

        Args:
            clob_client: Polymarket CLOB客户端
            logger: 日志记录器函数，如果为None则使用print
        """
        self.clob_client = clob_client
        self.log = logger if logger else print

    async def enter_position(
        self, token_id: str, price: float, current_prob: float
    ) -> Tuple[bool, float]:
        """
        入场操作

        Args:
            token_id: 代币ID
            price: 交易金额
            current_prob: 当前概率

        Returns:
            Tuple[bool, float]: (是否成功, 实际购买金额)
        """
        try:
            # 验证参数
            is_valid, error_msg = self.validate_buy_parameters(token_id, price, current_prob)
            if not is_valid:
                self.log(f"❌ 参数验证失败: {error_msg}")
                return False, 0.0

            # 验证最小交易金额
            if price < 1.0:
                self.log(f"❌ 交易金额${price}小于最小要求$1.0")
                return False, 0.0

            self.log(f"🎯 准备入场: token_id={token_id}, 金额=${price}")

            # 直接使用传入的金额，不进行任何格式化
            shares_rounded = price

            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=shares_rounded,
                side="BUY",
            )
            self.log(f"💰 交易金额: {shares_rounded} (直接使用传入参数)")

            signed_order = self.clob_client.create_market_order(order_args)
            result = self.clob_client.post_order(signed_order, orderType=OrderType.FOK)

            if result and result.get("orderID"):
                self.log(f"✅ 入场订单提交成功: {result}")
                self.log(f"📋 订单详情: {shares_rounded} @ 概率{current_prob:.3f}")
                return True, shares_rounded  # 返回实际购买的金额
            else:
                self.log(f"❌ 入场订单失败: {result}")
                return False, 0.0

        except Exception as e:
            error_str = str(e)
            self.log(f"❌ 入场操作失败: {e}")
            
            # 检查是否是最小金额错误
            if "minimum" in error_str.lower() or "amount" in error_str.lower():
                self.log(f"💡 提示: 可能是交易金额不满足最小要求，当前金额${price}")
            
            return False, 0.0

    async def create_buy_order(
        self, token_id: str, amount: float, side: str = "BUY"
    ) -> Tuple[bool, dict]:
        """
        创建买入订单的通用方法

        Args:
            token_id: 代币ID
            amount: 交易金额
            side: 交易方向，默认为"BUY"

        Returns:
            Tuple[bool, dict]: (是否成功, 订单结果)
        """
        try:
            self.log(f"📝 创建{side}订单: token_id={token_id}, 金额={amount}")

            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=side,
            )

            signed_order = self.clob_client.create_market_order(order_args)
            result = self.clob_client.post_order(signed_order, orderType=OrderType.FOK)

            if result and result.get("orderID"):
                self.log(f"✅ {side}订单创建成功: {result.get('orderID')}")
                return True, result
            else:
                self.log(f"❌ {side}订单创建失败: {result}")
                return False, result or {}

        except Exception as e:
            self.log(f"❌ 创建{side}订单异常: {e}")
            return False, {"error": str(e)}

    def validate_buy_parameters(
        self, token_id: str, amount: float, current_prob: float = None
    ) -> Tuple[bool, str]:
        """
        验证买入参数

        Args:
            token_id: 代币ID
            amount: 交易金额
            current_prob: 当前概率（可选）

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not token_id or not isinstance(token_id, str):
            return False, "token_id 必须是非空字符串"

        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "amount 必须是大于0的数字"

        if amount < 1.0:
            return False, f"amount ${amount} 小于最小要求 $1.0"

        if current_prob is not None and (
            not isinstance(current_prob, (int, float))
            or current_prob < 0
            or current_prob > 1
        ):
            return False, "current_prob 必须是0-1之间的数字"

        return True, "参数验证通过"

    async def enter_limit_range(
        self, token_id: str,
        amount: float,
        min_price: float = 0.705,
        max_price: float = 0.72,
        wait_seconds: float = 1.0,
        )-> Tuple[bool, float]:
        """
        在区间内挂一个限价 BUY，不成交就撤，不追价


        Args:
        token_id: token id
        amount: 购买份额
        min_price: 区间下沿（默认 0.605）
        max_price: 区间上沿（默认 0.62）
        wait_seconds: 等待成交时间（秒）


        Returns:
        (是否成交, 实际成交份额)
        """
        try:
            # 🎯 选择一个中间价作为埋伏价（可微调）
            limit_price = round((min_price + max_price) / 2, 3)

            self.log(f"🧲 LIMIT埋伏: token_id={token_id}, price={limit_price}, amount={amount}")

            order_args = OrderArgs(
                token_id=token_id,
                price=limit_price,
                size=amount,
                side="BUY",
                )

            signed = self.clob_client.create_order(order_args)
            result = self.clob_client.post_order(signed, orderType=OrderType.GTC)


            if not result or not result.get("orderID"):
                self.log(f"❌ LIMIT单创建失败: {result}")
                return False, 0.0


            order_id = result["orderID"]
            self.log(f"📌 LIMIT单已挂出: {order_id} @ {limit_price}")


            # ⏳ 等待成交
            await asyncio.sleep(wait_seconds)

            # 🔍 查询订单状态
            order_info = self.clob_client.get_order(order_id)

            if order_info and order_info.get("status") == "FILLED":
                filled = float(order_info.get("filledAmount", amount))
                self.log(f"✅ LIMIT成交: {filled} @ {limit_price}")
                return True, filled

            # 🚫 未成交 → 撤单
            self.log(f"⏹ 未成交，撤单: {order_id}")
            self.clob_client.cancel_order(order_id)

            return False, 0.0
        except Exception as e:
            self.log(f"❌ LIMIT入场异常: {e}")
            return False, 0.0