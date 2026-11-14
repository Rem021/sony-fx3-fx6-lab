# Phase 31 — `IMX510` Sensor Readout, Dual Base ISO (`800 / 12800`), HDMI RAW & `XAVC` Cross-Body Compatibility Matrix

> **Date**: `2026-11-14` · **Worker**: `Hydrogen-23` · **Branch**: `codex/h23-phase31-imx510-xavc-matrix`  
> **Verifier**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/sensor_codec_compatibility_analyzer.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/sensor_codec_compatibility_analyzer.py)  
> **Local Donor SHA-256**: `93acc1cca587578a4bf1a45db58bc9d7aa3188ab245d1829a02d8d2303659080` (`LOCAL_DONOR_VERIFIED`, `all_checks_passed = true`)

## 1. Executive Summary

Both `ILME-FX3` (v7.02) and `ILME-FX6` (v6.01) share Sony's **10.2 MP Full-Frame Back-Illuminated Exmor R CMOS `IMX510` sensor** (`4264x2408` effective, Dual Base ISO `800 / 12800` in S-Log3) and the `CXD90057` BIONZ XR hardware encode/ISP generation, while differing in external SDI hardware and container muxing (`MXF` `XAVC-I`/`XAVC-L` + 12G-SDI on FX6 vs `MP4` `XAVC S-I`/`XAVC S`/`XAVC HS` + HDMI 16-bit RAW on FX3).

Using strictly read-only (`os.O_RDONLY`) C-level `bytes.find` binary verification across all 6 donor artifacts (`fx3_appfw`: `79,015,712 B`, `fx6_appfw`: `50,520,424 B`, `fx3_libmpr`: `3,517,008 B`, `fx6_libmpr`: `28,921,824 B`, `fx3_cpapp`: `15,980,568 B`, `fx6_cpapp`: `17,952,816 B`) plus deterministic Clean-Room synthetic equivalents, Phase 31 proves:

1. **Sensor & Dual Base ISO Parity**: Both `cpapp-b.bin` images carry identical `IMX510` driver classes (`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`, `Camera6Imager21ImagerDrvParam_IMX510E`) and LiroSeq readout/ISO keys (`mov_size_req`, `mov_aspect_req`, `frate_req`, `e_set_img_frame_size`, `baseSensitivity`, `DCI4K`, `QFHD`, `FHD`, `RAW_OUTPUT_MODE`, `SLOG3`), while both `appFw.so` binaries carry Dual Base ISO `800 / 12800` (`EXPOSURE_INDEX_BASE_ISO_800_EI`, `EXPOSURE_INDEX_BASE_ISO_12800_EI`) and `120p`/`240p` S&Q markers.
2. **Unsupported `5016x3344` Open-Gate Negative Proof**: Although FX6 `appFw.so` contains `IMAGER_SCANMODE_FF_5K_3_2`, `VIDEO_FORMAT_5016x3344P`, and `SELECT_CODEC_X_OCN_LT` strings, **neither** `FX3 libmpr.so`, `FX6 libmpr.so`, `FX3 cpapp-b.bin`, nor `FX6 cpapp-b.bin` contains any `5016`, `3344`, `X_OCN`, or `XOCN` encoder backing (`0` hits across both `libmpr.so` images).
3. **MPR Hardware Encoder Engine Identity (`XAVC-I` vs `XAVC S-I`)**: Both `FX3 libmpr.so` and `FX6 libmpr.so` share the exact same 6 `mpr::movieRecParam` hardware encoder classes, 8 H.264 High422Intra (`H422IP`) profiles, 7 H.264 Long-GOP (`H422P`) profiles, and 3 HEVC (`M42210P` / `M10P`) profiles under `mpr::SetMovieRecParam(mpr::movieRecParam const&)`. Divergence occurs strictly at container muxing (`LOG_ID_LIBXAVCMXF_MUX` / `libXavcMxf::SetClipName` in FX6 vs `LOG_ID_LIBXAVCMP4` / `XavcsNamer` shared in both).
4. **Dual Media Slot & `12G-SDI` -> `HDMI` Non-Blocking Fallback**: Dual hybrid CFexpress Type A + SDXC slots (`SLOT_A`/`SLOT_B`/`No10_SSA`/`No116_SSB_INACTIVE_FRAME` in FX6 <-> `MEDIA_SLOT_1`/`MEDIA_SLOT_2` in FX3, both with `SIMULTANEOUS_REC` and `RELAY_REC`) map 1:1. FX6-only `12G-SDI` (`PRM_FEATURE_MANAGER_sdi_output`, `MoniFpgaSdi_SetRegSDIOutFormat`, `SDIC_ST01_SetMonModeInit`) is absent on FX3, where `HDMI` and `HDMI_RAW_OUTPUT_STATUS_CHANGED` (`RAW_OUTPUT_MODE`) remain active without blocking recording.

---

## 2. `IMX510` Readout, Dual Base ISO & Open-Gate Negative Proof Matrix

| Mode ID | Resolution / Aspect | Max FPS | FX3 Support | FX6 Support | Encoder Backed | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `IMX510_FF_4K_DCI` | `4096x2160` (`17:9`) | `60p` (`XAVC S-I` / `XAVC-I`) | Yes | Yes | Yes (`AVC480_4096_2160_H422IP`) | `FULL_PARITY` |
| `IMX510_FF_QFHD_4K` | `3840x2160` (`16:9`) | `120p` (S&Q / HFR crop) | Yes | Yes | Yes (`H422IP` / `M42210P`) | `FULL_PARITY` |
| `IMX510_FHD_1080P` | `1920x1080` (`16:9`) | `240p` (S&Q / HFR) | Yes | Yes | Yes (`AVC100/200_1920_1080_H422IP`, `H422P`) | `FULL_PARITY` |
| `IMX510_HDMI_16BIT_RAW` | `4096x2160` / `3840x2160` (`4264x2408` sensor) | `60p` | Yes | Yes | Yes (`RAW_OUTPUT_MODE`, `HDMI_RAW_OUTPUT_STATUS_CHANGED`) | `HDMI_RAW_PARITY` |
| `IMX510_OPEN_GATE_5K_3_2` | `5016x3344` (`3:2`) | `N/A` | **No** | **No** | **No** (`0` hits in `libmpr.so` & `cpapp-b.bin`) | `UNSUPPORTED_NEGATIVE_PROOF` |

- **Dual Base ISO (`800 / 12800`)**: Verified in FX3 `appFw.so` (`BASE_ISO_LOW_800`, `BASE_ISO_HIGH_12800`, `EXPOSURE_INDEX_BASE_ISO_800_EI`, `EXPOSURE_INDEX_BASE_ISO_12800_EI`, `SLOG3`) and FX6 `appFw.so` (`BASE_ISO_LOW`, `BASE_ISO_HIGH`, `800EI`, `12800EI`, `EXPOSURE_INDEX_BASE_ISO_800_EI`, `EXPOSURE_INDEX_BASE_ISO_12800_EI`, `S-Log3`).

---

## 3. `libmpr.so` & `appFw.so` Hardware Encoder Profile Matrix

Shared `libmpr.so` symbols present in **both** FX3 v7.02 and FX6 v6.01:
- **Core API**: `_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE`, `_ZN3mpr28SetMediaProfileClipInfoParamE...`, `_ZN3mpr32SetMediaProfileTakeMaterialParamE...`, `_ZN5MprIf13SetMediaTitleE...`, `_ZN5MprIf22SetMediaSizeMarginSyncEmj`.
- **`movieRecParam` Classes (6/6 identical)**: `AVC_Intra_4K`, `AVC_Intra_FHD`, `AVC_Long_4K`, `AVC_Long_FHD`, `HEVC_Long_4K`, `HEVC_Long_8K`.
- **H.264 High422Intra (`H422IP`) Profiles (8/8 identical)**: `AVC480_4096_2160_H422IP`, `AVC480CBG_4096_2160_H422IP`, `AVC480_3840_2160_H422IP`, `AVC480CBG_3840_2160_H422IP`, `AVCCBG_4096_2160_H422IP`, `AVCCBG_3840_2160_H422IP`, `AVC100_1920_1080_H422IP`, `AVC200CBG_1920_1080_H422IP`.
- **H.264 Long-GOP (`H422P`) Profiles (7/7 identical)**: `AVC280_3840_2160_H422P`, `AVC200_3840_2160_H422P`, `AVC140_3840_2160_H422P`, `AVC100_3840_2160_H422P`, `AVC50_1920_1080_H422P`, `AVC35_1920_1080_H422P`, `AVC25_1920_1080_H422P`.
- **HEVC (`M42210P` / `M10P`) Profiles (3/3 identical)**: `HEVC_3840_2160_M42210P`, `HEVC_3840_2160_M10P`, `HEVC_Proxy_1920_1080_M10P`.

| Codec | Container | Bitstream Engine | FX6 | FX3 | Shared HW Engine | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `XAVC-I` | `MXF` | H.264 High422Intra (`H422IP`) | Yes | No (MXF muxer FX6-only) | **Yes** | `SHARED_HW_ENGINE_MXF_MUX_FX6_ONLY` |
| `XAVC S-I` | `MP4` | H.264 High422Intra (`H422IP`) | Yes | Yes | **Yes** | `FULLY_SHARED_BITSTREAM_AND_MP4` |
| `XAVC-L` | `MXF` | H.264 Long-GOP (`H422P`) | Yes | No (MXF muxer FX6-only) | **Yes** | `SHARED_HW_ENGINE_MXF_MUX_FX6_ONLY` |
| `XAVC S` | `MP4` | H.264 Long-GOP (`H422P`) | Yes | Yes | **Yes** | `FULLY_SHARED_BITSTREAM_AND_MP4` |
| `XAVC HS` | `MP4` | HEVC (`M42210P` / `M10P`) | Yes | Yes | **Yes** | `FULLY_SHARED_BITSTREAM_AND_MP4` |
| `X-OCN LT` | `N/A` | None | No | No | **No** | `UNSUPPORTED_ENCODER_ABSENT_BOTH_BODIES` |

---

## 4. Dual Media Slot (`Slot A / Slot B`) & Video Output (`HDMI` vs `12G-SDI`) Boundary

- **Dual CFexpress Type A / SDXC Slot Parity (`DUAL_CFEXPRESS_TYPE_A_SDXC_PARITY_VERIFIED`)**:
  - FX6 `appFw.so` (`MEDIA_SLOT_1`, `MEDIA_SLOT_2`, `SLOT_A`, `SLOT_B`, `No10_SSA`, `No117_SSA_INACTIVE_FRAME`, `No116_SSB_INACTIVE_FRAME`, `SIMULTANEOUS_REC`, `RELAY_REC`) and FX6 `libmpr.so` (`Slot1`, `SlotA`, `SlotB`, `SDXC`, `isSDcardMediaType`, `pmaplSlot2Idx`) map cleanly to FX3's physical dual CFexpress Type A / SDXC bays (`MEDIA_SLOT_1`, `MEDIA_SLOT_2`, `SIMULTANEOUS_REC`, `RELAY_REC`).
- **Video Output Boundary (`SDI_ABSENT_GRACEFUL_HDMI_FALLBACK_NON_BLOCKING`)**:
  - `12G-SDI` control (`PRM_FEATURE_MANAGER_sdi_output`, `OUTPUT_SDI1`, `OUTPUT_SDI_SUPER`, `OUTPUT_SDI_HDMI_STOPPED_VIA_BOOT`, `BKID_APP_SETTING_OUTPUT_FORMAT_SDI_HDMI`) and CP FPGA SDI drivers (`MoniFpgaSdi_SetRegSDIOutFormat`, `MoniFpga_StartStopSDI`, `SDIC_ST01_SetMonModeInit`, `SDIC_ST04_SetModeMonOut`) are strictly isolated to FX6 (`0` hits in FX3 `appFw.so` and `cpapp-b.bin`).
  - Meanwhile, `HDMI`, `RAW_OUTPUT_MODE`, and `HDMI_RAW_OUTPUT_STATUS_CHANGED` are verified present in both bodies, confirming FX6 AP stacks fall back gracefully to `HDMI` / `HDMI 16-bit RAW` on FX3 without blocking recording.

---

## 5. Verification Commands & Results

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` -> **75 tests passed in 3.849s** (`LOCAL_DONOR_VERIFIED`).
- `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` -> **75 tests passed in 0.397s** (`CLEAN_ROOM_SYNTHETIC_VERIFIED`).
- `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` (`make clean-audit`) -> Verified clean.
