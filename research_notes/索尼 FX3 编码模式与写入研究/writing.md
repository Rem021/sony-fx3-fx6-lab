# Sony 局部补丁写入与恢复源码审计

## 其他人实际怎样写入，哪些安全机制可以借鉴？

### Takeaway
A7C II 的实用路线是先进入 Sony 服务通道，再执行临时本机模块，对现有程序做固定窗口写入；不要求先把修改后的 UFU 重加密成原厂卡刷包。可借鉴的是明确的机型和整文件指纹、每个改动窗口的原字节、原文件备份、写后全文件读回、阶段记录与冷启动检查，不能将现有“还原”当作独立救砖通道。

### Cited Findings
- 审计基准为 QAQLeonard `9f69e9dc59ef2cfbc3334bee977b7529aaee04b8`，本轮查询 HEAD 已到 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`，重新下载比对 installer.c/core.py/workflow.py/wbi.c 四文件字节均未改变。MDHan HEAD 仍为 `41950d3eab53e0b801f315af07505a2d0d3f76af`，YuuLuo HEAD 仍为 `1619f938663a36d41e72302a8cfee89a0f6acd1a`。按项目约定，审计后的第三方参考源码副本已删除，仅保留固定 URL/提交、摘要、审计回执与自写脚本；原厂固件提取证据未删除。下载 URL、尺寸、内容 SHA-256 存在[来源回执](../../work/sony-firmware-20261024/stage2/write-audit/source-receipt.json)。[最新固定 installer](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/installer.c)
- `core.py` L12–19 固定 ILCE-7CM2/2.01 及 AP/CP 原版和目标整文件 SHA-256；L55–73 的 patch_program 先查整文件，再查每个窗口旧字节、等长、范围、无重叠，最后核对候选整文件 SHA-256。不能只用某处字节碰巧相同作为版本匹配。[core.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/core.py#L55)
- native installer L84–99 确认常规文件、固定大小、inode/dev 身份及窗口内容；L121–150 先只读检查，再重挂载 `/usr` 为 rw，再次检查后写固定窗口。`/cp/cpapp-b.bin` 与 `/usr/lib/appFw.so` 是白名单目标。没有开放任意文件或任意地址写入。[installer.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c#L84)
- `patch()` L101–109 使用 pwrite 逐个窗口改原 inode，之后对两个文件分别 fsync、再次读回。失败时 L145–147 尝试逆序写回进入此次操作前的窗口并核对。L157–161 关闭文件、恢复 `/usr` ro 并保存结果。它不是双槽更新，也不是整文件原子 rename。[写入与回滚](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c#L101)
- 宏 `BYTE_WINDOWS_ONLY` 会让 native `verify_hashes()` 仅比较窗口，源码注释要求 host 完整读回；不能假定每一种构建在机内都做了全文件 SHA。主机 `files()` L208–219 对 AP/CP 全文件读回并核对哈希，作为独立门禁。[native 宏分支](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c#L111)、[host 完整读回](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L208)
- 安装编排顺序是备份与原版核验→WBI 只读诊断→局部程序写入→完整程序读回→保存选定设置并检查保留项→失效旧 WBI→正常退出服务→冷启动→文件、保存设置与运行内存核验。电量 50–100 是传入值门禁，不能当成自动测量电池或安全保证。[install/verify](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L302)
- MDHan 的 prepare L174–243 为每机身记录身份，保存 AP/CP 完整文件、当前与已保存参数、直接单元读回；新文件采用 O_EXCL/O_NOFOLLOW、0600、flush/fsync 和读回检查。支持可选第二目录，默认一份；同一 Mac 上的两份也不等于物理容灾。候选会反向还原并逐字节等于原文件。[Mac prepare](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/macfl23/workflow.py#L174)
- MacSession 绑定机型、机身序列摘要与同一 USB 物理端口；两次服务认证；I/O 异常或中断后会话标为未知，禁止继续命令。状态机将主体完成但普通 USB 返回未确认，与未知写入失败分开，不能盲目重试。[session.py](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/macfl23/session.py#L79)、[状态机](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/STATE-MACHINE.md)

### Inferences
- 固定窗口、保持 inode 是有意识地缩小改动面，不能解释成断电原子性。进程还活着时的错误回写，与掉电、断线后不可再次执行的恢复是两种能力。窗口之间、AP 与 CP 之间、程序与参数之间都存在中间状态；fsync 不能把多文件多设置事务变成原子操作。
- FX3 应借鉴检查策略而非复制偏移：将其自己的型号、实际程序全哈希、目标语义、窗口和目标哈希作为新补丁规范。不同程序版本上的原字节偶然相同不足以许可写入。

### Gaps
- 这些检查不是 FX3 7.02 的实机安装验收；本轮没有连接相机、没有调用服务命令，也没有运行第三方安装器。

## 还原功能怎样工作，哪里仍可能无法恢复？

### Takeaway
现有 restore 依赖相机仍能启动到可用的服务程序、完成认证并执行临时模块。它能恢复已识别的正常原版/已安装状态，不提供已证明的断电后任意损坏恢复。

### Cited Findings
- QAQLeonard `program_state()` L221–239 要求两个程序都具有已知原版或已安装整文件哈希，且状态一致；未知哈希或 AP/CP 一新一旧时立即停止。`restore()` L367–394 先确认本机备份与服务身份，再恢复目标设置、按 mode2 反写原字节、完整读回和处理 WBI。[状态判定](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L221)、[restore](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L366)
- WBI worker 在诊断时要求 image_mode 为 2、image_dev 为 `*wbi4`；实际处理只调用厂商 sysfs 的 image_drop=1、image_mode=0，并核对新鲜 `dropped wbi` 日志，未自行覆盖原始块。它失效旧开机快照，以便冷启动重新装载程序。[wbi.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/wbi.c#L31)
- MDHan 验证记录明确恢复实际未测试，断电/断线救援未测试；已实测范围包括一台机身的特定升级、专项 WBI、冷启动和部分功能，不能扩展为所有安装和故障分支通过。[验证记录](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md)、[恢复说明](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/ADVANCED.md)

### Inferences
- 若补丁破坏了进入服务流程必需的主程序，普通服务 restore 也可能到不了；“备份存在”不能使入口重新出现。未知或部分写入状态还会被当前还原工具主动拒绝，而非自动修复。
- 保留原版程序和参数是必要恢复材料，但不同于完整存储芯片、机身校准及独立 BootROM/硬件恢复能力。官方更新能否在某种损坏状态启动也要按具体状态验证。

### Gaps
- 未找到 FX3 7.02 对应的独立于被修改主程序、经过真实失效测试的恢复通道。
- 未证明用户机身当前 WBI 模式、设备标识、可操作 sysfs、服务执行特权与 A7C II 相同；这些不能仅因 FX3 包内存在 WBI2 推出。

## FX3 7.02 是否保留可以借鉴的本机临时加载入口？

### Takeaway
不再只是按机型相近推测：本轮对官方 FX3 7.02 的 `libJiritsu.so` 做了静态控制流检查，确认存在与 A7C II 当前上传路径直接对应的“写 libJit.so 后调用标准 dlopen”分支。它缩小了适配未知范围，但没有证明用户机身已允许认证、执行任意模块或获得 root。

### Cited Findings
- 由原厂包提取的 `/usr/lib/libJiritsu.so` 为 AArch64 ELF64，225200B，SHA-256 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`。带原始指令字节、函数地址、PLT 映射的[本次静态回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)可复核，源分区另通过官方 CRC。[提取完整清单](../../work/sony-firmware-20261024/stage2/extraction/supplementary-extracted-manifest.json)
- A7C II 当前 host `module()` 上传临时结果/请求文件和 `libJit.so`，读回原生 worker 结果，检查清理；`temp()` 把文件控制参数设为 `00 ff 00`，最大 host 临时文件 65536B。它不是 YuuLuo 文档中的单独 DEBUG/preload 触发叙述，不能把两条具体入口混成一条。[module L84–133](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L84)、[temp L173–184](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/transport.py#L173)、[YuuLuo 的不同研究链](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/README.md)
- FX3 `adj_cmd_set_file_path` VA `0x89b4` 长292B，先检查路径长度（包长约束）与参数类型，拷贝路径、将反斜杠改斜杠并过滤部分控制字符。`get_access_filename` VA `0x92e8` 长292B，在 selector=0xff 时取已保存路径：已含 `/tmp/jiritsu` 前缀者进入 snprintf `%s` 路径，在该函数未见 realpath/规范化 `..`；这解释为什么相似的遍历选择有静态适配依据，不是本轮设备操作结果。[本次指令回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)
- FX3 `adj_cmd_set_file2` VA `0x9528` 长1120B，`00 ff 00` 参数选 Work 挂载＋已选路径＋原始文件写入。该函数拒绝直接写 `jit.log`/`history.txt`，当目标精确为 `/tmp/jiritsu/libJit.so` 时还检查 `/tmp/jbusy`，执行目录准备、包数据和打开/写入检查，正常写入后 CFileAccess fsync、close；随后约 VA `0x98d0–0x9928` 的精确路径分支调用 dlopen(path,1)，成功后 dlclose。不能省略这些条件，仅称“有 dlopen 字符串”。[本次指令回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)
- 该 dlopen 是 `.rela.plt` 中的未定义动态导入，版本索引映射到 `libdl.so.2: GLIBC_2.17`，不是在此函数中调用的定制“验签加载”接口。这不证明运行时没有符号覆盖或其他上游 gate，也不证明所有 ELF 都会被正常接受。[动态依赖与 PLT 回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json)

### Inferences
- 如果在 FX3 7.02 上另行验证服务认证、参数协议与执行权限，后续研究有可能走“临时模块→最小本机补丁”的路径，无需以重新签名整包为唯一前提。当前静态事实比“不同机型所以不能借鉴”更积极，也更具体。
- 先做不改持久程序的最小诊断模块，只有输出结构化、带模型与原版指纹的结果并验证临时清理，才有依据继续；这一阶段仍会向相机上传和执行代码，不能称为完全无设备风险或已经获准执行。

### Gaps
- 本次未验证用户 FX3 的两次 Senser 认证、服务包接受、libJit 实际加载、调用方 euid、文件系统权限、清理和正常返回 USB 身份。没有向相机发出任何命令。
- 当前只有对接收函数的静态分支分析，不是完整服务认证调用图，也未审计所有导入函数和运行时动态链接环境。

## 已用真实 FX3 文件验证哪些 A7C II 安装门禁不能照搬？

### Takeaway
编写了只读移植审计器，实际比较提取的 FX3 AP/CP 文件与固定 A7C II 补丁规范：型号、固件、两份整文件指纹均不匹配；窗口也有越界和旧字节不符。它明确拒绝原样移植，不生成候选、不修改输入，也不包含 USB 代码。

### Cited Findings
- FX3 appFw.so 为79015712B，SHA `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；cpapp-b.bin 为15980568B，SHA `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。对照 A7C II patch spec 的8个 AP 窗口和32个 CP 窗口：AP 有5个窗口旧字节匹配但2个越界，CP 有0个窗口旧字节匹配且1个越界；整体 gate 拒绝。5处匹配包括相同字节或填充窗口，不足以证明功能适用。[本次完整比较结果](../../work/sony-firmware-20261024/stage2/write-audit/fx3-vs-a7c2-compatibility.json)、[固定公开补丁规范](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/assets/patches.json)
- 自写 [audit_patch_portability.py](../../work/sony-firmware-20261024/stage2/write-audit/audit_patch_portability.py) 只读取常规文件，先核对公共 spec 的固定 SHA，再核对规范结构、无重叠、每个窗口边界/旧字节与全文件指纹，检查输入审计期间未改变；报告输出限于脚本同目录的新 JSON，`camera_write_allowed` 永远为 false。已在真实 FX3 提取文件上执行，未应用任何窗口。[脚本与实际回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-vs-a7c2-compatibility.json)

### Inferences
- 可直接移植的是校验原则，不能直接移植 A7C II 偏移、目标字节、WBI 条件和恢复规则。FX3 专用补丁必须以新程序哈希和已解释的编码逻辑重新制定。

### Gaps
- 这个审计器不是 H.265 补丁，也没有产生可刷文件；仍需编码研究分支证明一个具体最小改动的语义和运行效果。

## FX3 下一步的最小验证条件是什么？

### Takeaway
应把“找到编码补丁”和“具备写入/恢复路径”分开推进，同时保留最小改动。服务临时加载的静态结构已找到；目前还不能为主力机交付可靠安装包。

### Cited Findings
- 当前 A7C II 原生 worker 首先验证 euid=0、只读挂载、文件大小/身份与原字节；主机还要求原版/候选全文件和目标保存参数一致。FX3 的静态临时加载路径不自动满足这些条件。[worker 前置条件](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c#L121)
- Mac 实际验证记录区分磁盘候选已更新、内存仍为旧内容；只有真实冷启动后内存和磁盘均匹配才进入完成状态，说明只看写后文件不够。[实机记录](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md)

### Inferences
- 进入任何 FX3 临时执行前，最小前置条件应包括准确机身型号/实际固件身份、与本次官方包的程序指纹关系、服务协议及调用权限的只读核验；诊断模块限定只读、固定版本/输出结构、禁止原始块和持久设置/程序写入，失败不自动重试。即使如此，也不能在未验证时称其保证安全。
- 真正写入前还需针对 FX3 的恢复入口可达性和具体补丁效果证据。软件层可借鉴原版保留、候选与反向候选全哈希、固定范围、全读回、阶段审计、故障拒绝与冷启动核验；断电安全不能由这些检查凭空获得。

### Gaps
- 独立主录 1080p29.97/30 HEVC 的具体改动由编码分支继续分析；这里没有伪造偏移或提供试刷命令。
- 公开 A7S III 快门角度案例源头仍是媒体转述的单一读者反馈，描述只改持久设置、固件未改，不能拿来证明 FX3 编码程序修改和掉电恢复。[原始媒体来信，仅作线索](https://www.sonyalpharumors.com/new-shutter-angle-hack-works-on-the-sony-a7siii-too/)


## 能否静态证实主应用损坏后仍可进入独立恢复通道？

### Takeaway
发现了有价值的“主启动前条件服务分支”，所以不能断言一切服务都必须等 appFw 成功启动；但本次仍没有证实一个在 appFw 损坏状态下可由外部进入、完成认证并恢复的独立通道。文件存在、脚本先后和直接依赖仅能支持候选入口，不能替代恢复测试。

### Cited Findings
- 官方 FX3 7.02 rootfs `/sbin/init` L24–28 做驱动/nflash/rootfs 设置后进入 init2；setup_rootfs 使用 `fstab.root` 将 `/dev/nflasha7` 以 ext2 ro 挂到 `/rootfs` 并 pivot_root。init2 L44–64 挂载分区，在 MODE 非0时装驱动，随后先 `setup_bis || setup_senser`，再后台启动 `/usr/bin/bootin.elf`。这些是原脚本控制流，不是脚本执行日志。[原始 init](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init)、[原始 init2](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init2)、[原始 setup_rootfs](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/initrc/setup_rootfs)、[启动静态回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-startup-recovery-static.json)
- `setup_senser()` 仅在 `/setting/sen/smode` 可读且内容为 UU 时，后台运行 `/usr/bin/sen.elf`；这一调用在 bootin 之前，但两个程序异步运行，未证明服务已就绪或主应用失败后服务仍存活。`setup_bis` 取决于 `/proc/udm/upm_bootmode`，还包含重新格式化 log 分区的分支；本次仅阅读，没有尝试任何模式切换。[init2 L12–41](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init2)
- 已提取 sen.elf（27240B，SHA `9e3236666176b69746848edaac31e1e0ef00c4e80a9f062794ff62be2d605470`）及 bootin.elf（23960B，SHA `dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2`）。两者直接 DT_NEEDED 都未列 appFw.so，但 sen.elf 导入 dlopen/dlsym 并包含 `libsencore.so`、`senser_usb_mode_start` 等动态入口；libsencore 进一步依赖多个测试命令库并有 `libpro%02X.so` 插件路径，未跟完全部依赖与 IPC。不能用“无直接依赖”推出完全独立。[二进制和脚本回执](../../work/sony-firmware-20261024/stage2/write-audit/fx3-startup-recovery-static.json)、[本轮小文件提取清单](../../work/sony-firmware-20261024/stage2/extraction/late-selected-manifest.json)
- `/usr/bin/up.sh` 明确存在通过 `/setting/updater/mode*` 选择后续 updater/service 模式并通知 LSI 的逻辑；它在正常系统的 usr 分区中，本身需要可执行环境。该脚本的 updater/mode3 与上述 sen/smode=UU 是不同条件，不能当成同一个救援开关。[原始 up.sh](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha15/bin/up.sh)
- setup_console 根据内核 cmdline 的 console 参数选择 getty/ash；这说明脚本含控制台分支，不证明用户可用接口/引脚、认证要求或失败状态下可达。[原始 setup_console](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/initrc/setup_console)
- 仅读取 macOS 缓存 IORegistry 的 IOUSBHostDevice 属性，当前未列出 Sony VID 0x054c 设备；没有打开 USB 接口或发送相机命令。回执去除了序列号及其他厂商设备。[USB 前提检查](../../work/sony-firmware-20261024/stage2/write-audit/sony-usb-presence.json)

### Inferences
- 值得优先验证的候选是主启动前的 sen.elf 服务分支，而非先假定“必须换完整固件”或“任何故障只能拆机”。若未来证明它在主应用无法加载时仍完整工作，才可能成为局部补丁的恢复保障；目前不应直接改 smode 或 updater 标志试验。
- 只损坏 appFw.so 与损坏 rootfs、usr 文件系统、内核、WBI 或启动标志不是相同故障，恢复路径必须按补丁可能影响的具体故障验证。

### Gaps
- 未跟踪 BootROM/bootloader 到内核/ramdisk/WBI 的选择路径；未证明冷启动一定经过本次 rootfs init2。
- 未证明不依赖正常主应用、可从外部设置或触发 sen/smode=UU 的方式；没有确认隐藏按键、硬件维护序列或提前配置的恢复标志在真实失败时有效。
- 尚未检查 sen.elf/全部动态插件/命令库的完整间接依赖与运行时注册、IPC，以及 service authentication、Jiritsu、可写权限在主应用损坏时是否仍成立。
- 没有做真实故障注入、独立恢复或官方更新器在任意自定义损坏后的恢复测试。结论是“找到候选而未证实独立恢复”，不是“静态证明不存在”。
