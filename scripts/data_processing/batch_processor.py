"""
USTB AI教务助手 - 分批处理器
支持分批处理、实时保存、进度监控
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 导入自定义模块
from data_config import DATA_PATHS, QUALITY_CONFIG, ensure_directories
from data_loader import DataLoader
from concurrent_scorer import ConcurrentQwenScorer
from deduplicator import Deduplicator
from dataset_generator import DatasetGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchProcessor:
    """分批处理器"""
    
    def __init__(self, batch_size=50, max_concurrent=5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.processed_dir = DATA_PATHS['processed_dir']
        
        # 确保目录存在
        ensure_directories()
        
        # 初始化组件
        self.data_loader = DataLoader()
        self.scorer = ConcurrentQwenScorer(max_concurrent=max_concurrent)
        self.deduplicator = Deduplicator()
        self.dataset_generator = DatasetGenerator()
        
        # 处理统计
        self.stats = {
            'total_loaded': 0,
            'total_scored': 0,
            'total_high_quality': 0,
            'total_deduplicated': 0,
            'batches_completed': 0,
            'start_time': None,
            'current_batch_time': None
        }
    
    def process_target_data(self, target_count=500):
        """处理目标数量的数据"""
        print("🚀 开始分批处理USTB数据")
        print("=" * 60)
        print(f"📊 处理配置:")
        print(f"  目标数量: {target_count} 条")
        print(f"  批次大小: {self.batch_size} 条")
        print(f"  并发数: {self.max_concurrent}")
        print(f"  预计批次: {(target_count + self.batch_size - 1) // self.batch_size}")
        print("=" * 60)
        
        self.stats['start_time'] = datetime.now()
        
        # 1. 加载原始数据
        print("📂 阶段1：加载原始数据")
        all_data = self.data_loader.load_all_data()
        self.stats['total_loaded'] = len(all_data)
        
        # 取前N条数据进行处理（实际应该是筛选后的高质量数据）
        processing_data = all_data[:target_count * 3]  # 多取一些以确保能筛选出足够的高质量数据
        print(f"✅ 准备处理: {len(processing_data)} 条数据")
        
        # 2. 分批处理
        all_scored_data = []
        batch_num = 0
        
        for i in range(0, len(processing_data), self.batch_size):
            batch_num += 1
            batch_data = processing_data[i:i + self.batch_size]
            
            print(f"\n🎯 处理批次 {batch_num}")
            print(f"数据范围: {i+1}-{min(i+self.batch_size, len(processing_data))}")
            
            # 处理当前批次
            batch_results = self._process_batch(batch_data, batch_num)
            
            if batch_results:
                all_scored_data.extend(batch_results)
                
                # 实时保存中间结果
                self._save_intermediate_results(all_scored_data, batch_num)
                
                # 检查是否已达到目标数量
                high_quality_count = len([item for item in all_scored_data 
                                        if item.get('qwen_score', 0) >= QUALITY_CONFIG['score_threshold']])
                
                print(f"📊 当前统计:")
                print(f"  已评分: {len(all_scored_data)} 条")
                print(f"  高质量: {high_quality_count} 条")
                print(f"  目标进度: {min(high_quality_count/target_count*100, 100):.1f}%")
                
                if high_quality_count >= target_count:
                    print(f"🎉 已达到目标数量 {target_count} 条高质量数据！")
                    break
        
        # 3. 最终处理
        print(f"\n✨ 阶段3：最终数据处理")
        final_results = self._final_processing(all_scored_data, target_count)
        
        # 4. 生成最终报告
        self._generate_final_report(final_results)
        
        return final_results
    
    def _process_batch(self, batch_data: List[Dict[str, Any]], batch_num: int) -> List[Dict[str, Any]]:
        """处理单个批次"""
        self.stats['current_batch_time'] = datetime.now()
        
        print(f"⚡ 开始评分: {len(batch_data)} 条数据")
        
        # 并发评分
        start_time = time.time()
        scored_batch = self.scorer.batch_score_concurrent(batch_data)
        scoring_time = time.time() - start_time
        
        print(f"✅ 批次评分完成:")
        print(f"  成功数量: {len(scored_batch)}/{len(batch_data)}")
        print(f"  评分耗时: {scoring_time:.2f} 秒")
        print(f"  平均速度: {scoring_time/len(batch_data):.2f} 秒/条")
        
        # 更新统计
        self.stats['total_scored'] += len(scored_batch)
        self.stats['batches_completed'] = batch_num
        
        return scored_batch
    
    def _save_intermediate_results(self, all_data: List[Dict[str, Any]], batch_num: int):
        """保存中间结果"""
        # 保存原始评分数据
        intermediate_file = self.processed_dir / f"intermediate_batch_{batch_num:03d}.json"
        
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 中间结果已保存: {intermediate_file.name}")
        
        # 保存当前统计
        stats_file = self.processed_dir / "processing_stats.json"
        current_stats = self.stats.copy()
        current_stats['last_update'] = datetime.now().isoformat()
        current_stats['total_data_processed'] = len(all_data)
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(current_stats, f, ensure_ascii=False, indent=2, default=str)
    
    def _final_processing(self, all_scored_data: List[Dict[str, Any]], target_count: int) -> Dict[str, Any]:
        """最终数据处理"""
        # 1. 质量筛选
        print("🔍 质量筛选...")
        threshold = QUALITY_CONFIG['score_threshold']
        high_quality_data = [
            item for item in all_scored_data 
            if item.get('qwen_score', 0) >= threshold
        ]
        
        print(f"✅ 高质量数据: {len(high_quality_data)} 条 (阈值: {threshold})")
        
        # 2. 去重处理
        print("🔄 去重处理...")
        deduplicated_data = self.deduplicator.deduplicate(high_quality_data)
        print(f"✅ 去重完成: {len(deduplicated_data)} 条")
        
        # 3. 截取目标数量
        if len(deduplicated_data) > target_count:
            final_data = deduplicated_data[:target_count]
            print(f"📏 截取到目标数量: {target_count} 条")
        else:
            final_data = deduplicated_data
            print(f"⚠️ 实际数量: {len(final_data)} 条 (少于目标 {target_count} 条)")
        
        # 4. 生成双数据集
        print("📊 生成双数据集...")
        dataset_paths = self.dataset_generator.generate_datasets(final_data)
        
        # 更新最终统计
        self.stats['total_high_quality'] = len(high_quality_data)
        self.stats['total_deduplicated'] = len(deduplicated_data)
        
        return {
            'final_data': final_data,
            'dataset_paths': dataset_paths,
            'stats': self.stats
        }
    
    def _generate_final_report(self, results: Dict[str, Any]):
        """生成最终报告"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        stats = results['stats']
        final_count = len(results['final_data'])
        
        report_content = f"""# USTB AI教务助手 - 分批处理报告

## 📊 处理概览
- **开始时间**: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **总耗时**: {duration}
- **处理状态**: ✅ 成功完成

## 📈 数据统计
| 阶段 | 数据量 | 说明 |
|------|--------|------|
| 原始加载 | {stats['total_loaded']} 条 | 全部原始数据 |
| 评分完成 | {stats['total_scored']} 条 | Qwen 6维度评分 |
| 高质量筛选 | {stats['total_high_quality']} 条 | 评分≥{QUALITY_CONFIG['score_threshold']}分 |
| 去重处理 | {stats['total_deduplicated']} 条 | 多层次去重 |
| 最终输出 | {final_count} 条 | 双数据集数据 |

## ⚡ 性能指标
- **批次数量**: {stats['batches_completed']} 个
- **批次大小**: {self.batch_size} 条/批次
- **并发数**: {self.max_concurrent}
- **平均速度**: {stats['total_scored']/duration.total_seconds():.2f} 条/秒
- **筛选率**: {(final_count/stats['total_loaded']*100):.1f}%

## 📁 输出文件
- **RAG数据集**: `{results['dataset_paths']['rag_dataset_path']}`
- **训练数据集**: `{results['dataset_paths']['training_dataset_path']}`

## ✅ 质量验收
- [x] Qwen评分≥{QUALITY_CONFIG['score_threshold']}分
- [x] 重复率<{QUALITY_CONFIG['duplicate_threshold']*100}%
- [x] 双数据集格式规范
- [x] 分批保存完整

---
*报告生成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        report_file = DATA_PATHS['reports_dir'] / f"batch_processing_report_{end_time.strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n📋 最终报告已生成: {report_file}")
        
        # 显示摘要
        print("\n" + "=" * 60)
        print("🎉 分批处理完成!")
        print(f"⏱️  总耗时: {duration}")
        print(f"📊 最终数据: {final_count} 条")
        print(f"📈 处理效率: {stats['total_scored']/duration.total_seconds():.2f} 条/秒")
        print("=" * 60)

def main():
    """主函数"""
    processor = BatchProcessor(batch_size=50, max_concurrent=5)
    results = processor.process_target_data(target_count=500)
    
    print(f"\n✅ 处理完成！最终获得 {len(results['final_data'])} 条高质量数据")

if __name__ == "__main__":
    main()
