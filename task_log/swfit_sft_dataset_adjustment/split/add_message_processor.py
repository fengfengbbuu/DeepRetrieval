#!/usr/bin/env python3
"""
为Spider数据集添加messages字段的处理器
复用validate_spider_preprocessor.py中的SpiderTrainPreprocessor逻辑
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class SpiderTrainPreprocessor:
    """
    Preprocessor for Spider Train dataset that converts prompt field with <|im_start|> format to messages format.
    复用自validate_spider_preprocessor.py
    """
    
    def preprocess(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert prompt field containing <|im_start|> format to standard messages format.
        Combines assistant content from prompt with ground truth SQL from reward_model.
        
        Args:
            row: Dictionary containing the data row with 'prompt' and 'reward_model' fields
            
        Returns:
            Dictionary with 'messages' field in standard format, or None if processing fails
        """
        try:
            # Extract prompt field
            prompt_data = row.get('prompt')
            reward_model = row.get('reward_model', {})
            
            if not prompt_data:
                return None
                
            # Parse the prompt data (it's a numpy array containing a list)
            if hasattr(prompt_data, 'tolist'):
                prompt_data = prompt_data.tolist()
            elif isinstance(prompt_data, str):
                import ast
                prompt_data = ast.literal_eval(prompt_data)
            
            # Extract content from the first item in the list
            if not prompt_data or not isinstance(prompt_data, list) or len(prompt_data) == 0:
                return None
                
            content = prompt_data[0].get('content', '')
            if not content:
                return None
            
            # Parse the content string to extract messages
            messages = self._parse_im_start_content(content, reward_model)
            if not messages:
                return None
                
            return {'messages': messages}
            
        except Exception as e:
            # Log error but don't fail the entire processing
            print(f"Error processing Spider Train row: {e}")
            return None
    
    def _parse_im_start_content(self, content: str, reward_model: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Parse content string with <|im_start|> and <|im_end|> markers into messages format.
        Completes assistant content with ground truth SQL from reward_model.
        
        Args:
            content: String containing the conversation with special markers
            reward_model: Dictionary containing ground truth SQL
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        import re
        import json
        
        # Split by the special markers
        parts = re.split(r'<\|im_start\|>|<\|im_end\|>', content)
        
        messages = []
        
        # Process every other part (skip empty strings)
        for i in range(1, len(parts), 2):
            if i < len(parts) and parts[i].strip():
                role_content = parts[i].strip()
                lines = role_content.split('\n', 1)  # Split only on first newline
                
                if len(lines) >= 1:
                    role = lines[0].strip()
                    content_text = lines[1] if len(lines) > 1 else ""
                    
                    # Only process valid roles
                    if role in ['system', 'user', 'assistant']:
                        # Special handling for assistant role
                        if role == 'assistant':
                            content_text = self._complete_assistant_content(content_text, reward_model)
                        
                        messages.append({
                            'role': role,
                            'content': content_text.strip()
                        })
        
        return messages
    
    def _complete_assistant_content(self, partial_content: str, reward_model: Dict[str, Any]) -> str:
        """
        Complete the assistant content by adding the ground truth SQL in proper format.
        
        Args:
            partial_content: Partial assistant content from prompt
            reward_model: Dictionary containing ground truth SQL
            
        Returns:
            Complete assistant content with <think> and <answer> tags
        """
        # Extract ground truth SQL
        ground_truth_sql = ""
        if reward_model and 'ground_truth' in reward_model and 'target' in reward_model['ground_truth']:
            ground_truth_sql = reward_model['ground_truth']['target']
        
        # Complete the content
        if '<think>' in partial_content and '</think>' not in partial_content:
            # Add thinking content and close think tag
            thinking_content = "I need to analyze the database schema and write a SQL query to answer the user's question."
            complete_content = partial_content + thinking_content + "\n</think>\n\n"
        else:
            # Add complete think section
            thinking_content = "I need to analyze the database schema and write a SQL query to answer the user's question."
            complete_content = partial_content + "<think>\n" + thinking_content + "\n</think>\n\n"
        
        # Add answer section with SQL
        if ground_truth_sql:
            sql_json = json.dumps({"sql": ground_truth_sql})
            complete_content += f"<answer>\n{sql_json}\n</answer>"
        else:
            complete_content += "<answer>\n{\n    \"sql\": \"SELECT * FROM table\"\n}\n</answer>"
        
        return complete_content


def process_spider_data(input_file: str, output_file: str):
    """
    处理Spider数据，为每条数据添加messages字段
    
    Args:
        input_file: 输入的parquet文件路径
        output_file: 输出的jsonl文件路径
    """
    print(f"开始处理Spider数据: {input_file}")
    
    # 加载数据
    print("正在加载数据...")
    df = pd.read_parquet(input_file)
    print(f"加载了 {len(df)} 行数据")
    
    # 创建预处理器
    preprocessor = SpiderTrainPreprocessor()
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 处理每一行数据
    processed_count = 0
    failed_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            if idx % 1000 == 0:
                print(f"处理进度: {idx}/{len(df)} ({idx/len(df)*100:.1f}%)")
            
            # 转换为字典格式，处理numpy数组
            row_dict = row.to_dict()
            
            # 处理numpy数组，转换为可序列化的格式
            for key, value in row_dict.items():
                if hasattr(value, 'tolist'):
                    row_dict[key] = value.tolist()
            
            # 处理数据，添加messages字段
            result = preprocessor.preprocess(row_dict)
            
            if result is None:
                failed_count += 1
                print(f"警告: 第 {idx} 行处理失败")
                continue
            
            # 合并原始数据和messages字段
            processed_row = row_dict.copy()
            processed_row.update(result)
            
            # 写入JSONL文件
            f.write(json.dumps(processed_row, ensure_ascii=False) + '\n')
            processed_count += 1
    
    print(f"\n处理完成!")
    print(f"成功处理: {processed_count} 行")
    print(f"处理失败: {failed_count} 行")
    print(f"输出文件: {output_file}")
    
    return processed_count, failed_count


def validate_output(output_file: str, sample_size: int = 5):
    """
    验证输出文件
    
    Args:
        output_file: 输出文件路径
        sample_size: 验证样本数量
    """
    print(f"\n验证输出文件: {output_file}")
    
    if not os.path.exists(output_file):
        print("❌ 输出文件不存在!")
        return False
    
    # 读取文件并验证格式
    lines = []
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            lines.append(line.strip())
    
    print(f"总行数: {len(lines)}")
    
    # 验证前几行
    valid_count = 0
    for i, line in enumerate(lines[:sample_size]):
        try:
            data = json.loads(line)
            if 'messages' in data:
                messages = data['messages']
                print(f"第 {i+1} 行: {len(messages)} 个消息")
                for j, msg in enumerate(messages):
                    if 'role' in msg and 'content' in msg:
                        print(f"  消息 {j+1}: role='{msg['role']}', content长度={len(msg['content'])}")
                    else:
                        print(f"  消息 {j+1}: ❌ 缺少role或content字段")
                        break
                else:
                    valid_count += 1
            else:
                print(f"第 {i+1} 行: ❌ 缺少messages字段")
        except json.JSONDecodeError as e:
            print(f"第 {i+1} 行: ❌ JSON解析错误: {e}")
    
    print(f"验证结果: {valid_count}/{sample_size} 行有效")
    return valid_count == sample_size


if __name__ == "__main__":
    # 设置输入输出路径
    input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/test.parquet"
    output_file = "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl"
    
    print("开始为Spider数据添加messages字段")
    print("=" * 60)
    
    try:
        # 处理数据
        processed_count, failed_count = process_spider_data(input_file, output_file)
        
        # 验证输出
        is_valid = validate_output(output_file)
        
        if is_valid:
            print("\n" + "=" * 60)
            print("✅ 任务完成! messages字段已成功添加")
            print(f"输出文件: {output_file}")
        else:
            print("\n" + "=" * 60)
            print("❌ 输出验证失败!")
            
    except Exception as e:
        print(f"\n❌ 处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
