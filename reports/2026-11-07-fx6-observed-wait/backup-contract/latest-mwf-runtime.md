# 302–305 MWF 最新运行核对（2026-11-07）

**结论：305 的变化是实际执行了 8 组 NULL 锁/列表操作跳过，避开 302 所见的 libMWF 崩溃；没有证明 MWF_Init 被调用或返回成功，也没有证明 provider、消息队列或 UI lifecycle 已恢复。305/303 均在120秒超时退出，所采渲染缓冲仍全零。** 本轮只读现有完成记录，未启动或接管 VM。

证据在 [latest-mwf-runtime.json](latest-mwf-runtime.json)，包括串口、command、run receipt 的路径/哈希、逐行运行标记、实际 CPIO 成员指纹、wchan 样本和像素文件统计。没有复制二进制或修改他人文件。

| 候选 | 实际运行目录 | 实际观察到的变化 | 未闭合项 |
|---|---|---|---|
| 302 | `cp-bind-6dccded6` | Lock patch 标记后出现 `pthread_mutex` 小地址强制成功；随后 libMWF SIGSEGV | 不是原锁/列表成功 |
| 303 | `cp-bind-61f3e945` | Lock 和 Unlock patch 应用标记；未见302的 SIGSEGV，推进到 MediaBlock 启动日志 | 没有 MWF_Init/provider 成功回执；仍超时、零帧 |
| 304 | 本 CP/runs 的 command 集中无匹配记录 | 本机有源文件，不能据此认定执行过 | 不将源码存在记作已运行 |
| 305 | `cp-bind-de72af8e` | NULL Lock / push_tail / Unlock 各8次；未见 SIGSEGV；MediaBlock 启动日志 | NULL 跳过不构造对象、不入队、不证明 provider/lifecycle 恢复 |

## 305 到底有没有调用 MWF_Init

**目前无法判定，不应回答“已经调用”或“确定没调用”。** 实际305 CPIO 的 `/usr/lib/libMWF.so` 是 353120B，SHA `3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782`，与实际 FX6 donor 相同，导出 `MWF_Init`。这只证明提供者二进制存在。

实际 `/usr/lib/libgrm-fbinit9.so` 是 82488B，SHA `f84cf2608f916434d321775158354d29e4ffee7d3e447c7e21afc1de73a58eca`；它导出三个 MWF 兼容方法（Lock/Unlock/push_tail），**不导出 `MWF_Init`**，其相关运行日志字符串也只有这三个 NULL 标记。串口没有专门的 MWF_Init 入口、参数、返回值或初始化状态观察器。因此“搜不到 MWF_Init 字样”不能证明调用没有发生。

305 第1231行 `FX6_APP_CONFIG_HOLD real_returned` 证明自编 wrapper 已越过其 `Application_System_Init` 调用；它不是 `MWF_Init` 的返回码，也不是嵌套 provider 注册完成或资源服务可用证明。第1185行 `preload /usr/lib/libMWF.so` 只证明 DSO 加载成功。

## 故障变化的运行证据

302：第1231行 `FX6_OBJSHLOCK_PATCH`，第1268行 `FX6_PTHREAD_MUTEX_STUB lock m=0x28 -> 0`，紧接第1269行 `APPFW_SEGV sig=11 addr=0x8`。PC/LR 模块均为 libMWF，PC 相对其基址是 `0x3b37c`。这是实际用户态崩溃，不能把 `run-receipt.json` 的 `fault_markers=[]` 当作无错；该 parser 没收进此信号。

303：第1231/1233行报告 Lock/Unlock patch 写入，第1234行 `real_returned`；第1291行 MediaBlock 启动。没有 `APPFW_SEGV` 标记。patch 写入标记不证明两个原方法的合法调用成功，也没有方法调用计数可以核对。

305：第1266–1289行恰为8组三连 `FX6_MWF_NULL ObjShLock::Lock / push_tail self=0 / ObjShLock::Unlock`，是被跳过的 NULL 对象操作的实际执行证据。随后第1310行 MediaBlock 启动、后续 `muxInit:done: 0`。这是某条绕过路径进一步推进的观察，不等同于先前未初始化对象已经得到初始化。

三个候选均有运行标记 `FX6_PATCH_OSAL_RCV_SUCCESS off=0x20efbb8 ... mprotect=0`，即仍保留强制接收成功补丁；不能把这些候选的 provider/lifecycle 行为概括为原厂语义已经通过。

## 当前卡点与画面

303/305 串口中都有9次 `FX6_UX_SCREEN_AREA_1024` 和一次 `FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0`。本轮独立逐字节统计了各自 `gpe0.bin/gpe1.bin`（各2211840B）及 `dmm0403.bin`（1232896B）：**所有已采文件的非零字节都是0**。302同样全零。这里只描述指定缓冲与采样时刻，不能替代全部显示路径或实机显示验收。

305 后续反复采到多线程 `futex_wait_queue_me`，也有 `osal_rcv_msg_tmo`、`osal_unlock`、`hrtimer_nanosleep`。例如第一组 TID217 是 hrtimer、TID220/221 是 futex、TID224 是 osal_rcv；这些快照只有 TID/wchan，缺少 comm/用户调用栈。**不能沿用另一次 observer 中“AppFw=TID224”的身份来解释305，也不能把全部 futex 线程都认作 AppFw/uxengine。**

305 receipt：`reason=wall_timeout`、`elapsed_seconds=120.11706304200925`、`qemu_exit=0`、`process_reaped=true`、`locks_released=true`。这是本次运行结束与回收的记录，不是菜单成功。仍有 ftp/remote `load_im` assert、UIPC `-1020` 警告和未处理 CP 通知；这些没有调用链绑定，不能据最后一条日志指定当前等待根因。

下一步有信息增益的工作是父 agent 已排队的调用链 observer，或者单独给 MWF_Init/provider 初始化边界加只读命中/返回观测；无需再次从源码意图推断运行结果。本轮不重做静态 MWF 分析，不建议继续扩展 NULL 成功或锁跳过。
