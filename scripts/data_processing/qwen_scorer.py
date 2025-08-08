"""
USTB AI教务助手 - Qwen评分器
负责使用Qwen API对数据进行6维度质量评分
"""

import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from data_config import QWEN_CONFIG, QUALITY_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QwenScorer:
    """Qwen API评分器"""
    
    def __init__(self):
        self.api_key = QWEN_CONFIG['api_key']
        self.base_url = QWEN_CONFIG['base_url']
        self.model = QWEN_CONFIG['model']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.score_weights = QUALITY_CONFIG['score_weights']
        
        # 验证API配置
        if not self.api_key:
            logger.warning("未设置QWEN_API_KEY环境变量")
    
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
    
    def call_qwen_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用Qwen API"""
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
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=QWEN_CONFIG['timeout']
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return self._parse_score_response(content)
                else:
                    logger.warning(f"API调用失败，状态码: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"API调用异常 (尝试 {attempt + 1}): {e}")
                
            if attempt < QWEN_CONFIG['max_retries'] - 1:
                time.sleep(QWEN_CONFIG['retry_delay'] * (2 ** attempt))
        
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
    
    def score_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """对单条数据进行评分"""
        title = item.get('title', '')
        content = item.get('content', '')
        category = item.get('category', item.get('data_category', ''))
        
        # 创建评分提示词
        prompt = self.create_scoring_prompt(title, content, category)
        
        # 调用API获取评分
        score_result = self.call_qwen_api(prompt)
        
        if score_result:
            # 计算加权评分
            weighted_score = self.calculate_weighted_score(score_result)
            score_result['weighted_score'] = weighted_score
            
            logger.info(f"评分完成: {title[:30]}... -> {weighted_score:.2f}")
            return score_result
        else:
            logger.error(f"评分失败: {title[:30]}...")
            return None
    
    def batch_score(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量评分"""
        scored_data = []
        total_count = len(data_list)
        
        logger.info(f"开始批量评分，总计 {total_count} 条数据")
        
        for i, item in enumerate(data_list):
            logger.info(f"评分进度: {i+1}/{total_count}")
            
            score_result = self.score_single_item(item)
            
            if score_result:
                # 将评分结果添加到原数据中
                item['qwen_score'] = score_result['weighted_score']
                item['score_breakdown'] = {
                    k: v for k, v in score_result.items() 
                    if k in self.score_weights or k in ['overall_score', 'reasoning']
                }
                scored_data.append(item)
            
            # 添加延迟避免API限流
            time.sleep(0.5)
        
        logger.info(f"批量评分完成，成功评分 {len(scored_data)} 条数据")
        return scored_data

def main():
    """测试Qwen评分器"""
    # 测试样本数据
    test_data = {
        'title': '关于开展2025年工程教育认证申请工作的通知',
        'content': '各教学单位：根据中国工程教育专业认证协会要求，我校将开展2025年工程教育认证申请工作...',
        'category': '通知通告'
    }
    
    scorer = QwenScorer()
    result = scorer.score_single_item(test_data)
    
    if result:
        print("评分结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("评分失败")

if __name__ == "__main__":
    main()
