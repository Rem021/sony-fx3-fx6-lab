# FX3 独立恢复入口与最小可逆修改

## 原厂 SD 更新环境能否在 MAIN 损坏时工作

### Takeaway

发现了明确可继续追的恢复路线：FX3 官方历史更新分区自带内核和 initrd，脚本可从自己的 init 直接分派到 SD 更新器；7.02 AP 中的启动切换脚本又与这个历史环境逐字节相同。这支持研究“保留原更新器、另行选择它以恢复应用”，但尚未证明当前7.02实机的强制进入入口，也未证明当前更新器允许同版本重装。[历史更新分区来源与边界](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/README.md)；[7.02 AP 原件及标志来源](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/image-origin-results.json)

### Cited Findings

- **独立环境确实存在于官方2.04／2.05过渡固件。** `0400_updater/dev/nflasha1` 内有 `/boot/vmlinux.bin`、`initrd.img`、`cxd90057.dtb`、`kemco.txt` 及原校验记录。两份分区各19,377,152字节，原CRC通过；initrd各含216普通文件。这里读取的是官方旧件，不是用户相机当前分区。[分区目录](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/updater-fat-inventory.json)；[来源与CRC](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/original-update-engine-results.json)
- **从 updater init 到 SD 输入的脚本分派不要求先调用 appFw.so。** `/sbin/init` 建立自己的环境、RAM目录并装载驱动后直接启动 `UdtrMain.sh`；后者选择模式，再调用 `execute_ufp.sh`。在 MODE_MSCRYPT=5 分支，后者装载存储卡驱动并启动 `sdfileinput.elf`，预载 `libInfraSKD.so`。这是所见脚本控制流的事实，不等于所有被调用 ELF 的全部内部依赖已审计。[init 第3至42行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/sbin/init:3)；[UdtrMain 第69行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/UdtrMain.sh:69)；[SD 分支第60至66行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh:60)
- **“独立环境存在”与“能强制进入”是两件事。** `UdtrMain.sh::getCurrentMode()` 在缺少 `/setting/updater/mode` 时选择 production，并非自动 SD 更新；mode3／2／6／1 还有高于 mode5 的优先级。`uincomp` 存在时会在进入 execute_ufp 之前走错误退出。不能把普通故障灯／插入SD卡当成已经选到了 SD 恢复器。[模式选择第7至37行及不完整标记第63至66行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/UdtrMain.sh:7)
- **对7.02的直接桥接已在本次静态重读核实。** 只读解析现有7.02 AP分区 `nflasha15.img`，先校验整分区 SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`，再取 `/bin/up.sh`：6572字节，SHA-256 `c774320a0ab92c13b467b9219e1f60262a1effa0b551ba3b713514a36dadc402`，与2.05 updater内 `/usr/bin/up.sh` 全字节相同。只运行既有只读 ext2 解析器，未执行 Sony 脚本或程序。这与已有来源记录一致。[7.02脚本源记录](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/image-origin-results.json)；[原AP分区指纹](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/partition-carve-manifest.json)
- **这份相同脚本在正常运行侧准备下次启动。** `func_mscrypt` 写 `/setting/updater/mode`、`mode5` 并 sync；其末尾在 `/root/IAMUPDATER` 不存在时调用 `ud_send_lsi.elf $mode_num`，对应 ms 分支传5。只改文件和调用子控制器的关系由脚本可见，但 `ud_send_lsi.elf` 内部及更早boot selector如何采纳仍未证明。这里没有执行任何写标记或切换模式。[up.sh 第55至71行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/up.sh:55)；[ms分支和最终发送第336至367行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/up.sh:336)
- **恢复还依赖未损坏的启动／存储基础设施。** updater 的 `insmod.sh` 先装载 `crypt-emmc.ko`、运行 `setup_nflash.sh`，再挂载 nflasha2 的 `/setting` 并加载备份设置驱动；正常路径设置分区挂载失败会退出。SD 分支另外依赖存储卡、SKD、公钥及其信任比较。这些依赖比 MAIN 应用更底层，不能因有原包就忽略。[驱动与设置依赖第12至35行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/insmod.sh:12)；[块设备映射脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/setup_nflash.sh)；[SD验签路径](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/README.md)
- **当前7.02包内另有更新执行镜像，但不能把它当作已验证可冷启动的 rescue initrd。** FDAT中1,253,376字节的 SquashFS body image 及 AP 内预置 `udtrbody.bin` 哈希相同；`BaseBodyLoaderModule::bodyExecute` VA `0x9064` 根据 `/root/IAMUPDATER` 选择上传镜像或预置镜像。该 body image 是更新流程的执行组件，和 nflasha1 的完整 kernel/initrd 是不同层级。[7.02镜像及原函数](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/README.md)

### Inferences

- 若修改范围只涉及应用／编码模块，且 boot selector、updater分区、设置、加密块设备和存储卡链均保留，独立更新环境原则上有机会重装官方包，而无需先恢复损坏的 MAIN 应用。关键未知已可收敛为：**MAIN失效后怎样独立选择 updater，以及该机实际 updater 是否接受当前恢复包**；不再笼统重复“没有已验证修改包”。依据为上述独立脚本链与7.02相同启动脚本。
- Erlla 的 A7 IV 恢复方法也是先在 Fastboot 中改设置分区的 mode/mode5 和版本记录，再让原 updater 从卡上更新；它为上述 FX3 标志层对照提供了具体先例。但其精确基线是 ILCE-7M4 V6.02、白名单中的一份修改版 updater，不能直接用于 FX3。该路线本身不负责进入 Fastboot，updater或更早引导损坏时也不适用。[固定代码](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/a7m4/sd_recovery.py)；[维护者恢复说明](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/0bfeee4f961610434588dc89c2cd3bc658816a3d/methods/00-sd-recovery/README.md)

### Gaps

- 未取得用户当前机身 nflasha1 的实机原件；历史2.04／2.05内核/initrd与7.02运行安装状态不能合并。单个 up.sh 相同不证明整个 updater 相同。
- 还没有经典 FX3 的独立 Fastboot／BootROM进入、冷启动 selector、读／写设置分区及恢复回读证据。已有Mac Fastboot识别为空只描述此前MSC状态，不证明永远无法进入。[已有识别与源码范围](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage135-Fastboot-entry-discovery/README.md)
- 尚未证明版本比较、settings标记、介质、包签名及机型等所有条件同时允许7.02同版本重装。复制A7IV的BCD0.00不是已验证的FX3方案。

## RAM 优先试验能否替代直接持久刷写以及需要保留哪些恢复材料

### Takeaway

RAM内最小修改值得优先研究，能缩小故障影响范围；但实际载荷入口、真实内存归属和WBI加载／失效语义仍需确定。恢复需求应对应修改范围：应用原字节回退、整分区重装、引导／CP损坏救援需要的材料与入口不同，不能把所有失败混成一种“有备份就可救”。[既有最小参数原型边界](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage75-private-preset-storage/README.md)；[WBI恢复适配边界](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage46-upstream-restore-audit/README.md)

### Cited Findings

- 当前16Mbps参数原型把副本移到 harness声明的试验槽，尚未在相机真实分配RAM、装载或执行。选择指针的原生共享状态及生命周期仍未完成；模型地址不可当作相机地址。[stage75原型](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage75-private-preset-storage/README.md)
- `/tmp`是否RAM取决于运行环境。7.02正常MAIN的现有官方启动记录把它配到可写 nflasha10；历史 updater 的 `mkramdsk.sh` 则明确把 `/ramdsk` 挂260M tmpfs、`/tmp` 挂64M tmpfs。**不能把 MAIN 的挂载规则机械套到独立 updater，也不能按路径名字宣称RAM。**[正常启动配置的原件记录](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage7-entry/firmware/runtime-static.json)；[updater RAM目录第5至19行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/mkramdsk.sh:5)
- 认证建立服务并非整条链零写入：7.02 `NinThread` VA `0xbe6c` 输出最终认证应答后，还可能走 `.hasp`、`.etools` 与模式文件尾段；当前相机上是否触发未查询。纯RAM目标不自动消除进入通道的这些条件副作用。[当前7.02原库审查](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage136-authentication-and-system-read-admission/authentication-publication-review.json)
- 原 `updater_storage_backup.sh` 和 restore脚本只处理 `UPDATER_STORAGE_DEV=/dev/nflasha13` 下的非易失 updater storage/hash/history及其临时副本；restore会在相应条件下格式化该分区。它们不是appFw／整机／校准数据的完整备份恢复。[common.src](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/common.src)；[backup脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/updater_storage_backup.sh)；[restore脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/updater_storage_restore.sh)
- 7.02参考 MAIN appFw.so 是79,015,712字节，只拿两个服务库无法恢复它；官方包原件也不是当前机身设置／个体数据备份。[原件读取范围](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage136-authentication-and-system-read-admission/README.md)
- 7.02官方FDAT的完整密文及IV已通过同一官方 RSA-2048／SHA-256公钥验签，修改签名覆盖字节后原签名不匹配。原文件替换、明文分区写回及正常SD更新包是不同写入合同，重算CRC／CBC并不能替代包验签。[原官方签名数值及边界](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/official-key-rsa-verification-results.json)

### Inferences

| 修改／故障范围 | 对应的最低恢复证据应包含 | 当前判断 |
|---|---|---|
| 单次RAM参数／代码试验 | 实际分配及地址、原字节、所有使用者退出、原状态复位、WBI不会把试验状态带入后续启动的证据 | 有离线候选；尚无真实装载及复位证据。不能许诺拔电即还原。 |
| appFw／av-cam等持久模块窗口 | 对应同机完整原件与窗口前后哈希、实际所在文件系统及加密／块映射、受限回写器、sync与完整回读、加载与WBI确认 | 可在更改前制作恢复工件；当前还不能把A7CII的程序/偏移常量套来回写。 |
| MAIN模块损坏而boot/updater完好 | 上述材料，加独立选择 updater／写设置的入口、当前updater指纹、能接受的官方恢复包、更新日志及机内启动验收 | 本轮发现明确静态路线；入口和当前updater适配尚缺。 |
| updater／boot selector／早期引导／CP NOR也损坏 | 各实际受影响介质的同机备份、几何/密文-明文合同、相应更低层独立读写入口及验证 | SD updater可能不再可用；Mac/Windows本身目前无已证明可替代的FX3底层入口。 |

表为研究上的恢复合同推导，不是已完成的实机恢复。A7IV维护者明确把RP2040串行BootROM→RAM Fastboot作为独立路线，且透明加密不含boot0；这是别机型研究，不能假设FX3电气、ROM、RAM及CP启动相同。[原作者说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE)

### Gaps

- 未证明WBI关机保存、冷启动和缓存加载会如何处理RAM试验状态；模型重新初始化不能代替物理冷启动。
- 未读取用户机身完整原件、设置／备份和当前分区几何。无法从官方包替代个体数据；也不应在尚无目标映射时开始通用全盘写入。
- “要准备的备份类别”已经能按修改范围列清，但实际源范围、可恢复写入入口及回读仍需逐项核对；备份文件存在本身不证明读回/写回合同正确。

## 接下来最值得检查的三个原始入口

### Takeaway

下一轮应先追“怎样选择独立更新环境”，不继续扩展主机夹具数量，也不先生成完整修改包。以下三个切口都可在现有原件上静态检查，不需要诱发主力机变砖。[已确认的7.02启动脚本](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/body-load-20261029/image-origin-results.json)

### Cited Findings

1. **7.02 AP里的 `ud_send_lsi.elf` 入口及其直接导入／调用者。** 从与历史相同的 `up.sh` 末尾调用出发，跟踪请求0／2／5的编码、交给哪一子控制器或电源管理接口、是否先设持久启动标志。目的：区分 mode5 是“进入已选中的updater后采用SD输入”还是同时触发更早的引导选择。不能先假定设置文件本身可使 MAIN 故障机进入 updater。[实际调用点第367行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/up.sh:367)
2. **当前实际 nflasha1 的 kernel/initrd／`/sbin/init`／`UdtrMain.sh::getCurrentMode`身份与上游选择器。** 先确定现有7.02官方材料是否完整带该分区；不能用旧2.05替代。待有具体读取方案时只取得当前原件作指纹，静态追加载p1与p3的上游决定、`uincomp`故障分支。目的：证明 MAIN不运行时，哪种已知入口仍能达到这条独立链。[历史p1成员](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/updater-fat-inventory.json)；[当前已提取普通分区清单](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/partition-carve-manifest.json)
3. **`libsdfileinputupdaterapi.so` 中 `SDUUDConditionChecker::getUpdateFirmwareInfo` 的版本来源和拒绝分支。** 已有原反汇编可继续读，结合 `copyCurrentFirmwareInfo()` 将p1的dat2/dat3及p2的dat4复制到RAM的路径，核对同版本官方包能否重装、该数据是否真控制比较，以及签名／机型检查先后。目的：制定恢复准入，而不是盲改版本记录。[原函数片段](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/disassembly/SDUUDConditionChecker-getUpdateFirmwareInfo.txt)；[数据来源脚本第7至15行](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/execute_ufp.sh:7)

### Inferences

- 若入口1／2证明能够在应用损坏后独立选择未改动的 updater，且入口3确认一种可接受的同机官方恢复包，那么首次改动就可进一步限制在非引导模块，并以事先形成的原件／恢复包回退。这是一条可逐步证伪或证实的路线，不要求先有“已经成功刷过的最终修改包”。
- 先构造不会传给相机的恢复工件（同机原件清单、差分白名单、待恢复字节、目标指纹／几何、恢复后核对项目）是有意义的准备；真正装载／设置／写入仍须等入口证据和具体方案。

### Gaps

- 本次只读静态工作，没有取得新的机身信息、进入模式、运行 Sony 代码、构建载荷、读卡、读写机身或刷写。也未把A7IV白名单与20MiB设置分区参数作为FX3实机条件。
- 本笔记只覆盖独立入口与回退设计；具体社区成功/失败案例及Sony官方客服恢复流程由其他研究者核对。
