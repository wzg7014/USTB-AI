"""
聊天对话数据模型
定义聊天会话、消息和相关数据结构
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID，不提供则创建新会话")
    message_type: str = Field(default="text", description="消息类型")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文信息")

class ChatMessage(BaseModel):
    """聊天消息模型"""
    message_id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    role: str = Field(..., description="角色：user/assistant/system")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(default="text", description="消息类型")
    timestamp: datetime = Field(..., description="消息时间")
    rag_results: Optional[List[Dict]] = Field(default=None, description="RAG搜索结果")
    response_time: Optional[float] = Field(None, description="响应时间(秒)")
    error_details: Optional[str] = Field(None, description="错误详情")

class ChatSession(BaseModel):
    """聊天会话模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    is_active: bool = Field(default=True, description="是否活跃")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")

class RAGResult(BaseModel):
    """RAG搜索结果模型"""
    id: str = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容摘要")
    score: float = Field(..., description="相似度评分")
    category: str = Field(..., description="文档分类")
    url: str = Field(..., description="原文链接")
    attachments: List[Dict[str, str]] = Field(default_factory=list, description="附件列表")
    publish_date: Optional[datetime] = Field(None, description="发布日期")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="AI回答")
    message_id: str = Field(..., description="消息ID")
    timestamp: datetime = Field(..., description="响应时间戳")
    response_time: float = Field(..., description="处理时间(秒)")
    rag_results: List[RAGResult] = Field(default_factory=list, description="RAG搜索结果")
    context_used: bool = Field(default=True, description="是否使用了上下文")
    confidence: Optional[float] = Field(None, description="回答置信度")

class ChatStats(BaseModel):
    """聊天统计信息"""
    total_sessions: int = Field(..., description="总会话数")
    total_messages: int = Field(..., description="总消息数")
    avg_response_time: float = Field(..., description="平均响应时间")
    active_sessions: int = Field(..., description="活跃会话数")
    user_satisfaction: Optional[float] = Field(None, description="用户满意度")

class StreamChatResponse(BaseModel):
    """流式聊天响应模型"""
    session_id: str
    chunk: str
    is_complete: bool = False
    chunk_index: int = 0
    total_chunks: Optional[int] = None
