#!/usr/bin/env python3
"""
USTB项目 AutoDL环境服务状态检查脚本
用于检查所有服务的运行状态和健康状况

功能:
1. 检查所有服务的运行状态
2. 验证服务健康检查接口
3. 检查GPU和系统资源使用情况
4. 生成状态报告

使用方法:
python check_services.py
"""

import requests
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class USTBServiceChecker:
    """USTB服务状态检查器"""
    
    def __init__(self):
        self.services = {
            "RAG服务": {
                "url": "http://localhost:8000",
                "health_endpoint": "/health",
                "port": 8000,
                "process_name": "rag_service_v2.py"
            },
            "LoRA推理服务": {
                "url": "http://localhost:8004", 
                "health_endpoint": "/health",
                "port": 8004,
                "process_name": "ustb_lora_inference_server.py"
            },
            "Web API连接器": {
                "url": "http://localhost:8003",
                "health_endpoint": "/health", 
                "port": 8003,
                "process_name": "web_api_connector.py"
            }
        }
        
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system": {},
            "summary": {}
        }
    
    def check_process_running(self, process_name: str) -> bool:
        """检查进程是否运行"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False
    
    def check_port_listening(self, port: int) -> bool:
        """检查端口是否监听"""
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False
    
    def check_service_health(self, service_name: str, service_config: Dict) -> Dict:
        """检查服务健康状态"""
        status = {
            "name": service_name,
            "process_running": False,
            "port_listening": False,
            "health_check": False,
            "response_time": None,
            "health_data": None,
            "error": None
        }
        
        try:
            # 检查进程
            status["process_running"] = self.check_process_running(service_config["process_name"])
            
            # 检查端口
            status["port_listening"] = self.check_port_listening(service_config["port"])
            
            # 健康检查
            if status["process_running"] and status["port_listening"]:
                start_time = time.time()
                try:
                    response = requests.get(
                        f"{service_config['url']}{service_config['health_endpoint']}",
                        timeout=10
                    )
                    status["response_time"] = time.time() - start_time
                    
                    if response.status_code == 200:
                        status["health_check"] = True
                        status["health_data"] = response.json()
                    else:
                        status["error"] = f"HTTP {response.status_code}: {response.text}"
                        
                except requests.exceptions.RequestException as e:
                    status["error"] = f"请求异常: {str(e)}"
            
        except Exception as e:
            status["error"] = f"检查异常: {str(e)}"
        
        return status
    
    def check_gpu_status(self) -> Dict:
        """检查GPU状态"""
        gpu_status = {
            "available": False,
            "devices": [],
            "error": None
        }
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                gpu_status["available"] = True
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 6:
                            gpu_status["devices"].append({
                                "index": int(parts[0]),
                                "name": parts[1],
                                "utilization": f"{parts[2]}%",
                                "memory_used": f"{parts[3]} MB",
                                "memory_total": f"{parts[4]} MB",
                                "temperature": f"{parts[5]}°C"
                            })
            else:
                gpu_status["error"] = "nvidia-smi命令执行失败"
                
        except Exception as e:
            gpu_status["error"] = f"GPU检查异常: {str(e)}"
        
        return gpu_status
    
    def check_system_resources(self) -> Dict:
        """检查系统资源"""
        system_status = {
            "cpu_usage": None,
            "memory_usage": None,
            "disk_usage": None,
            "load_average": None,
            "error": None
        }
        
        try:
            # CPU使用率
            result = subprocess.run(
                ["top", "-bn1", "|", "grep", "Cpu", "|", "awk", "'{print $2}'"],
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                system_status["cpu_usage"] = result.stdout.strip()
            
            # 内存使用率
            result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Mem:' in line:
                        parts = line.split()
                        system_status["memory_usage"] = {
                            "total": parts[1],
                            "used": parts[2],
                            "available": parts[6] if len(parts) > 6 else parts[3]
                        }
            
            # 磁盘使用率
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    system_status["disk_usage"] = {
                        "total": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "usage_percent": parts[4]
                    }
            
            # 负载平均值
            result = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if "load average:" in output:
                    load_part = output.split("load average:")[1].strip()
                    system_status["load_average"] = load_part
                    
        except Exception as e:
            system_status["error"] = f"系统资源检查异常: {str(e)}"
        
        return system_status
    
    def generate_report(self) -> Dict:
        """生成完整的状态报告"""
        print("🔍 开始检查USTB项目服务状态...")
        
        # 检查所有服务
        for service_name, service_config in self.services.items():
            print(f"📊 检查 {service_name}...")
            self.report["services"][service_name] = self.check_service_health(service_name, service_config)
        
        # 检查GPU状态
        print("🖥️ 检查GPU状态...")
        self.report["system"]["gpu"] = self.check_gpu_status()
        
        # 检查系统资源
        print("💻 检查系统资源...")
        self.report["system"]["resources"] = self.check_system_resources()
        
        # 生成摘要
        self.generate_summary()
        
        return self.report
    
    def generate_summary(self):
        """生成状态摘要"""
        total_services = len(self.services)
        healthy_services = 0
        running_services = 0
        
        for service_name, status in self.report["services"].items():
            if status["process_running"]:
                running_services += 1
            if status["health_check"]:
                healthy_services += 1
        
        self.report["summary"] = {
            "total_services": total_services,
            "running_services": running_services,
            "healthy_services": healthy_services,
            "all_healthy": healthy_services == total_services,
            "gpu_available": self.report["system"]["gpu"]["available"],
            "overall_status": "健康" if healthy_services == total_services else "异常"
        }
    
    def print_report(self):
        """打印格式化的状态报告"""
        print("\n" + "="*60)
        print("🎯 USTB项目服务状态报告")
        print("="*60)
        print(f"📅 检查时间: {self.report['timestamp']}")
        print(f"📊 总体状态: {self.report['summary']['overall_status']}")
        print(f"🔢 服务统计: {self.report['summary']['healthy_services']}/{self.report['summary']['total_services']} 健康")
        
        print("\n📋 服务详情:")
        print("-" * 60)
        
        for service_name, status in self.report["services"].items():
            status_icon = "✅" if status["health_check"] else "❌"
            print(f"{status_icon} {service_name}")
            print(f"   进程运行: {'✅' if status['process_running'] else '❌'}")
            print(f"   端口监听: {'✅' if status['port_listening'] else '❌'}")
            print(f"   健康检查: {'✅' if status['health_check'] else '❌'}")
            
            if status["response_time"]:
                print(f"   响应时间: {status['response_time']:.3f}s")
            
            if status["error"]:
                print(f"   错误信息: {status['error']}")
            
            if status["health_data"]:
                health_data = status["health_data"]
                if "version" in health_data:
                    print(f"   版本: {health_data['version']}")
                if "uptime" in health_data or "service_uptime" in health_data:
                    uptime = health_data.get("uptime", health_data.get("service_uptime", 0))
                    print(f"   运行时间: {uptime:.1f}s")
            
            print()
        
        print("🖥️ GPU状态:")
        print("-" * 60)
        gpu_status = self.report["system"]["gpu"]
        
        if gpu_status["available"]:
            print("✅ GPU可用")
            for gpu in gpu_status["devices"]:
                print(f"   GPU {gpu['index']}: {gpu['name']}")
                print(f"   利用率: {gpu['utilization']}")
                print(f"   显存: {gpu['memory_used']}/{gpu['memory_total']}")
                print(f"   温度: {gpu['temperature']}")
        else:
            print("❌ GPU不可用")
            if gpu_status["error"]:
                print(f"   错误: {gpu_status['error']}")
        
        print("\n💻 系统资源:")
        print("-" * 60)
        resources = self.report["system"]["resources"]
        
        if resources["memory_usage"]:
            mem = resources["memory_usage"]
            print(f"内存: {mem['used']}/{mem['total']} (可用: {mem['available']})")
        
        if resources["disk_usage"]:
            disk = resources["disk_usage"]
            print(f"磁盘: {disk['used']}/{disk['total']} ({disk['usage_percent']})")
        
        if resources["load_average"]:
            print(f"负载: {resources['load_average']}")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    checker = USTBServiceChecker()
    
    try:
        # 生成报告
        report = checker.generate_report()
        
        # 打印报告
        checker.print_report()
        
        # 保存JSON报告
        report_file = f"/root/autodl-tmp/ustb-project/logs/service_status_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 详细报告已保存到: {report_file}")
        
        # 返回退出码
        if report["summary"]["all_healthy"]:
            print("🎉 所有服务运行正常！")
            exit(0)
        else:
            print("⚠️ 部分服务存在问题，请检查！")
            exit(1)
            
    except Exception as e:
        print(f"❌ 检查过程中发生异常: {str(e)}")
        exit(2)

if __name__ == "__main__":
    main()

"""
使用方法:

1. 在AutoDL环境中运行:
cd /root/autodl-tmp/ustb-project/scripts/
python check_services.py

2. 通过SSH隧道在本地运行:
# 需要先建立SSH隧道
ssh -p 21020 -L 8000:localhost:8000 -L 8003:localhost:8003 -L 8004:localhost:8004 root@connect.bjb1.seetacloud.com

# 然后在本地运行检查脚本
python check_services.py

3. 定时检查 (可选):
# 添加到crontab，每5分钟检查一次
*/5 * * * * cd /root/autodl-tmp/ustb-project/scripts && python check_services.py >> /root/autodl-tmp/ustb-project/logs/health_check.log 2>&1
"""
