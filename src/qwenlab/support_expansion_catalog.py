"""Training-only scenario composition. Holdout wording is never a source.

An atom is a business fact/request boundary, not an independent user. Surface
forms and conversation-state variants share the same group and train split.
"""
from copy import deepcopy


def contexts():
    return [
        ('fresh', [], {'pending': None, 'selectedApplicationId': None}),
        ('pending_application', [
            {'role': 'user', 'content': '我想先查看一笔借款的申请详情。'},
            {'role': 'assistant', 'content': '请提供这笔申请的编号。'},
        ], {'pending': 'applicationId', 'selectedApplicationId': None}),
        ('pending_status', [
            {'role': 'user', 'content': '页面的申请状态代码我没弄明白。'},
            {'role': 'assistant', 'content': '请告诉我具体显示的状态码。'},
        ], {'pending': 'statusCode', 'selectedApplicationId': None}),
        ('selected_application', [
            {'role': 'user', 'content': '我刚查了申请48261。'},
            {'role': 'assistant', 'content': '申请48261：金额9000元，状态待审批。'},
        ], {'pending': None, 'selectedApplicationId': 48261}),
    ]


def build_rows():
    rows = []

    def add(group, title, messages, action, intent, tool=None, arguments=None,
            sources=('tools', 'policy'), rationale=None, mode='explicit'):
        for i, message in enumerate(messages, 1):
            for context_name, history, state in contexts():
                e = {'action': action, 'intent': intent, 'tool': tool, 'arguments': arguments or {},
                     'route': {'tool': 'tool', 'answer': 'llm', 'clarify': 'clarify', 'human': 'human'}[action]}
                if mode == 'reference':
                    if state['selectedApplicationId']:
                        e = {'action': 'tool', 'route': 'tool', 'intent': 'application_detail',
                             'tool': 'queryApplicationDetail', 'arguments': {'applicationId': state['selectedApplicationId']}}
                    else:
                        e = {'action': 'clarify', 'route': 'clarify', 'intent': 'application_detail', 'tool': None, 'arguments': {}}
                rows.append({
                    'id': f'{group}-{i:02d}-{context_name}', 'group': group,
                    'card_id': group, 'title': title, 'split': 'train', 'source_ids': list(sources),
                    'message': message, 'history': deepcopy(history), 'state': deepcopy(state),
                    'expected': deepcopy(e), 'rationale': rationale or title,
                    'discussion': None, 'authored_utterance_id': f'{group}-{i:02d}',
                    'augmentation': context_name, 'review': {'status': 'ai_preannotated', 'reviewer': '',
                                                           'notes': '', 'taxonomy_approved': False},
                })

    product_foci = [
        '平台目前开放申请的贷款名称', '所有在售借款产品的额度上限', '上架产品各自的标签',
        '在售贷款对应的受理分门槛', '当前贷款目录里的产品名称和最高金额',
        '工薪贷当前配置的最高额度', '极速贷现在公布的最高借款金额',
        '微企贷在产品目录中的名称和标签', '当前仍然开放申请的贷款目录',
        '不同在售产品的最高金额和受理分设置', '目前上架产品的编号与名称',
        '产品页面公布的额度上限与特点标签', '工薪贷在售版本的受理分要求',
        '极速贷当前展示的产品标签', '微企贷现在设置的最高可借金额',
        '当前借款产品一览表', '平台仍在上架的贷款及其最高额度',
        '在售产品目录中可以公开查看的基础字段', '当前各款贷款设置的产品受理分',
        '目前可浏览的贷款名称、金额上限和标签',
    ]
    lookup_forms = ['麻烦读取{item}。', '我想核对{item}，请查现有记录。',
                    '请把{item}展示给我，不用替我申请。', '现在先看{item}，查好给我即可。',
                    '需要的是{item}的当前记录，不是一般概念解释。', '能否查询{item}并列出来？']
    for i, focus in enumerate(product_foci, 1):
        add(f'EP{i:02d}', '产品实际字段：' + focus, [f.format(item=focus) for f in lookup_forms],
            'tool', 'products', 'queryLoanProducts', sources=('tools', 'seed'))

    applications = [
        '我提交过的全部申请记录', '本账户名下各笔申请的审批阶段', '我当前的贷款申请列表',
        '本人借款申请的编号和申请金额', '我提交的每笔申请分别处于什么状态',
        '我的借款申请记录中列出的产品编号', '我名下已有的申请和各自金额',
        '当前登录账户的申请清单', '我申请记录里能看到的编号与状态', '我在平台留下的借款申请记录',
    ]
    for i, focus in enumerate(applications, 1):
        forms = [f'请调出{focus}，我想自己查看。', f'现在要看{focus}，不是某一笔的详情。',
                 f'麻烦查询{focus}。', f'我想核对{focus}，给我列表就行。',
                 f'先列一下{focus}，不用让我挑单笔。', f'本次查询的对象是{focus}。']
        add(f'EA{i:02d}', '本人申请列表：' + focus, forms, 'tool', 'applications', 'queryMyApplications', sources=('tools', 'orders'))

    credit = ['我在平台已保存的信用分', '本人当前记录的信用评分', '本账户信用资料中的评分分档',
              '平台信用资料里给我的推荐额度字段', '我信用资料中的分数和分档', '平台保存的个人评分与推荐额度记录']
    for i, focus in enumerate(credit, 1):
        forms = [f'读取{focus}，不要重新给我打分。', f'帮我查{focus}的现有值。',
                 f'我想看看{focus}，不是问术语含义。', f'显示一下{focus}，没有记录就说明没有。',
                 f'只查询{focus}，不需要承诺审批金额。', f'我要核实的是{focus}，请读取账户记录。']
        add(f'EC{i:02d}', '信用资料只读字段：' + focus, forms, 'tool', 'credit', 'queryMyCreditScore', sources=('tools', 'credit'))

    details = ['申请金额', '借款期数', '产品名称', '当前审批状态', '填写的借款用途',
               '金额与借款期数', '申请产品和当前状态', '产品名称与借款用途',
               '申请金额与当前状态', '已经记录的基本申请信息', '借款用途和期数', '产品名称与申请金额']
    for i, focus in enumerate(details, 1):
        forms = [f'查看申请62417的{focus}。', f'申请号62417，帮我读取{focus}。',
                 f'编号62417的记录里，{focus}是什么？', f'请查申请62417，我要了解{focus}。',
                 f'我关心申请62417的{focus}，请读实际记录。', f'这次只查申请62417的{focus}，不修改内容。']
        add(f'ED{i:02d}', '指定申请的已有字段：' + focus, forms, 'tool', 'application_detail',
            'queryApplicationDetail', {'applicationId': 62417})
    for code in (0, 1, 2):
        forms = [f'状态码{code}具体表示哪种审批状态？', f'我需要状态码{code}的释义，不是查询列表。',
                 f'请把状态码{code}对应的文字解释给我。', f'页面说申请状态为{code}，这个代码指什么？',
                 f'代码{code}在申请状态字段里如何理解？', f'想核对申请状态码{code}的标准含义。',
                 f'看到状态显示{code}，我想知道它对应什么。', f'只查询状态码{code}对应的解释即可。']
        add(f'ES{code:02d}', '支持的申请状态码', forms, 'tool', 'status_code', 'explainApplicationStatus', {'status': code})

    # Concepts are deliberately not claims about this user's eligibility, fees,
    # interest rate or unknown approval reasons. Reply quality is separate.
    concepts = [
        ('产品额度上限与本人获批金额的区别', 'general'), ('信用分不能直接保证贷款获批的原因', 'general'),
        ('贷款产品与个人贷款申请的区别', 'general'), ('待审批这个文字通常表示的阶段', 'general'),
        ('未通过与待审批的区别', 'general'), ('产品标签与个人审批结果的区别', 'general'),
        ('产品受理分设置和个人最终审批结论的区别', 'general'), ('申请编号的用途', 'general'),
        ('产品编号与申请编号的区别', 'general'), ('信用评分这个概念', 'general'),
        ('平台推荐额度与实际获批额度的区别', 'general'), ('申请金额与产品最高金额的区别', 'general'),
        ('提交申请与审批通过的区别', 'general'), ('补交材料与审核通过的区别', 'general'),
        ('合同约定与客服一般解释的区别', 'general'), ('为什么客服不能保证审批必过', 'general'),
        ('查询申请与修改申请的区别', 'general'), ('查看信用分与重新计算评分的区别', 'general'),
        ('客服为什么要先确定具体申请对象', 'general'), ('为什么不要把登录验证码交给陌生人', 'general'),
        ('为什么查询他人账户需要严格的权限限制', 'general'), ('为什么还款必须由本人确认', 'repayment'),
        ('正常还款与提前还款的区别', 'repayment'), ('借款期数这个词的含义', 'repayment'),
        ('应还款日与实际还款日的区别', 'repayment'), ('本期应还与剩余待还的区别', 'repayment'),
        ('还款计划通常用来记录什么', 'repayment'), ('还款金额与申请金额的区别', 'repayment'),
        ('正常还款时本人确认步骤的作用', 'repayment'), ('还款记录与审批状态的区别', 'repayment'),
        ('还款成功提示与银行实际扣款凭证的区别', 'repayment'), ('提前还款时选择期数的含义', 'repayment'),
    ]
    explain_forms = ['我只是想弄懂{item}，不查个人记录。', '请用容易理解的话说明{item}。',
                     '先给我讲讲{item}，我是在问概念。', '关于{item}，能做个一般性解释吗？',
                     '我不需要现在执行操作，想了解{item}。', '请解释{item}，不要替我预测个人结果。']
    for i, (focus, intent) in enumerate(concepts, 1):
        add(f'EK{i:02d}', '一般知识说明：' + focus, [f.format(item=focus) for f in explain_forms],
            'answer', intent, sources=('policy', 'detail' if intent == 'repayment' else 'tools'))

    instructions = [
        ('自己浏览贷款产品目录', 'general', 'apply'), ('从选产品开始填写申请', 'general', 'apply'),
        ('查看自己的申请列表', 'general', 'orders'), ('打开某笔申请的详情页面', 'general', 'detail'),
        ('从申请详情进入补充材料页面', 'general', 'materials'), ('自己上传补充的收入材料', 'general', 'materials'),
        ('查看个人中心的信用分入口', 'general', 'credit'), ('在申请列表里寻找申请编号', 'general', 'orders'),
        ('打开正常还款的操作入口', 'repayment', 'detail'), ('在申请详情里选择提前还款', 'repayment', 'detail'),
        ('在还款界面确认选中的期数', 'repayment', 'detail'), ('在自己支付前检查还款页面', 'repayment', 'detail'),
        ('浏览申请详情中展示的还款计划', 'repayment', 'detail'), ('在申请详情里查看材料提交记录', 'general', 'detail'),
    ]
    for i, (focus, intent, source) in enumerate(instructions, 1):
        forms = [f'教我怎样{focus}，我自己操作。', f'我想{focus}，只需要告诉我页面路径。',
                 f'请说明{focus}的步骤，不用替我查询或提交。', f'准备{focus}，应该从哪个入口开始？',
                 f'我问的是如何{focus}，暂时不需要读账户记录。', f'能介绍一下{focus}的操作顺序吗？']
        add(f'EN{i:02d}', '页面操作说明：' + focus, forms, 'answer', intent, sources=(source, 'policy'))

    ui_issues = [
        '申请页的提交按钮是灰色的', '点贷款产品的申请入口没有反应', '补充材料页面上传按钮不能点',
        '选择图片以后没有出现上传结果', '个人信用页面一直显示加载中', '申请详情页面打不开',
        '贷款目录页面一片空白', '还款页面的确认按钮不可用', '提前还款页面不能勾选期数',
        '申请表提交时跳出提示但我没记下内容', '查看申请列表时页面报错', '材料上传进度一直不动',
        '点击申请详情返回了空页面', '信用分入口跳转失败', '产品页面没有显示申请按钮',
        '申请页面的选项无法选择',
    ]
    for i, focus in enumerate(ui_issues, 1):
        forms = [f'{focus}，我没看清具体提示，先怎么排查？', f'现在遇到{focus}，需要补充什么信息？',
                 f'{focus}，还不知道发生在哪一步的问题。', f'我发现{focus}，没有截图可以先问我哪些信息？',
                 f'{focus}，我还没记录页面的报错文字。', f'请协助定位：{focus}，原因我不确定。']
        add(f'EU{i:02d}', '界面问题先补证据：' + focus, forms, 'clarify', 'ui_issue', sources=('apply', 'detail', 'policy'),
            rationale='当前只有问题描述，没有页面禁用原因或截图；先追问具体页面/提示，不猜测拒贷原因。')

    for i, focus in enumerate(['金额', '期数', '产品名称', '审批进度', '借款用途', '金额和期数',
                               '产品和状态', '基本记录', '当前审批状态', '填写的用途和期限'], 1):
        forms = [f'帮我读取这笔申请的{focus}。', f'想查那笔的{focus}。',
                 f'给我看看这单的{focus}，不要改内容。', f'我需要那单记录的{focus}。',
                 f'再查询一下这笔的{focus}。', f'这笔的{focus}是什么，查现有记录。']
        add(f'ER{i:02d}', '同问法的对象有无对照：' + focus, forms, 'clarify', 'application_detail', mode='reference',
            rationale='只有服务端已有选中申请才可消解指代；其余上下文先明确单笔对象。')

    for i, messages in enumerate([
        ['刚才那个东西出问题了', '我说不清哪里不对，你先问问我', '就是那个，帮忙看一眼', '有问题了但我没说明是哪一项', '你知道我说的是哪个吗', '有一项不对劲，但我还没说清具体是哪项'],
        ['状态码填什么我还没看清', '页面有个状态代码，但我不知道具体值', '我想问状态码的意思，还没找到代码', '解释那个状态，具体数字我忘记了', '状态代码是什么我暂时说不上来', '我想核对一个状态代码的含义，但还没提供具体值'],
    ], 1):
        add(f'EV{i:02d}', '诉求或字段未明确', messages, 'clarify', 'general' if i == 1 else 'status_code')

    payment_events = [
        '我只付了一次，一期还款却出现两笔相同支出', '银行已扣走还款金额，平台仍显示这期未还',
        '本期实际扣款金额和我确认的金额不一致', '我收到两条同金额还款扣款通知，只确认过一次',
        '已经有还款凭证，但平台账单没有消掉', '正常还款后又被扣了同一期的钱',
        '我没有再次确认付款，账户又少了一笔还款金额', '付款显示失败但银行余额已经减少',
        '同一笔还款收到了两张不同流水号的扣款凭证', '还款已到账却仍被要求再付同一期金额',
        '银行流水与平台还款记录的金额对不上', '我怀疑本期还款被重复扣费了',
    ]
    event_forms = ['{item}，请帮助处理。', '{item}，这件事需要核实。',
                   '现在的情况是{item}，我该怎么解决？', '我遇到{item}，不能只给一般操作步骤。',
                   '{item}，请协助查明实际情况。', '{item}，希望得到进一步处理。']
    for i, focus in enumerate(payment_events, 1):
        add(f'EM{i:02d}', '实际资金争议：' + focus, [f.format(item=focus) for f in event_forms],
            'human', 'payment_dispute', rationale='实际资金记录争议超出现有五个只读工具的处置能力，需要人工核实，不承诺退款。')
    security_events = [
        '账户下出现一笔我从没办理过的借款', '我没有提交申请，却收到一笔贷款申请成功的通知',
        '有人使用我的身份资料办理了借款', '陌生人在未经我同意的情况下登录过我的账号',
        '我没有借过那笔钱，但它出现在我的申请列表里', '验证码已经发给陌生人，之后账户出现异常',
        '冒充平台客服的人拿走了我的登录验证码', '我怀疑自己的账户正在被别人使用',
        '有人拿我的个人资料在平台发起借款', '我发现登录记录不是自己的操作，担心资金安全',
        '我的身份信息被用于一笔未经我确认的申请', '我没进行借款操作，个人账户却多了贷款记录',
    ]
    for i, focus in enumerate(security_events, 1):
        add(f'EF{i:02d}', '已经发生的账户安全疑虑：' + focus, [f.format(item=focus) for f in event_forms],
            'human', 'security', rationale='实际身份或账户风险需要升级处理，不把受害求助当作越权请求。')

    handoffs = [
        '麻烦转接人工客服，我要继续说明问题。', '我想请真人客服来协助这次咨询。',
        '请找工作人员处理，我希望和人沟通。', '希望转人工继续，前面的解释我已经看过。',
        '现在需要人工客服接手这件事。', '请联系工作人员，我有情况需要核实。',
        '我要投诉处理流程，请转人工。', '我对自己的审批结论有异议，想提出申诉。',
        '请安排人工复核我的申请处理过程。', '我希望由人工受理这次正式申诉。',
        '这次我明确要求真人客服，不想继续自动问答。', '我需要工作人员协助处理投诉。',
    ]
    add('EH01', '明确人工或合法申诉请求', handoffs, 'human', 'handoff')
    return rows
