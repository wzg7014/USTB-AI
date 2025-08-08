"""
USTB AI教务助手 - 并发Qwen评分器
支持多线程并发API调用，大幅提升处理速度
"""

import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_config import QWEN_CONFIG, QUALITY_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConcurrentQwenScorer:
    """并发Qwen API评分器"""
    
    def __init__(self, max_concurrent=5):
        self.api_key = QWEN_CONFIG['api_key']
        self.base_url = QWEN_CONFIG['base_url']
        self.model = QWEN_CONFIG['model']
        self.max_concurrent = max_concurrent
        self.score_weights = QUALITY_CONFIG['score_weights']
        
        # 验证API配置
        if not self.api_key:
            logger.warning("未设置API密钥")
    
    def create_scoring_prompt(self, title: str, content: str, category: str) -> str:
        """创建评分提示词"""
        prompt = f"""
请对以下USTB教务数据进行6维度质量评分，每个维度0-10分：

标题：{title}
分类：{category}
内容：{content[:1000]}...

评分维度：
1. 完整性(completeness)：信息是否完整，是否包含必要的教务信息
2. 相关性(relevance)：与USTB教务场景的匹配度，是否解决实际问题
3. 时效性(timeliness)：信息的新鲜度和时效性
4. 可用性(usability)：用户理解和操作的便利性
5. 准确性(accuracy)：事实信息的正确性
6. 信息密度(density)：单位文本包含的有效信息量

请严格按照以下JSON格式返回评分结果：
{{
    "completeness": 8.5,
    "relevance": 9.0,
    "timeliness": 7.5,
    "usability": 8.0,
    "accuracy": 8.5,
    "density": 7.0,
    "overall_score": 8.1,
    "reasoning": "简要说明评分理由"
}}
"""
        return prompt
    
    async def call_qwen_api_async(self, session: aiohttp.ClientSession, prompt: str) -> Optional[Dict[str, Any]]:
        """异步调用Qwen API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": QWEN_CONFIG['max_tokens'],
            "temperature": QWEN_CONFIG['temperature']
        }
        
        for attempt in range(QWEN_CONFIG['max_retries']):
            try:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=QWEN_CONFIG['timeout'])
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._parse_score_response(content)
                    else:
                        logger.warning(f"API调用失败，状态码: {response.status}")
                        
            except Exception as e:
                logger.error(f"API调用异常 (尝试 {attempt + 1}): {e}")
                
            if attempt < QWEN_CONFIG['max_retries'] - 1:
                await asyncio.sleep(QWEN_CONFIG['retry_delay'] * (2 ** attempt))
        
        return None
    
    def _parse_score_response(self, content: str) -> Optional[Dict[str, Any]]:
        """解析Qwen返回的评分结果"""
        try:
            # 尝试提取JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                score_data = json.loads(json_str)
                
                # 验证必需字段
                required_fields = list(self.score_weights.keys()) + ['overall_score']
                for field in required_fields:
                    if field not in score_data:
                        logger.error(f"评分结果缺少字段: {field}")
                        return None
                
                return score_data
            else:
                logger.error("无法从响应中提取JSON格式的评分结果")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"解析评分结果JSON失败: {e}")
            return None
    
    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """计算加权综合评分"""
        weighted_sum = 0
        total_weight = 0
        
        for dimension, weight in self.score_weights.items():
            if dimension in scores:
                weighted_sum += scores[dimension] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    async def score_batch_async(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """异步批量评分"""
        logger.info(f"开始异步批量评分，总计 {len(data_list)} 条数据，并发数: {self.max_concurrent}")
        
        scored_data = []
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def score_single_item_with_semaphore(item: Dict[str, Any], index: int):
            async with semaphore:
                return await self._score_single_item_async(item, index)
        
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=self.max_concurrent * 2)
        timeout = aiohttp.ClientTimeout(total=QWEN_CONFIG['timeout'])
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建所有任务
            tasks = [
                score_single_item_with_semaphore(item, i) 
                for i, item in enumerate(data_list)
            ]
            
            # 执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"评分任务 {i} 失败: {result}")
                elif result is not None:
                    scored_data.append(result)
                    if (i + 1) % 10 == 0:
                        logger.info(f"评分进度: {len(scored_data)}/{len(data_list)}")
        
        logger.info(f"异步批量评分完成，成功评分 {len(scored_data)} 条数据")
        return scored_data
    
    async def _score_single_item_async(self, item: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """异步评分单条数据"""
        title = item.get('title', '')
        content = item.get('content', '')
        category = item.get('category', item.get('data_category', ''))
        
        # 创建评分提示词
        prompt = self.create_scoring_prompt(title, content, category)
        
        # 创建临时会话进行API调用
        connector = aiohttp.TCPConnector()
        timeout = aiohttp.ClientTimeout(total=QWEN_CONFIG['timeout'])
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            score_result = await self.call_qwen_api_async(session, prompt)
        
        if score_result:
            # 计算加权评分
            weighted_score = self.calculate_weighted_score(score_result)
            score_result['weighted_score'] = weighted_score
            
            # 将评分结果添加到原数据中
            item['qwen_score'] = weighted_score
            item['score_breakdown'] = {
                k: v for k, v in score_result.items() 
                if k in self.score_weights or k in ['overall_score', 'reasoning']
            }
            
            logger.debug(f"评分完成 [{index}]: {title[:30]}... -> {weighted_score:.2f}")
            return item
        else:
            logger.error(f"评分失败 [{index}]: {title[:30]}...")
            return None
    
    def batch_score_concurrent(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并发批量评分（同步接口）"""
        return asyncio.run(self.score_batch_async(data_list))

def main():
    """测试并发评分器"""
    # 创建测试数据
    test_data = [
        {
            'title': f'测试通知{i}',
            'content': f'这是第{i}个测试通知的内容...',
            'category': '通知通告'
        }
        for i in range(10)
    ]
    
    # 测试并发评分
    scorer = ConcurrentQwenScorer(max_concurrent=3)
    
    start_time = time.time()
    results = scorer.batch_score_concurrent(test_data)
    end_time = time.time()
    
    print(f"并发评分完成:")
    print(f"  数据量: {len(test_data)} 条")
    print(f"  成功: {len(results)} 条")
    print(f"  耗时: {end_time - start_time:.2f} 秒")
    print(f"  平均: {(end_time - start_time) / len(test_data):.2f} 秒/条")

if __name__ == "__main__":
    main()
