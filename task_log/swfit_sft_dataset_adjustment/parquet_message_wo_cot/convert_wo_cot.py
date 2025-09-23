#!/usr/bin/env python3
"""
数据转换脚本：将 val.messages.wcot.parquet 转换为不含 CoT 的 messages 格式
基于 task_log/rl_dataset_adjustment/parquet_add_message/convert_to_messages_fixed.py 进行完善

任务出处：task_log/swfit_sft_dataset_adjustment/parquet_message_wo_cot/parquet_message_wo_cot.txt
"""

import pandas as pd
import numpy as np
import re
from typing import List, Dict, Any

# 格式文件路径配置
COT_FORMAT_FILE = "task_log/no_training/zero-shot/cot_output_format.txt"
OUTPUT_FORMAT_FILE = "task_log/no_training/zero-shot/output_format.txt"

# 格式内容变量（将在运行时从文件读取）
COT_FORMAT = ""
OUTPUT_FORMAT = ""


def load_format_from_file(file_path: str) -> str:
    """
    从文件中读取格式内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        print(f"成功读取格式文件: {file_path}")
        return content
    except (FileNotFoundError, IOError, UnicodeDecodeError) as e:
        print(f"错误: 读取格式文件 {file_path} 时出错: {e}")
        return ""


def initialize_formats():
    """
    初始化格式内容，从文件中读取
    """
    global COT_FORMAT, OUTPUT_FORMAT
    
    print("初始化格式内容...")
    COT_FORMAT = load_format_from_file(COT_FORMAT_FILE)
    OUTPUT_FORMAT = load_format_from_file(OUTPUT_FORMAT_FILE)
    
    if not COT_FORMAT:
        print("警告: CoT格式内容为空")
    if not OUTPUT_FORMAT:
        print("警告: 输出格式内容为空")
    
    print(f"CoT格式长度: {len(COT_FORMAT)}")
    print(f"输出格式长度: {len(OUTPUT_FORMAT)}")


def analyze_input_data(input_file: str) -> Dict[str, Any]:
    """
    分析输入数据的结构和格式
    
    Args:
        input_file: 输入parquet文件路径
        
    Returns:
        数据统计信息
    """
    print(f"分析输入文件: {input_file}")
    
    df = pd.read_parquet(input_file)
    print(f"数据行数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    
    # 分析prompt字段
    if 'prompt' in df.columns:
        sample_prompt = df['prompt'].iloc[0]
        print(f"prompt字段类型: {type(sample_prompt)}")
        
        if isinstance(sample_prompt, list) and len(sample_prompt) > 0:
            print(f"prompt内容示例: {sample_prompt[0]}")
    
    return {
        'total_rows': len(df),
        'columns': list(df.columns),
        'sample_data': df.head(1).to_dict('records')[0] if len(df) > 0 else None
    }


def parse_prompt_to_messages(prompt_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    直接处理已经是messages格式的prompt数据
    
    Args:
        prompt_data: 已经是messages格式的数据列表
        
    Returns:
        messages列表
    """
    messages = []
    
    for item in prompt_data:
        if isinstance(item, dict) and 'role' in item and 'content' in item:
            messages.append({
                "role": item['role'],
                "content": item['content']
            })
    
    return messages


def replace_cot_format_with_output_format(content: str) -> str:
    """
    将CoT格式替换为输出格式
    
    Args:
        content: 原始内容
        
    Returns:
        替换后的内容
    """
    # 替换CoT格式为输出格式
    if COT_FORMAT.strip() in content:
        content = content.replace(COT_FORMAT.strip(), OUTPUT_FORMAT.strip())
    
    return content


def process_user_message_content(user_content: str) -> str:
    """
    处理user消息内容，替换CoT格式
    
    Args:
        user_content: 原始user内容
        
    Returns:
        处理后的user内容
    """
    return replace_cot_format_with_output_format(user_content)


def convert_parquet_to_messages_wo_cot(input_file: str, output_file: str) -> str:
    """
    将parquet文件转换为不含CoT的messages格式
    
    Args:
        input_file: 输入parquet文件路径
        output_file: 输出parquet文件路径
        
    Returns:
        输出文件路径
    """
    print(f"开始转换: {input_file} -> {output_file}")
    
    # 加载原始parquet文件
    print("加载parquet文件...")
    df = pd.read_parquet(input_file)
    
    print(f"处理 {len(df)} 行数据...")
    
    # 转换每个prompt为messages格式
    converted_data = []
    processed_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"处理行 {idx}/{len(df)}")
        
        try:
            # 获取prompt内容 - 处理numpy数组
            prompt_data = row['prompt']
            
            # 转换numpy数组为list
            if isinstance(prompt_data, np.ndarray):
                prompt_data = prompt_data.tolist()
            
            if isinstance(prompt_data, list) and len(prompt_data) > 0:
                # 直接处理已经是messages格式的数据
                messages = parse_prompt_to_messages(prompt_data)
            else:
                print(f"警告: 行 {idx} 的prompt格式异常: {type(prompt_data)}")
                error_count += 1
                continue
            
            if not messages:
                print(f"警告: 行 {idx} 无法提取messages")
                error_count += 1
                continue
            
            # 处理user消息内容，替换CoT格式
            for message in messages:
                if message['role'] == 'user':
                    message['content'] = process_user_message_content(message['content'])
            
            # 创建新行，保持messages格式
            new_row = row.copy()
            new_row['prompt'] = messages  # 保持原始字段名
            
            converted_data.append(new_row)
            processed_count += 1
            
        except (ValueError, KeyError, TypeError) as e:
            print(f"错误: 处理行 {idx} 时出错: {e}")
            error_count += 1
            continue
    
    # 创建新dataframe
    converted_df = pd.DataFrame(converted_data)
    
    print(f"转换完成: {processed_count} 行成功, {error_count} 行失败")
    print("转换后数据示例:")
    if len(converted_df) > 0:
        sample_messages = converted_df['prompt'].iloc[0]
        print(f"第一条prompt messages: {sample_messages}")
    
    # 保存到新parquet文件
    print(f"保存到 {output_file}...")
    converted_df.to_parquet(output_file, index=False)
    
    print("转换完成!")
    return output_file


def validate_conversion(input_file: str, output_file: str, num_samples: int = 3):
    """
    验证转换结果
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        num_samples: 验证样本数量
    """
    print("\n验证转换结果...")
    print("=" * 50)
    
    # 读取输入和输出文件
    input_df = pd.read_parquet(input_file)
    output_df = pd.read_parquet(output_file)
    
    print(f"输入文件行数: {len(input_df)}")
    print(f"输出文件行数: {len(output_df)}")
    
    # 验证样本
    for i in range(min(num_samples, len(output_df))):
        print(f"\n样本 {i+1}:")
        
        # 获取原始prompt内容
        original_prompt = input_df['prompt'].iloc[i]
        if isinstance(original_prompt, np.ndarray):
            original_prompt = original_prompt.tolist()
        original_content = original_prompt[0]['content'] if isinstance(original_prompt, list) else str(original_prompt)
        
        # 获取转换后的messages
        converted_messages = output_df['prompt'].iloc[i]
        
        print(f"  原始内容长度: {len(original_content)}")
        print(f"  转换后消息数量: {len(converted_messages)}")
        
        # 检查CoT格式是否被替换
        user_content = ""
        for msg in converted_messages:
            if msg['role'] == 'user':
                user_content = msg['content']
                break
        
        if COT_FORMAT.strip() in user_content:
            print("  ❌ CoT格式未被替换")
        else:
            print("  ✅ CoT格式已替换")
        
        if OUTPUT_FORMAT.strip() in user_content:
            print("  ✅ 输出格式已添加")
        else:
            print("  ❌ 输出格式未添加")
        
        # 显示内容预览
        print(f"  User内容预览: {user_content[:200]}...")


def main():
    """主函数"""
    # input_file = "code/data/sql/spider/val.messages.wcot.parquet"
    # input_file = "code/data/sql/spider/train.messages.wcot.parquet"
    # input_file = "code/data/sql/spider/test.messages.wcot.parquet"
    # input_file = "code/data/sql/bird/val.messages.wcot.parquet"
    # input_file = "code/data/sql/bird/test.messages.wcot.parquet"
    input_file = "code/data/sql/bird/train.messages.wcot.parquet"

    # output_file = "code/data/sql/spider/val.messages.wocot.parquet"
    # output_file = "code/data/sql/spider/train.messages.wocot.parquet"
    # output_file = "code/data/sql/spider/test.messages.wocot.parquet"
    # output_file = "code/data/sql/bird/val.messages.wocot.parquet"
    # output_file = "code/data/sql/bird/test.messages.wocot.parquet"
    output_file = "code/data/sql/bird/train.messages.wocot.parquet"

    # 初始化格式内容
    print("=== 初始化格式内容 ===")
    initialize_formats()
    
    # 分析输入数据
    print("\n=== 分析输入数据 ===")
    analyze_input_data(input_file)
    
    # 执行转换
    print("\n=== 执行数据转换 ===")
    result_file = convert_parquet_to_messages_wo_cot(input_file, output_file)
    
    # 验证结果
    print("\n=== 验证转换结果 ===")
    validate_conversion(input_file, result_file, num_samples=3)
    
    print(f"\n任务完成! 输出文件: {result_file}")


if __name__ == "__main__":
    main()
