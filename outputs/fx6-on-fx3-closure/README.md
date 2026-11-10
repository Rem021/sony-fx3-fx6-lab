# `fx6-on-fx3-closure` — Phase 7 Compatibility Closure, `U5` Boot-Selector Contract, `U3` Bank DDR Verifier, `U4`/RAM-Shadow `BK4\0` & CPIO Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation (`P1..P9` 9/9 full matrix + `Fan`), `VFAT` loopback image generation, UIPC completion synthesis, dual-kernel Backup Sync100 signature & trampoline verification, **Blueprint §3 5-Core-Camera-Feature Routing & Cross-Model ELF Dynamic Symbol Closure verification**, **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Only Shadow `BK4\0` Backup Schema Synthesis**, **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Non-Overlap Verifier (`U3` Advancement)**, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, RAM-Overlay `cpio newc` packaging, 4-Layer Fail-Safe automatic rollback sandbox drills, and 12-Gate pre-flash safety evaluation.

## Cleanroom & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, `.vfat` images, `.cube` 3D LUT test tables, RAM-shadow `BK4\0` containers, and `.cpio` archives are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit (`flash_write_allowed = False`; physical `p2:/setting/Backup.bin`, `p2:/setting/updater/mode*`, and `p1:/updater` are never modified).
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
- `fx6_closure/boot_selector_and_bank_verifier.py` — **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Verifier (`U3` Advancement)**:
  - **Dimension A (`U5` Closure)**: Audits `up.sh`, `common.src`, all three donor `ud_send_lsi.elf` binaries (`PT_LOAD` `0x0000..0x2070` 100% byte-identical across FX6 `p15`, FX6 `p1` initrd, and FX3 `2.05`), `loader_nor.bin` (`0xFE049000`), and `LdrBkupList.txt` (65 keys). Micro-executes `ud_send_lsi.elf` `main` (`0x400990..0x400ad8`) in Unicorn AArch64 across all 7 `up.sh` modes (`0 -> 00000000`, `2 -> 02000000`, `3 -> 03000000`, `4 -> 04000000`, `5 -> 05000000`, `6 -> 06000000`, `7 -> 07000000` on destination queue `0x804b0376`, source reply queue `0x004b0379`, `3000 ms` timeout, `-0x3fe` `OSAL_E_TMO` tolerance, and Backup key `0x004b0000` `LSI_MAIN=1` / `LSI_SUB=2` gate). Pins `loader_nor.bin`'s dual-condition arbitrator (`0xFE054AF8` Sub-LSI ANK latch + `0xFE053CF8` `p2:\updater\mode` -> sticky MMIO `0xFE170028` + `0xFE04D584` strict `BK4\0` `byte8 == 1`), proving zero sticky-updater risk for the RAM-only `p7` overlay and enforcing the mandatory two-step `p1` recovery exit reset (`rm -f /setting/updater/mode* && sync` + explicit `ud_send_lsi.elf 0` bypassing `up.sh`'s `/root/IAMUPDATER` early exit).
  - **Dimension B (`U3` Advancement)**: Parses all `64` descriptor slots (`64 x 144 = 9,216 B`, matching `loader_nor.bin` `0xFE054638..0xFE054688`) across FX3 (`bank0-fa0080.bin` 9 slots, `bank1-fa0080.bin` 11 slots) and FX6 (`CX95898_NTSC.bin` Bank 0 5 slots, Bank 1 10 slots), proving **0-byte pairwise DDR interval overlap** in every bank (including conservative `32 MiB` `[0x0800108000, 0x0802108000)` reserve for Bank 1 `\cpapp-b.bin` dynamic-size sentinel `mode = 0x81000000`), **0-byte AP shift** in Bank 0, and exact **`+0xE0000`** (`\psd.bin`, `\lensfile.bin`, `\OldAmtCL.bin`) and **`+0x14000`** (`\defdet.bin`, `\DmmCfg.bin`) Bank 1 calibration shifts while rejecting any DDR overlap, out-of-bounds partition, inverted range, or non-zero Bank 0 byte-8 selector.
- `fx6_closure/ram_overlay_packager.py` — Pure-Python deterministic SVR4 `cpio newc` (`070701` magic, 4-byte alignment, `TRAILER!!!` sentinel) builder & parser/auditor assembling `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`.
- `fx6_closure/rollback_drill.py` — Deterministic 4-Layer Fail-Safe state machine and `PREFIX`-isolated POSIX `/bin/sh` subprocess drill runner covering all 4 mandatory scenarios.
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler (`P1..P9` 9/9 + `Fan` + `5-Feature Routing` + `U4/RAM-Shadow BK4` + `U5/U3 Boot-Selector & Bank DDR` + `CPIO` + `Rollback Drill` + `Tier-0`) and `fx3_safety` 12-Gate evaluator (`Gate G12` `backup_mount_tolerance_ok` & `boot_selector_and_banks_ok`) integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `run-rollback-drill`, `verify-feature-routing`, `verify-backup-mount-contracts`, `verify-boot-selector-banks`, `dry-run-candidate`).

## CLI & Unit Test Commands

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

# 7. Assemble full P1..P9 + Fan + 5-Feature Routing + U4/BK4 + U5/U3 + CPIO candidate & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 8. Run full unit test suites (36/36 + 12/12)
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v
PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```
