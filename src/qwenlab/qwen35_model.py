"""Qwen3.5 text decision adapter; immutable older experiments are not patched."""
from pathlib import Path
from qwenlab.common import ROOT
from qwenlab import financial_actions_prompt as prompt

MODEL=ROOT/'models/Qwen3.5-0.8B'
TARGETS=('q_proj','v_proj','in_proj_qkv','in_proj_z')


def encode(tokenizer,row,task='action',target=None):
    messages,keys=prompt.messages(row,task)
    ids=[tokenizer.encode(chr(65+i),add_special_tokens=False) for i in range(len(keys))]
    if any(len(x)!=1 for x in ids):raise ValueError('Candidate must be one token')
    text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    if not text.endswith('<think>\n\n</think>\n\n'):
        raise ValueError('Expected explicitly closed non-thinking assistant prefix')
    tokens=tokenizer(text,return_tensors='pt')
    if tokens.input_ids.shape[1]>2048:raise ValueError('No silent prompt truncation')
    value=dict(tokens={k:v[0].tolist() for k,v in tokens.items()},keys=keys,ids=[x[0] for x in ids],id=row['id'],task=task)
    if target is not None:value['target']=keys.index(target)
    return value


def load(training=False,checkpoint=None):
    import torch
    from transformers import AutoTokenizer,Qwen3_5ForConditionalGeneration
    torch.set_num_threads(6)
    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    tokenizer.padding_side='left'
    model=Qwen3_5ForConditionalGeneration.from_pretrained(MODEL,dtype=torch.bfloat16,
        device_map={'':'cuda:0'},attn_implementation='sdpa',local_files_only=True)
    model.requires_grad_(False)
    model.config.use_cache=False
    if training or checkpoint:
        from peft import LoraConfig,get_peft_model,PeftModel
        if checkpoint:
            model=PeftModel.from_pretrained(model,checkpoint,is_trainable=training)
        else:
            targets=[name for name,module in model.named_modules() if '.language_model.' in name
                and name.rsplit('.',1)[-1] in TARGETS and isinstance(module,torch.nn.Linear)]
            if not targets or not any('in_proj_qkv' in n for n in targets):
                raise ValueError('Both linear and full attention adapters must be covered')
            model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,
                target_modules=targets,bias='none',task_type='CAUSAL_LM'))
    if training:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        model.enable_input_require_grads()
        active=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
        if not active or any('lora_' not in n or '.language_model.' not in n or 'visual' in n for n,p in active):
            raise ValueError('Only language LoRA may train')
    return tokenizer,model
