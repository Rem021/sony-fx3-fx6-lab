# 研究 FX3 的 HEVC 主录与局部写入

核查日期：2026-10-24（America/Los_Angeles）。研究基线为 Sony 官方 FX3 7.02；用户自述机身为“最新”，尚未读回机身版本与程序指纹。

2026-10-25 更新：[双机与独立仿真复核](<索尼 FX3 双机协作与HD HEVC仿真复核.md>)已确认 HD420、29.97p、16Mbps 的基础检查及原主流 Open 参数构造通过；HD422 则出现254／254字段缺口。仍无硬件接受或成片。下文对固定版本旧 restore 状态限制的描述是当时审计结果；最新 main 已增加等长未知／混合状态的 checkpoint 恢复与限定范围的内建原厂区域恢复，见[最新恢复评估](<索尼 FX3 刷机失败与救援研究.md>)，二者均不能原样用于 FX3。

**1080p、约 30p 的 H.265 独立主录已经有具体的局部改造研究路线。** 本轮从官方包提取到真正程序，并确认底层参数库能够表达 HD HEVC 10bit，编码器启动命令也有区分主流与代理的 HEVC 路由。这比“60p 可以，所以 30p 应当可以”的通量推理更有依据，但还不能证明全部参数检查、硬件编码和成片封装接受该组合。其他项目采用的服务模块与局部文件写入机制，也在 FX3 自身程序中找到对应结构，因此研究不必以重加密整包或跨刷系统为前提。当前交付是可复核的路由、写入审计和只读工具，**尚未生成可安装的 H.265 补丁，也未完成实机写入与恢复验证**。([本机路由证据](../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)、[FX3 服务入口证据](../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json))

## 底层已有 HD HEVC 主流参数与编码命令路由

“已有 60p H.265”确实支持优先追踪软件限制：官方 FX3 有 4K HEVC 60p，也有 1080p HEVC 10bit、9/16Mbps 代理。后一条已证明相机存在实际工作的 HD HEVC 管线，不过代理需要伴随主片，不能等同只录一份 HEVC 主片。常用“30p”指 NTSC 29.97p；精确 30.000fps 是另一项要求。([Sony 录制表](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)、[Sony 代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html))

本轮已按真实文件系统读取 `/usr`、rootfs 的 ext2，以及 `/system`、`/cp` 的 FAT12；五个原样分区的长度与 CRC32 均匹配包内官方检查表。核心提取物包括 79,015,712 字节的 `appFw.so`、3,517,008 字节的 `libmpr.so` 和 15,980,568 字节的 `cpapp-b.bin`。分析依据是 ELF 重定位、实际分支、表项和调用关系，已经超出包头、文件名与孤立字符串。([官方分区一致性结果](../work/sony-firmware-20261024/stage2/extraction/official-partition-verification.json)、[核心程序清单](../work/sony-firmware-20261024/stage2/extraction/extracted-manifest.json)、[追加库清单](../work/sony-firmware-20261024/stage2/extraction/late-selected-manifest.json))

| 已定位的层级 | 实际代码结果 | 对目标的意义与边界 |
|---|---|---|
| `libmpr::GetVideoParamComb` | HEVC＋1920×1080＋10bit＋Long GOP 返回 VPC6（4:2:0）或 VPC8（4:2:2） | 有真实输入分支和配置表；此函数不检查帧率、码率 |
| `GetCodecInfoForCodec` | HEVC 主流选择 codec ID15，代理选择 ID18 | 主流和代理存在各自的 HEVC 选择，当前选择器未按 HD 拒绝 |
| 编码命令组装 | Open、Start 等调用上述选择器，分别处理主流与代理 | 已连接到实际编码器命令组装；未向硬件发命令 |
| MP4 writer | VPC6/8 有 level 分派；存在与 16/9Mbps、29.97相关的配置路径 | 封装层能表达对应配置，未证明独立主录全链完成 |

VPC 是程序内部的视频参数组合编号。上述映射由真实表项和控制流交叉确认，详见[编码参数映射](../work/sony-firmware-20261024/stage2/modes/libmpr-codec-mappings.json)、[配置表](../work/sony-firmware-20261024/stage2/modes/libmpr-codec-table.json)、[编码命令调用者](../work/sony-firmware-20261024/stage2/modes/libmpr-codec-callers.json)及[writer 分派](../work/sony-firmware-20261024/stage2/modes/libmpr-writer-vpc-routes.json)。**4:2:2 类型或共享 8K 类型存在，不代表 FX3 已支持这些全部录制能力。**

工程上最值得先验证的是现有 4:2:0 10bit、16Mbps、29.97p 的 HD HEVC 配置作为独立主流，保留已经工作的 HD 读取和缩放路径；更高码率与 4:2:2 应另作验证。这里需要改造的是上层模式选择、参数路由及一致性，不能直接从较低数据吞吐量推出只差一个开关。

## 30p 的限制已经进入参数转换 但真实普通设置路径仍未全解

`appFw.so` 的主录格式枚举没有独立 HS HD。共享 `convert2MovieMainParams` 的 HS 4K 分派中，60/50、24、120/100p 有质量配置，30/25p 则进入错误通知路径；对应例程含断言处理，不只是让菜单变灰。**但该非模板转换的两个直接调用者用于录制状态和剩余时间查询，不能把它称为最终编码器拒绝 30p。** 真正的 `SetMovieRecParam` 调用、库实现和格式 builder 已定位：慢快路径也见 30/25 排除，普通路径复用预构造字段，其 model getter 与参数的完整绑定尚未恢复。([全部路由与作用域](../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)、[真正设置 builder](../work/sony-firmware-20261024/stage2/modes/actual-format-builder.asm))

代理转换已有更直接的证据：它写入 HD HEVC 的 VPC6，并把输入帧率传给输出，调用者同时包括查询和真实设置 wrapper。因此“29.97p 主片生成 29.97p HEVC 代理”的预期得到代码支持，实际文件仍需拍摄后检查。局部 feature 工具仅解析到 47 个匹配 getter、11 个注册项；其中未见 HEVC 开关，不足以推断完整能力表没有该开关。([代理与 feature 结果](../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)、[定位方法原始文档](https://github.com/leogenot/sony-a7iv-feature-research/blob/12582457829e34eae7211df5b0c599fa46b7e5e1/docs/PRODUCT_CLASS.md))

候选补丁至少要保持模式选择、查询、真实设置、主流 VPC、帧率、码率和 writer 元数据一致。只改菜单或把 60P 常量换成 30P，可能仍在查询阶段触发错误。当前没有把尚未解释的普通设置字段或地址拼成试刷补丁；地址记录仅用于定位对应模块代码，不是可复制的刷机偏移。只读复核器已在本次两份真实程序上运行，严格核对输入哈希后输出相应路由。([复核脚本](../work/sony-firmware-20261024/stage2/modes/inspect_mode_routes.py)、[实际输出](../work/sony-firmware-20261024/stage2/modes/routing-evidence.json))

## 其他项目的局部写入流程可借鉴 现成补丁不可直接套用

A7C II 项目采用服务通道上传临时本机模块，再局部改写现有程序；它不要求把修改后的整个 UFU 重加密后交给官方卡刷更新器。因此，公开解包工具缺少 `encrypt()` 不能单独否定这条路线。本轮审计固定在 QAQLeonard `9f69e9dc…`，并对照新 HEAD `b311407a…`，四份关键实现保持相同字节。([固定安装器](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c)、[来源与内容哈希](../work/sony-firmware-20261024/stage2/write-audit/source-receipt.json))

FX3 7.02 自己的 `libJiritsu.so` 也有对应结构：满足路径、文件类型和忙状态等条件后写入临时模块，完成 `fsync/close`，再调用 GLIBC 的 `dlopen`。这是实际代码分支及动态导入结果，不只是发现同名字符串；但上游服务认证、模块实际接受、执行权限与正常退出仍未实机验证。“临时模块”也不等于仅写 RAM，不能默认 `/tmp` 完全不涉及存储写入。([FX3 服务条件与动态导入回执](../work/sony-firmware-20261024/stage2/write-audit/fx3-jiritsu-static.json))

| 可借鉴的措施 | 源码中的实际作用 | FX3 适配仍需完成的部分 |
|---|---|---|
| 型号、版本、整文件哈希与旧字节窗口 | 拒绝错误程序、越界或重叠改动，核对候选整文件 | 以 FX3 自身程序和已解释的编码语义制定新规范 |
| 原文件与参数备份、完整读回 | 保留恢复材料，确认磁盘候选与预期一致 | 不能以官方包或设置导出代替机身恢复材料 |
| 固定白名单、原 inode 局部写入、fsync | 缩小写入范围，落盘并检查窗口 | 存活 worker 的反向回写不覆盖掉电或进程消失 |
| WBI 诊断、冷启动及磁盘与内存核验 | 避免磁盘已更新但热启动仍运行旧内容 | FX3 的 WBI 条件与冷启动效果需要重新验证 |

安装器用 `pwrite` 逐窗口改原 inode，再分别同步 AP/CP 文件；它不是双槽更新或多文件原子切换。部分构建的机内验证只覆盖窗口，必须依靠主机全文件读回。现有 restore 还要求服务可用、文件属于已知且一致的原版或安装状态，未知或部分写入状态会被拒绝。([写入与回写](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c#L101)、[完整读回与状态判定](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/workflow.py#L208)、[Mac 状态机](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/STATE-MACHINE.md))

本轮自写审计器已用真实 FX3 文件对照 A7C II 的 40 个写入窗口：型号、版本及两份整文件指纹不符，另有越界和旧字节不符，整体明确拒绝。它只读取本地文件，不生成补丁、不含 USB 操作。可迁移的是这些保护方法，不能照搬另一机型的偏移、目标字节和恢复条件。([移植审计器](../work/sony-firmware-20261024/stage2/write-audit/audit_patch_portability.py)、[实际比较结果](../work/sony-firmware-20261024/stage2/write-audit/fx3-vs-a7c2-compatibility.json))

## 启动前维护分支是恢复候选 仍需证明故障时可达

FX3 rootfs 的 `init2` 在特定 `/setting/sen/smode=UU` 条件下，先启动 `sen.elf`，随后启动 `bootin.elf`。这使“主应用损坏后仍有服务”的研究有了具体候选，不能断言所有服务都依赖 `appFw.so` 成功运行。但两个程序异步启动；`sen.elf` 虽没有直接依赖 `appFw.so`，仍有动态插件、间接依赖和 IPC。BootROM/WBI 是否走该路径、无主应用时如何从外部触发、认证和恢复是否可用，尚未证实，不能靠直接改启动标志来假定救援有效。([启动脚本与依赖回执](../work/sony-firmware-20261024/stage2/write-audit/fx3-startup-recovery-static.json))

因此，进入持久程序修改前，需要在准确机身身份与程序指纹下核实服务能力，先验证仅诊断用途的最小模块、权限、清理和正常返回，再证明补丁可能造成的具体失败状态仍可恢复。只有这些条件与编码效果都成立，才能把局部写入流程发展成可靠安装包。当前缓存 IORegistry 未发现 Sony USB 设备；本轮未打开相机接口、发送服务命令或执行固件代码。([USB 前提回执](../work/sony-firmware-20261024/stage2/write-audit/sony-usb-presence.json)、[完整写入审计](<../research_notes/索尼 FX3 编码模式与写入研究/writing.md>))

## 后续应验证最小主录改造

下一项关键工作是还原普通设置 builder 的字段绑定，形成可再生的 HD HEVC 主录参数原型，再分别验证参数接受、编码输出、MP4 解码、声音同步、分段、长录与冷启动状态。以既有 16Mbps、4:2:0 10bit 管线作为首个目标，可以减少同时改变的因素；通过后再讨论质量扩展。为了这个目标，没有必要先把 ZV-E1 整套换成 FX3 系统。

本轮实际工具为 ELF 分析、Capstone 与自写只读解析器，没有运行 REA 会话或向外上传固件；临时参考源码及独立分析环境已按约移除，保留固定来源、哈希、反汇编和不依赖第三方包的复核脚本。可沿[模式笔记](<../research_notes/索尼 FX3 编码模式与写入研究/modes.md>)、[提取笔记](<../research_notes/索尼 FX3 编码模式与写入研究/extraction.md>)和[写入审计](<../research_notes/索尼 FX3 编码模式与写入研究/writing.md>)继续推进。现在的结论是：**实现方向已有代码依据，写入方法已有可适配结构；稳定录像和失效恢复仍是交付可刷固件前的实机门槛。**
