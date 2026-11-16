# Phase 76 — Unified 6-Pillar Stage-B Release Dossier v3 (`stage_b_release_dossier_v3.py`)

## Summary

Phase 76 delivers [`stage_b_release_dossier_v3.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/stage_b_release_dossier_v3.py) (`schema_version = "stage_b_release_dossier_v3"`, `phase_version = "76.0.0"`), the unified, tamper-evident, fail-closed release signoff packet aggregating all **6 verification pillars (`Pillar A .. Pillar F`)** across physical rig safety, Tier-0 GF(256) self-healing & `init2` escape, 13 `fx3_firmware_lab` cross-body auditors, 10-stage `fx3-vm` heterogeneous co-emulation, Round 14 real unmodified FX3 `7.02` kernel 4-language × 3-surface UI rendering, and Phase 68/62 `R0..R6` / `H0 == H2` zero-persistence forensic proof — executing in **`< 3.5s`** (`~1.60s` in `LOCAL_DONOR_O_RDONLY`, `~1.30s` in `CLEAN_ROOM_SYNTHETIC`).

### Hard-Locked Safety Redlines & Authorization Split

- `persistent_emmc_writes_authorized = False` (permanently hard-locked `False`)
- `persistent_write_release = False` (permanently hard-locked `False`)
- `hardware_live_attachment_authorized = False` (explicitly distinguished from `all_pillars_simulation_ready = True`; live hardware attachment stays locked until physical `G10` Tier-0 same-body readback, `G11` `p1` recovery capsule verification, `G12` preflight pass, and explicit human operator signoff)
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- `calibration_mutation_bytes = 0`, `usb_or_camera_operations = 0`
- Local donor reads and Round 14 `summary.json` loading strictly use `os.O_RDONLY` (`o_rdonly_enforced = True`), with deterministic clean-room synthesis under `FX3_FX6_FORCE_CLEAN_ROOM=1` / `--clean-room`, zero raw `bytes` reprs (`b'...'` / `b"..."`), and guaranteed cleanup of all temporary directories (`temp_dir_cleaned = True`).

---

## 6-Pillar Stage-B Release Dossier v3 (`Pillar A .. Pillar F`)

| Pillar | Name | Integrated Modules & Phases | Verified Invariants | Fail-Closed Fault Injections Verified |
| :---: | --- | --- | --- | --- |
| **`Pillar A`** | `PHYSICAL_RIG_AND_20GATE_SAFETY` | Phase 69 `fx3_safety.rig_groundloop_lensrail_and_20gate_guard` (`evaluate_20gate_preflight`) | Offline hardware-truth block `17/20` (`overall_ready_for_hardware_attach = False`) vs simulated rehearsal `20/20` (`dry_run_rehearsal_only = True`); `G19` D-Tap/HDMI ground-loop isolation + E-Mount `< 2.0 ms` (`1.2 ms`) rail crowbar & `0x0400` IBIS park; `G20` `USB-PD -> NP-FZ100` UPS (`0` lost frames) + `.RSV` salvage | `G19` D-Tap ground-loop fault (`open_negative_ground_return_fault`), E-Mount crowbar `>= 2.0 ms`, `G20` UPS frame drop, persistent eMMC write request |
| **`Pillar B`** | `TIER0_GF256_SELFHEAL_AND_INIT2_ESCAPE` | Phase 72 `fx3_safety.tier0_backup_parity_and_manifest_guard` + Phase 66 `fx3_safety.init2_escape_and_watchdog_simulator` | `GF(256)` P+Q RAID-6 1-erasure, 2-erasure, and silent bit-rot self-healing + 3-loss quorum rejection (`UNRECOVERABLE_QUORUM_LOSS`); cross-body `cnflasha`/`C2PA` anti-transplant lock (`same_body=True`, `cross_body_blocked=True`); external SD `FX3_SAFE_STOCK.FLG` escape (`7/7`), `CXD90057 WDT` crash-loop breaker (`5/5`), `p1 FAT12/FAT16` clean mirror (`0` eMMC writes) | Cross-body `cnflasha`/C2PA transplant injection, `GF(256)` `>= 3`-shard quorum loss, `init2` escape / WDT fault |
| **`Pillar C`** | `FIRMWARE_PARITY_13PLUS_AUDITORS` | All `13/13` `fx3_firmware_lab` cross-body auditors (including Phase 70 `proxy_clipname_and_sidecar_auditor` & Phase 65 `wb_color_matrix_and_look_auditor` + `verify_raw_3x3_color_matrix`) | `13/13` firmware-lab auditors pass; Phase 65 `3x3` Paint Matrix white-point preservation (`white_point_preserved = True`) & `calibration_mutation_bytes == 0` / `cp_mutation_bytes == 0`; Phase 70 Dual-Slot Proxy / `CamID-Reel` / `NonRealTimeMeta v2.20` XML sidecar & `C2PA RQ_LIC.DAT` preservation (`internal_emmc_clip_writes == 0`) | `3x3` Paint Matrix white-point skew (`1.25`), `calibration_mutation_bytes > 0`, NRTM `v2.20` sidecar corruption |
| **`Pillar D`** | `TEN_STAGE_HETEROGENEOUS_COEMULATION` | Full `10/10` stages (`Stages 1..10`) of `outputs/fx3-vm` (`run_fx3_vm_coemulation_suite`) | All `10/10` co-emulation stages pass; Stage 9 `SMPTE 12M EXT-LK` + `PZ/IBIS` + Paint (`nop_count == 0`); Stage 10 `256 MiB` DRAM elastic FIFO Dual-Slot `Relay` `0`-drop rollover + UPS/`.RSV` salvage (`114/114` frames committed, `c2pa_license_untouched == True`); `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0` | Stage 10 `Relay` dropped frame (`> 0`), Stage 9 `nop_count > 0`, `cp_mutation_bytes > 0` |
| **`Pillar E`** | `FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI` | Round 14 (`reports/2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix/summary.json` via `os.O_RDONLY` or clean-room synthetic schema) | Real unmodified FX3 `4.9.337-scel+` kernel (`nop_count == 0`, `crashes == 0`, `13/13` Stage-B SHA-256 locks including `appFw.so = e2bc2619...` and `libWlanResource.so = 47fec188...`) renders `Big6 Home`, `3-Layer Menu`, and `Status Check` (`sid=0x2f`) across `EN`, `ZH-CN`, `ZH-TW`, `JA` with **`18/18` strictly positive pairwise pixel deltas** | `nop_count > 0`, collapsed `4`-lang pixel-delta pair (`= 0`), Stage-B manifest count mismatch (`12 != 13`) |
| **`Pillar F`** | `CLOSED_LOOP_R0_R6_ZERO_PERSISTENCE_PROOF` | Phase 68 `stage_b_rehearsal_orchestrator` (`R0..R6`) + Phase 62 `stage_b_post_trial_auditor` (`H0`-vs-`H2` 16-surface differ & 10-scenario matrix) | `R0..R6` closed-loop rehearsal (`7/7` stages pass) + `16/16` surface bit-for-bit `H0 == H2` post-trial proof (`drifted_surface_count == 0`, `persistent_bytes_mutated == 0`, `c2pa_rq_lic_intact == True`, `spacc_cnflasha_untouched == True`, `calibration_mutation_bytes == 0`, `10/10` anomaly matrix drills) | `1`-byte drift in `H2` `BK4`, `C2PA RQ_LIC.DAT`, `WBI2`, `Stock-CP`, or `sector0` |

---

## Deterministic Dossier Digests & Mode Parity

| Mode | Single Dossier Build | 32-Test Suite Runtime | `dossier_v3_sha256` | Hard-Locked Flags (`emmc` / `release` / `hw_attach`) |
| --- | :---: | :---: | --- | :---: |
| `LOCAL_DONOR_O_RDONLY` | `~1.60s` (`< 3.5s`) | `~2.79s` (`< 3.5s`) | `88fc67ec317a67eb86b19a4f2d3639d99f42dfbdede7ad12a62933dd80c8a354` | `False` / `False` / `False` |
| `CLEAN_ROOM_SYNTHETIC` | `~1.30s` (`< 3.5s`) | `~2.49s` (`< 3.5s`) | `a816fd9ae21b365e2645c250e9a8dfb6a7f1cd3ab33d3bce0973d1fae74bb0fd` | `False` / `False` / `False` |

- **Tamper-Evident Signoff Verifier (`verify_stage_b_release_dossier_v3`)**: Recomputes canonical `dossier_v3_sha256` (`sort_keys=True`), validates `schema_version == "stage_b_release_dossier_v3"`, checks all `6/6` pillars (`PILLAR_A .. PILLAR_F`) and quantitative cross-pillar invariants, enforces hard-locked `False` flags, rejects raw `bytes` reprs, and fails closed on any tamper or fault injection.
- **Bilingual Signoff Markdown (`render_dossier_v3_markdown`)**: Generates a structured `中文 + English` signoff summary covering all 6 pillars, redline locks, and `dossier_v3_sha256`.

---

## Exclusively Owned & Modified Files

1. [`outputs/fx6-on-fx3-closure/fx6_closure/stage_b_release_dossier_v3.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/stage_b_release_dossier_v3.py) — Phase 76 6-pillar dossier builder, `ProcessPoolExecutor` worker shims, fault-injection hooks, canonical SHA-256 signoff verifier, and bilingual Markdown renderer.
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — Exports `StageBReleaseDossierV3FaultInjection`, `DossierV3PillarResult`, `build_stage_b_release_dossier_v3`, `verify_stage_b_release_dossier_v3`, `compute_dossier_v3_sha256`, `render_dossier_v3_markdown`, and Phase 76 constants.
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — CLI subcommand `build-stage-b-dossier-v3 [--clean-room] [--json] [--markdown-out PATH] [--output PATH]`.
4. [`outputs/fx6-on-fx3-closure/tests/test_phase76_stage_b_release_dossier_v3.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase76_stage_b_release_dossier_v3.py) — `32` fast dual-mode unit & fail-closed fault-injection tests (`< 3.5s` in both Local Donor and Clean-Room modes).
5. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — Documented `stage_b_release_dossier_v3.py`, `__main__.py` subcommand, and verification command `#25`.
6. [`reports/2026-11-14-phase76-stage-b-release-dossier-v3/README.md`](README.md) — This Phase 76 verification report.

---

## Verification Commands

```sh
# 1. Phase 76 unit tests (32 tests, < 3.5s) in Local Donor and Clean-Room modes
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase76_stage_b_release_dossier_v3.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase76_stage_b_release_dossier_v3.py

# 2. Full outputs/fx6-on-fx3-closure test suite in Local Donor and Clean-Room modes
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -t outputs/fx6-on-fx3-closure/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -t outputs/fx6-on-fx3-closure/tests

# 3. CLI execution (Local Donor and Clean-Room modes)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure build-stage-b-dossier-v3 --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure build-stage-b-dossier-v3 --clean-room

# 4. Unified Lab Clean-Only Hygiene & Suite Check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
