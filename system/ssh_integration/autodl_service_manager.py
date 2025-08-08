#!/usr/bin/env python3
"""
AutoDL服务管理器 - 用于管理AutoDL上的RAG系统和模型推理服务
通过SSH远程启动、停止和监控服务
"""

import json
import time
import logging
from typing import Dict, Optional, List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoDLServiceManager:
    """AutoDL服务管理器"""
    
    def __init__(self):
        # AutoDL连接配置
        self.ssh_config = {
            "host": "connect.bjb1.seetacloud.com",
            "port": 21020,
            "username": "root",
            "password": "oqpdtTQSuC2B",
            "timeout": 300
        }
        
        # 服务配置
        self.services = {
            'rag': {
                'name': 'RAG系统',
                'port': 8000,
                'script_path': '/root/autodl-tmp/ustb-project/services/rag_system/main.py',
                'working_dir': '/root/autodl-tmp/ustb-project/services/rag_system',
                'log_file': '/root/autodl-tmp/ustb-project/logs/rag_service.log',
                'pid_file': '/root/autodl-tmp/ustb-project/logs/rag_service.pid'
            },
            'model': {
                'name': '模型推理服务',
                'port': 8001,
                'script_path': '/root/autodl-tmp/ustb-project/services/model_inference/qwen_inference_server_8004_fixed.py',
                'working_dir': '/root/autodl-tmp/ustb-project/services/model_inference',
                'log_file': '/root/autodl-tmp/ustb-project/logs/model_service.log',
                'pid_file': '/root/autodl-tmp/ustb-project/logs/model_service.pid'
            }
        }
    
    def execute_ssh_command(self, command: str, working_dir: str = "/root", timeout: int = 300) -> Tuple[bool, str, int]:
        """执行SSH命令"""
        try:
            # 这里需要调用autodl-ssh-remote工具
            # 由于我们在Python中，需要通过其他方式调用
            # 暂时返回模拟结果，实际使用时需要集成工具调用
            logger.info(f"执行SSH命令: {command}")
            logger.info(f"工作目录: {working_dir}")
            
            # TODO: 实际调用autodl-ssh-remote工具
            # 这里需要通过适当的方式调用MCP工具
            
            return True, "命令执行成功", 0
            
        except Exception as e:
            logger.error(f"SSH命令执行失败: {str(e)}")
            return False, str(e), 1
    
    def check_service_status(self, service_name: str) -> Dict:
        """检查服务状态"""
        if service_name not in self.services:
            return {"error": f"未知服务: {service_name}"}
        
        service = self.services[service_name]
        
        # 检查端口是否被占用
        check_port_cmd = f"netstat -tlnp | grep :{service['port']}"
        success, output, exit_code = self.execute_ssh_command(check_port_cmd)
        
        port_in_use = success and exit_code == 0 and str(service['port']) in output
        
        # 检查进程是否存在
        if 'pid_file' in service:
            check_pid_cmd = f"if [ -f {service['pid_file']} ]; then cat {service['pid_file']}; else echo 'no_pid'; fi"
            success, pid_output, _ = self.execute_ssh_command(check_pid_cmd)
            
            if success and pid_output.strip() != 'no_pid':
                pid = pid_output.strip()
                check_process_cmd = f"ps -p {pid} -o pid,cmd --no-headers"
                success, process_output, exit_code = self.execute_ssh_command(check_process_cmd)
                process_running = success and exit_code == 0 and pid in process_output
            else:
                process_running = False
                pid = None
        else:
            process_running = False
            pid = None
        
        return {
            "service_name": service['name'],
            "port": service['port'],
            "port_in_use": port_in_use,
            "process_running": process_running,
            "pid": pid,
            "status": "运行中" if (port_in_use and process_running) else "未运行"
        }
    
    def start_service(self, service_name: str) -> Dict:
        """启动服务"""
        if service_name not in self.services:
            return {"success": False, "error": f"未知服务: {service_name}"}
        
        service = self.services[service_name]
        
        # 检查服务是否已经运行
        status = self.check_service_status(service_name)
        if status.get("status") == "运行中":
            return {"success": True, "message": f"{service['name']}已经在运行中"}
        
        # 创建必要的目录
        create_dirs_cmd = f"mkdir -p {service['working_dir']} /root/autodl-tmp/ustb-project/logs"
        success, output, exit_code = self.execute_ssh_command(create_dirs_cmd)
        
        if not success:
            return {"success": False, "error": f"创建目录失败: {output}"}
        
        # 启动服务
        if service_name == 'rag':
            start_cmd = self._get_rag_start_command(service)
        elif service_name == 'model':
            start_cmd = self._get_model_start_command(service)
        else:
            return {"success": False, "error": f"不支持的服务类型: {service_name}"}
        
        logger.info(f"启动{service['name']}: {start_cmd}")
        success, output, exit_code = self.execute_ssh_command(start_cmd, service['working_dir'])
        
        if success and exit_code == 0:
            # 等待服务启动
            time.sleep(3)
            
            # 验证服务是否成功启动
            status = self.check_service_status(service_name)
            if status.get("status") == "运行中":
                return {"success": True, "message": f"{service['name']}启动成功", "status": status}
            else:
                return {"success": False, "error": f"{service['name']}启动失败，请检查日志"}
        else:
            return {"success": False, "error": f"启动命令执行失败: {output}"}
    
    def stop_service(self, service_name: str) -> Dict:
        """停止服务"""
        if service_name not in self.services:
            return {"success": False, "error": f"未知服务: {service_name}"}
        
        service = self.services[service_name]
        
        # 检查服务状态
        status = self.check_service_status(service_name)
        if status.get("status") != "运行中":
            return {"success": True, "message": f"{service['name']}已经停止"}
        
        # 尝试优雅停止
        if status.get("pid"):
            stop_cmd = f"kill {status['pid']}"
            success, output, exit_code = self.execute_ssh_command(stop_cmd)
            
            if success:
                time.sleep(2)
                # 检查是否成功停止
                new_status = self.check_service_status(service_name)
                if new_status.get("status") != "运行中":
                    # 清理PID文件
                    cleanup_cmd = f"rm -f {service['pid_file']}"
                    self.execute_ssh_command(cleanup_cmd)
                    return {"success": True, "message": f"{service['name']}已停止"}
        
        # 强制停止
        force_stop_cmd = f"pkill -f {service['script_path']}"
        success, output, exit_code = self.execute_ssh_command(force_stop_cmd)
        
        # 清理PID文件
        cleanup_cmd = f"rm -f {service['pid_file']}"
        self.execute_ssh_command(cleanup_cmd)
        
        return {"success": True, "message": f"{service['name']}已强制停止"}
    
    def _get_rag_start_command(self, service: Dict) -> str:
        """获取RAG服务启动命令"""
        return f"""
cd {service['working_dir']} && 
nohup python {service['script_path']} > {service['log_file']} 2>&1 & 
echo $! > {service['pid_file']}
""".strip().replace('\n', ' ')
    
    def _get_model_start_command(self, service: Dict) -> str:
        """获取模型推理服务启动命令"""
        # 注意：模型服务实际运行在8004端口，但我们需要在8001端口提供服务
        return f"""
cd {service['working_dir']} && 
nohup python {service['script_path']} > {service['log_file']} 2>&1 & 
echo $! > {service['pid_file']}
""".strip().replace('\n', ' ')
    
    def get_all_services_status(self) -> Dict:
        """获取所有服务状态"""
        status = {}
        for service_name in self.services.keys():
            status[service_name] = self.check_service_status(service_name)
        return status
    
    def start_all_services(self) -> Dict:
        """启动所有服务"""
        results = {}
        for service_name in self.services.keys():
            results[service_name] = self.start_service(service_name)
            time.sleep(2)  # 避免同时启动造成资源竞争
        return results
    
    def stop_all_services(self) -> Dict:
        """停止所有服务"""
        results = {}
        for service_name in self.services.keys():
            results[service_name] = self.stop_service(service_name)
        return results
    
    def print_services_status(self):
        """打印所有服务状态"""
        print("\n" + "="*60)
        print("🖥️  AutoDL服务状态")
        print("="*60)
        
        status = self.get_all_services_status()
        for service_name, info in status.items():
            if 'error' in info:
                print(f"❌ {info.get('error', '未知错误')}")
                continue
                
            status_icon = "🟢" if info['status'] == "运行中" else "🔴"
            print(f"{status_icon} {info['service_name']}")
            print(f"   端口: {info['port']}")
            print(f"   状态: {info['status']}")
            if info.get('pid'):
                print(f"   进程ID: {info['pid']}")
            print()

def main():
    """主函数 - 用于测试"""
    manager = AutoDLServiceManager()
    
    try:
        print("🚀 AutoDL服务管理器")
        print("1. 检查服务状态")
        manager.print_services_status()
        
        print("\n2. 启动所有服务")
        results = manager.start_all_services()
        for service_name, result in results.items():
            if result['success']:
                print(f"✅ {service_name}: {result['message']}")
            else:
                print(f"❌ {service_name}: {result['error']}")
        
        print("\n3. 最终状态")
        manager.print_services_status()
        
    except Exception as e:
        print(f"❌ 执行出错: {str(e)}")

if __name__ == "__main__":
    main()
