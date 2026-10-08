"""Authored training-only state contrasts; never import evaluation questions."""
from qwenlab.financial_pilot import base_input, label, make


UI = [
    ('材料上传页的提示什么意思？', '请上传PDF文件', '提示指定了PDF这种文件格式。'),
    ('借款按钮下面的提醒是在说什么？', '请先完成实名认证', '提示要求先完成实名认证。'),
    ('验证码输入框的红字能解释一下吗？', '验证码已过期，请重新获取', '提示原验证码已失效，需要重新获取。'),
    ('我这个密码框的提醒是什么意思？', '两次输入的密码不一致', '两次填写的密码内容需要相同。'),
    ('还款页弹出来那句话是什么意思？', '请勿重复提交', '提示不要重复提交同一个请求。'),
    ('我上传照片时显示的文字是什么意思？', '图片无法读取，请重新上传', '提示当前图片未能读取，需要重新上传可读取的文件。'),
    ('职业信息旁边的提醒能解释吗？', '请选择职业类型', '这是要求选择职业类型的填写提示。'),
    ('贷款金额输入框为什么提示红字？', '请输入正数金额', '提示金额应为大于零的数。'),
    ('借款期限那里的文字是在说什么？', '请选择借款期数', '提示尚需选择借款期数。'),
    ('协议页面弹窗那句话怎么理解？', '请阅读并同意协议后继续', '提示继续前需要阅读并确认协议。'),
    ('银行卡页面这条提醒是什么意思？', '银行卡号格式不正确', '它表示所填卡号格式未通过校验；不能据此判断银行卡是否真实有效。'),
    ('联系人表单的提示怎么理解？', '联系人电话不能为空', '提示联系人电话这一项需要填写。'),
    ('这个身份证页面的提示是在说什么？', '姓名不能为空', '提示姓名这一项需要填写。'),
    ('居住地址输入框的提示什么意思？', '请填写详细地址', '提示需要补充详细地址信息。'),
    ('借款用途页面红色文字是什么意思？', '请选择借款用途', '提示需要选择借款用途。'),
    ('登录时弹出的通知是在说什么？', '登录状态已失效，请重新登录', '通知要求重新登录；这不等于账户一定被封禁。'),
    ('申请列表这一行提示能解释吗？', '暂无记录', '当前列表没有显示记录；不能据此推断申请被拒绝。'),
    ('文件选择页面那条提示什么意思？', '文件为空，请重新选择', '选中的文件没有可读取内容，需要重新选择。'),
    ('材料扫描后系统那条提醒什么意思？', '请确保文字清晰可辨', '它要求材料中的文字足够清晰。'),
    ('还款金额旁边的提醒可以解释吗？', '小数位最多两位', '金额输入只允许最多两位小数。'),
    ('设备验证弹窗文字怎么理解？', '正在验证，请稍候', '当前文字表示验证仍在进行；没有提供完成时间。'),
    ('申请页的错误提示意味着什么？', '网络请求失败', '当前请求未能成功完成；单靠这句无法确定是网络还是服务器原因。'),
    ('产品页提示那句话是什么意思？', '服务暂时不可用', '服务当前不可用；原文没有说明恢复时间。'),
    ('个人资料页的提示能解释一下吗？', '保存成功', '提示这次保存操作已收到成功反馈；只解释用户提供的文字。'),
    ('借款详情页那条通知怎么理解？', '信息更新中', '提示信息仍在更新；不代表审核已经完成。'),
    ('提交材料后那句话什么意思？', '已接收材料', '提示材料已接收；接收不等于审批通过。'),
    ('页面为什么有个提示我看不懂？', '未选择任何文件', '尚未选中文件；需要先选择文件。'),
    ('手机号页面的提示能说明吗？', '手机号格式不正确', '输入的手机号格式未通过校验，不代表号码的所属人发生问题。'),
    ('关于浏览器权限的提示怎么理解？', '相机权限未开启', '提示应用目前没有相机权限。'),
    ('定位那条通知是什么意思？', '定位权限未授权', '提示目前未获定位权限；不能把它解释为贷款拒绝。'),
    ('这个表单底部的提醒是什么意思？', '必填项尚未完成', '还有必填内容未完成；原文没有指出具体哪一项。'),
    ('刷新按钮旁的提示什么意思？', '请稍后再试', '提示稍后重试，但未给出具体等待时长。'),
    ('退出页面的弹窗怎么理解？', '未保存的内容可能丢失', '提示离开可能丢失尚未保存的内容。'),
    ('申请材料区那个提示是什么意思？', '文件名包含不支持的字符', '提示文件名中的某些字符未被支持；原文没有列出完整字符规则。'),
    ('借款页面这个确认框什么意思？', '您确定返回上一页吗', '这是确认是否返回上一页，并不是批准贷款的确认。'),
]

DETAIL = [
    '帮我打开刚才说的那份申请明细。', '我想再看一下上一笔申请的金额。',
    '刚刚选中的借款申请现在是什么状态？', '查一下我提到的那个申请用了什么用途。',
    '能再列出那笔申请所选的借款期数吗？', '前面说的那份借款申请对应哪个产品？',
    '我要核对刚才指定那笔申请的全部详情。', '把我们正讨论的那份申请记录查出来。',
    '我只想看刚才标记的申请，不是全部记录。', '能调出之前提到的那笔申请让我核对吗？',
    '这回查看刚才指定的那个申请编号。', '我想核对那一笔申请填的借款金额。',
    '刚才那条申请的信息可以展开吗？', '请重新查询上面提到的申请详情。',
    '看一下我们刚说的那笔申请的借款用途。', '前面指定的申请是否有状态记录？',
    '这次就查我刚刚指的那份申请。', '先确认刚才说的申请记录里有什么信息。',
    '把前文选的借款申请明细带出来。', '我要复核之前指定的单笔申请资料。',
]

AUTH = [
    ('请查本账户保存的信用评分数值。', 'queryMyCreditScore'),
    ('我的当前信用分和评分档位能查到吗？', 'queryMyCreditScore'),
    ('账户里记录的建议额度是多少？', 'queryMyCreditScore'),
    ('我想查看属于我自己的评分记录。', 'queryMyCreditScore'),
    ('系统记下来的我的分值是多少，不要重新预测。', 'queryMyCreditScore'),
    ('读取一下当前账号的信用评分和档位。', 'queryMyCreditScore'),
    ('先告诉我个人评分记录中的建议额度。', 'queryMyCreditScore'),
    ('请列出这个账号已经提交的借款申请。', 'queryMyApplications'),
    ('我想看我的申请列表里有哪些记录。', 'queryMyApplications'),
    ('查我的全部借款申请和列表中的状态。', 'queryMyApplications'),
    ('帮我调取本账户的申请清单。', 'queryMyApplications'),
    ('我提交过哪些贷款申请，先列出来。', 'queryMyApplications'),
    ('请展示本人名下的申请列表，不查询别人的。', 'queryMyApplications'),
    ('当前账户有哪些申请记录及金额？', 'queryMyApplications'),
    ('把已经入库的我的申请编号列出来。', 'queryMyApplications'),
    ('请查询平台当前的贷款产品目录。', 'queryLoanProducts'),
    ('现有借款产品各自叫什么名字？', 'queryLoanProducts'),
    ('想比较当前产品记录里的最高金额。', 'queryLoanProducts'),
    ('各产品目前保存的审批难度分是多少？', 'queryLoanProducts'),
    ('贷款产品资料里的标签都有哪些？', 'queryLoanProducts'),
    ('查一下当前产品列表里的极速贷最高额度。', 'queryLoanProducts'),
    ('我需要实时产品清单里的名称和编号。', 'queryLoanProducts'),
    ('平台现有产品有哪些金额上限？', 'queryLoanProducts'),
    ('帮我读出产品目录里的审批难度分，不要预测通过率。', 'queryLoanProducts'),
    ('工薪贷当前产品记录上的标签是什么？', 'queryLoanProducts'),
]

KNOWLEDGE = [
    ('平台规定借款材料上传需要走哪些步骤？', 'loan_service_docs'),
    ('申请借款前这个平台要求完成哪些认证？', 'loan_service_docs'),
    ('这里正式公布的提前还款办理流程是什么？', 'loan_service_docs'),
    ('平台要求怎样更正提交的个人资料？', 'loan_service_docs'),
    ('本平台有没有说明银行卡信息变更的流程？', 'loan_service_docs'),
    ('这家平台是按什么规则处理申请材料不清晰的问题？', 'loan_service_docs'),
    ('这里借款协议正式公布的查看入口和步骤是什么？', 'loan_service_docs'),
    ('平台隐私政策写的设备信息保存范围是什么？', 'privacy_policy'),
    ('本平台对个人信息查阅申请有哪些官方流程？', 'privacy_policy'),
    ('这里隐私说明有没有规定撤回授权怎样办理？', 'privacy_policy'),
]

UNAVAILABLE = [
    ('请读出我这个账户的最新申请清单。', 'queryMyApplications'),
    ('本账户有哪些申请编号和金额，查一下记录。', 'queryMyApplications'),
    ('我需要核对个人借款申请的列表状态。', 'queryMyApplications'),
    ('查我已有申请清单中的产品编号。', 'queryMyApplications'),
    ('列出我本人提交的申请，暂不新增申请。', 'queryMyApplications'),
    ('当前个人评分档位请帮我从记录里查。', 'queryMyCreditScore'),
    ('读取本账号的信用分和建议额度记录。', 'queryMyCreditScore'),
    ('我要查看已有的本账户评分数值。', 'queryMyCreditScore'),
    ('请核对本人信用评分记录对应的档位。', 'queryMyCreditScore'),
    ('本账户现存的推荐额度记录帮我查询一下。', 'queryMyCreditScore'),
]


def rows():
    out = []
    def add(family, value, target):
        target['evidence_paths'] = ['input.message', 'input.history', 'input.state',
                                    'input.capabilities', 'input.available_tools']
        r = make(str(len(out)+1), 'financial-release-v1:core:' + family, value, target,
                 dict(kind='assistant_authored_state_contrast', source='project_requirements',
                      parent_id=None, source_split=None, license='project_authored',
                      origin='synthetic', producer='root',
                      modification='Authored wording with controlled visible state/capability contrast.'))
        r['id'] = f'FIN-TR1-C-{len(out)+1:04d}'
        out.append(r)
    for i, (msg, original, explanation) in enumerate(UI):
        family = f'ui-{i+1:02d}'
        add(family, base_input(msg, {'authenticated': bool(i % 2)}),
            label('clarify', '所指文字或报错原文尚未给出，先补充原文，不猜测原因。', slots=['error_context']))
        history = [{'role': 'user', 'content': f'页面原文是“{original}”。我只想理解这句文字的含义。'}]
        add(family, base_input(msg, {'authenticated': bool(i % 2)}, history),
            label('answer', '可见原文足够做一般释义：' + explanation + ' 不编造账户事实或平台规则。'))
    for i, msg in enumerate(DETAIL):
        family, number = f'detail-{i+1:02d}', 86231+i
        add(family, base_input(msg), label('clarify', '没有可见历史或指定申请编号，无法确定单笔查询对象。', slots=['application_id']))
        history = [{'role': 'user', 'content': f'本次指定的申请编号是{number}。'},
                   {'role': 'assistant', 'content': '已收到您指定的编号；查询仍会校验是否属于当前账户。'}]
        add(family, base_input(msg, {'authenticated': True, 'application_id': number}, history),
            label('tool', '输入历史与可信选择状态一致，调用单笔只读查询；服务端仍须校验记录归属。',
                  tool='queryApplicationDetail', arguments={'applicationId': number}))
    for i, (msg, tool) in enumerate(AUTH):
        family = f'authentication-{i+1:02d}'
        add(family, base_input(msg, {'authenticated': False}),
            label('clarify', '当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。', slots=['authentication']))
        add(family, base_input(msg, {'authenticated': True}),
            label('tool', '已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。', tool=tool))
    for i, (msg, collection) in enumerate(KNOWLEDGE):
        family = f'knowledge-{i+1:02d}'
        value = base_input(msg, {'authenticated': bool(i % 2)})
        add(family, value, label('retrieve', '未知平台规定应通过模拟可用的正式文档集合核实；本训练不表示检索服务已上线。', collection=collection))
        value = base_input(msg, {'authenticated': bool(i % 2)})
        value['capability_profile'] = 'current-no-kb-v1'
        value['capabilities']['knowledge_collections'] = []
        add(family, value, label('answer', '没有可用文档或规则事实；只如实说明暂无法核实并指向正式渠道，不编造细则或声称已检索。'))
    for i, (msg, tool) in enumerate(UNAVAILABLE):
        family = f'query-capability-{i+1:02d}'
        add(family, base_input(msg), label('tool', '本人已认证且白名单工具可用，可以只读查询当前账户记录。', tool=tool))
        value = base_input(msg)
        value['available_tools'].remove(tool)
        add(family, value, label('human', '所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。'))
    return out
