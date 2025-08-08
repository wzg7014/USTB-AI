#!/usr/bin/env python3
"""
USTB训练模型检查器 - 专门检查训练好的LoRA模型
检查训练后的模型状态、推理能力和性能指标

创建时间: 2025-08-07
作者: AI助手
用途: 验证训练模型的完整性和推理能力
"""

import os
import sys
import json
import time
import logging
import torch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/root/autodl-tmp/ustb-project/logs/trained_model_check.log')
    ]
)
logger = logging.getLogger(__name__)

class TrainedModelChecker:
    """训练模型检查器"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.check_results = {}
        
        # 训练模型路径配置
        self.trained_model_paths = [
            "/root/autodl-tmp/ustb-project/models/trained",
            "/root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned",
            "/root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned_merged",
            "/root/autodl-tmp/ustb-project/models/qwen25-ustb-tuned",
            "/root/autodl-tmp/ustb-project/models/qwen25-ustb-tuned_merged"
        ]
        
        # 基础模型路径
        self.base_model_path = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct"
        
        # 测试问题
        self.test_questions = [
            "北京科技大学的选课系统如何使用？",
            "如何查询期末考试成绩？",
            "学分不够怎么办？",
            "如何申请休学？",
            "教务系统密码忘记了怎么办？"
        ]
        
        logger.info("训练模型检查器初始化完成")
        logger.info(f"将检查路径: {self.trained_model_paths}")
    
    def check_environment(self) -> Dict:
        """检查环境配置"""
        logger.info("🔍 检查环境配置...")
        
        env_info = {
            "python_version": sys.version,
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "packages": {}
        }
        
        if torch.cuda.is_available():
            env_info["gpu_name"] = torch.cuda.get_device_name(0)
            env_info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB"
        
        # 检查关键包
        packages_to_check = ['transformers', 'torch', 'unsloth', 'peft']
        for package in packages_to_check:
            try:
                module = __import__(package)
                env_info["packages"][package] = getattr(module, '__version__', 'unknown')
            except ImportError:
                env_info["packages"][package] = "not_installed"
        
        self.check_results["environment"] = env_info
        logger.info("✅ 环境检查完成")
        return env_info
    
    def find_trained_model(self) -> Dict:
        """查找训练好的模型"""
        logger.info("🔍 查找训练好的模型...")
        
        model_info = {
            "found_models": [],
            "selected_model": None,
            "model_type": None,
            "model_files": []
        }
        
        for model_path in self.trained_model_paths:
            if os.path.exists(model_path):
                logger.info(f"✅ 发现模型路径: {model_path}")
                
                # 检查模型文件
                model_files = []
                for root, dirs, files in os.walk(model_path):
                    for file in files:
                        if file.endswith(('.bin', '.safetensors', '.json', '.txt')):
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                model_files.append({
                                    "name": file,
                                    "size": f"{file_size / (1024**2):.1f}MB",
                                    "path": file_path
                                })
                            except OSError:
                                model_files.append({
                                    "name": file,
                                    "size": "unknown",
                                    "path": file_path
                                })
                
                # 判断模型类型
                model_type = "unknown"
                if any("adapter" in f["name"] for f in model_files):
                    model_type = "lora_adapter"
                elif any("pytorch_model.bin" in f["name"] or "model.safetensors" in f["name"] for f in model_files):
                    model_type = "merged_model"
                
                model_info["found_models"].append({
                    "path": model_path,
                    "type": model_type,
                    "files": model_files,
                    "file_count": len(model_files)
                })
        
        # 选择最佳模型（优先选择合并模型）
        if model_info["found_models"]:
            merged_models = [m for m in model_info["found_models"] if m["type"] == "merged_model"]
            if merged_models:
                model_info["selected_model"] = merged_models[0]["path"]
                model_info["model_type"] = "merged_model"
            else:
                model_info["selected_model"] = model_info["found_models"][0]["path"]
                model_info["model_type"] = model_info["found_models"][0]["type"]
            
            logger.info(f"✅ 选择模型: {model_info['selected_model']} (类型: {model_info['model_type']})")
        else:
            logger.warning("⚠️ 未找到训练好的模型")
        
        self.check_results["model_discovery"] = model_info
        return model_info
    
    def load_model(self, model_path: str, model_type: str) -> Dict:
        """加载训练模型"""
        logger.info(f"🔄 加载训练模型: {model_path}")
        
        loading_info = {
            "model_path": model_path,
            "model_type": model_type,
            "loading_success": False,
            "loading_time": 0,
            "error_message": None,
            "loader": "unknown"
        }
        
        start_time = time.time()
        
        try:
            if model_type == "lora_adapter":
                # 加载LoRA适配器
                logger.info("使用LoRA适配器加载方式...")
                try:
                    from unsloth import FastLanguageModel
                    
                    # 先加载基础模型
                    self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                        self.base_model_path,
                        max_seq_length=2048,
                        dtype=None,
                        load_in_4bit=True,
                    )
                    
                    # 加载LoRA适配器
                    from peft import PeftModel
                    self.model = PeftModel.from_pretrained(self.model, model_path)
                    loading_info["loader"] = "unsloth_lora"
                    
                except Exception as e:
                    logger.warning(f"Unsloth LoRA加载失败: {e}")
                    # 尝试标准transformers加载
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    from peft import PeftModel
                    
                    base_model = AutoModelForCausalLM.from_pretrained(
                        self.base_model_path,
                        torch_dtype=torch.float16,
                        device_map="auto"
                    )
                    self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_path)
                    self.model = PeftModel.from_pretrained(base_model, model_path)
                    loading_info["loader"] = "transformers_lora"
                    
            else:
                # 加载合并模型
                logger.info("使用合并模型加载方式...")
                try:
                    from unsloth import FastLanguageModel
                    
                    self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                        model_path,
                        max_seq_length=2048,
                        dtype=None,
                        load_in_4bit=True,
                    )
                    loading_info["loader"] = "unsloth_merged"
                    
                except Exception as e:
                    logger.warning(f"Unsloth合并模型加载失败: {e}")
                    # 尝试标准transformers加载
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float16,
                        device_map="auto"
                    )
                    self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                    loading_info["loader"] = "transformers_merged"
            
            loading_info["loading_success"] = True
            loading_time = time.time() - start_time
            loading_info["loading_time"] = loading_time
            
            logger.info(f"✅ 模型加载成功，耗时: {loading_time:.2f}秒")
            
        except Exception as e:
            loading_info["error_message"] = str(e)
            logger.error(f"❌ 模型加载失败: {e}")
        
        self.check_results["loading"] = loading_info
        return loading_info
    
    def test_inference(self) -> Dict:
        """测试模型推理能力"""
        logger.info("🧪 测试模型推理能力...")
        
        if not self.model or not self.tokenizer:
            logger.error("❌ 模型未加载，无法进行推理测试")
            return {"error": "模型未加载"}
        
        # 启用推理模式
        if self.check_results.get("loading", {}).get("loader", "").startswith("unsloth"):
            try:
                from unsloth import FastLanguageModel
                FastLanguageModel.for_inference(self.model)
                logger.info("✅ 启用Unsloth推理模式")
            except Exception as e:
                logger.warning(f"启用Unsloth推理模式失败: {e}")
        
        inference_results = {
            "test_count": len(self.test_questions),
            "success_count": 0,
            "failed_count": 0,
            "total_time": 0,
            "average_time": 0,
            "results": []
        }
        
        for i, question in enumerate(self.test_questions, 1):
            logger.info(f"测试问题 {i}: {question}")
            
            start_time = time.time()
            try:
                # 构建输入
                messages = [
                    {"role": "system", "content": "你是北京科技大学的AI教务助手，请根据学校的教务规定和流程回答学生的问题。"},
                    {"role": "user", "content": question}
                ]
                
                # 应用聊天模板
                input_text = self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
                
                # 编码输入
                inputs = self.tokenizer(input_text, return_tensors="pt").to(self.model.device)
                
                # 生成回答
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=256,
                        temperature=0.1,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # 解码输出
                response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
                
                inference_time = time.time() - start_time
                inference_results["total_time"] += inference_time
                inference_results["success_count"] += 1
                
                result = {
                    "question": question,
                    "response": response[:200] + "..." if len(response) > 200 else response,
                    "inference_time": inference_time,
                    "status": "success"
                }
                
                logger.info(f"✅ 推理成功，耗时: {inference_time:.2f}秒")
                
            except Exception as e:
                inference_results["failed_count"] += 1
                result = {
                    "question": question,
                    "response": None,
                    "inference_time": 0,
                    "status": "failed",
                    "error": str(e)
                }
                logger.error(f"❌ 推理失败: {e}")
            
            inference_results["results"].append(result)
        
        # 计算平均时间
        if inference_results["success_count"] > 0:
            inference_results["average_time"] = inference_results["total_time"] / inference_results["success_count"]
        
        logger.info(f"✅ 推理测试完成，成功率: {inference_results['success_count']}/{inference_results['test_count']}")
        
        self.check_results["inference"] = inference_results
        return inference_results
    
    def generate_report(self) -> Dict:
        """生成检查报告"""
        logger.info("📊 生成检查报告...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "checker_version": "1.0.0",
            "report_type": "trained_model_check",
            "summary": {
                "environment_ok": bool(self.check_results.get("environment", {}).get("cuda_available", False)),
                "model_found": bool(self.check_results.get("model_discovery", {}).get("selected_model")),
                "model_loaded": bool(self.check_results.get("loading", {}).get("loading_success", False)),
                "inference_working": self.check_results.get("inference", {}).get("success_count", 0) > 0,
                "overall_status": "unknown"
            },
            "details": self.check_results
        }
        
        # 计算总体状态
        if (report["summary"]["environment_ok"] and 
            report["summary"]["model_found"] and 
            report["summary"]["model_loaded"] and 
            report["summary"]["inference_working"]):
            report["summary"]["overall_status"] = "excellent"
        elif report["summary"]["model_found"] and report["summary"]["model_loaded"]:
            report["summary"]["overall_status"] = "good"
        elif report["summary"]["model_found"]:
            report["summary"]["overall_status"] = "partial"
        else:
            report["summary"]["overall_status"] = "failed"
        
        return report
    
    def save_report(self, report: Dict, filename: str = None):
        """保存检查报告"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"trained_model_check_{timestamp}.json"
        
        report_path = f"/root/autodl-tmp/ustb-project/reports/{filename}"
        
        try:
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 报告已保存: {report_path}")
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
    
    def run_full_check(self):
        """运行完整检查"""
        logger.info("🚀 开始训练模型完整检查...")
        
        # 1. 环境检查
        self.check_environment()
        
        # 2. 查找模型
        model_info = self.find_trained_model()
        
        if not model_info["selected_model"]:
            logger.error("❌ 未找到训练模型，检查终止")
            report = self.generate_report()
            self.save_report(report)
            return report
        
        # 3. 加载模型
        loading_result = self.load_model(model_info["selected_model"], model_info["model_type"])
        
        if not loading_result["loading_success"]:
            logger.error("❌ 模型加载失败，检查终止")
            report = self.generate_report()
            self.save_report(report)
            return report
        
        # 4. 推理测试
        self.test_inference()
        
        # 5. 生成报告
        report = self.generate_report()
        self.save_report(report)
        
        logger.info("✅ 训练模型检查完成")
        return report

def main():
    """主函数"""
    print("🧪 USTB训练模型检查器")
    print("=" * 60)
    
    checker = TrainedModelChecker()
    report = checker.run_full_check()
    
    # 打印摘要
    print("\n📊 检查摘要:")
    print(f"环境状态: {'✅' if report['summary']['environment_ok'] else '❌'}")
    print(f"模型发现: {'✅' if report['summary']['model_found'] else '❌'}")
    print(f"模型加载: {'✅' if report['summary']['model_loaded'] else '❌'}")
    print(f"推理测试: {'✅' if report['summary']['inference_working'] else '❌'}")
    print(f"总体状态: {report['summary']['overall_status']}")
    
    if report['summary']['inference_working']:
        inference_info = report['details'].get('inference', {})
        print(f"推理成功率: {inference_info.get('success_count', 0)}/{inference_info.get('test_count', 0)}")
        print(f"平均推理时间: {inference_info.get('average_time', 0):.2f}秒")

if __name__ == "__main__":
    main()
