# FX3 r49｜r48 两次 MENU click 帧准入拒绝的离线归因

- Task：`task_1570d1fe8f1b`
- Dispatch：`ctx_8c5041207422`
- 状态：**离线诊断完成（证据完整）；不是菜单/FX6 通过。**
- 范围：只读 r48/r47/旧证据；只写本 `r49-frame-admission-analysis` 目录；未启动/接触 VM、browser、server、QMP、guest；未接触外部 FX6 任务/进程；未改运行政策、源码、测试或旧封存。
- r48 的唯一 Start 已耗用；本任务不重跑、不重试、不产生新 runtime。

## 0. 结论先行

1. **拒绝发生在 PAGE 点击 handler 的 freshness 分支，不是 identity/lifecycle 分支。** 两次 click 的 host 26 项预检都通过并 `click_invoked`；随后 PAGE 自己的 fresh `/api/status` 看到比点击快照更新的帧：
   - attempt 1：`gen19/seq120/e014…` → `gen20/seq128/2914…`
   - attempt 2：`gen43/seq231/e014…` → `gen44/seq235/2914…`
   PAGE canonical 第 304–305 行的 OR 条件中实际为真的三项是：
   `preflight.frame.PNG_sha256 !== clickedSHA`、
   `preflight.frame.content_generation !== clickedGeneration`、
   `!frameLoadedFor(preflight)`。
   identity/lifecycle 项为假（同 launch/run/document/timeOrigin，steps=0，phase=ready，ready=true，busy=false，review_required=false，error=null，render_valid=true）。
2. **这是帧内容/代次/序列变化，不是步骤或身份变化。** PNG SHA 改变、content_generation +1、sequence +4/+8；steps/phase/ready/busy/review/error/render/launch/run/document/timeOrigin 均未变。HAR 只有 `/api/start`、`/api/stop`、`/api/final-ack` 三个 POST，**没有 `/api/key`**。
3. **采样节奏和两次状态观察放大了竞态。** PAGE tick 为 400ms；click 快照使用最近一次 tick 的 `lastStatus`/displayed 帧（attempt 1 的最后 tick 距 click 264.5ms；attempt 2 为 32.8ms）；PAGE handler 的 fresh preflight 在 click 快照后约 1.0–1.3ms 读到新帧。第一次观察最多可陈旧一个 tick；第二次观察 fresh，两帧不一致，因此拒绝。median status 间隔 405.3ms。
4. **实际 PAGE + 实际 `planned_navigation_click.js` 离线重放复现两次 `not_posted`**，且拒绝场景 `/api/key` 计数为 0；负例 wrong identity、expired due、accepted attempt 仍被拒绝。回执 `receipts/page-helper-replay.json`。
5. **视觉纠正：** coordinator 实际查看 `recovery-before` 截图没有 `NO CARD` 文字；`initial-standby` 和 `recovery-after` 有。r48 原报告把三图都说成 `NO CARD` 不精确；本报告只在新目录纠正，不改旧封存。**该差异不能直接断言原生闪烁是根因。**
6. **最小改进仅设计、不实现。** 观测增强（记录 last tick/fresh preflight/exact predicate）不需要政策变更；pre-click frame stabilization 需要 60s 内新增等待/时序政策批准；不得去掉 freshness、白名单闪烁、按 hash 稳定自动通过或无限重试。

---

## 1. 输入与只读边界

- 卷 UUID：`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- r48 终审：`r48-coordinator-final-review.json` SHA256 `efbc476f1f035a6cbd2e4918805d8fbd2753b79148a7885e60ef44e0f714d8d6`；其中独立 HAR 复核与 visual correction 已记录。
- r48 run：`r47-runtime-integration-candidate/run-inputs/f9c618eedbad`；run `SHA256SUMS` `4640192527daa51c3bdb006a64d768016714657a3254256f4e773b120eb6428f`（187 项）。
- r48 HAR：`cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/traffic.har`；本目录只读解析。
- 实际 PAGE/helper（r47 候选，只读）：
  - canonical PAGE `sha256=f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`；final served script `a90a82c1b4b30d12ef298272f65cb643a74c8c491a02e88a71fdb14851f3cb5b`。
  - `planned_navigation_click.js` `sha256=6e120517b1c785bb3eb277268908801465dd55dc0bda5901cfaa2be4fc7175e0`。
- r49 输入封存：`receipts/before-input-seal.json`（31 项）与 `receipts/after-input-seal.json`；`input-seal-compare.json` 显示 `changed=[]`、`unchanged=true`。

## 2. HAR 事实：只有 start/stop/final-ack，无 api/key

HAR 的 POST：

| UTC | path | HTTP |
|---|---|---|
| 2026-11-05T15:38:07.205552128Z | `/api/start` | 202 |
| 2026-11-05T15:39:20.008865024Z | `/api/stop` | 202 |
| 2026-11-05T15:39:22.379295232Z | `/api/final-ack` | 200 |

`/api/key` POST 计数：**0**。这与 PAGE 拒绝在 mutation 前一致；不是“已发送但结果未知”。

## 3. 两次 MENU click 的精确字段与时间顺序

| 字段 | attempt 1 | attempt 2 |
|---|---|---|
| click receipt | `status=click_invoked`，26 checks 全 true，`failed_checks=[]` | 同 |
| nonce | `5e23d534-a3dd-4645-9e02-6f8d0a1c84b0` | `59ac034b-3fb2-4bd8-bebb-dab642b13196` |
| attempt_id | `79e01010-68a7-4deb-9a07-176b6937343f` | `465af599-4c73-4f97-ba8a-55ccd3e90565` |
| clicked frame | `gen19 / seq120 / e0140ea1…` | `gen43 / seq231 / e0140ea1…` |
| loaded at click | `displayed_sequence=120, shown_sequence=120, generation=19, sha256=e014…` | `231/231/43/e014…` |
| status_frame at click | `gen19/seq120/e014…` | `gen43/seq231/e014…` |
| last tick before click | 15:39:04.413544960Z，`gen19/seq120/e014…` | 15:39:19.896267776Z，`gen43/seq231/e014…` |
| click snapshot `alarm.now_ms` | 61618.90000003576 | 76870.0 |
| fresh preflight status | 15:39:04.679329024Z，`gen20/seq128/2914…` | 15:39:19.930139136Z，`gen44/seq235/2914…` |
| last tick → click | 264.456ms | 32.833ms |
| click snapshot → preflight | 1.329ms | 1.039ms |
| PAGE outcome | `not_posted / preflight_identity_or_lifecycle_changed / mutation_called=false` | 同 |
| created → updated (page perf) | 61619.4 → 61623.1ms | 76870.1 → 76871.5ms |

时间映射方法：HAR `startedDateTime` 减去 click receipt 的 `document_time_origin`（`1793893083059.1` ms），与 click receipt 的 `performance.now`/alarm `now_ms` 对齐；这是同一页面时钟的只读重建，不做 guest/host/browser 跨域强减。

## 4. 分支判定：freshness，而不是 identity/lifecycle

PAGE canonical 第 108 行：

```
frameLoadedFor(s) = !!s.frame && displayed>0 && shownSHA===s.frame.PNG_sha256 &&
                    displayedGeneration===s.frame.content_generation && s.render_valid && !renderFault
```

PAGE canonical 第 302–309 行是点击 handler 的组合门。两次实际为真的 freshness 项完全一致：

| 项 | attempt 1 | attempt 2 |
|---|---|---|
| `preflight.frame.PNG_sha256 !== clickedSHA` | true（e014≠2914） | true |
| `preflight.frame.content_generation !== clickedGeneration` | true（20≠19） | true（44≠43） |
| `!frameLoadedFor(preflight)` | true（displayed gen 19/43 ≠ preflight 20/44） | true |
| `preflight.sequence !== clicked sequence` | true（128≠120） | true（235≠231） |
| `shownSHA !== clickedSHA` | false（仍 e014） | false |
| `displayedGeneration !== clickedGeneration` | false（仍 19/43） | false |
| `!frameLoadedFor(lastStatus)` | false（lastStatus 仍是点击帧） | false |
| `lastStatus.steps !== clickedStep` | false（0=0） | false |
| steps/phase/ready/busy/review/error/render | 全部不变 | 全部不变 |
| page document/timeOrigin/launch/fingerprint | 全部 true | 全部 true |

**结论：** 拒绝分支是帧新鲜度 OR；不是 identity/lifecycle 分支，也不是 step 变化。原因字符串 `preflight_identity_or_lifecycle_changed` 是组合标签，不能单独当作身份失败。

## 5. content vs sequence vs identity/lifecycle

**事实：**

- `content_generation`：19→20 / 43→44（+1）。
- `sequence`：120→128 / 231→235（+8/+4）。
- `PNG_sha256`：`e0140ea1…`→`2914275c…`（像素内容 SHA 变化）。
- steps=0、phase=ready、ready=true、busy=false、review_required=false、error=null、render_valid=true。
- launch/run/document/timeOrigin 在 click 回执与 fresh status 中一致；page identity 全部 true；alarm nonce/due/armed 未变。

**分类：** 这是 **frame content/generation/sequence change**，不是 step/identity/lifecycle change。HAR 不能证明 `2914…` 与 `e014…` 的语义差异；`NO CARD` 视觉差异只是在全页截图上观察到，不能替代 raw frame-pixel 比较。

## 6. 采样节奏与“两次状态请求”是否放大竞态

**事实：**

- PAGE tick 间隔 400ms（源码 `setTimeout(tick,400)`）；本 HAR 中 status 间隔中位数 **405.3ms**。
- host `planned_navigation_click.js` 的 26 项预检读取 `lastStatus`/displayed（来自最近 tick），不自己发 fresh HTTP status；PAGE 点击 handler 随后执行 fresh `GET /api/status`。
- attempt 1：最后 tick 到 click 264.5ms；click 到 preflight 1.33ms；新帧在 fresh preflight 中。
- attempt 2：最后 tick 到 click 32.8ms；click 到 preflight 1.04ms；新帧在 fresh preflight 中。
- 两次观测并不检查同一个帧：第一次是 tick 的旧快照，第二次是 PAGE 的 fresh 请求。

**推断（有限）：** 400ms tick + 异步 fresh preflight 形成了“旧快照→点击→fresh 状态”的窗口；新帧在窗口内出现时，第二次观测会正确拒绝。这是采样节奏与两次观测共同放大的竞态；但不能据此断言新帧在点击前还是点击后提交，也不能断言 native/OSD 原因。**freshness 不能去掉**：去掉会把旧图点击放行，违反本任务和 r47 的视觉确认/未入队语义。

## 7. 实际 PAGE/helper 离线重放

`replay/replay.cjs` 在 fake DOM 里装载：

- 实际 r47 canonical/served PAGE（`f9a428…` / `a90a82…`）；
- 实际 `operator-helpers/planned_navigation_click.js`（`6e1205…`）；
- fake alarm 60000ms、fake `/api/status`/`/frame.png`/`/api/key`；无 browser/server/network/VM。

结果（`receipts/page-helper-replay.json`）：

| case | clicked → preflight | helper | PAGE outcome | `/api/key` POST |
|---|---|---|---|---|
| attempt1 | `gen19/120/e014` → `gen20/128/2914` | `click_invoked`，failed_checks=[] | `not_posted`，reason 同 | 0 |
| attempt2 | `gen43/231/e014` → `gen44/235/2914` | 同 | 同 | 0 |

负例（实际 PAGE recovery eligibility）：

- wrong attempt_id → `{eligible:false, reason:'binding_mismatch'}`。
- expired due → `{eligible:false, reason:'document_or_alarm_mismatch'}`。
- accepted attempt（fake `/api/key` 正例控制）→ `{eligible:false, reason:'attempt_not_proven_unqueued'}`；该正例仅验证状态机，**不是 guest 输入**。

`planned_navigation_click.js` 的实际接口点：第 88 行 `click_time_frame`（shownSHA/displayedGeneration/displayed），第 102 行 `b.click()`，第 106 行 `status=click_invoked`。PAGE handler 的 fresh preflight 与 26 项 host 预检分离，是两次观察。

## 8. 视觉纠正（旧 r48 报告不精确）

- `initial-standby/current.png`：`NO CARD` 可见；FX3 相机待机 UI；无菜单。SHA `4854157c…`。
- `recovery-before`（`step-01-attempt-01/recovery-review/observation.png`）：**没有 `NO CARD` 文字**；仍是相机待机 UI；无菜单。SHA `7cf47832…`。
- `recovery-after`（`recovery-cancel/observation/observation.png`）：`NO CARD` 可见；仍是相机待机 UI；无菜单。SHA `4e9c654e…`。

r48 原报告“三图均 NO CARD”不精确；本报告纠正，但**不修改旧 r48 封存**。这一视觉差异是观测事实；不能据此直接断言 native OSD 闪烁是帧变化根因，也不能把 `NO CARD` 当成菜单语义。

## 9. command-entry 时序只读解析（边界明确）

| 边界 | 值 |
|---|---|
| `/api/start` POST | 15:38:07.205552Z |
| `FIRST-FRAME-CLOCK` | 15:38:07.643264Z；`start_monotonic=476772.34903925`，limit 180s |
| `FIRST-FRAME-PASS` | 15:38:53.299233Z |
| 首帧等待（start_monotonic→pass） | **46.1047566s**（<180s） |
| `/api/start`→首帧 | 46.093681s |
| initial-standby | 15:38:53.298729Z；page `performance_ms` before/after 50176.4/50237.4；firmware gen4/seq13/2914…；截图 SHA `4854157c…` |
| attempt1 identity / arm | 15:39:04.540793 / 15:39:04.596（ENDED-STATE events） |
| attempt2 identity / arm | 15:39:19.790157 / 15:39:19.847 |
| `/api/stop` POST | 15:39:20.008865Z |
| `/api/final-ack` POST | 15:39:22.379295Z |
| cleanup result | 15:39:22.817800Z；status completed |
| native duration / key_steps / menu_verified | 75.0913468s / 0 / false |

实际运行 argv：`ACTUAL-RUNNING-ARGV.json` 的 `ps` 与 native `command.json` 是双证据；QEMU `bf4d4648…`、`-cpu cortex-a35`、`-smp 4`、`-m 5120`、`-accel tcg,thread=multi`、无 `-icount`、kernel `da4a66…`、CPIO `59c585…`、DTB `5aa2be…`、地址 `0x440000000`。`ACTUAL-ARGV-PREPARED` 只作为 prepared，不冒充 actual。

**明确 unknown：**

- 无 `phases.first_kinds` 产物 → 交互截止 serial offset **unknown**；不拿 `serial_bytes_before_cleanup`（cleanup 中为 6082916）或最终 serial 大小替代。
- 无 exact guest-entry marker → command-entry→guest-entry / guest-entry→return **unknown**。
- 不做 guest/host/browser 跨域强减；同线程相邻间隔不证明 CPU/FIFO 空闲或 HTTP 延迟。
- `startup-qmp-timing` 仅 QMP connect/greeting/capabilities（约 0.171s），不是 guest entry。

## 10. 事实 / 推断 / unknown

**事实：**

- HAR 只有 start/stop/final-ack POST，无 api/key。
- 两次 click 的 26 项 host 预检通过，`click_invoked`；PAGE 随后 `not_posted`、`mutation_called=false`。
- clicked/preflight 帧分别为 `19/120/e014 → 20/128/2914`、`43/231/e014 → 44/235/2914`。
- identity/lifecycle 项保持通过；三个 frame-freshness 项为真。
- 实际 PAGE+helper fake DOM 重放复现，拒绝场景 0 api/key；负例拒绝。
- recovery-before 无 NO CARD；initial/recovery-after 有。

**推断（有限）：**

- PAGE 最后一次 tick 的快照最多陈旧约 400ms；PAGE fresh preflight 在 click 后约 1ms 看到新帧。
- 两次状态观察（tick lastStatus + PAGE fresh GET）放大了“旧快照 vs 新帧”的竞态。
- 帧像素内容在窗口内变化（SHA/gen/seq 同时变化）。

**unknown：**

- `e014→2914` 的 native/OSD 根因；NO CARD 差异是否因果；raw frame-pixel 差异。
- exact guest entry、`phases.first_kinds` offset、interaction cutoff。
- CPU/FIFO/HTTP 延迟；pre-click stabilization 是否会让本 run 通过；任何代码变更的授权。

## 11. 最小改进设计（不实现）

详见 `DESIGN-MINIMAL-IMPROVEMENT.md`：

1. **obs_v2（无需政策变更）：** 记录 `last_tick_frame`、`fresh_preflight_status_frame`、`frame_loaded_for_preflight` 和精确 predicate 布尔；不改门、不改视觉确认/输入证据语义；未实现。
2. **pre-click frame stabilization（需要政策/时序变更）：** 在 `b.click()` 前读取 fresh `/api/status`，要求其帧身份等于 PAGE displayed frame（或短时稳定 hold），再点击；保留 PAGE freshness；无自动 retry；在 60s 内；需要批准；未实现。
3. **new-frame notice（UX）：** 拒绝时显式呈现新帧并要求操作者重新点击；不改门；未实现。

**拒绝的捷径：** 去掉/放宽 freshness；白名单 `NO CARD`/e014/2914/已知 generation；按 hash 稳定自动通过；无限/自动重试；合并 pin/confirm 或自动视觉通过。r49 不实现任何源码/政策变更。

## 12. 交付与限制

- `REPORT.md`（本文件）、`RESULT.json`、`DESIGN-MINIMAL-IMPROVEMENT.md`、`SHA256SUMS`。
- 回执：`receipts/har-transitions.json`、`page-helper-replay.json`、`command-entry-timing.json`、`visual-correction.json`、`frame-admission-findings.json`、`test-run.json`、输入封存前后/compare、raw stdout/stderr。
- 复现：`analyze_har.py`、`replay/replay.cjs`、`analyze_timing.py`、`analyze_visual.py`、`analyze_findings.py`、`run_all.py`；全部离线，无 browser/VM/process。
- **r49 成功仅表示证据完整，不是八步菜单/FX6/提速通过。** r48 仍 failed；r45 仍 failed/cleanup unknown；无新 VM 授权。
