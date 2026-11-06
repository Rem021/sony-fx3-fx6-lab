# FX3 r49（v2 修正版）｜r48 MENU 帧准入拒绝与 command-entry 时序归因

- Task：`task_1570d1fe8f1b`
- Dispatch：`ctx_8c5041207422`
- 状态：**离线诊断完成（证据完整）；不是菜单/FX6 通过。**
- 只读 r48/r47/native/历史资料；只写本 `r49-frame-admission-analysis`；未启动/接触 VM、browser、server、QMP、guest；未接触外部 FX6；未改运行政策/源码/旧封存。
- 旧 r49 报告/回执已原样保存到 `superseded/pre-correction/`（不删）；本文件是修正后的 active 版本。

## 0. 修正结论先行

1. **帧拒绝仍是 PAGE 点击 handler 的 freshness 分支，不是 identity/lifecycle。** 两次 click 的 host 26 项预检均通过、`click_invoked`；PAGE 的 fresh `/api/status` 看到更新帧：
   - attempt 1：`gen19/seq120/e014…` → `gen20/seq128/2914…`
   - attempt 2：`gen43/seq231/e014…` → `gen44/seq235/2914…`
   PAGE canonical 第 304–305 行实际为真的项只有帧 freshness 三项：
   `preflight.frame.PNG_sha256 !== clickedSHA`、
   `preflight.frame.content_generation !== clickedGeneration`、
   `!frameLoadedFor(preflight)`。
   identity/lifecycle 项为假（同 launch/run/document/timeOrigin，steps=0、phase=ready、ready=true、busy=false、review_required=false、error=null、render_valid=true）。
2. **sequence 变化只是观测字段，不是 PAGE 301–308 的直接相等门。** PAGE 304–305 只比较 SHA、content_generation 和 `frameLoadedFor`（后者用 SHA/gen）；sequence 在 HAR/status 中也变了（+8/+4），但不在直接门里。不得把 sequence 变化写成 PAGE 直接 gate term。
3. **native phases 已知，旧“无 phases.first_kinds”是漏读，不是 unknown。** `startup-observation.json`：
   - `phases.first_kinds` = startup offset 0、cleanup offset **6077228**、after_cleanup offset **6260972**；
   - `ready` 首次 `qualified=true && evaluation_complete=true` 的 startup offset = **3490401**；
   - `errors={}`，`stage=after_cleanup`，`ready_incomplete=null`；`phases`/`ready`/`headers` 的 `evicted_transitions=0`、`first_kind_omitted=0`；
   - `ready.last` 在 offset 6077228（stage startup，host_received 476845162442041），带 `seq235/2914…`；cleanup phase 在 6077228 host_received 476845216322916；after_cleanup 6260972 host_received 476847484541750。
   - cleanup receipt 中的 later `serial_bytes_before_cleanup=6082916` **不是 phase/cutoff**，本报告不用它替代 6077228。
4. **command-entry 已用 r41 `parse_command_timing.py` 实际解析。** 以 3490401（startup 首次 qualified/evaluation_complete）和 6077228（首 cleanup）为 cutoff：
   - startup cutoff 3490401：84 records、76 known durations、67 known same-thread gaps、8 malformed/interleaved unknown、29845 complete other lines。
   - precleanup cutoff 6077228：211 records、190 known durations、168 known same-thread gaps、21 malformed/interleaved unknown、58569 complete other lines。
   - 示例：`seq0 entry_ns=38288877008 end_ns=38351201008 duration=62,324,000ns`；`seq1 entry_ns=38356974000 end_ns=38374215008 duration=17,241,008ns`。
   - **guest-command entry = FX3_GPE104_CMD_RETURN 的 `entry_ns`**；这**不是** boot guest-entry。`phases.startup.serial_offset=0` 是 host startup observation 起点，不是 boot guest-entry 时间；boot guest-entry exact timestamp 仍 unknown。
   - parser `clock_domain` 为 guest CLOCK_MONOTONIC only；same-thread adjacent gap 可能包含未观测活动，**不推断 CPU/FIFO 空闲或 HTTP 提速**。
5. **HAR `startedDateTime`→performance 的映射是近似 wall-clock 映射。** 旧报告中的 1.0ms 精度不能写成同一单调时钟直接实测；frame 变化只能定位在“最后旧帧观测→fresh preflight 读取”之间，不能限定为点击后 1ms 内。两次 click 的近似值见第 4 节。
6. **视觉纠正：** `recovery-before` 截图没有 `NO CARD`；`initial-standby` 和 `recovery-after` 有。r48 原报告“三图均 NO CARD”不精确；old r48 sealed 未改；这不能直接断言 native 闪烁为根因。
7. **DESIGN：** pre-click stabilization 是**一种待验证候选**，不是“唯一/最佳设计”（无比较证据）；离线准备可在既有可逆优化授权内做，未来运行/政策启用另行决定；本设计不自设额外权限门。
8. **本任务仅修正诊断，不实施行为变更。** r48 仍 failed、唯一 Start 已耗用；r45 仍 failed/cleanup unknown；无新 VM/browser/server/QMP/guest。

---

## 1. 输入与只读边界

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- r48 终审 `r48-coordinator-final-review.json` SHA256 `efbc476f1f035a6cbd2e4918805d8fbd2753b79148a7885e60ef44e0f714d8d6`；r48 run SHA256SUMS `4640192527daa51c3bdb006a64d768016714657a3254256f4e773b120eb6428f`（187 项）。
- native run：`.../runs/v47runtime-n64-r47-f1be5a01`。
- 只读 native 输入 hash：
  - `startup-observation.json` `fd1c04729ca47ce155a009ea79ef9b1912d17af68b5924716fe36aab1458529b`；
  - `serial.log` `0d31f76a9406dd77611fb7f8af11fabcfffa30912efced6dfe47ba433a18da0d`；
  - r41 parser `594b03cef5fa4c3b9f81ce1076222c45618d83b959be851722307d0287dafc0e`。
- 实际 PAGE/helper（r47 候选只读）：canonical `f9a428…`，final served `a90a82…`，`planned_navigation_click.js` `6e1205…`。
- 旧 r49 版本保留：`superseded/pre-correction/`；旧 REPORT `b99ae3d7…`、旧 RESULT `649dfea9…`、旧 design `9f0a7314…`、旧 manifest `a59a609f…`（不删）。
- r49 输入前后封存 31 项：`receipts/before-input-seal.json` / `after-input-seal.json`，`changed=[]`、`unchanged=true`。

## 2. native `startup-observation.json` 的 schema/errors/limits/eviction/offset

事实（只读）：

| 字段 | 值 |
|---|---|
| schema | `fx3-startup-observation-r30-v1` |
| saved / flush_attempted | true / true |
| errors | `{}` |
| stage | `after_cleanup` |
| ready_incomplete | null |
| limits | header_recent 48、ready_recent 32、phase_recent 8、first_kind_per_stream 32、marker_whitelist 14、serial_carry_bytes 42、file_bytes 262144 |
| header_counts | bad_magic 91、valid_seq0 2、valid_positive 64 |
| headers | 157 observations、4 transitions、recent_limit 48、evicted 0、first_kind_omitted 0 |
| phases | 3 observations、3 transitions、recent_limit 8、evicted 0、first_kind_omitted 0 |
| ready | 1230 observations、6 transitions、recent_limit 32、evicted 0、first_kind_omitted 0 |
| serial | bytes 6260972、consumed_offset 6260972、carry_bytes 42 |
| markers | 14 |

`phases.first_kinds`：

| stage | serial_offset | host_received_ns |
|---|---:|---:|
| startup | 0 | 476767085622916 |
| cleanup | **6077228** | 476845216322916 |
| after_cleanup | **6260972** | 476847484541750 |

`ready.first_kinds` 共 6 条；第一次 `qualified=true && evaluation_complete=true` 在 **startup offset 3490401**（host_received 476817961827500）；`ready.last` 在 offset 6077228（host_received 476845162442041），`validated_ring_identity` 为 `seq235 / 2914…`。

边界：

- startup phase 使用 `[0,6077228)`；首次 startup qualified/evaluation_complete 为 3490401；cleanup 从 6077228 开始；after_cleanup=6260972。
- `startup-observation` 的 cleanup receipt `serial_bytes_before_cleanup=6082916` 是 later 值，**未用于** phase/cutoff；不替代 6077228。
- `phases.startup.serial_offset=0` 是 host observation 起点，**不是 boot guest-entry**；exact boot guest-entry 仍 unknown。

## 3. r41 command-entry 实际解析器调用

- parser：`.../r41-command-entry-timing-candidate/parse_command_timing.py`，SHA `594b03ce…`。
- 实际调用（详见 `receipts/parser-invocation.json`）：

```sh
python3 -B .../parse_command_timing.py .../serial.log \
  --run-id v47runtime-n64-r47-f1be5a01-startup \
  --cutoff-byte 3490401 \
  --output .../receipts/command-entry-parse-startup-3490401.json

python3 -B .../parse_command_timing.py .../serial.log \
  --run-id v47runtime-n64-r47-f1be5a01 \
  --cutoff-byte 6077228 \
  --output .../receipts/command-entry-parse-6077228.json
```

| cutoff | records | known durations | known same-thread gaps | unknown | ignored complete other lines |
|---|---:|---:|---:|---|---:|
| 3490401 startup-first-qualified | 84 | 76 | 67 | `malformed_or_interleaved_record: 8` | 29845 |
| 6077228 first cleanup | 211 | 190 | 168 | `malformed_or_interleaved_record: 21` | 58569 |

- examples:
  - `seq0`: `entry_ns=38288877008`, `end_ns=38351201008`, duration `62,324,000 ns`;
  - `seq1`: `entry_ns=38356974000`, `end_ns=38374215008`, duration `17,241,008 ns`.
- parser `clock_domain`: guest CLOCK_MONOTONIC only；`duration` 是 adapter entry→return-marker sample；same-thread gap 可能含未观测活动。**不推断 CPU/FIFO 空闲、HTTP 延迟或加速。**
- **guest-command entry**（FX3_GPE104_CMD_RETURN `entry_ns`）与 **boot guest-entry** 不同；后者 exact timestamp 仍 unknown。
- unknown/interleaved 计数原样保留（8/21）；没有把 malformed 记录丢弃后重算通过率。

## 4. HAR 帧变化与两次 click

POST：`/api/start`（15:38:07.205552Z）、`/api/stop`（15:39:20.008865Z）、`/api/final-ack`（15:39:22.379295Z）；`/api/key` **0**。

| 字段 | attempt 1 | attempt 2 |
|---|---|---|
| click receipt | `click_invoked`，26 checks true | 同 |
| clicked/loaded frame | `gen19/seq120/e014…` | `gen43/seq231/e014…` |
| fresh preflight | `gen20/seq128/2914…` | `gen44/seq235/2914…` |
| last tick → click（approx） | 264.456ms | 32.833ms |
| click → preflight（approx） | 1.329ms | 1.039ms |
| last tick → preflight（approx） | 265.785ms | 33.872ms |
| PAGE outcome | `not_posted / preflight_identity_or_lifecycle_changed / mutation_called=false` | 同 |

**时钟边界：** HAR `startedDateTime` 与 `document_time_origin` 的映射是近似 wall-clock epoch 映射，不是同一单调时钟直接实测；上面的 1.0ms 数字不能当 exact monotonic。frame 变化只能定位在最后旧帧观测（last tick）与 fresh preflight 读取之间；click snapshot 位于该区间内；**不能把 frame 变化限定为点击后 1ms 内**，也不能断言它发生在 click 前还是后。

## 5. 分支判定与 sequence 语义

PAGE canonical 第 108 行 `frameLoadedFor` 使用 SHA/gen/render_valid，不使用 sequence；第 304–305 行实际为真的 freshness 项：

1. `preflight.frame.PNG_sha256 !== clickedSHA`；
2. `preflight.frame.content_generation !== clickedGeneration`；
3. `!frameLoadedFor(preflight)`。

identity/lifecycle 项均 false：steps 0、phase ready、ready true、busy false、review_required false、error null、render_valid true、launch/run/document/timeOrigin 不变、page identity 全 true。

**sequence：** 是 status/HAR 中的**观测字段**，两次确实变化（120→128、231→235），但 PAGE 301–308 不直接比较 sequence；本报告不把 sequence 写成直接 gate term。`failing_frame_terms` 仅列出上述三项。

## 6. 采样节奏与两次状态观察

- PAGE tick 400ms；HAR status 间隔中位数 **405.3ms**。
- host 26 项预检读取 `lastStatus`/displayed（来自最后 tick，不自己发 fresh status）；PAGE handler 随后执行 fresh `/api/status`。
- attempt1 最后 tick 到 click 约 264.5ms，attempt2 约 32.8ms；fresh preflight 读取在 click 快照后约 1.0–1.3ms（**approx wall-clock**）。
- 两次观察不检查同一帧：最后一次 tick 是旧帧，PAGE fresh 请求看到新帧；这是采样节奏与两次观察共同放大的竞态。freshness 是设计上的第二道门，不能去掉；去掉会放行旧图。

## 7. 实际 PAGE/helper 离线重放

`replay/replay.cjs` 在 fake DOM 中装载实际 PAGE（canonical f9a428… / served a90a82…）与实际 `planned_navigation_click.js`（6e1205…），fake alarm/fetch；无 browser/server/network/VM。

结果（`receipts/page-helper-replay.json`）：

| case | clicked → preflight | helper | PAGE outcome | `/api/key` |
|---|---|---|---|---|
| attempt1 | gen19/120/e014 → gen20/128/2914 | click_invoked，failed_checks=[] | not_posted | 0 |
| attempt2 | gen43/231/e014 → gen44/235/2914 | 同 | not_posted | 0 |

负例（实际 PAGE recovery eligibility）：wrong attempt_id → `binding_mismatch`；expired due → `document_or_alarm_mismatch`；accepted attempt（fake `/api/key` 正例控制）→ `attempt_not_proven_unqueued`。正例控制仅验证状态机，不是 guest 输入。

## 8. 视觉纠正

| 图 | SHA256 | 实际观察 |
|---|---|---|
| `initial-standby/current.png` | `4854157c…` | 相机待机 UI；`NO CARD` 可见；无菜单 |
| `recovery-before` | `7cf47832…` | 相机待机 UI；**无 `NO CARD` 文字**；无菜单 |
| `recovery-after` | `4e9c654e…` | 相机待机 UI；`NO CARD` 可见；无菜单 |

r48 原报告“三图均 NO CARD”不精确；本报告纠正，old r48 sealed 未改。该差异是观测事实，不能直接断言 native OSD 闪烁是帧变化根因。

## 9. 事实 / 推断 / unknown（修正版）

**事实：**

- HAR 只有 start/stop/final-ack POST，`/api/key`=0。
- 两次 click 的 26 项 host 预检通过；PAGE 随后 `not_posted/mutation_called=false`。
- clicked/preflight 帧如第 4 节；identity/lifecycle 项保持通过；三项 freshness 为真；sequence 变化是观测字段，不是直接 gate。
- native phases.first_kinds 为 0/6077228/6260972；startup 首次 qualified/evaluation_complete 为 3490401；errors/limits/eviction 如第 2 节。
- r41 parser 在 3490401/6077228 得到 76/190 known durations、67/168 gaps、8/21 interleaved unknown；seq0/1 示例保留。
- 实际 PAGE+helper 重放两次 not_posted，0 api/key；负例拒绝。
- recovery-before 无 NO CARD；initial/after 有。

**推断（有限）：**

- PAGE 最后 tick 快照最多陈旧约 400ms；PAGE fresh preflight 在 click 快照后约 1ms（approx）看到新帧。
- 两次状态观察放大旧快照/新帧竞态。
- frame 内容/代次在最后旧观测与 fresh 读取之间变化。

**unknown：**

- `e014→2914` 的 native/OSD 根因；NO CARD 差异是否因果；raw frame-pixel 差异。
- exact boot guest-entry；`phases` 之外/更后 interaction cutoff（不要用 later 6082916 替代已保留的 6077228）。
- CPU/FIFO/HTTP 延迟；pre-click stabilization 是否通过；任何代码/政策变更授权。

## 10. 最小改进（仅设计，不实现）

详见 `DESIGN-MINIMAL-IMPROVEMENT.md`：

1. **obs_v2（无政策变更）：** 记录 last_tick_frame、fresh_preflight_status_frame、frame_loaded_for_preflight 和精确 predicate 布尔；不改门。
2. **pre-click stabilization（一种待验证候选）：** click 前 fresh `/api/status` 要求帧身份等于 PAGE displayed frame（或短时 stable hold），再点击；保留 PAGE freshness；无 retry；60s 内。**不是唯一/最佳设计，无比较证据，需要离线验证和政策/时序批准。** 现有可逆优化授权仅允许离线准备；未来运行/政策启用另行决定。
3. **new-frame notice（UX）：** 拒绝时显式呈现新帧并要求操作者重新点击；不改门。

拒绝捷径：去掉 freshness、白名单 NO CARD/e014/2914/已知 generation、按 hash 稳定自动通过、无限/自动重试、自动合并 pin/confirm。r49 不实现行为变更。

## 11. 交付/证据

- `REPORT.md`（本文件）、`RESULT.json`、`DESIGN-MINIMAL-IMPROVEMENT.md`、`SHA256SUMS`。
- `receipts/startup-observation-audit.json`、`parser-invocation.json`、`command-entry-parse-startup-3490401.json`、`command-entry-parse-6077228.json`、`command-entry-timing.json`、`har-transitions.json`、`page-helper-replay.json`、`visual-correction.json`、`frame-admission-findings.json`、`test-run.json`、输入封存/compare、raw logs。
- 复现脚本：`startup_observation_audit.py`、`run_parser.py`、`analyze_har.py`、`replay/replay.cjs`、`analyze_timing.py`、`analyze_visual.py`、`analyze_findings.py`、`run_all.py`。
- 旧版本：`superseded/pre-correction/` 原样保留（不删）。
- **r49 成功仅表示离线证据完整；不表示八步菜单/FX6/提速通过。** r48 failed；r45 failed/cleanup unknown；本任务无新 runtime。
