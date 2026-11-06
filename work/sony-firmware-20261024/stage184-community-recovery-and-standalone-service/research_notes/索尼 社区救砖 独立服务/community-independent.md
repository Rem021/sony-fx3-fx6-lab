# 索尼社区独立恢复路线与经典 FX3 7.02 的转用条件

## 哪些社区项目真正提供独立于正常拍摄应用的入口

### Takeaway

2026-10-29 定向复核发现，A7 IV、A6700 和一代 ZV-E10 已有不同程度的 BootROM／RAM Fastboot 实作；其中 ZV-E10 明确提供 Linux 不可启动时的用户分区恢复脚本。**这些是型号专用先例，本轮未找到其公开支持经典 ILME-FX3 7.02 的证明。** PMCA 的 serviceshell 则是在系统已经运行时使用的服务接口，不能凭它支持某型号，就推成该型号坏 MAIN 后仍能进入。([A7 IV 原研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/README.md)、[ZV-E10 恢复](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/recovery.md)、[PMCA 模式说明](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md))

### Cited Findings

本轮经 GitHub commits/HEAD API 得到下列修订；日期是提交者 UTC 时间，核验是本轮网络请求，而非搜索摘要中的旧 HEAD。

| 项目 | 当前固定修订／提交时间 | 本轮确定的适用范围 |
|---|---|---|
| DavidBuchanan314/ILCE-7M4-RE | `e85e137fc3b88b7cb26e69faa9f1304184678ff7`，2026-10-28 12:09:46Z | A7 IV 原始 BootROM、RP2040 与裸机 Fastboot 研究；README未给FX3适配声明。[提交](https://github.com/DavidBuchanan314/ILCE-7M4-RE/commit/e85e137fc3b88b7cb26e69faa9f1304184678ff7) |
| Erlla/sony-a7m4-custom-firmware | `0bfeee4f961610434588dc89c2cd3bc658816a3d`，2026-10-28 18:19:05Z | ILCE-7M4 官方6.02相关方法；SD救砖另有精确initrd门控。[提交](https://github.com/Erlla/sony-a7m4-custom-firmware/commit/0bfeee4f961610434588dc89c2cd3bc658816a3d)、[方法](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/README.md) |
| dino2048/zv-e10-toolkit | `bd2b4ac03af71bd397f8b88162db1ec1671e222a`，2026-10-26 15:38:38Z | ZV-E10固件`30110_05.2025031501`、macOS主机。[提交](https://github.com/dino2048/zv-e10-toolkit/commit/bd2b4ac03af71bd397f8b88162db1ec1671e222a)、[范围](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/README.md) |
| xyzhangxin/sony-a6700-powerful | `d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9`，2026-10-23 11:41:35Z | A6700 2.00；本轮API成功，补足181轮API失败的时效缺口。[提交](https://github.com/xyzhangxin/sony-a6700-powerful/commit/d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9) |
| ma1co/Sony-PMCA-RE | `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`，2022-08-18 12:46:04Z | 主分支仍是该修订；新issue反馈不代表主分支新增独立恢复器。[提交](https://github.com/ma1co/Sony-PMCA-RE/commit/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0) |

- **A7 IV 的 Fastboot 是注入的裸机程序。** 原作者说明通过配件接口RX在复位后触发串行BootROM，再使用自制Fastboot读写eMMC；透明加解密明确排除尚未实现的boot0。Fastboot目录还称其运行于USB 2.0 Multi口。它不是证明“索尼所有相机出厂就有标准Fastboot USB模式”。— [原README](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/README.md)、[payload说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/payloads/fastboot/README.md)。
- **Erlla方法0只是已有Fastboot之后的恢复触发器。** 需要Multi引出线、RP2040-Zero启动桥及相应外部payload；普通USB线不能替代。免Fastboot安装路径则明确要求正常开机并进入MSC，因此不能作为MAIN无法启动时的等价入口。— [固定README](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/README.md)、[接线范围](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/docs/wiring.md)。
- **一代ZV-E10有独立的两级路线。** Pico经串行BootROM把stage1放入SRAM，主机经USB加载stage2；后者读写eMMC，无需Sony-PMCA-RE。需要RP2040 Pico、24针USB-C引出板、复位电阻／CC电阻、Python、libusb和主机fastboot。已发布配对镜像分别8028B和10588B，源码说明约四分钟外部复位限制，长恢复要分批重新注入。— [BootROM说明](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/README.md)、[硬件说明](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/hardware.md)、[配对manifest](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/prebuilt/manifest.json)。
- **ZV-E10代际不可混同。** ma1co的型号表将`ZV-E10`列为`CXD90045`；这里不是ZV-E10 II，也不是FX3的型号适配。`restore_rescue.py`硬编码16个用户分区名，不包含`nflashaB0/B1`。— [上游型号表](https://github.com/ma1co/fwtool.py/blob/master/devices.yml#L499)、[恢复源码](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/host/restore_rescue.py#L32)。
- **A6700当前公开Pico路线只读。** 手册称RAM临时Fastboot不要求相机菜单MSC／FTP；历史完成的是用户区分区表覆盖的1,864,368,128字节和两个引导区各前4MiB，双读校验；未确认物理eMMC全部容量，完整恢复尚未验证。当前普通USB应用支持限定字段开关，完整备份恢复入口仍未提供。— [固定操作手册](https://github.com/xyzhangxin/sony-a6700-powerful/blob/d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9/操作手册.md)、[进展](https://github.com/xyzhangxin/sony-a6700-powerful/blob/d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9/开发计划与进展.md)。
- **PMCA分三种入口，不能混用能力。** App安装依赖支持PMCA的Android相机；updatershell利用自定义更新代码，README明确排除CXD90045／CXD90057签名架构；serviceshell在运行系统上执行代码，须完成USB服务切换与认证。— [固定模式说明](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md)。

### Inferences

- 最值得转用的是“在正常应用之前建立型号专用RAM入口，验证当前分区与同机备份，再受限写入并完整回读”的结构；不是跨机复制payload、FAT偏移、分区表或密钥。
- 用户目前只有Mac与Windows11 x86、没有Pico／串行硬件；这不足以执行上述已公开硬件入口。换电脑可改变主机USB驱动与运行环境，但不能替代缺少的启动桥、目标适配和正确接线。
- serviceshell可能适合作为“Linux／USB服务仍活着”层的恢复入口；它是否独立于FX3拟改的appFw／av-cam及看护链，须由FX3本身代码与后续授权验证，不能由其他型号正常开机解锁成功推出。

### Gaps

- 本轮检查的上述项目与定向FX3检索中，未见“经典FX3 7.02、MAIN／av-cam损坏、独立BootROM入口、恢复原件、回读与拍摄”公开闭环；这是本轮范围的未发现，不是声称整个互联网或Sony服务体系不存在此能力。
- ZV-E10公开文档给出固件身份；未把其营销版本号另行猜成某个版本。表中CXD90045来自上游型号表，而非本轮拆机或芯片读取。
- 未将REA／AI辅助品牌、QEMU能启动、代码生成或工具菜单中的“救砖”文字列作硬件入口的证明。

## 已公开的恢复成功、失败和备份覆盖到底到哪一层

### Takeaway

可核对的源码能够区分六分区触发备份、16用户分区恢复、Linux可见镜像与物理存储全覆盖。公开“有硬件验证”与公开了逐次故障／恢复原始日志也不是同一层；ZV-E10与Erlla当前文档须保留这一证据差异。([ZV-E10恢复范围](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/recovery.md)、[Erlla验证说明](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/validation.md))

### Cited Findings

| 路线／材料 | 真正保存／恢复的范围 | 原始记录与未覆盖部分 |
|---|---|---|
| Erlla A7 IV MODE5触发 | 本次六区`B0/B1/1/2/8/13`；只写`nflasha2`本次候选，变更DAT4两字节及MODE／MODE5空标志文件的目录项；完整20MiB回读后普通重启 | 精确修改版initrd白名单，既有密钥仍决定DAT接受；主机`update_completed=false`，不把重启算机内安装成功。[恢复源码](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py)、[profile](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/profiles/sd-recovery.json) |
| Erlla维护者历史同机记录 | 称观察NOR更新结束、User Update OK、NOR回读一致、正常取景 | 原始备份／日志留本地未公开；2026-10-21公开适配是离线验证，没有新的公开版硬件安装验收。[验证E-004与限制](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/validation.md) |
| ZV-E10 Linux raw backup | Linux驱动可见user area与B0/B1各读两次，边接收边哈希、fsync后主机再读哈希 | 非物理芯片dump；无RPMB、OTP/eFuse或隐藏区；可写分区两次读取可能变化，非原子快照。[Linux说明](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/linux/README.md) |
| ZV-E10 Linux前restore_rescue | 仅显式选定的16用户分区；离线按布局切片、稀疏镜像、哈希检查，写后读回；不自动reboot | 需要BootROM注入、stage1通信和eMMC仍正常；不处理boot0/1、分区表和物理故障。备份含B0/B1不等于恢复脚本会写B0/B1。[恢复指南](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/recovery.md)、[源码](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/host/restore_rescue.py) |
| ZV-E10验证声明 | 维护者称裸机读写、sparse、回读及分区恢复有硬件记录；发布配对与旧已验版本逐字节相同 | CONTRIBUTING规定研究快照、test-pattern drills、private device data不进公开仓库，并明确此次整理未新增hardware session。未见公开逐次坏机→恢复原始日志。[README](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/README.md)、[开发与验证](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/CONTRIBUTING.md) |
| A7 IV常规维护完整备份 | payload列出的eMMC分区、boot0/boot1、分区表与SHA256 | 明确不等于整颗芯片所有地址；不含独立CP NOR、其他MCU与全部硬件状态；涉及CP NOR须另备。六区触发备份不能替代。[备份范围](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/README.md#备份范围与恢复条件) |

- FX3A #715是**2.02正常可进MSC时**的本人认证故障→切换Mac Python／libusb环境→PAL/NTSC设置成功反馈；不是经典FX3 7.02，也不是主程序损坏后的恢复。首帖失败与本人后续成功应一起读，不能只取标题“authentication timeout”。— [本人完整后续](https://github.com/ma1co/Sony-PMCA-RE/issues/715)（见issue中2026-06-09的“SUCCESS”段；本轮按全文核对）。
- 经典FX3官方更新故障有**本人失败与维修后续**：2025-04-11一帖描述4→6.02 SD更新失败、多次续行无效，首帖后补称维修更换主板；这是该机主维修结果，不是证明故障必须换板或不可软件恢复。— [原帖及机主后续](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)。
- 2024-09-27求6.00文件帖中`Shaolin_Wolf`称送Sony Pro Service，9月28日补充正常返还、版本5.00、换主板。该帖同时转引`TheSilentPhotog`第三次SD续行成功的话，但本轮未定位到后者原评论，所以**仅作为被转引成功线索**；不能升级成我们的独立首手复验。该贴中“只有Creator App会坏”的猜测，与上一个明确SD更新失败个案不一致。— [原帖本人维修评论及被转引成功文字](https://www.reddit.com/r/FX3/comments/1fqgexj/in_need_of_the_fx3_ver_600_dat_update_file/)。
- 2025-01一名经典FX3机主称由1.01经Mac执行两阶段官方更新后不响应；后续更新器仍检测相机但反复报错。所读线程没有机主修复后续；这说明“可检测”本身不能作为恢复成功。— [原始故障帖](https://www.reddit.com/r/FX3/comments/1hu6qui/fx3_firmware_update_failed_camera_wont_turn_on/)。

### Inferences

- 六区／局部备份足以服务“限定标志触发＋原更新器仍健全”的恢复合同，不能覆盖更新器、引导区、独立NOR或个体校准被破坏的任意故障。
- “换主板修好”只证明维修存在结果；没有芯片读写记录，不能把它描述成Sony或社区已经完成原板eMMC离线重编程。同理，维护者说有本地日志时，应标“维护者硬件经验／声明”，不能冒充公开原始逐步记录。
- 只要恢复触碰个体设置／校准，必须保持同机身份和当前布局；健康机备份、官方DAT、他机整区镜像三者不能混称可互换原件。

### Gaps

- 未取得经典FX3 7.02外部编程器读原芯片→恢复引导／校准→全回读→正常拍摄的公开可复核个案；没有足够证据给出原板外部重写采购／接线处方。
- ZV-E10原始硬件会话日志、坏分区前后镜像和完整拍摄验收不在所读公开树中；目前能公开复核的是代码、镜像配对manifest、限制与维护者验证声明。
- A7R V项目（[本轮API HEAD `75dbcc05393b0d6a08b3f46e187215d5bbba43b5`](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware/commit/75dbcc05393b0d6a08b3f46e187215d5bbba43b5)）有功能修改与重启失败历史，但所读入口没有新增经典FX3独立恢复证据；未继续扩展为无关机型功能清单。

## 面向经典 FX3 7.02，应如何按失败状态选择下一项研究

### Takeaway

当前最有价值的工作是把FX3目标修改范围与“仍然活着的最早入口”对齐；不必要求每个小试验先备整机，却必须证明备份能够经未被拟改目标破坏的入口写回。下表是从已列社区能力推导的研究合同，**不是FX3上机步骤或已验证救砖方案**。

### Cited Findings

| 故障状态 | 已有社区先例 | 所需入口／材料 | 移到FX3还缺什么 |
|---|---|---|---|
| 仍能正常开UI／MSC | A7 IV免Fastboot安装、PMCA serviceshell、A6700普通USB功能关闭 | 正常USB切换与认证、目标原文件／原字段、受限逆修改与回读 | 经典7.02的具体文件协议、修改窗口和退出／冷启验收；UI正常不证明全部功能正常。[A7 IV入口](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/README.md)、[PMCA](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md) |
| UI／MAIN坏，但Linux与服务仍活 | ZV-E10把Linux服务路线与BootROM路线分开 | 服务进程、USB gadget、认证及文件／块读写存活；本机原件 | FX3 sen／服务是否能独立于appFw、av-cam、CP和看护进程运行，须单独证明。[ZV-E10 Linux前提](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/linux/README.md) |
| Linux也不能启动，BootROM还能注入／RAM Fastboot可运行 | A7 IV独立RAM payload；ZV-E10两级16用户分区restore | 型号专用硬件时序与payload；eMMC控制器、分区几何、密文／明文映射；可信同机备份 | FX3专用入口、SRAM／USB／eMMC／CP映射、可回读写范围；A7 IV和ZV-E10二进制不能代用。[A7 IV](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/README.md)、[ZV-E10恢复](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/recovery.md) |
| BootROM通信／引导区／存储或其他硬件层也失效 | 已见FX3维修换板本人后续；未找到本轮可复核外部原板重写闭环 | 服务能力或型号专用外部硬件；若重写则需物理几何、引导区、个体原件与回读 | 不能用官方DAT或Linux可见备份自行补齐缺失的OTP／RPMB／独立NOR／校准；外部编程是否可行须具体器件证据。[维修后续](https://www.reddit.com/r/FX3/comments/1jwp86i/602_firmware_update_bricked_fx3/)、[Linux dump边界](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/linux/README.md) |

### Inferences

- 先读目标机原件证明“MAIN坏了仍可选中现有updater”或“sen独立存活”任一条，即可明显缩小恢复合同；随后才决定哪些局部原件必须备份、何种错误必须更早入口。
- 若只做真正不持久化的RAM实验，保存原值、核对入口副作用和确认断电回原状态可能比全eMMC镜像更直接；若拟改更新器或早期选择器，则需要更早入口，服务文件备份不足以代替。
- 对用户现有硬件，本轮可推进的是离线源码／固件映射、恢复候选边界和依赖列表。Windows11 x86仅是已知可用主机条件，本轮不安装驱动、不运行PMCA／UU／Fastboot、不启动任何相机／USB／管理员／GUI动作。

### Gaps

- 本轮不负责重新证明stage182／183的FX3内部独立服务链；这些应由对应研究员用FX3原件补证。这里不把其他型号经验替换成FX3当前实机事实。
- 自有证据为本目录`community-evidence/source-manifest.json`及其列出的少量文本；部分raw.githubusercontent请求发生TLS EOF／握手超时，已原样记error，成功网页阅读与API实时HEAD核验分开记录。不下载固件、payload二进制、工具安装包或大仓库。
- 范围遵守只读研究。旧stage、正式README、canonical材料和记忆未修改；仅在目标卷UUID核对通过后创建本任务笔记与文本证据。

### 定稿时的源码范围勘误

综合登记前复核本轮已保存的固定`sd_recovery.py`：A7 IV的`BACKUP_NAMES`明确为`nflashaB0`、`nflashaB1`、`nflasha1`、`nflasha2`、`nflasha8`、`nflasha13`，`recover()`初始化记录`full_eMMC_backup=False`。因此本项目只陈述这六个确切名称与非整盘范围，**不猜测B0/B1对应boot0/boot1，也不把这六区描述成“不含boot0/1”**。前文ZV-E10恢复器不写boot0/1及分区表的结论属于另一项目，不套到A7 IV；旧封存阶段不改。([固定源码](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py#L17))
