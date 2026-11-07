# FX6 原厂队列等待的精确观察与离线共享库候选

## RTLD_NEXT、PLT/GOT 与 AArch64 ABI：观察器能否命中原厂接收？

### Takeaway

已将现有自编接收观察器链接为 **AArch64 ET_DYN，5,400 bytes**；绑定已核验的 guest glibc 2.25，`--no-undefined --no-allow-shlib-undefined` 通过。冷 ELF 显示真 FX6 appFw 有 **29 个**直接 BL 到接收 PLT 的调用点，其中观察器命名了 5 个，其余正常归入 `other_appfw`；这只证明可被动态符号解析覆盖的条件，不证明 guest 已命中。[构建收据](observability/build-result.json)；[调用点审计](observability/interposition-result.json)

### Cited Findings

- `RTLD_NEXT` 从当前对象之后继续查找，适合分层 preload wrapper；应先清 `dlerror`，调用后再读错误。它不保证找到的下一层就是最终 Sony 实现；现有观察器会记录解析目标路径/地址，解析失败或指向自己则退出 126，不伪造接收成功。依据 Linux man-pages 6.19 维护者手册，页面标记其材料取于 2026-09-09；代码依据本次源指纹。— [dlsym(3)](https://man7.org/linux/man-pages/man3/dlsym.3.html)；[现有源](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)；[源指纹](observability/build-result.json)
- `LD_PRELOAD` 按给定顺序加载；`RTLD_DEEPBIND`、独立 `dlmopen` namespace 会改变可见查找范围；secure-execution 可忽略 preload。GNU ld 的 `-Bsymbolic/-Bsymbolic-functions` 可将 DSO 内引用绑定到本 DSO 定义。因此 preload 不能保证拦截内部直接 B/BL、hidden/local/protected 绑定或显式 handle 查找。— [ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html)；[dlopen(3)](https://man7.org/linux/man-pages/man3/dlopen.3.html)；[GNU ld Options](https://sourceware.org/binutils/docs/ld/Options.html)
- Arm **AAPCS64 2025Q1，2025-04-07** 规定 x0–x7 传参、x30 为 LR；BL/BLR 写入下一条指令地址，合规 linker veneer 除 x16/x17 和条件码外须保留寄存器。故在原厂 `BL receive@plt` 无额外 wrapper 改写的条件下，观察器入口 LR 应为原厂 call-PC+4，参数为 w0=qid、x1=out-slot、w2=timeout。尾调用则可能保留更上层 LR，不能一概按最近源码函数归因。— [Arm AAPCS64 §6.1.1/6.5](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)
- `__builtin_return_address(0)` 语义是当前函数返回地址；GCC 文档特别说明 AArch64 栈中签名 LR 可与 builtin 返回值不同。本机 clang 21 编译后的自编观察器在第一次 helper BL 之前用 `mov x25,x30` 保存入口 LR，再完成 builtin 所需处理；不依赖调用若干日志函数之后的瞬时 x30。— [GCC Return Address](https://gcc.gnu.org/onlinedocs/gcc/Return-Address.html)；[自编 ELF 审计](observability/interposition-result.json)
- 本次冷文件精确绑定 `appFw.so a1c58b69...`、`libosal_uipc.so fe248d22...`：app 的 `osal_rcv_msg_tmo` 为 undefined/default-visible，PLT=`0xb19ec0`，对应 `R_AARCH64_JUMP_SLOT`；真实库导出位置为 `0x6468`。5 个命名 LR `{0xc0a20c,0x20ef554,0x20ef7cc,0x20efbbc,0x20f80f8}` 均实际存在，另有 24 个调用点。不应把分类表当成全部调用者清单。— [可重跑只读审计](observability/audit_interposition.py)；[29 点结构结果](observability/interposition-result.json)

### Inferences

- 最小下一轮应把观察器放在该进程 preload 查找链前端，并保存真实 loader 查找/绑定信息；可用 `LD_DEBUG=bindings,symbols` 验证 app 的接收符号绑定到哪个 DSO，但这会增加日志和时序扰动。下一层 target 必须结合本轮 `/proc/<pid>/maps` 和库 SHA 判断是否真 `libosal_uipc+0x6468`，不能只看 `RTLD_NEXT` 成功。— [ld.so 的绑定诊断](https://man7.org/linux/man-pages/man8/ld.so.8.html)；[当前解析与日志源](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)
- 对内部直接调用、其他 namespace 或显式真实 handle 的路径，外层 recv preload 没有全面覆盖保证；如果冷 ELF/loader evidence 显示确实绕开，应改用 guest 进程级断点观察真实 `libosal+0x6468` 的入口参数，不能把没有 ENTER 当成没有等待。— [dlopen 查找范围](https://man7.org/linux/man-pages/man3/dlopen.3.html)；[QEMU 用户空间调试建议](https://www.qemu.org/docs/master/system/gdb.html)

### Gaps

- 本轮没有执行 guest loader；没有验证 preload 顺序、真实 GOT 值、重复 wrapper、版本符号实际绑定、日志时序影响或运行中 payload。现有 host fixture 只验证假函数上的转发/errno，不能代替这些结果。— [host fixture](../../reports/2026-11-07-fx6-queue-contract/observer/test_observe_osal_queue.c)；[候选限制](observability/build-result.json)
- 当前 C 源按 `basename=appFw.so` 和 LR 相对偏移分类，不在进程内计算 appFw SHA。**分类名称只有与本轮 appFw SHA、maps、输入 manifest 独立绑定时才成立**；更换文件后必须取消命名归因。— [分类源码](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)；[固定输入审计](observability/interposition-result.json)

## QEMU vCPU、用户线程与 run/socket：怎样得到可靠的 LR/qid？

### Takeaway

QEMU 系统 gdbstub 的 thread 是 CPU，不是 guest Linux TID；观察停在内核等待的 vCPU 或读取 wchan 不能还原该用户线程调用接收时的 LR/qid。官方建议优先在 guest 内用 GDB 或 guest gdbserver 调试用户进程；本项目最小实现可以先用上述进程内、阻塞前记录参数的观察器，再用同一 run 的线程生命周期与 maps 交叉验证。— [QEMU GDB usage](https://www.qemu.org/docs/master/system/gdb.html)；[GNU GDB server](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Server.html)

### Cited Findings

- QEMU master 文档（检索日期 **2026-11-07**）说明系统 gdbstub 按 CPU cluster 暴露 inferiors、按 CPU 暴露 threads；内核抢占和模式切换会干扰用户程序调试，推荐 guest GDB/gdbserver。此 master 文档不是本项目 QEMU 构建版本证明。— [QEMU Debugging user-space / multicore](https://www.qemu.org/docs/master/system/gdb.html)
- 官方支持每个测试采用独立 Unix socket：QEMU 参数示例 `-chardev socket,path=<run-specific>,server=on,wait=off,id=gdb0 -gdb chardev:gdb0`；GDB 9.0 起可 `target remote /absolute/socket`。QMP 和 gdbstub 是不同协议，不能因文件名相近就互连。— [QEMU Using unix sockets](https://www.qemu.org/docs/master/system/gdb.html)
- guest gdbserver 使用进程级调试设施，host GDB负责符号；可调试 stripped 程序，前提是 host 持有匹配二进制/符号与运行库。其 attach/断点会影响目标调度，本轮未执行。— [GNU GDB server](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Server.html)

### Inferences

- run 绑定计划：由运行负责人给出唯一 run-id、冷输入 manifest SHA、实际 argv、QEMU PID/开始时间、run 目录和完整 gdbstub/QMP Unix socket 路径；连接前核对该 PID 的实际 argv 和 socket owner/inode，归档相同 run 的串口、maps、线程 comm/TID、观察日志。只选择明确的 gdbstub socket，不扫描/复用别人的监听端口。该清单是项目集成建议，本轮没有读取任何 live socket或 guest。— [QEMU socket 与 CPU 范围](https://www.qemu.org/docs/master/system/gdb.html)；[候选未运行状态](observability/build-result.json)
- 若使用 guest gdbserver，运行负责人须先证明内核 ptrace/进程身份和调试链可用，再在原厂接收入口观察 `$x30/$w0/$x1/$w2`；若用户态观察器命中，则其 ENTER 在真实 wait 之前记录 LR/qid，适合避免“已睡眠后找寄存器”的混淆。— [GNU GDB server](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Server.html)；[Arm 参数与 LR](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)；[观察器源](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)
- 集成还应在前/中/后时点保存 task 数、每个 TID 的 comm/wchan，以及原厂 UI worker 的真正进入/返回证据；异步启动函数返回不能代替 worker 生命周期。父线程提供的新候选观察指出：295 未采到 293 的 TID 225，只有 217 的 hrtimer_nanosleep 和 220–222 的 futex。**此条为协调者转交的待绑定运行证据，本分支未独立读取原始日志**，只据此增加验收要求，不在这里重复发布其运行结论。
- 无 ENTER 可能来自 worker 未进入/已退出、查找绕行、错误 PID/run、源日志上限（当前最多 1024 次 ENTER）、未成功装载等情况，不能推导“未调用”或“死锁消失”。本轮不扩展 pthread hook。— [观察器上限与失败路径](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)

### Gaps

- 尚无本轮 guest 的真实 TID、LR、qid、发送者或队列生命周期收据；任何根因结论均须等待唯一运行负责人采集。本分支未连接 VM，也未建立 gdbserver。

## 本机工具链、guest glibc 闭包与可审阅 ET_DYN 候选

### Takeaway

无需安装或下载工具。已复用 **Apple clang 21.0.0 + 项目现有 Zig 0.17.0 内置 LLD 22.1.8**，完成 guest 共享库离线链接；输入仅为自编源码和已存在 guest glibc 的动态链接描述，未将原厂闭源 payload 打入输出。二进制全在 ignored `work/`；未打包 CPIO、未加载或运行。— [完整命令/指纹/验证](observability/build-result.json)；[构建脚本](observability/build_shared_observer.py)

### Cited Findings

- LLD 官方文档说明它是跨目标 linker，支持 AArch64 ELF；官网本次展示 **24.0.0git**，本机实际版本以执行结果 **22.1.8** 为准。GNU `--no-undefined` 检查 regular object 未解析引用，`--no-allow-shlib-undefined` 检查输入 DSO 的未解析引用。本候选两者同时启用，没有为了通过而放宽。— [LLD 官方说明](https://lld.llvm.org/)；[GNU ld 未定义检查](https://sourceware.org/binutils/docs/ld/Options.html)；[本机构建结果](observability/build-result.json)
- 不能仅凭“glibc 2.25”认同一个运行库。只读解析 Candidate 293 CPIO，核验其中 `libc-2.25.so f9104526...`、`libdl-2.25.so 6dde01ab...`、`ld-2.25.so 90b4fe73...` 与现有 `menu-repair-01/runtime/guest-sdk/lib` 完全一致；真 FX6 原生 initrd 同名库 SHA 不同。本候选绑定前者，**不是宣称适配任意 2.25**。— [CPIO/SDK 指纹与闭包](observability/build-result.json)
- **295 集成范围补核（仅冷输入）**：已分别读取 293/295 manifest、校验它们声明的 CPIO bytes/SHA，再对 CPIO 内 libc/libdl/loader/libosal_uipc 四件直接计算成员 bytes/SHA；四件全部一致。295 manifest SHA=`fd945eaa7ba97f297f0a8073f0072416add4fb0af480efe8e28e6b5d76c9dcef`，其 CPIO SHA=`f46acb182a87b4aaf541166d416ca347a5820e6c9eef80c51a58a03139618489`。293 manifest SHA=`b823079391cdc92eb2530f83c080df108b9b64dc1aaa0f567f807cfa84f57b44`，CPIO SHA=`2a527baedbf9b2873300cb19bc43230e17655cb2ef785ea2319ed16985d66e2c`。因此本候选针对 293 的这四个 provider 文件约束，可以用于已固定的 295 冷基线；**未推广为 295 live 装载、符号查找或线程状态已验证**。— [完整四成员比较收据](observability/baseline-closure-comparison.json)
- 最终文件 `libfx6-queue-observer.so`：**5,400 bytes，SHA-256 `8e7f71167bb1619f933df622d5f41b6cb1b8439a6ea6b5b9d7bed2ac9ff016fc`**；AArch64 `ET_DYN`，唯一导出 `osal_rcv_msg_tmo`；8 个动态导入均由被固定的 libc/libdl 解析，版本要求仅 **GLIBC_2.17**。`DT_NEEDED={libc.so.6,libdl.so.2}`，二者的传递闭包包含 `ld-linux-aarch64.so.1`。无额外 atomic/compiler-runtime 导入、无 init/fini-array、无可执行栈。— [离线 ELF 验收](observability/build-result.json)
- 原始观察器源 SHA `eb202750d7b863c2608318ff2c577c73855933c9ea72414e94b609b44e65bd31`；本轮不改其转发逻辑。源码保留 qid/out-slot/timeout、返回值和 errno，不读写 payload；但新增计时、符号解析和日志必然有成本，因此只称诊断候选。— [自编源](../../reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)；[构建源指纹](observability/build-result.json)

### Inferences

- 可审阅二进制位置：`work/parallel-research-20261107/online-observability/libfx6-queue-observer.so`。复跑：`python3 -B 'research_notes/FX6 原厂启动 在线交叉验证/observability/build_shared_observer.py'`；脚本带外盘 UUID 守卫，只向 ignored work 写构建产物，冷读 CPIO核对库指纹。再运行同目录 `audit_interposition.py` 可复核 PLT覆盖和入口 LR 保存。— [构建脚本](observability/build_shared_observer.py)；[冷输入审计脚本](observability/audit_interposition.py)

### Gaps

- linked/undefined 检查成功仍不是 Sony guest 动态加载、实际ABI、拦截覆盖、线程存活或首帧验收；当前 manifest 明确 `guest_loaded=false / guest_executed=false / cpio_changed=false`。下一轮如更换 CPIO库集必须重核 SHA/版本闭包。— [候选状态与限制](observability/build-result.json)
- 295 的四件冷 provider 文件与 293 一致已单独核清；若实际采用的 manifest/CPIO 不是上述 SHA，仍须重新做此比较。即便 SHA 相同，集成 preflight 仍需核实际 guest 的 maps/provider 路径、LD_PRELOAD 顺序和运行身份。— [295 冷输入适用边界](observability/baseline-closure-comparison.json)
