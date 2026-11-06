# FX3 官方失败处理与条件救援能力

核查始于 2026-10-24 PDT，来源与本机只读回执保存在 `stage3-recovery/technical/`。用户 FX3 以自述“最新”对应的官方 7.02 为研究基线，尚未读回实际机身身份或程序。

## 官方升级失败是否都能重新刷入解决？

### Takeaway
不能一概而论。Sony 7.02 有明确的卡文件或升级顺序错误处理，但它不是任意自定义损坏的救砖承诺；较早的 Sony 维修通报甚至对特定升级后循环重启规定更换主板。

### Cited Findings
- 官方 7.02 的正常升级约六分钟，黑屏与访问灯 1→3→5 次闪烁是进度现象；不能仅凭黑屏判定已经变砖。若为 5 长 6 短或 7 长 7 短，以及目标机型错误提示，官方指出可能未先到 2.04/2.05 或文件拷贝不正确，指导移出电池/卡、准备另一张卡并重新准备正确更新文件；此操作仅对应官方明确列出的失败情形，不应套用于仍在正常写入的相机。[Sony 7.02 官方步骤及 If the Update Fails](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- 7.02 必须由 2.04/2.05 或更高进入；2.02 及以前不能直接跳至 7.02。当前包经卡槽 1 更新，不是旧版 PC USB updater 的通用替代。[Sony 官方当前更新页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)、[官方升级路径页](https://www.sony.com/electronics/support/software/00287451)
- Sony 日本当前版本历史承认 6.00 曾因部分机身升级失败于 2024-09-13 停发，经处理于 2024-10-09 恢复；6.02 另修复了特定 6.00→6.01、已登记用户 LUT 条件下不能应用 LUT、录像或操作的故障。后者属于可启动或应用层异常，不能与无 USB 的完全失联混为一谈。日本官方页已直接获取 HTTP 200，相关段落保存在访问回执；网页工具首次超时不影响随后官方原文直接获取。[Sony 日本完整历史](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)、[访问回执](../../work/sony-firmware-20261024/stage3-recovery/technical/web-access-receipts.json)
- Sony Europe B.V. 技术通报 **22PV028 Rev0，2022-11-18** 的公开预览可辨明：适用 FX3 **2.01**、FX30 **1.01**，症状是更新后反复重启而无法工作，服务方案为更换 SY 主板，并避免将替换板更新至所列问题版本。它不是 7.02 或任何自定义补丁的现行维修承诺。[公开目录与文号](https://store.professionalshow.com/en/ilmefx3)、[目录已展示的公开预览](https://store.professionalshow.com/ImagesNoZoom/TECHDRAW/BA026/BA026118.jpg)、[来源与预览哈希回执](../../work/sony-firmware-20261024/stage3-recovery/technical/official-source-receipt.json)
- 完整 PDF 下载实际指向索取联系资料的 contact form；没有提交表单、绕过登录或获取完整 PDF。只使用已公开显示的预览作必要概述，未使用任何服务凭据或未公开维修步骤。[公开目录](https://store.professionalshow.com/en/ilmefx3)

### Inferences
- 官方卡更新器仍能处理正确文件的错误，可以依照该型号、版本和实际灯号尝试官方流程；不能把“重备卡成功过”扩展到改坏 appFw、内核、文件系统、启动区或硬件供电故障。
- 能否同版本覆盖、能否从某个自定义损坏状态自动进入更新器、能否降级，必须分别核实；7.02 页面只说明已为 7.02 无须更新，没有证明这些能力。

### Gaps
- 没有找到 Sony 对 FX3 7.02 提供的公开任意故障重刷、任意降级或 BootROM 救援保证。旧 PC 更新页面部分访问超时/403，未将它当作已经可在本机运行的工具。

## 最新社区 Recovery 是否仍只接受已知原版或安装完成状态？

### Takeaway
必须区分旧 restore 和最新 Recovery。最新 A7C II 3.0.3 系列已增加以同一机身 checkpoint 为目标、从当前完整程序重新规划恢复的路径，因此某些未知哈希或混合状态可以进入恢复；它仍要求服务可达、可信备份及兼容文件结构，不能用于 FX3 原样刷入。

### Cited Findings
- 固定最新源码 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d` 的 `checkpoint.py` L15、L34–41 定义范围：appFw.so、cpapp-b.bin、68 个名称资源、选定外观参数；它明确不是完整相机文件系统或校准重置。`same_body()` 以机型与机身序列摘要绑定，版本限定 ILCE-7CM2 2.01。[checkpoint.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py)
- `checkpointjob.py` L87–94 读取当前两程序，明确不采用原固件来源/整文件哈希准入；L168–184 在同机身绑定后重新计算 current→target，并调用机内预检。这比旧 `program_state()` 仅允许原版/最终版的流程更宽，不能继续笼统说“未知哈希一律拒绝”。[checkpointjob.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L87)
- 当前与 checkpoint 两程序必须等长，按 4096 字节块寻找差异并分批形成旧/新字节窗口，再由原生 worker 检查现场文件大小和旧字节；因此文件截断、异长或读不完整并不在这条 in-place 恢复范围内。[checkpointworker.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py)
- `checkpointjob.py` L189–203 写两程序、完整读回并恢复资源/外观、处理 WBI；L214–226 再核盘、设置和 AP 内存 probe。LOADED 明确仅覆盖 AP probe，CP RAM 与拍摄行为仍需人工检查。[写入与重载验证](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L189)、[本轮直接读源码回执](../../work/sony-firmware-20261024/stage3-recovery/technical/latest-checkpoint-source-receipt.json)
- 最新 changelog 有维护者本人机身的 checkpoint/factory recovery 成功反馈，同时仍把故障用户的 `054C:0D68` 标为未识别；自己的正常/服务 USB 身份为其他 PID。维护者恢复成功不能自动当作该无法启动案例救回。[固定 changelog](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/docs/en/changelog.md)

### Inferences
- 在“服务可用、两程序能完整读取、文件长度相符、可信同机 checkpoint 与相关结构可解释”的条件下，最新源码有能力覆盖一部分中断或混合状态；不必因旧工具 needs_review 就认定物理损坏。
- checkpoint 的可信性是前提。升级后或已损坏时才创建的存档不自动成为健康原版；从另一机身抄来的文件、官方包里的默认 backup 目录也不代替本机备份。新准入更宽并不等于无需验证固件/数据布局。
- 即使采用更宽的恢复算法，仍需要活的服务会话、机内执行权限、WBI/冷启动和实际拍摄确认；不能从 Mac 能运行 Python 推出能救没有该入口的机身。

### Gaps
- 该 checkpoint schema、设置键与 worker 仍限定 A7C II 2.01，没有已复现的 FX3 7.02 适配。没有实际损坏的 FX3 文件、可信同机 checkpoint 或在线机身用于验证。

## FX3 服务候选是否能独立于 appFw.so 工作？

### Takeaway
比上一轮更具体：已完成四个入口的 **DT_NEEDED 传递闭包**，21 个唯一 ELF 节点中没有 appFw.so，支持继续研究先于主应用的服务入口。但动态插件、IPC、启动触发和实机权限仍未知，不能把静态无依赖当成已能救砖。

### Cited Findings
- 官方 FX3 7.02 rootfs 的 `init2` 在非零 MODE 下先挂载相关分区/装驱动，随后 `setup_bis || setup_senser`，再后台运行 bootin。`setup_senser` 仅在可读的 `/setting/sen/smode` 等于 UU 时启动 `/usr/bin/sen.elf`；其 `setup_bis` 分支还会格式化 log，不能作为无副作用测试来执行。[实际 init2](../../work/sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init2)
- 本轮 stdlib 只读脚本直接从已校验的 ext2 镜像读取 ELF，不加载 ELF、不执行固件。sen.elf 静态闭包 10 个文件、bootin.elf 12 个、libsencore.so 17 个、libpro00.so 9 个，合并 21 个节点，全部解析成功、没有 appFw.so 的 DT_NEEDED 路径。[复核脚本](../../work/sony-firmware-20261024/stage3-recovery/technical/trace_dependencies.py)、[完整闭包及各文件 SHA256](../../work/sony-firmware-20261024/stage3-recovery/technical/dependency-closure.json)
- sen.elf 动态引用 libsencore.so；libsencore 进一步使用 `libpro%02X.so`、libtestcmd_scn 等插件/命令库，后者仍有 dlopen/dlsym。静态闭包没有覆盖所有运行时插件及与其他进程的 IPC。[同一闭包与 runtime hints](../../work/sony-firmware-20261024/stage3-recovery/technical/dependency-closure.json)
- sen、bootin、libsencore 及多数服务库在 `/usr`，与 appFw 所在分区相同；rootfs 提供动态加载器与 libc 等基础依赖。若 `/usr` 整体不可挂载、rootfs/内核不能启动，这条文件级服务链会失去前提。[实际 mount 配置](../../work/sony-firmware-20261024/fx3-7.02-bounded-probes.json)、[依赖解析路径](../../work/sony-firmware-20261024/stage3-recovery/technical/dependency-closure.json)

### Inferences
- “只损坏 appFw 文件”与“损坏整个 /usr 或早期启动链”是不同恢复问题。前者有尚待验证的独立服务候选，后者不能指望同一 /usr 内的服务自救。
- 即使 sen 能工作，还必须证明相机在故障后能由外部进入相应模式，服务认证/文件读写可用，并能在不损坏其他本机数据的情况下回写。静态文件存在不满足这些条件。

### Gaps
- BootROM/WBI 到当前 init2 的实机路径、无主应用时可达的外部触发方式、全部动态插件与 IPC 仍未验证。未改 smode/updater 标志，也未尝试模式切换。

## 哪些故障适合现有软件恢复 哪些需要低层或售后？

### Takeaway
现有 Mac 环境可以支撑离线分析、校验、归档和后续服务工具适配；在准确 FX3 上未建立经失效验证的完整恢复链。能否恢复由仍然可达的入口和损坏范围决定，USB 仍有枚举本身不是恢复成功的证据。

### Cited Findings
- A7 IV 原作者确实公开了串行 BootROM 入口与自制 fastboot payload，可经 USB 备份/恢复 eMMC 分区，但明确 boot0 的处理尚未实现。这是 **ILCE-7M4** 的原始研究，不是 FX3 可直接使用的救砖包；涉及真实硬件接口和专用 payload，不能只凭同为 BIONZ XR 就外推。[A7 IV 原作者 README](https://github.com/DavidBuchanan314/ILCE-7M4-RE)
- 社区最新 changelog 对故障 PID `054C:0D68` 仍未识别，不能把它认成正常的 Senser 服务端点、普通 updater 或通用 fastboot。[维护者最新说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/docs/en/changelog.md)
- 当前本机具备的官方 BODYDATA 和提取程序属于公开升级源；它们不包含用户机身的实测完整存储备份、实际服务会话或故障日志。官方包内分区表还区分 setting/cert/lens 等区域，不能将升级文件当作机身所有独有数据的镜像。[现有官方包与配置回执](../../work/sony-firmware-20261024/fx3-7.02-bounded-probes.json)

### Inferences

| 故障状态 | 可以依据的恢复路线 | 对当前环境的判断 |
|---|---|---|
| 官方列明的卡文件/升级顺序错误，更新器仍可处理卡 | 型号/版本对应的官方重备卡流程 | 不依赖 Windows 刷机工具；需可用读卡器/正确卡和相机实际状态，不代表任意救砖 |
| 外观/参数设置异常，相机与服务仍可工作 | 同机健康 checkpoint 或经解释的有限参数恢复 | Mac 可研究/适配软件；现有 A7C II schema 不能原样用于 FX3 |
| 局部程序等长修改或 AP/CP 混合状态，服务仍可用 | 最新 checkpoint 式 current→可信 target 的完整重规划、现场预检与读回 | 有工程依据可开发 FX3 对应恢复；没有已经验证的 FX3 安装/恢复成品 |
| 主应用不启动，但 rootfs、/usr 和 sen 候选可能仍工作 | 验证先于主应用的服务分支，再验证认证和恢复 | 静态候选；未证明故障时可达，不承诺可救 |
| 只剩未知 HID PID，普通服务不通 | 先识别具体接口/协议/启动阶段 | 当前没有对应已核验 FX3 协议/payload；不能向未知接口试发写入命令 |
| /usr 文件系统、内核、rootfs、WBI 或启动区损坏 | 独立早期加载器、型号验证的低层恢复或售后 | A7IV 的方法只能作研究线索，当前未具备 FX3 完整链 |
| 无上电、供电/存储芯片/主板物理故障 | 维修检测、硬件修复或主板更换 | Mac/Python/官方 DAT 无法代替硬件检测和机身校准 |

### Gaps
- 没有用户机身的独立救援接口验证、完整备份、FX3 BootROM payload 或适配过的 checkpoint。未进行故障注入、UART/短接、存储芯片读写或任何相机操作。结论不是所有情况只能送修，而是现有证据只支持条件恢复，不能支持“现在刷坏也保证能救”。
