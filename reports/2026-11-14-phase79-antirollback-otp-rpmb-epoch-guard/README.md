# Phase 79 — `CXD90057` OTP/RPMB Anti-Rollback Monotonic Epoch Verifier, Bootloader Downgrade Brick Firewall & BYOF Donor Compatibility Matrix

> **Date**: `2026-11-14` · **Worker**: `gemini-4-hydrogen`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `PHYSICAL_DEVICE_WRITES = 0` (hard-locked)

---

## 1. Executive Summary

Phase 79 delivers an offline, zero-hardware-write `CXD90057` Secure-Boot OTP/RPMB anti-rollback firewall, a zero-key BYOF donor compatibility & structural verifier, and an eMMC `EXT_CSD` permanent write-protect fuse-trap guard in [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md):

| Deliverable | Entrypoints | Core Invariants & Failure Gates |
| :--- | :--- | :--- |
| **1. `CXD90057` OTP Fuse & `RPMB` Monotonic Anti-Rollback Firewall** | [`evaluate_bootchain_transition`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py), [`evaluate_stage_b_volatile_ram_overlay`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py) | Models monotonic epoch enforcement across `BootROM -> nbl_a/b -> tz/optee -> uboot_a/b -> kernel boot_a/b`. Blocks flashing pre-`v7.00` boot-chain components (`v1.01..v6.00`) onto Sony `v7.00`/`v7.02` ratcheted FX3 bodies (`BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE`). Blocks cross-SKU `FX6` `nbl`/`tz`/`uboot`/`WBI2`/`cpapp-b.bin` transplants onto `FX3` (`BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK`). Proves structurally that the **Stage-B Volatile RAM Overlay** (`FX3 v7.02` Stock Bootchain + `FX3 v7.02` `4.9.337-scel+` Kernel + `FX3 v7.02` Stock-CP + `FX6 v6.01` `/tmp` bind-mounts) incurs `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, and `antirollback_brick_risk == "ZERO_USERSPACE_RAM_ONLY"`. |
| **2. Zero-Key BYOF Version Matrix & Donor Tree Verifier** | [`classify_byof_version_pair`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py), [`build_byof_compatibility_matrix`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py), [`validate_byof_donor_tree`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py), [`inspect_elf64_aarch64_bytes`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py) | Inspects local donors strictly `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK` (`4.9.337-scel+`, `GLIBC_2.17`, `CXXABI_1.3..1.3.10`, `WBI2` `1399` vs `1197` sections, `libInfra*`, `cxd90057.dtb`, zero proprietary keys) with clean-room fallback. Classifies `FX3 v7.00/v7.01/v7.02` x `FX6 v5.02/v6.00/v6.01` (`(v7.02, v6.01) -> TIER_A_GOLD_VERIFIED`, `(v7.00/v7.01, v6.01)` & `v6.00 -> TIER_B_CONDITIONALLY_COMPATIBLE`, pre-`v6.00` `v5.02 -> REJECTED_INCOMPATIBLE_PRE_V600_NO_BIG6`). Rejects corrupted trees (`MISSING_REQUIRED_DONOR_MEMBER`, `WRONG_ISA_OR_ENDIANNESS`, `TRUNCATED_ELF_LOAD_SEGMENT`) prior to Stage-B `cpio` packaging. |
| **3. eMMC `EXT_CSD` Permanent WP Fuse Trap Firewall** | [`audit_ext_csd_write_protect`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py), [`audit_mmc_wp_command_or_write`](../../outputs/fx3-recovery-adapter/fx3_recovery/firmware_updata_and_antirollback_guard.py) | Audits JEDEC `EXT_CSD[173]` `B_PERM_WP_EN` (`0x04`) and `EXT_CSD[171]` `US_PERM_WP_EN` (`0x04`) permanent OTP write-protect bits as well as `mmc-utils` / manifest operations attempting permanent WP (`BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP`). |
| **4. CLI & 34 Fast Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_firmware_updata_and_antirollback_guard.py`](../../outputs/fx3-recovery-adapter/tests/test_firmware_updata_and_antirollback_guard.py) | Wires `verify-antirollback-guard [--clean-room] [--json] [--out ...]`, exports all Phase 79 symbols in `__init__.py`, and adds **34 fast dual-mode tests** (`< 0.03s`) passing in both Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes. |

---

## 2. Verification Commands & Observed Results

- **Phase 79 Unit Tests (`test_firmware_updata_and_antirollback_guard.py`, 34 tests)**:
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **34 tests** ran in **0.017s** (`OK`).
  - Local Donor mode (`os.O_RDONLY` verifying FX3 `v7.02` & FX6 `v6.01` `WBI2` `1399` vs `1197` sections, `4.9.337-scel+`, `GLIBC_2.17`, `CXXABI_1.3..1.3.10`, `libInfraSetupFile.so`, `appFw.so`, `cxd90057.dtb`): **34 tests** ran in **0.026s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **297 tests** (`263` existing + `34` new) in **29.073s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **239 tests** (`205` existing + `34` new) in **2.608s** (`OK`, `skipped=8`).
- **CLI Entrypoint Verification**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-antirollback-guard` -> `exit 0` (`status=VERIFIED_ANTIROLLBACK_GUARD mode=LOCAL_DONOR_O_RDONLY all_passed=True otp_fuse_touches=0 rpmb_counter_increments=0 antirollback_brick_risk=ZERO_USERSPACE_RAM_ONLY physical_device_writes=0 persistent_emmc_writes_authorized=False persistent_write_release=False`).
  - `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-antirollback-guard --clean-room` -> `exit 0` (`mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`).
- **Clean-Room Hygiene Audit**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN` (`0.03s`).
