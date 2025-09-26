
# ROOT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wocot/test_100
# ROOT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wcot/test_500
# ROOT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wcot/test_100

# OUTPUT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wocot/test_100/draw
# OUTPUT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wcot/test_500/draw
# OUTPUT_DIR=/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wcot/test_100/draw

ROOT_DIR_LST=(
    # RL
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum_wocot/test_500 
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum_wocot/test_100 
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum/test_500 
    /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_sft10_1A6000_2epoch_32bs_4accum_wcot/test_500 
    # sft
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-090640/test_500 
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wcot/v0-20250917-141558/test_100 
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-082318/test_500
)

OUTPUT_DIR_LST=(
    # RL
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum_wocot/test_500/draw 
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum_wocot/test_100/draw 
    # /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_0_5_1A6000_1epoch_32bs_4accum/test_500/draw 
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-090640/test_500/draw 
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wcot/v0-20250917-141558/test_100/draw 
    # /root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_1_5b_1A6000_2ep_16bs_2accum_wocot/v1-20250921-082318/test_500/draw 
    /root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_sft10_1A6000_2epoch_32bs_4accum_wcot/test_500/draw
)


# 遍历 ROOT_DIR_LST 和 OUTPUT_DIR_LST
for i in {0..2}; do
    python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/draw/analyze_summary_data_improved.py \
        --root_dir ${ROOT_DIR_LST[$i]} \
        --output_dir ${OUTPUT_DIR_LST[$i]}
done

# python /root/data1/projects/RL/DeepRetrieval/task_log/analyze/draw/analyze_summary_data_improved.py \
#     --root_dir $ROOT_DIR \
#     --output_dir $OUTPUT_DIR
