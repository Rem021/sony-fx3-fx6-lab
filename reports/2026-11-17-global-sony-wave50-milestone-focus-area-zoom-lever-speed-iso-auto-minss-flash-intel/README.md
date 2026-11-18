# Global Sony Real-Hardware Intelligence — Wave 50 (`50th` Milestone: `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Complete `[Focus Area]` Hierarchy + `[Focus Area Limit]` / `[Circ. of Focus Point]` / `[AF Area Registration]`, `[Zoom]` Lever & `[Remote Zoom Speed]` `Variable` vs `Fixed` `1..8`, `[ISO Range Limit]` / `[ISO AUTO Min. SS]`, and `[Flash Mode]` Still-Only MI-Shoe vs Movie Lockout)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Focus Area*, *Focus Area Limit*, *Switch V/H AF Area*, *Focus Area Color*, *AF Area Registration*, *Del. Regist. AF Area*, *Circ. of Focus Point*, *Tracking function*, *Touch Tracking*, *Touch Focus*, *Focus Standard*, *Zoom Range*, *Zoom Lever Speed*, *Custom Key Z. Speed*, *Remote Zoom Speed*, *XLR handle unit*, *ISO Range Limit*, *ISO AUTO Min. SS*, *Log shooting*, *Flexible Exp. Mode*, *Flash Mode*, *Flash Comp.*, *Exp.comp.set*, *Wireless Flash*, *Red Eye Reduction*, *FEL lock*, *External Flash Set.*, *Using flash (sold separately)*, *Video Light Mode*, *Silent Mode Settings*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_english.uxc` / `_2.uxc`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Focus Area]` Complete Hierarchy, `[Focus Area Limit]`, `[Switch V/H AF Area]`, `[Focus Area Color]`, `[AF Area Registration]`, & `[Circ. of Focus Point]`

### 1.1 Complete `ILME-FX3 Ver. 7.02` `[Focus Area]` Matrix (Still vs Movie / `S&Q` `Tracking:` Split)

- **Menu Path**: `MENU` -> `(Focus)` -> `[Focus Area]` -> **`[Focus Area]`** (`BKID_APP_setting_autofocus_area_contrast_detect_af`, `_f.uxc` `0x70ac`/`0x6334`, `_g.uxc` `0x61f1`, `.uxc` `0xe0ad`/`0xe1cf`).
- **Factory Default**: **`[Wide]`** (`Can be reset` via `[Camera Settings Reset]`). Locked to `[Wide]` in `[Intelligent Auto]`.

| Focus Area Option (`ilc/2210`) | Still Mode | Movie / `S&Q` Mode | `appFw.so` Internal Enum / `_f.uxc` `resid16` | Behavior & Prerequisites |
| :--- | :---: | :---: | :--- | :--- |
| **`Wide`** (**Default**) | Yes | Yes | `AUTOFOCUS_AREA_CONTRAST_DETECT_AF_WIDE` (`.uxc` `0xe9b5`) | Full-frame automatic subject selection |
| **`Zone`** | Yes | Yes | `AUTOFOCUS_AREA_CONTRAST_DETECT_AF_ZONE` (`.uxc` `0xea3e`) | Selectable zone; camera chooses focus point inside zone |
| **`Center Fix`** | Yes | Yes | `AUTOFOCUS_AREA_CONTRAST_DETECT_AF_CENTER` (`_f.uxc` `0x7824`) | Fixed center-frame AF |
| **`Spot: S`** / **`Spot: M`** / **`Spot: L`** | Yes | Yes | `..._FLEXIBLE_SPOT` + `OPTION_{S,M,L}` (`_f.uxc` `0x65bf..0x65c1`) | Movable precision AF point (`Small` / `Medium` / `Large`) |
| **`Expand Spot`** | Yes | Yes | `..._EXPANDED_FLEXIBLE_SPOT` (`_f.uxc` `0x6785`) | Single spot with surrounding fallback focus points |
| **`Tracking: Wide`** | **Still only (`AF-C`)** | **Locked out** | `..._TRACKING_AF` (`_f.uxc` `0x6701`) | Starts tracking from whole frame on half-shutter |
| **`Tracking: Zone`** | **Still only (`AF-C`)** | **Locked out** | `..._TRACKING_AF` (`_f.uxc` `0x6853`) | Starts tracking within chosen zone on half-shutter |
| **`Tracking: Center Fix`** | **Still only (`AF-C`)** | **Locked out** | `..._TRACKING_AF` (`_f.uxc` `0x602b`) | Starts tracking from center on half-shutter |
| **`Tracking: Spot S / M / L`** | **Still only (`AF-C`)** | **Locked out** | `..._TRACKING_AF` (`_f.uxc` `0x7739..0x7741`) | Starts tracking from selected spot size on half-shutter |
| **`Tracking: Expand Spot`** | **Still only (`AF-C`)** | **Locked out** | `..._TRACKING_AF` (`_f.uxc` `0x6125`) | Starts tracking from Expand Spot on half-shutter |

- **Empirical Still vs Movie `Tracking:` & Legacy-Name Finding (`ilc/2210` + `appFw.so` + `_f.uxc`)**:
  - Official `ilc/2210` (*Focus Area*, *Tracking function*) explicitly prohibits all 7 `[Tracking: ...]` menu focus areas in Movie and S&Q modes: *"When the shooting mode is set to [Movie] or [S&Q Motion] or during movie shooting, [Tracking] cannot be selected for [Focus Area]."* In Movie/S&Q recording, subject tracking is triggered via **`[Touch Tracking]`** (`MENU -> Setup -> Touch Operation -> Touch Func. in Shooting -> Touch Tracking`), which operates across `AF-S`/`AF-A`/`AF-C`/`DMF` (unavailable in `MF` or non-optical zoom).
  - `O_RDONLY` inspection of `FX3 appFw.so` & `_f.uxc` (`ns=227`) confirms the firmware retains legacy Alpha `Flexible Spot` symbol names (`FLEXIBLE_SPOT`, `EXPANDED_FLEXIBLE_SPOT`, `Flexible Spot: S/M/L` `0x6a3c..0x7252`, `Tracking: Flexible Spot S/M/L` `0x65f4..0x65f6`, `Tracking: Expand Flexible Spot` `0x7808`) alongside the active `ILME-FX3` menu labels (`Spot: S/M/L` `0x65bf..0x65c1`, `Expand Spot` `0x6785`, `Tracking: Spot S/M/L` `0x7739..0x7741`, `Tracking: Expand Spot` `0x6125`).

### 1.2 `[Focus Area Limit]`, `[Switch V/H AF Area]`, `[Focus Area Color]`, `[AF Area Registration]`, & `[Circ. of Focus Point]`

| Setting (`MENU -> Focus -> [Focus Area]`) | Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Hardware Constraints |
| :--- | :--- | :---: | :---: | :--- |
| **`[Focus Area Limit]`** | Checkboxes for all `14` focus areas | `—` *(All enabled)* | **Can be reset** | `BKID_APP_focus_area_limit_{wide,zone,center,flexible_spot_{s,m,l},expanded_flexible_spot,tracking_af_*}` (`.uxc` `0x6de2`/`0x6599`/`0x6943`); `.uxc` `0xe227` enforces `>= 2` areas; unchecking an area registered in `[Switch V/H AF Area]` or `[AF Area Registration]` alters those registered states |
| **`[Switch V/H AF Area]`** *(Still only)* | `Off`, `AF Point Only`, `AF Point + AF Area` | **`Off`** | **Can be reset** | `BKID_APP_setting_vertical_horizontal_focus_area_switch` (`0`/`90`/`270` deg tables); inactive in Movie, `iAuto`, Digital Zoom, Self-timer, `Focus Magnifier`, active `AF-C` / burst, or vertical lens pitch |
| **`[Focus Area Color]`** | `White`, `Red` | **`White`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_focus_frame_color` (`_f.uxc` `0x6af1`/`0x74ad`; `WHITE`/`RED`); alters non-tracking AF frame color |
| **`[Circ. of Focus Point]`** | `Does Not Circulate`, `Circulate` | **`Does Not Circulate`** | **Can be reset** | `BKID_APP_setting_circulate_of_focus_point` (`_f.uxc` `0x744d`/`0x74f6`); wraps horizontally/vertically (not diagonally) on `Zone`, `Spot: S/M/L`, `Expand Spot`, and `Tracking: Zone / Spot S/M/L / Expand Spot` |
| **`[AF Area Registration]`** *(Still recall)* | `Off`, `On` | **`Off`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_register_the_af_frame` (`_f.uxc` `0x6b64`/`0x6b65`; note `ilc/2210` uses **`[AF Area Registration]`**, whereas older bodies like ILCE-7RM3/ILCE-9 used `AF Area Regist.`); hold **`Fn`** to store frame; recall via custom key (`[Regist. AF Area hold]`, `[Regist AF Area tggle]`, `[Reg. AF Area+AF On]`; disabled in Movie/`S&Q`/`iAuto`; locks `[Lock Operation Parts]` to `Off`) |
| **`[Del. Regist. AF Area]`** | Action (deletes stored AF area) | `—` | **Not available** | `_f.uxc` `0x608e`/`0x696c` (`Delete the registered focus area?` `0x75c1`) |

- **`ILME-FX6 Ver. 6.01` Cinema Contrast (`5-024-458-18` + `FX6 appFw.so`)**:
  - `FX6` `Shooting > Focus > Focus Area` exposes strictly **`Wide`**, **`Zone`**, and **`Flexible Spot`** (plus `Focus Area (AF-S)` = `Flexible Spot`, `Focus Area (Push AF)` `0x54dc`). It has **zero** `Tracking:` menu focus areas, **zero** `[Focus Area Limit]`, **zero** `[Switch V/H AF Area]` (though `appFw.so` internally inherits `0/90/270` structs), **zero** `[Circ. of Focus Point]`, and **zero** `[AF Area Registration]`.

---

## 2. `[Zoom]` Body Lever, `XLR-H1` Handle Myth-Bust, `[Zoom Lever Speed]`, `[Custom Key Z. Speed]`, & `[Remote Zoom Speed]`

### 2.1 `ILME-FX3` Body Zoom Lever vs `XLR-H1` Handle Unit (`ilc/2210` Hardware Verification)

- **Critical Empirical Finding (`XLR-H1` Has NO Zoom Lever and NO `ZOOM HOLD` Switch)**:
  - On **`ILME-FX3`**, the physical **`W/T` zoom lever** sits on the **camera body** itself (top-front beside the shutter button, `_f.uxc` `0x64c3` *Zoom Lever*).
  - Per official `ilc/2210` (*XLR handle unit*), Sony's **`XLR-H1` XLR handle unit** for `ILME-FX3` / `ILME-FX30` / `ILME-FX2` is strictly an audio-interface handle: its physical switches are exclusively audio/power controls (`INPUT1`/`INPUT2` `LINE/MIC/MIC+48V`, `ATT`, `LOW CUT`, `AUTO/MAN`/`LINK`, `AUDIO LEVEL` dials, `INPUT SELECT` `IN1`/`IN1·IN2`/`IN3`, and **`HANDLE AUDIO` `ON`/`OFF`**). **`XLR-H1` contains NO zoom lever, NO record button, and NO `ZOOM HOLD` switch.** *(By contrast, `ILME-FX6`'s Smart Handle carries a physical **Handle zoom lever** + **Handle `HOLD` switch**; and the unrelated third-party *Zoom H1 XLR* portable audio recorder carries a `POWER/HOLD` switch.)*

### 2.2 Complete `MENU -> Shooting -> [Zoom]` Speed & Range Hierarchy (`ilc/2210` + `appFw.so`)

| Setting (`MENU -> Shooting -> [Zoom]`) | Options / Range | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Behavior |
| :--- | :--- | :---: | :---: | :--- |
| **`[Zoom]`** *(Action)* | Direct focal-length / Clear Image / Digital zoom trigger | `—` | `—` | `_f.uxc` `0x62ef` (`Change zoom mag.`); disabled in `RAW` / `119.88p`/`100p` / high-fps `S&Q` unless power-zoom optical lens attached |
| **`[Zoom Range]`** | `Optical zoom only`, `ClearImage Zoom`, `Digital Zoom` | **`Optical zoom only`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_zoom_setting` (`_f.uxc` `0x774e`/`0x7164`); `ClearImage Zoom` (`0x70e1`) & `Digital Zoom` (`0x796c`) unavailable in `RAW` or `119.88p`/`100p` |
| **`[Zoom Lever Speed]`** *(Body `W/T` lever)* | **`1st Zoom Spd.`** (`1 Slow .. 8 Fast`) & **`2nd Zoom Spd.`** (`1 Slow .. 8 Fast`), split **`STBY`** / **`REC`** | **`1st = 3`**, **`2nd = 8 (Fast)`** | **Can be reset** | `BKID_APP_setting_{1st,2nd}_zoom_spd_{stby,rec}` (`_f.uxc` `0x6079`/`0x6304`, `0x753f`/`0x78f0`); 2-step proportional rocker pressure speeds |
| **`[Custom Key Z. Speed]`** | **`Fixed Speed`** (`1 .. 8`), split **`STBY`** / **`REC`** | **`3`** | **Can be reset** | `BKID_APP_setting_fixed_zoom_speed_{stby,rec}` (`_f.uxc` `0x6ccf`/`0x78e8`); governs `Zoom (Tele)` / `Zoom (Wide)` custom keys |
| **`[Remote Zoom Speed]`** | **`Speed Type`**: `Variable` / `Fixed`; **`Fixed Speed`** (`1 .. 8`), split **`STBY`** / **`REC`** | **`Variable`**, **`Fixed Speed = 3`** | **Can be reset** | `BKID_APP_setting_fixed_zoom_speed_type` (`ZOOM_SPEED_TYPE_{VARIABLE,FIXED}`) + `BKID_APP_setting_remote_fixed_zoom_speed_{stby,rec}` (`_f.uxc` `0x6992`/`0x7128`); governs RMT-P1BT / GP-VPT2BT / Smartphone remote zoom |

### 2.3 `ILME-FX6 Ver. 6.01` Handle Zoom, Grip Remote, `HOLD` Switch, & `0..99` Indicator Contrast

- **`ILME-FX6` Physical Zoom Topology (`5-024-458-18`)**:
  - `FX6` provides **two** hardware zoom rockers: the **Grip Remote Control** zoom lever and the **Smart Handle zoom lever**, plus a physical **Handle `HOLD` switch** and body `HOLD` switch.
  - **`Technical > Handle Zoom`**: `Setting` = **`Off` / `Low` / `High` / `Variable`** (`FX6 string_english_2.uxc` `0x569b..0x56d4`); sub-items **`High`** (`1..8`, default **`8`**, `BKID_APP_SETTING_HANDLE_ZOOM_HIGH`) and **`Low`** (`1..8`, default **`3`**, `BKID_APP_SETTING_HANDLE_ZOOM_LOW`). **`FX6` does NOT use a `Fixed 1..99` zoom speed scale** — **`0` to `99`** on `FX6` is the **`Zoom Position Display`** numeric wide-to-tele focal indicator (`BKID_APP_SETTING_ZOOM_POSITION_DISPLAY`, `string_english.uxc` `0x22ce`).
  - **`Technical > HOLD Switch Setting`**: `with Rec Button` (`On`/`Off`), `with Hand Grip Remote` (`On`/`Off`), and **`Handle HOLD Switch`** (`Normal` vs **`Rec Button Only`**, `BKID_APP_SETTING_HOLD_SWITCH_SETTING_HANDLE_HOLD_SWITCH` — setting `Rec Button Only` locks the handle `REC` button while keeping the **handle zoom lever** active!).
  - **`Technical > Zoom > Zoom Type`**: `Optical Zoom Only` vs `On(Clear Image Zoom)` (up to `1.5x` 4K / `2x` HD even on prime lenses).

---

## 3. `[ISO Range Limit]` & `[ISO AUTO Min. SS]` vs `[Log Shooting]` (`Cine EI` / `Flexible ISO`)

### 3.1 `[ISO Range Limit]` & `[ISO AUTO Min. SS]` Rules (`ilc/2210` + `appFw.so`)

- **Menu Paths**:
  - `MENU` -> `(Exposure/Color)` -> `[Exposure]` -> **`[ISO Range Limit]`** (`BKID_APP_setting_iso_range_limit_{min,max}`, `_still`, `_movie`, `_f.uxc` `0x75a0`/`0x72f8`) -> `[Minimum]` / `[Maximum]`.
  - `MENU` -> `(Exposure/Color)` -> `[Exposure]` -> **`[ISO]`** -> `[ISO AUTO]` -> Right-wheel -> `[ISO AUTO Minimum]` (`.uxc` `0xe88c`) / `[ISO AUTO Maximum]` (`.uxc` `0xe69b`).
  - `MENU` -> `(Exposure/Color)` -> `[Exposure]` -> **`[ISO AUTO Min. SS]`** (`BKID_APP_setting_iso_auto_min_s_s` & `_auto`, `_f.uxc` `0x778b`/`0x6717`).

| Setting | Exposed Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | Coupling & Override Rules |
| :--- | :--- | :---: | :---: | :--- |
| **`[ISO Range Limit]`** *(Still/Movie)* | `Minimum` / `Maximum` across `ISO 50..409600` (`appFw.so` `VAL_HAITA_model_diff_normal_iso_range_*` bounds `80/100..102400` movie, `Cine1` min `64`, `Cine2` min `50`, `HLG Still On` min `100`) | `—` *(Full body range)* | **Not available** *(needs `[Initialize]`)* | Constrains **manual** `[ISO]` only; `[ISO AUTO]` limits are configured separately inside `[ISO] -> [ISO AUTO]` |
| **`[ISO AUTO Min. SS]`** *(Still `P` / `A` only)* | `SLOWER` (`-2 EV`), `SLOW` (`-1 EV`), **`STD` (`Standard`)**, `FAST` (`+1 EV`), `FASTER` (`+2 EV`) — `1 EV` per step relative to lens-focal-length baseline — **or manual threshold `1/8000` .. `30"`** | **`Standard`** | **Can be reset** | Active only with `[ISO AUTO]` in Still **`P`** or **`A`**; if exposure remains insufficient at `[ISO AUTO Maximum]`, camera lowers shutter speed slower than `Min. SS`; overridden by flash (`1/250 s` sync cap / `[Fill-flash]` auto speed) |

### 3.2 Interaction with `[Log Shooting]` (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) & `[Flexible Exp. Mode]`

- **Still-Only Scope of `[ISO AUTO Min. SS]`**: `[ISO AUTO Min. SS]` governs **still `P` / `A`** exposure ramp-up only and does **not** apply in Movie / `S&Q` (`[Auto Slow Shutter]` handles movie low-light shutter slowdown when `[Exposure Ctrl Type]` = `P/A/S/M` or `Flexible Exp. Mode` with `Tv = Auto`).
- **`[Cine EI]` / `[Cine EI Quick]` ISO Lockout**:
  - When `[Log Shooting]` = **`[Cine EI]`** or **`[Cine EI Quick]`**, sensor recording sensitivity is **hard-pinned to Base ISO** (**`ISO 800`** `[L]` or **`ISO 12800`** `[H]`; `[Exposure Index]` only alters monitoring LUT brightness & EI metadata), and **`[Auto Slow Shutter]` is locked out**. Consequently, neither manual `[ISO Range Limit]` nor `[ISO AUTO]` / `[ISO AUTO Min. SS]` controls recording gain in `Cine EI` / `Cine EI Quick`.
  - When `[Log Shooting]` = **`[Flexible ISO]`**, variable/manual ISO (and `[ISO AUTO]` within `S-Log3` floor/ceiling) remains active.
- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` has zero `[ISO AUTO Min. SS]` and uses `AGC` (`Auto Exposure AGC`, `AGC Limit`, `AGC Point`) in `Custom` / `Flexible ISO`, while `Cine EI` / `Cine EI Quick` similarly pins sensor sensitivity to `Base ISO` (`ISO 800` / `ISO 12800`).

---

## 4. `[Flash]` (`[Flash Mode]` / `[Flash Comp.]` / `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`) Still-Only MI-Shoe vs Movie Lockout & `[Video Light Mode]`

### 4.1 Complete `MENU -> Exposure/Color -> [Flash]` Submenu (`ilc/2210` + `appFw.so`)

| Setting (`MENU -> Exposure/Color -> [Flash]`) | Exposed Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key & Notes |
| :--- | :--- | :---: | :---: | :--- |
| **`[Flash Mode]`** *(Still only)* | **`Autoflash`**, **`Fill-flash`**, **`Slow Sync.`**, **`Rear Sync.`**, **`Flash Off`** | **`Autoflash`** *(mode-dependent)* | **Can be reset** | `BKID_APP_setting_flash_mode`; `VAL_HAITA_setting_flash_mode_exposure_mode_*` gates all 5 modes strictly to **`EXPOSURE_MODE_STILL`** (`ADVANCED_FLASH` & `WIRELESS` in `VAL_setting_flash_mode_*` are dormant enum entries) |
| **`[Flash Comp.]`** *(Still only)* | `-3.0 EV` .. `+3.0 EV` (`1/3 EV` steps) | **`±0.0`** | **Can be reset** | `BKID_APP_setting_flash_compensation` (`.uxc` `0xe20b`/`0xe5d3`, `_f.uxc` `0x7200`) |
| **`[Exp.comp.set]`** *(Still only)* | `Ambient&flash`, `Ambient only` | **`Ambient&flash`** | **Not available** | `BKID_APP_setting_exp_comp_set` (`.uxc` `0xe11a..0xe11c`, `_f.uxc` `0x73c2`/`0x6efe`/`0x7617`) |
| **`[Wireless Flash]`** *(Still only)* | `Off`, `On` | **`Off`** | **Can be reset** | `BKID_APP_setting_wireless_flash` (`_f.uxc` `0x605b`/`0x6201`); radio commander mode |
| **`[Red Eye Reduction]`** *(Still only)* | `Off`, `On` | **`Off`** | **Can be reset** | `BKID_APP_setting_red_eye_reduction` (`.uxc` `0xe206`, `_f.uxc` `0x7ac9`) |
| **`[External Flash Set.]`** *(Still only)* | `[Ext. Flash Firing Set.]`, `[Ext. Flash Cust. Set.]` | `—` | **Not available** | `BKID_APP_external_flash_menu_*` (`_f.uxc` `0x6771`) |

*(Note: `[FEL lock]` custom keys — `FEL Lock hold` `0x64a1`, `FEL Lock toggle` `0x6e2f`, `FEL Lock/AEL hold` `0x69bd`, `FEL Lock/AEL tggle.` `0x626d` — appear in the custom-key tables for Still, Movie, and S&Q, but are inoperable without an attached compatible flash and unavailable in `Flash Off` / `Autoflash` / external manual flash.)*

### 4.2 Mechanical-Shutter-Only Restriction, Movie Lockout, MI-Shoe Pin Sharing, & `[Video Light Mode]`

- **Total Flash Lockouts (`ilc/2210` + `VAL_HAITA_*`)**:
  1. **Movie / `S&Q Motion` Mode Lockout**: *"You cannot use the flash when recording movies."* All `[Flash]` menu items apply strictly to still images (`EXPOSURE_MODE_STILL` in `VAL_HAITA_setting_flash_mode_exposure_mode_*`).
  2. **Electronic Shutter / `[Silent Mode] = [On]` Lockout**: Flash shooting is hard-disabled whenever `[Shutter Type] = [Electronic Shutter]` OR `[Silent Mode] = [On]`. Mechanical flash sync ceiling is **`1/250 s`** (at shutter speeds faster than `1/4000 s` with HSS external flash, light/dark banding can occur unless manual flash `>= 1/2` power is used).
- **MI-Shoe Pin Sharing & `[Video Light Mode]` (`MENU -> Setup -> [Setup Option] -> [Video Light Mode]`)**:
  - `ILME-FX3`'s **Multi Interface (MI) Shoe** shares power/digital-serial pins across **still flashes** (`HVL-*`, non-Sony `<250 V` positive-polarity center-pin guard), **`XLR-H1` 4-channel 24-bit digital audio**, and **continuous LED video lights** (`HVL-LBPC`).
  - Unlike Flash, **`[Video Light Mode]`** (`BKID_APP_setting_video_light_set`, `_f.uxc` `0x6211`) is active in **Still, Movie, and `S&Q`** with 4 modes verified in `FX3 appFw.so`: **`Power Link`** (**default**, `VIDEO_LIGHT_SET_POWER_LINK`, `0x7282`), **`REC Link`** (`VIDEO_LIGHT_SET_REC_LINK`, `0x76b8`), **`REC Link&STBY`** (`VIDEO_LIGHT_SET_REC_LINK_W_LIGHT`, `0x719b`), and **`Auto`** (`VIDEO_LIGHT_SET_AUTO_LOW_LIGHT`).
- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` (`mechanical_shutter = False`) has **zero still flash stack** (`Flash Mode`/`Flash Comp.`/`Wireless Flash` absent); its MI-Shoe handles smart handle/audio & video light (`Video Light Set` `0x4289`/`0x4d9c`), while rolling-shutter flash artifacts in video are handled by **`Flash Band Reduce`** (`On`/`Off`, `string_english_2.uxc` `0x4215`/`0x43f0`, `0x5614..0x5615`).

---

## 5. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 5.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 50 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_focus_area_limit_*` (`14` areas), `BKID_APP_setting_vertical_horizontal_focus_area_switch`, `BKID_APP_setting_focus_frame_color` (`WHITE`/`RED`), `BKID_APP_setting_circulate_of_focus_point`, `BKID_APP_setting_register_the_af_frame`, `BKID_APP_setting_zoom_setting`, `BKID_APP_setting_{1st,2nd}_zoom_spd_{stby,rec}` (`1..8`), `BKID_APP_setting_fixed_zoom_speed_{type,stby,rec}`, `BKID_APP_setting_remote_fixed_zoom_speed_{stby,rec}`, `BKID_APP_setting_iso_range_limit_{min,max}`, `BKID_APP_setting_iso_auto_min_s_s{_auto}` (`1_8000..30`, `SLOW_PLUS..FAST_PLUS`), `BKID_APP_setting_flash_mode` (`VAL_HAITA_*_EXPOSURE_MODE_STILL`), `BKID_APP_setting_flash_compensation` (`-3.0..+3.0`), `BKID_APP_setting_exp_comp_set`, `BKID_APP_setting_wireless_flash`, `BKID_APP_setting_red_eye_reduction`, `BKID_APP_setting_video_light_set` (`VIDEO_LIGHT_SET_*`) |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` sequential `0x1e1c` records (`0x6000..0x7d3d`): `Spot: S/M/L`, `Expand Spot`, `Center Fix`, `Tracking: Wide/Zone/Center Fix/Spot S/M/L/Expand Spot`, `Focus Area Limit`, `Switch V/H AF Area`, `Focus Area Color`, `Circ. of Focus Point`, `AF Area Registration`, `Del. Regist. AF Area`, `Zoom Range`, `Zoom Lever Speed`, `Custom Key Z. Speed`, `Remote Zoom Speed`, `ISO Range Limit`, `ISO AUTO Min. SS`, `External Flash Set.`, `Video Light Mode`, `FEL Lock hold/toggle` |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` records: `Focus Area` (`0xe0ad`), `Wide` (`0xe9b5`), `Zone` (`0xea3e`), `ISO AUTO Min/Max` (`0xe88c`/`0xe69b`), `Flash Mode` (`0xe5ce`), `Autoflash` (`0xe6d2`), `Flash Off` (`0xe6d3`), `Slow Sync.` (`0xe6d4`), `Fill-flash` (`0xe6d5`), `Rear Sync.` (`0xe95c`), `Flash Comp.` (`0xe5d3`), `Exp.comp.set` (`0xe11a..0xe11c`), `White`/`Red` (`0xe883`/`0xe8c6`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` records: `Focus Area` (`0x61f1`), `Zoom` (`0x6045`), `Flash` (`0x6355`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records (`819` subsystems, `35,668` / `31,197` properties; checksums `0x018adbdb` & `0x09443bb1` PASS) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_HANDLE_ZOOM` (`_HIGH`/`_LOW`), `BKID_APP_SETTING_HOLD_SWITCH_SETTING_{WITH_REC_BUTTON,WITH_HAND_GRIP_REMOTE,HANDLE_HOLD_SWITCH}`, `BKID_APP_SETTING_ZOOM_POSITION_DISPLAY`, `BKID_APP_SETTING_FOCUS_AREA_AF_S`, `BKID_APP_SETTING_BASE_ISO` / `AGC_LIMIT_*` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Handle Zoom` (`0x3258`), `Handle Zoom High/Low` (`0x2f60`/`0x2f7f`), `Handle HOLD Switch` (`0x2518`), `Rec Button Only` (`0x251c`), `Zoom Position Display` (`0x22ce`), `Focus Area (AF-S)` (`0x222c`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Handle Zoom: Off / Speed Low / Speed High / Speed Variable` (`0x569b..0x56d4`), `HOLD Switch Setting` (`0x42b5`), `Flexible Spot` (`0x54d4`), `Focus Area (Push AF)` (`0x54dc`), `Flash Band Reduce` (`0x4215`/`0x43f0`) |

### 5.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Domain / Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_g` `0x61f1` | `Focus Area` | `对焦区域` | `對焦區域` | `フォーカスエリア` | Focus submenu (`Wide` `.uxc` `0xe9b5`, `Zone` `0xea3e`) |
| `_f` `0x7824` | `Center Fix` | `中间固定` | `中間固定` | `中央固定` | Fixed center AF area |
| `_f` `0x65bf..0x65c1` | `Spot: S` / `Spot: M` / `Spot: L` | `点: S` / `M` / `L` | `點: S` / `M` / `L` | `スポット: S` / `M` / `L` | Spot AF (`Expand Spot` `0x6785`) |
| `_f` `0x6701` | `Tracking: Wide` | `跟踪: 广域` | `追蹤: 寬` | `ﾄﾗｯｷﾝｸﾞ:ﾜｲﾄﾞ` | Still `AF-C` tracking (`Zone` `0x6853`, `Center Fix` `0x602b`) |
| `_f` `0x7739..0x7741` | `Tracking: Spot S/M/L` | `跟踪: 点S/M/L` | `追蹤: 點S/M/L` | `ﾄﾗｯｷﾝｸﾞ:ｽﾎﾟｯﾄ S/M/L` | Still `AF-C` spot tracking (`Tracking: Expand Spot` `0x6125`) |
| `_f` `0x6de2` | `Focus Area Limit` | `对焦区域限制` | `對焦區域限制` | `ﾌｫｰｶｽｴﾘｱ限定` | Checkbox limiter (`>= 2` `.uxc` `0xe227`) |
| `_f` `0x73ae` | `Switch V/H AF Area` | `换垂直和水平AF区` | `換垂直/水平AF區` | `縦横ﾌｫｰｶｽｴﾘｱ切換` | `AF Point Only` (`0x6b5f`) / `AF Point + AF Area` (`0x69e8`) |
| `_f` `0x6af1` | `\ue61eFocus Area Color` | `\ue61e对焦边框颜色` | `\ue61e對焦框色` | `\ue61eﾌｫｰｶｽｴﾘｱ枠色` | `White` (`.uxc` `0xe883`, default) / `Red` (`0xe8c6`) |
| `_f` `0x74f6` | `Circ. of Focus Point` | `对焦点的循环` | `對焦點循環` | `ﾌｫｰｶｽ位置の循環` | `Does Not Circulate` (`0x7968`) / `Circulate` (`0x78e1`) |
| `_f` `0x6b65` | `AF Area Registration` | `AF区域注册功能` | `對焦區域登錄功能` | `ﾌｫｰｶｽｴﾘｱ登録機能` | `Fn` hold save; `Del. Regist. AF Area` (`0x696c`) |
| `_g` `0x6045` | `Zoom` | `变焦` | `變焦` | `ズーム` | Shooting -> Zoom submenu |
| `_f` `0x7164` | `Zoom Range` | `变焦范围` | `變焦範圍` | `ズーム範囲` | `Optical zoom only` (`0x73f2`) / `ClearImage Zoom` (`0x70e1`) / `Digital Zoom` (`0x796c`) |
| `_f` `0x6304` | `Zoom Lever Speed` | `变焦杆速度` | `變焦控制桿速度` | `ｽﾞｰﾑﾚﾊﾞｰｽﾋﾟｰﾄﾞ` | `1st Zoom Spd.` (`0x753f`, `3`) / `2nd Zoom Spd.` (`0x78f0`, `8`) |
| `_f` `0x78e8` | `Custom Key Z. Speed` | `自定义键变焦速度` | `自訂鍵變焦速度` | `ｶｽﾀﾑｷｰｽﾞｰﾑｽﾋﾟｰﾄﾞ` | `Fixed Speed` `1..8` (`STBY`/`REC`, default `3`) |
| `_f` `0x7128` | `Remote Zoom Speed` | `遥控变焦速度` | `遙控變焦速度` | `ﾘﾓｰﾄｽﾞｰﾑｽﾋﾟｰﾄﾞ` | `Speed Type` (`0x6b9e`): `Variable` (`0x728a`) / `Fixed` (`0x69ec`) |
| `_f` `0x72f8` | `ISO Range Limit` | `ISO范围限制` | `ISO範圍限制` | `ISO感度範囲限定` | Manual ISO bounds (not resettable) |
| `_f` `0x778b` | `ISO AUTO Min. SS` | `ISO AUTO最小速度` | `ISO AUTO快門速度` | `ISO AUTO低速限界` | `Slower` (`0x6d2e`) / `Standard` (`.uxc` `0xe651`) / `Faster` (`0x73e6`) / `1/8000..30"` |
| `.uxc` `0xe5ce` | `Flash Mode` | `闪光模式` | `閃光燈模式` | `フラッシュモード` | `Autoflash` (`0xe6d2`), `Flash Off` (`0xe6d3`), `Slow Sync.` (`0xe6d4`), `Fill-flash` (`0xe6d5`), `Rear Sync.` (`0xe95c`) |
| `.uxc` `0xe5d3` | `Flash Comp.` | `闪光补偿` | `閃光補償` | `調光補正` | `-3.0 .. +3.0 EV` (`±0.0` default) |
| `.uxc` `0xe11a` | `Exp.comp.set` | `曝光补偿设置` | `曝光補償設定` | `露出補正の影響` | `Ambient&flash` (`0xe11c`) / `Ambient only` (`0xe11b`) |
| `_f` `0x6201` | `Wireless Flash` | `无线闪光灯` | `無線閃光燈` | `ワイヤレスフラッシュ` | `Off` (default) / `On` |
| `_f` `0x7ac9` | `Red Eye Reduction` | `减轻红眼闪光` | `紅眼減弱` | `赤目軽減発光` | `Off` (default) / `On` |
| `_f` `0x6771` | `External Flash Set.` | `外置闪光灯设置` | `外接閃光燈設定` | `外部フラッシュ設定` | MI-Shoe external flash firing & custom setup |
| `_f` `0x6211` | `Video Light Mode` | `视频灯模式` | `視訊燈模式` | `ビデオライトモード` | `Power Link` (`0x7282`), `REC Link` (`0x76b8`), `REC Link&STBY` (`0x719b`) |
