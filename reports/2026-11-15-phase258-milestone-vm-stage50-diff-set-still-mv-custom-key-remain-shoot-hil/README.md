# Phase 258 — GRAND MILESTONE VM Stage 50 (`50/50`) Real-Hardware `ILME-FX3` Wave-40 `[Different Set for Still/Mv]` 8-Item Asymmetric Transitions & `Ver. 7.02` `[Shutter Angle]` Override, `[Custom Key/Dial Set.]` 3-Domain `ISO/EI` Auto-Adaptation & Slot-1 `CAMSET01.DAT` Vault, and `[Remain Shoot Display]` Still-Buffer Scope & EVF-Less Monitor Topology HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H291` / `codex/h291-phase258-milestone-vm-stage50-diff-set-still-mv-custom-key-remain-shoot-hil`
- **Target Schema & Grand Milestone**: `realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1` (`version = 258.0.0`, `phase_number = 258`, `stage = stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil`, advancing `outputs/fx3-vm/` HIL stages to the **`50/50` GRAND MILESTONE**)
- **Authoritative Wave-40 Reference**: [`reports/2026-11-15-global-sony-wave40-milestone-diff-set-still-mv-8items-shutter-angle-custom-key-dial-remain-shoot-intel/README.md`](../2026-11-15-global-sony-wave40-milestone-diff-set-still-mv-8items-shutter-angle-custom-key-dial-remain-shoot-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 258` Stage 50 (`50/50` Grand Milestone) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py`](../../outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py) (`schema = realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1`) and registered `stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil` (`--include-stage50` / `--skip-stage50` / `--no-include-stage50` / `--skip-phase258` / `stage50_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `49/49` to **`50/50` (`vm_stages=50/50`)**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **15** real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts (`string_english_f.uxc`, FX6 `string_english.uxc`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`) strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `11c56edf4aec...` (`fx3_vm_coemulation_suite` 50-stage digest `b4cb393df976...`, `verify-milestone-233` SHA-256 `7185fd2a1f26b964...`, `verify-milestone-221` SHA-256 `a4380ccabab09bb8...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `82a8964d136c...` (`fx3_vm_coemulation_suite` 50-stage digest `f2659536748d...`, `verify-milestone-233` SHA-256 `ca133e8c48f82f5a...`, `verify-milestone-221` SHA-256 `13641906a1eba59c...`)
3. **Hard Safety Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `diff_set_transition_corruption_events = 0`, `shutter_angle_common_bleed_events = 0`, `slot1_custom_key_vault_mutation_bytes = 0`, `fx3_has_builtin_evf = False`, `evf_finder_monitor_spoof_events = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py`](../../outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py) | **NEW** — Phase 258 Stage 50 (`50/50` Grand Milestone) Wave-40 HIL co-emulator (`realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil`, `include_stage50`, `--include-stage50` / `--skip-stage50` / `--no-include-stage50` / `--skip-phase258`, and `stage50_ok` (`50/50`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 258 Stage 50 (`50/50` Grand Milestone) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py) | **NEW** — `68` fast dual-mode `unittest` tests (`3.288s` local donor / `1.338s` clean-room, both `< 4s`) |
| 5 | [`reports/2026-11-15-phase258-milestone-vm-stage50-diff-set-still-mv-custom-key-remain-shoot-hil/README.md`](README.md) | **NEW** — Full `Phase 258` Stage 50 (`50/50` Grand Milestone) engineering & verification report |

---

## 3. Hardware-Exact Wave-40 Co-Emulation Architecture

### 3.1 `O_RDONLY` 15-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves `Different Set for Still/Mv`, all 8 checkable items `Aperture` / `Shutter Speed` / `ISO` / `Exposure Comp.` / `Metering Mode` / `White Balance` / `Picture Profile` / `Focus Mode`, `Shutter Mode`, `Angle`, `Custom Key/Dial Set.`, `ISO/EI`, `Control Wheel`, `Follow Custom`, `My Dial`, `Recall Custom hold`, `Cine EI`, `Remain Shoot Display`, `Not Displayed`, `Always Display`, `Shoot-Only Display`, `Save/Load Settings`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings` and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraAdjMedia.so`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, and `libInfraMediaConfig.so`, alongside bounded `<= 4096 B` windows in `appFw.so` (`SHUTTER`, `APERTURE`, `CUSTOM`, `DIAL`, `CAMSET`, `REMAIN`, `MONITOR`, `RESET`), `cpapp-b.bin` (`Shutter`, `Custom`, `Dial`, `Display`, `Monitor`, `Initialize`), `libmpr.so`, and `BK4`.

### 3.2 Sub-Model 50A — `[Different Set for Still/Mv]` 8-Item Asymmetric Transitions & `Ver. 7.02` `[Shutter Angle]` Override
- Models `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` across the exact 8 items (`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture Profile`, `Focus Mode`), surviving `[Camera Settings Reset]` and `[Reset Network Set.]` and resetting only via `[Initialize]`.
- Enforces **Common -> Separate** (copies current values to both Still and Movie registers **EXCEPT `Custom White Balance`**, which stays Still-only), **Separate -> Common** (resets parameters to initial factory defaults **EXCEPT `Aperture`, `Shutter Speed`, and `Custom White Balance`**, which retain Still values; `diff_set_transition_corruption_events == 0`), and `Ver. 7.02` (`Ver. 6.00+`) **`[Shutter Mode] = [Angle]`** override (Movie Shutter Angle and Still Shutter Speed remain independent even when `Shutter Speed` is Common; `shutter_angle_common_bleed_events == 0`).

### 3.3 Sub-Model 50B — `[Custom Key/Dial Set.]` 3-Domain `ISO/EI` Auto-Adaptation & Slot-1 `CAMSET01.DAT` Vault
- Models `MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]` across `Still` / `Movie` / `Playback` 3-domain keymaps, factory Cinema-Line dial defaults (`Front dial = Aperture`, `Rear dial = ISO/EI` auto-adapting between `ISO` in `Off`/`Flexible ISO` and `Exposure Index (EI)` in `Cine EI`/`Cine EI Quick`, `Control Wheel = Shutter Speed`), Movie `[Follow Custom]` inheritance, `[My Dial 1..3]` temporary dial swap, and `[Recall Custom hold 1..3]`.
- Verifies survival across `[Camera Settings Reset]` and `[Reset Network Set.]` (reset only via `[Initialize]`), and proves lossless `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` round-trip while blocking mutating Slot-1 vault writes (`EROFS = 30`, `slot1_custom_key_vault_mutation_bytes == 0`).

### 3.4 Sub-Model 50C — `[Remain Shoot Display]` Still-Buffer Scope & EVF-Less `ILME-FX3` Monitor Topology
- Models `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]` (`Not Displayed` default / `Always Display` / `Shoot-Only Display`), strictly scoping display to continuous-shooting still-image buffer capacity (`displays_movie_card_remaining_time == False`) and surviving `[Camera Settings Reset]` and `[Reset Network Set.]` (reset only via `[Initialize]`).
- Enforces EVF-less `ILME-FX3` (`ilc/2210`) topology (`fx3_has_builtin_evf == False`, no `[Finder/Monitor]` eye-sensor switch, rejecting EVF/`Finder/Monitor` spoof attempts with `EOPNOTSUPP = 95`, `evf_finder_monitor_spoof_events == 0`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h291-phase258-milestone-vm-stage50-diff-set-still-mv-custom-key-remain-shoot-hil` and exited `0`.
- **Engineering Inference (工程推断)**: Modeling Sony's asymmetric `Separate -> Common` reset table (`Aperture`, `Shutter Speed`, and Still-only `Custom White Balance` retained while `ISO`, `Exposure Comp.`, `Metering Mode`, `Picture Profile`, and `Focus Mode` revert to initial factory defaults), `Ver. 7.02` `[Shutter Angle]` independence, and `O_RDONLY` Slot-1 `CAMSET01.DAT` restoration prevents operator parameter loss during offline bench validation, while physical camera attachment and persistent eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`68 / 68` PASS** (`3.288s` local donor / `1.338s` clean-room, both `< 4s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2189 / 2189` PASS** (`159.415s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2189` ran (`2186` PASS, `3` donor-only skips)** (`167.417s`, `0` failures) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=50/50 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=50/50 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Full Lab Gate | **`ALL GREEN`** (`0` `.pyc` files across repository, `0` leaked bytes) |
