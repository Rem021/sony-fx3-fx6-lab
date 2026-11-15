# Phase 66 — `init2` SD-Card Sentinel Escape Shell, CXD90057 Watchdog Boot-Loop Breaker & `p1` FAT12/FAT16 Chain Integrity Verifier

> **Date**: `2026-11-14` · **Worker**: `gemini-4-hydrogen`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `PHYSICAL_WRITES = 0` (hard-locked)

---

## 1. Executive Summary

Phase 66 delivers an offline, zero-hardware-write recovery-safety verification suite in [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md) proving that FX3 (`0x91030080`) Stage-B overlays can fail open to stock FX3 `v7.02` via field SD/CFexpress sentinel files, GPIO key chords, payload integrity guards, crash-loop unmounting, `CXD90057` hardware watchdog resets, and verified `p1` FAT12/FAT16 pointer consistency:

| Deliverable | Entrypoints | Core Invariants & Failure Gates |
| :--- | :--- | :--- |
| **1. Zero-Hardware `init2` POSIX `/bin/sh` Escape Sandbox** | [`render_init2_escape_wrapper_script`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [`run_init2_escape_drill`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [`run_all_init2_escape_drills`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py) | Executes a pure POSIX `/bin/sh` `init2` wrapper inside an isolated `tempfile.TemporaryDirectory` sandbox proving **4 fail-open escape mechanisms** BEFORE `cpio` extraction or `mount --bind`: (1) `FX3_SAFE_STOCK.FLG` / `DISABLE_STAGE_B.TXT` on Slot A or Slot B (`0` mounts, `0` eMMC writes); (2) `REC+MENU` / `SHUTTER` boot-GPIO chord; (3) corrupt/truncated `stage_b_overlay.cpio` SHA-256 or `070701` magic mismatch; (4) `procam_app` `>= 3` exits within `15s` in volatile `/tmp/stage_b_crash.cnt` triggering `tmpfs` bind unmount and stock `procam_app` `exec`. |
| **2. CXD90057 Hardware Watchdog & `Tier-0..Tier-2` State Machine** | [`simulate_cxd90057_watchdog_scenario`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [`run_cxd90057_watchdog_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py) | Models `timeout_ms=10000`, `kick_interval_ms=2000` across `NORMAL_OPERATION`, `HUNG_UI_PRESENTER`, `KERNEL_OOPS_PANIC_ON_OOPS`, `CLEAN_REBOOT` (`H1 -> H2` volatile RAM wipe), and `EXPERIMENTAL_P1_POINTER_ROLLBACK` (`Tier-1/2`), proving `0` persistent eMMC mutations guarantee `H0 == H2` stock boot restoration on WDT reset alone. |
| **3. Pure-Python `p1` FAT12/FAT16 Chain & Atomic `8.3` Swap Auditor** | [`audit_p1_fat_filesystem`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [`simulate_atomic_83_dir_swap`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py), [`build_synthetic_p1_vfat_with_init2`](../../outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py) | Compatible with [`fx3_recovery.fat.FatP1`](../../outputs/fx3-recovery-adapter/fx3_recovery/fat.py); verifies BPB geometry (`512B`, `fat_count=2`), `FAT1 == FAT2` byte-equality, Floyd + visited-set cycle detection, cross-linked cluster detection, orphan allocated cluster detection, `8.3`/LFN checksums, and in-memory-only `INIT2.SH` ↔ `INIT2BAK.SH` 32-byte pointer swap + exact roundtrip (`physical_writes == 0`). |
| **4. CLI & 34 Fast Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_init2_escape_and_watchdog_simulator.py`](../../outputs/fx3-recovery-adapter/tests/test_init2_escape_and_watchdog_simulator.py) | Wires `verify-init2-escape [--clean-room] [--json] [--out ...]`, exports all Phase 66 symbols in `__init__.py`, and adds **34 fast dual-mode tests** passing in both Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes. |

---

## 2. Verification Commands & Observed Results

- **Phase 66 Unit Tests (`test_init2_escape_and_watchdog_simulator.py`, 34 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **34 tests** ran in **1.150s** (`OK`), with `run_init2_escape_and_watchdog_suite` completing in `< 0.5s`.
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **34 tests** ran in **1.186s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **231 tests** (`197` existing + `34` new) in **28.275s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **173 tests** (`139` existing + `34` new) in **2.187s** (`OK`, `skipped=8`).
- **CLI Entrypoint Verification**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-init2-escape` → `exit 0` (`status=VERIFIED_INIT2_ESCAPE_WDT_FAT mode=LOCAL_DONOR_O_RDONLY all_passed=True escape_drills=7/7 wdt_scenarios=5/5 physical_writes=0 persistent_emmc_writes_authorized=False persistent_write_release=False`).
  - `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-init2-escape --clean-room` → `exit 0` (`mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`).
- **Clean-Room Hygiene Audit**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` (`ALL GREEN`).
