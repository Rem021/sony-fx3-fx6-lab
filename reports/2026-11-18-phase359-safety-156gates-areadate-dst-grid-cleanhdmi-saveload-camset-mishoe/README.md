# Phase 359 (`Task H451`, Wave-68, `156/156` Hardware Safety Gates): `[Area/Date/Time Setting]` 30 GMT Zones / RTC vs FX6 `Clock Set` + `[Grid Line]` HDMI Pass-Through vs `[Marker Display]` Zero-HDMI & Reset Firewall (`G155`) and `[Save/Load Settings]` `Slot 1` `EROFS=30` `CAMSET01..10.DAT` Vault + Zero `Sync Terminal` & `XLR-H1` vs `HVL-LBPC` MI-Shoe Exclusion / `PMIC 5V <= 900 mA` vs FX6 `TC IN/OUT` & Zero `GENLOCK` (`G156`)

- **Date**: `2026-11-18`
- **Task / Phase**: `H451` · **Phase 359 (`156/156` Safety Gates Milestone)**
- **Wave Ground Truth**: [Wave-68 Empirical Report](../2026-11-17-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/README.md) & [`realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulator.py`](../../outputs/fx3-vm/realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulator.py)
- **Hardware Safety Posture**: Strictly read-only `os.O_RDONLY` + bounded `os.pread` across 12 local donor artifacts with deterministic clean-room fallback (`raw_firmware_bytes_leaked == 0`, `emmc_writes_authorized == False`, `cross_model_flash_authorized == False`, `hardware_live_attachment_authorized == False`, `usb_packets_transmitted == 0`).

---

## 1. Deliverables & Strict Domain Ownership

- Guard module: [`realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.py`](../../outputs/fx3-safety/fx3_safety/realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.py)
- Package exports & CLI wiring: [`fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py), [`fx3_safety/__main__.py`](../../outputs/fx3-safety/fx3_safety/__main__.py) (`verify-areadate-grid-cleanhdmi-guard` / `verify-g155`, `verify-saveload-camset-mishoe-genlock-guard` / `verify-g156`, `verify-156-gates`), [`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md)
- Unit test suite (`104` tests, 4-mode): [`test_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_156gate_guard.py`](../../outputs/fx3-safety/tests/test_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_156gate_guard.py)

---

## 2. Implemented Safety Gates

### 2.1 Gate `G155`: `AREADATE_30ZONE_RTC_AND_GRID_LINE_VS_MARKER_CLEANHDMI_RESET_GUARD`
- **`Setup -> [Area/Date] -> [Area/Date/Time Setting]`** (`_f 0x6a9c`):
  - **Reset-immune (`Not available` under `[Camera Settings Reset]`)**: cleared and re-triggers `37dlg_rec203_initial_setting_controller` / `PRM_launch_date_time_setup_area_setting` **only** via `[Initialize]` or RTC depletion.
  - Enforces **30** `AREA_GMT_*` zones (`GMT_M_11_0`..`GMT_P_12_0`) including **6** `:30` half-hour offsets (`M_03_5`, `P_03_5`, `P_04_5`, `P_05_5`, `P_06_5`, `P_09_5`), `[Daylight Savings]` (`Off`/`On`, Sony ELF typo `convert_setting_daylight_saving_to_saylight_saving`), `[Date/Time]` (24h, `BKID_APP_setting_auto_sync_sever_date_time`), and exact **3** `[Date Format]` options (`Y-M-D`, `M-D-Y`, `D-M-Y`; rejects `YYYY-MM-DD`).
  - Internal soldered rechargeable RTC backup battery (`>= 24h` power-off charge from `NP-FZ100`/USB-PD; **zero** user-replaceable CR2032 slot -> `EOPNOTSUPP=95`; rejects fabricated `"3 months"` `ilc/2210` claim -> `EINVAL=22`), contrasted with `ILME-FX6` `Maintenance > Clock Set` (`UTC -12:00..+14:00` in 30m steps, `YYMMDD/MMDDYY/DDMMYY` + `12h/24h`, zero standalone DST toggle -> `EOPNOTSUPP=95`, `Backup Battery End`).
- **`[Grid Line Display]` / `[Grid Line Type]` vs `[Marker Display]` Clean-HDMI & Reset Firewall**:
  - `[Grid Line Display]` (`Off`/`On`) & `[Grid Line Type]` (`Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid`) operate across **Still / Movie / `S&Q`** (retired `BKID_APP_deleted_setting_grid_line_*_movie` -> `EOPNOTSUPP=95`) and **pass out HDMI** when `[HDMI Info. Display] = On` & non-clean-feed (`Off(HDMI Only)` / `RAW Output = On` strips it).
  - `[Marker Display]` (`Center Marker`, **15** `Aspect Marker` ratios, `Safety Zone` `80%/90%`, `Guideframe`) is strictly **Movie/`S&Q`-only** (`PRM_HAITA_setting_marker_display_exposure_mode` rejects Still -> `EOPNOTSUPP=95`), auto-hidden during `Focus Magnifier`, and **NEVER output over HDMI regardless of `[HDMI Info. Display]`** (`hdmi_marker_injected_pixels == 0`).
  - Both `[Grid Line Display/Type]` and all **5** `[Marker Display]` items are **Reset-immune `Not available`** in `ilc/2210` (consistent with `G89`), contrasted with `ILME-FX6` `Monitoring > Marker` (`384` matrix states).

### 2.2 Gate `G156`: `SAVELOAD_SLOT1_EROFS_CAMSET_VAULT_AND_MISHOE_XLRH1_ZERO_SYNC_GENLOCK_FIREWALL`
- **`[Save/Load Settings]` `Slot 1` `EROFS=30` `CAMSET01..10.DAT` Vault & `Camera Set. Memory`**:
  - `Setup -> [Reset/Save Settings] -> [Save/Load Settings]` (`libSaveLoadSettings.so` `18,760 B`, locked strictly to **`Slot 1` only** for up to **10** `CAMSET01..10.DAT` files + `60` Cloud slots, disabled in `MR` mode -> `EOPNOTSUPP=95`, auto-reboots on Load).
  - Enforces `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` (`/PRIVATE` on SDXC, `""` on CFexpress Type A), **zero `PRO/CAMERA` path hits** on FX3, same-model & `Ver. <= 1.01` -> `Ver. 2.00+` incompatibility checks, `20`-item official exclusion list, `[Save/Load FTP Settings]` (`FTPSET%02d`, `Slot 1` only), and `[Camera Set. Memory]` (`1..3` NVRAM vs `M1..M4` `CAMPR%02d%c.DAT` on `Slot 1` or `Slot 2`).
  - Hard **`EROFS=30`** firewall blocks any `Save`/`Delete`/write targeting Tier-0 read-only `Slot 1` (`slot1_data_sector_writes == 0`, `emmc_nflasha_write_count == 0`), contrasted with FX6 `Project > All File` (`Media(B)` max 64 `.ALL`) and dormant `Reference File` (`0` ELF hits -> `EOPNOTSUPP=95`).
- **Zero Physical `Sync Terminal` + `XLR-H1` vs `HVL-LBPC` MI-Shoe Mutual Exclusion + `PMIC 5V <= 900 mA` vs FX6 Zero `GENLOCK`**:
  - Rejects dormant `Sync Terminal` / `Flash Sync Spd. Prty.` (`0` `SYNCHRO_TERMINAL*` hits in `FX3 appFw.so` -> `EOPNOTSUPP=95`).
  - Enforces mechanical shutter MI-Shoe flash sync (`<= 1/250 s` FX3 ceiling; noting `1/160 s FF` / `1/200 s APS-C` EFCS ceilings lie safely within `<= 1/250 s`, `< 250 V`, positive polarity, blocked in Electronic Shutter / Silent Mode).
  - Enforces **`EBUSY=16`** physical/electrical mutual exclusion when `XLR-H1` (passive cold shoes only) occupies the sole FX3 MI-Shoe alongside `HVL-LBPC` (`[Video Light Mode]` 4 modes incl. `Auto`) or `MI_FLASH`, plus **`PMIC 5V <= 900 mA`** overcurrent guard (`384` matrix states).
  - Contrasts FX6 3-mode `Video Light Set` (zero `Auto`), zero Still `[Flash]` UI, switchable `TC IN/OUT` BNC, and **zero physical `GENLOCK`/`REF` BNC** (`107` dormant `GENLOCK` symbols -> `EOPNOTSUPP=95`).

---

## 3. Verification Results (Observed Facts)

| Command / Suite | Scope | Mode | Observed Outcome |
| :--- | :--- | :--- | :--- |
| `test_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_156gate_guard.py` | `104` tests | Normal (`O_RDONLY`) & `FX3_FX6_FORCE_CLEAN_ROOM=1` | PASS (`104/104`, `<0.2s` donor audit) |
| Full `outputs/fx3-safety` unittest discovery | `4,717` tests (`80` files) | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | PASS (`4,717/4,717`, `0` failures) |
| `python3 -B -m fx6_closure verify-milestone-349` | Upstream closure master gate | Normal & `--force-clean-room` | PASS (`gate148=153/156`, `leaked=0`) |
| `python3 -B -m fx6_closure verify-milestone-311 --force-clean-room` | Regression closure milestone | `--force-clean-room` | PASS (`gate134=153/156`, `leaked=0`) |
| `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | Repo hygiene & leak audit | Offline | ALL GREEN (zero `.pyc`, zero untracked) |
