#!/usr/bin/env python3
"""
USTB数据科学专家 - 数据可视化脚本
生成4个必需的可视化图表
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

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

class DataVisualizer:
    """数据可视化器"""
    
    def __init__(self):
        self.df = None
        self.output_dir = project_root / "analysis" / "data_visualization"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self):
        """加载数据"""
        data_path = project_root / "data" / "processed" / "training_data.json"
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            self.df['content_length'] = self.df['content'].str.len()
            print(f"✅ 成功加载数据: {len(self.df)} 条")
            return True
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return False
    
    def create_score_distribution(self):
        """创建评分分布图"""
        print("📊 生成评分分布图...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('USTB数据质量评分分布分析', fontsize=16, fontweight='bold')
        
        # 1. 评分直方图
        axes[0, 0].hist(self.df['qwen_score'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].axvline(self.df['qwen_score'].mean(), color='red', linestyle='--', 
                          label=f'平均分: {self.df["qwen_score"].mean():.3f}')
        axes[0, 0].set_title('评分分布直方图')
        axes[0, 0].set_xlabel('Qwen评分')
        axes[0, 0].set_ylabel('频次')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 评分箱线图
        axes[0, 1].boxplot(self.df['qwen_score'], patch_artist=True, 
                          boxprops=dict(facecolor='lightgreen', alpha=0.7))
        axes[0, 1].set_title('评分箱线图')
        axes[0, 1].set_ylabel('Qwen评分')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 评分密度图
        axes[1, 0].hist(self.df['qwen_score'], bins=20, density=True, alpha=0.7, 
                       color='orange', label='实际分布')
        
        # 添加正态分布对比
        mean_score = self.df['qwen_score'].mean()
        std_score = self.df['qwen_score'].std()
        x = np.linspace(self.df['qwen_score'].min(), self.df['qwen_score'].max(), 100)
        normal_dist = (1/(std_score * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_score) / std_score) ** 2)
        axes[1, 0].plot(x, normal_dist, 'r-', label='理论正态分布')
        axes[1, 0].set_title('评分密度分布')
        axes[1, 0].set_xlabel('Qwen评分')
        axes[1, 0].set_ylabel('密度')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 评分统计信息
        stats_text = f"""
        数据量: {len(self.df)}
        平均分: {self.df['qwen_score'].mean():.3f}
        标准差: {self.df['qwen_score'].std():.3f}
        最小值: {self.df['qwen_score'].min():.3f}
        最大值: {self.df['qwen_score'].max():.3f}
        中位数: {self.df['qwen_score'].median():.3f}
        """
        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        axes[1, 1].set_title('评分统计信息')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        output_path = self.output_dir / "score_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ 评分分布图已保存: {output_path}")
        
    def create_category_analysis(self):
        """创建分类分析图"""
        print("📈 生成分类分析图...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('USTB数据分类分布分析', fontsize=16, fontweight='bold')
        
        # 1. 分类数量分布饼图
        category_counts = self.df['category'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(category_counts)))
        axes[0, 0].pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%',
                      colors=colors, startangle=90)
        axes[0, 0].set_title('分类数量分布')
        
        # 2. 分类评分对比
        category_scores = self.df.groupby('category')['qwen_score'].agg(['mean', 'std', 'count'])
        x_pos = np.arange(len(category_scores))
        bars = axes[0, 1].bar(x_pos, category_scores['mean'], 
                             yerr=category_scores['std'], capsize=5,
                             color=colors[:len(category_scores)], alpha=0.7)
        axes[0, 1].set_title('各分类平均评分对比')
        axes[0, 1].set_xlabel('分类')
        axes[0, 1].set_ylabel('平均评分')
        axes[0, 1].set_xticks(x_pos)
        axes[0, 1].set_xticklabels(category_scores.index, rotation=45)
        axes[0, 1].grid(True, alpha=0.3)
        
        # 添加数值标签
        for i, bar in enumerate(bars):
            height = bar.get_height()
            axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                           f'{height:.3f}', ha='center', va='bottom')
        
        # 3. 分类评分分布箱线图
        categories = self.df['category'].unique()
        score_data = [self.df[self.df['category'] == cat]['qwen_score'].values for cat in categories]
        bp = axes[1, 0].boxplot(score_data, labels=categories, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        axes[1, 0].set_title('各分类评分分布')
        axes[1, 0].set_xlabel('分类')
        axes[1, 0].set_ylabel('评分')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 分类统计表
        stats_df = category_scores.round(3)
        table_data = []
        for idx, row in stats_df.iterrows():
            table_data.append([idx, f"{row['mean']:.3f}", f"{row['std']:.3f}", f"{int(row['count'])}"])
        
        table = axes[1, 1].table(cellText=table_data,
                                colLabels=['分类', '平均分', '标准差', '数量'],
                                cellLoc='center',
                                loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
        axes[1, 1].set_title('分类统计表')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        output_path = self.output_dir / "category_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ 分类分析图已保存: {output_path}")
        
    def create_quality_trends(self):
        """创建质量趋势分析图"""
        print("📉 生成质量趋势分析图...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('USTB数据质量趋势分析', fontsize=16, fontweight='bold')
        
        # 1. 内容长度与评分关系
        axes[0, 0].scatter(self.df['content_length'], self.df['qwen_score'], 
                          alpha=0.6, color='blue', s=30)
        
        # 添加趋势线
        z = np.polyfit(self.df['content_length'], self.df['qwen_score'], 1)
        p = np.poly1d(z)
        axes[0, 0].plot(self.df['content_length'], p(self.df['content_length']), 
                       "r--", alpha=0.8, linewidth=2)
        
        correlation = self.df['content_length'].corr(self.df['qwen_score'])
        axes[0, 0].set_title(f'内容长度与评分关系 (相关性: {correlation:.3f})')
        axes[0, 0].set_xlabel('内容长度 (字符)')
        axes[0, 0].set_ylabel('Qwen评分')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 评分区间分布
        score_bins = pd.cut(self.df['qwen_score'], bins=5)
        bin_counts = score_bins.value_counts().sort_index()
        axes[0, 1].bar(range(len(bin_counts)), bin_counts.values, 
                      color='green', alpha=0.7)
        axes[0, 1].set_title('评分区间分布')
        axes[0, 1].set_xlabel('评分区间')
        axes[0, 1].set_ylabel('数量')
        axes[0, 1].set_xticks(range(len(bin_counts)))
        axes[0, 1].set_xticklabels([f'{interval.left:.2f}-{interval.right:.2f}' 
                                   for interval in bin_counts.index], rotation=45)
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 时间趋势分析 (如果有时间数据)
        try:
            self.df['publish_date'] = pd.to_datetime(self.df['publish_date'])
            self.df['year_month'] = self.df['publish_date'].dt.to_period('M')
            time_scores = self.df.groupby('year_month')['qwen_score'].agg(['mean', 'count'])
            
            # 只显示数据量>=5的月份
            time_scores = time_scores[time_scores['count'] >= 5]
            
            if len(time_scores) > 1:
                axes[1, 0].plot(range(len(time_scores)), time_scores['mean'], 
                               marker='o', linewidth=2, markersize=6, color='purple')
                axes[1, 0].set_title('时间趋势分析')
                axes[1, 0].set_xlabel('时间')
                axes[1, 0].set_ylabel('平均评分')
                axes[1, 0].set_xticks(range(len(time_scores)))
                axes[1, 0].set_xticklabels([str(period) for period in time_scores.index], 
                                          rotation=45)
                axes[1, 0].grid(True, alpha=0.3)
            else:
                axes[1, 0].text(0.5, 0.5, '时间数据不足\n无法生成趋势图', 
                               ha='center', va='center', fontsize=12)
                axes[1, 0].set_title('时间趋势分析')
        except:
            axes[1, 0].text(0.5, 0.5, '时间数据格式错误\n无法生成趋势图', 
                           ha='center', va='center', fontsize=12)
            axes[1, 0].set_title('时间趋势分析')
        
        # 4. 质量指标汇总
        quality_metrics = {
            '高质量数据 (≥9.0)': len(self.df[self.df['qwen_score'] >= 9.0]),
            '中等质量 (8.0-9.0)': len(self.df[(self.df['qwen_score'] >= 8.0) & 
                                           (self.df['qwen_score'] < 9.0)]),
            '较低质量 (<8.0)': len(self.df[self.df['qwen_score'] < 8.0]),
            '异常长度 (>2000字符)': len(self.df[self.df['content_length'] > 2000]),
            '异常短文 (<200字符)': len(self.df[self.df['content_length'] < 200])
        }
        
        metrics_text = "质量指标汇总:\n\n"
        for metric, value in quality_metrics.items():
            percentage = (value / len(self.df)) * 100
            metrics_text += f"{metric}: {value} ({percentage:.1f}%)\n"
        
        axes[1, 1].text(0.1, 0.5, metrics_text, fontsize=11, verticalalignment='center',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.7))
        axes[1, 1].set_title('质量指标汇总')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        output_path = self.output_dir / "quality_trends.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ 质量趋势图已保存: {output_path}")

def main():
    """主函数"""
    print("🎨 USTB数据科学专家 - 数据可视化生成")
    print("="*60)
    
    visualizer = DataVisualizer()
    
    # 加载数据
    if not visualizer.load_data():
        return
    
    # 生成4个必需的可视化图表
    visualizer.create_score_distribution()
    visualizer.create_category_analysis()
    visualizer.create_quality_trends()
    
    print("\n" + "="*60)
    print("✅ 数据可视化生成完成")
    print(f"📁 输出目录: {visualizer.output_dir}")
    print("📋 下一步: 创建质量监控仪表板")
    print("="*60)

if __name__ == "__main__":
    main()
