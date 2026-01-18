#!/usr/bin/env python3
"""
测试API端点格式
Test the exact API endpoint format provided
"""

import requests
import json

def test_exact_endpoint():
    """测试确切的API端点"""
    
    # 你提供的确切端点
    url = "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=5"
    
    print(f"🔍 测试API端点: {url}")
    
    try:
        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://polymarket.com/"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ 成功获取JSON数据")
                print(f"📄 数据类型: {type(data)}")
                
                if isinstance(data, list):
                    print(f"📊 数据数量: {len(data)}")
                    if data:
                        print(f"🔍 第一个项目的键: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
                        print(f"📝 第一个项目示例:")
                        print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500] + "...")
                elif isinstance(data, dict):
                    print(f"🔍 数据键: {list(data.keys())}")
                    print(f"📝 数据示例:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"📄 响应内容 (前500字符): {response.text[:500]}")
        
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 连接错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_alternative_endpoints():
    """测试可能的替代端点"""
    
    alternative_urls = [
        "https://api.polymarket.com/events?active=true&closed=false&limit=5",
        "https://polymarket.com/api/events?active=true&closed=false&limit=5",
        "https://clob.polymarket.com/events?active=true&closed=false&limit=5",
        "https://gamma.polymarket.com/events?active=true&closed=false&limit=5"
    ]
    
    print(f"\n🔍 测试替代端点:")
    
    for url in alternative_urls:
        print(f"\n📡 测试: {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://polymarket.com/"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ 成功!")
                try:
                    data = response.json()
                    print(f"  📊 数据类型: {type(data)}")
                    if isinstance(data, list) and data:
                        print(f"  📄 数据数量: {len(data)}")
                    elif isinstance(data, dict):
                        print(f"  🔍 数据键: {list(data.keys())}")
                except:
                    print(f"  📄 非JSON响应")
            else:
                print(f"  ❌ 失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ⏰ 超时")
        except requests.exceptions.ConnectionError:
            print(f"  🔌 连接失败")
        except Exception as e:
            print(f"  ❌ 错误: {e}")

def main():
    """主函数"""
    print("🚀 测试Polymarket API端点")
    print("=" * 50)
    
    # 测试确切的端点
    test_exact_endpoint()
    
    # 测试替代端点
    test_alternative_endpoints()
    
    print(f"\n" + "=" * 50)
    print("📋 测试完成")
    
    # 提供使用建议
    print(f"\n💡 使用建议:")
    print(f"1. 如果API端点不可访问，可能需要:")
    print(f"   - VPN或代理")
    print(f"   - API密钥认证")
    print(f"   - 特定的请求头")
    print(f"2. 可以使用模拟数据进行开发和测试")
    print(f"3. 检查Polymarket官方文档获取最新API信息")

if __name__ == "__main__":
    main()