#!/usr/bin/env python3
"""
Polymarket 卖出策略模块
从 btc_15min_strategy.py 中提取的出场操作功能
"""
import asyncio
from typing import Tuple, Optional
from py_clob_client.clob_types import (
    MarketOrderArgs,
    OrderType,
    BalanceAllowanceParams,
    AssetType,
)


class SellStrategy:
    """卖出策略类"""

    def __init__(self, clob_client, logger=None):
        """
        初始化卖出策略

        Args:
            clob_client: Polymarket CLOB客户端
            logger: 日志记录器函数，如果为None则使用print
        """
        self.clob_client = clob_client
        self.log = logger if logger else print

    async def exit_position(self, token_id: str, amount: float) -> bool:
        """
        出场操作 - 持续重试直到成功

        Args:
            token_id: 代币ID
            amount: 预期卖出金额（实际会查询真实持仓）

        Returns:
            bool: 是否成功出场
        """
        max_retries = 10  # 最大重试次数，防止无限循环
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 获取实际持仓
                actual_balance = self.clob_client.get_balance_allowance(
                    params=BalanceAllowanceParams(
                        asset_type=AssetType.CONDITIONAL,
                        token_id=token_id,
                    )
                )

                # 确保余额是数字类型
                balance_value = actual_balance.get("balance", "0")
                if isinstance(balance_value, str):
                    balance_value = float(balance_value)
                balance_value = balance_value / 1000000

                # 如果没有持仓，直接返回成功
                if balance_value <= 0:
                    self.log("✅ 没有持仓，出场完成")
                    return True

                retry_count += 1
                self.log(
                    f"🎯 出场尝试 #{retry_count}: token_id={token_id}, 持仓={balance_value}份"
                )

                # 创建市场卖出订单
                order_args = MarketOrderArgs(
                    token_id=token_id,
                    amount=balance_value,
                    side="SELL",
                )
                signed_order = self.clob_client.create_market_order(order_args)
                result = self.clob_client.post_order(
                    signed_order, orderType=OrderType.FOK
                )

                if result and result.get("orderID"):
                    self.log(
                        f"✅ 出场成功 (第{retry_count}次尝试): {result.get('orderID')}"
                    )
                    self.log(f"📋 成功卖出: {balance_value}份")
                    return True
                else:
                    error_msg = str(result) if result else "无响应"
                    self.log(f"⚠️ 出场失败 (第{retry_count}次): {error_msg}")

                    # 等待1秒后重试
                    await asyncio.sleep(1)

            except Exception as e:
                error_msg = str(e)
                self.log(f"⚠️ 出场异常 (第{retry_count}次): {error_msg}")

                # 等待1秒后重试
                await asyncio.sleep(1)

        # 如果达到最大重试次数仍未成功
        self.log(f"❌ 出场失败: 已重试{max_retries}次，放弃操作")
        return False

    async def get_position_balance(self, token_id: str) -> Optional[float]:
        """
        获取指定代币的持仓余额

        Args:
            token_id: 代币ID

        Returns:
            Optional[float]: 持仓余额，获取失败返回None
        """
        try:
            actual_balance = self.clob_client.get_balance_allowance(
                params=BalanceAllowanceParams(
                    asset_type=AssetType.CONDITIONAL,
                    token_id=token_id,
                )
            )

            balance_value = actual_balance.get("balance", "0")
            if isinstance(balance_value, str):
                balance_value = float(balance_value)

            # 转换为实际余额（除以1000000）
            balance_value = balance_value / 1000000

            self.log(f"📊 持仓查询: token_id={token_id}, 余额={balance_value}份")
            return balance_value

        except Exception as e:
            self.log(f"❌ 获取持仓余额失败: {e}")
            return None

    async def create_sell_order(
        self, token_id: str, amount: float, side: str = "SELL"
    ) -> Tuple[bool, dict]:
        """
        创建卖出订单的通用方法

        Args:
            token_id: 代币ID
            amount: 交易金额
            side: 交易方向，默认为"SELL"

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

    async def exit_position_with_retry(
        self, token_id: str, max_retries: int = 5, retry_delay: float = 1.0
    ) -> bool:
        """
        带自定义重试参数的出场操作

        Args:
            token_id: 代币ID
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            bool: 是否成功出场
        """
        retry_count = 0
        total_sell_attempts = 0  # 总卖出尝试次数

        while retry_count < max_retries:
            try:
                # 获取当前持仓
                balance = await self.get_position_balance(token_id)
                if balance is None:
                    self.log("❌ 无法获取持仓信息")
                    return False

                if balance <= 0:
                    self.log("✅ 没有持仓，出场完成")
                    return True

                retry_count += 1
                self.log(f"🎯 出场尝试 #{retry_count}/{max_retries}: 持仓={balance}份")

                # 创建卖出订单
                success, result = await self.create_sell_order(token_id, balance)
                total_sell_attempts += 1

                if success:
                    self.log(f"✅ 卖出订单成功 (第{retry_count}次尝试)")

                    # 等待订单执行
                    await asyncio.sleep(0.5)

                    # 再次获取余额检查是否完全卖出
                    remaining_balance = await self.get_position_balance(token_id)
                    if remaining_balance is None:
                        self.log("⚠️ 无法获取剩余持仓，假设出场成功")
                        return True

                    # 检查剩余余额是否小于0.01 (除以1000000后)
                    remaining_after_conversion = remaining_balance / 1000000
                    self.log(
                        f"📊 卖出后剩余持仓: {remaining_balance}份 (转换后: {remaining_after_conversion:.6f})"
                    )

                    if remaining_after_conversion < 0.01:
                        self.log(
                            f"✅ 出场完成: 剩余持仓 {remaining_after_conversion:.6f} < 0.01"
                        )
                        return True
                    else:
                        self.log(
                            f"⚠️ 仍有剩余持仓 {remaining_after_conversion:.6f} >= 0.01，继续卖出"
                        )
                        # 重置retry_count，继续尝试卖出剩余部分
                        retry_count = 0
                        continue
                else:
                    self.log(f"⚠️ 出场失败 (第{retry_count}次): {result}")

                # 等待后重试
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)

            except Exception as e:
                self.log(f"⚠️ 出场异常 (第{retry_count}次): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)

        self.log(
            f"❌ 出场失败: 已重试{max_retries}次，总共尝试卖出{total_sell_attempts}次，放弃操作"
        )
        return False

    def validate_sell_parameters(
        self, token_id: str, amount: float = None
    ) -> Tuple[bool, str]:
        """
        验证卖出参数

        Args:
            token_id: 代币ID
            amount: 交易金额（可选）

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not token_id or not isinstance(token_id, str):
            return False, "token_id 必须是非空字符串"

        if amount is not None and (not isinstance(amount, (int, float)) or amount <= 0):
            return False, "amount 必须是大于0的数字"

        return True, "参数验证通过"
