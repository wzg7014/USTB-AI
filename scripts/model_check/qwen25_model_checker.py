#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen2.5基础模型全面检查工具
检查模型文件完整性、加载能力、推理性能等关键指标

作者: 梁晓阳 (项目经理)
创建时间: 2025-08-07
版本: 1.0.0
"""

import os
import sys
import json
import time
import torch
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import GPUtil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qwen25_check.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class Qwen25ModelChecker:
    """Qwen2.5模型检查器"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.check_results = {}

        # 检查项目配置
        self.max_seq_length = 2048
        self.load_in_4bit = True
        self.test_questions = [
            "北京科技大学的选课系统如何使用？",
            "如何查询期末考试成绩？",
            "学分不够怎么办？",
            "如何申请休学？"
        ]

        # AutoDL本地模型路径检查
        self.local_model_paths = [
            "/root/autodl-tmp/models/Qwen2.5-7B-Instruct",
            "/root/autodl-tmp/ustb-project/models/Qwen2.5-7B-Instruct",
            "/root/models/Qwen2.5-7B-Instruct"
        ]

        logger.info(f"初始化Qwen2.5模型检查器: {model_name}")
        logger.info(f"将检查本地路径: {self.local_model_paths}")
    
    def check_system_environment(self) -> Dict:
        """检查系统环境"""
        logger.info("🔍 检查系统环境...")
        
        env_info = {
            "python_version": sys.version,
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cpu_count": psutil.cpu_count(),
            "memory_total": f"{psutil.virtual_memory().total / (1024**3):.1f}GB",
            "memory_available": f"{psutil.virtual_memory().available / (1024**3):.1f}GB"
        }
        
        # GPU信息
        if torch.cuda.is_available():
            try:
                gpus = GPUtil.getGPUs()
                env_info["gpu_info"] = []
                for gpu in gpus:
                    env_info["gpu_info"].append({
                        "name": gpu.name,
                        "memory_total": f"{gpu.memoryTotal}MB",
                        "memory_free": f"{gpu.memoryFree}MB",
                        "memory_used": f"{gpu.memoryUsed}MB",
                        "utilization": f"{gpu.load * 100:.1f}%"
                    })
            except Exception as e:
                env_info["gpu_info"] = f"获取GPU信息失败: {e}"
        
        # 检查关键依赖包
        required_packages = [
            "transformers", "torch", "tokenizers", 
            "accelerate", "bitsandbytes", "peft"
        ]
        
        env_info["packages"] = {}
        for package in required_packages:
            try:
                module = __import__(package)
                version = getattr(module, '__version__', 'unknown')
                env_info["packages"][package] = version
            except ImportError:
                env_info["packages"][package] = "未安装"
        
        # 检查Unsloth（如果可用）
        try:
            import unsloth
            env_info["packages"]["unsloth"] = getattr(unsloth, '__version__', 'unknown')
            env_info["unsloth_available"] = True
        except ImportError:
            env_info["unsloth_available"] = False
        
        self.check_results["environment"] = env_info
        logger.info("✅ 系统环境检查完成")
        return env_info
    
    def check_model_availability(self) -> Dict:
        """检查模型可用性"""
        logger.info("🔍 检查模型可用性...")

        availability_info = {
            "model_name": self.model_name,
            "huggingface_accessible": False,
            "local_cache_exists": False,
            "local_model_exists": False,
            "model_files": [],
            "download_required": True,
            "actual_model_path": None
        }

        # 首先检查AutoDL本地模型路径
        logger.info("🔍 检查AutoDL本地模型路径...")
        for local_path in self.local_model_paths:
            if os.path.exists(local_path):
                logger.info(f"✅ 发现本地模型: {local_path}")
                availability_info["local_model_exists"] = True
                availability_info["actual_model_path"] = local_path
                availability_info["download_required"] = False

                # 检查本地模型文件
                model_files = []
                for root, dirs, files in os.walk(local_path):
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
                availability_info["model_files"] = model_files

                # 更新模型名称为本地路径
                self.model_name = local_path
                logger.info(f"🔄 更新模型路径为: {local_path}")
                break

        # 如果没有找到本地模型，检查HuggingFace Hub连接
        if not availability_info["local_model_exists"]:
            try:
                from huggingface_hub import HfApi
                api = HfApi()
                model_info = api.model_info(self.model_name)
                availability_info["huggingface_accessible"] = True
                availability_info["model_size"] = getattr(model_info, 'safetensors', {}).get('total', 'unknown')
                logger.info("✅ HuggingFace Hub连接正常")
            except Exception as e:
                availability_info["huggingface_error"] = str(e)
                logger.warning(f"⚠️ HuggingFace Hub连接失败: {e}")

            # 检查HuggingFace缓存
            cache_dirs = [
                os.path.expanduser("~/.cache/huggingface/hub"),
                "/root/.cache/huggingface/hub",
                os.path.expanduser("~/.cache/huggingface/transformers")
            ]

            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    model_cache_pattern = self.model_name.replace("/", "--")
                    for item in os.listdir(cache_dir):
                        if model_cache_pattern in item:
                            cache_path = os.path.join(cache_dir, item)
                            if os.path.isdir(cache_path):
                                availability_info["local_cache_exists"] = True
                                availability_info["cache_path"] = cache_path
                                availability_info["download_required"] = False

                                # 检查缓存文件
                                model_files = []
                                for root, dirs, files in os.walk(cache_path):
                                    for file in files:
                                        if file.endswith(('.bin', '.safetensors', '.json')):
                                            file_path = os.path.join(root, file)
                                            file_size = os.path.getsize(file_path)
                                            model_files.append({
                                                "name": file,
                                                "size": f"{file_size / (1024**2):.1f}MB",
                                                "path": file_path
                                            })
                                availability_info["model_files"] = model_files
                                break

        self.check_results["availability"] = availability_info
        logger.info("✅ 模型可用性检查完成")
        return availability_info
    
    def check_model_loading(self) -> Dict:
        """检查模型加载能力"""
        logger.info("🔍 检查模型加载能力...")
        
        loading_info = {
            "load_success": False,
            "load_time": 0,
            "memory_usage": {},
            "error_message": None
        }
        
        # 记录加载前内存使用
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            loading_info["memory_usage"]["gpu_before"] = f"{torch.cuda.memory_allocated() / (1024**2):.1f}MB"
        
        loading_info["memory_usage"]["ram_before"] = f"{psutil.virtual_memory().used / (1024**3):.1f}GB"
        
        start_time = time.time()
        
        try:
            # 尝试使用Unsloth加载（如果可用）
            if self.check_results.get("environment", {}).get("unsloth_available", False):
                logger.info("使用Unsloth加载模型...")
                from unsloth import FastLanguageModel
                
                self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                    self.model_name,
                    max_seq_length=self.max_seq_length,
                    dtype=None,
                    load_in_4bit=self.load_in_4bit,
                )
                loading_info["loader"] = "unsloth"
            else:
                # 使用标准transformers加载
                logger.info("使用transformers加载模型...")
                from transformers import AutoModelForCausalLM, AutoTokenizer
                
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None,
                    load_in_4bit=self.load_in_4bit if torch.cuda.is_available() else False
                )
                loading_info["loader"] = "transformers"
            
            loading_info["load_success"] = True
            loading_info["load_time"] = time.time() - start_time
            
            # 记录加载后内存使用
            if torch.cuda.is_available():
                loading_info["memory_usage"]["gpu_after"] = f"{torch.cuda.memory_allocated() / (1024**2):.1f}MB"
            loading_info["memory_usage"]["ram_after"] = f"{psutil.virtual_memory().used / (1024**3):.1f}GB"
            
            logger.info(f"✅ 模型加载成功，耗时: {loading_info['load_time']:.2f}秒")
            
        except Exception as e:
            loading_info["error_message"] = str(e)
            loading_info["traceback"] = traceback.format_exc()
            logger.error(f"❌ 模型加载失败: {e}")
        
        self.check_results["loading"] = loading_info
        return loading_info
    
    def check_inference_capability(self) -> Dict:
        """检查推理能力"""
        logger.info("🔍 检查推理能力...")
        
        inference_info = {
            "inference_success": False,
            "test_results": [],
            "average_time": 0,
            "error_message": None
        }
        
        if not self.model or not self.tokenizer:
            inference_info["error_message"] = "模型未加载，无法进行推理测试"
            self.check_results["inference"] = inference_info
            return inference_info
        
        try:
            # 设置推理模式
            if hasattr(self.model, 'eval'):
                self.model.eval()
            
            # 如果使用Unsloth，启用推理模式
            if self.check_results.get("loading", {}).get("loader") == "unsloth":
                from unsloth import FastLanguageModel
                FastLanguageModel.for_inference(self.model)
            
            total_time = 0
            successful_tests = 0
            
            for i, question in enumerate(self.test_questions):
                logger.info(f"测试问题 {i+1}: {question}")
                
                test_result = {
                    "question": question,
                    "success": False,
                    "response": "",
                    "inference_time": 0,
                    "error": None
                }
                
                try:
                    start_time = time.time()
                    
                    # 构建输入
                    prompt = f"问题：{question}\n回答："
                    inputs = self.tokenizer(prompt, return_tensors="pt")
                    
                    if torch.cuda.is_available():
                        inputs = {k: v.cuda() for k, v in inputs.items()}
                    
                    # 生成回答
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=256,
                            temperature=0.7,
                            do_sample=True,
                            pad_token_id=self.tokenizer.eos_token_id
                        )
                    
                    # 解码回答
                    response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    response = response.replace(prompt, "").strip()
                    
                    test_result["success"] = True
                    test_result["response"] = response[:200] + "..." if len(response) > 200 else response
                    test_result["inference_time"] = time.time() - start_time
                    
                    total_time += test_result["inference_time"]
                    successful_tests += 1
                    
                    logger.info(f"✅ 推理成功，耗时: {test_result['inference_time']:.2f}秒")
                    
                except Exception as e:
                    test_result["error"] = str(e)
                    logger.error(f"❌ 推理失败: {e}")
                
                inference_info["test_results"].append(test_result)
            
            if successful_tests > 0:
                inference_info["inference_success"] = True
                inference_info["average_time"] = total_time / successful_tests
                inference_info["success_rate"] = f"{successful_tests}/{len(self.test_questions)}"
                logger.info(f"✅ 推理测试完成，成功率: {inference_info['success_rate']}")
            else:
                inference_info["error_message"] = "所有推理测试都失败了"
                logger.error("❌ 所有推理测试都失败了")
        
        except Exception as e:
            inference_info["error_message"] = str(e)
            logger.error(f"❌ 推理测试异常: {e}")
        
        self.check_results["inference"] = inference_info
        return inference_info

    def check_model_compatibility(self) -> Dict:
        """检查模型兼容性"""
        logger.info("🔍 检查模型兼容性...")

        compatibility_info = {
            "tokenizer_compatible": False,
            "config_valid": False,
            "architecture_supported": False,
            "quantization_supported": False,
            "issues": []
        }

        try:
            if self.tokenizer:
                # 检查tokenizer
                test_text = "这是一个测试文本"
                tokens = self.tokenizer.encode(test_text)
                decoded = self.tokenizer.decode(tokens)

                if decoded.strip():
                    compatibility_info["tokenizer_compatible"] = True
                    compatibility_info["vocab_size"] = len(self.tokenizer)
                    compatibility_info["special_tokens"] = {
                        "pad_token": self.tokenizer.pad_token,
                        "eos_token": self.tokenizer.eos_token,
                        "bos_token": self.tokenizer.bos_token,
                        "unk_token": self.tokenizer.unk_token
                    }
                else:
                    compatibility_info["issues"].append("Tokenizer编码解码异常")

            if self.model:
                # 检查模型配置
                config = self.model.config
                compatibility_info["config_valid"] = True
                compatibility_info["model_config"] = {
                    "model_type": getattr(config, 'model_type', 'unknown'),
                    "hidden_size": getattr(config, 'hidden_size', 'unknown'),
                    "num_attention_heads": getattr(config, 'num_attention_heads', 'unknown'),
                    "num_hidden_layers": getattr(config, 'num_hidden_layers', 'unknown'),
                    "vocab_size": getattr(config, 'vocab_size', 'unknown')
                }

                # 检查架构支持
                if hasattr(config, 'model_type') and 'qwen' in config.model_type.lower():
                    compatibility_info["architecture_supported"] = True
                else:
                    compatibility_info["issues"].append("模型架构可能不是Qwen2.5")

                # 检查量化支持
                if hasattr(self.model, 'is_quantized') or any('4bit' in str(param.dtype) for param in self.model.parameters()):
                    compatibility_info["quantization_supported"] = True

        except Exception as e:
            compatibility_info["issues"].append(f"兼容性检查异常: {e}")
            logger.error(f"❌ 兼容性检查失败: {e}")

        self.check_results["compatibility"] = compatibility_info
        logger.info("✅ 模型兼容性检查完成")
        return compatibility_info

    def generate_report(self) -> Dict:
        """生成检查报告"""
        logger.info("📊 生成检查报告...")

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": self.model_name,
            "overall_status": "unknown",
            "summary": {},
            "recommendations": [],
            "detailed_results": self.check_results
        }

        # 计算总体状态
        checks = [
            self.check_results.get("environment", {}).get("cuda_available", False),
            self.check_results.get("availability", {}).get("huggingface_accessible", False) or
            self.check_results.get("availability", {}).get("local_cache_exists", False),
            self.check_results.get("loading", {}).get("load_success", False),
            self.check_results.get("inference", {}).get("inference_success", False),
            self.check_results.get("compatibility", {}).get("tokenizer_compatible", False)
        ]

        success_count = sum(checks)
        total_checks = len(checks)

        if success_count == total_checks:
            report["overall_status"] = "excellent"
            report["status_message"] = "✅ 所有检查项目都通过，模型状态优秀"
        elif success_count >= total_checks * 0.8:
            report["overall_status"] = "good"
            report["status_message"] = "✅ 大部分检查项目通过，模型状态良好"
        elif success_count >= total_checks * 0.6:
            report["overall_status"] = "warning"
            report["status_message"] = "⚠️ 部分检查项目存在问题，需要注意"
        else:
            report["overall_status"] = "critical"
            report["status_message"] = "❌ 多个关键检查项目失败，需要立即处理"

        # 生成摘要
        report["summary"] = {
            "environment_ok": self.check_results.get("environment", {}).get("cuda_available", False),
            "model_available": self.check_results.get("availability", {}).get("local_cache_exists", False) or
                             self.check_results.get("availability", {}).get("huggingface_accessible", False),
            "loading_ok": self.check_results.get("loading", {}).get("load_success", False),
            "inference_ok": self.check_results.get("inference", {}).get("inference_success", False),
            "compatibility_ok": self.check_results.get("compatibility", {}).get("tokenizer_compatible", False),
            "average_inference_time": self.check_results.get("inference", {}).get("average_time", 0)
        }

        # 生成建议
        if not report["summary"]["environment_ok"]:
            report["recommendations"].append("🔧 建议安装CUDA支持以获得更好的性能")

        if not report["summary"]["model_available"]:
            report["recommendations"].append("📥 需要下载Qwen2.5-7B-Instruct模型")

        if not report["summary"]["loading_ok"]:
            report["recommendations"].append("⚠️ 模型加载失败，检查内存和依赖包")

        if not report["summary"]["inference_ok"]:
            report["recommendations"].append("🔍 推理测试失败，检查模型完整性")

        if report["summary"]["average_inference_time"] > 5:
            report["recommendations"].append("⚡ 推理速度较慢，考虑使用GPU加速或模型量化")

        if not self.check_results.get("environment", {}).get("unsloth_available", False):
            report["recommendations"].append("🚀 建议安装Unsloth以获得2倍训练加速")

        return report

    def save_report(self, report: Dict, filename: str = None):
        """保存检查报告"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"qwen25_check_report_{timestamp}.json"

        # 确保reports目录存在
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        report_path = reports_dir / filename

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 检查报告已保存: {report_path}")
        return report_path

    def print_summary(self, report: Dict):
        """打印检查摘要"""
        print("\n" + "="*60)
        print("🔍 Qwen2.5基础模型检查报告")
        print("="*60)
        print(f"📅 检查时间: {report['timestamp']}")
        print(f"🤖 模型名称: {report['model_name']}")
        print(f"📊 总体状态: {report['status_message']}")
        print("\n📋 检查项目摘要:")

        summary = report['summary']
        status_icon = lambda x: "✅" if x else "❌"

        print(f"  {status_icon(summary['environment_ok'])} 系统环境")
        print(f"  {status_icon(summary['model_available'])} 模型可用性")
        print(f"  {status_icon(summary['loading_ok'])} 模型加载")
        print(f"  {status_icon(summary['inference_ok'])} 推理能力")
        print(f"  {status_icon(summary['compatibility_ok'])} 兼容性")

        if summary['average_inference_time'] > 0:
            print(f"  ⏱️ 平均推理时间: {summary['average_inference_time']:.2f}秒")

        if report['recommendations']:
            print("\n💡 改进建议:")
            for rec in report['recommendations']:
                print(f"  • {rec}")

        print("\n" + "="*60)

    def run_full_check(self) -> Dict:
        """运行完整检查"""
        logger.info("🚀 开始Qwen2.5基础模型全面检查...")

        try:
            # 执行各项检查
            self.check_system_environment()
            self.check_model_availability()
            self.check_model_loading()

            if self.check_results.get("loading", {}).get("load_success", False):
                self.check_inference_capability()
                self.check_model_compatibility()
            else:
                logger.warning("⚠️ 模型加载失败，跳过推理和兼容性测试")

            # 生成报告
            report = self.generate_report()

            # 保存报告
            self.save_report(report)

            # 打印摘要
            self.print_summary(report)

            logger.info("✅ Qwen2.5基础模型检查完成")
            return report

        except Exception as e:
            logger.error(f"❌ 检查过程异常: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "traceback": traceback.format_exc()}

        finally:
            # 清理资源
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Qwen2.5基础模型检查工具")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct", help="模型名称")
    parser.add_argument("--output", help="报告输出文件名")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建检查器并运行
    checker = Qwen25ModelChecker(args.model)
    report = checker.run_full_check()

    if args.output:
        checker.save_report(report, args.output)

    return report


if __name__ == "__main__":
    main()

    def check_model_compatibility(self) -> Dict:
        """检查模型兼容性"""
        logger.info("🔍 检查模型兼容性...")

        compatibility_info = {
            "tokenizer_compatible": False,
            "config_valid": False,
            "architecture_supported": False,
            "quantization_supported": False,
            "issues": []
        }

        try:
            if self.tokenizer:
                # 检查tokenizer
                test_text = "这是一个测试文本"
                tokens = self.tokenizer.encode(test_text)
                decoded = self.tokenizer.decode(tokens)

                if decoded.strip():
                    compatibility_info["tokenizer_compatible"] = True
                    compatibility_info["vocab_size"] = len(self.tokenizer)
                    compatibility_info["special_tokens"] = {
                        "pad_token": self.tokenizer.pad_token,
                        "eos_token": self.tokenizer.eos_token,
                        "bos_token": self.tokenizer.bos_token,
                        "unk_token": self.tokenizer.unk_token
                    }
                else:
                    compatibility_info["issues"].append("Tokenizer编码解码异常")

            if self.model:
                # 检查模型配置
                config = self.model.config
                compatibility_info["config_valid"] = True
                compatibility_info["model_config"] = {
                    "model_type": getattr(config, 'model_type', 'unknown'),
                    "hidden_size": getattr(config, 'hidden_size', 'unknown'),
                    "num_attention_heads": getattr(config, 'num_attention_heads', 'unknown'),
                    "num_hidden_layers": getattr(config, 'num_hidden_layers', 'unknown'),
                    "vocab_size": getattr(config, 'vocab_size', 'unknown')
                }

                # 检查架构支持
                if hasattr(config, 'model_type') and 'qwen' in config.model_type.lower():
                    compatibility_info["architecture_supported"] = True
                else:
                    compatibility_info["issues"].append("模型架构可能不是Qwen2.5")

                # 检查量化支持
                if hasattr(self.model, 'is_quantized') or any('4bit' in str(param.dtype) for param in self.model.parameters()):
                    compatibility_info["quantization_supported"] = True

        except Exception as e:
            compatibility_info["issues"].append(f"兼容性检查异常: {e}")
            logger.error(f"❌ 兼容性检查失败: {e}")

        self.check_results["compatibility"] = compatibility_info
        logger.info("✅ 模型兼容性检查完成")
        return compatibility_info

    def generate_report(self) -> Dict:
        """生成检查报告"""
        logger.info("📊 生成检查报告...")

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": self.model_name,
            "overall_status": "unknown",
            "summary": {},
            "recommendations": [],
            "detailed_results": self.check_results
        }

        # 计算总体状态
        checks = [
            self.check_results.get("environment", {}).get("cuda_available", False),
            self.check_results.get("availability", {}).get("huggingface_accessible", False) or
            self.check_results.get("availability", {}).get("local_cache_exists", False),
            self.check_results.get("loading", {}).get("load_success", False),
            self.check_results.get("inference", {}).get("inference_success", False),
            self.check_results.get("compatibility", {}).get("tokenizer_compatible", False)
        ]

        success_count = sum(checks)
        total_checks = len(checks)

        if success_count == total_checks:
            report["overall_status"] = "excellent"
            report["status_message"] = "✅ 所有检查项目都通过，模型状态优秀"
        elif success_count >= total_checks * 0.8:
            report["overall_status"] = "good"
            report["status_message"] = "✅ 大部分检查项目通过，模型状态良好"
        elif success_count >= total_checks * 0.6:
            report["overall_status"] = "warning"
            report["status_message"] = "⚠️ 部分检查项目存在问题，需要注意"
        else:
            report["overall_status"] = "critical"
            report["status_message"] = "❌ 多个关键检查项目失败，需要立即处理"

        # 生成摘要
        report["summary"] = {
            "environment_ok": self.check_results.get("environment", {}).get("cuda_available", False),
            "model_available": self.check_results.get("availability", {}).get("local_cache_exists", False) or
                             self.check_results.get("availability", {}).get("huggingface_accessible", False),
            "loading_ok": self.check_results.get("loading", {}).get("load_success", False),
            "inference_ok": self.check_results.get("inference", {}).get("inference_success", False),
            "compatibility_ok": self.check_results.get("compatibility", {}).get("tokenizer_compatible", False),
            "average_inference_time": self.check_results.get("inference", {}).get("average_time", 0)
        }

        # 生成建议
        if not report["summary"]["environment_ok"]:
            report["recommendations"].append("🔧 建议安装CUDA支持以获得更好的性能")

        if not report["summary"]["model_available"]:
            report["recommendations"].append("📥 需要下载Qwen2.5-7B-Instruct模型")

        if not report["summary"]["loading_ok"]:
            report["recommendations"].append("⚠️ 模型加载失败，检查内存和依赖包")

        if not report["summary"]["inference_ok"]:
            report["recommendations"].append("🔍 推理测试失败，检查模型完整性")

        if report["summary"]["average_inference_time"] > 5:
            report["recommendations"].append("⚡ 推理速度较慢，考虑使用GPU加速或模型量化")

        if not self.check_results.get("environment", {}).get("unsloth_available", False):
            report["recommendations"].append("🚀 建议安装Unsloth以获得2倍训练加速")

        return report

    def save_report(self, report: Dict, filename: str = None):
        """保存检查报告"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"qwen25_check_report_{timestamp}.json"

        # 确保reports目录存在
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        report_path = reports_dir / filename

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 检查报告已保存: {report_path}")
        return report_path

    def print_summary(self, report: Dict):
        """打印检查摘要"""
        print("\n" + "="*60)
        print("🔍 Qwen2.5基础模型检查报告")
        print("="*60)
        print(f"📅 检查时间: {report['timestamp']}")
        print(f"🤖 模型名称: {report['model_name']}")
        print(f"📊 总体状态: {report['status_message']}")
        print("\n📋 检查项目摘要:")

        summary = report['summary']
        status_icon = lambda x: "✅" if x else "❌"

        print(f"  {status_icon(summary['environment_ok'])} 系统环境")
        print(f"  {status_icon(summary['model_available'])} 模型可用性")
        print(f"  {status_icon(summary['loading_ok'])} 模型加载")
        print(f"  {status_icon(summary['inference_ok'])} 推理能力")
        print(f"  {status_icon(summary['compatibility_ok'])} 兼容性")

        if summary['average_inference_time'] > 0:
            print(f"  ⏱️ 平均推理时间: {summary['average_inference_time']:.2f}秒")

        if report['recommendations']:
            print("\n💡 改进建议:")
            for rec in report['recommendations']:
                print(f"  • {rec}")

        print("\n" + "="*60)

    def run_full_check(self) -> Dict:
        """运行完整检查"""
        logger.info("🚀 开始Qwen2.5基础模型全面检查...")

        try:
            # 执行各项检查
            self.check_system_environment()
            self.check_model_availability()
            self.check_model_loading()

            if self.check_results.get("loading", {}).get("load_success", False):
                self.check_inference_capability()
                self.check_model_compatibility()
            else:
                logger.warning("⚠️ 模型加载失败，跳过推理和兼容性测试")

            # 生成报告
            report = self.generate_report()

            # 保存报告
            report_path = self.save_report(report)

            # 打印摘要
            self.print_summary(report)

            logger.info("✅ Qwen2.5基础模型检查完成")
            return report

        except Exception as e:
            logger.error(f"❌ 检查过程异常: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "traceback": traceback.format_exc()}

        finally:
            # 清理资源
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Qwen2.5基础模型检查工具")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct", help="模型名称")
    parser.add_argument("--output", help="报告输出文件名")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建检查器并运行
    checker = Qwen25ModelChecker(args.model)
    report = checker.run_full_check()

    if args.output:
        checker.save_report(report, args.output)

    return report


if __name__ == "__main__":
    main()
