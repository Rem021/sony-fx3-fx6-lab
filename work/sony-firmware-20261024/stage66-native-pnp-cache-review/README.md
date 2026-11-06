# FX3 原生 PnP 缓存关联复核

Windows 原生枚举已找到 ILME-FX3 的 USB 根节点与3条USBSTOR磁盘子节点的历史关联，当前4个节点均显示断开，关联接口禁用。现时连接候选为0；该结果不能作为后续相机接口访问的当前绑定。

本轮沿用已授权的缓存元数据范围，使用系统自带 PnPUtil 枚举关系、服务、驱动、堆栈及接口属性。7条内置查询均退出0；没有运行此前被执行策略阻止的PS1，没有提权、刷新硬件、改变驱动或打开相机接口。10件公开材料已通过UU接收，Windows会话显示任务完成。观察区间为2026-10-26 16:08:26至16:17:49 UTC。

| 缓存对象 | 服务及INF | 本次输出的驱动版本 | 连接状态 |
|---|---|---|---|
| ILME-FX3 USB根节点，054C:0DA1 | USBSTOR / usbstor.inf | 10.0.26100.9444 | Disconnected，IsPresent=FALSE |
| 3条磁盘子节点 | disk / disk.inf | 10.0.26100.9711 | 全部Disconnected，IsPresent=FALSE |

PnPUtil报告的提供者为Microsoft、签名者为Microsoft Windows；这些是驱动缓存字段，未独立验证驱动文件签名。HasProblem=FALSE不能替代缺失的问题码或当前DevNode状态，后两者仍为UNKNOWN。磁盘接口GUID来自本次设备树缓存；单节点枚举没有列出当前启用接口。[微软PnPUtil语法](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax)。

## 证据与限制

- 前一阶段64件封存文件和进度快照已复核，见[前一阶段记录](../stage65-windows-cache-and-runtime-readiness/README.md)。原四件交接输入及失败日志保留。
- 已核对[总回执](from-windows-public/receipt.json)、[节点关系](from-windows-public/node-relations.json)和[命令清单](from-windows-public/commands.json)的对应内容；三条子节点父摘要均等于根节点摘要。旧13件材料的前后哈希也与Mac已保存副本一致。原始实例ID、接口路径与序列号保留在Windows私有目录；16件私有原件仅传回哈希清单，没有传回原件，因此Mac未独立重算原标识摘要或复查私有原文。
- 重新连接相机后的缓存元数据必须另存新观察，不能把本次断开快照改写成“当前连接”。即便得到唯一磁盘接口，仍不代表相机协议、写入、录制或恢复已经验证。
- 公共JSON的部分Windows路径字符串包含双重反斜杠，是报告格式问题。原件保留，复核报告另给按UU实际目录核对的规范路径；这些字符串没有当作命令执行。
- 当前查询上下文记录LocalMachine=RemoteSigned，其余作用域Undefined；前一阶段独立PS1进程的UnauthorizedAccess日志同样保留。两次观察的上下文差异尚未解释，没有由新快照倒推改写旧错误原因，也没有改执行策略。
- 报告生成曾因命令过长被CreateProcess拒绝（os error206，未启动进程），随后用文件写入工具完成，不重复PnP查询。

## 内核配置核对

另对已固定SHA256的7.02原kernel Image做静态检查，找到4.9.337-scel+及SMP/PREEMPT版本标记；该Image没有找到IKCFG_ST或IKCFG_ED标记，未恢复实际构建的完整.config。公开7.00厂商配置仍只能用于选定字段相关性核对，不能认定整份配置等于7.02实际配置。见[kernel-config-presence.json](kernel-config-presence.json)。原内核及下载源码均未执行。

1920×1080、29.97fps、HEVC420 10bit约16Mbps主录及精确30fps的区分保持原目标；实际录制、音画同步、长录、冷启动、同机备份和独立恢复仍未完成。相机连接状态已另向用户核对；收到连接确认后，下一份缓存快照另存新目录，授权仍仅缓存PnP。goal_complete=false，persistent_write_release=false。
