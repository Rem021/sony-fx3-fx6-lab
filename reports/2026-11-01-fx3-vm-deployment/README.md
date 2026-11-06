# 让 FX3 原固件 在 Mac 运行

2026-11-01；对象为经典 FX3／ILME-FX3 7.02，以及本机 Apple M2 Pro、macOS 27.2、16 GiB 内存。

**可以在这台 Mac 上部署 FX3 的最小研究虚拟机，而且已经实际跑通原内核、原用户态和原应用加载器。** 正式运行包位于 `outputs/fx3-vm/`，采用原生 ARM64 QEMU／TCG，未另建 Linux 虚拟机。FX3 原始 Linux Image 没有修改；实验设备树、4 KiB 启动邮箱模型和明确禁用七项未建模硬件的配置，使原 BusyBox 与原 glibc 成功执行。原链接器对 `bootin.elf`、`im.elf` 的加载验证也全部通过。**完整机身菜单尚未部署成功**：额外的原 `im` 短时启动尝试报告缺少 `/dev/uipc`，没有证明进入应用 main 或显示界面。当前结果支持继续进行 FX3 专属系统移植，不能代替 CMOS／ISP、H.265 成片或修改固件刷入验收。([正式运行包](../../outputs/fx3-vm/README.md)、[最终实测回执](../../outputs/fx3-vm/metadata/final-runtime-validation.json)、[独立运行核验](../../work/fx3-vm-20261101/fx3-audit/final-runtime-independent-proof.json))

## 已部署到原用户态，菜单仍停在 UIPC 环境边界

两次正式验收使用**同一份最终 QEMU 二进制**，分别执行基础 Linux 与应用加载器配置。原内核 `4.9.337-scel+` 完成初始化后，原 BusyBox 执行本任务编写的最小 `/init` 和原 `uname`；两项完成标记均出现。另一配置使用原 `ld-linux-aarch64.so.1` 对原 bootin／im 各执行 `--verify`、`--list`，**四项返回码均为 0**。20 份原 ELF 构成 88 条声明依赖边；实际 provider 输出对应的 15 个原库，路径与原始字节摘要逐项吻合。加载器配置没有进入应用构造函数或 main。([原 ELF 清单](../../work/fx3-vm-20261101/fx3-audit/application-loader-probe.json)、[正式包独立核验](../../work/fx3-vm-20261101/fx3-audit/final-runtime-independent-proof.json))

| 验收层 | 本轮状态 | 已取得的证据 | 不能据此推导的能力 |
|---|---|---|---|
| Mac 宿主运行环境 | 通过 | 原生 ARM64 QEMU 11.1.2 实际执行 TCG，非系统 dylib 闭包重定位后再次运行 | HVF 加速、其它 Mac 兼容性未验 |
| L1：FX3 原内核与原用户态 | 通过 | `a-7811bbff`；原内核、glibc、BusyBox／uname、完成标记与退出回执 | Sony 原 `/init`、全部板级设备和交互 shell 未验 |
| L2：原应用 ELF 加载 | 通过 | `a-2d6d46e5`；原 bootin／im 的 verify／list 四项返回 0 | 原 AP 业务正常启动、原菜单运行未验 |
| 原 AP 短时启动 | 发现具体阻塞 | `p12-im-entry`；原 im 进程报告 `/dev/uipc` 不存在后退出 | main、原 qemu 参数分支实际执行未证 |
| 原厂菜单、输入与设置 | 未完成 | 尚无 FX3 原界面出帧、按键响应与设置恢复的同次运行证据 | 不能把终端入口当相机 GUI |
| CMOS／ISP、编码与媒体保存 | 未完成 | 本轮没有图像源、原处理链、编码和写卡闭环 | H.265 录像、VENICE 全链及实际刷写均未通过 |

表中正式两次运行，均在结束后核对输入摘要未变、回收所属 QEMU；各自原 printk ring 的 **803 条记录**被独立按结构边界复核。观察窗为约 12 秒宿主壁钟，采样峰值 RSS 分别约 **120.3 MiB、137.6 MiB**。这些数字说明当前最小配置可以在本机运行，不能作为完整菜单、CP 或成像模型的内存上限、长期稳定性或性能指标。([最终运行回执](../../outputs/fx3-vm/metadata/final-runtime-validation.json)、[独立核验](../../work/fx3-vm-20261101/fx3-audit/final-runtime-independent-proof.json))

独立 AP 试验只在默认包之外追加一次：原 `im.elf target=qemu` 在 guest 中限时 2 秒，宿主观察 12 秒。错误字面量的唯一原 provider 已定位为 `libosal_uipc.so`，文件偏移 `0x8c80`；原始串口随后记录进程退出，wait 返回 133。没有取得 syscall trace，所以**不把 133 解释成特定信号或 ABI 不兼容，也不把该输出定位为 main 之后**。它证明当前最小环境缺少原厂 UIPC 运行条件；没有补固定成功回复来掩盖这一缺口。([AP 入口独立核验](../../work/fx3-vm-20261101/fx3-audit/p12-ap-entry-independent-proof.json)、[同次原始串口](../../work/fx3-vm-20261101/host/runs/p12-im-entry/serial.log))

## A7C II 提供整系统方法，FX3 的接口仍须重新定位

本轮复用了新装的 Scrapling 0.5 环境，实际抓取公开资料，并将 `chocotan/a7c2-qemu` 固定到 **`b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`**。35 份选定文本、约 2.06 MB 的源码与 Git blob 对应关系已核验；公开来源与本机实测分别保存。该项目采用原 Sony 内核的 QEMU **system** 仿真，配合原 AP 程序和软件设备模型。维护者已展示原厂菜单，最新说明仍将原厂拍照／录像标为未贯通；本轮没有在这台 Mac 上重现 A7C II 菜单。([源码取证回执](../../work/fx3-vm-20261101/upstream/selected-source-receipt.json)、[固定上游](https://github.com/chocotan/a7c2-qemu/tree/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500)、[10 月 31 日状态](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/2026-10-31-current-progress.md))

| 层 | A7C II 可借鉴的实现 | FX3 本轮处理与剩余适配 |
|---|---|---|
| 宿主与 CPU | system-aarch64、TCG、Cortex-A35、显式装载与 QMP 观察 | 已在 macOS 原生构建和实跑；没有照搬 Linux 的 bwrap、X11、linux-user 依赖 |
| 固件身份与用户态 | 固定包身份、原文件摘要、独立运行目录 | 重新核 FX3 7.02 Image、ext2、glibc 2.25 与 ELF 依赖，不绕过 A7C II 导入器的机型限制 |
| 内存、DTB 与中断 | 高地址装载、板级模型、受约束的初始化配置 | 已按 FX3 原指令修正 FDT 地址、SMP mailbox、高 DDR 与固定 GICD 虚拟地址 |
| 原 AP 与服务 | bootin／im 启动、IMDB、模块顺序和运行观察器 | 原 ELF 加载通过；FX3 原参数 parser 已静态核对，UIPC／Backup／模块服务未接通 |
| 图形与输入 | 软件 GPE／LZ77／OSD，QMP 截图和宿主窗口 | FX3 的资源、像素格式、消息、函数偏移、按键映射仍须逐项定位，不能复制 A7C II appFw 地址 |
| CP／AV 与成像 | 明示软件协议模型、图像源与编码组件 | 未移植；原 CP／AV 不是可直接交给 Linux 链接器的应用 ELF |

迁移矩阵的上游依据来自固定的[启动脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh)、[应用启动说明](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/04-app-and-first-setup.md)、[显示实现](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/05-display.md)和[成像边界](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/docs/tech/11-imaging-frontier.md)；FX3 一侧来自本轮[原始资产核验](../../work/fx3-vm-20261101/fx3-audit/asset-audit.json)及[独立运行证据](../../work/fx3-vm-20261101/fx3-audit/final-runtime-independent-proof.json)。

本机材料已包含原内核、ext2 根文件系统和用户程序分区，可以继续做 Linux／AP 研究。原 `av-cam.bin` 属 ORIL 载荷，`cpapp-b.bin` 为另一套 ARM／Thumb 指令流；它们的运行环境、装载接口和 CP／AV 通信必须独立建模。**同属 BIONZ XR 或 CPU 指令集相近，只能提供定位线索。** 上游 Mac 移植文档原来仅是静态评估，本轮已经补上 FX3 最小路径的本机执行证据，尚未补上其完整图形与软件设备集合。([协处理器资产](../../work/fx3-vm-20261101/fx3-audit/coprocessor-artifacts.json)、[上游跨平台评估](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/PORTING-WIN-MAC.md))

## 原内核的三个启动合同决定了最小模型

本轮没有改写原 Image 来跳过异常。原内核先后暴露的装载、内存及中断合同，分别通过原指令、同次日志和最小差分核对。最终只在 QEMU 增加两项门控内存模型，并调整实验 DTB 与启动配置；本机成功来自这些明确适配。([两项源码差分](../../outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch)、[原 head 证据](../../work/fx3-vm-20261101/fx3-audit/early-head-original.json))

| 合同 | 原件／实际故障揭示的约束 | 本次解决及验证边界 |
|---|---|---|
| FDT 装载位置 | `ej_head_init` 覆盖传入 x0，改读 `ImageBase-0x7e000` | 将有效 DTB 显式放到该位置；普通 `-append` 或默认 DTB 地址不能代替此合同 |
| 启动邮箱与高 DDR | 原 SMP 代码写 `0xfe005010`；低地址 RAM 又不能覆盖 `setup_kemco` 对 `0x400001000` 的访问 | 补 `[0xfe005000,0xfe006000)` 4 KiB RAM 式 mailbox；主 RAM 基址改为 `0x400000000`，容量仍仅 2 GiB |
| 固定 GICD 虚拟地址 | 原 IRQ helper 访问 `fffffffff13a1c38`，实际是页表 translation fault | 通过原 `map_io` 的 DTB `iomap`，把固定 VA 映到现有 QEMU GICD；QMP 实测翻译到 `0x08000c38` |

高地址 `0x400000000` 是 **16 GiB 的物理地址位置**，不是实际分配 16 GiB。原 setting DTB 声明的窗口和上游 `-m24576` 的稀疏覆盖需求，也不能直接换算为用户机身芯片容量或宿主 RSS。本次以 2 GiB backing 实跑，解决的是地址合同。4 KiB mailbox 只覆盖所观察的原 SMP 入口与标志用法，不能推出完整 ESRAM、DMM 缓冲池或当前机身 RAM 状态已经恢复。([原 DTB 与 Image](../../work/fx3-vm-20261101/fx3-audit/asset-audit.json)、[SMP mailbox 原消费者](../../work/fx3-vm-20261101/fx3-audit/smp-esram-mailbox-proof.json)、[原高地址异常的独立核验](../../work/fx3-vm-20261101/fx3-audit/p06-independent-printk-proof.json))

GICD 适配使用原 FX3 `map_io` 实际消费的 `device_type=iomap` 节点，属性为 **`phys/virt/size/memtype`**；FX5 的 `physaddr` 不能直接套用。实验节点将固定 VA `fffffffff13a1000` 映向 QEMU 已有 GICD PA `0x08000000`，没有凭空造一个 Sony 中断控制器，也没有使用全 F 窗口读全 1 的替身。映射成功后，原 IRQ 申请越过，下一处真实故障才显现为未建模的 Sony hwtimer。([原 map_io／IRQ consumer](../../work/fx3-vm-20261101/fx3-audit/gicd-original-consumer-proof.json)、[DTB 差分](../../work/fx3-vm-20261101/fx3-audit/virt-high-gicd-probe01.dtb.json)、[同次 QMP](../../work/fx3-vm-20261101/host/runs/p08/qmp.json))

另外两项配置差异直接决定是否能进入用户态。原内核明确报告未配置 gzip initramfs 支持，因此实际运行改用**同内容的未压缩 newc CPIO**，原 ELF 字节保持不变。基础 Linux 配置通过原 `initcall_blacklist` 禁用 hwtimer、wdt、FUSB OTG、PCIe、DDRC、PCI DMA、Sony USB 七个初始化 wrapper；每项都与原 initcall 表指针核对，最终两次运行也记录了真实接受与跳过。hwtimer、PCIe 已有本次实际硬件访问失败；其它项是明示的缺模型排除，不能写成它们都已发生过同类故障，更不能写成硬件初始化已成功。([容器格式修正](../../work/fx3-vm-20261101/fx3-audit/raw-initramfs-correction.json)、[七项原表与理由](../../work/fx3-vm-20261101/fx3-audit/minimal-linux-blacklist-evidence.json)、[最终实际跳过日志核验](../../work/fx3-vm-20261101/fx3-audit/final-runtime-independent-proof.json))

## 本机运行包已闭合，默认入口是有界终端探针

已部署目录为 [outputs/fx3-vm](../../outputs/fx3-vm/README.md)。QEMU 与 glib、pcre2、intl 共四个 Mach-O 文件组成运行闭包，采用相对 dylib 链接，构建目录 RPATH 已移除；本地 ad-hoc 签名校验后，使用最终二进制重新完成了两个正式配置。最终 QEMU SHA256 为 `78e36d4060aa4aae5a802c69cbd45beab3c69c47746371897e229e1c1eeb7e93`。原 FX3 Image SHA256 为 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`。([最终文件清单](../../outputs/fx3-vm/metadata/file-manifest.json)、[相对链接记录](../../outputs/fx3-vm/metadata/runtime-relocation.json)、[最终运行回执](../../outputs/fx3-vm/metadata/final-runtime-validation.json))

从 Finder 双击 [启动FX3最小研究虚拟机.command](../../outputs/fx3-vm/启动FX3最小研究虚拟机.command)，其设计行为是在终端运行约 12 秒后显示状态和日志路径并退出。**CLI 已实跑；`.command` 已生成并通过语法检查，Finder／Terminal 双击操作本轮没有 GUI 验收。** 它没有相机外观窗口，也不是持续交互的 FX3 shell。需要逐项复现时，使用实际交付支持的命令：

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --self-check
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --profile minimal-linux --seconds 12
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --profile app-loader --seconds 12
```

入口固定外盘 UUID、源内核及运行文件 SHA；缺失或变化时停止，独占自身锁并保存每次运行日志。`--seconds` 是 **1–30 秒的宿主壁钟观察窗**；没有达到 guest 标记或出现异常会返回失败，不把 QEMU 自身正常退出当作内核通过。原内核只读引用既有 stage47，实验 DTB 与最小 CPIO 位于包内 `share/`。按项目规则完成本轮第三方参考源码清理后，运行包和原输入仍与冻结摘要一致；四个 Mach-O 的相对依赖、签名和无构建目录 RPATH 状态也已只读复核，未额外重跑虚拟机。运行仍依赖原内核所在的已登记路径和本机 Python 3.14。([入口说明与源路径](../../outputs/fx3-vm/README.md)、[运行清单](../../outputs/fx3-vm/manifest.json)、[启动器](../../outputs/fx3-vm/run_probe.py))

复建环境时，需要重新取得固定版本的第三方源：QEMU 为 [11.1.2 官方归档](https://download.qemu.org/qemu-11.1.2.tar.xz)，SHA256 `731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016`；DTC 固定到 `b6910bec11614980a21e46fbccc35934b671bd81`。自己的完整补丁、构建参数、依赖来源及运行证据均保留，首次构建源码已按记录清理；**日常运行无需这些源码树或归档**。重新构建尚未在清理后执行，不据此声称二次构建已通过。([复建说明](../../work/fx3-vm-20261101/host/source-cleanup-support/README.md)、[宿主源清理与依赖核验](../../work/fx3-vm-20261101/host/third-party-source-cleanup-receipt.json)、[上游参考源清理](../../work/fx3-vm-20261101/upstream/cleanup-receipt.json))

本次没有全局安装包管理器、改变系统设置或征用 Claude 专用 Linux 环境，也没有新建常驻 Linux VM。运行配置为单个 Cortex-A35 vCPU、2 GiB RAM backing，无网卡、USB、宿主原始磁盘或目录透传。当前验收仅覆盖短时运行，长期稳定性、完整应用内存开销、图形性能和实际双击体验仍需各自证据。([主机与现有环境核验](../../work/fx3-vm-20261101/host/host-inventory.json)、[最终范围](../../outputs/fx3-vm/metadata/final-runtime-validation.json))

## 完整菜单的下一步从 UIPC 开始

现有证据将工作从“先搭一台 Linux 电脑”推进到了一个更具体的问题：**让 FX3 原库在当前 ARM64 guest 中取得正确的 UIPC、配置、模块和显示服务**。下一轮应以原 `libosal_uipc.so` 的 `/dev/uipc` 消费者为起点，逆向模块加载顺序、设备节点注册、ioctl、共享映射、消息结构和 CP 往返；先决定运行原驱动还是实现明确的软件协议模型。创建同名节点或返回恒定成功都不足以验证原程序的数据消费。([已观察 UIPC 边界](../../work/fx3-vm-20261101/fx3-audit/p12-ap-entry-independent-proof.json)、[原 init 与库元数据](../../work/fx3-vm-20261101/fx3-audit/asset-audit.json))

| 后续里程碑 | 需要关闭的具体缺口 | 达成标准 |
|---|---|---|
| 原 AP 运行环境 | UIPC 节点／模块／ioctl／共享映射／CP 协议；原 Backup、IMDB 与模块初始化顺序 | 同一次运行中原 AP 实际消费回复并推进，完成／错误／退出路径可复核；明确证明 main 与 qemu 目标分支 |
| 原厂界面与输入 | FX3 字体和资源、GPE／LZ77／OSD、屏幕格式、按键／拨盘、设置保存 | 原 UI 实际出帧，可见菜单操作产生对应状态变化，配置恢复与正常退出分别验收 |
| 成像与录像 | 虚拟图像源、原处理接口、缓冲／CP／AV、编码及媒体写出 | 同帧源输入→原处理消费→编码→原写卡→独立解码；录像还验证停止和文件收尾 |

这些是基于本轮阻塞和上游分层实现提出的**工程路径，尚未执行完成**。原 `av-cam` 和 `cpapp-b` 的独立运行环境意味着完整成像不能仅靠 Linux 应用加载通过来获得。此前 HEVC 参考针对 A7C II 的 4K29.97／25p VM 菜单往返，未证明 FX3 主录；此前 VENICE 成果也只恢复了部分外观数学与数据，私有 ISP、采样／插值与实际像素路由仍有缺口。VM 可以成为继续定位这些消费者与菜单逻辑的工具，真实编码结果、物理 ASIC 和实际刷入准入仍须独立验证。([已安装 Scrapling 调查](../2026-11-01-scrapling-fx3-research/README.md)、[VENICE 已恢复范围](../2026-10-31-venice-phayen-color-chain/README.md)、[本轮 CP／AV 资产](../../work/fx3-vm-20261101/fx3-audit/coprocessor-artifacts.json))
