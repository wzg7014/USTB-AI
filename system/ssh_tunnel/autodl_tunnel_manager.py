#!/usr/bin/env python3
"""
AutoDL SSH隧道管理器 - USTB混合云架构
自动建立和管理到AutoDL的SSH隧道连接
"""

import subprocess
import threading
import time
import socket
import requests
import json
from typing import Dict, List, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoDLTunnelManager:
    """AutoDL SSH隧道管理器"""
    
    def __init__(self):
        # AutoDL连接信息
        self.ssh_config = {
            "host": "connect.bjb1.seetacloud.com",
            "port": 21020,
            "username": "root",
            "password": "oqpdtTQSuC2B"
        }
        
        # 隧道配置
        self.tunnels = {
            "rag_service": {
                "local_port": 8000,
                "remote_port": 8000,
                "service_name": "RAG检索服务",
                "health_endpoint": "/health"
            },
            "model_service": {
                "local_port": 8081,
                "remote_port": 8004,
                "service_name": "模型推理服务", 
                "health_endpoint": "/health"
            }
        }
        
        self.tunnel_processes = {}
        self.tunnel_threads = {}
        self.running = False
    
    def check_port_available(self, port: int) -> bool:
        """检查本地端口是否可用"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return True
        except OSError:
            return False
    
    def check_service_health(self, local_port: int, health_endpoint: str) -> bool:
        """检查服务健康状态"""
        try:
            response = requests.get(f"http://localhost:{local_port}{health_endpoint}", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def create_ssh_tunnel(self, tunnel_name: str, local_port: int, remote_port: int) -> Optional[subprocess.Popen]:
        """创建SSH隧道"""
        try:
            # 检查本地端口
            if not self.check_port_available(local_port):
                logger.warning(f"本地端口 {local_port} 已被占用，尝试终止占用进程...")
                self.kill_port_process(local_port)
                time.sleep(2)
            
            # 构建SSH命令
            ssh_command = [
                "ssh",
                "-N",  # 不执行远程命令
                "-L", f"{local_port}:localhost:{remote_port}",  # 本地端口转发
                "-p", str(self.ssh_config["port"]),
                f"{self.ssh_config['username']}@{self.ssh_config['host']}",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3"
            ]
            
            logger.info(f"🚀 启动SSH隧道: {tunnel_name} ({local_port}→{remote_port})")
            
            # 启动SSH进程
            process = subprocess.Popen(
                ssh_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送密码
            if process.stdin:
                process.stdin.write(self.ssh_config["password"] + "\n")
                process.stdin.flush()
            
            # 等待隧道建立
            time.sleep(3)
            
            # 检查进程状态
            if process.poll() is None:
                logger.info(f"✅ SSH隧道 {tunnel_name} 启动成功")
                return process
            else:
                stderr_output = process.stderr.read() if process.stderr else "无错误信息"
                logger.error(f"❌ SSH隧道 {tunnel_name} 启动失败: {stderr_output}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 创建SSH隧道失败: {e}")
            return None
    
    def kill_port_process(self, port: int):
        """终止占用端口的进程"""
        try:
            # Windows命令
            result = subprocess.run(
                ["netstat", "-ano", "|", "findstr", f":{port}"],
                shell=True, capture_output=True, text=True
            )
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            subprocess.run(["taskkill", "/F", "/PID", pid], 
                                         capture_output=True)
                            logger.info(f"已终止占用端口{port}的进程 PID:{pid}")
        except Exception as e:
            logger.warning(f"终止端口{port}进程失败: {e}")
    
    def monitor_tunnel(self, tunnel_name: str, process: subprocess.Popen):
        """监控隧道状态"""
        tunnel_config = self.tunnels[tunnel_name]
        local_port = tunnel_config["local_port"]
        health_endpoint = tunnel_config["health_endpoint"]
        
        while self.running and process.poll() is None:
            try:
                # 检查服务健康状态
                if self.check_service_health(local_port, health_endpoint):
                    logger.debug(f"✅ {tunnel_name} 隧道正常")
                else:
                    logger.warning(f"⚠️ {tunnel_name} 服务无响应")
                
                time.sleep(30)  # 30秒检查一次
                
            except Exception as e:
                logger.error(f"❌ 监控隧道 {tunnel_name} 出错: {e}")
                break
        
        logger.info(f"🔚 隧道 {tunnel_name} 监控结束")
    
    def start_all_tunnels(self):
        """启动所有SSH隧道"""
        logger.info("🚀 开始启动所有SSH隧道...")
        self.running = True
        
        for tunnel_name, config in self.tunnels.items():
            local_port = config["local_port"]
            remote_port = config["remote_port"]
            
            # 创建隧道
            process = self.create_ssh_tunnel(tunnel_name, local_port, remote_port)
            
            if process:
                self.tunnel_processes[tunnel_name] = process
                
                # 启动监控线程
                monitor_thread = threading.Thread(
                    target=self.monitor_tunnel,
                    args=(tunnel_name, process),
                    daemon=True
                )
                monitor_thread.start()
                self.tunnel_threads[tunnel_name] = monitor_thread
                
                logger.info(f"✅ {config['service_name']} 隧道已启动")
            else:
                logger.error(f"❌ {config['service_name']} 隧道启动失败")
        
        # 等待隧道稳定
        logger.info("⏳ 等待隧道稳定...")
        time.sleep(5)
        
        # 验证所有隧道
        self.verify_all_tunnels()
    
    def verify_all_tunnels(self):
        """验证所有隧道连接"""
        logger.info("🔍 验证隧道连接状态...")
        
        all_healthy = True
        for tunnel_name, config in self.tunnels.items():
            local_port = config["local_port"]
            health_endpoint = config["health_endpoint"]
            service_name = config["service_name"]
            
            if self.check_service_health(local_port, health_endpoint):
                logger.info(f"✅ {service_name} 连接正常 (端口{local_port})")
            else:
                logger.error(f"❌ {service_name} 连接失败 (端口{local_port})")
                all_healthy = False
        
        if all_healthy:
            logger.info("🎉 所有SSH隧道验证通过！混合云架构就绪！")
        else:
            logger.warning("⚠️ 部分隧道连接异常，请检查AutoDL服务状态")
        
        return all_healthy
    
    def stop_all_tunnels(self):
        """停止所有SSH隧道"""
        logger.info("🛑 停止所有SSH隧道...")
        self.running = False
        
        for tunnel_name, process in self.tunnel_processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"✅ 隧道 {tunnel_name} 已停止")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.info(f"🔪 强制终止隧道 {tunnel_name}")
            except Exception as e:
                logger.error(f"❌ 停止隧道 {tunnel_name} 失败: {e}")
        
        self.tunnel_processes.clear()
        self.tunnel_threads.clear()
    
    def get_tunnel_status(self) -> Dict:
        """获取隧道状态"""
        status = {
            "timestamp": time.time(),
            "running": self.running,
            "tunnels": {}
        }
        
        for tunnel_name, config in self.tunnels.items():
            local_port = config["local_port"]
            health_endpoint = config["health_endpoint"]
            
            tunnel_status = {
                "service_name": config["service_name"],
                "local_port": local_port,
                "remote_port": config["remote_port"],
                "process_running": tunnel_name in self.tunnel_processes and 
                                self.tunnel_processes[tunnel_name].poll() is None,
                "service_healthy": self.check_service_health(local_port, health_endpoint)
            }
            
            status["tunnels"][tunnel_name] = tunnel_status
        
        return status

def main():
    """主函数"""
    manager = AutoDLTunnelManager()
    
    try:
        # 启动所有隧道
        manager.start_all_tunnels()
        
        # 保持运行
        logger.info("🔄 SSH隧道管理器运行中... (Ctrl+C 停止)")
        while True:
            time.sleep(60)
            
            # 定期检查状态
            status = manager.get_tunnel_status()
            healthy_count = sum(1 for t in status["tunnels"].values() if t["service_healthy"])
            total_count = len(status["tunnels"])
            
            logger.info(f"📊 隧道状态: {healthy_count}/{total_count} 健康")
            
    except KeyboardInterrupt:
        logger.info("🛑 收到停止信号...")
    finally:
        manager.stop_all_tunnels()
        logger.info("👋 SSH隧道管理器已退出")

if __name__ == "__main__":
    main()
