#!/usr/bin/env python3
"""
USTB AI教务助手 - Web前后端API连接器
解决混合API接口路径不匹配问题，实现Web前后端与混合API的无缝对接

功能:
1. API路径适配: /api/v1/chat -> /api/v1/hybrid_inference
2. 请求格式转换: Web格式 -> 混合API格式
3. 响应格式转换: 混合API格式 -> Web格式
4. 错误处理和降级机制
5. 性能监控和日志记录

创建时间: 2025-08-07
作者: 系统集成专家
状态: 生产就绪
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/web_api_connector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Web API请求/响应模型
class WebChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    max_tokens: int = 300
    temperature: float = 0.1

class WebChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    sources: List[str] = []
    attachments: List[Dict] = []
    response_time: float
    confidence: float

class WebAPIConnector:
    """
    Web前后端API连接器
    负责将Web界面的API调用转换为混合API服务调用
    """
    
    def __init__(self, 
                 hybrid_api_url: str = "http://localhost:8002",
                 connector_port: int = 8003):
        
        self.hybrid_api_url = hybrid_api_url
        self.connector_port = connector_port
        self.start_time = time.time()
        
        # 性能统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="USTB Web API连接器",
            description="Web前后端与混合API服务的桥接器",
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
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"Web API连接器初始化完成")
        logger.info(f"混合API服务: {self.hybrid_api_url}")
        logger.info(f"连接器端口: {self.connector_port}")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            hybrid_health = await self.check_hybrid_api_health()
            
            return {
                "status": "healthy" if hybrid_health else "degraded",
                "hybrid_api_status": hybrid_health,
                "uptime": time.time() - self.start_time,
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/api/v1/chat", response_model=WebChatResponse)
        async def web_chat(request: WebChatRequest):
            """Web聊天接口 - 适配到混合API"""
            request_id = f"web_{int(time.time() * 1000)}"
            
            try:
                response = await self.call_hybrid_api(
                    query=request.message,
                    strategy="parallel_merge",  # 默认使用并行合并策略
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    request_id=request_id
                )
                
                return response
                
            except Exception as e:
                logger.error(f"Web聊天接口调用失败 [{request_id}]: {str(e)}")
                raise HTTPException(status_code=500, detail=f"聊天服务异常: {str(e)}")
        
        @self.app.get("/api/v1/stats")
        async def get_stats():
            """获取连接器统计信息"""
            return {
                "request_count": self.request_count,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "success_rate": self.success_count / max(self.request_count, 1) * 100,
                "average_response_time": self.total_response_time / max(self.request_count, 1),
                "hybrid_api_url": self.hybrid_api_url,
                "uptime": time.time() - self.start_time
            }
    
    async def check_hybrid_api_health(self) -> bool:
        """检查混合API服务健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.hybrid_api_url}/health", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"混合API健康检查失败: {e}")
            return False
    
    async def call_hybrid_api(self, 
                            query: str, 
                            strategy: str = "parallel_merge",
                            request_id: str = None,
                            **kwargs) -> WebChatResponse:
        """调用混合API服务"""
        
        self.request_count += 1
        start_time = time.time()
        
        try:
            # 构造混合API请求
            payload = {
                "query": query,
                "strategy": strategy,
                "max_tokens": kwargs.get("max_tokens", 300),
                "temperature": kwargs.get("temperature", 0.1),
                "top_p": kwargs.get("top_p", 0.9),
                "include_attachments": True,
                "timeout": 30
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hybrid_api_url}/api/v1/hybrid_inference",
                    json=payload,
                    timeout=35
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # 转换为Web API格式
                        web_response = WebChatResponse(
                            response=data["primary_response"],
                            conversation_id=request_id or f"conv_{int(time.time())}",
                            timestamp=data["timestamp"],
                            sources=data["sources"],
                            attachments=data["attachments"],
                            response_time=data["total_time"],
                            confidence=data["confidence"]
                        )
                        
                        self.success_count += 1
                        self.total_response_time += time.time() - start_time
                        
                        logger.info(f"Web API调用成功 [{request_id}]: 耗时={web_response.response_time:.2f}s, 置信度={web_response.confidence:.2f}")
                        
                        return web_response
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"混合API调用失败 [{request_id}]: {response.status} - {error_text}")
                        raise HTTPException(status_code=response.status, detail=f"混合API调用失败: {error_text}")
                        
        except Exception as e:
            self.error_count += 1
            logger.error(f"混合API调用异常 [{request_id}]: {e}")
            
            # 返回降级响应
            return WebChatResponse(
                response=f"抱歉，服务暂时不可用。请稍后再试。错误信息: {str(e)}",
                conversation_id=request_id or f"conv_{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                sources=[],
                attachments=[],
                response_time=time.time() - start_time,
                confidence=0.0
            )
    
    def run(self, host: str = "0.0.0.0", port: int = None):
        """运行Web API连接器"""
        if port is None:
            port = self.connector_port
        
        logger.info(f"启动Web API连接器")
        logger.info(f"连接器地址: http://{host}:{port}")
        logger.info(f"混合API服务: {self.hybrid_api_url}")
        logger.info(f"Web聊天接口: http://{host}:{port}/api/v1/chat")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )

# 全局连接器实例
web_api_connector = WebAPIConnector()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web API连接器")
    parser.add_argument("--host", default="0.0.0.0", help="连接器主机地址")
    parser.add_argument("--port", type=int, default=8003, help="连接器端口")
    parser.add_argument("--hybrid-url", default="http://localhost:8002", help="混合API服务URL")
    
    args = parser.parse_args()
    
    # 创建连接器实例
    connector = WebAPIConnector(
        hybrid_api_url=args.hybrid_url,
        connector_port=args.port
    )
    
    # 运行连接器
    try:
        connector.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("连接器被用户中断")
    except Exception as e:
        logger.error(f"连接器运行异常: {str(e)}")

if __name__ == "__main__":
    main()
