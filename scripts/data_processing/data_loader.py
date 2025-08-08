"""
USTB AI教务助手 - 数据加载器
负责从8个分类目录加载原始数据
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from data_config import DATA_PATHS

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """原始数据加载器"""
    
    def __init__(self):
        self.raw_data_dir = DATA_PATHS['raw_data_dir']
        self.data_categories = []
        self.total_count = 0
        
    def load_all_data(self) -> List[Dict[str, Any]]:
        """加载所有分类的原始数据"""
        all_data = []
        category_stats = {}
        
        logger.info(f"开始加载原始数据，目录: {self.raw_data_dir}")
        
        # 遍历所有分类目录
        for category_dir in os.listdir(self.raw_data_dir):
            category_path = self.raw_data_dir / category_dir
            
            if not category_path.is_dir():
                continue
                
            category_data = self._load_category_data(category_path, category_dir)
            category_count = len(category_data)
            
            if category_count > 0:
                all_data.extend(category_data)
                category_stats[category_dir] = category_count
                logger.info(f"加载 {category_dir}: {category_count}条数据")
        
        self.total_count = len(all_data)
        self._log_data_statistics(category_stats)
        
        return all_data
    
    def _load_category_data(self, category_path: Path, category_name: str) -> List[Dict[str, Any]]:
        """加载单个分类的数据"""
        category_data = []
        
        # 遍历分类目录下的所有JSON文件
        for file_path in category_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 处理不同的数据格式
                    if isinstance(data, list):
                        # 列表格式：直接处理
                        for i, item in enumerate(data):
                            item['data_category'] = category_name
                            item['original_id'] = f"{category_name}_{file_path.stem}_{i}"
                            category_data.append(item)
                    elif isinstance(data, dict) and 'pages' in data:
                        # 对象格式：提取pages字段
                        pages = data['pages']
                        for i, item in enumerate(pages):
                            item['data_category'] = category_name
                            item['original_id'] = f"{category_name}_{file_path.stem}_{i}"
                            category_data.append(item)
                        logger.info(f"文件 {file_path} 对象格式，提取pages: {len(pages)}条")
                    else:
                        logger.warning(f"文件 {file_path} 格式不支持，跳过")
                        
            except Exception as e:
                logger.error(f"加载文件 {file_path} 失败: {e}")
                continue
        
        return category_data
    
    def _log_data_statistics(self, category_stats: Dict[str, int]):
        """记录数据统计信息"""
        logger.info("=" * 50)
        logger.info("数据加载统计:")
        
        for category, count in sorted(category_stats.items()):
            percentage = (count / self.total_count) * 100
            logger.info(f"  {category}: {count}条 ({percentage:.1f}%)")
        
        logger.info(f"总计: {self.total_count}条数据")
        logger.info(f"筛选目标: 500条 (筛选率: {500/self.total_count*100:.1f}%)")
        logger.info("=" * 50)
    
    def validate_data_structure(self, data: List[Dict[str, Any]]) -> bool:
        """验证数据结构完整性"""
        required_fields = ['title', 'content', 'url']
        invalid_count = 0
        
        logger.info("开始验证数据结构...")
        
        for i, item in enumerate(data):
            missing_fields = []
            for field in required_fields:
                if field not in item or not item[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                invalid_count += 1
                if invalid_count <= 5:  # 只显示前5个错误
                    logger.warning(f"数据 {i} 缺少字段: {missing_fields}")
        
        if invalid_count > 0:
            logger.warning(f"发现 {invalid_count} 条数据结构不完整")
            return False
        
        logger.info("数据结构验证通过")
        return True
    
    def get_sample_data(self, count: int = 5) -> List[Dict[str, Any]]:
        """获取样本数据用于测试"""
        all_data = self.load_all_data()
        return all_data[:count] if all_data else []

def main():
    """测试数据加载器"""
    loader = DataLoader()
    
    # 加载所有数据
    all_data = loader.load_all_data()
    
    # 验证数据结构
    is_valid = loader.validate_data_structure(all_data)
    
    # 显示样本数据
    if all_data:
        sample = all_data[0]
        logger.info("样本数据结构:")
        for key in sample.keys():
            logger.info(f"  {key}: {type(sample[key])}")

if __name__ == "__main__":
    main()
