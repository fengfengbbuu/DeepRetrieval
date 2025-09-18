#!/usr/bin/env python3
"""
来自任务：`zero-shot_evaluator`
Enhanced evaluator for zero-shot model outputs with CoT and non-CoT support.
Based on REF_FILE with parameter support and dual evaluation metrics.
"""

import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Add the project root to path to import spider module
sys.path.append('/root/data1/projects/RL/DeepRetrieval')
sys.path.append('/root/data1/projects/RL/DeepRetrieval/code')
from verl.utils.reward_score.spider import calculate_answer_score

class ZeroShotStructuredOutputEvaluator:
    """
    Enhanced evaluator for zero-shot model outputs with CoT and non-CoT support.
    
    Features:
    1. Parameter support for flexible data processing
    2. Dual evaluation metrics (CoT and non-CoT)
    3. Modular design for easy extension
    4. Comprehensive error analysis
    """
    
    def __init__(self, 
                 response_key: str = 'api_result',
                 ground_truth_key: str = 'ground_truth',
                 db_path_key: str = 'db_path',
                 is_cot: bool = True):
        """
        Initialize the evaluator with configurable parameters.
        
        Args:
            response_key: Key for model response in data
            ground_truth_key: Key for ground truth in data
            db_path_key: Key for database path in data
            is_cot: Whether to use CoT evaluation metrics
        """
        self.response_key = response_key
        self.ground_truth_key = ground_truth_key
        self.db_path_key = db_path_key
        self.is_cot = is_cot
        self.metric_name = f"zero_shot_structured_output_format_{'cot' if is_cot else 'non_cot'}"
    
    def get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """
        Get nested field value, supporting key1.key2 format.
        
        Args:
            data: The data dictionary
            key_path: Dot-separated key path (e.g., 'key1.key2')
            
        Returns:
            The value at the nested key path, or None if not found
        """
        try:
            keys = key_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except (KeyError, TypeError, AttributeError):
            return None
    
    def extract_response_content(self, record: Dict[str, Any]) -> str:
        """
        Extract content from response field based on response_key.
        
        Args:
            record: The inference result record
            
        Returns:
            Extracted content string
        """
        try:
            response_data = self.get_nested_value(record, self.response_key)
            
            if isinstance(response_data, str):
                return response_data
            elif isinstance(response_data, dict):
                # Handle api_result structure
                if not response_data.get('success', False):
                    return ""
                
                response = response_data.get('response', {})
                choices = response.get('choices', [])
                
                if not choices:
                    return ""
                
                message = choices[0].get('message', {})
                content = message.get('content', '')
                
                return content
            else:
                return ""
        except Exception as e:
            print(f"Error extracting response content: {e}")
            return ""
    
    def extract_ground_truth(self, record: Dict[str, Any]) -> str:
        """
        Extract ground truth from record.
        
        Args:
            record: The inference result record
            
        Returns:
            Ground truth string
        """
        try:
            # Try to get from original_data first
            original_data = record.get('original_data', {})
            ground_truth = self.get_nested_value(original_data, self.ground_truth_key)
            
            if ground_truth:
                return ground_truth
            
            # Fallback to direct access
            ground_truth = self.get_nested_value(record, self.ground_truth_key)
            return ground_truth or ""
        except Exception as e:
            print(f"Error extracting ground truth: {e}")
            return ""
    
    def extract_db_path(self, record: Dict[str, Any]) -> str:
        """
        Extract database path from record.
        
        Args:
            record: The inference result record
            
        Returns:
            Database path string
        """
        try:
            # Try to get from original_data first
            original_data = record.get('original_data', {})
            db_path = self.get_nested_value(original_data, self.db_path_key)
            
            if db_path:
                return db_path
            
            # Fallback to direct access
            db_path = self.get_nested_value(record, self.db_path_key)
            return db_path or ""
        except Exception as e:
            print(f"Error extracting db path: {e}")
            return ""
    
    def evaluate_cot_output(self, content: str) -> Dict[str, Any]:
        """
        Evaluate CoT (Chain of Thought) output format.
        
        Args:
            content: The model's output content string
            
        Returns:
            Dictionary containing CoT evaluation flags and scores
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
            
            # Check overall format correctness for CoT
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
            result['error_message'] = f"CoT evaluation error: {str(e)}"
        
        return result
    
    def evaluate_non_cot_output(self, content: str) -> Dict[str, Any]:
        """
        Evaluate non-CoT output format (JSON in <answer> tags, no <think> tags).
        
        Args:
            content: The model's output content string
            
        Returns:
            Dictionary containing non-CoT evaluation flags and scores
        """
        result = {
            'has_answer_tag': False,
            'has_valid_json': False,
            'format_correct': False,
            'answer_content': '',
            'json_content': None,
            'error_message': None,
            'answer_tag_count': 0,
            'has_think_tag': False,
            'think_tag_count': 0,
            'malformed_structure': False
        }
        
        try:
            # Check for think tags (should not exist in non-CoT mode)
            think_matches = re.findall(r'<think>(.*?)</think>', content, re.DOTALL)
            result['think_tag_count'] = len(think_matches)
            if think_matches:
                result['has_think_tag'] = True
                # Having think tags in non-CoT mode is considered malformed
                result['malformed_structure'] = True
            
            # Look for answer tags
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
            
            # Check for malformed structure (multiple answer tags)
            if result['answer_tag_count'] > 1:
                result['malformed_structure'] = True
            
            # Check overall format correctness for non-CoT
            # Requirements:
            # 1. Has exactly one answer tag
            # 2. Has valid JSON content
            # 3. No think tags (this is non-CoT mode)
            # 4. No malformed structure
            if (result['answer_tag_count'] == 1 and 
                result['has_valid_json'] and 
                not result['has_think_tag'] and
                not result['malformed_structure']):
                result['format_correct'] = True
                
        except Exception as e:
            result['error_message'] = f"Non-CoT evaluation error: {str(e)}"
        
        return result
    
    def extract_sql_from_content(self, content: str) -> Optional[str]:
        """
        Extract SQL from model output content based on is_cot setting.
        
        Args:
            content: The model's output content string
            
        Returns:
            Extracted SQL string or None if not found
        """
        try:
            # Both CoT and non-CoT modes now use the same format: JSON in <answer> tags
            # The difference is that CoT mode should have <think> tags, non-CoT should not
            answer_matches = re.findall(r'<answer>(.*?)</answer>', content, re.DOTALL)
            if answer_matches:
                answer_content = answer_matches[0].strip()
                try:
                    json_content = json.loads(answer_content)
                    if isinstance(json_content, dict) and 'sql' in json_content:
                        return json_content['sql']
                except json.JSONDecodeError:
                    pass
            
            return None
        except Exception as e:
            print(f"Error extracting SQL from content: {e}")
            return None
    
    def evaluate_execution_accuracy(self, pred_sql: str, gold_sql: str, db_path: str) -> Dict[str, Any]:
        """
        Evaluate SQL execution accuracy using spider module.
        
        Args:
            pred_sql: Predicted SQL query
            gold_sql: Ground truth SQL query
            db_path: Database path relative to {project_root}/code
            
        Returns:
            Dictionary containing execution accuracy results
        """
        result = {
            'execution_accuracy': 0,
            'execution_error': None,
            'pred_results': None,
            'gold_results': None
        }
        
        try:
            if pred_sql and gold_sql and db_path:
                # Convert relative path to absolute path
                # db_path is relative to {project_root}/code
                project_root = '/root/data1/projects/RL/DeepRetrieval'
                code_dir = os.path.join(project_root, 'code')
                absolute_db_path = os.path.join(code_dir, db_path)
                
                # Check if database file exists
                if not os.path.exists(absolute_db_path):
                    result['execution_error'] = f"Database file not found: {absolute_db_path}"
                    return result
                
                accuracy_score = calculate_answer_score(pred_sql, gold_sql, absolute_db_path, do_print=False)
                result['execution_accuracy'] = accuracy_score
            else:
                result['execution_error'] = "Missing SQL or database path"
        except Exception as e:
            result['execution_error'] = f"Execution error: {str(e)}"
            result['execution_accuracy'] = 0
        
        return result
    
    def evaluate_single_output(self, content: str, ground_truth: str = "", db_path: str = "") -> Dict[str, Any]:
        """
        Evaluate a single model output based on is_cot setting.
        
        Args:
            content: The model's output content string
            ground_truth: Ground truth SQL for execution accuracy
            db_path: Database path for execution accuracy
            
        Returns:
            Dictionary containing evaluation flags and scores
        """
        # Get basic format evaluation
        if self.is_cot:
            result = self.evaluate_cot_output(content)
        else:
            result = self.evaluate_non_cot_output(content)
        
        # Add execution accuracy evaluation
        pred_sql = self.extract_sql_from_content(content)
        execution_result = self.evaluate_execution_accuracy(pred_sql, ground_truth, db_path)
        
        # Merge execution results
        result.update(execution_result)
        result['extracted_sql'] = pred_sql
        
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
            content = self.extract_response_content(record)
            ground_truth = self.extract_ground_truth(record)
            db_path = self.extract_db_path(record)
            
            result = self.evaluate_single_output(content, ground_truth, db_path)
            result['index'] = i
            result['original_question'] = record.get('original_data', {}).get('question', '')
            result['db_id'] = record.get('original_data', {}).get('db_id', '')
            result['data_source'] = record.get('original_data', {}).get('data_source', '')
            result['ground_truth'] = ground_truth
            result['db_path'] = db_path
            result['success'] = record.get('api_result', {}).get('success', False)
            results.append(result)
        
        # Calculate aggregate metrics
        total_samples = len(results)
        success_count = sum(1 for r in results if r['success'])
        
        # Common metrics for both modes
        execution_accuracy_sum = sum(r.get('execution_accuracy', 0) for r in results)
        execution_accuracy_rate = execution_accuracy_sum / total_samples if total_samples > 0 else 0
        execution_error_count = sum(1 for r in results if r.get('execution_error') is not None)
        
        if self.is_cot:
            # CoT metrics
            has_think_count = sum(1 for r in results if r.get('has_think_tag', False))
            has_answer_count = sum(1 for r in results if r.get('has_answer_tag', False))
            has_valid_json_count = sum(1 for r in results if r.get('has_valid_json', False))
            format_correct_count = sum(1 for r in results if r.get('format_correct', False))
            malformed_structure_count = sum(1 for r in results if r.get('malformed_structure', False))
            
            # Calculate average tag counts
            avg_think_tags = sum(r.get('think_tag_count', 0) for r in results) / total_samples if total_samples > 0 else 0
            avg_answer_tags = sum(r.get('answer_tag_count', 0) for r in results) / total_samples if total_samples > 0 else 0
            
            return {
                'total_samples': total_samples,
                'success_rate': success_count / total_samples if total_samples > 0 else 0,
                'has_think_rate': has_think_count / total_samples if total_samples > 0 else 0,
                'has_answer_rate': has_answer_count / total_samples if total_samples > 0 else 0,
                'has_valid_json_rate': has_valid_json_count / total_samples if total_samples > 0 else 0,
                'format_correct_rate': format_correct_count / total_samples if total_samples > 0 else 0,
                'malformed_structure_rate': malformed_structure_count / total_samples if total_samples > 0 else 0,
                'execution_accuracy_rate': execution_accuracy_rate,
                'execution_error_rate': execution_error_count / total_samples if total_samples > 0 else 0,
                'avg_think_tags': avg_think_tags,
                'avg_answer_tags': avg_answer_tags,
                'individual_results': results,
                'evaluation_mode': 'cot'
            }
        else:
            # Non-CoT metrics (now uses same format as CoT but without think tags)
            has_answer_count = sum(1 for r in results if r.get('has_answer_tag', False))
            has_valid_json_count = sum(1 for r in results if r.get('has_valid_json', False))
            has_think_count = sum(1 for r in results if r.get('has_think_tag', False))  # Should be 0 for proper non-CoT
            format_correct_count = sum(1 for r in results if r.get('format_correct', False))
            malformed_structure_count = sum(1 for r in results if r.get('malformed_structure', False))
            
            # Calculate average tag counts
            avg_answer_tags = sum(r.get('answer_tag_count', 0) for r in results) / total_samples if total_samples > 0 else 0
            avg_think_tags = sum(r.get('think_tag_count', 0) for r in results) / total_samples if total_samples > 0 else 0
            
            return {
                'total_samples': total_samples,
                'success_rate': success_count / total_samples if total_samples > 0 else 0,
                'has_answer_rate': has_answer_count / total_samples if total_samples > 0 else 0,
                'has_valid_json_rate': has_valid_json_count / total_samples if total_samples > 0 else 0,
                'has_think_rate': has_think_count / total_samples if total_samples > 0 else 0,  # Should be 0
                'format_correct_rate': format_correct_count / total_samples if total_samples > 0 else 0,
                'malformed_structure_rate': malformed_structure_count / total_samples if total_samples > 0 else 0,
                'execution_accuracy_rate': execution_accuracy_rate,
                'execution_error_rate': execution_error_count / total_samples if total_samples > 0 else 0,
                'avg_answer_tags': avg_answer_tags,
                'avg_think_tags': avg_think_tags,  # Should be 0
                'individual_results': results,
                'evaluation_mode': 'non_cot'
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
    Create visualizations for zero-shot evaluation results.
    
    Args:
        evaluation_result: The evaluation result dictionary
        output_dir: Directory to save visualizations
    """
    is_cot = evaluation_result.get('evaluation_mode') == 'cot'
    
    if is_cot:
        # CoT visualization
        summary_data = {
            'Metric': [
                'Success Rate',
                'Think Tag Rate', 
                'Answer Tag Rate',
                'Valid JSON Rate',
                'Format Correct Rate',
                'Execution Accuracy Rate',
                'Malformed Structure Rate'
            ],
            'Rate': [
                evaluation_result['success_rate'],
                evaluation_result['has_think_rate'],
                evaluation_result['has_answer_rate'],
                evaluation_result['has_valid_json_rate'],
                evaluation_result['format_correct_rate'],
                evaluation_result['execution_accuracy_rate'],
                evaluation_result['malformed_structure_rate']
            ]
        }
    else:
        # Non-CoT visualization (now uses same format but without think tags)
        summary_data = {
            'Metric': [
                'Success Rate',
                'Answer Tag Rate', 
                'Valid JSON Rate',
                'Think Tag Rate (Should be 0)',
                'Format Correct Rate',
                'Execution Accuracy Rate',
                'Malformed Structure Rate'
            ],
            'Rate': [
                evaluation_result['success_rate'],
                evaluation_result['has_answer_rate'],
                evaluation_result['has_valid_json_rate'],
                evaluation_result['has_think_rate'],
                evaluation_result['format_correct_rate'],
                evaluation_result['execution_accuracy_rate'],
                evaluation_result['malformed_structure_rate']
            ]
        }
    
    df_summary = pd.DataFrame(summary_data)
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = ['green', 'blue', 'orange', 'red', 'purple', 'cyan', 'brown']
    bars = ax.bar(df_summary['Metric'], df_summary['Rate'], 
                  color=colors[:len(df_summary)])
    
    # Customize the plot
    mode_title = 'CoT' if is_cot else 'Non-CoT'
    ax.set_title(f'Zero-Shot Model Structured Output Evaluation Results ({mode_title})', 
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
    mode_suffix = 'cot' if is_cot else 'non_cot'
    plot_path = Path(output_dir) / f'zero_shot_evaluation_results_{mode_suffix}.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
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
    is_cot = evaluation_result.get('evaluation_mode') == 'cot'
    
    error_analysis = {
        'total_samples': len(individual_results),
        'format_correct_samples': sum(1 for r in individual_results if r.get('format_correct', False)),
        'error_patterns': {},
        'error_examples': []
    }
    
    if is_cot:
        error_analysis['error_patterns'] = {
            'missing_think_tag': 0,
            'missing_answer_tag': 0,
            'invalid_json': 0,
            'multiple_think_tags': 0,
            'multiple_answer_tags': 0,
            'malformed_structure': 0,
            'execution_error': 0,
            'api_failure': 0
        }
    else:
        error_analysis['error_patterns'] = {
            'missing_answer_tag': 0,
            'invalid_json': 0,
            'has_think_tag': 0,  # This is an error in non-CoT mode
            'multiple_answer_tags': 0,
            'malformed_structure': 0,
            'execution_error': 0,
            'api_failure': 0
        }
    
    for result in individual_results:
        if not result.get('success', False):
            error_analysis['error_patterns']['api_failure'] += 1
            continue
        
        # Check for execution errors
        if result.get('execution_error') is not None:
            error_analysis['error_patterns']['execution_error'] += 1
            
        if not result.get('format_correct', False):
            if is_cot:
                if not result.get('has_think_tag', False):
                    error_analysis['error_patterns']['missing_think_tag'] += 1
                if not result.get('has_answer_tag', False):
                    error_analysis['error_patterns']['missing_answer_tag'] += 1
                if not result.get('has_valid_json', False):
                    error_analysis['error_patterns']['invalid_json'] += 1
                if result.get('think_tag_count', 0) > 1:
                    error_analysis['error_patterns']['multiple_think_tags'] += 1
                if result.get('answer_tag_count', 0) > 1:
                    error_analysis['error_patterns']['multiple_answer_tags'] += 1
                if result.get('malformed_structure', False):
                    error_analysis['error_patterns']['malformed_structure'] += 1
            else:
                if not result.get('has_answer_tag', False):
                    error_analysis['error_patterns']['missing_answer_tag'] += 1
                if not result.get('has_valid_json', False):
                    error_analysis['error_patterns']['invalid_json'] += 1
                if result.get('has_think_tag', False):  # Think tags are not allowed in non-CoT
                    error_analysis['error_patterns']['has_think_tag'] += 1
                if result.get('answer_tag_count', 0) > 1:
                    error_analysis['error_patterns']['multiple_answer_tags'] += 1
                if result.get('malformed_structure', False):
                    error_analysis['error_patterns']['malformed_structure'] += 1
            
            # Collect error examples (first 5 of each type)
            if len(error_analysis['error_examples']) < 5:
                error_example = {
                    'index': result['index'],
                    'question': result['original_question'][:100] + '...' if len(result['original_question']) > 100 else result['original_question'],
                    'error_message': result.get('error_message', ''),
                    'execution_accuracy': result.get('execution_accuracy', 0),
                    'execution_error': result.get('execution_error', '')
                }
                
                if is_cot:
                    error_example.update({
                        'has_think': result.get('has_think_tag', False),
                        'has_answer': result.get('has_answer_tag', False),
                        'has_valid_json': result.get('has_valid_json', False),
                        'think_count': result.get('think_tag_count', 0),
                        'answer_count': result.get('answer_tag_count', 0)
                    })
                else:
                    error_example.update({
                        'has_answer': result.get('has_answer_tag', False),
                        'has_valid_json': result.get('has_valid_json', False),
                        'has_think': result.get('has_think_tag', False),  # Should be False
                        'answer_count': result.get('answer_tag_count', 0),
                        'think_count': result.get('think_tag_count', 0)  # Should be 0
                    })
                
                error_analysis['error_examples'].append(error_example)
    
    return error_analysis

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zero-Shot Structured Output Evaluator")
    
    # Required arguments
    parser.add_argument("--file_path", type=str, required=True,
                       help="Path to the data file to process")
    
    # Optional arguments with defaults
    parser.add_argument("--response_key", type=str, default="api_result",
                       help="Model response key name (default: api_result)")
    parser.add_argument("--ground_truth_key", type=str, default="ground_truth",
                       help="Ground truth key name (default: ground_truth)")
    parser.add_argument("--db_path_key", type=str, default="db_path",
                       help="Database path key name (default: db_path)")
    # parser.add_argument("--is_cot", type=bool, default=True,
    #                    help="Whether model output contains CoT information (default: True)")
    parser.add_argument("--is_cot", action="store_true",
                       help="Whether model output contains CoT information (default: True)")
    
    return parser.parse_args()

def main():
    """Main function to run zero-shot structured output evaluation"""
    args = parse_args()
    
    # Determine output directory
    input_path = Path(args.file_path)
    output_dir = input_path.parent / 'analyze'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Starting zero-shot structured output evaluation analysis...")
    print(f"Target file: {args.file_path}")
    print(f"Output directory: {output_dir}")
    print(f"Response key: {args.response_key}")
    print(f"Ground truth key: {args.ground_truth_key}")
    print(f"DB path key: {args.db_path_key}")
    print(f"Is CoT: {args.is_cot}")
    
    # Load inference data
    records = load_inference_data(args.file_path)
    
    if not records:
        print("No inference data found!")
        return
    
    print(f"Loaded {len(records)} inference records")
    
    # Create evaluator and evaluate
    evaluator = ZeroShotStructuredOutputEvaluator(
        response_key=args.response_key,
        ground_truth_key=args.ground_truth_key,
        db_path_key=args.db_path_key,
        is_cot=args.is_cot
    )
    evaluation_result = evaluator.evaluate_batch(records)
    
    # Create visualizations
    df_summary = create_visualization(evaluation_result, str(output_dir))
    
    # Analyze error patterns
    error_analysis = analyze_error_patterns(evaluation_result)
    
    # Save detailed results to CSV
    individual_results = evaluation_result['individual_results']
    df_detailed = pd.DataFrame(individual_results)
    mode_suffix = 'cot' if args.is_cot else 'non_cot'
    csv_path = output_dir / f'zero_shot_detailed_results_{mode_suffix}.csv'
    df_detailed.to_csv(csv_path, index=False)
    print(f"Detailed results saved to: {csv_path}")
    
    # Save summary results to CSV
    summary_csv_path = output_dir / f'zero_shot_summary_results_{mode_suffix}.csv'
    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Summary results saved to: {summary_csv_path}")
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"Total samples: {evaluation_result['total_samples']}")
    print(f"Success rate: {evaluation_result['success_rate']:.3f}")
    
    print(f"\n=== Format Evaluation Summary ({'CoT' if args.is_cot else 'Non-CoT'}) ===")
    if args.is_cot:
        print(f"Think Tag Rate: {evaluation_result['has_think_rate']:.3f}")
        print(f"Answer Tag Rate: {evaluation_result['has_answer_rate']:.3f}")
        print(f"Valid JSON Rate: {evaluation_result['has_valid_json_rate']:.3f}")
        print(f"Average Think Tags per Sample: {evaluation_result['avg_think_tags']:.3f}")
        print(f"Average Answer Tags per Sample: {evaluation_result['avg_answer_tags']:.3f}")
    else:
        print(f"Answer Tag Rate: {evaluation_result['has_answer_rate']:.3f}")
        print(f"Valid JSON Rate: {evaluation_result['has_valid_json_rate']:.3f}")
        print(f"Think Tag Rate (Should be 0): {evaluation_result['has_think_rate']:.3f}")
        print(f"Average Answer Tags per Sample: {evaluation_result['avg_answer_tags']:.3f}")
        print(f"Average Think Tags per Sample: {evaluation_result['avg_think_tags']:.3f}")
    
    print(f"Format Correct Rate: {evaluation_result['format_correct_rate']:.3f}")
    print(f"Execution Accuracy Rate: {evaluation_result['execution_accuracy_rate']:.3f}")
    print(f"Execution Error Rate: {evaluation_result['execution_error_rate']:.3f}")
    print(f"Malformed Structure Rate: {evaluation_result['malformed_structure_rate']:.3f}")
    
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
        if args.is_cot:
            print(f"  Has Think: {example['has_think']}, Has Answer: {example['has_answer']}")
            print(f"  Think Count: {example['think_count']}, Answer Count: {example['answer_count']}")
        else:
            print(f"  Has Answer: {example['has_answer']}, Has Valid JSON: {example['has_valid_json']}")
            print(f"  Has Think (Should be False): {example['has_think']}")
            print(f"  Answer Count: {example['answer_count']}, Think Count: {example['think_count']}")
        print(f"  Execution Accuracy: {example['execution_accuracy']}")
        if example['error_message']:
            print(f"  Format Error: {example['error_message']}")
        if example['execution_error']:
            print(f"  Execution Error: {example['execution_error']}")
        print()

if __name__ == "__main__":
    main()
