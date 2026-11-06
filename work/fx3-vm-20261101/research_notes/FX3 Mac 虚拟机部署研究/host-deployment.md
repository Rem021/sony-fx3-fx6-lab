# Mac 原生 FX3 虚拟机部署与实际运行

## 这台 Mac 是否具备可运行环境

### Takeaway
本机已经部署并实际运行了原生 ARM64 QEMU/TCG；经典 FX3 7.02 原内核、原 BusyBox 用户态和原 AP 动态加载器两层验证通过。当前是最小研究虚拟机，完整机身界面与成像未部署。

### Cited Findings
- 实测宿主是 macOS 27.2 ARM64、Apple M2 Pro、16 GiB RAM、10 CPU。初始 PATH 与常见绝对位置未发现 QEMU/UTM/Docker/OrbStack/Lima；存在的 Claude Desktop bundle 属专用环境，未使用或修改。此范围的缺失不扩成全盘不存在。— [主机清单](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/host-inventory.json)；[现有环境约定](/Volumes/KAFU2T/AI/Projects/Mac/docs/shared-development-storage.md)
- 没有新建常驻 Linux VM、全局包管理器或系统设置。任务目录局部取得官方 QEMU 11.1.2 源 141815216 B，SHA256 `731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016`；与 A7C2 固定源身份一致。— [QEMU 官方](https://www.qemu.org/download/)；[源回执](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/source-receipt.json)
- 局部编译依赖是 Meson 1.9.1、Ninja 1.13.0，以及 Homebrew 官方 ARM64 glib/pcre2/gettext/pkgconf 瓶，均有官方元数据和下载SHA；Qt/GTK/Cocoa等GUI与网络/USB后端未启用。FDT 最终使用 QEMU wrap 固定 DTC 提交 `b6910bec11614980a21e46fbccc35934b671bd81`，备选 Homebrew DTC 瓶未被选中。— [依赖源](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/metadata/python-build-deps.json)；[配置](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/configure-02.log)；[DTC来源](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/internal-dtc-receipt.json)；[Homebrew glib 官方元数据](https://formulae.brew.sh/api/formula/glib.json)
- 实际最终运行二进制是 Mach-O ARM64、QEMU 11.1.2，包含两个明确门控的本地内存模型改动。原/最终 entitlements 为空，本地 ad-hoc 重新签名通过，最终签名二进制已实际执行 TCG，而不是仅版本检查。— [最终部署回执](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/final-runtime-validation.json)

### Inferences
- 这台16GiB Mac足以承载本次2GiB backing的最小原固件内核/用户态。上游 `-m24576` 用于稀疏覆盖地址跨度，不能当成必须24GiB实际驻留；我们直接把RAM物理基址放到 `0x400000000`（16GiB物理地址位置）而仍只给2GiB backing。依据是原FX3 DTB和原 `setup_kemco` 对 `0x400001000` 的真实访问。— [模型差分](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/qemu-high-ddr-change.json)；[p06原ring](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p06/printk-decoded.json)

### Gaps
- GUI/原厂菜单/CP运行的内存、性能和长期稳定性没有通过，不能把短时120–138MiB RSS外推成完整相机运行的资源上限。— [最终两次RSS/时间窗口](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/final-runtime-validation.json)

## 采用哪条部署路线以及运行依赖

### Takeaway
选择原生 macOS TCG system-aarch64，省去额外Linux虚拟机。正式入口与非系统 dylib 闭包已经部署到 `outputs/fx3-vm/`，不依赖编译目录或 Homebrew 全局安装。

### Cited Findings
- QEMU 官方支持 macOS 主机的系统仿真；本次实际构建 `aarch64-softmmu`，运行 `virt/gicv2 + cortex-a35 + smp1`，不是 macOS 原生直接加载 Linux ELF，也不是用通用 Linux 来替代 FX3 内核。— [QEMU macOS](https://www.qemu.org/download/#macos)；[构建参数](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/configure-02-command.json)；[启动器](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py)
- 正式闭包为QEMU、glib、pcre2、intl共四个Mach-O文件。非系统库采用 `@loader_path` 相对链接，并删除两个未使用的构建目录 `LC_RPATH`。源码构建SHA→重定位前后SHA和完整 `otool` 已保存；我早期从截断预览误称“仅Apple动态库”的判断已经纠正。— [重定位闭包](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/runtime-relocation.json)；[RPATH更正](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/rpath-removal.json)
- 双击 `.command` 的终端入口已生成，CLI自检、Python编译、zsh语法和最终两profile端到端运行均通过；没有实际操控GUI/双击Terminal验收。默认12秒宿主壁钟、最多30秒，固定卷UUID和源SHA，独占自身运行锁，QMP socket短路径，16MiB单日志上限，退出回收所属QEMU。— [入口说明](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/README.md)；[固定清单](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json)；[最终回执](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/final-runtime-validation.json)
- `share/`仅保留运行必需的自有原固件最小ELF摘取CPIO和实验DTB，无完整BODYDATA或完整分区。原6610952B FX3内核只读引用既有stage47，SHA `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`；每次运行前后核对。无网卡、无USB/原始磁盘/宿主目录透传。— [固定资产](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json)；[原ELF来源](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/application-loader-probe.json)

### Inferences
- 可直接从交付入口继续内核/用户态、动态加载和后续AP研究，不必先在这台Mac上建设一套x86 Linux环境。完整A7C2 GTK/bwrap/观察器与Sony外设模型不能通过这个最小包自动获得。— [已验入口](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/README.md)；[上游迁移研究](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/research_notes/FX3 Mac 虚拟机部署研究/upstream.md)

### Gaps
- `.command`双击的Terminal GUI流程未验收；CLI已真实执行。完整机身菜单需要后续输入、显示、设置、Backup和AP/CP/IPC服务适配；本包没有将原系统 `/init` 或更新流程跑起来。— [包范围声明](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json)

## 原 FX3 实际运行到哪一步

### Takeaway
严格逐层原件对照已从早期异常推进到完整最小内核/原BusyBox启动；原bootin/im的原loader verify/list也在同一原内核里成功。两个正式profile都使用最终SHA二进制实跑通过，菜单和成像仍未验收。

### Cited Findings
- 原head会覆盖传入DTB地址，必须显式把实验DTB放在ImageBase减 `0x7e000` 处。stock virt低DDR baseline实际执行原Image后在SMP初始化写 `0xfe005010` 进入EL1向量；只补4KiB RAM式SMP mailbox后进入MMU阶段。— [原head](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/early-head-original.json)；[p02](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p02/receipt.json)；[mailbox证明](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/smp-esram-mailbox-proof.json)
- p06从原symbol读取同次完整128KiB printk ring，指针/长度/索引/原始字节均保留，QMP实际翻译VA到PA；61条结构记录严格闭合。其首异常是低RAM布局未覆盖原 `setup_kemco` 硬编码地址 `0x400001000`，而不是“不支持Sony内核”的笼统结论。— [同次QMP](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p06/qmp.json)；[原ring](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p06/printk-ring.bin)；[独立复核](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/p06-independent-printk-proof.json)
- 高DDR+2GiB RAM后原串口实际输出Linux4.9.337-scel+与UDIF线程；下一故障是原IRQ helper的固定VA缺映射。仅实验DTB新增一个Sony `iomap` 节点，把 `fffffffff13a1000` 指向现有真实QEMU GICD `0x08000000`，p08 QMP核到 `fffffffff13a1c38→0x08000c38`，原IRQ申请越过后触发实际缺失的Sony timer地址。没有伪造IRQ返回，也没有加外设catch-all。— [p07](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p07/printk-decoded.json)；[p08](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p08/qmp.json)；[GICD DTB来源](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/virt-high-gicd-probe01.dtb)
- 原内核不支持gzip initramfs；压缩包的失败保留后改为同一newc内容的raw CPIO。minimal-linux只使用原Image，明确禁用七个没有模型的原初始化wrapper，均由原initcall表指针逐项核对；hwtimer/PCIe有实际失败，其他项是明示profile排除。— [格式修正](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/raw-initramfs-correction.json)；[七项证据](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/minimal-linux-blacklist-evidence.json)
- 最终 `minimal-linux` 运行 `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/a-7811bbff`：原kernel完成initcalls，原BusyBox执行自写 `/init`、原 `uname` 输出 `4.9.337-scel+ aarch64`，两个marker齐全，输入前后SHA一致；采样RSS峰 `123152` KiB（约 `120.3` MiB）。— [最终core回执](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/a-7811bbff/receipt.json)
- 最终 `app-loader` 运行 `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/a-2d6d46e5`：原ld对原bootin/im的 `--verify`、`--list` 四项返回均0，20份原ELF、88条依赖闭包实际解析；没有执行app main/constructor。采样RSS峰 `140896` KiB（约 `137.6` MiB）。— [最终loader回执](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/a-2d6d46e5/receipt.json)；[原ELF闭包](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/application-loader-probe.json)
- 两次最终运行均核原inputs未变、正常QMP退出并回收进程。原Image未patch；没有相机/USB/手机/刷写。最终QEMU SHA `78e36d4060aa4aae5a802c69cbd45beab3c69c47746371897e229e1c1eeb7e93`。— [正式最终验收](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/final-runtime-validation.json)

- 默认包之外仅追加一次原 `im.elf target=qemu` 启动alpha：使用相同最终QEMU，guest原AP限2秒/host观察12秒，原程序报告 `/dev/uipc` 不存在，原wait RC133；kernel无panic，进程已回收。syscall tracing不可用，所以仅称原程序报告的阻塞资源，不宣称已枚举所有open、已到main或菜单，也不把133猜成ABI故障。该候选不进入默认包，之后停止新增修复轮。— [alpha原始串口](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/runs/p12-im-entry/serial.log)；[独立alpha摘要](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/ap-entry-alpha-summary.json)；[参数parser原字节](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/im-argument-static.json)

### Inferences
- 本机的“FX3最小研究虚拟机”部署已经有可复现产物和真实运行证据；原厂AP的Linux用户态基础ABI可用。原AP业务、模块、CP/IPC和显示依赖仍应逐层核对，不能将loader成功升级为原相机菜单成功。— [交付入口](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/README.md)

### Gaps
- 七项硬件服务没有完整设备模型；原厂菜单、CMOS/ISP、编码和媒体保存不在通过范围。独立AP入口alpha已具体停在缺失 `/dev/uipc` 的环境边界，未提升菜单/CP兼容性，也未改变上述默认profile。
- 观察窗是宿主12秒，未作长时间运行/多次反复开关机/视觉验收；旧probe字段 `guest_seconds_requested` 实际表示宿主观察窗，Sony printk时间不按宿主壁钟解释。— [时间边界更正](/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/metadata/final-runtime-validation.json)
