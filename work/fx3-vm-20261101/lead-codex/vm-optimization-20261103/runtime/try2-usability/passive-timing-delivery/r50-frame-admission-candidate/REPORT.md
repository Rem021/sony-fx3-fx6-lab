# FX3 r50｜帧准入 obs_v2 离线候选 + pre-click sync 失败比较

- Task：`task_0cce6dde0290`
- Dispatch：`ctx_89f797a305ca`
- 状态：**离线候选完成；A 已实现为隔离 PAGE 候选并通过等价重放；B 原型比较未显示准入收益，保持 disabled、不集成。**
- 不是真实菜单/提速/FX6 通过；没有新 VM/browser/server/QMP/guest；没有部署、默认入口/运行政策变更、外部 FX6 操作。
- r47/r48/r49 及平台/包只读；只写本 `r50-frame-admission-candidate`。
- 60s 步进、native 12s、snapshot TTL 20s、总 8min、原恢复次数均保持；未复制 CPIO/历史大矩阵，未建完整新运行包。

## 0. 结论

1. **目标 A 已完成最小候选**：在 actual r47 PAGE 的点击 handler 内加入 `obs_v2`，只在原有 combined freshness/identity 拒绝分支记录 clicked/displayed/lastStatus/fresh preflight 的 SHA+gen+seq、实际 performance 单调时间点、完整 predicate 值与短路 evaluated 前缀；`sequence` 仅观测（`sequence_in_gate:false`），原 reason 保留。原条件表达式、status 请求、key POST、`frameLoadedFor` 调用次数、confirm/pin/recovery 代码均未改变。
2. **等价性通过**：actual baseline PAGE 与 actual candidate PAGE + actual `planned_navigation_click.js`，在 fake DOM/fake clock 下重放 r48 两例、step identity、lifecycle phase、accepted、expired 负例；每例 key POST 数量、outcome/reason/mutation、key body、fetch 计数、confirm/pin disabled 均等价。r48 两例 candidate 记录的首个真 predicate 是 `not_frame_loaded_for_preflight`；accepted 不产生 observation。
3. **目标 B 原型已实现但无收益**：`prototype/preclick_sync.js` 为 disabled-by-default、未 import 的只读同步原型；有界 200ms/3 attempts/2 stable samples、`due-500ms` 上限、不重置 arm。比较显示：同帧正常仍 accepted 但多 2 次读/50.5ms；r48 变化帧被 pre-click 拒绝（无 PAGE attempt/recovery），但没有任何变化帧被接受；prep 后再次变化仍被原 PAGE freshness 拒绝；never-ready 消耗 3 reads/100.75ms；expiry/identity 无改善。**不集成**，保留失败比较证据。
4. r49 DESIGN 的 only-design 断言在本新设计中已纠正为“一种待验证候选”；本设计不创建额外权限门，未来运行/政策启用另行决定。
5. r48 仍 failed；r45 仍 failed/cleanup unknown；无新 runtime 授权。

---

## 1. 输入/边界

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- r49 终审只读：`r49-coordinator-final-review.json`（61 清单、parser/serial/hash 边界已核；design caveat 已记录）。
- baseline actual PAGE：r47 canonical `f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`，full PAGE `551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b`。
- actual helper：`operator-helpers/planned_navigation_click.js` `6e120517b1c785bb3eb277268908801465dd55dc0bda5901cfaa2be4fc7175e0`（未改）。
- 输入前后封存 16 项：`receipts/before-input-seal.json` / `after-input-seal.json`，`changed=[]`、`unchanged=true`。

## 2. 目标 A：obs_v2 候选

### 2.1 候选身份与 diff

由 `make_candidate.py` 从 actual r47 assembled PAGE 读取/装配，输出：

| artifact | SHA256 |
|---|---|
| baseline canonical script | `f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf` |
| baseline full PAGE | `551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b` |
| candidate canonical script | `70d08c79c3d20216b36ae1cef6c58584a45d1727ec3fcb99a2eae2608c974205` |
| candidate full PAGE | `9406948426e8899e3f6b122fd752ba128ad2c2327d5b417ce155dd44a6b765f1` |
| candidate served replay script | `75c1e967769c0c9a52b27e4c052c73849bcc93709f82715b20d76a182f349833` |
| diff `candidate/DIFF-obs-v2.patch` | `7825a9ce831474fe941bc69e112428421604a08cb202d4148aad6f745322c3dc` |

diff：52 added / 4 rewritten lines（4 行只是原行追加时间/状态捕获，原条件与 reason 文本不变）；`candidate-static-audit.json` 证实 condition block 完全未变。

### 2.2 记录内容

`window.__fx3FrameAdmissionObsV2`，schema `fx3-frame-admission-obs-v2`，cap 8；只在原 combined 拒绝分支记录：

- `clicked`：attempt frame SHA/gen/seq + click performance 单调时间；
- `displayed_at_click`：PAGE displayed SHA/gen/seq + displayedAt 单调时间；
- `last_status_at_click`：lastStatus steps/phase/ready/busy/review/frame SHA/gen/seq；
- `preflight`：fresh status frame SHA/gen/seq + request start/end/response 单调时间；
- `displayed_at_decision`、`last_status_at_decision`、decision 单调时间；
- `predicates`：按原条件顺序的全部布尔值；`first_true_term`；`evaluated_terms` 前缀（短路实际求值范围）；
- 原 `reason:'preflight_identity_or_lifecycle_changed'` 不变；
- `sequence_observed` 记录 clicked/displayed/preflight/decision 的 sequence，但 `sequence_in_gate:false`，不参与条件；
- 无额外 `fetch`/status/key `/api/key` 请求；无额外 `frameLoadedFor` 调用；无 confirm/pin/ARM/recovery 改动。

### 2.3 静态审计

`receipts/candidate-static-audit.json`：

- original `if(ending||…lastStatus.frame.content_generation!==clickedGeneration){` block 未变；
- `frameLoadedFor(preflight)` / `frameLoadedFor(lastStatus)` counts baseline=candidate；
- `request('/api/status')`、`post('/api/key'`、`setAttempt(...reason...)`、confirm/pin/recovery 计数全部一致；
- recorder 内无 fetch/request/post/frameLoadedFor/setAttempt；
- diff 仅新增/原行扩展；原 key/confirm 语义未改。

### 2.4 前后等价重放（actual PAGE/helper）

`tests/admission_compare.cjs`，fake DOM/fake clock；baseline actual PAGE vs candidate actual PAGE + actual helper：

| case | baseline | candidate | key POST | candidate obs first_true | 等价 |
|---|---|---|---|---|---|
| r48 attempt1 gen19/120/e014 → gen20/128/2914 | not_posted, key0 | not_posted, key0 | 0/0 | `not_frame_loaded_for_preflight` | key/outcome/reason/mutation/key body/fetch/confirm/pin 全部等 |
| r48 attempt2 gen43/231/e014 → gen44/235/2914 | not_posted, key0 | not_posted, key0 | 0/0 | `not_frame_loaded_for_preflight` | 同上 |
| step identity changed (direct PAGE) | not_posted, key0 | not_posted, key0 | 0/0 | `preflight_steps_changed` | 同上 |
| lifecycle phase stopping (direct PAGE) | not_posted, key0 | not_posted, key0 | 0/0 | `preflight_phase_not_ready` | 同上 |
| accepted same frame | accepted, key1 | accepted, key1 | 1/1 | none | 同上 |
| expired recovery eligibility | false / `document_or_alarm_mismatch` | false / 同 | 0/0 | n/a | eligible/reason/key 等 |

说明：identity/lifecycle 用 **direct PAGE** 注入，因为 actual helper 的 26 项 host preflight 会在这些状态先拒绝、不会进入 PAGE；这正好验证 PAGE gate 本体。accepted 是 fake `/api/key` 正例控制，仅验证状态机，不是 guest 输入。`confirm_disabled`/`pin_disabled` 每例 baseline=candidate；两页都没有 confirm 调用。

r48 attempt1 的 observation 关键值：
`clicked=e014…/gen19/seq120`，`displayed_at_click=e014…/gen19/seq120`，`last_status_at_click` 同，`preflight=2914…/gen20/seq128`，`first_true_term=not_frame_loaded_for_preflight`，`evaluated_terms` 长度 13，`sequence_in_gate=false`；`preflight.request_start<=request_end<=decision`，`response_ms>0`（fake clock 步进）。

### 2.5 未集成 / 未来接入

候选是 actual assembled PAGE 的**隔离 final-script artifact**，不是 r47 source/import/default entry。`candidate/INTEGRATION.md` 说明：未来需把插入应用到 base PAGE click handler（再经 r24 装配）、重新生成 canonical/full PAGE 并绑定 hash；helper 本身不变。r50 未做这些接入；未来 runtime 另行授权。

## 3. 目标 B：pre-click sync 原型与比较

### 3.1 原型与语义

`prototype/preclick_sync.js`（SHA `ff595fbe12185c9cb02f768540f8ac124c25938915319b828dc606f9f9379a06`），disabled-by-default、未被 PAGE/helper import：

- 仅 bounded read-only `/api/status`（由 `rt.readStatus` 注入）；无 `/frame.png` 额外加载、无 key/confirm/pin/ARM 写；
- 默认 `maxWaitMs=200`、`sampleIntervalMs=50`、`requiredStableSamples=2`、`maxAttempts=3`、`reserveMs=500`；`deadline=min(now+200,due-500)`；不重置/不重置 arm；
- 要求 displayed frame loaded、fresh status ready、frame SHA/gen 与 displayed 相同连续 2 样本；sequence 只记录；
- fresh 与 displayed 不同：立即 `displayed_frame_superseded` 拒绝并要求重新看图，不自动重绑、不自动选择新帧；
- not ready：最多 3 次有界重试后拒绝；
- expiry/identity 变化：click 前拒绝；
- 返回 allow 后调用者至多一次原 `b.click()`；原型自身 `key_calls=0`、`confirm_calls=0`、`pin_calls=0`、`arm_reset=false`；原 PAGE 最终 freshness/完整 identity 门始终保留。

### 3.2 比较结果

`tests/preclick_compare.cjs` + `receipts/preclick-compare.json`（fake DOM/fake clock，actual baseline PAGE + helper；prototype 只在 allow 后进入 PAGE）：

| scenario | baseline | prototype | key POST | reads / waited | 结论 |
|---|---|---|---|---|---|
| same frame | accepted key1 | allow→accepted key1 | 1/1 | 2 / 50.5ms | 无准入收益；+50.5ms |
| r48 attempt1 changed | not_posted key0 | pre-click refuse, no attempt, key0 | 0/0 | 1 / 0.25ms | 无准入收益；更早拒绝但改变 attempt/recovery 记账 |
| r48 attempt2 changed | not_posted key0 | pre-click refuse, no attempt, key0 | 0/0 | 1 / 0.25ms | 同上 |
| prepared then changed | not_posted key0 | allow→PAGE not_posted key0 | 0/0 | 2 / 50.5ms | 无收益；加延迟 |
| never ready | not_posted key0 | pre-click refuse after 3 reads, key0 | 0/0 | 3 / 100.75ms | 无收益；有界成本 |
| expired arm | no click key0 | pre-click refuse key0 | 0/0 | 0 / 0 | 无收益 |
| identity changed | no click key0 | pre-click refuse key0 | 0/0 | 0 / 0 | 无收益 |

`summary`：`no_changed_frame_accepted=true`；`same_frame_only_accepted=['same_frame_normal']`；`all_key_posts_equal=true`；`all_confirm_equal=true`；`one_click_max=true`。**没有变化帧被接受**；同帧仅有额外延迟。changed-frame 的 pre-click 拒绝避免了一个 PAGE not_posted attempt/recovery，但改变 attempt/recovery 记账，不能证明菜单/准入改善。因此 **不集成**，保留为失败比较证据；未来验证/政策启用另行决定。

## 4. 事实/限制

**事实：** candidate diff/static audit；r48 两例等价；identity/lifecycle direct PAGE 等价；accepted key1 等价；expired recovery 等价；B 原型无变化帧接受；B 每例 key POST 与 confirm disabled 与 baseline 一致；input 16 项未变；test 5/5 通过。

**限制：** fake DOM/fake clock，不是 real browser/network；latency 是 synthetic read/interval，不是实测网络；没有真实视觉确认（confirm 只用 disabled/静态审计等价）；A 候选未集成；B 未集成；不声称 CPU/FIFO/guest/menu/FX6 结果。

## 5. 交付/回执

- `REPORT.md`、`RESULT.json`、`DESIGN-r50.md`、`SHA256SUMS`。
- `candidate/PAGE-script-obs-v2.canonical.js`、`.served.js`、`candidate/DIFF-obs-v2.patch`、`candidate/PAGE-IDENTITY-CANDIDATE.json`、`candidate/INTEGRATION.md`。
- `prototype/preclick_sync.js`（disabled）。
- `tests/admission_compare.cjs`、`tests/preclick_compare.cjs`、`make_candidate.py`、`verify_candidate.py`、`run_all.py`。
- `receipts/candidate-build.json`、`candidate-static-audit.json`、`admission-compare.json`、`preclick-compare.json`、`test-run.json`、输入前后/compare、raw stdout/stderr。
- 旧失败：r48 failed、r45 failed/cleanup unknown；无新 VM 授权。**r50 成功仅指离线候选/比较证据完成，不代表真实菜单/提速/FX6 通过。**
