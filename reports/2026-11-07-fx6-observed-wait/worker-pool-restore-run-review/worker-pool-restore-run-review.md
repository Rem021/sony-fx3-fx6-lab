# 已完成 worker-pool-restore 运行独立复核

恢复点后已有明确的原生初始化推进：本轮采样到 129 个不同 TID，并出现 9 次真实 receive 入口、8 次返回。唯一未配对入口是 TID 231 / SeqQueueCommon 的 `bb_request_reply`，用户 LR 为 `appFw+0x20ef7cc`、qid=`0x81cf610f`、timeout=`-1`。四份捕获仍全零，冷启动 completion、guest 按键消费和原厂菜单均未证明。

运行：[worker-pool-restore-a3af746e3d receipt](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-worker-pool-restore-20261107/runs/worker-pool-restore-a3af746e3d/run-receipt.json)。完整证据与原始行号见 [worker-pool-restore-run-review.json](worker-pool-restore-run-review.json)，只读脚本见 [review_worker_pool_run.py](review_worker_pool_run.py)。本复核未操作 VM/端口/进程，未重复反汇编。

## 绑定与完成回执

25 项检查全部通过：receipt 的全部文件大小/SHA，实际 runner/fixed_runner，完整 295 → observer → snapshot → restore proof、raw CPIO 和源变更门，helper/ABI 指纹及 command argv。command 与 v4 规范化结果完全相同，无重复 `-s`，mode/schema/authorization 均准确记录 worker-pool-restore。所读运行输入前后大小/mtime 不变。

- manifest SHA：`8f3dc13a934a5d35110b7527bbae9a913c1ffdbb462a3646d4066949b462dcc1`
- runner SHA：`cc2e0ab98d66a62eb767f5afe5a8f8eff2b288e50e36a0cbdc4f3fa75c2b9d39`
- serial SHA：`2f86db9e4692c333aa17aa8e3e070ffa0705740c8aa8e687dac443b9a6a33b99`

receipt：`wall_timeout`、120.209245 s、QEMU 42729 exit 0、`process_reaped=true`、`locks_released=true`。这是限时运行及清理完成，不能解释为原生冷启动成功。实际 patch 日志保留 `12d824c,12d8250,12d8254,c09e50` 四项，没有 `12d825c` 的 NOP 日志。

## 实际线程数与生命周期

任务快照共 2,838 块，覆盖 129 个不同 TID。status 的 Threads 字段分布为：初始 `1` 共 1 条、`128` 共 97 条、后续 `129` 共 2,740 条。129 不仅来自 helper 枚举，后续常规 status 也实录为 129。不能将工厂静态声明的某个池规模等同于进程总线程数。

COMM 包含 AppFw、两个 UX resource、SeqThreadPool0–3、多个 SeqQueue、MPR、UIPC 和存储任务；COMM 可能截断或重复，身份按 TID 区分，完整分组保存在 JSON。

| TID / COMM | 样本数 | 首次 → 末次 guest uptime | 实录状态 |
|---|---:|---|---|
| 217 / appfw-launch | 23 | 4.54 → 116.27 | 首次 R；后 22 次 S，含 3 次 hrtimer_nanosleep / 19 次 sys_restart_syscall |
| 224 / AppFw | 22 | 7.60 → 116.29 | 全部 S / futex_wait_queue_me |
| 231 / SeqQueueCommon | 22 | 7.72 → 116.40 | 全部 S / osal_rcv_msg_tmo |

224 和 231 末次均存在，没有退出或未启动证据。主 agent 单独负责 AppFw future 及其他用户帧的地址/调用链解释；本复核保留其寄存器与 FP 原始记录，不由 wchan 推 owner 或用户 LR。

## 真实 receive 配对

seq 1–8 均由 TID 231 在 guest monotonic 7.283244–7.299357 之间经 `libmpr.so+0xcbb3a0`、qid=`0x80c7610f`、timeout=`-1` 调用，均有 EXIT rc=0。返回时 errno=22 仅作为原始字段保存，不能单独解释成调用失败或协议错误。

seq 9（serial 1355）为：

```text
tid=231 t=7.309308000
caller=/usr/lib/appFw.so+0x20ef7cc site=bb_request_reply
qid=0x81cf610f timeout=-1
target=/usr/lib/libosal_uipc.so@0x7f97a30468
```

直到该完整运行日志末尾未见对应 EXIT。此处用户 LR/qid 来自实际观察器入口，而非内核 wchan 猜测；它与本轮 231 的等待状态一致。仍不能由无 EXIT 断言永久死锁、缺失消息类型或回执 owner；观察器没有读取输出消息内容。也不能将此 request/reply 入口错当成旧 `bb_finalize` 握手。

## 129 次 snapshot 与 detach

helper 枚举/处理 129 个 TID。129 组 SEIZE、INTERRUPT、REG、DETACH 均完整，SEIZE/INTERRUPT/DETACH rc 全为 0，TID 集合一致。serial 10286 END：

```text
processed=129 enumerated=129 failures=0 cancelled=0
overflow=0 detach_failed=0 elapsed_ms=975
```

10287 行 helper rc=0。共保留 129 组 PC/LR 与 781 个 FP frame，合计 1,039 条原始地址；本复核不重新做 ELF 归属解析。成功 detach 不能抹去 sequential ptrace 对线程时序的诊断干扰。

## 捕获、按键与 fault

四份捕获逐字节统计均为 0 非零字节：GPE0/GPE1 各 2,211,840 B；DMM0400 8,388,608 B；DMM0403 1,232,896 B。GPE0/1 仍是同一物理资源 `0x41e001000` 的重复捕获。没有 APPFW_SEGV、assert、Kernel panic/Oops/Internal error 标记。

按键仅有 step 1（0x1ab）软件 gate 的 12 B 写入/回读一致，step JSON 与 gate history 一致；没有 guest 消费或原厂 UI 响应回执。step 2（0x30）顺序/identity/result 门失败，receipt 保留 unknown delivery，停止后续步骤且未重发；实际 attempts 只有 1、2，成功 operation 只有 1。不能因为第二步失败重放第一步，也不能把软件页 READY 或新线程数量当成键 worker 消费证据。

本轮关闭了“恢复点是否产生可见原生推进”的观测缺口，并将新的真实等待定位到 SeqQueueCommon 的 BB request/reply 接收。等待消息/owner 和 AppFw completion 的因果链由后续独立研究继续闭合。
