#!/usr/bin/env python3
"""
BIRD SQL 执行分析脚本
基于 sql_execution_analyzer.py 改进，添加 gold_sql_res 字段和 resume_from_idx 功能
"""

import pandas as pd
import sqlite3
import time
import json
import os
import signal
import argparse
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from datetime import datetime

class BirdSQLAnalyzer:
    """BIRD SQL 执行分析器"""
    
    def __init__(self, input_file: str, output_root: str, start_idx: int = 0, end_idx: int = -1, timeout: int = 50):
        """
        初始化分析器
        
        Args:
            input_file: 输入文件路径
            output_root: 输出目录
            start_idx: 从指定索引开始处理
            end_idx: 结束索引（不包含），-1表示处理到最后
            timeout: 超时时间（秒）
        """
        self.input_file = input_file
        self.output_root = output_root
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.timeout = timeout
        self.results = []
        self.batch_size = 100  # 每批处理的数据量
        
        # 确保输出目录存在
        os.makedirs(output_root, exist_ok=True)
        
        # 结果文件路径
        self.results_file = os.path.join(output_root, "bird_sql_execution_results.jsonl")
        self.report_file = os.path.join(output_root, "bird_execution_report.txt")
        
    def load_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        加载数据
        
        Args:
            limit: 限制加载的数据量，用于测试
            
        Returns:
            加载的 DataFrame
        """
        print(f"正在加载数据: {self.input_file}")
        df = pd.read_parquet(self.input_file)
        
        if limit:
            df = df.head(limit)
            print(f"限制加载前 {limit} 条数据")
        
        print(f"成功加载 {len(df)} 条数据")
        return df
    
    def extract_sql_info(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        从数据行中提取 SQL 信息
        
        Args:
            row: 数据行
            
        Returns:
            包含 SQL 信息的字典，如果提取失败返回 None
        """
        try:
            # 提取 ground truth SQL
            reward_model = row['reward_model']
            if isinstance(reward_model, str):
                reward_model = json.loads(reward_model)
            
            ground_truth_sql = reward_model['ground_truth']['target']
            
            # 提取数据库路径
            extra_info = row['extra_info']
            if isinstance(extra_info, str):
                extra_info = json.loads(extra_info)
            
            db_path = extra_info['db_path']
            
            return {
                'gold_sql': ground_truth_sql,
                'db_path': db_path
            }
        except Exception as e:
            print(f"提取 SQL 信息失败: {e}")
            return None
    
    def execute_sql_with_timeout(self, sql: str, db_path: str) -> tuple[float, Any, str]:
        """
        执行 SQL 并测量时间，支持超时，同时返回执行结果
        
        Args:
            sql: 要执行的 SQL 语句
            db_path: 数据库文件路径
            
        Returns:
            (执行时间（秒），执行结果，错误信息)，超时返回 (timeout + 1, None, error_msg)
        """
        # 构建完整的数据库路径
        full_db_path = os.path.join("/root/data1/projects/RL/DeepRetrieval/code", db_path)
        
        if not os.path.exists(full_db_path):
            print(f"数据库文件不存在: {full_db_path}")
            return -1, None, f"Database file not found: {full_db_path}"
        
        def execute_query():
            """在单独线程中执行查询"""
            try:
                conn = sqlite3.connect(full_db_path)
                cursor = conn.cursor()
                
                start_time = time.time()
                cursor.execute(sql)
                # 获取结果以确保查询真正执行
                results = cursor.fetchall()
                end_time = time.time()
                
                conn.close()
                return end_time - start_time, results, ""  # 成功执行，无错误
                
            except Exception as e:
                print(f"SQL 执行错误: {e}")
                return -2, None, str(e)  # 表示执行错误
        
        try:
            # 使用线程池执行，设置超时
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_query)
                execution_time, execution_result, error_msg = future.result(timeout=self.timeout)
                return execution_time, execution_result, error_msg
                
        except TimeoutError:
            print(f"SQL 执行超时 ({self.timeout}s): {sql[:100]}...")
            return self.timeout + 1, None, f"Execution timeout after {self.timeout}s"  # 超时标记
    
    def process_single_record(self, idx: int, row: pd.Series) -> Dict[str, Any]:
        """
        处理单条记录
        
        Args:
            idx: 记录索引
            row: 数据行
            
        Returns:
            处理结果
        """
        # 提取 SQL 信息
        sql_info = self.extract_sql_info(row)
        if not sql_info:
            return {
                'idx': idx,
                'gold_sql': None,
                'time_cost': -3,  # 表示提取失败
                'gold_sql_res': None,
                'error_info': 'Failed to extract SQL info',
                'db_path': None
            }
        
        # 执行 SQL 并测量时间
        execution_time, execution_result, error_msg = self.execute_sql_with_timeout(
            sql_info['gold_sql'], 
            sql_info['db_path']
        )
        
        result = {
            'idx': idx,
            'gold_sql': sql_info['gold_sql'],
            'time_cost': execution_time,
            'gold_sql_res': execution_result,
            'error_info': error_msg,  # 使用返回的错误信息
            'db_path': sql_info['db_path']  # 添加数据库路径字段
        }
        
        return result
    
    def save_batch_results(self, batch_results: List[Dict[str, Any]]):
        """
        保存批次结果到文件
        
        Args:
            batch_results: 批次结果列表
        """
        with open(self.results_file, 'a', encoding='utf-8') as f:
            for result in batch_results:
                # 序列化结果，处理可能包含不可序列化对象的情况
                serializable_result = result.copy()
                if serializable_result['gold_sql_res'] is not None:
                    # 将SQL结果转换为可序列化的格式
                    try:
                        serializable_result['gold_sql_res'] = [
                            list(row) if isinstance(row, (list, tuple)) else row 
                            for row in serializable_result['gold_sql_res']
                        ]
                    except Exception as e:
                        serializable_result['gold_sql_res'] = str(serializable_result['gold_sql_res'])
                
                f.write(json.dumps(serializable_result, ensure_ascii=False) + '\n')
        
        print(f"已保存 {len(batch_results)} 条结果到 {self.results_file}")
    
    def load_existing_results(self) -> set:
        """
        加载已有的结果索引，用于断点续传
        
        Returns:
            已有结果的索引集合
        """
        existing_indices = set()
        if os.path.exists(self.results_file):
            with open(self.results_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            result = json.loads(line)
                            existing_indices.add(result['idx'])
                        except Exception as e:
                            print(f"解析已有结果时出错: {e}")
        return existing_indices
    
    def process_data(self, df: pd.DataFrame):
        """
        处理所有数据，支持断点续传
        
        Args:
            df: 要处理的数据
        """
        total_records = len(df)
        print(f"开始处理 {total_records} 条记录")
        
        # 加载已有结果
        existing_indices = self.load_existing_results()
        if existing_indices:
            print(f"发现 {len(existing_indices)} 条已有结果，将跳过这些记录")
        
        batch_results = []
        processed_count = 0
        skipped_count = 0
        
        # 从指定索引开始处理
        start_idx = max(self.start_idx, 0)
        if start_idx > 0:
            print(f"从索引 {start_idx} 开始处理")
        
        # 确定结束索引
        end_idx = self.end_idx if self.end_idx != -1 else len(df)
        if self.end_idx != -1:
            print(f"到索引 {end_idx} 结束处理（不包含）")
        
        for idx, row in df.iterrows():
            # 检查是否需要跳过
            if idx < start_idx or idx >= end_idx:
                continue
            
            # 检查是否已存在结果
            if idx in existing_indices:
                skipped_count += 1
                if skipped_count % 100 == 0:
                    print(f"已跳过 {skipped_count} 条已有记录")
                continue
            
            try:
                result = self.process_single_record(idx, row)
                batch_results.append(result)
                processed_count += 1
                
                # 每处理一定数量的记录就保存一次
                if len(batch_results) >= self.batch_size:
                    self.save_batch_results(batch_results)
                    batch_results = []
                
                # 显示进度
                if processed_count % 50 == 0:
                    print(f"已处理 {processed_count} 条新记录，跳过 {skipped_count} 条已有记录")
                    
            except KeyboardInterrupt:
                print("\n用户中断处理，保存当前结果...")
                if batch_results:
                    self.save_batch_results(batch_results)
                break
            except Exception as e:
                print(f"处理第 {idx} 条记录时出错: {e}")
                error_result = {
                    'idx': idx,
                    'gold_sql': None,
                    'time_cost': -4,  # 表示处理错误
                    'gold_sql_res': None,
                    'error_info': str(e),
                    'db_path': None
                }
                batch_results.append(error_result)
                processed_count += 1
        
        # 保存剩余的结果
        if batch_results:
            self.save_batch_results(batch_results)
        
        print(f"处理完成，共处理 {processed_count} 条新记录，跳过 {skipped_count} 条已有记录")
        print(f"结果已保存到 {self.results_file}")
    
    def load_all_results(self) -> List[Dict[str, Any]]:
        """
        加载所有结果
        
        Returns:
            所有结果的列表
        """
        results = []
        if os.path.exists(self.results_file):
            with open(self.results_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line))
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]):
        """
        生成分析报告
        
        Args:
            results: 所有结果
        """
        if not results:
            print("没有结果可生成报告")
            return
        
        print(f"正在生成报告，共 {len(results)} 条结果")
        
        # 统计信息
        total_count = len(results)
        success_count = 0
        timeout_count = 0
        error_count = 0
        file_not_found_count = 0
        execution_error_count = 0
        
        execution_times = []
        result_counts = []
        
        for result in results:
            time_cost = result['time_cost']
            
            if time_cost > 0 and time_cost <= self.timeout:
                success_count += 1
                execution_times.append(time_cost)
                # 统计结果行数
                if result['gold_sql_res'] is not None:
                    result_counts.append(len(result['gold_sql_res']))
            elif time_cost == self.timeout + 1:
                timeout_count += 1
            elif time_cost == -1:
                file_not_found_count += 1
            elif time_cost == -2:
                execution_error_count += 1
            else:
                error_count += 1
        
        # 计算统计信息
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            median_time = sorted(execution_times)[len(execution_times) // 2]
        else:
            avg_time = min_time = max_time = median_time = 0
        
        # 计算结果行数统计
        if result_counts:
            avg_results = sum(result_counts) / len(result_counts)
            max_results = max(result_counts)
            min_results = min(result_counts)
        else:
            avg_results = max_results = min_results = 0
        
        # 生成报告
        report_content = f"""
BIRD SQL 执行时间分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据文件: {self.input_file}
输出目录: {self.output_root}
超时设置: {self.timeout} 秒

=== 总体统计 ===
总记录数: {total_count}
成功执行: {success_count} ({success_count/total_count*100:.1f}%)
执行超时: {timeout_count} ({timeout_count/total_count*100:.1f}%)
文件不存在: {file_not_found_count} ({file_not_found_count/total_count*100:.1f}%)
执行错误: {execution_error_count} ({execution_error_count/total_count*100:.1f}%)
其他错误: {error_count} ({error_count/total_count*100:.1f}%)

=== 执行时间统计 (仅成功执行的查询) ===
平均执行时间: {avg_time:.3f} 秒
最短执行时间: {min_time:.3f} 秒
最长执行时间: {max_time:.3f} 秒
中位数执行时间: {median_time:.3f} 秒

=== 查询结果统计 (仅成功执行的查询) ===
平均结果行数: {avg_results:.1f} 行
最多结果行数: {max_results} 行
最少结果行数: {min_results} 行

=== 执行时间分布 ===
"""
        
        if execution_times:
            # 时间分布统计
            time_ranges = [
                (0, 0.1, "0-0.1秒"),
                (0.1, 0.5, "0.1-0.5秒"),
                (0.5, 1.0, "0.5-1秒"),
                (1.0, 2.0, "1-2秒"),
                (2.0, 5.0, "2-5秒"),
                (5.0, 10.0, "5-10秒"),
                (10.0, float('inf'), "10秒以上")
            ]
            
            for min_t, max_t, label in time_ranges:
                count = sum(1 for t in execution_times if min_t <= t < max_t)
                percentage = count / len(execution_times) * 100
                report_content += f"{label}: {count} 条 ({percentage:.1f}%)\n"
        
        # 添加超时和错误的详细信息
        if timeout_count > 0:
            report_content += f"\n=== 超时查询示例 ===\n"
            timeout_examples = [r for r in results if r['time_cost'] == self.timeout + 1][:5]
            for i, result in enumerate(timeout_examples, 1):
                report_content += f"{i}. 索引 {result['idx']}: {result['gold_sql'][:100]}...\n"
        
        if file_not_found_count > 0:
            report_content += f"\n=== 文件不存在示例 ===\n"
            file_error_examples = [r for r in results if r['time_cost'] == -1][:5]
            for i, result in enumerate(file_error_examples, 1):
                report_content += f"{i}. 索引 {result['idx']}: {result.get('error', 'Unknown error')}\n"
        
        # 保存报告
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"报告已生成: {self.report_file}")
        print("\n=== 报告摘要 ===")
        print(report_content)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BIRD SQL 执行分析工具')
    parser.add_argument('--input_file', required=True, help='输入文件路径')
    parser.add_argument('--start_idx', type=int, default=0, help='从指定索引开始处理')
    parser.add_argument('--end_idx', type=int, default=-1, help='结束索引（不包含），-1表示处理到最后')
    parser.add_argument('--output_root', required=True, help='输出目录')
    parser.add_argument('--timeout', type=int, default=50, help='超时时间（秒）')
    parser.add_argument('--test_mode', action='store_true', help='测试模式（仅处理前200条数据）')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = BirdSQLAnalyzer(
        input_file=args.input_file,
        output_root=args.output_root,
        start_idx=args.start_idx,
        end_idx=args.end_idx,
        timeout=args.timeout
    )
    
    # 检查是否已有结果文件
    if os.path.exists(analyzer.results_file):
        print(f"发现已有结果文件: {analyzer.results_file}")
        print("将跳过已有结果，继续处理新数据...")
    
    if args.test_mode:
        # 测试模式
        print("使用测试模式 (前200条数据)")
        df = analyzer.load_data(limit=200)
    else:
        # 完整模式
        print("使用完整模式 (所有数据)")
        df = analyzer.load_data()
    
    # 处理数据
    analyzer.process_data(df)
    
    # 生成报告
    results = analyzer.load_all_results()
    analyzer.generate_report(results)
    
    print("分析完成！")

if __name__ == "__main__":
    main()
