# Phase 47 — Unified Tier-0..Tier-4 Unbrick Escalation Ladder Simulator & `p1` VFAT Atomic Rollback Capsule Verifier

> **Date**: `2026-11-14` · **Worker**: `Hydrogen-40` · **Branch**: `codex/h40-phase47-recovery-unbrick-ladder-capsule`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `ALLOW_PERSISTENT_JIRITSU_WRITES = False`, `WBI_MUTATION_BYTES = 0`, `EMMC_WRITE_BYTES = 0` (hard-locked)

---

## 1. Executive Summary

Phase 47 unifies all five recovery pillars in [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md) ([`capture.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/capture.py), [`boot_worker.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/boot_worker.py), [`macos_usb_transport_guard.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/macos_usb_transport_guard.py), [`p1_symbol_autolocator.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/p1_symbol_autolocator.py), and [`emmc_dump_forensic_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/emmc_dump_forensic_verifier.py)) into a single deterministic **Tier-0..Tier-4 Unbrick Escalation State Machine** and **`p1` VFAT Atomic Rollback Capsule Verifier**:

| Deliverable | Entrypoints | Core Invariants & Evidence |
| :--- | :--- | :--- |
| **1. 12-Scenario Tier-0..Tier-4 Escalation Matrix** | [`default_12_scenarios`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [`evaluate_unbrick_scenario`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [`run_12_scenario_escalation_matrix`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py) | Deterministic diagnosis -> minimal-privilege `TIER_0..TIER_4` selection -> post-recovery verification across all 12 specified FX3/FX6 failure & safety scenarios (`emmc_write_bytes == 0`, `wbi_mutation_bytes == 0`). |
| **2. `p1` VFAT Atomic Rollback Capsule Verifier (`FAT12`/`FAT16`)** | [`build_p1_vfat_rollback_capsule`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [`verify_p1_vfat_capsule`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [`audit_capsule_fsync_order`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py) | Verifies `FAT12` (16 clusters) & `FAT16` (4,100 clusters) `p1` failsafe hook capsules: `8.3` + VFAT LFN entries & DOS checksums, `FAT1 == FAT2` mirror equality, cycle/cross-link rejection, strict 6-step `fsync` atomic staging (`O_CREAT\|O_EXCL\|O_NOFOLLOW` + two-pass `O_RDONLY` SHA-256), and `boot_attempts >= 1` one-shot latch. |
| **3. Dual-Mode Recovery Pillar Audit (`O_RDONLY` / Clean-Room)** | [`audit_recovery_pillars_dual_mode`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py), [`run_unbrick_ladder_and_capsule_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py) | Reads FX3 `2.05/nflasha1` (`19,377,152 B`, SHA-256 `ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591`) strictly via `os.O_RDONLY` two-pass verification (`LOCAL_DONOR_O_RDONLY`), or switches deterministically to synthetic clean-room fixtures under `FX3_FX6_FORCE_CLEAN_ROOM=1` (`CLEAN_ROOM_SYNTHETIC`). |
| **4. CLI & Fast Dual-Mode Test Suite** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`test_unbrick_ladder_and_capsule.py`](../../outputs/fx3-recovery-adapter/tests/test_unbrick_ladder_and_capsule.py) | Wires `verify-unbrick-ladder [--clean-room] [--json] [--out ...]`, exports all public symbols in [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), preserves all 137 existing tests, and adds **30 fast dual-mode tests** (`0.543s` local / `0.494s` clean-room). |

---

## 2. Deterministic 12-Scenario Tier-0..Tier-4 Escalation Matrix

Each scenario maps an exact failure signature to the minimal-privilege recovery tier (`TIER_0` -> `TIER_4`) and validates post-recovery state invariants without authorizing persistent eMMC or BootROM writes:

| # | Scenario ID | Minimal Tier | Invoked Pillars | Verified Disposition & Outcome |
| :-: | :--- | :---: | :--- | :--- |
| 1 | `S01_CLEAN_STAGE_AB_REBOOT` | `TIER_0` | `capture`, `macos_usb_transport_guard` | `RECOVERED_STOCK_BOOT` — Zero-persistence RAM teardown (`emmc_write_bytes = 0`), instant stock FX3 `v7.02` boot. |
| 2 | `S02_P1_VFAT_BOOT_COUNTER_LATCH` | `TIER_0` | `emmc_dump_forensic_verifier` | `RECOVERED_ONESHOT_FAILSAFE_LATCH` — `p1` VFAT `boot_attempts >= 1` trips one-shot latch -> automatic stock boot without SD removal. |
| 3 | `S03_WF12_00342260_WIRELESS_HANG` | `TIER_0` | `macos_usb_transport_guard` | `RECOVERED_WF12_GUARD_AND_COLD_CYCLE` — Prevented by `P12` `0x70d4` + `BK4` Airplane shadow; cleared on unpatched trial via `>= 60s` cold power-cycle. |
| 4 | `S04_0X100D_EARLY_INIT_APPFW_ABORT` | `TIER_0` | `emmc_dump_forensic_verifier` | `RECOVERED_HOOK_SKIP` — `0x100D` (`13S` LED) early `init`/`appFw` abort -> `TIER_0` one-shot hook skip -> stock FX3 boot. |
| 5 | `S05_MACOS26_IOUSBHOST_PIPE_STALL_H0` | `TIER_1` | `macos_usb_transport_guard`, `capture` | `RECOVERED_USB_QUIESCENCE_AND_RETRY` — macOS 26 `IOUSBHost` `0xe00002be` conflict during `H0` read-only capture resolved via `>= 350 ms` MSC quiescence + exponential backoff (`50/100/200/400/800 ms`), zero duplicate retries on STALL. |
| 6 | `S06_SHIFTED_VMA_V702_P1_AUTOLOCATE` | `TIER_2` | `p1_symbol_autolocator` | `RECOVERED_AUTOLOCATED` — Hardcoded v2.00 offsets rejected fail-closed; 4-site AArch64 `ADRP/BL` autolocator resolves shifted VMA FX3 `v7.02` offsets (`isVersionOK`, `VerifySignature`, `chkFirmInfo_before_reject_ret`, `chkFirmInfo_before_cmp_csinv`) and verifies byte-exact rollback. |
| 7 | `S07_CORRUPTED_H0_EMMC_STUCK_BUS` | `TIER_4` | `emmc_dump_forensic_verifier` | `BLOCKED_FAIL_CLOSED` — All-`0x00`, all-`0xFF`, and truncated `H0` dumps caught pre-flight by bus/entropy analyzer (`h1_entry_blocked = True`). |
| 8 | `S08_VMC_BNCM1_LTC_CABLE_TIER3_UART` | `TIER_3` | `emmc_dump_forensic_verifier` | `BLOCKED_FAIL_CLOSED` — Multi-Port `VMC-BNCM1` LTC cable plugged in blocks `Tier-3` `RP2040-Zero` `-DOPEN_DRAIN` `48000`-baud `uart_boot` until unplugged and `1.8V/3.3V` open-drain fixture verified. |
| 9 | `S09_DESTRUCTIVE_FASTBOOT_FIREWALL` | `TIER_3` | `emmc_dump_forensic_verifier` | `BLOCKED_FAIL_CLOSED` — Destructive Fastboot (`fastboot erase boot0`, `flash:boot0`, `oem format`) rejected by BootROM command firewall & `audit_boot_chain_immutability` (`persistent_emmc_writes_authorized = False`). |
| 10 | `S10_LD_SO_PRELOAD_BUSYBOX_DEADLOCK` | `TIER_2` | `p1_symbol_autolocator`, `macos_usb_transport_guard` | `BLOCKED_FAIL_CLOSED` — `/etc/ld.so.preload` dynamic BusyBox deadlock rejected pre-packaging; static-binary and `LD_PRELOAD`-scoped `appFw` launcher contracts verified. |
| 11 | `S11_CROSS_BODY_FX6_WBI2_INJECTION` | `TIER_2` | `emmc_dump_forensic_verifier` | `BLOCKED_FAIL_CLOSED` — Cross-body `ILME-FX6` (`v6.01`) `WBI2` hibernation snapshot injection into FX3 (`0x91030080`) rejected fail-closed (`wbi_mutation_bytes == 0`). |
| 12 | `S12_THERMAL_OR_USBPD_BROWNOUT_ABORT` | `TIER_0` | `capture`, `macos_usb_transport_guard` | `ABORTED_GRACEFUL` — Thermal `>= 90.0°C` (`91.5°C`) or USB-PD `< 7.80V` (`7,650 mV`) VBUS brownout during `H0` capture triggers graceful abort with `0` partition mutations. |

---

## 3. `p1` VFAT Atomic Rollback Capsule & Two-Pass SHA-256 Verification

- **Supported VFAT Geometries**:
  - `FAT12` (`311,808 B`, `16,384 B` clusters, `16` clusters): Tripped capsule (`boot_attempts=1`, `max_boot_attempts=1`) deterministic `capsule_sha256`:
    `663503a208d3797d07c4c0e980d7414fe95140914262e58ed36e6a0973f1061d`
  - `FAT16` (`2,133,504 B`, `512 B` clusters, `4,100` clusters): Tripped capsule (`boot_attempts=1`, `max_boot_attempts=1`) deterministic `capsule_sha256`:
    `7da7b1dc9cb57f70f0d1cc76cc5616ca14587aaee5cc3de13aa1ac38ac7d2946`
- **Structural & Integrity Checks**:
  - Validates BPB boot signature (`0x55AA`), cluster geometry (`FAT12 <= 4084`, `4085 <= FAT16 <= 65524`), and exact `FAT1 == FAT2` mirror equality.
  - Validates `8.3` uppercase name/character whitelist (`short_83_valid`), VFAT Long File Name (`0x0F`) sequence numbering, UTF-16LE reconstruction, and exact `lfn_checksum` across `/boot`, `/boot/vmlinux.bin`, `/boot/initrd.img`, `/capsule`, `/capsule/failsafe-hook-capsule.cfg`, `/capsule/capsule-manifest.json`, and `/p1chksum`.
  - Detects and rejects cyclic FAT cluster chains and cross-linked clusters across directory entries.
- **Atomic Staging & Strict `fsync` Ordering**:
  - Enforces the 6-stage sequence in a `tempfile.TemporaryDirectory` (`O_CREAT | O_EXCL | O_NOFOLLOW`, mode `0600`):
    `stage_tmp_write` -> `fsync_tmp_file` -> `verify_pass1_sha256_o_rdonly` -> `atomic_replace` -> `fsync_parent_dir` -> `verify_pass2_sha256_o_rdonly`.
  - Rejects out-of-order `fsync` traces, manifest tampering (`persistent_emmc_writes_authorized = True`), or external SHA-256 mismatches fail-closed.

---

## 4. Verification Commands & Results

- **Phase 47 Unit Tests (`outputs/fx3-recovery-adapter/tests/test_unbrick_ladder_and_capsule.py`, 30 tests)**:
  - Local Donor mode:
    `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_unbrick_ladder_and_capsule.py -v` -> **30 tests** ran in **0.543s** (`OK`).
  - Clean-Room mode:
    `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_unbrick_ladder_and_capsule.py -v` -> **30 tests** ran in **0.494s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode: **167 tests** (`137` existing + `30` new) ran in **26.708s** (`OK (skipped=1)` optional Unicorn dependency).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **109 tests** ran in **1.016s** (`OK (skipped=8)` donor-only classes in pre-existing suites; all 30 Phase 47 tests passed).
- **CLI Entrypoint Verification**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-unbrick-ladder` -> `exit 0` (`status=VERIFIED_ALL_12_SCENARIOS_AND_CAPSULES mode=LOCAL_DONOR_O_RDONLY all_passed=True scenarios_passed=12/12 persistent_emmc_writes_authorized=False`).
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-unbrick-ladder --clean-room --json` -> `exit 0` (`verification_mode=CLEAN_ROOM_SYNTHETIC`, `scenarios_passed=12`).
- **Repository Hygiene**:
  - `make clean-audit` (`ALL GREEN`) and clean `git status --porcelain`.
