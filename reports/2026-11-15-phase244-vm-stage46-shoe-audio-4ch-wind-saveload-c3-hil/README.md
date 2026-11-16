# Phase 244 — VM Stage 46 (`46/46` Milestone) Real-Hardware `ILME-FX3` Wave-36 `[Shoe Audio Set.]` `48kHz/24bit 4ch` vs `3.5mm`/`ANALOG`/`S&Q` Lockouts, `[Wind Noise Reduct.]` Built-In-Mic Exclusivity & Indoor Guard, and `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Firewall & Slot-1 Tier-0 Vault Guard HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H273` / `codex/h273-phase244-vm-stage46-shoe-audio-4ch-wind-saveload-c3-hil`
- **Target Schema & Milestone**: `realhw_shoe_audio_wind_saveload_c3_coemulator_v1` (`version = 244.0.0`, `stage = stage46_realhw_shoe_audio_wind_saveload_c3_hil`, advancing `outputs/fx3-vm/` HIL stages to **`46/46`**)
- **Authoritative Wave-36 Reference**: [`reports/2026-11-15-global-sony-wave36-shoe-audio-4ch-wind-noise-builtin-only-saveload-c3-exclusions-intel/README.md`](../2026-11-15-global-sony-wave36-shoe-audio-4ch-wind-noise-builtin-only-saveload-c3-exclusions-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **Stage 46 (`46/46`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py`](../../outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py) (`schema = realhw_shoe_audio_wind_saveload_c3_coemulator_v1`) and registered `stage46_realhw_shoe_audio_wind_saveload_c3_hil` (`--include-stage46` / `--skip-stage46` / `--no-include-stage46` / `--skip-phase244` / `stage46_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `45/45` to **`46/46`**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity**: Verified all 14 real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `decf311e4643...` (`fx3_vm_coemulation_suite` 46-stage digest `85f7710c1a3d...`, `verify-milestone-221` SHA-256 `20c97fee13e2dab6...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `f81d5b1199e1...` (`fx3_vm_coemulation_suite` 46-stage digest `1c81fd699c9b...`, `verify-milestone-221` SHA-256 `ea652693a98fb63e...`)
3. **Hard Safety Redlines Strictly Locked**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `shoe_audio_4ch_disqualification_bypass_events = 0`, `external_mic_wind_reduct_applied_frames = 0`, `excluded_secret_or_calibration_leak_events = 0`, `tier0_slot1_unverified_camset_save_events = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py`](../../outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py) | **NEW** — Phase 244 Stage 46 (`46/46`) Wave-36 HIL co-emulator (`realhw_shoe_audio_wind_saveload_c3_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage46_realhw_shoe_audio_wind_saveload_c3_hil`, `include_stage46`, `--include-stage46` / `--skip-stage46` / `--skip-phase244`, and `stage46_ok` (`46/46`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 244 Stage 46 (`46/46` milestone) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_shoe_audio_wind_saveload_c3_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_shoe_audio_wind_saveload_c3_coemulator.py) | **NEW** — `64` fast dual-mode `unittest` tests (`2.83s`) covering `LOCAL_DONOR_O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1` |
| 5 | [`reports/2026-11-15-phase244-vm-stage46-shoe-audio-4ch-wind-saveload-c3-hil/README.md`](README.md) | **NEW** — Engineering & verification report |

---

## 3. Hardware-Exact Wave-36 Co-Emulation Architecture

### 3.1 Sub-Model 46A — `[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter Expansion vs 3 Hardware Lockouts
- Models `MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]` (`48kHz/16bit 2ch` factory default, `48kHz/24bit 2ch`, `48kHz/24bit 4ch`), cleanly resettable back to `48kHz/16bit 2ch` via `[Camera Settings Reset]` and recallable from Slot 1 `CAMSET01..10.DAT` with `bk4_persistent_nvram_writes == 0`.
- Automatically expands `[Audio Level Display]` OSD meters from `2ch` (`CH1..CH2`) to `4ch` (`CH1..CH4`) when `48kHz/24bit 4ch` is active on a digital 4ch MI Shoe source (`XLR-H1` in `DIGITAL` mode or `ECM-M1`).
- Enforces all 3 hardware lockouts/overrides (`shoe_audio_4ch_disqualification_bypass_events == 0`; forced bypass attempts fail closed with `EOPNOTSUPP = 95`):
  1. `[Audio Recording] = Off` or `S&Q Motion` -> `0` recorded tracks (`shoe_audio_menu_grayed_out = True`).
  2. Body `3.5mm` stereo `MIC` plug-in priority -> overrides built-in mic and MI Shoe digital transport to `2ch` `48kHz/16bit` analog ADC (`BODY_35MM_ANALOG_ADC_2CH`).
  3. `XLR-H1` `[DIGITAL/ANALOG]` slide switch = `ANALOG` (or analog MI Shoe mic) -> bypasses digital I2S `24bit/4ch` transport to `2ch` `48kHz/16bit` analog (`MI_SHOE_ANALOG_ADC_2CH`).

### 3.2 Sub-Model 46B — `[Wind Noise Reduct.]` Built-In Stereo Mic Exclusivity & Indoor Bench Low-Cut Guard
- Models `MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]` (`Off` default / `On`, resettable via `[Camera Settings Reset]`).
- Functions **exclusively** on the camera body's built-in stereo microphone (`external_mic_wind_reduct_applied_frames == 0` across `3.5mm` `MIC` and MI Shoe `XLR-H1` / `ECM-M1`, where physical `XLR-H1` `[LOW CUT]` `Off`/`100Hz`/`300Hz` switches govern hardware low-cut; forcing body wind DSP onto external mics fails closed with `EOPNOTSUPP = 95`).
- Flags and suppresses indoor bench `[On]` low-frequency attenuation (`EBUSY = 16` when bench guard is enforced) and locks out `[Wind Noise Reduct.]` in `S&Q Motion` or `[Audio Recording] = Off`.

### 3.3 Sub-Model 46C — `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Firewall & Slot-1 Tier-0 Vault Guard
- Models `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]` across `Slot 1` / `Slot 2` (`CAMSET01.DAT..CAMSET10.DAT`, max `10` per card, strict `ILME-FX3` same-model lock rejecting `ILME-FX6` / `ILME-FX3A` with `EOPNOTSUPP = 95`) and `Cloud(Private)` / `Cloud(Share)` (`C3 Portal`, `Ver. 4.00+`).
- Strips on `[Save]` and preserves 100% untouched on `[Load]` all 4 Sony Help Guide excluded categories (`excluded_secret_or_calibration_leak_events == 0`): `IPTC` & `Copyright Info`, `Custom White Balance 1..3`, `Face Memory`, and `FTP`/`Streaming`/`Wi-Fi`/static IP/TLS credentials.
- Blocks `[Save]` targeting a `WP`-locked (`EROFS = 30`) or unverified / non-`WP`-locked (`EBUSY = 16`) Slot 1 Tier-0 forensic vault card (`tier0_slot1_unverified_camset_save_events == 0`), while keeping `[Load]` strictly `O_RDONLY` (`card_sector_writes == 0`) and admitting scratch `[Save]` on `Slot 2`.

---

## 4. Measured Verification Evidence

| Verification Gate | Mode | Result |
|---|---|---|
| `test_realhw_shoe_audio_wind_saveload_c3_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`64 / 64` PASS** (`2.83s` `< 5s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`1923 / 1923` PASS** (`152.04s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`1923` ran (`1920` PASS, `3` donor-only skips)** (`128.71s`, `0` failures) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=46/46 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Full Lab Gate | **PASS** (`0` `.pyc` files across repository) |
