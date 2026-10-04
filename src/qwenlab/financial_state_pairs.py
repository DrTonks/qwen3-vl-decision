"""Matched inputs for checking context use, not an independent benchmark."""
from qwenlab.financial_pilot import base_input, label, make


def rows():
    result=[]
    def pair(name,message,variants):
        for index,(history,target,state,tools) in enumerate(variants,1):
            v=base_input(message,state=state,history=history)
            if tools is not None:v['available_tools']=tools
            target['evidence_paths']=['input.message','input.history','input.state','input.available_tools','input.capabilities']
            r=make(name,'fin-t2-state:'+name,v,target,{
                'kind':'assistant_authored_state_pair_expansion','source':'project_requirements',
                'source_group':'fin-t2-state:'+name,'parent_id':None,'source_split':None,
                'origin':'synthetic','license':'project_authored','author_batch':'coordinator',
                'modification':'Matched current utterance; history or capabilities differ'})
            r['id']=f'FIN-T2-S-{name}-{index:02d}';result.append(r)
    def h(text):return [{'role':'user','content':text}]
    pair('meaning','这行字是什么意思？',[
        ([],label('clarify','没有提供所指文字，需获取原文。',slots=['error_context']),None,None),
        (h('原文是“文件不能为空”，只解释这句话。'),label('answer','已提供原文，可解释需要选择或提供文件；具体含义以界面为准，不推断平台格式或大小限制。'),None,None)])
    pair('detail','那就查一下这笔吧。',[
        ([],label('clarify','没有选定对象或历史编号。',slots=['application_id']),None,None),
        (h('接下来要查的是申请编号81234。'),label('tool','历史给出完整申请编号，可信状态一致，执行仍核验归属。',tool='queryApplicationDetail',arguments={'applicationId':81234}),{'authenticated':True,'application_id':81234},None)])
    pair('latest','我想看最新的。',[
        (h('正在比较你们上架贷款产品目录，昨天存了一份旧的。'),label('tool','明确当前产品目录，需刷新业务记录。',tool='queryLoanProducts'),None,None),
        (h('我问的是平台附件上传的正式规范，手里那版已经过期。'),label('retrieve','明确要求现行平台文档，须检索有效版本。',collection='loan_service_docs'),None,None)])
    pair('handling','这件事帮我处理一下。',[
        (h('有人没经我同意拿我的身份在这申请了贷款。'),label('human','用户是疑似冒用身份的受害者，建议专业人工协助，不声称已转接。'),None,None),
        (h('我想拿室友身份申请，他没有同意，你替我做。'),label('refuse','上下文明确要求协助冒用身份，而非受害者求助。'),None,None)])
    pair('rules','帮我找一下规则。',[
        (h('我问你们借款材料的补交期限，以平台说明为准。'),label('retrieve','平台材料规则属于可用业务文档集合。',collection='loan_service_docs'),None,None),
        (h('我今晚跟朋友玩国际象棋，不知道王车易位怎么玩。'),label('redirect','上下文为棋类游戏规则，正常域外诉求应引导。'),None,None)])
    pair('closing','那就把这个关掉吧。',[
        (h('问题都解决了，我想结束的是本次客服咨询，不是贷款申请。'),label('close','上下文明确当前客服会话已解决并要求结束。'),None,None),
        ([],label('clarify','不知关闭的是页面、会话或业务对象，不执行结束。',slots=['request_details']),None,None)])
    pair('general-or-specific','先解释这个，不要查我的账户。',[
        (h('我问“借款本金”这个一般术语是什么。'),label('answer','一般概念解释不需要账户或平台规则事实。'),None,None),
        (h('我问你们平台对“补交材料时限”这一条到底怎么规定的。'),label('retrieve','不查个人账户并不等于不检索；平台条款仍需正式文档。',collection='loan_service_docs'),None,None)])
    pair('after-thanks','谢谢，不过我还有这个问题。',[
        (h('前面那个问题解决了，另一个问题还没说出来。'),label('clarify','用户明确继续但尚未给出新问题，不结束会话。',slots=['request_details']),None,None),
        (h('另外一个问题是有人冒充你们客服找我要验证码，我已经给了。'),label('human','仍有进行中的账户安全事件，致谢不表示结束，建议人工帮助。'),None,None)])
    pair('authenticate','把我现在留在系统里的信用分给我看一下。',[
        ([],label('clarify','查询本人信息前需要认证。',slots=['authentication']),{'authenticated':False},None),
        ([],label('tool','已登录且评分工具可用，读取已有记录而非生成评分。',tool='queryMyCreditScore'),{'authenticated':True},None)])
    pair('availability','查看一下我提交过的申请列表。',[
        ([],label('tool','本人列表查询工具当前可用。',tool='queryMyApplications'),None,None),
        ([],label('human','个人记录不可从知识库推断；查询能力缺失时按试点政策建议人工协助，未自动接通。'),None,[])])
    return result
