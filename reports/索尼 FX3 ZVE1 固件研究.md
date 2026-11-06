# 研究索尼 FX3 与 ZV E1 的固件扩展

研究日期：2026-10-24（America/Los_Angeles）。你确认使用 REA，FX3 固件为“最新”；本报告按当日 Sony 公开最新版 **7.02** 研究，尚未读取你的机身版本。

**可以继续做不写入相机的离线研究，而且本次已经实际解密 FX3 7.02 官方固件的 FDAT 容器，校验通过并列出内部 155 项内容。** 你要的 1080p H.265 也已有官方入口：FX3 的 **XAVC HS HD 代理录制**支持 1920×1080、4:2:0 10bit、9/16Mbps，但必须与主片同时录制；29.97p 主片对应的代理实际帧率还需样片确认。若目标是独立的 1080p30 H.265 主录，目前没有找到可复核的 FX3 补丁与恢复记录。ZV-E1 刷完整 FX3 系统也没有找到稳定录像与恢复均可复现的实现，现阶段不能将其称为安全方案。REA 能辅助分析，不能把“解包成功”自动变成“功能实现并安全刷入”。([Sony 代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)、[本次离线解包清单](../work/sony-firmware-20261024/fx3-7.02-offline-manifest.json))

## FX3 已能编码 1080p HEVC，先验证官方代理是否满足用途

Sony 原版 FX3 的旧版及 Ver.2+ 帮助指南都列出 XAVC HS HD 代理，因此这不是 FX3A 专属功能，也不是必须刷第三方固件才能取得的能力。当前主录格式有 XAVC HS 4K、XAVC S/S-I 4K 与 HD 等，**没有独立的 XAVC HS HD 主录选项**。另一个容易误配的细节是，FX3 的 XAVC HS 4K 主录表没有 29.97p/25p，不能建议“选 4K H.265 30p 再生成代理”。([原 FX3 旧指南](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000282137.html)、[主录格式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)、[录制设置完整表](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html))

| 方式 | 官方已确认的规格 | 对本次目标的意义 |
|---|---|---|
| XAVC S HD 主录 | AVC/H.264；含 29.97p、50Mbps、4:2:2 10bit | 可作为正常主片和代理录制的试验搭配 |
| XAVC HS HD 代理 | HEVC/H.265；1920×1080；4:2:0 10bit；9/16Mbps；最高 59.94p/50p | 已有 HD HEVC 编码管线；具体 29.97p 输出待样片核验 |
| 独立 HD HEVC 主录 | 官方菜单未提供 | 本次未找到可复现的第三方解锁实现 |

表中编码与采样规格来自 Sony 帮助指南和原 FX3 规格页；代理音频为 **AAC-LC 128kbps 双声道**，不能等同保留主片的 PCM 或多声道能力。([Sony 代理说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)、[原 FX3 官方规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html))

最小验证方案是先记录当前设置，在普通视频模式选择 **XAVC S HD、29.97p、50M 4:2:2 10bit**，再进入 `MENU → Shooting → Image Quality/Rec → Proxy Settings`，将 `Proxy Recording` 设为 `On`、`Proxy File Format` 设为 `XAVC HS HD`、`Proxy Rec. Settings` 设为 `16M 4:2:0 10bit`，录制约 10–20 秒，内容包含运动物体与一次清楚的拍手。29.97p 属于 NTSC 模式；“30p”通常是其菜单简称，不能等同精确 30.000fps。若当前处于 PAL，先核对现有拍摄工作流再考虑制式设置。代理没有独立帧率菜单，随主片输出 29.97p 是待验证的工程预期；官方页面只给最高帧率，本次没有把这个预期当成实测。([主录设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)、[代理菜单](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html))

将素材完整复制到电脑后，在副本中找代理：SD 卡目录为 `PRIVATE/M4ROOT/SUB`，CFexpress Type A 为 `M4ROOT/SUB`；主片在对应 `CLIP` 目录。若电脑已有 `ffprobe`，可对复制出的代理执行以下只读检查，期望视频流为 `hevc`、1920×1080、10bit 4:2:0，若要确认常用 30p，帧率应为 `30000/1001`。还需完整播放检查画面、声音与同步；元数据正确不能代替播放验收。([Sony 导入电脑说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868300.html))

```sh
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,bit_rate,sample_rate,channels -of json '/实际路径/代理副本.MP4'
```

代理的实用限制需要与用途一起判断：它必须伴随主片录制，相机内不能回放代理；普通 119.88p/100p 及部分 S&Q 条件不可用。16Mbps 视频约 7.2GB/小时，9Mbps 约 4.05GB/小时，均为未计音频和封装的计算值；若搭配 50Mbps 主片，当次视频总量约 29.7GB/小时，**开代理会增加拍摄时的总写卡数据**。因此，它适合验证“小型 HEVC 文件是否可直接交付”，不能默认解决“只写一份文件、减少机内负担或获得主片级码率”的需求。画质、Log/LUT、色彩与元数据还需真实场景检查，先保留原片。精确 30.000fps 或自定码率可在后期制作中控制，但需明确如何处理 29.97→30 的帧与时长。([Sony 代理限制](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html))

## 本次已解开 FX3 官方包的容器层，尚未定位编码模式表

公开进展比旧教程更深入：`ma1co/fwtool.py` 的 PR #52 于 **2026-09-10** 提出 CXD90057 支持，作者测试列表明确包含 FX3。PR 当前仍为 Open，旧主分支的兼容表不能代表该研究分支。本次核对的源码固定在 `3955d7890fc38daf942bb52827599bfe35de4a14`；该版支持相应 AES-CBC 解密，但其 `encrypt()` 明确抛出 `Encryption not supported`，不能将解包工具当成已具备刷回能力的工具。([维护者原始 PR](https://github.com/ma1co/fwtool.py/pull/52)、[固定版 FDAT 源码](https://github.com/DavidBuchanan314/fwtool.py/blob/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/fdat.py))

本次从 [Sony 日本 FX3 7.02 官方页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)取得[公开下载地址](https://support.d-imaging.sony.co.jp/download/NEX/ey8d8a84ee/BODYDATA.DAT?fm=jp)，完整下载 **811,876,768 字节**。使用依据已审阅公共格式编写的只读脚本，完成外层 UFU CRC、全部 **792,848 个加密块**的校验及末块标记检查，再列出内部 tar。没有启动更新器、执行包内程序、连接或写入相机，也没有运行一次 REA 会话；这里的实际成果是专用格式的离线解密与检查。([下载回执](../work/sony-firmware-20261024/fx3-7.02-download-receipt.json)、[自写解密脚本](../work/sony-firmware-20261024/decrypt_fx3_offline.py))

| 检查层级 | FX3 7.02 本次结果 | ZV-E1 2.02 本次结果 |
|---|---|---|
| 官方来源与长度 | 整包已下载，长度匹配 | 仅取得前 65,536 字节及尾部 284 字节 |
| UFU / FDAT 头 | 识别、头校验通过 | 识别、头及首块校验通过 |
| 整个 FDAT | 解密并校验通过，808,704,512 字节 | 未做整包解密或整包 CRC |
| 内部固件 tar | 807,450,624 字节，155 项目录 | 未做 |
| 嵌套文件系统、主应用、模式表 | 尚未展开和定位 | 未做 |
| 重打包、刷入、启动、录像、恢复 | 均未验证 | 均未验证 |

FX3 内部目录及少量配置已显示 `ALCIN`、`/usr`、`/system`、WBI2、rootfs、CP 与 `cxd90057.dtb` 等内容。它们为后续定位主程序提供入口，但目前未判断全部嵌套映像格式，不能统称“仍然加密”，也不能宣传为完整恢复了全部系统文件。两包匹配同一公开 CXD90057 k8 解密路径，型号标识分别为 `0x91030080` 与 `0x20030000`；这证明封装代际相近且目标型号不同，不证明主板相同、签名相同或允许跨刷。([完整解包清单](../work/sony-firmware-20261024/fx3-7.02-offline-manifest.json)、[限量配置探测](../work/sony-firmware-20261024/fx3-7.02-bounded-probes.json)、[双包头分析](../work/sony-firmware-20261024/ufu-header-analysis.json)、[ZV-E1 官方页](https://support.d-imaging.sony.co.jp/www/cscs/firm/?area=jp&lang=jp&mdl=ZV-E1))

复核锚点保存在回执中：官方 FX3 包 SHA-256 为 `f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854`，解密 FDAT 为 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`。CRC 与分块校验确认本次获取、解析和解密的一致性，**没有替代 Sony 签名认证或设备运行验证**。包内名称含 `backup` 的默认文件也不等于你的机身独有校准数据与完整可恢复备份。([本次清单与范围声明](../work/sony-firmware-20261024/fx3-7.02-offline-manifest.json))

## A7C II 的局部移植是真进展，REA 与成果仍须分开看

REA 是连接智能体与 Hopper/Ghidra/IDA 等分析器的工具。核查版本固定为 `fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4`；其固件流程使用 Binwalk、Unblob 和提取后的 ELF 分析，第一阶段验证平台为 Linux x64。文档明确区分分析覆盖率意义的“complete”与完整固件重建，并保留未知或失败区域。REA 适合辅助检索模式门控、编码参数与调用关系；Sony 专有容器仍需相应解析知识，生成的分析也要与原始字节核对。该平台边界不能解释为 Mac 绝对不可用，但不能承诺本机固件模块已获验证。([REA 固定版本](https://github.com/morluto/rea/tree/fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4)、[固件分析说明](https://github.com/morluto/rea/blob/fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4/docs/firmware-analysis.md))

现代 A7C II 确有实质补丁。`QAQLeonard/a7c2-fl23-research` 的研究快照 `9f69e9dc59ef2cfbc3334bee977b7529aaee04b8` 只支持 **ILCE-7CM2 固件 2.01**，包括 FL2/FL3 与自定义外观等。源码检查机型、原版哈希和固定窗口，安装器修改 `/usr/lib/appFw.so` 与 `/cp/cpapp-b.bin` 的局部内容并落盘；这是本机程序的持久修改，并非通用签名存储卡升级包。作者验证表覆盖一台 Windows 环境机身的部分功能，快门声长期验证、竖屏等项目仍有边界，README 直言读回一致不证明启动安全、恢复不保证救砖。([固定 README](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/README.zh-CN.md)、[安装源码](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c))

其服务入口也有明确范围：YuuLuo 在 A7C II 2.01 观察到服务认证、Jiritsu 与 preload 路径下的临时 root 子进程执行；作者明确这不永久禁用签名。MDHan 的 Mac 适配 0.2.3 有有限机身反馈，同时保留首次安装中断、实际恢复未测等记录。因此“有源码”“工具报告验证通过”“能启动拍摄”“失效后能恢复”需要分别判断。([YuuLuo 固定版说明](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/README.md)、[Mac 适配固定版验证](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md))

本次检查上述项目及 leogenot 项目的固定版 README，没有发现它们将成果归因于 REA；这仅说明公开说明未如此声明，不能推断开发者从未使用过它。REA 自己的 FX3 Discussion #3027 是第三方电池限制的求助，核查时没有回复，不是已完成的破解。另一些“快门角度”标题也应回到验证表：leogenot 的 A7 IV 6.02 研究只确认图标显示，调节仍受门控，不能据此推出完整录像功能或跨系统兼容。([REA FX3 讨论](https://github.com/morluto/rea/discussions/3027)、[A7 IV 原作者验证表](https://github.com/leogenot/sony-a7iv-feature-research/blob/12582457829e34eae7211df5b0c599fa46b7e5e1/README.md))

旧 OpenMemories Tweak 面向支持 PlayMemories Camera Apps 的机型和隐藏设置；旧 PMCA updater 路径的限制，也不能概括现代所有服务入口。反过来，A7 IV 硬件研究对其特定 eMMC 分区的“没有 signature verification”描述，不能外推到 FX3/ZV-E1。**本次没有核定两台目标机的完整启动验证、反回滚及失效恢复机制。**([OpenMemories](https://github.com/ma1co/OpenMemories-Tweak)、[PMCA 固定版说明](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md)、[A7 IV 原始研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE))

## ZV-E1 与 FX3 共享平台特征，仍不足以直接交换系统

Sony 官方规格将两者都列为全画幅 Exmor R、相近有效像素与 BIONZ XR 平台。这可以支持“技术基础接近”，但官方信息不足以证明具体传感器 die、主板、内存布局和固件接口完全相同。FX3 有主动风扇、双 CFexpress Type A/SD 槽与全尺寸 HDMI；ZV-E1 官方列单 SD 槽、Type-D HDMI，且 RAW 输出规格不同。这些外围和热管理差异会影响完整固件的初始化与运行。刷入软件不会产生缺失的硬件。([FX3 原始发布](https://sony.mediaroom.com/2021-02-23-Sony-Electronics-Launches-FX3-Full-Frame-Camera-for-Cinematic-Look-and-Enhanced-Operability-for-Creators)、[FX3 规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)、[ZV-E1 规格](https://www.sony.com/electronics/support/e-mount-body-zv-e-series/zv-e1/specifications))

工程上，整套跨刷还要解决产品识别、驱动、按钮和屏幕、传感器校准、热管理、更新接受及恢复入口。即使共用部分主应用，也不能据此认定修改一个型号字节即可工作。ZV-E1 自身也已有 HD HEVC 代理，无需借 FX3 系统取得这条管线；其官方热条件说明则进一步提示，持续录制能力必须按机身与环境验证。([ZV-E1 代理](https://helpguide.sony.net/ilc/2310/v1/en/contents/0412M_proxy_rec.html)、[官方热条件](https://helpguide.sony.net/ilc/2310/v1/en/contents/0601L_auto_power_off_temperature.html))

截至本次检索，未找到包含准确原版本、目标版本、补丁源码、成功启动、稳定录像与可验证恢复方法的 **ZV-E1→FX3 完整跨刷案例**；同样未找到 **FX3 7.02 独立 1080p29.97/30 HEVC 主录**的完整实现。这个结论是公开证据不足，不是理论不可能。Sony 当前公开下载为 FX3 7.02（2026-03-17）、ZV-E1 2.02（2025-11-11），各自限定适用型号；官方更新包及设置导出没有被证明能恢复任意刷坏状态。([FX3 更新说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)、[ZV-E1 更新说明](https://www.sony.com/electronics/support/software/00296227)、[本次项目检索与缺口](<../research_notes/索尼 FX3 ZVE1 固件研究/projects.md>))

## 下一阶段应先确认用途，再追踪最小功能改动

官方代理已把研究问题从“硬件能否编码 1080 HEVC”推进到“能否让这条管线满足你的实际交付要求”。先做上述短片验证，能直接判断是否还需要固件开发；若必须只录一份 HEVC 主片，下一步有价值的离线工作是展开 FX3 的 `/usr`、`/system` 与 WBI2，定位主应用及编码/封装参数，查清代理是否依赖主流初始化、分辨率和帧率如何路由。找到模式名称或菜单枚举之后，仍需验证录像数据、音频、同步、分段、长录与温度行为，才能认定新增模式实现。

对你的主力机，“保证安全”的可执行边界目前是继续电脑端只读分析和使用官方录制设置。进入机身写入前，准确机型/版本上的可再生补丁和失效时仍可到达的恢复通道都还缺证据，现阶段不能交付安全定制固件。全部研究笔记在 [官方能力](<../research_notes/索尼 FX3 ZVE1 固件研究/official.md>)、[逆向项目](<../research_notes/索尼 FX3 ZVE1 固件研究/projects.md>)、[实测解包与跨刷](<../research_notes/索尼 FX3 ZVE1 固件研究/crossflash.md>)，离线原件、脚本、哈希和清单保存在[任务工作目录](../work/sony-firmware-20261024/)，可沿证据继续研究。
