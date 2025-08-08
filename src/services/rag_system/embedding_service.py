"""
USTB RAG系统 - BCE嵌入模型服务
严格按照8专家分工文档要求实现：BCE-embedding-base_v1
"""
import os
import time
from typing import List, Union
import numpy as np

# 设置离线模式，避免连接huggingface.co
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

from sentence_transformers import SentenceTransformer
from loguru import logger

class EmbeddingService:
    """BCE嵌入服务类"""
    
    def __init__(self):
        # 模型配置 - 严格按照技术方案
        self.model_name = "maidalun1020/bce-embedding-base_v1"
        self.device = "cpu"  # 可根据环境调整为 "cuda"
        self.batch_size = 128  # 优化批处理大小
        self.vector_size = 768  # BCE-embedding-base_v1向量维度

        # 缓存配置
        self.query_cache = {}  # 查询缓存
        self.cache_max_size = 1000  # 最大缓存数量

        # 加载模型
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载BCE嵌入模型"""
        try:
            logger.info(f"正在加载BCE嵌入模型: {self.model_name}")
            start_time = time.time()

            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )

            load_time = time.time() - start_time
            logger.info(f"BCE嵌入模型加载完成，耗时: {load_time:.2f}秒")

            # 模型预热
            self._warmup_model()

        except Exception as e:
            logger.error(f"BCE嵌入模型加载失败: {str(e)}")
            raise

    def _warmup_model(self):
        """模型预热，提升首次推理速度"""
        try:
            logger.info("开始模型预热...")
            warmup_start = time.time()

            # 预热文本
            warmup_texts = [
                "测试文本",
                "查询示例",
                "检索测试",
                "文档内容示例",
                "这是一个用于预热模型的测试文本"
            ]

            # 执行预热
            test_embeddings = self.model.encode(
                warmup_texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=len(warmup_texts)
            )

            warmup_time = time.time() - warmup_start
            logger.info(f"模型预热完成，向量维度: {test_embeddings.shape[1]}，耗时: {warmup_time:.2f}秒")

        except Exception as e:
            logger.warning(f"模型预热失败: {e}")
            # 预热失败不影响正常使用

    def encode_text(self, text: str) -> List[float]:
        """编码单个文本 - 优化版本"""
        if not text or not text.strip():
            logger.warning("输入文本为空，返回零向量")
            return [0.0] * self.vector_size

        try:
            # 使用优化的编码参数
            embedding = self.model.encode(
                [text.strip()],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=1
            )[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"文本编码失败: {str(e)}")
            return [0.0] * self.vector_size
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """批量编码文本"""
        if not texts:
            return []
        
        # 过滤空文本
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            logger.warning("所有输入文本为空")
            return [[0.0] * self.vector_size for _ in texts]
        
        try:
            logger.info(f"开始批量编码 {len(valid_texts)} 个文本")
            start_time = time.time()
            
            # 优化的分批处理
            embeddings = []
            total_batches = (len(valid_texts) + self.batch_size - 1) // self.batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * self.batch_size
                end_idx = min(start_idx + self.batch_size, len(valid_texts))
                batch = valid_texts[start_idx:end_idx]

                # 优化的编码参数
                batch_embeddings = self.model.encode(
                    batch,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # 归一化提升检索效果
                    batch_size=len(batch)  # 动态批大小
                )
                embeddings.extend(batch_embeddings)

                # 进度日志
                if total_batches > 1 and (batch_idx + 1) % max(1, total_batches // 4) == 0:
                    progress = (batch_idx + 1) / total_batches * 100
                    logger.info(f"批处理进度: {progress:.1f}% ({batch_idx + 1}/{total_batches})")
            
            encode_time = time.time() - start_time
            logger.info(f"批量编码完成，耗时: {encode_time:.2f}秒")
            
            # 转换为列表格式
            return [embedding.tolist() for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"批量编码失败: {str(e)}")
            return [[0.0] * self.vector_size for _ in texts]
    
    def encode_documents(self, documents: List[str]) -> List[List[float]]:
        """编码文档列表 - 为文档索引优化"""
        logger.info(f"开始编码 {len(documents)} 个文档")
        
        # 预处理文档文本
        processed_docs = []
        for doc in documents:
            # 限制文档长度，避免超长文本
            if len(doc) > 2000:
                doc = doc[:2000] + "..."
            processed_docs.append(doc)
        
        return self.encode_batch(processed_docs)
    
    def encode_query(self, query: str) -> List[float]:
        """编码查询文本 - 为检索优化"""
        # 查询文本预处理
        if len(query) > 500:
            query = query[:500]
        
        return self.encode_text(query)
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "vector_size": self.vector_size,
            "batch_size": self.batch_size,
            "is_loaded": self.model is not None
        }
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            # 转换为numpy数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"相似度计算失败: {str(e)}")
            return 0.0

# 全局嵌入服务实例
embedding_service = EmbeddingService()
