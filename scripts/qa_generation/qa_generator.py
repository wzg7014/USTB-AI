#!/usr/bin/env python3
"""
USTB问答生成专家 - 问答对生成主脚本
基于500条训练数据生成2500个高质量问答对
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import re
import random
from datetime import datetime
from typing import List, Dict, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

class QAGenerator:
    """问答对生成器"""
    
    def __init__(self):
        self.project_root = project_root
        self.data_path = self.project_root / "data" / "processed" / "training_data.json"
        self.output_dir = self.project_root / "data" / "training"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 8个教务分类映射
        self.category_mapping = {
            "转专业": ["转专业", "专业调整", "学院转换"],
            "选课": ["选课", "课程安排", "学分", "课表"],
            "考试": ["考试", "成绩", "补考", "重修", "绩点"],
            "学籍": ["学籍", "注册", "休学", "复学", "退学", "毕业"],
            "奖助": ["奖学金", "助学金", "勤工助学", "资助"],
            "实践": ["实习", "实践", "毕业设计", "论文", "创新"],
            "国际": ["国际", "交流", "出国", "留学", "交换"],
            "其他": ["通知", "公告", "政策", "服务", "咨询"]
        }
        
        # 问题类型模板
        self.question_templates = {
            "事实查询类": [
                "{主题}的时间是什么时候？",
                "{主题}的地点在哪里？",
                "{主题}的条件是什么？",
                "{主题}的要求有哪些？",
                "{主题}的截止日期是什么时候？"
            ],
            "流程指导类": [
                "如何进行{主题}？",
                "{主题}的流程是什么？",
                "{主题}需要准备哪些材料？",
                "{主题}的步骤有哪些？",
                "怎样申请{主题}？"
            ],
            "条件判断类": [
                "什么情况下可以{主题}？",
                "{条件}能否{主题}？",
                "{主题}有什么限制？",
                "谁可以参与{主题}？",
                "{主题}的资格要求是什么？"
            ],
            "比较选择类": [
                "{选项A}和{选项B}有什么区别？",
                "选择{主题}还是{备选}更好？",
                "{主题}的优缺点是什么？",
                "不同{主题}方案的差异？",
                "{主题}的各种选择？"
            ],
            "解释说明类": [
                "什么是{主题}？",
                "{主题}是什么意思？",
                "为什么要{主题}？",
                "{主题}的目的是什么？",
                "{主题}的意义何在？"
            ],
            "故障排除类": [
                "{主题}遇到问题怎么办？",
                "{主题}失败了如何解决？",
                "{主题}不成功的原因？",
                "如何解决{主题}的问题？",
                "{主题}出错怎么处理？"
            ]
        }
        
        self.qa_pairs = []
        self.quality_scores = []
        
    def load_training_data(self):
        """加载训练数据"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            print(f"✅ 成功加载训练数据: {len(self.df)} 条")
            return True
        except Exception as e:
            print(f"❌ 加载训练数据失败: {e}")
            return False
    
    def classify_content(self, content: str, title: str) -> str:
        """基于内容和标题智能分类到8个教务分类"""
        content_lower = (content + " " + title).lower()
        
        # 分类关键词匹配
        category_scores = {}
        for category, keywords in self.category_mapping.items():
            score = 0
            for keyword in keywords:
                score += content_lower.count(keyword.lower())
            category_scores[category] = score
        
        # 返回得分最高的分类，如果都是0则归为"其他"
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] == 0:
            return "其他"
        return best_category
    
    def extract_key_info(self, content: str) -> List[str]:
        """从内容中提取关键信息点"""
        # 简化的关键信息提取
        key_info = []
        
        # 提取时间信息
        time_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{1,2}月\d{1,2}日',
            r'第\d+周',
            r'\d{1,2}:\d{2}'
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, content)
            key_info.extend(matches)
        
        # 提取重要概念（简化版）
        important_concepts = [
            "申请", "截止", "要求", "条件", "流程", "材料", 
            "时间", "地点", "联系", "咨询", "办理", "提交"
        ]
        for concept in important_concepts:
            if concept in content:
                key_info.append(concept)
        
        return list(set(key_info))
    
    def generate_question(self, content: str, title: str, question_type: str) -> str:
        """生成特定类型的问题"""
        # 从标题和内容中提取主题
        main_topic = title.split("关于")[-1].split("的通知")[0] if "关于" in title else title[:20]
        
        # 选择模板
        templates = self.question_templates.get(question_type, [])
        if not templates:
            return None
        
        template = random.choice(templates)
        
        # 替换模板中的占位符
        question = template.replace("{主题}", main_topic)
        question = question.replace("{条件}", "学生")
        question = question.replace("{选项A}", "方案A")
        question = question.replace("{选项B}", "方案B")
        question = question.replace("{备选}", "其他选择")
        
        return question
    
    def generate_answer(self, content: str, question: str) -> str:
        """基于内容生成答案"""
        # 简化的答案生成逻辑
        # 实际项目中应该使用更复杂的NLP技术
        
        # 提取与问题相关的内容段落
        content_sentences = content.split('。')
        relevant_sentences = []
        
        # 基于关键词匹配找到相关句子
        question_keywords = re.findall(r'[\u4e00-\u9fff]+', question)
        
        for sentence in content_sentences:
            relevance_score = 0
            for keyword in question_keywords:
                if keyword in sentence:
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_sentences.append((sentence, relevance_score))
        
        # 按相关性排序，取前3个句子
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in relevant_sentences[:3]]
        
        if top_sentences:
            answer = "。".join(top_sentences) + "。"
            # 清理答案
            answer = answer.replace("。。", "。").strip()
            return answer
        else:
            # 如果没有找到相关内容，返回通用回答
            return "根据相关规定，具体信息请咨询教务处或查看官方通知。"
    
    def calculate_quality_score(self, question: str, answer: str, content: str) -> float:
        """计算问答对质量评分"""
        score = 0.0
        
        # 可回答性评估 (40%)
        if len(answer) > 20 and "具体信息请咨询" not in answer:
            score += 0.4
        elif len(answer) > 10:
            score += 0.2
        
        # 问题自然性评估 (30%)
        if len(question) > 5 and len(question) < 50:
            score += 0.15
        if "？" in question or "吗" in question or "如何" in question:
            score += 0.15
        
        # 内容相关性评估 (30%)
        question_chars = set(question)
        content_chars = set(content)
        overlap = len(question_chars & content_chars) / len(question_chars) if question_chars else 0
        score += overlap * 0.3
        
        return min(score, 1.0)
    
    def generate_qa_pairs_for_document(self, doc: Dict) -> List[Dict]:
        """为单个文档生成问答对"""
        content = doc['content']
        title = doc['title']
        doc_id = doc['id']
        
        # 重新分类到8个教务分类
        new_category = self.classify_content(content, title)
        
        qa_pairs = []
        question_types = list(self.question_templates.keys())
        
        # 为每个文档生成5个问答对
        for i in range(5):
            question_type = random.choice(question_types)
            question = self.generate_question(content, title, question_type)
            
            if question:
                answer = self.generate_answer(content, question)
                quality_score = self.calculate_quality_score(question, answer, content)
                
                # 只保留质量评分≥0.6的问答对
                if quality_score >= 0.6:
                    qa_pair = {
                        "id": f"qa_{doc_id}_{i+1:03d}",
                        "instruction": question,
                        "input": "",
                        "output": answer,
                        "source_id": doc_id,
                        "category": new_category,
                        "question_type": question_type,
                        "quality_score": round(quality_score, 3),
                        "created_time": datetime.now().isoformat()
                    }
                    qa_pairs.append(qa_pair)
        
        return qa_pairs
    
    def generate_all_qa_pairs(self):
        """生成所有问答对"""
        print("\n🚀 开始生成问答对...")
        
        all_qa_pairs = []
        category_stats = {}
        
        for idx, row in self.df.iterrows():
            doc_qa_pairs = self.generate_qa_pairs_for_document(row.to_dict())
            all_qa_pairs.extend(doc_qa_pairs)
            
            # 统计分类分布
            for qa in doc_qa_pairs:
                category = qa['category']
                category_stats[category] = category_stats.get(category, 0) + 1
            
            if (idx + 1) % 50 == 0:
                print(f"  已处理 {idx + 1}/{len(self.df)} 个文档，生成 {len(all_qa_pairs)} 个问答对")
        
        self.qa_pairs = all_qa_pairs
        
        print(f"\n✅ 问答对生成完成:")
        print(f"  总数量: {len(all_qa_pairs)} 个")
        print(f"  分类分布:")
        for category, count in sorted(category_stats.items()):
            print(f"    {category}: {count} 个")
        
        return all_qa_pairs
    
    def save_qa_dataset(self):
        """保存问答数据集"""
        output_file = self.output_dir / "qa_dataset.jsonl"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for qa in self.qa_pairs:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        print(f"✅ 问答数据集已保存: {output_file}")
        return output_file

def main():
    """主函数"""
    print("🔬 USTB问答生成专家 - 问答对生成系统")
    print("="*70)
    
    generator = QAGenerator()
    
    # 加载数据
    if not generator.load_training_data():
        return
    
    # 生成问答对
    qa_pairs = generator.generate_all_qa_pairs()
    
    # 保存数据集
    generator.save_qa_dataset()
    
    print("\n" + "="*70)
    print("✅ 问答对生成完成")
    print("📋 下一步: 质量评估和验证")
    print("="*70)

if __name__ == "__main__":
    main()
