from py_clob_client.client import ClobClient

# 填入你的私钥
client = ClobClient(host="https://clob.polymarket.com", key="YOUR_PRIVATE_KEY", chain_id=137)

# 创建或获取现有的 API Key
creds = client.create_or_derive_api_key()
print(creds)