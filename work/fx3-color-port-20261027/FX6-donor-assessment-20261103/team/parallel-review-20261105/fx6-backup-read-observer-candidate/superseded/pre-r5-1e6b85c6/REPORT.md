# FX6 AppFw two-key observer — r4 host-only correction

- Task：`task_3d797ea658d3`
- Dispatch：`ctx_d639ad6a1ef6`
- Status：**HOST_ONLY_R4_CORRECTED; RUNTIME_CLEANUP_BLOCKED; NOT RUN**
- 只改本目录；`superseded/pre-r4-b3cd050d/` 与更早版本保留；固定 FX3 平台、3a08 CPIO、b1fe appFw、其他输入、旧 observer、运行政策未改。
- 无 VM/guest/QMP/browser/server/live-process；无 camera/USB/SD；UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核。
- 仅离线候选；不是 FX6 boot/menu 证据。

## 1. prelaunch 修正

`-S` 的初始 QMP 状态是 `prelaunch, running=false`（本地 r5 receipt line371；QEMU RunState 文档一致）。`HostRunner.start` 现接受 `prelaunch` 或 `paused` 且必须 `running=false`；随后允许一次 QMP `cont` boot，**boot 后**才等当前 serial maps；after-map `stop/query` 必须 `paused`。不再去掉 `-S`，也不把 prelaunch 当 paused 失败。实际 E2E 的 QMP 服务初始必须 `prelaunch` 且 caps 前拒绝命令。

## 2. 真实四stop E2E

`tests/test_e2e_stateful.py` 已替换为 **实际 Observer + 实际 QMP/RSP + Sysregs XML/p** socketpair E2E；fake 仅提供 guest regs/mem/QMP state，不替换 Observer 完成逻辑：

- QMP greeting → qmp_capabilities → query(prelaunch) → cont boot → map → stop/query paused。
- RSP Z1/z1/Hg/Hc/g/m/p/qXfer，真实 target appFw 字节做只读 memory fixture；Sysregs 读取 XML/TPIDR_EL0。
- 4 次真实 stop：214 entry/return、218 entry/return；每次非 final 必须 addressless c 才发下一 stop；最终计数 `continued=4`。
- GDB/QMP 服务端异常、线程残留、ACK/checksum/帧错误都在测试中 assert；normal 必须 clean。

`tests/test_stateful_transport.py` 5/5：实际 QMP 类 greeting/caps/id、缺能力拒绝、无响应 timeout；实际 RSP c 后立即 T05、无响应 bounded。

## 3. deadline/接口

- `Deadline` 分开 `remaining_observation` 与 `remaining_total`；始点在一次 launch preparation 前。
- HostRunner factory 显式传同一 Deadline：QMP constructor/greeting/capabilities、RSP connect/command/poll/XML/p/Z1/z1、map wait、cleanup wait 均用剩余预算；QMP `call` 直接收 deadline，无 TypeError 重试丢 deadline。
- RSP 实际类支持 deadline；`connect` bounded retry；`command/virtual_read/send_continue` clamp；`poll_stop` 不再固定新 1s。socketpair 无响应测试实测 bounded，无后台线程越过任务期。
- fake clock/真实 socketpair 覆盖无 packet、无 map、无 hit、cleanup wait、start failure。

## 4. cleanup/partial

- `self.possibly` 初始化；observer 未 arm 为 0；partial arm 用 observer.possibly；没有凭空断点。
- stop/query 未确认时**不删断点、不调用 inherited**，只对自有 child 做安全停止/退出并 unclean；不能把未知 guest 恢复写成 not-applicable。
- 正常顺序：QMP stop/query paused → z1 possibly → close RSP → inherited（仅完整 clean 且有可取消 callback）→ QMP quit → bounded wait/reap → exit code 记录 → 锁释放；`lock_released` 写回 receipt。
- RSP/QMP 构造失败/部分 launch/observer 异常/quit 失败/wait 超时/release 失败/重复 cleanup 均记录；RSP/QMP fd 有界关闭。launcher parent stdout/stderr fd 在 Popen 后关闭。
- 实际 receipt 落盘到私有 run 的 `receipt.json`，含 command SHA、target/app/serial hash、qemu exit、lock、records；`runtime_evidence` 由 deps 来源决定，不再硬编码 false。

## 5. HOST_STOP_ONLY_OBSERVATION

- `observer/run_stop_only.py` 默认 DISABLED；独立 token + `--new-run-approval` + fresh run root 才允许审阅。
- 不写任何 guest 控制/代码/数据；无 inherited callback；观察完成/期限到后确认 pause、删可确认 Z1、关 RSP、QMP quit→reap→锁释放。
- 输出字段分离：`two_keys_observed`、`host_cleanup_complete`、`guest_restore_status=unknown_not_attempted`、`boot_menu_passed=false`；完整 clean 默认策略仍要求 inherited 合同，stop-only 不替代它，也不叫 Guest End/API16 成功。
- 残余断点/stop 不确认仍只退出自有 QEMU 并标异常，绝不 resume。

## 6. API16

仅结论：旧 `restore_api103_v2` 控制合同在 3a08 上**未建立**；target helper 仍有 `fx3_sync100_shutdown`/`sync100_restore` 与 `FX3_SYNC100_SHUTDOWN original16_verified` 标记，不能仅因无 `F100FILE` 字符串推断无恢复机制。未虚构 callback、未改 CPIO/helper；完整 clean 的 inherited 条件仍 open。`receipts/api16-contract.json`。

## 7. 测试

- host 16/16、RSP socket 7/7、旧 adapter 5/5。
- runner fake 11/11（含 stop-only）。
- stateful transport 5/5。
- **actual Observer/QMP/RSP/Sysregs E2E 1/1，continued=4**。
- 所有 fake/stateful 明确标注；无真实 QEMU 运行。

## 8. 剩余/授权

- 真实一次运行仍需完整候选复核后的单独授权；本目录不是授权。
- 完整 clean 仍 blocked 于 3a08 inherited restore 合同未建立；stop-only 可用于独立报告观察与宿主 cleanup，但 guest_restore_status 必须 unknown，不能称 guest End/API16 成功。
- 无实际 VM 调用；真实 QMP/RSP/Sysregs 协议仅 socketpair 假服务验证。

## 9. 交付

`REPORT.md`、`RESULT.json`、`SHA256SUMS`、`RUN-PLAN.md`、`DIFF-NOTES.md`、`CODE-DIFF.txt`、`observer/*`、`tests/*`、`receipts/*`；snapshot `superseded/pre-r4-b3cd050d/`。
