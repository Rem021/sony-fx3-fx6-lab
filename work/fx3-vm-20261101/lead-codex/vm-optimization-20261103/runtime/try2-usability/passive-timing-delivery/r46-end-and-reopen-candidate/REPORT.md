# FX3 r46｜第8步拒绝与提前 End 清理矛盾：离线诊断及最小宿主候选

生成时间：2026-11-05（America/Los_Angeles）
卷 UUID：`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`（已核）
根：`/Volumes/KAFU2T/AI/Projects/Mac`（非 Git 根，未 clone、未复制历史大树）
本目录：`work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r46-end-and-reopen-candidate`

## 0. 结论先行

**问题 A（清理）已证实根因，并完成最小隔离宿主候选。**
r45 的第二次清理 `cleanup-calls/4302ff41-653d-4ae5-9b79-f713120ab9e2` 中，原 End、结束页、浏览器关闭、HAR/PNG、native/QEMU 回收、双锁、端口和 API16 回执均通过；`body-result.json` 为 `errors=[]`、`runner_alive=false`、`port_closed=true`、`alarm_disposition=valid_armed_do_not_cancel_or_dispose`。但 `r44-review-budget-candidate/runtime-wrapper/cleanup_evidence.py:122` 的 certify 白名单只允许 `valid_null_never_armed/valid_nonarmed`，且 `:127` 又强制要求 `deadline-dispose` 阶段；armed 路径按设计不 cancel/dispose，只写 `dispose-not-invoked.json`，因此 certify **必然** 抛 `cleanup_body_incomplete`。`revalidate` 复用 `certify`，同一缺陷会让未来的 armed 完成索引无法复核。候选没有“把 armed 加入白名单就放行”：它新增独立的 armed 证据链（完整 alarm 身份/nonce/due、原 End 完成、同 owned 页面/launch/run/document/timeOrigin、browser 关闭、native/资源回执），nonarmed 仍强制原 `deadline-dispose` 回执；unknown、缺证、错身份、仍 live、二次完成索引篡改均拒绝。**原始 r45 cleanup 仍是 unknown，未倒改。**

**问题 B（第 8 步拒绝）已定位到具体谓词。**
`click-receipt.json` 的 26 项 host 预检全为 true、`status=click_invoked`、点击帧为 `gen 58 / seq 1886 / SHA e014…`；随后 PAGE 自己的第二次 preflight 拒绝：`not_posted / preflight_identity_or_lifecycle_changed / mutation_called=false`。HAR 给出了直接证据：点击前 `11:28:11.680683008Z` 的 `/api/status` 是 `gen 58 / seq 1886 / e014…`，点击 handler 的 preflight `11:28:11.935694848Z` 已变成 `gen 59 / seq 1892 / 2914275c…`；PAGE 的 freshness 条件 `!frameLoadedFor(preflight)`、`preflight.frame.PNG_sha256!==clickedSHA`、`preflight.frame.content_generation!==clickedGeneration` 同时成立，故拒绝。这是**正确的画面新鲜度门**，不是旧图、缓存或超时；本任务不取消它。

**问题 B 的 recovery 拒绝另有一个真实内部不一致。**
`recovery-readonly` 在 `performance=243342.4 < due=303173.9`（非 60 秒到期）、`mode=armed` 下返回 `not_eligible_armed`。原因是 PAGE 的 `keyAttemptRecoveryEligibility()` 仍硬编码旧预算 `deadline_ms!==20000` 和 `due_ms!==armed_ms+20000`（fixture 第 252/256 行），而 r44/r45 安装的是 60000ms alarm；因此它返回 `document_or_alarm_mismatch`，`recovery_readonly.js:20` 将其折叠为 `not_eligible_armed`。没有发生 60 秒到期，也没有缺身份；是 20s/60s 的预算不一致。候选只改这两个字面量为 60000，保留全部身份/freshness/确认/未入队门；fake DOM 回放 5/5，原 PAGE 拒绝、候选 PAGE 放行、篡改仍拒绝。**该页面候选未启用、未部署、未改变运行政策；需新的自绑定 profile/hash 和协调器批准。**

**未升级 r45。** r45 仍是 `failed`，原 cleanup 仍是 `unknown`，第 8 步仍是 `not_posted`。离线测试通过不代表真实菜单/清理/recovery 通过。

---

## 1. 边界、输入与封存

- 全程未启动 VM、browser、server、QMP 或 guest；未部署；未改运行政策、固定 FX3 配置、固件、CPIO 或 FX6 源。
- 唯一写目录是本目录；`r44`、`r45`、native run、ledger、README 全部只读。
- 卷身份：`diskutil info /Volumes/KAFU2T` → `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；`/Volumes/KAFU2T/AI/Projects/Mac` 非 Git 根（`git rev-parse` 失败），未 clone。
- 输入封存：`tests/input_seal.py before|after`，51 个输入路径，包含 r45 的 554 项 `SHA256SUMS`、150 项 `NATIVE-SHA256SUMS` 及关键清理/第 8 步 evidence。
  - before：`receipts/input-seal-before.json`，SHA256SUMS 自身 `82f91be572e61b896718d8f7c8689d3c7a79cac3edf28fb0a4d02bd41f49a614`，`shasum -c` 554 OK；NATIVE `8e500b1c1bc76146533b5e4d36db1eb657d0309d79f97b8f34ce05fb5ae0b79f`，从 `runs/v44review-n64-r44-6583e25e` 运行 150 OK。
  - after：`receipts/input-seal-after.json`，同一 self-hash，554/150 OK。
  - 对比：`receipts/input-seal-compare.json`，`changed=[]`、`unchanged=true`、`input_count=51`。
- 输入 hash：r44 `SOURCE-FREEZE.json=3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c`，`CORE-SOURCE-FREEZE.json=b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1`，与任务给定一致。
- r45 批准记录：`APPROVAL.json` 的本地 `task_r45vm0323/ctx_r45vm0323` 不是 Orca 正式 ID；原用户消息的独立核验仍待提供。本报告不补造批准、不改旧 APPROVAL。

---

## 2. 问题 A：证明链

### 2.1 r45 清理调用实际发生了什么

调用目录（只读）：`r44-review-budget-candidate/run-inputs/r45-vm-r45vm0323/cleanup-calls/4302ff41-653d-4ae5-9b79-f713120ab9e2/`。

| 证据 | 实测值 | 说明 |
|---|---|---|
| `End-original-button-stdout.txt` | `{"End_invoked": true}` | 原 End 按钮被点击一次，不是替代关闭 |
| `ENDED-STATE.json` | `finished=true`、`ending=true`、`url=http://127.0.0.1:58245/`、`document_id=70f5e6af-…`、`document_time_origin=1793877848674.9`、`lastStatus.phase=finished`、`launch_request_id=d23ffef6-…`、`run_incarnation=9cab2340-…` | 同一 owned 页面已到 finished |
| `deadline-after-End.json` | `version=1`、`deadline_ms=60000`、`expectedURL/launch` 匹配、`sealed=false`、`current.state=armed`、`nonce=d1b0d0c4-…`、`armed_ms=243173.9`、`due_ms=303173.9`、`due-armed=60000`、最后一次事件为 `armed`、无后续 cancel/expire | End 时 alarm 仍 armed；没有 cancel/dispose |
| `dispose-not-invoked.json` | `reason=valid_armed_do_not_cancel_or_dispose`、`alarm_cleanup=no cancel/no dispose; owned document closes below` | armed 路径保留“未 dispose”而不是伪造 dispose |
| `body-result.json` | `errors=[]`、`runner_alive=false`、`port_closed=true`、`alarm_disposition=valid_armed_do_not_cancel_or_dispose` | `_cleanup_once` 的 body 成功 |
| `browser-before-close` | `active=true`、`pid=53382`、session 匹配 | 关闭前 session 仍活 |
| `browser-after-close` | `active=false`、`pid=null`、session 匹配 | 关闭后 session 不活 |
| `traffic.har` / `ended-page.png` | HAR 有 entries；PNG 头 `89 50 4e 47` | 清理阶段完整 |
| native `trial-session.json` | `observer_pid=53378`、`qemu_pid=53782`、`url`/run 匹配、`host_launch_uuid=b1f17b5a-…` | 同一 run/session |
| native `receipt.json` | `process_reaped=true`、`PID_absent=true`、`qemu_exit=0`、双锁 `free_at_close=true`、`cleanup.API16_restored=true`、`cleanup.quit_sent=true` | QEMU/PID/锁/API16 通过 |
| `trial-web-final-receipt.json` | `acknowledged=true`、`end_reason=browser_ack`、`maximum_wait_seconds=30` | final ACK 送达（仅投递证明） |
| `RESOURCE-AUDIT.json` | runner 53378/QEMU 53782 absent、双锁 free、58245 closed、browser session inactive、cleanup index absent | 独立资源审计 |
| `result.json` | `status=unknown`、`errors=["cleanup incomplete: ValueError('cleanup_body_incomplete')"]`、`End_required=true` | 原调用确实 unknown |

第一次调用 `0687a34f-8dcd-4d62-b4a0-b1c0037830b1` 的 End 在旧文档上失败（`owned_page_identity`），`lastStatus` 未定义，deadline 状态读取失败；它仍然是 unknown，未用于候选证明。

### 2.2 根因（两个独立拒绝点）

原文件 `r44-review-budget-candidate/runtime-wrapper/cleanup_evidence.py`：

- **第 122 行**：
  ```python
  if body['errors'] or body['runner_alive'] is not False or body['port_closed'] is not True or body['alarm_disposition'] not in ('valid_null_never_armed','valid_nonarmed'):
      raise ValueError('cleanup_body_incomplete')
  ```
  armed 分类被排除，所以即使 `_cleanup_once` 成功写 body，也必然在这里失败。
- **第 127 行**：
  ```python
  for name in ['End-original-button','ended-state','ended-page','deadline-after-End','deadline-dispose','HAR-stop','browser-before-close','browser-close','browser-after-close']:
  ```
  armed 路径设计上不调用 `deadline-dispose`，只写 `dispose-not-invoked.json`；因此即使 122 行放行，这里也会因缺少 `deadline-dispose-process.json` 失败。
- `revalidate`（第 163 行）调用 `certify`，所以未来 armed 完成索引同样无法复核；`validate_reference` 的 required 集合也没有 armed 专用的 `dispose-not-invoked.json`。

这与 `cleanup.py` 的设计直接冲突：`_cleanup_once` 第 39–41 行明确对 `valid_armed_do_not_cancel_or_dispose` 不 cancel/dispose，并写 `dispose-not-invoked.json`。**这不是“少一个白名单项”，而是 body、certify、stage required、revalidate、manifest required 五个地方没有统一。**

### 2.3 候选修复（精确范围）

改动只在 `runtime-wrapper/cleanup.py` 与 `runtime-wrapper/cleanup_evidence.py`；`DIFF-cleanup.patch` 为完整 unified diff。

1. **单一分类源**：把原 `cleanup.py` 的 `alarm_disposition` 迁到 `cleanup_evidence.classify_alarm(value,c)`，`cleanup.py` 通过 `evidence.classify_alarm` 调用，避免 body 与 certify 两套逻辑漂移。
2. **armed 证据函数 `alarm_evidence`**：
   - 重算分类必须与 `body.alarm_disposition`、`ALARM-DISPOSITION.classification` 一致；
   - `forced_cancel` 必须 `False`；
   - `ALARM-DISPOSITION.alarm_sha256` 必须是 `deadline-after-End.json` 的精确 digest；
   - armed 时 `dispose-not-invoked.json` 必须存在，`reason` 匹配，`alarm_cleanup` 文案匹配，`alarm_sha256` 匹配，**整个 `alarm` 对象深比较相等**，并单独绑定 `version/deadline_ms/expectedURL/expectedLaunchId/documentTimeOrigin/sealed/nonce/state/armed_ms/due_ms/current_deadline_ms`；
   - armed 时 `deadline-dispose.json`/`deadline-dispose-process.json` 必须不存在，marker 的 `dispose_invoked` 必须 `False`；
   - nonarmed 时必须存在 `deadline-dispose.json` 与 rc=0 的 `deadline-dispose-process.json`；dispose 状态必须 `sealed=true`、包含 `disposed` 事件、current 的 state/nonce/armed/due 与原 alarm 一致；`valid_null_never_armed` 还要求 current 为 null 且 dispose 事件中没有 armed/cancelled/expired；非 armed 出现 `dispose-not-invoked.json` 直接拒绝。
3. **`ended_state_evidence`**：
   - `ENDED-STATE.finished=true`、`lastStatus.phase='finished'`；
   - `lastStatus.launch_request_id==c.launch_id`、`run_incarnation` 非空；
   - `state.url==c.url`、`document_id` 非空、`document_time_origin` 有限且等于 `deadline-after-End.documentTimeOrigin`；
   - `ENDED-STATE.alarm` 与 `deadline-after-End` 的 version/deadline_ms/expectedURL/expectedLaunchId/documentTimeOrigin 以及 current 的 nonce/state/armed_ms/due_ms/deadline_ms 一致；
   - 解析 `End-original-button` 的 stdout：`End_invoked=true` 时 `ending=true`；`false` 时要求 `finished=true`；其他值拒绝；
   - 若存在 `current-attempt.json`，要求 document_id/document_time_origin/run_incarnation 与该 attempt 的 `postkey_binding` 一致，alarm nonce 与 attempt nonce 一致（r45 的 70f5…/1793877848674.9/9cab…/d1b0d0c4… 均通过）。
4. **`browser_evidence`**：before 必须 `success=true`、session 匹配、`active=true`、pid 为整数；after 必须 `success=true`、session 匹配、`active=false`、pid 为 null。
5. **条件 stage 列表**：公共阶段 + armed 不要求 `deadline-dispose`、nonarmed 要求；PNG/HAR、native/resource 检查保持并加强。
6. **`validate_reference`**：按 body disposition 条件要求 `dispose-not-invoked.json`（armed）或 `deadline-dispose.json` + `deadline-dispose-process.json`（nonarmed）；armed 不再被“缺 deadline-dispose”误杀。
7. **`revalidate`**：除 native/run_incarnation/document_id 外，还比较 `document_time_origin`、`alarm`、`ended_state`、`browser`，防止“证明文件没变但语义变了”。
8. **完成索引**：`cleanup()` 原有的“无效索引先归档、必须同时匹配归档 bytes、`owned_live_candidate` 不通过则不重访 browser、不可无归档替换”逻辑保留；`publish` 未放宽。新增测试证明二次替换必须提供原始 invalid index 的 sha 和归档文件 sha，篡改归档即拒绝。

### 2.4 候选行为与测试

`tests/cleanup_evidence_test.py`：35 个用例，全部通过（`receipts/cleanup-evidence-tests.json`，35/35）。

覆盖：

- `armed` 正例：原 End 后 close 成功、browser before/after、full alarm/nonce/due、native/resource、current-attempt 全部通过；
- `wrong identity`：nonce、due、document、timeOrigin、launch、marker digest、body disposition、forced_cancel；
- `missing evidence`：缺 `dispose-not-invoked`、缺 `deadline-dispose`、unsealed dispose、dispose 错 nonce；
- `browser still live`：after active=true；before inactive；
- `nonarmed missing dispose`、armed 混入 dispose、nonarmed 混入 armed artifact；
- `unknown/malformed`：旧 20000 alarm、due-armed 不等于 60000、坏 nonce、null current 却带 armed 事件；
- 资源 probe 未 closed、stage rc 非 0、PNG/HAR 坏；
- 完成索引：`validate_reference` 正例、tampered result/artifact/proof 拒绝、`publish` 幂等与篡改归档拒绝；
- **r45 真实证据回放**：把原 `4302ff41…` 调用复制到候选临时目录，**仅添加新候选会写出的** `dispose-not-invoked.json`/`ALARM-DISPOSITION.json`，用记录值注入 native/resource probe，`certify` 通过；证明 full identity/End/browser/native/resource 逻辑对真实 r45 证据成立。**副本不是原调用，原调用仍是 unknown。**
- **原调用拒绝**：原 `4302ff41…`（无新 marker digest）被拒绝 `alarm_marker_digest`；原第一次 `0687a34f…` 被拒绝 `cleanup_body_incomplete`。没有倒改。

结论边界：这证明“未来由新候选写出的 armed cleanup，在具备同样证据时可以完成”；**不证明 r45 原 cleanup 已完成**。

---

## 3. 问题 B：第 8 步拒绝的精确谓词

### 3.1 host 26 项预检通过，PAGE 第二次 preflight 拒绝

`step-08-attempt-08/click-receipt.json`：

- `status=click_invoked`，`eval_may_have_started=true`，`guest_keys_sent_directly_by_cli=0`；
- `result.checks` 26 项全 true，`failed_checks=[]`；
- `click_time_frame = {gen 58, seq 1886, SHA e0140ea1…}`；
- `previous_confirm.expected.step=7`，`document_id=70f5…`，`launch=d23ff…`，`run_incarnation=9cab…`；
- `alarm.current.state=armed`，`nonce=d1b0d0c4…`，`armed=243173.9`，`due=303173.9`，`now=243258.6`，`due-armed=60000`。

随后 `step-08-attempt-08/outcome.json` / `step-08-attempt-08-attributed-outcome-process.json`：

```json
{"outcome":"not_posted","reason":"preflight_identity_or_lifecycle_changed",
 "mutation_called":false,"created_monotonic_ms":243258.8,"updated_monotonic_ms":243260.4,
 "frame":{"PNG_sha256":"e0140ea1…","content_generation":58,"sequence":1886}}
```

即：host helper 的 26 项预检通过并调用了原按钮一次；PAGE 自己的点击 handler 在 `b.click()` 内部做了第二次 preflight，判定“画面/生命周期已变化”，**没有调用 mutation（/api/key）**。

### 3.2 HAR 直接给出“哪个帧变了”

`cleanup-calls/4302ff41…/traffic.har` 中，点击前后的 `/api/status`：

| HAR 时间 | 状态 | frame |
|---|---|---|
| `2026-11-05T11:28:11.680683008Z` | 200，2835 bytes，steps=7、phase=ready、ready=true | `gen 58`、`seq 1886`、`SHA e0140ea1…`、pixel_source_sequence=1879 |
| `2026-11-05T11:28:11.935694848Z` | 200，2868 bytes，steps=7、phase=ready、ready=true | `gen 59`、`seq 1892`、`SHA 2914275c…`、pixel_source_sequence=1887 |

点击 eval 的 host 时间约 `11:28:11.928–11:28:11.938`；PAGE 的 preflight GET 在 `11:28:11.935694848Z`。点击 handler 的快照是上一帧（58/1886），preflight 已经读到新帧（59/1892）。HAR 中点击后没有 `POST /api/key`，下一次 POST 是 `11:28:12.088363008Z` 的 `/api/stop`。

### 3.3 具体谓词

真实 PAGE 源码（`r44-review-budget-candidate/tests/fixtures/PAGE-script.txt`，canonical SHA `852c83d6…`；运行时由 `trial_web_r24_review_snapshot.py` 从 base PAGE 组装）中：

- `frameLoadedFor(s)`（第 108–110 行）要求 `displayed>0 && shownSHA===s.frame.PNG_sha256 && displayedGeneration===s.frame.content_generation && s.render_valid && !renderFault`。
- 点击 handler 的 preflight 组合门（第 302–309 行）包括：
  - `preflight.steps!==clickedStep`
  - `!frameLoadedFor(preflight)`
  - `preflight.frame.PNG_sha256!==clickedSHA`
  - `preflight.frame.content_generation!==clickedGeneration`
  - `shownSHA!==clickedSHA`
  - `displayedGeneration!==clickedGeneration`
  - `!lastStatus || !frameLoadedFor(lastStatus)`
  - `lastStatus.steps!==clickedStep`
  - `lastStatus.frame.PNG_sha256!==clickedSHA`
  - `lastStatus.frame.content_generation!==clickedGeneration`

在本例中，`clickedSHA=e014…`、`clickedGeneration=58`、`shownSHA=e014…`、`displayedGeneration=58`，而 preflight 是 `gen59/2914…`。因此至少以下三项同时为真：

1. `!frameLoadedFor(preflight)`（displayedGeneration 58 ≠ preflight 59）；
2. `preflight.frame.PNG_sha256!==clickedSHA`；
3. `preflight.frame.content_generation!==clickedGeneration`。

`lastStatus` 仍是点击时的 58（页面 tick 的下一帧尚未更新），所以 `lastStatus.*` 条件本身不失败；`ending/finished/deliveryUnknown/review*/awaitingStep/phase/ready/busy/review_required/steps` 也未失败。**失败点是“点击后、PAGE preflight 前，服务器发布了新帧，点击帧不再是当前帧”**。`setAttempt(...,'not_posted',{reason:'preflight_identity_or_lifecycle_changed'})` 在 `mutation_called=false` 下执行（第 309 行），所以没有 key 入队。

这不是旧图/缓存/超时推断：HAR 中 preflight 的 200 响应体直接包含新帧；也不是 60 秒到期：`performance.now=243258.6 < due=303173.9`。**该拒绝是设计要求的正确行为；不得为了通过而取消 freshness/身份/确认/未入队判定。** host 侧也无法在 `b.click()` 与 PAGE 的异步 preflight 之间原子冻结服务器帧；真正的原子点在 PAGE handler，且它已经正确拒绝。

### 3.4 recovery-readonly 的 `not_eligible_armed`

`step-08-attempt-08/recovery-review/observation-result.json`：

- `status=refused`、`mode=armed`；
- `before.performance_ms=243342.4`、`before.qualified=false`、`before.reason=not_eligible_armed`；
- `input_permission=false`、`postkey_confirmation=false`、`firmware_generation=null`、`causality=not asserted`。

`recovery_readonly.js:19–20`：

```js
if(c.mode==='armed'){
  if(performance.now()>=h.current.due_ms||!window.fx3KeyAttemptRecoveryEligibility?.(b)?.eligible)return fail('not_eligible_armed');
}
```

本例 `performance.now()=243342.4 < due=303173.9`，所以第一项不成立，失败在 PAGE 的 `fx3KeyAttemptRecoveryEligibility(binding)`。该函数（fixture 第 239–269 行）在：

- 第 252 行：`h.deadline_ms!==20000`
- 第 256 行：`h.current.due_ms!==h.current.armed_ms+20000`

处返回 `deny('document_or_alarm_mismatch')`。r45 的 alarm 是 `deadline_ms=60000`、`due-armed=60000`，所以它必然不匹配 20000。`recovery_readonly.js` 把所有 not eligible 折叠成 `not_eligible_armed`，因此表面上看不出是 20s/60s 不一致。**这不是 60 秒到期；是 PAGE 的 recovery 预算仍停留在旧 20s。**

### 3.5 最小 fake DOM 回放

`tests/page_replay_test.cjs` 在 vm + fake DOM 中执行真实 PAGE 脚本；无 browser/server/network。5/5 通过（`receipts/page-replay-tests.json`）：

1. 原 PAGE：点击帧 58、preflight 返回 59 → `not_posted/preflight_identity_or_lifecycle_changed/mutation_called=false`，`/api/key` 调用数 0；随后 `fx3KeyAttemptRecoveryEligibility` 返回 `{eligible:false, reason:'document_or_alarm_mismatch'}`。
2. 候选 PAGE：同一 59 帧场景仍拒绝（freshness 未削弱）；recovery eligibility 返回 `{eligible:true, reason:'attributed_unqueued_local_snapshot_only'}`。
3. 候选 PAGE 正例：同帧点击 → `accepted`、`mutation_called=true`、`/api/key` 恰好 1 次。
4. 候选 PAGE 篡改门：wrong attempt_id / document_time_origin / frame sha / frame generation → `binding_mismatch`；wrong alarm nonce / sealed / old 20s / due in past / expired state → `document_or_alarm_mismatch`（9 个负例全部拒绝）。
5. 候选 PAGE 对已 `accepted` 的 attempt 调用 recovery → `attempt_not_proven_unqueued` 拒绝。

`tests/page_source_check.py` 证明：base PAGE 与最终 r24 canonical PAGE 都只改了两行（20000→60000），没有其他差异；候选 canonical SHA 为 `f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`（原 `852c83d6…`）。回执：`receipts/page-source-check.json`。

### 3.6 最小页面候选与“缺失观察点”

页面候选文件：

- `page/trial_web_v22_navigation_review_r46.py`：base PAGE 的副本，只把 recovery eligibility 的两处 `20000` 改成 `60000`；
- `page/PAGE-script-r46.txt`：r24 canonical PAGE 的对应副本；
- `page/PAGE-IDENTITY-r46.json`：原/新 canonical hash、两行 diff、若启用需更新的绑定点。

**未启用**：没有把它接入 `trial_web_r24_review_snapshot.py`，没有改 `deadline.js` 的 `SCRIPT_SHA`、`planned_navigation_click.py` 的 `PAGE_SHA`、`PAGE-IDENTITY.json` 或任何 SOURCE-FREEZE。若未来启用，必须自绑定新 profile/hash，并显式更新这些绑定点；否则 `deadline.js` 的 PAGE fingerprint 检查会拒绝安装。该候选保留所有原门；不是“取消 20000 检查”，而是把 recovery 预算与已安装的 60s alarm 对齐。

**精确缺失观察点方案（即使不启用页面候选也应补）**：

1. host 的 click 回执除 `clicked_sha/clicked_generation` 外，应在点击后记录一次**只读** `/api/status` 的 `frame`（gen/seq/sha）与 `steps/phase/ready/busy`，写入 receipt 的 `post_click_preflight_status_frame`，并与 clicked frame 比较。r45 这次只能从 HAR 反推；未来应直接留证。
2. `recovery_readonly.js` 应把 PAGE `fx3KeyAttemptRecoveryEligibility` 的 `reason`（`binding_mismatch`/`document_or_alarm_mismatch`/`attempt_not_proven_unqueued`/`current_state_not_ready`）原样带入 observation-result，而不是折叠为 `not_eligible_armed`。
3. recovery 的 host 侧不得自动重试、自动选图、合并 pin/confirm；只能在操作者明确看图后重新做 planned click。页面候选若未被批准，armed recovery 在 60s 政策下应继续视为不可用并如实报 unknown，而不是放宽。

---

## 4. 明确 unknown / 未证实

- **r45 原 cleanup 仍 unknown**；本报告没有、也不能把 `4302ff41…` 或 `0687a34f…` 的 `result.json`、`CLEANUP.json`、`CLEANUP-COMPLETED.json` 改成 completed。候选回放只针对复制件和“未来候选会写出的 artifacts”。
- **未运行真实菜单/清理/recovery**；没有 VM、browser、server、QMP、guest、部署。所有“通过”都是离线单元/回放测试。真实 FX3 菜单、真实 End、真实 browser close、真实 native 回收仍未在本轮验证。
- **r45 仍是 failed**；7 张固定图已由协调器实际查看、7 次 confirmed、第 8 步 not_posted，这些结论不改变。
- **用户批准独立核验仍待提供**；本地 r45 task/dispatch 不是 Orca 正式 ID，未补造。
- **第 8 步新帧为何在点击 handler 的 preflight 前（点击后约 7ms）已由服务器发布**（菜单动画/刷新或其他）没有 server 侧因果日志；HAR 只能证明“preflight 时服务器已有 gen59”，不能证明新帧的生成原因。未推断旧图/缓存/超时。
- **页面候选未部署**；new canonical hash 未绑定任何 profile；`deadline.js`/`PAGE-IDENTITY`/`planned_navigation_click.py` 等绑定点未改。若协调器不批准新 page hash，则该候选仅作为诊断。
- **cleanup 候选不是可直接运行的完整 43 文件运行包**：它包含两个改动模块、直接依赖 `common.py`（未改）和测试；未来若用于真实 run，需把候选绑定到完整 SOURCE43 并自绑定新 profile/hash，且由协调器另行授权。本轮未做该绑定，避免伪造运行包。

---

## 5. 交付清单与本目录结构

```
r46-end-and-reopen-candidate/
  REPORT.md
  CANDIDATE-DELTA.json          # old/new sha256、页面绑定点、测试计数、r45 状态
  CANDIDATE-POLICY.json         # enabled=false、边界、保留预算、未来 run 前置条件
  DIFF-cleanup.patch            # cleanup.py + cleanup_evidence.py 精确 unified diff
  DIFF-page.patch               # base PAGE 与 canonical PAGE 的两行 diff
  runtime-wrapper/
    cleanup.py                  # 候选
    cleanup_evidence.py         # 候选
    common.py                   # 未改副本（hash 与 r44 相同）
  page/
    trial_web_v22_navigation_review_r46.py  # 两行页面候选（未接线）
    PAGE-script-r46.txt                     # canonical 页面候选
    PAGE-IDENTITY-r46.json                  # 原/新 hash、绑定点、enabled=false
  tests/
    cleanup_evidence_test.py    # 35 用例
    page_replay_test.cjs        # 5 用例 fake DOM
    page_source_check.py        # 两行 diff/源码核验
    input_seal.py               # before/after 输入封存
    run_all.py                  # 总驱动，捕获 raw stdout/stderr
    fixtures/PAGE-script.txt    # r44 原 canonical 副本（852c83…）
  receipts/
    cleanup-evidence-tests.json # 35/35
    page-replay-tests.json      # 5/5
    page-source-check.json      # 2/2 changed lines
    input-seal-before.json      # 51 输入，554/150 OK
    input-seal-after.json       # 51 输入，554/150 OK
    input-seal-compare.json     # unchanged=true
    test-run.json               # 4/4 suite，passed=true
    raw/*.stdout.txt/*.stderr.txt
  SHA256SUMS                    # 本目录文件清单（不含自身）
```

关键文件 SHA256（`SHA256SUMS` 生成前）：

- `runtime-wrapper/cleanup.py`：`ed3edbb402529acfa84a6fb18ce96720b48cb7b7c1edc1cbc622da9c92b7a1cb`
- `runtime-wrapper/cleanup_evidence.py`：`b9c511e2c4ecf1ff24a0446a6a462dce86776b58ac983c73db12f811261a00dc`
- `runtime-wrapper/common.py`：`96196e962cf9e2cdc520a9128508e32a45349db4d9d86442c7c2a05395b11c5e`（与 r44 相同）
- `page/trial_web_v22_navigation_review_r46.py`：`8a40a4a67bdbe4ce8712d1a4ef78c893ffc2ea625fb6f0966d1a4e4136ba1be7`
- `page/PAGE-script-r46.txt`：`f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`
- `tests/fixtures/PAGE-script.txt`：`852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b`
- 回执：`cleanup-evidence-tests.json` `ea19b013f3cac3493e520cf8b24b170446ff526044dcb17008c134367d9f6b33`；`page-replay-tests.json` `deaaa56fcd1fc70ce3fb9eda78445368af92e12e32027d1e65bd407cda74fb80`；`test-run.json` `9e11c133c669a19577f29f09c4dd1fde799907140aadd295d771552ba0b81085`
- `DIFF-cleanup.patch` / `DIFF-page.patch` 在 `SHA256SUMS` 中。

运行方式（离线，自包含）：

```sh
cd .../r46-end-and-reopen-candidate
python3 tests/run_all.py
```

该命令只运行候选测试与输入封存，不接触真实 browser/进程；`run_all.py` 确认 `input-seal-compare.json.unchanged=true` 后返回 0。

---

## 6. 建议的下一步（由协调器决定）

1. **不升级 r45**：保留 `failed`、`cleanup=unknown`、`step8=not_posted`；不要把 r45 的 `result.json`/`CLEANUP.json` 改成 completed。
2. **验收问题 A 候选**：若接受，将 `cleanup.py`/`cleanup_evidence.py` 纳入下一次自绑定 SOURCE43 的新 profile；在下一次真实 run 后，只有同时具备原 End 完成、同 owned 页面/launch/run/document/timeOrigin、browser 关闭、native/QEMU/端口/双锁/API16 回执和完整 alarm 身份/nonce/due 的 armed cleanup，才允许 `completed`。
3. **问题 B 先补观察点，再决定页面候选**：至少在 host click receipt 中记录 post-click preflight status frame，并让 recovery 原样报告 PAGE eligibility 子原因。若不接受新的 page hash，则 armed recovery 在 60s 政策下继续不可用，应如实报 unknown；不得用“跳过 freshness”或“自动重发”绕过。
4. **不改变任何固定值**：整步 60s、native 12s、snapshot 20s、API16 restore 20s、startup 180s、总 8min、8 accepted/10 attempt/2 recovery、固定平台与原 CPIO 均未改。
5. **若未来真实 run**：需协调器新的明确授权与 Orca 正式 dispatch；本候选 `enabled=false`，不得被当作 r45 的重试或被拦截 FX6 实现的替代。

---

## 7. 一句话状态

- **A：证实并修复候选**（armed 清理证据链严格化；35/35 离线测试；r45 原调用仍 unknown）。
- **B：证实两个谓词**（click 帧 freshness 竞争；recovery 20s/60s 预算不一致），给出最小页面候选 + fake DOM 回放（5/5）与缺失观察点；未启用。
- **r45：failed 保留；无升级；无真实菜单/清理结论。**
