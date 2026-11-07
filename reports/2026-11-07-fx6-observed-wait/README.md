# FX6：实际等待栈、输入修复与原厂线程池恢复

2026-11-07，基于重启后已完成产物继续；旧运行未重跑。**已修复独立 runner 的 Unix GDB 输入端点，以及 295 自行跳过原厂线程池的缺口。单变量运行确认真实 cold-boot 已执行到 HDMI 格式请求；原厂菜单仍未通过。** 当前等待已落到一条真实 BB/CP 请求，不能用假接收成功或空锁掩盖。

## 已完成的三轮独立运行

| 运行 | 变更与结果 | 验证边界 |
|---|---|---|
| `observer-004ab971f4` | 295 派生，只加接收观察绑定和线程元数据。120.101s，正常回收/解锁；实际 GOT provider/readback 指向观察库，但没有 ENTER/EXIT；AppFw 224 / UX 225、226 各 37 次睡眠/futex 样本 | 原 argv 末尾重复 `-s`，主机连接 Unix `g` 失败，未有软件键写入。四捕获全零 |
| `observer-00d964f97c` | 新快照候选，修正 host 端点；120.164s，exit0、正常回收/解锁。uptime22.65s 顺序读取4个线程寄存器/FP链，4次 DETACH rc0；helper137ms、rc0 | key1 只证明软件门写入/回读，key2 顺序校验失败后停止，不重发；消费和 UI 响应未证实。四捕获仍全零 |
| `worker-pool-restore-a3af746e3d` | 仅自有 shim 两行删掉 `12d825c` NOP并同步数组/循环上限；120.209s，exit0、回收/解锁。出现129个实际TID，cold-boot生产者执行到 `init_hdmi`；9次接收进入/8次返回 | AppFw future仍等待；唯一未返回接收为TID231 `SeqQueueCommon` 的BB请求。129次快照/DETACH成功，helper975ms。四捕获仍全零，键证据边界同上 |

三轮 GPE0/1 都来自同一 `0x41e001000`，不是两路独立显示。`APPFW_SEGV/assert=0` 只描述本运行日志；控制候选含五个 NOP，修复候选仍保留四个 NOP、Backup 空成功和 MWF guard，不能据此宣布原厂生命周期恢复。[首轮复核](observer-review/observer-run-review.md)、[快照轮复核](snapshot-run-review/snapshot-run-review.md)、[修复轮复核](worker-pool-restore-run-review/worker-pool-restore-run-review.md)保存完整统计与来源哈希。

## 实际 AppFw 等待链

控制运行 `observer-00d964f97c` 以 COMM/STATUS 绑定 TID224=`AppFw`，没有跨运行复用线程编号。完整快照的31个 FP saved-LR 加8个 PC/LR，共39个地址，全部用**本次 CPIO 中的实际 ELF**、`/proc/maps` 和 `PT_LOAD` 解析成功；VA 不作为文件偏移。实际 AppFw 为 50,520,424B / SHA `a1c58b69…`。

```mermaid
flowchart LR
  U["UI worker<br/>appFw+c0b52c"] --> A["App主循环<br/>+c0a6d0"]
  A --> I["App::initialize<br/>+c09de4 调用"]
  I --> T["+12d9fc8 → +12d8174<br/>记录返回点12da024 / 12d9dec"]
  T --> F["model_future::wait<br/>+1acd874 / 返回点1acd988"]
  F --> C["std::condition_variable::wait"]
  C --> P["pthread_cond_wait<br/>libpthread+d5ec"]
```

`model_future::wait` 名称由同一 ELF 的断言字符串 `void model::model_future::wait()` 绑定。`App::initialize +c09e0c` 才调用屏幕 manager 的 `initialize +de31ac`，因此**此时这次 App 初始化仍等在它前面**。不能把当前等待称为 App 事件队列接收，也不能据 ScreenArea 个数推断 HOME presenter 已构造。两个 UX 资源线程实际停在 `MsgQueAsyncImpl::get → WorkerThread::run`，同样不等同原厂菜单完成。

[实际地址及解析](analysis/resolved.json)、[快照输入](analysis/snapshot.json)、[调用点断言](analysis/callsite-facts.json)、[解析脚本](analysis/resolve_snapshot.py)可复核上述边界。代码页因既有 NOP 写入被 `mprotect` 成 RWX；解析允许映射的 W 与原 ELF PF_W 不同，不把这种正常差异伪报成来源错误。已用观察库 VA `0x106d4` 对应文件偏移 `0x6d4` 作实际输入核对。

读取线程需要短暂停顿，属于会影响调度的诊断。快照后主线程 wchan 从 nanosleep 变成 `sys_restart_syscall` 有实录；AppFw/UX 仍持续采到 futex。137ms 不作为应用性能数据，更不作为实机结论。[helper 源码与约束](snapshot-candidate/README.md)。

## 主机输入修复

原 argv 先选 `-gdb chardev:keygate93` / Unix `g`，末尾又用 `-s` 选择 TCP1234。已删除这个重复项，保留已有 Unix gate 与 QMP 单读者。相同 QEMU11.1.2 的无固件停止态 smoke 完成 `qSupported` 和 `?` 协议交互；快照轮进一步取得了软件门写入/回读记录。该选项语义也由实际二进制 help 和 [QEMU 官方说明](https://www.qemu.org/docs/master/system/gdb.html)交叉验证。

[runner v2](runner/README.md)含端点修复和4项验证；[v3](runner-v3/README.md)增加新 proof schema 与完整 295→observer→snapshot 父链校验，15项测试通过。未知 schema、缺失/假 flag、父链篡改及不一致的派生引用均拒绝。继续保留原两把锁、120s预算、每 manifest 一次 Start、未知投递停止且不重发的约束。

## 已执行的原生修复与新等待点

实际栈驱动的新静态追踪将这项 future 绑定到 cold-boot 命令 `0x2d`，其完成路径调用 ready/notify；295 的 `+12d825c` NOP 跳过 `+1d96370` 的原厂工作线程池创建。[完整等待/通知链](analysis/wait-chain/wait-chain.md)明确区分自行删除执行器与外部服务缺失。

已构建并运行**只恢复这个原始调用**的候选：自有源码仅两行变化，NOP数组和循环上限从5改4，唯一移除 `12d825c`；不改 ready/notify、超时、消息内容或返回值。原295 shim全部17个 `SHF_ALLOC` 节的字节、地址及相关元数据复现一致，原源码到实际运行对象的关系得到绑定；复现命令是由内容一致性确认的命令，不冒称历史命令原文。CPIO只改变 `usr/lib/libgrm-fbinit9.so`，其余所有 raw record、顺序、两个 trailer 和空隙均独立核对一致。14个原导入与导出契约保持。[候选源码与凭据](worker-pool-restore-candidate/README.md)。[runner v4](runner-v4/README.md)另以24项检查验证修复差异和完整来源链。

实际出现的总任务数先128后129；这里不能把“池工厂有45项”说成“进程只有45个线程”。129个不同TID由COMM/STATUS和快照分别核对。接收观察器记录9次ENTER/8次EXIT，前8次返回rc0，唯一未配对seq9为：

```text
TID231 = SeqQueueCommon
appFw LR+20ef7cc = bb_request_reply
qid=0x81cf610f, timeout=-1
CP destination=0x92840747, source=0x81cf610f
request=0d202d030a0001800000 (10B)
```

同一线程实际栈经过 `sequence_cold_boot::init_hdmi()`，到 `adf_set_hdmi_format`，在 `cold_boot` 取promise并fulfill之前停住。与前一控制运行相比，这同时证明**原厂执行器已经实际执行生产者**，也证明当前尚不能宣称 future完成或App初始化已返回。[实际生产者与BB等待证据](worker-pool-outcome/restore-outcome.md)。129个线程均成功解除跟踪；AppFw仍采到futex，SeqQueueCommon仍采到OSAL接收等待。接收的errno22是原样保留值，不能把rc0旁的遗留errno解释为接收失败。

已进一步从固定FX6 CP原件绑定完成函数：12B头为 `{0x200d,0x132d,12,0x8001}`，`+8`来自处理函数状态；内部请求分支会向 `0x9058003f` 发子请求。子发送非零失败时才生成 `-1` 完成，正常情况由下游事件带回状态。AP将 `-1` 映射成 `0x6f`；`init_hdmi` 会检查、记录并提前返回，外层cold-boot继续。这不能被解释为HDMI初始化成功。[请求与原CP契约](bb-request-contract/bb-request-contract.md)。

仍有两项协议缺口：外部 `0x032d` 到内部请求索引的精确入口边、下游服务的真实完成条件；事务FIFO/取消的完整所有权也未恢复。[独立审查](adf-negative-model-review/adf-negative-model-review.md)还确认，当前VM桥接层对未知目的地实际是返回0、无回复/无释放，**并没有得到原CP所依据的“下游send返回非零”结果**。因此“没有专项handler”不足以选择 `-1` 作为完成状态。本轮既未构造成功回复，也未把未知路径改装成原厂失败；HDMI等待保持待修，后续需先核路由状态、派发和事务所有权。96B DFS异步通知和既有自编CAPID常量不用于填补本协议。

## 已核对的独立排除项

已排除日志中的两个误导方向：

- 最后一条 `0x92a208fc /96B/no_reply` 是与当前 UPM 的异步 DFS 通知路径吻合的消息。当前模块显式申请96B，原 FX6 同构模块申请40B；明确初始化的仅前20B，`a5a5a5a5` 是分配器 source 初值。没有 sender PC/TID，不能唯一归属或把尾部当指针数组，更不能为它制造同步应答。[证据](backup-contract/MESSAGE-96B.md)。
- `Backup_read` 不使用残留 w2 作长度，`backup_sync_msg` 的函数返回值也不是业务结果。已提供有类型/尺寸约束的四键读取候选及97项 C 检查、140项模板检查；**尚未集成 guest**。295 的空成功不是契约修复。[契约报告](backup-contract/README.md)。

另一运行线的302–305核对也保留在[运行审计](backup-contract/latest-mwf-runtime.md)：302确有被空 fault 数组漏报的 SIGSEGV；303/305 的无崩溃包含锁/消息空对象跳过，未证明 MWF 对象初始化。305的TID224没有COMM，不能套用本轮线程身份。

## 来源与归档

诊断按 Linux4.9 AArch64 `NT_PRSTATUS` 的272B布局实现，实际返回长度也经校验；SEIZE/INTERRUPT/PEEKDATA/DETACH 的用法依据 [Linux ptrace 手册](https://man7.org/linux/man-pages/man2/ptrace.2.html)及[版本固定的内核 ABI](https://raw.githubusercontent.com/torvalds/linux/v4.9/arch/arm64/include/uapi/asm/ptrace.h)。QEMU 的 system GDB thread 表示 vCPU，因此未用它伪充 Linux TID 栈。[来源与适用条件](analysis/research-sources.json)。

追加联网复核了 [Sony V6.00 OSS目录](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html)及[FX6官方规格](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx6v/specifications)。公开的glibc/GCC包及用户音频规格用于核对环境和术语，不能替代私有BB消息的原消费者和状态码证据；本报告不从产品音频参数推导CP应答。

正式目录只保存源码、文档、JSON和哈希；固件、ELF/KO、CPIO与帧 dump 留在被忽略的 `work/`。源码目录是审阅存档；重建需使用相应原始 work 目录与 BYOF 输入，不就地覆盖已经封存的候选。原始运行指针见[回执](analysis/runtime-receipt.json)，项目外供体未移动或改写；未操作物理相机。
