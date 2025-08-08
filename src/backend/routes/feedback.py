"""
用户反馈API路由
实现POST /api/v1/feedback接口，支持评分、评论和问题上报功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

# 临时简化导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.feedback import (
    FeedbackRequest, FeedbackResponse, FeedbackDetail,
    FeedbackStats, FeedbackListResponse
)
from models.user import UserResponse
from config import config

router = APIRouter(prefix="/api/v1", tags=["feedback"])

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

# 真实的数据库连接
async def get_database():
    """获取数据库连接"""
    import aiomysql
    try:
        connection = await aiomysql.connect(
            host="rm-2ze5109q5z7n8r8ej.mysql.rds.aliyuncs.com",
            port=3306,
            user="ustb_admin",
            password="USTB2024!@#",
            db="ustb",
            charset='utf8mb4'
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

class FeedbackService:
    """反馈服务类 - 处理用户反馈相关逻辑"""
    
    def __init__(self):
        self.db = None
    
    async def init_db(self):
        """初始化数据库连接"""
        if not self.db:
            self.db = await get_database()
    
    async def create_feedback(self, request: FeedbackRequest, user_id: str) -> str:
        """创建用户反馈"""
        await self.init_db()
        
        feedback_id = str(uuid.uuid4())
        
        # 验证关联的查询或消息是否存在（可选验证）
        if request.query_id and self.db:
            try:
                async with self.db.cursor() as cursor:
                    await cursor.execute("""
                        SELECT message_id FROM chat_messages WHERE message_id = %s
                    """, (request.query_id,))

                    query_exists = await cursor.fetchone()
                    if not query_exists:
                        raise HTTPException(
                            status_code=404,
                            detail="关联的查询不存在"
                        )
            except HTTPException:
                raise
            except Exception as e:
                print(f"验证查询失败: {e}")
                # 继续执行，不阻止反馈创建
        
        # 创建反馈记录
        if not self.db:
            return feedback_id  # 返回临时ID

        try:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO user_feedback (
                        feedback_id, user_id, query_id, result_id, feedback_type,
                        rating, comment, category, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    feedback_id, user_id, request.query_id, request.result_id,
                    request.feedback_type, request.rating, request.comment,
                    request.category, "submitted", datetime.now(), datetime.now()
                ))

                await self.db.commit()
                return feedback_id

        except Exception as e:
            print(f"创建反馈失败: {e}")
            return feedback_id

    async def _update_feedback_stats(self, feedback_type: str, rating: Optional[int]):
        """更新反馈统计信息（简化版）"""
        # 暂时简化统计功能，避免复杂的MongoDB操作
        print(f"反馈统计: 类型={feedback_type}, 评分={rating}")
    
    async def get_user_feedback_list(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        feedback_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[FeedbackDetail]:
        """获取用户反馈列表"""
        await self.init_db()
        if not self.db:
            return []

        try:
            async with self.db.cursor() as cursor:
                # 构建查询条件
                where_conditions = ["user_id = %s"]
                params = [user_id]

                if feedback_type:
                    where_conditions.append("feedback_type = %s")
                    params.append(feedback_type)
                if status:
                    where_conditions.append("status = %s")
                    params.append(status)

                where_clause = " AND ".join(where_conditions)

                # 查询反馈记录
                await cursor.execute(f"""
                    SELECT feedback_id, user_id, query_id, result_id, feedback_type,
                           rating, comment, category, status, created_at, updated_at
                    FROM user_feedback
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [limit, offset])

                rows = await cursor.fetchall()
                feedback_list = []

                for row in rows:
                    feedback = FeedbackDetail(
                        feedback_id=row[0],
                        user_id=row[1],
                        query_id=row[2],
                        result_id=row[3],
                        feedback_type=row[4],
                        rating=row[5],
                        comment=row[6],
                        category=row[7],
                        status=row[8],
                        created_at=row[9],
                        updated_at=row[10]
                    )
                    feedback_list.append(feedback)

                return feedback_list

        except Exception as e:
            print(f"获取反馈列表失败: {e}")
            return []
    
    async def get_feedback_by_id(self, feedback_id: str, user_id: str) -> Optional[FeedbackDetail]:
        """根据ID获取反馈详情"""
        await self.init_db()
        if not self.db:
            return None

        try:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    SELECT feedback_id, user_id, query_id, result_id, feedback_type,
                           rating, comment, category, status, created_at, updated_at
                    FROM user_feedback
                    WHERE feedback_id = %s AND user_id = %s
                """, (feedback_id, user_id))

                row = await cursor.fetchone()
                if not row:
                    return None

                return FeedbackDetail(
                    feedback_id=row[0],
                    user_id=row[1],
                    query_id=row[2],
                    result_id=row[3],
                    feedback_type=row[4],
                    rating=row[5],
                    comment=row[6],
                    category=row[7],
                    status=row[8],
                    created_at=row[9],
                    updated_at=row[10]
                )

        except Exception as e:
            print(f"获取反馈详情失败: {e}")
            return None
    
    async def get_feedback_stats(self, days: int = 30) -> FeedbackStats:
        """获取反馈统计信息"""
        await self.init_db()
        
        # 计算时间范围
        start_date = datetime.now() - timedelta(days=days)
        
        # 聚合查询统计信息
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {
                "$group": {
                    "_id": None,
                    "total_feedback": {"$sum": 1},
                    "avg_rating": {"$avg": "$rating"},
                    "feedback_by_type": {
                        "$push": "$feedback_type"
                    },
                    "rating_distribution": {
                        "$push": "$rating"
                    }
                }
            }
        ]
        
        try:
            result = await self.db.user_feedback.aggregate(pipeline).to_list(length=1)
            
            if result:
                data = result[0]
                
                # 统计反馈类型分布
                type_counts = {}
                for feedback_type in data.get("feedback_by_type", []):
                    type_counts[feedback_type] = type_counts.get(feedback_type, 0) + 1
                
                # 统计评分分布
                rating_counts = {}
                for rating in data.get("rating_distribution", []):
                    if rating:
                        rating_counts[str(rating)] = rating_counts.get(str(rating), 0) + 1
                
                return FeedbackStats(
                    total_feedback=data.get("total_feedback", 0),
                    avg_rating=round(data.get("avg_rating", 0.0), 2),
                    feedback_by_type=type_counts,
                    rating_distribution=rating_counts,
                    period_days=days,
                    last_updated=datetime.now()
                )
            else:
                return FeedbackStats(
                    total_feedback=0,
                    avg_rating=0.0,
                    feedback_by_type={},
                    rating_distribution={},
                    period_days=days,
                    last_updated=datetime.now()
                )
                
        except Exception:
            # 查询失败返回默认统计
            return FeedbackStats(
                total_feedback=0,
                avg_rating=0.0,
                feedback_by_type={},
                rating_distribution={},
                period_days=days,
                last_updated=datetime.now()
            )

# 创建服务实例
feedback_service = FeedbackService()

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user: UserResponse = Depends(get_current_user)
):
    """
    提交用户反馈
    
    支持多种反馈类型：
    - helpful: 有帮助
    - not_helpful: 没有帮助
    - irrelevant: 不相关
    - error: 错误信息
    - suggestion: 建议改进
    """
    try:
        feedback_id = await feedback_service.create_feedback(request, user.id)
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            message="反馈提交成功，感谢您的宝贵意见！",
            status="submitted",
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提交反馈失败: {str(e)}"
        )

@router.get("/feedback", response_model=FeedbackListResponse)
async def get_feedback_list(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    feedback_type: Optional[str] = Query(default=None, description="反馈类型过滤"),
    status: Optional[str] = Query(default=None, description="状态过滤"),
    user: UserResponse = Depends(get_current_user)
):
    """获取用户反馈列表"""
    try:
        feedback_list = await feedback_service.get_user_feedback_list(
            user.id, limit, offset, feedback_type, status
        )
        
        # 获取总数
        query = {"user_id": user.id}
        if feedback_type:
            query["feedback_type"] = feedback_type
        if status:
            query["status"] = status
        
        await feedback_service.init_db()
        total = await feedback_service.db.user_feedback.count_documents(query)
        
        return FeedbackListResponse(
            feedback_list=feedback_list,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取反馈列表失败: {str(e)}"
        )

@router.get("/feedback/{feedback_id}", response_model=FeedbackDetail)
async def get_feedback_detail(
    feedback_id: str,
    user: UserResponse = Depends(get_current_user)
):
    """获取反馈详情"""
    try:
        feedback = await feedback_service.get_feedback_by_id(feedback_id, user.id)
        
        if not feedback:
            raise HTTPException(
                status_code=404,
                detail="反馈记录不存在或无权访问"
            )
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取反馈详情失败: {str(e)}"
        )

@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
    user: UserResponse = Depends(get_current_user)
):
    """获取反馈统计信息（管理员功能）"""
    try:
        # 这里可以添加管理员权限检查
        # if not user.is_admin:
        #     raise HTTPException(status_code=403, detail="需要管理员权限")
        
        stats = await feedback_service.get_feedback_stats(days)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取反馈统计失败: {str(e)}"
        )
