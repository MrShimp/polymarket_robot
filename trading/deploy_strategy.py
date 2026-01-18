#!/usr/bin/env python3
"""
高频策略部署脚本
High-Frequency Strategy Deployment Script
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyDeployer:
    """策略部署器"""
    
    def __init__(self):
        self.required_files = [
            'high_frequency_strategy.py',
            'polymarket_clob_client.py',
            'risk_manager.py',
            'strategy_monitor.py',
            'backtest_engine.py',
            'data_saver.py',
            'hf_config.json'
        ]
        
        self.required_packages = [
            'requests>=2.28.0',
            'pandas>=1.5.0',
            'numpy>=1.21.0',
            'python-dotenv>=1.0.0',
            'asyncio',
            'matplotlib>=3.5.0',
            'seaborn>=0.11.0'
        ]
    
    def check_environment(self) -> bool:
        """检查环境配置"""
        logger.info("检查环境配置...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            logger.error("需要Python 3.8或更高版本")
            return False
        
        # 检查必需文件
        missing_files = []
        for file in self.required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"缺少必需文件: {missing_files}")
            return False
        
        # 检查环境变量
        required_env_vars = ['POLYMARKET_API_KEY', 'POLYMARKET_API_SECRET', 'POLYMARKET_PASSPHRASE']
        missing_env_vars = []
        
        for var in required_env_vars:
            if not os.getenv(var):
                missing_env_vars.append(var)
        
        if missing_env_vars:
            logger.warning(f"缺少环境变量: {missing_env_vars}")
            logger.warning("策略将在模拟模式下运行")
        
        logger.info("环境检查完成")
        return True
    
    def install_dependencies(self) -> bool:
        """安装依赖包"""
        logger.info("安装依赖包...")
        
        try:
            for package in self.required_packages:
                logger.info(f"安装 {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            
            logger.info("依赖包安装完成")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"安装依赖包失败: {e}")
            return False
    
    def create_directories(self):
        """创建必要的目录"""
        directories = ['./hf_data', './logs', './backups']
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"创建目录: {directory}")
    
    def setup_logging(self):
        """设置日志配置"""
        log_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': './logs/strategy.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'formatter': 'detailed'
                },
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed'
                }
            },
            'root': {
                'level': 'INFO',
                'handlers': ['file', 'console']
            }
        }
        
        with open('./logs/logging_config.json', 'w') as f:
            json.dump(log_config, f, indent=2)
        
        logger.info("日志配置已创建")
    
    def create_systemd_service(self):
        """创建systemd服务文件 (Linux)"""
        if os.name != 'posix':
            logger.info("非Linux系统，跳过systemd服务创建")
            return
        
        service_content = f"""[Unit]
Description=High Frequency Trading Strategy
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={os.getcwd()}
Environment=PATH={os.environ.get('PATH')}
Environment=POLYMARKET_API_KEY={os.getenv('POLYMARKET_API_KEY', '')}
Environment=POLYMARKET_API_SECRET={os.getenv('POLYMARKET_API_SECRET', '')}
Environment=POLYMARKET_PASSPHRASE={os.getenv('POLYMARKET_PASSPHRASE', '')}
ExecStart={sys.executable} high_frequency_strategy.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = 'hf-strategy.service'
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        logger.info(f"systemd服务文件已创建: {service_file}")
        logger.info("要安装服务，请运行:")
        logger.info(f"sudo cp {service_file} /etc/systemd/system/")
        logger.info("sudo systemctl daemon-reload")
        logger.info("sudo systemctl enable hf-strategy")
        logger.info("sudo systemctl start hf-strategy")
    
    def create_startup_script(self):
        """创建启动脚本"""
        startup_script = """#!/bin/bash

# 高频策略启动脚本
echo "启动高频交易策略..."

# 检查环境变量
if [ -z "$POLYMARKET_API_KEY" ]; then
    echo "警告: POLYMARKET_API_KEY 未设置"
fi

if [ -z "$POLYMARKET_API_SECRET" ]; then
    echo "警告: POLYMARKET_API_SECRET 未设置"
fi

if [ -z "$POLYMARKET_PASSPHRASE" ]; then
    echo "警告: POLYMARKET_PASSPHRASE 未设置"
fi

# 创建必要目录
mkdir -p ./hf_data ./logs ./backups

# 启动策略
python3 high_frequency_strategy.py

echo "策略已停止"
"""
        
        with open('start_strategy.sh', 'w') as f:
            f.write(startup_script)
        
        # 设置执行权限
        os.chmod('start_strategy.sh', 0o755)
        
        logger.info("启动脚本已创建: start_strategy.sh")
    
    def create_monitoring_script(self):
        """创建监控脚本"""
        monitoring_script = """#!/bin/bash

# 策略监控脚本
echo "启动策略监控..."

# 实时监控
python3 strategy_monitor.py --mode monitor --interval 30

echo "监控已停止"
"""
        
        with open('monitor_strategy.sh', 'w') as f:
            f.write(monitoring_script)
        
        os.chmod('monitor_strategy.sh', 0o755)
        
        logger.info("监控脚本已创建: monitor_strategy.sh")
    
    def run_backtest(self):
        """运行回测"""
        logger.info("运行策略回测...")
        
        try:
            subprocess.check_call([sys.executable, 'backtest_engine.py'])
            logger.info("回测完成")
        except subprocess.CalledProcessError as e:
            logger.error(f"回测失败: {e}")
    
    def create_config_template(self):
        """创建配置模板"""
        config_template = {
            "strategy_name": "High-Frequency Near-Certainty Strategy",
            "version": "1.0.0",
            "description": "专门针对90¢-99¢近乎确定性合约的高频微型仓位策略",
            
            "trading_parameters": {
                "min_price": 0.90,
                "max_price": 0.99,
                "min_confidence": 0.95,
                "position_size": 1,
                "max_positions": 100,
                "target_profit_pct": 0.02,
                "stop_loss_pct": 0.05
            },
            
            "frequency_control": {
                "scan_interval": 3,
                "max_daily_trades": 27000,
                "trades_per_minute": 30
            },
            
            "risk_management": {
                "max_daily_loss": 500,
                "max_consecutive_losses": 10,
                "max_position_loss": 10,
                "min_volume": 1000,
                "max_spread": 0.05
            },
            
            "market_filters": {
                "exclude_keywords": ["test", "demo", "practice", "simulation"],
                "min_market_age_hours": 1,
                "max_time_to_expiry_hours": 168
            },
            
            "trading_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC",
                "trading_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            
            "notifications": {
                "email_alerts": False,
                "slack_webhook": "",
                "discord_webhook": "",
                "alert_on_loss_threshold": 100,
                "alert_on_profit_threshold": 1000
            }
        }
        
        with open('config_template.json', 'w') as f:
            json.dump(config_template, f, indent=2)
        
        logger.info("配置模板已创建: config_template.json")
    
    def deploy(self):
        """执行完整部署"""
        logger.info("开始部署高频交易策略...")
        
        # 检查环境
        if not self.check_environment():
            logger.error("环境检查失败，部署中止")
            return False
        
        # 安装依赖
        if not self.install_dependencies():
            logger.error("依赖安装失败，部署中止")
            return False
        
        # 创建目录
        self.create_directories()
        
        # 设置日志
        self.setup_logging()
        
        # 创建脚本
        self.create_startup_script()
        self.create_monitoring_script()
        self.create_systemd_service()
        
        # 创建配置模板
        self.create_config_template()
        
        # 运行回测
        self.run_backtest()
        
        logger.info("部署完成！")
        
        # 显示使用说明
        self.show_usage_instructions()
        
        return True
    
    def show_usage_instructions(self):
        """显示使用说明"""
        instructions = """
╔══════════════════════════════════════════════════════════════╗
║                    部署完成 - 使用说明                       ║
╠══════════════════════════════════════════════════════════════╣
║ 🚀 启动策略:                                                 ║
║   ./start_strategy.sh                                        ║
║   或                                                         ║
║   python3 high_frequency_strategy.py                        ║
║                                                              ║
║ 📊 监控策略:                                                 ║
║   ./monitor_strategy.sh                                      ║
║   或                                                         ║
║   python3 strategy_monitor.py --mode monitor                ║
║                                                              ║
║ 📈 查看报告:                                                 ║
║   python3 strategy_monitor.py --mode report                 ║
║                                                              ║
║ 🔄 运行回测:                                                 ║
║   python3 backtest_engine.py                                ║
║                                                              ║
║ ⚙️  配置文件:                                                 ║
║   hf_config.json - 策略参数配置                             ║
║   config_template.json - 完整配置模板                       ║
║                                                              ║
║ 📁 重要目录:                                                 ║
║   ./hf_data/ - 交易数据和统计                               ║
║   ./logs/ - 日志文件                                        ║
║   ./backups/ - 备份文件                                     ║
║                                                              ║
║ 🔐 环境变量 (生产环境必需):                                  ║
║   POLYMARKET_API_KEY                                         ║
║   POLYMARKET_API_SECRET                                      ║
║   POLYMARKET_PASSPHRASE                                      ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        print(instructions)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='高频策略部署工具')
    parser.add_argument('--action', choices=['deploy', 'check', 'install-deps'], 
                       default='deploy', help='执行的操作')
    
    args = parser.parse_args()
    
    deployer = StrategyDeployer()
    
    if args.action == 'deploy':
        deployer.deploy()
    elif args.action == 'check':
        deployer.check_environment()
    elif args.action == 'install-deps':
        deployer.install_dependencies()

if __name__ == "__main__":
    main()