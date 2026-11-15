# Phase 68 — Stage-B `R0..R6` Closed-Loop Hardware Rehearsal Orchestrator (`stage_b_rehearsal_orchestrator.py`)

## Summary

Phase 68 delivers [`stage_b_rehearsal_orchestrator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/fx6_closure/stage_b_rehearsal_orchestrator.py) (`schema_version = "stage_b_closed_loop_rehearsal_v1"`, `phase_version = "68.0.0"`), unifying the repository's pre-plug bench fixture self-test, 18-gate hardware safety & `exFAT` media firewall, `H0` 16-surface baseline snapshot, Stage-B SVR4 `cpio newc` volatile RAM overlay, Stage 7/8/Round-13 live co-emulation + 4-language UI check, cold power-cycle wipe model (`H1 -> H2`), and Phase 62 `H0`-vs-`H2` post-trial forensic audit + 10-scenario negative tamper drills into a single zero-write, fail-closed `R0..R6` closed-loop rehearsal pipeline executing in `< 2.0s` (`< 4.0s` budget) in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes.

### Hard-Locked Safety Redlines & Authorization Split

- `persistent_emmc_writes_authorized = False` (permanently hard-locked `False`)
- `persistent_write_release = False` (permanently hard-locked `False`)
- `hardware_live_attachment_authorized = False` (explicitly distinguished from `rehearsal_passed = True`; live camera cable attachment remains locked pending `G10_physical_tier0_same_body_readback`, `G11_physical_p1_recovery_capsule_verified`, `G12_physical_stage_b_preflight_pass`, and `explicit_human_operator_signoff`)
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- `calibration_mutation_bytes = 0`, `usb_or_camera_operations = 0`
- Strict `os.O_RDONLY` file access for local donor artifacts, deterministic clean-room synthesis under `FX3_FX6_FORCE_CLEAN_ROOM=1` / `--clean-room`, zero raw `bytes` reprs (`b'...'` / `b"..."`), and automatic cleanup of any temporary rehearsal workspace.

---

## 7-Stage Zero-Write Closed-Loop Rehearsal (`R0..R6`)

| Stage | Name | Integrated Subsystems | Key Verified Invariants | Fail-Closed Fault Injection Covered |
| :---: | --- | --- | --- | --- |
| `R0` | `BENCH_FIXTURE_SELFTEST` | Phase 59 `rp2040_multiport_fixture_selftest` | `waveshare_rp2040_zero`, `-DOPEN_DRAIN=1`, `v_idle_tx_v == 1.8V`, `48000` baud PIO (`0.0004%` error), loopback bit-exactness, ohmmeter + camera/LTC disconnected pre-plug interlocks | `3.3V` overvoltage (`v_idle_tx_v = 3.3`), `open_drain_enforced = False`, camera attached pre-plug |
| `R1` | `SAFETY_18GATE_AND_MEDIA_FIREWALL` | Phase 61 `usblan_ptpip_and_18gate_preflight` + Phase 57 `exfat_media_integrity_guard` | All `18/18` gates (`G01..G18`) in offline dry-run rehearsal, blank dedicated lab `exFAT` 12-sector `BootChecksum` pass, and live negative rejection of production CFexpress/SD card containing `XDROOT`/`M4ROOT`/`.RSV` | Client card with `PRIVATE/M4ROOT/CLIP/C0001.RSV`, `G17` or `G18` gate failure |
| `R2` | `H0_BASELINE_SNAPSHOT` | Phase 62 `stage_b_post_trial_auditor` / `build_deterministic_stage_b_bundle_pair` | `16/16` cryptographic baseline surfaces (`Tier-0` eMMC + `BK4` + `WBI2` + `Stock-CP` + `C2PA RQ_LIC.DAT` + `SPACC cnflasha`) captured in `H0` | Corrupt `WBI2` magic (`BAD!`) or invalid `H0` baseline surface |
| `R3` | `STAGE_B_VOLATILE_OVERLAY_MOUNT` | Phase 48/52 `stage_b_ram_overlay_packager` + `init2` `/bin/sh` sandbox | SVR4 `cpio newc` overlay (`9.21 MiB` local / `8.11 MiB` clean-room, `<= 48 MiB` budget), `13/13` lock table entries, `P12` Airplane-Mode `00342260` (`WF-12`) immunity (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`), `init2` `9/9` drills with `0` eMMC writes | `WF-12` (`00342260`) key non-zero (`0x01`), `48 MiB` tmpfs budget overflow (`52 MiB`) |
| `R4` | `LIVE_H1_COEMULATION_AND_4LANG_UI` | Stage 7 `qmp_guest_introspection_tracer` + Stage 8 `uvc_hdmi_raw_output_emulator` + Round 13 `summary.json` | QMP non-intrusive guest tracer (`nop_count == 0`, `ctrl_mailbox` magic valid), HDMI `RAW16 256B EDID` & USB-C single-gadget arbitrator (`sdi_transceiver_faults == 0`), Round 13 real FX3 `4.9.337-scel+` 4-language (`EN`/`ZH-CN`/`ZH-TW`/`JA`) presenter (`Status Check sid=0x2f`, 3-layer menu `sid=0x11`, `6/6` big6 & `6/6` menu cross-language pixel-delta pairs `> 0`) | `qmp_nop_count = 1`, `edid_256b_valid = False`, collapsed 4-language pixel-delta pair (`= 0`) |
| `R5` | `COLD_POWER_CYCLE_WIPE` | Volatile `tmpfs` lifecycle model (`H1 -> H2`) | `/tmp/fx6_overlay` unmounts and vanishes completely (`volatile_overlay_vanished == True`), `lingering_mounts == 0`, `tmpfs_residue_files == 0`, `emmc_residual_writes == 0`, `mod_arm_once_present == False`, `stock_fx3_restored == True` | Lingering `/tmp/fx6_overlay` mount (`lingering_mounts = 1`) or `emmc_residual_writes > 0` |
| `R6` | `H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT` | Phase 62 `verify_stage_b_post_trial_zero_persistence` + `run_stage_b_forensic_anomaly_matrix` + `verify_stage_b_post_trial_receipt` | `16/16` surfaces bit-for-bit matched (`drifted_surface_count == 0`, `persistent_bytes_mutated == 0`), `c2pa_keystore_untouched == True`, `spacc_cnflasha_untouched == True`, `calibration_mutation_bytes == 0`, `10/10` negative tamper scenarios (`S01..S10`) pass fail-closed | 1-byte tamper in `H2` `p2_backup_bin.bin` (`BK4`), `c2pa_rq_lic.dat` (`C2PA`), or `p5_wbi_header.bin` (`WBI2`) |

---

## Deterministic Rehearsal Certificates & Mode Parity

| Mode | Elapsed (CLI/Suite) | `rehearsal_digest_sha256` | `R3` Overlay (`MiB` / CPIO Bytes) | `R6` Audit Report SHA-256 | `R6` Receipt SHA-256 |
| --- | :---: | --- | :---: | --- | --- |
| `LOCAL_DONOR_O_RDONLY` | `~1.65s` | `58a157e8154014d38b2778653eabe35263b194fd4f954be704f09d771166cc93` | `9.2134 MiB` (`39,508 B`) | `ecc5751ee8805264d937b48bf3d93309a395f311e7ed27a5600fbcbd10f4ef93` | `ce88773e06974c82a9fc0b86ee40393fbe5dcfa1709ed81905b27458013d42bb` |
| `CLEAN_ROOM_SYNTHETIC` | `~1.83s` | `cdc27185be2577f23de2976b911b869469529f1f6ff2a5e021b59b2a0b870696` | `8.1143 MiB` (`39,480 B`) | `1ad69d75caad0a9f81b4c1074ce4ca21bdb299fcc8b43bd66b8b700173fa1f95` | `2031114f62ee73096c5afde15350572561d9353d5c2064c858e615f89098e91b` |

- **Round 13 `4.9.337-scel+` 4-Language Big6 Pixel Deltas (`6/6 > 0`)**:
  - `en_vs_schinese = 11928`, `en_vs_tchinese = 11252`, `en_vs_japanese = 11961`, `schinese_vs_tchinese = 676`, `schinese_vs_japanese = 88`, `tchinese_vs_japanese = 764` (`Status Check sid=0x2f`, 3-layer menu `sid=0x11`).
- **Certificate Verification (`verify_stage_b_rehearsal_certificate`)**:
  - Canonicalizes the report payload (`sort_keys=True`), verifies `rehearsal_digest_sha256` against [`compute_rehearsal_digest_sha256`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/fx6_closure/stage_b_rehearsal_orchestrator.py), checks all 7 stage statuses, enforces permanent `False` lock on `persistent_emmc_writes_authorized` and `persistent_write_release`, and rejects any payload drift or boolean downgrade fail-closed.

---

## Deliverables Owned & Modified

- [`stage_b_rehearsal_orchestrator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/fx6_closure/stage_b_rehearsal_orchestrator.py) — Phase 68 `R0..R6` orchestrator, fault-injection hooks, canonical SHA-256 certificate builder/verifier, and Markdown renderer.
- [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — Public symbol exports for Phase 68 orchestrator constants, dataclasses, and functions.
- [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — `rehearse-stage-b-closed-loop [--clean-room] [--lang {en,schinese,tchinese,japanese}] [--json] [--markdown-out PATH] [--output PATH]` CLI subcommand.
- [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/README.md) — Updated module structure, CLI commands, and Phase 68 usage entry (`#24`).
- [`test_phase68_stage_b_rehearsal_orchestrator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/outputs/fx6-on-fx3-closure/tests/test_phase68_stage_b_rehearsal_orchestrator.py) — `34` fast (`< 3.0s`) dual-mode unit and fail-closed fault-injection tests covering `R0..R6`, digest determinism, CLI exit codes, certificate verification, and clean-room parity.
- [`reports/2026-11-14-phase68-stage-b-closed-loop-rehearsal/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h62-phase68-stage-b-closed-loop-rehearsal/reports/2026-11-14-phase68-stage-b-closed-loop-rehearsal/README.md) — This phase report.

---

## Verification Commands

```sh
# 1. Phase 68 unit tests (34 tests, < 3.0s) in Local Donor and Clean-Room modes
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase68_stage_b_rehearsal_orchestrator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase68_stage_b_rehearsal_orchestrator.py

# 2. Full outputs/fx6-on-fx3-closure test suite in Local Donor and Clean-Room modes
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -t outputs/fx6-on-fx3-closure -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -t outputs/fx6-on-fx3-closure -v

# 3. CLI execution (Local Donor and Clean-Room modes)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure rehearse-stage-b-closed-loop
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure rehearse-stage-b-closed-loop --clean-room --json

# 4. Clean-room hygiene audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
