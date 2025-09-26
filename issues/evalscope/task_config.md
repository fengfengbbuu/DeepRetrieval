# 问题

- [...] 问题描述：用 ms-swift 的 [Evaluation During Training](https://swift.readthedocs.io/en/latest/Instruction/Evaluation.html#evaluation-during-training) 参数。evalscope 的主流程 `evaluate_model()` 没能成功以 yaml 形式导出 task config 信息。
- 原因：出在 `TaskConfig` 类的 `to_dict()` 方法上，该方法没有考虑 key-value 对儿中，value 为 class 的情况。
- 代码修正：完善 `to_dict()` 代码逻辑后，task config 信息能成功导出。
- 后续：其实也可能是 ms-swift 传参不规范，一般不会直接传一个没有经过序列化的 class。
    - 确实是 ms-swift 传参不规范， [evalscope_model_parameters](https://evalscope.readthedocs.io/en/latest/get_started/parameters.html#model-parameters) 中提及 `--model-args` 最好是 json string，然而 `_evalscope_eval()` 穿的参数是 python dict。
- log
    - 2025.9.21 给 evalscope 官方提了 issue
