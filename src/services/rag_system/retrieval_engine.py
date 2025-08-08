"""
USTB RAG系统 - 检索引擎核心逻辑
严格按照8专家分工文档要求实现
"""
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from loguru import logger

# 导入本地模块
from vector_store import vector_store
from embedding_service import embedding_service

class RetrievalEngine:
    """检索引擎类"""
    
    def __init__(self):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        
        # 数据路径
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.rag_data_file = self.project_root / "data" / "processed" / "rag_data.json"
        
        logger.info("检索引擎初始化完成")
    
    def load_and_index_documents(self) -> int:
        """加载并索引RAG检索数据集"""
        try:
            logger.info("开始加载RAG检索数据集")
            
            # 检查数据文件是否存在
            if not self.rag_data_file.exists():
                raise FileNotFoundError(f"RAG数据文件不存在: {self.rag_data_file}")
            
            # 加载数据
            with open(self.rag_data_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            logger.info(f"加载了 {len(documents)} 条文档")
            
            # 准备文档文本用于向量化
            doc_texts = []
            for doc in documents:
                # 组合标题和内容作为向量化文本
                text = f"标题: {doc['title']}\n内容: {doc['content']}"
                doc_texts.append(text)
            
            # 批量向量化
            logger.info("开始文档向量化...")
            start_time = time.time()
            
            embeddings = self.embedding_service.encode_documents(doc_texts)
            
            embed_time = time.time() - start_time
            logger.info(f"文档向量化完成，耗时: {embed_time:.2f}秒")
            
            # 添加到向量数据库
            self.vector_store.add_documents(documents, embeddings)
            
            logger.info(f"成功索引 {len(documents)} 个文档")
            return len(documents)
            
        except Exception as e:
            logger.error(f"文档加载和索引失败: {str(e)}")
            raise
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[List[str]] = None,
        date_range: Optional[List[str]] = None,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """执行检索"""
        try:
            logger.info(f"执行检索查询: {query}")
            start_time = time.time()
            
            # 查询向量化
            query_embedding = self.embedding_service.encode_query(query)
            
            # 向量检索 - 检索更多候选结果
            candidate_count = max(top_k * 2, 10)  # 至少检索10个候选
            raw_results = self.vector_store.search(
                query_vector=query_embedding,
                top_k=candidate_count,
                category_filter=category_filter,
                date_range=date_range,
                similarity_threshold=similarity_threshold
            )
            
            # 结果后处理和重排
            processed_results = self._post_process_results(raw_results, query)

            # 重排并截取到目标数量
            reranked_results = self._rerank_results(processed_results, query)
            final_results = reranked_results[:top_k]

            search_time = time.time() - start_time
            logger.info(f"检索完成，候选 {len(processed_results)} 个，返回 {len(final_results)} 个结果，耗时: {search_time:.3f}秒")

            return final_results
            
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []
    
    def _post_process_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """结果后处理"""
        processed_results = []
        
        for result in results:
            # 转换为标准格式
            processed_result = {
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "score": result["similarity_score"],
                "category": result["category"],
                "url": result["url"],
                "attachments": self._format_attachments(result.get("attachments", []))
            }
            
            processed_results.append(processed_result)
        
        # 按相似度排序
        processed_results.sort(key=lambda x: x["score"], reverse=True)
        
        return processed_results
    
    def _format_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """格式化附件信息"""
        formatted_attachments = []
        
        for att in attachments:
            if isinstance(att, dict) and "title" in att and "url" in att:
                formatted_attachments.append({
                    "title": att["title"],
                    "url": att["url"]
                })
        
        return formatted_attachments
    
    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """纯语义检索"""
        return self.search(
            query=query,
            top_k=top_k,
            similarity_threshold=0.6  # 降低阈值获取更多结果
        )
    
    def category_search(self, query: str, categories: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """分类检索"""
        return self.search(
            query=query,
            top_k=top_k,
            category_filter=categories
        )
    
    def simple_hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """简单混合检索：语义检索 + 关键词过滤"""
        # 先进行语义检索
        semantic_results = self.semantic_search(query, top_k * 2)

        # 关键词过滤和重排序
        filtered_results = self._keyword_filter(semantic_results, query)

        # 返回top_k结果
        return filtered_results[:top_k]
    
    def _keyword_filter(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """关键词过滤和重排序"""
        # 简单的关键词匹配加权
        query_keywords = query.lower().split()
        
        for result in results:
            keyword_score = 0
            text = (result["title"] + " " + result["content"]).lower()
            
            for keyword in query_keywords:
                if keyword in text:
                    keyword_score += 1
            
            # 结合语义相似度和关键词匹配
            result["final_score"] = result["score"] * 0.7 + (keyword_score / len(query_keywords)) * 0.3
        
        # 按最终得分排序
        results.sort(key=lambda x: x.get("final_score", x["score"]), reverse=True)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取检索引擎统计信息"""
        collection_info = self.vector_store.get_collection_info()
        model_info = self.embedding_service.get_model_info()
        
        return {
            "collection_info": collection_info,
            "embedding_model": model_info,
            "data_file": str(self.rag_data_file),
            "data_file_exists": self.rag_data_file.exists()
        }

    def _rerank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """重排检索结果，提升质量"""
        if not results:
            return results

        # 计算查询关键词
        query_keywords = [word.lower() for word in query.split() if len(word) > 1]

        # 为每个结果计算综合得分
        for result in results:
            # 基础相似度得分
            similarity_score = result.get("similarity_score", 0.0)

            # 关键词匹配得分
            text = (result.get("title", "") + " " + result.get("content", "")).lower()
            keyword_matches = sum(1 for keyword in query_keywords if keyword in text)
            keyword_score = keyword_matches / max(len(query_keywords), 1)

            # Qwen质量得分
            qwen_score = result.get("qwen_score", 0.0) / 10.0  # 归一化到0-1

            # 综合得分：相似度60% + 关键词30% + 质量10%
            final_score = (similarity_score * 0.6 +
                          keyword_score * 0.3 +
                          qwen_score * 0.1)

            result["rerank_score"] = final_score

        # 按重排得分排序
        results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return results

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[List[str]] = None,
        date_range: Optional[List[str]] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """混合检索：向量检索 + 关键词检索"""
        try:
            logger.info(f"执行混合检索: {query}")
            start_time = time.time()

            # 1. 向量检索 - 获取更多候选
            vector_results = self.search(
                query=query,
                top_k=top_k * 3,  # 获取3倍候选
                category_filter=category_filter,
                date_range=date_range,
                similarity_threshold=0.2  # 降低阈值
            )

            # 2. 关键词检索
            keyword_results = self._keyword_search(
                query=query,
                top_k=top_k * 2,
                category_filter=category_filter,
                date_range=date_range
            )

            # 3. 结果融合
            merged_results = self._merge_search_results(
                vector_results, keyword_results,
                vector_weight, keyword_weight
            )

            # 4. 重排和截取
            final_results = merged_results[:top_k]

            search_time = time.time() - start_time
            logger.info(f"混合检索完成，返回 {len(final_results)} 个结果，耗时: {search_time:.3f}秒")

            return final_results

        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            # 降级到普通向量检索
            return self.search(query, top_k, category_filter, date_range)

    def _keyword_search(
        self,
        query: str,
        top_k: int = 10,
        category_filter: Optional[List[str]] = None,
        date_range: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """关键词检索 - 简化版本"""
        try:
            # 获取所有文档进行关键词匹配
            all_results = self.search(
                query="",  # 空查询获取所有文档
                top_k=1000,  # 获取大量文档
                category_filter=category_filter,
                date_range=date_range,
                similarity_threshold=0.0  # 最低阈值
            )

            # 关键词匹配
            query_keywords = [word.lower().strip() for word in query.split() if len(word.strip()) > 1]
            keyword_results = []

            for result in all_results:
                text = (result.get("title", "") + " " + result.get("content", "")).lower()

                # 计算关键词匹配分数
                matches = 0
                for keyword in query_keywords:
                    if keyword in text:
                        matches += text.count(keyword)

                if matches > 0:
                    result_copy = result.copy()
                    result_copy["keyword_matches"] = matches
                    result_copy["keyword_score"] = matches / len(query_keywords)
                    result_copy["search_type"] = "keyword"
                    keyword_results.append(result_copy)

            # 按关键词匹配分数排序
            keyword_results.sort(key=lambda x: x["keyword_score"], reverse=True)

            return keyword_results[:top_k]

        except Exception as e:
            logger.warning(f"关键词检索失败: {str(e)}")
            return []

    def _merge_search_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """融合向量检索和关键词检索结果"""
        merged_dict = {}

        # 处理向量检索结果
        for i, result in enumerate(vector_results):
            doc_id = result.get("id", f"vector_{i}")
            # 向量检索得分
            vector_score = result.get("score", result.get("similarity_score", 0)) * vector_weight
            position_bonus = (len(vector_results) - i) / len(vector_results) * 0.1

            merged_dict[doc_id] = {
                **result,
                "vector_score": vector_score,
                "keyword_score": 0,
                "position_bonus": position_bonus,
                "final_score": vector_score + position_bonus,
                "search_types": ["vector"]
            }

        # 处理关键词检索结果
        for i, result in enumerate(keyword_results):
            doc_id = result.get("id", f"keyword_{i}")
            # 关键词检索得分
            keyword_score = result.get("keyword_score", 0.5) * keyword_weight
            position_bonus = (len(keyword_results) - i) / len(keyword_results) * 0.05

            if doc_id in merged_dict:
                # 文档已存在，更新分数
                merged_dict[doc_id]["keyword_score"] = keyword_score
                merged_dict[doc_id]["final_score"] += keyword_score
                merged_dict[doc_id]["search_types"].append("keyword")
            else:
                # 新文档
                merged_dict[doc_id] = {
                    **result,
                    "vector_score": 0,
                    "keyword_score": keyword_score,
                    "position_bonus": position_bonus,
                    "final_score": keyword_score + position_bonus,
                    "search_types": ["keyword"]
                }

        # 按最终得分排序
        merged_results = list(merged_dict.values())
        merged_results.sort(key=lambda x: x["final_score"], reverse=True)

        return merged_results

# 全局检索引擎实例
retrieval_engine = RetrievalEngine()
