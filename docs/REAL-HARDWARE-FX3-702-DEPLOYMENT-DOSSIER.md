# Sony ILME-FX3 (`Ver. 7.02`) 实机 Stage-B 双系统部署、逃生舱与无痕卸载权威手册（Milestone Phase 175 Dossier）

> **文档定位 / Document Scope**: 本手册为 **Milestone Phase 175 实机主线最终台架前总闸门（`realhw_milestone175_master_gate_v1` / `make verify-milestone-175`）** 的权威工程总册，覆盖 **Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`, SoC `CXD90057` Mira + `CXD90058` Cetus)** 上部署 **ILME-FX6 (`Ver. 6.01`)** Hybrid Userland Stage-B 双系统的完整闭环链路（Phases 134–174 & QEMU Rounds 28–34）：  
> `preflight-realhw-bench`（零发射 `ioreg` 被动分类 + SD 防火墙）→ `054C:0DA1 -> 054C:0336`（`SET_FILE2` + `op=0xFF` 金丝雀 + `AdjustControl 0x40` + `64 KiB libJit.so` + 双介质 RAID-6 `GF(256)`）Tier-0 16 面冷备 → 实机全硬件/外设/双 SoC 二进制兼容与隔离（`U2/U3/libmpr.so/U6` · `p18:/lens` · `IMX510/MLUT` · `CFexpress/UFU` · `sabin/CXD90058` · `C2PA/TC/Gyro` · `WBI2/hibdrv`）→ Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接（`U4`）→ `/dev/cnflasha15` 原子 `/usr/bin/im.elf` 逃生舱包装器与 5 级不可变砖恢复梯（`EH1 47 us`..`EL3/ISP RO`）→ `p1` 首行清除救援（`U5`）与 `H0 == H3` 16 面零漂移无痕卸载 SOP。  
> **配套文档 / Companion Docs**: [`STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`](./STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md) · [`STAGE-B-ARCHITECTURE-AND-SAFETY.md`](./STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [`BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) · [`outputs/fx6-on-fx3-closure/README.md`](../outputs/fx6-on-fx3-closure/README.md)

> [!CAUTION]
> **刚性安全红线与工程状态严格边界（Hard-Locked Safety Posture & Facts vs Bench Boundary）**
> 1. **实验仓与离线门禁硬锁（当前仓库/CI 默认锁定态）**：
>    - `persistent_emmc_writes_authorized = False` · `persistent_write_release = False`
>    - `spi_nor_write_authorized = False` · `el3_payload_transmit_authorized = False` · `isp_write_authorized = False`
>    - `hardware_live_attachment_authorized = False` · `agent_auto_flash_blocked = True`
>    - `physical_usb_packets_emitted = 0` · `otp_fuse_touches = 0` · `rpmb_counter_increments = 0` · `passive_tx_bytes_emitted = 0`
>    - `sector0_mutation_bytes = 0` · `cp_mutation_bytes = 0`（`p8:/cpapp-b.bin` 与 `CXD90058` / `sabin` 零改动）· `wbi_mutation_bytes = 0`（`p5:/wbi` `WBI2` `hibdrv.ko` 禁止写入/休眠）· `calibration_mutation_bytes = 0`（`C2PA RQ_LIC.DAT` / `p2:/setting/Backup.bin, psd.bin, defdet.bin` / `p18:/lens/LENSFILE.BIN` / `p12/p13 RF NVS` 全程零修改）
> 2. **已闭环实证 vs 未执行实机台架的严格区分**：
>    - **已闭环（Verified Offline / Unicorn / POSIX `/bin/sh` / Live FX3 `7.02` `4.9.337-scel+` ARM64 QEMU）**：Phases 134–174 与 Milestone Phase 175 全部 6 支柱代码、双模测试（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）、58 安全闸门（`58/58` 模拟演练）、22 支柱恢复主引擎（`22/22`）、36 项固件实验室真实二进制审计器（`36/36`）、30 阶段异构 VM HIL 协同仿真（`30/30`）、Phase 154 被动预检分类器以及 **Rounds 28–34（7 轮共 21/21 子实验）** 实机 ARM64 内核 QEMU 演练已全部通过并留痕。
>    - **尚未执行（Not Yet Executed）**：**真实物理 Sony ILME-FX3 实机上电 USB 连接与现场台架采集/刷写/卸载会话（Physical Camera Bench Session）尚未执行**；在物理相机通过操作员两步人工授权与 `Gate G10..G12` + `Gate G58` 独立 Tier-0 实机双介质回读签收前，禁止任何持久化写入或物理 USB 控制包发射。

---

## English Executive Summary

This dossier consolidates **Milestone Phase 175 (`realhw_milestone175_master_gate_v1` / `make verify-milestone-175`)** — the Grand Unified Final Pre-Bench Master Closure spanning **Phases 134–174** and **Rounds 28–34** (`7/7` rounds, `21/21` sub-experiments) live **Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`)** ARM64 QEMU kernel rehearsals:

- **58-Gate Hardware-Truth Safety Preflight (`P1`, `G01..G58`, Phase 174)**: Upgrades Milestone 147 (`44` gates) through `G45..G58` (`58/58` dry-run simulated pass while locking `55/58` offline with `G10..G12` physical Tier-0 capture unexecuted), hard-locking `persistent_emmc_writes_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `overall_ready_for_hardware_attach = False`, and `G58` two-step human bench authorization (`agent_auto_flash_blocked = True`).
- **22-Pillar Recovery Vault & Dual-Media RAID-6 (`P2`, `verify-22pillar-recovery`, Pillars 18–22, Phase 166)**: Adds `054C:0336` `op=0xFF` zero-mount RAM canary (`slot=0x11`) + `64 KiB`-aligned self-`unlinkat` `libJit.so`, dual-layer `pnflasha/cnflasha` CID-paired + `mtd0ro` (`EROFS`/`errno=30`) firewall, `1.8V ttyAMA0` (`460800 8N1`, `3.3V` over-voltage abort `-34`) / `VMC-BNCM1` mutex + ISP write firewall, 5-Tier EL3/UFU escalation (`< 100 us` `BODYDATA.DAT` bypass), and Dual-Media (`media_a != media_b`) `GF(256)` (`0x11d`) RAID-6 bit-rot scrub & `16/16` pre-restore RAM dry-run (`OTP=0`, `RPMB=0`, `passive_tx=0`, `usb_pkts=0`).
- **36 Firmware-Lab Real-Binary Auditors (`P3`, Auditors `#29..#36`, Phases 144–171) & 30-Stage Heterogeneous VM HIL (`P4`, Stages `25..30`, Phases 145–172)**: Closes live recording (`libmpr.so` / `DmmCfg.bin`), `p18:/lens` RO + 5-axis IBIS Center-Lock + `XLR-H1` 4ch audio, body keymap + `3x` tally + `65°C` `OFF_IN_REC` fan override + `NP-FZ100` / USB-PD (`6100 mV` `encwfistop`), zero-diff Wi-Fi/BT (`0 ms` hang) / `CDC-NCM` / `054C:0DA1`, `IMX510` Dual-Base ISO (`800/12800`) + `psd/defdet` EROFS + non-bake `.cube` MLUT, `CFexpress/SDXC V90` + card-door flush + `.RSV` salvage + `BODYDATA.DAT` coexistence, `CXD90057 + CXD90058 + sabin` (`1724 MiB` memcfg + SDI-RAW `MEW` mask), `p12:/cert/RQ_LIC.DAT` C2PA + `VMC-BNCM1` `24.00fps` `EXT-LK` + `IMX510` Gyro XML, and `p5:/wbi` `WBI2` `hibdrv.ko` hibernation isolation.
- **Closure, Passive Bench Preflight (`P5`, Ph136+Ph143+Ph154) & Live QEMU Receipts (`P6`, Rounds 28–34)**: Pairs Strategy-A (`U4`), `p1` single-shot rescue (`U5`), `U6`, `EH1 47 us` SD escape, and `16/16 H0 == H3` uninstaller with Phase 154 `preflight-realhw-bench` (`usb_packets_emitted=0`, `iokit_handles_opened=0`) and `21/21` `4.9.337-scel+` QEMU receipts (`nop=0`, `crashes=0`, `emmc_writes=0`).

---

## 第一章 实机部署全景架构与 6 支柱总闸门映射（Milestone Phase 175）

| 支柱 ID | 对应模块与 Phase | 核心技术契约与通过门槛 | 实测基线数据（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | [`fx3_safety`](../outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py) (Ph174) | **`>= 58` 安全门禁 (`G01..G58`)**：干跑演练 `>= 58/58`；默认离线态严格锁定 `G10..G12`（`>= 55/58`），硬锁 `emmc/spi_nor/el3` 与两步人工授权 `G58` | `58/58` dry-run、`55/58` offline lock（`G45..G58` 14 项全绿，`overall_ready_for_hardware_attach=False`） |
| **`P2`** | [`fx3_recovery`](../outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py) (Ph166/174) | **`>= 22` 恢复支柱 (`verify-22pillar-recovery`)**：涵盖 Pillars `18..22`（`054C:0336` `op=0xFF`、`pnflasha/cnflasha/mtd0ro`、`1.8V ttyAMA0`、5 级 EL3/UFU、双介质 RAID-6） | `22/22`（`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx_bytes_emitted=0`、`physical_usb_packets_emitted=0`） |
| **`P3`** | [`fx3_firmware_lab`](../outputs/fx3-firmware-lab/) (Ph1..171) | **`>= 36` 实机二进制审计器**：涵盖 Auditors `#29..#36`（`p18` + IBIS + XLR-H1、按键 + 风扇 + FZ100、Wi-Fi/`0DA1`、`IMX510` + MLUT、`CFexpress/UFU`、`CXD90058/sabin`、`C2PA/TC/Gyro`、`WBI2/hibdrv`） | `36/36`（`calibration_mutation_bytes=0`、`wbi2_hibdrv_mutation_bytes=0`、`c2pa_cert_mutation_bytes=0`） |
| **`P4`** | [`fx3-vm`](../outputs/fx3-vm/) (Ph33..172) | **`>= 30` 阶段异构 VM HIL 协同仿真**：涵盖 Stages `25..30`（AArch64 AP + Thumb-2 Stock-CP，无损扩展兼容 Stage 31+） | `30/30`（`emmc_corruptions=0`、`cp_mutation_bytes=0`、`wf12_00342260_hits=0`） |
| **`P5`** | [`fx6_closure`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py) (Ph136/143/154) | **`U4/U5/U6` + BYOF SD (`H0==H3`) + `preflight-realhw-bench`**：Strategy-A、`EH1 <= 50 us`、`16/16 H0==H3`、零发射被动 USB 分类器 | `U4/U5/U6 CLOSED`、`EH1=47 us`、`H0==H3 16/16`、`p154_bench_go=True`（`usb_pkts=0`, `iokit=0`） |
| **`P6`** | QEMU Rounds 28..34 (FX3 `7.02`) | **7 轮实机 FX3 `7.02` (`4.9.337-scel+`) ARM64 内核 QEMU 收据**：`O_RDONLY` 只读审计（洁净室确定性合成回退），全 21 子实验零缺陷 | **`7/7` 轮 (`21/21` 子实验)**（`nop_count=0`、`crashes=0`、`emmc_write_count=0`） |

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

## 第七章 Phase 174 58-Gate 安全总闸门与 `G45..G58` 增量守卫矩阵

由 [`fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py`](../outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py) 统一执行，在 Milestone 147 (`G01..G44`) 之上增补 **`G45..G58` 共 14 道实机主线专项安全闸门**：

| Gate ID | Gate Code | 核心防护域与硬锁定条件 |
| :--- | :--- | :--- |
| **`G45`** | `SERVICE_0336_OP_FF_CANARY_64K_UNLINK_AND_MSC_RETURN_SAFE` | `054C:0336` `op=0xFF`（`slot=0x11`）纯内存金丝雀、`64 KiB` `libJit.so` 自毁与返回 `054C:0DA1` |
| **`G46`** | `STAGEB_P18_RO_5AXIS_IBIS_PARK_AND_DMMCFG_POOL_SAFE` | `p18:/lens` 只读隔离、5 轴 IBIS 上电回中锁止与 `DmmCfg.bin` 20 内存池边界 |
| **`G47`** | `PNFLASHA_CNFLASHA_CID_PAIRING_AND_MTD0RO_GUARD` | `pnflasha`/`cnflasha` CID 域配对防误写及 `/dev/mtd0ro` SPI-NOR 只读防火墙 |
| **`G48`** | `RFNVS_P12_P13_MSC_0DA1_FAN_65C_OVERRIDE_AND_6100MV_ENCWFISTOP_SAFE` | `p12/p13` RF NVS 保护、`054C:0DA1` 恢复、`65°C` 紧急风扇强开与 `6100 mV` `encwfistop` |
| **`G49`** | `UART1V8_TTYAMA0_PASSIVE_RX_VMC_BNCM1_AND_EMMC_ISP_FIREWALL` | `1.8V ttyAMA0`（禁 `3.3V`）纯被动 RX、`VMC-BNCM1` 互斥与 eMMC ISP 写防火墙 |
| **`G50`** | `IMX510_PSD_DEFDET_NVS_LOCK_DUAL_ISO_AND_MLUT_GUARD` | `IMX510` 双原生 ISO、`psd.bin`/`defdet.bin` 只读锁及非烘焙 `.cube` MLUT 校验 |
| **`G51`** | `CFEXPRESS_SDXC_V90_CARD_DOOR_GPIO_AND_BODYDATA_UFU_GUARD` | `CFexpress/SDXC V90` 准入、舱门 GPIO 刷盘、`BODYDATA.DAT` UFU 共存与防错刷保护 |
| **`G52`** | `5TIER_UNBRICKABLE_RECOVERY_FX3_MODEL_ID_AND_EL3_RO_GUARD` | `0x91030080` FX3 型号锁、5 级恢复梯及 `CXD90057 EL3` + `SPI-NOR` 零发射/零写锁 |
| **`G53`** | `CXD90058_SABIN_DSP_AND_SDI_RAW_MASK_GUARD` | `CXD90058` / `sabin` SA-DSP 只读边界与 FX3 无 SDI 硬件 (`MEW`) 失效封闭屏蔽 |
| **`G54`** | `POST_BENCH_16_SURFACE_H0_H3_SEAL_AND_OFFICIAL_READINESS_GUARD` | 16 面 `H0 == H3` 封口验收、残余零计数及正式实机上台架前置守卫 |
| **`G55`** | `C2PA_RQ_LIC_RO_LOCK_AND_CROSS_MODEL_SIGNING_FIREWALL` | `p12:/cert/RQ_LIC.DAT` C2PA 只读锁定及跨型号签名拦截 |
| **`G56`** | `VMC_BNCM1_LTC_MUX_AND_IMX510_GYRO_NRTM_GUARD` | `VMC-BNCM1` `EXT-LK` `24.00fps` LTC 复用隔离与 `IMX510` `8700 us` 陀螺仪 `NRTM` XML |
| **`G57`** | `DUALMEDIA_TIER0_DEVICE_ID_SEPARATION_AND_GF256_SCRUB_GUARD` | 双独立物理介质 `FX3RCPT1` 隔离（`media_a != media_b`）与 RAID-6 `GF(256)` 洗盘 |
| **`G58`** | `TWO_STEP_HUMAN_BENCH_AUTHORIZATION_AND_ZERO_AUTO_FLASH_INTERLOCK` | 两步操作员人工签名解锁互锁与 Agent 自动刷写硬阻断（`agent_auto_flash_blocked=True`） |

---

## 第八章 Recovery Vault 与 5 级不可变砖梯（Pillars `18..22` / `22/22`）

[`fx3_recovery/realhw_22pillar_master_recovery_verifier.py`](../outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py)（`make verify-22pillar-recovery`）在 Pillars `1..17` 之上闭环 **`Pillars 18..22`**：

| Pillar | 模块标识符 | 验证内容与零接触红线 |
| :--- | :--- | :--- |
| **Pillar 18** | `realhw_service_usb_session_and_libjit_elf_hardener` | `054C:0336` `op=0xFF`（`slot=0x11`）RAM 金丝雀 + `64 KiB` 对齐 `libJit.so` 自删除（`physical_usb_packets_emitted=0`） |
| **Pillar 19** | `realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier` | 双层 `pnflasha`（ISP 物理）/ `cnflasha`（SPACC 逻辑）CID 配对与 `/dev/mtd0ro` 只读保险库验证 |
| **Pillar 20** | `realhw_uart_460800_post_triage_and_isp_guard` | `1.8V ttyAMA0`（`460800 8N1`）/ `VMC-BNCM1` 6 阶段 POST 解码（`passive_tx_bytes_emitted=0`）与 ISP 写屏蔽 |
| **Pillar 21** | `realhw_bootrom_el3_and_ufu_stock_reflash_verifier` | 5 级 EL3/UFU 恢复升级链 + `BODYDATA.DAT` UFU 回退（`el3_payload_transmit_authorized=False`） |
| **Pillar 22** | `realhw_22pillar_master_recovery_verifier` | 双介质（`media_a != media_b`）`FX3RCPT1` 与 `GF(256)` (`0x11d`) RAID-6 2 块静默位翻转修复演练 + 16/16 RAM 预恢复演练 |

---

## 第九章 固件审计器 `#29..#36`（`36/36`）与 VM HIL 阶段 `25..30`（`30/30`）

| 审计器 / VM 阶段 | 覆盖硬件子系统与关键实证指标 | 零破坏红线 |
| :--- | :--- | :--- |
| **`#29` + `Stage 26`** | `p18:/lens`（`LENSFILE.BIN` `262,592 B` `VX8900` 57 镜头）+ 5 轴 IBIS 居中锁止 + `XLR-H1` 4ch 24b/48kHz + HDMI Type-A（SDI/BNC-TC 屏蔽） | `p18_lens_writes_permitted=False`, `emmc_mutation_bytes=0` |
| **`#30` + `Stage 26`** | 机身键位（`0x7028` MODE→Big6、`0x01fb` DISP→Status、C1..6、T/W 变焦）+ `3x` Tally GPIO + `65°C` 风扇强开（`4800 RPM`）+ `NP-FZ100` (`6100 mV` `encwfistop`) | `always_off_blocked=1`, `false_19v5_dcin_alarm=0` |
| **`#31` + `Stage 27`** | 零差异 Wi-Fi/BT（`4` 库/`8` `dlsym`、`ttyAMA3` 零挂起）+ USB `CDC-NCM`（`1000 Mbps` PTP-IP `:15740`）+ `054C:0DA1` 恢复保留 | `rf_nvs_p12_p13_writes_permitted=False`, `rf_nvs_mutation_bytes=0` |
| **`#32` + `Stage 27`** | `IMX510` 双原生 ISO（`800/12800`, `8700 us` 读出）+ `psd.bin/defdet.bin` EROFS + 非烘焙 `.cube` 17³ MLUT（`4,913` 项, NaN 拒收） | `sensor_cal_p2_writes_permitted=False`, `calibration_mutation_bytes=0` |
| **`#33` + `Stage 28`** | `CFexpress/SDXC V90`（`600 Mbps` 准入/`V30` `-22`）+ 舱门 GPIO 刷盘 + `.RSV -> .MXF` + `MEDIAPRO.XML` + `BODYDATA.DAT` UFU (`48 us < 100 us`) | `user_media_clips_intact=True`, `spi_nor_write_authorized=False` |
| **`#34` + `Stage 29`** | `CXD90057 Mira` + `CXD90058 Cetus`（`p8:/cpapp-b.bin` EROFS）+ `sabin` SA-DSP (`5` blobs) + `1724 MiB` memcfg + SDI-RAW `MEW` `-19` 屏蔽 | `cxd90058_fw_mutation_bytes=0`, `cp_mutation_bytes=0` |
| **`#35` + `Stage 30`** | `p12:/cert/RQ_LIC.DAT` C2PA EROFS（跨机型 `-22` 阻断）+ `VMC-BNCM1` `EXT-LK` `24.00fps` (`1800 mV` LTC) + `IMX510` `8700 us` 6 轴陀螺仪 `NRTM` XML (`809 B`) | `c2pa_cert_mutation_bytes=0`, `over_voltage_damage_events=0` |
| **`#36` + `Stage 30`** | `p5:/wbi` `WBI2` `hibdrv.ko` 休眠与写彻底隔离（`wbi_save_inhibited=True`, `stock_fx3_wbi2_preserved=True`） | `wbi_mutation_bytes=0` |
| **`Stage 25`** | `appFw -> libmpr.so / DmmCfg.bin` 录影双 ISA 协同仿真（衔接 Round 29 `r29a` 实机 6 参数 + `C0001.MXF` 封口） | `appfw_crashes=0`, `rsv_orphan_count=0`, `wf12_00342260_hits=0` |

---

## 第十章 Phase 154 台架被动预检 (`preflight-realhw-bench`) 与 Live FX3 `7.02` QEMU 实证（Rounds 28–34 · `21/21`）

### 10.1 Phase 154 零发射被动 USB 分类器与双备份验签 (`preflight-realhw-bench`)
由 [`fx6_closure/realhw_bench_preflight_and_usb_classifier.py`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py) 提供台架物理操作前的唯只读入口：
- **100% 被动 `ioreg` 解析**：仅读取文本/XML-plist 快照，**绝不打开 IOKit 句柄、绝不发送 USB 控制/批量包**（`usb_packets_emitted == 0`、`iokit_handles_opened == 0`），准确识别 6 态：`NO_SONY_CAMERA_ATTACHED`、`READY_MSC_054C_0DA1`、`STRANDED_SERVICE_054C_0336`（自动触发 `STOP (0336:7)` 处置手册）、`WRONG_USB_MODE_MTP_REMOTE_OR_UVC`、`MULTIPLE_SONY_DEVICES_AMBIGUOUS`、`UNSUPPORTED_MODEL_PID`；
- **ExFAT SD 卡暂存防火墙**：只读 `O_RDONLY | O_NOFOLLOW` 拒绝软链及危险工厂文件（`BODYDATA.DAT`、`edisx.elf`、`nor_loader_writer.sh`、`us_spi_firmup.sh`、`us_darwin_firm.sh`、`/setting/updater/mode*`），校验 `13/13` Stage-B 清单与 `>= 2 GiB` 空间；
- **双份 `FX3RCPT1` 交叉一致性校验**：强校验 SD 卡与 Mac 宿主保险库双份 `528 B` 回执 `CRC32 + SHA-256 + camera_cid_sha256` 一致后才签发 `GO_READONLY_PREFLIGHT`。

### 10.2 Live Sony ILME-FX3 `Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 7 轮（21/21 子实验）实证清单
| Round | 汇总报告文件 | 核心实机内核验证范围（3 子实验/轮） | 实测不变量 |
| :--- | :--- | :--- | :--- |
| **Round 28** | [`r28/summary.json`](../reports/2026-11-15-round28-realhw-escape-hatch-dualboot-qemu/summary.json) | `r28a` (`EH1 47 us` bypass) · `r28b` (`libJit.so` 自毁 + Strategy-A + Big-6) · `r28c` (`EH3` 篡改 `< 50 ms`) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 29** | [`r29/summary.json`](../reports/2026-11-15-round29-realhw-atomic-installer-mpr-rec-qemu/summary.json) | `r29a` (`/dev/cnflasha15` 原子装 + `libmpr` 6 参数 + `C0001.MXF`) · `r29b` (写中回滚) · `r29c` (`p1` 清锁) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 30** | [`r30/summary.json`](../reports/2026-11-15-round30-realhw-canary-tier0-peripheral-uninstall-qemu/summary.json) | `r30a` (`op=0xFF` RAM 金丝雀 + `64K libJit` 16 面) · `r30b` (`p18/IBIS/XLR` + Big-6) · `r30c` (`JBUSY 0x10000011` + `H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 31** | [`r31/summary.json`](../reports/2026-11-15-round31-realhw-keymap-fan-fz100-mtdro-qemu/summary.json) | `r31a` (按键/3x Tally + Big-6) · `r31b` (`65°C` 风扇 + `FZ100/PD 6100mV`) · `r31c` (`pnflasha/mtd0ro` 防火墙) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 32** | [`r32/summary.json`](../reports/2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu/summary.json) | `r32a` (`IMX510` 800/12800 + `.cube` MLUT) · `r32b` (`CDC-NCM` + `0DA1`) · `r32c` (`1.8V ttyAMA0` 6 阶段 + `3.3V` 熔断) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 33** | [`r33/summary.json`](../reports/2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu/summary.json) | `r33a` (`CFexpress/SDXC V90` + `.RSV`) · `r33b` (`BODYDATA.DAT` UFU `48 us` + FX30 拒收) · `r33c` (5 级恢复梯) | `3/3` · `nop=0, crash=0, emmc=0` |
| **Round 34** | [`r34/summary.json`](../reports/2026-11-15-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu/summary.json) | `r34a` (`C2PA + VMC-BNCM1 TC + Gyro XML`) · `r34b` (`CXD90058/sabin` + `1724M`) · `r34c` (`GF(256)` 2 块愈合 + `16/16 H0==H3`) | `3/3` · `nop=0, crash=0, emmc=0` |

---

## 第十一章 上机前必跑门禁指令清单（Milestone Phase 175 Verification Matrix）

执行以下全部命令时，默认保持**洁净字节码**（`/usr/bin/python3 -B`），并可在双模（本地只读供体与无供体洁净室 `FX3_FX6_FORCE_CLEAN_ROOM=1`）下交叉互验：

```sh
# 1. Milestone Phase 175 58-Gate 安全总闸门与分阶安全守卫（G01..G58）
make verify-48-gates verify-50-gates verify-52-gates verify-54-gates verify-56-gates verify-58-gates

# 2. 22+ 支柱恢复保险库与双介质 RAID-6 GF(256) 门禁
make verify-22pillar-recovery

# 3. Phase 154 零发射被动 USB 台架预检工作台 & BYOF SD Stage-B 演练
make preflight-realhw-bench
make verify-sd-stageb-bundle

# 4. Milestone Phase 175 Grand Unified 六支柱实机主线最终台架前总闸门（< 3.8s 本地 / < 2.2s 洁净室）
make verify-milestone-175
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-175

# 5. 全实验室快速核心门禁与全量洁净单元测试审计
make verify-fast
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
