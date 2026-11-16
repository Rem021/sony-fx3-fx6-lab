# Wave-3 Global Sony Firmware Security, QEMU Camera Rehosting & eMMC ISP Unbrick Intelligence Dossier
# Phase 42 全球索尼固件安全、QEMU 相机双核协同仿真与 eMMC ISP 离线取证情报综合报告

- **Date / 日期**: 2026-11-14
- **Lane / Worker**: Hydrogen-34 (`phase42-global-sony-wave3-recovery-vm-intel`)
- **Read-Only Safety Invariant / 只读安全底线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, Zero live camera/eFuse/RPMB writes.
- **Machine-Readable Alignment Matrix**: [`wave3_alignment_matrix.json`](wave3_alignment_matrix.json)

---

## Executive Summary / 执行摘要

**English:**  
Wave-3 global public research across Sony BIONZ XR (`CXD90057` ARM64 + `CXD90058` ARMv7-R), embedded eMMC 5.1 ISP hardware unbricking, and multi-ISA QEMU camera co-emulation converges on three critical architectural lessons for our FX3 (`ILME-FX3` v7.02) + FX6 (`ILME-FX6` v6.01) laboratory:
1. **TrustZone & Hibernation Boundary (`BL1 -> BL2 -> EL3 BL31 -> OP-TEE BL32` vs `WBI2`/`hibdrv`)**: While public `CXD90057` researchers (`DavidBuchanan314/ILCE-7M4-RE`, `Erlla/sony-a7m4-custom-firmware`, `Hearts-Ace/sony-a7r5-custom-firmware`) force cold boot by corrupting `WBI2` magic (`wbi2`/`WBI3`) in persistent flash and document `SDM2` AES-XTS-256 plus `pmca-re-reloaded` Senser v2 RSA hardening, Sony's proprietary `BL2`/`BL31`/`OP-TEE` binaries still lack full public disassembly. By keeping `nflasha1..nflasha8` completely untouched and operating strictly in volatile RAM overlay (`tmpfs`), our FX3 lab avoids all eFuse/RPMB counter burn and WBI flash bricking risks.
2. **eMMC ISP & Multi-Port `48000` Baud Forensics**: Recent JESD84-B51 eMMC forensics and June 2026 fault-injection research (*Hugget et al., FSI:DI 57:302109*) confirm that `EXT_CSD[179]` (`PART_CONFIG` `0xB3`) misconfiguration, unpowered `CMD42` forced-erase hazards, and stuck `0x00`/`0xFF` SPI/SDMMC bus reads are primary failure modes in offline hardware recovery. Multi-Port UART requires true open-drain `48000` baud signaling (`RP2040-Zero` GP27/28/29 avoiding Pico GP29's `VSYS/3` divider).
3. **Multi-ISA QEMU Camera Co-Emulation**: Comparing Magic Lantern `qemu-eos` (`qemu-eos-v4.2.1`), `OpenIPC/qemu-bench` (QEMU 10.2.0), `Avatar2` QMP orchestration, and `chocotan/a7c2-qemu` (`ramfb` + `sony-lz77.c`) validates our Phase 24 (`ivshmem-doorbell` + unmodified ARMv7-R `cpapp-b.bin`), Phase 29 (`ramfb` + software GPE + `virtual-rom-v1` BT), and Phase 33 suites—surpassing single-ISA camera forks in live cross-core shared-memory synchronization while exposing Phase 41's PCIe BAR/Mailbox FDT gap on the Wave-3 branch.

To operationalize these findings safely, Phase 42 delivers [`emmc_dump_forensic_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/emmc_dump_forensic_verifier.py) (`verify-emmc-forensics` CLI) with 28 dual-mode unit tests verifying real FX3 `2.05/nflasha1`, `nflasha8.img`, and `nflasha5.img` donor images strictly `O_RDONLY` in `2.01s`.

**中文摘要：**  
第三波（Wave-3）全球公开研究涵盖索尼 BIONZ XR（`CXD90057` ARM64 + `CXD90058` ARMv7-R）安全启动链与 TrustZone、嵌入式 eMMC 5.1 ISP 硬件救砖与 Multi-Port 串口电平安全，以及多架构 QEMU 相机协同仿真三大方向。结合本地 FX3/FX6 实验室实证，本报告提炼出三条核心结论并完成了可执行工程闭环：
1. **TrustZone 启动链与 `WBI2` 休眠边界**：社区对 `CXD90057`（“Mira”）与 `CXD90058`（“Cetus”）的逆向已公开 48 KiB BootROM（`0xFFFF0000..0xFFFFBFFF`）、Fastboot SRAM（`0x92028000`/`0xFE020000`）与 `SDM2` AES-XTS-256 加密，但 Sony 原厂 `BL2`/`BL31`/`OP-TEE` 仍无完整公开反汇编；社区常通过篡改 `nflasha5` `WBI2` 魔数为 `wbi2`/`WBI3` 强制冷启，而本实验室坚持零持久写入与易失 RAM 覆盖（`tmpfs`），做到零 eFuse/RPMB 计数消耗。
2. **eMMC ISP 取证与 Multi-Port `48000` 波特率规范**：依据 JEDEC JESD84-B51 与 2026 年 6 月发表的 `CMD42` 电压故障注入取证论文（*Hugget et al., FSI:DI 2026*），离线救砖前必须强制校验 `EXT_CSD[179]`（`PART_CONFIG` `0xB3`）防止禁用启动分区变砖，严禁盲目发送 `CMD42` Forced Erase 清空用户区，并通过严格 `O_RDONLY` 双次 SHA-256 与香农熵检测剔除总线拉死（全 `0x00`/全 `0xFF`）或截断镜像；Multi-Port 必须使用真开漏 `48000` 波特率电平转换（避开标准 Pico `GP29` 的 `VSYS/3` 分压陷阱）。
3. **QEMU 多架构相机仿真对比与工程闭环**：横评 Magic Lantern `qemu-eos`、`OpenIPC/qemu-bench`、`Avatar2` 与 `a7c2-qemu`/`zve10-qemu`，确认本实验室 Phase 24（ARM64 AP + 未修改 ARMv7-R `cpapp-b.bin` + `ivshmem`）、Phase 29（软 GPE + `ramfb` + 虚拟 BT UART）及 Phase 33 套件已领先于单核社区分支。同时 Phase 42 落地交付第四层离线只读 eMMC 取证审计器 [`emmc_dump_forensic_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/emmc_dump_forensic_verifier.py)，以 **28 项双模式单元测试**在真实 FX3 供体镜像与洁净室模式下全数通过。

---

## Pillar 1: Sony BIONZ XR ARM Trusted Firmware (`BL2`/`BL31`/`OP-TEE`), `WBI2`/`hibdrv` & `fwtool`/`PMCA`

### 1.1 Boot Chain & TrustZone Reality Check / 启动链与 TrustZone 公开边界
- **Hardware Architecture / 硬件架构**: Sony `ILME-FX3` (`CXD90057` "Mira" 4x Cortex-A35 ARM64 Linux `4.9.337-scel+` + `CXD90058` "Cetus" Cortex-R5 ARMv7-R TOPPERS/FMP RTOS) shares core SoC primitives with `ILCE-7M4` (`a7M4`) and `ILCE-7RM5` (`a7RV`).
  - Public BootROM documentation ([DavidBuchanan314/ILCE-7M4-RE](https://github.com/DavidBuchanan314/ILCE-7M4-RE)): 48 KiB BootROM mapped at `0xFFFF0000..0xFFFFBFFF`, watchdog reset register `>= 0xFFFFC000`, SRAM Fastboot loader staging at `0x92028000` (MIRAMEM) / `0xFE020000` with USB PID `18D1:4EE0`.
  - Encrypted eMMC subsystem: `SDM2` driver performs AES-XTS-256 sector encryption for `cnflasha*` nodes.
  - **Key Gap / 公开研究缺口**: Standard ARM Trusted Firmware flow (`BootROM BL1 -> BL2 -> EL3 BL31 Monitor -> OP-TEE BL32 Secure OS -> BL33 Normal World Linux`, as documented in [NXP ARM Trusted Firmware Architecture](https://www.nxp.com/docs/en/user-guide/UG10155.pdf) and [TI TF-A Boot Flow](https://software-dl.ti.com/processor-sdk-linux/esd/AM62PX/09_02_01_09/exports/docs/linux/Foundational_Components/ARM_Trusted_Firmware/Intro_atf.html)) matches Sony's SoC security posture, **however Sony's proprietary `BL2`/`BL31`/`OP-TEE` binaries remain largely undisclosed in public RE repositories**—no verified public exploit bypasses `BL2` RSA-PSS/RoT on unmodified BIONZ XR units without hardware fault/SRAM-fastboot assumptions.

### 1.2 `WBI2` (`hibdrv`) Snapshot Authentication vs Volatile RAM Overlay / 休眠恢复与易失覆盖对比
- **Embedded `hibdrv` vs Sony `WBI2`**: Embedded fast-boot frameworks such as Lineo Warp!! ([fail0verflow: Enhancing the AVIC-5000NEX - part 2](https://fail0verflow.com/blog/2014/enhancing-the-avic-5000nex-part-2/)) serialize physical RAM pages and resume execution via a dedicated kernel hibernate driver (`hibdrv`) reading a raw flash partition. Sony uses `WBI1` (CXD90045) and **`WBI2` (`nflasha5`)** on CXD90057:
  - 88-byte header `<4sI10Q` (`magic="WBI2"`, section count, flag, `resume_vector`, `sector_size=512`, `r_data_size`, `o_data_size`), followed by LZO-compressed RAM snapshot sections and 64-byte `<8Q` descriptors protected by metadata XOR checksum `0x0F0F0F0F ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt` ([Erlla/sony-a7m4-custom-firmware IMPLEMENTATION.md](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/main/IMPLEMENTATION.md)).
  - **Community Cold-Boot Hack vs Lab Policy**: Custom-firmware installers ([Erlla/sony-a7m4-custom-firmware](https://github.com/Erlla/sony-a7m4-custom-firmware), [Hearts-Ace/sony-a7r5-custom-firmware](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware)) overwrite the 4-byte `WBI2` magic to lowercase `wbi2` or `WBI3` in `nflasha5` so `hibdrv` fails magic validation and falls back to cold Linux boot. **Risk**: modifying `nflasha5` is a persistent eMMC write. Our FX3 lab keeps `nflasha1..nflasha8` strictly `O_RDONLY`, validates `WBI2` integrity offline without modifying magic bytes, and targets volatile `tmpfs` RAM-overlay experimentation only (0 eFuse/RPMB burn).

### 1.3 `fwtool.py` & `PMCA` Transport Evolution / 固件解包与 USB 传输演进
- **[ma1co/fwtool.py](https://github.com/ma1co/fwtool.py)** & **[DavidBuchanan314/fwtool.py](https://github.com/DavidBuchanan314/fwtool.py)**: Remain the standard public parsers for Sony `.DAT` (`UDTRFIRM` / `FDAT`) payloads and `p1` (`nflasha1`) / `p5` (`nflasha5`) container extraction; `fwtool.py` #54 highlights newer encrypted updater headers (e.g., A7CR/A7C2/A7IV generation keys).
- **[masterflai/pmca-re-reloaded](https://github.com/masterflai/pmca-re-reloaded) (v1.12.1) & [ma1co/Sony-PMCA-RE #752](https://github.com/ma1co/Sony-PMCA-RE/issues/752)**: Documents macOS `IOUSBHost` exclusive lock collisions (`kIOReturnExclusiveAccess` `0xe00002be`) and Sony's transition from Senser v1 (symmetric 7-round challenge, `FX3` `0x91030080`) to **Senser v2 RSA challenge** (`ILCE-7M5` / `xyzhangxin/sony-a6700-powerful`), already fail-closed guarded in our [`macos_usb_transport_guard.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/macos_usb_transport_guard.py).

---

## Pillar 2: Hardware Unbrick, eMMC ISP Forensics & Multi-Port `48000` UART

### 2.1 JEDEC JESD84-B51 `EXT_CSD` (`PART_CONFIG` `0xB3`) & Brick Mechanics / 启动分区配置与变砖机理
- **Critical `EXT_CSD` Registers ([JEDEC JESD84-B51](https://www.jedec.org/standards-documents/docs/jesd84-b51) / Linux `mmc-utils`)**:
  - `EXT_CSD[179]` (`0xB3` **`PART_CONFIG`**): Bit 6 = `BOOT_ACK`; Bits `[5:3]` = `BOOT_PARTITION_ENABLE` (`0x0`=disabled -> **hard SoC boot hang / brick**, `0x1`=BOOT0, `0x2`=BOOT1, `0x7`=UDA); Bits `[2:0]` = `PARTITION_ACCESS` (`0x0`=UDA, `0x1`=BOOT0, `0x2`=BOOT1, `0x3`=RPMB). Switching `PARTITION_ACCESS` to read `BOOT0` without restoring `0x0` before reset can trap boot loaders expecting UDA.
  - `EXT_CSD[177]` (`0xB1` `BOOT_BUS_CONDITIONS`), `EXT_CSD[162]` (`0xA2` `RST_n_ENABLE` — permanent disable `0x2` is OTP-like), `EXT_CSD[226]` (`0xE2` `BOOT_SIZE_MULT * 128 KiB`), `EXT_CSD[267..269]` (`PRE_EOL_INFO`, `LIFE_TIME_EST_TYP_A/B`).
- **eMMC ISP & Stuck-Bus Anomalies**:
  - Direct eMMC ISP probing taps `CLK`, `CMD`, `DAT0`, `GND` (`1.8V VCCQ`, `3.3V VCC` with SoC held in reset / crystal grounded). Loose spring pins, floating `DAT0` pull-ups, or reader voltage brownouts produce signature artifacts: **all-`0xFF` pull-up pages**, **all-`0x00` shorted-bus pages**, **sector-unaligned truncated reads**, or **non-deterministic two-pass SHA-256 drift**.
  - Tools such as [parse_emmc_boot0 / flash forensic parsers](https://github.com/tomeravishur/emmc-tools) and our newly implemented `analyze_bus_and_entropy()` + `verify_ext_csd_dump()` catch these defects deterministically before any partition image enters the analysis pipeline.

### 2.2 `CMD42` Lock Hazards & 2026 Fault-Injection Research / `CMD42` 锁定风险与最新文献
- **JEDEC `CMD42` (`LOCK_UNLOCK`) Hazard**: Executed in **1-bit bus width**, setting a 1–16 byte `PWD` locks UDA (`CLR_PWD`/`UNLOCK`); issuing `ERASE` (`0x08` bit) clears the password **while performing a destructive full cryptographic/physical erase of UDA** — fatal to calibration (`nflasha10` / `BK4\0`, `p12`, `p18`).
- **June 2026 Peer-Reviewed Research**: Nicolas Hugget, Thomas Souvignet, Thibaut Heckmann, and David Naccache, *"Forensic qualification of fault-assisted access restoration on CMD42-locked eMMC: A case study"*, *Forensic Science International: Digital Investigation* **57**:302109 (June 2026) (complementing Nicolas Oberli's DEF CON 27 *"Poking the 'S' in SD Cards"*). Demonstrates that **timing side-channels fail** on tested commercial eMMCs while controlled voltage glitching restored read access on **5/10 tested eMMC devices**—proving `CMD42` cannot be trivially software-bypassed and must remain strictly forbidden (`ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS = False`, `MUTATING_FORBIDDEN_OPS` blocking `cmd42_lock`/`cmd42_force_erase`).

### 2.3 Sony Multi-Port `48000` Baud Open-Drain UART Best Practices / Multi-Port 串口工程规范
- Sony's `CXD90057` UART pins (`Multi-Port` micro-USB proprietary edge pins) boot at an unusual **`48000` baud** open-drain UART before transitioning to **`115200` baud** Fastboot (`18D1:4EE0`) as documented in [DavidBuchanan314/ILCE-7M4-RE](https://github.com/DavidBuchanan314/ILCE-7M4-RE).
- **Best Practices**:
  - Use **`RP2040-Zero` (`-DOPEN_DRAIN`)** with pins GP27/28/29 and external weak pull-up (`3.3V` / camera IO tolerant level shifting); **never** reuse Raspberry Pi Pico `GP29` (`VSYS/3` resistor divider) which corrupts open-drain RX/TX levels.
  - Validate serial probe continuity passively before asserting Fastboot handshake pins; zero persistent flash writes during UART telemetry capture.

---

## Pillar 3: QEMU Multi-ISA Camera Rehosting (`ARM64` + `ARM32`/`ARMv7-R`) & Lab Phase Comparison

### 3.1 Global Landscape vs Our FX3 Lab Phases 24, 29, 33, 41 / 社区生态与本实验室对比

| Project / Phase | Target ISA / SoC | Inter-Core IPC & Display | Firmware Execution Fidelity | Safety & Forensic Integration |
|---|---|---|---|---|
| **Magic Lantern [`qemu-eos`](https://bitbucket.org/hudson/magic-lantern) / [`reticulatedpines/qemu-eos`](https://github.com/reticulatedpines/qemu-eos)** (`v4.2.1`) | Canon DIGIC (`ARMv5TE`..`AArch64`) | Custom DIGIC MMIO stubs, SDL/VNC VRAM display, `-icount` determinism, DrySh | Full DryOS bootROM + ML `autoexec.bin` | Offline ROM dump based; single-vendor MMIO patches hardcoded in QEMU C fork |
| **[`OpenIPC/qemu-bench`](https://github.com/OpenIPC/qemu-bench)** (`QEMU 10.2.0`) | 11 IP-Camera SoCs (`ARM32` HiSilicon/Goke/SigmaStar/Novatek + `ARM64` `hi3519dv500`/`nt98332`) | Table-driven SoC peripheral MMIO descriptors + SPI NOR flash snapshots | Linux kernel + rootfs rehosting without physical board | Rapid multi-SoC CI bring-up; lacks dual-CPU `AP <-> RTOS` live shared-memory IPC |
| **[`avatartwo/avatar2`](https://github.com/avatartwo/avatar2)** (+ `HALucinator` / `FirmWire`) | Hybrid `ARM` / `QEMU` + physical JTAG/HIL targets | `avatar2.protocols.qmp.QMPProtocol` + Python peripheral forwarding | Dynamic MMIO forwarding & partial HIL | Excellent QMP orchestration model; slower per-packet Python MMIO trap overhead |
| **Sony Forks ([`chocotan/a7c2-qemu`](https://github.com/chocotan/a7c2-qemu), [`cokeenet/zve10-qemu`](https://github.com/cokeenet/zve10-qemu), `Liwenru88/a7r5-rea`, `ivica00/sony-a6400-research`)** | Sony `CXD90057` / `CXD90045` (`ARM64` Linux) | `ramfb` OSD display + software GPE + `sony-lz77.c` + `virtual-rom-v1` | Mostly AP Linux userland/kernel experiments; BT/CP often stubbed | Demonstrates Sony `ramfb` & `virtual-rom-v1` viability; often lacks full `CP` execution |
| **Our Lab Phase 24 ([`dual_ap_cp_ivshmem_bridge.py`](../../outputs/fx3-vm/dual_ap_cp_ivshmem_bridge.py))** | **Dual-ISA**: `AArch64` AP (`CXD90057`) + **Unmodified Thumb-2 `ARMv7-R` `cpapp-b.bin`** (`CXD90058`) | QEMU `ivshmem-doorbell` + `ivshmem-flat` shared memory + [OpenAMP `dual_qemu_ivshmem`](https://github.com/OpenAMP/openamp-system-reference) pattern | Real Cortex-R5 vector execution + bidirectional IPC verified (22 tests) | Zero physical write; strict read-only donor loading |
| **Our Lab Phase 29 ([`soft_gpe_and_bt_rom_emulator.py`](../../outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py))** | `ARM64` + `ramfb` + `virtual-rom-v1` BT H4 | `ramfb` framebuffer + software GPE compositor + `hciattach` H4 BT UART | Full OSD icon compositing + BT HCI handshake loop (25 tests) | Deterministic clean-room & donor modes |
| **Our Lab Phase 33 ([`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py))** | Unified 3-Stage VM Co-Emulation | Integrates Phase 24 + 29 + FDT topology | End-to-end 3-stage pipeline (71 `fx3-vm` tests) | Enforces safety locks & memory budget bounds |
| **Parallel Wave-3 Phase 41 (`codex/h33-phase41-qemu-pcie-bar-mailbox-dtb`)** | `CXD90057` PCIe BAR / Hardware Mailbox / DTB | Planned PCIe BAR0/2 + Mailbox + DTB injection + QMP HIL | Branch not yet merged into base commit `b7aa47bf`; tracked as Wave-3 peer track | Will compose cleanly with Tier-4 verified dumps before booting QEMU guests |

---

## Technical Closure: Tier-4 Offline `O_RDONLY` eMMC Dump Forensic Verifier (Phase 42)

To prevent untrusted, bus-corrupted, wrong-camera (`FX6` / `FX3A` / `A7IV`), or boot-chain-mutating images from ever reaching QEMU HIL or `H0` read-only rehearsal, Phase 42 delivers:

1. **Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/emmc_dump_forensic_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/emmc_dump_forensic_verifier.py)
   - **Strict `O_RDONLY` Two-Pass Reader (`read_two_pass_sha256_readonly`)**: Opens regular single-link files with `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, verifies `fstat` invariance across two streaming SHA-256 passes, rejects symlinks/FIFOs/size drift, and never prints raw `bytes` reprs (hex digests only).
   - **Stuck-Bus / Truncation / Entropy Detector (`analyze_bus_and_entropy`)**: Rejects `ALL_ZERO_DUMP`, `ALL_FF_DUMP`, constant-byte fills (`0xAA`), `>=16` contiguous `0xFF` pull-up pages, unaligned `mod512 != 0` / truncated sizes, compressed `p1` entropy collapse (`<4.0` bits), and AES-XTS-256 `cnflasha` global (`<7.75`) or 64 KiB window (`<6.5`) entropy collapse or single `0x00`/`0xFF` pages.
   - **Sony Partition Magic & Geometry Verifiers**:
     - `verify_sector0_dump`: Validates `'8246' '2.00'` 30-entry table, `<0x80` collision checks, partition overlap checks, canonical `FX3_702` vs `FX3_PARTINF_205` profiles, and rejects **`FX6_601` `p18@0x312000` shift hazard** (`FX6_SECTOR0_P18_SHIFT_HAZARD`).
     - `verify_p1_vfat_dump`: Validates FX3 FAT12 BPB, `0x55 0xAA`, mirrored FAT1/FAT2, and root/cluster tree via `FatP1`.
     - `verify_p2_bk4_nvram_dump`: Validates raw or VFAT-embedded `'BK4\0'` (`0xAAAAAAAA` sync), 32-bit byte-sum checksum, TLV bounds, and **`PRODUCT_MODEL = 0x91030080` (`ALCIN_UUD` enum `4`) immutability** (rejecting `FX3A_0x91030082`, `A7IV_0x01030081`, and wrong enums).
     - `verify_p5_wbi2_dump`: Validates 88-byte `<4sI10Q` `'WBI2'` header, catches community-invalidated `'wbi2'`/`'WBI3'`/`'WBI0'` headers, checks 64-byte section descriptors + `0x0F0F0F0F` metadata XOR checksum, non-overlapping physical spans, and resume vector coverage.
     - `verify_p8_cp_rtos_dump`: Supports both `FAT12` (`reserved=32`, `/cpapp-b.bin`, `/tomco.txt`) and raw `cpapp-b.bin`, validating ARMv7-R reset vector `(0xE59F1004, 0xE2811004, 0xE1A0F001, 0x0010800C)` and `TOPPERS>` / `[TOMCO]` markers.
     - `verify_ext_csd_dump`: Audits 512-byte `EXT_CSD[179]` (`PART_CONFIG` `0xB3`) rejecting `BOOT_PARTITION_ENABLE == 0` (`BRICK_RISK`) and reserved bit 7, warning on leftover `PARTITION_ACCESS != UDA` or high wear (`PRE_EOL_INFO = 0x02/0x03`, `LIFE_TIME >= 0x0A`).
   - **Boot-Chain Immutability Firewall (`audit_boot_chain_immutability`)**: Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `ALLOW_BOOT_PARTITION_TARGETING = False`, blocking any manifest attempting `write`/`flash`/`erase`/`patch`/`dd`/`cmd42_force_erase` against `BOOT0`, `BOOT1`, `RPMB`, `nflashaB0/B1`, `nflasha1..nflasha8`, `sector0`, `loader_nor`, or `LdrBkup`.
2. **CLI & Package Exports**: Wired `verify-emmc-forensics` subcommand into [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) and exported all public symbols in [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py).
3. **Verification Results / 测试验收结果**:
   - **28/28** dual-mode unit tests pass in `2.01s` in Local Donor `O_RDONLY` mode (verifying real `2.05/nflasha1`, `nflasha8.img`, and `nflasha5.img` with zero errors/warnings).
   - **27/27 (+1 donor skip)** pass in `0.32s` under `FX3_FX6_FORCE_CLEAN_ROOM=1`.
   - Zero regression across all 109 pre-existing `outputs/fx3-recovery-adapter/tests` (`137` total tests).
