# Milestone Phase 75 Report — Assignable Buttons (`FX6 1..11` -> `FX3`), `T/W` Zoom Lever / `Clear Image Zoom` (`CIZ`), Touch AF + Anamorphic Desqueeze, and `Big6` / `Fn` Volatile `BK4` Shadow Auditor

- **Date**: `2026-11-14`
- **Milestone**: Phase 75 (`PHASE_75_SCHEMA = "fx3_firmware_lab_phase75_assignable_ciz_big6_v1"`, `PHASE_75_VERSION = "75.0.0"`)
- **Related Wave-7 Intel Report**: [`reports/2026-11-14-global-sony-wave7-ciz-assignable-hidvm-intel/README.md`](../2026-11-14-global-sony-wave7-ciz-assignable-hidvm-intel/README.md)
- **Live Safety Redlines Verified**:
  - `o_rdonly_enforced = True` (`os.O_RDONLY` + `mmap.ACCESS_READ` across all 12 donor artifacts)
  - `persistent_emmc_writes_authorized = False`
  - `bk4_persistent_nvram_writes = 0`
  - `null_gpio_faults = 0`
  - `icx1295_crashed = False`, `libcamera_crashed = False`
  - Zero proprietary keys, binaries, or `.pyc` files committed; live port `8768` (`PID 18787`) untouched.

---

## 1. Deliverables Built & Wired

1. **Wave-7 Live Web Intelligence Report**:
   - [`reports/2026-11-14-global-sony-wave7-ciz-assignable-hidvm-intel/README.md`](../2026-11-14-global-sony-wave7-ciz-assignable-hidvm-intel/README.md) — bilingual ZH-CN/EN synthesis with verified public URLs covering Sony FX3 `v7.00–v7.02` & FX6 `v6.00–v6.02` (`Big6`, `Clear Image Zoom`, `Assignable 1..11` vs `1..6` + `XLR-H1`), QEMU VirtIO-Input / Linux `uinput`/`evdev` capacitive multi-touch + rotary/zoom rocker virtualization, and volatile `BK4` / `CAMSET` shadow overlays.
2. **14th Unified Firmware-Lab Auditor**:
   - [`outputs/fx3-firmware-lab/fx3_firmware_lab/assignable_zoom_ciz_and_fn_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/assignable_zoom_ciz_and_fn_auditor.py)
   - Wired into [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) and [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-assignable-ciz [--clean-room] [--json]`, plus `assignable_zoom_ciz_and_fn_audit` as the **14th auditor** in `run_audit_all()`).
   - Documented in [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md).
3. **34 Fast Dual-Mode Unit Tests**:
   - [`outputs/fx3-firmware-lab/tests/test_assignable_zoom_ciz_and_fn.py`](../../outputs/fx3-firmware-lab/tests/test_assignable_zoom_ciz_and_fn.py)

---

## 2. Four-Pillar Engineering Verification

| Pillar | Scope Audited | Observed Donor & Clean-Room Invariants |
|---|---|---|
| **Pillar 1: Assignable Button Cross-Body Catalog** | `FX6 ASSIGN_1..11` + `LENS_FOCUS_HOLD` -> `FX3 CUSTOM_1..6` + `LENS_FOCUS_HOLD` + `JOYSTICK_CENTER` + `AF_ON` + `AEL` + `TOUCH_FN_ICON` | `11` hardware-backed Cinema Line actions (`Zebra`, `Peaking`, `Marker`, `Base ISO / Cine EI`, `S&Q Motion`, `Focus Magnifier x4.0`, `AF/MF`, `LUT On/Off`, `Status Check`, `Big6 / Shooting Screen`, `Audio Level Display`) + `6` FX6-only absent-hardware targets safely isolated/redirected/grayed-out (`ND Preset`, `Auto ND`, `VF Adjust`, `Push Auto ND/Iris -> Push Auto Iris`, `SDI/HDMI Rec Control -> HDMI Rec Control`, `Smart Grip Assign 7..9`); **`null_gpio_faults = 0`**, `xlr_h1_compatible = True`, shared `libInfraLensCommunicator.so` (`14,544 B`) verified. |
| **Pillar 2: `T/W` Zoom Lever (`8-Step`) & `CIZ` Mutual-Exclusion Matrix** | `Optical Zoom Only` (`1.00x`), `Clear Image Zoom` (`1.50x` 4K DCI/QFHD, `2.00x` FHD), `Digital Zoom` (`4.00x`), `HDMI RAW16`, `S&Q 120/240fps` | `T/W` rocker speeds `1..8` validated; `CIZ` retains `By-Pixel Super Resolution`, `627-pt PDAF`, and `Face/Eye Tracking`; enabling `HDMI RAW16` or `S&Q >= 100fps` (`120/240fps`) deterministically clamps `CIZ` back to `1.00x` `OPTICAL_ZOOM_ONLY` (`CIZ_CLAMPED_TO_OPTICAL_1X_SAFE`) with `icx1295_crashed = False` and `libcamera_crashed = False`. |
| **Pillar 3: Touch Tracking AF & Anamorphic Desqueeze + `4.0x` Magnifier** | `GPE0 960x540` capacitive touch -> `IMX510` `33x19` (`627`-pt) normalized `[0.0..1.0]` PDAF coordinates | Verified exact inverse-X desqueeze math `u_sensor = 0.5 + (u_view - 0.5) / D` across `1.0x`, `1.3x`, `1.5x`, `1.6x`, `2.0x` (e.g., `x=864.0` at `2.0x` -> `u_disp=0.90` -> `u_sensor=0.70`), `4.0x` Focus Magnifier crop composition (`x=720.0` at `4.0x + 2.0x` -> `0.53125`), edge center-clamping, and `Touch Shutter` blocked in Cine mode (`BLOCKED_TOUCH_SHUTTER_DISABLED_IN_CINE`). |
| **Pillar 4: Custom `Big6` (`6` Slots) & `Fn` (`12` Slots) Volatile `BK4` Shadow** | FX3 `v7.00+` `S&Q Mode Settings = FIXED_VARIABLE` gate, `Home (Lower Left)` `APERTURE` vs `ND_FILTER`, `/tmp` / `ram://` `CAMSET` JSON shadow | `6` `Big6` slots + `12` `Fn` slots serialize/roundtrip cleanly to volatile `/tmp` / `ram://` `CAMSET` JSON while `LEGACY_SQ_MODE` blocks Big6 (`BLOCKED_BIG6_REQUIRES_FIXED_VARIABLE_SQ`) and `/dev/nflasha*` / `/dev/cnflasha*` / `bk4://persistent` paths are hard-blocked (`BLOCKED_PERSISTENT_BK4_NVRAM_WRITE`, `bk4_persistent_nvram_writes = 0`). |

---

## 3. Observed Donor Artifacts, Determinism Hashes & Verification Runs

### 12 Verified `os.O_RDONLY` Donor Artifacts (`LOCAL_DONOR_VERIFIED`)
- `fx3_appfw`: `79,015,712 B` | `fx6_appfw`: `50,520,424 B`
- `fx3_cpapp`: `15,980,568 B` | `fx6_cpapp`: `17,952,816 B`
- `fx3_lens_comm`: `14,544 B` | `fx6_lens_comm`: `14,544 B`
- `fx3_global_xdb`: `11,664 B` | `fx6_global_xdb`: `1,792 B`
- `fx3_str_en`: `165,740 B` | `fx3_str_en_g`: `69,600 B`
- `fx6_str_en_1`: `118,208 B` | `fx6_str_en_2`: `118,676 B`

### Execution Benchmarks & Deterministic `report_sha256`
- `analyze_assignable_zoom_ciz_and_fn()` (Local Donor mode): **`0.273s`** (`< 0.5s` target), `all_checks_passed = True`, `report_sha256 = 772c9ae0be7745fbcd5062f72d1b422bfec8cd7965e3bee729f5eb26b6303ac8`
- `analyze_assignable_zoom_ciz_and_fn(clean_room=True)`: **`0.002s`**, `all_checks_passed = True`, `report_sha256 = f4859522eb6cdcb37543272376c24db987d2488b2f64c79759365c4295f22d7b`
- `run_audit_all()` across all **14 unified auditors**:
  - Local Donor mode: **`6.837s`**, `all_checks_passed = True`
  - Clean-Room mode: **`0.026s`**, `all_checks_passed = True`

### Test & Hygiene Commands Executed (All Passing)
1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_assignable_zoom_ciz_and_fn.py -v` -> **`Ran 34 tests in 0.618s` (`OK`)**
2. `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_assignable_zoom_ciz_and_fn.py -v` -> **`Ran 34 tests in 0.345s` (`OK`)**
3. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v` -> **`Ran 337 tests in 11.119s` (`OK`)**
4. `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v` -> **`Ran 337 tests in 4.408s` (`OK`)**
5. `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> **`CLEAN (0.03s)` / `ALL GREEN`**
