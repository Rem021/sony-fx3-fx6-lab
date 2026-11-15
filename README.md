# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![English Standalone](https://img.shields.io/badge/Standalone_EN-README.en.md-0969da?style=flat)](./README.en.md)
[![简体中文独立版](https://img.shields.io/badge/独立中文版-README.zh--CN.md-0969da?style=flat)](./README.zh-CN.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-20--Gate_%7C_EN_%2B_ZH-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-Tier--0..4_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-1,601_Local_%7C_1,543_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r14d_(18%2F18)-success?style=flat)](#5-outputsfx6-native-presenter-closure-61-tests)
[![Stage-B Closure](https://img.shields.io/badge/Stage--B_Closure-Phases_1..70_%7C_Rounds_1..14_%7C_Waves_1..6-1a7f37?style=flat)](#3-outputsfx6-on-fx3-closure-339-tests)

> **Language Navigation / 语言切换**: **[English Documentation](#english-documentation)** · **[简体中文文档](#简体中文文档)** · **[Stage-B Architecture & 20-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** · **[Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)** · **[Standalone `README.en.md`](./README.en.md)** · **[独立中文版 `README.zh-CN.md`](./README.zh-CN.md)**

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> **硬件写入硬锁状态（严禁持久化刷写真机 eMMC / SPI NOR）**  
> Persistent flashing remains **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), and `calibration_mutation_bytes = 0`. All Stage-A/Stage-B overlays target volatile DDR (`tmpfs`) only, read donor blobs strictly via `os.O_RDONLY`, support `< 1s` `FX3_SAFE_STOCK.FLG` zero-cable SD escape, and revert instantaneously to 100% stock Sony ILME-FX3 `Ver. 7.02` upon power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware) / 净室开源合规边界**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` images) and **0 vendor AES/RSA private keys**. Donorless clean-room verification (`1,543` tests across all `7` suites + `20-Gate`, `RP2040`, `init2`, and `Post-Trial` CLI gates) runs cleanly via `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` and [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded by `make verify-byof`, `57+57` SHA-256 entries + `46` code constants).

---

# English Documentation

## 1. Executive Summary (`Phases 1–70` · `Rounds 1–14` · `Waves 1–6`)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, cross-model firmware compatibility, and anti-brick safety laboratory targeting the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)**, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

Across **`Phases 1–70`**, **`Rounds 1–14`**, and **`Global Intel Waves 1–6`**, the lab integrates **7 unified verification suites (`1,601` Local Donor / `1,543` Clean-Room passing tests via `make test`)** covering:
- **Stage-B Volatile RAM-Overlay (`P1..P12 + Fan`, `13/13` Verify-Before-Mount)** with FX3 physical button remap (`P10`), AP-side UIPC-CP shim (`P11`, preserving `XLR-H1` & 5-axis IBIS center-lock), `WF-12` bootloop immunity (`P12`), `< 48 MiB` SVR4 `070701` CPIO packaging, Phase 52 Candidate Integrator (`< 5s`), and Phase 62 `16`-surface `H0 == H2` Post-Trial Forensic Auditor.
- **20-Gate Master Preflight (`G01..G20`) & Tier-0..Tier-4 Unbrick Ladder (`S01..S12`)**: Protects Sony **C2PA** (`RQ_LIC.DAT`, `sigcert.p12`), factory calibration, `exFAT` `BootChecksum`/client media (`G17`), wired `USB-LAN CDC-NCM` / `PTP-IP 15740` + `P12` Airplane coexistence (`G18`), cinema rig D-Tap/copper HDMI ground-loop isolation + E-Mount `2.0ms` `V_LENS` crowbar (`G19`), `NP-FZ100 >= 15%` UPS reserve + `.RSV` salvage (`G20`), `RP2040-Zero -DOPEN_DRAIN` bench self-test (`Phase 59`), and `< 1s` `FX3_SAFE_STOCK.FLG` 4-layer `init2` escape + `CXD90057` WDT `10,000ms` breaker (`Phase 66`).
- **Live Port `8768` Multilingual QEMU Console (`FX6菜单.command`), 9-Stage Co-Emulation (`fx3-vm`), 13 Unified `fx3-firmware-lab` Auditors & `Rounds 1–14` (`18/18` 4-Lang × 3-Surface `nop_count = 0`)**: Interactive Dual Base `800/12800` Cine EI, IRE Waveform/RGB Histogram, Shutter Angle/`ECS`, `S&Q 1–240fps`, Tally Stealth, `HDMI RAW16` / `USB-LAN` controls, `QMP`/`libqemu-plugin` tracing, `SMPTE 12M` LTC `EXT-LK`, `OCIO v2`/`ACES`, and `CamID/Reel#` + `*M01.XML` auditing.

For complete architectural & field manuals, see **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** and **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**.

---

## 2. The 7 Unified Verification Suites (`make test` — `1,601` Local Donor / `1,543` Clean-Room)

Running `make test` executes all **7 suites (`1,601` Local Donor / `1,543` Clean-Room)**, the bilingual `docs/BYOF-REPRODUCTION.md` manifest audit (`57+57` entries, `46` constants), and the `git status --porcelain` zero-binary/zero-`.pyc` hygiene sweep:

### 1. [`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`231` Local Donor / `173` Clean-Room tests)
- **Phase 66 `init2` SD-Sentinel (`FX3_SAFE_STOCK.FLG` `< 1s`), `CXD90057` WDT `10,000ms` Breaker & `p1` `FAT12/16` Chain Verifier** (`init2_escape_and_watchdog_simulator.py`, [Phase 66 Report](reports/2026-11-14-phase66-init2-escape-watchdog-fat-verifier/README.md), `make verify-init2-escape`) proving 4-layer fail-open escape before `mount --bind`, atomic `INIT2.SH <-> INIT2BAK.SH` 32B entry swaps, and `H0 == H2` WDT recovery.
- **Phase 59 Camera-Disconnected `RP2040-Zero -DOPEN_DRAIN` Bench Self-Test** (`rp2040_multiport_fixture_selftest.py`, [Phase 59 Report](reports/2026-11-14-phase59-rp2040-multiport-fixture-selftest/README.md), `make verify-rp2040-fixture`) enforcing `[1.71, 1.89V]` pull-up, `>= 1 MOhm` rail isolation, and `48,000`-baud PIO fractional divider `<= 0.0004%` error prior to any physical camera attach.
- **Tier-0..Tier-4 Unbrick Ladder (`S01..S12`) & `p1` VFAT Capsule** ([Phase 47 Report](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md)), **Shifted-VMA FX3 `v7.02` `p1` 4-Site Autolocator**, **macOS 26 `IOUSBHost` (`0xe00002be`) Guard**, **strict `O_RDONLY` eMMC ISP Verifier** ([Phase 42 Report](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)), and static AArch64 capture workers.

### 2. [`outputs/fx3-safety/`](outputs/fx3-safety/) (`292` Local Donor / `292` Clean-Room tests)
- **20-Gate Master Safety Preflight Engine (`G01..G20`)** (`make verify-20-gates`) composing `preflight.py` (`G01..G12`) + `master_16gate_preflight.py` (`G13..G16`) + **Phase 57** [`exfat_media_integrity_guard.py`](outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py) (`BootChecksum`, `VolumeDirty=0`, `XDROOT`/`M4ROOT`/`.RSV`) + **Phase 61** [`usblan_ptpip_and_18gate_preflight.py`](outputs/fx3-safety/fx3_safety/usblan_ptpip_and_18gate_preflight.py) (`G17` exFAT/client media firewall & `G18` wired `USB-LAN CDC-NCM` + `PTP-IP 15740` + `P12` Airplane coexistence) + **Phase 69** [`rig_groundloop_lensrail_and_20gate_guard.py`](outputs/fx3-safety/fx3_safety/rig_groundloop_lensrail_and_20gate_guard.py) (`G19` D-Tap/copper HDMI ground-loop & E-Mount `<= 2.0ms` `V_LENS` crowbar + Stock-CP `0x0400` IBIS park; `G20` `NP-FZ100 >= 15%` UPS reserve + read-only `.RSV` salvage).
- **6-Stage `H0` Hardware Rehearsal (`--unicorn`)**, **`serial_fault_detector_v2`**, **`RP2040-Zero -DOPEN_DRAIN` & `VMC-BNCM1` LTC**, **`CrSDK` PTP2**, **MI-Shoe `XLR-H1`**, **`SPACC` `cnflasha` AES-XTS-256**, **FX3 Fan PWM (`libfan.so @ 0x1dec`)**, and runtime anti-brick guards.

### 3. [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`339` Local Donor / `339` Clean-Room tests)
- **Stage-A (`P1..P9+Fan`) & Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` binaries / `18` sites, 100% SHA-256 rollback)**: `P10` 24B FX3 button remap (`e2bc2619...`), `P11` AP-side UIPC-CP shim preserving `XLR-H1` & 5-axis IBIS center-lock, and `P12` `libWlanResource.so @ 0x70d4` (`47fec188...`) `WF-12` bootloop immunity + `BK4\0` Airplane/CJK shadow.
- **`U1..U5` Blueprint Closure**, `60`-ELF `.dynsym` + `137` `/dev/*` + `.ko` Closure, **`S01..S10` Stage-B Lifecycle Drill**, **Phase 48 SVR4 `070701` Packager (`9/9` `init2`)**, **Phase 52 Unified Candidate Integrator** (`stage_b_integrated_dossier_v1`, `< 5s`, [Phase 52 Report](reports/2026-11-14-phase52-stage-b-candidate-integrator/README.md)), and **Phase 62 `16`-Surface `H0 == H2` Post-Trial Forensic Auditor** (`make verify-post-trial-audit`, [Phase 62 Report](reports/2026-11-14-phase62-stage-b-post-trial-forensic-auditor/README.md)).

### 4. [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`129` Local Donor / `129` Clean-Room tests)
- **Live QEMU ARM64 `1024×540` `GPE0` Interactive Web Console on port `8768`** ([`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command), [`FX3菜单.command`](outputs/fx3-vm-trial/FX3菜单.command)):
  - Native `image_00_169.uxc` `LDEC103` sprite blitting & `60/60` `0 SEGV`, LRU 128-page pool (`170/170`), live **`简体中文 / 繁體中文 / EN / 日本語`** switching, FX3 `P10` button deck, `.cube` `17^3/33^3` 3D LUT uploader, 4-Ch `XLR-H1` VU meter, and 11-category / 128-page bilingual search.
  - **Phase 56** (`/api/scope_stats` 32-col IRE Waveform + 16-bin RGB Histogram, `/api/assist_tools` Zebra `70%/94%/100%`, Focus Peaking, `2.39:1..9:16` guides, `1.33x/2.0x` desqueeze, [Phase 56 Report](reports/2026-11-14-phase56-vm-trial-cinema-scopes-markers/README.md)) & **Phase 64** (`/api/cine_exposure` Dual Base `800/12800` 14.0-stop latitude, Shutter Angle `5.6°..360.0°`/Speed/`ECS`, `S&Q 1–240fps` + auto audio-mute, `STBY/REC` + Front/Rear/Off Tally Stealth, `usblan_ptpip` / `hdmi_raw16` with HTTP `400` `P4`/`P12` tamper locks, `/api/camset_export`/`import`, [Phase 64 Report](reports/2026-11-14-phase64-vm-trial-cineei-shutter-sq-tally/README.md)).

### 5. [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`61` Local Donor / `61` Clean-Room tests)
- **Rounds 1–14 (`r1a..r14d`) Real FX3 `7.02` (`4.9.337-scel+`) Kernel Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, `LDEC103` GPE physical pool sprite blitting, and multi-language `BK4 0x02cf019c -> switchBank` (`EN` `0x00`/`0,4`, `ZH-CN` `0x19`/`23,19`, `ZH-TW` `0x18`/`27,22`, `JA` `0x01`/`1,12`) achieving **`18/18` (`3 Surfaces` `Big6 Home` `sid=0x0a` / `3-Layer Menu` `sid=0x10..0x11` / `Status Check` `sid=0x2f` × `6 Language Pairs`) strictly positive (`> 0`) GPE0 pixel-diff closure** ([Round 12](reports/2026-11-14-round12-fx6-on-fx3-cjk-ja-p110-presenter/README.md), [Round 13](reports/2026-11-14-round13-fx6-on-fx3-status-4lang-closure/README.md), [Round 14](reports/2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix/README.md)).

### 6. [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`246` Local Donor / `246` Clean-Room tests)
- **9-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
  - **Stages 1–5**: Cold-boot + `virtual-rom-v1` `/dev/ttyAMA3` BT H4; Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> unmodified `ARM32` `cpapp-b.bin @ 0x00108000` (`cp_mutation_bytes = 0`); `Soft-GPE0` + `ramfb`; Pure-Py `CXD90057` FDT `0xd00dfeed` + `MmioWindowBus` + `MHLX`; `IMX510` VSYNC / `libmpr` XAVC / `RTMD 0xE304` / Dual CFexpress.
  - **Stage 6 (Ph53)**: 8-scenario HIL Fault & Thermal/`NP-FZ100`/`XLR-H1`/`C2PA` Harness ([Phase 53](reports/2026-11-14-phase53-vm-hil-fault-thermal-c2pa-harness/README.md)).
  - **Stage 7 (Ph58)**: Non-intrusive `QMP` OOB / `HMP` / `libqemu-plugin` / `GDB RSP` Tracer (`nop_count = 0`) + `USB-LAN` / `PTP-IP 15740` ([Phase 58](reports/2026-11-14-phase58-wave5-usblan-qmp-introspection-intel/README.md)).
  - **Stage 8 (Ph63)**: VESA/CEA-861 `256B` `EDID` (`ATOMOS_NINJA_RAW16` `4264x2408@59.94p`, `SMALLHD_CINE_10BIT_422` `MLUT`/Clean-Feed, `12G-SDI` no-op containment) & `USB-C` gadget arbitrator ([Phase 63](reports/2026-11-14-phase63-vm-hdmi-raw16-edid-uvc-emulator/README.md)).
  - **Stage 9 (Ph67)**: Multi-cam `SMPTE 12M` LTC `EXT-LK` PLL (`0.0`-frame 12h drift + Phase 38 `uart_boot` block), E-Mount `PZ 1..8` servo + Breathing LUT + IBIS fusion, `libpaint` `3x3` (`sum(row)==1.0`, [Phase 67](reports/2026-11-14-phase67-vm-tc-genlock-lens-paint-stage9/README.md)).

### 7. [`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`303` Local Donor / `303` Clean-Room tests)
- **13 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**:
  - `#1..#8`: Keyless `UFU`/`FDAT`/`UDTRFIRM`/`SDM2` (`5L+6S`), `ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610`-sprite CPU `LDEC`, `IMX510`/Dual ISO/XAVC, `.cube` `17^3->33^3` + `RTMD`, `WBI2`/`hibdrv` EL1 + ELF64 ABI differ, `global.xdb` `uxa\x07` 128-page menu tree.
  - `#9 (Ph51)` `audit-audio-tc-hdmi` ([Phase 51](reports/2026-11-14-phase51-audio-tc-hdmi-sdi-routing-matrix/README.md)) · `#10 (Ph55)` `audit-emount-af` ([Phase 55](reports/2026-11-14-phase55-emount-af-breathing-ibis-matrix/README.md)) · `#11 (Ph60)` `audit-shutter-tally` ([Phase 60](reports/2026-11-14-phase60-shutter-angle-ecs-sq-tally-matrix/README.md)) · `#12 (Ph65)` `audit-wb-color-look` ([Phase 65](reports/2026-11-14-global-sony-wave6-color-c2c-unbrick-intel/README.md)) · `#13 (Ph70)` `audit-proxy-clipname` (`CamID/Reel#`, `S03.MP4`, Dual-Slot, `*M01.XML` `NonRealTimeMeta ver.2.20`, [Phase 70](reports/2026-11-14-phase70-proxy-clipname-xml-sidecar-auditor/README.md)).

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
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite & Gate Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test (`make test`), 20-Gate, RP2040, init2 Escape, Post-Trial, Stage-B, VM & Lab targets
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 20-Gate (`G01..G20`), 9-Stage VM & Tier-0..4 guide
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual field/bench SOP: RP2040, Rig D-Tap/HDMI, Media/C2PA & <1s SD Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite test runner (1,601 Local / 1,543 Clean-Room) + BYOF + hygiene audit
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # 7 controlled engineering packages (1,601 Local Donor / 1,543 Clean-Room tests)
│   ├── fx3-recovery-adapter/                # Tier-0..4, Ph59 RP2040 self-test, Ph66 init2 escape/WDT, p1 VFAT & eMMC ISP (231/173)
│   ├── fx3-safety/                          # 20-Gate Master Preflight G01..G20, H0 rehearsal, WDT v2, exFAT, USB-LAN, Rig Safety (292)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B P1..P12+Fan, U1..U5, S01..S10, Ph52 Integrator & Ph62 Post-Trial Auditor (339)
│   ├── fx3-vm-trial/                        # Live QEMU port 8768 Web UI: 128p, Scopes/Assist, Cine Exposure, Shutter, S&Q, Tally (129)
│   ├── fx6-native-presenter-closure/        # Rounds 1..14 FX3 7.02 kernel GPE0 closure: nop_count=0, 18/18 4-Lang x 3-Surface (61)
│   ├── fx3-vm/                              # 9-stage Dual-ISA AP<->IVSHMEM<->CP, Soft-GPE0, HIL, QMP, EDID RAW16 & LTC/Lens/Paint (246)
│   └── fx3-firmware-lab/                    # 13 unified keyless auditors: UFU..global.xdb, Audio/TC/HDMI, AF/IBIS, Shutter, WB, Proxy (303)
├── reports/                                 # Phases 1..70 & Phase 74, Rounds 1..14, Waves 1..6 global intel & verification reports
└── conversations/                           # Categorized multi-agent engineering archives across 5 thematic workspaces
```

---

## 4. Quick Start & Verification

```bash
# 1. Run all 1,601 Local Donor tests across all 7 suites + BYOF manifest audit (57+57) + clean-room hygiene
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (1,543 tests across 7 suites, zero Sony firmware blobs — matches clean-room-ci.yml)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Phase 59..69 Safety Preflight, Bench Fixture, Escape & Post-Trial Forensic Gates (work in BOTH modes)
make verify-20-gates
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B Lifecycle Drill, Wireless Guard, Firmware Lab (13 Auditors), 9-Stage Co-Emulation & Stage-A Lifecycle targets
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
- **FX6 128-Page / Big6 / Cine EI / Scopes / S&Q / 3D LUT Interactive QEMU Console**: `./outputs/fx3-vm-trial/FX6菜单.command` -> `http://127.0.0.1:8768/`
- **FX3 Native Menu Web Console**: `./outputs/fx3-vm-trial/FX3菜单.command` (`--check` validates SHA-256 inputs without starting QEMU)

---
---

# 简体中文文档

## 一、项目总览（`Phases 1–70` · `Rounds 1–14` · `Waves 1–6`）

**`sony-fx3-fx6-lab`** 围绕 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 开展净室系统工程、多架构 QEMU 协同仿真、跨机型固件兼容适配与真机防变砖安全研究。两款机型均基于 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

历经 **`Phases 1–70`**、**`Rounds 1–14`** 与 **`Waves 1–6` 全球公开情报同步** 迭代，实验室已构建起 **7 大统一自动化测试套件（`make test` 本地供体全量 `1,601` 项通过 / `FX3_FX6_FORCE_CLEAN_ROOM=1` 无供体洁净室 `1,543` 项全绿通过）**：
- **Stage-B 易失性 RAM 覆盖层（`P1..P12+Fan`，`13/13` 挂载前校验）**：涵盖 `P10` FX3 实体按键映射、`P11` AP 侧 UIPC-CP 垫片（保留 `XLR-H1` 热靴音频与 5 轴 IBIS 居中锁止）、`P12` `WF-12` 无线断环补丁、`< 48 MiB` SVR4 `070701` CPIO 打包器、Phase 52 五轨候选集成简报（`< 5s`）与 Phase 62 `16` 表面 `H0 == H2` 试后零持久化法证审计。
- **20 门禁主安全预检引擎（`G01..G20`）与 `Tier-0..Tier-4` 救砖阶梯（`S01..S12`）**：刚性锁定 **C2PA**（`RQ_LIC.DAT`/`sigcert.p12`）与出厂校准不可变性、`exFAT` 掉电卫生与客户素材防火墙（`G17`）、有线 `USB-LAN CDC-NCM` + `PTP-IP 15740` 与 `P12` 飞行共存（`G18`）、电影套件 D-Tap/铜 HDMI 地环路互锁与 E 卡口 `<= 2.0ms` 撬棍断流（`G19`）、`NP-FZ100 >= 15%` UPS 冗余与 `.RSV` 只读抢救（`G20`）、`RP2040-Zero -DOPEN_DRAIN` 断机治具自检（`Phase 59`），以及 `< 1s` `FX3_SAFE_STOCK.FLG` 四层 `init2` 逃生与 `CXD90057` WDT `10,000ms` 破环（`Phase 66`）。
- **端口 `8768` 实时交互式 QEMU 控制台（`FX6菜单.command`）、9 阶段全板协同仿真（`fx3-vm`）、13 大无密钥固件审计器（`fx3-firmware-lab`）与 `Rounds 1–14`（`18/18` 四语×三界面 `nop_count = 0`）**：支持双原生 ISO `800/12800` Cine EI、IRE 波形/直方图/斑马纹/峰值、快门角/`ECS`、`S&Q 1–240fps`、Tally 隐身、`HDMI RAW16`/`USB-LAN`、`QMP`/`libqemu-plugin` 自省、`SMPTE 12M` LTC `EXT-LK`、`OCIO v2`/`ACES` 与 `CamID/Reel#`/`*M01.XML` 审计。

架构细节与现场操作规范请参见 **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** 与 **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**。

---

## 二、七大统一测试套件明细（`make test` — 本地供体 `1,601` 项 / 洁净室 `1,543` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `231` / 洁净室 `173` 项测试）**：**Phase 66** 4 层 `<1s` `FX3_SAFE_STOCK.FLG` `init2` SD 逃生 + `CXD90057` WDT `10,000ms` 破环 + `p1` `FAT12/16` 链与 `INIT2.SH↔INIT2BAK.SH` 交换（`make verify-init2-escape`）、**Phase 59** `RP2040-Zero -DOPEN_DRAIN` 断机治具自检（`make verify-rp2040-fixture`）、`Tier-0..Tier-4` 救砖阶梯（`S01..S12`）、`p1` VFAT 胶囊、偏移 VMA `v7.02` `p1` 4 锚点自动定位、macOS 26 `IOUSBHost` 与 `O_RDONLY` eMMC ISP 取证。
2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `292` 项测试）**：**`G01..G20` 20 门禁主安全预检引擎**（`make verify-20-gates`）涵盖 `G01..G16` 基础红线、**Phase 57** `exFAT` `BootChecksum`/`.RSV` 防火墙（`G17`）、**Phase 61** 有线 `USB-LAN CDC-NCM` + `PTP-IP 15740` 安全防火墙（`G18`）、**Phase 69** D-Tap/HDMI 地环路互锁、E 卡口 `2.0ms` 断流+IBIS 居中停靠（`G19`）与 `NP-FZ100 >= 15%` UPS / `.RSV` 审计（`G20`）。
3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `339` 项测试）**：Stage-A（`P1..P9+Fan`）+ Stage-B（`P1..P12+Fan` `13/13` 补丁）：`P10` 物理按键映射、`P11` `Uipc/CP` 手柄垫片（保留 `XLR-H1` 与 5 轴 IBIS）、`P12` `WF-12` 断环补丁 + `BK4\0` 飞行/中文影子、`U1..U5` 全清零、`S01..S10` 生命周期、`070701` CPIO + `9/9` `init2`、**Phase 52** 五轨候选集成简报与 **Phase 62** `16` 表面 `H0==H2` 试后法证审计（`make verify-post-trial-audit`）。
4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `129` 项测试）**：端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 控制台：原生 `LDEC103` 图标与 `60/60` 零崩溃、LRU 128 页四语池、`.cube` LUT、4 通道 `XLR-H1` VU、128 页搜索、**Phase 56** IRE 波形/RGB 直方图/斑马纹/峰值对焦/画幅参考线/变形反挤压与 **Phase 64** 双原生 ISO `800/12800` Cine EI、快门角 `5.6°..360°`/`ECS`、`S&Q 1–240fps` 自动静音、Tally 隐身、`USB-LAN`/`HDMI RAW16` 与 `CAMSET` 往返。
5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `61` 项测试）**：**Rounds 1–14（`r1a..r14d`）** FX3 `7.02` 原厂 `4.9.337-scel+` 内核混合态真机实跑（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`），完成 **`EN / ZH-CN / ZH-TW / JA` 四语种 × `Big6 主页` (`0x0a`) / `三级全菜单` (`0x10..0x11`) / `Status Check` (`0x2f`) 共 `18/18` 对跨语种像素差分严格全正（`> 0`）全矩阵闭环**。
6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `246` 项测试）**：**9 阶段全板级虚拟相机协同仿真（`make verify-coemulation`）**：Stage 1–5（BT、双核 `AArch64` AP ↔ `IVSHMEM` ↔ 原厂 `ARM32` `cpapp-b.bin`、`Soft-GPE0`、纯 Py FDT + `MHLX`、`IMX510`/XAVC/CFexpress）+ **Stage 6（Ph53）** 8 场景 HIL 故障台 + **Stage 7（Ph58）** `QMP`/`HMP`/`libqemu-plugin`/`GDB RSP` 非侵入自省 + **Stage 8（Ph63）** `256B` `EDID` `HDMI RAW16`/`MLUT` & `USB-C` 仲裁 + **Stage 9（Ph67）** 多机 `SMPTE 12M` LTC `EXT-LK` PLL（12h `0.0` 帧漂移）+ E 卡口 `PZ` 伺服/呼吸补偿 + `libpaint` `3×3` 矩阵。
7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `303` 项测试）**：**13 大洁净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：前 8 项（`UFU`/`SDM2`、`HAITA`/`BK4`、62 包 29 语 `.uxc` + 6 套 CJK 字体 + 1,610 精灵 `LDEC`、`IMX510`/XAVC、`.cube` + `RTMD`、`WBI2`/ELF64 ABI、`global.xdb`）+ **#9（Ph51）** `XLR-H1`/TC/`HDMI RAW16` + **#10（Ph55）** E 卡口 `PZ`/627 点 PDAF/呼吸补偿/5 轴 IBIS + **#11（Ph60）** 机械快门保护/快门角/`ECS`/`S&Q`/Tally + **#12（Ph65）** 白平衡/`OCIO v2` & `ACES`/`3×3` Paint 矩阵 + **#13（Ph70）** `CamID/Reel#`/`S03.MP4` 代理/双卡四模式/`*M01.XML` 伴随元文件。

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
# 1. 运行全部 7 套 1,601 项本地供体测试 + BYOF 双语清单审计 (57+57) + git 净室零残留审计
make test
make test-json

# 2. 本地模拟无供体洁净室 CI (7 套 1,543 项测试，零索尼固件依赖，与 GitHub Actions 完全一致)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Phase 59..69 安全预检、断机治具自检、SD 瞬时逃生与试后法证门禁（双模式通用）
make verify-20-gates
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B 生命周期演练、无线防护、固件实验室（13 审计器）、9 阶段协同仿真与 Stage-A 演练命令
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
- **FX6 128 页 / Big6 / Cine EI / 示波器 / S&Q / 3D LUT 实时控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入 SHA-256）。

---

## 四、多智能体归档与开源协议 (Archives & License)

- **工程对话归档**：5 大专题工作区多智能体研究对话已按净室规范分类归档至 **[conversations/README.md](conversations/README.md)**。
- **免责与开源协议**：本仓库包含 **0 字节** 索尼专有二进制固件或私有密钥，与 Sony Group Corporation 无任何隶属或合作关系。自研源码采用 MIT 协议，QEMU 补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
