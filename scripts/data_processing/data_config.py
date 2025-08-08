"""
USTB AI教务助手 - 数据处理配置文件
数据处理专家：Qwen评分系统和双数据集生成
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 加载环境变量文件
def load_env_file():
    """加载.env文件中的环境变量"""
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# 自动加载环境变量
load_env_file()

# 数据路径配置
DATA_PATHS = {
    'raw_data_dir': PROJECT_ROOT / 'data' / 'raw' / '全部原始数据',
    'processed_dir': PROJECT_ROOT / 'data' / 'processed',
    'logs_dir': PROJECT_ROOT / 'logs',
    'reports_dir': PROJECT_ROOT / 'reports'
}

# Qwen API配置
QWEN_CONFIG = {
    'api_key': os.getenv('DASHSCOPE_API_KEY', ''),
    'model': 'qwen-plus',
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'max_tokens': 1000,
    'temperature': 0.1,
    'timeout': 30,
    'max_retries': 3,
    'retry_delay': 1
}

# 质量评分配置
QUALITY_CONFIG = {
    'score_threshold': 7.5,
    'duplicate_threshold': 0.02,
    'target_count': 500,
    'sample_check_ratio': 0.1,
    
    # 6维度评分权重
    'score_weights': {
        'completeness': 0.2,    # 完整性
        'relevance': 0.2,       # 相关性
        'timeliness': 0.15,     # 时效性
        'usability': 0.15,      # 可用性
        'accuracy': 0.15,       # 准确性
        'density': 0.15         # 信息密度
    }
}

# 去重配置
DEDUP_CONFIG = {
    'url_exact_match': True,
    'title_similarity_threshold': 0.85,
    'content_similarity_threshold': 0.90,
    'min_content_length': 50
}

# 输出配置
OUTPUT_CONFIG = {
    'rag_dataset_file': 'rag_data.json',
    'training_dataset_file': 'training_data.json',
    'quality_report_file': 'data_quality_report.md'
}

# 批处理配置
BATCH_CONFIG = {
    'batch_size': 10,
    'max_concurrent': 3,
    'progress_save_interval': 50
}

def ensure_directories():
    """确保所有必需的目录存在"""
    for path in DATA_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_directories()
    print("配置文件加载完成")
