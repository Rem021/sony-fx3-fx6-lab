# r45｜固定 FX3 平台真实菜单八步＋60 秒整步审阅

**结论：failed。唯一一次 VM/Start 已执行；第 1–7 步完成固定快照与独立确认，第 8 步 MENU 重开在 click 后返回 `not_posted`，随后恢复链拒绝、清理协议未完成。没有第二次 Start，没有部署，也没有启动 FX6、相机、USB、SD 或刷写。60 秒整步期限本身没有在第 8 步到期。**

任务身份：`task_r45vm0323` / `ctx_r45vm0323` / `fx3-deadline-r45vm0323`。用户在本会话明确批准“60 秒政策 + 一次 VM 测量”；协调器被通知（`msg_9a7cbe257113`），但当时未绑定 Run、未正式派发，因此本轮以本地独占 task/dispatch 记录执行，批准原文保存在 `APPROVAL.json`。这是一处需要协调器复核的流程偏差。

## 1. 固定平台与输入

| 项目 | 值 |
|---|---|
| 卷 | `/Volumes/KAFU2T`，UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`（已核） |
| 候选 | `r44-review-budget-candidate`；profile `r44-review-budget-60s`，label `v44review-n64-r44` |
| SOURCE43 / CORE38 | `3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c` / `b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1` |
| r42 封存包 | candidate `857c2b7a…11806`，CPIO `59c5850a…3c63`，453213884 B |
| GPE slot | body 129600 B `19ca7deaf570eeb68fda0036bb75dec740ab30f404f9f91bd208fd3d53c06a39` + 147384 B 零尾；padded-slot `17abe2cab22da7ede9e3af337e9958e4f1e592f75670cf038928110bb4b8bcdd` |
| QEMU / kernel / DTB | `bf4d4648…c70d` / `da4a66fa…4820c` / `5aa2beac…7855b` |
| 运行 | `runs/v44review-n64-r44-6583e25e`，Start 1 次，duration 211.855 s，max 480 s |

启动前 `EXCLUSIVE-BEFORE-SERVER.json` 记录冲突进程为空、双锁 free；`launch_prepare` 与 `start_and_wait` 都通过。实际 runner argv 与 `PLANNED-ARGV.json` 的平台参数为 4×cortex-a35、5120 MiB、`tcg,thread=multi`、无 icount。

## 2. 逐步结果

| 步 | 键 | 目标 | 原生结果 | 固定快照 | 独立确认 | 结果 |
|---:|---:|---|---|---|---|---|
| 1 | MENU | Setup > Area/Date，橙色 Area/Date/Time Setting | accepted | `60e9accc…e1292` | 是 | 通过 |
| 2 | UP | Language English | accepted | `c5452b85…3ce2` | 是 | 通过 |
| 3 | C4 | Language 帮助页 | accepted | `74a59929…c808` | 是 | 通过 |
| 4 | MENU | 返回 Language | accepted | `c5452b85…3ce2` | 是 | 通过 |
| 5 | OK | English 语言列表，不改值 | accepted | `5aa0cd7e…17e7` | 是 | 通过 |
| 6 | MENU | 取消语言列表 | accepted | `c5452b85…3ce2` | 是 | 通过 |
| 7 | MENU | 关闭到完整待机 | accepted | `e0140ea1…2eb4` | 是 | 通过 |
| 8 | MENU | 重开完整菜单 | **not_posted** | 无 | 无 | **失败** |

第 8 步细节：

- arm 于 performance_ms `243173.9`，due_ms `303173.9`（60 秒）；click 时 `243258.6`，仍远早于 due。
- `planned_navigation_click.js` 的 26 项 preflight checks 全部为 true，`click_called:true`，`identity_trusted:true`。
- 随后原 PAGE 归因 `outcome=not_posted`、`mutation_called=false`、`reason=preflight_identity_or_lifecycle_changed`；没有 guest key 被入队，也没有固定图。
- `operate.py` 立即进入失败路径：写 `FAILURE.json`、`POSTKEY-TERMINAL.json`，并调用原 cleanup；没有重试、没有第二次点击、没有 recovery 重发。
- 恢复捕获在 `performance_ms=243342.4` 被 `recovery_readonly` 拒绝为 `not_eligible_armed`；当时 alarm 仍 armed，due 仍在未来。因此这不是 60 秒期限到期，而是恢复资格/页面生命周期门拒绝。具体内部原因未进一步推断。

## 3. 清理与资源

**清理协议未通过：`CLEANUP-COMPLETED.json` 不存在，兼容索引 `latest_status=unknown`。**

- 首次 cleanup `4302ff41-653d-4ae5-9b79-f713120ab9e2`：`status=unknown`，`alarm_disposition=valid_armed_do_not_cancel_or_dispose`，`runner_alive=false`，`port_closed=true`，错误 `cleanup_body_incomplete`。
- 第二次显式 cleanup `0687a34f-8dcd-4d62-b4a0-b1c0037830b1`：页面已不可用，End/status 读取失败，`status=unknown`。
- 独立资源审计 `RESOURCE-AUDIT.json`：runner PID 53378、QEMU PID 53782 均 absent；无 runner/QEMU 进程；双锁 free；端口 58245 closed；browser session inactive。
- runner 自身回执 `receipt.json`：`stop_cause=end_trial_button`，`qemu_exit=0`，`process_reaped=true`，`PID_absent=true`，`API16_restored=true`（1.800 s，原 20 s 预算内），`quit_sent=true`，`health/lifecycle/diagnostic/protocol/render` 均 true，`menu_verified=false`，`key_steps=7`。
- `trial-web-final-receipt.json`：`acknowledged=true`，`wait_seconds=0.3799`。

因此资源层面已无残留、QEMU 正常退出且 API16 已恢复；但 cleanup 证据索引未完成，不能把清理标为通过。

## 4. 离线计时

边界严格取本轮：

- startup 首个保留 `evaluation_complete=true / qualified=true`：offset `3570591`。
- 交互截止：`startup-observation.json` 的 `phases.first_kinds` 首个 `cleanup.serial_offset=19706189`；没有改用较晚的 `serial_bytes_before_cleanup=19711955`。
- serial 总字节 `19770977`，cleanup tail `64788`，carry 42 B。
- 解析器：封存 `r41-command-entry-timing-candidate/parse_command_timing.py`；`--run-id v44review-n64-r44-6583e25e`；三个输出均在 native run 目录。

| 阶段 | command 记录 / unknown | 已知 duration 中位 / p95 / 最大 | 已知 gap 中位 / p95 / 最大 |
|---|---:|---|---|
| startup [0,3570591) | 100 总 / 91 含 tid；8 malformed + 1 incomplete | 91；15.748 / 27.776 / 49.647 ms | 83；2.941 / 11.550 / 1327.043 ms |
| ready 至首 cleanup [3570591,19706189) | 894 总 / 790 含 tid；104 malformed + 1 end_before | 789；10.957 / 22.280 / 237.021 ms | 685；1.950 / 558.496 / 25957.920 ms |
| precleanup 合计 [0,19706189) | 993 / 112 malformed + 1 end_before | 880；11.273 / 24.172 / 237.021 ms | 768；2.040 / 527.402 / 25957.920 ms |
| 全文件含 cleanup tail | 996 / 112 + 1 | 883 known | 771 known gaps |

计时只解释 guest `CLOCK_MONOTONIC` 内 adapter entry→return marker 与同线程有序 return→entry；不是 CPU 时间、纯 FIFO 空闲或 HTTP 可见延迟。大的 gap 可能包含模型审阅/工具/调度/未观察活动，不能归因于固件绘图或 60 秒政策。完整记录见 `TIMING-SUMMARY.json` 及三个 `COMMAND-TIMING-*.json`。

## 5. 结论与限制

- 60 秒政策在本轮前 7 步可用；第 8 步失败不是 60 秒到期，而是 `not_posted` + 恢复资格拒绝的组合。
- 完整八步未通过，因此整体 **failed**；`8 accepted` 不等于 8 步通过。
- 清理索引 unknown，但资源终态独立核查为空、双锁 free、端口 closed、QEMU exit 0、API16 restored。该区分必须保留。
- 没有第二次 Start、没有部署；没有 FX6 开机、相机/USB/SD、性能改善或零帧根因结论。
- 原始证据保留在 `tool-return-*/`、`step-08-attempt-08/`、`cleanup-calls/`、`cleanup-dispatches/`、`FAILURE.json`、`AUDIT-AFTER-STDERR.txt` 与 native run 目录；`SHA256SUMS`/`NATIVE-SHA256SUMS` 为封存哈希。
