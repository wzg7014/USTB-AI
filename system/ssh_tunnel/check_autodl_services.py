#!/usr/bin/env python3
"""
检查AutoDL服务状态
直接SSH连接到AutoDL检查RAG和模型服务的运行状态
"""

import subprocess
import time
import sys

def run_ssh_command(command):
    """执行SSH命令"""
    ssh_command = [
        "ssh",
        "-p", "21020",
        "root@connect.bjb1.seetacloud.com",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        command
    ]
    
    try:
        print(f"🔍 执行命令: {command}")
        process = subprocess.Popen(
            ssh_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 发送密码
        process.stdin.write("oqpdtTQSuC2B\n")
        process.stdin.flush()
        process.stdin.close()
        
        # 等待命令完成
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode == 0:
            print(f"✅ 命令执行成功:")
            print(stdout)
        else:
            print(f"❌ 命令执行失败 (返回码: {process.returncode}):")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
        
        return stdout, stderr, process.returncode
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("❌ 命令执行超时")
        return "", "超时", -1
    except Exception as e:
        print(f"❌ SSH连接失败: {e}")
        return "", str(e), -1

def main():
    """主函数"""
    print("🌟 AutoDL服务状态检查器")
    print("=" * 50)
    
    # 检查命令列表
    commands = [
        # 基础系统信息
        ("检查当前目录", "pwd"),
        ("检查项目目录", "ls -la /root/autodl-tmp/ustb-project/"),
        
        # 检查端口占用
        ("检查8000端口", "netstat -tlnp | grep :8000 || echo '端口8000未被占用'"),
        ("检查8004端口", "netstat -tlnp | grep :8004 || echo '端口8004未被占用'"),
        ("检查所有Python进程", "ps aux | grep python | grep -v grep || echo '无Python进程'"),
        
        # 检查服务文件
        ("检查RAG服务文件", "ls -la /root/autodl-tmp/ustb-project/system/rag_system/ | head -10"),
        ("检查模型服务文件", "ls -la /root/autodl-tmp/ustb-project/system/model_service/ | head -10"),
        
        # 检查日志文件
        ("检查最近的日志", "find /root/autodl-tmp/ustb-project/ -name '*.log' -type f -exec ls -la {} \\; | head -5"),
        
        # 尝试启动服务检查
        ("检查Python环境", "which python && python --version"),
        ("检查pip包", "pip list | grep -E '(torch|transformers|fastapi|uvicorn)' | head -5"),
    ]
    
    print("🔍 开始检查AutoDL服务状态...\n")
    
    for description, command in commands:
        print(f"\n📋 {description}")
        print("-" * 40)
        
        stdout, stderr, returncode = run_ssh_command(command)
        
        if returncode != 0:
            print(f"⚠️ 命令执行异常，继续下一个检查...")
        
        time.sleep(1)  # 避免连接过于频繁
    
    print("\n" + "=" * 50)
    print("🎯 检查完成！请根据上述信息分析服务状态")
    print("\n💡 如果发现问题，可能需要:")
    print("   1. 重新启动RAG服务")
    print("   2. 重新启动模型服务") 
    print("   3. 检查Python环境和依赖")
    print("   4. 查看详细的错误日志")

if __name__ == "__main__":
    main()
