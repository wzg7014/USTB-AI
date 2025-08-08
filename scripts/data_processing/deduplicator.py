"""
USTB AI教务助手 - 数据去重处理器
负责多层次去重：URL精确匹配、标题相似度、内容语义相似度
"""

import logging
import hashlib
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
from data_config import DEDUP_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Deduplicator:
    """数据去重处理器"""
    
    def __init__(self):
        self.url_exact_match = DEDUP_CONFIG['url_exact_match']
        self.title_threshold = DEDUP_CONFIG['title_similarity_threshold']
        self.content_threshold = DEDUP_CONFIG['content_similarity_threshold']
        self.min_content_length = DEDUP_CONFIG['min_content_length']
        
        # 去重统计
        self.duplicate_stats = {
            'url_duplicates': 0,
            'title_duplicates': 0,
            'content_duplicates': 0,
            'total_removed': 0
        }
    
    def deduplicate(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行多层次去重"""
        logger.info(f"开始去重处理，原始数据: {len(data_list)} 条")
        
        # 第一层：URL精确去重
        data_list = self._url_exact_dedup(data_list)
        logger.info(f"URL精确去重后: {len(data_list)} 条")
        
        # 第二层：标题相似度去重
        data_list = self._title_similarity_dedup(data_list)
        logger.info(f"标题相似度去重后: {len(data_list)} 条")
        
        # 第三层：内容语义去重
        data_list = self._content_similarity_dedup(data_list)
        logger.info(f"内容语义去重后: {len(data_list)} 条")
        
        self._log_dedup_statistics(data_list)
        return data_list
    
    def _url_exact_dedup(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """URL精确匹配去重"""
        if not self.url_exact_match:
            return data_list
        
        seen_urls = set()
        unique_data = []
        
        for item in data_list:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_data.append(item)
            else:
                self.duplicate_stats['url_duplicates'] += 1
        
        return unique_data
    
    def _title_similarity_dedup(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标题相似度去重"""
        unique_data = []
        processed_titles = []
        
        for item in data_list:
            title = item.get('title', '').strip()
            if not title:
                continue
            
            # 检查与已处理标题的相似度
            is_duplicate = False
            for existing_title in processed_titles:
                similarity = self._calculate_text_similarity(title, existing_title)
                if similarity >= self.title_threshold:
                    is_duplicate = True
                    self.duplicate_stats['title_duplicates'] += 1
                    break
            
            if not is_duplicate:
                processed_titles.append(title)
                unique_data.append(item)
        
        return unique_data
    
    def _content_similarity_dedup(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """内容语义相似度去重"""
        unique_data = []
        content_hashes = set()
        
        for item in data_list:
            content = item.get('content', '').strip()
            
            # 跳过过短的内容
            if len(content) < self.min_content_length:
                continue
            
            # 使用内容哈希进行快速去重
            content_hash = self._get_content_hash(content)
            
            if content_hash not in content_hashes:
                # 进一步检查语义相似度
                is_duplicate = self._check_content_similarity(content, unique_data)
                
                if not is_duplicate:
                    content_hashes.add(content_hash)
                    unique_data.append(item)
                else:
                    self.duplicate_stats['content_duplicates'] += 1
            else:
                self.duplicate_stats['content_duplicates'] += 1
        
        return unique_data
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _get_content_hash(self, content: str) -> str:
        """获取内容哈希值"""
        # 标准化内容：去除空白字符、转小写
        normalized = ''.join(content.split()).lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _check_content_similarity(self, content: str, existing_data: List[Dict[str, Any]]) -> bool:
        """检查内容与已有数据的相似度"""
        # 简化版本：只检查最后几条数据以提高效率
        check_count = min(50, len(existing_data))
        recent_data = existing_data[-check_count:] if existing_data else []
        
        for existing_item in recent_data:
            existing_content = existing_item.get('content', '')
            if len(existing_content) < self.min_content_length:
                continue
            
            similarity = self._calculate_text_similarity(content, existing_content)
            if similarity >= self.content_threshold:
                return True
        
        return False
    
    def _log_dedup_statistics(self, final_data: List[Dict[str, Any]]):
        """记录去重统计信息"""
        total_removed = sum(self.duplicate_stats.values())
        original_count = len(final_data) + total_removed
        
        logger.info("=" * 50)
        logger.info("去重统计结果:")
        logger.info(f"  原始数据: {original_count} 条")
        logger.info(f"  URL重复: {self.duplicate_stats['url_duplicates']} 条")
        logger.info(f"  标题重复: {self.duplicate_stats['title_duplicates']} 条")
        logger.info(f"  内容重复: {self.duplicate_stats['content_duplicates']} 条")
        logger.info(f"  总计移除: {total_removed} 条")
        logger.info(f"  最终保留: {len(final_data)} 条")
        
        if original_count > 0:
            duplicate_rate = (total_removed / original_count) * 100
            logger.info(f"  重复率: {duplicate_rate:.2f}%")
            
            target_rate = DEDUP_CONFIG.get('duplicate_threshold', 0.02) * 100
            if duplicate_rate <= target_rate:
                logger.info(f"  ✅ 重复率控制达标 (≤{target_rate}%)")
            else:
                logger.warning(f"  ⚠️ 重复率超标 (>{target_rate}%)")
        
        logger.info("=" * 50)
    
    def get_duplicate_rate(self) -> float:
        """获取重复率"""
        total_removed = sum(self.duplicate_stats.values())
        total_processed = total_removed  # 这里需要从外部传入原始总数
        return (total_removed / total_processed) if total_processed > 0 else 0

def main():
    """测试去重处理器"""
    # 创建测试数据
    test_data = [
        {
            'title': '关于开展2025年工程教育认证申请工作的通知',
            'content': '各教学单位：根据中国工程教育专业认证协会要求...',
            'url': 'https://jwc.ustb.edu.cn/notice/001'
        },
        {
            'title': '关于开展2025年工程教育认证申请工作的通知',  # 重复标题
            'content': '各教学单位：根据中国工程教育专业认证协会要求...',
            'url': 'https://jwc.ustb.edu.cn/notice/002'
        },
        {
            'title': '关于转专业工作的通知',
            'content': '根据学校规定，现开展转专业工作...',
            'url': 'https://jwc.ustb.edu.cn/notice/003'
        }
    ]
    
    deduplicator = Deduplicator()
    result = deduplicator.deduplicate(test_data)
    
    print(f"去重前: {len(test_data)} 条")
    print(f"去重后: {len(result)} 条")

if __name__ == "__main__":
    main()
