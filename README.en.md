# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Stage-B Architecture & Safety](https://img.shields.io/badge/Stage--B_Arch_%26_Safety-40--Gate_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![Operator SOP & Unbrick](https://img.shields.io/badge/Operator_SOP_%26_Unbrick-13--Pillar_%7C_EN_%2B_ZH-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-3,743_Local_%7C_3,685_Clean--Room_(7_Suites)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r24e_(18%2F18%2B45%2F45%2B55%2F55%2B60%2F60)-success?style=flat)](#the-7-unified-verification-suites-make-test--3743-local-donor--3685-clean-room)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#5-legal--clean-room-compliance-notice)

> **Switch Language / Deep Reference**: [**👉 简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master (`README.md`)**](./README.md) · [**Stage-B Architecture & 40-Gate Safety (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**Operator SOP & Unbrick Runbook (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** digital cinema cameras, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

> [!CAUTION]
> **STRICT HARDWARE FLASH LOCK (`persistent_emmc_writes_authorized = False` / `NO-GO` FOR PERSISTENT FLASHING)**  
> Persistent hardware flashing & live attach remain **hard-locked OFF (`NO-GO`)**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `hardware_live_attachment_authorized = False`, `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`), `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`), `calibration_mutation_bytes = 0`, `otp_fuse_touches = 0`, `rpmb_counter_increments = 0`, `emmc_flash_mutation_bytes = 0`, and `passive_tx_bytes_emitted = 0`. Every Stage-A and Stage-B overlay operates strictly in volatile Linux DDR (`tmpfs`), accesses donor blobs strictly via `os.O_RDONLY`, supports `< 1s` zero-cable `FX3_SAFE_STOCK.FLG` SD escape, and reverts cleanly to 100% stock Sony ILME-FX3 `Ver. 7.02` on power-cycle.

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**  
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images) and **0 vendor AES/RSA private keys**. All `7` verification suites (`3,685` clean-room tests) plus `Milestone Phase 130 Master Gate`, `40-Gate`, `13-Pillar Recovery`, `Milestone Phase 110`, `32-Gate`, `Milestone Phase 90`, `24-Gate`, `RP2040`, `init2`, `Tier-0 GF(256)`, `OTP/RPMB Anti-Rollback`, and `Post-Trial` CLI gates execute cleanly in donorless mode (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) on `ubuntu-latest` + `macos-latest` via [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing interactive VM sessions with your own official firmware files.

---

## 1. Engineering Milestones (`Phases 1–130` · `Rounds 1–24` · `Waves 1–14`)

### The 7 Unified Verification Suites (`make test` — `3,743` Local Donor / `3,685` Clean-Room)

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`557` Local Donor / `499` Clean-Room tests)**
   - **13-Pillar Recovery Master Suite (`make verify-13pillar-recovery`)**: Composes all `10` foundational & Phase 94/101/106 recovery pillars (`macOS IOUSBHost`, `RP2040-Zero -DOPEN_DRAIN` `make verify-rp2040-fixture`, `< 1s` `FX3_SAFE_STOCK.FLG` `init2` escape + WDT `make verify-init2-escape`, `GF(256)` RAID-6 Tier-0 healer `make verify-tier0-backup`, `OTP/RPMB` anti-rollback `make verify-antirollback-guard`, `Tier-0..Tier-4` ladder, passive `1.8V` RX-only UART `S0..S6` `passive_tx_bytes_emitted == 0`, GPT CRC32/RPMB replay, SVR4 `newc` cpio/`EXT_CSD[267..269]` Pre-EOL, and FDT `/chosen/bootargs` `ro`/ARM64 `Image`) **plus** **Pillar 11 (Ph113)** Dual-Bank A/B & interrupted `BODYDATA.DAT` OTA triage ([Phase 113 Report](reports/2026-11-14-phase113-ab-bank-interrupted-ota-recovery/README.md)), **Pillar 12 (Ph119)** SquashFS `4.0` `hsqs` & Warp-Boot `hibdrv` `WBI2` triage ([Phase 119 Report](reports/2026-11-14-phase119-squashfs-wbi-hibdrv-recovery/README.md)), and **Pillar 13 (Ph124)** Mask-BootROM USB & JEDEC eMMC `BOOT0/BOOT1` `EXT_CSD[179/177/173/226]` triage ([Phase 124 Report](reports/2026-11-14-phase124-bootrom-usb-emmc-bootpart-recovery/README.md)).

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/) (`665` Local Donor / `665` Clean-Room tests)**
   - **40-Gate Master Safety Preflight Engine (`G01..G40`, `make verify-40-gates`)**: Extends `G01..G32` (`make verify-32-gates`) with **Phase 108** (`G33` coastal salt-spray/alkali dust/glycol haze, `G34` wireless follow-focus torque & telescoping-zoom gimbal CoG, [Phase 108](reports/2026-11-14-phase108-saltspray-followfocus-34gate-safety/README.md)), **Phase 115** (`G35` HDMI AOC Pin-18 `+5V` backfeed & leverage shear, `G36` CFexpress VPG sustained write/NVMe thermal/door-open flush, [Phase 115](reports/2026-11-14-phase115-safety-hdmi5v-cfexpress-36gates/README.md)), **Phase 120** (`G37` `20V` USB-C PD decoy/dual-power cross-feed/UVC 4K30p thermal saturation, `G38` 15-pin Multi-Terminal `LTC`/`3.3V` UART/`CRSDK` PTP flash firewall, [Phase 120](reports/2026-11-14-phase120-safety-usbpd-multiterminal-38gates/README.md)), and **Phase 125** [`monsoon_mishoe_cagetwist_and_40gate_guard.py`](outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py) (`G39` wet 24-pin MI-Shoe rain galvanic short & open side-flap capillary ingress, `G40` `XLR-H1` whip shear/`1/4"-20 > 3.5 N*m` thread strip/asymmetric cage-twist `18.00 mm` E-Mount FFD warpage — `37/40` offline truthful block vs `40/40` simulated rehearsal, [Phase 125](reports/2026-11-14-phase125-safety-monsoon-mishoe-cagetwist-40gates/README.md)).

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`559` Local Donor / `559` Clean-Room tests)**
   - **Milestone Phase 130 6-Pillar Master Gate ([`stage_b_milestone130_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone130_master_gate.py), `make verify-milestone-130`, `< 2.5s`)**: Unifies all 6 Milestone-130 pillars (`40-Gate`, `13-Pillar Recovery`, `>= 24` Firmware-Lab Auditors, `>= 21` VM Stages, `Round 14 (18/18)` + `Round 17 (10/10 Status 45/45)` + `Round 19 (11/11 Menu 55/55)` + `Rounds 20–24 (5/5 60/60)` real FX3 `7.02` closures, and `H0 == H2` 16-surface immutability + hardware lock invariants) with deterministic `milestone130_sha256` ([Phase 130 Report](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)).
   - Preserves **Phase 110 Master Gate (`make verify-milestone-110`)**, **Phase 90 Master Gate (`make verify-milestone-90`)**, **Stage-A (`P1..P9+Fan`)**, **Stage-B (`P1..P12+Fan`, `13/13` lock-table)**, **`U1..U5`**, **`S01..S10` lifecycle drill**, **Phase 52/76 Candidate Integrator & Dossier v3**, and **Phase 62/68/83 Capstone `H0 == H2` Forensic Auditor** (`make verify-post-trial-audit`).

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`367` Local Donor / `367` Clean-Room tests)**
   - **Live QEMU ARM64 `1024×540` `GPE0` Web Console (`127.0.0.1:8768`, [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command))**: Authentic `LDEC103` icons (`60/60` `0 SEGV`), LRU 128-page 4-language pool (`简体中文 / 繁體中文 / EN / 日本語`), FX3 `P10` deck, 4-Ch `XLR-H1` VU meter, **Phases 56..102** (Scopes, Cine EI, Touch AF/`x4`/False Color/`CIZ`, Gyroflow/Anamorphic/Tone, Picture Cache/Interval/`.cube`/FTPS), **Phase 109** (`'MCFL'` Monitor & Control 4-Cam wired Gang-REC + HDMI->12G-SDI `AVI`/`RP 188` + E-Mount/PL shading + `C2PA 2.1` zero-touch provenance HUD, [Phase 109](reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md)), **Phase 116** (`'HLGA'` `HLG1/2/3 BT.2100` + `Display Assist` clean-feed + `CTA-861.3 (0x87)` + `ProRes RAW`/`BRAW` + Focus Breathing HUD, [Phase 116](reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md)), and **Phase 123** (`'UVCS'` USB-C `UVC 1.5/UAC 2.0` + wired `P12`-safe `SRT/RTMPS TLS 1.3` + `CRSDK PTP` flash-opcode firewall HUD, [Phase 123](reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md)).

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`198` Local Donor / `198` Clean-Room tests)**
   - **Rounds 1–24 (`r1a..r24e`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, **R14 `18/18`**, **R17 `10/10` Status Check (`45/45` `>0`)**, **R19 `11/11` Full-Menu (`55/55` `>0`)**, **plus five 4-language (`EN/JA/ZH-CN/ZH-TW`) `12/12` dual-surface closures** in **Round 20 (`Network` + WF-12)**, **Round 21 (`Audio`)**, **Round 22 (`Paint/Look` & `Camera`)**, **Round 23 (`Monitoring`)**, and **Round 24 (`Project`)** -> **`60/60` multilingual pairs strictly `> 0`** across 27 runs ([Round 20](reports/2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure/README.md), [Round 21](reports/2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure/README.md), [Round 22](reports/2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure/README.md), [Round 23](reports/2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure/README.md), [Round 24](reports/2026-11-14-round24-fx6-on-fx3-project-4lang-dualsurface-closure/README.md)).

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`684` Local Donor / `684` Clean-Room tests)**
   - **21-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
     - **Stages 1–18 (`Phases 24–107`)** plus **Stage 19 (Ph112)** `HLG/BT.2100`, Display Assist & FIZ/Gimbal HIL ([Phase 112](reports/2026-11-14-phase112-vm-stage19-hdr-hlg-gimbal-fiz-hil/README.md)), **Stage 20 (Ph117)** `ProRes RAW`/`BRAW`, Focus Breathing & MI-Shoe I2S/AOC `+5V` HIL ([Phase 117](reports/2026-11-14-phase117-vm-stage20-proresraw-breathing-mishoe-hil/README.md)), and **Stage 21 (Ph121)** USB-C `UVC/UAC`, Wired `SRT/RTMPS`, `CRSDK PTP` Firewall & `20V` USB-PD Decoy HIL (`wf12_00342260_hits=0`, `emmc_flash_mutation_bytes=0`, [Phase 121](reports/2026-11-14-phase121-vm-stage21-uvc-srt-crsdk-usbpd-hil/README.md)).

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`713` Local Donor / `713` Clean-Room tests)**
   - **24 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**: `#1..#20` (`UFU`..`C2PA 2.1`/Lens Shading/MC Fleet) + **`#21 (Ph111)`** `HLG/BT.2100/Display Assist` ([Phase 111](reports/2026-11-14-phase111-hdr-hlg-bt2100-display-assist-auditor/README.md)) + **`#22 (Ph114)`** `ProRes RAW/BRAW/Breathing/MI-Shoe Clock` ([Phase 114](reports/2026-11-14-phase114-proresraw-breathing-mishoe-auditor/README.md)) + **`#23 (Ph118)`** `UVC/UAC/SRT/RTMPS/CRSDK PTP` ([Phase 118](reports/2026-11-14-phase118-uvc-srt-crsdk-ptp-auditor/README.md)) + **`#24 (Ph122)`** `MXF OP1a/MP4 RDD-18/PTPv2/TSL UMD v5.0` ([Phase 122](reports/2026-11-14-phase122-mxf-mp4-ptpv2-tally-auditor/README.md)).

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
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows; `v7.02` `p1` resolved via 4-site AArch64 `ADRP/BL` autolocator; `p1` `FAT12/16` swap audited by Phase 66; Phase 79/94/113 block `OTP`/`RPMB` & interrupted A/B OTA bricks. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 `7.02` and FX6 `6.01` (`@ 0xFE049000`); Tier-0 protected by `GF(256)` RAID-6 (`Phase 72`); Tier-3 BootROM `48000`-baud recovery uses `RP2040-Zero -DOPEN_DRAIN` (`make verify-rp2040-fixture`), Phase 124 USB/`BOOT0..1` gate & passive RX-only UART (`tx_bytes = 0`). |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; `p2:/setting/{psd,defdet}.bin`, `p6:Jiritsu`, `p12:/cert` (`C2PA 2.1` `RQ_LIC.DAT`), and `p18:/lens/lensfile.bin` remain hard-locked read-only (`G15`, `Ph105`). |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Phase 106/119 lock FDT `/chosen/bootargs` `ro`, ARM64 `0x644d5241`, SquashFS `hsqs`, & `WBI2`; Stage-A & Stage-B keep stock FX3 kernel, stock `p8:/cpapp-b.bin` (`cp_mutation_bytes = 0`), and `p5:/wbi` blocked (`wbi_mutation_bytes = 0`). |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A & Stage-B (`stage_b_init2_guard.sh`) check `FX3_SAFE_STOCK.FLG` first (`< 1s` instant escape), verify `13/13` SHA-256 digests before mount, enforce `40-Gate` + `EXT_CSD[267..269]`/`[179/177/173/226]` locks, activate volatile `tmpfs` (`< 48 MiB`), and unwind in reverse LIFO (`H0 == H2`). |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite, 40-Gate, 13-Pillar & Milestone-130 CI
├── Makefile                                 # Unified test, Milestone-130, 40-Gate, 13-Pillar, M110/M90, VM & Lab
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 40-Gate (`G01..G40`), 21-Stage VM & 13-Pillar ref
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V, TEC, Salt-Spray/AOC, USB-PD Decoy, Monsoon & Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite runner (3,743 Local / 3,685 Clean-Room) + BYOF audit + hygiene check
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # 7 controlled engineering packages (3,743 Local Donor / 3,685 Clean-Room tests)
│   ├── fx3-recovery-adapter/                # 13-Pillar Recovery: Tier-0..4, RP2040, init2, GF(256), OTP/RPMB, UART, A/B, WBI2, BootROM (557/499)
│   ├── fx3-safety/                          # 40-Gate Master Preflight G01..G40 (Salt-Spray, FIZ, AOC 5V, NVMe, USB-PD, Monsoon MI-Shoe, FFD) (665)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B, Ph52/76 Dossier v3, M90/110, Milestone Phase 130 6-Pillar Master Gate (559)
│   ├── fx3-vm-trial/                        # Live port 8768 Web UI: 128p, Scopes, Cine EI, M&C Fleet, HLG BT.2100/RAW, UVC/SRT/CRSDK (367)
│   ├── fx6-native-presenter-closure/        # Rounds 1..24 FX3 7.02 kernel GPE0: nop_count=0, R14/R17/R19 + R20..24 5/5 60/60 (198)
│   ├── fx3-vm/                              # 21-stage Dual-ISA AP<->IVSHMEM<->CP co-emulation through HLG/RAW/UVC/SRT/CRSDK (684)
│   └── fx3-firmware-lab/                    # 24 unified keyless auditors: UFU..C2PA 2.1, HLG, ProRes/BRAW, UVC/SRT/CRSDK, MXF/PTPv2 (713)
├── reports/                                 # Phases 1..130, Rounds 1..24, Waves 1..14 global intel & verification reports
└── conversations/                           # Categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Unified Test Suite, Clean-Room CI, Milestone-130, 40-Gate, 13-Pillar Recovery, Firmware Lab & Co-Emulation Targets

```bash
# 1. Run all 3,743 Local Donor tests across all 7 suites (557 + 665 + 559 + 367 + 198 + 684 + 713) + BYOF (57+57) + hygiene check
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (3,685 tests across 7 suites, zero Sony firmware blobs — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 130 6-Pillar Master Gate (< 2.5s) + 40-Gate + 13-Pillar Recovery + Legacy Gates (BOTH modes)
make verify-milestone-130
make verify-40-gates
make verify-13pillar-recovery
make verify-milestone-110
make verify-32-gates
make verify-10pillar-recovery
make verify-milestone-90
make verify-24-gates
make verify-fast
make verify-tier0-backup
make verify-antirollback-guard
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B Lifecycle Drill, Wireless Guard, Firmware Lab (24 Auditors), 21-Stage Co-Emulation & Stage-A Lifecycle targets
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
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Gyroflow / M&C Fleet / HLG / UVC-SRT-CRSDK Console**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under the MIT license; QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
