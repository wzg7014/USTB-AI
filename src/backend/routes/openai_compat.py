"""
OpenAI兼容API路由
为ChatGPT-Next-Web前端提供OpenAI兼容的API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import time
import json
import uuid
import asyncio

from routes.chat import ChatService, ChatRequest, get_current_user
from models.user import UserResponse

router = APIRouter(prefix="/v1", tags=["openai-compat"])

# OpenAI兼容的数据模型
class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = 300
    stream: Optional[bool] = False

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: str

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str

class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[OpenAIModel]

# 简化的认证函数（兼容OpenAI API Key格式）
async def get_openai_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """OpenAI兼容的认证函数"""
    # 接受任何Bearer token，返回测试用户
    return UserResponse(
        id="openai_user_001",
        username="openai_test_user",
        email="openai@ustb.edu.cn",
        is_active=True,
        search_count=0,
        last_login=None,
        created_at=datetime.now()
    )

# 创建聊天服务实例
chat_service = ChatService()

@router.get("/models", response_model=OpenAIModelsResponse)
async def list_models():
    """列出可用模型（OpenAI兼容）"""
    models = [
        OpenAIModel(
            id="ustb-assistant",
            created=int(time.time()),
            owned_by="ustb"
        ),
        OpenAIModel(
            id="ustb-rag-assistant", 
            created=int(time.time()),
            owned_by="ustb"
        )
    ]
    
    return OpenAIModelsResponse(data=models)

@router.post("/chat/completions")
async def create_chat_completion(
    request: OpenAIChatRequest,
    user: UserResponse = Depends(get_openai_user)
):
    """
    创建聊天完成（OpenAI兼容）

    将OpenAI格式的请求转换为我们的内部格式，
    然后调用混合API系统获取回答
    支持流式和非流式响应
    """

    # 检查是否请求流式响应
    if request.stream:
        return await create_chat_completion_stream(request, user)

    try:
        # 提取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_user_message = user_messages[-1].content
        
        # 构建内部聊天请求
        internal_request = ChatRequest(
            message=last_user_message,
            session_id=f"openai_session_{user.id}_{int(time.time())}"
        )
        
        # 调用内部聊天服务
        start_time = time.time()
        internal_response = await chat_service.process_chat_message(internal_request, user.id)
        response_time = time.time() - start_time
        
        # 转换为OpenAI格式的响应
        openai_response = OpenAIChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                OpenAIChoice(
                    index=0,
                    message=OpenAIMessage(
                        role="assistant",
                        content=internal_response.message
                    ),
                    finish_reason="stop"
                )
            ],
            usage=OpenAIUsage(
                prompt_tokens=len(last_user_message.split()),
                completion_tokens=len(internal_response.message.split()),
                total_tokens=len(last_user_message.split()) + len(internal_response.message.split())
            )
        )
        
        return openai_response
        
    except Exception as e:
        print(f"🚨 OpenAI兼容API错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """获取特定模型信息（OpenAI兼容）"""
    if model_id in ["ustb-assistant", "ustb-rag-assistant"]:
        return OpenAIModel(
            id=model_id,
            created=int(time.time()),
            owned_by="ustb"
        )
    else:
        raise HTTPException(status_code=404, detail="Model not found")

# 健康检查端点
@router.get("/health")
async def openai_health_check():
    """OpenAI兼容API健康检查"""
    return {
        "status": "healthy",
        "service": "USTB OpenAI Compatible API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

async def create_chat_completion_stream(
    request: OpenAIChatRequest,
    user: UserResponse
):
    """
    创建流式聊天完成（OpenAI兼容）

    将完整响应分块发送，模拟流式响应
    """
    from fastapi.responses import StreamingResponse
    import json

    try:
        # 提取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].content

        # 构建内部聊天请求
        internal_request = ChatRequest(
            message=last_user_message,
            session_id=f"openai_session_{user.id}_{int(time.time())}"
        )

        # 调用内部聊天服务获取完整响应
        start_time = time.time()
        internal_response = await chat_service.process_chat_message(internal_request, user.id)
        response_time = time.time() - start_time

        # 生成流式响应
        async def generate_stream():
            # 基础响应信息
            chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())

            # 将完整消息分块发送
            content = internal_response.message
            chunk_size = 10  # 每次发送10个字符

            for i in range(0, len(content), chunk_size):
                chunk_content = content[i:i + chunk_size]

                # 构建流式响应块
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": chunk_content
                            },
                            "finish_reason": None
                        }
                    ]
                }

                # 发送数据块
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                # 模拟打字延迟
                await asyncio.sleep(0.05)

            # 发送结束块
            final_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }

            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )

    except Exception as e:
        print(f"🚨 OpenAI流式API错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
