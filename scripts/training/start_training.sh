#!/bin/bash
# USTB教务助手 - DeepSeek-R1微调训练启动脚本
# 作者: 梁晓阳 (项目经理)
# 日期: 2025-08-06

echo "🚀 USTB教务助手 - DeepSeek-R1微调训练"
echo "=========================================="

# 检查当前目录
echo "📍 当前工作目录: $(pwd)"

# 激活unsloth环境
echo "🔧 激活unsloth环境..."
source /root/miniconda3/bin/activate unsloth

# 设置HuggingFace镜像
echo "🌐 设置HuggingFace镜像..."
export HF_ENDPOINT=https://hf-mirror.com

# 检查GPU状态
echo "🔍 检查GPU状态..."
nvidia-smi

# 检查Python环境
echo "🐍 检查Python环境..."
python --version
pip list | grep -E "(torch|transformers|unsloth|peft)"

# 检查训练数据
echo "📊 检查训练数据..."
if [ -f "/root/autodl-tmp/ustb-project/data/training/qa_dataset.json" ]; then
    echo "✅ 训练数据文件存在"
    echo "📈 数据量: $(cat /root/autodl-tmp/ustb-project/data/training/qa_dataset.json | jq length)"
else
    echo "❌ 训练数据文件不存在"
    exit 1
fi

# 创建输出目录
echo "📁 创建输出目录..."
mkdir -p /root/autodl-tmp/ustb-project/models

# 开始训练
echo "🎓 开始执行训练..."
echo "⚠️ 注意：训练过程预计需要1-2小时，请勿中断"

cd /root/autodl-tmp/ustb-project

# 执行训练脚本
python scripts/training/execute_training.py

# 检查训练结果
if [ $? -eq 0 ]; then
    echo "🎉 训练成功完成！"
    echo "📁 模型保存位置:"
    echo "   - LoRA适配器: /root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned"
    echo "   - 合并模型: /root/autodl-tmp/ustb-project/models/deepseek-ustb-tuned_merged"
else
    echo "❌ 训练失败，请检查错误信息"
    exit 1
fi

echo "✅ 训练脚本执行完成！"
