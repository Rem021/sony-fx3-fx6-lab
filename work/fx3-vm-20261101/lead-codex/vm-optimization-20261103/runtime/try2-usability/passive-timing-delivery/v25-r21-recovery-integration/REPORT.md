# FX3 r21 明确未入队恢复工具：离线集成候选

结论：在独立目录从冻结 r18 完整宿主包派生 r21，只有 PAGE/TrialState 替换为已验 r20；runner、guest、QEMU 配置及原清理顺序不变。三原辅助 JS 仅更新 canonical PAGE 指纹，`capture_after.js` 与三 CLI 字节不变。新增仅测试用的 `operator_click.py`、`recovery_tools.py`、只读审阅 JS 与显式取消 JS。**没有启动 VM、部署入口或改旧冻结件。**

## 关键边界

- `FIXED-INPUT-14.json` 对 N64 原 guest/DTB/kernel/Backup/8 个 runtime 基础件、manifest 与冷重载 base 共 14 个固定输入逐个重算 SHA，全部匹配；runner 与 r18 逐字节相同，仍 4 核、5120 MiB、MTTCG/no icount、原 API16/20 秒恢复与退出链。r20 PAGE SHA、r18 runner/源冻结、三辅助旧源码 SHA 均在输入清单。
- PAGE 的 attempt ID、结构化 409 未入队、202 仅入队、unknown 锁定保持 r20 合同。新只读审阅须绑定同一 attempt/nonce/step，截图前后校验原 PAGE/已加载图；不将未入队审阅图误当 accepted 菜单成功。原 first-MENU bounded helper 仍按实际 `review_step=1` 和完整图 SHA 才给 accepted 画面结果。原 explicit confirm 的 handler 和语义未改。
- 显式取消先 fsync 持久预留全轮最多两次、每 step 一次的恢复名额，再执行可能有副作用的浏览器 eval。JS 仅在原 alarm 仍 armed、当前有效已加载图与只读 server GET 一致、本次 r20 资格匹配时调用 `helper.cancel(nonce)`；保存原 helper 回执、matching cancelled event、elapsed<20000 与不变 due。审阅截图变成历史不阻止对旧未入队 alarm 的清理，结果明确 `historical_review_not_current/no_visual_approval`。取消后新截图供另行人工审阅，不能自动点击。
- eval 丢回执、取消后截图失败或进程中断时恢复槽保持 consumed/unknown；ledger 不会返还名额，下一键包装器拒绝继续。该只读 GET 与本地资格是瞬时快照，**不是**服务端锁内原子许可。独占操作员与后续新键再次经过原 server SHA/gen 门不可省。
- `operator_click.py` 只在独立显式调用时通过原 PAGE DOM 按钮发送键，且在 eval 前 fsync 预留 attempt 槽；`lastStatus.steps>=8`、尝试数>=10、任何未解预留或恢复截图未知均拒绝。实际操作员须遵守 `OPERATION.md` 的人眼核图和总预算；脚本不能阻止绕开它直接点网页按钮，故尚未构成实跑验收。

## 离线证据

- `tests/test_cancel_matrix_browser.py`：真实 PAGE + 派生原 deadline 的 5 项取消矩阵通过；本地未 POST 可清旧 alarm，accepted、POST 在途、delivery_unknown、**自然等待原 20 秒到期**均拒绝，实际 cancelled 事件与 key/confirm HTTP 计数存于 `evidence/LATEST-CANCEL-MATRIX.json`。未缩短计时器或伪造 due。
- `tests/test_recovery_browser.py`：真实 Chrome + 实际 r21 PAGE/TrialState/派生原 deadline。明确 409 后审阅 B，再刷新为有效 A，只取消旧 nonce、零 confirm/新键；历史画面标记；随后新的 nonce 与独立 `operator_click` 才多一次 POST。旧图 SHA/gen 的单独包装器调用零 POST；错 attempt/nonce/PAGE 及重复取消拒绝。最终回执路径见 `evidence/LATEST-BROWSER-RESULT.json`。
- 派生三辅助真实 Chrome 8 项通过：旧 PAGE pin 拒绝、新 pin 安装/捕图/原明确确认取消、错 PAGE 拒绝，见 `evidence/LATEST-HELPER-RESULT.json`。这是 host fixture，不代表真实菜单。
- `tests/test_recovery_faults.py`：真实 Python 接线的受控 transport 注入，覆盖取消成功后截图异常、eval 有副作用但回复丢失、调用前预留 fsync、重复同 step/10 attempt/未决恢复预算拒绝。见 `evidence/recovery-faults.json`，含点击 10 次/未决恢复预算拒绝断言。`eval` 副作用与丢回复由受控 mock 模拟，不是实际浏览器网络丢包或 VM 证据。

剩余门：真实操作员亲看新图、同轮最多 8 accepted/10 attempt 的监督执行、未知时实际 End、API16/QEMU/双锁与长期使用均未验。下一轮必须协调端另行授权；现有默认入口不变。
