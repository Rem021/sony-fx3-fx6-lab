# Hydrogen-6｜Phase 20 Stage-B P10 Physical Button Keymap Builder Integration & Combined Closed-Loop Verification

## 1. Summary

Phase 20 promotes Phase 17's 24-byte `PF_R` `.rodata` FX3 physical body button keymap adapter (`P10_KEYMAP_PATCH_SPEC` / `P10_APPFW_KEYMAP_SPEC`: `Fn -> HOME`, `C1 -> KURU_PON`, `C2 -> MENU_CANCEL`, `C3 -> DISP_SEL`, `PLAY -> THUMBNAIL`, `DELETE -> USER` on FX6 `appFw.so`) into the official candidate builder ([`patcher.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/patcher.py) and [`candidate_builder.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py)) as the default **Stage-B** build mode (`include_p10_keymap: bool = True` / `STAGE_B_PATCH_SPECS`), while keeping 100% backward compatibility with the Stage-A deterministic SHA-256 and RAM-overlay CPIO contracts (`include_p10_keymap=False` / `ALL_PHASE2_TARGET_SPECS` / `STAGE_A_PATCH_SPECS`).

All donor binary reads strictly enforce `os.O_RDONLY` via [`read_donor_bytes_readonly()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/patcher.py) and `donor_paths.py`, keeping `persistent_emmc_writes_authorized = False` and `persistent_write_release = False` locked.

---

## 2. Deterministic Multi-Patch Layout & SHA-256 Chain on FX6 6.01 `appFw.so`

### 2.1 Combined 10-Site / 41-Byte Allocation (`P1 + P4 + P8 + P10`)

Every patch site inside FX6 6.01 `appFw.so` (`50,520,424` bytes) was verified via `verify_patch_sites_non_overlapping()` to occupy strictly disjoint byte ranges and non-aliasing `PF_R | PF_X` vs `PF_R` ELF64 `PT_LOAD` segments:

| Patch Group | Site ID | ELF64 VMA / File Offset | Segment Flags | Size | Original Bytes (Hex / Meaning) | Patched Bytes (Hex / Meaning) |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **P4** | `P4_appfw_set_nd_filter_mode_clear` | `0x2111358..0x211135c` | `PF_R \| PF_X` | 4 B | `81000035` (`cbnz w1, #0x2111368`) | `1f2003d5` (`nop`) |
| **P4** | `P4_appfw_set_nd_filter_value_clear` | `0x21113f0..0x21113f4` | `PF_R \| PF_X` | 4 B | `61030034` (`cbz w1, #0x211145c`) | `1b000014` (`b #0x211145c`) |
| **P8** | `P8_appfw_async_log_wait_nonblocking` | `0x2159c50..0x2159c58` | `PF_R \| PF_X` | 8 B | `fd7bbaa9 fd030091` (prologue) | `00008052 c0035fd6` (`mov w0, #0; ret`) |
| **P10** | `p10_c1_to_kuru_pon` | `0x2245a84..0x2245a88` | `PF_R` (`.rodata`) | 4 B | `0e000000` (`app_key 0x00e`) | `29000000` (`0x029` KURU_PON) |
| **P10** | `p10_play_to_thumbnail` | `0x2245b24..0x2245b28` | `PF_R` (`.rodata`) | 4 B | `22000000` (`app_key 0x022`) | `83010000` (`0x183` THUMBNAIL) |
| **P10** | `p10_delete_to_user` | `0x2245b2c..0x2245b30` | `PF_R` (`.rodata`) | 4 B | `23000000` (`app_key 0x023`) | `85010000` (`0x185` USER) |
| **P10** | `p10_fn_to_home` | `0x2245e7c..0x2245e80` | `PF_R` (`.rodata`) | 4 B | `8d000000` (`app_key 0x08d`) | `84010000` (`0x184` HOME / Big6) |
| **P10** | `p10_c2_to_menu_cancel` | `0x224610c..0x2246110` | `PF_R` (`.rodata`) | 4 B | `df000000` (`app_key 0x0df`) | `92010000` (`0x192` MENU_CANCEL) |
| **P10** | `p10_c3_to_disp_sel` | `0x2246134..0x2246138` | `PF_R` (`.rodata`) | 4 B | `e4000000` (`app_key 0x0e4`) | `99010000` (`0x199` DISP_SEL) |
| **P1** | `P1_appfw_nflasha20_to_30` | `0x25896ce..0x25896cf` | `PF_R` (`.rodata`) | 1 B | `32` (`'/dev/nflasha20'`) | `33` (`'/dev/nflasha30'`) |

> **Total Stage-B (`P1+P4+P8+P10`) footprint on `appFw.so`**: `10` non-overlapping sites, `41` patched bytes (`17 B` Stage-A + `24 B` P10). Zero page aliasing between P10 `.rodata` (`0x2245000..0x2247000`) and executable `P4`/`P8` pages (`0x2111000`, `0x2159000`, `0x2167000`).

### 2.2 Deterministic SHA-256 Chain & Commutative / Reverse Rollback Proofs

| Stage / Artifact State | Patched Bytes | Verified SHA-256 Digest | Notes |
| :--- | :---: | :--- | :--- |
| FX6 6.01 Donor Baseline (`appFw.so`) | `0` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | Authoritative 50,520,424 B donor ELF64 |
| **Stage-A** (`P1+P4+P8`) | `17` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | Preserved 100% when `include_p10_keymap=False` |
| **P10-Only** (`P10` keymap) | `24` | `07a5405830becb169df4adc7d51eb19f53febe94e36b72de83e2bcad7081b84b` | Phase 17 24-byte keymap adapter alone |
| **Stage-B** (`P1+P4+P8+P10`) | `41` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | Default builder output (`include_p10_keymap=True`) |
| Forward Sequential `(P1+P4+P8) -> P10` | `41` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | Bit-for-bit identical to combined apply |
| Forward Sequential `P10 -> (P1+P4+P8)` | `41` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | Order-independent non-interference |
| Reverse Step 1 (`Stage-B -> Stage-A`) | `-24` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | Bit-for-bit equal to Stage-A baseline |
| Reverse Step 2 / Direct Rollback (`-> Donor`) | `-41` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | Bit-for-bit restoration of original donor |

---

## 3. Unicorn Engine AArch64 Execution Proofs Against Combined Stage-B `appFw.so`

All AArch64 runtime checks were executed directly against the single combined **Stage-B (`P1+P4+P8+P10`)** `appFw.so` image in [`verify_combined_stage_b_appfw_contract()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py) and [`test_phase20_p10_stage_b.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/tests/test_phase20_p10_stage_b.py):

1. **P4 Electronic Variable ND Filter Clear Lock (`set_nd_filter_mode_i` @ `0x2111358` & `set_nd_filter_value_i` @ `0x21113d8`)**:
   - `576/576` enum combinations returned `Clear` (`4` and `(1, 1)`) with `0` assertion hits and preserved callee-saved `sp`/`x19`.
2. **P8 Non-Blocking Async Log Wait (`0x2159c50`)**:
   - Returned `w0 == 0` in `2` instructions with `sp` preserved.
3. **P5 / P6 UIPC Completion Synthesis (`send_and_wait_cmp_i`)**:
   - All positive IPC opcodes (`0x032d`, `0x0400`, `0x0402`, `0x0404`, `0x0152`) passed and negative malformed tests were rejected on the same Stage-B image.
4. **P10 C++ `std::unordered_map` Builder (`0xc0b778`) + Lookup (`0xc0b6e8`) Over Combined Image (`15` Native 1:1 + `6` P10-Remapped Keys = `21/21`)**:
   - **15 Native 1:1 Controls**: `POWER (0x0002 -> 0x001)`, `UP (0x0003 -> 0x002)`, `LEFT (0x0015 -> 0x004)`, `DOWN (0x0030 -> 0x006)`, `MENU (0x01ab -> 0x013)`, `ENTER (0x01ac -> 0x014)`, `RIGHT (0x01af -> 0x016)`, `REC (0x01f0 -> 0x01c)`, `C5 (0x7049 -> 0x040)`, `C6 (0x704a -> 0x041)`, `VARI_LCD_OPEN (0x71c3 -> 0x1bb)`, `VARI_LCD_CLOSE (0x71c4 -> 0x1bc)`, `VARI_LCD_REV (0x71c5 -> 0x1bd)`, `DIAL_FRONT (0x04000011 -> 0x214)`, `DIAL_REAR (0x04000013 -> 0x216)`.
   - **6 P10-Remapped FX3 Physical Buttons**: `Fn (0x7095 -> 0x184 HOME)`, `C1 (0x0066 -> 0x029 KURU_PON)`, `C2 (0x70e7 -> 0x192 MENU_CANCEL)`, `C3 (0x70ec -> 0x199 DISP_SEL)`, `PLAY (0x01f7 -> 0x183 THUMBNAIL)`, `DELETE (0x01f8 -> 0x185 USER)`.

---

## 4. CandidateDryRunReport Integration & Backward Compatibility

- [`patcher.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/patcher.py):
  - Exports `P10_KEYMAP_PATCH_SPEC`, `P1_P4_P8_P10_APPFW_COMBINED_SPEC`, `STAGE_A_PATCH_SPECS`, `STAGE_B_PATCH_SPECS`, `ALL_PATCH_SPECS`, `FX6_APPFW_DONOR_SHA256`, `FX6_APPFW_STAGE_A_SHA256`, `FX6_APPFW_P10_ONLY_SHA256`, `FX6_APPFW_STAGE_B_SHA256`, `read_donor_bytes_readonly()`, `get_target_patch_specs(include_p10_keymap=...)`, `verify_patch_sites_non_overlapping()`, and `build_stage_b_appfw_image()`.
  - Keeping `STAGE_B_PATCH_SPECS` as a 7-target tuple with `P1_P4_P8_P10_APPFW_COMBINED_SPEC` ensures every staged library directory contains one unified `appFw.so` image (`P1+P4+P8+P10`), preserves `len(patch_receipts) == 7`, and leaves Stage-A CPIO (`30,956 B`) contracts unaffected.
- [`candidate_builder.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py):
  - Adds [`StageBCombinedAppFwReport`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py) and [`verify_combined_stage_b_appfw_contract()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h6-phase20-p10-stage-b/outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py) (dual-mode: real donor binary + clean-room synthetic AArch64 ELF64).
  - Adds safe default fields to `CandidateDryRunReport` (`stage_b_p10_keymap_enabled: bool = False`, `stage_b_appfw_sha256: str = ""`, `stage_b_combined_appfw_verified: bool = False`, `stage_b_p10_summary: Optional[StageBCombinedAppFwReport] = None`).
  - `run_offline_candidate_dry_run()` defaults to `include_p10_keymap=True` (`Stage-B`, 12/12 gates green, `e2bc2619...`), supports `include_p10_keymap=False` (`Stage-A`, 12/12 gates green, `95f46b6c...`), and blocks Gate G12 on `corrupt_stage_b_p10=True`.

---

## 5. Dual-Mode Verification Results

| Mode | Command | Result |
| :--- | :--- | :--- |
| **Clean-Room Synthetic CI Mode** | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-safety:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py" -v` | **PASS** — `Ran 129 tests in 55.083s` (`OK (skipped=45)`; all 16 clean-room Phase 20 tests executed and passed) |
| **Local Donor Mode (FX6 6.01 + FX3 7.02)** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py" -v` | **PASS** — `Ran 129 tests in 245.482s` (`OK`, `0` skipped, `20/20` Phase 20 tests + all existing tests green) |
| **Clean-Audit** | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **PASS** — `0` `.pyc`, `0` `__pycache__`, `0` transient binaries |
