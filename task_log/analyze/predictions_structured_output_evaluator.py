#!/usr/bin/env python3
"""
来自任务：`structured_output_eval` (更新版)
Custom metric implementation for evaluating structured output from predictions data.
Handles reasoning field and multiple think tags as specified in the task.
"""

import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

class PredictionsStructuredOutputEvaluator:
    """
    Custom metric evaluator for structured output from predictions data.
    
    Evaluates model outputs based on:
    1. Presence of <think>...</think> tags in text content
    2. Presence of reasoning field in model_output
    3. Presence of <answer>...</answer> tags
    4. Correct JSON format in answer content
    5. Overall format correctness according to expect_output_format.txt
    """
    
    def __init__(self):
        self.metric_name = "predictions_structured_output_format"
    
    def extract_text_content(self, prediction_data: Dict[str, Any]) -> str:
        """
        Extract text content from prediction data structure.
        
        Args:
            prediction_data: The prediction data dictionary
            
        Returns:
            Extracted text content string
        """
        try:
            model_output = prediction_data.get('model_output', {})
            choices = model_output.get('choices', [])
            
            if not choices:
                return ""
            
            message = choices[0].get('message', {})
            content = message.get('content', [])
            
            # Extract text content from content array
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            
            return ''.join(text_parts)
        except Exception as e:
            print(f"Error extracting text content: {e}")
            return ""
    
    def has_reasoning_field(self, prediction_data: Dict[str, Any]) -> bool:
        """
        Check if prediction data has reasoning field.
        
        Args:
            prediction_data: The prediction data dictionary
            
        Returns:
            True if reasoning field exists, False otherwise
        """
        try:
            model_output = prediction_data.get('model_output', {})
            choices = model_output.get('choices', [])
            
            if not choices:
                return False
            
            message = choices[0].get('message', {})
            content = message.get('content', [])
            
            # Check for reasoning field in content array
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'reasoning':
                    reasoning = item.get('reasoning', '')
                    if reasoning and reasoning.strip():
                        return True
            
            return False
        except Exception as e:
            print(f"Error checking reasoning field: {e}")
            return False
    
    def evaluate_single_output(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single model prediction for structured output format.
        
        Args:
            prediction_data: The prediction data dictionary
            
        Returns:
            Dictionary containing evaluation flags and scores
        """
        result = {
            'has_text_think_tag': False,
            'has_reasoning_field': False,
            'has_answer_tag': False,
            'has_valid_json': False,
            'format_correct': False,
            'think_content': '',
            'answer_content': '',
            'json_content': None,
            'error_message': None,
            'text_think_tag_count': 0,
            'answer_tag_count': 0,
            'total_think_sources': 0,
            'malformed_structure': False
        }
        
        try:
            # Extract text content
            text_content = self.extract_text_content(prediction_data)
            
            # Check for reasoning field
            result['has_reasoning_field'] = self.has_reasoning_field(prediction_data)
            
            # Count think tags in text content
            text_think_matches = re.findall(r'<think>(.*?)</think>', text_content, re.DOTALL)
            result['text_think_tag_count'] = len(text_think_matches)
            if text_think_matches:
                result['has_text_think_tag'] = True
                result['think_content'] = text_think_matches[0].strip()
            
            # Count total think sources (text tags + reasoning field)
            result['total_think_sources'] = result['text_think_tag_count'] + (1 if result['has_reasoning_field'] else 0)
            
            # Count answer tags
            answer_matches = re.findall(r'<answer>(.*?)</answer>', text_content, re.DOTALL)
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
            
            # Check for malformed structure (multiple answer tags, etc.)
            if result['answer_tag_count'] > 1:
                result['malformed_structure'] = True
            
            # Check overall format correctness according to expect_output_format.txt
            # Requirements:
            # 1. Has exactly one think source (either text think tag OR reasoning field, not both)
            # 2. Has exactly one answer tag
            # 3. Has valid JSON format
            # 4. No malformed structure
            if (result['total_think_sources'] == 1 and 
                result['answer_tag_count'] == 1 and 
                result['has_valid_json'] and 
                not result['malformed_structure']):
                result['format_correct'] = True
                
        except Exception as e:
            result['error_message'] = f"Evaluation error: {str(e)}"
        
        return result
    
    def evaluate_batch(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate a batch of predictions.
        
        Args:
            predictions: List of prediction data dictionaries
            
        Returns:
            Dictionary containing batch evaluation results
        """
        results = []
        for i, prediction in enumerate(predictions):
            result = self.evaluate_single_output(prediction)
            result['index'] = i
            results.append(result)
        
        # Calculate aggregate metrics
        total_samples = len(results)
        has_text_think_count = sum(1 for r in results if r['has_text_think_tag'])
        has_reasoning_count = sum(1 for r in results if r['has_reasoning_field'])
        has_answer_count = sum(1 for r in results if r['has_answer_tag'])
        has_valid_json_count = sum(1 for r in results if r['has_valid_json'])
        format_correct_count = sum(1 for r in results if r['format_correct'])
        malformed_structure_count = sum(1 for r in results if r['malformed_structure'])
        
        # Calculate average tag counts
        avg_text_think_tags = sum(r['text_think_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        avg_answer_tags = sum(r['answer_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        avg_total_think_sources = sum(r['total_think_sources'] for r in results) / total_samples if total_samples > 0 else 0
        
        return {
            'total_samples': total_samples,
            'has_text_think_rate': has_text_think_count / total_samples if total_samples > 0 else 0,
            'has_reasoning_rate': has_reasoning_count / total_samples if total_samples > 0 else 0,
            'has_answer_rate': has_answer_count / total_samples if total_samples > 0 else 0,
            'has_valid_json_rate': has_valid_json_count / total_samples if total_samples > 0 else 0,
            'format_correct_rate': format_correct_count / total_samples if total_samples > 0 else 0,
            'malformed_structure_rate': malformed_structure_count / total_samples if total_samples > 0 else 0,
            'avg_text_think_tags': avg_text_think_tags,
            'avg_answer_tags': avg_answer_tags,
            'avg_total_think_sources': avg_total_think_sources,
            'individual_results': results
        }

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object for sorting"""
    return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def extract_step_from_model_name(model_name):
    """Extract step number from model name like 'model-step50'"""
    match = re.search(r'model-step(\d+)', model_name)
    return int(match.group(1)) if match else None

def load_predictions_data(predictions_file_path: str) -> List[Dict[str, Any]]:
    """
    Load predictions data from JSONL file.
    
    Args:
        predictions_file_path: Path to the predictions JSONL file
        
    Returns:
        List of prediction records
    """
    predictions = []
    try:
        with open(predictions_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    prediction = json.loads(line.strip())
                    predictions.append(prediction)
    except Exception as e:
        print(f"Error loading predictions file {predictions_file_path}: {e}")
    
    return predictions

def analyze_predictions_directory(eval_dir: str) -> List[Dict[str, Any]]:
    """
    Analyze the entire evaluation directory structure for predictions files.
    
    Args:
        eval_dir: Path to the evaluation directory
        
    Returns:
        List of evaluation results for each checkpoint
    """
    eval_path = Path(eval_dir)
    
    if not eval_path.exists():
        print(f"Directory {eval_dir} does not exist!")
        return []
    
    # Get all timestamp directories and sort them
    timestamp_dirs = []
    for item in eval_path.iterdir():
        if item.is_dir() and re.match(r'\d{8}_\d{6}', item.name):
            timestamp_dirs.append(item.name)
    
    # Sort by timestamp
    timestamp_dirs.sort(key=parse_timestamp)
    
    all_results = []
    evaluator = PredictionsStructuredOutputEvaluator()
    
    for timestamp in timestamp_dirs:
        timestamp_path = eval_path / timestamp
        predictions_path = timestamp_path / 'predictions'
        
        if not predictions_path.exists():
            print(f"Predictions directory not found in {timestamp}")
            continue
        
        # Find model-step directories
        for model_dir in predictions_path.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith('model-step'):
                step = extract_step_from_model_name(model_dir.name)
                
                # Look for JSONL files in the model directory
                for jsonl_file in model_dir.glob('*.jsonl'):
                    print(f"Processing {jsonl_file}")
                    
                    # Load predictions data
                    predictions = load_predictions_data(str(jsonl_file))
                    if not predictions:
                        continue
                    
                    # Evaluate using custom metric
                    evaluation_result = evaluator.evaluate_batch(predictions)
                    
                    # Add metadata
                    evaluation_result['timestamp'] = timestamp
                    evaluation_result['step'] = step
                    evaluation_result['model_name'] = model_dir.name
                    evaluation_result['file_path'] = str(jsonl_file)
                    
                    all_results.append(evaluation_result)
    
    return all_results

def create_visualization(results: List[Dict[str, Any]], output_dir: str):
    """
    Create visualizations for predictions structured output evaluation results.
    
    Args:
        results: List of evaluation results
        output_dir: Directory to save visualizations
    """
    if not results:
        print("No results to visualize!")
        return
    
    # Convert to DataFrame
    df_data = []
    for result in results:
        df_data.append({
            'timestamp': result['timestamp'],
            'step': result['step'],
            'model_name': result['model_name'],
            'has_text_think_rate': result['has_text_think_rate'],
            'has_reasoning_rate': result['has_reasoning_rate'],
            'has_answer_rate': result['has_answer_rate'],
            'has_valid_json_rate': result['has_valid_json_rate'],
            'format_correct_rate': result['format_correct_rate'],
            'malformed_structure_rate': result['malformed_structure_rate'],
            'avg_text_think_tags': result['avg_text_think_tags'],
            'avg_answer_tags': result['avg_answer_tags'],
            'avg_total_think_sources': result['avg_total_think_sources'],
            'total_samples': result['total_samples']
        })
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('step')
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create comprehensive visualization
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Predictions Structured Output Format Evaluation Over Training Steps', fontsize=16, fontweight='bold')
    
    # Plot 1: Text Think tag presence rate
    ax1 = axes[0, 0]
    ax1.plot(df['step'], df['has_text_think_rate'], marker='o', linewidth=2, label='Text Think Tag Rate', color='blue')
    ax1.set_title('Text Think Tag Presence Rate', fontweight='bold')
    ax1.set_xlabel('Training Step')
    ax1.set_ylabel('Rate')
    ax1.set_ylim(0, 1)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Reasoning field presence rate
    ax2 = axes[0, 1]
    ax2.plot(df['step'], df['has_reasoning_rate'], marker='s', linewidth=2, label='Reasoning Field Rate', color='green')
    ax2.set_title('Reasoning Field Presence Rate', fontweight='bold')
    ax2.set_xlabel('Training Step')
    ax2.set_ylabel('Rate')
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Answer tag presence rate
    ax3 = axes[0, 2]
    ax3.plot(df['step'], df['has_answer_rate'], marker='^', linewidth=2, label='Answer Tag Rate', color='red')
    ax3.set_title('Answer Tag Presence Rate', fontweight='bold')
    ax3.set_xlabel('Training Step')
    ax3.set_ylabel('Rate')
    ax3.set_ylim(0, 1)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Plot 4: Valid JSON rate
    ax4 = axes[1, 0]
    ax4.plot(df['step'], df['has_valid_json_rate'], marker='v', linewidth=2, label='Valid JSON Rate', color='orange')
    ax4.set_title('Valid JSON Format Rate', fontweight='bold')
    ax4.set_xlabel('Training Step')
    ax4.set_ylabel('Rate')
    ax4.set_ylim(0, 1)
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Plot 5: Malformed structure rate
    ax5 = axes[1, 1]
    ax5.plot(df['step'], df['malformed_structure_rate'], marker='d', linewidth=2, label='Malformed Structure Rate', color='brown')
    ax5.set_title('Malformed Structure Rate', fontweight='bold')
    ax5.set_xlabel('Training Step')
    ax5.set_ylabel('Rate')
    ax5.set_ylim(0, 1)
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    
    # Plot 6: Overall format correctness
    ax6 = axes[1, 2]
    ax6.plot(df['step'], df['format_correct_rate'], marker='*', linewidth=2, label='Format Correct Rate', color='purple')
    ax6.set_title('Overall Format Correctness Rate', fontweight='bold')
    ax6.set_xlabel('Training Step')
    ax6.set_ylabel('Rate')
    ax6.set_ylim(0, 1)
    ax6.grid(True, alpha=0.3)
    ax6.legend()
    
    plt.tight_layout()
    
    # Save the plot
    plot_path = Path(output_dir) / 'predictions_structured_output_evaluation.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    # Create comprehensive single plot
    plt.figure(figsize=(16, 10))
    
    # Plot all metrics in one figure
    plt.plot(df['step'], df['has_text_think_rate'], marker='o', linewidth=2.5, label='Text Think Tag Rate', alpha=0.9)
    plt.plot(df['step'], df['has_reasoning_rate'], marker='s', linewidth=2.5, label='Reasoning Field Rate', alpha=0.9)
    plt.plot(df['step'], df['has_answer_rate'], marker='^', linewidth=2.5, label='Answer Tag Rate', alpha=0.9)
    plt.plot(df['step'], df['has_valid_json_rate'], marker='v', linewidth=2.5, label='Valid JSON Rate', alpha=0.9)
    plt.plot(df['step'], df['malformed_structure_rate'], marker='d', linewidth=2.5, label='Malformed Structure Rate', alpha=0.9)
    plt.plot(df['step'], df['format_correct_rate'], marker='*', linewidth=2.5, label='Format Correct Rate', alpha=0.9)
    
    plt.title('Predictions Structured Output Format Evaluation - All Metrics', fontsize=16, fontweight='bold')
    plt.xlabel('Training Step', fontsize=12)
    plt.ylabel('Rate', fontsize=12)
    plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1)
    plt.tight_layout()
    
    comprehensive_plot_path = Path(output_dir) / 'predictions_structured_output_comprehensive.png'
    plt.savefig(comprehensive_plot_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive plot saved to: {comprehensive_plot_path}")
    
    return df

def main():
    """Main function to run predictions structured output evaluation"""
    # Define paths
    # eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_2ep_16bs_2accum/v0-20250914-133424/eval"
    # eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample800/v0-20250916-021825/eval"
    eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample160/v0-20250916-025942/eval"
    # output_dir = "/root/data1/projects/RL/DeepRetrieval/task_log/analyze"
    # output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample800/v0-20250916-021825/eval_analyze"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample160/v0-20250916-025942/eval_analyze"
    
    print("Starting predictions structured output evaluation analysis...")
    print(f"Target directory: {eval_dir}")
    
    # Analyze the directory
    results = analyze_predictions_directory(eval_dir)
    
    if not results:
        print("No evaluation results found!")
        return
    
    print(f"Found {len(results)} evaluation checkpoints")
    
    # Create visualizations
    df = create_visualization(results, output_dir)
    
    # Save raw data to CSV
    if df is not None:
        csv_path = Path(output_dir) / 'predictions_structured_output_evaluation_data.csv'
        df.to_csv(csv_path, index=False)
        print(f"Raw data saved to: {csv_path}")
        
        # Print summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Number of checkpoints: {len(df)}")
        print(f"Step range: {df['step'].min()} - {df['step'].max()}")
        print(f"Timestamp range: {df['timestamp'].min()} - {df['timestamp'].max()}")
        
        print("\n=== Format Evaluation Summary ===")
        print(f"Average Text Think Tag Rate: {df['has_text_think_rate'].mean():.3f}")
        print(f"Average Reasoning Field Rate: {df['has_reasoning_rate'].mean():.3f}")
        print(f"Average Answer Tag Rate: {df['has_answer_rate'].mean():.3f}")
        print(f"Average Valid JSON Rate: {df['has_valid_json_rate'].mean():.3f}")
        print(f"Average Malformed Structure Rate: {df['malformed_structure_rate'].mean():.3f}")
        print(f"Average Format Correct Rate: {df['format_correct_rate'].mean():.3f}")
        print(f"Average Text Think Tags per Sample: {df['avg_text_think_tags'].mean():.3f}")
        print(f"Average Answer Tags per Sample: {df['avg_answer_tags'].mean():.3f}")
        print(f"Average Total Think Sources per Sample: {df['avg_total_think_sources'].mean():.3f}")
        
        print("\n=== Best Performance Checkpoint ===")
        best_idx = df['format_correct_rate'].idxmax()
        best_checkpoint = df.iloc[best_idx]
        print(f"Step: {best_checkpoint['step']}")
        print(f"Format Correct Rate: {best_checkpoint['format_correct_rate']:.3f}")
        print(f"Text Think Tag Rate: {best_checkpoint['has_text_think_rate']:.3f}")
        print(f"Reasoning Field Rate: {best_checkpoint['has_reasoning_rate']:.3f}")
        print(f"Answer Tag Rate: {best_checkpoint['has_answer_rate']:.3f}")
        print(f"Valid JSON Rate: {best_checkpoint['has_valid_json_rate']:.3f}")
        print(f"Malformed Structure Rate: {best_checkpoint['malformed_structure_rate']:.3f}")
        
        print("\n=== Worst Performance Checkpoint ===")
        worst_idx = df['format_correct_rate'].idxmin()
        worst_checkpoint = df.iloc[worst_idx]
        print(f"Step: {worst_checkpoint['step']}")
        print(f"Format Correct Rate: {worst_checkpoint['format_correct_rate']:.3f}")
        print(f"Malformed Structure Rate: {worst_checkpoint['malformed_structure_rate']:.3f}")
        print(f"Average Answer Tags: {worst_checkpoint['avg_answer_tags']:.3f}")

if __name__ == "__main__":
    main()
