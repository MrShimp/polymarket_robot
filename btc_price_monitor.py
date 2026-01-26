#!/usr/bin/env python3
"""
BTC价格监控器 - 使用Chainlink Data Streams API
每15分钟获取一次BTC价格并记录到文件
"""

import asyncio
import websockets
import json
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import schedule
import time
import threading

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BTCPriceMonitor:
    """BTC价格监控器"""
    
    def __init__(self, data_dir: str = "./data/btc"):
        self.data_dir = data_dir
        self.ws_url = "wss://ws.linkpool.io/ws"  # Chainlink Data Streams WebSocket
        self.btc_feed_id = "0x0000000000000000000000000000000000000000000000000000000000000000"  # BTC/USD feed ID
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 价格数据存储
        self.latest_price = None
        self.price_history = []
        
        # WebSocket连接
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # 调度器
        self.scheduler_running = False
        
        # 初始化CSV文件
        self.init_csv_files()
    
    def init_csv_files(self):
        """初始化CSV文件"""
        # 每日价格文件
        today = datetime.now().strftime("%Y%m%d")
        self.daily_file = os.path.join(self.data_dir, f"btc_prices_{today}.csv")
        
        # 15分钟价格文件
        self.interval_file = os.path.join(self.data_dir, "btc_15min_prices.csv")
        
        # 创建CSV文件头部（如果文件不存在）
        headers = ['timestamp', 'datetime', 'price', 'source', 'feed_id']
        
        for file_path in [self.daily_file, self.interval_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                logger.info(f"创建价格文件: {file_path}")
    
    async def connect_websocket(self):
        """连接WebSocket"""
        try:
            logger.info(f"连接Chainlink Data Streams WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("✅ WebSocket连接成功")
            
            # 订阅BTC价格数据
            await self.subscribe_btc_price()
            
            # 开始监听消息
            await self.listen_messages()
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            await self.handle_reconnect()
    
    async def subscribe_btc_price(self):
        """订阅BTC价格数据"""
        try:
            # Chainlink Data Streams订阅消息格式
            subscribe_message = {
                "method": "subscribe",
                "params": {
                    "feeds": [self.btc_feed_id],
                    "full_report": True
                },
                "id": 1
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info("📡 已订阅BTC价格数据流")
            
        except Exception as e:
            logger.error(f"订阅BTC价格失败: {e}")
    
    async def listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.process_price_data(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            self.is_connected = False
            await self.handle_reconnect()
        except Exception as e:
            logger.error(f"监听消息失败: {e}")
            self.is_connected = False
            await self.handle_reconnect()
    
    async def process_price_data(self, data: Dict):
        """处理价格数据"""
        try:
            # 解析Chainlink Data Streams响应格式
            if 'result' in data and 'reports' in data['result']:
                reports = data['result']['reports']
                
                for report in reports:
                    if 'feedId' in report and report['feedId'] == self.btc_feed_id:
                        # 提取价格信息
                        price = self.extract_price_from_report(report)
                        
                        if price:
                            self.latest_price = price
                            timestamp = datetime.now()
                            
                            logger.info(f"📈 BTC价格更新: ${price:,.2f}")
                            
                            # 添加到历史记录
                            self.price_history.append({
                                'timestamp': timestamp.timestamp(),
                                'datetime': timestamp.isoformat(),
                                'price': price,
                                'source': 'chainlink',
                                'feed_id': self.btc_feed_id
                            })
                            
                            # 保持历史记录在合理范围内
                            if len(self.price_history) > 1000:
                                self.price_history = self.price_history[-500:]
            
        except Exception as e:
            logger.error(f"处理价格数据失败: {e}")
    
    def extract_price_from_report(self, report: Dict) -> Optional[float]:
        """从Chainlink报告中提取价格"""
        try:
            # Chainlink Data Streams报告格式
            if 'price' in report:
                # 价格通常以整数形式提供，需要除以精度
                price_raw = int(report['price'])
                decimals = report.get('decimals', 8)  # 默认8位小数
                price = price_raw / (10 ** decimals)
                return price
            
            # 备用解析方法
            if 'observationsTimestamp' in report and 'median' in report:
                median = int(report['median'])
                decimals = report.get('decimals', 8)
                price = median / (10 ** decimals)
                return price
                
        except Exception as e:
            logger.error(f"提取价格失败: {e}")
        
        return None
    
    async def handle_reconnect(self):
        """处理重连"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"达到最大重连次数 ({self.max_reconnect_attempts})，停止重连")
            return
        
        self.reconnect_attempts += 1
        wait_time = min(2 ** self.reconnect_attempts, 60)  # 指数退避，最大60秒
        
        logger.info(f"等待 {wait_time} 秒后重连 (第 {self.reconnect_attempts} 次)")
        await asyncio.sleep(wait_time)
        
        await self.connect_websocket()
    
    def record_15min_price(self):
        """记录15分钟价格"""
        try:
            if not self.latest_price:
                logger.warning("没有最新价格数据，跳过记录")
                return
            
            timestamp = datetime.now()
            
            # 检查是否是15分钟整点
            if timestamp.minute % 15 != 0:
                # 调整到最近的15分钟整点
                minutes_to_next = 15 - (timestamp.minute % 15)
                timestamp = timestamp.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_next)
            
            price_record = {
                'timestamp': timestamp.timestamp(),
                'datetime': timestamp.isoformat(),
                'price': self.latest_price,
                'source': 'chainlink_15min',
                'feed_id': self.btc_feed_id
            }
            
            # 保存到15分钟文件
            self.save_price_record(price_record, self.interval_file)
            
            # 保存到每日文件
            self.save_price_record(price_record, self.daily_file)
            
            logger.info(f"✅ 记录15分钟价格: ${self.latest_price:,.2f} at {timestamp.strftime('%H:%M')}")
            
        except Exception as e:
            logger.error(f"记录15分钟价格失败: {e}")
    
    def save_price_record(self, record: Dict, file_path: str):
        """保存价格记录到CSV文件"""
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    record['timestamp'],
                    record['datetime'],
                    record['price'],
                    record['source'],
                    record['feed_id']
                ])
        except Exception as e:
            logger.error(f"保存价格记录失败: {e}")
    
    def setup_scheduler(self):
        """设置定时任务"""
        # 每15分钟的整点执行
        schedule.every().hour.at(":00").do(self.record_15min_price)
        schedule.every().hour.at(":15").do(self.record_15min_price)
        schedule.every().hour.at(":30").do(self.record_15min_price)
        schedule.every().hour.at(":45").do(self.record_15min_price)
        
        logger.info("⏰ 定时任务已设置: 每15分钟记录一次价格")
    
    def run_scheduler(self):
        """运行调度器"""
        self.scheduler_running = True
        logger.info("🚀 启动价格记录调度器")
        
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(1)
    
    def start_monitoring(self):
        """开始监控"""
        logger.info("🚀 启动BTC价格监控器")
        
        # 设置定时任务
        self.setup_scheduler()
        
        # 在单独线程中运行调度器
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # 运行WebSocket连接
        try:
            asyncio.run(self.connect_websocket())
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """停止监控"""
        logger.info("🛑 停止BTC价格监控器")
        self.scheduler_running = False
        self.is_connected = False
        
        if self.websocket:
            asyncio.create_task(self.websocket.close())
    
    def get_latest_price(self) -> Optional[float]:
        """获取最新价格"""
        return self.latest_price
    
    def get_price_history(self, limit: int = 100) -> List[Dict]:
        """获取价格历史"""
        return self.price_history[-limit:] if self.price_history else []
    
    def generate_daily_report(self):
        """生成每日价格报告"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            report_file = os.path.join(self.data_dir, f"btc_report_{today}.json")
            
            # 读取今日价格数据
            daily_prices = []
            if os.path.exists(self.daily_file):
                with open(self.daily_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    daily_prices = list(reader)
            
            if not daily_prices:
                logger.warning("没有今日价格数据")
                return
            
            # 计算统计信息
            prices = [float(record['price']) for record in daily_prices]
            
            report = {
                'date': today,
                'total_records': len(prices),
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': sum(prices) / len(prices),
                'first_price': prices[0],
                'last_price': prices[-1],
                'price_change': prices[-1] - prices[0],
                'price_change_pct': ((prices[-1] - prices[0]) / prices[0]) * 100,
                'generated_at': datetime.now().isoformat()
            }
            
            # 保存报告
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 每日报告已生成: {report_file}")
            logger.info(f"   价格范围: ${report['min_price']:,.2f} - ${report['max_price']:,.2f}")
            logger.info(f"   价格变化: {report['price_change_pct']:+.2f}%")
            
        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BTC价格监控器 - Chainlink Data Streams")
    parser.add_argument("--data-dir", default="./data/btc", help="数据存储目录")
    parser.add_argument("--test", action="store_true", help="测试模式，立即记录一次价格")
    parser.add_argument("--report", action="store_true", help="生成今日价格报告")
    
    args = parser.parse_args()
    
    monitor = BTCPriceMonitor(data_dir=args.data_dir)
    
    if args.test:
        # 测试模式
        logger.info("🧪 测试模式")
        monitor.latest_price = 95000.00  # 模拟价格
        monitor.record_15min_price()
        
    elif args.report:
        # 生成报告
        monitor.generate_daily_report()
        
    else:
        # 正常监控模式
        try:
            monitor.start_monitoring()
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            monitor.stop_monitoring()


if __name__ == "__main__":
    main()