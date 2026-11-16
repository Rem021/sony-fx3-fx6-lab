# Phase 257 — VM Stage 49 (`49/49` Milestone) Real-Hardware `ILME-FX3` Wave-39 `[Display Quality]` (`Standard`/`High`) Battery Conservation Bench Guard, `[Bluetooth Rmt Ctrl]` Infrared `SIRCS` Lockout & 3-Way `[Reset Network Set.]` Split, and `[My Menu Setting]` / `[Display From My Menu]` 6-Operation Persistence & Slot-1 `CAMSET01.DAT` Vault HIL Co-Emulator

- **Date**: `2026-11-15`
- **Task / Branch**: `H289` / `codex/h289-phase257-vm-stage49-display-quality-bt-rmt-mymenu-hil`
- **Target Schema & Milestone**: `realhw_display_quality_bt_rmt_mymenu_coemulator_v1` (`version = 257.0.0`, `phase_number = 257`, `stage = stage49_realhw_display_quality_bt_rmt_mymenu_hil`, advancing `outputs/fx3-vm/` HIL stages to **`49/49`**)
- **Authoritative Wave-39 Reference**: [`reports/2026-11-15-global-sony-wave39-display-quality-battery-bt-rmt-ctrl-ir-lockout-network-reset-mymenu-persist-intel/README.md`](../2026-11-15-global-sony-wave39-display-quality-battery-bt-rmt-ctrl-ir-lockout-network-reset-mymenu-persist-intel/README.md)

---

## 1. Executive Summary (结论先行)

1. **`Phase 257` Stage 49 (`49/49`) HIL Co-Emulator Delivered**: Created [`outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py`](../../outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py) (`schema = realhw_display_quality_bt_rmt_mymenu_coemulator_v1`) and registered `stage49_realhw_display_quality_bt_rmt_mymenu_hil` (`--include-stage49` / `--skip-stage49` / `--no-include-stage49` / `--skip-phase257` / `stage49_ok`) inside [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), advancing `FX3-VM` full-board co-emulation stages from `48/48` to **`49/49`**.
2. **Dual-Mode `O_RDONLY` Donor Inspection + `CLEAN_ROOM_SYNTHETIC` Parity (实测事实)**: Verified all **15** real-hardware `ILME-FX3` (`Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) donor artifacts (`string_english_f.uxc`, FX6 `string_english.uxc`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, `libInfraMediaConfig.so`, `libInfraAdjMedia.so`, `appFw.so`, `cpapp-b.bin`, `libmpr.so`, and `BK4`) strictly via `os.O_RDONLY` bounded `<= 4096 B` windows in `< 0.02s` cold (`< 0.001s` cached, `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent:
   - `LOCAL_DONOR_O_RDONLY` digest: `665d703c0b35...` (`fx3_vm_coemulation_suite` 49-stage digest `c7527ca88ce4...`, `verify-milestone-233` SHA-256 `437c61f9eca91cd0...`, `verify-milestone-221` SHA-256 `8f4d7978295b43fa...`)
   - `CLEAN_ROOM_SYNTHETIC` digest: `8c490b40c588...` (`fx3_vm_coemulation_suite` 49-stage digest `28f21b1b0b09...`, `verify-milestone-233` SHA-256 `05145266d139a541...`, `verify-milestone-221` SHA-256 `992cb90576720a6f...`)
3. **Hard Safety Redlines Strictly Locked (实测事实)**: `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`, `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`, `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, `physical_device_writes = 0`, `nop_count = 0`, `guest_code_modification_bytes = 0`, `tier0_battery_high_display_violations = 0`, `passive_tx_bytes_emitted = 0`, `bt_rmt_ir_lockout_violations = 0`, `slot1_mymenu_vault_mutation_bytes = 0`, `raw_firmware_bytes_leaked = 0`, and zero `.pyc` bytecode files.

---

## 2. Owned Files Modified / Created (Strict 5-File Scope)

| # | File | Role |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py`](../../outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py) | **NEW** — Phase 257 Stage 49 (`49/49`) Wave-39 HIL co-emulator (`realhw_display_quality_bt_rmt_mymenu_coemulator_v1`) |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | Registered `stage49_realhw_display_quality_bt_rmt_mymenu_hil`, `include_stage49`, `--include-stage49` / `--skip-stage49` / `--no-include-stage49` / `--skip-phase257`, and `stage49_ok` (`49/49`) |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | Documented Phase 257 Stage 49 (`49/49`) architecture and dual-mode CLI commands |
| 4 | [`outputs/fx3-vm/tests/test_realhw_display_quality_bt_rmt_mymenu_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_display_quality_bt_rmt_mymenu_coemulator.py) | **NEW** — `66` fast dual-mode `unittest` tests (`3.750s` local donor / `1.569s` clean-room, both `< 4s`) |
| 5 | [`reports/2026-11-15-phase257-vm-stage49-display-quality-bt-rmt-mymenu-hil/README.md`](README.md) | **NEW** — Full `Phase 257` Stage 49 engineering & verification report |

---

## 3. Hardware-Exact Wave-39 Co-Emulation Architecture

### 3.1 `O_RDONLY` 15-Donor Verification (`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`)
- Inspects `string_english_f.uxc` (`373,820 B`: proves `Display Quality`, `Standard`, `High`, `Monitor`, `Brightness`, `Manual`, `Battery`, `Bluetooth Rmt Ctrl`, `Bluetooth Function`, `Bluetooth`, `Airplane Mode`, `Remote`, `IR Remote`, `My Menu`, `Display From My Menu`, `Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, `Save/Load Settings`, `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`, plus absence of `Autoframing Settings` and `ECS`), FX6 `string_english.uxc` (`118,208 B`), `libInfraAdjMedia.so`, `libIMDB.so`, `libUsbBusPower.so`, `libInfraMscServer.so`, and `libInfraMediaConfig.so`, alongside bounded `<= 4096 B` windows in `appFw.so` (`DISPLAY`, `MONITOR`, `BLUETOOTH`, `CAMSET`, `SIRCS`, `MYMENU`), `cpapp-b.bin` (`Display`, `Monitor`, `Remote`, `SIRCS`), `libmpr.so`, and `BK4`.

### 3.2 Sub-Model 49A — `[Display Quality]` `Standard`/`High` Battery Conservation Bench Guard
- Models `MENU -> Setup -> [Monitor] -> [Display Quality]` (`Standard` default / `High`):
  - **Setup Reset Survival**: Survives BOTH `[Camera Settings Reset]` and `[Reset Network Set.]` unchanged; restored to `Standard` strictly by `[Initialize]`.
  - **Battery Conservation & Tier-0 Bench Clamp**: Models accelerated `NP-FZ100` (`16.4 Wh`) live-view SoC/panel consumption in `[High]`, and clamps internal-battery Tier-0 `pnflasha`/`cnflasha` bench dumps to `[Display Quality] = Standard` + `[Monitor Brightness] = Manual(0)` (rejecting unclamped/forced bypass attempts with `EACCES = 13`, `tier0_battery_high_display_violations == 0`).

### 3.3 Sub-Model 49B — `[Bluetooth Rmt Ctrl]` Infrared `SIRCS` Lockout & 3-Way `Reset Network Set.` Split
- Models `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]` (`Off` default / `On`):
  - **Radio Prerequisite & Zero-RF Bench Suppression**: Requires `[Bluetooth Function] = On` + `[Airplane Mode] = Off` (`EOPNOTSUPP = 95` on forced prerequisite bypass), remaining suppressed on our zero-RF `Airplane Mode = On` bench (`EACCES = 13` on forced RF TX, `passive_tx_bytes_emitted == 0`).
  - **Infrared Remote (`SIRCS`) Mutual Exclusion**: Locks out Infrared Remote Commander (`SIRCS`) commands whenever `[Bluetooth Rmt Ctrl] = On` (`EBUSY = 16` on forced bypass, `bt_rmt_ir_lockout_violations == 0`).
  - **3-Way Reset Split**: Proves `[Bluetooth Rmt Ctrl]` survives `[Camera Settings Reset]`, is reset to `Off` by `[Reset Network Set.]` (re-unlocking `[Setup]`-resident `[IR Remote Ctrl]`), and is reset to `Off` alongside `[IR Remote Ctrl]` by `[Initialize]`.

### 3.4 Sub-Model 49C — `[My Menu Setting]` / `[Display From My Menu]` 6-Operation Persistence & `CAMSET01.DAT` Vault
- Models `MENU -> My Menu -> [My Menu Setting]` (`Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, up to `6 pages x 6 items = 36 items` with `ENOSPC = 28` overflow guard, plus `[Display From My Menu]` `Off` default / `On` menu landing router).
- Verifies survival across BOTH `[Camera Settings Reset]` and `[Reset Network Set.]` (cleared only via `[Delete All]` / `[Delete Page]` or `[Initialize]`), and proves `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` restoration after `[Initialize]` while blocking mutating Slot-1 vault writes (`EROFS = 30`, `slot1_mymenu_vault_mutation_bytes == 0`).

---

## 4. Measured Verification Evidence vs Engineering Inference

- **Measured Facts (实测事实)**: Every command in the table below was executed with `PYTHONDONTWRITEBYTECODE=1` and `/usr/bin/python3 -B` on branch `codex/h289-phase257-vm-stage49-display-quality-bt-rmt-mymenu-hil` and exited `0`.
- **Engineering Inference (工程推断)**: While `ILME-FX3` (`ilc/2210`, `Ver. 7.02`) exact live-view wattage depends on ambient temperature and lens actuator draw, `[Display Quality] = [High]` demonstrably increases SoC/panel power consumption relative to `[Standard]`; clamping Tier-0 battery bench reads to `[Standard]` + `Manual(0)` while keeping `[Airplane Mode] = [On]` (`passive_tx_bytes_emitted == 0`) maximizes brownout safety, and physical camera attachment / eMMC writes remain strictly prohibited (`overall_ready_for_hardware_attach == False`).

| Verification Gate | Mode | Measured Result |
|---|---|---|
| `test_realhw_display_quality_bt_rmt_mymenu_coemulator.py` | `LOCAL_DONOR_O_RDONLY` & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`66 / 66` PASS** (`3.750s` local donor / `1.569s` clean-room, both `< 4s`) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2121 / 2121` PASS** (`182.965s`, `0` failures) |
| Full `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2121` ran (`2118` PASS, `3` donor-only skips)** (`171.585s`, `0` failures) |
| `make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=49/49 leaked=0`** (both modes) |
| `make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=49/49 leaked=0`** (both modes) |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Full Lab Gate | **`ALL GREEN in 1.56s`** (`0` `.pyc` files across repository) |
