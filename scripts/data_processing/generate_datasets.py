#!/usr/bin/env python3
"""
生成双数据集：RAG检索数据集 + 微调训练数据集
"""

import json
import pandas as pd
from pathlib import Path

def generate_rag_dataset():
    """生成RAG检索数据集（全量4621条，含附件）"""
    
    # 加载全量评分数据
    with open('data/processed/complete_scoring_all_categories.json', 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    print(f"加载全量数据: {len(all_data)}条")
    
    # 整理为RAG格式
    rag_data = []
    for i, item in enumerate(all_data):
        rag_item = {
            'id': f'ustb_{i+1:04d}',
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'url': item.get('url', ''),
            'category': item.get('category', item.get('data_category', '')),
            'publish_date': item.get('publish_date', ''),
            'attachments': item.get('attachments', []),
            'data_category': item.get('data_category', ''),
            'qwen_score': item.get('qwen_score', 0),
            'score_breakdown': item.get('score_breakdown', {})
        }
        rag_data.append(rag_item)
    
    # 保存RAG数据集
    with open('data/processed/rag_data.json', 'w', encoding='utf-8') as f:
        json.dump(rag_data, f, ensure_ascii=False, indent=2)
    
    # 统计信息
    with_attachments = sum(1 for item in rag_data if item['attachments'])
    
    print(f"✅ RAG数据集已生成: {len(rag_data)}条数据")
    print(f"   包含附件的数据: {with_attachments}条")
    
    return rag_data

def generate_training_dataset():
    """生成微调训练数据集（筛选500条高质量数据，纯文本）"""
    
    # 加载全量评分数据
    with open('data/processed/complete_scoring_all_categories.json', 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    df = pd.DataFrame(all_data)
    
    # 筛选策略：7.5分以上 + 排除fylm分类
    filtered_data = df[(df['qwen_score'] >= 7.5) & (df['data_category'] != 'fylm')]
    
    print(f"筛选前数据量: {len(df)}条")
    print(f"7.5分以上数据: {len(df[df['qwen_score'] >= 7.5])}条")
    print(f"排除fylm后: {len(filtered_data)}条")
    
    # 按分数排序取前500条
    if len(filtered_data) > 500:
        top_500 = filtered_data.nlargest(500, 'qwen_score')
    else:
        top_500 = filtered_data
    
    print(f"最终筛选: {len(top_500)}条")
    print(f"分数范围: {top_500['qwen_score'].min():.2f} - {top_500['qwen_score'].max():.2f}")
    print(f"平均分: {top_500['qwen_score'].mean():.2f}")
    
    # 转换为训练格式（纯文本，无附件）
    training_data = []
    for i, (_, item) in enumerate(top_500.iterrows()):
        training_item = {
            'id': f'train_{i+1:04d}',
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'category': item.get('category', item.get('data_category', '')),
            'publish_date': item.get('publish_date', ''),
            'data_category': item.get('data_category', ''),
            'qwen_score': item.get('qwen_score', 0)
        }
        training_data.append(training_item)
    
    # 保存训练数据集
    with open('data/processed/training_data.json', 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 训练数据集已生成: {len(training_data)}条数据")
    
    # 分类分布统计
    category_counts = top_500['data_category'].value_counts()
    print(f"分类分布:")
    for category, count in category_counts.items():
        print(f"  {category}: {count}条")
    
    return training_data

def main():
    """主函数"""
    print("=" * 50)
    print("生成USTB双数据集")
    print("=" * 50)
    
    # 1. 生成RAG检索数据集
    print("\n1. 生成RAG检索数据集...")
    rag_data = generate_rag_dataset()
    
    # 2. 生成微调训练数据集
    print("\n2. 生成微调训练数据集...")
    training_data = generate_training_dataset()
    
    print("\n" + "=" * 50)
    print("双数据集生成完成！")
    print("=" * 50)
    print(f"RAG数据集: data/processed/rag_data.json ({len(rag_data)}条)")
    print(f"训练数据集: data/processed/training_data.json ({len(training_data)}条)")
    print("\n✅ 数据处理专家任务完成！")

if __name__ == "__main__":
    main()
