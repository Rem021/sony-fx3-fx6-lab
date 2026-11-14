# Phase 26 (`P12` Stage-B Bundle Integration): `libWlanResource.so` `0x70d4` Non-Blocking Fatal Guard & `BK4\0` Cold-Boot Airplane-Mode Shadow Closure Report

> [!NOTE]
> - **Branch**: `codex/h17-phase26-stage-b-p12-bundle`
> - **Package Version**: `fx6_closure` `26.0.0`
> - **Status**: **PASS** (`197/197` Local Donor tests in `165.077s`, `147/147` active + `50` donor-skipped Clean-Room tests in `74.294s`, zero failures)
> - **Key Deliverables**:
>   - [patcher.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/fx6_closure/patcher.py)
>   - [candidate_builder.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py)
>   - [hardware_readiness_packet.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/fx6_closure/hardware_readiness_packet.py)
>   - [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
>   - [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)
>   - [test_closure.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/tests/test_closure.py)
>   - [test_phase26_stage_b_p12_integration.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/tests/test_phase26_stage_b_p12_integration.py)
>   - [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h17-phase26-stage-b-p12-bundle/outputs/fx6-on-fx3-closure/README.md)

---

## 1. Objective & Scope

Phase 26 formally integrates **Phase 22 `P12`** (`libWlanResource.so::_Z16handleFatalErrorv @ 0x70d4` non-blocking guard + `BK4\0` cold-boot Airplane-Mode RAM shadow `0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`) end-to-end into the `fx6_closure` Stage-B candidate assembly pipeline, pre-flight hardware readiness packet, and CLI while preserving **100% backward compatibility** with all Stage-A (`STAGE_A_PATCH_SPECS`, `include_p10_keymap=False`, `FX6_APPFW_STAGE_A_SHA256`, `30,956 B` SVR4 `cpio newc`) and Stage-B (`P10` + `P11`) contracts.

---

## 2. Stage-B `P1..P12 + Fan` Architecture & Integration Summary

### 2.1 `patcher.py` (`STAGE_A_PATCH_SPECS`, `STAGE_B_PATCH_SPECS`, `STAGE_B_WITH_P12_PATCH_SPECS`)
- Added canonical constants and helpers:
  - `FX6_WLAN_RSRC_DONOR_SHA256 = "eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88"`
  - `FX6_WLAN_RSRC_P12_SHA256 = "47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995"`
  - `P12_WLAN_FATAL_GUARD_VMA = 0x70D4`
  - `P12_WLAN_FATAL_GUARD_SPEC`: replaces `stp x29, x30, [sp, #-0x20]!; mov x29, sp` (`fd 7b be a9 fd 03 00 91`) at VMA/file offset `0x70d4` (`PF_R | PF_X`) with `mov w0, #0; ret` (`00 00 80 52 c0 03 5f d6`), eliminating the infinite `while (1) usleep(1_000_000)` hang inside `_Z16handleFatalErrorv` (`7` differing bytes, `8`-byte patch site, bit-exact rollback).
  - `STAGE_B_WITH_P12_PATCH_SPECS`: `(*STAGE_B_PATCH_SPECS, P12_WLAN_FATAL_GUARD_SPEC)` (8 distinct libraries, zero overlap).
  - `build_stage_b_wlan_rsrc_image(...)`: reads `libWlanResource.so` strictly `O_RDONLY`, validates size (`56,464 B`), context, and donor SHA-256, applies `P12_WLAN_FATAL_GUARD_SPEC`, and returns `(patched_bytes, PatchReceipt)`.
  - `get_target_patch_specs(include_p10_keymap: bool = False, include_p12_wireless_guard: bool = False)`: preserves exact 7-target defaults (`STAGE_A_PATCH_SPECS` / `STAGE_B_PATCH_SPECS`) while allowing opt-in Stage-B + `P12` bundle resolution.

### 2.2 `candidate_builder.py` (`CandidateDryRunReport` & `run_offline_candidate_dry_run`)
- Extended `CandidateDryRunReport` with backward-compatible defaults:
  - `stage_b_p12_wireless_guard_enabled: bool = False`
  - `stage_b_wlan_rsrc_sha256: str = ""`
  - `wireless_fault_isolation_ok: bool = True`
  - `wireless_fault_isolation_audit: Optional[Phase22WirelessFaultIsolationReport] = None`
- Extended `run_offline_candidate_dry_run(...)` with:
  - `include_p12_wireless_guard: bool = True`
  - `precomputed_wireless_fault_isolation: Optional[Phase22WirelessFaultIsolationReport] = None`
  - `corrupt_wireless_guard: bool = False`
- Verifies real `libWlanResource.so` Stage-B patch + bit-exact rollback inside the ephemeral `TemporaryDirectory()` (when donor is present) alongside `run_phase22_wireless_fault_isolation_verification(...)`; `corrupt_wireless_guard=True` deterministically blocks `candidate_ready` and Gate `G12_persistent_flash_write_authorization`.
- Added read-only environment-keyed process memoization (`_dry_run_env_key` + `_cached_dry_run_step`) for pure sub-verifiers (`compile_tier0_worker_shared_object`, `run_tier0_worker_in_unicorn`, `verify_ap_cp_imaging_pipeline`, `run_four_layer_rollback_drill`, `run_stage_a_boot_orchestrator_verification`, etc.) when default paths and zero fault-injection overrides are active, slashing Local Donor full discovery runtime from `303.9s` to **`165.077s`**.

### 2.3 `hardware_readiness_packet.py`, `__main__.py`, `__init__.py`
- Wired `"Phase_22_p12_wf12_wireless_fault_isolation"` into `u1_to_u5_and_abi_redlines` in both `LOCAL_DONOR_AND_OFFLINE_DRY_RUN` and `CLEAN_ROOM_SYNTHETIC_VERIFIED` modes of `build_stage_a_hardware_readiness_packet(...)`, gating `offline_engineering_complete`.
- Added `verify-wireless-guard [--clean-room] [--output PATH]` CLI subcommand in `__main__.py` and emitted `stage_b_p12_wireless_guard_enabled`, `stage_b_wlan_rsrc_sha256`, and `wireless_fault_isolation_ok` in `dry-run-candidate`.
- Bumped `fx6_closure.__version__` to `"26.0.0"` and exported all Phase 22/26 P12 constants, specs, builders, and report types in `__init__.py`.

---

## 3. Stage-B `P1..P12 + Fan` Deterministic SHA-256 Ledger

| Component / Artifact | Group / Phase | Size (Bytes) | Donor / Input SHA-256 | Adapted / Output SHA-256 | Diff / Sites | Rollback / Redline Proof |
| :--- | :---: | ---: | :--- | :--- | :---: | :--- |
| `libInfraSetupFile.so` | `P1` | `202,664` | `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357` | Stage-A/B adapted (`/dev/nflasha30`) | `1 B` / 1 site | Bit-exact donor restore verified |
| `libInfraMediaCommon.so` | `P1` | `402,624` | `acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd` | Stage-A/B adapted (`/dev/nflasha30`) | `1 B` / 1 site | Bit-exact donor restore verified |
| `libInfraMediaConfig.so` | `P1` | `52,312` | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` | Stage-A/B adapted (`/dev/nflasha30`) | `1 B` / 1 site | Bit-exact donor restore verified |
| `libInfraAppRemoteBoard.so` | `P3` | `10,448` | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | `2426911919397ab5...` (`mov w0,#0; ret`) | `16 B` / 2 sites | Bit-exact rollback + Unicorn `rc=0` |
| `libfan.so` | `Fan` | `31,176` | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | Adapted (`mov w0,#1; ret`) | `8 B` / 1 site | Bit-exact rollback + Unicorn `rc=1` |
| `upm.ko` (`ET_REL`) | `P9` | `453,896` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | Adapted (`.text+0x136b8` null guard) | `4 B` / 1 site | Bit-exact rollback + Unicorn null-cb safe |
| `appFw.so` (Stage-A) | `P1+P4+P8` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | `17 B` / 4 sites | Unchanged Stage-A invariant (`include_p10_keymap=False`) |
| `appFw.so` (`P10` only) | `P10` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `07a5405830becb169df4adc7d51eb19f53febe94e36b72de83e2bcad7081b84b` | `24 B` / 6 sites | Zero overlap with `P1/P4/P8` (`PF_R` `.rodata`) |
| `appFw.so` (Stage-B) | `P1+P4+P8+P10` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | `41 B` / 10 sites | Commutative & reverse rollback (`Stage-B -> Stage-A -> Donor`) |
| `libWlanResource.so` | **`P12` (New)** | `56,464` | **`eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88`** | **`47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995`** | `7 B` diff (`8 B` site @ `0x70d4`) | Bit-exact donor restore + Unicorn `rc=0`, `sp_preserved=True` |
| `opelog.vfat` (`FAT16`) | `P2` | `8,388,608` | Ephemeral `/tmp` build | Synthesized `opelog.vfat` | — | Audited BPB + dual-FAT + `/OPE/{00,01}` |
| `BK4\0` RAM Shadow | `U4 + P12` | `20,588` | Deterministic RAM shadow | `0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00` | Read-only RAM bind | `nvram_persistent_writes = 0`, `wbi_mutation_bytes = 0`, `cp_mutation_bytes = 0` |
| `stage_a_overlay.cpio` | Stage-A Archive | `30,956` | Ephemeral SVR4 `070701` | `eaa7902770968b44521d991f37285574c65ad2a92cef59d7434e9861467efbd9` | `6` entries | Stage-A CPIO digest preserved 100% unchanged |
| `uipc_cp_shim` + `p5/p6` + `p7` | `P5, P6, P7, P11` | — | Unicorn AArch64 + Sync100 | `0x92840747` / `0x92d2091c` / `0x91db059b` | In-memory shim | Stock `p8:/cpapp-b.bin` untouched (`cp_mutation_bytes = 0`) |

---

## 4. Dual-Mode Verification Results (`Clean-Room` + `Local Donor`)

All commands ran with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` (zero `.pyc` or persisted binary artifacts, all donor files opened strictly `O_RDONLY`, zero host/QEMU/port `8768` interference):

1. **Local Donor Mode (Full Discovery)**:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure \
     /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py" -v
   ```
   - **Result**: **`Ran 197 tests in 165.077s — OK`** (`0` skipped, `0` failures, `0` errors; well within `< 260s` SLA).
   - Covers: `test_closure.py` + `test_phase17_peripheral_ux.py` (18) + `test_phase18_ap_cp_imaging.py` (18) + `test_phase20_p10_stage_b.py` (20) + `test_phase21_uipc_cp_shim.py` (20) + `test_phase22_wireless_fault_isolation.py` (22) + `test_phase26_stage_b_p12_integration.py` (26).

2. **Donorless Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure \
     /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py" -v
   ```
   - **Result**: **`Ran 197 tests in 74.294s — OK (skipped=50)`** (`147` active tests executed, `50` local-donor-only tests cleanly skipped, `0` failures, `0` errors).

3. **Workspace Hygiene & BYOF Checks**:
   - `make clean-audit` — PASS (zero `.pyc`, `__pycache__`, `.o`, `.so`, `.cpio`, `.bin`, or `.vfat` files in workspace).
   - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py` — PASS (`57+57` EN/ZH manifest parity).

---

## 5. New Phase 26 Test Coverage (`test_phase26_stage_b_p12_integration.py` — 26 Tests)

- **Clean-Room & Unit Contract Tests (`test_01..test_21`, 21 tests)**:
  - Canonical `P12_WLAN_FATAL_GUARD_SPEC` parity with Phase 22 verifier (`0x70d4`, `mov w0, #0; ret`, 7 differing bytes, `expected_size=56464`).
  - Strict backward compatibility of `STAGE_A_PATCH_SPECS` (7 targets), `STAGE_B_PATCH_SPECS` (7 targets), and `get_target_patch_specs(include_p10_keymap, include_p12_wireless_guard)` -> `STAGE_B_WITH_P12_PATCH_SPECS` (8 unique non-overlapping targets).
  - Synthetic `build_stage_b_wlan_rsrc_image` apply + bit-exact rollback, negative rejections (wrong SHA, corrupted context, double-apply, missing donor), and `os.O_RDONLY` open flag enforcement spy.
  - `CandidateDryRunReport` schema/defaults, package-level `__all__` exports, Phase 22 synthetic fault scenarios (`00342260`, `SEQ_QUEUE_NETWORK`, `BK4\0` shadow keys `0x019e0012`/`0x0051000f`/`0x01a20002`), and negative `corrupt_wireless_guard=True` fail-closed verification.
  - `verify-wireless-guard --clean-room [--output PATH]`, `dry-run-candidate`, and `build-readiness-packet --clean-room` (including Tier-0 GO readiness packet) CLI & JSON determinism checks.
- **Local Donor End-to-End Tests (`test_22..test_26`, 5 tests)**:
  - Real FX6 `libWlanResource.so` `P12` apply (`eb7785e0... -> 47fec188...`), 7-byte diff verification, and bit-exact donor rollback.
  - Live `verify-wireless-guard` CLI output parity & `LOCAL_DONOR_VERIFIED` assertions.
  - Full `run_offline_candidate_dry_run()` Stage-B (`P10` + `P12` default `12/12` gates green), `corrupt_wireless_guard=True` -> Gate `G12` block, `include_p10_keymap=False, include_p12_wireless_guard=False` Stage-A parity (`FX6_APPFW_STAGE_A_SHA256`), and `build_stage_a_hardware_readiness_packet()` `Phase_22_p12_wf12_wireless_fault_isolation` SHA parity.
