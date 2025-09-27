#!/usr/bin/env python3
"""
SQL 执行时间分析脚本
统计 TARGET_FILE 中每条 ground_truth SQL 的执行时间
"""

import pandas as pd
import sqlite3
import time
import json
import os
import signal
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from datetime import datetime

class SQLExecutionAnalyzer:
    """SQL 执行时间分析器"""
    
    def __init__(self, target_file: str, output_dir: str, timeout: int = 50):
        """
        初始化分析器
        
        Args:
            target_file: 目标 parquet 文件路径
            output_dir: 输出目录
            timeout: 超时时间（秒）
        """
        self.target_file = target_file
        self.output_dir = output_dir
        self.timeout = timeout
        self.results = []
        self.batch_size = 100  # 每批处理的数据量
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 结果文件路径
        self.results_file = os.path.join(output_dir, "sql_execution_results.jsonl")
        self.report_file = os.path.join(output_dir, "execution_report.txt")
        
    def load_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        加载数据
        
        Args:
            limit: 限制加载的数据量，用于测试
            
        Returns:
            加载的 DataFrame
        """
        print(f"正在加载数据: {self.target_file}")
        df = pd.read_parquet(self.target_file)
        
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
    
    def execute_sql_with_timeout(self, sql: str, db_path: str) -> float:
        """
        执行 SQL 并测量时间，支持超时
        
        Args:
            sql: 要执行的 SQL 语句
            db_path: 数据库文件路径
            
        Returns:
            执行时间（秒），超时返回 timeout + 1
        """
        # 构建完整的数据库路径
        full_db_path = os.path.join("/root/data1/projects/RL/DeepRetrieval/code", db_path)
        
        if not os.path.exists(full_db_path):
            print(f"数据库文件不存在: {full_db_path}")
            return -1  # 表示文件不存在
        
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
                return end_time - start_time
                
            except Exception as e:
                print(f"SQL 执行错误: {e}")
                return -2  # 表示执行错误
        
        try:
            # 使用线程池执行，设置超时
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_query)
                execution_time = future.result(timeout=self.timeout)
                return execution_time
                
        except TimeoutError:
            print(f"SQL 执行超时 ({self.timeout}s): {sql[:100]}...")
            return self.timeout + 1  # 超时标记
    
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
                'error': 'Failed to extract SQL info'
            }
        
        # 执行 SQL 并测量时间
        execution_time = self.execute_sql_with_timeout(
            sql_info['gold_sql'], 
            sql_info['db_path']
        )
        
        result = {
            'idx': idx,
            'gold_sql': sql_info['gold_sql'],
            'time_cost': execution_time
        }
        
        # 添加错误信息
        if execution_time == -1:
            result['error'] = 'Database file not found'
        elif execution_time == -2:
            result['error'] = 'SQL execution error'
        elif execution_time == self.timeout + 1:
            result['error'] = 'Execution timeout'
        
        return result
    
    def save_batch_results(self, batch_results: List[Dict[str, Any]]):
        """
        保存批次结果到文件
        
        Args:
            batch_results: 批次结果列表
        """
        with open(self.results_file, 'a', encoding='utf-8') as f:
            for result in batch_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        print(f"已保存 {len(batch_results)} 条结果到 {self.results_file}")
    
    def process_data(self, df: pd.DataFrame):
        """
        处理所有数据
        
        Args:
            df: 要处理的数据
        """
        total_records = len(df)
        print(f"开始处理 {total_records} 条记录")
        
        batch_results = []
        
        for idx, row in df.iterrows():
            try:
                result = self.process_single_record(idx, row)
                batch_results.append(result)
                
                # 每处理一定数量的记录就保存一次
                if len(batch_results) >= self.batch_size:
                    self.save_batch_results(batch_results)
                    batch_results = []
                
                # 显示进度
                if (idx + 1) % 50 == 0:
                    print(f"已处理 {idx + 1}/{total_records} 条记录")
                    
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
                    'error': str(e)
                }
                batch_results.append(error_result)
        
        # 保存剩余的结果
        if batch_results:
            self.save_batch_results(batch_results)
        
        print(f"处理完成，结果已保存到 {self.results_file}")
    
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
        
        for result in results:
            time_cost = result['time_cost']
            
            if time_cost > 0 and time_cost <= self.timeout:
                success_count += 1
                execution_times.append(time_cost)
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
        
        # 生成报告
        report_content = f"""
SQL 执行时间分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据文件: {self.target_file}
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

def main(test_mode=True):
    """主函数"""
    # 配置参数
    target_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/train.parquet"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/task_log/analyze/sql_exe"
    # timeout = 50
    timeout = 30
    
    # 创建分析器
    analyzer = SQLExecutionAnalyzer(target_file, output_dir, timeout)
    
    # 检查是否已有结果文件
    if os.path.exists(analyzer.results_file):
        print(f"发现已有结果文件: {analyzer.results_file}")
        # 非交互模式下直接重新处理
        print("重新处理数据...")
    
    if test_mode:
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
    import sys
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        main(test_mode=False)
    else:
        main(test_mode=True)
