#!/usr/bin/env python3
"""
来自任务：`no_training_analyze`
Custom metric implementation for evaluating structured output from no-training inference results.
Evaluates api_result field content against expect_output_format.txt requirements.
"""

import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class NoTrainingStructuredOutputEvaluator:
    """
    Custom metric evaluator for structured output from no-training inference results.
    
    Evaluates model outputs based on:
    1. Presence of <think>...</think> tags
    2. Presence of <answer>...</answer> tags
    3. Correct JSON format in answer content
    4. Overall format correctness according to expect_output_format.txt
    """
    
    def __init__(self):
        self.metric_name = "no_training_structured_output_format"
    
    def extract_api_result_content(self, record: Dict[str, Any]) -> str:
        """
        Extract content from api_result field.
        
        Args:
            record: The inference result record
            
        Returns:
            Extracted content string
        """
        try:
            api_result = record.get('api_result', {})
            if not api_result.get('success', False):
                return ""
            
            response = api_result.get('response', {})
            choices = response.get('choices', [])
            
            if not choices:
                return ""
            
            message = choices[0].get('message', {})
            content = message.get('content', '')
            
            return content
        except Exception as e:
            print(f"Error extracting api_result content: {e}")
            return ""
    
    def evaluate_single_output(self, content: str) -> Dict[str, Any]:
        """
        Evaluate a single model output for structured output format.
        
        Args:
            content: The model's output content string
            
        Returns:
            Dictionary containing evaluation flags and scores
        """
        result = {
            'has_think_tag': False,
            'has_answer_tag': False,
            'has_valid_json': False,
            'format_correct': False,
            'think_content': '',
            'answer_content': '',
            'json_content': None,
            'error_message': None,
            'think_tag_count': 0,
            'answer_tag_count': 0,
            'malformed_structure': False
        }
        
        try:
            # Count think tags
            think_matches = re.findall(r'<think>(.*?)</think>', content, re.DOTALL)
            result['think_tag_count'] = len(think_matches)
            if think_matches:
                result['has_think_tag'] = True
                result['think_content'] = think_matches[0].strip()
            
            # Count answer tags
            answer_matches = re.findall(r'<answer>(.*?)</answer>', content, re.DOTALL)
            result['answer_tag_count'] = len(answer_matches)
            if answer_matches:
                result['has_answer_tag'] = True
                result['answer_content'] = answer_matches[0].strip()
                
                # Try to parse JSON content
                try:
                    json_content = json.loads(result['answer_content'])
                    if isinstance(json_content, dict) and 'sql' in json_content and len(json_content) == 1:
                        result['has_valid_json'] = True
                        result['json_content'] = json_content
                except json.JSONDecodeError as e:
                    result['error_message'] = f"JSON parsing error: {str(e)}"
            
            # Check for malformed structure (multiple tags, etc.)
            if result['think_tag_count'] > 1 or result['answer_tag_count'] > 1:
                result['malformed_structure'] = True
            
            # Check overall format correctness according to expect_output_format.txt
            # Requirements:
            # 1. Has exactly one think tag
            # 2. Has exactly one answer tag
            # 3. Has valid JSON format
            # 4. No malformed structure
            if (result['think_tag_count'] == 1 and 
                result['answer_tag_count'] == 1 and 
                result['has_valid_json'] and 
                not result['malformed_structure']):
                result['format_correct'] = True
                
        except Exception as e:
            result['error_message'] = f"Evaluation error: {str(e)}"
        
        return result
    
    def evaluate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate a batch of inference records.
        
        Args:
            records: List of inference result records
            
        Returns:
            Dictionary containing batch evaluation results
        """
        results = []
        for i, record in enumerate(records):
            content = self.extract_api_result_content(record)
            result = self.evaluate_single_output(content)
            result['index'] = i
            result['original_question'] = record.get('original_data', {}).get('question', '')
            result['db_id'] = record.get('original_data', {}).get('db_id', '')
            result['data_source'] = record.get('original_data', {}).get('data_source', '')
            result['success'] = record.get('api_result', {}).get('success', False)
            results.append(result)
        
        # Calculate aggregate metrics
        total_samples = len(results)
        has_think_count = sum(1 for r in results if r['has_think_tag'])
        has_answer_count = sum(1 for r in results if r['has_answer_tag'])
        has_valid_json_count = sum(1 for r in results if r['has_valid_json'])
        format_correct_count = sum(1 for r in results if r['format_correct'])
        malformed_structure_count = sum(1 for r in results if r['malformed_structure'])
        success_count = sum(1 for r in results if r['success'])
        
        # Calculate average tag counts
        avg_think_tags = sum(r['think_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        avg_answer_tags = sum(r['answer_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        
        return {
            'total_samples': total_samples,
            'success_rate': success_count / total_samples if total_samples > 0 else 0,
            'has_think_rate': has_think_count / total_samples if total_samples > 0 else 0,
            'has_answer_rate': has_answer_count / total_samples if total_samples > 0 else 0,
            'has_valid_json_rate': has_valid_json_count / total_samples if total_samples > 0 else 0,
            'format_correct_rate': format_correct_count / total_samples if total_samples > 0 else 0,
            'malformed_structure_rate': malformed_structure_count / total_samples if total_samples > 0 else 0,
            'avg_think_tags': avg_think_tags,
            'avg_answer_tags': avg_answer_tags,
            'individual_results': results
        }

def load_inference_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load inference data from JSONL file.
    
    Args:
        file_path: Path to the inference results JSONL file
        
    Returns:
        List of inference records
    """
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    records.append(record)
    except Exception as e:
        print(f"Error loading inference file {file_path}: {e}")
    
    return records

def create_visualization(evaluation_result: Dict[str, Any], output_dir: str):
    """
    Create visualizations for no-training structured output evaluation results.
    
    Args:
        evaluation_result: The evaluation result dictionary
        output_dir: Directory to save visualizations
    """
    # Create summary statistics DataFrame
    summary_data = {
        'Metric': [
            'Success Rate',
            'Think Tag Rate', 
            'Answer Tag Rate',
            'Valid JSON Rate',
            'Format Correct Rate',
            'Malformed Structure Rate'
        ],
        'Rate': [
            evaluation_result['success_rate'],
            evaluation_result['has_think_rate'],
            evaluation_result['has_answer_rate'],
            evaluation_result['has_valid_json_rate'],
            evaluation_result['format_correct_rate'],
            evaluation_result['malformed_structure_rate']
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.bar(df_summary['Metric'], df_summary['Rate'], 
                  color=['green', 'blue', 'orange', 'red', 'purple', 'brown'])
    
    # Customize the plot
    ax.set_title('No-Training Model Structured Output Evaluation Results', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Evaluation Metrics', fontsize=12, fontweight='bold')
    ax.set_ylabel('Rate', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 1)
    
    # Add value labels on bars
    for bar, rate in zip(bars, df_summary['Rate']):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{rate:.3f}', ha='center', va='bottom', fontweight='bold')
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    # Save the plot
    plot_path = Path(output_dir) / 'no_training_evaluation_results.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    # Create detailed analysis of individual results
    individual_results = evaluation_result['individual_results']
    
    # Analyze by data source
    data_source_analysis = {}
    for result in individual_results:
        source = result['data_source']
        if source not in data_source_analysis:
            data_source_analysis[source] = {
                'total': 0,
                'format_correct': 0,
                'has_think': 0,
                'has_answer': 0,
                'has_valid_json': 0
            }
        
        data_source_analysis[source]['total'] += 1
        if result['format_correct']:
            data_source_analysis[source]['format_correct'] += 1
        if result['has_think_tag']:
            data_source_analysis[source]['has_think'] += 1
        if result['has_answer_tag']:
            data_source_analysis[source]['has_answer'] += 1
        if result['has_valid_json']:
            data_source_analysis[source]['has_valid_json'] += 1
    
    # Create data source comparison chart
    if len(data_source_analysis) > 1:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        sources = list(data_source_analysis.keys())
        format_rates = [data_source_analysis[source]['format_correct'] / data_source_analysis[source]['total'] 
                       for source in sources]
        think_rates = [data_source_analysis[source]['has_think'] / data_source_analysis[source]['total'] 
                      for source in sources]
        answer_rates = [data_source_analysis[source]['has_answer'] / data_source_analysis[source]['total'] 
                       for source in sources]
        json_rates = [data_source_analysis[source]['has_valid_json'] / data_source_analysis[source]['total'] 
                     for source in sources]
        
        x = np.arange(len(sources))
        width = 0.2
        
        ax.bar(x - 1.5*width, format_rates, width, label='Format Correct Rate', alpha=0.8)
        ax.bar(x - 0.5*width, think_rates, width, label='Think Tag Rate', alpha=0.8)
        ax.bar(x + 0.5*width, answer_rates, width, label='Answer Tag Rate', alpha=0.8)
        ax.bar(x + 1.5*width, json_rates, width, label='Valid JSON Rate', alpha=0.8)
        
        ax.set_title('Evaluation Results by Data Source', fontsize=16, fontweight='bold')
        ax.set_xlabel('Data Source', fontsize=12, fontweight='bold')
        ax.set_ylabel('Rate', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(sources)
        ax.legend()
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save the comparison plot
        comparison_plot_path = Path(output_dir) / 'no_training_data_source_comparison.png'
        plt.savefig(comparison_plot_path, dpi=300, bbox_inches='tight')
        print(f"Data source comparison plot saved to: {comparison_plot_path}")
    
    return df_summary

def analyze_error_patterns(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze error patterns in the evaluation results.
    
    Args:
        evaluation_result: The evaluation result dictionary
        
    Returns:
        Dictionary containing error analysis
    """
    individual_results = evaluation_result['individual_results']
    
    error_analysis = {
        'total_samples': len(individual_results),
        'format_correct_samples': sum(1 for r in individual_results if r['format_correct']),
        'error_patterns': {
            'missing_think_tag': 0,
            'missing_answer_tag': 0,
            'invalid_json': 0,
            'multiple_think_tags': 0,
            'multiple_answer_tags': 0,
            'malformed_structure': 0,
            'api_failure': 0
        },
        'error_examples': []
    }
    
    for result in individual_results:
        if not result['success']:
            error_analysis['error_patterns']['api_failure'] += 1
            continue
            
        if not result['format_correct']:
            if not result['has_think_tag']:
                error_analysis['error_patterns']['missing_think_tag'] += 1
            if not result['has_answer_tag']:
                error_analysis['error_patterns']['missing_answer_tag'] += 1
            if not result['has_valid_json']:
                error_analysis['error_patterns']['invalid_json'] += 1
            if result['think_tag_count'] > 1:
                error_analysis['error_patterns']['multiple_think_tags'] += 1
            if result['answer_tag_count'] > 1:
                error_analysis['error_patterns']['multiple_answer_tags'] += 1
            if result['malformed_structure']:
                error_analysis['error_patterns']['malformed_structure'] += 1
            
            # Collect error examples (first 5 of each type)
            if len(error_analysis['error_examples']) < 5:
                error_analysis['error_examples'].append({
                    'index': result['index'],
                    'question': result['original_question'][:100] + '...' if len(result['original_question']) > 100 else result['original_question'],
                    'has_think': result['has_think_tag'],
                    'has_answer': result['has_answer_tag'],
                    'has_valid_json': result['has_valid_json'],
                    'think_count': result['think_tag_count'],
                    'answer_count': result['answer_tag_count'],
                    'error_message': result.get('error_message', '')
                })
    
    return error_analysis

def main():
    """Main function to run no-training structured output evaluation"""
    # Define paths
    input_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference_results_success.jsonl"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze"
    
    print("Starting no-training structured output evaluation analysis...")
    print(f"Target file: {input_file}")
    
    # Load inference data
    records = load_inference_data(input_file)
    
    if not records:
        print("No inference data found!")
        return
    
    print(f"Loaded {len(records)} inference records")
    
    # Create evaluator and evaluate
    evaluator = NoTrainingStructuredOutputEvaluator()
    evaluation_result = evaluator.evaluate_batch(records)
    
    # Create visualizations
    df_summary = create_visualization(evaluation_result, output_dir)
    
    # Analyze error patterns
    error_analysis = analyze_error_patterns(evaluation_result)
    
    # Save detailed results to CSV
    individual_results = evaluation_result['individual_results']
    df_detailed = pd.DataFrame(individual_results)
    csv_path = Path(output_dir) / 'no_training_detailed_results.csv'
    df_detailed.to_csv(csv_path, index=False)
    print(f"Detailed results saved to: {csv_path}")
    
    # Save summary results to CSV
    summary_csv_path = Path(output_dir) / 'no_training_summary_results.csv'
    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Summary results saved to: {summary_csv_path}")
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"Total samples: {evaluation_result['total_samples']}")
    print(f"Success rate: {evaluation_result['success_rate']:.3f}")
    
    print("\n=== Format Evaluation Summary ===")
    print(f"Think Tag Rate: {evaluation_result['has_think_rate']:.3f}")
    print(f"Answer Tag Rate: {evaluation_result['has_answer_rate']:.3f}")
    print(f"Valid JSON Rate: {evaluation_result['has_valid_json_rate']:.3f}")
    print(f"Format Correct Rate: {evaluation_result['format_correct_rate']:.3f}")
    print(f"Malformed Structure Rate: {evaluation_result['malformed_structure_rate']:.3f}")
    print(f"Average Think Tags per Sample: {evaluation_result['avg_think_tags']:.3f}")
    print(f"Average Answer Tags per Sample: {evaluation_result['avg_answer_tags']:.3f}")
    
    print("\n=== Error Pattern Analysis ===")
    print(f"Format Correct Samples: {error_analysis['format_correct_samples']}/{error_analysis['total_samples']}")
    print("Error Patterns:")
    for pattern, count in error_analysis['error_patterns'].items():
        if count > 0:
            print(f"  {pattern}: {count}")
    
    print("\n=== Sample Error Examples ===")
    for i, example in enumerate(error_analysis['error_examples'][:3]):
        print(f"Example {i+1}:")
        print(f"  Question: {example['question']}")
        print(f"  Has Think: {example['has_think']}, Has Answer: {example['has_answer']}")
        print(f"  Think Count: {example['think_count']}, Answer Count: {example['answer_count']}")
        if example['error_message']:
            print(f"  Error: {example['error_message']}")
        print()

if __name__ == "__main__":
    main()

