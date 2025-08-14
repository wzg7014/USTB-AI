#!/usr/bin/env python3
"""
USTB RAG系统服务 - 全新版本
严格按照文档技术栈要求：FastAPI + Qdrant + BCE-embedding-base_v1
解决搜索返回0结果的问题，使用正确的Qdrant search API
"""

import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# FastAPI核心组件
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Qdrant向量数据库
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# BCE嵌入模型
from sentence_transformers import SentenceTransformer

# 工具库
import torch
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 数据模型定义 ====================

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="检索查询", min_length=1, max_length=500)
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    include_metadata: bool = Field(default=True, description="是否包含元数据")
    include_attachments: bool = Field(default=True, description="是否包含附件")

class DocumentResult(BaseModel):
    """文档结果模型"""
    id: str
    title: str
    content: str
    score: float
    category: str
    url: str = ""
    publish_date: str = ""

class AttachmentResult(BaseModel):
    """附件结果模型"""
    title: str
    url: str
    type: str = "pdf"

class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str
    summary: str
    documents: List[DocumentResult]
    attachments: List[AttachmentResult]
    relevance_score: float
    response_time: float
    gpu_accelerated: bool
    total_documents: int

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    qdrant_status: str
    embedding_model: str
    document_count: int
    gpu_available: bool
    service_uptime: float
    timestamp: datetime

# ==================== RAG系统核心类 ====================

class USTBRAGSystem:
    """USTB RAG系统核心类"""
    
    def __init__(self):
        self.app = FastAPI(
            title="USTB RAG System API",
            description="北京科技大学教务RAG检索系统",
            version="2.0.0"
        )
        
        # 系统状态
        self.start_time = time.time()
        self.is_ready = False
        
        # 组件初始化
        self.vector_store = None
        self.embedding_model = None
        self.collection_name = "ustb_documents"
        
        # 配置路径
        self.vector_db_path = "/root/autodl-tmp/ustb-project/data/vectors"
        self.model_path = "/root/autodl-tmp/ustb-project/models/bce-embedding-base_v1"
        
        # 设置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """服务启动事件"""
            await self.initialize_system()
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """健康检查接口"""
            return await self.get_health_status()
        
        @self.app.post("/api/v1/search", response_model=SearchResponse)
        async def search_documents(request: SearchRequest):
            """文档搜索接口"""
            return await self.search_documents(request)
        
        @self.app.get("/")
        async def root():
            """根路径"""
            return {"message": "USTB RAG System API v2.0.0", "status": "running"}
    
    async def initialize_system(self):
        """初始化系统组件"""
        try:
            logger.info("🚀 开始初始化USTB RAG系统...")
            
            # 1. 初始化Qdrant向量数据库
            logger.info("📊 初始化Qdrant向量数据库...")
            self.vector_store = QdrantClient(path=self.vector_db_path)
            
            # 检查集合是否存在
            try:
                collection_info = self.vector_store.get_collection(self.collection_name)
                logger.info(f"✅ 向量数据库连接成功，文档数量: {collection_info.points_count}")
            except Exception as e:
                logger.error(f"❌ 向量数据库集合不存在: {e}")
                raise
            
            # 2. 初始化BCE嵌入模型
            logger.info("🤖 初始化BCE嵌入模型...")
            self.embedding_model = SentenceTransformer(self.model_path)
            
            # 检查GPU可用性
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                self.embedding_model = self.embedding_model.cuda()
                logger.info("🚀 GPU加速已启用")
            else:
                logger.info("💻 使用CPU模式")
            
            # 3. 预热模型
            logger.info("🔥 预热嵌入模型...")
            test_query = "测试查询"
            _ = self.embedding_model.encode([test_query])
            logger.info("✅ 模型预热完成")
            
            self.is_ready = True
            logger.info("🎉 USTB RAG系统初始化完成！")
            
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {str(e)}")
            self.is_ready = False
            raise
    
    async def get_health_status(self) -> HealthResponse:
        """获取系统健康状态"""
        try:
            # 检查Qdrant状态
            qdrant_status = "healthy"
            document_count = 0
            
            if self.vector_store:
                try:
                    collection_info = self.vector_store.get_collection(self.collection_name)
                    document_count = collection_info.points_count
                except:
                    qdrant_status = "error"
            else:
                qdrant_status = "not_initialized"
            
            return HealthResponse(
                status="healthy" if self.is_ready else "initializing",
                version="2.0.0",
                qdrant_status=qdrant_status,
                embedding_model="maidalun1020/bce-embedding-base_v1",
                document_count=document_count,
                gpu_available=torch.cuda.is_available(),
                service_uptime=time.time() - self.start_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")
    
    async def search_documents(self, request: SearchRequest) -> SearchResponse:
        """执行文档搜索"""
        start_time = time.time()
        
        try:
            if not self.is_ready:
                raise HTTPException(status_code=503, detail="系统尚未就绪，请稍后再试")
            
            logger.info(f"🔍 执行搜索: '{request.query}', top_k={request.top_k}")
            
            # 1. 生成查询向量
            query_embedding = self.embedding_model.encode([request.query])[0].tolist()
            logger.info(f"📊 查询向量生成完成，维度: {len(query_embedding)}")
            
            # 2. 执行向量搜索 - 使用正确的search方法
            search_results = self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=request.top_k,
                with_payload=True
            )
            
            logger.info(f"📋 向量搜索完成，返回 {len(search_results)} 个结果")
            
            # 3. 处理搜索结果
            documents = []
            attachments = []
            
            for result in search_results:
                # 构建文档结果
                doc = DocumentResult(
                    id=result.payload.get("ustb_id", ""),
                    title=result.payload.get("title", ""),
                    content=result.payload.get("content", "")[:500],  # 限制内容长度
                    score=float(result.score),
                    category=result.payload.get("category", ""),
                    url=result.payload.get("url", ""),
                    publish_date=result.payload.get("publish_date", "")
                )
                documents.append(doc)
                
                # 处理附件
                if request.include_attachments and result.payload.get("attachments"):
                    for att in result.payload["attachments"]:
                        if isinstance(att, dict):
                            attachment = AttachmentResult(
                                title=att.get("title", ""),
                                url=att.get("url", ""),
                                type=att.get("type", "pdf")
                            )
                            if attachment not in attachments:
                                attachments.append(attachment)
            
            # 4. 生成摘要
            if documents:
                summary = f"根据您的查询'{request.query}'，为您找到了{len(documents)}个相关的USTB教务文档。"
            else:
                summary = f"抱歉，没有找到与'{request.query}'相关的文档。请尝试使用其他关键词。"
            
            # 5. 计算相关度分数
            relevance_score = sum(doc.score for doc in documents) / len(documents) if documents else 0.0
            
            response_time = time.time() - start_time
            
            logger.info(f"✅ 搜索完成: {len(documents)}个文档, {len(attachments)}个附件, 耗时{response_time:.3f}s")
            
            return SearchResponse(
                query=request.query,
                summary=summary,
                documents=documents,
                attachments=attachments,
                relevance_score=relevance_score,
                response_time=response_time,
                gpu_accelerated=torch.cuda.is_available(),
                total_documents=len(documents)
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ 搜索失败: {str(e)}")
            
            # 返回错误响应，但保持API格式一致
            return SearchResponse(
                query=request.query,
                summary=f"搜索过程中发生错误: {str(e)}",
                documents=[],
                attachments=[],
                relevance_score=0.0,
                response_time=response_time,
                gpu_accelerated=torch.cuda.is_available(),
                total_documents=0
            )

# ==================== 主函数 ====================

def main():
    """主函数"""
    # 创建RAG系统实例
    rag_system = USTBRAGSystem()
    
    # 启动服务
    logger.info("🚀 启动USTB RAG系统服务...")
    uvicorn.run(
        rag_system.app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()

"""
启动命令:
cd /root/autodl-tmp/ustb-project/services/rag_system/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python rag_service_v2.py

验证命令:
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/search -H "Content-Type: application/json" -d '{"query":"选课","top_k":5}'
"""
