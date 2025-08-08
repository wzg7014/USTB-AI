#!/usr/bin/env python3
"""
SSH隧道健康监控器 - USTB混合云架构集成
负责监控SSH隧道状态、自动重连和告警
"""

import asyncio
import time
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from ssh_connection_manager import SSHConnectionManager, ConnectionStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    service_name: str
    status: HealthStatus
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class MonitorConfig:
    """监控配置"""
    check_interval: int = 30  # 检查间隔（秒）
    timeout: int = 10  # 请求超时（秒）
    max_failures: int = 3  # 最大失败次数
    alert_threshold: float = 2.0  # 响应时间告警阈值（秒）
    auto_reconnect: bool = True  # 是否自动重连

class TunnelHealthMonitor:
    """SSH隧道健康监控器"""
    
    def __init__(self, ssh_manager: SSHConnectionManager, config: MonitorConfig = None):
        self.ssh_manager = ssh_manager
        self.config = config or MonitorConfig()
        self.is_monitoring = False
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.failure_counts: Dict[str, int] = {}
        self.alert_callbacks: List[Callable] = []
        
        # 服务健康检查端点
        self.health_endpoints = {
            "rag_service": "http://localhost:8000/health",
            "model_inference": "http://localhost:8001/health"
        }
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    async def check_service_health(self, service_key: str) -> HealthCheckResult:
        """检查单个服务的健康状态"""
        service_name = self.ssh_manager.tunnels[service_key].service_name
        endpoint = self.health_endpoints.get(service_key)
        
        if not endpoint:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time=0,
                error_message="未配置健康检查端点"
            )
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                async with session.get(endpoint) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        # 检查响应时间
                        if response_time > self.config.alert_threshold:
                            status = HealthStatus.DEGRADED
                            error_message = f"响应时间过长: {response_time:.2f}s"
                        else:
                            status = HealthStatus.HEALTHY
                            error_message = None
                    else:
                        status = HealthStatus.UNHEALTHY
                        error_message = f"HTTP状态码: {response.status}"
                    
                    return HealthCheckResult(
                        service_name=service_name,
                        status=status,
                        response_time=response_time,
                        error_message=error_message
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error_message="请求超时"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """检查所有服务的健康状态"""
        results = {}
        
        # 并发检查所有服务
        tasks = []
        for service_key in self.ssh_manager.tunnels.keys():
            task = self.check_service_health(service_key)
            tasks.append((service_key, task))
        
        # 等待所有检查完成
        for service_key, task in tasks:
            try:
                result = await task
                results[service_key] = result
                
                # 记录历史
                if service_key not in self.health_history:
                    self.health_history[service_key] = []
                
                self.health_history[service_key].append(result)
                
                # 保持历史记录在合理范围内（最近100条）
                if len(self.health_history[service_key]) > 100:
                    self.health_history[service_key] = self.health_history[service_key][-100:]
                
                # 更新失败计数
                if result.status == HealthStatus.UNHEALTHY:
                    self.failure_counts[service_key] = self.failure_counts.get(service_key, 0) + 1
                else:
                    self.failure_counts[service_key] = 0
                
                # 检查是否需要告警
                await self._check_alert_conditions(service_key, result)
                
            except Exception as e:
                logger.error(f"检查服务健康状态时发生错误 {service_key}: {e}")
        
        return results
    
    async def _check_alert_conditions(self, service_key: str, result: HealthCheckResult):
        """检查告警条件"""
        failure_count = self.failure_counts.get(service_key, 0)
        
        # 连续失败告警
        if failure_count >= self.config.max_failures:
            await self._trigger_alert(
                "SERVICE_DOWN",
                f"服务 {result.service_name} 连续失败 {failure_count} 次",
                service_key,
                result
            )
            
            # 尝试自动重连
            if self.config.auto_reconnect:
                await self._attempt_reconnect(service_key)
        
        # 响应时间告警
        elif result.status == HealthStatus.DEGRADED:
            await self._trigger_alert(
                "SLOW_RESPONSE",
                f"服务 {result.service_name} 响应时间过长: {result.response_time:.2f}s",
                service_key,
                result
            )
    
    async def _trigger_alert(self, alert_type: str, message: str, service_key: str, result: HealthCheckResult):
        """触发告警"""
        alert_data = {
            "type": alert_type,
            "message": message,
            "service_key": service_key,
            "service_name": result.service_name,
            "timestamp": result.timestamp.isoformat(),
            "details": asdict(result)
        }
        
        logger.warning(f"告警触发: {message}")
        
        # 调用所有告警回调
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")
    
    async def _attempt_reconnect(self, service_key: str):
        """尝试重连服务"""
        logger.info(f"尝试自动重连服务: {service_key}")
        
        try:
            success = await self.ssh_manager.auto_reconnect(service_key)
            if success:
                logger.info(f"服务重连成功: {service_key}")
                # 重置失败计数
                self.failure_counts[service_key] = 0
                
                await self._trigger_alert(
                    "SERVICE_RECOVERED",
                    f"服务 {self.ssh_manager.tunnels[service_key].service_name} 重连成功",
                    service_key,
                    None
                )
            else:
                logger.error(f"服务重连失败: {service_key}")
                
        except Exception as e:
            logger.error(f"自动重连时发生错误: {e}")
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("监控已在运行中")
            return
        
        self.is_monitoring = True
        logger.info(f"开始SSH隧道健康监控，检查间隔: {self.config.check_interval}秒")
        
        while self.is_monitoring:
            try:
                # 执行健康检查
                results = await self.check_all_services()
                
                # 记录检查结果
                healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
                total_count = len(results)
                
                logger.info(f"健康检查完成: {healthy_count}/{total_count} 服务正常")
                
                # 等待下次检查
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环中发生错误: {e}")
                await asyncio.sleep(self.config.check_interval)
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        logger.info("SSH隧道健康监控已停止")
    
    def get_health_summary(self) -> Dict:
        """获取健康状态摘要"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "overall_status": "unknown"
        }
        
        healthy_count = 0
        total_count = 0
        
        for service_key, tunnel in self.ssh_manager.tunnels.items():
            history = self.health_history.get(service_key, [])
            latest_result = history[-1] if history else None
            
            service_summary = {
                "service_name": tunnel.service_name,
                "current_status": latest_result.status.value if latest_result else "unknown",
                "last_check": latest_result.timestamp.isoformat() if latest_result else None,
                "failure_count": self.failure_counts.get(service_key, 0),
                "avg_response_time": self._calculate_avg_response_time(service_key)
            }
            
            summary["services"][service_key] = service_summary
            
            if latest_result and latest_result.status == HealthStatus.HEALTHY:
                healthy_count += 1
            total_count += 1
        
        # 计算整体状态
        if total_count == 0:
            summary["overall_status"] = "unknown"
        elif healthy_count == total_count:
            summary["overall_status"] = "healthy"
        elif healthy_count > 0:
            summary["overall_status"] = "degraded"
        else:
            summary["overall_status"] = "unhealthy"
        
        summary["healthy_services"] = healthy_count
        summary["total_services"] = total_count
        
        return summary
    
    def _calculate_avg_response_time(self, service_key: str) -> float:
        """计算平均响应时间"""
        history = self.health_history.get(service_key, [])
        if not history:
            return 0.0
        
        # 计算最近10次检查的平均响应时间
        recent_results = history[-10:]
        total_time = sum(r.response_time for r in recent_results)
        return total_time / len(recent_results)

# 告警回调示例
async def console_alert_callback(alert_data: Dict):
    """控制台告警回调"""
    print(f"🚨 告警: {alert_data['message']}")
    print(f"   时间: {alert_data['timestamp']}")
    print(f"   服务: {alert_data['service_name']}")

async def log_alert_callback(alert_data: Dict):
    """日志告警回调"""
    logger.warning(f"告警: {alert_data['type']} - {alert_data['message']}")

# 使用示例
async def main():
    """主函数示例"""
    from ssh_connection_manager import SSHConnectionManager
    
    # 创建SSH管理器和健康监控器
    ssh_manager = SSHConnectionManager()
    monitor = TunnelHealthMonitor(ssh_manager)
    
    # 添加告警回调
    monitor.add_alert_callback(console_alert_callback)
    monitor.add_alert_callback(log_alert_callback)
    
    # 测试连接并创建隧道
    success, message = await ssh_manager.test_connection()
    if success:
        await ssh_manager.create_tunnel("rag_service")
        await ssh_manager.create_tunnel("model_inference")
    
    # 执行一次健康检查
    results = await monitor.check_all_services()
    print("健康检查结果:")
    for service_key, result in results.items():
        print(f"  {result.service_name}: {result.status.value} "
              f"({result.response_time:.2f}s)")
    
    # 获取健康摘要
    summary = monitor.get_health_summary()
    print("\n健康状态摘要:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 清理
    ssh_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
