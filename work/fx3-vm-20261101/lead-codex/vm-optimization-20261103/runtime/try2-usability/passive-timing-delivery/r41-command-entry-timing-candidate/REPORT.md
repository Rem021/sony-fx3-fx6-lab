# r41｜command 入口计时离线候选

**最小源码、宿主验证和 AArch64 构建完成；未运行 VM/guest、未部署，未证明性能改善。** 仅写本 r41 目录。FX6 被拒实现未重试、未转交；固定 FX3 平台、180秒/20秒、PAGE/server、独立 pin/confirm 和退出政策未改。

## 实际绑定与改动

从实际 `fx3-gpe-observe-v26-perf.c`（SHA `06f6d2968f55b2579b950df2a4954f3976fa9f624a5c6a987e27b253b475e1f9`）派生，只改变该文件与 `fx3-complete104-observe-v1.h`，完整差分见 `source.diff`。backend-v9、cache/resource/texture 等已有优化继续原样使用，未重新引入为新优化。

r36 CPIO 的实际 `simulation/fx3-gpe-observe-v7.so` 位于 451447396，276984B，直接按 source-index/header 读取的 SHA 与实际 helper 相同：`30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`。现有配方重建的基线全部21个 ALLOC 节的地址、尺寸、内容及全部 PHDR 与实际成员一致；raw SHA 不同仅在非 ALLOC debug_info/debug_str/debug_line/static symtab，debug_str 可见编译目录差异。未将 raw 哈希说成一致。见 `BINDING.json`、`SOURCE-ELF-REVIEW.json`。

`command()` 的首个 C 语句保存进入 errno、调用一次原 `gpe102_now()`（guest CLOCK_MONOTONIC=1）、恢复 errno；入口值仅为自动局部量。正常 done 和 `gpe102_take` 失败早返回均将它传给原静态返回观测 helper；只在原行末追加 ` entry_ns=%lu`。原 tid/tpidr/ns/seq/op/source/result/errno 字段、旧 ns 表达式及其前置调用顺序不变，原返回后 errno 恢复保留。clock 失败/返回0输出 entry_ns=0，由离线解析明确判 unknown，不改变 command 返回或重试。

无新 BSS/TLS/物理区/映射/锁/线程/定时器/日志调用点；不使用 profile104-v2。逆向消除这四处必要差分后两份文件与原件逐字节一致，draw、资源/生命周期验证、回调/SendDrawComp 和失败决策不变。实际目标反汇编可见首个 pread 前恰好新增1次 clock、errno 保存恢复、入口值保存在 sp+0xf0。现有 stack frame 66864B 不变，`.bss=569208`、`.tbss=44`、`.data=16` 不变，无新增 data/TLS symbol 或动态导入；`.text +56B`、`.rodata +16B`。这是编译和 host 证据，不声称 guest 时序零扰动。

## 测量含义与解析

`end_ns-entry_ns` 是**适配器入口采样到原返回标记采样的 elapsed time**，包含适配器内锁等待、验证、绘图、callback/完成调用、调度等；不含进入适配器前原 FIFO 排队，不是 CPU 时间。函数 prologue/取 errno 位于入口采样前；原返回 ns 在 tid/tpidr 取样后、同一 dprintf 的参数计算处取得，实际格式化/串口打印和返回发生更晚。

独立 `parse_command_timing.py` 仅离线读取一个显式 run 的完整 LF/CRLF 记录。按 tid/tpidr/seq/op、字段范围及原完整前缀检查；缺 entry、0、end<entry、重复/冲突、截断、混入其他记录或范围异常均输出 unknown/None，不变成0耗时。同一线程、连续 seq、两端完整且有序才算前 return→后 entry；跨线程、序列缺口、重叠或破损边界不相减。该间隔仍可能含日志尾部/原 Main/调度或未观察活动，不能称为纯 FIFO 等待或空闲。无 guest↔host 换算。

实际 r38 全历史 serial（包括 cleanup，仅兼容回放，不当 End cutoff）共391条：346 missing_entry、45 malformed/interleaved，**known duration=0、known gap=0**。没有用新字段补造旧数据或将 r38 改判。`R38-COMPATIBILITY.json` 保留原偏移与未知原因。

## 有界验证与成本

- `HOST-TESTS.json`：同一实际全 v26 源/真实 backend 的两个 host 可执行文件，IO/native/clock 均为显式 mock。5组成对场景为成功 callback+SendDrawComp、g/c 拒绝、take失败早返回、入口 clock 失败、入口 clock 零值；原 effects 顺序、调用数、rc/errno、独立16bpp像素预期和 CMD_RETURN 原前缀完全一致。每 command 恰好多1次 clock、0次新日志；第一项 pread 仍见进入 errno=17。原 callback→status 顺序及次数不变。
- `PARSER-TESTS.json`：18组正反例、按1/2/7/31/4096B chunk 回放、截止/不同run不拼接、不同线程不相减、实际候选 host 行和旧 r38 均通过。
- `COST.json`：每 command 最多新增30 ASCII字符（` entry_ns=`+20位 uint64）。有限 host 测量是实际旧/新返回 helper、真实 host clock、vsnprintf sink，3×20000次；中位数约346.15→755.65 ns，差409.5 ns。原始三组值均保留，波动明显；不是 QEMU、CPU或串口开销估计，不据此承诺性能。未新增 dprintf 调用点不等于底层 write 次数/时序零变化。

准备阶段的路径筛选错误、首版 fixture 将 fmt0 错当32bpp的断言失败、旧日志路径解析错误、cwd-only raw重建哈希不符及 objcopy 不支持均保留原证据；最终通过项以当前 JSON/源码冻结为准。没有重跑1398项历史输入或旧大矩阵，未复制 runtime/CPIO/DTB。

## ELF 与固定槽

未 strip 候选 `build/gpe-r41-candidate.so` 为277704B，较原276984B槽超720B，**不能直接装入原槽**。一次 `zig objcopy --strip-debug` 返回 `error: unimplemented`，stderr及空失败输出已保留，没有把它当有效ELF。

依协调 msg_137d3fb55434，复用 r36 已验证的链接期方式：相同候选编译命令仅增加 `-Wl,--strip-debug` 并改输出，得到 `build/gpe-r41-fixed-slot.so`：**129600B，SHA `19ca7deaf570eeb68fda0036bb75dec740ab30f404f9f91bd208fd3d53c06a39`**，原槽剩余147384B。全部 ALLOC 内容/布局/链接、PHDR、动态依赖/导出与未 strip 候选等价；所有 program segment 只允许 ELF 头 e_shoff/e_shnum/e_shstrndx 的节表元数据字节变化，实际偏移40/41/42/60/62。依赖仍仅 libc.so.6/libdl.so.2。见 `SLOT-ELF-REVIEW.json`。保留未 strip 原件；未填槽、未重打 CPIO、未接入 runner，尺寸合格不等于运行包准入。

## 输入、交付与后续

`INPUTS-BEFORE.json` 是最初33项技术输入快照；旧 serial 的 `ADDITIONAL-INPUTS-BEFORE.json` **在首次实际读取后生成，是首次观测 pin，不是读取前快照**。编译器报告的49个实际解析依赖与额外工具在 `DEPENDENCY-BINDING.json`，也是随后观测 pin；链接 strip 引用另有首次观测 pin。结束时只核这些实际用到的材料，不继承历史1398项；具体去重数量和匹配见 `INPUTS-AFTER.json`。共享 README 非冻结输入。编译缓存明确排除交付 SHA，其他源码/ELF/回执完整冻结。

下一次测量前须先独立审查新隔离包及实际成员/runner绑定，保留固定平台与独立看图、pin/confirm/20秒，取得当前run/library/线程身份及原 End 截止再解析；详见 `NEXT-MEASUREMENT.md`。本轮只具备可供后续测量的离线观测候选；没有新性能数据、菜单通过或 FX6 开机证据。

接口依据：[Linux man-pages clock_gettime](https://man7.org/linux/man-pages/man3/clock_gettime.3.html)：MONOTONIC 是经过时间域，区别于 thread/process CPU clock，失败可设置 errno；本任务显式恢复 errno。Open Group页面403未用作证据，实际目标 clock id 与类型仍以绑定源码/反汇编为准。
