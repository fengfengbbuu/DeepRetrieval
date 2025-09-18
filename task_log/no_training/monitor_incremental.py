#!/usr/bin/env python3
"""
监控增量保存进度脚本
"""

import json
import time
import os
from datetime import datetime

def monitor_incremental_progress():
    """监控增量保存进度"""
    log_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference.log"
    success_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference_results_success.jsonl"
    failed_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference_results_failed.jsonl"
    
    if not os.path.exists(log_file):
        print("日志文件不存在")
        return
    
    # 统计日志中的进度
    processed_items = 0
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if "Processing item" in line:
                parts = line.split("Processing item ")[1].split("/")[0]
                processed_items = max(processed_items, int(parts))
    
    # 统计已保存的结果
    saved_success = 0
    saved_failed = 0
    
    if os.path.exists(success_file):
        with open(success_file, 'r', encoding='utf-8') as f:
            saved_success = sum(1 for line in f if line.strip())
    
    if os.path.exists(failed_file):
        with open(failed_file, 'r', encoding='utf-8') as f:
            saved_failed = sum(1 for line in f if line.strip())
    
    total_saved = saved_success + saved_failed
    total_items = 2147
    progress_percent = (processed_items / total_items) * 100 if total_items > 0 else 0
    save_percent = (total_saved / total_items) * 100 if total_items > 0 else 0
    
    print(f"增量保存监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    print(f"处理进度: {processed_items}/{total_items} ({progress_percent:.1f}%)")
    print(f"已保存结果: {total_saved}/{total_items} ({save_percent:.1f}%)")
    print(f"  - 成功: {saved_success}")
    print(f"  - 失败: {saved_failed}")
    print(f"内存中待保存: {processed_items - total_saved}")
    
    # 显示文件大小
    if os.path.exists(success_file):
        size = os.path.getsize(success_file) / 1024 / 1024  # MB
        print(f"成功结果文件大小: {size:.2f} MB")
    
    if os.path.exists(failed_file):
        size = os.path.getsize(failed_file) / 1024 / 1024  # MB
        print(f"失败结果文件大小: {size:.2f} MB")
    
    # 估算剩余时间
    if processed_items > 0:
        remaining_items = total_items - processed_items
        estimated_minutes = remaining_items / 30  # 每分钟30个请求
        print(f"估算剩余时间: {estimated_minutes:.1f} 分钟")
    
    print(f"=" * 50)

if __name__ == "__main__":
    monitor_incremental_progress()
