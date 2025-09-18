#!/usr/bin/env python3
"""
数据分析脚本：分析 train_parquet_all.jsonl 数据格式和字段信息
"""

import json
import os
from collections import defaultdict, Counter
from typing import Dict, List, Any

def analyze_data_format(file_path: str) -> Dict[str, Any]:
    """分析数据格式和字段信息"""
    print(f"正在分析文件: {file_path}")
    
    stats = {
        'total_records': 0,
        'field_stats': defaultdict(int),
        'meta_info_fields': defaultdict(int),
        'response_lengths': [],
        'db_ids': Counter(),
        'data_sources': Counter(),
        'sample_records': []
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 100:  # 只分析前100条记录
                break
                
            try:
                record = json.loads(line.strip())
                stats['total_records'] += 1
                
                # 分析字段
                for field in record.keys():
                    stats['field_stats'][field] += 1
                
                # 分析 meta_info 字段
                if 'meta_info' in record:
                    meta_info = record['meta_info']
                    for field in meta_info.keys():
                        stats['meta_info_fields'][field] += 1
                    
                    # 统计 db_id 和 data_source
                    if 'db_id' in meta_info:
                        stats['db_ids'][meta_info['db_id']] += 1
                    if 'data_source' in meta_info:
                        stats['data_sources'][meta_info['data_source']] += 1
                
                # 分析 response 长度
                if 'response' in record:
                    stats['response_lengths'].append(len(record['response']))
                
                # 保存样本记录
                if i < 3:
                    stats['sample_records'].append(record)
                    
            except json.JSONDecodeError as e:
                print(f"JSON解析错误在第{i+1}行: {e}")
                continue
    
    return stats

def print_analysis_results(stats: Dict[str, Any]):
    """打印分析结果"""
    print("\n" + "="*50)
    print("数据分析结果")
    print("="*50)
    
    print(f"\n总记录数: {stats['total_records']}")
    
    print(f"\n字段统计:")
    for field, count in stats['field_stats'].items():
        print(f"  {field}: {count}")
    
    print(f"\nmeta_info 字段统计:")
    for field, count in stats['meta_info_fields'].items():
        print(f"  {field}: {count}")
    
    print(f"\n数据库ID统计 (前10个):")
    for db_id, count in stats['db_ids'].most_common(10):
        print(f"  {db_id}: {count}")
    
    print(f"\n数据源统计:")
    for source, count in stats['data_sources'].items():
        print(f"  {source}: {count}")
    
    if stats['response_lengths']:
        avg_length = sum(stats['response_lengths']) / len(stats['response_lengths'])
        print(f"\nResponse平均长度: {avg_length:.2f}")
        print(f"Response长度范围: {min(stats['response_lengths'])} - {max(stats['response_lengths'])}")
    
    print(f"\n样本记录结构:")
    for i, record in enumerate(stats['sample_records']):
        print(f"\n记录 {i+1}:")
        print(f"  顶层字段: {list(record.keys())}")
        if 'meta_info' in record:
            print(f"  meta_info字段: {list(record['meta_info'].keys())}")
            if 'extra_info' in record['meta_info']:
                print(f"  extra_info字段: {list(record['meta_info']['extra_info'].keys())}")
            if 'reward_model' in record['meta_info']:
                print(f"  reward_model字段: {list(record['meta_info']['reward_model'].keys())}")

def main():
    """主函数"""
    file_path = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.jsonl"
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    # 分析数据格式
    stats = analyze_data_format(file_path)
    
    # 打印分析结果
    print_analysis_results(stats)
    
    # 保存分析结果到文件
    output_file = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/filtering/train_parquet_all.jsonl.statistic.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("数据分析结果\n")
        f.write("="*50 + "\n")
        f.write(f"总记录数: {stats['total_records']}\n\n")
        
        f.write("字段统计:\n")
        for field, count in stats['field_stats'].items():
            f.write(f"  {field}: {count}\n")
        
        f.write("\nmeta_info 字段统计:\n")
        for field, count in stats['meta_info_fields'].items():
            f.write(f"  {field}: {count}\n")
        
        f.write("\n数据库ID统计 (前10个):\n")
        for db_id, count in stats['db_ids'].most_common(10):
            f.write(f"  {db_id}: {count}\n")
        
        f.write("\n数据源统计:\n")
        for source, count in stats['data_sources'].items():
            f.write(f"  {source}: {count}\n")
        
        if stats['response_lengths']:
            avg_length = sum(stats['response_lengths']) / len(stats['response_lengths'])
            f.write(f"\nResponse平均长度: {avg_length:.2f}\n")
            f.write(f"Response长度范围: {min(stats['response_lengths'])} - {max(stats['response_lengths'])}\n")
    
    print(f"\n分析结果已保存到: {output_file}")

if __name__ == "__main__":
    main()


