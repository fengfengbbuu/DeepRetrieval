#!/usr/bin/env python3
"""
验证脚本：检查CoT格式替换结果
"""

import pandas as pd
import numpy as np

def verify_cot_replacement():
    """验证CoT格式替换结果"""
    input_file = "code/data/sql/spider/val.messages.wcot.parquet"
    output_file = "code/data/sql/spider/val.messages.wocot.parquet"
    
    print("验证CoT格式替换结果")
    print("=" * 50)
    
    # 读取输入和输出文件
    input_df = pd.read_parquet(input_file)
    output_df = pd.read_parquet(output_file)
    
    print(f"输入文件行数: {len(input_df)}")
    print(f"输出文件行数: {len(output_df)}")
    
    # 从文件读取CoT格式和输出格式
    def load_format_from_file(file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"错误: 读取格式文件 {file_path} 时出错: {e}")
            return ""
    
    cot_format = load_format_from_file("task_log/no_training/zero-shot/cot_output_format.txt")
    output_format = load_format_from_file("task_log/no_training/zero-shot/output_format.txt")
    
    # 检查替换情况
    cot_found_in_input = 0
    cot_found_in_output = 0
    output_found_in_output = 0
    
    for i in range(min(10, len(input_df))):
        # 检查输入文件
        input_prompt = input_df['prompt'].iloc[i]
        if isinstance(input_prompt, np.ndarray):
            input_prompt = input_prompt.tolist()
        
        input_user_content = ""
        for msg in input_prompt:
            if msg['role'] == 'user':
                input_user_content = msg['content']
                break
        
        if cot_format.strip() in input_user_content:
            cot_found_in_input += 1
        
        # 检查输出文件
        output_prompt = output_df['prompt'].iloc[i]
        if isinstance(output_prompt, np.ndarray):
            output_prompt = output_prompt.tolist()
        
        output_user_content = ""
        for msg in output_prompt:
            if msg['role'] == 'user':
                output_user_content = msg['content']
                break
        
        if cot_format.strip() in output_user_content:
            cot_found_in_output += 1
        
        if output_format.strip() in output_user_content:
            output_found_in_output += 1
    
    print(f"\n验证结果 (前10个样本):")
    print(f"输入文件中包含CoT格式: {cot_found_in_input}/10")
    print(f"输出文件中仍包含CoT格式: {cot_found_in_output}/10")
    print(f"输出文件中包含新格式: {output_found_in_output}/10")
    
    if cot_found_in_output == 0 and output_found_in_output == 10:
        print("\n✅ CoT格式替换成功!")
    else:
        print("\n❌ CoT格式替换可能有问题")
    
    # 显示一个样本的对比
    print(f"\n样本对比 (第1个):")
    print("输入文件user内容片段:")
    input_prompt = input_df['prompt'].iloc[0]
    if isinstance(input_prompt, np.ndarray):
        input_prompt = input_prompt.tolist()
    
    for msg in input_prompt:
        if msg['role'] == 'user':
            content = msg['content']
            # 找到CoT格式的位置
            cot_start = content.find("Show your work in <think>")
            if cot_start != -1:
                print(content[cot_start:cot_start+200] + "...")
            break
    
    print("\n输出文件user内容片段:")
    output_prompt = output_df['prompt'].iloc[0]
    if isinstance(output_prompt, np.ndarray):
        output_prompt = output_prompt.tolist()
    
    for msg in output_prompt:
        if msg['role'] == 'user':
            content = msg['content']
            # 找到输出格式的位置
            output_start = content.find("Show your final answer")
            if output_start != -1:
                print(content[output_start:output_start+200] + "...")
            break

if __name__ == "__main__":
    verify_cot_replacement()
