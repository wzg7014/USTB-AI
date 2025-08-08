"""
USTB AI教务助手 - 修复版评分器
修复提示词问题，避免模型复制示例数值
"""

import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from data_config import QWEN_CONFIG, QUALITY_CONFIG
from data_loader import DataLoader

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedQwenScorer:
    """修复版Qwen评分器"""
    
    def __init__(self):
        self.api_key = QWEN_CONFIG['api_key']
        self.base_url = QWEN_CONFIG['base_url']
        self.model = QWEN_CONFIG['model']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.score_weights = QUALITY_CONFIG['score_weights']
    
    def create_scoring_prompt_fixed(self, title: str, content: str, category: str) -> str:
        """创建修复版评分提示词 - 不包含具体数值示例"""
        prompt = f"""
你是一个专业的教务数据质量评估专家。请对以下USTB教务数据进行客观、准确的6维度质量评分。

数据信息：
标题：{title}
分类：{category}
内容：{content[:800]}

评分要求：
请根据内容实际情况，对每个维度给出0-10分的评分（可以是小数）：

1. 完整性(completeness)：信息是否完整，包含必要的教务信息
   - 10分：信息非常完整，包含所有必要细节
   - 7-9分：信息较完整，包含主要内容
   - 4-6分：信息基本完整，缺少部分细节
   - 1-3分：信息不完整，缺少重要内容
   - 0分：信息严重不完整

2. 相关性(relevance)：与USTB教务场景的匹配度
   - 10分：与教务工作高度相关，直接解决实际问题
   - 7-9分：与教务工作相关性较强
   - 4-6分：与教务工作有一定相关性
   - 1-3分：相关性较弱
   - 0分：无相关性

3. 时效性(timeliness)：信息的新鲜度和时效性
   - 10分：信息非常新鲜，时效性强
   - 7-9分：信息较新，有一定时效性
   - 4-6分：信息一般新鲜
   - 1-3分：信息较旧
   - 0分：信息过时

4. 可用性(usability)：用户理解和操作的便利性
   - 10分：非常易懂，操作指引清晰
   - 7-9分：比较易懂，指引较清晰
   - 4-6分：基本可懂，指引一般
   - 1-3分：较难理解
   - 0分：难以理解

5. 准确性(accuracy)：事实信息的正确性
   - 10分：信息完全准确，无错误
   - 7-9分：信息基本准确，极少错误
   - 4-6分：信息大部分准确
   - 1-3分：存在一些错误
   - 0分：错误较多

6. 信息密度(density)：单位文本包含的有效信息量
   - 10分：信息密度很高，内容丰富
   - 7-9分：信息密度较高
   - 4-6分：信息密度一般
   - 1-3分：信息密度较低
   - 0分：信息密度很低

请严格按照以下JSON格式返回评分结果，不要包含任何其他文字：
{{
    "completeness": [请填入0-10的数值],
    "relevance": [请填入0-10的数值],
    "timeliness": [请填入0-10的数值],
    "usability": [请填入0-10的数值],
    "accuracy": [请填入0-10的数值],
    "density": [请填入0-10的数值],
    "overall_score": [请填入0-10的数值],
    "reasoning": "[请简要说明评分理由，50字以内]"
}}
"""
        return prompt
    
    def call_qwen_api_debug(self, prompt: str, item_index: int) -> Optional[Dict[str, Any]]:
        """调用API并显示调试信息"""
        print(f"\n🔍 API调用 [数据{item_index}]:")
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": QWEN_CONFIG['max_tokens'],
            "temperature": 0.3,  # 提高温度增加随机性
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=QWEN_CONFIG['timeout']
            )
            
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                raw_content = result['choices'][0]['message']['content']
                
                print(f"  原始响应: {raw_content[:150]}...")
                
                parsed_result = self._parse_score_response(raw_content)
                
                if parsed_result:
                    print(f"  ✅ 解析成功")
                    self._display_detailed_scores(parsed_result, item_index)
                    return parsed_result
                else:
                    print(f"  ❌ 解析失败")
                    
            else:
                print(f"  ❌ API失败: {response.text}")
                
        except Exception as e:
            print(f"  ❌ 异常: {e}")
        
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
                required_fields = list(self.score_weights.keys()) + ['overall_score']
                for field in required_fields:
                    if field not in score_data:
                        return None
                
                return score_data
            
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _display_detailed_scores(self, scores: Dict[str, Any], item_index: int):
        """显示详细评分"""
        print(f"  📊 评分结果 [数据{item_index}]:")
        print(f"     完整性: {scores.get('completeness', 'N/A')}")
        print(f"     相关性: {scores.get('relevance', 'N/A')}")
        print(f"     时效性: {scores.get('timeliness', 'N/A')}")
        print(f"     可用性: {scores.get('usability', 'N/A')}")
        print(f"     准确性: {scores.get('accuracy', 'N/A')}")
        print(f"     信息密度: {scores.get('density', 'N/A')}")
        print(f"     总体评分: {scores.get('overall_score', 'N/A')}")
        
        weighted_score = self.calculate_weighted_score(scores)
        print(f"     加权评分: {weighted_score:.2f}")
        
        reasoning = scores.get('reasoning', '')
        print(f"     评分理由: {reasoning}")
    
    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """计算加权评分"""
        weighted_sum = 0
        total_weight = 0
        
        for dimension, weight in self.score_weights.items():
            if dimension in scores:
                weighted_sum += scores[dimension] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def test_fixed_scoring(self, data_list: List[Dict[str, Any]], max_items=3) -> List[Dict[str, Any]]:
        """测试修复版评分"""
        print(f"\n🧪 测试修复版评分器")
        print("=" * 60)
        
        scored_data = []
        
        for i, item in enumerate(data_list[:max_items]):
            print(f"\n📋 处理数据 {i+1}/{max_items}")
            print(f"   标题: {item.get('title', '')[:60]}...")
            
            title = item.get('title', '')
            content = item.get('content', '')
            category = item.get('category', item.get('data_category', ''))
            
            # 使用修复版提示词
            prompt = self.create_scoring_prompt_fixed(title, content, category)
            
            # 调用API
            score_result = self.call_qwen_api_debug(prompt, i+1)
            
            if score_result:
                weighted_score = self.calculate_weighted_score(score_result)
                item['qwen_score'] = weighted_score
                item['score_breakdown'] = score_result
                scored_data.append(item)
                print(f"   ✅ 成功: {weighted_score:.2f}")
            else:
                print(f"   ❌ 失败")
            
            time.sleep(2)
        
        return scored_data

def main():
    """测试修复版评分器"""
    print("🔧 USTB数据处理 - 修复版评分测试")
    print("=" * 60)
    
    # 加载不同的测试数据
    loader = DataLoader()
    all_data = loader.load_all_data()
    
    # 选择差异较大的数据进行测试
    test_data = [
        all_data[0],    # 第1条
        all_data[100],  # 第101条
        all_data[500],  # 第501条
    ]
    
    # 显示测试数据信息
    print("\n📋 测试数据信息:")
    for i, item in enumerate(test_data):
        print(f"数据{i+1}: {item.get('title', '')[:50]}...")
        print(f"       内容长度: {len(item.get('content', ''))} 字符")
        print(f"       分类: {item.get('category', item.get('data_category', ''))}")
    
    # 测试修复版评分
    scorer = FixedQwenScorer()
    results = scorer.test_fixed_scoring(test_data)
    
    # 对比结果
    print("\n" + "=" * 60)
    print("🔍 评分结果对比:")
    
    for i, result in enumerate(results):
        print(f"\n数据 {i+1}:")
        print(f"  标题: {result.get('title', '')[:50]}...")
        print(f"  最终评分: {result.get('qwen_score', 0):.2f}")
        
        breakdown = result.get('score_breakdown', {})
        print(f"  详细评分:")
        for dim in ['completeness', 'relevance', 'timeliness', 'usability', 'accuracy', 'density']:
            print(f"    {dim}: {breakdown.get(dim, 'N/A')}")
        print(f"  评分理由: {breakdown.get('reasoning', 'N/A')}")

if __name__ == "__main__":
    main()
