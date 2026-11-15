# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-24--Gate_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-Tier--0..4_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-2,191_Local_%7C_2,133_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r16d_(18%2F18_%2B_10%2F10)-success?style=flat)](#the-7-unified-verification-suites-make-test--2191-local-donor--2133-clean-room)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#5-legal--clean-room-compliance-notice)

> **Switch Language / Deep Reference**: [**👉 简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master (`README.md`)**](./README.md) · [**Stage-B Architecture & 24-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** digital cinema cameras, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> Persistent hardware flashing & live attach remain **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `hardware_live_attachment_authorized = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), `calibration_mutation_bytes = 0`, `otp_fuse_touches = 0`, and `rpmb_counter_increments = 0`. Every Stage-A and Stage-B overlay operates strictly in volatile Linux DDR (`tmpfs`), accesses donor blobs strictly via `os.O_RDONLY`, supports `< 1s` zero-cable `FX3_SAFE_STOCK.FLG` SD escape, and reverts cleanly to 100% stock Sony ILME-FX3 `Ver. 7.02` on power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images) and **0 vendor AES/RSA private keys**. All `7` verification suites (`2,133` clean-room tests) plus `Milestone Phase 90 Master Gate`, `24-Gate`, `20-Gate`, `RP2040`, `init2`, `Tier-0 GF(256)`, `OTP/RPMB Anti-Rollback`, and `Post-Trial` CLI gates execute cleanly in donorless mode (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) on `ubuntu-latest` + `macos-latest` via [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing interactive VM sessions with your own official firmware files.

---

## 1. Engineering Milestones (`Phases 1–90` · `Rounds 1–16` · `Waves 1–8`)

### The 7 Unified Verification Suites (`make test` — `2,191` Local Donor / `2,133` Clean-Room)

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`297` Local Donor / `239` Clean-Room tests)**
   - **Phase 79 `CXD90057` OTP/RPMB Anti-Rollback & `EXT_CSD[173/171]` Guard** ([Phase 79 Report](reports/2026-11-14-phase79-antirollback-otp-rpmb-epoch-guard/README.md), `make verify-antirollback-guard`): Verifies `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, monotonic downgrade protection, and permanent eMMC write-protect trap containment.
   - **Phase 72 `GF(256)` (`0x11d`) RAID-6 Tier-0 Vault & Cross-Unit Portability Guard** ([Phase 72 Report](reports/2026-11-14-phase72-tier0-backup-gf256-parity-guard/README.md), `make verify-tier0-backup`): Enforces 2-shard bit-rot self-healing across `11` read-only partitions bound to `body_binding_sha256` (`c65670ea25a2c28e`).
   - **Phase 66 `init2` SD-Sentinel (`FX3_SAFE_STOCK.FLG` `< 1s`), `CXD90057` WDT `10,000ms` Breaker & `p1` `FAT12/16` Verifier** ([`init2_escape_and_watchdog_simulator.py`](outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [Phase 66 Report](reports/2026-11-14-phase66-init2-escape-watchdog-fat-verifier/README.md), `make verify-init2-escape`) & **Phase 59 `RP2040-Zero -DOPEN_DRAIN` Bench Self-Test** ([`rp2040_multiport_fixture_selftest.py`](outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [Phase 59 Report](reports/2026-11-14-phase59-rp2040-multiport-fixture-selftest/README.md), `make verify-rp2040-fixture`).
   - **Tier-0..Tier-4 Unbrick Ladder (`S01..S12`), `p1` VFAT Capsule, Shifted-VMA `v7.02` `p1` Autolocator, macOS 26 `IOUSBHost` & `O_RDONLY` eMMC ISP Verifier** ([Phase 47](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md), [Phase 42](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)), plus freestanding static AArch64 capture workers.

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/) (`360` Local Donor / `360` Clean-Room tests)**
   - **24-Gate Master Safety Preflight Engine (`G01..G24`, `make verify-24-gates`)**: Composes `preflight.py` (`G01..G12`) + [`master_16gate_preflight.py`](outputs/fx3-safety/fx3_safety/master_16gate_preflight.py) (`G13..G16`) + **Phase 57/61** (`G17` exFAT/client media firewall & `G18` wired `USB-LAN CDC-NCM` + `PTP-IP 15740`) + **Phase 69** (`G19` D-Tap/HDMI ground-loop & `<= 2.0ms` `V_LENS` crowbar + Stock-CP `0x0400` IBIS park; `G20` `NP-FZ100 >= 15%` UPS & `.RSV` salvage) + **Phase 77** [`phantom48v_gimbal_and_22gate_guard.py`](outputs/fx3-safety/fx3_safety/phantom48v_gimbal_and_22gate_guard.py) (`G21` `+48V` XLR phantom burnout guard; `G22` gimbal/focus torque `<= 0.35 N*m` & shutter guard, [Phase 77](reports/2026-11-14-phase77-phantom48v-gimbal-22gate-guard/README.md)) + **Phase 84** [`dewpoint_tec_usbc_and_24gate_guard.py`](outputs/fx3-safety/fx3_safety/dewpoint_tec_usbc_and_24gate_guard.py) (`G23` Magnus dew-point `TEC` condensation block & `G24` PMIC `5V 900 mA` accessory budget guard, [Phase 84](reports/2026-11-14-phase84-dewpoint-tec-usbc-24gate-guard/README.md)).
   - **Hardware Guardrails & Rehearsal**: Includes 6-stage `H0` rehearsal (`--unicorn`), `serial_fault_detector_v2`, `RP2040-Zero -DOPEN_DRAIN` & `VMC-BNCM1` LTC firewall, `CrSDK` PTP2, MI-Shoe `XLR-H1`, `CXD90057 SPACC` AES-XTS-256 guard, FX3 Fan PWM (`libfan.so @ 0x1dec`) + `NP-FZ100`/`USB-PD 9V/3A` guards, and runtime anti-brick guards.

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`477` Local Donor / `477` Clean-Room tests)**
   - **Phase 90 Milestone Master Gate ([`stage_b_milestone90_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone90_master_gate.py), `make verify-milestone-90`, `< 2s`)**: Unifies all 6 Milestone-90 pillars (`G01..G24`, `OTP/RPMB` + `GF(256)` + `FX3_SAFE_STOCK.FLG`, `16` Firmware-Lab Auditors, `13-Stage` VM, `Round 16` + `Round 14` real FX3 kernel closure, and `H0 == H2` 16-surface immutability) with deterministic `milestone90_sha256` ([Phase 90 Report](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)).
   - **Stage-A (`P1..P9+Fan`) & Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` ELF/module targets / `18` sites, 100% SHA-256 rollback)**: `P10` 24B FX3 button remap (`e2bc2619...`), `P11` AP-side UIPC-CP shim preserving `XLR-H1` & 5-axis IBIS center-lock, and `P12` `libWlanResource.so @ 0x70d4` (`47fec188...`) `WF-12` bootloop immunity + `BK4\0` Airplane/CJK shadow.
   - **Full Blueprint, Integration & Post-Trial Forensics**: Closes **`U1..U5`**, `60`-ELF `.dynsym` + `137` `/dev/*` + `.ko` linkage, **`S01..S10` Stage-B lifecycle drill**, **Phase 48 SVR4 `070701` Packager (`9/9` `init2`)**, **Phase 52/76 Unified Candidate Integrator & Release Dossier v3** ([Phase 76 Report](reports/2026-11-14-phase76-stage-b-release-dossier-v3/README.md)), and **Phase 62/68/83 `16`-Surface `H0 == H2` Capstone Post-Trial Forensic Auditor** (`make verify-post-trial-audit`, [Phase 83 Report](reports/2026-11-14-phase83-stage-b-capstone-22gate-verifier/README.md)).

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`183` Local Donor / `183` Clean-Room tests)**
   - **Live QEMU ARM64 `1024×540` `GPE0` Web Console (`127.0.0.1:8768`, [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command))**: Authentic `image_00_169.uxc` `LDEC103` icons & `60/60` `0 SEGV`, LRU 128-page pool (`170/170`), live **`简体中文 / 繁體中文 / EN / 日本語`** switching, FX3 `P10` deck, `.cube` `17^3/33^3` 3D LUT uploader, 4-Ch `XLR-H1` VU meter, **Phase 56** IRE Waveform/RGB Histogram/Zebra/Peaking/Guides/Desqueeze, **Phase 64** Dual Base `800/12800` Cine EI, Shutter Angle `5.6°..360.0°`/`ECS`, `S&Q 1–240fps` + auto audio-mute, Tally Stealth, `usblan_ptpip`/`hdmi_raw16` with HTTP `400` `P4`/`P12` tamper locks, **Phase 73** Shockless WB/Base Look/Dual-Slot & `*M01.XML` ([Phase 73](reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md)), and **Phase 81** Canvas click 627-pt `Touch AF` (`GPE0 TAFC`), `x4` Focus Magnify (Clean HDMI), `S-Log3` `41%/94% IRE` False Color & `EL-Zone`, `CIZ` `1.5x/2.0x` interlocks, and `CAMSET` round-trip ([Phase 81](reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md)).

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`83` Local Donor / `83` Clean-Room tests)**
   - **Rounds 1–16 (`r1a..r16d`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, `LDEC103` physical pool sprite blitting, **Round 14 `18/18` (`Big6` `0x0a` / `3-Layer Full Menu` `0x10..0x11` / `Status Check` `0x2f` × `6 Language Pairs`)** plus **Rounds 15–16 complete 5-tab `Status Check` (`0x2f..0x33`, `C(5,2)=10/10` pairwise pixel-diffs `> 0`) and `TC/Media` `ZH-TW` (`0x18`) / `Monitoring` `ZH-CN`/`JA` (`0x19`/`0x01`) zero-crash closures** ([Round 15](reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/README.md), [Round 16](reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/README.md)).

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`388` Local Donor / `388` Clean-Room tests)**
   - **13-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**: Stages 1–5 (`virtual-rom-v1` `/dev/ttyAMA3` BT, Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> `ARM32` unmodified `cpapp-b.bin`, `Soft-GPE0` + `ramfb`, Pure-Py `CXD90057` FDT `0xd00dfeed` + `MHLX`, `IMX510`/XAVC/`RTMD`/Dual CFexpress); **Stages 6–9 (`Phases 53..67`)** (8-scenario HIL, `QMP`/`HMP`/`libqemu-plugin`/`GDB RSP` `nop_count = 0`, `256B` `EDID` `HDMI RAW16`/USB-C, `SMPTE 12M` LTC `EXT-LK` PLL + `PZ` + `libpaint` `3x3`); **Stage 10 (Ph71)** Dual-slot relay & UPS `.RSV` salvage ([Phase 71](reports/2026-11-14-phase71-vm-stage10-dualslot-proxy-ups-salvage/README.md)); **Stage 11 (Ph78)** `960×540` `evdev` Touch AF/`CIZ`/Assignable ([Phase 78](reports/2026-11-14-phase78-vm-stage11-touchaf-ciz-assignable/README.md)); **Stage 12 (Ph82)** `CAMSET01.DAT`/4ch `24-bit` LPCM/`BG1..BG8` UB ([Phase 82](reports/2026-11-14-phase82-vm-stage12-camset-lpcm-tcub/README.md)); **Stage 13 (Ph87)** Playback/`ShotMark1/2`/`<EssenceMark>`/`p1` format intercept/`Push Auto Iris`/Tropical `TEC` dew-point & `5V` shed ([Phase 87](reports/2026-11-14-phase87-vm-stage13-playback-shotmark-dewpoint/README.md)).

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`403` Local Donor / `403` Clean-Room tests)**
   - **16 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**: `#1..#13` (`UFU`/`SDM2`, `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610` sprites, `IMX510`/XAVC, `.cube` + `RTMD`, `WBI2`/ELF64 `.dynsym`, `global.xdb` 128p, Audio/TC/HDMI, AF/IBIS, Shutter/Tally, WB/`OCIO v2`, Proxy/`*M01.XML`) + **`#14 (Ph75)`** `audit-assignable-ciz` ([Phase 75](reports/2026-11-14-phase75-assignable-ciz-big6-auditor/README.md)) + **`#15 (Ph80)`** `audit-falsecolor-lpcm-ub` ([Phase 80](reports/2026-11-14-phase80-falsecolor-lpcm-tc-ub-auditor/README.md)) + **`#16 (Ph85)`** `audit-playback-shotmark-ae` ([Phase 85](reports/2026-11-14-phase85-playback-shotmark-ae-auditor/README.md)).

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
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows; `v7.02` `p1` resolved via 4-site AArch64 `ADRP/BL` autolocator; `p1` `FAT12/16` atomic swap audited by Phase 66; Phase 79 blocks `OTP`/`RPMB` rollbacks. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 `7.02` and FX6 `6.01` (`@ 0xFE049000`); Tier-0 protected by `GF(256)` RAID-6 (`Phase 72`); Tier-3 BootROM `48000`-baud recovery requires `RP2040-Zero -DOPEN_DRAIN` (`make verify-rp2040-fixture`). |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; `p2:/setting/{psd,defdet}.bin`, `p6:Jiritsu`, `p12:/cert` (C2PA `RQ_LIC.DAT`), and `p18:/lens/lensfile.bin` remain hard-locked read-only (`G15`). |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Stage-A & Stage-B keep stock FX3 kernel, stock `p8:/cpapp-b.bin` (`@ 0x00108000`, `cp_mutation_bytes = 0`), and `p5:/wbi` hibernation blocked (`wbi_mutation_bytes = 0`). |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A (`30-stage-a-orchestrator.sh`) & Stage-B (`stage_b_init2_guard.sh`) check `FX3_SAFE_STOCK.FLG` first (`< 1s` instant escape), verify `13/13` SHA-256 digests before mount, enforce `24-Gate` + `EXT_CSD` locks, activate volatile `tmpfs` (`< 48 MiB`), and unwind in reverse LIFO (`H0 == H2`). |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite & Milestone-90 Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test, Milestone-90, 24-Gate, Tier-0 GF(256), OTP/RPMB, RP2040, init2, Stage-B, VM, Lab & BYOF
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 24-Gate (`G01..G24`), 13-Stage VM & Tier-0..4 reference
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V XLR, Gimbal, Dew-Point TEC, 5V PMIC & <1s SD Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite runner (2,191 Local / 2,133 Clean-Room) + BYOF audit + hygiene check
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
└── conversations/                           # Categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Unified Test Suite, Clean-Room CI, Milestone-90, 24-Gate, Recovery, Stage-B, Firmware Lab & Co-Emulation Targets

```bash
# 1. Run all 2,191 Local Donor tests across all 7 suites (297 + 360 + 477 + 183 + 83 + 388 + 403) + BYOF (57+57) + hygiene check
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (2,133 tests across 7 suites, zero Sony firmware blobs — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 90 Master Gate (< 2s) + 24-Gate, Tier-0 GF(256), OTP/RPMB, RP2040, init2 Escape & Post-Trial Gates (BOTH modes)
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

### 4.2 Launch Interactive FX3 or FX6 Web Menu Emulators (Requires BYOF Setup)

After preparing your own official firmware files per **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**:
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Scopes / S&Q / 3D LUT / Multilingual Web Console**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under the MIT license; QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
