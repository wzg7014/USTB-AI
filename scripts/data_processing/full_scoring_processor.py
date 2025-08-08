"""
USTB AI教务助手 - 全量评分处理器
数据处理专家：对全部4180条数据进行评分，获得真实分布后制定筛选策略
"""

import json
import time
import logging
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import matplotlib.pyplot as plt

# 导入自定义模块
from data_config import DATA_PATHS, QWEN_CONFIG, QUALITY_CONFIG, ensure_directories
from data_loader import DataLoader

# 配置日志
def setup_logging():
    """设置详细日志"""
    log_file = DATA_PATHS['logs_dir'] / 'full_scoring.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)

class FullScoringProcessor:
    """全量评分处理器"""
    
    def __init__(self, max_concurrent=5, batch_size=100):
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.api_key = QWEN_CONFIG['api_key']
        self.base_url = QWEN_CONFIG['base_url']
        self.model = QWEN_CONFIG['model']
        
        # 统计信息
        self.stats = {
            'total_data': 0,
            'scored_data': 0,
            'failed_data': 0,
            'start_time': None,
            'score_distribution': {},
            'dimension_stats': {}
        }
        
        # 确保目录存在
        ensure_directories()
    
    def create_scoring_prompt_fixed(self, title: str, content: str, category: str) -> str:
        """创建修复版评分提示词 - 避免固定示例数值"""
        prompt = f"""
你是专业的教务数据质量评估专家。请对以下USTB教务数据进行客观评分。

数据信息：
标题：{title}
分类：{category}
内容：{content[:800]}

评分要求：
对每个维度给出0-10分的评分（可以是小数），请根据实际内容质量评分：

1. 完整性(completeness)：信息是否完整，包含必要的教务信息
2. 相关性(relevance)：与USTB教务场景的匹配度
3. 时效性(timeliness)：信息的新鲜度和时效性
4. 可用性(usability)：用户理解和操作的便利性
5. 准确性(accuracy)：事实信息的正确性
6. 信息密度(density)：单位文本包含的有效信息量

请严格按照JSON格式返回，不要包含其他文字：
{{
    "completeness": [0-10的数值],
    "relevance": [0-10的数值],
    "timeliness": [0-10的数值],
    "usability": [0-10的数值],
    "accuracy": [0-10的数值],
    "density": [0-10的数值],
    "overall_score": [0-10的数值],
    "reasoning": "[简要评分理由]"
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
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": QWEN_CONFIG['max_tokens'],
            "temperature": 0.3
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
        """解析评分响应"""
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                score_data = json.loads(json_str)
                
                # 验证必需字段
                required_fields = ['completeness', 'relevance', 'timeliness', 'usability', 'accuracy', 'density', 'overall_score']
                for field in required_fields:
                    if field not in score_data:
                        return None
                
                return score_data
            
        except json.JSONDecodeError:
            pass
        
        return None
    
    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """计算加权评分"""
        weights = QUALITY_CONFIG['score_weights']
        weighted_sum = 0
        total_weight = 0
        
        for dimension, weight in weights.items():
            if dimension in scores:
                weighted_sum += scores[dimension] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    async def process_batch_async(self, batch_data: List[Dict[str, Any]], batch_num: int) -> List[Dict[str, Any]]:
        """异步处理批次数据"""
        logger.info(f"🔄 处理批次 {batch_num}: {len(batch_data)} 条数据")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def score_single_item(item: Dict[str, Any], index: int):
            async with semaphore:
                title = item.get('title', '')
                content = item.get('content', '')
                category = item.get('category', item.get('data_category', ''))
                
                prompt = self.create_scoring_prompt_fixed(title, content, category)
                
                connector = aiohttp.TCPConnector()
                timeout = aiohttp.ClientTimeout(total=QWEN_CONFIG['timeout'])
                
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    score_result = await self.call_qwen_api_async(session, prompt)
                
                if score_result:
                    weighted_score = self.calculate_weighted_score(score_result)
                    item['qwen_score'] = weighted_score
                    item['score_breakdown'] = score_result
                    return item
                else:
                    self.stats['failed_data'] += 1
                    return None
        
        # 创建所有任务
        tasks = [score_single_item(item, i) for i, item in enumerate(batch_data)]
        
        # 执行任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        scored_batch = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"评分任务失败: {result}")
            elif result is not None:
                scored_batch.append(result)
        
        self.stats['scored_data'] += len(scored_batch)
        logger.info(f"✅ 批次 {batch_num} 完成: {len(scored_batch)}/{len(batch_data)} 成功")
        
        return scored_batch
    
    def save_batch_results(self, all_scored_data: List[Dict[str, Any]], batch_num: int):
        """保存批次结果"""
        # 保存当前所有数据
        output_file = DATA_PATHS['processed_dir'] / f"full_scoring_progress_{batch_num:03d}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_scored_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 进度保存: {output_file.name} ({len(all_scored_data)} 条数据)")
        
        # 更新统计信息
        self._update_statistics(all_scored_data)
    
    def _update_statistics(self, scored_data: List[Dict[str, Any]]):
        """更新统计信息"""
        if not scored_data:
            return
        
        scores = [item.get('qwen_score', 0) for item in scored_data]
        
        # 评分分布统计
        self.stats['score_distribution'] = {
            'mean': np.mean(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'median': np.median(scores),
            'q25': np.percentile(scores, 25),
            'q75': np.percentile(scores, 75)
        }
        
        # 各维度统计
        dimensions = ['completeness', 'relevance', 'timeliness', 'usability', 'accuracy', 'density']
        self.stats['dimension_stats'] = {}
        
        for dim in dimensions:
            dim_scores = []
            for item in scored_data:
                breakdown = item.get('score_breakdown', {})
                if dim in breakdown:
                    dim_scores.append(breakdown[dim])
            
            if dim_scores:
                self.stats['dimension_stats'][dim] = {
                    'mean': np.mean(dim_scores),
                    'std': np.std(dim_scores),
                    'min': np.min(dim_scores),
                    'max': np.max(dim_scores)
                }
    
    def analyze_score_distribution(self, scored_data: List[Dict[str, Any]]):
        """分析评分分布并建议阈值"""
        scores = [item.get('qwen_score', 0) for item in scored_data]
        
        print("\n" + "="*60)
        print("📊 全量评分分布分析")
        print("="*60)
        
        # 基础统计
        print(f"总数据量: {len(scores)} 条")
        print(f"平均分: {np.mean(scores):.2f}")
        print(f"标准差: {np.std(scores):.2f}")
        print(f"最低分: {np.min(scores):.2f}")
        print(f"最高分: {np.max(scores):.2f}")
        print(f"中位数: {np.median(scores):.2f}")
        
        # 分位数分析
        print(f"\n📈 分位数分析:")
        for p in [10, 25, 50, 75, 90, 95]:
            percentile_score = np.percentile(scores, p)
            count_above = len([s for s in scores if s >= percentile_score])
            print(f"  {p}%分位数: {percentile_score:.2f} (≥此分数的数据: {count_above} 条)")
        
        # 阈值建议
        print(f"\n💡 筛选阈值建议:")
        for threshold in [6.0, 6.5, 7.0, 7.5, 8.0, 8.5]:
            count = len([s for s in scores if s >= threshold])
            percentage = count / len(scores) * 100
            print(f"  阈值 {threshold}: {count} 条数据 ({percentage:.1f}%)")
            
            if count >= 500:
                print(f"    ✅ 可筛选出≥500条数据")
            else:
                print(f"    ❌ 数据不足500条")
        
        return scores
    
    async def run_full_scoring(self):
        """运行全量评分"""
        print("🚀 开始全量评分处理")
        print("="*60)
        
        self.stats['start_time'] = datetime.now()
        
        # 1. 加载数据
        print("📂 加载原始数据...")
        loader = DataLoader()
        all_data = loader.load_all_data()
        self.stats['total_data'] = len(all_data)
        
        print(f"✅ 数据加载完成: {len(all_data)} 条")
        
        # 2. 分批处理
        all_scored_data = []
        total_batches = (len(all_data) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(all_data), self.batch_size):
            batch_num = i // self.batch_size + 1
            batch_data = all_data[i:i + self.batch_size]
            
            print(f"\n🎯 批次 {batch_num}/{total_batches}")
            
            # 异步处理批次
            scored_batch = await self.process_batch_async(batch_data, batch_num)
            all_scored_data.extend(scored_batch)
            
            # 保存进度
            self.save_batch_results(all_scored_data, batch_num)
            
            # 显示进度
            progress = len(all_scored_data) / len(all_data) * 100
            print(f"📊 总进度: {len(all_scored_data)}/{len(all_data)} ({progress:.1f}%)")
            
            # 每10个批次分析一次分布
            if batch_num % 10 == 0:
                self.analyze_score_distribution(all_scored_data)
        
        # 3. 最终分析
        print(f"\n🎉 全量评分完成!")
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        print(f"⏱️  总耗时: {duration}")
        print(f"📊 成功评分: {len(all_scored_data)}/{len(all_data)}")
        print(f"❌ 失败数量: {self.stats['failed_data']}")
        
        # 4. 详细分布分析
        final_scores = self.analyze_score_distribution(all_scored_data)
        
        # 5. 保存最终结果
        final_file = DATA_PATHS['processed_dir'] / "full_scoring_complete.json"
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(all_scored_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 最终结果保存: {final_file}")
        
        return all_scored_data, final_scores

def main():
    """主函数"""
    setup_logging()
    
    processor = FullScoringProcessor(max_concurrent=5, batch_size=50)
    
    # 运行全量评分
    scored_data, scores = asyncio.run(processor.run_full_scoring())
    
    print(f"\n✅ 全量评分处理完成！")
    print(f"📊 获得 {len(scored_data)} 条评分数据")
    print(f"💡 现在可以基于真实分布制定筛选策略")

if __name__ == "__main__":
    main()
