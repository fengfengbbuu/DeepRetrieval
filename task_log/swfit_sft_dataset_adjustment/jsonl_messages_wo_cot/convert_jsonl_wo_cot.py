#!/usr/bin/env python3
"""
JSONL数据转换脚本：将 JSONL 文件转换为不含 CoT 的 messages 格式
处理 messages 字段：
1. 将 user role 的 content 中的 CoT 格式替换为直接输出格式
2. 移除 assistant role 的 content 中的 <think>...</think> 标签及其内容
3. 移除 assistant role 的 content 中的 "Let me write the SQL query with reasoning." 文本

任务出处：task_log/swfit_sft_dataset_adjustment/jsonl_messages_wo_cot/jsonl_messages_wo_cot.txt
"""

import json
import os
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


def replace_cot_format_with_output_format(content: str) -> tuple[str, bool]:
    """
    将CoT格式替换为输出格式
    
    Args:
        content: 原始内容
        
    Returns:
        (替换后的内容, 是否有替换发生)
    """
    # 替换CoT格式为输出格式
    if COT_FORMAT.strip() in content:
        content = content.replace(COT_FORMAT.strip(), OUTPUT_FORMAT.strip())
        return content, True
    
    return content, False


def remove_think_tags_from_content(content: str) -> tuple[str, bool]:
    """
    移除内容中的<think>...</think>标签及其内容，以及"Let me write the SQL query with reasoning."文本
    
    Args:
        content: 原始内容
        
    Returns:
        (移除think标签和指定文本后的内容, 是否有移除发生)
    """
    import re
    
    has_changes = False
    new_content = content
    
    # 移除<think>...</think>标签及其内容
    think_pattern = r'<think>.*?</think>'
    matches = re.findall(think_pattern, new_content, re.DOTALL)
    
    if matches:
        # 移除所有匹配的think标签及其内容
        new_content = re.sub(think_pattern, '', new_content, flags=re.DOTALL)
        has_changes = True
    
    # 移除"Let me write the SQL query with reasoning."文本
    reasoning_text = "Let me write the SQL query with reasoning."
    if reasoning_text in new_content:
        new_content = new_content.replace(reasoning_text, '')
        has_changes = True
    
    if has_changes:
        # 清理多余的空行和空白字符
        new_content = re.sub(r'\n\s*\n', '\n', new_content)
        new_content = re.sub(r'^\s+', '', new_content)  # 移除开头的空白
        new_content = new_content.strip()
        return new_content, True
    
    return content, False


def process_messages(messages: List[Dict[str, str]]) -> tuple[List[Dict[str, str]], bool]:
    """
    处理messages列表：
    1. 替换user role中的CoT格式为输出格式
    2. 移除assistant role中的<think>...</think>标签及其内容
    3. 移除assistant role中的"Let me write the SQL query with reasoning."文本
    
    Args:
        messages: 原始messages列表
        
    Returns:
        (处理后的messages列表, 是否有替换发生)
    """
    processed_messages = []
    has_replacement = False
    
    for message in messages:
        role = message.get('role')
        content = message.get('content', '')
        
        if role == 'user':
            # 处理user消息内容，替换CoT格式
            new_content, replaced = replace_cot_format_with_output_format(content)
            processed_messages.append({
                'role': role,
                'content': new_content
            })
            if replaced:
                has_replacement = True
                
        elif role == 'assistant':
            # 处理assistant消息内容，移除think标签
            new_content, removed = remove_think_tags_from_content(content)
            processed_messages.append({
                'role': role,
                'content': new_content
            })
            if removed:
                has_replacement = True
        else:
            # 其他role保持不变
            processed_messages.append(message.copy())
    
    return processed_messages, has_replacement


def analyze_input_file(input_file: str) -> Dict[str, Any]:
    """
    分析输入文件的结构和格式
    
    Args:
        input_file: 输入JSONL文件路径
        
    Returns:
        文件统计信息
    """
    print(f"分析输入文件: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在 {input_file}")
        return {}
    
    line_count = 0
    has_messages_field = 0
    sample_data = None
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            line_count += 1
            try:
                data = json.loads(line.strip())
                
                # 检查是否有messages字段
                if 'messages' in data:
                    has_messages_field += 1
                    
                # 保存第一条数据作为样本
                if line_num == 0:
                    sample_data = data
                    
            except json.JSONDecodeError as e:
                print(f"JSON解析错误 (行 {line_num + 1}): {e}")
                continue
    
    print(f"文件行数: {line_count}")
    print(f"包含messages字段的行数: {has_messages_field}")
    
    if sample_data and 'messages' in sample_data:
        messages = sample_data['messages']
        print(f"样本messages数量: {len(messages)}")
        for i, msg in enumerate(messages):
            print(f"  消息 {i+1}: role={msg.get('role', 'N/A')}, content长度={len(msg.get('content', ''))}")
    
    return {
        'total_lines': line_count,
        'messages_count': has_messages_field,
        'sample_data': sample_data
    }


def convert_jsonl_to_wocot(input_file: str, output_file: str) -> str:
    """
    将JSONL文件转换为不含CoT的格式
    
    Args:
        input_file: 输入JSONL文件路径
        output_file: 输出JSONL文件路径
        
    Returns:
        输出文件路径
    """
    print(f"开始转换: {input_file} -> {output_file}")
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 {input_file}")
        return ""
    
    processed_count = 0
    replacement_count = 0
    error_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile):
            if line_num % 100 == 0:
                print(f"处理行 {line_num + 1}...")
            
            try:
                # 解析JSON行
                data = json.loads(line.strip())
                
                # 检查是否有messages字段
                if 'messages' not in data:
                    print(f"警告: 行 {line_num + 1} 缺少messages字段")
                    # 保持原数据不变
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                    processed_count += 1
                    continue
                
                # 处理messages字段
                messages = data['messages']
                new_messages, has_replacement = process_messages(messages)
                
                # 更新数据
                data['messages'] = new_messages
                
                # 写入输出文件
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                processed_count += 1
                
                if has_replacement:
                    replacement_count += 1
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误 (行 {line_num + 1}): {e}")
                error_count += 1
                continue
            except (ValueError, KeyError, TypeError) as e:
                print(f"处理错误 (行 {line_num + 1}): {e}")
                error_count += 1
                continue
    
    print(f"转换完成: {processed_count} 行成功处理, {replacement_count} 行发生替换, {error_count} 行出错")
    return output_file


def validate_conversion(input_file: str, output_file: str, num_samples: int = 5):
    """
    验证转换结果
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        num_samples: 验证样本数量
    """
    print("\n验证转换结果...")
    print("=" * 50)
    
    if not os.path.exists(output_file):
        print(f"错误: 输出文件不存在 {output_file}")
        return
    
    # 统计行数
    with open(input_file, 'r', encoding='utf-8') as f:
        input_lines = sum(1 for _ in f)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        output_lines = sum(1 for _ in f)
    
    print(f"输入文件行数: {input_lines}")
    print(f"输出文件行数: {output_lines}")
    
    if input_lines != output_lines:
        print("警告: 输入和输出文件行数不一致")
    
    # 验证样本
    cot_found_in_input = 0
    cot_found_in_output = 0
    output_found_in_output = 0
    think_found_in_input = 0
    think_found_in_output = 0
    reasoning_found_in_input = 0
    reasoning_found_in_output = 0
    
    with open(input_file, 'r', encoding='utf-8') as input_f, \
         open(output_file, 'r', encoding='utf-8') as output_f:
        
        for i in range(min(num_samples, input_lines)):
            input_line = input_f.readline().strip()
            output_line = output_f.readline().strip()
            
            try:
                input_data = json.loads(input_line)
                output_data = json.loads(output_line)
                
                print(f"\n样本 {i+1}:")
                
                # 检查输入文件
                input_user_content = ""
                input_assistant_content = ""
                if 'messages' in input_data:
                    for msg in input_data['messages']:
                        if msg.get('role') == 'user':
                            input_user_content = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            input_assistant_content = msg.get('content', '')
                
                if COT_FORMAT.strip() in input_user_content:
                    cot_found_in_input += 1
                
                if '<think>' in input_assistant_content and '</think>' in input_assistant_content:
                    think_found_in_input += 1
                
                if "Let me write the SQL query with reasoning." in input_assistant_content:
                    reasoning_found_in_input += 1
                
                # 检查输出文件
                output_user_content = ""
                output_assistant_content = ""
                if 'messages' in output_data:
                    for msg in output_data['messages']:
                        if msg.get('role') == 'user':
                            output_user_content = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            output_assistant_content = msg.get('content', '')
                
                # 验证CoT格式替换
                if COT_FORMAT.strip() in output_user_content:
                    cot_found_in_output += 1
                    print("  ❌ User CoT格式未被替换")
                else:
                    print("  ✅ User CoT格式已替换")
                
                if OUTPUT_FORMAT.strip() in output_user_content:
                    output_found_in_output += 1
                    print("  ✅ User输出格式已添加")
                else:
                    print("  ❌ User输出格式未添加")
                
                # 验证think标签移除
                if '<think>' in output_assistant_content or '</think>' in output_assistant_content:
                    think_found_in_output += 1
                    print("  ❌ Assistant think标签未被移除")
                else:
                    print("  ✅ Assistant think标签已移除")
                
                # 验证reasoning文本移除
                if "Let me write the SQL query with reasoning." in output_assistant_content:
                    reasoning_found_in_output += 1
                    print("  ❌ Assistant reasoning文本未被移除")
                else:
                    print("  ✅ Assistant reasoning文本已移除")
                
                print(f"  User内容长度: 输入={len(input_user_content)}, 输出={len(output_user_content)}")
                print(f"  Assistant内容长度: 输入={len(input_assistant_content)}, 输出={len(output_assistant_content)}")
                
            except json.JSONDecodeError as e:
                print(f"  验证错误 (样本 {i+1}): {e}")
                continue
    
    print(f"\n验证汇总 (前{num_samples}个样本):")
    print(f"输入文件中包含CoT格式: {cot_found_in_input}/{num_samples}")
    print(f"输出文件中仍包含CoT格式: {cot_found_in_output}/{num_samples}")
    print(f"输出文件中包含新格式: {output_found_in_output}/{num_samples}")
    print(f"输入文件中包含think标签: {think_found_in_input}/{num_samples}")
    print(f"输出文件中仍包含think标签: {think_found_in_output}/{num_samples}")
    print(f"输入文件中包含reasoning文本: {reasoning_found_in_input}/{num_samples}")
    print(f"输出文件中仍包含reasoning文本: {reasoning_found_in_output}/{num_samples}")
    
    cot_success = cot_found_in_output == 0 and output_found_in_output > 0
    think_success = think_found_in_output == 0
    reasoning_success = reasoning_found_in_output == 0
    
    if cot_success and think_success and reasoning_success:
        print("✅ 所有格式替换验证通过!")
    else:
        if not cot_success:
            print("❌ CoT格式替换可能有问题")
        if not think_success:
            print("❌ Think标签移除可能有问题")
        if not reasoning_success:
            print("❌ Reasoning文本移除可能有问题")


def main():
    """主函数"""
    # 文件路径配置
    # input_file = "outputs/llm_response/split/test_863.jsonl"
    # input_file = "outputs/llm_response/split/train_4312.jsonl"
    input_file = "outputs/llm_response/split/dev_862.jsonl"

    # output_file = "outputs/llm_response/split/test_863.wocot.jsonl"
    # output_file = "outputs/llm_response/split/train_4312.wocot.jsonl"
    output_file = "outputs/llm_response/split/dev_862.wocot.jsonl"

    # 初始化格式内容
    print("=== 初始化格式内容 ===")
    initialize_formats()
    
    # 分析输入文件
    print("\n=== 分析输入文件 ===")
    file_info = analyze_input_file(input_file)
    
    if not file_info:
        print("输入文件分析失败，终止处理")
        return
    
    # 执行转换
    print("\n=== 执行数据转换 ===")
    result_file = convert_jsonl_to_wocot(input_file, output_file)
    
    if not result_file:
        print("数据转换失败")
        return
    
    # 验证结果
    print("\n=== 验证转换结果 ===")
    validate_conversion(input_file, result_file, num_samples=5)
    
    print(f"\n任务完成! 输出文件: {result_file}")


if __name__ == "__main__":
    main()
