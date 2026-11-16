# Sony FX3 / FX6 Lab

**Explore Sony FX3 and FX6 firmware with QEMU, browser menu tools, and offline checks.**

用 QEMU、浏览器菜单工具和离线校验研究索尼 FX3 / FX6 固件。

For firmware researchers and developers interested in camera internals. This repository contains research tools and evidence; it is not a ready-to-flash camera upgrade.

**[Start here](#start-here)** · [English research guide](README.en.md) · [中文研究文档](README.zh-CN.md) · [Firmware setup](docs/BYOF-REPRODUCTION.md) · [Real-HW Deployment Dossier](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)

[![Clean-room CI](https://github.com/Rem021/sony-fx3-fx6-lab/actions/workflows/clean-room-ci.yml/badge.svg)](https://github.com/Rem021/sony-fx3-fx6-lab/actions/workflows/clean-room-ci.yml) [![Tests](https://img.shields.io/badge/Automated_Tests-12,101_Local_%7C_12,043_Clean--Room_(7_Suites)-brightgreen?style=flat-square)](#latest-mainline-snapshot) [![Milestone 264](https://img.shields.io/badge/Master_Gate-Milestone_264_%7C_Phases_1..268_%7C_Rounds_1..53-1a7f37?style=flat-square)](#latest-mainline-snapshot) [![License](https://img.shields.io/badge/license-MIT_%2F_GPLv2-blue?style=flat-square)](./LICENSE)

> [!IMPORTANT]
> Firmware-dependent experiments require your own matching official firmware (BYOF). Sony proprietary firmware is not distributed here (`0` bytes of vendor binaries or keys). Offline tests and emulator results do not establish safe operation on a physical camera. Persistent/cross-model flashing of a real FX3 remains **hard-locked OFF (`BLOCKED / NO-GO`)**.
>
> 固件实验需自备匹配版本的官方固件；仓库不分发索尼专有固件或私钥（`0` 字节闭源二进制）。离线与模拟器结果不代表真机安全验收，真实物理 FX3 跨机型持久化刷写仍为硬锁禁止状态（**`BLOCKED / NO-GO`**）。

## What you can explore

| Area | Start with |
| :--- | :--- |
| **Camera menus** | [FX3 / FX6 browser menu runners (`8768`)](outputs/fx3-vm-trial/README.md), after BYOF setup |
| **Emulation & HIL co-emulation** | [52-stage virtual camera HIL suite](outputs/fx3-vm/README.md), [QEMU Round 1–53 closures](outputs/fx6-native-presenter-closure/README.md), and [research guide](README.en.md) |
| **Safety, closure & recovery** | [108-gate safety preflight](outputs/fx3-safety/README.md), [45-pillar offline recovery adapter](outputs/fx3-recovery-adapter/README.md), [Stage-B & Milestone-264 closure](outputs/fx6-on-fx3-closure/README.md), and [45 keyless firmware auditors](outputs/fx3-firmware-lab/README.md) |
| **Reproduction & bench rules** | [BYOF SHA-256 requirements](docs/BYOF-REPRODUCTION.md) and [ILME-FX3 Ver. 7.02 deployment dossier](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md) |

## Start here

To inspect and verify a source checkout without camera hardware or Sony firmware, install Python 3 and GNU Make, then run the clean-room audits:

```bash
git clone https://github.com/Rem021/sony-fx3-fx6-lab.git
cd sony-fx3-fx6-lab
PYTHON=python3 make clean-audit
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHON=python3 make verify-byof
make verify-milestone-264
```

The audits verify the clean-room boundary, manifest parity, and 6-pillar offline/synthetic gates; they do not run a physical camera flash or certify hardware attachment (`overall_ready_for_hardware_attach = False`). For firmware-dependent QEMU menus, follow the [BYOF guide](docs/BYOF-REPRODUCTION.md) before launching a runner.

## Latest mainline snapshot

Current verified mainline state across **`Phases 1–268`**, **`Grand Milestone Phase 264`**, **`Rounds 1–53`**, and **Sony Help Guide (`ilc/2210`) Primary-Source `Waves 1–45`**:

| Pillar / Suite | Verified Baseline | Quick Verification Command |
| :--- | :--- | :--- |
| **7 Unified Test Suites** | **`12,101`** Local Donor / **`12,043`** Clean-Room tests (`2,341`/`2,283` recovery · `2,613` safety · `1,485` closure · `429` vm-trial · `1,170` presenter-closure · `2,325` fx3-vm · `1,738` firmware-lab) | `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` |
| **Grand Milestone 264 Master Gate** | **6/6** pillars (`LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC`), `16/16` `H0 == H3` immutability, `0` leaked bytes | `make verify-milestone-264` |
| **Safety Preflight Engine (`Ph268`)** | **`108/108`** gates (`G01..G108`: `105/108` offline truthful block, `108/108` bench dry-run rehearsal) | `PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-108-gates --simulate-bench-dry-run` |
| **Offline Recovery Master (`Ph265`)** | **`45/45`** pillars (`Tier-0..4`, `GF(256)` RAID-6, `OTP/RPMB`, `1.8V` RX-only UART, `cnflasha` `O_RDONLY`, Slot-1 vault firewall) | `PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m fx3_recovery verify-45pillar-recovery` |
| **VM HIL Co-Emulation (`Ph267`)** | **`52/52`** full-board HIL co-emulation stages (`stage1..stage52`) | `make verify-coemulation` |
| **Keyless Firmware Lab** | **`45/45`** clean-room binary/synthetic auditors (`audit-all`) | `make verify-firmware-lab` |
| **Live `FX3 7.02` ARM64 QEMU (`R53`)** | **`26/26`** unmodified `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) real-HW QEMU rounds (`r28..r53`, **`78/78`** runs, **`52/52`** PNGs `< 28 KiB`) + `Rounds 1..27` | `python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests` |
| **Physical Bench Preflights** | **`6`** host-side passive verifiers (`Ph186`, `Ph204`, `Ph216`, `Ph227`, `Ph248`, `Ph261`; `usb_tx_packets = 0`) | See [`docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md`](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md) |

## Engineering record

The dated record below preserves historical architectural notes, commands, and bilingual milestone summaries.

<details>
<summary>Expand the full bilingual engineering record / 展开中英双语工程记录</summary>

# English Documentation

## 1. Historical Architecture & Foundation Summary (`Phases 1–130` -> Extended through `Phase 268` / `Milestone 264`)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, multi-ISA QEMU virtualization, cross-model firmware compatibility, and anti-brick safety laboratory targeting the **Sony Cinema Line ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** and **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)**, both powered by the **Sony CXD90057 (`AArch64` CE Linux `4.9.337-scel+`)** AP and **CXD90058 (`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`)** co-processor.

Across **`Phases 1–268`**, **`Rounds 1–53`**, and **`Global Intel Waves 1–45`**, the lab integrates **7 unified verification suites (`12,101` Local Donor / `12,043` Clean-Room passing tests via `make test`)** and the **Grand Milestone Phase 264 Six-Pillar Master Gate (`make verify-milestone-264`)** (building upon the foundational Phase 90/110/130/147/175/193/209/221/233/254 master gates documented below):
- **Stage-B Volatile RAM-Overlay (`P1..P12 + Fan`, `13/13` Verify-Before-Mount)** with FX3 physical button remap (`P10`), AP-side UIPC-CP shim (`P11`, preserving `XLR-H1` & 5-axis IBIS center-lock), `WF-12` bootloop immunity (`P12`), `< 48 MiB` SVR4 `070701` CPIO packaging, Phase 52/76 Candidate Integrator & Release Dossier v3, Phase 62/68/83 `16`-surface `H0 == H2` / `H0 == H3` Post-Trial Forensic & Capstone Auditor, Phase 90/110/130 Master Gates, and **Grand Milestone Phase 264 6-Pillar Master Gate** ([Phase 264 Report](reports/2026-11-15-phase264-milestone264-master-closure-gate/README.md), [Phase 130 Report](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)).
- **108-Gate Master Preflight (`G01..G108`, building on `G01..G40`) & 45-Pillar Recovery Master Suite (`Phases 47..268`)**: Extends `G01..G32` (`C2PA 2.1`, `exFAT`, wired `USB-LAN`/`PTP-IP`, D-Tap/HDMI `V_LENS` crowbar, `NP-FZ100 >= 15%` UPS, `+48V` XLR, gimbal torque, Magnus dew-point `TEC`, PMIC `5V 900 mA`, Sigma fan intake/`1/4-20` tripod, `IMX510` laser/curtain/`-20C`, `5G/6G` EMI/`>6h` CFexpress, PL cantilever/`>8.4V` OVP) with **Ph108 (`G33..G34`)** coastal salt-spray/glycol haze & wireless follow-focus CoG, **Ph115 (`G35..G36`)** HDMI AOC Pin-18 `+5V` backfeed & CFexpress VPG/NVMe thermal/door-open flush, **Ph120 (`G37..G38`)** `20V` USB-C PD decoy/dual-power/UVC 4K30p thermal & 15-pin Multi-Terminal `LTC`/`3.3V` UART/`CRSDK` PTP firewall, **Ph125 (`G39..G40`)** tropical monsoon wet 24-pin MI-Shoe short/open-flap capillary & `XLR-H1` whip shear/`1/4"-20 > 3.5 N*m` strip/cage-twist `18.00 mm` E-Mount FFD warp, and **Phases 131–268 (`G41..G108`)** real-hardware bench, `ilc/2210` operational, and Slot-1 vault guards; paired with **`45` unified recovery pillars** (`verify-45pillar-recovery`).
- **Live Port `8768` Multilingual QEMU Console (`FX6菜单.command`), `52-Stage` Co-Emulation (`fx3-vm`), `45` Unified `fx3-firmware-lab` Auditors & `Rounds 1–53` (`26/26` live `FX3 7.02` ARM64 QEMU rounds `r28..r53` / `78/78` runs / `52/52` `<28 KiB` PNGs + `Rounds 1–27` at `nop_count = 0`)**: Adds **Ph109** Monitor & Control 4-Cam wired Gang-REC + HDMI->12G-SDI `AVI`/`RP 188` + E-Mount/PL shading + `C2PA 2.1` provenance HUD, **Ph116** `HLG1/2/3 BT.2100` + `Display Assist` clean-out + `CTA-861.3 (0x87)` + external `ProRes RAW`/`BRAW` + Focus Breathing HUD, **Ph123** USB-C `UVC 1.5/UAC 2.0` (`480M` stepdown, 0 OSD) + wired `CDC-NCM P12-Safe SRT/RTMPS TLS 1.3` + `CRSDK PTP` flash-opcode (`0x9280..0x92FF`) firewall HUD, and `Rounds 28–53` unmodified `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) QEMU GPE0 rehearsals.

For complete architectural & field manuals, see **[docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)**, **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)**, and **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**.

---

## 2. The 7 Unified Verification Suites (`make test` — `12,101` Local Donor / `12,043` Clean-Room)

Running `make test` executes all **7 suites (`12,101` Local Donor / `12,043` Clean-Room)**, the bilingual `docs/BYOF-REPRODUCTION.md` manifest audit (`57+57` entries, `46` constants), and the `git status --porcelain` zero-binary/zero-`.pyc` hygiene sweep:

### 1. [`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md) (`557` Local Donor / `499` Clean-Room tests)
- **13-Pillar Recovery Master Suite (`make verify-13pillar-recovery`)**: Composes Pillars `1..10` (`macOS 26 IOUSBHost`, `RP2040-Zero -DOPEN_DRAIN` `make verify-rp2040-fixture`, `<1s` `FX3_SAFE_STOCK.FLG` `init2` escape + WDT `make verify-init2-escape`, `GF(256)` RAID-6 Tier-0 healer `make verify-tier0-backup`, `OTP/RPMB` anti-rollback `make verify-antirollback-guard`, Tier-0..4 ladder, passive `1.8V` RX-only UART `S0..S6` `passive_tx_bytes_emitted == 0`, Ph94 GPT CRC32/RPMB, Ph101 SVR4 `cpio`/`EXT_CSD` Pre-EOL, Ph106 FDT `/chosen/bootargs` `ro`/ARM64 `Image`) **plus** **Pillar 11 (Ph113)** Dual-Bank A/B & interrupted `BODYDATA.DAT` OTA ([Phase 113](reports/2026-11-14-phase113-ab-bank-interrupted-ota-recovery/README.md)), **Pillar 12 (Ph119)** SquashFS `4.0` & `hibdrv` `WBI2` ([Phase 119](reports/2026-11-14-phase119-squashfs-wbi-hibdrv-recovery/README.md)), and **Pillar 13 (Ph124)** Mask-BootROM USB & JEDEC eMMC `BOOT0/BOOT1` ([Phase 124](reports/2026-11-14-phase124-bootrom-usb-emmc-bootpart-recovery/README.md)).

### 2. [`outputs/fx3-safety/`](outputs/fx3-safety/) (`665` Local Donor / `665` Clean-Room tests)
- **40-Gate Master Safety Preflight Engine (`G01..G40`, `make verify-40-gates`)**: Extends `G01..G32` (`make verify-32-gates`) with **Phase 108** (`G33` coastal salt-spray/glycol haze, `G34` wireless FIZ torque/gimbal CoG), **Phase 115** (`G35` HDMI AOC Pin-18 `+5V` backfeed/shear, `G36` CFexpress VPG/NVMe thermal/door flush), **Phase 120** (`G37` `20V` USB-C decoy/cross-feed/UVC thermal, `G38` Multi-Terminal `LTC`/`3.3V` UART/`CRSDK` PTP firewall), and **Phase 125** [`monsoon_mishoe_cagetwist_and_40gate_guard.py`](outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py) (`G39` wet 24-pin MI-Shoe rain short/flap capillary & `G40` `XLR-H1` whip shear/`1/4"-20 > 3.5 N*m` strip/cage-twist `18.00 mm` E-Mount FFD warp — `37/40` offline truthful block vs `40/40` simulated rehearsal, [Phase 125](reports/2026-11-14-phase125-safety-monsoon-mishoe-cagetwist-40gates/README.md)).

### 3. [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) (`559` Local Donor / `559` Clean-Room tests)
- **Milestone Phase 130 6-Pillar Master Gate ([`stage_b_milestone130_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone130_master_gate.py), `make verify-milestone-130`, `< 2.5s`)**: Unifies all 6 Milestone-130 pillars (`40-Gate`, `13-Pillar Recovery`, `>= 24` Firmware-Lab Auditors, `>= 21` VM Stages, Real FX3 `7.02` Closures `Rounds 14/17/19/20..24`, and `H0 == H2` 16-surface immutability + hardware lock invariants) with deterministic `milestone130_sha256` ([Phase 130 Report](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)) while keeping [`stage_b_milestone110_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone110_master_gate.py) (`make verify-milestone-110`), [`stage_b_milestone90_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone90_master_gate.py) (`make verify-milestone-90`), and all Stage-A/B CLIs 100% intact.

### 4. [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) (`367` Local Donor / `367` Clean-Room tests)
- **Live QEMU ARM64 `1024×540` `GPE0` Web Console on port `8768`** ([`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command), [`FX3菜单.command`](outputs/fx3-vm-trial/FX3菜单.command)):
  - Native `LDEC103` icons (`60/60` `0 SEGV`), 128-page 4-language pool (`简体中文 / 繁體中文 / EN / 日本語`), `P10` button deck, 4-Ch `XLR-H1` VU, **Phases 56..102** (Scopes, Cine EI, Touch AF/`x4`/False Color/`CIZ`, Anamorphic IBIS/Gyroflow `2kHz`/Tone, Picture Cache/Interval/`.cube`/FTPS), **Phase 109** (`'MCFL'` Monitor & Control 4-Cam wired Gang-REC + HDMI->12G-SDI `AVI`/`RP 188` + E-Mount/PL shading + `C2PA 2.1` shield, [Phase 109](reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md)), **Phase 116** (`'HLGA'` `HLG1/2/3 BT.2100` + `Display Assist` clean-feed + `CTA-861.3 (0x87)` + `ProRes RAW`/`BRAW` + Focus Breathing, [Phase 116](reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md)), and **Phase 123** (`'UVCS'` USB-C `UVC 1.5/UAC 2.0` + wired `P12`-safe `SRT/RTMPS TLS 1.3` + `CRSDK PTP` flash-opcode firewall, [Phase 123](reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md)).

### 5. [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md) (`198` Local Donor / `198` Clean-Room tests)
- **Rounds 1–24 (`r1a..r24e`) Real FX3 `7.02` (`4.9.337-scel+`) Hybrid QEMU Closure at `nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`): `13/13` Verify-Before-Mount SHA-256, `P10` + `P11` + `P12`, **R14 `18/18`**, **R17 `10/10` Status Check (`45/45` `>0`)**, **R19 `11/11` Full-Menu (`55/55` `>0`)**, **plus five 4-language (`EN/JA/ZH-CN/ZH-TW`) `12/12` dual-surface closures** in **Round 20 (`Network` + WF-12)**, **Round 21 (`Audio`)**, **Round 22 (`Paint/Look` & `Camera`)**, **Round 23 (`Monitoring`)**, and **Round 24 (`Project`)** -> **`60/60` multilingual pairs strictly `> 0`** across 27 runs ([Round 20](reports/2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure/README.md), [Round 21](reports/2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure/README.md), [Round 22](reports/2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure/README.md), [Round 23](reports/2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure/README.md), [Round 24](reports/2026-11-14-round24-fx6-on-fx3-project-4lang-dualsurface-closure/README.md)).

### 6. [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) (`684` Local Donor / `684` Clean-Room tests)
- **21-Stage Full-Board Virtual Camera Co-Emulation (`fx3_vm_coemulation_suite.py` / `make verify-coemulation`)**:
  - **Stages 1–18 (`Phases 24–107`)** plus **Stage 19 (Ph112)** `HLG/BT.2100`, Display Assist & FIZ/Gimbal HIL ([Phase 112](reports/2026-11-14-phase112-vm-stage19-hdr-hlg-gimbal-fiz-hil/README.md)); **Stage 20 (Ph117)** External `ProRes RAW`/`BRAW`, Focus Breathing & MI-Shoe I2S/AOC `+5V` HIL ([Phase 117](reports/2026-11-14-phase117-vm-stage20-proresraw-breathing-mishoe-hil/README.md)); and **Stage 21 (Ph121)** USB-C `UVC/UAC`, Wired `SRT/RTMPS`, `CRSDK PTP` Firewall & `20V` USB-PD Decoy HIL (`wf12_00342260_hits=0`, `emmc_flash_mutation_bytes=0`, [Phase 121](reports/2026-11-14-phase121-vm-stage21-uvc-srt-crsdk-usbpd-hil/README.md)).

### 7. [`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md) (`713` Local Donor / `713` Clean-Room tests)
- **24 Unified Clean-Room Keyless Auditors (`audit-all` / `make verify-firmware-lab`)**:
  - `#1..#20` (`UFU`..`C2PA 2.1`/Lens Shading/MC Fleet) plus **`#21 (Ph111)`** `hdr_hlg_bt2100_and_display_assist_audit` ([Phase 111](reports/2026-11-14-phase111-hdr-hlg-bt2100-display-assist-auditor/README.md)) · **`#22 (Ph114)`** `hdmi_raw_prores_breathing_and_mishoe_clock_audit` ([Phase 114](reports/2026-11-14-phase114-proresraw-breathing-mishoe-auditor/README.md)) · **`#23 (Ph118)`** `usb_uvc_uac_srt_and_crsdk_ptp_audit` ([Phase 118](reports/2026-11-14-phase118-uvc-srt-crsdk-ptp-auditor/README.md)) · **`#24 (Ph122)`** `mxf_mp4_essence_ptpv2_and_tally_umd_audit` ([Phase 122](reports/2026-11-14-phase122-mxf-mp4-ptpv2-tally-auditor/README.md)).

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
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 7-suite, 40-Gate, 13-Pillar & Milestone-130 CI
├── Makefile                                 # Unified test, Milestone-130, 40-Gate, 13-Pillar Recovery, M110/90, VM & Lab
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # Bilingual Stage-B (`P1..P12+Fan`), 40-Gate (`G01..G40`), 21-Stage VM & 13-Pillar ref
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # Bilingual SOP: RP2040, +48V, TEC, Salt-Spray/AOC, PD Decoy, Monsoon MI-Shoe, <1s Escape
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent hardware operator runbook
│   └── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 7-suite test runner (3,743 Local / 3,685 Clean-Room) + BYOF + hygiene audit
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
└── conversations/                           # Categorized multi-agent engineering archives across 5 thematic workspaces
```

---

## 4. Quick Start & Verification

```bash
# 1. Run all 3,743 Local Donor tests across all 7 suites + BYOF manifest audit (57+57) + clean-room hygiene
make test
make test-json

# 2. Simulate donorless Clean-Room CI locally (3,685 tests across 7 suites, zero Sony firmware blobs — matches clean-room-ci.yml)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 130 6-Pillar Master Gate (< 2.5s) + 40-Gate Safety + 13-Pillar Recovery + Legacy Gates (BOTH modes)
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

**Launch Interactive Web Console (Requires BYOF Setup per `docs/BYOF-REPRODUCTION.md`)**:
- **FX6 128-Page / Big6 / Touch AF / False Color / CIZ / Cine EI / Gyroflow / M&C Fleet / HLG / UVC-SRT-CRSDK Console**: `./outputs/fx3-vm-trial/FX6菜单.command` -> `http://127.0.0.1:8768/`
- **FX3 Native Menu Web Console**: `./outputs/fx3-vm-trial/FX3菜单.command` (`--check` validates SHA-256 inputs without starting QEMU)

---
---

# 简体中文文档

## 一、项目总览（`Phases 1–130` · `Rounds 1–24` · `Waves 1–14`）

**`sony-fx3-fx6-lab`** 围绕 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 开展净室系统工程、多架构 QEMU 协同仿真、跨机型固件兼容适配与真机防变砖安全研究。两款机型均基于 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

历经 **`Phases 1–130`**、**`Rounds 1–24`** 与 **`Waves 1–14` 全球公开情报同步** 迭代，实验室已构建起 **7 大统一自动化验证套件（`make test` 本地供体全量 `3,743` 项通过 / `FX3_FX6_FORCE_CLEAN_ROOM=1` 无供体洁净室 `3,685` 项全绿通过）** 与 **Milestone Phase 130 六柱一体化总闸（`make verify-milestone-130`，`< 2.5s`）**：
- **Stage-B 易失性 RAM 覆盖层（`P1..P12+Fan`，`13/13` 挂载前校验）**：涵盖 `P10` FX3 实体按键映射、`P11` AP 侧 UIPC-CP 垫片（保留 `XLR-H1` 热靴音频与 5 轴 IBIS 居中锁止）、`P12` `WF-12` 无线断环补丁、`< 48 MiB` SVR4 `070701` CPIO 打包器、Phase 52/76 集成与发布简报 v3、Phase 62/68/83 `16` 表面 `H0 == H2` 试后法证审计、Phase 90/110 总闸，以及 **Milestone Phase 130 六柱总闸**（[Phase 130 报告](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)）。
- **40 门禁主安全预检引擎（`G01..G40`）与 13 支柱救砖恢复主套件（`Phases 47..124`）**：在 `G01..G32` 基础上新增 **Ph108（`G33..G34`）** 海岸盐雾/烟雾过滤与无线跟焦动态质心振荡拦截、**Ph115（`G35..G36`）** HDMI AOC Pin-18 `+5V` 倒灌与 CFexpress VPG/NVMe 降速/仓门未关刷写防护、**Ph120（`G37..G38`）** `20V` USB-C PD 诱骗线/双电源串电/UVC 热饱和与 15 针多接口 `LTC`/`3.3V` UART/`CRSDK` PTP 刷机防火墙，以及 **Ph125（`G39..G40`）** 热带季风湿润 24 针 MI 热靴短路/敞口毛细渗水与 `XLR-H1` 甩力滑丝/`1/4"-20` 滑扣/不对称兔笼扭矩导致 E 卡口 `18.00 mm` 法兰距形变拦截；并集成 **13 大救砖恢复支柱**（含 Ph113 双槽 A/B 与断电 `BODYDATA.DAT` OTA 修复、Ph119 SquashFS `4.0` `hsqs` 与 `hibdrv` `WBI2` 审计及 Ph124 Mask-BootROM USB 与 JEDEC eMMC `BOOT0/BOOT1` 分区引导恢复）。
- **端口 `8768` 实时交互式 QEMU 控制台（`FX6菜单.command`）、21 阶段全板协同仿真（`fx3-vm`）、24 大无密钥固件审计器（`fx3-firmware-lab`）与 `Rounds 1–24`（`R14 18/18` + `R17 45/45` + `R19 55/55` + `R20..24 5/5 60/60`，`nop_count = 0`）**：新增 **Ph109** Monitor & Control 4 机位有线 Gang-REC + HDMI->12G-SDI `AVI`/`RP 188` + E/PL 阴影 + `C2PA 2.1` 溯源护盾、**Ph116** `HLG1/2/3 BT.2100` + `Display Assist` 洁净输出 + `CTA-861.3 (0x87)` + `ProRes RAW`/`BRAW` + 呼吸补偿 HUD，以及 **Ph123** USB-C `UVC 1.5/UAC 2.0` + 有线 `P12` `SRT/RTMPS TLS 1.3` + `CRSDK PTP` 防火墙 HUD，并与 `21` 阶段协仿真及 `24` 大审计器全面对齐。

架构细节与现场操作规范请参见 **[docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md](docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)** 与 **[docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md](docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)**。

---

## 二、七大统一测试套件明细（`make test` — 本地供体 `3,743` 项 / 洁净室 `3,685` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `557` / 洁净室 `499` 项测试）**：**13 支柱救砖恢复主套件（`make verify-13pillar-recovery`）**——涵盖支柱 `1..10`（`macOS 26 IOUSBHost`、`RP2040-Zero -DOPEN_DRAIN`、`<1s` `FX3_SAFE_STOCK.FLG`、`GF(256)` RAID-6、`OTP/RPMB` 防回滚、被动只收 `1.8V` UART `S0..S6`、Ph94 GPT/RPMB、Ph101 `cpio`/`EXT_CSD` Pre-EOL、Ph106 FDT `/chosen/bootargs` `ro`/ARM64 `Image`）叠加 **Ph113** A/B OTA（[Phase 113](reports/2026-11-14-phase113-ab-bank-interrupted-ota-recovery/README.md)）、**Ph119** SquashFS/`WBI2`（[Phase 119](reports/2026-11-14-phase119-squashfs-wbi-hibdrv-recovery/README.md)）及 **Ph124** Mask-BootROM USB/eMMC `BOOT0..1`（[Phase 124](reports/2026-11-14-phase124-bootrom-usb-emmc-bootpart-recovery/README.md)）。
2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `665` 项测试）**：**`G01..G40` 40 门禁主安全预检引擎（`make verify-40-gates`）**在 `G01..G32` 基础上扩展 **Ph108（`G33..G34`）** 盐雾/无线跟焦 CoG、**Ph115（`G35..G36`）** HDMI AOC `+5V`/CFexpress 刷写、**Ph120（`G37..G38`）** `20V` USB-C PD 诱骗/多接口/CRSDK PTP 防火墙，以及 **Ph125** [`monsoon_mishoe_cagetwist_and_40gate_guard.py`](outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py)（`G39` 季风湿润 24 针热靴与侧盖毛细渗水、`G40` `XLR-H1` 甩力滑丝/`1/4"-20` 超扭矩与兔笼扭曲 E 卡口 `FFD` 形变，[Phase 125](reports/2026-11-14-phase125-safety-monsoon-mishoe-cagetwist-40gates/README.md)）。
3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `559` 项测试）**：**Milestone Phase 130 六柱一体化总闸（[`stage_b_milestone130_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone130_master_gate.py)，`make verify-milestone-130`，`< 2.5s`）**汇聚 `40-Gate`、`13-Pillar 恢复`、`>= 24` 固件审计器、`>= 21` VM 阶段、`Round 14/17/19/20..24` 真内核全闭环与 `H0 == H2` 16 表面不可变性并生成 `milestone130_sha256`（[Phase 130 报告](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)），完整保留 `verify-milestone-110`、`verify-milestone-90` 与 Stage-A/B 所有命令。
4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `367` 项测试）**：端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)），覆盖 `Ph109` Monitor & Control 四机位联机/SDI `RP 188`/`C2PA 2.1`（[Phase 109](reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md)）、`Ph116` `HLG BT.2100`/`Display Assist` 洁净输出/`ProRes RAW`/`BRAW`/呼吸补偿（[Phase 116](reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md)）及 `Ph123` `UVC/UAC` + 有线 `P12` `SRT/RTMPS` + `CRSDK PTP` 防火墙（[Phase 123](reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md)）。
5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `198` 项测试）**：**Rounds 1–24（`r1a..r24e`）** FX3 `7.02` 原厂 `4.9.337-scel+` 内核混合态真机实跑（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）：除 **R14 `18/18`**、**R17 `45/45`**、**R19 `55/55`** 外，补齐 **Round 20（`Network` + `WF-12`）**、**Round 21（`Audio`）**、**Round 22（`Paint/Look` & `Camera`）**、**Round 23（`Monitoring`）** 与 **Round 24（`Project`）** 五大四语 `12/12` 双界面闭环，合计 **`60/60` 多语言配对严格正差分**（[Round 20](reports/2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure/README.md)、[Round 21](reports/2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure/README.md)、[Round 22](reports/2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure/README.md)、[Round 23](reports/2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure/README.md)、[Round 24](reports/2026-11-14-round24-fx6-on-fx3-project-4lang-dualsurface-closure/README.md)）。
6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `684` 项测试）**：**21 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**——在 Stages 1–18 之上新增 **Stage 19（Ph112）** `HLG/BT.2100`/跟焦稳定器 HIL（[Phase 112](reports/2026-11-14-phase112-vm-stage19-hdr-hlg-gimbal-fiz-hil/README.md)）、**Stage 20（Ph117）** `ProRes RAW`/`BRAW`/呼吸补偿/MI 热靴 HIL（[Phase 117](reports/2026-11-14-phase117-vm-stage20-proresraw-breathing-mishoe-hil/README.md)）及 **Stage 21（Ph121）** `UVC/UAC`/`SRT`/`CRSDK PTP`/`20V USB-PD` HIL（[Phase 121](reports/2026-11-14-phase121-vm-stage21-uvc-srt-crsdk-usbpd-hil/README.md)）。
7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `713` 项测试）**：**24 大洁净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**——在 `#1..#20` 之上新增 **`#21（Ph111）`** `HLG/BT.2100/Display Assist`（[Phase 111](reports/2026-11-14-phase111-hdr-hlg-bt2100-display-assist-auditor/README.md)）、**`#22（Ph114）`** `ProRes RAW/BRAW`/呼吸补偿/MI 时钟（[Phase 114](reports/2026-11-14-phase114-proresraw-breathing-mishoe-auditor/README.md)）、**`#23（Ph118）`** `UVC/UAC/SRT/CRSDK PTP`（[Phase 118](reports/2026-11-14-phase118-uvc-srt-crsdk-ptp-auditor/README.md)）及 **`#24（Ph122）`** `MXF OP1a/MP4 RDD-18/PTPv2/TSL UMD v5.0`（[Phase 122](reports/2026-11-14-phase122-mxf-mp4-ptpv2-tally-auditor/README.md)）。

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
# 1. 运行全部 7 套 3,743 项本地供体测试 + BYOF 双语清单审计 (57+57) + git 净室零残留审计
make test
make test-json

# 2. 本地模拟无供体洁净室 CI (7 套 3,685 项测试，零索尼固件依赖，与 GitHub Actions 完全一致)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 130 六柱总闸 (<2.5s) + 40 门禁、13 支柱救砖与历史兼容总闸（双模式通用）
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

# 4. Stage-B 生命周期演练、无线防护、固件实验室（24 审计器）、21 阶段协同仿真与 Stage-A 演练命令
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
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / Gyroflow / M&C / HLG / UVC-SRT-CRSDK 控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入 SHA-256）。

---

## 四、多智能体归档与开源协议 (Archives & License)

- **工程对话归档**：5 大专题工作区多智能体研究对话已按净室规范分类归档至 **[conversations/README.md](conversations/README.md)**。
- **免责与开源协议**：本仓库包含 **0 字节** 索尼专有二进制固件或私有密钥，与 Sony Group Corporation 无任何隶属或合作关系。自研源码采用 [MIT](./LICENSE) 协议，QEMU 补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。

</details>
