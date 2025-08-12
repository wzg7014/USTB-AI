"""
USTB RAG系统 - BCE嵌入模型服务
严格按照8专家分工文档要求实现：BCE-embedding-base_v1
AutoDL GPU加速版本 - RTX 4090优化
"""
import os
import time
from typing import List, Union
import numpy as np
import torch

# 设置离线模式，避免连接huggingface.co
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

from sentence_transformers import SentenceTransformer
from loguru import logger

class EmbeddingService:
    """嵌入服务类 - AutoDL GPU加速版"""
    
    def __init__(self):
        # 模型配置 - AutoDL GPU优化
        self.model_name = "/root/autodl-tmp/ustb-project/models/bce-embedding-base_v1"
        
        # GPU配置 - RTX 4090优化
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.batch_size = 256 if self.device == "cuda" else 128  # GPU加大批处理
        self.vector_size = 768  # BCE-embedding-base_v1向量维度

        # 缓存配置
        self.query_cache = {}  # 查询缓存
        self.cache_max_size = 2000  # GPU环境增大缓存

        # 加载模型
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载BCE嵌入模型 - GPU优化"""
        try:
            logger.info(f"正在加载BCE嵌入模型: {self.model_name}")
            logger.info(f"使用设备: {self.device}")
            
            if self.device == "cuda":
                logger.info(f"GPU信息: {torch.cuda.get_device_name(0)}")
                logger.info(f"显存信息: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
            
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
            logger.error(f"模型加载失败: {str(e)}")
            raise
    
    def _warmup_model(self):
        """模型预热 - GPU优化"""
        try:
            logger.info("正在预热模型...")
            start_time = time.time()
            
            # 预热文本
            warmup_texts = [
                "北京科技大学教务系统",
                "选课通知和成绩查询",
                "转专业申请流程"
            ]
            
            # 执行预热
            embeddings = self.model.encode(warmup_texts, batch_size=self.batch_size)
            
            warmup_time = time.time() - start_time
            logger.info(f"模型预热完成，耗时: {warmup_time:.2f}秒")
            logger.info(f"输出向量维度: {embeddings.shape}")
            
            if self.device == "cuda":
                logger.info(f"当前显存使用: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB")
            
        except Exception as e:
            logger.error(f"模型预热失败: {str(e)}")
    
    def encode_texts(self, texts: Union[str, List[str]], use_cache: bool = True) -> np.ndarray:
        """编码文本为向量 - GPU加速版"""
        if isinstance(texts, str):
            texts = [texts]
        
        # 缓存检查
        if use_cache and len(texts) == 1:
            cache_key = texts[0]
            if cache_key in self.query_cache:
                return self.query_cache[cache_key]
        
        try:
            start_time = time.time()
            
            # GPU加速编码
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            encode_time = time.time() - start_time
            
            # 缓存管理
            if use_cache and len(texts) == 1:
                if len(self.query_cache) >= self.cache_max_size:
                    # 清理最旧缓存
                    oldest_key = next(iter(self.query_cache))
                    del self.query_cache[oldest_key]
                
                self.query_cache[cache_key] = embeddings
            
            logger.debug(f"编码{len(texts)}个文本，耗时: {encode_time:.3f}秒")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"文本编码失败: {str(e)}")
            raise
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        gpu_info = {}
        if self.device == "cuda" and torch.cuda.is_available():
            gpu_info = {
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB",
                "gpu_memory_used": f"{torch.cuda.memory_allocated(0) / 1024**3:.2f}GB"
            }
        
        return {
            "model_name": self.model_name,
            "device": self.device,
            "vector_size": self.vector_size,
            "batch_size": self.batch_size,
            "cache_size": len(self.query_cache),
            "cache_max_size": self.cache_max_size,
            **gpu_info
        }
    
    def clear_cache(self):
        """清理缓存"""
        self.query_cache.clear()
        logger.info("缓存已清理")

# 全局实例
embedding_service = EmbeddingService()
