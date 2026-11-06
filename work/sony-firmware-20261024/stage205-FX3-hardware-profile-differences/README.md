# FX3恢复载荷的硬件配置对应与看护字段

2026-10-29。**本轮将A7 IV参考载荷与FX3公开资料对照到9项资源、4个USB时钟及看护字段：参考载荷的链接布局不依赖完整DDR训练；FX3 7.02 MCU原码使用同一看护计数表及三个重装值地址。** 这些新增证据缩小了适配范围，尚未形成可在FX3运行的载荷，也没有完成任何相机读写、恢复或首刷。

上一轮204实际取得AP启动原件并绑定更新启动路径，归类为progress。本轮核对了决定移植范围的资源和MCU字段，也归类为progress；不将状态文件新增或重复检索本身计作进展。持续目标、16项要求和全部授权不变。

## 可以缩小的前置工作

参考[链接脚本](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/payloads/fastboot/fastboot.ld)将代码、数据和栈放在 `[0xFE020000, 0xFE030000)`，USB DMA区放在 `[0xFE100000, 0xFE200000)`；分块传输缓冲为512 KiB加一个USB包的余量。因而**不必将“先恢复完整DDR初始化”作为这类最小恢复载荷的统一前提**。这是参考程序的布局事实，不是证明FX3当前硬件已经允许这些访问。

Sony的[FX3 Ver7.00 GPL参考](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)声明 `0xFE000000` 起的16 MiB eSRAM地址窗口，两段候选落在其中。窗口声明不等于全部物理容量可用，仍需确认保留区、总线/DMA访问、ROM版本及早期状态。当前7.02包内DTB还声明了8 GiB外部内存范围；它与参考源码的通用配置相符，不能当作用户机身实际RAM容量或运行后设备树的测量值。

## 哪些地址已有具体对应

| 资源 | 参考地址 | FX3证据层级 |
| --- | --- | --- |
| 系统控制器SCU | `0xF1388000` | 当前7.02包DTB对应 |
| USB PHY | `0xF1080000` | 当前7.02包DTB对应 |
| DWC3控制器 | `0xF10C0000` | 当前7.02包DTB对应 |
| SPI0 | `0xF1017000` | 当前7.02包DTB对应 |
| SPACC | `0xF7FC0000` | 当前7.02包DTB对应 |
| eMMC | `0xF10D6000` | Ver7.00 GPL平台定义对应；当前DTB的emmc0没有reg属性 |
| timer0 | `0xF1042000` | Ver7.00 GPL平台定义对应；4 MHz实际频率未确认 |
| SIO0 | `0xF1005000` | Ver7.00 GPL平台定义对应；板级用途未确认 |
| GPIO公式基址 | `0xF101D000` | Ver7.00 GPL定义对应；通道/引脚用途未确认 |

4个USB时钟经DTB phandle、clock ID及GPL门控表逐一绑定：ID16–19对应bank0 bit12–15。USB复位ID8–11及参考驱动的set/clear偏移也吻合。它们支持代码复用研究，不证明冷启动PLL、引脚或USB枚举已经通过。

完整对应、来源行号和28份行范围摘要见[硬件配置比较](hardware-profile-comparison.json)。当前包DTB为16875字节，完整解析68个节点，解析器检查了结构边界、属性长度及父总线的cell数。[原件来源](DTB-source-capture.json)、[解析结果](DTB-decoded.json)、[解析程序](inspect_DTB.py)。通用ranges译码没有代替驱动专用syscon/MFD解释；子节点的0或0x300不能直接当作最终MMIO物理地址。

## FX3当前MCU的看护字段已绑定

用此前已固定SHA的FX3 7.02 `darwin_core.bin`，按已验证的源布局基址0x4200重新检查：

- `0x65B4`常量池含 `0x200026FC`，4处实际LDR引用分别进入初始化、设置、禁用值和递减消费者。
- 初始化入口声明4字节；递减消费者跳过0xFF值，其余字节减1，归零返回1。该证明没有继续把返回值当作物理断电或复位完成。
- 三个明确调用点分别向设置函数传slot0/1/2，重装字节来源为 `0x2000003C/3D/3E`，与参考载荷头文件中的字段相符。只证明这3个调用点，不概括所有设置来源。

这比字符串命中更具体：10份原始代码/数据切片、PC相对LDR和Thumb BL位解码均绑定到当前FX3原件。[MCU字段证明](Darwin-WDT-source-proof.json)、[复核程序](prove_Darwin_WDT.py)。没有读取实际MCU RAM或任何当前计数值，未发送看护、停用或保活命令。

参考main只明确调用 `darwin_init()` 做链路引脚准备；普通运行路径未见显式看护计数保活。`darwin_write_block`在AP源中只有定义，OEM看护诊断读取字段。**因此不能预设参考Fastboot可在FX3持续运行到完成长时间备份或恢复。** 是否需要保活、何时超时，必须结合当前MCU协议和运行状态继续确认。

## 必须继续解决的差异

1. FX3当前AP/CP ROM身份和参考的ROM函数调用，尤其LED初始化固定地址；同SoC名称不够。
2. 独立BootROM入口、附件接口电气/时序与启动桥。用户目前没有RP2040；本轮没有提供纯USB替代入口。
3. Darwin的SIO通道、CS引脚、帧格式和读命令0x16兼容性；静态字段对应不能替代链路证明。
4. CP复位/启动模式及RAM监视器。参考main在USB之前就执行CP bring-up，不能把整条加载过程称为只读。
5. 当前机身boot0/p1身份、明文/密文分区映射、故障状态下逆写及冷启动验收。

下一项有明确用途的离线工作是核对FX3当前MCU的读命令分派及其与上述字段的关系，并追查SIO/CS配置来源。这能决定参考Darwin诊断代码是否可以适配；继续泛扫日志或重复生成检查回执不能替代它。没有将这些未验证地址写成供用户执行的参数。

## 来源与执行范围

A7 IV代码固定为 `e85e137fc3b88b7cb26e69faa9f1304184678ff7`：47份文件核对Git blob和SHA，其中44份与既存参考逐字节相同，3份新取自固定路径。[载荷源码来源](payload-source-capture.json)。GPL参考18份文件按归档逐字节固定：[平台与USB](vendor-source-capture.json)、[时钟与复位](clock-reset-source-capture.json)。Ver7.00源码没有被宣称为7.02精确构建。

本轮只有宿主机数据解析与静态反汇编，没有构建/上传/运行参考载荷，也未执行Sony代码或guest。工具0.4及195固定方案未变；root01仍未具体批准、未启动、未重问。相机、USB、root、管理员、Windows、UU、驱动和GUI操作为0；`goal_complete=false`、`persistent_write_release=false`。真实MAIN 1080p29.97 HEVC及长录、同机备份/恢复和独立救砖均未验收。
