#!/usr/bin/env python3
"""
上传RAG数据到AutoDL
"""

import json
import base64
import os

def upload_rag_data():
    """上传RAG数据文件到AutoDL"""
    
    # 读取本地RAG数据文件
    local_file = "data/processed/rag_data.json"
    
    if not os.path.exists(local_file):
        print(f"❌ 本地文件不存在: {local_file}")
        return False
    
    print(f"📁 读取本地文件: {local_file}")
    
    try:
        with open(local_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 数据记录数: {len(data)}")
        
        # 将数据转换为JSON字符串
        json_content = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 计算文件大小
        file_size = len(json_content.encode('utf-8'))
        print(f"📏 文件大小: {file_size / (1024*1024):.2f} MB")
        
        # 将内容编码为base64以便安全传输
        encoded_content = base64.b64encode(json_content.encode('utf-8')).decode('ascii')
        
        # 生成上传脚本
        upload_script = f'''
import base64
import json

# 解码内容
encoded_content = """{encoded_content}"""
content = base64.b64decode(encoded_content).decode('utf-8')

# 写入文件
with open('/root/autodl-tmp/ustb-project/data/processed/rag_data.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ RAG数据文件上传成功")
print(f"📊 文件大小: {{len(content.encode('utf-8')) / (1024*1024):.2f}} MB")

# 验证文件
try:
    with open('/root/autodl-tmp/ustb-project/data/processed/rag_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"📋 验证成功: {{len(data)}} 条记录")
except Exception as e:
    print(f"❌ 验证失败: {{e}}")
'''
        
        # 保存上传脚本
        script_file = "temp_upload_script.py"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(upload_script)
        
        print(f"✅ 上传脚本已生成: {script_file}")
        print(f"📝 脚本大小: {os.path.getsize(script_file) / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理文件失败: {str(e)}")
        return False

if __name__ == "__main__":
    upload_rag_data()
