DATASET_TYPE=bird

PROJECT_NAME=${DATASET_TYPE}_cold_start

# MODEL_NAME=qwen2_5_05b
# MODEL_NAME=qwen2_5_1_5b     # 1.5b
# MODEL_NAME=train_test

# MODEL_PATH="/root/data3/Qwen.Qwen2.5-1.5B-Instruct"
# MODEL_PATH="/root/data3/Qwen.Qwen2.5-0.5B-Instruct"

# DATA_SAMPLE=800
# DATA_SAMPLE=32
# DATA_SAMPLE=320
# WITH_COT=False
# WITH_COT=True
# WITH_COT=True

# EXP_NAME=train_test_v1
# EXP_NAME=${MODEL_NAME}_1A6000_2ep_16bs_2accum
# EXP_NAME=${MODEL_NAME}_1A6000_1ep_16bs_2accum_sample800
# EXP_NAME=${MODEL_NAME}_1A6000_1ep_16bs_2accum_sample160
# EXP_NAME=${MODEL_NAME}_1A6000_2ep_16bs_2accum_wcot
# EXP_NAME=${MODEL_NAME}_1A6000_2ep_16bs_2accum_wocot

# 如果 data sample 存在且大于 0，则使用部分数据进行测试
if [ -n "$DATA_SAMPLE" ] && [ "$DATA_SAMPLE" -gt 0 ]; then
    if [ "$WITH_COT" == "False" ]; then
        if [ "$DATASET_TYPE" == "spider" ]; then
            TRAIN_DATASET_PATH="/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/spider/split/train_4312.wocot.jsonl#${DATA_SAMPLE}"
            VAL_DATASET_NAME="dev_862.wocot"
        else
            TRAIN_DATASET_PATH="/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/split/train_3767.wocot.jsonl#${DATA_SAMPLE}"
            VAL_DATASET_NAME="dev_128.wocot"
        fi
    else
        if [ "$DATASET_TYPE" == "spider" ]; then
            TRAIN_DATASET_PATH="/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/spider/split/train_4312.jsonl#${DATA_SAMPLE}"
            VAL_DATASET_NAME="dev_862"
        else
            TRAIN_DATASET_PATH="/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/split/train_3767.jsonl#${DATA_SAMPLE}"
            VAL_DATASET_NAME="dev_128"
        fi
    fi
    echo "Using a subset of the dataset with ${DATA_SAMPLE} samples for testing."
else
    if [ "$WITH_COT" == "False" ]; then
        if [ "$DATASET_TYPE" == "spider" ]; then
            TRAIN_DATASET_PATH='/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/spider/split/train_4312.wocot.jsonl'
            VAL_DATASET_NAME="dev_862.wocot"
        else
            TRAIN_DATASET_PATH='/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/split/train_3767.wocot.jsonl'
            VAL_DATASET_NAME="dev_128.wocot"
        fi
    else
        if [ "$DATASET_TYPE" == "spider" ]; then
            TRAIN_DATASET_PATH='/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/spider/split/train_4312.jsonl'
            VAL_DATASET_NAME="dev_862"
        else
            TRAIN_DATASET_PATH='/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/bird/split/train_3767.jsonl'
            VAL_DATASET_NAME="dev_128"
        fi
    fi
fi

TRAIN_TYPE=full
OUTPUT_DIR=/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift

MODEL_NAME_LST=(
    qwen2_5_0_5b 
    qwen2_5_0_5b 
    qwen2_5_1_5b 
    qwen2_5_1_5b 
    # train_test
)
MODEL_PATH_LST=(
    "/root/data3/Qwen.Qwen2.5-0.5B-Instruct" 
    "/root/data3/Qwen.Qwen2.5-0.5B-Instruct" 
    "/root/data3/Qwen.Qwen2.5-1.5B-Instruct" 
    "/root/data3/Qwen.Qwen2.5-1.5B-Instruct" 
    # "/root/data3/Qwen.Qwen2.5-0.5B-Instruct"
)
WITH_COT_LST=(
    # qwen2.5-0.5b
    "True"
    "False"
    # qwen2.5-1.5b
    "True"
    "False"
)
EPOCH=1
GPU_DEVICE=1A6000

for MODEL_NAME in "${MODEL_NAME_LST[@]}"; do
    for MODEL_PATH in "${MODEL_PATH_LST[@]}"; do
        for WITH_COT in "${WITH_COT_LST[@]}"; do
            # 判断有没有 data sample
            if [ -n "$DATA_SAMPLE" ] && [ "$DATA_SAMPLE" -gt 0 ]; then
                # 判断 WITH_COT 是否为 True
                if [ "$WITH_COT" == "True" ]; then
                    EXP_NAME=${MODEL_NAME}_${GPU_DEVICE}_${EPOCH}ep_16bs_2accum_wcot_sample${DATA_SAMPLE}
                else
                    EXP_NAME=${MODEL_NAME}_${GPU_DEVICE}_${EPOCH}ep_16bs_2accum_wocot_sample${DATA_SAMPLE}
                fi
            else
                if [ "$WITH_COT" == "True" ]; then
                    EXP_NAME=${MODEL_NAME}_${GPU_DEVICE}_${EPOCH}ep_16bs_2accum_wcot
                else
                    EXP_NAME=${MODEL_NAME}_${GPU_DEVICE}_${EPOCH}ep_16bs_2accum_wocot
                fi
            fi

            # 训练
            CUDA_VISIBLE_DEVICES=0,1,2,3 \
            swift sft \
                --model $MODEL_PATH \
                --model_type qwen2_5 \
                --train_type $TRAIN_TYPE \
                --dataset $TRAIN_DATASET_PATH \
                --columns '{"response": "re", "answer": "an"}' \
                --torch_dtype bfloat16 \
                --num_train_epochs $EPOCH \
                --per_device_train_batch_size 8 \
                --per_device_eval_batch_size 8 \
                --learning_rate 1e-4 \
                --gradient_accumulation_steps 2 \
                --eval_strategy "steps" \
                --eval_steps 40 \
                --eval_use_evalscope \
                --eval_dataset general_qa \
                --eval_dataset_args "{\"general_qa\": {\"local_path\": \"/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/${DATASET_TYPE}/split\", \"subset_list\": [\"${VAL_DATASET_NAME}\"]}}" \
                --eval_generation_config '{"max_tokens": 512, "temperature": 0}' \
                --eval_limit 128 \
                --extra_eval_args '{"ignore_errors": true}' \
                --save_steps 40 \
                --save_total_limit 100 \
                --logging_steps 1 \
                --max_length 2048 \
                --max_new_tokens 512 \
                --truncation_strategy delete \
                --output_dir $OUTPUT_DIR/$PROJECT_NAME/$EXP_NAME \
                --logging_dir $OUTPUT_DIR/tensorboard/$PROJECT_NAME/$EXP_NAME \
                --warmup_ratio 0.05 \
                --dataloader_num_workers 4 \
                --model_author swift \
                --model_name $MODEL_NAME 2>&1 | tee /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/exp_log/$PROJECT_NAME-$EXP_NAME.log

            # 休息 10s
            sleep 10
        done
    done
done

# TODO generation config 不会写，不了解模型 geneation 的过程。
