# FX3 7.02 服务链的运行时独立性与磁盘启动入口

## 1. 动态插件、文件操作与 IPC 是否重新依赖主应用？

### Takeaway
普通文件操作的关键实现直接位于原厂 `libsencore.so`，不是仅由未追踪的 `libpro` 插件提供；本次已观察到包分派到本地文件处理器的静态调用。但这只能缩小依赖范围，尚不能证明主应用损坏时 USB 服务及全部恢复步骤仍可用。[原始指令与调用点](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)

### Cited Findings
- 本轮只做原 ext2 的只读解析、ELF 元数据及反汇编，没有执行/仿真固件或接触硬件。`sen.elf` SHA256 为 `9e3236666176b69746848edaac31e1e0ef00c4e80a9f062794ff62be2d605470`，`libsencore.so` 为 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`；镜像、六个选定 ELF 和启动脚本的固定来源哈希均留存。[来源清单](../../work/sony-firmware-20261024/stage7-entry/firmware/source-manifest.json)、[分析脚本](../../work/sony-firmware-20261024/stage7-entry/firmware/static_service.py)
- `sen.elf` VA `0x402b78` 选择字符串 `libsencore.so`，`0x402b84` 路径随后查询 `senser_usb_mode_start` 并间接调用；实际 `dlopen` 包装器调用点为 `0x4039f4`。`sen` 初始化还调用 `osal_reg_sync_msg_queue_cb`（`0x401fb0`），因此服务本身已经依赖 OSAL/内核基础设施，而不仅是一个 ELF 能被加载。[sen 固定字节与启动分支](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[完整静态索引](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- `libsencore` 的 `GetPluginModule` VA `0xdb68` 以 `/usr/lib/` 为基础构造插件路径，先检查文件再 `dlopen(...,1)`，并有缓存及失败返回分支。`ProductInfoFunc` 中 VA `0xeb5c` 引用 `libpro%02X.so`；`CreatePluginCommand` VA `0xe254` 查询 `command%04X`、`open%04X`、`close%04X`、`memory%04X`。官方 rootfs/usr 的本轮索引只找到 `libpro00.so` 一个该命名家族的实际文件；它导出 `command001F`、`command00F1`，前者调用 core 的 `Read_Hasp`。不能从格式字符串推出所有编号插件都已存在。[插件指令](../../work/sony-firmware-20261024/stage7-entry/firmware/targeted-disassembly.txt)、[原 ELF 导出与索引](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- 文件操作 helper VA `0x10994..0x10d3c` 首24字节为 `fd7bbba9001c00531f280071fd030091f35301a9f40301aa`（以逐指令回执为准）；它按小整数操作码分派到 `access`、`mkdir`、`DeviceIo::open/read/write/size`、`fopen/fgetc/fclose`、`remove`、`rmdir`、`sync`。该 helper 的全部已解直接调用中没有 `SubsystemCommunicationCommand`、`testcmd_*` 或 OSAL 消息发送；`DeviceIo` 的最终包装器直接调用 libc 的 `open/read/write/ioctl`。这是本地文件执行层的证据，不是全部祖先流程独立的证明。[逐字节函数与调用清单](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[DeviceIo 导出和调用](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- 本地包分派存在 `0x12884 → 0x10d3c`，随后在 `0x10de4/0x10e00` 等处直接调用上述文件 helper；相邻 `0x1101c` 等处理器也重复使用它。当前可确认本地处理器没有把每次文件读写都转发给主应用，但尚未给所有匿名处理器赋予协议名称。[处理器原始指令](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[处理器调用上下文](../../work/sony-firmware-20261024/stage7-entry/firmware/handler-disassembly.txt)
- 另一条明确的路径是 `HostCommunicationCommand::DoExecute` VA `0xd724`：打开两条设备消息接口、写 `0x10c` 字节、poll/read 回应；`SubsystemCommunicationCommand::TransactionStart` 则有 `testcmd_init`、`testcmd_sndmsg`、`testcmd_run_scenario`。`libtestcmd_scn.so` 的 `testcmd_scn_open` 在 `0xea0` 调用 `dlopen`，从 `/usr/scenario/` 组装场景文件并在 `0xed0` 查询入口。这些是另有 IPC/场景依赖的命令路径，不能推广为普通文件 helper 的必经路径。[Host 路径指令](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[IPC 和场景加载索引](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- `libSnr.so` 动态加载位于 core 的匿名回调 `0xe60c`，查询 `Sonar_Packet`；`SonarFunc` VA `0xec9c` 把该回调地址写入命令对象。模块缺失分支 `0xe71c` 返回 `0x80`，符号缺失分支返回 `0x82`；本轮官方 rootfs/usr 索引没有该模块。它目前表现为 Sonar 命令的可失败分支，未发现必须先成功才能启动整个服务的证据。[Sonar 回调和失败分支](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[未找到模块的索引结果](../../work/sony-firmware-20261024/stage7-entry/firmware/dynamic-extra.json)
- `/appfw_infra` 在所查 `0x11a4c` 路径中与 `/tmp`、`/ilog_data_%010d.bin` 拼接，是日志输出路径线索，不能把字符串本身称为 IPC 端点或主应用依赖。[路径拼接原始指令](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)

### Inferences
- 普通文件执行层已经比“21 节点 DT_NEEDED 不含 appFw”更接近独立路径：它有真实的本地分派和 libc 文件读写实现。若先决驱动、服务认证和协议状态仍正常，局部文件恢复值得继续研究；目前仍不能承诺它在 appFw 无法加载时可从外部使用。[本地文件层证据](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)
- 某一类服务命令需要 CP/其他进程回应，不意味着所有文件命令都必须经过该 IPC；反过来，本地 helper 不发 IPC，也不能排除它的初始化、上游认证或会话退出依赖其他组件。[独立路径和 IPC 路径对照](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)

### Gaps
- 尚未闭合所有协议命令码到匿名处理器、完整认证状态机和服务生命周期；未证明主应用崩溃后上述本地分支可到达。
- 未追完任意 `/usr/scenario/` 模块及全部 IPC 对端，不能宣布运行时依赖图完全无 appFw。
- 未证明服务访问权限、usr 可写/重挂载、文件替换和可靠退出可以在目标故障条件下完成。

## 2. init2、MODE、BIS、UU 与 WBI 启动各证明了什么？

### Takeaway
原脚本支持一条从磁盘 rootfs 进入 init2、在正常主应用启动前条件式启动 Senser 的路径；这不是 BootROM/热启动 WBI 到该脚本的完整入口证明，也不是外部能够强制建立 `UU` 标志的证明。[原启动脚本](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)

### Cited Findings
- `/sbin/init` 先 source `insmod_drv1`、`setup_nflash`、`setup_rootfs`。`setup_rootfs` 在非 NFS 条件下挂载并 `pivot_root`，之后以 `exec busybox chroot ... /sbin/init2` 继续；`init` 本身也有后续直接调用 init2 的分支。这是磁盘脚本的静态控制流，没有实机启动日志支持。[脚本原文及 SHA](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- `init2` 自行设定 `DEFAULT_MODE=3`，再以可读的 `/setting/mode/dmode` 覆盖。只有 MODE 非字符串 `0` 时，才设置 `/proc/udm/drivers`、source 后续驱动、执行 `setup_bis || setup_senser`，然后后台启动 bootin。`init` 中的默认0不能直接套给 init2；init2默认3也不能当作外部可强制进入恢复的证据。[init/init2 原文](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- `setup_bis` 读取 `/proc/udm/upm_bootmode`，仅等于 `BIS` 才继续；该分支会卸载、`mkdosfs` 格式化并重新挂载 fstab 的 `/log` 分区。成功返回0时 `||` 使 `setup_senser` 不再执行。`setup_senser` 则要求 `/setting/sen/smode` 可读且内容恰为 `UU` 才启动 `sen.elf &`；之后 bootin 也是后台启动，没有等待 Senser 就绪的脚本级 barrier。[init2 条件与副作用](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- `insmod_drv2` 明确包括 OSAL UIPC、`usbg_sen.ko`、`usb_extcmd.ko` 等驱动；fstab 将 `/usr` 从 nflasha15 以只读 ext2 挂载，而 `/setting` 是另一个可写分区。服务可执行文件和多数库与 appFw 同处 usr，不能覆盖 usr 整体不可挂载的故障。[驱动表和 fstab 原文](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- 官方 `/usr/bin/change_mode.sh` 的 usage 明确区分 kernel/global infra/LIRO/appFw 等模式，3标注默认完整启动。但脚本在处理参数甚至 `--help` 前，就可能创建 mode 文件并 chmod，随后各模式会写 dmode/preload，尾部删除额外环境文件。它是有副作用的设置工具，不能当作只读查询来运行。[原脚本与 SHA](../../work/sony-firmware-20261024/stage7-entry/firmware/dynamic-extra.json)
- 原 nflasha5 镜像头是 `WBI2`，本轮 SHA256 为 `ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1`。这证明有该快照格式的分区数据，不证明恢复快照后一定重新运行上述 init2。[镜像原始头和哈希](../../work/sony-firmware-20261024/stage7-entry/firmware/source-manifest.json)
- `libsencore` VA `0x118ac` 是一个持久写入分支：打开 `/dev/nflasha5`，准备512字节缓冲；特定输入条件下将前4字节设为常量 `invl`（原始字节 `69 6e 76 6c`），在 `0x11958` 调用 write。上层明确调用点为 `0x13174`（原字节 `ce f9 ff 97`），从包分派返回 `0x126ec`。分派入口 `0x12630` 读取 packet+`0x24`/`0x26` 的两个16位命令字段；本轮未反解到完整外部命令码。[WBI 写入原始指令](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)、[上层分派回执](../../work/sony-firmware-20261024/stage7-entry/firmware/wbi-caller-static.json)

### Inferences
- “磁盘启动时先起条件式 Senser”支持局部 appFw 故障恢复的研究方向；“WBI 恢复的内存状态是否绕过磁盘脚本”必须单独回答。两条路线不能用同一张 init2 流程图冒充已闭合。[启动脚本与 WBI 分区证据](../../work/sony-firmware-20261024/stage7-entry/firmware/source-manifest.json)
- WBI helper 是显式包处理分支，不能仅凭其存在就认为 `auth.stop` 或普通服务退出会自动失效 WBI；它与主机工具上传 worker 后修改 sysfs 的具体方案也不是已证同一路实现。[WBI 上层调用点](../../work/sony-firmware-20261024/stage7-entry/firmware/wbi-caller-static.json)

### Gaps
- 没有 BootROM/bootloader→内核/ramdisk 或 WBI resume→当前 init2 的完整静态证明；未识别可信的无主应用外部触发路径。
- 没有证明 USB 按键序列、预先存在的标志或硬件维护条件能在所讨论故障下建立 UU 服务，更未验证这个机身的实际状态。
- 未将 WBI 写入 opcode 与任何 Python 服务退出 API 对应，不能据此保证退出自动刷新快照。

## 3. 下一步怎样只做无硬件验证，并隔离会改机身的动作？

### Takeaway
下一步可继续静态闭合“具体协议命令→本地文件分支→服务退出”的调用关系，以及 WBI 的上层分派；无需先执行固件或尝试切模式。已有写入/格式化分支应作为研究对象留在字节与控制流层。[本轮静态复现脚本](../../work/sony-firmware-20261024/stage7-entry/firmware/static_service.py)、[聚焦指令脚本](../../work/sony-firmware-20261024/stage7-entry/firmware/focused_static.py)

### Cited Findings
- 优先目标1：固定 `libsencore` SHA，反解 dispatcher `0x12630` 所读 packet+`0x24/+0x26`，把已知 `0x12884→0x10d3c→0x10994` 文件路径和 `0x13174→0x118ac` WBI 路径各绑定到一个明确命令，保留输入字段检查、失败返回和原始指令字节。它能回答文件恢复与 WBI 是否是独立命令，当前字节回执已提供起点。[调用证据](../../work/sony-firmware-20261024/stage7-entry/firmware/wbi-caller-static.json)、[文件层与完整字节](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)
- 优先目标2：从 `sen` 的 `0x401f80` 核心启动、`0x402b84` 动态入口和 core 的 USB 初始化追踪必需回调、消息队列与驱动对象，区分“注册了可选IPC命令”和“启动必须等待主应用”。当前 sen 的核心启动失败会走 abort，故 `libsencore` 成功加载与接口初始化是真实先决条件。[sen 启动分支](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)
- 优先目标3：只读对照主机协议实现与固件命令分派，分别标注读文件、写文件、模式变更、WBI失效和服务退出，随后才可能设计故障注入验收。已有 `libtestcmd_scn` 和 Host/Subsystem 路径的观察不足以将所有恢复动作归为本地文件路径。[插件与 IPC 索引](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)
- 已识别的持久/设备副作用包括 init2 的 BIS 格式化 log、change_mode 的 dmode/preload/env/权限修改、core 的 nflasha5 512字节写入、文件 helper 的 remove/rmdir/write/sync，以及模式存储函数。它们都未在本轮执行；读取脚本、静态反汇编和计算哈希与这些动作是不同层次。[脚本原文](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)、[模式工具原文](../../work/sony-firmware-20261024/stage7-entry/firmware/dynamic-extra.json)、[WBI与文件调用](../../work/sony-firmware-20261024/stage7-entry/firmware/focused-evidence.json)
- 复现环境复用既有 task venv 的 pyelftools 0.33 / Capstone 5.0.9，本轮没有安装组件。`static_service.py` 和 `focused_static.py` 只解析原始镜像内存映射和 ELF，输出仅进入 stage7-entry/firmware；未读取私人卡片内容、真实机身标识、USB 或 Windows GUI。[来源与方法回执](../../work/sony-firmware-20261024/stage7-entry/firmware/source-manifest.json)

### Inferences
- 值得优先求证的是“usr/rootfs仍可启动而 appFw 局部失效”的窄故障模型。即使这一模型最终通过，也不覆盖 rootfs/usr/内核不可用、存储损坏或完全无 USB 的情况。[同分区与启动先决条件](../../work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)

### Gaps
- 本轮没有实机故障注入、冷启动或 WBI恢复验收，因此不能给出已验证的独立救砖保证。
- 原 bootloader/WBI内部执行入口、外部认证/触发以及全部初始化 IPC仍不完整；在这些边界未闭合前，不应把本轮静态结果视为可刷入授权或安全性证明。
