# Phase 37 Report: `.cube` (`17^3` / `33^3`) User 3D LUT Sanitizer, `P1` (`/dev/nflasha30`) + `P11` Hardware Packer & Sony `RTMD` (`0xE304` `IMX510` IBIS) Verifier

- **Task / Agent**: `Hydrogen-29` (`task_7cb73505992d`, Wave 5)
- **Target Package**: [`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/)
- **Primary Module**: [`cube_lut_and_rtmd_verifier.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/cube_lut_and_rtmd_verifier.py)
- **CLI Entrypoint**: `python3 -B -m fx3_firmware_lab audit-lut-rtmd [--clean-room]` ([`__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py))
- **Unit Test Suite**: [`test_cube_lut_and_rtmd.py`](../../outputs/fx3-firmware-lab/tests/test_cube_lut_and_rtmd.py) (**27** new tests; **102** total tests in `outputs/fx3-firmware-lab/tests`, `< 5s` runtime in both Local Donor `O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)

---

## 1. Executive Summary

| Pillar | Verification Scope | Key Quantitative Result |
| --- | --- | --- |
| **Part A1: Anti-Crash `.cube` Sanitizer** | Adobe/Iridas `.cube` (`17^3` & `33^3`) parser & fault guard against v6.00->v6.01 custom `.cube` crash & `/dev/nflasha30` overflow | Rejects `NaN`/`Inf`, wrong voxel counts, `DOMAIN_MIN >= DOMAIN_MAX`, `LUT_1D_SIZE` mismatches, unsafe `TITLE`/control chars, and oversized files (`> 2 MiB` / `> 40,000` lines) |
| **Part A2: Trilinear `17^3 -> 33^3` & `S-Log3` Proof** | Exact R-fastest/G-middle/B-slowest trilinear interpolation + `U12.0`/`U16` (`215,622 B`) & `U8` (`107,812 B`) DMA packing | `17^3` (`4,913`) -> `33^3` (`35,937`) `S-Log3` OETF ramp across 256 samples: `max_lsb_error = 1`, `max_float_error = 3.33e-16` (`<= 1 LSB` proven) |
| **Part A3: `P1` (`/dev/nflasha30`) + `P11` + `BK4`** | `P1` 16-slot VFAT (`48.00 MiB`), `P11` `164B SetLutData` + `0x0165` (`36 B`) + `0x0166` (`10 B`), `BK4` `0x02cf1453` + `0x02cf14a4..0x02cf14b3` | `16` full `33^3` slots (`970,460 B` each) consume `15,597,568 B` (`8 KiB` clusters) leaving `34,118,656 B` (`67.79%` margin); `BK4\0` checksum valid |
| **Part B1: Donor `O_RDONLY` Marker Audit** | FX3 v7.02 (`appFw.so`, `libmpr.so`) & FX6 v6.01 (`appFw.so`, `libmpr.so`) read-only scan | `100%` markers matched (`0` missing): `/dev/nflasha30`, `model_user_lut_files`, `mpr::SetLutData`, `KlvConverter::Rdd18KeyCameraUnit`, `UDAMSetGyroscopeValue`, `SMPTE UL 060e2b34` (`106` FX3 / `3,278` FX6 hits) |
| **Part B2: Sony `RTMD` (`0xE304` `IMX510` IBIS)** | Big-endian `SMPTE RDD 18` KLV + BER length + local tags (`0x3209`, `0x3219`, `0x321A`, `0xE105`, `0xE304`) | `90 B` deterministic packet (`sha256=f3bf0d3f...`); enforces `center_lock_energized=True`, `floating_sensor_hazard=False`, and `0x000F` Catalyst Browse / Gyroflow coherence |

---

## 2. Part A — `.cube` (`17^3` / `33^3`) Sanitizer, `P1` `/dev/nflasha30`, `P11` `SetLutData` & `BK4` Slot Flags

### 2.1 Anti-Crash Sanitization Rules (v6.00 -> v6.01 Fault & `model_user_lut_files file sizeover!!` Prevention)

Inspection of FX3 v7.02 `appFw.so` (`79,015,712 B`) and `libmpr.so` (`3,517,008 B`) alongside FX6 v6.01 `appFw.so` (`50,520,424 B`) and `libmpr.so` (`28,921,824 B`) confirms:
- Both bodies parse `.cube` files using `LUT_3D_SIZE`, `DOMAIN_MIN`, `DOMAIN_MAX`, and `LUT_3D_INPUT_RANGE` inside `appFw.so::model_user_lut_files` and `libmpr.so::ExecuteSetLutData` (`malloc(0x6a1b9)` = `434,617 B`).
- FX3 `appFw.so` mounts `/dev/nflasha30` (`P1` adapted from FX6 `/dev/nflasha20`) onto `/usr/data/lut/` (`LUT%03d.cube`), guarding against oversized uploads via `model_user_lut_files file sizeover!!`.
- `parse_and_sanitize_cube_lut()` enforces:
  1. **Size & Line Caps**: `<= 2,097,152 B` (`2.00 MiB` per `.cube` slot) and `<= 40,000` lines (`33^3 = 35,937` entries), preventing heap/stack parser exhaustion and `/dev/nflasha30` VFAT exhaustion.
  2. **Strict Directive & Syntax Guards**: Rejects `LUT_1D_SIZE`, `LUT_1D_INPUT_RANGE`, duplicate `TITLE`/`LUT_3D_SIZE`/`DOMAIN_MIN`/`DOMAIN_MAX`, non-`{17, 33}` grid sizes, control characters / NUL bytes / path-traversal `TITLE` (`..`, `/`, `\`), and RGB triplets before `LUT_3D_SIZE`.
  3. **Numerical & Domain Integrity**: Rejects `NaN`, `+Inf`, `-Inf`, extreme floats (`|v| > 10.0`), non-monotonic `DOMAIN_MIN >= DOMAIN_MAX` on any channel, and exact voxel count mismatches (`len(entries) != size^3`).

### 2.2 Trilinear `17^3 -> 33^3` Upsampler, `S-Log3` Identity Proof & `P11`/`BK4` Framing

- **`upsample_cube_17_to_33()` & `pack_cube_to_dma_table()`**:
  - Converts `17^3` (`4,913` triplets) -> `33^3` (`35,937` triplets) in standard R-fastest, G-middle, B-slowest lattice ordering (`idx = r + N*(g + N*b)`).
  - Packs into CXD90057 hardware DMA tables: `U12.0` (`215,622 B`, `0..4095` in `<HHH`), `U16` (`215,622 B`, `0..65535` in `<HHH`), and `U8` 4-byte aligned (`107,812 B`).
  - **`verify_slog3_identity_ramp()`**: Evaluates 256 samples across the Sony S-Log3 OETF (`slog3_linear_to_code`) through `17^3 -> 33^3` + `U12.0` DMA table lookup, proving `max_lsb_error = 1` (`<= 1 LSB`) and `max_float_error = 3.33e-16`.
- **`P11` & `BK4` Framing (`build_p11_lut_hardware_bundle()`)**:
  - **`mpr::SetLutData` (`164 B`)**: Exact `+0x00` length (`164`), `+0x04` enable (`1`), `+0x05..+0x1e` metadata (`category=3`, `look_slot`, `grid=33`, `dma_bytes=215622`, `base_iso`, `ei_index`, `35937`, `0x6a1b9`, `0xbb80`), `+0x1f..+0x5e` NUL-terminated `/usr/data/lut/LUT001.cube`.
  - **`0x92840747` UIPC Packets**: `0x0165` (`36 B` DMA packet switching to DRAM/SRAM+REG when `> 0xbb80 = 48,000 B`) and `0x0166` (`10 B` LUT enable/reset toggle).
  - **`BK4\0` LUT Slot Flags**: Generates `0x02cf1453` (`Select LUT`: `0x00=S709`, `0x01=R709`, `0x02=S-Log3`, `0x03..0x12=User1..16`) and `0x02cf14a4..0x02cf14b3` (`User1..16` presence flags `0x01`/`0x00`), validated via `build_clean_room_bk4_record()` + `audit_bk4_record_bytes()`.
- **`P1` `/dev/nflasha30` (`48.00 MiB` VFAT) Storage Budget**:
  - `50,331,648 B` total (`0x00018000` sectors) - `615,424 B` VFAT overhead = `49,716,224 B` usable data area (`8 KiB` clusters).
  - `16` full `33^3` `.cube` slots (`970,460 B` each) allocate `15,597,568 B`, leaving `34,118,656 B` (`67.79%` free margin).

---

## 3. Part B — Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) & `IMX510` IBIS Center-Lock Verification

### 3.1 Donor Binary Read-Only Findings (`O_RDONLY`)

| Binary (`O_RDONLY`) | Size (B) | Verified LUT & `RTMD` / `RDD 18` Markers | SMPTE UL `060e2b34` Hits |
| --- | ---: | --- | ---: |
| FX3 v7.02 `appFw.so` | `79,015,712` | `/dev/nflasha30`, `model_user_lut_files::mount_lut_folder():OK`, `LUT_3D_SIZE`, `LUT_3D_INPUT_RANGE`, `/usr/data/lut`, `User1:`..`User16:`, `SL3SG3Ctos709.cube` | `0` (handled in `libmpr.so`) |
| FX6 v6.01 `appFw.so` | `50,520,424` | `model_user_lut_files::mount_lut_folder():OK`, `LUT_3D_SIZE`, `LUT_3D_INPUT_RANGE`, `/usr/data/lut`, `User1`..`User16`, `SL3SG3Ctos709.cube` | `0` (handled in `libmpr.so`) |
| FX3 v7.02 `libmpr.so` | `3,517,008` | `LUT_3D_SIZE`, `DOMAIN_MIN`, `DOMAIN_MAX`, `mpr::SetLutData`, `KlvConverter::Rdd18KeyCameraUnit`, `Rdd18KeyLensUnit`, `UDAMKeyUnit`, `UDAMSetGyroscopeValue`, `UDAMSetAccelerometerValue`, `UDAMSetSonyLookControlValue` | `106` |
| FX6 v6.01 `libmpr.so` | `28,921,824` | Same `mpr::SetLutData` & `mpr::KlvConverter` (`RDD18` / `UDAM` / `DistortionCorrection` / `Gyroscope` / `Accelerometor`) contracts | `3,278` |

### 3.2 Big-Endian `RTMD` (`SMPTE RDD 18` / `0xE304`) Frame Packet Layout

- **Outer KLV Envelope**: 16-byte SMPTE RDD 18 Acquisition Metadata Set UL (`060e2b34025301010c02010101010000`) + definite BER length.
- **Big-Endian Local Tags (`>HH`)**:
  - `0x3209` (`4 B`): Shutter Angle in `0.01°` (`18000` = `180.0°`).
  - `0x3219` (`4 B`): `IMX510` sensor readout duration (`8600` us).
  - `0x321A` (`8 B`): Dual Base ISO (`800` or `12800`) + EI Index (`200..102400`).
  - `0xE105` (`UTF-8`): Active 3D LUT name (`S-Cinetone`, `User1`, etc.).
  - `0xE304` (`32 B` `>BBBBHH3i3i`): FX3 5-Axis IBIS Center-Lock (`Off`/`Standard`/`Active`, `center_lock_energized=1`, `floating_sensor_hazard=0`, `axes=5`), `gyro_sample_hz` (`1000`), `coherence_flags` (`0x000F`: center-lock + gyro + Catalyst Browse + Gyroflow), 3-axis Gyro (`mrad/s`), and 3-axis Accelerometer (`mg`).

---

## 4. Verification Summary

```sh
# 1. Local Donor (O_RDONLY) full suite: 102 / 102 PASS (< 5s)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v

# 2. Forced Clean-Room full suite: 102 / 102 PASS (< 2s)
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v

# 3. Phase 37 CLI auditor & repository clean audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-lut-rtmd
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-lut-rtmd --clean-room
make clean-audit
```
