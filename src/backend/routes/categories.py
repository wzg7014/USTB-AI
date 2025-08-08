"""
教务分类API路由
实现GET /api/v1/categories接口，返回所有可用的教务分类和统计信息
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Optional
import httpx
from datetime import datetime, timedelta

# 临时简化导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.categories import CategoryResponse, CategoryStats, CategoryDetail
from models.user import UserResponse
from config import config

router = APIRouter(prefix="/api/v1", tags=["categories"])

# 简化的认证函数
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """简化的用户认证"""
    return UserResponse(
        id="user_001",
        username="test_user",
        email="test@ustb.edu.cn",
        is_active=True,
        search_count=0,
        last_login=None,
        created_at=datetime.now()
    )

# 简化的数据库连接
async def get_database():
    """简化的数据库连接"""
    return None

class CategoryService:
    """分类服务类 - 处理教务分类相关逻辑"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=10.0)
        self.db = None
        # 缓存分类数据，避免频繁查询
        self._categories_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5分钟缓存
    
    async def init_db(self):
        """初始化数据库连接"""
        if not self.db:
            self.db = await get_database()
    
    async def get_categories_from_rag(self) -> List[Dict]:
        """从RAG系统获取分类信息"""
        try:
            response = await self.http_client.get(
                f"{config.RAG_API_URL}/api/v1/categories",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json().get("categories", [])
            else:
                # RAG系统可能没有分类接口，返回默认分类
                return self._get_default_categories()
                
        except Exception:
            # 网络错误或RAG系统不可用，返回默认分类
            return self._get_default_categories()
    
    def _get_default_categories(self) -> List[Dict]:
        """获取默认的教务分类"""
        return [
            {
                "id": "course_selection",
                "name": "选课管理",
                "display_name": "选课管理",
                "description": "课程选择、退课、课程表查询等",
                "icon": "📚",
                "parent_id": None,
                "level": 1,
                "sort_order": 1
            },
            {
                "id": "exam_management",
                "name": "考试管理", 
                "display_name": "考试管理",
                "description": "考试安排、成绩查询、补考申请等",
                "icon": "📝",
                "parent_id": None,
                "level": 1,
                "sort_order": 2
            },
            {
                "id": "student_status",
                "name": "学籍管理",
                "display_name": "学籍管理", 
                "description": "学籍变更、休学复学、转专业等",
                "icon": "👨‍🎓",
                "parent_id": None,
                "level": 1,
                "sort_order": 3
            },
            {
                "id": "graduation",
                "name": "毕业管理",
                "display_name": "毕业管理",
                "description": "毕业要求、学位申请、毕业证书等",
                "icon": "🎓",
                "parent_id": None,
                "level": 1,
                "sort_order": 4
            },
            {
                "id": "scholarship",
                "name": "奖助学金",
                "display_name": "奖助学金",
                "description": "奖学金申请、助学金、勤工助学等",
                "icon": "💰",
                "parent_id": None,
                "level": 1,
                "sort_order": 5
            },
            {
                "id": "international",
                "name": "国际交流",
                "display_name": "国际交流",
                "description": "交换生项目、海外学习、国际合作等",
                "icon": "🌍",
                "parent_id": None,
                "level": 1,
                "sort_order": 6
            },
            {
                "id": "campus_life",
                "name": "校园生活",
                "display_name": "校园生活",
                "description": "住宿管理、食堂服务、校园卡等",
                "icon": "🏫",
                "parent_id": None,
                "level": 1,
                "sort_order": 7
            },
            {
                "id": "other",
                "name": "其他事务",
                "display_name": "其他事务",
                "description": "其他教务相关事务",
                "icon": "📋",
                "parent_id": None,
                "level": 1,
                "sort_order": 8
            }
        ]
    
    async def get_category_stats(self, category_id: str = None) -> Dict:
        """获取分类统计信息"""
        await self.init_db()
        
        # 构建查询条件
        match_condition = {}
        if category_id:
            match_condition["category"] = category_id
        
        # 聚合查询统计信息
        pipeline = [
            {"$match": match_condition},
            {
                "$group": {
                    "_id": "$category" if not category_id else None,
                    "document_count": {"$sum": 1},
                    "recent_searches": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$gte": [
                                        "$last_accessed",
                                        datetime.now() - timedelta(days=7)
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    },
                    "avg_score": {"$avg": "$qwen_score"}
                }
            }
        ]
        
        try:
            # 从搜索历史表获取统计
            stats = await self.db.search_history.aggregate(pipeline).to_list(length=100)
            
            if category_id:
                # 单个分类统计
                return stats[0] if stats else {
                    "document_count": 0,
                    "recent_searches": 0,
                    "avg_score": 0.0
                }
            else:
                # 所有分类统计
                return {stat["_id"]: stat for stat in stats}
                
        except Exception:
            # 数据库查询失败，返回默认值
            return {}
    
    async def get_categories_with_stats(self, include_stats: bool = True) -> List[CategoryDetail]:
        """获取带统计信息的分类列表"""
        # 检查缓存
        now = datetime.now()
        if (self._categories_cache and self._cache_timestamp and 
            (now - self._cache_timestamp).seconds < self._cache_ttl):
            return self._categories_cache
        
        # 获取基础分类信息
        categories = await self.get_categories_from_rag()
        
        # 获取统计信息
        stats_data = {}
        if include_stats:
            stats_data = await self.get_category_stats()
        
        # 构建详细分类信息
        detailed_categories = []
        for cat in categories:
            category_id = cat["id"]
            stats = stats_data.get(category_id, {})
            
            detailed_category = CategoryDetail(
                id=category_id,
                name=cat["name"],
                display_name=cat["display_name"],
                description=cat["description"],
                icon=cat.get("icon", "📁"),
                parent_id=cat.get("parent_id"),
                level=cat.get("level", 1),
                sort_order=cat.get("sort_order", 999),
                document_count=stats.get("document_count", 0),
                recent_searches=stats.get("recent_searches", 0),
                avg_score=stats.get("avg_score", 0.0),
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            detailed_categories.append(detailed_category)
        
        # 按sort_order排序
        detailed_categories.sort(key=lambda x: x.sort_order)
        
        # 更新缓存
        self._categories_cache = detailed_categories
        self._cache_timestamp = now
        
        return detailed_categories
    
    async def get_category_by_id(self, category_id: str) -> Optional[CategoryDetail]:
        """根据ID获取单个分类信息"""
        categories = await self.get_categories_with_stats()
        
        for category in categories:
            if category.id == category_id:
                return category
        
        return None
    
    async def search_categories(self, query: str) -> List[CategoryDetail]:
        """搜索分类"""
        categories = await self.get_categories_with_stats()
        
        # 简单的文本匹配搜索
        query_lower = query.lower()
        matched_categories = []
        
        for category in categories:
            if (query_lower in category.name.lower() or 
                query_lower in category.display_name.lower() or
                query_lower in category.description.lower()):
                matched_categories.append(category)
        
        return matched_categories

# 创建服务实例
category_service = CategoryService()

@router.get("/categories", response_model=CategoryResponse)
async def get_categories(
    include_stats: bool = Query(default=True, description="是否包含统计信息"),
    parent_id: Optional[str] = Query(default=None, description="父分类ID"),
    level: Optional[int] = Query(default=None, description="分类层级"),
    user: UserResponse = Depends(get_current_user)
):
    """
    获取教务分类列表
    
    返回所有可用的教务分类和统计信息，支持：
    - 分层级分类展示
    - 文档数量统计
    - 最近搜索统计
    - 分类质量评分
    """
    try:
        categories = await category_service.get_categories_with_stats(include_stats)
        
        # 根据条件过滤
        if parent_id is not None:
            categories = [cat for cat in categories if cat.parent_id == parent_id]
        
        if level is not None:
            categories = [cat for cat in categories if cat.level == level]
        
        # 计算总体统计
        total_categories = len(categories)
        total_documents = sum(cat.document_count for cat in categories)
        total_searches = sum(cat.recent_searches for cat in categories)
        
        stats = CategoryStats(
            total_categories=total_categories,
            total_documents=total_documents,
            recent_searches=total_searches,
            avg_documents_per_category=total_documents / total_categories if total_categories > 0 else 0,
            most_popular_category=max(categories, key=lambda x: x.recent_searches).id if categories else None
        )
        
        return CategoryResponse(
            categories=categories,
            stats=stats,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取分类列表失败: {str(e)}"
        )

@router.get("/categories/{category_id}", response_model=CategoryDetail)
async def get_category_detail(
    category_id: str,
    user: UserResponse = Depends(get_current_user)
):
    """获取单个分类的详细信息"""
    try:
        category = await category_service.get_category_by_id(category_id)
        
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"分类 {category_id} 不存在"
            )
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取分类详情失败: {str(e)}"
        )

@router.get("/categories/search", response_model=List[CategoryDetail])
async def search_categories(
    q: str = Query(..., description="搜索关键词", min_length=1),
    user: UserResponse = Depends(get_current_user)
):
    """搜索分类"""
    try:
        categories = await category_service.search_categories(q)
        return categories
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索分类失败: {str(e)}"
        )
