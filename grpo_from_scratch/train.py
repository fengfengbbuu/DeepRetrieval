from transformers import AutoModelForCausalLM, AutoModel, AutoModelForSequenceClassification, AutoTokenizer, PreTrainedModel
from dataclasses import dataclass
from typing import Optional, Union, Tuple
import random
import torch
import torch.nn.functional as F
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter
from typing import Callable, Dict, List, Optional, Tuple, Union, Any
from copy import deepcopy
from datasets import load_dataset
from reward_func import *
import os
# os.environ['CUDA_VISIBLE_DEVICES'] = '4'


class GSM8KDataset(Dataset):
    def __init__(self, data_path, tokenizer):
        
        self.tokenizer = tokenizer
        data = load_dataset(data_path)
        self.data = data['train']

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        sample = self.data[index]
        # prompt = self.tokenizer.apply_chat_template(sample['prompt'], tokenize=False, add_generation_prompt=True)
        answer = sample['answer_only']
        # prompt = sample['question_zh-cn']
        prompt = sample['question_zh']
        return {'prompt': prompt, 'answer': answer}


@dataclass
class Samples:
    prompt_response_ids: torch.Tensor
    response_ids: torch.Tensor
    prompt: Any
    answer: Any
    attention_mask: Optional[torch.LongTensor]
    action_mask: Optional[torch.BoolTensor]
    num_actions: Union[int, torch.Tensor]
    response_length: int


class GRPOArguments:
    
    output_dir = './output'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    lr = 0.000001
    save_steps = 100
    epoch = 1               # （训练总轮数）
    num_generations = 4 # 组内样本数     （针对一个输入，模型生成的样本数量（即回复数量））
    max_prompt_length = 256 # 最大输入长度
    max_generate_length = 256 # 最大输出长度
    reward_weights : List[float] = None # 奖励的权重（多个奖励函数）
    beta = 0.0 # KL散度的系数，为0则忽略KL散度，即不使用参考模型
    clip_eps = 0.2
    gradient_accumulation_steps = 2 # 梯度累加    （累计 2 个批次（batch）的梯度后再进行一次参数更新）
    num_iterations = 1 # 采样一次样本训练模型轮数      （对同一批采样的样本（即通过 `num_generations` 生成的样本）进行训练的迭代次数。RL 中，采样样本成本较高（需要模型生成），因此会重复利用进行多次训练）
    batch_size = 3          #（模型更新时，使用的样本数量）

class GRPOTrainer:
    def __init__(self,
        model = None,
        reward_funcs: Union[List[str], List[Callable]] = None,
        args = None,
        train_dataset: Optional[Union[Dataset]] = None,
        eval_dataset: Optional[Union[Dataset]] = None,
        tokenizer = None,
        reward_tokenizers = None):

        self.args = args
        # 加载模型
        if isinstance(model, str):
            model = AutoModelForCausalLM.from_pretrained(model)
        self.model = model.to(self.args.device)
        
        # 是否使用参考模型
        self.ref_model = None
        if self.args.beta != 0.0:
            self.ref_model = deepcopy(model)
            self.ref_model.eval()

        if isinstance(tokenizer, str):
            tokenizer = AutoTokenizer.from_pretrained(tokenizer)

        self.tokenizer = self.get_tokenizer(tokenizer)

        if isinstance(reward_funcs, str):
            reward_funcs = [reward_funcs]
        
        for i, reward_func in enumerate(reward_funcs):
            # 如果奖励函数为字符串，表示使用的是奖励模型，则加载模型
            if isinstance(reward_func, str):
                reward_funcs[i] = AutoModelForSequenceClassification.from_pretrained(
                    reward_func, num_labels=1).to(self.args.device)
        
        self.reward_funcs = reward_funcs
        
        if reward_tokenizers is None:
            reward_tokenizers = [None] * len(reward_funcs)
            
        elif isinstance(reward_tokenizers, str):
            reward_tokenizers = [reward_tokenizers]
            
        else:
            if len(reward_tokenizers) != len(reward_funcs):
                raise ValueError("Length of reward_tokenizers must be equal to the number of reward_funcs.")
            
        for i, (reward_tokenizer, reward_func) in enumerate(zip(reward_tokenizers, reward_funcs)):
            if isinstance(reward_func, PreTrainedModel):
                if reward_tokenizer is None:
                    reward_tokenizer = AutoTokenizer.from_pretrained(reward_func.config._name_or_path)
                if reward_tokenizer.pad_token_id is None:
                    reward_tokenizer.pad_token = reward_tokenizer.eos_token
                
                reward_func.config.pad_token_id = reward_tokenizer.pad_token_id
                reward_tokenizers[i] = reward_tokenizer
        self.reward_tokenizers = reward_tokenizers
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.args.lr)
        self.train_dataset = train_dataset
        self.eval_dataset = eval_dataset
        
        # 缓存已经生成的数据的一个批次的数据，可供模型多次训练迭代，无需重新生成
        self.input_buffer = [None] * self.args.gradient_accumulation_steps
        
        # 模型更新的次数
        self.update_steps = 0 

    def get_tokenizer(self, tokenizer):
        tokenizer.padding_side = "left"
        return tokenizer
    
    # 生成样本，以组为单位
    def generate_samples(self, inputs):     # return shape: (bs,)
        samples_list = []
        self.model.eval()
        prompts = [prompt for prompt in inputs['prompt']]
        answers = [None] * len(prompts)
        
        if 'answer' in inputs:
            answers = [answer for answer in inputs['answer']]
        
        max_length = self.args.max_generate_length + self.args.max_prompt_length
        for prompt, answer in zip(prompts, answers):
            # 应用聊天模板，加入系统提示词
            input_text = self.tokenizer.apply_chat_template(
                [{"role": "system", 'content': SYSTEM_PROMPT}, {"role": "user", 'content': prompt}], 
                add_generation_prompt=True, tokenize=False
            )
            
            # 生成一个group的输入数据
            inputs = self.tokenizer(
                [input_text] * self.args.num_generations, 
                padding='max_length', 
                max_length=self.args.max_prompt_length, 
                truncation=True, 
                return_tensors='pt'
            )
            prompt_ids = inputs['input_ids']        # shape: (num_generations, max_prompt_length)
            with torch.no_grad():
                prompt_response_ids = self.model.generate(**inputs.to(self.args.device), 
                                    max_new_tokens = self.args.max_generate_length,
                                    temperature=0.9,
                                    top_p = 1,
                                    top_k = 50)         # 看一下返回类型的 shape。生成的内容不够 max_new_tokens，会自动做 padding 吗？（不会自动做 padding）

            print(f"prompt_response_size(1) = {prompt_response_ids.size(1)}; max_length = {max_length}.")
            if prompt_response_ids.size(1) != max_length:   # 确实不等，不会做 padding。
                print("Warning: prompt_response_ids.size(1) != max_length.")
            if prompt_response_ids.size(1) >= max_length:
                prompt_response_ids = prompt_response_ids[:, :max_length]
            else:       # 我认为 prompt_response_ids.size(1) == max_length. `else` 不会执行（并不相等，似乎没有做 padding）
                prompt_response_ids = torch.cat([           # 手动 padding
                    prompt_response_ids, 
                    torch.full(
                        (prompt_response_ids.size(0), max_length - prompt_response_ids.size(1)), 
                        fill_value=self.tokenizer.pad_token_id, device=prompt_response_ids.device
                    )
                ], dim=1)

            # 如果是 Agent，这里的 mask 可能会复杂很多。首先需要对 generated tokens 做 decode，然后匹配有用的片段，确定其位置，之后再 tokenize，再做各种 mask。
            attention_mask = (prompt_response_ids.ne(self.tokenizer.pad_token_id)).to(dtype=torch.long)
            response_ids = prompt_response_ids[:, prompt_ids.size(1):]
            action_mask = (response_ids.ne(self.tokenizer.eos_token_id) & response_ids.ne(self.tokenizer.pad_token_id)).to(dtype=torch.long)
        
            print(f"action_mask.size(1) = {action_mask.size(1)}.")          # 我认为是一个定值，且等于 `max_generate_length`（确实是这样的）
            # 存储的是一个group的数据
            samples = Samples(
                prompt_response_ids=prompt_response_ids,        # 整个 prompt（含输入和输出）的 token ids. shape: (num_generations, max_length)
                response_ids=response_ids,                      # 模型输出结果的 token ids. shape: (num_generations, max_generate_length)
                prompt = prompt,                                # 模型输入内容（str）.
                answer = answer,                                # 正确答案
                attention_mask=attention_mask,                  # 整个输入输出的掩码. shape: (num_generations, max_length)
                action_mask=action_mask,                        # 输出部分的掩码. shape: (num_generations, max_generate_length)
                num_actions=action_mask.size(1),                # 为什么会有 num_actions？为什么叫这个名字？这里取 size(1) 不就是个固定的值了？（num actions 直译是“动作数量”，符合 RL 对该任务的建模——把文本生成任务的每个 token 看作一个 action）
                response_length=action_mask.float().sum(dim=-1)         # 不考虑 response 中 padding 和 eos 的长度.
            )
            samples_list.append(samples)

        return samples_list
    
    # 生成经验(优势、token的概率分布)
    def generate_experiences(self, inputs):
        
        self.model.eval()
        samples_list = self.generate_samples(inputs)    # shape: (bs,) .(batch_size, num_generations)
        
        batch_prompt_response_ids = []
        batch_attention_mask = []
        batch_action_mask = []
        batch_advantages = []
        batch_old_action_log_probs = []
        batch_ref_action_log_probs = []
        
        for samples in samples_list:
            prompt_response_ids = samples.prompt_response_ids # shape: (num_generations, seq_len)
            response_ids = samples.response_ids # shape: (num_generations, seq_len)
            answer = samples.answer
            attention_mask = samples.attention_mask # shape: (num_generations, seq_len)
            action_mask = samples.action_mask # shape: (num_generations, seq_len)
            num_actions = samples.num_actions
            prompt = samples.prompt
            batch_prompt_response_ids.append(prompt_response_ids)
            batch_attention_mask.append(attention_mask)
            batch_action_mask.append(action_mask)
            
            with torch.no_grad():
                # 计算策略模型输出token的概率
                old_action_log_probs = self.get_action_log_probs(self.model, prompt_response_ids, attention_mask, num_actions)
                batch_old_action_log_probs.append(old_action_log_probs)
                
                # 是否使用参考模型
                if self.ref_model:
                    #计算参考模型输出token的概率
                    ref_action_log_probs = self.get_action_log_probs(self.ref_model, prompt_response_ids, attention_mask, num_actions)
                    batch_ref_action_log_probs.append(ref_action_log_probs)
                
                # 存储各个奖励函数在一个group内各个响应的奖励
                rewards_per_func = torch.zeros(len(self.reward_funcs), self.args.num_generations, device=self.args.device)
                
                # 将输出转换成文本
                response_texts = self.tokenizer.batch_decode(response_ids, skip_special_tokens=True)
                prompt_texts = [prompt] * len(response_texts)
                prompt_response_texts = [prompt + response for prompt, response in zip(prompt_texts, response_texts)]
                
                for i, (reward_func, reward_tokenizer) in enumerate(
                    zip(self.reward_funcs, self.reward_tokenizers)
                ):
                    if isinstance(reward_func, PreTrainedModel):
                        with torch.inference_mode():
                            reward_model_inputs = reward_tokenizer(prompt_response_texts, return_tensors="pt", padding=True)
                            rewards_per_func[i] = reward_func(**reward_model_inputs.to(self.args.device)).logits.squeeze(-1)
                    
                    else:
                        answers = [answer] * len(prompt_texts)
                        output_reward_func = reward_func(prompts=prompt_texts, responses=response_texts, answers=answers)
                        output_reward_func = [reward if reward is not None else torch.nan for reward in output_reward_func]
                        rewards_per_func[i] = torch.tensor(output_reward_func, dtype=torch.float32, device=self.args.device)
                
                # rewards_per_func: [num_funcs, num_generations]
                if not self.args.reward_weights:
                    self.args.reward_weights = [1.0] * len(self.reward_funcs)
                if len(self.args.reward_weights) != len(self.reward_funcs):
                    raise ValueError("The number of reward weights must be equal to the number of reward functions.")
                # 乘以各个奖励函数的权重
                rewards = rewards_per_func * torch.tensor(self.args.reward_weights, dtype=torch.float32, device=rewards_per_func.device).unsqueeze(1)
                
                # rewards: [num_funcs, num_generations]
                rewards = rewards.sum(dim=0) # shape: [num_generations]
                print(f'rewards: {rewards}')
                mean_group_rewards = rewards.mean()
                std_group_rewards = rewards.std()
                
                # GRPO的优势是句子粒度的，而非token粒度的
                advantages = (rewards - mean_group_rewards) / (std_group_rewards + 1e-8) # shape: [num_generations] （每个采样样本相对于组内样本的优势）
                batch_advantages.append(advantages)
        
               
        return {
            "prompt_response_ids": torch.cat(batch_prompt_response_ids, dim=0),     # shape: (bs * ng, max_length)
            "attention_mask": torch.cat(batch_attention_mask, dim=0),               # shape: (bs * ng, max_length)
            "action_mask": torch.cat(batch_action_mask, dim=0),                     # shape: (bs * ng, max_gen)
            "old_action_log_probs": torch.cat(batch_old_action_log_probs, dim=0),   # shape: (bs * ng, num_actions)
            "ref_action_log_probs": torch.cat(batch_ref_action_log_probs, dim=0) if self.ref_model else None,
            "advantages": torch.cat(batch_advantages, dim=0),                       # shape: (bs,)
        }
    
    def compute_loss(self, model, inputs):
        
        prompt_response_ids = inputs['prompt_response_ids']     # prompt + response 的 token ids. shape: (bs * ng, max_length)
        attention_mask = inputs['attention_mask']               # 基于 prompt_response_ids mask 掉 pad token. shape: (bs * ng, max_length)
        action_mask = inputs['action_mask']                     # 基于 response，mask 掉 pad token 和 eos tokenshape: (bs * ng, max_generate_length)
        num_actions = action_mask.size(1)                       # 等于 `max_generate_length`
        print(f"Compute loss, prompt_response_ids.shape = {prompt_response_ids.shape}")
        action_log_probs = self.get_action_log_probs(model, prompt_response_ids, attention_mask, num_actions)
        
        if self.args.beta != 0.0:       # TODO ref 模型的作用（作用：限制更新幅度，防止模型畸变）
            
            ref_action_log_probs = inputs['ref_action_log_probs']
            log_ratio = ref_action_log_probs - action_log_probs 
            log_ratio = log_ratio * action_mask
            
            # k3: log_ratio.exp() - 1 - log_ratio
            k3 = log_ratio.exp() - 1 - log_ratio        # TODO 通过 k3 估计计算 KL 散度。
        
        advantages = inputs['advantages']
        
        old_action_log_probs = inputs['old_action_log_probs'] if self.args.num_iterations > 1 else action_log_probs.detach() # 为什么 detach()？（detach() 将张量从计算图中分离，使其成为一个常数。因为 action_log_probs 是前向传播的结果，与模型参数存在一张计算图中，如果不 detach，backward 时系统会计算其对模型参数的梯度）
        # （GRPO 优化目标）
        coef_1 = torch.exp(action_log_probs - old_action_log_probs) # 重要性采样 shape: [batch_size * num_generations, num_actions]
        coef_2 = torch.clamp(coef_1, 1 - self.args.clip_eps, 1 + self.args.clip_eps)        # TODO 剪辑权重：限制在 [1-clip_eps, 1+clip_eps] 范围内，避免权重过大导致梯度爆炸
        per_token_loss1 = coef_1 * advantages.unsqueeze(1)      # 一个序列中每个token的优势是一样的
        per_token_loss2 = coef_2 * advantages.unsqueeze(1)
        per_token_loss = -torch.min(per_token_loss1, per_token_loss2)   # torch.min(a, b) 逐元素比较 a, b 张量中的最小值。
        per_token_loss = per_token_loss * action_mask

        if self.args.beta != 0.0:
            per_token_loss = per_token_loss + self.args.beta * k3
        
        loss = per_token_loss.sum(dim=1) / action_mask.sum(dim=1) # shape: [batch_size * num_generations]
        loss = loss.mean()
        
        # loss = per_token_loss.sum() / action_mask.sum()
        
        return loss


    def get_action_log_probs(self, model, input_ids, attention_mask, num_actions):
        """只取 generation 部分的 log prob"""
        # 计算策略模型输出token的概率
        output = model(input_ids, attention_mask=attention_mask)            # 这里的 `model()` 和之前的 `model.generate()` 是有区别的。`model()` 是执行前向传播，返回模型对输入的每个 token 的概率分布预测，而 `model.generate()` 是在前向传播的基础上，增加了“自回归逻辑生成”。
        logits = output.logits
        log_probs = F.log_softmax(logits[:, :-1, :], dim=-1)        # 这里 `logits[:, :-1, :]` 排除最后一个位置的 logits（第 0 个位置的 logits 用于预测第 1 个位置的 token，最后一个位置的 logits 用于预测最后 + 1 个位置的 token，然而并不存在）
        log_probs_labels = log_probs.gather(dim=-1, index=input_ids[:, 1:].unsqueeze(-1))       # shape: (ng, sq - 1, 1)
        action_log_probs = log_probs_labels.squeeze(-1)[:, -num_actions:]       # shape: (ng, num_actions)
        return action_log_probs

    
    
    def train_step(self, model, inputs, optimizer, step):       # 更新肯定是按 batch 更新，inputs 第一个维度肯定是 batch_size
        model.train()
        # scaler = torch.amp.GradScaler()
        # with torch.amp.autocast(device_type='cuda'):
        loss = self.compute_loss(model, inputs)
        loss = loss / self.args.gradient_accumulation_steps
        # loss = scaler.scale(loss)
        loss.backward()
        if (step + 1) % self.args.gradient_accumulation_steps == 0:
            
            optimizer.step()
            optimizer.zero_grad()
            # scaler.unscale_(optimizer)
            # scaler.step(optimizer)
            # scaler.update()
        
            writer.add_scalar("grpo_loss", loss.item(), self.update_steps)
            print(f"step: {self.update_steps}/{self.global_steps}  grpo_loss: {loss.item():.8f}")
        torch.cuda.empty_cache()                    # TODO 通常会清空什么？

    def train(self):
        self.global_steps = self.args.num_iterations * self.args.epoch * len(self.train_dataset) // (self.args.batch_size * self.args.gradient_accumulation_steps)
        for _ in range(self.args.epoch):
            
            dataloader = DataLoader(self.train_dataset, batch_size=self.args.batch_size, shuffle=True)
            for idx, batch in enumerate(dataloader):
                
                inputs = self.generate_experiences(batch)           # dict
                self.input_buffer[idx % self.args.gradient_accumulation_steps] = inputs
                if (idx + 1) % self.args.gradient_accumulation_steps == 0:

                    for _ in range(self.args.num_iterations):
                        for step, inputs in enumerate(self.input_buffer):
                            self.train_step(self.model, inputs, self.optimizer, step)

                        self.update_steps += 1
                        if self.update_steps % self.args.save_steps == 0:
                            self.model.save_pretrained(self.args.output_dir + f'/checkpoint_{self.update_steps}')
                            self.tokenizer.save_pretrained(self.args.output_dir + f'/checkpoint_{self.update_steps}')

                del inputs

    def save_model(self):
        self.model.save_pretrained(self.args.output_dir)
        self.tokenizer.save_pretrained(self.args.output_dir)           

if __name__ == "__main__":
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    
    SYSTEM_PROMPT = """
按照如下格式回答问题：
<think>
你的思考过程
</think>
<answer>
你的回答
</answer>
"""
    
    args = GRPOArguments()
    
    writer = SummaryWriter('./runs/9m5d')
    # 策略模型
    MODEL_PATH = "/root/data3/Qwen.Qwen2.5-0.5B-Instruct"
    # tokenizer = AutoTokenizer.from_pretrained('/home/user/Downloads/Qwen2.5-1.5B-Instruct')
    # model = AutoModelForCausalLM.from_pretrained('/home/user/Downloads/Qwen2.5-1.5B-Instruct')
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
    # 奖励函数
    # reward_model = '/home/user/Downloads/reward-model-deberta-v3-large-v2'
    # reward_tokenizer = AutoTokenizer.from_pretrained('/home/user/Downloads/reward-model-deberta-v3-large-v2')

    # prompts_dataset = GSM8KDataset('/home/user/wyf/deepseek_learn/gsm8k_chinese', tokenizer)
    prompts_dataset = GSM8KDataset('/root/data1/datasets/meta-math.GSM8K_zh', tokenizer)

    trainer = GRPOTrainer(model=model,
                          reward_funcs = [correctness_reward, digit_reward, hard_format_reward, mark_reward],
                          args=args,
                          train_dataset=prompts_dataset,
                          tokenizer=tokenizer)
    trainer.train()
    trainer.save_model()


# 记录下时间：steps: 0/1465 （23:37 开始）（9m4d） events.out.tfevents.1757000217.28116312b940.55942.0
# 记录下时间：steps: 0/1465 （22:47 开始）（9m5d） events.out.tfevents.1757083687.28116312b940.31178.0
