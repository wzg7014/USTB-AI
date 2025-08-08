"""
USTB RAG系统性能测试脚本
测试Recall@5和响应时间性能指标
"""
import asyncio
import json
import time
import statistics
from typing import List, Dict, Any
from pathlib import Path
import requests
import concurrent.futures

from loguru import logger

class RAGPerformanceTester:
    """RAG系统性能测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_queries_file = self.project_root / "data" / "processed" / "rag_data.json"
        self.results = {}
        
    def load_test_queries(self, sample_size: int = 100) -> List[Dict[str, Any]]:
        """加载测试查询"""
        try:
            with open(self.test_queries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 从文档中提取测试查询
            test_queries = []
            for i, doc in enumerate(data[:sample_size]):
                # 基于文档标题和内容生成测试查询
                queries = [
                    doc['title'][:50],  # 标题前50字符
                    doc['category'],    # 分类名称
                    ' '.join(doc['content'].split()[:10])  # 内容前10个词
                ]
                
                for query in queries:
                    if len(query.strip()) > 5:  # 过滤太短的查询
                        test_queries.append({
                            'query': query.strip(),
                            'expected_doc_id': doc['id'],
                            'category': doc['category']
                        })
            
            logger.info(f"生成了 {len(test_queries)} 个测试查询")
            return test_queries[:200]  # 限制测试数量
            
        except Exception as e:
            logger.error(f"加载测试查询失败: {str(e)}")
            return []
    
    def test_single_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个查询"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/v1/search",
                json={
                    "query": query_data['query'],
                    "top_k": 5
                },
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查是否找到预期文档
                found_expected = any(
                    r['id'] == query_data['expected_doc_id'] 
                    for r in result['results']
                )
                
                return {
                    'query': query_data['query'],
                    'response_time': response_time,
                    'found_expected': found_expected,
                    'result_count': len(result['results']),
                    'success': True
                }
            else:
                return {
                    'query': query_data['query'],
                    'response_time': response_time,
                    'found_expected': False,
                    'result_count': 0,
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'query': query_data['query'],
                'response_time': 10.0,  # 超时
                'found_expected': False,
                'result_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def test_recall_at_5(self, test_queries: List[Dict[str, Any]]) -> Dict[str, float]:
        """测试Recall@5性能"""
        logger.info("开始Recall@5测试...")
        
        results = []
        for query_data in test_queries:
            result = self.test_single_query(query_data)
            results.append(result)
        
        # 计算Recall@5
        successful_queries = [r for r in results if r['success']]
        if not successful_queries:
            return {'recall_at_5': 0.0, 'total_queries': len(test_queries)}
        
        found_count = sum(1 for r in successful_queries if r['found_expected'])
        recall_at_5 = found_count / len(successful_queries)
        
        logger.info(f"Recall@5测试完成: {recall_at_5:.3f}")
        
        return {
            'recall_at_5': recall_at_5,
            'total_queries': len(test_queries),
            'successful_queries': len(successful_queries),
            'found_count': found_count
        }
    
    def test_response_time(self, test_queries: List[Dict[str, Any]]) -> Dict[str, float]:
        """测试响应时间性能"""
        logger.info("开始响应时间测试...")
        
        response_times = []
        for query_data in test_queries[:50]:  # 限制测试数量
            result = self.test_single_query(query_data)
            if result['success']:
                response_times.append(result['response_time'])
        
        if not response_times:
            return {'avg_response_time': 0.0, 'max_response_time': 0.0}
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        logger.info(f"响应时间测试完成: 平均{avg_time:.3f}秒")
        
        return {
            'avg_response_time': avg_time,
            'max_response_time': max_time,
            'min_response_time': min_time,
            'p95_response_time': p95_time,
            'total_tests': len(response_times)
        }
    
    def test_concurrent_performance(self, concurrent_users: int = 10) -> Dict[str, Any]:
        """测试并发性能"""
        logger.info(f"开始并发性能测试: {concurrent_users}个并发用户")
        
        test_query = "选课通知"
        
        def single_request():
            return self.test_single_query({'query': test_query, 'expected_doc_id': 'test'})
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(single_request) for _ in range(concurrent_users * 5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        successful_requests = [r for r in results if r['success']]
        
        if successful_requests:
            avg_response_time = statistics.mean([r['response_time'] for r in successful_requests])
            throughput = len(successful_requests) / total_time
        else:
            avg_response_time = 0.0
            throughput = 0.0
        
        logger.info(f"并发测试完成: 吞吐量{throughput:.2f}请求/秒")
        
        return {
            'concurrent_users': concurrent_users,
            'total_requests': len(results),
            'successful_requests': len(successful_requests),
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'total_time': total_time
        }
    
    def run_full_performance_test(self) -> Dict[str, Any]:
        """运行完整性能测试"""
        logger.info("开始RAG系统完整性能测试")
        
        # 检查服务是否可用
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                raise Exception("RAG服务不可用")
        except Exception as e:
            logger.error(f"RAG服务连接失败: {str(e)}")
            return {'error': 'RAG服务不可用'}
        
        # 加载测试数据
        test_queries = self.load_test_queries()
        if not test_queries:
            return {'error': '无法加载测试查询'}
        
        # 执行各项测试
        results = {
            'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service_url': self.base_url,
            'test_queries_count': len(test_queries)
        }
        
        # Recall@5测试
        results['recall_test'] = self.test_recall_at_5(test_queries)
        
        # 响应时间测试
        results['response_time_test'] = self.test_response_time(test_queries)
        
        # 并发性能测试
        results['concurrent_test'] = self.test_concurrent_performance()
        
        # 性能评估
        results['performance_evaluation'] = self._evaluate_performance(results)
        
        logger.info("RAG系统性能测试完成")
        return results
    
    def _evaluate_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """评估性能指标"""
        evaluation = {}
        
        # Recall@5评估
        recall = results['recall_test']['recall_at_5']
        evaluation['recall_at_5_pass'] = recall >= 0.8
        evaluation['recall_at_5_score'] = recall
        
        # 响应时间评估
        avg_time = results['response_time_test']['avg_response_time']
        evaluation['response_time_pass'] = avg_time <= 0.5
        evaluation['response_time_score'] = avg_time
        
        # 并发性能评估
        throughput = results['concurrent_test']['throughput']
        evaluation['throughput_pass'] = throughput >= 10  # 至少10请求/秒
        evaluation['throughput_score'] = throughput
        
        # 总体评估
        all_pass = (
            evaluation['recall_at_5_pass'] and 
            evaluation['response_time_pass'] and 
            evaluation['throughput_pass']
        )
        evaluation['overall_pass'] = all_pass
        
        return evaluation

def main():
    """主函数"""
    tester = RAGPerformanceTester()
    results = tester.run_full_performance_test()
    
    # 保存测试结果
    output_file = Path(__file__).parent.parent.parent.parent / "reports" / "rag_performance_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 打印关键指标
    if 'error' not in results:
        print("\n" + "="*50)
        print("RAG系统性能测试结果")
        print("="*50)
        print(f"Recall@5: {results['recall_test']['recall_at_5']:.3f} ({'✅ PASS' if results['performance_evaluation']['recall_at_5_pass'] else '❌ FAIL'})")
        print(f"平均响应时间: {results['response_time_test']['avg_response_time']:.3f}秒 ({'✅ PASS' if results['performance_evaluation']['response_time_pass'] else '❌ FAIL'})")
        print(f"并发吞吐量: {results['concurrent_test']['throughput']:.2f}请求/秒 ({'✅ PASS' if results['performance_evaluation']['throughput_pass'] else '❌ FAIL'})")
        print(f"总体评估: {'✅ 所有指标通过' if results['performance_evaluation']['overall_pass'] else '❌ 部分指标未达标'}")
        print("="*50)

if __name__ == "__main__":
    main()
