# Phase 86 — Passive `1.8V` RX-Only `CXD90057` UART Boot-Stage Decoder (`S0..S6`) & Unified `fx3_recovery` 7-Pillar Master Self-Audit

> **Date**: `2026-11-14` · **Worker**: `gemini-4-hydrogen`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `PHYSICAL_DEVICE_WRITES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0` (hard-locked)

---

## 1. Executive Summary

Phase 86 closes the unified `outputs/fx3-recovery-adapter/` diagnostics & readiness loop by delivering a passive `1.8V` RX-only `CXD90057` boot-stage state machine (`S0..S6`) with 10-signature fault triage, alongside a `< 1.0s` 7-pillar `fx3_recovery` master readiness audit (`run_recovery_master_suite` & `verify-all-recovery`):

| Deliverable | Entrypoints | Core Invariants & Failure Gates |
| :--- | :--- | :--- |
| **1. Passive `1.8V` RX-Only Tap Firewall & `S0..S6` 10-Signature Fault Triage** | [`audit_passive_rx_tap_safety`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py), [`parse_cxd90057_boot_stages`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py), [`decode_uart_boot_log`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py), [`run_uart_boot_decoder_10_scenario_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py) | Enforces `tx_line_connected == False` or `open_drain_tx_idle_1v8 == True`, `passive_tx_bytes_emitted == 0`, `io_voltage_v in [1.65V, 1.98V]`, and zero LTC cable conflict so `CXD90057` BootROM `uart_boot` is never accidentally triggered during boot monitoring. Parses all 7 stages (`S0_BOOTROM_ENTRY` -> `S1_NBL_OPTEE_TRUSTZONE` -> `S2_UBOOT_BOOT_AB` -> `S3_LINUX_4_9_337_SCEL` -> `S4_INIT2_SENTINEL_CHECK` -> `S5_STAGE_B_TMPFS_MOUNT` -> `S6_ICX1295_BIG6_READY`) and classifies all 10 boot/runtime outcomes with minimal zero-eMMC-write recovery prescriptions (`HEALTHY_STAGE_B_LIVE`, `CLEAN_SD_SENTINEL_STOCK_ESCAPE`, `CLEAN_HASH_FAILOPEN_STOCK_BOOT`, `NO_EMMC_FLASH_NEEDED`, `TIER0_CRASH_BREAKER_RECOVERED`, `TIER0_COLD_REBOOT_WIPES_TMPFS`, `NEVER_CROSS_FLASH_FX6_WBI2`, `TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK`, `CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN`, `DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN`). |
| **2. Unified 7-Pillar `fx3_recovery` Master Readiness Audit** | [`run_recovery_master_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/recovery_master_suite_and_uart_decoder.py) | Concurrently executes and aggregates all 7 pillars in `< 0.5s` across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes: (1) `macos_usb_transport_guard`, (2) `rp2040_multiport_fixture_selftest` (`camera_connected == False`), (3) `init2_escape_and_watchdog_simulator` (`7/7` escape + `5/5` WDT), (4) `tier0_backup_parity_and_manifest_guard` (`GF(256)` P+Q heal + anti-transplant lock), (5) `firmware_updata_and_antirollback_guard` (`otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, `EXT_CSD` perm-WP blocked), (6) `unbrick_ladder_and_capsule_verifier` (`12/12` Tier-0..4 ladder + `p1` VFAT capsules), and (7) passive `S0..S6` UART 10-scenario decoder (`passive_tx_bytes_emitted == 0`). Emits deterministic `recovery_master_sha256` with `persistent_emmc_writes_authorized = False` and `persistent_write_release = False` hard-locked. |
| **3. CLI `verify-all-recovery` & 34 Fast Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_recovery_master_suite_and_uart_decoder.py`](../../outputs/fx3-recovery-adapter/tests/test_recovery_master_suite_and_uart_decoder.py) | Wires `verify-all-recovery [--clean-room] [--json] [--out ...]`, exports all Phase 86 symbols in `__init__.py`, and adds **34 fast dual-mode tests** (`< 0.5s`) covering `S0..S6` transitions, all 10 fault classifications, `TX=0` enforcement, 7-pillar determinism, fault injection fail-closed behavior, CLI output, and Local Donor vs Clean-Room parity. |

---

## 2. Verification Commands & Observed Results

- **Phase 86 Unit Tests (`test_recovery_master_suite_and_uart_decoder.py`, 34 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **34 tests** ran in **0.426s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **34 tests** ran in **0.355s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **273 tests** (`239` existing + `34` new) in **4.324s** (`OK`, `skipped=8`).
  - Local Donor mode (`os.O_RDONLY`): **331 tests** (`297` existing + `34` new) in **29.212s** (`OK`, `skipped=1`).
- **CLI Entrypoint Verification (`verify-all-recovery`)**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --json` -> `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `mode=LOCAL_DONOR_O_RDONLY`, `pillars=7/7`, `uart_scenarios=10/10`, `elapsed_seconds=0.341`, `passive_tx_bytes_emitted=0`, `recovery_master_sha256=0630b15eeaff85be...`, `persistent_emmc_writes_authorized=False`, `persistent_write_release=False`).
  - `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --clean-room` -> `exit 0` (`mode=CLEAN_ROOM_SYNTHETIC`, `pillars=7/7`, `uart_scenarios=10/10`, `recovery_master_sha256=07b2c16ad97e1ac5...`).
- **Clean-Room Hygiene Audit**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN` (`0.04s`).
