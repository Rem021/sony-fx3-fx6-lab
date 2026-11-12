# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![English Standalone](https://img.shields.io/badge/Standalone_EN-README.en.md-0969da?style=flat)](./README.en.md)
[![简体中文独立版](https://img.shields.io/badge/独立中文版-README.zh--CN.md-0969da?style=flat)](./README.zh-CN.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-177%2F177_Passing_(make_test)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 Cold-Boot GPE0](https://img.shields.io/badge/FX6_Cold--Boot_GPE0-nop__count%3D0_r1a..r7c_(20_PNGs)-success?style=flat)](#track-1b-fx6-native-cold-boot-nop_count--0-gpe0-shooting-big6-base-look-3-layer-menu--backup_write-closure)
[![FX6-on-FX3 Closure](https://img.shields.io/badge/FX6--on--FX3_Closure-P1..P9%2BFan_%7C_U1..U5_%7C_H0--%3EH2_Drill-1a7f37?style=flat)](#track-3-fx6-on-fx3-p1p9--fan-closure-u1u5-closure--12-gate-anti-brick-suite)

> **Language Navigation / 语言切换**: **[English Documentation](#english-documentation)** · **[简体中文文档](#简体中文文档)** · **[Standalone `README.en.md`](./README.en.md)** · **[独立中文版 `README.zh-CN.md`](./README.zh-CN.md)**

> **2026-11-12 Master Milestones (全线工程里程碑闭环)**:
> 1. **Track 1A — Interactive FX6 128-Page Guest `GPE0` UI, 22.1x Pipeline Acceleration & 16 Offline Unit Tests**: Rendered **100% of all 128** FX6 Ver. 6.01 (`ILME-FX6V`) page descriptor tables (`2,249` widget rows) into physical `GPE0` (`0x41e001000`, `1024×540` RGBA32, `segv = 0`), refactored leak-free [`fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c) (eliminating per-frame `calloc` leaks, ~1,500 `dlsym` lookups, and `DISP` OOB reads), added a **22.1x faster** compiled C BGRA-to-PNG scanline packer (`fx6_pack_scanlines` in [`run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py)), delivered deterministic CPIO builder [`build_live700.py`](outputs/fx3-vm-trial/build_live700.py), and backed both Track 1A & Track 2 (`fx3-vm`) with **16** clean-room offline unit tests ([`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)).
> 2. **Track 1B — FX6 Native Cold-Boot `nop_count = 0` `GPE0` Shooting, Big6, Base Look, 3-Layer Menu & `Backup_write` Closure (`r1a..r7c`, 20 PNG Receipts, 12 Unit Tests)**: Delivered [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) ([Evidence Report](reports/2026-11-10-fx6-native-presenter-closure/README.md)), achieving **`nop_count = 0`** `FX6_NATIVE_FAITHFUL=1` (`subst_* = 0`) cold-boot and interactive navigation across 161 live threads on physical `GPE0` (`0x41e001000`): Initial Setting (`sid=0x03`), Shooting HUD (`sid=0x02`, `29` colors), native `0x7023` (`CANCEL`) APR dialog dismissal, Big6 Home (`sid=0x0a`, `74` colors), Big6 Setting (`sid=0x0c`, `59` colors), Cine EI Base Look (`sid=0x0b`, `66` colors), 1st/2nd/3rd-layer full menus (`sid=0x0f` / `0x10` / `0x11`), bit-identical `Presenter::close` return to Shooting, and live `Backup_write(0x02cf0546={0x01})` `S-Cinetone` Scene File mutation round-trip (`1,928`-px FreeType glyph delta).
> 3. **Track 3 & Track 4 — FX6-on-FX3 Phase 16 Closure (`P1..P9 + Fan`, `U1..U5`, `nflasha3-initrd` & `p5` WBI Hibernation Redline, Atomic Stage-A Orchestrator, Stage-A `.ko` / `/dev/*` / 60-ELF Linkage Closure, Pre-Flight Readiness Packet, Post-Trial Zero-Mutation Auditor & `H0 -> H1 -> H2` Lifecycle Drill, Donorless Clean-Room CI, `p1` Bridge, BYOF Auditor & `177/177` 5-Suite Automated Tests)**: Delivered [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md), [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md), [`outputs/fx3-safety/`](outputs/fx3-safety/), [`scripts/verify_byof_manifest.py`](scripts/verify_byof_manifest.py), & [`.github/workflows/clean-room-ci.yml`](.github/workflows/clean-room-ci.yml) ([Phase 16 Master Report](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md)), closing **all 10 compatibility items (`P1..P9 + Fan`)** with 100% SHA-256 rollback, **all 5 Blueprint Unknowns (`U1..U5`)**, Phase 10 `U2` Stock-CP Redline (`p8_cp_mutation_forbidden = True`), Phase 11 Cross-Package `p1` Recovery & Tier-0 Bridge (`fx3_recovery` ↔ `fx3_safety` ↔ `fx6_closure`), Phase 12 `nflasha3-initrd` boot-chain audit + `p5:/wbi` hibernation redline (`wbi_p5_write_and_hibernation_forbidden = True`) + 6-scenario POSIX `/bin/sh` atomic Verify-Before-Mount Stage-A orchestrator (`30-stage-a-orchestrator.sh`), Phase 14 Stage-A `insmod_drv1`/`insmod_drv2` 127-`.ko` matrix (`0` FX6 `.ko`s loaded, `0` `.ko` mutations) + `137` `/dev/*` node closure (`0` unaccounted) + `60`-ELF `DT_NEEDED`/`DYNSYM`/`VERNEED` linkage closure (`267/267` `VERNEED` satisfied, `0` unresolved required symbols) + donorless `FX3_FX6_FORCE_CLEAN_ROOM=1` GitHub Actions CI, Phase 15 deterministic Stage-A Hardware Readiness Packet (`stage_a_readiness_packet_v1`, `make readiness-packet`, `persistent_emmc_writes_authorized = False`), `verify_real_tier0_capture_bundle` fail-closed hardware backup validator & bilingual operator runbook, **Phase 16 Post-Trial Zero-Mutation Receipt Auditor (`stage_a_post_trial_auditor.py` / `verify-post-trial`) & End-to-End `H0 -> H1 -> H2` Lifecycle Sandbox Drill (`make lifecycle-drill`, 10 negative fault injections)**, Stage-A `cpio newc` (`30,956 B`) + 4-Layer Fail-Safe rollback (`0` eMMC writes), **12/12** pre-flash safety gates, automated bilingual BYOF SHA-256 manifest synchronization (`57+57` entries, `46` code constants via `make verify-byof`), and **`177/177` automated tests passing across all 5 suites via `make test`** (`63` `fx3-recovery-adapter` + `19` `fx3-safety` + `67` `fx6-on-fx3-closure` + `16` `fx3-vm-trial` + `12` `fx6-native-presenter-closure`).

---

# English Documentation

## 1. Executive Summary & Clean-Room Scope

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, QEMU AArch64 virtualization, cross-model compatibility verification, and hardware anti-brick safety research repository focused on the **Sony Cinema Line ILME-FX3 (Ver. 7.02, Model ID `0x91030080`)** and **ILME-FX6 (Ver. 6.01, Model ID `0x91040086`)** digital cinema cameras, both powered by the **Sony CXD90057 AArch64 SoC** running Sony CE Linux `4.9.337-scel+` alongside a TOPPERS-FMP 1.4.0 SMP RTOS co-processor (`cpapp-b.bin` `@ 0x00108000`).

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**
> To strictly respect intellectual property laws and repository hygiene, **this repository contains 0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` partition dumps, or `.cpio` rootfs images). We open-source **100% of our self-authored Python verifiers, freestanding AArch64 C/Assembly workers, Unicorn AArch64 emulation harnesses, QEMU device patches, Web UI frontends, SHA-256 receipts, and technical reports**. Donorless clones automatically verify cleanly via `FX3_FX6_FORCE_CLEAN_ROOM=1 make test` (and `.github/workflows/clean-room-ci.yml`). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded automatically by `make verify-byof`) for exact SHA-256 hashes when reproducing VM sessions with your own official firmware packages.

---

## 2. Development Progress & Technical Milestones (As of Nov 12, 2026)

### Track 1A: Interactive FX6 128-Page Guest `GPE0` UI & `fx3-vm-trial` Pipeline Optimization

- **100% 128-Page Descriptor Rendering on Physical `GPE0`**: Rendered all **128** native FX6 Ver. 6.01 (`ILME-FX6V`) page descriptor tables (`2,249` widget rows across `appFw.so` `0x02e90fb0..0x02eba7b8`) inside the ARM64 QEMU guest via `appFw.so` + `libuxengine.so` + `TextRM` directly into physical framebuffer `0x41e001000` (`GPE0`, `1024×540` RGBA32) with **`segv = 0`** ([EVIDENCE-751-812-FULL-128-PAGES.md](reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md)).
- **Leak-Free `fx6_live_guest.c` & 22.1x Compiled C Scanline Packer**:
  - Refactored [`outputs/fx3-vm-trial/src/fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c) to reuse static scratch buffers, eliminating per-frame `calloc` memory leaks, ~1,500 redundant `dlsym` lookups, and `DISP` out-of-bounds reads.
  - Added a compiled C BGRA-to-PNG scanline packer (`fx6_pack_scanlines` in [`outputs/fx3-vm-trial/run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py)) delivering a **22.1x host frame-packing speedup**, paired with deterministic pure-stdlib CPIO builder [`outputs/fx3-vm-trial/build_live700.py`](outputs/fx3-vm-trial/build_live700.py) and one-click launcher [`outputs/fx3-vm-trial/FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command).

### Track 1B: FX6 Native Cold-Boot `nop_count = 0` `GPE0` Shooting, Big6, Base Look, 3-Layer Menu & `Backup_write` Closure

- **Controlled Package & Evidence**: [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) · [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md)
- **Zero-Instruction-NOP Full Cold-Boot & Interactive Presenter Stack (`r1a..r7c`, 20 PNG Receipts, 12 Unit Tests)**: Maintaining strict evidence separation from Track 1A's direct descriptor viewer, Track 1B boots unmodified FX6 userland (`bootin` → `im.elf` → `appFw.so`) with **`nop_count = 0`**, **`subst_* = 0`**, and **`FX6_NATIVE_FAITHFUL=1`** across 161 live threads on physical `GPE0` (`0x41e001000`, `1024×540` `RGBA4444`/`RGBA8888`): verified Initial Setting (`sid=0x03`), Shooting HUD (`sid=0x02`, `29` ARGB colors), native `0x7023` (`CANCEL`) APR dialog dismissal, Big6 Home (`sid=0x0a`, `74` colors), Big6 Setting (`sid=0x0c`, `59` colors), Cine EI Base Look (`sid=0x0b`, `66` colors), 1st/2nd/3rd-layer full menus (`sid=0x0f` / `0x10` / `0x11`), bit-identical `Presenter::close` return to Shooting, and live `Backup_write(0x02cf0546={0x01})` `S-Cinetone` Scene File mutation round-trip (`1,928`-px FreeType glyph delta).

### Track 2: FX3 Native Firmware QEMU Virtual Machine & Interactive Web Menu Emulator

- **Primary Packages & Reports**: [`outputs/fx3-vm/`](outputs/fx3-vm/README.md) · [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) · [`reports/2026-11-01-fx3-vm-resumed-repair/README.md`](reports/2026-11-01-fx3-vm-resumed-repair/README.md)
- **Hardware Subsystem Modeling & AP70–AP105 Bring-Up**: Patches QEMU AArch64 ([`fx3-esram-high-ddr.patch`](outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch)) to map up to 5 GiB High DDR at `0x400000000`, 4 KiB ESRAM mailbox at `[0xfe005000, 0xfe006000)`, fixed GICD VA, Sony timers, SCU, GPIO Bank5, UIPC, DMM, GPE v13/v14, and software LDEC LZ77 asset decompression, booting unmodified FX3 7.02 `vmlinux.bin` + `appFw.so`.
- **Interactive Web Menu Launcher (`FX3菜单.command`)**: Starts a local browser UI (`4096`-key / `60`-minute session budget, ~`40.1s` start-to-first-OSD-frame latency, verified across 32-key live menu navigation and clean API16 shutdown restoration).

### Track 3: FX6-on-FX3 `P1..P9 + Fan` Closure, `U1..U5` Closure & 12-Gate Anti-Brick Suite

- **Controlled Packages & Master Reports**: [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) · [`outputs/fx3-safety/`](outputs/fx3-safety/) · [`reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md`](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md) · [`reports/2026-11-03-fx6-full-system-to-fx3/README.md`](reports/2026-11-03-fx6-full-system-to-fx3/README.md)
- **10/10 Compatibility Matrix (`P1..P9 + Fan`) & 100% SHA-256 Rollback**:
  - Deterministic ELF64 `PT_LOAD` / `ET_REL` adaptation and **100% bit-exact SHA-256 rollback** across all 7 binary targets (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `libInfraAppRemoteBoard.so`, `appFw.so`, `libfan.so`, `upm.ko`), pure-Python `8/16/44.5 MiB` `opelog.vfat` synthesis (`P2`), Unicorn-verified UIPC completion synthesis on `0x92840747` (`P5`/`P6`), and dual-kernel `pcidma_transfer_async` Sync100 trampoline verification (`P7`).
- **5-Feature Routing, FDT (`cxd90057.dtb`), `.ko` Load-Order Matrix, `/dev/*` Nodes & 60-ELF `DT_NEEDED`/`DYNSYM`/`VERNEED` Closure**:
  - 60-ELF transitive `DT_NEEDED` + `DYNSYM` + `VERNEED` closure (`0` missing `DT_NEEDED`, `0` unresolved required symbols, `0` patch `.dynsym` delta, `267/267` `GLIBC_*`/`CXXABI_*`/`GLIBCXX_*`/`GCC_*` `VERNEED` checks satisfied, and 100% FX3 vs FX6 base runtime ABI parity), `137` `/dev/*` paths audited across `61` FX6 userland binaries (`0` unaccounted), 100% byte-identical `insmod_drv1` (`4` `.ko`s) & `insmod_drv2` (`39` `.ko`s, `126` shared CXD90057 `.ko`s, `1` FX6-only `emg.ko` benignly skipped, `0` `.ko` mutations), 16x `33^3` `.cube` 3D LUT budget on FX3 `48.00 MiB` `p30` (`+32.04 MiB` headroom), 100% byte-identical 68-node / 493-property `cxd90057.dtb` (`16,875 B`, `0xd00dfeed`), and `P9` `upm.ko` `vermagic` + 61-symbol `modversion_info` CRC preservation.
- **Zero-Repartition `p15` / DDR `tmpfs` Budgets, `nflasha3-initrd` / WBI (`p5`) Redline & Atomic Stage-A Orchestrator**:
  - Enforces `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`) and **Stage-A WBI Hibernation Safety Redline (`wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`)** after auditing 27 `nflasha3-initrd` → `/usr` (`p15` `ext2 ro`) → `insmod_drv2` (`#24` `upm.ko`) → `im.elf` artifacts and FX6's `202,677,056 B` `p5` `WBI2` snapshot (`1,197` sections, `+13.47 MiB` `wbimem` collision vs FX3); proves `+138.76 MiB` raw / `+74.81 MiB` ext2-image headroom inside FX3's `500.00 MiB` `p15`, bounds Stage-A `tmpfs` peak usage to `57.46–130.76 MiB` within a `256.00 MiB` ceiling (`3.00%–6.82%` of `1,917.62 MiB` net Linux DDR), builds deterministic SVR4 `cpio newc` (`30,956 B`, 6 entries including `30-stage-a-orchestrator.sh`), and verifies both the 4 fail-safe rollback drills and **6 atomic Verify-Before-Mount + reverse LIFO teardown `/bin/sh` sandbox scenarios (10 runs)** with **`0` eMMC writes and `0` WBI writes**.
- **All 5 Blueprint Unknowns (`U1..U5`) Closed**:

| ID | Architectural Question | Verified Closure Module & Proof |
| :---: | :--- | :--- |
| **`U1`** | Total eMMC UDA geometry & partition headroom without Sector-0 repartitioning | Closed in `storage_and_ram_budget_verifier.py` + `tier0_backup_worker.c`: `p20 -> p30`, `p21 -> tmpfs` VFAT loopback, `p15` `500 MiB` fit (`+74.81 MiB` image headroom) + Tier-0 read-only `/sys/block/nflasha/size` capture. |
| **`U2`** | Cross-model `tomco.txt` IPC compatibility & `cpapp-b.bin` (`nflasha8`) safety | Closed in Phase 10 `cp_rtos_compatibility_verifier.py`: FX3/FX6 `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) & 20 IPC keys are **100% identical**; FX6 `cpapp-b.bin` (`17.12 MiB` `@ 0x00108000`) embeds 8 FX6-exclusive `Darwin` ND / `Mew` SDI-Genlock drivers → enforces **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)**. |
| **`U3`** | Per-body `p6:Jiritsu`, `psd.bin`, `defdet.bin` & `lensfile.bin` calibration schema | Closed in `boot_selector_and_bank_verifier.py` + Stock-CP Redline: 64-slot `0xfa0080` Bank 0/1 zero-overlap proof; untouched FX3 stock CP consumes untouched FX3 per-body calibration partitions at native Bank 1 addresses. |
| **`U4`** | Non-fatal `Backup.bin` (`BK4\0`) missing keys & `/etc/opelog` mount fallback | Closed in `backup_mount_tolerance_verifier.py`: Unicorn AArch64 proof of clean fallback on `ENOENT`/`EINVAL`/`EROFS` in `SetupFile::RcvThread` (`0x19650`) & `KikiLogGenerator_res_ope` (`0x3cb0`) + `20,588 B` RAM-Shadow `BK4\0`. |
| **`U5`** | `ud_send_lsi` (`0x804b0376`) single-shot boot flag polarity & `p1` recovery lock | Closed in `boot_selector_and_bank_verifier.py` + Phase 11 `p1_recovery_bridge_verifier.py`: 10-case Unicorn audit of `ud_send_lsi.elf` + `loader_nor.bin` (`0xFE049000`) arbitrator + `fx3_recovery` `p1` FAT16/SquashFS/`p1chksum` container & mandatory 2-step atomic `p1` exit reset. |

- **Tier-0 Freestanding Backup Worker, `p1` Bridge, Readiness Packet, Post-Trial Zero-Mutation Auditor (`H0 -> H1 -> H2` Drill) & 12 Safety Gates**: Zero-import AArch64 Linux `svc #0` two-pass read-only backup worker (`native/tier0_backup_worker.c`, `11` mandatory items) verified in Unicorn, bridged offline with `fx3_recovery` (`p1_recovery_bridge_verifier.py`), paired with deterministic Stage-A Hardware Readiness Packet (`hardware_readiness_packet.py` / `make readiness-packet`), real Tier-0 capture validator (`verify_real_tier0_capture_bundle`), **Phase 16 Post-Trial Zero-Mutation Receipt Auditor (`stage_a_post_trial_auditor.py` / `verify-post-trial` & `make lifecycle-drill` end-to-end `H0 -> H1 -> H2` sandbox + 10 fault injections)**, bilingual [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md), and `fx3_safety` **12/12** pre-flash gates (`Gate G1..G12`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`).

### Track 4: FX3 Offline Recovery Adapter (`v0.5`) & Service Interface Tooling

- **Primary Package**: [`outputs/fx3-recovery-adapter/README.md`](outputs/fx3-recovery-adapter/README.md) · [`outputs/fx3-recovery-adapter/ROADMAP.md`](outputs/fx3-recovery-adapter/ROADMAP.md)
- Provides zero-dependency `inspect`, `build`, `verify`, `diagnose`, `rollback`, custom minimal ELF64 AArch64 linker (`fx3_recovery/elflink.py`), and zero-libc static capture workers for `/dev/cnflasha1` (`p1` updater, `25,100,288 B`) and `/dev/nflashaB0`/`B1` (`boot0`/`boot1`), cross-verified with Track 3 (`verify-p1-recovery-bridge`) and backed by **63** unit, synthetic clean-room, and instruction-level fault-injection tests.

### Track 5 & Track 6: VENICE Color Science Research & Categorized Multi-Agent Session Archives

- **Color Science & Encoding Reports**: [FX5 Firmware & FX3 Cinema Menu Review](reports/FX5%20%E5%9B%BA%E4%BB%B6%E4%B8%8E%20FX3%20%E7%A7%BB%E6%A4%8D%E5%A4%8D%E6%A0%B8.md) · [VENICE Color Chain & 3DLUT Audit](reports/2026-10-31-venice-phayen-color-chain/REPORT.md) · [FX3 H.265/HEVC Encoding Pipeline](reports/%E7%B4%A2%E5%B0%BC%20FX3%20%E7%BC%96%E7%A0%81%E6%A8%A1%E5%BC%8F%E4%B8%8E%E5%86%99%E5%85%A5%E7%A0%94%E7%A9%B6.md).
- **Categorized Orca Engineering Archives**: **135** multi-agent research conversations across 5 specialized workspaces (`01-fx6-system-porting`, `02-fx5-unpack-and-cinema-color`, `03-fx3-firmware-re-and-h265`, `04-fx3-vm-menu-and-gpe`, `05-fx3-flash-safety-and-recovery`) are archived in **[conversations/README.md](conversations/README.md)** with clean-room secret/binary filtering.

---

## 3. Repository Directory Structure

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # Donorless Ubuntu + macOS 5-suite Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # Unified test (`make test`), BYOF, dry-run, `make readiness-packet` & `make lifecycle-drill`
├── README.md                                # Bilingual (EN + ZH-CN) master documentation (Nov 12, 2026)
├── README.en.md                             # Standalone English documentation (Nov 12, 2026)
├── README.zh-CN.md                          # Standalone Simplified Chinese documentation (Nov 12, 2026)
├── docs/
│   ├── BYOF-REPRODUCTION.md                 # Bilingual 57+57 entry SHA-256 firmware manifest & clean-room reproduction guide
│   └── STAGE-A-HARDWARE-RUNBOOK.md          # Bilingual Phase H0->H1->H2 non-persistent Stage-A hardware operator runbook
├── scripts/
│   ├── run_all_lab_tests.py                 # Unified 5-suite 177-test runner + BYOF manifest audit + `git status --porcelain` hygiene check
│   └── verify_byof_manifest.py              # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/                                 # Controlled engineering packages & interactive VM launchers
│   ├── fx6-on-fx3-closure/                  # Phase 16 P1..P9+Fan, U1..U5, initrd/WBI, Stage-A orchestrator, .ko/ABI, readiness & post-trial auditor (67 tests)
│   ├── fx6-native-presenter-closure/        # Cold-boot `nop_count=0` `FX6_NATIVE_FAITHFUL=1` GPE0 Shooting, Big6, Base Look & 3-layer menu closure (12 tests)
│   ├── fx3-safety/                          # 12-Gate pre-flash safety evaluator, Sector-0/BK4 contracts & brick classifier (19 tests)
│   ├── fx3-recovery-adapter/                # FX3 Offline Recovery Adapter v0.5 & AArch64 static capture workers (63 tests)
│   ├── fx3-vm-trial/                        # Interactive FX3 & FX6 (128-page `live700`, 22.1x C scanline packer) Web UI & offline tests (16 tests)
│   └── fx3-vm/                              # FX3 Minimal QEMU AArch64 research VM & High-DDR / ESRAM patches
├── reports/                                 # Milestone technical reports & SHA-256 verification receipts
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/     # Master Phase 1–16 compatibility, U1..U5, initrd/WBI, .ko/ABI, readiness, H0->H2 drill & 12-Gate report
│   ├── 2026-11-10-fx6-native-presenter-closure/ # Cold-boot `nop_count=0` GPE0 Rounds 1–7 (`r1a..r7c`, 20 PNG receipts) evidence report
│   ├── 2026-11-08-fx6-native-text-gpe0/     # 100% 128-page FX6 descriptor rendering evidence on physical GPE0
│   ├── 2026-11-03-fx6-full-system-to-fx3/   # FX6 6.01 -> FX3 7.02 30-partition & SPI NOR static compatibility matrix
│   └── 2026-11-01-fx3-vm-resumed-repair/    # AP70–AP105 FX3 menu bring-up reports & browser navigation records
└── conversations/                           # 135 categorized multi-agent engineering session archives across 5 workspaces
```

---

## 4. Quick Start & Verification

### 4.1 Run All 177 Automated Tests, BYOF Audit, Donorless Clean-Room CI, Readiness Packet & Lifecycle Drill

```bash
# 1. Run all 177 automated tests across all 5 suites (63 + 19 + 67 + 16 + 12) + BYOF manifest audit + clean-room residue audit
make test

# 2. Simulate donorless Clean-Room CI locally (zero Sony firmware blobs required — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 3. Verify bilingual docs/BYOF-REPRODUCTION.md SHA-256 manifest (57 EN + 57 ZH entries + 46 code constants + optional live donors)
make verify-byof

# 4. Run full offline FX6-on-FX3 candidate dry-run, Stage-A Readiness Packet & End-to-End H0->H1->H2 Lifecycle Drill
make dry-run
make readiness-packet
make lifecycle-drill

# 5. Run standalone Phase 11 p1 Bridge, Phase 12 Stage-A Atomic Orchestrator & Phase 14 Kmod/Userland ABI verifiers
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
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

## 2. 核心开发进度与技术里程碑（截至 2026-11-12）

### 主线 1A：FX6 128 页 Guest `GPE0` 实时互动 UI 与 `fx3-vm-trial` 管线加速

- **100% 全量 128 页原生描述符物理 `GPE0` 渲染**：在 ARM64 QEMU Guest 内通过 FX6 Ver. 6.01（`ILME-FX6V`）原生 `appFw.so` + `libuxengine.so` + `TextRM` 将全部 **128 张页面描述符表**（`0x02e90fb0..0x02eba7b8`，共 `2,249` 行控件）真实渲染写入物理帧缓冲 `0x41e001000`（`GPE0`，`1024×540` RGBA32），全程 **`segv = 0`**（详见 [EVIDENCE-751-812-FULL-128-PAGES.md](reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md)）。
- **零内存泄漏 `fx6_live_guest.c` 与 22.1 倍 C 扫描线打包器**：
  - 重构 [`outputs/fx3-vm-trial/src/fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c) 复用静态工作缓冲，彻底消除每帧 `calloc` 内存泄漏、约 1,500 次冗余 `dlsym` 查找开销及 `DISP` 越界读取。
  - 在 [`outputs/fx3-vm-trial/run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py) 中集成编译态 C 扫描线打包器 `fx6_pack_scanlines`，实现 **22.1 倍宿主机 BGRA→PNG 打包加速**，并配套纯标准库确定性 CPIO 构建器 [`outputs/fx3-vm-trial/build_live700.py`](outputs/fx3-vm-trial/build_live700.py) 与一键入口 [`outputs/fx3-vm-trial/FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)。

### 主线 1B：FX6 原版冷启动 `nop_count = 0` `GPE0` 拍摄、Big6、Base Look、三层菜单与参数持久化闭环

- **受控工程目录与证据报告**：[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) · [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md)
- **零指令 NOP 原版冷启动与全栈 Presenter 闭环（`r1a..r7c`，20 张 PNG 凭证，12 项单测）**：与主线 1A 描述符直绘严格证据分离，在 **`FX6_NATIVE_FAITHFUL=1`**（`nop_count = 0`、`subst_* = 0`）与 161 活跃线程完整冷启动生命周期下，以精确 `RGBA4444`/`RGBA8888` GPE0 解包连续跑通初始设置（`sid=0x03`）、拍摄主屏 HUD（`sid=0x02`，`29` 色）、原生 `0x7023`（`CANCEL`）冷启动提示窗关闭、Big6 主屏（`sid=0x0a`，`74` 色）、Big6 参数子窗（`sid=0x0c`，`59` 色）、Cine EI Base Look（`sid=0x0b`，`66` 色）、1/2/3 层完整菜单树（`sid=0x0f` / `0x10` / `0x11`）、`Presenter::close` 逐位一致退回拍摄主屏，以及 `Backup_write(0x02cf0546={0x01})` `S-Cinetone` 实时参数修改持久化往返（`1,928` 像素字形增量）。

### 主线 2：FX3 原生固件 QEMU 虚拟机与可视化网页菜单模拟器

- **核心工程包与报告**：[`outputs/fx3-vm/`](outputs/fx3-vm/README.md) · [`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md) · [`reports/2026-11-01-fx3-vm-resumed-repair/README.md`](reports/2026-11-01-fx3-vm-resumed-repair/README.md)
- 通过 [`fx3-esram-high-ddr.patch`](outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) 建模 `0x400000000` 高位 DDR（5 GiB）、`0xfe005000` ESRAM 邮箱、GICD、Sony 硬件定时器、SCU、GPIO Bank5、UIPC、DMM、GPE v13/v14 与软件 LDEC LZ77 解压，直接启动未修改的 FX3 7.02 `vmlinux.bin` 与原厂菜单；双击 `FX3菜单.command` 即可在浏览器按键交互（约 40.1 秒出首帧待机 OSD，已通过 32 键逐屏导航与 API16 恢复验收）。

### 主线 3：FX6-on-FX3 `P1..P9 + Fan` 兼容闭环、`U1..U5` 全清零与 12 道防变砖门禁

- **受控工程包与主报告**：[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) · [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md) · [`outputs/fx3-safety/`](outputs/fx3-safety/) · [`reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md`](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md) · [`reports/2026-11-03-fx6-full-system-to-fx3/README.md`](reports/2026-11-03-fx6-full-system-to-fx3/README.md)
- **10/10 兼容适配矩阵（`P1..P9 + Fan`）与 100% SHA-256 无损回滚**：覆盖全部 7 个 ELF64 二进制目标（`libInfraSetupFile.so`、`libInfraMediaCommon.so`、`libInfraMediaConfig.so`、`libInfraAppRemoteBoard.so`、`appFw.so`、`libfan.so`、`upm.ko`）的确定性适配与逐字节 SHA-256 还原、纯 Python `8/16/44.5 MiB` `opelog.vfat` 合成（`P2`）、`0x92840747` 端点 UIPC 应答合成（`P5`/`P6`，Unicorn 实测验证）及双内核 `pcidma_transfer_async` Sync100 跳板校验（`P7`）。
- **5 大特性路由、FDT（`cxd90057.dtb`）、Stage-A `.ko` 加载矩阵、`/dev/*` 节点与 60-ELF `DT_NEEDED`/`DYNSYM`/`VERNEED` 闭包**：验证 60 个 ELF 的传递 `DT_NEEDED` + `DYNSYM` + `VERNEED` 闭包（`0` 缺失依赖、`0` 未决强导入、`0` 补丁符号表偏移、`267/267` `VERNEED` 满足、FX3/FX6 基础运行时 ABI 100% 对齐）、61 个用户态二进制的 `137` 条 `/dev/*` 节点全量归类（`0` 未知）、FX3/FX6 100% 逐字节一致的 `insmod_drv1`（`4` 个 `.ko`）与 `insmod_drv2`（`39` 个 `.ko`，`126` 共享 CXD90057 `.ko`，`1` 个 FX6 独占 `emg.ko` 安全跳过，`0` `.ko` 篡改）、FX3 `48.00 MiB` `p30` 上的 16 组 `33^3` `.cube` LUT 余量（`+32.04 MiB`）、`cxd90057.dtb`（`16,875 B`）以及 `P9` `upm.ko` 的 `vermagic` 与 61 项 `modversion_info` CRC 零漂移。
- **零重分区 `p15` / DDR `tmpfs` 容量预算、`nflasha3-initrd` / WBI（`p5`）休眠安全红线与 Stage-A 原子编排器**：锁定 `edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）与 **Stage-A WBI 休眠红线（`wbi_p5_write_and_hibernation_forbidden = True`，`wbi_mutation_bytes = 0`）**（审计 27 项 `nflasha3-initrd` → `/usr` 只读 → `insmod_drv2` `#24` `upm.ko` → `im.elf` 启动链工件及 FX6 `202,677,056 B` `p5` `WBI2` 休眠头与 `+13.47 MiB` `wbimem` 地址碰撞），证明 FX3 `500.00 MiB` `p15` 具备 `+138.76 MiB` 裸载荷 / `+74.81 MiB` ext2 镜像余量，Stage-A `tmpfs` 峰值仅 `57.46–130.76 MiB`（严守 `256.00 MiB` 上限）；生成确定性 SVR4 `cpio newc`（`30,956 B`，含 `30-stage-a-orchestrator.sh` 共 6 项），并在 `/bin/sh` 隔离沙盒中验证 4 类掉电回滚与 **6 大 Verify-Before-Mount 原子校验 + 逆序 LIFO 卸载场景（10 次执行）** 全程 **`0` 字节 eMMC 写入与 `0` 字节 WBI 写入**。
- **五大蓝图未知项（`U1..U5`）100% 离线验证清零**：
  - **`U1`**：30 分区零重分区映射（`p20 -> p30`、`p21 -> tmpfs` VFAT 回环、`p15` `500 MiB` 余量）+ Tier-0 只读 `/sys/block/nflasha/size` 采集闭环。
  - **`U2`**：Phase 10 `cp_rtos_compatibility_verifier.py` 证明 FX3 与 FX6 `tomco.txt` 的 4 段 `memcfg=`（`1,724.00 MiB`）与 20 项 IPC 键值 **100% 相同**，定位 FX6 `cpapp-b.bin`（`17.12 MiB` `@ 0x00108000`）中 8 项 FX6 独占硬件风险（`Darwin` 可变 ND 与 `Mew` SDI/Genlock FPGA），强制执行 **Stage-A 原厂 CP 红线（`p8_cp_mutation_forbidden = True`，`cp_mutation_bytes = 0`）**。
  - **`U3`**：`0xfa0080` 64 槽位 Bank 0/1 零重叠证明 + 原厂 CP 红线（FX3 原厂 CP 直接消费本机原厂 `psd.bin` / `defdet.bin` / `lensfile.bin` / `p6:Jiritsu`）。
  - **`U4`**：Unicorn AArch64 证明 `SetupFile::RcvThread`（`0x19650`）与 `KikiLogGenerator_res_ope`（`0x3cb0`）在 `ENOENT`/`EINVAL`/`EROFS` 下非致命安全降级 + `20,588 B` RAM-Shadow `BK4\0`。
  - **`U5`**：`ud_send_lsi.elf`（`0x804b0376`）+ `loader_nor.bin`（`0xFE049000`）10 组 Unicorn 边界案例 + Phase 11 `p1_recovery_bridge_verifier.py` 跨包恢复容器与两步原子 `p1` 退出复位验证。
- **Tier-0 无依赖只读备份、`p1` 恢复桥接、Stage-A 真机前就绪包、试运行后零写入审计器（`H0 -> H1 -> H2` 全周期演练）与 12 道安全门禁**：零外部符号 AArch64 `svc #0` 双遍只读备份工作器（覆盖 11 项关键分区）通过 Unicorn 全路径验证，联合 Phase 11 `p1_recovery_bridge_verifier.py` 对齐 `fx3_recovery`，提供 Phase 15 确定性 Stage-A 真机就绪包（`hardware_readiness_packet.py` / `make readiness-packet`）、真实 Tier-0 采集包校验器（`verify_real_tier0_capture_bundle`）、**Phase 16 试运行后零写入回执审计器（`stage_a_post_trial_auditor.py` / `verify-post-trial` 与 `make lifecycle-drill` 端到端 `H0 -> H1 -> H2` 沙盒 + 10 项故障注入测试）**、中英双语操作手册 [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md)，并与 `fx3_safety` **12/12** 道门禁联动（`Gate G1..G12`，`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`）。

### 主线 4：FX3 离线恢复适配工具（`v0.5`）与服务接口安全工具集

- **核心目录**：[`outputs/fx3-recovery-adapter/README.md`](outputs/fx3-recovery-adapter/README.md) · [`outputs/fx3-recovery-adapter/ROADMAP.md`](outputs/fx3-recovery-adapter/ROADMAP.md)
- 提供针对 `/dev/cnflasha1`（`p1`）与 `/dev/nflashaB0`/`B1`（`boot0`/`boot1`）的 `inspect`、`build`、`verify`、`diagnose`、`rollback` 及无 libc AArch64 ELF 静态采集工作器，与主线 3 跨包桥接校验（`verify-p1-recovery-bridge`）并配套 **63 项** 单元、净室合成与故障注入测试。

### 主线 5 与主线 6：VENICE 色彩科学审计与 135 篇多智能体对话分类归档

- **色彩与编码专项报告**：[FX5 固件与 FX3 电影菜单移植复核](reports/FX5%20%E5%9B%BA%E4%BB%B6%E4%B8%8E%20FX3%20%E7%A7%BB%E6%A4%8D%E5%A4%8D%E6%A0%B8.md) · [VENICE 色彩科学与 3DLUT 链路审计](reports/2026-10-31-venice-phayen-color-chain/REPORT.md) · [索尼 FX3 H.265/HEVC 编码与码率研究](reports/%E7%B4%A2%E5%B0%BC%20FX3%20%E7%BC%96%E7%A0%81%E6%A8%A1%E5%BC%8F%E4%B8%8E%E5%86%99%E5%85%A5%E7%A0%94%E7%A9%B6.md)。
- **Orca 多智能体工程归档**：五大专项工作区共 **135 篇** 工程研究对话已分类归档至 **[conversations/README.md](conversations/README.md)**（内置净室二进制过滤与密钥脱敏门禁）。

---

## 3. 快速开始（简体中文）

### 3.1 一键运行全部 177 项离线自动化测试、无供体净室 CI、BYOF 审计、真机就绪包与全周期演练

```bash
# 1. 一键运行全部 5 套测试集 (63 + 19 + 67 + 16 + 12 = 177 项测试) + BYOF 指纹审计 + git 净室零残留审计
make test

# 2. 本地模拟 GitHub Actions 无供体净室 CI 模式 (零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 3. 单独校验中英双语 docs/BYOF-REPRODUCTION.md 清单 (57+57 项镜像、46 项源码常量与可选本地固件)
make verify-byof

# 4. 运行 FX6-on-FX3 完整候选包干跑验收、Stage-A 真机前预检就绪包与 H0->H1->H2 全生命周期沙盒演练
make dry-run
make readiness-packet
make lifecycle-drill

# 5. 单独运行 Phase 11 跨包 p1 桥接、Phase 12 Stage-A 原子编排与 Phase 14 Kmod/用户态 ABI 校验器
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
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
