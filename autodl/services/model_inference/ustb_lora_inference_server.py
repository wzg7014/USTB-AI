#!/usr/bin/env python3
"""
USTB AI教务助手 - LoRA模型推理服务
基于Qwen2.5-7B-Instruct + LoRA适配器的专业推理服务

创建时间: 2025-08-07
作者: 模型训练专家 (重写版)
状态: 生产就绪
"""

import os
import sys
import asyncio
import uvicorn
import torch
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/autodl-tmp/ustb-project/logs/lora_inference.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API模型定义
class InferenceRequest(BaseModel):
    query: str
    max_tokens: int = 512
    temperature: float = 0.1
    top_p: float = 0.9
    do_sample: bool = True
    system_prompt: Optional[str] = None

class InferenceResponse(BaseModel):
    query: str
    response: str
    inference_time: float
    model_name: str
    tokens_generated: int
    confidence: float
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    gpu_available: bool
    gpu_memory_used: float
    gpu_memory_total: float
    service_uptime: float
    model_path: str
    version: str

class USTBLoRAInferenceService:
    """USTB LoRA模型推理服务"""
    
    def __init__(self, 
                 base_model_path: str = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct",
                 lora_model_path: str = "/root/autodl-tmp/ustb-project/models/trained"):
        
        # 初始化FastAPI应用
        self.app = FastAPI(
            title="USTB AI教务助手 - LoRA推理服务",
            description="基于Qwen2.5-7B-Instruct + LoRA的USTB教务专业推理服务",
            version="1.0.0"
        )
        
        # CORS配置
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 服务配置
        self.start_time = time.time()
        self.base_model_path = base_model_path
        self.lora_model_path = lora_model_path
        self.gpu_available = torch.cuda.is_available()
        self.device = torch.device("cuda:0" if self.gpu_available else "cpu")
        
        # 模型相关
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.model_name = "Qwen2.5-7B-Instruct-USTB-LoRA"
        
        # 性能统计
        self.request_count = 0
        self.total_response_time = 0.0
        self.total_tokens_generated = 0
        
        # 默认系统提示词
        self.default_system_prompt = (
            "你是北京科技大学(USTB)的AI教务助手，专门为学生提供教务相关的咨询和帮助。"
            "请基于学校的教务规定和流程，为学生提供准确、实用的指导和建议。"
            "如果遇到不确定的问题，请建议学生联系相关部门或查看官方通知。"
        )
        
        logger.info(f"USTB LoRA推理服务初始化")
        logger.info(f"基座模型: {self.base_model_path}")
        logger.info(f"LoRA模型: {self.lora_model_path}")
        logger.info(f"GPU可用: {self.gpu_available}")
        logger.info(f"设备: {self.device}")
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """健康检查接口"""
            gpu_memory_used = 0.0
            gpu_memory_total = 0.0
            
            if self.gpu_available:
                gpu_memory_used = torch.cuda.memory_allocated(0) / 1024**3
                gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            return HealthResponse(
                status="healthy" if self.model_loaded else "loading",
                model_loaded=self.model_loaded,
                gpu_available=self.gpu_available,
                gpu_memory_used=gpu_memory_used,
                gpu_memory_total=gpu_memory_total,
                service_uptime=time.time() - self.start_time,
                model_path=self.lora_model_path,
                version="1.0.0"
            )
        
        @self.app.post("/api/v1/inference", response_model=InferenceResponse)
        async def inference(request: InferenceRequest):
            """模型推理接口"""
            if not self.model_loaded:
                raise HTTPException(status_code=503, detail="模型未加载完成")
            
            start_time = time.time()
            
            try:
                # 构建消息
                system_prompt = request.system_prompt or self.default_system_prompt
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.query}
                ]
                
                # 应用聊天模板
                input_text = self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
                
                # 编码输入
                inputs = self.tokenizer(
                    input_text, 
                    return_tensors="pt", 
                    truncation=True, 
                    max_length=2048
                ).to(self.device)
                
                # 生成回答
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=request.max_tokens,
                        temperature=request.temperature,
                        top_p=request.top_p,
                        do_sample=request.do_sample,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                        repetition_penalty=1.1
                    )
                
                # 解码输出
                response_text = self.tokenizer.decode(
                    outputs[0][len(inputs["input_ids"][0]):], 
                    skip_special_tokens=True
                ).strip()
                
                # 计算统计信息
                inference_time = time.time() - start_time
                tokens_generated = len(outputs[0]) - len(inputs["input_ids"][0])
                
                # 更新统计
                self.request_count += 1
                self.total_response_time += inference_time
                self.total_tokens_generated += tokens_generated
                
                # 简单的置信度评估
                confidence = min(0.95, max(0.6, 1.0 - (inference_time / 20.0)))
                
                logger.info(f"推理完成 - 查询: {request.query[:50]}... 耗时: {inference_time:.2f}s")
                
                return InferenceResponse(
                    query=request.query,
                    response=response_text,
                    inference_time=inference_time,
                    model_name=self.model_name,
                    tokens_generated=tokens_generated,
                    confidence=confidence,
                    timestamp=datetime.now().isoformat()
                )
                
            except Exception as e:
                logger.error(f"推理异常: {str(e)}")
                raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")
        
        @self.app.get("/api/v1/stats")
        async def get_stats():
            """获取服务统计信息"""
            avg_response_time = 0.0
            avg_tokens_per_request = 0.0
            
            if self.request_count > 0:
                avg_response_time = self.total_response_time / self.request_count
                avg_tokens_per_request = self.total_tokens_generated / self.request_count
            
            return {
                "request_count": self.request_count,
                "average_response_time": avg_response_time,
                "total_tokens_generated": self.total_tokens_generated,
                "average_tokens_per_request": avg_tokens_per_request,
                "uptime_seconds": time.time() - self.start_time,
                "model_loaded": self.model_loaded,
                "gpu_available": self.gpu_available,
                "device": str(self.device),
                "model_name": self.model_name
            }
    
    async def load_model(self):
        """加载LoRA模型"""
        try:
            logger.info("开始加载LoRA模型...")
            
            # 检查路径
            if not os.path.exists(self.base_model_path):
                raise FileNotFoundError(f"基座模型路径不存在: {self.base_model_path}")
            
            if not os.path.exists(self.lora_model_path):
                raise FileNotFoundError(f"LoRA模型路径不存在: {self.lora_model_path}")
            
            # 使用Unsloth加载模型
            logger.info("使用Unsloth框架加载模型...")
            from unsloth import FastLanguageModel
            
            # 加载基座模型
            logger.info(f"加载基座模型: {self.base_model_path}")
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.base_model_path,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )
            
            # 加载LoRA适配器
            logger.info(f"加载LoRA适配器: {self.lora_model_path}")
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, self.lora_model_path)
            
            # 启用推理模式
            logger.info("启用推理模式...")
            FastLanguageModel.for_inference(self.model)
            
            # 确保模型在正确设备上
            if self.gpu_available:
                self.model = self.model.to(self.device)
                logger.info(f"模型已移至GPU: {torch.cuda.get_device_name(0)}")
                logger.info(f"GPU显存使用: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB")
            
            self.model_loaded = True
            logger.info("✅ LoRA模型加载完成")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            self.model_loaded = False
            raise
    
    def run(self, host: str = "0.0.0.0", port: int = 8001):
        """运行推理服务"""
        logger.info(f"启动USTB LoRA推理服务 - {host}:{port}")
        logger.info(f"模型: {self.model_name}")
        logger.info(f"GPU状态: {self.gpu_available}")
        
        if self.gpu_available:
            logger.info(f"GPU设备: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="USTB LoRA推理服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8001, help="服务端口")
    parser.add_argument("--base-model", default="/root/autodl-tmp/models/Qwen2.5-7B-Instruct", help="基座模型路径")
    parser.add_argument("--lora-model", default="/root/autodl-tmp/ustb-project/models/trained", help="LoRA模型路径")
    parser.add_argument("--gpu-device", type=int, default=0, help="GPU设备ID")
    
    args = parser.parse_args()
    
    # 设置GPU设备
    if torch.cuda.is_available():
        torch.cuda.set_device(args.gpu_device)
        logger.info(f"设置GPU设备: {args.gpu_device}")
    
    # 创建服务实例
    service = USTBLoRAInferenceService(
        base_model_path=args.base_model,
        lora_model_path=args.lora_model
    )
    
    # 运行服务
    try:
        # 先加载模型
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(service.load_model())
        loop.close()
        
        # 运行服务
        service.run(host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
    except Exception as e:
        logger.error(f"服务运行异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
启动命令:
cd /root/autodl-tmp/ustb-project/services/model_inference/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python ustb_lora_inference_server.py --port 8001

验证命令:
curl http://localhost:8001/health
curl -X POST http://localhost:8001/api/v1/inference -H "Content-Type: application/json" -d '{"query":"请问如何选课？","max_tokens":256}'
"""
