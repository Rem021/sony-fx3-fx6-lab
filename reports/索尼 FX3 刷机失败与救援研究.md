# 核对 FX3 刷机失败与救援条件

核查日期：2026-10-24 至 25（America/Los_Angeles）。下表案例日期沿用 GitHub UTC；FX3 研究基线为官方 7.02，尚未读回用户机身身份与程序指纹。

2026-10-25 补充：用户确认另有 **Windows 11、Intel／AMD** 电脑。现有主机条件可按 Mac＋Windows x64 双机规划；Windows 的实际驱动绑定与相机连接尚未盘点，详见下文 Windows 路线。

同日双机实查更新：[UU 协作与回传盘点](<索尼 FX3 双机协作与HD HEVC仿真复核.md>)已核实 Windows 11 专业版26200、i7-14700KF及现有离线分析依赖。首轮缓存只有 Sony 手柄；用户接入相机后，09:54:17 UTC 的[新快照](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json)已确认 ILME-FX3、`054C:0DA1`、Microsoft `USBSTOR` 驱动绑定、状态OK／错误码0。仅验证普通 MSC 枚举与驱动元数据，尚无相机接口访问、服务认证或恢复成功证据。

本轮按用户要求优先完善[下方分阶段刷写与救援流程](#分阶段刷写与救援流程)，整机硬件模拟不作为刷机前提。已用[只读核验器](../work/sony-firmware-20261024/stage6-safety/audit_readiness.py)重算三份官方程序的完整哈希，3/3相符；[接线后就绪回执](../outputs/fx3-safety/readiness-20261025-msc.json)新增普通 MSC 绑定的快照证据，整体仍为 `OFFLINE_RESEARCH_ONLY`，没有放行持久写入。接线前[旧回执](../outputs/fx3-safety/readiness-20261025.json)保留，不能与新快照混同。

**有真实的安装失败、修改后无法启动并送修的报告，也有仍能进入服务时恢复成功的记录。当前这台 Mac 能做离线分析和恢复材料核验，但还不是经过 FX3 实机验证的救援平台。** 能否救回，取决于故障后仍可进入哪个通道、损坏范围，以及有没有同机身可信备份。最新上游 Recovery 已能处理一部分旧工具拒绝的等长未知或混合程序状态；它仍依赖相机服务，不能代替 BootROM 救援，也未形成 FX3 成品。现存官方固件不能替代这台机身的检查点、校准或完整存储备份。因此，现阶段不能以“刷坏后保证能救回”为前提写入主力 FX3。([不可启动报告](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)、[最新恢复源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py)、[本机材料回执](../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json))

## 公开反馈中已有无法启动与恢复受阻的真实案例

“安装失败”“黑画面”和“无法启动”不是同一种故障。以下保留原报告的机型和版本范围；用户报告能证明故障被报告过，不等同维护者已复现根因。

| 原始记录与日期 UTC | 机型与版本 | 故障及公开结果 | 能说明什么 |
|---|---|---|---|
| [上游 #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，10月23日 | A7C II 项目反馈；准确固件、工具版本未给出 | 用户称写入后第二次拔电池无法启动，灯2-3-5循环，仍有 HID `054C:0D68`；已送修，无公开救回结局 | 是真实不可启动报告；尚不能认定永久硬砖，也不能认作普通服务可恢复 |
| [上游 #28](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28)，10月23日 | A7C II 2.01、Windows 3.0.3 | 前一功能已写入，后一功能遇 patch conflict；总体 FAILED，但仍能拍摄、回放 | 失败标志不表示早先改动全部回滚，亦不表示机身变砖 |
| [Mac #14](https://github.com/MDHan/a7c2-fl23-macos/issues/14)，10月24日 | A7C II 2.01、0.2.3，新版组合首装 | 停在 `writing_settings`；冷启后仍可拍摄，但无 FL2/FL3，旧收尾命令不支持，验证与恢复被 `needs_review` 阻止；无解决回复 | 有真实的工具中间态，不能直接套旧专项收尾 |
| [Mac #2](https://github.com/MDHan/a7c2-fl23-macos/issues/2)／[#8](https://github.com/MDHan/a7c2-fl23-macos/issues/8)，10月18至21日 | A7C II 2.01、Apple Silicon，旧 FL23 流程 | 程序已写入，设置检查／WBI 收尾中断；#2称重试可用，#8明确专项收尾、冷启后生效并验证内存与磁盘匹配 | 有可进服务的专项安装收尾成功，不是 #31 的不可启动救回 |
| [Mac #7](https://github.com/MDHan/a7c2-fl23-macos/issues/7)，10月18至21日 | A7C II 2.01、0.2.2 | 有原版备份，restore 等待服务 USB `054C:0336` 超时；未执行恢复 worker，机身仍运行 FL23；无恢复完成报告 | 有备份仍可能到不了恢复入口；0336是产品ID，不是错误码 |
| [上游 #32](https://github.com/QAQLeonard/a7c2-fl23-research/issues/32)，10月23日 | A7C II 外观修改，准确工具版本未明 | 调外观参数后画面近黑，复位参数可正常拍摄；作者离线复现相关缺陷 | 属渲染／参数问题，不能计为无法开机的砖 |
| [上游 #15](https://github.com/QAQLeonard/a7c2-fl23-research/issues/15)，10月22至23日 | Windows11、3.0 | 进入服务失败；原报告后来称两种USB身份匹配驱动后解决 | 是主机连接问题修复，不能作为固件救砖成功 |

故障 #31 的 `0D68` 在维护者记录中仍是未识别身份，不能因为 USB 可见就当作 `0336` 服务、普通更新器或 fastboot。报告未公开确切版本及返修结论，本轮也未下载可能包含私人机身信息的附件。([固定版更新记录](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/en/changelog.md))

本次查看五仓库全部可见 open/closed issue 列表，共43条非PR问题，重点读18条正文和15个线程全部可见评论。它足以确认存在失败与不可启动报告；没有安装总人数、独立机身数和完整返修结果，**不能据此计算失败率或“变砖率”**。完整12组分级记录见[案例笔记](<../research_notes/索尼 FX3 刷机失败与救援研究/cases.md>)与[查询回执](../work/sony-firmware-20261024/stage3-recovery/cases/)。

## 最新 Recovery 更灵活 但仍依赖服务和可信检查点

正式发布包与最新源码必须分开。核查到的最新 release 为 **v3.0.3，2026-10-23 UTC发布，提交78278564…**；所审 main 为 **b311407a…，2026-10-25 UTC提交**。正式包已有设置步骤续接等可靠性改进，其 changelog 也记录维护者单机的项目范围 factory recovery 成功；这不是 #31 故障的救回记录，亦没有公开对应输入、目标完整哈希供独立复核。Mac适配项目的0.2.3又是另一版本，不能共用实测结论。([正式v3.0.3](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)、[tag内恢复记录](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/en/changelog.md)、[所审main](https://github.com/QAQLeonard/a7c2-fl23-research/commit/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d))

**所审 main 的 checkpoint Recovery 不再只接受“原版／安装完成版”两个固定哈希。** 它读取当前程序，以同机身可信检查点为目标，重新规划 current→target 差异。范围包含 `appFw.so`、`cpapp-b.bin`、68个名称资源和选定外观设置，不是仅恢复参数，也不是完整相机文件系统或校准重置。机身绑定和明确的 A7C II 2.01 条件仍在，不能将它原样用于 FX3。([恢复范围与机身绑定](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py)、[当前状态读取与恢复规划](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L87))

恢复仍要求两程序可完整读取、当前与目标**长度相同**。实现按4096字节块定位差异，再形成受负载限制的旧／新字节窗口，机内检查现场内容和大小，写后完整读回并处理WBI。因此，它能覆盖部分等长未知或AP/CP混合状态，不能在原位置修复截断、异长文件或不可读文件系统。`LOADED` 核对完整磁盘内容及选定AP运行区；CP RAM与实际拍摄行为仍需检查，不是整机验收。([差异与等长限制](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py#L7)、[写入和重载验证](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L189))

可借鉴的设计已经清楚：安装前保存可信健康状态，故障后读当前状态，按精确差异恢复，并验证磁盘、冷启动和行为。这比跳过旧哈希门禁更有价值；但若服务入口本身不工作，读取、身份绑定和worker执行都无从进行。

## 已确认 Mac 与 Windows 主机条件 尚未打通 FX3 实机恢复

本机只读盘点为 **macOS27.2、arm64、Python3.14.6**。PyUSB1.3.1已装，但默认libusb查找为空；PATH与常见路径未找到现成PMCA、相关工具或Windows VM应用。缓存IORegistry当前没有Sony设备。这些查询只覆盖已记录位置，不等于用户没有其他未连接设备；也没有打开USB接口、认证或发送相机命令。([环境回执](../work/sony-firmware-20261024/stage3-recovery/environment/environment-inventory.json)、[查询覆盖](../work/sony-firmware-20261024/stage3-recovery/environment/known-path-probe.json))

| 当前已确认具备 | 仍缺的关键条件 |
|---|---|
| 官方7.02完整DAT、解密数据、校验过的分区与AP/CP原字节 | 此机正常状态的可信checkpoint、实际程序指纹与必要设置读回 |
| 离线解析、差异和哈希检查、日志分析 | FX3服务入口、认证、执行权限和恢复读写的实机验证 |
| Mac/Python与一般编译工具 | 已验证的FX3低层载荷、触发接口、电气条件和故障状态恢复证据 |
| Windows 11专业版26200、i7-14700KF；FX3普通MSC身份及驱动绑定（双机实查） | FX3诊断／服务身份、实际接口访问、固件指纹与恢复能力 |

官方通用包不是此机的全存储、boot0、NVRAM或校准备份，包内默认／地区数据不能代替独有机身数据。本任务尚未制作这类实机材料。([恢复材料清单及缺项](../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json))

对于服务仍可达、仅需修复已知程序的等长改动，匹配的可信原程序与相关设置检查点可以是相应恢复材料；全存储、boot区与校准缺项对应更低层故障，不能把全盘镜像说成每次AP/CP局部修复的统一前提。

Sony当前Camera Driver声明支持macOS11至26的所列版本，**不含本机27.2**；旧FX3 USB桥接更新器自己的页面只列11至13，两种范围不可混同。FX3官方7.02正常更新走存储卡，不依赖该旧USB驱动；这些兼容性限制也不能概括为所有第三方USB方法都不能运行。已确认的Windows主机增加了主机侧选择，但不能补出相机已失去的恢复入口。([当前驱动范围](https://www.sony.com.sg/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00268924)、[旧桥接更新器](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280268)、[7.02卡更新](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561))

## Windows 11 x64 可用于下一阶段主机验证

用户确认的 Windows 11、Intel／AMD 符合 A7C2Tools v3.0.3 发布包的 Windows 10／11 x64 要求；该项目仍仅支持 ILCE-7CM2 2.01，不能把 EXE 直接用于 FX3。可借鉴其普通连接与服务连接分别绑定驱动、先做只读稳定性检查的流程；`0E8A` 是该 A7C II 的普通连接示例，不应预设 FX3 也使用这个 PID。([发布包](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)、[固定版机型与驱动说明](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/README.zh-CN.md#第-1-步安装驱动windows))

还需区分两条恢复路线：同机 checkpoint 回滚依赖可信旧状态；项目另有使用内建原厂区域数据的恢复功能，文档称无需旧备份。后者的数据清单明确限定 A7C II 2.01 的项目程序区域及 FL23 色彩子区，不是全固件、校准或任意启动损坏的恢复。两者均没有因此获得 FX3 支持。([内建恢复范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/assets/factory-regions-2.01.json)、[同机检查点选择](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/desktopapp/recovery.py))

双机分工可以确定为：Mac 保留离线分析与基准核验；Windows 先观察真实 USB 身份和现有驱动状态，再决定 FX3 专用通信适配。Windows 的旧官方 FX3 USB 更新器虽然支持该主机架构，但只用于指定旧版本的过渡；官方明确已到 2.04 及以上应转最新卡更新流程，不能把旧 EXE 当成 7.02 通用救砖器。([Sony Windows 适用条件](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280265))

第一步可在 Windows 自带 PowerShell 中只读查看已连接 Sony 设备的 PnP 信息，不启动服务或更新器，也不显示完整设备实例路径／序列号：

```powershell
Get-PnpDevice -PresentOnly |
  Where-Object { $_.InstanceId -match '(?i)VID_054C&PID_[0-9A-F]{4}' } |
  ForEach-Object {
    [pscustomobject]@{
      Name = $_.FriendlyName
      Class = $_.Class
      Status = $_.Status
      UsbId = [regex]::Match($_.InstanceId, '(?i)VID_054C&PID_[0-9A-F]{4}').Value
    }
  } | Format-Table -AutoSize
```

此查询只返回 Windows 的 PnP 设备信息，看到 Sony 也不代表服务认证成功。上述是可复用示例；Windows Codex 先取得仅含手柄的旧快照，随后另存接线后新快照。新盘点通过 CIM、已安装驱动元数据及缓存的 `DEVPKEY_Device_BusReportedDeviceDesc` 核对 FX3，未打开相机接口、更换驱动、进入服务模式或写入机身。已取回并审阅[实际脚本](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/inventory_cached_sony_pnp.ps1)；旧快照的 SHA 在两端均仍为 `fb0b5739…`，见[传输与保留核验](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/transfer-review.json)。方法依据 [Microsoft Get-PnpDevice](https://learn.microsoft.com/en-us/powershell/module/pnpdevice/get-pnpdevice)，补充核查与源码指纹见 [Windows 路线记录](<../research_notes/索尼 FX3 刷机失败与救援研究/windows.md>)。

## 能否救回取决于故障后仍可进入的通道

| 故障表现 | 已有恢复依据 | 对当前环境的判断 |
|---|---|---|
| 主机工具失败，机身正常，尚未写入 | 核对日志、工具版本、USB身份和阶段 | 可以诊断；不应直接套写入后的收尾命令 |
| 程序已改，但机身与服务正常 | 同机可信checkpoint下的等长差异恢复 | 有可移植设计；尚无验证过的FX3恢复成品 |
| 主应用不启动，rootfs和/usr仍完好 | 主启动前Senser服务候选 | 可继续研究，故障时触发与权限未证实 |
| 只剩未知HID `0D68`，普通服务不通 | 尚需识别协议和启动阶段 | 当前没有对应已验证FX3救援链，不能当0336处理 |
| /usr、rootfs、内核、WBI或启动区损坏 | 独立早期入口、型号专用低层恢复或售后 | 现有文件级服务可能自身无法加载，当前不能承诺救回 |
| 无上电或供电、存储芯片、主板物理故障 | 硬件检测、维修或换板 | 官方DAT与Mac软件不能替代硬件维修及校准 |

FX3服务独立性有进一步证据：本轮追踪Senser相关四个入口的静态依赖闭包，21个ELF节点没有`appFw.so`。但动态插件、IPC、WBI启动路径和故障后外部触发仍未验证；多数服务文件也在`/usr`，整个分区损坏时不能指望它们自救。表中的软件恢复判断是按这些入口与材料作出的工程评估，不是实际故障注入结果。([依赖闭包和哈希](../work/sony-firmware-20261024/stage3-recovery/technical/dependency-closure.json)、[只读复核器](../work/sony-firmware-20261024/stage3-recovery/technical/trace_dependencies.py))

Sony7.02正常更新中，黑屏及1、3、5次闪灯可以是进度；5长6短、7长7短等特定错误才对应官方重备文件／卡及核对升级顺序的处理，不能把正常更新中的黑屏当砖并任意断电。另有经销商公开展示的Sony **22PV028 Rev0，2022-11-18** 维修公告，针对旧FX3 2.01／FX30 1.01升级后循环重启规定更换SY板。这不能外推到7.02或所有自定义损坏，但说明电脑重刷不是所有故障的既定解法；本轮仅读取公开预览，未提交完整PDF索取表单或获取未公开流程。([Sony当前错误处理](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)、[公告公开预览](https://store.professionalshow.com/ImagesNoZoom/TECHDRAW/BA026/BA026118.jpg)、[预览来源回执](../work/sony-firmware-20261024/stage3-recovery/technical/official-source-receipt.json))

A7IV原作者确已公开串行BootROM入口、自制fastboot及eMMC备份／恢复研究，boot0处理尚未实现。它证明低层救援并非空想，但对象是ILCE-7M4，不是已经适配的FX3；还需要型号载荷、可达接口、正确电气条件和原始材料，不能由同为BIONZ XR推定通用。([A7IV原始研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE))

## 下一步应先建立 FX3 的恢复证据

对1080p30 HEVC研究，当前更有价值的推进是保留离线参数与路由分析，同时先核准真实机身身份、诊断入口及正常状态材料，再证明拟修改范围发生失败时仍能读回和恢复。健康检查点必须在修改前取得；故障后创建的存档不会自动变成可信原版。进入实机阶段前，不需要先购置通用编程器、创建虚拟机或改变本机安全策略，只有确认FX3实际入口才能知道这些措施是否有用。

本轮救援研究没有安装相机驱动、创建VM、改变相机启动或安全策略、发送相机服务命令或做故障注入。独立的 Mac UU 输入监控权限已按用户确认开启，见[双机记录](<索尼 FX3 双机协作与HD HEVC仿真复核.md>)。详细依据分别保存在[案例笔记](<../research_notes/索尼 FX3 刷机失败与救援研究/cases.md>)、[恢复技术笔记](<../research_notes/索尼 FX3 刷机失败与救援研究/recovery.md>)和[环境评估](<../research_notes/索尼 FX3 刷机失败与救援研究/environment.md>)。当前交付的是诊断材料和恢复适配依据，尚未验证的FX3低层救援不能作为试刷的兜底。

## 分阶段刷写与救援流程

此流程的目标是把可避免的损坏挡在写入前，并明确每一种恢复承诺依赖什么。它是执行规范与证据清单，目前不是可操作 FX3 的安装器。2026-10-25 再核上游 main 仍为 `b311407a…`，没有新的 FX3 独立救援证明，见[来源回执](../work/sony-firmware-20261024/stage6-safety/source-review.json)。

### 先区分恢复覆盖范围

| 要防的失败 | 对应材料和通道 | 何时才可称这一级可恢复 |
|---|---|---|
| 设置异常或已知程序的等长局部改动，服务仍可达 | 对应程序原字节、设置检查点、同机身身份、可用的文件级恢复通道 | 在 FX3 上真实恢复后完整读回相符，冷启动与基础拍摄正常 |
| 主应用损坏或不启动 | 不依赖拟修改主应用的恢复入口；该入口所需 rootfs、库及存储仍完好 | 在对应主应用失效条件下，入口确实可达并完成恢复；正常开机能进服务不够 |
| 文件被截断、文件系统／内核／WBI／启动区受损 | 覆盖该损坏范围的更低层入口与备份、型号适配载荷 | 对应低层链路已验证；普通等长文件补丁恢复不覆盖这一层 |
| 无可用软件入口、存储或主板硬件故障 | 合格硬件检测、必要的板级修复与校准 | 取决于硬件状态及维修条件；当前双机软件环境不能保证自行救回 |

局部程序恢复需要与拟修改范围匹配的原件，并非每次都必须先做全盘镜像；反过来，完整存储镜像也不能替代电气接口、可达入口或硬件维修。官方 DAT 只能作版本原件参考，不能替代机身独有的设置、校准和 NVRAM。

### 持久写入前的顺序和停止条件

| 阶段 | 实际动作与必须留下的证据 | 本轮状态／停止条件 |
|---|---|---|
| A 普通连接 | 相机选“图像传输（MSC）”；仅查询 Windows 缓存设备名称、VID/PID、驱动提供者／版本／服务／错误状态；结果另存 | 已完成：ILME-FX3、054C:0DA1、Microsoft 10.0.26100.9444、已签名USBSTOR、OK／0；未读卡内素材、认证或切服务 |
| B 精确基线 | 核对 ILME-FX3、实际固件版本及程序指纹；区分官方包版本与实机版本 | 机身“最新”是用户报告，尚未读回；不允许借用 A7C II 或 ZV-E1 的型号、偏移和补丁 |
| C 健康状态检查点 | 在任何修改前取得拟修改文件原件及相关设置；记录同机身绑定、长度、完整 SHA256、工具版本和采集方式；在第二端验证清单 | 任务内尚无实机检查点；故障后新建的存档不能标为健康原件，设置导出不等于程序备份 |
| D FX3 恢复入口 | 先验证 FX3 专用诊断通道的能力、清理和正常退出；再验证其不依赖拟修改主应用 | 静态依赖闭包只是候选证据；只有普通服务可用，仍不能宣称主应用失效后可救 |
| E 恢复实际闭环 | 完成与目标损坏范围相符的恢复；完整读回原件哈希、核对磁盘／运行内容、受控冷启动、菜单与短片验收 | dry-run、原样不变的 no-op restore、CPU 仿真都不能替代这一步；不在主力机上人为制造砖来取证 |
| F 写入方案审计 | 固定型号／版本／整文件哈希／旧字节／范围／预期最终哈希；拒绝重叠、越界、长度变化及未知现场；只修改功能所需最小范围 | 当前没有经过实测的 FX3 写入器；正常检测或未知状态不能自动放行 |
| G 写后验收 | 完整读回；确认 WBI／冷启动后实际运行内容；验证新模式码流、音频、时戳、分段、长录与温度；再验证恢复原版闭环 | 现有函数仿真未覆盖这些实机结果；保留每次失败与恢复记录 |

Sony 官方列出的 MSC 是普通图像传输模式；选择它只是建立正常 USB 身份，不代表进入维护或救援环境。([Sony USB 模式说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000843988.html))

未来的写入器还需要明确处理断电风险。逐窗口 `pwrite`、`fsync`、读回和反向回写能降低部分错误，但不构成多文件原子提交：恢复 worker 消失或电源丢失时，仍可能留下混合状态。完整回滚能力必须与实际入口一起验证，不能由“有备份”和“程序里写了 rollback”推导出来。首次功能适配不应顺便修改启动分区、分区表、OTP／熔丝或校准区；如某项功能确实需要更深范围，应重新评估对应恢复覆盖。

### 中断发生后如何处理

| 现场情况 | 下一动作 | 本流程禁止据此作出的推定 |
|---|---|---|
| UU 远程断开，Windows 与相机仍供电 | 重新连回同一 Windows，先看本地任务和日志；确认 worker 是否仍运行，再读当前状态 | UU 是控制界面，不是相机的 USB 传输链；远程断开不等于刷写已停止或已回滚 |
| USB 超时或主机程序退出 | 把结果记为 UNKNOWN；保持已知供电状态，保存日志，不启动第二个并行写入／恢复任务；先确定当前文件状态 | FAILED 不代表“没有改动”；不能直接重放首次安装计划 |
| 服务可重新进入、程序可完整读出且等长 | 以同机可信原件为目标，按 current→target 重新规划；检查身份和现场字节，再由已验证 FX3 恢复器处理 | A7C II 最新 Recovery 能规划部分混合状态，不表示现成工具支持 FX3 |
| 只枚举出未知 USB/HID 身份、服务不可用 | 保存 VID/PID、设备类、驱动状态、灯序及发生阶段；按型号确认协议和启动层次 | USB 可见不等于可恢复；`054C:0D68` 不等于 `0336` 服务或 fastboot |
| 无入口、文件系统不可读或出现供电／硬件异常 | 转向覆盖该层故障的已验证低层方案或维修；保留原机身材料 | 换 Mac／Windows 或下载官方 DAT 不能自行补出机身失去的入口 |

官方卡更新故障按对应版本的 Sony 指示处理，不与第三方局部写入中断混用。黑屏及部分闪灯可能是正常更新阶段；普通 7.02 卡更新也没有在本研究中证明能从任意不可启动状态触发。旧 USB 过渡更新器不能当成最新机身的强制刷机／降级工具。([Sony 7.02 适用顺序及错误处理](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561))

### 当前已经落实和仍待完成的工作

已重算三份官方程序完整哈希、保存 Windows 首轮脱敏盘点、复核上游恢复版本，并把以上顺序、范围和中断规则写入执行规范。[只读核验器](../work/sony-firmware-20261024/stage6-safety/audit_readiness.py)只检查明确列出的本地研究材料并新建 JSON 回执；它不打开相机接口、不联网、不覆盖固件或备份，也不是救援认证或刷机授权。

当前 A 阶段已完成，原始 JSON、脚本和文字回执均通过 UU 取回。其后 B 至 E 仍需 FX3 自身的实机证据；普通 MSC 正常不证明服务访问、备份可读或故障后可恢复。单纯增加流程文档、模拟器或第二台电脑，不能将它们标成已通过。研究中的“备份”“入口”“恢复成功”“冷启动与拍摄验收”必须各自有回执，才能进一步缩小持久写入风险。
