`spider_cold_start-train_test.log`
- 问题：
    - [√] 2025.9.13 (问题已被解决)
        - nltk 缺少相关包，无法做 eval。然而 `per_device_eval_batch_size` 为 128 是，系统没有这种报错信息，反而在 batch 较小（比如 8）的时候能看到这个问题。
        - 即便装了 nltk 相关包，evalscope 也只有 `per_device_eval_batch_size` 较小时才工作。可能是一个 bug。（但目前不是重点，影响也不大）

