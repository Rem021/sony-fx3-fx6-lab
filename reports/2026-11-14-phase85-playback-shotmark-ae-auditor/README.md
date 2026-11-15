# Milestone Phase 85 Report — 16th Unified Firmware-Lab Auditor: Playback/Thumbnail Presenter, `ShotMark1 / ShotMark2` (`EssenceMark` XML) & `Push Auto Iris / AE Shift`

- **Date**: `2026-11-14`
- **Milestone**: Phase 85 (`PHASE_85_SCHEMA = "fx3_firmware_lab_phase85_playback_shotmark_ae_v1"`, `PHASE_85_VERSION = "85.0.0"`)
- **Live Safety Redlines Verified**:
  - `o_rdonly_enforced = True` (`os.O_RDONLY` + `mmap.ACCESS_READ` across all 14 donor artifacts)
  - `persistent_emmc_writes_authorized = False`
  - `internal_emmc_format_possible = False`
  - `calibration_mutation_bytes = 0`
  - `p4_nd_motor_fault_attempts = 0`
  - Zero proprietary keys, binaries, or `.pyc` files committed; live port `8768` untouched.

---

## 1. Deliverables Built & Wired

1. **16th Unified Firmware-Lab Auditor**:
   - [`outputs/fx3-firmware-lab/fx3_firmware_lab/playback_shotmark_and_ae_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/playback_shotmark_and_ae_auditor.py)
   - Wired into [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) and [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-playback-shotmark-ae [--clean-room] [--json]`, plus `playback_shotmark_and_ae_audit` as the **16th auditor** in `run_audit_all()`).
   - Documented in [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md).
2. **34 Fast Dual-Mode Unit Tests**:
   - [`outputs/fx3-firmware-lab/tests/test_playback_shotmark_and_ae.py`](../../outputs/fx3-firmware-lab/tests/test_playback_shotmark_and_ae.py)

---

## 2. Four-Pillar Engineering Verification

| Pillar | Scope Audited | Observed Donor & Clean-Room Invariants |
|---|---|---|
| **Pillar 1: Playback / Thumbnail Presenter (`icx1295`) & Internal `p1` Media Delete/Format Firewall** | FX3 `v7.02` & FX6 `v6.01` `appFw.so`, `libmpr.so`, `cpapp-b.bin`, `global.xdb`, and `.uxc` string packs | Verifies `EID_PLAYBACK`, `EVENT_FUNC_PROTECT_ON/OFF`, `EXECUTE_PLAYBACK_FUNCTION_AFTER_PLAYBACK_DELETE`, `THUMBNAIL_*`, `Cue/Review` shuttle speeds (`1x, 2x, 5x, 15x` forward/reverse), Clip Protect (`Lock`), and Media Format target arbitration. Strictly isolates internal eMMC `p1` (`/dev/mmcblk0p1`) and boot/calibration flash (`/dev/mmcblk0*`, `/dev/nflasha*`, `/dev/cnflasha*`, `p1:/`, `p2:/`, `p6:/`) from `Delete Clip` and `Format Media` (`BLOCKED_INTERNAL_EMMC_FORMAT_OR_DELETE`, `internal_emmc_format_possible = False`), permitting only external `Slot A` / `Slot B` CFexpress Type A & SDXC UHS-II (`/dev/mmcblk1p1`, `/dev/mmcblk2p1`, `/dev/nvme*`) when write-unprotected. |
| **Pillar 2: Cinema Line `Shot Mark 1 / 2` (`_ShotMark1`, `_ShotMark2`, `OK / KEEP`) & `EssenceMark` XML Verifier** | Live `IN_REC` and `IN_PLAY` ShotMark registry (`0..100` marks/clip) + Sony `NonRealTimeMeta v2.20` `<KlvPacketTable>` / `<EssenceMark>` XML | Proves frame-indexed insertion/removal of `ShotMark1` (`_ShotMark1`), `ShotMark2` (`_ShotMark2`), `OK` (`_OK`), and `KEEP` (`_KEEP`) marks, enforces duplicate/capacity (`MAX_SHOT_MARKS_PER_CLIP = 100`) and frame-bounds validation, and performs lossless XML serialization/round-trip (`start="<frame>"`, SMPTE timecode, KLV Universal Key `060E2B34010101050102010201000000`, `Resolve` / `Premiere` / `Catalyst` interoperability) across all 5 Cinema framerates (`23.98p / 24.00p / 25.00p / 29.97p / 59.94p`). |
| **Pillar 3: `Push Auto Iris`, `AE Shift (-2.0..+2.0 EV)`, Photometry & `P4` Auto-ND Redirection** | FX3/FX6 `appFw.so`, `libInfraLensCommunicator.so` (`14,544 B` identical ABI), `libmpr.so`, `.uxc` string packs | Proves under `Cine EI` (locked Base ISO `800`/`12800` and locked `180.0°` Shutter Angle) that FX6 `AUTO_ND` / `PUSH_AUTO_ND` routes cleanly on FX3 (`has_internal_variable_nd = False`) to E-Mount **`Push Auto Iris`** (`1/8`-stop smooth aperture servo via `libInfraLensCommunicator.so`) with **`p4_nd_motor_fault_attempts = 0`**, while preserving `AE Shift` bounds (`-2.0..+2.0 EV`), all 5 metering modes (`MULTI`, `CENTER`, `SPOT`, `ENTIRE_SCREEN_AVG`, `HIGHLIGHT`), `94.0% IRE` `S-Log3` Highlight anti-clip protection, and `Face/Eye Priority in Multi Metering` (`EVENT_FUNC_FACE_DETECTION_IN_MULTI_ON` / `FACE_DETECTION_IN_MULTI_VALUE_ON`). |
| **Pillar 4: Zero Calibration / Zero NVRAM Mutation Proof** | Volatile `/tmp/` & `ram://` overlays vs persistent eMMC/NVRAM calibration partitions | Verifies `calibration_mutation_bytes = 0`, `internal_emmc_format_possible = False`, and `persistent_emmc_writes_authorized = False`, permitting volatile RAM shadow state while rejecting persistent eMMC/calibration writes (`BLOCKED_PERSISTENT_EMMC_OR_CALIBRATION_WRITE`). |

---

## 3. Observed Donor Artifacts, Determinism Hashes & Verification Runs

### 14 Verified `os.O_RDONLY` Donor Artifacts (`LOCAL_DONOR_VERIFIED`)
- `fx3_appfw`: `79,015,712 B` | `fx6_appfw`: `50,520,424 B`
- `fx3_libmpr`: `3,517,008 B` | `fx6_libmpr`: `28,921,824 B`
- `fx3_cpapp`: `15,980,568 B` | `fx6_cpapp`: `17,952,816 B`
- `fx3_lens_comm`: `14,544 B` | `fx6_lens_comm`: `14,544 B`
- `fx3_global_xdb`: `11,664 B` | `fx6_global_xdb`: `1,792 B`
- `fx3_str_en`: `165,740 B` | `fx3_str_en_g`: `69,600 B`
- `fx6_str_en_1`: `118,208 B` | `fx6_str_en_2`: `118,676 B`

### Execution Benchmarks & Deterministic `report_sha256`
- `analyze_playback_shotmark_and_ae()` (Local Donor mode): **`0.2455s`** (`< 0.5s` target), `all_checks_passed = True`, `report_sha256 = 5a0189074481cdc5aa4ec705f5f938b38422e0e314c77448998766892e3916e2`
- `analyze_playback_shotmark_and_ae(clean_room=True)`: **`0.0032s`**, `all_checks_passed = True`, `report_sha256 = c6b1b88831b30d7ce73ff327886eb0f5a130dcc1e23b3683fa670b258df1a556`
- `run_audit_all()` across all **16 unified auditors**:
  - Local Donor mode: **`7.4877s`**, `all_checks_passed = True`
  - Clean-Room mode: **`0.0335s`**, `all_checks_passed = True`

### Test & Hygiene Commands Executed (All Passing)
1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_playback_shotmark_and_ae.py -v` -> **`Ran 34 tests in 1.060s` (`OK`)**
2. `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_playback_shotmark_and_ae.py -v` -> **`Ran 34 tests in 0.565s` (`OK`)**
3. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v` -> **`Ran 403 tests in 13.506s` (`OK`)**
4. `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v` -> **`Ran 403 tests in 5.847s` (`OK`)**
5. `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> **`CLEAN (0.20s)` / `ALL GREEN in 0.20s`**
