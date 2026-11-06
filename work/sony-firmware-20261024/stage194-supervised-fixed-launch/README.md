# FX3 固定启动监督器与程序自读握手

2026-10-29。**16项完整假对象启动流程＋1项实际本地分段流检查通过**。原生候选10只编译，仍固定 `FX3_NATIVE_RELEASED=0`；没有运行管理员、相机、Windows或GUI操作。原生Terminal命令仅生成文本并做shell语法检查，未打开Terminal、未执行sudo。

本轮将自建假设备的启动、实际helper身份核验、握手、observe/end、私有回执和进程结束观察接到同一个监督器。原生实际启动/跨UID仍未验，不能从这17项推出安全刷写或救砖。

## 实现与发现

- [fixed_launch.py](fixed_launch.py)提供有界私有复制、固定哈希安装、目录与入口各自一次性租约、清空环境的Terminal/sudo命令模板。假对象测试实际运行同类shell启动流程；原生启动API保持拒绝，旧05授权不会被当成10的批准。
- [supervisor.py](supervisor.py)只把内核核对过的实际helper PID作为拥有者；启动请求/relay的退出码、stdout和共享completed均不能替代私有回执。超时继续观察同一实例、同一连接和已收到的字节，没有kill/reset/重启分支。
- [helper_hello.c](helper_hello.c)在操作前自读当前程序，检查普通文件、UID、权限、单链接、大小、前后身份及摘要，并在同一已核对peer的socket发送固定160字节HELLO。监督器核对内核PID/UID/出生时间/路径和HELLO中的程序摘要后才ACK。它解决普通用户不能直接读取root0500程序的适配问题；**root权限下的实际验证尚未做**，现有root场景只覆盖政策模型。
- [controller_ipc.py](controller_ipc.py)仅加载数据/进程IPC库，用pread/pwrite处理报告，不把用户文件mmap成控制状态。报告截断时仍可接收私有结果。
- 重启后[recorded_observation](supervisor.py)只提供当前内核元数据对照，保持 `UNKNOWN_RECORDED_CONTEXT`。用户可改的JSON、bin或“认证成功”字段不能重建原来的存活peer证明；root私有归档及可信重新查询尚待实现。

一次实际测试发现，当前Mac的Python `monotonic_ns()`与C入口的 `CLOCK_MONOTONIC` 数值约差3.8秒，导致请求预算被拒绝。协议截止时间已统一为 `clock_gettime_ns(CLOCK_MONOTONIC)`，不扩大预算；相对观察等待仍在各自一致的时钟内计算。[实测](clock-observation.json)与[Python官方说明](https://docs.python.org/3/library/time.html#time.monotonic)分别提供本机证据和API背景，不能将该偏移推广到所有Mac。

## 证据

| 文件 | 范围 |
| --- | --- |
| [构建](build-receipt-v2.json) | 假设备helper运行ASan/UBSan；native仅编译/链接 |
| [16项流程](supervisor-results.json) | 实际启动与helper区分、观察超时、保留与排他、错误哈希/伪造relay、租约、特殊文件、固定原生命令语法、重启拒绝、截断、ACK拒绝/取消、HELLO及shell引用 |
| [1项分段流](incremental-stream-result.json) | 真实同UID Unix连接，明确构造的HELLO；观察超时后保留部分数据和同一个FD，未发送放行ACK |
| [限制与复核](verification-receipt.json) | 当前源码/构建/执行回执及193封存摘要 |
| [实现边界](implementation-review.json) | root跨UID、原生放行、持久可信回执、真实恢复缺口 |

193的58项与192的18项日志证据没有重复计入17。底层设备、MSC会话、拥有者核心和排他日志字节保持原样。自己的假对象测试中包含一条明确标记的START保留路径，假helper不链接IOKit；没有Sony鉴权或相机START。

失败历史保留：首版时钟混用；一次测试在实际启动前就假定100ms内已到HELLO；一次误把只做内存检查的P_PROFILE当成可阻塞外部调用。后两项已改为等待实际已核对helper、选择真实P_CLAIM假调用，不放宽拥有者或清理判断。

## 后续

先构建独立的、完全不链接IOKit的root仅主机假对象程序和固定启动方案；核对root→UID501、0500自读、实际helper/relay及受保护文件行为后，再申请该具体单次执行。随后补root私有归档/重新核验；不能仅靠用户日志宣称重启后已恢复可信状态。

真实MSC接管、Sony鉴权、机身/p1读取、模块执行、备份写回和刷写仍须各自适用的范围与证据。恢复优先、原来全部16项要求及授权状态保留；`goal_complete=false`、`persistent_write_release=false`。
