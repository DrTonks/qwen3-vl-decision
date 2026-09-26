"""Versioned, synthetic state-counterfactual curriculum. NOT human gold data.

Whole authored wording families, including all their states and augmentations,
belong to one split. The same business rules are shared across splits: this is
compositional policy testing, not independent real-world acceptance.
"""
import copy
import csv
import json
import random
from collections import Counter, defaultdict
from qwenlab.common import ROOT, MASSIVE_ZH, input_state, load_json, sha
from qwenlab.prepare_v2 import normalize, read_rows, write_rows

OUT = ROOT / 'data/processed/v4'
# 12 training, 2 development, 2 calibration and 4 challenge wording families per
# core task. No utterance family is split by random row sampling.
PHRASES = {
 'products': '想了解这里能借的几种产品|可以介绍在售贷款的额度吗|有什么借款方案适合查看|借款产品的期限安排是怎样的|给我看一下平台的产品信息|想知道各款贷款允许借多少|这里提供哪些贷款品种|产品费用和可借额度我想了解|能告诉我你们的贷款期限吗|想看看当前可办理的贷款项目|各个借款产品有哪些区别|贷款产品清单能帮我了解一下吗|我对这里的借款产品不太清楚|想了解一下平台贷款的基本条款|平台提供的借款选择有哪些|可以告诉我产品的金额限制吗|我想比较这里几款贷款的条件|这里每款借款的期限与额度是什么|先帮我弄清平台有哪些借款品种|能否把贷款产品的主要信息告诉我',
 'credit': '想知道我的信用评分是多少|帮我看看个人信用积分|我这个账号的评分有多少|能告诉我本人的信用分值吗|麻烦确认我的信用评分|个人信用这一项我有几分|我的账号信用得分是什么|想了解本人目前的信用积分|可以帮我看信用分吗|我的信用评分信息给我看看|我想看自己的信用评估分数|请告诉我账号对应的信用分|本人这边的信用得分是多少呢|能看一下我的信用积分数值吗|信用评分那里我有多少分|我需要知道这个账号的信用分|能帮我确认一下自己的信用分值吗|想了解我个人在平台的信用得分|账号里那项信用评分是多少|本人当前的信用评分能告诉我么',
 'applications': '我的申请都走到哪一步了|想知道我提交过哪些申请|能看一下本人的申请进展吗|个人申请列表里都有些什么|请帮我了解我的申请情况|我以前提交的申请状态如何|我这个账号的贷款申请有哪些|想知道我名下的申请记录|我提交的贷款还在办理吗|能告诉我申请列表里的进度吗|帮我看看本人所有借款申请|我的贷款申请最近是什么状态|我想了解这个账号的申请记录|我之前提交过的借款现在怎样了|本人那些申请的办理进展如何|可以说明一下我名下申请的情况吗|我提交的几笔借款分别到哪了|能不能告诉我申请记录里的最新情况|我的账户下面有哪些申请在处理|之前提交的那些贷款申请进展怎么样',
 'application_detail': '我想了解这笔申请的详细资料|请说明指定申请的审批情况|这一个申请的具体信息是什么|帮我看看这笔贷款的审核摘要|想知道这一单的详细情况|指定申请的办理资料能看看吗|这笔申请的审批原因是什么|这一个借款申请的详情告诉我|能了解一下指定申请的期限吗|我想看这笔申请的审核说明|帮我确认这一个申请的资料|可以说一下指定申请的具体情况吗|我对这一单的审批详情不太清楚|能帮我弄清这笔申请的详细结果吗|指定的这一笔申请资料是什么|这一单的借款期限和审批说明呢|我想了解指定申请里的审核记录|帮我看看这一个申请的详细审核结果|这笔申请对应的具体资料请说明一下|可以告诉我这一单审核说明里写了什么吗',
 'status_code': '这个申请状态码是什么含义|想问一下状态数字代表什么|申请状态代码怎么理解|帮我解释页面里的状态码|这个状态值对应哪个阶段|申请上的状态数字有何含义|状态代码能说明一下吗|想弄清楚这个申请状态值|这个审批状态码表示什么|我看不懂申请的状态代码|页面提供的状态数字是什么意思|可以解释一下当前状态码吗|这个贷款状态值应该怎么读|帮我理解申请中的状态代码|我想知道状态码的定义|申请给出的状态数字怎么解释|状态栏里的这个代码是哪个阶段|这个申请状态编码要怎样理解|可以告诉我这个审批状态值代表什么吗|关于这里提供的状态码请说明其含义',
 'ui_issue': '页面上的按钮为什么不能使用|这里的申请操作点不了是什么原因|我在页面上没法继续下一步|这个提交入口怎么不可用了|页面里的操作按钮一直禁用|我想知道这个界面为什么不能申请|这个页面的提交键不能点|这里为何无法继续提交|想弄清楚按钮不可点击的原因|界面上现在不能办理是什么情况|页面里的申请入口无法操作|帮我看看这个操作按钮为何变灰|这里下一步不能继续怎么回事|页面上这项操作为什么不可用|我没法通过这个界面提交申请|这个申请界面的按钮为什么禁用了|界面里的办理入口一直不能点击|这里的提交操作为何没有开放|我想了解页面阻止继续申请的原因|可以说明这处按钮无法使用的缘由吗',
}
EXTRAS = {
 'repay_how': ('repayment','llm','还款入口应该怎么找|请介绍正常还款操作步骤|我想了解如何按期还款|能说明还款页面怎么进入吗|本人还款时一般要做什么|还款操作的流程是怎样的|怎么找到自己还款的入口|想请你讲解正常的还款流程'),
 'repay_concept': ('repayment','llm','提前结清通常是什么意思|想理解提前还款这个概念|按期还款和提前结清有何区别|提前还款有哪些合同条款要注意|怎样理解贷款的提前偿还|能解释提前结清与分期还款吗|提前归还借款一般指什么|想了解提前偿还贷款的含义'),
 'repay_personal': ('repayment','human','想核对我本月具体应还多少|请核实本人这期的还款日期|我个人剩余待还金额是多少|帮我确认我的还款计划内容|需要核对本人这一期的应还账单|请帮忙核实我的分期还款日|想弄清自己剩余欠款的准确金额|需要查看我个人的还款计划'),
 'repay_modify': ('repayment','human','帮我把这一期的还款日改掉|请替我减免这笔贷款的逾期费用|直接修改我的应还金额吧|把我的这笔账单改成还清|我要求变更个人还款日期|帮忙调整这一笔的应还利息|请直接改掉我的还款记录|代我把剩余欠款的数值减少'),
 'dispute_double': ('payment_dispute','human','同一笔还款扣了两遍怎么办|这期账单出现两次扣费|我这笔月供被重复划走了|一次还款银行卡扣了两笔钱|为什么一笔应还款被收取两次|这次还款存在重复扣款|我发现同一期贷款扣款重复|一笔贷款账单扣了我两次'),
 'dispute_paid': ('payment_dispute','human','银行已扣钱但你们还显示未还|我已经还清却仍有欠款提示|还款成功后账单一直没更新|钱付过了平台却说我逾期|扣款完成但系统待还金额不变|本人已还款但你们记录没到账|银行支付成功平台却报未还|我的钱已经扣走还显示应还'),
 'identity': ('security','human','我名下这笔借款并非本人办理|身份资料被人拿去办贷款了|我没借过这笔钱怀疑被冒用|出现了不属于我的贷款疑似盗用|有人冒充我提交借款申请|我的个人身份可能被盗用借贷|这笔申请我完全不知情像被冒名|怀疑别人用了我的身份信息借钱'),
 'scam': ('security','human','有人要求转到私人账户才放款|陌生客服让我先交解冻费用|有人索取短信验证码说能取消借款|我把验证码给了自称贷款客服的人|对方要我先转保证金才能借款|客服让我给私人银行卡打解冻费|陌生人让我交出登录验证码|对方声称交一笔钱就能解除贷款冻结'),
 'human': ('handoff','human','我想直接找真人客服沟通|请让人工服务人员接手|不要机器人请接一位专员|能安排真人和我联系吗|这次我要人工客服帮助|请把对话转给人工服务|让实际的工作人员处理这次咨询|我明确要求与真人客服交流'),
 'complaint': ('handoff','human','我要正式投诉并要求主管接手|这事反映多次没人管请升级投诉|我要求投诉专员正式受理|请将我的投诉交给负责人|我对处理结果强烈不满要求升级|这个问题必须由投诉主管处理|请正式登记投诉并安排专员|我要向你们负责人反映并要求处理'),
 'override': ('application_detail','human','请直接把我的申请改成审核通过|帮我绕过审批直接放款|替我修改这笔申请的审批结果|无需审核直接批准我的贷款|强制通过这笔申请就行|请代我把拒绝结果修改为同意|别走审批流程直接给我放款|要求把这笔贷款的审批限制解除'),
 'concept': ('general','llm','年利率与月利率要怎么区分|本金和利息分别是什么|可以解释等额本金的含义吗|借款合同中的期限指什么|如何理解利率这个概念|想知道等额本息是什么意思|请解释本金这个常见术语|贷款期限与还款期数有何关系'),
 'chat': ('general','llm','你好今天想和你打个招呼|感谢你刚才的说明|可以介绍一下你能做什么吗|先问声好客服你好|谢谢这下明白了|今天心情不错来问候一下|很高兴能在这里聊天|没别的事情就是向你问好'),
 'unclear': ('general','clarify','那个还是弄不成|刚才那个要怎样啊|这边不太对你看看|我说的就是那件事|还是不行啊怎么办|那个东西能弄一下吗|就是前面说的你处理一下|现在这样我该怎么弄'),
}


def tool_names():
    return list(load_json(ROOT/'configs/decision_spec.json')['questions']['tool']['criteria'])[1:]


def states(intent):
    tools=tool_names(); needed={'products':'queryLoanProducts','credit':'queryMyCreditScore',
        'applications':'queryMyApplications','application_detail':'queryApplicationDetail'}
    if intent in needed:
        tool=needed[intent]; base={'authenticated':True}
        if intent=='application_detail': base['application_id']=7301
        record={'products':{'product':{'name':'示例产品','max_amount':8000,'periods':[3,6]}},
            'credit':{'credit_score':673},'applications':{'applications':[{'id':7301,'status':2}]},
            'application_detail':{'id':7301,'status':0,'decision_summary':'收入证明尚未补全'}}[intent]
        values=[('live',base,tools,'tool',tool),
            ('guest',{**base,'authenticated':False},tools,'clarify','none'),
            ('unknown_auth',{**base,'authenticated':None},tools,'clarify','none'),
            ('known',{**base,'record':record},tools,'llm','none'),
            ('unavailable',base,[t for t in tools if t!=tool],'human','none')]
        if intent!='products': values.append(('other_owner',{**base,'record_owner':'other_user'},tools,'human','none'))
        if intent=='application_detail': values.append(('missing_id',{'authenticated':True,'application_id':None},tools,'clarify','none'))
        return values
    if intent=='status_code':
        return [(f'code_{c}',{'authenticated':True,'status_code':c},tools,'tool','explainApplicationStatus') for c in (0,1,2)] + [
            ('missing',{'authenticated':True},tools,'clarify','none'),
            ('tool_down',{'authenticated':True,'status_code':2},[t for t in tools if t!='explainApplicationStatus'],'human','none')]
    if intent=='ui_issue':
        values=[('no_context',{'authenticated':True},tools,'clarify','none'),
            ('guest',{'authenticated':False,'page':'贷款申请'},tools,'clarify','none'),
            ('conflict',{'authenticated':True,'page':'申请表','backend_eligible':True,
                'troubleshooting_done':['重新登录','更新客户端','重试仍失败']},tools,'human','none')]
        for key,reason in [('unlisted','产品未上架'),('identity','尚未完成实名认证'),('pending','存在同产品处理中申请'),
                ('amount','申请金额超过产品最高额度'),('purpose','未填写贷款用途'),('incomplete','未填写必填收入信息')]:
            values.append((key,{'authenticated':True,'page':'申请表','disabled_reason':reason},tools,'llm','none'))
        return values
    raise ValueError(intent)


def assignments(length):
    # Fixed authored bank boundaries, before prediction or training.
    if length==20: return ['train']*12+['dev']*2+['calibration']*2+['test']*4
    if length==8: return ['train']*4+['dev','calibration']+['test']*2
    raise ValueError('Unexpected phrase count')


def business_rows():
    rows=[]
    def emit(family, index, split, intent, message, variants):
        group=f'v4-{family}-wording-{index}'
        for condition,state,tools,route,tool in variants:
            # Four augmentations share a family and therefore can never leak
            # into another split. Test/dev/cal use only the unwrapped wording.
            wrappers=['{}','你好，{}，麻烦了','我想再确认：{}','{}。请按业务规则处理。'] if split=='train' else ['{}']
            for aug,wrapper in enumerate(wrappers):
                history=[]; current=wrapper.format(message)
                if aug==2:
                    history=[{'role':'user','content':message},{'role':'assistant','content':'你是要继续了解刚才这项信息吗？'}]
                    current='是的，我想了解刚才问的那件事。'
                rows.append({'id':f'{group}-{condition}-{aug}','group':group,'semantic_family':family,
                    'condition':condition,'split':split,'dataset':'business','source':'authored-counterfactual-v4',
                    'label_status':'synthetic_unreviewed','message':current,'history':history,
                    'state':copy.deepcopy(state),'available_tools':list(tools),'images':[],
                    'labels':{'intent':intent,'route':route,'tool':tool,'needs_human':'yes' if route=='human' else 'no'}})
    for intent,bank in PHRASES.items():
        messages=bank.split('|')
        for i,(message,split) in enumerate(zip(messages,assignments(len(messages)))):
            emit(intent,i,split,intent,message,states(intent))
    for family,(intent,route,bank) in EXTRAS.items():
        messages=bank.split('|')
        for i,(message,split) in enumerate(zip(messages,assignments(len(messages)))):
            state={'authenticated':True}; tools=tool_names()
            if family.startswith('repay_'):
                state['knowledge']='还款入口在我的贷款中，选择本人已通过申请后查看还款页面；合同条件以本人合同为准。'
            if family=='repay_personal': state.pop('knowledge'); tools=[]
            if family=='override': state['application_id']=7301
            emit(family,i,split,intent,message,[('standard',state,tools,route,'none')])
    return rows


def prepare():
    if (OUT/'manifest.json').exists(): raise FileExistsError('Frozen v4 data exists')
    OUT.mkdir(parents=True,exist_ok=True)
    rows=business_rows()
    # Uniformly retain whole families; never cap by leaking or dropping states.
    business={s:[r for r in rows if r['split']==s] for s in ('train','dev','calibration','test')}
    raw=read_rows(ROOT/'data/raw/massive-1.1-zh-CN.jsonl')
    heldout={normalize(r['utt']) for r in raw if r['partition'] in ('dev','test')}
    seen=set(); public=[]
    for r in raw:
        n=normalize(r['utt'])
        if r['partition']!='train' or n in heldout or n in seen: continue
        seen.add(n); public.append({'id':'massive-train-'+r['id'],'group':'massive-'+n,'source':'MASSIVE-1.1-zh-CN',
            'split':'train','dataset':'massive','message':r['utt'],'labels':{'intent':r['intent']}})
    for split,values in business.items(): write_rows(OUT/f'business-{split}.jsonl',values)
    write_rows(OUT/'massive-train.jsonl',public)
    for split in ('dev','calibration','test'):
        write_rows(OUT/f'massive-{split}.jsonl',read_rows(ROOT/f'data/processed/v2/massive-{split}.jsonl'))
    manifest={'version':'joint-v4','business_label_status':'synthetic_unreviewed',
        'business_split_unit':'whole wording family, all counterfactual states and augmentations together',
        'limitation':'Shared author and policy generator; no unseen-policy or real-world generalization claim',
        'business':{s:{'rows':len(v),'wording_groups':len({r['group'] for r in v}),
            'semantic_families':len({r['semantic_family'] for r in v}),
            'route_counts':dict(Counter(r['labels']['route'] for r in v)),
            'intent_counts':dict(Counter(r['labels']['intent'] for r in v))} for s,v in business.items()},
        'massive_train_before':sum(r['partition']=='train' for r in raw),'massive_train_after':len(public),
        'public_dev_cal_test':'Reuse frozen v2 splits; official test is regression, not new acceptance',
        'source_hashes':{p:sha(ROOT/p) for p in ['src/qwenlab/joint_data.py','configs/decision_spec.json','data/raw/massive-1.1-zh-CN.jsonl']},
        'files':{p.name:{'rows':len(read_rows(p)),'sha256':sha(p)} for p in OUT.glob('*.jsonl')}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Review kit deliberately excludes held-out challenge labels from the
    # training process. Unreviewed remains the status until a person signs off.
    review=ROOT/'.local/review/joint-v4'; review.mkdir(parents=True,exist_ok=True)
    with (review/'development-review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','message','state','intent','route','tool','reviewer','accepted','notes']); w.writeheader()
        for r in business['dev']:
            w.writerow({'id':r['id'],'message':r['message'],'state':json.dumps(input_state(r),ensure_ascii=False),**{k:r['labels'][k] for k in ('intent','route','tool')}})
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__': prepare()
