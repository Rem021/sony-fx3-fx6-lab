# Phase 267 — VM Stage 52 (`52/52`) Real-Hardware `ILME-FX3` Wave-42 `[APS-C S35 Shooting]` 12.1MP `4K`/`RAW` Lockout & `Clear Image Zoom` Disjointness, BIONZ XR `[Face/Eye AF]` 4-Item Clean-HDMI Frame Isolation & `[Face Memory]` Persistence, and `[Version]` Read-Only `Ver. 7.02` + `BODYDATA.DAT` Hard-Blocked Flash Guard HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H301` / `codex/h301-phase267-vm-stage52-apsc-s35-face-eye-af-version-hil`
- **Target Schema & Stage**: `realhw_apsc_s35_face_eye_af_version_coemulator_v1` (`version = 267.0.0`, `phase_number = 267`, `stage = stage52_realhw_apsc_s35_face_eye_af_version_hil`, advancing `outputs/fx3-vm/` HIL stages from `51/51` to **`52/52`**)
- **Authoritative Wave-42 Reference**: [`reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md`](../2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 267` Stage 52 (`52/52`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py`](../../outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py) (`schema = realhw_apsc_s35_face_eye_af_version_coemulator_v1`) and registered `stage52_realhw_apsc_s35_face_eye_af_version_hil` (`--include-stage52` / `--skip-stage52` / `--no-include-stage52` / `--skip-phase267` / `stage52_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `51/51` to **`52/52` (`vm_stages=52/52`)**.
2. **Dual-Mode `O_RDONLY` 18-Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **18** real-hardware `ILME-FX3` (`Ver. 7.02`, `ilc/2210`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts — including the 3 Wave-42 version/updater ELF64 libraries `libInfraGetVersion.so` (`10,144 B`, SHA-256 `3a69e737c04b50d120d00e8a0b977f1d60dbb4228abe3b41083e7ab9178be620`), `libupdatermedia.so` (`10,144 B`, SHA-256 `1b5fa6dfd53075afcea591f3a38a1af9a957d6129ea3d180fe1cd562cfdd30db`), and `libupdaterufp.so` (`22,768 B`, SHA-256 `f2e7d27602e3f7b236fc41dd93fccf53ba24f0793fd454e7fec171ae378beca7`) alongside `string_english_f.uxc`, FX6 `string_english.uxc`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4` — strictly via `os.O_RDONLY` bounded `<= 4096 B` windows (`raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` parity when `FX3_CLEAN_ROOM_TEST=1` or `FX3_FX6_FORCE_CLEAN_ROOM=1` is set:
   - `LOCAL_DONOR_O_RDONLY` digest: `560f93422505...` (`fx3_vm_coemulation_suite` 52-stage digest `1e21672ae0d1...`, `verify-milestone-254` SHA-256 `a33c0c4ecb55cdb1...`, `verify-milestone-233` SHA-256 `b1be31ea280ff3c9...`, `verify-milestone-221` SHA-256 `dc2b8ed3b6d41773...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `e69e1d76b296...` (`fx3_vm_coemulation_suite` 52-stage digest `f93bfa55602d...`, `verify-milestone-254` SHA-256 `90f54befdb1307ed...`, `verify-milestone-233` SHA-256 `77fd0cac9cce8e48...`, `verify-milestone-221` SHA-256 `274042c4e6306ce4...`)
3. **Hard Safety & `BODYDATA.DAT` Flash-Block Redlines Strictly Locked (实测事实)**: `bodydata_update_execution_blocked = True`, `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `emmc_corruptions = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `apsc_s35_4k_or_raw_bypass_events = 0`, `apsc_s35_clear_image_zoom_conflation_events = 0`, `face_eye_ai_coprocessor_spoof_accepts = 0`, `hdmi_clean_feed_eye_frame_baked_pixels = 0`, `version_passive_tx_bytes_emitted = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py`](../../outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py) | **NEW** — Phase 267 Stage 52 (`52/52`) Wave-42 HIL co-emulator (`realhw_apsc_s35_face_eye_af_version_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage52_realhw_apsc_s35_face_eye_af_version_hil`, `include_stage52`, `--include-stage52` / `--skip-stage52` / `--no-include-stage52` / `--skip-phase267`, and `stage52_ok` (`52/52`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 267 Stage 52 (`52/52`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_apsc_s35_face_eye_af_version_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_apsc_s35_face_eye_af_version_coemulator.py) | **NEW** — `70` fast dual-mode `unittest` tests (`2.545s` local donor / `0.783s` `FX3_CLEAN_ROOM_TEST=1` / `0.769s` `FX3_FX6_FORCE_CLEAN_ROOM=1`, all `< 4.0s`) |
| 5 | [`reports/2026-11-15-phase267-vm-stage52-apsc-s35-face-eye-af-version-hil/README.md`](README.md) | **NEW** — Full `Phase 267` Stage 52 (`52/52`) engineering & verification report |

---

## 3. Hardware-Exact Wave-42 Co-Emulation Architecture

### 3.1 `O_RDONLY` 18-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves shared BIONZ XR localization tokens `APS-C/Super 35mm`, `APS-C Size Capture`, `Clear Image Zoom`, `Face/Eye AF`, `Face/Eye Priority in AF`, `Face/Eye Subject`, `Right/Left Eye Select`, `Face/Eye Frame Display`, `Regist. Faces Priority`, `Face Memory`, `HDMI Info. Display`, `Version`, `Airplane Mode`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings`, `Version Update`, and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraGetVersion.so` (`InfraGetVersion`, `InfraGetVersionLens`, `GetVersion_init`, `GetVersion_exit`, `rcv_async_thread_lens`), `libupdatermedia.so` (`UDTR_MEDIA`, `udtr_get_media_path`, `getMediaInfo`), and `libupdaterufp.so` (`/BODYDATA.DAT`, `LENSDATA.DAT`, `/dev/nflasha1`, `udtr_get_firm_info_inmedia`, `udtr_write_firm_from_media`), alongside bounded `<= 4096 B` windows in `appFw.so`, `cpapp-b.bin`, `libmpr.so`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, and `BK4`.
- Supports both `FX3_CLEAN_ROOM_TEST=1` and `FX3_FX6_FORCE_CLEAN_ROOM=1` environment toggles with bit-for-bit identical `CLEAN_ROOM_SYNTHETIC` reports (`e69e1d76b296...`).

### 3.2 Sub-Model 52A — `[APS-C S35 Shooting]` 12.1MP `4K`/`RAW` Hard-Lockout & `Clear Image Zoom` Disjointness
- Models `MENU -> Shooting -> [Image Quality] -> [APS-C S35 Shooting]` (`Auto` factory default / `On` / `Off`; survives `[Reset Network Set.]` and resets to `Auto` on `[Camera Settings Reset]` and `[Initialize]`).
- Because `ILME-FX3` uses a `12.1 MP` (`4240 x 2832` still / `4264 x 2408` RAW) Full-Frame sensor whose `1.5x` APS-C / Super 35mm crop (`2768 x 1848`, `~5.1 MP`) lacks native `3840 x 2160` photosites, `[APS-C S35 Shooting]` is **HARD-LOCKED (`Off` / grayed out)** across all **5** `4K` / `RAW` formats (`XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`, `DCI 4K`, and `HDMI RAW Output`), rejecting forced activation with `EINVAL = 22` (`apsc_s35_4k_or_raw_bypass_events == 0` across all `144` exhaustive format x setting x lens x zoom states).
- Active only in `XAVC S HD`, `XAVC S-I HD` (`Auto` follows E-mount APS-C `SELP18105G` = `On` vs Full-Frame `SEL2470GM2` = `Off`, while manual `On` crops `1.5x` on FF lenses), and `Still Image` (`~5.1 MP`), while `Clear Image Zoom` (`1.5x` in `4K` / `DCI 4K`, `2.0x` in `HD`, unavailable in `HDMI RAW Output`) remains strictly orthogonal (`apsc_s35_clear_image_zoom_conflation_events == 0`).

### 3.3 Sub-Model 52B — BIONZ XR `[Face/Eye AF]` 4-Item Contract, Clean-HDMI Frame Isolation & `[Face Memory]` Persistence
- Models `MENU -> Focus -> [Face/Eye AF]` with all **4** hardware-exact `ILME-FX3` BIONZ XR items (`Face/Eye Priority in AF` `On`/`Off`, `Subject Recognition in AF` `Human`/`Animal`, `Right/Left Eye Select` `Auto`/`Right Eye`/`Left Eye` plus custom-key `[Switch Right/Left Eye]` toggle `Auto -> Right Eye -> Left Eye -> Right Eye`, and `Face/Eye Frame Display` `On`/`Off`) alongside `[Face Memory]` (`0..8` registered faces) and `[Regist. Faces Priority]` (`On`/`Off`).
- Strictly rejects spoofed dedicated AI-coprocessor subjects (`Bird`, `Insect`, `Car/Train`, `Airplane` from `ILME-FX2` / `ZV-E1` / `ILCE-7RM5`) with `EOPNOTSUPP = 95` (`face_eye_ai_coprocessor_spoof_accepts == 0`, while Animal Eye AF locks `[Right/Left Eye Select]` unavailable with `EINVAL = 22`).
- Enforces Clean External HDMI isolation: when `HDMI Info. Display = Off` (or `HDMI RAW Output = On`), `[Face/Eye Frame Display] = [On]` renders tracking boxes on the camera LCD (`lcd_eye_frame_rendered == True`) and **never** burns boxes into the external HDMI feed (`hdmi_clean_feed_eye_frame_baked_pixels == 0`).
- Verifies reset split: the 4 `[Face/Eye AF]` items and `[Regist. Faces Priority]` reset to defaults on `[Camera Settings Reset]`, whereas `[Face Memory]` enrolled slots survive both `[Camera Settings Reset]` and `[Reset Network Set.]` and clear **only** via explicit `[Delete]` or `[Initialize]`.

### 3.4 Sub-Model 52C — `[Version]` Read-Only `Ver. 7.02` + Lens Inspection, `Airplane Mode` Badge Suppression & `BODYDATA.DAT` Hard-Blocked Flash Guard
- Models `MENU -> Setup -> [Setup Option] -> [Version]` (`Body = Ver. 7.02` `ILME-FX3` `ilc/2210` + attached E-mount lens `SEL2470GM2 Ver. 02` / `SELP18105G Ver. 01` / `LA-EA5 Ver. 02`, or `Lens = --` on manual/unmounted glass) strictly as a read-only modal backed by `libInfraGetVersion.so` (`InfraGetVersion` / `InfraGetVersionLens`).
- Verifies `[Airplane Mode] = [On]` suppresses Creators' App Bluetooth/Wi-Fi firmware update notification badges with `passive_tx_bytes_emitted == 0` across all states.
- Hard-blocks any SD / CFexpress `/BODYDATA.DAT`, `/LENSDATA.DAT`, or `[Version Update]` execution path (`libupdatermedia.so` / `libupdaterufp.so` -> `/dev/nflasha*`) with `EROFS = 30` (`bodydata_update_execution_blocked == True`, `physical_device_writes == 0`, `emmc_corruptions == 0`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h301-phase267-vm-stage52-apsc-s35-face-eye-af-version-hil` and exited `0`.
- **Engineering Inference (工程推断)**: Modeling Sony's 12.1MP sensor `[APS-C S35 Shooting]` `4K`/`RAW` lockout separately from `1.5x` `Clear Image Zoom`, isolating `[Face/Eye Frame Display]` LCD overlays from clean external `HDMI Info. Display = Off` capture while rejecting dedicated AI-coprocessor subject spoofing, and enforcing read-only `[Version]` inspection with `BODYDATA.DAT` flash execution hard-blocked prevents silent field-of-view mismatches, burned-in HDMI tracking overlays, and accidental flash-updater execution in offline HIL simulation, while live camera attachment and eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_apsc_s35_face_eye_af_version_coemulator.py` | `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`70 / 70` PASS** (`2.545s` local donor / `0.783s` `FX3_CLEAN_ROOM_TEST=1` / `0.769s` `FX3_FX6_FORCE_CLEAN_ROOM=1`, all `< 4.0s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2325 / 2325` PASS** (`189.144s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_CLEAN_ROOM_TEST=1` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2325` ran (`2322` PASS, `3` donor-only skips)** (`160.229s`, `0` failures) |
| `make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=52/52 leaked=0`** (both modes) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=52/52 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=52/52 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene & BYOF Gate | **`ALL GREEN`** (`0.05s`, `0` `.pyc` files across repository, `0` leaked bytes) |
