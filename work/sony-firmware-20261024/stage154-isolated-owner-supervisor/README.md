# FX3：隔离工作进程、在途观察和停止请求（仍未放行真机）

2026-10-28。**实现并验证了模拟提供者的独立进程监管：超时不强杀、不重启，停止请求等待在途调用返回后才进入清理。** 实际IOKit库仍只编译未加载；真实/管理员执行入口、独立驱动归还验收尚未完成，没有新增相机、USB、Windows、UU、驱动或权限操作。

前一轮153的原生候选、33项离线检查是进展。本轮保留该封存原件，派生ABI2候选；原MAIN 1920×1080、30000/1001、HEVC42010约16Mbps、同机完整健康恢复及独立救援等16项要求不变。

## 可审核的新实现

- [owner_core.c](owner_core.c) / [owner_trial.h](owner_trial.h)：增加独立的停止控制块与原子在途阶段。停止只阻止后续工作步骤，清理仍单次执行；不能取消正在运行的系统调用。
- [owner_ipc.c](owner_ipc.c)：无设备API的共享内存原子读写。SIGINT／SIGTERM／SIGHUP只写停止标志，使用锁自由原子对象；工作进程保持映射有效直到退出。
- [owner_supervisor.py](owner_supervisor.py)：保留实际Popen句柄。超时只设置停止标志，轮询同一进程；不调用kill、terminate或自动重开。每个任务在创建子进程前消耗单次记录。
- [owner_worker.py](owner_worker.py)：当前**只接受自写fixture**。核对构建/DSO/共享块身份，调用后写回执；即使已出现“原生函数返回”记录，监管器也要等进程真正退出并校验最终回执。
- [shared_job.py](shared_job.py)：共享块身份、布局、私有文件权限及原子操作。不会加载真实IOKit候选。

两个ABI2库均已编译，来源、参数、依赖、SHA见 [构建回执](build-receipt.json)。自写fixture DSO只依赖libSystem；真实IOKit库没有被加载。阶段153的真实绑定仍被拒绝，本阶段也没有live worker或提权器，授权标志即使被模拟为通过，也不会产生真实子进程。

## 两项实际Mac问题及修正

**跨语言时钟不能混用。** 本机Python3.14的 `time.monotonic_ns()` 使用mach_absolute_time；C候选使用CLOCK_MONOTONIC。当时实测两者相差约4.54秒，导致父进程认为期限已到时，C侧仍可能认为还有时间。现在配置、监管器比较和C提供者全部采用明确的CLOCK_MONOTONIC纳秒，不硬编码差值。测试内部的相对等待不跨ABI，继续使用Python自身单调计时。[本机测量](clock-domain-diagnostic.json)、[Python官方说明](https://docs.python.org/3.14/library/time.html#time.monotonic)。

**Python启动时会换用Framework入口。** 实际Popen句柄仍在、PID与启动时间相同，但ps中的可执行路径从venv变成Framework Python。恢复观察不再比较整行命令完全相等；它核对启动时间、启动时生成的解释器路径白名单、固定worker/任务路径和随机nonce。未匹配或暂时无法读取时保持UNKNOWN，不重新启动。[诊断原件](interpreter-identity-diagnostic.json)。

两项失败版本及对应源码、任务记录、DSO均保存在 `attempt-interpreter-reexec`、`attempt-clock-domain-review`。C回归适配曾把已合法的ABI2继续当作非法值，修正后的负例为ABI3，旧测试保存在 `attempt-regression-ABI-value`。没有改写已封存153或删除旧回执。

## 实际运行的离线验收

[进程测试](run-process-tests/results.json) 共14项断言组、9个真实创建的**非IOKit测试进程**，已全部终止：

| 情况 | 观测与处理 |
| --- | --- |
| 正常完成 | 进程退出、nonce/构建/结果哈希及回执都一致后，才报告提供者观察完成 |
| 在capture夹具内阻塞后请求停止 | 实际Popen仍在、在途阶段为4；请求不会让它假装退出。明确释放夹具后，只清理，不继续reopen/claim |
| 整体期限已过但原生调用仍阻塞 | 同一Popen仍确认存活，停止标志为1；不杀、不重启。调用返回后执行单次归还/关闭，缺少期限内最终观察则保持UNKNOWN |
| SIGTERM | 只设置协作停止，阻塞调用仍在；返回后清理，进程正常退出。没有将信号解释为内核I/O取消 |
| C已返回但worker仍在写回执前等待 | 仍报告进程运行，不把原生返回记录当作进程退出 |
| 退出0但无回执／nonce错误 | 都保持UNKNOWN |
| 临时Popen/ps观察失败 | 保留同一任务；之后重新核对原句柄/进程身份，不启动第二个worker |
| 故意终止自写fixture进程 | 在途阶段仍为4、无有效终态回执；保持UNKNOWN，单次凭据仍消耗 |
| 当前真实权限／模拟权限通过 | 均在创建真实任务或查询真实库前拒绝 |

测试中唯一的强杀是对已经确认不链接IOKit的自写fixture进行故障注入；生产监管模块没有这类调用。源码检查在 [本地复核](local-source-and-lifetime-review.json)。

另将153的C核心检查适配到ABI2，加上提前停止和错误Control ABI两项，**35项通过**，见 [C回归回执](run-core-regression/results.json)。它验证C流程/ABI，不验证真实IOKit调用或相机。共享映射使用MAP_SHARED/写穿方式，进程状态依赖实际Popen/ps，而非单靠状态文件。[Python进程文档](https://docs.python.org/3/library/subprocess.html)、[共享映射文档](https://docs.python.org/3/library/mmap.html)。

## 对“完成”的分层

本轮区分：主机函数是否返回、worker是否退出、提供者是否给出一致的缓存观察。三者都不能单独证明真实MSC驱动回归、相机线程结束、服务认证、健康备份/恢复、目标HEVC文件或救砖。

`observe_recorded()` 的恢复能力只覆盖确认既有fixture进程的当前身份；尚不是经过验收的管理员会话重接、真实驱动观察或实机接管恢复工具。worker意外消失、回执缺失、时钟/身份不明时不自动清理其它新句柄、不重置USB、不重用授权。

## 下一步与实际权限

继续补齐真实IOKit worker/管理员一次性入口、固定物理试验凭据、前后独立缓存采集与归还判据，并审查全部相机卷的卸载/重挂载竞态。只有形成具体可审阅方案，再请求对应的新user-client、显式Seize、capture/release及驱动操作授权。当前不执行sudo、卸载卷或原生接管，也不复用已经消耗的描述符授权。

H.265演示的原片和具体补丁仍未取得。完整主录与对应恢复流程没有实机验收，目标保持进行中，没有可试刷包。
