"""Build a candidate-only text expansion; no training or model calls."""
import argparse
from collections import Counter
from copy import deepcopy
import difflib
import json
import re

from qwenlab.common import ROOT, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.financial_pilot import (
    OUT as PILOT, MASSIVE, ACTIONS, TOOLS, base_input, label, make,
    protected_pool, validate_rows, review_markdown, normalize,
)

OUT=ROOT/'data/financial-actions-text-v2'
SLOTS={'application_id','status_code','error_context','request_details','authentication'}
PUBLIC_EXCLUSIONS={
    'massive-train-8379':'“有什么活动”可能指平台活动，缺少足够域外对象。',
    'massive-train-12170':'“电报上的交通”表达异常，暂不用于确定标签。',
}
# Require explicit out-of-domain evidence in the utterance, not just a source tag.
PUBLIC_TOPICS={
    'weather_query':('天气预报','天气|下雨|下雪|刮风|太阳'),
    'play_music':('音乐播放','音乐|歌|爵士|五月天'),
    'play_radio':('广播播放','广播|收音机|电台'),
    'play_podcasts':('播客播放','播客'),
    'play_audiobook':('有声书播放','有声|书|三体|一九八四|美国众神|托马斯'),
    'cooking_recipe':('烹饪菜谱','菜谱|食谱|煮|烹饪|披萨|比萨|寿司|牛排'),
    'recommendation_movies':('电影推荐','电影|影院|电影院|大话西游'),
    'recommendation_events':('当地活动','活动|展会|演出|音乐会'),
    'recommendation_locations':('餐饮地点','餐馆|餐厅|菜|包子|食品店|酒吧|炸鸡|游览'),
    'transport_ticket':('交通订票','火车|高铁|旅行|票'),
    'transport_taxi':('出租车预约','出租车|优步|计程车'),
    'transport_traffic':('交通路况','交通|路况|班车|拥堵'),
    'transport_query':('出行路线','火车|开车|家乐福|沃尔玛|老街|乘车|公交|地铁'),
    'takeaway_order':('餐饮下单','外卖|寿司|披萨|比萨|汉堡|午餐|晚餐'),
    'takeaway_query':('外卖查询','外送|外卖|咖喱|多米诺'),
    'iot_coffee':('咖啡设备','咖啡'),
    'iot_cleaning':('家居清洁','打扫|吸尘|扫地'),
    'play_game':('游戏娱乐','游戏|象棋|猜拳|下棋'),
}


def public_rows(existing, blocked):
    seen={normalize(r['input']['message']) for r in existing}|blocked
    counts=Counter(); rows=[]; skipped=[]
    for r in read_rows(MASSIVE):
        intent=r['labels']['intent']; msg=r['message']; norm=normalize(msg)
        if intent not in PUBLIC_TOPICS or counts[intent]>=10:continue
        topic,pattern=PUBLIC_TOPICS[intent]
        reason=None
        if r['id'] in PUBLIC_EXCLUSIONS:reason=PUBLIC_EXCLUSIONS[r['id']]
        elif norm in seen:reason='existing_or_protected_normalized_message'
        elif len(norm)<6:reason='too_short_for_unambiguous_scope'
        elif not re.search(pattern,msg):reason='source_label_without_explicit_domain_evidence'
        elif re.search('贷款|借款|银行|还款|客服|扣款|信用|身份证|验证码|投诉|自杀|杀人|色情',msg):reason='needs_separate_scope_or_safety_review'
        if reason:
            skipped.append({'source_id':r['id'],'reason':reason});continue
        value=base_input(msg)
        row=make(r['id'],'massive:'+r['id'],value,
            label('redirect',f'当前内容明确请求{topic}，不属于贷款平台服务；正常域外请求应引导，不等同违规拒绝。'),
            {'kind':'public_original_reannotated_expansion','source':MASSIVE.relative_to(ROOT).as_posix(),
             'parent_id':r['id'],'source_split':'train','source_original_labels':r['labels'],
             'origin':'public_MASSIVE','license':'CC-BY-4.0',
             'modification':'Original utterance retained; assistant-labelled redirect for loan-only scope',
             'topic_cluster':intent})
        row['id']='FIN-T2-P-'+r['id'];rows.append(row);counts[intent]+=1;seen.add(norm)
    if len(rows)!=180:raise ValueError(f'Public selection incomplete: {counts}')
    return rows,skipped


def check(rows,blocked):
    for r in rows:
        a=r['annotation']; v=r['input']
        if any(not isinstance(r.get(k),str) or not r[k].strip() for k in ['id','scene_family_id']):raise ValueError('Missing ID/family')
        if set(a)!={'action','tool_name','tool_arguments','retrieval_collection','missing_slots','reason','evidence_paths','policy_version'}:raise ValueError('Unexpected annotation fields')
        if not isinstance(a['tool_arguments'],dict):raise ValueError('Arguments must be an object')
        if any(type(value) is not int for value in a['tool_arguments'].values()):raise ValueError('Tool argument must be an integer, not bool')
        if not isinstance(a['missing_slots'],list) or any(not isinstance(s,str) or s not in SLOTS for s in a['missing_slots']):raise ValueError('Invalid missing slots')
        if len(a['missing_slots'])!=len(set(a['missing_slots'])):raise ValueError('Duplicate missing slots')
        if not isinstance(a['reason'],str) or not a['reason'].strip():raise ValueError('Empty annotation reason')
        if not isinstance(a['evidence_paths'],list) or any(not isinstance(s,str) for s in a['evidence_paths']):raise ValueError('Invalid evidence paths')
        if not isinstance(v['history'],list):raise ValueError('History must be a list')
        state=v['state']
        if 'application_id' in state and state['application_id']<=0:raise ValueError('Invalid application ID')
        if 'status_code' in state and state['status_code'] not in [0,1,2]:raise ValueError('Unknown status code')
        if a['tool_name']=='explainApplicationStatus':
            observed=v['message']+' '.join(h['content'] for h in v['history'])
            if not re.search(r'(?<!\d)'+str(state['status_code'])+r'(?!\d)',observed):raise ValueError('Status code not observable')
        if a['tool_name']=='queryApplicationDetail':
            n=state.get('application_id'); observed=v['message']+' '.join(h['content'] for h in v['history'])
            if type(n) is not int or not re.search(r'(?<!\d)'+str(n)+r'(?!\d)',observed):raise ValueError('Whole application ID not observable')
            current_ids={int(x) for x in re.findall(r'(?:申请(?:编号|单号|号)?|编号|单号)[为是：:\s]*(\d{4,})',v['message'])}
            if current_ids and current_ids!={n}:raise ValueError('Current explicit application ID conflicts with state')
        if len(v['history']) and 'input.history' not in a['evidence_paths']:
            # Existing pilot annotations remain unchanged; it has its own provenance.
            if r['id'].startswith('FIN-T2-'):raise ValueError('History missing from evidence paths: '+r['id'])
    result=validate_rows(rows,blocked)
    result['with_history']=sum(bool(r['input']['history']) for r in rows)
    result['by_action_history']=dict(Counter(r['annotation']['action'] for r in rows if r['input']['history']))
    result['provenance_note']='Family count is a provenance grouping count, not independent real-user scenario count.'
    return result


def render_reviews(rows):
    (OUT/'review.md').write_text(review_markdown(rows),encoding='utf-8')
    folder=OUT/'review-by-action';folder.mkdir(exist_ok=True)
    for action in ACTIONS:
        (folder/(action+'.md')).write_text(review_markdown([r for r in rows if r['annotation']['action']==action]),encoding='utf-8')
    (OUT/'pending-review.md').write_text(review_markdown([r for r in rows if r['review']['status']=='needs_discussion']),encoding='utf-8')


def assemble():
    from qwenlab.financial_batch_a import rows as batch_a
    from qwenlab.financial_batch_b import rows as batch_b
    from qwenlab.financial_state_pairs import rows as state_pairs
    blocked,finance,protected=protected_pool()
    prior=read_rows(PILOT/'cases.jsonl')
    authored=batch_a()+batch_b()+state_pairs()
    public,skipped=public_rows(prior+authored,blocked)
    rows=deepcopy(prior)+authored+public
    return rows,skipped,blocked,finance,protected


def build():
    if OUT.exists():raise FileExistsError('Expansion exists; do not overwrite reviewed data')
    rows,skipped,blocked,finance,protected=assemble()
    result=check(rows,blocked)
    near=[]
    for r in rows:
        norm=normalize(r['input']['message'])
        m=difflib.get_close_matches(norm,sorted(finance),n=1,cutoff=.90)
        if m:near.append({'id':r['id'],'protected_normalized_message':m[0],'ratio':difflib.SequenceMatcher(None,norm,m[0]).ratio()})
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in PILOT.iterdir() if p.is_file()}
    sources[MASSIVE.relative_to(ROOT).as_posix()]=sha(MASSIVE)
    OUT.mkdir(parents=True)
    write_rows(OUT/'cases.jsonl',rows)
    atomic_json(OUT/'manifest.json',{'version':'financial-actions-text-v2',**result,
        'cases_sha256':sha(OUT/'cases.jsonl'),'all_candidates_train_only':True,
        'review':'assistant-authored and agent-reviewed, no current-version human attestation',
        'production_compatible':False,'independent_test_set':False})
    atomic_json(OUT/'isolation-audit.json',{'protected_file_hashes':protected,
        'protected_unique_messages':len(blocked),'near_matches_to_review':near,
        'scope':'Exact normalized current message only, plus finance lexical similarity; not semantic or conversation-level independence',
        'source_file_hashes':sources,'public_selection_skipped':skipped})
    atomic_json(OUT/'sources.json',{'inherited_pilot':'data/financial-actions-text-pilot-v1',
        'public':{'file':MASSIVE.relative_to(ROOT).as_posix(),'split':'train','license':'CC-BY-4.0',
                  'attribution':'FitzGerald et al., MASSIVE, Amazon Science','url':'https://github.com/alexa/massive'},
        'new_authored':'Assistant agents A/B, synthetic loan-service scenes; no real private records',
        'source_code':{p:sha(ROOT/p) for p in ['src/qwenlab/financial_expansion.py','src/qwenlab/financial_batch_a.py','src/qwenlab/financial_batch_b.py','src/qwenlab/financial_state_pairs.py']}})
    render_reviews(rows)
    atomic_json(OUT/'validation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


def validate(render=False):
    blocked,_,protected=protected_pool()
    audit=json.loads((OUT/'isolation-audit.json').read_text(encoding='utf-8'))
    if protected!=audit['protected_file_hashes']:raise ValueError('Protected evaluation files changed')
    for path,digest in audit['source_file_hashes'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Read-only source changed: '+path)
    rows=read_rows(OUT/'cases.jsonl');result=check(rows,blocked)
    result['cases_match_initial_manifest']=sha(OUT/'cases.jsonl')==json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['cases_sha256']
    if render:render_reviews(rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','validate','render-review'])
    args=parser.parse_args()
    build() if args.action=='build' else validate(args.action=='render-review')
