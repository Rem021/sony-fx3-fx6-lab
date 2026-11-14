# Phase 44 — FX3 Fan PWM Thermal Envelope, `NP-FZ100` (`7.2V`) vs `BP-U` (`14.4V`) Battery Brownout Firewall & USB-PD Stability Verifier

> **Date**: `2026-11-14` · **Worker**: `Hydrogen-36` · **Branch**: `codex/h36-phase44-safety-thermal-power-usbpd-guard`  
> **Primary Module**: [`outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False` (hard-locked)

---

## 1. Executive Summary

Phase 44 closes the cross-body **thermal cooling** and **battery / USB-PD power-domain** hazards between **Sony ILME-FX6 (`v6.01`, `14.4V` 4S `BP-U` / `19.5V` DC-IN + large chassis blower)** and **Sony ILME-FX3 (`v7.02`, `7.2V` 2S `NP-FZ100` + `9V/3A` `27W` USB-PD + compact internal fan)** inside [`outputs/fx3-safety/`](../../outputs/fx3-safety/README.md).

| Deliverable | Entrypoint | Core Invariants & Evidence |
| :--- | :--- | :--- |
| **1. `O_RDONLY` Donor Thermal/Fan/Power Audit** | [`audit_donor_thermal_fan_power_contracts`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py) | Audits FX3 `v7.02` & FX6 `v6.01` `libfan.so`, `libBusPower.so`, `libUsbBusPower.so`, `FX3-CX95900_ALLLANG-Backup.bin` / `CX95898_NTSC.bin` (`0x0238000a..0x0238006d` `g_bkup_dev_temp_bkid_list`), `appFw.so`, and `cpapp-b.bin` strictly via `os.O_RDONLY` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` pinned fallback. |
| **2. FX3 Compact Fan PWM Thermal Runaway Guard** | [`verify_fan_thermal_envelope`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py), [`evaluate_fan_mode_matrix`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py) | Verifies Stage-A/B `libfan.so` `@ 0x1dec` (`_Z19fan_i_bkup_is_validv` -> `mov w0, #1; ret`) + Stock FX3 CP thermal loop across all 4 menu modes (`AUTO1`, `AUTO2`, `MINIMUM`, `OFF_IN_REC`), enforcing mandatory active cooling override (`>= 62.0°C` SoC or `>= 68.0°C` CFexpress slot A/B), soft recording warning (`>= 82.0°C`), and fail-closed graceful unmount & RAM-overlay teardown (`>= 90.0°C`). |
| **3. `NP-FZ100` vs `BP-U` & USB-PD `9V/3A` Firewall** | [`normalize_npfz100_infolithium_mv`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py), [`verify_battery_and_usbpd_firewall`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py) | Proves `NP-FZ100` (`6200..8400 mV`) is normalized via InfoLITHIUM SOC (`%` + `remaining_minutes`) rather than raw `4S BP-U` `11500 mV` emergency-cutoff comparators (preventing false `0%` `OFF_BY_BATT_END` boot shutdown), and enforces `>= 80%` (`>= 7800 mV`) + stable USB-PD `9V/3A` (`>= 27W`, VBUS droop `<= 450 mV`) for `H0`/`H1` rehearsals. |
| **4. CLI & Dual-Mode Unit Tests** | [`fx3_safety/__main__.py`](../../outputs/fx3-safety/fx3_safety/__main__.py), [`test_thermal_pwm_and_power_guard.py`](../../outputs/fx3-safety/tests/test_thermal_pwm_and_power_guard.py) | Wires `verify-thermal-power-guard [--clean-room] [--json]`, exports all public symbols in [`fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py), keeps all 144 existing tests green, and adds **30 fast unit tests** (`0.018s`). |

---

## 2. Read-Only (`O_RDONLY`) Donor Findings: FX3 `v7.02` vs FX6 `v6.01`

### 2.1 Binary & Digest Inventory

| Artifact | Body | Size (Bytes) | SHA-256 Digest | Verified Contracts / Symbols |
| :--- | :---: | ---: | :--- | :--- |
| `libfan.so` | FX3 `7.02` | `27,280` | `c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv` (`0x1ec0`: `fd7bbea920008052`), `g_bkup_dev_temp_bkid_list` (`100` IDs `0x0238000a..0x0238006d`) |
| `libfan.so` | FX6 `6.01` | `31,176` | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | `fan_infra_init` (`0x1c80`), `_Z19fan_i_bkup_is_validv` (`0x1dec`: `fd7bbda920018052` -> Stage-A/B `20008052c0035fd6` `mov w0, #1; ret`), `g_bkup_dev_temp_bkid_list` (`0x170e8`) |
| `libBusPower.so` | FX3 `7.02` | `43,968` | `4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e` | `SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState`, `NotifyUSBPowerSupplyState` |
| `libBusPower.so` | FX6 `6.01` | `43,968` | `d4f2ffe4e74786b66b64ca4eec05b0d433ff0157326156a486d7afec742d00b8` | `SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState`, `NotifyUSBPowerSupplyState` |
| `libUsbBusPower.so` | FX3 `7.02` | `48,232` | `c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748` | `IsVbusReady`, `GetCurrentBattState`, `SetPowerContractStatus`, `CheckSupplySetting`, `GetCurrentLimit` |
| `libUsbBusPower.so` | FX6 `6.01` | `48,232` | `4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71` | `IsVbusReady`, `GetCurrentBattState`, `SetPowerContractStatus`, `CheckSupplySetting`, `GetCurrentLimit` |
| `FX3-CX95900_ALLLANG-Backup.bin` | FX3 `7.02` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | BK4 `0x02380007..0x02380009` = `40 / 55 / 82` (`0x52 = 82°C` thermal threshold), `0x02380013=0x02` |
| `CX95898_NTSC.bin` | FX6 `6.01` | `2,253,333` | `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e` | BK4 `0x02380007..0x02380009` = `49 / 54 / 76`, `0x02380013=0x00` |
| `appFw.so` | FX3 `7.02` | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `FAN_CONTROL_AUTO/MINIMUM/OFF_IN_REC/ALWAYS_OFF`, `AUTO1`/`AUTO2`, `OFF_BY_IM_THERMAL`, `OFF_BY_MEDIA_THERMAL`, `OFF_BY_BATT_END_FAKE` |
| `appFw.so` | FX6 `6.01` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_FAN_CONTROL`, `MEDIA_ANOMALY_TEMP_HIGH_SLOT1_HIGH`/`SLOT2_HIGH`, `OFF_BY_BATT_LOW`, `convert_MODE_ID_INFOBATT_END_VALUE` |
| `cpapp-b.bin` | FX3 `7.02` | `15,980,568` | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` | `FAN_EQ_ID`, `BATT_AUTH_S`, `BATT_STATE1_S..3_S`, `BATT_TYPE1_S..2_S`, `THERMISTOR_ADJ_*` |
| `cpapp-b.bin` | FX6 `6.01` | `17,952,816` | `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668` | `FAN_EQ_ID`, `THERMAL_SENSOR`, `BATT_AUTH_S`, `BATT_STATE1_S..3_S`, `BATT_TYPE1_S..2_S` |

---

## 3. Fan PWM Envelope & `NP-FZ100` / USB-PD Firewall Contracts

### 3.1 FX3 Compact Fan PWM Safety Envelope

| Thermal Condition | `AUTO1` | `AUTO2` | `MINIMUM` | `OFF_IN_REC` | Guard Disposition |
| :--- | :---: | :---: | :---: | :---: | :--- |
| Nominal (`<= 45°C`) | `30%` PWM | `20%` PWM | `25%` PWM | `0%` PWM | `VERIFIED_SAFE` |
| `CXD90057` SoC `>= 62.0°C` | Active ramp | Active ramp | Active ramp | **Override `>= 65%` (`AUTO1_THERMAL_OVERRIDE`)** | `VERIFIED_SAFE` (blocks if override disabled -> `BLOCKED_FAN_MODE_UNSAFE`) |
| CFexpress Slot A/B `>= 68.0°C` | Active ramp | Active ramp | Active ramp | **Override `>= 65%` (`AUTO1_THERMAL_OVERRIDE`)** | `VERIFIED_SAFE` (blocks if override disabled -> `BLOCKED_FAN_MODE_UNSAFE`) |
| Any Zone `>= 82.0°C` (`< 90°C`) | `100%` PWM | `100%` PWM | `100%` PWM | `100%` PWM (`AUTO1_THERMAL_OVERRIDE`) | `THERMAL_SOFT_WARNING` (`recording_warning = True`) |
| Any Zone `>= 90.0°C` | `100%` PWM | `100%` PWM | `100%` PWM | `100%` PWM | `BLOCKED_THERMAL_RUNAWAY` (`graceful_unmount_required = True`, `ram_overlay_teardown_required = True`, `abort_required = True`) |
| `FAN_CONTROL_ALWAYS_OFF` / Broken Fan | Blocked | Blocked | Blocked | Blocked | `BLOCKED_FAN_MODE_UNSAFE` / `BLOCKED_FAN_CONTROLLER_FAULT` |

### 3.2 `NP-FZ100` (`7.2V`) vs `BP-U` (`14.4V`) & USB-PD `9V/3A` Firewall

- **False `0%` Boot Shutdown Firewall**: Raw `NP-FZ100` (`6200..8400 mV`) falls strictly below `4S BP-U` `11500 mV` emergency-cutoff comparators. [`normalize_npfz100_infolithium_mv`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py) and [`verify_battery_and_usbpd_firewall`](../../outputs/fx3-safety/fx3_safety/thermal_pwm_and_power_guard.py) enforce `INFOLITHIUM_SOC` normalization and block `RAW_BPU_11500MV_COMPARATOR`, `RAW_19V5_DC_IN_COMPARATOR`, or `BP-U` chemistry with `BLOCKED_BATT_COMPARATOR_MISMATCH`.
- **`H0`/`H1` Rehearsal Gate**: Requires `NP-FZ100` `>= 80%` SOC, `>= 7800 mV`, `>= 20` remaining minutes, AND active USB-PD `9V/3A` (`>= 27W` contract) with VBUS droop `<= 450 mV` (`>= 8550 mV` measured under load).
- **Hard-Locked Safety Policy**: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`.

---

## 4. Verification Commands & Results

- **Local Donor Mode (`outputs/fx3-safety/tests`)**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests`
  - **174 tests** ran in **0.162s** — `OK` (30 new Phase 44 tests in `0.018s`).
- **Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
  - `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests`
  - **174 tests** ran in **0.153s** — `OK (skipped=1)` (existing optional Unicorn test).
- **CLI Entrypoint**:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-thermal-power-guard` -> `exit 0` (`mode=LOCAL_DONOR_O_RDONLY`, `status=VERIFIED_SAFE`, `persistent_emmc_writes_authorized=False`).
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-thermal-power-guard --clean-room --json` -> `exit 0` (`verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=true`).
- **Full Repository Verification & Hygiene**:
  - `make clean-audit` (`ALL GREEN`) and `make test` (`ALL PASSED`).
