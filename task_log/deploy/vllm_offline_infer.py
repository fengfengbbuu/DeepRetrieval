#!/usr/bin/env python3
"""
VLLM Offline Inference Script
基于VLLM的离线推理脚本，结合了zero_shot.py的数据处理功能和chat_basic_vllm.py的VLLM推理能力
"""

import json
import time
import argparse
import yaml
from datetime import datetime
import os
from typing import List, Dict, Any
import logging
from pathlib import Path
import pandas as pd

from vllm import LLM, SamplingParams
from vllm.utils import FlexibleArgumentParser


class DataParser:
    """数据解析类，支持多种数据格式"""
    
    @staticmethod
    def load_data(file_path: str) -> List[Dict[str, Any]]:
        """加载数据文件，支持 .jsonl 和 .parquet 格式"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix == '.jsonl':
            return DataParser._load_jsonl(file_path)
        elif file_path.suffix == '.parquet':
            return DataParser._load_parquet(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    @staticmethod
    def _load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
        """加载 JSONL 文件"""
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line.strip()))
        return data
    
    @staticmethod
    def _load_parquet(file_path: Path) -> List[Dict[str, Any]]:
        """加载 Parquet 文件"""
        df = pd.read_parquet(file_path)
        # 将 DataFrame 转换为字典列表
        data = df.to_dict('records')
        return data
    
    @staticmethod
    def extract_messages(item: Dict[str, Any], prompt_key: str) -> List[Dict[str, str]]:
        """提取消息列表，支持不同的数据格式"""
        if prompt_key not in item:
            return None
        
        prompt_value = item[prompt_key]
        
        # 如果 prompt_value 是列表，直接返回
        if isinstance(prompt_value, list):
            return prompt_value
        
        # 如果 prompt_value 是 numpy.ndarray，转换为列表
        elif hasattr(prompt_value, 'tolist'):
            return prompt_value.tolist()
        
        # 如果 prompt_value 是字典，尝试提取 messages 字段
        elif isinstance(prompt_value, dict):
            if "messages" in prompt_value:
                return prompt_value["messages"]
            else:
                # 如果是字典但没有 messages 字段，可能需要其他处理
                # 这里可以根据实际数据结构进行调整
                return [prompt_value]
        
        # 其他情况返回空列表
        else:
            return []


class VLLMOfflineInference:
    """VLLM离线推理类"""
    
    def __init__(self, args):
        self.args = args
        
        # 设置日志
        self.setup_logging()
        
        # 加载格式模板
        self.load_format_templates()
        
        # 初始化VLLM模型
        self.setup_vllm_model()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }
        
        # 批处理相关
        self.results_buffer = []
        self.failed_buffer = []
        self.processed_count = 0
        
        # 设置输出目录
        self.setup_output_directory()
        
        # 设置输出文件路径
        self.output_file = args.output_file
    
    def setup_logging(self):
        """设置日志"""
        global logger
        # 确保输出目录存在
        os.makedirs(self.args.output_dir, exist_ok=True)
        log_file = os.path.join(self.args.output_dir, "inference.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
    
    def load_format_templates(self):
        """加载格式模板"""
        # 获取脚本所在目录
        script_dir = Path(__file__).parent.parent / "no_training" / "zero-shot"
        
        # 加载CoT格式模板
        cot_format_file = script_dir / "cot_output_format.txt"
        if cot_format_file.exists():
            with open(cot_format_file, 'r', encoding='utf-8') as f:
                self.cot_format = f.read().strip()
        else:
            # 默认CoT格式
            self.cot_format = """Show your work in <think> </think> tags. Your final response must be in JSON format within <answer> </answer>. For example,
<think>
[thinking process]
</think>
<answer>
{
    "sql": "SELECT ... (in one line)"
} 
</answer>."""
        
        # 加载非CoT格式模板
        output_format_file = script_dir / "output_format.txt"
        if output_format_file.exists():
            with open(output_format_file, 'r', encoding='utf-8') as f:
                self.output_format = f.read().strip()
        else:
            # 默认非CoT格式
            self.output_format = """Your final response must be in JSON format within <answer> </answer>. For example,
<answer>
{
    "sql": "SELECT ... (in one line)"
} 
</answer>."""
        
        logger.info(f"Loaded CoT format template: {len(self.cot_format)} chars")
        logger.info(f"Loaded output format template: {len(self.output_format)} chars")
    
    def setup_vllm_model(self):
        """初始化VLLM模型"""
        model_path = getattr(self.args, 'model_path', self.args.model_name)
        logger.info(f"Initializing VLLM model: {self.args.model_name} (path: {model_path})")
        
        # 创建VLLM模型
        self.llm = LLM(
            model=model_path,
            tensor_parallel_size=getattr(self.args, 'tensor_parallel_size', 1),
            gpu_memory_utilization=getattr(self.args, 'gpu_memory_utilization', 0.9),
            max_model_len=getattr(self.args, 'max_model_len', None),
            trust_remote_code=getattr(self.args, 'trust_remote_code', True)
        )
        
        # 创建采样参数
        self.sampling_params = SamplingParams(
            temperature=getattr(self.args, 'temperature', 0.0),
            top_p=getattr(self.args, 'top_p', 1.0),
            top_k=getattr(self.args, 'top_k', -1),
            max_tokens=getattr(self.args, 'max_tokens', 512),
            stop=getattr(self.args, 'stop', None)
        )
        
        logger.info(f"VLLM model initialized successfully")
        logger.info(f"Sampling params: temperature={self.sampling_params.temperature}, "
                   f"top_p={self.sampling_params.top_p}, max_tokens={self.sampling_params.max_tokens}")
    
    def setup_output_directory(self):
        """设置输出目录"""
        # 创建输出目录结构
        self.output_dir = Path(self.args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Output directory: {self.output_dir}")
    
    def get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """获取嵌套字段的值，支持 key1.key2 格式"""
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
    
    def modify_messages_for_cot(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """修改messages以支持CoT/非CoT模式"""
        if self.args.with_cot:
            # CoT模式：保持原样
            return messages
        else:
            # 非CoT模式：替换格式说明
            modified_messages = []
            for message in messages:
                if message.get("role") == "user":
                    content = message["content"]
                    # 替换CoT格式为非CoT格式
                    if self.cot_format in content:
                        content = content.replace(self.cot_format, self.output_format)
                        modified_messages.append({
                            "role": message["role"],
                            "content": content
                        })
                    else:
                        modified_messages.append(message)
                else:
                    modified_messages.append(message)
            return modified_messages
    
    def make_inference(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """使用VLLM进行推理"""
        try:
            # 修改messages以支持CoT/非CoT模式
            modified_messages = self.modify_messages_for_cot(messages)
            
            # 使用VLLM的chat接口
            outputs = self.llm.chat(
                [modified_messages], 
                sampling_params=self.sampling_params,
                use_tqdm=False
            )
            
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1
            
            # 提取生成的文本
            if outputs and len(outputs) > 0:
                generated_text = outputs[0].outputs[0].text
                return {
                    "success": True,
                    "response": {
                        "choices": [{
                            "message": {
                                "content": generated_text
                            }
                        }]
                    }
                }
            else:
                self.stats["failed_requests"] += 1
                return {
                    "success": False,
                    "error": "No output generated"
                }
                
        except Exception as e:
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1
            logger.error(f"VLLM inference error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_batch_results(self, output_file: str, force_save: bool = False):
        """增量保存批处理结果"""
        if not force_save and len(self.results_buffer) < 50:
            return
        
        if not self.results_buffer and not self.failed_buffer:
            return
        
        # 保存成功的结果
        if self.results_buffer:
            success_file = output_file.replace('.jsonl', '_success.jsonl')
            with open(success_file, 'a', encoding='utf-8') as f:
                for result in self.results_buffer:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            logger.info(f"Saved {len(self.results_buffer)} successful results to {success_file}")
            self.results_buffer.clear()
        
        # 保存失败的结果
        if self.failed_buffer:
            failed_file = output_file.replace('.jsonl', '_failed.jsonl')
            with open(failed_file, 'a', encoding='utf-8') as f:
                for result in self.failed_buffer:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            logger.info(f"Saved {len(self.failed_buffer)} failed results to {failed_file}")
            self.failed_buffer.clear()
    
    def add_result_to_buffer(self, result_record: Dict[str, Any]):
        """将结果添加到缓冲区"""
        if result_record["api_result"]["success"]:
            self.results_buffer.append(result_record)
        else:
            self.failed_buffer.append(result_record)
        
        self.processed_count += 1
        
        # 检查是否需要保存
        if len(self.results_buffer) + len(self.failed_buffer) >= 50:
            self.save_batch_results(self.output_file)
    
    def process_test_data(self):
        """处理测试数据"""
        model_path = getattr(self.args, 'model_path', self.args.model_name)
        logger.info(f"Starting VLLM offline inference")
        logger.info(f"Model: {self.args.model_name} (path: {model_path})")
        logger.info(f"With CoT: {self.args.with_cot}")
        logger.info(f"Sample num: {self.args.sample_num}")
        logger.info(f"Results will be saved to {self.output_file}")
        
        # 清空输出文件（如果存在）
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
        success_file = self.output_file.replace('.jsonl', '_success.jsonl')
        failed_file = self.output_file.replace('.jsonl', '_failed.jsonl')
        if os.path.exists(success_file):
            os.remove(success_file)
        if os.path.exists(failed_file):
            os.remove(failed_file)
        
        # 读取输入数据
        data = DataParser.load_data(self.args.test_set_path)
        
        # 如果指定了样本数量，则只处理指定数量的样本
        if self.args.sample_num > 0:
            data = data[:self.args.sample_num]
        
        total_items = len(data)
        logger.info(f"Total items to process: {total_items}")
        
        for i, item in enumerate(data):
            logger.info(f"Processing item {i+1}/{total_items}")
            
            # 提取消息列表
            messages = DataParser.extract_messages(item, self.args.prompt_key)
            if not messages:
                logger.warning(f"Item {i+1} missing or invalid '{self.args.prompt_key}' field, skipping")
                continue
            
            # 进行VLLM推理
            result = self.make_inference(messages)
            
            # 获取数据库路径和标准答案
            db_path = self.get_nested_value(item, self.args.db_path_key)
            ground_truth = self.get_nested_value(item, self.args.ground_truth_key)
            
            # 构建结果记录
            result_record = {
                "index": i,
                "original_data": {
                    "question": item.get("question", ""),
                    "db_id": item.get("db_id", ""),
                    "data_source": item.get("data_source", ""),
                    "db_path": db_path,
                    "ground_truth": ground_truth
                },
                "api_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加到缓冲区并检查是否需要保存
            self.add_result_to_buffer(result_record)
            
            if result["success"]:
                logger.info(f"Item {i+1} processed successfully")
            else:
                logger.error(f"Item {i+1} failed: {result['error']}")
            
            # 每处理100个项目输出一次进度
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{total_items} ({((i+1)/total_items)*100:.1f}%)")
                logger.info(f"Stats: Success={self.stats['successful_requests']}, Failed={self.stats['failed_requests']}")
                logger.info(f"Buffer: {len(self.results_buffer)} success, {len(self.failed_buffer)} failed")
        
        # 保存剩余的结果
        self.save_batch_results(self.output_file, force_save=True)
        
        # 合并最终结果文件
        self.merge_final_results()
        
        # 保存配置信息
        self.save_config()
        
        # 输出最终统计
        self.print_final_stats(total_items)
    
    def merge_final_results(self):
        """合并最终结果文件"""
        success_file = self.output_file.replace('.jsonl', '_success.jsonl')
        failed_file = self.output_file.replace('.jsonl', '_failed.jsonl')
        
        all_results = []
        
        # 读取成功的结果
        if os.path.exists(success_file):
            with open(success_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        all_results.append(json.loads(line.strip()))
        
        # 读取失败的结果
        if os.path.exists(failed_file):
            with open(failed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        all_results.append(json.loads(line.strip()))
        
        # 按索引排序
        all_results.sort(key=lambda x: x.get('index', 0))
        
        # 写入合并后的结果
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for result in all_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"Merged {len(all_results)} results into {self.output_file}")
    
    def save_config(self):
        """保存配置信息"""
        model_path = getattr(self.args, 'model_path', self.args.model_name)
        config = {
            "model_name": self.args.model_name,
            "model_path": model_path,
            "test_set_path": self.args.test_set_path,
            "prompt_key": self.args.prompt_key,
            "sample_num": self.args.sample_num,
            "db_path_key": self.args.db_path_key,
            "ground_truth_key": self.args.ground_truth_key,
            "with_cot": self.args.with_cot,
            "temperature": self.sampling_params.temperature,
            "top_p": self.sampling_params.top_p,
            "max_tokens": self.sampling_params.max_tokens,
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats
        }
        
        config_file = self.output_dir / "args.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Configuration saved to {config_file}")
    
    def print_final_stats(self, total_items: int):
        """输出最终统计信息"""
        logger.info("=" * 50)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total items: {total_items}")
        logger.info(f"Total inference requests: {self.stats['total_requests']}")
        logger.info(f"Successful requests: {self.stats['successful_requests']}")
        logger.info(f"Failed requests: {self.stats['failed_requests']}")
        if self.stats['total_requests'] > 0:
            logger.info(f"Success rate: {(self.stats['successful_requests']/self.stats['total_requests'])*100:.2f}%")
        logger.info("=" * 50)


def create_parser():
    """创建参数解析器"""
    parser = argparse.ArgumentParser(description="VLLM Offline Inference")
    
    # 模型相关参数
    parser.add_argument("--model_name", type=str, required=True,
                       help="模型名称/昵称")
    parser.add_argument("--model_path", type=str, default=None,
                       help="模型路径，如果不指定则使用model_name")

    # VLLM相关参数
    parser.add_argument("--tensor_parallel_size", type=int, default=1,
                       help="张量并行大小")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.9,
                       help="GPU内存利用率")
    parser.add_argument("--max_model_len", type=int, default=None,
                       help="模型最大长度")
    parser.add_argument("--trust_remote_code", action="store_true",
                       help="是否信任远程代码")
    
    # 采样参数
    parser.add_argument("--temperature", type=float, default=0.0,
                       help="采样温度")
    parser.add_argument("--top_p", type=float, default=1.0,
                       help="Top-p采样")
    parser.add_argument("--top_k", type=int, default=-1,
                       help="Top-k采样")
    parser.add_argument("--max_tokens", type=int, default=512,
                       help="最大生成token数")
    parser.add_argument("--stop", type=str, nargs="+", default=None,
                       help="停止词")
    
    # 数据相关参数
    parser.add_argument("--test_set_path", type=str, required=True,
                       help="测试集路径")
    parser.add_argument("--prompt_key", type=str, default="messages",
                       help="模型input对应的key")
    parser.add_argument("--sample_num", type=int, default=-1,
                       help="抽取指定个数的样例进行测试，-1表示处理所有样例")
    parser.add_argument("--db_path_key", type=str, default="extra_info.db_path",
                       help="数据库路径对应的字段名，支持嵌套访问如 key1.key2")
    parser.add_argument("--ground_truth_key", type=str, default="reward_model.ground_truth.target",
                       help="标准答案对应字段名，支持嵌套访问如 key1.key2")
    
    # 输出相关参数
    parser.add_argument("--output_root", type=str, required=True,
                       help="输出根目录")
    
    # 实验相关参数
    parser.add_argument("--with_cot", action="store_true",
                       help="是否使用CoT模式")
    
    return parser


def parse_args():
    """解析命令行参数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 生成输出目录
    test_name = Path(args.test_set_path).stem
    cot_info = "wcot" if args.with_cot else "wocot"
    sample_info = "all" if args.sample_num == -1 else f"sample{args.sample_num}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 如果没有指定model_path，则使用model_name作为路径
    if args.model_path is None:
        args.model_path = args.model_name
    
    # 使用model_name作为输出目录名
    args.output_dir = f"{args.output_root}/{args.model_name}/{date_str}"
    
    if args.with_cot:
        args.output_dir = f"{args.output_dir}/wcot"
    else:
        args.output_dir = f"{args.output_dir}/wocot"
    
    args.output_file = f"{args.output_dir}/{test_name}.{cot_info}.{sample_info}.jsonl"
    
    return args


def main():
    """主函数"""
    args = parse_args()
    
    # 创建推理实例并处理数据
    inference = VLLMOfflineInference(args)
    
    try:
        inference.process_test_data()
        logger.info("VLLM offline inference completed successfully!")
    except KeyboardInterrupt:
        logger.info("Inference interrupted by user")
    except Exception as e:
        logger.error(f"Inference failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
