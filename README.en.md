# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-147%2F147_Passing_(make_test)-brightgreen?style=flat)](#4-quick-start--verification)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

> **Switch Language**: [**👉 点击切换至简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master Overview (`README.md`)**](./README.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, QEMU AArch64 virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (Ver. 7.02, Model ID `0x91030080`)** and **ILME-FX6 (Ver. 6.01, Model ID `0x91040086`)** digital cinema cameras, both powered by the **Sony CXD90057 AArch64 SoC** running Sony CE Linux `4.9.337-scel+` alongside a TOPPERS-FMP 1.4.0 SMP RTOS co-processor (`cpapp-b.bin` `@ 0x00108000`).

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images). All self-authored Python verifiers, freestanding C/Assembly workers, Unicorn AArch64 harnesses, QEMU patches, Web UI frontends, and SHA-256 receipts operate in clean-room mode. See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded by `make verify-byof`) for exact SHA-256 digests when reproducing VM sessions with your own official firmware packages.

---

## 1. Engineering Milestones (As of Nov 10, 2026)

### Track 1A — Interactive FX6 128-Page Guest `GPE0` UI & `fx3-vm-trial` Pipeline Optimization
- **100% 128-Page In-Guest Rendering**: Rendered all **128** native FX6 Ver. 6.01 (`ILME-FX6V`) page descriptor tables (`2,249` widget rows in `appFw.so` `0x02e90fb0..0x02eba7b8`) via ARM64 `appFw.so` + `libuxengine.so` + `TextRM` into physical framebuffer `0x41e001000` (`GPE0`, `1024×540` RGBA32) with **`segv = 0`** ([EVIDENCE-751-812-FULL-128-PAGES.md](reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md)).
- **Leak-Free Guest Driver, 22.1x C Scanline Packer & 16 Offline Unit Tests**: Refactored [`outputs/fx3-vm-trial/src/fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c) with static scratch buffer reuse (eliminating per-frame `calloc` leaks, ~1,500 `dlsym` lookups, and `DISP` out-of-bounds reads), added a **22.1x faster** compiled C BGRA-to-PNG scanline packer (`fx6_pack_scanlines` in [`outputs/fx3-vm-trial/run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py)), delivered deterministic pure-stdlib CPIO builder [`outputs/fx3-vm-trial/build_live700.py`](outputs/fx3-vm-trial/build_live700.py), and backed both Track 1A & Track 2 (`fx3-vm`) with **16** clean-room offline unit tests ([`outputs/fx3-vm-trial/tests/test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)).

### Track 1B — FX6 Native Cold-Boot `nop_count = 0` `GPE0` Foreground Glyphs & Shooting HUD
- **Zero-Instruction-NOP Cold-Boot Breakthrough (`256314b5`)**: Delivered [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) and [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md), achieving **`nop_count = 0`** `FX6_NATIVE_FAITHFUL=1` cold-boot foreground glyph rendering across both **`37procam_menu_initial_setting_presenter`** (Initial Setting Menu) and **`25procam_shooting_presenter`** (Shooting HUD) directly onto physical `GPE0` (`0x41e001000`, `1024×540`) over the full 153-TID `MWF_Init` + `ScreenManager` + `GraphicsEngine::drawFramebuffer()` lifecycle.

### Track 2 — FX3 Native Firmware QEMU Virtual Machine & Interactive Web Menu Emulator
- **Unmodified FX3 7.02 Kernel & Camera Menu (`outputs/fx3-vm/`, `outputs/fx3-vm-trial/`)**: Models CXD90057 High DDR (`0x400000000`), ESRAM mailbox (`0xfe005000`), GICD, Sony timers, SCU, GPIO Bank5, UIPC, DMM, GPE v13/v14, and software LDEC LZ77 decompression, exposing a live browser-controlled FX3 camera menu (`FX3菜单.command`, 4096-key / 60-minute budget, ~40.1s start-to-first-OSD-frame, verified across 32-key live navigation and API16 clean restoration).

### Track 3 — FX6-on-FX3 `P1..P9 + Fan` Compatibility Closure, `U1..U5` Closure & 12-Gate Anti-Brick Suite
- **Controlled Source Packages**: [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) & [`outputs/fx3-safety/`](outputs/fx3-safety/) ([Phase 13 Verification Report](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md)):
  - **10/10 Binary & Protocol Matrix (`P1..P9 + Fan`)**: Deterministic ELF64 `PT_LOAD` / `ET_REL` adaptation with **100% bit-exact SHA-256 rollback** across all 7 binary targets (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `libInfraAppRemoteBoard.so`, `appFw.so`, `libfan.so`, `upm.ko`), pure-Python `8/16/44.5 MiB` `opelog.vfat` synthesis (`P2`), Unicorn-verified UIPC completion synthesis on `0x92840747` (`P5`/`P6`), and dual-kernel `pcidma_transfer_async` Sync100 trampoline verification (`P7`).
  - **5-Feature Routing, FDT (`cxd90057.dtb`) & `.ko` Integrity**: 43-ELF `DT_NEEDED` dynamic symbol closure (`0` missing), 16x `33^3` `.cube` LUT budget on FX3 `48.00 MiB` `p30` (`+32.04 MiB` headroom), 100% byte-identical 68-node / 493-property `cxd90057.dtb` (`0xd00dfeed`) & 7 `kemco.txt` `memrsv=` carveouts, and `P9` `upm.ko` `vermagic` + 61-symbol `modversion_info` CRC preservation.
  - **Zero-Repartition `p15` / DDR `tmpfs` Budgets, `nflasha3-initrd` / WBI (`p5`) Redline & Atomic Stage-A Orchestrator**: Proves `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`), **Stage-A WBI Hibernation Safety Redline (`wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`)** across 27 `nflasha3-initrd` → `/usr` (`p15` `ext2 ro`) → `insmod_drv2` (`#24` `upm.ko`) → `im.elf` artifacts and FX6's `202,677,056 B` `p5` `WBI2` snapshot (`1,197` sections, `+13.47 MiB` `wbimem` collision vs FX3), `+138.76 MiB` raw / `+74.81 MiB` ext2-image headroom inside FX3's `500.00 MiB` `p15`, and `57.46–130.76 MiB` peak Stage-A `tmpfs` usage within a `256.00 MiB` ceiling (`3.00%–6.82%` of `1,917.62 MiB` net Linux DDR); packages deterministic SVR4 `cpio newc` (`30,860 B`, 6 entries including `30-stage-a-orchestrator.sh`) and verifies both 4 fail-safe rollback scenarios and **6 atomic Verify-Before-Mount + reverse LIFO teardown `/bin/sh` sandbox scenarios (10 runs)** with **`0` eMMC writes and `0` WBI writes**.
  - **All 5 Blueprint Unknowns (`U1..U5`) Closed**:
    - **`U1`**: Closed via 30-partition zero-repartition mapping (`p20 -> p30`, `p21 -> tmpfs` VFAT loopback, `p15` `500 MiB` fit) + Tier-0 read-only `/sys/block/nflasha/size` capture.
    - **`U2`**: Closed via `cp_rtos_compatibility_verifier.py` — proves 100% identical `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) & 20 IPC keys, pinpoints 8 FX6-exclusive CP hardware hazards (`Darwin` variable ND + `Mew` SDI/Genlock FPGA) in FX6 `cpapp-b.bin` (`17.12 MiB` `@ 0x00108000`), and enforces the **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)**.
    - **`U3`**: Closed via 64-slot `0xfa0080` Bank 0/1 zero-overlap proof + Stock-CP Redline (FX3 stock CP consumes FX3 stock per-body `psd.bin` / `defdet.bin` / `lensfile.bin` / `p6:Jiritsu` at native Bank 1 addresses).
    - **`U4`**: Closed via Unicorn AArch64 proof of non-fatal `ENOENT`/`EINVAL`/`EROFS` fallback in `SetupFile::RcvThread` (`0x19650`) & `KikiLogGenerator_res_ope` (`0x3cb0`) + `20,588 B` RAM-Shadow `BK4\0` synthesis.
    - **`U5`**: Closed via 10-case Unicorn audit of `ud_send_lsi.elf` (`0x804b0376`) + `loader_nor.bin` (`0xFE049000`) arbitrator + Phase 11 `p1_recovery_bridge_verifier.py` (`fx3_recovery` `p1` FAT16/SquashFS/`p1chksum` container & mandatory 2-step atomic `p1` exit reset).
  - **Tier-0 Worker, Cross-Package `p1` Recovery Bridge & 12 Safety Gates**: Zero-import AArch64 Linux `svc #0` two-pass read-only backup worker (`native/tier0_backup_worker.c`) verified in Unicorn across 11 mandatory partitions, bridged offline with `fx3_recovery`, and integrated with `fx3_safety` **12/12** pre-flash gates (`persistent_write_release = False`).

### Track 4 — FX3 Offline Recovery Adapter (`v0.5`) & USB Service Protocol Tooling
- **Zero-Dependency `p1` & Boot-Partition Suite (`outputs/fx3-recovery-adapter/`)**: Provides `inspect`, `build`, `verify`, `diagnose`, `rollback`, and standalone zero-libc AArch64 ELF capture workers for `/dev/cnflasha1` (`p1` updater) and `/dev/nflashaB0`/`B1` (`boot0`/`boot1`), cross-verified with Track 3 (`verify-p1-recovery-bridge`) and backed by **58** unit and Unicorn instruction-level fault-injection tests.

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
| **01 — Update Container** | `BODYDATA.DAT` (`sauu` / `sdfileinput.elf`) | Model ID (`0x91030080` vs `0x91040086`), region, and cryptographic checks execute strictly inside userland `p1` updater flows. |
| **02 — Octal-SPI NOR Boot** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | `pformat_config.txt` (`1,274 B`) and `LdrBkupList.txt` (`65` keys) are 100% byte-identical across FX3 7.02 and FX6 6.01 (`@ 0xFE049000`). |
| **03 — Bank 0/1 Descriptors** | `p2:/setting/Backup.bin` (`0x00fa0080`) | 64-slot (`9,216 B`) Bank 0 (AP) & Bank 1 (CP/calibration) tables verified with 0-byte pairwise DDR overlap; Bank 0 AP load addresses are 100% identical. |
| **04 — Kernel, FDT & CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb` (`16,875 B`) & `tomco.txt` 4x `memcfg=` (`1,724.00 MiB`) are 100% identical; Stage-A keeps stock FX3 kernel, stock `p8:/cpapp-b.bin` (`@ 0x00108000`), and `p5:/wbi` hibernation blocked. |
| **05 — Camera Userland** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | `30-stage-a-orchestrator.sh` verifies all 11 digests before first mount, activates `tmpfs` RAM-Overlay (`0` eMMC/WBI writes), and tears down in strict reverse LIFO order. |

---

## 3. Repository Layout

```text
sony-fx3-fx6-lab/
├── Makefile                                    # Unified test (`make test`), BYOF audit (`make verify-byof`) & dry-run (`make dry-run`)
├── README.md                                   # Bilingual (EN + ZH-CN) comprehensive master documentation
├── README.en.md                                # Standalone English documentation (Nov 10, 2026)
├── README.zh-CN.md                             # Standalone Simplified Chinese documentation (Nov 10, 2026)
├── docs/
│   └── BYOF-REPRODUCTION.md                    # Clean-room bilingual 51+51 entry SHA-256 firmware manifest & reproduction guide
├── scripts/
│   ├── run_all_lab_tests.py                    # Unified 4-suite 147-test runner + BYOF manifest audit + `git status --porcelain` hygiene auditor
│   └── verify_byof_manifest.py                 # Bilingual BYOF SHA-256 schema, code-constant & live-donor manifest auditor
├── outputs/
│   ├── fx6-on-fx3-closure/                     # Phase 12 P1..P9+Fan, U1..U5, initrd/WBI, Stage-A orchestrator, p1 bridge & Tier-0 (56 tests)
│   ├── fx6-native-presenter-closure/           # Cold-boot `nop_count=0` `FX6_NATIVE_FAITHFUL=1` GPE0 glyphs & Shooting HUD closure
│   ├── fx3-safety/                             # 12-Gate pre-flash safety evaluator, Sector-0/BK4 contracts & brick classifier (17 tests)
│   ├── fx3-recovery-adapter/                   # FX3 Offline Recovery Adapter v0.5 & AArch64 static capture workers (58 tests)
│   ├── fx3-vm-trial/                           # Interactive FX3 & FX6 (128-page `live700`, 22.1x C scanline packer) Web UI & offline tests (16 tests)
│   └── fx3-vm/                                 # Minimal FX3 QEMU AArch64 research VM & High-DDR / ESRAM patches
├── reports/
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/        # Master Phase 1–13 compatibility, U1..U5, initrd/WBI, p1 bridge & 12-Gate report
│   ├── 2026-11-10-fx6-native-presenter-closure/# Cold-boot `nop_count=0` GPE0 foreground glyph & Shooting HUD evidence report
│   ├── 2026-11-08-fx6-native-text-gpe0/        # 100% 128-page FX6 descriptor rendering evidence on physical GPE0
│   └── 2026-11-03-fx6-full-system-to-fx3/      # FX6 6.01 vs FX3 7.02 full 30-partition & SPI NOR static audit
└── conversations/                              # Categorized multi-agent engineering session archives
```

---

## 4. Quick Start & Verification

### 4.1 Run All 147 Automated Tests, BYOF Audit & Clean-Room Check (`make test` / `make verify-byof`)

```bash
# Run all 4 suites (58 fx3-recovery-adapter + 17 fx3-safety + 56 fx6-on-fx3-closure + 16 fx3-vm-trial = 147 tests) + BYOF & binary/.pyc hygiene check
make test

# Verify bilingual docs/BYOF-REPRODUCTION.md SHA-256 manifest (51 EN + 51 ZH entries + 40 code constants + optional live donors)
make verify-byof

# Run full offline FX6-on-FX3 candidate dry-run (P1..P9 + Fan + U1..U5 + CP RTOS + p1 Bridge + Stage-A/WBI + 12/12 Safety Gates)
make dry-run

# Run standalone Phase 11 p1 Bridge & Phase 12 nflasha3-initrd / WBI (p5) / Stage-A Atomic Orchestrator verifiers
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
```

### 4.2 Launch Interactive FX3 or FX6 Web Menu Emulators (Requires BYOF Setup)

After preparing your own official firmware files per **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**:
- **FX6 128-Page / Big6 Interactive Trial**: Run `./outputs/fx3-vm-trial/FX6菜单.command` and open `http://127.0.0.1:8768/`.
- **FX3 Native Menu Trial**: Run `./outputs/fx3-vm-trial/FX3菜单.command` (or `--check` to verify SHA-256 manifests without starting QEMU).

---

## 5. Legal & Clean-Room Compliance Notice

1. **Zero Proprietary Firmware**: This repository distributes **0 bytes** of Sony binary firmware, encrypted update images, or private cryptographic keys.
2. **Independent Interoperability & Safety Research**: All source code, Unicorn emulation harnesses, and technical reports are authored independently for embedded systems research, virtualization, and hardware anti-brick safety auditing, with no affiliation with Sony Group Corporation.
3. **Licensing**: Repository source code is released under [MIT](./LICENSE); QEMU patches follow [GPLv2](outputs/fx3-vm/COPYING-QEMU).
