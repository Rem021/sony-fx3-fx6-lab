# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-20--Gate_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-Tier--0..4_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-1,601_Local_%7C_1,543_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r14d_(18%2F18)-success?style=flat)](#the-7-unified-verification-suites-make-test--1601-local-donor--1543-clean-room)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#5-legal--clean-room-compliance-notice)

> **Switch Language / Deep Reference**: [**👉 简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master (`README.md`)**](./README.md) · [**Stage-B Architecture & 20-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** digital cinema cameras, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> Persistent hardware flashing remains **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), and `calibration_mutation_bytes = 0`. Every Stage-A and Stage-B overlay operates strictly in volatile Linux DDR (`tmpfs`), accesses donor blobs strictly via `os.O_RDONLY`, supports `< 1s` zero-cable `FX3_SAFE_STOCK.FLG` SD escape, and reverts cleanly to 100% stock Sony ILME-FX3 `Ver. 7.02` on power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images) and **0 vendor AES/RSA private keys**. All `7` verification suites (`1,543` clean-room tests) plus `20-Gate`, `RP2040`, `init2`, and `Post-Trial` CLI gates execute cleanly in donorless mode (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) on `ubuntu-latest` + `macos-latest` via [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing interactive VM sessions with your own official firmware files.

---

## 1. Engineering Milestones (`Phases 1–70` · `Rounds 1–14` · `Waves 1–6`)

### The 7 Unified Verification Suites (`make test` — `1,601` Local Donor / `1,543` Clean-Room)

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`231` Local Donor / `173` Clean-Room tests)**
   - **Phase 66 `init2` SD-Sentinel (`FX3_SAFE_STOCK.FLG` `< 1s`), `CXD90057` WDT `10,000ms` Breaker & `p1` `FAT12/16` Verifier** ([`init2_escape_and_watchdog_simulator.py`](outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [Phase 66 Report](reports/2026-11-14-phase66-init2-escape-watchdog-fat-verifier/README.md), `make verify-init2-escape`): Proves 4-layer fail-open escape before `mount --bind`, atomic `INIT2.SH <-> INIT2BAK.SH` 32B directory swap, and `H0 == H2` WDT rollback.
   - **Phase 59 Camera-Disconnected `RP2040-Zero -DOPEN_DRAIN` Bench Self-Test** ([`rp2040_multiport_fixture_selftest.py`](outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [Phase 59 Report](reports/2026-11-14-phase59-rp2040-multiport-fixture-selftest/README.md), `make verify-rp2040-fixture`): Verifies `[1.71, 1.89V]` pull-up, `>= 1 MOhm` rail isolation, and `48,000`-baud PIO fractional divider `<= 0.0004%` error before connecting to any camera.
   - **Tier-0..Tier-4 Unbrick Ladder (`S01..S12`), `p1` VFAT Capsule, Shifted-VMA `v7.02` `p1` Autolocator, macOS 26 `IOUSBHost` & `O_RDONLY` eMMC ISP Verifier** ([Phase 47](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md), [Phase 42](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)), plus freestanding static AArch64 capture workers.

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/) (`292` Local Donor / `292` Clean-Room tests)**
   - **20-Gate Master Safety Preflight Engine (`G01..G20`, `make verify-20-gates`)**: Composes `preflight.py` (`G01..G12`) + [`master_16gate_preflight.py`](outputs/fx3-safety/fx3_safety/master_16gate_preflight.py) (`G13..G16`) + **Phase 57** [`exfat_media_integrity_guard.py`](outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py) (`BootChecksum`, `VolumeDirty=0`, `XDROOT`/`M4ROOT`/`.RSV`) + **Phase 61** [`usblan_ptpip_and_18gate_preflight.py`](outputs/fx3-safety/fx3_safety/usblan_ptpip_and_18gate_preflight.py) (`G17` exFAT/client media firewall & `G18` wired `USB-LAN CDC-NCM` + `PTP-IP 15740` + `P12` Airplane coexistence) + **Phase 69** [`rig_groundloop_lensrail_and_20gate_guard.py`](outputs/fx3-safety/fx3_safety/rig_groundloop_lensrail_and_20gate_guard.py) (`G19` D-Tap/copper HDMI ground-loop & E-Mount `<= 2.0ms` `V_LENS` crowbar + Stock-CP `0x0400` IBIS park; `G20` `NP-FZ100 >= 15%` UPS reserve + read-only `.RSV` salvage).
   - **Hardware Guardrails & Rehearsal**: Includes 6-stage `H0` rehearsal (`--unicorn`), `serial_fault_detector_v2`, `RP2040-Zero -DOPEN_DRAIN` & `VMC-BNCM1` LTC firewall, `CrSDK` PTP2, MI-Shoe `XLR-H1`, `CXD90057 SPACC` AES-XTS-256 guard, FX3 Fan PWM (`libfan.so @ 0x1dec`) + `NP-FZ100`/`USB-PD 9V/3A` guards, and runtime anti-brick guards.

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`339` Local Donor / `339` Clean-Room tests)**
   - **Stage-A (`P1..P9+Fan`) & Stage-B (`P1..P12+Fan`, `13/13` lock-table, `8` ELF/module targets / `18` sites, 100% SHA-256 rollback)**: `P10` 24B FX3 button remap (`e2bc2619...`), `P11` AP-side UIPC-CP shim preserving `XLR-H1` & 5-axis IBIS center-lock, and `P12` `libWlanResource.so @ 0x70d4` (`47fec188...`) `WF-12` bootloop immunity + `BK4\0` Airplane/CJK shadow.
   - **Full Blueprint, Integration & Post-Trial Forensics**: Closes **`U1..U5`**, `60`-ELF `.dynsym` + `137` `/dev/*` + `.ko` linkage, **`S01..S10` Stage-B lifecycle drill**, **Phase 48 SVR4 `070701` Packager (`9/9` `init2`)**, **Phase 52 Unified Candidate Integrator** (`stage_b_integrated_dossier_v1`, `< 5s`, [Phase 52 Report](reports/2026-11-14-phase52-stage-b-candidate-integrator/README.md)), and **Phase 62 `16`-Surface `H0 == H2` Post-Trial Forensic Auditor** (`make verify-post-trial-audit`, [Phase 62 Report](reports/2026-11-14-phase62-stage-b-post-trial-forensic-auditor/README.md)).

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`129` Local Donor / `129` Clean-Room tests)**
   - **Live QEMU ARM64 `1024×540` `GPE0` Web Console (`127.0.0.1:8768`, [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command))**: Authentic `image_00_169.uxc` `LDEC103` icons & `60/60` `0 SEGV`, LRU 128-page pool (`170/170`), live **`简体中文 / 繁體中文 / EN / 日本語`** switching, FX3 `P10` deck, `.cube` `17^3/33^3` 3D LUT uploader, 4-Ch `XLR-H1` VU meter, `RTMD 0xE304`, 11-cat/128-page search, **Phase 56** IRE Waveform/RGB Histogram/Zebra/Peaking/Guides/Desqueeze ([Phase 56](reports/2026-11-14-phase56-vm-trial-cinema-scopes-markers/README.md)), and **Phase 64** Dual Base `800/12800` Cine EI, Shutter Angle `5.6°..360.0°`/`ECS`, `S&Q 1–240fps` + auto audio-mute, Tally Stealth, `usblan_ptpip`/`hdmi_raw16` with HTTP `400` `P4`/`P12` tamper locks, and `CAMSET` round-trip ([Phase 64](reports/2026-11-14-phase64-vm-trial-cineei-shutter-sq-tally/README.md)).

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`61` Local Donor / `61` Clean-Room tests)**
   - **Rounds 1–14 (`r1a..r14d`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, `LDEC103` physical pool sprite blitting, and multi-language `BK4 0x02cf019c -> switchBank` (`EN`, `ZH-CN`, `ZH-TW`, `JA`) achieving **`18/18` (`3 Surfaces` `Big6 Home` `0x0a` / `3-Layer Full Menu` `0x10..0x11` / `Status Check` `0x2f` × `6 Language Pairs`) strictly positive (`> 0`) GPE0 pixel-diff closure** ([Round 12](reports/2026-11-14-round12-fx6-on-fx3-cjk-ja-p110-presenter/README.md), [Round 13](reports/2026-11-14-round13-fx6-on-fx3-status-4lang-closure/README.md), [Round 14](reports/2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix/README.md)).

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`246` Local Donor / `246` Clean-Room tests)**
   - **9-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**: Stages 1–5 (`virtual-rom-v1` `/dev/ttyAMA3` BT, Dual-ISA `AArch64` AP <-> `IVSHMEM` <-> `ARM32` unmodified `cpapp-b.bin`, `Soft-GPE0` + `ramfb`, Pure-Py `CXD90057` FDT `0xd00dfeed` + `MHLX`, `IMX510`/XAVC/`RTMD`/Dual CFexpress); **Stage 6 (Ph53)** 8-scenario HIL fault harness ([Phase 53](reports/2026-11-14-phase53-vm-hil-fault-thermal-c2pa-harness/README.md)); **Stage 7 (Ph58)** non-intrusive `QMP`/`HMP`/`libqemu-plugin`/`GDB RSP` tracer (`nop_count = 0`) + `USB-LAN`/`PTP-IP 15740` ([Phase 58](reports/2026-11-14-phase58-wave5-usblan-qmp-introspection-intel/README.md)); **Stage 8 (Ph63)** `256B` `EDID` (`ATOMOS_NINJA_RAW16`/`SMALLHD_CINE_10BIT_422` `MLUT`/Clean-Feed/`12G-SDI` no-op) & USB-C arbitrator ([Phase 63](reports/2026-11-14-phase63-vm-hdmi-raw16-edid-uvc-emulator/README.md)); **Stage 9 (Ph67)** `SMPTE 12M` LTC `EXT-LK` PLL (`0.0`-frame 12h drift), E-Mount `PZ 1..8`/Breathing/IBIS, and `libpaint` `3x3` (`sum(row)==1.0`, [Phase 67](reports/2026-11-14-phase67-vm-tc-genlock-lens-paint-stage9/README.md)).

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`303` Local Donor / `303` Clean-Room tests)**
   - **13 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**: `#1..#8` (`UFU`/`SDM2`, `HAITA`/`BK4`, `62` `.uxc` + `6` CJK fonts + `1,610`-sprite CPU `LDEC`, `IMX510`/Dual ISO/XAVC, `.cube` `17^3->33^3` + `RTMD`, `WBI2`/`hibdrv` EL1 + ELF64 `.dynsym`, `global.xdb` 128p menu tree) + `#9 (Ph51)` `audit-audio-tc-hdmi` ([Phase 51](reports/2026-11-14-phase51-audio-tc-hdmi-sdi-routing-matrix/README.md)) + `#10 (Ph55)` `audit-emount-af` ([Phase 55](reports/2026-11-14-phase55-emount-af-breathing-ibis-matrix/README.md)) + `#11 (Ph60)` `audit-shutter-tally` ([Phase 60](reports/2026-11-14-phase60-shutter-angle-ecs-sq-tally-matrix/README.md)) + `#12 (Ph65)` `audit-wb-color-look` ([Phase 65](reports/2026-11-14-global-sony-wave6-color-c2c-unbrick-intel/README.md)) + `#13 (Ph70)` `audit-proxy-clipname` ([Phase 70](reports/2026-11-14-phase70-proxy-clipname-xml-sidecar-auditor/README.md)).

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
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows; `v7.02` `p1` resolved via 4-site AArch64 `ADRP/BL` autolocator; `p1` `FAT12/16` atomic swap audited by Phase 66. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 `7.02` and FX6 `6.01` (`@ 0xFE049000`); Tier-3 BootROM `48000`-baud recovery strictly requires `RP2040-Zero -DOPEN_DRAIN` verified camera-disconnected (`make verify-rp2040-fixture`). |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; `p2:/setting/{psd,defdet}.bin`, `p6:Jiritsu`, `p12:/cert` (C2PA `RQ_LIC.DAT`), and `p18:/lens/lensfile.bin` remain hard-locked read-only (`G15`). |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Stage-A & Stage-B keep stock FX3 kernel, stock `p8:/cpapp-b.bin` (`@ 0x00108000`, `cp_mutation_bytes = 0`), and `p5:/wbi` hibernation blocked (`wbi_mutation_bytes = 0`). |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A (`30-stage-a-orchestrator.sh`) & Stage-B (`stage_b_init2_guard.sh`) check `FX3_SAFE_STOCK.FLG` first (`< 1s` instant escape), verify `13/13` SHA-256 digests before mount, activate volatile `tmpfs` (`< 48 MiB` + `ro_sd_loop_bind`, `0` eMMC/WBI/CP writes), and unwind in reverse LIFO (`H0 == H2`). |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite & Gate Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test, 20-Gate, RP2040, init2 Escape, Post-Trial, Stage-B, VM, Lab & BYOF targets
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 20-Gate (`G01..G20`), 9-Stage VM & Tier-0..4 reference
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual field/bench SOP: RP2040, Rig D-Tap/HDMI, Media/C2PA & <1s SD Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite runner (1,601 Local / 1,543 Clean-Room) + BYOF audit + hygiene check
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
└── conversations/                           # Categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Unified Test Suite, Clean-Room CI, 20-Gate, Recovery, Stage-B, Firmware Lab & Co-Emulation Targets

```bash
# 1. Run all 1,601 Local Donor tests across all 7 suites (231 + 292 + 339 + 129 + 61 + 246 + 303) + BYOF (57+57) + hygiene check
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (1,543 tests across 7 suites, zero Sony firmware blobs — identical to GitHub Actions)
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

### 4.2 Launch Interactive FX3 or FX6 Web Menu Emulators (Requires BYOF Setup)

After preparing your own official firmware files per **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**:
- **FX6 128-Page / Big6 / Cine EI / Scopes / S&Q / 3D LUT / Multilingual Web Console**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under the MIT license; QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
