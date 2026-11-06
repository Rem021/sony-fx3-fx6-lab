# FX3 与 ZV E1 跨机型固件及离线解包证据

## 现在能不能真实解包 FX3 和 ZV E1

### Takeaway

可以开始安全的离线研究，而且本次已经实际完成 FX3 7.02 官方包完整下载、FDAT 容器解密、整包 CRC 与全部分块校验、内部 tar 的 155 项目录枚举。ZV-E1 2.02 已完成官方 HTTP Range 头尾取样和首块解密/头 CRC 验证。两者都成功匹配公开 CXD90057 k8 解密路径；这是一项离线格式和加密层证据，不是刷回、移植、录制或恢复证据。

### Cited Findings

- 研究日期为洛杉矶当地 2026-10-24；技术回执 UTC 为 2026-10-25。用户称 FX3 已是最新版，本次使用公开 Sony 7.02 包，未从机身读取版本。[Sony FX3 7.02 官方页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)
- ma1co/fwtool.py PR #52 在 2026-09-10 提交，目前仍 open；作者实际测试列表明确包括 FX3、FX6、FX2、A7 IV、A7S III、A7C II 等。原 master 机型表没更新，不能据旧表断言现代机不可解包。[PR #52](https://github.com/ma1co/fwtool.py/pull/52)
- 本次核验并固定 DavidBuchanan314/fwtool.py a7iv commit `3955d7890fc38daf942bb52827599bfe35de4a14`。源码 `fdat.py` 支持 CXD90057 k0/k8 AES-CBC 解密，`AesCbcCrypter.encrypt()` 明确抛出 `Encryption not supported`。因此公开工具具备解密能力，未提供该代完整重加密打包能力。[固定版 fdat.py](https://github.com/DavidBuchanan314/fwtool.py/blob/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/fdat.py)
- q19032/Sony-firmware-unpacker 原页是对 ma1co/fwtool.py 的封装/说明，正文描述 CXD90057/CXD90058 的公开推导；本次不采用来历不明的预编译程序，只参考可审阅的原始格式代码。该仓库记录 commit `e118ab0145275382d6114e047b8ce4df98020374`，未 clone 或保留第三方源码副本。[原仓库](https://github.com/q19032/Sony-firmware-unpacker)
- 官方 FX3 7.02 `BODYDATA.DAT`：811,876,768 bytes，官方发布日期 2026-03-17；日本支持页给出的公开下载 URL 为 `https://support.d-imaging.sony.co.jp/download/NEX/ey8d8a84ee/BODYDATA.DAT?fm=jp`，正常重定向至 Sony CDN。完整下载 SHA-256 `f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854`。整包 UFU CRC32 `0x92be8c5f` 通过，792,848 个加密块校验和以及末块标志全部通过。[官方页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)；[本次下载回执](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/fx3-7.02-download-receipt.json)；[本次完整解包清单](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/fx3-7.02-offline-manifest.json)
- FX3 解密 FDAT 为 808,704,512 bytes，SHA-256 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`；内部固件 tar 807,450,624 bytes，共 155 项，含分区配置、各区默认备份、`nflasha15` /usr 镜像、`nflasha3` /system 镜像、`nflasha5` WBI2 镜像、rootfs、CP、`cxd90057.dtb`。`MainDest.txt` 明确含 `SYSIPSX-DSLR / ALCIN / CX95900_UC2.bin`。[实测清单](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/fx3-7.02-offline-manifest.json)；[限量分区/配置探测](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/fx3-7.02-bounded-probes.json)
- ZV-E1 2.02 官方包为 1,060,230,584 bytes，2025-11-11 发布。仅取前 65,536 bytes 与尾部 284 bytes，未完整下载。官方头 CRC 与首块校验通过，model ID `0x20030000`；FX3 为 `0x91030080`。两者 UFU 外层与 CXD90057 k8 路径相同，但型号头不同。[ZV-E1 官方页](https://support.d-imaging.sony.co.jp/www/cscs/firm/?area=jp&lang=jp&mdl=ZV-E1)；[双包实测头信息](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/ufu-header-analysis.json)
- 所有实际操作为电脑端下载/读取字节，未打开相机 USB、未启动更新器、未执行包内程序、未向卡根目录复制、未修改任何相机。自写脚本用 `ast.literal_eval` 读取固定版公共常量，不执行下载来的 Python 源码。[头探测脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/inspect_ufu_headers.py)；[完整包解密脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/decrypt_fx3_offline.py)

| 层级 | FX3 7.02 本次结果 | ZV-E1 2.02 本次结果 |
|---|---|---|
| 官方来源/文件长度 | 已验证，整包下载 | 已验证，Range 获取 |
| UFU 外层识别 | 已完成，整包 CRC 通过 | 已识别，未做整包 CRC |
| FDAT 头解密/CRC | 已完成 | 已完成 |
| 整个 FDAT 解密/分块检查 | 已完成，792,848 块通过 | 未做 |
| 固件 tar 列目录 | 已完成，155 项 | 未做 |
| 嵌套文件系统/主应用函数 | 未解出，未分析模式表 | 未做 |
| 重打包、刷入、运行、恢复 | 均未做 | 均未做 |

### Inferences

- 本次双包成功解密证明可对现代 FX3 与 ZV-E1 做有价值的离线研究，不宜再以“Sony 全部加密所以研究不了”作结论。
- 共享公共解密路径表明固件封装/加密代际相近；不证明所有 CPU/传感器/内存/驱动/主板相同，也不证明存在相同的更新签名或跨刷许可。model ID 不同只证明两包面向不同型号，不能单独证明跨刷绝对不可能。
- 内部默认文件名有 `backup`，不代表拿到了用户机身逐台校准值、完整 eMMC、boot0、主副处理器/NOR 或可恢复救砖备份。

### Gaps

- 没有解出嵌套分区内的主相机应用和编码调用图；未定位 HD30 HEVC 模式描述、白名单、分辨率约束或编码器驱动控制点。分区名称与常量不是模式可用证据。
- 未对嵌套文件系统进一步判断压缩、加密或稀疏映像格式，不能把它们统称“仍加密”，也不能声称完整所有文件系统已恢复。
- 没有做 Sony 包签名认证；CRC 和分块校验能证明获取/解密一致性，不能替代安全签名或设备运行验证。

## ZV E1 能否安全刷成 FX3 系统

### Takeaway

本次没有找到可核验的 ZV-E1→FX3 完整移植、稳定录像和恢复闭环；不能把它作为安全可用方案。公开进展足以证明研究路径存在，但不够证明直接使用 FX3 官方包或修改机型字节会成功。

### Cited Findings

- A7C II 最新成熟工具的原 README 明确只支持 ILCE-7CM2 固件 2.01，并拒绝其他型号。其服务模式、应用补丁、局部曲线/设置解锁不是跨型号整套固件移植。[A7C II Tools 原 README](https://github.com/QAQLeonard/a7c2-fl23-research)
- YuuLuo 的原始研究限定 A7C II 2.01，证明服务认证、Jiritsu 路径与 preload 一次 root 执行链；这不证明 FX3 或 ZV-E1 的同链、地址和落盘方式相同。[原始服务研究](https://github.com/YuuLuo/a7c2-service-preload)
- DavidBuchanan314/ILCE-7M4-RE README 记载 A7 IV 的 eMMC 分区 AES-XTS 加密但没有 signature verification，并提供串行启动/fastboot 备份恢复研究；fastboot crypto 不含 boot0 的实现。这个技术事实限定其 A7 IV 研究对象，不能外推为 FX3/ZV-E1 同样无签名或可恢复。[原 README](https://github.com/DavidBuchanan314/ILCE-7M4-RE)；[该 fastboot 文档](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/payloads/fastboot/README.md)
- Sony 官方 FX3 与 ZV-E1 更新页各自限定适用型号和更新过程，错误数据可报“target model incorrect”；Sony 还明确提示更新断电可能无法工作。官方提供的是受支持的本型号升级流程，不是跨刷或任意损坏恢复保证。[FX3 更新页](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298559)；[ZV-E1 更新页](https://www.sony.com/electronics/support/software/00296227)
- Sony FX3 官方发布材料确认主动风扇、双 CFexpress Type A/SD 槽、全尺寸 HDMI Type A，并称 HEVC 主格式为 4K only。外设/散热这些差异影响完整固件适配，不能通过写入系统凭空取得对应硬件。[Sony FX3 原始发布](https://sony.mediaroom.com/2021-02-23-Sony-Electronics-Launches-FX3-Full-Frame-Camera-for-Cinematic-Look-and-Enhanced-Operability-for-Creators)

### Inferences

- 更合理的研究方向是先在本机型固件中确认目标功能已存在，再研究最小模式/设置补丁；整套跨刷同时涉及板级初始化、外设配置、按键屏幕、热管理、校准和恢复，失败面显著更大。
- 同传感器或相同 BIONZ XR 名称不能推出相同系统镜像；即使共享主应用，产品分类、驱动与配置也可能不同。上述是工程判断，不是已证明的 FX3/ZV-E1 独有安全机制。
- 应避免“安全签名绝对无法破解”和“解密了就能任意刷”这两种过度结论。目前可确认离线研究进展，无法确认安全跨刷。

### Gaps

- 未找到带准确 ZV-E1 型号/原固件/目标 FX3 固件/补丁源码/启动证据/正常录像/回退路径的完整公开跨刷案例。
- 未实测 FX3 或 ZV-E1 的服务认证、ROM/boot0/NOR、签名检查、反回滚、机身唯一校准数据备份或恢复。
- 未找到可复核的 FX3 7.02 主录 1080p29.97 HEVC 补丁与录制样本。这个缺口不等于物理不可能，也不支持在用户主力机试写。

## 在安全条件下下一步能做什么

### Takeaway

当前安全完成的是“官方包→离线解密→可复核目录/配置证据”；下一阶段可在电脑上继续分析 FX3 本机型模式表和代理编码路径。进入相机写入以前，必须先有针对准确型号/固件的可复现补丁与经验证的恢复手段；本次证据尚不足以把任何实验包称为可安全刷入。

### Cited Findings

- 本次所有原始包、部分样本、SHA-256 回执、脚本与 JSON 清单均保存在任务工作目录。完整 FX3 FDAT 已解密但未展开主应用，不应把本次产物宣传为“完整 FX3 系统破解”。[工作目录](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/)
- 当前原始格式工具对该代没有加密写回实现，现代服务链和 A7 IV 硬件恢复研究也各自限定适用环境；仅备份官方包、仅做菜单设置导出，均没有被这些来源证明能恢复任意刷坏状态。[固定版加密边界](https://github.com/DavidBuchanan314/fwtool.py/blob/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/fdat.py)；[服务链适用范围](https://github.com/YuuLuo/a7c2-service-preload)；[A7 IV 原始研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE)

### Inferences

- 对 HD30 HEVC 的有效逆向问题应是：已有代理 HEVC 管线是否可在保留分辨率/帧率时作为唯一正式录制输出，是否需要主录流初始化、代理固定低码率/4:2:0是否可改、录音/元数据/分段/热管理是否正常。仅把菜单加一行、枚举改成 H.265 不足以回答。
- 如果需要进一步研究，可优先继续只读解析 `nflasha15` /usr、`nflasha3` /system 与 WBI2，定位主应用和 codec/muxer 参数表，先做静态映射和代码路径比较。找到字符串或隐藏枚举后仍需真实样片解码/持续录制验证，才能宣称功能实现。
- 备份与可恢复是两个不同结论。恢复闭环需要在失效模式下仍能到达的下载/引导通道、完整必要区域和本机唯一数据，以及准确设备上已验证的流程。

### Gaps

- 用户未提供精确机身版本画面；“最新版”按公开 7.02 研究，没有读机证据。
- 本次没有建立任何机身写入或实机恢复条件，也没有修改相机；目前不能交付安全定制固件。
