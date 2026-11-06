# 当前 Mac 环境的 FX3 故障诊断与恢复能力

## 现有电脑和软件是否已经构成可用的救援环境

### Takeaway
当前环境已能做离线固件解析、原文件与候选差异检查、日志分析和缓存 USB 身份观察，但尚不是经过 FX3 实机验证的服务恢复环境。Python 或 USB 设备可见，只说明前提的一部分，不代表服务认证、临时模块运行和文件恢复已经可用。

### Cited Findings
- 本次只读盘点得到 macOS **27.2 / 26B5091g**、arm64、Mac14,9、16GiB 内存；Python **3.14.6**，Xcode **27.0 / 27A5228h**，Apple clang 21。查询仅使用系统元数据，不输出机身或电脑序列号。[本机盘点回执](../../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)
- 当前 Python 元数据有 **PyUSB 1.3.1**、PyCryptodome 3.23.0；未发现 libusb、libusb-package、Capstone、pyelftools 的安装元数据。`ctypes.util.find_library('usb-1.0')` 返回空，`/opt/homebrew/lib` 与 `/usr/local/lib` 的常见 libusb 路径均未命中；没有调用 PyUSB 打开设备。[元数据](../../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)、[常见路径查询](../../work/sony-firmware-20261024/stage3-recovery/environment/known-path-probe.json)
- PATH 与检查的常见路径未见 PMCA、REA、Ghidra、Wine、aarch64-linux-gnu-gcc、ld.lld；`/Applications` 与用户 Applications 的名称过滤未发现 Parallels、VMware、VirtualBox、UTM、CrossOver。没有启动或创建虚拟机，也没有遍历用户其他私人目录。[查询范围与结果](../../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)
- 当前缓存 IORegistry 没有 Sony VID `0x054c`，也未出现本次名称筛选覆盖的 USB-UART、常见调试器或 USB 读卡器。此检查没有打开 USB 接口或发送相机命令；不说明用户没有未连接的设备、非 USB 读卡器或其他未覆盖硬件。[缓存设备回执](../../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)
- libusb 官方区分“取得设备引用”和“打开设备句柄”：能枚举的设备仍可能因权限、拔出、其他程序或驱动占用而不可操作。打开、接口占用、服务协议认证和还原文件是不同阶段。[libusb 官方设备处理说明](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html)
- 固定版 MDHan `session.py` 定义 `UsbWaitTimeout`，等待指定 PID；其会话进入与检测使用 `0x0336`、PyUSB/libusb backend。故 `0336` 超时是没有到达工具所期望的 USB 身份，不能单凭该错误诊断持久程序已经损坏。[固定会话源码](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/macfl23/session.py)、[本次源码指纹与相关行](../../work/sony-firmware-20261024/stage3-recovery/environment/tool-protocol-source.json)

### Inferences
- 已确认具备的是离线研究和无设备命令的观察能力；实际 FX3 的 USB 打开、Senser 身份切换、两次认证、模块权限和恢复读写仍未验证。缺失的 Python/USB 软件可以补装，但补装成功不能替代后三类实机验证。
- `054C:0D68` 这样的 USB 标识若仍出现，只说明系统能取得某种 USB 身份；既不证明相机已进入 `0336` 服务，也不证明它是不可恢复的硬件砖。不能将“Mac 能看到 HID”简化为“Mac 能写回程序”。
- 当前 clang 是 Apple 平台工具链；尚未确认可直接链接 Sony Linux 或 BootROM/裸机载荷所需的完整交叉链接器、sysroot 和目标兼容运行库。宿主工具或语言本身不构成已验证的相机载荷。

### Gaps
- 查询覆盖仅限当前 PATH、常见安装路径、已知应用目录及 Python 元数据，并非所有磁盘位置的穷举。未命中不等于全机绝对没有相应工具。
- 没有实机服务认证、驱动占用或读写能力测试；没有已确认的 Windows 环境或当前连接的专用串口、探针、编程器，未推断用户实际拥有的未连接硬件。

## Sony 官方更新流程与这台 Mac 的兼容性如何区分

### Takeaway
对已在较新固件的 FX3，官方 7.02 走存储卡更新；Mac 可负责下载和检查文件，不依赖旧版 USB 更新驱动。当前 macOS 27.2 不在已核查的 Sony Camera Driver 或旧 FX3 USB 更新器声明的系统范围，不能把它当成已支持的 USB 救援平台。

### Cited Findings
- FX3 7.02 官方文件为 `BODYDATA.DAT`，811,876,768B，2026-03-17 发布；要求使用机内更新、slot 1、正确文件和电量条件。版本 2.02 及以前要先经 2.04/2.05，已为 7.02 时无需更新。官方说明给出了特定文件/前置版本错误处理，但没有承诺任意自定义损坏可通过该文件恢复。[FX3 7.02 官方说明](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298559)
- Sony 当前 Camera Driver 页面明确列出 macOS **11、12、13、14、15、26**，同时支持 Apple silicon 与 Intel，且只适用于明确链接到该页的更新，不是任意机型/恢复程序的通用驱动。[Sony Camera Driver 官方兼容范围](https://www.sony.com.sg/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00268924)
- FX3 从旧版本经 2.04/2.05 的 Mac USB 更新器页面自身只列 macOS **11、12、13**；要求 Camera Driver，并在 Apple silicon 上说明安全策略调整。该旧更新器的范围与当前驱动页范围不可混同。[FX3 旧 USB 桥接更新器](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280268)
- PMCA 原作者说明 macOS 发行版测试少于 Windows，并区分 mass-storage、旧 updater shell 与 service mode；service mode 要求自定义 USB 驱动，旧 updater 注入路径不支持 CXD90057。这不能否定新服务模块方法，也不能把旧 updater shell 当 FX3 通用救援器。[PMCA 原始说明](https://github.com/ma1co/Sony-PMCA-RE/blob/master/README.md)

### Inferences
- 当前 Mac 可参与官方卡更新材料准备，但相机是否还进入官方更新器、是否接受该版本、卡与电池是否满足要求，均是机身端条件。下载成功不等于具备自动重刷或降级能力。
- 不应为了这一尚未验证的恢复方案先修改本机安全策略、安装内核驱动或创建 Windows 虚拟机。Windows 或 VM 最多可能解决某类主机驱动/工具兼容，不能修复相机侧已无法提供的服务；后续仍需按具体工具和机型确认。

### Gaps
- 未证明 Camera Driver 在 macOS 27.2 可用，也没有安装或加载它；没有尝试降低 SIP、启动安全策略或修改权限。
- 尚未确认用户手边可用的兼容存储卡、读卡器、稳定电源及数据线。本次没有格式化卡、复制更新文件到卡或发起更新。

## 已保存的固件材料能恢复什么 还缺什么

### Takeaway
现存材料是经过检查的官方通用固件及其提取程序，可以作为有限程序恢复研究的原始字节来源。它们不是用户这台相机的实机备份，尚不能据此宣称可以还原全存储、设备特有校准或所有未知中间状态。

### Cited Findings
- 完整官方 7.02 包 811,876,768B 与解密 FDAT 808,704,512B 均仍在；下载回执保留 HTTPS 来源和包 SHA256。`appFw.so` 79,015,712B、`cpapp-b.bin` 15,980,568B 及服务库、启动程序均在，分区已有包内 CRC 复核结果。[官方下载回执](../../work/sony-firmware-20261024/fx3-7.02-download-receipt.json)、[材料存在与长度复核](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)、[分区检查](../../work/sony-firmware-20261024/stage2/extraction/official-partition-verification.json)
- 本轮重新计算的 `libJiritsu.so`、`sen.elf`、`bootin.elf` 小文件 SHA256 与原提取清单相符；没有无故重算整个多 GB 工作目录。[本轮小文件复核](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)、[提取清单](../../work/sony-firmware-20261024/stage2/extraction/supplementary-extracted-manifest.json)
- 任务目录中未发现命名包含 backup 的文件；更重要的是此前回执明确没有相机访问，现阶段没有这台机身身份、程序指纹、NVRAM/校准、全 eMMC 或 boot 区的实机读回证据。包内工厂默认/地区数据与实机读回不是同一来源。[材料范围及缺项](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)、[来源回执](../../work/sony-firmware-20261024/fx3-7.02-download-receipt.json)
- MDHan issue #7 的 0.2.2 恢复失败案例中，用户记录原版备份完整但等待 0336 失败，且工作流进入 needs_review。该例说明“有备份”和“当前工具能到达并执行恢复”需要分别核验，不代表最新专用 recovery 的所有能力；具体故障与最新变化由案例分支整理。[原始恢复失败记录](https://github.com/MDHan/a7c2-fl23-macos/issues/7)

### Inferences
- 若未来已证明服务仍可用、机身指纹相符且损坏只在已知文件窗口，现存官方原字节可帮助构造受约束的恢复候选；这不是当前已具备的 FX3 还原包。
- 自定义补丁造成未知或部分状态时，上述版本的普通 restore 流程可能主动拒绝恢复；专用 recovery 是否接受等长未知或 AP/CP 混合状态，应按它自己的恢复条件判断。即使后续代码允许这类恢复，本机仍没有来自同一机身、可核实的原始程序与参数 checkpoint，也未验证服务可达。不能通过编辑 state.json、跳过哈希检查或把“未知”改成“prepared”来补足这些材料。
- 若借鉴 A7 IV 的 BootROM/fastboot 研究，仍需要针对 FX3 验证的 payload、可达的接口/触发条件、符合电气要求的硬件，以及对应存储与机身独有数据。当前 Mac 的编译和 Python 能力不能替代这些材料；技术分支负责核验该 A7 IV 方法的准确范围。

### Gaps
- 尚无用户机身的可信恢复 checkpoint、全存储、boot0/bootloader、校准/唯一身份材料，也没有记录可恢复的 FX3 半写入状态或独立恢复通道。
- 不知道发生故障后是否仍有足够可用的 rootfs、usr、WBI、服务组件与权限；不能把单文件补丁恢复推及整个文件系统或启动区损坏。

## 按故障状态 现有环境能做到哪一步

### Takeaway
目前可以确认的是诊断和准备材料；服务仍存活的有限软件恢复属于待验证候选。完全失联、启动链或存储损坏的情况，当前没有可交付的 FX3 自助救砖能力。

### Cited Findings
| 故障状态 | 当前已具备 | 仍需具备或验证 | 现阶段判断 |
|---|---|---|---|
| 主机工具报错 机身正常且未开始写入 | 缓存 USB 身份、日志/阶段分析、原始文件核对 | 正确 backend、接口可用、准确服务 PID 与协议 | 可诊断；不应先认定相机变砖 |
| 功能异常 但机身与服务均正常 | 官方程序原始字节、只读审计工具 | 此机备份、准确 FX3 指纹、实际认证和恢复工具接受其状态 | 有条件的软件恢复候选，未实机证明 |
| 黑屏但仍出现 HID/USB 身份 | 可观察设备描述信息；当前无相机可测 | 该身份代表的启动阶段、能否进入服务、模块权限、独立恢复可达性 | 不能仅凭 USB 可见宣称可救 |
| 半写入或未知 AP/CP 状态 | 可离线对照已知字节/哈希 | 相机可读回、同机身可信 checkpoint、受约束的专用还原路径 | 旧版常规 restore 有拒绝实例；专用 recovery 需按自己的条件验证 |
| usr/rootfs/WBI/启动区损坏 或完全无 USB | 一般离线原厂包和日志分析 | 已验证 FX3 低层入口、专用载荷/接口、原存储及独有数据；可能需要专业硬件/维修 | 当前不能承诺本机救砖 |

表中“当前已具备”来自[环境回执](../../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)与[材料回执](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)；枚举与实际访问的区别依据[libusb 官方说明](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html)，现有恢复被状态阻止的实例见[MDHan #7](https://github.com/MDHan/a7c2-fl23-macos/issues/7)。其余“仍需验证”是将已知入口和材料映射到故障状态的工程推断，不是做过故障注入或维修的结果。

### Inferences
- 最有用的准备顺序是先取得准确机身身份、正常状态的原始程序/必要设置读回，再验证非破坏性的诊断入口与退出；随后针对预定补丁的具体失败状态建立恢复证据。工具安装和静态备份只是这一过程的前提。
- 当前不需要为假设的故障先创建虚拟机或购买通用编程器；先确定 FX3 的真实入口与目标载荷，才知道新增硬件是否有用。

### Gaps
- 本轮没有向相机发任何命令，也没有做真实故障、恢复、重刷、短接或硬件接入实验；当前评估是准备程度与适用条件，不是维修验收。
