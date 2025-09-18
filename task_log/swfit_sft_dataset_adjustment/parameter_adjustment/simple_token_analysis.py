#!/usr/bin/env python3
"""
简化的Token长度统计分析脚本
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from transformers import AutoTokenizer
import os

# 配置
MODEL_PATH = "/root/data3/Qwen.Qwen2.5-0.5B-Instruct"
DATA_FILE = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.final.message.jsonl"
OUTPUT_DIR = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/parameter_adjustment"

def main():
    print("开始Token长度统计分析...")
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载tokenizer
    print("正在加载tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    print(f"Tokenizer加载完成")
    
    # 加载数据集（只处理前1000条数据进行测试）
    print(f"正在加载数据集: {DATA_FILE}")
    data = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # if line_num > 1000:  # 只处理前1000条
            #     break
            try:
                item = json.loads(line.strip())
                data.append(item)
            except json.JSONDecodeError as e:
                print(f"警告: 第{line_num}行JSON解析失败: {e}")
                continue
    
    print(f"数据集加载完成，共{len(data)}条数据")
    
    # 分析token长度
    print("正在分析token长度...")
    total_token_lengths = []
    input_token_lengths = []
    output_token_lengths = []
    
    for i, item in enumerate(data):
        if i % 100 == 0:
            print(f"已处理 {i}/{len(data)} 条数据")
        
        # 获取messages字段
        messages = item.get('messages', [])
        
        # 处理messages - 分别统计input和output
        input_content_parts = []
        output_content_parts = []
        all_content_parts = []
        
        for msg in messages:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg['content']
                role = msg.get('role', '')
                
                all_content_parts.append(content)
                
                # 根据role分类
                if role in ['system', 'user']:
                    input_content_parts.append(content)
                elif role == 'assistant':
                    output_content_parts.append(content)
            elif isinstance(msg, str):
                all_content_parts.append(msg)
                # 对于字符串类型的消息，无法确定role，暂时归类到input
                input_content_parts.append(msg)
        
        # 计算总长度
        total_text = " ".join(all_content_parts)
        if total_text:
            total_tokens = tokenizer.encode(total_text, add_special_tokens=True)
            total_len = len(total_tokens)
        else:
            total_len = 0
        
        # 计算input长度
        input_text = " ".join(input_content_parts)
        if input_text:
            input_tokens = tokenizer.encode(input_text, add_special_tokens=True)
            input_len = len(input_tokens)
        else:
            input_len = 0
        
        # 计算output长度
        output_text = " ".join(output_content_parts)
        if output_text:
            output_tokens = tokenizer.encode(output_text, add_special_tokens=True)
            output_len = len(output_tokens)
        else:
            output_len = 0
        
        total_token_lengths.append(total_len)
        input_token_lengths.append(input_len)
        output_token_lengths.append(output_len)
    
    print(f"Token长度分析完成，共处理{len(total_token_lengths)}条数据")
    
    # 计算统计信息
    total_lengths = np.array(total_token_lengths)
    input_lengths = np.array(input_token_lengths)
    output_lengths = np.array(output_token_lengths)
    
    def calculate_stats(lengths):
        return {
            'count': len(lengths),
            'mean': np.mean(lengths),
            'median': np.median(lengths),
            'std': np.std(lengths),
            'min': np.min(lengths),
            'max': np.max(lengths),
            'percentile_50': np.percentile(lengths, 50),
            'percentile_75': np.percentile(lengths, 75),
            'percentile_90': np.percentile(lengths, 90),
            'percentile_95': np.percentile(lengths, 95),
            'percentile_99': np.percentile(lengths, 99),
        }
    
    total_stats = calculate_stats(total_lengths)
    input_stats = calculate_stats(input_lengths)
    output_stats = calculate_stats(output_lengths)
    
    # 打印统计信息
    print("\n=== Total Token Length Statistics ===")
    print(f"Sample Count: {total_stats['count']:,}")
    print(f"Mean: {total_stats['mean']:.2f}")
    print(f"Median: {total_stats['median']:.2f}")
    print(f"Std Dev: {total_stats['std']:.2f}")
    print(f"Min: {total_stats['min']}")
    print(f"Max: {total_stats['max']}")
    print(f"50th Percentile: {total_stats['percentile_50']:.2f}")
    print(f"75th Percentile: {total_stats['percentile_75']:.2f}")
    print(f"90th Percentile: {total_stats['percentile_90']:.2f}")
    print(f"95th Percentile: {total_stats['percentile_95']:.2f}")
    print(f"99th Percentile: {total_stats['percentile_99']:.2f}")
    
    print("\n=== Input Token Length Statistics (System + User) ===")
    print(f"Sample Count: {input_stats['count']:,}")
    print(f"Mean: {input_stats['mean']:.2f}")
    print(f"Median: {input_stats['median']:.2f}")
    print(f"Std Dev: {input_stats['std']:.2f}")
    print(f"Min: {input_stats['min']}")
    print(f"Max: {input_stats['max']}")
    print(f"50th Percentile: {input_stats['percentile_50']:.2f}")
    print(f"75th Percentile: {input_stats['percentile_75']:.2f}")
    print(f"90th Percentile: {input_stats['percentile_90']:.2f}")
    print(f"95th Percentile: {input_stats['percentile_95']:.2f}")
    print(f"99th Percentile: {input_stats['percentile_99']:.2f}")
    
    print("\n=== Output Token Length Statistics (Assistant) ===")
    print(f"Sample Count: {output_stats['count']:,}")
    print(f"Mean: {output_stats['mean']:.2f}")
    print(f"Median: {output_stats['median']:.2f}")
    print(f"Std Dev: {output_stats['std']:.2f}")
    print(f"Min: {output_stats['min']}")
    print(f"Max: {output_stats['max']}")
    print(f"50th Percentile: {output_stats['percentile_50']:.2f}")
    print(f"75th Percentile: {output_stats['percentile_75']:.2f}")
    print(f"90th Percentile: {output_stats['percentile_90']:.2f}")
    print(f"95th Percentile: {output_stats['percentile_95']:.2f}")
    print(f"99th Percentile: {output_stats['percentile_99']:.2f}")
    
    # 绘制直方图
    print("正在绘制直方图...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Token Length Distribution Analysis', fontsize=16)
    
    # 总长度分布
    axes[0, 0].hist(total_lengths, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    axes[0, 0].set_xlabel('Token Length')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Total Token Length Distribution')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 输入长度分布
    axes[0, 1].hist(input_lengths, bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
    axes[0, 1].set_xlabel('Token Length')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Input Token Length Distribution (System + User)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 输出长度分布
    axes[1, 0].hist(output_lengths, bins=30, alpha=0.7, color='lightcoral', edgecolor='black')
    axes[1, 0].set_xlabel('Token Length')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Output Token Length Distribution (Assistant)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 对比图
    axes[1, 1].hist(total_lengths, bins=30, alpha=0.5, color='skyblue', label='Total', edgecolor='black')
    axes[1, 1].hist(input_lengths, bins=30, alpha=0.5, color='lightgreen', label='Input', edgecolor='black')
    axes[1, 1].hist(output_lengths, bins=30, alpha=0.5, color='lightcoral', label='Output', edgecolor='black')
    axes[1, 1].set_xlabel('Token Length')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Comparison of Token Length Distributions')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图片
    output_path = os.path.join(OUTPUT_DIR, 'token_length_histogram.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"直方图已保存到: {output_path}")
    plt.close()
    
    # 保存统计信息（转换为Python原生类型）
    stats_file = os.path.join(OUTPUT_DIR, 'token_length_statistics.json')
    
    def make_serializable(stats_dict):
        return {k: float(v) if isinstance(v, (np.integer, np.floating)) else int(v) if isinstance(v, np.integer) else v for k, v in stats_dict.items()}
    
    all_stats = {
        'total': make_serializable(total_stats),
        'input': make_serializable(input_stats),
        'output': make_serializable(output_stats)
    }
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, indent=2, ensure_ascii=False)
    print(f"统计信息已保存到: {stats_file}")
    
    print("\n分析完成！")

if __name__ == "__main__":
    main()
