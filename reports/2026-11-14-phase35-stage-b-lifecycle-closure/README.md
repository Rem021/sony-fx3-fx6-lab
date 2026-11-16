# Phase 35 — Stage-B (`P1..P12+Fan`) 10-Scenario RAM-Overlay Lifecycle, Serial Watchdog (`serial_fault_detector_v2`) & `H0 -> H1 -> H2` Cryptographic Zero-Drift Closure Report

- **Date**: 2026-11-14
- **Branch**: `codex/h27-phase35-stage-b-lifecycle`
- **Owner**: Hydrogen-27 (Stage-B Full-Lifecycle & Hardware Zero-Drift Verification)
- **Deliverables**:
  - [`outputs/fx6-on-fx3-closure/fx6_closure/stage_b_lifecycle_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/stage_b_lifecycle_verifier.py)
  - [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
  - [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) (`run-stage-b-lifecycle-drill [--clean-room] [--output PATH]`)
  - [`outputs/fx6-on-fx3-closure/tests/test_phase35_stage_b_lifecycle.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase35_stage_b_lifecycle.py) (25 unit & scenario tests, `< 5s` in both Local Donor and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)
  - [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)

## 1. Stage-B (`P1..P12+Fan`) Architecture & Safety Redlines

Phase 35 unifies the Stage-A RAM-overlay lifecycle with all Stage-B deliverables (`P10` physical keymap, `P11` UIPC-CP shim + `XLR-H1` preservation + Cine EI / `33^3` 3D LUT / IBIS bridge, `P12` `libWlanResource.so` `0x70d4` fatal guard + `BK4\0` cold-boot Airplane-Mode RAM shadow) inside a single deterministic `H0 -> H1 -> H2` verifier:

- **Hard-Locked Safety Constants**:
  - `persistent_emmc_writes_authorized = False`
  - `persistent_write_release = False`
  - `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes == 0`)
  - `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes == 0`)
  - `usb_or_camera_operations = 0`
  - All donor reads executed strictly via `os.O_RDONLY`; all staging performed inside ephemeral `tempfile.TemporaryDirectory()` (`temp_dir_cleaned = True`).

- **Stage-B Orchestrator (`etc/fx6_overlay/35-stage-b-orchestrator.sh`)**:
  - Enforces host sandbox `PREFIX` guard, idempotent re-entry lock, and unarmed stock FX3 cold-boot passthrough.
  - Performs **Layer-2 Clear-Before-Exec**: unlinks `/tmp/mod_arm_once` and executes `busybox sync` before any verification, `insmod`, or `mount --bind`.
  - Locks `p5:/dev/nflasha5` WBI hibernation (`STAGE_B_WBI_HIBERNATION_FORBIDDEN=1`), enforces `upm_bootmode != BIS`, and runs **Atomic Verify-Before-Mount SHA-256** across all staged payloads + `ram_shadow_Backup.bin`.
  - Executes 12 forward steps (`01_kmod_p9_upm_ko` .. `12_activate_p11_uipc_cp_shim`) and unwinds strictly in reverse `12..1` LIFO order before stock restoration.

## 2. 10-Scenario Stage-B `H0 -> H1 -> H2` Lifecycle Matrix

| ID | Scenario | Phase Scope | Serial Watchdog / Guard Disposition | Verified Outcome |
| --- | --- | --- | --- | --- |
| `S01` | `S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE` | `H0 -> H1 -> H2` | `PASS` (`< 90s` / `< 220s` `TIMER-IP`) | 12/12 forward & LIFO steps, Clear-Before-Exec, Verify-Before-Mount, cold reboot passthrough, `13/13` (`11+2`) items `H0 == H2`, `0` eMMC/WBI/CP/NVRAM writes |
| `S02` | `S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT` | `H1_VERIFY_BEFORE_MOUNT` | `FAIL_CLOSED_ABORT` (`VERIFY_BEFORE_MOUNT_SHA_MISMATCH`) | 1-bit flip in `appFw.so` (`e2bc2619...`) aborts with `0` mounts, falls back cleanly to stock FX3 |
| `S03` | `S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT` | `H1_VERIFY_BEFORE_MOUNT` | `FAIL_CLOSED_ABORT` (`VERIFY_BEFORE_MOUNT_SHA_MISMATCH`) | 1-bit flip in `libWlanResource.so` (`47fec188...`) aborts with `0` mounts and zero `0x70d4` hang |
| `S04` | `S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL` | `H1_RUNTIME_FAULT` | `ALLOWED_DEGRADED` (`WF12_DEGRADED_RADIO_OFF`) | Simulated `WF-12` SDIO + `00342260` handled cleanly (`patched_rc=0`), shooting continues, `0` bootloops |
| `S05` | `S05_BT_BSA_UART_ABSENT_SURVIVAL` | `H1_RUNTIME_FAULT` | `ALLOWED_DEGRADED` (`BT_DEGRADED_DISABLED_0xBB9`) | Missing `/dev/ttyAMA3` resolved via `BK4\0` Airplane shadow (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`) + `0xbb9`, zero `"System Error"` |
| `S06` | `S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE` | `H1_RUNTIME_FAULT` | `ALLOWED_DEGRADED` (`P11_DETACHED_GRIP_ACK_0x91DB059B`) | `P11` `0x91db059b` detached-grip ACK unblocks cold boot while keeping `XLR-H1` MI-Shoe digital audio (`0x5d90`) online |
| `S07` | `S07_LD_SO_PRELOAD_INJECTION_BLOCKED` | `PRE_STAGING_GUARD` | `FAIL_CLOSED_ABORT` (`LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK`) | `/etc/ld.so.preload` injection blocked by `runtime_antibrick_guards` before staging |
| `S08` | `S08_NFLASHA10_0x10000009_HEADROOM_GUARD` | `PRE_STAGING_GUARD` | `FAIL_CLOSED_ABORT` (`NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009`) | `nflasha10` 12 MiB VFAT overrun caught and blocked before staging |
| `S09` | `S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT` | `H1_WDT_REVERT` | `FAIL_CLOSED_ABORT` (`watchdog_passed=False`) | Simulated `> 90s` stall caught; `/tmp/mod_arm_once` already cleared -> reset boots straight into untouched stock FX3 (`H2 == H0`) |
| `S10` | `S10_POST_TRIAL_DRIFT_DETECTION` | `H0 -> H2_AUDIT` | `FAIL_CLOSED_ABORT` (`POST_TRIAL_DRIFT_DETECTED`) | 1-byte drift injected on `p12_cert` and `p5_wbi_header` caught fail-closed by `verify_post_trial_zero_mutation` |

## 3. Verified Digests & Execution Results

### Local Donor Mode (`LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED`)
- **Stage-B `appFw.so` (`P1+P4+P8+P10`) SHA-256**: `e2bc2619845e9614...` (`FX6_APPFW_STAGE_B_SHA256`)
- **Stage-B `libWlanResource.so` (`P12`) SHA-256**: `47fec188cc174faa...` (`FX6_WLAN_RSRC_P12_SHA256`)
- **Deterministic `report_sha256`**: `a8cd29fe0a31e7833d9f4f69c01e14b3d9a88109b3cf5a7ef8a08c0e812f03a1`
- **`H2` Receipt SHA-256 (`13` items, `0` bytes mutated)**: `d82216d3c8e0ab60...`
- **Test Suite (`test_phase35_stage_b_lifecycle.py`)**: `Ran 25 tests in 3.876s — OK`

### Clean-Room CI Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` / `--clean-room`)
- **Verification Mode**: `CLEAN_ROOM_SYNTHETIC_VERIFIED`
- **Deterministic `report_sha256`**: `5bb97d65c3857ca4dcec3eb74b4199180c04398e842bca7aa1fb87ff1a6e7386`
- **`H2` Receipt SHA-256 (`13` items, `0` bytes mutated)**: `4eceec9ef259300e...`
- **Test Suite (`test_phase35_stage_b_lifecycle.py`)**: `Ran 25 tests in 3.064s — OK`

### Commands Executed
```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
  /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase35_stage_b_lifecycle.py

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
  /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase35_stage_b_lifecycle.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
  /usr/bin/python3 -B -m fx6_closure run-stage-b-lifecycle-drill

FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
  /usr/bin/python3 -B -m fx6_closure run-stage-b-lifecycle-drill --clean-room
```
