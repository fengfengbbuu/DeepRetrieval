#!/usr/bin/env python3
"""
SQL 验证脚本（批量版本）：对过滤后的数据进行 SQL 执行验证
"""

import json
import re
import sqlite3
import os
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import multiprocessing as mp
from functools import partial

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

def execute_sql_query(db_path: str, sql: str) -> Tuple[bool, Any]:
    """在数据库中执行 SQL 查询"""
    try:
        # 构建完整的数据库路径
        full_db_path = os.path.join("/root/data1/projects/RL/DeepRetrieval/code", db_path)
        
        if not os.path.exists(full_db_path):
            return False, f"数据库文件不存在: {full_db_path}"
        
        conn = sqlite3.connect(full_db_path)
        cursor = conn.cursor()
        
        # 执行查询
        cursor.execute(sql)
        results = cursor.fetchall()
        
        conn.close()
        return True, results
        
    except sqlite3.Error as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

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
    success1, results1 = execute_sql_query(db_path, model_sql)
    success2, results2 = execute_sql_query(db_path, ground_truth_sql)
    
    if not success1 or not success2:
        result['reason'] = 'sql_execution_failed'
        return result
    
    # 比较结果
    try:
        if results1 == results2:
            result['valid'] = True
            result['reason'] = 'sql_results_match'
        else:
            result['reason'] = 'sql_results_differ'
    except Exception as e:
        result['reason'] = f'sql_comparison_error: {str(e)}'
    
    return result

def validate_sql_dataset_batch(input_file: str, output_file: str, batch_size: int = 1000) -> Dict[str, Any]:
    """批量验证数据集中的 SQL"""
    print(f"开始批量 SQL 验证: {input_file}")
    
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
    
    validated_data = []
    
    # 分批处理
    for batch_start in range(0, len(data), batch_size):
        batch_end = min(batch_start + batch_size, len(data))
        batch_data = data[batch_start:batch_end]
        
        print(f"处理批次 {batch_start//batch_size + 1}: 记录 {batch_start+1} 到 {batch_end}")
        
        # 使用多进程处理批次
        with mp.Pool(processes=min(4, mp.cpu_count())) as pool:
            batch_results = pool.map(validate_single_record, 
                                  [(i + batch_start, record) for i, record in enumerate(batch_data)])
        
        # 处理批次结果
        for result in batch_results:
            stats['validated_records'] += 1
            
            if result['valid']:
                stats['sql_validation_passed'] += 1
                validated_data.append(data[result['index']])
            else:
                stats['sql_validation_failed'] += 1
                stats['filtered_details'].append(result)
        
        print(f"批次完成: 通过 {stats['sql_validation_passed']} 条，失败 {stats['sql_validation_failed']} 条")
    
    # 保存验证后的数据
    print(f"保存验证后的数据到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in validated_data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"批量 SQL 验证完成！")
    print(f"总记录数: {stats['total_records']}")
    print(f"验证记录数: {stats['validated_records']}")
    print(f"SQL 验证通过: {stats['sql_validation_passed']}")
    print(f"SQL 验证失败: {stats['sql_validation_failed']}")
    print(f"通过率: {stats['sql_validation_passed']/stats['total_records']*100:.2f}%")
    
    return stats

def save_validation_report(stats: Dict[str, Any], output_file: str):
    """保存验证报告"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# SQL 批量验证报告\n\n")
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
        # for detail in stats['filtered_details'][:100]:
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
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.filtered.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.final.jsonl"
    report_file = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/filtering/sql_validation_report.txt"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        return
    
    # 执行批量 SQL 验证（先测试100条）
    stats = validate_sql_dataset_batch(input_file, output_file, batch_size=100)
    
    # 保存验证报告
    save_validation_report(stats, report_file)
    
    print(f"SQL 验证报告已保存到: {report_file}")

if __name__ == "__main__":
    main()
