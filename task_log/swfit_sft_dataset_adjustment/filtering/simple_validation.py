#!/usr/bin/env python3
"""
简化SQL验证脚本：通过SQL执行和结果比较验证SQL，批量写入报告，串行处理
"""

import json
import os
import re
import sqlite3
import sys
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter

# 添加代码路径以导入 SpiderDatabaseSearcher
sys.path.append('/root/data1/projects/RL/DeepRetrieval/code')
from src.sql.spider import SpiderDatabaseSearcher

# 全局数据库搜索器
_searcher = None

def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = SpiderDatabaseSearcher()
    return _searcher

# 初始化搜索器
get_searcher()

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

def extract_last_answer_content(combined_text: str) -> str:
    """从组合文本中提取最后一个 <answer>...</answer> 内容"""
    answer_pattern = r'<answer>(.*?)</answer>'
    answer_matches = re.findall(answer_pattern, combined_text, re.DOTALL)
    
    # 过滤掉模板示例
    filtered_answers = []
    for match in answer_matches:
        content = match.strip()
        # 跳过空内容或模板示例
        if content and content not in ['', '{\n    "sql": "SELECT ... (in one line)"\n} ']:
            filtered_answers.append(content)
    
    return filtered_answers[-1] if filtered_answers else ""

def extract_sql_from_response(response: str) -> Optional[str]:
    """从 response 中提取 SQL"""
    last_answer_content = extract_last_answer_content(response)
    
    if not last_answer_content:
        return None
    
    try:
        answer_dict = json.loads(last_answer_content)
        
        if isinstance(answer_dict, dict):
            if 'sql' in answer_dict:
                return answer_dict['sql']
        return None
    except json.JSONDecodeError:
        return None

def normalize_sql(sql: str) -> str:
    """标准化 SQL 查询以便比较"""
    if not sql:
        return ""
    
    # 转换为小写
    sql = sql.lower()
    
    # 移除多余的空格和换行
    sql = re.sub(r'\s+', ' ', sql)
    
    # 移除分号
    sql = sql.rstrip(';')
    
    return sql.strip()

def validate_single_record(record_data: Tuple[int, Dict]) -> Dict[str, Any]:
    """验证单条记录"""
    i, record = record_data
    
    result = {
        'index': i,
        'valid': False,
        'reason': '',
        'question': record.get('meta_info', {}).get('question', ''),
        'db_id': record.get('meta_info', {}).get('db_id', ''),
        'model_sql': '',
        'ground_truth_sql': ''
    }
    
    # 提取模型生成的 SQL
    model_sql = extract_sql_from_response(record.get('response', ''))
    
    if model_sql is None:
        result['reason'] = 'sql_extraction_failed'
        return result
    
    # 获取 ground truth SQL
    ground_truth_sql = record.get('meta_info', {}).get('reward_model', {}).get('ground_truth', {}).get('target', '')
    db_path = record.get('meta_info', {}).get('extra_info', {}).get('db_path', '')
    
    if not ground_truth_sql or not db_path:
        result['reason'] = 'missing_ground_truth_or_db_path'
        return result
    
    result['model_sql'] = model_sql
    result['ground_truth_sql'] = ground_truth_sql
    
    # 标准化 SQL
    sql1_norm = normalize_sql(model_sql)
    sql2_norm = normalize_sql(ground_truth_sql)
    
    # 如果 SQL 完全相同，直接返回 True
    if sql1_norm == sql2_norm:
        result['valid'] = True
        result['reason'] = 'sql_identical'
        return result
    
    # 执行两个查询并比较结果
    try:
        db_path = os.path.join("/root/data1/projects/RL/DeepRetrieval/code", db_path)
        res_info1 = _searcher.search(model_sql, db_path, timeout=15)
        res_info2 = _searcher.search(ground_truth_sql, db_path, timeout=15)
    # except (OSError, sqlite3.Error, ValueError) as e:
    except Exception as e:
        print(f"SQL执行错误: {e}")
        res_info1 = []
        res_info2 = []
    
    if not res_info1 or not res_info2:
        result['reason'] = 'sql_execution_failed'
        return result

    # 比较结果
    try:
        if res_info1 == res_info2:
            result['valid'] = True
            result['reason'] = 'sql_results_match'
        else:
            result['reason'] = 'sql_results_differ'
    except (ValueError, TypeError) as e:
        result['reason'] = f'sql_comparison_error: {str(e)}'
    
    return result

def validate_sql_dataset_serial(input_file: str, output_file: str, report_file: str, batch_size: int = 50) -> Dict[str, Any]:
    """串行验证数据集中的 SQL，批量写入报告"""
    print(f"开始串行 SQL 验证: {input_file}")
    print(f"批量大小: {batch_size} 条记录")
    
    # 加载数据
    data = load_jsonl_data(input_file)
    print(f"总共加载了 {len(data)} 条记录")
    
    # 统计信息
    stats = {
        'total_records': len(data),
        'validated_records': 0,
        'sql_validation_passed': 0,
        'sql_validation_failed': 0,
        'filtered_details': []
    }
    
    # 初始化报告文件
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# SQL 串行验证报告\n\n")
        f.write(f"**验证时间:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 验证统计\n\n")
        f.write(f"- **总记录数:** {stats['total_records']}\n")
        f.write(f"- **验证记录数:** 0\n")
        f.write(f"- **SQL 验证通过:** 0\n")
        f.write(f"- **SQL 验证失败:** 0\n")
        f.write(f"- **通过率:** 0.00%\n\n")
        f.write("## 失败原因统计\n\n")
        f.write("## 验证失败的详细信息\n\n")
    
    # 打开输出文件用于写入验证通过的数据
    output_f = open(output_file, 'w', encoding='utf-8')
    
    # 生成失败数据文件名
    output_dir = os.path.dirname(output_file)
    output_basename = os.path.basename(output_file)
    failed_filename = output_basename.replace('.jsonl', '_failed.jsonl')
    failed_file = os.path.join(output_dir, failed_filename)
    
    # 打开失败数据文件用于写入验证失败的数据
    failed_f = open(failed_file, 'w', encoding='utf-8')
    
    # 失败原因计数器和批量数据
    failure_reasons = Counter()
    batch_failed_records = []  # 批量存储失败记录
    
    try:
        # 串行处理每条记录
        for i, record in enumerate(data):
            if i % 100 == 0:
                print(f"处理进度: {i}/{len(data)}")
            
            # 验证单条记录
            result = validate_single_record((i, record))
            stats['validated_records'] += 1
            
            if result['valid']:
                stats['sql_validation_passed'] += 1
                # 立即写入验证通过的数据
                output_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                output_f.flush()  # 确保立即写入磁盘
            else:
                stats['sql_validation_failed'] += 1
                failure_reasons[result['reason']] += 1
                # 将失败记录添加到批量列表中
                batch_failed_records.append(result)
                # 将失败记录添加到 stats['filtered_details'] 中
                stats['filtered_details'].append(result)
            
            # 每处理 batch_size 条记录或处理完所有数据时，批量写入统计信息
            if (i + 1) % batch_size == 0 or i == len(data) - 1:
                # 批量写入失败记录到报告和失败数据文件
                if batch_failed_records:
                    with open(report_file, 'a', encoding='utf-8') as f:
                        for failed_result in batch_failed_records:
                            f.write(f"### 索引 {failed_result['index']}\n")
                            f.write(f"- **问题:** {failed_result['question']}\n")
                            f.write(f"- **数据库:** {failed_result['db_id']}\n")
                            f.write(f"- **失败原因:** {failed_result['reason']}\n")
                            if failed_result['model_sql']:
                                f.write(f"- **模型SQL:** {failed_result['model_sql']}\n")
                            if failed_result['ground_truth_sql']:
                                f.write(f"- **标准SQL:** {failed_result['ground_truth_sql']}\n")
                            f.write("\n")
                    
                    # 批量写入失败数据到失败数据文件
                    for failed_result in batch_failed_records:
                        failed_f.write(json.dumps(failed_result, ensure_ascii=False) + '\n')
                    failed_f.flush()  # 确保立即写入磁盘
                    
                    # 清空批量列表
                    batch_failed_records = []
                
                # 更新统计信息到报告
                with open(report_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 更新统计部分
                stats_section = """## 验证统计

- **总记录数:** {total_records}
- **验证记录数:** {validated_records}
- **SQL 验证通过:** {sql_validation_passed}
- **SQL 验证失败:** {sql_validation_failed}
- **通过率:** {pass_rate:.2f}%

## 失败原因统计

""".format(
                    total_records=stats['total_records'],
                    validated_records=stats['validated_records'],
                    sql_validation_passed=stats['sql_validation_passed'],
                    sql_validation_failed=stats['sql_validation_failed'],
                    pass_rate=stats['sql_validation_passed']/stats['total_records']*100
                )
                
                for reason, count in failure_reasons.items():
                    stats_section += "- **{}:** {}\n".format(reason, count)
                stats_section += "\n"
                
                # 重新写入报告文件
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(content.split("## 验证统计")[0])
                    f.write(stats_section)
                    f.write("## 验证失败的详细信息\n\n")
                    f.write(content.split("## 验证失败的详细信息\n\n")[1])
                
                print(f"批量更新: 通过 {stats['sql_validation_passed']} 条，失败 {stats['sql_validation_failed']} 条 (已处理 {i+1}/{len(data)})")
    
    finally:
        # 关闭输出文件
        output_f.close()
        failed_f.close()
    
    print(f"串行 SQL 验证完成！")
    print(f"总记录数: {stats['total_records']}")
    print(f"验证记录数: {stats['validated_records']}")
    print(f"SQL 验证通过: {stats['sql_validation_passed']}")
    print(f"SQL 验证失败: {stats['sql_validation_failed']}")
    print(f"通过率: {stats['sql_validation_passed']/stats['total_records']*100:.2f}%")
    print(f"验证通过的数据已保存到: {output_file}")
    print(f"验证失败的数据已保存到: {failed_file}")
    
    return stats

def save_validation_report(stats: Dict[str, Any], output_file: str):
    """保存验证报告（兼容性函数，实际使用实时写入）"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# SQL 串行验证报告\n\n")
        f.write(f"**验证时间:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 验证统计\n\n")
        f.write(f"- **总记录数:** {stats['total_records']}\n")
        f.write(f"- **验证记录数:** {stats['validated_records']}\n")
        f.write(f"- **SQL 验证通过:** {stats['sql_validation_passed']}\n")
        f.write(f"- **SQL 验证失败:** {stats['sql_validation_failed']}\n")
        f.write(f"- **通过率:** {stats['sql_validation_passed']/stats['total_records']*100:.2f}%\n\n")
        
        # 统计失败原因
        failure_reasons = Counter([detail['reason'] for detail in stats['filtered_details']])
        f.write("## 失败原因统计\n\n")
        for reason, count in failure_reasons.items():
            f.write(f"- **{reason}:** {count}\n")
        f.write("\n")
        
        f.write(f"## 验证失败的详细信息\n\n")
        for detail in stats['filtered_details']:
            f.write(f"### 索引 {detail['index']}\n")
            f.write(f"- **问题:** {detail['question']}\n")
            f.write(f"- **数据库:** {detail['db_id']}\n")
            f.write(f"- **失败原因:** {detail['reason']}\n")
            if detail['model_sql']:
                f.write(f"- **模型SQL:** {detail['model_sql']}\n")
            if detail['ground_truth_sql']:
                f.write(f"- **标准SQL:** {detail['ground_truth_sql']}\n")
            f.write("\n")

def main():
    """主函数"""
    # 测试模式：只处理100条数据
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/train_parquet_all.filtered.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/train_parquet_all.final_simple.jsonl"
    report_file = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/filtering/simple_validation_report_bird.txt"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        return
    
    # 执行串行 SQL 验证（批量大小50条）
    stats = validate_sql_dataset_serial(input_file, output_file, report_file, batch_size=50)
    
    print(f"SQL 验证报告已保存到: {report_file}")
    print(f"验证通过的数据已保存到: {output_file}")
    
    # 生成失败数据文件名并输出
    output_dir = os.path.dirname(output_file)
    output_basename = os.path.basename(output_file)
    failed_filename = output_basename.replace('.jsonl', '_failed.jsonl')
    failed_file = os.path.join(output_dir, failed_filename)
    print(f"验证失败的数据已保存到: {failed_file}")

if __name__ == "__main__":
    main()
