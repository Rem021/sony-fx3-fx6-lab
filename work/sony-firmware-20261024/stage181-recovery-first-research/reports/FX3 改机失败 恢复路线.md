# 先证明 FX3 刷坏后退路，再推进 HEVC 主录

2026-10-29，经典 **ILME-FX3 7.02**，目标仍为1080p29.97 HEVC主录。研究优先级现改为**修改失败后怎样退回**；缺少已验证修改包，是研究要解决的问题，不能循环作为停止研究的理由。本轮找到更具体的退路：旧官方分区确有独立更新环境，7.02又保留相同的更新切换脚本。现在最应证明的是“MAIN坏后怎样选中它”和“恢复续行接受什么包”，再据此设计最小修改。

## 独立更新器已有原件，强制选择入口尚待证明

官方2.04／2.05的更新分区带自己的kernel、initrd；所见脚本从init进入`UdtrMain.sh`，MODE5分支启动SD输入更新器，分派过程不要求先调用`appFw.so`。这是**历史原件**，不是当前7.02机身分区；7.02包内另一个body执行镜像也不能代作完整救援initrd。([分区与脚本证据](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/README.md)、[7.02 body范围](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/README.md))

本轮静态重读核实：7.02 AP里的`/bin/up.sh`为6572字节，与2.05 updater脚本**全字节相同**；它准备`mode/mode5`，并在正常环境调用`ud_send_lsi.elf 5`。这提供了7.02的直接追踪起点，但单脚本相同不证明整个updater相同。旧脚本缺少mode时走production，其他模式有更高优先级，`uincomp`还会阻止继续；插卡或黑屏本身都不证明进入SD恢复。([7.02来源指纹](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/image-origin-results.json)、[模式选择原件](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/UdtrMain.sh:7))

Sony明确提供指定更新失败后的重新上电续行，但未公开经典FX3从“未选择更新、MAIN已坏”状态强制进入的方法。FAQ正常准入拒绝同版／旧版；**不能据此断言恢复续行也必然拒绝同版**，两个入口的判断须分别追代码。([Sony 7.02错误流程](https://service.sony.com.cn/content/casch/download/firm/00003048.html)、[Sony续行及版本FAQ](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342))

## A7 IV 给出设计先例，尚无 FX3 现成救援器

A7 IV已有“独立Fastboot→受限写设置标志与版本记录→重启交给SD更新器”的具体实现。它先要求Multi接口／RP2040进入BootROM并装载RAM Fastboot；触发脚本本身不负责进入，且只接受一个精确的**修改版initrd**。这说明独立于拍摄应用的退路值得移植研究，不代表FX3可直接运行，更不能照搬设置分区大小、偏移或BCD版本值。([固定恢复代码](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py)、[入口与适用条件](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/README.md))

A7C II故障机主从Movie模式恢复的后续也是真实线索，但保留的录像启动路径是前提；FX3拟改的正是录像逻辑，不能预设同样旁路仍活着。其局部原字节恢复方法可参考，不能当作MAIN完全失效后的入口。([本人后续](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31#issuecomment-6442900646)、[固定恢复范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py))

## 备份和退路须覆盖实际改动范围

| 改动范围 | 必须建立的恢复材料与入口 | 当前边界 |
|---|---|---|
| 纯RAM参数／代码 | 原值、真实内存归属、使用者退出及撤销；确认WBI和重启不保留试验状态 | 无需一律先备全eMMC；尚无FX3真实装载／复位证明 |
| 持久appFw窗口 | 同机完整原文件、精确差分及相关设置；独立于拟改窗口的逆写入口、完整回读与冷启动加载核对 | 文件备份本身不能使坏MAIN重新可达 |
| av-cam／编码器或独立CP程序 | 先查实际介质及依赖；备对应镜像、配置与涉及的个体数据，分别设计文件／CP NOR恢复 | eMMC不能自动覆盖独立NOR；A7C II清单不含av-cam |
| boot／updater／选择器本身 | 更早的型号专用入口，加对应boot区、几何、密文／明文映射及个体数据 | 原SD更新器可能已失效；现有Mac／Windows没有已证明的FX3替代入口 |

这是按失败范围推导的恢复合同，尚非实机验收。原`updater_storage_backup`只覆盖nflasha13，不是整机备份；服务认证还可能条件写入`.hasp`、`.etools`及模式文件，纯RAM目标也须核清入口副作用，不能宣称全程零写入。([原备份范围](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/updater_storage_backup.sh)、[7.02认证尾部审查](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage136-authentication-and-system-read-admission/authentication-publication-review.json)、[分范围研究笔记](<../research_notes/FX3 改机失败 恢复路线/independent-entry.md>))

## 下一项离线工作应直接证明逃生路径

**先追7.02的`ud_send_lsi.elf`请求与boot selector**：从已确认的脚本调用出发，解析0／2／5请求交给谁、是否设置持久启动状态，以及哪个上游决定加载更新分区而非MAIN。交付可复核的调用链和条件表，明确MODE5究竟只选SD输入，还是也参与早期引导选择。同时核对现有7.02材料是否含完整nflasha1，缺件就列出精确缺件，不能拿2.05冒充当前更新器。([调用点](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/up.sh:367)、[现有分区清单](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/partition-carve-manifest.json))

随后追`SDUUDConditionChecker::getUpdateFirmwareInfo`，核对dat2／dat3／dat4的来源、同版比较及拒绝分支、恢复续行状态和签名／机型检查顺序，形成“正常更新／失败续行／独立触发”的准入差异表。目的是找出可用恢复包的准确条件，不能先照搬A7 IV改版本号。([原反汇编](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/disassembly/SDUUDConditionChecker-getUpdateFirmwareInfo.txt)、[版本数据复制](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh:7))

这两项能把“有没有退路”变成可证伪的具体问题，随后再形成原值、拟改值、最小逆修改和入口依赖工件。本轮没有相机动作；此前55项SDK夹具、20项进程夹具均不充相机验收。**目前仍无已验证修改包、FX3独立救援闭环或目标HEVC主录实录，也不保证任意刷坏可救。** ([179边界](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage179-bounded-IOKit-wire/README.md)、[180边界](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage180-native-MSC-request-channel/README.md))
