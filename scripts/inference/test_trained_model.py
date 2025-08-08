#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
USTB教务助手 - 训练后模型推理测试脚本
测试微调后的DeepSeek-R1模型性能

作者: 梁晓阳 (项目经理)
日期: 2025-08-06
版本: v1.0
"""

import os
import torch
from unsloth import FastLanguageModel

class USTBAssistantInference:
    """USTB教务助手推理类"""
    
    def __init__(self, model_path):
        """初始化推理模型"""
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 设置HF镜像
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        self.load_model()
    
    def load_model(self):
        """加载训练后的模型"""
        print(f"🤖 加载训练后的模型: {self.model_path}")
        
        try:
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                self.model_path,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )
            
            # 切换到推理模式
            FastLanguageModel.for_inference(self.model)
            
            print("✅ 模型加载成功")
            print(f"🔧 设备: {self.device}")
            
        except Exception as e:
            print(f"❌ 模型加载失败: {str(e)}")
            raise
    
    def generate_answer(self, question, max_new_tokens=512, temperature=0.7, top_p=0.9):
        """生成问题回答"""
        
        # 构建提示模板
        prompt = f"""你是USTB（北京科技大学）的智能教务助手，专门为师生提供准确、及时的教务信息服务。
请根据以下问题提供专业、详细的回答。

问题：{question}
回答："""
        
        # 编码输入
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        # 生成回答
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # 解码回答
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = response[len(prompt):].strip()
        
        return answer
    
    def interactive_test(self):
        """交互式测试"""
        print("\n🎯 进入交互式测试模式")
        print("💡 输入问题测试模型效果，输入 'quit' 退出")
        print("-" * 50)
        
        while True:
            question = input("\n❓ 请输入问题: ").strip()
            
            if question.lower() in ['quit', 'exit', '退出']:
                print("👋 退出测试模式")
                break
            
            if not question:
                print("⚠️ 请输入有效问题")
                continue
            
            print("🤔 思考中...")
            try:
                answer = self.generate_answer(question)
                print(f"\n🤖 USTB教务助手回答:")
                print(f"💬 {answer}")
                
            except Exception as e:
                print(f"❌ 生成回答时出错: {str(e)}")
    
    def batch_test(self):
        """批量测试预设问题"""
        print("\n📋 批量测试预设问题")
        print("-" * 50)
        
        # 预设测试问题
        test_questions = [
            "如何查询课程表？",
            "选课系统什么时候开放？",
            "如何申请缓考？",
            "学分不够怎么办？",
            "如何查看考试安排？",
            "转专业需要什么条件？",
            "如何办理休学手续？",
            "毕业论文答辩时间是什么时候？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 测试问题 {i}: {question}")
            
            try:
                answer = self.generate_answer(question, max_new_tokens=256)
                print(f"🤖 回答: {answer}")
                
            except Exception as e:
                print(f"❌ 回答生成失败: {str(e)}")
            
            print("-" * 30)

def main():
    """主函数"""
    print("🧪 USTB教务助手 - 训练后模型测试")
    print("=" * 60)
    
    # 模型路径配置
    lora_model_path = "/root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned"
    merged_model_path = "/root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned_merged"
    
    # 选择模型路径
    if os.path.exists(merged_model_path):
        model_path = merged_model_path
        print(f"📁 使用合并模型: {model_path}")
    elif os.path.exists(lora_model_path):
        model_path = lora_model_path
        print(f"📁 使用LoRA模型: {model_path}")
    else:
        print("❌ 未找到训练后的模型文件")
        print("💡 请确保训练已完成并且模型已保存")
        return
    
    try:
        # 初始化推理器
        assistant = USTBAssistantInference(model_path)
        
        # 选择测试模式
        print("\n🎯 选择测试模式:")
        print("1. 批量测试预设问题")
        print("2. 交互式测试")
        print("3. 两种模式都执行")
        
        choice = input("\n请选择 (1/2/3): ").strip()
        
        if choice == "1":
            assistant.batch_test()
        elif choice == "2":
            assistant.interactive_test()
        elif choice == "3":
            assistant.batch_test()
            assistant.interactive_test()
        else:
            print("⚠️ 无效选择，执行批量测试")
            assistant.batch_test()
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")

if __name__ == "__main__":
    main()
