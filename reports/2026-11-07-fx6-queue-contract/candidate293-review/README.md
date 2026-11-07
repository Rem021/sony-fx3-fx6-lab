# Candidate 293：无新增串口异常，但运行代码已改写且菜单仍不可见

复核291、292、293三个已结束实验后，结论是：**293的有限串口记录没有assert、SEGV或kernel Oops标记；两份显示采样仍全零。PID217的TID225反复停在内核`osal_rcv_msg_tmo`，现有材料不足确认它就是UI主线程或确定消息队列。**

293不是“原件appFw未经修改而稳定运行”：实际shim在原件入口前对appFw的5个BL调用点写NOP，并增加MonCtrl guard和Backup key替代值。容器内原件SHA不变，不能代表运行内存代码不变。

## 范围、产物与复跑

写入前确认外盘UUID为`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。本轮只读取完成回执、磁盘CPIO、源码、日志与既有内存采样，没有启动/停止VM，没有连接GDB/QMP/HTTP、进程端口或相机，也没有修改共享输入。

- `inspect_candidate293.py`：复用上一轮只读工具与协调者完整CPIO扫描器。
- `summary.json`：291–293的整包、成员、launcher、raw serial绑定；全部477个库entry比较；原始故障/patch行号；线程wchan样本；init与shim源码差异。
- `source-snapshots/`：保存本次读取到的四份自建源码，含291/293 shim、`init292.sh`及`appfw-launch288.c`。没有保存Sony固件或ELF二进制。

```sh
python3 -B reports/2026-11-07-fx6-queue-contract/candidate293-review/inspect_candidate293.py \
  --root /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic \
  --scanner reports/2026-11-07-fx6-parallel-native-ui/inspect_cpio_binding.py \
  --base-review reports/2026-11-07-fx6-native-lifecycle/deep-runtime/review_latest.py \
  --source-dir reports/2026-11-07-fx6-queue-contract/candidate293-review/source-snapshots
```

三轮都已`process_reaped=true`且`locks_released=true`。完整CPIO SHA/bytes、loader路径、完成回执manifest SHA、serial SHA均匹配。CPIO扫描包含首TRAILER后的追加members；采用最后出现成员索引，仍不模拟内核hardlink/最终文件系统抽取。

## 真实变更：292是另一条启动支线

| Candidate / run | 实际init及启动 | 实际shim SHA前缀 | 关键区别 |
| --- | --- | --- | --- |
| 291 / `cp-bind-bb80f799` | `LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch`，PID217 | `b6489cbd3f3e` | 添加kikilog callback stub；仍发生旧MWF空MonCtrl故障 |
| 292 / `cp-bind-d0a9cec4` | 写`/setting/mode/dmode=3`、清空preload，改用`LD_PRELOAD=libgrm-fbinit9.so bootin.elf 'target=qemu ' dmode=3`，PID218 | `46974fad8e0c` | 回退到289/290的shim；不含291 kikilog stub，也不含293的guard/patch；随后im.elf PID224崩溃 |
| 293 / `cp-bind-4cdf812e` | 恢复与291完全相同的init和launcher，PID217 | `73c603ab9685` | shim同时增加5处NOP、MonCtrl guard、两个Backup key override |

三轮`usr/bin/appfw-launch`逐字节相同，SHA`0a4eb7a70b38aed52b644dfc044515197334a7d3842ef254e56e5ff809376ea6`，92,488 B；它在292仍在容器中，但该轮init没有调用它。291与293的init SHA也完全相同：`797b9e900d48781ac8d3d6bcbc25295cb7c001f821b4899655f922d8e0a8b7ec`。

各相邻轮及291→293直接比较，477个库entry中只有`usr/lib/libgrm-fbinit9.so`改变。三轮容器中的50,520,424 B appFw仍为`a1c58b...`原件，libMWF未改变。

`/tmp/libgrm-fbinit25-291.so`、`/tmp/libgrm-fbinit25-293.so`及`/tmp/appfw/appfw-launch288`的SHA均与对应容器成员相符。源码snapshot与这些产物有明确路径和诊断内容关联，但本次没有重建编译或独立build receipt，因此不把源码SHA直接当作可重复构建证明。

## 293运行代码写入的证据

实际CPIO内293 shim的ELF符号与控制流确认：

- `Application_System_Init`位于shim`+0x17eac`；`+0x17f5c`先调用`fx6_patch_blocking_calls`，`+0x17f7c`随后调用原件entry。
- patcher位于shim`+0x17fa4`，其40 B偏移数组位于`+0x2b18`。从实际ELF数组解析出的5项与源码、串口完全一致。
- 源码使用`dladdr(real_init)`取得appFw基址，`mprotect(page,0x1000,RWX)`后写`0xd503201f`并清指令缓存。没有旧指令校验、写后读回或恢复RX。

| appFw偏移 | 容器原始指令 | 293串口行 |
| --- | --- | --- |
| `+0x12d824c` | `bl +0x1a6ee10` | 1228 |
| `+0x12d8250` | `bl +0x1a5a230` | 1229 |
| `+0x12d8254` | `bl +0x20ed13c` | 1230 |
| `+0x12d825c` | `bl +0x1d96370` | 1231 |
| `+0xc09e50` | `bl +0xc09c14` | 1232 |

以上五行都是`FX6_PATCH_NOP ... mprotect=0`，位于1227入口日志之后、1233`real_returned`之前。由此可以确认有执行到的改写路径及自报；当前磁盘产物中没有写后guest代码字节读回，不能声称五处内存逐字节验证通过。

同时新增：`MonCtrl::GetFlag(NULL)`返回0的interposition；`Backup_read_8Byte(0x00fa01a3)`返回`0x429100000`、`0x00fa01a4`返回`0x100000`。因此从291→293无崩溃不能单归因于某一个BL被NOP。

此外，共用launcher本来就含`mprotect`和GOT slot写入；291及293串口均有`fix_got_table ... entries=832 fixed=799 missing=33`。`appFw.so`容器原件SHA从来不足以证明其运行映像未修改。

## 异常计数与观察边界

只统计raw serial真实标记，排除kernel command line的`panic=-1`，不把普通“error”字符串算成kernel Oops。

| Candidate | assert | SEGV | kernel Oops/panic/BUG | 两份gpe采样 |
| --- | ---: | ---: | ---: | --- |
| 291 | 2 | 1 | 0 | gpe0/gpe1全部零 |
| 292 | 0 | 1 | 0 | gpe0/gpe1全部零 |
| 293 | 0 | 0 | 0 | gpe0/gpe1全部零 |

291原始行1253/1262是FTP/remote assert；1283为`APPFW_SEGV addr=0x10`，1316给出libMWF基址，仍对应`MonCtrl::GetFlag +0x3e908`。

292原始行1700–1707将异常归属到`im.elf(im.elf) pid224`，PC`0x7f781209d0`、访问地址0。映射基址`libMWF=0x7f780e0000`，相对PC`+0x409d0`，对应`MonQueue::GetQueueRemain()`。这不是291那条MonCtrl故障，也没有appfw wrapper入口日志。

293完整serial为2,108行，扫描没有上述故障标记。可以表述“本次有限日志未见assert/SEGV/Oops”，不能扩展为原厂相机初始化成功或所有错误均消失。1238–1256仍仅到图形/Arena初始化，1243的flush明确为`prims=0 nz_pixels=0`。

293的`gpe0.bin`、`gpe1.bin`均为2,211,840 B，非零字节数0。两个DMM buffer是否为最终原厂显示平面未在这里验收；现有材料不能给出可见菜单PASS。

## PID217 / TID225到底证明了什么

293串口1175给出appfw-launch PID217；init原始行241–246明确枚举`/proc/$appfw_pid/task/*`并只读取每个task的`wchan`。TID225共有26组完整采样：

- 第一组serial1277–1279，内容为`osal_rcv_msg_tmo`；
- 最后一组serial2102–2104，内容相同；
- 没有该线程的`comm/status/syscall`、用户PC、用户栈或消息队列id；也没有命令line或完整进程映射快照绑定到TID225。

因此确定归属是**appfw-launch进程的一个线程在OSAL消息接收内核等待点**。函数名带`tmo`不证明发生了超时或永久死锁，也不区分正常事件循环等待、特定IPC请求未完成、UI主线程或工作线程。现有观察不能把225提升为“UI主线程正在等某外部服务”。

291对应样本还与异常寄存器输出交错：`THREAD_BEGIN_225`之后出现的`APPFW_X*`属于异步信号日志，不能因文本夹在该区块就认定崩溃线程是225。293的26组wchan区块没有这类寄存器交错。

293另在serial1257–1258记录CP未处理请求，`no_reply=1 no_free=1`、source=`0xa5a5a5a5`。这说明本轮还存在未完成的IPC路径；没有队列/step/caller关联证据可把它与225的等待绑定。

下一步需要在原有运行负责人控制下，获得线程名、真实创建函数/入口与TID的绑定，以及同一线程的用户栈/接收队列信息，再判断它是否是目标UI worker。此次没有为填补缺口而连接运行进程，也没有提出吞掉所有消息接收的补丁。
