#!/usr/bin/env python3
"""
USTB数据科学专家 - 初始数据检查脚本
对数据处理专家筛选的500条训练数据进行基本统计分析
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def load_training_data():
    """加载训练数据"""
    data_path = project_root / "data" / "processed" / "training_data.json"
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 成功加载训练数据: {len(data)} 条")
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ 加载数据失败: {e}")
        return None

def basic_statistics(df):
    """基本统计分析"""
    print("\n" + "="*50)
    print("📊 数据基本信息")
    print("="*50)
    print(f"数据总量: {len(df)} 条")
    print(f"数据列: {list(df.columns)}")
    
    print("\n📈 分类分布:")
    category_counts = df['category'].value_counts()
    for category, count in category_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {category}: {count} 条 ({percentage:.1f}%)")
    
    print("\n📊 Qwen评分统计:")
    score_stats = df['qwen_score'].describe()
    print(f"  平均分: {df['qwen_score'].mean():.3f}")
    print(f"  标准差: {df['qwen_score'].std():.3f}")
    print(f"  最小值: {df['qwen_score'].min():.3f}")
    print(f"  最大值: {df['qwen_score'].max():.3f}")
    print(f"  中位数: {df['qwen_score'].median():.3f}")
    
    print("\n📋 详细分布:")
    print(score_stats)
    
    return category_counts, score_stats

def quality_analysis(df):
    """质量分析"""
    print("\n" + "="*50)
    print("🔍 数据质量分析")
    print("="*50)
    
    # 评分分布分析
    high_quality = df[df['qwen_score'] >= 9.0]
    medium_quality = df[(df['qwen_score'] >= 8.0) & (df['qwen_score'] < 9.0)]
    low_quality = df[df['qwen_score'] < 8.0]
    
    print(f"高质量数据 (≥9.0分): {len(high_quality)} 条 ({len(high_quality)/len(df)*100:.1f}%)")
    print(f"中等质量数据 (8.0-9.0分): {len(medium_quality)} 条 ({len(medium_quality)/len(df)*100:.1f}%)")
    print(f"较低质量数据 (<8.0分): {len(low_quality)} 条 ({len(low_quality)/len(df)*100:.1f}%)")
    
    # 内容长度分析
    df['content_length'] = df['content'].str.len()
    print(f"\n📝 内容长度统计:")
    print(f"  平均长度: {df['content_length'].mean():.0f} 字符")
    print(f"  最短内容: {df['content_length'].min()} 字符")
    print(f"  最长内容: {df['content_length'].max()} 字符")
    
    # 检查缺失值
    print(f"\n🔍 数据完整性检查:")
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        if missing_count > 0:
            print(f"  {col}: {missing_count} 个缺失值")
        else:
            print(f"  {col}: ✅ 无缺失值")

def main():
    """主函数"""
    print("🔬 USTB数据科学专家 - 独立验证开始")
    print("📋 任务: 对数据处理专家筛选的500条训练数据进行统计分析")
    
    # 加载数据
    df = load_training_data()
    if df is None:
        return
    
    # 基本统计分析
    category_counts, score_stats = basic_statistics(df)
    
    # 质量分析
    quality_analysis(df)
    
    print("\n" + "="*50)
    print("✅ 初始数据检查完成")
    print("📋 下一步: 进行独立验证和深度统计分析")
    print("="*50)

if __name__ == "__main__":
    main()
