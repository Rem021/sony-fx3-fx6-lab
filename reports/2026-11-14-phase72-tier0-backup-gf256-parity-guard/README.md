# Phase 72 — Tier-0 Backup `GF(256)` Parity Bit-Rot Healer, Short-Read/Blank-Flash Detector & Cross-Body Anti-Transplant Lock

> **Date**: `2026-11-14` · **Worker**: `gemini-4-hydrogen`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `PHYSICAL_DEVICE_WRITES = 0` (hard-locked)

---

## 1. Executive Summary

Phase 72 delivers an offline, zero-hardware-write host-backup integrity, `GF(2^8)` Reed-Solomon / RAID-6 dual-parity healing, and per-body cryptographic anti-transplant firewall in [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md) for FX3 (`0x91030080`) `Tier-0` recovery backups:

| Deliverable | Entrypoints | Core Invariants & Failure Gates |
| :--- | :--- | :--- |
| **1. 11-Partition `Tier-0` Truncation, Blank-Flash & A/B Symmetry Verifier** | [`validate_tier0_partition`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), [`validate_tier0_backup_bundle`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py) | Validates all 11 critical partitions (`nbl_a`, `nbl_b`, `uboot_a`, `uboot_b`, `boot_a`, `boot_b`, `p1_vfat`, `bk4_nvram`, `wbi2_hibdrv`, `cnflasha_spacc`, `c2pa_rq_lic`). Rejects `dd` short reads & header overflows (`TRUNCATED_PARTITION_DUMP`), uninitialized/erased bus reads (`ALL_ZERO_BLANK_READ`, `ALL_FF_ERASED_FLASH_READ`, `DEGENERATE_BYTE_ENTROPY`), invalid structural magics (`INVALID_STRUCTURAL_MAGIC`, zero Sony keys embedded), and A/B slot drift (`AB_SLOT_ASYMMETRY_DETECTED`). |
| **2. Pure-Python `GF(2^8)` (`0x11d`) `P + Q` RAID-6 Bit-Rot Healer** | [`encode_gf256_pq_parity`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), [`heal_gf256_pq_shards`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), [`heal_tier0_backup_bundle`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py) | Precomputes `GF(2^8)` (`0x11D`, generator `0x02`) `exp`/`log`/`inv` and `bytes.translate` tables. Heals 1 or 2 erased shards (exhaustive all $\binom{11}{2} = 55$ pairs verified), 1-shard silent bit-rot via pure `GF(256)` syndrome localization (`S1 / S0 == g^x`), and up to 2 corrupted/erased shards (`reconstructed_sha256 == original_sha256`). Fails closed on `>= 3` simultaneous losses (`UNRECOVERABLE_QUORUM_LOSS`). |
| **3. Per-Body Hardware Identity Lock (`Cross-Body Anti-Transplant Firewall`)** | [`compute_body_identity_binding_sha256`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), [`build_tier0_backup_manifest`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), [`verify_cross_body_anti_transplant`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py) | Binds `tier0_backup_manifest_v1` to `body_identity_binding_sha256` derived from `(camera_model, body_serial_hash, cnflasha_calibration_sha256, c2pa_rq_lic_sha256)`. Rejects cross-body `cnflasha` / `RQ_LIC.DAT` C2PA pairing (`CROSS_BODY_TRANSPLANT_FORBIDDEN`) and enforces `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_device_writes = 0`. |
| **4. CLI & 32 Fast Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_tier0_backup_parity_and_manifest_guard.py`](../../outputs/fx3-recovery-adapter/tests/test_tier0_backup_parity_and_manifest_guard.py) | Wires `verify-tier0-backup [--clean-room] [--json] [--out ...]`, exports all Phase 72 symbols in `__init__.py`, and adds **32 fast dual-mode tests** passing in both Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes. |

---

## 2. Verification Commands & Observed Results

- **Phase 72 Unit Tests (`test_tier0_backup_parity_and_manifest_guard.py`, 32 tests)**:
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **32 tests** ran in **0.266s** (`OK`).
  - Local Donor mode (`os.O_RDONLY` verifying `2.05/nflasha1` and `nflasha5.img`): **32 tests** ran in **0.469s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **263 tests** (`231` existing + `32` new) in **26.919s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **205 tests** (`173` existing + `32` new) in **2.562s** (`OK`, `skipped=8`).
- **CLI Entrypoint Verification**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-tier0-backup` → `exit 0` (`status=VERIFIED_TIER0_BACKUP mode=LOCAL_DONOR_O_RDONLY all_passed=True partitions=11 body_binding_sha256=c65670ea25a2c28e physical_device_writes=0 persistent_emmc_writes_authorized=False persistent_write_release=False`).
  - `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-tier0-backup --clean-room` → `exit 0` (`mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`).
- **Clean-Room Hygiene Audit**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` → `ALL GREEN` (`0.20s`).
