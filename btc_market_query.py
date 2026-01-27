#!/usr/bin/env python3
"""
BTC市场查询工具
查找可用的BTC 15分钟市场信息
"""

import requests
import json
import datetime
import pytz
import sys

def get_next_15min_et_timestamp():
    """
    获取当前北京时间下一个15分钟整点对应的美东冬季时间（UTC-5）的Unix时间戳
    返回：timestamp（整数，秒级）、北京时间字符串、美东时间字符串
    """
    # 1. 定义时区：北京时间(UTC+8)、美东冬季时间(UTC-5，固定，不切换夏令时)
    tz_beijing = pytz.timezone('Asia/Shanghai')
    tz_et_winter = pytz.FixedOffset(-5 * 60)  # UTC-5，美东冬季
    
    # 2. 获取当前北京时间（带时区）
    now_beijing = datetime.datetime.now(tz_beijing)
    
    # 3. 计算下一个15分钟整点的北京时间
    # 计算当前分钟数离最近的15分整点的差值（向上取整）
    minutes = now_beijing.minute
    remainder = minutes % 15
    if remainder == 0:
        # 刚好是15分整点，取当前整点（或下一个，可根据需求调整）
        next_15min_beijing = now_beijing
    else:
        # 计算需要加的分钟数，凑到下一个15分
        add_minutes = 15 - remainder
        next_15min_beijing = now_beijing + datetime.timedelta(minutes=add_minutes)
    
    # 4. 重置秒和微秒为0（确保是整点）
    next_15min_beijing = next_15min_beijing.replace(second=0, microsecond=0)
    
    # 5. 将北京时间转换为美东冬季时间
    next_15min_et = next_15min_beijing.astimezone(tz_et_winter)
    
    # 6. 计算美东时间的Unix时间戳（秒级）
    et_timestamp = int(next_15min_et.timestamp())
    
    # 格式化时间字符串（便于查看）
    beijing_str = next_15min_beijing.strftime('%Y-%m-%d %H:%M:%S %Z%z')
    et_str = next_15min_et.strftime('%Y-%m-%d %H:%M:%S %Z%z')
    
    return et_timestamp, beijing_str, et_str

def get_btc_15m_markets_cleaned(silent=False):
    GAMMA_BASE = "https://gamma-api.polymarket.com"
    
    if not silent:
        print(f"[*] 正在扫描BTC 15分钟市场...")

    all_active_markets = []
    timestamp, beijing_time, et_time = get_next_15min_et_timestamp()
    
    if not silent:
        print(f"[*] 目标时间戳: {timestamp}")
        print(f"[*] 北京时间: {beijing_time}")
        print(f"[*] 美东时间: {et_time}")
    
    try:
        url = f"{GAMMA_BASE}/markets/slug/btc-updown-15m-{timestamp}"
        if not silent:
            print(f"[*] 请求URL: {url}")
        response = requests.get(url, timeout=30)
        
        if not silent:
            print(f"[*] 响应状态码: {response.status_code}")
        
        if response.status_code == 404:
            if not silent:
                print(f"[!] 未找到对应时间戳的市场")
            return []
        
        response.raise_for_status()
        
        # 检查响应内容
        try:
            data = response.json()
            if not silent:
                print(f"[*] 响应数据类型: {type(data)}")
            
            # 如果返回的是单个市场对象而不是列表
            if isinstance(data, dict):
                if not silent:
                    print(f"[*] 响应是单个市场对象")
                markets = [data]  # 包装成列表
            elif isinstance(data, list):
                if not silent:
                    print(f"[*] 响应是市场列表")
                markets = data
            else:
                if not silent:
                    print(f"[!] 未知的响应格式: {type(data)}")
                    print(f"[*] 响应内容: {str(data)[:200]}...")
                return []
                
        except json.JSONDecodeError as e:
            if not silent:
                print(f"[!] JSON解析失败: {e}")
                print(f"[*] 原始响应: {response.text[:500]}...")
            return []
        
        if not silent:
            print(f"[*] 找到 {len(markets)} 个市场")
        
        for market in markets:
            if not isinstance(market, dict):
                if not silent:
                    print(f"[!] 市场项不是字典格式: {type(market)}")
                continue
                
            m_id = market.get('id', '')
            question = market.get('question', '').strip()
            
            if not silent:
                print(f"[*] 处理市场: {question}")
            
            # 获取token IDs
            clob_token_ids = market.get('clobTokenIds', '[]')
            try:
                if isinstance(clob_token_ids, str):
                    token_ids = json.loads(clob_token_ids)
                elif isinstance(clob_token_ids, list):
                    token_ids = clob_token_ids
                else:
                    if not silent:
                        print(f"[!] 未知的token IDs格式: {type(clob_token_ids)}")
                    continue
            except (json.JSONDecodeError, TypeError) as e:
                if not silent:
                    print(f"[!] 无法解析token IDs: {clob_token_ids}, 错误: {e}")
                continue
            
            if not silent:
                print(f"[*] Token IDs: {token_ids}")
            
            if (market.get('closed') is False and 
                isinstance(token_ids, list) and 
                len(token_ids) >= 2):
                
                all_active_markets.append({
                    "question": question,
                    "ends_at": market.get('endDate', ''),
                    "market_id": m_id,
                    "yes_token": token_ids[0],
                    "no_token": token_ids[1],
                    "accepting_order": market.get('acceptingOrders', True)
                })
                if not silent:
                    print(f"[+] 添加市场: {m_id}")
            else:
                if not silent:
                    print(f"[!] 跳过市场: closed={market.get('closed')}, token_count={len(token_ids) if isinstance(token_ids, list) else 0}")
                
    except requests.RequestException as e:
        if not silent:
            print(f"[!] 网络请求失败: {e}")
        return []
    except Exception as e:
        if not silent:
            print(f"[!] 获取市场数据失败: {e}")
            print(f"[!] 错误类型: {type(e)}")
            import traceback
            traceback.print_exc()
        return []
        
    return sorted(all_active_markets, key=lambda x: x.get('ends_at', '')) # 按结束时间排序

def main():
    """主函数"""
    import sys  # 确保sys模块可用
    
    try:
        # 检查是否需要JSON输出
        json_output = len(sys.argv) > 1 and sys.argv[1] == "--json"
        
        # 执行并打印
        markets = get_btc_15m_markets_cleaned(silent=json_output)
        
        if json_output:
            # 输出JSON格式供其他脚本使用
            print(json.dumps(markets, indent=2, ensure_ascii=False))
        else:
            # 人类可读格式
            print(f"\n[+] 过滤后发现 {len(markets)} 个唯一的 BTC-15m 市场：")
            
            if not markets:
                print("[!] 没有找到符合条件的市场")
                return
            
            for i, m in enumerate(markets, 1):
                print(f"--- 市场 {i} ---")
                print(f"时间段: {m['question']}")
                print(f"Market ID: {m['market_id']}")
                print(f"YES Token: {m['yes_token']}")
                print(f"NO Token: {m['no_token']}")
                print(f"结束时间: {m['ends_at']}")
                print(f"接受订单: {m['accepting_order']}")
                print()
            
    except Exception as e:
        # 确保在异常处理中也能访问sys
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--json":
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"[!] 程序执行失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()