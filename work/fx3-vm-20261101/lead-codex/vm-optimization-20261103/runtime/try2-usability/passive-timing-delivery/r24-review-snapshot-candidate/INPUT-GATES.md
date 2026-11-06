# 输入门逐项保留对照

| 门 | r24实现 |
|---|---|
| 七键白名单、整数key、100ms和步骤顺序 | 原TrialState.submit、InputGate/valid_command及runner原调用不变 |
| observed sequence为整数且在原64项cache | 原submit继承；新审阅对象不替代输入cache |
| 有当前有效frame、SHA和content_generation相等 | 原submit三个条件保留；A→B→A照旧增代，历史快照确认不豁免 |
| stop/error/stopping/finished | 原submit及runner全部原生错误分支保留；同时撤销审阅对象 |
| ready/busy/pending/review_required、原configured limit | 原submit继承全部条件，r23 planned 8步/10attempt及各条件保留 |
| PAGE按键前loaded、step、lifecycle、busy/review/unknown及点击frame固定 | 原key handler异步GET及POST判断保留；额外加document_id及sticky review unknown/终态阻挡 |
| 单tab、exact URL、launch、document incarnation、plan/前步confirm、新nonce | r23 planned helper保留；仅更新新PAGE指纹并精确消费r24历史schema |
| 原20秒deadline | 只适配新PAGE指纹/确认文案；计时、原End、nonce、不延长/不重arm均不变；新helper恢复version/URL/launch/sealed全部显式断言 |
| Host/token/Origin/请求格式 | 原端点继承；新pin/abort端点同样校验，原PNG快照GET另需本会话token和匹配document |

刻意改变的只有**后置确认对象**：确认指定的已绑定PNG，不再要求它等于当前实时PNG/gen或live image loaded。确认不入队、不写guest；下一键仍独立通过以上全部实时门。固定图与live图分开展示，不设两SHA白名单、掩码、暂停guest或等待动画回到SHA自动确认。
