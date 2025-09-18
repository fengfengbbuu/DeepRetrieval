#!/bin/bash

########################################################################
# Zero-Shot Evaluator Test Script
# 用于验证zero_shot_evaluator.py的功能

# echo "=== Zero-Shot Evaluator Test Script ==="
# echo "Date: $(date)"
# echo ""

# # 设置环境
# echo "1. 激活conda环境..."
# conda activate swift
# echo ""

# # 设置输入文件路径
# INPUT_FILE="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot/gpt-3.5-turbo/2025-09-16/test.wcot.sample100_success.jsonl"

# echo "2. 检查输入文件是否存在..."
# if [ ! -f "$INPUT_FILE" ]; then
#     echo "错误: 输入文件不存在: $INPUT_FILE"
#     echo "请检查文件路径是否正确"
#     exit 1
# fi
# echo "输入文件存在: $INPUT_FILE"
# echo ""

# # 测试1: CoT模式评估
# echo "3. 测试CoT模式评估..."
# python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
#     --file_path "$INPUT_FILE" \
#     --response_key "api_result" \
#     --ground_truth_key "ground_truth" \
#     --db_path_key "db_path" \
#     --is_cot True

# echo ""
# echo "CoT模式评估完成！"
# echo ""

# # 测试2: 非CoT模式评估
# echo "4. 测试非CoT模式评估..."
# python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
#     --file_path "$INPUT_FILE" \
#     --response_key "api_result" \
#     --ground_truth_key "ground_truth" \
#     --db_path_key "db_path" \
#     --is_cot False

# echo ""
# echo "非CoT模式评估完成！"
# echo ""

# # 检查结果文件
# echo "5. 检查生成的结果文件..."
# echo "查找输出目录..."
# find /root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot/gpt-3.5-turbo/2025-09-16/analyze -name "*.csv" -type f 2>/dev/null | head -5
# find /root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot/gpt-3.5-turbo/2025-09-16/analyze -name "*.png" -type f 2>/dev/null | head -5

# echo ""
# echo "=== 测试完成 ==="
# echo "请检查生成的结果文件和可视化图表"

# # 显示帮助信息
# echo ""
# echo "6. 显示帮助信息..."
# python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py --help

########################################################################

# echo "=== Updated Format Verification Test ==="
# echo "Testing updated non-CoT format (now uses <answer> tags like CoT mode)"
# echo ""

# # 验证更新后的格式
# echo "1. 测试更新后的CoT模式..."
# eval "$(conda shell.bash hook)" && conda activate swift && python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
#     --file_path "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot/gpt-3.5-turbo/2025-09-17/wcot/test.messages.wcot.wcot.sample100_success.jsonl" \
#     --response_key "api_result" \
#     --ground_truth_key "ground_truth" \
#     --db_path_key "db_path" \
#     --is_cot

# echo ""
# echo "2. 测试更新后的Non-CoT模式..."
# eval "$(conda shell.bash hook)" && conda activate swift && python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
#     --file_path "/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot/gpt-3.5-turbo/2025-09-17/wcot/test.messages.wcot.wcot.sample100_success.jsonl" \
#     --response_key "api_result" \
#     --ground_truth_key "ground_truth" \
#     --db_path_key "db_path"

# echo ""
# echo "=== Format Update Verification Complete ==="
# echo ""

########################################################################


ROOT_DIR="/root/data1/projects/RL/DeepRetrieval/outputs/no_training/spider/zero-shot"
# MODEL_NAME_LST=("claude-3-haiku-20240307" "gpt-3.5-turbo" "gpt-4o-2024-11-20")
# MODEL_NAME_LST=("qwen2_5_1_5")
# MODEL_NAME_LST=("qwen2_5_05")
MODEL_NAME_LST=("claude-3-haiku-20240307" "gpt-3.5-turbo" "gpt-4o-2024-11-20" "claude-3-5-sonnet-latest" "qwen2_5_1_5" "qwen2_5_05")

for model_name in "${MODEL_NAME_LST[@]}"; do
    # 遍历所有 ROOT_DIR/model_name 下的 date dir
    for date_dir in "${ROOT_DIR}/${model_name}"/*; do
        # 要求 date 符合 yyyy-mm-dd 格式
        # 获取 date_dir 的名称
        date_dir_name=$(basename "$date_dir")
        echo "Processing date directory: $date_dir_name"
        if ! [[ "$date_dir_name" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            echo "Invalid date directory: $date_dir_name"
            continue
        fi

        for is_cot in True False; do
            # 处理 is_cot
            if [ "$is_cot" == "True" ]; then
                INPUT_FILE_DIR="${date_dir}/wcot"
            else
                INPUT_FILE_DIR="${date_dir}/wocot"
            fi

            # 遍历所有以 'success.jsonl' 结尾的文件
            input_file_lst=($(find "${INPUT_FILE_DIR}" -name "*_success.jsonl"))
            for input_file in "${input_file_lst[@]}"; do
                echo "====================================================================="
                echo "Processing file: $input_file"

                # 输出内容追加到 /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/close_llm.txt

                if [ "$is_cot" == "True" ]; then
                    python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
                        --file_path "$input_file" \
                        --response_key "api_result" \
                        --ground_truth_key "ground_truth" \
                        --db_path_key "db_path" \
                        --is_cot 2>&1 | tee -a /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/close_llm.txt

                else
                    python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/zero_shot_evaluator.py \
                        --file_path "$input_file" \
                        --response_key "api_result" \
                        --ground_truth_key "ground_truth" \
                        --db_path_key "db_path" 2>&1 | tee /root/data1/projects/RL/DeepRetrieval/task_log/analyze/no_training_analyze/close_llm.txt
                fi

                # 只处理一个文件
                break
                
            done
        done
    done
done
