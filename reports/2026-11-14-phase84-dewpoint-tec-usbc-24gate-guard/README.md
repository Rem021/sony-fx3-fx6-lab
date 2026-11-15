# Phase 84 — Sub-Dewpoint Peltier TEC Condensation Firewall, PMIC `5V` Accessory Current-Budget / USB-C Strain Guard & `G01..G24` 24-Gate Preflight

- **Date**: 2026-11-14
- **Branch**: `h81-phase84-safety-dewpoint-tec-usbc-24gates`
- **Target Package**: `outputs/fx3-safety/fx3_safety/`
- **New Module**: [`dewpoint_tec_usbc_and_24gate_guard.py`](../../outputs/fx3-safety/fx3_safety/dewpoint_tec_usbc_and_24gate_guard.py)
- **Redlines Preserved**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `preflight.py` / `master_16gate_preflight.py` / `usblan_ptpip_and_18gate_preflight.py` / `rig_groundloop_lensrail_and_20gate_guard.py` / `phantom48v_gimbal_and_22gate_guard.py` unmodified.

---

## 1. Engineering Deliverables Implemented

### 1.1 Read-Only (`os.O_RDONLY`) Compact Donor Audit (`audit_phase84_donor_contracts`)
Inspects 5 compact (`198,888 B` total) FX3 `v7.02` & FX6 `v6.01` ELF donor libraries strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room synthesis under `FX3_FX6_FORCE_CLEAN_ROOM=1`:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Export / Token |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_libfan` | FX3 | `libfan.so` | `27,280` | `c607fc8d3ea3b46e...` | `fan_infra_init` |
| `fx6_libfan` | FX6 | `libfan.so` | `31,176` | `d4f01ff36a2d3d45...` | `_Z19fan_i_bkup_is_validv` |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt` |
| `fx3_lib_usb_bus_power` | FX3 | `libUsbBusPower.so` | `48,232` | `c606880c92ecf602...` | `_ZN11UsbBusPower15GetCurrentLimitEv` |
| `fx6_lib_usb_bus_power` | FX6 | `libUsbBusPower.so` | `48,232` | `4215a9e989d25896...` | `_ZN11UsbBusPower15GetCurrentLimitEv` |

### 1.2 Magnus-Tetens Dew-Point Condensation & External Peltier (`TEC`) Cooler Short-Circuit Firewall (`Gate G23`)
- Computes exact psychrometric dew point $T_{dp}(T_{amb}, RH\%)$ via the Magnus-Tetens formula ($a = 17.625$, $b = 243.04^\circ\text{C}$).
- **Sub-Dewpoint Peltier (`TEC`) Condensation Block (`BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD`)**: Blocks unregulated or unmonitored external Peltier semiconductor backplate coolers whenever `tec_cold_plate_c < dew_point_c + 2.0` (e.g., `30°C / 75% RH` $\rightarrow T_{dp} = 25.08^\circ\text{C}$, blocking `10°C` Peltier coolers that condense liquid water onto the FX3 magnesium rear chassis and LCD hinge flex). Permits PID-regulated dry-air operation when `tec_cold_plate_c >= dew_point_c + 2.0`.
- **Cold-to-Warm Unbagged Thermal Shock Block (`BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK`)**: Blocks moving a `-5°C` outdoor camera directly into a `+26°C / 65% RH` indoor room without a sealed acclimation bag until `body_temp_c >= dew_point_c + 2.0`.
- **Internal Centrifugal Fan Immunity Proof**: Proves FX3's internal `libfan.so` centrifugal Sigma-shaped blower (`cooling_method == "internal_centrifugal_air"`) never cools the chassis below ambient dew point ($T_{chassis} \ge T_{amb} > T_{dp} \rightarrow 0\%$ condensation risk).

### 1.3 PMIC `5V` Accessory Current-Budget, Non-Compliant USB-C PD Cable Droop & Cage Strain-Relief Guard (`Gate G24`)
- Models simultaneous `5V` rail current draw across:
  - `24-pin MI-Shoe` (`XLR-H1` digital ADC + dual `+48V` phantom boost under `10 mA` dual condenser load = `300.0 mA`),
  - `HDMI Type-A Pin-18 +5V` (`<= 55.0 mA` active optical HDMI / EDID EEPROM),
  - `USB-C VBUS` host-mode (`RTL8153` `380.0 mA` / `AX88179` `400.0 mA` / `USB-C SSD` `750.0 mA`),
  - `Multi-Port` accessory logic draw (`40.0 mA`).
- **Fail-Closed PMIC Budget (`BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET`)**: Blocks whenever combined `5V` accessory draw exceeds `900.0 mA` without an external powered USB-C PD hub (`external_powered_usbc_pd_hub = True` offloads USB-C VBUS draw from the FX3 PMIC).
- **USB-C Cable IR Droop & Strain-Relief Guards**: Blocks high-resistance / un-E-marked `>2m` USB-C cables (`cable_ir_drop_v > 0.65V` at `3.0A` -> `BLOCKED_USBC_PD_CABLE_IR_DROOP`) and unclamped heavy USB-C/HDMI cables in handheld/gimbal rigs (`require_cage_cable_clamp == True` -> `BLOCKED_UNCLAMPED_USBC_HDMI_STRAIN_HAZARD`).

### 1.4 24-Gate Master Safety Preflight (`G01..G24`) & CLI `verify-24-gates`
- **`evaluate_24gate_preflight(...)`** composes `evaluate_22gate_preflight` (`G01..G22`) with `G23` (`psychrometric_dewpoint_and_tec_condensation_safe`) and `G24` (`pmic_5v_accessory_budget_and_usbc_strain_safe`):
  - **Offline default (`dry_run_simulated_backup=False`)**: `21/24` gates pass; `G10..G12` truthfully report `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` (`overall_ready_for_hardware_attach = False`).
  - **Dry-run rehearsal (`--dry-run-simulated-backup`)**: `24/24` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts

| Command | Mode | Result | Duration |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_dewpoint_tec_usbc_and_24gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `34/34` passed (`OK`) | `0.189s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_dewpoint_tec_usbc_and_24gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `34/34` passed (`OK`) | `0.185s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `360/360` passed (`OK`) | `<0.9s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `360` run, `359` passed, `1` skipped (`OK`) | `<0.9s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` | `<0.1s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-24-gates` | CLI Offline Default | `status=VERIFIED_21_OF_24_AWAITING_PHYSICAL_TIER0`, `verified=21/24`, `persistent_emmc_writes_authorized=False` | `<0.1s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-24-gates --clean-room --dry-run-simulated-backup` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_24_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=24/24`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.1s` |

---

## 3. Owned Files Touched
1. `outputs/fx3-safety/fx3_safety/dewpoint_tec_usbc_and_24gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_dewpoint_tec_usbc_and_24gate_guard.py`
6. `reports/2026-11-14-phase84-dewpoint-tec-usbc-24gate-guard/README.md`
