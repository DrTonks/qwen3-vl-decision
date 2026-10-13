"""Fresh 2B QLoRA; identical NF4 prepared base for baseline/train/inference."""
from qwenlab.common import ROOT

MODEL=ROOT/'models/Qwen3-VL-2B-Instruct'
TARGETS=('q_proj','v_proj')


def load(training=False,checkpoint=None):
    import torch
    from qwenlab.modeling import load_model
    from peft import prepare_model_for_kbit_training,LoraConfig,get_peft_model,PeftModel
    tok,model=load_model('nf4')
    tok.padding_side='left'
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=training,
        gradient_checkpointing_kwargs={'use_reentrant':False})
    model.config.use_cache=False
    if training or checkpoint:
        if checkpoint:
            model=PeftModel.from_pretrained(model,checkpoint,is_trainable=training)
        else:
            targets=[n for n,_ in model.named_modules() if '.language_model.' in n and n.rsplit('.',1)[-1] in TARGETS]
            if not targets: raise ValueError('Missing language LoRA targets')
            model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,
                target_modules=targets,bias='none',task_type='CAUSAL_LM'))
    if training:
        active=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
        if not active or any('lora_' not in n or '.language_model.' not in n or 'visual' in n or p.dtype!=torch.float32 for n,p in active):
            raise ValueError('Only FP32 language LoRA may train')
    return tok,model
