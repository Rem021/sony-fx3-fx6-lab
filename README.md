# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![English Standalone](https://img.shields.io/badge/Standalone_EN-README.en.md-0969da?style=flat)](./README.en.md)
[![简体中文独立版](https://img.shields.io/badge/独立中文版-README.zh--CN.md-0969da?style=flat)](./README.zh-CN.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-24--Gate_%7C_EN_%2B_ZH-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-Tier--0..4_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-2,191_Local_%7C_2,133_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r16d_(18%2F18_%2B_10%2F10)-success?style=flat)](#5-outputsfx6-native-presenter-closure-83-tests)
[![Milestone Phase 90](https://img.shields.io/badge/Milestone_Phase_90-Phases_1..90_%7C_Rounds_1..16_%7C_Waves_1..8-1a7f37?style=flat)](#3-outputsfx6-on-fx3-closure-477-tests)

> **Language Navigation / 语言切换**: **[English Documentation](#english-documentation)** · **[简体中文文档](#简体中文文档)** · **[Stage-B Architecture & 24-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** · **[Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)** · **[Standalone `README.en.md`](./README.en.md)** · **[独立中文版 `README.zh-CN.md`](./README.zh-CN.md)**

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> **硬件写入硬锁状态（严禁持久化刷写真机 eMMC / SPI NOR）**  
> Persistent flashing & hardware attach remain **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `hardware_live_attachment_authorized = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), `calibration_mutation_bytes = 0`, `otp_fuse_touches = 0`, and `rpmb_counter_increments = 0`. All Stage-A/Stage-B overlays target volatile DDR (`tmpfs`) only, read donor blobs strictly via `os.O_RDONLY`, support `< 1s` `FX3_SAFE_STOCK.FLG` zero-cable SD escape, and revert instantaneously to 100% stock Sony ILME-FX3 `Ver. 7.02` upon power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware) / 净室开源合规边界**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` images) and **0 vendor AES/RSA private keys**. Donorless clean-room verification (`2,133` tests across all `7` suites + `Milestone Phase 90 Master Gate`, `24-Gate`, `20-Gate`, `RP2040`, `init2`, `Tier-0 GF(256)`, `OTP/RPMB Anti-Rollback`, and `Post-Trial` CLI gates) runs cleanly via `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` and [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded by `make verify-byof`, `57+57` SHA-256 entries + `46` code constants).

---

# English Documentation

## 1. Executive Summary (`Phases 1–90` · `Rounds 1–16` · `Waves 1–8`)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, cross-model firmware compatibility, and anti-brick safety laboratory targeting the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)**, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

Across **`Phases 1–90`**, **`Rounds 1–16`**, and **`Global Intel Waves 1–8`**, the lab integrates **7 unified verification suites (`2,191` Local Donor / `2,133` Clean-Room passing tests via `make test`)** and the **Phase 90 Six-Pillar Master Gate (`make verify-milestone-90`, `< 2s`)**:
- **Stage-B Volatile RAM-Overlay (`P1..P12 + Fan`, `13/13` Verify-Before-Mount)** with FX3 physical button remap (`P10`), AP-side UIPC-CP shim (`P11`, preserving `XLR-H1` & 5-axis IBIS center-lock), `WF-12` bootloop immunity (`P12`), `< 48 MiB` SVR4 `070701` CPIO packaging, Phase 52/76 Candidate Integrator & Release Dossier v3, Phase 62/68/83 `16`-surface `H0 == H2` Post-Trial Forensic & Capstone Auditor, and **Phase 90 Unified 6-Pillar Master Gate** ([Phase 90 Report](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)).
- **24-Gate Master Preflight (`G01..G24`) & Tier-0..Tier-4 Unbrick Ladder (`S01..S12`)**: Protects Sony **C2PA** (`RQ_LIC.DAT`, `sigcert.p12`), factory calibration, `exFAT` `BootChecksum`/client media (`G17`), wired `USB-LAN CDC-NCM` / `PTP-IP 15740` + `P12` Airplane coexistence (`G18`), D-Tap/HDMI ground-loop + E-Mount `2.0ms` `V_LENS` crowbar (`G19`), `NP-FZ100 >= 15%` UPS reserve + `.RSV` salvage (`G20`), **`+48V` XLR phantom burnout (`G21`)**, **gimbal/focus torque `<= 0.35 N*m` & shutter guard (`G22`)**, **Magnus dew-point `TEC` condensation block (`G23`)**, **PMIC `5V` `900 mA` accessory budget guard (`G24`)**, `RP2040-Zero -DOPEN_DRAIN` bench self-test (`Phase 59`), `< 1s` `FX3_SAFE_STOCK.FLG` `init2` escape (`Phase 66`), **`GF(256)` RAID-6 Tier-0 healer (`Phase 72`)**, and **`CXD90057` OTP/RPMB zero-touch anti-rollback + `EXT_CSD[173/171]` trap blocker (`Phase 79`)**.
- **Live Port `8768` Multilingual QEMU Console (`FX6菜单.command`), 13-Stage Co-Emulation (`fx3-vm`), 16 Unified `fx3-firmware-lab` Auditors & `Rounds 1–16` (`18/18` + `10/10` Status Tabs `0x2f..0x33` at `nop_count = 0`)**: Interactive Dual Base `800/12800` Cine EI, IRE Waveform/RGB Histogram, **627-pt Touch AF (`GPE0 TAFC`)**, **`x4` Focus Magnify (Clean HDMI)**, **`S-Log3` `41%/94% IRE` False Color & `EL-Zone`**, **`CIZ` (`1.5x/2.0x`)**, **`Shockless WB`/`Base Look`/`*M01.XML`**, **`CAMSET` round-trip**, **`ShotMark1/2` `<EssenceMark>`**, **`Push Auto Iris`**, `13-Stage` heterogeneous VM (`cp_mutation_bytes = 0`), and `16` keyless auditors.

For complete architectural & field manuals, see **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** and **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**.

---

## 2. The 7 Unified Verification Suites (`make test` — `2,191` Local Donor / `2,133` Clean-Room)

Running `make test` executes all **7 suites (`2,191` Local Donor / `2,133` Clean-Room)**, the bilingual `docs/BYOF-REPRODUCTION.md` manifest audit (`57+57` entries, `46` constants), and the `git status --porcelain` zero-binary/zero-`.pyc` hygiene sweep:

### 1. [`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`297` Local Donor / `239` Clean-Room tests)
- **Phase 79 `CXD90057` OTP/RPMB Anti-Rollback & `EXT_CSD[173/171]` Guard** ([Phase 79 Report](reports/2026-11-14-phase79-antirollback-otp-rpmb-epoch-guard/README.md), `make verify-antirollback-guard`) enforcing `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, and permanent eMMC WP fuse trap blocking.
- **Phase 72 `GF(256)` (`0x11d`) RAID-6 Tier-0 Backup Vault & Cross-Unit Guard** ([Phase 72 Report](reports/2026-11-14-phase72-tier0-backup-gf256-parity-guard/README.md), `make verify-tier0-backup`) proving 2-shard bit-rot self-healing across `11` read-only partitions with SHA-256 body binding (`c65670ea25a2c28e`).
- **Phase 66 `init2` SD-Sentinel (`FX3_SAFE_STOCK.FLG` `< 1s`), `CXD90057` WDT `10,000ms` & `p1` `FAT12/16`** ([Phase 66 Report](reports/2026-11-14-phase66-init2-escape-watchdog-fat-verifier/README.md), `make verify-init2-escape`), **Phase 59 `RP2040-Zero -DOPEN_DRAIN` Bench Self-Test** ([Phase 59 Report](reports/2026-11-14-phase59-rp2040-multiport-fixture-selftest/README.md), `make verify-rp2040-fixture`), `Tier-0..Tier-4` ladder (`S01..S12`), `p1` VFAT capsule, shifted-VMA `v7.02` `p1` autolocator, macOS 26 `IOUSBHost`, and `O_RDONLY` eMMC ISP.

### 2. [`outputs/fx3-safety/`](outputs/fx3-safety/) (`360` Local Donor / `360` Clean-Room tests)
- **24-Gate Master Safety Preflight Engine (`G01..G24`, `make verify-24-gates`)** composing `G01..G16` + **Phase 57/61** (`G17` exFAT/client media firewall, `G18` wired `USB-LAN CDC-NCM` + `PTP-IP 15740`) + **Phase 69** (`G19` D-Tap/HDMI ground-loop & `<= 2.0ms` `V_LENS` crowbar + IBIS park, `G20` `NP-FZ100 >= 15%` UPS & `.RSV` salvage) + **Phase 77** [`phantom48v_gimbal_and_22gate_guard.py`](outputs/fx3-safety/fx3_safety/phantom48v_gimbal_and_22gate_guard.py) (`G21` `+48V` XLR phantom burnout guard, `G22` gimbal/focus torque `<= 0.35 N*m` & shutter protection) + **Phase 84** [`dewpoint_tec_usbc_and_24gate_guard.py`](outputs/fx3-safety/fx3_safety/dewpoint_tec_usbc_and_24gate_guard.py) (`G23` Magnus dew-point `TEC` condensation block & `G24` PMIC `5V` `900 mA` accessory power budget guard — `21/24` offline truthful block vs `24/24` simulated rehearsal).
- **6-Stage `H0` Rehearsal (`--unicorn`), `serial_fault_detector_v2`, `RP2040-Zero` & `VMC-BNCM1` LTC, `CrSDK` PTP2, `XLR-H1`, `SPACC` AES-XTS-256, Fan PWM (`libfan.so @ 0x1dec`) & Anti-Brick Guards**.

### 3. [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`477` Local Donor / `477` Clean-Room tests)
- **Phase 90 Milestone Master Gate (`stage_b_milestone90_master_gate.py`, `make verify-milestone-90`, `< 2s`)**: Unifies all 6 Milestone-90 pillars (`G01..G24`, `OTP/RPMB` + `GF(256)` + `FX3_SAFE_STOCK.FLG`, `16` Firmware-Lab Auditors, `13-Stage` VM, `Round 16` + `Round 14` real FX3 kernel closure, and `H0 == H2` 16-surface immutability) with deterministic `milestone90_sha256` ([Phase 90 Report](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)).
- **Stage-A (`P1..P9+Fan`) & Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` binaries / `18` sites, 100% SHA-256 rollback)**: `P10`, `P11` UIPC-CP shim, `P12` `WF-12` bootloop immunity + `BK4\0` shadow, `U1..U5`, `S01..S10`, `070701` CPIO, **Phase 52/76 Integrator & Release Dossier v3**, and **Phase 62/68/83 `16`-Surface `H0 == H2` Capstone Verifier** (`make verify-post-trial-audit`).

### 4. [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`183` Local Donor / `183` Clean-Room tests)
- **Live QEMU ARM64 `1024×540` `GPE0` Web Console on port `8768`** ([`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command), [`FX3菜单.command`](outputs/fx3-vm-trial/FX3菜单.command)):
  - Native `LDEC103` icons (`60/60` `0 SEGV`), 128-page 4-language pool (`简体中文 / 繁體中文 / EN / 日本語`), `P10` button deck, `.cube` 3D LUTs, 4-Ch `XLR-H1` VU, **Phase 56** IRE Waveform/RGB Histogram/Zebra/Peaking/Guides/Desqueeze, **Phase 64** Cine EI `800/12800`/Shutter Angle/`S&Q 1–240fps`/Tally Stealth/`usblan_ptpip`/`hdmi_raw16`, **Phase 73** Shockless WB/Base Look/Dual-Slot & `*M01.XML` export ([Phase 73 Report](reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md)), and **Phase 81** Canvas click 627-pt `Touch AF` (`GPE0 TAFC`), `x4` Focus Magnify (Clean HDMI), `S-Log3` `41%/94% IRE` False Color & `EL-Zone`, `CIZ` `1.5x/2.0x` zoom interlocks, and `CAMSET` round-trip ([Phase 81 Report](reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md)).

### 5. [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`83` Local Donor / `83` Clean-Room tests)
- **Rounds 1–16 (`r1a..r16d`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, **Round 14 `18/18` (`Big6` `0x0a` / `3-Layer Menu` `0x10..0x11` / `Status Check` `0x2f` × `6 Language Pairs`)** + **Rounds 15–16 complete 5-tab `Status Check` (`0x2f..0x33`, `C(5,2)=10/10` pairwise pixel-diffs `> 0`) plus `TC/Media` `ZH-TW` (`0x18`) and `Monitoring` `ZH-CN`/`JA` (`0x19`/`0x01`) zero-crash closures** ([Round 15](reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/README.md), [Round 16](reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/README.md)).

### 6. [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`388` Local Donor / `388` Clean-Room tests)
- **13-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
  - **Stages 1–9 (`Phases 24–67`)**: BT `/dev/ttyAMA3`, Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> unmodified `ARM32` `cpapp-b.bin`, `Soft-GPE0`, Pure-Py `CXD90057` FDT + `MHLX`, `IMX510`/XAVC/`RTMD`, 8-scenario HIL fault harness, `QMP`/`HMP`/`libqemu-plugin`/`GDB RSP` (`nop_count = 0`), `256B` `EDID` `HDMI RAW16`/USB-C, `SMPTE 12M` LTC `EXT-LK` PLL + `PZ` + `libpaint` `3x3`.
  - **Stages 10–13 (`Phases 71, 78, 82, 87`)**: **Stage 10 (Ph71)** Dual-slot relay & UPS `.RSV` salvage ([Phase 71](reports/2026-11-14-phase71-vm-stage10-dualslot-proxy-ups-salvage/README.md)); **Stage 11 (Ph78)** `960×540` `evdev` Touch AF/`CIZ`/Assignable shadow ([Phase 78](reports/2026-11-14-phase78-vm-stage11-touchaf-ciz-assignable/README.md)); **Stage 12 (Ph82)** `CAMSET01.DAT`/4ch `24-bit` LPCM/`SMPTE 12M` `BG1..BG8` UB ([Phase 82](reports/2026-11-14-phase82-vm-stage12-camset-lpcm-tcub/README.md)); **Stage 13 (Ph87)** Playback/`ShotMark1/2`/`<EssenceMark>`/`p1` format block/`Push Auto Iris`/Tropical `TEC` dew-point & `5V` rail shed ([Phase 87](reports/2026-11-14-phase87-vm-stage13-playback-shotmark-dewpoint/README.md)).

### 7. [`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`403` Local Donor / `403` Clean-Room tests)
- **16 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**:
  - `#1..#13`: `UFU`/`SDM2`, `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610` sprites, `IMX510`/XAVC, `.cube` + `RTMD`, `WBI2`/ELF64 `.dynsym`, `global.xdb` 128p, Audio/TC/HDMI (`#9`), E-Mount AF/IBIS (`#10`), Shutter Angle/`S&Q`/Tally (`#11`), WB/`OCIO v2`/ACES (`#12`), Proxy/`CamID`/`*M01.XML` (`#13`).
  - **`#14 (Ph75)`** `audit-assignable-ciz` (`Custom 1..6`, `CIZ 1.5x/2.0x`, `Big6` layout, [Phase 75](reports/2026-11-14-phase75-assignable-ciz-big6-auditor/README.md)) · **`#15 (Ph80)`** `audit-falsecolor-lpcm-ub` (`S-Log3` `41%/94% IRE`, `24-bit` LPCM, `User-Bits`, [Phase 80](reports/2026-11-14-phase80-falsecolor-lpcm-tc-ub-auditor/README.md)) · **`#16 (Ph85)`** `audit-playback-shotmark-ae` (Playback, `ShotMark1/2`, `Cine EI` `Push Auto Iris`, `p4_nd_motor_faults=0`, `internal_emmc_format_possible=False`, [Phase 85](reports/2026-11-14-phase85-playback-shotmark-ae-auditor/README.md)).

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
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite & Milestone-90 Clean-Room CI
├── Makefile                                 # Unified test, Milestone-90, 24-Gate, Tier-0 GF(256), OTP/RPMB, RP2040, init2, Stage-B, VM & Lab
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 24-Gate (`G01..G24`), 13-Stage VM & Tier-0..4 guide
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V XLR, Gimbal, Dew-Point TEC, 5V PMIC & <1s SD Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite test runner (2,191 Local / 2,133 Clean-Room) + BYOF + hygiene audit
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # 7 controlled engineering packages (2,191 Local Donor / 2,133 Clean-Room tests)
│   ├── fx3-recovery-adapter/                # Tier-0..4, Ph59 RP2040, Ph66 init2 escape/WDT, Ph72 GF(256), Ph79 OTP/RPMB (297/239)
│   ├── fx3-safety/                          # 24-Gate Master Preflight G01..G24 (+48V, Gimbal, TEC Dew-Point, 5V PMIC) (360)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B, Ph52/76 Integrator, Ph62/68/83 Post-Trial, Ph90 Master Gate (477)
│   ├── fx3-vm-trial/                        # Live port 8768 Web UI: 128p, Touch AF, x4, False Color, CIZ, Cine EI, Scopes (183)
│   ├── fx6-native-presenter-closure/        # Rounds 1..16 FX3 7.02 kernel GPE0: nop_count=0, 18/18 + 5-tab 10/10 (83)
│   ├── fx3-vm/                              # 13-stage Dual-ISA AP<->IVSHMEM<->CP, Soft-GPE0, HIL, QMP, EDID, CAMSET, Playback (388)
│   └── fx3-firmware-lab/                    # 16 unified keyless auditors: UFU..global.xdb, CIZ, FalseColor/LPCM, Playback/AE (403)
├── reports/                                 # Phases 1..90, Rounds 1..16, Waves 1..8 global intel & verification reports
└── conversations/                           # Categorized multi-agent engineering archives across 5 thematic workspaces
```

---

## 4. Quick Start & Verification

```bash
# 1. Run all 2,191 Local Donor tests across all 7 suites + BYOF manifest audit (57+57) + clean-room hygiene
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (2,133 tests across 7 suites, zero Sony firmware blobs — matches clean-room-ci.yml)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 90 Six-Pillar Master Gate (< 2s) + 24-Gate, Tier-0 GF(256) & OTP/RPMB Anti-Rollback (work in BOTH modes)
make verify-milestone-90
make verify-24-gates
make verify-tier0-backup
make verify-antirollback-guard
make verify-20-gates
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B Lifecycle Drill, Wireless Guard, Firmware Lab (16 Auditors), 13-Stage Co-Emulation & Stage-A Lifecycle targets
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
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Scopes / S&Q / 3D LUT Interactive QEMU Console**: `./outputs/fx3-vm-trial/FX6菜单.command` -> `http://127.0.0.1:8768/`
- **FX3 Native Menu Web Console**: `./outputs/fx3-vm-trial/FX3菜单.command` (`--check` validates SHA-256 inputs without starting QEMU)

---
---

# 简体中文文档

## 一、项目总览（`Phases 1–90` · `Rounds 1–16` · `Waves 1–8`）

**`sony-fx3-fx6-lab`** 围绕 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 开展净室系统工程、多架构 QEMU 协同仿真、跨机型固件兼容适配与真机防变砖安全研究。两款机型均基于 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

历经 **`Phases 1–90`**、**`Rounds 1–16`** 与 **`Waves 1–8` 全球公开情报同步** 迭代，实验室已构建起 **7 大统一自动化验证套件（`make test` 本地供体全量 `2,191` 项通过 / `FX3_FX6_FORCE_CLEAN_ROOM=1` 无供体洁净室 `2,133` 项全绿通过）** 与 **Phase 90 六柱一体化总闸（`make verify-milestone-90`，`< 2s`）**：
- **Stage-B 易失性 RAM 覆盖层（`P1..P12+Fan`，`13/13` 挂载前校验）**：涵盖 `P10` FX3 实体按键映射、`P11` AP 侧 UIPC-CP 垫片（保留 `XLR-H1` 热靴音频与 5 轴 IBIS 居中锁止）、`P12` `WF-12` 无线断环补丁、`< 48 MiB` SVR4 `070701` CPIO 打包器、Phase 52/76 集成与发布简报 v3、Phase 62/68/83 `16` 表面 `H0 == H2` 试后法证与收官审计，以及 **Phase 90 六柱一体化总闸**（[Phase 90 报告](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)）。
- **24 门禁主安全预检引擎（`G01..G24`）与 `Tier-0..Tier-4` 救砖阶梯（`S01..S12`）**：刚性锁定 **C2PA**（`RQ_LIC.DAT`/`sigcert.p12`）与出厂校准不可变性、`exFAT` 掉电卫生与客户素材防火墙（`G17`）、有线 `USB-LAN CDC-NCM` + `PTP-IP 15740` 与 `P12` 飞行共存（`G18`）、套件 D-Tap/铜 HDMI 地环路互锁与 E 卡口 `<= 2.0ms` 撬棍断流（`G19`）、`NP-FZ100 >= 15%` UPS 冗余与 `.RSV` 只读抢救（`G20`）、**`+48V` XLR 幻象电源防烧毁（`G21`）**、**稳定器/跟焦 `<= 0.35 N·m` 扭矩与快门保护（`G22`）**、**Magnus 露点 `TEC` 结露拦截（`G23`）**、**PMIC `5V 900 mA` 配件供电预算（`G24`）**、`RP2040-Zero -DOPEN_DRAIN` 断机治具自检（`Phase 59`）、`< 1s` `FX3_SAFE_STOCK.FLG` `init2` 逃生（`Phase 66`）、**`GF(256)` RAID-6 Tier-0 备份自愈（`Phase 72`）**，以及 **`CXD90057` OTP/RPMB 零写入防回滚与 `EXT_CSD[173/171]` 熔丝陷阱拦截（`Phase 79`）**。
- **端口 `8768` 实时交互式 QEMU 控制台（`FX6菜单.command`）、13 阶段全板协同仿真（`fx3-vm`）、16 大无密钥固件审计器（`fx3-firmware-lab`）与 `Rounds 1–16`（`18/18` + Status Check 5 标签 `10/10` 闭环，`nop_count = 0`）**：支持双原生 ISO `800/12800` Cine EI、IRE 波形/RGB 直方图、**627 点 `Touch AF`（`GPE0 TAFC`）**、**`x4` 放大（HDMI 净流）**、**`S-Log3` `41%/94% IRE` 伪色与 `EL-Zone`**、**`CIZ`（`1.5x/2.0x`）**、**`Shockless WB`/`Base Look`/`*M01.XML`**、**`CAMSET` 往返**、**`ShotMark1/2` `<EssenceMark>`**、**`Push Auto Iris`**、13 阶段双核协同仿真（`cp_mutation_bytes = 0`）与 16 大无密钥审计器。

架构细节与现场操作规范请参见 **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** 与 **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**。

---

## 二、七大统一测试套件明细（`make test` — 本地供体 `2,191` 项 / 洁净室 `2,133` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `297` / 洁净室 `239` 项测试）**：**Phase 79** `CXD90057` OTP/RPMB 零写入防回滚与 `EXT_CSD[173/171]` 陷阱拦截（`make verify-antirollback-guard`，[Phase 79 报告](reports/2026-11-14-phase79-antirollback-otp-rpmb-epoch-guard/README.md)）、**Phase 72** `GF(256)` (`0x11d`) RAID-6 Tier-0 双分片坏道自愈备份库（`make verify-tier0-backup`，[Phase 72 报告](reports/2026-11-14-phase72-tier0-backup-gf256-parity-guard/README.md)）、**Phase 66** 4 层 `<1s` `FX3_SAFE_STOCK.FLG` `init2` SD 逃生 + WDT `10,000ms` 破环 + `p1` `FAT12/16` 交换（`make verify-init2-escape`）、**Phase 59** `RP2040-Zero -DOPEN_DRAIN` 断机治具自检（`make verify-rp2040-fixture`）、`Tier-0..Tier-4` 救砖阶梯（`S01..S12`）、`p1` VFAT 胶囊、偏移 VMA `v7.02` `p1` 4 锚点自动定位、macOS 26 `IOUSBHost` 与 `O_RDONLY` eMMC ISP 取证。
2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `360` 项测试）**：**`G01..G24` 24 门禁主安全预检引擎（`make verify-24-gates`）** 涵盖 `G01..G16` 基础红线、**Phase 57/61** `exFAT` 与 `USB-LAN CDC-NCM` + `PTP-IP 15740`（`G17/G18`）、**Phase 69** D-Tap/HDMI 地环路与 `<= 2.0ms` E 卡口断流+IBIS 居中停靠、`NP-FZ100 >= 15%` UPS（`G19/G20`）、**Phase 77** `+48V` XLR 幻象电源防烧毁与 `<= 0.35 N·m` 稳定器跟焦/快门保护（`G21/G22`，[Phase 77 报告](reports/2026-11-14-phase77-phantom48v-gimbal-22gate-guard/README.md)），以及 **Phase 84** Magnus 露点 `TEC` 结露拦截与 PMIC `5V 900 mA` 配件预算门禁（`G23/G24`，[Phase 84 报告](reports/2026-11-14-phase84-dewpoint-tec-usbc-24gate-guard/README.md)）；另含 6 阶段 `H0` 预演、`WDT v2`、`VMC-BNCM1`、`SPACC`、`libfan.so` PWM 等。
3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `477` 项测试）**：**Phase 90 六柱一体化总闸（`make verify-milestone-90`，`< 2s`）** 汇聚 `24-Gate`、`OTP/RPMB + GF(256) + init2`、`16` 审计器、`13-Stage` VM、`Round 16/14` 真机核闭环与 `H0 == H2` 16 表面不可变性（[Phase 90 报告](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)）；Stage-A（`P1..P9+Fan`）+ Stage-B（`P1..P12+Fan` `13/13` 补丁）：`P10`、`P11` `Uipc/CP` 垫片、`P12` `WF-12` 断环 + `BK4\0`、`U1..U5`、`S01..S10`、`070701` CPIO、**Phase 52/76** 集成简报与发布档案 v3，以及 **Phase 62/68/83** 16 表面 `H0==H2` 试后收官审计（`make verify-post-trial-audit`）。
4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `183` 项测试）**：端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)）：原生 `LDEC103` 图标与 `60/60` 零崩溃、LRU 128 页四语池、`.cube` 3D LUT、4 通道 `XLR-H1` VU、**Phase 56** IRE 波形/RGB 直方图/斑马纹/峰值/画幅参考线、**Phase 64** 双原生 ISO `800/12800` Cine EI/快门角/`S&Q 1–240fps`/Tally 隐身/`usblan_ptpip`/`hdmi_raw16`、**Phase 73** `Shockless WB`/`Base Look`/双卡与 `*M01.XML` 导出（[Phase 73 报告](reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md)），以及 **Phase 81** 画布点击 627 点 `Touch AF`（`GPE0 TAFC`）/`x4` 放大（HDMI 净流）/`S-Log3` `41%/94% IRE` 伪色 & `EL-Zone`/`CIZ` `1.5x/2.0x` 变焦互斥与 `CAMSET` 往返（[Phase 81 报告](reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md)）。
5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `83` 项测试）**：**Rounds 1–16（`r1a..r16d`）** FX3 `7.02` 原厂 `4.9.337-scel+` 内核混合态真机实跑（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）：完成 **Round 14 `EN/ZH-CN/ZH-TW/JA` × 3 大界面 `18/18` 像素差分严格全正闭环**，以及 **Rounds 15–16 完整 `5` 标签 `Status Check`（`0x2f..0x33`，`C(5,2)=10/10` 两两差分全正 `> 0`）+ `TC/Media` 繁中（`0x18`）与 `Monitoring` 简中/日语（`0x19`/`0x01`）零崩溃全闭环**（[Round 15](reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/README.md)、[Round 16](reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/README.md)）。
6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `388` 项测试）**：**13 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**：Stages 1–9（BT、双核 `AArch64` AP ↔ `IVSHMEM` ↔ `ARM32` `cpapp-b.bin`、`Soft-GPE0`、纯 Py FDT+`MHLX`、`IMX510`/XAVC、8 场景 HIL、`QMP`/`libqemu-plugin`、`256B EDID` `HDMI RAW16`、`SMPTE 12M` LTC `EXT-LK` PLL/`PZ`/`libpaint`）+ **Stage 10（Ph71）** 双卡槽无缝中继/UPS `.RSV`（[Phase 71](reports/2026-11-14-phase71-vm-stage10-dualslot-proxy-ups-salvage/README.md)）+ **Stage 11（Ph78）** `960×540` `evdev` Touch AF/`CIZ`/自定义键影子（[Phase 78](reports/2026-11-14-phase78-vm-stage11-touchaf-ciz-assignable/README.md)）+ **Stage 12（Ph82）** `CAMSET01.DAT`/4ch `24-bit` LPCM/`BG1..BG8` UB（[Phase 82](reports/2026-11-14-phase82-vm-stage12-camset-lpcm-tcub/README.md)）+ **Stage 13（Ph87）** 回放/`ShotMark1/2`/`<EssenceMark>`/`p1` 格式化拦截/`Push Auto Iris` 与热带露点/5V 卸载（[Phase 87](reports/2026-11-14-phase87-vm-stage13-playback-shotmark-dewpoint/README.md)）。
7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `403` 项测试）**：**16 大洁净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：`#1..#13`（`UFU`..`global.xdb` 128p、Audio/TC/HDMI、AF/IBIS、快门/Tally、白平衡/`OCIO v2`、代理/`*M01.XML`）+ **`#14（Ph75）`** `Custom 1..6`/`CIZ 1.5x/2.0x`/`Big6`（[Phase 75](reports/2026-11-14-phase75-assignable-ciz-big6-auditor/README.md)）+ **`#15（Ph80）`** `S-Log3` `41%/94% IRE` 伪色/`24-bit` LPCM/`User-Bits`（[Phase 80](reports/2026-11-14-phase80-falsecolor-lpcm-tc-ub-auditor/README.md)）+ **`#16（Ph85）`** 回放/`ShotMark1/2`/自动光圈与 `p4_nd_motor_faults=0`/`internal_emmc_format_possible=False` 护栏（[Phase 85](reports/2026-11-14-phase85-playback-shotmark-ae-auditor/README.md)）。

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
# 1. 运行全部 7 套 2,191 项本地供体测试 + BYOF 双语清单审计 (57+57) + git 净室零残留审计
make test
make test-json

# 2. 本地模拟无供体洁净室 CI (7 套 2,133 项测试，零索尼固件依赖，与 GitHub Actions 完全一致)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 90 六柱一体化总闸 (<2s) + 24 门禁、Tier-0 GF(256)、OTP/RPMB 防回滚与治具逃生（双模式通用）
make verify-milestone-90
make verify-24-gates
make verify-tier0-backup
make verify-antirollback-guard
make verify-20-gates
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B 生命周期演练、无线防护、固件实验室（16 审计器）、13 阶段协同仿真与 Stage-A 演练命令
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
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / 示波器 / S&Q / 3D LUT 实时控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入 SHA-256）。

---

## 四、多智能体归档与开源协议 (Archives & License)

- **工程对话归档**：5 大专题工作区多智能体研究对话已按净室规范分类归档至 **[conversations/README.md](conversations/README.md)**。
- **免责与开源协议**：本仓库包含 **0 字节** 索尼专有二进制固件或私有密钥，与 Sony Group Corporation 无任何隶属或合作关系。自研源码采用 MIT 协议，QEMU 补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
