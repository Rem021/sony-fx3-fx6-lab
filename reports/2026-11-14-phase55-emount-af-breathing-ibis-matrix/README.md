# Phase 55 Report — 10th Unified Firmware-Lab Auditor: Sony E-Mount Power Zoom (`PZ`), 627-Point Fast Hybrid PDAF, Focus Breathing Compensation (`UDAM`/`RTMD`) & 5-Axis `IBIS`/`OSS` Compatibility Matrix

- **Date**: `2026-11-14`
- **Target Package**: `outputs/fx3-firmware-lab/` ([`emount_af_breathing_and_ibis_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/emount_af_breathing_and_ibis_auditor.py))
- **Milestone**: **10th Unified Auditor** integrated into [`run_audit_all()`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-emount-af [--clean-room]`)
- **Dual-Mode Verification Status**:
  - **Local Donor (`os.O_RDONLY`)**: `LOCAL_DONOR_VERIFIED`, `all_checks_passed = true`, `14 / 14` donor artifacts verified, `report_sha256 = 6f53a1a9af091da5642d69ee3e8d5eb0164a3f62e378f34f8ef1f52f2ca29d30`
  - **Forced Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**: `CLEAN_ROOM_SYNTHETIC_VERIFIED`, `all_checks_passed = true`, `14 / 14` synthetic fixtures verified, `report_sha256 = d889c6f9bcff297b3a82c8b1d5b3a13cc11efe9eeed0fc7c07da806416fa3030`
  - **Unit Tests**: `213 / 213` total suite tests pass (`2.670s` Clean-Room, `7.917s` Local Donor; `28` new Phase 55 tests in [`test_emount_af_breathing_and_ibis.py`](../../outputs/fx3-firmware-lab/tests/test_emount_af_breathing_and_ibis.py))

---

## 1. Strictly `os.O_RDONLY` Donor Artifact Inventory (14 Binaries)

All local donor reads open files strictly via `os.O_RDONLY` without copying or mutating any proprietary binaries, and fall back deterministically to synthetic clean-room fixtures under `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or missing donor trees.

| Key | Body / FW | Artifact | Local Donor Size (B) | Role in Phase 55 Audit |
|---|---|---|---:|---|
| `fx3_appfw` | FX3 `v7.02` | `appFw.so` | `79,015,712` | Zoom (`T/W`), PDAF/Eye AF, Breathing Comp., `set_steadyshot_advanced_movie_i` |
| `fx6_appfw` | FX6 `v6.01` | `appFw.so` | `50,520,424` | Handle Zoom, Focus Map/AF markers, Breathing Comp., `PRM_is_imager_stabilization_unit_fixed` |
| `fx3_libmpr` | FX3 `v7.02` | `libmpr.so` | `3,517,008` | `KlvConverter::UDAMSetBreathingCorrectionValue`, `UDAMSetGyroscopeValue`, `UDAMSetAccelerometerValue` |
| `fx6_libmpr` | FX6 `v6.01` | `libmpr.so` | `28,921,824` | Shared UDAM serializers + 7 FX6 `BreathingCorrection_*` / `DistortionCorrection_*` metadata tags |
| `fx3_cpapp` | FX3 `v7.02` | `cpapp-b.bin` | `15,980,568` | Stock-CP (`cp_mutation_bytes == 0`), `36` Thumb-2 `MOVW #0x1400` sites, `LiroSeq: Restore.`, `HallPIDOUT_0`, `GyroPIDOUT_0` |
| `fx6_cpapp` | FX6 `v6.01` | `cpapp-b.bin` | `17,952,816` | Gyro-only (`Mount_DividedInfo_SteadyShotInfo`, `Gyro Data >>`), zero `steadyshot_body_axis` / `FWCP-isRetract` |
| `fx3_lens_comm` | FX3 `v7.02` | `libInfraLensCommunicator.so` | `14,544` | E-mount lens communicator ELF64 (`.text` SHA-256 `a1196fddd4a029c6...`) |
| `fx6_lens_comm` | FX6 `v6.01` | `libInfraLensCommunicator.so` | `14,544` | `0 B` loadable-segment diff vs FX3 (`6 B` non-loadable `.comment` diff only) |
| `fx6_hotshoe` | FX6 `v6.01` | `libInfraHotshoe.so` | `47,808` | Bounded MI-Shoe UIPC wait (`E_TMO = -50 -> 0x8000`) when Smart Grip is absent |
| `fx3_global_xdb` | FX3 `v7.02` | `global.xdb` | `11,664` | `uxa\x07` (`75786107`) UX resource registry |
| `fx6_global_xdb` | FX6 `v6.01` | `global.xdb` | `1,792` | `uxa\x07` (`75786107`) UX resource registry |
| `fx3_str_en` | FX3 `v7.02` | `string_english.uxc` | `165,740` | `Peaking Level`, `Peaking Color`, `SteadyShot`, `Focus Magnifier` labels |
| `fx6_str_en_1` | FX6 `v6.01` | `string_english.uxc` | `118,208` | `AF Transition Speed`, `AF Subj. Shift Sens.`, `Face/Eye Detection AF`, `Breathing Comp.`, `Focus Map`, fixed SS notice |
| `fx6_str_en_2` | FX6 `v6.01` | `string_english_2.uxc` | `118,676` | `SteadyShot: Active`, `SteadyShot: Standard`, `Zoom Speed`, `Handle Zoom Speed`, `Focus Magnifier ×4` |

---

## 2. Four-Pillar Lens, AF, Breathing & Stabilization Matrix

### Pillar A — E-Mount Servo/Power Zoom (`PZ`) & FX3 Body `T/W` Zoom Lever
- **Grip/Handle Zoom -> Shutter-Ring `T/W` Mapping (`P10` Keymap Safe)**:
  - Verified `SHARED_APPFW_ZOOM_MARKERS` (`13/13`), `FX3_APPFW_ZOOM_EXTRA_MARKERS` (`7/7`), `FX6_APPFW_HANDLE_ZOOM_MARKERS` (`10/10`), and Stock-CP `Parameter:us_zoom_speed` / `ezoom_mode`.
  - When FX6's Smart Grip/Handle is absent on FX3, `P11` queue `0x91db059b` emits `0x88000002` (detached) and `libInfraHotshoe.so` bounds `E_TMO = -50` to `0x8000`, falling back cleanly (`smart_grip_absent_crash_count == 0`) to FX3's physical shutter-ring `T/W` lever (`UIBIZ_KEY_TACT_ZOOM_TELE/WIDE` + `UIBIZ_KEY_VOL_ZOOM_AD`) across zoom speeds `1..8`.
- **Sony `SELP` Power Zoom & Clear Image Zoom (`CIZ`)**:
  - `LENS_POWER_ZOOM_SUPPORT` and `UIBIZ_KEY_LENS_ZOOM_LEVER/RING` drive Sony `SELP` lenses natively on both bodies, and `ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON` honors `1.5x` (`4K`) and `2.0x` (`FHD`) limits.

### Pillar B — 627-Point Fast Hybrid PDAF, Face/Eye AF, AF Transition (`1..7`) & Subj. Shift (`1..5`)
- **Wire Protocol Identity (`libInfraLensCommunicator.so`)**:
  - Pure-Python ELF64 section comparison proves `.dynsym`, `.plt`, `.text`, `.rodata`, and `.data` are **byte-identical** (`loadable_segment_diff_bytes == 0`, `.text` SHA-256 `a1196fddd4a029c634fc392fcb8509132a59b3fa457b0f49b33aa208af0dcfa1`) across FX3 `v7.02` and FX6 `v6.01`, differing only by `6 B` in `.comment` (`GCC: (Sony-FX)` build date).
- **AP<->Stock-CP (`U2`, `cp_mutation_bytes == 0`) AF Contract**:
  - Verified `627`-point IMX510 PDAF grid, `MOVIE_AF_TRANSITION_SPEED_1_SLOW..7_FAST`, `MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON..5_RESPONSICE` (Sony's exact binary token spelling), Face/Eye Priority & Only AF (`PID_SET_EYE_AF_MODE`), Touch Focus / Touch Tracking, Focus Magnifier (`x4.0` FX3 / `x3/x6` FX6 / `×4` ns=2), Peaking (`MSG_ID_INFRABB_VDF_SRVC_SET_PEAKING`), and Focus Map AP overlay.

### Pillar C — Focus Breathing Compensation (`UDAM` / `RTMD` Tables)
- **Breathing Comp. FOV Crop & Unsupported-Lens Gating**:
  - Verified `PID_SET_BREATHING_CORRECTION`, `BREATHING_CORRECTION_LENS_TYPE_SUPPORT/NOT_SUPPORT`, and Stock-CP `Mount_DividedInfo_BreathingCorrectionData` / `MakeDistortionCorrectionParam`.
  - Enabled mode computes bounded even-aligned cut-out crops (`1.01..1.18x`) and logs `7` `UDAM`/`RTMD` metadata tags (`BreathingCorrection_*`, `DistortionCorrection_*`); unsupported lenses reject activation fail-closed (`BREATHING_CORRECTION_LENS_TYPE_NOT_SUPPORT`).

### Pillar D — 5-Axis Body `IBIS` + Lens `OSS` & Factory Gyro Calibration Immutability
- **Cross-Body Hardware Asymmetry Proof**:
  - **FX6 `v6.01` `appFw.so`** contains `PRM_is_imager_stabilization_unit_fixed` (present on FX6, **absent** on FX3) and its `cpapp-b.bin` contains `Mount_DividedInfo_SteadyShotInfo` + `Gyro Data >> (yaw:%d, pit:%d, roll:%d)` with **zero** `steadyshot_body_axis`, `FWCP-isRetract`, or `CheckSetSteadyShotAdvancedMovie` tokens — proving FX6 has a rigidly fixed CMOS mount with gyro metadata-only stabilization + optional lens `OSS`.
  - **FX3 `v7.02` `appFw.so`** retains `set_steadyshot_advanced_movie_i` (absent on FX6), and Stock-CP `cpapp-b.bin` retains `LiroSeq: Restore.`, `HallPIDOUT_0`, `GyroPIDOUT_0`, `FusionOUT_0`, `AllPIDOUT_0`, `PWMOUT_0`, `ExecImagerCalibration`, and **36** Thumb-2 `MOVW Rd, #0x1400` (`0x0400 | 0x1000`) completion dispatch sites.
- **Stock-CP Calibration Immutability (`calibration_mutation_bytes == 0`)**:
  - Preserving FX3 Stock-CP `cpapp-b.bin` unmodified protects factory gyro/Hall calibration partitions (`p2:/Backup.bin`, `p2:/psd.bin`, `p6:Jiritsu`), sends `0x0400` (`0d2000040a0001800000` when `Off`) to keep Center-Lock energized (preventing unpowered floating-sensor rattle hazards), coordinates lens `OSS`, and preserves `UDAMSetGyroscopeValue` / `UDAMSetAccelerometerValue` telemetry for Catalyst Browse / Gyroflow.

---

## 3. Verification Commands & Results

```sh
# 1. Clean-Room & Local Donor Phase 55 CLI audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-emount-af --clean-room
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-emount-af

# 2. Full 10-auditor Makefile verification
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-firmware-lab
make verify-firmware-lab

# 3. Full 213-test dual-mode unit suite (<8s in both modes)
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
```

- Clean-Room full suite: **213 tests in 2.670s** (`OK`)
- Local Donor full suite: **213 tests in 7.917s** (`OK`)
