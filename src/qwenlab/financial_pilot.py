"""Build/validate a traceable eight-action TEXT candidate pilot, never train.

Existing train sources and frozen evaluation files are read-only. No model,
vendor API, automatic human-review declaration or production config is used.
"""
import argparse
from collections import Counter
from copy import deepcopy
import difflib
import json
from pathlib import Path
import zipfile
from qwenlab.common import ROOT, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.support_curriculum import normalize
from qwenlab.financial_pilot_catalog import BUSINESS_PLANS, MASSIVE_IDS, ADAPTATIONS, authored_groups

OUT=ROOT/'data/financial-actions-text-pilot-v1'
BUSINESS=ROOT/'data/support-curriculum-v2-reviewed-01/train-reviewed-only.jsonl'
MASSIVE=ROOT/'data/processed/v5/massive-train.jsonl'
ACTIONS=['clarify','retrieve','tool','answer','human','redirect','refuse','close']
TOOLS=['queryLoanProducts','queryMyApplications','queryApplicationDetail','queryMyCreditScore','explainApplicationStatus']
COLLECTIONS=['loan_service_docs','privacy_policy']
VERSION='loan-eight-actions-pilot-1'
DISCUSSION={'FIN-P1-F13-A-01-base':'可能是在同时询问两个状态，而非缺少状态；旧澄清标签未必成立，暂不纳入可选训练候选。'}


def visible_input(row):
    """Only this object may be encoded. Labels/provenance are never model input."""
    value=deepcopy(row['input'])
    value['available_tools']=sorted(value['available_tools'])
    value['capabilities']['knowledge_collections']=sorted(value['capabilities']['knowledge_collections'])
    return value


def serialize_input(row):
    return json.dumps(visible_input(row),ensure_ascii=False,sort_keys=True,separators=(',',':'))


def base_input(message, state=None, history=None):
    return {'message':message,'history':history or [],'state':state or {'authenticated':True},
            'service_scope':'loan_platform','capability_profile':'planned-kb-v1',
            'capabilities':{'knowledge_collections':COLLECTIONS.copy(),'handoff_connected':False},
            'available_tools':TOOLS.copy(),'images':[]}


def label(action, reason, tool=None, collection=None, slots=None, arguments=None):
    return {'action':action,'tool_name':tool,'tool_arguments':arguments or {},
            'retrieval_collection':collection,'missing_slots':slots or [],'reason':reason,
            'evidence_paths':['input.message'],'policy_version':VERSION}


def make(key, family, value, target, provenance):
    return {'id':'FIN-P1-'+key,'scene_family_id':family,'split':'train_candidate',
            'input':value,'annotation':target,'provenance':provenance,
            'review':{'status':'needs_discussion' if 'FIN-P1-'+key in DISCUSSION else 'assistant_draft','human_reviewed_current_version':False},
            'usage':'candidate_only_not_training_release'}


def protected_pool():
    paths=[]
    for p in (ROOT/'data').rglob('*.jsonl'):
        if any(x in p.stem.lower() for x in ['test','dev','calibration','challenge']) or p==ROOT/'data/support-fresh-holdout-v1/cases.jsonl':
            paths.append(p)
    texts=set(); hashes={}; finance=set()
    for p in paths:
        hashes[p.relative_to(ROOT).as_posix()]=sha(p)
        for r in read_rows(p):
            msg=r.get('message')
            if msg:
                texts.add(normalize(msg))
                if r.get('dataset')=='business':finance.add(normalize(msg))
    p=ROOT/'data/raw/massive-1.1-zh-CN.jsonl';hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    for r in read_rows(p):
        if r['partition']!='train':texts.add(normalize(r['utt']))
    for name in ['val','test']:
        p=ROOT/f'data/raw/crosswoz-{name}.json.zip';hashes[p.relative_to(ROOT).as_posix()]=sha(p)
        with zipfile.ZipFile(p) as z:
            d=json.loads(z.read(next(x for x in z.namelist() if x.endswith('.json'))))
        for dialog in d.values():
            texts.update(normalize(m['content']) for m in dialog['messages'] if m['role']=='usr')
    return texts,finance,hashes


def business_label(r, action):
    intent=r['labels']['intent']; tool=r['labels']['tool'] if action=='tool' else None
    args={}
    if tool=='queryApplicationDetail':args={'applicationId':r['state']['application_id']}
    if tool=='explainApplicationStatus':args={'status':r['state']['status_code']}
    slots=[]
    if action=='clarify':
        slots=[{'application_detail':'application_id','status_code':'status_code','ui_issue':'error_context'}.get(intent,'request_details')]
    reason={'tool':'需要现有白名单只读工具取得当前账户或产品数据；参数须由可信状态/明确输入落地。',
            'clarify':'缺少或未明确必要查询对象、状态或问题细节，先补充信息。',
            'answer':'一般解释或礼貌交流，不要求未知平台规则或新的个人记录。',
            'human':'明确人工需求或正在发生的账户/资金/申诉事项需要升级；并不表示工单已创建。',
            'retrieve':'平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。'}[action]
    return label(action,reason,tool,'loan_service_docs' if action=='retrieve' else None,slots,args)


def contrast_rows():
    rows=[]
    def pair(key,message,variants):
        for i,(value,target) in enumerate(variants):
            target['evidence_paths']=['input.message','input.history','input.state','input.capabilities','input.available_tools']
            rows.append(make(f'contrast-{key}-{i+1}',f'new-contrast:{key}',value,target,
                {'kind':'assistant_authored_state_pair','source':'project_requirements','parent_id':None,
                 'origin':'synthetic','source_split':None,'license':'project_authored','modification':'same message, controlled state/capability change'}))
    message='把本账户已经记录的评分数值调给我。'
    a=base_input(message,{'authenticated':False});b=base_input(message)
    pair('login',message,[(a,label('clarify','未登录不能查个人评分；追问/引导完成认证。',slots=['authentication'])),
                          (b,label('tool','已登录且无当前评分事实，可只读查询。',tool='queryMyCreditScore'))])
    message='请打开我刚才指定的那份借款申请明细。'
    a=base_input(message);b=base_input(message,{'authenticated':True,'application_id':73168},
        [{'role':'user','content':'接下来我要看的申请编号是73168。'},{'role':'assistant','content':'已确认您指定的编号，可以继续说明需要查询的内容。'}])
    pair('object',message,[(a,label('clarify','没有历史与选中编号，无法落地单笔查询。',slots=['application_id'])),
                         (b,label('tool','历史明确提供对象，状态有相同编号；执行时仍核对归属。',tool='queryApplicationDetail',arguments={'applicationId':73168}))])
    message='这里上传申请材料允许哪些文件后缀？'
    a=base_input(message);b=base_input(message);b['capability_profile']='current-no-kb-v1';b['capabilities']['knowledge_collections']=[]
    pair('kb-availability',message,[(a,label('retrieve','规则依赖平台文档，模拟检索能力可用。',collection='loan_service_docs')),
        (b,label('answer','规则事实与检索均不可用，回答仅如实说明无法核实并指向已公布渠道，不编造支持格式。'))])
    message='能说明当前页面那条材料格式提示的意思吗？'
    a=base_input(message);b=base_input(message,history=[{'role':'user','content':'页面原文是“请上传PDF文件”。我只想理解这句话，不核实其他规则。'}])
    pair('known-text',message,[(a,label('clarify','缺少所指提示原文，先请用户提供文字。',slots=['error_context'])),
        (b,label('answer','已给明确提示原文，只解释可见文字，不把它当账户或审批事实。'))])
    message='请列出我这个账号提交的全部借款申请。'
    a=base_input(message);b=base_input(message);b['available_tools']=[]
    pair('tool-availability',message,[(a,label('tool','登录且列表工具可用，查询本人记录。',tool='queryMyApplications')),
        (b,label('human','需要个人记录但无可用查询能力，按试点政策建议人工协助；handoff未接通须明确告知。'))])
    message='平台正式的附件上传流程能查给我吗？'
    a=base_input(message,{'authenticated':False});b=base_input(message)
    pair('public-doc-login',message,[(a,label('retrieve','模拟知识集合为公开业务文档，不要求登录。',collection='loan_service_docs')),
        (b,label('retrieve','已登录也应检索未知平台流程，不能改为查询个人记录。',collection='loan_service_docs'))])
    return rows


def candidates(blocked):
    business=read_rows(BUSINESS); massive={r['id']:r for r in read_rows(MASSIVE)}
    rows=[];exclusions=[]
    for action,prefixes in BUSINESS_PLANS.items():
        for prefix in prefixes:
            chosen=[]
            for r in business:
                if not r['id'].startswith(prefix) or r.get('history'):continue
                if normalize(r['message']) in blocked:
                    exclusions.append({'source_id':r['id'],'reason':'protected_evaluation_normalized_message'});continue
                chosen.append(r)
                if len(chosen)==2:break
            if len(chosen)!=2:raise ValueError('Insufficient reviewed source rows for '+prefix)
            for r in chosen:
                rows.append(make(r['id'],'business:'+r['group'],base_input(r['message'],r['state'],r.get('history')),
                    business_label(r,action),{'kind':'business_policy_migration','source':BUSINESS.relative_to(ROOT).as_posix(),
                    'parent_id':r['id'],'source_group':r['group'],'source_split':'train','source_original_labels':r['labels'],
                    'source_human_review':True,'origin':'assistant_authored_user_reviewed_old_policy','license':'project_authored',
                    'modification':'text unchanged; eight-action annotation and planned capability profile added'}))
    for number in MASSIVE_IDS:
        r=massive[f'massive-train-{number}']
        rows.append(make(r['id'],'massive:'+r['id'],base_input(r['message']),
            label('redirect','合法日常服务请求超出本贷款平台范围，说明范围并引导，不视为违规。'),
            {'kind':'public_original_reannotated','source':MASSIVE.relative_to(ROOT).as_posix(),'parent_id':r['id'],
             'source_split':'train','origin':'public_MASSIVE','source_original_labels':r['labels'],
             'license':'CC-BY-4.0','modification':'original text retained; action manually specified for loan scope'}))
    for x in authored_groups():
        rows.append(make(x['key'],'new:'+x['family'],base_input(x['message']),label(x['action'],x['reason'],collection=x['collection']),
            {'kind':'assistant_authored','source':'project_requirements','parent_id':None,'source_split':None,
             'origin':'synthetic','license':'project_authored','modification':'new text and annotation'}))
    for number,message,action,tool,reason in ADAPTATIONS:
        r=massive[f'massive-train-{number}']
        rows.append(make(r['id']+'-loan-adaptation','massive:'+r['id'],base_input(message),
            label(action,reason,tool,'loan_service_docs' if action=='retrieve' else None,
                  ['application_id'] if action=='clarify' else []),
            {'kind':'public_loan_adaptation','source':MASSIVE.relative_to(ROOT).as_posix(),'parent_id':r['id'],
             'source_split':'train','origin':'public_structure_assistant_rewrite','license':'CC-BY-4.0',
             'parent_message':r['message'],'modification':reason}))
    return rows+contrast_rows(),exclusions


def validate_row(r):
    if r.get('split')!='train_candidate' or r.get('usage')!='candidate_only_not_training_release':raise ValueError('Pilot is not a training release')
    if r['review']['human_reviewed_current_version'] is not False:raise ValueError('No new human review has been attested')
    if r['review']['status'] not in ['assistant_draft','needs_discussion']:raise ValueError('Unknown review status')
    v=r['input']; a=r['annotation']; action=a['action']
    if set(v)!={'message','history','state','service_scope','capability_profile','capabilities','available_tools','images'}:raise ValueError('Unexpected visible field or label leakage')
    if action not in ACTIONS or a['policy_version']!=VERSION:raise ValueError('Action/policy mismatch')
    if not isinstance(v['message'],str) or not v['message'].strip() or len(v['message'])>2000:raise ValueError('Invalid message')
    if len(v['history'])>4 or any(set(m)!={'role','content'} or m['role'] not in ['user','assistant'] or not isinstance(m['content'],str) for m in v['history']):raise ValueError('Invalid history')
    if v['images']!=[]:raise ValueError('This pilot is text only')
    if v['service_scope']!='loan_platform' or v['capability_profile'] not in ['planned-kb-v1','current-no-kb-v1']:raise ValueError('Unknown capability scope')
    if set(v['state'])-{'authenticated','application_id','status_code'} or type(v['state'].get('authenticated')) is not bool:raise ValueError('Unknown/invalid trusted state')
    for field in ['application_id','status_code']:
        if field in v['state'] and type(v['state'][field]) is not int:raise ValueError('State ID/code must be an integer')
    if len(v['available_tools'])!=len(set(v['available_tools'])) or not set(v['available_tools'])<=set(TOOLS):raise ValueError('Invalid tools')
    cap=v['capabilities']
    if set(cap)!={'knowledge_collections','handoff_connected'} or type(cap['handoff_connected']) is not bool:raise ValueError('Invalid capabilities')
    if len(cap['knowledge_collections'])!=len(set(cap['knowledge_collections'])) or not set(cap['knowledge_collections'])<=set(COLLECTIONS):raise ValueError('Invalid collections')
    if v['capability_profile']=='current-no-kb-v1' and cap['knowledge_collections']:raise ValueError('Current profile cannot claim retrieval')
    if action=='tool':
        tool=a['tool_name'];args=a['tool_arguments']
        if tool not in v['available_tools'] or not v['state']['authenticated']:raise ValueError('Unavailable/unauthenticated tool')
        if tool=='queryApplicationDetail':
            n=v['state'].get('application_id')
            if type(n) is not int or n<=0 or args!={'applicationId':n}:raise ValueError('Application ID not grounded')
            if str(n) not in v['message']+' '.join(m['content'] for m in v['history']):raise ValueError('ID absent from context')
        elif tool=='explainApplicationStatus':
            n=v['state'].get('status_code')
            if type(n) is not int or n not in [0,1,2] or args!={'status':n}:raise ValueError('Invalid status')
        elif args:raise ValueError('Unexpected tool arguments')
    elif a['tool_name'] is not None or a['tool_arguments']:raise ValueError('Non-tool action has executable tool')
    if action=='retrieve':
        if a['retrieval_collection'] not in cap['knowledge_collections']:raise ValueError('Retrieval not available')
    elif a['retrieval_collection'] is not None:raise ValueError('Unexpected retrieval target')
    if action=='clarify' and not a['missing_slots']:raise ValueError('Clarification needs an explicit missing field')
    if action!='clarify' and a['missing_slots']:raise ValueError('Unexpected missing fields')
    if not a['reason'] or not a['evidence_paths'] or any(not p.startswith('input.') for p in a['evidence_paths']):raise ValueError('Missing observable annotation evidence')
    for path in a['evidence_paths']:
        value=r
        for part in path.split('.'):
            if not isinstance(value,dict) or part not in value:raise ValueError('Evidence path does not exist')
            value=value[part]
    if r['provenance']['source_split'] not in [None,'train']:raise ValueError('Evaluation source prohibited')


def validate_rows(rows,blocked):
    seen=set();labels={}; families={}
    for r in rows:
        validate_row(r)
        if r['id'] in seen:raise ValueError('Duplicate ID')
        seen.add(r['id'])
        if normalize(r['input']['message']) in blocked:raise ValueError('Protected evaluation message: '+r['id'])
        key=serialize_input(r); target=json.dumps(r['annotation'],sort_keys=True,ensure_ascii=False)
        if key in labels:raise ValueError('Duplicate or conflicting canonical input: '+r['id'])
        labels[key]=target
        prov=r['provenance']
        if prov.get('parent_id'):
            source=(prov['source'],prov.get('source_group',prov['parent_id']))
            if source in families and families[source]!=r['scene_family_id']:raise ValueError('Related source rows split into different families')
            families[source]=r['scene_family_id']
    eligible=[r for r in rows if r['review']['status']=='assistant_draft']
    return {'rows':len(rows),'actions':dict(Counter(r['annotation']['action'] for r in rows)),
            'eligible_draft_candidates':len(eligible),'pending_discussion':len(rows)-len(eligible),
            'eligible_actions':dict(Counter(r['annotation']['action'] for r in eligible)),
            'source_kinds':dict(Counter(r['provenance']['kind'] for r in rows)),
            'families':len({r['scene_family_id'] for r in rows}),
            'unique_normalized_messages':len({normalize(r['input']['message']) for r in rows}),
            'duplicate_canonical_inputs':0,'protected_exact_normalized_matches':0,
            'human_reviewed_current_version':0,'training_release':False}


def review_markdown(rows):
    out=['# 八动作首批逐条复核','', '助手起草/重新标注；新版本未人工复核。所有条目仅为训练候选，不是测试金标。模型只读input，不读annotation/provenance/review。','']
    for action in ACTIONS:
        out += ['## '+action,'']
        for r in rows:
            if r['annotation']['action']!=action:continue
            v=r['input'];a=r['annotation'];p=r['provenance']
            out += [f"### {r['id']}", '', v['message'], '',
                f"- 来源：{p['kind']} / {p.get('parent_id') or '新起草'}；同源组：{r['scene_family_id']}",
                '- 复核状态：'+r['review']['status']+('；'+DISCUSSION[r['id']] if r['id'] in DISCUSSION else ''),
                '- 历史：'+json.dumps(v['history'],ensure_ascii=False),
                '- 状态：'+json.dumps(v['state'],ensure_ascii=False),
                '- 能力：'+json.dumps(v['capabilities'],ensure_ascii=False)+'；工具：'+', '.join(v['available_tools']),
                '- 标签：'+json.dumps({k:a[k] for k in ['action','tool_name','tool_arguments','retrieval_collection','missing_slots']},ensure_ascii=False),
                '- 依据：'+a['reason'], '']
    return '\n'.join(out)


def build():
    if OUT.exists():raise FileExistsError('Pilot exists; never overwrite reviewed data. Use validate or a new version.')
    blocked,finance,hashes=protected_pool(); rows,exclusions=candidates(blocked)
    summary=validate_rows(rows,blocked)
    near=[]
    for r in rows:
        matches=difflib.get_close_matches(normalize(r['input']['message']),sorted(finance),n=1,cutoff=.90)
        if matches:near.append({'id':r['id'],'protected_normalized_message':matches[0],'ratio':difflib.SequenceMatcher(None,normalize(r['input']['message']),matches[0]).ratio()})
    OUT.mkdir(parents=True)
    write_rows(OUT/'cases.jsonl',rows)
    atomic_json(OUT/'contract.json',{'version':VERSION,'actions':ACTIONS,'tools':TOOLS,'collections':COLLECTIONS,
        'model_visible_field':'input','canonicalization':'sort JSON object keys and set-like tool/collection arrays',
        'production_compatible':False,'knowledge_profile':'planned synthetic capability; current backend has no retrieval',
        'human_semantics':'request/recommend escalation; never imply a ticket exists',
        'answer_when_no_kb':'truthful capability limitation; do not invent missing platform facts'})
    atomic_json(OUT/'sources.json',{'business':{'file':BUSINESS.relative_to(ROOT).as_posix(),'sha256':sha(BUSINESS),'review':'old policy user-reviewed; current labels not human reviewed'},
        'massive':{'file':MASSIVE.relative_to(ROOT).as_posix(),'sha256':sha(MASSIVE),'url':'https://github.com/alexa/massive','license':'CC-BY-4.0','attribution':'FitzGerald et al., MASSIVE, Amazon Science','split':'train'},
        'new_text':'assistant authored; hypothetical loan scenes; no private database records',
        'source_code':{p:sha(ROOT/p) for p in ['src/qwenlab/financial_pilot.py','src/qwenlab/financial_pilot_catalog.py']}})
    atomic_json(OUT/'isolation-audit.json',{'protected_file_hashes':hashes,'protected_unique_messages':len(blocked),
        'excluded_source_rows':exclusions,'near_matches_to_review':near,'near_threshold':.90,
        'limitation':'String isolation is not semantic independence. This is a train-only candidate pilot, not a new held-out benchmark.'})
    atomic_json(OUT/'manifest.json',{'version':VERSION,**summary,'source_review':'assistant_draft_pending_current_version_review',
        'cases_sha256':sha(OUT/'cases.jsonl'),'all_candidates_train_only':True,'future_split_rule':'Source conversation/family and every original/adaptation remain in one partition; already trained sources cannot become independent final tests.'})
    (OUT/'review.md').write_text(review_markdown(rows),encoding='utf-8')
    atomic_json(OUT/'validation.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def validate(render=False):
    blocked,_,hashes=protected_pool()
    audit=json.loads((OUT/'isolation-audit.json').read_text(encoding='utf-8'))
    if hashes!=audit['protected_file_hashes']:raise ValueError('Protected files changed; re-audit explicitly')
    rows=read_rows(OUT/'cases.jsonl');summary=validate_rows(rows,blocked)
    summary['cases_match_initial_manifest']=sha(OUT/'cases.jsonl')==json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['cases_sha256']
    if render:(OUT/'review.md').write_text(review_markdown(rows),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','validate','render-review']);args=parser.parse_args()
    build() if args.action=='build' else validate(render=args.action=='render-review')
