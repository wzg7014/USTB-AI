#!/usr/bin/env python3
"""
系统集成测试 - 验证所有服务的连接和功能
测试RAG系统、模型推理服务和混合API服务的集成状态
"""

import json
import time
import logging
import requests
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemIntegrationTest:
    """系统集成测试器"""
    
    def __init__(self):
        # 服务配置 - 使用SSH隧道端口
        self.services = {
            'rag': {
                'name': 'RAG系统',
                'url': 'http://localhost:8004',
                'health_endpoint': '/health',
                'test_endpoint': '/api/v1/search'
            },
            'model': {
                'name': '模型推理服务',
                'url': 'http://localhost:8003',
                'health_endpoint': '/health',
                'test_endpoint': '/api/v1/inference'
            },
            'hybrid_api': {
                'name': '混合API服务',
                'url': 'http://localhost:8005',
                'health_endpoint': '/health',
                'test_endpoint': '/api/v1/hybrid_inference'
            }
        }
        
        # 测试用例
        self.test_cases = [
            {
                'query': '如何查询成绩？',
                'expected_keywords': ['成绩', '查询', '教务']
            },
            {
                'query': '选课系统怎么使用？',
                'expected_keywords': ['选课', '系统', '使用']
            },
            {
                'query': '毕业论文有什么要求？',
                'expected_keywords': ['毕业', '论文', '要求']
            }
        ]
    
    def test_service_health(self, service_name: str) -> Dict:
        """测试服务健康状态"""
        service = self.services[service_name]
        
        try:
            start_time = time.time()
            response = requests.get(
                f"{service['url']}{service['health_endpoint']}",
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'response_time': response_time,
                    'data': data,
                    'status': '🟢 健康'
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'status': '🔴 异常'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': '🔴 连接失败'
            }
    
    def test_rag_service(self, query: str) -> Dict:
        """测试RAG服务"""
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.services['rag']['url']}/api/v1/search",
                json={
                    "query": query,
                    "top_k": 3,
                    "include_metadata": True
                },
                timeout=15
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                # 兼容新RAG服务v2.0的响应格式（documents字段）
                results_count = len(data.get('documents', data.get('results', [])))

                return {
                    'success': True,
                    'response_time': response_time,
                    'results_count': results_count,
                    'data': data,
                    'status': f'✅ 返回{results_count}个结果'
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'status': '❌ 查询失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': '❌ 连接异常'
            }
    
    def test_model_service(self, query: str) -> Dict:
        """测试模型推理服务"""
        try:
            start_time = time.time()
            prompt = f"我是USTB的学生，请问{query}"
            
            response = requests.post(
                f"{self.services['model']['url']}/api/v1/inference",
                json={
                    "query": prompt,
                    "max_tokens": 200,
                    "temperature": 0.1
                },
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                return {
                    'success': True,
                    'response_time': response_time,
                    'response_length': len(response_text),
                    'data': data,
                    'status': f'✅ 生成{len(response_text)}字符回答'
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'status': '❌ 推理失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': '❌ 连接异常'
            }
    
    def test_hybrid_api_service(self, query: str, strategy: str = 'parallel_merge') -> Dict:
        """测试混合API服务"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.services['hybrid_api']['url']}/api/v1/hybrid_inference",
                json={
                    "query": query,
                    "strategy": strategy,
                    "max_tokens": 300,
                    "temperature": 0.1
                },
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                return {
                    'success': True,
                    'response_time': response_time,
                    'response_length': len(response_text),
                    'strategy': strategy,
                    'data': data,
                    'status': f'✅ 混合回答({len(response_text)}字符)'
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'status': '❌ 混合API失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': '❌ 连接异常'
            }
    
    def run_comprehensive_test(self) -> Dict:
        """运行综合测试"""
        print("\n" + "="*80)
        print("🚀 USTB混合云架构系统集成测试")
        print("="*80)
        
        results = {
            'health_checks': {},
            'functional_tests': {},
            'performance_metrics': {},
            'overall_status': 'unknown'
        }
        
        # 1. 健康检查
        print("\n📊 1. 服务健康检查")
        print("-" * 50)
        
        healthy_services = 0
        for service_name, service_config in self.services.items():
            health_result = self.test_service_health(service_name)
            results['health_checks'][service_name] = health_result
            
            print(f"{health_result['status']} {service_config['name']}")
            print(f"   响应时间: {health_result.get('response_time', 0):.3f}s")
            
            if health_result['success']:
                healthy_services += 1
                if 'data' in health_result:
                    # 显示关键健康信息
                    data = health_result['data']
                    if service_name == 'rag' and 'document_count' in data:
                        print(f"   文档数量: {data['document_count']}")
                    elif service_name == 'model' and 'gpu_memory_used' in data:
                        print(f"   GPU内存: {data['gpu_memory_used']:.1f}GB")
            else:
                print(f"   错误: {health_result.get('error', '未知错误')}")
            print()
        
        # 2. 功能测试
        print("🔧 2. 功能测试")
        print("-" * 50)
        
        for i, test_case in enumerate(self.test_cases, 1):
            query = test_case['query']
            print(f"\n测试用例 {i}: {query}")
            print("." * 40)
            
            test_results = {}
            
            # 测试RAG服务
            if results['health_checks']['rag']['success']:
                rag_result = self.test_rag_service(query)
                test_results['rag'] = rag_result
                print(f"RAG系统: {rag_result['status']} ({rag_result.get('response_time', 0):.2f}s)")
            
            # 测试模型推理服务
            if results['health_checks']['model']['success']:
                model_result = self.test_model_service(query)
                test_results['model'] = model_result
                print(f"模型推理: {model_result['status']} ({model_result.get('response_time', 0):.2f}s)")
            
            # 测试混合API服务
            if results['health_checks']['hybrid_api']['success']:
                hybrid_result = self.test_hybrid_api_service(query)
                test_results['hybrid_api'] = hybrid_result
                print(f"混合API: {hybrid_result['status']} ({hybrid_result.get('response_time', 0):.2f}s)")
            
            results['functional_tests'][f'test_case_{i}'] = test_results
        
        # 3. 性能指标统计
        print("\n📈 3. 性能指标")
        print("-" * 50)
        
        performance = {}
        for service_name in self.services.keys():
            times = []
            success_count = 0
            total_count = 0
            
            # 收集健康检查时间
            if results['health_checks'][service_name]['success']:
                times.append(results['health_checks'][service_name]['response_time'])
            
            # 收集功能测试时间
            for test_key, test_data in results['functional_tests'].items():
                if service_name in test_data:
                    total_count += 1
                    if test_data[service_name]['success']:
                        success_count += 1
                        times.append(test_data[service_name]['response_time'])
            
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                
                performance[service_name] = {
                    'avg_response_time': avg_time,
                    'max_response_time': max_time,
                    'min_response_time': min_time,
                    'success_rate': success_rate
                }
                
                print(f"{self.services[service_name]['name']}:")
                print(f"   平均响应时间: {avg_time:.3f}s")
                print(f"   最大响应时间: {max_time:.3f}s")
                print(f"   最小响应时间: {min_time:.3f}s")
                print(f"   成功率: {success_rate:.1f}%")
                print()
        
        results['performance_metrics'] = performance
        
        # 4. 总体状态评估
        total_services = len(self.services)
        if healthy_services == total_services:
            results['overall_status'] = '🟢 全部正常'
        elif healthy_services > 0:
            results['overall_status'] = f'🟡 部分正常 ({healthy_services}/{total_services})'
        else:
            results['overall_status'] = '🔴 全部异常'
        
        print("🎯 4. 总体状态")
        print("-" * 50)
        print(f"系统状态: {results['overall_status']}")
        print(f"健康服务: {healthy_services}/{total_services}")
        
        return results

def main():
    """主函数"""
    tester = SystemIntegrationTest()
    
    try:
        results = tester.run_comprehensive_test()
        
        print("\n" + "="*80)
        print("✅ 系统集成测试完成")
        print("="*80)
        
        # 保存测试结果
        timestamp = int(time.time())
        results_file = f"system/integration_test/test_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📄 测试结果已保存到: {results_file}")
        
    except Exception as e:
        print(f"❌ 测试执行出错: {str(e)}")

if __name__ == "__main__":
    main()
