# FX3 r12 历史画面确认推进：离线候选

**结论：宿主前端的确认等待缺陷已做最小修复并通过离线真实 Chrome 回放；真实 guest、长时运行和默认入口均未验收或部署。** 本目录只派生 r11 的 22 项宿主源，只有 `trial_web_v22_navigation_review.py` 的 PAGE JavaScript 变化；服务端 `TrialState.submit`、`confirm_visual`、帧缓存、健康门、原 5000ms 与 API16 期限、guest/QEMU/CPIO/DTB/Backup 均未改。

## 实测动机与根因边界

真实 r11 run `v25diag-web-r6-814c425f` 的 [HTTP证据](../../runs/v25diag-web-r6-814c425f/R11-web-http-evidence.json) 记录第 7 键 MENU 接受 202，随后 nonce `d39b2219-e14c-4346-a346-8ddf2a8d9b27`、step7、seq3275、generation69、SHA `e0140ea1…64d56ec4` 的看图确认返回 200、`confirmed=true`、`guest_input_written=false`。其 [43 条确认后状态](../../runs/v25diag-web-r6-814c425f/R11-confirm7-status-evidence.json) 均给出同一正确历史确认、`review_required=false`、`ready=true`，但当前帧已是 generation70–98。r11 `confirmationMatches` 同时要求当前帧仍为 generation69/SHA69，故无法通过状态消费；直接成功 ACK 分支又未清除 `reviewAwaiting`，造成前端持续锁键。原生第 7 键已到待机，第 8 键未请求；这解释本次前端卡住，不证明更广泛的 guest 稳定性。该匹配逻辑来自 r10，非 r11 可见拒绝补丁新增。

## 修复

`confirmationMatches` 只用当前待确认请求与服务端**历史 receipt** 的 nonce、step、seq、generation、SHA、`guest_input_written=false`、ready phase、已结束 review 和同一步数作精确匹配，不再将历史确认绑定当前帧。直接 HTTP 200 同样仅在 `pendingConfirm===confirmation` 且上述 ACK 字段全等时清除 `reviewAwaiting/reviewUnknown/pendingConfirm`。迟到的旧 ACK 不能改动新请求或其拒绝提示。

这只是**消费已经成功的旧确认**，不会自动确认未来画面、发新固件键或将变化像素视为原菜单完成。下一键仍须 `enableKeys` 见到当前有效、已加载的 PNG SHA 和 `content_generation`；服务端仍用最新帧身份、包括 A→B→A 新 generation 校验。4xx 拒绝持续显示，5xx/超时/无效 JSON 保持 unknown 锁，renderFault/原生 error/停止/终态仍优先。

## 离线验证

- `python3 tests/confirmation_replay.py`：真实 agent-browser Chrome + loopback `TrialState`/PAGE，**PASS，13 张浏览器截图**。[完整 DOM/计数/截图 SHA/网络摘录](tests/confirmation-evidence/RESULT.json)。r11 原版在确认200后画面 B 已加载仍 `reviewAwaiting=true`/键锁；r12 同图解锁，下一键经工具明确点击一次才入队（确认数1、key数由1变2）。A→B→A 时原确认 generation1、新图 generation3，同 SHA 不绕过新帧校验；新键的 `observed_sequence=3`。
- 丢失确认响应时，状态中 nonce/step/seq/generation/SHA/`guest_input_written` 任一错误均维持锁；8s 超时仍 unknown，恢复完整历史 receipt 后才解锁，且确认过程未增加 guest key。旧 status receipt 不解锁新请求。
- 异步旧 ACK 场景：首确认已被 status 消费后，第二确认开始；Chrome 网络 API **实际捕获首 nonce 的 HTTP 200 完整响应体**（[脱敏字段](tests/confirmation-evidence/RESULT.json) 的 `late_old_http_response`），新 pending 此时仍锁；另一场景中旧 ACK 到达后，新确认的 409 提示仍可见。`delayed_ack_sent` 只是夹具准备返回计数，浏览器网络记录才是响应到达证据。两次均2次键入队、2次确认请求，无自动补发。
- `python3 tests/browser_replay.py --candidate-only`：复用 r11 的真实浏览器 4xx/ABA、手动再按、confirm拒绝、5xx/超时/坏 JSON、终态与渲染故障优先回归，**PASS，12 张截图**。[回执](tests/browser-evidence/RESULT.json)。脚本中的点击是自动浏览器操作，不是人类试用或 guest 运行。
- `python3 -m py_compile trial_web_v22_navigation_review.py tests/rejection_harness.py tests/confirmation_replay.py` 通过。回放 harness 均已停止，未启动 QEMU。

截图示例：[旧版卡住](tests/confirmation-evidence/r11-confirm-200-new-frame-stuck.png)、[新版 B 图后可继续](tests/confirmation-evidence/r12-confirm-200-new-frame-unlocked.png)、[ABA 新代](tests/confirmation-evidence/r12-confirm-200-ABA-generation.png)、[旧 ACK 不解锁新请求](tests/confirmation-evidence/r12-late-old-ack-keeps-new-request-locked.png)、[旧 ACK 不抹去新拒绝](tests/confirmation-evidence/r12-late-old-ack-keeps-new-rejection.png)。这些是离线夹具彩色 PNG，不是 FX3 原生画面。

## 审查与剩余门

[r11-to-r12.diff](r11-to-r12.diff) 仅含上述 PAGE 两处变更；[SOURCE-FREEZE.json](SOURCE-FREEZE.json) 固定 22 项宿主源，[DELIVERY-FREEZE.json](DELIVERY-FREEZE.json) 固定报告、差异、测试和图像，[SHA256SUMS](SHA256SUMS) 固定两个清单。r11 原 22 项哈希重算相符，r12 其余21项逐字节等同 r11。

仍需单独批准真实网页+FX3 guest 再验第7次确认后的人工第8键、完整原生图像与健康/退出门；本离线回放不等于真实可用性通过。未修改现行启动入口、README、ledger、旧 run 或冻结 r11。
