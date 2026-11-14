# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![English Standalone](https://img.shields.io/badge/Standalone_EN-README.en.md-0969da?style=flat)](./README.en.md)
[![简体中文独立版](https://img.shields.io/badge/独立中文版-README.zh--CN.md-0969da?style=flat)](./README.zh-CN.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-271_Passing_(make_test)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot & Hybrid GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r9d_(26_PNGs)-success?style=flat)](#track-1b-fx6-native-cold-boot--round-8--round-9-fx6-on-fx3-hybrid-qemu-closure)
[![FX6-on-FX3 Closure](https://img.shields.io/badge/FX6--on--FX3_Closure-Phase_21_%7C_P1..P11%2BFan_%7C_U1..U5_%7C_IBIS-1a7f37?style=flat)](#track-3-fx6-on-fx3-p1p9--fan-closure-u1u5-closure--12-gate-anti-brick-suite)

> **Language Navigation / 语言切换**: **[English Documentation](#english-documentation)** · **[简体中文文档](#简体中文文档)** · **[Standalone `README.en.md`](./README.en.md)** · **[独立中文版 `README.zh-CN.md`](./README.zh-CN.md)**

> **2026-11-14 Master Milestones (全线工程里程碑闭环)**:
> 1. **Track 1A — Phase 19 Live FX6 Native Icon Blitting (`image_00_169.uxc`), Multi-Click `60/60` Freeze Fix, 128-Page Guest `GPE0` UI & 20 Offline Unit Tests**: Integrated authentic Sony FX6 sprite blitting (`image_00_169.uxc` LDEC `/dev/mem` GPE physical pool `0x410524000..0x410e64000`, `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` blitter) and permanently eliminated the multi-click `PC=0` `APPFW_SEGV` freeze (`GenerateImageCommand::notify(bool)` interposition + 32-slot aligned widget ring pools + serialized GDB `finally` resume, **`60/60` rapid clicks `0 SEGV`**, avg `179.3 ms`/click, up to `icon_n=119`, [Phase 19 Report](reports/2026-11-14-phase19-live-icon-rendering/README.md)) alongside all **128** FX6 page descriptors, **22.1x** C scanline packer, and **20** unit tests ([`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)).
> 2. **Track 1B — FX6 Native Cold-Boot + Round 8 (Stage-A) & Round 9 (Stage-B `P10` Keymap) FX6-on-FX3 Hybrid QEMU Real-Kernel Closure (`r1a..r9d`, 26 PNG Receipts, 20 Unit Tests)**: Delivered [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) ([Rounds 1–7](reports/2026-11-10-fx6-native-presenter-closure/README.md), [Round 8 Stage-A](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md), & [Round 9 Stage-B `P10`](reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md)), running **FX3 7.02 stock `vmlinux.bin` (`4.9.337-scel+`)** at **`nop_count = 0`** with `11/11` in-guest SHA-256 Verify-Before-Mount checks and driving physical FX3 `Fn`/`C1`/`C2`/`MENU`/`ENTER` keys (`SRM3KYE5`) through `InfraInput` into Stage-B `appFw.so` across `r9a` Shooting HUD (`sid=0x02`), `r9b` Big6 Home (`sid=0x0a`), `r9c` Big6 Setting Sub-Dialog (`sid=0x0c`, `2,035` Cinema Line `0xffffaa00` amber px), and `r9d` Full Menu 2nd Layer (`sid=0x10`, `434,010` px, `87` colors).
> 3. **Track 3, Track 4 & Global Intel Sync — FX6-on-FX3 Phase 21 Full-Stack Closure (`P1..P11 + Fan`, `U1..U5`, Stage-B Combined `appFw.so` `e2bc2619...`, `P11` UIPC-CP Shim, 5-Axis IBIS Center-Lock, 2025–2026 Global Sony Firmware/VM/BootROM Unbrick Dossier & `271` 5-Suite Automated Tests)**: Delivered [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md), [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md), [`outputs/fx3-safety/`](outputs/fx3-safety/), [Phase 20 Stage-B `P10` Report](reports/2026-11-14-phase20-p10-stage-b-integration/README.md), [Phase 21 `P11` UIPC-CP Shim Report](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md), and [2025–2026 Global Sony Firmware/VM/Unbrick Intel Dossier](reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md), closing **Phase 20** combined Stage-B `appFw.so` (`P1+P4+P8+P10`, 10 sites / 41 B zero overlap, SHA-256 `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`, 21-key Unicorn proof, `make verify-stage-b-p10`), **Phase 21** `P11` AP-side UIPC-CP shim (`0x92d2091c` `/dev/rtc0->udate` & `0x91db059b` Smart Handle ACK preserving `XLR-H1`, `developing_mode_FHD -> 0x92840747`, `0x0165`/`0x0166` `33^3` 3D LUT DMA, 5-axis IBIS center-lock, `make verify-uipc-cp-shim`), **all 5 Blueprint Unknowns (`U1..U5`)**, **12/12** pre-flash safety gates (`persistent_emmc_writes_authorized = False`), `57+57` BYOF manifest parity (`make verify-byof`), and **`271` automated tests passing across all 5 suites via `make test`** (`63` `fx3-recovery-adapter` + `19` `fx3-safety` + `149` `fx6-on-fx3-closure` + `20` `fx3-vm-trial` + `20` `fx6-native-presenter-closure`).

---

# English Documentation

## 1. Executive Summary & Clean-Room Scope

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, QEMU AArch64 virtualization, cross-model compatibility verification, and hardware anti-brick safety research repository focused on the **Sony Cinema Line ILME-FX3 (Ver. 7.02, Model ID `0x91030080`)** and **ILME-FX6 (Ver. 6.01, Model ID `0x91040086`)** digital cinema cameras, both powered by the **Sony CXD90057 AArch64 SoC** running Sony CE Linux `4.9.337-scel+` alongside a TOPPERS-FMP 1.4.0 SMP RTOS co-processor (`cpapp-b.bin` `@ 0x00108000`).

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**
> To strictly respect intellectual property laws and repository hygiene, **this repository contains 0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` partition dumps, or `.cpio` rootfs images). We open-source **100% of our self-authored Python verifiers, freestanding AArch64 C/Assembly workers, Unicorn AArch64 emulation harnesses, QEMU device patches, Web UI frontends, SHA-256 receipts, and technical reports**. Donorless clones automatically verify cleanly via `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` (and `.github/workflows/clean-room-ci.yml`). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing VM sessions with your own official firmware packages.

---

## 2. Development Progress & Technical Milestones (As of Nov 14, 2026)

### Track 1A: Interactive FX6 128-Page Guest `GPE0` UI, Phase 19 Native Icon Blitting & `fx3-vm-trial` Stability

- **Phase 19 Authentic FX6 Sprite/Icon Rendering & `60/60` Multi-Click Freeze Fix**: Added read-only `image_00_169.uxc` CPIO injection + LDEC-legal `/dev/mem` GPE physical pool (`0x410524000..0x410e64000`) + `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` blitting onto `GPE0`, and eliminated the `liblibra.so` `GenerateImageCommand::notify(bool)` (`0x2a238`) async worker race via PLT interposition, 32-slot aligned widget ring pools, and serialized GDB `$c#63` resume (`60/60` rapid clicks `0 SEGV`, up to `icon_n=119`, avg `179.3 ms`, [Phase 19 Report](reports/2026-11-14-phase19-live-icon-rendering/README.md)).
- **100% 128-Page Descriptor Rendering & 22.1x Compiled C Scanline Packer**: Rendered all **128** native FX6 Ver. 6.01 (`ILME-FX6V`) page descriptor tables (`2,249` widget rows across `appFw.so` `0x02e90fb0..0x02eba7b8`) into physical framebuffer `0x41e001000` (`GPE0`, `1024×540` RGBA32) with **`segv = 0`**, backed by `fx6_pack_scanlines` (**22.1x** host speedup), [`build_live700.py`](outputs/fx3-vm-trial/build_live700.py), [`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command), and **20** offline tests ([`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)).

### Track 1B: FX6 Native Cold-Boot + Round 8 & Round 9 FX6-on-FX3 Hybrid QEMU Closure

- **Controlled Package & Evidence**: [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) · [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md) · [`reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md`](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md) · [`reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md`](reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md)
- **Zero-Instruction-NOP Full Cold-Boot (`r1a..r7c`), Round 8 Stage-A (`r8a..r8b`) & Round 9 Stage-B `P10` Multi-Scene Closure (`r9a..r9d`, 26 PNG Receipts, 20 Unit Tests)**: Boots unmodified FX6 userland (`bootin` → `im.elf` → `appFw.so`) at **`nop_count = 0`** (`FX6_NATIVE_FAITHFUL=1`), boots **FX3 7.02 stock `vmlinux.bin`** + Stage-A (`r8a..r8b`), and in **Round 9** verifies `11/11` Stage-B SHA-256 digests (`P10` live readback `ok=1`) while routing physical FX3 `Fn`/`C1`/`C2`/`MENU`/`ENTER` keys (`SRM3KYE5`) through `InfraInput` (`0x007a804c -> 0x005503e0`) into `r9a` Shooting HUD (`sid=0x02`), `r9b` Big6 Home (`sid=0x0a`), `r9c` Big6 Setting Sub-Dialog (`sid=0x0c`, `2,035` amber `0xffffaa00` px), and `r9d` Full Menu 2nd Layer (`sid=0x10`, `434,010` px, `87` colors).

### Track 2: FX3 Native Firmware QEMU Virtual Machine & Interactive Web Menu Emulator

- **Primary Packages & Reports**: [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) · [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) · [`reports/2026-11-01-fx3-vm-resumed-repair/README.md`](reports/2026-11-01-fx3-vm-resumed-repair/README.md)
- **Hardware Subsystem Modeling & AP70–AP105 Bring-Up**: Patches QEMU AArch64 ([`fx3-esram-high-ddr.patch`](outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch)) to map up to 5 GiB High DDR at `0x400000000`, 4 KiB ESRAM mailbox at `[0xfe005000, 0xfe006000)`, fixed GICD VA, Sony timers, SCU, GPIO Bank5, UIPC, DMM, GPE v13/v14, and software LDEC LZ77 asset decompression, booting unmodified FX3 7.02 `vmlinux.bin` + `appFw.so`.
- **Interactive Web Menu Launcher (`FX3菜单.command`)**: Starts a local browser UI (`4096`-key / `60`-minute session budget, ~`40.1s` start-to-first-OSD-frame latency, verified across 32-key live menu navigation and clean API16 shutdown restoration).

### Track 3: FX6-on-FX3 `P1..P11 + Fan` Closure, `U1..U5` Closure & 12-Gate Anti-Brick Suite

- **Controlled Packages & Master Reports**: [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) · [`outputs/fx3-safety/`](outputs/fx3-safety/) · [`reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md`](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md) · [`reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md`](reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md) · [`reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md`](reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md) · [`reports/2026-11-14-phase20-p10-stage-b-integration/README.md`](reports/2026-11-14-phase20-p10-stage-b-integration/README.md) · [`reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md`](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)
- **Full Compatibility Matrix (`P1..P11 + Fan`), Stage-B Combined `appFw.so` & 100% SHA-256 Rollback**:
  - Deterministic ELF64 `PT_LOAD` / `ET_REL` adaptation and **100% bit-exact SHA-256 rollback** across all binary targets, pure-Python `8/16/44.5 MiB` `opelog.vfat` synthesis (`P2`), Unicorn-verified UIPC completion synthesis on `0x92840747` (`P5`/`P6`), dual-kernel `pcidma_transfer_async` Sync100 trampoline verification (`P7`), **Phase 17 & Phase 20** combined Stage-B `appFw.so` (`P1+P4+P8+P10` 10 sites / 41 B zero overlap, SHA-256 `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`, 21-key Unicorn proof, LCD/HDMI OSD routing & `XLR-H1` audio closure via `make verify-peripheral-ux` & `make verify-stage-b-p10`), and **Phase 18 & Phase 21 (`P11`)** AP↔Stock-CP imaging & UIPC-CP shim (`44/44` `0x92840747` opcodes + Unicorn-verified `0x92d2091c` `/dev/rtc0->udate` & `0x91db059b` Smart Handle ACK preserving `XLR-H1`, `developing_mode_FHD -> 0x92840747`, `0x0165`/`0x0166` `33^3` 3D LUT DMA / Cine EI / Dual ISO `800`/`12800`, `0 B` loadable diff on `libInfraLensCommunicator.so` E-mount AF, and **FX3 5-axis IBIS energized center-lock** via `make verify-ap-cp-imaging` & `make verify-uipc-cp-shim`).
- **5-Feature Routing, FDT (`cxd90057.dtb`), `.ko` Load-Order Matrix, `/dev/*` Nodes & 60-ELF `DT_NEEDED`/`DYNSYM`/`VERNEED` Closure**:
  - 60-ELF transitive `DT_NEEDED` + `DYNSYM` + `VERNEED` closure (`0` missing `DT_NEEDED`, `0` unresolved required symbols, `0` patch `.dynsym` delta, `267/267` `VERNEED` checks satisfied), `137` `/dev/*` paths audited across `61` FX6 userland binaries (`0` unaccounted), 100% byte-identical `insmod_drv1` (`4` `.ko`s) & `insmod_drv2` (`39` `.ko`s, `126` shared CXD90057 `.ko`s, `0` `.ko` mutations), 16x `33^3` `.cube` 3D LUT budget on FX3 `48.00 MiB` `p30` (`+32.04 MiB` headroom), and 100% byte-identical `cxd90057.dtb` (`16,875 B`, `0xd00dfeed`).
- **Zero-Repartition `p15` / DDR `tmpfs` Budgets, `nflasha3-initrd` / WBI (`p5`) Redline & Atomic Stage-A Orchestrator**:
  - Enforces `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), **Stage-A WBI Hibernation Safety Redline (`wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`)**, and **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)**; builds deterministic SVR4 `cpio newc` (`30,956 B`) and verifies 4 fail-safe rollback drills + 6 atomic Verify-Before-Mount + reverse LIFO teardown `/bin/sh` sandbox scenarios with **`0` eMMC writes and `0` WBI writes**.
- **All 5 Blueprint Unknowns (`U1..U5`) Closed**:

| ID | Architectural Question | Verified Closure Module & Proof |
| :---: | :--- | :--- |
| **`U1`** | Total eMMC UDA geometry & partition headroom without Sector-0 repartitioning | Closed in `storage_and_ram_budget_verifier.py` + `tier0_backup_worker.c`: `p20 -> p30`, `p21 -> tmpfs` VFAT loopback, `p15` `500 MiB` fit (`+74.81 MiB` image headroom) + Tier-0 read-only `/sys/block/nflasha/size` capture. |
| **`U2`** | Cross-model `tomco.txt` IPC compatibility & `cpapp-b.bin` (`nflasha8`) safety | Closed in Phase 10 `cp_rtos_compatibility_verifier.py` + Phase 18/21 `uipc_cp_shim_verifier.py`: FX3/FX6 `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) & 20 IPC keys are **100% identical**; FX3 Stock-CP implements `44/44` `0x92840747` opcodes + 5-axis IBIS center-lock while `P11` synthesizes `0x92d2091c`/`0x91db059b` under **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)**. |
| **`U3`** | Per-body `p6:Jiritsu`, `psd.bin`, `defdet.bin` & `lensfile.bin` calibration schema | Closed in `boot_selector_and_bank_verifier.py` + Stock-CP Redline: 64-slot `0xfa0080` Bank 0/1 zero-overlap proof; untouched FX3 stock CP consumes untouched FX3 per-body calibration partitions at native Bank 1 addresses. |
| **`U4`** | Non-fatal `Backup.bin` (`BK4\0`) missing keys & `/etc/opelog` mount fallback | Closed in `backup_mount_tolerance_verifier.py`: Unicorn AArch64 proof of clean fallback on `ENOENT`/`EINVAL`/`EROFS` in `SetupFile::RcvThread` (`0x19650`) & `KikiLogGenerator_res_ope` (`0x3cb0`) + `20,588 B` RAM-Shadow `BK4\0`. |
| **`U5`** | `ud_send_lsi` (`0x804b0376`) single-shot boot flag polarity & `p1` recovery lock | Closed in `boot_selector_and_bank_verifier.py` + Phase 11 `p1_recovery_bridge_verifier.py`: 10-case Unicorn audit of `ud_send_lsi.elf` + `loader_nor.bin` (`0xFE049000`) arbitrator + `fx3_recovery` `p1` FAT16/SquashFS/`p1chksum` container & mandatory 2-step atomic `p1` exit reset. |

- **Tier-0 Freestanding Backup Worker, `p1` Bridge, Readiness Packet, Post-Trial Zero-Mutation Auditor (`H0 -> H1 -> H2` Drill) & 12 Safety Gates**: Zero-import AArch64 Linux `svc #0` two-pass read-only backup worker (`native/tier0_backup_worker.c`, `11` mandatory items) verified in Unicorn, bridged offline with `fx3_recovery`, paired with Stage-A Hardware Readiness Packet (`make readiness-packet`), real Tier-0 capture validator (`verify_real_tier0_capture_bundle`), Phase 16 Post-Trial Zero-Mutation Receipt Auditor (`make lifecycle-drill`), bilingual [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md), and `fx3_safety` **12/12** pre-flash gates (`Gate G1..G12`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`).

### Track 4: FX3 Offline Recovery Adapter (`v0.5`), Global Unbrick Intel & Service Interface Tooling

- **Primary Package & Global Intel Dossier**: [`outputs/fx3-recovery-adapter/README.md`](outputs/fx3-recovery-adapter/README.md) · [`outputs/fx3-recovery-adapter/ROADMAP.md`](outputs/fx3-recovery-adapter/ROADMAP.md) · [`reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md`](reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md)
- Provides zero-dependency `inspect`, `build`, `verify`, `diagnose`, `rollback`, custom minimal ELF64 AArch64 linker (`fx3_recovery/elflink.py`), and zero-libc static capture workers for `/dev/cnflasha1` (`p1` updater, `25,100,288 B`) and `/dev/nflashaB0`/`B1` (`boot0`/`boot1`), cross-verified with Track 3 (`verify-p1-recovery-bridge`), aligned with 2025–2026 global Sony BIONZ XR RE (`ALCIN_UUD`, 4-site `nflasha1` parity, Multi-port `48000`-baud BootROM `uart_boot -> 0x92028000` Tier-3 unbricking, and WF-12 wireless bootloop isolation), and backed by **63** unit tests.

### Track 5 & Track 6: VENICE Color Science Research & Categorized Multi-Agent Session Archives

- **Color Science & Encoding Reports**: [FX5 Firmware & FX3 Cinema Menu Review](reports/FX5%20%E5%9B%BA%E4%BB%B6%E4%B8%8E%20FX3%20%E7%A7%BB%E6%A4%8D%E5%A4%8D%E6%A0%B8.md) · [VENICE Color Chain & 3DLUT Audit](reports/2026-10-31-venice-phayen-color-chain/REPORT.md) · [FX3 H.265/HEVC Encoding Pipeline](reports/%E7%B4%A2%E5%B0%BC%20FX3%20%E7%BC%96%E7%A0%81%E6%A8%A1%E5%BC%8F%E4%B8%8E%E5%86%99%E5%85%A5%E7%A0%94%E7%A9%B6.md).
- **Categorized Orca Engineering Archives**: **135** multi-agent research conversations across 5 specialized workspaces (`01-fx6-system-porting`, `02-fx5-unpack-and-cinema-color`, `03-fx3-firmware-re-and-h265`, `04-fx3-vm-menu-and-gpe`, `05-fx3-flash-safety-and-recovery`) are archived in **[conversations/README.md](conversations/README.md)** with clean-room secret/binary filtering.

---

## 3. Repository Directory Structure

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 5-suite Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test (`make test`), BYOF, dry-run, Phase 17..21, `make readiness-packet` & `make lifecycle-drill`
├── README.md                                # Bilingual (EN + ZH-CN) master documentation (Nov 14, 2026)
├── README.en.md                             # Standalone English documentation (Nov 14, 2026)
├── README.zh-CN.md                          # Standalone Simplified Chinese documentation (Nov 14, 2026)
├── docs/
│   ├── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
│   └── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent Stage-A hardware operator runbook
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 5-suite 271-test runner + BYOF manifest audit + `git status --porcelain` hygiene check
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # Controlled engineering packages & interactive VM launchers
│   ├── fx6-on-fx3-closure/                  # Phase 21 P1..P11+Fan, U1..U5, Stage-A/B, .ko/ABI, peripheral UX, imaging/UIPC-CP/IBIS, readiness & post-trial auditor (149 tests)
│   ├── fx6-native-presenter-closure/        # Cold-boot `nop_count=0` + Round 8 (Stage-A) & Round 9 (Stage-B `P10`) Hybrid QEMU GPE0 closure (20 tests)
│   ├── fx3-safety/                          # 12-Gate pre-flash safety evaluator, Sector-0/BK4 contracts & brick classifier (19 tests)
│   ├── fx3-recovery-adapter/                # FX3 Offline Recovery Adapter v0.5 & AArch64 static capture workers (63 tests)
│   ├── fx3-vm-trial/                        # Interactive FX3 & FX6 (Phase 19 native icons `image_00_169.uxc`, `60/60` multi-click stability) Web UI (20 tests)
│   └── fx3-vm/                              # FX3 Minimal QEMU AArch64 research VM & High-DDR / ESRAM patches
├── reports/                                 # Milestone technical reports & SHA-256 verification receipts
│   ├── 2026-11-14-phase19-live-icon-rendering/         # Phase 19 live FX6 native icon blitting + 60/60 multi-click freeze fix report
│   ├── 2026-11-14-phase20-p10-stage-b-integration/     # Phase 20 Stage-B combined `appFw.so` (`P1+P4+P8+P10`) & 21-key Unicorn report
│   ├── 2026-11-14-phase21-uipc-cp-shim-closure/        # Phase 21 `P11` UIPC-CP shim (`0x92d2091c`/`0x91db059b`), LUT DMA & IBIS report
│   ├── 2026-11-14-round9-fx6-on-fx3-p10-presenter/     # Round 9 FX6-on-FX3 Stage-B `P10` multi-scene QEMU Presenter (`r9a..r9d`) report
│   ├── 2026-11-14-global-sony-firmware-vm-unbrick-intel/ # 2025-2026 global Sony firmware RE, QEMU/IVSHMEM & Multi-port BootROM unbrick dossier
│   ├── 2026-11-14-fx6-on-fx3-qemu-hybrid/  # Round 8 FX6-on-FX3 Stage-A Hybrid QEMU E2E boot (`r8a..r8b`) evidence report
│   ├── 2026-11-14-phase17-fx3-input-display-audio-audit/ # Phase 17 FX3 controls (`P10`), touch, LCD/HDMI & `XLR-H1` audio report
│   ├── 2026-11-14-phase18-ap-cp-imaging-ibis-audit/      # Phase 18 AP<->Stock-CP imaging, 3D LUT, XAVC, AF & 5-axis IBIS report
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/     # Master Phase 1–16 compatibility, U1..U5, initrd/WBI, .ko/ABI, readiness, H0->H2 drill & 12-Gate report
│   ├── 2026-11-10-fx6-native-presenter-closure/ # Cold-boot `nop_count=0` GPE0 Rounds 1–7 (`r1a..r7c`, 20 PNG receipts) evidence report
│   ├── 2026-11-08-fx6-native-text-gpe0/     # 100% 128-page FX6 descriptor rendering evidence on physical GPE0
│   ├── 2026-11-03-fx6-full-system-to-fx3/   # FX6 6.01 -> FX3 7.02 30-partition & SPI NOR static compatibility matrix
│   └── 2026-11-01-fx3-vm-resumed-repair/    # AP70–AP105 FX3 menu bring-up reports & browser navigation records
└── conversations/                           # 135 categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Run All 271 Automated Tests, BYOF Audit, Donorless Clean-Room CI, Phase 17..21, Readiness Packet & Lifecycle Drill

```bash
# 1. Run all 271 automated tests across all 5 suites (63 + 19 + 149 + 20 + 20) + BYOF manifest audit + clean-room residue audit
make test

# 2. Simulate donorless Clean-Room CI locally (zero Sony firmware blobs required — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-peripheral-ux && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-ap-cp-imaging && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-stage-b-p10 && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-uipc-cp-shim && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 3. Verify bilingual docs/BYOF-REPRODUCTION.md SHA-256 manifest (57 EN + 57 ZH entries + 46 code constants + optional live donors)
make verify-byof

# 4. Run full offline FX6-on-FX3 candidate dry-run, Stage-A Readiness Packet & End-to-End H0->H1->H2 Lifecycle Drill
make dry-run
make readiness-packet
make lifecycle-drill

# 5. Run standalone Phase 11 p1 Bridge, Phase 12 Stage-A Orchestrator, Phase 14 Kmod/ABI, Phase 17..21 Peripheral/Imaging/Stage-B/UIPC-CP verifiers
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
```

### 4.2 Launch Interactive FX6 or FX3 Web Menu Emulators (Requires BYOF Setup)

After preparing your own official firmware files as documented in **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**:
1. **FX6 128-Page / Big6 Interactive Web UI**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
2. **FX3 Native Menu Interactive Web UI**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `./outputs/fx3-vm-trial/FX3菜单.command --check` to verify all SHA-256 input manifests without starting QEMU).

---
---

# 简体中文文档

## 1. 项目简介与净室开源范围

**`sony-fx3-fx6-lab`** 是围绕 **Sony Cinema Line ILME-FX3（Ver. 7.02，机型 ID `0x91030080`）** 与 **ILME-FX6（Ver. 6.01，机型 ID `0x91040086`）** 数字电影摄影机开展的净室系统工程、QEMU AArch64 虚拟化、跨机型兼容性验证与真机防变砖安全研究开源仓库。两款机型均基于 **Sony CXD90057 AArch64 SoC**，运行 Sony CE Linux `4.9.337-scel+` 内核与 TOPPERS-FMP 1.4.0 SMP RTOS 协处理器固件（`cpapp-b.bin` `@ 0x00108000`）。

> [!IMPORTANT]
> **净室开源合规边界说明（BYOF：自备官方固件复现）**
> 为严格遵守知识产权法规与仓库卫生规范，**本仓库包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）。我们 **100% 开源全部独立编写的 Python 离线校验器、无依赖 AArch64 C/汇编工作器、Unicorn 指令级仿真套件、QEMU 设备补丁、网页交互前端、SHA-256 验收回执与技术报告**。请参考 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护指纹一致性）自备对应 SHA-256 指纹的官方固件复现虚拟机运行环境。

---

## 2. 核心开发进度与技术里程碑（截至 2026-11-14）

### 主线 1A：FX6 128 页 Guest `GPE0` 实时互动 UI、Phase 19 原生图标渲染与 `60/60` 连击零死机修复

- **Phase 19 索尼 FX6 原生精灵图标（`image_00_169.uxc`）解码渲染与 `60/60` 多连击零崩溃根治**：只读叠加 `image_00_169.uxc` 并建立 LDEC 合法 `/dev/mem` GPE 物理内存池（`0x410524000..0x410e64000`）与 `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` 硬件混合器；拦截 `liblibra.so` 异步工作线程 `_ZN5libra20GenerateImageCommand6notifyEb`（`0x2a238`）悬垂回调、将静态单槽控件缓冲升级为 32 槽对齐环形池并串行化 GDB `finally` `$c#63` 恢复，顺利通过 **60/60 跨页快速连击压测（`0 APPFW_SEGV`，单页最高 `icon_n=119`，平均 `179.3 ms`/次，详见 [Phase 19 报告](reports/2026-11-14-phase19-live-icon-rendering/README.md)）**。
- **100% 全量 128 页原生描述符物理 `GPE0` 渲染与 22.1 倍 C 扫描线打包器**：将全部 **128 张页面描述符表**（`2,249` 行控件）真实渲染写入 `0x41e001000`（`GPE0`，`1024×540` RGBA32，`segv = 0`），配套 `fx6_pack_scanlines`（**22.1 倍**加速）、[`build_live700.py`](outputs/fx3-vm-trial/build_live700.py)、[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command) 与 **20 项**双模式单测（[`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)）。

### 主线 1B：FX6 原版冷启动 + Round 8 / Round 9 FX6-on-FX3 混合态 QEMU 闭环

- **受控工程目录与证据报告**：[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) · [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md) · [`reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md`](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md) · [`reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md`](reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md)
- **零指令 NOP 原版冷启动（`r1a..r7c`）、Round 8 Stage-A（`r8a..r8b`）与 Round 9 Stage-B `P10` 多场景闭环（`r9a..r9d`，26 张 PNG 凭证，20 项单测）**：在 **`FX6_NATIVE_FAITHFUL=1`**（`nop_count = 0`、`subst_* = 0`）下直接运行 **FX3 7.02 原厂内核 `vmlinux.bin`（`4.9.337-scel+`）**，并在 **Round 9** 完成 Guest 内 **11/11** Stage-B SHA-256 原子校验（`P10` 内存读回 `ok=1`），经 `SRM3KYE5 -> InfraInput` 注入真实 FX3 机身 `Fn`/`C1`/`C2`/`MENU`/`ENTER` 按键流，跑通 `r9a` 拍摄主屏 HUD（`sid=0x02`）、`r9b` Big6 主屏（`sid=0x0a`）、`r9c` Big6 参数子窗（`sid=0x0c`，含 `2,035` 个电影机琥珀色 `0xffffaa00` 高亮像素）与 `r9d` 全量菜单第 2 层（`sid=0x10`，`434,010` 像素，`87` 色）。

### 主线 2：FX3 原生固件 QEMU 虚拟机与可视化网页菜单模拟器

- **核心工程包与报告**：[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) · [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) · [`reports/2026-11-01-fx3-vm-resumed-repair/README.md`](reports/2026-11-01-fx3-vm-resumed-repair/README.md)
- 通过 [`fx3-esram-high-ddr.patch`](outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) 建模 `0x400000000` 高位 DDR（5 GiB）、`0xfe005000` ESRAM 邮箱、GICD、Sony 硬件定时器、SCU、GPIO Bank5、UIPC、DMM、GPE v13/v14 与软件 LDEC LZ77 解压，直接启动未修改的 FX3 7.02 `vmlinux.bin` 与原厂菜单；双击 `FX3菜单.command` 即可在浏览器按键交互（约 40.1 秒出首帧待机 OSD，已通过 32 键逐屏导航与 API16 恢复验收）。

### 主线 3：FX6-on-FX3 Phase 21 全栈兼容闭环（`P1..P11 + Fan`）、`U1..U5` 全清零与 12 道防变砖门禁

- **受控工程包与主报告**：[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) · [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md) · [`outputs/fx3-safety/`](outputs/fx3-safety/) · [`reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md`](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md) · [`reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md`](reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md) · [`reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md`](reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md) · [`reports/2026-11-14-phase20-p10-stage-b-integration/README.md`](reports/2026-11-14-phase20-p10-stage-b-integration/README.md) · [`reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md`](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)
- **全量兼容适配矩阵（`P1..P11 + Fan`）、Phase 20 Stage-B 联合 `appFw.so` 与 Phase 21 `P11` UIPC-CP 垫片闭环**：覆盖全部 ELF64 目标的确定性适配与 100% SHA-256 无损回滚；**Phase 20** 将 24 字节 `P10` 机身按键表集成进联合 Stage-B `appFw.so`（`P1+P4+P8+P10` 10 处共 41 B 零重叠、SHA-256 `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`、21 键 Unicorn 实测，`make verify-stage-b-p10`）；**Phase 21** 交付可执行 `P11` AP 侧 UIPC-CP 垫片（Unicorn 验证 `0x92d2091c` `/dev/rtc0->udate` 解除 `std::promise` 死锁与 `0x91db059b` 侧手柄离线应答并保留 `XLR-H1` 音频、`developing_mode_FHD -> 0x92840747` 翻译、`0x0165`/`0x0166` `33^3` 3D LUT DMA / 双原生 ISO `800`/`12800` 及 **FX3 5 轴 IBIS 音圈平台通电居中锁止**，`make verify-uipc-cp-shim`），全部接入 `fx3_safety` **12/12** 道安全门禁（`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`）。

### 主线 4：FX3 离线恢复适配工具（`v0.5`）、全球救砖情报同步与服务接口安全工具集

- **核心目录与全球情报卷宗**：[`outputs/fx3-recovery-adapter/README.md`](outputs/fx3-recovery-adapter/README.md) · [`outputs/fx3-recovery-adapter/ROADMAP.md`](outputs/fx3-recovery-adapter/ROADMAP.md) · [`reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md`](reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md)
- 提供针对 `/dev/cnflasha1`（`p1`）与 `/dev/nflashaB0`/`B1`（`boot0`/`boot1`）的 `inspect`、`build`、`verify`、`diagnose`、`rollback` 及无 libc AArch64 ELF 静态采集工作器，与主线 3 跨包桥接校验（`verify-p1-recovery-bridge`），同步对齐 2025–2026 全球索尼 BIONZ XR 固件逆向（`ALCIN_UUD`、4 处 `nflasha1` 偏移对齐）、QEMU/IVSHMEM 双核仿真、Multi-port `48000` 波特率 BootROM `uart_boot -> 0x92028000` 硬件级救砖与 WF-12 无线故障非阻塞隔离方案，并配套 **63 项** 单元与故障注入测试。

### 主线 5 与主线 6：VENICE 色彩科学审计与 135 篇多智能体对话分类归档

- **色彩与编码专项报告**：[FX5 固件与 FX3 电影菜单移植复核](reports/FX5%20%E5%9B%BA%E4%BB%B6%E4%B8%8E%20FX3%20%E7%A7%BB%E6%A4%8D%E5%A4%8D%E6%A0%B8.md) · [VENICE 色彩科学与 3DLUT 链路审计](reports/2026-10-31-venice-phayen-color-chain/REPORT.md) · [索尼 FX3 H.265/HEVC 编码与码率研究](reports/%E7%B4%A2%E5%B0%BC%20FX3%20%E7%BC%96%E7%A0%81%E6%A8%A1%E5%BC%8F%E4%B8%8E%E5%86%99%E5%85%A5%E7%A0%94%E7%A9%B6.md)。
- **Orca 多智能体工程归档**：五大专项工作区共 **135 篇** 工程研究对话已分类归档至 **[conversations/README.md](conversations/README.md)**（内置净室二进制过滤与密钥脱敏门禁）。

---

## 3. 快速开始（简体中文）

### 3.1 一键运行全部 271 项离线自动化测试、无供体净室 CI、BYOF 审计、Phase 17..21、真机就绪包与全周期演练

```bash
# 1. 一键运行全部 5 套测试集 (63 + 19 + 149 + 20 + 20 = 271 项测试) + BYOF 指纹审计 + git 净室零残留审计
make test

# 2. 本地模拟 GitHub Actions 无供体净室 CI 模式 (零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-peripheral-ux && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-ap-cp-imaging && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-stage-b-p10 && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-uipc-cp-shim && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 3. 单独校验中英双语 docs/BYOF-REPRODUCTION.md 清单 (57+57 项镜像、46 项源码常量与可选本地固件)
make verify-byof

# 4. 运行 FX6-on-FX3 完整候选包干跑验收、Stage-A 真机前预检就绪包与 H0->H1->H2 全生命周期沙盒演练
make dry-run
make readiness-packet
make lifecycle-drill

# 5. 单独运行 Phase 11 跨包 p1 桥接、Phase 12 Stage-A 原子编排、Phase 14 Kmod/ABI 及 Phase 17..21 专项校验器
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
```

### 3.2 在自备 BYOF 固件环境下启动 FX6 或 FX3 网页菜单模拟器

参照 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** 准备匹配 SHA-256 指纹的官方固件后：
- **启动 FX6 128 页 / Big6 实时网页模拟器**：运行 `./outputs/fx3-vm-trial/FX6菜单.command`，打开 `http://127.0.0.1:8768/`。
- **启动 FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（或加 `--check` 仅做 SHA-256 预检）。

---

## 4. 免责声明与开源许可 (Disclaimer & License)

1. 本仓库仅用于嵌入式系统架构研究、QEMU 虚拟化技术探索与固件刷前防变砖安全审计，与 Sony Group Corporation 无任何隶属或合作关系。
2. 本仓库不分发任何受版权保护的 Sony 专有闭源二进制文件或私有密钥。
3. 仓库自研源码采用 [MIT](./LICENSE) 协议发布；针对 QEMU 的修改补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议发布。
