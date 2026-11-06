# FX3 r48｜r47候选单次真实运行报告（失败：第1步）

- Task：`task_f9c618eedbad`
- Dispatch：`ctx_df9d59d4ecda`
- Session：`fx3-deadline-r48f9c618`
- 授权：`.../passive-timing-delivery/r48-user-approval.json`
  - SHA256 `9d9bcc1570c07c9129faed7dd4fb7d438c6815f7b33233272b946de0e6a1226b`
  - 用户文本：`批准60秒候选并进行一次测试（推荐）`；`批准一次 r47 测试（推荐）`
  - 一次 Start；未改 candidate policy/REPORT 来伪造授权。
- 结论：**failed**。唯一 Start 发生；首帧/standby 成功；第 1 步两次点击的 PAGE 都返回 `not_posted`，第一次已合法恢复，第二次因“每步最多 1 次 recovery”被 `operate.py:59` 拒绝并自动原 End/cleanup；没有 accepted key、没有 pin/confirm、没有第 2 步。**cleanup 为 completed，audit_after 为 collected_only；八步菜单/FX6/提速均未证实。**

## 1. 候选与固定输入（运行前核）

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；候选 `SHA256SUMS=3fecb3631c4126c4b7468cc8a849a5f7932a353d8dc34c10ba27c9370d61533d`（93/93 OK）。
- `SOURCE-FREEZE.json=981664fb7c563162e84ac0feaa82a0ebf0ae8bc361df74d11519e29499831e76`（44 项逐项 OK）。
- `CORE-SOURCE-FREEZE.json=c87cb75380013efd940a653da015d2116b8caf159db4a818ac377546b9349dc2`（39 项逐项 OK）。
- profile `r47-runtime-integration-60s`，label `v47runtime-n64-r47`；PAGE canonical `f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf`，full `551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b`。
- r42 package candidate `857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806`；CPIO `59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63`；未复制/重建。
- QEMU `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`；kernel `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`；DTB `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`；4×cortex-a35/5120MiB/MTTCG/noicount，initrd 地址 `0x440000000`；实际 argv 与 `command.json` 见第 4 节。
- 历史图像工具检查（Start 前）：实际查看 r45 历史 fixed step7 PNG `e0140ea1…`，确认 `read_image` 可用；该历史图未作为本轮画面。记录：`HISTORICAL-IMAGE-TOOL-CHECK.json`。

## 2. 创建与准备（未启动 guest）

- 运行目录：本目录（`CAND/run-inputs/f9c618eedbad`），新建，未覆盖任何旧 run。
- `prepare_run.py`：`status=prepared_only_no_process_started`；config 的 task/dispatch/session/profile/source root/frozen root 正确；`LOCAL-SOURCE-FREEZE` 44 项。`PREPARE-STDOUT.txt`。
- `preflight.py`：`{"passed": true}`；逐项包/CPIO/DTE/CORE/SOURCE/旧 frozen/import-only/CLI parser 检查通过；无 browser/QEMU。`PREFLIGHT-STDOUT.txt`、`PREFLIGHT-RESULT.json`。
- 启动前锁/进程检查：无 qemu/runner，两个锁 free。`PRE-RUN-RESOURCE-CHECK.json`。
- `launch_prepare.py`：实际输出 `status=web_prepared_guest_not_started`，URL `http://127.0.0.1:50102/`，native run `.../runs/v47runtime-n64-r47-f1be5a01`；页面 `awaiting_launch`，`runtime.json.launch_id=null`；未启动 QEMU/guest。`PRESTART-READY.json` UTC `2026-11-05T15:38:03.667727+00:00`。`LAUNCH-PREPARE-STDOUT.txt`。
- `start_and_wait.py`：唯一 Start；创建 `Start-once`，点击 `#start` 一次；`FIRST-FRAME-CLOCK` start `15:38:07.643264Z`，`FIRST-FRAME-PASS` `15:38:53.299233Z`（limit 180s），未超时；`initial-standby/current.png` SHA256 `4854157cc2d0554ecc19a20c0eb6aca7d4b99571c1cf9b5a81ad5fac06696fb8`；`runtime.json.launch_id=27b2237c-27c6-49e0-ab28-a8cb2679c398`。`START-AND-WAIT-STDOUT.txt`。
- 实际查看 initial standby：1280×1200 PNG，画面为 FX3 相机待机 UI、`NO CARD`，页面提示按 MENU 打开菜单。独立 `standby_review` target 记录在 `step-00-prerequisite.json`；未把历史图当本轮。

## 3. 第 1 步：两次 not_posted，恢复被每步上限终止

目标：`完整Setup > Area/Date，橙色Area/Date/Time Setting`，key 427（MENU）。

### 3.1 第一次 attempt（attempt 1）

- `tool-return-click-01` 通过 `return-tools/return_adapter.py` 调用，child rc=0；adapter status `qualified_recovery_observation`、`step=1`、`attempt=1`。
- `step-01-attempt-01/click-receipt.json`：`status=click_invoked`；`step-01-attempt-01/outcome.json`：
  - `outcome=not_posted`、`reason=preflight_identity_or_lifecycle_changed`、`mutation_called=false`；
  - frame `gen=19`、`seq=120`、`PNG_sha256=e0140ea1…`；
  - nonce `5e23d534-a3dd-4645-9e02-6f8d0a1c84b0`；attempt `79e01010-68a7-4deb-9a07-176b6937343f`。
- 实际查看 recovery 前图 `step-01-attempt-01/recovery-review/observation.png`（SHA256 `7cf4783282db9dbd350f90cb787eda0da6d03ee76a308e8a1d0823c9beb4e13f`）：相机待机 UI、NO CARD，菜单未打开。
- 实际查看后独立 `recovery_cancel`：`cancelled_unqueued_alarm_only`，nonce 匹配，取消 elapsed 6769.1ms（alarm events 记录），未发 guest key。`tool-return-recovery-cancel-01`。
- 实际查看取消后图 `step-01-attempt-01/recovery-cancel/observation/observation.png`（SHA256 `4e9c654e5772c38e0e0e4b854a27fa75bdf881b349d0602dc4425dde9d372abc`）：仍为相机待机 UI、NO CARD，菜单未打开。
- 独立 `recovery_review`：`explicit_recovery_image_reviewed`。ledger 记录 1 次 recovery（step 1）。

### 3.2 第二次 attempt（attempt 2）

- 使用新 nonce `59ac034b-3fb2-4bd8-bebb-dab642b13196`，新 attempt `465af599-4c73-4f97-ba8a-55ccd3e90565`；`step-01-attempt-02/click-receipt.json` `status=click_invoked`。
- `step-01-attempt-02/outcome.json`：`outcome=not_posted`、`reason=preflight_identity_or_lifecycle_changed`、`mutation_called=false`；frame `gen=43`、`seq=231`、`PNG_sha256=e0140ea1…`；`created_monotonic_ms=76870.1`、`updated_monotonic_ms=76871.5`。
- `operate.py:59` 断言 `len(recoveries)<2 and not any(step)` 失败，因为第 1 步已有 1 次 recovery，政策每步最多 1 次；`FAILURE.json`：
  - `action=click`、`error=AssertionError()`、UTC `2026-11-05T15:39:19.948380+00:00`；
  - child stderr 明确 `operate.py line 59`。
- 按协议立即原 End/cleanup；**没有第二次 recovery、没有 repin/重试、没有新 VM**。`tool-return-click-01b` status `return_failed`、`End_required=true`；cleanup dispatch 已生成。
- 结果：step 1 accepted=0、fixed snapshot=0、confirm=0；`reached_step=0`、`failed_step=1`。`ledger.json`：2 attempts、1 recovery。

## 4. 原 End/cleanup、audit 与资源

- 自动 `failcleanup` 产生的 cleanup 调用：`cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b`；`result.json`：
  - `status=completed`、`errors=[]`、`runner_alive=false`、`port_closed=true`；
  - `alarm_disposition=valid_armed_do_not_cancel_or_dispose`，`dispose_invoked=false`，完整 marker/nonce/due/digest；
  - End `End_invoked=true`；browser before pid 44256 / after `active=false,pid=null`；
  - resources：runner 44250/qemu 44381 absent、双锁 free、port 50102 closed、`resources_closed=true`；
  - CALL/RECEIPT：`CLEANUP-COMPLETED.json`、call receipt SHA `ccb3b6dbae7224a6f9b92ee4cb4ecae9f40763a3abc8c86c09aa43a0942d56b1`。
- `audit_after.py` 通过严格 `CLEANUP-COMPLETED` 读取并 revalidate：`status=collected_only`、`CLEANUP-AUDIT.json`；它明确不做 menu acceptance。`AUDIT-AFTER-STDOUT.txt`。
- native run `.../runs/v47runtime-n64-r47-f1be5a01`：
  - `receipt.json`：`stop_cause=end_trial_button`、`qemu_exit=0`、`process_reaped=true`、`PID_absent=true`、`API16_restored=true`、`quit_sent=true`、`health_pass/lifecycle_pass/diagnostic_readback_pass/protocol_pass/render_pass=true`、`menu_verified=false`、`key_steps=0`、duration `75.0913467920036s`、max `480`；
  - `trial-session.json`：observer 44250、qemu 44381、url `http://127.0.0.1:50102`、host_launch_uuid `b3e113bf-4249-4fba-8bc0-4a9d4d6ca4fb`；
  - `trial-web-final-receipt.json`：`acknowledged=true`、`browser_ack`、max wait 30；
  - `resource-guard-receipt.json`：`process_reaped=true`、`locks_released_after_reap=true`。
- 实际运行 argv：
  - `ACTUAL-RUNNING-ARGV.json` 的 `ps` 与 native `command.json` args 双证据均显示 QEMU sha `bf4d4648…`、`-cpu cortex-a35`、`-smp 4`、`-m 5120`、`-accel tcg,thread=multi`、无 `-icount`、kernel `da4a66…`、CPIO `59c585…`、DTB `5aa2be…`、地址 `0x440000000`；native `command.json` candidate sha `857c2b…`。
- 独立 post-run 资源：
  - 我们的 runner 44250/qemu 44381 absent；port 50102 `ECONNREFUSED`；browser session inactive/pid null；API16/quit/reap/ACK 通过。`POST-RUN-RESOURCE-CHECK.json`。
  - **注意**：我们的 cleanup 完成后，观察到另一个 FX6 donor QEMU `45763`（07:40:07 启动）占用两个全局锁；它不是本 run 的进程，未触碰、未 kill、未用于本 run。我们的 cleanup proof 在自身探测点记录 locks free；当前全局锁被外部进程持有是之后的独立事实。
- `INPUTS-BEFORE`/`INPUTS-AFTER` 的 groups/counts 相等；候选/源码/固定输入未变。`INPUT-HASH-COMPARE.json`；文件 hashes 见 RESULT。

## 5. 证据清单（本目录）

- `RESULT.json`：失败结果、步骤明细、固定输入、cleanup/native/资源/图像 hash。
- `PREPARE-STDOUT.txt`、`PREFLIGHT-STDOUT.txt`、`PREFLIGHT-RESULT.json`。
- `PRE-RUN-RESOURCE-CHECK.json`、`LAUNCH-PREPARE-STDOUT.txt`、`START-AND-WAIT-STDOUT.txt`、`PRESTART-READY.json`、`runtime.json`、`Start-once`。
- `FIRST-FRAME-CLOCK.json`、`FIRST-FRAME-PASS.json`、`initial-standby/current.png`、`step-00-prerequisite.json`、`STANDBY-REVIEW-STDOUT.json`。
- `step-01-attempt-01/`、`step-01-attempt-02/`、`tool-return-*` 原始 child streams/summary/returned PNG。
- `FAILURE.json`、`cleanup-calls/dc3a…/`（含 native 副本、HAR、PNG、proof/manifest）、`CLEANUP.json`、`CLEANUP-COMPLETED.json`、`CLEANUP-AUDIT.json`。
- `LEDGER`、`INPUTS-BEFORE/AFTER`、`INPUT-HASH-COMPARE.json`、`POST-RUN-RESOURCE-CHECK.json`。
- `NATIVE-RUN` 路径与 key hashes 见 RESULT；本目录没有复制整个 native run。

## 6. Unknown / 限制

- 第 1 步未通过；没有 8 步菜单、没有 8 accepted、没有 pin/confirm；`menu_verified=false`。
- 第 1 步第二次 not_posted 后因每步 1 recovery 政策终止；没有第二次 VM、没有新 Start、没有自动重试。
- cleanup 为 completed、audit_after 为 collected_only；这验证清理/身份/资源，不证明菜单或 FX6 开机。
- 外部分离 FX6 donor QEMU 在本 run cleanup 后占用全局锁；本 run 未触碰它；不把它算作本 run 资源，也不据此重试。
- r45 仍 `failed`、cleanup `unknown`；未修改旧 r44/r45/r46 输入。
- 离线/真实图像判断：initial standby 和 recovery 前后图已实际查看；没有在未通过步骤上伪造 pin/confirm；未使用 OCR/hash 代替看固定图。

## 7. 结束状态

- `Start_count=1`；`explicit_attempts=2`；`accepted_keys=0`；`recoveries=1`；`fixed_snapshots=0`；`confirms=0`；`reached_step=0`；`failed_step=1`。
- cleanup `completed`；audit `collected_only`；native qemu exit/reap/API16/quit/ACK 证据齐全；本 run 自身 runner/QEMU/端口/browser 已回收。
- **整体 outcome=failed**；无第二次 VM。r45 历史不动。
