# 未来真实VM操作模板（本任务不执行）

由协调端核验候选后另行授权一次完整8步VM。使用prepare_run.py创建全新task后缀run目录；导出FX3_NAV_RUN_DIR。CLI-TEMPLATES.json记录本r26绝对路径和环境，先执行实际preflight，部署/launch仍需本次之外的统一运行授权。

启动与初始待机步骤沿用原r25：launch_prepare、start_and_wait、实际查看initial-standby新图、operate.py standby_review。

每个固定计划step按以下独立工具调用，不把人工/agent看图时间省略：

1. operate.py click STEP 原计划目标。只点击一次原PAGE；accepted后返回第1张尚未固定的观察PNG，检查返回status为qualified_unpinned_postkey_observation。
2. 实际查看本次返回PNG。若只是合法过渡且尚未耗尽3张/20s，可另一次调用operate.py observe 填实际过渡判断；实际查看新PNG后再决定。禁止自动轮询直到SHA命中、自动补键或等待后暗中点击。
3. 看到目标完整后，另一调用operate.py pin 填上一观察已完整的明确选择。这一步才调用原PAGE pin并返回qualified_review_snapshot及新的精确PNG。
4. 必须重新实际查看新固定PNG。若符合目标，再另一调用operate.py confirm 填该固定PNG的具体语义判断。若不符/不确定，operate.py reject 填原因，原End；不再observe/repin。
5. 原精确确认且原nonce取消成功后，才可下一固定计划step。

原20秒从click前arm开始，覆盖等待native/界面、所有工具、模型审阅、observe、pin和confirm；不能重置。超过3次观察、任何未知/错误/身份变更/End都停止本轮，不可凭后续新帧复活。最后第8步也必须真实固定图审阅和精确confirm，8accepted本身不算通过。

若click返回qualified_recovery_observation，仍先实际看该未入队恢复图，再独立recovery_cancel；返回另一取消后恢复图，实际看后再独立recovery_review，然后另一次click新nonce。它不是postkey确认，不能跳到pin/confirm。

各步骤目标和键码完全沿用NAVIGATION-PLAN.json；不得增加8accepted/10attempts/2recoveries每步一次预算。收尾原cleanup/audit_after和独立PID/port/锁核验照旧；失败保持失败，不追溯补确认。
