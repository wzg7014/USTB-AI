#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试前端问题 - 检查ChatGPT-Next-Web的实际请求
"""

import requests
import json
import time

def test_exact_openai_format():
    """测试完全符合OpenAI格式的响应"""
    print("🔍 测试OpenAI标准格式响应...")
    
    url = "http://localhost:8001/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-ustb-web-backend-api-key"
    }
    
    payload = {
        "model": "ustb-assistant",
        "messages": [
            {
                "role": "user",
                "content": "你好"
            }
        ],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 150
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 响应成功!")
            
            # 检查OpenAI标准字段
            required_fields = ["id", "object", "created", "model", "choices", "usage"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ 缺少必需字段: {missing_fields}")
            else:
                print(f"✅ 所有必需字段都存在")
            
            # 检查choices格式
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                choice_fields = ["index", "message", "finish_reason"]
                choice_missing = []
                
                for field in choice_fields:
                    if field not in choice:
                        choice_missing.append(field)
                
                if choice_missing:
                    print(f"❌ choices[0]缺少字段: {choice_missing}")
                else:
                    print(f"✅ choices[0]格式正确")
                
                # 检查message格式
                if "message" in choice:
                    message = choice["message"]
                    message_fields = ["role", "content"]
                    message_missing = []
                    
                    for field in message_fields:
                        if field not in message:
                            message_missing.append(field)
                    
                    if message_missing:
                        print(f"❌ message缺少字段: {message_missing}")
                    else:
                        print(f"✅ message格式正确")
                        print(f"📝 消息内容: {message['content'][:100]}...")
            
            # 检查object字段值
            if data.get("object") != "chat.completion":
                print(f"❌ object字段错误: {data.get('object')}, 应该是'chat.completion'")
            else:
                print(f"✅ object字段正确")
            
            # 显示完整响应结构
            print(f"\n📋 完整响应结构:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"📝 错误内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_stream_request():
    """测试流式请求"""
    print("\n🔍 测试流式请求...")
    
    url = "http://localhost:8001/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-ustb-web-backend-api-key"
    }
    
    payload = {
        "model": "ustb-assistant",
        "messages": [
            {
                "role": "user",
                "content": "你好"
            }
        ],
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"📊 流式请求状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        print(f"📝 响应内容: {response.text[:200]}...")
        
    except Exception as e:
        print(f"❌ 流式请求异常: {e}")

def check_frontend_config():
    """检查前端配置"""
    print("\n🔍 检查前端配置...")
    
    # 检查前端是否能访问我们的API
    try:
        response = requests.get("http://localhost:3000", timeout=10)
        if response.status_code == 200:
            print(f"✅ 前端服务正常运行")
        else:
            print(f"❌ 前端服务异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 前端服务连接失败: {e}")

if __name__ == "__main__":
    print("🚀 ChatGPT-Next-Web 前端问题调试")
    print("=" * 60)
    
    test_exact_openai_format()
    test_stream_request()
    check_frontend_config()
    
    print("\n" + "=" * 60)
    print("💡 可能的问题原因:")
    print("1. 前端客户端设置覆盖了环境变量配置")
    print("2. 前端期望流式响应但我们只支持非流式")
    print("3. 响应格式的某些细节不符合ChatGPT-Next-Web的期望")
    print("4. 前端缓存了错误的配置")
    print("5. CORS问题导致前端无法正确处理响应")
