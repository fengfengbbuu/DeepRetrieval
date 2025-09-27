#!/usr/bin/env python3
"""
数据集划分脚本
将 train_parquet_all.final.jsonl 按照 5:1:1 的比例划分为 train, dev, test 三个子集
"""

import json
import random
import os
from pathlib import Path

def load_jsonl(file_path):
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def save_jsonl(data, file_path):
    """保存数据到JSONL文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def split_dataset(input_file, output_dir, train_ratio=5, dev_ratio=1, test_ratio=1):
    """
    划分数据集
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        train_ratio, dev_ratio, test_ratio: 训练集、验证集、测试集的比例
    """
    print(f"正在加载数据集: {input_file}")
    data = load_jsonl(input_file)
    total_samples = len(data)
    print(f"总样本数: {total_samples}")
    
    # 设置随机种子确保结果可重现
    random.seed(42)
    
    # 打乱数据
    print("正在打乱数据...")
    shuffled_data = data.copy()
    random.shuffle(shuffled_data)
    
    # 计算各集合的大小
    total_ratio = train_ratio + dev_ratio + test_ratio
    train_size = int(total_samples * train_ratio / total_ratio)
    dev_size = int(total_samples * dev_ratio / total_ratio)
    test_size = total_samples - train_size - dev_size  # 确保所有样本都被分配
    
    print(f"划分比例: train={train_ratio}:dev={dev_ratio}:test={test_ratio}")
    print(f"实际划分: train={train_size}, dev={dev_size}, test={test_size}")
    
    # 划分数据
    train_data = shuffled_data[:train_size]
    dev_data = shuffled_data[train_size:train_size + dev_size]
    test_data = shuffled_data[train_size + dev_size:]
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存划分后的数据
    splits = [
        ('train', train_data, train_size),
        ('dev', dev_data, dev_size),
        ('test', test_data, test_size)
    ]
    
    for split_name, split_data, split_size in splits:
        output_file = os.path.join(output_dir, f"{split_name}_{split_size}.jsonl")
        print(f"正在保存 {split_name} 集到: {output_file}")
        save_jsonl(split_data, output_file)
        print(f"{split_name} 集保存完成，样本数: {len(split_data)}")
    
    # 验证划分结果
    print("\n=== 划分结果验证 ===")
    total_split = len(train_data) + len(dev_data) + len(test_data)
    print(f"原始样本数: {total_samples}")
    print(f"划分后样本数: {total_split}")
    print(f"样本数是否一致: {total_samples == total_split}")
    
    return {
        'train': len(train_data),
        'dev': len(dev_data), 
        'test': len(test_data),
        'total': total_samples
    }

if __name__ == "__main__":
    # 设置路径
    # input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.final.jsonl"
    # input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.final.message.jsonl"
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/train_parquet_all.final.message.jsonl"

    # output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/split"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/split"
    
    print("开始数据集划分任务")
    print("=" * 50)
    
    # 执行划分
    # result = split_dataset(input_file, output_dir)
    result = split_dataset(input_file, output_dir, train_ratio=3767, dev_ratio=128, test_ratio=0)
    
    print("=" * 50)
    print("数据集划分完成!")
    print(f"最终结果: {result}")
