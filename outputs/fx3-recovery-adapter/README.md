# FX3 恢复适配工具 0.5

[实施路线与当前进度](ROADMAP.md)：8个里程碑、首刷前置、已有成果和下一批交付标准。工具版本号与测试数量不表示真机验收进度。

**已实现的第一版是离线镜像工具：识别 FX3 更新分区、生成限定候选、检查改动范围，以及从备份重建原始镜像。** 参考了 A7C II 社区的原件绑定、片段长度保持和逆修改设计，重新绑定到 FX3 自己的原库和函数。代码没有相机传输、管理员启动或刷写入口。

当前在 Mac 上，以 Sony 官方 FX3 2.04、2.05 的原始 p1 载荷完成真实文件闭环。0.2新增本地采集；0.3新增机身侧C工作器候选；0.4把固定C源码与显式入口链接为静态Linux ELF，并在ARM64指令模拟环境中完成三组383块读取和精确还原。**系统调用、内核状态与数据源仍为自建夹具，未在相机上加载或执行；尚未取得或验证你这台7.02机身的p1原件，没有完成真机恢复，也没有包含1080p29.97 H.265功能补丁。** Windows主机运行未验证。

0.5新增独立的boot0／boot1读取源码候选、固定入口、动态容量协议、本地解码及组装。它使用公开7.02主系统文件指纹作为有限的环境过滤，拒绝更新环境标记；这些检查不证明已加载驱动、机身来源或安装中的p1身份。启动区读取可能触发内核切换eMMC访问选择，特定失败路径存在panic，结束后恢复先前选择尚未证明。**本版仅交付源码和本地构建工具，没有相机上传、启动或恢复后端。** 0.4发行压缩包原样保留。

## 可以实际运行的功能

| 命令 | 本地操作 |
|---|---|
| `inspect` | 检查逻辑／已解密的FAT12 p1镜像；验证FAT副本、簇链、长文件名、内核／initrd MD5，识别两份更新库 |
| `build` | 保存完整输入，动态定位SquashFS压缩片段，生成固定长度候选和变换清单；再次解析核对 |
| `verify` | 复核完整原件与候选SHA、全部允许范围、压缩流及新库内容 |
| `diagnose` | 将本地镜像分为原件、候选、已知范围混合或未知状态；不自动修复 |
| `rollback` | 在新目录生成与备份逐字节相同的原镜像；不是向机身写回 |
| `capture-local` | 从已保存的完整本地p1文件逐块读取、留档、关闭来源，再组装和回读镜像 |
| `verify-capture` | 用外部提供的SHA复核完整读取记录、三组清单、383块数据和镜像；不证明机身来源 |
| `assemble-worker` | 解码已保存的三组工作器格式文件，核对请求、精确长度、范围、设备号及CRC，再在本地重组；不加载C代码 |
| `build-worker` | 本机编译固定C／汇编源码，完成限定重定位，生成静态Linux ELF与链接记录；不执行该文件 |
| `boot-request` | 在本地生成boot0／boot1专用请求，首组允许发现容量；不上传 |
| `build-boot-worker` | 本地构建独立的boot读取候选ELF，核对源码指纹；不加载或启动 |
| `assemble-boot-worker` | 验证1至4组已经保存的boot记录、正常返回码和完整范围，在本地重组；不接触相机 |

输入只接受本项目内的单链接普通文件，拒绝设备节点、FIFO和符号链接；输出必须使用不存在的新目录，不覆盖原件。中断或失败留下的目录保留，缺少完整manifest的结果会被拒绝。原件、候选和结果文件按0600创建，输出目录按0700创建；不上传。

## 首次复核

无需安装新Python依赖。在当前工作区运行：

```sh
cd outputs/fx3-recovery-adapter
python3 -B -m fx3_recovery --help
python3 -B -m fx3_recovery inspect \
  --input ../../work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-inspect
python3 -B -m fx3_recovery build \
  --input ../../work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle
python3 -B -m fx3_recovery verify \
  --bundle ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle
python3 -B -m fx3_recovery rollback \
  --bundle ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle \
  --input ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-bundle/candidate.p1 \
  --out ../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/manual-restored
```

再次运行须换输出目录名。检查报告中的`flashable`、`hardware_validated`和`current_body_p1_identity_verified`始终为false。命令没有`--execute`或`--flash`，不能用上述结果启动机身刷写。

已有本地完整快照时，`build --scope unverified-snapshot --body-tag <64位十六进制摘要>`可以记录操作员提供的分组标记。输入须为25,100,288字节且两库全部匹配；标记不得填原始序列号。**这只是本地关联，不是机身身份验证或采集回执。**默认`reference`只接受两份固定官方历史原件。输入应是`cnflasha1`类逻辑／已解密视图，不是完整BODYDATA.DAT或未经识别的物理密文。

## 0.2 定长读取与留档

`capture-local`只打开本地普通文件，使用`O_RDONLY`和固定偏移读取。固定研究配置为25,100,288字节，分383块、每块65,536字节；三组分别为128／128／127块。**该长度来自已保存的FX3配置证据，不是本次实测相机分区长度。**历史2.04／2.05分发载荷较短，不能直接作为完整输入，工具不会自动补尾。

读取前检查外部提供的完整SHA和文件元数据；每块关联本次随机请求，检查精确返回长度、状态、来源一致性，再保存0600数据和哈希。三组清单按SHA串联。结束时重算来源全SHA，确认来源关闭，重新读取已落盘的383块、组装镜像并回读，最后才写`complete.json`。

调用前写入`read-in-flight`日志。总预算600秒、单次5秒，超期返回的数据拒绝入库；**这些是调用前后的检查，不能中断正在阻塞的系统调用**。不创建超时替代调用、不强杀、不自动重试。未正常返回的调用记为`UNKNOWN_IN_FLIGHT`并保留提供者引用，关闭失败记为`UNKNOWN_CLOSE`；两者均不能形成完整备份。进程退出或主机重启后的实际设备状态没有在本版得到处理或验证。

已保存完整本地镜像时可运行：

```sh
python3 -B -m fx3_recovery capture-local \
  --input <项目内已有的完整p1普通文件> --sha256 <独立保存的完整SHA256> \
  --body-tag <本地分组用64位十六进制标记> --out <不存在的新目录>
python3 -B -m fx3_recovery verify-capture \
  --capture <上一步目录> --sha256 <同一个外部SHA256>
```

这里的外部SHA用于验证已有本地文件及采集程序，不是对首次机身读取提出“必须提前知道机身SHA”的循环条件。首次真实采集仍需实现机身来源绑定、双次一致性检查等独立方案。操作员标签、全文件SHA、读取成功及来源关闭都不等于相机身份认证、服务正常退出或救砖证明。

主机采集目前只提供`RegularFileSource`，内部读取接口预留给后续评审；主机端没有动态插件加载、相机节点打开、服务认证、工作器上传或Sony运行时导入。未来实际相机后端需要另行实现。参见[读取实现](fx3_recovery/capture.py)与[故障测试](tests/test_capture.py)。

## 机身侧工作器候选与0.4链接

[C源码与明确限制](native/README.md)只提供显式函数入口，固定目标为`/dev/cnflasha1`；根据内核分区记录、块设备身份和容量进行检查，不照搬A7C II的设备编号。分区始终O_RDONLY，输出仅限经fstatfs核验的tmpfs新目录。短读、容量变化、来源变化、超期返回、证据写入和关闭失败均拒绝完成；没有preload、构造函数、删除、自动重试或刷写代码。

0.3只有AArch64可重定位对象与Mac系统调用夹具；0.4新增[限定链接器](fx3_recovery/elflink.py)和显式`_start`，生成无动态加载器／外部导入的静态ELF。47项当前本地检查通过，其中ARM64模拟环境实际执行生成的机器码，完整输出三组383块，再完成本地候选和原件还原。Linux系统调用、设备与tmpfs仍是假提供者，未启动真实Linux或FX3内核。

每个构建只支持该工作器固定的C／汇编源码和5类已观察的重定位，检查操作码、目标、对齐、范围、字段回算及范围外不变；页分为R／RX／RW，栈不可执行。两种工作器的入口名称分别限定，不支持的编译器输出会拒绝，不进行地址猜测、导入补齐或宽松回退。生成文件以0600保存在新0700目录，不自动执行。

```sh
python3 -B -m fx3_recovery build-worker \
  --out ../../work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/runs/manual-worker-build
```

输出含`worker.elf`、两份中间对象、源码计划及59处链接记录；再次运行须换目录。**可执行文件格式不等于机身可启动方案。** 当前没有上传／启动命令；受审查的机身入口、实际传输、同机绑定、服务归还与Sony内核支持仍待验证，不能将构建物直接上机试运行。

`assemble-worker --windows <第0组目录> <第1组目录> <第2组目录> --returns 0 0 0 --body-tag <64位分组标记> --out <新目录>`仅复核已保存的本地格式。返回码是调用者提供的记录，不是工具独立观察的相机退出证明。即使每组内部一致，分组之间也可能发生内容变化；全部来源、硬件与独立恢复标志保持false。

FX3原日期触发命令固定设置2017年的时间，不接受任意shell文本；原固定库加载分支仍在当前进程中加载libJit.so。本工具没有采用这些路径，也不把终端切换的成功响应当作shell已经开启。[188轮入口核对](../../work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/launch-route-review.json)。

## 0.5 启动区候选

目标限于当前公开主系统模块已对应的`/dev/nflashaB0`与`/dev/nflashaB1`，设备号分别252:126、252:127。两者必须同时出现在唯一的分区记录中、容量相等，再用原路径已识别的BLKGETSIZE分别核对。容量只接受实际报告的`1..255 × 128KiB`，不填入4MiB或formatter写入长度；最大33,423,360字节不是当前机身实测值。

每块65,536字节，一次入口最多读取128块，完整区域最多4组。首组可用`expected_total=0`发现容量；后续请求必须填入首组记录的容量，绑定同一capture ID、目标、指纹和全局偏移。128字节请求、256字节块头和256字节清单与旧p1协议分开，跨目标／错误范围／缺组／CRC损坏／非正常返回均拒绝。调用者提供的返回码和分组标记仍不是可信的相机来源证明，分组读取也不证明原子快照。

以下命令只创建本地文件，输出目录每次须换新；capture ID示例只用于本地检查，未来实际采集须由受审查方案生成新随机值：

```sh
python3 -B -m fx3_recovery boot-request \
  --capture-id 88888888888888888888888888888888 --target boot0 --window 0 \
  --out ../../work/sony-firmware-20261024/stage215-AP-boot-capture-worker-candidate/runs/manual-boot-request
python3 -B -m fx3_recovery build-boot-worker \
  --out ../../work/sony-firmware-20261024/stage215-AP-boot-capture-worker-candidate/runs/manual-boot-build
```

候选逐个核对`emmc.ko`、`crypt-emmc.ko`和`devno.ko`的精确长度、SHA-256及前后元数据；存在`/root/IAMUPDATER`或查询它出现ENOENT以外错误即拒绝。主系统原文件与更新环境驱动不能互换。静态选中路径跳过已识别解密回调，实际字节视图、写回对应关系和访问选择归还均未验证，报告中明确保持false。

候选不写源分区；输出限经核验的tmpfs新文件。短读、元数据变化、容量变化、保护区异常和超期返回不补读、不重试。阻塞时入口仍挂起，不能因主机超时伪造退出；清单写入、同步、关闭或最终目录关闭失败时，已有清单也不能覆盖失败返回。没有进程外可信回执或重启后状态恢复实现。

11项新增测试包含容量最小值与最大值的全区域合成文件、实际C的SHA校验和失败分支，并执行当前链接ELF的ARM64机器码。Linux调用、内核、节点和时钟均为自建夹具。详细结果及旧功能回归见[215轮证据](../../work/sony-firmware-20261024/stage215-AP-boot-capture-worker-candidate/README.md)。这些测试不能代替真机备份、独立启动或救砖验收。

## FX3 专用改动

第一版配置`fx3-p1-reference-v1`绑定以下完整库指纹，任何不符都会停止：

| 原库 | 长度 | SHA-256 |
|---|---:|---|
| `libsdfileinputupdaterapi.so` | 60,584 | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` |
| `libupdatercorecommon.so` | 72,864 | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` |

前者使用FX3原`isVersionOK`的`0x9fd4`与`VerifySignature`的`0xabf0`，并保留`isModelOK/isRegionOK`字节；后者使用已完全匹配的`0xd208/0xd27c`。A7C II的`0xa0cc/0xace8`没有被移植到FX3。它们是原ELF内已核验的文件偏移，不是运行地址。

**该配置会在离线候选中改变版本／签名检查及核心版本判断；不会生成Sony新签名。** 压缩片段由实际文件系统映射推导，不硬套A7C II的initrd长度、片段偏移或p1chksum位置。重新压缩必须保留原长度并完整解码，额外字节、截断和填充流均拒绝；FAT映射和校验文件之外的字节必须保持原样。

这是恢复与安装通路的参考组件适配，不是完整改机安装器。即使本地快照的库指纹匹配，也只证明组件代码匹配，不能证明它来自指定机身或故障时仍有路写回。

## 下一步接入与限制

尚需补齐当前机身p1的可信来源与组件指纹、实际相机读取／恢复后端、菜单RAM版本门的FX3专用绑定、DAT重封和功能补丁，以及服务退出和独立救援验证。现有两份历史原件不能冒充7.02机身读回。

未知或混合状态会保留并拒绝自动回退；本地重建原件不证明断电后机身能接收它。也没有把standalone sen的USB存活当作独立文件服务：目前GET／SET仍依赖im里的Jiritsu消费者。

[源码与参考说明](NOTICE.md) · [实现](fx3_recovery/engine.py) · [测试](tests/test_adapter.py) · [本轮证据](../../work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/README.md)

## 新增安全传输防护、自动符号定位与包导出 (`fx3_recovery.__init__`)

- **[`macos_usb_transport_guard.py`](fx3_recovery/macos_usb_transport_guard.py)**：实现 macOS 26+ `IOUSBHost` `0xe00002be`（`kIOReturnExclusiveAccess`）独占冲突退避状态机（MSC `054C:0DA1` `>= 350 ms` 静默等待 + 指数退避 `50/100/200/400/800 ms` + `IOUSBHost` 接管）、Vendor Control `(0x43, 1, 0x37FF, 0xD7AA)`、USB STALL 非重传保护、Senser v1（FX3 `0x91030080` 7 轮校验 -> `054C:0336`）与 Senser v2（RSA 挑战 fail-closed 拒止）分类，以及硬锁定的只读 Jiritsu (`0x40 / 0x1001`) 防火墙（`ALLOW_PERSISTENT_JIRITSU_WRITES = False`、`ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS = False`）。
- **[`p1_symbol_autolocator.py`](fx3_recovery/p1_symbol_autolocator.py)**：提供面向 FX3 Ver. 7.02 `p1` 更新库（`libsdfileinputupdaterapi.so` 与 `libupdatercorecommon.so`）的偏移无关 4 位点自动重定位（`autolocate_4_sites`）、合成偏移镜像闭环校验（`run_autolocated_p1_roundtrip`）、逐字节回滚恢复（`rollback_autolocated_patches`）与可选 Unicorn AArch64 仿真校验（`verify_sites_in_unicorn`），强制保持 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` 与只读供体访问。
- **[`emmc_dump_forensic_verifier.py`](fx3_recovery/emmc_dump_forensic_verifier.py)**（Phase 42 Tier-4 只读 eMMC 转储取证审计器）：在任何硬件恢复或 Phase `H0` 演练采信本地转储之前，严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 双次 SHA-256 一致性读取与校验 eMMC 分区镜像与 `EXT_CSD`：
  - **总线卡死 / 截断 / 熵坍缩检测（`analyze_bus_and_entropy`）**：拦截全 `0x00`/全 `0xFF`/单字节恒定填充、`>=16` 页连续 `0xFF` 上拉卡死、非 512B 对齐或长度截断读出，以及 `p1`/AES-XTS-256 `cnflasha` 的全局与 64 KiB 滑窗香农熵坍缩。
  - **Sony 分区魔数与几何校验（`verify_sector0_dump` / `verify_p1_vfat_dump` / `verify_p2_bk4_nvram_dump` / `verify_p5_wbi2_dump` / `verify_p8_cp_rtos_dump` / `verify_ext_csd_dump`）**：核验 Sector 0 `'8246' '2.00'` 30 项分区表及 FX6 `p18@0x312000` 偏移告警、`p1` FAT12 BPB、`p2` `'BK4\0'` 校验和与 `PRODUCT_MODEL = 0x91030080`（`ALCIN_UUD`）FX3 不可变约束、`p5` `'WBI2'` 88B 休眠头与 `0x0f0f0f0f` 节描述符 XOR 校验、失效魔数 `wbi2`/`WBI3` 识别、`p8` (`nflasha8`) FAT12 (`reserved=32`) `/cpapp-b.bin` ARMv7-R 复位向量与 `[TOMCO]` 标记，以及 `EXT_CSD[179]`（`PART_CONFIG` `0xB3`）启动使能与磨耗指标。
  - **引导链不可变防火墙（`audit_boot_chain_immutability`）**：硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` 与 `ALLOW_BOOT_PARTITION_TARGETING = False`，拒绝任何针对 `BOOT0`、`BOOT1`、`RPMB`、`nflashaB0/B1`、`nflasha1..nflasha8`、`sector0`、`loader_nor` 或 `CMD42` 写/擦/锁操作的清单。
- **包级导出（[`fx3_recovery/__init__.py`](fx3_recovery/__init__.py)）**：直接导出 `macos_usb_transport_guard`、`p1_symbol_autolocator`、`emmc_dump_forensic_verifier` 及其核心类与函数，支持 `fx3_safety.h0_hardware_rehearsal` 自动集成。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-emmc-forensics --clean-room

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -v
```

## Phase 47 — Unified Tier-0..Tier-4 Unbrick Escalation Ladder Simulator & `p1` VFAT Atomic Rollback Capsule Verifier

- **[`unbrick_ladder_and_capsule_verifier.py`](fx3_recovery/unbrick_ladder_and_capsule_verifier.py)**：将 `outputs/fx3-recovery-adapter/` 内全部五大恢复支柱（[`capture.py`](fx3_recovery/capture.py)、[`boot_worker.py`](fx3_recovery/boot_worker.py)、[`macos_usb_transport_guard.py`](fx3_recovery/macos_usb_transport_guard.py)、[`p1_symbol_autolocator.py`](fx3_recovery/p1_symbol_autolocator.py)、[`emmc_dump_forensic_verifier.py`](fx3_recovery/emmc_dump_forensic_verifier.py)）统一至确定性 Tier-0..Tier-4 救砖升级状态机与 `p1` VFAT 原子回滚胶囊校验器：
  - **12 场景 Tier-0..Tier-4 确定性升级梯（`run_12_scenario_escalation_matrix`）**：按“精确诊断 -> 最小权限恢复层选择 -> 恢复后验真（含零持久写入不变量）”覆盖以下 12 种故障模式：
    1. `S01_CLEAN_STAGE_AB_REBOOT`（`TIER_0`）：Stage-A/B 零持久 RAM 卸载断电重启，即时恢复原厂 FX3 `v7.02` 启动（`emmc_write_bytes = 0`）。
    2. `S02_P1_VFAT_BOOT_COUNTER_LATCH`（`TIER_0`）：`p1` VFAT Stage-A/B 启动计数器（`boot_attempts >= 1`）一次性故障保护锁存，无需拆卸 SD 卡即自动回退原厂启动。
    3. `S03_WF12_00342260_WIRELESS_HANG`（`TIER_0`）：`00342260` `WF-12`（`6L+9S` LED）无线致命挂死防御与恢复——由 `P12` `0x70d4` + `BK4` Airplane 影子项阻断；未打补丁试验遇到时需 `>= 60s` 冷断电清除。
    4. `S04_0X100D_EARLY_INIT_APPFW_ABORT`（`TIER_0`）：`0x100D`（`13S` LED）早期 `init`/`appFw` 中止 -> `TIER_0` 一次性 hook 跳过并恢复原厂 FX3 启动。
    5. `S05_MACOS26_IOUSBHOST_PIPE_STALL_H0`（`TIER_1`）：macOS 26 `IOUSBHost` `0xe00002be` USB MSC 管道阻塞 -> 调度 `MacOSUSBTransportSession` 静默等待（`>= 350 ms`）与指数退避干净重试，零破坏性重传。
    6. `S06_SHIFTED_VMA_V702_P1_AUTOLOCATE`（`TIER_2`）：VMA 偏移的 FX3 `v7.02` `p1` 更新库 -> 硬编码 v2.00 偏移 fail-closed 拒绝，通过 `autolocate_4_sites` 4 位点 AArch64 `ADRP/BL` 签名定位并验证逐字节回滚（`rollback_byte_exact = True`）。
    7. `S07_CORRUPTED_H0_EMMC_STUCK_BUS`（`TIER_4`）：受损/截断的 `H0` eMMC 备份读出（全 `0x00`/全 `0xFF` 总线卡死与长度截断）-> 被 `analyze_bus_and_entropy` / `verify_emmc_dump_bytes` 预检拦截，强阻断 `H1` 进入（`h1_entry_blocked = True`）。
    8. `S08_VMC_BNCM1_LTC_CABLE_TIER3_UART`（`TIER_3`）：Multi-Port `VMC-BNCM1` LTC 线缆未拔出时尝试 `Tier-3` `RP2040-Zero` `-DOPEN_DRAIN` `48000` 波特 `uart_boot` -> fail-closed 阻断，直至拔除 LTC 适配器并通过 `1.8V/3.3V` 开漏治具校验。
    9. `S09_DESTRUCTIVE_FASTBOOT_FIREWALL`（`TIER_3`）：破坏性 Fastboot 指令（`fastboot erase` / `flash boot0` / `oem format`）-> 被 BootROM 指令防火墙与 `audit_boot_chain_immutability` 阻断（`persistent_emmc_writes_authorized = False`）。
    10. `S10_LD_SO_PRELOAD_BUSYBOX_DEADLOCK`（`TIER_2`）：`/etc/ld.so.preload` 动态 BusyBox 死锁注入尝试 -> 打包前即被静态 ELF / `LD_PRELOAD` 作用域限定 `appFw` 启动器契约拒绝。
    11. `S11_CROSS_BODY_FX6_WBI2_INJECTION`（`TIER_2`）：跨机身 `FX6 WBI2` 休眠快照注入尝试 -> fail-closed 拒绝，保证 `wbi_mutation_bytes == 0`。
    12. `S12_THERMAL_OR_USBPD_BROWNOUT_ABORT`（`TIER_0`）：`H0` 采集中发生 `>= 90.0°C` 过温或 USB-PD `< 7.80V` VBUS 欠压 -> 优雅中止与零分区改写（`partition_mutation_count = 0`）。
  - **`p1` VFAT 原子回滚胶囊与双遍 SHA-256 校验器（`build_p1_vfat_rollback_capsule` / `verify_p1_vfat_capsule` / `audit_capsule_fsync_order`）**：构建并校验支持 `FAT12` 与 `FAT16` 的 `p1` 故障保护 hook 胶囊，覆盖 `8.3` 与 LFN 长文件名条目、FAT1/FAT2 镜像一致性、簇链环路/交叉检测、`tempfile` `O_CREAT|O_EXCL|O_NOFOLLOW` 暂存 -> `fsync_tmp_file` -> 首遍 `O_RDONLY` SHA-256 -> 原子替换 -> `fsync_parent_dir` -> 二遍 `O_RDONLY` SHA-256 序列，`boot_attempts >= 1` 一次性锁存及确定性 `capsule_sha256`（FAT12 `663503a2...` / FAT16 `7da7b1dc...`），硬锁定 `persistent_emmc_writes_authorized = False`。
  - **CLI 与双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-unbrick-ladder [--clean-room] [--json] [--out ...]`，并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部公开符号；[`tests/test_unbrick_ladder_and_capsule.py`](tests/test_unbrick_ladder_and_capsule.py) 包含 30 项快速测试（`< 0.6s`），同时在本地供体模式（`os.O_RDONLY`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下通过，保留全部 137 项既有测试绿色通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-unbrick-ladder --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -v
```

## Phase 59 — Camera-Disconnected `RP2040-Zero` `-DOPEN_DRAIN` `1.8V` Multi-Port Bench Fixture Self-Test & `48000`-Baud PIO Verifier

- **[`rp2040_multiport_fixture_selftest.py`](fx3_recovery/rp2040_multiport_fixture_selftest.py)**：在将自制 Tier-3 Sony 15-pin Multi-Port 救砖线插入物理 FX3 机身**之前**，提供离机台架（`camera_connected == False`）全自动电气安全与协议自检：
  - **15 针 Sony Multi-Port 万用表预检防火墙（`audit_ohmmeter_isolation` / `verify_open_drain_1v8_swing` / `verify_multiport_id_keying`）**：
    - 强制断开相机与 `VMC-BNCM1` LTC 线缆，校验 `VBUS (5.0V)` / `3.3V` 供电轨与 `UART_TX (Pin 8)` / `UART_RX (Pin 7)` / `ID (Pin 6)` / `XRESET (Pin 9)` 之间以及线间隔离电阻 `>= 1 MΩ`、`Pin 2` GND 连续性 `<= 2.0 Ω`，并阻断标准 Raspberry Pi Pico（`GP29` `VSYS/3` 分压下拉缺陷）。
    - 校验开漏 `1.8V` 上拉摆幅（`V_idle ∈ [1.71V, 1.89V]`、`V_low <= 0.35V`），任何 `> 1.98V` 或 `3.3V` 推挽输出立即触发 `FAIL_OVERVOLTAGE_HAZARD`。
    - 校验 Multi-Port `Pin 6 (ID)` 电阻键控矩阵：`BOOTROM_UART_BOOT`、`CONSOLE_READONLY`（禁止拉低 `XReset` 与主动 TX 驱动），以及对 `VMC_BNCM1_LTC_ADAPTER`（`680 kΩ`）和 `LANC_REMOTE`（`100 kΩ`）冲突的 fail-closed 阻断。
  - **`RP2040-Zero` (`125 MHz` / `133 MHz` `clk_sys`) PIO 分频、开漏指令与 CMake 构建标志审计（`compute_pio_uart_clkdiv` / `audit_pio_open_drain_program` / `audit_cmake_open_drain_flags`）**：
    - 精确核验 RP2040 16.8 小数分频器（`div = clk_sys / (8 * baud)`），证明 `48000` baud（`20.833 µs/bit`）与 `115200` baud（`8.681 µs/bit`）波特率误差均 `<= 0.05%`（拒绝整数截断导致的超差）。
    - 审计 PIO 汇编程序仅通过 `pindirs` 方向切换实现开漏驱动（`pins_init_level == 0`，严禁 `out pins` / `set pins, 1` 推挽拉高），并强制审计 CMake `-DOPEN_DRAIN=1` 编译定义。
  - **TX<->RX 8x 过采样台架回环与只读 BootROM 握手仿真（`simulate_uart_loopback_and_handshake`）**：
    - 逐位验证起始位、8 数据位、奇偶校验/停止位、起始位毛刺（glitch）拦截、帧错误（framing error）拦截，以及只读 `UB` CRC32 BootROM 握手与 `0xFFFF0000` 读回显（`persistent_emmc_writes_authorized = False` 硬件锁死）。
  - **CLI 与双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-rp2040-fixture [--clean-room] [--json] [--out ...]`，并在 [`tests/test_rp2040_multiport_fixture_selftest.py`](tests/test_rp2040_multiport_fixture_selftest.py) 新增 **30 项快速单元测试**（`< 0.2s`），在本地供体（`os.O_RDONLY`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下均 100% 通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-rp2040-fixture --clean-room --json
```

## Phase 66 — `init2` SD-Card Sentinel Escape Shell, CXD90057 Watchdog Boot-Loop Breaker & `p1` FAT12/FAT16 Chain Integrity Verifier

- **[`init2_escape_and_watchdog_simulator.py`](fx3_recovery/init2_escape_and_watchdog_simulator.py)**：提供面向 FX3 (`0x91030080`) Stage-B 恢复链路的三重确定性安全与文件一致性校验：
  - **零硬件 SD/CFexpress 哨兵 Fail-Open 逃生沙箱（`render_init2_escape_wrapper_script` / `run_init2_escape_drill` / `run_all_init2_escape_drills`）**：在 `tempfile.TemporaryDirectory` 隔离沙箱内实际执行纯 POSIX `/bin/sh` Stage-B `init2` 守卫脚本，在任何 `cpio` 解包或 `mount --bind` 发生**之前**验证 4 条 fail-open 逃生机制：
    1. Slot A / Slot B 外置存储卡哨兵文件（`FX3_SAFE_STOCK.FLG` / `DISABLE_STAGE_B.TXT`）→ 零 bind-mount、零 eMMC 写入直接回退原厂 FX3 `v7.02` 启动（`Tier-0` 现场零线缆免拆救援）。
    2. 物理按键组合逃生（`REC+MENU` / `SHUTTER` 启动 GPIO 锁存）→ 跳过 Stage-B 覆盖直接进入原厂 `v7.02`。
    3. Stage-B 载荷 SHA-256 / CPIO `070701` 魔数不一致或截断 → fail-closed 拒绝加载并 fail-open 回退原厂启动。
    4. `procam_app` 崩溃循环断路器（易失 `/tmp/stage_b_crash.cnt` 在 `15s` 窗口内 `>= 3` 次非零退出）→ 自动卸载易失 `tmpfs` bind-mount 并 `exec` 原厂 FX3 `procam_app`，`0` eMMC 写入。
  - **CXD90057 硬件看门狗 (`WDT`) 与 `Tier-0..Tier-2` 状态机校验器（`simulate_cxd90057_watchdog_scenario` / `run_cxd90057_watchdog_suite`）**：按 `timeout_ms=10000`、`kick_interval_ms=2000` 建模 Stage-B `H1` 正常运行、UI Presenter 挂死、内核 `oops` (`panic_on_oops`)、干净重启（`H1 -> H2` 易失 RAM 清空）及 `Tier-1/2` Multi-Port `p1` 实验指针回滚，证明 `0` 持久 eMMC 变更时仅靠 `WDT` 复位即可还原 `H0 == H2` 原厂启动。
  - **纯 Python `p1` FAT12/FAT16 簇链与 `8.3` 原子目录项交换审计器（`audit_p1_fat_filesystem` / `simulate_atomic_83_dir_swap`）**：兼容 [`fx3_recovery/fat.py`](fx3_recovery/fat.py)（`FatP1`），校验 BPB 几何、`FAT1 == FAT2` 镜像一致性、零簇链环路（Floyd 判环 + 访问集合）、零交叉链接簇、零孤立已分配簇、合法 `8.3`/LFN 校验和，并在纯内存中执行 `INIT2.SH` ↔ `INIT2BAK.SH` 32 字节目录项指针原子交换与逐字节逆向回滚（`physical_writes == 0`、`persistent_emmc_writes_authorized == False`、`persistent_write_release == False`）。
  - **CLI 与双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-init2-escape [--clean-room] [--json] [--out ...]` 并导出全部公开符号；[`tests/test_init2_escape_and_watchdog_simulator.py`](tests/test_init2_escape_and_watchdog_simulator.py) 新增 **34 项双模式单元测试**，在本地供体（`os.O_RDONLY`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下均 100% 通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-init2-escape --clean-room --json
```

## Phase 72 — Tier-0 Backup `GF(256)` Parity Bit-Rot Healer, Short-Read/Blank-Flash Detector & Cross-Body Anti-Transplant Lock

- **[`tier0_backup_parity_and_manifest_guard.py`](fx3_recovery/tier0_backup_parity_and_manifest_guard.py)**：面向 FX3（`0x91030080`）`Tier-0` 宿主机离线备份包提供三大防损毁与防跨机移植门禁：
  - **11 分区 `Tier-0` 截断、空读（全 `0x00`/全 `0xFF`）与 A/B 槽位对称性校验（`validate_tier0_partition` / `validate_tier0_backup_bundle`）**：校验 `nbl_a`、`nbl_b`、`uboot_a`、`uboot_b`、`boot_a`、`boot_b`、`p1_vfat`、`bk4_nvram`、`wbi2_hibdrv`、`cnflasha_spacc`、`c2pa_rq_lic` 全 11 个关键分区的 `dd` 短读/头声明越界截断（`TRUNCATED_PARTITION_DUMP`）、未初始化/擦除总线读出（`ALL_ZERO_BLANK_READ` / `ALL_FF_ERASED_FLASH_READ` / `DEGENERATE_BYTE_ENTROPY`）、无 Sony 私钥依赖的结构化魔数（`ELF`/`FDT`/`uImage`/`ANDROID!`/`ARM64`、`FAT12/16 0x55AA`、`BK4\0`、`WBI2` XOR、`cnflasha` 高熵、`RQLC`/`C2PA`/`jumb`），以及 `(nbl_a, nbl_b)` / `(uboot_a, uboot_b)` / `(boot_a, boot_b)` A/B 对称性（`AB_SLOT_ASYMMETRY_DETECTED`）。
  - **纯 Python `GF(2^8)`（`0x11d` 本原多项式）双校验（`P + Q` RAID-6）位翻转自愈引擎（`encode_gf256_pq_parity` / `heal_gf256_pq_shards` / `heal_tier0_backup_bundle`）**：基于 `exp`/`log`/`inv` 与 `bytes.translate` 查表实现 `P = XOR(D_i)`、`Q = XOR(g^i * D_i)` 条带编码、单分区静默位翻转纯伴随式定位（`S1 / S0 == g^x`）以及任意 1～2 个分区擦除/静默位翻转的 100% 逐比特无损自愈（`reconstructed_sha256 == original_sha256`）；当同时丢失或损坏 `>= 3` 个分片时严格 fail-closed（`UNRECOVERABLE_QUORUM_LOSS`）。
  - **单机身硬件身份锁 / 跨机身防移植防火墙（`compute_body_identity_binding_sha256` / `build_tier0_backup_manifest` / `verify_cross_body_anti_transplant`）**：将每份 `tier0_backup_manifest_v1` 密码学绑定至由 `(camera_model, body_serial_hash, cnflasha_calibration_sha256, c2pa_rq_lic_sha256)` 派生的 `body_identity_binding_sha256`，强拦截将 `Body-A` 校准/C2PA 许可（`cnflasha` / `RQ_LIC.DAT`）误配至 `Body-B` 的操作（`CROSS_BODY_TRANSPLANT_FORBIDDEN`），硬锁定 `persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`physical_device_writes = 0`。
  - **CLI 与 32 项双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-tier0-backup [--clean-room] [--json] [--out ...]` 并导出全部公开符号；[`tests/test_tier0_backup_parity_and_manifest_guard.py`](tests/test_tier0_backup_parity_and_manifest_guard.py) 在本地供体（`os.O_RDONLY` 验证 `2.05/nflasha1` 与 `nflasha5.img`）及 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下均 100% 通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-tier0-backup --clean-room --json
```

## Phase 79 — `CXD90057` OTP/RPMB Anti-Rollback Monotonic Epoch Verifier, Bootloader Downgrade Brick Firewall & BYOF Donor Compatibility Matrix

- **[`firmware_updata_and_antirollback_guard.py`](fx3_recovery/firmware_updata_and_antirollback_guard.py)**：面向 FX3（`0x91030080` / `ALCIN_UUD`）与 FX6（`0x91040086` / `CHAPLIN`）提供三大离线只读防变砖防火墙与零密钥 BYOF 供体审计：
  - **`CXD90057` 安全启动 OTP 熔丝与 eMMC `RPMB` 单调防回滚防火墙（`evaluate_bootchain_transition` / `evaluate_stage_b_volatile_ram_overlay`）**：
    - 建模 `BootROM -> nbl_a/b -> tz/optee -> uboot_a/b -> kernel boot_a/b` 启动链单调纪元锁，显式阻断向已被 Sony `v7.00`/`v7.02` 拉高 OTP/`RPMB` 计数器的 FX3 机身回刷旧版 `nbl`/`tz`/`uboot`/`boot`/`firmware.updata`（`v1.01..v6.00`）导致的不可逆安全启动变砖（`BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE`）。
    - 显式阻断向 FX3 机身跨机型刷入 FX6 `nbl`/`tz`/`uboot`/`WBI2`/`cpapp-b.bin` 导致的 TrustZone 密钥阶梯与分区表变砖（`BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK`）。
    - 结构化证明 Stage-B 易失 RAM 覆盖架构（FX3 `v7.02` 原厂引导链 + FX3 `v7.02` `4.9.337-scel+` 内核 + FX3 `v7.02` 原厂 CP + FX6 `v6.01` 用户态 `/tmp` 绑定挂载）严格满足 `otp_fuse_touches == 0`、`rpmb_counter_increments == 0` 与 `antirollback_brick_risk == "ZERO_USERSPACE_RAM_ONLY"`。
  - **零密钥 BYOF 供体版本与结构兼容性矩阵（`classify_byof_version_pair` / `build_byof_compatibility_matrix` / `validate_byof_donor_tree`）**：
    - 严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 有界读取本地供体（内核 `4.9.337-scel+` 横幅、`GLIBC_2.17` / `CXXABI_1.3..1.3.10` ELF64 ABI、`WBI2` 节计数 `1399` vs `1197`、`libInfra*` / `cxd90057.dtb` 标记——零专有密钥），并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换确定性净室合成夹具。
    - 覆盖 `(FX3 v7.00/v7.01/v7.02) <-> (FX6 v5.02/v6.00/v6.01)` 全矩阵：`FX3 v7.02 + FX6 v6.01 -> TIER_A_GOLD_VERIFIED`，`v7.00/v7.01` 或 `v6.00 -> TIER_B_CONDITIONALLY_COMPATIBLE`（需重定位），缺失 Big6 的 `v5.02` 与 ABI 不匹配组合 -> 明确拒绝并给出可执行修复建议。
    - 在 Stage-B `cpio` 打包前拦截损坏或不完整的用户解包目录（`MISSING_REQUIRED_DONOR_MEMBER`、`WRONG_ISA_OR_ENDIANNESS`、`TRUNCATED_ELF_LOAD_SEGMENT`、`KERNEL_VERSION_MISMATCH`、`WBI2_SECTION_COUNT_MISMATCH`）。
  - **eMMC `EXT_CSD` 永久写保护熔丝陷阱防火墙（`audit_ext_csd_write_protect` / `audit_mmc_wp_command_or_write`）**：
    - 审计 `EXT_CSD[173]` `B_PERM_WP_EN`（`0x04`）与 `EXT_CSD[171]` `US_PERM_WP_EN`（`0x04`）一次性 OTP 永久写保护位，并拦截任何企图触发永久写保护的 `mmc-utils` 命令或清单（`BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP`）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_DEVICE_WRITES = 0`。
  - **CLI 与 34 项双模快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-antirollback-guard [--clean-room] [--json] [--out ...]` 并导出全部公开符号；[`tests/test_firmware_updata_and_antirollback_guard.py`](tests/test_firmware_updata_and_antirollback_guard.py) 在本地供体（`os.O_RDONLY`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下均 `< 0.05s` 通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-antirollback-guard --clean-room --json
```

## Phase 86 — Passive `1.8V` RX-Only `CXD90057` UART Boot-Stage Decoder (`S0..S6`) & Unified `fx3_recovery` 7-Pillar Master Self-Audit

- **[`recovery_master_suite_and_uart_decoder.py`](fx3_recovery/recovery_master_suite_and_uart_decoder.py)**：面向 FX3（`0x91030080`）提供纯离线只读被动串口启动阶段状态机与全包 7 支柱统一自检门禁：
  - **被动 `1.8V` RX-Only 串口安全防火墙与 `S0..S6` 10 签名故障分诊（`audit_passive_rx_tap_safety` / `parse_cxd90057_boot_stages` / `decode_uart_boot_log` / `run_uart_boot_decoder_10_scenario_suite`）**：
    - 强制执行 **RX-Only 被动监听安全约束**（`tx_line_connected == False` 或 `open_drain_tx_idle_1v8 == True`、`passive_tx_bytes_emitted == 0`、`io_voltage_v ∈ [1.65V, 1.98V]`），防止正常启动监控期间误触发 `CXD90057` BootROM `uart_boot`，并对任何主动 TX 注入、推挽 TX 连线、LTC 线冲突或 `3.3V` 过压/帧噪突发 fail-closed 拦截。
    - 解析 `S0_BOOTROM_ENTRY -> S1_NBL_OPTEE_TRUSTZONE -> S2_UBOOT_BOOT_AB -> S3_LINUX_4_9_337_SCEL -> S4_INIT2_SENTINEL_CHECK -> S5_STAGE_B_TMPFS_MOUNT -> S6_ICX1295_BIG6_READY` 全部 7 个确定性启动阶段，并精确分诊 10 类启动/运行态结局与零 eMMC 写入最小恢复动作（`HEALTHY_STAGE_B_LIVE`、`CLEAN_SD_SENTINEL_STOCK_ESCAPE`、`CLEAN_HASH_FAILOPEN_STOCK_BOOT`、`NO_EMMC_FLASH_NEEDED`、`TIER0_CRASH_BREAKER_RECOVERED`、`TIER0_COLD_REBOOT_WIPES_TMPFS`、`NEVER_CROSS_FLASH_FX6_WBI2`、`TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK`、`CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN`、`DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN`）。
  - **统一 `fx3_recovery` 7 支柱主自检套件（`run_recovery_master_suite`）**：
    - 在 `< 1.0s` 内并发核验并聚合全部 7 大恢复支柱（支持 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 双模式）：`macos_usb_transport_guard`、`rp2040_multiport_fixture_selftest`（`camera_connected == False`）、`init2_escape_and_watchdog_simulator`（`7/7` 逃生 + `5/5` WDT）、`tier0_backup_parity_and_manifest_guard`（`GF(256)` P+Q 自愈 + 跨机防移植锁）、`firmware_updata_and_antirollback_guard`（`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`EXT_CSD` 永久写保护阻断）、`unbrick_ladder_and_capsule_verifier`（`12/12` 阶梯 + VFAT 胶囊）以及被动 `S0..S6` 10 场景串口解码器（`passive_tx_bytes_emitted == 0`）。
    - 输出确定性 `recovery_master_sha256`，并硬锁定 `persistent_emmc_writes_authorized = False` 与 `persistent_write_release = False`。
  - **CLI 与 34 项双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-all-recovery [--clean-room] [--json] [--out ...]` 并导出全部公开符号；[`tests/test_recovery_master_suite_and_uart_decoder.py`](tests/test_recovery_master_suite_and_uart_decoder.py) 在本地供体（`os.O_RDONLY`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下均在 `< 0.5s` 内通过。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --clean-room --json
```

## Phase 94 — `CXD90057` eMMC Primary/Backup GPT & Sony Sub-Partition Header Healer, RPMB HMAC-SHA256 Monotonic Write-Counter Replay Guard & Offline SD-Rescue Bundle Verifier

- **[`gpt_rpmb_and_rescue_bundle_verifier.py`](fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py)**：面向 FX3（`0x91030080` / `ALCIN_UUD`）`CXD90057` eMMC 恢复链路提供三大只读 RAM-only 防变砖支柱（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`RPMB_WRITES_EMITTED = 0`，本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 净室回退）：
  - **支柱 1 — Primary/Backup GPT（LBA 1 vs Last LBA）IEEE 802.3 CRC32 与 15 分区几何重建器（`build_gpt_pair_bytes` / `verify_gpt_copy` / `heal_gpt_pair_ram_only`）**：
    - 建模 `CXD90057` FX3 15 分区布局（`p1` FAT boot、`p2..p15` kernel/rootfs/app/calibration/userdata/`cnflasha`，`FX3_LENS_CAL_START_LBA = 0x0031C000`），覆盖 92 字节 `EFI PART` 头 CRC32 与 128 项分区表数组 CRC32、4 KiB（8-LBA）边界对齐及 Sony Sector 0（`'8246' '2.00'`）交叉验证。
    - 证明在纯 RAM 中确定性重建损坏的 Primary GPT <- Backup GPT（以及 Backup GPT <- Primary GPT），并对重叠 LBA 区间（`ERR_GPT_PARTITION_OVERLAP`）、非 4 KiB 对齐（`ERR_GPT_MISALIGNED_4K`）、双副本同毁（`ERR_GPT_BOTH_COPIES_CORRUPTED`）及跨机型 FX6 分区几何移植（`ERR_CROSS_SKU_FX6_GPT_TRANSPLANT`，`0x00312000`）严格 fail-closed 拦截。
  - **支柱 2 — eMMC RPMB（JEDEC eMMC 5.1 512 字节帧）HMAC-SHA256 单调写计数器与防重放沙箱（`build_rpmb_frame` / `parse_rpmb_frame` / `RpmbSandboxController` / `prove_stage_b_zero_rpmb_writes`）**：
    - 仅使用公开合成测试密钥（`SYNTHETIC_RPMB_TEST_KEY`，绝不嵌入任何专有密钥）建模 512 字节 RPMB 帧（196B 填充 + 32B MAC + 284B 载荷、16B nonce、4B 大端 `write_counter`、2B `address`/`block_count`/`result`/`req_resp`）。
    - 证明 fail-closed 拒绝旧写计数器重放（`RPMB_RESULT_COUNTER_FAILURE = 0x0003`）、nonce 不匹配（`ERR_RPMB_NONCE_MISMATCH`）、MAC 伪造（`RPMB_RESULT_AUTH_FAILURE = 0x0002`）及接近 `0xFFFFFFFF` 耗尽拦截（`RPMB_RESULT_COUNTER_EXPIRED = 0x0080`），同时证明 Stage-B RAM/SD 覆盖启动需 **0 次**物理 RPMB 写入（`rpmb_writes_emitted == 0`）。
  - **支柱 3 — 离线气隙 SD-Rescue 急救包清单与双人复核验证器（`build_synthetic_sd_rescue_bundle` / `verify_sd_rescue_bundle`）**：
    - 在允许任何 Stage-B 演练前，核验 `FX3_SAFE_STOCK.FLG` 哨兵、`p1..p15` 全量 SHA-256 清单（拦截缺失/截断/全空读出）、基于 [`tier0_backup_parity_and_manifest_guard.py`](fx3_recovery/tier0_backup_parity_and_manifest_guard.py) 的 `GF(256)` P+Q RAID-6 校验分片与单分片擦除自愈演练、机身序列号绑定（`build_body_hardware_identity`）以及不同双操作员独立摘要复核（`TwoManAttestation`）。
  - **CLI 与 36 项双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-gpt-rpmb-bundle [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94`（Pillar 8），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部公开符号；[`tests/test_gpt_rpmb_and_rescue_bundle_verifier.py`](tests/test_gpt_rpmb_and_rescue_bundle_verifier.py) 包含 **36 项双模式快速单元测试**（`< 0.4s`）。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-gpt-rpmb-bundle --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --clean-room --json
```

## Phase 101 — `CXD90057` `init2` SVR4 `newc` `cpio` RAM-Disk Overlay Path/Symlink/Device-Node Firewall, JEDEC eMMC 5.1 `EXT_CSD [267..269]` Pre-EOL & Life-Time Health Auditor & 9-Pillar Master Suite Integration

- **[`ramdisk_overlay_and_emmc_health_verifier.py`](fx3_recovery/ramdisk_overlay_and_emmc_health_verifier.py)**：面向 FX3（`0x91030080` / `ALCIN_UUD`）与 FX6（`CXD90057`）Stage-B 易失 RAM/SD 叠加启动提供三大只读安全门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`，本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **支柱 1 — SVR4 Portable `'070701'` `newc` `cpio` RAM-Disk 叠加结构与安全防火墙（`build_cpio_newc` / `parse_cpio_newc` / `audit_cpio_ramdisk_overlay` / `build_synthetic_stage_b_cpio_overlay`）**：
    - 纯 Python 实现 SVR4 `'070701'` `newc` `cpio` 解析与校验器（110 字节 ASCII hex 头、4 字节 `(110 + namesize)` 文件名对齐、4 字节载荷对齐、`TRAILER!!!` 哨兵且 `filesize == 0` 校验、`mode`/`rdev`/`uid`/`gid`/`filesize` 校验）。
    - 对 `../` 路径穿越、绝对路径、规范化重复路径、逃逸至 `/dev/mmcblk0*`/`/dev/nflasha*` 或根目录之外的符号链接、任何 `S_IFBLK` 原始块设备节点、未授权 `S_IFCHR` 字符设备节点（含 `rdevmajor == 179/252` 及 `rdevmajor == 1, rdevminor in (1, 2)` 原始内存别名）、白名单外 `S_ISUID`/`S_ISGID` 二进制及截断归档实现 100% fail-closed 拦截。
  - **支柱 2 — JEDEC eMMC 5.1 `EXT_CSD [267..269]` Pre-EOL 与寿命评估只读健康审计器（`build_synthetic_emmc_ext_csd` / `audit_emmc_ext_csd_health`）**：
    - 解析 512 字节 `EXT_CSD` 寄存器：`PRE_EOL_INFO [267]`（`0x01` Normal、`0x02` Warning 80% 保留块消耗、`0x03` Urgent 90% 消耗）、`DEVICE_LIFE_TIME_EST_TYP_A [268]`（SLC）与 `TYP_B [269]`（MLC，`0x01..0x0A = 0%..100%`，`0x0B` 超出最大估计寿命），以及 `PARTITION_CONFIG [179]`（`BOOT_ACK = 1`、`BOOT_PARTITION_ENABLE = 1`、`PARTITION_ACCESS = 0` 出厂 `0x48` 校验，确保启动分区指针未被改写）。
    - 在任何 Stage-B 演练前，一旦检测到 `PRE_EOL_INFO >= 0x02`、`LIFE_TIME >= 0x09`（>80% 磨损）或启动分区指针偏离出厂配置，立即 fail-closed 阻断演练并强制要求先做只读 Tier-0 全量备份留存（`tier0_preservation_mandatory = True`）。
  - **支柱 3 — RAM-Only `tmpfs` / `overlayfs` `upperdir` 隔离证明（`build_synthetic_safe_stage_b_mount_table` / `audit_ramdisk_overlay_mount_table`）**：
    - 解析 Linux `/proc/mounts` / `fstab` 挂载表，通过最长挂载点前缀匹配证明所有 `overlay`/`overlayfs` 的 `upperdir` 与 `workdir` 均严格驻留于易失 `tmpfs`（RAM）且互不重叠，同时证明所有 `/dev/mmcblk0*`、`/dev/nflasha*` 与 `/dev/cnflasha*` 条目均处于未挂载或 `ro,noatime` 只读状态，零 `rw` 块设备挂载。
  - **CLI 与 36 项双模式快速单元测试**：在 [`fx3_recovery/__main__.py`](fx3_recovery/__main__.py) 注册 `verify-ramdisk-emmc-health [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase101`（Pillar 9，与 `--with-phase94` 组合构成 9/9 支柱总检，同时保持既有默认 `7/7` 行为完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部公开符号；[`tests/test_ramdisk_overlay_and_emmc_health_verifier.py`](tests/test_ramdisk_overlay_and_emmc_health_verifier.py) 包含 **36 项双模式快速单元测试**。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-ramdisk-emmc-health --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --clean-room --json
```

## Phase 106 — `CXD90057` Flattened Device-Tree (`FDT 0xd00dfeed` v17) `/chosen/bootargs` 只读 Rootfs 与 Init 路径防火墙、ARM64 内核 `Image`（`0x644d5241`）魔数校验器及 10 支柱总检集成

- **[`fdt_bootargs_and_kernel_verifier.py`](fx3_recovery/fdt_bootargs_and_kernel_verifier.py)**：面向 FX3（`0x91030080` / `ALCIN_UUD`）`CXD90057` Stage-B 恢复门禁提供三大只读 RAM-only 安全验证支柱（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`，本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室合成回退）：
  - **支柱 1 — 纯 Python IEEE 1275 / Devicetree v17（`0xd00dfeed`）二进制解析器与 `/chosen/bootargs` 防火墙（`build_synthetic_fdt_blob` / `parse_fdt_blob` / `audit_fdt_chosen_bootargs`）**：
    - 解析 40 字节大端 `fdt_header`、8 字节对齐且 `(0, 0)` 终结的 `mem_rsvmap`、`FDT_BEGIN_NODE (1)` / `FDT_END_NODE (2)` / `FDT_PROP (3)` / `FDT_NOP (4)` / `FDT_END (9)` 令牌流，严格校验 `off_dt_struct` / `off_dt_strings` 边界、重叠区域、`nameoff` 字符串越界、零填充对齐与非闭节点（测试夹具均在纯内存中合成，绝不提交 `.dtb` 二进制文件）。
    - 审计 `/chosen/bootargs` 与 `/chosen/linux,initrd-start..end`（4B/8B 边界校验）：
      * 对 `/dev/mmcblk0p*` / `/dev/nflasha*` / `/dev/cnflasha*` eMMC rootfs 传入 `rw`、缺少 `ro` 或缺少 `rootwait` 时 fail-closed 拦截；
      * 当 `init=` / `rdinit=` 指向白名单（`/sbin/init`、`/init`、`/sbin/init2` 及 Stage-B 易失 RAM 包装器）之外路径时 fail-closed 拦截；
      * 拦截任何企图重分区的 `mtdparts=` / `blkdevparts=` / `mmcparts=` 参数，并严禁 `nowatchdog` 等关闭 `CXD90057` 硬件看门狗的启动参数。
  - **支柱 2 — ARM64 Linux 内核 `Image`（`0x644d5241` `'ARM\x64'` @ `0x38`）头部与跨机型防火墙（`build_synthetic_arm64_kernel_image` / `audit_arm64_kernel_image`）**：
    - 解析 64 字节 ARM64 `Image` 头部（`code0`、`code1`、`text_offset = 0x80000`、`image_size = 0x6af000`、`flags = 0xa` LE + 4K 页 + 2MB 对齐、`magic == 0x644d5241`），核验真机 FX3 `vmlinux.bin`（`6,610,952` 字节，`4.9.337-scel+`，`dic-build-scm-u20-028`）并 fail-closed 拒绝 FX6 跨机型内核移植（`dic-build-scm-u24-002` / `Sony CE Linux 14.0.2.0`）、大端/非 4K 页标志或截断镜像。
  - **支柱 3 — CLI 与 10 支柱总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-fdt-bootargs [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106`（构成 **10/10** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 106 公开符号（采用 `FDT_MAGIC_U32` 与 `ARM64_IMAGE_MAGIC_U32` 避免覆盖既有 `tier0` bytes 常量）；[`tests/test_fdt_bootargs_and_kernel_verifier.py`](tests/test_fdt_bootargs_and_kernel_verifier.py) 提供 **36 项快速双模式单元测试**。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-fdt-bootargs --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --clean-room --json
```

## Phase 113 — `CXD90057` / `CXD90058` 双槽 A/B 一致性校验、官方 `BODYDATA.DAT` / USB-OTA 断电半刷取证分诊与 11 支柱总检

- **[`ab_bank_and_interrupted_ota_verifier.py`](fx3_recovery/ab_bank_and_interrupted_ota_verifier.py)**：面向 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，AP `CXD90057` + CP `CXD90058`）提供三大只读 RAM-only 恢复安全验证支柱（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`，本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_ab_bank_and_ota_donors_readonly`）**：只读核验 FX3 `2.05/nflasha1` SquashFS（`/usr/bin/sdfileinput.elf` `BODYDATA.DAT`、`/usr/bin/UdtrMain.sh` `/setting/updater/uincomp` / `mode*`、`/usr/bin/common.src` `ERROR_UINCOMP=54`、`/usr/kmod/usb_buspwr.ko` `BATTERY_STATE_EXIST`）、`udtrbody.squashfs`（`/bin/nor_loader_writer.sh` `cpapp-b.bin` / `loader_nor.bin` / `MIS.bin`）、FX3 与 FX6 `cpapp-b.bin`（`15,980,568` vs `17,952,816` 字节，严禁跨机型刷写）及 `fx3-7.02-BODYDATA.DAT` 有界 `4096 B` UFU 头部（`\x89UFU\r\n\x1a\n`）。
  - **支柱 1 — `CXD90057` / `CXD90058` 双槽 A/B（Bank-A / Bank-B）AP+CP 同步 Epoch 与半写入检测器（`classify_bank_slot_health` / `audit_dual_bank_ap_cp_consistency`）**：
    - 精确建模 4 类双槽健康状态：`ACTIVE_VERIFIED`、`PENDING_TRIAL`、`TORN_PARTIAL_WRITE`、`ROLLBACK_FENCED`。
    - 在纯 RAM 中完成 AP 与 CP 双槽 CRC/写入字节数/Epoch 审计，fail-closed 拦截 AP 启动 Bank-B `7.02` 而 CP 滞留在半写入 Bank-A `2.05` / 坏 CRC 所导致的 AP<->CP IPC 协议死锁（琥珀/红灯闪烁变砖）、跨 SKU 移植与未配置完整回退槽的 `PENDING_TRIAL`。
  - **支柱 2 — 官方 `BODYDATA.DAT` / Creators'-App OTA 断电半刷取证分诊与预检门禁（`audit_official_ota_preflight` / `triage_interrupted_ota_brick` / `run_interrupted_ota_6_scenario_triage`）**：
    - 强制校验 Sony 官方升级 `>= 51%` 电量门禁（`SONY_FW_UPDATE_MIN_BATTERY_PCT = 51`）、`0x91030080` 机型与 `NTSC`/`PAL` 同区校验、UFU 魔数与传输介质稳定性。
    - 精确分诊 6 类真实相机维修/升级场景（`U1_BATTERY_PULLED_DURING_CP_FLASH`、`U2_SD_CARD_READ_CRC_MID_UPDATA`、`U3_USB_CABLE_YANKED_LEGACY_UPDATER`、`U4_CROSS_REGION_NTSC_PAL_MISMATCH`、`U5_STAGE_B_CLEAN_SD_EJECT_ZERO_BRICK`、`U6_INTACT_DUAL_BANK_HEALTHY`），并映射到最小无损恢复动作（SD `FX3_SAFE_STOCK.FLG` 秒级回退 vs 被动 `1.8V` UART 诊断 vs Tier-0 只读转储）。
    - 显式证明 `U5` Stage-B 易失 RAM/SD 用户态叠加即使突发拔电池/退卡也具有**零闪存中断变砖面**（`emmc_bank_transitions == 0`、`updata_flags_touched == False`、`flash_interruption_brick_surface == False`）。
  - **支柱 3 — CLI 与 11 支柱总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-ab-bank-triage [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113`（构成 **11/11** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 113 公开符号；[`tests/test_ab_bank_and_interrupted_ota_verifier.py`](tests/test_ab_bank_and_interrupted_ota_verifier.py) 提供快速双模式单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-ab-bank-triage --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --clean-room --json
```

## Phase 119 — SquashFS 4.0（`hsqs` `0x73717368`）分区超级块与表边界校验器、Sony Warp-Boot `hibdrv`（`WBI2` 休眠快照）过期恢复中毒分诊及易失 `noresume` RAM 启动旁路验证器与 12 支柱总检

- **[`squashfs_and_hibdrv_wbi_verifier.py`](fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py)**：面向 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057` Linux `4.9.337-scel+`）提供两大只读取证与防变砖支柱并接入 12 支柱总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`WBI_PARTITION_WRITES = 0`，本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_squashfs_and_wbi_donors_readonly`）**：只读核验 FX3 `2.05/nflasha1` `/boot/initrd.img` SquashFS 4.0（`9,097,216 B`）、FX3 `udtrbody.squashfs`（`1,253,376 B`）、FX6 `updater.img`（`1,253,376 B`）、有界 512B+节表 `O_RDONLY` 读取 FX3 `nflasha5.img`（`1399` 节 `WBI2`）与 FX6 `nflasha5`（`1197` 节 `WBI2`），以及 FX3/FX6 `vmlinux.bin` 内核 `UTS_VERSION` 与 `WBI:invalid param`/`hibernate` 符号锚点。
  - **支柱 A — SquashFS 4.0（`hsqs` 小端魔数 `0x73717368`）超级块与表边界校验器（`verify_squashfs_partition_bytes` / `build_synthetic_squashfs_superblock`）**：
    - 纯 Python 解析 96 字节 `<5I6H8Q` 超级块，校验 `s_magic == 0x73717368`（fail-closed 拦截大端 `sqsh` `0x68737173` 与全 `0x00`/全 `0xFF` 擦除态）、`s_major == 4, s_minor == 0`、`block_size` 2 的幂（`4 KiB..1 MiB` 且 `block_size == 1 << block_log`）、`compression_id` ∈ `{1:GZIP, 2:LZMA, 3:LZO, 4:XZ, 5:LZ4, 6:ZSTD}`、`no_ids >= 1`、`96 < bytes_used <= partition_size`、严格单调表边界（`inode_table_start < directory_table_start <= fragment <= export <= id <= xattr <= bytes_used`）与 `root_inode` 偏移合法性，离线捕获截断 `rootfs`/`app` 刷写引发的 `/sbin/init2` `SIGBUS` 与 `VFS: Unable to mount root fs` 循环崩溃。
  - **支柱 B — Sony `Warp-Boot` / `hibdrv`（`WBI2`）过期恢复中毒分诊与易失 `noresume` RAM 旁路验证器（`parse_wbi2_header_and_table` / `triage_wbi_hibdrv_snapshot` / `verify_ephemeral_noresume_bootargs_bypass` / `audit_wbi_partition_write_attempt` / `run_wbi_hibdrv_6_scenario_triage`）**：
    - 建模 88B/512B `WBI2` 休眠头与 64B 节表（`0x0f0f0f0f` 元数据 XOR 校验和、4K 页对齐、`resume_vector` 覆盖与重叠区间检测），精准识别三大中毒风险：`WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH`、`WBI_KERNEL_ABI_FINGERPRINT_MISMATCH` 与 `WBI_EPHEMERAL_NORESUME_REQUIRED`。
    - 验证修复动作严格使用 RAM-only `bootargs`（`noresume` / `hibdrv.resume=0`，`ro rootwait` 挂载 eMMC 根文件系统且禁 `rw`/`mtdparts`/`nowatchdog`），并通过 `audit_wbi_partition_write_attempt` 对 `/dev/nflasha5`/`mmcblk0p5` 持久擦写实现 100% fail-closed 拦截（`wbi_partition_writes == 0`）。
  - **支柱 C — CLI 与 12 支柱总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-squashfs-wbi-triage [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119`（构成 **12/12** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 119 公开符号；[`tests/test_squashfs_and_hibdrv_wbi_verifier.py`](tests/test_squashfs_and_hibdrv_wbi_verifier.py) 提供 40 项快速双模式单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-squashfs-wbi-triage --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --clean-room --json
```

## Phase 124 — `CXD90057` Mask-BootROM USB 冷插拔枚举校验器、JEDEC eMMC `BOOT0/BOOT1` 硬件引导分区（`EXT_CSD[179]`/`[177]`/`[173]`）防损坏分诊与 13 支柱恢复总检

- **[`bootrom_usb_and_emmc_bootpart_verifier.py`](fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py)**：面向 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057`）提供两大只读与 RAM-only 防变砖恢复支柱并接入 **13 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`EMMC_PERSISTENT_PROGRAM_COMMANDS = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_bootrom_and_bootpart_donors_readonly`）**：严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检查本地 FX3 `v7.02`（`loader_nor.bin` `101,888 B` SRAM `0xFE049000`、`pformat_config.txt` `awake_memaddr=0xFE040800`、`loader_nor.tar`、`partinf.conf`）与 FX6 `v6.01`（`loader_nor.tar` 内含 `92,448 B` `loader_nor.bin`、`partinf.conf`），验证跨机型 `SBL`/分区配置严格隔离且零原始固件字节输出。
  - **支柱 A — JEDEC `eMMC 5.1` `BOOT0 / BOOT1` 硬件引导分区与 `EXT_CSD` 配置分诊（`parse_ext_csd_boot_config` / `audit_boot_wp_script_or_profile` / `triage_emmc_boot_partitions_and_ext_csd` / `run_emmc_bootpart_6_scenario_triage`）**：
    - 建模 `CXD90057` 一级引导程序（`SBL`/`ipl`/`loader`）驻留的 `4 MiB` `BOOT0` 与冗余 `4 MiB` `BOOT1` 硬件分区，核验 `EXT_CSD[179]`（`PART_CONFIG`）、`EXT_CSD[177]`（`BOOT_BUS_CONDITIONS`）、`EXT_CSD[173]`（`BOOT_WP`）与 `EXT_CSD[226]`（`BOOT_SIZE_MULT == 32`）。
    - fail-closed 检出四大致命风险：`BOOT_PART_DISABLED_DEAD_BOOT_TRAP`（`BOOT_PARTITION_ENABLE == 0x0` 或 `0x7` UDA 误配）、`BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE`（主 `BOOT0` SHA-256/头损坏而冗余 `BOOT1` 完好）、`BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD`（任何配置/脚本试图置位不可逆永久写保护 `EXT_CSD[173]` `B_PERM_WP_EN` `bit 2` 或 `bit 6`）、以及 `PARTITION_ACCESS_NONZERO_LEAK`（`PART_CONFIG[2:0]` 读取后未归 `0x0` 导致用户区失活），并在 `BOOT0/BOOT1` 双毁时升级分诊至 Mask-BootROM 救援。
  - **支柱 B — `CXD90057` Mask-BootROM USB 冷插拔枚举与 `RAM_LOAD_ONLY` 沙盒校验（`verify_bootrom_usb_coldplug_and_ram_sandbox` / `run_bootrom_usb_5_scenario_sandbox`）**：
    - 建模 `CXD90057` Mask-BootROM 回退枚举（`USB VID 0x054C` PID `0x0C90`/`0x0336`/`0x0DA1` 冷插拔描述符与 Bulk IN/OUT 端点握手），强制校验任何恢复载荷暂存仅允许面向 CXD90057 SRAM（`0xFE040000..0xFE100000`）/DRAM（`0x40000000..0xC0000000`）原地执行（`RAM_LOAD_ONLY`），对跨机型 FX6 载荷、非 Sony VID 与任何持久 `eMMC/NOR/OTP` 刷写指令（`emmc_program`/`flash_boot0`/`mmc_write`/`cmd42`/`burn_otp`）实现 100% 阻断（`emmc_persistent_program_commands == 0`）。
  - **支柱 C — CLI 与 13 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-bootrom-bootpart [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124`（构成 **13/13** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 124 公开符号；[`tests/test_bootrom_usb_and_emmc_bootpart_verifier.py`](tests/test_bootrom_usb_and_emmc_bootpart_verifier.py) 提供 **40 项快速双模单元测试**。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-bootrom-bootpart --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --clean-room --json
```

## Phase 126 — 单机身出厂校准（`nvs` / `cnflasha` / `adj`）三副本校验与跨机身投毒防火墙、`IMX510` 坏点/双原生 ISO 列 ADC 与 5 轴 `IBIS` 霍尔零点/陀螺仪温漂表校验器，及 14 支柱恢复总检

- **[`factory_cal_ibis_defectpixel_and_nvs_verifier.py`](fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py)**：面向 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057` / `CXD90058`）提供两大只读防变砖/防校准中毒支柱并接入 **14 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`FACTORY_CAL_MUTATION_BYTES = 0`、`PRIVATE_KEY_BYTES_READ = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_factory_cal_and_sensor_donors_readonly`）**：严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检查本地 FX3 `v7.02`（`libbackup.so` `14,232 B`、`backup.ko` `144,976 B`、`appFw.so` `79,015,712 B`、按需 `cpapp-b.bin` `15,980,568 B`）与 FX6 `v6.01`（`libbackup.so` `14,232 B`、`appFw.so` `50,520,424 B`、按需 `cpapp-b.bin` `17,952,816 B`）校准/备份/传感器/`IBIS` 符号锚点，验证跨机型摘要严格隔离且零原始固件字节/私钥输出。
  - **支柱 A — 单机身出厂校准分区（`nvs` / `adj` / `cnflasha`）三副本 SHA-256 仲裁与跨机身移植防火墙（`verify_factory_cal_triple_parity_and_firewall` / `audit_cnflasha_key_vault_operation` / `run_factory_cal_6_scenario_firewall`）**：
    - `BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT`：恢复清单 `body_serial_hash` / `board_uid_hash` 或机型 SKU 与目标相机 Tier-0 身份不匹配时 fail-closed 拦截跨机身移植；
    - `BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY`：`nvs` / `adj` / `cnflasha` 任一分区独立一致 SHA-256 副本少于 2/3 时拒绝；
    - `BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION`：严格拦截任何修改 `cnflasha` 或读取原始非对称私钥材质的请求（`private_key_bytes_read == 0`、`factory_cal_mutation_bytes == 0`，`6/6` 场景绿色通过）。
  - **支柱 B — `IMX510` 坏点表（`Base ISO 800 / 12800` 双增益列 ADC）与 5 轴 `IBIS` 霍尔/陀螺仪温漂表校验器（`verify_imx510_and_ibis_cal_tables` / `run_sensor_ibis_cal_6_scenario_suite`）**：
    - 校验 `4264 x 2408` 有效像素阵列内严格行主序单调坏点坐标、有界双增益 `ISO 800 / 12800` 暗电流与列 FPN 偏置（`±32 LSB`）、完整 5 轴 `IBIS`（`pitch` / `yaw` / `roll` / `x` / `y`）霍尔零点中心与限位、`-10°C..+60°C` 覆盖及有限边界内的 `IMU` 陀螺仪温漂多项式与 `CRC32` 篡改校验（`6/6` 场景绿色通过）。
  - **支柱 C — CLI 与 14 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-factory-cal-guard [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126`（构成 **14/14** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 126 公开符号；[`tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py`](tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py) 提供 **40 项快速双模单元测试**。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-factory-cal-guard --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --clean-room --json
```

## Phase 134 — `CXD90057` `IPL / BLoader / ATF BL31 / Kernel` 安全启动信任链信封校验器、`nflasha1..nflasha20` `4 KiB / 512 KiB` 擦除组分区边界重叠防火墙，及 15 支柱恢复总检

- **[`secureboot_chain_and_partition_align_verifier.py`](fx3_recovery/secureboot_chain_and_partition_align_verifier.py)**：面向 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057`）提供两大只读防变砖/防跨界擦写支柱并接入 **15 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`SPACC_KEY_READS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_secureboot_and_partalign_donors_readonly`）**：严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检查本地 FX3 `v7.02`（`loader_nor.bin` `101,888 B`、`partinf.conf` `3,999 B` `LensData @ 0x0031C000`、`vmlinux.bin` `6,610,952 B`）与 FX6 `v6.01`（`loader_nor.tar` 内含 `92,448 B` `loader_nor.bin`、`partinf.conf` `3,990 B` `LensData @ 0x00312000`、`vmlinux.bin` `6,610,952 B`）引导/分区/`SPAcc`/`eFuse`/`OTP` 符号锚点与跨机型边界差异，零原始固件字节或硬件私钥输出。
  - **支柱 A — `CXD90057` `IPL -> BLoader -> ARM Trusted Firmware (BL31) -> Kernel` 安全启动信封与跨机型签名失配防火墙（`verify_cxd90057_secureboot_envelope` / `audit_otp_efuse_and_spacc_operation` / `run_secureboot_envelope_6_scenario_firewall`）**：
    - `BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC`：当面向锁定 SoC 的 eMMC 引导时，任何引导阶段（`IPL` / `BLoader` / `BL31` / `Kernel`）出现摘要篡改、缺失原厂签名信封、分区容量溢出或防回滚代次降级即 fail-closed 拦截（而 Stage-B `QEMU` / 内核后用户态 bind-mount 易失覆盖不修改任何已签名引导阶段，正常放行）；
    - `BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC`：拦截混入 FX6 引导加载器或 `PMIC` 初始化镜像；
    - `BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS`：拦截任何 `eFuse/OTP` 烧断或 `SPAcc` 密钥槽转储请求（`otp_fuse_writes == 0`、`spacc_key_reads == 0`，`6/6` 场景绿色通过）。
  - **支柱 B — `nflasha1..nflasha20` `eMMC` `512 B` LBA / `4 KiB` 页 / `512 KiB` 擦除组边界与邻分区串写防火墙（`LbaIntervalTree` / `find_partition_lba_overlaps` / `verify_partition_map_and_flash_ops` / `run_partition_align_6_scenario_firewall`）**：
    - 通过增强区间树确定性校验分区映射（`erase_group_lba_multiple = 1024` 扇区 = `512 KiB`）与恢复操作：
      - `PARTITION_LBA_OVERLAP_DETECTED`：检测任意两分区之间的 LBA 重叠；
      - `UNALIGNED_ERASE_GROUP_BLEED_HAZARD`：拦截非 `512 KiB` 擦除组对齐（如 `dd seek=1` 差一偏移）或越过 `partition_sector_count` 串写邻近 `nvs`/`cnflasha` 校准分区；
      - `PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED`：拦截对 `BOOT0`、`BOOT1`、`RPMB`、`nvs`、`adj`、`cnflasha` 的写入/擦除请求（`6/6` 场景绿色通过）。
  - **支柱 C — CLI 与 15 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-secureboot-partalign [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134`（构成 **15/15** 支柱总检，同时保持无标志默认 `7/7` 完全兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 134 公开符号；[`tests/test_secureboot_chain_and_partition_align_verifier.py`](tests/test_secureboot_chain_and_partition_align_verifier.py) 提供 **42 项快速双模单元测试**。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-secureboot-partalign --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --clean-room --json
```

## Phase 138 — 真机主线 Part 4：可逆 A7C-II 风格 `/dev/nflasha15`（`ext2` `/usr`）文件级原子安装预演、哈希回滚引擎与 `p1` 一次性救援校验器（16 支柱恢复总检）

- **[`realhw_ext2_installer_and_p1_rescue_verifier.py`](fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py)**：面向物理 `ILME-FX3`（`7.02`，`0x91030080` / `ALCIN_UUD`）真机刷入就绪审计提供三大纯内存、只读供体验证支柱并接入 **16 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_realhw_ext2_and_p1_donors_readonly`）**：严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验 FX3 `7.02` 与 FX6 `6.01` `partinf.conf`、`mount.conf`、`kemco.txt`（`FX3 cfg.uart=1` vs `FX6 cfg.uart=9`）、`nflasha1/boot/loadaddr.txt`、`nflasha15` 有界 `4 KiB` ext2 超级块（FX3 `479,846,400 B` 镜像与 `500 MiB` 槽位 `>= 32 MiB` 余量）及 `im.elf`，零原始固件字节输出。
  - **支柱 A — `EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK`（`parse_ext2_superblock_bytes` / `audit_crypto_block_device_path` / `validate_sd_escape_hatch_wrapper` / `simulate_atomic_ext2_install_and_rollback` / `run_ext2_atomic_installer_6_scenario_suite`）**：
    - 校验 `/dev/nflasha15` `ext2` 超级块（`s_magic == 0xEF53`、`>= 32 MiB` 余量、空闲 inode 检查），强制 `type=5, flag=1` 加密分区经由 `/dev/nflashaN` / `/dev/cnflashaN` 透明加密路由并**硬阻断** `/dev/pnflasha3/8/15/23` 原始明文写入风险（`BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD`）。
    - 强制 SD 卡逃生门哨兵脚本（`if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig "$@"; fi`），并在纯内存交易中完整模拟 `remount rw -> 校验原厂 SHA-256 -> 保存 .orig 备份 -> 写入包装器 -> 全量回读 SHA-256 校验 -> 注入 bit-flip / short-write 时自动从 .orig 100% 逐字节回滚 -> remount ro`（`6/6` 场景全绿）。
  - **支柱 B — `P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD`（`audit_p1_p3_mutual_exclusion` / `audit_p1_oneshot_rescue_proposal` / `run_p1_rescue_and_mutual_exclusion_6_scenario_suite`）**：
    - 强制执行 **p1/p3 黄金互斥律**（严禁在同一事务中同时修改 `p1` `23.94 MiB` 与 `p3` `75 MiB`，确保至少一个可引导分区始终完好）。
    - 核验 `p1:/dat2 == "91030080"` 与 `p1:/dat3` 原封保留、`p1:/boot/loadaddr.txt` 合法、`p1:/boot/kemco.txt` 强制 `cfg.uart=1` & `console=ttyAMA0,460800n8`（硬阻断 FX6 `cfg.uart=9` 串口黑屏），以及 `/sbin/init` 首条可执行语句必须为 `rm -f /setting/updater/mode* && sync`（`6/6` 场景全绿）。
  - **支柱 C — `TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK`（`verify_tier0_backup_precondition` / `run_tier0_precondition_and_lock_4_scenario_suite`）**：
    - 强制要求具备已回读 SHA-256 验证的完整 Tier-0 备份回执（`sector0`、`p1`、`p2`、`p6`、`p12`、`p18`、SPI NOR `ddrtraining.dat`）后才允许演练就绪通过，同时硬锁定 `persistent_emmc_writes_authorized = False`（`4/4` 场景全绿）。
  - **CLI 与 16 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-realhw-ext2-installer [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase138`（构成 **16/16** 支柱总检，同时保持无标志默认 `7/7` 与 `--with-phase134` `15/15` 向后兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 138 公开符号；[`tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py`](tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py) 提供 **44 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-realhw-ext2-installer --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --clean-room --json
```

## Phase 139 — 真机主线 Part 5：主机端 `AdjustControl (0x40)` 流式冷备份客户端、`p6`（`25 MiB`）滑窗回拉与 Fake-IOKit 端到端回归（17 支柱恢复总检）

- **[`realhw_adjustcontrol_streaming_backup_client.py`](fx3_recovery/realhw_adjustcontrol_streaming_backup_client.py)**：严格衔接 Stage-288 `§6` 与 `2026-11-03 §5.2` 冷备份清单，面向真实 `ILME-FX3`（`7.02`，`0x91030080` / `054C:0336`）提供三大净室协议与双路径全机冷备份支柱并接入 **17 支柱**恢复总检门禁（硬锁定 `LIVE_USB_IOKIT_TRANSMIT_ENABLED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PHYSICAL_USB_BYTES_TRANSMITTED = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退）：
  - **供体只读核验（`inspect_adjustcontrol_donors_readonly`）**：严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验 Stage-288 `jiritsu_wire.py`、`fake_jiritsu_camera.py`、`libJit_test.so`（`PT_LOAD 0x1000`）与 FX3 `libJiritsu.so`（`225,200 B`，`PT_LOAD 0x10000`）、`partinf.conf`（`p6 = 25 MiB`、`p3 = 75 MiB`、`p15 = 500 MiB`）及 `pformat_config.txt`，JSON 输出零原始专有固件字节。
  - **支柱 A — `ADJUSTCONTROL_0X40_WIRE_TRANSPORT_AND_PREFLIGHT_ABORT`（`7/7`）**：
    - 精确实现 Stage-288 净室线帧（`SET_FILE_PATH`: `b"\x00" + path + b"\x00"`；`SET_FILE2`: `b"\x00\xff\x00" + payload`；`GET_FILE2`: `b"\x00\xff\x00"`），硬拒绝 selector `2`，严禁 `MODE`/`MOUNT`/`FORMAT`/`START`/`DEBUG`/`FIRMUP` 及 `edisx`/`uc_mkfs` 与 `/tmp/jiritsu/` 外路径穿越。
    - 强制会话前 `/tmp/jbusy` 探针（`GET_FILE2` 必须返回 `0x11` `ENOENT`），遇到 `/tmp/jbusy` 存在、`0x10000011`、`0x10000201`、`0x10000000`、`0x10000004`、`0x1000000F` 或 USB 超时时**立即中止，绝不盲目重发第二次 `SET_FILE2`**（`set_file2_retry_count == 0`）。
  - **支柱 B — `DUAL_PATH_SD_STREAM_AND_P6_SLIDING_WINDOW_COLD_BACKUP`（`6/6`）**：
    - **Path 1（SD/CFexpress ExFAT 直接流式转储）**：将全部 16 项关键资产（`Sector 0` + Tier-0 `p2`/`p6`/`p12`/`p18`/SPI NOR `ddrtraining.dat @ 0x3e210fc` + `loader_nor.bin` + Tier-1 `p1(含dat2/dat3)`/`p3`/`p7`/`p8` + Tier-2 `p5`/`p13`/`p15`/`p23`/`p30`）流式写入 `/mnt/sd/FX3_COLD_BACKUP/` 与 `MANIFEST.SHA256`，仅通过 `GET_FILE2` 回传紧凑 `528 B` `FX3RCPT1` 签名哈希回执（`< 1 KiB` `p6` 占用）。
    - **Path 2（`p6` 受限 `<= 4 MiB` 滑窗 USB 分片回拉）**：无可用 SD 卡时以 `<= 4 MiB` 滑窗分片拉取任意大分区（如 `75 MiB` `p3` 19 片，`peak_p6_bytes <= 4.2 MiB << 25 MiB` `nflasha6` 配额），逐片校验 `[8B "FX3CHK1\0" + u64 offset + u32 length + u32 crc32]`，核实 `libJit.so` 与临时分片均已解链（`p6_residual_files == 0`），并证明重组全量 SHA-256 与源分区逐字节一致。
  - **支柱 C — `FAKE_IOKIT_USB_CAMERA_REGRESSION_AND_PASSIVE_LOCK`（`5/5`）**：
    - 有状态 `FakeIOKitAdjustControlCamera` 建模 Sony `054C:0336` `AdjustControl (0x40)` 端点、`25 MiB` `p6` 配额（`0x1000000F`）、`/tmp/jbusy` 锁定、ELF `DT_HASH (1,1,0,0)` + `PT_LOAD 0x10000`（64 KiB 页对齐）校验及会话后残留文件审计，并硬锁定 `live_usb_iokit_transmit_enabled = False` 与 `persistent_emmc_writes_authorized = False`。
  - **CLI 与 17 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-adjustcontrol-backup-client [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase139`（构成 **17/17** 支柱总检，同时保持无标志默认 `7/7` 与 `--with-phase134`/`--with-phase138` 向后兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 139 公开符号；[`tests/test_realhw_adjustcontrol_streaming_backup_client.py`](tests/test_realhw_adjustcontrol_streaming_backup_client.py) 提供 **46 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-adjustcontrol-backup-client --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139 --clean-room --json
```

## Phase 144 — 真机主线 Part 6：`MSC (054C:0DA1) -> SERVICE (054C:0336)` 独占会话、`op=0xFF` 零挂载 RAM 金丝雀与 Stage-288 §4 (1..6) 加固 ARM64 `libJit.so` 门禁（18 支柱恢复总检）

- **[`realhw_service_usb_session_and_libjit_elf_hardener.py`](fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py)**：严格收口 Stage-285 / Stage-286 / Stage-288 真机主线剩余主机端协议与 ARM64 `libJit.so` ELF64 安全门禁，并接入 **18 支柱**恢复总检门禁（硬锁定 `LIVE_USB_IOKIT_TRANSMIT_ENABLED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`USB_TX_PACKETS_EMITTED = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`；供体严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露回退）：
  - **供体只读核验（`inspect_service_usb_and_libjit_donors_readonly`）**：只读验证 FX3 `7.02` `libJiritsu.so`（`225,200 B`、`PT_LOAD 0x10000`、5 个 `adj_cmd_*`/`cmd_high_capacity_*` 符号）、`libsencore.so`（`377,328 B`、`PT_LOAD 0x10000`、`AdjustControlFunc`/`Inconcurrent::resource_t::lock`/`TransactionStart` 符号）以及可选 Stage-288 `libJit_test.so`（`8,345 B`、`PT_LOAD 0x1000`），并明确标注未加固 `libJit_test.so` 触发的 §4 预加固拒绝项。
  - **支柱 A — `STAGE285_286_SERVICE_USB_AND_OP_FF_RAM_CANARY`（`8/8`）**：
    - 完整建模并校验 9 步会话契约：`MSC (054C:0DA1)` 7 轮握手 -> 同物理端口 `SERVICE (054C:0336)` `USBDeviceOpenSeize` 单航道独占（`SenserThread` `Inconcurrent::resource_t::lock` @ `0xdd00`）-> 7 轮认证到达 Level 2/3（`*0x6aee0`，放行 `flags & 0xe000 == 0x4000`、于 `0xfe48` 拒绝 Level 1）-> `ProductInfoFunc`（`pFunc=0x0010` `read0`：12B 请求 + 12B `version=3, res=1` 响应 + 88B 体）。
    - **强制 Branch-A `op=0xFF` 零挂载 RAM 金丝雀前置门槛**：在放行任何 `op=0x00`（`/dev/nflasha6` `/tmp/jiritsu`）指令之前，强制通过 `SET_FILE2 / GET_FILE2 op=0xFF`（`slot <= 0x11`、`size <= 5 MiB` @ `*0x46bd8`、零 `sys_mount`、零 `dlopen`）含 `0x124` 内联/DMM 分界与 `Phase 1 (TransactionStart) -> Phase 4 (DoExecute) -> Phase 16 (dmm_free)` 往返校验；硬拒绝 `slot > 0x11`、`size > 5 MiB`、并发重叠 `seq`，以及缺失 `STOP (0336:7) -> release (0336:8) -> 054C:0DA1 return (0da1:9)` 收尾序列；附带被动 `ioreg` XML/文本 USB 拓扑干跑解析器（零 IOKit 建连、零 USB 发包）。
  - **支柱 B — `STAGE288_SEC4_HARDENED_ARM64_LIBJIT_ELF_GATE`（`8/8`）**：
    - 净室构造最小 ARM64 `ET_DYN`（`e_machine = 183`、`< 16 KiB`）探针生成器与静态反汇编/Unicorn 行为验证器，强制全部 6 项 Stage-288 §4 P0 安全规则：
      1. `§4.1` 构造器首条系统调用自删 `unlinkat(AT_FDCWD=-100, "/tmp/jiritsu/libJit.so", 0)`（`mov x8, #35; svc #0`）；
      2. `§4.2` 先以 `O_RDONLY | O_CLOEXEC` 打开源设备并核验 `read == 512` 后再打开输出，杜绝 `0 B` 截断歧义；
      3. `§4.3` 输出紧凑 `528 B` 帧（`8B "FX3S0OK\x00"` + `<II(512, crc32_ieee)` + `512 B` Sector 0 `"8246"` / `"2.00"`、`n_partitions == 30`、`p1 == (0x80, 0xbf80)`）；
      4. `§4.4` 检查 `/dev/nflasha`（`newfstatat` `S_ISBLK`）并带 `/proc/partitions` / `/dev/nflasha1` 回退探测与 `16 B` `b"FX3S0ERR" + <ii(stage, errno)` 错误回执；
      5. `§4.6` `PT_LOAD` `p_align = 0x10000`（64 KiB）无重叠 `R|E` 与 `R|W`（无 `W+X`），且 `DT_SYMTAB`、`DT_STRTAB`、`DT_HASH`（`nbucket>=1, nchain>=1`）、`DT_INIT` 严格位于文件与 `PT_LOAD` 边界内（拦截旧 `0x2100 > 0x2099` 越界缺陷）；
      6. 静态系统调用与危险令牌防火墙（拦截 `/dev/nflasha*` / `/dev/cnflasha*` / `/dev/pnflasha*` / `/dev/mtd*` / `/setting` 上的 `O_WRONLY`/`O_RDWR`、块/MTD 上 `write`/`pwrite64`/`ioctl`/`mount`，以及 `edisx` / `uc_mkfs` / `nor_loader_writer`）。
  - **CLI 与 18 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-service-usb-libjit [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase144`（全开启时汇总为 **18/18** 支柱总检，同时保持无标志默认 `7/7` 与 `--with-phase139` `17/17` 向后兼容），[`tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py`](tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py) 提供 **46 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-service-usb-libjit --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139 --with-phase144 --clean-room --json
```

## Phase 151 — 真机主线 Part 7（Pillar 19 / `19/19`）：`/dev/pnflasha*` 原始 ISP 密文 + `/dev/cnflasha*` SPACC 逻辑层 + `/dev/mtd*ro` SPI NOR + `Sector 0` 30 分区双层 Tier-0 冷备份仓库校验器

- **[`realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py`](fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py)**：面向真实物理 `ILME-FX3`（`7.02`、`CXD90057`、`Linux 4.9.337-scel+`）提供两大只读与防混刷隔离支柱并接入 **19 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_DEVICE_WRITES = 0`、`MTD_RW_OPENS_OR_ERASE_IOCTLS = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`；本地供体严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读检查，并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露回退）：
  - **供体只读核验（`inspect_tier0_dual_layer_donors_readonly`）**：只读验证 11 项 FX3 `7.02` 本地供体（`partinf.conf` `3,999 B`、`mount.conf` `1,248 B`、`setup_nflash` `375 B` 含 `rename_nflasha()`、`insmod_drv1` `152 B` 含 `crypt-emmc.ko` / `emmc.ko`、`nor_loader_writer.sh` `9,106 B`、`pformat_config.txt` `1,274 B`、`loader_nor.bin` `101,888 B`、`libsencore.so` `377,328 B`、`im.elf` `40,920 B`、有界 4K 头部 `cpapp-b.bin` `15,980,568 B` 与 `nflasha15.img` `479,846,400 B` `ext2 0xEF53`），JSON 输出零原始专有固件字节。
  - **支柱 A — 16 表面双层 Tier-0 冷备份清单、30 分区 `Sector 0` LBA 几何与跨域还原防火墙（`8/8`）**：
    - 建模全部 16 个强制表面（`Sector 0`、`p1`、`p2`、`p3`、`p5`、`p6`、`p7`、`p8`、`p12`、`p13`、`p15`、`p18`、`p23`、`p30`、`SPI NOR /dev/mtd0ro`、`eMMC EXT_CSD`），逐一标注 `layer_domain`（`RAW_PNFLASHA_ISP` / `SPACC_CNFLASHA_LOGICAL` / `SPI_NOR_MTDRO` / `EMMC_REG_METADATA`）、FX3 `"8246"/"2.00"` 30 分区 `Sector 0` LBA 起始/扇区数与魔数/熵特征（`ext2 0xEF53`、`SquashFS hsqs`、`BK4\0`、`VX8900`、SPACC 密文熵 `>= 7.9 bits/byte`），并检测 FX6 邻区 LBA 偏移。
    - 8 场景跨域防火墙：硬拦截 `SPACC_CNFLASHA_LOGICAL` 镜像配对 `RAW_PNFLASHA_ISP` 目标（及反向错配）、拦截跨机身 `body_serial / cid_sha256` 的 `pnflasha*` 还原（每台相机 SPACC OTP 密钥唯一）、拦截非 `ro` `/dev/mtd*` 路径或 `MEMERASE`/`MEMWRITEOOB` ioctl，并结合双副本（`SD ExFAT` + `Mac Host Vault`）与 GF(256) `P+Q` 纠删码完成位腐败自愈与不可修复拒绝。
  - **支柱 B — `/dev/mtd*ro` SPI NOR 与 `p12/p13/p18/p23/p30` 单机身出厂校准完整性门禁（`6/6`）**：
    - 核验 `/proc/mtd` -> `/dev/mtd0ro..mtdNro` 只读转储纪律（`IPL / BLoader / BL31` 启动包络、`64 KiB` / `4 KiB` 擦除块对齐、零 `O_WRONLY`/`O_RDWR` 与零 `MEMERASE`），并锁定单机身 `p12/p13`（`ID/NVS`）、`p18`（`/lens` `VX8900`）与 `p23/p30`（`Backup.bin` `BK4\0`）双副本 SHA-256 锁与写授权双锁（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`）。
  - **CLI 与 19 支柱恢复总检集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-tier0-dual-layer-vault [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase151`（全开启时汇总为 **19/19** 支柱总检，同时保持无标志默认 `7/7` 与 `--with-phase144` `18/18` 向后兼容），[`tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py`](tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py) 提供 **46 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-tier0-dual-layer-vault --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139 --with-phase144 --with-phase151 --clean-room --json
```

## Phase 155 — 真机主线 Part 8（Pillar 20 / `20/20` 里程碑）：`CXD90057` `1.8V ttyAMA0 460800n8` 被动启动阶段分诊、多 USB `1.8V` 电气防火墙与最后手段硬件 ISP 检查单校验器

- **[`realhw_uart_460800_post_triage_and_isp_guard.py`](fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py)**：闭合真实物理 `Sony ILME-FX3`（`7.02`，`p1:/boot/kemco.txt` `cfg.uart=1 console=ttyAMA0,460800n8`）的被动只读串口诊断与最后手段硬件 ISP 应急核验链路，完成 **20/20 支柱**恢复总检里程碑（硬锁定 `PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`；供体严格通过 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退）：
  - **供体只读核验（`inspect_uart_460800_and_isp_donors_readonly`）**：只读验证 5 项 FX3 `7.02` 本地供体（`kemco.txt` `1,736 B`、`tomco.txt` `710 B`、`init` `735 B`、`libsencore.so` `377,328 B` 及有界 4 KiB 头部 `cpapp-b.bin` `15,980,568 B`），并校验 `p1:/boot/kemco.txt` 诊断模式（`cfg.uart=1` + `console=ttyAMA0,460800n8`，硬拒 FX6 `cfg.uart=9` 与 `console=ttynull`），JSON 输出零原始专有固件字节。
  - **支柱 A — 被动 `1.8V` 只接收 `460800 8N1` 六阶段启动分诊引擎（`8/8`）**：
    - 跨全 6 个启动阶段（`STAGE_0_BOOTROM_SPI_NOR_IPL` -> `STAGE_1_BLOADER_BL31_ATF` -> `STAGE_2_LINUX_4_9_337_SCEL_KERNEL` -> `STAGE_3_SPACC_CNFLASHA15_EXT2_USR` -> `STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER` -> `STAGE_5_STAGEB_APPFW_BIG6_READY`）解析真实/捕获 `ttyAMA0` 启动日志并验证单调递增与时序。
    - 将任意卡死/Panic/EROFS/清单不匹配精准映射至最低影响确定性恢复动作：`EJECT_SD_47US_BYPASS`、`CREATE_STOP_STAGEB_FLAG`、`HOLD_MENU_SHUTTER_POWER`、`P1_LINE1_MODE_CLEAR` 或 `TIER0_VAULT_RESTORE`；遇到乱码/空日志 fail-closed 拒绝盲写。
  - **支柱 B — `1.8V` 逻辑电平与多 USB `VMC-BNCM1` 竞争防火墙（`6/6`）**：
    - 硬拦截 `3.3V` / `5.0V` 串口适配器（致命 `CXD90057` `1.8V` IO 引脚过压烧毁）与欠压探头（`< 1.65V`），强制物理 TX 引脚悬空只接收（`passive_tx_bytes_emitted == 0`），拦截非 `460800 8N1` 波特率/帧格式、H0 期间同时挂载 `VMC-BNCM1`（`680 kOhm` LTC 适配器）/ `LANC`（`100 kOhm`）及多 USB 并发主机竞争。
  - **支柱 C — 最后手段脱机硬件 ISP（`1.8V VCCQ` eMMC + `1.8V` SPI-NOR）应急校验清单（`6/6`）**：
    - 在任何理论台架修复前核验 `1.8V VCCQ` eMMC 与 `1.8V` SPI-NOR 供电轨、SoC `RESET_N` 拉低隔离 + 主电池/USB 断开、飞线长度 `<= 10.0 cm`、`EXT_CSD[179]`（`BOOT_PARTITION_ENABLE`、`BOOT_ACK`、`PARTITION_ACCESS == 0`）、`EXT_CSD[177]`（`BOOT_BUS_CONDITIONS`）、`EXT_CSD[162]`（`RST_n_FUNCTION`，永久阻断 OTP 写入），以及单机身 `CID` 绑定的 `pnflasha*` + `/dev/mtd0ro` 双遍 SHA-256 仓库配对（硬锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`）。
  - **CLI 与 `20/20` 恢复总检里程碑（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-uart-460800-isp-triage [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase155`（全开启时汇总为 **20/20** 支柱总检里程碑，同时保持无标志默认 `7/7` 与 `--with-phase151` `19/19` 向后兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 155 公开符号；[`tests/test_realhw_uart_460800_post_triage_and_isp_guard.py`](tests/test_realhw_uart_460800_post_triage_and_isp_guard.py) 提供 **48 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-uart-460800-isp-triage --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139 --with-phase144 --with-phase151 --with-phase155 --clean-room --json
```

## Phase 160 — 真机主线 Part 9（Pillar 21 / `21/21` 终局闭环）：5 级防变砖恢复升级阶梯、`CXD90057` (`Mira`) Multi-USB `1.8V UART` EL3 (`0xfe020000`) 冷启动防护与官方 `BODYDATA.DAT` (`\x89UFU`) 原厂回刷核验器

- **[`realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py`](fx3_recovery/realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py)**：面向真实物理 `Sony ILME-FX3`（`Ver. 7.02`、Model ID `0x91030080`、SoC `CXD90057` *Mira* + `CXD90058` *Cetus*）收口全部 5 级防变砖恢复升级架构与 `BODYDATA.DAT` / `EL3` 只读安全护栏，完成 **21/21 支柱**恢复总检门禁（硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`；供体严格通过 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 只读检查，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退）：
  - **供体有界只读核验（`inspect_phase160_5tier_donors_readonly`）**：只读验证 6 项 FX3 `7.02` 本地供体（`loader_nor.bin` `101,888 B` 含 AArch64 `VBAR_EL3`、`p1` `/sbin/init` `1,438 B`、`7.02 p3` `/sbin/init` `735 B`、`Backup.bin` `2,229,740 B` `BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`、有界 4 KiB 头部 `cpapp-b.bin` `15,980,568 B`，以及有界 `<= 64 KiB` 首尾扫描官方 `fx3-7.02-BODYDATA.DAT` `811,876,768 B` `\x89UFU\r\n\x1a\n` `DATV=1` / `PROV=1` / `UDID=10` 含 `054C:0DA1` / `FDAT` `1024 B` 对齐 / `DEND`），全套运行 `< 0.05 s`，JSON 输出零原始专有固件字节。
  - **支柱 A — 官方 Sony `BODYDATA.DAT` (`\x89UFU\r\n\x1a\n` `Ver. 7.02`) 原厂 `p1` 回刷前置核验（`8/8`）**：
    - 解析 `DATV` / `PROV` / `UDID` / `FDAT` / `DEND` TLV 封装，核验 `FDAT` `1024 B` 帧（`<HH` 长度与求和校验、`0x8000` 终止帧 + `272 B` IV/RSA-2048 尾签），强制唯一放行 `ILME-FX3` (`0x91030080`)（硬拒绝跨机身 `ILME-FX30` `0x910300a0`、`ILCE-7SM3` `0x91030040`、`ILCE-7M4` `0x91030070`、`ILME-FX6`、`ILME-FX3A`），并强制执行更新前 `p15:/usr` `.orig` `16/16` 净卸载检查、电量 `>= 51%`、同区 `NTSC/PAL` 及防回滚代际检查。
  - **支柱 B — `CXD90057` (`Mira`) 15 针 Multi/Micro-USB `1.8V UART` EL3 (`0xfe020000`) 冷启动防护审计（`6/6`）**：
    - 审计 15 针 Multi/Micro-USB 引脚定义（`Pin 2 GND`、`Pin 7 XRESET_REQ`、`Pin 8 UART_TX`、`Pin 9 UART_RX` `1.8V CMOS`、`Pin 10 AD_JACK_IN`），强制 `1.65V..1.98V` 电平安全窗口（拦截 `3.3V`/`5.0V` 烧毁风险），强制 `Pin 10 AD_JACK_IN` 与 `VMC-BNCM1`（`680 kOhm` LTC）/ `LANC`（`100 kOhm`）互斥，校验 `0xfe020000..0xfe060000` EL3 SRAM 窗口，并硬锁定 `el3_payload_transmit_authorized = False`（仅作脱机焊接前只读架构审计）。
  - **支柱 C — 确定性 5 级防变砖硬件恢复升级阶梯引擎（`8/8`）**：
    - 按最低影响严格分级决策：`Tier-1`（断电拔卡 / `EH1` `47 us` Stage-A 旁路 -> 原厂系统，零写入）-> `Tier-2`（`p15:/usr` `.orig` 原子回滚，经 `EH2` / `16/16` `SHA256(H0)==SHA256(H3)` + `054C:0DA1 -> 054C:0336` 净卸载）-> `Tier-3`（官方 `BODYDATA.DAT` `\x89UFU` 原厂 `p1` 回刷，遇未清理 `p15` 强制重定向至 `Tier-2`）-> `Tier-4`（`CXD90057` EL3 `0xfe020000` 冷启动只读诊断护栏）-> `Tier-5`（同机身 `CID` 绑定 `pnflasha*` 原始密文 + `loader_nor.bin` `/dev/mtd0ro` 离线 `8-bit` ISP 与 SPI NOR 最后手段仓库，硬锁定 `isp_write_authorized = False` / `spi_nor_write_authorized = False`）。
  - **CLI 与 `21/21` 恢复总检终局集成（[`fx3_recovery/__main__.py`](fx3_recovery/__main__.py)）**：
    - 注册 `verify-realhw-5tier-el3-ufu [--clean-room] [--json] [--out ...]` 与 `verify-all-recovery ... --with-phase160`（全开启时汇总为 **21/21** 支柱总检，同时保持无标志默认 `7/7` 与 `--with-phase155` `20/20` 向后兼容），并在 [`fx3_recovery/__init__.py`](fx3_recovery/__init__.py) 导出全部 Phase 160 公开符号；[`tests/test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py`](tests/test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py) 提供 **48 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_recovery verify-realhw-5tier-el3-ufu --clean-room --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --with-phase139 --with-phase144 --with-phase151 --with-phase155 --with-phase160 --clean-room --json
```

## Phase 166 — 真机主线 Part 10（Pillar 22 / `22/22` 统一恢复总检）：双介质独立 Tier-0 冷备份 Bit-Rot 校验、`GF(256)` 恢复预演与 `verify-22pillar-recovery`

- **[`realhw_22pillar_master_recovery_verifier.py`](fx3_recovery/realhw_22pillar_master_recovery_verifier.py)**：面向 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`CXD90057`）补齐操作员冷备份存储持久性门禁并落地 **22/22 支柱**统一实时恢复总检 CLI（`< 2.0s`），硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 只读检查本地 `7.02` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露回退：
  - **支柱 22A — 双介质独立 Tier-0 16 表面冷备份与 `528 B FX3RCPT1` 门禁（`verify_dual_media_cold_backup_vault` / `6/6`）**：
    - 强制要求同一机身的 16 表面 Tier-0 冷备份（`FX3RCPT1` 528 B CRC32 收据 + `pnflasha*`/`cnflasha*`/`mtd0ro`/`ext_csd` + `p2:/setting/{psd.bin,defdet.bin,Backup.bin}` + `p18:/lens/LENSFILE.BIN`）必须同时存在于**两个物理独立存储介质**（`media_a_device_id != media_b_device_id` 且 `hardware_uuid`、`mount_point` 不同，如主机 NVMe + 外置 SSD/SDXC）且 SHA-256 清单完全一致后，才允许进入 Stage-A 暂存准备（`stage_a_staging_permitted`）。
  - **支柱 22B — RAID-6 `GF(256)`（`0x11d`）静默 Bit-Rot 清洗与 `16/16` RAM 恢复前预演（`encode_16_surface_gf256_archive` / `scrub_and_rehearse_dual_media_bitrot_recovery` / `6/6`）**：
    - 模拟最多 2 块（1 块纯代数 `GF(256)` 伴随式定位或 2 块 `P+Q` 双校验）静默 bit-rot 损坏并完成无损重建与 `16/16` 内存魔数/域隔离/SHA-256 恢复前预演；`>= 3` 块超法定人数损坏、跨域混淆或写解锁请求 100% fail-closed 拦截（`physical_device_writes == 0`）。
  - **统一 `22/22` 总检聚合器与 CLI（`evaluate_22pillar_recovery_master` / `verify_22pillar_recovery_suite` / `verify-22pillar-recovery`）**：
    - 并发评估并聚合 Pillars `1..22`（含 Pillars 18、19、20、21、22），在 `< 2.0s` 内输出摘要或 `--json` / `--out`，同时在 `verify-all-recovery` 中注册 `--with-phase166`（保持无标志默认 `7/7` 与 `--with-phase160` `21/21` 完全向后兼容）；[`tests/test_realhw_22pillar_master_recovery_verifier.py`](tests/test_realhw_22pillar_master_recovery_verifier.py) 提供 **50 项**双模式快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_recovery verify-22pillar-recovery

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_recovery verify-22pillar-recovery --clean-room --json
```

## Phase 176 — 真机主线 Part 11（Pillar 23）：`p5:/wbi`（`WBI2` / `hibdrv.ko`）跨模式污染防火墙、断电/掉电恢复与 100 次循环 `H0 -> H1 -> H2 -> H3` 不变性校验器

- **[`realhw_wbi_powerloss_and_100cycle_transition_verifier.py`](fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`Linux 4.9.337-scel+`，`CXD90057`）落地两大关键真机可靠性护栏，硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`WBI_PERSISTENT_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 只读检查本地 FX3 `7.02` 供体（`nflasha5.img` `209,112,512 B` `1399` 节区、`partinf.conf`、`mount.conf`、`kemco.txt`、`p7-rootfs/sbin/{init,init2,initrc/setup_nflash}`、`vmlinux.bin`、`fx3-7.02-BODYDATA.DAT` `\x89UFU` 有界 4 KiB 头部）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退（`< 1.0s`）：
  - **支柱 23A — `p5:/wbi`（`WBI2` / `hibdrv.ko`）跨模式休眠快照污染防火墙（`8/8`）**：
    - `WBI_S1`..`WBI_S8`：强制 Stage-A（SD 卡插入）执行冷启动入口（`WBI_RESUME_BYPASS=1` + `noresume hibdrv.resume=0`，`wbi_resume_attempted == False`），在 Stage-B 期间同时对 `/dev/nflasha5` 与 `/dev/pnflasha5` 锁定 `BLKROSET=1`（`hibdrv.ko` 任何写入请求均 fail-closed 返回 `-EROFS` / `errno=30`，`wbi_persistent_writes == 0`），验证 `EH1` 拔卡（`< 50 us`）原厂 `p5:/wbi` SHA-256 与 `H0` 逐比特一致、损坏/过期 `WBI2` 魔数优雅回退冷启动、`/mnt/sd/BODYDATA.DAT`（`\x89UFU`）在 `< 100 us` 内同时绕过 Stage-B 与 `WBI2` 休眠恢复、拦截/静默屏蔽 `/sys/power/state` `disk` / `PM_SUSPEND_DISK`、校验 `p2/p5/p12/p18` 只读不变性，以及双介质 `FX3RCPT1` 收据对 `p5:/wbi` 基线 SHA-256 的前置绑定。
  - **支柱 23B — `NP-FZ100` 突发拔电池 / `6.3V` 掉电恢复与 100 次循环 `H0 -> H1 -> H2 -> H3` 确定性状态机（`8/8` + `100/100` 循环）**：
    - `PWR_S1`..`PWR_S8`：在 100 次确定性循环中混合正常原厂启动（`H0`）、Stage-A -> Stage-B（`H1`/`H2`）、Big-6 菜单界面突发拔 `NP-FZ100` 电池（`tmpfs` `/tmp` 与 `/etc/opelog` 蒸发，只读 eMMC 零日志损坏）、录制中 `6.3V` 掉电 / `EncWfiStop`（`.RSV` 隔离至外置 ExFAT 存储卡以便 `.MXF` 挽救）、`EH1` 拔卡 `47 us` 原厂重启、`EH2` `DISP+MENU+SHUTTER` 安全冷启动、`EH3` `libJit.so` 1 字节 CRC32 篡改 `< 1 ms` 原厂回退、`BODYDATA.DAT` UFU 共存与 `H2 -> H3` 净卸载，证明 `16/16` 关键表面 **0-bit eMMC 漂移**且 `H0 == H3` 逐比特一致；[`tests/test_realhw_wbi_powerloss_and_100cycle_transition.py`](tests/test_realhw_wbi_powerloss_and_100cycle_transition.py) 提供双模式快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-wbi-powerloss-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-wbi-powerloss-recovery --force-clean-room --json
```

## Phase 180 — 真机主线 Part 12（Pillar 24 / `24/24` 统一恢复总检）：Slot-1 `BODYDATA.DAT`（`>= 2.04`）回刷就绪度、`WPA2/WPA3` + HDMI-BRAW / `.cube` LUT 回退卫生与 `verify-24pillar-recovery`

- **[`realhw_24pillar_master_recovery_verifier.py`](fx3_recovery/realhw_24pillar_master_recovery_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`CXD90057` *Mira*）落地 **Pillar 24** 并提供统一 **24/24 恢复总检聚合器**（`< 1.8s` 并发运行，保留 [`realhw_22pillar_master_recovery_verifier.py`](fx3_recovery/realhw_22pillar_master_recovery_verifier.py) / `verify-22pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `7.02` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退：
  - **支柱 24A — 官方 Slot-1 `BODYDATA.DAT`（`811,876,768 B`，`\x89UFU\r\n\x1a\n`）卸载后原厂回刷就绪度门禁（`6/6`）**：
    - `P24A1`..`P24A6`：核验干净卸载（`H2 -> H3`）后机身固件满足 `>= Ver. 2.04` 底线（硬阻断 `<= Ver. 2.02` 防止硬件 `7 long + 7 short` LED 闪灯错误）、仅允许 **Slot-1 ExFAT 根目录** `/BODYDATA.DAT`（拦截 Slot-2、子目录及 `BODYDATA (1).DAT` / `BODYDATA_OLD.DAT` 重命名副本）、`p1` 更新武装标志清零（`0`）、`p15:/usr` `.orig`（`H0 == H3`）与 `p5:/wbi` `WBI2\x00\x00\x00\x00`（`H0 == H3`）恢复、`NP-FZ100` 电量底线（`>= 3 格 / >= 7.20V`），以及 `p12:/cert/RQ_LIC.DAT` C2PA 许可证上限（`<= 100`）与 `RO` 只读完整性。
  - **支柱 24B — 挥发网络（仅 `WPA2/WPA3`）与 HDMI-BRAW / `.cube` 3D LUT 回退卫生（`6/6`）**：
    - `P24B1`..`P24B6`：强制仅放行 `WPA2` / `WPA3` / `Access Authentication`（硬拒 `WEP`、`WPA1`、旧版 `IPsec`），证明 Stage-B `tmpfs` Wi-Fi 凭据、`.cube` 3D LUT 暂存文件与 HDMI BRAW 运行态在 `EH1` 拔卡或 `H2 -> H3` 干净卸载后 **零泄露** 至原厂 `p2:/setting/Backup.bin`（`BK4\x00`，`H0 == H3`）或 `p30:/usr/data/lut`（`H0 == H3`），且任何写解锁请求均 fail-closed 拦截。
  - **统一 `24/24` 恢复总检聚合器与 CLI（`evaluate_24pillar_recovery_master` / `verify-24pillar-recovery` / `verify-slot1-ufu-reflash-readiness`）**：
    - 并发调度 `Pillars 1..22`（`evaluate_22pillar_recovery_master`）+ **Pillar 23**（`run_wbi_powerloss_and_100cycle_suite`）+ **Pillar 24**（`run_pillar24_standalone_suite`），汇总产出 **`24/24`**（`VERIFIED_24OF24_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_24pillar_master_recovery_verifier.py`](tests/test_realhw_24pillar_master_recovery_verifier.py) 提供 **50 项**双模式快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-slot1-ufu-reflash-readiness --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-24pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-24pillar-recovery --force-clean-room --json
```

## Phase 184 — 真机主线 Part 13（Pillar 25）：气隙实验台 SD/CFexpress BYOF 清单（`FX3BNDL1`）、双介质 `FX3RCPT1` 绑定与零联网卫生护栏

- **[`realhw_airgap_sd_bundle_manifest_verifier.py`](fx3_recovery/realhw_airgap_sd_bundle_manifest_verifier.py)**：面向 `Sony ILME-FX3`（`Ver. 7.02`，Model ID `0x91030080`）在物理插卡前提供完全离线的气隙实验台 SD/CFexpress 暂存包校验，并保持 `verify-22pillar-recovery` 与 `verify-24pillar-recovery` 100% 向后兼容；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`、`AIRGAP_SOCKETS_OPENED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `7.02` 供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性净室回退：
  - **支柱 25A — 单机绑定 `FX3RCPT1` 与 `FX3BNDL1`（HMAC-SHA256 + CRC32）交叉验签（`8/8`）**：
    - `P25A1`..`P25A8`：将卡内 `FX3BNDL1` 清单绑定至目标物理机身双介质 `FX3RCPT1`（`528 B`）冷备份回执（`serial_hash`、`model_id == 0x91030080`、`body_fw == "7.02"`、5 项核心 Tier-0 `H0` 摘要 `p2`/`p5`/`p12`/`p15`/`p18`、`st_dev_primary != st_dev_secondary`），fail-closed 拦截跨机插卡错配（`CAMERA_SERIAL_RECEIPT_MISMATCH`）、非 FX3 机型（`0x91030084` FX30 / `0x91020080` FX6）、`< 7.02` 机身固件、单介质未复核回执以及 CRC32/HMAC 篡改。
  - **支柱 25B — macOS/Linux ExFAT 卫生、AppleDouble（`._*`）清洗、AArch64 ELF64 Shim 与 `BODYDATA.DAT` 互斥防火墙（`8/8`）**：
    - `P25B1`..`P25B8`：拦截 `.DS_Store`、`.Spotlight-V100`、`.fseventsd`、`.Trashes`、`.TemporaryItems` 与 `._*` AppleDouble 残留并支持仅限系统临时目录的 dry-run 清洗（`scrub_exfat_staging_tree_tempdir_dry_run`），校验 `FX6_STAGEB/` 下 `fx6-stage-a-verify`、`libJit.so`（`<= 64 KiB`）与 `libgrm-fbinit9.so` 的 ELF64 `EM_AARCH64`（`e_machine == 183`）头与精确 SHA-256，硬阻断卡根 `BODYDATA.DAT` / `BODYDATA (1).DAT`（`\x89UFU`）与活跃 `p1` 触发器共存及任何网络套接字打开（`airgap_sockets_opened == 0`）。
  - **CLI 与双模式快速单元测试（[`tests/test_realhw_airgap_sd_bundle_manifest_verifier.py`](tests/test_realhw_airgap_sd_bundle_manifest_verifier.py) / **50 项**）**：
    - 注册 `verify-airgap-sd-bundle [--force-clean-room] [--json] [--out ...]` 并导出完整 Phase 184 Pillar 25 公开符号。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-airgap-sd-bundle --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-airgap-sd-bundle --force-clean-room --json
```

## Phase 190 — 真机主线 Part 14（Pillar 26 / `26/26` 统一恢复总检）：`ILME-FX3` vs `ILME-FX3A` 跨分支恢复防火墙、`CAMSET` 设置隔离与 `XLR-H1` MI 热靴音频卫生护栏

- **[`realhw_26pillar_master_recovery_verifier.py`](fx3_recovery/realhw_26pillar_master_recovery_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`1.44M` LCD + NFC + IR）落地 **Pillar 26** 并提供统一 **26/26 恢复总检聚合器**（`< 2.0s` 并发运行，保留 [`realhw_22pillar_master_recovery_verifier.py`](fx3_recovery/realhw_22pillar_master_recovery_verifier.py) / `verify-22pillar-recovery` 与 [`realhw_24pillar_master_recovery_verifier.py`](fx3_recovery/realhw_24pillar_master_recovery_verifier.py) / `verify-24pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `7.02` 与 `libInfraHotshoe.so` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退：
  - **支柱 26A — `ILME-FX3`（`Ver. 7.02`，`1.44M` LCD + NFC + IR）vs `ILME-FX3A`（`Ver. 2.02`，`2.36M` XGA LCD，无 NFC/IR）跨分支恢复与 `CAMSET` 防火墙（`6/6`）**：
    - `P26A1`..`P26A6`：`< 50 us` 预检验证机身硬件特征（`1.44M` LCD + NFC + IR），双向拦截 `ILME-FX3`（`0x91030080`）与 `ILME-FX3A`（`Ver. 1.xx/2.xx`）、`ILME-FX30`（`0x91030084`）、`ILME-FX6`（`0x91020080`）之间的 `BODYDATA.DAT` 恢复包及显示垫片混用，拦截跨分支 `CAMSET01.DAT`..`CAMSET10.DAT` SD 卡设置导入，并验证原厂 `p2:/setting/Backup.bin`（`BK4\x00`，`H0 == H3`，`BLKROSET=1`）。
  - **支柱 26B — `XLR-H1` MI 热靴 `48kHz/24bit 4ch` 恢复后与 UFU 升级后音频卫生护栏（`6/6`）**：
    - `P26B1`..`P26B6`：强制零手柄独立固件写入（索尼从未发布独立 `XLR-H1` 固件包），校验冷启动恢复期机身 `3.5mm` 麦克风插孔物理抢占安全（`[MI Shoe Audio Set.]` 物理切断与灰显保护）、`S&Q` 静音一致性及 Stage-A->Stage-B `+48V` 幻象供电无毛刺，审计 `BODYDATA.DAT` 官方升级后 `48kHz/16bit 2ch` 默认重置行为，并确保 Stage-B 零污染 `p2:/setting/Backup.bin`（`stage_b_backup_bin_writes == 0`、`H0 == H3`）。
  - **统一 `26/26` 恢复总检聚合器与 CLI（`evaluate_26pillar_recovery_master` / `verify-26pillar-recovery` / `verify-fx3a-branch-recovery-firewall`）**：
    - 并发调度 `evaluate_24pillar_recovery_master`（`Pillars 1..24`）+ **Pillar 25**（`run_airgap_sd_bundle_manifest_suite`）+ **Pillar 26**（`run_pillar26_standalone_suite`），汇总产出 **`26/26`**（`VERIFIED_26OF26_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_26pillar_master_recovery_verifier.py`](tests/test_realhw_26pillar_master_recovery_verifier.py) 提供 **50 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-fx3a-branch-recovery-firewall --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-26pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-26pillar-recovery --force-clean-room --json
```

## Phase 195 — 真机主线 Part 15（Pillar 27 / `27/27` 统一恢复总检）：`DC-C1`（`>=65W / 5A`）与 `NP-FZ100` 欠压互锁、双介质 `.cube` User LUT `p2:/setting` 金库隔离与 `verify-27pillar-recovery`

- **[`realhw_27pillar_dcc1_pd_lut_vault_verifier.py`](fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 27** 并提供统一 **27/27 恢复总检聚合器**（`< 2.2s` 并发运行，保留 [`realhw_22pillar_master_recovery_verifier.py`](fx3_recovery/realhw_22pillar_master_recovery_verifier.py) / `verify-22pillar-recovery`、[`realhw_24pillar_master_recovery_verifier.py`](fx3_recovery/realhw_24pillar_master_recovery_verifier.py) / `verify-24pillar-recovery` 与 [`realhw_26pillar_master_recovery_verifier.py`](fx3_recovery/realhw_26pillar_master_recovery_verifier.py) / `verify-26pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `7.02` 与 `libUsbBusPower.so` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 零专有字节泄露确定性回退：
  - **支柱 27A — `NP-FZ100`（`>=51%` / `>=3 格`）与 `DC-C1`（`>=65W + 5A` e-Marked 线缆）冷备份与 UFU 欠压互锁（`6/6`）**：
    - `P27A1`..`P27A6`：进入冷备份 `AdjustControl (0x40)` / UFU `BODYDATA.DAT` 阶段前硬校验电源拓扑——机身 USB-C PD 必须装配物理 `NP-FZ100` 电池（`>= 51%` / `>= 3 格` / `>= 7.20V`），硬阻断 Micro-USB 供电企图，并强制 `DC-C1` 假电池耦合器满足 `>= 65W` PD + `5A` e-Marked 线缆且无供电故障闪烁指示；证明若 Stage-B 中途 `DC-C1` 突然断电，易失性 `tmpfs` 覆盖层干净蒸发且 `16/16` Tier-0 关键表面保持零 eMMC 损伤（`H0 == H3`）。
  - **支柱 27B — 双介质 `.cube` User LUT（`User1..User16`）易失覆盖层 vs 原厂 `p2:/setting` 金库保全（`6/6`）**：
    - `P27B1`..`P27B6`：校验 `SDXC`（`/Private/Sony/PRO/LUT/`）与 `CFexpress Type A`（`/Sony/PRO/LUT/`）双介质非对称 LUT 目录路径及 `17pt/33pt`（`<= 63B` ASCII 文件名）`.cube` 规范，强制 Stage-B 期间所有暂存仅驻留易失 `/tmp/fx6_lut_overlay`（`tmpfs`），`0` 次写入 `p2:/setting`；证明重启回原厂 FX3 `7.02` 后 `p2:/setting/Backup.bin` 保持 `BLKROSET=1` 且 `User1..User16` 全部 `16` 个注册槽位与 `AE Level Offset`（`0.0..+2.0 EV`、`1/3 EV` 步进）`100%` 逐比特一致（`H0 == H3`）。
  - **统一 `27/27` 恢复总检聚合器与 CLI（`evaluate_27pillar_recovery_master` / `verify-27pillar-recovery` / `verify-dcc1-pd-lut-vault`）**：
    - 并发调度 `evaluate_26pillar_recovery_master`（`Pillars 1..26`）+ **Pillar 27**（`run_pillar27_standalone_suite`），汇总产出 **`27/27`**（`VERIFIED_27OF27_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py`](tests/test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py) 提供 **50 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-dcc1-pd-lut-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-27pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-27pillar-recovery --force-clean-room --json
```

## Phase 198 — 真机主线 Part 16（Pillar 28 / `28/28` 统一恢复总检）：`[Fan Control] = Always Off -> Auto` 备份前温控覆盖互锁、`Backup.bin` 快门 `Speed/Angle` 独立槽位与 `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User LUT 代际防污染总检（`verify-28pillar-recovery`）

- **[`realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py`](fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 28** 并提供统一 **28/28 恢复总检聚合器**（`< 2.4s` 并发运行，保留 `verify-22pillar-recovery`、`verify-24pillar-recovery`、`verify-26pillar-recovery` 与 `verify-27pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`、`FX6 6.01`、`Backup.bin`、`libfan.so` 与 `libbackup.so` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 28A — `ILME-FX3` 精确四态 `[Fan Control]`（`Auto`、`Minimum`、`Off in Rec`、`Always Off`，硬拒 `Auto1/Auto2`）与冷备份前温控覆盖互锁（`6/6`）**：
    - `P28A1`..`P28A6`：若原厂 FX3 `[Fan Control]` 停留在 `Always Off`（或非 `Auto`），在进入 `AdjustControl (0x40)` 75 MiB `p3` 冷备份或高负载 Stage-B 前硬阻断直至关切为 `Auto`（严格识别 `[Auto Power OFF Temp.] = Standard / High`）；建模 `Off in Rec` 待机 `MAX PWM (100%)` vs 录制 `0% PWM` 及 `>= 82°C` 紧急热保护满速覆盖，并 fail-closed 拦截不存在的 `Auto1`/`Auto2` 伪枚举。
  - **支柱 28B — `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT 二进制代际分裂防污染金库与 `Backup.bin` `[Speed]`/`[Angle]` 独立槽位完整性（`6/6`）**：
    - `P28B1`..`P28B6`：阻断供体 `FX6 Ver. 6.01`（`<= 6.01` 旧版 LUT 槽位序列化格式）污染宿主 `Stock FX3 Ver. 7.02`（`7.00+` 优化后 LUT 序列化格式）的 `p2:/setting` `User1..User16` 槽位，强制 Stage-B 严格重定向至易失 `/tmp/fx6_lut_overlay`（`tmpfs`）；校验 `Backup.bin` 中 `[Speed]` 与 `[Angle]` 独立键槽存储（与 `[Exposure step]` `0.3EV / 0.5EV` 解耦）、常规 `5.6°..64F` vs `119.88p / 100p` & `S&Q` `5.6°..360°` 量程边界，以及冷重启回原厂 `7.02` 后 `16/16 H0 == H3`。
  - **统一 `28/28` 恢复总检聚合器与 CLI（`evaluate_28pillar_recovery_master` / `verify-28pillar-recovery` / `verify-fan-pwm-lut-split-vault`）**：
    - 并发调度 `evaluate_27pillar_recovery_master`（`Pillars 1..27`）+ **Pillar 28**（`run_pillar28_standalone_suite`），汇总产出 **`28/28`**（`VERIFIED_28OF28_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py`](tests/test_realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py) 提供 **52 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-fan-pwm-lut-split-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-28pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-28pillar-recovery --force-clean-room --json
```

## Phase 208 — 真机主线 Part 17（Pillar 29 / `29/29` 统一恢复总检）：仅限 Slot-1 `CAMSET01..10.DAT` 双介质路径分裂金库、`BIG6` 零物理 e-ND 总线护栏、双卡 `[Simult. + Auto Switch = Off]` 严格冗余与 `VMC-BNCM1` / `1.65x` 净冷回退（`verify-29pillar-recovery`）

- **[`realhw_29pillar_camset_slot1_simult_vault_verifier.py`](fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 29** 并提供统一 **29/29 恢复总检聚合器**（`< 2.5s` 并发运行，保留 `verify-22pillar-recovery`、`verify-24pillar-recovery`、`verify-26pillar-recovery`、`verify-27pillar-recovery` 与 `verify-28pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`、`cpapp-b.bin`、`appFw.so`、`Backup.bin`、`libInfraMediaConfig.so` 与 `libBackupManager.so` 供体并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 29A — 仅限 Slot-1 `CAMSET01..10.DAT` 双介质金库隔离与 `BIG6` 零物理 e-ND 总线保护（`6/6`）**：
    - `P29A1`..`P29A6`：强制仅允许 **Slot 1** 读写 `<= 10` 个 `CAMSET01.DAT..CAMSET10.DAT` 档案（硬拦截 `Slot 2`、`> 10` 档案、`MR` 调出相机设置模式，并排除 `WB Custom 1/2/3`、`FTP`、流媒体、IP/证书与日期时间等机器绑定项）；严格区分 **SDXC**（`/PRIVATE/SONY/SETTING/FX3/CAMSET/`）与 **CFexpress Type A**（`/SONY/SETTING/FX3/CAMSET/`）根目录非对称拓扑；拦截 `FX3` vs `FX3A` vs `FX6` 跨机型 `.DAT` 混入，强制 Stage-B 将 `FX6` 配置沙箱化至易失 `/tmp/fx6_camset_overlay`（`tmpfs`）；同时强制 `BIG6`（`Home`）左下角 `[Aperture / ND Filter]` 在 FX3 `CP` 总线上保持零物理 e-ND 执行器驱动帧（`e_nd_actuator_tx_count == 0`）。
  - **支柱 29B — 双卡 `[Simult. Recording]` + `[Auto Switch Media = Off]` 严格金库冗余、`VMC-BNCM1` 仅机身 `TC IN` 门禁与 `[De-Squeeze]` `1.65x` 净冷回退（`6/6`）**：
    - `P29B1`..`P29B6`：在双卡冷备/严格冗余录制下强制 `[Auto Switch Media] = Off`，防止 `Ver. 2.0+` 单卡写满后静默降级为单卡续录；硬阻断 `VMC-BNCM1` 误插 `XLR-H1` 手柄 Micro-USB 口及在机身 Multi/Micro USB 口反向发射 BNC `TC OUT`（`EOPNOTSUPP`，时间码输出严格路由至 Type-A HDMI）；验证 `[De-Squeeze Display]`（`1.6x == 1.65` 倍水平拉伸 + `MF / Wide / SteadyShot Off / Face Priority Off` 四项硬件强锁 + HDMI RAW 抑制）、无内置菜单的外置 `M&C Focus Map`（`>= 150fps` 截止）及 `[Shockless WB]`（`[C.Temp./Filter]` K 值与 `A–B / G–M` 即时旁路）在冷启动回到原厂 `7.02` 后保持 `p2:/setting` `16/16 H0 == H3`。
  - **统一 `29/29` 恢复总检聚合器与 CLI（`evaluate_29pillar_recovery_master` / `verify-29pillar-recovery` / `verify-camset-simult-vault`）**：
    - 并发调度 `evaluate_28pillar_recovery_master`（`Pillars 1..28`）+ **Pillar 29**（`run_pillar29_standalone_suite`），汇总产出 **`29/29`**（`VERIFIED_29OF29_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_29pillar_camset_slot1_simult_vault_verifier.py`](tests/test_realhw_29pillar_camset_slot1_simult_vault_verifier.py) 提供 **52 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-camset-simult-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-29pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-29pillar-recovery --force-clean-room --json
```

## Phase 212 — 真机主线 Part 18（Pillar 30 / `30/30` 里程碑恢复总检）：`Px` 主片+代理双槽原子联动金库与 `[Off(HDMI Only)]` 零内录卡互锁（`verify-30pillar-recovery` / `verify-proxy-coupled-hdmi-vault`）

- **[`realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py`](fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 30** 并将全套恢复总检正式收口至 **`30/30` 里程碑（`VERIFIED_30OF30_PILLAR_RECOVERY_MASTER`）**（`< 2.6s` 并发运行，保持 `verify-22/24/26/27/28/29pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libInfraMediaConfig.so`、`libBackupManager.so` 与 `libbackup.so` 供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 30A — `M4ROOT/CLIP/` 与 `M4ROOT/SUB/` `(Px)` 原子联动金库（`6/6`）**：
    - `P30A1`..`P30A6`：跨 **Slot 1 & Slot 2** 审计 `M4ROOT/CLIP/`（`XAVC HS` / `XAVC S` / `XAVC S-I` `.MP4` + `.XML` 伴生元数据）与 `M4ROOT/SUB/`（`*S03.MP4`：`XAVC HS HD` `1920x1080` 10-bit `16M`/`9M` HEVC 或 `XAVC S HD` `1280x720` 8-bit `6M` AVC）原子联动一致性；强制机内 Delete / Protect 对 `CLIP/` 与 `SUB/` 双侧原子生效，fail-closed 拦截孤立 `SUB/`、带 `(Px)` 位但缺 `SUB/`、保护只读属性不一致与单侧操作请求；同时强制 `119.88p`/`100p` Normal 及 `>=120fps`/`100fps` S&Q 代理生成硬截断，严禁机内代理直接回放假设。
  - **支柱 30B — `[Off(HDMI Only)]` 零内录卡互锁、HDMI Log `1080p` 降档与 `FocusMag × BrightMon` 互斥（`6/6`）**：
    - `P30B1`..`P30B6`：阻断将 `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]`（`[4K Output Set.(HDMI Only)]` `59.94p..24.00p 10bit`）误判为 Slot 1 / Slot 2 已开启内录的重大风险；校验 `[On]` 且关闭 HDMI RAW 输出时 `Log Shooting`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）或 `PPLUT1..4` 强制 HDMI `1080p` 降档、`[HDMI Info. Display]` 黑屏/自动抑制逻辑，以及 `Focus Magnifier`（`x1.0`/`x4.0`）与 `Bright Monitoring`（`Setting Effect OFF` + `P/A/S/M + MF` 硬锁）双向互斥互锁；证明 Stage-B 易失 `tmpfs` 覆盖层与 `Backup.bin` / `16/16` Tier-0 表面干净复位（`H0 == H3`）。
  - **统一 `30/30` 里程碑恢复总检聚合器与 CLI（`evaluate_realhw_30pillar_recovery_master` / `verify-30pillar-recovery` / `verify-proxy-coupled-hdmi-vault`）**：
    - 并发调度 `evaluate_29pillar_recovery_master`（`Pillars 1..29`）+ **Pillar 30**（`run_pillar30_standalone_suite`），汇总产出 **`30/30`**（`VERIFIED_30OF30_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py`](tests/test_realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py) 提供 **52 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-proxy-coupled-hdmi-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-30pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-30pillar-recovery --force-clean-room --json
```

## Phase 215 — 真机主线 Part 19（Pillar 31 / `31/31` 统一恢复总检）：`File Settings`（37 字符 / SDHC 强锁）+ `Shot Mark1/2` `*M01.XML` 伴生金库与 `TC Regenerate` Slot-1 连续性总检（`verify-31pillar-recovery` / `verify-filesettings-shotmark-tcregen-vault`）

- **[`realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.py`](fx3_recovery/realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 31** 并将全套恢复总检推进至 **`31/31`（`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER`）**（`< 2.8s` 并发运行，保持 `verify-22/24/26/27/28/29/30pillar-recovery` 100% 向后兼容）；硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libInfraMediaConfig.so`、`libInfraMediaCommon.so` 与 `libInfraMediaMount.so` 供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 31A — `[File Settings]`（5 态格式 / `<=37` ASCII 标题 / SDHC `<=32GB` FAT32 强锁）与 `Shot Mark1/2` `*M01.XML` 伴生金库（`6/6`）**：
    - `P31A1`..`P31A6`：跨 **Slot 1 & Slot 2** 审计 `[File Number]`（`Series` / `Reset` + `Series Counter Reset`）、5 态 `[File Name Format]`（`Standard`、`Cam ID + Reel#`、`Title`、`Date + Title`、`Title + Date`）、`[Title Name Settings]`（`1..37` 位受限 ASCII 字符且仅对新录片段生效，禁止回溯改名假设）及 **SDHC `<=32GB` FAT32** 插入时强制锁定 `[Standard]` 与禁止自定义文件夹规则；拦截 `Backup.bin` 恢复或回滚后序列号 / 卷号（`Reel#`）与现有 `/M4ROOT/CLIP/` 素材发生冲突；同时审计 `/M4ROOT/CLIP/*M01.XML` 非实时元数据伴生完整性，阻断破坏 `[Image Jump Setting]`（`Shot Mark Only` / `Shot Mark1/2 Only`）或 FTP `[Only Shot Mark Mov.]` 批量抢救传输的孤立/损坏 XML。
  - **支柱 31B — `[TC/UB]` `[Regenerate]` Slot-1 独占主时间码连续性、`VMC-BNCM1` `EXT-LK` 掉锁告警、S&Q 锁止与耦合 `REC Lamp`（`6/6`）**：
    - `P31B1`..`P31B6`：校验 `[Time Code Make] = [Regenerate]` 强制切换至 `[Rec Run]` 步进，并在 `[Simult. Recording]` 下严格从 **Slot 1** 读取上一条片段末尾时间码顺延 `+1` 帧；拦截恢复 `Backup.bin` 切换 `Time Code Make != Preset` 或 `Time Code Run != Free Run` 时未确认重同步的 `VMC-BNCM1` `EXT-LK` 外部锁定释放风险；阻断 `S&Q` 模式下 `[Time Code Run]` 覆盖与 HDMI `[Time Code Output = On]`；并校验后部与顶部 `REC` 按键灯硬件同步耦合（`All On` / `Only Front Off` / `All Off`）、`[Silent Mode = On] -> [Audio signals = Off]` 硬锁及 Tier-0 `16/16 H0 == H3`。
  - **统一 `31/31` 恢复总检聚合器与 CLI（`evaluate_realhw_31pillar_recovery_master` / `verify-31pillar-recovery` / `verify-filesettings-shotmark-tcregen-vault`）**：
    - 并发调用 `evaluate_realhw_30pillar_recovery_master`（`Pillars 1..30`）+ **Pillar 31**（`run_pillar31_standalone_suite`），汇总产出 **`31/31`**（`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.py`](tests/test_realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.py) 提供 **54 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-filesettings-shotmark-tcregen-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-31pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-31pillar-recovery --force-clean-room --json
```

## Phase 220 — 真机主线 Part 20（Pillar 32 / `32/32` 统一恢复总检）：`NTSC/PAL` 数据库留存隔离、`Gamma Display Assist` × `Display LUT` 恢复对等与 `Pixel Mapping` 自动重启 `cnflasha` 只读金库总检（`verify-32pillar-recovery` / `verify-ntscpal-pixelmap-vault`）

- **[`realhw_32pillar_ntscpal_pixelmap_vault_verifier.py`](fx3_recovery/realhw_32pillar_ntscpal_pixelmap_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 32** 并将全套恢复总检正式收口至 **`32/32`（`VERIFIED_32OF32_PILLAR_RECOVERY_MASTER`）**（`< 3.0s` 并发运行，保持 `verify-22/24/26/27/28/29/30/31pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so` 与 `libInfraMediaConfig.so` 供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 32A — `[NTSC/PAL Selector]` 复位非对称性、帧率/`DF-NDF` 制式互斥、双卡槽 `M4ROOT`/`PRIVATE/AVCHD` 媒体库隔离与 `[Gamma Display Assist]` × `[Display LUT]` 对等金库（`6/6`）**：
    - `P32A1`..`P32A6`：审计 `[Camera Settings Reset]` 保留 `[Setup]` 下 `[NTSC/PAL Selector]` 而仅完整 `[Initialize]` 恢复出厂区域制式的复位非对称性，以及偏离出厂区域制式时开机横幅（`"Running on NTSC."` / `"Running on PAL."`）一致性；强制 NTSC（`23.98p` NTSC 独占、`24.00p`、`29.97p`、`59.94p`、`119.88p` + `DF`/`NDF` `[TC Format]`）与 PAL（`25p`、`50p`、`100p`；无 `23.98p` 且 `DF`/`NDF` 锁定不可用）制式边界；跨 **Slot 1 & Slot 2** 校验 `/M4ROOT/MEDIAPRO.XML` 与 `/PRIVATE/AVCHD/BDMV/INDEX.BDM` 媒体数据库区域隔离，阻断未完成冷备份即通过 `Backup.bin` 恢复或跨制式换卡触发破坏性重新注册；同时审计 4 态 `[Gamma Disp. Assist Typ.]`（`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`）、`[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）激活时强制锁定 `[Gamma Display Assist = Off]` 并完全交由 `[Display LUT]` 接管、仅作用于机身 LCD/取景器而不注入外接 HDMI 的作用域边界，以及 `Backup.bin` 恢复前后状态对等（`16/16` Tier-0 `H0 == H3`）。
  - **支柱 32B — 手动 `[Pixel Mapping]` 自动重启（`H1 -> H2` 易失 `/tmp` Stage-B 覆盖层清零回归原厂 `FX3 Ver. 7.02` `H0 == H2`）、低电量门禁、`[Auto Pixel Mapping]` 关机暗场快门安全与 `cnflasha` 传感器坏点表只读金库（`6/6`）**：
    - `P32B1`..`P32B6`：强制手动 `[Pixel Mapping]`（`>= 20%` 且无低电告警）与 Tier-0 冷备份（`>= 51%` NP-FZ100 底线）低电量硬门禁、校准期间整机操作闭锁及校准完成后的强制自动重启，验证重启将 `/tmp` 易失 Stage-B 覆盖层（`H1`）彻底清零并回归原厂 `FX3 Ver. 7.02`（`H0 == H2`）；审计 `[Auto Pixel Mapping = On]`（即便在 `[Silent Mode = On]` 下周期性关机机械快门暗场动作声属正常校准，阻断关机瞬间拔电池或误判硬件故障；设为 `[Off]` 时校验 `<= 3` 天手动校准周期）；并硬锁定 `cnflasha`（`/dev/cnflasha`、`cnflasha12/13`、`nvs`、`adj`）`IMX510` 传感器坏点补偿表严格只读（`cnflasha_userspace_write_blocked == True`，`physical_device_writes == 0`）。
  - **统一 `32/32` 恢复总检聚合器与 CLI（`evaluate_realhw_32pillar_recovery_master` / `verify-32pillar-recovery` / `verify-ntscpal-pixelmap-vault`）**：
    - 并发调用 `evaluate_realhw_31pillar_recovery_master`（`Pillars 1..31`）+ **Pillar 32**（`run_pillar32_standalone_suite`），汇总产出 **`32/32`**（`VERIFIED_32OF32_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_32pillar_ntscpal_pixelmap_vault_verifier.py`](tests/test_realhw_32pillar_ntscpal_pixelmap_vault_verifier.py) 提供 **56 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-ntscpal-pixelmap-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-32pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-32pillar-recovery --force-clean-room --json
```

## Phase 225 — 真机主线 Part 21（Pillar 33 / `33/33` 统一恢复总检）：`Power Save Start Time` 9 条件气隙防休眠互锁、`Auto Power OFF Temp.` 脚架热安全金库与 `SteadyShot Active` / `Clear Image Zoom` 档案一致性总检（`verify-33pillar-recovery` / `verify-powersave-9cond-temp-vault`）

- **[`realhw_33pillar_powersave_9cond_temp_vault_verifier.py`](fx3_recovery/realhw_33pillar_powersave_9cond_temp_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 33** 并将全套恢复总检正式收口至 **`33/33`（`VERIFIED_33OF33_PILLAR_RECOVERY_MASTER`）**（`< 3.2s` 并发运行，保持 `verify-22/24/26/27/28/29/30/31/32pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so` 与 `libInfraMediaConfig.so` 供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 33A — `[Power Save Start Time]` 9 条件自动解除矩阵、气隙 `NP-FZ100` `75 MiB` `p3` 冷备份防休眠互锁与 `[Auto Power OFF Temp.]` + `[Fan Control]` 备份前冷却热金库（`6/6`）**：
    - `P33A1`..`P33A6`：全量审计官方 9 项自动解除待机休眠条件（USB 供电、幻灯片播放、FTP 传输、动态影像录制、连接电脑、HDMI/TV 连接、`[IR Remote Ctrl] = [On]`、`[Bluetooth Rmt Ctrl] = [On]`、流媒体 / Creators' Cloud 上传）；在纯气隙机内 `NP-FZ100` 电池（`>= 51%` 底线）执行 Tier-0 `75 MiB` `p3` 冷转储或 `CAMSET` 恢复且 9 项解除条件均未激活时，强制 `[Power Save Start Time]` 设为 `30 Min` 或 `Off`（拦截默认 `5 Min`、`2 Min`、`1 Min`、`10 Sec` 防中途休眠中断）；审计 `[Auto Power OFF Temp.]`（`Standard` 默认 vs `High` 强制三脚架固定防低温烫伤），并在冷转储 / `CAMSET` 恢复前强制将 `[Fan Control] = [Always Off]` 预冷切换至 `[Auto]`（`< 85.0°C` SoC 上限）。
  - **支柱 33B — `[SteadyShot]`（`Active` 三重禁入截断）与 `[Clear Image Zoom]`（四重自动锁定）`Backup.bin` / `CAMSET01..10.DAT` 档案一致性金库（`6/6`）**：
    - `P33B1`..`P33B6`：强制拦截 `[SteadyShot] = [Active]`（`~1.1x` 视角裁切）在 `119.88p`/`100p`、S&Q `>=100fps`/`120fps` 与外接 HDMI `[RAW Output = On]` 下的非法组合；拦截 `[Clear Image Zoom]` / `[Digital Zoom]` 在静态 `RAW`、`119.88p`/`100p` 与 S&Q `100/120/200/240fps` 下的禁用状态，并审计超出光学变焦范围时的 4 项自动锁定（`[Focus Area]` 禁用并锁定中心优先、`[Metering Mode]` 锁定 `Multi`、`[Face/Eye Prior. in AF]` 及多重测光人脸优先禁用、实时追踪禁用）；校验 Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT` 与 `Backup.bin`（`BK4\x00`）恢复前后参数对等（`16/16` Tier-0 `H0 == H3`）。
  - **统一 `33/33` 恢复总检聚合器与 CLI（`evaluate_realhw_33pillar_recovery_master` / `verify-33pillar-recovery` / `verify-powersave-9cond-temp-vault`）**：
    - 并发调用 `evaluate_realhw_32pillar_recovery_master`（`Pillars 1..32`）+ **Pillar 33**（`run_pillar33_standalone_suite`），汇总产出 **`33/33`**（`VERIFIED_33OF33_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_33pillar_powersave_9cond_temp_vault_verifier.py`](tests/test_realhw_33pillar_powersave_9cond_temp_vault_verifier.py) 提供 **58 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-powersave-9cond-temp-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-33pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-33pillar-recovery --force-clean-room --json
```

## Phase 229 — 真机主线 Part 22（Pillar 34 / `34/34` 统一恢复总检）：`Zebra` 跨复位留存、`(Delete)` `Full Format` & `MENU+Delete` 2s 组合键 Slot-1 金库防火墙与 `S&Q` 状态恢复总检（`verify-34pillar-recovery` / `verify-zebra-fullformat-chord-vault`）

- **[`realhw_34pillar_zebra_fullformat_chord_vault_verifier.py`](fx3_recovery/realhw_34pillar_zebra_fullformat_chord_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 34** 并将全套恢复总检正式收口至 **`34/34`（`VERIFIED_34OF34_PILLAR_RECOVERY_MASTER`）**（`< 3.4s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libInfraMediaConfig.so` 与 `libInfraMediaCommon.so`（校验 `GetFormatProgress`、`mmcdIoctlFormat`、`msdFormat`）7 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 34A — Slot-1 Tier-0 金库防格式化防火墙（`Quick Format`、`(Delete)` 切换 `Full Format`、中途 `Cancel` 已擦除风险与拍摄界面 `MENU + (Delete)` 约 2s 硬件组合键）（`6/6`）**：
    - `P34A1`..`P34A6`：当 **Slot 1** 存有活跃或未完成离线校验的 Tier-0 恢复金库（`pnflasha` / `cnflasha` / `CAMSET01.DAT`）时，全面建模并阻断 4 类高危擦除向量：① 默认 `[Quick Format]` 文件系统管理区擦除；② 格式化对话框内按 `(Delete)` 键切换触发的 `[Full Format]` 全盘数据块彻底物理擦除（不可通过数据恢复软件找回）；③ `[Full Format]` 执行中途按下 `[Cancel]` 虽使存储卡保持可用但已将先前扇区永久擦除的残损风险；④ 拍摄画面长按 `MENU + (Delete)` 约 `2s` 直接唤起 `[Format]` 的盲按组合键误触；强制要求完成离机 `SHA-256` 校验回执 + 拨下 SDXC 物理 `LOCK/WP` 写保护开关 + 取出/替换金库卡后方可格式化，并对仍处于物理 WP 锁定的 SDXC 卡执行硬件拒写拦截。
  - **支柱 34B — `[Zebra Display]` / `[Zebra Level]` 跨 `[Camera Settings Reset]` 非对称留存、LCD 独占监看隔离（`0` HDMI 辅助泄漏）与 `Ver. 7.02` `[Mode Settings]`（`Fixed/Variable` vs `S&Q`）状态恢复（`6/6`）**：
    - `P34B1`..`P34B6`：校验 `[Zebra Display]`（`Off`/`On`）与 `[Zebra Level]`（`70..100+`、`Custom 1` `Std ± Range`、`Custom 2` `Lower Limit`）在 `[Camera Settings Reset]` 后完整保留、仅在完整 `[Initialize]` 下归零至 `Off` / `70`；强制校验 `[Zebra]` 条纹与 `[Peaking]` 峰值轮廓（`High`/`Mid`/`Low`、`Red`/`Yellow`/`Blue`/`White`）严格仅在机身本地 LCD（`fb0` OSD）渲染、绝不泄漏至外接 HDMI 输出（`0` 辅助像素泄漏，即便 `[HDMI Info. Display] = [On]`）；审计 `Ver. 7.00+/7.02` `[Mode Settings] = [Fixed/Variable]` 对旧版 `[S&Q Settings]` 的锁定关系及 `S&Q` 全部 6 项硬件录制锁止（`0ch` 无音频、`[Audio Out Timing]` 禁用、`[Time Code Run]`/`[Time Code Output]` 禁用、`240/200fps` 禁 4K、`120/100fps` 禁 `XAVC S-I DCI 4K`、`119.88p/100p` 或 `>=100fps` 禁 `[Proxy Recording]`），并验证退出 `S&Q` 与恢复 `CAMSET01..10.DAT` / `Backup.bin` 后 `[Mode Settings]`、`[Audio Out Timing]`（`Live`/`Lip Sync`）、`[Time Code Run]`/`[Time Code Output]` 与 `[Proxy Recording]` 的无漂移恢复及 Tier-0 `16/16 H0 == H3`。
  - **统一 `34/34` 恢复总检聚合器与 CLI（`evaluate_realhw_34pillar_recovery_master` / `verify-34pillar-recovery` / `verify-zebra-fullformat-chord-vault`）**：
    - 并发调用 `evaluate_realhw_33pillar_recovery_master`（`Pillars 1..33`）+ **Pillar 34**（`run_pillar34_standalone_suite`），汇总产出 **`34/34`**（`VERIFIED_34OF34_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_34pillar_zebra_fullformat_chord_vault_verifier.py`](tests/test_realhw_34pillar_zebra_fullformat_chord_vault_verifier.py) 提供 **60 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-zebra-fullformat-chord-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-34pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-34pillar-recovery --force-clean-room --json
```

## Phase 231 — 真机主线 Part 23（里程碑 Pillar 35 / `35/35` 统一恢复总检）：`Silent Mode` `Auto Pixel Mapping` 台架关机防火墙、`Shutter When Pwr OFF` 硬件缺席拦截与 `Marker` / `Flexible Exp.` 复位分流金库（`verify-35pillar-recovery` / `verify-silent-autopixelmap-marker-vault`）

- **[`realhw_35pillar_silent_autopixelmap_marker_vault_verifier.py`](fx3_recovery/realhw_35pillar_silent_autopixelmap_marker_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **`35/35` 里程碑 Pillar 35** 并将全套恢复总检正式推进至 **`35/35`（`VERIFIED_35OF35_PILLAR_RECOVERY_MASTER`）**（`< 3.6s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libInfraMediaConfig.so` 与 `CameraOnDemandSaver.so`（校验 `cam_ondemand_saver_init`、`cam_ondemand_saver_thread`、`cam_ondemand_saver_exit`）7 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 35A — `[Silent Mode]` `[Auto Pixel Mapping]` 台架关机暗场校准防火墙、5 项拍摄功能锁止与 `ILME-FX3` `[Shutter When Pwr OFF]` 硬件缺席拦截（`6/6`）**：
    - `P35A1`..`P35A6`：将 `[Silent Mode] = [On]` 配合 `[Target Function Settings]` 将 `[Auto Pixel Mapping]` 设为 `[Target]` 建模为确定性、非侵入式软件台架关机防火墙，防止在 Tier-0 备份/恢复关机周期中意外触发断电机械快门暗场像素映射校准（`0` 次 `cnflasha` 触碰），同时验证非台架关机场景下 `[Not Target]` 完整保留常规 `[Auto Pixel Mapping]` 与 `[Aperture Drive in AF]` 设定；强制审计 `[Silent Mode] = [On]` 自动锁死 `[Shutter Type]` / `[Shutter Type in Interval] = [Electronic Shutter]`、`[Audio signals] = [Off]` 及 5 项禁用功能（闪光灯拍摄、`[Long Exposure NR]`、`[e-Front Curtain Shut.]`、`BULB`、`[Anti-flicker Shoot.]`）；全面拦截并拒绝物理 `ILME-FX3`（`Ver. 2.00..7.02`）根本不存在的 `[Shutter When Pwr OFF]` 伪造菜单断言（真机仅存在 `[Sensor Cleaning]`、`[Auto Pixel Mapping]` 与 `[Pixel Mapping]`）。
  - **支柱 35B — `[Marker Display]` 15 比例非复位金库、本地 LCD 独占 HDMI 零标记抑制与 `[Flexible Exp. Mode]`（`Av`/`Tv`/`ISO`）+ `[Auto Slow Shutter]` 复位分流（`6/6`）**：
    - `P35B1`..`P35B6`：校验 `[Marker Display]`（`Center Marker`、`Aspect Marker` `Off` + 15 项 `Ver. 3.00+/7.02` 画幅比例、`Safety Zone` `Off/80%/90%`、`Guideframe`）在 `[Camera Settings Reset]` 后完整存留、仅在完整 `[Initialize]` 下清零为 `Off`，且即便 `[HDMI Info. Display] = [On]` 仍严格仅在机身本地监视器显示、向 HDMI 泄漏 `0` 层标记叠加；验证 `[Flexible Exp. Mode]` 下 `[Auto/Manual Swt. Set.]`（`Av`/`Tv`/`ISO` -> `Manual`）与 `[Auto Slow Shutter]`（`-> On`）在 `[Camera Settings Reset]` 下干净复位为默认值，或经 Slot-1 `CAMSET01.DAT` 金库无漂移恢复（`16/16` Tier-0 `H0 == H3`）。
  - **统一 `35/35` 里程碑恢复总检聚合器与 CLI（`evaluate_realhw_35pillar_recovery_master` / `verify-35pillar-recovery` / `verify-silent-autopixelmap-marker-vault`）**：
    - 并发调用 `evaluate_realhw_34pillar_recovery_master`（`Pillars 1..34`）+ **Pillar 35**（`run_pillar35_standalone_suite`），汇总产出 **`35/35`**（`VERIFIED_35OF35_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_35pillar_silent_autopixelmap_marker_vault_verifier.py`](tests/test_realhw_35pillar_silent_autopixelmap_marker_vault_verifier.py) 提供 **64 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-silent-autopixelmap-marker-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-35pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-35pillar-recovery --force-clean-room --json
```

## Phase 234 — 真机主线 Part 24（Pillar 36 / `36/36` 统一恢复总检）：`Recover Image DB` 亏电拒执与 Slot-1 Tier-0 金库防篡改防火墙、`Monitor Flip Direction` 跨复位留存 / 回放不翻转与 `AF` 运动学 + `Interval Shoot Func.` 状态恢复金库（`verify-36pillar-recovery` / `verify-recover-imagedb-monitor-flip-vault`）

- **[`realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier.py`](fx3_recovery/realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 36** 并将全套恢复总检正式推进至 **`36/36`（`VERIFIED_36OF36_PILLAR_RECOVERY_MASTER`）**（`< 3.8s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libInfraMediaConfig.so` 与 `libIMDB.so`（校验 `IMDB_find_entry`、`IMDB_get_entries`、`InfraDatabase_Init`）7 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 36A — `[Recover Image DB]` 极端亏电硬件拒执、零删片 `AVF_INFO` 修复与 Slot-1 Tier-0 金库防写入防火墙（`6/6`）**：
    - `P36A1`..`P36A6`：精确建模 `MENU` -> `Shooting` -> `[Media]` -> `[Recover Image DB]` 在不删除任何已录制视频片段或静态照片的前提下修复 `AVF_INFO` / 媒体管理数据库不一致（消除 `"Image DataBase File error"` 告警与虚假 `"0"` 可拍张数显示）；强制拦截极端亏电 `NP-FZ100` 电池包（`battery_extremely_depleted` 或 `< 10%` / `< 6.60V`）下的执行请求以防中途断电导致 FAT/exFAT 元数据二次损坏；验证 `[Recover Image DB]` 按需动作项对 `[Camera Settings Reset]` 与 `[Initialize]` 双重免疫；并在 **Slot 1** 存有未完成离机 `SHA-256` 校验或处于物理 `WP/LOCK` 保护的 Tier-0 冷转储金库（`pnflasha` / `cnflasha` / `CAMSET01.DAT`）时，100% 阻断 `[Recover Image DB]` 对 Slot 1 文件系统元数据的任何写入。
  - **支柱 36B — `[Monitor Flip Direction]` 跨复位留存与回放零镜像反转、`Movie/S&Q` 对焦运动学（`[AF Subj. Shift Sensitivity]` / `[AF Transition Speed]`）与仅限静态照片的 `[Interval Shoot Func.]` 状态恢复（`6/6`）**：
    - `P36B1`..`P36B6`：校验 `[Monitor Flip Direction]`（`Auto` 默认、`Horizontal Flip`、`Vertical Flip`、`Off`）在 `[Camera Settings Reset]` 后完整保留、仅在完整 `[Initialize]` 下归位为 `Auto`，且即使设为 `[Horizontal Flip]` 时**回放模式绝不翻转监视器画面与时间码/文件名文字**；校验精确全称菜单项 `[AF Subj. Shift Sensitivity]`（`1(Locked on)..5(Responsive)`，默认 `5(Responsive)`，硬拦截缩写 `AF Subj. Shift Sens.`）与 `[AF Transition Speed]`（`1(Slow)..7(Fast)`，默认 `5`）在 `[Camera Settings Reset]` 下干净复位或经 Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT` 无漂移恢复；强制校验 `ILME-FX3` `[Interval Shoot Func.]`（拍摄开始时间 `1s..99m59s`、拍摄间隔 `1s..60s`）严格仅限静态照片序列连拍（需外部后期合成延时视频），阻断将其误判为 FX6 机内视频抽帧 `Interval Rec`（`16/16` Tier-0 `H0 == H3`）。
  - **统一 `36/36` 恢复总检聚合器与 CLI（`evaluate_realhw_36pillar_recovery_master` / `verify-36pillar-recovery` / `verify-recover-imagedb-monitor-flip-vault`）**：
    - 并发调用 `evaluate_realhw_35pillar_recovery_master`（`Pillars 1..35`）+ **Pillar 36**（`run_pillar36_standalone_suite`），汇总产出 **`36/36`**（`VERIFIED_36OF36_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier.py`](tests/test_realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier.py) 提供 **64 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-recover-imagedb-monitor-flip-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-36pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-36pillar-recovery --force-clean-room --json
```

## Phase 238 — 真机主线 Part 25（Pillar 37 / `37/37` 统一恢复总检）：`Touch Operation` 4 项跨复位留存与台架防误触锁、`Emphasized REC` / `Grid Line` HDMI 净信号自动钳制与 `Sunny Weather` 室内电池/热护栏（`verify-37pillar-recovery` / `verify-touch-recframe-hdmi-sunny-vault`）

- **[`realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier.py`](fx3_recovery/realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 37** 并将全套恢复总检正式推进至 **`37/37`（`VERIFIED_37OF37_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35/36pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`（校验 `SaveLoadSettingsIf`、`Backup_read`、`Backup_write`）与 `libgpe.so`（校验 `gpe_blog_error`、`_ZNK5mpgpe5Gperm4InitEv`）7 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室回退：
  - **支柱 37A — `[Touch Operation]` 4 项跨 `[Camera Settings Reset]` 留存、Tier-0 `75 MiB` `p3` 无人值守台架电容屏防误触锁与 `[Monitor Brightness]`（`[Manual]` `-2..+2` vs `[Sunny Weather]`）室内 `NP-FZ100` 电池/热护栏（`6/6`）**：
    - `P37A1`..`P37A6`：精确建模 `MENU` -> `Setup` -> `[Touch Operation]` 全部 4 项设定（`[Touch Operation]` `On`/`On: Playback Only`/`Off`、`[Touch Sensitivity]` `Standard`/`Sensitive`、`[Swipe Up]` `Open the Fn Menu`/`Off`、`[Touch Func. in Shooting]` `Touch Tracking`/`Touch Focus`/`Off`）对 `[Camera Settings Reset]` 免疫留存、仅在完整 `[Initialize]` 下归位为原厂默认；强制在无人值守 Tier-0 `75 MiB` `p3` 冷转储期间锁定 `[Touch Operation] = Off`（或 `On: Playback Only`），阻断意外电容触碰呼出 `Fn` 菜单或触发 `Touch Tracking` / `Touch Focus`（`0` 次误触发）；同时建模 `MENU` -> `Setup` -> `[Monitor]` -> `[Monitor Brightness]`（`Manual` `-2..+2` 默认 `0` vs `Sunny Weather`）跨 `[Camera Settings Reset]` 留存，并将室内 `NP-FZ100` 台架演练硬锁至 `[Manual]`（`0`），杜绝室内高光裁切误判与 LCD 背光额外发热/耗电。
  - **支柱 37B — `[Emphasized REC Display]` 与 `[Grid Line Display]` 复位分流、HDMI 监看路由 vs `[Off(HDMI Only)]` / `RAW` 净信号强制钳制与 Slot-1 `CAMSET01.DAT` 恢复（`6/6`）**：
    - `P37B1`..`P37B6`：校验 `ILME-FX3` `[Emphasized REC Display]`（默认 `On`，可经 `[Camera Settings Reset]` 复位）与 `[Grid Line Display]`（默认 `Off`，含 `Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid` 三种类型，**不受** `[Camera Settings Reset]` 复位、仅在 `[Initialize]` 下归位）的复位不对称；验证 `[HDMI Info. Display] = On`（非 RAW 且启用机内录卡）时自动熄灭机身本地 LCD 并将红框/网格线路由至外接监看器（同时严保本地专属 `Marker`/`Zebra`/`Peaking` 零层泄漏至 HDMI），而在 `[Rec. Media dur HDMI Output] = Off(HDMI Only)` 或 HDMI `RAW` 视频输出激活时由硬件强制钳制 `[HDMI Info. Display] -> Off`（外录 HDMI 母带烘焙 `0` 层红框与网格线，机身 LCD 保持点亮），以及经 Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT` 确定性恢复与 `16/16` Tier-0 `H0 == H3` 不变性。
  - **统一 `37/37` 恢复总检聚合器与 CLI（`evaluate_realhw_37pillar_recovery_master` / `verify-37pillar-recovery` / `verify-touch-recframe-hdmi-sunny-vault`）**：
    - 并发调用 `evaluate_realhw_36pillar_recovery_master`（`Pillars 1..36`）+ **Pillar 37**（`run_pillar37_standalone_suite`），汇总产出 **`37/37`**（`VERIFIED_37OF37_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier.py`](tests/test_realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier.py) 提供 **64 项**双模快速单元测试。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-touch-recframe-hdmi-sunny-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-37pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-37pillar-recovery --force-clean-room --json
```

## Phase 240 — 真机主线 Part 26（Pillar 38 / `38/38` 统一恢复总检）：`Shoe Audio Set.` `24bit 4ch` 三重锁止与四轨电平表联动、`Wind Noise Reduct.` 内置麦独占护栏与 `Save/Load Settings` `C3 Portal` 隐私/校准排除防火墙 + Slot-1 金库写锁（`verify-38pillar-recovery` / `verify-shoe-audio-wind-saveload-vault`）

- **[`realhw_38pillar_shoe_audio_wind_saveload_vault_verifier.py`](fx3_recovery/realhw_38pillar_shoe_audio_wind_saveload_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`）落地 **Pillar 38** 并将全套恢复总检正式推进至 **`38/38`（`VERIFIED_38OF38_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35/36/37pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`（校验 `SaveLoadSettingsIf`、`requestToRead`、`requestToCheck`、`requestToWrite`）与 `FX6 6.01` `appFw.so`、`libInfraHotshoe.so`（校验 `_ZN12InfraHotshoe9GetShoeIdEj`、`_ZN12InfraHotshoe13QueryShoeIdOnEij`、`_ZN12InfraHotshoe11SetAdcLevelEiPj`）8 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室合成回退：
  - **支柱 38A — `[Shoe Audio Set.]`（`48kHz/16bit 2ch` 默认 / `24bit 2ch` / `24bit 4ch`）恢复、三重硬件锁止、`CH1..CH4` 四轨电平表联动与 `[Wind Noise Reduct.]` 仅限内置麦复位 `[Off]` 基线（`6/6`）**：
    - `P38A1`..`P38A6`：精确建模 `MENU` -> `Shooting` -> `[Audio Recording]` -> `[Shoe Audio Set.]` 与 `[Wind Noise Reduct.]` 在 `[Camera Settings Reset]`（及 `[Initialize]`）下分别归位至 `48kHz/16bit 2ch` 与 `Off`，并可经 Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT` `[Load]` 确定性恢复；强制校验 `[Shoe Audio Set.]` 三重硬件锁止：① `[Audio Recording] = Off` 或 `S&Q Motion` 静音锁止（`0ch`、无电平表）；② 机身 `3.5mm` `MIC` 插孔接入模拟外麦时抢占覆盖内置麦与 MI 热靴，强制回落 `2ch 16bit` 模拟采集并禁用数字 `24bit/4ch`；③ `XLR-H1` 手柄物理拨杆置于 `[ANALOG]`（或接入模拟 MI 热靴麦）时绕过数字 I2S 并回落 `2ch 16bit`；同时验证 `XLR-H1`/`ECM-M1` 数字 `48kHz/24bit 4ch` 模式下 `[Audio Level Display] = On` 自动扩展为 `CH1..CH4` 四轨电平表；强制审计 `[Wind Noise Reduct.]` 仅作用于机身内置立体声麦克风（接入 `3.5mm` 外麦或 MI 热靴 `XLR-H1` 时完全不生效，外接手柄改由物理 `[LOW CUT]` `Off`/`100Hz`/`300Hz` 控制），并将室内台架恢复演练硬锁为 `[Off]` 以杜绝正常低频音频被高通衰减。
  - **支柱 38B — `[Save/Load Settings]`（`CAMSET01..10.DAT` & `C3 Portal` `Cloud(Private)` / `Cloud(Share)`）同机型锁、Sony 官方排除隐私/校准项防火墙与 Slot-1 Tier-0 金库写锁（`6/6`）**：
    - `P38B1`..`P38B6`：精确建模 `MENU` -> `Setup` -> `[Reset/Save Settings]` -> `[Save/Load Settings]` 在本地存储卡 `Media`（`/PRIVATE/SONY/PRO/CAMERA/ILME-FX3` 下 `CAMSET01.DAT..CAMSET10.DAT` 单卡上限 `10` 份、严格锁定 `ILME-FX3` 同机型并硬拦截跨机型 `ILME-FX6` `.DAT` 导入）与 `Ver. 4.00+` `Creators' Cloud` / `C3 Portal`（`Cloud(Private)` / `Cloud(Share)`，在气隙 Tier-0 冷转储激活时硬阻断云同步）上的读写边界；强制执行 Sony 官方帮助指南 **8 类排除项防火墙**，确保 `[Save]` 与 `[Load]` 绝不导出或覆写 `[IPTC Information]`、`[Copyright Info]`、`[Custom White Balance]`（`Custom 1..3`）、`[Face Memory]` 人脸生物特征及全部网络凭据（`FTP`、`RTMP/SRT` 推流密钥、`Wi-Fi` SSID/密码、静态 IP/TLS 证书，`excluded_secret_or_cal_leak_count == 0`）；同时强制执行 **Slot-1 Tier-0 金库写锁**：从 Slot 1 执行 `[Load]` 严格 `O_RDONLY` 安全，而任何针对未完成离线 `SHA-256` 校验、处于物理 `WP/LOCK` 保护或存有基线 `pnflasha`/`cnflasha`/`CAMSET01.DAT` 的 Slot 1 金库卡发起的 `[Save]` 覆写均被 100% 阻断（`slot1_unverified_camset_save_mutations == 0`，临时配置 `[Save]` 仅允许落入 Slot 2 或已完成离线哈希验讫的专用测试卡，且严守 `16/16` Tier-0 `H0 == H3` 不变性）。
  - **统一 `38/38` 恢复总检聚合器与 CLI（`evaluate_realhw_38pillar_recovery_master` / `verify-38pillar-recovery` / `verify-shoe-audio-wind-saveload-vault`）**：
    - 并发调用 `evaluate_realhw_37pillar_recovery_master`（`Pillars 1..37`）+ **Pillar 38**（`run_pillar38_standalone_suite`），汇总产出 **`38/38`**（`VERIFIED_38OF38_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_38pillar_shoe_audio_wind_saveload_vault_verifier.py`](tests/test_realhw_38pillar_shoe_audio_wind_saveload_vault_verifier.py) 提供 **66 项**双模快速单元测试（`< 5s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-shoe-audio-wind-saveload-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-38pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-38pillar-recovery --force-clean-room --json
```

## Phase 243 — 真机主线 Part 27（Pillar 39 / `39/39` 统一恢复总检）：`Framing Settings` 非对称 `Full`/`Crop` 恢复与 HDMI `RAW` 裁切互斥、`Anti-flicker Shoot.` 仅机械快门静态照片 / 无 `Var. Shutter` 守恒与 `USB Power Supply` 强制 `NP-FZ100` 在位 + `USB Type-C` 独占 & `USB LUN Setting` `Multi`/`Single` 跨复位留存（`verify-39pillar-recovery` / `verify-framing-usbpower-lun-antiflicker-vault`）

- **[`realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier.py`](fx3_recovery/realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`）落地 **Pillar 39** 并将全套恢复总检正式推进至 **`39/39`（`VERIFIED_39OF39_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35/36/37/38pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libUsbBusPower.so`（校验 `UsbBusPower_Init`、`_ZN11UsbBusPower11GetInstanceEv`、`_ZN11UsbBusPower18SetWatchSWForceOFFEv`）、`libUsbControl.so`（校验 `_ZN15UsbControlDebug9BlogWriteEhhtj`、`_ZN9UsbAdjCmdC1Ev`）与 `FX6 6.01` `appFw.so` 共 9 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室合成回退：
  - **支柱 39A — `[Framing Settings]` 非对称 `Full`/`Crop` 恢复、HDMI `RAW` 裁切互斥、`ILME-FX3`（`ilc/2210`）vs `ZV-E1` 命名锁与 `[Anti-flicker Shoot.]` 仅机械快门静态照片 / 无 `[Var. Shutter]` 守恒（`6/6`）**：
    - `P39A1`..`P39A6`：精确建模 `MENU` -> `Shooting` -> `[Framing Settings]` 三子项（`[Framing]` 默认 `Off` / `On`、`[Recording/Streaming]` 默认 `Full` / `Crop`、`[HDMI]` 默认 `Crop` / `Full`）在 `[Camera Settings Reset]`（及 `[Initialize]`）下干净复位为 `Off`/`Full`/`Crop` 并支持经 Slot-1 `CAMSET01.DAT` `[Load]` 无漂移恢复；强制校验默认非对称双路输出（机内全幅录制 `Full` + 外接 HDMI 构图裁切 `Crop`），100% 阻断 HDMI `RAW` 输出与开启裁切的 `[Framing] = On` 非法并存，并严格区分 `ILME-FX3`（`ilc/2210`，搭配 *Monitor & Control*）的 `[Framing Settings]` 与消费级 `ZV-E1`（`ilc/2310`）的 `[Autoframing Settings]`；同时建模 `MENU` -> `Shooting` -> `[Shutter/Silent]` -> `[Anti-flicker Shoot.]`（默认 `Off` / `On`，受 `[Camera Settings Reset]` 复位）严格仅对 `100 Hz` / `120 Hz` 人工光源下的**机械快门静态照片**生效（在 `Movie` / `S&Q Motion` 视频模式及 `[Silent Mode] = On` / `Electronic Shutter` 下完全不生效），并硬锁定原厂 `ILME-FX3`（`ilc/2210` 直至 `Ver. 7.02`）不存在 `[Var. Shutter]`（`fx3_has_var_shutter == False`，100% 拦截误套用 `FX30` `ilc/2220` `[Var. Shutter]` 或 `FX6` `ECS` 菜单节点的伪造断言，严守 `16/16` Tier-0 `H0 == H3` 不变性）。
  - **支柱 39B — `[USB Power Supply]` 强制 `NP-FZ100` 在位 + `USB Type-C` 供电独占、`[USB LUN Setting]` `Multi`/`Single` 跨 `[Camera Settings Reset]` 留存与离线 `WP` 读卡器 Tier-0 校验金库（`6/6`）**：
    - `P39B1`..`P39B6`：精确建模 `MENU` -> `Setup` -> `[USB]` 全部 3 项设定（`[USB Connection Mode] = Sel. When Connect`、`[USB LUN Setting] = Multi`、`[USB Power Supply] = On`）**在 `[Camera Settings Reset]` 后完整留存**、仅在完整 `[Initialize]` 下复位为出厂默认；强制执行 `[USB Power Supply]` 两大硬件供电互锁：① 电池仓未插入 `NP-FZ100` 电池包（或 `DC-C1` 假电池耦合器）或电池极度亏电（`< 10%`）时无法仅靠 USB 开机供电，且严禁在 USB-PD 供电中途拔出 `NP-FZ100` 触发无缓冲瞬断掉电（`unbuffered_battery_pull_events == 0`）；② 机身 `Multi/Micro USB` 端口在物理电路上绝不支持外部供电或机内充电（仅 `USB Type-C` 独占支持）；同时强制审计 `[USB LUN Setting]` 在 `Multi`（同时挂载 Slot 1 + Slot 2 双盘符 `2 LUN`）与 `Single`（仅暴露主槽 Slot 1 `1 LUN`、隐藏 Slot 2）下的槽位可见性语义，并硬锁定离线气隙读卡器（启用 SDXC 物理 `WP/LOCK` 写保护开关）完成 Tier-0 `SHA-256` 核验（严禁主机 USB 实时在线挂载，`physical_usb_packets_emitted == 0`、`hardware_live_attachment_authorized == False`）。
  - **统一 `39/39` 恢复总检聚合器与 CLI（`evaluate_realhw_39pillar_recovery_master` / `verify-39pillar-recovery` / `verify-framing-usbpower-lun-antiflicker-vault`）**：
    - 并发调用 `evaluate_realhw_38pillar_recovery_master`（`Pillars 1..38`）+ **Pillar 39**（`run_pillar39_standalone_suite`），汇总产出 **`39/39`**（`VERIFIED_39OF39_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier.py`](tests/test_realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 4s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-framing-usbpower-lun-antiflicker-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-39pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-39pillar-recovery --force-clean-room --json
```

## Phase 245 — 真机主线 Part 28（里程碑 Pillar 40 / `40/40` 统一恢复总检）：`Lock Operation Parts` 跨复位留存与 `MENU + Fn` 5s 整机物理防误触锁（严防 `MENU + Delete` 2s 格式化混淆）、`My Dial` 临时解锁、`Audio Out Timing` vs `Audio signals` 复位分流及 `Exposure step` vs `Shutter Angle` 恒定角度表免疫金库（`verify-40pillar-recovery` / `verify-lock-op-parts-audio-timing-exp-step-vault`）

- **[`realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier.py`](fx3_recovery/realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`）落地 **`40/40` 里程碑 Pillar 40** 并将全套恢复总检正式推进至 **`40/40`（`VERIFIED_40OF40_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35/36/37/38/39pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so` 与 `FX6 6.01` `appFw.so`、`libInfraDial.so`（校验 `_ZN9InfraDial4InitEv`、`_ZN9InfraDial10set4KeyInhEb`、`_ZN10InfraInput12SetKeyInhExtEibi`）、`libInfraInput.so`（校验 `_ZN14InfraInputBase14KeyConfigAllocEi`、`_ZN14InfraInputBase13KeyConfigFreeEv`、`_ZN14InfraInputBase7SuspendEv`）共 10 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动洁净室合成回退：
  - **支柱 40A — `[Lock Operation Parts]` 跨 `[Camera Settings Reset]` 留存、`Fn` 长按提示、`MENU + Fn` 5s 整机物理键锁（严防 `MENU + Delete` 2s 全盘格式化混淆）与 `My Dial` 临时解锁台架金库（`6/6`）**：
    - `P40A1`..`P40A6`：精确建模 `MENU` -> `Setup` -> `[Dial Customize]` -> `[Lock Operation Parts]` 四态（默认 `Off`、`Multi-Selector Only` / `Multi-Slct Only`、`Dial + Wheel`、`All`）作为 `[Setup]` 项**在 `[Camera Settings Reset]` 后完整留存**、仅在完整 `[Initialize]` 下归位为 `Off`，并支持经 Slot-1 `CAMSET01.DAT` `[Load]` 确定性恢复；强制校验三大物理按键与覆盖规则：① 长按 `Fn` 触发目标范围锁定并弹出 `"Locked."`（`Off` 时长按 `Fn` 不锁定任何控件）；② 同时按住 **`MENU + Fn` 满 `5` 秒**锁定/解锁**除快门按钮外的全部机身按键、拨盘与控制拨轮**，为无人值守 Tier-0 `pnflasha`/`cnflasha` 冷转储提供物理防误触锁，并 **100% 阻断将其与破坏性 `MENU + Delete` `2` 秒卡槽全盘格式化组合键混淆**（`destructive_menu_delete_confusions == 0`）；③ 即便拨盘/控制拨轮已被 `[Lock Operation Parts]` 锁定，按住 **`My Dial`** 期间仍临时解锁已分配拨盘并在松开后立即恢复锁定（严守 `16/16` Tier-0 `H0 == H3` 不变性）。
  - **支柱 40B — `[Audio Out Timing]`（`Live`/`Lip Sync`）vs `[Audio signals]` 复位非对称留存、`S&Q` / `Silent Mode` 硬件锁止与 `[Exposure step]`（`0.3EV`/`0.5EV`）vs `[Shutter Angle]` 恒定电影快门角度表免疫恢复（`6/6`）**：
    - `P40B1`..`P40B6`：精确建模 `MENU` -> `Shooting` -> `[Audio Recording]` -> `[Audio Out Timing]`（默认 `Live` 零延迟监听 vs `Lip Sync` 音画同步延迟，受 `[Camera Settings Reset]` 复位为 `Live`，并在 `S&Q Motion` 慢快动作或 `[Audio Recording] = Off` 时硬件锁止不可用）与 `MENU` -> `Setup` -> `[Sound Option]` -> `[Audio signals]`（默认 `On` / `Off`，**跨 `[Camera Settings Reset]` 完整留存**、仅由 `[Initialize]` 复位，但在 **`[Silent Mode] = On` 时被硬件强制锁死为 `Off`**）之间的复位与锁止边界；同时建模 `MENU` -> `Exposure/Color` -> `[Exposure Comp.]` -> `[Exposure step]`（默认 `0.3EV` / `0.5EV`，受 `[Camera Settings Reset]` 复位）仅调节 `[Shutter Speed]`、光圈（`Aperture`）与曝光补偿（`Exposure Comp.`）步进，而 **`Ver. 6.00+`..`7.02` `[Shutter Mode] = [Shutter Angle]` 下的 `[Shutter Angle]` 对 `[Exposure step]` 100% 免疫、严格保持恒定电影快门角度表**（`5.6°`..`360°`，`shutter_angle_exposure_step_drift_events == 0`），并支持经 Slot-1 `CAMSET01.DAT` `[Load]` 无损恢复。
  - **统一 `40/40` 里程碑恢复总检聚合器与 CLI（`evaluate_realhw_40pillar_recovery_master` / `verify-40pillar-recovery` / `verify-lock-op-parts-audio-timing-exp-step-vault`）**：
    - 并发调用 `evaluate_realhw_39pillar_recovery_master`（`Pillars 1..39`）+ **Pillar 40**（`run_pillar40_standalone_suite`），汇总产出 **`40/40`**（`VERIFIED_40OF40_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier.py`](tests/test_realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 4s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-lock-op-parts-audio-timing-exp-step-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-40pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-40pillar-recovery --force-clean-room --json
```

## Phase 247 — 真机主线 Part 29（Pillar 41 / `41/41` 统一恢复总检）：`Display Quality` `Standard`/`High` 跨双复位留存与 `NP-FZ100` 台架节能钳制、`Bluetooth Rmt Ctrl` 红外遥控互斥锁与 `Reset Network Set.` 三向复位分流及 `My Menu Setting` 6 操作持久化 + `CAMSET01.DAT` 无损往返金库（`verify-41pillar-recovery` / `verify-display-quality-bt-rmt-mymenu-vault`）

- **[`realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier.py`](fx3_recovery/realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`）落地 **Pillar 41** 并将全套恢复总检正式推进至 **`41/41`（`VERIFIED_41OF41_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22/24/26/27/28/29/30/31/32/33/34/35/36/37/38/39/40pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`libInfraBluetooth.so`（校验 `_ZN14InfraBluetoothC1Ev`、`_ZN14InfraBluetooth12start_threadEv`、`_ZN14InfraBluetooth11register_cbEv`）、`libInfraAirplaneMode.so`（校验 `_Z23AirplaneModeTraceRecordhhtj`、`_Z28AirplaneModeTraceRecordErrorhhtj`）与 `FX6 6.01` `appFw.so`、`libInfraSircs.so`（校验 `_ZN10InfraSircs4InitEv`、`_ZN10InfraSircs11GetInstanceEv`、`_ZN10InfraSircs15SetSircsOffTimeEi`）共 11 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动洁净室合成回退：
  - **支柱 41A — `[Display Quality]`（`Standard`/`High`）跨双复位留存与 `NP-FZ100` 台架省电钳制 + `[Bluetooth Rmt Ctrl]` 红外遥控互斥锁、零射频抑制与三向复位分流（`6/6`）**：
    - `P41A1`..`P41A6`：精确建模 `MENU` -> `Setup` -> `[Monitor]` -> `[Display Quality]`（默认 `Standard` / `High`，开启 `[High]` 会显著增加 `NP-FZ100` 电池功耗）**同时跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存**、仅在完整 `[Initialize]` 下归位为 `Standard`，并支持经 Slot-1 `CAMSET01.DAT` `[Load]` 确定性恢复；在机内 `NP-FZ100` 电池驱动的 Tier-0 `pnflasha`/`cnflasha` 冷转储台架期间，强制将 `[Display Quality]` 钳制为 `[Standard]` 且配合 `[Monitor Brightness] = [Manual](0)`（`tier0_battery_high_display_violations == 0`）；同时建模 `MENU` -> `Network` -> `[Bluetooth]` -> `[Bluetooth Rmt Ctrl]`（默认 `Off` / `On`）的三项硬件规则：① 依赖 `[Bluetooth Function] = On` 且 `[Airplane Mode] = Off`（在零射频台架 `[Airplane Mode] = On` 下硬抑制发射、`passive_tx_bytes_emitted == 0`）；② 当 `[Bluetooth Rmt Ctrl] = [On]` 时，硬件**强制互斥锁定红外遥控器（`SIRCS` 不可用，`bt_rmt_ir_lockout_violations == 0`）**；③ 严格执行三向复位分流——**跨越 `[Camera Settings Reset]` 留存，但在 `[Reset Network Set.]` 与 `[Initialize]` 下均复位至 `[Off]`**（严守 `16/16` Tier-0 `H0 == H3` 不变性）。
  - **支柱 41B — `[My Menu Setting]` / `[Display From My Menu]` 6 操作状态机持久化、双复位留存与 Slot-1 `CAMSET01.DAT` `O_RDONLY` 无损往返金库（`6/6`）**：
    - `P41B1`..`P41B6`：精确建模 `MENU` -> `My Menu` -> `[My Menu Setting]` 全部 6 项子操作（`Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All` 及 `[Display From My Menu]` 默认 `Off` 打开最近页签 vs `On` 优先打开 `My Menu`，上限 `5` 页 × 每页 `6` 项 = `30` 项）；验证已注册的 `My Menu` 条目与 `[Display From My Menu]` **同时跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存**，仅通过 `[Delete All]` / `[Delete Page]` 或完整 `[Initialize]` 清空归零；验证经 `O_RDONLY` + SDXC 物理 `WP` 锁保护的 Slot 1 `CAMSET01.DAT` `[Load]` 可无损往返恢复全部 `My Menu` 页面与 `[Display From My Menu]` 状态，且 100% 阻断跨机型 `ILME-FX6` 导入及对 Slot 1 Tier-0 金库扇区的任何 `[Save]` 覆写或可变挂载（`slot1_mymenu_vault_mutation_bytes == 0`，`16/16` Tier-0 `H0 == H3`）。
  - **统一 `41/41` 恢复总检聚合器与 CLI（`evaluate_realhw_41pillar_recovery_master` / `verify-41pillar-recovery` / `verify-display-quality-bt-rmt-mymenu-vault`）**：
    - 并发调用 `evaluate_realhw_40pillar_recovery_master`（`Pillars 1..40`）+ **Pillar 41**（`run_pillar41_standalone_suite`），汇总产出 **`41/41`**（`VERIFIED_41OF41_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier.py`](tests/test_realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 4s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-display-quality-bt-rmt-mymenu-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-41pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-41pillar-recovery --force-clean-room --json
```

## Phase 251 — 真机主线 Part 30（Pillar 42 / `42/42` 统一恢复总检）：`Different Set for Still/Mv` 8 项非对称状态跃迁与 `Shutter Angle` 独立解耦、`Custom Key/Dial Set.` 三域键位 / `ISO/EI` 持久化及 `Remain Shoot Display` 连拍缓存边界 + 无 EVF 监视拓扑金库（`verify-42pillar-recovery` / `verify-diff-set-still-mv-custom-key-remain-shoot-vault`）

- **[`realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier.py`](fx3_recovery/realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-40）落地 **Pillar 42** 并将全套恢复总检正式推进至 **`42/42`（`VERIFIED_42OF42_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22..41pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`（校验 `CameraOnDemandSaver`、`_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji`）与 `FX6 6.01` `appFw.so`、`libInfraDial.so`（校验 `InfraDial`、`InfraDialEventDataRecord`、`INFRA_DIAL_UIPC_SETDIALEVENTINTERVAL`）、`libInfraInput.so`（校验 `InfraInput`、`ApiGetKeySta`、`ApiSetKeyInh`）共 11 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动洁净室合成回退：
  - **支柱 42A — `[Different Set for Still/Mv]` 8 项非对称跃迁、跨双复位留存与 `Ver. 7.02` `[Shutter Mode] = [Angle]` 独立解耦（`6/6`）**：
    - `P42A1`..`P42A6`：精确建模 `MENU` -> `Setup` -> `[Operation Customize]` -> `[Different Set for Still/Mv]` 全部 8 项可勾选参数（`Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`），校验勾选集**同时跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存**、仅在 `[Initialize]` 下归位为未勾选出厂默认（并支持经 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 恢复）；严格校验两项索尼非对称硬件状态跃迁规则（`diff_set_transition_corruption_events == 0`）：① **Common -> Separate**：当前值同时复制到照片与视频寄存器，**唯独 `Custom White Balance` 仅作用于照片拍摄、不复制到视频**；② **Separate -> Common**：各参数回归初始出厂默认，**唯独 `Aperture`、`Shutter Speed` 与 `Custom White Balance` 保留照片端设定值**；同时强制执行 `Ver. 6.00+` / `Ver. 7.02` **`[Shutter Mode] = [Angle]`** 硬件规则——当视频快门设为 `[Angle]`（快门角度）时，即便 `Shutter Speed` 在 `[Different Set for Still/Mv]` 中未勾选（设为通用 Common），照片快门速度与视频快门角度仍作为独立寄存器运行、绝不串写（`shutter_angle_common_bleed_events == 0`）。
  - **支柱 42B — `[Custom Key/Dial Set.]` 三域键位 / `ISO/EI` 自适应持久化与 `[Remain Shoot Display]` 连拍缓存边界 + 无 EVF 拓扑金库（`6/6`）**：
    - `P42B1`..`P42B6`：精确建模 `MENU` -> `Setup` -> `[Operation Customize]` -> `[Custom Key/Dial Set.]`（照片/视频/回放三域独立键位、`Custom Button 1..6` + 多功能选择器 + 镜头对焦保持按钮，以及电影机线出厂三拨轮默认：`Front dial = Aperture`、`Rear dial = ISO/EI` 在 `Flexible ISO` 与 `Cine EI` / `Cine EI Quick` 间自动切换 `ISO` 与 `Exposure Index (EI)`、`Control Wheel = Shutter Speed`、`[Follow Custom]` 视频继承照片键位、`[My Dial 1..3]` 与 `[Recall Custom hold 1..3]`）跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存，以及经 `O_RDONLY` + SDXC `WP` 物理锁保护的 Slot-1 `CAMSET01.DAT` `[Load]` 无损往返恢复（`slot1_custom_key_vault_mutation_bytes == 0`）；同时建模 `MENU` -> `Setup` -> `[Display Option]` -> `[Remain Shoot Display]`（默认 `Not Displayed` / `Always Display` / `Shoot-Only Display`）仅面向**照片连拍缓存余量**（绝不混淆视频存储卡剩余录制时长）、跨越双复位留存，并强制锚定 `ILME-FX3`（`ilc/2210`）无内置 EVF 与无 `[Finder/Monitor]` 眼控切换的纯翻转屏监视拓扑（`fx3_has_builtin_evf == False`、`evf_finder_monitor_spoof_events == 0`、`16/16` Tier-0 `H0 == H3`）。
  - **统一 `42/42` 恢复总检聚合器与 CLI（`evaluate_realhw_42pillar_recovery_master` / `verify-42pillar-recovery` / `verify-diff-set-still-mv-custom-key-remain-shoot-vault`）**：
    - 并发调用 `evaluate_realhw_41pillar_recovery_master`（`Pillars 1..41`）+ **Pillar 42**（`run_pillar42_standalone_suite`），汇总产出 **`42/42`**（`VERIFIED_42OF42_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier.py`](tests/test_realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 3.5s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-diff-set-still-mv-custom-key-remain-shoot-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-42pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-42pillar-recovery --force-clean-room --json
```

## Phase 255 — 真机主线 Part 31（Pillar 43 / `43/43` 统一恢复总检）：`Auto Slow Shutter` 6 条件禁能与 `Shutter Angle` 严格互斥、`HDMI Output Settings` `REC Control` <- `Time Code Output` 门控与 `4ch Audio Output` 路由 + `Breathing Comp.` 边界金库（`verify-43pillar-recovery` / `verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault`）

- **[`realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier.py`](fx3_recovery/realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-41）落地 **Pillar 43** 并将全套恢复总检正式推进至 **`43/43`（`VERIFIED_43OF43_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22..42pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`、`libInfraLensCommunicator.so`（校验 `LensCommunicator`、`_Z23LensCommunicator_CreatePN3MWF5ErrCdE`）、`libInfraMediaConfig.so`（校验 `InfraMediaConfig`、`_ZN16InfraMediaConfig10SaveBackupEt`）与 `FX6 6.01` `appFw.so`、`libInfraHotshoe.so`（校验 `InfraHotshoe`、`_ZN12InfraHotshoe15ResourceToInfraEi`）共 12 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动洁净室合成回退：
  - **支柱 43A — `[Auto Slow Shutter]` 6 条件硬件禁能、`Ver. 7.02` `[Shutter Mode] = [Angle]` 严格互斥与 `[Breathing Comp.]` 电影/镜头/RAW/240p 边界（`6/6`）**：
    - `P43A1`..`P43A6`：精确建模 `MENU` -> `Exposure/Color` -> `[Exposure]` -> `[Auto Slow Shutter]`（默认 `On` / `Off`，受 `[Camera Settings Reset]` 与 `[Initialize]` 归位为 `On`、跨越 `[Reset Network Set.]` 留存），强制校验全部 **6 项索尼官方不生效/禁能硬件条件**（`auto_slow_shutter_lockout_bypass_events == 0`）：① `S&Q` 慢快动作、② 快门优先（`S`）、③ 手动曝光（`M`）、④ `[ISO]` 非 `[ISO AUTO]`（固定手动 ISO）、⑤ `[Flexible Exp. Mode]` 手动快门速度、⑥ `[Log Shooting]` = `Cine EI Quick` 或 `Cine EI`；同时从硬件状态空间证明 `Ver. 6.00+` / `Ver. 7.02` **`[Shutter Mode] = [Angle]`**（仅在 `S`/`M`/`Flexible Exp. Mode` 手动快门下接管曝光时间）与 `[Auto Slow Shutter]` **100% 严格互斥、零交叠**（`auto_slow_shutter_angle_overlap_events == 0`）；建模 `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[Lens Compensation]` -> `[Breathing Comp.]`（默认 `Off` / `On`，受 `[Camera Settings Reset]` 归位），强制校验仅限视频（不作用于照片）、需兼容呼吸补偿的索尼 E 卡口镜头并施加轻微视角裁切，且在 `4264x2408` `RAW Output` 与 `S&Q` `239.76p`/`200p` 下严格锁定（`breathing_comp_raw_or_240p_bypass_events == 0`）。
  - **支柱 43B — `[HDMI Output Settings]`（`[REC Control]` <- `[Time Code Output]` 前置门控、`[4ch Audio Output]` 声道映射与 `[Rec. Media dur HDMI Output]` 护栏金库）（`6/6`）**：
    - `P43B1`..`P43B6`：精确建模 `MENU` -> `Setup` -> `[External Output]` -> `[HDMI Output Settings]` **同时跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存**、仅由 `[Initialize]` 清零归位；强制执行 `[REC Control]`（默认 `Off` / `On`）必须以 **`[Time Code Output] = [On]`** 为硬件前置条件（`hdmi_rec_ctrl_without_tc_violations == 0`）；建模 `[4ch Audio Output]`（默认 `CH1/CH2` -> `Ch1=L / Ch2=R` vs 启用 4 声道 MI 热靴音频时 `CH3/CH4` -> `Ch3=L / Ch4=R`）；强制校验 `[Rec. Media dur HDMI Output] = [Off]` 在 HDMI 输出期间同步抑制机内 Slot-1/Slot-2 主片与 `[Proxy Recording]` 代理写入以保护 Slot-1 Tier-0 恢复金库介质（`slot1_hdmi_rec_vault_mutation_bytes == 0`）、`O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 无损往返恢复，以及 `16/16` Tier-0 `Backup.bin` `H0 == H3` 不变性。
  - **统一 `43/43` 恢复总检聚合器与 CLI（`evaluate_realhw_43pillar_recovery_master` / `verify-43pillar-recovery` / `verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault`）**：
    - 并发调用 `evaluate_realhw_42pillar_recovery_master`（`Pillars 1..42`）+ **Pillar 43**（`run_pillar43_standalone_suite`），汇总产出 **`43/43`**（`VERIFIED_43OF43_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier.py`](tests/test_realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 3.5s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-43pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-43pillar-recovery --force-clean-room --json
```

## Phase 260（第 260 阶段里程碑）— 真机主线 Part 32（Pillar 44 / `44/44` 统一恢复总检）：`APS-C S35 Shooting` `12.1MP` `4K` 视频硬锁定、`Face/Eye AF` 左右眼选择与纯净 HDMI 隔离 + `Version` 只读巡检 vs `BODYDATA.DAT` 刷写硬阻断金库（`verify-44pillar-recovery` / `verify-apsc-s35-face-eye-af-version-vault`）

- **[`realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier.py`](fx3_recovery/realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-42）落地 **Phase 260（`260th` Phase Milestone）Pillar 44** 并将全套恢复总检正式推进至 **`44/44`（`VERIFIED_44OF44_PILLAR_RECOVERY_MASTER`）**（`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22..43pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`、`libInfraLensCommunicator.so`、`libInfraGetVersion.so`（校验 `InfraGetVersion`、`InfraGetVersionLens`、`GetVersion_init`）、`libInfraAirplaneMode.so`（校验 `infra_airplane_mode_init`、`_ZN3MWF6InhMgr15UpdateInhFactorEv`）、`libupdatermedia.so`（校验 `udtr_get_media_path`、`UDTR_MEDIA`）与 `FX6 6.01` `appFw.so` 共 13 项供体（`< 0.15s`）并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动洁净室合成回退：
  - **支柱 44A — `[APS-C S35 Shooting]` `12.1MP` 传感器 `4K` 视频与 `4264x2408` `HDMI RAW` 硬锁定 + `[Face/Eye AF]` 左右眼选择、纯净 HDMI 隔离与 `[Face Memory]` 留存（`6/6`）**：
    - `P44A1`..`P44A6`：精确建模 `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[APS-C S35 Shooting]`（默认 `Auto` / `On` ~`1.5x` Super 35mm / `Off` 35mm 全画幅，受 `[Camera Settings Reset]` 与 `[Initialize]` 归位为 `Auto`、跨越 `[Reset Network Set.]` 留存），强制执行 `ILME-FX3`（`12.1MP` 全画幅传感器：`4240x2832` 静态 / `3840x2160` 1:1 `4K` 读出）硬件边界——在录制 **`4K` 视频（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`）或 `4264x2408` `HDMI RAW Output`** 时禁用并强制锁定为 **`[Off]`**，Super 35mm 视频采集**仅限 `HD`（`XAVC S HD` / `XAVC S-I HD`）**（`apsc_s35_4k_or_raw_bypass_events == 0`，严格区分 `ILME-FX3` 与原生 S35 `ILME-FX30` 及超采样 `ILCE-7RM5`/`ILCE-7M4`）；建模 `MENU` -> `Focus` -> `[Face/Eye AF]`（拒绝伪造独立 AI 芯片机型的 `[Subject Recog in AF]`，`ai_unit_subject_recog_spoof_events == 0`：`[Face/Eye Prior. in AF]`、`[Face/Eye Subject]` `Human`/`Animal`/`Ver. 3.00+ Bird`、`[Right/Left Eye Select]` + `[Switch Right/Left Eye]` 自定义键切换、`[Face/Eye Frame Disp.]`），强制证明 `[HDMI Info. Display] = [Off]` 纯净 HDMI 与 `HDMI RAW Output` 零像素烧录对焦框（`hdmi_clean_feed_eye_frame_baked_pixels == 0`），以及已注册 `[Face Memory]` 人脸库跨越 `[Camera Settings Reset]` 完整留存（仅由显式删除或 `[Initialize]` 清空）。
  - **支柱 44B — `[Version]` 只读机身/镜头/转接环版本巡检、零射频红点更新提示抑制与 Slot-1 `BODYDATA.DAT` 刷写硬阻断金库（`6/6`）**：
    - `P44B1`..`P44B6`：精确建模 `MENU` -> `Setup` -> `[Setup Option]` -> `[Version]` 以严格 `O_RDONLY` 模式巡检 `ILME-FX3` Body（`Ver. 7.02`）、E 卡口镜头与卡口转接环固件版本，全流程零分区写入（`version_dialog_flash_writes == 0`）且固件版本跨越 `[Camera Settings Reset]`、`[Reset Network Set.]` 与 `[Initialize]` 恒定不变；强制验证零射频 `Airplane Mode = On` 台架下抑制 `Ver. 6.00+` / `7.02` 红色固件更新提示角标且零被动射频发包（`passive_tx_bytes_emitted == 0`）；对一切自动化 Slot-1 `BODYDATA.DAT` 固件刷写请求实施无条件硬阻断（`persistent_emmc_writes_authorized == False`、`bodydata_flash_attempts_blocked >= 1`、`slot1_bodydata_vault_mutation_bytes == 0`，并校验人工物理台架前置门槛 `NP-FZ100 >= 3 格 / >= 51%` 与原厂签名 `ILME-FX3` 镜像边界），同时验证 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 无损往返与 `16/16` Tier-0 `Backup.bin` `H0 == H3` 不变性。
  - **统一 `44/44` 恢复总检聚合器与 CLI（`evaluate_realhw_44pillar_recovery_master` / `verify-44pillar-recovery` / `verify-apsc-s35-face-eye-af-version-vault`）**：
    - 并发调用 `evaluate_realhw_43pillar_recovery_master`（`Pillars 1..43`）+ **Pillar 44**（`run_pillar44_standalone_suite`），汇总产出 **`44/44`**（`VERIFIED_44OF44_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier.py`](tests/test_realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier.py) 提供 **68 项**双模快速单元测试（`< 3.5s`）。

```sh
PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-apsc-s35-face-eye-af-version-vault --json

PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-44pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-44pillar-recovery --force-clean-room --json
```

## Phase 265（`45/45` 大里程碑）— 真机主线 Part 33（Pillar 45 / `45/45` 统一恢复总检）：`Release w/o Card` & `Release w/o Lens` 台架/实拍双姿态护栏、`Ver. 7.02` 5 项 `Audio Recording` vs `DISP` 音频电平表 + `Copyright Info` 46 字符静态 EXIF 隔离与洁净室 PII 清零金库（`verify-45pillar-recovery` / `verify-release-wo-card-lens-audio-meter-copyright-vault`）

- **[`realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier.py`](fx3_recovery/realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-43）落地 **Phase 265（Grand Milestone `45/45`）Pillar 45** 并将全套恢复总检正式推进至 **`45/45`（`VERIFIED_45OF45_PILLAR_RECOVERY_MASTER`）**（`< 1.8s` 进程内预算、`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22..44pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`、`libInfraLensCommunicator.so`、`libInfraMediaConfig.so`、`libInfraMediaDetect.so`（校验 `InfraMediaDetect`、`_ZN16InfraMediaDetect10GetVersionEv`）、`libInfraMetaSupplier.so`（校验 `InfraMetaSupplier_Init`、`_ZN20InfraMetaSupplier_If4InitEv`）、`libInfraIPTC.so`（校验 `_ZTV9InfraIPTC`、`_ZN9InfraIPTC10ThreadStopEv`）与 `FX6 6.01` `appFw.so`、`libInfraHotshoe.so` 共 15 项供体（`< 0.15s`），并同时支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 45A — `[Release w/o Card]` 仅静态快门作用域 vs 视频内录介质门控、`[Release w/o Lens]` 无内置电子 ND / 零镜头 UART 裸机台架与 `Ver. 7.02` 5 项 `[Audio Recording]` vs `DISP` 音频电平表（`6/6`）**：
    - `P45A1`..`P45A6`：精确建模 `MENU` -> `Shooting` -> `[Shutter/Silent]` -> `[Release w/o Card]`（出厂默认 `Enable` / `Disable`）与 `[Release w/o Lens]`（出厂默认 `Enable` / `Disable`）跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存、仅由 `[Initialize]` 复位为 `Enable`（并支持 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 无损恢复）；在 `768` 组合笛卡尔状态空间下实证 **`[Release w/o Card]` 仅控制无卡静态快门释放**——视频（`Movie`）与慢快动作（`S&Q`）机内录制始终强制要求已插入存储卡且受 `[Rec. Media dur HDMI Output]` 门控，同时强制区分无卡只读诊断台架（`CARDLESS_DIAGNOSTIC_BENCH`）与正式实拍防漏录姿态（`PRODUCTION_SHOOT` 强制 `[Release w/o Card] = [Disable]`，`cardless_unrecorded_production_violations == 0`）；实证 `[Release w/o Lens]` 同时覆盖 `Still` + `Movie` + `S&Q`，且在裸机机身盖 / 纯机械 PL 转接环 / 望远镜台架上严格锁定无内置电子 ND 与零 E 卡口镜头串口发包（`fx3_has_builtin_end_filter == False`、`e_nd_actuator_tx_count == 0`、`emount_lens_uart_tx_bytes == 0`）；同时强制锚定 `Ver. 2.00+` / `Ver. 7.02`（`ilc/2210`）精确 5 项 `[Audio Recording]` 菜单（`Audio Recording`、`Audio Rec Level` `0..31`、`Audio Out Timing` `Live`/`Lip Sync`、`Wind Noise Reduct.`、`Shoe Audio Set.`），拒绝伪造 `Ver. 1.x`（`ilc/2035`）已移除的独立 `[Audio Level Display]` 菜单项（`legacy_v1_audio_level_menu_spoof_events == 0`），证明屏幕音频电平表（`2ch` 或 MI 数字热靴 `4ch`，`S&Q` 下自动消隐）统一由 `MENU` -> `Setup` -> `[Operation Customize]` -> `[DISP (Screen Disp) Set]` 控制。
  - **支柱 45B — `[Copyright Info]` `<= 46` 字符可打印 ASCII 边界、仅静态 JPEG/HEIF EXIF 作用域、`[Camera Settings Reset]` 留存 vs `[Initialize]` 清空与洁净室 PII 零泄漏金库（`6/6`）**：
    - `P45B1`..`P45B6`：精确建模 `MENU` -> `Shooting` -> `[File]` -> `[Copyright Info]` 全部 4 项子菜单（`Write Copyright Info` 默认 `Off`/`On`、`Set Photographer`、`Set Copyright`、`Disp. Copyright Info` `O_RDONLY` 零闪存写入预览），强制执行 `<= 46` 字符可打印 ASCII（`0x20..0x7E`）边界并拦截 `>= 47` 字符溢出、控制字符与非 ASCII 注入；强制验证 `[Copyright Info]` **仅写入静态照片（`JPEG` / `HEIF` / `RAW+JPEG` / `RAW+HEIF`）EXIF 元数据**，绝不篡改任何 `XAVC HS/S/S-I` 或 `4264x2408` `HDMI RAW` 视频流（`movie_xavc_or_raw_copyright_mutated == False`、`copyright_char_overflow_or_movie_mutation_events == 0`）；验证 `[Camera Settings Reset]` 将 `[Write Copyright Info]` 复位为 `[Off]` 但完整保留已登记摄影师/版权字符串，而 `[Initialize]` 同时彻底清空两项字符串；强制执行 `CAMSET01..10.DAT` 版权排除防火墙、Slot-1 Tier-0 金库写保护锁（`slot1_copyright_vault_mutation_bytes == 0`、`16/16` Tier-0 `Backup.bin` `H0 == H3`）以及洁净室测试操作员 PII 零残留（`photographer_copyright_pii_leaked_bytes == 0`）。
  - **统一 `45/45` 恢复总检聚合器与 CLI（`evaluate_realhw_45pillar_recovery_master` / `verify-45pillar-recovery` / `verify-release-wo-card-lens-audio-meter-copyright-vault`）**：
    - 并发调用 `evaluate_realhw_44pillar_recovery_master`（`Pillars 1..44`）+ **Pillar 45**（`run_pillar45_standalone_suite`），汇总产出 **`45/45`**（`VERIFIED_45OF45_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier.py`](tests/test_realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier.py) 提供 **70 项**双模快速单元测试（实测 `1.94s`–`2.31s` < `4.0s`）。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-release-wo-card-lens-audio-meter-copyright-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-45pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-45pillar-recovery --clean-room --json
```

## Phase 269 — 真机主线 Part 34（Pillar 46 / `46/46` 统一恢复总检）：视频 `File Settings`（`Cam ID + Reel#` 与 `37` 字符 `Title Name`）vs 静态 `File/Folder Settings`（`DSC` 前缀与 `Slot-1` 金库防火墙）、`Gamma Display Assist` `Log Shooting` 锁定 vs `Display LUT`/`Select LUT`、`Auto Review` `Off` 默认与 `6` 项 `TC/UB` 非重置留存（`verify-46pillar-recovery` / `verify-file-settings-gamma-assist-tcub-vault`）

- **[`realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier.py`](fx3_recovery/realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-44）落地 **Phase 269 Pillar 46（`46/46`）** 并将全套恢复总检推进至 **`46/46`（`VERIFIED_46OF46_PILLAR_RECOVERY_MASTER`）**（`< 1.9s` CLI 运行预算、`< 4.0s` 标称、`< 6.0s` 并发硬上限，保持 `verify-22..45pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` `BODYDATA.DAT`、`appFw.so`、`Backup.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`、`libInfraMediaConfig.so`、`libInfraMediaDetect.so`、`libInfraMediaCommon.so`、`libInfraMediaMount.so`、`libInfraFsys.so`、`libInfraMetaSupplier.so` 与 `FX6 6.01` `appFw.so`、`libInfraSetupFile.so` 共 16 项供体（`< 0.15s`），并同时支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 46A — 视频 `[File Settings]`（`Cam ID + Reel#` & `37` 字符 `Title Name`）vs 静态 `[File/Folder Settings]`（`DSC` 前缀与 `Slot-1` 金库 DCIM 防火墙）（`6/6`）**：
    - `P46A1`..`P46A6`：精确建模 `MENU` -> `Shooting` -> `[File]` -> `[File Settings]`（`File Number` `Series`/`Reset`、`Series Counter Reset`、`File Name Format` `Standard`/`Cam ID + Reel#`（`Camera ID` `A..Z`、`Reel Number` `001..999`、`Camera Position` `C`/`L`/`R`）/`Title`/`Date + Title`/`Title + Date`、`Title Name Settings` `<= 37` 字符默认 `"C"`、固定 `PRIVATE/M4ROOT/CLIP` 不可自定义视频目录）与 `[File/Folder Settings]`（`File Number` `Series`/`Reset`、`Forced File Number Reset`、`Set File Name` 默认 `"DSC"` `3` 字符 `A-Z`/`0-9`/`_` 且首位禁止 `_`、`Folder Name` `Standard Form` `100MSDCF` vs `Date Form`）；验证二者全部子项均跨越 `[Camera Settings Reset]` 留存、仅随 `[Initialize]` 恢复出厂默认，并支持 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 无损回放；同时在 `Slot 1` 持有只读 `CAMSET`/`BODYDATA.DAT` 恢复金库时硬拦截 `[Forced File Number Reset]` 与 `[Create New Folder]` 对 `Slot 1` DCIM 目录表的任何写入/变更（`slot1_vault_folder_mutation_events == 0`、`slot1_vault_folder_mutation_bytes == 0`）。
  - **支柱 46B — `[Gamma Display Assist]` `[Log Shooting]` 硬锁定 & 机内 LCD 专属作用域 vs `[Display LUT]`/`[Select LUT]`、`[Auto Review]` `Off` 默认与 `6` 项 `[TC/UB]` 非重置留存（`6/6`）**：
    - `P46B1`..`P46B6`：精确建模 `MENU` -> `Setup` -> `[Display Option]` -> `[Gamma Display Assist]`（默认 `Off` / `On`、`Gamma Disp. Assist Typ.` 默认 `Auto` / `S-Log3->709(800%)` / `HLG(BT.2020)` / `HLG(709)`）在 `[Log Shooting] != Off`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）下硬锁定为 `Off`（`gamma_assist_log_lockout_bypass_events == 0`），并将 Log 监看转换交由 `[Display LUT]`（默认 `On` / `Off`）与 `[Select LUT]`（`S-Log3` / `s709` / `709(800%)` + `User1..User16`）接管，同时锁定 `[Gamma Display Assist]` 仅作用于机内 LCD 而不污染外接 HDMI 视频输出（`gamma_assist_external_hdmi_leak_events == 0`）；精确校验电影机取向 `[Auto Review] = [Off]` 默认与全部 6 项 `[TC/UB]` 参数（`Time Code Preset` `00:00:00.00`、`User Bit Preset` `00 00 00 00`、`Time Code Format` `DF`/`NDF` 且 `24.00p`/PAL 强制 `NDF`、`Time Code Run` `Rec Run`/`Free Run`、`Time Code Make` `Preset`/`Regenerate`、`User Bit Time Rec` `Off`/`On`）及 `[TC/UB Disp. Setting]`（默认 `TC`）均跨越 `[Camera Settings Reset]` 完整留存、仅由 `[Initialize]` 复位（`tcub_camera_reset_wipe_or_format_violations == 0`）。
  - **统一 `46/46` 恢复总检聚合器与 CLI（`evaluate_realhw_46pillar_recovery_master` / `evaluate_46pillar_recovery_master` / `verify-46pillar-recovery` / `verify-file-settings-gamma-assist-tcub-vault`）**：
    - 并发调用 `evaluate_realhw_45pillar_recovery_master`（`Pillars 1..45`）+ **Pillar 46**（`run_pillar46_standalone_suite`），汇总产出 **`46/46`**（`VERIFIED_46OF46_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier.py`](tests/test_realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier.py) 提供 **70 项**双模快速单元测试（实测 `1.309s` < `4.0s`）。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-file-settings-gamma-assist-tcub-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-46pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-46pillar-recovery --clean-room --json
```

## Phase 272 — 真机主线 Part 35（Pillar 47 / `47/47` 统一恢复总检）：`[Focus Assistant]`（`[Auto Magnifier in MF]` vs 历史 `MF Assist`、`Custom Button 5`、双 `[Initial Focus Mag.] = [x1.0]`、纯静态 `[AF in Focus Mag.]` / `[AF Illuminator]` 与纯净 HDMI `[Peaking Display]`）+ `[Area/Date/Time Setting]` 零射频保护、`[Video Light Mode]` `5V <= 900mA` & `[HDMI Resolution]` Log `1080p` 降档与 Slot-1 金库（`verify-47pillar-recovery` / `verify-focus-mag-datetime-videolight-hdmires-vault`）

- **[`realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](fx3_recovery/realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-45）落地 **Phase 272 Pillar 47（`47/47`）** 并将全套恢复总检推进至 **`47/47`（`VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`）**（`< 2.0s` CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..46pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **16 项** 供体（`< 0.15s`，CI 下放宽至 `< 0.50s`），同时支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 47A — `[Focus Assistant]` 命名规范、双 `[Initial Focus Mag.] = [x1.0]`、纯净 HDMI `[Peaking Display]` 与纯静态 `[AF Illuminator]`（`6/6`）**：
    - `P47A1`..`P47A6`：精确建模 `MENU` -> `Focus` -> `[Focus Assistant]`，校验 `[Auto Magnifier in MF] = [On]` 出厂默认并严格拦截历史 `"MF Assist"` 命名伪造（`legacy_mf_assist_spoof_events == 0`）、`[Focus Magnifier]` 默认绑定 `Custom Button 5`、`[Focus Magnif. Time] = [No Limit]` 默认、照片与视频各自独立的 `[Initial Focus Mag.] = [x1.0]` 寄存器（`still_movie_initial_mag_couplings == 0`）、仅限静态照片生效的 `[AF in Focus Mag.] = [On]`（`movie_af_in_focus_mag_events == 0`）、`[Peaking Display]`（默认 `Off` / `Control Wheel Right` / `Mid` / `White`）机内 LCD 专属隔离（`hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`）以及仅限静态照片生效的 `[AF Illuminator]`（`Auto` 默认，`movie_sq_af_illuminator_fire_events == 0`），并在 `144` 组合矩阵下验证 `[Camera Settings Reset]` vs `[Reset Network Set.]` vs `[Initialize]` 复位边界与 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 恢复。
  - **支柱 47B — `[Area/Date/Time Setting]` 零射频取证时间戳完整性、`[Video Light Mode]` `5V <= 900mA` 供电护栏、`[HDMI Resolution]` Log `1080p` 降档与 Slot-1 金库只读锁（`6/6`）**：
    - `P47B1`..`P47B6`：精确建模 `MENU` -> `Setup` -> `[Area/Date]` -> `[Area/Date/Time Setting]`（拦截历史 `"Date/Time Setup"` 伪造，`legacy_datetime_setup_spoof_events == 0`）全部 4 项子菜单（`Area Setting`、`Daylight Savings = Off`、`Date/Time`、`Date Format`）、`[Camera Settings Reset]` 留存（仅 `[Initialize]` 或 RTC 后备电池失电清除）、以及 `[Airplane Mode] = [On]` 下强制抑制 Creators' App `[Auto Time Correction]` 与 `[Auto Area Adjustment]`（`unsolicited_rtc_timezone_jump_events == 0`）以保障 `H0..H3` 取证时间戳；校验 `[Video Light Mode]`（`Power Link` 默认）MI 热靴 `5V <= 900 mA`（Gate G24）预算护栏（`mishoe_5v_overcurrent_events == 0`）、`[HDMI Resolution]`（`Auto` 默认，跨 `[Camera Settings Reset]` 留存）在 `[Log Shooting] != Off` 机内录制时的强制 `1080p` 降档（`hdmi_res_log_internal_rec_2160p_bypass_events == 0`）、以及 Slot-1 只读金库与 `16/16` Tier-0 `Backup.bin` `H0 == H3` 不变性（`slot1_vault_mutation_bytes == 0`，覆盖 `256` 组合矩阵）。
  - **统一 `47/47` 恢复总检聚合器与 CLI（`evaluate_realhw_47pillar_recovery_master` / `evaluate_47pillar_recovery_master` / `verify-47pillar-recovery` / `verify-focus-mag-datetime-videolight-hdmires-vault`）**：
    - 并发调用 `evaluate_realhw_46pillar_recovery_master`（`Pillars 1..46`）+ **Pillar 47**（`run_pillar47_standalone_suite`），汇总产出 **`47/47`**（`VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py) 提供双模快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-focus-mag-datetime-videolight-hdmires-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-47pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-47pillar-recovery --clean-room --json
```

## Phase 277 — 真机主线 Part 36（Pillar 48 / `48/48` 统一恢复总检）：`[Power Save by Monitor]` 现实分歧与 `[Power Save Start Time]` 9 条件无射频护栏、`[Language]` `BK_LANG` (`0x02cf019c`) 4 语言 Stage-B 等价、`[Volume Settings]` `0..15` (`7`) + `XLR-H1`、`[4ch Audio Monitoring]` 5 路由、`[Delete confirm.]` (`"Cancel" first`) 与 `Slot-1` 金库删格防火墙（`verify-48pillar-recovery` / `verify-power-save-monitor-language-volume-delete-vault`）

- **[`realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py`](fx3_recovery/realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-46）落地 **Phase 277 Pillar 48（`48/48`）** 并将全套恢复总检推进至 **`48/48`（`VERIFIED_48OF48_PILLAR_RECOVERY_MASTER`）**（`< 2.0s` CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..47pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`P277_SLOT1_FORMAT_HARD_LOCKED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **18 项** 供体（`< 0.15s`，CI 下放宽至 `< 0.50s`），同时支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 48A — `[Power Save by Monitor]` 现实分歧、`[Power Save Start Time]` 9 条件恢复护栏与 `[Language]` `BK_LANG` 4 语言 Stage-B 等价（`6/6`）**：
    - `P48A1`..`P48A6`：精确验证原厂 `ILME-FX3 Ver. 7.02` `[Setup] -> [Power Setting Option]` 仅暴露 `[Power Save Start Time]`（`Off`、`30 Min`、`5 Min` 默认、`2 Min`、`1 Min`、`10 Sec`）与 `[Auto Power OFF Temp.]`（`Standard` 默认、`High`）两项（`fx3_ui_exposes_power_save_by_monitor == False`），同时核对共享 `appFw.so`（`BKID_APP_setting_monitor_power_linkage`）与 `string_*_f.uxc`（`0x60b9`）编入的精确 4 模式（`Both Linked` `0x6db5`、`Open: Return` `0x6db6`、`Close: Power Save` `0x60a8`、`Does Not Link` `0x6b2e`），驳回 `"Open: On/Close: Off"` 伪造；在无任何 9 项停用条件激活的无射频电池 Tier-0 恢复会话中强制 `[Power Save Start Time]` ∈ `{Off, 30 Min}`；校验 `BK_LANG`（`0x02cf019c`）在 `FX3-CX95900_ALLLANG-Backup.bin`（`4 B @ 0x90ff0 = 0x00`，`34` 语言）与 `FX6` `CX95898_NTSC.bin`（`0x00`）/ `CX95899_CN1.bin`（`0x19`，`1 B @ 0x89242`，`29` 语言）及 Stage-B 4 语言 `.uxc` + `.ltt` 字库表一致性，并验证 `(Setup)` 跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 留存、仅经 `[Initialize]` 复位。
  - **支柱 48B — `[Volume Settings]`（`0..15` 默认 `7`）+ `XLR-H1` 啸叫护栏、`[4ch Audio Monitoring]`（5 路由）与 `[Delete confirm.]`（`"Cancel" first`）`Slot-1` 删格防火墙（`6/6`）**：
    - `P48B1`..`P48B6`：精确建模 `[Volume Settings]`（`BKID_APP_setting_volume_settings`，`0xe8c9`，离散 `0..15` 默认 `7`）及 `XLR-H1` 机内扬声器声反馈护栏（`<= 4` 或声学隔离）、`[4ch Audio Monitoring]`（`CH1/CH2` 默认 `0x713b`、`CH3/CH4` `0x6bf6`、`CH1+3/CH2+4` `0x6c2e`、`CH1/CH1` `0x6f9c`、`CH2/CH2` `0x7a26`）与 HDMI `[4ch Audio Output]`（`0x6aa0`）及 3.5mm 双声道边界隔离、`[Delete confirm.]`（`"Cancel" first` 默认 `0xe724`/`0x6a5e` vs `"Delete" first` `0xe725`/`0x6e0a`）+ `[Delete pressing twice]`（`Off` 默认 `0x74db`）跨越 `[Camera Settings Reset]` 留存，以及针对 `Slot 1`（`CAMSET`/`BODYDATA.DAT` 恢复金库）全部删除/双击删除/格式化操作硬阻断（`slot1_vault_delete_events == 0`、`slot1_format_hard_locked == True`、`slot1_vault_mutation_bytes == 0`）。
  - **统一 `48/48` 恢复总检聚合器与 CLI（`evaluate_realhw_48pillar_recovery_master` / `evaluate_48pillar_recovery_master` / `verify-48pillar-recovery` / `verify-power-save-monitor-language-volume-delete-vault`）**：
    - 并发调用 `evaluate_realhw_47pillar_recovery_master`（`Pillars 1..47`）+ **Pillar 48**（`run_pillar48_standalone_suite`），汇总产出 **`48/48`**（`VERIFIED_48OF48_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py`](tests/test_realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py) 提供 `>= 72` 项双模快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-power-save-monitor-language-volume-delete-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-48pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-48pillar-recovery --clean-room --json
```

## Phase 282 — 真机主线 Part 37（Pillar 49 / `49/49` 统一恢复总检）：`[USB Connection Mode]` 4 模式与休眠 `NOUVC` 拆离、数据隔离 `USB PD` 供电护栏、`[HDMI Info. Display]` LCD 熄屏/`1080` 钳位与 `4K` 洁净回传、`[Protect]` vs `[Format]` `Slot-1` 双层 WP+防火墙及 `[Reset Network Set.]` 自动重启 + 重置后 `[Airplane Mode]=On` 零射频序列（`verify-49pillar-recovery` / `verify-usb-mode-hdmi-info-protect-network-reset-vault`）

- **[`realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py`](fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-47）落地 **Phase 282 Pillar 49（`49/49`）** 并将全套恢复总检推进至 **`49/49`（`VERIFIED_49OF49_PILLAR_RECOVERY_MASTER`）**（`< 2.0s` CLI 快速预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..48pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`P282_SLOT1_FORMAT_HARD_LOCKED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **18 项** 供体（`< 0.15s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 49A — `[USB Connection Mode]` 4 模式 vs 休眠 `NOUVC` `[USB Streaming]`、数据隔离 `USB PD` 供电护栏与 `[HDMI Info. Display]` LCD 熄屏 / `1080` 钳位 vs `4K` 洁净回传（`6/6`）**：
    - `P49A1`..`P49A6`：精确核验原厂 `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`（`BKID_APP_setting_usb_connection_method`，`_f.uxc` `0x69a2`）仅暴露 **4 项**（`Sel. When Connect` `0x7738` 默认、`MassStorage(MSC)` `0x6c54` / `054C:0DA1` / `USB_CONNECTION_METHOD_MASS_STRAGE`、`MTP` `0xe24b`、`Remote Shoot (PC Remote)` `0x60aa`），而 `usb_f_uvc.ko`（`78,840 B`）与 `_f.uxc` `0x7399` `[USB Streaming]` 处于 `NOUVC` 休眠隔离状态；在气隙 Tier-0 备份/回滚期间严禁 `MSC`、`MTP`、`Remote Shoot`、`USB-LAN` 主机数据枚举，仅当物理隔离 `D+/D-` 与 SuperSpeed 数据线且插入 `NP-FZ100` 电池并使用 `USB Type-C`（非 `Multi/Micro USB`）时允许 `[USB Power Supply] = [On]`（`0x721e`；`[USB LUN Setting]` `Multi` 默认 `0xe631` / `Single` `0x776d`）；当外部 HDMI 录制/分析仪接入且处于操作员引导的机内 LCD 菜单恢复流程时强制 `[HDMI Info. Display] = [Off]`（`0xe297`），杜绝 `On`（`0xe07c` / `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`）导致机内 LCD 黑屏盲操；核验 `1080p` 内录 Log/`PPLUT` 钳位与 `4K` `Off(HDMI Only)`（`0x6573`）/`RAW Output`（`0x6e97`）自动洁净回传覆盖，并验证 `(Setup)` 跨 `[Camera Settings Reset]` 完整留存（仅 `[Initialize]` 复位并可重放 `Slot-1` `CAMSET01.DAT`）。
  - **支柱 49B — `[Protect]` 4 范围 vs `[Format]` 抹除（`Slot-1` 双层硬件 SD `WP` + 防火墙强制）与 `[Reset Network Set.]` 自动重启 + 重置后 `[Airplane Mode] = [On]` 零射频序列（`6/6`）**：
    - `P49B1`..`P49B6`：精确校验 `ILME-FX3` 全 4 项 `[Protect]` 范围（`Single`/`Multiple Img.` `0xe2ca`、`All in this Folder` `0x6848`、`All with this date` `0x69f7`、`All Images in This Group` `0xe826`）仅阻止 `[Delete]` / `[Delete pressing twice]`，但 **`[Format]`（`0xe449` / `0xe414`）会直接抹除已保护文件与卡内 `M1..M4` 设置**，因此 `Slot 1`（`CAMSET`/`BODYDATA.DAT` 恢复金库）必须同时具备物理 SD `WP` 锁定（`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）与 `slot1_format_hard_locked == True` 双层防护（驳回仅靠软件 `[Protect]` 的伪金库姿态）；同时验证 `[Reset Network Set.]`（`FUNC_reset_network_settings` / `SETTING_RESET_NW` / `_f.uxc` `0x60d3` & `0x65d3`）仅清空 `(Network)` 凭证、保留 `(Shooting)`/`(Setup)`/`(Playback)`/`CAMSET`、触发强制自动重启（`BKID_APP_is_shutdown_factor_network_reset`）并把 `[Airplane Mode]` 复归 `Off`，必须在重启完成且重新置位 `[Airplane Mode] = [On]`（`0x6df9`）后方可通过零射频恢复认证。
  - **统一 `49/49` 恢复总检聚合器与 CLI（`evaluate_realhw_49pillar_recovery_master` / `evaluate_49pillar_recovery_master` / `verify-49pillar-recovery` / `verify-usb-mode-hdmi-info-protect-network-reset-vault`）**：
    - 并发调用 `evaluate_realhw_48pillar_recovery_master`（`Pillars 1..48`）+ **Pillar 49**（`run_pillar49_standalone_suite`），汇总产出 **`49/49`**（`VERIFIED_49OF49_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py`](tests/test_realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py) 提供 `>= 72` 项双模快速单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-usb-mode-hdmi-info-protect-network-reset-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-49pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-49pillar-recovery --clean-room --json
```

## Phase 287（`50/50` 里程碑！Pillar 50 & 统一 `verify-50pillar-recovery` 总检）：`[Picture Profile]` `PP11`（`S-Cinetone`）默认与 `[Creative Look]` / `[DRO]` / `[Log Shooting]` 互斥锁、`PPLUT` `1080p` 钳位与 `PP1..11` 非可复位内部参数陷阱、`[White Balance]` `Custom 1..3` `CAMSET` 排除与 `[Metering Mode]` `De-Squeeze` / `Cine EI` Base ISO 被动 `M.M.` 不变性验证（`verify-50pillar-recovery` / `verify-pp-scinetone-wb-metering-vault`）

- **[`realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py`](fx3_recovery/realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-48）落地 **Phase 287 Pillar 50（`50/50` 恢复支柱总里程碑！）** 并将全套恢复总检推进至 **`50/50`（`VERIFIED_50OF50_PILLAR_RECOVERY_MASTER`）**（`< 2.2s` CLI 快速预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..49pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`P287_SLOT1_FORMAT_HARD_LOCKED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **11 项** Wave-48 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 50A — `[Picture Profile]` 开箱 `PP11`（`S-Cinetone`）默认与 `[Creative Look]`（10 组预设 + `CREATIVE_BOX_1..6`）/ `[D-Range Optimizer]` / `[Log Shooting]` 互斥锁、`PPLUT1..4` 电影独占与 `1080p` HDMI 钳位、`PP1..11` 非可复位内部参数陷阱及与 FX6 `Base Look` 区分（`6/6`）**：
    - `P50A1`..`P50A6`：精确核验原厂 `ILME-FX3` `[Picture Profile]`（`BKID_APP_setting_picture_profile`，`_f.uxc` `0x6830`）默认 **`PP11`（`S-Cinetone`，`0x67ab`/`0x6e61`）** 同效作用于 Movie 与 Still（除非勾选 `[Different Set for Still/Mv]` `0x62ee`）；一旦 `[Picture Profile] != Off`，`[Creative Look]`（`0x6823`：`ST`..`SE` + `CREATIVE_BOX_1..6`）强制锁为 `'-'` 且 `[D-Range Optimizer]`（`0xe89c`：`Auto`/`Lv1..Lv5`）强制锁为 `Off`；`[Log Shooting]`（`Flexible ISO`/`Cine EI Quick`/`Cine EI`，`0x6020`）同时锁死 `PP = Off`、`CL = '-'` 与 `DRO = Off`（杜绝双 Log 畸变），而 `PPLUT1..4` 仅限 Movie 域并将内录下 HDMI 输出钳位在 `1080p`；显式校验 **关键恢复复位陷阱**：`[Camera Settings Reset]` 与 `[Initialize]` **均不会**复位 `PP1..PP11` 内部参数或 `[Different Set for Still/Mv]` 勾选标记，完整基线恢复必须执行逐配置 `[PPx] -> [Reset]`（`PPLUT1..4` 随 `Initialize` 复位）及跨机型与 `ILME-FX6` `Base Look`（`Custom` 下场景文件 1 默认 `S-Cinetone`，`Cine EI` 锁 `S-Log3`）划界。
  - **支柱 50B — `[White Balance]`（`2500K..9900K` / `A7..B7` / `G7..M7`、`Custom 1..3` 随 `Reset` 留存但被 `Slot-1` `CAMSET` 排除、`Cine EI` AWB 封锁、`Custom Setup` 错误陷阱、非可复位 `Shutter AWB Lock`）与 `[Metering Mode]`（6 模式、`De-Squeeze != Off` 强锁 `Face Priority = Off`、非可复位 `AEL w/ Shutter`、`Cine EI` Base ISO `800`/`12800` 被动 `M.M.` 不变性）（`6/6`）**：
    - `P50B1`..`P50B6`：精确校验 `[White Balance]`（`0xe5d4`）`Auto` 默认（`Priority Set in AWB` `0x67a7`）、`2500K..9900K`（`100K` 步进 / `75` 档 + `A7..B7`/`G7..M7`）、`Custom 1..3`（`0xe79d..0xe79c`）、非可复位 `Shutter AWB Lock`（`Off` `0x66db`）与 `Shockless WB`（`1 (Fast)` `0x62fe`）；拦截 `Cine EI` / `Cine EI Quick` 下 `Auto`/`Underwater Auto` WB 及 `Log Shooting != Off` 或 `S-Log3`/`PPLUT1..4` 下执行 `[Custom Setup]` 的错误陷阱；核验 **`Custom 1..3` 白平衡记忆值跨 `[Camera Settings Reset]` 留存却无法由 `Slot 1` `Save/Load Settings`（`CAMSET`）保存或恢复**——强制以人工重标定替代虚假的 `CAMSET` 复原预期；完整覆盖 6 种 `[Metering Mode]`（`0xe5cf`）、`De-Squeeze != Off` 时强锁 `Face Priority in Multi Metering = Off`（`0x69c7`）、`Wide` 对焦区强锁 `Spot Metering Point = Center`（`0x625c`）、非可复位 `AEL w/ Shutter`（`0x669d`），以及 `Cine EI` Base ISO（`800`/`12800`）仅输出 `M.M.` 偏差而不变动传感器增益的不变性。
  - **统一 `50/50` 恢复总检聚合器与 CLI（`evaluate_realhw_50pillar_recovery_master` / `evaluate_50pillar_recovery_master` / `verify-50pillar-recovery` / `verify-pp-scinetone-wb-metering-vault`）**：
    - 并发调用 `evaluate_realhw_49pillar_recovery_master`（`Pillars 1..49`）+ **Pillar 50**（`run_pillar50_standalone_suite`），汇总产出 **`50/50`**（`VERIFIED_50OF50_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py`](tests/test_realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py) 提供 `>= 74` 项双模（本地只读供体 + 洁净室 + 环境变量强制）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pp-scinetone-wb-metering-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-50pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-50pillar-recovery --clean-room --json
```

## Phase 292（Pillar 51 / `51/51` 统一恢复总检）：静态 `[Image Quality Settings]`（`Compressed`/`Uncompressed` `.ARW` 禁用休眠 `Lossless Comp`、`HEIF 4:2:0/4:2:2` `.HIF`、`[HLG Still Image]` `BT.2100`）、`[Color Space]` `AdobeRGB` `_DSC` 与禁止 `_` 开头前缀、`[Shutter Type]` 精确 2 选（无 `Auto`）+ 5 锁矩阵/`1/250 s` 闪光同步、`[Long Exposure NR]`/`[High ISO NR]`/`[Drive Mode]` `10 fps` 连拍与 `Slot-1` 金库写入防火墙（`verify-51pillar-recovery` / `verify-pillar51-raw-heif-colorspace-shuttertype-vault`）

- **[`realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py`](fx3_recovery/realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-49）落地 **Phase 292 Pillar 51（`51/51`）** 并将全套恢复总检推进至 **`51/51`（`VERIFIED_51OF51_PILLAR_RECOVERY_MASTER`）**（`< 1.2s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..50pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`P292_SLOT1_FORMAT_HARD_LOCKED = True`、`P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-49 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 51A — 静态 `[Image Quality Settings]`（`Compressed`/`Uncompressed` 14-bit `.ARW` 禁用休眠 `Lossless Comp`、`JPEG/HEIF Switch` `4:2:0/4:2:2` 10-bit `.HIF`、`[HLG Still Image]` `BT.2100` 覆盖与 4 项锁定 vs 无静态管线 `ILME-FX6`）、`[Color Space]` `AdobeRGB` `_DSC` 前缀、`[Set File Name]` 禁 `_` 开头与 `Slot-1` 金库写入防火墙（`6/6`）**：
    - `P51A1`..`P51A6`：精确建模 `MENU -> Shooting -> [Image Quality/Rec]`：`ILME-FX3 Ver. 7.02`（`12 MP IMX510`）仅暴露 `[Compressed]`（默认）与 `[Uncompressed]` 14-bit `.ARW`（fail-closed 拦截 `appFw.so`/`_f.uxc` `0x6b56` 休眠 `Lossless Comp` / `Lossless Comp (L)/(M)/(S)`），并与零 `DCIM`/`.ARW`/`.JPG`/`.HIF` 静态管线的 `ILME-FX6` 严格划界；`[HLG Still Image] = On` 强制校验 3 项前提（`HEIF(4:2:0/4:2:2)` + `File Format == HEIF` + `P/A/S/M` 且未被 `Reg. Custom Shoot Set` 覆盖），锁定 `Picture Profile`/`Creative Look`/`D-Range Optimizer`/`DRO Bracket`，迁移 ISO 边界并把有效 `[Color Space]` 覆盖为 `BT.2100`（`BT.2020`）；校验 `[Color Space]`（`sRGB` 默认 -> `DSC00001` vs `AdobeRGB` -> `_DSC0001`）与 `[Set File Name]`（`DSC` 默认、跨 `[Camera Settings Reset]` 留存、禁止首字符为 `_`）；强制 `Slot-1` Tier-0 金库 `EROFS`/`EBUSY` 写入防火墙阻断静态 `.ARW`/`.JPG`/`.HIF` 拍摄写入与 `Sort Recording` 定向写入，保持 Stage-B `/tmp/` 易失叠加（`BLKROSET=True`）及 `16/16` `H0 == H3` `Backup.bin` 不变性。
  - **支柱 51B — `[Shutter Type]` 精确 2 选分割（`Mechanical Shutter` 默认 vs `Electronic Shutter`，无 `Auto`！）、`1/250 s` 闪光同步、电子/静音 5 锁矩阵、`[e-Front Curtain Shut.]`、`[Long Exposure NR]`/`[High ISO NR]` 与 `[Drive Mode]` `10 fps` 连拍/包围 `Slot-1` 金库防火墙（`6/6`）**：
    - `P51B1`..`P51B6`：精确建模 `MENU -> Shooting -> [Shutter/Silent] -> [Shutter Type]`（`0x7aa9`）在 `ILME-FX3 Ver. 7.02` 仅暴露 **2 项**（`Mechanical Shutter` 默认 vs `Electronic Shutter`，fail-closed 拦截休眠 `Auto` / `BKID_APP_setting_still_shutter_type_anti_distortion_shutter`），并与 `mechanical_shutter = False` 的 `ILME-FX6` 划界；校验 `Electronic Shutter` 与 `Silent Mode = On`（可经 `Target Function Settings` 覆盖）触发 **5 锁矩阵**（禁用 ① `Flash` `1/250 s` 全幅同步、② `Long Exposure NR`、③ `e-Front Curtain Shut.` 默认 `On` 且跨 `Camera Settings Reset` 留存、④ `BULB`、⑤ `Anti-flicker Shoot.`）；校验 `[Long Exposure NR]`（`>= 1 s` 等长暗帧 `t_NR == t_shutter`，连拍/连续包围锁定为 `Off`，`Intelligent Auto` 强制 `On`）、`[High ISO NR]`（`Normal` 默认 / `Low` / `Off`，`RAW` 不可用且不作用于 `.ARW`）、`[Drive Mode]`（全部 8 模式，`Hi+` 在 `Compressed` RAW 下达 `10 fps`、在 `Uncompressed` RAW 或闪光时降速 `< 10 fps`、`Hi+` 非实时监看、`F > F11` 首张对焦锁定、`HLG Still = On` 禁用 `DRO Bracket`），以及 `Slot-1` 突发连拍/包围 `DCIM` 与 `AVF_INFO` ImageDB `EROFS`/`EBUSY` 金库防火墙。
  - **统一 `51/51` 恢复总检聚合器与 CLI（`evaluate_realhw_51pillar_recovery_master` / `evaluate_51pillar_recovery_master` / `verify-51pillar-recovery` / `verify-pillar51-raw-heif-colorspace-shuttertype-vault`）**：
    - 并发调用 `evaluate_realhw_50pillar_recovery_master`（`Pillars 1..50`）+ **Pillar 51**（`run_pillar51_standalone_suite`），汇总产出 **`51/51`**（`VERIFIED_51OF51_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py`](tests/test_realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py) 提供 `>= 76` 项双模（本地只读供体 + 洁净室 + 环境变量强制）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pillar51-raw-heif-colorspace-shuttertype-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-51pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-51pillar-recovery --clean-room --json
```

## Phase 296（Pillar 52 / `52/52` 统一恢复总检）：`[Focus Area]` 14 项分层与 Movie `Tracking:` 锁闭、`[AF Area Registration]` 解锁互斥与 `Initialize` 留存、机身 `W/T` 变焦杆 vs 无变焦 `XLR-H1` 辟谣、`[ISO Range Limit]` / 静态专用 `[ISO AUTO Min. SS]` vs `Cine EI` Base ISO 锁定、`[Flash Mode]` 机械快门静态门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA` 与 `Slot-1` 金库写入防火墙（`verify-52pillar-recovery` / `verify-pillar52-focus-area-zoom-iso-flash-vault`）

- **[`realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py`](fx3_recovery/realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-50）落地 **Phase 296 Pillar 52（`52/52`）** 并将全套恢复总检推进至 **`52/52`（`VERIFIED_52OF52_PILLAR_RECOVERY_MASTER`）**（`< 1.2s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..51pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`P296_SLOT1_FORMAT_HARD_LOCKED = True`、`P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-50 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 52A — `[Focus Area]` 14 项分层、`[AF Area Registration]` 与机身 `W/T` 变焦杆 vs 无变焦 `XLR-H1` 辟谣及 `Slot-1` 金库防火墙（`6/6`）**：
    - `P52A1`..`P52A6`：精确校验 `MENU -> Focus -> [Focus Area]` 7 项通用区域（`Wide`、`Zone`、`Center Fix`、`Spot: S/M/L`、`Expand Spot`）与 7 项仅静态 `Tracking:` 区域（Movie/`S&Q` 中锁定，改由 `[Touch Tracking]` 接管）；校验 `[Focus Area Limit]`（`>= 2` 项启用，`.uxc` `0xe227`）、`[Switch V/H AF Area]`（仅静态）、`[Circ. of Focus Point]`（H/V 循环不含斜向）与 `[AF Area Registration]`（`Off`/`On`，跨 `Camera Settings Reset` 留存、仅随 `Initialize` / `Del. Regist. AF Area` 清除，且强制 `[Lock Operation Parts] = Off`）；严格辟谣 **`ILME-FX3` `XLR-H1` 手柄仅为音频手柄（零变焦杆、零录制键、零 `ZOOM HOLD` 开关）**，与具备 `Handle Zoom`（`Off`/`Low`/`High`/`Variable 1..8`）、`Handle HOLD Switch` 及 `0..99` 变焦位置指示（`Zoom Position Display`）的 `ILME-FX6` 智能手柄严格划界；强制 `Slot-1` `EROFS`/`EBUSY` 写入防火墙、`Stage-B` `/tmp/` 易失叠加（`BLKROSET=True`）及 `16/16` `H0 == H3` `Backup.bin`。
  - **支柱 52B — `[ISO Range Limit]` / 仅静态 `[ISO AUTO Min. SS]` vs `Cine EI`、`[Flash Mode]` 机械快门静态门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA` 护栏（`6/6`）**：
    - `P52B1`..`P52B6`：精确校验 `[ISO Range Limit]`（`Min/Max` 限制手动与 `ISO AUTO`）及仅限静态（`P`/`A` 或 `M + ISO AUTO`）的 `[ISO AUTO Min. SS]`（`Slower..Faster` 或 `1/8000..30"`，经 `Camera Settings Reset` 复位于 `Standard`），并在 Movie/`S&Q` `Cine EI` / `Cine EI Quick` 下硬锁定 Base ISO `800 / 12800` 及 `[Auto Slow Shutter]`（对比无 `ISO AUTO Min. SS` 的 `ILME-FX6` `AGC`）；校验 `[Flash Mode]`（`Flash Off` / `Autoflash` / `Fill-flash` / `Slow Sync.` / `Rear Sync.`，Pillar 52 基线默认 `Fill-flash`，全幅 `1/250 s` 机械快门同步上限）严格门控至 `ILME-FX3` 机械快门静态模式（在 Movie/`S&Q`、`Electronic Shutter`、`Silent Mode = On` 与无机械快门 `ILME-FX6` 中禁止），同时校验跨静态/Movie/`S&Q` 的 `[Video Light Mode]`（`Power Link` 默认 / `REC Link` / `REC Link&STBY` / `Auto`）受 MI 热靴 `PMIC 5V <= 900 mA` 电流护栏、`<= 250 V` 触发电压与 `Slot-1` `EROFS`/`EBUSY` 金库防火墙保护。
  - **统一 `52/52` 恢复总检聚合器与 CLI（`evaluate_realhw_52pillar_recovery_master` / `evaluate_52pillar_recovery_master` / `verify-52pillar-recovery` / `verify-pillar52-focus-area-zoom-iso-flash-vault`）**：
    - 并发调用 `evaluate_realhw_51pillar_recovery_master`（`Pillars 1..51`）+ **Pillar 52**（`run_pillar52_standalone_suite`），汇总产出 **`52/52`**（`VERIFIED_52OF52_PILLAR_RECOVERY_MASTER`）与规范摘要哈希；[`tests/test_realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py`](tests/test_realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py) 提供 `>= 76` 项双模（本地只读供体 + 洁净室 + 环境变量强制）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pillar52-focus-area-zoom-iso-flash-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-52pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-52pillar-recovery --clean-room --json
```

## Phase 300（`300th` Phase Milestone Grand Closure!! Pillar 53 & 统一 `53/53` 恢复总检）：`[XAVC S-I DCI 4K]` `4096x2160` vs Long-GOP UHD 分裂、`24.00p` 强制重启清空 `/tmp` Stage-B 与回放隔离、`4264x2408` HDMI RAW 与静态 `[Aspect Ratio]`、`[Reg. Custom Shoot Set]` 11 项勾选与 `HLG` 锁定、`[Camera Set. Memory]` `CAMPR%02d%c.DAT` 路径隔离 vs FX6 `PRO/CAMERA`，及 `[Photo Capture]` DCI 4K 禁用与 `Slot-1` 金库 `EROFS`/`EBUSY` 防火墙（`verify-53pillar-recovery` / `verify-pillar53-dci4k-aspect-custom-hold-camset-vault`）

- **[`realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py`](fx3_recovery/realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-51）落地 **Phase 300（第 300 阶段总里程碑！！）Pillar 53** 并将全套恢复总检推进至 **`53/53`（`VERIFIED_53OF53_PILLAR_RECOVERY_MASTER`）**（`< 1.2s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..52pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`P300_SLOT1_FORMAT_HARD_LOCKED = True`、`P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-51 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 53A — `[XAVC S-I DCI 4K]`（`4096x2160` `17:9` All-Intra vs Long-GOP `3840x2160` UHD 分裂）、`24.00p` 强制重启与回放隔离（易失 `/tmp` Stage-B 清空危险！）、`4264x2408` Type-A HDMI RAW 与静态 `[Aspect Ratio]`（`3:2 / 4:3 / 16:9 / 1:1`）（`6/6`）**：
    - `P53A1`..`P53A6`：精确校验 `ILME-FX3 Ver. 3.00+/7.02` 真实暴露 **`[XAVC S-I DCI 4K]`**（`4096x2160` `17:9` All-Intra `4:2:2 10bit`，`23.98p`/`24.00p` `240M`..`59.94p` `600M`，`S&Q 1..48fps` 锁定 `100/120fps`，`600M` 强制 `CFexpress VPG200+` / `SDXC V90+`；`Ver. 6.00+` `Angle` `5.6..360.0°`），而 Long-GOP（`XAVC HS 4K`/`XAVC S 4K`）与 `XAVC S-I 4K` 严格保持 `3840x2160` `16:9` UHD 且无 `24.00p`（fail-closed 拦截休眠 `xavc_hs_8k_24p`）；**关键 Stage-B 防护**：切入或切出 `24.00p` 触发**强制相机重启**（`_g.uxc` `0x639b`/`0x63b6`），干净清空易失 `/tmp/` Stage-B bind mounts 回落原厂 `7.02`（`H0 == H2`）并隔离 `24.00p` 回放（`_g.uxc` `0x63d7`）；精确建模 `4264x2408` Type-A HDMI RAW（vs `ILME-FX6` `4096x2160 / 3840x2160` SDI/HDMI RAW）及静态 `[Aspect Ratio]`（`3:2` 默认 `12M`、`4:3` `11M`、`16:9` `10M`、`1:1` `8.0M`；RAW 保留完整 `3:2` 像素 + 裁切元数据；`APS-C S35 = On` 降档 `L -> M` vs 无静态管线 `ILME-FX6`）。
  - **支柱 53B — `[Reg. Custom Shoot Set]`（`Recall Custom hold 1..3` 11 勾选框与 `HLG Still Image` 锁定）、`[Camera Set. Memory]`（`1..3 + M1..M4` `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT` & `CAMSET` vs FX6 `s/SONY/PRO/CAMERA/` 跨机型封锁），及 `[Playback] [Photo Capture]`（`8.3M/2.1M` DCI 4K 禁用与 `Slot-1` Tier-0 金库 `EROFS`/`EBUSY` 写入防火墙）/ 只读 `[Enlarge Image]`（`6/6`）**：
    - `P53B1`..`P53B6`：强制静态 `P/A/S/M` 独占 `[Reg. Custom Shoot Set]`（`Recall Custom hold 1..3`、仅随 `Initialize` 清除、**11** 项 `is_checked_recall_custom_hold0..10` 勾选框、召回 `ISO` 或 `DRO Bracket` 时强锁 `[HLG Still Image] = Off`）；严格隔离存储卡路径：`ILME-FX3` 写入 `%c:%s/SONY/SETTING/FX3/CAMPR%02d%c.DAT`（`M1..M4`）与 `%c:%s/SONY/SETTING/FX3/CAMSET/*.DAT`（`CAMSET`，**零 `PRIVATE/SONY/PRO/CAMERA`**——后者属 `ILME-FX6` `Scene/User/All File` 专用，跨机型导入 fail-closed 拦截！），并阻断向只读 `Slot-1` Tier-0 金库保存 `M1..M4`/`CAMSET`；强制 `[Playback] -> [Edit] -> [Photo Capture]`（`8.3M` UHD / `2.1M` HD `JPEG`/`HEIF` 抽帧）：在 `XAVC S-I DCI 4K` 剪辑上禁止（`_g.uxc` `0x60ce`）且只要 `[Select Playback Media] = Slot 1` 挂载只读 Tier-0 恢复金库即 fail-closed 返回 `EROFS`/`EBUSY` 阻断写入，而只读 `[Enlarge Image]`（`Enlarge Initial Mag.` / `Enlarge Initial Position`，跨 `Camera Settings Reset` 留存）安全放行。
  - **统一 `53/53` 恢复总检聚合器与 CLI（`evaluate_realhw_53pillar_recovery_master` / `evaluate_53pillar_recovery_master` / `verify-53pillar-recovery` / `verify-pillar53-dci4k-aspect-custom-hold-camset-vault`）**：
    - 并发调用 `evaluate_realhw_52pillar_recovery_master`（`Pillars 1..52`）+ **Pillar 53**（`run_pillar53_standalone_suite`），汇总产出 **`53/53`（`VERIFIED_53OF53_PILLAR_RECOVERY_MASTER`）**与规范摘要哈希；[`tests/test_realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py`](tests/test_realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py) 提供 `>= 78` 项双模（本地只读供体 + 洁净室 + 环境变量强制）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pillar53-dci4k-aspect-custom-hold-camset-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-53pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-53pillar-recovery --clean-room --json
```

## Phase 304（Pillar 54 / `54/54` 统一恢复总检）：`[Sensor Cleaning]` `>= 51%` 电量门槛与强制断电 vs FX6 `e-ND + APR`、`[Exposure Comp.]` `+-5.0/+-2.0 EV` & `Cine EI` 锁定、`[Focus Mode]` 静态 5 项 vs 视频 `AF-C/MF` 钳位，及回放 `[Image Index]` `9/25` 与 `[Rotate]` Slot-1 金库 `EROFS`/`EBUSY` 防火墙（`verify-54pillar-recovery` / `verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault`）

- **[`realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py`](fx3_recovery/realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-52）落地 **Phase 304 Pillar 54（`54/54`）** 并将全套恢复总检推进至 **`54/54`（`VERIFIED_54OF54_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..53pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P304_SLOT1_FORMAT_HARD_LOCKED = True`、`P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-52 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 54A — `[Sensor Cleaning]`（`>= 51%` `NP-FZ100` 电量门控 + 物理开关断电 `OFF` vs 无 IBIS `ILME-FX6` 电子 `e-ND` + `APR`）与 `[Exposure Comp.]`（`+-5.0 / +-2.0 EV`、`M + ISO AUTO` 专享、`[Exposure step]` 仅随 `Initialize` 重置及 100% `Cine EI` 锁死）与 `Slot-1` 金库防火墙（`6/6`）**：
    - `P54A1`..`P54A6`：精确验证 `ILME-FX3 Ver. 2.00+..7.02` `[Setup] -> [Setup Option] -> [Sensor Cleaning]`（`_f.uxc` `0x67d6`、旧版 `.uxc` `0xe7d7 Cleaning Mode`、`appFw.so` `FUNC_set_cleaning_mode` / `MODEL_CLEANING_MODE_COMP`）强制要求 `NP-FZ100 >= 51%`（`< 51%` 触发 `BATTERY_CHECK_FOR_CLEANING_MODE_LOWER` -> `.uxc` `0xe574` `Power insufficient.` 拒绝，对比 Ver. 1.x `>= 3` 格电量），并在 IBIS 震动/归位后要求强制物理拨动电源开关 `OFF`（`_g.uxc` `0x6221`）方可卸下镜头；与无 IBIS 的 `ILME-FX6 Ver. 6.01` 前置电子 `Variable ND`（`1/4..1/128 + CLEAR`、`PID_SET_VARIABLE_ND_VALUE`）+ `Technical > APR`（`MODEL_APR_EXECUTE_COMP`，`CrCommandId_SensorCleaning = 320` 不支持）严格隔离。校验 `[Exposure Comp.]`（`_f.uxc` `0x76de` / `.uxc` `0xe956`）跨度：`+-5.0 EV` 静态 / `+-2.0 EV` Movie & `S&Q`（可被 `Camera Settings Reset` 复位；`[Exposure step]` `0.3EV`/`0.5EV` 与 `[Exposure Std. Adjust]` 为 `Initialize` 专属；`ilc/2210` 省略休眠物理拨盘 `[Reset EV Comp.]` `0x7853` 与 Ver. 1 `[Dial Ev Comp]` `0xe4d9`）、`M` 模式下仅与 `ISO AUTO` 共存，并在 `[Log Shooting] = Cine EI / Cine EI Quick` 下 **100% 锁死**（由 `Base ISO 800/12800` + `[Exposure Index]` `+-2.0 EV` 接管监看）。
  - **支柱 54B — `[Focus Mode]`（静态 5 项 vs Movie/`S&Q` 2 项 `AF-C/MF` 钳位 + `[Priority Set in AF-S/AF-C]` / `[AF Illuminator]`）与回放 `[View Mode]` / `9/25` `[Image Index]` / `[Display as Group]` / `[Display Rotation]` / `[Rotate]` `Slot-1` Tier-0 金库防火墙（`6/6`）**：
    - `P54B1`..`P54B6`：精确校验 `[Focus Mode]` 静态 5 模式（`AF-S`、`AF-A` 默认可被 `Camera Settings Reset` 复位、`AF-C`、`DMF`、`MF`，拒绝休眠 `PF`/`SEMI_MANUAL`）vs Movie & `S&Q` 严格钳位至 **2 模式**（`AF-C` / `MOVIE_AUTO` `0x66ea` 与 `MF`，在 Movie/`S&Q` 下请求 `AF-S`/`AF-A`/`DMF` 时 fail-closed 返回 `EOPNOTSUPP=95` / `EINVAL=22`）；校验 `[Priority Set in AF-S/AF-C]`（`AF`/`Release`/`Balanced Emphasis` 仅随 `Initialize` 清除）与 `[AF Illuminator]`（仅静态、Movie/`S&Q`/`AF-C` 锁死）。校验回放设置（跨越 `Camera Settings Reset` 留存）：`[View Mode]`（`Date View`/`Folder View(Still)`/`Movie View`/`AVCHD View`/`XAVC S View`）、精确 `[Image Index]` `9 Images / 25 Images`（拒绝休眠 `12/30 Images`）、`[Display as Group]`、`[Display Rotation]`（`Auto`/`Manual`/`Off`），以及**关键恢复金库防火墙**：回放 `[Rotate]`（`FUNC_rotate_content`、`_f.uxc` `0x795a`）会直接篡改卡上 EXIF 方向或 `AVF_INFO` 数据库 -> 只要 `Slot 1` 挂载 Tier-0 恢复金库即 MUST fail-closed 返回 `EROFS=30` / `EBUSY=16`（`slot1_data_sector_writes == 0`、`slot1_rotate_exif_mutation_bytes == 0`、`slot1_vault_mutation_bytes == 0`）。
  - **统一 `54/54` 恢复总检聚合器与 CLI（`evaluate_realhw_54pillar_recovery_master` / `evaluate_54pillar_recovery_master` / `verify-54pillar-recovery` / `verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault`）**：
    - 并发调用 `evaluate_realhw_53pillar_recovery_master`（`Pillars 1..53`）+ **Pillar 54**（`run_pillar54_standalone_suite`），汇总产出 **`54/54`（`VERIFIED_54OF54_PILLAR_RECOVERY_MASTER`）**与规范摘要哈希；[`tests/test_realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py`](tests/test_realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py) 提供 `>= 80` 项双模（本地只读供体 + 洁净室 + 环境变量强制）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-54pillar-recovery --json

FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-54pillar-recovery --clean-room --json
```

## Phase 308（`55/55` 恢复支柱里程碑 / Pillar 55）：`[Lens Compensation]`（`Shading Comp.` 仅 `Auto`/`Off` vs 休眠 `Auto: Low` `0x6c9c` `EOPNOTSUPP=95`）、机身前置 `[AF Illuminator]` LED `#8` vs 零发光器 `FX6`、`[Aperture Drive]`/`[Circ. of Focus Point]`/`[Focus Area Color]` `Initialize`-only 留存，及 `[Create New Folder]` + 回放 `[Rating]` `1..5` 星 `Slot-1` Tier-0 金库 `EROFS`/`EBUSY` 防火墙（`verify-55pillar-recovery` / `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault`）

- **[`realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py`](fx3_recovery/realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-53）落地 **Phase 308 Pillar 55（`55/55` 里程碑）** 并将全套恢复总检正式推进至 **`55/55`（`VERIFIED_55OF55_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..54pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P308_SLOT1_FORMAT_HARD_LOCKED = True`、`P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **18 项** Wave-53 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 55A — `[Lens Compensation]`（`Shading Comp.` `Auto`/`Off` vs 休眠 `Auto: Low`、镜头/SteadyShot Active 强制 `Distortion = Auto` 与零 `.ARW` 烘焙）、Movie AF 速率/灵敏度/`AF Assist` 及内置前置 `[AF Illuminator]` LED `#8`（`0.3..3.0 m`）+ MI-Shoe 对比零内置灯 `ILME-FX6`（`6/6`）**：
    - `P55A1`..`P55A6`：精确验证 `ILME-FX3 Ver. 7.02` `[Shooting] -> [Image Quality/Rec] -> [Lens Compensation]`（`_f.uxc` `0x75c8` / `.uxc` `0x631f`）中 `[Shading Comp.]`（`BKID_APP_setting_lens_comp_shading`，`_f.uxc` `0x64e1`，`Initialize`-only）**仅暴露 `Auto` / `Off`**，对休眠枚举 `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` / `_f.uxc` `0x6c9c`（`Auto: Low`）严格 fail-closed 拒绝并返回 `EOPNOTSUPP=95`；验证 `[Chromatic Aberration Comp.]`（`Auto`/`Off`）、`[Distortion Comp.]`（`Auto`/`Off`，对未校正镜头或 Movie `[SteadyShot] = Active` 强制锁定 `Auto` 且绝不烘焙至 `.ARW` 原始像素）、Movie 专属 `[Breathing Comp.]`（`Ver. 3.00+`、`Camera Settings Reset` 复位、HDMI 外录 RAW/不兼容镜头禁用）及无触点手动镜头置灰锁定；严格对照 `ILME-FX6 Ver. 6.01` 位于 `Technical > Lens`（非 `Project/Paint/Lens`）、保存于 `All File` 且受 `Distortion=Off`/`S&Q=On`/`RAW` 锁定的架构边界。校验 Movie `[AF Transition Speed]`（`1..7`，默认 `5`）、`[AF Subj. Shift Sensitivity]`（`1..5`，默认 `5(Responsive)`）及 `[AF Assist]`（默认 `Off`、`SELP1650`/`SEL18200LE` 禁用，随 `Camera Settings Reset` 复位）。落地**关键硬件纠偏**：对比 `ILME-FX6` **零内置 AF 辅助灯**（仅 `appFw.so` 中 6 个休眠 Alpha 符号），`ILME-FX3` 具备物理机身前置内置 AF 辅助灯/自拍定时灯 LED（`TP1000886886.html` `#8`，有效距离 `0.3..3.0 m`）及 MI-Shoe 外接闪光灯 AF 辅助灯，**仅在 Still `AF-S`（及静止 `AF-A`）生效**，在 `Movie`、`S&Q`、`AF-C`、`MF`、`Silent Mode = On`、对焦放大与卡口转接环下硬锁闭。
  - **支柱 55B — `[Aperture Drive in AF]` / `[AF w/ Shutter]` / `[Pre-AF]` / `[Circ. of Focus Point]`（正交仅限水平/垂直、禁止对角回绕） / `[Focus Area Color]` `Initialize`-only 留存，及 `[Create New Folder]` + 回放 `[Rating]` `1..5` 星 `Slot-1` Tier-0 金库 `EROFS`/`EBUSY` 防火墙（`6/6`）**：
    - `P55B1`..`P55B6`：验证全部 5 项 `Initialize`-only 对焦/光圈参数跨越 `[Camera Settings Reset]` 完整留存且仅随 `[Initialize]` 复位至出厂默认：`[Aperture Drive in AF]`（`Focus Priority` 需确认高速连拍降速与机械音告警 `_g.uxc` `0x63e2` / `Standard` 默认 / `Silent Priority`）、仅静态 `[AF w/ Shutter]`（默认 `On`）与 `[Pre-AF]`（默认 `Off`，受 `LENS_PRE_AF_SUPPORT` 镜头门控）、`[Circ. of Focus Point]`（默认 `Does Not Circulate`，**仅限正交水平/垂直环绕、硬拒绝 `Diagonal` 对角回绕**）及 `[Focus Area Color]`（默认 `White`/`Red`），并与无此 5 项（使用电影 `Iris`）的 `ILME-FX6` 严格隔离。验证 `[File/Folder Settings]`（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`、`Series`/`Reset`、3 字符 `[Set File Name]` 前缀 `DSC` 禁用前导 `_`、单夹 `4,000` 张上限）与回放 `[Rating]`（`1..5` 星 `FUNC_rating_content`、`[Rating Set(Custom Key)]` 与仅静态 `[Add Rating]` 无覆盖护栏 `_g.uxc` `0x627d`）；并强执行**关键恢复金库防火墙**：只要 `Slot 1` 挂载 Tier-0 恢复金库（或启用双卡同时录制触及 `Slot 1`），`[Create New Folder]`、`[Forced File Number Reset]`、双卡 `[Select REC Folder]`、回放 `[Rating]`（篡改卡上 EXIF/XMP 与 `AVF_INFO` 数据库）及 `[Add Rating]` 均 MUST fail-closed 返回 `EROFS=30` / `EBUSY=16`（后台传输期），确保 `slot1_data_sector_writes == 0`、`slot1_folder_dir_mutation_bytes == 0`、`slot1_rating_avf_info_mutation_bytes == 0`、`slot1_vault_mutation_bytes == 0`。
  - **统一 `55/55` 恢复支柱里程碑聚合器与 CLI（`evaluate_realhw_55pillar_recovery_master` / `evaluate_55pillar_recovery_master` / `verify-55pillar-recovery` / `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault`）**：
    - 并发调用 `evaluate_realhw_54pillar_recovery_master`（`Pillars 1..54`）+ **Pillar 55**（`run_pillar55_standalone_suite`），汇总产出 **`55/55`（`VERIFIED_55OF55_PILLAR_RECOVERY_MASTER`）**与规范摘要哈希，并接入 Milestone 295 自动最高支柱发现接口；[`tests/test_realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py`](tests/test_realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py) 提供 **85 项**双模（本地只读供体 + `FX3_CLEAN_ROOM_TEST=1` + `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-pillar55-lens-comp-af-illuminator-folder-rating-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-55pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  python3 -B -m fx3_recovery verify-55pillar-recovery --force-clean-room --json
```

## Phase 314（`56/56` 恢复支柱 / Pillar 56）：Still-only `[Switch V/H AF Area]` `0/90/270/INVALID` + 14 项 `[Focus Area Limit]` `>= 2` vs 休眠 `xl/xs/custom_1..3` + `Initialize`-only `[Focus Area Color]` vs `FX6`，5 模式 `[Exposure Std. Adjust]` `1/6 EV` + Still `[Bracket Settings]`、7 项 `Initialize`-only `[TC/UB]` & `[TC/UB Disp. Setting]` `23.98p/24p/PAL` 锁 vs `FX6` 物理 BNC `TC IN/OUT`，及 `Slot-2 -> Slot-1` 反向 `[Copy]` Tier-0 金库 `EROFS=30`/`EBUSY=16` 防火墙 + `[Slide Show]` 省电旁路（`verify-56pillar-recovery` / `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault`）

- **[`realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py`](fx3_recovery/realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-54）落地 **Phase 314 Pillar 56（`56/56`）** 并将全套恢复总检正式推进至 **`56/56`（`VERIFIED_56OF56_PILLAR_RECOVERY_MASTER`，`schema_version = "realhw_56pillar_recovery_master_v1"`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..55pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P314_SLOT1_FORMAT_HARD_LOCKED = True`、`P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-54 供体（`< 0.20s`，CI 下放宽至 `< 0.50s`），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 56A — `[Switch V/H AF Area]` Still `AF-C` 专属（`0/90/270/INVALID` 方向 + 8 项 `EBUSY=16` 锁定 + 切换清坐标）+ 精确 14 项 `[Focus Area Limit]`（`>= 2` `.uxc 0xea28 -> EINVAL=22` vs 休眠 `xl/xs/custom_1..3 -> EOPNOTSUPP=95`）+ `Initialize`-only `[Focus Area Color]` vs 零切换 `ILME-FX6`（`6/6`）**：
    - `P56A1`..`P56A6`：精确验证 `[Switch V/H AF Area]`（`_f.uxc 0x73ae`，`BKID_APP_setting_vertical_horizontal_focus_area_switch`：`Off` 默认 / `AF Point Only` `0x615a` / `AF Point + AF Area` `0x69e8`）**仅在 Still `AF-C` 生效**，跟踪 `0_DEGREES`/`90_DEGREES`/`270_DEGREES`，镜头垂直俯仰返回 `INVALID` 不切换，并在 Movie、`S&Q`、非 `AF-C`、`iAuto`、数码变焦、AF 进行中、连拍、自拍倒计时及 `[Focus Magnifier]` 下锁定（`EBUSY=16`），变更模式即清除三向记忆坐标并随 `[Camera Settings Reset]` 复位；核验 `[Focus Area Limit]`（`_f.uxc 0x6de2`）精确暴露 **14 项** `BKID_APP_focus_area_limit_*`（7 非追踪 + 7 仅 Still `Tracking:*`），强制启用数 `>= 2`（`.uxc 0xea28 -> EINVAL=22`）并拦截共享 BIONZ XR 休眠符号 `flexible_spot_{xl,xs}` / `custom_{1..3}`（`EOPNOTSUPP=95`）；校验 `[Focus Area Color]`（`_f.uxc 0x74ad`，`White` `.uxc 0xe883` / `Red` `.uxc 0xe8c6`）跨 `[Camera Settings Reset]` 留存并仅随 `[Initialize]` 复位，与无自动切换/无限制菜单/移动变橙框及 `Focus Area Ind.(AF-S)` `0x2236` 的 `ILME-FX6` 严格划界。
  - **支柱 56B — 全 5 模式 `[Exposure Std. Adjust]` `1/6 EV` `Initialize`-only 校准 + Still `[Bracket Settings]`、7 项 `Initialize`-only `[TC/UB]` & `[TC/UB Disp. Setting]` `23.98p/24p/PAL` 锁 vs `FX6` BNC `TC IN/OUT`，及 `Slot-2 -> Slot-1` 反向 `[Copy]` Tier-0 金库 `EROFS=30`/`EBUSY=16` 防火墙 + `[Slide Show]` 省电旁路（`6/6`）**：
    - `P56B1`..`P56B6`：精确消歧并核验 `[Exposure Std. Adjust]`（`_f.uxc 0x6114`/`0x6f71`，`.uxc 0xe567` 确认提示）支持**全部 5 种测光模式**（`Multi` `0x6d79`、`Center` `0x6da8`、`Spot` `0x7a8a`、`Entire Screen Avg.` `0x6f15`、`Highlight` `0x7600`）× 13 档（`-1..+1 EV @ 1/6 EV`），独立写入 EXIF 不篡改 `[Exposure Comp.]`、同步偏移 `M.M.` 零点、包围中途修改复位已拍张数且**仅随 `[Initialize]` 复位**；校验 Still `[Bracket Settings]`（`Selftimer during Bracket` `Off/2/5/10 Sec`、`Bracket order` `0->-->+` / `-->0->+`）可经 `[Camera Settings Reset]` 复位并隔离 FX6 零命中/休眠 `bracket_*`（`ENOENT=2`）。核验全部 6 项 `(Shooting) -> [TC/UB]` + `(Setup) -> [Display Option] -> [TC/UB Disp. Setting]`（`Counter`/`TC`/`U-Bit`，回放仅动态影像可切换 `.uxc 0xe728`）全部跨 `[Camera Settings Reset]` 留存（`Initialize`-only），`[Time Code Format]`（`DF`/`NDF`）仅限 NTSC、`23.98p`/`24.00p` 强制 `NDF`（`[-]`）且 `PAL` 下隐藏，对照 `ILME-FX6` 物理 BNC `TC IN/OUT`（`EXT-LK`）与 `Users Bit Mode: Fix/Time`。强执行**关键反向 `[Copy]` Tier-0 恢复金库防火墙**：`MENU -> Playback -> Edit -> [Copy]`（`FUNC_copy_content`）从 `[Select Playback Media]` 复制到对侧槽位；`Slot 1 -> Slot 2` 仅只读源卡并清除目标卡群组与 `Protect`，一旦切换为 **`[Select Playback Media] = Slot 2` 并调用 `[Copy]`，即试图向 `Slot 1` 大量写盘并改写 `AVF_INFO`** — 只要 `Slot 1` 挂载 Tier-0 恢复金库即 MUST fail-closed（`EROFS=30` / `EBUSY=16`，`slot1_data_sector_writes == 0`，`slot1_copy_avf_info_mutation_bytes == 0`）；同时校验 `[Slide Show]`（`Repeat: Off`、`Interval: 1/3/5/10/30 Sec` 默认 `3 Sec`）`Initialize`-only 留存并旁路 `[Power Save Start Time]`，及 FX6 休眠 `Copy Clip`。
  - **统一 `56/56` 恢复总检聚合器与 CLI（`evaluate_realhw_56pillar_recovery_master` / `evaluate_56pillar_recovery_master` / `verify-56pillar-recovery` / `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault`）**：
    - 并发调用 `evaluate_realhw_55pillar_recovery_master`（`Pillars 1..55`）+ **Pillar 56**（`run_pillar56_standalone_suite`），汇总产出 **`56/56`（`VERIFIED_56OF56_PILLAR_RECOVERY_MASTER`）** 与规范摘要哈希，并接入 Milestone 311 / 295 自动最高支柱发现接口；[`tests/test_realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py`](tests/test_realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py) 提供 **88 项**双模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-56pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-56pillar-recovery --force-clean-room --json
```

## Phase 320（Pillar 57 / `57/57` 统一恢复总检里程碑）：Wave-55 `[Touch Operation]` 4 项 `Initialize` 专属树 vs 休眠触控陷阱、4 拍摄/3 回放 `DISP` 零 EVF 黑屏防线、静态专用 `[AEL w/ Shutter]` 与 `[Flash]` 子菜单复位分化、9 档间隔连续回放及回放 `[Edit]` `Slot-1` `EROFS=30` 金库防火墙（`verify-57pillar-recovery` / `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault`）

- **[`realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](fx3_recovery/realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-55）落地 **Phase 320 Pillar 57（`57/57`）** 并将全套恢复总检推进至 **`57/57`（`VERIFIED_57OF57_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..56pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P320_SLOT1_FORMAT_HARD_LOCKED = True`、`P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-55 供体（`< 0.20s`，CI 下放宽至 `< 0.50s` 且显式防护 `work_root is None` 避免无供体 runner `NoneType / str` 异常），并支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - **支柱 57A — Wave-55 `[Touch Operation]` 4 项 `Initialize` 专属菜单树 vs 休眠 Alpha 触控陷阱（`EOPNOTSUPP=95`）、`[Operation Customize] -> [DISP (Screen Disp) Set]` 4 拍摄/3 回放分页与零 EVF 黑屏防线 + FX6 边界（`6/6`）**：
    - `P57A1`..`P57A6`：精确建模 `MENU -> (Setup) -> [Touch Operation]`（`_g 0x6345`）**全部 4 项有效配置且全员仅随 `[Initialize]` 复位**（`[Camera Settings Reset]` 不重置）：`[Touch Operation]`（`On` 默认 / `On: Playback Only` `_f 0x6cde` / `Off`）、`[Touch Sensitivity]`（`Standard` 默认 / `Sensitive` `_f 0x7205`，禁止误标 `Responsive`）、`[Touch Func. in Shooting]`（Still/Movie/`S&Q` 完全统一：`Touch Focus` / `Touch Tracking` 默认 / `Off`）、`[Swipe Up]`（`Open the Fn Menu` 默认 / `Off`，仅当 `Touch Operation == On` 生效）；Fail-closed `EOPNOTSUPP=95` 拦截 `FX3 appFw.so`/UXC 中 0 命中休眠符号（`Touch Shutter`、`Touch AE`、`Touch Panel/Pad`、`Touch Pad Settings`、`Footer Icon Touch`、`Swipe Left/Right`）并与 `ILME-FX6 Ver. 6.01`（`Technical > Touch Operation` `On/Off` + `Touch Function in MF` `Spot Focus`/`Tracking AF`，无灵敏度与上滑菜单）严格划界；精确建模 `[Operation Customize] -> [DISP (Screen Disp) Set]`（`_g 0x61c4 -> 0x61da`，`Initialize` 专属，非 `Display Option`）**4 页拍摄**（`Display All Info.`、`No Disp. Info.`、`Histogram`、`Level`）与**3 页回放**（`Display Info.`、`Histogram`、`No Disp. Info.`），强制 **Zero-EVF Blackout Guard**（`ILME-FX3` 无内置 EVF、无眼感器、无 `FINDER/MONITOR` 键，对 `Select Finder/Monitor`、`For viewfinder`、`Graphic Display`、`Monitor Off` 强制 `EOPNOTSUPP=95`，杜绝 Stage-B/恢复脚本切至幽灵 EVF 导致机身屏黑屏，并对比 `FX6` `TYPE_BUILTIN_EVF_NOT_EXIST` 可拆式 3.5" LCD `Viewfinder` + `Viewfinder Hood` + `Monitoring > Display On/Off`，严禁 `Loupe` 误称）。
  - **支柱 57B — 静态专用 `[AEL w/ Shutter]` 与 `[Flash]` 子菜单复位分化、`Playback -> [Viewing]` 9 档间隔连续回放及 `Playback -> [Edit]` `Slot-1` `EROFS=30` 金库防火墙（`6/6`）**：
    - `P57B1`..`P57B6`：精确校验 **4 项 Still 专属（Movie/`S&Q` 不可用 -> `EOPNOTSUPP=95`）测光/闪光菜单的非对称 `[Camera Settings Reset]` 行为**：`[AEL w/ Shutter]`（`Auto`/`On`/`Off`，`Initialize` 专属，`[AEL toggle]` 覆盖半按锁）、`[Exp.comp.set]`（`Ambient&flash`/`Ambient only`，`Initialize` 专属）、**`[Wireless Flash]`（`Off`/`On`，4 项中唯一会被 `Camera Settings Reset` 复位的项！）**、以及仅限机顶 MI 热靴直插（拒绝有线同步口离机与机内菜单复位）的 `[External Flash Set.]`（`Initialize` 专属），对比无机械快门/无静态管线的 `ILME-FX6`（仅滚动快门 `Flash Band Reduce`）；校验 `MENU -> (Playback) -> [Viewing]`（非 `Playback Option`）下 `[Cont. Play for Interval]` 与 `[Play Speed for Interval]` **精确 `1..9` 档步进（默认 `5`，`Initialize` 专属、纯只读 `safe_read_only=True`、不合成延时视频）**；强制 `MENU -> (Playback) -> [Edit]`（`[Rotate]`、`[Photo Capture]` + `[JPEG/HEIF Switch]`、`[Copy]`，以及休眠 `[Beauty Effect]`/`[Trimming]`）`Slot-1` Tier-0 金库防火墙——写操作在 `[Select Playback Media]` 默认 `Slot 1` 下直指金库时强制 `EROFS=30`（`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`），`Slot 2` 允许安全操作，休眠 `Beauty Effect`/`Trimming` 全局 `EOPNOTSUPP=95`（靶向 `Slot 1` 时叠加 `EROFS=30`）。
  - **统一 `57/57` 恢复总检聚合器与 CLI（`evaluate_realhw_57pillar_recovery_master` / `evaluate_57pillar_recovery_master` / `verify-57pillar-recovery` / `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault`）**：
    - 并发调用 `evaluate_realhw_56pillar_recovery_master`（`Pillars 1..56`）+ **Pillar 57**（`run_pillar57_standalone_suite`），在 `< 1.5s` 内汇总产出 **`57/57`（`VERIFIED_57OF57_PILLAR_RECOVERY_MASTER`）** 与规范摘要哈希，并自动接入 Milestone 311 / 295 最高支柱发现接口；[`tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py) 提供 **>= 86 项**双模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-57pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-57pillar-recovery --force-clean-room --json
```

## Phase 326（Pillar 58 / `58/58` 统一恢复总检里程碑）：Wave-56 `[Dial Customize]` 5 项 `Initialize` 专属树与 3 转盘拓扑、`My Dial 1..3` 临时解锁与 `Fn 12+12` 拆分、`[Live View Display Set.]` 3 项非对称复位、`[Grid Line]` Clean-HDMI 隔离及 `[Embed LUT File]` 内嵌容器 vs `PPLUT1..4` 烘焙与 `Slot-1` 金库防火墙（`verify-58pillar-recovery` / `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault`）

- **[`realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py`](fx3_recovery/realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-56）落地 **Phase 326 Pillar 58（`58/58`）** 并将全套恢复总检推进至 **`58/58`（`VERIFIED_58OF58_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..57pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P326_SLOT1_FORMAT_HARD_LOCKED = True`、`P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-56 供体（`< 0.20s`，CI 下 `< 0.50s` 且显式防护 `work_root is None` 以避免无供体 Ubuntu CI 触发 `NoneType / str` 异常），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **支柱 58A — Wave-56 `[Dial Customize]` 5 项 `Initialize` 专属树 vs 休眠 `[Dial Setup]`/`[Dial / Wheel Lock]`/`Rear Dial L/R`（`EOPNOTSUPP=95`）、`My Dial 1..3` 跳空与锁覆盖及 `[Fn Menu Settings]` `12 + 12` 拆分 + FX6 边界（`6/6`）**：
    - `P58A1`..`P58A6`：精确建模 `MENU -> (Setup) -> [Dial Customize]`（`_g 0x62ed`）全 **5 项 `Initialize` 专属**配置（`[Custom Key/Dial Set.]` 取代 Ver. 1.xx `[Dial Setup]`、`[My Dial Settings]` `1..3`、`[Av/Tv Rotate]` `Normal`/`Reverse`、`[Function Ring(Lens)]` `Power Focus` / `APS-C/Super 35 mm / Full Frame` 并拦截 `INVALID`、`[Lock Operation Parts]` `Off`/`Multi-Selector Only`/`Dial + Wheel`/`All` 取代 `[Dial / Wheel Lock]` 并支持长按 `Fn` 锁/解锁与 5 秒 `MENU + Fn` 全锁）；强制 **3 物理转盘拓扑**（`Front Dial`、单 `Rear Dial`、`Control Wheel`），fail-closed `EOPNOTSUPP=95` 拦截休眠 `Rear Dial L/R`、`Dial Setup`、`Dial/Wheel Setup` 与 `Dial / Wheel Lock`；校验 `My Dial 1..3` `Hold`/`Toggle`/`1->2->3` 自动跳过全 `Not set` 空组并在激活期间临时解锁 `[Lock Operation Parts]`；校验 `[Operation Customize] -> [Fn Menu Settings]` 严格 `12 Still + 12 Movie` 槽位（`0..11`，全 `Not set` 触发 `_f 0x6220` 无效提示）；并与 `ILME-FX6`（`Multi Function Dial`、`Grip/Handle/IRIS/ND Dial`、物理 `HOLD` 开关、`Status Screens` 与 `Direct Menu`）严格划界。
  - **支柱 58B — `[Live View Display Set.]` 3 项非对称复位、`[Grid Line]` Clean-HDMI/RAW 隔离与 `[Manage User LUTs]`/`[Embed LUT File]` 内嵌容器 vs `PPLUT1..4` 烘焙及 `Slot-1` 金库防火墙（`6/6`）**：
    - `P58B1`..`P58B6`：精确建模 `Shooting -> [Shooting Display] -> [Live View Display Set.]` Still 专属 3 项非对称复位分化（`[Live View Display]` `Setting Effect ON/OFF` `Initialize` 专属且随 `[Bright Monitoring]` 自动切 `OFF`、`[Exposure Effect]` `Exposure Set. & flash`/`Exposure Setting Only` `Initialize` 专属、**`[Frame Rate Low Limit]` `On/Off` 为唯一支持 `Camera Settings Reset` 的可复位项**）；校验 `[Grid Line Display]`（默认 `Off`）与 `[Grid Line Type]`（`Rule of 3rds Grid`/`Square Grid`/`Diag. + Square Grid`）在 `HDMI Info. Display = Off` 或 RAW/`Off(HDMI Only)` 下严格隔离于机身 LCD（对比 FX6 `Monitoring > Marker > Guide Frame` 与休眠 PNG 网格）；校验 `Exposure/Color -> [Color/Tone] -> [Manage User LUTs]`（`User1..16` `17/33-pt .cube`，SD/SDXC `/Private/Sony/PRO/LUT`、CFexpress `/Sony/PRO/LUT`，`Slot-1` 纯只读导入且零创建目录时放行）与 `[Select LUT]`（默认 `s709` 可复位，空 User 槽回退 `S-Log3`）vs `Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]`（默认 `On` 可复位，不在 `Color/Tone` 下，容器元数据内嵌保留原生 `S-Log3` 像素，SD/SDHC 下硬件锁死 `Off` `_g 0x61a0`）vs `Picture Profile -> PPLUT1..4`（不可逆 DSP 像素烘焙，随 Reset/Initialize 重置，区别于 `PP1..PP11`）vs FX6 `Base Look`（`16` 槽上限 vs 休眠 `0..49`、多通道独立开关）；并在 `Slot-1` 挂载 Tier-0 保险库时对任何指向 `Slot-1` 的写盘/内嵌录制/烘焙/建目录/格式化强制 `EROFS=30`（`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`）。
  - **统一 `58/58` 恢复总检聚合器与 CLI（`evaluate_realhw_58pillar_recovery_master` / `evaluate_58pillar_recovery_master` / `verify-58pillar-recovery` / `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault`）**：
    - 并发调用 `evaluate_realhw_57pillar_recovery_master`（`Pillars 1..57`）+ **Pillar 58**（`run_pillar58_standalone_suite`），在 `< 1.5s` 内汇总产出 **`58/58`（`VERIFIED_58OF58_PILLAR_RECOVERY_MASTER`）** 与规范摘要哈希，并自动接入 Milestone 311 / 295 最高支柱发现接口；[`tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py`](tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py) 提供 **>= 88 项**双模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-58pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-58pillar-recovery --force-clean-room --json
```

## Phase 332（Pillar 59 / `59/59` 统一恢复总检里程碑）：Wave-57 `SteadyShot` 5 轴 IBIS 47 档焦距与 4 重锁死 / 休眠电影自拍 vs 静态自拍 `#8` 灯与提示音 / `Zebra Custom1-2` IRE 与 4 色峰值 Clean-HDMI 隔离 / `RTMP/RTMPS/SRT` 推流零射频与 `Slot-1` 金库防火墙（`verify-59pillar-recovery` / `verify-pillar59-recovery` / `verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault`）

- **[`realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py`](fx3_recovery/realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-57）落地 **Phase 332 Pillar 59（`59/59`）** 并将全套恢复总检推进至 **`59/59`（`VERIFIED_59OF59_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..58pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P332_AIRPLANE_MODE_FORCED_ON = True`、`P332_RF_PACKETS_TRANSMITTED = 0`、`P332_SLOT1_FORMAT_HARD_LOCKED = True`、`P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-57 供体（`< 0.20s`，CI 下 `< 0.50s` 且显式防护 `work_root is None` 以避免无供体 Ubuntu CI 触发 `NoneType / str` 异常），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 59A（`SteadyShot` 47 档焦距与 4 重锁死 + 休眠电影自拍 vs 静态自拍 `#8` 灯/提示音 + FX6 无机身防抖边界）**：锁定 `Shooting -> [Image Stabilization]` 4 项（Movie `Active/Standard[default]/Off`、Still `On[default]/Off`、`SteadyShot Adjust.` `Auto[default]/Manual`、精确 **47 档** `Focal Length` `8..1000mm` 默认 `8mm`，全部 Resettable）；`Active` 约 `1.104x` 裁切、强制 `Distortion Comp. = Auto` 并在 **4 条件**（`Movie >= 100p/119.88p`、`S&Q >= 100/120fps`、`HDMI RAW = On`、`De-Squeeze != Off`）锁死；休眠 `Dynamic active`（`_f 0x741c`）严格返回 `EOPNOTSUPP=95`；FX6 无机身 IBIS（`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`）。锁定电影 `[Self-timer]`（`BKID_APP_setting_movie_self_timer` / `Rec Start delay`）休眠（`EOPNOTSUPP=95`）vs 静态 `[Drive Mode]` 6 种连续自拍组合、`#8` 前灯与 `Initialize` 专属 `[Audio signals]`（`Silent Mode = On` 或电影 HDMI 音频时静音），及 FX6 `Picture Cache Rec` / `Interval Rec` 边界。
  - **Sub-Pillar 59B（`Zebra Custom1/2` IRE、`4 色 Peaking` Clean-HDMI 隔离与 `RTMP/RTMPS/SRT` 推流零射频 / `Slot-1 EROFS=30` 金库防火墙）**：锁定 `Initialize` 专属 `[Zebra Display]` 与 `[Zebra Level]`（`70..100+`、`Custom1` `Std+Range 0..109 ± 1..10%`、`Custom2` `Lower Limit 0..109+`，`Display LUT = On` 时测 LUT 后信号）及 4 色 `[Peaking Display]`（`Red/Yellow/Blue/White[def]`，Clean-HDMI 隔离），对照 FX6 互斥 `Off / Zebra1 / Zebra2`（非 `Both`）与 `B&W/Red/Yellow/Blue`。锁定 `Network -> [Streaming] -> [Network Streaming]`（`RTMP`/`RTMPS`/`SRT`、`59.94/50/29.97/25p` 禁止 `23.98p/24p`、`[Movie Rec During Streaming]` 4K 锁死与 `Reset Network Set.` 保留 `Airplane Mode = On`），强制零射频（`rf_packets_transmitted == 0`）与 `Slot-1` Tier-0 恢复金库 `EROFS=30` 防火墙 + `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `59/59` 恢复总检聚合器与 CLI（`evaluate_realhw_59pillar_recovery_master` / `evaluate_59pillar_recovery_master` / `verify-59pillar-recovery` / `verify-pillar59-recovery` / `verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault`）**：
    - 并发调用 `evaluate_realhw_58pillar_recovery_master`（`Pillars 1..58`）+ **Pillar 59**（`run_pillar59_standalone_suite`），在 `< 1.5s` 内汇总产出 **`59/59`（`VERIFIED_59OF59_PILLAR_RECOVERY_MASTER`）** 并自动接入 Milestone 311 / 324 最高支柱发现接口；[`tests/test_realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py`](tests/test_realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py) 提供 **>= 90 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar59-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-59pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-59pillar-recovery --force-clean-room --json
```

## Phase 336（Pillar 60 / `60/60` 统一恢复总检里程碑）：Wave-58 `Bright Monitoring` Ver.7.00+ 放大对焦共存与监视器亮度 / 机械快门 `BULB` 与 `DRO` vs 休眠 `Bulb Timer`/`Auto HDR` / `Shot Mark 1-2` 与 `Clip Flag` vs 休眠 `Divide/Extract`、`VMC-BNCM1 EXT-LK`、`WPA3-SAE` + `USB-LAN` 零射频与 `Slot-1 EROFS=30` 金库防火墙（`verify-60pillar-recovery` / `verify-pillar60-recovery` / `verify-pillar60-bright-mon-shotmark-usblan-bulb-vault`）

- **[`realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py`](fx3_recovery/realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-58）落地 **Phase 336 Pillar 60（`60/60`）** 并将全套恢复总检正式推进至 **`60/60`（`VERIFIED_60OF60_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..59pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P336_AIRPLANE_MODE_FORCED_ON = True`、`P336_RF_PACKETS_TRANSMITTED = 0`、`P336_SLOT1_FORMAT_HARD_LOCKED = True`、`P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-58 供体（`< 0.20s`，CI 下 `< 0.50s` 且显式防护 `work_root is None` 以避免无供体 Ubuntu CI 触发 `NoneType / str` 异常），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 60A（`Bright Monitoring` Ver.7.00+ 放大对焦共存、`Monitor Brightness` 手动/晴天模式、机械 `BULB` 与 `D-Range Optimizer` vs 休眠 `Bulb Timer`/`Auto HDR` + FX6 `VF Setting` / `AE Backlight` 边界）**：锁定仅自定义键可触发的 `[Bright Monitoring]`（强制 `Live View Display = Setting Effect OFF`；关机、切离 `P/A/S/M` 或切离 `MF` 时自动取消；**Ver. 7.00/7.02 解锁与 `[Focus Magnifier]` 及 `[Auto Magnifier in MF]` 并发共存**；无多档增益/区域扩展）、`Initialize` 专属 `Setup -> [Monitor] -> [Monitor Brightness]`（`Manual -2..+2` 默认 `0` / `Sunny Weather`，休眠 `Auto` 严格拒绝 `EOPNOTSUPP=95`），对照 FX6 `VF Setting > Brightness (1..15)` 与 `Auto Exposure > Mode > Backlight` 命名歧义隔离。锁定静态机械快门专属 `[BULB]`（在 `Electronic Shutter`、连拍、包围或间隔下自动退回 `30"` 并在激活时禁用 `Anti-flicker Shoot.`）与可复位 `[D-Range Optimizer]`（`Auto[默认]/Off/Lv1..5` 及 `DRO Bracket`，`Picture Profile != Off` 或 `HLG Still Image = On` 时锁死），以及严格 fail-closed 的休眠 `[Bulb Timer]`（`_f 0x630f`）与 `[Auto HDR]`（`base 0xe49d`，`EOPNOTSUPP=95`）。
  - **Sub-Pillar 60B（`Shot Mark 1/2` 与 Ver.6.00+/7.00+ `Clip Flag` `OK/NG/KEEP` vs 休眠 `Divide/Extract`、`VMC-BNCM1 EXT-LK`、WPA3-SAE 与 `USB-LAN` 零射频飞行隔离 + `Slot-1 EROFS=30` 金库防火墙）**：锁定录制/回放 `[Shot Mark 1/2]`（`*M01.XML`）、`[Clip Flag]`（`OK/NG/KEEP`）、`[Image Jump Setting]` 及 `[Edit]`（`Photo Capture`、`JPEG/HEIF Switch`、`Copy`、`Rotate`、`Create Divider Frame`），严格阻断在 FX3 `appFw.so` 中 0 命中的休眠 `[Divide]` / `[Extract]` / `Cut to 15/30/60s`（`EOPNOTSUPP=95`）。锁定零蓝牙 `[Timecode Link]` / `UltraSync BLUE`（`0` 命中 -> `EOPNOTSUPP=95`）与 Multi/Micro USB `VMC-BNCM1` 有线 LTC `EXT-LK` + HDMI `TC Output`（对照 FX6 物理 `TC IN/OUT` BNC），锁定 Wi-Fi SKU 边界（`WW728473` `2.4/5GHz` vs `WW558244` `2.4GHz`）、Ver. 7.00+ 剔除 `WEP/WPA-PSK/IPsec` 强制 `WPA2-PSK/WPA3-SAE`、`USB-LAN`（`cdc_ncm`/`r8152`）与 Wi-Fi/Multi USB 互斥、`Airplane Mode = On` 在 `Reset Network Set.` 与 `Initialize` 后均保持开启（`rf_packets_transmitted == 0`），以及保护 `Slot-1` `M4ROOT/*M01.XML`、`AVF_INFO`、`Photo Capture` 与 `Create Divider Frame` 的 Tier-0 金库 `EROFS=30` 防火墙（`Backup.bin H0 == H3`，`16/16`）。
  - **统一 `60/60` 恢复总检聚合器与 CLI（`evaluate_realhw_60pillar_recovery_master` / `evaluate_60pillar_recovery_master` / `verify-60pillar-recovery` / `verify-pillar60-recovery` / `verify-pillar60-bright-mon-shotmark-usblan-bulb-vault`）**：
    - 并发调用 `evaluate_realhw_59pillar_recovery_master`（`Pillars 1..59`）+ **Pillar 60**（`run_pillar60_standalone_suite`），在 `< 1.5s` 内汇总产出 **`60/60`（`VERIFIED_60OF60_PILLAR_RECOVERY_MASTER`）** 并自动接入 Milestone 311 / 324 最高支柱发现接口；[`tests/test_realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py`](tests/test_realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py) 提供 **>= 96 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar60-bright-mon-shotmark-usblan-bulb-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar60-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-60pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-60pillar-recovery --force-clean-room --json
```

## Phase 340（Pillar 61 / `61/61` 统一恢复总检里程碑）：Wave-59 `BIG6` Home 主屏幕与手动 `Framing Settings` vs 休眠 `Auto Framing` / 静态 `Interval Shoot Func.` 9,999 张 `Slot-1 EROFS=30` vs FX6 `Interval Rec` / `Time Code Make/Run` `Regenerate` 强锁 `Rec Run` 与 HDMI `REC Control` / `Access Authen.` SSH+PTP-IP + `Fan Control` 4 档无 `Max` 与 `Slot-1` 金库防火墙（`verify-61pillar-recovery` / `verify-pillar61-recovery` / `verify-pillar61-big6-framing-interval-tc-auth-fan-vault`）

- **[`realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py`](fx3_recovery/realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-59）落地 **Phase 340 Pillar 61（`61/61`）** 并将全套恢复总检正式推进至 **`61/61`（`VERIFIED_61OF61_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..60pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P340_AIRPLANE_MODE_FORCED_ON = True`、`P340_RF_PACKETS_TRANSMITTED = 0`、`P340_SLOT1_FORMAT_HARD_LOCKED = True`、`P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02` 与 `FX6 6.01` 共 **17 项** Wave-59 供体（`< 2.0s` 并发宽容预算且显式防护 `work_root is None` 以避免无供体 CI 触发 `NoneType / str` 异常），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`（同时将旧版 `30..49` 支柱过紧的 `0.15s` donor 读取壁钟阈值统一放宽至 `2.0s` 以消除并发 QEMU 重 I/O 抖动）：
  - **Sub-Pillar 61A（`HOME (BIG6)` 主屏幕与 `Mode Settings=Fixed/Variable` 前置条件 + 手动 `Framing Settings` vs 休眠 `Auto Framing` + 静态 `Interval Shoot Func.` 9,999 张 `Slot-1 EROFS=30` 防火墙 vs FX6 `Interval Rec`）**：锁定 FX3 Ver. 7.00/7.02 `HOME` (`BIG6`) 激活硬前提 `Mode Settings = Fixed/Variable`（`BKID_APP_setting_fps_fixed_variable_select`）、动态 6 格矩阵（`FPS`、`ISO / Base ISO + EI` 经 `update_big6_item_iso_ei`、`Shutter Speed/Angle`、`Home (Lower Left)` 默认 `Aperture` vs 纯手动元数据 `ND Filter` 且无物理 `e-ND` 硬件、`Picture Profile / Select LUT`、`White Balance`）及只读边缘状态条；锁定手动 `[Framing Settings]`（`Framing`、`Recording/Streaming` `Full`/`Crop`、`HDMI` `Crop`/`Full`、`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`、强关 `APS-C S35` 及录制/流传输/`>=100p` 锁定）vs 100% 休眠 AI `[Auto Framing]`（`FX3 appFw.so` `AUTO_FRAMING_AFR` / `PTZAUTOFRAMING_*` 均 `0` 命中 -> `EOPNOTSUPP=95`）；锁定仅生成静态照片的 `[Interval Shoot Func.]`（7 项全部支持 `Camera Settings Reset`，`Shutter Type in Interval = Electronic Shutter` 独立默认，`1..9,999` 张与 `BULB -> 30"` 回退 -> `Slot-1` Tier-0 触发 `EROFS=30` 阻断 `DCIM/` 与 `AVF_INFO` 写卡爆发）对照 `FX6 Project > Interval Rec`（单 XAVC MXF、`1s..24h`、`Pre-Lighting` 与互斥列表）。
  - **Sub-Pillar 61B（不可 Reset `[Time Code Make/Run]` + HDMI `[REC Control]` + Ver. 7.00+ `[Access Authen.]` SSH/TLS + `[Fan Control]` 4 档零 `Max` 对照 + 零射频 / `Slot-1 EROFS=30` 金库防火墙）**：锁定不可随 `Camera Settings Reset` 复位的 `[Time Code Make]`（`Preset`/`Regenerate`：`Regenerate` 在 `Simult. Recording` 下读 Slot 1 且无视选项强按 `Rec Run` 运行；`VMC-BNCM1` LTC `EXT-LK` 要求 `Preset + Free Run`）与 HDMI `[REC Control]`（强制要求 `[Time Code Output] = On`，实测 `Rec. Media = On` 与 `Off(HDMI Only)` 含 RAW 下均有效，`S&Q`/Streaming 受限）及 `[4ch Audio Output]` 对照 `FX6 TC_MAKE_CLOCK` 与 `SDI/HDMI Remote I/F` vs `Parallel Rec`；锁定 Ver. 7.00+ `[Access Authen.]`（基于 `SSH` `MSGID_SSHD_START_CMD` + `PTP-IP` 与 Host Key Fingerprint，`WEP`/`WPA-PSK`/`IPsec` 已移除，`HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS` 均为 `0` 命中，`[Import Root Certificate]` 仅用于 FTPS/RTMPS/Cloud 出站 TLS）；锁定 `[Fan Control]`（FX3 `Auto`/`Minimum`/`Off in Rec`/`Always Off` 4 档 vs FX6 `Auto`/`Minimum`/`Off in Rec` 3 档且 `Always Off` 休眠，**FX3 与 FX6 均不存在 `Max` 选项！**）与 `[Auto Power OFF Temp.]`（`Standard`/`High` 约 `90..120` 分钟，低温烫伤/三脚架警告）、Zero-RF（`Airplane Mode=On` 经 `Reset Network Set.` 保留，USB-LAN `cdc_ncm`）与 `Slot-1 EROFS=30` 金库防火墙 + `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `61/61` 恢复总检聚合器与 CLI（`evaluate_realhw_61pillar_recovery_master` / `evaluate_61pillar_recovery_master` / `verify-61pillar-recovery` / `verify-pillar61-recovery` / `verify-pillar61-big6-framing-interval-tc-auth-fan-vault`）**：
    - 并发调用 `evaluate_realhw_60pillar_recovery_master`（`Pillars 1..60`）+ **Pillar 61**（`run_pillar61_standalone_suite`），在 `< 1.5s` 内汇总产出 **`61/61`（`VERIFIED_61OF61_PILLAR_RECOVERY_MASTER`）** 并自动接入 Milestone 311 / 324 最高支柱发现接口；[`tests/test_realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py`](tests/test_realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py) 提供 **>= 96 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar61-big6-framing-interval-tc-auth-fan-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar61-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-61pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-61pillar-recovery --force-clean-room --json
```

## Phase 344（Pillar 62 / `62/62` 统一恢复总检里程碑）：Wave-60 `[Rec. Media Settings]` 分离演进与 `Auto Switch Media` `Slot-1` 溢出防线 / `VPG200/VPG400` 卡速门禁 / `[Proxy Settings]` `sq_proxy` `XAVC S-I DCI 4K` 放行与 `120p/100p` 锁死 / `[Creators' Cloud]` `*` 抗初始化持久性 / `[Cnct. while Power OFF]` 关机 BLE 零射频护栏 / `[My Menu]` `6×7=42` 槽位 vs FX6 `20` 项 `User Menu with Lock` + `Slot-1 EROFS=30` 金库防火墙（`verify-62pillar-recovery` / `verify-pillar62-recovery` / `verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault`）

- **[`realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py`](fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-60）落地 **Phase 344 Pillar 62（`62/62`）** 并将全套恢复总检正式推进至 **`62/62`（`VERIFIED_62OF62_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..61pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P344_AIRPLANE_MODE_FORCED_ON = True`、`P344_POWER_OFF_BLE_FORCED_OFF = True`、`P344_RF_PACKETS_TRANSMITTED = 0`、`P344_SLOT1_FORMAT_HARD_LOCKED = True`、`P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（14 项）与 `FX6 6.01`（3 项）共 **17 项** Wave-60 供体（`< 2.0s` 预算且显式防护 `work_root is None` 以避免无供体 CI 异常），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 62A（`[Rec. Media Settings]` 演进、`VPG200/VPG400` 门禁、`[Auto Switch Media]` `Slot-1` 溢出防线与 `[Proxy Settings]` `sq_proxy` 规则）**：实证确认旧 Alpha `[Prioritize Rec. Media]`（`_f 0x719e`）在 `FX3 appFw.so` 中 `0` 命中（`EOPNOTSUPP=95`），由拆分的抗 `[Camera Settings Reset]` `[Recording Media]`（Still 4 模式 vs Movie 3 模式零 `Sort Recording`、`Simult. Recording` 同文件系统门禁）与抗 `[Camera Settings Reset]` `[Auto Switch Media]`（`BKID_APP_setting_relay_rec`）替代；强制执行 Tier-0 `Slot-1` 溢出双重闭锁（`RELAY_REC_OFF` + `SLOT_2` + `PRM_HAITA_setting_relay_rec_*_media_read_only_state_slot1` + VFS `EROFS=30`，`slot1_data_sector_writes == 0`），对照 FX6 `Project > Simul Rec` + 双 `Rec Button Set` + 硬互斥；建模 `SDXC V60/V90` vs `CFexpress Type A VPG200/VPG400`（S&Q `1200 Mbps` 强制 CFexpress）；建模 `[Proxy Settings]`（`sq_proxy`，`0` 条 `PRM_HAITA_*proxy*`）中 `XAVC S-I DCI 4K` 允许而仅 Movie `119.88p/100p` 与 `S&Q 120/100fps` 禁用、`XAVC S HD 6M 8bit` / `XAVC HS HD 9M/16M 10bit`、`M4ROOT/SUB/*S03.MP4` 联动保护/删除及 `Slot-1` `EROFS=30` 拦截。
  - **Sub-Pillar 62B（`[Creators' Cloud]` `*` 抗初始化持久性、`[Cnct. while Power OFF]` 关机 BLE 零射频护栏、`[My Menu]` `6×7=42` 槽位 vs FX6 `20` 项 `User Menu with Lock`）**：锁定 `Cloud Connection *` / `Cloud Information *` 在 `[Camera Settings Reset]` 与 `[Initialize]` 后均保持绑定（`FTP` 互斥、`Ver. 7.00+` `Clip Flag` `OK/NG/KEEP`）；锁定 `[Cnct. while Power OFF]`（`BKID_APP_extern_menu_cnct_while_power_off`，`_f 0x6ab3`，抗 `Camera Settings Reset`）在 `On` 且物理开关 `OFF` 时保持 BLE 常驻通电风险，零射频台架必须同时强制 `[Airplane Mode] = On` 且 `[Cnct. while Power OFF] = Off`（`rf_packets_transmitted == 0`，对照无蓝牙的 `ILME-FX6`）；纠正容量误传，实证锁定 FX3 `[My Menu]` 精确为 **`6×7=42` NVRAM 槽位**（`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`，非 30/36，禁用回放且抗 `Camera Settings Reset`）对照 FX6 `20` 项 `User Menu Only` 与 `User Menu with Lock`（`Multi-selector + MENU` + 4 位 PIN，不入 `All File`/`Scene File`），叠合 Stage-B `/tmp` 覆写隔离、`Backup.bin H0 == H3`（`16/16`）与 `Slot-1 EROFS=30`。
  - **统一 `62/62` 恢复总检聚合器与 CLI（`evaluate_realhw_62pillar_recovery_master` / `evaluate_62pillar_recovery_master` / `verify-62pillar-recovery` / `verify-pillar62-recovery` / `verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault`）**：并发聚合 `Pillars 1..61` + `Pillar 62`，自动对接 Milestone 311 / 324 最高支柱发现接口；[`tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py`](tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py) 提供 **`>= 100` 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar62-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-62pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-62pillar-recovery --force-clean-room --json
```

## Phase 348（Pillar 63 / `63/63` 统一恢复总检里程碑）：Wave-61 `[FTP Transfer Func.]` `FTP`/`FTPES` 显式 TLS vs 零 `SFTP` / `9` 服务器槽位 / 休眠 `Transfer JPEG/HEIF Size` / `USB-LAN` 飞行模式旁路与 `Slot-1 AVF_INFO EROFS=30` 防火墙 / 白平衡 `Custom 1..3`、`Cine EI` 锁定与抗复位 `[Shutter AWB Lock]` / Movie `AF Transition Speed 1..7` & `AF Subj. Shift Sens. 1..5` 同等性 / App-Only `[Focus Map]` 辟谣 / 8 项抗复位 `[Marker Display]` 15 比例与 `[Peaking Display]` 4 色零 HDMI 隔离 vs FX6 `User Box`（`verify-63pillar-recovery` / `verify-pillar63-recovery` / `verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault`）

- **[`realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py`](fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-61）落地 **Phase 348 Pillar 63（`63/63`）** 并将全套恢复总检正式推进至 **`63/63`（`VERIFIED_63OF63_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..62pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`P348_AIRPLANE_MODE_FORCED_ON = True`、`P348_USBLAN_BENCH_LOCKED_OFF = True`、`P348_RF_PACKETS_TRANSMITTED = 0`、`P348_USBLAN_PACKETS_TRANSMITTED = 0`、`P348_HDMI_MARKER_PEAKING_LEAK_PIXELS = 0`、`P348_SLOT1_FORMAT_HARD_LOCKED = True`、`P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（14 项）与 `FX6 6.01`（3 项）共 **17 项** Wave-61 供体（`< 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 63A（`[FTP Transfer Func.]` `FTP`/`FTPES` `9` 槽位 Passive-only、零 `SFTP`/休眠 `Transfer JPEG Size`、`USB-LAN` 飞行模式旁路、`Slot-1 AVF_INFO EROFS=30` 与 White Balance `Custom 1..3` / `Cine EI` / `Shockless WB` / `Shutter AWB Lock`）**：实证 `FX3 appFw.so` 对 `sftp`、`ftpes`、`passive_mode` 与 `Transfer JPEG Size` 均 `0` 命中（`EOPNOTSUPP=95`），支持 `Server 1..9`（抗 `[Camera Settings Reset]`、随 `[Reset Network Set.]`/`[Initialize]` 清除）、`FTP` 与 `FTPES`（`FTPS` Explicit TLS `SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`）且仅限 Passive Mode、`Slot 1` 根目录 `cacert.pem`（`<= 1 MB`），对照 `FX6` `Server Settings1..3` + `Active/Passive` + `Slot B` `certification.pem` + `Auto Upload (Proxy): Chunk`；封堵 `[Airplane Mode] = On` 仍放行有线 `USB-LAN` FTP（`USB_ETHER`）的零射频旁路（台架强制双锁 `Airplane Mode = On` + `USB-LAN = Off`），并强制对 `save_ftp_transfer_list_to_media` / `CONTENT_INFO_FTP_TRANS_STAT_*` / `AVF_INFO`（`base 0x0a13`）写入 `Slot 1` 返回 `EROFS=30`；精确建模 White Balance `2500K..9900K`、`Custom 1..3`（不进 `CAMSET*.DAT`、`Log != Off`/`S-Log3`/`PPLUT1..4` 下 `Custom WB Error`）、`Cine EI`/`Cine EI Quick` 锁定 `Auto`/`Underwater Auto`、`Shockless WB`（`Off/1[def]/2/3` 直接色温/tint 微调旁路）与 Still-only **抗复位** `[Shutter AWB Lock]` vs `FX6` `WHT BAL PRST/A/B` + `Memory A..H` + `ATW Speed 1..5`。
  - **Sub-Pillar 63B（Movie `AF Transition Speed 1..7` & `AF Subj. Shift Sens. 1..5` 同等性、`Ver. 6.00+` App-Only `[Focus Map]` 辟谣与 8 项抗复位 `[Marker Display]` 15 比例 + `[Peaking Display]` 4 色 Clean-HDMI 隔离）**：实证修复 `FX6` 认知偏差——`ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 均为 **`AF Transition Speed = 1..7`** 与 **`AF Subj. Shift Sensitivity = 1..5`**（`FX6 appFw.so` 对 `6`/`7` 为 `0` 命中），并检定 `[AF Assist]`（`SELP1650`/`SEL18200LE` 禁用）；证伪机内 `[Focus Map]`（`FX3 appFw.so` 零 `BKID_APP_USER_MENU_FOCUS_MAP`/`ASSIGNABLE_SWITCH_FOCUS_MAP`，机内 `EOPNOTSUPP=95`；仅 `Ver. 6.00+` 通过 *Monitor & Control* `Ver. 2.1.0+` 远程遥测提供且 `>= 150 fps` 如 `200/240fps` 锁定 vs `FX6` 原生机内 `<= 6 fps`/`>= 150 fps` 锁定）；强制 5 项 `[Marker Display]`（含 `Off` + **15 种** `Aspect Marker` 比例 `9:16..2.39:1` = `16` 态、在 `[Focus Magnifier]` 下自动隐藏）与 3 项 `[Peaking Display]`（`High/Mid/Low`、`Red/Yellow/Blue/White`）共 **8 项**全员抗 `[Camera Settings Reset]` 且 Clean-HDMI 输出 **`0 px`**，对照 `FX6` `Aspect Mask 0..15`、`User Box` 像素框（`Width 3..479`/`Height 3..269`/`H -476..+476`/`V -266..+266`）与 `B&W` 峰值颜色，叠加 Stage-B `/tmp` 隔离、`Backup.bin H0 == H3`（`16/16`）与 `Slot-1 EROFS=30`。
  - **统一 `63/63` 恢复总检聚合器与 CLI（`evaluate_realhw_63pillar_recovery_master` / `evaluate_63pillar_recovery_master` / `verify-63pillar-recovery` / `verify-pillar63-recovery` / `verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault`）**：并发聚合 `Pillars 1..62` + `Pillar 63`，自动对接 Milestone 311 / 324 最高支柱发现接口；[`tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py`](tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py) 提供 **`>= 100` 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar63-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-63pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-63pillar-recovery --force-clean-room --json
```

## Phase 352（Pillar 64 / `64/64` 统一恢复总检里程碑）：Wave-62 `[Shoe Audio Set.]` `4ch 24-bit` 与 `XLR-H1`/`3.5mm` 硬件接管优先级 / `[Audio Out Timing]` `Live`/`Lip Sync` 菜单纠偏 / `[Face/Eye Subject]` `Human`/`Animal`-Only 破谣言与 `[Face Memory]` 8 人脸 / `[Silent Mode Settings]` 2 项 `[Target Function Settings]` 与休眠 `[Shutter When Pwr OFF]` / `[Version]` `BODYDATA.DAT` `Slot 1` `EROFS=30` 与 `NO-GO` 刷机防火墙（`verify-64pillar-recovery` / `verify-pillar64-recovery` / `verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault`）

- **[`realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py`](fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-62）落地 **Phase 352 Pillar 64（`64/64`）** 并将全套恢复总检正式推进至 **`64/64`（`VERIFIED_64OF64_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..63pillar-recovery` 100% 向后兼容）；硬锁定 `BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`P352_AIRPLANE_MODE_FORCED_ON = True`、`P352_RF_PACKETS_TRANSMITTED = 0`、`P352_SLOT1_FORMAT_HARD_LOCKED = True`、`P352_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02/2.05`（16 项）与 `FX6 6.01`（5 项）共 **21 项** Wave-62 供体（`<= 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 64A（Digital MI Shoe `[Shoe Audio Set.]` `48kHz/24bit 4ch`、`XLR-H1`/`3.5mm` 硬件接管优先级、`[Audio Out Timing]` 与 `[Face/Eye Subject]` `Human`/`Animal`-Only 破谣言）**：实证锁定 `Shooting -> [Audio Recording]` 下 `[Audio Recording]`（`On` 默认/`Off`，`S&Q` 下 `EOPNOTSUPP=95`）、`[Audio Rec Level]`（`0..31` 默认 `26` + 不可关闭机身 Limiter）、`[Shoe Audio Set.]`（`48kHz/24bit 4ch`、`48kHz/24bit 2ch`、`48kHz/16bit 2ch` 默认；全系主码流 `XAVC HS 4K` / `XAVC S 4K/HD` / `XAVC S-I 4K/HD/DCI 4K` 均支持 `24-bit 4ch LPCM`，而 Proxy 恒定降级为 `MPEG-4 AAC-LC 2ch 128 kbps` 且 `>= 100p/120p+` 禁用）、`[Wind Noise Reduct.]`（仅作用于机内麦）与 `[Audio Out Timing]`（`Live` 默认/`Lip Sync`，实位于 `Shooting -> [Audio Recording]` 而非 `Setup -> [Sound Option]`），且 Ver. 2.00..7.02 已移除独立 `[Audio Level Display]` 菜单（`_f 0x7a36` -> `EOPNOTSUPP=95`）；建立硬件接管矩阵（`3.5mm MIC` 插孔优先于 MI 靴并强制 2ch 模拟+置灰 `[Shoe Audio Set.]`；`XLR-H1 HANDLE AUDIO=OFF` 回退机内麦；`ANALOG` 拨挡限制为 `48kHz/16bit 2ch`）对照 FX6 原生 `4ch 24-bit 48kHz`、物理 `CH1..CH4` 旋钮、6 档 `Limiter Mode`（`Off/-6/-9/-12/-15/-17 dB`）及休眠 `32bit float`（`FX6 ns1 0x3215`）；实证证伪 FX3 Ver. 7.02 `Bird`/`Insect`/`Car/Train`/`Airplane`（`BKID_APP_*airplane* == 0`，严格仅开放 `Human` 默认与 `Animal` 且 `Animal` 仅限 Still 眼部识别：`VAL_HAITA_..._TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` -> Movie/S&Q `EOPNOTSUPP=95`），保留活跃 `[Face Memory]`（最多 `8` 张人脸、抗 `Camera Settings Reset`、不导出 `CAMSET*.DAT`、`Delete All`/`Initialize` 清除）与 `[Face/Eye Frame Disp.]` 默认 `Off`（Clean-HDMI `0 px`），对照 FX6 `Human`-only 与会话式 `Saved Tracking Face`。
  - **Sub-Pillar 64B（`[Silent Mode Settings]` 2 项 `[Target Function Settings]`、休眠 `[Shutter When Pwr OFF]` 与 `[Version]` `BODYDATA.DAT` `Slot 1` `EROFS=30` + `NO-GO` 防火墙）**：实证锁定 `Shooting -> [Shutter/Silent] -> [Silent Mode Settings]` 中 `[Silent Mode]`（`Off` 默认/`On` 强制电子快门 + 关闭 `[Audio signals]` + 硬锁 5 项功能：`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`，且不自动禁用 `[AF Illuminator]`）与 `[Target Function Settings]` 严格仅 `2` 项（`[Aperture Drive in AF]` Still-only `Standard`/`Silent Priority`/`Not Target`；`[Auto Pixel Mapping]` `Off` 默认/`Not Target` 以阻断关机快门动作及 `cnflasha` 坏点表写入），实机 `0` 暴露 `[Shutter When Pwr OFF]`（`dormant_shutter_when_pwr_off_exposed_events == 0` -> `EOPNOTSUPP=95`；FX6 无机械快门）；建模 `Setup -> [Setup Option] -> [Version]` 与 `[Software Update]`（`BODYDATA.DAT` 严格仅认 **`Slot 1` 根目录**、忽略 `Slot 2`，对照 FX6 **`Slot B` 根目录** + 强制 `AC Adaptor`；`NP-FZ100 >= 51%` / `3` 格；`<= Ver. 2.02` 必须先经 `Ver. 2.04/2.05` 跳板方可升 `Ver. 7.02`，`5 long / 6 short` 与 `7 long / 7 short` LED 故障码及升级后重置 TC/UB），任何企图将 `BODYDATA.DAT` 写入/触发 `Slot 1` 或跨机型刷写的动作均通过 `EROFS=30` 故障闭锁（`slot1_data_sector_writes == 0`），叠加 Stage-B `/tmp` 覆写隔离与 `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `64/64` 恢复总检聚合器与 CLI（`evaluate_realhw_64pillar_recovery_master` / `evaluate_64pillar_recovery_master` / `verify_64pillar_recovery_suite` / `verify_64pillar_recovery` / `verify-64pillar-recovery` / `verify-pillar64-recovery` / `verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault`）**：并发聚合 `Pillars 1..63` + `Pillar 64`，自动对接 Milestone 311 / 324 最高支柱发现接口（`recovery=64/64`）；[`tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py`](tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py) 提供 **`>= 128` 项**（实测 180 项）四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar64-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-64pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-64pillar-recovery --force-clean-room --json
```

## Phase 355（Pillar 65 / `65/65` 统一恢复总检里程碑）：Wave-63 `4264x2408` 16-bit HDMI `RAW Output` 与 `Rec. Media dur HDMI Output` `Slot 1 EROFS=30` vs `Off(HDMI Only)` 零写入 / Ver. 7.00/7.02 `De-Squeeze Display` `1.3x/1.5x/1.6x[1.65x]/2.0x` 零 `1.8x` 与 FX6 SDI 不去挤压 / `[REC Lamp]` 三灯后顶联动与 `[Silent Mode]` 解耦 + `[Emphasized REC Display]` / 休眠 `[Var. Shutter]` vs FX6 `ECS` `23.99..8000 Hz` 与 `[APS-C S35]` 抗复位 4K 锁死 + `5.1M` 静态裁切（`verify-65pillar-recovery` / `verify-pillar65-recovery` / `verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault`）

- **[`realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py`](fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-63）落地 **Phase 355 Pillar 65（`65/65`）** 并将全套恢复总检正式推进至 **`65/65`（`VERIFIED_65OF65_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..64pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False`、`P355_AIRPLANE_MODE_FORCED_ON = True`、`P355_RF_PACKETS_TRANSMITTED = 0`、`P355_SLOT1_FORMAT_HARD_LOCKED = True`、`P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`P355_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`P355_FX3_HAS_VAR_SHUTTER = False`、`P355_DESQUEEZE_1_8X_HITS = 0`、`P355_HDMI_RED_BORDER_CLEAN_FEED_LEAK_PIXELS = 0`、`P355_RECORDED_MEDIA_DESQUEEZE_PIXELS = 0`、`P355_FX6_SDI_DESQUEEZE_PIXELS = 0`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（14 项）与 `FX6 6.01`（3 项）共 **17 项** Wave-63 供体（`<= 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 65A（HDMI 输出 8 项活跃树、`4264x2408` 16-bit 线性 RAW 与 `Rec. Media dur HDMI Output` `Slot 1` 防火墙）**：实证锁定 `Setup -> [External Output] -> [HDMI Output Settings]` 全树抗 `[Camera Settings Reset]`（仅 `[Initialize]` 清除）且仅暴露 **8 项**活跃菜单（`[Color Gamut for RAW Output]` `_f 0x6bdc` 已自 Ver. 2.00..7.02 移除并并入 `[Log Shooting Setting] -> [Color Gamut]`）：`[Rec. Media dur HDMI Output]`（默认 `On` / `Off(HDMI Only)`，`S&Q` 锁死 `On`）、`[Output Resolution]`、`[4K Output Set.(HDMI Only)]`（FX3 仅 10-bit；`24.00p` 强制重启；休眠 `24.00p 8bit` `_f 0x706c` -> `EOPNOTSUPP=95`）、`[RAW Output]`（HDMI Type-A `4264x2408` 16-bit 线性 RAW，需 Movie + `Log != Off`，`S&Q` 锁死 `Off`）、`[RAW Output Setting]`（`59.94p/50p/29.97p/25p/23.98p/24.00p`）、`[Time Code Output]`（`[REC Control]` 硬前提）、`[REC Control]` 与 `[4ch Audio Output]`（`CH1/CH2` 或 `CH3/CH4` 2ch LPCM）；当 `RAW Output = On` + `Rec. Media dur HDMI Output = On` 时 FX3 仍同步写内录 XAVC (+ Proxy) 至 `[Recording Media]`（触发 `Slot 1 EROFS=30` 闭锁）、锁 `S-Log3`、禁 `Active` 防抖并强制 `HDMI Info. Display = Off`，而 `Off(HDMI Only)` 时零卡写入；对照 FX6 双 `12G-SDI RAW`（`4096x2160` / `3840x2160 "C"` 且 HDMI 被锁 `<= 1080p`）+ `RAW(HDMI)`（`4240x2392` 且无 `24Hz`）及 `SDI/HDMI Remote I/F` vs `Parallel Rec`。
  - **Sub-Pillar 65B（`De-Squeeze Display` `1.6x[1.65x]` 零 `1.8x`、`[REC Lamp]` 三灯联动、休眠 `[Var. Shutter]` vs FX6 `ECS` 与 `[APS-C S35]` 抗复位勘误）**：实证锁定 Ver. 7.00/7.02 `[De-Squeeze Display]` 为 `Off / 1.3x / 1.5x / 1.6x`（底层实际水平拉伸 **`1.65x`** `VAL_DE_SQUEEZE_DISP_1_65X` / `_f 0x7d0c`）/`2.0x` 且 **`0` 次 `1.8x` 命中**，强制 4 重硬件互斥（`Manual Focus`、`Focus Area = Wide`、`SteadyShot = Off`、`Face Priority = Off`），绝不改写录制像素，在 6 种条件旁路（`Log=Off`、`RAW=On`、`HDMI Only`、Still `MOVIE` 键、`Remote Shooting`、`Photo Capture`），且不禁用 `Focus Magnifier` 与 `Bright Monitoring`，对照 FX6 `Off/1.3x/1.5x(v5.00+)/2.0x`（无 `1.6x`，SDI 绝不去挤压）；锁定 `[REC Lamp]`（零 `[Tally Light]`，抗复位）3 颗物理 LED（前/后/顶 `REC` 键环，后+顶硬件串联）仅 3 态 `All On` / `Only Front Off` / `All Off`（休眠 `ONLY_ONE`），并与 `[Silent Mode]` 严格解耦；叠加可复位 `[Emphasized REC Display]`（HDMI clean feed 红框 `0 px`）、抗复位 `[Remain Shoot Display]`（Active Still 连拍余量）与 `[Auto Review]`（仅 Still `Off/2/5/10 Sec`，Interval 禁用）；证实 `[Var. Shutter]`（`BKID_APP_setting_high_res_ss` / `_f 0x6831`）在 FX3 Ver. 7.02 有 `0` 次 `TYPE_MENU_ITEM_*HIGH_RES*` 命中且完全休眠（仅暴露可复位 Still 机械快门 `[Anti-flicker Shoot.]` 100/120Hz），对照 FX6 `ECS`（`23.99..8000 Hz`）；并将 `[APS-C S35 Shooting]` 纠正为**抗 `[Camera Settings Reset]`（Wave 42 勘误）**，开为 `On` 时锁死所有 4K / DCI 4K / 4K HDMI Only（仅留 HD `<= 120p` 与 Still `M: 5.1M` `2768x1848` 3:2 / `4.3M` 16:9），叠加 Stage-B `/tmp` 隔离、`Backup.bin H0 == H3`（`16/16`）与 `Slot-1 EROFS=30`。
  - **统一 `65/65` 恢复总检聚合器与 CLI（`evaluate_realhw_65pillar_recovery_master` / `evaluate_65pillar_recovery_master` / `verify_65pillar_recovery_suite` / `verify_65pillar_recovery` / `verify_all_65_recovery_pillars` / `verify-65pillar-recovery` / `verify-pillar65-recovery` / `verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault`）**：并发聚合 `Pillars 1..64` + `Pillar 65`（`< 1.5s` 预算与确定性 SHA-256），自动对接 Milestone 349 最高支柱发现接口（`recovery=65/65`）；[`tests/test_realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py`](tests/test_realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py) 提供 **`>= 120` 项**四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar65-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-65pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-65pillar-recovery --force-clean-room --json
```

## Phase 361（Pillar 66 / `66/66` 统一恢复总检里程碑）：Wave-64 `[Breathing Comp.]` `120p`/`S&Q>=100`/RAW/`Catalyst Prepare` vs FX6 3 锁、电影 `[File Settings]` `[Cam ID + Reel#]`/`37` 字符/`SDHC 4GB`、`[Copyright Info]` `46` 字符抗 Reset（Round 57 勘误）+ 活跃 Still+Movie `[Write Serial Number]` + `CAMSET` 隔离、9 条件 `[Power Setting Option]` + 休眠 `[Power Save by Monitor]` 与 `[NTSC/PAL Selector]` `Slot 1 EROFS=30` 防火墙（`verify-66pillar-recovery` / `verify-pillar66-recovery` / `verify-pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault`）

- **[`realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py`](fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-64）落地 **Phase 361 Pillar 66（`66/66`）** 并将全套恢复总检正式推进至 **`66/66`（`VERIFIED_66OF66_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..65pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False`、`P361_SLOT1_FORMAT_HARD_LOCKED = True`、`P361_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`P361_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`P361_ROUND57_ERRATUM_COPYRIGHT_RESETTABLE = False`、`P361_WRITE_SERIAL_STILL_AND_MOVIE_ACTIVE = True`、`P361_FX3_HAS_POWER_SAVE_BY_MONITOR = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（15 项，含 `libSaveLoadSettings.so` `18,760 B`）与 `FX6 6.01`（3 项）共 **18 项** Wave-64 供体（`<= 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 66A（`[Breathing Comp.]` 光学裁切 / `120p` + `S&Q >= 100fps` + `RAW` / `Catalyst Prepare` vs FX6 3 锁与电影 `[File Settings]` `Cam ID + Reel#` / `SDHC 4GB` / `Slot 1 EROFS=30` 防火墙）**：实证锁定 `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（默认 `Off` / `On`，同组唯独它 **`Can be reset`**，而 `Shading`/`Chromatic Aberration`/`Distortion` 均为 `Not available`）、`BKID_APP_setting_lens_comp_breathing` + `PRM_HAITA_breathing_correction_lens_type_lens_information`（`SUPPORT`/`NOT_SUPPORT`/`NA`，排除 `SEL100F28GM` 微距环 `0.57m..1.0m` 与 `SEL14TC`/`SEL20TC` 增距镜），在 Still 静态、常规电影 `119.88p/100p` 与 `S&Q >= 100/120fps` 下硬锁定 `EOPNOTSUPP=95`（FX3 允许 `<100fps` S&Q），在外录 HDMI 16-bit `RAW Output` 上旁路不裁切；后期呼吸元数据补偿严格要求付费版 `Catalyst Prepare` / `Catalyst Prepare Plugin`（`Catalyst Browse` 不支持）且机内 `[Distortion Comp.] = [Auto]`，对照 FX6 `Technical > Lens > Breathing Compensation`（`Auto`/`Off`，在 `Distortion Comp.=Off`、**全部** `S&Q=On` 及任意 `RAW` 编码下强制锁 `Off`）。同步锁定电影 `Shooting -> [File] -> [File Settings]`（全项抗 Reset `Not available`）：`[File Number]`（`Series` 跨 Slot 1/2 递增 / `Reset` + `[Series Counter Reset]` -> `max + 1`）、`[File Name Format]`（5 模式；`SDHC <=32GB FAT32` 强制锁 `[Standard]`、XAVC S 按 `4 GB` 自动分割且禁止 `FAT32+exFAT` `[Simult. Recording]`）、`[Cam ID + Reel# Settings]`（改 `Camera ID` `A..Z` 重置 `001..999` Reel#，而 `File Number=Reset` 不重置 Reel#；`C/L/R` 溢出 `C999 -> D001` 仅作用于输出文件名而不修改菜单设定值；6 位 `YYMMDD` + 2 位随机字符 vs `Date + Title` 8 位 `YYYYMMDD`）、`[Title Name Settings]`（`<=37` 字符，默认 `"C"`，固定路径 `PRIVATE/M4ROOT/CLIP`），并将 `BKID_APP_update_required_xavcs_file_name_reel_number` 等写卡链路锁闭在 Tier-0 `Slot 1 EROFS=30` 之后，对照 FX6 `TC/Media > Clip Name Format`（`Cam ID + Reel#` / `Title`、`4..46` 字符 `Title Prefix` 默认 `nnn_`、`DIADEM_PRO` 卡内片段继承与 `/XDROOT/Clip/*.MXF`）。
  - **Sub-Pillar 66B（`[Copyright Info]` `46` 字符抗 Reset [Round 57 勘误] / 活跃 Still+Movie `[Write Serial Number]` / `CAMSET*.DAT` 隐私隔离与 `[Power Setting Option]` 9 条件旁路 / 休眠 `[Power Save by Monitor]` / `[NTSC/PAL Selector]` `Slot 1 EROFS=30` 防火墙）**：显式落地 Round 57 勘误——`[Copyright Info]` 全部 4 项（含 `[Write Copyright Info]` `Off`/`On` 与 `<=46` ASCII `[Set Photographer]`/`[Set Copyright]`/`[Disp. Copyright Info]`）以及 `[Write Serial Number]`（`Off`/`On`）**全部抗 `[Camera Settings Reset]`（`Not available`）**，仅 `[Initialize]` 清除；实证 `[Write Serial Number]` 在 Ver. 2.00..7.02 上跨 Still + Movie 全域活跃（`BKID_APP_setting_write_serial_number_still_movie` `_f 0x6704`）；强制验证 `Copyright Info` PII 被 `Slot 1` `CAMSET*.DAT`（`libSaveLoadSettings.so`）严格排除（0 字节泄漏），对照 FX6 零 EXIF 版权菜单与镜头序列号跟踪 `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`。同步覆盖 `Setup -> [Power Setting Option]`（仅 2 项抗 Reset 活跃设置：`[Power Save Start Time]` `Off/30Min/5Min/2Min/1Min/10Sec` 受官方精确 **9 条件**自动旁路控制，`[Auto Power OFF Temp.]` `Standard`/`High` 三脚架警告 `_g 0x61a9`；休眠项 `[Power Save by Monitor]` `BKID_APP_setting_monitor_power_linkage` 在无 EVF 的 FX3 上 100% 未暴露）与 `[NTSC/PAL Selector]`（`base 0xe5c1` 重启 + `Running on NTSC./PAL.` `base 0xe77a`/`0xe0b6` + `_g 0x61ca`/`0x644e` 跨制式回放拦截 + `base 0xe595` `"Format? Slot 1"` SD-Erase/TRIM 隐患在 Tier-0 `Slot 1` 防火墙上触发 `EROFS=30` 闭锁，`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`slot1_sector_writes=0`）及 Stage-B `/tmp` 隔离 + `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `66/66` 恢复总检聚合器与 CLI（`evaluate_realhw_66pillar_recovery_master` / `evaluate_66pillar_recovery_master` / `verify_66pillar_recovery_suite` / `verify_66pillar_recovery` / `verify_all_66_recovery_pillars` / `verify-66pillar-recovery` / `verify-pillar66-recovery` / `verify-pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault`）**：并发聚合 `Pillars 1..65` + `Pillar 66`（`< 1.5s` 预算与剥离 `elapsed_seconds` 的确定性 SHA-256），自动对接 Milestone 349 / 311 最高支柱发现接口（`recovery=66/66`）；[`tests/test_realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py`](tests/test_realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py) 提供 **`>= 130` 项**（实测 146 项）四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar66-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-66pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-66pillar-recovery --force-clean-room --json
```

## Phase 366（Pillar 67 / `67/67` 统一恢复总检里程碑）：Wave-65 `[Zoom Range]` 清晰影像/数字变焦与 8 档双段速度、`[Auto Slow Shutter]` 6+ 项锁死、静态专属 `[ISO AUTO Min. SS]` 与双原生 Base ISO 矩阵、休眠 `Lossless Comp` `.ARW` 拒绝 / `[HLG Still Image]` / `Sort Recording`、`[USB LUN Setting] = Single`（仅暴露 `Slot 1`!）macOS MSC 灾备阻断、`NP-FZ100` PD 门控与双机休眠 `UVC` 防火墙（`verify-67pillar-recovery` / `verify-pillar67-recovery` / `verify-pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault`）

- **[`realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py`](fx3_recovery/realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-65）落地 **Phase 366 Pillar 67（`67/67`）** 并将全套恢复总检正式推进至 **`67/67`（`VERIFIED_67OF67_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..66pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False`、`P366_SLOT1_FORMAT_HARD_LOCKED = True`、`P366_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`P366_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`P366_FX3_ZOOM_RANGE_RESETTABLE = False`、`P366_FX3_ZOOM_SPEED_RESETTABLE = True`、`P366_FX3_HAS_DORMANT_LOSSLESS_ARW_EXPOSED = False`、`P366_FX3_HAS_NATIVE_UVC_STREAMING = False`、`P366_FX6_HAS_NATIVE_UVC_STREAMING = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（18 项，含 `usbg_storage.ko` / `usbg_stillimage.ko` / `usb_f_uvc.ko` / `g_webcam.ko`）与 `FX6 6.01`（7 项）共 **25 项** Wave-65 供体（`<= 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 67A（`[Zoom Range]` / 8 档 Standby-vs-Movie 变焦速度 / `[Auto Slow Shutter]` 6+ 项锁死 / 静态 `[ISO AUTO Min. SS]` 与双原生 Base ISO 矩阵）**：实证锁定 `[Zoom Range]`（`Optical zoom only` 默认 / `ClearImage Zoom` `1.5x` 4K & `2.0x` HD / `Digital Zoom` `4.0x` 电影 & 最高 `8.0x` 静态 S，抗 Reset `Not available`）+ `[Zoom Ring Rotate]`（`Left(W)/Right(T)` 默认 / `Right(W)/Left(T)`，`Not available`）对照可复位（`Can be reset`）`[Zoom Lever Speed]`（`1st=3`、`2nd=8 Fast`）、`[Custom Key Z. Speed]`（`1..8` 默认 `3`）与 `[Remote Zoom Speed]`（`Variable` 默认 / `Fixed 1..8` 默认 `3`）；在静态 `RAW` / `119.88p/100p` / `S&Q >= 100fps` / HDMI `RAW Output` / `Breathing Comp.` 下锁定 CIZ/Digital（`EOPNOTSUPP=95`）并在激活时强制画面中央优先 AF + `[Multi]` 测光，对照 FX6 `Zoom Type` 2 档（零 `Digital Zoom`）+ `Handle Zoom`。同步锁定 `[Auto Slow Shutter]`（电影专属、默认 `On`、`Can be reset`，在 `S&Q`、`S`、`M`、固定手动 ISO、`Flexible Exp.` 手动快门、`Cine EI`/`Cine EI Quick` 及 `Shutter Mode = Angle` 下禁用）、`[ISO Range Limit]`（抗 Reset `Not available`，仅限手动 ISO）、静态专属 `[ISO AUTO Min. SS]`（`SLOWER..FASTER` / `1/8000..30"`，默认 `STD`，电影/`S&Q` 下 `EOPNOTSUPP=95`，闪光同步 `1/250s` 覆盖）与双原生 Base ISO 矩阵（`800/12800` Cine EI、`640/12800` Flexible ISO S-Log3/S-Log2/ITU709 800%、`100/2000` PP11 S-Cinetone/HLG/HLG3/Cine4、`80/1600` PP Off/HLG2/Cine3、`64/1280` Cine1、`50/1000` HLG1/Cine2）。
  - **Sub-Pillar 67B（休眠 `Lossless Comp` `.ARW` 拒绝 / `[HLG Still Image]` / `Sort Recording` 外溢、`[USB LUN Setting] = Single`（`Slot 1`-Only!）macOS MSC 威胁、`NP-FZ100` PD 门控与双机休眠 `UVC` 防火墙）**：实证拒绝 `FX3 Ver. 7.02` 休眠 `RAW_FILE_TYPE_LOSSLESS`（`L/M/S`，`EOPNOTSUPP=95`，仅暴露 `Compressed` 与 `Uncompressed` 14-bit `.ARW`），锁定 `[HLG Still Image]`（纯 `HEIF` + `P/A/S/M`，强制 `BT.2100` 与 ISO 下限 `100/125`），并将 `[Sort Recording]` + `[Auto Switch Media]` 满卡外溢及流媒体 `[Movie Rec During Streaming]` / HDMI `[Rec. Media dur HDMI Output]` 写卡全部封死在 Tier-0 `Slot 1 EROFS=30` 防火墙之后（`slot1_data_sector_writes == 0`）。锁定 `Setup -> [USB]` 全树抗 Reset：`[USB Connection Mode]` 4 项（`Sel. When Connect` / `MassStorage(MSC)` / `MTP` / `Remote Shooting`）与 **`[USB LUN Setting]`（`Multi` 暴露 `Slot 1+2`，`Single` 暴露“仅 `Slot 1`”而非隐藏 `Slot 1`！）**，严禁在 Tier-0 台架上以 MSC（`054C:0DA1`）直连 macOS 触发 `mds`/`fseventsd`/`fsck_exfat` 脏写；校验 `NP-FZ100` 即使在 `9V/3A` USB-C PD 下仍强制存在（无电池供电须 `DC-C1` + `>=65W PD` + `5A e-Marked` 线缆）对照 FX6 `19.5V DC IN`；并在 FX3 Ver. 7.02 与 FX6 Ver. 6.01 上双双阻断休眠原生 `UVC USB Streaming`（`usb_f_uvc.ko` / `g_webcam.ko`，`EOPNOTSUPP=95`），叠加 Stage-B `/tmp` 与 `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `67/67` 恢复总检聚合器与 CLI（`evaluate_realhw_67pillar_recovery_master` / `evaluate_67pillar_recovery_master` / `verify_67pillar_recovery_suite` / `verify_67pillar_recovery` / `verify_all_67_recovery_pillars` / `verify-67pillar-recovery` / `verify-pillar67-recovery` / `verify-pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault`）**：并发聚合 `Pillars 1..66` + `Pillar 67`（`< 1.5s` 预算与剥离 `elapsed_seconds` 的确定性 SHA-256），自动对接 Milestone 349 最高支柱发现接口（`recovery=67/67`）；[`tests/test_realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py`](tests/test_realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py) 提供 **`>= 130` 项**（实测 176 项）四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar67-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-67pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-67pillar-recovery --force-clean-room --json
```

## Phase 370（Pillar 68 / `68/68` 统一恢复总检里程碑）：Wave-66 静态 `[Drive Mode]` 10fps 与休眠 `[Focus Bracket]` 辟谣、2 档 `[Shutter Type]` 无 `Auto` / `1/250 s` X-Sync / 抗 Reset `[e-Front Curtain Shut.]` / `[Long Exposure NR]` / `[High ISO NR]`、10 预设 8 非对称参数 `[Creative Look]` vs 休眠 `[Soft Skin Effect]` 及 `[Delete]`/`[Protect]`/`[Recover Image DB]` `Slot 1 EROFS=30` 防火墙（`verify-68pillar-recovery` / `verify-pillar68-recovery` / `verify-pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault`）

- **[`realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py`](fx3_recovery/realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py)**：面向物理 `Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，Wave-66）落地 **Phase 370 Pillar 68（`68/68`）** 并将全套恢复总检正式推进至 **`68/68`（`VERIFIED_68OF68_PILLAR_RECOVERY_MASTER`）**（`< 1.5s` 快速 CLI 预算、`< 4.0s` 标称、`< 6.0s` 并发上限，保持 `verify-22..67pillar-recovery` 100% 向后兼容）；硬锁定 `CNFLASHA_USERSPACE_WRITE_BLOCKED = True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`、`OVERALL_READY_FOR_HARDWARE_ATTACH = False`、`CROSS_MODEL_FLASH_AUTHORIZED = False`、`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False`、`P370_SLOT1_FORMAT_HARD_LOCKED = True`、`P370_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True`、`P370_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`、`P370_FX3_HAS_DORMANT_FOCUS_BRACKET_EXPOSED = False`、`P370_FX3_HAS_SHUTTER_TYPE_AUTO_EXPOSED = False`、`P370_FX3_HAS_DORMANT_SOFT_SKIN_EXPOSED = False`、`P370_FX6_HAS_STILL_DRIVE_MODE = False`、`P370_FX3_EFCS_RESETTABLE = False`、`P370_FX3_CREATIVE_LOOK_RESETTABLE = True`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`，严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 有界只读检查本地 `FX3 7.02`（14 项）与 `FX6 6.01`（3 项）共 **17 项** Wave-66 供体（`<= 2.0s` 预算且显式防护 `work_root is None`），并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时安全回退至 `CLEAN_ROOM_SYNTHETIC`：
  - **Sub-Pillar 68A（静态 `[Drive Mode]` 10fps / 休眠 `[Focus Bracket]` 拒绝 + 2 档 `[Shutter Type]` / `1/250 s` X-Sync / `[e-Front Curtain Shut.]` / `[Long Exposure NR]` / `[High ISO NR]`）**：实证锁定 `ILME-FX3 Ver. 7.02` `Shooting -> [Drive Mode]` 全量 `9` 项（全部 `Can be reset`）：`Single Shooting`（默认）、`Cont. Shooting`（`Hi+` 10 fps 非实时取景刷新 / `Hi` 8 fps / `Mid` 6 fps / `Lo` 3 fps；`> F11` 在 `Hi+/Hi/Mid` 首帧锁焦；`Uncompressed RAW` 或闪光灯降速）、`Self-timer(Single)`（`10/5/2 Sec`）、`Self-timer(Cont)`（严格 6 组合，拒绝休眠 `10SEC_10IMAGES`）、`Cont. Bracket` 与 `Single Bracket`（`0.3..1.0 EV` × `3/5/9`、`2.0/3.0 EV` × `3/5`，`iAuto` 下禁用）、`WB bracket`（`Lo`/`Hi`）、`DRO Bracket`（`HLG Still Image = On` 时禁用）与 `[Interval Shoot Func.]`（仅输出静态序列，独立 `[Shutter Type in Interval]` 默认 `Electronic Shutter`）；显式拒绝 FX3 休眠 `[Focus Bracket]`（`0` 命中 `ilc/2210`，尽管 ELF 含 `BKID_APP_setting_focus_bracket_*`）与纯电影机 `ILME-FX6` Still `Drive Mode` / `Focus Bracket`（`EOPNOTSUPP=95`）。同步锁定 `[Shutter Type]` 严格 2 档（`Mechanical Shutter` 默认 / `Electronic Shutter`，`Can be reset`，**无 `Auto`**——拒绝 `ANTI_DISTORTION_SHUTTER_AUTO` / `_f 0x66b8`）、`Electronic Shutter` / `Silent Mode = On` 强制锁死 5 项（`Flash` / `Long Exposure NR` / `e-Front Curtain Shut.` / `BULB` / `Anti-flicker Shoot.`）、机械闪光 X-Sync 上限严格 **`1/250 s`**（拒绝 `1/320`）、`[e-Front Curtain Shut.]`（Sony 拼写 `BKID_APP_setting_front_curtaion_shutter`，默认 `On`，**抗 `[Camera Settings Reset]`**）、`[Long Exposure NR]`（`>= 1 s` 暗帧减除，电子/静音/连拍/连拍包围禁用，`iAuto` 锁 `On`）与 `[High ISO NR]`（`Normal`/`Low`/`Off` 三档，拒绝 `HIGH`，不改写 `.ARW` RAW）对照 FX6 `Noise Suppression` 与 `APR`。
  - **Sub-Pillar 68B（`[Creative Look]` 10 预设 + 6 Custom + 8 非对称参数 / 休眠 `[Soft Skin Effect]` 拒绝 + `[Delete]` / `[Protect]` / `[Recover Image DB]` `Slot 1 EROFS=30` 防火墙）**：实证锁定 `[Creative Look]`（`Can be reset`）10 预设（`ST..SE`）+ `Custom Look 1..6`（`look_still0..15` / `look_movie0..15`）及 8 项非对称微调参数范围（`-9..+9` 对比度/高光/阴影/饱和度；**`0..9`** 褪色/锐度/`Clarity`；**`1..5`** `Sharpness Range`/`fineness`），锁定 `BW`/`SE` 饱和度与 Movie/`S&Q` `Sharpness Range`，在 `Picture Profile != Off`、`Log Shooting != Off`、`HLG Still Image = On` 或 `iAuto` 时强制禁用固定为 `[-]`；同时在 FX3 与 FX6 上双双拒绝休眠 `[Soft Skin Effect]`（`0` `ilc/2210` 命中，对照 FX6 `Base Look` / `Scene File` / `Multi Matrix`）。回放与媒体侧锁定 `[Delete]`（多作用域 + 联动删除 Proxy + 跳过受保护文件）、`[Delete confirm.]`（`"Cancel" first` / `"Delete" first`）与 `[Delete pressing twice]`（双按快删隐患，均抗 Reset）、`[Protect]`（`Fsys_Chmod` + 联动保护 Proxy；`Copy` 不保留保护属性）以及 `[Recover Image DB]`（重建 `AVF_INFO` 并清除 FTP 传输结果，受电量门控，**抗 Reset 且抗 Initialize**）对照只读 `[Display Media Info.]`（`40,000` 张上限），并在块层对任何指向 Tier-0 `Slot 1`（或 FX6 `Restore Media(A)`）的删除/保护/重建请求强制返回 **`EROFS (errno 30)`** fail-closed 拦截（`slot1_sector_writes == 0`、`cnflasha_writes == 0`、`emmc_writes_authorized == False`、`raw_firmware_bytes_leaked == 0`）+ Stage-B `/tmp` 叠加层与 `Backup.bin H0 == H3`（`16/16`）。
  - **统一 `68/68` 恢复总检聚合器与 CLI（`evaluate_realhw_68pillar_recovery_master` / `evaluate_68pillar_recovery_master` / `verify_68pillar_recovery_suite` / `verify_68pillar_recovery` / `verify_all_68_recovery_pillars` / `verify-68pillar-recovery` / `verify-pillar68-recovery` / `verify-pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault`）**：并发聚合 `Pillars 1..67` + `Pillar 68`（`< 1.5s` 预算与剥离 `elapsed_seconds` 的确定性 SHA-256），自动对接 Milestone 364 最高支柱发现接口（`recovery=68/68`）；[`tests/test_realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py`](tests/test_realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py) 提供 **`>= 140` 项**（实测 `192` 项）四模单元测试。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-pillar68-recovery --json

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-68pillar-recovery --json

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_recovery verify-68pillar-recovery --force-clean-room --json
```


