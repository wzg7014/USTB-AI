"""
USTB AI教务助手后端配置
包含数据库连接、API配置、安全设置等
"""

import os
from typing import Optional

class Config:
    """应用配置类"""
    
    # 基础配置
    APP_NAME = "USTB AI教务助手 API"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    
    # 数据库配置 - 阿里云MySQL
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "mysql+aiomysql://USTB:wzg7014ok%40Work@rm-2zeem9cul93l70ieleo.mysql.rds.aliyuncs.com:3306/ustb?charset=utf8mb4"
    )
    
    # 数据库连接池配置
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    # Redis配置（可选，用于缓存）
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    
    # RAG系统配置（已弃用，使用混合API替代）
    RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
    RAG_API_TIMEOUT = float(os.getenv("RAG_API_TIMEOUT", "30.0"))

    # 混合API系统配置（新）
    HYBRID_API_URL = os.getenv("HYBRID_API_URL", "http://localhost:8003")
    HYBRID_API_TIMEOUT = float(os.getenv("HYBRID_API_TIMEOUT", "35.0"))
    
    # JWT认证配置
    SECRET_KEY = os.getenv("SECRET_KEY", "ustb-ai-assistant-secret-key-2025")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24小时
    
    # API配置
    API_V1_PREFIX = "/api/v1"
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # 文件上传配置
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/ustb_backend.log")
    
    # 性能配置
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    
    # 缓存配置
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1小时
    CATEGORIES_CACHE_TTL = int(os.getenv("CATEGORIES_CACHE_TTL", "1800"))  # 30分钟
    
    # 安全配置
    ALLOWED_HOSTS = ["*"]  # 生产环境应该限制具体域名
    TRUSTED_HOSTS = ["localhost", "127.0.0.1", "*.ustb.edu.cn"]

# 创建配置实例
config = Config()

# 数据库表名常量
class TableNames:
    """数据库表名常量"""
    USERS = "users"
    CHAT_SESSIONS = "chat_sessions"
    CHAT_MESSAGES = "chat_messages"
    USER_FEEDBACK = "user_feedback"
    CATEGORIES = "categories"
    SEARCH_HISTORY = "search_history"
    SYSTEM_CONFIG = "system_config"
    API_LOGS = "api_logs"

# 创建表名实例
tables = TableNames()
