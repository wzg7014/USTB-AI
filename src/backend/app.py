"""
USTB AI教务助手 - Web后端主应用
基于FastAPI构建，集成RAG系统，提供高性能API服务

技术栈：FastAPI + MongoDB + Redis + httpx
性能目标：API响应<200ms，并发>100用户，可用性>99%
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import httpx
import asyncio
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置
class Config:
    RAG_API_URL = "http://localhost:8000"  # RAG系统地址
    MONGODB_URL = "mongodb://localhost:27017"
    REDIS_URL = "redis://localhost:6379"
    SECRET_KEY = "ustb-ai-assistant-secret-key"
    API_TIMEOUT = 30.0  # RAG API超时时间
    CACHE_TTL = 3600    # 缓存过期时间（秒）

config = Config()

# 数据模型定义
class SearchRequest(BaseModel):
    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    category_filter: Optional[List[str]] = Field(default=None, description="分类过滤")
    date_range: Optional[List[str]] = Field(default=None, description="日期范围")

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    category: str
    url: str
    attachments: List[Dict[str, str]]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    response_time: float
    query_id: str
    cached: bool = False

class UserProfile(BaseModel):
    user_id: str
    username: str
    email: str
    preferences: Dict[str, Any] = {}
    created_at: datetime

class SearchHistory(BaseModel):
    query: str
    timestamp: datetime
    results_count: int
    response_time: float

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]

# 全局服务实例
http_client = None
security = HTTPBearer()

# 创建FastAPI应用
app = FastAPI(
    title="USTB AI教务助手 API",
    description="北京科技大学AI教务助手后端服务，提供智能搜索和用户管理功能",
    version="1.0.0"
)

# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global http_client

    logger.info("🚀 启动USTB AI教务助手后端服务...")
    http_client = httpx.AsyncClient(timeout=config.API_TIMEOUT)

    # 初始化数据库连接池
    try:
        from routes.chat import db_pool
        await db_pool.init_pool()
        logger.info("✅ 数据库连接池初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库连接池初始化失败: {str(e)}")

    # 检查混合API系统连接
    try:
        # 临时硬编码解决配置缓存问题
        hybrid_api_url = "http://localhost:8003"
        response = await http_client.get(f"{hybrid_api_url}/health")
        if response.status_code == 200:
            result = response.json()
            hybrid_status = result.get('hybrid_api_status', False)
            if hybrid_status:
                logger.info("✅ 混合API系统连接正常")
            else:
                logger.warning("⚠️ 混合API系统部分功能异常")
        else:
            logger.warning(f"⚠️ 混合API系统响应异常: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 混合API系统连接失败: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    global http_client

    logger.info("🛑 关闭USTB AI教务助手后端服务...")

    # 关闭数据库连接池
    try:
        from routes.chat import db_pool
        await db_pool.close_pool()
        logger.info("✅ 数据库连接池已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭数据库连接池失败: {str(e)}")

    if http_client:
        await http_client.aclose()

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.ustb.edu.cn"]
)

# 性能监控中间件
@app.middleware("http")
async def monitor_performance(request, call_next):
    """性能监控中间件"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录性能日志
        logger.info(f"API调用: {request.method} {request.url.path} - {process_time:.3f}s")
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"API错误: {request.method} {request.url.path} - {process_time:.3f}s - {str(e)}")
        raise

# 服务类定义
class RAGProxyService:
    """RAG系统代理服务 - 处理与RAG系统的集成"""
    
    def __init__(self):
        self.cache = {}  # 简单内存缓存，生产环境应使用Redis
    
    async def search_documents(self, request: SearchRequest, user_id: str = None) -> SearchResponse:
        """代理RAG系统搜索请求，添加容错和缓存"""
        query_id = f"query_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # 检查缓存
        cache_key = f"search:{hash(request.query)}:{request.top_k}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            cached_result["cached"] = True
            cached_result["query_id"] = query_id
            logger.info(f"缓存命中: {request.query}")
            return SearchResponse(**cached_result)
        
        try:
            logger.info(f"代理RAG搜索请求 [{query_id}]: {request.query}")
            
            # 调用RAG系统API
            response = await http_client.post(
                f"{config.RAG_API_URL}/api/v1/search",
                json=request.dict(),
                timeout=config.API_TIMEOUT
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"RAG系统错误: {response.text}"
                )
            
            rag_data = response.json()
            response_time = time.time() - start_time
            
            # 构造响应
            search_response = {
                "results": rag_data["results"],
                "total": rag_data["total"],
                "response_time": response_time,
                "query_id": query_id,
                "cached": False
            }
            
            # 写入缓存
            self.cache[cache_key] = search_response.copy()
            
            logger.info(f"RAG搜索完成 [{query_id}]: {len(rag_data['results'])}个结果，耗时{response_time:.3f}秒")
            
            return SearchResponse(**search_response)
            
        except httpx.TimeoutException:
            logger.error(f"RAG系统超时 [{query_id}]: {config.API_TIMEOUT}秒")
            raise HTTPException(
                status_code=504,
                detail="搜索服务响应超时，请稍后重试"
            )
        except httpx.ConnectError:
            logger.error(f"RAG系统连接失败 [{query_id}]")
            raise HTTPException(
                status_code=503,
                detail="搜索服务暂时不可用，请稍后重试"
            )
        except Exception as e:
            logger.error(f"RAG搜索异常 [{query_id}]: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"搜索服务内部错误: {str(e)}"
            )

# 服务实例
rag_service = RAGProxyService()

# 用户认证（简化版，生产环境需要完整的JWT实现）
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户信息"""
    # 简化的用户验证，生产环境需要验证JWT token
    token = credentials.credentials
    if not token or token == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 返回模拟用户信息
    return {
        "user_id": "user_001",
        "username": "test_user",
        "email": "test@ustb.edu.cn"
    }

# 导入路由模块
from routes.chat import router as chat_router
from routes.categories import router as categories_router
from routes.feedback import router as feedback_router
from routes.openai_compat import router as openai_router

# 注册路由
app.include_router(chat_router)
app.include_router(categories_router)
app.include_router(feedback_router)
app.include_router(openai_router)  # OpenAI兼容API

# API路由定义
@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径 - API信息"""
    return {
        "service": "USTB AI教务助手 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    services_status = {}
    
    # 检查混合API系统状态
    try:
        hybrid_api_url = "http://localhost:8003"
        response = await http_client.get(f"{hybrid_api_url}/health", timeout=5.0)
        if response.status_code == 200:
            result = response.json()
            services_status["hybrid_api"] = "healthy" if result.get('hybrid_api_status') else "partial"
        else:
            services_status["hybrid_api"] = "unhealthy"
    except:
        services_status["hybrid_api"] = "unavailable"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        services=services_status
    )

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    user: dict = Depends(get_current_user)
):
    """文档搜索接口 - 代理RAG系统搜索"""
    try:
        result = await rag_service.search_documents(request, user["user_id"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索接口异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="搜索服务内部错误"
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 启动USTB AI教务助手后端服务...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,  # 使用8001端口，避免与RAG系统8000端口冲突
        reload=True,
        log_level="info"
    )
