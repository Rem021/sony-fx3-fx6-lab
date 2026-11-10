# `fx6-on-fx3-closure` — Offline Compatibility Adaptation, VFAT, Tier-0 Backup & 12-Gate Dry-Run Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation, `VFAT` loopback image generation, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, and 12-Gate pre-flash safety evaluation.

## Cleanroom & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, and `.vfat` images are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit.
- **100% deterministic SHA-256 rollback**: Every binary adaptation specification (`ET_DYN` shared libraries and `ET_REL` `.ko` kernel modules) enforces ELF64 segment/section bounds, context byte verification, and bit-exact SHA-256 restoration.
- **Zero hardware or VM side effects**: Strictly offline static, memory, and Unicorn AArch64 emulation; `persistent_write_release` remains unconditionally `False`.

## Module Structure

- `fx6_closure/elf_verify.py` — ELF64 `PT_LOAD` (`ET_DYN`/`ET_EXEC`) and `ET_REL` section-header file-offset mapper.
- `fx6_closure/patcher.py` — Compatibility adaptation & rollback specs for P1 (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so`), P3 (`libInfraAppRemoteBoard.so`), P4 (`appFw.so` ND Clear lock), P8 (`appFw.so` `0x2159c50` non-blocking async log wait), P9 (`upm.ko` `.text+0x136b8` null-callback guard), and Fan (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv`).
- `fx6_closure/vfat_builder.py` — Deterministic pure-Python `FAT16` / `FAT32` image builder (`8m_ram`, `16m_log`, `44.5m_log`, `44.5m_fat32`) and BPB / dual-FAT / `/OPE/{00,01}` auditor.
- `fx6_closure/nd_unicorn_verifier.py` — Unicorn AArch64 instruction-level verifiers for P3, P4 (576-combination sweep), P8, P9, and Fan.
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler and `fx3_safety` 12-Gate evaluator integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `dry-run-candidate`).

## CLI & Unit Test Commands

```sh
# 1. Verify all 7 binary targets (P1, P3, P4, P8, P9, Fan) & 100% SHA-256 rollback
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-donors

# 2. Run Unicorn AArch64 instruction-level & Tier-0 syscall audit
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-unicorn-audit

# 3. Assemble offline candidate in TemporaryDirectory & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 4. Run full unit test suites
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v
PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```
