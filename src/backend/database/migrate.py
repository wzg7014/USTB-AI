#!/usr/bin/env python3
"""
数据库迁移脚本
用于创建和管理USTB AI教务助手数据库表结构
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

# 直接导入，避免相对导入问题
import asyncio
import aiomysql
from urllib.parse import urlparse

# 数据库配置
DATABASE_CONFIG = {
    'host': 'rm-2zeem9cul93l70ieleo.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'USTB',
    'password': 'wzg7014ok@Work',
    'db': 'ustb',
    'charset': 'utf8mb4',
    'autocommit': True
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """数据库迁移器"""

    def __init__(self):
        self.connection = None

    async def init(self):
        """初始化数据库连接"""
        try:
            self.connection = await aiomysql.connect(**DATABASE_CONFIG)
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {str(e)}")
            raise
    
    async def read_sql_file(self, file_path: str) -> str:
        """读取SQL文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"SQL文件不存在: {file_path}")
            raise
        except Exception as e:
            logger.error(f"读取SQL文件失败: {str(e)}")
            raise
    
    async def execute_sql_file(self, file_path: str):
        """执行SQL文件"""
        logger.info(f"执行SQL文件: {file_path}")

        sql_content = await self.read_sql_file(file_path)

        # 移除注释和空行，然后分割SQL语句
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)

        # 重新组合并分割语句
        clean_sql = ' '.join(lines)
        statements = [stmt.strip() for stmt in clean_sql.split(';') if stmt.strip()]

        success_count = 0
        error_count = 0

        async with self.connection.cursor() as cursor:
            for i, statement in enumerate(statements, 1):
                try:
                    # 检查是否是有效的SQL语句
                    statement_upper = statement.upper()
                    if any(statement_upper.startswith(keyword) for keyword in
                          ['CREATE', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP', 'SET']):
                        await cursor.execute(statement)
                        success_count += 1
                        logger.info(f"✅ 语句 {i} 执行成功: {statement.split()[0]} {statement.split()[1] if len(statement.split()) > 1 else ''}")
                    else:
                        logger.info(f"⏭️ 跳过语句 {i}: {statement[:50]}...")

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 语句 {i} 执行失败: {str(e)}")
                    logger.error(f"   语句内容: {statement[:200]}...")

        logger.info(f"SQL文件执行完成: 成功 {success_count} 条，失败 {error_count} 条")
        return success_count, error_count
    
    async def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            query = """
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            """
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (table_name,))
                result = await cursor.fetchone()
                return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"检查表存在性失败: {str(e)}")
            return False
    
    async def get_table_list(self) -> list:
        """获取数据库中的表列表"""
        try:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY table_name
            """
            async with self.connection.cursor() as cursor:
                await cursor.execute(query)
                results = await cursor.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            return []
    
    async def create_tables(self):
        """创建数据库表"""
        logger.info("🚀 开始创建数据库表...")
        
        schema_file = Path(__file__).parent / "schema.sql"
        
        if not schema_file.exists():
            logger.error(f"Schema文件不存在: {schema_file}")
            return False
        
        try:
            success_count, error_count = await self.execute_sql_file(str(schema_file))
            
            if error_count == 0:
                logger.info("✅ 数据库表创建成功！")
                return True
            else:
                logger.warning(f"⚠️ 数据库表创建完成，但有 {error_count} 个错误")
                return False
                
        except Exception as e:
            logger.error(f"❌ 数据库表创建失败: {str(e)}")
            return False
    
    async def verify_tables(self):
        """验证表结构"""
        logger.info("🔍 验证数据库表结构...")
        
        expected_tables = [
            'users', 'chat_sessions', 'chat_messages', 'user_feedback',
            'categories', 'search_history', 'system_config', 'api_logs'
        ]
        
        existing_tables = await self.get_table_list()
        
        missing_tables = []
        for table in expected_tables:
            if table not in existing_tables:
                missing_tables.append(table)
            else:
                logger.info(f"✅ 表 {table} 存在")
        
        if missing_tables:
            logger.error(f"❌ 缺失表: {', '.join(missing_tables)}")
            return False
        else:
            logger.info("✅ 所有必需的表都已创建")
            return True
    
    async def show_database_info(self):
        """显示数据库信息"""
        logger.info("📊 数据库信息:")

        try:
            async with self.connection.cursor() as cursor:
                # 数据库基本信息
                await cursor.execute("SELECT DATABASE() as db_name, VERSION() as version")
                db_info = await cursor.fetchone()
                if db_info:
                    logger.info(f"   数据库名: {db_info[0]}")
                    logger.info(f"   MySQL版本: {db_info[1]}")

                # 表统计信息
                tables = await self.get_table_list()
                logger.info(f"   表数量: {len(tables)}")

                for table in tables:
                    try:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        result = await cursor.fetchone()
                        count = result[0] if result else 0
                        logger.info(f"   - {table}: {count} 条记录")
                    except Exception as e:
                        logger.warning(f"   - {table}: 无法获取记录数 ({str(e)})")

        except Exception as e:
            logger.error(f"获取数据库信息失败: {str(e)}")

async def main():
    """主函数"""
    logger.info("🎯 USTB AI教务助手数据库迁移工具")
    logger.info("=" * 50)
    
    migrator = DatabaseMigrator()
    
    try:
        # 初始化数据库连接
        await migrator.init()
        logger.info("✅ 数据库连接成功")
        
        # 显示当前数据库信息
        await migrator.show_database_info()
        
        # 创建表
        success = await migrator.create_tables()
        
        if success:
            # 验证表结构
            await migrator.verify_tables()
            
            # 显示最终数据库信息
            logger.info("\n" + "=" * 50)
            logger.info("🎉 迁移完成后的数据库信息:")
            await migrator.show_database_info()
            
            logger.info("\n✅ 数据库迁移成功完成！")
        else:
            logger.error("\n❌ 数据库迁移失败！")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ 迁移过程中发生错误: {str(e)}")
        sys.exit(1)
    
    finally:
        # 关闭数据库连接
        if migrator.connection:
            migrator.connection.close()

if __name__ == "__main__":
    asyncio.run(main())
