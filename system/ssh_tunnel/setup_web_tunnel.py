#!/usr/bin/env python3
"""
USTB AI教务助手 - Web前后端SSH隧道配置器
建立本地Web后端到AutoDL Web API连接器的SSH隧道

功能:
1. 建立SSH隧道: 本地8003 -> AutoDL 8003 (Web API连接器)
2. 健康检查和自动重连
3. 隧道状态监控
4. 一键启动和停止

创建时间: 2025-08-07
作者: 系统集成专家
状态: 生产就绪
"""

import subprocess
import time
import requests
import threading
import signal
import sys
import os
from datetime import datetime

class WebTunnelManager:
    """Web前后端SSH隧道管理器"""
    
    def __init__(self):
        # AutoDL SSH配置
        self.ssh_host = "connect.bjb1.seetacloud.com"
        self.ssh_port = 21020
        self.ssh_user = "root"
        self.ssh_password = "oqpdtTQSuC2B"
        
        # 隧道配置
        self.local_port = 8003  # 本地端口
        self.remote_port = 8003  # AutoDL上的Web API连接器端口
        
        # 状态管理
        self.tunnel_process = None
        self.monitoring = False
        self.start_time = None
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n🛑 收到信号 {signum}，正在关闭SSH隧道...")
        self.stop_tunnel()
        sys.exit(0)
    
    def check_local_port(self):
        """检查本地端口是否被占用"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', self.local_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def kill_existing_tunnel(self):
        """杀死现有的SSH隧道进程"""
        try:
            # 查找占用端口的进程
            result = subprocess.run(
                f"netstat -ano | findstr :{self.local_port}",
                shell=True, capture_output=True, text=True
            )
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) > 4:
                            pid = parts[-1]
                            print(f"🔪 杀死占用端口{self.local_port}的进程 PID: {pid}")
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                            time.sleep(1)
                            break
        except Exception as e:
            print(f"⚠️ 清理现有隧道时出错: {e}")
    
    def start_tunnel(self):
        """启动SSH隧道"""
        print(f"🚀 启动Web前后端SSH隧道...")
        print(f"📍 本地端口: {self.local_port}")
        print(f"📍 远程地址: {self.ssh_host}:{self.ssh_port}")
        print(f"📍 远程端口: {self.remote_port}")
        
        # 检查并清理现有隧道
        if self.check_local_port():
            print(f"⚠️ 端口 {self.local_port} 已被占用，正在清理...")
            self.kill_existing_tunnel()
            time.sleep(2)
        
        # 构建SSH命令
        ssh_command = [
            "ssh",
            "-N",  # 不执行远程命令
            "-L", f"{self.local_port}:localhost:{self.remote_port}",  # 本地端口转发
            "-p", str(self.ssh_port),
            f"{self.ssh_user}@{self.ssh_host}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3"
        ]
        
        try:
            print(f"🔗 建立SSH隧道连接...")
            
            # 启动SSH隧道进程
            self.tunnel_process = subprocess.Popen(
                ssh_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送密码
            if self.tunnel_process.stdin:
                self.tunnel_process.stdin.write(f"{self.ssh_password}\n")
                self.tunnel_process.stdin.flush()
            
            # 等待隧道建立
            print("⏳ 等待隧道建立...")
            time.sleep(5)
            
            # 检查隧道状态
            if self.tunnel_process.poll() is None:
                self.start_time = datetime.now()
                print(f"✅ SSH隧道建立成功！")
                print(f"🌐 Web API连接器地址: http://localhost:{self.local_port}")
                return True
            else:
                error_output = self.tunnel_process.stderr.read() if self.tunnel_process.stderr else "未知错误"
                print(f"❌ SSH隧道建立失败: {error_output}")
                return False
                
        except Exception as e:
            print(f"🚨 启动SSH隧道异常: {e}")
            return False
    
    def test_tunnel(self):
        """测试隧道连接"""
        try:
            print("🧪 测试隧道连接...")
            
            # 测试健康检查接口
            response = requests.get(
                f"http://localhost:{self.local_port}/health",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 隧道连接正常")
                print(f"📊 Web API连接器状态: {data.get('status', 'unknown')}")
                print(f"📊 混合API状态: {data.get('hybrid_api_status', 'unknown')}")
                return True
            else:
                print(f"❌ 隧道连接异常: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ 隧道连接失败: 无法连接到Web API连接器")
            return False
        except Exception as e:
            print(f"🚨 测试隧道连接异常: {e}")
            return False
    
    def monitor_tunnel(self):
        """监控隧道状态"""
        self.monitoring = True
        print("👁️ 开始监控隧道状态...")
        
        while self.monitoring:
            try:
                # 检查SSH进程状态
                if self.tunnel_process and self.tunnel_process.poll() is not None:
                    print("⚠️ SSH隧道进程已退出，尝试重启...")
                    if self.start_tunnel():
                        print("✅ SSH隧道重启成功")
                    else:
                        print("❌ SSH隧道重启失败")
                
                # 测试连接
                if not self.test_tunnel():
                    print("⚠️ 隧道连接测试失败")
                
                # 显示运行时间
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    print(f"⏱️ 隧道运行时间: {uptime}")
                
                time.sleep(30)  # 每30秒检查一次
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"🚨 监控异常: {e}")
                time.sleep(10)
    
    def stop_tunnel(self):
        """停止SSH隧道"""
        print("🛑 正在停止SSH隧道...")
        
        self.monitoring = False
        
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
                print("✅ SSH隧道已停止")
            except subprocess.TimeoutExpired:
                print("⚠️ 强制杀死SSH隧道进程...")
                self.tunnel_process.kill()
                self.tunnel_process.wait()
                print("✅ SSH隧道已强制停止")
            except Exception as e:
                print(f"🚨 停止SSH隧道异常: {e}")
        
        # 清理端口占用
        self.kill_existing_tunnel()
    
    def run(self):
        """运行隧道管理器"""
        print("🌉 USTB Web前后端SSH隧道管理器")
        print("=" * 50)
        
        try:
            # 启动隧道
            if not self.start_tunnel():
                print("❌ 隧道启动失败，退出")
                return False
            
            # 测试隧道
            if not self.test_tunnel():
                print("❌ 隧道测试失败，但继续运行")
            
            # 启动监控线程
            monitor_thread = threading.Thread(target=self.monitor_tunnel, daemon=True)
            monitor_thread.start()
            
            print("\n🎯 隧道已建立，Web后端现在可以连接到混合API系统")
            print(f"🌐 本地Web API连接器: http://localhost:{self.local_port}")
            print("📝 按 Ctrl+C 停止隧道")
            print("=" * 50)
            
            # 主循环
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n👋 用户中断，正在停止...")
        except Exception as e:
            print(f"🚨 运行异常: {e}")
        finally:
            self.stop_tunnel()
            return True

def main():
    """主函数"""
    tunnel_manager = WebTunnelManager()
    tunnel_manager.run()

if __name__ == "__main__":
    main()
