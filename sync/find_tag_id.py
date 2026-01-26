#!/usr/bin/env python3
"""
标签ID查找工具 - 帮助用户快速查找标签ID
"""

import json
import os
import argparse
import glob
from typing import List, Dict, Any

def find_latest_tag_mapping(data_dir: str = "./data") -> str:
    """
    查找最新的标签映射文件
    
    Args:
        data_dir: 数据目录
        
    Returns:
        str: 最新标签映射文件路径
    """
    pattern = os.path.join(data_dir, "tags", "tag_id_mapping_*.json")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # 按文件名排序，最新的在最后
    files.sort()
    return files[-1]

def load_tag_mapping(file_path: str) -> Dict[str, Dict]:
    """
    加载标签映射文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict: 标签映射数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 无法加载标签映射文件: {e}")
        return {}

def search_tags(tag_mapping: Dict[str, Dict], query: str) -> List[Dict]:
    """
    搜索标签
    
    Args:
        tag_mapping: 标签映射数据
        query: 搜索查询
        
    Returns:
        List[Dict]: 匹配的标签列表
    """
    query_lower = query.lower()
    matches = []
    
    for tag_id, tag_info in tag_mapping.items():
        label = tag_info.get('label', '').lower()
        slug = tag_info.get('slug', '').lower()
        
        # 检查是否匹配
        if (query_lower in label or 
            query_lower in slug or 
            query_lower == tag_id):
            matches.append({
                'id': tag_id,
                'label': tag_info.get('label', ''),
                'slug': tag_info.get('slug', ''),
                'score': 0  # 可以添加相关性评分
            })
    
    # 按标签名称排序
    matches.sort(key=lambda x: x['label'].lower())
    return matches

def main():
    parser = argparse.ArgumentParser(description="标签ID查找工具")
    parser.add_argument("query", nargs='?', help="搜索查询（标签名称、slug或ID）")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--list-all", action="store_true", help="列出所有标签")
    parser.add_argument("--limit", type=int, default=20, help="显示结果数量限制")
    
    args = parser.parse_args()
    
    # 查找最新的标签映射文件
    mapping_file = find_latest_tag_mapping(args.data_dir)
    
    if not mapping_file:
        print("❌ 未找到标签映射文件")
        print("请先运行: python3 sync/tag_markets_sync.py --sync-tags")
        return
    
    print(f"📁 使用标签映射文件: {os.path.basename(mapping_file)}")
    
    # 加载标签映射
    tag_mapping = load_tag_mapping(mapping_file)
    
    if not tag_mapping:
        return
    
    print(f"📊 总共有 {len(tag_mapping)} 个标签")
    
    # 如果要求列出所有标签
    if args.list_all:
        print("\n🏷️  所有可用标签:")
        print("-" * 80)
        
        # 按标签名称排序
        sorted_tags = sorted(tag_mapping.items(), key=lambda x: x[1].get('label', '').lower())
        
        for i, (tag_id, tag_info) in enumerate(sorted_tags[:args.limit]):
            label = tag_info.get('label', 'N/A')
            slug = tag_info.get('slug', 'N/A')
            print(f"{i+1:3d}. ID: {tag_id:<10} 名称: {label:<25} Slug: {slug}")
        
        if len(sorted_tags) > args.limit:
            print(f"\n... 还有 {len(sorted_tags) - args.limit} 个标签")
            print(f"使用 --limit {len(sorted_tags)} 查看全部")
        
        return
    
    # 如果没有提供查询，显示帮助
    if not args.query:
        print("\n💡 使用方法:")
        print("  python3 sync/find_tag_id.py 'israel'     # 搜索包含'israel'的标签")
        print("  python3 sync/find_tag_id.py '180'        # 搜索ID为180的标签")
        print("  python3 sync/find_tag_id.py --list-all   # 列出所有标签")
        return
    
    # 搜索标签
    matches = search_tags(tag_mapping, args.query)
    
    if not matches:
        print(f"\n❌ 未找到匹配 '{args.query}' 的标签")
        print("\n💡 建议:")
        print("  - 尝试使用部分关键词")
        print("  - 使用 --list-all 查看所有可用标签")
        return
    
    print(f"\n🔍 搜索 '{args.query}' 的结果:")
    print("-" * 80)
    
    for i, match in enumerate(matches[:args.limit]):
        tag_id = match['id']
        label = match['label']
        slug = match['slug']
        print(f"{i+1:3d}. ID: {tag_id:<10} 名称: {label:<25} Slug: {slug}")
    
    if len(matches) > args.limit:
        print(f"\n... 还有 {len(matches) - args.limit} 个匹配结果")
        print(f"使用 --limit {len(matches)} 查看全部")
    
    print(f"\n💡 使用标签ID搜索市场:")
    if len(matches) == 1:
        tag_id = matches[0]['id']
        print(f"  python3 sync/tag_markets_sync.py --tag-ids {tag_id}")
    else:
        # 显示前3个标签ID的示例
        tag_ids = [match['id'] for match in matches[:3]]
        print(f"  python3 sync/tag_markets_sync.py --tag-ids {' '.join(tag_ids)}")

if __name__ == "__main__":
    main()