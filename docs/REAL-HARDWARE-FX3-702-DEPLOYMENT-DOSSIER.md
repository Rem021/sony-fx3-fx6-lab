# Sony ILME-FX3 (`Ver. 7.02`) 实机 Stage-B 双系统部署、逃生舱与无痕卸载权威手册（Grand Milestone Phase 264 Dossier）

> **文档定位 / Document Scope**: 本手册为 **Grand Milestone Phase 264 实机主线六支柱总闭环闸门（`realhw_milestone264_master_gate_v1` / `make verify-milestone-264`）** 的权威工程总册，完整同步 **Wave 21–43** 全量实机主线子系统（Phases 134–263 & QEMU Rounds 28–52，含第 25 轮实机 / 第 75 子实验里程碑 `Round 52`）与 **六联台架前置预检**，覆盖 **Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`, SoC `CXD90057` Mira + `CXD90058` Cetus)** 上部署 **ILME-FX6 (`Ver. 6.01`)** Hybrid Userland Stage-B 双系统的完整闭环链路：  
> `preflight-realhw-bench` + **`preflight-card-insert`** + **`preflight-bench-cable-fan-slot1`** + **`preflight-hdmi-proxy-desqueeze-and-simult`** + **`preflight-pixelmap-ntscpal-powersave-and-autotemp`** + **`preflight-imagedb-touch-shoeaudio-and-lockop`** + **`preflight-diffset-customkey-autoslow-and-apsc`**（零发射 `ioreg` 被动分类 + Slot-1 ExFAT `>=128 KiB`/`._*` 卫生与 `FX3BNDL1 ↔ FX3RCPT1` 绑定 + `DC-C1 >=65W/5A`/`NP-FZ100 >=51%` 供电、`VMC-BNCM1` 机身 `Multi/Micro USB` 单向 `TC IN` 与 HDMI 数字 `TC OUT`、精确 **4 档 `[Fan Control]` `Auto/Minimum/Off in Rec/Always Off`** 禁 `Auto1/Auto2` 且 `Always Off -> Auto` 备份前置热保护、Slot-1 专属 `CAMSET01..10.DAT` 双介质路径分离 + **`De-Squeeze 1.6x=1.65x` 4 项硬锁 / 外置 `M&C Focus Map <150fps`、HDMI Log `1080p` vs `[Off(HDMI Only)]` `4K 10-bit` 内录互斥与黑屏预警、双卡 `Simult+AutoSwitch` 与 `Px` 代理成对保险库、`37` 字符 `File Settings`/`SDHC`/`Shot Mark1/2` XML/`TC Regenerate` Slot-1 主读及机身+`XLR-H1` 耦合 `REC Lamp`** + **`Pixel Mapping` 满电重启与 `/dev/cnflasha*` `O_RDONLY` 防火墙、`NTSC/PAL` 复位保持、`Gamma Display Assist` vs `Display LUT` 分流、`Power Save Start Time` 9 项旁路与 `p3` 75 MiB 冷备防休眠、`Auto Power OFF Temp. = High` 三脚架互锁、`SteadyShot Active` `1.1x` / `CIZ` 4 锁** + **`Recover Image DB` 电量与 Slot-1 Tier-0 保险库防覆写、`Monitor Flip` 回放不翻转、`Touch Operation` 4 项防误触与室内 `Sunny Weather`/`Display Quality=Standard` 省电钳位、`Shoe Audio 48kHz/24bit 4ch` 3 项硬锁与内置麦专属防风、`Save/Load Settings` `C3` 4 类敏感排除与 Slot-1 防写、`Lock Operation Parts` `MENU+Fn 5s` 全锁 vs 阻断 `MENU+Delete` 全格组合键、`USB Power Supply` 必插 `NP-FZ100` 及 `Exposure step` 与 `Shutter Angle` 独立表** + **`Different Set for Still/Mv` 8 项非对称切换与 `Shutter Angle` 独立优先、`Custom Key/Dial Set.` 3 域 `ISO/EI` 与 Slot-1 `O_RDONLY` 防火墙、无 EVF `FX3` `Remain Shoot Display` 边界、`Auto Slow Shutter` 6 项硬锁与 `HDMI REC Control <- TC Output` 前置、`Breathing Comp.` 视频专属、`APS-C S35` 12.1MP `4K/RAW` 禁用锁、`Face/Eye AF` 4 项层级与 HDMI 净流隔离、`[Version]` 纯只读防自动刷写 `BODYDATA.DAT`、`Release w/o Card/Lens` 零 E-ND、`Ver. 7.02` 5 项 `Audio Recording` 菜单及 `Copyright Info` 46 字符 PII 脱敏**）→ `054C:0DA1 -> 054C:0336`（`SET_FILE2` + `op=0xFF` 金丝雀 + `AdjustControl 0x40` + `64 KiB libJit.so` + 双介质 RAID-6 `GF(256)`）Tier-0 16 面冷备 → 实机全硬件/外设/光学/音频/供电/散热/色彩/监看二进制兼容与防火墙 → Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接（`U4`）→ `/dev/cnflasha15` 原子 `/usr/bin/im.elf` 逃生舱包装器（`EH1 47 us` / `EH2` / `EH3`）→ `p1` 首行清除救援（`U5`）与 `H0 == H3` 16 面零漂移无痕卸载 SOP。  
> **配套文档 / Companion Docs**: [`STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`](./STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md) · [`STAGE-B-ARCHITECTURE-AND-SAFETY.md`](./STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [`BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) · [`outputs/fx6-on-fx3-closure/README.md`](../outputs/fx6-on-fx3-closure/README.md)

> [!CAUTION]
> **刚性安全红线与工程状态严格边界（Hard-Locked Safety Posture & Facts vs Bench Boundary）**
> 1. **实验仓与离线门禁硬锁（当前仓库/CI 默认锁定状态）**：
>    - `overall_ready_for_hardware_attach = False` · `persistent_emmc_writes_authorized = False` · `persistent_write_release = False`
>    - `spi_nor_write_authorized = False` · `el3_payload_transmit_authorized = False` · `isp_write_authorized = False`
>    - `hardware_live_attachment_authorized = False` · `agent_auto_flash_blocked = True` · `cnflasha_userspace_write_blocked = True` · `fx3_has_builtin_evf = False` · `fx3_has_var_shutter = False`
>    - `usb_packets_transmitted = 0` · `physical_usb_packets_emitted = 0` · `physical_device_writes = 0` · `raw_firmware_bytes_leaked = 0` · `e_nd_actuator_tx_count = 0` · `emmc_write_count = 0` · `otp_fuse_touches = 0` · `otp_fuse_writes = 0` · `rpmb_counter_increments = 0` · `rpmb_writes = 0` · `passive_tx_bytes_emitted = 0` · `passive_tx_bytes = 0`
>    - `sector0_mutation_bytes = 0` · `cp_mutation_bytes = 0`（`p8:/cpapp-b.bin` 与 `CXD90058` / `sabin` 零改动）· `wbi_mutation_bytes = 0`（`p5:/wbi` `WBI2` `hibdrv.ko` 禁止写入/休眠）· `calibration_mutation_bytes = 0`（`C2PA RQ_LIC.DAT` / `p2:/setting/Backup.bin, psd.bin, defdet.bin` / `User1..16` LUT 槽位 / `p18:/lens/LENSFILE.BIN` / `p12/p13 RF NVS` 全程零修改）
> 2. **已闭环实证 vs 未执行实机台架的严格区分**：
>    - **已闭环（Verified Offline / Unicorn / POSIX `/bin/sh` / Live FX3 `7.02` `4.9.337-scel+` ARM64 QEMU）**：Phases 134–263 与 Grand Milestone Phase 264 全部 6 支柱代码、双模测试（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）、**102 安全闸门**（`102/102` `--simulate-bench-dry-run` 模拟演练含 `100/100` 大里程碑 `G100`，`99/102` 离线锁定 `G10..G12`，前向兼容 `104+`）、**44 支柱恢复主引擎**（`44/44` `VERIFIED_44OF44_PILLAR_RECOVERY_MASTER`，`cnflasha_userspace_write_blocked=True`，前向兼容 `45+`）、**45+ 项固件实验室真实二进制审计器**（`45/45`，支持 `46/46+` 前向兼容）、**50+ 阶段异构 VM HIL 协同仿真**（`50/50` 含 `50/50` 大里程碑 `Stage 50`，支持 `51+` 前向兼容）、Phase 154 被动预检 + **六联台架前置预检**（Phase 186 `preflight-card-insert` `C1..C4` + Phase 204 `preflight-bench-cable-fan-slot1` `B1..B3` + Phase 216 `preflight-hdmi-proxy-desqueeze-and-simult` `S1..S5` + Phase 227 `preflight-pixelmap-ntscpal-powersave-and-autotemp` `P1..P3` + Phase 248 `preflight-imagedb-touch-shoeaudio-and-lockop` `A..D` + **Phase 261 `preflight-diffset-customkey-autoslow-and-apsc` `A..D`**）以及 **Rounds 28–52（25 轮含第 25 轮实机 / 第 75 子实验里程碑 `Round 52`，共 75/75 子实验 `r28a..r52c` + 50/50 `< 50 KiB` PNG 截图收据，实测最大 `27,467 B`，并支持 `r53+` 自动前向发现）** 实机 ARM64 内核 QEMU 演练已全部通过并留痕；同时 `verify-milestone-90/110/130/147/175/193/209/221/233/254` 与全部六项预检 CLI 保持 100% 向后兼容通过。
>    - **尚未执行（Not Yet Executed）**：**真实物理 Sony ILME-FX3 实机上电 USB 连接与现场台架采集/插卡/卸载会话（Physical Camera Bench Session）尚未执行**；在物理相机通过操作员两步人工授权与 `Gate G10..G12` + `Gate G58` 独立 Tier-0 实机双介质回读签收前，禁止任何持久化写入或物理 USB 控制包发射。

---

## English Executive Summary

This dossier consolidates **Grand Milestone Phase 264 (`realhw_milestone264_master_gate_v1` / `make verify-milestone-264`)** — uniting ALL **Waves 21–43** real-hardware subsystems (**Phases 134–263**) and **Rounds 28–52+** (`>= 25` rounds including `Round 51` and the `25th` Real-HW / `75th` Run Milestone `Round 52`, `>= 75` sub-runs `r28a..r52c`, `>= 50` PNG receipts `< 50 KiB` / `< 51,200 B`) live **Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`)** ARM64 QEMU kernel rehearsals while keeping `verify-milestone-90/110/130/147/175/193/209/221/233/254` and all 6 bench preflight CLIs 100% intact and forward-compatible (`>= 102` gates, `>= 44` pillars, `>= 45` auditors, `>= 50` VM stages, `>= 25` QEMU rounds):

- **102-Gate Hardware-Truth Safety Preflight (`P1`, `G01..G102`, `fx3_safety.evaluate_102gate_preflight`)**: Extends Milestone 254 (`96` gates) through `G97..G102` (`102/102` `--simulate-bench-dry-run` simulated pass vs `99/102` offline with `3` Tier-0 physical-bench receipt gates `G10..G12` fail-closed; forward-compatible with `104+`), adding **`Display Quality` Tier-0 `Standard` clamp & `Bluetooth Rmt Ctrl` IR lockout** (`G97`), **`My Menu` 36-item survival & `CAMSET` Slot-1 `O_RDONLY` vault** (`G98`), **`Different Set for Still/Mv` 8-item asymmetric transitions & `Shutter Angle` override** (`G99`), **`100/100` Grand Milestone `Custom Key/Dial Set.` 3-domain `ISO/EI` Slot-1 firewall & EVF-less `Remain Shoot Display`** (`G100`), **`Auto Slow Shutter` 6-condition lockout & `Breathing Comp.` movie-only RAW/240p lockout** (`G101`), and **`HDMI REC Control <- Time Code Output` prerequisite, `4ch Audio Output` & `Rec. Media dur HDMI Output`** (`G102`).
- **44-Pillar Recovery Master (`P2`, `verify-44pillar-recovery`, Pillars 1..44)**: Extends `41/41` through `Pillars 42..44` (`42` Wave-40 `Diff Set` + `Custom Key` Slot-1 `O_RDONLY` + EVF-less `Remain Shoot` vault, `43` Wave-41 `Auto Slow Shutter` + `HDMI REC Control <- TC` + `Breathing Comp.` vault, and `44` Wave-42 `260th` Milestone `44A` `APS-C S35` 4K/RAW lockout + `Face/Eye AF` clean-HDMI + `44B` `[Version]` read-only `BODYDATA.DAT` firewall), returning `VERIFIED_44OF44_PILLAR_RECOVERY_MASTER` (`cnflasha_userspace_write_blocked=True`, `fx3_has_builtin_evf=False`, `otp_fuse_touches=0`, `rpmb_counter_increments=0`, `passive_tx_bytes_emitted=0`, `physical_usb_packets_emitted=0`, `raw_firmware_bytes_leaked=0`; forward-compatible with `45+`).
- **45+ Firmware-Lab Real-Binary Auditors (`P3`, `auditors_passed >= 45 and == auditors_total`) & 50+ Stage VM HIL (`P4`, `vm_stages_passed >= 50 and == vm_stages_total`)**: Verifies all `45+` real-binary auditors plus VM Stages `48..50` (`Stage 48` LockOpParts/AudioTiming/ExpStep, `Stage 49` DisplayQuality/BTRmt/MyMenu, and `50/50` Grand Milestone `Stage 50` DiffSet/CustomKey/RemainShoot with `fx3_has_builtin_evf=False`), with dynamic `Stage 51+` discovery (`raw_firmware_bytes_leaked=0`, `physical_device_writes=0`, `emmc_corruptions=0`).
- **Sextuple Bench Readiness Preflights (`P5`, `Ph186 + Ph204 + Ph216 + Ph227 + Ph248 + Ph261`) & Live QEMU Receipts (`P6`, Rounds 28–52+)**: Verifies ALL 6 bench preflights (`preflight-card-insert` `Ph186`, `preflight-bench-cable-fan-slot1` `Ph204`, `preflight-hdmi-proxy-desqueeze-and-simult` `Ph216`, `preflight-pixelmap-ntscpal-powersave-and-autotemp` `Ph227`, `preflight-imagedb-touch-shoeaudio-and-lockop` `Ph248`, AND **`preflight-diffset-customkey-autoslow-and-apsc` `Ph261`** `A..D` + `verify_phase261_report`) return `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run (`overall_ready_for_hardware_attach=False`, `16/16 H0 == H3`, `e_nd_tx=0`), paired with **`>= 25` rounds (`25/25` incl. `25th` Real-HW / `75th` Run Milestone `Round 52`, `75/75` runs `r28a..r52c`, `50/50` PNG `< 50 KiB`, max `27,467 B`)** on unmodified FX3 `7.02` (`4.9.337-scel+`, `nop=0`, `crashes=0`, `emmc_write_count=0`).

---

## 第一章 实机部署全景架构与 6 支柱总闸门映射（Grand Milestone Phase 264）

| 支柱 ID | 对应模块与 Phase | 核心技术契约与通过门槛 | 实测基线数据（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | [`fx3_safety`](../outputs/fx3-safety/) (Ph174–259) | **`>= 102` 安全门禁 (`G01..G102`, `evaluate_102gate_preflight`)**：模拟台架干跑 `102/102`（`all_102_gates_verified=True`，含 `100/100` 里程碑 `G100`）；离线态严格锁定 `G10..G12`（`99/102`），硬锁 `emmc/spi_nor/el3/auto_flash` 与 `usb_packets_transmitted == 0` | `102/102` dry-run、`99/102` offline lock（`G63..G102` 40 项全绿，`overall_ready_for_hardware_attach=False`） |
| **`P2`** | [`fx3_recovery`](../outputs/fx3-recovery-adapter/) (Ph166–260) | **`>= 44` 恢复支柱 (`evaluate_realhw_44pillar_recovery_master`)**：在 `Pillars 1..41` 上增量闭环 **`Pillars 42..44`**（`DiffSet/CustomKey/RemainShoot`、`AutoSlow/HDMIRecCtrl/Breathing`、第 260 阶段里程碑 `44A` `APSC-S35/FaceEyeAF` + `44B` `VersionRO`） | `44/44`（`VERIFIED_44OF44_PILLAR_RECOVERY_MASTER`，`cnflasha_userspace_write_blocked=True`、`fx3_has_builtin_evf=False`、`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx_bytes_emitted=0`、`physical_usb_packets_emitted=0`） |
| **`P3`** | [`fx3_firmware_lab`](../outputs/fx3-firmware-lab/) (Ph1..231+) | **`>= 45` 实机二进制审计器（前向兼容 `45/45+`）**：全量验证 `#1..#45` 并自动纳入后续 `realhw_*_auditor.py` | `45/45`（`auditors_passed == auditors_total >= 45`，`raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0`） |
| **`P4`** | [`fx3-vm`](../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (Ph33..258) | **`>= 50` 阶段异构 VM HIL 协同仿真（前向兼容 `50/50+`）**：新增 **Stages `48..50`**（`LockOp/AudioTiming/ExpStep`、`DisplayQual/BTRmt/MyMenu`、`50/50` 大里程碑 `DiffSet/CustomKey/RemainShoot`） | `50/50`（`vm_stages_passed == vm_stages_total >= 50`，`physical_device_writes=0`、`emmc_corruptions=0`、`raw_firmware_bytes_leaked=0`） |
| **`P5`** | [`fx6_closure`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_diffset_customkey_autoslow_and_apsc_verifier.py) (Ph136/143/154/186/204/216/227/248/261) | **六联台架前置预检（`Ph186` + `Ph204` + `Ph216` + `Ph227` + `Ph248` + `Ph261` `preflight-diffset-customkey-autoslow-and-apsc`）+ `U4/U5/U6` + BYOF SD (`H0==H3`)** | 六项预检离线均 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`、模拟均 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（`4/4`、`3/3`、`5/5`、`3/3`、`4/4`、`4/4`），`H0==H3 16/16`、`e_nd_tx=0` |
| **`P6`** | QEMU Rounds 28..52+ (FX3 `7.02`) | **`>= 25` 轮实机 FX3 `7.02` (`4.9.337-scel+`) ARM64 内核 QEMU 收据 + `>= 50` 张 `< 50 KiB` PNG**：覆盖 `Rounds 28..52`（含第 25 轮实机 / 第 75 子实验里程碑 `Round 52`）并自动发现 `Round 53+` | **`25/25` 轮 (`75/75` 子实验 `r28a..r52c`)**、`50/50` PNG（max `27,467 B < 50 KiB`）、`H0==H3 16/16`、`nop=0, crashes=0, emmc=0` |

---

## 第二章 Step 1 — `054C:0DA1 -> 054C:0336` (`SET_FILE2`) Tier-0 16 面流式冷备规程

### 2.1 USB 阶段迁移与 Stage-288 `libJiritsu.so` P0 加固
在任何文件系统或包装器改动**之前**，必须通过只读冷备完成本机全量 16 面取证留档（`Gate G43/G45` + `Pillar 17/18`）：

1. **USB PID 受控切换 (`054C:0DA1 -> 054C:0336`) 与 `op=0xFF` 金丝雀**：
   - FX3 `7.02` 原厂维护模式以 `054C:0DA1` 枚举；首先可通过受控 **`op=0xFF`、`selector=0xFF`、`slot=0x11`** 执行 `64 B` 纯内存零挂载 RAM 金丝雀探测（Round 30 `r30a` 实证 `sys_mount_count=0`、`dlopen_count=0`、`emmc_write_count=0`）；
   - 随后通过 `SET_FILE2` + **`AdjustControl (0x40)`** 请求触发 `libJiritsu.so`（`225,200 B`，SHA-256 `bdef58b2...`）内联 `dlopen` 通道，切换至调试传输端点 `054C:0336`；当存在 `/tmp/jiritsu/jbusy` 锁文件时返回 `0x10000011` 零写入中止（Round 30 `r30c` 实证 `libjit_bytes_written=0`）。
   - **U6 闭环证明**（Phase 136）：Category `0x1001` 全部 19 条内置操作码均不直接导出 `/setting` 或 `/dev/nflasha*`，仅允许经由 `SET_FILE2` 注入经 Stage-288 §4 P0 加固的瞬态读写工兵（`10,032 B` `ET_DYN` `e_machine=183`）。
2. **Stage-288 §4 六项 P0 安全加固约束**：
   - **入口自毁 (`unlinkat`)**：`.init` 入口立即执行 `unlinkat("/tmp/jiritsu/libJit.so")`，Round 28/30 实证 `errno=2`（`ENOENT`），内存驻留后磁盘零残留；
   - **严格只读与反追踪打开**：所有设备读取强锁 `O_RDONLY | O_NOFOLLOW`（`devno.ko`/`emmc.ko`/`setup_nflash` 映射 `/dev/pnflasha0` 与 `/dev/nflasha*`），禁止截断（零 `O_TRUNC`）；
   - **64 KiB 页对齐 ELF 与固定哈希**：严格对齐 `ld-2.25.so` 的 `PT_LOAD p_align=0x10000` 及 `DT_HASH (1,1,0,0)`（Round 30 实证 `4` 个 `PT_LOAD` 全 64 KiB 对齐）；
   - **8 字节帧头 + CRC32 封包**：`J0` 魔数 + `u16 length` + `u32 CRC32`，如 Round 28 实证 `512 B Sector-0`（`"8246"` / `"2.00"` / `30` 分区，CRC32 `0x29f1a341`）打包为 `528 B` `FX3S0OK` 帧；
   - **双介质无损回传与 `GF(256)` 纠删**：
     - **SD 流式冷备通路 (`FX3RCPT1`)**：直接流式转储全量 16 面镜像与 `FX3RCPT1`（`528 B`）机身绑定回执至实验 SD 卡，并按 **Pillar 22A** 强制双份落盘至两个物理独立存储介质（`media_a_device_id != media_b_device_id`）；
     - **`p6 <= 4 MiB` 滑窗回传通路 (`FX3CHK1`)**：Round 30 `r30a` 实证 `7,864,832 B` 以 `2 MiB`（`<= 4 MiB`）分 4 窗拉取完毕且 `p6_residual_bytes=0`，并附带 `GF(256)`（本原多项式 `0x11d`）P+Q RAID-6 冗余校验（Round 34 `r34c` 实证 11 数据块 + 2 校验块损坏 2 块仍 100% 比特级无损愈合，`>= 3` 块丢失拒绝）。

### 2.2 16 面 Tier-0 必检指纹清单（`H0` 黄金基线）
必须覆盖：`sector0`（512 B `'8246'`）、`p1`（VFAT + `dat2=91030080` + `dat3`）、`p2`（`Backup.bin` / `psd.bin` / `defdet.bin` / `cxd90057.dtb`）、`p3`、`p5`（`WBI2`）、`p6`、`p7`、`p8`（`cpapp-b.bin`）、`p12`（`C2PA RQ_LIC.DAT`）、`p15`（`/usr`）、`p18`（`/lens/LENSFILE.BIN`）、`p23`、`p30`、`spi_nor`（`ddrtraining.dat` + `loader_nor.bin` + `/dev/mtd0ro` `16,384 B` 校验）、`otp`、`rpmb`（后三者仅元状态/只读审计，`0` 修改）。

---

## 第三章 Step 2 — 实机二进制兼容闭环（`U2` / `U3` / `libmpr.so` / `U6`）

- **`U2` Stock-CP RTOS 零侵入红线 (`p8:/cpapp-b.bin`)**：FX3 `7.02` 与 FX6 `6.01` `tomco.txt` 共享完全一致的 4 个 `memcfg=` 内存池（`1,724.00 MiB`）与 20 个 IPC 键；Stage-B 严禁修改 `p8`（`cp_mutation_bytes = 0`），通过 AP 侧 `P11` 垫片合成 FX6 独有阻塞队列 `0x92d2091c`（RTC `/dev/rtc0->udate`）与 `0x91db059b`（Smart Handle），保活 Stock-CP 全部 `44/44` `0x92840747` 操作码与 5 轴 IBIS 居中锁止。
- **`U3` 校准数据结构与 Bank 0/1 映射 (`Backup.bin` `819 -> 840`)**：Phase 137 验证 FX3 `Backup.bin` `819` 条目向 FX6 `840` 槽位及 `0xfa0080` Bank 0/1 映射的无冲突适配，运行期通过易失性 `/tmp/bk4_shadow`（`BK4\0`）内存影子承接语言/飞行模式（`0x019e0012=00` / `0x0051000f=00` / `0x01a20002=00`）与 CJK 字符集配置，确保物理 `p2:/setting/Backup.bin` 零字节写入。
- **`libmpr.so` & `DmmCfg.bin` 录影管线桥接**：Phase 140 实证 `libmpr.so` **74 项直接透传符号 + 15 项精确垫片符号**（屏蔽 FX6 专属 SDI 与物理 ND 滤镜调用）及 **20 个 MAIN `DmmCfg.bin` 内存池**；Round 29 `r29a` 已在真实 FX3 `7.02` ARM64 QEMU 内核中实测通过 `libmpr.so` `11/11` 核心符号、6 参数切换（`Base ISO 800->12800`、`23.98p`、`180.0 deg / 1/48s`、`5600K`、`S-Log3/S-Gamut3.Cine`）以及 `/tmp/r29_clip/C0001.MXF`（`640 B`, `mpr_rec_finalized=1`, `rsv_orphan_count=0`）完整封口。

---

## 第四章 Step 3 — Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接与 BYOF SD 载荷包

- **Strategy-A 零重分区桥接 (`U4` 闭环)**：拒绝高风险的 `edisx.elf` eMMC 重分区（`sector0_mutation_bytes = 0`）。启动阶段建立 `/dev/nflasha20 -> /dev/nflasha30`（`48.00 MiB`，兼容 `/dev/cnflasha30` 加密块层映射）符号链接，并将操作日志挂载为易失性 `tmpfs /etc/opelog`（含 `OPE/00` 与 `OPE/01` 目录）。FX3 原厂 `Sector 0`（30 分区）、`p12:/cert` 与 `p18:/lens` 全程 100% 原样保留。
- **BYOF SD 卡 Stage-B 目录树与清单验签（Phase 143）**：
  - `/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST`：强制绑定机身序列号与 Tier-0 `FX3RCPT1` 回执哈希（拒绝跨机身串卡启动），锁定 **13/13 Stage-B 载荷 SHA-256**；
  - `/FX6_STAGEB/shim/`：`libgrm-fbinit9.so`、`libmpr_fx6_to_fx3_bridge.so`；
  - `/FX6_STAGEB/usr_overlay/`：FX6 Stage-B 兼容库与语言资源包（`tmpfs` 总占用 `< 64 MiB`，实测 `9.234 MiB` 本地 / `8.135 MiB` 洁净室；`appFw.so` `e2bc2619...` 通过只读回环绑定，`libWlanResource.so` `47fec188...` 隔离 `WF-12 00342260` 无限重启）；
  - `/FX6_STAGEB/runtime/bk4_ram_shadow.seed` & `/FX6_STAGEB/rescue/uninstall_restore_stock.manifest`。

---

## 第五章 Step 4 — `/dev/cnflasha15` 原子 `/usr/bin/im.elf` 逃生舱包装器与 3 道毫秒级 bypass

> [!IMPORTANT]
> **`/dev/cnflasha15` 强制通道铁令 (`Gate G44` & Round 29)**  
> 凡修改 `/usr/bin/im.elf` 包装器，**必须且只能经由加密块设备节点 `/dev/cnflasha15`（或对应映射 `/dev/nflasha15`）原子操作**；**绝对禁止直接写入 `/dev/pnflasha15`（底层物理设备）**，否则将破坏加密映射一致性并立即被安全守卫拦截（`pnflasha15_rejected=1`）。

1. **原子安装与回滚实证（Round 29 `r29a / r29b`）**：
   - 将原厂 `/usr/bin/im.elf`（`40,920 B`，SHA-256 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`）原子备份为 `.orig`，写入 `128 B` 逃生舱启动包装器（`edb450bb...`）并立即执行 `MS_REMOUNT | MS_RDONLY`（验证 `EROFS` 只读锁死，耗时 `4.81 ms`）；严禁写入 `/etc/ld.so.preload`。
   - **写中故障自愈（`r29b`）**：当注入 1-bit 翻转 + 50% 短写损坏（`735f8c54...`）时，安装器在 `8.90 ms` 内自动从 `.orig` 原子回滚并恢复与原厂完全一致的 `2838e5da...`。
2. **三道独立“零变砖”物理逃生舱（Round 28 `r28a..r28c` & Phase 143）**：
   - **`EH1` 无卡极速旁路**：未检测到 `/mnt/sd/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST` 时，包装器跳过所有挂载与验签，实测耗时 **`47 us`（硬指标 `<= 50 us`）** 返回 `STOCK_FX3_BYPASS`（`rc=10`），零延迟直启原厂 FX3 `7.02`；
   - **`EH2` 物理防误触标志与按键组合**：检测到 SD 卡根目录 `STOP_STAGEB.FLAG` 或冷启动按住 **`MENU + PLAY`**（兼容 `FX3_SAFE_STOCK.FLG`），立即旁路进入原厂系统并可选触发干净自动卸载；
   - **`EH3` 清单/序列号/13 锁篡改失效关闭**：当检测到哪怕 **1 字节** 清单或载荷篡改（`r28c` 实测 `669 us <= 50 ms`），立即 `FAIL_CLOSED_STOCK_FX3_FALLBACK`（`rc=11`）拒绝挂载 `tmpfs` 并输出 `/mnt/sd/FX6_STAGEB/LAST_BOOT_DIAG.TXT` 排障日志，直接启动原厂系统。

---

## 第六章 Step 5 — `p1` 首行救援（`U5`）与 `H0 == H3` 无痕卸载 SOP

### 6.1 `p1` 首行清除单次启动锁与强制返回 `p3`（Round 29 `r29c` & `U5`）
为彻底防止更新器循环卡死（`p1` bootloop），所有从恢复/更新模式退出的操作**必须遵守 `U5` 两步退出契约**：
1. 在 `/sbin/init` 第一行或恢复入口强制执行：
   ```sh
   rm -f /setting/updater/mode* && sync
   ud_send_lsi.elf 0
   ```
2. Round 29 `r29c` 在真实 FX3 `7.02` 内核中实证：清除 `mode6` 后 `mode_files_remaining == 0`、`dat2 == 91030080`、`p3` 零改动、`next_cold_boot_bank == p3`，全流程耗时 `16.69 ms`；Round 33 `r33b` 进一步验证脏态未恢复前严禁武装 `p1`（`p1_arm_blocked_rc=-16`）。

### 6.2 `H0 -> H1 -> H2 -> H3` 16 面原厂字节级无痕卸载规程（Phase 143 & Round 30/34）
| 阶段 | 状态定义 | 关键执行动作 | 验证红线 |
| :--- | :--- | :--- | :--- |
| **`H0`** | 原厂 FX3 `7.02` 黄金基线 | Step 1 完成全量 16 面只读快照并生成 `FX3RCPT1` + 双介质 `GF(256)` 校验卷 | `16/16` SHA-256 锁定记录 |
| **`H1`** | Stage-B 原子接入态 | 通过 `/dev/cnflasha15` 原子包装 `/usr/bin/im.elf`（保留 `.orig`）并验证 `EH1..EH3` | `/dev/pnflasha15` 写入次数 `0`；`EROFS` 重新挂载成功 |
| **`H2`** | Stage-B 双系统拍摄态 | 插入已绑定本机序列号的 SD 卡运行 Stage-B 易失性 `tmpfs` 覆盖层与 `BK4\0` 影子 | 其余 15 面持久化修改 `0 B` |
| **`H3`** | 原厂字节级干净卸载态 | 拔卡或触发 `uninstall_restore_stock.manifest`：经 `/dev/cnflasha15` 原子还原 `.orig -> /usr/bin/im.elf`，删除包装器与 `/tmp/jiritsu` 残余，执行 `sync` + `MS_RDONLY` + `p1` 首行清理 | **`16/16` 存储面 `SHA256(H0) == SHA256(H3)`**，零 `.orig`/残余；通过 `5/5` 卸载中掉电恢复演练（Round 30 `r30c` & Round 34 `r34c`） |

---

## 第七章 Phase 259 102-Gate 安全总闸门与 `G45..G102` 增量守卫矩阵

由 [`fx3_safety`](../outputs/fx3-safety/)（`evaluate_102gate_preflight` / `verify-102-gates`）统一执行，在 Milestone 147 (`G01..G44`) 之上增补 **`G45..G102` 共 58 道实机主线专项安全闸门**（含 `100/100` 大里程碑 `G100`，同时保持 `verify-58-gates`..`verify-96-gates` 100% 向后兼容）：

| Gate ID | Gate Code | 核心防护域与硬锁定条件 |
| :--- | :--- | :--- |
| **`G45`** | `SERVICE_0336_OP_FF_CANARY_64K_UNLINK_AND_MSC_RETURN_SAFE` | `054C:0336` `op=0xFF`（`slot=0x11`）纯内存金丝雀、`64 KiB` `libJit.so` 自毁与返回 `054C:0DA1` |
| **`G46`** | `STAGEB_P18_RO_5AXIS_IBIS_PARK_AND_DMMCFG_POOL_SAFE` | `p18:/lens` 只读隔离、5 轴 IBIS 上电回中锁定与 `DmmCfg.bin` 20 内存池边界 |
| **`G47`** | `PNFLASHA_CNFLASHA_CID_PAIRING_AND_MTD0RO_GUARD` | `pnflasha`/`cnflasha` CID 域配对防误写及 `/dev/mtd0ro` SPI-NOR 只读防火墙 |
| **`G48`** | `RFNVS_P12_P13_MSC_0DA1_FAN_65C_OVERRIDE_AND_6100MV_ENCWFISTOP_SAFE` | `p12/p13` RF NVS 保护、`054C:0DA1` 恢复、`65°C` 紧急风扇强开与 `6100 mV` `encwfistop` |
| **`G49`** | `UART1V8_TTYAMA0_PASSIVE_RX_VMC_BNCM1_AND_EMMC_ISP_FIREWALL` | `1.8V ttyAMA0`（禁 `3.3V`）纯被动 RX、`VMC-BNCM1` 互斥与 eMMC ISP 写防火墙 |
| **`G50`** | `IMX510_PSD_DEFDET_NVS_LOCK_DUAL_ISO_AND_MLUT_GUARD` | `IMX510` 双原生 ISO、`psd.bin`/`defdet.bin` 只读锁及非烘焙 `.cube` MLUT 校验 |
| **`G51`** | `CFEXPRESS_SDXC_V90_CARD_DOOR_GPIO_AND_BODYDATA_UFU_GUARD` | `CFexpress/SDXC V90` 准入、舱门 GPIO 刷盘、`BODYDATA.DAT` UFU 共存与防错刷保护 |
| **`G52`** | `5TIER_UNBRICKABLE_RECOVERY_FX3_MODEL_ID_AND_EL3_RO_GUARD` | `0x91030080` FX3 型号锁、5 级恢复梯及 `CXD90057 EL3` + `SPI-NOR` 零发射/零写锁 |
| **`G53`** | `CXD90058_SABIN_DSP_AND_SDI_RAW_MASK_GUARD` | `CXD90058` / `sabin` SA-DSP 只读边界与 FX3 无 SDI 硬件 (`MEW`) 失效封闭屏蔽 |
| **`G54`** | `POST_BENCH_16_SURFACE_H0_H3_SEAL_AND_OFFICIAL_READINESS_GUARD` | 16 面 `H0 == H3` 封口验收、残留零计数及正式实机上台架前置守卫 |
| **`G55`** | `C2PA_RQ_LIC_RO_LOCK_AND_CROSS_MODEL_SIGNING_FIREWALL` | `p12:/cert/RQ_LIC.DAT` C2PA 只读锁定及跨型号签名拦截 |
| **`G56`** | `VMC_BNCM1_LTC_MUX_AND_IMX510_GYRO_NRTM_GUARD` | `VMC-BNCM1` `EXT-LK` `24.00fps` LTC 复用隔离与 `IMX510` `8700 us` 陀螺仪 `NRTM` XML |
| **`G57`** | `DUALMEDIA_TIER0_DEVICE_ID_SEPARATION_AND_GF256_SCRUB_GUARD` | 双独立物理介质 `FX3RCPT1` 隔离（`media_a != media_b`）与 RAID-6 `GF(256)` 洗盘 |
| **`G58`** | `TWO_STEP_HUMAN_BENCH_AUTHORIZATION_AND_ZERO_AUTO_FLASH_INTERLOCK` | 两步操作员人工签名解锁互锁与 Agent 自动刷写硬阻断（`agent_auto_flash_blocked=True`） |
| **`G59`** | `SSBOOT_WBI2_PRSV_IMG_BYPASS_AND_H0_H3_GUARD` | `ssboot` / `WBI2` `prsv-img` 休眠引导旁路、`liro.ko` / `/proc/udm` 只读锁及 `H0 == H3` 防线 |
| **`G60`** | `FX3_SLOT1_UFU_204_FLOOR_C2PA_100_CEILING_AND_WPA2_WPA3` | `>= Ver. 2.04` UFU 下限（防 `7L+7S` 闪烁）、Slot-1 `BODYDATA.DAT` 唯一性、C2PA 100 证书上限及 `WPA2/WPA3` 强制 |
| **`G61`** | `MIRA_CETUS2_EMOUNT_INFO3D_BREATHING_02CF0232_AND_P18_RO` | `MIRA_CETUS2` E-Mount `info7/8/3D` 协议、`0x02cf0232` 呼吸效应过滤（`Sony == 3` 启用/三方屏蔽）、`MC 2.1.0+` 与 `p18:/lens` RO |
| **`G62`** | `HDMI_TYPE_A_4264X2408_16BIT_RAW_BRAW_PRORES_AND_SDI_MASK` | Type-A HDMI `4264×2408` 60p 16-bit 线性 RAW（`VA 12G HDR` `.braw` / `Ninja ProRes RAW`，拒 `VA 3G`）、非烘焙与 `12G-SDI` MMIO 屏蔽 |
| **`G63..G78`** | `ILME_FX3_VS_FX3A` .. `TC_REGENERATE_SLOT1_AND_REC_LAMP` | `FX3 vs FX3A` 分支、`XLR-H1` 4ch、`No-UVC` / `DC-C1 65W`、`.cube` LUT 路径、4 档风扇 PWM、`6.01/7.02` LUT 隔离、`BIG6` `e_nd_tx=0`、`VMC-BNCM1`、`De-Squeeze 1.65x`、`Simult`、HDMI Log `1080p`、`Px` 代理、`37` 字符 `File Settings` 与耦合 `REC Lamp` |
| **`G79..G90`** | `PIXEL_MAPPING_CNFLASHA_RO` .. `TOUCH_4ITEM_AND_SUNNY_WEATHER` | `Pixel Mapping` + `/dev/cnflasha*` `O_RDONLY`、`NTSC/PAL` 保持、`SteadyShot Active` / `CIZ`、`Power Save` 9 旁路、`S&Q` 6 锁、`Zebra` / `MENU+DELETE` 拦截、`Silent Mode`、`Marker` 15 画幅、`Recover Image DB`、`Monitor Flip`、`Emphasized REC` 与 `Touch Operation` |
| **`G91..G96`** | `SHOE_AUDIO_4CH_3LOCK` .. `AUDIO_TIMING_AND_EXP_STEP_VS_SHUTTER_ANGLE` | **`Shoe Audio 48kHz/24bit 4ch` 3 锁与内置麦防风**（`G91`）、**`Save/Load CAMSET C3` 4 类敏感排除与 Slot-1 防火墙**（`G92`）、**`Framing Stabilizer` 裁切与 `Anti-flicker` / 禁 `Var. Shutter`**（`G93`）、**`USB Power` 必插 `NP-FZ100` 与 `USB LUN`**（`G94`）、**`Lock Operation Parts` `MENU+Fn 5s` 全锁 vs 阻断 `MENU+Delete` 与 `My Dial`**（`G95`）、**`Audio Out Timing` / `Audio signals` 与 `Exposure step` vs `Shutter Angle`**（`G96`） |
| **`G97`** | `DISPLAY_QUALITY_TIER0_STANDARD_CLAMP_AND_BT_RMT_IR_LOCKOUT_GUARD` | **Tier-0 冷备阶段 `[Display Quality]=[Standard]` 电流钳位** + **`[Bluetooth Rmt Ctrl]` 启用期间红外遥控互斥锁** |
| **`G98`** | `MY_MENU_36ITEM_SURVIVAL_AND_CAMSET_SLOT1_ORDONLY_FIREWALL_GUARD` | **`[My Menu]` 最多 `6×6=36` 项跨复位保持** + **Slot-1 `CAMSET01..10.DAT` `O_RDONLY` 只读防火墙** |
| **`G99`** | `DIFF_SET_STILL_MV_8ITEM_ASYMMETRIC_TRANSITION_AND_SHUTTER_ANGLE_GUARD` | **`[Different Set for Still/Mv]` 8 项非对称切换（`Custom WB` 仅静态保留）** + **`Ver. 7.02` `[Shutter Angle]` 独立优先防串扰** |
| **`G100`** | `CUSTOM_KEY_3DOMAIN_ISO_EI_SLOT1_VAULT_AND_EVFLESS_REMAIN_SHOOT_GUARD` | **`100/100` 大里程碑：`[Custom Key/Dial Set.]` 3 域 `ISO/EI` 与 Slot-1 `CAMSET01.DAT` 防火墙** + **无 EVF `FX3`（`fx3_has_builtin_evf=False`）`[Remain Shoot Display]` 静态缓存边界** |
| **`G101`** | `AUTO_SLOW_SHUTTER_6COND_LOCKOUT_AND_BREATHING_COMP_MOVIE_ONLY_GUARD` | **`[Auto Slow Shutter]` 6 条件硬锁与 `[Shutter Angle]` 互斥** + **`[Breathing Comp.]` 视频专属合规镜头及 `HDMI RAW`/`240p` 自动关闭** |
| **`G102`** | `HDMI_REC_CTRL_TC_PREREQ_4CH_AUDIO_AND_REC_MEDIA_DUR_HDMI_VAULT_GUARD` | **`[HDMI Output Settings]`：`[REC Control]=On` 强制 `[Time Code Output]=On` 前置、`[4ch Audio Output]` 与 `[Rec. Media dur HDMI Output]` Slot-1 保险库保护** |

> 执行入口：`fx3_safety.evaluate_102gate_preflight` / `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-102-gates --simulate-bench-dry-run`（保留 `evaluate_58gate_preflight`..`evaluate_96gate_preflight` 100% 不变）。

---

## 第八章 Recovery Vault 与 44 支柱恢复主引擎（Pillars `18..44` / `44/44`）

[`fx3_recovery`](../outputs/fx3-recovery-adapter/)（`evaluate_realhw_44pillar_recovery_master` / `verify-44pillar-recovery`）在 `Pillars 1..38`（保留 `verify-22pillar-recovery`..`verify-41pillar-recovery` 不变）之上增量闭环 **`Pillars 39..44`**：

| Pillar | 模块标识符 | 验证内容与零接触红线 |
| :--- | :--- | :--- |
| **Pillars 18..31** | `service_usb` .. `filesettings_tcregen_vault` | `op=0xFF` 金丝雀、`pnflasha/cnflasha` CID、`1.8V ttyAMA0`、5 级 EL3/UFU、双介质 `GF(256)`、`WBI2` 100 次掉电、`FX3BNDL1`、`FX3 vs FX3A`、`No-UVC`/`DC-C1`、4 档风扇/`6.01-7.02` LUT、Slot-1 `CAMSET`、`Px` 代理与 `37` 字符 `File Settings` |
| **Pillars 32..38** | `pillar_32_ntscpal_pixelmap` .. `pillar_38_shoe_audio_saveload` | `/dev/cnflasha*` `O_RDONLY`、`Power Save` 9 旁路、`Zebra`/Slot-1 全格拦截、`Silent Mode`/`Marker`、`Recover Image DB`、`Touch`/`Sunny Weather` 及 `Shoe Audio 4ch` + `Save/Load C3` 排除 |
| **Pillar 39** | `pillar_39_framing_usbpower_lun_antiflicker_vault` | `Framing Stabilizer` 非对称裁切、`USB Power Supply` 必插 `NP-FZ100`、`USB LUN` 与 `Anti-flicker` 禁 `Var. Shutter`（`fx3_has_var_shutter=False`） |
| **Pillar 40** | `pillar_40_lockop_5schord_audiotiming_expstep_vault` | `Lock Operation Parts` `MENU+Fn 5s` 全锁 vs 阻断 `MENU+Delete`、`Audio Out Timing` 与 `Exposure step` vs `Shutter Angle` 独立表 |
| **Pillar 41** | `pillar_41_display_quality_btrmt_mymenu_camset_vault` | `41A`: Tier-0 `Display Quality=Standard` 钳位与 `BT Rmt` IR 互斥；`41B`: `My Menu` 36 项保持与 Slot-1 `CAMSET` 只读保险库 |
| **Pillar 42** | `pillar_42_diff_set_custom_key_remain_shoot_vault` | Wave-40 `Different Set for Still/Mv` 8 项非对称切换、`Shutter Angle` 防串扰、Slot-1 `CAMSET01.DAT` `Custom Key` `O_RDONLY` 与无 EVF `FX3` `Remain Shoot Display` |
| **Pillar 43** | `pillar_43_auto_slow_shutter_hdmi_rec_ctrl_breathing_vault` | Wave-41 `Auto Slow Shutter` 6 锁、`HDMI REC Control <- Time Code Output` 前置、`Rec. Media dur HDMI` Slot-1 防写与 `Breathing Comp.` 视频专属保险库 |
| **Pillar 44** | `pillar_44_apsc_s35_face_eye_af_version_readonly_vault` | **第 260 阶段里程碑**：`44A` `APS-C S35` 12.1MP `4K/HDMI-RAW` 禁用锁与 `Face/Eye AF` 4 项 HDMI 净流零烘入；`44B` `[Version]` 纯只读弹窗 vs 硬阻断自动 `BODYDATA.DAT` 刷写（`otp_fuse_touches=0`, `rpmb_counter_increments=0`, `passive_tx_bytes_emitted=0`） |

---

## 第九章 固件审计器 `#29..#45`（`45/45+`）与 VM HIL 阶段 `25..50`（`50/50+`）

| 审计器 / VM 阶段 | 覆盖硬件子系统与关键实证指标 | 零破坏红线 |
| :--- | :--- | :--- |
| **`#29..#40` + `Stage 25..34`** | `p18:/lens` + 5 轴 IBIS + `XLR-H1` + 按键/Tally/`65°C` 风扇 + Wi-Fi/BT/CDC-NCM + `IMX510`/`.cube` MLUT + `CFexpress V90`/`.RSV` + `CXD90058/sabin` + `C2PA`/`VMC-BNCM1`/Gyro + `WBI2` + `4264×2408` RAW + `MIRA_CETUS2` + `FX3 vs FX3A` + `No-UVC`/`DC-C1` | `cp_mutation_bytes=0`, `wbi_mutation_bytes=0`, `calibration_mutation_bytes=0` |
| **`#41..#45` + `Stage 35..39`** | 4 档风扇 PWM + `[Speed]`/`[Angle]` 快门 + `6.01/7.02` LUT 隔离 + `BIG6` `e_nd_tx=0` + Slot-1 `CAMSET` + `De-Squeeze 1.65x` + 外置 `M&C Focus Map <150fps` + HDMI Log `1080p` vs `Off(HDMI Only)` + `Px` 代理 + `37` 字符 `File Settings` + `TC Regenerate` Slot-1 + 耦合 `REC Lamp` | `e_nd_actuator_tx_count=0`, `slot1_fx3_camset_mutation_bytes=0`, `raw_firmware_bytes_leaked=0` |
| **`Stage 40..47`** | `Pixel Mapping` + `/dev/cnflasha*` `O_RDONLY` + `NTSC/PAL` + `SteadyShot Active`/`CIZ` + `Power Save` 9 旁路 + `S&Q` 6 锁 + `Zebra` + `Silent Mode`/`Marker` + `Recover Image DB`/`Monitor Flip` + `Emphasized REC`/`Touch`/`Sunny` + `Shoe Audio 4ch`/`SaveLoad C3` + 第 250 阶段 `Framing`/`USB Power`/`Anti-flicker` | `cnflasha_userspace_write_blocked=True`, `fx3_has_var_shutter=False`, `emmc_mutation_bytes=0` |
| **`Stage 48..50` (`50/50` Grand Milestone)** | **`Stage 48`：`Lock Operation Parts` `MENU+Fn 5s` 全锁 vs 阻断 `MENU+Delete` + `Audio Out Timing` + `Exposure step` vs `Shutter Angle`** · **`Stage 49`：Tier-0 `Display Quality=Standard` + `BT Rmt` IR 互斥 + `My Menu` 36 项与 `CAMSET` 只读** · **`Stage 50`（`50/50` 大里程碑）：`Different Set` 8 项切换 + `Custom Key` 3 域 Slot-1 防火墙 + 无 EVF `FX3` `Remain Shoot Display`** | `milestone="50/50"`, `fx3_has_builtin_evf=False`, `physical_device_writes=0`, `emmc_corruptions=0` |

---

## 第十章 被动预检、六联台架前置预检（`Ph186` + `Ph204` + `Ph216` + `Ph227` + `Ph248` + `Ph261`）与 Live FX3 `7.02` QEMU 实证（Rounds 28–52 · `75/75` + `50` PNG）

### 10.1 Phase 154 (`preflight-realhw-bench`) 与 六联台架前置预检（`Ph186` · `Ph204` · `Ph216` · `Ph227` · `Ph248` · `Ph261`）
- **Phase 154 [`realhw_bench_preflight_and_usb_classifier.py`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py)**：100% 被动 `ioreg` 解析（`usb_packets_emitted=0`, `iokit_handles_opened=0`）识别 `054C:0DA1` / `054C:0336` / `MTP` / `UVC`，ExFAT SD 防火墙拒绝 `BODYDATA.DAT` / `edisx.elf`，校验双介质 `FX3RCPT1`。
- **Phase 186 (`preflight-card-insert`) · Phase 204 (`preflight-bench-cable-fan-slot1`) · Phase 216 (`preflight-hdmi-proxy-desqueeze-and-simult`) · Phase 227 (`preflight-pixelmap-ntscpal-powersave-and-autotemp`) · Phase 248 (`preflight-imagedb-touch-shoeaudio-and-lockop`)**：覆盖 Slot-1 ExFAT `>=128 KiB`、双介质 `FX3RCPT1`、`DC-C1 65W/5A`、精确 4 档风扇 `Always Off -> Auto`、`BIG6` `e_nd_tx=0`、`De-Squeeze 1.65x`、HDMI Log `1080p`、`Px` 代理、`37` 字符 `File Settings`、`Pixel Mapping` `/dev/cnflasha*` `O_RDONLY`、`Power Save` 9 旁路、`Recover Image DB` Slot-1 保险库、`Touch Operation`、`Shoe Audio 4ch`、`Save/Load C3` 与 `Lock Operation Parts` `MENU+Fn 5s` 组合键。
- **Phase 261 [`realhw_diffset_customkey_autoslow_and_apsc_verifier.py`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_diffset_customkey_autoslow_and_apsc_verifier.py)（CLI `preflight-diffset-customkey-autoslow-and-apsc`）**：第 6 项物理台架与开拍前综合准备度 4 组终审（`Group A` Wave-40 `Different Set for Still/Mv` 8 项非对称切换、`Shutter Angle` 独立优先、Slot-1 `CAMSET01.DAT` `Custom Key` `O_RDONLY` 防火墙与无 EVF `FX3` `Remain Shoot Display`；`Group B` Wave-41 `Auto Slow Shutter` 6 项硬锁、`HDMI REC Control <- Time Code Output` 前置、`4ch Audio` 与 `Breathing Comp.` 视频专属；`Group C` Wave-42 `APS-C S35` 12.1MP `4K/RAW` 禁用锁、`Face/Eye AF` 4 项层级 HDMI 净流隔离与 `[Version]` 纯只读防自动 `BODYDATA.DAT` 刷写；`Group D` Wave-43 `Release w/o Card/Lens` 零 E-ND、`Ver. 7.02` 5 项 `Audio Recording` 菜单 `DISP` 电平表、`Copyright Info` `<=46` 字符 PII 脱敏与 `16/16 H0 == H3`）；**全部六项前置预检离线均输出 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑均输出 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（全程 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`e_nd_tx = 0`）**。

### 10.2 Live Sony ILME-FX3 `Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 25 轮（含第 25 轮实机 / 第 75 子实验里程碑 `Round 52` · `75/75` 子实验 + `50/50` `< 50 KiB` PNG）实证清单
| Round | 汇总报告文件 | 核心实机内核验证范围（3 子实验/轮） | 实测不变量 & PNG 收据 |
| :--- | :--- | :--- | :--- |
| **Rounds 28..47** | `r28/summary.json` .. `r47/summary.json` | 覆盖 `EH1 47 us` 旁路、`/dev/cnflasha15` 原子装卸、`op=0xFF` 16 面冷备、按键/风扇/`IMX510`/`CFexpress V90`/`CXD90058`/`WBI2` 100 次掉电、E-Mount `info3D`/`4264×2408` RAW、`FX3 vs FX3A`/`XLR-H1`、`No-UVC`/`.cube` LUT、4 档风扇、`BIG6` `e_nd_tx=0`、`De-Squeeze 1.65x`、HDMI Log `1080p`、`File Settings 37-char`、`Pixel Mapping`/`cnflasha RO`、`SteadyShot`/`Power Save`、`S&Q`/`Zebra`、`Silent Mode`/`Marker`（共 20 轮 / 60 子实验） | `60/60` · `nop=0, crash=0, emmc=0` · 40 PNGs (`< 50 KiB`) |
| **Round 48** | [`r48/summary.json`](../reports/2026-11-15-round48-realhw-recover-imagedb-monitor-flip-af-sens-qemu/summary.json) | `r48a` (`Recover Image DB` 电量与 Slot-1 Tier-0 防写) · `r48b` (`Monitor Flip` 回放不翻转 + Big-6 `ZH-CN`) · `r48c` (`AF Speed 1..7` / `AF Subj. Shift Sens 1..5` + `Interval` + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` · 2 PNGs (`27,132 B` / `27,467 B`) |
| **Round 49** | [`r49/summary.json`](../reports/2026-11-15-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu/summary.json) | `r49a` (`Emphasized REC` + `Grid Line` HDMI 路由/Clean-Feed + Big-6 `ZH-CN`) · `r49b` (`Touch Operation` 4 项保持与台架防误触) · `r49c` (室内 `Sunny Weather` 钳位 + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` · 2 PNGs (`26,842 B` / `27,147 B`) |
| **Round 50 (50th Milestone)** | [`r50/summary.json`](../reports/2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu/summary.json) | `r50a` (`Shoe Audio 48kHz/24bit 4ch` 电平表与 3 锁 + Big-6 `ZH-CN`) · `r50b` (`Wind Noise Reduct.` 内置麦专属) · `r50c` (`Save/Load CAMSET C3` 排除与 Slot-1 保险库 + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` · 2 PNGs (`< 50 KiB`) |
| **Round 51** | [`r51/summary.json`](../reports/2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/summary.json) | `r51a` (`Framing Stabilizer` 裁切 + Big-6 `ZH-CN`) · `r51b` (`USB Power` `NP-FZ100` Type-C PD + `USB LUN`) · `r51c` (`Anti-flicker Shoot.` 禁 `Var. Shutter` + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` · 2 PNGs (`< 50 KiB`) |
| **Round 52 (25th Real-HW / 75th Run)** | [`r52/summary.json`](../reports/2026-11-15-round52-milestone-realhw-lockop-audiotiming-expstep-qemu/summary.json) | `r52a` (`Lock Operation Parts` `MENU+Fn 5s` 全锁 vs 阻断 `MENU+Delete` + Big-6 `ZH-CN`) · `r52b` (`Audio Out Timing` `Live`/`Lip Sync` + `Silent Mode` 静音联动) · `r52c` (`Exposure step` vs `Shutter Angle` 独立表 + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` · 2 PNGs (`50/50 max 27,467 B < 50 KiB`) |

---

## 第十一章 上机前必跑门禁指令清单（Grand Milestone Phase 264 Verification Matrix）

执行以下全部命令时，默认保持**洁净字节码**（`PYTHONDONTWRITEBYTECODE=1` 与 `/usr/bin/python3 -B`），并可在双模（本地只读供体与无供体洁净室 `FX3_FX6_FORCE_CLEAN_ROOM=1`）下交叉互验：

```sh
# 1. Grand Milestone Phase 264 102-Gate 安全总闸门与向后兼容分阶守卫（G01..G102，含 100/100 里程碑 G100，前向兼容 104+）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-102-gates --simulate-bench-dry-run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-96-gates --simulate-bench-dry-run

# 2. 44 支柱恢复保险库（cnflasha O_RDONLY + DiffSet/CustomKey + AutoSlow/HDMIRecCtrl + APSC-S35/FaceEyeAF/VersionRO）与向后兼容 41/38 支柱门禁
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-44pillar-recovery
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-41pillar-recovery

# 3. 45+ 项固件实验室审计器 & 50+ 阶段异构 VM HIL 协同仿真（含 50/50 大里程碑 Stage 50）
PYTHONDONTWRITEBYTECODE=1 make verify-firmware-lab verify-coemulation

# 4. Phase 154 被动预检 + 六联台架前置预检（Ph186 + Ph204 + Ph216 + Ph227 + Ph248 + Ph261）+ Milestone 175..254（100% 向后兼容）
PYTHONDONTWRITEBYTECODE=1 make preflight-realhw-bench
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure preflight-card-insert --dry-run-simulated --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure preflight-bench-cable-fan-slot1 --simulate-ready-bench --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure preflight-hdmi-proxy-desqueeze-and-simult --simulate-bench-dry-run --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure preflight-pixelmap-ntscpal-powersave-and-autotemp --simulate-bench-dry-run --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure preflight-imagedb-touch-shoeaudio-and-lockop --simulate-bench-dry-run --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure preflight-diffset-customkey-autoslow-and-apsc --simulate-bench-dry-run --json | head -n 25
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-175 verify-milestone-193 verify-milestone-209 verify-milestone-221 verify-milestone-233 verify-milestone-254

# 5. Grand Milestone Phase 264 六支柱实机主线总闭环闸门（双模单次实测 < 5.0s）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm /usr/bin/python3 -B -m fx6_closure verify-milestone-264 --force-clean-room --json

# 6. 全实验室快速核心门禁与洁净字节码审计
PYTHONDONTWRITEBYTECODE=1 make verify-fast
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
