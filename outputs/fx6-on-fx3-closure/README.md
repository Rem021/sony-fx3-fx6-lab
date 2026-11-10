# `fx6-on-fx3-closure` — Phase 9 Compatibility Closure, 30-Partition Zero-Repartition Storage/`p15` Footprint & Linux DDR/`tmpfs` RAM-Overlay Budget Verifier, `cxd90057.dtb` FDT & `.ko` Integrity Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation (`P1..P9` 9/9 full matrix + `Fan`), `VFAT` loopback image generation, UIPC completion synthesis, dual-kernel Backup Sync100 signature & trampoline verification, **Blueprint §3 5-Core-Camera-Feature Routing & Cross-Model ELF Dynamic Symbol Closure verification**, **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Only Shadow `BK4\0` Backup Schema Synthesis**, **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Non-Overlap Verifier (`U3` Advancement)**, **Phase 8 Flattened Device Tree (`cxd90057.dtb` `0xd00dfeed`) SoC MMIO/Carveout Compatibility Auditor & Kernel Module `.modinfo` (`vermagic`) / `__versions` (`modversion_info`) CRC Integrity Verifier**, **Phase 9 30-Partition Zero-Repartition Storage/`p15` (`/usr`) Footprint & CXD90057 Linux DDR / Stage-A `tmpfs` RAM-Overlay Budget Verifier**, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, RAM-Overlay `cpio newc` packaging, 4-Layer Fail-Safe automatic rollback sandbox drills, and 12-Gate pre-flash safety evaluation.

## Cleanroom & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, `.vfat` images, `.cube` 3D LUT test tables, RAM-shadow `BK4\0` containers, synthetic `__versions`-instrumented `.ko` test images, and `.cpio` archives are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit (`flash_write_allowed = False`; `edisx_repartition_forbidden = True`; `sector0_mutation_bytes = 0`; physical `p2:/setting/Backup.bin`, `p2:/setting/updater/mode*`, and `p1:/updater` are never modified).
- **100% deterministic SHA-256 rollback & reproducibility**: Every binary adaptation specification (`ET_DYN` shared libraries, `ET_REL` `.ko` kernel modules, and in-memory 16-byte kernel entry hooks) enforces segment/section bounds, context byte verification, and bit-exact SHA-256 restoration; both the pure-Python `cpio newc` (`070701`) builder and the RAM-shadow `BK4\0` synthesizer produce 100% reproducible SHA-256 digests.
- **Sandboxed zero-host-side-effect rollback drills**: All POSIX `/bin/sh` fail-safe drills inject an isolated `TemporaryDirectory` via `PREFIX`, enforce a host-OS guard + sandbox `busybox` path lock (never touching host `/dev` or `/tmp`), and verify **0 writes** across simulated eMMC partitions (`sector0`, `p2`, `p6`, `p15`, `p18`).
- **Zero hardware or VM side effects**: Strictly offline static, memory, POSIX sandbox, and Unicorn AArch64 emulation; `persistent_write_release` remains unconditionally `False`.

## Module Structure

- `fx6_closure/elf_verify.py` — ELF64 `PT_LOAD` (`ET_DYN`/`ET_EXEC`) and `ET_REL` section-header file-offset mapper.
- `fx6_closure/patcher.py` — Compatibility adaptation & rollback specs for P1 (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so`), P3 (`libInfraAppRemoteBoard.so`), P4 (`appFw.so` ND Clear lock), P8 (`appFw.so` `0x2159c50` non-blocking async log wait), P9 (`upm.ko` `.text+0x136b8` null-callback guard), and Fan (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv`).
- `fx6_closure/vfat_builder.py` — Deterministic pure-Python `FAT16` / `FAT32` image builder (`8m_ram`, `16m_log`, `44.5m_log`, `44.5m_fat32`) and BPB / dual-FAT / `/OPE/{00,01}` auditor (P2).
- `fx6_closure/nd_unicorn_verifier.py` — Unicorn AArch64 instruction-level verifiers for P3, P4 (576-combination sweep), P8, P9, and Fan.
- `fx6_closure/uipc_completion_verifier.py` — P5 (`0x032d -> 0x132d`) & P6 (`0x0400 -> 0x1400`, `0x0402 -> 0x1402`, `0x0404 -> 0x1404`, `0x0152 -> 0x1152`) byte-exact UIPC completion synthesizer on queue `0x92840747` and Unicorn AArch64 verifier for `appFw.so` `send_and_wait_cmp_i` (`0x20ef604`..`0x20ef7ec`) + `0x20edd1c` status mapper.
- `fx6_closure/backup_bridge_verifier.py` — P7 kernel-space Backup Sync100 address-agnostic bridge verifier: dual-kernel `pcidma_transfer_async` 16-byte prologue (`b4000b00, a9bb7bfd, 910003fd, a90153f3`), `fallback_zero = api + 0x160` / `fallback_nonzero = api + 0x10` Unicorn trampoline on FX3 (`0xffffff80083220c8`) and FX6 (`0xffffff8008322f70`), 40-byte `dst = 0x903e0811` / `op = 0x30` schema, and synchronous `backupfile_cb_getcp` DMA callback contract.
- `fx6_closure/feature_routing_verifier.py` — **Phase 5 Blueprint §3 5-Core-Feature Routing & Cross-Model ELF Dynamic Symbol Closure Verifier** (43-node `DT_NEEDED` transitive closure, 16x `33^3` `.cube` `p30` budget, and Cine EI / AF / `libmpr.so` Dual-Slot Unicorn contracts).
- `fx6_closure/backup_mount_tolerance_verifier.py` — **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Shadow `BK4\0` Synthesizer** (Unicorn verification of `SetupFile::RcvThread` @ `0x19650` & `KikiLogGenerator_res_ope` @ `0x3cb0` + `20,588 B` RAM-Shadow `BK4\0` synthesis).
- `fx6_closure/boot_selector_and_bank_verifier.py` — **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Verifier (`U3` Advancement)** (`up.sh` + `ud_send_lsi.elf` 10-case Unicorn + `loader_nor.bin` arbitrator + 64-slot `0xfa0080` Bank 0/1 pairwise non-overlap & `+0xE0000` / `+0x14000` calibration shifts).
- `fx6_closure/kernel_dtb_compatibility_verifier.py` — **Phase 8 Flattened Device Tree (`cxd90057.dtb`) SoC Compatibility Auditor & Kernel Module `vermagic` / `__versions` CRC Integrity Verifier** (68-node / 493-property `0xd00dfeed` FDT identity + 7 `kemco.txt` `memrsv=` carveouts + `.ko` `vermagic` & `modversion_info` CRC integrity).
- `fx6_closure/storage_and_ram_budget_verifier.py` — **Phase 9 30-Partition Zero-Repartition Topology, `edisx.elf` Redline, `p15` (`/usr`) Footprint & CXD90057 Linux DDR / Stage-A `tmpfs` RAM-Overlay Budget Verifier**:
  - **Dimension A (30-Partition Zero-Repartition Topology, `edisx.elf` Redline & `p15` Footprint Budget)**: Cross-verifies FX3 (`0x0035E000` sectors = `1,724.00 MiB`) vs FX6 (`0x00384400` sectors = `1,800.50 MiB`, `+76.50 MiB` UDA delta) 30-partition `partinf.conf` & Sector-0 layouts (`fx3_safety.boot_contracts`) plus 6 SPI NOR regions in `pformat_config.txt`, proving **every FX6 runtime partition maps onto FX3's stock Sector-0 without repartitioning** (`edisx_repartition_forbidden = True`, `sector0_mutation_bytes = 0`, `spi_nor_mutation_bytes = 0`: `p20 -> p30` `48.00 MiB` via P1; `p21 -> /tmp/opelog.vfat` `8/16 MiB` loopback via P2; `p12` & `p18` Tier-0 preserved intact). Audits `nflasha15-manifest.json` + `nflasha15-files` (`753` files, `81` symlinks, `34` directories, `378,791,274 B` = `361.24 MiB` raw) and `nflasha15` ext2 superblock (`425.19 MiB`) against FX3 stock `p15` (`500.00 MiB` = `524,288,000 B`), proving **`+138.76 MiB` raw / `+137.21 MiB` SquashFS / `+125.62 MiB` ext4 / `+74.81 MiB` donor-image positive headroom**.
  - **Dimension B (CXD90057 Linux Usable DDR Pool & Stage-A `tmpfs` RAM-Overlay Budget)**: Computes DTB `/memory@400000000` (`8,192.00 MiB`), `kemco.txt` `mem=2G` (`2,048.00 MiB`), 7 `memrsv=` carveouts (`130.38 MiB`), and **net Linux-managed DDR (`2,010,771,456 B` = `1,917.62 MiB`)**, then models 4 KiB-paged Stage-A `tmpfs` (`/tmp`) footprints across all 11 components (`appFw.so`, `libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `libInfraKikiLogGenerator.so`, `libInfraAppRemoteBoard.so`, `libfan.so`, `upm.ko`, `opelog.vfat` `8/16 MiB`, `20,588 B` RAM-shadow `BK4\0`, `19,696 B` control CPIO), proving both streaming-unpack (`57.45 MiB` / `65.45 MiB` peak) and peak-buffer (`114.73 MiB` / `130.73 MiB` peak) modes stay strictly inside the conservative `256.00 MiB` `tmpfs` ceiling (`3.00%`–`6.82%` of Linux `MemTotal`) while rejecting over-budget payloads and `edisx.elf` Sector-0 rewrite attempts.
- `fx6_closure/ram_overlay_packager.py` — Pure-Python deterministic SVR4 `cpio newc` (`070701` magic, 4-byte alignment, `TRAILER!!!` sentinel) builder & parser/auditor assembling `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`.
- `fx6_closure/rollback_drill.py` — Deterministic 4-Layer Fail-Safe state machine and `PREFIX`-isolated POSIX `/bin/sh` subprocess drill runner covering all 4 mandatory scenarios.
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler (`P1..P9` 9/9 + `Fan` + `5-Feature Routing` + `U4/RAM-Shadow BK4` + `U5/U3 Boot-Selector & Bank DDR` + `Phase 8 DTB/.ko Integrity` + `Phase 9 Storage/RAM Budget` + `CPIO` + `Rollback Drill` + `Tier-0`) and `fx3_safety` 12-Gate evaluator (`Gate G12` `backup_mount_tolerance_ok`, `boot_selector_and_banks_ok`, `kernel_dtb_ok`, and `storage_and_ram_budget_ok`) integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `run-rollback-drill`, `verify-feature-routing`, `verify-backup-mount-contracts`, `verify-boot-selector-banks`, `verify-kernel-dtb`, `verify-storage-ram-budget`, `dry-run-candidate`).

## CLI & Unified Verification Commands

```sh
# 1. Verify all 7 binary targets (P1, P3, P4, P8, P9, Fan), 100% SHA-256 rollback & P7 dual-kernel signatures
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-donors

# 2. Run Unicorn AArch64 instruction-level (P3, P4, P5, P6, P7, P8, P9, Fan) & Tier-0 syscall audit
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-unicorn-audit

# 3. Build RAM-Overlay CPIO newc package & execute all 4 sandboxed fail-safe rollback scenarios
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-rollback-drill

# 4. Verify Blueprint §3 5-core-feature routing, 43-node ELF64 symbol closure, 16x .cube p30 budget & dual-slot Unicorn contracts
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-feature-routing

# 5. Verify Phase 6 U4 storage mount-failure tolerance in Unicorn & synthesize/audit RAM-shadow BK4\0 contracts
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-backup-mount-contracts

# 6. Verify Phase 7 U5 boot-selector contract (ud_send_lsi.elf Unicorn + loader_nor.bin) & U3 Bank 0/1 DDR non-overlap maps
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-boot-selector-banks

# 7. Verify Phase 8 cxd90057.dtb FDT (0xd00dfeed) SoC MMIO/carveouts & .ko vermagic/__versions CRC integrity
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-kernel-dtb

# 8. Verify Phase 9 30-partition zero-repartition topology, edisx.elf redline, p15 (/usr) footprint & CXD90057 DDR/tmpfs budget
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-storage-ram-budget

# 9. Assemble full P1..P9 + Fan + 5-Feature Routing + U4/BK4 + U5/U3 + DTB/.ko + Storage/RAM Budget + CPIO candidate & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 10. Run Unified Lab Verification Runner across all 3 suites (58 + 14 + 44 = 116 tests) + clean-room binary/pyc audit
/usr/bin/python3 -B scripts/run_all_lab_tests.py
make test
```
