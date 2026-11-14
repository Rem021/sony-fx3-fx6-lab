# Sony FX3 & FX6 Porting, QEMU Virtual Machine & Clean-Room Compatibility Lab (`sony-fx3-fx6-lab`)

[![简体中文](https://img.shields.io/badge/Language-简体中文-0969da?style=flat)](./README.zh-CN.md)
[![Bilingual](https://img.shields.io/badge/Master_Doc-README.md_(EN_%2B_ZH)-1a7f37?style=flat)](./README.md)
[![Platform](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![Target](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![Tests](https://img.shields.io/badge/Automated_Tests-271_Passing_(make_test)-brightgreen?style=flat)](#4-quick-start--verification)
[![Clean-Room CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![License](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

> **Switch Language**: [**👉 点击切换至简体中文完整版 (`README.zh-CN.md`)**](./README.zh-CN.md) · [**Bilingual Master Overview (`README.md`)**](./README.md)

**`sony-fx3-fx6-lab`** is a clean-room systems engineering, QEMU AArch64 virtualization, hardware-compatibility verification, and anti-brick safety research repository for the **Sony Cinema Line ILME-FX3 (Ver. 7.02, Model ID `0x91030080`)** and **ILME-FX6 (Ver. 6.01, Model ID `0x91040086`)** digital cinema cameras, both powered by the **Sony CXD90057 AArch64 SoC** running Sony CE Linux `4.9.337-scel+` alongside a TOPPERS-FMP 1.4.0 SMP RTOS co-processor (`cpapp-b.bin` `@ 0x00108000`).

> [!IMPORTANT]
> **Clean-Room Open-Source Boundary (BYOF — Bring Your Own Firmware)**
> This repository contains **0 bytes of proprietary Sony firmware binaries** (no `BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `cpapp-b.bin`, `nflasha*` dumps, or `.cpio` rootfs images). All self-authored Python verifiers, freestanding C/Assembly workers, Unicorn AArch64 harnesses, QEMU patches, Web UI frontends, and SHA-256 receipts operate in clean-room mode (automatically gated on `ubuntu-latest` + `macos-latest` via `.github/workflows/clean-room-ci.yml`). See **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** (guarded by `make verify-byof`) for exact SHA-256 digests when reproducing VM sessions with your own official firmware packages.

---

## 1. Engineering Milestones (As of Nov 14, 2026)

### Track 1A — Interactive FX6 128-Page Guest `GPE0` UI, Phase 19 Native Icons & `60/60` Multi-Click Stability
- **Phase 19 Authentic FX6 Sprite/Icon Rendering & `60/60` Freeze Fix**: Integrated read-only `image_00_169.uxc` CPIO injection, LDEC-legal `/dev/mem` GPE physical pool (`0x410524000..0x410e64000`), and `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` blitting onto `GPE0`, and eliminated the `liblibra.so` `GenerateImageCommand::notify(bool)` (`0x2a238`) async worker race via PLT interposition, 32-slot aligned widget ring pools, and serialized GDB `$c#63` resume (`60/60` rapid clicks `0 SEGV`, up to `icon_n=119`, avg `179.3 ms`, [Phase 19 Report](reports/2026-11-14-phase19-live-icon-rendering/README.md)).
- **100% 128-Page In-Guest Rendering, 22.1x C Scanline Packer & 20 Offline Unit Tests**: Rendered all **128** native FX6 Ver. 6.01 (`ILME-FX6V`) page descriptor tables (`2,249` widget rows) into physical `GPE0` (`0x41e001000`, `1024×540` RGBA32, `segv = 0`), backed by `fx6_pack_scanlines` (**22.1x** faster), [`build_live700.py`](outputs/fx3-vm-trial/build_live700.py), and **20** dual-mode automated unit tests ([`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)).

### Track 1B — FX6 Native Cold-Boot + Round 8 & Round 9 FX6-on-FX3 Hybrid QEMU Closure (`r1a..r9d`, 26 PNG Receipts, 20 Unit Tests)
- **Zero-Instruction-NOP Full Cold-Boot & Interactive Presenter Stack (`r1a..r7c`)**: Delivered [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) and [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md), booting unmodified FX6 userland under **`FX6_NATIVE_FAITHFUL=1`** (`nop_count = 0`, `subst_* = 0`) across 161 live threads.
- **Round 8 (Stage-A) & Round 9 (Stage-B `P10` Keymap) FX6-on-FX3 Hybrid Real-Kernel Closure (`r8a..r9d`)**: Boots **FX3 7.02 stock `vmlinux.bin`** (`4.9.337-scel+`) + FX3 `cxd90057.dtb` at **`nop_count = 0`** ([Round 8 Report](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md) & [Round 9 Report](reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md)), verifying `11/11` Stage-B SHA-256 digests (`P10` live readback `ok=1`) and driving FX3 `Fn`/`C1`/`C2`/`MENU`/`ENTER` keys (`SRM3KYE5`) through `InfraInput` into `r9a` Shooting HUD (`sid=0x02`), `r9b` Big6 Home (`sid=0x0a`), `r9c` Big6 Setting Sub-Dialog (`sid=0x0c`, `2,035` amber `0xffffaa00` px), and `r9d` Full Menu 2nd Layer (`sid=0x10`, `434,010` px, `87` colors).

### Track 2 — FX3 Native Firmware QEMU Virtual Machine & Interactive Web Menu Emulator
- **Unmodified FX3 7.02 Kernel & Camera Menu (`outputs/fx3-vm/`, `outputs/fx3-vm-trial/`)**: Models CXD90057 High DDR (`0x400000000`), ESRAM mailbox (`0xfe005000`), GICD, Sony timers, SCU, GPIO Bank5, UIPC, DMM, GPE v13/v14, and software LDEC LZ77 decompression, exposing a live browser-controlled FX3 camera menu (`FX3菜单.command`, 4096-key / 60-minute budget, ~40.1s start-to-first-OSD-frame, verified across 32-key live navigation and API16 clean restoration).

### Track 3 — FX6-on-FX3 Phase 21 Full-Stack Closure (`P1..P11 + Fan`, `U1..U5`, Stage-B `P10`, `P11` UIPC-CP Shim, 5-Axis IBIS & 12-Gate Suite)
- **Controlled Source Packages**: [`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md), [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md) & [`outputs/fx3-safety/`](outputs/fx3-safety/) ([Phase 1–16 Report](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md), [Phase 17 Report](reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md), [Phase 18 Report](reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md), [Phase 20 Report](reports/2026-11-14-phase20-p10-stage-b-integration/README.md), [Phase 21 Report](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)):
  - **Full Compatibility Matrix (`P1..P11 + Fan`) & Phase 20 Combined Stage-B `appFw.so` (`make verify-stage-b-p10`)**: Deterministic ELF64 `PT_LOAD` / `ET_REL` adaptation with **100% bit-exact SHA-256 rollback**, combining `P1+P4+P8+P10` (`10` sites / `41 B` zero overlap, Stage-B SHA-256 `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`, 21-key Unicorn proof) alongside touch, LCD/HDMI OSD routing & `XLR-H1` audio closure (`make verify-peripheral-ux`).
  - **Phase 18 & Phase 21 `P11` AP↔Stock-CP UIPC Shim, 3D LUT / Cine EI / Dual Native ISO & 5-Axis IBIS Center-Lock (`make verify-ap-cp-imaging` & `make verify-uipc-cp-shim`)**: Proves **all 44 UIPC BB opcodes on `0x92840747`** exist in FX3 7.02 Stock-CP and Unicorn-verifies `P11` AP synthesis on `0x92d2091c` (`/dev/rtc0->udate` unblocking `std::promise`) & `0x91db059b` (Smart Handle ACK preserving `XLR-H1`), `developing_mode_FHD -> 0x92840747`, `0x0165`/`0x0166` `33^3` 3D LUT DMA (`800`/`12800` Dual Base ISO), E-mount AF (`0 B` diff), and **FX3 5-axis IBIS actuator energized center-lock**.
  - **Zero-Repartition Budgets, `p5:/wbi` & `p8:/cp` Redlines, `U1..U5` Closure, Stage-A Readiness Packet, `H0 -> H1 -> H2` Zero-Mutation Auditor & 12 Safety Gates**: Hard-locks `edisx_repartition_forbidden = True`, `p8_cp_mutation_forbidden = True`, `wbi_p5_write_and_hibernation_forbidden = True`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False`.

### Track 4 — FX3 Offline Recovery Adapter (`v0.5`), Global Unbrick Intel & USB Service Protocol Tooling
- **Zero-Dependency `p1` Suite & Global Intel Dossier (`outputs/fx3-recovery-adapter/`, [Global Intel Report](reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md))**: Provides `inspect`, `build`, `verify`, `diagnose`, `rollback`, and standalone zero-libc AArch64 ELF capture workers for `/dev/cnflasha1` (`p1` updater) and `/dev/nflashaB0`/`B1` (`boot0`/`boot1`), aligned with 2025–2026 Sony BIONZ XR RE (`ALCIN_UUD`, Multi-port `48000`-baud BootROM `uart_boot -> 0x92028000` Tier-3 unbricking, and WF-12 wireless fault isolation) and backed by **63** tests.

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
├── .github/workflows/clean-room-ci.yml     # Donorless Ubuntu + macOS 5-suite Clean-Room CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                # Unified test (`make test`), BYOF, dry-run, Phase 17..21, `make readiness-packet` & `make lifecycle-drill`
├── README.md                               # Bilingual (EN + ZH-CN) comprehensive master documentation (Nov 14, 2026)
├── README.en.md                            # Standalone English documentation (Nov 14, 2026)
├── README.zh-CN.md                         # Standalone Simplified Chinese documentation (Nov 14, 2026)
├── docs/
│   ├── BYOF-REPRODUCTION.md                # Clean-room bilingual 57+57 entry SHA-256 firmware manifest & reproduction guide
│   └── STAGE-A-HARDWARE-RUNBOOK.md         # Bilingual Phase H0->H1->H2 non-persistent Stage-A hardware operator runbook
├── scripts/
│   ├── run_all_lab_tests.py                # Unified 5-suite 271-test runner + BYOF manifest audit + `git status --porcelain` hygiene auditor
│   └── verify_byof_manifest.py             # Bilingual BYOF SHA-256 schema, 46 code-constant & live-donor manifest auditor
├── outputs/
│   ├── fx6-on-fx3-closure/                 # Phase 21 P1..P11+Fan, U1..U5, Stage-A/B, .ko/ABI, peripheral UX, imaging/UIPC-CP/IBIS, readiness & post-trial auditor (149 tests)
│   ├── fx6-native-presenter-closure/       # Cold-boot `nop_count=0` + Round 8 (Stage-A) & Round 9 (Stage-B `P10`) Hybrid QEMU GPE0 closure (20 tests)
│   ├── fx3-safety/                         # 12-Gate pre-flash safety evaluator, Sector-0/BK4 contracts & brick classifier (19 tests)
│   ├── fx3-recovery-adapter/               # FX3 Offline Recovery Adapter v0.5 & AArch64 static capture workers (63 tests)
│   ├── fx3-vm-trial/                       # Interactive FX3 & FX6 (Phase 19 native icons `image_00_169.uxc`, `60/60` multi-click stability) Web UI (20 tests)
│   └── fx3-vm/                             # Minimal FX3 QEMU AArch64 research VM & High-DDR / ESRAM patches
├── reports/
│   ├── 2026-11-14-phase19-live-icon-rendering/         # Phase 19 live FX6 native icon blitting + 60/60 multi-click freeze fix report
│   ├── 2026-11-14-phase20-p10-stage-b-integration/     # Phase 20 Stage-B combined `appFw.so` (`P1+P4+P8+P10`) & 21-key Unicorn report
│   ├── 2026-11-14-phase21-uipc-cp-shim-closure/        # Phase 21 `P11` UIPC-CP shim (`0x92d2091c`/`0x91db059b`), LUT DMA & IBIS report
│   ├── 2026-11-14-round9-fx6-on-fx3-p10-presenter/     # Round 9 FX6-on-FX3 Stage-B `P10` multi-scene QEMU Presenter (`r9a..r9d`) report
│   ├── 2026-11-14-global-sony-firmware-vm-unbrick-intel/ # 2025-2026 global Sony firmware RE, QEMU/IVSHMEM & Multi-port BootROM unbrick dossier
│   ├── 2026-11-14-fx6-on-fx3-qemu-hybrid/  # Round 8 FX6-on-FX3 Stage-A Hybrid QEMU E2E boot (`r8a..r8b`) evidence report
│   ├── 2026-11-14-phase17-fx3-input-display-audio-audit/ # Phase 17 FX3 controls (`P10`), touch, LCD/HDMI & `XLR-H1` audio report
│   ├── 2026-11-14-phase18-ap-cp-imaging-ibis-audit/      # Phase 18 AP<->Stock-CP imaging, 3D LUT, XAVC, AF & 5-axis IBIS report
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/    # Master Phase 1–16 compatibility, U1..U5, initrd/WBI, .ko/ABI, readiness & 12-Gate report
│   ├── 2026-11-10-fx6-native-presenter-closure/# Cold-boot `nop_count=0` GPE0 Rounds 1–7 (`r1a..r7c`, 20 PNG receipts) evidence report
│   ├── 2026-11-08-fx6-native-text-gpe0/    # 100% 128-page FX6 descriptor rendering evidence on physical GPE0
│   └── 2026-11-03-fx6-full-system-to-fx3/  # FX6 6.01 vs FX3 7.02 full 30-partition & SPI NOR static audit
└── conversations/                          # Categorized multi-agent engineering session archives
```

---

## 4. Quick Start & Verification

### 4.1 Run All 271 Automated Tests, Donorless Clean-Room CI, BYOF Audit, Phase 17..21, Readiness Packet & Lifecycle Drill

```bash
# Run all 5 suites (63 fx3-recovery-adapter + 19 fx3-safety + 149 fx6-on-fx3-closure + 20 fx3-vm-trial + 20 fx6-native-presenter-closure = 271 tests) + BYOF & hygiene check
make test

# Simulate donorless Clean-Room CI locally (zero Sony firmware blobs required — identical to GitHub Actions)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-peripheral-ux && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-ap-cp-imaging && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-stage-b-p10 && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-uipc-cp-shim && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# Verify bilingual docs/BYOF-REPRODUCTION.md SHA-256 manifest (57 EN + 57 ZH entries + 46 code constants + optional live donors)
make verify-byof

# Run full offline FX6-on-FX3 candidate dry-run, Stage-A Readiness Packet & End-to-End H0->H1->H2 Lifecycle Drill
make dry-run
make readiness-packet
make lifecycle-drill

# Run standalone Phase 11 p1 Bridge, Phase 12 Stage-A Orchestrator, Phase 14 Kmod/ABI & Phase 17..21 verifiers
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
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
