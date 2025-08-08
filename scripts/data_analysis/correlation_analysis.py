#!/usr/bin/env python3
"""
USTB数据科学专家 - 相关性分析脚本
生成评分维度相关性分析图
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def load_full_scoring_data():
    """加载完整评分数据（包含6维度详细评分）"""
    data_path = project_root / "data" / "processed" / "full_scoring_complete.json"
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 成功加载完整评分数据: {len(data)} 条")
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ 加载完整评分数据失败: {e}")
        return None

def create_correlation_matrix():
    """创建相关性矩阵图"""
    print("🔗 生成评分维度相关性分析图...")
    
    # 加载完整评分数据
    df = load_full_scoring_data()
    if df is None:
        return
    
    # 提取6维度评分
    if 'score_breakdown' in df.columns:
        # 展开score_breakdown字典
        score_breakdown_df = pd.json_normalize(df['score_breakdown'])
        dimensions = ['completeness', 'relevance', 'timeliness', 'usability', 'accuracy', 'density']
        
        # 检查哪些维度存在
        available_dims = [dim for dim in dimensions if dim in score_breakdown_df.columns]
        
        if len(available_dims) >= 3:
            # 创建相关性分析
            correlation_data = score_breakdown_df[available_dims]
            correlation_data['overall_score'] = df['qwen_score']
            correlation_data['content_length'] = df['content'].str.len()
            
            # 计算相关性矩阵
            corr_matrix = correlation_data.corr()
            
            # 创建图表
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('USTB数据评分维度相关性分析', fontsize=16, fontweight='bold')
            
            # 1. 相关性热力图
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='coolwarm', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": .8}, ax=axes[0, 0])
            axes[0, 0].set_title('评分维度相关性热力图')
            
            # 2. 散点图矩阵（选择几个关键维度）
            key_dims = available_dims[:4] if len(available_dims) >= 4 else available_dims
            scatter_data = correlation_data[key_dims]
            
            # 创建散点图矩阵
            for i, dim1 in enumerate(key_dims):
                for j, dim2 in enumerate(key_dims):
                    if i != j and i < 2 and j < 2:  # 只显示2x2的子图
                        if i == 0 and j == 1:
                            axes[0, 1].scatter(scatter_data[dim1], scatter_data[dim2], 
                                             alpha=0.6, s=20)
                            axes[0, 1].set_xlabel(dim1)
                            axes[0, 1].set_ylabel(dim2)
                            axes[0, 1].set_title(f'{dim1} vs {dim2}')
                            axes[0, 1].grid(True, alpha=0.3)
            
            # 3. 维度评分分布对比
            dims_to_plot = available_dims[:4]
            box_data = [correlation_data[dim].values for dim in dims_to_plot]
            bp = axes[1, 0].boxplot(box_data, labels=dims_to_plot, patch_artist=True)
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(dims_to_plot)))
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            axes[1, 0].set_title('各维度评分分布对比')
            axes[1, 0].set_ylabel('评分')
            axes[1, 0].tick_params(axis='x', rotation=45)
            axes[1, 0].grid(True, alpha=0.3)
            
            # 4. 相关性统计表
            # 选择与总分相关性最高的几个维度
            overall_corr = corr_matrix['overall_score'].drop('overall_score').abs().sort_values(ascending=False)
            
            table_data = []
            for dim, corr_val in overall_corr.head(6).items():
                if dim != 'content_length':
                    table_data.append([dim, f"{corr_val:.3f}"])
            
            if table_data:
                table = axes[1, 1].table(cellText=table_data,
                                        colLabels=['维度', '与总分相关性'],
                                        cellLoc='center',
                                        loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(11)
                table.scale(1.2, 1.8)
                axes[1, 1].set_title('维度与总分相关性排序')
                axes[1, 1].axis('off')
            
            plt.tight_layout()
            
            # 保存图表
            output_dir = project_root / "analysis" / "data_visualization"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "correlation_matrix.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 相关性矩阵图已保存: {output_path}")
            
            return corr_matrix
            
        else:
            print("❌ 可用的评分维度不足，无法生成相关性分析")
            return None
    else:
        print("❌ 数据中缺少score_breakdown字段")
        return None

def main():
    """主函数"""
    print("🔗 USTB数据科学专家 - 相关性分析")
    print("="*50)
    
    # 生成相关性矩阵图
    corr_matrix = create_correlation_matrix()
    
    if corr_matrix is not None:
        print("\n📊 相关性分析结果:")
        print("="*30)
        print(corr_matrix.round(3))
        
        print("\n" + "="*50)
        print("✅ 相关性分析完成")
        print("📋 所有4个可视化图表已生成完毕")
        print("="*50)
    else:
        print("\n❌ 相关性分析失败")

if __name__ == "__main__":
    main()
