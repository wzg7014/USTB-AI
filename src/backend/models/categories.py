"""
教务分类数据模型
定义分类信息、统计数据和相关数据结构
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class CategoryBase(BaseModel):
    """分类基础信息"""
    id: str = Field(..., description="分类ID")
    name: str = Field(..., description="分类名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="分类描述")
    icon: Optional[str] = Field(None, description="分类图标")

class CategoryDetail(CategoryBase):
    """分类详细信息"""
    parent_id: Optional[str] = Field(None, description="父分类ID")
    level: int = Field(default=1, description="分类层级")
    sort_order: int = Field(default=999, description="排序顺序")
    document_count: int = Field(default=0, description="文档数量")
    recent_searches: int = Field(default=0, description="最近搜索次数")
    avg_score: float = Field(default=0.0, description="平均质量评分")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

class CategoryStats(BaseModel):
    """分类统计信息"""
    total_categories: int = Field(..., description="总分类数")
    total_documents: int = Field(..., description="总文档数")
    recent_searches: int = Field(..., description="最近搜索总数")
    avg_documents_per_category: float = Field(..., description="平均每分类文档数")
    most_popular_category: Optional[str] = Field(None, description="最热门分类ID")

class CategoryResponse(BaseModel):
    """分类列表响应"""
    categories: List[CategoryDetail] = Field(..., description="分类列表")
    stats: CategoryStats = Field(..., description="统计信息")
    timestamp: datetime = Field(..., description="响应时间戳")

class CategoryTree(BaseModel):
    """分类树结构"""
    category: CategoryDetail
    children: List['CategoryTree'] = Field(default_factory=list, description="子分类")

# 更新前向引用
CategoryTree.model_rebuild()
