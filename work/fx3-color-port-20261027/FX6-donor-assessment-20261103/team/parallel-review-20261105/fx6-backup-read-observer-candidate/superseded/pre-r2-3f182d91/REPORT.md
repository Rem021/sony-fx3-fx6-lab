# FX6 AppFw two-key Backup read observer — corrected host candidate

- Task：`task_a11971763fc5`
- Dispatch：`ctx_064d81a251c4`
- Status：**HOST_ONLY_CORRECTED_CANDIDATE; RUNTIME_CLEANUP_OPEN; NOT RUN**
- 只修改本目录；旧 candidate e145f8c6 已快照在 `superseded/initial-e145f8c6/`；旧 observer、固件、CPIO、Backup、helper、默认运行政策未改。
- 无 VM/guest/browser/server/QMP/live-process 交互；无 camera/USB/SD 操作；旧授权未复用。
- 输入 10 项 + 关键新增 4 项前后 hash 不变（`receipts/input-compare.json`、`receipts/extra-input-compare.json`）。

## 1. 已修复的协调器四项缺陷

1. **RSP framing/checksum**：`observer/rsp_readonly.py` 现在是实际使用的类，不再使用 test Fake 绕过。严格解析 `$payload#HH`，必须恰好两位 hex checksum；`+$OK#00`（错误 checksum）、`+$OK#`/缺 checksum/EOF 均拒绝；支持流式分包/合包、前导 ACK、`O` console、异步 `T05` stop、timeout/EOF。`tests/test_rsp_host.py` 用真实 socketpair 跑实际类，7/7。
2. **T05 thread**：`select_thread` 只接受 `T05...;` 且 `thread:` 字段恰好 1 个；值必须是 hex 或 `pPID.TID`；`T05thread:1;thread:2;` 拒绝。QEMU system GDB 的 thread-id 是 **vCPU/GDB CPU thread**，不是 guest AppFw TID；记录字段改为 `gdb_cpu_thread`，`guest_tid:"unknown"`，不做 `int()`。返回必须同 `gdb_cpu_thread`；跨 CPU 保守判 unknown，不能称同 guest 线程。
3. **map 严格性**：只取**最新** early map block；不完整/矛盾/无 appFw 不得回退旧块。每个 PT_LOAD 必须有同 inode、页对齐 offset、至少覆盖一页的 row，并检查 x/w perms；所有 row end=start+1、截断 row、错误 perms 均拒绝。`tests/test_host.py` 覆盖截断和不完整最新块。
4. **预算/短读**：`BudgetRSP` 对 identity+data 总读取统一计数，上限 128 次 × 4B；当前 AppFw header+PHDR+四字实际 104 次；短读拒绝；`Observer` 150s deadline、adapter 总 180s，data read 上限 16、stop 上限 8。`capacity_static=4` 与 `capacity_runtime_w2=not_measured` 分开，绝不伪称测到 w2。

## 2. 目标/地址/身份

- target CPIO：`3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b`（不放宽）。
- target appFw：`b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be`。
- serial：`377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e`；baseline：`854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`。
- thunk entry `0x2169784` / `0x21697d4`；exact return `0x11f67d4` / `0x11f67f4`；frame slot `+0xb4`/`+0xc4`；thunk 原文 `e10300aa`。
- 当前 epoch5 map 仅作为离线 fixture：pid237，bias `0x7ed3ccc000`；实际运行必须从新 run 的完整 maps 重新计算，不得用历史 ASLR。
- 身份门：Stage1 当前完整 early maps + appFw 全部 PT_LOAD；Stage2 live CPU 的 appFw ELF header/PHDR/四个原字；再要求 entry `x0=x29+slot`、`x30=exact return`、TLS 可得；return 同 `gdb_cpu_thread`/TLS/x29、exact return 字；缺失任一 -> unknown 停止。**同 CPU 不等于同 guest TID**；guest TID 无独立证据时保持 unknown。

## 3. 离线执行适配器

- `observer/execution_adapter.py`：私有 run dir + 新 `serial.log`（`open('x')`，拒绝旧输出），index20 指向新私有串口，index31 固定 target CPIO；其他 32 项 argv 不变；prepare 直接校验 baseline/APP_ELF/target CPIO full SHA。
- arm：QMP stop + `query-status` 必须 paused；Z1 前把地址放入 `possibly_installed`；ACK 丢失绝不当作未安装。
- cleanup：QMP stop -> 对 possibly 逐个 `z1` -> 若 residual 保持 stopped，QMP quit/只回收自有 QEMU，不恢复 guest；不得带残余断点恢复。
- `tests/test_adapter.py` fake QMP/QEMU/locks/observer 5/5：正常私有路径+arm/consume/cleanup、residual 无继承无 resume、缺失 inherited cleanup 阻断、旧输出拒绝、总/观测 deadline。
- `observer/run_lifecycle.py` 默认输出 `DISABLED`；token `APPROVE_GRMREAL46_TWO_KEYS_0214_0218` 只显示 `READY_FOR_REVIEW`，不启动。
- **继承清理未删**：目标 grmreal46 helper `fx3-cp-backup-reset-v1.ko`（SHA `7e8d859e…`）在 serial 1023/1025 将 API16 从 `b4000b00…` 绑定到 `58000050…`，1026/1032 无软件 CP；旧 runner 的 `restore_api103_v2`（SHA `8fb5f7a7…`）通过现有 guest unbind helper 做 8B control 请求+ack+16B original 校验。新 adapter **自身不写** API16，但要求注入该继承 `inherited_cleanup`；缺失时状态 `inherited_cleanup_required`，不恢复 guest。回执 `receipts/api16-contract.json`。
- 因而：**离线候选完整；真实运行仍有一个精确的 inherited cleanup 条件**，需要已审 restore callback/范围；这是 local technical condition，不是假装 runtime-ready。

## 4. 测试

- `tests/test_host.py` 14/14：当前 epoch5 fixture、两 key entry/return、旧 ASLR/空映射、错 ELF/PHDR/字、错 LR/PC/frame/TID/TLS/return、读失败、超时、残余、截断/不完整 map、ACK 丢失、短读/预算。
- `tests/test_rsp_host.py` 7/7：**真实 socketpair**，非 Fake.command；错误/缺失 checksum、分片/合包、console/async T05、重复 thread、pPID.TID、timeout。
- `tests/test_adapter.py` 5/5：fake lifecycle，非真实 QEMU。
- 明确：fake RSP/fixture 不是真实 CPU/menu；没有运行证据。

## 5. Baseline/argv/清理差异

- `baseline_binding.py` 验证 baseline SHA、5 个 frozen artifact、QEMU/kernel/DTB/CPU/memory/model-env；qemu argv 34 项仅 index31 为 target CPIO；adapter 实际 prepare 只改 index20 为新私有 serial（baseline plan 已把 index31 固定 target），其余不变。
- 旧 observer CPIO `bb61…`、appFw `a1c5…`、CAPID/AP 地址、旧 API16 清理合同不继承；新候选 CPIO `3a08…`、appFw `b1fe…`。旧 observer 文件和授权均未改/复用。
- 旧 `restore_api103_v2` 的 8B control/guest unbind 是继承清理，不删除；新 adapter 不新增 guest 写，仅要求注入该合同。

## 6. 时序

66ed splitlines epoch5 map end=8950，3147/3176 assert 线 11688/11738；历史 map 早于 assert，但不保证每次 live arming 赶得上。实际 adapter 必须检查当前 run map/identity；若目标已过/超时/未捕获，只能报告 unknown，不得宣称捕获。未再盲扫 receiver。

## 7. 可回答/不可回答

**可回答（未来获准运行且身份通过）**：两 key 的 entry buffer 指针、static capacity 4、entry 前 4B、return w0/hex、return 后 4B、GDB CPU thread、PID、TLS/x29/精确 callsite 配对；是否两个 callsite 各命中一次。

**不可回答**：guest OS TID（QEMU GDB thread 不是它；无独立证据）；0x3e014d receiver；92fe 是否 appFw 来源；FX3 共享消费者；boot/menu；迁移效果。

## 8. 状态/剩余

- 四项协调器缺陷已修复；实际 RSP/地图/线程/预算/ACK/生命周期离线测试已补齐。
- **未运行**：无 VM/QMP/guest 连接，无真实 CPU hit；本任务完成仅指离线候选交付。
- **局部 runtime blocker**：inherited API16/unbind cleanup 需由已审 callback 提供并验证；未提供前不把 candidate 称为 runtime-ready，也不实际启动。
- 任何未来运行仍需单独 VM 授权；本目录不是运行授权。

## 9. 交付

`REPORT.md`、`RESULT.json`、`SHA256SUMS`、`RUN-PLAN.md`、`DIFF-NOTES.md`、`CODE-DIFF.txt`、`observer/*.py`、`tests/*`、`receipts/*`。初始 e145 快照在 `superseded/initial-e145f8c6/`。
