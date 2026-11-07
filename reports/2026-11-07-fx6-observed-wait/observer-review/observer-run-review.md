# 已完成 observer-004ab971f4 语义复核

本次证明 AppFw 线程已启动并持续存在于多次快照，未见线程退出；它处于内核 futex 等待。没有新的用户态 LR/qid，不能确定等待对象或把它归给 `osal_rcv_msg_tmo`。两份 GPE 及两份 DMM 捕获均全零，菜单可用性仍未成立。

运行来自冻结 Candidate 295 的观察器派生，未采用 299 假接收成功。原始 [receipt](/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-observer-integration-20261107/runs/observer-004ab971f4/run-receipt.json) 显示 `wall_timeout`、120.1007 s、`process_reaped=true`、`locks_released=true`。本次校验 manifest、实际 CPIO、command loader、runner/fixed_runner 指纹和 receipt 内所有文件指纹均相符；所读输入审计前后大小/mtime 不变。完整记录见 [observer-run-review.json](observer-run-review.json)，复核脚本为 [review_observer.py](review_observer.py)。

## 线程：已出现并存活到最后采样

| PID / TID | COMM | 样本数 | 首次 → 末次 guest uptime | State / wchan |
|---|---|---:|---|---|
| 217 / 217 | appfw-launch | 38 | 4.08 → 118.35 | 首次 R / 0，之后 37 次 S / hrtimer_nanosleep |
| 217 / 224 | AppFw | 37 | 7.14 → 118.37 | 37 次 S / futex_wait_queue_me |
| 217 / 225 | uxengine_res1 | 37 | 7.15 → 118.38 | 37 次 S / futex_wait_queue_me |
| 217 / 226 | uxengine_res2 | 37 | 7.16 → 118.40 | 37 次 S / futex_wait_queue_me |

AppFw 的首次完整块为 serial 1330–1344，末次为 3490–3504。COMM 与 status Name 都为 `AppFw`，Tgid=217、Pid=224、Threads=4。四线程出现后的所有完整采样均为 Threads=4，没有后续消失/退出/僵尸记录。因此“AppFw 未启动”及“出现后退出”均不受本次证据支持。采样不能排除间隔内的短暂状态变化，也不能提供精确线程创建时刻。

`THREAD_BEGIN/END` 仍是 `/proc/.../task/*` 采样边界，不是创建/退出事件。Linux 官方文档将 wchan 定义为任务等待所在的**内核**函数；`futex_wait_queue_me` 不能给出用户 LR、锁 owner、条件变量或队列身份。[Linux /proc 文档](https://docs.kernel.org/filesystems/proc.html) 表中的 uptime 也不作为主机性能或定时器准确度测量。

## 到达点与观察边界

serial 顺序是：

1. 1263、1279：观察器库 owner 正确；appFw GOT `+0x2ef2868` 的 requested/readback 同为 `0x7fadc6f6d4`，owner 为 `libfx6-queue-observer.so`，mprotect=0。原值 owner 为 appFw。
2. 1283–1289：进入真实 AppConfig 初始化，记录继承的五处 NOP（`12d824c,12d8250,12d8254,12d825c,c09e50`），随后 `real_returned`。保留这些 patch 使本次仍不能证明原厂完整初始化链。
3. 1290–1300：Stella heap、GRM framebuffer 对象/尺寸、BMP、软件键页、OSD 映射/资源和一次 framebuffer 回调有实录。`FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0`。
4. 1301–1312：九条 `FX6_UX_SCREEN_AREA_1024`，最后一条在 1312。随后 1313–1314 为 CP unhandled/no_reply 日志；1315 至文件末尾 3534 只有任务快照，没有新的可见 UX/绘制进度。

这把最后**可见**到达点收窄到 UX screen-area 初始化之后、AppFw 与资源线程 futex 等待的稳定采样阶段。日志未给这些 UX 行加 TID，不能把每条行的发出者直接绑定到 224，亦不能由“最后日志”推出精确当前用户 PC。

`FX6_QUEUE_OBS_ENTER=0`、`EXIT=0`，无 bind/resolve failure。安装时的 GOT 回读是有效证据，但没有初始化后持续/末次 GOT 回读；内部 direct call、其他入口或后续重绑不在这一次 readback 的证明范围内。因此只能说“这个 hook 没有产生入口记录”，不能说“没有任何 receive 调用”，不能声称事件循环/BB finalize 已被截获。

## fault、帧与独立按键错误

无 `APPFW_SEGV`、`assert at`、`Assertion `、Kernel panic/Oops/Internal error。相较 296–299 没复现其空 ObjShLock crash，但此基线仍 NOP 了更多原始调用，不能将此归为 MWF 生命周期已修复。

四个捕获都逐字节统计为 0 非零字节：GPE0、GPE1 各 2,211,840 B；DMM0400 8,388,608 B；DMM0403 1,232,896 B。GPE0/1 的物理来源均为 `0x41e001000`，是同一注册区域的重复捕获，不能视为两路独立画面。

`keyinject-error.txt` 是 host 的 `FileNotFoundError(2, 'No such file or directory')`，receipt `key_operations=[]`，无 step JSON 或输入 gate 写入回执。匹配 receipt SHA 的 runner 在首次 gate.command 异常后关闭后续按键；gate 源码固定连接运行目录 Unix `g`，首次 connect 位于任何软件键内存写之前。本错误应单独归为 host 输入入口失败，不能归为 guest 菜单拒键。

实际 argv 先指定 `-gdb chardev:keygate93` / `socket,path=g`，末尾又带 `-s`。QEMU 官方定义 `-s` 等于 `-gdb tcp::1234`，这是端点重复配置的具体缺陷。[QEMU Invocation](https://www.qemu.org/docs/master/system/invocation.html) 由于异常仅保存 repr、没有 traceback，精确抛出行和覆盖过程仍需独立源码或无 guest smoke 证明；不能把当前已结束后 socket 文件不存在当作运行时证据。本审计未连接 `g`、TCP1234 或任何其他端口，也未重跑 VM。

## 对下一步的约束

可复用的新增证据是：安装时 hook provider/readback 已闭合，AppFw 224/UX 225、226 长期可采样。后续应分别修 host Unix gate 配置，并在保留真实调用/返回语义的前提下获得 AppFw 用户态停点和 futex 对象/上游 owner；先补观测，不由 wchan 推断 LR，也不继续使用假 receive 成功。当前结果是可复核的等待状态诊断，不是菜单修复通过。
