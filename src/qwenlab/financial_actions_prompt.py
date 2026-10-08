"""Visible-input prompts for eight actions and a separate five-tool decision.

The two tasks share a model, not a claim of one forward pass. Tool arguments
remain observable state/ownership constraints, not an output of these letters.
"""
import json
from qwenlab.financial_pilot import ACTIONS, TOOLS, visible_input

ACTION_DESCRIPTIONS = {
    'clarify': '追问：缺必要对象、状态、提示原文或认证',
    'retrieve': '检索：未知平台规则，且正式知识集合可用',
    'tool': '查询：需要白名单只读能力获取业务记录或状态说明，已认证且相应工具可用',
    'answer': '回答：已给信息可解释，或如实说明能力限制',
    'human': '人工：明确人工诉求、具体争议或当前能力无法处理的个人事项',
    'redirect': '引导：合法请求明确超出贷款平台服务范围',
    'refuse': '拒绝：明确要求造假、越权或不允许的操作',
    'close': '结束：明确结束当前咨询，不等于撤销申请或关闭账号',
}
TOOL_DESCRIPTIONS = {
    'queryLoanProducts': '查询当前产品目录：编号、名称、金额上限、审批参考分、标签',
    'queryMyApplications': '查询本人可返回范围内的申请列表及列表状态',
    'queryApplicationDetail': '查询已明确编号的本人单笔申请明细',
    'queryMyCreditScore': '查询本人已有信用评分、档位和建议额度',
    'explainApplicationStatus': '解释已给申请状态码，仅支持0/1/2，不读取本人实时进度',
}
POLICY = (
    '你是贷款平台的客服决策组件。只根据可见消息、最多四条历史和可信状态决定下一步，不生成业务事实。'
    '五个工具都要求认证；工具不可用不能假称已查询。单笔申请需明确完整编号；状态解释仅支持0/1/2。'
    '已有提示文字可直接解释；未知平台规定仅在正式知识集合可用时检索，否则如实说明限制。'
    '人工未接通不能声称已转接。普通感谢不等于结束。合法域外需求引导，明确违规请求才拒绝。'
)


def messages(row, task='action'):
    if task not in ['action', 'tool']:
        raise ValueError('Unknown decision task')
    value = visible_input(row)
    if value['images']:
        raise ValueError('This protocol is text only')
    keys = ACTIONS if task == 'action' else TOOLS
    descriptions = ACTION_DESCRIPTIONS if task == 'action' else TOOL_DESCRIPTIONS
    choices = '\n'.join(f'{chr(65+i)} {descriptions[key]}' for i, key in enumerate(keys))
    instruction = ('选择下一步业务动作。' if task == 'action' else
                   '动作已选查询，现在选择所需的一个可用工具；仍由后端校验身份和参数。')
    return [dict(role='system', content=POLICY+'只输出一个候选字母。'),
            dict(role='user', content=json.dumps(value, ensure_ascii=False, sort_keys=True,
                separators=(',', ':'))+'\n'+instruction+'\n'+choices)], list(keys)


def encode(tokenizer, row, task='action', max_tokens=2048):
    content, keys = messages(row, task)
    symbols = [chr(65+i) for i in range(len(keys))]
    ids = [tokenizer.encode(s, add_special_tokens=False) for s in symbols]
    if any(len(value) != 1 for value in ids):
        raise ValueError('Candidate symbols must be single tokens')
    text = tokenizer.apply_chat_template(content, tokenize=False, add_generation_prompt=True)
    encoded = tokenizer(text, return_tensors='pt')
    if encoded.input_ids.shape[1] > max_tokens:
        raise ValueError('Input too long; silent truncation is prohibited')
    return encoded, keys, [value[0] for value in ids]
