"""改变验证集格式，适应 ms-swift 和 evalscope"""

import json

def to_qa_format(data: dict):
    """改成 query response 格式。"""
    query = data['messages'][0]['content'] + '\n\n' + data['messages'][1]['content']
    response = data['messages'][2]['content']
    return {
        "query": query,
        "response": response
    }


def add_loss_field(data: dict):
    """为 assistant role 添加 loss 字段。"""
    for message in data['messages']:
        if message['role'] == 'assistant':
            message['loss'] = True
    return {
        "messages": data['messages']
    }

if __name__ == "__main__":
    input_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/split/dev_862.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/split/dev_862.qa.jsonl"
    output_file = "/root/data1/projects/RL/DeepRetrieval/outputs/llm_response/split/dev_862_loss.jsonl"

    with open(input_file, "r") as fr, open(output_file, "w") as fw:
        for line in fr:
            data = json.loads(line)
            # qa_data = to_qa_format(data)
            # fw.write(json.dumps(qa_data) + "\n")
            new_data = add_loss_field(data)
            fw.write(json.dumps(new_data) + "\n")
