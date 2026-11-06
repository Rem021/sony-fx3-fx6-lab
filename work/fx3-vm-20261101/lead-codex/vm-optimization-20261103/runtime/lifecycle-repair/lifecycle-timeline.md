# AP105 save1800 生命周期定向诊断（2026-11-03）

## 来源与时间域

输入是已结束运行 `../runs/vmopt-20261103-save1800-836febd8/serial.log`，SHA256 `54dd1237d678dfd5aa2cd03d0b087a5a45a438d69ab63c7365c587a6272270ec`。以下 `ns` 是 guest 用户态 observer 的 `CLOCK_MONOTONIC`，内核 printk `[38320.919593]` 是独立内核域，host QMP 时间是第三域；只在各自域内相减，不互相换算。串口多线程字节会交错，行序只能辅助归属，同线程 event/sequence 优先。

`FX3_GPE104_*` 来自注入的 GPE observer/adapter，`FX3_OSD_LIFE_*` 和 `FX3_OSD_ALLOC_DEADLINE*` 来自注入的 `fx3-osd-lifetime-v2.c`，`FX3_OSD_HEADLESS_*` 来自项目 headless adapter，`free_dynamic_msgq_id` 是原内核 `osal_uipc` printk。旧 `../vmopt-20261103-save1800-report.md` 第19行把 OSD deadline 叫作“original”，此处更正为**注入诊断**；runner 仅将该 marker 当停机门，不是 marker 生产者。

## GPE QID `0x808261c0` 的这一次代次

| 原串口行 | guest 用户 `ns` 或内核 printk | 线程 | 事件 |
|---:|---:|---:|---|
| 607292 | 1220214193008 | GPE Main tid274 | `osal_dynamic_id(0x2a,module=0x82)` 返回 QID `0x808261c0`，event1439，result0 |
| 608050 | 1225848214000 | adapter tid275 | seq7545 `SendDrawComp` 进入；距分配返回 5634.021ms，这是**上界**，不是原生 `ReceiveDrawComp` 的直接耗时 |
| 608051 | 1225865192000 | adapter tid275 | 原 `SendDrawComp` 返回1、errno0；上界 5650.999ms，调用自身 16.978ms |
| 608054 | 1225870836000 | adapter tid275 | Flush seq7545 返回0，仍无原 Main 消费确认 |
| 608060 | 1225919092000 | GPE Main tid274 | `osal_dynamic_id(0x4a,QID)` 释放进入，event1441 |
| 608068 | `[38320.919593]` | 原内核 | `**UIPC ERROR** free_dynamic_msgq_id: QID[808261c0] M=1 C=0 S=0 A=1`，发生于释放调用内；`M/C/S/A` 内部字段语义未经原内核源码证实，不能把 `M=1` 直接命名为消息个数 |
| 608084 | 1226152875008 | GPE Main tid274 | 外层 `osal_dynamic_id` 返回 result0、errno1022；外层返回0并不消除内核内部错误，也不能凭 errno 单独判错 |

原串口在释放附近还出现原内核 `UDIF: cdev_ioctl() ... uipc: warning ret = -1022`；它是内核返回的负错误码，而注入用户态 wrapper 记录的 `errno=1022` 是正 errno，两个记录不直接当成同一函数返回。内核 free 的直接返回值没有单独拦截，故精确传播路径 unknown。

同 QID 在 1421/1423 等更早 event 代次曾正常完成/释放；本表按 1439→1441 单代次配对。AP104 另一次同 QID 的原 `ReceiveDrawComp` 5000ms budget 到期后，释放 return `355389662000ns`，首个零状态完成尝试才在 `400101364000ns`，相隔 44.712s，内核报 unfetched；见 `menu-repair-01/runtime/ap104-unfetched-source-timeline-v1.json`。AP105 这次完成先于释放 enter，不能把 AP104 的“释放后才完成”顺序照搬。AP105 的 5.651s 上界超过原 5000ms，原 `ReceiveDrawComp` 入口/返回未直接拦截，不能证明其实际超时；但它是释放错误前首个可测超预算风险。外层 452 组 completed/released 是 API 配对/返回计数，其中一组内部内核释放报错，故两类记录并不矛盾。

seq6329 同源上界 5021.873ms，seq7545 为 5650.999ms；二者各自完成函数仅 36.112/16.978ms。`host/save1800-analysis/intervals.json` 表明两段主要在完成调用进入前，50余个命令和线程交错；本地 host 全历史 regex/串口重读实测耗时显著，但既有 host/QMP 与 guest 时钟无精确对齐，不能断言它单独导致 kernel free。新 runner 仅针对可复现 host 工作量降负载，保留相同 guest 原 5000ms 和所有错误门，并记录分段 host monotonic 供运行后比较。

## OSD allocation 诊断的实际根因

原串口 671771 附近：`FX3_OSD_LIFE_ALLOC_BEGIN sequence=21328 tid=838 destination=0x8288076c bytes=8 wait=1 op=6008 native_caller=0x149f4`；随后的注入 watcher 在 671772 报 `age_ns=2026011008`，671773 记录 blocked tid838。`/proc/self/task/838/stack` 在 671780—671790 是 `tty_write/redirected_tty_write/SyS_write`，用户帧 671795 是 `/simulation/fx3-osd-headless-v5.so+0x149f4`。OSD frame5332 的原生队列/控制线程分别在邻近记录中出现；此 8B allocation 属于 tid838 的 headless ACK 路径，destination `0x8288076c`，非 GPE 动态 QID。该消息/对象没有独立 epoch 字段，**epoch unknown**；邻近 GPE bitmap/source epoch4 不能移植给它。671770 的 OSD `frame=5332` commit/pair 已完成，`pair_pending=0`，本次是随后 ACK 消息分配。

源码 `menu-repair-01/runtime/helpers/fx3-osd-lifetime-v2.c` 先把 `active[slot].since=now_ns()` 登记，再调用 `dprintf(FX3_OSD_LIFE_ALLOC_BEGIN)` 和 `start_watch()`，最后才调用 `alloc_next()`。watcher 以自身 guest monotonic 看 active age>=2s 输出 `FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END`，其耗时包含 observer 的串口输出。栈落在 `tty_write`、而非 osal allocator，证明这一现场的 `original_call_still_waiting=1` 文字不是有效推论。672712 原 allocator 返回 result0/errno0，随后用户 free0、原 ACK/信号路径继续；673274 marker 是 watcher 在 dump 了大量 /proc 信息后才打印，marker 行序不能当 allocation 仍阻塞的证据。runner 保守停机门正确执行，但输入 marker 是**观察器计时起点错误的误报**。

新 `fx3-osd-lifetime-v3.c` 仅将 active 登记移到自身 BEGIN 日志和 watcher 启动之后、原 `alloc_next()` 前；watcher 的原 2s 截止和 runner 停机门保持。host 定向 C harness 令 BEGIN `dprintf` 模拟耗时3s：旧源码 exit134（计时提前），新源码通过且原参数、结果、errno、send/free 不变。这个修复只纠正 observer 本次假阳性，不证明 QID/kernel free 问题已经解决。新候选仅更换 CPIO 中 `simulation/fx3-osd-lifetime-v2.so` 的内容，原固件/原种子/原 5000ms 均不变。
