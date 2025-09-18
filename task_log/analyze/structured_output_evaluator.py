#!/usr/bin/env python3
"""
来自任务：`structured_output_eval`
Custom metric implementation for evaluating structured output from models.
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

class StructuredOutputEvaluator:
    """
    Custom metric evaluator for structured output from models.
    
    Evaluates model outputs based on:
    1. Presence of <think>...</think> tags
    2. Presence of <answer>...</answer> tags  
    3. Correct JSON format in answer content
    4. Overall format correctness
    """
    
    def __init__(self):
        self.metric_name = "structured_output_format"
    
    def evaluate_single_output(self, prediction: str) -> Dict[str, Any]:
        """
        Evaluate a single model prediction for structured output format.
        
        Args:
            prediction: The model's prediction string
            
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
            'think_before_answer': False,
            'malformed_structure': False
        }
        
        try:
            # Count think tags
            think_matches = re.findall(r'<think>(.*?)</think>', prediction, re.DOTALL)
            result['think_tag_count'] = len(think_matches)
            if think_matches:
                result['has_think_tag'] = True
                result['think_content'] = think_matches[0].strip()
            
            # Count answer tags
            answer_matches = re.findall(r'<answer>(.*?)</answer>', prediction, re.DOTALL)
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
            
            # Check if think appears before answer
            think_positions = [m.start() for m in re.finditer(r'<think>', prediction)]
            answer_positions = [m.start() for m in re.finditer(r'<answer>', prediction)]
            
            if think_positions and answer_positions:
                result['think_before_answer'] = min(think_positions) < min(answer_positions)
            
            # Check for malformed structure (multiple tags, wrong order, etc.)
            if result['think_tag_count'] > 1 or result['answer_tag_count'] > 1:
                result['malformed_structure'] = True
            
            # Check overall format correctness
            if (result['has_think_tag'] and result['has_answer_tag'] and 
                result['has_valid_json'] and result['think_before_answer'] and 
                not result['malformed_structure']):
                result['format_correct'] = True
                
        except Exception as e:
            result['error_message'] = f"Evaluation error: {str(e)}"
        
        return result
    
    def evaluate_batch(self, predictions: List[str]) -> Dict[str, Any]:
        """
        Evaluate a batch of predictions.
        
        Args:
            predictions: List of model prediction strings
            
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
        has_think_count = sum(1 for r in results if r['has_think_tag'])
        has_answer_count = sum(1 for r in results if r['has_answer_tag'])
        has_valid_json_count = sum(1 for r in results if r['has_valid_json'])
        format_correct_count = sum(1 for r in results if r['format_correct'])
        think_before_answer_count = sum(1 for r in results if r['think_before_answer'])
        malformed_structure_count = sum(1 for r in results if r['malformed_structure'])
        
        # Calculate average tag counts
        avg_think_tags = sum(r['think_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        avg_answer_tags = sum(r['answer_tag_count'] for r in results) / total_samples if total_samples > 0 else 0
        
        return {
            'total_samples': total_samples,
            'has_think_rate': has_think_count / total_samples if total_samples > 0 else 0,
            'has_answer_rate': has_answer_count / total_samples if total_samples > 0 else 0,
            'has_valid_json_rate': has_valid_json_count / total_samples if total_samples > 0 else 0,
            'format_correct_rate': format_correct_count / total_samples if total_samples > 0 else 0,
            'think_before_answer_rate': think_before_answer_count / total_samples if total_samples > 0 else 0,
            'malformed_structure_rate': malformed_structure_count / total_samples if total_samples > 0 else 0,
            'avg_think_tags': avg_think_tags,
            'avg_answer_tags': avg_answer_tags,
            'individual_results': results
        }

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object for sorting"""
    return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

def extract_step_from_model_name(model_name):
    """Extract step number from model name like 'model-step50'"""
    match = re.search(r'model-step(\d+)', model_name)
    return int(match.group(1)) if match else None

def load_review_data(review_file_path: str) -> List[Dict[str, Any]]:
    """
    Load review data from JSONL file.
    
    Args:
        review_file_path: Path to the review JSONL file
        
    Returns:
        List of review records
    """
    reviews = []
    try:
        with open(review_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    review = json.loads(line.strip())
                    reviews.append(review)
    except Exception as e:
        print(f"Error loading review file {review_file_path}: {e}")
    
    return reviews

def analyze_eval_directory(eval_dir: str) -> List[Dict[str, Any]]:
    """
    Analyze the entire evaluation directory structure for review files.
    
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
    evaluator = StructuredOutputEvaluator()
    
    for timestamp in timestamp_dirs:
        timestamp_path = eval_path / timestamp
        reviews_path = timestamp_path / 'reviews'
        
        if not reviews_path.exists():
            print(f"Reviews directory not found in {timestamp}")
            continue
        
        # Find model-step directories
        for model_dir in reviews_path.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith('model-step'):
                step = extract_step_from_model_name(model_dir.name)
                
                # Look for JSONL files in the model directory
                for jsonl_file in model_dir.glob('*.jsonl'):
                    print(f"Processing {jsonl_file}")
                    
                    # Load review data
                    reviews = load_review_data(str(jsonl_file))
                    if not reviews:
                        continue
                    
                    # Extract predictions from the correct field
                    predictions = []
                    for review in reviews:
                        # Try to get prediction from sample_score.score.extracted_prediction
                        prediction = ''
                        if 'sample_score' in review:
                            sample_score = review['sample_score']
                            if 'score' in sample_score and 'extracted_prediction' in sample_score['score']:
                                prediction = sample_score['score']['extracted_prediction']
                        predictions.append(prediction)
                    
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
    Create visualizations for structured output evaluation results.
    
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
            'has_think_rate': result['has_think_rate'],
            'has_answer_rate': result['has_answer_rate'],
            'has_valid_json_rate': result['has_valid_json_rate'],
            'format_correct_rate': result['format_correct_rate'],
            'think_before_answer_rate': result['think_before_answer_rate'],
            'malformed_structure_rate': result['malformed_structure_rate'],
            'avg_think_tags': result['avg_think_tags'],
            'avg_answer_tags': result['avg_answer_tags'],
            'total_samples': result['total_samples']
        })
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('step')
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create comprehensive visualization
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Structured Output Format Evaluation Over Training Steps', fontsize=16, fontweight='bold')
    
    # Plot 1: Think tag presence rate
    ax1 = axes[0, 0]
    ax1.plot(df['step'], df['has_think_rate'], marker='o', linewidth=2, label='Think Tag Rate', color='blue')
    ax1.set_title('Think Tag Presence Rate', fontweight='bold')
    ax1.set_xlabel('Training Step')
    ax1.set_ylabel('Rate')
    ax1.set_ylim(0, 1)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Answer tag presence rate
    ax2 = axes[0, 1]
    ax2.plot(df['step'], df['has_answer_rate'], marker='s', linewidth=2, label='Answer Tag Rate', color='green')
    ax2.set_title('Answer Tag Presence Rate', fontweight='bold')
    ax2.set_xlabel('Training Step')
    ax2.set_ylabel('Rate')
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Valid JSON rate
    ax3 = axes[0, 2]
    ax3.plot(df['step'], df['has_valid_json_rate'], marker='^', linewidth=2, label='Valid JSON Rate', color='red')
    ax3.set_title('Valid JSON Format Rate', fontweight='bold')
    ax3.set_xlabel('Training Step')
    ax3.set_ylabel('Rate')
    ax3.set_ylim(0, 1)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Plot 4: Think before answer rate
    ax4 = axes[1, 0]
    ax4.plot(df['step'], df['think_before_answer_rate'], marker='v', linewidth=2, label='Think Before Answer Rate', color='orange')
    ax4.set_title('Think Before Answer Rate', fontweight='bold')
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
    plot_path = Path(output_dir) / 'structured_output_evaluation.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    # Create comprehensive single plot
    plt.figure(figsize=(16, 10))
    
    # Plot all metrics in one figure
    plt.plot(df['step'], df['has_think_rate'], marker='o', linewidth=2.5, label='Think Tag Rate', alpha=0.9)
    plt.plot(df['step'], df['has_answer_rate'], marker='s', linewidth=2.5, label='Answer Tag Rate', alpha=0.9)
    plt.plot(df['step'], df['has_valid_json_rate'], marker='^', linewidth=2.5, label='Valid JSON Rate', alpha=0.9)
    plt.plot(df['step'], df['think_before_answer_rate'], marker='v', linewidth=2.5, label='Think Before Answer Rate', alpha=0.9)
    plt.plot(df['step'], df['malformed_structure_rate'], marker='d', linewidth=2.5, label='Malformed Structure Rate', alpha=0.9)
    plt.plot(df['step'], df['format_correct_rate'], marker='*', linewidth=2.5, label='Format Correct Rate', alpha=0.9)
    
    plt.title('Structured Output Format Evaluation - All Metrics', fontsize=16, fontweight='bold')
    plt.xlabel('Training Step', fontsize=12)
    plt.ylabel('Rate', fontsize=12)
    plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1)
    plt.tight_layout()
    
    comprehensive_plot_path = Path(output_dir) / 'structured_output_comprehensive.png'
    plt.savefig(comprehensive_plot_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive plot saved to: {comprehensive_plot_path}")
    
    return df

def main():
    """Main function to run structured output evaluation"""
    # Define paths
    # eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_2ep_16bs_2accum/v0-20250914-133424/eval"
    eval_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample800/v0-20250916-021825/eval"
    # output_dir = "/root/data1/projects/RL/DeepRetrieval/task_log/analyze"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/1A6000_1ep_16bs_2accum_sample800/v0-20250916-021825/eval_analyze"
    
    print("Starting structured output evaluation analysis...")
    print(f"Target directory: {eval_dir}")
    
    # Analyze the directory
    results = analyze_eval_directory(eval_dir)
    
    if not results:
        print("No evaluation results found!")
        return
    
    print(f"Found {len(results)} evaluation checkpoints")
    
    # Create visualizations
    df = create_visualization(results, output_dir)
    
    # Save raw data to CSV
    if df is not None:
        csv_path = Path(output_dir) / 'structured_output_evaluation_data.csv'
        df.to_csv(csv_path, index=False)
        print(f"Raw data saved to: {csv_path}")
        
        # Print summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Number of checkpoints: {len(df)}")
        print(f"Step range: {df['step'].min()} - {df['step'].max()}")
        print(f"Timestamp range: {df['timestamp'].min()} - {df['timestamp'].max()}")
        
        print("\n=== Format Evaluation Summary ===")
        print(f"Average Think Tag Rate: {df['has_think_rate'].mean():.3f}")
        print(f"Average Answer Tag Rate: {df['has_answer_rate'].mean():.3f}")
        print(f"Average Valid JSON Rate: {df['has_valid_json_rate'].mean():.3f}")
        print(f"Average Think Before Answer Rate: {df['think_before_answer_rate'].mean():.3f}")
        print(f"Average Malformed Structure Rate: {df['malformed_structure_rate'].mean():.3f}")
        print(f"Average Format Correct Rate: {df['format_correct_rate'].mean():.3f}")
        print(f"Average Think Tags per Sample: {df['avg_think_tags'].mean():.3f}")
        print(f"Average Answer Tags per Sample: {df['avg_answer_tags'].mean():.3f}")
        
        print("\n=== Best Performance Checkpoint ===")
        best_idx = df['format_correct_rate'].idxmax()
        best_checkpoint = df.iloc[best_idx]
        print(f"Step: {best_checkpoint['step']}")
        print(f"Format Correct Rate: {best_checkpoint['format_correct_rate']:.3f}")
        print(f"Think Tag Rate: {best_checkpoint['has_think_rate']:.3f}")
        print(f"Answer Tag Rate: {best_checkpoint['has_answer_rate']:.3f}")
        print(f"Valid JSON Rate: {best_checkpoint['has_valid_json_rate']:.3f}")
        print(f"Think Before Answer Rate: {best_checkpoint['think_before_answer_rate']:.3f}")
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
