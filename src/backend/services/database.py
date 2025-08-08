"""
数据库连接服务
提供MySQL数据库连接和操作功能
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, MetaData
import aiomysql
from contextlib import asynccontextmanager

from ..config import config

logger = logging.getLogger(__name__)

# SQLAlchemy基础类
Base = declarative_base()
metadata = MetaData()

class DatabaseService:
    """数据库服务类"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._connection_pool = None
        
    async def init_database(self):
        """初始化数据库连接"""
        try:
            # 创建异步引擎
            self.engine = create_async_engine(
                config.DATABASE_URL,
                pool_size=config.DB_POOL_SIZE,
                max_overflow=config.DB_MAX_OVERFLOW,
                pool_timeout=config.DB_POOL_TIMEOUT,
                pool_recycle=config.DB_POOL_RECYCLE,
                echo=config.DEBUG,
                future=True
            )
            
            # 创建会话工厂
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 测试连接
            await self.test_connection()
            logger.info("✅ 数据库连接初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {str(e)}")
            raise
    
    async def test_connection(self):
        """测试数据库连接"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            logger.info("✅ 数据库连接测试成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接测试失败: {str(e)}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """获取数据库会话上下文管理器"""
        if not self.session_factory:
            await self.init_database()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行查询语句"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text(query), params or {})
                rows = result.fetchall()
                
                # 转换为字典列表
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            raise
    
    async def execute_command(self, command: str, params: Dict = None) -> int:
        """执行命令语句（INSERT, UPDATE, DELETE）"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text(command), params or {})
                await session.commit()
                return result.rowcount
                
        except Exception as e:
            logger.error(f"命令执行失败: {str(e)}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("数据库连接已关闭")

# 全局数据库服务实例
db_service = DatabaseService()

async def get_database() -> DatabaseService:
    """获取数据库服务实例"""
    if not db_service.engine:
        await db_service.init_database()
    return db_service

async def init_database():
    """初始化数据库"""
    await db_service.init_database()

async def close_database():
    """关闭数据库连接"""
    await db_service.close()

# 简化的数据库操作类
class SimpleDB:
    """简化的数据库操作类"""
    
    def __init__(self):
        self.db = None
    
    async def init(self):
        """初始化数据库连接"""
        if not self.db:
            self.db = await get_database()
    
    async def fetch_one(self, query: str, params: Dict = None) -> Optional[Dict]:
        """查询单条记录"""
        await self.init()
        results = await self.db.execute_query(query, params)
        return results[0] if results else None
    
    async def fetch_all(self, query: str, params: Dict = None) -> List[Dict]:
        """查询多条记录"""
        await self.init()
        return await self.db.execute_query(query, params)
    
    async def execute(self, command: str, params: Dict = None) -> int:
        """执行命令"""
        await self.init()
        return await self.db.execute_command(command, params)
    
    async def insert(self, table: str, data: Dict) -> int:
        """插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f':{key}' for key in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return await self.execute(query, data)
    
    async def update(self, table: str, data: Dict, where: str, where_params: Dict = None) -> int:
        """更新数据"""
        set_clause = ', '.join([f'{key} = :{key}' for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        # 合并参数
        params = data.copy()
        if where_params:
            params.update(where_params)
        
        return await self.execute(query, params)
    
    async def delete(self, table: str, where: str, params: Dict = None) -> int:
        """删除数据"""
        query = f"DELETE FROM {table} WHERE {where}"
        return await self.execute(query, params)
    
    async def count(self, table: str, where: str = None, params: Dict = None) -> int:
        """统计记录数"""
        query = f"SELECT COUNT(*) as count FROM {table}"
        if where:
            query += f" WHERE {where}"
        
        result = await self.fetch_one(query, params)
        return result['count'] if result else 0

# 创建简化数据库实例
simple_db = SimpleDB()
