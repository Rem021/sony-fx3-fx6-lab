# Phase 32 Report — Fail-Closed Serial & Kernel Telemetry Fault Detector v2

- **Worker**: Hydrogen-24
- **Branch**: `codex/h24-phase32-serial-fault-wdt-v2`
- **Date**: `2026-11-14`
- **Safety Posture**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `PERSISTENT_WRITE_RELEASE = False` (hard-locked) · `os.O_RDONLY`-only file reads

---

## 1. Deliverables Summary

1. **[`outputs/fx3-safety/fx3_safety/serial_fault_detector_v2.py`](../../outputs/fx3-safety/fx3_safety/serial_fault_detector_v2.py)**
   - Implemented deterministic **streaming (`StreamingSerialFaultDetectorV2`)** and **batch (`audit_serial_boot_telemetry`)** fail-closed serial & kernel telemetry fault detection across five engineering domains:
     1. **Sony Linux `4.9.337-scel+` Kernel Panics, Oops & Signal Diagnostics**: Detects `Unable to handle kernel`, `Kernel panic`, `Internal error: Oops`, `SError Interrupt`, `BUG:`, `Unhandled fault:`, Sony `zve10-qemu` diagnostic classes `ZZTGKILL`, `ZZSTACK`, `ZZEXCSTACK`, `SIGSEGV`/`SIGABRT`/`SIGBUS`/`SIGILL`, and `assert at <source>:<line>`.
     2. **Dynamic Linker & Device/Module Missing Diagnostics**: Detects `MISSSO`, `MISSDEV`, `IMOPEN` (error/missing vs benign `status=OK`), `MODLOAD` (error/missing vs benign `rc=0`/`module_loaded=1`), `error while loading shared libraries`, and `/etc/ld.so.preload` dynamic `busybox`/`/sbin/init` deadlock markers.
     3. **Synchronization & IPC Hang Diagnostics**: Detects `ZZFUTEX`, `ZZCOMPLETE`, `INFO: task .* blocked for more than`, unpatched `WlanResourceMainThread` `0x70d4` `handleFatalError` infinite `usleep` loops (while allowing verified `P12_wlan_resource_handleFatalError_nonblocking` `status=OK`), and unshimmed UIPC `0x92d2091c` / `0x91db059b` blocking timeouts (distinguished from shimmed `P11` ACK `0x91db059b`).
     4. **`TIMER-IP` `220.0s` (`3m 40s`) & `90.0s` Stage-A Guard Watchdog Budget Verifier (`verify_watchdog_budget`)**: Enforces that `WDT_SET_STOP` and active (non-commented) `/tmp/mod_arm_once` Clear-Before-Exec occur strictly before the `90.0s` Stage-A soft guard and `220.0s` `TIMER-IP` hardware watchdog ceiling, and strictly before `mount --bind`/overlay execution.
     5. **Degraded-Safe vs Fatal Classifier + `brick_classifier.py` Cross-Links**:
        - **Allowed Degraded (`ALLOWED_DEGRADED`, `passed=True`, `abort_required=False`)**: `WF12_DEGRADED_RADIO_OFF` / Notice `00342260`, `BT_DEGRADED_DISABLED` `0xbb9`, `P11` detached-grip ACK `0x91db059b`, `P11` `/dev/rtc0` `open_ok=0` probe, and `P4` ND `Clear`.
        - **Fail-Closed Abort (`FAIL_CLOSED_ABORT`, `passed=False`, `abort_required=True`)**: `"System Error"`, `0x10000009` `nflasha10` VFAT exhaustion, Verify-Before-Mount SHA mismatch / nonzero `FX6_STAGE_A_VERIFY_RC`, and `nop_count > 0` or substitution invariant breaches in `FX6_NATIVE_FAITHFUL=1` mode — each automatically cross-linked to [`classify_brick_state(...)`](../../outputs/fx3-safety/fx3_safety/brick_classifier.py) recovery playbooks (`LEVEL_0`..`LEVEL_4`).
   - Added [`audit_round10_summary_telemetry`](../../outputs/fx3-safety/fx3_safety/serial_fault_detector_v2.py) to validate our committed Round 10 real FX3 `4.9.337-scel+` [`summary.json`](../2026-11-14-round10-fx6-on-fx3-full-icon-presenter/summary.json) strictly via `os.O_RDONLY` (auditing all 4 runs `r10a`..`r10d`: `wall_elapsed_sec` `61.62s..80.93s < 90.0s`, `nop_count=0`, `crashes=0`, `FX6_STAGE_A_VERIFY_RC=0`, `P11` `0x91db059b` ACK, `P4` ND `Clear` -> `ALLOWED_DEGRADED`), with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.

2. **Package Exports, Documentation & Unit Tests (`24` New Tests)**
   - Exported v2 symbols in [`outputs/fx3-safety/fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py).
   - Updated [`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md) with Section 4 documentation and CLI usage.
   - Added [`outputs/fx3-safety/tests/test_serial_fault_detector_v2.py`](../../outputs/fx3-safety/tests/test_serial_fault_detector_v2.py) (**24** new unit & fault-injection tests, bringing `outputs/fx3-safety/tests` from `92` to **`116` tests**).

---

## 2. Verification Results

All checks were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B`:

| Suite / Command | Mode | Result | Duration |
| :--- | :--- | :---: | :---: |
| `outputs/fx3-safety/tests` (`PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter`) | Normal | `116` tests (`OK`, `0` skipped) | `0.122s` |
| `outputs/fx3-safety/tests` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | Clean-Room | `116` tests (`OK`, `skipped=1` external donor) | `0.119s` |
| `python3 -B -m fx3_safety.serial_fault_detector_v2 --round10-summary` | Committed `summary.json` | Exit `0`, `all_passed=True`, `overall_disposition=ALLOWED_DEGRADED`, `runs_audited=4` | `< 0.1s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 python3 -B -m fx3_safety.serial_fault_detector_v2 --round10-summary` | Clean-Room Fallback | Exit `0`, `all_passed=True`, `telemetry_source=clean_room_synthetic`, `runs_audited=4` | `< 0.1s` |
| `make clean-audit` | Cleanliness | Clean-room audit passed (`0` residue binaries/pyc) | `0.03s` |
