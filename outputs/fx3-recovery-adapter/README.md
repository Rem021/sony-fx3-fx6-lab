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

