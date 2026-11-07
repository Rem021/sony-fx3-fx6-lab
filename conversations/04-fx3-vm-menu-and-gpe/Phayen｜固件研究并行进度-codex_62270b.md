# Phayen｜固件研究并行进度

- **Session ID**: `codex_62270b28_126b_48b3_807e_ea85894ab6a5`
- **Agent Provider**: `codex`
- **Orca Category Workspace**: `FX3｜虚拟机主屏菜单与 GPE 渲染修复`
- **Orca Workspace ID**: `e52bdbc7-1cf3-4bc8-bdd4-f37b01044ebd::/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab::workspace:2a92721a-f206-4472-82a5-edf30db5be8c`
- **Created At**: `2026-11-07T14:25:30.791Z`
- **Updated At**: `2026-11-07T16:43:49.717Z`
- **Captured Messages (User / Assistant)**: `33`

---

## 🤖 Assistant

已确认重启前的报告、构建记录和观察库都已保存，仓库也已推送；这些不需要重做。当前还有另一条主线的 299 实验在运行，我不会抢占或重复启动它。

接下来把已完成的观察库接入独立候选，保留冻结基线的行为，先取得真实线程和队列调用证据，再据此修复。

---

## 🤖 Assistant

我将只读核对 296–299 的完成回执、实际输入和串口证据；运行中的实验不纳入最终结论，也不连接或控制 VM。

---

## 🤖 Assistant

我会先绑定真实 Backup 库、调用者和记录模板，选择能证明类型与长度的少量启动键做离线候选；未知键保留原厂路径，避免再次把未定义寄存器或空成功当作数据契约。

---

## 🤖 Assistant

299 的结果也核清了：替换接收函数为“直接成功”没有解决崩溃。296–299 都落在同一个空锁对象路径：`libMWF` 把空对象中的 mutex 地址交给了 `pthread_mutex_lock`。

所以这轮不会沿用“伪造成功”的分支。独立候选只修正观察接入，确保能记录真实调用点，并保持原厂接收行为。

---

## 🤖 Assistant

候选已构建完成，正在核对实际 295 的动态库闭包、完整 CPIO 成员保留情况，以及观察器槽位绑定证据。确认后交由主 agent 执行唯一一次受控运行。

---

## 🤖 Assistant

冷核验已通过：新 launcher 和观察器的 55 个强导入符号及版本均由 295 原有的 glibc 2.25 闭包满足。原 CPIO 首个结束标记后的 58 条记录也已保留；候选已冻结，主 agent 正准备受控运行。

---

## 🤖 Assistant

独立候选已通过完整镜像差异检查和逐符号 ABI 校验：原件、旧 shim、Backup 行为和超时都保持 295，新增的只是观察接入与线程元数据记录。

现在执行一次 120 秒的受控 VM 验证，使用现有双锁；若锁被其他实验占用，就不启动。

---

## 🤖 Assistant

已交付 [契约报告与最小候选](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-backup-contract-fix-20261107/README.md)。

关键结论：

- 原厂 `Backup_read` 不使用调用者 `w2` 作为长度；295 的空成功仍违约。
- `backup_sync_msg` 返回 0 不等于业务成功；需要恢复整条原调用链。
- 四键均有 8B 证明；`fa0191/92` 可使用同一自有 arena 的地址/容量候选。
- `fa01a3/a4` 默认均为全一哨兵，现有假物理窗口缺少映射依据。
- 未知 ID 明确 `NOT_HANDLED`，交还原实现或失败。

[测试结果](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-backup-contract-fix-20261107/test-results.json)：97 项 C 检查通过（ASan/UBSan），140 项真实模板输入检查通过。未集成、未运行 VM、未改供体或共享源、未写 Git。

---

## 🤖 Assistant

296–299 审计完成：[报告](work/fx6-post-restart-audit-20261107/README.md)、[完整证据](work/fx6-post-restart-audit-20261107/evidence.json)。

- 四次均完整结束，但同样崩溃、GPE 帧全零，不能晋升修复基线。
- 新阻塞已精确绑定：`ObjShLock::Lock(this=NULL)` → `pthread_mutex_lock` 读取 `0x38`。上层 owner 尚未确定。
- 299 仅伪造 receive 返回值，没有原厂回执证据。
- `THREAD_END_217` 是 wchan 采样结束标记，不能解释为线程退出。
- 未连接或控制 VM；待 observer 完成回执后继续审计。

---

## 🤖 Assistant

运行中的首个关键验证已通过：实际 AppFw 接收槽位已回读到观察库地址，解决了此前普通 preload 可能被手工 GOT 修复绕过的问题。

目前这段日志还没有接收入口记���。我会等本轮完整结束，再结合线程名称和状态判断，避免把“没有日志”误当成“没有调用”或“已经修好”。

---

## 🤖 Assistant

独立候选已完成，可交主 agent 受控运行。

- 入口：[candidate-manifest.json](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-observer-integration-20261107/candidate-manifest.json)，SHA `d5732c03…`
- 仅改变 init、诊断 launcher，新增观察器；295 原 appFw、shim、Backup、NOP 保持原样。
- 全部 832 条 GOT 核对一致；显式绑定 recv 槽并记录 provider/readback。
- 55 个强导入及版本全部满足原 glibc 2.25 闭包。
- 首 TRAILER 后 58 条原记录完整保留。
- 基线源码重编的 `.text/.rodata/.got/.got.plt` 与实际 295 完全相同。

构建、源码 diff、成员证明、ABI 证明及指纹已收于同目录 [README.md](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-observer-integration-20261107/README.md)。未启动或连接 VM，未修改 donor 或 Git。

---

## 🤖 Assistant

恢复后的这轮观察测试已结束：接收函数的 GOT 槽位确实绑定到了观察库，AppFw 线程也持续存在，但一直停在 futex 等待，没有观察到接收入口。另查到按键测试在主机侧连接 GDB 时失败；我会先修正连接配置，再定位线程等待的位置。

---

## 🤖 Assistant

我会另建候选，先核对 guest 内核的 ptrace 支持与 AArch64 寄存器 ABI，再实现有超时、逐线程清理的一次性快照工具。它会短暂停住线程，相关干扰会明确记录；本轮不启动 VM。

---

## 🤖 Assistant

下一轮将加一项定点诊断：短暂停住各个 guest 线程，读取寄存器和调用栈后立即恢复。这样能把“停在 futex”缩小到具体调用路径；QEMU 官方文档也确认，主机 GDB 显示的是虚拟 CPU，不能直接当作 Linux 线程栈。此次会保留原接收超时和消息返回值。

---

## 🤖 Assistant

已确认四份画面捕获全为零，当前仍不能算菜单修复通过。日志里最后一条 CP 消息也找到了原厂发送函数：它是异步发送，申请 40 字节，而内核日志报告 96 字节。还需核对这两个长度的含义，目前不能据此认定消息损坏或给它伪造回复。

---

## 🤖 Assistant

一次性快照工具的核心逻辑已实现，主机上的模拟测试覆盖了正常采样、等待超时、寄存器读取失败、分离失败、取消和信号保留。正在补齐严格链接与归档核验；还会在暂停前读取各线程的 `/proc/.../syscall`，供后续定位内核返回 PC。

---

## 🤖 Assistant

按键连接配置已修正：去掉重复的 `-s`，保留 Unix socket。用同一 QEMU 做的无固件 smoke 测试已完成 GDB 协议交互并正常回收。接下来会在新的栈快照候选上验证 guest 运行，已完成的旧候选保持封存。

---

## 🤖 Assistant

已完成两项交付：

- [Observer 运行复核](work/fx6-post-restart-audit-20261107/observer-run-review.md)：AppFw 224 持续存在，37 次均为 futex 等待；没有用户 LR/qid。四份捕获全零。
- [Runner v2](work/fx6-observer-runtime-v2-20261107/README.md)：移除重复 `-s`，保留 Unix `g`；纠正未验证菜单标识，未知投递停止且不重发。

4 项测试及同一 QEMU 的停止态 Unix RSP smoke 通过。未启动 Sony guest，冻结候选未改，新 manifest 离线检查通过。

---

## 🤖 Assistant

已按白名单复制到正式报告：

- `reports/2026-11-07-fx6-observed-wait/runner/`
- `reports/2026-11-07-fx6-observed-wait/observer-review/`

共 12 个文件，两目录均附 `files.json`。源码哈希完全一致，仅调整必要文档链接。未复制固件/二进制/缓存，未执行 Git 或同步。

---

## 🤖 Assistant

新候选已冻结并交给主 agent：相较上一轮，只改 init 的一次性调用并新增 helper，两个原归档结束标记及其余成员逐字节保留。严格链接、41 个强导入的版本闭包核验和 18 个��机模拟场景均通过；实际 guest 快照仍待主 agent 运行。

---

## 🤖 Assistant

栈快照候选已构建完成，源码测试和链接检查通过。启动前校验拦住了一个兼容问题：新候选的成员证明格式更严格，旧 runner 尚不识别；我会补齐格式支持和完整来源链校验。另外检测到另一条研究线正在运行 305 候选，本轮会排队，等其释放锁后再启动。

---

## 🤖 Assistant

CP 消息的长度差已有更具体的解释：当前候选里的 UPM 内核模块本身会申请 96 字节，真正 FX6 的同类模块申请 40 字节；两者都只初始化前 20 字节。`a5a5a5a5` 来源字段也是分配器预置值。因此，这段日志不足以证明指针污染，也不足以认定它是 AppFw 等待的原因。

---

## 🤖 Assistant

已复制 12 个白名单文件至 [backup-contract](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-07-fx6-observed-wait/backup-contract/files.json)，逐文件哈希核验通过。

[96B 报告](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-07-fx6-observed-wait/backup-contract/MESSAGE-96B.md)确认：

- 当前内核 UPM 显式分配 96B；原 FX6 对应路径分配 40B。
- 仅前 20B 有明确写入，尾部不能当指针数组。
- `a5a5a5a5` 是分配器 source 初始化值。
- 这是异步 DFS 通知；无证据把它绑��到当前 futex 等待或 Backup 空成功链。
- 缺少 sender PC/TID，未伪造唯一生产点归属。

未复制二进制，未运行 VM、修改 shim 或执行 Git/sync。

---

## 🤖 Assistant

独立快照候选已完成并冻结，未运行 VM。

- manifest SHA：`df39ee856ea9c667d786920c0ec9c12b43992fbc17525870cbd53b38f5c8da42`
- 仅改 init，新增 helper；两条原 TRAILER 和其余成员逐字节保留。
- 严格 SDK 2.25 链接、41 个强导入闭包及 18 次主机模拟用例通过。
- 源码与凭据已按白名单复制到正式报告目录，未复制二进制、CPIO 或缓存，未写 Git。

说明与入口：[snapshot-candidate/README.md](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-07-fx6-observed-wait/snapshot-candidate/README.md)。

---

## 🤖 Assistant

新候选的完整来源链校验已通过，可以开始一次受控运行。另一线最新的 305 结果也已核对：空锁和空消息表的跳过逻辑确实执行了，但没有 MWF 初始化成功的凭据。新一轮会读取实际线程栈，确认稳定等待落在哪条调用路径。

---

## 🤖 Assistant

v3 已完成：[交付说明](work/fx6-observer-runtime-v3-20261107/README.md)。

- 明确验证两种 proof schema及完整 295 → observer → snapshot 父链，缺字段或未知 schema 拒绝。
- 15 项测试通过，实际 snapshot manifest `--check` 返回 0。
- Runner SHA：`8147eaa9eed628c7bf30d7d2b92f478b3d434cf047a3d8959d317451108c007b`。
- v2、候选及父链文件未改；未启动 VM、获取锁或重复 smoke。

---

## 🤖 Assistant

已复制至 `reports/2026-11-07-fx6-observed-wait/runner-v3/`，附 `files.json`。9 个文件哈希全部一致，runner 保持 `8147eaa9…c007b`。

未重复测试、操作 VM 或读取运行中片段；等待完成回执。

---

## 🤖 Assistant

已读到完整线程快照，4 个线程均成功解除跟踪。AppFw 当前等在 `pthread_cond_wait → std::condition_variable::wait → appFw 内部同步路径`；两个 UX 资源线程则等在消息队列。这已把应用线程的等待与先前怀疑的 OSAL 接收点区分开，下一步会解析具体调用点。主机按键也首次完成了软件门写入和回读，尚无 guest 消费证明。

---

## 🤖 Assistant

我会沿这条已确认的等待链反查条件变量、状态写入和通知路径，再核对 295 的五处 NOP 是否影响了生产者。先把“缺少服务”和“补丁造成等待”分开验证；本轮只读实际 ELF，不运行 VM。

---

## 🤖 Assistant

核对完成：[运行报告](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-backup-contract-fix-20261107/latest-mwf-runtime.md)、[JSON 证据](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-backup-contract-fix-20261107/latest-mwf-runtime.json)。

- 302 实际发生 libMWF SIGSEGV，receipt 的空 fault 列表漏报。
- 303 跳过 Lock/Unlock；305 执行8组 NULL 操作跳过，未证明对象初始化。
- 现有日志无法判定 MWF_Init 是否调用或成功返回；没有专门观测。
- 303/305 均超时，所采 GPE/DMM 文件全零。
- 305 的 TID224 显示 OSAL 接收等待，但缺少 comm，不能沿用295的线程身份。

未修改他人文件或运行 VM。

---

## 🤖 Assistant

这一轮已正常结束，进程已回收、两把锁已释放。调用栈定位到 `App::initialize` 在 `+0xc09de4` 发起的同步调用；在这次调用中，它仍停在屏幕 manager 初始化之前。现在可以继续追这个同步调用的完成通知来源，暂不应跳过等待，否则会掩盖未完成的初始化。

---

## 🤖 Assistant

复核完成并复制到 [正式报告](reports/2026-11-07-fx6-observed-wait/snapshot-run-review/snapshot-run-review.md)。

21 项检查通过；4 次 snapshot/detach 完整成功，helper 用时 137 ms。四份捕获全零，AppFw/UX 线程持续等待。key 1 仅证明软件写入/回读，key 2 失败后停止且未重发。

未操作 VM，未重复反汇编；源码和运行证据未改。

---

## 🤖 Assistant

找到了一个可修复的具体原因：295 的跳过表禁用了原厂工作线程池创建，而 AppFw 正在等待的 cold-boot future，需要由这个池执行并完成通知。实际快照中也没有这些工作线程。我会先只恢复这一个调用，保留其余行为，验证它能否越过当前屏障。

---
