#!/usr/bin/env python3
"""
Qwen2.5-7B-Instruct LoRA推理服务 - USTB教务助手 (修复版)
修复了prompt模板不匹配问题，使用与训练数据一致的简单格式
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import torch
import time
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/autodl-tmp/ustb-project/logs/qwen_service_8004.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 请求模型
class InferenceRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 512
    temperature: Optional[float] = 0.1  # 更保守的默认值
    top_p: Optional[float] = 0.95
    do_sample: Optional[bool] = False  # 默认不采样，更稳定

class InferenceResponse(BaseModel):
    response: str
    inference_time: float
    model_name: str

class QwenInferenceService:
    def __init__(self):
        self.app = FastAPI(
            title="USTB教务助手 - Qwen2.5推理服务 (修复版)",
            description="修复了prompt模板问题的USTB教务助手推理服务",
            version="1.1.0"
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 模型相关属性
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "Qwen2.5-7B-Instruct-USTB-Fixed"
        
        # 设置路由
        self.setup_routes()
        
        logger.info(f"推理服务初始化完成，设备: {self.device}")

    def setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "model_loaded": self.model is not None,
                "device": self.device,
                "gpu_available": torch.cuda.is_available()
            }

        @self.app.post("/inference", response_model=InferenceResponse)
        async def generate_response(request: InferenceRequest):
            if self.model is None:
                raise HTTPException(status_code=503, detail="模型未加载")

            try:
                start_time = time.time()

                # 🔧 修复：使用与训练数据匹配的简单prompt格式
                # 训练数据格式：{"instruction": "问题", "input": "", "output": "答案"}
                # 推理格式应该匹配训练时的格式
                full_prompt = f"问题：{request.prompt}\n答案："

                # 编码输入
                inputs = self.tokenizer(
                    full_prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=1024  # 减少长度避免内存问题
                ).to(self.device)

                # 生成回复 - 使用更保守的参数
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=min(request.max_length, 256),  # 限制生成长度
                        temperature=max(request.temperature, 0.01),  # 避免温度为0
                        top_p=request.top_p,
                        do_sample=request.do_sample,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                        repetition_penalty=1.1,  # 避免重复
                        no_repeat_ngram_size=3   # 避免重复n-gram
                    )

                # 解码输出
                response = self.tokenizer.decode(
                    outputs[0][inputs['input_ids'].shape[1]:],
                    skip_special_tokens=True
                ).strip()

                # 清理输出，移除可能的格式问题
                response = self.clean_response(response)

                inference_time = time.time() - start_time

                logger.info(f"推理完成，耗时: {inference_time:.2f}秒，输出长度: {len(response)}")

                return InferenceResponse(
                    response=response,
                    inference_time=inference_time,
                    model_name=self.model_name
                )

            except Exception as e:
                logger.error(f"推理错误: {str(e)}")
                raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    def clean_response(self, response: str) -> str:
        """清理响应内容，移除异常格式"""
        # 移除可能的图片链接格式
        import re
        response = re.sub(r'!\[.*?\]\(.*?\)', '', response)
        response = re.sub(r'<img.*?>', '', response)
        response = re.sub(r'https?://[^\s]+', '', response)
        
        # 移除重复的特殊字符
        response = re.sub(r'!{3,}', '', response)
        response = re.sub(r'#{3,}', '', response)
        
        # 清理空行和多余空格
        response = re.sub(r'\n\s*\n', '\n', response)
        response = response.strip()
        
        return response

    async def load_model(self):
        """加载模型和分词器"""
        try:
            logger.info("开始加载训练过的模型...")

            # 直接使用训练过的模型路径
            trained_model_path = "/root/autodl-tmp/ustb-project/models/trained"

            # 加载分词器
            logger.info("加载分词器...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                trained_model_path,
                trust_remote_code=True,
                use_fast=False
            )

            # 设置pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # 直接加载训练过的模型
            logger.info("加载训练过的模型...")
            self.model = AutoModelForCausalLM.from_pretrained(
                trained_model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )

            # 设置为评估模式
            self.model.eval()

            logger.info("训练过的模型加载完成！")

        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise e

    def run(self, host="0.0.0.0", port=8004):
        """启动推理服务"""
        logger.info(f"启动推理服务，地址: http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

def main():
    """主函数"""
    service = QwenInferenceService()

    # 加载模型
    import asyncio
    asyncio.run(service.load_model())

    # 启动服务
    service.run()

if __name__ == "__main__":
    main()
