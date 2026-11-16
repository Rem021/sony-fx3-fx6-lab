# Phase 25 Report: Version-Independent `nflasha1` (`p1`) 4-Site AArch64 Autolocator & 2026 Global Runtime Anti-Brick Guard

> **Engineer**: Hydrogen-16 (Recovery-Engine & Anti-Brick Safety)  
> **Branch**: `codex/h16-phase25-v702-p1-autolocator-brickv2`  
> **Safety Policy**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked) · Donor inputs `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` · Zero binaries/bytecode committed.

---

## 1. Executive Summary

This phase closes the two highest-priority Row 1 & Row 2 engineering gaps identified in [`reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md`](../2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md):

1. **Version-Independent `nflasha1` (`p1`) 4-Site AArch64 Autolocator** ([`p1_symbol_autolocator.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/p1_symbol_autolocator.py)):
   - Replaces brittle hardcoded offsets with a bounded **ELF64 `.dynsym` + `.rela.plt` + masked AArch64 prologue/pattern autolocator** across `libsdfileinputupdaterapi.so` and `libupdatercorecommon.so`.
   - Verified `O_RDONLY` against real **FX3 2.04 and 2.05** donor `nflasha1` images, reproducing exact baseline offsets (`0x9fd4`, `0xabf0`, `0xd208`, `0xd27c`) while preserving `isModelOK` and `isRegionOK` (`0xa004..0xa02c`).
   - Verified on **shifted-VMA `v7.02`-simulated ELF64 images** (`+0x140` / `+0x280` and arbitrary VMA biases), rejecting missing symbols, multi-match ambiguity, out-of-`.text` targets, PLT mismatches, and corrupted prologues fail-closed.
   - Executed **Unicorn AArch64** emulation across `ORIGINAL -> PATCHED -> ROLLED-BACK` states for all 4 sites plus preserved `isModelOK` checks, and verified **SquashFS `Z_SYNC_FLUSH` byte-length invariance** + **2-pass SHA-256 rollback** on both real donors and synthetic clean-room FAT12+SquashFS `p1` images.

2. **2026 Global Runtime Anti-Brick Guards & Brick Classifier v2** ([`runtime_antibrick_guards.py`](../../outputs/fx3-safety/fx3_safety/runtime_antibrick_guards.py) & [`brick_classifier.py`](../../outputs/fx3-safety/fx3_safety/brick_classifier.py)):
   - Implemented deterministic static + script + storage-budget + NVRAM-diff auditors blocking all four field-proven 2025–2026 Sony BIONZ XR brick vectors:
     1. `LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK`
     2. `BUSYBOX_DD_TRUNCATION_HAZARD` (+ `pmca-re-reloaded` 5-step atomic write & 5-slot rollback manifest)
     3. `NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009`
     4. `CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK`
   - Extended `classify_brick_state()` (100% backward-compatible with all 41 existing `fx3-safety` tests) to diagnose `13S` (`0x100D` Multi-port BootROM UART framing error), `6L+9S` (`WF-12` Wi-Fi/BT / CP NOR subcomponent fault per Sony `00342260`), `0x10000009` (`nflasha10` 12 MiB VFAT full-disk lockout), and `/etc/ld.so.preload` dynamic `/bin/busybox` init deadlock -> mapping each to exact non-destructive recovery playbooks including FX3 Multi-port `RP2040-Zero` `-DOPEN_DRAIN` Tier-3 rescue.

---

## 2. Deliverable 1: `p1` 4-Site AArch64 Autolocator Architecture

### 2.1 Located Sites & Masked AArch64 Templates

| Site ID | Library | `.dynsym` Symbol | Masked Template / `.rela.plt` Anchor | FX3 2.04/2.05 Verified Offset | Patch (`ORIGINAL` -> `PATCHED`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `isVersionOK` | `/usr/lib/libsdfileinputupdaterapi.so` | `_ZN7Updater21SDUUDConditionChecker11isVersionOKERN10UpdaterAPI22firmware_information_tE` | `ldr w2,[x1,#imm]`; `mov w0,#0`; `ldr w3,[x1,#imm]`; `cmp w3,w2`; tail `ret`; non-overlap with `isModelOK`/`isRegionOK` | `0x9fd4` | `mov w0, #1; ret` (`20008052c0035fd6`) |
| `VerifySignature` | `/usr/lib/libsdfileinputupdaterapi.so` | `_ZN7Updater21SignatureVerification15VerifySignatureENS_13verify_info_tEPKc` | `stp x29, x30, [sp, #imm]!` (`(w & 0xFFC07FFF) == 0xA9807BFD`) + `mov x29, sp` (`0x910003FD`) + `.rela.plt` `bl` cross-check | `0xabf0` | `mov w0, #0; ret` (`00008052c0035fd6`) |
| `chkFirmInfo_before_reject_ret` | `/usr/lib/libupdatercorecommon.so` | `_ZN7Updater8RVchk4PI18chkFirmInfo_beforeEPN10UpdaterAPI22firmware_information_t11informationE` | Unique match inside `chkFirmInfo_before`: `adrp x0`; `mov w19, #-1`; `add x0`; `bl remove@plt`; `adrp x0`; `add x0`; `bl remove@plt`; ...; `bl umount@plt` | `0xd208` | `13008012` -> `13008052` (`mov w19, #0`) |
| `chkFirmInfo_before_cmp_csinv` | `/usr/lib/libupdatercorecommon.so` | `_ZN7Updater8RVchk4PI18chkFirmInfo_beforeEPN10UpdaterAPI22firmware_information_t11informationE` | Unique match inside `chkFirmInfo_before`: `cmp wN, wM`; `csinv w19, wzr, wzr, gt` (`0x5A9FC3F3`); backward `b` inside function | `0xd27c` | `f3c39f5a` -> `13008052` (`mov w19, #0`) |

### 2.2 Unicorn AArch64 & SquashFS `Z_SYNC_FLUSH` Verification

- **Real FX3 2.04 & 2.05 Donors (`O_RDONLY`)**:
  - Autolocated offsets: `{'isVersionOK': 0x9fd4, 'VerifySignature': 0xabf0, 'chkFirmInfo_before_reject_ret': 0xd208, 'chkFirmInfo_before_cmp_csinv': 0xd27c}`.
  - Unicorn AArch64:
    - `isVersionOK`: downgrade (`0x0702 -> 0x0200`) returns `0` originally, `1` when patched, `0` after rollback; preserved `isModelOK` (`+0x0c` vs `+0x24`) returns `1` on `0x91030080 == 0x91030080` and `0` on mismatch in all states.
    - `VerifySignature`: enters original prologue + hits `.plt` (`orig=1`), returns `0` immediately when patched (`plt=False`), restores original `.plt` call on rollback.
    - `chkFirmInfo_before_reject_ret` & `chkFirmInfo_before_cmp_csinv`: `w19=0xffffffff` originally and after rollback, `w19=0x0` when patched.
  - SquashFS `Z_SYNC_FLUSH` repack preserved exact byte length (`25,100,288` B? Note: 2.04/2.05 payloads preserve exact source image length), passed independent `SquashFS` readback, and passed 2-pass SHA-256 rollback verification (`pass1_sha256 == pass2_sha256 == source_sha256`).
- **Shifted `v7.02`-Simulated ELF64 & Clean-Room FAT12+SquashFS**:
  - Shifted `+0x140` / `+0x280` (and `+0x3c0` / `+0x700` with VMA bias `0x200000`), plus rebased donor VMAs (`+0x80000` / `+0x120000`), all pass Unicorn AArch64 execution, `Z_SYNC_FLUSH` repack, and 2-pass SHA-256 rollback.

---

## 3. Deliverable 2: 2026 Runtime Anti-Brick Guards & Brick Classifier v2

| Guard / Classifier Feature | Vector Blocked / Diagnosed | Key Enforcement & Recovery Contract |
| :--- | :--- | :--- |
| `audit_ld_so_preload_and_overlay` | `LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK` | Blocks `/etc/ld.so.preload`, `ld.so.preload`, and Jiritsu `0x400f` `SET_FILE_PATH` traversals (`/tmp/jiritsu/../../etc/...`); enforces `rm -f /tmp/mod_arm_once` + `sync` BEFORE `LD_LIBRARY_PATH=` or `mount --bind`. |
| `audit_busybox_dd_commands` & `audit_pmca_5step_write_contract` | `BUSYBOX_DD_TRUNCATION_HAZARD` & `PMCA_5STEP_WRITE_GUARD_VIOLATION` | Blocks `dd of=<file>` lacking verified `conv=notrunc` support (`busybox_notrunc_verified=False`) and any `dd`/`>` targeting `/dev/nflasha*`, `/setting/*`, `/etc/*`, `/usr/*`, `/boot/*`; enforces Drop exit guard, tmpfs staging, full SHA-256 readback, and 5-slot rollback manifest. |
| `audit_nflasha10_vfat_budget` | `NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009` | Enforces 12 MiB partition limit (`12,582,912` B), 4 KiB VFAT cluster rounding, and `>= 2 MiB` default headroom (`1 MiB` hard floor) to prevent `0x10000009` write-lockout across shared `/setting`, `/tmp`, `/etc`, `/var`. |
| `audit_camset_bk4_diff` | `CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK` | Permits safe user `BK4` keys (`0x02cf1bf2` De-Squeeze, `0x02cf1453` LUT, `0x02cf1702` Shutter Mode, `0x02cf0004` NTSC/PAL) and valid checksummed user offsets while blocking `PRODUCT_MODEL` (`ALCIN_UUD` enum `4`), `0x02CF0001`, and protected `BK4` header/identity mutations. |
| `classify_brick_state` extensions | `13S` (`0x100D`), `6L+9S` (`WF-12` / Sony `00342260`), `0x10000009`, `ld.so.preload` | Maps each fault to exact non-destructive recovery playbooks including FX3 Multi-port `RP2040-Zero` (`-DOPEN_DRAIN`, `48,000` baud) Tier-3 rescue (`18D1:4EE0`) and Stage-B degraded mode, while preserving 100% compatibility with existing `classify_brick_state` callers. |

---

## 4. Verification Summary

All tests were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** mode and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** mode:

- `outputs/fx3-recovery-adapter/tests` (includes 24 new tests in [`test_p1_symbol_autolocator.py`](../../outputs/fx3-recovery-adapter/tests/test_p1_symbol_autolocator.py)):
  - Local Donor mode: **109 tests ran (`OK`, `skipped=1` existing conditional test)** — all 24/24 new autolocator tests passed.
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`: **51 tests ran (`OK`, `skipped=7`)** — 22/24 clean-room autolocator tests passed (2 donor-only tests skipped cleanly).
- `outputs/fx3-safety/tests` (includes 24 new tests in [`test_runtime_antibrick_guards.py`](../../outputs/fx3-safety/tests/test_runtime_antibrick_guards.py)):
  - Local Donor mode: **65 tests ran (`OK`)** — all 24/24 new anti-brick & classifier tests passed.
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`: **65 tests ran (`OK`, `skipped=1`)** — all 24/24 new anti-brick & classifier tests passed.
- Clean-room binary/bytecode hygiene (`make clean-audit`): **CLEAN** (zero untracked `.so`/`.elf`/`.ko`/`.cpio`/`.bin`/`.vfat`/`.pyc` or `__pycache__`).
