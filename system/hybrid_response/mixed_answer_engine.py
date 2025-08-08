#!/usr/bin/env python3
"""
混合回答引擎 - USTB混合云架构核心组件
实现微调模型基础回答与RAG系统附件链接的智能合并

创建时间: 2025-08-06 02:15
创建者: 系统集成专家
状态: 模型训练期间并行开发
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """回答类型枚举"""
    MODEL_ONLY = "model_only"
    RAG_ONLY = "rag_only" 
    MIXED = "mixed"
    CACHED = "cached"

@dataclass
class ModelResponse:
    """模型推理响应"""
    content: str
    confidence: float
    response_time: float
    model_name: str
    
@dataclass
class RAGResponse:
    """RAG检索响应"""
    content: str
    documents: List[Dict]
    attachments: List[Dict]
    relevance_score: float
    response_time: float

@dataclass
class MixedResponse:
    """混合回答响应"""
    final_answer: str
    model_response: ModelResponse
    rag_response: RAGResponse
    response_type: ResponseType
    total_response_time: float
    quality_score: float

class MixedAnswerEngine:
    """混合回答引擎"""
    
    def __init__(self,
                 model_service_url: str = "http://localhost:8081",  # 更新为实际SSH隧道端口
                 rag_service_url: str = "http://localhost:8000",
                 fallback_mode: bool = True):
        self.model_service_url = model_service_url
        self.rag_service_url = rag_service_url
        self.fallback_mode = fallback_mode  # 支持降级模式
        self.response_cache = {}
        self.cache_ttl = 300  # 5分钟缓存

        # 配置参数
        self.config = {
            "model_weight": 0.6,  # 模型回答权重
            "rag_weight": 0.4,    # RAG检索权重
            "min_confidence": 0.7,  # 最小置信度阈值
            "max_response_time": 5.0,  # 最大响应时间(秒)
            "enable_cache": True,
            "parallel_calls": True,
            "fallback_to_rag_only": True,  # 模型服务不可用时降级到RAG
            "retry_attempts": 2  # 重试次数
        }
        
    async def generate_mixed_response(self, query: str, 
                                    user_context: Dict = None) -> MixedResponse:
        """生成混合回答"""
        start_time = time.time()
        
        try:
            logger.info(f"开始生成混合回答: {query[:50]}...")
            
            # 检查缓存
            if self.config["enable_cache"]:
                cached_response = self._get_cached_response(query)
                if cached_response:
                    logger.info("返回缓存回答")
                    return cached_response
            
            # 并行调用模型和RAG服务（支持降级）
            if self.config["parallel_calls"]:
                model_response, rag_response = await self._parallel_call_with_fallback(query, user_context)
            else:
                model_response = await self._call_model_service(query, user_context)
                rag_response = await self._call_rag_service(query)
            
            # 智能合并回答
            mixed_response = await self._merge_responses(
                query, model_response, rag_response, start_time
            )
            
            # 缓存结果
            if self.config["enable_cache"]:
                self._cache_response(query, mixed_response)
            
            logger.info(f"混合回答生成完成，耗时: {mixed_response.total_response_time:.2f}秒")
            return mixed_response
            
        except Exception as e:
            logger.error(f"生成混合回答异常: {str(e)}")
            # 返回错误回答
            return self._create_error_response(query, str(e), start_time)
    
    async def _parallel_call(self, query: str, 
                           user_context: Dict = None) -> Tuple[ModelResponse, RAGResponse]:
        """并行调用模型和RAG服务"""
        try:
            # 创建并行任务
            model_task = asyncio.create_task(
                self._call_model_service(query, user_context)
            )
            rag_task = asyncio.create_task(
                self._call_rag_service(query)
            )
            
            # 等待两个任务完成
            model_response, rag_response = await asyncio.gather(
                model_task, rag_task, return_exceptions=True
            )
            
            # 处理异常情况
            if isinstance(model_response, Exception):
                logger.error(f"模型服务调用失败: {model_response}")
                model_response = self._create_fallback_model_response()
                
            if isinstance(rag_response, Exception):
                logger.error(f"RAG服务调用失败: {rag_response}")
                rag_response = self._create_fallback_rag_response()
            
            return model_response, rag_response
            
        except Exception as e:
            logger.error(f"并行调用异常: {str(e)}")
            # 返回备用响应
            return (self._create_fallback_model_response(),
                   self._create_fallback_rag_response())

    async def _parallel_call_with_fallback(self, query: str,
                                         user_context: Dict = None) -> Tuple[ModelResponse, RAGResponse]:
        """并行调用模型和RAG服务（支持降级）"""
        try:
            # 创建并行任务
            model_task = asyncio.create_task(
                self._call_model_service_with_retry(query, user_context)
            )
            rag_task = asyncio.create_task(
                self._call_rag_service_with_retry(query)
            )

            # 等待两个任务完成
            model_response, rag_response = await asyncio.gather(
                model_task, rag_task, return_exceptions=True
            )

            # 处理异常情况和降级
            if isinstance(model_response, Exception):
                logger.error(f"模型服务调用失败: {model_response}")
                if self.config["fallback_to_rag_only"]:
                    logger.info("启用RAG-only降级模式")
                    model_response = self._create_fallback_model_response()
                else:
                    model_response = self._create_fallback_model_response()

            if isinstance(rag_response, Exception):
                logger.error(f"RAG服务调用失败: {rag_response}")
                rag_response = self._create_fallback_rag_response()

            return model_response, rag_response

        except Exception as e:
            logger.error(f"并行调用异常: {str(e)}")
            return (self._create_fallback_model_response(),
                   self._create_fallback_rag_response())

    async def _call_model_service_with_retry(self, query: str,
                                           user_context: Dict = None) -> ModelResponse:
        """带重试的模型服务调用"""
        last_exception = None

        for attempt in range(self.config["retry_attempts"]):
            try:
                return await self._call_model_service(query, user_context)
            except Exception as e:
                last_exception = e
                if attempt < self.config["retry_attempts"] - 1:
                    logger.warning(f"模型服务调用失败，重试 {attempt + 1}/{self.config['retry_attempts']}")
                    await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避

        raise last_exception

    async def _call_rag_service_with_retry(self, query: str) -> RAGResponse:
        """带重试的RAG服务调用"""
        last_exception = None

        for attempt in range(self.config["retry_attempts"]):
            try:
                return await self._call_rag_service(query)
            except Exception as e:
                last_exception = e
                if attempt < self.config["retry_attempts"] - 1:
                    logger.warning(f"RAG服务调用失败，重试 {attempt + 1}/{self.config['retry_attempts']}")
                    await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避

        raise last_exception
    
    async def _call_model_service(self, query: str, 
                                user_context: Dict = None) -> ModelResponse:
        """调用模型推理服务"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "context": user_context or {},
                    "max_tokens": 512,
                    "temperature": 0.7
                }
                
                async with session.post(
                    f"{self.model_service_url}/api/v1/inference",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        response_time = time.time() - start_time
                        
                        return ModelResponse(
                            content=data.get("response", ""),
                            confidence=data.get("confidence", 0.8),
                            response_time=response_time,
                            model_name=data.get("model_name", "DeepSeek-R1")
                        )
                    else:
                        logger.error(f"模型服务返回错误: {response.status}")
                        return self._create_fallback_model_response()
                        
        except Exception as e:
            logger.error(f"调用模型服务异常: {str(e)}")
            return self._create_fallback_model_response()
    
    async def _call_rag_service(self, query: str) -> RAGResponse:
        """调用RAG检索服务"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "top_k": 5,
                    "include_attachments": True
                }
                
                async with session.post(
                    f"{self.rag_service_url}/api/v1/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        response_time = time.time() - start_time
                        
                        return RAGResponse(
                            content=data.get("summary", ""),
                            documents=data.get("documents", []),
                            attachments=data.get("attachments", []),
                            relevance_score=data.get("relevance_score", 0.7),
                            response_time=response_time
                        )
                    else:
                        logger.error(f"RAG服务返回错误: {response.status}")
                        return self._create_fallback_rag_response()
                        
        except Exception as e:
            logger.error(f"调用RAG服务异常: {str(e)}")
            return self._create_fallback_rag_response()
    
    async def _merge_responses(self, query: str, 
                             model_response: ModelResponse,
                             rag_response: RAGResponse,
                             start_time: float) -> MixedResponse:
        """智能合并回答"""
        try:
            # 计算总响应时间
            total_time = time.time() - start_time
            
            # 决定回答策略
            response_type = self._determine_response_type(model_response, rag_response)
            
            # 生成最终回答
            final_answer = await self._generate_final_answer(
                query, model_response, rag_response, response_type
            )
            
            # 计算质量评分
            quality_score = self._calculate_quality_score(
                model_response, rag_response, response_type
            )
            
            return MixedResponse(
                final_answer=final_answer,
                model_response=model_response,
                rag_response=rag_response,
                response_type=response_type,
                total_response_time=total_time,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"合并回答异常: {str(e)}")
            return self._create_error_response(query, str(e), start_time)
    
    def _determine_response_type(self, model_response: ModelResponse,
                               rag_response: RAGResponse) -> ResponseType:
        """决定回答类型"""
        # 基于置信度和相关性评分决定策略
        model_conf = model_response.confidence
        rag_relevance = rag_response.relevance_score
        
        if model_conf >= 0.8 and rag_relevance >= 0.8:
            return ResponseType.MIXED
        elif model_conf >= 0.7 and rag_relevance < 0.6:
            return ResponseType.MODEL_ONLY
        elif model_conf < 0.6 and rag_relevance >= 0.7:
            return ResponseType.RAG_ONLY
        else:
            return ResponseType.MIXED  # 默认混合
    
    async def _generate_final_answer(self, query: str,
                                   model_response: ModelResponse,
                                   rag_response: RAGResponse,
                                   response_type: ResponseType) -> str:
        """生成最终回答"""
        if response_type == ResponseType.MODEL_ONLY:
            return model_response.content
        
        elif response_type == ResponseType.RAG_ONLY:
            return self._format_rag_only_answer(rag_response)
        
        else:  # MIXED
            return self._format_mixed_answer(model_response, rag_response)
    
    def _format_mixed_answer(self, model_response: ModelResponse,
                           rag_response: RAGResponse) -> str:
        """格式化混合回答"""
        answer_parts = []
        
        # 添加模型基础回答
        if model_response.content:
            answer_parts.append(model_response.content)
        
        # 添加相关文档信息
        if rag_response.documents:
            answer_parts.append("\n\n📚 **相关文档**:")
            for i, doc in enumerate(rag_response.documents[:3], 1):
                title = doc.get("title", "未知文档")
                answer_parts.append(f"{i}. {title}")
        
        # 添加附件链接
        if rag_response.attachments:
            answer_parts.append("\n\n📎 **相关附件**:")
            for attachment in rag_response.attachments[:5]:
                name = attachment.get("name", "附件")
                url = attachment.get("url", "#")
                answer_parts.append(f"- [{name}]({url})")
        
        return "\n".join(answer_parts)
    
    def _format_rag_only_answer(self, rag_response: RAGResponse) -> str:
        """格式化RAG专用回答"""
        answer_parts = []
        
        if rag_response.content:
            answer_parts.append(rag_response.content)
        
        # 添加文档来源
        if rag_response.documents:
            answer_parts.append("\n\n📖 **信息来源**:")
            for doc in rag_response.documents[:3]:
                title = doc.get("title", "相关文档")
                answer_parts.append(f"- {title}")
        
        return "\n".join(answer_parts)
    
    def _calculate_quality_score(self, model_response: ModelResponse,
                               rag_response: RAGResponse,
                               response_type: ResponseType) -> float:
        """计算回答质量评分"""
        # 基于多个因素计算质量评分
        model_score = model_response.confidence * self.config["model_weight"]
        rag_score = rag_response.relevance_score * self.config["rag_weight"]
        
        # 响应时间惩罚
        time_penalty = 0
        total_time = model_response.response_time + rag_response.response_time
        if total_time > self.config["max_response_time"]:
            time_penalty = 0.1
        
        return max(0, min(1, model_score + rag_score - time_penalty))
    
    def _create_fallback_model_response(self) -> ModelResponse:
        """创建备用模型响应"""
        return ModelResponse(
            content="抱歉，模型服务暂时不可用，请稍后重试。",
            confidence=0.1,
            response_time=0.0,
            model_name="fallback"
        )
    
    def _create_fallback_rag_response(self) -> RAGResponse:
        """创建备用RAG响应"""
        return RAGResponse(
            content="",
            documents=[],
            attachments=[],
            relevance_score=0.0,
            response_time=0.0
        )
    
    def _create_error_response(self, query: str, error: str, 
                             start_time: float) -> MixedResponse:
        """创建错误响应"""
        return MixedResponse(
            final_answer=f"抱歉，处理您的问题时出现错误: {error}",
            model_response=self._create_fallback_model_response(),
            rag_response=self._create_fallback_rag_response(),
            response_type=ResponseType.MODEL_ONLY,
            total_response_time=time.time() - start_time,
            quality_score=0.0
        )
    
    def _get_cached_response(self, query: str) -> Optional[MixedResponse]:
        """获取缓存响应"""
        cache_key = hash(query)
        if cache_key in self.response_cache:
            cached_data, timestamp = self.response_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                cached_data.response_type = ResponseType.CACHED
                return cached_data
            else:
                del self.response_cache[cache_key]
        return None
    
    def _cache_response(self, query: str, response: MixedResponse):
        """缓存响应"""
        cache_key = hash(query)
        self.response_cache[cache_key] = (response, time.time())
        
        # 清理过期缓存
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.response_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.response_cache[key]

# 使用示例
async def main():
    """主函数示例"""
    engine = MixedAnswerEngine()
    
    # 测试查询
    query = "如何进行选课？"
    
    try:
        response = await engine.generate_mixed_response(query)
        print(f"查询: {query}")
        print(f"回答: {response.final_answer}")
        print(f"类型: {response.response_type.value}")
        print(f"质量评分: {response.quality_score:.2f}")
        print(f"响应时间: {response.total_response_time:.2f}秒")
        
    except Exception as e:
        print(f"测试异常: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
