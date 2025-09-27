#!/usr/bin/env python3
"""
数据分析脚本：分析 train_parquet_all.jsonl 数据格式和字段信息
"""

import json
import os
from typing import Dict, List, Any
from collections import defaultdict

def load_jsonl_data(file_path: str) -> List[Dict]:
    """Load JSONL data from file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    return data

def analyze_data_structure(data: List[Dict], sample_size: int = 100) -> Dict[str, Any]:
    """分析数据结构"""
    print(f"分析数据结构，样本数量: {min(sample_size, len(data))}")
    
    analysis = {
        'total_records': len(data),
        'sample_size': min(sample_size, len(data)),
        'field_analysis': {},
        'sample_records': []
    }
    
    # 分析字段
    field_counts = defaultdict(int)
    field_types = defaultdict(set)
    
    for i, record in enumerate(data[:sample_size]):
        # 记录样本
        if i < 5:  # 只保存前5个样本
            analysis['sample_records'].append(record)
        
        # 分析字段
        for key, value in record.items():
            field_counts[key] += 1
            field_types[key].add(type(value).__name__)
    
    # 分析字段信息
    for field, count in field_counts.items():
        analysis['field_analysis'][field] = {
            'count': count,
            'percentage': (count / sample_size) * 100,
            'types': list(field_types[field])
        }
    
    return analysis

def analyze_meta_info_structure(data: List[Dict], sample_size: int = 100) -> Dict[str, Any]:
    """分析 meta_info 字段结构"""
    print(f"分析 meta_info 结构，样本数量: {min(sample_size, len(data))}")
    
    meta_analysis = {
        'has_meta_info': 0,
        'meta_info_fields': defaultdict(int),
        'sample_meta_info': []
    }
    
    for i, record in enumerate(data[:sample_size]):
        if 'meta_info' in record:
            meta_analysis['has_meta_info'] += 1
            meta_info = record['meta_info']
            
            # 记录样本
            if i < 3:  # 只保存前3个样本
                meta_analysis['sample_meta_info'].append(meta_info)
            
            # 分析字段
            for key, value in meta_info.items():
                meta_analysis['meta_info_fields'][key] += 1
    
    return meta_analysis

def analyze_response_structure(data: List[Dict], sample_size: int = 100) -> Dict[str, Any]:
    """分析 response 字段结构"""
    print(f"分析 response 结构，样本数量: {min(sample_size, len(data))}")
    
    response_analysis = {
        'has_response': 0,
        'response_lengths': [],
        'sample_responses': []
    }
    
    for i, record in enumerate(data[:sample_size]):
        if 'response' in record:
            response_analysis['has_response'] += 1
            response = record['response']
            
            # 记录长度
            response_analysis['response_lengths'].append(len(str(response)))
            
            # 记录样本
            if i < 3:  # 只保存前3个样本
                response_analysis['sample_responses'].append(response[:500] + "..." if len(str(response)) > 500 else response)
    
    return response_analysis

def save_analysis_report(analysis: Dict[str, Any], meta_analysis: Dict[str, Any], 
                        response_analysis: Dict[str, Any], output_file: str):
    """保存分析报告"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 数据分析报告\n\n")
        f.write(f"**分析时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 数据概览\n\n")
        f.write(f"- **总记录数**: {analysis['total_records']:,}\n")
        f.write(f"- **分析样本数**: {analysis['sample_size']:,}\n\n")
        
        f.write("## 字段分析\n\n")
        for field, info in analysis['field_analysis'].items():
            f.write(f"### {field}\n")
            f.write(f"- **出现次数**: {info['count']}/{analysis['sample_size']} ({info['percentage']:.1f}%)\n")
            f.write(f"- **数据类型**: {', '.join(info['types'])}\n\n")
        
        f.write("## meta_info 字段分析\n\n")
        f.write(f"- **包含 meta_info 的记录**: {meta_analysis['has_meta_info']}/{analysis['sample_size']}\n\n")
        f.write("### meta_info 子字段\n")
        for field, count in meta_analysis['meta_info_fields'].items():
            percentage = (count / meta_analysis['has_meta_info']) * 100 if meta_analysis['has_meta_info'] > 0 else 0
            f.write(f"- **{field}**: {count} ({percentage:.1f}%)\n")
        f.write("\n")
        
        f.write("## response 字段分析\n\n")
        f.write(f"- **包含 response 的记录**: {response_analysis['has_response']}/{analysis['sample_size']}\n")
        if response_analysis['response_lengths']:
            avg_length = sum(response_analysis['response_lengths']) / len(response_analysis['response_lengths'])
            f.write(f"- **平均长度**: {avg_length:.0f} 字符\n")
            f.write(f"- **最小长度**: {min(response_analysis['response_lengths'])} 字符\n")
            f.write(f"- **最大长度**: {max(response_analysis['response_lengths'])} 字符\n")
        f.write("\n")
        
        f.write("## 样本数据\n\n")
        f.write("### 前3条记录的 meta_info 结构\n")
        for i, meta_info in enumerate(meta_analysis['sample_meta_info'][:3]):
            f.write(f"#### 记录 {i+1}\n")
            f.write(f"```json\n{json.dumps(meta_info, indent=2, ensure_ascii=False)}\n```\n\n")
        
        f.write("### 前3条记录的 response 内容（前500字符）\n")
        for i, response in enumerate(response_analysis['sample_responses'][:3]):
            f.write(f"#### 记录 {i+1}\n")
            f.write(f"```\n{response}\n```\n\n")

def main():
    """主函数"""
    input_file = "outputs/llm_response/spider/train_parquet_all.jsonl"
    output_file = "task_log/swfit_sft_dataset_adjustment/filtering/train_parquet_all.jsonl.statistic.json"
    
    print("=== 数据分析开始 ===")
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 {input_file}")
        return
    
    # 加载数据
    print("加载数据...")
    data = load_jsonl_data(input_file)
    print(f"成功加载 {len(data)} 条记录")
    
    # 分析数据结构
    print("\n=== 分析数据结构 ===")
    analysis = analyze_data_structure(data, sample_size=100)
    
    # 分析 meta_info 结构
    print("\n=== 分析 meta_info 结构 ===")
    meta_analysis = analyze_meta_info_structure(data, sample_size=100)
    
    # 分析 response 结构
    print("\n=== 分析 response 结构 ===")
    response_analysis = analyze_response_structure(data, sample_size=100)
    
    # 保存分析报告
    print("\n=== 保存分析报告 ===")
    save_analysis_report(analysis, meta_analysis, response_analysis, output_file)
    
    print(f"\n数据分析完成！")
    print(f"报告保存至: {output_file}")
    
    # 打印简要统计
    print(f"\n=== 简要统计 ===")
    print(f"总记录数: {analysis['total_records']:,}")
    print(f"包含 meta_info: {meta_analysis['has_meta_info']}/100")
    print(f"包含 response: {response_analysis['has_response']}/100")
    
    if response_analysis['response_lengths']:
        avg_length = sum(response_analysis['response_lengths']) / len(response_analysis['response_lengths'])
        print(f"response 平均长度: {avg_length:.0f} 字符")

if __name__ == "__main__":
    main()