"""
用户反馈数据模型
定义反馈请求、响应和统计数据结构
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class FeedbackRequest(BaseModel):
    """用户反馈请求模型"""
    query_id: Optional[str] = Field(None, description="关联的查询ID")
    result_id: Optional[str] = Field(None, description="关联的结果ID")
    feedback_type: str = Field(..., description="反馈类型", pattern="^(helpful|not_helpful|irrelevant|error|suggestion)$")
    rating: Optional[int] = Field(None, description="评分(1-5)", ge=1, le=5)
    comment: Optional[str] = Field(None, description="反馈评论", max_length=1000)
    category: Optional[str] = Field(None, description="反馈分类")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")

class FeedbackResponse(BaseModel):
    """反馈提交响应模型"""
    feedback_id: str = Field(..., description="反馈ID")
    message: str = Field(..., description="响应消息")
    status: str = Field(..., description="处理状态")
    created_at: datetime = Field(..., description="创建时间")

class FeedbackDetail(BaseModel):
    """反馈详细信息模型"""
    feedback_id: str = Field(..., description="反馈ID")
    user_id: str = Field(..., description="用户ID")
    query_id: Optional[str] = Field(None, description="关联的查询ID")
    result_id: Optional[str] = Field(None, description="关联的结果ID")
    feedback_type: str = Field(..., description="反馈类型")
    rating: Optional[int] = Field(None, description="评分")
    comment: Optional[str] = Field(None, description="反馈评论")
    category: Optional[str] = Field(None, description="反馈分类")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    status: str = Field(..., description="处理状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    processed_at: Optional[datetime] = Field(None, description="处理时间")
    response: Optional[str] = Field(None, description="处理回复")

class FeedbackStats(BaseModel):
    """反馈统计信息模型"""
    total_feedback: int = Field(..., description="总反馈数")
    avg_rating: float = Field(..., description="平均评分")
    feedback_by_type: Dict[str, int] = Field(..., description="按类型统计")
    rating_distribution: Dict[str, int] = Field(..., description="评分分布")
    period_days: int = Field(..., description="统计周期(天)")
    last_updated: datetime = Field(..., description="最后更新时间")

class FeedbackListResponse(BaseModel):
    """反馈列表响应模型"""
    feedback_list: List[FeedbackDetail] = Field(..., description="反馈列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否有更多数据")

class FeedbackSummary(BaseModel):
    """反馈摘要信息"""
    feedback_id: str
    feedback_type: str
    rating: Optional[int]
    created_at: datetime
    status: str
