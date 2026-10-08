"""Training-source-only contrast candidates. No release, inference or API.

Do not import development error lists, Jev predictions or final labels. Held-out
messages are only used by the rejection audit AFTER deterministic construction.
Never claim template expansion is independent scenario coverage or human review.
"""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import difflib
import hashlib
import json
from pathlib import Path
import re

from qwenlab.common import ROOT
from qwenlab.financial_pilot import TOOLS, label, serialize_input, normalize
from qwenlab import financial_ready as frozen

OUT=ROOT/'data/financial-boundary-candidates-v1'
SEED='boundary-training-sources-20261002-v1'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def training_sources():
    frozen.validate()
    paths=sorted((frozen.BASE/'parts').glob('part-*.jsonl'))+[frozen.OUT/'train-additions.jsonl']
    groups=read(frozen.OUT/'groups.json');rows=[];bindings={}
    for p in paths:
        bindings[p.relative_to(ROOT).as_posix()]=sha(p)
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            row=json.loads(line)
            if row['split']!='train' or groups[row['id']]['split']!='train':
                raise ValueError('Non-training source rejected')
            row=deepcopy(row);row['_source_file']=p.relative_to(ROOT).as_posix()
            row['_source_group']=groups[row['id']]['group'];rows.append(row)
    return rows,bindings


def choose(rows,predicate,count,used_groups):
    selected=[]
    for row in sorted(rows,key=lambda r:digest([SEED,r['id']])):
        if predicate(row) and row['_source_group'] not in used_groups:
            selected.append(row);used_groups.add(row['_source_group'])
            if len(selected)==count:break
    if len(selected)!=count:raise ValueError('Insufficient distinct training source groups')
    return selected


def eligible_tool(row):
    a=row['annotation'];v=row['input']
    return (a['action']=='tool' and a['tool_name'] in ['queryMyCreditScore','queryMyApplications','queryApplicationDetail']
        and v['state'].get('authenticated') is True and a['tool_name'] in v['available_tools']
        and not v['images'] and len(v['message'])<=120 and not v['history'])


def derive(source,kind,index):
    if source.get('split')!='train' or not source.get('_source_group') or not source.get('_source_file'):
        raise ValueError('Only bound training sources may generate candidates')
    if index not in [0,1,2]:raise ValueError('Unknown contrast variant')
    original={k:v for k,v in source.items() if not k.startswith('_')}
    v=deepcopy(source['input']);a=deepcopy(source['annotation']);tool=a['tool_name']
    if kind=='query':
        if index==0:
            v['state']['authenticated']=False
            a=label('clarify','查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。',slots=['authentication'])
            rule='authentication-required'
        elif index==1:
            v['available_tools']=[t for t in v['available_tools'] if t!=tool]
            a=label('human','所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。')
            rule='missing-exact-read-tool'
        else:
            v['message']+='这里只允许读取已有内容，不授权新增、删除或改动任何记录。'
            a['reason']='合法的本人只读查询；明示不授权写入不构成请求违规写入。'
            rule='deny-write-allow-read'
    elif kind=='human':
        if index==0:v['state']['authenticated']=False
        elif index==1:v['available_tools']=[]
        else:v['capabilities']['handoff_connected']=True
        a=label('human','保持原始明确人工诉求；认证/只读工具/是否已连通不取消下一步人工处理意图。不得把动作决定当受理结果。')
        rule=['human-before-auth','human-without-tools','human-with-connected-channel'][index]
    elif kind=='quoted_request':
        request=v['message']
        if index==0:
            v['message']='请实际执行下面这项操作，不是只讨论它：'+request
            a=label('refuse','引用内容仍被明确要求执行，原始违规请求不能因外层包装得到授权。')
            rule='quoted-execution'
        elif index==1:
            v['message']='有人给我发了这句话：“'+request+'”。我在辨认风险，想了解为什么不应照办，并没有要求你执行。'
            a=label('answer','用户询问已给违规话语的风险，明确不要求执行；可解释现有规则和能力边界，不提供实施方法。')
            rule='quoted-risk-explanation'
        else:
            v['message']='我收到一条可疑指令：“'+request+'”。我没有照做，想找真人客服报告这条信息。'
            a=label('human','当前真实诉求是向人工报告收到的可疑指令，不是代替发信者执行违规要求。')
            rule='quoted-report-to-human'
    else:raise ValueError('Unknown family')
    key=f"FIN-BC1-{kind}-{source['id']}-{index+1}"
    return dict(id=key,split='train_candidate',scene_family_id='boundary:'+source['_source_group'],input=v,annotation=a,
        provenance=dict(origin='synthetic',producer='assistant',method='controlled_training_source_contrast',
            source_file=source['_source_file'],source_id=source['id'],source_split='train',
            source_group=source['_source_group'],source_row_sha256=digest(original),
            source_license=source['provenance'].get('license'),rule=rule,
            adaptation='Training source only; no held-out mistake paraphrase; category priorities are informed by prior development diagnostics.'),
        review=dict(status='needs_independent_label_review',human_reviewed_current_version=False,independently_reviewed=False),
        usage='candidate_only_never_auto_train')


def construct(rows):
    used=set()
    query=choose(rows,eligible_tool,64,used)
    human=choose(rows,lambda r:r['annotation']['action']=='human' and not r['input']['history']
        and r['input']['state'].get('authenticated') is True
        and r['input']['capabilities']['handoff_connected'] is False
        and bool(r['input']['available_tools']) and bool(re.search('人工|真人',r['input']['message'])),32,used)
    quotes=choose(rows,lambda r:r['annotation']['action']=='refuse' and not r['input']['history']
        and len(r['input']['message'])<=95
        and bool(re.search('贷款|借款|还款|扣款|合同|账单|利息|授权|银行卡|征信',r['input']['message'])),32,used)
    return [derive(r,kind,i) for kind,group in [('query',query),('human',human),('quoted_request',quotes)] for r in group for i in range(3)]


def protected_inputs():
    # Read ONLY inputs, never propagate labels, model outputs or error IDs.
    paths=[frozen.OUT/'evaluation'/(split+'.json') for split in ['development','calibration','final']]
    texts=set();bindings={}
    for p in paths:
        bindings[p.relative_to(ROOT).as_posix()]=sha(p)
        texts.update(normalize(r['input']['message']) for r in read(p))
    for p in [ROOT/'data/support-fresh-holdout-v1/cases.jsonl',
              ROOT/'data/processed/v5/business-test.jsonl',ROOT/'data/processed/v5/business-calibration.jsonl']:
        if p.exists():
            bindings[p.relative_to(ROOT).as_posix()]=sha(p)
            for line in p.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    r=json.loads(line);texts.add(normalize(r.get('message') or r['input']['message']))
    return texts,bindings


def validate_row(r):
    v=r['input'];a=r['annotation'];rule=r['provenance']['rule']
    if r['split']!='train_candidate' or r['provenance']['source_split']!='train':raise ValueError('Wrong split')
    if r['review']['human_reviewed_current_version'] or r['review']['independently_reviewed']:raise ValueError('Unverified review claim')
    if v['images'] or len(v['history'])>4:raise ValueError('Text/short-history protocol')
    if a['action']=='tool':
        if not v['state'].get('authenticated') or a['tool_name'] not in v['available_tools']:raise ValueError('Impossible tool target')
    elif a['tool_name'] is not None:raise ValueError('Non-tool target leaked tool label')
    expected={'authentication-required':'clarify','missing-exact-read-tool':'human','deny-write-allow-read':'tool',
        'human-before-auth':'human','human-without-tools':'human','human-with-connected-channel':'human',
        'quoted-execution':'refuse','quoted-risk-explanation':'answer','quoted-report-to-human':'human'}
    if a['action']!=expected[rule]:raise ValueError('Contrast target inconsistent')


def legacy_audit(rows):
    from qwenlab.financial_completion import completion_protection, BASE
    blocked=completion_protection()
    matches=[r['id'] for r in rows if normalize(r['input']['message']) in blocked]
    if matches:raise ValueError('Legacy evaluation overlap; quarantine before any release')
    return dict(legacy_protection_sha256=sha(BASE/'protection.json'),legacy_protected_messages=len(blocked),
        candidate_sha256=sha(OUT/'candidates.json'),exact_matches=matches,
        limitation='Legacy public/evaluation normalized exact matching; .86 near matching is separately limited to frozen financial/current and selected legacy business evaluations.')


def build():
    if OUT.exists():raise FileExistsError('Candidate pack already exists; validate instead, never silently regenerate')
    sources,bindings=training_sources();draft=construct(sources)
    protected,eval_bindings=protected_inputs()
    train_keys={serialize_input(r) for r in sources};seen=set();excluded_groups={};near=[]
    for r in draft:
        key=serialize_input(r);group=r['scene_family_id'];text=normalize(r['input']['message'])
        if key in train_keys:excluded_groups.setdefault(group,[]).append('existing_training_input')
        if key in seen:excluded_groups.setdefault(group,[]).append('duplicate_candidate_input')
        seen.add(key)
        if text in protected:excluded_groups.setdefault(group,[]).append('protected_message_exact')
        else:
            matches=difflib.get_close_matches(text,protected,n=1,cutoff=.86)
            if matches:
                excluded_groups.setdefault(group,[]).append('protected_message_near')
                near.append(dict(candidate_id=r['id'],similarity=difflib.SequenceMatcher(None,text,matches[0]).ratio()))
    accepted=[r for r in draft if r['scene_family_id'] not in excluded_groups]
    if not accepted:raise ValueError('No candidates survived conservative group rejection')
    for r in accepted:validate_row(r)
    OUT.mkdir(parents=True)
    write(OUT/'candidates.json',accepted)
    write(OUT/'legacy-protection-audit.json',legacy_audit(accepted))
    selected_ids={r['provenance']['source_id'] for r in accepted}
    write(OUT/'training-source-snapshot.json',[{k:v for k,v in r.items() if not k.startswith('_')} for r in sources if r['id'] in selected_ids])
    audit=dict(initial_rows=len(draft),initial_source_groups=128,accepted_rows=len(accepted),
        accepted_source_groups=len({r['scene_family_id'] for r in accepted}),excluded_groups=excluded_groups,
        near_match_scores=near,near_cutoff=.86,actions=dict(Counter(r['annotation']['action'] for r in accepted)),
        rules=dict(Counter(r['provenance']['rule'] for r in accepted)),
        limitation='Lexical rejection is not semantic independence. Adaptive categories and repeated templates; no new blind evaluation, no independent label approval.')
    write(OUT/'audit.json',audit)
    with (OUT/'review.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','source_id','rule','message','state','available_tools','action','tool_name','review_decision','review_note'])
        writer.writeheader()
        for r in accepted:
            writer.writerow(dict(id=r['id'],source_id=r['provenance']['source_id'],rule=r['provenance']['rule'],
                message=r['input']['message'],state=json.dumps(r['input']['state'],ensure_ascii=False),
                available_tools=json.dumps(r['input']['available_tools'],ensure_ascii=False),action=r['annotation']['action'],
                tool_name=r['annotation']['tool_name'] or '',review_decision='pending',review_note=''))
    lines=['# 边界候选逐组复核','', '仅训练候选，未独立复核、未人审、不会自动训练。CSV为编辑草稿，不会悄悄覆盖JSON或生成审核证明。','']
    for r in accepted:
        lines += [f"## {r['id']}",f"来源：{r['provenance']['source_id']}；规则：{r['provenance']['rule']}",
            r['input']['message'],f"状态：`{json.dumps(r['input']['state'],ensure_ascii=False)}`",
            f"工具：`{','.join(r['input']['available_tools'])}`；人工连通：{r['input']['capabilities']['handoff_connected']}",
            f"建议：**{r['annotation']['action']}** / {r['annotation']['tool_name']}；{r['annotation']['reason']}",'']
    (OUT/'review.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    write(OUT/'manifest.json',dict(version='financial-boundary-candidates-v1',status='candidate_not_training_release',
        seed=SEED,source_files=bindings,protected_files=eval_bindings,
        files={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='review.csv'},
        author='assistant',human_review=False,independent_label_review=False,model_calls=0,
        frozen_training_protocol_changed=False,training_eligible=False,generator_sha256=sha(Path(__file__))))
    print(json.dumps(audit,ensure_ascii=False,indent=2))


def validate():
    m=read(OUT/'manifest.json')
    if m.get('generator_sha256')!=sha(Path(__file__)):raise ValueError('Generator changed; review required')
    for name,h in m['files'].items():
        if sha(OUT/name)!=h:raise ValueError('Candidate changed; regenerate review/audit in a new version before release: '+name)
    for name,h in dict(m['source_files'],**m['protected_files']).items():
        if sha(ROOT/name)!=h:raise ValueError('Source/protected data changed: '+name)
    rows=read(OUT/'candidates.json');snapshot={r['id']:r for r in read(OUT/'training-source-snapshot.json')}
    if read(OUT/'legacy-protection-audit.json')!=legacy_audit(rows):raise ValueError('Legacy overlap proof changed')
    for r in rows:
        validate_row(r)
        if digest(snapshot[r['provenance']['source_id']])!=r['provenance']['source_row_sha256']:raise ValueError('Source row changed')
    assert len({r['id'] for r in rows})==len(rows)
    parent_groups=read(frozen.OUT/'groups.json')
    for r in rows:
        parent=parent_groups[r['provenance']['source_id']]
        if parent['split']!='train' or parent['group']!=r['provenance']['source_group']:
            raise ValueError('Parent partition/group changed')
    print(json.dumps(dict(rows=len(rows),groups=len({r['scene_family_id'] for r in rows}),training_eligible=False,
        provenance_and_protection_hashes='pass',independent_label_review='pending'),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['build','validate']);args=p.parse_args()
    build() if args.command=='build' else validate()
