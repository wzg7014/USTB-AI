"""
用户数据模型
定义用户相关的数据结构和数据库操作
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

# 简化ObjectId处理，避免Pydantic v2兼容性问题
# class PyObjectId(ObjectId):
#     """MongoDB ObjectId的Pydantic兼容版本"""
#     pass

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    email: str = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, description="真实姓名", max_length=100)
    student_id: Optional[str] = Field(None, description="学号", max_length=20)
    department: Optional[str] = Field(None, description="院系", max_length=100)

class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., description="密码", min_length=6, max_length=128)

class UserUpdate(BaseModel):
    """更新用户信息"""
    full_name: Optional[str] = None
    department: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserInDB(UserBase):
    """数据库中的用户信息"""
    id: str = Field(..., description="用户ID")
    hashed_password: str
    is_active: bool = True
    preferences: Dict[str, Any] = Field(default_factory=dict)
    search_count: int = 0
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserResponse(UserBase):
    """用户信息响应"""
    id: str
    is_active: bool
    search_count: int
    last_login: Optional[datetime]
    created_at: datetime

class UserPreferences(BaseModel):
    """用户偏好设置"""
    default_search_categories: List[str] = Field(default_factory=list)
    results_per_page: int = Field(default=10, ge=5, le=50)
    language: str = Field(default="zh-CN")
    theme: str = Field(default="light")
    email_notifications: bool = True
    search_history_enabled: bool = True

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    """JWT Token数据"""
    user_id: Optional[str] = None
    username: Optional[str] = None
