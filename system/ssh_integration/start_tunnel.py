#!/usr/bin/env python3
"""
SSH隧道启动脚本 - USTB混合云架构
快速启动本地到AutoDL的SSH隧道连接
"""

import subprocess
import time
import sys
import signal
import os
from typing import Dict, List

class TunnelManager:
    """SSH隧道管理器"""
    
    def __init__(self):
        self.config = {
            "host": "connect.bjb1.seetacloud.com",
            "port": 21020,
            "username": "root",
            "password": "oqpdtTQSuC2B"
        }
        
        self.tunnels = {
            "rag_service": {
                "local_port": 8000,
                "remote_port": 8000,
                "description": "RAG GPU服务"
            },
            "model_inference": {
                "local_port": 8001,
                "remote_port": 8001,
                "description": "模型推理服务"
            }
        }
        
        self.processes = {}
    
    def create_tunnel(self, service_name: str) -> bool:
        """创建SSH隧道"""
        if service_name not in self.tunnels:
            print(f"❌ 未知服务: {service_name}")
            return False
        
        tunnel = self.tunnels[service_name]
        
        print(f"🚀 创建SSH隧道: {tunnel['description']}")
        print(f"   本地端口: {tunnel['local_port']} -> 远程端口: {tunnel['remote_port']}")
        
        # SSH隧道命令
        ssh_cmd = [
            "ssh",
            "-N",  # 不执行远程命令
            "-L", f"{tunnel['local_port']}:localhost:{tunnel['remote_port']}",
            "-p", str(self.config["port"]),
            f"{self.config['username']}@{self.config['host']}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=30"
        ]
        
        try:
            # 启动SSH隧道进程
            process = subprocess.Popen(
                ssh_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送密码
            if process.stdin:
                process.stdin.write(f"{self.config['password']}\n")
                process.stdin.flush()
            
            # 等待连接建立
            time.sleep(3)
            
            # 检查进程状态
            if process.poll() is None:
                self.processes[service_name] = process
                print(f"✅ SSH隧道创建成功: {tunnel['description']}")
                return True
            else:
                print(f"❌ SSH隧道创建失败: {tunnel['description']}")
                return False
                
        except Exception as e:
            print(f"❌ 创建SSH隧道时发生错误: {e}")
            return False
    
    def test_connection(self, service_name: str) -> bool:
        """测试隧道连接"""
        if service_name not in self.tunnels:
            return False
        
        tunnel = self.tunnels[service_name]
        
        try:
            import requests
            response = requests.get(
                f"http://localhost:{tunnel['local_port']}/health",
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ {tunnel['description']} 连接测试成功")
                return True
            else:
                print(f"❌ {tunnel['description']} 连接测试失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {tunnel['description']} 连接测试失败: {e}")
            return False
    
    def cleanup(self):
        """清理所有隧道"""
        print("🧹 清理SSH隧道...")
        for service_name, process in self.processes.items():
            try:
                process.terminate()
                print(f"✅ 已终止隧道: {self.tunnels[service_name]['description']}")
            except Exception as e:
                print(f"❌ 终止隧道时发生错误: {e}")
        
        self.processes.clear()
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n🛑 接收到退出信号，正在清理...")
        self.cleanup()
        sys.exit(0)

def main():
    """主函数"""
    manager = TunnelManager()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    print("🚀 USTB混合云架构 - SSH隧道管理器")
    print("=" * 50)
    
    # 创建RAG服务隧道
    if manager.create_tunnel("rag_service"):
        # 测试连接
        time.sleep(2)
        manager.test_connection("rag_service")
        
        print("\n✅ SSH隧道已建立！")
        print("📍 本地访问地址:")
        print(f"   RAG服务: http://localhost:8000")
        print(f"   健康检查: http://localhost:8000/health")
        print(f"   搜索API: http://localhost:8000/api/v1/search")
        
        print("\n🔄 隧道保持运行中... (Ctrl+C 退出)")
        
        try:
            # 保持运行
            while True:
                time.sleep(10)
                # 定期检查进程状态
                for service_name, process in manager.processes.items():
                    if process.poll() is not None:
                        print(f"⚠️ 隧道进程已退出: {manager.tunnels[service_name]['description']}")
                        # 尝试重连
                        print("🔄 尝试重新连接...")
                        manager.create_tunnel(service_name)
        except KeyboardInterrupt:
            pass
    else:
        print("❌ 无法建立SSH隧道")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
