#!/usr/bin/env python3
"""
AutoDL数据同步脚本
解决训练数据缺失问题
"""

import json
import os
import sys
from pathlib import Path

def create_upload_script():
    """创建数据上传脚本"""
    
    # 读取本地训练数据
    local_data_path = "data/training/qa_dataset.json"
    if not os.path.exists(local_data_path):
        print(f"❌ 本地训练数据不存在: {local_data_path}")
        return False
    
    print(f"✅ 发现本地训练数据: {local_data_path}")
    
    # 读取数据内容
    with open(local_data_path, 'r', encoding='utf-8') as f:
        data_content = f.read()
    
    # 统计数据
    lines = data_content.strip().split('\n')
    print(f"📊 数据统计: {len(lines)} 条训练记录")
    
    # 创建AutoDL上传脚本
    upload_script = f'''#!/bin/bash
# AutoDL训练数据上传脚本
# 解决qa_dataset.json缺失问题

echo "🚀 开始同步USTB训练数据到AutoDL..."

# 确保目录存在
mkdir -p /root/autodl-tmp/data/training

# 创建训练数据文件
cat > /root/autodl-tmp/data/training/qa_dataset.json << 'EOF'
{data_content}
EOF

# 验证文件创建
if [ -f "/root/autodl-tmp/data/training/qa_dataset.json" ]; then
    echo "✅ 训练数据文件创建成功"
    echo "📊 文件大小: $(du -h /root/autodl-tmp/data/training/qa_dataset.json | cut -f1)"
    echo "📋 数据条数: $(wc -l /root/autodl-tmp/data/training/qa_dataset.json | cut -d' ' -f1)"
else
    echo "❌ 训练数据文件创建失败"
    exit 1
fi

# 创建其他必要目录
mkdir -p /root/autodl-tmp/models/trained
mkdir -p /root/autodl-tmp/scripts/training
mkdir -p /root/autodl-tmp/reports
mkdir -p /root/autodl-tmp/logs/training

echo "🎯 AutoDL环境修复完成！"
echo "📍 训练数据位置: /root/autodl-tmp/data/training/qa_dataset.json"
echo "📍 模型保存位置: /root/autodl-tmp/models/trained/"
echo "📍 脚本位置: /root/autodl-tmp/scripts/training/"
echo "📍 日志位置: /root/autodl-tmp/logs/training/"
'''
    
    # 保存上传脚本
    script_path = "temp/autodl_upload.sh"
    os.makedirs("temp", exist_ok=True)
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(upload_script)
    
    print(f"✅ 创建上传脚本: {script_path}")
    print(f"📋 脚本大小: {len(upload_script)} 字符")
    
    return True

def main():
    """主函数"""
    print("🔧 AutoDL数据同步脚本")
    print("=" * 50)
    
    if create_upload_script():
        print("\n🎉 修复脚本创建成功！")
        print("\n📋 下一步操作：")
        print("1. 通过SSH工具执行 temp/autodl_upload.sh 脚本")
        print("2. 验证训练数据已正确上传")
        print("3. 更新模型训练专家配置")
        print("4. 启动模型训练专家")
    else:
        print("\n❌ 修复脚本创建失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
