# Phase 69 — Rig D-Tap/HDMI Ground-Loop Interlock, E-Mount Hot-Detach Rail Guard, Power-Loss `.RSV` Salvage & `G01..G20` 20-Gate Preflight

- **Date**: 2026-11-14
- **Branch**: `codex/h63-phase69-safety-rig-groundloop-20gates`
- **Target Package**: `outputs/fx3-safety/fx3_safety/`
- **New Module**: [`rig_groundloop_lensrail_and_20gate_guard.py`](../../outputs/fx3-safety/fx3_safety/rig_groundloop_lensrail_and_20gate_guard.py)
- **Redlines Preserved**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `preflight.py` / `master_16gate_preflight.py` / `usblan_ptpip_and_18gate_preflight.py` unmodified.

---

## 1. Engineering Deliverables Implemented

### 1.1 Read-Only (`os.O_RDONLY`) Compact Donor Audit (`audit_rig_20gate_donor_contracts`)
Inspects 6 compact (`589,304 B` total) FX3 `v7.02` & FX6 `v6.01` ELF donor libraries strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room synthesis under `FX3_FX6_FORCE_CLEAN_ROOM=1`:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Export / Token |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_libinfra_lens_comm` | FX3 | `libInfraLensCommunicator.so` | `14,544` | `e61bf145f050dd03...` | `_ZN16LensCommunicator18GetMountedLensInfoEPv` |
| `fx6_libinfra_lens_comm` | FX6 | `libInfraLensCommunicator.so` | `14,544` | `8848b33084f71856...` | `_ZN16LensCommunicator10SndSyncMsgEPvj` |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt` |
| `fx3_lib_usb_bus_power` | FX3 | `libUsbBusPower.so` | `48,232` | `c606880c92ecf602...` | `_ZN11UsbBusPower11IsVbusReadyEv` |
| `fx3_libinfra_media_mount` | FX3 | `libInfraMediaMount.so` | `65,392` | `33b4c61c39f724e0...` | `_ZN15InfraMediaMount10GetVersionEv` |
| `fx3_libinfra_media_common` | FX3 | `libInfraMediaCommon.so` | `402,624` | `1ddec7e4d903eaca...` | `mcmn_drv_default_unmount` |

### 1.2 D-Tap / HDMI Type-A Ground-Loop & Hot-Plug ESD Firewall (`Gate G19`)
- **Open-Negative Ground-Return Fault Detection**: Blocks rigs where `monitor` or camera `dummy coupler` D-Tap `GND` disconnects while `+14.8V` remains hot with copper HDMI plugged in (`open_negative_ground_return_fault = True`, `hdmi_pin17_shield_return_hazard = True`, `cxd90057_esd_array_at_risk = True` $\rightarrow$ `BLOCKED_GROUND_LOOP_HAZARD`).
- **Rig Topology Enforcement**: Permits `INTERNAL_NP_FZ100_ISOLATED_USBPD` (+ dedicated monitor battery), `OPTICAL_FIBER` HDMI exemption, `ISOLATED_DCDC_BOX`, or shared D-Tap with `ground_first_locking_connector=True` (emitting warning); blocks shared unisolated D-Tap + copper HDMI without ground-first locking connector.
- **Sequencing State Machine (`verify_rig_power_sequence`)**: Enforces `CONNECT_POWER_CABLES -> CONNECT_HDMI -> POWER_ON_CAMERA -> POWER_ON_MONITOR` and strictly reversed teardown `POWER_OFF_MONITOR -> POWER_OFF_CAMERA -> DISCONNECT_HDMI -> DISCONNECT_POWER_CABLES`; blocks hot-plugging HDMI while powered.
- **HDMI `+5V` Pin-18 Back-Feed Guard**: Hard-blocks `> 5.25V`, `> 55 mA`, or `hdmi_pin18_reverse_backfeed=True` (`BLOCKED_HDMI_PIN18_BACKFEED`).

### 1.3 E-Mount `V_LENS` (`3.3V` / `5.0V`) Hot-Detach Crowbar & Stock-CP IBIS Park (`Gate G19`)
- Models all 10 Sony E-Mount bayonet pins (`1:GND`, `2:V_LENS_LOGIC_3V3`, `3:V_LENS_SERVO_5V0`, `4..8:SPI/BUSY`, `9:LENS_DET`, `10:DGND`).
- Enforces `LENS_DET` first-break interrupt $\rightarrow$ `V_LENS_SERVO_5V0` crowbar to `0.0 mA` within `<= 2.0 ms` (well ahead of the `3.5 ms` rotary contact-wipe window) and `V_LENS_LOGIC_3V3` tri-state isolation.
- Verifies Stock-CP `0x0400` (`0x1400` completion, `LiroSeq: Restore.`) IBIS Center-Lock park with `cp_mutation_bytes == 0`.

### 1.4 Sudden Power-Loss `.RSV` Clip-Salvage & `USB-PD` Battery-Less Trap Guard (`Gate G20`)
- **`USB-PD 9V/3A` Unplug During `4K 60p XAVC S-I` (`600 Mbps`)**:
  - With `NP-FZ100` reserve (`soc_pct >= 15%` and `>= 6.8V` under load): verifies `0` lost frames and clean `moov`/`MXF FooterPartition` close.
  - Battery-less (`battery_less_usb_pd=True`) or `soc_pct < 15%` (`< 10%` critical) or `< 6.8V` under load: fails closed with `BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT`.
- **Read-Only `.RSV` Emergency Salvage Inspector (`inspect_sony_rsv_salvage_structure`)**: Parses ISO-BMFF (`ftyp` + `mdat` without `moov`, brands `XAVC`/`mp42`/`isom`/`MSNV`) and MXF KLV header partitions (`060e2b34...`) strictly read-only (`physical_media_writes == 0`, `persistent_emmc_writes_authorized == False`).

### 1.5 20-Gate Master Safety Preflight (`G01..G20`) & CLI `verify-20-gates`
- **`evaluate_20gate_preflight(...)`** composes `evaluate_18_master_safety_gates` (`G01..G18`) with `G19` (`rig_hdmi_dtap_groundloop_and_lensrail_safe`) and `G20` (`power_failover_ups_and_rsv_salvage_safe`):
  - **Offline default (`dry_run_simulated_backup=False`)**: `17/20` gates pass; `G10..G12` truthfully report `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` (`overall_ready_for_hardware_attach = False`).
  - **Dry-run rehearsal (`--dry-run-simulated-backup`)**: `20/20` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts

| Command | Mode | Result | Duration |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_rig_groundloop_lensrail_and_20gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `32/32` passed (`OK`) | `0.101s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_rig_groundloop_lensrail_and_20gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `32/32` passed (`OK`) | `0.101s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `292/292` passed (`OK`) | `0.528s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `292` run, `291` passed, `1` skipped (`OK`) | `0.514s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` | `0.03s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-20-gates` | CLI Offline Default | `status=VERIFIED_17_OF_20_AWAITING_PHYSICAL_TIER0`, `verified=17/20`, `persistent_emmc_writes_authorized=False` | `<0.1s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-20-gates --clean-room --dry-run-simulated-backup` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_20_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=20/20`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.1s` |

---

## 3. Owned Files Touched
1. `outputs/fx3-safety/fx3_safety/rig_groundloop_lensrail_and_20gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_rig_groundloop_lensrail_and_20gate_guard.py`
6. `reports/2026-11-14-phase69-rig-groundloop-lensrail-20gate-guard/README.md`
