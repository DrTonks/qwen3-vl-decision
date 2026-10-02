"""Author and freeze new synthetic episodes before any candidate scoring."""
import argparse
from collections import Counter
import difflib
import json
from qwenlab.common import ROOT, input_state, load_json, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.support_curriculum import normalize

OUT=ROOT/'data/support-fresh-holdout-v1'
TOOLS=['queryLoanProducts','queryMyCreditScore','queryMyApplications','queryApplicationDetail','explainApplicationStatus']


def catalog():
    rows=[]
    def group(route,intent,texts,tool='none',history=None,state=None,available=None,note=''):
        number=len(rows)//2+1
        for j,text in enumerate(texts):
            rows.append({'id':f'NEW-{number:03d}-{j+1}','group':f'NEW-{number:03d}',
                'dataset':'business','split':'fresh_evaluation','message':text,'history':history or [],
                'state':{'authenticated':True,**(state or {})},'available_tools':TOOLS if available is None else available,
                'labels':{'intent':intent,'route':route,'tool':tool,'needs_human':'yes' if route=='human' else 'no'},
                'label_status':'assistant_drafted_pending_independent_agent_review_not_human_reviewed',
                'usage':'evaluation_only_never_train','scenario_note':note})
    # Sixteen tool episodes, two independently worded variants each.
    group('tool','products',['刚把旧手机换掉，想重新浏览目前还在售的借款方案。','之前收藏的项目找不到了，给我当前可以查看的贷款产品目录。'],'queryLoanProducts')
    group('tool','products',['现在营业的借款品种都有哪些？先给目录，别替我申请。','请把平台现售的产品列出来，我打算逐个了解。'],'queryLoanProducts')
    group('tool','products',['家里准备比较借款方案，我先要本平台最新的在售清单。','不沿用我去年看过的名单，请重新查询现在上架的贷款种类。'],'queryLoanProducts')
    group('tool','credit',['我只想核对账户里的信用评分数值，麻烦读取现有记录。','帮我取一下登录账户当前的信用分记录，不需要重算。'],'queryMyCreditScore')
    group('tool','credit',['上回查分已经很久了，这次请从账户记录重新读取信用分。','登录完成了，想知道我的信用评分目前具体是多少分。'],'queryMyCreditScore')
    group('tool','credit',['产品先不看了，换成查我账户的信用分。','刚才说错项目了，我现在要查询的是本人信用评分。'],'queryMyCreditScore',history=[{'role':'user','content':'我想看看借款产品。'},{'role':'assistant','content':'可以帮您查询产品目录。'}])
    group('tool','applications',['把我账号里全部借款申请整理成清单，想对一下有没有漏掉的。','帮我重新读取本人提交过的借款申请列表。'],'queryMyApplications')
    group('tool','applications',['请看看我名下哪些申请还在处理中，先列出申请记录。','登录后想逐笔查看自己的审批进度，先给我申请清单。'],'queryMyApplications')
    group('tool','applications',['昨天的清单可能旧了，重新取一次我的全部申请记录。','别复用昨天那份列表，我需要刚查询出来的本人申请清单。'],'queryMyApplications')
    group('tool','application_detail',['申请号64231这一单的明细能调出来吗？','麻烦查看编号64231的本人借款申请详情。'],'queryApplicationDetail',state={'application_id':64231})
    group('tool','application_detail',['我说的是编号73524那单，不是刚刚那笔，重新查它的详情。','对象更正为申请73524，请取这份申请的具体记录。'],'queryApplicationDetail',state={'application_id':73524},history=[{'role':'user','content':'刚刚查看的是申请64231。'},{'role':'assistant','content':'您可以继续指定申请编号。'}])
    group('tool','application_detail',['申请86412的金额是两千元，请查询该申请的明细。','2026年9月提交的86412这笔申请，我想核实具体详情。'],'queryApplicationDetail',state={'application_id':86412})
    group('tool','application_detail',['申请59273，我已经提供编号了，看看这笔为何没有通过。','要查询的是申请号59273，读取记录里写的审批结果。'],'queryApplicationDetail',state={'application_id':59273})
    group('tool','status_code',['审批记录写着状态码0，请按平台定义说明它。','这里显示的是申请状态0，帮我查询这个编号代表什么。'],'explainApplicationStatus',state={'status_code':0})
    group('tool','status_code',['我更正之前的说法，现在只问状态码1具体是什么意思。','更正刚才的信息：申请状态码是1，请解释它。'],'explainApplicationStatus',state={'status_code':1},history=[{'role':'user','content':'原以为看到状态码0。'},{'role':'assistant','content':'请确认需要解释的状态码。'}])
    group('tool','status_code',['申请页明确标了状态码2，请给出平台对此代码的解释。','我只问申请状态2的含义，不是在问申请编号2。'],'explainApplicationStatus',state={'status_code':2})
    # Sixteen clarification episodes. No authentication-false inputs enter live classifier validation.
    group('clarify','application_detail',['上个月那份借款申请具体怎么处理的？我暂时没找到申请编号。','我想读一笔申请的详细记录，但现在手边没有它的编号。'])
    group('clarify','application_detail',['想看被退回那单的明细，我有好几笔，不记得是哪一个编号。','能说明我其中一份未通过申请的原因吗？还没确认具体是哪笔。'])
    group('clarify','application_detail',['要查我手机上标记的那一单，但编号还没有贴给你。','请调出我选中的申请明细，具体申请号待会儿再补。'])
    group('clarify','application_detail',['先查64231或73524中的一个，我还没决定查哪笔。','我提到了申请64231和73524，暂时不能确认要查哪一个。'])
    group('clarify','status_code',['页面写状态码9，是不是等于审核通过？','申请状态出现9这个数，请解释，别猜成其他代码。'])
    group('clarify','status_code',['表格里有状态码负一，请问它在这里对应什么？','申请状态显示-1，平台支持解释这个编号吗？'])
    group('clarify','status_code',['我忘了界面上的状态数字，只知道有个状态栏，帮我解释。','想知道申请状态码的意思，可我还没把具体代码告诉你。'])
    group('clarify','status_code',['我在两个截图里看到了状态码0和1，还没确定问哪张。','状态码1还是2我没看清，现在不能确认具体的数值。'])
    group('clarify','ui_issue',['页面有个控件点不动，我还没说明在哪个界面。','手机上一处按钮无法点击，位置和名称暂时想不起来。'])
    group('clarify','ui_issue',['我这边点一个入口没有反应，但尚未提供页面位置。','有个页面按钮不可用，截图还没发，先帮我确认需要补哪些信息。'])
    group('clarify','ui_issue',['已经打开产品详情页，申请按钮不可点，我没看到原因提示。','在借款产品详情界面操作不了申请，尚不清楚禁用原因。'])
    group('clarify','ui_issue',['申请表页面的下一步按不了，我还没检查必填项目。','贷款申请表填到一半，继续按钮无响应，原因提示尚未确认。'])
    group('clarify','general',['我想让你处理那个事项，但暂时没有具体问题描述。','刚才准备问点事情，具体要办理什么还没表达清楚。'])
    group('clarify','general',['我的问题就是那个，前面没有说过是哪件事。','你先看看这件情况，至于指哪件我还没说明。'])
    group('clarify','application_detail',['还是想找那份申请，可查询结果说不存在，我也不确定号有没有写错。','刚才按号没查到记录，先别断定被拒，我还需要核对申请对象。'],history=[{'role':'assistant','content':'只读查询结果：status=not_found，未找到您本人的对应申请。'}])
    group('clarify','application_detail',['我目前只知道借了一千五百元，还没找到申请编号，请看明细。','申请金额是1500元，但金额不是申请号，我要查的编号还缺着。'])
    # Sixteen answer-model episodes: common knowledge or explicit, sufficient facts.
    group('llm','repayment',['等额本金这种还款方式的大概原理是什么？只讲概念。','不用查我的账户，解释一下等额本金每期构成的基本意思。'])
    group('llm','repayment',['请用普通话说明提前还款和正常到期还款的区别，不针对具体合同。','我只了解还款的通用概念：提前结清通常指什么？'])
    group('llm','repayment',['把还款计划里的本金和利息分别解释一下，不需要查账单。','一般还款计划为什么会分别写本金、利息两项？'])
    group('llm','repayment',['到期还本和分期偿还的概念有什么区别？','我不查询个人记录，只想理解按期分批还款是什么意思。'])
    group('llm','repayment',['还款日前准备核对哪些常见事项？先给通用提醒即可。','不用看我的真实账单，说说按时还款前通常要检查什么。'])
    group('llm','repayment',['还款计划中的剩余本金是怎样一个概念？','只介绍术语：计划表上写的未偿本金指的是什么？'])
    group('llm','general',['客服对话里的只读查询是什么意思，为什么不能直接改记录？','可以解释一下只读工具与修改业务数据的操作有什么区别吗？'])
    group('llm','general',['先介绍一下客服通常能提供哪些类型的帮助，不查个人信息。','我刚来这里，想先听听客服查询和解释服务的基本范围。'])
    group('llm','general',['谢谢你的说明，内容我已经记到笔记里了。','刚刚的解释已经记下，感谢你的帮助。'])
    group('llm','general',['中午好，我来打个招呼，还没有具体查询要求。','你好呀，暂时没有要查的数据，先问候一下。'])
    group('llm','general',['我希望接下来的解释用短句，先确认你明白这个偏好。','后面请少用专业词，先确认收到这个表达偏好就好。'])
    group('llm','general',['先说明你不能承诺审批结果这一点，我不要求你作保证。','请解释客服为什么不能保证借款申请一定通过。'])
    group('llm','applications',['依据刚才完整查回的空清单，说明我现在没有申请记录即可。','刚才最新查询已经确认列表为空，直接解释这个结果，不要再查。'],history=[{'role':'assistant','content':'本人申请列表只读查询成功：status=ok，complete=true，fresh=true，items=[]。这是刚刚取得的完整结果。'}])
    group('llm','application_detail',['请只解释刚才查到的这笔申请金额是一千元这个事实，不需要重新查。','记录里已明确写了借款金额1000元，帮我用一句话复述这个已知信息。'],state={'application_id':64231},history=[{'role':'assistant','content':'刚刚查询本人申请64231成功，status=ok，complete=true，fresh=true；记录金额为1000元。'}])
    group('llm','credit',['根据刚刚查回的620分，直接告诉我分数是多少就行。','不用再次查分，把已有记录中的620分复述给我。'],history=[{'role':'assistant','content':'本人信用分查询成功，status=ok，complete=true，fresh=true，score=620。这是当前完整记录。'}])
    group('llm','general',['今天心情挺轻松，我没有贷款业务要办理，只想寒暄一句。','我暂时不办理业务，随口问候一声，祝工作顺利。'])
    # Sixteen human episodes span contract-defined risk/escalation categories.
    group('human','handoff',['希望这件事由真人客服接手，请替我联系人工。','请安排一位人工专员继续和我沟通。'])
    group('human','handoff',['我不想继续自动问答了，麻烦转给人工服务人员。','请把本次咨询升级到人工渠道，我需要真人处理。'])
    group('human','security',['收到借款提醒但我根本没提交过，怀疑身份被别人冒用了。','名下多出不属于我的借款申请，我担心有人冒用身份。'])
    group('human','security',['有陌生人诱导我把验证码交给他，我担心账户安全。','刚把短信验证码告诉了自称客服的人，现在觉得可能被骗。'])
    group('human','security',['手机遗失后账户出现我不认识的操作，想马上让安全人员处理。','丢手机之后发现借款账户有异常操作，需要人工核查安全情况。'])
    group('human','security',['有人声称缴保证金就能解冻贷款，这听起来像诈骗，想核实。','对方让我先汇解冻费才放款，我怀疑遭到诈骗，需要人工介入。'])
    group('human','payment_dispute',['银行已经显示还款成功，可平台仍向我收取同一笔欠款，我有争议。','我已还款并有成功凭证，系统却说这笔还没付，请人工核账。'])
    group('human','payment_dispute',['实际扣走的金额大于账单约定，我对这笔扣费提出异议。','还款扣款数额与应还账单不一致，我需要处理扣费争议。'])
    group('human','payment_dispute',['明明撤销了扣费授权却仍被划款，这笔款项我不认可。','我不认可账户里这笔还款扣款，需要人工受理争议。'])
    group('human','payment_dispute',['还款成功的凭证和平台欠款余额对不上，我要申诉核账。','对这次实际还款与账单余额的差异有异议，请转账务人工。'])
    group('human','handoff',['我正式投诉这次服务，希望转交投诉处理人员。','这次沟通让我很不满意，请升级投诉并由人工受理。'])
    group('human','application_detail',['请把申请64231的审批结果直接改为通过，我知道这不是查询。','我要求你改动申请73524的审批结果，不只是查看它。'])
    group('human','applications',['我想核对自己名下提交过哪些借款申请，请读取一份列表。','请重新列出我账户所有借款申请，我需要核对提交记录。'],available=[])
    group('human','credit',['我打算核实一下本人账户现在记录的信用评分。','想知道这个已登录账户的信用分数，麻烦查询一下。'],available=['queryLoanProducts'])
    group('human','ui_issue',['页面申请故障按普通步骤排查后仍未恢复，页面记录仍和后台冲突。','刷新、重新登录和核对资料都试过了，申请界面仍报同一错误。'],history=[{'role':'assistant','content':'普通排查已经结束但未能修复；页面与后端记录仍冲突。'}])
    group('human','applications',['刚才那次失败重试后仍超时，别再重复查了，帮我处理这个问题。','本人申请列表查询已经重试一次仍失败，这个查询问题还没有解决。'],history=[{'role':'assistant','content':'queryMyApplications只读工具返回status=timeout，retry_count=1，重试后仍超时。'}])
    assert len(rows)==128 and Counter(r['labels']['route'] for r in rows)==dict.fromkeys(['tool','clarify','llm','human'],32)
    return rows


def prepare():
    rows=catalog()
    old_paths=list((ROOT/'data/processed/support-v8').glob('*.jsonl'))
    old_paths += list((ROOT/'data/support-curriculum-v2-reviewed-01').glob('*candidates.jsonl'))
    old_paths += [ROOT/'data/processed/v4/business-train.jsonl',ROOT/'data/processed/v5/business-train.jsonl',ROOT/'data/processed/v5/business-test.jsonl',ROOT/'data/processed/v5/business-calibration.jsonl']
    old=[r for p in old_paths for r in read_rows(p) if r.get('dataset')=='business']
    existing={normalize(r['message']) for r in old}
    keys={json.dumps(input_state(r),ensure_ascii=False,sort_keys=True) for r in old}
    conflicts=[r['id'] for r in rows if normalize(r['message']) in existing or json.dumps(input_state(r),ensure_ascii=False,sort_keys=True) in keys]
    if conflicts: raise ValueError('Existing exact/normalized inputs: '+str(conflicts))
    near=[]
    texts=sorted(existing)
    for row in rows:
        text=normalize(row['message'])
        matches=difflib.get_close_matches(text,texts,n=1,cutoff=.78)
        if matches:
            near.append({'id':row['id'],'similarity':difflib.SequenceMatcher(None,text,matches[0]).ratio(),'message':row['message'],'old_normalized':matches[0]})
    if OUT.exists() and (OUT/'freeze.json').exists():
        raise FileExistsError('Dataset frozen; do not rewrite after scoring')
    OUT.mkdir(parents=True,exist_ok=True)
    write_rows(OUT/'cases.jsonl',rows)
    atomic_json(OUT/'overlap-audit.json',{'old_files':{p.relative_to(ROOT).as_posix():sha(p) for p in old_paths},
        'exact_or_normalized_matches':conflicts,'near_matches_for_review':near,'threshold':.78,
        'limitation':'String checks do not prove semantic or source independence; categories intentionally overlap the same business policy.'})
    atomic_json(OUT/'manifest.json',{'rows':128,'groups':64,'routes':dict(Counter(r['labels']['route'] for r in rows)),
        'origin':'assistant-authored synthetic episodes; not real customer data',
        'review':'pending independent agent review; not human-reviewed','new_inputs_before_scoring':True,
        'model_frozen_before_authoring':'.local/checkpoints/support-v8-observe/step-2801',
        'policy_sha256':sha(ROOT/'configs/decision-v5.json'),'known_limitation':'Author has seen previous experiments; not external blind data.',
        'no_training':True,'jev_new_requests':0})
    print(json.dumps({'rows':len(rows),'near_matches':len(near)},ensure_ascii=False))


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare']);p.parse_args();prepare()


if __name__=='__main__': main()
