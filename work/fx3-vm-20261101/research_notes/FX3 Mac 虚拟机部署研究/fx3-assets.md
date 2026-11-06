# FX3 7.02 原始资产与启动可行性

## 现有原始资产能否支撑 FX3 固件仿真

### Takeaway
原FX3 7.02内核与原glibc/busybox已经在这台Mac的原生TCG中运行，原动态链接器也已实际解析bootin/im及其声明依赖。已证的是可部署的固件执行底座；完整机身界面、成像和刷机不在本次通过范围。

### Cited Findings
- 经典 FX3 7.02 的原 `vmlinux.bin` 为 AArch64 Linux Image，6,610,952 B，SHA256 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`；原字节 banner 是 `Linux version 4.9.337-scel+`，Image header `text_offset=0x80000`、`image_size=0x6af000`、`flags=0xa`。本轮读回全部文件并重新哈希。— [本轮资产核验](../../fx3-audit/asset-audit.json)、[原提取来源](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-extraction-receipt.json)
- `nflasha7.img` 为 5,218,304 B ext2 根文件系统，SHA256 `ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7`；已存目录有 153 项及4份 `.ko`。`nflasha15.img` 为 479,846,400 B ext2 用户程序分区，SHA256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`；已存目录有915项及122份 `.ko`。本轮两个镜像全 SHA 与旧记录对应，原文件系统只读解析，没有宿主挂载。— [资产核验](../../fx3-audit/asset-audit.json)、[原目录解析器](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/read_filesystems.py)
- 原 busybox、glibc 2.25、ld-2.25、bootin.elf、im.elf、appFw.so 及相关已选库为 ELF64 little-endian / `e_machine=183`；动态解释器 `/lib/ld-linux-aarch64.so.1`。busybox 的两项 DT_NEEDED 为 `libcrypt.so.1` 和 `libc.so.6`；bootin、im 还需要 backup、osal_utm/osal_uipc、C++、pthread 等实际库，im 含 libIMDB/libSTMcmdexecute/libssl/libcrypto 依赖。— [逐个 ELF 元数据与原 inode/SHA](../../fx3-audit/asset-audit.json)
- 原 `/sbin/init` 首先挂 proc，再调用原 insmod_drv1/setup_nflash/setup_rootfs；`init2` 依赖 `/proc/udm/upm_bootmode`、`/proc/udm/drivers`、nflasha 各分区，再启动 `/usr/bin/bootin.elf`。root fstab 将 `/dev/nflasha7` 只读挂到 `/rootfs`，用户分区15只读挂到 `/usr`；所以不能把拷贝 bootin 文件就当完整相机系统。— [原 init/scripts 副本与来源 SHA](../../fx3-audit/asset-audit.json)
- `av-cam.bin` 是 ORIL/version5 原载荷而非 Linux userspace ELF；其 LIRO 装载器要写211项接口，旧阶段只绑定过受限内存函数。`cpapp-b.bin` 原始 ARM/Thumb 指令流也不是可交给 aarch64 Linux 动态加载器的 ELF。两者本轮重新读回SHA分别为 `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` 和 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。— [本轮载荷记录](../../fx3-audit/coprocessor-artifacts.json)、[原 LIRO 证据](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/README.md)

### Inferences
- 可以把原 kernel + 原 busybox/libc 放入隔离 ARM64 系统仿真，先验 CPU、启动 ABI、定时器、UART 和用户态；如果成功，只能称为该层 FX3 代码运行。
- 原厂 UI 还需原应用依赖、配置与 Backup、UDIF/UIPC、图形和 CP 服务；成像与编码还要额外证明真实输入与原软件消费。相同 A35/CXD90057 架构提供代码复用线索，不能替代这些门槛。

### Gaps
- 本轮没有真实用户机身的运行 RAM、当前Backup、已启动 CP/AV 任务、CMOS/编码器或完整UI状态。原包默认数据不能充机身校准。
- 尚未声称可以复制 A7C II 的固定 appFw 偏移或 observer 到 FX3；对应关系需逐个函数重新定位。

## 原内核与 DTB 的启动合同有什么实质发现

### Takeaway
FX3 原 Image 不是直接消费 QEMU 传入的 x0：其早期 head 会把 DTB 指针强制改为 `ImageBase-0x7e000`。这是普通 `qemu -kernel ...` 可能无串口输出的一个可证伪原因，必须将有效 DTB 放在对应位置。

### Cited Findings
- 原 Image 文件+0首指令跳至 `stext=+0x5b0000`，随后 BL 到 `ej_head_init=+0x40`。该函数+0x5c 为 `ADR x0, ImageBase`，+0x60 为 `SUB x0,x0,#0x7e,LSL#12`，接着清 x1/x2/x3、返回。指令字节与原内核 kallsyms 地址共同核对，未修改原 Image。— [原 head 指令记录](../../fx3-audit/early-head-original.json)、[符号原来源](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json)
- 现有 7.02 包内 setting 的原 `cxd90057.dtb` 是16875 B，SHA256 `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280`；本轮独立解析FDT。memory声明起点 `0x400000000`、长度 `0x200000000`，UART0 为PL011 `0xf1000000`、SPI中断218；GIC400 dist `0xf13a1000`、cpu `0xf13a2000`；armv8-timer声明2MHz；chosen stdout `serial0:460800n8`。有四个A35 CPU节点，不能据节点存在认定都在线。— [本轮 FDT 解码](../../fx3-audit/asset-audit.json)、[原DTB来源/范围](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage205-FX3-hardware-profile-differences/DTB-source-capture.json)
- 原头还访问 Cortex-A35 实现定义系统寄存器 `s3_1_c15_c2_1`；复制原内核并不意味着可以任意选 CPU。— [原指令+0xf4..0xfc](../../fx3-audit/early-head-original.json)
- A7C II 上游脚本已用高DDR固定 loader 并修改固定 DTB 的 chosen/bootargs；其七项初始 initcall_blacklist 名称，本轮逐个与 FX3 原 kallsyms 交叉检查，见记录。名字相同只表明可定位，不能据此认为跳过后语义仍正确。— [上游固定脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh)、[FX3 名称核对](../../fx3-audit/upstream-initcall-name-crosscheck.json)

### Inferences
- 如果 QEMU 把 Image 放到 `0x40080000`，原 head 将寻找 `0x40002000` 的FDT；如果 Image 放到高DDR `0x400080000`，则寻找 `0x400002000`。必须同时匹配原 head、loader 实际地址和有效 chosen/bootargs。
- 初探可用 QEMU virt 生成的 GIC/PL011/timer DTB，避免把真实板级MMIO节点未加模型就搬进模拟机。若要用 Sony DTB/原驱动，需要模型覆盖对应地址和中断。
- DTB中8GiB窗口不是用户FX3实装RAM容量；虚拟内存布局与芯片容量、原厂默认声明要分开。

### Gaps
- 原 kernel 在 TCG 中真正到达哪个 initcall、是否需要 A7C2 MMIO alias 和哪些最小 blacklist，仍需本轮实际日志。静态符号或FDT解析不充启动。

## 已准备的最小实验是什么 验收边界在哪里

### Takeaway
本机原生 QEMU TCG 已实际运行未修改的 FX3 原内核，从早期 head、MMU、start_kernel 推进到串口、调度、原UDIF驱动初始化。ESRAM mailbox、高DDR与GIC固定VA的具体阻塞已分别定位并作最小差分；原busybox执行（L1）和原动态链接器解析bootin/im（L2）已通过正式包实跑，完整AP/菜单仍未验收。

### Cited Findings
- `fx3-minimal-original-userspace-v2.cpio.gz` 为920180 B，SHA `c704d71d6e6618b087d21c3a2a1a2bb562cb19085032a69f7ec43314302c4f4f`，含原 busybox/ld/libc/libcrypt 及解释器链接。自写 `/init` 只输出标记、原busybox uname并sleep，不执行原init/updater，不创建磁盘连接或相机接口。— [探针清单](../../fx3-audit/minimal-probe-v2.json)、[构造脚本](../../fx3-audit/prepare_probe_v2.py)
- v1未执行，审查发现缺失原busybox依赖libcrypt；已保留v1及失败条件并创建v2，未用缺依赖包制造启动失败。— [v2审查记录](../../fx3-audit/minimal-probe-v2.json)
- 最新安装调查中，11月1日A7CII HEVC参考对应A7CII 2.01的4K29.97/25p VM菜单往返；原厂成片与真机安装未通过，不能当FX3或1080p验证。— [已安装Scrapling调查](/Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-scrapling-fx3-research/README.md)

- p01 在QEMU装载前因自动virt DTB与手工低地址DTB ROM区域重叠被拒；p02 改用标准 `-kernel/-initrd`，另将有效DTB加载到原head预期位置，实际执行3.2秒原Image。原trace最后到 `cxd900xx_smp_init` 的 `STR w6,[x5,#0x10]`（原file `0x426764`，runtime `0x404a6764`，观测x5=`0xfe005000`），随后 PC=`0x200`/EL1h。该运行的原kernel SHA不变，串口0字节，QMP正常退出0不充kernel启动成功。— [原运行回执](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p02/receipt.json)、[阻塞绑定](../../fx3-audit/p02-blocker-analysis.json)
- 相邻原 `cxd900xx_secondary_init` 从常量 `0xfe00501c` 按 MPIDR低8位索引写入0xff；原SMP init将secondary入口写入 `FE005010/14/18` 并清旁flags。支持将该页建模为RAM式SMP mailbox，最小可补 `[FE005000,FE006000)` 4KiB RAM后端。此归因仍保留“未采集ESR”的限制，不当作物理RAM或控制器已验；不需对整个F窗口用全1返回。— [原消费者与页范围](../../fx3-audit/smp-esram-mailbox-proof.json)
- 纯Python DTB重建器从QEMU实际generated DTB生成正式probe01：仅3项chosen属性变化，57节点其余值及reserve map不变；SHA `a8cd5a3ec6d43d8769fbe76eb4db14d18ff0df689af2388bcaf8e631d4c067e3`。DTB已按静态合同准备；p02在执行x0覆盖前已出错，不能据此称Linux已解析DTB。— [正式DTB差分回执](../../fx3-audit/virt-probe01.dtb.json)

- p04仅增加4KiB ESRAM mailbox后进入原 `start_kernel/setup_arch`，还没有串口。p06在相同模型停机后，通过QMP/HMP虚拟地址翻译读取了原128KiB printk ring、索引与指针；本资产worker用独立16B头解析器复核61条record，所有长度/文本/边界通过、end_idx恰为4264，与next_idx一致。原kernel自身日志确认4.9.337-scel+ banner、Hardware `linux,dummy-virt`、ESR `0x96000010` synchronous external abort、PC `strncmp+0x28`、LR `setup_kemco+0x50`、最后Fatal exception/panic.c191。— [独立原ring复核](../../fx3-audit/p06-independent-printk-proof.json)、[本次运行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p06/receipt.json)
- 原 `setup_kemco` file+0x5b50c0明确 `early_memremap(0x400001000,0x1000)`，再比较页首五字节；低地址2GiB virt RAM不覆盖该高DDR位置。故下一次差分迁移QEMU的RAM base到原 `0x400000000`，保持2GiB backing；不修改原Image，不先加入全部外设模型。— [原内核](../../fx3-audit/asset-audit.json)、[ring的原fault与寄存器](../../fx3-audit/p06-independent-printk-proof.json)

- p07迁移QEMU RAM基址到原高DDR `0x400000000`（只保留2GiB backing）后，原kernel串口实际显示完整早期Linux启动、页分配、PSCI、GIC、62.50MHz architected timer、调度与原UDIF线程。新失败为原 `irq_get_trigger+0x58` 读取固定VA `fffffffff13a1c38` 的level1 translation fault (`ESR=96000005`)，不是物理设备总线abort。— [p07原串口](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p07/serial.log)、[原consumer字节证明](../../fx3-audit/gicd-original-consumer-proof.json)
- 原 FX3 `map_io` 读取 `device_type=iomap` 节点的 `phys/virt/size/memtype`（不能套用FX5的 `physaddr` 字段）。本轮仅加一个DTB节点把固定VA `fffffffff13a1000` 映到现有QEMU GICD PA `08000000`，没有额外创造Sony物理GIC控制器；p08 gva2gpa读回具体 fault VA映到 `08000c38`，原IRQ申请已越过，随后到Sony hwtimer寄存器缺模型。— [原consumer证明](../../fx3-audit/gicd-original-consumer-proof.json)、[DTB准确差分](../../fx3-audit/virt-high-gicd-probe01.dtb.json)、[p08日志](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p08/serial.log)
- p07原kernel明确报 `compression method gzip not configured`，故初始gzip探针不能作为可运行包。已解压为同内容raw newc：最小包1860580 B，SHA `1478fde20c516ef9869573711d9626c5da80a5e45be15c5ca43200d5835bb00c`；20 ELF应用loader包8693220 B，SHA `7d151d8f1e363c66a947724fd65c5b818e8037347c886d8b0f133c970ad1f862`。只转换容器，原binary字节不变；p10原 `populate_rootfs`已正常解包raw格式。— [格式修正](../../fx3-audit/raw-initramfs-correction.json)、[p10 initramfs日志](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p10/printk-decoded.txt)
- 最小Linux配置通过原内核 `initcall_blacklist` 禁用尚未建模的Sony设备初始化，保留通用architected timer。七项wrapper与原 `__initcall_*6/7` 表项8B回调指针逐项相等核验；hwtimer/PCIe有实测fault，watchdog/FUSB/DDR管理/PCI DMA/SonyUSB按缺模型的profile范围排除，不能声称这些已硬件兼容。p10仅前三项有实际接受且跳过日志；七项配置下一轮结果须另验。— [七项表成员与禁用理由](../../fx3-audit/minimal-linux-blacklist-evidence.json)、[最小Linux v2 DTB](../../fx3-audit/virt-minimal-linux-probe02.dtb.json)
- 原应用加载探针已准备：20份原ELF、88条递归DT_NEEDED依赖边，guest只执行原ld-linux `--verify/--list` 原bootin/im，不执行应用main/原init/updater。预期证明解释器和库解析边界，不是相机UI已启动。— [完整原ELF和依赖清单](../../fx3-audit/application-loader-probe.json)

- L1正式原用户态通过：原内核释放init内存后执行原busybox、原ld/libc，串口真实uname为 `Linux (none) 4.9.337-scel+ #1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025 aarch64 GNU/Linux`；原七项初始化均有parse接受与真正skip证据。— [p11独立核验](../../fx3-audit/p11-core-independent-proof.json)
- 最终正式QEMU二进制SHA为 `78e36d4060aa4aae5a802c69cbd45beab3c69c47746371897e229e1c1eeb7e93`。两次正式包运行 `a-7811bbff`(minimal) 和 `a-2d6d46e5`(app-loader) 均12秒宿主有界观察、原Image SHA保持、输入不变、进程回收；两次原ring均803条被本worker独立解析边界通过，七项原initcall parse/skip齐全，无guest异常标记。— [最终正式包独立核验](../../fx3-audit/final-runtime-independent-proof.json)、[可重放的只读核验器](../../fx3-audit/verify_runtime_runs.py)
- L2正式加载边界通过：guest内原ld-linux对原bootin/im分别 `--verify/--list`，四RC均0、结束marker齐。25条实际provider输出对应15个原库canonical路径，逐个与原cpio中的SHA相等；闭包共20份原ELF/88条DT_NEEDED边（含busybox/loader/程序与库）。这是加载器层验证，未因此执行AP main或证明UI。— [最终独立provider与源码身份](../../fx3-audit/final-runtime-independent-proof.json)、[原20ELF清单](../../fx3-audit/application-loader-probe.json)
- FX3原im本身支持target参数：原VA `0x405110..0x405138`加载 `target=` 并strncmp长度7、保存argv+7；`0x405194..0x4051bc` 与 `0x405714..0x40573c`实际引用 `qemu` 并设置bit0x1000。bootin原usage也列target参数，不能用A7CII地址代替这些FX3原址。当前独立候选仅在无网络/host磁盘/USB的VM执行原im target=qemu，guest2秒边界+hostQMP兜底，不包含原init/updater/Jiritsu载荷、不进入默认manifest；入口结果已在下一条记录，未达UI。— [FX3原参数指令与上下文](../../fx3-audit/im-argument-static.json)、[独立入口候选](../../fx3-audit/ap-entry-probe.json)

- 唯一额外AP短探针 `p12-im-entry` 已实跑最终QEMU二进制，输入三SHA与正式原Image均独立复核。原im PID102启动尝试后输出 `open /dev/uipc error: : No such file or directory`、`im.elf(pid:102): some one called exit()`，在2秒边界前退出；wait RC仅记录为133，不推断信号/因果。错误字面量唯一原provider已核为 `/usr/lib/libosal_uipc.so`，原SHA `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3`、file+0x8c80。该运行没取得syscall trace，不能区分动态加载构造期还是AP main后，也不能因argv写了target=qemu便称原qemu分支已运行。— [独立AP入口核验](../../fx3-audit/p12-ap-entry-independent-proof.json)、[原始同次串口](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p12-im-entry/serial.log)
- 此结果提供了完整菜单部署的第一个具体环境缺口：原UIPC设备/协议/共享内存与其后CP服务尚未接通。没有补假成功响应、没有把该alpha候选加入默认manifest、没有继续扩大更多入口探针。— [同次边界](../../fx3-audit/p12-ap-entry-independent-proof.json)

### Inferences
- 本轮第一终点已实际通过：原Image串口banner → 原内核调度 → 原busybox/原ld/libc执行 → `FX3_ORIGINAL_BUSYBOX_REACHED` 与 `FX3_VM_PROBE_END`。依据是真实原二进制执行与同次身份回执。
- 该终点完成了基础固件执行层。原bootin/im的ELF加载/依赖解析后来也已通过；可操作FX3菜单仍需原AP入口及运行状态、原UI出帧、按键/菜单响应、保存配置与正常退出分别验证。拍照录像需要成像输入、原编码与存储证据。

### Gaps
- 最终两个正式profile已分别通过L1/L2，完整AP/菜单/成像仍未通过。独立AP短入口已经确证原vendor UIPC环境缺失（/dev/uipc ENOENT），但main/constructor阶段不可区分、原qemu分支执行未证明；不能把exec尝试当AP正常启动。下一项应先逆向原UIPC节点/模块/ioctl/映射合同，再选择guest原驱动或明确的协议模型；不能用固定成功回复代替。
