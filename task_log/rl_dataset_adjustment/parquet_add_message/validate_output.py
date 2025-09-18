#!/usr/bin/env python3
"""
Validation script based on hf_datasets_load_val.py
"""
import datasets
from typing import Literal

def validate_converted_parquet():
    """
    Validate the converted parquet file using the same method as hf_datasets_load_val.py
    """
    parquet_file = "/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/train.messages.parquet"
    split_name: Literal['train', 'val', 'test'] = 'train'
    
    print(f"Loading converted parquet file: {parquet_file}")
    dataframe = datasets.load_dataset("parquet", data_files=parquet_file)[split_name]
    print(dataframe)
    
    print("\nChecking the structure:")
    print(f"Number of rows: {len(dataframe)}")
    print(f"Columns: {dataframe.column_names}")
    
    print("\nSample prompt data:")
    if len(dataframe) > 0:
        sample_prompt = dataframe['prompt'][0]
        print(f"Type: {type(sample_prompt)}")
        print(f"Content: {sample_prompt}")
        
        # Check if it matches the expected messages format
        if isinstance(sample_prompt, list):
            print(f"Number of messages: {len(sample_prompt)}")
            for i, msg in enumerate(sample_prompt):
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    print(f"Message {i}: role='{msg['role']}', content_length={len(msg['content'])}")
                else:
                    print(f"Message {i}: Invalid format - {msg}")
        else:
            print("Warning: Prompt is not a list!")
    
    print("\nValidation completed!")

if __name__ == "__main__":
    validate_converted_parquet()
