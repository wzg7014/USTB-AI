"""
USTB RAG系统 - Qdrant向量数据库操作
严格按照8专家分工文档要求实现
"""
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, 
    FieldCondition, MatchValue, Range
)
from loguru import logger

class VectorStore:
    """Qdrant向量存储类"""
    
    def __init__(self):
        # 配置参数
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = "ustb_documents"
        self.vector_size = 768  # BCE-embedding-base_v1向量维度
        
        # 数据目录
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.vector_data_dir = self.project_root / "data" / "vectors"
        self.vector_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化客户端
        self.client = None
        self._connect()
    
    def _connect(self):
        """连接Qdrant数据库"""
        try:
            logger.info(f"连接Qdrant数据库: {self.host}:{self.port}")
            
            # 使用本地存储模式
            self.client = QdrantClient(
                path=str(self.vector_data_dir)  # 本地存储路径
            )
            
            # 测试连接
            collections = self.client.get_collections()
            logger.info(f"Qdrant连接成功，现有集合数: {len(collections.collections)}")
            
        except Exception as e:
            logger.error(f"Qdrant连接失败: {str(e)}")
            raise
    
    def create_collection(self):
        """创建文档集合"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections()
            existing_collections = [col.name for col in collections.collections]
            
            if self.collection_name in existing_collections:
                logger.info(f"集合 {self.collection_name} 已存在")
                return
            
            logger.info(f"创建集合: {self.collection_name}")
            
            # 创建集合 - 优化的HNSW配置
            from qdrant_client.models import HnswConfigDiff, OptimizersConfigDiff

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,  # 余弦相似度
                    hnsw_config=HnswConfigDiff(
                        m=32,  # 增加连接数，提升召回率
                        ef_construct=400,  # 增加构建时搜索深度
                        full_scan_threshold=20000  # 提高全扫描阈值
                    )
                ),
                optimizers_config=OptimizersConfigDiff(
                    default_segment_number=4,  # 增加段数
                    max_segment_size=50000,
                    memmap_threshold=100000,
                    indexing_threshold=20000
                )
            )
            
            logger.info(f"集合 {self.collection_name} 创建成功")
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        """批量添加文档"""
        if len(documents) != len(embeddings):
            raise ValueError("文档数量与嵌入向量数量不匹配")
        
        try:
            logger.info(f"开始添加 {len(documents)} 个文档到向量数据库")
            start_time = time.time()
            
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point = PointStruct(
                    id=i + 1,  # Qdrant需要数字ID
                    vector=embedding,
                    payload={
                        "doc_id": doc["id"],
                        "title": doc["title"],
                        "content": doc["content"][:2000],  # 限制payload大小
                        "url": doc["url"],
                        "category": doc["category"],
                        "publish_date": doc["publish_date"],
                        "attachments": doc.get("attachments", []),
                        "qwen_score": doc.get("qwen_score", 0.0),
                        "data_category": doc.get("data_category", "")
                    }
                )
                points.append(point)
            
            # 批量插入
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            add_time = time.time() - start_time
            logger.info(f"文档添加完成，耗时: {add_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            raise
    
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        category_filter: Optional[List[str]] = None,
        date_range: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """向量检索"""
        try:
            # 构建过滤条件
            filter_conditions = []
            
            if category_filter:
                filter_conditions.append(
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category_filter[0]) if len(category_filter) == 1 
                        else MatchValue(any=category_filter)
                    )
                )
            
            if date_range and len(date_range) == 2:
                filter_conditions.append(
                    FieldCondition(
                        key="publish_date",
                        range=Range(gte=date_range[0], lte=date_range[1])
                    )
                )
            
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # 执行检索 - 优化搜索参数
            from qdrant_client.models import SearchParams

            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=search_filter,
                score_threshold=similarity_threshold,
                search_params=SearchParams(
                    hnsw_ef=256,  # 增加搜索时的ef参数，提升精度
                    exact=False   # 使用近似搜索，提升速度
                )
            )
            
            # 转换结果
            results = []
            for result in search_results:
                payload = result.payload
                result_dict = {
                    "id": payload["doc_id"],
                    "title": payload["title"],
                    "content": payload["content"],
                    "url": payload["url"],
                    "category": payload["category"],
                    "publish_date": payload["publish_date"],
                    "attachments": payload.get("attachments", []),
                    "similarity_score": result.score,
                    "qwen_score": payload.get("qwen_score", 0.0)
                }
                results.append(result_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": self.vector_size
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {}
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant健康检查失败: {str(e)}")
            return False
    
    def delete_collection(self):
        """删除集合"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"集合 {self.collection_name} 已删除")
        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")

# 全局向量存储实例
vector_store = VectorStore()
