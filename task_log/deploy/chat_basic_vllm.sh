#!/bin/bash

# This script runs the chat.py VLLM example with customizable parameters.

# --- VLLM Engine and Model Configuration ---
# The name or path of the model to use.
# Defaults to "meta-llama/Llama-3.2-1B-Instruct" in the Python script.
# MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct"
# MODEL_NAME=/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424/checkpoint-300
MODEL_NAME=/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wcot/v0-20250917-141558/checkpoint-100

# Number of GPUs to use for the model.
GPU_COUNT=1

# --- Sampling Parameters ---
# Maximum number of tokens to generate.
# MAX_TOKENS=1024
MAX_TOKENS=512

# The randomness of the output. Higher values lead to more creative responses.
TEMPERATURE=0.0

# Nucleus sampling parameter.
# A value of 1.0 considers all tokens; a lower value prunes the token list.
# TOP_P=0.9
TOP_P=1.0

# Top-k sampling parameter. A value of -1 disables it.
TOP_K=-1

# --- Optional Arguments ---
# Path to a custom chat template file (optional).
# Use this if you need a specific template not built into the model.
CHAT_TEMPLATE_PATH=""

# --- Script Execution ---
echo "Starting VLLM chat script with the following parameters:"
echo "  Model: $MODEL_NAME"
echo "  GPUs: $GPU_COUNT"
echo "  Max Tokens: $MAX_TOKENS"
echo "  Temperature: $TEMPERATURE"
echo "  Top-P: $TOP_P"

python3 /root/data1/projects/RL/DeepRetrieval/task_log/deploy/chat_basic_vllm.py \
  --model "$MODEL_NAME" \
  --tensor-parallel-size "$GPU_COUNT" \
  --max-tokens "$MAX_TOKENS" \
  --temperature "$TEMPERATURE" \
  --top-p "$TOP_P" \
  --top-k "$TOP_K"

# Example of how to use the optional chat template path.
# Uncomment the following lines if you need to specify a custom template.
# if [ -n "$CHAT_TEMPLATE_PATH" ]; then
#   echo "Using custom chat template from: $CHAT_TEMPLATE_PATH"
#   python3 chat.py \
#     --model "$MODEL_NAME" \
#     --tensor-parallel-size "$GPU_COUNT" \
#     --max-tokens "$MAX_TOKENS" \
#     --temperature "$TEMPERATURE" \
#     --top-p "$TOP_P" \
#     --top-k "$TOP_K" \
#     --chat-template-path "$CHAT_TEMPLATE_PATH"
# fi
