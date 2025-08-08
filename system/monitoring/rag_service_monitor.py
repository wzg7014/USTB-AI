#!/usr/bin/env python3
"""
RAG服务性能监控工具
实时监控AutoDL RAG服务的性能指标和健康状态

创建时间: 2025-08-06 02:35
创建者: 系统集成专家
状态: 模型重训期间完善监控体系
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    response_time: float
    gpu_memory_used: float
    gpu_memory_total: float
    service_uptime: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class HealthStatus:
    """健康状态数据类"""
    timestamp: float
    status: str
    gpu_available: bool
    service_responsive: bool
    average_response_time: float
    error_rate: float

class RAGServiceMonitor:
    """RAG服务监控器"""
    
    def __init__(self, service_url: str = "http://localhost:8000"):
        self.service_url = service_url
        self.metrics_history: List[PerformanceMetrics] = []
        self.health_history: List[HealthStatus] = []
        self.monitoring_active = False
        
        # 监控配置
        self.config = {
            "check_interval": 30,  # 30秒检查一次
            "performance_test_interval": 300,  # 5分钟性能测试一次
            "max_history_size": 1000,  # 最大历史记录数
            "alert_thresholds": {
                "response_time": 1.0,  # 响应时间超过1秒告警
                "error_rate": 0.1,     # 错误率超过10%告警
                "gpu_memory_usage": 0.9  # GPU显存使用率超过90%告警
            }
        }
        
        # 测试查询
        self.test_queries = [
            "如何选课",
            "成绩查询",
            "考试安排",
            "学分要求"
        ]
    
    async def check_health(self) -> HealthStatus:
        """检查服务健康状态"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.service_url}/health",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # 计算平均响应时间
                        recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
                        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics) if recent_metrics else response_time
                        
                        # 计算错误率
                        recent_success = [m.success for m in recent_metrics]
                        error_rate = 1 - (sum(recent_success) / len(recent_success)) if recent_success else 0
                        
                        return HealthStatus(
                            timestamp=time.time(),
                            status=data.get("status", "unknown"),
                            gpu_available=data.get("gpu_available", False),
                            service_responsive=True,
                            average_response_time=avg_response_time,
                            error_rate=error_rate
                        )
                    else:
                        return HealthStatus(
                            timestamp=time.time(),
                            status="unhealthy",
                            gpu_available=False,
                            service_responsive=False,
                            average_response_time=response_time,
                            error_rate=1.0
                        )
                        
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return HealthStatus(
                timestamp=time.time(),
                status="error",
                gpu_available=False,
                service_responsive=False,
                average_response_time=0,
                error_rate=1.0
            )
    
    async def performance_test(self) -> PerformanceMetrics:
        """执行性能测试"""
        test_query = self.test_queries[int(time.time()) % len(self.test_queries)]
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": test_query,
                    "top_k": 3,
                    "include_attachments": True
                }
                
                async with session.post(
                    f"{self.service_url}/api/v1/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # 获取GPU信息
                        health_data = await self._get_health_data()
                        
                        return PerformanceMetrics(
                            timestamp=time.time(),
                            response_time=response_time,
                            gpu_memory_used=health_data.get("gpu_memory_used", 0),
                            gpu_memory_total=health_data.get("gpu_memory_total", 0),
                            service_uptime=health_data.get("service_uptime", 0),
                            success=True
                        )
                    else:
                        return PerformanceMetrics(
                            timestamp=time.time(),
                            response_time=response_time,
                            gpu_memory_used=0,
                            gpu_memory_total=0,
                            service_uptime=0,
                            success=False,
                            error_message=f"HTTP {response.status}"
                        )
                        
        except Exception as e:
            return PerformanceMetrics(
                timestamp=time.time(),
                response_time=0,
                gpu_memory_used=0,
                gpu_memory_total=0,
                service_uptime=0,
                success=False,
                error_message=str(e)
            )
    
    async def _get_health_data(self) -> Dict:
        """获取健康数据"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.service_url}/health") as response:
                    if response.status == 200:
                        return await response.json()
        except:
            pass
        return {}
    
    def check_alerts(self, metrics: PerformanceMetrics, health: HealthStatus) -> List[str]:
        """检查告警条件"""
        alerts = []
        
        # 响应时间告警
        if metrics.success and metrics.response_time > self.config["alert_thresholds"]["response_time"]:
            alerts.append(f"响应时间过长: {metrics.response_time:.2f}s")
        
        # 错误率告警
        if health.error_rate > self.config["alert_thresholds"]["error_rate"]:
            alerts.append(f"错误率过高: {health.error_rate:.1%}")
        
        # GPU显存告警
        if metrics.gpu_memory_total > 0:
            gpu_usage_rate = metrics.gpu_memory_used / metrics.gpu_memory_total
            if gpu_usage_rate > self.config["alert_thresholds"]["gpu_memory_usage"]:
                alerts.append(f"GPU显存使用率过高: {gpu_usage_rate:.1%}")
        
        # 服务不响应告警
        if not health.service_responsive:
            alerts.append("服务无响应")
        
        return alerts
    
    def generate_report(self) -> Dict:
        """生成监控报告"""
        if not self.metrics_history or not self.health_history:
            return {"error": "暂无监控数据"}
        
        # 最近的指标
        latest_metrics = self.metrics_history[-1]
        latest_health = self.health_history[-1]
        
        # 统计信息
        recent_metrics = self.metrics_history[-10:]
        successful_metrics = [m for m in recent_metrics if m.success]
        
        avg_response_time = sum(m.response_time for m in successful_metrics) / len(successful_metrics) if successful_metrics else 0
        success_rate = len(successful_metrics) / len(recent_metrics) if recent_metrics else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "service_status": latest_health.status,
            "current_metrics": {
                "response_time": f"{latest_metrics.response_time:.3f}s",
                "gpu_memory_used": f"{latest_metrics.gpu_memory_used:.2f}GB",
                "gpu_memory_total": f"{latest_metrics.gpu_memory_total:.2f}GB",
                "service_uptime": f"{latest_metrics.service_uptime:.0f}s"
            },
            "performance_summary": {
                "average_response_time": f"{avg_response_time:.3f}s",
                "success_rate": f"{success_rate:.1%}",
                "error_rate": f"{latest_health.error_rate:.1%}",
                "gpu_available": latest_health.gpu_available
            },
            "alerts": self.check_alerts(latest_metrics, latest_health),
            "monitoring_duration": f"{time.time() - self.metrics_history[0].timestamp:.0f}s" if self.metrics_history else "0s"
        }
    
    async def start_monitoring(self, duration: Optional[int] = None):
        """开始监控"""
        self.monitoring_active = True
        start_time = time.time()
        
        logger.info(f"开始监控RAG服务: {self.service_url}")
        
        try:
            while self.monitoring_active:
                # 健康检查
                health = await self.check_health()
                self.health_history.append(health)
                
                # 性能测试
                metrics = await self.performance_test()
                self.metrics_history.append(metrics)
                
                # 限制历史记录大小
                if len(self.metrics_history) > self.config["max_history_size"]:
                    self.metrics_history = self.metrics_history[-self.config["max_history_size"]:]
                if len(self.health_history) > self.config["max_history_size"]:
                    self.health_history = self.health_history[-self.config["max_history_size"]:]
                
                # 检查告警
                alerts = self.check_alerts(metrics, health)
                if alerts:
                    logger.warning(f"监控告警: {', '.join(alerts)}")
                
                # 输出状态
                status = "✅" if metrics.success else "❌"
                logger.info(f"{status} 响应时间: {metrics.response_time:.3f}s, GPU: {health.gpu_available}")
                
                # 检查是否达到监控时长
                if duration and (time.time() - start_time) >= duration:
                    break
                
                # 等待下次检查
                await asyncio.sleep(self.config["check_interval"])
                
        except KeyboardInterrupt:
            logger.info("监控被用户中断")
        finally:
            self.monitoring_active = False
            logger.info("监控已停止")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
    
    def save_report(self, filename: str = None):
        """保存监控报告"""
        if not filename:
            filename = f"rag_monitor_report_{int(time.time())}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"监控报告已保存: {filename}")
        return filename

# 使用示例
async def main():
    """主函数"""
    monitor = RAGServiceMonitor()
    
    print("🚀 开始RAG服务监控...")
    print("按 Ctrl+C 停止监控")
    
    try:
        # 监控5分钟
        await monitor.start_monitoring(duration=300)
    finally:
        # 生成并保存报告
        report = monitor.generate_report()
        print("\n📊 监控报告:")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
        monitor.save_report("system/monitoring/rag_monitor_report.json")

if __name__ == "__main__":
    asyncio.run(main())
