# FX6 一次性等待快照候选

已构建独立候选。它从已封存的 observer-only295 派生，只更改 init 的一次性调用并增加一个 helper；本构建子任务未启动或连接 VM。主 agent 的后续运行记录另行封存。

- 入口：[candidate-manifest.json](candidate-manifest.json)，schema `fx6-wait-snapshot-candidate-v1`，状态 `PREPARED_WAIT_SNAPSHOT`。
- manifest SHA256：`df39ee856ea9c667d786920c0ec9c12b43992fbc17525870cbd53b38f5c8da42`。
- CPIO SHA256：`453890e36e7e6b4cd66641707cf80bd7754a0a37d6fba8dfce2af55fc169c926`。
- helper 54312B SHA256：`8a2739ad9d826a2074af8e0c6b09a6233a1465a491f415b68f53346082c53f57`。

## 行为与边界

既有 3 秒诊断循环第一次读到 guest uptime≥20s 时，同步执行 helper 一次，通常在20–23s附近，实际受原线程日志输出耗时影响。init 原初始化、模型、Backup、NOP、队列观察器、键序列和120秒预算均沿用原候选。

helper 先输出 maps，再枚举指定 appfw PID 当时全部现存TID（最多512，溢出明确标记）。每个TID先输出未停止状态下的 comm、syscall；再验证Tgid身份，依次执行 SEIZE、INTERRUPT、限时等待、GETREGSET、受限FP链读取、DETACH。每次只暂停一个线程，新增线程不自动追踪。

寄存器记录包含 PC、LR、SP、x29、x0–x8、PSTATE。FP最多20帧，只对该TID的SP所在可读写匿名或 `[stack]` VMA读取；FP须16字节对齐、不低于SP、在同一映射中、两word不能跨页，下一FP须递增并检查环。每次PEEKDATA先清errno，返回-1且errno0视为合法word。不会解引用业务对象指针或读取Sony堆对象。

每TID正常等停上限200ms，清理另给250ms；全程alarm6s，触发后1s为硬清理期限。每个成功SEIZE的活TID均走DETACH尝试，非预期信号停止保留原信号。DETACH失败会明确记录并结束helper；不设置EXITKILL，Linux tracer退出会解除剩余附加。内核不可响应等异常无法声称每次DETACH必成功，日志会区分显式分离和退出兜底。

**诊断干扰**：ptrace会暂停线程，可能改变线程调度、系统调用时序与等待结果，不能当作完全无侵入观察。未使用PTRACE_SET/POKE、fork/clone/exec或物理硬件操作。

## 冷核验

- [member-diff-verification.json](member-diff-verification.json)：原1226条记录变为1227，包含两个原TRAILER；两个TRAILER及所有非init旧记录逐字节相同，原顺序保持。只更改init，新增 `usr/bin/fx6-wait-snapshot`。
- [abi-closure-verification.json](abi-closure-verification.json)：helper为AArch64 ET_EXEC，解释器原样；仅依赖libc.so.6，版本需求仅GLIBC_2.17。对实际295的libc/ld2.25递归闭包核对41个强导入，全部满足。
- [build-receipt.json](build-receipt.json)：对象由固定Zig编译，最终直接链接实际SDK2.25的libc/ld，并使用 `--no-undefined --no-allow-shlib-undefined`；未混入默认新glibc。
- [host-test-receipt.json](host-test-receipt.json)：18次mock用例执行（含两次正常路径重复），覆盖权限失败、等停超时、寄存器失败/短缓冲、PEEK errno、原信号保留、分离失败、身份竞态、取消与20帧边界。没有对host实际执行ptrace。
- [init-only.diff](init-only.diff)：唯一init变化；shell语法检查通过。

[Linux v4.9 AArch64 UAPI](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/include/uapi/asm/ptrace.h) 定义272字节通用寄存器结构，[v4.9 regset实现](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/kernel/ptrace.c) 将其绑定到NT_PRSTATUS。[ptrace维护者手册](https://man7.org/linux/man-pages/man2/ptrace.2.html) 说明SEIZE、INTERRUPT、等停及分离协议。实际Sony内核字符串为4.9.337-scel+且包含ptrace实现痕迹，支持本ABI选择；Sony权限与vendor差异仍需guest返回值确认，不能由冷核验代替。详见 [kernel-abi-review.json](kernel-abi-review.json)。

FP链布局依据 [Arm AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)，当前代码可能省略frame pointer，因此短链不等于没有上层调用。PC/LR需结合maps和原ELF PT_LOAD换算文件位置，不能把VA直接作为file offset。[guest glibc2.25 startup](https://github.com/bminor/glibc/blob/glibc-2.25/sysdeps/aarch64/start.S) 支持entry参数交接契约。

## 源码与复现

源码：[wait_snapshot.c](wait_snapshot.c)、[snapshot_core.c](snapshot_core.c)、[snapshot_core.h](snapshot_core.h)、[entry.S](entry.S)、[test_snapshot_core.c](test_snapshot_core.c)、[build_candidate.py](build_candidate.py)。正式报告只保存源码和JSON凭据；binary、CPIO、对象和cache保留于忽略的 `work/fx6-wait-snapshot-20261107/`。

离线重建命令：

```sh
python3 -B work/fx6-wait-snapshot-20261107/build_candidate.py
```

只能在没有使用该候选的运行时重建，命令会覆盖本工作目录产物并更新时间戳及manifest SHA。正式报告中的builder是原样来源快照，按原work目录布局运行；绝对工具链、SDK与父候选路径见receipt。builder不启动VM。

寄存器/帧日志prefix为 `FX6_WAIT_SNAPSHOT_REG` / `FX6_WAIT_SNAPSHOT_FRAME`；maps、comm、syscall均有BEGIN/END或FAIL标记。SEIZE/INTERRUPT/STOP/DETACH与最终统计明确记录；只有guest日志能证明这次快照实际执行。
