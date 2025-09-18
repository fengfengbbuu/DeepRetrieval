#!/usr/bin/env python3
"""
Zero-Shot LLM API Inference Script
基于REF_FILE的增强版本，支持参数传递和CoT/非CoT模式
"""

import json
import time
import requests
import argparse
import yaml
from datetime import datetime
import os
from typing import List, Dict, Any
import logging
from pathlib import Path
import pandas as pd

class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def wait_if_needed(self):
        """如果需要，等待直到可以发送下一个请求"""
        current_time = time.time()
        
        # 清理1分钟前的请求记录
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # 如果已达到限制，等待
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
        
        self.request_times.append(time.time())

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

class ZeroShotInference:
    """Zero-Shot推理类"""
    
    def __init__(self, args):
        self.args = args
        
        # 设置日志
        self.setup_logging()
        
        # 加载格式模板
        self.load_format_templates()
        
        # 设置API配置
        self.api_url = f"{args.base_url}/v1/chat/completions"
        self.api_key = args.api_key
        self.model_name = args.model_name
        
        # 设置请求配置
        self.request_config = {
            "max_tokens": 512,
            "temperature": 0.0
        }
        
        # 频率控制
        self.rate_limiter = RateLimiter(30)  # 每分钟30个请求
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_requests": 0
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
        script_dir = Path(__file__).parent
        
        # 加载CoT格式模板
        cot_format_file = script_dir / "cot_output_format.txt"
        with open(cot_format_file, 'r', encoding='utf-8') as f:
            self.cot_format = f.read().strip()
        
        # 加载非CoT格式模板
        output_format_file = script_dir / "output_format.txt"
        with open(output_format_file, 'r', encoding='utf-8') as f:
            self.output_format = f.read().strip()
        
        logger.info(f"Loaded CoT format template: {len(self.cot_format)} chars")
        logger.info(f"Loaded output format template: {len(self.output_format)} chars")
    
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
    
    def make_request(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict[str, Any]:
        """发送API请求"""
        # 修改messages以支持CoT/非CoT模式
        modified_messages = self.modify_messages_for_cot(messages)
        
        # 只取前两个消息（system + user）
        payload_messages = modified_messages[:2]
        
        payload = {
            "model": self.model_name,
            "messages": payload_messages,
            **self.request_config
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        for attempt in range(max_retries + 1):
            try:
                # 频率限制
                self.rate_limiter.wait_if_needed()
                
                # 发送请求
                self.stats["total_requests"] += 1
                if attempt > 0:
                    self.stats["retry_requests"] += 1
                    logger.info(f"Retry attempt {attempt} for request")
                
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    self.stats["successful_requests"] += 1
                    return {
                        "success": True,
                        "response": result,
                        "attempt": attempt + 1
                    }
                else:
                    logger.warning(f"API request failed with status {response.status_code}: {response.text}")
                    if attempt < max_retries:
                        delay = 1.0 * (2.0 ** attempt)  # 指数退避
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        self.stats["failed_requests"] += 1
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}: {response.text}",
                            "attempt": attempt + 1
                        }
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception: {e}")
                if attempt < max_retries:
                    delay = 1.0 * (2.0 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.stats["failed_requests"] += 1
                    return {
                        "success": False,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
        
        return {
            "success": False,
            "error": "Max retries exceeded",
            "attempt": max_retries + 1
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
        logger.info(f"Starting zero-shot inference")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Base URL: {self.args.base_url}")
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
            
            # 发送API请求
            result = self.make_request(messages)
            
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
                logger.info(f"Item {i+1} processed successfully (attempt {result['attempt']})")
            else:
                logger.error(f"Item {i+1} failed after {result['attempt']} attempts: {result['error']}")
            
            # 每处理100个项目输出一次进度
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{total_items} ({((i+1)/total_items)*100:.1f}%)")
                logger.info(f"Stats: Success={self.stats['successful_requests']}, Failed={self.stats['failed_requests']}, Retries={self.stats['retry_requests']}")
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
        config = {
            "model_name": self.args.model_name,
            "base_url": self.args.base_url,
            "api_key": self.args.api_key,
            "test_set_path": self.args.test_set_path,
            "prompt_key": self.args.prompt_key,
            "sample_num": self.args.sample_num,
            "db_path_key": self.args.db_path_key,
            "ground_truth_key": self.args.ground_truth_key,
            "with_cot": self.args.with_cot,
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
        logger.info(f"Total API requests: {self.stats['total_requests']}")
        logger.info(f"Successful requests: {self.stats['successful_requests']}")
        logger.info(f"Failed requests: {self.stats['failed_requests']}")
        logger.info(f"Retry requests: {self.stats['retry_requests']}")
        logger.info(f"Success rate: {(self.stats['successful_requests']/self.stats['total_requests'])*100:.2f}%")
        logger.info("=" * 50)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Zero-Shot LLM API Inference")
    
    # 模型方面
    parser.add_argument("--model_name", type=str, default="qwen2_5_05", 
                       help="模型名称")
    parser.add_argument("--base_url", type=str, default="http://10.1.1.15:11111", 
                       help="模型URL地址")
    parser.add_argument("--api_key", type=str, default="qwen2_5_05", 
                       help="API key")
    
    # 数据方面
    parser.add_argument("--test_set_path", type=str, 
                       default="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl",
                       help="测试集地址")
    parser.add_argument("--prompt_key", type=str, default="messages", 
                       help="模型input对应的key")
    parser.add_argument("--sample_num", type=int, default=-1, 
                       help="抽取指定个数的样例进行测试，-1表示处理所有样例")
    parser.add_argument("--db_path_key", type=str, default="extra_info.db_path", 
                       help="数据库路径对应的字段名，支持嵌套访问如 key1.key2")
    parser.add_argument("--ground_truth_key", type=str, default="reward_model.ground_truth.target", 
                       help="标准答案对应字段名，支持嵌套访问如 key1.key2")

    parser.add_argument("--output_root", type=str, default=None,
                       help="输出目录，必须指定")

    # 实验方面
    # parser.add_argument("--with_cot", type=bool, default=True,
    #                    help="是否使用CoT模式 (true/false)")
    parser.add_argument("--with_cot", action="store_true", help="是否使用CoT模式 (true/false)")
    
    args = parser.parse_args()
    
    # 生成输出目录
    test_name = Path(args.test_set_path).stem
    cot_info = "wcot" if args.with_cot else "wocot"
    sample_info = "all" if args.sample_num == -1 else f"sample{args.sample_num}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    if args.output_root is None:
        raise ValueError(f"output_root is None，输出目录必须指定")
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
    inference = ZeroShotInference(args)
    
    try:
        inference.process_test_data()
        logger.info("Zero-shot inference completed successfully!")
    except KeyboardInterrupt:
        logger.info("Inference interrupted by user")
    except Exception as e:
        logger.error(f"Inference failed with error: {e}")
        raise

if __name__ == "__main__":
    main()
