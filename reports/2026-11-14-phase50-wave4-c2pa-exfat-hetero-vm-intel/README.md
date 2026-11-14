# Phase 50 — Wave-4 Global Sony C2PA / Calibration / exFAT / Heterogeneous-VM Intelligence Sync + 16-Gate Master Safety Preflight Engine (`G01..G16`)

# 第 50 阶段 — Wave-4 全球索尼 C2PA / 校准分区 / exFAT 介质与异构双核 VM 情报同步暨 16 门禁主安全预检引擎

**Date / 日期**: `2026-11-14`  
**Owner / 负责代理**: Hydrogen-43 (`antigravity`, isolated child worktree)  
**Target Package / 目标模块**: [`outputs/fx3-safety/fx3_safety/master_16gate_preflight.py`](../../outputs/fx3-safety/fx3_safety/master_16gate_preflight.py)  
**Machine-Readable Matrix / 结构化矩阵**: [`wave4_alignment_matrix.json`](./wave4_alignment_matrix.json)  
**Safety Redlines / 硬性安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `os.O_RDONLY` only, `calibration_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `cp_mutation_bytes == 0`.

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 50 synchronizes current public research across three mission-critical domains — **(A) Sony FX3 v6/v7 & FX6 v5/v6 C2PA Content Authenticity & factory calibration partition immutability**, **(B) CFexpress Type A / SDXC `exFAT` & `p1` `VFAT` power-loss dirty-bit hygiene**, and **(C) Heterogeneous `Cortex-A53` Linux + `Cortex-R/M` RTOS rehosting & co-emulation** — and codifies all prior hardware/Stage-B/calibration safety invariants into the **16-Gate Master Safety Preflight Engine** (`master_16gate_preflight.py`, schema `fx3-master-16gate-preflight-v1`). Existing `preflight.py` (`G01..G12`) remains completely untouched so all 174 existing tests stay 100% green, while 26 new dual-mode tests raise `outputs/fx3-safety/tests` to **200 passing tests** (`0.206s`).

**中文摘要**:  
第 50 阶段同步了三大关键领域的最新公开研究：**（A）Sony FX3 v6/v7 与 FX6 v5/v6 C2PA 内容真实性数字签名及出厂校准分区保护**、**（B）CFexpress Type A / SDXC `exFAT` 与 `p1` `VFAT` 掉电脏位保护规范**、**（C）`Cortex-A53` Linux + `Cortex-R/M` RTOS 异构双核重宿主（Rehosting）与协同仿真架构对比**，并将全部安全约束固化为 **16 门禁主安全预检引擎**（[`master_16gate_preflight.py`](../../outputs/fx3-safety/fx3_safety/master_16gate_preflight.py)）。既有 [`preflight.py`](../../outputs/fx3-safety/fx3_safety/preflight.py)（`G01..G12`）保持零改动，原有 174 项测试全部保持通过；新增 26 项双模式（本地只读宿主 / `FX3_FX6_FORCE_CLEAN_ROOM=1` 无捐赠样本净室）单元测试后，`outputs/fx3-safety/tests` 总测试数达到 **200 项（耗时 `0.206s`）**。

---

## 2. Wave-4 Live Intelligence Sync / Wave-4 公开情报同步

### 2.1 Sony FX3 v6/v7 & FX6 v5/v6 C2PA Content Authenticity & Factory Calibration Protection

| Item / 项目 | `ILME-FX3` (`0x91030080`) | `ILME-FX6` (`0x91db059b`) | Security & Lab Implication / 安全与实验约束 |
| :--- | :--- | :--- | :--- |
| **Firmware Track / 固件演进** | `v6.00..v6.02` (Sep 2024–Feb 2025: Shutter Angle, OK/NG/KEEP, 709tone) $\rightarrow$ `v7.00` (Aug 2025: BIG6, 1.5x/1.6x anamorphic, BRAW HDMI; Oct 2025 C2PA) $\rightarrow$ `v7.02` (Mar 2026) | `v5.00..v5.02` (May–Sep 2024: 1.5x de-squeeze, 709tone, 23.98PsF SDI) $\rightarrow$ `v6.00` (Mar 2026: BIG6, BRAW HDMI, HLG Mild) $\rightarrow$ `v6.02` (Nov 2026: dual-slot rec fix) | Baseline `FX3 v7.02` + `FX6 v6.01/v6.02` matches our `G01` SHA-256 baseline. |
| **Sony C2PA Support / C2PA 数字签名支持** | **Supported** on `ILME-FX3` **Ver. 7.00+** (and `ILME-FX3A` Ver. 2.00+) for stills + MP4 `<= 222 Mbps` (excludes S&Q, 8K, live stream). | **Not Supported** (absent from Sony Camera Authenticity Solution camera list). | Preserving FX3 `p12:/cert`, TrustZone RoT, and `RQ_LIC.DAT` is critical even while running FX6 Stage-B UI overlays. |
| **Provisioning & Key Storage / 密钥与证书存储** | Paid license `RQ_LIC.DAT` (Slot 1 root, `<= 100` licenses/file), hardware chipset `Create Key Pair` (TrustZone / OP-TEE / RPMB / `p12:/cert` `40 MiB`), PKCS#12 `sigcert.p12/.pfx`, server time sync, and single-axis 3D depth metadata. | `p12:/cert` (`20 MiB`), TrustZone `BL31`/`BL32`, no C2PA license path. | Standard `[Setting Reset]`/`[Initialize]` preserves licenses, whereas `[Delete Signature Func.]` or wiping `p12:/cert`/`RPMB` permanently destroys camera keys. |
| **Calibration & Crypto Partitions / 校准与加密分区** | `cnflasha*` (`type=5, flag&1` SPACC `0xF7FC0000` AES-XTS-256), `p2:/setting/{Backup.bin,psd.bin,defdet.bin}`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin` (`0x31C000`), `SPI NOR ddrtraining.dat`. | Same SPACC XTS layout, but FX6 Sector 0 shifts `p18` to `0x312000` and `p12` to `20 MiB`. | Naive modding (`adjstctl.elf A_*`, cross-body `nflasha2`/`nflasha6`, Sector 0 overwrite) causes permanent de-calibration or bricking; **our volatile `tmpfs` RAM overlay guarantees `calibration_mutation_bytes == 0`**. |

**Verified Public Citations / 公开引用链接**:
- Sony Camera Authenticity Solution (Updated `2026/6/25`): <https://authenticity.sony.net/camera/en-us/index.html>
- Sony Digital Signature Function Help Guide (Enabling & `RQ_LIC.DAT` / `Create Key Pair`): <https://helpguide.sony.net/di/digitalsign/v1/en/contents/Enabling_digital_sig_func.html>
- Sony Digital Signature Function Help Guide (Loading `sigcert.p12` / Disabling & `Delete Signature Func.`): <https://helpguide.sony.net/di/digitalsign/v1/en/contents/Disabling_digital_sig_func.html>
- C2PA Technical Specification v2.1 — Trust Model & Hardware RoT: <https://c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html#_trust_model>
- `DavidBuchanan314/ILCE-7M4-RE` (BIONZ XR BootROM `0xFFFF0000..0xFFFFBFFF`, `SPACC` `0xF7FC0000`, `SDM2` AES-XTS): <https://github.com/DavidBuchanan314/ILCE-7M4-RE>

---

### 2.2 Camera Media Card (`CFexpress Type A` / `SDXC` exFAT & `p1` VFAT) Power-Loss & Dirty-Bit Hygiene

**English**:  
Per Microsoft's official **exFAT Specification**, `exFAT` is **non-journaled**: `VolumeFlags` at Main VBR byte offset `106` (`0x6A`, explicitly excluded from the 11-sector VBR checksum) holds `VolumeDirty` (bit 1). If an experimental Stage-A/B trial hits sudden battery brownout, thermal shutdown, or USB disconnect mid-recording:
1. **`VolumeDirty` Lockout**: `VolumeDirty=1` remains set, triggering macOS `fsck_exfat` mount blocks or camera "Recover Image DB" prompts.
2. **Torn Allocation Bitmap / `.RSV` Unfinalized Clips**: Open XAVC `.MP4`/`.MXF` recordings lack a finalized `moov` atom and remain as `.RSV` files, while CFexpress Type A NVMe garbage-collection caches may stall if power is yanked without clean unmount.
3. **Destructive `chkdsk /f` Pitfall**: Running `chkdsk /f` directly on the original media card severs orphaned exFAT clusters into `FOUND.000/FILE0000.CHK`. Always image the card read-only (`ddrescue` / `os.O_RDONLY`) first, use frame-header carving (`rsv.repair` / `untrunc`) on the clone, enforce **Gate `G14`** (`NP-FZ100 >= 80% / >= 7800 mV` + `USB-PD 9V/3A` + `90°C` graceful unmount), and enforce **Gate `G15`** (rejecting `exfat_dirty_bit_present` or `exfat_unfinalized_rsv_present`). Meanwhile, `p1` (`FAT12` / `VFAT`) `nflasha10` (`12 MiB`) avoids `0x10000009` exhaustion via atomic write budgets and zero mounted `busybox dd` truncation.

**中文说明**:  
依据 Microsoft 官方 **exFAT 规范**，`exFAT` **不具备日志（non-journaled）**：主引导扇区（Main VBR）字节偏移 `106`（`0x6A`，不计入 VBR 校验和）的 `VolumeFlags` 第 1 位为 `VolumeDirty` 标志。若 Stage-A/B 试运行期间遭遇电池欠压、过热关机或异常断电：
- **`VolumeDirty=1` 挂载锁死**：导致 macOS `fsck_exfat` 阻塞或机身触发数据库修复；
- **位图撕裂与 `.RSV` 未封口视频**：XAVC 录制流缺少 `moov` 原子并残留 `.RSV`，盲目在原卡运行 `chkdsk /f` 会将孤立簇切断为 `FOUND.000/FILE0000.CHK`。
- **实验 hygiene 规范**：原卡必须先以只读（`ddrescue` / `os.O_RDONLY`）克隆再进行 `.RSV` 修复；**门禁 `G14`** 强制 `NP-FZ100 >= 80% / >= 7800 mV`、`USB-PD 9V/3A` 及 `90°C` 优雅卸载；**门禁 `G15`** 显式拦截携带 `VolumeDirty` 脏位或未封口 `.RSV` 的介质进入试验流。

**Verified Public Citation / 公开引用链接**:
- Microsoft Learn — exFAT File System Specification (`VolumeFlags` Offset `106` / `0x6A`, `VolumeDirty`): <https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification>

---

### 2.3 Heterogeneous Dual-Core (`Cortex-A53` Linux + `Cortex-R/M` RTOS) Rehosting & Co-Emulation Comparison

| Platform / 架构 | AP Engine (`Cortex-A53`) | CP / RTOS Engine (`Cortex-R/M`) | Inter-Core IPC / 核间通信 | Assessment for FX3/FX6 Lab / 对本实验室的评估 |
| :--- | :--- | :--- | :--- | :--- |
| **Lab Hybrid VM (`outputs/fx3-vm`)** | `QEMU AArch64` (real Sony `4.9.337-scel+` + `appFw.so`) | `Unicorn` ARMv7-R (unmodified `cpapp-b.bin`) | PCI `ivshmem-doorbell` + `FDT` + `ramfb` + monitor bridge | **Best fit**: boots authentic Sony Linux userland + unmodified ARMv7-R CP with sub-ms UIPC/FDT state sync. |
| **QEMU `ivshmem-flat` + PCI `ivshmem`** | `QEMU AArch64` PCI host | `QEMU` non-PCI `Cortex-M/R` guest | `ivshmem-flat` MMRs (`INTRMASK`, `INTRSTATUS`, `IVPOSITION`, `DOORBELL`) via `ivshmem-server` | Ideal upstream QEMU blueprint if CP ever migrates off Unicorn into a full `Cortex-R52`/`M` QEMU guest. |
| **Antmicro Renode** | Functional ARMv8-A | Functional Cortex-R5 (Zephyr OpenAMP / RPMsg) | Deterministic virtual bus + shared RPMsg ring | Excellent deterministic functional AMP testing, but lacks Sony `4.9.337` / `SCEL` / `ramfb` device fidelity. |
| **Avatar2** | `QEMU` via QMP | `Unicorn` / Physical JTAG-SWD HIL | Python QMP + MMIO forwarding | Proven for physical JTAG/SWD MMIO forwarding, but Python round-trip latency bottlenecks high-rate `SysTick`/DMA UI streams. |
| **Icicle** | Rust + Ghidra SLEIGH P-code JIT | Single-core P-code | In-process snapshot fuzzing | Complementary for offline coverage-guided fuzzing of isolated parsers (`BK4\0`, `Sector 0`, `CrSDK`), not dual-OS UI display co-simulation. |

**Verified Public Citations / 公开引用链接**:
- QEMU System Documentation — `ivshmem-flat` Device (`INTRMASK`/`INTRSTATUS`/`IVPOSITION`/`DOORBELL`): <https://www.qemu.org/docs/master/system/devices/ivshmem-flat.html>
- `avatartwo/avatar2` (Multi-target QEMU + Unicorn + Physical JTAG orchestration): <https://github.com/avatartwo/avatar2>
- `Icicle-emu/icicle` (Rust + Ghidra SLEIGH P-code emulator, ACM CCS 2022 `10.1145/3597926.3598039`): <https://github.com/Icicle-emu/icicle> & <https://dl.acm.org/doi/10.1145/3597926.3598039>

---

## 3. Phase 50 16-Gate Master Safety Preflight Engine (`G01..G16`)

[`master_16gate_preflight.py`](../../outputs/fx3-safety/fx3_safety/master_16gate_preflight.py) composes `preflight.evaluate_12_safety_gates` (`G01..G12`) with four new Stage-B / Hardware-Session Safety Gates (`G13..G16`):

| Gate | Code / 门禁编号 | Integrated Verifier / 集成校验器 | Fail-Closed Guarantees / 失效关闭保障 |
| :--- | :--- | :--- | :--- |
| **`G13`** | `MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION` | `evaluate_phase38_safety_guards` + `validate_rp2040_multiport_harness` | Blocks `VMC-BNCM1` LTC + `uart_boot` pin-sharing (`Pin 7/8/9`, `680 kOhm` vs `100 kOhm`), enforces `RP2040-Zero -DOPEN_DRAIN` (`1.8V/3.15V`), verifies `P11` `0x91db059b -> 0x88000002` `XLR-H1` coexistence, and isolates `CrSDK` PTP2 + `SPACC` XTS. |
| **`G14`** | `THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE` | `evaluate_thermal_pwm_and_power_guard` | Enforces `CXD90057 SoC < 62.0°C` start headroom, FX3 `libfan.so @ 0x1dec` 4-mode PWM envelope (`82°C` warning, `90°C` teardown), `NP-FZ100 >= 80% / >= 7800 mV` (blocking `BP-U 11500 mV` comparators), and `USB-PD 9V/3A` droop `<= 450 mV`. |
| **`G15`** | `C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY` | `verify_c2pa_and_factory_calibration_immutability` | Blocks mount/write/script targets hitting `cnflasha*`, `RPMB`, TrustZone / OP-TEE / Sony C2PA (`RQ_LIC.DAT`, `sigcert.p12/.pfx`, `p12:/cert`, `/dev/tee*`), or factory calibration (`psd.bin`, `defdet.bin`, `Backup.bin`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin`, `ddrtraining.dat`, `adjstctl A_*`); requires `calibration_mutation_bytes == 0` and clean `exFAT` (`VolumeDirty=0`, no `.RSV`). |
| **`G16`** | `STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK` | `verify_stage_b_p12_wf12_and_wbi2_lock` | Audits FX6 `libWlanResource.so` (`O_RDONLY` SHA-256 `eb7785e0...`) & `P12` `0x70d4` (`00008052c0035fd6`, `rc=0`) + `BK4\0` Airplane shadow (`{0x019e0012: 0, 0x0051000f: 0, 0x01a20002: 0}` for Sony Notice `00342260` `WF-12` immunity), `wbi_mutation_bytes == 0`, `cp_mutation_bytes == 0`, `nvram_persistent_writes == 0`, and `persistent_emmc_writes_authorized == False`. |

---

## 4. Verification Receipts / 实测验证记录

1. **CLI Offline 13-Gate & 16-Gate Dry-Run (`verify-16-gates`)**:
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-16-gates`:  
     `status=VERIFIED_G01_G09_AND_G13_G16_AWAITING_PHYSICAL_TIER0 mode=LOCAL_DONOR_O_RDONLY verified=13/16 g13_to_g16_all_passed=True all_16_gates_verified=False persistent_emmc_writes_authorized=False` (`rc=0`).
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-16-gates --dry-run-tier0 --json`:  
     `status=VERIFIED_ALL_16_GATES_OFFLINE_DRY_RUN verified_gates=16/16 g13_to_g16_all_passed=True all_16_gates_verified=True persistent_emmc_writes_authorized=False` (`rc=0`).
2. **Unit Tests (Dual-Mode / 双模式单元测试)**:
   - Phase 50 (`test_master_16gate_preflight.py`, Local Donor mode): **26 tests in 0.031s — OK**.
   - Phase 50 (`test_master_16gate_preflight.py`, `FX3_FX6_FORCE_CLEAN_ROOM=1`): **26 tests in 0.023s — OK**.
   - Full `outputs/fx3-safety/tests` suite: **200 tests in 0.206s — OK**.
