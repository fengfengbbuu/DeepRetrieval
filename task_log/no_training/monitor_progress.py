#!/usr/bin/env python3
"""
监控推理进度脚本
"""

import json
import time
import os
from datetime import datetime

def monitor_progress():
    """监控推理进度"""
    log_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference.log"
    
    if not os.path.exists(log_file):
        print("日志文件不存在")
        return
    
    # 读取日志文件
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 统计进度
    processed_items = 0
    successful_items = 0
    failed_items = 0
    
    for line in lines:
        if "Processing item" in line:
            # 提取处理的项目编号
            parts = line.split("Processing item ")[1].split("/")[0]
            processed_items = max(processed_items, int(parts))
        elif "processed successfully" in line:
            successful_items += 1
        elif "failed after" in line:
            failed_items += 1
    
    total_items = 2147
    progress_percent = (processed_items / total_items) * 100 if total_items > 0 else 0
    
    print(f"推理进度监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"已处理项目: {processed_items}/{total_items} ({progress_percent:.1f}%)")
    print(f"成功: {successful_items}")
    print(f"失败: {failed_items}")
    
    # 估算剩余时间
    if processed_items > 0:
        # 假设每分钟处理30个项目
        remaining_items = total_items - processed_items
        estimated_minutes = remaining_items / 30
        print(f"估算剩余时间: {estimated_minutes:.1f} 分钟")

if __name__ == "__main__":
    monitor_progress()

