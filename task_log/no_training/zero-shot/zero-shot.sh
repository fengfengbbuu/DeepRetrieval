#!/bin/bash

########################################################################
# Zero-Shot测试脚本
# 用于验证zero_shot.py的功能

# echo "=== Zero-Shot Inference Test Script ==="
# echo "Date: $(date)"
# echo ""

# # 设置环境
# echo "1. 激活conda环境..."
# conda activate swift
# echo ""

# # 测试1: CoT模式，处理所有数据
# echo "2. 测试CoT模式（处理所有数据）..."
# python /root/data1/projects/RL/DeepRetrieval/task_log/no_training/zero-shot/zero_shot.py \
#     --model_name "qwen2_5_05" \
#     --base_url "http://10.1.1.15:11111" \
#     --api_key "qwen2_5_05" \
#     --test_set_path "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl" \
#     --prompt_key "messages" \
#     --sample_num 10 \
#     --with_cot

# echo ""
# echo "CoT模式测试完成！"
# echo ""

# # 测试2: 非CoT模式，处理10个样本
# echo "3. 测试非CoT模式（处理10个样本）..."
# python /root/data1/projects/RL/DeepRetrieval/task_log/no_training/zero-shot/zero_shot.py \
#     --model_name "qwen2_5_05" \
#     --base_url "http://10.1.1.15:11111" \
#     --api_key "qwen2_5_05" \
#     --test_set_path "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl" \
#     --prompt_key "messages" \
#     --sample_num 10 \
#     --no_cot

# echo ""
# echo "非CoT模式测试完成！"
# echo ""

# # 检查结果文件
# echo "4. 检查生成的结果文件..."
# echo "查找输出目录..."
# find /root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot -name "*.jsonl" -type f | head -5

# echo ""
# echo "查找配置文件..."
# find /root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot -name "args.yaml" -type f | head -5

# echo ""
# echo "=== 测试完成 ==="
# echo "请检查生成的结果文件和配置信息"

########################################################################

# 模型列表 ['gpt-3.5-turbo', 'gpt-4o-2024-11-20', 'claude-3-haiku-20240307']
# sample_num 为 100
# with_cot 为 True

SAMPLE_NUM=100
# MODEL_LIST=("gpt-3.5-turbo" "gpt-4o-2024-11-20" "claude-3-haiku-20240307" "claude-3-5-sonnet-latest")
# MODEL_LIST=("claude-3-haiku-20240307" "claude-3-5-sonnet-latest")
# MODEL_LIST=("claude-3-5-sonnet-latest")
MODEL_LIST=("claude-3-haiku-20240307")
BASE_URL="https://api.openai-proxy.org"
# API_KEY="sk-8YniBcTEPqUFmGAbqsnAS8I2ofII8SA1B8s3I5y1Ewxv2uKX"
API_KEY_LIST=(
    # "sk-8YniBcTEPqUFmGAbqsnAS8I2ofII8SA1B8s3I5y1Ewxv2uKX" 
    # "sk-8YniBcTEPqUFmGAbqsnAS8I2ofII8SA1B8s3I5y1Ewxv2uKX" 
    # "sk-8YniBcTEPqUFmGAbqsnAS8I2ofII8SA1B8s3I5y1Ewxv2uKX" 
    "sk-8YniBcTEPqUFmGAbqsnAS8I2ofII8SA1B8s3I5y1Ewxv2uKX"
)
OUTPUT_ROOT="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/bird/zero-shot"

# SAMPLE_NUM=500
# # MODEL_LIST=("qwen2_5_1_5")
# # MODEL_LIST=("qwen2_5_05")
# MODEL_LIST=("qwen2_5_0_5")
# # BASE_URL="http://10.1.1.15:11111"
# BASE_URL="http://10.1.1.14:11111"
# # API_KEY_LIST=("qwen2_5_1_5")
# API_KEY_LIST=("qwen2_5_0_5")
# # API_KEY="qwen2_5_1_5"
# # API_KEY="qwen2_5_05"
# # API_KEY="qwen2_5_0_5"
# # OUTPUT_ROOT="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot"
# # OUTPUT_ROOT="/root/data1/projects/RL/DeepRetrieval/outputs/rl/spider"
# # OUTPUT_ROOT=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum/global_step_258/eval
# OUTPUT_ROOT="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/bird/zero-shot"

# WITH_COT="True"

# 测试文件配置
# 原始 JSONL 文件
# JSONL_TEST_PATH="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/test.jsonl"
# JSONL_PROMPT_KEY="messages"

# 新的 Parquet 文件
# WOCOT_TEST_PATH="/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/test.messages.wocot.parquet"
WOCOT_TEST_PATH="/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/test.messages.wocot.parquet"
# COT_TEST_PATH="/root/data1/projects/RL/DeepRetrieval/code/data/sql/spider/test.messages.wcot.parquet"
COT_TEST_PATH="/root/data1/projects/RL/DeepRetrieval/code/data/sql/bird/test.messages.wcot.parquet"
PARQUET_PROMPT_KEY="prompt"

# 通用配置
DB_PATH_KEY="extra_info.db_path"
GROUND_TRUTH_KEY="reward_model.ground_truth.target"

echo ""
echo "5. 多模型批量测试（sample_num=${SAMPLE_NUM}, with_cot=${WITH_COT}）..."
echo ""

# 测试1: 原始 JSONL 文件
# echo "测试1: 原始 JSONL 文件 (CoT模式)"
# for MODEL in "${MODEL_LIST[@]}"; do
#     echo "---------------------------------------------"
#     echo "正在测试模型: $MODEL (JSONL + CoT)"
#     python /root/data1/projects/RL/DeepRetrieval/task_log/no_training/zero-shot/zero_shot.py \
#         --model_name "$MODEL" \
#         --base_url "$BASE_URL" \
#         --api_key "$API_KEY" \
#         --test_set_path "$JSONL_TEST_PATH" \
#         --prompt_key "$JSONL_PROMPT_KEY" \
#         --sample_num $SAMPLE_NUM \
#         --db_path_key "$DB_PATH_KEY" \
#         --ground_truth_key "$GROUND_TRUTH_KEY" \
#         --with_cot $WITH_COT
#     echo "模型 $MODEL (JSONL + CoT) 测试完成。"
#     echo ""
# done

# 测试2: WOCOT Parquet 文件
echo "测试2: WOCOT Parquet 文件 (非CoT模式)"
# for MODEL in "${MODEL_LIST[@]}"; do
# for idx in "${!MODEL_LIST[@]}"; do
#     MODEL="${MODEL_LIST[$idx]}"
#     API_KEY="${API_KEY_LIST[$idx]}"
    
#     echo "---------------------------------------------"
#     echo "正在测试模型: $MODEL (WOCOT Parquet)"
#     python /root/data1/projects/RL/DeepRetrieval/task_log/no_training/zero-shot/zero_shot.py \
#         --model_name "$MODEL" \
#         --base_url "$BASE_URL" \
#         --api_key "$API_KEY" \
#         --test_set_path "$WOCOT_TEST_PATH" \
#         --prompt_key "$PARQUET_PROMPT_KEY" \
#         --sample_num $SAMPLE_NUM \
#         --db_path_key "$DB_PATH_KEY" \
#         --output_root "$OUTPUT_ROOT" \
#         --ground_truth_key "$GROUND_TRUTH_KEY" \
#         --output_root "$OUTPUT_ROOT"
#     echo "模型 $MODEL (WOCOT Parquet) 测试完成。"
#     echo ""
# done

# 测试3: COT Parquet 文件
echo "测试3: COT Parquet 文件 (CoT模式)"
# 遍历索引
for idx in "${!MODEL_LIST[@]}"; do
    MODEL="${MODEL_LIST[$idx]}"
    API_KEY="${API_KEY_LIST[$idx]}"
    
    echo "---------------------------------------------"
    echo "正在测试模型: $MODEL (COT Parquet)"
    python /root/data1/projects/RL/DeepRetrieval/task_log/no_training/zero-shot/zero_shot.py \
        --model_name "$MODEL" \
        --base_url "$BASE_URL" \
        --api_key "$API_KEY" \
        --test_set_path "$COT_TEST_PATH" \
        --prompt_key "$PARQUET_PROMPT_KEY" \
        --sample_num $SAMPLE_NUM \
        --db_path_key "$DB_PATH_KEY" \
        --ground_truth_key "$GROUND_TRUTH_KEY" \
        --output_root "$OUTPUT_ROOT" \
        --failed_file_path /root/data1/projects/RL/DeepRetrieval/outputs/no_training/bird/zero-shot/claude-3-haiku-20240307/2025-09-29/wcot/test.messages.wcot.wcot.sample100_failed.jsonl \
        --with_cot 
    echo "模型 $MODEL (COT Parquet) 测试完成。"
    echo ""
done

echo "多模型批量测试完成！"
