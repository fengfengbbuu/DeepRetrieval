#!/usr/bin/env python3
"""
综合统计报告生成脚本
"""

import json
import os
from typing import Dict, List, Any
from collections import Counter

def load_jsonl_data(file_path: str) -> List[Dict]:
    """加载 JSONL 数据"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError as e:
                print(f"JSON解析错误在第{line_num}行: {e}")
                continue
    return data

def generate_comprehensive_report():
    """生成综合统计报告"""
    
    # 文件路径
    original_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.jsonl"
    filtered_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.filtered.jsonl"
    final_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.final.jsonl"
    
    # 检查文件是否存在
    files_exist = {
        'original': os.path.exists(original_file),
        'filtered': os.path.exists(filtered_file),
        'final': os.path.exists(final_file)
    }
    
    print("文件存在性检查:")
    for file_type, exists in files_exist.items():
        print(f"  {file_type}: {exists}")
    
    # 统计各阶段的数据量
    stats = {}
    
    if files_exist['original']:
        original_data = load_jsonl_data(original_file)
        stats['original_count'] = len(original_data)
        print(f"原始数据: {stats['original_count']} 条")
    
    if files_exist['filtered']:
        filtered_data = load_jsonl_data(filtered_file)
        stats['filtered_count'] = len(filtered_data)
        print(f"过滤后数据: {stats['filtered_count']} 条")
    
    if files_exist['final']:
        final_data = load_jsonl_data(final_file)
        stats['final_count'] = len(final_data)
        print(f"最终数据: {stats['final_count']} 条")
    
    # 计算过滤统计
    if 'original_count' in stats and 'filtered_count' in stats:
        stats['error_response_filtered'] = stats['original_count'] - stats['filtered_count']
        stats['error_response_filter_rate'] = stats['error_response_filtered'] / stats['original_count'] * 100
    
    if 'filtered_count' in stats and 'final_count' in stats:
        stats['sql_validation_filtered'] = stats['filtered_count'] - stats['final_count']
        stats['sql_validation_filter_rate'] = stats['sql_validation_filtered'] / stats['filtered_count'] * 100
    
    if 'original_count' in stats and 'final_count' in stats:
        stats['total_filtered'] = stats['original_count'] - stats['final_count']
        stats['total_filter_rate'] = stats['total_filtered'] / stats['original_count'] * 100
        stats['final_keep_rate'] = stats['final_count'] / stats['original_count'] * 100
    
    # 生成报告
    report_file = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/filtering/comprehensive_report.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 数据过滤综合统计报告\n\n")
        f.write(f"**生成时间:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 数据量统计\n\n")
        if 'original_count' in stats:
            f.write(f"- **原始数据量:** {stats['original_count']} 条\n")
        if 'filtered_count' in stats:
            f.write(f"- **过滤后数据量:** {stats['filtered_count']} 条\n")
        if 'final_count' in stats:
            f.write(f"- **最终数据量:** {stats['final_count']} 条\n")
        
        f.write("\n## 过滤统计\n\n")
        if 'error_response_filtered' in stats:
            f.write(f"- **error_response 过滤数量:** {stats['error_response_filtered']} 条\n")
            f.write(f"- **error_response 过滤率:** {stats['error_response_filter_rate']:.2f}%\n")
        
        if 'sql_validation_filtered' in stats:
            f.write(f"- **SQL 验证过滤数量:** {stats['sql_validation_filtered']} 条\n")
            f.write(f"- **SQL 验证过滤率:** {stats['sql_validation_filter_rate']:.2f}%\n")
        
        if 'total_filtered' in stats:
            f.write(f"- **总过滤数量:** {stats['total_filtered']} 条\n")
            f.write(f"- **总过滤率:** {stats['total_filter_rate']:.2f}%\n")
            f.write(f"- **最终保留率:** {stats['final_keep_rate']:.2f}%\n")
        
        f.write("\n## 过滤阶段说明\n\n")
        f.write("### 第一阶段：error_response 过滤\n")
        f.write("- 过滤掉 8 个预定义的 error_response 类型的错误数据\n")
        f.write("- 这些数据包含错误消息而不是有效的 SQL 查询\n")
        f.write("- 过滤索引: [256, 2225, 2650, 2999, 3899, 5924, 6640, 7294]\n\n")
        
        f.write("### 第二阶段：SQL 验证过滤\n")
        f.write("- 对每条数据的 SQL 进行格式检查和标准化比较\n")
        f.write("- 只保留与 ground truth SQL 完全相同的记录\n")
        f.write("- 过滤掉 SQL 格式无效或与标准答案不同的记录\n\n")
        
        f.write("## 文件说明\n\n")
        f.write("- **train_parquet_all.jsonl:** 原始数据集\n")
        f.write("- **train_parquet_all.filtered.jsonl:** 过滤 error_response 后的数据集\n")
        f.write("- **train_parquet_all.final.jsonl:** 最终过滤后的数据集\n\n")
        
        f.write("## 相关报告文件\n\n")
        f.write("- **quick_filtering_report.txt:** error_response 过滤详细报告\n")
        f.write("- **simple_validation_report.txt:** SQL 验证详细报告\n")
        f.write("- **comprehensive_report.txt:** 本综合统计报告\n")
    
    print(f"综合统计报告已保存到: {report_file}")
    
    return stats

def main():
    """主函数"""
    stats = generate_comprehensive_report()
    
    print("\n过滤统计摘要:")
    if 'original_count' in stats:
        print(f"原始数据: {stats['original_count']} 条")
    if 'filtered_count' in stats:
        print(f"过滤后数据: {stats['filtered_count']} 条")
    if 'final_count' in stats:
        print(f"最终数据: {stats['final_count']} 条")
    if 'total_filter_rate' in stats:
        print(f"总过滤率: {stats['total_filter_rate']:.2f}%")
    if 'final_keep_rate' in stats:
        print(f"最终保留率: {stats['final_keep_rate']:.2f}%")

if __name__ == "__main__":
    main()


