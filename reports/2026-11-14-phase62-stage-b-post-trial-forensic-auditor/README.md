# Phase 62 — Stage-B `H0`-vs-`H2` Post-Trial Zero-Persistence Forensic Auditor (`stage_b_post_trial_auditor.py`)

## Summary

Phase 62 delivers [`stage_b_post_trial_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h56-phase62-stage-b-post-trial-forensic-auditor/outputs/fx6-on-fx3-closure/fx6_closure/stage_b_post_trial_auditor.py), upgrading post-trial forensic auditing from Stage-A (`stage_a_post_trial_auditor.py`, left untouched) to full **Stage-B (`P1..P12+Fan` + C2PA/Calibration + `exFAT` Media + `RP2040` Fixture + `BK4`/`WBI2`/`CP` Zero-Drift)** with a fast (`<1s`) deterministic 10-scenario anomaly classifier and fail-closed SHA-256 report verifier (`stage_b_post_trial_forensic_audit_v1` / `stage_b_post_trial_receipt_v1`).

### Hard-Locked Safety Redlines
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
- All donor and bundle files are opened strictly read-only via `os.open(..., os.O_RDONLY)` in 1 MiB streaming chunks; zero raw binary `bytes` reprs (`b'...'` / `b"..."`) are emitted.

---

## Forensic Audit Dimensions (`verify_stage_b_post_trial_zero_persistence`)

1. **Bit-for-Bit 16-Surface `H0` Pre-Trial vs `H2` Post-Reboot Differ**:
   - Validates both `h0_bundle_dir` and `h2_bundle_dir` via `verify_real_tier0_capture_bundle`, enforces distinct non-symlink capture directories, and verifies identical camera hardware identity (`model_id == "0x91030080"`, `body_serial`, 128-bit `emmc_cid`, and `camera_body_tag`).
   - Streams and diffs all **11 mandatory Tier-0 partition/calibration backups + 2 redline headers + 3 Stage-B forensic probes** (`16/16`):
     - `sector0` (`'8246'`, `'2.00'`, `sector0_mutation_bytes == 0`)
     - `p2:/setting` (`'BK4\0'` persistent NVRAM: `bk4_mutated_bytes == 0`, `boot_img` byte `+8 == 0x00`, zero `/setting/updater/mode*` residue, persistent Airplane-Mode keys `0x019e0012` / `0x0051000f` / `0x01a20002` + persistent `BK_LANG` `0x02cf019c` 100% unchanged vs `H0`, proving `/tmp/bk4_shadow` Airplane + CJK override left `0` persistent NVRAM bytes altered)
     - `p5:/wbi` (`'WBI2'` header: `wbi_mutation_bytes == 0`)
     - `p8:/cp` (`p8_tomco.txt` + `p8_cpapp_b.bin`: Stock-CP `cp_mutation_bytes == 0`)
2. **C2PA (`RQ_LIC.DAT`) & `SPACC cnflasha` / Factory Sensor & IBIS Gyro Calibration Zero-Drift Proof**:
   - Verifies 9 calibration/keystore surfaces (`p2_backup_bin`, `p2_psd_bin`, `p2_defdet_bin`, `p6_jiritsu`, `p12_cert`, `p18_lensfile`, `spi_nor_ddrtraining`, `c2pa_rq_lic`, `spacc_cnflasha`), enforcing `calibration_mutation_bytes == 0`, `c2pa_keystore_untouched == True`, `spacc_cnflasha_untouched == True`, and zero forbidden mounts/writes via `fx3_safety.master_16gate_preflight.verify_c2pa_and_factory_calibration_immutability`.
3. **`p1` VFAT One-Shot Boot-Counter & Rollback Capsule + `exFAT` Lab Media Cleanliness**:
   - Validates `p1` VFAT (`FAT12`/`FAT16`), `boot_attempts == 0`, `/tmp/mod_arm_once` unlinked, `p1` capsule SHA-256 + `REQUIRED_FSYNC_ORDER`, and `exFAT` boot checksum + `VolumeDirty == 0` + `MediaFailure == 0` + zero `.RSV` / `.CHK` files via `fx3_safety.exfat_media_integrity_guard`.
4. **`RP2040` Fixture + `serial_fault_detector_v2` + Thermal/Power Session Log Post-Mortem**:
   - Enforces `RP2040-Zero` `-DOPEN_DRAIN` `1.8V` `48000` baud isolation (`validate_rp2040_multiport_harness`), `serial_fault_detector_v2` `PASS` (`TIMER-IP` `<90s/220s`), peak `SoC_C < 90.0°C`, zero `00342260` (`WF-12`) wireless hangs, zero `0x100D` (`13S`) panics, `NP-FZ100 >= 80%`, and `USB-PD >= 27000 mW`.

---

## 10-Scenario Anomaly & Drift Classifier (`S01..S10`)

| Scenario ID | Injected Condition | Expected Classification | Fail-Closed Verdict |
| :---: | --- | --- | :---: |
| `S01_CLEAN_H0_EQ_H2_STAGE_B_SESSION` | Clean `H0 == H2` Stage-B session | `CLEAN_H0_EQ_H2_ZERO_PERSISTENCE` | `PASS` (`0 B` mutated) |
| `S02_BK4_PERSISTENT_AIRPLANE_LEAK` | `0x019e0012=0x00` + CJK `BK_LANG=0x19` leaked into `H2 p2_backup_bin.bin` | `ANOMALY_BK4_PERSISTENT_NVRAM_LEAK` | Rejected (`all_checks_passed=False`) |
| `S03_WBI2_HEADER_DRIFT` | 1-bit drift in `H2 p5_wbi_header.bin` (`WBI2`) | `ANOMALY_WBI2_HEADER_DRIFT` | Rejected (`wbi_mutation_bytes=1`) |
| `S04_CP_BYTE_MUTATION` | 1-bit mutation in `H2 p8_cpapp_b.bin` | `ANOMALY_CP_BYTE_MUTATION` | Rejected (`cp_mutation_bytes=1`) |
| `S05_C2PA_CALIBRATION_DIGEST_DRIFT` | 1-bit drift in `H2 c2pa_rq_lic.dat` (`RQ_LIC.DAT`) | `ANOMALY_C2PA_OR_CALIBRATION_DRIFT` | Rejected (`calibration_mutation_bytes=1`) |
| `S06_EXFAT_VOLUME_DIRTY_SET` | `exFAT VolumeFlags & 0x0002` (`VolumeDirty`) set | `ANOMALY_EXFAT_VOLUME_DIRTY` | Rejected (`exfat_media_clean=False`) |
| `S07_EXFAT_RSV_CLIP_LEFT_BEHIND` | Unfinalized `PRIVATE/M4ROOT/CLIP/C0001.RSV` on media card | `ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP` | Rejected (`exfat_media_clean=False`) |
| `S08_WF12_00342260_LOG_SIGNATURE` | `00342260` (`WF-12`) wireless hang in session serial log | `ANOMALY_WF12_00342260_HANG` | Rejected (`wf12_00342260_hang_detected=True`) |
| `S09_THERMAL_90C_EMERGENCY_TEARDOWN` | Peak `SoC_C = 91.5°C` (`>= 90°C`) emergency teardown receipt | `ANOMALY_THERMAL_RUNAWAY_TEARDOWN` | Rejected (`thermal_under_90c_ok=False`) |
| `S10_SECTOR0_TAMPER` | 1-bit tamper in `H2 sector0.bin` (`'8246'` partition table) | `ANOMALY_SECTOR0_TAMPER` | Rejected (`sector0_mutation_bytes=1`) |

---

## Deterministic Audit Digests & Performance

| Mode | Elapsed | Canonical `report_sha256` | Nominal `receipt_sha256` | Items & Scenarios |
| --- | :---: | --- | --- | :---: |
| `LOCAL_DONOR_O_RDONLY` | `0.720s` | `ecc5751ee8805264d937b48bf3d93309a395f311e7ed27a5600fbcbd10f4ef93` | `ce88773e06974c82a9fc0b86ee40393fbe5dcfa1709ed81905b27458013d42bb` | `16/16` items, `10/10` scenarios |
| `CLEAN_ROOM_SYNTHETIC` | `0.719s` | `1ad69d75caad0a9f81b4c1074ce4ca21bdb299fcc8b43bd66b8b700173fa1f95` | `2031114f62ee73096c5afde15350572561d9353d5c2064c858e615f89098e91b` | `16/16` items, `10/10` scenarios |

---

## Deliverables Owned & Modified

- `outputs/fx6-on-fx3-closure/fx6_closure/stage_b_post_trial_auditor.py`
- `outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`
- `outputs/fx6-on-fx3-closure/fx6_closure/__main__.py` (`audit-stage-b-post-trial [--clean-room] [--json] [--output PATH]`)
- `outputs/fx6-on-fx3-closure/tests/test_phase62_stage_b_post_trial_auditor.py` (`30` fast `<3s` dual-mode unit & fail-closed tests)
- `outputs/fx6-on-fx3-closure/README.md`
- `reports/2026-11-14-phase62-stage-b-post-trial-forensic-auditor/README.md`

---

## Verification Commands

```sh
# 1. Phase 62 unit tests (30 tests, <3s) in Local Donor and Clean-Room modes
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase62_stage_b_post_trial_auditor.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase62_stage_b_post_trial_auditor.py

# 2. CLI verification (summary & JSON)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure audit-stage-b-post-trial
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure audit-stage-b-post-trial --clean-room --json

# 3. Clean-room binary/pyc audit
make clean-audit
```
