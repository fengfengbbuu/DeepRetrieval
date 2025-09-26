#!/usr/bin/env python3
"""
分析summary CSV文件并生成统计图表 - 改进版
支持 global_step_ 和 checkpoint- 两种路径模式
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

# 设置matplotlib后端，避免GUI问题
import matplotlib
matplotlib.use('Agg')

def setup_chinese_font():
    """设置中文字体支持"""
    try:
        # 尝试使用系统中文字体
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        # 如果中文字体不可用，使用英文标签
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

def find_summary_files(root_dir: str) -> List[Dict]:
    """
    查找所有符合要求的summary CSV文件
    支持两种路径模式：global_step_ 和 checkpoint-
    
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
                        'cot_type': cot_type,
                        'step_type': 'global_step'
                    })
    
    # 查找所有checkpoint-*目录
    checkpoint_pattern = os.path.join(root_dir, "checkpoint-*")
    checkpoint_dirs = glob.glob(checkpoint_pattern)
    
    for checkpoint_dir in checkpoint_dirs:
        # 提取step_num
        step_match = re.search(r'checkpoint-(\d+)', checkpoint_dir)
        if not step_match:
            continue
        step_num = int(step_match.group(1))
        
        # 查找日期目录
        date_pattern = os.path.join(checkpoint_dir, "*")
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
                        'cot_type': cot_type,
                        'step_type': 'checkpoint'
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
            df['step_type'] = file_info['step_type']
            df['file_path'] = file_info['file_path']
            
            all_data.append(df)
            print(f"Successfully loaded: {file_info['file_path']}")
            
        except Exception as e:
            print(f"Failed to load {file_info['file_path']}: {e}")
    
    if not all_data:
        raise ValueError("No data files loaded successfully")
    
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
    # 设置字体
    setup_chinese_font()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 按step_num和cot_type分组的折线图
    metrics = df['Metric'].unique()
    
    for metric in metrics:
        metric_data = df[df['Metric'] == metric]
        
        plt.figure(figsize=(12, 8))
        
        # 为每个cot_type和step_type组合创建一条线
        for cot_type in ['wcot', 'wocot']:
            for step_type in ['global_step', 'checkpoint']:
                cot_data = metric_data[
                    (metric_data['cot_type'] == cot_type) & 
                    (metric_data['step_type'] == step_type)
                ]
                if not cot_data.empty:
                    # 按step_num排序
                    cot_data = cot_data.sort_values('step_num')
                    label = f'{cot_type}_{step_type}' if len(df['step_type'].unique()) > 1 else cot_type
                    plt.plot(cot_data['step_num'], cot_data['Rate'], 
                            marker='o', linewidth=2, markersize=6, 
                            label=label, alpha=0.8)
        
        plt.title(f'{metric} Trend by Training Steps', fontsize=16, fontweight='bold')
        plt.xlabel('Training Steps', fontsize=12)
        plt.ylabel('Rate', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存图片
        safe_metric_name = metric.replace(' ', '_').replace('(', '').replace(')', '')
        output_file = os.path.join(output_dir, f'{safe_metric_name}_trend.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved chart: {output_file}")
    
    # 2. 综合对比图
    important_metrics = ['Success Rate', 'Execution Accuracy Rate', 'Format Correct Rate']
    available_metrics = [m for m in important_metrics if m in metrics]
    
    if available_metrics:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.flatten()
        
        for i, metric in enumerate(available_metrics):
            if i >= 4:  # 最多显示4个子图
                break
                
            metric_data = df[df['Metric'] == metric]
            
            for cot_type in ['wcot', 'wocot']:
                for step_type in ['global_step', 'checkpoint']:
                    cot_data = metric_data[
                        (metric_data['cot_type'] == cot_type) & 
                        (metric_data['step_type'] == step_type)
                    ]
                    if not cot_data.empty:
                        cot_data = cot_data.sort_values('step_num')
                        label = f'{cot_type}_{step_type}' if len(df['step_type'].unique()) > 1 else cot_type
                        axes[i].plot(cot_data['step_num'], cot_data['Rate'], 
                                   marker='o', linewidth=2, markersize=6, 
                                   label=label, alpha=0.8)
            
            axes[i].set_title(f'{metric}', fontsize=14, fontweight='bold')
            axes[i].set_xlabel('Training Steps', fontsize=10)
            axes[i].set_ylabel('Rate', fontsize=10)
            axes[i].legend(fontsize=10)
            axes[i].grid(True, alpha=0.3)
        
        # 隐藏多余的子图
        for i in range(len(available_metrics), 4):
            axes[i].set_visible(False)
        
        plt.suptitle('Key Metrics Comparison by Training Steps', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, 'key_metrics_comparison.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved comparison chart: {output_file}")
    
    # 3. 热力图 - 显示不同step和cot_type的指标对比
    try:
        pivot_data = df.pivot_table(values='Rate', index='step_num', 
                                   columns=['step_type', 'cot_type', 'Metric'], aggfunc='mean')
        
        plt.figure(figsize=(20, 10))
        sns.heatmap(pivot_data, annot=True, fmt='.3f', cmap='YlOrRd', 
                    cbar_kws={'label': 'Rate'})
        plt.title('Metrics Performance Heatmap by Training Steps, Step Type and CoT Type', 
                 fontsize=16, fontweight='bold')
        plt.xlabel('Step Type - CoT Type - Metric', fontsize=12)
        plt.ylabel('Training Steps', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, 'metrics_heatmap.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved heatmap: {output_file}")
    except Exception as e:
        print(f"Failed to create heatmap: {e}")
    
    # 4. 箱线图 - 显示各指标的分布
    important_metrics = ['Success Rate', 'Execution Accuracy Rate', 'Format Correct Rate', 'Valid JSON Rate']
    available_metrics = [m for m in important_metrics if m in metrics]
    
    if available_metrics:
        metric_data = df[df['Metric'].isin(available_metrics)]
        
        plt.figure(figsize=(12, 8))
        sns.boxplot(data=metric_data, x='Metric', y='Rate', hue='cot_type')
        plt.title('Distribution of Key Metrics by CoT Type', fontsize=16, fontweight='bold')
        plt.xlabel('Metric', fontsize=12)
        plt.ylabel('Rate', fontsize=12)
        plt.xticks(rotation=45)
        plt.legend(title='CoT Type', fontsize=10)
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, 'metrics_distribution.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved distribution chart: {output_file}")
    
    # 5. 按step_type分组的对比图
    if len(df['step_type'].unique()) > 1:
        plt.figure(figsize=(15, 10))
        
        # 选择几个重要指标
        important_metrics = ['Success Rate', 'Execution Accuracy Rate', 'Format Correct Rate']
        available_metrics = [m for m in important_metrics if m in metrics]
        
        if available_metrics:
            fig, axes = plt.subplots(1, len(available_metrics), figsize=(5*len(available_metrics), 6))
            if len(available_metrics) == 1:
                axes = [axes]
            
            for i, metric in enumerate(available_metrics):
                metric_data = df[df['Metric'] == metric]
                
                for cot_type in ['wcot', 'wocot']:
                    for step_type in ['global_step', 'checkpoint']:
                        cot_data = metric_data[
                            (metric_data['cot_type'] == cot_type) & 
                            (metric_data['step_type'] == step_type)
                        ]
                        if not cot_data.empty:
                            cot_data = cot_data.sort_values('step_num')
                            label = f'{cot_type}_{step_type}'
                            axes[i].plot(cot_data['step_num'], cot_data['Rate'], 
                                       marker='o', linewidth=2, markersize=6, 
                                       label=label, alpha=0.8)
                
                axes[i].set_title(f'{metric}', fontsize=14, fontweight='bold')
                axes[i].set_xlabel('Training Steps', fontsize=10)
                axes[i].set_ylabel('Rate', fontsize=10)
                axes[i].legend(fontsize=10)
                axes[i].grid(True, alpha=0.3)
            
            plt.suptitle('Metrics Comparison by Step Type and CoT Type', fontsize=16, fontweight='bold')
            plt.tight_layout()
            
            output_file = os.path.join(output_dir, 'step_type_comparison.png')
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved step type comparison chart: {output_file}")

def generate_summary_report(df: pd.DataFrame, output_dir: str):
    """
    生成数据摘要报告
    
    Args:
        df: 数据DataFrame
        output_dir: 输出目录
    """
    report_file = os.path.join(output_dir, 'analysis_summary.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Data Analysis Summary Report\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total data files: {len(df['file_path'].unique())}\n")
        f.write(f"Training steps range: {df['step_num'].min()} - {df['step_num'].max()}\n")
        f.write(f"Step types: {', '.join(df['step_type'].unique())}\n")
        f.write(f"CoT types: {', '.join(df['cot_type'].unique())}\n")
        f.write(f"Number of metrics: {len(df['Metric'].unique())}\n\n")
        
        f.write("Metrics Statistics:\n")
        f.write("-" * 30 + "\n")
        
        for metric in df['Metric'].unique():
            metric_data = df[df['Metric'] == metric]
            f.write(f"\n{metric}:\n")
            f.write(f"  Mean: {metric_data['Rate'].mean():.4f}\n")
            f.write(f"  Std: {metric_data['Rate'].std():.4f}\n")
            f.write(f"  Min: {metric_data['Rate'].min():.4f}\n")
            f.write(f"  Max: {metric_data['Rate'].max():.4f}\n")
            
            # 按step_type和CoT类型分组统计
            for step_type in df['step_type'].unique():
                for cot_type in ['wcot', 'wocot']:
                    cot_data = metric_data[
                        (metric_data['step_type'] == step_type) & 
                        (metric_data['cot_type'] == cot_type)
                    ]
                    if not cot_data.empty:
                        f.write(f"  {step_type}_{cot_type} mean: {cot_data['Rate'].mean():.4f}\n")
    
    print(f"Generated summary report: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='Analyze summary CSV files and generate statistical charts')
    parser.add_argument('--root_dir', required=True, help='Root directory path')
    parser.add_argument('--output_dir', required=True, help='Output directory path')
    
    args = parser.parse_args()
    
    print(f"Starting analysis, root directory: {args.root_dir}")
    print(f"Output directory: {args.output_dir}")
    
    # 查找所有符合要求的文件
    print("\nSearching for summary files...")
    files_info = find_summary_files(args.root_dir)
    
    if not files_info:
        print("No summary files found matching the requirements")
        return
    
    print(f"Found {len(files_info)} summary files")
    
    # 加载和处理数据
    print("\nLoading data...")
    df = load_and_process_data(files_info)
    
    print(f"Successfully loaded data, {len(df)} records total")
    print(f"Data columns: {list(df.columns)}")
    
    # 创建可视化图表
    print("\nGenerating charts...")
    create_visualizations(df, args.output_dir)
    
    # 生成摘要报告
    print("\nGenerating summary report...")
    generate_summary_report(df, args.output_dir)
    
    # 保存原始数据
    data_file = os.path.join(args.output_dir, 'combined_data.csv')
    df.to_csv(data_file, index=False, encoding='utf-8')
    print(f"Saved combined data: {data_file}")
    
    print(f"\nAnalysis completed! Results saved in: {args.output_dir}")

if __name__ == "__main__":
    main()
