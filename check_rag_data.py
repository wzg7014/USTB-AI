#!/usr/bin/env python3
"""
检查RAG数据文件
"""

import json
import os

def check_rag_data():
    """检查RAG数据文件"""
    file_path = "data/processed/rag_data.json"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    print(f"📁 文件大小: {file_size / (1024*1024):.2f} MB")
    
    try:
        # 加载JSON数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 数据记录数: {len(data)}")
        
        if len(data) > 0:
            # 检查第一条记录的结构
            first_record = data[0]
            print(f"\n📋 数据结构:")
            for key in first_record.keys():
                print(f"   - {key}: {type(first_record[key]).__name__}")
            
            # 检查附件信息
            has_attachments = sum(1 for record in data if record.get('attachments'))
            print(f"\n📎 包含附件的记录: {has_attachments}/{len(data)} ({has_attachments/len(data)*100:.1f}%)")
            
            # 检查分类分布
            categories = {}
            for record in data:
                cat = record.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"\n📂 分类分布:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   - {cat}: {count}")
            
            # 检查评分分布
            scores = [record.get('qwen_score', 0) for record in data]
            avg_score = sum(scores) / len(scores)
            print(f"\n⭐ 平均Qwen评分: {avg_score:.2f}")
            
            print(f"\n✅ RAG数据文件检查完成！")
            print(f"🎯 这个文件可以直接用于RAG系统的向量索引构建")
            
    except Exception as e:
        print(f"❌ 读取文件出错: {str(e)}")

if __name__ == "__main__":
    check_rag_data()
