#!/usr/bin/env python3
"""
LLM API Inference Script for Spider Test Dataset
基于API模板对测试集进行推理
"""

import json
import time
import requests
from datetime import datetime
import os
from typing import List, Dict, Any
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API配置 (与模板保持一致)
API_URL = "http://10.1.1.15:11111/v1/chat/completions"
API_KEY = "qwen2_5_05"
MODEL_NAME = "qwen2_5_05"

# 请求配置
REQUEST_CONFIG = {
    "max_tokens": 512,
    "temperature": 0.0
}

# 频率控制配置
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 30,  # 每分钟最多30个请求
    "initial_delay": 0.1,       # 初始延迟
    "max_retries": 3,           # 最大重试次数
    "retry_delay": 1.0,         # 重试延迟
    "backoff_factor": 2.0       # 退避因子
}

# 批处理配置
BATCH_CONFIG = {
    "batch_size": 50,           # 每批处理数量
    "save_interval": 50         # 保存间隔（条数）
}

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

class LLMAPIInference:
    """LLM API推理类"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(RATE_LIMIT_CONFIG["requests_per_minute"])
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
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
    
    def make_request(self, messages: List[Dict[str, str]], max_retries: int = None) -> Dict[str, Any]:
        """发送API请求"""
        if max_retries is None:
            max_retries = RATE_LIMIT_CONFIG["max_retries"]
        
        payload = {
            "model": MODEL_NAME,
            "messages": messages[:2],
            **REQUEST_CONFIG
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
                
                response = requests.post(API_URL, headers=self.headers, json=payload, timeout=30)
                
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
                        delay = RATE_LIMIT_CONFIG["retry_delay"] * (RATE_LIMIT_CONFIG["backoff_factor"] ** attempt)
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
                    delay = RATE_LIMIT_CONFIG["retry_delay"] * (RATE_LIMIT_CONFIG["backoff_factor"] ** attempt)
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
        if not force_save and len(self.results_buffer) < BATCH_CONFIG["save_interval"]:
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
        
        # 注意：这里不需要再次保存到主文件，因为success和failed文件已经包含了所有结果
        # 主文件会在最后合并时创建，或者通过读取success和failed文件来生成
    
    def add_result_to_buffer(self, result_record: Dict[str, Any]):
        """将结果添加到缓冲区"""
        if result_record["api_result"]["success"]:
            self.results_buffer.append(result_record)
        else:
            self.failed_buffer.append(result_record)
        
        self.processed_count += 1
        
        # 检查是否需要保存
        if len(self.results_buffer) + len(self.failed_buffer) >= BATCH_CONFIG["save_interval"]:
            self.save_batch_results("/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference_results.jsonl")
    
    def process_test_data(self, input_file: str, output_file: str):
        """处理测试数据"""
        logger.info(f"Starting inference for {input_file}")
        logger.info(f"Results will be saved incrementally to {output_file}")
        logger.info(f"Batch size: {BATCH_CONFIG['save_interval']} items")
        
        # 清空输出文件（如果存在）
        if os.path.exists(output_file):
            os.remove(output_file)
        success_file = output_file.replace('.jsonl', '_success.jsonl')
        failed_file = output_file.replace('.jsonl', '_failed.jsonl')
        if os.path.exists(success_file):
            os.remove(success_file)
        if os.path.exists(failed_file):
            os.remove(failed_file)
        
        # 读取输入数据
        with open(input_file, 'r', encoding='utf-8') as f:
            data = [json.loads(line.strip()) for line in f if line.strip()]
        
        total_items = len(data)
        logger.info(f"Total items to process: {total_items}")
        
        for i, item in enumerate(data):
            logger.info(f"Processing item {i+1}/{total_items}")
            
            # 提取messages字段
            if "messages" not in item:
                logger.warning(f"Item {i+1} missing 'messages' field, skipping")
                continue
            
            messages = item["messages"]
            
            # 发送API请求
            result = self.make_request(messages)
            
            # 构建结果记录
            result_record = {
                "index": i,
                "original_data": {
                    "question": item.get("question", ""),
                    "db_id": item.get("db_id", ""),
                    "data_source": item.get("data_source", "")
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
        self.save_batch_results(output_file, force_save=True)
        
        # 合并最终结果文件
        self.merge_final_results(output_file)
        
        # 输出最终统计
        self.print_final_stats(total_items)
    
    def merge_final_results(self, output_file: str):
        """合并最终结果文件"""
        success_file = output_file.replace('.jsonl', '_success.jsonl')
        failed_file = output_file.replace('.jsonl', '_failed.jsonl')
        
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
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in all_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"Merged {len(all_results)} results into {output_file}")
    
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

def main():
    """主函数"""
    # 输入和输出文件路径
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/task_log/no_training/inference_results.jsonl"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 创建推理实例并处理数据
    inference = LLMAPIInference()
    
    try:
        inference.process_test_data(input_file, output_file)
        logger.info("Inference completed successfully!")
    except KeyboardInterrupt:
        logger.info("Inference interrupted by user")
    except Exception as e:
        logger.error(f"Inference failed with error: {e}")
        raise

if __name__ == "__main__":
    main()

