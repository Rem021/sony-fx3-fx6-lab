# `fx6-on-fx3-closure` — Phase 4 Compatibility Closure, Stage-A RAM-Overlay CPIO & 4-Layer Fail-Safe Rollback Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation (`P1..P9` 9/9 full matrix + `Fan`), `VFAT` loopback image generation, UIPC completion synthesis, dual-kernel Backup Sync100 signature & trampoline verification, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, **Stage-A zero-flash-write `cpio newc` RAM-Overlay packaging**, **4-Layer Fail-Safe automatic rollback sandbox drills**, and 12-Gate pre-flash safety evaluation.

## Cleanroom & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, `.vfat` images, and Stage-A `.cpio` archives are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit.
- **100% deterministic SHA-256 rollback & reproducibility**: Every binary adaptation specification (`ET_DYN` shared libraries, `ET_REL` `.ko` kernel modules, and in-memory 16-byte kernel entry hooks) enforces segment/section bounds, context byte verification, and bit-exact SHA-256 restoration; the pure-Python `cpio newc` (`070701`) builder uses fixed `mtime` and sequential inode numbers for 100% reproducible archive SHA-256 digests without external `cpio` tools.
- **Sandboxed zero-host-side-effect rollback drills**: All POSIX `/bin/sh` fail-safe drills inject an isolated `TemporaryDirectory` via `PREFIX`, enforce a host-OS guard + sandbox `busybox` path lock (never touching host `/dev` or `/tmp`), and verify **0 writes** across simulated eMMC partitions (`sector0`, `p2`, `p6`, `p15`, `p18`).
- **Zero hardware or VM side effects**: Strictly offline static, memory, POSIX sandbox, and Unicorn AArch64 emulation; `persistent_write_release` remains unconditionally `False`.

## Module Structure

- `fx6_closure/elf_verify.py` — ELF64 `PT_LOAD` (`ET_DYN`/`ET_EXEC`) and `ET_REL` section-header file-offset mapper.
- `fx6_closure/patcher.py` — Compatibility adaptation & rollback specs for P1 (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so`), P3 (`libInfraAppRemoteBoard.so`), P4 (`appFw.so` ND Clear lock), P8 (`appFw.so` `0x2159c50` non-blocking async log wait), P9 (`upm.ko` `.text+0x136b8` null-callback guard), and Fan (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv`).
- `fx6_closure/vfat_builder.py` — Deterministic pure-Python `FAT16` / `FAT32` image builder (`8m_ram`, `16m_log`, `44.5m_log`, `44.5m_fat32`) and BPB / dual-FAT / `/OPE/{00,01}` auditor (P2).
- `fx6_closure/nd_unicorn_verifier.py` — Unicorn AArch64 instruction-level verifiers for P3, P4 (576-combination sweep), P8, P9, and Fan.
- `fx6_closure/uipc_completion_verifier.py` — P5 (`0x032d -> 0x132d`) & P6 (`0x0400 -> 0x1400`, `0x0402 -> 0x1402`, `0x0404 -> 0x1404`, `0x0152 -> 0x1152`) byte-exact UIPC completion synthesizer on queue `0x92840747` and Unicorn AArch64 verifier for `appFw.so` `send_and_wait_cmp_i` (`0x20ef604`..`0x20ef7ec`) + `0x20edd1c` status mapper.
- `fx6_closure/backup_bridge_verifier.py` — P7 kernel-space Backup Sync100 address-agnostic bridge verifier: dual-kernel `pcidma_transfer_async` 16-byte prologue (`b4000b00, a9bb7bfd, 910003fd, a90153f3`), `fallback_zero = api + 0x160` / `fallback_nonzero = api + 0x10` Unicorn trampoline on FX3 (`0xffffff80083220c8`) and FX6 (`0xffffff8008322f70`), 40-byte `dst = 0x903e0811` / `op = 0x30` schema, and synchronous `backupfile_cb_getcp` DMA callback contract.
- `fx6_closure/ram_overlay_packager.py` — Pure-Python deterministic SVR4 `cpio newc` (`070701` magic, 4-byte alignment, `TRAILER!!!` sentinel) builder & parser/auditor assembling `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}` (verified against `fx3_safety.preflight.verify_failsafe_hook_script`).
- `fx6_closure/rollback_drill.py` — Deterministic 4-Layer Fail-Safe state machine and `PREFIX`-isolated POSIX `/bin/sh` subprocess drill runner covering all 4 mandatory scenarios (unarmed stock boot, armed single-boot + reboot revert, SHA-256 mismatch / missing file fallback, and watchdog timeout / non-zero exit fallback with 0 eMMC writes).
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler (`P1..P9` 9/9 + `Fan` + `Stage-A CPIO` + `Rollback Drill` + `Tier-0`) and `fx3_safety` 12-Gate evaluator integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `run-rollback-drill`, `dry-run-candidate`).

## CLI & Unit Test Commands

```sh
# 1. Verify all 7 binary targets (P1, P3, P4, P8, P9, Fan), 100% SHA-256 rollback & P7 dual-kernel signatures
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-donors

# 2. Run Unicorn AArch64 instruction-level (P3, P4, P5, P6, P7, P8, P9, Fan) & Tier-0 syscall audit
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-unicorn-audit

# 3. Build Stage-A RAM-Overlay CPIO newc package & execute all 4 sandboxed fail-safe rollback scenarios
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-rollback-drill

# 4. Assemble full P1..P9 + Fan + Stage-A CPIO offline candidate in TemporaryDirectory & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 5. Run full unit test suites (24/24 + 10/10)
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v
PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```
