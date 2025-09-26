# Summary Data Analysis Tool

## 功能描述

这个工具用于分析训练过程中生成的summary CSV文件，并生成各种统计图表。支持两种路径模式：`global_step_` 和 `checkpoint-`。

## 文件说明

- `analyze_summary_data.py`: 基础版本的分析脚本
- `analyze_summary_data_improved.py`: 改进版本的分析脚本（推荐使用）

## 使用方法

### 基本用法

```bash
python analyze_summary_data_improved.py --root_dir <ROOT_DIR> --output_dir <OUTPUT_DIR>
```

### 参数说明

- `--root_dir`: 根目录路径，必须指定
- `--output_dir`: 输出目录路径，必须指定。如果目录不存在会自动创建

### 示例

```bash
python analyze_summary_data_improved.py \
  --root_dir '/path/to/your/experiment/results' \
  --output_dir '/path/to/output/directory'
```

## 输入文件要求

脚本会自动查找符合以下路径模式的文件：

### 模式1: global_step_
```
{ROOT_DIR}/global_step_{step_num}/{date}/{cot_ncot}/analyze/*summary*.csv
```

### 模式2: checkpoint-
```
{ROOT_DIR}/checkpoint-{step_num}/{date}/{cot_ncot}/analyze/*summary*.csv
```

其中：
- `{ROOT_DIR}`: 根目录
- `{step_num}`: 训练步数（整数）
- `{date}`: 日期，格式为 'yyyy-mm-dd'
- `{cot_ncot}`: CoT类型，只能是 'wcot' 或 'wocot'
- `*summary*.csv`: 匹配包含"summary"的CSV文件

## 输出文件

脚本会在输出目录中生成以下文件：

### 图表文件
- `{Metric}_trend.png`: 各指标随训练步数的变化趋势图
- `key_metrics_comparison.png`: 关键指标对比图
- `metrics_heatmap.png`: 指标热力图
- `metrics_distribution.png`: 指标分布箱线图
- `step_type_comparison.png`: 不同step_type的对比图（当存在多种step_type时）

### 数据文件
- `combined_data.csv`: 合并后的原始数据
- `analysis_summary.txt`: 数据分析摘要报告

## 环境要求

- Python 3.6+
- pandas
- matplotlib
- seaborn
- numpy

## 注意事项

1. 确保在swift环境中运行脚本
2. 脚本会自动处理中文字体显示问题
3. 如果某些图表生成失败，脚本会继续执行其他部分
4. 输出目录如果不存在会自动创建
5. 支持同时处理global_step_和checkpoint-两种路径模式

## 测试示例

### 测试用例1 (global_step_模式)
```bash
python analyze_summary_data_improved.py \
  --root_dir '/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wocot/test_500' \
  --output_dir '/root/data1/projects/RL/DeepRetrieval/code/checkpoints/spider/qwen2_5_1_5_1A6000_2epoch_32bs_4accum_wocot/test_500/draw'
```

### 测试用例2 (checkpoint-模式)
```bash
python analyze_summary_data_improved.py \
  --root_dir '/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424/test_500' \
  --output_dir '/root/data1/projects/RL/DeepRetrieval/outputs/ms-swift/spider_cold_start/qwen2_5_05b_1A6000_2ep_16bs_2accum/v0-20250914-133424/test_500/draw'
```

## 更新日志

### v2.0 (2025-09-25)
- 新增支持 `checkpoint-` 路径模式
- 增强图表功能，支持不同step_type的对比
- 改进数据处理逻辑，添加step_type元数据
- 优化热力图显示，支持多维度数据展示
