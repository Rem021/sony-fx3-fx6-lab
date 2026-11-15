# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-32--Gate_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-10--Pillar_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-2,980_Local_%7C_2,922_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r19e_(18%2F18_%2B_45%2F45_%2B_55%2F55)-success?style=flat)](#the-7-unified-verification-suites-make-test--2980-local-donor--2922-clean-room)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#5-legal--clean-room-compliance-notice)

> **Switch Language / Deep Reference**: [**👉 简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master (`README.md`)**](./README.md) · [**Stage-B Architecture & 32-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** digital cinema cameras, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> Persistent hardware flashing & live attach remain **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `hardware_live_attachment_authorized = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), `calibration_mutation_bytes = 0`, `otp_fuse_touches = 0`, `rpmb_counter_increments = 0`, and `passive_tx_bytes_emitted = 0`. Every Stage-A and Stage-B overlay operates strictly in volatile Linux DDR (`tmpfs`), accesses donor blobs strictly via `os.O_RDONLY`, supports `< 1s` zero-cable `FX3_SAFE_STOCK.FLG` SD escape, and reverts cleanly to 100% stock Sony ILME-FX3 `Ver. 7.02` on power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images) and **0 vendor AES/RSA private keys**. All `7` verification suites (`2,922` clean-room tests) plus `Milestone Phase 110 Master Gate`, `32-Gate`, `10-Pillar Recovery`, `Milestone Phase 90`, `24-Gate`, `RP2040`, `init2`, `Tier-0 GF(256)`, `OTP/RPMB Anti-Rollback`, and `Post-Trial` CLI gates execute cleanly in donorless mode (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) on `ubuntu-latest` + `macos-latest` via [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing interactive VM sessions with your own official firmware files.

---

## 1. Engineering Milestones (`Phases 1–110` · `Rounds 1–19` · `Waves 1–11`)

### The 7 Unified Verification Suites (`make test` — `2,980` Local Donor / `2,922` Clean-Room)

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`439` Local Donor / `381` Clean-Room tests)**
   - **10-Pillar Recovery Master Suite (`make verify-10pillar-recovery`)**: Composes all `7` foundational recovery pillars (`macOS IOUSBHost`, `RP2040-Zero -DOPEN_DRAIN` `make verify-rp2040-fixture`, `< 1s` `FX3_SAFE_STOCK.FLG` `init2` escape + WDT `make verify-init2-escape`, `GF(256)` RAID-6 Tier-0 healer `make verify-tier0-backup`, `OTP/RPMB` anti-rollback `make verify-antirollback-guard`, `Tier-0..Tier-4` ladder, and passive `1.8V` RX-only UART `S0..S6` decoder with `passive_tx_bytes_emitted == 0`) **plus** **Pillar 8 (Ph94)** CXD90057 15-partition GPT CRC32 healer & RPMB HMAC-SHA256 replay guard + 2-man SD rescue bundle ([Phase 94 Report](reports/2026-11-14-phase94-gpt-rpmb-rescue-bundle-verifier/README.md)), **Pillar 9 (Ph101)** SVR4 `newc` cpio traversal/setuid/blk firewall & JEDEC `EXT_CSD[267..269]` Pre-EOL health auditor ([Phase 101 Report](reports/2026-11-14-phase101-ramdisk-overlay-emmc-health-verifier/README.md)), and **Pillar 10 (Ph106)** FDT `0xd00dfeed` `/chosen/bootargs` `ro` firewall & ARM64 `0x644d5241` Kernel `Image` cross-SKU guard ([Phase 106 Report](reports/2026-11-14-phase106-fdt-bootargs-kernel-recovery-verifier/README.md)).

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/) (`505` Local Donor / `505` Clean-Room tests)**
   - **32-Gate Master Safety Preflight Engine (`G01..G32`, `make verify-32-gates`)**: Extends `G01..G24` (`make verify-24-gates`, covering C2PA, `exFAT`, `USB-LAN`, D-Tap/HDMI `V_LENS` crowbar, `NP-FZ100 >= 15%` UPS, `+48V` XLR, gimbal torque, Magnus dew-point `TEC`, and PMIC `5V 900 mA`) with **Phase 92** (`G25` Sigma fan intake/exhaust occlusion & rain blimp, `G26` `1/4-20` tripod screw `<=5.5mm` & housing vacuum, [Phase 92](reports/2026-11-14-phase92-intake-occlusion-tripod-26gate-safety/README.md)), **Phase 97** (`G27` IMX510 laser/curtain-at-power-off/IBIS transport lock, `G28` `-20C` Li-Ion ESR sag & `>3000m` altitude derating, [Phase 97](reports/2026-11-14-phase97-sensor-curtain-subzero-28gate-safety/README.md)), **Phase 100** (`G29` 5GHz/6GHz TX near-field EMI & ESD, `G30` `>6h` exFAT clip-spanning & CFexpress zero-NVRAM-churn, [Phase 100](reports/2026-11-14-phase100-wireless-emi-endurance-30gate-safety/README.md)), and **Phase 104** [`pl_cantilever_dummybatt_and_32gate_guard.py`](outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py) (`G31` heavy PL-to-E cantilever `15mm` LWS lens support & `G32` 14.8V/26V V-Mount dummy-battery `>8.4V` OVP crowbar — `29/32` offline truthful block vs `32/32` simulated rehearsal, [Phase 104](reports/2026-11-14-phase104-pl-cantilever-dummybatt-32gate-safety/README.md)).

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`517` Local Donor / `517` Clean-Room tests)**
   - **Milestone Phase 110 6-Pillar Century+10 Master Gate ([`stage_b_milestone110_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone110_master_gate.py), `make verify-milestone-110`, `< 2.5s`)**: Unifies all 6 Milestone-110 pillars (`32-Gate`, `10-Pillar Recovery`, `>= 20` Firmware-Lab Auditors, `>= 18` VM Stages, `Round 14 (18/18)` + `Round 17 (10/10 Status 45/45)` + `Round 19 (11/11 Menu 55/55)` real FX3 `7.02` closures, and `H0 == H2` 16-surface immutability + hardware lock invariants) with deterministic `milestone110_sha256` ([Phase 110 Report](reports/2026-11-14-phase110-milestone-master-gate-and-docs-sync/README.md)).
   - Preserves **Phase 90 Master Gate (`make verify-milestone-90`)**, **Stage-A (`P1..P9+Fan`)**, **Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` ELF/module targets / `18` sites, 100% SHA-256 rollback)**, **`U1..U5`**, **`S01..S10` lifecycle drill**, **Phase 52/76 Candidate Integrator & Dossier v3**, and **Phase 62/68/83 Capstone `H0 == H2` Forensic Auditor** (`make verify-post-trial-audit`).

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`273` Local Donor / `273` Clean-Room tests)**
   - **Live QEMU ARM64 `1024×540` `GPE0` Web Console (`127.0.0.1:8768`, [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command))**: Authentic `LDEC103` icons (`60/60` `0 SEGV`), LRU 128-page 4-language pool (`简体中文 / 繁體中文 / EN / 日本語`), FX3 `P10` deck, 4-Ch `XLR-H1` VU meter, **Phases 56/64/73/81** (Scopes, Cine EI `800/12800`, Shutter Angle/`S&Q 1–240fps`, Shockless WB/`*M01.XML`, 627-pt `Touch AF`, `x4` Focus Magnify, `S-Log3` False Color/`EL-Zone`, `CIZ`, `CAMSET` round-trip), **Phase 95** (`1.33x..2.0x` Anamorphic IBIS Asymmetric/Center-Lock, Gyroflow `2000Hz` RTMD HUD, `1kHz -20dBFS` tone + 4-Ch `-3.0 dBFS` limiter, [Phase 95](reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md)), and **Phase 102** (Picture Cache `<=384 MiB` DDR ring-buffer, Electronic Shutter Interval Rec `mechanical_curtain_actuations == 0`, Live `.cube` `17^3/33^3/65^3 -> 33^3` Tetrahedral 3D-LUT Uploader, and Wired USB-LAN FTPS queue with `P12` RF-off + eMMC traversal block, [Phase 102](reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md)).

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`125` Local Donor / `125` Clean-Room tests)**
   - **Rounds 1–19 (`r1a..r19e`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, **Round 14 `18/18` (`Big6` / `3-Layer Menu` / `Status Check` × `6 Lang Pairs`)**, **Round 17 complete `10/10` `Status Check` (`0x2f..0x37,0x39`, `C(10,2)=45/45` pairwise pixel-diffs `> 0`, `10`-step wrap-around + Tab 9 `Network` `WF-12` immunity)** ([Round 17](reports/2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio/README.md)), and **Rounds 18–19 complete `11/11` Full-Menu L1 shooting categories (`User`..`Maintenance`, `C(11,2)=55/55` pairwise pixel-diffs `> 0`, `11x DOWN` wrap-around + `ZH-TW` `Network` `WF-12` `00342260` immunity)** ([Round 18](reports/2026-11-14-round18-fx6-on-fx3-menu-8category-closure/README.md), [Round 19](reports/2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep/README.md)).

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`568` Local Donor / `568` Clean-Room tests)**
   - **18-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
     - **Stages 1–13 (`Phases 24–87`)**: BT, Dual-ISA `AArch64` AP ↔ `IVSHMEM` ↔ `ARM32` `cpapp-b.bin`, `Soft-GPE0`, FDT+`MHLX`, `IMX510`/XAVC, HIL, `QMP`/`GDB` (`nop_count=0`), `EDID RAW16`, `SMPTE 12M` PLL/`libpaint`, Dual-Slot `.RSV`, Touch AF/`CIZ`, `CAMSET`/LPCM/UB, and Playback/`ShotMark`/Dew-Point.
     - **Stages 14–18 (`Phases 91, 96, 99, 103, 107`)**: **Stage 14 (Ph91)** Gyroflow `2000Hz` IMU `RTMD`/Anamorphic IBIS ([Phase 91](reports/2026-11-14-phase91-vm-stage14-gyroflow-rtmd-anamorphic-hil/README.md)); **Stage 15 (Ph96)** Interval Rec/Picture Cache/USB-LAN FTP + Sigma fan occlusion ([Phase 96](reports/2026-11-14-phase96-vm-stage15-interval-cache-ftp-hil/README.md)); **Stage 16 (Ph99)** Tetrahedral 3D LUT/Sub-Zero `-20C`/`12G-SDI` ([Phase 99](reports/2026-11-14-phase99-vm-stage16-lut3d-subzero-sdi-hil/README.md)); **Stage 17 (Ph103)** 5GHz/6GHz TX EMI/`>6h` exFAT endurance (`emmc_sector_writes=0`, [Phase 103](reports/2026-11-14-phase103-vm-stage17-emi-exfat-endurance-hil/README.md)); **Stage 18 (Ph107)** C2PA 2.1/E-Mount Shading/MC Multi-Cam Fleet/PL Cantilever & V-Mount OVP (`cnflasha_mutation_bytes=0`, `private_key_exports=0`, [Phase 107](reports/2026-11-14-phase107-vm-stage18-c2pa-shading-mcfleet-hil/README.md)).

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`553` Local Donor / `553` Clean-Room tests)**
   - **20 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**: `#1..#16` (`UFU`/`SDM2`, `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610` sprites, `IMX510`/XAVC, `.cube` + `RTMD`, `WBI2`/ELF64 `.dynsym`, `global.xdb` 128p, Audio/TC/HDMI, AF/IBIS, Shutter/Tally, WB/`OCIO v2`, Proxy/`*M01.XML`, `Custom 1..6`/`CIZ`, False Color/LPCM/UB, Playback/AE) + **`#17 (Ph89)`** Gyroflow/Catalyst `RTMD` ([Wave 9](reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md)) + **`#18 (Ph93)`** Interval/Picture Cache/FTP ([Phase 93](reports/2026-11-14-phase93-interval-cache-ftp-auditor/README.md)) + **`#19 (Ph98)`** Tetrahedral `.cube` + `S-Log3` HDMI/`12G-SDI` ([Phase 98](reports/2026-11-14-phase98-lut3d-tetrahedral-sdi-hdmi-auditor/README.md)) + **`#20 (Ph105)`** `C2PA 2.1` + E-Mount Lens Shading + Monitor & Control Multi-Cam Fleet ([Phase 105](reports/2026-11-14-phase105-c2pa-shading-mc-fleet-auditor/README.md)).

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
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows; `v7.02` `p1` resolved via 4-site AArch64 `ADRP/BL` autolocator; `p1` `FAT12/16` swap audited by Phase 66; Phase 79/94 block `OTP`/`RPMB` rollbacks. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 `7.02` and FX6 `6.01` (`@ 0xFE049000`); Tier-0 protected by `GF(256)` RAID-6 (`Phase 72`); Tier-3 BootROM `48000`-baud recovery uses `RP2040-Zero -DOPEN_DRAIN` (`make verify-rp2040-fixture`) & passive RX-only UART (`tx_bytes = 0`). |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; `p2:/setting/{psd,defdet}.bin`, `p6:Jiritsu`, `p12:/cert` (`C2PA 2.1` `RQ_LIC.DAT`), and `p18:/lens/lensfile.bin` remain hard-locked read-only (`G15`, `Ph105`). |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Phase 106 locks FDT `/chosen/bootargs` `ro` + ARM64 `0x644d5241`; Stage-A & Stage-B keep stock FX3 kernel, stock `p8:/cpapp-b.bin` (`cp_mutation_bytes = 0`), and `p5:/wbi` blocked (`wbi_mutation_bytes = 0`). |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A & Stage-B (`stage_b_init2_guard.sh`) check `FX3_SAFE_STOCK.FLG` first (`< 1s` instant escape), verify `13/13` SHA-256 digests before mount, enforce `32-Gate` + `EXT_CSD[267..269]`/`[173/171]` locks, activate volatile `tmpfs` (`< 48 MiB`), and unwind in reverse LIFO (`H0 == H2`). |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite, 32-Gate, 10-Pillar & Milestone-110 CI
├── Makefile                                 # Unified test, Milestone-110, 32-Gate, 10-Pillar Recovery, Milestone-90, VM & Lab
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 32-Gate (`G01..G32`), 18-Stage VM & 10-Pillar ref
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V XLR, TEC, Fan, Subzero, PL/OVP & <1s SD Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite runner (2,980 Local / 2,922 Clean-Room) + BYOF audit + hygiene check
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # 7 controlled engineering packages (2,980 Local Donor / 2,922 Clean-Room tests)
│   ├── fx3-recovery-adapter/                # 10-Pillar Recovery: Tier-0..4, RP2040, init2, GF(256), OTP/RPMB, UART, GPT, Pre-EOL, FDT (439/381)
│   ├── fx3-safety/                          # 32-Gate Master Preflight G01..G32 (Fan, Tripod, Curtain, -20C, EMI, >6h, PL, Dummy-Batt OVP) (505)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B, Ph52/76 Dossier v3, Ph62/68/83/90, Milestone Phase 110 6-Pillar Master Gate (517)
│   ├── fx3-vm-trial/                        # Live port 8768 Web UI: 128p, Touch AF, False Color, Gyroflow, Picture Cache, .cube, FTPS (273)
│   ├── fx6-native-presenter-closure/        # Rounds 1..19 FX3 7.02 kernel GPE0: nop_count=0, 18/18 + 10/10 Status 45/45 + 11/11 Menu 55/55 (125)
│   ├── fx3-vm/                              # 18-stage Dual-ISA AP<->IVSHMEM<->CP co-emulation through C2PA/Shading/MC Fleet/OVP (568)
│   └── fx3-firmware-lab/                    # 20 unified keyless auditors: UFU..global.xdb, Gyroflow, Cache/FTP, 3D LUT/SDI, C2PA 2.1 (553)
├── reports/                                 # Phases 1..110, Rounds 1..19, Waves 1..11 global intel & verification reports
└── conversations/                           # Categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Unified Test Suite, Clean-Room CI, Milestone-110, 32-Gate, 10-Pillar Recovery, Firmware Lab & Co-Emulation Targets

```bash
# 1. Run all 2,980 Local Donor tests across all 7 suites (439 + 505 + 517 + 273 + 125 + 568 + 553) + BYOF (57+57) + hygiene check
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (2,922 tests across 7 suites, zero Sony firmware blobs — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 110 Master Gate (< 2.5s) + 32-Gate + 10-Pillar Recovery + Phase 90 Gates (BOTH modes)
make verify-milestone-110
make verify-32-gates
make verify-10pillar-recovery
make verify-milestone-90
make verify-24-gates
make verify-tier0-backup
make verify-antirollback-guard
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B Lifecycle Drill, Wireless Guard, Firmware Lab (20 Auditors), 18-Stage Co-Emulation & Stage-A Lifecycle targets
make stage-b-lifecycle-drill
make verify-wireless-guard
make verify-firmware-lab
make verify-coemulation
make readiness-packet
make lifecycle-drill
make dry-run

# 5. Individual Phase & Subsystem Verifiers
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
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Gyroflow / Picture Cache / `.cube` / FTPS Console**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under the MIT license; QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
