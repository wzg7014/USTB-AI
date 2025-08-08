#!/usr/bin/env python3
"""
USTB AI教务助手 - 完整版API接口模块
与RAG系统的API接口集成，实现混合回答机制
专为系统集成专家设计的生产级API接口

功能:
1. LoRA模型推理API封装
2. RAG系统接口调用
3. 混合回答合并逻辑
4. 错误处理和降级机制
5. 完整的FastAPI服务
6. 健康检查和监控
7. 性能统计和日志

创建时间: 2025-08-07
作者: 模型微调专家
状态: 生产就绪
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/autodl-tmp/ustb-project/logs/api_interface.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API请求/响应模型
class HybridInferenceRequest(BaseModel):
    query: str
    strategy: str = "model_primary"
    max_tokens: int = 300
    temperature: float = 0.1
    top_p: float = 0.9
    include_attachments: bool = True
    timeout: int = 30

class HybridInferenceResponse(BaseModel):
    query: str
    primary_response: str
    enhanced_response: Optional[str] = None
    attachments: List[Dict] = []
    confidence: float
    total_time: float
    model_time: float
    rag_time: float
    strategy: str
    timestamp: str
    sources: List[str]
    request_id: str

class ServiceHealthResponse(BaseModel):
    status: str
    lora_service: bool
    rag_service: bool
    uptime: float
    version: str
    timestamp: str

class APIStatsResponse(BaseModel):
    request_count: int
    success_count: int
    error_count: int
    success_rate: float
    average_response_time: float
    supported_strategies: List[str]
    service_status: Dict[str, bool]

@dataclass
class ModelResponse:
    """模型响应数据类"""
    query: str
    response: str
    inference_time: float
    confidence: float
    model_name: str
    tokens_generated: int
    timestamp: str
    source: str = "lora_model"

@dataclass
class RAGResponse:
    """检索增强生成响应数据类"""
    query: str
    response: str
    sources: List[Dict]
    confidence: float
    response_time: float
    timestamp: str
    source: str = "rag_system"

class USTBHybridAPIService:
    """
    USTB AI教务助手混合API服务
    完整的生产级API服务，支持LoRA模型和RAG系统的混合推理
    """
    
    def __init__(self, 
                 lora_service_url: str = "http://localhost:8001",
                 rag_service_url: str = "http://localhost:8000",
                 service_port: int = 8002):
        
        # 服务配置
        self.lora_service_url = lora_service_url
        self.rag_service_url = rag_service_url
        self.service_port = service_port
        self.start_time = time.time()
        
        # 服务状态
        self.lora_available = False
        self.rag_available = False
        
        # 性能统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="USTB AI教务助手 - 混合API服务",
            description="LoRA模型与RAG系统的混合推理API服务",
            version="1.0.0"
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 混合策略配置
        self.hybrid_strategies = {
            "model_primary": self._model_primary_strategy,
            "rag_primary": self._rag_primary_strategy,
            "parallel_merge": self._parallel_merge_strategy,
            "fallback_chain": self._fallback_chain_strategy
        }
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"USTB混合API服务初始化完成")
        logger.info(f"LoRA服务: {self.lora_service_url}")
        logger.info(f"RAG服务: {self.rag_service_url}")
        logger.info(f"API服务端口: {self.service_port}")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/health", response_model=ServiceHealthResponse)
        async def health_check():
            """健康检查接口"""
            health_status = await self.check_services_health()
            
            return ServiceHealthResponse(
                status="healthy" if any(health_status.values()) else "degraded",
                lora_service=health_status.get("lora_service", False),
                rag_service=health_status.get("rag_service", False),
                uptime=time.time() - self.start_time,
                version="1.0.0",
                timestamp=datetime.now().isoformat()
            )
        
        @self.app.post("/api/v1/hybrid_inference", response_model=HybridInferenceResponse)
        async def hybrid_inference(request: HybridInferenceRequest):
            """混合推理主接口"""
            request_id = f"req_{int(time.time() * 1000)}"
            
            try:
                response = await self.hybrid_inference_internal(
                    query=request.query,
                    strategy=request.strategy,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    include_attachments=request.include_attachments,
                    timeout=request.timeout,
                    request_id=request_id
                )
                
                return response
                
            except Exception as e:
                logger.error(f"混合推理失败 [{request_id}]: {str(e)}")
                raise HTTPException(status_code=500, detail=f"推理服务异常: {str(e)}")
        
        @self.app.get("/api/v1/stats", response_model=APIStatsResponse)
        async def get_stats():
            """获取API统计信息"""
            health_status = await self.check_services_health()
            
            return APIStatsResponse(
                request_count=self.request_count,
                success_count=self.success_count,
                error_count=self.error_count,
                success_rate=self.success_count / max(self.request_count, 1) * 100,
                average_response_time=self.total_response_time / max(self.request_count, 1),
                supported_strategies=list(self.hybrid_strategies.keys()),
                service_status=health_status
            )
        
        @self.app.get("/api/v1/strategies")
        async def get_strategies():
            """获取支持的混合策略"""
            return {
                "strategies": list(self.hybrid_strategies.keys()),
                "descriptions": {
                    "model_primary": "模型主导策略：以LoRA模型为主，RAG提供附件链接",
                    "rag_primary": "检索主导策略：以RAG系统为主，模型辅助增强",
                    "parallel_merge": "并行合并策略：同时调用两个服务，智能合并结果",
                    "fallback_chain": "降级链策略：优先模型，失败后降级到RAG"
                }
            }
    
    async def check_services_health(self) -> Dict[str, bool]:
        """检查服务健康状态"""
        health_status = {
            "lora_service": False,
            "rag_service": False
        }
        
        # 检查LoRA服务
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.lora_service_url}/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        health_status["lora_service"] = data.get("model_loaded", False)
                        self.lora_available = health_status["lora_service"]
        except Exception as e:
            logger.debug(f"LoRA服务健康检查失败: {e}")
            self.lora_available = False
        
        # 检查RAG服务
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.rag_service_url}/health", timeout=5) as response:
                    if response.status == 200:
                        health_status["rag_service"] = True
                        self.rag_available = True
        except Exception as e:
            logger.debug(f"RAG服务健康检查失败: {e}")
            self.rag_available = False
        
        return health_status
    
    async def call_lora_model(self, query: str, **kwargs) -> Optional[ModelResponse]:
        """调用LoRA模型推理服务"""
        if not self.lora_available:
            return None
        
        try:
            payload = {
                "query": query,
                "max_tokens": kwargs.get("max_tokens", 300),
                "temperature": kwargs.get("temperature", 0.1),
                "top_p": kwargs.get("top_p", 0.9)
            }
            
            timeout = kwargs.get("timeout", 30)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.lora_service_url}/api/v1/inference",
                    json=payload,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return ModelResponse(
                            query=data["query"],
                            response=data["response"],
                            inference_time=data["inference_time"],
                            confidence=data["confidence"],
                            model_name=data["model_name"],
                            tokens_generated=data["tokens_generated"],
                            timestamp=data["timestamp"]
                        )
                    else:
                        logger.error(f"LoRA模型调用失败: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"LoRA模型调用异常: {e}")
            return None
    
    async def call_rag_system(self, query: str, **kwargs) -> Optional[RAGResponse]:
        """调用RAG检索增强生成系统"""
        if not self.rag_available:
            return None
        
        try:
            payload = {
                "query": query,
                "top_k": kwargs.get("top_k", 5),
                "include_metadata": kwargs.get("include_attachments", True)
            }
            
            timeout = kwargs.get("timeout", 15)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rag_service_url}/api/search",
                    json=payload,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return RAGResponse(
                            query=query,
                            response=data.get("answer", ""),
                            sources=data.get("sources", []),
                            confidence=data.get("confidence", 0.5),
                            response_time=data.get("response_time", 0),
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                        logger.error(f"RAG系统调用失败: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"RAG系统调用异常: {e}")
            return None

    async def _model_primary_strategy(self, query: str, request_id: str, **kwargs) -> HybridInferenceResponse:
        """模型主导策略: 以LoRA模型为主，RAG提供附件链接"""
        start_time = time.time()

        # 并行调用两个服务
        model_task = self.call_lora_model(query, **kwargs)
        rag_task = self.call_rag_system(query, **kwargs) if kwargs.get("include_attachments", True) else None

        if rag_task:
            model_response, rag_response = await asyncio.gather(
                model_task, rag_task, return_exceptions=True
            )
        else:
            model_response = await model_task
            rag_response = None

        # 处理结果
        primary_response = ""
        attachments = []
        confidence = 0.5
        model_time = 0.0
        rag_time = 0.0
        sources = []

        if isinstance(model_response, ModelResponse):
            primary_response = model_response.response
            confidence = model_response.confidence
            model_time = model_response.inference_time
            sources.append("lora_model")

        if isinstance(rag_response, RAGResponse):
            attachments = rag_response.sources
            rag_time = rag_response.response_time
            sources.append("rag_system")

            # 如果模型回答失败，使用RAG作为备选
            if not primary_response and rag_response.response:
                primary_response = rag_response.response
                confidence = rag_response.confidence

        # 如果都失败了，返回错误信息
        if not primary_response:
            primary_response = "抱歉，服务暂时不可用，请稍后再试。"
            confidence = 0.0

        total_time = time.time() - start_time

        return HybridInferenceResponse(
            query=query,
            primary_response=primary_response,
            enhanced_response=None,
            attachments=attachments,
            confidence=confidence,
            total_time=total_time,
            model_time=model_time,
            rag_time=rag_time,
            strategy="model_primary",
            timestamp=datetime.now().isoformat(),
            sources=sources,
            request_id=request_id
        )

    async def _rag_primary_strategy(self, query: str, request_id: str, **kwargs) -> HybridInferenceResponse:
        """检索主导策略: 以RAG系统为主，模型辅助增强"""
        start_time = time.time()

        # 先调用RAG系统
        rag_response = await self.call_rag_system(query, **kwargs)

        primary_response = ""
        enhanced_response = None
        attachments = []
        confidence = 0.5
        model_time = 0.0
        rag_time = 0.0
        sources = []

        if rag_response:
            primary_response = rag_response.response
            attachments = rag_response.sources
            confidence = rag_response.confidence
            rag_time = rag_response.response_time
            sources.append("rag_system")

            # 如果RAG结果不理想，调用模型增强
            if confidence < 0.7:
                model_response = await self.call_lora_model(query, **kwargs)
                if model_response:
                    enhanced_response = f"专业解答: {model_response.response}"
                    confidence = max(confidence, model_response.confidence)
                    model_time = model_response.inference_time
                    sources.append("lora_model")
        else:
            # RAG失败，降级到模型
            model_response = await self.call_lora_model(query, **kwargs)
            if model_response:
                primary_response = model_response.response
                confidence = model_response.confidence
                model_time = model_response.inference_time
                sources.append("lora_model")

        if not primary_response:
            primary_response = "抱歉，服务暂时不可用，请稍后再试。"
            confidence = 0.0

        total_time = time.time() - start_time

        return HybridInferenceResponse(
            query=query,
            primary_response=primary_response,
            enhanced_response=enhanced_response,
            attachments=attachments,
            confidence=confidence,
            total_time=total_time,
            model_time=model_time,
            rag_time=rag_time,
            strategy="rag_primary",
            timestamp=datetime.now().isoformat(),
            sources=sources,
            request_id=request_id
        )

    async def _parallel_merge_strategy(self, query: str, request_id: str, **kwargs) -> HybridInferenceResponse:
        """并行合并策略: 同时调用两个服务，智能合并结果"""
        start_time = time.time()

        # 并行调用
        model_task = self.call_lora_model(query, **kwargs)
        rag_task = self.call_rag_system(query, **kwargs)

        model_response, rag_response = await asyncio.gather(
            model_task, rag_task, return_exceptions=True
        )

        # 智能合并逻辑
        primary_response = ""
        enhanced_response = None
        attachments = []
        confidence = 0.5
        model_time = 0.0
        rag_time = 0.0
        sources = []

        if isinstance(model_response, ModelResponse) and isinstance(rag_response, RAGResponse):
            # 两个服务都成功，智能合并
            if model_response.confidence > rag_response.confidence:
                primary_response = model_response.response
                if rag_response.response:
                    enhanced_response = f"相关资料: {rag_response.response}"
            else:
                primary_response = rag_response.response
                if model_response.response:
                    enhanced_response = f"专业解答: {model_response.response}"

            attachments = rag_response.sources
            confidence = max(model_response.confidence, rag_response.confidence)
            model_time = model_response.inference_time
            rag_time = rag_response.response_time
            sources = ["lora_model", "rag_system"]

        elif isinstance(model_response, ModelResponse):
            # 只有模型成功
            primary_response = model_response.response
            confidence = model_response.confidence
            model_time = model_response.inference_time
            sources = ["lora_model"]

        elif isinstance(rag_response, RAGResponse):
            # 只有RAG成功
            primary_response = rag_response.response
            attachments = rag_response.sources
            confidence = rag_response.confidence
            rag_time = rag_response.response_time
            sources = ["rag_system"]

        if not primary_response:
            primary_response = "抱歉，服务暂时不可用，请稍后再试。"
            confidence = 0.0

        total_time = time.time() - start_time

        return HybridInferenceResponse(
            query=query,
            primary_response=primary_response,
            enhanced_response=enhanced_response,
            attachments=attachments,
            confidence=confidence,
            total_time=total_time,
            model_time=model_time,
            rag_time=rag_time,
            strategy="parallel_merge",
            timestamp=datetime.now().isoformat(),
            sources=sources,
            request_id=request_id
        )

    async def _fallback_chain_strategy(self, query: str, request_id: str, **kwargs) -> HybridInferenceResponse:
        """降级链策略: 优先模型，失败后降级到RAG"""
        start_time = time.time()

        primary_response = ""
        attachments = []
        confidence = 0.5
        model_time = 0.0
        rag_time = 0.0
        sources = []

        # 先尝试LoRA模型
        model_response = await self.call_lora_model(query, **kwargs)

        if model_response and model_response.confidence > 0.6:
            # 模型回答质量较高，直接使用
            primary_response = model_response.response
            confidence = model_response.confidence
            model_time = model_response.inference_time
            sources = ["lora_model"]

            # 尝试获取附件链接
            if kwargs.get("include_attachments", True):
                rag_response = await self.call_rag_system(query, **kwargs)
                if rag_response:
                    attachments = rag_response.sources
                    rag_time = rag_response.response_time
                    sources.append("rag_system")
        else:
            # 模型回答不理想，降级到RAG
            rag_response = await self.call_rag_system(query, **kwargs)
            if rag_response:
                primary_response = rag_response.response
                attachments = rag_response.sources
                confidence = rag_response.confidence
                rag_time = rag_response.response_time
                sources = ["rag_system"]

                if model_response:
                    model_time = model_response.inference_time
                    sources.insert(0, "lora_model")

        if not primary_response:
            primary_response = "抱歉，服务暂时不可用，请稍后再试。"
            confidence = 0.0

        total_time = time.time() - start_time

        return HybridInferenceResponse(
            query=query,
            primary_response=primary_response,
            enhanced_response=None,
            attachments=attachments,
            confidence=confidence,
            total_time=total_time,
            model_time=model_time,
            rag_time=rag_time,
            strategy="fallback_chain",
            timestamp=datetime.now().isoformat(),
            sources=sources,
            request_id=request_id
        )

    async def hybrid_inference_internal(self,
                                      query: str,
                                      strategy: str = "model_primary",
                                      request_id: str = None,
                                      **kwargs) -> HybridInferenceResponse:
        """
        内部混合推理方法

        Args:
            query: 用户查询
            strategy: 混合策略
            request_id: 请求ID
            **kwargs: 其他参数

        Returns:
            HybridInferenceResponse: 混合响应结果
        """
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"

        self.request_count += 1
        start_time = time.time()

        try:
            # 检查服务状态
            await self.check_services_health()

            # 根据策略执行推理
            if strategy in self.hybrid_strategies:
                response = await self.hybrid_strategies[strategy](query, request_id, **kwargs)
                self.success_count += 1
            else:
                logger.warning(f"不支持的策略: {strategy}，使用fallback_chain")
                response = await self._fallback_chain_strategy(query, request_id, **kwargs)
                self.success_count += 1

            self.total_response_time += time.time() - start_time

            logger.info(f"混合推理完成 [{request_id}]: 策略={strategy}, 耗时={response.total_time:.2f}s, 置信度={response.confidence:.2f}")

            return response

        except Exception as e:
            self.error_count += 1
            logger.error(f"混合推理异常 [{request_id}]: {e}")

            # 返回错误响应
            return HybridInferenceResponse(
                query=query,
                primary_response=f"抱歉，服务暂时不可用。错误信息: {str(e)}",
                enhanced_response=None,
                attachments=[],
                confidence=0.0,
                total_time=time.time() - start_time,
                model_time=0.0,
                rag_time=0.0,
                strategy=strategy,
                timestamp=datetime.now().isoformat(),
                sources=[],
                request_id=request_id
            )

    def run(self, host: str = "0.0.0.0", port: int = None):
        """运行API服务"""
        if port is None:
            port = self.service_port

        logger.info(f"启动USTB混合API服务")
        logger.info(f"服务地址: http://{host}:{port}")
        logger.info(f"LoRA服务: {self.lora_service_url}")
        logger.info(f"RAG服务: {self.rag_service_url}")
        logger.info(f"支持的策略: {list(self.hybrid_strategies.keys())}")

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )

# 全局服务实例
hybrid_api_service = USTBHybridAPIService()

# 导出主要接口
__all__ = [
    "USTBHybridAPIService",
    "HybridInferenceRequest",
    "HybridInferenceResponse",
    "ServiceHealthResponse",
    "APIStatsResponse",
    "hybrid_api_service"
]

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="USTB混合API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8002, help="服务端口")
    parser.add_argument("--lora-url", default="http://localhost:8001", help="LoRA服务URL")
    parser.add_argument("--rag-url", default="http://localhost:8000", help="RAG服务URL")

    args = parser.parse_args()

    # 创建服务实例
    service = USTBHybridAPIService(
        lora_service_url=args.lora_url,
        rag_service_url=args.rag_url,
        service_port=args.port
    )

    # 运行服务
    try:
        service.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
    except Exception as e:
        logger.error(f"服务运行异常: {str(e)}")

if __name__ == "__main__":
    main()
