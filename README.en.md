# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-1,045_Passing_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#5-legal--clean-room-compliance-notice)

> **Switch Language / Deep Reference**: [**👉 简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master (`README.md`)**](./README.md) · [**Stage-B Architecture & 16-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** digital cinema cameras, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> Persistent hardware flashing remains **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), and `calibration_mutation_bytes = 0`. Every Stage-A and Stage-B overlay operates strictly in volatile Linux DDR (`tmpfs`), accesses donor blobs strictly via `os.O_RDONLY`, and reverts cleanly to 100% stock Sony ILME-FX3 `Ver. 7.02` on power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images) and **0 vendor AES/RSA private keys**. All 7 verification suites execute cleanly in donorless mode (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) on `ubuntu-latest` + `macos-latest` via [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing interactive VM sessions with your own official firmware files.

---

## 1. Engineering Milestones Across Waves 1–8 (`Phases 1–50` · `Rounds 1–11`)

### The 7 Unified Verification Suites (`make test` — `1,045` Passing Tests)

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`167` tests)**
   - **Tier-0..Tier-4 Unbrick Escalation Ladder (`12` scenarios `S01..S12`) & `p1` `FAT12`/`FAT16` VFAT Atomic Rollback Capsule**: Verifies `FAT1==FAT2`, VFAT LFN checksums, cycle/cross-link rejection, and 6-step `fsync` atomic staging ([`unbrick_ladder_and_capsule_verifier.py`](outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [Phase 47 Report](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md)).
   - **Shifted-VMA FX3 `v7.02` `p1` 4-Site Autolocator, macOS 26 `IOUSBHost` Guard & `O_RDONLY` eMMC Forensic Verifier**: Resolves shifted `v7.02` `p1` symbols via AArch64 `ADRP/BL` (`p1_symbol_autolocator.py`), enforces macOS `0xe00002be` quiescence + Senser v1/v2 guards (`macos_usb_transport_guard.py`), verifies `EXT_CSD[179]` / `CMD42` bans / `Sector 0` / `BK4\0` / `WBI2` strictly `O_RDONLY` ([Phase 42 Report](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)), and builds freestanding static AArch64 capture workers (`fx3_p1_reader.c`, `fx3_boot_reader.c`, `elflink.py`).

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/) (`200` tests)**
   - **16-Gate Master Safety Preflight Engine (`G01..G16`)**: Composes `G01..G12` (`preflight.py`) with `G13..G16` ([`master_16gate_preflight.py`](outputs/fx3-safety/fx3_safety/master_16gate_preflight.py), [Phase 50 Report](reports/2026-11-14-phase50-wave4-c2pa-exfat-hetero-vm-intel/README.md)) to lock Sony **C2PA** (`RQ_LIC.DAT`, `sigcert.p12`, `p12:/cert`, TrustZone/RPMB), factory calibrations (`psd.bin`, `defdet.bin`, `Backup.bin`, `p6:Jiritsu`, `p18:/lens/lensfile.bin`), `exFAT` (`VolumeDirty`/`.RSV`), and `P12`/`WBI2`/`CP` immutability.
   - **Hardware Guardrails & Rehearsal**: Includes 6-stage `H0` read-only rehearsal (`--unicorn`), `serial_fault_detector_v2` (`TIMER-IP` `220s`/`90s` budget), **`RP2040-Zero -DOPEN_DRAIN` Multi-Port `48000`-baud `uart_boot` & `VMC-BNCM1` LTC firewall**, **`CrSDK` PTP2 (`0x9201..0x9209`)**, **24-pin MI-Shoe `XLR-H1`**, **`CXD90057 SPACC` (`0xf7fc0000`) `cnflasha` AES-XTS-256 guard** ([Phase 38 Report](reports/2026-11-14-phase38-crsdk-mishoe-ltc-spacc-guard/README.md)), **FX3 Fan PWM (`libfan.so @ 0x1dec`) & `NP-FZ100`/`USB-PD 9V/3A` guards** ([Phase 44 Report](reports/2026-11-14-phase44-thermal-pwm-npfz100-usbpd-guard/README.md)), and runtime anti-brick guards (`ld.so.preload`, `dd`, `nflasha10` `0x10000009`).

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`279` tests)**
   - **Stage-A (`P1..P9+Fan`) & Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` ELF/module targets / `18` sites, 100% SHA-256 rollback)**:
     - **`P10`**: 24-byte `.rodata` FX3 physical body button remap (`Fn->HOME`, `C1->KURU_PON`, `C2->MENU_CANCEL`, `C3->DISP_SEL`, `PLAY->THUMBNAIL`, `DELETE->USER`) in combined Stage-B `appFw.so` (`e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`, [Phase 20 Report](reports/2026-11-14-phase20-p10-stage-b-integration/README.md)).
     - **`P11`**: AP-side UIPC-CP shim (`0x92d2091c` `/dev/rtc0->udate` & `0x91db059b` Smart Handle ACK preserving `XLR-H1`, `developing_mode_FHD`, `0x0165`/`0x0166` `33^3` 3D LUT DMA, Cine EI `800/12800`, and **5-axis IBIS center-lock**, [Phase 21 Report](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)).
     - **`P12`**: `libWlanResource.so::_Z16handleFatalErrorv @ 0x70d4 -> mov w0, #0; ret` (`7 B` diff, `47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995`) blocking Notice `00342260` `WF-12` bootloops + `BK4\0` Airplane-Mode & selectable CJK/EN/JA shadow ([Phase 22 Report](reports/2026-11-14-phase22-wf12-wireless-fault-isolation/README.md)).
   - **Full Blueprint & Lifecycle Closure**: Closes **`U1..U5`**, `60`-ELF `.dynsym`/`DT_NEEDED`/`VERNEED` + `137` `/dev/*` + `.ko` linkage, **`S01..S10` Stage-B lifecycle drill** ([Phase 35 Report](reports/2026-11-14-phase35-stage-b-lifecycle-closure/README.md)), **`stage_b_ram_overlay_packager`** (`070701` CPIO + `9/9` `/bin/sh` `init2` sandbox, [Phase 48 Report](reports/2026-11-14-phase48-stage-b-ram-overlay-packager/README.md)), and **`stage_b_master_readiness_packet`** (`stage_b_readiness_packet_v2`, [Phase 39 Report](reports/2026-11-14-phase39-stage-b-master-readiness-dossier/README.md)).

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`81` tests)**
   - **Live QEMU ARM64 `1024×540` `GPE0` Web Console (`127.0.0.1:8768`, [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command))**: Authentic `image_00_169.uxc` `LDEC103` icons & `60/60` `0 SEGV` multi-click freeze fix ([Phase 19 Report](reports/2026-11-14-phase19-live-icon-rendering/README.md)), LRU 128-page pool (`170/170`), live **`简体中文 / EN / 日本語`** switching, FX3 `P10` button deck ([Phase 23 Report](reports/2026-11-14-phase23-128page-multilang-fx3deck/README.md)), interactive **Cine EI / Shutter / `P4` ND-Clear Lock** ([Phase 30 Report](reports/2026-11-14-phase30-cineei-lut-nd-interactive-trial/README.md)), **`.cube` `17^3/33^3` 3D LUT uploader**, **4-Ch `XLR-H1` VU meter**, **`RTMD 0xE304`**, **`CAMSET` presets** ([Phase 40 Report](reports/2026-11-14-phase40-vm-trial-cube-lut-xlr-presets/README.md)), **11-cat/128-page bilingual search & jump bar**, **live `EN/ZH/JA` `GPE0` pixel-diff verifier**, and **`HardenedThreadingHTTPServer`** ([Phase 49 Report](reports/2026-11-14-phase49-vm-trial-menu-search-hardening/README.md)).

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`34` tests)**
   - **Cold-Boot `nop_count = 0` (`r1a..r7c`) & Rounds 8–11 Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure (`r8a..r11d`)**: `13/13` Verify-Before-Mount SHA-256, `P10` keymap + `P11` telemetry + `P12` `libWlanResource.so` + `BK4 0x02cf019c=0x19`, `LDEC103` physical pool sprite blitting, and native **`MYingHeiC-GB18030-SJ_wIcon.ltt`** Simplified Chinese (`bank 19/23`) up to **`476` colors** and `24,891` glyph blits ([Round 10 Report](reports/2026-11-14-round10-fx6-on-fx3-full-icon-presenter/README.md), [Round 11 Report](reports/2026-11-14-round11-fx6-on-fx3-schinese-p12-presenter/README.md)).

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`127` tests)**
   - **5-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py`)**: Stage 1 cold-boot + `virtual-rom-v1` `/dev/ttyAMA3` BT H4 UART ([Phase 29](reports/2026-11-14-phase29-soft-gpe-bt-rom-emulator/README.md)); Stage 2 **Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> `ARM32` Stock-CP `cpapp-b.bin @ 0x00108000`** (`cp_mutation_bytes = 0`, [Phase 24](reports/2026-11-14-phase24-dual-ap-cp-ivshmem-bridge/README.md)); Stage 3 `Soft-GPE0` + `ramfb` (`HOSDAP02`); Stage 4 pure-Python `CXD90057` FDT `0xd00dfeed` (`4,614 B`) + `MmioWindowBus` + 8-ch `mhlx` rings ([Phase 41](reports/2026-11-14-phase41-qemu-pcie-bar-mailbox-dtb/README.md)); Stage 5 **`IMX510` VSYNC / `libmpr` XAVC / `SMPTE RDD 18` `RTMD 0xE304` / dual CFexpress Type A & SDXC pipeline** ([Phase 45](reports/2026-11-14-phase45-vm-imx510-xavc-cfexpress-pipeline/README.md)).

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`157` tests)**
   - **8 Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**: Keyless `UFU`/`FDAT`/`UDTRFIRM`/`SDM2` auditor (`5L+6S` guard), `ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4` differ (`5016×3344` Open-Gate negative proof), **62-pack 29-language `.uxc` + 6 CJK/JP/EN Monotype `.ltt`/`.ttf` `cmap` verifier + `1,610`-sprite CPU `LDEC`** ([Phase 27](reports/2026-11-14-phase27-uxc-multilang-cjk-font-audit/README.md)), **`IMX510`/Dual Base ISO `800/12800`/XAVC matrix** ([Phase 31](reports/2026-11-14-phase31-imx510-xavc-codec-matrix/README.md)), **`.cube` `17^3->33^3` 3D LUT + `RTMD 0xE304` verifier** ([Phase 37](reports/2026-11-14-phase37-cube-3dlut-rtmd-verifier/README.md)), **`WBI2`/`hibdrv` EL1 mismatch guard + pure-Python ELF64 `.dynsym` ABI differ** ([Phase 43](reports/2026-11-14-phase43-wbi2-hibdrv-and-elf64-abi-diff/README.md)), and **`global.xdb` `uxa\x07` + 11-cat/128-page menu tree & FX3 predicate auditor** ([Phase 46](reports/2026-11-14-phase46-global-xdb-and-128page-menu-audit/README.md)).

---

## 2. Five-Stage Hardware Boot & Trust Boundary Overview

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/boot-pipeline-en-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/boot-pipeline-en-light.svg">
    <img alt="Five-Stage Secure Boot Pipeline" src="./assets/boot-pipeline-en-light.svg" width="100%">
  </picture>
</p>

| Layer | Component | Verified Architectural Contract |
| :--- | :--- | :--- |
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows; `v7.02` `p1` resolved via 4-site AArch64 `ADRP/BL` autolocator. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 `7.02` and FX6 `6.01` (`@ 0xFE049000`); Tier-3 BootROM `48000`-baud recovery strictly requires `RP2040-Zero -DOPEN_DRAIN`. |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; `p2:/setting/{psd,defdet}.bin`, `p6:Jiritsu`, `p12:/cert` (C2PA), and `p18:/lens/lensfile.bin` remain hard-locked read-only (`G15`). |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Stage-A & Stage-B keep stock FX3 kernel, stock `p8:/cpapp-b.bin` (`@ 0x00108000`, `cp_mutation_bytes = 0`), and `p5:/wbi` hibernation blocked (`wbi_mutation_bytes = 0`). |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A (`30-stage-a-orchestrator.sh`) & Stage-B (`stage_b_init2_guard.sh`) verify all `13/13` SHA-256 digests before first mount, activate volatile `tmpfs` RAM-Overlay (`< 48 MiB` + `ro_sd_loop_bind`, `0` eMMC/WBI/CP writes), and unwind in strict reverse LIFO order. |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test, Stage-B, Firmware Lab, Co-Emulation, BYOF & hygiene targets
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 16-Gate (`G01..G16`) & Tier-0..4 architecture reference
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite 1,045-test runner + BYOF manifest audit + `git status` hygiene check
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # 7 controlled engineering packages (`1,045` automated tests total)
│   ├── fx3-recovery-adapter/                # Tier-0..4 ladder, p1 VFAT capsules, v7.02 autolocator, macOS USB & eMMC ISP (167)
│   ├── fx3-safety/                          # 16-Gate Master Preflight G01..G16, H0 rehearsal, WDT v2, RP2040, C2PA & Thermal (200)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B P1..P12+Fan, U1..U5, S01..S10, SVR4 Packager v2 & Readiness v2 (279)
│   ├── fx3-vm-trial/                        # Live QEMU port 8768 EN/ZH/JA 128-page Web UI, .cube LUT, XLR VU & search (81)
│   ├── fx6-native-presenter-closure/        # Cold-boot nop_count=0 + Rounds 8..11 real FX3 7.02 kernel GPE0 closure (34)
│   ├── fx3-vm/                              # 5-stage Dual-ISA AP<->IVSHMEM<->CP, Soft-GPE0, FDT, IMX510/XAVC/RTMD VM (127)
│   └── fx3-firmware-lab/                    # Keyless UFU/SDM2, HAITA/BK4, 62 .uxc/CJK, IMX510, .cube, WBI2 & global.xdb (157)
├── reports/                                 # Phases 1..50, Rounds 1..11, Waves 1..4 global intel & Phase 54 sync reports
└── conversations/                           # Categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Unified Test Suite, Clean-Room CI, Stage-B, Firmware Lab & Co-Emulation Targets

```bash
# 1. Run all 1,045 automated tests across all 7 suites (167 + 200 + 279 + 81 + 34 + 127 + 157) + BYOF (57+57) + hygiene check
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (zero Sony firmware blobs required — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Stage-B Lifecycle Drill, Wireless Guard, Firmware Lab, Co-Emulation & Stage-A Lifecycle targets
make stage-b-lifecycle-drill
make verify-wireless-guard
make verify-firmware-lab
make verify-coemulation
make readiness-packet
make lifecycle-drill
make dry-run

# 4. Individual Phase & Subsystem Verifiers
make verify-byof
make verify-storage-ram-budget
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
make clean-audit
```

### 4.2 Launch Interactive FX3 or FX6 Web Menu Emulators (Requires BYOF Setup)

After preparing your own official firmware files per **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**:
- **FX6 128-Page / Big6 / Cine EI / 3D LUT / Multilingual Web Console**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under the MIT license; QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
