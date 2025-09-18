#!/usr/bin/env python3
"""
Script to categorize and analyze the different types of failures in requirement 2.
"""

import json
import re
from typing import Dict, List, Any
from collections import defaultdict

def load_jsonl_data(file_path: str) -> List[Dict]:
    """Load JSONL data from file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    return data

def extract_prompt_content(meta_info: Dict) -> str:
    """Extract content from meta_info.prompt[0].content."""
    try:
        return meta_info['prompt'][0]['content']
    except (KeyError, IndexError, TypeError):
        return ""

def extract_last_answer_content(combined_text: str) -> str:
    """Extract the last <answer>...</answer> content from the combined text."""
    answer_pattern = r'<answer>(.*?)</answer>'
    answer_matches = re.findall(answer_pattern, combined_text, re.DOTALL)
    
    # Filter out template examples
    filtered_answers = []
    for match in answer_matches:
        content = match.strip()
        # Skip empty or template examples
        if content and content not in ['', '{\n    "sql": "SELECT ... (in one line)"\n} ']:
            filtered_answers.append(content)
    
    return filtered_answers[-1] if filtered_answers else ""

def categorize_failure(last_answer_content: str) -> Dict[str, Any]:
    """Categorize the type of failure based on the last answer content."""
    try:
        answer_dict = json.loads(last_answer_content)
        
        if isinstance(answer_dict, dict):
            if 'sql' in answer_dict:
                sql_value = answer_dict['sql']
                if isinstance(sql_value, str) and sql_value.strip().upper().startswith('SELECT'):
                    return {
                        'type': 'valid_sql',
                        'description': 'Contains valid SQL query',
                        'sql': sql_value
                    }
                else:
                    return {
                        'type': 'invalid_sql',
                        'description': 'Contains sql key but not a valid SELECT statement',
                        'sql': sql_value
                    }
            elif 'error' in answer_dict:
                return {
                    'type': 'error_response',
                    'description': 'Contains error message instead of SQL',
                    'error': answer_dict['error']
                }
            else:
                return {
                    'type': 'other_dict',
                    'description': 'Dictionary without sql or error key',
                    'content': answer_dict
                }
        else:
            return {
                'type': 'not_dict',
                'description': 'Not a dictionary',
                'content': answer_dict
            }
    except json.JSONDecodeError as e:
        return {
            'type': 'json_parse_error',
            'description': f'JSON parsing failed: {str(e)}',
            'raw_content': last_answer_content
        }

def analyze_failed_records_detailed(data: List[Dict], failed_indices: List[int]) -> Dict[str, Any]:
    """Analyze failed records with detailed categorization."""
    analysis_results = {
        'total_failed': len(failed_indices),
        'categories': defaultdict(list),
        'detailed_records': []
    }
    
    for idx in failed_indices:
        if idx >= len(data):
            print(f"Warning: Index {idx} is out of range (max: {len(data)-1})")
            continue
            
        record = data[idx]
        
        # Extract prompt content and response
        prompt_content = extract_prompt_content(record.get('meta_info', {}))
        response = record.get('response', '')
        combined_text = prompt_content + response
        
        # Extract last answer content
        last_answer_content = extract_last_answer_content(combined_text)
        
        # Categorize the failure
        failure_category = categorize_failure(last_answer_content)
        
        # Extract question and other metadata
        question = record.get('meta_info', {}).get('question', '')
        db_id = record.get('meta_info', {}).get('db_id', '')
        
        record_analysis = {
            'index': idx,
            'question': question,
            'db_id': db_id,
            'last_answer_content': last_answer_content,
            'failure_category': failure_category
        }
        
        analysis_results['categories'][failure_category['type']].append(record_analysis)
        analysis_results['detailed_records'].append(record_analysis)
    
    return analysis_results

def save_detailed_analysis(analysis_results: Dict[str, Any], output_file: str):
    """Save detailed analysis results to a file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Detailed Failure Analysis - Requirement 2\n\n")
        f.write(f"**Total failed records:** {analysis_results['total_failed']}\n\n")
        
        f.write("## Failure Categories Summary\n\n")
        for category_type, records in analysis_results['categories'].items():
            f.write(f"- **{category_type}:** {len(records)} records\n")
        f.write("\n")
        
        # Detailed analysis by category
        for category_type, records in analysis_results['categories'].items():
            f.write(f"## Category: {category_type}\n\n")
            f.write(f"**Count:** {len(records)}\n")
            f.write(f"**Description:** {records[0]['failure_category']['description']}\n\n")
            
            f.write("**Records:**\n")
            for record in records:
                f.write(f"- Index {record['index']}: {record['question'][:100]}...\n")
            f.write("\n")
            
            # Show examples
            if records:
                f.write("**Example (Index {}):**\n".format(records[0]['index']))
                f.write(f"Question: {records[0]['question']}\n")
                f.write(f"Database: {records[0]['db_id']}\n")
                f.write("Last Answer Content:\n")
                f.write(f"```\n{records[0]['last_answer_content']}\n```\n\n")
            f.write("---\n\n")
        
        # Complete list of all failed records
        f.write("## Complete List of Failed Records\n\n")
        for record in analysis_results['detailed_records']:
            f.write(f"### Index {record['index']}\n")
            f.write(f"**Question:** {record['question']}\n")
            f.write(f"**Database:** {record['db_id']}\n")
            f.write(f"**Failure Type:** {record['failure_category']['type']}\n")
            f.write(f"**Description:** {record['failure_category']['description']}\n")
            f.write("**Last Answer Content:**\n")
            f.write(f"```\n{record['last_answer_content']}\n```\n\n")

def main():
    """Main function."""
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/task_log/swfit_sft_dataset_adjustment/add_thinking/detailed_failure_analysis.txt"
    
    # Failed indices from the analysis results
    failed_indices = [256, 2225, 2650, 2999, 3047, 3899, 5924, 6625, 6640, 7294, 7356]
    
    print("Loading data...")
    data = load_jsonl_data(input_file)
    print(f"Loaded {len(data)} records")
    
    print(f"Analyzing {len(failed_indices)} failed records with detailed categorization...")
    analysis_results = analyze_failed_records_detailed(data, failed_indices)
    
    print("Saving detailed analysis results...")
    save_detailed_analysis(analysis_results, output_file)
    
    print(f"\nDetailed analysis complete!")
    print(f"Results saved to: {output_file}")
    
    # Print summary
    print(f"\nFailure categories:")
    for category_type, records in analysis_results['categories'].items():
        print(f"- {category_type}: {len(records)} records")

if __name__ == "__main__":
    main()

