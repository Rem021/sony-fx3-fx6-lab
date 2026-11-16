# Phase 262 — VM Stage 51 (`51/51`) Real-Hardware `ILME-FX3` Wave-41 `[Auto Slow Shutter]` 6-Condition Lockout & `Ver. 7.02` `[Shutter Angle]` Disjointness, `[HDMI Output Settings]` `REC Control` <- `Time Code Output` Gate & `4ch Audio Output` + Slot-1 Vault Guard, and `[Breathing Comp.]` Movie-Only Compliant-Lens Crop & RAW/240p Lockout HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H295` / `codex/h295-phase262-vm-stage51-auto-slow-shutter-hdmi-reccontrol-breathing-hil`
- **Target Schema & Stage**: `realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1` (`version = 262.0.0`, `phase_number = 262`, `stage = stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil`, advancing `outputs/fx3-vm/` HIL stages from `50/50` to **`51/51`**)
- **Authoritative Wave-41 Reference**: [`reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md`](../2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 262` Stage 51 (`51/51`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py`](../../outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py) (`schema = realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1`) and registered `stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil` (`--include-stage51` / `--skip-stage51` / `--no-include-stage51` / `--skip-phase262` / `stage51_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `50/50` to **`51/51` (`vm_stages=51/51`)**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **15** real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts (`string_english_f.uxc`, FX6 `string_english.uxc`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`) strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `f16406e13a5e...` (`fx3_vm_coemulation_suite` 51-stage digest `de9d2e0a7b8e...`, `verify-milestone-254` SHA-256 `637713780a1cde8a...`, `verify-milestone-233` SHA-256 `bcd435222dffc45c...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `43aa56dff311...` (`fx3_vm_coemulation_suite` 51-stage digest `1ef930d4a21b...`, `verify-milestone-254` SHA-256 `178f3266b4d7e992...`, `verify-milestone-233` SHA-256 `43815857647a4394...`)
3. **Hard Safety Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `auto_slow_shutter_lockout_bypass_events = 0`, `auto_slow_shutter_angle_overlap_events = 0`, `hdmi_rec_ctrl_without_tc_violations = 0`, `slot1_hdmi_rec_vault_mutation_bytes = 0`, `breathing_comp_raw_or_240p_bypass_events = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py`](../../outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py) | **NEW** — Phase 262 Stage 51 (`51/51`) Wave-41 HIL co-emulator (`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil`, `include_stage51`, `--include-stage51` / `--skip-stage51` / `--no-include-stage51` / `--skip-phase262`, and `stage51_ok` (`51/51`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 262 Stage 51 (`51/51`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py) | **NEW** — `66` fast dual-mode `unittest` tests (`2.876s` local donor / `0.787s` clean-room, both `< 4s`) |
| 5 | [`reports/2026-11-15-phase262-vm-stage51-auto-slow-shutter-hdmi-reccontrol-breathing-hil/README.md`](README.md) | **NEW** — Full `Phase 262` Stage 51 (`51/51`) engineering & verification report |

---

## 3. Hardware-Exact Wave-41 Co-Emulation Architecture

### 3.1 `O_RDONLY` 15-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves `Auto Slow Shutter`, `Shutter Mode`, `Angle`, `Flexible Exp. Mode`, `Log Shooting`, `Cine EI`, `Cine EI Quick`, `Flexible ISO`, `HDMI Output Settings`, `REC Control`, `Time Code Output`, `4ch Audio Output`, `CH1/CH2`, `CH3/CH4`, `Rec. Media dur HDMI Output`, `Output Resolution`, `RAW Output`, `Lens Compensation`, `Breathing Comp.`, `Proxy Recording`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings` and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraAdjMedia.so`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, and `libInfraMediaConfig.so`, alongside bounded `<= 4096 B` windows in `appFw.so` (`SHUTTER`, `HDMI`, `TIMECODE`, `AUDIO`, `BREATH`, `LENS`, `RAW`, `RESET`), `cpapp-b.bin` (`Shutter`, `HDMI`, `Audio`, `Lens`, `Time`, `Initialize`), `libmpr.so`, and `BK4`.

### 3.2 Sub-Model 51A — `[Auto Slow Shutter]` 6-Condition Lockout & `Ver. 7.02` `[Shutter Angle]` Disjointness
- Models `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]` (`On` factory default / `Off`, dropping shutter floor from `1/60 s` to `1/30 s` in dark scenes when active; survives `[Reset Network Set.]` and resets to `On` on `[Camera Settings Reset]` and `[Initialize]`).
- Enforces all **6** exact Sony `ILME-FX3` hardware non-function lockouts: (1) `S&Q Motion`, (2) `Movie: Shutter Priority (S)`, (3) `Movie: Manual Exposure (M)`, (4) `[ISO] != [ISO AUTO]` (`ISO 800`), (5) `[Flexible Exp. Mode]` with manual shutter speed, and (6) `[Log Shooting]` set to `[Cine EI Quick]` or `[Cine EI]` (`EINVAL = 22` on forced bypass, `auto_slow_shutter_lockout_bypass_events == 0`).
- Proves strict `Ver. 7.02` (`Ver. 6.00+`) disjointness with `[Shutter Mode] = [Angle]` (`180.0 deg`): `[Shutter Angle]` requires manual shutter / `S` / `M` / `Flexible Exp. Manual Shutter` and is disabled in `S&Q`, so `[Auto Slow Shutter]` and `[Shutter Angle]` can never be simultaneously active (`auto_slow_shutter_angle_overlap_events == 0`).

### 3.3 Sub-Model 51B — `[HDMI Output Settings]` `REC Control` <- `Time Code Output` Gate, `4ch Audio Output` & Slot-1 Vault Guard
- Models `MENU -> Setup -> [External Output] -> [HDMI Output Settings]` (`Output Resolution = Auto`, `24p/60p Output = 60p`, `HDMI Info. Display = Off`, `Time Code Output = Off` default / `On`, `REC Control = Off` default / `On`, `4ch Audio Output = CH1/CH2` default / `CH3/CH4`, `Rec. Media dur HDMI Output = Off` default / `On`), surviving both `[Camera Settings Reset]` and `[Reset Network Set.]` and resetting only via `[Initialize]`.
- Enforces the mandatory Sony hardware prerequisite `[Time Code Output] = [On]` before `[REC Control] = [On]` can trigger external HDMI recorders (`EINVAL = 22` if `Time Code Output = Off`, auto-disarming `REC Control` if `Time Code Output` returns to `Off`; `hdmi_rec_ctrl_without_tc_violations == 0`).
- Verifies `[4ch Audio Output]` 2-channel HDMI pair routing (`CH1/CH2` vs `CH3/CH4`) and `[Rec. Media dur HDMI Output] = [Off]` internal Slot-1/Slot-2 movie clip + `[Proxy Recording]` inhibition while blocking mutating Slot-1 vault writes (`EROFS = 30`, `slot1_hdmi_rec_vault_mutation_bytes == 0`).

### 3.4 Sub-Model 51C — `[Lens Compensation]` -> `[Breathing Comp.]` Movie-Only Compliant-Lens Crop & RAW/240p Lockout
- Models `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]` (`Off` factory default / `On`, surviving `[Reset Network Set.]` and resetting to `Off` on `[Camera Settings Reset]` and `[Initialize]`).
- Applies movie-only compliant E-mount FOV crop (`SEL2470GM2` `0.93x`, `SEL50F12GM` `0.91x`, `SELP1635G` `0.94x`; inactive in Still mode `1.00x` and non-compliant `SEL24105G` `1.00x`), while strictly locking out `[Breathing Comp.]` during `4264 x 2408` 16-bit `HDMI RAW Output` and `S&Q` `239.76p` (`240fps`) / `200p` (`200fps`) (`EINVAL = 22` on forced bypass, `breathing_comp_raw_or_240p_bypass_events == 0`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h295-phase262-vm-stage51-auto-slow-shutter-hdmi-reccontrol-breathing-hil` and exited `0`.
- **Engineering Inference (工程推断)**: Modeling Sony's 6-condition `[Auto Slow Shutter]` lockout and `Ver. 7.02` `[Shutter Angle]` mutual exclusion, `[HDMI Output Settings]` `REC Control <- Time Code Output` dependency + `Rec. Media dur HDMI Output = Off` internal media/proxy inhibition, and `[Breathing Comp.]` compliant-lens crop / `RAW` & `240p` lockouts prevents silent external-recorder trigger failures and unintended FOV/shutter shifts during offline bench validation, while physical camera attachment and persistent eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`66 / 66` PASS** (`2.876s` local donor / `0.787s` clean-room, both `< 4s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2255 / 2255` PASS** (`208.341s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2255` ran (`2252` PASS, `3` donor-only skips)** (`170.453s`, `0` failures) |
| `make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=51/51 leaked=0`** (both modes) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=51/51 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene & BYOF Gate | **`ALL GREEN`** (`0` `.pyc` files across repository, `0` leaked bytes) |
