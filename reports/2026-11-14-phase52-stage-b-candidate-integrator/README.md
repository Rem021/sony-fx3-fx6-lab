# Phase 52 — Unified Stage-B End-to-End Candidate Integrator (`stage_b_integrated_dossier_v1`)

## Summary

Phase 52 delivers [`stage_b_candidate_integrator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h45-phase52-stage-b-end2end-candidate-v2/outputs/fx6-on-fx3-closure/fx6_closure/stage_b_candidate_integrator.py), composing all five newly merged Phase 35..50 Stage-B safety, recovery, forensic, and packaging engines into a single fast (`<5s`), deterministic, self-authenticating JSON dossier (`stage_b_integrated_dossier_v1`) with fail-closed tamper detection (`verify_stage_b_integrated_dossier(payload)`).

### Hard-Locked Safety Redlines
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- `calibration_mutation_bytes = 0`
- `usb_or_camera_operations = 0`
- All donor files opened strictly read-only (`os.O_RDONLY`) with zero raw binary `bytes` reprs (`b'...'` / `b"..."`) emitted.

---

## Five Cross-Track Stage-B Pillars Composed

| Pillar | Engine / Module | Scope Verified Inside `stage_b_integrated_dossier_v1` | Verdict |
| :---: | --- | --- | :---: |
| **1** | Phase 50 `fx3_safety.master_16gate_preflight` | `G01..G16` (`16/16` `VERIFIED*`): C2PA `RQ_LIC.DAT` & factory sensor/IBIS calibration (`calibration_mutation_bytes == 0`), thermal PWM + `NP-FZ100 >= 80%` + `USB-PD 9V/3A` (`27000 mW`), Multi-Port `VMC-BNCM1` LTC / MI-Shoe `XLR-H1` isolation, `P12` `WF-12` bootloop immunity, and `WBI2` cold-boot isolation (`wbi_mutation_bytes == 0`, `cp_mutation_bytes == 0`). | **PASS (`16/16`)** |
| **2** | Phase 48 `fx6_closure.stage_b_ram_overlay_packager` | Deterministic SVR4 `cpio newc` (`070701`, `mtime=0`, `uid=0`, `gid=0`, `TRAILER!!!`) across all 4 `BK_LANG` profiles (`en=0x01`, `schinese=0x0c`, `tchinese=0x0b`, `japanese=0x00`), `13/13` `P1..P12+Fan` Verify-Before-Mount SHA-256 locks, `< 48 MiB` `tmpfs` DDR footprint (`9.21 MiB` Local Donor / `8.11 MiB` Clean-Room), and 9-scenario POSIX `/bin/sh` `stage_b_init2_guard.sh` audit (`0` eMMC/CP/WBI writes). | **PASS (`4/4` langs, `13/13` locks, `9/9` drill)** |
| **3** | Phase 47 `fx3_recovery.unbrick_ladder_and_capsule_verifier` | `12/12` Tier-0..Tier-4 escalation state-machine scenarios + `p1` VFAT (`FAT12` armed `3981b951fc35fa73...`, `FAT12` tripped `663503a208d3797d...`, `FAT16` tripped `7da7b1dc9cb57f70...`) atomic rollback capsule SHA-256 + `allow_boot_partition_targeting = False`, `emmc_write_bytes = 0`. | **PASS (`12/12`, `3/3` capsules)** |
| **4** | Phase 42 `fx3_recovery.emmc_dump_forensic_verifier` | `O_RDONLY` 7-role clean-room gate (`sector0`, `p1`, `p2`, `p5`, `p8`, `ext_csd`, `cnflasha`), pre-session negative gates (`stuck_bus`, `truncation`, invalidated `'WBI2'`, `BOOT0` flash block), and Local Donor `O_RDONLY` readback on `nflasha1` (`p1`), `nflasha5.img` (`WBI2` header), and `nflasha8.img` (`p8`). | **PASS (`7/7` roles + `4/4` negative + donor `p1`/`p5`/`p8`)** |
| **5** | Phase 39 `fx6_closure.stage_b_master_readiness_packet` | `stage_b_readiness_packet_v2` + Phase 35 `10/10` `S01..S10` Stage-B lifecycle drill & `H2` zero-drift verification (`appFw.so` `e2bc2619845e9614...`, `libWlanResource.so` `47fec188cc174faa...`) + `57+57` BYOF manifest parity. | **PASS (`10/10`, `13/13`, `57+57` BYOF)** |

---

## Deterministic Dossier Digests & Performance

| Mode | Selected `BK_LANG` | Measured Elapsed Time | Canonical `dossier_sha256` | `tmpfs` Footprint |
| --- | --- | :---: | --- | :---: |
| `LOCAL_DONOR_O_RDONLY` | `en` (`0x01`) | `4.107s` / `4.228s` (`< 5.0s`) | `715a69128a94d6524fe2ca9f493b94a7ca61936329bb6f92c51d51f2d8afe37a` | `9.2134 / 48.00 MiB` |
| `CLEAN_ROOM_SYNTHETIC` | `en` (`0x01`) | `3.143s` (`< 5.0s`) | `136761dcdcbcb660f97b0d5c24980882b0349037ad8831c4609c3df4016042f9` | `8.1143 / 48.00 MiB` |
| `CLEAN_ROOM_SYNTHETIC` | `schinese` (`0x0c`) | `2.446s` (`< 5.0s`) | `ab42b2930849cdd022d2867cc9257f8076d58f3d152b02dc5d989c325dee729c` | `8.1144 / 48.00 MiB` |

---

## Deliverables Modified / Added

- `outputs/fx6-on-fx3-closure/fx6_closure/stage_b_candidate_integrator.py`
- `outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`
- `outputs/fx6-on-fx3-closure/fx6_closure/__main__.py` (`verify-stage-b-candidate [--clean-room] [--lang en|schinese|tchinese|japanese] [--json] [--output PATH]`)
- `outputs/fx6-on-fx3-closure/tests/test_phase52_stage_b_candidate_integrator.py` (30 fast dual-mode unit & fail-closed tamper tests)
- `outputs/fx6-on-fx3-closure/README.md`
- `reports/2026-11-14-phase52-stage-b-candidate-integrator/README.md`

---

## Verification Commands

```sh
# 1. Phase 52 unit & fail-closed tamper tests (Local Donor mode & Clean-Room mode)
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase52_stage_b_candidate_integrator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase52_stage_b_candidate_integrator.py -v

# 2. CLI verification (summary & JSON)
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-candidate
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-candidate --clean-room --lang schinese --json

# 3. Full unified lab test suite + clean-room binary/pyc audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py
make clean-audit
```
