#!/usr/bin/env python3
"""
来自任务：`sft_eval_analyze`
Script to extract evaluation metrics from all checkpoint reports
and create visualization data for training progress analysis.
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import re
from datetime import datetime

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object for sorting"""
    return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def extract_step_from_model_name(model_name):
    """Extract step number from model name like 'model-step50'"""
    match = re.search(r'model-step(\d+)', model_name)
    return int(match.group(1)) if match else None

def extract_metrics_from_json(json_file_path):
    """Extract metrics from a single JSON report file"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metrics = {}
        metrics['overall_score'] = data.get('score', 0)
        
        # Extract individual metrics
        for metric in data.get('metrics', []):
            metric_name = metric.get('name', '')
            metric_score = metric.get('score', 0)
            metrics[metric_name] = metric_score
        
        return metrics
    except Exception as e:
        print(f"Error reading {json_file_path}: {e}")
        return {}

def analyze_eval_directory(eval_dir):
    """Analyze the entire evaluation directory structure"""
    eval_path = Path(eval_dir)
    
    if not eval_path.exists():
        print(f"Directory {eval_dir} does not exist!")
        return None
    
    # Get all timestamp directories and sort them
    timestamp_dirs = []
    for item in eval_path.iterdir():
        if item.is_dir() and re.match(r'\d{8}_\d{6}', item.name):
            timestamp_dirs.append(item.name)
    
    # Sort by timestamp
    timestamp_dirs.sort(key=parse_timestamp)
    
    all_data = []
    
    for timestamp in timestamp_dirs:
        timestamp_path = eval_path / timestamp
        reports_path = timestamp_path / 'reports'
        
        if not reports_path.exists():
            print(f"Reports directory not found in {timestamp}")
            continue
        
        # Find model-step directories
        for model_dir in reports_path.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith('model-step'):
                step = extract_step_from_model_name(model_dir.name)
                
                # Look for JSON files in the model directory
                for json_file in model_dir.glob('*.json'):
                    metrics = extract_metrics_from_json(json_file)
                    if metrics:
                        metrics['timestamp'] = timestamp
                        metrics['step'] = step
                        metrics['model_name'] = model_dir.name
                        all_data.append(metrics)
    
    return all_data, timestamp_dirs

def create_visualization(data, output_dir):
    """Create line plots for training progress"""
    if not data:
        print("No data to visualize!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Sort by step number
    df = df.sort_values('step')
    
    # Set up the plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Training Progress: Evaluation Metrics Over Checkpoints', fontsize=16, fontweight='bold')
    
    # Define metric groups for better visualization
    bleu_metrics = [col for col in df.columns if 'bleu' in col.lower()]
    rouge_metrics = [col for col in df.columns if 'rouge' in col.lower()]
    
    # Plot 1: BLEU scores
    ax1 = axes[0, 0]
    for metric in bleu_metrics:
        if metric in df.columns:
            ax1.plot(df['step'], df[metric], marker='o', linewidth=2, label=metric)
    ax1.set_title('BLEU Scores', fontweight='bold')
    ax1.set_xlabel('Training Step')
    ax1.set_ylabel('Score')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: ROUGE Recall scores
    ax2 = axes[0, 1]
    rouge_r_metrics = [col for col in rouge_metrics if col.endswith('-R')]
    for metric in rouge_r_metrics:
        if metric in df.columns:
            ax2.plot(df['step'], df[metric], marker='s', linewidth=2, label=metric)
    ax2.set_title('ROUGE Recall Scores', fontweight='bold')
    ax2.set_xlabel('Training Step')
    ax2.set_ylabel('Score')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: ROUGE Precision scores
    ax3 = axes[1, 0]
    rouge_p_metrics = [col for col in rouge_metrics if col.endswith('-P')]
    for metric in rouge_p_metrics:
        if metric in df.columns:
            ax3.plot(df['step'], df[metric], marker='^', linewidth=2, label=metric)
    ax3.set_title('ROUGE Precision Scores', fontweight='bold')
    ax3.set_xlabel('Training Step')
    ax3.set_ylabel('Score')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: ROUGE F1 scores
    ax4 = axes[1, 1]
    rouge_f_metrics = [col for col in rouge_metrics if col.endswith('-F')]
    for metric in rouge_f_metrics:
        if metric in df.columns:
            ax4.plot(df['step'], df[metric], marker='d', linewidth=2, label=metric)
    ax4.set_title('ROUGE F1 Scores', fontweight='bold')
    ax4.set_xlabel('Training Step')
    ax4.set_ylabel('Score')
    ax4.legend()
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    plot_path = Path(output_dir) / 'training_progress_metrics.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    # Also create a comprehensive single plot with better visual distinction
    plt.figure(figsize=(18, 12))
    
    # Plot all metrics in one figure
    all_metrics = [col for col in df.columns if col not in ['timestamp', 'step', 'model_name', 'overall_score']]
    
    # Define better color palette and line styles for better distinction
    colors = plt.cm.tab20(np.linspace(0, 1, len(all_metrics)))
    line_styles = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--']
    markers = ['o', 's', '^', 'v', 'D', 'p', '*', 'h', 'H', '8', 'P', 'X', 'd', '>']
    
    for i, metric in enumerate(all_metrics):
        plt.plot(df['step'], df[metric], 
                color=colors[i], 
                linestyle=line_styles[i % len(line_styles)],
                marker=markers[i % len(markers)],
                linewidth=2.5, 
                markersize=6,
                label=metric, 
                alpha=0.9,
                markevery=1)
    
    plt.title('All Evaluation Metrics Over Training Steps', fontsize=18, fontweight='bold', pad=20)
    plt.xlabel('Training Step', fontsize=14, fontweight='bold')
    plt.ylabel('Score', fontsize=14, fontweight='bold')
    
    # Improve legend layout
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', 
              fontsize=10, frameon=True, fancybox=True, shadow=True,
              ncol=1, columnspacing=0.5, handlelength=2)
    
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()
    
    comprehensive_plot_path = Path(output_dir) / 'all_metrics_comprehensive.png'
    plt.savefig(comprehensive_plot_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive plot saved to: {comprehensive_plot_path}")
    
    return df

def main():
    # Define paths
    eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_2ep_16bs_2accum/v0-20250914-133424/eval"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/task_log/analyze"
    
    print("Starting evaluation data analysis...")
    print(f"Target directory: {eval_dir}")
    
    # Analyze the directory
    data, timestamp_dirs = analyze_eval_directory(eval_dir)
    
    if not data:
        print("No evaluation data found!")
        return
    
    print(f"Found {len(data)} evaluation reports")
    print(f"Timestamps found: {timestamp_dirs}")
    
    # Create visualizations
    df = create_visualization(data, output_dir)
    
    # Save raw data to CSV
    if df is not None:
        csv_path = Path(output_dir) / 'evaluation_metrics_data.csv'
        df.to_csv(csv_path, index=False)
        print(f"Raw data saved to: {csv_path}")
        
        # Print summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Number of checkpoints: {len(df)}")
        print(f"Step range: {df['step'].min()} - {df['step'].max()}")
        print(f"Timestamp range: {df['timestamp'].min()} - {df['timestamp'].max()}")
        
        print("\n=== Metric Summary ===")
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        summary_stats = df[numeric_cols].describe()
        print(summary_stats)

if __name__ == "__main__":
    main()
