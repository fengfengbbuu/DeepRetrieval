#!/usr/bin/env python3
"""
快速过滤脚本：过滤掉 error_response 类型的错误数据
"""

import json
import os
from typing import Dict, List, Any

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

def save_jsonl_data(data: List[Dict], file_path: str):
    """Save data to JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

def extract_prompt_content(meta_info: Dict) -> str:
    """Extract content from meta_info.prompt[0].content."""
    try:
        return meta_info['prompt'][0]['content']
    except (KeyError, IndexError, TypeError):
        return ""

def extract_last_answer_content(combined_text: str) -> str:
    """Extract the last <answer>...</answer> content from the combined text."""
    import re
    answer_pattern = r'<answer>(.*?)</answer>'
    answer_matches = re.findall(answer_pattern, combined_text, re.DOTALL)
    
    # Filter out template examples
    filtered_answers = []
    for match in answer_matches:
        content = match.strip()
        # Skip empty or template examples
        if content and content not in ['', '{\n    "sql": "SELECT ... (in one line)"\n} ']:
            filtered_answers.append(content)
    
    return filtered_answers[-1] if filtered_answers else ""

def is_error_response(record: Dict) -> bool:
    """Check if the record contains an error response."""
    try:
        # Extract prompt content and response
        prompt_content = extract_prompt_content(record.get('meta_info', {}))
        response = record.get('response', '')
        combined_text = prompt_content + response
        
        # Extract last answer content
        last_answer_content = extract_last_answer_content(combined_text)
        
        if not last_answer_content:
            return False
        
        # Parse JSON content
        answer_dict = json.loads(last_answer_content)
        
        # Check if it's an error response
        if isinstance(answer_dict, dict) and 'error' in answer_dict:
            return True
        
        return False
    except (json.JSONDecodeError, KeyError, TypeError):
        return False

def filter_error_responses(data: List[Dict]) -> tuple[List[Dict], List[Dict], List[int]]:
    """Filter out error_response records."""
    filtered_data = []
    error_records = []
    error_indices = []
    
    for i, record in enumerate(data):
        if is_error_response(record):
            error_records.append(record)
            error_indices.append(i)
            print(f"发现 error_response 记录: 索引 {i}")
        else:
            filtered_data.append(record)
    
    return filtered_data, error_records, error_indices

def save_filtering_report(error_records: List[Dict], error_indices: List[int], 
                         total_records: int, output_file: str):
    """保存过滤报告"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Error Response 过滤报告\n\n")
        f.write(f"**过滤时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 过滤统计\n\n")
        f.write(f"- **原始记录数**: {total_records:,}\n")
        f.write(f"- **过滤记录数**: {len(error_records)}\n")
        f.write(f"- **保留记录数**: {total_records - len(error_records):,}\n")
        f.write(f"- **过滤率**: {(len(error_records) / total_records) * 100:.2f}%\n\n")
        
        f.write("## 过滤的 error_response 记录\n\n")
        f.write(f"**过滤索引**: {error_indices}\n\n")
        
        for i, (record, idx) in enumerate(zip(error_records, error_indices)):
            f.write(f"### 记录 {i+1} (索引 {idx})\n")
            
            # 提取问题信息
            question = record.get('meta_info', {}).get('question', '')
            db_id = record.get('meta_info', {}).get('db_id', '')
            
            f.write(f"**问题**: {question}\n")
            f.write(f"**数据库**: {db_id}\n")
            
            # 提取错误内容
            prompt_content = extract_prompt_content(record.get('meta_info', {}))
            response = record.get('response', '')
            combined_text = prompt_content + response
            last_answer_content = extract_last_answer_content(combined_text)
            
            f.write("**错误内容**:\n")
            f.write(f"```\n{last_answer_content}\n```\n\n")

def main():
    """主函数"""
    # input_file = "outputs/llm_response/spider/train_parquet_all.jsonl"
    input_file = "outputs/llm_response/bird/train_parquet_all.jsonl"

    # output_file = "outputs/llm_response/spider/train_parquet_all.filtered.jsonl"
    output_file = "outputs/llm_response/bird/train_parquet_all.filtered.jsonl"

    # report_file = "task_log/swfit_sft_dataset_adjustment/filtering/quick_filtering_report.txt"
    report_file = "task_log/swfit_sft_dataset_adjustment/filtering/quick_filtering_report_bird.txt"
    
    print("=== Error Response 过滤开始 ===")
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 {input_file}")
        return
    
    # 加载数据
    print("加载数据...")
    data = load_jsonl_data(input_file)
    print(f"成功加载 {len(data)} 条记录")
    
    # 过滤掉格式有误的 response
    failed_indices = [120, 265, 287, 322, 329, 349, 357, 367, 371, 493, 530, 539, 603, 671, 685, 701, 707, 714, 737, 755, 792, 797, 821, 897, 932, 936, 966, 973, 1174, 1233, 1262, 1292, 1296, 1318, 1362, 1374, 1380, 1423, 1438, 1491, 1506, 1515, 1556, 1590, 1600, 1605, 1713, 1795, 1834, 1988, 1999, 2009, 2014, 2024, 2040, 2050, 2064, 2071, 2087, 2132, 2385, 2479, 2481, 2511, 2578, 2604, 2750, 2754, 2761, 2763, 2784, 2811, 2909, 2929, 2954, 2962, 2963, 2971, 2984, 2990, 3015, 3115, 3135, 3147, 3162, 3215, 3264, 3391, 3444, 3459, 3524, 3573, 3593, 3747, 3834, 3842, 3982, 3990, 4097, 4100, 4110, 4131, 4156, 4189, 4208, 4327, 4403, 4477, 4520, 4524, 4553, 4563, 4786, 4798, 4835, 4846, 4857, 4860, 4908, 4965, 4999, 5001, 5026, 5083, 5163, 5195, 5230, 5240, 5251, 5300, 5351, 5355, 5369, 5370, 5395, 5399, 5441, 5460, 5500, 5596, 5669, 5687, 5922, 6055, 6064, 6092, 6165, 6213, 6224, 6278, 6321, 6399, 6428, 6446, 6479, 6530, 6543, 6614, 6635, 6640, 6673, 6685, 6696, 6709, 6743, 6799, 6981, 6988, 7020, 7143, 7203, 7257, 7316, 7406, 7498, 7550, 7557, 7578, 7604, 7671, 7701, 7713, 7772, 7774, 7791, 7915, 7919, 7964, 7985, 8001, 8040, 8146, 8272, 8299, 8328, 8348, 8380, 7128]
    data_new = []
    for idx in range(len(data)):
        if idx in failed_indices:
            continue
        data_new.append(data[idx])
    print(f"成功过滤掉 {len(failed_indices)} 条记录，data 长度从 {len(data)} 变为 {len(data_new)}")
    data = data_new

    # 过滤 error_response
    print("\n=== 过滤 error_response 记录 ===")
    filtered_data, error_records, error_indices = filter_error_responses(data)
    
    print(f"过滤完成:")
    print(f"- 原始记录: {len(data)}")
    print(f"- 过滤记录: {len(error_records)}")
    print(f"- 保留记录: {len(filtered_data)}")
    print(f"- 过滤率: {(len(error_records) / len(data)) * 100:.2f}%")
    
    # 保存过滤后的数据
    print(f"\n保存过滤后的数据到: {output_file}")
    save_jsonl_data(filtered_data, output_file)
    
    # 保存过滤报告
    print(f"保存过滤报告到: {report_file}")
    save_filtering_report(error_records, error_indices, len(data), report_file)
    
    print(f"\n过滤完成！")
    print(f"过滤后的数据: {output_file}")
    print(f"过滤报告: {report_file}")

if __name__ == "__main__":
    main()
