# FX3 7.02 独立 sen 的命令能力与恢复边界

## 独立模式到底使用什么协作者，认证后发布哪些命令？

### Takeaway

独立 `sen.elf` 确实有自己的 `WorkerThreadManager`，认证完成后发布分等级的真实命令表；它与普通 `im.elf/libObj` 传入的 `Senser::SenUsbIf` 协作者不同。文件命令名称存在于调整命令表，但其消费者仍须逐条证明，不能由目录存在推导独立恢复。[原构造器、虚表、命令表与重定位](../../evidence/standalone-commands/command-tables-and-relocations.json)、[原函数与字节哈希](../../evidence/standalone-commands/selected-original-functions.json)

### Cited Findings

- 本轮原件均为既有官方 FX3 7.02 包的静态提取文件，非相机读回：`sen.elf` SHA-256 `9e3236666176b69746848edaac31e1e0ef00c4e80a9f062794ff62be2d605470`；`libsencore.so` 为 `a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410`；`libtestcmd.so` 为 `a6fcb217753d7315abafaf15b8b56dd3106d198e68785c434b3b641862ca1cc6`；`libJiritsu.so` 为 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`。本轮使用现有 Python 的 ELF/Capstone 主机解析器，未加载、执行任何 Sony ELF、脚本或 guest。[完整来源登记](../../evidence/standalone-commands/sources.json)、[分析脚本](../../evidence/standalone-commands/analyze_static.py)
- `libsencore+0xaeb4` 全局构造器把 `WorkerThreadManager` 虚表 `0x6a5e8+0x10` 写入对象 `0x6ba30`，把两条线程槽设为 `-1`；虚表的接收、发送、Hasp登记、完成回调槽分别重定位到 `0xc0f0`、`0xc0fc`、`0xc190`、`0xc108`。`senser_usb_mode_start+0xb094` → `SenserIfStart+0xceb0` → `Usb::handle_input+0xcc1c` 确实使用这个对象。[原构造器/FDE](../../evidence/standalone-commands/selected-original-functions.json)、[原虚表和 GOT](../../evidence/standalone-commands/command-tables-and-relocations.json)
- `start_authentication+0xc328` 清空 `pFunc`，保存完成回调并以原 `NinThread+0xbbfc` 启动线程；`NinThread` 通过协作者虚槽 `+0x28` 调 `onComplete(level)`。`onComplete+0xc108` 的实际选择为 level 1 → C 表 `0x6b8f8`，level 2 → B 表 `0x6b8b8`，level 3 → A 表 `0x6b848`，其它值清空表。不是认证任意完成就得到全部命令。[原认证与完成函数](../../evidence/standalone-commands/selected-original-functions.json)、[三表原字节与重定位](../../evidence/standalone-commands/command-tables-and-relocations.json)

| 等级 | 外层命令表中的原槽 |
| --- | --- |
| 1 / C | `0x40 AdjustControlFunc` |
| 2 / B | `0x40 AdjustControlFunc`、`0x10 ProductInfoFunc`、`0x20 FirmwareUpdateFunc` |
| 3 / A | 上述三项，另有 `0x30 MiconAccessFunc`、`0xff00 TestMode`、`0xff02 SonarFunc` |

表中 `FirmwareUpdateFunc+0xec08` 原函数只有 `mov x0,0; ret`；不能把此槽当作独立固件更新实现。`TestMode` 转 FIFO `/var/fifo/sen_host_req/res`；`SonarFunc` 则动态寻找 `libSnr.so/Sonar_Packet`，本轮没有证明这些提供者在损坏态存在。[原表与函数](../../evidence/standalone-commands/command-tables-and-relocations.json)、[原动态/FIFO路径](../../evidence/standalone-commands/libsencore.so-text.txt)

- 调整命令表位于 `0x17698`，共 `0x6c6` 行、每行 `0x48` 字节，原 `TransactionStart+0xfb0c` 自己按这个步长查表。`0x31b58/0x31ba0` 为 `JIRITSU_SET_FILE/GET_FILE`；`0x31d98/0x31de0/0x31e28` 为 `SET_FILE_PATH/SET_FILE2/GET_FILE2`，均为 command `0x1001`，低子码依次 `7/8/f/10/11`，表限制位为 `0x4000`，queue 均 `0x016f0480`。实际名称为 SET_FILE，没有发现这组里另一个名为 PUT_FILE 的入口。[选定原行](../../evidence/standalone-commands/command-tables-and-relocations.json)
- 外层 `Parse+0xe9f4` 只接受当前 `pFunc` 中的命令。内层 `0xfd9c..0xfe58` 还比较表项低子码、限制位和 `adjCodeLevel`：对 JIRITSU 的 `0x4000` 表项，level 1 被拒，level 2/3 可以通过这段局部检查。请求子码中的 `0x1800` 路由位另选直接 IPC、`testcmd_sndmsg` 或 scenario；它不是上述等级位，不能从字符串前的 `@` 猜执行方式。[原两级分派](../../evidence/standalone-commands/selected-original-functions.json)

### Inferences

- level 2/3 的局部准入使文件服务值得继续取证，但不构成真实认证成功、queue存活或文件恢复完成证明。普通协作者已有实型证据仍只适用于普通 NIN 路径。[本轮命令分派](../../evidence/standalone-commands/selected-original-functions.json)、[既有普通协作者](../../../stage149-normal-cooperator-and-NIN-checkpoint/normal-cooperator-static.json)

### Gaps

- 本轮没有实际认证等级、当前对象/驱动状态或损坏态运行回执；等级值可选表这一静态事实不保证真实 USB 会话进入对应等级。

## GET/SET 文件与备份还原能否在 MAIN 进程失效后独立完成？

### Takeaway

本轮没有闭合独立文件恢复，反而找到了明确的跨进程消息依赖：`testcmd` 分支并不装入 `libJiritsu`，它仍向 `0x016f0480` 发同步消息；已定位的该 queue 消费者由 `im.elf` 的 IMDB 装载路线初始化。即使独立 USB 进程仍活着，也不能据此保证 `im.elf` 已死时能够 GET/SET appFw 或 av-cam。[提供者依赖回执](../../evidence/standalone-commands/provider-dependency.json)

### Cited Findings

- `TransactionStart+0x100b8..0x10130` 的 `testcmd` 分支先调 `testcmd_init`，再把选定表行 `+0x44` 的 queue 交给 `testcmd_sndmsg`。原 `libtestcmd+0x1e1c` 只清空 40 字节结构；`+0x1e3c` 分配/填充 OSAL 消息，`+0x1eb8` 调 `osal_snd_sync_msg`。该路径没有 `dlopen`、`jiritsu_init` 或创建 Jiritsu线程；“testcmd分支”等同“进程内文件处理”是错误推论。[原调用者与两个提供者函数](../../evidence/standalone-commands/selected-original-functions.json)
- `libJiritsu+0x6d74 jiritsu_init` 在 `0x6da0..0x6dbc` 注册 queue `0x016f0480`，回调是 `0xb278`。回调的 `GET_FILE2` 分支经 `cmd_high_capacity_get_file+0xb0ac`，在 `0xb20c` 调原 `adj_cmd_get_file2+0x9e74`；SET_FILE2 则位于同库 `0x9528`。这才是实际文件实现，服务文件本身仍须存活并已初始化。[原消费者/包装器/文件函数](../../evidence/standalone-commands/selected-original-functions.json)
- 原 IMDB 行 `0x1d8e8` 为 `libJiritsu.so / jiritsu_init`，type `0x20000001`、me `0x16f`、alias字段 `+0xe=0`。既有原 `im.elf+0x40625c..0x406270` 为该类型选择 `0x405f5c`，alias为0时保留表中库名，再经 `dlopen/dlsym` 调入口；这把已定位的 Jiritsu初始化置于 `im.elf` 装载域。`CImJiritsu::init+0xb5dc` 另建自己的 OSAL 线程，但那是库被初始化后的同进程线程，不是独立 ELF 进程。[原 IMDB 行/来源哈希](../../evidence/standalone-commands/provider-dependency.json)、[原 im 装载器](../../../stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/disassembly/im.elf.txt)、[原Jiritsu线程创建](../../evidence/standalone-commands/selected-original-functions.json)
- 独立 `sen.elf+0x401f80` 的已追 startup 在 `0x402b84` 打开 `libsencore`、查 `senser_usb_mode_start`，随后 `0x402010→0x402c94` 查并调用 `sens_adjCmd_init`。该入口 `libsencore+0x13200` 注册的是 queue `0x003d025f`、回调 `0x12630`，不是 Jiritsu 的 `0x016f0480`。原静态依赖闭包也不含 `libJiritsu`；本轮未发现这条独立启动路径替它调用 `jiritsu_init`。[原独立启动与自身注册](../../evidence/standalone-commands/selected-original-functions.json)、[已核对静态闭包](../../../stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/static-dependency-closure.json)
- 独立注册的 `READ_SSBI` 与 `READ_NFLASHA8` 确实走自身回调到 `0x1231c` 的 open/flock/mmap 路径，但原数据记录 `0x6b9a8/0x6b9c8` 只绑定 `/dev/nflasha5` 和 `/dev/nflasha8`。它们不是任意分区读取器，也没有在该固定记录中提供 p15 appFw 或通用写回/还原。[固定设备记录与重定位](../../evidence/standalone-commands/command-tables-and-relocations.json)、[原固定读取函数](../../evidence/standalone-commands/selected-original-functions.json)
- `GET_FILE2+0x9e74` 本轮重读确认：kind 0/1 选挂载及路径，路径缓冲 `0x202`；variant在 `msg+0x2a`，仅接受0/1。实际长度由 stat 的64位N导入，在 `0xa134/0xa13a` 做32位 `(N+4)` 或其二倍，`0xa1bc` 把读取长度收为low32(N)，随后一次 `CFileAccess::read`。`0xa200` 按32位比对；短读走 `0x1000000a`，stat/open/DMM等分别有内部错误，外函数仍可在 `0xa000` 返回0。此原函数不是带offset/count的文件范围读取合同。[本轮原函数/FDE/哈希](../../evidence/standalone-commands/selected-original-functions.json)、[既有长度与错误分层复核](../../../stage157-original-whole-file-read-length-and-status/README.md)
- selector相关路径可从保存的 `SET_FILE_PATH` 状态拼接文件名；kind0/selector3且有待处理日志时，`0xa058..0xa0d8` 会打开日志路径、写待处理字节、fsync/close/sync并把后续stat改为日志路径。因此 GET_FILE2 整体不能笼统标为零写入。[原日志与路径分支](../../evidence/standalone-commands/selected-original-functions.json)

### Inferences

- 若 `appFw` 故障杀死整个 `im.elf`，同地址空间的 Jiritsu消费者也不会因独立sen还活着而自动继续；若只是appFw装载失败而im尚存，是否仍完成Jiritsu登记须另证。本结论不能扩大为“任何appFw损坏都绝对无法读取”，也不能扩大为“MAIN坏后必能恢复”。[原共同装载器与独立队列边界](../../evidence/standalone-commands/provider-dependency.json)
- 文件恢复候选现在缺的是独立提供者启动/最小依赖设计，而非再寻找命令名称。完整 `libJiritsu` 初始化还会建立JIT相关线程和资源，因此单独在sen里补一次 `dlopen` 也不能视为已经获得安全恢复服务。[原初始化与线程](../../evidence/standalone-commands/selected-original-functions.json)

### Gaps

- 尚未证明任何不依赖im的 Jiritsu初始化路线；没有把其全部Fsys、DMM、backup/OSAL、LIRO/av-cam下游依赖闭合，也没有原 appFw/p15 写回、完整备份或还原回读实测。
- 当前固定原函数没有范围参数；库中存在seek导出不等于有可达的范围协议。下一份最小读取合同仍需证明固定小文件、明确路径语义、设备侧分配/读取上限、完整长度和内外状态，而不能用主机USB分片替代设备侧约束。

## 模式标志与系统寿命还有哪些独立能力，下一步最小缺口是什么？

### Takeaway

独立sen自己登记的 `SEN_MODE` 具备直接POSIX模式文件操作，认证尾部也存在持久状态写入；这些能力与appFw文件还原不同。UU早启仍会继续启动bootin/im，worker启停还有UPM同步通知，整体故障看护和冷启动寿命仍未证明。[自身回调与模式写入](../../evidence/standalone-commands/selected-original-functions.json)、[UPM与提供者表](../../evidence/standalone-commands/provider-dependency.json)

### Cited Findings

- `SEN_MODE` 原行为 `0x601/0x11` → 自身 `0x12630` → `0x10d3c`。`0x10898` 选择存在的 `/setting`，否则 `/boot`，拼 `/sen/smode`；操作helper `0x10994` 用POSIX读取、mkdir/open/write/remove/rmdir/sync。写入分支 `0x10fec..0x11018` 把 `UU` 连NUL的3字节交给创建/写入helper；清除分支 `0x10ed8..0x10fb8` 还清 `/mode/cmode`、`/mode/tmode` 及smode/目录。这段不经Jiritsu消费者，但目标不是p2的 `updater/mode`，也不表明会立即重启或完成恢复。[原模式回调/路径/文件helper](../../evidence/standalone-commands/selected-original-functions.json)、[原模式字面量](../../evidence/standalone-commands/command-tables-and-relocations.json)
- `NinThread+0xbe94` 经协作者调用 `registHaspId`，独立槽 `0xc190` 转 `Regist_HaspId+0x142f0`；在已有Hasp历史且读取成功等条件下，`0x14468..0x144ec` 会写 `/setting/.hasp` 并sync。`NinThread+0xbf30..0xbf4c` 在已有 `.etools` 时可更新日志，原 `tlog_write_file+0x13660` 以 `wb` 写 `/setting/.etools`。尾部level3还可创建/写 `/ramdsk/dev/mode`，其它等级有remove/rmdir。文件读取任务不能因此把认证过程记为零写入。[原认证尾部与两类持久写者](../../evidence/standalone-commands/selected-original-functions.json)
- `Usb::handle_input+0xccd4..0xcd0c` 收到认证完成事件后，先以 `0xc444` 同步通知 queue `0x80924220`、消息首字 `0x00920203`，返回后即使非零也只记日志并调用 `run_workers`；停止分支用 `0x00920202`。原IMDB的group `0x92` 对应 `/kmod/upm.ko`。本轮只证明这条真实同步依赖及错误后继续分支，未证明目标队列缺失或UPM等待下游时一定及时返回。[原通知与worker启动](../../evidence/standalone-commands/selected-original-functions.json)、[原UPM登记行](../../evidence/standalone-commands/provider-dependency.json)
- 原 `init2` 的 UU 分支只增加 `sen.elf &`，之后仍执行 `bootin.elf &`。本轮 `bootin.elf` SHA-256 `dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2`：main `0x4017e0` 调 `0x402b90` 组装启动命令；`0x402e84..0x402e8c` 交给fork/exec包装器，`0x401cb4` 另有明确 `/usr/bin/im.elf` fork/execv入口。`0x4030c4` 的SIGCHLD相关代码只循环 `waitpid(...,WNOHANG)`；不能据它排除UPM/内核/其他服务整体复位。[原init2](../../../stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/sbin/init2)、[bootin原代码](../../evidence/standalone-commands/bootin.elf-text.txt)、[bootin来源哈希](../../evidence/standalone-commands/sources.json)

### Inferences

- 真正最小的下一研究切口是：先证明目标命令提供者可达，再定义固定小目标的范围与错误合同；同时证明worker前UPM同步通知在im/av-cam故障下能完成。本结论不进入p1读取或标志写入。现有自身模式命令与固定p5/p8读者可单独分析，却不能替代appFw/p15恢复。[已闭合依赖及未闭合边界](../../evidence/standalone-commands/provider-dependency.json)
- 后续仅RAM实验应按它实际会触及的模式、认证历史和日志状态定义副作用与回退合同；不把每个RAM实验一律升级为整eMMC备份要求。任何持久标志或恢复写回方案仍须明确逐对象原值、备份、恢复与授权范围。本轮没有制定或执行新设备方案。

### Gaps

- 尚未证明smode=UU抑制watchdog、抑制MAIN启动或改变UPM看护；本轮没有完整追入upm.ko/内核看护状态机。仅“bootin未见smode字符串”不是充分否定证明。
- 没有相机、USB、管理员、Windows、UU、GUI、安装、构建或guest执行；只新增本目录静态证据及本笔记。已核对目标卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；旧stage、原件、canonical、README和memory未改。[可复核分析/封存脚本](../../evidence/standalone-commands/analyze_static.py)、[44段原函数与证据清单](../../evidence/standalone-commands/manifest.json)
