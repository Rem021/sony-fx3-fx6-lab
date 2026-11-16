# Phase 65 Report — 12th Unified Firmware-Lab Auditor: White Balance (`Shockless WB` / `ATW` / `WHT BAL` Soft-Mapping), Base Look / Gamma-Gamut Matrix, Paint Menu `3x3` Color Matrix (`R-G..B-G`) / Knee / Black Gamma & `cnflasha` Calibration Immutability

- **Date**: `2026-11-14`
- **Target Package**: `outputs/fx3-firmware-lab/` ([`wb_color_matrix_and_look_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/wb_color_matrix_and_look_auditor.py))
- **Milestone**: **12th Unified Auditor** integrated into [`run_audit_all()`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-wb-color-look [--clean-room] [--json]`)
- **Wave-6 Intelligence Companion**: [`reports/2026-11-14-global-sony-wave6-color-c2c-unbrick-intel/README.md`](../2026-11-14-global-sony-wave6-color-c2c-unbrick-intel/README.md)
- **Dual-Mode Verification Status**:
  - **Local Donor (`os.O_RDONLY`)**: `LOCAL_DONOR_VERIFIED`, `all_checks_passed = true`, `10 / 10` donor artifacts verified (`0.312s` standalone), `report_sha256 = 3dd8bcebe9afb2f75052b42dcc1c3009f52d197ce87e61938440a8456d86c55f`
  - **Forced Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**: `CLEAN_ROOM_SYNTHETIC_VERIFIED`, `all_checks_passed = true`, `10 / 10` synthetic fixtures verified (`0.001s` standalone), `report_sha256 = 5de410d384d8f14a769d3064d21838ab2d726ace5696d6e5f0ce92399d8c2bfe`
  - **Unit Tests**: `271 / 271` total suite tests pass (`3.618s` Clean-Room, `9.896s` Local Donor across all 10 test files; `30` new Phase 65 tests in [`test_wb_color_matrix_and_look.py`](../../outputs/fx3-firmware-lab/tests/test_wb_color_matrix_and_look.py) running in `0.634s`)

---

## 1. Strictly `os.O_RDONLY` Donor Artifact Inventory (10 Binaries & String Packs)

All local donor reads open files strictly via `os.O_RDONLY` (`mmap.ACCESS_READ` ELF64 `.rodata`/`.dynstr` section-scoped single-pass scanning without copying or mutating proprietary files), and fall back deterministically to synthetic clean-room fixtures when `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or absent donor trees are detected.

| Key | Body / FW | Artifact | Local Donor Size (B) | Role in Phase 65 Audit |
|---|---|---|---:|---|
| `fx3_appfw` | FX3 `v7.02` | `appFw.so` | `79,015,712` | `MOVIE_SHOCKLESS_WB_OFF/1/2/3`, `WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_*`, `GAMMA_SLOG3/ITU709_800/HLG`, `S_GAMUT3_CINE`, `EVENT_REMOTE_PICTURE_PROFILE_KNEE_*`, `PID_SET_SHADING_CORRECTION`, `0` physical `WHITE_SWITCH_POSITION_A/B` markers |
| `fx6_appfw` | FX6 `v6.01` | `appFw.so` | `50,520,424` | `WHITE_SWITCH_POSITION_PRESET/A/B`, `ATW_MODE_ON/OFF`, `MOVIE_SHOCKLESS_WB_*`, `SELECT_LUT_SDR/HDR_*`, `USER_MATRIX_RG..BG_SDR`, `PID_SET_MULTI_MATRIX`, `PID_SET_KNEE_POINT/SLOPE`, `PID_SET_BLACK_GAMMA/LEVEL` |
| `fx3_libmpr` | FX3 `v7.02` | `libmpr.so` | `3,517,008` | `CaptureGammaEquation`, `WhiteBalance`, `CaptureColorPrimaries`, `LUT_3D_SIZE` |
| `fx6_libmpr` | FX6 `v6.01` | `libmpr.so` | `28,921,824` | `CaptureGammaEquation`, `WhiteBalance`, `GammaForLook`, `ConvertSRLiveDataTransferMatrix` |
| `fx3_cpapp` | FX3 `v7.02` | `cpapp-b.bin` | `15,980,568` | Stock-CP (`cp_mutation_bytes == 0`), `SET_CUSTOM_WB_SAVE`, `MLUT*`, `PP_KneePoint`, `PP_BlackGammaLevel/Range`, `IMX510` calibration & `ShadowReadBackup`/`ShadowWriteBackup` |
| `fx6_cpapp` | FX6 `v6.01` | `cpapp-b.bin` | `17,952,816` | `GetATWSpeed`, `setWBChangeSpeed_ATWSpeed_OnePushAWBDetectArea_AWBMode`, `MLUT*`, `MULTI_MATRIX*`, `Paint_KneePoint/Slope`, `WBGainR/G/B/Std`, `IMX510` calibration |
| `fx3_str_en` | FX3 `v7.02` | `string_english.uxc` (`ns=39`) | `165,740` | `0x0004E5D4` (`White Balance`), `0x0004E8A4` (`Color Temp.`) |
| `fx3_str_en_g` | FX3 `v7.02` | `string_english_g.uxc` (`ns=3`) | `69,600` | `0x000062F0` (`White Balance`), `0x00006531` (`ITU709 Matrix`) |
| `fx6_str_en_1` | FX6 `v6.01` | `string_english.uxc` (`ns=1`) | `118,208` | `MLUT`, `ATW`, `White Balance`, `S-Cinetone`, `Base Look/LUT`, `709(800%)`, `S-Log3`, `ITU709`, `HLG Live`, `HLG Natural` |
| `fx6_str_en_2` | FX6 `v6.01` | `string_english_2.uxc` (`ns=2`) | `118,676` | `Preset 3200K/4300K`, `5600K`, `Memory A/B`, `Shockless White`, `ATW Speed`, `User Matrix R-G..B-G`, `Multi Matrix`, `Knee Point/Slope`, `Black Gamma` |

---

## 2. Four-Pillar White Balance, Base Look, Paint Matrix & Calibration Verification

### Pillar A — White Balance Control & `WHT BAL` Physical Switch Soft-Mapping
- **Kelvin -> Mired & Tint Bounds**: Validates `Preset` (`3200K` Tungsten = `312.5` Mired, `4300K`, `5600K` Daylight) and `Memory A / Memory B` across `2000K..15000K` in `100K`/`50K` steps plus `CC MG/GR` tint `-99..+99`, enforcing monotonic R/B gain ratios across color temperature.
- **Shockless WB (`Off / 1 / 2 / 3`) Slew Damping**: Evaluates perceptual Mired-space exponential transitions ($\tau \in \{0.0, 0.65, 1.60, 3.20\}\text{ s}$), proving monotonic convergence and strict speed ordering (`OFF > 1 > 2 > 3`).
- **FX3 Hardware Absence & Soft-Mapping (`missing_gpio_faults == 0`)**: Confirms `0 / 3` FX6 physical `WHITE_SWITCH_POSITION_A/B` / `ATW_MODE_ON` tokens in FX3 `appFw.so` and maps `PRESET_3200K/4300K/5600K`, `MEMORY_A/B`, and `ATW` (`ATW Hold`) cleanly onto FX3 Assignable Buttons + `Fn`/Big6 touch without missing-GPIO faults.

### Pillar B — Base Look & Gamma/Gamut Matrix
- Verifies all `8` canonical Cinema Line profiles across FX6 `v6.01` and FX3 `v7.02`:
  - `S-Cinetone`, `S-Log3 / S-Gamut3.Cine`, `S-Log3 / S-Gamut3`, `ITU709`, `709(800%)`, `HLG Live`, `HLG Natural`, and `User 3D LUT (MLUT)` (`User1..16` slots, internal/monitor MLUT routing, and SDR/HDR target display validation).

### Pillar C — Paint Menu Matrix (`R-G..B-G`), Multi-Matrix, Knee & Black Gamma
- **Exact `3x3` Linear Color Matrix White-Point Verifier**:
  - Formulates $M_{ii} = 1 - \sum_{j \neq i} M_{ij}$ from Paint Menu off-diagonal tweaks (`R-G, R-B, G-R, G-B, B-R, B-G` in `[-99..+99]`, with Level/Phase scaling), proving every row sums strictly to `1.0` (`max_row_sum_error <= 1e-9`) and `det(M) > 0.05` so neutral grey `[1, 1, 1]` never tint-shifts.
  - Explicitly rejects synthetic/corrupted `3x3` matrices where any row sum deviates from `1.0` (`BLOCKED_PAINT_MATRIX_WHITE_POINT_DRIFT`) or `det(M) <= 0.05`.
- **Knee & Black Gamma Bounds**: Enforces Sony Knee Point (`75.0%..109.0%`), Knee Slope (`-99..+99`), Black Level (`-99..+99`), Black Gamma Level (`-99..+99` + `HIGH/MIDDLE/LOW/WIDE/NARROW`), and Multi-Matrix Hue/Sat (`-99..+99`).

### Pillar D — Factory Color/WB Calibration & `cnflasha` Zero-Mutation Proof
- Verifies shared `IMX510` sensor driver & defect/shading calibration markers (`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`, `ExecDefectCorrection`, `ExecImagerCalibration`, `ShadowReadBackup`, `WBGainR/G/B/Std`), proving `cnflasha` (`p2:/Backup.bin` + `p6:Jiritsu`) and Stock-CP (`p8:/cp`) remain strictly read-only (`calibration_mutation_bytes == 0`, `cp_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).

---

## 3. Verification Commands & Results

```sh
# 1. Local Donor & Clean-Room Phase 65 CLI audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-wb-color-look --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-wb-color-look --clean-room --json

# 2. Full 12-auditor unified CLI check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room

# 3. Full 271-test dual-mode unit suite + hygiene audit
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -q
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- Clean-Room full suite: **271 tests in 3.618s** (`OK`)
- Local Donor Phase 65 suite (`test_wb_color_matrix_and_look.py`): **30 tests in 0.634s** (`OK`)
- Local Donor full suite: **271 tests in 9.896s** (`OK`)
- `scripts/run_all_lab_tests.py --clean-only`: **`ALL GREEN in 0.03s` (`CLEAN`)**
