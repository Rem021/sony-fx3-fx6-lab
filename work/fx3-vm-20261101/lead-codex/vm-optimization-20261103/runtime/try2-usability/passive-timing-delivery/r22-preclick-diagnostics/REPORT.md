# r22：点击前拒绝诊断候选与动态画面评估

**offline candidate passed；runtime/menu 待验。** 最终 17 个针对性离线场景通过，未启动 VM、未部署。本候选只能让下一次拒绝可归因，不能把动态待机画面变成可用的跨工具审阅流程，也不修复已失败的 r21c。

## 范围与交付

卷 UUID 已核为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；Mac 根非 Git。仅写本新目录；冻结 r21、原收尾目录、ledger、PAGE/server、部署入口和 FX3 平台不变；无新 guest、相机/USB/SD/FX6 操作。

- `operator-helpers/operator_click.py`：由冻结 r21 最小派生，保持原 CLI 参数、10 次显式预算、8 步门、白名单、独占锁和 reservation-before-eval/fsync；回执可记新类型。
- `operator-helpers/operator_preflight.js`：提取原内联 JS，拆分原条件与原 key 可用检查，保存有名 `checks/failed_checks` 和同一同步片段的诊断快照。
- `operator-helpers/recovery_tools.py`：仅为 `check/call` 提供原样依赖，字节与冻结原件一致；本候选不调用其恢复操作。
- `MINIMAL.diff`、`INPUTS-BEFORE.json` / `INPUTS-AFTER.json`、`INPUTS-VERIFICATION.json`、`SHA256SUMS`；原始定向回执在 `evidence/`，历史测试回执保留于 `evidence-attempt1/2/`。

## 判定与未知边界

摘要 await 前只保存文档、timeOrigin、script 对象和原脚本文本身份；摘要完成后重新检查这些身份未变，随后**一个无 await 的同步片段**读取判定字段、记录 decision，并选择返回或恰调用一次原 `b.click()`。快照含 page/document/launch、phase、ready/busy/review、steps、各阻塞标志、loaded/status/reviewed SHA+generation、sequence、nonce/armed/due/now、key availability；不含 token、脚本文本、页面私密正文或原始异常文本。

- `preflight_not_clicked`：仅在身份可信、明确失败谓词、控制流返回于 `b.click()` 之前时成立。Python 还核对完整检查字段集、失败项集合、launch/key/nonce/审阅输入/PAGE 摘要绑定；不依赖 JSON object 的键顺序。
- `click_invoked`：只证明调用一次原 PAGE 按钮并取得原 attempt 绑定，**不等于 server accepted、guest 收键或菜单成功**。原 PAGE 的异步预检和 server SHA/generation gate 继续独立判断。
- 身份变化、抛异常、回包丢失、非对象/畸形/不匹配回包、点击后异常全部 `unknown`；即使某离线注入实测 0 POST，生产端也不借此降格 unknown。非对象回包不再在 reservation 收尾处二次 `.get` 崩溃。
- 原 `now >= due` 拒绝门保留，并显式拒绝非有限 due；20 秒计时、timer、nonce 不改。known no-click 仍阻断后续尝试并结束，不取消 alarm、不恢复、不重发。

一致性仅覆盖该浏览器同步 JS 执行片段，**不跨 await，也不覆盖 server/guest 或人的视觉判断**。MDN 的 job run-to-completion 说明同一 job 不会被另一个 job 交错，promise/await 会形成后续 job；由此不能推出整个 async 函数或 HTTP/guest 原子性。[MDN 官方执行模型](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)（2026-11-04 回读）。

## 针对性验证

`python3 -B test_targeted.py`；fixture 自建 2×2 PNG、实际冻结 r21 PAGE/TrialState、独立 Chrome session `fx3-deadline-r22-c83d4bcb5872`，没有真人看图声明或 VM 行为证据。PAGE canonical SHA 仍为 `f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab`。

| 场景 | 最终判定 | DOM click / key POST / pending |
|---|---|---|
| 审阅 generation 过期、审阅 SHA 过期、render 未 loaded、busy+review、nonce 错、due 过期、key disabled、digest await 中 busy 改变（8 项） | preflight_not_clicked | 各 0 / 0 / 0 |
| 完全匹配 | click_invoked | 1 / 1 / 1，原 server accepted |
| 原 PAGE 预检后、submit 前切换 generation | click_invoked | 1 / 1 / 0，原 server 409，SHA+gen 两门拒绝 |
| digest await 中 script 身份改变 | unknown | 0 / 0 / 0 |
| b.click 调用原按钮后同步异常 | unknown | 1 / 1 / 1 |
| host transport：eval 前异常 / 执行后丢失回包 | unknown / unknown | 0 / 0 / 0；1 / 1 / 1 |
| JSON null 回包、foreign 绑定、缺失检查字段（3 项） | unknown | 各 0 / 0 / 0，receipt/ledger 完整收尾 |

每个 eval 入口核对已持久 reservation 为 reserved_unknown；每个 known no-click 还断言第二次尝试被原预算门拒绝、alarm 仍 armed。`evidence/server-submit-trace.json` 保留 server 原返回；各场景保存完整候选 receipt、ledger、PAGE attempt、server rejection snapshot。

初次 fixture 的离线 canonical hash 断言误删了原脚本首尾换行，尚未启动浏览器即失败，已改按原字节计算。随后多失败项回包暴露 agent-browser 对 object 键排序的问题，候选已改按唯一失败项集合比对；并修正 fixture 人工 busy 残留的等待方式。`evidence-attempt1` 保存该失败；`evidence-attempt2` 是修后 16 项通过记录；最终收紧 schema 字段集并增加缺项回包用例后，17 项通过，见 `evidence/RESULT.json`。没有重跑 145 项集成回归。

自有服务线程停止、端口关闭、browser daemon 及其 11 个子进程全消失；外层再次核服务 PID、12 个 browser PID 和 port，见 `evidence/FINAL-CLEANUP.json`。关闭自有文档回收测试 alarm，未调用 cancel/dispose、未延长计时。

## 动态待机画面：当前跨工具流程没有可用窗口

只读 r21c 既有 `traffic.har`，提取 ready 阶段 22 次 status GET：`00:17:22.337860096Z` 至 `00:17:30.901103872Z`，可见 generation 8→20，共 12 次变化，两种 PNG SHA 反复出现。**新 generation 首次观测间隔**最小 0.403926 秒、中位 0.405826 秒、最大 1.618827 秒；它是约 0.4 秒轮询下的观测，不是精确发布周期。内部 generation 的轮询夹逼寿命上界约 0.809–2.024 秒；边缘代际截断，不能据此概括所有未来画面。原始行、变化边界及算法在 `evidence/HAR-ANALYSIS.json` / `analyze_har.py`。

已审 gen9/seq38/SHA2914… 在 HAR 只有一次 GET 样本，它的两个相邻代际轮询夹逼窗口约 0.809 秒。`capture-result.host_ns=421528400576541` 到 `ledger reservation.host_ns=421536657368333` 为 **8.256791792 秒**，跨过 gen10…20；此为同 host 时钟工具边界间隔，不是纯模型思考时间，模型接图/看完时刻未知。相同 SHA 返回到 gen19 也不能复活 gen9 审阅。

因此，在该段实测数据及该工具延迟下，“静图返回→跨工具审阅→严格同 generation 再点击”没有可复用窗口；多开 VM 或重复同一盲跑不能修复这个时序。紧邻 HAR 的 gen20 ready 状态支持 freshness 失配推测，**不能证明 eval 瞬间 DOM 或原合并 if 的具体失败项**。r21c 原结果仍是 failed、unknown reservation；本候选不追溯改判 known。

## 建议下一步：改为同一实时页面内的直接视觉操作合同，先离线验证

最小、无需放宽 server gate 的实用路线是：**由能连续亲看实时原 PAGE 的操作者，在该页面直接点击原按钮，并在原页面完成每键后的视觉确认；消除静图返回与下一次工具命令间 8.26 秒往返。** 原页面在 click handler 第一处 await 前固定当时已加载帧、nonce、key/step；用该逐次绑定回执及紧邻的当前图作为点击归属证据。保持原 PAGE/server SHA+generation 门、20 秒、每键真实视觉审阅与 unknown 即 End；拒绝时也不偷偷重发。这条路线面向真实交互，不能冒称现有静图模型已经具备流式视觉能力，也不保证任意本地点击必被接受。

需要另外批准的新宿主验收合同是：将**测试自定的“operator helper 的 reviewed_generation 必须等于数秒前工具静图 generation”**，改为**同一实时页面亲看并直接操作，绑定原 PAGE 在点击时实际加载的帧**。替代证据应包括独占文档身份、连续可见画面/明确操作者动作及 click-time attempt/frame/nonce、原 server 回执和键后真实视觉确认；单靠 `ready/steps/hash` 或事后抓一张图不足。人工与流式视觉工具的审阅来源必须明确记录；当前跨工具模型不能用“拿最新 generation”代替看新图。

风险：本地人/流式工具仍可能对变化滞后；click 后 server 再变仍会 409，HTTP 后至 guest 消费的原生上下文缺口也仍存在。已经阅读 `../input-context-review/REPORT.md`：两张待机图同义、两 SHA 白名单、掩码 bbox、稳定 steps/ready 均不构成普遍按键安全或原生 input-context 证明，不能据此放宽门。若必须坚持现有静图代理全自动跨工具审阅，这条合同不能直接沿用；需具备可审计的低延迟视觉输入能力，或另外取得原生上下文及最终键消费的因果/序列化证据，不能只换字段名。

新合同的最小验证应先在**离线动态 fixture**以此次两 SHA / 观测间隔回放，量化直接点击是否实际缩短视觉操作到 handler 的延迟及 gate 接受率，并刻意覆盖跨代际、A→B→A、点击后 server 变化、unknown/停止；必须仍由 gate 拒绝过时帧，不能用自动重试堆成功率。离线证明可操作后，再另行授权一次有明确停止条件的真实连续菜单验收，逐键核真实菜单效果与原生收键。**本任务未实现或启用该合同，诊断通过不是交互优化完成。**
