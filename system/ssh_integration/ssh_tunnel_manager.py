#!/usr/bin/env python3
"""
SSH隧道管理器 - 用于连接AutoDL上的RAG系统和模型推理服务
支持自动重连、健康检查和多隧道管理
"""

import time
import threading
import logging
from typing import Dict, Optional, Tuple
from sshtunnel import SSHTunnelForwarder
import requests
import socket

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoDLSSHTunnelManager:
    """AutoDL SSH隧道管理器"""
    
    def __init__(self):
        # AutoDL连接配置
        self.ssh_host = "connect.bjb1.seetacloud.com"
        self.ssh_port = 21020
        self.ssh_username = "root"
        self.ssh_password = "oqpdtTQSuC2B"
        
        # 隧道配置
        self.tunnels: Dict[str, SSHTunnelForwarder] = {}
        self.tunnel_configs = {
            'rag': {
                'local_port': 8004,
                'remote_port': 8000,
                'service_name': 'RAG系统'
            },
            'model': {
                'local_port': 8003,
                'remote_port': 8001,
                'service_name': '模型推理服务'
            },
            'hybrid_api': {
                'local_port': 8005,
                'remote_port': 8002,
                'service_name': '混合API服务'
            }
        }
        
        # 健康检查配置
        self.health_check_interval = 30  # 30秒检查一次
        self.health_check_thread = None
        self.running = False
        
    def create_tunnel(self, service_name: str) -> bool:
        """创建SSH隧道"""
        if service_name not in self.tunnel_configs:
            logger.error(f"未知服务: {service_name}")
            return False
            
        config = self.tunnel_configs[service_name]
        
        try:
            # 检查本地端口是否被占用
            if self._is_port_in_use(config['local_port']):
                logger.warning(f"本地端口 {config['local_port']} 已被占用，尝试关闭现有隧道")
                self.close_tunnel(service_name)
                time.sleep(2)
            
            # 创建SSH隧道
            tunnel = SSHTunnelForwarder(
                (self.ssh_host, self.ssh_port),
                ssh_username=self.ssh_username,
                ssh_password=self.ssh_password,
                local_bind_address=('127.0.0.1', config['local_port']),
                remote_bind_address=('127.0.0.1', config['remote_port']),
                set_keepalive=30.0,  # 保持连接
                compression=True
            )
            
            # 启动隧道
            tunnel.start()
            
            # 验证隧道是否成功建立
            if tunnel.is_active:
                self.tunnels[service_name] = tunnel
                logger.info(f"✅ {config['service_name']} SSH隧道已建立: localhost:{config['local_port']} -> AutoDL:{config['remote_port']}")
                return True
            else:
                logger.error(f"❌ {config['service_name']} SSH隧道建立失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 创建{config['service_name']}隧道时出错: {str(e)}")
            return False
    
    def close_tunnel(self, service_name: str) -> bool:
        """关闭SSH隧道"""
        if service_name in self.tunnels:
            try:
                self.tunnels[service_name].stop()
                del self.tunnels[service_name]
                config = self.tunnel_configs[service_name]
                logger.info(f"🔴 {config['service_name']} SSH隧道已关闭")
                return True
            except Exception as e:
                logger.error(f"❌ 关闭{service_name}隧道时出错: {str(e)}")
                return False
        return True
    
    def create_all_tunnels(self) -> bool:
        """创建所有隧道"""
        success_count = 0
        for service_name in self.tunnel_configs.keys():
            if self.create_tunnel(service_name):
                success_count += 1
                time.sleep(1)  # 避免连接过快
        
        total_count = len(self.tunnel_configs)
        logger.info(f"📊 隧道创建结果: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def close_all_tunnels(self):
        """关闭所有隧道"""
        for service_name in list(self.tunnels.keys()):
            self.close_tunnel(service_name)
    
    def check_tunnel_health(self, service_name: str) -> bool:
        """检查隧道健康状态"""
        if service_name not in self.tunnels:
            return False
            
        tunnel = self.tunnels[service_name]
        config = self.tunnel_configs[service_name]
        
        # 检查隧道是否活跃
        if not tunnel.is_active:
            logger.warning(f"⚠️ {config['service_name']} 隧道不活跃")
            return False
        
        # 检查服务是否响应
        try:
            if service_name == 'rag':
                # 检查RAG服务健康状态
                response = requests.get(f"http://localhost:{config['local_port']}/health", timeout=5)
                return response.status_code == 200
            elif service_name == 'model':
                # 检查模型推理服务健康状态  
                response = requests.get(f"http://localhost:{config['local_port']}/health", timeout=5)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"⚠️ {config['service_name']} 健康检查失败: {str(e)}")
            return False
        
        return True
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def _health_check_loop(self):
        """健康检查循环"""
        while self.running:
            try:
                for service_name in self.tunnel_configs.keys():
                    if service_name in self.tunnels:
                        if not self.check_tunnel_health(service_name):
                            logger.warning(f"🔄 {self.tunnel_configs[service_name]['service_name']} 健康检查失败，尝试重连")
                            self.close_tunnel(service_name)
                            time.sleep(2)
                            self.create_tunnel(service_name)
                
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"❌ 健康检查循环出错: {str(e)}")
                time.sleep(10)
    
    def start_health_monitoring(self):
        """启动健康监控"""
        if self.health_check_thread is None or not self.health_check_thread.is_alive():
            self.running = True
            self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_check_thread.start()
            logger.info("🔍 SSH隧道健康监控已启动")
    
    def stop_health_monitoring(self):
        """停止健康监控"""
        self.running = False
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
        logger.info("🛑 SSH隧道健康监控已停止")
    
    def get_tunnel_status(self) -> Dict[str, Dict]:
        """获取所有隧道状态"""
        status = {}
        for service_name, config in self.tunnel_configs.items():
            is_active = service_name in self.tunnels and self.tunnels[service_name].is_active
            is_healthy = self.check_tunnel_health(service_name) if is_active else False
            
            status[service_name] = {
                'service_name': config['service_name'],
                'local_port': config['local_port'],
                'remote_port': config['remote_port'],
                'is_active': is_active,
                'is_healthy': is_healthy,
                'status': '🟢 正常' if is_healthy else ('🟡 连接但不健康' if is_active else '🔴 未连接')
            }
        
        return status
    
    def print_status(self):
        """打印隧道状态"""
        print("\n" + "="*60)
        print("🚇 AutoDL SSH隧道状态")
        print("="*60)
        
        status = self.get_tunnel_status()
        for service_name, info in status.items():
            print(f"{info['status']} {info['service_name']}")
            print(f"   本地端口: {info['local_port']} -> AutoDL端口: {info['remote_port']}")
            print(f"   连接状态: {'活跃' if info['is_active'] else '未连接'}")
            print(f"   健康状态: {'健康' if info['is_healthy'] else '不健康'}")
            print()

def main():
    """主函数 - 用于测试"""
    manager = AutoDLSSHTunnelManager()
    
    try:
        print("🚀 启动AutoDL SSH隧道管理器...")
        
        # 创建所有隧道
        if manager.create_all_tunnels():
            print("✅ 所有隧道创建成功")
        else:
            print("⚠️ 部分隧道创建失败")
        
        # 启动健康监控
        manager.start_health_monitoring()
        
        # 显示状态
        manager.print_status()
        
        # 保持运行
        print("按 Ctrl+C 退出...")
        while True:
            time.sleep(10)
            manager.print_status()
            
    except KeyboardInterrupt:
        print("\n🛑 正在关闭隧道...")
        manager.stop_health_monitoring()
        manager.close_all_tunnels()
        print("✅ 隧道管理器已关闭")

if __name__ == "__main__":
    main()
