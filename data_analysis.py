#!/usr/bin/env python3
"""
简单的数据分析脚本，用于验证CSV数据质量
"""

import pandas as pd
import json
from datetime import datetime

def analyze_markets_csv(csv_file):
    """分析市场CSV文件"""
    print(f"📊 分析文件: {csv_file}")
    print("=" * 60)
    
    # 读取CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ 成功读取CSV文件")
        print(f"📈 总记录数: {len(df):,}")
        print(f"📋 字段数: {len(df.columns)}")
        print()
        
        # 显示字段信息
        print("📝 字段列表:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        print()
        
        # 基本统计
        print("📊 基本统计:")
        print(f"  活跃市场: {df['active'].sum():,}")
        print(f"  已关闭市场: {df['closed'].sum():,}")
        print(f"  接受订单的市场: {df['acceptingOrders'].sum():,}")
        print()
        
        # 分类统计
        if 'category' in df.columns:
            categories = df['category'].value_counts().head(10)
            print("🏷️  热门分类 (前10):")
            for cat, count in categories.items():
                if pd.notna(cat) and cat != '':
                    print(f"  {cat}: {count:,}")
        print()
        
        # 交易量统计
        if 'volumeNum' in df.columns:
            df['volumeNum'] = pd.to_numeric(df['volumeNum'], errors='coerce')
            volume_stats = df['volumeNum'].describe()
            print("💰 交易量统计:")
            print(f"  平均交易量: ${volume_stats['mean']:,.2f}")
            print(f"  中位数交易量: ${volume_stats['50%']:,.2f}")
            print(f"  最大交易量: ${volume_stats['max']:,.2f}")
        print()
        
        # 流动性统计
        if 'liquidityNum' in df.columns:
            df['liquidityNum'] = pd.to_numeric(df['liquidityNum'], errors='coerce')
            liquidity_stats = df['liquidityNum'].describe()
            print("💧 流动性统计:")
            print(f"  平均流动性: ${liquidity_stats['mean']:,.2f}")
            print(f"  中位数流动性: ${liquidity_stats['50%']:,.2f}")
            print(f"  最大流动性: ${liquidity_stats['max']:,.2f}")
        print()
        
        # 数据质量检查
        print("🔍 数据质量检查:")
        missing_data = df.isnull().sum()
        for col in ['id', 'question', 'active', 'closed']:
            if col in df.columns:
                missing = missing_data[col]
                print(f"  {col} 缺失值: {missing} ({missing/len(df)*100:.1f}%)")
        print()
        
        # 示例记录
        print("📋 示例记录 (前3条):")
        for i in range(min(3, len(df))):
            record = df.iloc[i]
            print(f"  记录 {i+1}:")
            print(f"    ID: {record['id']}")
            print(f"    问题: {record['question'][:80]}...")
            print(f"    活跃: {record['active']}")
            print(f"    交易量: {record.get('volumeNum', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 读取CSV文件失败: {e}")
        return False

def main():
    csv_file = "data/markets/markets_2026-01-16.csv"
    
    print("🎯 Polymarket数据分析")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = analyze_markets_csv(csv_file)
    
    if success:
        print("🎉 数据分析完成!")
    else:
        print("❌ 数据分析失败!")

if __name__ == "__main__":
    main()