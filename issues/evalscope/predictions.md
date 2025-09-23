# Enhancement

issue#1: 期望 predictions 的输出内容不单有 input, output，还有 question 这种信息。
- log:
    - 2025.9.22 尝试寻找解决方案。
        - `evaluate/evaluator.py` 中 `save_prediction_cache()` 方法调用，保存 prediction 结果。可以看到具体要存的信息是从 TaskState 中获取的，我想要的 question 可以放在 `metadata` 字段中。问题变成了如何在 cli 中指定 metadata 字段的信息？
        - 尝试修改 `record_to_sample()` 函数。为什么？其实 evalscope 的 `metadata` 设计的听完善的，至少在很多模块上都有定义，如果你全局搜索 `metadata`，会发现在 Sample，ModelOutput，TaskState 等类上都有定义，但缺少具体的应用场景。在这么多定义中，我认为 question 这样的 metadata 与 Sample 最相关，而要做到这一点，最好就是在 `record_to_sample()` 函数中实现。而我之所有这个需求，归根结底是不知道怎么自定义 metrics，所以希望 prediction 能有更多的返回信息，好让我写后处理代码。理论上 [Contribute Benchmark](https://evalscope.readthedocs.io/en/latest/advanced_guides/add_benchmark.html) 已经告诉用户该怎么做了，问题在于这个流程是否简洁明了，是否容易上手。因此如果想提这个 issue，可以从 docs 上入手——*“一个更简洁应用自己 metrics 的方式”*。
            - 再次之前，最根源的问题是，*“训练阶段的目标和验证阶段的目标不一致，是否正常？”*。我目前是 “合理的”，这好比在一个任务上做训练，然后适配到别的任务上。


issue#2: 期望能够有自定义的 metrics：[Contribute Benchmark](https://evalscope.readthedocs.io/en/latest/advanced_guides/add_benchmark.html) (这个流程走通，应该能实现目标)
- log:
    2025.9.22 从 `run.py` 开始梳理 evalscope 对数据集的处理方式。
        - 指定 `prompt_template`: 发现对于自定义的 dataset，最好还是要指定 `prompt_template` ，并且实现自己 dataset 的 adapter（不知道 hf 上那些 “标准” 的 dataset 在加载时是否不需要指定 prompt template，因为相关配置文件中已经写清楚了）。

# log
- 2025.9.22 TODO issue #1 和 #2 可以一块解决。流程是按照 Contribute Benchmark 设计自己的评估数据集以及 metrics，然后尝试在别的任务上也这样做，之后得出更简洁的适配方法，提出 issue。
