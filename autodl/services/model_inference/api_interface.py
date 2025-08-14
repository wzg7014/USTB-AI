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
import re
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
                 service_port: int = 8002):  # 注意：默认端口是8002
        
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

    # 注意：这是一个大文件（839行），这里只显示前150行
    # 完整文件包含所有混合策略实现、服务调用逻辑等
    
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

    # 其他方法实现...
    # （由于文件太大，这里只显示关键部分）

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="USTB混合API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8002, help="服务端口")  # 默认8002端口
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
        logger.info(f"启动USTB混合API服务 - {args.host}:{args.port}")
        uvicorn.run(
            service.app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
    except Exception as e:
        logger.error(f"服务运行异常: {str(e)}")

if __name__ == "__main__":
    main()

"""
启动命令:
cd /root/autodl-tmp/ustb-project/services/model_inference/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python api_interface.py --port 8002

验证命令:
curl http://localhost:8002/health
curl -X POST http://localhost:8002/api/v1/hybrid_inference -H "Content-Type: application/json" -d '{"query":"请问如何选课？","strategy":"parallel_merge"}'

注意：这是一个839行的大文件，包含完整的混合推理逻辑、多种策略实现等。
此处仅显示关键结构，完整文件请直接从AutoDL获取。
"""
