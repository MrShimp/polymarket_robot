import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com", save_data: bool = True):
        self.base_url = base_url
        self.save_data = save_data
    
    def _save_to_csv(self, data: List[Dict], filename: str):
        """简单的CSV保存功能"""
        if not data or not self.save_data:
            return
        
        try:
            os.makedirs("data/api_cache", exist_ok=True)
            filepath = f"data/api_cache/{filename}"
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        except Exception as e:
            logger.warning(f"Failed to save data to {filename}: {e}")
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://polymarket.com/'
        })
    
    def get_market(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定市场信息
        
        Args:
            condition_id: 市场条件ID
            
        Returns:
            市场数据字典或None
        """
        try:
            url = f"{self.base_url}/markets/{condition_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            market_data = response.json()
            logger.info(f"成功获取市场 {condition_id} 的数据")
            
            # 保存数据到CSV
            if self.save_data and market_data:
                self._save_to_csv([market_data], f"market_{market_id}.csv")
            
            return market_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场数据失败: {e}")
            return None
    
    def get_markets(self, 
                   limit: int = 100, 
                   offset: int = 0,
                   active: Optional[bool] = None,
                   closed: Optional[bool] = None,
                   tag: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        获取市场列表
        
        Args:
            limit: 返回结果数量限制
            offset: 偏移量
            active: 是否只返回活跃市场
            closed: 是否只返回已关闭市场
            tag: 按标签筛选
            
        Returns:
            市场列表或None
        """
        try:
            url = f"{self.base_url}/markets"
            params = {
                'limit': limit,
                'offset': offset
            }
            
            if active is not None:
                params['active'] = str(active).lower()
            if closed is not None:
                params['closed'] = str(closed).lower()
            if tag:
                params['tag'] = tag
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            markets_data = response.json()
            logger.info(f"成功获取 {len(markets_data)} 个市场数据")
            
            # 保存数据到CSV
            if self.save_data and markets_data:
                self._save_to_csv(markets_data, "markets_list.csv")
            
            return markets_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场列表失败: {e}")
            return None
    
    def get_orderbook(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单簿数据
        
        Args:
            token_id: 代币ID
            
        Returns:
            订单簿数据或None
        """
        try:
            url = f"{self.base_url}/book"
            params = {'token_id': token_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            orderbook_data = response.json()
            logger.info(f"成功获取代币 {token_id} 的订单簿数据")
            
            # 保存数据到CSV
            if self.save_data and orderbook_data:
                self._save_to_csv([orderbook_data], f"orderbook_{token_id}.csv")
            
            return orderbook_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取订单簿失败: {e}")
            return None
    
    def get_trades(self, 
                  market: Optional[str] = None,
                  maker: Optional[str] = None,
                  taker: Optional[str] = None,
                  limit: int = 100,
                  offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """
        获取交易历史
        
        Args:
            market: 市场ID
            maker: 做市商地址
            taker: 接受者地址
            limit: 返回结果数量限制
            offset: 偏移量
            
        Returns:
            交易历史列表或None
        """
        try:
            url = f"{self.base_url}/trades"
            params = {
                'limit': limit,
                'offset': offset
            }
            
            if market:
                params['market'] = market
            if maker:
                params['maker'] = maker
            if taker:
                params['taker'] = taker
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            trades_data = response.json()
            logger.info(f"成功获取 {len(trades_data)} 条交易记录")
            
            # 保存数据到CSV
            if self.save_data and trades_data:
                self._save_to_csv(trades_data, "trades_list.csv")
            
            return trades_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取交易历史失败: {e}")
            return None
    
    def get_market_prices(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        获取市场价格信息
        
        Args:
            condition_id: 市场条件ID
            
        Returns:
            价格信息或None
        """
        try:
            url = f"{self.base_url}/prices"
            params = {'market': condition_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            prices_data = response.json()
            logger.info(f"成功获取市场 {condition_id} 的价格信息")
            
            # 保存数据到CSV
            if self.save_data and prices_data:
                self._save_to_csv([prices_data], f"prices_{condition_id}.csv")
            
            return prices_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取价格信息失败: {e}")
            return None