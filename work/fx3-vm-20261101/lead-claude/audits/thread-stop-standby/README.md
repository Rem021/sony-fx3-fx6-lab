# AP96 assert 后的线程停止审计

结论：最符合现有证据的发送者是 **FX3 原内核的异常转储路径**，不是待机或我们的按键 worker 自停。原厂 `lib_assert` 引发 SIGABRT，原内核 `do_coredump` 在进入 exception monitor 前，调用 `stop_all_threads_timeout` 对同地址空间的其他线程发送 **SIGSTOP(19)**；因此 tid327 的 `do_signal_stop` 与该路径吻合。静态发送链已闭合；本轮没有捕获故障线程的 `do_coredump` 实时栈或 signal_generate/siginfo，运行时发送者身份仍是强证据推断，而非直接信号追踪回执。[证据：K `81dcb04`、`80c5ae4..80c5af8`；S 248655–248724；P `kernel`/`timeline`]

本轮依协调者消息 `msg_2f2fb41c2314` 收窄到 assert → exception stop 与 UIPC 时序；原任务中的电池、自动关机及省电条件全面审计未继续。未启动 QEMU，未运行 target ELF，未修改运行链或原件；仅输出本目录的脚本、proof 和本文。

## 复跑及证据约定

从 Mac 项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/thread-stop-standby/audit_thread_stop.py
```

退出 0 重建 [thread-stop-proof.json](thread-stop-proof.json)。脚本先核对外盘 UUID，读取固定 SHA 的原 kernel Image，重解压原 kallsyms、反汇编并断言关键分支及信号常量；另枚举 159 份投影 ELF 的信号导入与直接 B/BL→PLT 调用，并重算 serial 时序。它不执行 QEMU、runner 或任何原厂代码，唯一写入是同目录 proof。[脚本：`audit_thread_stop.py`]

本文缩写：

- **K**：`work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin`，SHA256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`；完整 VA 前缀 `0xffffff800`，例如 `81dcb04` = `0xffffff80081dcb04`。
- **A/C**：`menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so` / `lib/libc-2.25.so` 的 ELF VA。
- **U**：`menu-repair-01/original-uipc/original-modules/osal_uipc.ko` 的 **ET_REL `.text` 偏移**，不是已加载 VA；外部调用由原 relocation 表定位。
- **S**：`menu-repair-01/runtime/runs/ap96v1replaydiag-0f72a1e0/serial.log`，**1-based 物理 LF 行**，保留输出交错。
- **P**：本目录 proof 对应 JSON 字段。所有输入路径、字节数、SHA256 在 `inputs`。

已有 correction JSON 及 thread-live JSON 的部分行号来自不同换行解析，约有数行差异；本文以原始 LF 计数为准，不把该差异解释成不同运行。[P `timeline.line_convention`；`source_evidence`；S 248615、248655–248657]

## 1. 谁发 SIGSTOP，以及为何观测库没有 kill 日志

| 原代码位置 | 指令/行为 | 含义 |
|---|---|---|
| A `2ebf404..2ebf420` | 设置 false / lib_assert.cpp / 函数名 / 行30，`bl 1594060` | PLT1594060 是 `__assert_fail`；串口 caller 的 `2ebf424` 是该调用返回地址 |
| C `2a930..2a978`，`2a8e0` | `__assert_fail`→内部 assert base→`bl 32350` | 原 libc 直接进入 abort，不经过可抢占的 abort PLT |
| C `3246c..32470` | `mov w0,#6; bl 30fe0` | abort 直接调用 libc 内部 raise(SIGABRT)，不经过观测库 raise wrapper |
| C `31030..31054` | getpid/gettid；`mov x8,#0x83; svc #0` | raise 用 AArch64 tgkill(131) 原 syscall；signal 参数由 w19 传入 |
| K `80ae768..80ae790` | core-signal 掩码包含6；调用 `do_coredump@81dca40` | SIGABRT 进入 core/异常路径 |
| K `81dcad8..81dcb04` | 检查 exception_check_mode / exception_check，`x1=0x1b58`、`w2=0`，调用 `80c5a50` | 原 exception callback 分支先停同 mm 线程，等待期限7000ms |
| K `80c5ac8..80c5af8` | 比较 task mm 与目标 mm；跳过 current；`w0=0x13,w2=1; bl 80adb68` | `send_sig(SIGSTOP, peer_task, 1)`，发送者在内核，不是用户态 kill |
| K `81dcb48..81dcb64` | `blr exception_check`；返回后 `start_all_threads(mm)` | monitor 返回后本来会发送 SIGCONT；本次没有继续运行证据 |

上述每条的原始字节和完整指令保存在 P `app_libc_blocks`、`kernel.blocks`。原内核 `exception_check_mode` 初值为3；`__boottime_em_module_init@863cd20` 在 `863cd48` 将 `em_exception_monitor@8136f28` 写入 `exception_check@870b6e8`。S 486–487 证明这次启动执行该初始化并返回0；没有采集运行时 callback 槽的内存读回，故其后是否被其他组件改写仍未直接验证。[K `869de2c`、`863cd34..863cd48`；P `kernel.exception_check_mode_initial`/`timeline.exception_init`]

`signal-observe-v2.c:9–18` 只报告并转发 kill/raise/pthread_kill/abort；`:19` 转发原 `__assert_fail`。它不生成19/20/21/22，也没有 tgkill、直接 svc 或内核 send_sig 的观测能力。原 libc 的内部直接调用加上内核发信号，使“只有 assert marker、没有 kill/raise marker”成为合理结果，不能据此排除信号停止。[C `2a8e0`、`32470`、`31054`；P `source_evidence`；S 248655–248657]

Linux 官方语义也将 SIGSTOP/SIGTSTP/SIGTTIN/SIGTTOU 的停止和 ptrace stop 区分；这里记录的是 `State T` / `do_signal_stop`，而非 `ptrace_stop`。该常识仅辅助解释，Sony 分支结论来自上述原 Image，不将通用上游源码当作本机二进制证明。[Linux man-pages ptrace(2)](https://man7.org/linux/man-pages/man2/ptrace.2.html)；[Linux v4.9.226 signal.c](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable.git/+/refs/tags/v4.9.226/kernel/signal.c)

## 2. assert 与 UIPC 错误的先后及真正触发点

| S 行 | 记录 |
|---|---|
| 248604 | 第二次 VDF 0x119，tid432，dst92840747，src81cf61c4，28B，`raw=0d2019011c0001800101000000000000000000000000000000000000` |
| 248615–248616 | `assert at infra_wrapper_bb.cpp:870`；函数 send_and_wait_cmp_i |
| 248655–248657 | notify_model_system_error → 原 __assert_fail false → 原 libc Assertion failed |
| 248658 起 | 第一条完整 `-1021` 警告；随后46条完整 -1021 全在 assertion 输出之后 |
| 248708–248724 | uptime315.62、tid327 State T、do_signal_stop → get_signal → do_signal → do_notify_resume |

**需要修正“未收到回复所以超时”的表述。** A `2de7260` 是 `osal_snd_msg`，`2de7264 cbz w0,2de72f4` 仅在发送返回0时进入后续接收；非0分支设置 `w2=0x366`（870），并在 `2de72f0` 调用 lib_assert。接收是之后的 `2de72f4..2de7300`，参数 timeout=-1。所以本次确切静态含义是 **发送返回非0触发870断言**，尚未到接收等待；第二次请求被谁返回了哪一具体错误码，当前日志没有直接捕获。[P `app_libc_blocks.app_send_and_wait_cmp_send_error`；A `2de7260..2de7300`]

U `.text+43cc..43d8` 读取 current 的 flags 并检查 bit0（TIF_SIGPENDING），置返回值 `-0x3fd`（-1021）；其前面的 schedule/schedule_timeout 由 relocation 表确认。这是 pending signal 打断等待的直接实现证据，结合全部完整 -1021 行都发生在 assert 后，更支持它们是异常停线程的副作用，而非先发生的服务故障诱因。U `.text+45a0..45ac` 的另一个等待路径也作同样检查。[P `osal_kernel.blocks`/`relocations`；S 248657–248705]

`-1022` 需独立看待：共有1637条完整警告，其中1636条在原 libc assertion 输出之前，1条在之后；早在系统正常绘制、首次设置交互期间就存在。U `.text+4360..436c` 在 schedule_timeout 返回0时置 `-0x3fe`（-1022），也有空队列/有限等待分支；它本身不能被解读成某个固定服务不可用。[P `timeline.warnings.-1022`/`osal_kernel.blocks`；U `.text+4288`、`.text+436c`]

**目标没有可归因证据。** 通用 `UDIF cdev_ioctl warning ret` 行没有 tid、ioctl op 或 queue ID；不能把所有 -1022 算在 VDF，也不能仅凭相邻行把它们绑定到 tid432。现有 syscall 观测容量有丢弃，尚未直接证明第二次0119发送返回值、是否是模型的一次性处理限制、队列状态或消息所有权错误。[S 248604、248615、248655–248705；P `limitations`]

## 3. tid327 的身份与 harness 排查

tid327 是 **我们的输入 keyworker**。`runtime/helpers/fx3-rm-empty-provider-v7-diag96.c:24–27` 在匹配 im.elf、建立 RM callback 后 `pthread_create(...keyworker...)`；包含文件 `fx3-rm-key-gate-v5-diag96.inc:18` 写出 pid/tid identity，`:15` 记录自身 gettid，`:20` 每轮门控和 usleep(5000)。S 5851 明确记录 `FX3_KEY96_POLL tid=327`，S 6879 则显示原厂同名 THREAD_INFRA1 接收线程实际是 tid258/queue80af6181。未见 keyworker 设置自己的线程名，`THREAD_INFRA1` 是继承 comm 的合理推断；**不能用 comm 将 tid327 当作原厂 infra 队列线程**。[P `source_evidence`/`timeline.keyworker_identity`/`timeline.native_infra_receiver`]

冻结的 host runner `observer-source/run_candidate96.py:300–396` 的 `qmp('stop')` 是暂停虚拟 CPU；`:429–433` 的 killpg 仅向宿主 QEMU 进程组发 SIGTERM/SIGKILL。已审阅的 init 脚本不含 kill/ptrace/stop 信号命令。guest shell 在 AP 停止后继续输出 /proc 采样，与“只冻结同 mm 的 im.elf”吻合；QMP 全机停止本身不会让 guest 调度器继续打印 `do_signal_stop`。[P `source_evidence`；S 248708–248726 及后续 THREAD 采样]

159份投影 ELF 扫描中，appFw 的4处直接 raise 均为 **SIGTRAP(5)**：A `16ea494/16ea4f8/16ea598/16ea5fc`；没有 kill/tgkill/ptrace 导入。其他导入者的直接 kill 包括 libBTUtils 的15、libCertificateManager 的0/9/15、libosal_ulogio 的9、libcurl 的9/15；libminimp 的 pthread_kill 参数是调用者传入，不能静态一概排除。完整清单、上下文及是否名称出现在 serial maps 中见 P `signal_inventory`；这里只排除了已识别直接调用，不声称覆盖间接函数指针、隐藏符号或任意 svc。

## 4. 修正方向和未证实项

建议运行链优先捕获第二次0119 **发送前后返回值**，按这次请求的 src81cf61c4、消息租约与 generation 建立可重复的面板状态事务；只有消费者实际保存本次控制状态后才回本次完成。不要把过去的 src81cf61c1 或一次性成功复用到新请求，也不要跳过870断言或向 im.elf 直接发 SIGCONT 来掩盖原错误。[S 13419 与248604 的 source 差异；A `2de7260..2de72f4`；K `81dcb04..81dcb64`]

当前没有证据需要补造电池、电源、SysCon 或操作超时输入；本次停止与既有明确 assertion 更吻合。未证实的是故障线程当前内核栈、内核实际发送的 siginfo、exception callback 后续卡在哪里，以及导致第二次 osal_snd_msg 非0的具体组件；这些缺口需要由运行链另行观测，本只读审计未操作 VM。[S 248615–248724；P `verdict.confidence`/`limitations`]

本目录交付仅接受静态因果审计与现有日志时序；不构成修复后的运行、可操作菜单或实机验收。
