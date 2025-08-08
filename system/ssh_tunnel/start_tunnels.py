#!/usr/bin/env python3
"""
快速启动AutoDL SSH隧道 - 简化版
一键启动RAG服务和模型服务的SSH隧道
"""

import subprocess
import time
import requests
import sys
import os

def check_service(port, name):
    """检查服务是否可访问"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} (端口{port}) 连接正常")
            return True
        else:
            print(f"❌ {name} (端口{port}) HTTP状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name} (端口{port}) 连接失败: {e}")
        return False

def kill_port_process(port):
    """终止占用端口的进程 (Windows)"""
    try:
        # 查找占用端口的进程
        result = subprocess.run(
            f'netstat -ano | findstr ":{port}"',
            shell=True, capture_output=True, text=True
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        print(f"🔪 已终止占用端口{port}的进程 PID:{pid}")
                        return True
        return False
    except Exception as e:
        print(f"⚠️ 终止端口{port}进程失败: {e}")
        return False

def create_ssh_tunnel(local_port, remote_port, service_name):
    """创建SSH隧道"""
    print(f"🚀 启动 {service_name} SSH隧道 ({local_port}→{remote_port})...")
    
    # 检查并清理端口
    kill_port_process(local_port)
    time.sleep(1)
    
    # SSH命令
    ssh_command = [
        "ssh", "-N",
        "-L", f"{local_port}:localhost:{remote_port}",
        "-p", "21020",
        "root@connect.bjb1.seetacloud.com",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ServerAliveInterval=30"
    ]
    
    try:
        # 启动SSH进程
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
        
        # 等待隧道建立
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ {service_name} SSH隧道启动成功")
            return process
        else:
            stderr = process.stderr.read() if process.stderr else "无错误信息"
            print(f"❌ {service_name} SSH隧道启动失败: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 创建SSH隧道失败: {e}")
        return None

def main():
    """主函数"""
    print("🌟 USTB混合云架构 - AutoDL SSH隧道启动器")
    print("=" * 50)
    
    # 隧道配置
    tunnels = [
        {"local": 8000, "remote": 8000, "name": "RAG检索服务"},
        {"local": 8081, "remote": 8004, "name": "模型推理服务"}
    ]
    
    processes = []
    
    try:
        # 启动所有隧道
        for tunnel in tunnels:
            process = create_ssh_tunnel(
                tunnel["local"], 
                tunnel["remote"], 
                tunnel["name"]
            )
            if process:
                processes.append((process, tunnel))
        
        if not processes:
            print("❌ 没有成功启动任何隧道")
            return
        
        print("\n⏳ 等待隧道稳定...")
        time.sleep(5)
        
        # 验证连接
        print("\n🔍 验证服务连接...")
        all_healthy = True
        for _, tunnel in processes:
            if not check_service(tunnel["local"], tunnel["name"]):
                all_healthy = False
        
        if all_healthy:
            print("\n🎉 所有服务连接正常！混合云架构就绪！")
            print("\n📋 服务访问地址:")
            print("   RAG检索服务: http://localhost:8000")
            print("   模型推理服务: http://localhost:8081")
            print("\n🔄 隧道保持运行中... (Ctrl+C 停止)")
            
            # 保持运行
            while True:
                time.sleep(30)
                # 定期检查
                print("📊 定期检查服务状态...")
                for _, tunnel in processes:
                    check_service(tunnel["local"], tunnel["name"])
        else:
            print("\n⚠️ 部分服务连接异常，请检查AutoDL服务状态")
            
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭隧道...")
    finally:
        # 清理进程
        for process, tunnel in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {tunnel['name']} 隧道已停止")
            except:
                process.kill()
                print(f"🔪 强制终止 {tunnel['name']} 隧道")
        
        print("👋 SSH隧道管理器已退出")

if __name__ == "__main__":
    main()
