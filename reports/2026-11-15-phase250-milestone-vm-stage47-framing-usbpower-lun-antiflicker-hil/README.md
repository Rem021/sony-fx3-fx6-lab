# Phase 250 (`250th` Phase Milestone!) — VM Stage 47 (`47/47` Milestone) Real-Hardware `ILME-FX3` Wave-37 `[Framing Settings]` Asymmetric `Full`/`Crop` & HDMI `RAW` Mutual Exclusion, `[USB Power Supply]` Mandatory `NP-FZ100` + `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence, and `[Anti-flicker Shoot.]` Mechanical-Still-Only & Stock `ILME-FX3` Absence of `[Var. Shutter]` HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H281` / `codex/h281-phase250-milestone-vm-stage47-framing-usbpower-lun-antiflicker-hil`
- **Target Schema & Milestone**: `realhw_framing_usbpower_lun_antiflicker_coemulator_v1` (`version = 250.0.0`, `phase_number = 250`, `is_250th_phase_milestone = True`, `stage = stage47_realhw_framing_usbpower_lun_antiflicker_hil`, advancing `outputs/fx3-vm/` HIL stages to **`47/47`**)
- **Authoritative Wave-37 Reference**: [`reports/2026-11-15-global-sony-wave37-framing-settings-crop-full-usb-power-battery-lun-antiflicker-novarshutter-intel/README.md`](../2026-11-15-global-sony-wave37-framing-settings-crop-full-usb-power-battery-lun-antiflicker-novarshutter-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 250` (`250th` Phase Milestone!) Stage 47 (`47/47`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py`](../../outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py) (`schema = realhw_framing_usbpower_lun_antiflicker_coemulator_v1`) and registered `stage47_realhw_framing_usbpower_lun_antiflicker_hil` (`--include-stage47` / `--skip-stage47` / `--no-include-stage47` / `--skip-phase250` / `stage47_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `46/46` to **`47/47`** across the lab's **250th Phase Milestone**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **15** real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts (`libUsbBusPower.so`, `libInfraMscServer.so`, `libIMDB.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `string_english_f.uxc`, FX6 `string_english.uxc`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`) strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `ea79f2adc21f...` (`fx3_vm_coemulation_suite` 47-stage digest `499f68948c8f...`, `verify-milestone-233` SHA-256 `4ebf5e4ddf6e644d...`, `verify-milestone-221` SHA-256 `3b33642dba59c53b...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `308f7362fa94...` (`fx3_vm_coemulation_suite` 47-stage digest `c7f65be4de35...`, `verify-milestone-233` SHA-256 `0b275034b850ce11...`, `verify-milestone-221` SHA-256 `bee0d523db12b0d3...`)
3. **Hard Safety Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `physical_usb_packets_emitted = 0`, `framing_crop_hdmi_raw_conflict_events = 0`, `zve1_autoframing_conflation_events = 0`, `unbuffered_usb_pd_battery_pull_events = 0`, `multi_micro_usb_power_bypass_events = 0`, `antiflicker_movie_or_eshutter_bypass_events = 0`, `false_var_shutter_or_ecs_node_events = 0`, `fx3_has_var_shutter = False`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py`](../../outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py) | **NEW** — Phase 250 (`250th` Phase Milestone) Stage 47 (`47/47`) Wave-37 HIL co-emulator (`realhw_framing_usbpower_lun_antiflicker_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage47_realhw_framing_usbpower_lun_antiflicker_hil`, `include_stage47`, `--include-stage47` / `--skip-stage47` / `--no-include-stage47` / `--skip-phase250`, and `stage47_ok` (`47/47`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 250 (`250th` Phase Milestone) Stage 47 (`47/47`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_framing_usbpower_lun_antiflicker_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_framing_usbpower_lun_antiflicker_coemulator.py) | **NEW** — `66` fast dual-mode `unittest` tests (`4.77s` local donor / `2.80s` clean-room, both `< 5s`) |
| 5 | [`reports/2026-11-15-phase250-milestone-vm-stage47-framing-usbpower-lun-antiflicker-hil/README.md`](README.md) | **NEW** — Full `Phase 250` Milestone engineering & verification report |

---

## 3. Hardware-Exact Wave-37 Co-Emulation Architecture

### 3.1 `O_RDONLY` 15-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `libUsbBusPower.so` (`48,232 B`: `_ZN11UsbBusPower4MainEv`, `UsbBusPower`, `Backup_read`), `libInfraMscServer.so` (`64,456 B`: `MscServer_Init`, `MassStorageServer_Create`, `ufw_ko_insmod`), `libIMDB.so` (`71,536 B`), `libInfraMediaConfig.so` (`52,312 B`), `libInfraAdjMedia.so` (`318,152 B`), `string_english_f.uxc` (`373,820 B`: proves `Framing Settings`, `Recording/Streaming`, `Crop`, `Full`, `USB Power Supply`, `USB LUN Setting`, `USB Connection Mode`, `Sel. When Connect`, `MassStorage(MSC)`, `Multi`, `Single`, `Anti-flicker Shoot.`, `Silent Mode`, `Camera Settings Reset`, `Initialize`, plus absence of `Autoframing Settings` and `ECS`), and FX6 `string_english.uxc` (`118,208 B`: `ECS`), alongside bounded `<= 4096 B` windows in `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`.

### 3.2 Sub-Model 47A — `[Framing Settings]` Asymmetric `Full`/`Crop` Stream Co-Emulation & HDMI `RAW` Mutual Exclusion
- Models `MENU -> Shooting -> [Framing Settings]` (controllable on-camera or via Sony *Monitor & Control*):
  - `[Framing]` = `Off` (default) / `On`, `[Recording/Streaming]` = `Full` (default) / `Crop`, `[HDMI]` = `Crop` (default) / `Full` — all 3 reset cleanly via `[Camera Settings Reset]` and `[Initialize]`.
- Verifies the factory asymmetric split (`Recording/Streaming = Full` full-frame master capture vs `HDMI = Crop` cropped external monitor), blocks `[Framing] = On` when HDMI `RAW` output is enabled (`EBUSY = 16` / forced bypass `EOPNOTSUPP = 95`, `framing_crop_hdmi_raw_conflict_events == 0`), and rejects consumer `ZV-E1` (`ilc/2330`) `[Autoframing Settings]` conflation on `ILME-FX3` (`ilc/2210`, `EOPNOTSUPP = 95`).

### 3.3 Sub-Model 47B — `[USB Power Supply]` Mandatory `NP-FZ100` Insertion + `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence
- Models `MENU -> Setup -> [USB]` (`[USB Connection Mode] = Sel. When Connect`, `[USB LUN Setting] = Multi`, `[USB Power Supply] = On`):
  - **Setup Reset Survival**: All 3 `[Setup] -> [USB]` items **survive `[Camera Settings Reset]`** unchanged and reset **only** via `[Initialize]`.
  - **Mandatory `NP-FZ100` / `DC-C1` Interlock**: Refuses power-on with an empty battery bay (`EACCES = 13`) and triggers immediate unbuffered power-off protection (`EBUSY = 16`, `unbuffered_usb_pd_battery_pull_events == 0`) on mid-session `NP-FZ100` removal under USB PD wall power.
  - **`USB Type-C` Exclusivity & Live Host USB Hard-Block**: Rejects power delivery and internal charging over `Multi/Micro USB` (`EOPNOTSUPP = 95`, `0 mW`), models `MassStorage(MSC)` `Multi` (`Slot 1` + `Slot 2`) vs `Single` (`Slot 1`) LUN visibility, and hard-blocks live host USB attachment (`EACCES = 13`, `physical_usb_packets_emitted == 0`).

### 3.4 Sub-Model 47C — `[Anti-flicker Shoot.]` Mechanical-Still-Only Boundary & Stock `ILME-FX3` Absence of `[Var. Shutter]`
- Models `MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]` (`Off` default / `On`, resettable via `[Camera Settings Reset]`):
  - Detects `100 Hz` / `120 Hz` lighting flicker **strictly** in `Still` + `Mechanical` shutter + `[Silent Mode] = Off`; grayed out and inactive in `Movie` / `S&Q Motion` or `[Silent Mode] = On` / `Electronic` shutter (forced bypass fails closed with `EOPNOTSUPP = 95`).
  - Enforces `fx3_has_var_shutter == False` (`false_var_shutter_or_ecs_node_events == 0`), rejecting cross-model `ILME-FX30` / `ILCE-6700` `[Var. Shutter]` and `ILME-FX6` `ECS` node queries on stock `ILME-FX3` (`ilc/2210` through `Ver. 7.02`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h281-phase250-milestone-vm-stage47-framing-usbpower-lun-antiflicker-hil` and exited `0`.
- **Engineering Inference (工程推断)**: While the shared ILC string container `string_english_f.uxc` carries sibling Alpha/Cinema string entries in its raw pool, `ILME-FX3` (`0x91030080`, `ilc/2210`) does not expose `[Var. Shutter]` in its active `[Shutter/Silent]` menu tree and lacks `ECS` (`absent_marker_hits["ECS"] == 0` vs FX6 `marker_hits["ECS"] == 1`); physical camera attachment and eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_framing_usbpower_lun_antiflicker_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`66 / 66` PASS** (`4.765s` local donor / `2.799s` clean-room, both `< 5s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`1989 / 1989` PASS** (`155.047s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`1989` ran (`1986` PASS, `3` donor-only skips)** (`142.573s`, `0` failures) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=47/47 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=47/47 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Full Lab Gate | **`ALL GREEN in 0.12s`** (`0` `.pyc` files across repository) |
