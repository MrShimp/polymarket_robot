from btc_15min_strategy import BTC15MinStrategy
from trading.polymarket_clob_client import PolymarketCLOBClient
from py_clob_client.clob_types import OrderArgs, OrderType, MarketOrderArgs

client = PolymarketCLOBClient()
order_args = MarketOrderArgs(
    token_id="5548733376589342349503466530474997339123140755981908659223626897731311602926",
    amount=1,
    side="BUY",
)

signed_order = client.clob_client.create_market_order(order_args)
result = client.clob_client.post_order(signed_order, orderType=OrderType.FOK)
print(result)
