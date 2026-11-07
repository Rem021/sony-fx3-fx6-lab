# 已完成 snapshot 运行独立复核

本轮成功取得四个线程的寄存器/FP 链，并记录四次成功 detach；AppFw 和两个 UX 资源线程持续存在。软件键第一步写入/回读成功，第二步顺序门失败后停止，未重发。四份画面/内存捕获全零，原厂菜单及 guest 消费仍未证明。

运行：[observer-00d964f97c receipt](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-wait-snapshot-20261107/runs/observer-00d964f97c/run-receipt.json)。独立结构化证据见 [snapshot-run-review.json](snapshot-run-review.json)，只读复核脚本见 [review_snapshot_run.py](review_snapshot_run.py)。本复核未连接 VM、端口或控制进程，未重复反汇编。

## 输入与完成绑定

21 项复核检查通过：receipt 绑定全部记录文件、manifest、实际 runner/fixed_runner；v3 离线完整校验再次验证 295 → observer → snapshot 的 proof、真实 CPIO 和固定父链；helper/ABI 文件哈希也匹配。command argv 与 v3 规范化结果完全一致，保留 Unix `g`，没有 `-s`；authorization 为 `bounded diagnostic derived295`。所读输入前后大小/mtime 不变。

- manifest SHA：`df39ee856ea9c667d786920c0ec9c12b43992fbc17525870cbd53b38f5c8da42`
- runner SHA：`8147eaa9eed628c7bf30d7d2b92f478b3d434cf047a3d8959d317451108c007b`
- serial SHA：`5f4e7e5fd909dd6888df5ae2b0506a485274f9aa6a9c2193106bcff7616feafa`

receipt 为 `wall_timeout`、120.164393 s、QEMU 34729 exit 0、`process_reaped=true`、`locks_released=true`。这是受控限时运行与清理完成，不表示原生 App 正常退出或 UI 可用。

## 四次 snapshot 与 detach

serial 1615 开始一次 helper，目标 PID=217，枚举既有 4 个 TID、overflow=0。每个 TID 都有 SEIZE rc=0、INTERRUPT rc=0、STOP、REG、FP 链及 DETACH rc=0，detach signal=0：

| TID | COMM | FP frame 数 | detach 原始行 |
|---:|---|---:|---:|
| 217 | appfw-launch | 4 | 1984 |
| 224 | AppFw | 11 | 2008 |
| 225 | uxengine_res1 | 8 | 2029 |
| 226 | uxengine_res2 | 8 | 2050 |

2051 行 END 为 `processed=4 enumerated=4 failures=0 cancelled=0 overflow=0 detach_failed=0 elapsed_ms=137`；2052 行 `INIT_END rc=0`。原始 PC/LR 共 8 个、FP saved LR 31 个，合计 39 条地址。本复核只核数量与记录完整性；ELF/PT_LOAD 归属和等待调用链由主报告单独分析。

helper 会逐线程短暂停止执行。detach 成功证明本次 detach 回执完整，不能消除诊断对调度/系统调用的干扰。

## 线程生命周期与最后到达点

| TID | 样本数 | 首次 → 末次 guest uptime | 状态 |
|---:|---:|---|---|
| 217 | 38 | 4.17 → 118.72 | 首次 R，后 37 次 S；5 次 hrtimer_nanosleep、32 次 sys_restart_syscall |
| 224 | 37 | 7.25 → 118.74 | 全部 S / futex_wait_queue_me |
| 225 | 37 | 7.27 → 118.76 | 全部 S / futex_wait_queue_me |
| 226 | 37 | 7.28 → 118.77 | 全部 S / futex_wait_queue_me |

AppFw/UX 线程末次仍存在，不能称为未启动或已经退出；采样也不能排除间隔中的短暂状态变化。主线程在 helper 之后出现 `sys_restart_syscall` 是新观测，不是新 fault 证明。wchan 只描述内核等待位置，不能由它推用户 LR、qid 或 owner。

可见初始化仍到达 AppConfig `real_returned`、GRM/BMP/OSD、九个 UX screen-area（最后一条 serial 1312）。OSD flush 为 `prims=0 nz_pixels=0`。GOT 安装时 provider/readback 正确，但本轮 ENTER/EXIT 仍均为 0；不能据此排除 direct call、其他入口或之后的重绑定。无 APPFW_SEGV、assert、Kernel panic/Oops 标记。

## 捕获与按键证据边界

四份捕获均逐字节统计为 0 非零字节：GPE0/GPE1 各 2,211,840 B，DMM0400 8,388,608 B，DMM0403 1,232,896 B。GPE0/GPE1 都来自 `0x41e001000`，是同一资源区域的重复捕获。全零不能用作菜单可用证据。

key 1（0x1ab）写入软件页 `0x41df00008` 的 12 B 与回读一致；step JSON 和 gate history 一致，标识明确为 `native-screen-unverified`。这只证明软件 gate 写入/回读，未记录 keyworker 完成 ack、guest 消费或原厂画面响应。

key 2（0x30）报 `host-step software identity/order/result mismatch`；receipt 保守保留 `delivery=unknown`、`retry_suppressed=true`、`subsequent_steps_suppressed=true`。实际 attempts 只有 1、2，成功 operation 只有 1，没有 step 2 成功回执或重发。不能把第二步失败抹去第一步已写入状态，也不能重放第一步。KEY96_READY 仅为软件页初始化，本轮四线程列表不单独证明键 worker 的存在或消费。

本轮新增的是可用的用户寄存器/FP 链与完整 detach 证据；修复基线、等待 owner 和菜单响应仍需要各自证据闭合。
