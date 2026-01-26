from btc_15min_strategy import BTC15MinStrategy
from trading.polymarket_clob_client import PolymarketCLOBClient
from py_clob_client.clob_types import OrderArgs, OrderType, MarketOrderArgs, BalanceAllowanceParams,AssetType


client = ClobClient(
                        host="https://clob.polymarket.com",
                        key="",
                        chain_id=137,)
api_creds = client.create_or_derive_api_creds()
print(api_creds)
