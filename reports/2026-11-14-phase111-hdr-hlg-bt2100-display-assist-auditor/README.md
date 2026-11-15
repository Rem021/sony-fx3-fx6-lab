# Phase 111 — 21st Unified `fx3-firmware-lab` Auditor: ITU-R BT.2100 / ARIB STD-B67 HLG (`HLG1`/`HLG2`/`HLG3`/`HLG Live`/`HLG Natural` & `BT.2020` vs `BT.709`), Gamma Display Assist EVF/LCD Tone-Mapping Isolation, & CTA-861.3 HDMI HDR Dynamic Range and Mastering InfoFrame (`0x87`) Auditor (`hdr_hlg_bt2100_and_display_assist_auditor.py`)

- **Date / 日期**: 2026-11-14
- **Schema / 版本**: `fx3_firmware_lab_phase111_hdr_hlg_bt2100_assist_v1` (`111.0.0`)
- **CLI Subcommand / CLI 子命令**: `/usr/bin/python3 -B -m fx3_firmware_lab audit-hdr-hlg-assist [--clean-room] [--json]`
- **Strict Read-Only / 只读零突变约束**: `os.O_RDONLY` + `mmap.ACCESS_READ`, `persistent_emmc_writes_authorized = False`, `calibration_mutation_bytes = 0`, `emmc_mutation_bytes = 0`

---

## 1. Executive Summary / 核心摘要

Phase 111 integrates the **21st unified auditor** ([`hdr_hlg_bt2100_and_display_assist_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdr_hlg_bt2100_and_display_assist_auditor.py)) into `fx3-firmware-lab`, establishing end-to-end dual-mode (`LOCAL_DONOR_VERIFIED` + `CLEAN_ROOM_SYNTHETIC`) verification across FX3 `v7.02` and FX6 `v6.01` for:

1. **Pillar 1 — ITU-R BT.2100 / ARIB STD-B67 Hybrid Log-Gamma OETF & Sony `HLG1` / `HLG2` / `HLG3` / `HLG Live` / `HLG Natural` Curve Auditor**
2. **Pillar 2 — Gamma Display Assist (`S-Log3 -> ITU709(800%)`, `S-Log2 -> 709(800%)`, `HLG(BT.2020) -> 709`, `HLG(709) -> 709`) EVF/LCD Viewfinder Tone-Mapping Isolation**
3. **Pillar 3 — CTA-861.3 / HDMI 2.0b+ Static Metadata Type 1 HDR InfoFrame (`0x87`) Synthesizer & Checksum Guard**
4. **Pillar 4 — `NonRealTimeMeta v2.20` XML `<CaptureGammaEquation>` / `<ColorPrimaries>` 16-Byte SMPTE UL Parity & Zero-Calibration-Mutation Proof**

第 111 阶段向 `fx3-firmware-lab` 集成第 **21** 个统一审计器 [`hdr_hlg_bt2100_and_display_assist_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdr_hlg_bt2100_and_display_assist_auditor.py)，在本地只读供体（`LOCAL_DONOR_VERIFIED`）与净室合成（`CLEAN_ROOM_SYNTHETIC`）双模式下全部通过验证，全套 **21 个审计器** 与 **591 项单元测试**（含本阶段新增 38 项双模式测试）在双模式下 **100% 绿灯**。

---

## 2. Observed Verification Metrics / 实测验证数据

| Metric / 指标 | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) | Gate / 门禁要求 |
| :--- | :--- | :--- | :--- |
| **21st Auditor Status** | `all_checks_passed = True` (`0` errors) | `all_checks_passed = True` (`0` errors) | 100% Pass |
| **21st Auditor Wall Runtime** | **`0.2221 s`** warm (`0.2277 s` cold) | **`0.0027 s`** warm (`0.0026 s` cold) | `< 0.35 s` local / `< 0.02 s` clean-room |
| **Report SHA-256 Digest** | `585933ba16b90c796b20dd5ae3994654b206986f82a9dd7f8533ce2ef7cbf96c` | `03d32f45fa3e772528448a511d52819541a08bbc4d29d1fd712d495127e5e131` | Deterministic |
| **`audit-all --json`** | **21 / 21 green** (`all_checks_passed = True`) | **21 / 21 green** (`all_checks_passed = True`) | 21 / 21 Auditors |
| **Phase 111 Unit Tests (`test_hdr_hlg_bt2100_and_display_assist.py`)** | **38 / 38 passed** (`0.525 s`) | **38 / 38 passed** (`0.339 s`) | `>= 34` dual-mode tests |
| **Full Lab Unit Suite (`unittest discover`)** | **591 / 591 passed** (`20.221 s`) | **591 / 591 passed** (`10.507 s`) | Zero failures |
| **`scripts/run_all_lab_tests.py --clean-only`** | `CLEAN (0.04s)` — ALL GREEN | `CLEAN (0.04s)` — ALL GREEN | Zero `.pyc` / binaries |
| **Calibration / eMMC Mutation** | `0 B` / `0 B` (`os.O_RDONLY`) | `0 B` / `0 B` | Strict zero-mutation |

---

## 3. Inspected Local Donor Artifacts (`os.O_RDONLY`) / 只读本地供体清单

| Artifact Key | Exact Role | Local Donor Size (Bytes) | Clean-Room Fixture Size (Bytes) | Verified Real Markers / Findings |
| :--- | :--- | ---: | ---: | :--- |
| `fx3_appfw` | FX3 `v7.02` `appFw.so` | `79,015,712` | `966` | `SETTING_PICTUREPROFILE_GAMMA_HLG{,1,2,3}`, `COLORMODE_BT2020/709`, `GAMMA_DISP_ASSIST_DISPLAY_ON/OFF`, `GAMMA_DISP_ASSIST_TYPE_{AUTO,SLOG3,SLOG2,HLG_BT2020,HLG_709}`, `VIDEO_COLOR_SPACE_BT2020` |
| `fx6_appfw` | FX6 `v6.01` `appFw.so` | `50,520,424` | `921` | `SELECT_LUT_HDR_HLG_{LIVE,NATURAL,MILD}`, `TARGET_DISPLAY_{HDR_HLG,SDR_BT_709}`, `VIEW_FINDER_HDR_DISPLAY_STATE_GAMUT_BT2020`, `BKID_APP_SETTING_GAMMA_DISP_ASSIST_DISPLAY` |
| `fx3_libmpr` | FX3 `libmpr.so` | `3,517,008` | `297` | `CaptureGammaEquation`, `CaptureColorPrimaries`, `rec2100-hlg`, `hlg-slog3ootf`, all 8 16-byte SMPTE ULs in `.rodata` |
| `fx6_libmpr` | FX6 `libmpr.so` | `28,921,824` | `421` | `MetaConverterImpl::ConvertCaptureGammaEquation`, `ConvertColorPrimaries`, `smpte2084`, `hlg-mildlook`, all 8 16-byte SMPTE ULs in `.rodata` |
| `fx3_cpapp` | FX3 `cpapp-b.bin` | `15,980,568` | `161` | `HLG`, `BT.2020`, `BT2020rgb`, `BT2020ycc`, `SET_GAMMA_DISP_ASSIST`, `MSG_ID_INFRABB_VIDEO_SET_GAMMA_DISP_ASSIST` |
| `fx6_cpapp` | FX6 `cpapp-b.bin` | `17,952,816` | `242` | Shared CP markers + `cpActGammaDisplayAssist`, `36cpActGammaDisplayAssistWidgetService`, `MonColorPrimaries` |
| `fx3_global_xdb` | FX3 `global.xdb` (`uxa\x07`) | `11,664` | `1,724` | `uxa\x07` container parsed read-only |
| `fx6_global_xdb` | FX6 `global.xdb` (`uxa\x07`) | `1,792` | `1,792` | `uxa\x07` container parsed read-only |
| `fx3_str_en` | FX3 English `ns=39` `.uxc` | `165,740` | `976` | `0x0000e1d5` (`"HDMI Resolution"`) |
| `fx3_str_en_g` | FX3 English `ns=3` `.uxc` | `69,600` | `2,824` | `0x00006531` (`"ITU709 Matrix"`), `0x00006538` (`"Use Gamma Display Assist instead of LUT..."`) |
| `fx6_str_en_1` | FX6 English `ns=1` `.uxc` | `118,208` | `9,496` | `0x00002018` (`"HLG_BT.2100"`), `0x000020b9` (`"BT.2020/HDR(HLG)"`), `0x00002109` (`"LUT 709(800)"`), `0x000021a3` (`"HLG Live"`), `0x000021a4` (`"HLG Natural"`), `0x00003247` (`"Gamma Display Assist"`) |
| `fx6_str_en_2` | FX6 English `ns=2` `.uxc` | `118,676` | `9,080` | `0x0000419d..419f` (`"Gamma Display Assist: Auto/HLG/S-Log3"`), `0x000042ea` (`"HLG→709(800%)"`), `0x0000515d..515f` (`"HDR(HLG1/2/3)"`) |

---

## 4. Technical Pillar Breakdown / 四大审计支柱详情

### Pillar 1 — ARIB STD-B67 / ITU-R BT.2100 HLG OETF & Sony Variants (`HLG1`/`HLG2`/`HLG3` + Gamut Guard)
- **Exact Piecewise ARIB STD-B67 HLG OETF (`verify_arib_b67_oetf_roundtrip`)**:
  - For $E \le 1/12$: $E' = \sqrt{3E}$; for $E > 1/12$: $E' = a \ln(12E - b) + c$ ($a = 0.17883277, b = 0.28466892, c = 0.55991073$).
  - Verified $C^0$ continuity error $= 4.73 \times 10^{-10}$, analytical $C^1$ slope $= 3.0$ ($0.0$ slope mismatch), max inverse roundtrip error $= 5.55 \times 10^{-16} < 10^{-10}$, strict monotonicity, and 10-bit legal landmarks (`64`, `502`, `940`).
- **Sony Cinema / Alpha HLG Curve Family (`sony_hlg_variant_oetf`)**:
  - Audits `HLG1` (`87%` max signal, ~`11.5` stops, NR priority), `HLG2` (`95%` max signal, ~`12.3` stops balanced), `HLG3` (`100%` max signal, ~`13.0` stops widest DR), and FX6 `HLG Live` / `HLG Natural` / `HLG Mild`.
- **Fail-Closed Gamut/Transfer Guard (`evaluate_hlg_gamut_transfer_contract`)**:
  - Blocks `BT.2020` recorded primaries tagged as `BT.709` without 3x3 chromaticity conversion (`47.11%` CIE xy gamut area collapse + broadcast NLE hue shift), blocks `BT.709` mis-tagged as `BT.2020`, blocks `S_LOG3` transfer mismatches, and blocks raw `HLG BT.2020` fed into `SDR_BT_709` targets without conversion.

### Pillar 2 — Gamma Display Assist EVF/LCD Isolation (`S-Log3 -> 709(800%)` & `HLG(BT.2020) -> 709`)
- **Viewfinder Preview & ITU-R BT.2087 Matrix (`compute_display_assist_preview_rgb`)**:
  - Resolves `AUTO` across `S_LOG3 -> SLOG3_TO_709_800` (`(0.41, 0.41, 0.41) -> (0.589828, 0.589828, 0.589828)`), `S_LOG2 -> SLOG2_TO_709_800`, `REC2100_HLG + BT.2020 -> HLG_BT2020_TO_709` (`(0.50, 0.50, 0.50) -> (0.606481, 0.606481, 0.606481)` via unit-row-sum BT.2087 3x3 matrix), and `REC2100_HLG + BT.709 -> HLG_709_TO_709`.
- **Double Tone-Map Prevention & Burn-In Firewall (`evaluate_gamma_display_assist_isolation`)**:
  - Defers Display Assist (`DEFERRED_TO_ACTIVE_MLUT`) when `lcd_evf_mlut_active=True`, and fails closed if LCD/EVF assist leaks into `XAVC` main clips (`BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_XAVC`) or `Clean-HDMI` (`BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_HDMI`) without explicit MLUT burn-in.

### Pillar 3 — CTA-861.3 / HDMI 2.0b+ Static Metadata Type 1 HDR InfoFrame (`0x87`) Synthesizer & Guard
- **30-Byte Packet Codec (`build_cta861_3_hdr_infoframe` / `decode_cta861_3_hdr_infoframe`)**:
  - Synthesizes `type=0x87, version=0x01, length=26`, checksum `(256 - sum) & 0xFF`, `Static_Metadata_Descriptor_ID=0`, `G/B/R/W` CIE chromaticities in `0.00002` units, and EOTF signaling:
    - `BT2100_HLG` (`0x03`, `csum=0x90`): `87011a9003003421aa9b9619fc08488a0839133d4240e8033200e8039001` -> Atomos Ninja V+ & SmallHD Cine 7 auto-switch to `HLG_BT2020_HDR`.
    - `SMPTE_ST2084_PQ` (`0x02`, `csum=0x91`): `87011a9102003421aa9b9619fc08488a0839133d4240e8033200e8039001` -> `PQ_ST2084_BT2020_HDR`.
    - `SDR_GAMMA` (`0x00`, `csum=0x1f`): `87011a1f0000983a30754c1db80b007d7440133d4240e8033200e8039001` -> `SDR_BT709`.
- **Fail-Closed HDMI Guards (`evaluate_hdmi_hdr_infoframe_handshake`)**:
  - Rejects corrupted checksums, `HLG` mis-signaled with `SDR` EOTF, `HLG BT.2020` paired with `BT709` AVI Colorimetry, and `HDMI RAW16` HDR InfoFrame conflicts.

### Pillar 4 — `NonRealTimeMeta v2.20` XML SMPTE UL Parity & Zero-Calibration-Mutation Proof
- **16-Byte SMPTE UL Parity (`synthesize_hlg_nrtm_xml` / `parse_and_verify_hlg_nrtm_xml`)**:
  - Cross-verifies all 8 SMPTE ULs present in FX3 and FX6 `libmpr.so` (`rec2100-hlg`, `smpte2084`, `rec709_transfer`, `s-log3`, `rec2020_primaries`, `rec709_primaries`, `s-gamut3`, `s-gamut3-cine`) against `NonRealTimeMeta v2.20` XML `<CaptureGammaEquation>` and `<CaptureColorPrimaries>`, blocking HLG/`BT.709` mismatch (unless compat opt-in) and UL tampering.
- **Zero Calibration / eMMC Mutation Firewall (`evaluate_hdr_calibration_write_guard`)**:
  - Permits volatile staging only (`/tmp/`, `ram://`, `memory://`) and blocks all persistent targets (`p2:/setting/psd.bin`, `defdet.bin`, `Backup.bin`, `p6:/tmp/jiritsu`, `p12:/cert`, `/dev/cnflasha0`, `/dev/nflasha*`, `/dev/mmcblk0p1`, `nvram://`), keeping `calibration_mutation_bytes = 0`, `emmc_mutation_bytes = 0`, and `persistent_emmc_writes_authorized = False`.

---

## 5. Owned File Inventory (7 Files) / 本阶段交付文件清单

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/hdr_hlg_bt2100_and_display_assist_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/hdr_hlg_bt2100_and_display_assist_auditor.py) (NEW 21st unified auditor)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) (export Phase 111 symbols)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (wire `audit-hdr-hlg-assist` CLI & 21st auditor in `run_audit_all()`)
4. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md) (document Phase 111 21st auditor)
5. [`outputs/fx3-firmware-lab/tests/test_hdr_hlg_bt2100_and_display_assist.py`](../../outputs/fx3-firmware-lab/tests/test_hdr_hlg_bt2100_and_display_assist.py) (NEW, 38 dual-mode unit tests)
6. [`outputs/fx3-firmware-lab/tests/test_c2pa_lens_shading_and_mc_fleet.py`](../../outputs/fx3-firmware-lab/tests/test_c2pa_lens_shading_and_mc_fleet.py) (coordinator-authorized forward-compatible `>= 20` auditor count check at line 207)
7. [`reports/2026-11-14-phase111-hdr-hlg-bt2100-display-assist-auditor/README.md`](./README.md) (NEW bilingual Phase 111 audit report)
