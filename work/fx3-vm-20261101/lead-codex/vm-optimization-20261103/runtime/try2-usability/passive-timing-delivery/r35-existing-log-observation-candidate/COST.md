# r35 成本与上界

这里测的是 Apple Silicon/macOS 宿主，真实宿主 getpid syscall，原 native、claim、mmap、worker 为受控 mock；不是 AArch64 Linux/MTTCG 的时延保证。wrapper interval 包括测量 clock 的开销，fixture 重置在计时区间外；稳态不重置 collector。摘要成本含真实候选 formatter 与原选中 UI block，另用真实宿主 vdprintf 到 /dev/null 测输出调用。没有据此推断实际 glibc dprintf 的 write/syscall/malloc 次数不变；没有“零扰动”声明。

## 新增调用累计

| 路径（新增部分） | getpid syscall 上界 | 新 clock | 普通32位 atomic 上界（含load/store/CAS） | 新64位atomic/UC RMW |
|---|---:|---:|---:|---:|
| pub begin | 1 | 0 | 3 | 0 |
| pub end，非零token | 1 | 0 | 4 | 0 |
| bind begin | 1 | 0 | 3 | 0 |
| bind end，非零token | 1 | 0 | 4 | 0 |
| 完整首次 send wrapper，包括它原 observe 调用的首次 bind | **4** | **0** | **14**（保守累计） | 0 |
| snapshot | 1 | 0 | 4 | 0 |
| 原选中 UI callback，含它调用的 snapshot | **2** | **0** | **7**（3+4） | 0 |

正常首次完成点无重复异常分支时普通原子累计12；14是逐点保守界。token0完成入口不查询；外来TGID在一个查询及owner load后拒绝、无写入。每个观测点均≤4次普通32位原子，无64位原子；weak CAS 一个尝试，失败不循环等待，原有 own_lock/peak 等旧循环不被伪称删除。原有日志/锁/快照原成本不包含在“新增”列，却包含在相应完整路径测量中。每个原本的递归 wrapper invocation 单独计算，未声称整个固件所有嵌套调用只花4次查询。

阶段完成后仍有成本：pub_begin 即使 phase2 也查询/claim后返回token0；若原 observe 再次尝试失败的 bind，bind_begin 同样查询/claim。因此 claim-failure 稳态新增2次，总getpid从原1变3。bind已ready且不进入原 bind 时，稳态新增1次。UI摘要用尽后目前仍执行2次getpid与snapshot，只抑制额外字节。未借收尾擅自优化这些路径。

两 helper 初始化合计新增2次clock、2次getpid和1次UI dlsym；仅构造阶段，失败未知，不做热路径解析/分配。最终不再注册atfork。原 hsend rc/errno 的恢复和原 native call 次数在实际 wrapper fixture 逐案对照。

## 宿主测量

三个样本，每样本20,000次 wrapper。单位ns/完整wrapper，不能外推 guest。

| 路径 | 范围 | 中位数 |
|---|---:|---:|
| baseline first/claim-failure | 145.25–147.70 | 145.40 |
| baseline completed steady/claim-failure | 143.50–145.65 | 144.00 |
| candidate first/claim-failure | 535.70–543.60 | 542.90 |
| candidate completed steady/claim-failure | 342.95–345.50 | 343.10 |

HOST-COST.json 保留全部三组原始输出和 argv；首次原1 vs 候选5个getpid，完成后原1 vs候选3个getpid，已实际计数。

UI单次有界测量（100,000次，原结果原样列出）：

```text
SELECTED count=51 tid_calls=51 diagnostic_getpid=0 original_clock=51 chars=9224
BENCH steady_suppressed_ns_per_callback=477.26 iterations=100000
BENCH actual_host_getpid_syscall_ns=99.82 iterations=100000 last=70128
BENCH actual_host_vdprintf_devnull_ns_per_callback=1389.37 iterations=100000 underlying_write_syscall_count_not_inferred=1
SELECTED count=51 tid_calls=51 diagnostic_getpid=102 original_clock=51 chars=9408
BENCH steady_suppressed_ns_per_callback=690.98 iterations=100000
BENCH forced_fixture_export_ns_per_callback=836.83 iterations=100000 fixture_resets_not_runtime_API=1
BENCH actual_host_getpid_syscall_ns=96.76 iterations=100000 last=70134
BENCH actual_host_vdprintf_devnull_ns_per_callback=1613.55 iterations=100000 underlying_write_syscall_count_not_inferred=1
BENCH actual_host_vdprintf_devnull_forced_export_ns_per_callback=1728.40 iterations=100000 fixture_resets_only=1
BENCH exhausted_budget_actual_host_vdprintf_ns_per_callback=1582.66 iterations=100000 diagnostic_getpid_per_callback=2 no_collector_or_budget_reset=1

```

单次forced-export测量由fixture重置obligation强制走最坏格式化路径，绝不是运行API或实际运行输出率。实际seven-record测试不重置预算，原UI条件在n1..1001中仍51次clock/gettid/dprintf；去掉后缀后所有原字段逐字节一致。真实格式化与输出字节成本大于0，host微基准受调度/缓存影响；更快的一个样本不构成负开销。

## 字节与内存

- 固定后缀184B；一条完整原日志调用没有增加额外换行。整轮最多7条=1288B，原正式2048B上限不放宽。七个独立单调obligation（含两阶段各自entry/return）保证每次至少消费一位，bind-first不遮蔽publication。
- BSS collector record 88B，owner/lock/loss各4B，合计100B（另有链接对齐）；UI exporter/identity/budget等仅普通 BSS。没有新的 physical reserve/mmap/probe。
- 每个formatter执行固定上界的84个FNV字节、176个hex字符和7字节前缀+结尾，不存在重试等待。原dprintf的内部缓冲/内核输出时序仍需目标运行评审。
- 调试ELF当前 UI72656B、OSD119544B；超过原slot UI58856B、OSD109000B。**未集成、不可直接换入固定CPIO**；后续单独release打包/两成员差分及固定runner绑定，不在本任务实施。
