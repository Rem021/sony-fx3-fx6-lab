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

## Usage & Tests

```sh
# Emit deterministic JSON across all 3 auditors (Local Donor or Clean-Room)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room

# Run all 28 unit tests in Local Donor mode and forced Clean-Room mode
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
```
