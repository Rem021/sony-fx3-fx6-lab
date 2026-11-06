# 验证范围与结论

**offline replay passed，未执行任何真实operate动作、未启动VM或浏览器。** 只复制冻结r26离线样本，未接触正在封存的真实任务。本准备不说明原20秒内必能完成人工/agent审阅，也不把真实r26失败改成通过。

- 8例：长观察JSON、固定图、确认成功；child非零、非法JSON、截断JSON、旧current-return残留/空JSON、旧mtime PNG均拒绝且无返回图。实际stdout分别约7.9KB/1.8KB，摘要977–1383字节；完整文件保留。[TEST-RESULT](evidence/TEST-RESULT.json)。
- 首次测试在“空JSON+旧结果残留”发现action缺省status=None被错误当作无图成功；已修为action和status都必须在明确白名单。原失败tests.stderr.txt和case-current_only原件保留；新attempt02目录8例通过，没有覆盖历史。
- 实际functions顶层调用先exec执行一个历史fake child（输出cap8 tokens），再真实Node filesystem读取本次摘要、校验并emitImage，观察截图已显示。[DISPLAY-OBSERVATION](evidence/display-observation.json)。
- 另一真实Node同调用execFile执行一个固定图fake child→loadResult→emitImage，独立640×480固定PNG已显示。[DISPLAY-FIXED-NODE](evidence/display-fixed-node.json)。两次展示都明确fixture_only，不充作语义通过或新VM证据。
- 另对7922字节完整回放stdout加8 token屏幕上限，实际返回显示原1981 tokens被截断；Node直接从完整文件解析成功，未解析该屏幕。[EXEC-TRUNCATION-PROOF](evidence/EXEC-TRUNCATION-PROOF.json)。
- 真实Node逐个loadResult八例，所有失败和确认结果均png=null；对旧成功目录传入非零退出也返回失败/无图，对不存在目录传非零亦成功拒绝，证明失败分支不读旧summary。[NODE-LOAD-NEGATIVES](evidence/NODE-LOAD-NEGATIVES.json)。
- Python生产dispatch spy确认只构造原冻结operate.py固定argv且一次；含shell字符的目标只是一个普通参数，无shell解释。生产CLI不提供fake-child或任意command路径，测试child必须显式fixture环境。
- 生产tool_call.mjs已在真实Node import成功，JS语法/Python编译检查通过；生产模板使用已实测execFile/文件读取/emitImage组合，未在本任务执行原operate，因为没有真实运行授权。

适配器不自动追加任何动作。原child失败自行原End；返回/图片通路失败由操作代理下一明确调用原cleanup/End，原20秒alarm仍兜底，不能以补回包为由重发。

只核用到的源/样本前后哈希及原r26 SHA清单pin，不重跑16/15矩阵或912输入清单。详见INPUTS-BEFORE/AFTER与SHA256SUMS。
