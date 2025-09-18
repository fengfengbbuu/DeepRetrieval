#!/usr/bin/env python3
"""
将JSONL格式的数据集转换为HuggingFace datasets格式
支持train, dev, test三个子集的整合和转换
"""

import json
import os
from pathlib import Path
from datasets import Dataset, DatasetDict

def load_jsonl(file_path):
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def convert_to_hf_dataset(input_dir, output_dir):
    """
    将JSONL文件转换为HuggingFace datasets格式
    
    Args:
        input_dir: 输入目录，包含train, dev, test的JSONL文件
        output_dir: 输出目录，保存转换后的HF格式数据集
    """
    print(f"开始转换数据集从 {input_dir} 到 {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义文件映射关系
    file_mapping = {
        'train': None,
        'validation': None,  # HF datasets通常使用validation而不是dev
        'test': None
    }
    
    # 查找对应的文件
    for filename in os.listdir(input_dir):
        if filename.endswith('.jsonl'):
            if 'train' in filename:
                file_mapping['train'] = os.path.join(input_dir, filename)
            elif 'dev' in filename:
                file_mapping['validation'] = os.path.join(input_dir, filename)
            elif 'test' in filename:
                file_mapping['test'] = os.path.join(input_dir, filename)
    
    # 检查文件是否存在
    missing_files = [split for split, path in file_mapping.items() if path is None]
    if missing_files:
        print(f"警告: 未找到以下分割的文件: {missing_files}")
    
    # 创建数据集字典
    datasets = {}
    
    for split, file_path in file_mapping.items():
        if file_path and os.path.exists(file_path):
            print(f"正在加载 {split} 集: {file_path}")
            data = load_jsonl(file_path)
            print(f"{split} 集样本数: {len(data)}")
            
            # 创建HuggingFace Dataset
            dataset = Dataset.from_list(data)
            datasets[split] = dataset
            
            # 显示数据集信息
            print(f"{split} 集特征: {dataset.features}")
        else:
            print(f"跳过 {split} 集: 文件不存在")
    
    if not datasets:
        raise ValueError("没有找到任何有效的JSONL文件")
    
    # 创建DatasetDict
    dataset_dict = DatasetDict(datasets)
    
    print(f"\n数据集统计:")
    print(f"总分割数: {len(dataset_dict)}")
    for split_name, dataset in dataset_dict.items():
        print(f"{split_name}: {len(dataset)} 样本")
    
    # 保存数据集
    print(f"\n正在保存数据集到: {output_dir}")
    dataset_dict.save_to_disk(output_dir)
    print("数据集保存完成!")
    
    # 验证保存的数据集
    print(f"\n验证保存的数据集...")
    try:
        from datasets import load_from_disk
        loaded_dataset = load_from_disk(output_dir)
        print("✅ 数据集可以成功加载")
        print(f"加载的数据集分割: {list(loaded_dataset.keys())}")
        for split_name, dataset in loaded_dataset.items():
            print(f"{split_name}: {len(dataset)} 样本")
    except Exception as e:
        print(f"❌ 数据集加载失败: {e}")
        raise
    
    return dataset_dict

def test_dataset_loading(output_dir):
    """测试数据集加载功能"""
    print(f"\n=== 测试数据集加载功能 ===")
    
    try:
        from datasets import load_from_disk
        
        # 测试load_from_disk
        print("测试 datasets.load_from_disk()...")
        dataset = load_from_disk(output_dir)
        print("✅ datasets.load_from_disk() 成功")
        
        # 显示数据集信息
        print(f"数据集分割: {list(dataset.keys())}")
        for split_name, split_data in dataset.items():
            print(f"{split_name}: {len(split_data)} 样本")
            if len(split_data) > 0:
                print(f"  特征: {split_data.features}")
                print(f"  示例: {split_data[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    # 设置路径
    input_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/split"
    output_dir = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/hf"
    
    print("开始JSONL到HuggingFace Datasets转换任务")
    print("=" * 60)
    
    try:
        # 执行转换
        dataset_dict = convert_to_hf_dataset(input_dir, output_dir)
        
        # 测试加载功能
        success = test_dataset_loading(output_dir)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 转换任务完成! 数据集已成功转换为HuggingFace格式")
            print(f"输出目录: {output_dir}")
            print("可以使用 datasets.load_from_disk() 加载数据集")
        else:
            print("\n" + "=" * 60)
            print("❌ 转换任务失败!")
            
    except Exception as e:
        print(f"\n❌ 转换过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

