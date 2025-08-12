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
    """向量存储类"""
    
    def __init__(self):
        # 配置参数
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = "ustb_documents"
        self.vector_size = 768  # BCE-embedding-base_v1向量维度
        
        # AutoDL数据目录
        self.vector_data_dir = Path("/root/autodl-tmp/ustb-project/data/vectors")
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
            existing_names = [col.name for col in collections.collections]
            
            if self.collection_name in existing_names:
                logger.info(f"集合 {self.collection_name} 已存在")
                return True
            
            # 创建新集合
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"集合 {self.collection_name} 创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {"error": str(e)}

# 全局实例
vector_store = VectorStore()
