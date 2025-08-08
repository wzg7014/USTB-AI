#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
USTB教务助手 - 训练执行脚本
实际执行DeepSeek-R1微调训练的脚本

作者: 梁晓阳 (项目经理)  
日期: 2025-08-06
版本: v1.0
"""

import os
import sys
import time
import torch
from datetime import datetime
from trl import SFTTrainer

# 导入训练配置
sys.path.append('/root/autodl-tmp/ustb-project/scripts/training')
from deepseek_unsloth_training import main as prepare_training

def execute_training():
    """执行实际的模型训练"""
    print("🚀 开始执行USTB教务助手模型训练")
    print("=" * 60)
    
    # 记录训练开始时间
    start_time = datetime.now()
    print(f"⏰ 训练开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 准备训练组件
        print("\n📋 准备训练组件...")
        components = prepare_training()
        
        model = components["model"]
        tokenizer = components["tokenizer"]
        dataset = components["dataset"]
        training_args = components["training_args"]
        
        # 2. 创建SFT训练器
        print("\n🎯 创建SFT训练器...")
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=2048,
            args=training_args,
            packing=False,  # 不使用序列打包
        )
        
        print("✅ SFT训练器创建成功")
        
        # 3. 显示训练前状态
        print("\n📊 训练前状态检查:")
        print(f"🔢 训练样本数量: {len(dataset)}")
        print(f"🎯 有效批次大小: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
        print(f"📚 训练轮次: {training_args.num_train_epochs}")
        print(f"💾 模型保存路径: {training_args.output_dir}")
        
        # 4. 开始训练
        print("\n🎓 开始模型训练...")
        print("⚠️ 训练过程中请勿中断，预计需要1-2小时")
        
        # 执行训练
        trainer.train()
        
        # 5. 保存训练后的模型
        print("\n💾 保存训练后的模型...")
        
        # 保存LoRA适配器
        model.save_pretrained(training_args.output_dir)
        tokenizer.save_pretrained(training_args.output_dir)
        
        # 保存合并后的模型（可选）
        merged_model_path = f"{training_args.output_dir}_merged"
        print(f"🔄 保存合并模型到: {merged_model_path}")
        
        model.save_pretrained_merged(
            merged_model_path, 
            tokenizer, 
            save_method="merged_16bit"
        )
        
        print("✅ 模型保存完成")
        
        # 6. 训练完成统计
        end_time = datetime.now()
        training_duration = end_time - start_time
        
        print("\n🎉 训练完成!")
        print("=" * 60)
        print(f"⏰ 训练结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总训练时长: {training_duration}")
        print(f"💾 LoRA适配器保存路径: {training_args.output_dir}")
        print(f"🔄 合并模型保存路径: {merged_model_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 训练过程中出现错误: {str(e)}")
        print("💡 请检查错误信息并重新尝试")
        return False

def test_trained_model(model_path):
    """测试训练后的模型"""
    print(f"\n🧪 测试训练后的模型: {model_path}")
    
    try:
        from unsloth import FastLanguageModel
        
        # 加载训练后的模型
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_path,
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
        )
        
        # 切换到推理模式
        FastLanguageModel.for_inference(model)
        
        # 测试问题
        test_question = "请问如何查询课程表？"
        
        prompt = f"""你是USTB（北京科技大学）的智能教务助手，专门为师生提供准确、及时的教务信息服务。
请根据以下问题提供专业、详细的回答。

问题：{test_question}
回答："""
        
        # 生成回答
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # 解码回答
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = response[len(prompt):].strip()
        
        print(f"🤖 测试问题: {test_question}")
        print(f"💬 模型回答: {answer}")
        print("✅ 模型测试完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("USTB教务助手 - DeepSeek-R1微调训练执行器")
    print("=" * 60)
    
    # 执行训练
    success = execute_training()
    
    if success:
        # 测试训练后的模型
        model_path = "/root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned_merged"
        test_trained_model(model_path)
        
        print("\n🎊 恭喜！USTB教务助手模型训练完成！")
        print("📝 可以开始使用训练后的模型进行教务问答服务")
    else:
        print("\n😞 训练失败，请检查错误信息并重新尝试")
        sys.exit(1)
