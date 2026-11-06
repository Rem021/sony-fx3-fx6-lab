# 当前 7.02 NOR Loader2 的早期 updater 条件与 MAIN 观测桥

## 原件能否定位 MAIN 之前对 updater 标志的真实条件消费

### Takeaway

**能定位当前官方包内的原条件消费者：Loader2 包含 partition 2 下 `\updater\mode` 的存在性检查，以及更优先的内存标志 `0xFE170028`。但该文件检查先要求 FAT-ready 与当前 partition=2；本轮没有补全其初始化来源，因此不能升级成“实机每次必读 p2”或“标志存在就已证明能独立救援”。**[原函数](../../evidence/early-selector/mode-file-consumer.txt)；[FAT 前提](../../evidence/early-selector/fat-mount-preconditions.txt)

### Cited Findings

- 源为 stage182 已审计的当前包 `loader_nor.bin`，101,888 字节，SHA-256 `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`。原配置 `pformat_config.txt` 明定 Loader2 `load=0xFE049000`；原开头为 AArch64 指令，绝对指针与该基址相容，不以熵或名字推断密码或可启动性。本文地址均是**按该配置换算的静态装载 VA**，不是机身读回 PC；文件偏移=VA−`0xFE049000`。原末尾版本字符串是 `OT NOR Loader Ver.01.03 (Apr 2 2021 17:22:46)`，表示当前包沿带该成员，不能称为 2026 年新编译 loader。[原配置](../../../stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/pformat_config.txt)；[身份及片段 SHA](../../evidence/early-selector/early-selector-evidence.json)
- `0xFE053C78` 开始的函数先读 cache `0xFE061FE8`：1 返回 true；2 返回 false；其他值读 `0xFE170028`，非零直接返回 true。只有该内存 word 为0才请求 `fat_mount(2)`；失败直接返回 false。[原条件顺序](../../evidence/early-selector/mode-file-consumer.txt)
- `fat_mount` 原入口 `0xFE057F0C` **不是此处完整的硬件挂载实现**：参数须>0、`0xFE06216A` bit0须为1、`0xFE0620F8`须等于参数；只有这些条件成立才返回0。partition不同分支会改记录并报错，不能据函数名默认为已成功装载 p2。FAT-ready 和当前分区在本轮未取得运行值。[原全函数](../../evidence/early-selector/fat-mount-preconditions.txt)
- `fat_mount(2)` 返回0后，`0xFE053CF0–0xFE053CF8` 为原 `\updater\mode` 字符串建立指针并调用 `0xFE057FA0`；返回值的符号位为0即走成功：cache置1且 `0xFE170028=1`，返回true；负值则cache置2、返回false。该调用没有传mode5/mode6，也不读mode正文。原open例程还包含目录/文件名解析与 FAT12/16 配套读例程，因此这里有代码消费，不只是孤立字符串。[条件与写点](../../evidence/early-selector/mode-file-consumer.txt)；[原open](../../evidence/early-selector/fat-open.txt)
- 该成员启动初始化描述表实际清零 `0xFE061E00` 起 `0x1D38` 字节，覆盖上述 cache 与 FAT-ready。描述表原字节记录在证据 JSON，清零 handler 为 `0xFE04C750`。但这只确定 C 启动时初值；后续共享内存、配置记录或别核写入是否建立 FAT-ready，未穷尽，所以本轮不宣布文件检查永不可达。[原初始化代码](../../evidence/early-selector/startup-bss-zero.txt)；[原描述表值](../../evidence/early-selector/early-selector-evidence.json)
- `0xFE054AE4` 的早期 SPI 选择函数中，先检查 byte `0xFE062178`（非零选3），再检查 `0xFE062174`（非零选1）；都为0才调用上述mode存在函数，true选4、false选7，写入待发缓冲 `0xFE062279+1`。它在同一缓冲首字节写 `0x11`，随后调用 `0xFE052348`。这证明**条件输入改变一个原早期通信字段**；这些值是本函数通信字段，不能直接叫 loader enum 或已证明的 p1/p3分区号。[原SPI选择](../../evidence/early-selector/early-spi-choice.txt)

### Inferences

- 比 stage182 更具体：可以排除“当前可见代码中 mode 文件只有历史 updater 内部消费”这一过强概括；当前 NOR 成员存在早期条件消费者。可支持的是**消费者存在及原前提**，不是机身实际命中，也不是独立救砖验收。[消费者与前提](../../evidence/early-selector/mode-file-consumer.txt)；[挂载前提](../../evidence/early-selector/fat-mount-preconditions.txt)
- `0xFE170028` 在本代码中是内存 word，不能凭地址就称为跨断电持久寄存器。它在 `0xFE053308` 会被 UPDATE_MIRA 信号结果覆盖，又在文件成功时置1；本轮未确定掉电域或机身外部输入状态。[信号收集/写点](../../evidence/early-selector/external-signal-collect.txt)；[文件成功写点](../../evidence/early-selector/mode-file-consumer.txt)

### Gaps

- 未补全 `0xFE06216A` bit0、FAT表与 BPB、当前partition `0xFE0620F8` 的初始化生产者及实机状态。故不能把静态 `fat_mount(2)` 调用替代实际 p2 成功访问回执。[精确前提](../../evidence/early-selector/fat-mount-preconditions.txt)
- `0xFE062178`/`0xFE062174` 两个更优先 byte 的生产者未在本轮完整恢复；不能把选3/1分支按名字指定成用户按键组合或强制恢复入口。[原优先顺序](../../evidence/early-selector/early-spi-choice.txt)

## 早期所选 loader mode 怎样进入当前 MAIN 的 upm_bootmode 观测

### Takeaway

**已取得一条真实原字段桥：NOR 把 loader mode 写到 Backup 项 `0x0051000F`；当前 7.02 UPM 从同一项读入 `.bss+0x88`，getter也读同一地址。**该桥说明 MAIN 观测的来源层次，不能倒置成 MAIN 正在生成早期选择；argv5/6、SPI字段4/7、loader enum3也不能混为一套枚举。[NOR写点](../../evidence/early-selector/mode-to-backup.txt)；[UPM同址重定位](../../evidence/early-selector/early-selector-evidence.json)

### Cited Findings

- NOR `0xFE053D20(w0=mode)` 在 `0xFE053D24–0xFE053D48` 将参数作为4字节数据，通过原包装 `0xFE058F50` 写 item `0x0051000F`（第一参数 domain `0x51`）；之后 `0xFE053D8C` 更新本地全局 `0xFE0615D4`，并写 `0x00510037`、`0x00510036` 另两项。`0xFE053D20` 被序列表中 “Copy BM/BF” 对应函数 `0xFE053518` 调用，参数来自 loader上下文 `+0x1B4`。[原写mode函数](../../evidence/early-selector/mode-to-backup.txt)；[原包装](../../evidence/early-selector/backup-write-wrapper.txt)；[序列表、地址、SHA](../../evidence/early-selector/early-selector-evidence.json)
- 当前 AP `upm.ko` SHA-256 `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e`，`k_upm_setup_boot_factor` `.text+0x3CBC–0x3CCC` 调 `Backup_nread(0x0051000F, destination, 4)`。其 literal `.text+0x40F0` 原 `R_AARCH64_ABS64` 重定位指向 `.bss+0x88`；`k_upm_get_ldr_mode` literal `.text+0x34C8` 的重定位也指该地址。这比只按“bootmode”字符串连接更强，但仍非机身运行回执。[UPM原函数](../../../stage182-boot-selector-and-recovery-admission/evidence/boot-request/disassembly/upm.ko-k_upm_setup_boot_factor.txt)；[getter](../../../stage182-boot-selector-and-recovery-admission/evidence/boot-request/disassembly/upm.ko-k_upm_get_ldr_mode.txt)；[独立重定位核对](../../evidence/early-selector/early-selector-evidence.json)
- NOR `0xFE053DFC–0xFE053E10` 用 `mode*8` 索引原固定8字节名字表（file `+0x14F3C`），可确认0 none、1 cold、2 hot、3 updater、4 cipa、5 adjust、6 usbchrg、7 off、8 reboot、9 ontimer、10 warm、11 ss、12 bis、13 loadoff、14 hot off、15 debug。该表是原始loader命名，**5/6在这里不是SD/verskip命令含义**。[索引原指令](../../evidence/early-selector/mode-to-backup.txt)；[逐槽原字节解析](../../evidence/early-selector/early-selector-evidence.json)
- mode全局还有原 setter `0xFE053EB0`。`0xFE059198` 从输入 bootdata结构 `+0x30` 取mode交给该setter；调用者 `0xFE05331C` 先经 `0xFE05C03C` 收取原 SPI 数据，成功后复制该结构并调用 `0xFE059198`。因而至少有一条 mode生产数据来自早期外部通信输入；本轮没有将其远端提供者反编译为一个已命名的 p1/p3选择器。[SPI后结构导入](../../evidence/early-selector/spi-input-and-mode-import.txt)；[+0x30取值](../../evidence/early-selector/bootdata-copy-mode.txt)；[setter](../../evidence/early-selector/mode-global-setter.txt)；[SPI底层接收](../../evidence/early-selector/spi-read.txt)
- 当前 p3 init脚本没有新增p1选择代码：原 `/sbin/init` 装驱动、setup_nflash、setup_rootfs；fstab.root/pivot仍转p7。`init2` 读取 `/proc/udm/upm_bootmode` 只显式比较BIS，并有 `/setting/sen/smode=UU` 启动独立sen.elf；这与 NOR的 `\updater\mode` 是不同文件、不同阶段。sen通道由另一研究员追踪，本轮没有混成救援路径。[当前init](../../../stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-initrd/sbin/init)；[当前init2](../../../stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-initrd/sbin/init2)；[原pivot](../../../stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-initrd/sbin/initrc/setup_rootfs)

### Inferences

- `Backup 0x0051000F` 是现有原件中可以精确对齐的**早期选中状态→MAIN观测**接口；其持久介质、跨断电合同和本机实际值未取得，不能仅因名为Backup便认定为独立持久启动选择器。[NOR写点](../../evidence/early-selector/mode-to-backup.txt)；[UPM读点](../../../stage182-boot-selector-and-recovery-admission/evidence/boot-request/disassembly/upm.ko-k_upm_setup_boot_factor.txt)
- 正常AP `ud_send_lsi.elf` 的 argv5/6 请求消费者由另线负责；本轮没有把该消息参数等同于以上loader enum。即使日后队列消费解释为reset，也还须验证reset后远端bootdata `+0x30` 与加载路径。[先前helper原参数证据](../../../stage182-boot-selector-and-recovery-admission/research_notes/FX3%20恢复启动%20版本准入/boot-request.md)

### Gaps

- 尚无 SPI bootdata `+0x30` 的远端原生产函数、输入4/7到该字段的转换、或真实机身消息。不能从 NOR发送字段4/7直接宣布“4=p1、7=p3”。[字段消费者](../../evidence/early-selector/early-spi-choice.txt)；[mode导入](../../evidence/early-selector/bootdata-copy-mode.txt)

## p1/p3实际镜像选择、外部输入与失败回退还缺哪段原证据

### Takeaway

**当前精确缺口已经缩小到早期通信输入的mode生产者及实际镜像装载数据，不能再用一个“mode函数未找到”概括。**原NOR还识别了按描述表装载文件的消费者，但表内容来自Backup项而非该NOR中的硬编码p1/p3；未取得记录值就不能把普通加载、off加载和 updater恢复混在一起。[配置record消费者](../../evidence/early-selector/config-record-consumer.txt)；[mode输入](../../evidence/early-selector/bootdata-copy-mode.txt)

### Cited Findings

- NOR `0xFE0545DC` 从 Backup项 `0x00FA0080` 取配置记录到 `0xFE208000`；每条步长`0x90`，`+0x10`作partition参数、`+0x14`作匹配flags、`+0x18`作文件路径。原循环比较 `(record.flags ^ caller_flags) & 0x00F00000`，匹配后才处理，`0xFE05479C`/`0xFE054950` 把record分区交`fat_mount`。当前可见两个直接caller在 `0xFE0530B8`，是loader enum13/14的off/hot-off分支；不能把它自动升格为正常 p1/p3入口。[原record读取/过滤/参数](../../evidence/early-selector/config-record-consumer.txt)；[caller与序列地址索引](../../evidence/early-selector/loader-all.txt)
- `0xFE0542CC` 对 `0xF102E008` 写2，并写同基址`+0x1C`，读取`+8`（即`0xF102E010`）的bit1，日志原名 `UPDATE_MIRA [17-1][0xF102E010]`；`0xFE054208` 根据Backup `0x00F909D5`/`0x00F909D6` 取得端口/bit后读GPIO，原日志名 `DEBUG_MODE_SW`；`0xFE0541B0` 读`0xF1388F10` bit2，日志名 `BOOT_EXT(SPI_BOOT_MODE)`。这是可证的外部电平/启动信号读取，**没有证明对应任何用户可按按钮、USB插线组合或无需拆机的恢复操作**。[原信号读取](../../evidence/early-selector/external-signal-read.txt)；[原收集与内存写点](../../evidence/early-selector/external-signal-collect.txt)
- `0xFE0529F8` 的kernel跳转前路径明确读Backup `0x00510020` 并写回：loader mode2或10时置0，其他mode把读值加1；mode3在函数开头绕过该路径。该片段只证明一个分支计数值存在，未在此处看到“达到N自动选p1”。不能把日志 `NR_RES` 或 `ERR` 字样当作自动恢复证明。[原counter分支](../../evidence/early-selector/kernel-jump-counter.txt)
- 当前包完整定义结构没有 p1载荷，历史p1不能自动充当本机当前p1；本轮不重复包审计、不改旧stage。此次只新增17段原指令片段、原名字/序列表和UPM重定位的独立复核；源loader写前/后SHA相同，volume UUID在写入前再次匹配；宿主解析未运行Sony代码。[本轮证据manifest及操作边界](../../evidence/early-selector/early-selector-evidence.json)；[既有完整包范围](../../../stage182-boot-selector-and-recovery-admission/research_notes/FX3%20恢复启动%20版本准入/current-updater.md)

### Inferences

- 下一份有用原代码/数据不是再次泛搜“FX3救砖”：第一是产生 SPI bootdata结构`+0x30`的原远端函数及该交换实际载荷；第二是独立装载器选 p1/p3 的真实描述/分区函数，`0x00FA0080`原record是一个具体可查候选，而当前已解析函数只直接出现于off分支，不能预设它覆盖通常冷启；第三是FAT-ready/partition2初始化合同。当前没有取得这些原件。[精确代码接口](../../evidence/early-selector/bootdata-copy-mode.txt)；[record候选及适用边界](../../evidence/early-selector/config-record-consumer.txt)
- 外部信号、计数写回、mode存在、Backup所选状态构成多个输入/状态层；任一个局部成立都不能替代“MAIN失效时独立updater成功启动并回装”的最终验收。[信号](../../evidence/early-selector/external-signal-read.txt)；[counter](../../evidence/early-selector/kernel-jump-counter.txt)；[mode条件](../../evidence/early-selector/mode-file-consumer.txt)

### Gaps

- 未证明当前同机p1身份/可用性、p1/p3实际选择、远端mode生成、USB-only无MAIN恢复入口或自动失败回退阈值；没有进行相机/USB/管理员/Windows/UU/GUI/串口/Pico动作，也没有执行固件或原脚本、仿真、构建、安装、新增巨量下载、修改原件/README/GOAL/memory。[本轮范围](../../evidence/early-selector/early-selector-evidence.json)
- 2026-10-29 对Sony官方7.02说明页的新联网fetch超时；本文未据失败fetch添加任何官网事实。当前包身份沿用已有原下载/整包审计，本轮直接重新核验NOR/UPM源哈希。官网是否另提供独立救援入口不在此次静态原证据结论内。[已有官方页引用与审计](../../../stage182-boot-selector-and-recovery-admission/research_notes/FX3%20恢复启动%20版本准入/current-updater.md)；[新源身份核对](../../evidence/early-selector/early-selector-evidence.json)
