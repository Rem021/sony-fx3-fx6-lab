# Phase 270 (`270th` Milestone) — VM Stage 53 (`53/53`) Real-Hardware `ILME-FX3` Wave-43 `[Release w/o Card]` & `[Release w/o Lens]` (`e_nd_actuator_tx_count == 0`), `Ver. 7.02` (`ilc/2210`) Exact 5-Item `[Audio Recording]` vs `DISP` Audio Meter, and `[Copyright Info]` 46-Char Still EXIF Hygiene & Clean-Room PII Zeroing HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H305` / `codex/h305-phase270-milestone-vm-stage53-release-wo-card-audio-meter-copyright-hil`
- **Target Schema & Stage**: `realhw_release_wo_card_audio_meter_copyright_coemulator_v1` (`version = 270.0.0`, `phase_number = 270`, `is_270th_phase_milestone = True`, `stage = stage53_realhw_release_wo_card_audio_meter_copyright_hil`, advancing `outputs/fx3-vm/` HIL stages from `52/52` to **`53/53`**)
- **Authoritative Wave-43 Reference**: [`reports/2026-11-15-global-sony-wave43-release-wo-card-lens-disp-audio-meter-v2-vs-v1-copyright-info-46char-intel/README.md`](../2026-11-15-global-sony-wave43-release-wo-card-lens-disp-audio-meter-v2-vs-v1-copyright-info-46char-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 270` (`270th` Milestone) Stage 53 (`53/53`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py`](../../outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py) (`schema = realhw_release_wo_card_audio_meter_copyright_coemulator_v1`, `is_270th_phase_milestone = True`) and registered `stage53_realhw_release_wo_card_audio_meter_copyright_hil` (`--include-stage53` / `--skip-stage53` / `--no-include-stage53` / `--skip-phase270` / `stage53_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `52/52` to **`53/53` (`vm_stages=53/53`)**.
2. **Dual-Mode `O_RDONLY` 18-Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **18** real-hardware `ILME-FX3` (`Ver. 7.02`, `ilc/2210`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts — `libInfraLensCommunicator.so`, `libInfraMediaDetect.so`, `libInfraMetaSupplier.so`, `libInfraIPTC.so` (`64,256 B`), `libInfraHotshoe.so`, `libSaveLoadSettings.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `string_english_f.uxc` (`373,820 B`), FX6 `string_english.uxc` (`118,208 B`), and bounded `<= 4096 B` windows in `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4` — strictly via `os.O_RDONLY` (`raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` parity when `FX3_CLEAN_ROOM_TEST=1` or `FX3_FX6_FORCE_CLEAN_ROOM=1` is set:
   - `LOCAL_DONOR_O_RDONLY` digest: `a2d2a8049be6...` (`fx3_vm_coemulation_suite` 53-stage digest `b224dc54c6c5`, `verify-milestone-254` SHA-256 `4a2a659f9b5983e0...`, `verify-milestone-233` SHA-256 `133537f435d4908b...`, `verify-milestone-221` SHA-256 `a86d6a91e76f50dc...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `40503c9169fd...` (`fx3_vm_coemulation_suite` 53-stage digest `20a6251bfb24`, `verify-milestone-254` SHA-256 `4e891f7bcebeabe1...`, `verify-milestone-233` SHA-256 `c3ec1003a60a29e4...`, `verify-milestone-221` SHA-256 `e33b05359dc10317...`)
3. **Hard Safety & Wave-43 Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `emmc_corruptions = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `fx3_has_builtin_end_filter = False`, `e_nd_actuator_tx_count = 0`, `cardless_unrecorded_production_violations = 0`, `legacy_v1_audio_level_menu_spoof_events = 0`, `hdmi_clean_feed_audio_meter_baked_pixels = 0`, `photographer_copyright_pii_leaked_bytes = 0`, `copyright_char_overflow_or_movie_mutation_events = 0`, `slot1_copyright_vault_mutation_bytes = 0`, `camset_copyright_pii_leaked_bytes = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py`](../../outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py) | **NEW** — Phase 270 (`270th` Milestone) Stage 53 (`53/53`) Wave-43 HIL co-emulator (`realhw_release_wo_card_audio_meter_copyright_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage53_realhw_release_wo_card_audio_meter_copyright_hil`, `include_stage53`, `--include-stage53` / `--skip-stage53` / `--no-include-stage53` / `--skip-phase270`, and `stage53_ok` (`53/53`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 270 (`270th` Milestone) Stage 53 (`53/53`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py) | **NEW** — `70` fast dual-mode `unittest` tests (`2.185s` local donor / `0.621s` `FX3_CLEAN_ROOM_TEST=1` / `0.626s` `FX3_FX6_FORCE_CLEAN_ROOM=1`, all `< 4.0s`) |
| 5 | [`reports/2026-11-15-phase270-milestone-vm-stage53-release-wo-card-audio-meter-copyright-hil/README.md`](README.md) | **NEW** — Full `Phase 270` (`270th` Milestone) Stage 53 (`53/53`) engineering & verification report |

---

## 3. Hardware-Exact Wave-43 Co-Emulation Architecture

### 3.1 `O_RDONLY` 18-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves shared BIONZ XR tokens `Release w/o Card`, `Release w/o Lens`, `Audio Recording`, `Audio Rec Level`, `Audio Out Timing`, `Wind Noise Reduct.`, `Shoe Audio Set.`, `DISP`, `Copyright Info`, `Write Copyright Info`, `Set Photographer`, `Set Copyright`, `Disp. Copyright Info`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings`, `Built-In ND`, and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraLensCommunicator.so`, `libInfraMediaDetect.so`, `libInfraMetaSupplier.so`, `libInfraIPTC.so`, `libInfraHotshoe.so`, `libSaveLoadSettings.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, plus bounded `<= 4096 B` windows across `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`.
- Supports both `FX3_CLEAN_ROOM_TEST=1` and `FX3_FX6_FORCE_CLEAN_ROOM=1` environment toggles with deterministic `CLEAN_ROOM_SYNTHETIC` parity (`40503c9169fd...`).

### 3.2 Sub-Model 53A — `[Release w/o Card]` Still-Only Scope vs Movie Media Gate & `[Release w/o Lens]`
- Models `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]` (`Enable` default / `Disable`, Still-image scope only) and `[Release w/o Lens]` (`Enable` default / `Disable`, `Still` + `Movie` + `S&Q` scope); both survive `[Camera Settings Reset]` and `[Reset Network Set.]`, resetting to `Enable` only on `[Initialize]`.
- Exhaustively evaluates `768` states across `bench_posture` (`CARDLESS_DIAGNOSTIC_BENCH` vs `PRODUCTION_SHOOT`), `shooting_domain` (`Still`, `Movie`, `S&Q`), `slot_state` (`EMPTY`, `SLOT1_RO_VAULT`, `SLOT2_SCRATCH`, `BOTH`), `lens_mount_kind` (`EMOUNT_ELECTRONIC_LENS`, `BODY_ONLY_CAP`, `PL_MOUNT_MECHANICAL_ADAPTER`, `TELESCOPE_T_MOUNT`), `[Release w/o Card]`, `[Release w/o Lens]`, and HDMI state:
  - `CARDLESS_DIAGNOSTIC_BENCH` with `Release w/o Card = Enable` permits Still shutter release with `card_bytes_written == 0`, while Movie/`S&Q` internal media recording remains blocked (`EACCES = 13`) when both slots are empty (external HDMI capture stays governed by `[Rec. Media dur HDMI Output]`).
  - `PRODUCTION_SHOOT` with `Release w/o Card = Disable` prevents accidental cardless shoots (`cardless_unrecorded_production_violations == 0`).
  - Body-only / mechanical PL / telescope mounts under `Release w/o Lens = Enable` execute with `0` E-mount lens UART bytes and `e_nd_actuator_tx_count == 0` (`fx3_has_builtin_end_filter == False`, forced e-ND actuator TX blocked with `EOPNOTSUPP = 95`).

### 3.3 Sub-Model 53B — `Ver. 2.00+`/`7.02` (`ilc/2210`) Exact 5-Item `[Audio Recording]` vs `Ver. 1.x` Spoof Rejection & `DISP` Audio Meter
- Enforces the exact **5** items under `MENU -> Shooting -> [Audio Recording]`: `Audio Recording` (`On`/`Off`), `Audio Rec Level` (`0..31`), `Audio Out Timing` (`Live`/`Lip Sync`), `Wind Noise Reduct.` (`On`/`Off`), and `Shoe Audio Set.` (`48kHz/24bit 2ch`, `48kHz/24bit 4ch`, `48kHz/16bit 2ch`).
- Rejects legacy `Ver. 1.x` (`ilc/2035`) standalone `[Audio Level Display]` spoofing with `EOPNOTSUPP = 95` (`legacy_v1_audio_level_menu_spoof_events == 0`).
- Models 2ch / 4ch MI-shoe audio level meter visibility via `MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]` across `72` exhaustive states: automatically suppressed during `S&Q` (`audio_meter_suppressed_by_sq == True`) or `Audio Recording = Off`, never baked onto clean external HDMI (`hdmi_clean_feed_audio_meter_baked_pixels == 0`), and preserves `[DISP (Screen Disp) Set]` across `[Camera Settings Reset]` and `[Reset Network Set.]`.

### 3.4 Sub-Model 53C & Redlines — `[Copyright Info]` `<= 46`-Char Still EXIF Hygiene & Clean-Room PII Zeroing
- Models `MENU -> Shooting -> [File] -> [Copyright Info]` (`Write Copyright Info` `Off` default / `On`, `Set Photographer` `<= 46` chars, `Set Copyright` `<= 46` chars, `Disp. Copyright Info` read-only modal).
- Enforces `<= 46`-char printable ASCII bounds (`0x20..0x7E`, rejecting `47`-char strings and control/non-ASCII bytes with `EINVAL = 22`), Still JPEG/HEIF EXIF-only scope (never mutating `XAVC` / `HDMI RAW` movie streams, blocking forced movie write with `EOPNOTSUPP = 95`), `Slot-1` Tier-0 recovery vault guard (`EROFS = 30`, `slot1_copyright_vault_mutation_bytes == 0`), `[Camera Settings Reset]` (`Write Copyright Info -> Off` while preserving strings) vs `[Initialize]` full wipe, `CAMSET` export PII exclusion (`camset_copyright_pii_leaked_bytes == 0`), and clean-room operator PII zeroing (`photographer_copyright_pii_leaked_bytes == 0`), plus all **16** hard safety redline probes.

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h305-phase270-milestone-vm-stage53-release-wo-card-audio-meter-copyright-hil` and exited `0`.
- **Engineering Inference (工程推断)**: Pinning `Release w/o Card` strictly to Still shutter actuation while gating internal Movie/`S&Q` writes, rejecting legacy `Ver. 1.x` `[Audio Level Display]` spoofing while modeling `DISP` 2ch/4ch meter suppression in `S&Q` and clean HDMI feeds, and isolating `<= 46`-char `[Copyright Info]` EXIF tagging away from movie streams, `Slot-1`, and clean-room exports prevents silent cardless movie failures, audio menu schema drift, and operator PII leaks in offline HIL co-emulation, while live camera attachment and eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_release_wo_card_audio_meter_copyright_coemulator.py` | `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`70 / 70` PASS** (`2.185s` local donor / `0.621s` `FX3_CLEAN_ROOM_TEST=1` / `0.626s` `FX3_FX6_FORCE_CLEAN_ROOM=1`, all `< 4.0s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2395 / 2395` PASS** (`166.433s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_CLEAN_ROOM_TEST=1` | **`2395 / 2395` PASS** (`166.480s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2395` ran (`2392` PASS, `3` donor-only skips)** (`142.078s`, `0` failures) |
| `make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=53/53 leaked=0`** (both modes) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=53/53 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=53/53 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene & BYOF Gate | **`ALL GREEN`** (`0.05s`, `0` `.pyc` files across repository, `0` leaked bytes) |
