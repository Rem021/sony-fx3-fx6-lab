# FX3 r47｜r46 清理/PAGE 修复接入当前运行器的离线集成与自绑定 profile

生成时间：2026-11-05（America/Los_Angeles）
卷 UUID：`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`（已核）
根：`/Volumes/KAFU2T/AI/Projects/Mac`（非 Git 根；未 clone、未复制历史 run/CPIO/大测试矩阵）
本目录：`work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r47-runtime-integration-candidate`

## 0. 结论先行

**r47 已完成离线集成，但没有、也不能声称真实菜单/清理/recovery 通过。**
以 r44 实际 SOURCE 依赖为底建立了自绑定 profile `r47-runtime-integration-60s`、label `v47runtime-n64-r47`、`APPROVED_HOST=本候选目录`，SOURCE/CORE 按真实依赖为 **44/39**（加入本地 base PAGE；不硬维持 43/38）。r46 的 `cleanup.py`/`cleanup_evidence.py` 已接入当前 runtime-wrapper；r44 `trial_web_r24_review_snapshot.py` 已改为显式加载**本候选根目录**的 base PAGE（`BASE=HERE`），不再从旧 `v25-r21-recovery-integration` 载入旧页面；只改 r46 的两个 recovery 预算字面量 20000→60000，base Python server、snapshot TTL 20、live freshness、全部身份/确认/未入队门保持不变。

**实际运行器 import-only 取证：** 执行 `run_trial_r24_review_snapshot.py` 的模块顶层（不调用 main、不启动 spawn/socket），实际 `trial_web_r24_review_snapshot` 的 base 模块为 `.../r47-runtime-integration-candidate/trial_web_v22_navigation_review.py`；最终服务 PAGE 的 canonical script 为 `f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`，完整 PAGE 为 `551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b`。不是运行时字符串替换，也不是“只放一个独立 PAGE 文件但仍旧加载旧文件”。

**清理闭环：** 7/7 通过，但关键点是使用**实际 `_cleanup_once`**（真实写 `dispose-not-invoked`/`ALARM-DISPOSITION`/`body-result`）→ **实际 `certify`** → **实际 `seal`/`validate_reference`/`revalidate`**；browser/ev/dl/resource/native 都是注入假依赖，没有真实 browser、PID 探测、QMP 或 guest。armed 正常、nonarmed 正常，browser 仍 live、nonarmed 缺 dispose、armed 缺 marker、错 nonce、unknown alarm 均拒绝。

**页面闭环：** 4/4 通过。同一 fake DOM 实际装载最终 served PAGE + 最终 `deadline.js`（新 SCRIPT_SHA）+ 最终 `recovery_readonly.js`/`recovery_cancel.js`；复现 r45 的 `gen58/seq1886/e014` → `gen59/seq1892/2914` 帧变化导致 `not_posted/preflight_identity_or_lifecycle_changed/mutation_called=false`，随后取得合法 armed recovery 资格；错 nonce/已 accepted/到期/旧 20s 仍拒绝。`recovery_cancel` 只使用**合成 review** 验证状态机，没有实际截图、实际看图、实际取消/复核/新 nonce 的视觉链；报告明确不把资格检查成功写成完整视觉恢复通过。

**输入与回归：** 套件 9/9 通过（input-seal before、cleanup closed-loop、prepare-only、preflight、import-only、binding-inventory、package-pin、page-runtime、input-seal after）；输入封存 51 项前后 hash 不变；r46 32 项清单 32/32 OK，r45 554/150 清单仍 OK；r42 package/CPIO/DTB 只读复用、未复制/写。**r45 仍 failed、cleanup 仍 unknown；r45 唯一一次运行已耗用，无新 VM 授权；本候选 `enabled_for_real_run=false`。**

---

## 1. 输入、卷与边界

- 卷身份：`diskutil info /Volumes/KAFU2T` → `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；本项目根非 Git 根；未新 clone。
- 输入 pin（首次读入即核，随后在最终封存再次核）：
  - r44 `SOURCE-FREEZE.json=3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c`，`CORE-SOURCE-FREEZE.json=b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1`。
  - r46 `SHA256SUMS=46fec31b6c727803e05937f38a23050dee70cae6bf01934e5545ec9201b8fa96`（32 项，32/32 OK）；`cleanup_evidence.py=b9c511e2c4ecf1ff24a0446a6a462dce86776b58ac983c73db12f811261a00dc`；`cleanup.py=ed3edbb402529acfa84a6fb18ce96720b48cb7b7c1edc1cbc622da9c92b7a1cb`；r46 canonical PAGE `f9a428…`，原 `852c83…`。
  - r42 包 candidate `857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806`、CPIO `59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63`（453213884 bytes）；未复制/写。
  - r45 唯一运行 `failed`、cleanup `unknown`；本报告不升级、不倒改。
- r46 协调器终审的**时间顺序纠正**（本报告采纳；r46 文件未改）：`4302ff41-653d-4ae5-9b79-f713120ab9e2` 是 **11:28:12.079540Z 第一次**；`0687a34f-8dcd-4d62-b4a0-b1c0037830b1` 是 **11:28:20.641615Z 第二次**。r46 REPORT 将 first/second 写反，本报告按 source invocation timestamps 更正；诊断结论不变。
- 输入封存：
  - `receipts/input-seal-before.json`（51 项）`sha256=b32f9371e04e89d26c61dd791b7f342e1cf18af1d56df84d0ea5aa06971d6ede`
  - `receipts/input-seal-after.json`（51 项）`sha256=ea1c31184d8da441cda5068543f2148084ab5cc7e62df6adae850c60cb2fa9ca`
  - `receipts/input-seal-compare.json`：`changed=[]`、`unchanged=true`、`input_count=51`、r46 32/32、r45 554/554、150/150。
  - `receipts/first-read-pins.json` 记录会话首次只读核对的 r44/r46/r42 pin；before/after 文件覆盖最终验证窗口，内容前后完全一致。旧 r44/r45/r46/r42 输入只读，没有 content 改动。
- 全程未启动 VM/browser/server/QMP/guest，未部署；唯一写目录本候选；未改固定平台/固件/CPIO/FX6。`preflight`/`prepare` 仅使用必要宿主子进程（diskutil、parser `--help`），不启动 browser/QEMU。

---

## 2. 问题 A：清理修复真正接入运行器

### 2.1 r46 修复的接入

`runtime-wrapper/cleanup.py` 与 `runtime-wrapper/cleanup_evidence.py` 采用 r46 的严格版本（hash 分别 `ed3edb…`、`b9c511…`）。本候选没有把它们只放在独立测试目录：`common.helper` 的候选路由包含 `deadline_cli.py`/`recovery_tools.py` 等，`cleanup.py` 通过 `common` 的 `CANDIDATE_OPS` 执行候选 `deadline_cli.py`/`deadline.js`；`cleanup_evidence.py` 在候选 runtime-wrapper 内被 `common` 导入。

保留的严格语义（与 r46 一致）：

- armed：不 cancel/dispose；`dispose-not-invoked.json` 保留完整 alarm 身份/nonce/armed/due/digest；不允许存在 `deadline-dispose*`。
- nonarmed：仍要求原 `deadline-dispose` status + rc=0 process；dispose 必须 `sealed=true`、含 `disposed` 事件、current nonce/state/armed/due 与原 alarm 一致；不允许 armed marker 混入。
- `certify` 绑定 `ENDED-STATE` 的 finished/ending/url/document_id/document_time_origin/launch/run_incarnation、End 原按钮回执、browser before active/pid 与 after inactive/pid null、HAR/PNG、native QEMU/observer/reap/PID/exit/API16/quit、双锁与端口；`revalidate` 重新执行同一语义并与 proof 比较 alarm/ended/browser/native/run/document/timeOrigin。
- unknown/malformed/缺证/错身份/仍 live/篡改索引均拒绝；`publish` 的二次完成索引归档保护保留。

### 2.2 实际 `_cleanup_once` 写出 → 实际 `certify` → seal/reference/revalidate

测试文件：`tests/cleanup_closed_loop_test.py`；回执：`receipts/cleanup-closed-loop-tests.json`（7/7）。

测试注入的依赖只有：

- `cleanup.ev/browser/dl/os/socket/write/event`：假实现；`browser` 写 PNG/HAR/process JSON，`dl` 返回 alarm/dispose，`os.kill` 抛 `ProcessLookupError`，`socket.connect_ex` 返回 `ECONNREFUSED`；**没有真实 browser、PID 探测、QMP、VM**。
- `cleanup_evidence.native_evidence` 与 resource probe：注入 fake native/resource 回执，测试结束仍标明不是新 runtime 证据。

用例：

| 用例 | 实际执行 | 结果 |
|---|---|---|
| armed 正常 | `_cleanup_once` 真实写 armed marker → `certify` → `seal` → `validate_reference` → `revalidate` | 7/7 中 PASS；`dispose_invoked=false`、nonce `d1b0d0c4…`、due 61000、End_invoked true、browser before pid 5555/after null、resources closed |
| nonarmed 正常 | 同上，真实写 `deadline-dispose.json` + process，`certify`/seal/revalidate | PASS；`dispose_invoked=true`、classification `valid_nonarmed` |
| browser 仍 live | 实际 `_cleanup_once` 后 after active=true | `browser_close_unproven` 拒绝 |
| nonarmed 缺 dispose | 实际 `_cleanup_once` 的 `dl(dispose)` 抛错，body errors 非空 | `cleanup_body_incomplete` 拒绝 |
| armed 缺 `dispose-not-invoked` | 实际写后删除 marker | `armed_dispose_not_invoked_missing` 拒绝 |
| armed 错 nonce | 实际写后篡改 marker nonce | `armed_dispose_field_identity` 拒绝 |
| unknown alarm | 实际 `_cleanup_once` 写 negative marker | `alarm_identity_malformed` 拒绝 |

这满足“不能只独立调用 `certify` 而手写 marker”的要求：marker 是实际 `_cleanup_once` 写出的，再进入实际 `certify`/`seal`/`validate_reference`/`revalidate`。**测试中的 native/resource 是 mock，不构成新的 runtime 证据。**

### 2.3 r45 清理仍 unknown

本候选没有读取/改写 r45 `4302…`/`0687…` 的 result/CLEANUP/CLEANUP-COMPLETED，也没有把 r45 原 body 重新 certify 成 completed。r46 已经证实原 `4302…` body 完整但被 `cleanup_evidence.py:122` 的 armed 白名单和 `:127` 的 `deadline-dispose` 必需阶段拒绝；本次集成保留该历史 unknown。r45 的原调用顺序按 r46 终审纠正为 11:28:12 首次、11:28:20 第二次。

---

## 3. 问题 B：页面恢复修复真正接入运行器

### 3.1 实际 import 映射

`trial_web_r24_review_snapshot.py` 原为：

```python
BASE = HERE.parent / 'v25-r21-recovery-integration'
spec = importlib.util.spec_from_file_location('fx3_r24_original_web', BASE / 'trial_web_v22_navigation_review.py')
```

r47 改为：

```python
BASE = HERE   # 本候选根目录
```

本候选根目录有 `trial_web_v22_navigation_review.py`，是旧 frozen base 的 patched copy，唯一差异是 r46 的两行：

```diff
-    !h||h.version!==1||h.sealed||h.deadline_ms!==20000||h.expectedURL!==location.href||
+    !h||h.version!==1||h.sealed||h.deadline_ms!==60000||h.expectedURL!==location.href||
-    h.current.due_ms!==h.current.armed_ms+20000||
+    h.current.due_ms!==h.current.armed_ms+60000||
```

测试 `tests/import_only_test.py` 通过 `runpy.run_path` 执行真实 `run_trial_r24_review_snapshot.py` 顶层（**不调用 main**），audit hook 阻断 `subprocess.Popen`/`os.system`/`os.fork`/`os.posix_spawn`/`socket.__new__`；结果 `blocked_import_side_effects=[]`。实际：

- `trial_web_r24_review_snapshot.__file__` 在本候选；
- `trial_web_r24_review_snapshot.base.__file__` 在本候选 `trial_web_v22_navigation_review.py`；
- 最终 `PAGE_SCRIPT_SHA = f9a428…`（与 r46 双行修复一致）；
- 完整 PAGE `sha256=551cbd…`；
- base PAGE 旧 20000 不存在、新 60000 存在；served PAGE 同样。
- `r35_package_selection`、`startup_observation`、`trial_ring_cached`、`trial_log_v4_mss` 在本候选；`qmp_line_transport`/`gate_input_usability`/`runtime_resource_guard` 仍来自只读旧 frozen root（非 PAGE hash 源）。
- 回执：`receipts/page-import-only.json`（`sha256=255655…`）。

不是“运行时字符串替换”：`PAGE-IDENTITY.json`、`deadline.js`、`recovery_readonly.js`、`recovery_cancel.js`、`planned_navigation_click.py`、`untimed_image.py`、`later_capture.py`、`launch_prepare.py` 全部静态绑定新 canonical hash；`review_snapshot_cli.py` 从 `PAGE-IDENTITY.json` 读取新 hash；`postkey_observation.py`/`postkey_flow.py` 继承新值。旧 hash 在 runtime source 中的命中为 0（`binding-inventory`）。

### 3.2 同 fake DOM 装载最终 PAGE + deadline + recovery

测试文件：`tests/page_runtime_test.cjs`；回执：`receipts/page-runtime-tests.json`（4/4）。

- 最终 served script 来自 `receipts/final-served-script.txt`（import-only 从真实 `trial_web_r24_review_snapshot.PAGE` 提取），canonical 来自 `receipts/final-canonical-script.txt`；canonical `f9a428…`，完整 PAGE `551cbd…`。
- 最终 `operator-helpers/deadline.js`（`SCRIPT_SHA=f9a428…`）在同一个 fake DOM 执行 `arm`，产生 60000ms alarm。
- 最终 `operator-helpers/recovery_readonly.js`、`operator-helpers/recovery_cancel.js` 在同一 fake DOM 执行；PAGE 的 `fx3KeyAttemptRecoveryEligibility` **没有被 stub**（r44 测试的缺口已修复）。

用例：

1. 最终 PAGE + 最终 deadline.js：点击帧 `gen58/seq1886/e014…`，PAGE preflight 读到 `gen59/seq1892/2914…`，PAGE 自身拒绝：`not_posted / preflight_identity_or_lifecycle_changed / mutation_called=false`，没有 `/api/key`。随后 `recovery_readonly.js` 用真实最终 PAGE 的 eligibility 返回 `qualified=true`，`alarm_budget_ms=60000`，`mode=armed`。
2. 最终 `recovery_cancel.js` 使用**合成** `qualified_recovery_observation` review 执行取消，返回 `cancelled_unqueued_alarm_only`、`cancel_invoked=true`、`no_guest_key=true`、`no_confirm_visual=true`。回执明确 `synthetic_review=true`、`actual_visual_review=false`、`human_visual_chain_not_performed=true`；这不是视觉恢复通过。
3. 错 nonce、已 accepted、到期（`performance>=due`）仍拒绝：分别 `attributed_unqueued_binding`、`attributed_unqueued_binding`、`not_eligible_armed`。
4. 旧 20s alarm 被最终 host helper 拒绝：`alarm_identity`（最终 PAGE 绑定 60000；20s 旧预算不匹配）。

> 人工链保持独立：观察 → 操作者实际看图 → 取消 → 取消后图实际复核 → 新 nonce。离线测试只验证证据/状态机，不替代真实视觉判断，也不自动重发/选图/合并 pin 或 confirm。

### 3.3 PAGE 绑定变化

| 文件 | 变更 |
|---|---|
| `trial_web_v22_navigation_review.py` | 新增本地 base PAGE（旧 frozen base + 两行 20000→60000）；旧 frozen 文件未改 |
| `trial_web_r24_review_snapshot.py` | `BASE=HERE`，加载本地 base；server 行为、`SNAPSHOT_TTL=20.0`、review/confirm 代码不变 |
| `PAGE-IDENTITY.json` | canonical `f9a428…`；完整 PAGE `551cbd…` |
| `operator-helpers/deadline.js` | `SCRIPT_SHA=f9a428…` |
| `operator-helpers/recovery_readonly.js` | PAGE fingerprint `f9a428…` |
| `operator-helpers/recovery_cancel.js` | `PAGE_SHA=f9a428…` |
| `operator-helpers/planned_navigation_click.py` | `PAGE_SHA=f9a428…` |
| `runtime-wrapper/untimed_image.py` | inline PAGE fingerprint `f9a428…` |
| `runtime-wrapper/later_capture.py` | inline PAGE fingerprint `f9a428…` |
| `runtime-wrapper/launch_prepare.py` | prestart assert `f9a428…` |
| `review_snapshot_cli.py` | 从 `PAGE-IDENTITY.json` 读新值（文件本身未改） |
| `postkey_observation.py`/`postkey_flow.py` | 继承 `review_snapshot_cli.PAGE_SHA` 新值（文件本身未改） |

---

## 4. 全链绑定与 import 继承

`common.py` 的实际路径：

- `SOURCE` = 本候选 `runtime-wrapper`；
- `FROZEN` = 只读旧 `v25-r21-recovery-integration`；
- `OPS` = 旧 frozen `operator-helpers`；
- `CANDIDATE_OPS` = 本候选 `operator-helpers`；
- `helper()` 的候选路由为 `planned_navigation_click.py`、`review_snapshot_cli.py`、`deadline_cli.py`、`recovery_tools.py`、`postkey_observation.py`；这些实际执行时使用候选副本。
- 实际 PAGE hash 校验全部在候选副本：`deadline.js`、`recovery_cancel.js`、`recovery_readonly.js`、`planned_navigation_click.py`、`untimed_image.py`、`later_capture.py`、`launch_prepare.py`；`review_snapshot_cli.py`/`postkey_observation.py`/`postkey_flow.py` 读/继承候选 `PAGE-IDENTITY`。旧 frozen root 只用于不校验 PAGE hash 的模块（如 `qmp_line_transport`/`gate_input_usability`/`runtime_resource_guard`）。
- `run_trial_r24_review_snapshot.py` 的 sys.path 仍含旧 frozen root 供上述非页模块；`trial_web_r24_review_snapshot.py` 的 base 走显式本地路径，observer-source copy 的 `trial_web_v22_navigation_review.py` 也从本候选 `HERE` 取得。
- `r35_package_selection.py`：`APPROVED_HOST=本候选`、`PROFILE=r47-runtime-integration-60s`、`LABEL=v47runtime-n64-r47`；`PACKAGE` 仍 r42 package，candidate/CPIO pin 不变。
- `return-tools/return_adapter.py`：`FROZEN=parents[1]` 本候选；`OPERATE_SHA=e0aca…`（operate.py 未改，sha 匹配）；`CORE_FREEZE_SHA` 更新为新 CORE `c87cb7…`；`main` 仍用新 CORE/SOURCE，不忽略旧 hash 检查。
- `prepare_run.py` 的 `config.candidate_source_root`、`runner_profile`、`frozen_root` 与 44 项 `LOCAL-SOURCE-FREEZE` 自绑定；`prepare-only` 回执 `receipts/prepare-only.json` 证明没有启动 runner/browser/QEMU。
- `preflight.py` 在 fake run 上通过（raw `receipts/raw/preflight.stdout.txt`），包含 package pin、CORE 39、旧 frozen 输入、parser `--help`、import-only 检查；没有 browser/QEMU。

### 4.1 SOURCE/CORE 成员（真实依赖，不硬 43/38）

- **CORE = 39**：r44 CORE38 + `trial_web_v22_navigation_review.py`。`CORE-SOURCE-FREEZE.json` `sha256=c87cb75380013efd940a653da015d2116b8caf159db4a818ac377546b9349dc2`。
- **SOURCE = 44**：CORE39 + `return-tools/` 4 个文件 + `CORE-SOURCE-FREEZE.json`。`SOURCE-FREEZE.json` `sha256=981664fb7c563162e84ac0feaa82a0ebf0ae8bc361df74d11519e29499831e76`。
- 旧 frozen base `1459d5b7…` 只读保留；新 base `8a40a4a67bdbe4ce8712d1a4ef78c893ffc2ea625fb6f0966d1a4e4136ba1be7`。完整成员和逐文件 hash 见两个 freeze JSON。

### 4.2 全局 20 的语义分类

`binding-inventory` 对 runtime source 逐行扫描：

- 旧 whole-step/recovery 20s 预算已不在运行器：runtime source 中 `20000`/`20_000` 的“旧预算”命中为 **0**。
- 唯一允许的 `20000` 是 `run_trial_r24_review_snapshot.py` 的 serial raw literal `raw=02000007000000`，不是时间预算；回执 `allowed_20_semantics` 记录。
- 保留：native input deadline 12s；snapshot TTL 20.0；API16 restore timeout 20s；startup 180s；total 8min；8 accepted/10 attempts/2 recoveries/每步 1 恢复。`NAVIGATION-PLAN.runtime_budget` 精确匹配。

---

## 5. 测试回执

| 测试 | 结果 | 回执 |
|---|---|---|
| full suite | **9/9 PASS**，input_unchanged=true | `receipts/test-run.json` `sha256=912007ec0c085f56caf945c73407ec6fb5862e6842213930e6b8050ffac81922` |
| cleanup closed loop | 7/7 PASS；actual `_cleanup_once` + certify/seal/revalidate | `receipts/cleanup-closed-loop-tests.json` `sha256=fc28f8d26c0f4e633dc5358c5c8441b3892d6b57976b31f56d44134b9a672543` |
| PAGE runtime fake DOM | 4/4 PASS；final PAGE + deadline + recovery helpers；synthetic review | `receipts/page-runtime-tests.json` `sha256=5e4484d2009872004a1ef6c67bbd3a2cd631991c8632e8f9bd2c727aff8fc5e2` |
| runner import-only | PASS；local base、canonical f9a428、full 551cbd、blocked=[] | `receipts/page-import-only.json` `sha256=2556559b1a20a8480e529a7cf9bfbcafbde0a36358ad6bc5ba43dadbc4f8e4a0` |
| binding inventory | PASS；SOURCE 44/CORE 39；old PAGE hits 0；old 20000 hits 0（只留 serial literal） | `receipts/binding-inventory.json` `sha256=e14220089b00376368b5a5a3fb675a2e8bfa49176f9da85bd0fecb655036b1f0` |
| package pin | PASS；r42 candidate/CPIO/DTB 不变；未复制/写 | `receipts/package-pin.json` `sha256=696a54fe4444f104c69089b675a551f7a7501d0edab9cadff0a3e2de44bb9510` |
| prepare-only | PASS；44 项 local freeze；无 runtime.json | `receipts/prepare-only.json` `sha256=acfaae15c778b4f99628e8b8ac9046c821aac8866bfb11012ff9cce3d74f4515` |
| input seal before | 51 项 | `receipts/input-seal-before.json` `sha256=b32f9371e04e89d26c61dd791b7f342e1cf18af1d56df84d0ea5aa06971d6ede` |
| input seal after | 51 项，unchanged | `receipts/input-seal-after.json` `sha256=ea1c31184d8da441cda5068543f2148084ab5cc7e62df6adae850c60cb2fa9ca` |
| input compare | changed=[]，r46 32/32，r45 554/150 | `receipts/input-seal-compare.json` `sha256=4164521930dc82b7748ec65f9e743265701b52fedbab768ea8a02da1bbec2edd` |

`preflight`/`prepare-only` 的 raw stdout/stderr 在 `receipts/raw/`。所有测试不接触真实 browser、PID、QMP、VM、guest；cleanup 的 native/resource 是注入假依赖。

---

## 6. r46 报告 first/second 纠正

r46 协调器终审 source invocation timestamps：

- **第一次**：`4302ff41-653d-4ae5-9b79-f713120ab9e2` @ `2026-11-05T11:28:12.079540Z`。
- **第二次**：`0687a34f-8dcd-4d62-b4a0-b1c0037830b1` @ `2026-11-05T11:28:20.641615Z`。

r46 REPORT 将两者写反。本 r47 REPORT 按该终审纠正；r46 原文件未被重写，r45 failed/cleanup unknown 结论不变。该笔误不影响 armed 白名单/deadline-dispose 矛盾的诊断。

---

## 7. 明确 unknown / 未证实

- **r45 仍 failed、cleanup 仍 unknown**；本候选没有把 r45 任何 result/CLEANUP/CLEANUP-COMPLETED 改成 completed；原始 unknown 保留。
- **没有真实 VM/browser/server/QMP/guest/menu/cleanup/recovery 运行**；所有“通过”都是离线 import-only/fake-DOM/注入依赖测试。真实菜单、真实 End、真实 browser close、native 回收、视觉恢复均未验证。
- **页面 candidate 的 recovery 资格通过是状态机/证据通过，不是完整视觉恢复通过**；`recovery_cancel` 使用合成 review，人工观察→实际看图→取消→复核→新 nonce 链未执行。
- **新 profile 未授权**：`enabled_for_real_run=false`；r45 唯一一次运行已耗用，无新 VM 授权；`FUTURE-SINGLE-TEST-COMMAND.md` 只是草案，当前不得运行。
- **r47 完整 PAGE 551cbd / canonical f9a428 是通过真实 import-only 计算**；`receipts/page-runtime-tests.json` 的 `served_script_sha256=a90a82…` 是 token 替换后的 served script hash，不是 canonical；canonical/full 已分开记录。
- **cleanup 的 native/resource 是 mock**，不是新的 runtime 证据；真实清理仍需未来授权运行。
- **preflight** 使用旧 frozen 只读输入与 r25/r24/r42 pin；它证明绑定/导入/包一致，不证明 FX6 开机/菜单/提速。
- **不是被拦截 FX6 实现的替代或重试**；未改 FX6 源。

---

## 8. 交付清单

```
r47-runtime-integration-candidate/
  REPORT.md
  FUTURE-SINGLE-TEST-COMMAND.md     # 草案；当前不得运行
  CANDIDATE-DELTA.json              # old/new hash、profile、页面、测试、r46 correction
  CANDIDATE-POLICY.json             # offline/enabled_for_real_run=false、边界、保留预算
  DIFF-r47.patch                    # 全部变更合并
  DIFF-cleanup.patch                # cleanup.py + cleanup_evidence.py
  DIFF-page.patch                   # base PAGE + trial_web BASE
  DIFF-bindings.patch               # profile/PAGE-IDENTITY/helper/return-adapter
  DIFF-manifests.patch              # SOURCE/CORE
  SOURCE-FREEZE.json                # 44 项，相对路径+hash
  CORE-SOURCE-FREEZE.json           # 39 项
  PAGE-IDENTITY.json                # f9a428 / 551cbd
  trial_web_v22_navigation_review.py
  trial_web_r24_review_snapshot.py
  run_trial_r24_review_snapshot.py
  r35_package_selection.py
  prepare_run.py
  operator-helpers/*                # 11 文件，PAGE hash 已本地绑定
  runtime-wrapper/*                  # cleanup/evidence 及其他运行器
  return-tools/*                     # return_adapter 新 CORE 绑定
  tests/                             # import_only, cleanup_closed_loop, page_runtime, binding_inventory,
                                     # package_pin, prepare_only, input_seal, run_all
  receipts/                          # 9 suite/每次测试回执/final canonical+served script/raw stdout/stderr
  SHA256SUMS                        # 本目录文件清单（不含自身）
```

关键 hash（`SHA256SUMS` 生成前）：

- `SOURCE-FREEZE.json` `981664fb7c563162e84ac0feaa82a0ebf0ae8bc361df74d11519e29499831e76`
- `CORE-SOURCE-FREEZE.json` `c87cb75380013efd940a653da015d2116b8caf159db4a818ac377546b9349dc2`
- `PAGE-IDENTITY.json` canonical `f9a428…`，full `551cbd…`；base PAGE `8a40a4…`（旧 `1459d5…`）
- `runtime-wrapper/cleanup.py` `ed3edbb402529acfa84a6fb18ce96720b48cb7b7c1edc1cbc622da9c92b7a1cb`
- `runtime-wrapper/cleanup_evidence.py` `b9c511e2c4ecf1ff24a0446a6a462dce86776b58ac983c73db12f811261a00dc`
- `trial_web_r24_review_snapshot.py` `201d14b0daaede2ec582dc9e3f63e021845daa0db2d205f5896077a7736b618c`
- `r35_package_selection.py` `2b14b69b218ace83c6f83bafe0008e56ab7f514f9624a9e8866004e82bd955b0`
- `return-tools/return_adapter.py` `6a1eb32fcde5fa2b83904eae3c87b88c0d72a03ab1998f6d8360eec5a5b39f2e`
- 测试回执 hash 见第 5 节。

运行方式（离线）：

```sh
cd .../r47-runtime-integration-candidate
python3 tests/run_all.py
```

该命令会重新生成 receipts 并校验输入前后 hash；不接触真实 browser/VM。**它不授权也不启动 future run。**

---

## 9. 建议的下一步（协调器决定）

1. 验收 r47 离线集成：重点看 `DIFF-r47.patch`、`CANDIDATE-DELTA.json`、`tests/cleanup_closed_loop_test.py`（实际 `_cleanup_once` 闭环）、`tests/page_runtime_test.cjs`（最终 PAGE+deadline+recovery）。
2. r45 保持 failed/cleanup unknown；r46 first/second 纠正已记录，不改旧文件。
3. 若未来要做真实单次测试：先重新授权，按 `FUTURE-SINGLE-TEST-COMMAND.md` 的实际链执行：`prepare_run.py` → `preflight.py` → `launch_prepare.py`（仅网页/runner/browser 准备，输出 `web_prepared_guest_not_started`，不启动 QEMU/guest、不点 Start）→ `start_and_wait.py`（唯一 Start + 最多 180s 首帧等待 + `initial-standby/current.png`）→ 操作者实际看 initial-standby 图 → `operate.py standby_review` → 后续 click/pin/confirm 或 recovery capture/cancel/review 的人工看图链 → `cleanup.py` → 仅当 cleanup completed 且 `CLEANUP-COMPLETED.json` 存在/可复核时才 `audit_after.py`。若 cleanup unknown，保留失败与 unknown 并上报，不另启 VM、不自动重试、不延长。
4. 若不授权新 VM：保持离线候选，不改运行政策、不部署、不声称菜单/FX6 开机/提速通过。
5. 本次仅文档修正：更新 `FUTURE-SINGLE-TEST-COMMAND.md` 第 3/4 节与本节 Start 链；源码、测试、政策、SOURCE/CORE 未改（`SOURCE-FREEZE.json=981664…`、`CORE-SOURCE-FREEZE.json=c87cb7…` 仍不变）；`SHA256SUMS` 因文档变更重生成，其新 self-hash 由 worker_done 报告。

---

## 10. 一句话状态

- **r47 离线集成完成**：真实 import-only 服务本地 base PAGE（canonical f9a428/full 551cbd）；清理 actual `_cleanup_once`+certify+seal+revalidate 闭环 7/7；最终 PAGE+deadline+recovery fake DOM 4/4；全链 44/39 自绑定；9/9 suite；输入 51 项前后不变。
- **r45 仍 failed/cleanup unknown**；**无新 VM 授权、未部署、未真实运行**；`FUTURE-SINGLE-TEST-COMMAND.md` 只是草案。
- **这是宿主内部一致性修复，不是菜单/FX6 开机/提速证明。**
