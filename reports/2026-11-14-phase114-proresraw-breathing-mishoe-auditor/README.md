# Phase 114 — 22nd Unified `fx3-firmware-lab` Auditor: External Atomos/Blackmagic ProRes RAW / BRAW 16-Bit Linear -> 12-Bit Log Metadata Handshake, Focus-Breathing Dynamic FOV Crop LUTs, & MI-Shoe I2S 48kHz Audio Master-Clock PLL Drift Auditor (`hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py`)

- **Date / 日期**: 2026-11-14
- **Schema / 版本**: `fx3_firmware_lab_phase114_proresraw_breathing_mishoe_v1` (`114.0.0`)
- **CLI Subcommand / CLI 子命令**: `/usr/bin/python3 -B -m fx3_firmware_lab audit-proresraw-breathing-mishoe [--clean-room] [--json]`
- **Strict Read-Only / 只读零突变约束**: `os.O_RDONLY` + `mmap.ACCESS_READ`, `persistent_emmc_writes_authorized = False`, `ob_clamp_calibration_mutation_bytes = 0`, `emmc_mutation_bytes = 0`

---

## 1. Executive Summary / 核心摘要

Phase 114 integrates the **22nd unified auditor** ([`hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py)) into `fx3-firmware-lab`, establishing end-to-end dual-mode (`LOCAL_DONOR_VERIFIED` + `CLEAN_ROOM_SYNTHETIC`) verification across FX3 `v7.02` and FX6 `v6.01` for:

1. **Pillar 1 — 16-Bit Scene-Linear Sensor RAW -> 12-Bit Non-Linear HDMI RAW Packing & Atomos ProRes RAW / Blackmagic BRAW Metadata Handshake**
2. **Pillar 2 — Focus-Breathing Compensation Dynamic FOV Crop (`1.000x..1.125x`) vs HDMI RAW / S&Q 120p / Unchipped Manual Lens Mutual-Exclusion Guard**
3. **Pillar 3 — 24-Pin MI-Shoe Digital Audio `48.000 kHz` I2S Master-Clock PLL (`29.97p` `1602,1601,1602,1601,1602` / `59.94p` `800.8`) & 6-Hour Lip-Sync Drift Firewall**
4. **Pillar 4 — Per-Body Factory OB-Clamp (`2048 ADU` -> `S-Log3 95`) / Black-Level Pedestal Read-Only Preservation Proof**

第 114 阶段向 `fx3-firmware-lab` 集成第 **22** 个统一审计器 [`hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py)，在本地只读供体（`LOCAL_DONOR_VERIFIED`）与净室合成（`CLEAN_ROOM_SYNTHETIC`）双模式下全部通过验证，全套 **22 个审计器**与 **631 项单元测试**（含本阶段新增 40 项双模式测试）在双模式下 **100% 绿灯**。

---

## 2. Observed Verification Metrics / 实测验证数据

| Metric / 指标 | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) | Gate / 门禁要求 |
| :--- | :--- | :--- | :--- |
| **22nd Auditor Status** | `all_checks_passed = True` (`0` errors) | `all_checks_passed = True` (`0` errors) | 100% Pass |
| **22nd Auditor Wall Runtime** | **`0.2249 s`** warm (`0.2327 s` cold) | **`0.0095 s`** warm (`0.0095 s` cold) | `< 0.35 s` local / `< 0.02 s` clean-room |
| **Report SHA-256 Digest** | `1c0c3fe2da699fdb8f31b3a17ce41b0baa455161664eeb348eb4e02524a770ee` | `a0a04e8acd64c103d54e529b639a77734c7bb8ca8e3d6ea295606647da2efc42` | Deterministic |
| **`audit-all --json`** | **22 / 22 green** (`all_checks_passed = True`) | **22 / 22 green** (`all_checks_passed = True`) | 22 / 22 Auditors |
| **Phase 114 Unit Tests (`test_hdmi_raw_prores_breathing_and_mishoe_clock.py`)** | **40 / 40 passed** (`0.876 s`) | **40 / 40 passed** (`0.471 s`) | `>= 36` dual-mode tests |
| **Full Lab Unit Suite (`unittest discover`)** | **631 / 631 passed** (`20.339 s`) | **631 / 631 passed** (`11.095 s`) | Zero failures |
| **`scripts/run_all_lab_tests.py --clean-only`** | `CLEAN (0.04s)` — ALL GREEN | `CLEAN (0.04s)` — ALL GREEN | Zero `.pyc` / binaries |
| **OB-Clamp / eMMC Mutation** | `0 B` / `0 B` (`os.O_RDONLY`) | `0 B` / `0 B` | Strict zero-mutation |

---

## 3. Inspected Local Donor Artifacts (`os.O_RDONLY`) / 只读本地供体清单

| Artifact Key | Exact Role | Local Donor Size (Bytes) | Clean-Room Fixture Size (Bytes) | Verified Real Markers / Findings |
| :--- | :--- | ---: | ---: | :--- |
| `fx3_appfw` | FX3 `v7.02` `appFw.so` | `79,015,712` | `677` | `RAW_OUTPUT_RESTRICTION_{60P,24_00P,NOT_SET}`, `PID_SET_BREATHING_CORRECTION`, `NID_BREATHING_CORRECTION_LENS_TYPE`, `i2s_48k_24bit_{4ch,2ch}:`, `EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON`, `EVENT_REMOTE_PICTURE_PROFILE_BLACK_LEVEL` |
| `fx6_appfw` | FX6 `v6.01` `appFw.so` | `50,520,424` | `552` | `convert_MODE_ID_RAW_OUTPUT_FORMAT_INDEX`, `INTERNAL_REC_RAW_OUT_RAW_HDMI_ONLY`, `SELECT_CODEC_RAW_OUT_ONLY`, `BREATHING_CORRECTION_LENS_TYPE_{SUPPORT,NOT_SUPPORT}`, `INFRA_HOTSHOE_UIPC_SHOEINFO_EVT`, `APC_LPCM_24BIT_48KHZ`, `PID_SET_BLACK_LEVEL` |
| `fx3_libmpr` | FX3 `libmpr.so` | `3,517,008` | `210` | `_ZN3mpr12KlvConverter31UDAMSetBreathingCorrectionValueE`, `_ZN3mpr12KlvConverter36ExecuteSerialize_BreathingCorrectionE...` |
| `fx6_libmpr` | FX6 `libmpr.so` | `28,921,824` | `419` | `UDAMSetBreathingCorrectionValue`, `BreathingCorrection_{BreathingCorrectionApplied,MinimumBreathingScaleRatio,MaximumBreathingScaleRatio}`, `muxQtProResComponentBufferConnect`, `muxMxfRtmetaBufferBlackLevelWrite` |
| `fx3_cpapp` | FX3 `cpapp-b.bin` | `15,980,568` | `466` | `DevHdmiRawMetaConverter`, `DevHdmiRawMetaConverterAtomos`, `DevHdmiRawMetaConverterBlackmagicDesign`, `MOVIE_RAW_OUTPUT_MODE`, `SET_BREATHING_CORRECTION`, `MSGQ_GID_HOTSHOE_INFRA1`, `GENLOCK_CID_PLLLOCK`, `/setting/defdet.bin`, `MasterBlackLevelMeta`, `I2S_SD0_MUS_OSEL`, `PP_BlackLevel` |
| `fx6_cpapp` | FX6 `cpapp-b.bin` | `17,952,816` | `485` | Shared CP markers + `i2s_48k_24bit_4ch`, `GetBlackLevelOffset_BeforeGamma` |
| `fx6_hotshoe` | FX6 `libInfraHotshoe.so` | `47,808` | `206` | `INFRA_HOTSHOE_UIPC_SHOEINFO_EVT`, `SETCTRL_BCK_LRCK`, `SETSHOE_PWR_ON`, `SETSHOE_LOGIC_PWR_ON` |
| `fx3_global_xdb` | FX3 `global.xdb` (`uxa\x07`) | `11,664` | `1,724` | `uxa\x07` container parsed read-only |
| `fx6_global_xdb` | FX6 `global.xdb` (`uxa\x07`) | `1,792` | `1,792` | `uxa\x07` container parsed read-only |
| `fx3_str_en` | FX3 English `ns=39` `.uxc` | `165,740` | `4,096` | `0x0004e7de` (`"Invalid during RAW movies output over HDMI."`) |
| `fx3_str_en_g` | FX3 English `ns=3` `.uxc` | `69,600` | `2,904` | `0x0000603e` (`"Connect to the device that supports\nRAW movies output of camera."`), `0x0000642a` (`"External Output"`), `0x0000656c` (`"Crop: HDMI"`) |
| `fx6_str_en_1` | FX6 English `ns=1` `.uxc` | `118,208` | `9,736` | `0x0000218d` (`"RAW Output Format"`), `0x000023ce` (`"RAW Output Control Status"`), `0x0000250d` (`"Breathing Compensation"`), `0x0000250e` (`"Breathing Comp."`), `0x000032bc` (`"4ch/48kHz/24bit"`) |
| `fx6_str_en_2` | FX6 English `ns=2` `.uxc` | `118,676` | `7,920` | `0x00004356` (`"ProRes"`), `0x00004f5c` (`"RAW Output Format"`) |

---

## 4. Technical Pillar Breakdown / 四大审计支柱详情

### Pillar 1 — 16-Bit Linear -> 12-Bit Log HDMI RAW Packing & ProRes RAW / BRAW Metadata Handshake
- **Piecewise Shadow-Toe Log Compander (`verify_raw16_to_raw12_dynamic_range`)**:
  - Uses $C^1$-smooth breakpoint $x_b = 1/128$ (`code16 = 512`), $y_b = 1 / (1 + \ln 128) = 0.17088088$ (`code12 = 700`), yielding $1.367\times$ shadow-toe code gain so **all 513 shadow codes `[0..512]` map 1:1 injectively** without shadow posterization.
  - Verified $C^0$ continuity error $= 2.19 \times 10^{-8}$, $C^1$ slope error $= 1.40 \times 10^{-4}$, strict monotonicity across all `65,536` 16-bit codes, max relative quantization error above code 64 $= 0.000976 < 0.01$, and **`15.0` stops** effective dynamic range (`>= 14.5` stops) at nominal 2 ADU sensor noise floor.
- **56-Byte Sony HDMI RAW Vendor Metadata Packet (`build_hdmi_raw_metadata_packet` / `decode_hdmi_raw_metadata_packet`)**:
  - Encodes `WhiteBalanceKelvin`, `Tint`, `ISO_Base_800_12800` (`640/800/12800`), `ExposureIndex`, `4264x2408` sensor active area vs `4240x2385` metadata crop, unit-row-sum `S-Gamut3.Cine` Q13 3x3 matrix, and CRC-32 (`ATOMOS_PRORES_RAW`: `534f4e59...1cd7c113`; `BLACKMAGIC_BRAW`: `534f4e59...ba9fb96d`).
  - Correctly distinguishes Atomos ProRes RAW (`wb_iso_unlocked_in_nle = True`) vs Blackmagic BRAW on FX3 HDMI (`wb_iso_locked_in_resolve_braw = True`) and fails closed on `MLUT` burn-in, `HDMI Info. Display` OSD contamination, Log Shooting Off, S&Q conflict, unsupported FPS, and CRC-32 tampering.

### Pillar 2 — Focus-Breathing Compensation Dynamic FOV Crop vs HDMI RAW / S&Q 120p Guard
- **Dynamic Magnification Polynomial (`compute_breathing_fov_crop_factor`)**:
  - Evaluates focus-distance `u_mm` across `8` E-Mount GM/G lens profiles (`1.000x` at optical infinity up to `1.105x` on `SEL50F12GM` at MOD `400 mm` and `1.125x` max on `SEL70200GM2` at `400 mm`).
- **Mutual-Exclusion & Fail-Safe Identity Bypass (`evaluate_focus_breathing_guard`)**:
  - Automatically bypasses the ISP geometric resampler (`applied_crop_factor = 1.000`, `isp_geometric_resampler_bypassed = True`) whenever **HDMI 16-bit RAW** is active (`BYPASSED_FOR_HDMI_RAW_BAYER_STREAM`), **S&Q 120p+** is active (`BYPASSED_FOR_HFR_SQ_120P`), or an **unchipped manual lens**, teleconverter (`SEL14TC`/`SEL20TC`), or `0.57m-1.0m` macro ring is mounted, and rejects illegal forced ISP crop on HDMI RAW (`BLOCKED_BREATHING_CROP_ON_HDMI_RAW_ILLEGAL`).

### Pillar 3 — 24-Pin MI-Shoe Digital Audio `48.000 kHz` I2S PLL & 6-Hour Lip-Sync Drift Firewall
- **Fractional NTSC vs Integer Crystal Cadence (`evaluate_mishoe_i2s_clock_pll`)**:
  - Locks `48,000 Hz` 24-bit 4-ch I2S (`4,608,000 bps`) to the `CXD90057` `27.000 MHz / 1.001` video clock:
    - `29.97p` (`30000/1001`): exact 5-frame cadence `(1602, 1601, 1602, 1601, 1602)` (`1601.6` avg, `0.0125 ms` intra-cadence phase jitter, **`0.0 ms`** cumulative drift at 6h `21,600 s`).
    - `59.94p` (`60000/1001`): exact 5-frame cadence `(801, 801, 801, 801, 800)` (`800.8` avg, `0.0167 ms` jitter, **`0.0 ms`** drift at 6h).
    - `23.976p`: `2002` samples/frame; `24/25/50p`: `2000 / 1920 / 960` samples/frame (`0.0 ms` drift).
  - Blocks unlocked `1000 ppm` NTSC crystal slip (`21,578.422 ms` drift over 6h > `0.100 ms`), verifies `P11` (`0x91db059b` / `0x88000002`) hot-detach 2-ch internal-mic fallback, and enforces S&Q audio mute safety.

### Pillar 4 — Per-Body Factory OB-Clamp / Black-Level Pedestal Preservation Proof
- Verifies `IMX510_RAW16_OB_CLAMP_ADU = 2048` (`ob_clamp_post_roundtrip_adu = 2048`, `0 ADU` drift across 16->12->16 log companding) and `SLOG3_10BIT_BLACK_PEDESTAL = 95`, `FX3`/`FX6` `global.xdb` integrity, volatile RAM staging (`/tmp/`, `ram://`, `memory://`), and hard blocking of all persistent calibration/eMMC targets (`defdet.bin`, `psd.bin`, `Backup.bin`, `jiritsu`, `/dev/cnflasha*`, `/dev/nflasha*`, `/dev/mmcblk0*`) with **`ob_clamp_calibration_mutation_bytes = 0`**, **`emmc_mutation_bytes = 0`**, and **`persistent_emmc_writes_authorized = False`**.

---

## 5. Owned File Inventory (7 Files) / 本阶段交付文件清单

1. [`reports/2026-11-14-global-sony-wave12-proresraw-breathing-unbrick-intel/README.md`](../2026-11-14-global-sony-wave12-proresraw-breathing-unbrick-intel/README.md) (NEW bilingual Wave-12 live web intelligence report)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py) (NEW 22nd unified auditor)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) (export Phase 114 symbols)
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (wire `audit-proresraw-breathing-mishoe` CLI & 22nd auditor in `run_audit_all()`)
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md) (document Phase 114 22nd auditor)
6. [`outputs/fx3-firmware-lab/tests/test_hdmi_raw_prores_breathing_and_mishoe_clock.py`](../../outputs/fx3-firmware-lab/tests/test_hdmi_raw_prores_breathing_and_mishoe_clock.py) (NEW, 40 dual-mode unit tests)
7. [`reports/2026-11-14-phase114-proresraw-breathing-mishoe-auditor/README.md`](./README.md) (NEW bilingual Phase 114 audit report)
