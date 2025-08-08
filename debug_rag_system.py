#!/usr/bin/env python3
"""
RAG系统深度调试脚本
系统性测试RAG系统的各个组件，找出搜索返回0结果的根本原因
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class RAGSystemDebugger:
    """RAG系统调试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8004"
        self.test_queries = [
            "如何查询成绩",
            "选课系统怎么使用",
            "毕业论文要求",
            "grade query",
            "course selection"
        ]
    
    def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查"""
        print("🏥 测试健康检查...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
            
            if result["success"]:
                print(f"✅ 健康检查通过 ({result['response_time']:.3f}s)")
                print(f"📊 GPU可用: {result['data'].get('gpu_available', 'N/A')}")
                print(f"📊 运行时间: {result['data'].get('service_uptime', 'N/A'):.1f}s")
            else:
                print(f"❌ 健康检查失败: {result['status_code']}")
                
            return result
            
        except Exception as e:
            print(f"❌ 健康检查异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_search_api_detailed(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """详细测试搜索API"""
        print(f"\n🔍 详细测试搜索API: '{query}'")
        
        try:
            # 准备请求数据
            request_data = {
                "query": query,
                "top_k": top_k,
                "include_metadata": True,
                "include_attachments": True
            }
            
            print(f"📝 请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            
            # 发送请求
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/v1/search",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = time.time() - start_time
            
            print(f"📊 响应状态码: {response.status_code}")
            print(f"⏱️ 响应时间: {response_time:.3f}s")
            print(f"📏 响应大小: {len(response.content)} bytes")
            
            # 分析响应
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response_time,
                "query": query,
                "request_data": request_data
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["data"] = data
                    
                    print(f"✅ 搜索请求成功")
                    print(f"📋 响应结构:")
                    for key, value in data.items():
                        if key == "documents":
                            print(f"   - {key}: {len(value) if isinstance(value, list) else type(value).__name__}")
                            if isinstance(value, list) and len(value) > 0:
                                print(f"     第一个文档: {value[0].get('title', 'N/A')[:50]}...")
                        elif key == "attachments":
                            print(f"   - {key}: {len(value) if isinstance(value, list) else type(value).__name__}")
                        else:
                            print(f"   - {key}: {str(value)[:100]}...")
                    
                    # 关键指标
                    documents = data.get("documents", [])
                    attachments = data.get("attachments", [])
                    
                    print(f"\n📊 关键指标:")
                    print(f"   - 文档数量: {len(documents)}")
                    print(f"   - 附件数量: {len(attachments)}")
                    print(f"   - 相关度分数: {data.get('relevance_score', 'N/A')}")
                    print(f"   - GPU加速: {data.get('gpu_accelerated', 'N/A')}")
                    
                    if len(documents) == 0:
                        print("⚠️ 警告: 搜索返回0个文档!")
                        print("🔍 可能的原因:")
                        print("   1. 向量搜索逻辑有问题")
                        print("   2. 查询向量生成失败")
                        print("   3. 向量数据库连接问题")
                        print("   4. 异常被捕获但未正确处理")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {str(e)}")
                    print(f"📄 原始响应: {response.text[:500]}...")
                    result["error"] = f"JSON解析失败: {str(e)}"
                    result["raw_response"] = response.text
                    
            else:
                print(f"❌ 搜索请求失败: {response.status_code}")
                print(f"📄 错误响应: {response.text}")
                result["error"] = response.text
            
            return result
            
        except requests.exceptions.Timeout:
            print(f"⏰ 请求超时")
            return {"success": False, "error": "请求超时"}
        except requests.exceptions.ConnectionError:
            print(f"🔌 连接错误")
            return {"success": False, "error": "连接错误"}
        except Exception as e:
            print(f"❌ 搜索测试异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_different_parameters(self) -> Dict[str, Any]:
        """测试不同的参数组合"""
        print("\n🧪 测试不同参数组合...")
        
        test_cases = [
            {"query": "成绩查询", "top_k": 1, "include_metadata": False, "include_attachments": False},
            {"query": "成绩查询", "top_k": 3, "include_metadata": True, "include_attachments": False},
            {"query": "成绩查询", "top_k": 5, "include_metadata": True, "include_attachments": True},
            {"query": "grade", "top_k": 3, "include_metadata": True, "include_attachments": True},
        ]
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                response = requests.post(
                    f"{self.base_url}/api/v1/search",
                    json=test_case,
                    timeout=15
                )
                
                result = {
                    "test_case": test_case,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    data = response.json()
                    result["document_count"] = len(data.get("documents", []))
                    result["attachment_count"] = len(data.get("attachments", []))
                    print(f"✅ 成功 - 文档: {result['document_count']}, 附件: {result['attachment_count']}")
                else:
                    result["error"] = response.text
                    print(f"❌ 失败 - {response.status_code}")
                
                results.append(result)
                
            except Exception as e:
                print(f"❌ 测试用例 {i} 异常: {str(e)}")
                results.append({"test_case": test_case, "success": False, "error": str(e)})
        
        return {"test_results": results}
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """测试所有API端点"""
        print("\n🌐 测试所有API端点...")
        
        endpoints = [
            {"path": "/", "method": "GET"},
            {"path": "/health", "method": "GET"},
            {"path": "/api/v1/search", "method": "POST", "data": {"query": "test", "top_k": 1}},
            {"path": "/docs", "method": "GET"},
            {"path": "/openapi.json", "method": "GET"},
        ]
        
        results = []
        for endpoint in endpoints:
            print(f"🔗 测试 {endpoint['method']} {endpoint['path']}")
            try:
                if endpoint["method"] == "GET":
                    response = requests.get(f"{self.base_url}{endpoint['path']}", timeout=10)
                else:
                    response = requests.post(
                        f"{self.base_url}{endpoint['path']}", 
                        json=endpoint.get("data", {}),
                        timeout=10
                    )
                
                result = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 404],  # 404也算正常，说明服务在运行
                    "response_size": len(response.content)
                }
                
                print(f"   状态码: {response.status_code}, 大小: {result['response_size']} bytes")
                results.append(result)
                
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                results.append({"endpoint": endpoint, "success": False, "error": str(e)})
        
        return {"endpoint_results": results}
    
    def run_comprehensive_debug(self) -> Dict[str, Any]:
        """运行综合调试"""
        print("🚀 开始RAG系统综合调试")
        print("=" * 80)
        
        debug_results = {
            "timestamp": time.time(),
            "test_summary": {}
        }
        
        # 1. 健康检查
        health_result = self.test_health_check()
        debug_results["health_check"] = health_result
        debug_results["test_summary"]["health_check"] = health_result.get("success", False)
        
        if not health_result.get("success", False):
            print("\n❌ 健康检查失败，停止后续测试")
            return debug_results
        
        # 2. API端点测试
        endpoint_results = self.test_api_endpoints()
        debug_results["api_endpoints"] = endpoint_results
        
        # 3. 详细搜索测试
        search_results = []
        for query in self.test_queries:
            result = self.test_search_api_detailed(query)
            search_results.append(result)
        
        debug_results["search_tests"] = search_results
        debug_results["test_summary"]["search_success_rate"] = sum(1 for r in search_results if r.get("success", False)) / len(search_results)
        
        # 4. 参数组合测试
        param_results = self.test_different_parameters()
        debug_results["parameter_tests"] = param_results
        
        # 5. 生成总结报告
        self.generate_debug_report(debug_results)
        
        return debug_results
    
    def generate_debug_report(self, results: Dict[str, Any]):
        """生成调试报告"""
        print("\n" + "=" * 80)
        print("📊 RAG系统调试报告")
        print("=" * 80)
        
        # 健康状态
        health_ok = results.get("health_check", {}).get("success", False)
        print(f"🏥 服务健康状态: {'✅ 正常' if health_ok else '❌ 异常'}")
        
        # 搜索测试结果
        search_tests = results.get("search_tests", [])
        successful_searches = sum(1 for test in search_tests if test.get("success", False))
        searches_with_results = sum(1 for test in search_tests if test.get("success", False) and len(test.get("data", {}).get("documents", [])) > 0)
        
        print(f"🔍 搜索测试: {successful_searches}/{len(search_tests)} 成功")
        print(f"📋 有结果的搜索: {searches_with_results}/{len(search_tests)}")
        
        if searches_with_results == 0 and successful_searches > 0:
            print("\n⚠️ 关键问题: 搜索API正常响应但返回0个文档")
            print("🔧 建议的解决方案:")
            print("   1. 检查向量搜索逻辑是否正确执行")
            print("   2. 验证嵌入模型是否正确加载")
            print("   3. 确认向量数据库连接状态")
            print("   4. 检查异常处理是否掩盖了错误")
            print("   5. 添加详细的日志输出进行调试")
        
        # 保存详细结果
        timestamp = int(time.time())
        report_file = f"rag_debug_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n📄 详细报告已保存: {report_file}")
        except Exception as e:
            print(f"\n❌ 保存报告失败: {str(e)}")

def main():
    """主函数"""
    debugger = RAGSystemDebugger()
    
    try:
        results = debugger.run_comprehensive_debug()
        
        # 基于结果给出具体建议
        if results.get("test_summary", {}).get("search_success_rate", 0) == 1.0:
            # 搜索成功但无结果
            print("\n🎯 下一步行动建议:")
            print("1. 直接在AutoDL上添加调试输出到RAG服务代码")
            print("2. 检查向量搜索的具体执行过程")
            print("3. 验证query_points方法的返回值格式")
            print("4. 确认异常处理逻辑是否正确")
        
    except KeyboardInterrupt:
        print("\n🛑 调试中断")
    except Exception as e:
        print(f"\n❌ 调试过程异常: {str(e)}")

if __name__ == "__main__":
    main()
