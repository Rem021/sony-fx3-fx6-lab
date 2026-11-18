# Global Sony Real-Hardware Intelligence — Wave 52 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: `[Sensor Cleaning]` / `[Cleaning Mode]` IBIS Battery Gate vs FX6 e-ND Optical Block, `[Exposure Comp.]` `±5.0 EV` / `±2.0 EV` & `[Reset EV Comp.]` / `[Cine EI]` Lockout, `[Focus Mode]` `AF-S/AF-A/AF-C/DMF/MF` Still vs `AF-C/MF` Movie Split + `[Priority Set in AF-S/AF-C]` / `[AF Illuminator]`, and `[Playback]` `[View Mode]` / `[Image Index]` / `[Display as Group]` / `[Display Rotation]` / `[Rotate]`)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Cleaning the image sensor (Sensor Cleaning)*, *Warning messages*, *Exposure Comp. (still image/movie)*, *Exposure step*, *Exposure Std. Adjust*, *Log shooting / Log Shooting Setting*, *Exposure Index*, *Auto Slow Shutter*, *My Dial Settings*, *Selecting the focus method (Focus Mode)*, *Priority Set in AF-S*, *Priority Set in AF-C*, *AF Illuminator*, *AF Assist*, *Focusing using touch operations (Touch Focus)*, *Switching between still images and movies (View Mode)*, *Playing back images on the image index screen (Image Index)*, *Display as Group*, *Rotating recorded images automatically (Display Rotation)*, *Rotating an image (Rotate)*, *List of default setting values*), `ILME-FX3 Ver. 1` Help Guide (`ilc/2035/v1/en/` — *Dial Ev Comp*), `ILCE-7SM3` Help Guide (*Reset EV Comp.*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_english.uxc` / `_2.uxc`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Sensor Cleaning]` (`[Cleaning Mode]`) IBIS Sensor-Shift Battery Gate vs `ILME-FX6 Ver. 6.01` e-ND Optical Block

### 1.1 Empirical Naming & Battery-Gate Evolution (`Ver. 1.x` `>= 3` Bars vs `Ver. 2.00+` `>= 51%`)

Cross-checking `helpguide.sony.net/ilc/2210/v1/en/` against `FX3 Ver. 7.02 appFw.so` and UXC string packs reveals two critical firmware evolutions:
- **Menu Path & Active Label**: `MENU` -> `(Setup)` -> `[Setup Option]` -> **`[Sensor Cleaning]`** -> `[Enter]` (`_f.uxc` `0x67d6`). Legacy `.uxc` (`0xe7d7` `Cleaning Mode`, `0xe879` *"Starts the cleaning mode to clean the image sensor."*) and `appFw.so` C++ symbols (`FUNC_set_cleaning_mode`, `sequence_set_cleaning_mode`, `sensor_cleaning`, `sensor_cleaning_enable_status`) preserve the earlier Alpha `Cleaning Mode` naming alongside `Sensor Cleaning`.
- **Battery Gate (`NP-FZ100`)**:
  - **Pre-Ver. 2.00 (`ILME-FX3 Ver. 1.x`)**: Sony Help Guide required **`3` or more remaining battery icons (bars)**.
  - **Ver. 2.00+ through `Ver. 7.02` (`ilc/2210/v1/en/`)**: With numeric percentage display enabled, Sony requires **`51% or more`** remaining battery charge.
  - **Firmware Enforcement (`FX3 appFw.so` + `.uxc`)**: `get_battery_status_for_cleaning_mode` (`battery_check_for_cleaning_mode` -> `BATTERY_CHECK_FOR_CLEANING_MODE_{LOWER,UNKNOWN,UPPER}`) gates entry. If below threshold, `INSUFFICIENT_BATTERY_CLEANING_MODE` aborts execution and displays **`Power insufficient.`** (`.uxc` `0xe574` / `0xe7ba`).
- **IBIS Sensor-Shift Mechanics & Mandatory `OFF` Termination**:
  1. Selecting `[Enter]` triggers `sequence_set_cleaning_mode`, briefly vibrating the 5-axis IBIS sensor carriage (`MODEL_CLEANING_MODE_COMP` / `INFRA_NOTIFY_CLEANING_MODE_COMP`) to shake off loose dust and locking/centering the sensor plane for safe access.
  2. Upon completion, the camera displays `_g.uxc` `0x6221` (*"Turn the power off after cleaning the image sensor manually."*), requiring a **mandatory physical power-switch `OFF`** before detaching the lens and using a manual blower (never compressed air) slightly face-downward.

### 1.2 `ILME-FX6 Ver. 6.01` Contrast: Zero IBIS, Front e-ND Optical Assembly, & `APR` vs Drop-Off Cleaning

| Feature / Property | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`) |
| :--- | :--- | :--- |
| **Menu Item & Path** | `(Setup) -> [Setup Option] -> [Sensor Cleaning]` (`_f.uxc` `0x67d6`) | **No ultrasonic IBIS shake in `5-024-458-18`**; exposes **`Technical > APR`** (*Automatic Pixel Restoration*, `MODEL_APR_EXECUTE_COMP`) |
| **IBIS Actuator** | **Yes** (`5-axis` sensor-shift IBIS unit vibrates & parks centered) | **None** (`FX6` relies on lens OSS + gyro RTMD; `BUILT_IN_STEADY_SHOT_ERROR_*` in `FX6 appFw.so` are dormant Alpha symbols) |
| **Front Optical Element** | Exposed sensor cover-glass behind E-mount | **Electronic Variable ND filter assembly** (`1/4..1/128` + `CLEAR`, `PID_SET_VARIABLE_ND_VALUE`, `BKID_APP_VARIABLE_ND_CONT`) sits directly in front of the CMOS sensor |
| **Battery / Remote Gate** | `NP-FZ100` **`>= 51%`** (`>= 3` bars pre-Ver. 2.00); `BATTERY_CHECK_FOR_CLEANING_MODE_*` -> `Power insufficient.` | `CrCommandId_SensorCleaning` (`320`) is marked **unsupported (`-`)** for `ILME-FX6` in Sony Camera Remote SDK; Sony Japan restricts `FX6` cleaning to drop-off service (*全コースお預かり*) despite inherited `SENSOR_CLEANING` / `BATTERY_CHECK_FOR_CLEANING_MODE_*` strings in `FX6 appFw.so` / `string_english.uxc` (`0x2fa3..0x2fb4`, `0x3149`) |

---

## 2. `[Exposure Comp.]` (`±5.0 EV` / `±2.0 EV`), `[Reset EV Comp.]`, `[Dial Ev Comp]`, & `[Cine EI]` Lockout

### 2.1 Range, `[Exposure step]`, & `[Reset EV Comp.]` / `[Dial Ev Comp]` Empirical Audit

| Setting (`MENU -> Exposure/Color -> [Exposure Comp.]`) | Options / Range (`ilc/2210` + `appFw.so`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Empirical Notes |
| :--- | :--- | :---: | :---: | :--- |
| **`[Exposure Comp.]`** | **Still**: **`-5.0 EV` to `+5.0 EV`**; **Movie / `S&Q`**: **`-2.0 EV` to `+2.0 EV`** *(live EV meter scale displays `-3.0 .. +3.0 EV`)* | **`±0.0`** | **Can be reset** | `BKID_APP_setting_exposure_compensation` (`_still`/`_movie`), `BKID_APP_separate_movie_exposure_comp`, `VAL_setting_exposure_compensation_EXPOSURE_COMPENSATION_{MINUS_5_0..PLUS_5_0}` |
| **`[Exposure step]`** | **`0.3EV`**, **`0.5EV`** | **`0.3EV`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_exposure_step` (`_f.uxc` `0x78c4`/`0x77c0`, `.uxc` `0xe348`); does **not** alter `[Shutter Mode] = [Angle]` (`Ver. 6.00+`) |
| **`[Exposure Std. Adjust]`** | `-1 EV` to `+1 EV` (`1/6 EV` steps per `Multi/Center/Spot/Entire Screen Avg.`) | **`±0`** | **Not available** *(needs `[Initialize]`)* | `_f.uxc` `0x6f71` / `0x7578` |
| **`[Reset EV Comp.]`** *(Alpha physical-dial legacy)* | `Maintain` (`_f.uxc` `0x799f`/`0x6dd3`) / `Reset` | **`Reset`** *(on `ILCE-7SM3`)* | **Not available** *(on `ILCE-7SM3`)* | `BKID_APP_setting_exposure_compensation_reset_save` (`EXPOSURE_COMPENSATION_RESET_SAVE_{SAVE,RESET}`); retained in `FX3 appFw.so` & `_f.uxc` (`0x7853`/`0x73cb`, `0x6a33`), **omitted** from `ilc/2210` because `FX3` lacks a physical EV-comp dial |
| **`[Dial Ev Comp]`** *(Ver. 1 `ilc/2035` only)* | `Off` / `Front dial` / `Rear dial` | **`Off`** *(Ver. 1)* | \u2014 | Folded into `(Setup) -> [Dial Customize] -> [Custom Key/Dial Set.]` & `[My Dial Settings]` in `ilc/2210` (`Ver. 2.00+`); legacy `.uxc` `0xe4d9` & `_f.uxc` `0x76d2`/`0x7ae9` strings remain in pack |

### 2.2 Manual `M` + `ISO AUTO` vs Fixed `ISO` & Total `[Cine EI]` / `[Cine EI Quick]` Lockout

- **Intelligent Auto (`iAuto`)**: `[Exposure Comp.]` is disabled (`ilc/2210`).
- **Manual Exposure (`M`) Split**:
  - When `[Exposure Mode]` = `Manual Exposure` and `[ISO]` = **`[ISO AUTO]`**, `[Exposure Comp.]` remains active and biases the auto-ISO target (`-5.0..+5.0 EV` still, `-2.0..+2.0 EV` movie).
  - When `[ISO]` is **fixed** (manual numeric ISO), `[Exposure Comp.]` is unavailable and the metered exposure indicator (`M.M.`) reflects raw scene deviation without shifting exposure parameters.
- **Total Lockout Under `[Log Shooting]` = `[Cine EI]` / `[Cine EI Quick]`**:
  - `FX3 appFw.so` `VAL_HAITA_setting_log_shooting_*` enforces two hard locks whenever `[Log Shooting]` = `Cine EI` or `Cine EI Quick` (`GENERAL_SHOOTING_MODE_MOVIE`):
    1. Exposure mode is hard-locked to **`EXPOSURE_MODE_MOVIE_M`** (and under `Flexible Exp. Mode`, `VAL_HAITA_setting_log_shooting_general_shooting_mode_setting_aperture_a_m_switching_setting_shutter_speed_a_m_switching_exposure_mode_*` forces both Aperture `A/M` and Shutter Speed `A/M` switches to **`MANUAL`**).
    2. Sensor recording gain is hard-pinned to **`Base ISO` (`ISO 800` `[L]` or `ISO 12800` `[H]`)**, disabling `[ISO AUTO]` and `[Auto Slow Shutter]`.
  - With Aperture, Shutter, and Recording ISO all manual/pinned, `[Exposure Comp.]` has zero auto-exposure lever to actuate and is **completely locked out**. Monitoring brightness shifts use **`[Exposure Index]`** (`±2 EV` relative to Base ISO: `200–3200 EI` / `3200–51200 EI`) with `[Display LUT] = [On]`. Under **`[Flexible ISO]`**, variable ISO & `[ISO AUTO]` remain active.
- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` has no `Exposure Comp.` (`±5.0 EV`) menu; exposure trim in `Custom` / `Flexible ISO` uses `Auto Exposure Level`, `Iris`, `e-ND` (`Auto ND`), and `AGC`, while `Cine EI` / `Cine EI Quick` likewise locks gain to `Base ISO 800 / 12800` and shifts monitoring via `Exposure Index`.

---

## 3. `[Focus Mode]` Still (`5` Modes) vs Movie / `S&Q` (`2` Modes) Split + `[Priority Set in AF-S/AF-C]` & `[AF Illuminator]`

### 3.1 Complete Still vs Movie / `S&Q` `[Focus Mode]` & AF Submenu Matrix (`ilc/2210` + `FX3 appFw.so`)

- **Menu Path**: `MENU` -> `(Focus)` -> `[AF/MF]` -> **`[Focus Mode]`** (`BKID_APP_setting_focus_mode_menu_dial`, `BKID_APP_separate_movie_focus_mode`, `_g.uxc` `0x625e` / `0x6412`).
- **Factory Default**: **`Automatic AF`** (`AF-A`) in Still (`Can be reset` via `[Camera Settings Reset]`).

| Focus Mode (`ilc/2210`) | Still Mode | Movie / `S&Q` | `appFw.so` Enum & `VAL_HAITA` Gate | Behavior & Notes |
| :--- | :---: | :---: | :--- | :--- |
| **`Single-shot AF` (`AF-S`)** | Yes | **Locked out** | `FOCUS_MODE_MENU_DIAL_AF_S_EXPOSURE_MODE_STILL` | Locks focus on half-shutter; governed by `[Priority Set in AF-S]` |
| **`Automatic AF` (`AF-A`)** (**Default**) | Yes | **Locked out** | `FOCUS_MODE_MENU_DIAL_AF_A_EXPOSURE_MODE_STILL` | Auto-switches `AF-S` <-> `AF-C` (requires phase-detect AF lens; disables manual fine-tuning `.uxc` `0xe0fa`) |
| **`Continuous AF` (`AF-C`)** | Yes | **Yes** | `..._AF_C_EXPOSURE_MODE_STILL` / **`..._MOVIE_AUTO_EXPOSURE_MODE_MOVIE`** | Continuous AF; note `appFw.so` internally encodes Movie `AF-C` as **`MOVIE_AUTO`** (`0x66ea` / `VAL_HAITA_setting_af_assist_*_MOVIE_AUTO`); no focus beep |
| **`DMF`** | Yes | **Locked out** | `FOCUS_MODE_MENU_DIAL_DMF_EXPOSURE_MODE_STILL` | Auto-focus on half-shutter followed by manual focus ring fine adjustment (`_f.uxc` `0x7810`) |
| **`Manual Focus` (`MF`)** | Yes | **Yes** | `..._MF_EXPOSURE_MODE_STILL` & `..._MF_EXPOSURE_MODE_MOVIE` | Full manual focus; in Movie `MF`, temporary AF available via `[AF On]`, half-shutter, `[Eye AF]`, or `[Touch Focus]` |

*(Note: `FOCUS_MODE_MENU_DIAL_PF` and `SEMI_MANUAL` in `FX3 appFw.so` are dormant Alpha symbols unused on `ILME-FX3`.)*

### 3.2 `[AF Assist]`, `[Priority Set in AF-S]`, `[Priority Set in AF-C]`, & `[AF Illuminator]`

| Setting (`MENU -> Focus -> [AF/MF]`) | Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Hardware Constraints |
| :--- | :--- | :---: | :---: | :--- |
| **`[AF Assist]`** *(Movie `AF-C` ring override)* | `On`, `Off` | **`Off`** *(menu-configurable)* | \u2014 | `BKID_APP_setting_af_assist` (`_f.uxc` `0x64a9`); gated to Movie **`AF-C`** (`MOVIE_AUTO`); turning focus ring overrides AF manually and AF-C re-locks on the new subject once ring stops |
| **`[Priority Set in AF-S]`** *(Still)* | `AF`, `Release`, **`Balanced Emphasis`** | **`Balanced Emphasis`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_af_s_priority_setup` (`_f.uxc` `0x7519`/`0x664d`); applies in `AF-S`, `DMF`, and `AF-A` (still subject) |
| **`[Priority Set in AF-C]`** *(Still)* | `AF`, `Release`, **`Balanced Emphasis`** | **`Balanced Emphasis`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_af_c_priority_setup` (`_f.uxc` `0x681b`/`0x6982`); applies in `AF-C` and `AF-A` (moving subject) |
| **`[AF Illuminator]`** *(Still only)* | **`Auto`**, `Off` | **`Auto`** | **Can be reset** | `BKID_APP_setting_still_image_af_illuminator` (`.uxc` `0xe07f`, `_f.uxc` `0x6e18`); **locked out** in `Movie`, `S&Q Motion`, `AF-C` / moving `AF-A`, `Focus Magnifier`, or Mount Adaptor |

- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` uses physical lens/body **`AF/MF`** selection (`Focus Mode` `string_english_2.uxc` `0x4547`) plus **`Push AF Mode`** (`AF` vs `Single-shot AF(AF-S)`, `string_english.uxc` `0x26b2..0x26b3`), `Push AF/Push MF` (`0x431a`), `Focus Hold` (`0x5436`), and **`AF Assist`** (`0x43e2..0x43e5`). `FX6` has zero `AF-A`, `DMF`, `Priority Set in AF-S/AF-C`, or `AF Illuminator`.

---

## 4. `[Playback]` `[View Mode]`, `[Image Index]`, `[Display as Group]`, `[Display Rotation]`, & `[Rotate]`

### 4.1 Complete `(Playback)` Viewing & Edit Matrix (`ilc/2210` + `FX3 appFw.so`)

| Setting & Menu Path (`ilc/2210`) | Active `ILME-FX3` Options *(vs Dormant `appFw.so`)* | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Hardware / Slot Behavior |
| :--- | :--- | :---: | :---: | :--- |
| **`[View Mode]`** (`Playback -> [Playback Target] -> [View Mode]`) | **`Date View`** (`.uxc` `0xe3b8`), **`Folder View(Still)`** (`.uxc` `0xe3b9`), **`Movie View`** (`_f.uxc` `0x7468`) *(dormant UXC/ELF strings: `Folder View(MP4)` `.uxc` `0xe3ba`, `AVCHD View` `0xe3bb`, `Mov. View by File Format` `_f` `0x6e4b`)* | **`Date View`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_menu_view_mode`; in `Date View`, plays back strictly from the card selected in `[Select Playback Media]` (`Slot 1` default); `[Slide Show]` requires `Date View` or `Folder View(Still)` |
| **`[Image Index]`** (`Playback -> [Playback Option] -> [Image Index]`) | **`9 Images`** (`.uxc` `0xe4a3`), **`25 Images`** (`_f.uxc` `0x7302` / `0x6db8`) *(dormant `appFw.so` / `_f.uxc` `0x6e7a`: `12_IMAGES` & `30 Images` NOT exposed on `ILME-FX3`)* | **`9 Images`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_menu_image_index`; left-hand bar jumps dates/folders or switches `View Mode` |
| **`[Display as Group]`** (`Playback -> [Playback Option] -> [Display as Group]`) | **`Off`**, **`On`** | **`Off`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_display_group` (`_f.uxc` `0x6f26`); groups continuous-shooting bursts & `[Interval Shoot Func.]` sessions (`CONTENT_GROUPING_TYPE_CONTINUATION`); deleting a group deletes all frames in the group |
| **`[Display Rotation]`** (`Playback -> [Playback Option] -> [Display Rotation]`) | **`Auto`**, **`Manual`**, **`Off`** | **`Auto`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_display_rotatiton` *(Sony `rotatiton` spelling in `appFw.so`)*, `_f.uxc` `0x6aa4`; movies always play back horizontally |
| **`[Rotate]`** (`Playback -> [Edit] -> [Rotate]`) | Interactive counter-clockwise `90°` step per center-wheel press | \u2014 | \u2014 | `FUNC_rotate_content`, `VAL_is_edit_rotate_*` (`_f.uxc` `0x795a`, `.uxc` `0xe5ae`); persists orientation into recorded file metadata on card; blocked during background transfer (`FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE`) or non-rotatable clips (`.uxc` `0xe922`) |

### 4.2 `Slot 1` Write Hazard of `[Rotate]` & `ILME-FX6` Contrast

- **Mandatory `Slot 1` Write Guard on `[Rotate]`**: Because `[Select Playback Media]` defaults to **`Slot 1`** and `[Rotate]` (`FUNC_rotate_content`) mutates file EXIF orientation metadata on the memory card, any write-protected / read-only `Slot 1` cinema volume (`VAL_status_of_media_slot1_STATUS_OF_MEDIA_SLOT1_READ_ONLY`, `VAL_media_movie_write_protect_state_slot1_MEDIA_MOVIE_WRITE_PROTECT_STATE_SLOT1_PROTECT`) **must block `[Rotate]` execution**.
- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` has zero still `Image Index` (`9/25`), zero burst `Display as Group`, zero `Display Rotation`, and zero EXIF `Rotate` (`Clip Thumbnail View Mode` `string_english_2.uxc` `0x4fd1` and `Material Group` `0x5010` apply exclusively to cinema MXF clip thumbnail lists).

---

## 5. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 5.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 52 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `FUNC_set_cleaning_mode`, `BATTERY_CHECK_FOR_CLEANING_MODE_{LOWER,UNKNOWN,UPPER}`, `INSUFFICIENT_BATTERY_CLEANING_MODE`, `BKID_APP_setting_exposure_compensation` (`MINUS_5_0..PLUS_5_0`), `BKID_APP_setting_exposure_compensation_reset_save` (`SAVE`/`RESET`), `BKID_APP_setting_exposure_step`, `VAL_HAITA_setting_log_shooting_*_EXPOSURE_MODE_MOVIE_M`, `BKID_APP_setting_focus_mode_menu_dial` (`STILL` 5 modes vs `MOVIE_AUTO`/`MF`), `BKID_APP_setting_af_{s,c}_priority_setup`, `BKID_APP_setting_still_image_af_illuminator`, `BKID_APP_setting_af_assist`, `BKID_APP_setting_menu_view_mode`, `BKID_APP_setting_menu_image_index`, `BKID_APP_setting_display_group`, `BKID_APP_setting_display_rotatiton`, `FUNC_rotate_content`, `FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE` |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` sequential `0x1e1c` records (`0x6000..0x7d3d`): `Sensor Cleaning` (`0x67d6`), `Exposure Comp.` (`0x76de`), `Reset EV Comp.` (`0x7853`/`0x73cb`), `Maintain` (`0x799f`/`0x6dd3`), `Exposure step` (`0x78c4`), `AF Assist` (`0x64a9`), `Priority Set in AF-S` (`0x7519`), `Priority Set in AF-C` (`0x681b`), `Balanced Emphasis` (`0x6a60`), `Movie View` (`0x7468`), `25 Images` (`0x7302`), `30 Images` (`0x6e7a` dormant), `Display as Group` (`0x6f26`), `Display Rotation` (`0x6aa4`), `Rotate` (`0x795a`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` records: `Cleaning Mode` (`0xe7d7`), `Power insufficient.` (`0xe574`/`0xe7ba`), `Exposure Comp.` (`0xe956`), `Dial Ev Comp` (`0xe4d9`), `Exposure step` (`0xe348`), `Single-shot AF` (`0xe56d`), `Automatic AF` (`0xe56c`), `Continuous AF` (`0xe56e`), `DMF` (`0xe4ac`), `Manual Focus` (`0xe9e4`), `AF Illuminator` (`0xe07f`), `View Mode` (`0xe3b7`), `Date View` (`0xe3b8`), `Folder View(Still)` (`0xe3b9`), `Image Index` (`0xe20a`), `9 Images` (`0xe4a3`), `Rotate` (`0xe5ae`), `Unable to rotate image.` (`0xe922`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` records: `Turn the power off after cleaning the image sensor manually.` (`0x6221`), `Exposure Comp.` (`0x63c5`), `Focus Mode` (`0x625e`, `0x6412`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records (`819` subsystems, numeric BKID store) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `PID_SET_VARIABLE_ND_VALUE`, `BKID_APP_VARIABLE_ND_CONT`, `MODEL_APR_EXECUTE_COMP`, `BKID_APP_USER_MENU_SENSOR_CLEANING` (inherited/SDK-disabled), zero FX3 `Exposure Comp.` / `Display as Group` / `Image Index` / `Rotate` stack |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Push AF Mode : AF / Single-shot AF(AF-S)` (`0x26b2..0x26b3`), `ND Filter Preset1..3`, `Auto ND Filter`, `Sensor Cleaning` (`0x2fa3..0x2fb4`, `0x3149`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Push AF/Push MF` (`0x431a`), `AF Assist` (`0x43e2..0x43e5`), `Focus Mode` (`0x4547`), `Clip Thumbnail View Mode` (`0x4fd1`), `Material Group` (`0x5010`) |

### 5.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Domain / Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x67d6` | `Sensor Cleaning` | `传感器清洁` | `感應器清潔` | `ｾﾝｻｰｸﾘｰﾆﾝｸﾞ` | Active FX3 Ver. 2+ menu label (`Setup Option`) |
| `.uxc` `0xe7d7` | `Cleaning Mode` | `清洁模式` | `清潔模式` | `クリーニングモード` | Legacy Alpha cleaning mode label (`0xe879`) |
| `.uxc` `0xe574` | `Power insufficient.` | `电量不足。` | `電量不足。` | `電池が少ないので実行できません` | Low-battery abort (`< 51%` / `< 3` bars; `0xe7ba`) |
| `_g` `0x6221` | `Turn the power off after cleaning\nthe image sensor manually.` | `手动清洁影像传感器后关机。` | `關閉電源前，\n請先手動清潔影像感應器。` | `イメージセンサーを手動清掃した後\n電源をOFFしてください` | Mandatory power-`OFF` termination prompt |
| `_f` `0x76de` | `\ue61eExposure Comp.` | `\ue61e曝光补偿` | `\ue61e曝光補償` | `\ue61e露出補正` | `±5.0 EV` still / `±2.0 EV` movie (`.uxc` `0xe956`) |
| `_f` `0x7853` | `\ue61eReset EV Comp.` | `\ue61e重置EV补偿` | `\ue61e重設EV補償` | `\ue61e露出補正値のﾘｾｯﾄ` | Alpha dial EV reset (`Maintain` `0x799f` / `Reset` `0x687b`) |
| `_f` `0x78c4` | `\ue61eExposure step` | `\ue61e曝光步级` | `\ue61e曝光級數` | `\ue61e露出値ステップ幅` | `0.3EV` (`0x787a`, default) / `0.5EV` (`0x64f2`) |
| `.uxc` `0xe4d9` | `Dial Ev Comp` | `转盘Ev补偿` | `轉盤Ev補償` | `ダイヤル露出補正` | Ver. 1 (`ilc/2035`) dial EV menu label |
| `_g` `0x625e` | `Focus Mode` | `对焦模式` | `對焦模式` | `フォーカスモード` | Still 5 modes vs Movie/`S&Q` 2 modes (`0x6412`) |
| `.uxc` `0xe56d` | `Single-shot AF` | `单次AF` | `單次對焦` | `シングルAF` | Still-only (`AF-S`) |
| `.uxc` `0xe56c` | `Automatic AF` | `自动AF` | `自動對焦` | `AF制御自動切り換え` | Default Still mode (`AF-A`, `0xe4ab`) |
| `.uxc` `0xe56e` | `Continuous AF` | `连续AF` | `連續對焦` | `コンティニュアスAF` | Active in Still, Movie, & `S&Q` (`AF-C`) |
| `.uxc` `0xe4ac` | `DMF` | `DMF` | `DMF` | `DMF` | Still-only Direct Manual Focus (`0xe67c`) |
| `.uxc` `0xe9e4` | `Manual Focus` | `手动对焦` | `手動對焦` | `ﾏﾆｭｱﾙﾌｫｰｶｽ` | Active in Still, Movie, & `S&Q` (`_f` `0x6df4`) |
| `_f` `0x64a9` | `AF Assist` | `AF帮助` | `AF幫助` | `AFアシスト` | Movie `AF-C` manual ring override |
| `_f` `0x7519` | `Priority Set in AF-S` | `AF-S优先级设置` | `單次對焦優先設定` | `AF-S時の優先設定` | `Balanced Emphasis` (`0x6a60`) / `AF` (`.uxc` `0xe404`) / `Release` (`0x7358`) |
| `_f` `0x681b` | `Priority Set in AF-C` | `AF-C优先级设置` | `連續對焦優先設定` | `AF-C時の優先設定` | `Balanced Emphasis` (`0x6f43`) / `AF` / `Release` |
| `.uxc` `0xe07f` | `AF Illuminator` | `AF辅助照明` | `對焦輔助照明` | `AF補助光` | `Auto` (`0xe6da`, default) / `Off` (`0xe898`); Still only |
| `.uxc` `0xe3b7` | `View Mode` | `观看模式` | `觀看模式` | `ビューモード` | `Date View` (`0xe3b8`) / `Folder View(Still)` (`0xe3b9`) / `Movie View` (`_f` `0x7468`) |
| `.uxc` `0xe20a` | `Image Index` | `影像索引` | `影像索引` | `一覧表示` | `9 Images` (`.uxc` `0xe4a3`, default) / `25 Images` (`_f` `0x7302`) |
| `_f` `0x6f26` | `Display as Group` | `以组显示` | `以群組形式顯示` | `グループ表示` | `Off` (`0x63aa`, default) / `On` (`0x7963`) |
| `_f` `0x6aa4` | `Display Rotation` | `显示旋转` | `顯示旋轉` | `記録画像の回転表示` | `Auto` (`.uxc` `0xe6da`, default) / `Manual` (`0x6a71`) / `Off` |
| `.uxc` `0xe5ae` | `Rotate` | `旋转` | `轉動` | `回転` | Still EXIF rotation (`_f` `0x795a`; blocked `.uxc` `0xe922` / read-only `Slot 1`) |
