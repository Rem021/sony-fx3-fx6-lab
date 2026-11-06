# r11 明确拒绝提示：宿主候选离线回执

**结论：离线浏览器与 TrialState fixture 通过；未运行 VM，未部署。** r10 的明确 4xx 键/确认拒绝在下一次正常 status 轮询会失去可见说明；r11 让该拒绝持续显示，明确“本次未被接收、看最新画面后自行决定是否再操作”。旧帧拒绝依然严格执行，未把 409 变成成功。

## 输入证据与改动

- 已读真实 run `v25diag-web-r6-b6209581/INTERACTION-key-http-immediate.json`：`POST /api/key` 带 `key=427, observed_sequence=196`，HTTP 409 原文“当前画面已变化或不可用，请等待并查看最新画面”；该轮实际 0 键，无 native down/up/done。frame196 generation30 到 frame200 generation31 是竞争线索，**没有拒绝分支现场，不能称唯一根因**。
- r10 `trial_web_v22_navigation_review.py` 的按键 catch 只写 `err.textContent`，每 400ms 的正常 `tick` 重设 `diagnostics.hidden=!s.error` 并清 `failureSummary`，因此用户看起来按了没反应。r11 仅改 PAGE JavaScript：保存 `explicitRejection(kind,detail)`，按键/画面确认的明确 4xx 分别持续展示中文告警；下一次对应手动操作成功才清除。显示优先级为原生 `s.error`、`finished/stopping/ending`、网页读取/渲染故障、送达未知、明确拒绝。严格匹配 `confirmationMatches` 的只读成功状态也会清此前确认拒绝，即使当前确认响应丢失。
- `request` 的 8 秒界限、5xx/超时/坏 JSON 送达未知锁、一次 pending、手动确认、PNG SHA 与 `content_generation`（含 A→B→A）、frame 缓存、终态/stop 与实际 submit/confirm 后端函数均保持。未自动重发、自动确认、模拟 guest 成功、放宽旧图身份门或解除未知结果锁。后端若返回明确拒绝，只有这时本次请求按现有合同可知未入队；未增添结构化字段或 token 输出。
- `SOURCE-FREEZE.json` 含 r10 的 22 个宿主源；其中 21 个 SHA 完全相同，唯一变化为 `trial_web_v22_navigation_review.py`，SHA256 `1425d8f7c29724909fe9a8f29d3e591d73655ae313bf0d8695641fe1de0575eb`。r10 基线 SOURCE-FREEZE SHA256 `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce`；r11 SOURCE-FREEZE SHA256 `8be8343b234d5d579e75fcf86b002ed675376d0de896cb6925fbf6af64454985`；`r10-to-r11.diff` SHA256 `9dac8dba8aedc94247fe18af0df524cee45d0c200352b749884be1776b0d7cc3`。

## 可复现浏览器验证

- `tests/rejection_harness.py` 从指定 r10/r11 模块加载**真实** `TrialState` 与 `PAGE`，另开受控 loopback 控制端口；不启动 runner/QEMU。`tests/browser_replay.py` 用独立 agent-browser/Chrome 会话点页面按钮、读 DOM 与 HTTP/队列计数，并存截图；命令：`python3 tests/browser_replay.py`。原始结果 `tests/browser-evidence/RESULT.json` 为 `pass=true`，14 组记录，其中 13 张浏览器截图；每条均含截图 SHA、可见 summary、按钮 disabled、服务端请求数与入队数。`--candidate-only` 可在保留旧版通过记录时只重放候选。
- 旧 r10：一次 stale SHA 409 后经过下一 status tick，告警及详情消失；请求 1、入队 0（`r10-swallowed-409.png`）。r11 同一 fixture：告警持续可见、诊断非隐藏、请求 1、入队 0；新帧加载后按钮可用，由测试明确再次点击，第二次请求才入队 1 且告警清理（`r11-stale-409-visible.png`、`r11-manual-key-accepted.png`）。
- A→B→A 保持同 SHA 而 generation 增至 3，旧 generation 请求仍 409、入队 0；画面确认旧身份 409 后提示可见，用户看新图重试后才成功，确认请求 2、guest 输入入队数仍 1。确认先遭明确 409、随后手动重试已在服务端成功却丢响应：严格匹配 request_id/step/sequence/generation/SHA 的 status 消除旧提示；8 秒超时后依然无过期告警，也未产生第二个 guest 输入。
- 5xx、8 秒超时和**真实非法 JSON 原字节**（HTTP 202 body 为 `not valid JSON`，非 JSON 字符串）均保持“送达未知”且按钮禁用，入队 0。原生错误终态覆盖本地 409；坏图无法显示后成功取得 finished 权威状态时，旧告警被清除。该夹具仍保留 `state.frame`，**未单测 frame 字段缺失**；异步 409 catch 也不能盖过当前 renderFault。对应截图与计数均在 RESULT 中。
- 首次自动回放在 r11 409 告警已经出现、但更新图尚未加载时断言按钮解锁，故一次测试等待点过早失败；已改为同时等待最新帧身份和按钮解锁，随后的完整离线回放 `pass=true`。未将该测试时序问题归咎产品，也未扩大测试范围。部分截图因浏览器滚动显示局部区域，DOM 和服务端请求/队列计数提供对应行为证据。

## 验收边界

这是宿主页面候选与离线受控 HTTP/Chrome 证据，不能替代 FX3 guest/UI 实跑。未改 r10 原件、已部署入口、README/ledger、原固件/CPIO/QEMU/Backup、省电/5000ms 与 API16 20 秒合同；未涉及 FX6。后续是否整合和真实 VM 窗口由协调端决定。
