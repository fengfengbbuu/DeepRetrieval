#!/usr/bin/env python3
"""
分析summary CSV文件并生成统计图表
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from pathlib import Path
import re
from typing import List, Dict, Tuple
import numpy as np

def find_summary_files(root_dir: str) -> List[Dict]:
    """
    查找所有符合要求的summary CSV文件
    
    Args:
        root_dir: 根目录路径
        
    Returns:
        包含文件信息的字典列表
    """
    files_info = []
    
    # 查找所有global_step_*目录
    global_step_pattern = os.path.join(root_dir, "global_step_*")
    global_step_dirs = glob.glob(global_step_pattern)
    
    for global_step_dir in global_step_dirs:
        # 提取step_num
        step_match = re.search(r'global_step_(\d+)', global_step_dir)
        if not step_match:
            continue
        step_num = int(step_match.group(1))
        
        # 查找日期目录
        date_pattern = os.path.join(global_step_dir, "*")
        date_dirs = glob.glob(date_pattern)
        
        for date_dir in date_dirs:
            date_name = os.path.basename(date_dir)
            
            # 查找cot_ncot目录 (wcot 或 wocot)
            cot_pattern = os.path.join(date_dir, "*")
            cot_dirs = glob.glob(cot_pattern)
            
            for cot_dir in cot_dirs:
                cot_type = os.path.basename(cot_dir)
                if cot_type not in ['wcot', 'wocot']:
                    continue
                
                # 查找analyze目录下的summary CSV文件
                analyze_dir = os.path.join(cot_dir, "analyze")
                if not os.path.exists(analyze_dir):
                    continue
                
                summary_pattern = os.path.join(analyze_dir, "*summary*.csv")
                summary_files = glob.glob(summary_pattern)
                
                for summary_file in summary_files:
                    files_info.append({
                        'file_path': summary_file,
                        'step_num': step_num,
                        'date': date_name,
                        'cot_type': cot_type
                    })
    
    return files_info

def load_and_process_data(files_info: List[Dict]) -> pd.DataFrame:
    """
    加载并处理所有CSV文件的数据
    
    Args:
        files_info: 文件信息列表
        
    Returns:
        合并后的DataFrame
    """
    all_data = []
    
    for file_info in files_info:
        try:
            df = pd.read_csv(file_info['file_path'])
            
            # 添加元数据列
            df['step_num'] = file_info['step_num']
            df['date'] = file_info['date']
            df['cot_type'] = file_info['cot_type']
            df['file_path'] = file_info['file_path']
            
            all_data.append(df)
            print(f"成功加载文件: {file_info['file_path']}")
            
        except Exception as e:
            print(f"加载文件失败 {file_info['file_path']}: {e}")
    
    if not all_data:
        raise ValueError("没有成功加载任何数据文件")
    
    # 合并所有数据
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # 确保Rate列是数值类型
    if 'Rate' in combined_df.columns:
        combined_df['Rate'] = pd.to_numeric(combined_df['Rate'], errors='coerce')
    
    return combined_df

def create_visualizations(df: pd.DataFrame, output_dir: str):
    """
    创建各种统计图表
    
    Args:
        df: 数据DataFrame
        output_dir: 输出目录
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 按step_num和cot_type分组的折线图
    metrics = df['Metric'].unique()
    
    for metric in metrics:
        metric_data = df[df['Metric'] == metric]
        
        plt.figure(figsize=(12, 8))
        
        # 为每个cot_type创建一条线
        for cot_type in ['wcot', 'wocot']:
            cot_data = metric_data[metric_data['cot_type'] == cot_type]
            if not cot_data.empty:
                # 按step_num排序
                cot_data = cot_data.sort_values('step_num')
                plt.plot(cot_data['step_num'], cot_data['Rate'], 
                        marker='o', linewidth=2, markersize=6, 
                        label=f'{cot_type}', alpha=0.8)
        
        plt.title(f'{metric} 随训练步数变化趋势', fontsize=16, fontweight='bold')
        plt.xlabel('训练步数 (Global Step)', fontsize=12)
        plt.ylabel('比率 (Rate)', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存图片
        safe_metric_name = metric.replace(' ', '_').replace('(', '').replace(')', '')
        output_file = os.path.join(output_dir, f'{safe_metric_name}_trend.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"保存图表: {output_file}")
    
    # 2. 综合对比图
    plt.figure(figsize=(15, 10))
    
    # 选择几个重要指标
    important_metrics = ['Success Rate', 'Execution Accuracy Rate', 'Format Correct Rate']
    available_metrics = [m for m in important_metrics if m in metrics]
    
    if available_metrics:
        n_metrics = len(available_metrics)
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.flatten()
        
        for i, metric in enumerate(available_metrics):
            if i >= 4:  # 最多显示4个子图
                break
                
            metric_data = df[df['Metric'] == metric]
            
            for cot_type in ['wcot', 'wocot']:
                cot_data = metric_data[metric_data['cot_type'] == cot_type]
                if not cot_data.empty:
                    cot_data = cot_data.sort_values('step_num')
                    axes[i].plot(cot_data['step_num'], cot_data['Rate'], 
                               marker='o', linewidth=2, markersize=6, 
                               label=f'{cot_type}', alpha=0.8)
            
            axes[i].set_title(f'{metric}', fontsize=14, fontweight='bold')
            axes[i].set_xlabel('训练步数', fontsize=10)
            axes[i].set_ylabel('比率', fontsize=10)
            axes[i].legend(fontsize=10)
            axes[i].grid(True, alpha=0.3)
        
        # 隐藏多余的子图
        for i in range(len(available_metrics), 4):
            axes[i].set_visible(False)
        
        plt.suptitle('关键指标随训练步数变化对比', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, 'key_metrics_comparison.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"保存综合对比图: {output_file}")
    
    # 3. 热力图 - 显示不同step和cot_type的指标对比
    pivot_data = df.pivot_table(values='Rate', index='step_num', 
                               columns=['cot_type', 'Metric'], aggfunc='mean')
    
    plt.figure(figsize=(20, 10))
    sns.heatmap(pivot_data, annot=True, fmt='.3f', cmap='YlOrRd', 
                cbar_kws={'label': 'Rate'})
    plt.title('各指标在不同训练步数和CoT类型下的表现热力图', fontsize=16, fontweight='bold')
    plt.xlabel('CoT类型 - 指标', fontsize=12)
    plt.ylabel('训练步数', fontsize=12)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'metrics_heatmap.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"保存热力图: {output_file}")

def generate_summary_report(df: pd.DataFrame, output_dir: str):
    """
    生成数据摘要报告
    
    Args:
        df: 数据DataFrame
        output_dir: 输出目录
    """
    report_file = os.path.join(output_dir, 'analysis_summary.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("数据分析摘要报告\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"总数据文件数量: {len(df['file_path'].unique())}\n")
        f.write(f"训练步数范围: {df['step_num'].min()} - {df['step_num'].max()}\n")
        f.write(f"CoT类型: {', '.join(df['cot_type'].unique())}\n")
        f.write(f"指标数量: {len(df['Metric'].unique())}\n\n")
        
        f.write("各指标统计:\n")
        f.write("-" * 30 + "\n")
        
        for metric in df['Metric'].unique():
            metric_data = df[df['Metric'] == metric]
            f.write(f"\n{metric}:\n")
            f.write(f"  平均值: {metric_data['Rate'].mean():.4f}\n")
            f.write(f"  标准差: {metric_data['Rate'].std():.4f}\n")
            f.write(f"  最小值: {metric_data['Rate'].min():.4f}\n")
            f.write(f"  最大值: {metric_data['Rate'].max():.4f}\n")
            
            # 按CoT类型分组统计
            for cot_type in ['wcot', 'wocot']:
                cot_data = metric_data[metric_data['cot_type'] == cot_type]
                if not cot_data.empty:
                    f.write(f"  {cot_type} 平均值: {cot_data['Rate'].mean():.4f}\n")
    
    print(f"生成摘要报告: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='分析summary CSV文件并生成统计图表')
    parser.add_argument('--root_dir', required=True, help='根目录路径')
    parser.add_argument('--output_dir', required=True, help='输出目录路径')
    
    args = parser.parse_args()
    
    print(f"开始分析，根目录: {args.root_dir}")
    print(f"输出目录: {args.output_dir}")
    
    # 查找所有符合要求的文件
    print("\n正在查找summary文件...")
    files_info = find_summary_files(args.root_dir)
    
    if not files_info:
        print("未找到任何符合要求的summary文件")
        return
    
    print(f"找到 {len(files_info)} 个summary文件")
    
    # 加载和处理数据
    print("\n正在加载数据...")
    df = load_and_process_data(files_info)
    
    print(f"成功加载数据，共 {len(df)} 条记录")
    print(f"数据列: {list(df.columns)}")
    
    # 创建可视化图表
    print("\n正在生成图表...")
    create_visualizations(df, args.output_dir)
    
    # 生成摘要报告
    print("\n正在生成摘要报告...")
    generate_summary_report(df, args.output_dir)
    
    # 保存原始数据
    data_file = os.path.join(args.output_dir, 'combined_data.csv')
    df.to_csv(data_file, index=False, encoding='utf-8')
    print(f"保存合并数据: {data_file}")
    
    print(f"\n分析完成！结果保存在: {args.output_dir}")

if __name__ == "__main__":
    main()
