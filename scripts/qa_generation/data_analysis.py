#!/usr/bin/env python3
"""
USTB问答生成专家 - 训练数据分析脚本
分析数据科学专家验证通过的500条训练数据
"""

import json
import pandas as pd
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def analyze_training_data():
    """分析训练数据"""
    print("🔬 USTB问答生成专家 - 训练数据分析")
    print("="*60)
    
    # 加载训练数据
    data_path = project_root / "data" / "processed" / "training_data.json"
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        print(f"✅ 成功加载训练数据: {len(df)} 条")
        
        # 基本信息
        print(f"\n📊 数据基本信息:")
        print(f"  数据总量: {len(df)} 条")
        print(f"  数据字段: {list(df.columns)}")
        
        # 分类分布统计
        print(f"\n📈 分类分布统计:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {category}: {count} 条 ({percentage:.1f}%)")
        
        # 评分统计
        print(f"\n📊 评分统计:")
        print(f"  平均评分: {df['qwen_score'].mean():.3f}")
        print(f"  最低评分: {df['qwen_score'].min():.3f}")
        print(f"  最高评分: {df['qwen_score'].max():.3f}")
        print(f"  标准差: {df['qwen_score'].std():.3f}")
        
        # 内容长度统计
        df['content_length'] = df['content'].str.len()
        print(f"\n📝 内容长度统计:")
        print(f"  平均内容长度: {df['content_length'].mean():.0f} 字符")
        print(f"  最短内容: {df['content_length'].min()} 字符")
        print(f"  最长内容: {df['content_length'].max()} 字符")
        
        # 问答生成策略分析
        print(f"\n🎯 问答生成策略分析:")
        target_qa_per_doc = 5  # 每条文档生成5个问答对
        total_target_qa = len(df) * target_qa_per_doc
        
        print(f"  目标问答对总数: {total_target_qa} 个")
        print(f"  每条文档生成: {target_qa_per_doc} 个问答对")
        
        # 分类生成分布
        print(f"\n📋 各分类生成计划:")
        for category, count in category_counts.items():
            qa_count = count * target_qa_per_doc
            print(f"  {category}: {qa_count} 个问答对 (基于{count}条文档)")
        
        return df, category_counts
        
    except Exception as e:
        print(f"❌ 加载数据失败: {e}")
        return None, None

def main():
    """主函数"""
    df, category_counts = analyze_training_data()
    
    if df is not None:
        print("\n" + "="*60)
        print("✅ 训练数据分析完成")
        print("📋 下一步: 开始问答对生成工作")
        print("="*60)
    else:
        print("\n❌ 数据分析失败，请检查数据文件")

if __name__ == "__main__":
    main()
