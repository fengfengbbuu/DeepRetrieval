#!/usr/bin/env python3
"""
临时脚本：分析 TARGET_FILE 的数据结构
"""

import pandas as pd
import os

def analyze_data_structure():
    """分析 parquet 文件的数据结构"""
    target_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/train.parquet"
    
    print(f"正在分析文件: {target_file}")
    
    # 检查文件是否存在
    if not os.path.exists(target_file):
        print(f"错误：文件不存在 {target_file}")
        return
    
    try:
        # 读取 parquet 文件
        df = pd.read_parquet(target_file)
        
        print(f"数据形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        print("\n数据类型:")
        print(df.dtypes)
        
        print("\n前几行数据:")
        print(df.head())
        
        # 检查是否有 reward_model.ground_truth.target 字段
        if 'reward_model' in df.columns:
            print("\nreward_model 字段信息:")
            print(df['reward_model'].head())
            
            # 如果 reward_model 是字典类型，检查其结构
            if isinstance(df['reward_model'].iloc[0], dict):
                sample_reward = df['reward_model'].iloc[0]
                print(f"reward_model 字典键: {list(sample_reward.keys())}")
                
                if 'ground_truth' in sample_reward:
                    print(f"ground_truth 键: {list(sample_reward['ground_truth'].keys())}")
                    
                    if 'target' in sample_reward['ground_truth']:
                        print(f"找到 target 字段！")
                        print(f"示例 target: {sample_reward['ground_truth']['target']}")
        
        # 检查 db_path 字段
        if 'db_path' in df.columns:
            print(f"\ndb_path 字段示例:")
            print(df['db_path'].head())
        
    except Exception as e:
        print(f"读取文件时出错: {e}")

if __name__ == "__main__":
    analyze_data_structure()