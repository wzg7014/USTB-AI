"""
聊天对话API路由
实现POST /api/v1/chat接口，集成RAG系统，支持流式对话和上下文管理
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional, AsyncGenerator
import httpx
import json
import time
import uuid
from datetime import datetime

# 临时简化导入，避免循环导入问题
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.chat import ChatRequest, ChatResponse, ChatMessage, ChatSession
from models.user import UserResponse
from config import config

router = APIRouter(prefix="/api/v1", tags=["chat"])

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

# 模拟数据库服务
class MockDatabase:
    def __init__(self):
        self.chat_sessions = MockCollection("chat_sessions")
        self.chat_messages = MockCollection("chat_messages")

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = []

    async def insert_one(self, document):
        self.data.append(document)
        return type('Result', (), {'inserted_id': f"{self.name}_{len(self.data)}"})()

    async def find_one(self, query):
        # 简单的查询匹配
        for doc in self.data:
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                return doc
        return None

    def find(self, query):
        return MockCursor([doc for doc in self.data if self._match_query(doc, query)])

    async def update_one(self, query, update):
        for doc in self.data:
            if self._match_query(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for key, value in update["$inc"].items():
                        doc[key] = doc.get(key, 0) + value
                return type('Result', (), {'modified_count': 1})()
        return type('Result', (), {'modified_count': 0})()

    def _match_query(self, doc, query):
        for key, value in query.items():
            if doc.get(key) != value:
                return False
        return True

class MockCursor:
    def __init__(self, data):
        self.data = data

    def sort(self, key, direction):
        if direction == -1:
            self.data.sort(key=lambda x: x.get(key, ""), reverse=True)
        else:
            self.data.sort(key=lambda x: x.get(key, ""))
        return self

    def limit(self, count):
        self.data = self.data[:count]
        return self

    async def to_list(self, length=None):
        return self.data[:length] if length else self.data

# 数据库连接池管理
class DatabasePool:
    """数据库连接池管理器"""
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        """初始化连接池"""
        if self.pool is None:
            import aiomysql
            try:
                self.pool = await aiomysql.create_pool(
                    host="rm-2ze5109q5z7n8r8ej.mysql.rds.aliyuncs.com",
                    port=3306,
                    user="ustb_admin",
                    password="USTB2024!@#",
                    db="ustb",
                    charset='utf8mb4',
                    minsize=2,  # 最小连接数（减少资源占用）
                    maxsize=10,  # 最大连接数（适合小型应用）
                    autocommit=True,  # 自动提交
                    pool_recycle=25200,  # 7小时，小于MySQL默认8小时
                    connect_timeout=10,  # 连接超时10秒
                    echo=False  # 关闭SQL日志
                )
                print("✅ 数据库连接池初始化成功")
            except Exception as e:
                print(f"❌ 数据库连接池初始化失败: {e}")
                self.pool = None

    async def get_connection(self):
        """获取数据库连接"""
        if self.pool is None:
            await self.init_pool()

        if self.pool is None:
            print("⚠️ [数据库] 连接池未初始化，返回None")
            return None

        try:
            conn = await self.pool.acquire()
            print(f"✅ [数据库] 成功获取连接，当前池大小: {self.pool.size}")
            return conn
        except Exception as e:
            import traceback
            print(f"❌ [数据库] 获取连接失败: {type(e).__name__}: {e}")
            print(f"📋 [数据库] 错误堆栈: {traceback.format_exc()}")
            return None

    async def release_connection(self, conn):
        """释放数据库连接"""
        if self.pool and conn:
            try:
                await self.pool.release(conn)
            except Exception as e:
                print(f"释放数据库连接失败: {e}")

    async def close_pool(self):
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

# 全局数据库连接池实例
db_pool = DatabasePool()

class ChatService:
    """聊天服务类 - 处理对话逻辑和RAG系统集成"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def init_db(self):
        """初始化数据库连接池（如果尚未初始化）"""
        if db_pool.pool is None:
            await db_pool.init_pool()

    async def create_chat_session(self, user_id: str, title: str = None) -> str:
        """创建新的聊天会话"""
        session_id = str(uuid.uuid4())
        title = title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        conn = await db_pool.get_connection()
        if not conn:
            return session_id  # 返回临时ID

        try:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO chat_sessions (session_id, user_id, title, created_at, updated_at, message_count, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (session_id, user_id, title, datetime.now(), datetime.now(), 0, True))
        except Exception as e:
            print(f"创建会话失败: {e}")
        finally:
            await db_pool.release_connection(conn)

        return session_id
    
    async def get_chat_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """获取聊天历史记录"""
        conn = await db_pool.get_connection()
        if not conn:
            return []

        try:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT message_id, session_id, role, content, timestamp, metadata
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY timestamp ASC
                    LIMIT %s
                """, (session_id, limit))

                rows = await cursor.fetchall()
                messages = []
                for row in rows:
                    messages.append({
                        "message_id": row[0],
                        "session_id": row[1],
                        "role": row[2],
                        "content": row[3],
                        "timestamp": row[4],
                        "metadata": json.loads(row[5]) if row[5] else {}
                    })
                return messages
        except Exception as e:
            print(f"获取聊天历史失败: {e}")
            return []
        finally:
            await db_pool.release_connection(conn)

    async def save_chat_message(self, session_id: str, message: Dict) -> str:
        """保存聊天消息，返回消息ID（降级模式：暂时跳过数据库操作）"""
        message_id = str(uuid.uuid4())

        # 降级模式：暂时跳过数据库操作，直接返回message_id
        # 这确保聊天功能正常工作，不被数据库连接问题阻塞
        print(f"💾 [降级模式] 跳过数据库保存，消息ID: {message_id}")
        return message_id
    
    async def call_hybrid_api(self, query: str, context: List[Dict] = None) -> Dict:
        """调用混合API系统进行智能问答"""
        import time
        start_time = time.time()

        try:
            print(f"🤖 [混合API] 开始智能问答: {query[:50]}...")

            # 构建混合API请求 - 使用Web API连接器的格式
            hybrid_request = {
                "message": query,
                "max_tokens": 300,
                "temperature": 0.1
            }

            # 调用Web API连接器 (通过SSH隧道连接到AutoDL)
            # 临时硬编码解决配置缓存问题
            api_url = "http://localhost:8003/api/v1/chat"

            response = await self.http_client.post(
                api_url,
                json=hybrid_request,
                timeout=35.0
            )

            elapsed_time = time.time() - start_time

            if response.status_code != 200:
                print(f"❌ [混合API] 失败: HTTP {response.status_code}, 耗时: {elapsed_time:.3f}秒")
                print(f"📋 [混合API] 错误详情: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"混合API系统错误: {response.text}"
                )

            result = response.json()
            attachment_count = len(result.get("attachments", []))
            confidence = result.get("confidence", 0.0)
            print(f"✅ [混合API] 成功: {attachment_count}个附件, 置信度: {confidence:.2f}, 耗时: {elapsed_time:.3f}秒")

            return result

        except httpx.TimeoutException as e:
            elapsed_time = time.time() - start_time
            print(f"⏰ [混合API] 超时: {elapsed_time:.3f}秒")
            raise HTTPException(
                status_code=504,
                detail="混合API系统响应超时，请稍后重试"
            )
        except httpx.ConnectError as e:
            elapsed_time = time.time() - start_time
            print(f"🔌 [混合API] 连接失败: {e}, 耗时: {elapsed_time:.3f}秒")
            raise HTTPException(
                status_code=503,
                detail="混合API系统连接失败，请稍后重试"
            )
        except Exception as e:
            elapsed_time = time.time() - start_time
            import traceback
            print(f"🚨 [混合API] 未知错误: {type(e).__name__}: {e}, 耗时: {elapsed_time:.3f}秒")
            print(f"📋 [混合API] 错误堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"混合API调用失败: {str(e)}"
            )
    
    async def format_hybrid_response(self, hybrid_result: Dict) -> str:
        """格式化混合API响应为用户友好的回答"""

        # 获取主要回答
        main_response = hybrid_result.get("response", "")
        if not main_response:
            return "抱歉，我没有找到相关的教务信息。请尝试换个问题或联系教务处获取帮助。"

        # 构建完整回答
        answer_parts = [main_response]

        # 添加附件信息
        attachments = hybrid_result.get("attachments", [])
        if attachments:
            answer_parts.append("\n📎 **相关教务文档**:")
            for i, attachment in enumerate(attachments[:5], 1):  # 最多显示5个附件
                title = attachment.get('title', '未知文档')
                url = attachment.get('url', '')
                category = attachment.get('category', '')
                publish_date = attachment.get('publish_date', '')

                # 格式化附件信息
                attachment_info = f"{i}. **{title}**"
                if category:
                    attachment_info += f" ({category})"
                if publish_date:
                    attachment_info += f" - {publish_date}"
                if url:
                    attachment_info += f"\n   🔗 链接: {url}"

                answer_parts.append(attachment_info)

        # 添加置信度信息（如果较低则提醒用户）
        confidence = hybrid_result.get("confidence", 0.0)
        if confidence < 0.7:
            answer_parts.append(f"\n💡 **提示**: 回答置信度为 {confidence:.1%}，建议您核实相关信息或联系教务处确认。")

        return "\n".join(answer_parts)
    
    async def process_chat_message(self, request: ChatRequest, user_id: str) -> ChatResponse:
        """处理聊天消息的完整流程"""
        start_time = time.time()
        
        # 创建或获取会话
        session_id = request.session_id
        if not session_id:
            session_id = await self.create_chat_session(user_id, f"关于: {request.message[:20]}...")
        
        # 获取上下文历史
        context = await self.get_chat_history(session_id, limit=5)
        
        # 保存用户消息
        user_message = {
            "role": "user",
            "content": request.message,
            "message_type": "text"
        }
        user_message_id = await self.save_chat_message(session_id, user_message)
        
        try:
            # 调用混合API系统进行智能问答
            hybrid_result = await self.call_hybrid_api(request.message, context)

            # 格式化混合API响应
            ai_response = await self.format_hybrid_response(hybrid_result)

            # 保存AI回答
            ai_message = {
                "role": "assistant",
                "content": ai_response,
                "message_type": "text",
                "hybrid_result": hybrid_result,
                "response_time": time.time() - start_time
            }
            ai_message_id = await self.save_chat_message(session_id, ai_message)

            # 构建响应 - 使用混合API的附件格式，处理日期字段
            rag_results = []
            for attachment in hybrid_result.get("attachments", []):
                # 处理publish_date字段，空字符串转换为None
                if "publish_date" in attachment and attachment["publish_date"] == "":
                    attachment["publish_date"] = None
                rag_results.append(attachment)

            response = ChatResponse(
                session_id=session_id,
                message=ai_response,
                response_time=time.time() - start_time,
                rag_results=rag_results,
                message_id=ai_message_id,
                timestamp=datetime.now()
            )

            return response
            
        except Exception as e:
            # 详细错误日志记录
            import traceback
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
                "session_id": session_id,
                "user_message": request.message[:100] + "..." if len(request.message) > 100 else request.message,
                "timestamp": datetime.now().isoformat()
            }

            print(f"🚨 [聊天API错误] {error_details['error_type']}: {error_details['error_message']}")
            print(f"📍 [错误详情] 会话ID: {session_id}, 用户消息: {error_details['user_message']}")
            print(f"📋 [错误堆栈] {error_details['traceback']}")

            # 保存错误信息（降级模式）
            error_message = {
                "role": "system",
                "content": f"处理失败: {str(e)}",
                "message_type": "error",
                "error_details": error_details
            }
            error_message_id = await self.save_chat_message(session_id, error_message)

            # 返回用户友好的错误响应而不是抛出异常
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "聊天处理失败",
                    "message": "系统暂时无法处理您的请求，请稍后重试",
                    "error_id": error_message_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

# 创建服务实例
chat_service = ChatService()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    user: UserResponse = Depends(get_current_user)
):
    """
    聊天对话接口
    
    与USTB AI教务助手进行对话，支持：
    - 教务问题咨询
    - 上下文对话管理
    - RAG系统集成搜索
    - 聊天历史记录
    """
    try:
        response = await chat_service.process_chat_message(request, user.id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"聊天服务内部错误: {str(e)}"
        )

@router.get("/chat/sessions", response_model=List[ChatSession])
async def get_chat_sessions(
    user: UserResponse = Depends(get_current_user),
    limit: int = 20
):
    """获取用户的聊天会话列表"""
    await chat_service.init_db()

    conn = await db_pool.get_connection()
    if not conn:
        return []

    try:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT session_id, user_id, title, created_at, updated_at, message_count, is_active
                FROM chat_sessions
                WHERE user_id = %s AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user.id, limit))

            rows = await cursor.fetchall()
            sessions = []
            for row in rows:
                sessions.append(ChatSession(
                    session_id=row[0],
                    user_id=row[1],
                    title=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                    message_count=row[5],
                    is_active=bool(row[6])
                ))
            return sessions
    except Exception as e:
        print(f"获取会话列表失败: {e}")
        return []
    finally:
        await db_pool.release_connection(conn)

@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(
    session_id: str,
    user: UserResponse = Depends(get_current_user),
    limit: int = 50
):
    """获取指定会话的聊天消息"""
    # 验证会话所有权
    await chat_service.init_db()

    if not chat_service.db:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    try:
        async with chat_service.db.cursor() as cursor:
            await cursor.execute("""
                SELECT session_id FROM chat_sessions
                WHERE session_id = %s AND user_id = %s AND is_active = 1
            """, (session_id, user.id))

            session = await cursor.fetchone()
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="聊天会话不存在或无权访问"
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"验证会话失败: {e}")
        raise HTTPException(status_code=500, detail="验证会话失败")

    messages = await chat_service.get_chat_history(session_id, limit)
    return [ChatMessage(
        message_id=msg["message_id"],
        session_id=msg["session_id"],
        role=msg["role"],
        content=msg["content"],
        timestamp=msg["timestamp"],
        metadata=msg.get("metadata", {})
    ) for msg in messages]

@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    user: UserResponse = Depends(get_current_user)
):
    """删除聊天会话"""
    await chat_service.init_db()

    if not chat_service.db:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    try:
        async with chat_service.db.cursor() as cursor:
            # 验证会话所有权
            await cursor.execute("""
                SELECT session_id FROM chat_sessions
                WHERE session_id = %s AND user_id = %s AND is_active = 1
            """, (session_id, user.id))

            session = await cursor.fetchone()
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="聊天会话不存在或无权访问"
                )

            # 软删除会话
            await cursor.execute("""
                UPDATE chat_sessions
                SET is_active = 0, deleted_at = %s
                WHERE session_id = %s
            """, (datetime.now(), session_id))

            await chat_service.db.commit()
            return {"message": "聊天会话已删除"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话失败")
