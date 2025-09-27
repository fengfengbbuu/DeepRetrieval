#!/bin/bash

# BIRD SQL 分析任务测试脚本
# 激活环境并运行分析脚本

echo "激活 swift 环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate swift

echo "运行 BIRD SQL 分析脚本..."
python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/bird/bird_analyze_task.py \
    --input_file "/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/train.parquet" \
    --start_idx 0 \
    --end_idx 50 \
    --output_root "/root/data1/projects/RL/DeepRetrieval/task_log/analyze/bird"

echo "分析完成！"
