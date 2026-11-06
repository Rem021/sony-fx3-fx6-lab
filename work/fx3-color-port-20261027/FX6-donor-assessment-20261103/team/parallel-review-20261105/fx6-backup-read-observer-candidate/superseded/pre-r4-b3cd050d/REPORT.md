# FX6 AppFw two-key observer — r2 corrected host candidate

- Task：`task_b57412ab29f6`
- Dispatch：`ctx_e8ab32545125`
- Status：**HOST_ONLY_R3_CORRECTED; RUNTIME_CLEANUP_BLOCKED; NOT RUN**
- 只改本目录；当前 `superseded/pre-r2-3f182d91/` 与 `superseded/initial-e145f8c6/` 保留；旧 observer/固件/CPIO/Backup/helper/默认政策未改。
- 无 VM/guest/QMP/browser/server/live-process 交互；无 camera/USB/SD 操作；旧授权未复用；UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核。
- 输入 10 + 新增 4 项前后 hash 不变；本任务仅离线候选交付，不是 FX6 boot/menu 证据。

## 1. r3 协议/启动/恢复/收尾修复

- QMP: greeting → `qmp_capabilities` → 命令 id；异步 event/EOF/碎片/迟到回复/共用 deadline；无 capabilities 或 silent greeting 拒绝。
- Boot: `-S` prelaunch paused 确认 → QMP `cont` boot → 当前 serial 等 maps → QMP stop/query paused → arm → **RSP addressless `c`**；初始 arm 不再用 QMP cont 代替 GDB stop gate。
- Observe: 每个 entry/return stop 后，在无残余不确定时用 addressless `c` 恢复；测试状态严格（无 c 不给下一 stop），并处理立即 T05。
- Cleanup: QMP quit **先于** bounded wait/reap；正常 paused QEMU 不靠 terminate；记录 `qemu_exit`；成功后 `lock_released` 写回；stop/query 不确认时**不删断点/不调用 inherited**，只停/退自有进程并 unclean；RSP/QMP fd 有界关闭。
- Callback: 不再 daemon 超时后继续用 qmp；没有可取消实现时 `callback_not_cancellable_not_run`，不假称 bounded。
- 旧假 clean/异常收尾仍由测试覆盖。

`observer/host_runner.py` 的 `cleanup()` 现在：

- QMP `stop` 后**必须** `query-status` 为 `paused`；`stop` 抛异常不再中断，记录 `qmp_stop_or_query` 并继续自有进程回收。
- 断点使用 `possibly_installed` 集合；Z1 ACK 丢失不会视为未安装；residual 存在则**不恢复 guest**。
- inherited callback 必须显式 `passed=True`、`API16_restored=True`、`original_bytes_verified=True`、`ack_seen=True`；任意缺失/false/异常/超时都不 clean。**没有可取消 callback 实现时不运行**（`callback_not_cancellable_not_run`），不使用 daemon 线程伪造 bounded。
- 自有 child 的 `wait` 超时后只对**自有进程**做 terminate/kill，再 wait；若仍不确认退出，`qemu_reaped=false`，**不释放互斥锁**。
- 只有 stop 确认 + 断点全清 + inherited 合同满足 + child 明确 reaped + 锁 release 成功 + 无 errors，才 `clean=True`。未观测/错误状态绝不 clean。
- `finally` 覆盖 stop 异常、partial launch/connect、observer 异常、callback 失败/异常/超时、quit 失败、wait 超时、release 失败、重复 cleanup、无断点未初始化。重复 cleanup 幂等返回同一 receipt。
- fake runner 测试 10/10：正常两 key、false inherited+wait timeout（不 clean、锁保留）、stop 异常 fallback、无 map、无 hit、callback timeout、quit 失败、release 失败、partial launch。**不再出现 callback false 仍 clean**。

## 2. 完整宿主 runner 与默认禁用入口

- `observer/host_runner.py`：`HostRunner.run()` 覆盖 UUID/mount guard、锁获取、私有 run 目录/新 serial、一次 launch、QMP/RSP connect、当前 serial map、QMP stop paused 确认、Observer.arm、QMP cont、stop 轮询、TLS reader、无 hit/总 deadline、receipt、cleanup。`real_deps()` 提供真实 Popen/QMP/RSP/文件锁/map/Sysregs 依赖骨架；真实依赖未在本次调用。
- `observer/run_lifecycle.py` 默认 `DISABLED`；token 还需 `--new-run-approval` 与 fresh `--run-root`，否则拒绝；token 不是新运行批准。批准路径已接 `HostRunner`，但本任务不调用。
- RSP 白名单现包含 addressless `c`、`pN`、`qXfer:features:read`、Z1/z1；真实 runner 的 boot resume 用 QMP `cont`，每次观察 stop 后用 RSP addressless `c`，TLS 由 Sysregs 只读 XML/p 取得；仍无 Z0/写/软件单步。

## 3. 输入/argv/环境绑定

- `HostRunner.prepare` 从**固定 hash 通过的 baseline** `fx3_vm_command` 派生 34 argv；仅 index20 指向本次新私有 `serial.log`，index31 为固定 target CPIO `3a08…` loader；其余 32 项与 baseline 逐字相同。
- 环境严格为 baseline 的 5 项，不 merge 宿主 env；CPU `cortex-a35`、memory `5120`、machine/accel/kernel/DTB/model-env 均固定；target CPIO/appFw 校验 hash+size；旧 serial 拒绝；路径/锁/写由 UUID/mount guard 保护。
- 不使用可变 plan 的 initrd 或哈希来替换固定 baseline；target loader 路径固定。

## 4. 映射覆盖

- 只取最新 early block；要求每个 PT_LOAD 文件支持范围被 map rows 完整覆盖（允许 RELRO 合法拆分），同 inode、页对齐 offset、至少一页、x/w perms。
- 显式检查 ELF header、PHDR、两个 thunk 和两个 return 地址的映射范围/权限；非可执行 code 拒绝。
- 测试：合法 target epoch5 通过；全部 row 截成一页、offset jump、错误 perms、末端缺目标 code、不完整最新块均拒绝且不回退旧块。

## 5. 预算/身份

- `BudgetRSP` 统一 identity+data 总上限 128×4B；当前 appFw header 64B + PHDR 336B + 4 word = **104**；短读/预算超限拒绝。
- `Observer` 150s 观测；`HostRunner` 从 launch 前的 prepare 开始共用 180s 单调 deadline，所有 map/stop/IO/cleanup 使用剩余时限；cleanup 保留预算。fake clock 覆盖无 map、无 hit、callback 慢/cleanup 卡住。
- **gdb_cpu_thread** 是 QEMU system GDB 的 vCPU 线程，不是 guest AppFw TID；记录 `guest_tid:"unknown"`，同 CPU 不是同 guest 线程证明；跨 CPU 保守 unknown。入口/返回要求同 `gdb_cpu_thread`、TLS、x29、exact LR/return；不伪称 guest TID。
- `capacity_expected_static=4`，`capacity_runtime_w2=not_measured`，不伪称测到运行 w2。

## 6. Inherited API16 清理（关键局部 blocked）

- 目标 helper `fx3-cp-backup-reset-v1.ko` SHA `7e8d859e…`；serial 1023/1025 将 API16 `b4000b00…` 绑为 `58000050…`，1026/1032 无软件 CP。
- 旧 runner `restore_api103_v2`（SHA `8fb5f7a7…`）要求 `F100FILE` header @ `0x41d400000`、API16 `0xffffff80083220c8`、8B control 请求、ack、原 16B 验证。
- 对 3a08 CPIO 的真实 helper/observer/unbind 审计：`fx3-cp-backup-reset` 没有 `F100FILE`/API16 字符串；`fx3-file100-observer-v1` 明确 `observer_only_control=1`；`fx3-sync100-unbind-v1` 报 `reason=no_symbol`。因此只能结论为 **旧 restore_api103_v2 控制合同未建立**；target helper 仍有 `fx3_sync100_shutdown`/`sync100_restore` 与 `FX3_SYNC100_SHUTDOWN original16_verified` 标记，不能因缺 `F100FILE` 字符串推断“不存在任何恢复机制”。不能把旧 callback 假装接入，也不能修改 CPIO/helper。
- Adapter 接受注入 callback 但真实入口默认 `inherited_cleanup=None`，cleanup 会拒绝 clean；需要未来单独证明/批准的控制操作。具体来源/最小操作见 `receipts/api16-contract.json`。**只读 observer 本身无代码/寄存器/数据写，但若未来接入 inherited 8B control，全链路不是 zero-writes；本任务不执行。**

## 7. 测试

- `tests/test_host.py` **16/16**（fake RSP + target serial map/APP bytes）：两 key、旧 ASLR、错 ELF/PHDR/机器字、错 entry LR/PC、错 return frame/TID/TLS/call、读失败、timeout、残余、截断/不完整 map、offset/perms、ACK 丢失、预算/短读。
- `tests/test_rsp_host.py` **7/7**：真实 socketpair；错误/缺失 checksum、分片/合包、console/async T05、重复 thread、pPID.TID、timeout。
- `tests/test_adapter.py` **5/5**：旧 lightweight adapter 的私有输出/清理/缺失 callback/deadline。
- `tests/test_runner.py` **10/10**：完整 HostRunner fake E2E 正反例（见第 1 节）。
- `tests/test_stateful_transport.py` **4/4**：实际 QMP/RSP 类 + socketpair（greeting/capabilities/id、缺能力、无响应 timeout、addressless c 后立即 T05）。
- `tests/test_e2e_stateful.py` **1/1**：实际 HostRunner+实际 QMP/RSP socketpair，boot `-S`→cont→map→stop→arm→c；fake guest observer only。
- 所有 fake/mock 明确标注，不是真实 CPU/menu 证据。

## 8. 结论/剩余

- r2 指出的 clean、map 覆盖、deadline、baseline 比较、runner 占位均已代码修复并有 fake 反例；RSP 协议修复保留。
- **未运行**；真实 inherited API16/unbind 控制合同未在 3a08 目标上建立，故 actual runtime clean 仍 blocked；不称 runtime-ready。QMP/RSP 状态协议已用 socketpair 覆盖，但仍非真实 QEMU 证据。
- 当前候选仅可提交复核；真实一次运行需完整方案复核后另行授权；本目录不是运行授权。

## 9. 交付

`REPORT.md`、`RESULT.json`、`SHA256SUMS`、`RUN-PLAN.md`、`DIFF-NOTES.md`、`CODE-DIFF.txt`、`observer/*`、`tests/*`、`receipts/*`；初始/当前 snapshot 在 `superseded/`。
