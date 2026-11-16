# Phase 98 — 19th Unified `fx3-firmware-lab` Auditor: User 3D LUT (`.cube` `17^3`/`33^3`/`65^3`) Domain/NaN Sanitizer & Tetrahedral vs Trilinear `CXD90058` Quantization, `S-Log3` Legal/Extended HDMI AVI InfoFrame Guard, & HDMI-to-12G-SDI Active Converter REC-Trigger Parity (`lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py`)

- **Date / 日期**: 2026-11-14
- **Schema / 版本**: `fx3_firmware_lab_phase98_lut3d_tetrahedral_sdi_hdmi_v1` (`98.0.0`)
- **CLI Subcommand / CLI 子命令**: `python3 -m fx3_firmware_lab audit-lut3d-sdi-hdmi [--clean-room] [--json]`
- **Strict Read-Only / 只读零突变约束**: `os.O_RDONLY` + `mmap.ACCESS_READ`, `persistent_emmc_writes_authorized = False`, `calibration_mutation_bytes = 0`, `emmc_mutation_bytes = 0`

---

## 1. Executive Summary / 核心摘要

Phase 98 integrates the **19th unified auditor** ([`lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py)) into `fx3-firmware-lab`, establishing end-to-end dual-mode (`LOCAL_DONOR_VERIFIED` + `CLEAN_ROOM_SYNTHETIC`) verification across FX3 `v7.02` and FX6 `v6.01` for:

1. **Pillar 1 — Adobe/Iridas `.cube` (`17^3` / `33^3` / `65^3`) Domain/NaN Sanitizer, Exact 6-Tetrahedra Subdivision vs Trilinear Resampler & `CXD90058` `33^3` `U12.4`/`U16` DMA Packer**
2. **Pillar 2 — `S-Log3` 10-Bit Legal (`64..940`) vs Extended Super-White (`64..1019`) & CEA-861 HDMI AVI InfoFrame Quantization Range Guard**
3. **Pillar 3 — FX6 Native `12G-SDI` (`SMPTE ST 2082` ANC / `RP 188` / `ST 12-2` ATC) vs FX3 HDMI-to-12G-SDI Active Converter REC-Trigger & Timecode Parity**
4. **Pillar 4 — `MLUT` Burn-In vs Proxy-Only vs Clean-HDMI Independent Routing Matrix & Zero-Calibration-Mutation Proof**

第 98 阶段向 `fx3-firmware-lab` 集成第 **19** 个统一审计器 [`lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py)，在本地只读供体（`LOCAL_DONOR_VERIFIED`）与净室合成（`CLEAN_ROOM_SYNTHETIC`）双模式下全部通过验证，全套 **19 个审计器** 与 **513 项单元测试**（含本阶段新增 38 项双模式测试）在双模式下 **100% 绿灯**。

---

## 2. Observed Verification Metrics / 实测验证数据

| Metric / 指标 | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) | Gate / 门禁要求 |
| :--- | :--- | :--- | :--- |
| **19th Auditor Status** | `all_checks_passed = True` (`0` errors) | `all_checks_passed = True` (`0` errors) | 100% Pass |
| **19th Auditor Wall Runtime** | **`0.2494 s`** (cold `0.2567 s`) | **`0.0180 s`** (warm; cold `0.0183 s`) | `< 0.35 s` local / `< 0.02 s` clean-room |
| **Report SHA-256 Digest** | `55878c1e3bb02bf22422a4155fa302c349bccdc9139bae263e442f402ba27d7f` | `edb34cb3250567550e88613bf8415326a4af6716d4e76b39181f5a36c1bae82e` | Deterministic |
| **`audit-all --json`** | **19 / 19 green** (`all_checks_passed = True`) | **19 / 19 green** (`all_checks_passed = True`) | 19 / 19 Auditors |
| **Phase 98 Unit Tests (`test_lut3d_cube_tetrahedral_and_sdi_hdmi.py`)** | **38 / 38 passed** (`2.577 s`) | **38 / 38 passed** (`1.949 s`) | `>= 34` dual-mode tests |
| **Full Lab Unit Suite (`unittest discover`)** | **513 / 513 passed** (`19.949 s`) | **513 / 513 passed** (`9.716 s`) | Zero failures |
| **`scripts/run_all_lab_tests.py --clean-only`** | `CLEAN (0.04s)` — ALL GREEN | `CLEAN (0.04s)` — ALL GREEN | Zero `.pyc` / binaries |
| **Calibration / eMMC Mutation** | `0 B` / `0 B` (`os.O_RDONLY`) | `0 B` / `0 B` | Strict zero-mutation |

---

## 3. Inspected Local Donor Artifacts (`os.O_RDONLY`) / 只读本地供体清单

| Artifact Key | Exact Role | Local Donor Size (Bytes) | Clean-Room Fixture Size (Bytes) | Verified Real Markers / Findings |
| :--- | :--- | ---: | ---: | :--- |
| `fx3_appfw` | FX3 `v7.02` `appFw.so` | `79,015,712` | `752` | `LUT_3D_SIZE`, `LUT_3D_INPUT_RANGE`, `VAL_setting_embed_lut_file_EMBED_LUT_FILE_ON/OFF`, `VAL_setting_rec_control_REC_CONTROL_ON`, `VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON`, `VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_OFF` |
| `fx6_appfw` | FX6 `v6.01` `appFw.so` | `50,520,424` | `795` | `VAL_setting_sdi_hdmi_rec_control_SDI_HDMI_REC_CONTROL_SDI_HDMI_REMOTE_I_F`, `PARALLEL_REC`, `VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT`, `BKID_APP_EXTERN_MONITOR_LUT_HDMI_ONOFF`, `BKID_APP_EXTERN_MONITOR_LUT_SDI1_ONOFF` |
| `fx3_libmpr` | FX3 `libmpr.so` | `3,517,008` | `216` | `LUT_3D_SIZE`, `LUT_3D_INPUT_RANGE`, `DOMAIN_MIN`, `DOMAIN_MAX`, `_ZN3mpr10SetLutDataE` |
| `fx6_libmpr` | FX6 `libmpr.so` | `28,921,824` | `216` | `LUT_3D_SIZE`, `LUT_3D_INPUT_RANGE`, `DOMAIN_MIN`, `DOMAIN_MAX`, `_ZN3mpr10SetLutDataE` |
| `fx3_cpapp` | FX3 `cpapp-b.bin` | `15,980,568` | `317` | `SET_MONITOR_LUT`, `SET_SHOOTING_LUT`, `SET_HDMI_REC_CONTROL`, `SET_VIDEO_OUTPUT_FORMAT` |
| `fx6_cpapp` | FX6 `cpapp-b.bin` | `17,952,816` | `317` | `SET_MONITOR_LUT`, `SET_SHOOTING_LUT`, `SET_HDMI_REC_CONTROL`, `SET_VIDEO_OUTPUT_FORMAT` |
| `fx6_avbb_panelevf` | FX6 `AVBB_SCN_START_PANELEVF.so` | `275,968` | `220` | `SET_MONITOR_LUT`, `SET_MONITOR_MLUT`, `EXEC_SDI_MAIN_OUTPUT`, `EXEC_HDMI_OUTPUT` |
| `fx3_global_xdb` | FX3 `global.xdb` (`uxa\x07`) | `11,664` | `1,724` | `uxa\x07` container parsed read-only |
| `fx6_global_xdb` | FX6 `global.xdb` (`uxa\x07`) | `1,792` | `1,792` | `uxa\x07` container parsed read-only |
| `fx3_str_en` | FX3 English `ns=39` `.uxc` | `165,740` | `2,168` | `0x0000e1d5` (`"HDMI Resolution"`), `0x0000e41f` (`"CTRL FOR HDMI"`) |
| `fx3_str_en_g` | FX3 English `ns=3` `.uxc` | `69,600` | `1,152` | `0x00006128` (`"Deletes LUT files imported to User${v1}."`), `0x0000620b` (`"Import the LUT file to User${v1}?"`) |
| `fx6_str_en_1` | FX6 English `ns=1` `.uxc` | `118,208` | `912` | `0x00002029` (`"MLUT"`), `0x00002068` (`"Monitor LUT"`), `0x00002109` (`"LUT 709(800)"`), `0x0000219d` (`"Base Look/LUT"`) |
| `fx6_str_en_2` | FX6 English `ns=2` `.uxc` | `118,676` | `1,912` | `0x00004245` (`"HDMI TC Out"`), `0x00004251` (`"Rec Control"`), `0x00004287` (`"Monitor 3D LUT"`), `0x0000428d` (`"SDI/HDMI Rec Control"`), `0x0000435e` (`"Look: User 3D LUT Select"`), `0x00004362` (`"Look File: Load User 3D LUT"`) |

---

## 4. Technical Pillar Breakdown / 四大审计支柱详情

### Pillar 1 — `.cube` (`17^3` / `33^3` / `65^3`) Sanitizer & Exact 6-Tetrahedra `CXD90058` DMA Resampler
- **Fail-Closed `.cube` Sanitizer (`parse_and_sanitize_cube_lut_3d`)**: Supports `17^3` (`4,913`), `33^3` (`35,937`), and DaVinci Resolve / Dehancer `65^3` (`274,625`) `.cube` tables up to `16 MiB` / `300,000` lines, normalizing arbitrary `DOMAIN_MIN` / `DOMAIN_MAX` / `LUT_3D_INPUT_RANGE` bounds while failing closed on `NaN`, `±Inf`, inverted/degenerate `DOMAIN_MIN >= DOMAIN_MAX`, `LUT_1D_SIZE`, wrong voxel counts, control bytes (`NUL`, `0x07`), path-traversal/overlong `TITLE`, and negative/out-of-unit entries (with explicit opt-in `on_negative_or_oob="CLAMP"`).
- **Exact 6-Tetrahedra Subdivision (`tetrahedral_sample_cube`) vs Trilinear (`trilinear_sample_cube_3d`)**:
  - Proven on `S-Log3 / S-Gamut3.Cine -> Rec.709 (800%)`:
    - `17^3`: tetrahedral max delta = **`9.594e-4`** vs trilinear **`1.082e-3`**
    - `33^3`: tetrahedral max delta = **`2.170e-4`** vs trilinear **`2.673e-4`**
    - `65^3`: tetrahedral max delta = **`6.237e-5 < 1e-4`** vs trilinear **`7.455e-5`**
  - Monotonic convergence (`err_17 > err_33 > err_65`), tetrahedral `<=` trilinear across all grids, exact affine `3x3` preservation (`max delta = 5.55e-17 < 1e-12`), and exact `65^3 -> 33^3` stride-2 node identity (`0.0` delta).
- **`CXD90058` Hardware DMA Packing**: Resamples `17^3` / `33^3` / `65^3` onto Sony's native `33^3` (`35,937` voxels, `215,622 B`) little-endian `U12.4` (`max_q_err = 7.63e-6`) or `U16` (`max_q_err = 7.63e-6`) DMA tables strictly in volatile RAM (`/tmp/` or `ram://`) for up to `16` User LUT slots.

### Pillar 2 — `S-Log3` 10-Bit Legal (`64..940`) vs Extended (`64..1019`) & CEA-861 HDMI AVI InfoFrame Guard
- **Exact `S-Log3` 10-Bit Code Landmarks**: Verifies `0% black = 95/1023`, `18% grey = 420/1023`, `90% white = 598/1023`, and extended super-white `949..1019` (`+6.5..+7.5 EV` over middle grey).
- **CEA-861 17-Byte AVI InfoFrame Codec**: Builds and checksum-verifies (`sum(packet) & 0xFF == 0`) 17-byte `0x82 v2` AVI InfoFrames carrying `Y1:Y0` (`RGB` / `YCBCR_422` / `YCBCR_444`), `Q1:Q0`, and `YQ1:YQ0` range signaling.
- **Double-Scaling Shadow-Crush Prevention**: Blocks `SLOG3_EXTENDED_64_1019` `YCbCr 4:2:2` (`YQ=LIMITED`) fed into a `FULL_RANGE`-configured external recorder (Atomos / SmallHD), catching the exact `-59` code shadow crush (`95 -> 36`) and super-white highlight clipping (`949..1019 -> 1023`), as well as `HDMI RAW16` mislabeled as `YCbCr`.

### Pillar 3 — FX6 Native `12G-SDI` (`SMPTE ST 2082`) vs FX3 HDMI-to-12G-SDI Bridge REC-Trigger & TC Parity
- **Bit-Level `SMPTE ST 12-2 / RP 188` ATC Codec**: Packs and verifies `DID=0x60 / SDID=0x60` ANC timecode (`DF` & `NDF` BCD nibbles) + DBB bit-7 `SDI Remote REC` trigger across FX6 native `12G-SDI` BNC (`PARALLEL_REC`) and FX3 active HDMI-to-12G-SDI converters (`BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G`, `TERADEK_BOLT_HDMI_SDI_BRIDGE`, `ATOMOS_CONNECT_HDMI_SDI_BRIDGE`).
- **Fail-Closed Hardware & Protocol Guards**: Blocks FX3 targeting non-existent native `12G-SDI` BNC, blocks passive HDMI cables claiming `RP 188` ANC injection, blocks active converter REC triggers when `HDMI TC Output = OFF`, and enforces FX3 `HDMI RAW16` vs internal `PARALLEL_REC` exclusion (`ghost_sdi_bnc_hw_faults == 0`).

### Pillar 4 — `MLUT` Burn-In vs Proxy-Only vs Clean-HDMI Routing Matrix & Zero-Mutation Firewall
- Audits independent routing across `SLOG3_CLEAN_HDMI_LOG_INTERNAL`, `SLOG3_MLUT_HDMI_MONITORING`, `SLOG3_PROXY_EMBED_LUT_ONLY`, `FX6_BURN_IN_INTERNAL_LOOK`, and `HDMI_RAW16_CLEAN_NO_MLUT`, gating FX6 `SDI1` MLUT cleanly on FX3 (`VALID_FX3_SDI1_MLUT_SAFELY_GATED`) while blocking `RAW16 + HDMI MLUT` bake conflicts and rejecting all persistent writes to `/dev/cnflasha*`, `/dev/nflasha*`, `p2:/Backup.bin`, `p2:/psd.bin`, `Jiritsu`, and `/dev/mmcblk0*`.

---

## 5. Owned File Inventory (6 Files) / 本阶段交付文件清单

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)
4. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md)
5. [`outputs/fx3-firmware-lab/tests/test_lut3d_cube_tetrahedral_and_sdi_hdmi.py`](../../outputs/fx3-firmware-lab/tests/test_lut3d_cube_tetrahedral_and_sdi_hdmi.py)
6. [`reports/2026-11-14-phase98-lut3d-tetrahedral-sdi-hdmi-auditor/README.md`](./README.md)
