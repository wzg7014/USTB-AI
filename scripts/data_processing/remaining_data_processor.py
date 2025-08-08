"""
USTB AI教务助手 - 剩余数据处理器
处理fylm、jxfc、zyxz、tspy、bmgk等剩余分类的数据
"""

import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# 导入自定义模块
from data_config import DATA_PATHS, QWEN_CONFIG, ensure_directories
from data_loader import DataLoader

class RemainingDataProcessor:
    """剩余数据处理器"""
    
    def __init__(self, max_concurrent=5):
        self.max_concurrent = max_concurrent
        self.api_key = QWEN_CONFIG['api_key']
        self.base_url = QWEN_CONFIG['base_url']
        self.model = QWEN_CONFIG['model']
        
        # 已处理的分类
        self.processed_categories = {'notices', 'regulations'}
        
        ensure_directories()
    
    def load_remaining_data(self) -> List[Dict[str, Any]]:
        """加载剩余未处理的数据"""
        print("📂 加载剩余数据...")
        
        loader = DataLoader()
        all_data = loader.load_all_data()
        
        # 筛选出未处理的分类
        remaining_data = []
        category_stats = {}
        
        for item in all_data:
            category = item.get('data_category', '')
            if category not in self.processed_categories:
                remaining_data.append(item)
                category_stats[category] = category_stats.get(category, 0) + 1
        
        print(f"✅ 剩余数据加载完成:")
        for category, count in sorted(category_stats.items()):
            print(f"  {category}: {count}条")
        print(f"  总计: {len(remaining_data)}条")
        
        return remaining_data
    
    def create_scoring_prompt_fixed(self, title: str, content: str, category: str) -> str:
        """创建修复版评分提示词"""
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
                    
            except Exception as e:
                print(f"API调用异常 (尝试 {attempt + 1}): {e}")
                
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
        weights = {
            'completeness': 0.2,
            'relevance': 0.2,
            'timeliness': 0.15,
            'usability': 0.15,
            'accuracy': 0.15,
            'density': 0.15
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for dimension, weight in weights.items():
            if dimension in scores:
                weighted_sum += scores[dimension] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    async def process_remaining_data_async(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """异步处理剩余数据"""
        print(f"🚀 开始处理剩余数据: {len(data_list)}条")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def score_single_item(item: Dict[str, Any], index: int):
            async with semaphore:
                title = item.get('title', '')
                content = item.get('content', '')
                category = item.get('data_category', '')
                
                prompt = self.create_scoring_prompt_fixed(title, content, category)
                
                connector = aiohttp.TCPConnector()
                timeout = aiohttp.ClientTimeout(total=QWEN_CONFIG['timeout'])
                
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    score_result = await self.call_qwen_api_async(session, prompt)
                
                if score_result:
                    weighted_score = self.calculate_weighted_score(score_result)
                    item['qwen_score'] = weighted_score
                    item['score_breakdown'] = score_result
                    
                    if (index + 1) % 10 == 0:
                        print(f"  进度: {index + 1}/{len(data_list)} ({(index + 1)/len(data_list)*100:.1f}%)")
                    
                    return item
                else:
                    print(f"  评分失败: {title[:30]}...")
                    return None
        
        # 创建所有任务
        tasks = [score_single_item(item, i) for i, item in enumerate(data_list)]
        
        # 执行任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        scored_data = []
        for result in results:
            if isinstance(result, Exception):
                print(f"任务失败: {result}")
            elif result is not None:
                scored_data.append(result)
        
        print(f"✅ 剩余数据处理完成: {len(scored_data)}/{len(data_list)} 成功")
        return scored_data
    
    def merge_with_existing_data(self, new_scored_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并新数据与已有数据"""
        print("🔄 合并数据...")
        
        # 加载已有的评分数据
        existing_file = DATA_PATHS['processed_dir'] / "full_scoring_progress_084.json"
        
        if existing_file.exists():
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"  已有数据: {len(existing_data)}条")
        else:
            existing_data = []
            print("  未找到已有数据文件")
        
        # 合并数据
        all_data = existing_data + new_scored_data
        print(f"  合并后总数据: {len(all_data)}条")
        
        # 保存完整数据
        complete_file = DATA_PATHS['processed_dir'] / "complete_scoring_all_categories.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 完整数据已保存: {complete_file}")
        
        return all_data
    
    def analyze_complete_distribution(self, all_data: List[Dict[str, Any]]):
        """分析完整数据分布"""
        print("\n" + "="*60)
        print("📊 完整数据分布分析")
        print("="*60)
        
        # 分类统计
        category_stats = {}
        category_scores = {}
        
        for item in all_data:
            category = item.get('data_category', 'Unknown')
            score = item.get('qwen_score', 0)
            
            category_stats[category] = category_stats.get(category, 0) + 1
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(score)
        
        print("📋 分类分布:")
        for category, count in sorted(category_stats.items()):
            avg_score = sum(category_scores[category]) / len(category_scores[category])
            print(f"  {category}: {count}条 (平均分: {avg_score:.2f})")
        
        # 总体评分分析
        all_scores = [item.get('qwen_score', 0) for item in all_data]
        
        print(f"\n📊 总体评分分析:")
        print(f"  总数据量: {len(all_scores)}条")
        print(f"  平均分: {sum(all_scores)/len(all_scores):.2f}")
        print(f"  最低分: {min(all_scores):.2f}")
        print(f"  最高分: {max(all_scores):.2f}")
        
        # 阈值分析
        print(f"\n💡 筛选阈值分析:")
        for threshold in [6.0, 6.5, 7.0, 7.5, 8.0]:
            count = len([s for s in all_scores if s >= threshold])
            percentage = count / len(all_scores) * 100
            print(f"  阈值 {threshold}: {count}条 ({percentage:.1f}%)")
            
            if count >= 500:
                print(f"    ✅ 可筛选出≥500条数据")
            else:
                print(f"    ❌ 数据不足500条")

async def main():
    """主函数"""
    processor = RemainingDataProcessor(max_concurrent=5)
    
    # 1. 加载剩余数据
    remaining_data = processor.load_remaining_data()
    
    if not remaining_data:
        print("✅ 没有剩余数据需要处理")
        return
    
    # 2. 处理剩余数据
    start_time = datetime.now()
    scored_data = await processor.process_remaining_data_async(remaining_data)
    end_time = datetime.now()
    
    print(f"\n⏱️  处理耗时: {end_time - start_time}")
    
    # 3. 合并数据
    complete_data = processor.merge_with_existing_data(scored_data)
    
    # 4. 分析完整分布
    processor.analyze_complete_distribution(complete_data)
    
    print(f"\n🎉 所有数据处理完成！")
    print(f"📊 总数据量: {len(complete_data)}条")

if __name__ == "__main__":
    asyncio.run(main())
