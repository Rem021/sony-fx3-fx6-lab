# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![English Standalone](https://img.shields.io/badge/Standalone_EN-README.en.md-0969da?style=flat)](./README.en.md)
[![简体中文独立版](https://img.shields.io/badge/独立中文版-README.zh--CN.md-0969da?style=flat)](./README.zh-CN.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-32--Gate_%7C_EN_%2B_ZH-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-10--Pillar_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-2,980_Local_%7C_2,922_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r19e_(18%2F18_%2B_45%2F45_%2B_55%2F55)-success?style=flat)](#5-outputsfx6-native-presenter-closure-125-tests)
[![Milestone Phase 110](https://img.shields.io/badge/Milestone_Phase_110-Phases_1..110_%7C_Rounds_1..19_%7C_Waves_1..11-1a7f37?style=flat)](#3-outputsfx6-on-fx3-closure-517-tests)

> **Language Navigation / 语言切换**: **[English Documentation](#english-documentation)** · **[简体中文文档](#简体中文文档)** · **[Stage-B Architecture & 32-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** · **[Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)** · **[Standalone `README.en.md`](./README.en.md)** · **[独立中文版 `README.zh-CN.md`](./README.zh-CN.md)**

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> **硬件写入硬锁状态（严禁持久化刷写真机 eMMC / SPI NOR）**  
> Persistent flashing & hardware attach remain **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `hardware_live_attachment_authorized = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), `calibration_mutation_bytes = 0`, `otp_fuse_touches = 0`, `rpmb_counter_increments = 0`, and `passive_tx_bytes_emitted = 0`. All Stage-A/Stage-B overlays target volatile DDR (`tmpfs`) only, read donor blobs strictly via `os.O_RDONLY`, support `< 1s` `FX3_SAFE_STOCK.FLG` zero-cable SD escape, and revert instantaneously to 100% stock Sony ILME-FX3 `Ver. 7.02` upon power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware) / 净室开源合规边界**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` images) and **0 vendor AES/RSA private keys**. Donorless clean-room verification (`2,922` tests across all `7` suites + `Milestone Phase 110 Master Gate`, `32-Gate`, `10-Pillar Recovery`, `Milestone Phase 90`, `24-Gate`, `RP2040`, `init2`, `Tier-0 GF(256)`, `OTP/RPMB Anti-Rollback`, and `Post-Trial` CLI gates) runs cleanly via `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` and [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded by `make verify-byof`, `57+57` SHA-256 entries + `46` code constants).

---

# English Documentation

## 1. Executive Summary (`Phases 1–110` · `Rounds 1–19` · `Waves 1–11`)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, cross-model firmware compatibility, and anti-brick safety laboratory targeting the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)**, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

Across **`Phases 1–110`**, **`Rounds 1–19`**, and **`Global Intel Waves 1–11`**, the lab integrates **7 unified verification suites (`2,980` Local Donor / `2,922` Clean-Room passing tests via `make test`)** and the **Milestone Phase 110 Six-Pillar Master Gate (`make verify-milestone-110`, `< 2.5s`)**:
- **Stage-B Volatile RAM-Overlay (`P1..P12 + Fan`, `13/13` Verify-Before-Mount)** with FX3 physical button remap (`P10`), AP-side UIPC-CP shim (`P11`, preserving `XLR-H1` & 5-axis IBIS center-lock), `WF-12` bootloop immunity (`P12`), `< 48 MiB` SVR4 `070701` CPIO packaging, Phase 52/76 Candidate Integrator & Release Dossier v3, Phase 62/68/83 `16`-surface `H0 == H2` Post-Trial Forensic & Capstone Auditor, Phase 90 24-Gate Master Gate, and **Milestone Phase 110 6-Pillar Century+10 Master Gate** ([Phase 110 Report](reports/2026-11-14-phase110-milestone-master-gate-and-docs-sync/README.md)).
- **32-Gate Master Preflight (`G01..G32`) & 10-Pillar Recovery Master Suite (`Phases 47..106`)**: Protects Sony **C2PA 2.1** (`RQ_LIC.DAT`, `sigcert.p12`, `cnflasha`), factory shading/calibration, `exFAT` `BootChecksum`/6h+ clip-spanning (`G17`, `G30`), wired `USB-LAN CDC-NCM` / `PTP-IP 15740` + FTPS + `P12` Airplane coexistence (`G18`), D-Tap/HDMI ESD & E-Mount `2.0ms` `V_LENS` crowbar (`G19`, `G29`), `NP-FZ100 >= 15%` UPS reserve (`G20`), `+48V` XLR phantom burnout (`G21`), gimbal/focus `<= 0.35 N*m` (`G22`), Magnus dew-point `TEC` (`G23`), PMIC `5V 900 mA` (`G24`), **Sigma fan intake occlusion & `1/4-20` tripod/housing vacuum (`G25`, `G26`)**, **`IMX510` laser/curtain-at-power-off & `-20C`/high-altitude derating (`G27`, `G28`)**, **5GHz/6GHz wireless TX EMI & `>6h` CFexpress zero-NVRAM-churn (`G29`, `G30`)**, **heavy PL-to-E cantilever `15mm` LWS & 14.8V/26V V-Mount dummy-battery `>8.4V` OVP blowout firewall (`G31`, `G32`)**, plus **`10` unified recovery pillars** (`RP2040`, `<1s` `FX3_SAFE_STOCK.FLG`, `GF(256)` RAID-6, `OTP/RPMB`, passive `1.8V` RX-only UART `S0..S6`, `CXD90057` GPT/RPMB replay, SVR4 cpio/JEDEC `EXT_CSD [267..269]` Pre-EOL, and FDT `/chosen/bootargs` `ro` + ARM64 Kernel `Image`).
- **Live Port `8768` Multilingual QEMU Console (`FX6菜单.command`), `18-Stage` Co-Emulation (`fx3-vm`), `20` Unified `fx3-firmware-lab` Auditors & `Rounds 1–19` (`18/18` + `10/10` Status Tabs `45/45` + `11/11` Full-Menu `55/55` at `nop_count = 0`)**: Adds **Phase 95** Anamorphic (`1.33x..2.0x`) IBIS Asymmetric/Center-Lock, Gyroflow `2000Hz` RTMD, and `1kHz -20dBFS` tone / 4-Ch `-3.0 dBFS` limiter plus **Phase 102** Picture Cache (`<=384 MiB` DDR ring-buffer), Electronic Shutter Interval Recording (`mechanical_curtain_actuations == 0`), `.cube` (`17^3/33^3/65^3 -> 33^3` Tetrahedral) Live Uploader, and Wired USB-LAN FTPS background queue (`P12` RF-off enforced) on top of Touch AF, `x4` Focus Magnify, `S-Log3` False Color/`EL-Zone`, `CIZ`, Cine EI, `CAMSET` & `M01.XML` export, alongside `18-Stage` VM co-emulation and `20` keyless auditors.

For complete architectural & field manuals, see **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** and **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**.

---

## 2. The 7 Unified Verification Suites (`make test` — `2,980` Local Donor / `2,922` Clean-Room)

Running `make test` executes all **7 suites (`2,980` Local Donor / `2,922` Clean-Room)**, the bilingual `docs/BYOF-REPRODUCTION.md` manifest audit (`57+57` entries, `46` constants), and the `git status --porcelain` zero-binary/zero-`.pyc` hygiene sweep:

### 1. [`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`439` Local Donor / `381` Clean-Room tests)
- **10-Pillar Recovery Master Suite (`make verify-10pillar-recovery`)**: Composes Phases `47..88` (Tier-0..4 ladder, macOS 26 `IOUSBHost`, `RP2040-Zero -DOPEN_DRAIN` `make verify-rp2040-fixture`, `<1s` `FX3_SAFE_STOCK.FLG` `init2` escape + WDT `make verify-init2-escape`, `GF(256)` RAID-6 Tier-0 healer `make verify-tier0-backup`, `OTP/RPMB` anti-rollback `make verify-antirollback-guard`, and passive `1.8V` RX-only UART `S0..S6` decoder with `passive_tx_bytes_emitted == 0`) plus **Pillar 8 (Ph94)** GPT CRC32/RPMB HMAC-SHA256 replay & SD rescue bundle, **Pillar 9 (Ph101)** SVR4 `newc` cpio firewall & `EXT_CSD[267..269]` Pre-EOL health, and **Pillar 10 (Ph106)** FDT `0xd00dfeed` `/chosen/bootargs` `ro` & ARM64 `0x644d5241` Kernel `Image` cross-SKU firewall.

### 2. [`outputs/fx3-safety/`](outputs/fx3-safety/) (`505` Local Donor / `505` Clean-Room tests)
- **32-Gate Master Safety Preflight Engine (`G01..G32`, `make verify-32-gates`)**: Extends `G01..G24` (`make verify-24-gates`, including C2PA, `exFAT`, `USB-LAN`, D-Tap/HDMI `V_LENS` crowbar, `NP-FZ100 >= 15%` UPS, `+48V` XLR, gimbal torque, Magnus dew-point `TEC`, PMIC `5V 900 mA`) with **Phase 92** (`G25` Sigma intake/exhaust occlusion & rain blimp, `G26` `1/4-20` tripod screw `<=5.5mm` & housing vacuum), **Phase 97** (`G27` IMX510 laser/curtain-at-power-off/IBIS transport lock, `G28` `-20C` Li-Ion ESR & `>3000m` altitude derating), **Phase 100** (`G29` 5GHz/6GHz TX near-field EMI & ESD, `G30` `>6h` exFAT clip-spanning & CFexpress zero-NVRAM-churn), and **Phase 104** [`pl_cantilever_dummybatt_and_32gate_guard.py`](outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py) (`G31` heavy PL-to-E cantilever `15mm` LWS lens support & `G32` 14.8V/26V V-Mount dummy-battery `>8.4V` OVP crowbar — `29/32` offline truthful block vs `32/32` simulated rehearsal).

### 3. [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`517` Local Donor / `517` Clean-Room tests)
- **Milestone Phase 110 6-Pillar Century+10 Master Gate ([`stage_b_milestone110_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone110_master_gate.py), `make verify-milestone-110`, `< 2.5s`)**: Unifies all 6 Milestone-110 pillars (`32-Gate`, `10-Pillar Recovery`, `>= 20` Firmware-Lab Auditors, `>= 18` VM Stages, `Round 14 (18/18)` + `Round 17 (10/10 Status 45/45)` + `Round 19 (11/11 Menu 55/55)` real FX3 `7.02` closures, and `H0 == H2` 16-surface immutability + hardware lock invariants) with deterministic `milestone110_sha256` ([Phase 110 Report](reports/2026-11-14-phase110-milestone-master-gate-and-docs-sync/README.md)) while keeping [`stage_b_milestone90_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone90_master_gate.py) (`make verify-milestone-90`) and Stage-A/B (`P1..P12+Fan`, `13/13` lock-table, `U1..U5`, `Dossier v3`, `H0==H2` `make verify-post-trial-audit`) 100% intact.

### 4. [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`273` Local Donor / `273` Clean-Room tests)
- **Live QEMU ARM64 `1024×540` `GPE0` Web Console on port `8768`** ([`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command), [`FX3菜单.command`](outputs/fx3-vm-trial/FX3菜单.command)):
  - Native `LDEC103` icons (`60/60` `0 SEGV`), 128-page 4-language pool (`简体中文 / 繁體中文 / EN / 日本語`), `P10` button deck, 4-Ch `XLR-H1` VU, **Phase 56/64/73/81** (Scopes, Cine EI `800/12800`, Shutter Angle/`S&Q 1–240fps`, Shockless WB/Base Look/`*M01.XML`, 627-pt `Touch AF`, `x4` Focus Magnify, `S-Log3` False Color/`EL-Zone`, `CIZ`, `CAMSET` round-trip), **Phase 95** (`1.33x..2.0x` Anamorphic IBIS Asymmetric/Center-Lock, Gyroflow `2000Hz` RTMD HUD, `1kHz -20dBFS` tone + 4-Ch `-3.0 dBFS` limiter, [Phase 95](reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md)), and **Phase 102** (Picture Cache `<=384 MiB` DDR ring-buffer, Electronic Shutter Interval Rec `mechanical_curtain_actuations == 0`, Live `.cube` `17^3/33^3/65^3 -> 33^3` Tetrahedral 3D-LUT Uploader, and Wired USB-LAN FTPS queue with `P12` RF-off + eMMC traversal block, [Phase 102](reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md)).

### 5. [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`125` Local Donor / `125` Clean-Room tests)
- **Rounds 1–19 (`r1a..r19e`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, **Round 14 `18/18` (`Big6` / `3-Layer Menu` / `Status Check` × `6 Lang Pairs`)**, **Round 17 complete `10/10` `Status Check` (`0x2f..0x37,0x39`, `C(10,2)=45/45` pairwise pixel-diffs `> 0`, `10`-step wrap-around + Tab 9 `Network` `WF-12` immunity)** ([Round 17](reports/2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio/README.md)), and **Rounds 18–19 complete `11/11` Full-Menu L1 categories (`User`..`Maintenance`, `C(11,2)=55/55` pairwise pixel-diffs `> 0`, `11x DOWN` wrap-around + `ZH-TW` `Network` `WF-12` `00342260` immunity)** ([Round 18](reports/2026-11-14-round18-fx6-on-fx3-menu-8category-closure/README.md), [Round 19](reports/2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep/README.md)).

### 6. [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`568` Local Donor / `568` Clean-Room tests)
- **18-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
  - **Stages 1–13 (`Phases 24–87`)**: BT, Dual-ISA `AArch64` AP ↔ `IVSHMEM` ↔ `ARM32` `cpapp-b.bin`, `Soft-GPE0`, FDT+`MHLX`, `IMX510`/XAVC, HIL, `QMP`/`GDB` (`nop_count=0`), `EDID RAW16`, `SMPTE 12M` PLL/`libpaint`, Dual-Slot `.RSV`, Touch AF/`CIZ`, `CAMSET`/LPCM/UB, and Playback/`ShotMark`/Dew-Point.
  - **Stages 14–18 (`Phases 91, 96, 99, 103, 107`)**: **Stage 14 (Ph91)** Gyroflow `2000Hz` IMU `RTMD`/Anamorphic IBIS ([Phase 91](reports/2026-11-14-phase91-vm-stage14-gyroflow-rtmd-anamorphic-hil/README.md)); **Stage 15 (Ph96)** Interval Rec/Picture Cache/USB-LAN FTP + Sigma fan occlusion ([Phase 96](reports/2026-11-14-phase96-vm-stage15-interval-cache-ftp-hil/README.md)); **Stage 16 (Ph99)** Tetrahedral 3D LUT/Sub-Zero `-20C`/`12G-SDI` ([Phase 99](reports/2026-11-14-phase99-vm-stage16-lut3d-subzero-sdi-hil/README.md)); **Stage 17 (Ph103)** 5GHz/6GHz TX EMI/`>6h` exFAT endurance (`emmc_sector_writes=0`, [Phase 103](reports/2026-11-14-phase103-vm-stage17-emi-exfat-endurance-hil/README.md)); **Stage 18 (Ph107)** C2PA 2.1/E-Mount Shading/MC Multi-Cam Fleet/PL Cantilever & V-Mount OVP (`cnflasha_mutation_bytes=0`, `private_key_exports=0`, [Phase 107](reports/2026-11-14-phase107-vm-stage18-c2pa-shading-mcfleet-hil/README.md)).

### 7. [`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`553` Local Donor / `553` Clean-Room tests)
- **20 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**:
  - `#1..#16`: `UFU`/`SDM2`, `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610` sprites, `IMX510`/XAVC, `.cube` + `RTMD`, `WBI2`/ELF64 `.dynsym`, `global.xdb` 128p, Audio/TC/HDMI (`#9`), E-Mount AF (`#10`), Shutter/Tally (`#11`), WB/`OCIO v2` (`#12`), Proxy/`*M01.XML` (`#13`), `Custom 1..6`/`CIZ` (`#14`), False Color/`24-bit` LPCM/UB (`#15`), Playback/`ShotMark`/`Push Auto Iris` (`#16`).
  - **`#17 (Ph89)`** `metadata_gyro_catalyst_and_anamorphic_audit` ([Wave 9](reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md)) · **`#18 (Ph93)`** `interval_cache_and_ftp_audit` ([Phase 93](reports/2026-11-14-phase93-interval-cache-ftp-auditor/README.md)) · **`#19 (Ph98)`** `lut3d_cube_tetrahedral_and_sdi_hdmi_audit` ([Phase 98](reports/2026-11-14-phase98-lut3d-tetrahedral-sdi-hdmi-auditor/README.md)) · **`#20 (Ph105)`** `c2pa_lens_shading_and_mc_fleet_audit` (`C2PA 2.1`, E-Mount shading/CA/distortion, wired Monitor & Control fleet, [Phase 105](reports/2026-11-14-phase105-c2pa-shading-mc-fleet-auditor/README.md)).

---

## 3. Five-Stage Hardware Boot Pipeline & Directory Layout

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/boot-pipeline-en-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/boot-pipeline-en-light.svg">
    <img alt="Five-Stage Secure Boot Pipeline" src="./assets/boot-pipeline-en-light.svg" width="100%">
  </picture>
</p>

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite, 32-Gate, 10-Pillar & Milestone-110 CI
├── Makefile                                 # Unified test, Milestone-110, 32-Gate, 10-Pillar Recovery, Milestone-90, VM & Lab
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 32-Gate (`G01..G32`), 18-Stage VM & 10-Pillar guide
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V XLR, TEC, Fan Occlusion, Subzero, PL/OVP & <1s Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite test runner (2,980 Local / 2,922 Clean-Room) + BYOF + hygiene audit
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
└── conversations/                           # Categorized multi-agent engineering archives across 5 thematic workspaces
```

---

## 4. Quick Start & Verification

```bash
# 1. Run all 2,980 Local Donor tests across all 7 suites + BYOF manifest audit (57+57) + clean-room hygiene
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (2,922 tests across 7 suites, zero Sony firmware blobs — matches clean-room-ci.yml)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 110 6-Pillar Master Gate (< 2.5s) + 32-Gate Safety + 10-Pillar Recovery + Phase 90 Gates (BOTH modes)
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

**Launch Interactive Web Console (Requires BYOF Setup per `docs/BYOF-REPRODUCTION.md`)**:
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Gyroflow / Picture Cache / `.cube` / FTPS Console**: `./outputs/fx3-vm-trial/FX6菜单.command` -> `http://127.0.0.1:8768/`
- **FX3 Native Menu Web Console**: `./outputs/fx3-vm-trial/FX3菜单.command` (`--check` validates SHA-256 inputs without starting QEMU)

---
---

# 简体中文文档

## 一、项目总览（`Phases 1–110` · `Rounds 1–19` · `Waves 1–11`）

**`sony-fx3-fx6-lab`** 围绕 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 开展净室系统工程、多架构 QEMU 协同仿真、跨机型固件兼容适配与真机防变砖安全研究。两款机型均基于 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

历经 **`Phases 1–110`**、**`Rounds 1–19`** 与 **`Waves 1–11` 全球公开情报同步** 迭代，实验室已构建起 **7 大统一自动化验证套件（`make test` 本地供体全量 `2,980` 项通过 / `FX3_FX6_FORCE_CLEAN_ROOM=1` 无供体洁净室 `2,922` 项全绿通过）** 与 **Milestone Phase 110 六柱一体化总闸（`make verify-milestone-110`，`< 2.5s`）**：
- **Stage-B 易失性 RAM 覆盖层（`P1..P12+Fan`，`13/13` 挂载前校验）**：涵盖 `P10` FX3 实体按键映射、`P11` AP 侧 UIPC-CP 垫片（保留 `XLR-H1` 热靴音频与 5 轴 IBIS 居中锁止）、`P12` `WF-12` 无线断环补丁、`< 48 MiB` SVR4 `070701` CPIO 打包器、Phase 52/76 集成与发布简报 v3、Phase 62/68/83 `16` 表面 `H0 == H2` 试后法证审计、Phase 90 六柱总闸，以及 **Milestone Phase 110 百十纪念六柱总闸**（[Phase 110 报告](reports/2026-11-14-phase110-milestone-master-gate-and-docs-sync/README.md)）。
- **32 门禁主安全预检引擎（`G01..G32`）与 10 支柱救砖恢复主套件（`Phases 47..106`）**：刚性锁定 **C2PA 2.1**（`RQ_LIC.DAT`/`sigcert.p12`/`cnflasha`）与出厂光学/传感器校准、`exFAT` 与 `6h+` 分片（`G17`, `G30`）、有线 `USB-LAN CDC-NCM` + `PTP-IP 15740` + FTPS + `P12` 飞行共存（`G18`）、D-Tap/HDMI 隔离与 E 卡口 `<= 2.0ms` `V_LENS` 断流（`G19`）、`NP-FZ100 >= 15%` UPS（`G20`）、`+48V` XLR 防烧毁（`G21`）、稳定器 `<= 0.35 N·m`（`G22`）、Magnus 露点 `TEC`（`G23`）、PMIC `5V 900 mA`（`G24`）、**外挂风扇进排气遮挡与 `1/4-20` 三脚架/防水壳真空门禁（`G25`, `G26`）**、**`IMX510` 激光/关机快门帘与 `-20°C` 高原降额门禁（`G27`, `G28`）**、**5GHz/6GHz 图传近场 EMI 与连续长录零 NVRAM 磨损门禁（`G29`, `G30`）**、**重型 PL 转 E 悬臂 `15mm` 导管支撑与 14.8V/26V 假电池 `>8.4V` OVP 爆管熔断防火墙（`G31`, `G32`）**；并集成 **10 大救砖恢复支柱**（含被动只收 `1.8V` 串口解码 `S0..S6`、`CXD90057` GPT/RPMB 重放防火墙、SVR4 cpio/eMMC 5.1 `EXT_CSD[267..269]` 寿命审计及 FDT `/chosen/bootargs` `ro` + ARM64 内核 `Image` 防跨机互刷防火墙）。
- **端口 `8768` 实时交互式 QEMU 控制台（`FX6菜单.command`）、18 阶段全板协同仿真（`fx3-vm`）、20 大无密钥固件审计器（`fx3-firmware-lab`）与 `Rounds 1–19`（`18/18` + 10 标签 `Status Check` `45/45` + 11 类别全菜单 `55/55` 闭环，`nop_count = 0`）**：在 Touch AF、`x4` 放大、`S-Log3` 伪色/`EL-Zone`、`CIZ`、Cine EI、`CAMSET` 与 `M01.XML` 基础上，新增 **Phase 95** 变形镜头（`1.33x..2.0x`）非对称/居中锁 IBIS 仲裁、Gyroflow `2000Hz` RTMD 遥测、`1kHz -20dBFS` 测试音/4-Ch 限幅器，以及 **Phase 102** 预录制 Picture Cache（`<=384 MiB` DDR 环缓）、电子快门间隔摄影（`mechanical_curtain_actuations = 0`）、`.cube`（`17³/33³/65³ -> 33³` 四面体）实时上传与有线 USB-LAN FTPS 后台队列（强制 `P12` 射频关闭）。

架构细节与现场操作规范请参见 **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** 与 **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**。

---

## 二、七大统一测试套件明细（`make test` — 本地供体 `2,980` 项 / 洁净室 `2,922` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `439` / 洁净室 `381` 项测试）**：**10 支柱救砖恢复主套件（`make verify-10pillar-recovery`）**——集成 Phase `47..88`（`Tier-0..Tier-4`、`macOS 26 IOUSBHost`、**Phase 59** `RP2040-Zero -DOPEN_DRAIN` 自检 `make verify-rp2040-fixture`、**Phase 66** `<1s` `FX3_SAFE_STOCK.FLG` `init2` 逃生 `make verify-init2-escape`、**Phase 72** `GF(256)` RAID-6 自愈 `make verify-tier0-backup`、**Phase 79** `OTP/RPMB` 防回滚 `make verify-antirollback-guard` 及被动只收 `1.8V` UART `S0..S6` `passive_tx_bytes_emitted=0`）+ **支柱 8（Ph94）** GPT CRC32 修复与 RPMB HMAC-SHA256 重放锁 + 双人 SD 救援包 + **支柱 9（Ph101）** SVR4 `newc` cpio 防火墙与 `EXT_CSD[267..269]` Pre-EOL 健康审计 + **支柱 10（Ph106）** FDT `0xd00dfeed` `/chosen/bootargs` `ro` 与 ARM64 内核 `Image` 防跨机校验。
2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `505` 项测试）**：**`G01..G32` 32 门禁主安全预检引擎（`make verify-32-gates`）**在 `G01..G24`（`make verify-24-gates`）基础上扩展 **Phase 92**（`G25` 风扇进排气遮挡与防雨罩背压、`G26` 三脚架 `1/4-20` 螺孔深度与防水壳真空）、**Phase 97**（`G27` IMX510 激光/关机快门帘/IBIS 运输锁、`G28` `-20°C` 低温电池内阻与高海拔散热降额）、**Phase 100**（`G29` 5GHz/6GHz 图传近场 EMI 与热插拔 ESD、`G30` `>6h` exFAT 分片与 CFexpress 零 NVRAM 磨损），以及 **Phase 104** [`pl_cantilever_dummybatt_and_32gate_guard.py`](outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py)（`G31` 重型 PL 转 E 悬臂 `15mm` 导管支撑与 `G32` 14.8V/26V 假电池 `>8.4V` 过压爆管拦截）。
3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `517` 项测试）**：**Milestone Phase 110 六柱一体化总闸（[`stage_b_milestone110_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone110_master_gate.py)，`make verify-milestone-110`，`< 2.5s`）** 汇聚 `32-Gate`、`10-Pillar Recovery`、`>= 20` 固件审计器、`>= 18` VM 阶段、`Round 14/17/19` 真内核闭环与 `H0 == H2` 16 表面不可变性，并保留 `verify-milestone-90` 与 Stage-A/B（`P1..P12+Fan` `13/13` 补丁、`U1..U5`、`Dossier v3`、`H0==H2` `make verify-post-trial-audit`）。
4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `273` 项测试）**：端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)），在 `LDEC103` `60/60` 零崩溃、128 页四语池、示波器、Cine EI、Touch AF/`x4`、`S-Log3` 伪色/`CIZ`、`CAMSET`/`M01.XML` 之上新增 **Phase 95** 变形镜头 IBIS 仲裁/Gyroflow `2000Hz` RTMD/`1kHz -20dBFS` 基准音（[Phase 95 报告](reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md)）与 **Phase 102** 预录制 Picture Cache（`<=384 MiB`）、电子快门间隔摄影、`.cube -> 33³` 四面体实时上传及有线 USB-LAN FTPS 后台队列（[Phase 102 报告](reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md)）。
5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `125` 项测试）**：**Rounds 1–19（`r1a..r19e`）** FX3 `7.02` 原厂 `4.9.337-scel+` 内核混合态真机实跑（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）：完成 **Round 14 四语×三界面 `18/18`**、**Round 17 `Status Check` 完整 `10/10` 标签（`0x2f..0x37,0x39`，$\binom{10}{2}=45/45$ 严正差分 + `10` 步环绕 + Tab 9 `WF-12` 免疫）**（[Round 17](reports/2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio/README.md)），以及 **Rounds 18–19 完整 `11/11` 全功能菜单类别（$\binom{11}{2}=55/55$ 严正差分 + `11x DOWN` 环绕 + 繁中 `Network` `WF-12` 免疫）**（[Round 18](reports/2026-11-14-round18-fx6-on-fx3-menu-8category-closure/README.md)、[Round 19](reports/2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep/README.md)）。
6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `568` 项测试）**：**18 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**，覆盖 Stages 1–13 至 **Stage 14（Ph91）** Gyroflow `2000Hz` IMU/变形防抖、**Stage 15（Ph96）** 间隔录制/Picture Cache/FTP/风扇遮挡、**Stage 16（Ph99）** 四面体 3D LUT/`-20°C`/`12G-SDI`、**Stage 17（Ph103）** 5GHz/6GHz 图传 EMI/`>6h` exFAT 耐久，以及 **Stage 18（Ph107）** `C2PA 2.1`/镜头阴影/Monitor & Control 车队/PL 悬臂与假电池 OVP（`cnflasha_mutation_bytes=0`, `private_key_exports=0`）。
7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `553` 项测试）**：**20 大洁净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**，在 `#1..#16` 之上新增 **`#17（Ph89）`** Gyroflow/Catalyst `RTMD`（[Wave 9](reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md)）、**`#18（Ph93）`** 间隔录制/Picture Cache/有线 FTP（[Phase 93](reports/2026-11-14-phase93-interval-cache-ftp-auditor/README.md)）、**`#19（Ph98）`** `.cube` `17³/33³/65³` 四面体 LUT 与 `12G-SDI` 触发（[Phase 98](reports/2026-11-14-phase98-lut3d-tetrahedral-sdi-hdmi-auditor/README.md)），以及 **`#20（Ph105）`** `C2PA 2.1`/`cnflasha`、E 卡口光学阴影补偿与有线多机车队审计（[Phase 105](reports/2026-11-14-phase105-c2pa-shading-mc-fleet-auditor/README.md)）。

---

## 三、硬件安全引导边界与快速验收命令

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/boot-pipeline-zh-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/boot-pipeline-zh-light.svg">
    <img alt="五阶段安全引导流水线" src="./assets/boot-pipeline-zh-light.svg" width="100%">
  </picture>
</p>

```bash
# 1. 运行全部 7 套 2,980 项本地供体测试 + BYOF 双语清单审计 (57+57) + git 净室零残留审计
make test
make test-json

# 2. 本地模拟无供体洁净室 CI (7 套 2,922 项测试，零索尼固件依赖，与 GitHub Actions 完全一致)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 110 六柱总闸 (<2.5s) + 32 门禁、10 支柱救砖与 Phase 90 兼容总闸（双模式通用）
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

# 4. Stage-B 生命周期演练、无线防护、固件实验室（20 审计器）、18 阶段协同仿真与 Stage-A 演练命令
make stage-b-lifecycle-drill
make verify-wireless-guard
make verify-firmware-lab
make verify-coemulation
make readiness-packet
make lifecycle-drill
make dry-run

# 5. 其余各阶段专项校验与卫生检查
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

**自备 BYOF 固件启动交互式控制台（见 [`docs/BYOF-REPRODUCTION.md`](docs/BYOF-REPRODUCTION.md)）**：
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / Gyroflow / 预录制 / `.cube` / FTPS 控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入 SHA-256）。

---

## 四、多智能体归档与开源协议 (Archives & License)

- **工程对话归档**：5 大专题工作区多智能体研究对话已按净室规范分类归档至 **[conversations/README.md](conversations/README.md)**。
- **免责与开源协议**：本仓库包含 **0 字节** 索尼专有二进制固件或私有密钥，与 Sony Group Corporation 无任何隶属或合作关系。自研源码采用 MIT 协议，QEMU 补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
