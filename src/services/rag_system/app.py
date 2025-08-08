"""
USTB RAG系统 - FastAPI主服务
严格按照8专家分工文档要求实现
"""
import time
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from loguru import logger

# 导入本地模块
from vector_store import vector_store
from embedding_service import embedding_service
from retrieval_engine import retrieval_engine
from cache_service import cache_service, CachedRetrievalService
from query_expansion import query_expansion_service, EnhancedRetrievalEngine

# 数据模型
class AttachmentModel(BaseModel):
    title: str
    url: str

class SearchRequest(BaseModel):
    query: str = Field(..., description="检索查询", min_length=1, max_length=500)
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    category_filter: Optional[List[str]] = Field(default=None, description="分类过滤")
    date_range: Optional[List[str]] = Field(default=None, description="日期范围过滤")

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    category: str
    url: str
    attachments: List[AttachmentModel]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    response_time: float

class HealthResponse(BaseModel):
    status: str
    version: str
    qdrant_status: str
    embedding_model: str
    document_count: int
    timestamp: datetime

# FastAPI应用
app = FastAPI(
    title="USTB RAG系统",
    description="北京科技大学教务助手RAG检索服务",
    version="1.0.0",
    docs_url=None,  # 禁用默认docs
    redoc_url=None,  # 禁用默认redoc
    openapi_url="/openapi.json"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    logger.info("RAG系统启动中...")
    
    # 初始化向量存储
    try:
        vector_store.create_collection()
        logger.info("向量存储初始化完成")
    except Exception as e:
        logger.error(f"向量存储初始化失败: {str(e)}")
        raise
    
    # 检查嵌入服务
    try:
        model_info = embedding_service.get_model_info()
        logger.info(f"嵌入服务就绪: {model_info}")
    except Exception as e:
        logger.error(f"嵌入服务初始化失败: {str(e)}")
        raise

    # 初始化缓存服务
    try:
        global cached_retrieval_service, enhanced_retrieval_service
        cached_retrieval_service = CachedRetrievalService(retrieval_engine)
        enhanced_retrieval_service = EnhancedRetrievalEngine(cached_retrieval_service, query_expansion_service)
        cache_stats = cache_service.get_stats()
        expansion_stats = query_expansion_service.get_expansion_stats()
        logger.info(f"缓存服务初始化完成: {cache_stats}")
        logger.info(f"查询扩展服务初始化完成: {expansion_stats}")
    except Exception as e:
        logger.error(f"高级服务初始化失败: {str(e)}")
        # 失败不影响系统启动

    logger.info("RAG系统启动完成")

@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "service": "USTB RAG系统",
        "version": "1.0.0",
        "status": "running",
        "api_docs": "/api-docs",
        "openapi_json": "/openapi.json"
    }

@app.get("/api-docs")
async def api_docs():
    """简单的API文档页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>USTB RAG系统 API文档</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .method { display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }
            .get { background-color: #61affe; }
            .post { background-color: #49cc90; }
            code { background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>USTB RAG系统 API文档</h1>
        <p>北京科技大学教务助手RAG检索服务</p>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /health</h3>
            <p>检查系统健康状态</p>
            <p><strong>示例:</strong> <code>curl http://localhost:8000/health</code></p>
        </div>

        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/v1/search</h3>
            <p>执行文档检索</p>
            <p><strong>请求体:</strong></p>
            <pre><code>{
  "query": "选课通知",
  "top_k": 5,
  "category_filter": ["选课"],
  "date_range": ["2024-01-01", "2024-12-31"]
}</code></pre>
            <p><strong>示例:</strong></p>
            <pre><code>curl -X POST http://localhost:8000/api/v1/search \\
  -H "Content-Type: application/json" \\
  -d '{"query":"选课通知","top_k":3}'</code></pre>
        </div>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/v1/stats</h3>
            <p>获取系统统计信息</p>
            <p><strong>示例:</strong> <code>curl http://localhost:8000/api/v1/stats</code></p>
        </div>

        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/v1/index</h3>
            <p>重新索引文档</p>
            <p><strong>示例:</strong> <code>curl -X POST http://localhost:8000/api/v1/index</code></p>
        </div>

        <h2>OpenAPI规范</h2>
        <p>完整的API规范: <a href="/openapi.json" target="_blank">/openapi.json</a></p>

        <h2>测试工具</h2>
        <p>使用Python测试:</p>
        <pre><code>import requests

# 健康检查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 文档检索
response = requests.post("http://localhost:8000/api/v1/search",
                        json={"query": "选课通知", "top_k": 3})
print(response.json())</code></pre>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    try:
        # 检查Qdrant状态
        qdrant_status = "healthy" if vector_store.health_check() else "unhealthy"
        
        # 获取文档数量
        collection_info = vector_store.get_collection_info()
        doc_count = collection_info.get("points_count", 0)
        
        # 获取嵌入模型信息
        model_info = embedding_service.get_model_info()
        
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            qdrant_status=qdrant_status,
            embedding_model=model_info.get("model_name", "unknown"),
            document_count=doc_count,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="健康检查失败")

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """文档检索API - 按照8专家分工文档要求的接口格式"""
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    try:
        logger.info(f"收到检索请求 [{query_id}]: {request.query}")
        
        # 执行检索 - 使用缓存服务
        try:
            results = cached_retrieval_service.search_cached(
                query=request.query,
                top_k=request.top_k,
                category_filter=request.category_filter,
                date_range=request.date_range
            )
        except NameError:
            # 缓存服务未初始化，使用原始检索
            results = retrieval_engine.search(
                query=request.query,
                top_k=request.top_k,
                category_filter=request.category_filter,
                date_range=request.date_range
            )
        
        response_time = time.time() - start_time
        
        logger.info(f"检索完成 [{query_id}]: 返回{len(results)}个结果，耗时{response_time:.3f}秒")
        
        return SearchResponse(
            results=results,
            total=len(results),
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(f"检索失败 [{query_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")

@app.post("/api/v1/search/enhanced")
async def enhanced_search(request: SearchRequest):
    """增强检索接口 - 带查询扩展"""
    try:
        query_id = f"enhanced_{int(time.time() * 1000)}"
        logger.info(f"增强检索请求 [{query_id}]: {request.query}")
        start_time = time.time()

        # 使用增强检索引擎
        try:
            results = enhanced_retrieval_service.search_with_expansion(
                query=request.query,
                top_k=request.top_k,
                use_expansion=True,
                use_rewrite=True,
                category_filter=request.category_filter,
                date_range=request.date_range
            )
        except NameError:
            # 增强服务未初始化，使用缓存服务
            try:
                results = cached_retrieval_service.search_cached(
                    query=request.query,
                    top_k=request.top_k,
                    category_filter=request.category_filter,
                    date_range=request.date_range
                )
            except NameError:
                # 缓存服务也未初始化，使用原始检索
                results = retrieval_engine.search(
                    query=request.query,
                    top_k=request.top_k,
                    category_filter=request.category_filter,
                    date_range=request.date_range
                )

        response_time = time.time() - start_time

        logger.info(f"增强检索完成 [{query_id}]: 返回{len(results)}个结果，耗时{response_time:.3f}秒")

        # 添加扩展信息到响应
        expanded_query = query_expansion_service.expand_query(request.query)

        return {
            "results": results,
            "query": request.query,
            "expanded_query": expanded_query,
            "total": len(results),
            "response_time": response_time,
            "search_type": "enhanced"
        }

    except Exception as e:
        logger.error(f"增强检索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"增强检索失败: {str(e)}")

@app.post("/api/v1/index")
async def index_documents():
    """索引文档API"""
    try:
        logger.info("开始索引文档...")
        
        # 加载并索引文档
        doc_count = retrieval_engine.load_and_index_documents()
        
        return {
            "status": "success",
            "message": f"成功索引 {doc_count} 个文档",
            "document_count": doc_count
        }
        
    except Exception as e:
        logger.error(f"文档索引失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档索引失败: {str(e)}")

@app.get("/api/v1/stats")
async def get_stats():
    """获取系统统计信息"""
    try:
        collection_info = vector_store.get_collection_info()
        model_info = embedding_service.get_model_info()
        cache_stats = cache_service.get_stats()

        return {
            "collection": collection_info,
            "embedding_model": model_info,
            "cache_stats": cache_stats,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")

# 手动添加文档路由
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
    )

# OpenAI兼容API - 为ChatGPT-Next-Web提供兼容接口
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "ustb-rag-assistant"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI兼容的聊天完成API - 连接到USTB RAG系统"""
    try:
        # 获取最后一条用户消息作为查询
        user_message = None
        for message in reversed(request.messages):
            if message.role == "user":
                user_message = message.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="没有找到用户消息")

        # 调用RAG系统进行检索
        search_request = SearchRequest(query=user_message, top_k=5)
        search_response = await search_documents(search_request)

        # 格式化RAG响应为聊天格式
        if search_response.results:
            # 构建回答
            answer_parts = ["📚 根据USTB教务信息，我为您找到以下相关内容：\n"]

            for i, result in enumerate(search_response.results[:3], 1):
                answer_parts.append(f"**{i}. {result.title}**")
                answer_parts.append(f"{result.content[:200]}...")
                if result.attachments:
                    answer_parts.append("📎 相关附件：")
                    for att in result.attachments[:2]:
                        answer_parts.append(f"• [{att.title}]({att.url})")
                answer_parts.append("")

            answer_parts.append("💡 如需更详细信息，请点击上方附件链接查看完整文档。")
            bot_response = "\n".join(answer_parts)
        else:
            bot_response = "抱歉，没有找到相关的教务信息。请尝试使用其他关键词搜索，或联系教务处获取帮助。"

        # 构建OpenAI格式的响应
        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": bot_response
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(bot_response.split()),
                "total_tokens": len(user_message.split()) + len(bot_response.split())
            }
        )

        return response

    except Exception as e:
        logger.error(f"聊天完成API失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"聊天完成失败: {str(e)}")

# 模型列表API - ChatGPT-Next-Web需要
@app.get("/v1/models")
async def list_models():
    """返回可用模型列表"""
    return {
        "object": "list",
        "data": [
            {
                "id": "ustb-rag-assistant",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ustb",
                "permission": [],
                "root": "ustb-rag-assistant",
                "parent": None
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
