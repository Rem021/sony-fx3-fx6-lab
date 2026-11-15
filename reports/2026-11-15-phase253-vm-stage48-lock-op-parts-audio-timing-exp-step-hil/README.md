# Phase 253 — VM Stage 48 (`48/48` Milestone) Real-Hardware `ILME-FX3` Wave-38 `[Lock Operation Parts]` (`MENU + Fn >= 5s` Chord vs `MENU + Delete >= 2s` Format Firewall & `[My Dial 1..3]` Override), `[Audio Out Timing]` vs `[Audio signals]` Persistence & `[Silent Mode]` Lockout, and `[Exposure step]` `0.3EV`/`0.5EV` vs `[Shutter Angle]` Constant-Table Immunity HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H286` / `codex/h286-phase253-vm-stage48-lock-op-parts-audio-timing-exp-step-hil`
- **Target Schema & Milestone**: `realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1` (`version = 253.0.0`, `phase_number = 253`, `stage = stage48_realhw_lock_op_parts_audio_timing_exp_step_hil`, advancing `outputs/fx3-vm/` HIL stages to **`48/48`**)
- **Authoritative Wave-38 Reference**: [`reports/2026-11-15-global-sony-wave38-lock-op-parts-menu-fn-5s-audio-out-timing-audio-signals-exp-step-shutter-angle-intel/README.md`](../2026-11-15-global-sony-wave38-lock-op-parts-menu-fn-5s-audio-out-timing-audio-signals-exp-step-shutter-angle-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 253` Stage 48 (`48/48`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py`](../../outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py) (`schema = realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1`) and registered `stage48_realhw_lock_op_parts_audio_timing_exp_step_hil` (`--include-stage48` / `--skip-stage48` / `--no-include-stage48` / `--skip-phase253` / `stage48_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `47/47` to **`48/48`**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **15** real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts (`string_english_f.uxc`, FX6 `string_english.uxc`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`) strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `98abc54b396f...` (`fx3_vm_coemulation_suite` 48-stage digest `53f61a0eb6a5...`, `verify-milestone-233` SHA-256 `8df9c710a2123d15...`, `verify-milestone-221` SHA-256 `94131934d4937eff...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `4fda9fd6839f...` (`fx3_vm_coemulation_suite` 48-stage digest `aac75a4f728d...`, `verify-milestone-233` SHA-256 `b42d2e44db88dd6b...`, `verify-milestone-221` SHA-256 `f58545800a077470...`)
3. **Hard Safety Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `destructive_menu_delete_confusions = 0`, `slot1_vault_format_events = 0`, `silent_mode_audio_signal_leak_events = 0`, `shutter_angle_exposure_step_drift_events = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py`](../../outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py) | **NEW** — Phase 253 Stage 48 (`48/48`) Wave-38 HIL co-emulator (`realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage48_realhw_lock_op_parts_audio_timing_exp_step_hil`, `include_stage48`, `--include-stage48` / `--skip-stage48` / `--no-include-stage48` / `--skip-phase253`, and `stage48_ok` (`48/48`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 253 Stage 48 (`48/48`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_lock_op_parts_audio_timing_exp_step_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_lock_op_parts_audio_timing_exp_step_coemulator.py) | **NEW** — `66` fast dual-mode `unittest` tests (`3.569s` local donor / `1.787s` clean-room, both `< 4s`) |
| 5 | [`reports/2026-11-15-phase253-vm-stage48-lock-op-parts-audio-timing-exp-step-hil/README.md`](README.md) | **NEW** — Full `Phase 253` Stage 48 engineering & verification report |

---

## 3. Hardware-Exact Wave-38 Co-Emulation Architecture

### 3.1 `O_RDONLY` 15-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves `Lock Operation Parts`, `Dial/Wheel`, `Dial + Wheel`, `Multi-Selector`, `My Dial`, `Locked`, `Delete`, `Audio Out Timing`, `Live`, `Lip Sync`, `Audio Recording`, `Sound`, `Beep`, `Silent Mode`, `Exposure step`, `0.3EV`, `0.5EV`, `Exposure`, `Shutter Mode`, `Shutter Speed`, `Angle`, `Speed`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings` and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraAdjMedia.so` (`318,152 B`: `AUDIO`, `Backup_read`), `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, and `libInfraMediaConfig.so`, alongside bounded `<= 4096 B` windows in `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`.

### 3.2 Sub-Model 48A — `[Lock Operation Parts]`, Full-Body `MENU + Fn >= 5s` Chord vs Destructive `MENU + Delete >= 2s` Firewall & `[My Dial 1..3]` Override
- Models `MENU -> Setup -> [Operation Customize] -> [Lock Operation Parts]` (`Off` default / `Multi-Slct Only` / `Dial/Wheel` / `Dial+Wheel+MSlct`):
  - **Setup Reset Survival**: Survives `[Camera Settings Reset]` and `[Reset Network Set.]` unchanged; restored to `Off` strictly by `[Initialize]`.
  - **`Fn >= 3s` Toggle vs `MENU + Fn >= 5s/3s` Full-Body Lock Chord**: `Fn >= 3.0s` toggles configured lock scope (`"Locked."` / `"Unlocked."`) when `[Lock Operation Parts] != Off`; `MENU + Fn >= 5.0s` locks all physical buttons, dials, control wheel, and multi-selector except the Shutter button even when `[Lock Operation Parts] = Off`, releasing on `MENU + Fn >= 3.0s`.
  - **Destructive `MENU + Delete >= 2s` Firewall & `[My Dial 1..3]` Temporary Override**: Intercepts any accidental `MENU + Delete` chord (`EROFS = 30` on Slot 1 Tier-0 vault, `EACCES = 13` on Slot 2 / bench, `destructive_menu_delete_confusions == 0`, `slot1_vault_format_events == 0`), and verifies `[My Dial 1..3]` temporarily unlocks standard dials/wheel while recalled under `[Lock Operation Parts]` (while blocked by `EBUSY = 16` under full-body `MENU + Fn` lock).

### 3.3 Sub-Model 48B — `[Audio Out Timing]` vs `[Audio signals]` Persistence & `[Silent Mode]` Hard Lockout
- Models `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]` (`Live` default / `Lip Sync`, resettable by `[Camera Settings Reset]` and `[Initialize]`, surviving `[Reset Network Set.]`, and unavailable in `S&Q Motion` or `[Audio Recording] = Off` with forced bypass blocked via `EOPNOTSUPP = 95`).
- Models `MENU -> Setup -> [Sound Option] -> [Audio signals]` (`On: all` default / `On: shutter only` / `Off: all`, surviving `[Camera Settings Reset]` and `[Reset Network Set.]`, reset only by `[Initialize]`, and forcibly muted whenever `[Silent Mode] = On` while preserving the underlying `[Setup]` register with `silent_mode_audio_signal_leak_events == 0`).

### 3.4 Sub-Model 48C — `[Exposure step]` `0.3EV`/`0.5EV` vs `[Shutter Angle]` Constant-Table Immunity
- Models `MENU -> Exposure/Color -> [Exposure] -> [Exposure step]` (`0.3EV` default / `0.5EV`, resettable to `0.3EV` via `[Camera Settings Reset]` and `[Initialize]`, surviving `[Reset Network Set.]`).
- Verifies `0.5EV` re-quantizes Aperture (`F3.2 -> F3.5`), Shutter Speed (`1/50 -> 1/45`), ISO (`1000 -> 1100`), and Exposure Comp. (`+0.3EV -> +0.5EV`), whereas `Ver. 7.02` (`Ver. 6.00+`) `[Shutter Mode] = [Angle]` (`5.6°..360°`, including `90°`, `172.8°`, `180°`, `360°`) stays 100% constant-table immune (`shutter_angle_exposure_step_drift_events == 0`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h286-phase253-vm-stage48-lock-op-parts-audio-timing-exp-step-hil` and exited `0`.
- **Engineering Inference (工程推断)**: While `ILME-FX3` (`ilc/2210`, `Ver. 7.02`) Help Guide documentation cross-lists `[Lock Operation Parts]` under `[Dial Customize]` / `[Operation Customize]` depending on firmware generation, its `[Setup]` NVRAM partition class, `MENU + Fn >= 5s` full-body lock chord, and `[Shutter Angle]` cine table immunity from `[Exposure step]` behave deterministically across `Ver. 6.00..7.02`; physical camera attachment and eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_lock_op_parts_audio_timing_exp_step_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`66 / 66` PASS** (`3.569s` local donor / `1.787s` clean-room, both `< 4s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2055 / 2055` PASS** (`153.304s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2055` ran (`2052` PASS, `3` donor-only skips)** (`141.463s`, `0` failures) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=48/48 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=48/48 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Full Lab Gate | **`ALL GREEN in 0.04s`** (`0` `.pyc` files across repository) |
