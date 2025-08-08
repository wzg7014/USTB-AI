"""
USTB RAG系统 - 查询扩展服务
实现同义词扩展和查询重写，提升检索质量
"""
import re
from typing import List, Dict, Set
from loguru import logger

class QueryExpansionService:
    """查询扩展服务"""
    
    def __init__(self):
        # 教务相关同义词词典
        self.synonyms = {
            # 选课相关
            "选课": ["课程选择", "选修", "课程", "报名", "选择课程"],
            "课程": ["选课", "科目", "学科", "课"],
            "选修": ["选课", "选择", "报名"],
            
            # 考试相关
            "考试": ["测试", "考核", "评估", "测验", "期末", "期中"],
            "测试": ["考试", "考核", "检测"],
            "成绩": ["分数", "得分", "评分", "结果"],
            
            # 申请相关
            "申请": ["报名", "提交", "办理", "申报"],
            "报名": ["申请", "注册", "登记"],
            "办理": ["申请", "处理", "操作"],
            
            # 专业相关
            "转专业": ["专业转换", "换专业", "专业调整"],
            "专业": ["学科", "方向", "领域"],
            
            # 毕业相关
            "毕业": ["毕业生", "完成学业", "结业"],
            "毕业设计": ["毕业论文", "论文", "设计", "答辩"],
            "论文": ["毕业设计", "设计", "研究"],
            "答辩": ["毕业设计", "论文", "评审"],
            
            # 学分相关
            "学分": ["学时", "分数", "积分"],
            "学时": ["学分", "课时", "时间"],
            
            # 奖学金相关
            "奖学金": ["助学金", "奖励", "资助"],
            "助学金": ["奖学金", "资助", "补助"],
            
            # 实习相关
            "实习": ["实践", "实训", "工作"],
            "实践": ["实习", "实训", "操作"],
            
            # 通知相关
            "通知": ["公告", "消息", "信息", "公示"],
            "公告": ["通知", "公示", "消息"],
            "安排": ["计划", "时间", "日程"],
            
            # 时间相关
            "时间": ["日期", "安排", "计划", "日程"],
            "日期": ["时间", "日程"],
            "截止": ["结束", "最后", "期限"],
            
            # 地点相关
            "地点": ["位置", "场所", "教室"],
            "教室": ["地点", "位置", "场所"],
            
            # 要求相关
            "要求": ["条件", "标准", "规定"],
            "条件": ["要求", "标准", "规定"],
            "规定": ["要求", "条件", "标准"],
            
            # 流程相关
            "流程": ["步骤", "程序", "过程"],
            "步骤": ["流程", "程序", "过程"],
            "程序": ["流程", "步骤", "过程"]
        }
        
        # 停用词
        self.stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", 
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
            "着", "没有", "看", "好", "自己", "这", "那", "什么", "怎么", "如何"
        }
        
        logger.info("查询扩展服务初始化完成")
    
    def expand_query(self, query: str, max_expansions: int = 3) -> str:
        """扩展查询，添加同义词"""
        try:
            # 清理查询
            cleaned_query = self._clean_query(query)
            
            # 提取关键词
            keywords = self._extract_keywords(cleaned_query)
            
            # 扩展关键词
            expanded_terms = set([cleaned_query])  # 包含原查询
            
            for keyword in keywords:
                if keyword in self.synonyms:
                    synonyms = self.synonyms[keyword][:max_expansions]
                    for synonym in synonyms:
                        # 创建扩展查询
                        expanded_query = cleaned_query.replace(keyword, synonym)
                        expanded_terms.add(expanded_query)
            
            # 组合扩展查询
            final_query = " ".join(expanded_terms)
            
            logger.debug(f"查询扩展: '{query}' -> '{final_query}'")
            return final_query
            
        except Exception as e:
            logger.warning(f"查询扩展失败: {e}")
            return query
    
    def get_synonyms(self, word: str) -> List[str]:
        """获取单词的同义词"""
        return self.synonyms.get(word, [])
    
    def rewrite_query(self, query: str) -> List[str]:
        """查询重写，生成多个查询变体"""
        try:
            rewrites = [query]  # 包含原查询
            
            # 清理查询
            cleaned_query = self._clean_query(query)
            keywords = self._extract_keywords(cleaned_query)
            
            # 生成同义词替换的查询变体
            for keyword in keywords:
                if keyword in self.synonyms:
                    for synonym in self.synonyms[keyword][:2]:  # 限制每个词最多2个同义词
                        rewrite = cleaned_query.replace(keyword, synonym)
                        if rewrite not in rewrites:
                            rewrites.append(rewrite)
            
            # 生成关键词组合查询
            if len(keywords) > 1:
                # 关键词组合
                keyword_combo = " ".join(keywords)
                if keyword_combo not in rewrites:
                    rewrites.append(keyword_combo)
            
            logger.debug(f"查询重写: '{query}' -> {len(rewrites)} 个变体")
            return rewrites[:5]  # 最多返回5个变体
            
        except Exception as e:
            logger.warning(f"查询重写失败: {e}")
            return [query]
    
    def _clean_query(self, query: str) -> str:
        """清理查询文本"""
        # 去除特殊字符，保留中文、英文、数字
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', query)
        
        # 去除多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取：分词并去除停用词
        words = query.split()
        keywords = []
        
        for word in words:
            word = word.strip()
            if len(word) > 1 and word not in self.stop_words:
                keywords.append(word)
        
        return keywords
    
    def enhance_query_with_context(self, query: str, context_keywords: List[str] = None) -> str:
        """基于上下文增强查询"""
        try:
            enhanced_query = query
            
            if context_keywords:
                # 添加相关的上下文关键词
                relevant_context = []
                query_keywords = self._extract_keywords(query)
                
                for ctx_word in context_keywords:
                    # 检查上下文词是否与查询相关
                    if any(ctx_word in self.synonyms.get(qword, []) for qword in query_keywords):
                        relevant_context.append(ctx_word)
                
                if relevant_context:
                    enhanced_query = f"{query} {' '.join(relevant_context[:2])}"
            
            logger.debug(f"上下文增强: '{query}' -> '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.warning(f"上下文增强失败: {e}")
            return query
    
    def get_expansion_stats(self) -> Dict[str, int]:
        """获取扩展服务统计信息"""
        return {
            "synonym_categories": len(self.synonyms),
            "total_synonyms": sum(len(syns) for syns in self.synonyms.values()),
            "stop_words_count": len(self.stop_words)
        }

# 全局查询扩展服务实例
query_expansion_service = QueryExpansionService()

class EnhancedRetrievalEngine:
    """增强的检索引擎，集成查询扩展"""
    
    def __init__(self, base_retrieval_engine, query_expansion_service):
        self.base_engine = base_retrieval_engine
        self.expansion_service = query_expansion_service
    
    def search_with_expansion(
        self,
        query: str,
        top_k: int = 5,
        use_expansion: bool = True,
        use_rewrite: bool = True,
        **kwargs
    ) -> List[Dict]:
        """带查询扩展的检索"""
        try:
            all_results = []
            
            if use_expansion:
                # 1. 扩展查询检索
                expanded_query = self.expansion_service.expand_query(query)
                expanded_results = self.base_engine.search_cached(expanded_query, top_k * 2, **kwargs)
                all_results.extend(expanded_results)
            
            if use_rewrite:
                # 2. 查询重写检索
                rewritten_queries = self.expansion_service.rewrite_query(query)
                for rewrite in rewritten_queries[1:]:  # 跳过原查询
                    rewrite_results = self.base_engine.search_cached(rewrite, top_k, **kwargs)
                    all_results.extend(rewrite_results)
            
            # 3. 原查询检索
            original_results = self.base_engine.search_cached(query, top_k, **kwargs)
            all_results.extend(original_results)
            
            # 4. 去重和重排
            unique_results = self._deduplicate_results(all_results)
            final_results = unique_results[:top_k]
            
            logger.info(f"扩展检索完成: 原查询+扩展 -> {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            logger.error(f"扩展检索失败: {e}")
            # 降级到原始检索
            return self.base_engine.search_cached(query, top_k, **kwargs)
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重结果"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            doc_id = result.get("id")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)
        
        # 按分数排序
        unique_results.sort(key=lambda x: x.get("score", x.get("similarity_score", 0)), reverse=True)
        
        return unique_results
