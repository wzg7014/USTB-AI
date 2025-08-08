#!/usr/bin/env python3
"""
SSH连接管理器 - USTB混合云架构集成
负责管理AutoDL SSH连接、隧道建立和健康检查
"""

import asyncio
import subprocess
import time
import json
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"

@dataclass
class SSHConfig:
    """SSH连接配置"""
    host: str = "connect.bjb1.seetacloud.com"
    port: int = 21020
    username: str = "root"
    password: str = "oqpdtTQSuC2B"  # 2025-08-07 最新密码
    timeout: int = 30
    max_retries: int = 3
    retry_interval: int = 5

@dataclass
class TunnelConfig:
    """SSH隧道配置"""
    local_port: int
    remote_port: int
    service_name: str
    description: str

class SSHConnectionManager:
    """SSH连接管理器"""
    
    def __init__(self, config: SSHConfig = None):
        self.config = config or SSHConfig()
        self.status = ConnectionStatus.DISCONNECTED
        self.tunnels: Dict[str, TunnelConfig] = {}
        self.tunnel_processes: Dict[str, subprocess.Popen] = {}
        self.last_health_check = 0
        self.health_check_interval = 30  # 30秒检查一次
        
        # 预定义服务隧道配置
        self.setup_default_tunnels()
    
    def setup_default_tunnels(self):
        """设置默认的服务隧道配置"""
        self.tunnels = {
            "rag_service": TunnelConfig(
                local_port=8000,
                remote_port=8000,
                service_name="RAG服务",
                description="GPU加速RAG检索服务"
            ),
            "model_inference": TunnelConfig(
                local_port=8001,
                remote_port=8001,
                service_name="模型推理服务",
                description="LoRA微调模型推理服务"
            )
        }
    
    async def test_connection(self) -> Tuple[bool, str]:
        """测试SSH连接"""
        try:
            logger.info("测试AutoDL SSH连接...")

            # 使用autodl-ssh-remote工具测试连接
            import subprocess
            import json

            # 调用autodl-ssh-remote工具
            test_result = subprocess.run([
                "python", "-c",
                f"""
import sys
sys.path.append('.')
from promptx_tool_promptx import promptx_tool_promptx
result = promptx_tool_promptx(
    tool_resource='@tool://autodl-ssh-remote',
    parameters={{
        'host': '{self.config.host}',
        'port': {self.config.port},
        'username': '{self.config.username}',
        'password': '{self.config.password}',
        'command': 'echo "SSH连接测试成功" && date',
        'timeout': 30
    }}
)
print(result)
"""
            ], capture_output=True, text=True, cwd=".")

            if test_result.returncode == 0:
                logger.info("SSH连接测试成功")
                return True, "连接正常"
            else:
                logger.error(f"SSH连接测试失败: {test_result.stderr}")
                return False, test_result.stderr

        except Exception as e:
            logger.error(f"SSH连接测试失败: {e}")
            return False, str(e)
    
    async def create_tunnel(self, tunnel_key: str) -> bool:
        """创建SSH隧道"""
        if tunnel_key not in self.tunnels:
            logger.error(f"未知的隧道配置: {tunnel_key}")
            return False
        
        tunnel = self.tunnels[tunnel_key]
        
        try:
            logger.info(f"创建SSH隧道: {tunnel.service_name} "
                       f"({tunnel.local_port} -> {tunnel.remote_port})")
            
            # SSH隧道命令
            ssh_command = [
                "ssh",
                "-N",  # 不执行远程命令
                "-L", f"{tunnel.local_port}:localhost:{tunnel.remote_port}",
                "-p", str(self.config.port),
                f"{self.config.username}@{self.config.host}",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", f"ConnectTimeout={self.config.timeout}"
            ]
            
            # 启动隧道进程
            process = subprocess.Popen(
                ssh_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送密码（实际实现中应该使用更安全的方式）
            if process.stdin:
                process.stdin.write(f"{self.config.password}\n")
                process.stdin.flush()
            
            # 等待隧道建立
            await asyncio.sleep(2)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                self.tunnel_processes[tunnel_key] = process
                logger.info(f"SSH隧道创建成功: {tunnel.service_name}")
                return True
            else:
                logger.error(f"SSH隧道创建失败: {tunnel.service_name}")
                return False
                
        except Exception as e:
            logger.error(f"创建SSH隧道时发生错误: {e}")
            return False
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查所有隧道"""
        current_time = time.time()
        
        # 检查是否需要进行健康检查
        if current_time - self.last_health_check < self.health_check_interval:
            return {}
        
        self.last_health_check = current_time
        health_status = {}
        
        for tunnel_key, tunnel in self.tunnels.items():
            try:
                # 检查隧道进程是否还在运行
                if tunnel_key in self.tunnel_processes:
                    process = self.tunnel_processes[tunnel_key]
                    if process.poll() is None:
                        # 进程还在运行，测试端口连接
                        health_status[tunnel_key] = await self._test_port(tunnel.local_port)
                    else:
                        # 进程已退出
                        health_status[tunnel_key] = False
                        logger.warning(f"隧道进程已退出: {tunnel.service_name}")
                else:
                    health_status[tunnel_key] = False
                    
            except Exception as e:
                logger.error(f"健康检查失败 {tunnel.service_name}: {e}")
                health_status[tunnel_key] = False
        
        return health_status
    
    async def _test_port(self, port: int) -> bool:
        """测试本地端口是否可访问"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=5
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def auto_reconnect(self, tunnel_key: str) -> bool:
        """自动重连隧道"""
        tunnel = self.tunnels.get(tunnel_key)
        if not tunnel:
            return False
        
        logger.info(f"尝试重连隧道: {tunnel.service_name}")
        
        # 清理旧的进程
        if tunnel_key in self.tunnel_processes:
            try:
                self.tunnel_processes[tunnel_key].terminate()
                del self.tunnel_processes[tunnel_key]
            except:
                pass
        
        # 重新创建隧道
        for attempt in range(self.config.max_retries):
            logger.info(f"重连尝试 {attempt + 1}/{self.config.max_retries}")
            
            if await self.create_tunnel(tunnel_key):
                logger.info(f"隧道重连成功: {tunnel.service_name}")
                return True
            
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_interval)
        
        logger.error(f"隧道重连失败: {tunnel.service_name}")
        return False
    
    def get_tunnel_status(self) -> Dict[str, Dict]:
        """获取所有隧道状态"""
        status = {}
        
        for tunnel_key, tunnel in self.tunnels.items():
            is_running = (tunnel_key in self.tunnel_processes and 
                         self.tunnel_processes[tunnel_key].poll() is None)
            
            status[tunnel_key] = {
                "service_name": tunnel.service_name,
                "description": tunnel.description,
                "local_port": tunnel.local_port,
                "remote_port": tunnel.remote_port,
                "is_running": is_running,
                "process_id": (self.tunnel_processes[tunnel_key].pid 
                             if is_running else None)
            }
        
        return status
    
    def cleanup(self):
        """清理所有隧道连接"""
        logger.info("清理SSH隧道连接...")
        
        for tunnel_key, process in self.tunnel_processes.items():
            try:
                process.terminate()
                logger.info(f"已终止隧道: {self.tunnels[tunnel_key].service_name}")
            except Exception as e:
                logger.error(f"终止隧道时发生错误: {e}")
        
        self.tunnel_processes.clear()
        self.status = ConnectionStatus.DISCONNECTED

# 使用示例
async def main():
    """主函数示例"""
    manager = SSHConnectionManager()
    
    # 测试连接
    success, message = await manager.test_connection()
    print(f"连接测试: {success}, {message}")
    
    # 创建隧道
    if success:
        await manager.create_tunnel("rag_service")
        await manager.create_tunnel("model_inference")
        
        # 获取状态
        status = manager.get_tunnel_status()
        print("隧道状态:", json.dumps(status, indent=2, ensure_ascii=False))
        
        # 健康检查
        health = await manager.health_check()
        print("健康检查:", health)
    
    # 清理
    manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
