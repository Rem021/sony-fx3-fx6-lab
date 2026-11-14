# Phase 28 Report — End-to-End Phase H0 -> H1 -> H2 Read-Only Hardware Rehearsal Engine & Runbook Modernization

- **Worker**: Hydrogen-19
- **Branch**: `codex/h19-phase28-h0-rehearsal-runbook`
- **Date**: `2026-11-14`
- **Safety Posture**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `persistent_write_release = False` (hard-locked)

---

## 1. Deliverables Summary

1. **`outputs/fx3-safety/fx3_safety/h0_hardware_rehearsal.py`**
   - Implemented the 6-stage deterministic, fail-closed Phase H0 read-only rehearsal pipeline (`run_h0_hardware_rehearsal`, `H0RehearsalConfig`, `H0RehearsalReport`, `StageResult`, per-stage entrypoints, and CLI `python3 -B -m fx3_safety.h0_hardware_rehearsal`):
     - **Stage 1 (`S1_multiport_tier3_harness`)**: Audits `RP2040-Zero` (`-DOPEN_DRAIN`, `1.8V` High-Z, strict Back Row pinout `GP27 -> Pin 9 XReset`, `GP28 -> Pin 7 Cam UART RX`, `GP29 <- Pin 8 Cam UART TX`, `GND -> Pin 2`), rejects standard Raspberry Pi Pico `GP29` `VSYS/3` pull-down traps, tests the `48000`-baud `uart_boot` frame codec, enforces `< 0xFFFFC000` WDT firewall, decodes `0x100D` (`13S`), and firewalls Fastboot (`18D1:4EE0`) strictly to read-only inspection commands.
     - **Stage 2 (`S2_macos_usb_transport_guard`)**: Exercises macOS 26+ `IOUSBHost` `0xe00002be` quiescence (`>= 350 ms`) & bounded exponential backoff (`50/100/200/400/800 ms`), Vendor Control `(0x43, 1, 0x37FF, 0xD7AA)`, USB STALL non-retransmit rule, Senser v1 7-round auth (`054C:0DA1 -> 054C:0336`), Senser v2 RSA fail-closed rejection, and read-only Jiritsu (`0x40 / 0x1001`) firewalling via `fx3_recovery.macos_usb_transport_guard` (with clean decoupled fallback when `fx3_recovery` is absent from `sys.path`).
     - **Stage 3 (`S3_runtime_antibrick_audit`)**: Enforces all 4 2026 runtime anti-brick vectors (`/etc/ld.so.preload` dynamic BusyBox ban + Clear-Before-Exec, Sony BusyBox `dd` truncation ban + 5-step atomic contract, `nflasha10` `12 MiB` `0x10000009` headroom `>= 2 MiB`, and `CAMSET`/`BK4\0` `PRODUCT_MODEL` `ALCIN_UUD` enum `4` NVRAM lock).
     - **Stage 4 (`S4_brick_classifier_v2_matrix`)**: Verifies all 6 symptom paths (`5L+6S`, `7L+7S`, `6L+9S` `WF-12` Sony Notice `00342260`, `13S` `0x100D`, `0x10000009`, and `ld_so_preload_deadlock`) plus wireless fault isolation readiness.
     - **Stage 5 (`S5_v702_p1_autolocator_rollback`)**: Exercises shifted-VMA `v7.02` `p1` 4-site autolocation and byte-exact rollback restoration via `fx3_recovery.p1_symbol_autolocator` (with optional `--unicorn` emulation and clean decoupled fallback).
     - **Stage 6 (`S6_preflight_12_gate_audit`)**: Evaluates all 12 safety gates via `preflight.evaluate_12_safety_gates(...)`, verifying `persistent_write_release == False` and deterministic Gate `G12` blocking on any injected stage fault.

2. **`outputs/fx3-safety/fx3_safety/preflight.py` (Gate `G12` Upgrade — 100% Backward Compatible)**
   - Added `wireless_fault_isolation_ok: Optional[bool] = None`, `runtime_antibrick_ok: Optional[bool] = None`, and `multiport_tier3_harness_ok: Optional[bool] = None` to `evaluate_12_safety_gates(...)`.
   - `None` preserves existing behavior (`fx6-on-fx3-closure` compatibility untouched); `False` deterministically blocks Gate `G12` with:
     - `BLOCKED_BY_WIRELESS_FAULT_ISOLATION_REDLINE`
     - `BLOCKED_BY_RUNTIME_ANTIBRICK_REDLINE`
     - `BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE`

3. **Package Exports & Documentation**
   - Updated [`outputs/fx3-safety/fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py) and [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) with clean `__all__` exports.
   - Updated [`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md) and [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md).
   - Modernized [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](../../docs/STAGE-A-HARDWARE-RUNBOOK.md) (bilingual EN + 简体中文) with Pre-H0 6-stage rehearsal invocation and dedicated Sections 4–7 for Multi-Port `RP2040-Zero` (`-DOPEN_DRAIN`) Tier-3 safety, macOS 26+ `IOUSBHost` `0xe00002be` connection procedure, Sony Notice `00342260` `WF-12` cold-boot Airplane isolation, and 2026 forbidden operations.

4. **Tests (`27` New Tests Added)**
   - [`outputs/fx3-safety/tests/test_h0_hardware_rehearsal.py`](../../outputs/fx3-safety/tests/test_h0_hardware_rehearsal.py): **24** unit & fault-injection tests covering happy path, decoupled fallback, `FX3_FX6_FORCE_CLEAN_ROOM=1`, CLI JSON output, and fault injection across Stages 1–6.
   - [`outputs/fx3-safety/tests/test_safety.py`](../../outputs/fx3-safety/tests/test_safety.py): **3** tests covering Gate `G12` backward compatibility, Phase 28 redline blocking, and public package exports.

---

## 2. Verification Results

All Python checks were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B`:

| Suite / Command | Mode | Result | Duration |
| :--- | :--- | :---: | :---: |
| `outputs/fx3-safety/tests` (`PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter`) | Normal | `92` tests (`OK`, 0 skipped) | `< 0.2s` |
| `outputs/fx3-safety/tests` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | Clean-Room | `92` tests (`OK`, `skipped=1` external donor) | `< 0.2s` |
| `outputs/fx3-recovery-adapter/tests` (`PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter`) | Normal | `109` tests (`OK`, `skipped=1` external donor) | `~29.6s` |
| `outputs/fx3-recovery-adapter/tests` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | Clean-Room | `51` tests (`OK`, `skipped=7` external donor) | `< 0.1s` |
| `outputs/fx6-on-fx3-closure/tests` (backward-compatibility check) | Normal | `171` tests (`OK`) | `~242s` |
| `python3 -B -m fx3_safety.h0_hardware_rehearsal --unicorn` | CLI Smoke | Exit `0`, `all_passed=True`, `persistent_write_release=False` | `< 0.2s` |
| `make clean-audit` | Cleanliness | Clean-room audit passed (`0` residue binaries/pyc) | `< 1s` |
