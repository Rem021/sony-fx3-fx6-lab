# 分清 FX3 请求交接与独立恢复入口

2026-10-29，经典 **ILME-FX3 7.02**，目标仍为1080p29.97 HEVC主录，当前优先研究修改失败后的退回。本轮取得两个具体入口：**当前NOR确有早期mode文件条件消费者；当前系统确有独立sen.elf进程。** 前者仍缺FAT初始化及实际镜像选择，后者仍缺命令准入与看护依赖。queue0x376则须纠正：前轮停点是OSAL交接层，尚未找到真正处理0／2／5／6的业务收件人。缺少预验证修改包继续作为研究问题；这些发现没有构成独立救援保证。([早启原证据](../evidence/early-selector/early-selector-evidence.json)、[进程依赖图](../evidence/usb-main-dependency/process-registration-dependency-graph.json)、[队列原指令](../evidence/queue-consumer/annotated-pins.txt))

## NOR已消费mode存在性，尚不能保证每次读到p2

当前包的Loader2原函数`0xFE053C78`先查cache，再查内存word `0xFE170028`；该word非零即通过，只有为零才调用`fat_mount(2)`并检查`\updater\mode`。这里**只看存在性，不读mode5／mode6正文**。FAT函数先要求ready位已置、当前partition恰为2；它不是在此完整初始化硬件的挂载实现。成功检查会置cache与内存word，失败缓存拒绝。启动清零表覆盖cache和FAT-ready，但后续生产者尚未补全，既不能保证实机必读，也不能断言此路永不可达。([mode消费者](../evidence/early-selector/mode-file-consumer.txt)、[FAT前提](../evidence/early-selector/fat-mount-preconditions.txt)、[初始化](../evidence/early-selector/startup-bss-zero.txt))

早期SPI选择还优先检查两个byte，之后才按上述条件发送字段4／7；远端再提供bootdata `+0x30`的loader mode。**发送字段、loader枚举、helper参数是三个数值域**：NOR表中3是updater、5是adjust、6是usbchrg、12是bis，不能把argv5／6解释成同一枚举，也不能称4／7就是p1／p3。外部GPIO／UPDATE_MIRA读取未映射为用户可操作的恢复按键。本文NOR地址为配置基址`0xFE049000`下静态VA，非机身PC。([SPI选择](../evidence/early-selector/early-spi-choice.txt)、[mode导入](../evidence/early-selector/bootdata-copy-mode.txt)、[原枚举与信号](../evidence/early-selector/early-selector-evidence.json))

NOR将实际上下文mode写到Backup项`0x0051000F`，当前UPM从同项读入`.bss+0x88`，getter也读同址，接通了**已选状态→MAIN观测**。这不是运行请求导致早启切换的因果证明。配置项`0x00FA0080`确能提供分区／文件记录，但已见直接caller属于off／hot-off；失败计数也未见阈值触发p1。当前同机p1、远端mode生产及p1／p3装载仍缺。([NOR写点](../evidence/early-selector/mode-to-backup.txt)、[UPM重定位](../evidence/early-selector/early-selector-evidence.json)、[record边界](../evidence/early-selector/config-record-consumer.txt))

## queue0x376第一跳是交接，真实启动业务仍待识别

应明确修正前轮`.text+0x3644 → node+0x10`的理解：公开构造路径分别填入**阻塞接收唤醒、内核回调包装、用户pending投递**。普通`osal_rcv_msg_tmo`会自行登记栈节点，回调只交正文指针并唤醒线程，连四字节命令都不解释；因此仅查显式reg API会漏掉真实接收者。内核包装须继续到`node+0x20`、`.text+0x28ec`，用户代理则到`libosal_uipc.so+0x32f0`才调用业务函数。这里是模块节偏移／ELF链接VA，非运行地址。([三类构造与第二跳](../evidence/queue-consumer/annotated-pins.txt)、[原重定位](../evidence/queue-consumer/callback-provider-relocations.json))

本轮没有识别queue0x376实际节点属于哪类。LIRO登记向量及av-cam veneer虽已定位，av-cam中的0x376却只是20字节配置记录，不能补作登记证据。既不能声称请求已经切LSI，也不能由纯唤醒路径宣告命令无效。([LIRO与导入审计](../evidence/queue-consumer/liro-metadata.json)、[配置原记录](../evidence/queue-consumer/avcam-queue-table.txt))

## 独立sen提供新候选，恢复能力仍须逐项证明

普通NIN的`libsensapi`表项经alias装入`libObj.so`，appFw也由**同一个im.elf执行dlopen／dlsym**；`THREAD_INFRA/APP`实际创建线程。由此推论，若故障终止整个im进程，普通NIN随之失去执行空间；单纯appFw文件装载失败则不能直接等同进程致命退出。([72字节表与原装载代码](../evidence/usb-main-dependency/process-registration-dependency-graph.json))

独立路径更具体：init2在`MODE!=0`、非BIS、smode可读且等于`UU`时，先后台启动sen.elf，**随后仍启动bootin**。sen自建USB对象、打开`/dev/usb/event`、建立自己的线程与事件循环；静态依赖闭包18文件，没有appFw／libObj。这个闭包不覆盖动态插件、IPC、LIRO／av-cam或驱动健康。shell没有wait／trap／联动kill，只能排除该脚本文本的直接寿命绑定，不能排除UPM、watchdog或其他服务整机复位。服务初始化失败本身也会abort。([原init2](../evidence/usb-main-dependency/originals/sbin/init2)、[USB自建](../evidence/usb-main-dependency/service-start-slices.json)、[静态闭包](../evidence/usb-main-dependency/static-dependency-closure.json))

| 故障范围／候选 | 已证明的依赖与入口 | 恢复仍缺 |
|---|---|---|
| im进程仍存活／普通NIN | 同进程libObj回调与线程 | 故障态对象及命令实际可用 |
| im致命退出／预启sen | init2条件启动，独立USB事件循环 | 命令表、Cooperator、看护、退出归还 |
| MAIN启动失败／NOR | 早期mode存在性条件、已选状态桥 | FAT-ready、远端mode、当前p1与镜像选择 |
| LIRO／av-cam或更早层损坏 | 本轮无独立恢复闭环 | 对应故障域外的读写与逆写路径 |

表中均为候选，未证明鉴权后能写标志、恢复目标文件、清理退出或冷启动归还。当前包无独立p1载荷的前轮结论继续成立，历史p1不能替代同机原件。([独立服务边界](<../research_notes/FX3 请求处理 独立启动/usb-main-dependency.md>)、[完整包审计](../../stage182-boot-selector-and-recovery-admission/current-updater-evidence/current-updater-asset-audit.json))

## 下一项先追独立sen命令与看护条件

最有价值的离线切口是`sen.elf+0x401f80`、`libsencore+0xb094/+0xceb0/+0xcc1c`：从独立模式构造器识别Worker／Cooperator和实际命令表，追鉴权后文件／请求能力及下游IPC，同时核对bootin／watchdog的存活前提。随后再按真实登记或阻塞接收来源追queue第二跳，不再把通用唤醒函数当reset实现。恢复材料随拟改故障域确定；原字节、独立逆写入口及归还合同各自成立，才评价最小可逆修改。([选定原函数](../evidence/usb-main-dependency/independent-service-slices.json)、[命令分派入口](../evidence/usb-main-dependency/disassembly/libsencore.so-cc1c.txt))

本轮仅综合宿主静态证据并核验来源，未执行原固件／脚本、guest或相机／USB／管理员／Windows／UU／GUI动作。目标继续；`goal_complete=false`、`persistent_write_release=false`。([队列范围](../evidence/queue-consumer/scope.json)、[早启范围](../evidence/early-selector/early-selector-evidence.json))
