#!/usr/bin/env python3
"""
Script to convert train.parquet prompt data to messages format
Fixed version that handles numpy arrays
"""
import pandas as pd
import numpy as np
import json
import re
from typing import List, Dict, Any

def parse_prompt_to_messages(prompt_content: str) -> List[Dict[str, str]]:
    """
    Parse the prompt content and extract system and user messages.
    The prompt contains <|im_start|>system and <|im_start|>user tags.
    """
    messages = []
    
    # Extract system message
    system_match = re.search(r'<\|im_start\|>system\n(.*?)<\|im_end\|>', prompt_content, re.DOTALL)
    if system_match:
        system_content = system_match.group(1).strip()
        messages.append({
            "role": "system",
            "content": system_content
        })
    
    # Extract user message
    user_match = re.search(r'<\|im_start\|>user\n(.*?)<\|im_end\|>', prompt_content, re.DOTALL)
    if user_match:
        user_content = user_match.group(1).strip()
        messages.append({
            "role": "user", 
            "content": user_content
        })
    
    return messages

def convert_parquet_to_messages():
    """
    Convert the train.parquet file to messages format
    """
    # Load the original parquet file
    # input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/train.parquet"
    # input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/test.parquet"
    # input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/val.parquet"
    # input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/train.parquet"
    # input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/val.parquet"
    input_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/test.parquet"

    # output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/train.messages.wcot.parquet"
    # output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/test.messages.wcot.parquet"
    # output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/val.messages.wcot.parquet"
    # output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/train.messages.wcot.parquet"
    # output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/val.messages.wcot.parquet"
    output_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/test.messages.wcot.parquet"

    print("Loading parquet file...")
    df = pd.read_parquet(input_file)
    
    print(f"Processing {len(df)} rows...")
    
    # Convert each prompt to messages format
    converted_data = []
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"Processing row {idx}/{len(df)}")
        
        # Get the prompt content - handle numpy array
        prompt_data = row['prompt']
        
        # Convert numpy array to list if needed
        if isinstance(prompt_data, np.ndarray):
            prompt_data = prompt_data.tolist()
        
        if isinstance(prompt_data, list) and len(prompt_data) > 0:
            prompt_content = prompt_data[0]['content']
        else:
            print(f"Warning: Unexpected prompt format at row {idx}: {type(prompt_data)}")
            continue
        
        # Parse to messages format
        messages = parse_prompt_to_messages(prompt_content)
        
        if not messages:
            print(f"Warning: No messages extracted from row {idx}")
            continue
        
        # Create new row with messages format
        new_row = row.copy()
        new_row['prompt'] = messages  # Keep the original field name as required
        
        converted_data.append(new_row)
    
    # Create new dataframe
    converted_df = pd.DataFrame(converted_data)
    
    print(f"Converted {len(converted_df)} rows")
    print("Sample converted data:")
    if len(converted_df) > 0:
        print(f"First prompt messages: {converted_df['prompt'].iloc[0]}")
    
    # Save to new parquet file
    print(f"Saving to {output_file}...")
    converted_df.to_parquet(output_file, index=False)
    
    print("Conversion completed!")
    return output_file

if __name__ == "__main__":
    convert_parquet_to_messages()
