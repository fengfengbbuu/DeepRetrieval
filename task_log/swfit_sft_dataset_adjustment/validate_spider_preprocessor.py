#!/usr/bin/env python3
"""
Validation script for SpiderTrainPreprocessor
"""

import pandas as pd
import json
import ast
import re
from typing import Dict, List, Any, Optional
import random

class SpiderTrainPreprocessor:
    """
    Preprocessor for Spider Train dataset that converts prompt field with <|im_start|> format to messages format.
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


def validate_preprocessor():
    """Validate the SpiderTrainPreprocessor implementation"""
    
    # Load the data
    print("Loading spider train data...")
    df = pd.read_parquet('code/data/sql/spider/train.parquet')
    print(f"Loaded {len(df)} rows")
    
    # Create preprocessor instance
    preprocessor = SpiderTrainPreprocessor()
    
    # Sample 5 random rows for validation
    sample_indices = random.sample(range(len(df)), min(5, len(df)))
    print(f"Sampling rows: {sample_indices}")
    
    validation_results = []
    
    for idx in sample_indices:
        row = df.iloc[idx]
        print(f"\n=== Validating Row {idx} ===")
        
        # Extract the raw data
        prompt_data = row['prompt']
        reward_model = row['reward_model']
        
        print(f"Prompt type: {type(prompt_data)}")
        print(f"Reward model type: {type(reward_model)}")
        
        # Convert numpy array to list for easier handling
        if hasattr(prompt_data, 'tolist'):
            prompt_data = prompt_data.tolist()
        
        # Process with current preprocessor
        processed_row = {'prompt': prompt_data, 'reward_model': reward_model}
        result = preprocessor.preprocess(processed_row)
        
        if result is None:
            print("❌ Preprocessing failed - returned None")
            validation_results.append({
                'row_idx': idx,
                'status': 'failed',
                'error': 'Preprocessing returned None'
            })
            continue
            
        messages = result.get('messages', [])
        print(f"✅ Preprocessing succeeded - got {len(messages)} messages")
        
        # Validate each message
        valid_messages = True
        for i, msg in enumerate(messages):
            print(f"  Message {i}: role='{msg['role']}', content_length={len(msg['content'])}")
            
            # Check for remaining tokens
            if '<|im_start|>' in msg['content'] or '<|im_end|>' in msg['content']:
                print(f"  ❌ Message {i} still contains tokens!")
                valid_messages = False
                
            # Check for required tags in assistant messages
            if msg['role'] == 'assistant':
                if '<answer>' not in msg['content'] or '</answer>' not in msg['content']:
                    print(f"  ❌ Assistant message {i} missing <answer> tags!")
                    valid_messages = False
                if '<think>' not in msg['content'] or '</think>' not in msg['content']:
                    print(f"  ❌ Assistant message {i} missing <think> tags!")
                    valid_messages = False
        
        if valid_messages:
            print("✅ All messages are valid")
            validation_results.append({
                'row_idx': idx,
                'status': 'success',
                'messages_count': len(messages),
                'messages': messages
            })
        else:
            print("❌ Some messages are invalid")
            validation_results.append({
                'row_idx': idx,
                'status': 'invalid_messages',
                'messages': messages
            })
    
    # Save validation results
    with open('task_log/swfit_sft_dataset_adjustment/validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Validation Summary ===")
    success_count = sum(1 for r in validation_results if r['status'] == 'success')
    print(f"Successful validations: {success_count}/{len(validation_results)}")
    
    return validation_results


if __name__ == "__main__":
    results = validate_preprocessor()