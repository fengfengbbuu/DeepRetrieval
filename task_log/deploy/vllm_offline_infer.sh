#!/bin/bash

# VLLM Offline Inference Test Script
# Date: 2025.9.19

# Activate conda environment
# source /opt/miniconda3/etc/profile.d/conda.sh
# conda activate swift

########################################################################
# # Set variables
# # VAL_MODEL_PATH="outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424/checkpoint-300"
# MODEL_PATH="outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424/checkpoint-300"

# WOCOT_VAL_FILE="code/data/sql/spider/test.messages.wocot.parquet"
# COT_VAL_FILE="code/data/sql/spider/test.messages.wcot.parquet"

# # OUTPUT_ROOT="task_log/deploy/outputs"
# OUTPUT_ROOT=$MODEL_PATH
# SCRIPT_PATH="task_log/deploy/vllm_offline_infer.py"

# # Create output directory
# mkdir -p $OUTPUT_ROOT

# echo "=== VLLM Offline Inference Test ==="
# echo "Model: $VAL_MODEL_PATH"
# echo "Script: $SCRIPT_PATH"
# echo "Output Root: $OUTPUT_ROOT"
# echo

# # Test 1: Small sample without CoT
# echo "=== Test 1: Without CoT (sample 3) ==="
# python $SCRIPT_PATH \
#     --model_name $MODEL_PATH \
#     --test_set_path $WOCOT_VAL_FILE \
#     --output_root $OUTPUT_ROOT \
#     --sample_num 3 \
#     --prompt_key prompt \
#     --db_path_key "extra_info.db_path" \
#     --ground_truth_key "reward_model.ground_truth.target" \
#     --temperature 0.0 \
#     --max_tokens 512

# echo
# echo "=== Test 1 Completed ==="
# echo

# # Test 2: Small sample with CoT
# echo "=== Test 2: With CoT (sample 3) ==="
# python $SCRIPT_PATH \
#     --model_name $VAL_MODEL_PATH \
#     --test_set_path $COT_VAL_FILE \
#     --output_root $OUTPUT_ROOT \
#     --sample_num 3 \
#     --prompt_key prompt \
#     --db_path_key "extra_info.db_path" \
#     --ground_truth_key "reward_model.ground_truth.target" \
#     --with_cot \
#     --temperature 0.0 \
#     --max_tokens 512

# echo
# echo "=== Test 2 Completed ==="
# echo

# # Test 3: Larger sample without CoT (uncomment to run)
# # echo "=== Test 3: Without CoT (sample 10) ==="
# # python $SCRIPT_PATH \
# #     --model_name $VAL_MODEL_PATH \
# #     --test_set_path $WOCOT_VAL_FILE \
# #     --output_root $OUTPUT_ROOT \
# #     --sample_num 10 \
# #     --prompt_key prompt \
# #     --db_path_key "extra_info.db_path" \
# #     --ground_truth_key "reward_model.ground_truth.target" \
# #     --temperature 0.0 \
# #     --max_tokens 512

# echo "=== All Tests Completed ==="
# echo "Check results in: $OUTPUT_ROOT"

########################################################################

WOCOT_VAL_FILE="code/data/sql/spider/test.messages.wocot.parquet"
COT_VAL_FILE="code/data/sql/spider/test.messages.wcot.parquet"
SCRIPT_PATH="task_log/deploy/vllm_offline_infer.py"
SAMPLE_NUM=100

# MODEL_ROOT=/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424

# sft
MODEL_ROOT_LST=(
    # qwen2.5-0.5b
    "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424" 
    "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-090640" 
    # qwen2.5-1.5b
    "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wcot/v0-20250917-141558" 
    "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-082318"
)

# WITH_COT=True

WITH_COT_LST=(
    # qwen2.5-0.5b 
    "True" 
    "False" 
    # qwen2.5-1.5b 
    "True" 
    "False" 
)

SAMPLE_NUM=500

# 遍历 MODEL_ROOT_LST 和 WITH_COT_LST 的组合
for idx in "${!MODEL_ROOT_LST[@]}"; do
    MODEL_ROOT="${MODEL_ROOT_LST[$idx]}"
    WITH_COT="${WITH_COT_LST[$idx]}"
    
    for CHECKPOINT in $MODEL_ROOT/checkpoint-*; do
        MODEL_PATH=$CHECKPOINT
        OUTPUT_ROOT=$MODEL_ROOT/test_${SAMPLE_NUM}
        
        # 如果 OUTPUT_ROOT 不存在，则创建
        if [ ! -d $OUTPUT_ROOT ]; then
            mkdir -p $OUTPUT_ROOT
        fi

        if [ "$WITH_COT" == "True" ]; then
            python $SCRIPT_PATH \
                --model_name $MODEL_PATH \
                --test_set_path $COT_VAL_FILE \
                --output_root $OUTPUT_ROOT \
                --sample_num $SAMPLE_NUM \
                --prompt_key prompt \
                --db_path_key "extra_info.db_path" \
                --ground_truth_key "reward_model.ground_truth.target" \
                --temperature 0.0 \
                --max_tokens 512 \
                --with_cot
        else
            python $SCRIPT_PATH \
                --model_name $MODEL_PATH \
                --test_set_path $WOCOT_VAL_FILE \
                --output_root $OUTPUT_ROOT \
                --sample_num $SAMPLE_NUM \
                --prompt_key prompt \
                --db_path_key "extra_info.db_path" \
                --ground_truth_key "reward_model.ground_truth.target" \
                --temperature 0.0 \
                --max_tokens 512 
        fi

        # 休息 5s
        sleep 5

    done
done

# RL
cd /root/data1/projects/RL/DeepRetrieval

MODEL_ROOT_LST=(
    # qwen2.5-0.5b 
    "/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum" 
    "/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum_wocot" 
    # qwen2.5-1.5b 
    # "/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-082318" 
    "/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wcot" 
    "/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wocot"
)

WITH_COT_LST=(
    # qwen2.5-0.5b 
    "True" 
    "False" 
    # qwen2.5-1.5b 
    "True" 
    "False" 
)

SAMPLE_NUM=500

# 遍历 MODEL_ROOT_LST 和 WITH_COT_LST 的组合
for idx in "${!MODEL_ROOT_LST[@]}"; do
    MODEL_ROOT="${MODEL_ROOT_LST[$idx]}"
    WITH_COT="${WITH_COT_LST[$idx]}"
    
    # for CHECKPOINT in $MODEL_ROOT/checkpoint-*; do
    for CHECKPOINT in $MODEL_ROOT/global_step_*; do
        MODEL_PATH=$CHECKPOINT/actor/huggingface
        OUTPUT_ROOT=$MODEL_ROOT/test_${SAMPLE_NUM}
        
        # 如果 OUTPUT_ROOT 不存在，则创建
        if [ ! -d $OUTPUT_ROOT ]; then
            mkdir -p $OUTPUT_ROOT
        fi

        # Extract model name from path for naming
        MODEL_NAME=$(basename $CHECKPOINT)
        
        # 如果 `$CHECKPOINT/actor` 目录下存在 `model_world_size*.pt` 文件，
        # 将其移动到 `MODEL_PATH` 中。
        if [ -d "$CHECKPOINT/actor" ]; then
            for ptfile in $CHECKPOINT/actor/model_world_size*.pt; do
                if [ -f "$ptfile" ]; then
                    mv "$ptfile" "$MODEL_PATH"/
                fi
            done
        fi

        if [ "$WITH_COT" == "True" ]; then
            python $SCRIPT_PATH \
                --model_name $MODEL_NAME \
                --model_path $MODEL_PATH \
                --test_set_path $COT_VAL_FILE \
                --output_root $OUTPUT_ROOT \
                --sample_num $SAMPLE_NUM \
                --prompt_key prompt \
                --db_path_key "extra_info.db_path" \
                --ground_truth_key "reward_model.ground_truth.target" \
                --temperature 0.0 \
                --max_tokens 512 \
                --with_cot
        else
            python $SCRIPT_PATH \
                --model_name $MODEL_NAME \
                --model_path $MODEL_PATH \
                --test_set_path $WOCOT_VAL_FILE \
                --output_root $OUTPUT_ROOT \
                --sample_num $SAMPLE_NUM \
                --prompt_key prompt \
                --db_path_key "extra_info.db_path" \
                --ground_truth_key "reward_model.ground_truth.target" \
                --temperature 0.0 \
                --max_tokens 512 
        fi

        # 休息 5s
        sleep 5

    done
done
