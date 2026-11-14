# Phase 38 Executable CrSDK PTP2, 24-Pin MI-Shoe, Multi-Port LTC & CXD90057 SPACC AES-XTS-256 Safety Guard

> **Date**: `2026-11-14` · **Worker**: `Hydrogen-30` · **Branch**: `codex/h30-phase38-mishoe-ltc-crsdk-guard`  
> **Upstream Dossier**: [`reports/2026-11-14-global-sony-ptp-mishoe-rtmd-spacc-intel/README.md`](../2026-11-14-global-sony-ptp-mishoe-rtmd-spacc-intel/README.md) & [`protocol_alignment_matrix.json`](../2026-11-14-global-sony-ptp-mishoe-rtmd-spacc-intel/protocol_alignment_matrix.json)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False` (hard-locked)

---

## 1. Executive Summary

Phase 38 operationalizes the four hardware and protocol findings from the Wave-2 global intelligence dossier into fast, deterministic, fail-closed executable safety verifiers in [`outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py):

| Domain | Verifier Entrypoint | Key Hazards Blocked |
| :--- | :--- | :--- |
| **1. Multi-Port 15-Pin `VMC-BNCM1` LTC vs `uart_boot`** | [`verify_multiport_ltc_vs_uart_boot`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py) | Simultaneous `VMC-BNCM1` + `RP2040-Zero` attachment, `2Vpp-5Vpp` SMPTE LTC injection onto `CXD90057` `1.8V/3.15V` UART (`Pin 7/8/9`), DC-coupled `> 3.15V` / `> 5.0Vpp` overvoltage, `100 kOhm` LANC vs `680 kOhm` LTC ID-resistor mismatch, and FX3 TC OUT requests (validating unidirectional `EXT-LK` LTC IN fallback with `P11` `0x92d2091c`). |
| **2. 24-Pin MI-Shoe Digital Audio (`XLR-H1`/`ECM-B1M`) & `P11` `0x91db059b`** | [`verify_mishoe_digital_audio_and_p11_coexistence`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py) | Invalid 6-bin `ID1..ID3` resistor ladder values, `UNREG > 1.6A` / `LOGIC_VDD` out-of-range rails, invalid I2S PCM framing (`48kHz / 24-bit 4ch` `CH1..CH4` for `XLR-H1`), `libInfraHotshoe.so` (`0x5d90`) `E_TMO = -50 -> 0x8000` hangs, and `P11` `0x91db059b` spoofed attached ACK (`0x88000001`) suppressing `XLR-H1`. |
| **3. Sony `CrSDK` PTP2 (`0x9201..0x9209`) Remote Control Firewall** | [`audit_crsdk_ptp2_session`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py), [`classify_crsdk_ptp2_request`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py) | Non-Sony Vendor Extension / `0x920a..0x920f` Nikon opcode collisions, incomplete/out-of-order `0x9201` `SDIOConnect` `(1,0,0)->(2,0,0)->(3,0,0)`, `0x12c` (`3_00`) regression without `0xc8` (`2_00`) fallback, firmware updates/`FormatMedia`/`CAMSET`, `PRODUCT_MODEL` (`ALCIN_UUD`) NVRAM tampering, and raw service-mode escalation (`054C:0336`/`SET_FILE_PATH`/`AdjustControl`), while permitting safe live-shooting writes (`ExposureIndex`, `ShutterAngle`, `WhiteBalance`, `LogShootingMode`, `MovieRec`). |
| **4. `CXD90057` `SPACC` (`0xf7fc0000`) `AES-XTS-256` Block-Layer Guard** | [`audit_spacc_block_layer`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py) | Raw `/dev/nflasha*` mounts or plaintext reads on `AES-XTS-256` (`type=5, flag&1`) partitions, `/dev/cnflasha*` access on plaintext/WBI partitions, mixed `nflasha*`/`cnflasha*` session reads/comparisons, and userland `SPACC` MMIO (`0xf7fc0000..0xf7fcffff`) access — all deterministically blocked with `BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH`. |

---

## 2. Deliverables

1. [`outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py) — Four executable hardware/protocol guards, unified [`evaluate_phase38_safety_guards`](../../outputs/fx3-safety/fx3_safety/crsdk_mishoe_ltc_spacc_guard.py), and CLI `--self-check --json`.
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py) — Exports all Phase 38 classes, constants, and functions in `__all__`.
3. [`outputs/fx3-safety/tests/test_crsdk_mishoe_ltc_spacc_guard.py`](../../outputs/fx3-safety/tests/test_crsdk_mishoe_ltc_spacc_guard.py) — **28 deterministic unit tests** pushing `outputs/fx3-safety/tests` from 116 to **144 tests**.
4. [`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md) — Updated package documentation with Section 5.
5. [`reports/2026-11-14-phase38-crsdk-mishoe-ltc-spacc-guard/README.md`](README.md) — This report.

---

## 3. Verification Commands & Observed Results

- **Normal mode** (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`):
  - **144 tests** ran in **0.113s** — `OK (skipped=1)` (existing optional Unicorn test; all 28 new Phase 38 tests passed).
- **Clean-room mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests`):
  - **144 tests** ran in **0.114s** — `OK (skipped=1)`.
- **CLI self-check** (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety.crsdk_mishoe_ltc_spacc_guard --self-check --json`):
  - Exited `0`, emitting JSON with `status = "VERIFIED_SAFE"`, `persistent_emmc_writes_authorized = false`, `persistent_write_release = false`.
- **Clean-room hygiene audit** (`make clean-audit`):
  - `ALL GREEN` (`0.03s`).
