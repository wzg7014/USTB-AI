"""
USTB AI教务助手 - 双数据集生成器
负责生成RAG检索数据集和微调训练数据集
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from data_config import DATA_PATHS, OUTPUT_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatasetGenerator:
    """双数据集生成器"""
    
    def __init__(self):
        self.processed_dir = DATA_PATHS['processed_dir']
        self.rag_fields = OUTPUT_CONFIG.get('rag_fields', [
            'id', 'title', 'content', 'url', 'category', 
            'publish_date', 'attachments', 'qwen_score', 'score_breakdown'
        ])
        self.training_fields = OUTPUT_CONFIG.get('training_fields', [
            'id', 'title', 'content', 'category', 
            'publish_date', 'qwen_score'
        ])
        
        # 确保输出目录存在
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_datasets(self, scored_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """生成双数据集"""
        logger.info(f"开始生成双数据集，输入数据: {len(scored_data)} 条")
        
        # 生成RAG检索数据集
        rag_dataset = self._generate_rag_dataset(scored_data)
        rag_file_path = self._save_rag_dataset(rag_dataset)
        
        # 生成微调训练数据集
        training_dataset = self._generate_training_dataset(scored_data)
        training_file_path = self._save_training_dataset(training_dataset)
        
        # 验证数据一致性
        self._validate_dataset_consistency(rag_dataset, training_dataset)
        
        logger.info("双数据集生成完成")
        return {
            'rag_dataset_path': rag_file_path,
            'training_dataset_path': training_file_path
        }
    
    def _generate_rag_dataset(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成RAG检索数据集（包含附件信息）"""
        rag_dataset = []
        
        for i, item in enumerate(data):
            rag_item = {
                'id': f"ustb_{i+1:04d}",
                'title': item.get('title', ''),
                'content': item.get('content', ''),
                'url': item.get('url', ''),
                'category': item.get('category', item.get('data_category', '')),
                'publish_date': item.get('publish_date', ''),
                'qwen_score': item.get('qwen_score', 0),
                'score_breakdown': item.get('score_breakdown', {}),
                'attachments': self._process_attachments(item.get('attachments', []))
            }
            
            # 只保留指定字段
            filtered_item = {k: v for k, v in rag_item.items() if k in self.rag_fields}
            rag_dataset.append(filtered_item)
        
        logger.info(f"RAG数据集生成完成: {len(rag_dataset)} 条")
        return rag_dataset
    
    def _generate_training_dataset(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成微调训练数据集（纯文本内容）"""
        training_dataset = []
        
        for i, item in enumerate(data):
            training_item = {
                'id': f"ustb_{i+1:04d}",
                'title': item.get('title', ''),
                'content': self._clean_content_for_training(item.get('content', '')),
                'category': item.get('category', item.get('data_category', '')),
                'publish_date': item.get('publish_date', ''),
                'qwen_score': item.get('qwen_score', 0)
            }
            
            # 只保留指定字段
            filtered_item = {k: v for k, v in training_item.items() if k in self.training_fields}
            training_dataset.append(filtered_item)
        
        logger.info(f"训练数据集生成完成: {len(training_dataset)} 条")
        return training_dataset
    
    def _process_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理附件信息"""
        processed_attachments = []
        
        for attachment in attachments:
            if isinstance(attachment, dict):
                processed_attachment = {
                    'name': attachment.get('title', attachment.get('name', '')),
                    'url': attachment.get('url', ''),
                    'type': self._get_file_type(attachment.get('title', ''))
                }
                processed_attachments.append(processed_attachment)
        
        return processed_attachments
    
    def _get_file_type(self, filename: str) -> str:
        """根据文件名获取文件类型"""
        if not filename:
            return 'unknown'
        
        filename_lower = filename.lower()
        if filename_lower.endswith('.pdf'):
            return 'application/pdf'
        elif filename_lower.endswith('.docx'):
            return 'application/docx'
        elif filename_lower.endswith('.doc'):
            return 'application/doc'
        elif filename_lower.endswith('.xlsx'):
            return 'application/xlsx'
        elif filename_lower.endswith('.xls'):
            return 'application/xls'
        else:
            return 'unknown'
    
    def _clean_content_for_training(self, content: str) -> str:
        """清理内容用于训练（移除附件引用等）"""
        if not content:
            return ''
        
        # 移除常见的附件引用模式
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过附件相关行
            if any(keyword in line for keyword in ['附件', '相关附件', '下载', '.pdf', '.docx', '.doc']):
                continue
            if line and not line.startswith('附件'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _save_rag_dataset(self, dataset: List[Dict[str, Any]]) -> str:
        """保存RAG数据集"""
        file_path = self.processed_dir / OUTPUT_CONFIG['rag_dataset_file']
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        logger.info(f"RAG数据集已保存: {file_path}")
        return str(file_path)
    
    def _save_training_dataset(self, dataset: List[Dict[str, Any]]) -> str:
        """保存训练数据集"""
        file_path = self.processed_dir / OUTPUT_CONFIG['training_dataset_file']
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        logger.info(f"训练数据集已保存: {file_path}")
        return str(file_path)
    
    def _validate_dataset_consistency(self, rag_dataset: List[Dict[str, Any]], 
                                    training_dataset: List[Dict[str, Any]]):
        """验证双数据集的一致性"""
        if len(rag_dataset) != len(training_dataset):
            logger.warning(f"数据集长度不一致: RAG({len(rag_dataset)}) vs 训练({len(training_dataset)})")
            return
        
        inconsistent_count = 0
        for i, (rag_item, training_item) in enumerate(zip(rag_dataset, training_dataset)):
            if rag_item['id'] != training_item['id']:
                inconsistent_count += 1
                if inconsistent_count <= 5:  # 只显示前5个不一致
                    logger.warning(f"ID不一致 [{i}]: RAG({rag_item['id']}) vs 训练({training_item['id']})")
        
        if inconsistent_count == 0:
            logger.info("✅ 双数据集一致性验证通过")
        else:
            logger.warning(f"⚠️ 发现 {inconsistent_count} 处不一致")

def main():
    """测试双数据集生成器"""
    # 创建测试数据
    test_data = [
        {
            'title': '关于开展2025年工程教育认证申请工作的通知',
            'content': '各教学单位：根据要求开展认证工作...\n附件1：申请表.pdf',
            'url': 'https://jwc.ustb.edu.cn/notice/001',
            'category': '通知通告',
            'publish_date': '2025-07-23',
            'qwen_score': 8.5,
            'score_breakdown': {'completeness': 8.5, 'relevance': 8.0},
            'attachments': [
                {'title': '申请表.pdf', 'url': 'https://jwc.ustb.edu.cn/files/form.pdf'}
            ]
        }
    ]
    
    generator = DatasetGenerator()
    result = generator.generate_datasets(test_data)
    
    print("生成结果:")
    for key, path in result.items():
        print(f"  {key}: {path}")

if __name__ == "__main__":
    main()
