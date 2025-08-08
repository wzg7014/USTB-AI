"""
搜索相关数据模型
定义搜索请求、响应和历史记录的数据结构
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId

class AttachmentModel(BaseModel):
    """附件信息模型"""
    title: str = Field(..., description="附件标题")
    url: str = Field(..., description="附件下载链接")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    category_filter: Optional[List[str]] = Field(default=None, description="分类过滤")
    date_range: Optional[List[str]] = Field(default=None, description="日期范围过滤")
    similarity_threshold: Optional[float] = Field(default=0.3, description="相似度阈值", ge=0.0, le=1.0)

class SearchResult(BaseModel):
    """单个搜索结果"""
    id: str = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容摘要")
    score: float = Field(..., description="相似度评分", ge=0.0, le=1.0)
    category: str = Field(..., description="文档分类")
    url: str = Field(..., description="原文链接")
    attachments: List[AttachmentModel] = Field(default_factory=list, description="附件列表")
    publish_date: Optional[datetime] = Field(None, description="发布日期")
    department: Optional[str] = Field(None, description="发布部门")

class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="结果总数")
    response_time: float = Field(..., description="响应时间(秒)")
    query_id: str = Field(..., description="查询ID")
    cached: bool = Field(default=False, description="是否来自缓存")
    rag_response_time: Optional[float] = Field(None, description="RAG系统响应时间")

class SearchHistoryItem(BaseModel):
    """搜索历史记录项"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="用户ID")
    query: str = Field(..., description="搜索查询")
    results_count: int = Field(..., description="结果数量")
    response_time: float = Field(..., description="响应时间")
    timestamp: datetime = Field(default_factory=datetime.now, description="搜索时间")
    category_filter: Optional[List[str]] = Field(None, description="使用的分类过滤")
    clicked_results: List[str] = Field(default_factory=list, description="用户点击的结果ID")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""
    history: List[SearchHistoryItem]
    total: int
    page: int
    page_size: int

class SearchStats(BaseModel):
    """搜索统计信息"""
    total_searches: int
    unique_queries: int
    avg_response_time: float
    most_searched_categories: List[Dict[str, Any]]
    search_trends: List[Dict[str, Any]]

class CategoryInfo(BaseModel):
    """分类信息"""
    name: str = Field(..., description="分类名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="分类描述")
    document_count: int = Field(..., description="文档数量")
    icon: Optional[str] = Field(None, description="图标")

class CategoriesResponse(BaseModel):
    """分类列表响应"""
    categories: List[CategoryInfo]
    total: int

class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    query_id: str = Field(..., description="查询ID")
    result_id: Optional[str] = Field(None, description="结果ID")
    feedback_type: str = Field(..., description="反馈类型", regex="^(helpful|not_helpful|irrelevant|error)$")
    comment: Optional[str] = Field(None, description="反馈评论", max_length=500)
    rating: Optional[int] = Field(None, description="评分", ge=1, le=5)

class FeedbackResponse(BaseModel):
    """反馈响应"""
    message: str
    feedback_id: str
