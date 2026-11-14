# `fx3-firmware-lab` — Clean-Room `UFU`/`FDAT`/`UDTRFIRM`, `HAITA`/`BK4` & `.uxc`/CPU `LDEC` Auditor

Core clean-room firmware container auditor, `PRODUCT_MODEL_ALCIN_UUD` (FX3 v7.02) vs `PRODUCT_MODEL_CHAPLIN` (FX6 v6.01) `HAITA`/`BK4` differential analyzer, and hardware-free `.uxc`/`LDEC` CPU asset inspector.

## Clean-Room & BYOF Compliance

- **Zero Embedded Proprietary Keys**: This package contains **zero** Sony AES keys (such as `CXD90057_k8`) and **zero** vendor RSA private keys. Only public container magic bytes (`\x89UFU\r\n\x1a\n`, `FDAT`, `UDTRFIRM`, `SDM2` `8246` `2.00`), public mathematical test constants (`hashlib.sha256(b"").digest()[:16]`), 1024-byte `<HH` checksum verification, and optional caller-supplied BYOF callbacks are used.
- **Strictly `O_RDONLY` Donor Inspection**: All local donor ELF/`.uxc` reads open with `os.O_RDONLY` without mutating or copying any proprietary files into the repository.
- **Dual-Mode Execution**: Automatically uses verified local BYOF donors when present and falls back cleanly to deterministic synthetic fixtures under `FX3_FX6_FORCE_CLEAN_ROOM=1` or `--clean-room`.

## Modules

1. [`fx3_firmware_lab/ufu_container_auditor.py`](fx3_firmware_lab/ufu_container_auditor.py)
   - Validates `\x89UFU\r\n\x1a\n` envelopes and `FDAT` trailer geometry (`16B IV` + `256B RSA-2048 signature` = 272 B at `off + size`).
   - Enforces Model ID guard (`0x91030080` FX3 vs `0x91030082` FX3A -> `5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD`).
   - Audits 1024-byte `<HH` chunk framing (16-bit LE checksum + payload length / `0x8000` terminal flag).
   - Parses and SHA-256 verifies `UDTRFIRM` partition manifest entries and `SDM2` (`8246` `2.00`) 30-entry partition tables (`type=5, flag&1` -> AES-XTS-256 `/dev/cnflasha*`).
2. [`fx3_firmware_lab/haita_bk4_feature_analyzer.py`](fx3_firmware_lab/haita_bk4_feature_analyzer.py)
   - Fast `bytes.find` / byte-regex differential audit of FX3 v7.02 `appFw.so` (`9` active `PRODUCT_MODEL_*` classes centered on `PRODUCT_MODEL_ALCIN_UUD` enum `4` / idx `24` / `IMX510`, `13` `TYPE_MENU_ITEM_*` entries, `7,643` `*HAITA*` tokens) vs FX6 v6.01 `appFw.so` (`28` `PRODUCT_MODEL_*` classes including `PRODUCT_MODEL_CHAPLIN`, `5,534` `BKID_*` tokens, `IMAGER_SCANMODE_FF_5K_3_2` / `VIDEO_FORMAT_5016x3344P` / `SELECT_CODEC_X_OCN_LT` Open-Gate asymmetry).
   - Audits `BK4\0` Cinema Line NVRAM property contracts (`0x02cf1702` Shutter Angle Mode, `0x02cf1704` Shutter Angle Value, `0x02cf1443` Log Shooting / Cine EI, `0x02cf1453` Select LUT, `0x02cf1bf2` Anamorphic De-Squeeze, `0x02cf00d7` Movie Rec Aspect Open-Gate, `0x02cf0004` NTSC/PAL Popup) and proves `BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD` vs Stage-A/B RAM-shadow `BK4\0` (`flash_mutation_bytes = 0`).
3. [`fx3_firmware_lab/uxc_ldec_inspector.py`](fx3_firmware_lab/uxc_ldec_inspector.py)
   - Parses `uxd\x07` / `uxc\x07` containers (`image_00_169.uxc` 1,610 sprites / 22 nine-patch, `string_english_2.uxc` 5,915 strings, `string_english.uxc`, `color_cmn.uxc`, `lang_cmn.uxc`, `style_cmn.uxc`, and 62 sibling `.uxc` packs).
   - Implements bounded CPU-only Sony LDEC / LZ77 (`0x0F` raw + `0xF0` flag-byte/match streams, `((w + 15) & ~15)` aligned width) without `/dev/ldec`, plus `RGBA4444` / `RGBA8888` / `ARGB4444` / `A8` -> `ARGB8888` conversion parity.
4. [`fx3_firmware_lab/uxc_multilang_and_font_verifier.py`](fx3_firmware_lab/uxc_multilang_and_font_verifier.py)
   - Audits all **62** FX6 `.uxc` packs (`29` languages × `ns=1` `5,044` strings + `29` × `ns=2` `5,915` strings + `color_cmn` / `lang_cmn` / `style_cmn` + `image_00_169.uxc`) for strict UTF-8 validity and 1:1 `STRID` slot/`resid16` parity against English, plus FX3 v7.02 (`121` `.uxc` packs across `34` languages) cross-body isolation diff (`MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY`).
   - Parses OpenType/TrueType `cmap` format-4 and format-12 tables across `.ttf`/`.otf`/`.ttc` and Monotype `.ltt` linked font containers (`Sony_DI_Icons.ttf`, `UniversOTS-SJ_wIcon.ltt`, `HeiseiKakuGothW5-SJ_wIcon.ltt`, `MYingHeiC-GB18030-SJ_wIcon.ltt`, `MYingHeiC-Big5HKSCS-SJ_wIcon.ltt`, `MYingHeiC-KSX1001-SJ_wIcon.ltt`) to prove 100% standard Unicode glyph coverage for Simplified Chinese, Traditional Chinese, Japanese, and English.
   - Sweeps 100% of all `1,610` FX6 sprites (`51,972,736` decoded bytes) and FX3 image pack samples via pure-CPU `fast_decode_ldec_lz77` with deterministic SHA-256 verification.
5. [`fx3_firmware_lab/sensor_codec_compatibility_analyzer.py`](fx3_firmware_lab/sensor_codec_compatibility_analyzer.py)
   - Strictly `os.O_RDONLY` (`bytes.find`) & Clean-Room cross-body verifier across FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) and FX6 v6.01 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`).
   - **IMX510 Sensor & Dual Base ISO (`800 / 12800`) Matrix**: Verifies shared `IMX510` CP drivers (`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`, `4264x2408` effective), `4K DCI (4096x2160)`, `QFHD (3840x2160)`, `FHD (1920x1080)` up to `120p`/`240p` S&Q, `HDMI 16-bit RAW`, and negative proof that `5016x3344` (`IMAGER_SCANMODE_FF_5K_3_2` / `SELECT_CODEC_X_OCN_LT`) has `0` encoder hits in `libmpr.so` and `cpapp-b.bin`.
   - **MPR / Hardware Encoder Profile Matrix**: Proves `XAVC-I` (`MXF`) and `XAVC S-I` (`MP4`) share the exact same CXD90057 H.264 High422Intra (`AVC480_*_H422IP`) elementary bitstream hardware engine and `mpr::SetMovieRecParam` ABI in `libmpr.so`, diverging only at the container muxer (`libXavcMxf` vs `libXavcMp4`), alongside `XAVC-L`, `XAVC S`, and `XAVC HS` (`HEVC_3840_2160_M42210P` / `M10P`).
   - **Dual Media Slot & Video Output Boundary**: Verifies `Slot A / Slot B` (`SSA`/`SSB`) <-> `Slot 1 / Slot 2` CFexpress Type A + SDXC dual-slot parity (`SIMULTANEOUS_REC` / `RELAY_REC`) and confirms FX6-only `12G-SDI` (`PRM_FEATURE_MANAGER_sdi_output`, `MoniFpgaSdi_SetRegSDIOutFormat`) gracefully falls back to `HDMI` / `HDMI RAW` on FX3 without blocking recording.
6. [`fx3_firmware_lab/cube_lut_and_rtmd_verifier.py`](fx3_firmware_lab/cube_lut_and_rtmd_verifier.py)
   - **Anti-Crash `.cube` (`17^3` / `33^3`) Sanitizer & Trilinear `17^3 -> 33^3` Hardware Packer**: Parses Adobe/Iridas `.cube` files (`TITLE`, `DOMAIN_MIN`, `DOMAIN_MAX`, `LUT_3D_SIZE 17|33`, `LUT_3D_INPUT_RANGE`) while rejecting NaN/Inf, wrong voxel counts, `DOMAIN_MIN >= DOMAIN_MAX`, `LUT_1D_SIZE` mismatches, control chars / unsafe titles, and oversized files (`> 2 MiB` / `> 40,000` lines) that would overflow FX3 `P1` (`/dev/nflasha30`, `48.00 MiB` VFAT, 16-slot `User1..16` budget) or trigger the historical v6.00->v6.01 custom `.cube` parser crash. Performs exact trilinear `17^3 -> 33^3` (`35,937` voxels) upsampling + `U12.0` / `U16` (`215,622 B`) / `U8` (`107,812 B`) DMA packing (`S-Log3` identity ramp `<= 1 LSB`), `P11` 164-byte `mpr::SetLutData` / `0x0165` (36 B) / `0x0166` (10 B) descriptor framing, and `BK4` `0x02cf1453` + `0x02cf14a4..0x02cf14b3` slot-flag generation.
   - **Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) & `IMX510` IBIS Center-Lock Verifier**: Inspects FX3 v7.02 & FX6 v6.01 `appFw.so` / `libmpr.so` (`O_RDONLY`, with synthetic clean-room fallback) for `/dev/nflasha30`, `model_user_lut_files`, `mpr::SetLutData`, `KlvConverter` (`Rdd18KeyCameraUnit`, `UDAMSetGyroscopeValue`, `UDAMSetAccelerometerValue`), and SMPTE UL `06 0e 2b 34` markers; builds and verifies big-endian KLV `RTMD` packets carrying `IMX510` readout duration, Dual Base ISO (`800`/`12800`) & EI index, Shutter Angle (`180.0°`), Active 3D LUT name, and `0xE304` 5-Axis IBIS Center-Lock + Gyro/Accel telemetry for Catalyst Browse & Gyroflow coherence.

## Usage & Tests

```sh
# Emit deterministic JSON across all 6 auditors (Local Donor or Clean-Room)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-multilang --clean-room
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-sensor-codec
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-sensor-codec --clean-room
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-lut-rtmd
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-lut-rtmd --clean-room

# Run all 102 unit tests in Local Donor mode and forced Clean-Room mode (< 5s)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
```
