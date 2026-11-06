# Sony 现代自定义修改的失败案例与恢复证据

核查基准：2026-10-25 UTC。只研究公开原始反馈、维护者记录与固定版本实现；没有执行安装器、连接相机、下载用户诊断包或向外发送消息。GitHub 原始列表、评论、版本及来源回执保存在 [cases 工作目录](../../work/sony-firmware-20261024/stage3-recovery/cases/)。

## 最新项目是否真的出现安装失败和无法启动？

### Takeaway

有。最新公开反馈不仅有安装、验证、恢复超时，还有一条修改后无法启动、读写灯循环且 USB 仅表现为 HID 的送修报告；目前未见其公开救回结果。它是实际不可启动报告，不能淡化成普通报错，也不能据现有材料认定永久硬件损坏。其他标题含“黑屏”的报告，有的是仍可操作、复位参数即恢复画面的渲染缺陷，必须分开。——[无法启动 #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)、[参数导致黑画面 #32](https://github.com/QAQLeonard/a7c2-fl23-research/issues/32)

### Cited Findings

| 记录与时间 UTC | 明确的机型、版本、动作 | 实际失败状态与是否已写入 | 公开恢复结果和证据等级 |
|---|---|---|---|
| [QAQLeonard #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)，2026-10-23 | A7C II 项目反馈；正文没有明确工具版本与机身固件号，不能替其补成 3.0.3／2.01。用户称按要求写入，第二次拔电池后发生 | 无法启动；读写灯 2-3-5 循环，USB 仍枚举 HID `054C:0D68`；按描述已到写入后冷启阶段，但没有独立分析私人原始日志 | 用户称送修。作者四条评论仅致谢、请求安装证据，用户上传附件；没有公开修复、返修诊断或成功恢复结论。属于第一手启动失败报告，不是已证实永久硬砖，也不是只需正常 restore 的可启动状态 |
| [QAQLeonard #28](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28)，2026-10-23 | ILCE-7CM2 2.01、Windows 工具 3.0.3，一键选择多项功能 | 竖屏准备已写入读回，后续 FL23 在 `appFw.so 0x3528804` 遇 patch conflict；整体 FAILED，但相机重启、拍照、回放和原有菜单正常 | 作者确认总体 FAILED 不表示早先操作已回滚；在看诊断前不能确认恢复按钮适合该状态。公开未提供完成恢复结果。是部分安装、功能未完成，不是启动砖 |
| [MDHan #14](https://github.com/MDHan/a7c2-fl23-macos/issues/14)，2026-10-24 | ILCE-7CM2 原版 2.01、MacBook Air、0.2.3；新版 `fl23 + mr_card_compat` 首装 | 已到 `writing_settings`，保持性检查发现额外字段变动后停止；冷启、拍照、回放正常，但无 FL2/FL3。旧专项 diagnose/finish 拒绝新版组合，install/verify/restore 又拒绝 needs_review | 核查时无评论、无已完成修复记录。不是砖，却是现有 Mac 工具真实存在的无受控续接路径中间态 |
| [MDHan #2](https://github.com/MDHan/a7c2-fl23-macos/issues/2)及 [#8](https://github.com/MDHan/a7c2-fl23-macos/issues/8)，2026-10-18 至21 | 旧 FL23、A7C II 2.01，Apple Silicon Mac；#8 给出原安装 `5babef4`、诊断/收尾 `dd69799` | 程序已完成完整读回，目标设置匹配，但 `0x02770015` 恰好 +60 触发保持性检查；磁盘是候选，部分运行内存仍原版；#8 首次退出普通 MSC 超时 | #2 用户最后报告重试后可用。#8 用户明确报告专项 WBI 收尾成功、冷启后 FL2/FL3 生效，verify 六区域内存与磁盘匹配。作者合并后增加来源绑定，明确原用户补丁单机成功与加固后版本离线验证分开。这是可进服务的专项收尾成功，不是恢复原厂或不可启动救砖 |
| [MDHan #7](https://github.com/MDHan/a7c2-fl23-macos/issues/7)，2026-10-18 至21 | A7C II 2.01、macOS arm64、0.2.2；已安装验证后尝试 restore | 等待服务 USB 产品 ID `054C:0336` 超时，尚未执行恢复 worker；机身仍运行 FL23。用户还曾手改 phase，后被拒绝 | 作者确认没有覆盖该情况的受控续接路径，完整通用 restore 未获实机验证；无恢复完成回报。`0336` 是 USB PID，不是错误码；失败前已发送模式切换/认证，不能说整个会话未发生设备操作 |
| [MDHan #4](https://github.com/MDHan/a7c2-fl23-macos/issues/4)，2026-10-18 | Mac 进入安装会话 | 等服务 USB `0336` 超时，停止在 prepared，尚未运行安装主体；普通 MSC 可见 | 作者明确不是 #2 的写入后中断，不能套 WBI 收尾；当时无受控续接，未声称已修好。是安装前连接故障，不是已写坏程序 |
| [MDHan #6](https://github.com/MDHan/a7c2-fl23-macos/issues/6)，2026-10-18 | A7C II 2.01、Apple Silicon、macOS 26.2、Python3.12.13、`b625c78` | 安装完成、可正常启动和选择 FL2/FL3，但冷启 verify 两处菜单运行内存仍原版，磁盘候选；进入 needs_review | 新增受控只读重验的离线验证，不能据此自动算此报告机身已完成修复；不是砖 |
| [QAQLeonard #32](https://github.com/QAQLeonard/a7c2-fl23-research/issues/32)，2026-10-23 | A7C II 自定义外观；确切工具版本未明 | 调创意外观参数（示例对比度0→+1）后预览接近全黑，参数复位就可正常拍摄；先前也发生导入重试 | 作者离线复现相关空曲线回退缺陷，但没有宣称原帖全部原因或真机已修复。不是无法开机，不应当作硬砖计数 |
| [QAQLeonard #34](https://github.com/QAQLeonard/a7c2-fl23-research/issues/34)，2026-10-24 至25 | 自述最新版本；未准确给构建号 | 快切外观后 EVF/屏幕假死，可慢切回原厂外观再返回；快门声和横线异常 | 作者承认快切假死尚可能无解决方案，横线修复中；用户对恢复后声音结果互相不同。是功能/稳定性退化，无已完成统一恢复结论 |
| [QAQLeonard #15](https://github.com/QAQLeonard/a7c2-fl23-research/issues/15)，2026-10-22 至23 | Windows11、3.0，MSC→服务身份连接失败 | USB 稳定性操作不能进入服务；未据此证明程序写入 | 原报告更新称给两种 USB 身份安装匹配驱动后解决；是主机驱动/连接修复，不是固件救砖。不能把换线、WinUSB/libusbK 一律视为通用办法 |
| [QAQLeonard #38](https://github.com/QAQLeonard/a7c2-fl23-research/issues/38)与 [#41](https://github.com/QAQLeonard/a7c2-fl23-research/issues/41)，2026-10-24 至25 | 修改后的 A7C II，版本未精确报告 | 换电池后启动数秒、部分外观连续AF时横线 | #38 作者解释冷启重载而关闭；#41 仍未回应。数秒后能启动不等于 bootloop，关闭 issue 也不等于独立测试已修复 |
| [YuuLuo #1](https://github.com/YuuLuo/a7c2-service-preload/issues/1)，2026-10-21 | FX30 6.00，尝试类似服务文件命令 | Jiritsu 文件命令缺失，相关 pFunc 返回128 | 没有报告刷坏或成功写入。这是跨机型入口不兼容线索，不能由 A7C II 服务成功推所有 FX 系列可用 |

- #31 的 USB 仍在，不表示普通 MSC 或 Senser 已可用。上游固定版本 changelog 也将 `054C:0D68` 保留为未识别身份，作者已测机身使用 `0E8A`／`0336`；没有把未知 PID 自动装驱动或当服务通道。——[固定版更新记录](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/en/changelog.md)

### Inferences

- 必须先按失败时“还能启动吗、USB是什么身份、服务能进吗、写入到哪一步”分级，再决定恢复路径；把所有现象统称砖会混淆已经有证据可处理的中间态和当前未知的不可启动状态。
- 能读回程序、还能拍照的失败，有机会利用证据和原始备份重规划；只有 HID 的启动失败不能直接套 MSC/Senser restore。公开帖子未提供结局时，不能用作者请求证据、关闭工单或工具有恢复按钮补成已救回。

### Gaps

- #31 没有公开确切版本、独立复现、最终原因和返修结局。本轮没有下载其可能含私人机身数据的附件，不能代替维修诊断认定物理损坏。
- 未找到可核验的 FX3 7.02 HEVC 自定义修改后无法启动并经本机环境救回的公开案例；当前也没有该新增模式的可运行成品，缺少 FX3 失败报告不是安全证据。

## 最新恢复方案究竟恢复什么 有没有真实成功？

### Takeaway

最新上游有维护者报告的一台机身项目范围恢复成功，也有用户记录的 Mac 专项安装收尾成功；不应沿用“所有恢复都未实测”的笼统说法。但“独立 Recovery”主要指不依赖旧工作目录／旧 LUT 任务，仍需可用的相机服务入口，不等于独立于正常系统的 bootloader 救砖。——[固定版更新记录](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/en/changelog.md)、[Mac 专项成功](https://github.com/MDHan/a7c2-fl23-macos/issues/8#issuecomment-6290096683)

### Cited Findings

- 最新 release 仍为 v3.0.3，2026-10-23 04:59:59 UTC，目标提交 `782785641ca9f8b984940c7274b48706219e0da4`；Windows x64 和 macOS arm64 包均在此时发布。核查 main 为 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`（2026-10-25 06:17:50 UTC）。正式 release 与更新后的 main 不是同一版本。——[v3.0.3](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)、[main 固定提交](https://github.com/QAQLeonard/a7c2-fl23-research/commit/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d)
- v3.0.2 说明修复 `/usr` 中旧任务名称备份占满空间，导致安装、竖屏和恢复 ENOSPC；同时重排 ST 设置以避免失败后留有指向新外观的配方，并明确修复未在所有受影响机身逐项复测。v3.0.3 增加程序写完后的设置续接、USB 收包修正及 Mac 声音保存崩溃修复。这些是具体可靠性改进，不能读成已覆盖掉电和所有启动失败。——[v3.0.2](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.2)、[v3.0.3](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)
- v3.0.3 tag 自身的 changelog 已记录 owner 确认 `cp-restore.2` 的恢复在 fresh-boot 检查后达到 LOADED；preview.5 明确写的是 owner 的 factory recovery，通过新启动、完整读回、loaded-state 和只读挂载验证，**不是 installation**。这是维护者的一台机身报告，没有公开对应原版／目标程序完整哈希和原始事务，因此不能独立核实为任意 factory 镜像或 #31 HID 送修案例救回。——[固定 tag 更新记录](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/en/changelog.md)
- Recovery 的代码范围包含 `appFw.so` 与 `cpapp-b.bin`、68个名称资源、外观绑定／色彩单元和六槽配方；不是只恢复 CP 参数，也不是整机文件系统和校准重置。恢复目标来自同机身可信 checkpoint 或原始 FL23 backup。——[checkpoint.py L15、L34–45](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py#L15)
- `checkpointjob.capture()` 不使用旧 `program_state()` 的 ORIGINAL/FINAL整文件哈希二选一：先读取当前两程序和身份，保存当前状态，再以 current→可信 target 建立新恢复事务；仍要求同机身、明确 2.01、能进入服务并完整读文件。`checkpointworker.differences()` 强制前后程序等长，按4096块找字节差异并按负载上限分批；原生预检查检查现场旧字节和文件大小。**它可以覆盖部分旧恢复会拒绝的等长混合／未知状态，但不是任意截断或文件系统损坏的修复器。**——[capture/run L87–91、L155–195](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L87)、[等长与差异规划](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py#L7)
- 恢复流程先写两程序、完整磁盘读回，恢复资源与设置，再按当前状态处理 WBI。verify 再核完整磁盘程序／资源／选定设置与 AP 选定内存区，记 LOADED 或带人工接受标记的 COMPLETE；源码特别限定 loaded-state 为 AP probe spans，CP RAM 与实际行为仍需用户检查。**LOADED 不等于整机全部运行内容都验证过。**——[checkpointjob.py L189–226](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L189)
- MDHan 的0.2.3仍明确真实通用 restore、断电/断线救援未验证；#8的用户专项成功与合并后的补强版离线验证区分记录。它和上游新的完整 checkpoint Recovery 是不同实现与版本，不能相互代替实测结论。——[MDHan 固定 VALIDATION](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md)、[#8 作者说明](https://github.com/MDHan/a7c2-fl23-macos/issues/8#issuecomment-6310001753)

### Inferences

- 对我们未来 FX3 专用研究，值得移植的是“保存可信安装前状态→读取当前状态→生成当前到目标的精确差异→机内预检查→完整读回→冷启验证”的恢复设计，而非把旧版 original/final gate 或 A7C II 的现成偏移当万能恢复。
- 对还能进入服务的等长文件错写，新的 checkpoint 设计比固定最终哈希的旧 restore 更有实际恢复价值；如果服务本身不能启动或 USB 只有未知 HID，它依赖的读取、身份绑定和 worker 执行前提尚不存在。

### Gaps

- 维护者恢复报告未给可独立核验的原始事务和原版／目标全哈希，不能据 LOADED 确认 CP RAM 或所有拍照录像行为。
- 没有公开证明这套 A7C II Recovery 已支持 FX3、当前 FX3 指纹、错误启动状态或 `0D68`。其功能增加不能直接升级为本机已具备 FX3 救砖能力。

## 本次证据覆盖和失败率能说明什么？

### Takeaway

本次覆盖五个主要仓库所有可见 open/closed issue 列表，共43条非PR issue，重点读取18条反馈正文，并保存其中15条有回复反馈的全部可见评论；此外核查了release和固定版本验证文档。它足以说明“有真实失败及不可启动报告”，不足以计算失败率、硬砖率或保证我们有恢复能力。——[原始查询与回执](../../work/sony-firmware-20261024/stage3-recovery/cases/)

### Cited Findings

- API列表分别有 QAQLeonard 31条非PR issue、MDHan8条、YuuLuo1条、leogenot0条、DavidBuchanan314 A7IV3条；每仓库全部结果均少于100且包含closed，没有把PR当失败案例。各仓库可见讨论均未启用。查询对象、时间、返回数据保留在对应 `--issues.json` 与 `--meta.json`。——[QAQLeonard issue 列表](https://github.com/QAQLeonard/a7c2-fl23-research/issues?q=is%3Aissue)、[MDHan issue 列表](https://github.com/MDHan/a7c2-fl23-macos/issues?q=is%3Aissue)、[本次回执目录](../../work/sony-firmware-20261024/stage3-recovery/cases/)
- 当前 leogenot 无issue、A7IV3条主要为型号/接线问题，没有可借用的不可启动后实际恢复闭环；YuuLuo唯一issue是FX30文件命令不适配。A7CR说明只表述有限机身测试和恢复不保证，本轮没有将泛化免责声明计作失败案例。——[A7IV issues](https://github.com/DavidBuchanan314/ILCE-7M4-RE/issues?q=is%3Aissue)、[YuuLuo #1](https://github.com/YuuLuo/a7c2-service-preload/issues/1)、[A7CR 原始说明](https://github.com/lzh2016zzz/a7cr-fl23-research)
- API随后出现共享IP速率限制；已获取的正文、评论、版本未丢失。补查恢复实现通过固定SHA raw原文完成，直接下载的参考代码在审计后移除，仅保留URL、内容哈希、行号和审计结论。没有运行代码或查看私人诊断附件。——[恢复源码回执](../../work/sony-firmware-20261024/stage3-recovery/cases/recovery-scope-source.json)、[release核查回执](../../work/sony-firmware-20261024/stage3-recovery/cases/release-v3.0.3-changelog-check.json)

### Inferences

- 下载次数、星标、可见issue数都不是完成安装的机身数；同一机身可能跨issue重复，私聊、删帖、未报告者不可见，不能把“43条issue里一条不开机”换算成失败概率。
- 安装失败、仍可拍摄、服务可用、HID启动失败和完全无USB至少是不同级别；FX3风险判断应对照拟修改文件与实际可进入的恢复通道，不依据“很多人刷成功”作保证。

### Gaps

- 本次不是所有Sony机型、中文社群和私人聊天的穷举。没有成功安装机身总数、独立复现失败数据或完整返修结果。
- 我们当前 Mac／USB／调试设备清单与 FX3 独立恢复通道由其他研究分支另行核对；不能仅从这些外机型案例得出本机必能或必不能救砖。
