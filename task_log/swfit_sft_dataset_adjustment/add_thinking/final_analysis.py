#!/usr/bin/env python3
"""
Final analysis script using the most reasonable interpretation of the requirements.
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

def validate_requirement_1(combined_text: str) -> bool:
    """
    Requirement 1: Check if combined text contains at least 1 <think>...</think> and 1 <answer>...</answer> patterns.
    We exclude template examples from the prompt.
    """
    think_pattern = r'<think>.*?</think>'
    answer_pattern = r'<answer>.*?</answer>'
    
    think_matches = re.findall(think_pattern, combined_text, re.DOTALL)
    answer_matches = re.findall(answer_pattern, combined_text, re.DOTALL)
    
    # Filter out template examples (empty or placeholder content)
    filtered_think_matches = []
    for match in think_matches:
        content = match.replace('<think>', '').replace('</think>', '').strip()
        # Skip empty or template examples
        if content and content not in ['', '[thinking process]']:
            filtered_think_matches.append(match)
    
    filtered_answer_matches = []
    for match in answer_matches:
        content = match.replace('<answer>', '').replace('</answer>', '').strip()
        # Skip empty or template examples
        if content and content not in ['', '{\n    "sql": "SELECT ... (in one line)"\n} ']:
            filtered_answer_matches.append(match)
    
    return len(filtered_think_matches) >= 1 and len(filtered_answer_matches) >= 1

def validate_requirement_2(combined_text: str) -> bool:
    """
    Requirement 2: Check if the last <answer>...</answer> contains a valid SQL dictionary.
    """
    answer_pattern = r'<answer>(.*?)</answer>'
    answer_matches = re.findall(answer_pattern, combined_text, re.DOTALL)
    
    if not answer_matches:
        return False
    
    # Get the last answer
    last_answer = answer_matches[-1].strip()
    
    try:
        # Try to parse as JSON
        answer_dict = json.loads(last_answer)
        
        # Check if it's a dict with only 'sql' key
        if isinstance(answer_dict, dict) and len(answer_dict) == 1 and 'sql' in answer_dict:
            sql_value = answer_dict['sql']
            # Check if sql value looks like a SQL query
            if isinstance(sql_value, str) and sql_value.strip().upper().startswith('SELECT'):
                return True
    except (json.JSONDecodeError, TypeError):
        pass
    
    return False

def analyze_data_final(data: List[Dict]) -> Dict[str, Any]:
    """Analyze data and categorize based on requirements."""
    results = {
        'total_records': len(data),
        'both_requirements': [],
        'only_requirement_1': [],
        'only_requirement_2': [],
        'neither_requirement': [],
        'errors': [],
        'detailed_stats': {
            'requirement_1_stats': {'total': 0, 'valid': 0},
            'requirement_2_stats': {'total': 0, 'valid': 0}
        }
    }
    
    for idx, record in enumerate(data):
        try:
            # Extract prompt content and response
            prompt_content = extract_prompt_content(record.get('meta_info', {}))
            response = record.get('response', '')
            
            # Combine them
            combined_text = prompt_content + response
            
            # Validate requirements
            req1_valid = validate_requirement_1(combined_text)
            req2_valid = validate_requirement_2(combined_text)
            
            # Update detailed stats
            results['detailed_stats']['requirement_1_stats']['total'] += 1
            results['detailed_stats']['requirement_2_stats']['total'] += 1
            if req1_valid:
                results['detailed_stats']['requirement_1_stats']['valid'] += 1
            if req2_valid:
                results['detailed_stats']['requirement_2_stats']['valid'] += 1
            
            # Categorize
            if req1_valid and req2_valid:
                results['both_requirements'].append(idx)
            elif req1_valid and not req2_valid:
                results['only_requirement_1'].append(idx)
            elif not req1_valid and req2_valid:
                results['only_requirement_2'].append(idx)
            else:
                results['neither_requirement'].append(idx)
                
        except Exception as e:
            results['errors'].append((idx, str(e)))
    
    return results

def save_final_results(results: Dict[str, Any], output_file: str):
    """Save final analysis results to file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Final Data Analysis Results\n\n")
        f.write(f"**Total records analyzed:** {results['total_records']}\n\n")
        
        f.write("## Summary Statistics\n")
        f.write(f"- **Both requirements satisfied:** {len(results['both_requirements'])}\n")
        f.write(f"- **Only requirement 1 satisfied:** {len(results['only_requirement_1'])}\n")
        f.write(f"- **Only requirement 2 satisfied:** {len(results['only_requirement_2'])}\n")
        f.write(f"- **Neither requirement satisfied:** {len(results['neither_requirement'])}\n")
        f.write(f"- **Errors encountered:** {len(results['errors'])}\n\n")
        
        f.write("## Detailed Statistics\n")
        f.write(f"- **Requirement 1 (think/answer patterns):** {results['detailed_stats']['requirement_1_stats']['valid']}/{results['detailed_stats']['requirement_1_stats']['total']} satisfied\n")
        f.write(f"- **Requirement 2 (SQL dictionary):** {results['detailed_stats']['requirement_2_stats']['valid']}/{results['detailed_stats']['requirement_2_stats']['total']} satisfied\n\n")
        
        f.write("## Detailed Index Lists\n\n")
        f.write("### Both Requirements Satisfied\n")
        f.write(f"**Count:** {len(results['both_requirements'])}\n")
        f.write(f"**Indices:** {results['both_requirements'][:100]}{'...' if len(results['both_requirements']) > 100 else ''}\n\n")
        
        f.write("### Only Requirement 1 Satisfied\n")
        f.write(f"**Count:** {len(results['only_requirement_1'])}\n")
        f.write(f"**Indices:** {results['only_requirement_1']}\n\n")
        
        f.write("### Only Requirement 2 Satisfied\n")
        f.write(f"**Count:** {len(results['only_requirement_2'])}\n")
        f.write(f"**Indices:** {results['only_requirement_2'][:100]}{'...' if len(results['only_requirement_2']) > 100 else ''}\n\n")
        
        f.write("### Neither Requirement Satisfied\n")
        f.write(f"**Count:** {len(results['neither_requirement'])}\n")
        f.write(f"**Indices:** {results['neither_requirement']}\n\n")
        
        if results['errors']:
            f.write("### Errors\n")
            for idx, error in results['errors']:
                f.write(f"- Index {idx}: {error}\n")
        
        f.write("\n## Interpretation Notes\n")
        f.write("- **Requirement 1:** Interpreted as 'at least 1 <think>...</think> and 1 <answer>...</answer> pattern' (excluding template examples)\n")
        f.write("- **Requirement 2:** The last <answer>...</answer> must contain a valid SQL dictionary with 'sql' key\n")
        f.write("- **Template filtering:** Empty patterns and placeholder content are excluded from the count\n")

def main():
    """Main function."""
    # input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/train_parquet_all.jsonl"
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/train_parquet_all.jsonl"

    # output_file = "/root/data1/projects/RL/DeepRetrieval/scripts/final_analysis_results.txt"
    output_file = "/root/data1/projects/RL/DeepRetrieval/scripts/final_analysis_results_bird.txt"
    
    print("Loading data...")
    data = load_jsonl_data(input_file)
    print(f"Loaded {len(data)} records")
    
    print("Analyzing data...")
    results = analyze_data_final(data)
    
    print("Saving final results...")
    save_final_results(results, output_file)
    
    print("\nFinal analysis complete!")
    print(f"Results saved to: {output_file}")
    print(f"\nSummary:")
    print(f"- Total records: {results['total_records']}")
    print(f"- Both requirements: {len(results['both_requirements'])}")
    print(f"- Only requirement 1: {len(results['only_requirement_1'])}")
    print(f"- Only requirement 2: {len(results['only_requirement_2'])}")
    print(f"- Neither requirement: {len(results['neither_requirement'])}")
    print(f"- Errors: {len(results['errors'])}")

if __name__ == "__main__":
    main()
