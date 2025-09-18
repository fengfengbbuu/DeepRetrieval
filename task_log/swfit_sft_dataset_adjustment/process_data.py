#!/usr/bin/env python3
"""
数据转换脚本：将 train_parquet_all.final.jsonl 转换为包含 messages 字段的格式
"""

import json
import re
from typing import Dict, List, Any, Optional

class MessageProcessor:
    """
    处理数据并添加 messages 字段的处理器
    """
    
    def process_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理单行数据，添加 messages 字段
        
        Args:
            row: 输入的数据行
            
        Returns:
            处理后的数据行，包含 messages 字段
        """
        try:
            # 获取必要字段
            meta_info = row.get('meta_info', {})
            prompt_data = meta_info.get('prompt', [])
            response = row.get('response', '')
            
            if not prompt_data or not response:
                return None
            
            # 提取 prompt 内容
            prompt_content = prompt_data[0].get('content', '') if prompt_data else ''
            if not prompt_content:
                return None
            
            # 拼接 prompt 内容和 response
            full_content = prompt_content + response
            
            # 解析为 messages 格式
            messages = self._parse_to_messages(full_content)
            if not messages:
                return None
            
            # 添加 messages 字段到原数据
            result = row.copy()
            result['messages'] = messages
            
            return result
            
        except Exception as e:
            print(f"Error processing row: {e}")
            return None
    
    def _parse_to_messages(self, content: str) -> List[Dict[str, str]]:
        """
        将包含 <|im_start|> 标记的内容解析为 messages 格式
        
        Args:
            content: 包含特殊标记的内容字符串
            
        Returns:
            messages 列表
        """
        # 使用正则表达式分割标记
        parts = re.split(r'<\|im_start\|>|<\|im_end\|>', content)
        
        messages = []
        
        # 处理每个部分（跳过空字符串）
        for i in range(1, len(parts), 2):
            if i < len(parts) and parts[i].strip():
                role_content = parts[i].strip()
                lines = role_content.split('\n', 1)  # 只分割第一个换行符
                
                if len(lines) >= 1:
                    role = lines[0].strip()
                    content_text = lines[1] if len(lines) > 1 else ""
                    
                    # 只处理有效的角色
                    if role in ['system', 'user', 'assistant']:
                        messages.append({
                            'role': role,
                            'content': content_text.strip()
                        })
        
        return messages


def process_jsonl_file(input_file: str, output_file: str):
    """
    处理整个 JSONL 文件
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    processor = MessageProcessor()
    
    processed_count = 0
    total_count = 0
    error_count = 0
    
    print(f"开始处理文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            total_count += 1
            
            if line_num % 1000 == 0:
                print(f"已处理 {line_num} 行...")
            
            try:
                # 解析 JSON 行
                row = json.loads(line.strip())
                
                # 处理数据
                processed_row = processor.process_row(row)
                
                if processed_row:
                    # 写入处理后的数据
                    outfile.write(json.dumps(processed_row, ensure_ascii=False) + '\n')
                    processed_count += 1
                else:
                    error_count += 1
                    print(f"第 {line_num} 行处理失败")
                    
            except json.JSONDecodeError as e:
                error_count += 1
                print(f"第 {line_num} 行 JSON 解析错误: {e}")
            except Exception as e:
                error_count += 1
                print(f"第 {line_num} 行处理错误: {e}")
    
    print(f"\n处理完成!")
    print(f"总行数: {total_count}")
    print(f"成功处理: {processed_count}")
    print(f"失败行数: {error_count}")
    print(f"输出文件: {output_file}")


def validate_sample(input_file: str, num_samples: int = 3):
    """
    验证处理结果的样本
    
    Args:
        input_file: 输入文件路径
        num_samples: 验证样本数量
    """
    processor = MessageProcessor()
    
    print(f"验证样本处理结果...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
                
            try:
                row = json.loads(line.strip())
                processed_row = processor.process_row(row)
                
                if processed_row and 'messages' in processed_row:
                    messages = processed_row['messages']
                    print(f"\n样本 {i+1}:")
                    print(f"  消息数量: {len(messages)}")
                    
                    for j, msg in enumerate(messages):
                        print(f"  消息 {j+1}: role='{msg['role']}', content_length={len(msg['content'])}")
                        
                        # 检查是否还有未处理的标记
                        if '<|im_start|>' in msg['content'] or '<|im_end|>' in msg['content']:
                            print(f"    ⚠️  消息 {j+1} 仍包含未处理的标记!")
                        
                        # 显示内容预览
                        content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                        print(f"    内容预览: {content_preview}")
                else:
                    print(f"样本 {i+1}: 处理失败")
                    
            except Exception as e:
                print(f"样本 {i+1}: 验证错误 - {e}")


if __name__ == "__main__":
    input_file = "outputs/llm_response/train_parquet_all.final.jsonl"
    output_file = "outputs/llm_response/train_parquet_all.final.message.jsonl"
    
    # 先验证几个样本
    print("=== 验证样本 ===")
    validate_sample(input_file, num_samples=3)
    
    print("\n=== 开始批量处理 ===")
    process_jsonl_file(input_file, output_file)
    
    print("\n=== 验证输出结果 ===")
    validate_sample(output_file, num_samples=3)
