# FX3 双机协作与 HD HEVC 仿真复核

核查日期：2026-10-25。样本为官方 FX3 7.02，未读回实机版本。本报告记录 UU 远程协作及 Mac 独立复核；Windows 当日新任务已完成并取回最终报告，不能将旧证据包与这份新任务回执混同。

**1080p、29.97fps、H.265、4:2:0 10bit、16Mbps 已取得原固件参数构造层的正面结果。** 基础检查通过，原程序能组出对应的主流 Open 参数包。仍未执行实际编码器 Open/Start，也没有成片或可安全刷入的补丁。HD 4:2:2 的相同路线出现明确的字段缺口。

## 双机之间实际完成的交接

通过用户已连接的网易 UU 远程，核对 Windows 现有 Codex 会话“查找 FX3 固件逆向案例”，沿用项目 `C:\Users\owo\Documents\Codex\2026-10-16\rea-2`。没有创建虚拟机或复制新项目。

已发送 `outputs\FX3-READONLY-TASK.txt`，UU 显示“已发送”。文件 SHA256 为 `ae0a0cf0b826ecc0d768e648deff91abcb58cdf22e817f6ae36bdd8cda544c04`。任务限定主机环境与缓存 PnP 信息盘点、既有离线代码研究、保留旧输出；禁止驱动和安全设置变更、相机服务认证、模式切换、读写机身及刷机。随后已在该 Codex 会话提交读取任务文件的消息，最终完成回执和[新报告](../work/sony-firmware-20261024/stage4-windows-collab/from-windows/FX3-HD-READONLY-REPORT.txt)均已取得。后续由用户提交的 MSC 缓存盘点也已完成，见下文。

已收到该机旧的 `FX3-7.02-4K30-H265离线研究证据.zip`，303,060 字节，SHA256 为 `785c3b3fdb5e879dd7acda3b782001f09e3dce8210c71d6104ce141d77ba4865`。ZIP 包含 43 个普通文件，CRC、内部清单哈希正常，无路径穿越、符号链接或特殊项。三份核心输入与 Mac 官方提取物的哈希一致。旧任务集中于 4K30，本轮另补用户真正关心的 HD30 主录目标。

远程输入最初出现剪贴板、输入法及点击传递问题。切换输入法并延长点击时间后成功提交。用户另明确允许只为 UU 远程添加 Mac 输入监控权限，并完成原生验证。系统界面回读确认 UU 为开启、Discord 仍关闭；已按系统提示重启 UU 并重新连接同一 Windows。部分合成键盘和点击操作仍不稳定，不能据此认定输入问题全部源自缺少该权限。

本轮 Windows Codex 已找到任务原文，明确按 HD 主录目标和只读边界执行。已取回 [host-inventory.json](../work/sony-firmware-20261024/stage4-windows-collab/from-windows/host-inventory.json)，4,340 字节、SHA256 `fb0b5739a3fc4a9a6719b0e17240f128f78f4d4983b72d38229055db3096f734`。回执为 Windows 11 专业版10.0.26200、x64，i7-14700KF（20核、28线程），Codex 默认 Python3.12.14。默认 Python 没有相关逆向依赖，但后续在现有项目目录找到 Unicorn2.1.4、Capstone5.0.9、pyelftools0.33，无需新安装。缓存 PnP 仅发现 Sony `054C:0DF2` 的 DualSense Edge 手柄及其复合／HID／音频接口，没有发现相机；这不能当作 FX3 服务认证、驱动访问或救援验证。没有为该盘点打开相机接口、更换驱动或发送机身命令。

Mac 的工程说明另已通过 UU 发送至本次 Windows 协作目录，界面显示 `MAC-FX3-HD420-RESULTS.txt`“已发送”；补充消息是否成功提交与该文件是否已被 Windows Agent 读取，需另看会话回执，不能仅凭传输完成认定。

用户接入相机并选普通 MSC 后，再次在该 Windows 会话提交仅查询缓存 PnP 的任务。新目录为 `outputs\fx3-pnp-readonly-20261025T095416Z`；取回三份文件后，核对到总线缓存型号 **ILME-FX3**、`054C:0DA1`、Microsoft **10.0.26100.9444**、已签名 `USBSTOR`、Present／OK及错误码0。之前四个手柄接口已明确排除。原始[新 JSON](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json) SHA256 为 `01b5b580eb4378a40c8e9ea751be9201ccca8a52e8efe8a415015c6fc93ff415`；脚本仅查 CIM、驱动元数据和缓存总线描述，未打开相机接口、列举存储卡、读取素材、认证、切模式、改驱动或刷写。旧盘点哈希在两端保持不变，见[核验回执](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/transfer-review.json)。这完成普通连接阶段，尚未读回实际固件版本或证明任何恢复入口。

交接、文件指纹及权限状态见[双机回执](../work/sony-firmware-20261024/stage4-windows-collab/handoff-receipt.json)。

## 独立复核结果

没有直接执行回传的 Windows 脚本。审阅核心实现后，在 Mac 隔离环境重写适配器，以 Unicorn 执行有限的 AArch64 函数片段。固定源文件哈希，限制执行范围、可写内存、指令数和时间；未知调用及系统调用停止，无 USB、设备、网络或 MMIO 转发。部分查询、日志和 C++ 容器访问由明确记录的替身处理，编码包中的尺寸、codec、帧率、色度及位深则由原固件指令生成。

完成 176 例函数实验，10 项预期核验通过。原 Windows 80 例查询转换器的原版／内存候选结果全部复现一致。内存候选只改变仿真地址空间，原始文件哈希保持不变；该转换器的调用者包括查询入口，不能把它成功返回当成真实录像 setter 已闭合。

| 组合 | 基础参数检查 | 原 Open 参数包 | 判断 |
|---|---|---|---|
| UHD 4:2:0 10bit、29.97、100M，正控制 | 返回 0 | 3840×2160、codec15、色度0／位深1 | 作为函数级对照，未测硬件 |
| UHD 4:2:2 10bit、29.97、100M，正控制 | 返回 0 | 3840×2160、codec15、色度2／位深1 | 作为函数级对照，未测硬件 |
| **HD 4:2:0 10bit、29.97、16M** | **返回 0** | **1920×1080、codec15、Frame3、NTSC1、色度0／位深1** | **主目标的参数构造层通过** |
| HD 4:2:2 10bit、29.97、16M | 返回 0 | 尺寸与 codec 有值，但色度／位深为254／254 | 不具备有效包的证据，不能宣称支持 |

HD420 输入为 VPC6、VQuality6、Frame3。真实 `GetVideoBitrate` 返回16000，帧率转换输出30000／1001；主流选择 codec15，代理选择 codec18。本次调用的是主流 `SetEncOpenParam`，594 条指令后返回。输入质量枚举6由原转换函数转成 API 枚举22，不能把两个枚举的不同数值当作异常。完整实参、0x98字节输出包、实际调用与逐字段写入 PC 见 [HD420 调用证据](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)。

HD422 的问题由直接 helper 和原始指令交叉确认：`GetChromaFormat(8)`、`GetVideoBitLen(8)` 均返回254；两个常量位图也排除 VPC8。通用组合选择器存在 VPC8，并不代表后续转换完整支持它。

另一个缺口是 app 原常量表16→VQuality6，而 MPR `GetVQuality(16)` 返回255。12→2→12000、100→12→100000的对照排除了简单单位误用；尚不清楚设计原因，也未证明实际 setter 必经这条反向 helper。不能随意把255替换成6就视为修复完成。HD100M 的 metadata 仿真停在未允许的 printf 提示调用，不能将隔离停止误报为相机拒绝。

## 对实机与恢复判断的影响

Windows 后续报告新增了 MP4／MPF 构建层结果：HD420 的16M／9M下游参数可继续转换；30M／50M走 level 提示分支，HD422仍有254／254及MPF找不到对应项的问题。该端称完成148次有边界的离线调用、23项一致性观察，51个受保护旧文件哈希不变；这些计数来自其最终报告，原始全部JSON尚未回传，不等同本机独立重跑。先前“Conv ERROR”的差异对应码率／质量枚举不同，不能概括为16M目标也失败。

已取回普通设置桥反编译及调用关系，并在 Mac 对入口、跳表和原指令复核：`appFw @0x2e6e5d8` 将 VPC／VQuality／Frame 写入 `movieRecParam +0x170/174/178` 后交给真实 MPR setter。原版格式6选择VPC5／7，格式8选择1／3，没有主录6／8分支；通用质量输入2→VQuality6，输入13→VQuality12，帧输入15→Frame3。该静态字段链现已闭合，UI／模型如何产出输入及真正 Start 仍未闭合。此桥本身未调用 `GetVQuality(16)`，故反向 helper 缺口未必阻断该路线。证据见[真实设置桥](../work/sony-firmware-20261024/stage4-windows-collab/from-windows/app-actual-setter.c.txt)及[调用关系](../work/sony-firmware-20261024/stage4-windows-collab/from-windows/app-setter-and-converter-callers.json)。

结果加强了“优先适配现有 HD420 16M 管线”的工程依据；下一步仍须闭合模型 setter、主录 Start、音频与 writer 的一致性，再验证真实编码器接受及可解码文件。当前实验没有验证实际 HEVC 码流、声音同步、分段、连续录制、温度、冷启动或恢复。

2026-10-25 再读上游 [v3.0.3 发布页](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)及[不可启动报告 #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，仍不能据此认定 FX3 已有可用的独立救援链。恢复能力与本轮编码参数结果分别成立，不能用离线组包通过替代掉电恢复验证。完整失效分级见[刷机失败与救援研究](<索尼 FX3 刷机失败与救援研究.md>)。

复核脚本、原始矩阵及限制见[工程说明](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/engineering-note.txt)。主代理额外执行仅用标准库的[收据核验器](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/verify_receipts.py)，来源哈希、内部清单、80例记录对照、原始 VPC8 位图和固定依赖 wheel 哈希均通过；此核验不重复 CPU 仿真。
