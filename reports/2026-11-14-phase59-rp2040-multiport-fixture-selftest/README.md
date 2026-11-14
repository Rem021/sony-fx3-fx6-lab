# Phase 59 — Camera-Disconnected `RP2040-Zero` `-DOPEN_DRAIN` `1.8V` Multi-Port Bench Fixture Self-Test, `48000`-Baud PIO Divider & Ohmmeter Pre-Plug Verifier

> **Date**: `2026-11-14` · **Worker**: `Hydrogen-52`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `CAMERA_ATTACHED_ALLOWED_FOR_BENCH_SELFTEST = False` (hard-locked)

---

## 1. Executive Summary

Phase 59 provides a deterministic, camera-disconnected bench self-test suite in [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md) so any operator assembling a Tier-3 Sony 15-pin Multi-Port UART / `CXD90057` BootROM recovery harness can verify electrical isolation, `1.8V` open-drain pull-up swing, `ID` resistor keying, RP2040 PIO fractional dividers, `-DOPEN_DRAIN=1` CMake flags, and `48000`/`115200`-baud TX↔RX loopback **before plugging into a physical FX3 camera body**:

| Deliverable | Entrypoints | Core Invariants & Failure Gates |
| :--- | :--- | :--- |
| **1. 15-Pin Multi-Port Ohmmeter & Electrical Pre-Plug Firewall** | [`audit_ohmmeter_isolation`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [`verify_open_drain_1v8_swing`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [`verify_multiport_id_keying`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py) | Requires `camera_connected == False` (`FAIL_CAMERA_CONNECTED_DURING_BENCH_TEST`) and `ltc_cable_connected == False`; enforces `R_isolation >= 1 MΩ` across `VBUS (5.0V)` / `3.3V` rails to `UART_TX`/`UART_RX`/`ID`/`XRESET`, `Pin 2` GND continuity `<= 2.0 Ω`, forbids Raspberry Pi Pico (`GP29` `VSYS/3` divider), checks `V_idle ∈ [1.71V, 1.89V]` (`> 1.98V` or push-pull → `FAIL_OVERVOLTAGE_HAZARD`), and enforces `Pin 6` `ID` keying (`BOOTROM_UART_BOOT`, `CONSOLE_READONLY`, vs blocked `VMC_BNCM1_LTC_ADAPTER` `680 kΩ` and `LANC_REMOTE` `100 kΩ`). |
| **2. RP2040-Zero PIO Divider, `pindirs` Program & CMake `-DOPEN_DRAIN=1` Auditor** | [`compute_pio_uart_clkdiv`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [`audit_pio_open_drain_program`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [`audit_cmake_open_drain_flags`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py) | Verifies RP2040 16.8 fractional PIO clock divider (`div = clk_sys / (8 * baud)`) for both `125 MHz` and `133 MHz` `clk_sys` at `48000` baud (`20.833 µs/bit`, `<= 0.0004%` error) and `115200` baud (`8.681 µs/bit`, `<= 0.0012%` error), rejecting integer-only truncation (`0.160% > 0.05%`), push-pull `out pins`/`set pins, 1` instructions, and missing/disabled `-DOPEN_DRAIN=1` CMake flags. |
| **3. 8x-Oversampled TX↔RX Bench Loopback & BootROM Echo Simulator** | [`simulate_uart_loopback_and_handshake`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py), [`run_rp2040_multiport_fixture_selftest`](../../outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py) | Bit-level 8N1 / 8E1 / 8O1 UART waveform encoder/decoder verifying start/data/parity/stop bits, start-bit glitch rejection, stop-bit framing-error rejection, stuck-low break / open-wire fault detection, and read-only `UB` CRC32 BootROM `HANDSHAKE_PING` + `MEM_READ` (`0xFFFF0000`) echo with `persistent_emmc_writes_authorized = False` hard-locked. |
| **4. CLI & Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_rp2040_multiport_fixture_selftest.py`](../../outputs/fx3-recovery-adapter/tests/test_rp2040_multiport_fixture_selftest.py) | Wires `verify-rp2040-fixture [--clean-room] [--json] [--out ...]`, exports all public symbols in `__init__.py`, preserves all 167 existing tests, and adds **30 fast dual-mode tests** (bringing `outputs/fx3-recovery-adapter/tests` to **197 tests**). |

---

## 2. RP2040-Zero PIO Fractional Clock Divider Matrix (`div = clk_sys / (8 * baud)`)

| `clk_sys` | Target Baud | Ideal `div` | RP2040 `INT + FRAC/256` | Actual Baud | Ideal Bit Period | Actual Bit Period | Error (`<= 0.05%`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `125 MHz` | `48,000` | `325.520833` | `325 + 133/256` (`325.519531`) | `48,000.192` | `20.833 µs` | `20.833 µs` | `0.00040%` |
| `125 MHz` | `115,200` | `135.633681` | `135 + 162/256` (`135.632812`) | `115,200.737` | `8.681 µs` | `8.681 µs` | `0.00064%` |
| `133 MHz` | `48,000` | `346.354167` | `346 + 91/256` (`346.355469`) | `47,999.820` | `20.833 µs` | `20.833 µs` | `0.00038%` |
| `133 MHz` | `115,200` | `144.314236` | `144 + 80/256` (`144.312500`) | `115,201.386` | `8.681 µs` | `8.680 µs` | `0.00120%` |

---

## 3. Verification Commands & Observed Results

- **Phase 59 Unit Tests (`test_rp2040_multiport_fixture_selftest.py`, 30 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **30 tests** ran in **0.146s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **30 tests** ran in **0.126s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode: **197 tests** (`167` existing + `30` new) (`OK`, `skipped=1` optional `capstone` check).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **139 tests** (`OK`, `skipped=8` donor-only classes in pre-existing suites; all 30 Phase 59 tests passed).
- **CLI Entrypoint Verification**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-rp2040-fixture` → `exit 0` (`status=VERIFIED_BENCH_FIXTURE mode=LOCAL_DONOR_O_RDONLY all_passed=True board=waveshare_rp2040_zero camera_connected=False persistent_emmc_writes_authorized=False`).
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-rp2040-fixture --clean-room --json` → `exit 0` (`verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=true`).
- **Repository Hygiene**:
  - `make clean-audit` (`ALL GREEN`) and clean `git status --porcelain`.
