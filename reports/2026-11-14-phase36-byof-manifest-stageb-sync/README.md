# Phase 36 — Bilingual `docs/BYOF-REPRODUCTION.md` & `scripts/verify_byof_manifest.py` Stage-B (`P10` / `P12` / `.uxc` / CJK Font / Wireless) SHA-256 Sync

- **Date**: 2026-11-14
- **Branch**: `codex/h28-phase36-byof-manifest-sync`
- **Auditor**: Hydrogen-28
- **Status**: **PASSED** (`LOCAL_DONOR_VERIFIED` in `0.52s`, `CLEAN_ROOM_SCHEMA_VERIFIED` in `0.02s`)

## 1. Summary of Changes (Option B Architecture)

Following Coordinator architecture decision **Option (B)**, Stage-A (`§1.1–1.3`) baseline metrics (`en_entry_count=57`, `zh_entry_count=57`, `code_constants_checked=46`, `live_donor_files_verified=54`) remain backward-compatible for `outputs/fx6-on-fx3-closure/tests/test_closure.py` and `fx6_closure.hardware_readiness_packet`, while adding full Stage-B & Phase 19–35 cryptographic manifest coverage:

1. **Bilingual `docs/BYOF-REPRODUCTION.md` Upgrade (`§1.4` & `§2.5` & `§3`)**:
   - Added symmetrical English and Simplified Chinese **`§1.4`** tables containing **40** verified entries:
     - **4 deterministic Stage-A/B adapted in-memory outputs (`fx6_closure.patcher`)**:
       - `usr/lib/appFw.so (Stage-A P1+P4+P8 adapted)`: `50,520,424 B`, `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0`
       - `usr/lib/appFw.so (Stage-B P10-only adapted)`: `50,520,424 B`, `07a5405830becb169df4adc7d51eb19f53febe94e36b72de83e2bcad7081b84b`
       - `usr/lib/appFw.so (Stage-B P1+P4+P8+P10 adapted)`: `50,520,424 B`, `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`
       - `usr/lib/libWlanResource.so (Stage-B P12 adapted)`: `56,464 B`, `47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995`
     - **7 Phase 22/26 Wireless / Bluetooth / Network donors**: `libWlanResource.so` (`eb7785e0...`), `libWlanControlCommon.so`, `libInfraBluetooth.so`, `libInfraBluetoothCore.so`, `libResourceBluetooth.so`, `libbt-vendor.so`, `libInfraNetInitializer.so`.
     - **10 Phase 17/18/19/21/24/31 Peripheral, UIPC, Presentation & Codec donors**: `libInfraInput.so`, `libInfraTp.so`, `libInfraHotshoe.so`, `libgpe.so`, `AVBB_SCN_START_PANELEVF.so`, `AVBB_SCN_START_AUDIO.so`, `libosal_uipc.so`, `liblibra.so`, `libux_core.so`, `libmpr.so` (FX6 `6.01`).
     - **3 Cross-body FX3 `7.02` donors**: `appFw.so` (`545c5053...`), `libmpr.so` (`9aeef3b9...`), `string_english.uxc` (`204328c3...`).
     - **16 FX6 `.uxc` & Monotype `.ltt`/`.ttf` Font donors**: `image_00_169.uxc` (`f9bb82a2...`), `string_english.uxc`, `string_english_2.uxc`, `string_simplifiedchinese.uxc`, `string_simplifiedchinese_2.uxc` (`058c0906...`), `string_traditionalchinese_2.uxc`, `string_japanese_2.uxc`, `color_cmn.uxc`, `lang_cmn.uxc`, `style_cmn.uxc`, `MYingHeiC-GB18030-SJ_wIcon.ltt` (`3ed0c7dd...`), `MYingHeiC-Big5HKSCS-SJ_wIcon.ltt`, `HeiseiKakuGothW5-SJ_wIcon.ltt`, `UniversOTS-SJ_wIcon.ltt`, `MYingHeiC-KSX1001-SJ_wIcon.ltt`, `Sony_DI_Icons.ttf` (`058c1b07...`).
   - Added bilingual **`§2.5 Track 5 & Stage-B`** reproduction commands and updated **`§3`** auditor documentation.
   - Zero `stage<digits>` references anywhere in docs or relpath mappings (`zero_stage_reference_ok=True`).

2. **`scripts/verify_byof_manifest.py` Verifier Upgrade**:
   - Enforced strict `os.open(..., os.O_RDONLY)` + `os.fdopen(fd, "rb")` in `_stream_sha256_and_size` and `_read_bytes_rdonly` for all donor reads.
   - Extended `parse_byof_markdown` to parse `§1.1–1.4`.
   - Added `_load_expected_stage_b_constants` cross-checking **21** Stage-B / Phase 17–35 pinned constants across `fx6_closure.patcher`, `fx6_closure.wireless_fault_isolation_verifier`, `fx6_closure.peripheral_ux_compatibility_verifier`, `outputs/fx3-safety/readiness-20261025-msc.json`, and `outputs/fx6-native-presenter-closure/static-contracts-summary.json`.
   - Extended `ByofVerificationReport` with dedicated Stage-B fields (`stage_b_en_entry_count`, `stage_b_zh_entry_count`, `stage_b_en_zh_parity_ok`, `stage_b_constants_verified`, `stage_b_constants_ok`, `stage_b_live_donor_files_verified`, `stage_b_live_donor_unique_blobs_hashed`, `stage_b_outputs_verified`) and `.passed` property, requiring **both** Stage-A and Stage-B parity, constants, live donors (`54 + 36`), and in-memory `patcher.apply_patch_spec` builds (`4`) to pass 100%.

## 2. Verification Results

| Check | Mode | Outcome | Timing / Metrics |
| :--- | :--- | :--- | :--- |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py` | `LOCAL_DONOR_VERIFIED` | **PASS** (`rc=0`) | `0.52s` (`en=57 zh=57 constants=46 live=54`; `stage_b: en=40 zh=40 constants=21 live=36 outputs=4`) |
| `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py` | `CLEAN_ROOM_SCHEMA_VERIFIED` | **PASS** (`rc=0`) | `0.02s` (`en=57 zh=57 constants=46 live=0`; `stage_b: en=40 zh=40 constants=21 live=0 outputs=0`) |
| Tamper/Drift Negative Self-Check (`§1.4` 1-char SHA corruption) | `FAILED_CLEAN_ROOM_SCHEMA_VERIFIED` | **FAIL-CLOSED** | `.passed=False`, `stage_b_en_zh_parity_ok=False`, `stage_b_constants_ok=False` |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py -k byof` | Option (B) Compat | **PASS** (`rc=0`) | `1 test` passed in `0.53s` |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py -k readiness_packet` | Packet Parity | **PASS** (`rc=0`) | `2 tests` passed in `34.56s` |
| `make clean-audit` | Clean-Room Hygiene | **PASS** (`rc=0`) | Zero `.pyc`, `__pycache__`, or forbidden binary residue (`0.04s`) |

## 3. Clean-Room & Scope Compliance
- Edited/created strictly the 3 scoped files (`docs/BYOF-REPRODUCTION.md`, `scripts/verify_byof_manifest.py`, `reports/2026-11-14-phase36-byof-manifest-stageb-sync/README.md`).
- Zero `outputs/*`, `Makefile`, or `scripts/run_all_lab_tests.py` edits; zero `.pyc`/`__pycache__` residue; zero `qemu`/port `8768` interference.
