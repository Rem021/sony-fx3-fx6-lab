# Global Sony Real-Hardware Intelligence — Wave 48 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: `[Picture Profile]` `PP1..PP11` `S-Cinetone` vs `[Creative Look]` & `[D-Range Optimizer]` Lockouts under `[Log Shooting]`, `[White Balance]` `Custom 1..3` / `Priority Set in AWB` / `Cine EI` Restrictions, and `[Metering Mode]` + `[Spot Metering Point]`)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Picture Profile (still image/movie)*, *Different Set for Still/Mv*, *Creative Look (still image/movie)*, *D-Range Optimizer (still image/movie)*, *Log Shooting Setting*, *Log shooting*, *Base ISO*, *Exposure Index*, *White Balance (still image/movie)*, *Priority Set in AWB*, *Shutter AWB Lock*, *Shockless WB*, *Capturing a standard white color to set the white balance*, *Metering Mode (still image/movie)*, *Face Priority in Multi Metering*, *Spot Metering Point*, *AEL w/ Shutter*, *Manual Exposure*, *Exposure Std. Adjust*, *Save/Load Settings*, *Setting Reset*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_english.uxc` / `_2.uxc`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Picture Profile]` (`PP1..PP11`, `S-Cinetone`), `[Creative Look]`, & `[D-Range Optimizer]` Mutual-Exclusivity & `[Log Shooting]` Lockout (`Ver. 2.00+` / `Ver. 7.02`)

### 1.1 Out-of-Box Cinema Posture (`PP11` Default for Both Movie & Still) & `PP1..PP11` / `PPLUT1..4` Matrix

- **Verified Factory Default (`PP11` — NOT `Off`)**: Unlike consumer Sony Alpha bodies (`ILCE-7M4`, `ILCE-6700`, etc.) that default `[Picture Profile]` to `Off`, official `ilc/2210` *List of default setting values* pins **`[Picture Profile]` = `[PP11]` (`S-Cinetone`)** as the out-of-box factory default on `ILME-FX3` (matching Cinema Line siblings `ILME-FX30` and `ILME-FX2`).
- **Still vs Movie Split (`Different Set for Still/Mv`)**: `O_RDONLY` inspection of `FX3 appFw.so` confirms three linked keys — `BKID_APP_setting_picture_profile`, `BKID_APP_setting_picture_profile_movie`, and `BKID_APP_setting_picture_profile_still` — gated by `[Different Set for Still/Mv]` (`_f.uxc` `0x62ee`, `BKID_APP_setting_different_set`). Out of the box, `[Picture Profile]` is **not** checked inside `[Different Set for Still/Mv]`, so **`PP11` (`S-Cinetone`) is active for BOTH Movie and Still** by default. Checking `[Picture Profile]` under `[Different Set for Still/Mv]` decouples still vs movie selections, and **neither `[Camera Settings Reset]` nor `[Initialize]` clears that check mark**.
- **Reset Trap (`[Camera Settings Reset]` vs `[Initialize]` vs `[Picture Profile] -> [Reset]`)**: `[Camera Settings Reset]` restores the active profile selector to `PP11`, **but customized internal parameters inside `PP1..PP11` are NOT reset by `[Camera Settings Reset]` or `[Initialize]`** (only `PPLUT1..PPLUT4` reset). Individual profiles must be reset one at a time via `MENU -> (Exposure/Color) -> [Color/Tone] -> [Picture Profile] -> [PPx] -> [Reset]`.

| `appFw.so` Enum (`VAL_setting_picture_profile_*`) | Menu Option | Default Gamma | Default Color Mode | Scope / Notes (`ilc/2210` + `appFw.so`) |
| :--- | :--- | :--- | :--- | :--- |
| `PICTURE_PROFILE_OFF` | `Off` | — | — | Required to unlock `[Creative Look]` & `[D-Range Optimizer]` |
| `PICTURE_PROFILE_PP1` | `PP1` | `Movie` | `Movie` | Standard video gamma example |
| `PICTURE_PROFILE_PP2` | `PP2` | `Still` | `Still` | Standard still-like gamma example |
| `PICTURE_PROFILE_PP3` | `PP3` | `ITU709` | `ITU709` | Natural ITU709 tone |
| `PICTURE_PROFILE_PP4` | `PP4` | `ITU709` | `ITU709` | Faithful ITU709 standard tone |
| `PICTURE_PROFILE_PP5` | `PP5` | `Cine1` | `Cinema` | Soft highlight roll-off (`Cine1`) |
| `PICTURE_PROFILE_PP6` | `PP6` | `Cine2` | `Cinema` | Broadcast-legal `Cine2` (`100%` clip) |
| `PICTURE_PROFILE_PP7` | `PP7` | `S-Log2` | `S-Gamut` | Legacy `S-Log2` (8-bit/compat) |
| `PICTURE_PROFILE_PP8` | `PP8` | `S-Log3` | `S-Gamut3.Cine` | Cinema `S-Log3 / S-Gamut3.Cine` |
| `PICTURE_PROFILE_PP9` | `PP9` | `S-Log3` | `S-Gamut3` | Wide-gamut `S-Log3 / S-Gamut3` |
| `PICTURE_PROFILE_PP10` | `PP10` | `HLG2` | `BT.2020` | HDR HLG movie preset |
| `PICTURE_PROFILE_PP11` | **`PP11` (Default)** | **`S-Cinetone`** | **`S-Cinetone`** | Cinema Line skin-tone/roll-off default (`CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG`) |
| `PICTURE_PROFILE_PPLUT1..4` | `PPLUT1..PPLUT4` | User `.cube` LUT | User `.cube` LUT | **Movie only** (`BKID_APP_setting_pplut1..4_link_uset_lut`); `1080p` HDMI clamp when rec internally |

### 1.2 `[Creative Look]` (10 Presets) & `[D-Range Optimizer]` (`Off` / `Auto` / `Lv1..Lv5`)

- **`[Creative Look]` (`MENU -> Exposure/Color -> [Color/Tone] -> [Creative Look]`)**:
  - `ilc/2210` sets **`[ST]`** as factory default (`Can be reset`).
  - `O_RDONLY` inspection of `FX3 appFw.so` reveals Sony's internal `BKID_APP_setting_creative_style_plus` enum (`VAL_setting_creative_style_plus_CREATIVE_STYLE_PLUS_*`) mapping all **10** presets + **6** custom slots (`CREATIVE_BOX_1..6`):
    - **`ST`** (`STANDARD`), **`PT`** (`PORTRAIT`), **`NT`** (`NEUTRAL`), **`VV`** (`VIVID`), **`VV2`** (`BRILLIANT`), **`FL`** (`FILM`), **`IN`** (`RETRO`), **`SH`** (`AIRY`), **`BW`** (`BLACK_WHITE`), **`SE`** (`SEPIA`).
  - Exposes 8 fine-tuning parameters (`Contrast`, `Highlights`, `Shadows`, `Fade`, `Saturation` [locked in `BW`/`SE`], `Sharpness`, `Sharpness Range` [locked in movie], `Clarity`).
- **`[D-Range Optimizer]` (`MENU -> Exposure/Color -> [Exposure Comp.] -> [D-Range Optimizer]`)**:
  - `BKID_APP_setting_dro` (`DRO_OFF` / `DRO_D_RANGEOPTIMIZER`) + `BKID_APP_setting_dro_d_range_optimizer` (`AUTO`, `LV1..LV5`).
  - Factory default is **`D-Range Optimizer: Auto`** (`Can be reset` via `[Camera Settings Reset]`).

### 1.3 Mutual-Exclusivity & `[Log Shooting]` Lockout Matrix vs `ILME-FX6 Ver. 6.01`

| Active Pipeline State (`ILME-FX3 Ver. 7.02`) | `[Picture Profile]` | `[Creative Look]` | `[D-Range Optimizer]` | `[Gamma Display Assist]` / LUT Path |
| :--- | :--- | :--- | :--- | :--- |
| **`[Log Shooting]` = `Flexible ISO` / `Cine EI Quick` / `Cine EI`** | **Locked to `Off`** | **Locked to `-`** | **Locked to `Off`** | `Display LUT` + `Select LUT` (`s709` default / `R709` / `S-Log3` / `User1..16`); movie `Gamma Display Assist` locked `Off` |
| **`[Log Shooting]` = `Off` & `[Picture Profile]` = `PP1..PP11` / `PPLUT1..4`** *(incl. factory default `PP11`!)* | Active (`PP1..11` / `PPLUT1..4`) | **Locked to `-`** | **Locked to `Off`** | `Gamma Display Assist` active for `S-Log2`/`S-Log3`/`HLG` |
| **`[Log Shooting]` = `Off` & `[Picture Profile]` = `Off`** | `Off` | **Active** (`ST` default) | **Active** (`Auto` default; disabled if `[HLG Still Image] = On`) | Standard SDR tone curve |
| **`[Intelligent Auto]` Shoot Mode** | `Off` | **Locked to `-`** | Auto-managed | Locked `Auto` scene color |

- **Critical Real-Hardware Gotcha**: Because `ILME-FX3` ships out of the box with `[Picture Profile] = PP11`, both **`[Creative Look]` and `[D-Range Optimizer]` are disabled by default** until the operator explicitly sets `[Picture Profile] = [Off]`.
- **Why `[Log Shooting]` Locks Out `[Picture Profile]`**: `Log Shooting` (`BKID_APP_setting_log_shooting`: `LOG_SHOOTING_{OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI}`) switches the `BIONZ XR` ISP into a dedicated `S-Log3` recording + non-destructive monitoring LUT pipeline (`BKID_APP_setting_select_lut`, `BKID_APP_setting_apply_lut`, `BKID_APP_setting_embed_lut_file`), making `PP1..PP11` / `PPLUT1..4` gamma/matrix stages and `Creative Look` / `DRO` tone-mapping mutually exclusive to prevent double-log or baked-look corruption.
- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` does not use `Picture Profile`, `Creative Look`, or `D-Range Optimizer`. Instead, `Project > Base Setting > Shooting Mode` (`Custom` vs `Cine EI` / `Cine EI Quick`) + `Paint/Look > Base Look > Select` (`BKID_APP_USER_MENU_BASE_LOOK0..8`) selects the pipeline: **`Custom` (`SDR(BT.709)`) defaults to `S-Cinetone`** (Scene File 1; alongside `Standard`, `Still`, `ITU709`, `709tone`, `User1..16`; or `HLG Live`/`HLG Natural`/`HLG Mild` under `HDR(HLG)`), while **`Cine EI` locks recording to `S-Log3` (`S-Gamut3.Cine` / `S-Gamut3`)** with monitoring LUTs (`s709`, `709(800)`, `S-Log3`, `User1..16`).

---

## 2. `[White Balance]`, `[Priority Set in AWB]`, & `[Shutter AWB Lock]` vs `Cine EI` Color Pipeline Rules

### 2.1 Complete `ILME-FX3 Ver. 7.02` White Balance & AWB Subsystem

- **Menu Path**: `MENU` -> `(Exposure/Color)` -> `[White Balance]` (`BKID_APP_setting_white_balance`, `_still`, `_movie`; assigned to `Custom Button 2` by default).
- **Verified Modes (`ilc/2210` + `FX3 appFw.so` `VAL_setting_white_balance_*`)**:
  1. **`Auto`** (**factory default**, `WHITE_BALANCE_AUTO_WB`): Sub-displays `(Auto: Ambience)` or `(Auto: White)` when `[Priority Set in AWB]` != `Standard`.
  2. **Fixed Presets**: `Daylight`, `Shade`, `Cloudy`, `Incandescent`, **`Fluor.: Warm White`** (`-1`), **`Fluor.: Cool White`** (`0`), **`Fluor.: Day White`** (`+1`), **`Fluor.: Daylight`** (`+2`), **`Flash`** (still images only), **`Underwater Auto`**.
  3. **`C.Temp./Filter`**: Color temperature verified in `FX3 appFw.so` across **`2500K .. 9900K`** (`75` steps in `100 K` increments: `WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_2500K..9900K`, `_f.uxc` `0x6741 <2500K` / `0x751f >9900K`), plus 2-axis fine-tuning **`A7..B7`** and **`G7..M7`** (`.uxc` `0xe992`, `appFw.so` `A7`/`B7`/`G7`/`M7`). Turning the rear dial adjusts Kelvin directly.
  4. **`Custom 1` / `Custom 2` / `Custom 3`**: Three independent custom WB memory slots captured via `[Custom Setup]` (`WHITE_BALANCE_CUSTOM_WHITE_BALANCE_SET`).
- **`[Priority Set in AWB]`**: `BKID_APP_setting_priority_set_in_awb` -> **`Standard`** (**factory default**), `Ambience`, `White`. Resettable via `[Camera Settings Reset]`.
- **`[Shutter AWB Lock]`** (Still): `BKID_APP_setting_stl_awb_lock_with_shutter` -> `Shutter Half Press` (`Shut. Halfway Down` `_f.uxc` `0x6ccc`), `Cont. Shooting`, **`Off`** (**factory default**). **NOT resettable via `[Camera Settings Reset]`** (only `[Initialize]`). For movie/live work, custom keys expose **`[AWB Lock Hold]`** and **`[AWB Lock Toggle]`** (`EVENT_FUNC_CUSTOM_AWB_LOCK_{HOLD,TOGGLE}_{ON,OFF}`).
- **`[Shockless WB]`** (Movie): `BKID_APP_setting_movie_shockless_wb` -> `Off`, **`1 (Fast)`** (**factory default**), `2`, `3 (Slow)`. Resettable via `[Camera Settings Reset]`. Smooths preset/custom WB switching during recording, but **does not** smooth `[Auto]`/`[Underwater Auto]` or live `[C.Temp./Filter]` / fine-tune adjustments (which apply immediately).

### 2.2 `Cine EI` Restrictions, Custom Setup Error Workaround, Reset Boundary & `ILME-FX6` Contrast

- **`Cine EI` / `Cine EI Quick` Lockout**: When `[Log Shooting]` = `[Cine EI]` or `[Cine EI Quick]`, **`[Auto]` and `[Underwater Auto]` cannot be selected** (`ilc/2210` prevents uncontrolled AWB shifts across cinema Log shots). Fixed presets, `C.Temp./Filter` (`2500K..9900K`), and `Custom 1..3` remain available.
- **Custom WB Capture Error Trap (`Display LUT` / `Log Shooting` / `S-Log3`)**: Regardless of `[Display LUT]` (`On` / `Off`), Sony explicitly warns in `ilc/2210` that running `[Custom Setup]` while **`[Log Shooting] != [Off]`** or **`[Picture Profile]` uses `[S-Log3]` or `[PPLUT1..4]`** may trigger a custom WB setup error. **Mandated procedure**: temporarily set `[Log Shooting] = [Off]` (or switch off `S-Log3`/`PPLUT`), capture `Custom 1..3`, then restore `[Log Shooting]`.
- **`[Camera Settings Reset]` vs `Custom 1..3` Persistence & `Save/Load Settings` Exclusion**:
  - `[Camera Settings Reset]` resets the **active `[White Balance]` selection** to `Auto` (and `Priority Set in AWB` -> `Standard`, `Shockless WB` -> `1 (Fast)`), **while registered `Custom 1..3` memorized white data remains stored until overwritten** (*"will remain memorized until overwritten by the another setting"*).
  - Under `[Save/Load Settings]` (`CAMSET`), Sony explicitly lists **`White Balance: Custom 1/Custom 2/Custom 3` as settings that CANNOT be saved** to memory card or `C3 Portal`.
- **`ILME-FX6 Ver. 6.01` Contrast**: Replaces FX3's `Auto` / `C.Temp./Filter` / `Custom 1..3` model with broadcast **`Memory A`**, **`Memory B`** (`BKID_APP_EXTERN_WHITEMEMORY{A,B}_ND{1..4,V,OFF}_*`, stored per ND filter state with `20K`/mired fine trim `2000K..15000K`), **`Preset`** (**`3200K` / `4300K` / `5600K` / `6300K`** in `Custom` mode vs **`3200K` / `4300K` / `5500K`** in `Log` / `Cine EI` mode, with `100K` dial trim), and **`ATW`** (`ATW Speed`, `ATW Hold`, `BKID_APP_SETTING_ATW_MODE`). Just like FX3's AWB lockout, **`ATW` cannot be used in `Cine EI` or `Cine EI Quick`**.

---

## 3. `[Metering Mode]`, `[Face Priority in Multi Metering]`, `[Spot Metering Point]`, & `[AEL w/ Shutter]`

### 3.1 Exact 6 `[Metering Mode]` Options & Linked Sub-Settings (`ilc/2210` + `appFw.so`)

- **Menu Path**: `MENU` -> `(Exposure/Color)` -> `[Metering]` -> `[Metering Mode]` (`BKID_APP_setting_metering_mode`, `_still`, `_movie`; `[Spot]` size split in `BKID_APP_setting_metering_mode_spot`).
- **All 6 Modes (`ilc/2210` + `VAL_setting_metering_mode_*`)**:
  1. **`Multi`** (**factory default**, `METERING_MODE_MULTI`): Evaluative multi-zone metering (`Can be reset`).
  2. **`Center`** (`METERING_MODE_CENTER`): Center-weighted average (`Can be reset`).
  3. **`Spot: Standard`** (`METERING_MODE_SPOT` + `SPOT_OPTION_STANDARD`): Small spot metering circle.
  4. **`Spot: Large`** (`METERING_MODE_SPOT` + `SPOT_OPTION_LARGE`): Large spot metering circle.
  5. **`Entire Screen Avg.`** (`METERING_MODE_AVERAGE`): Unweighted full-frame average (`Can be reset`).
  6. **`Highlight`** (`METERING_MODE_HIGHLIGHT`): Highlight-weighted metering to protect bright highlights (`Can be reset`).
- **Companion Sub-Settings**:
  - **`[Face Priority in Multi Metering]`** (`BKID_APP_setting_face_detection_in_multi`): **`On`** (**factory default**, `Can be reset`) vs `Off`. Biases `[Multi]` metering toward detected faces; **hard-locked to `Off`** whenever `[De-Squeeze Display]` != `Off`.
  - **`[Spot Metering Point]`** (`BKID_APP_setting_spot_metering_link_to_focus_point`): **`Center`** (**factory default**, `CENTRAL_FIXED`, `Can be reset`) vs **`Focus Point Link`** (`LINK_TO_FOCUS_POINT`). Coordinates the spot circle with `[Spot: S/M/L]`, `[Expand Spot]`, or `[Tracking: Spot S/M/L]` / `[Tracking: Expand Spot]` **initial start position** (does **not** follow active subject tracking; locks to `Center` for `Wide`/`Zone`/`Center Fix`).
  - **`[AEL w/ Shutter]`** (Still only, `BKID_APP_setting_still_image_ael_w_shutter`): **`Auto`** (**factory default**) / `On` / `Off`. **NOT resettable via `[Camera Settings Reset]`** (only `[Initialize]`).
  - **`[Exposure Std. Adjust]`** (`BKID_APP_setting_exposure_standard_metering_mode_{multi,center,spot,average,highlight}`): Independent `-1 EV .. +1 EV` (`1/6 EV` steps) zero-point trim per base metering mode.

### 3.2 Behavior Under `[Log Shooting] = [Cine EI]` / `[Cine EI Quick]`

- In `Cine EI` / `Cine EI Quick`, sensor recording sensitivity is **hard-locked to Base ISO** (`ISO 800 [L]` or `ISO 12800 [H]`; `[Auto Slow Shutter]` is also disabled), and `[Exposure Index]` (`200EI..3200EI` @ `ISO 800`, `3200EI..51200EI` @ `ISO 12800`) shifts **monitoring brightness only** when `[Display LUT] = [On]`.
- Consequently, `[Metering Mode]` **does not alter recording ISO/gain** in `Cine EI`; instead, it feeds the **Metered Manual (`M.M.`)** deviation indicator (`-` / `0` / `+` EV relative to `[Exposure Std. Adjust]`) as a passive exposure-monitoring reference while the operator sets aperture, shutter, or external ND. *(Locked to `Multi` in `Intelligent Auto` or non-optical zoom.)*

---

## 4. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 4.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 48 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_picture_profile` (`OFF`, `PP1..PP11`, `PPLUT1..4`), `CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG`, `BKID_APP_setting_different_set`, `BKID_APP_setting_creative_style_plus` (`10` looks + `CREATIVE_BOX_1..6`), `BKID_APP_setting_dro*` (`AUTO`, `LV1..5`), `BKID_APP_setting_log_shooting` (`OFF`, `FLEXIBLE_ISO`, `CINE_EI_QUICK`, `CINE_EI`), `BKID_APP_setting_select_lut`, `BKID_APP_setting_white_balance` (`2500K..9900K`, `A7`/`B7`/`G7`/`M7`), `BKID_APP_setting_priority_set_in_awb`, `BKID_APP_setting_stl_awb_lock_with_shutter`, `BKID_APP_setting_movie_shockless_wb`, `BKID_APP_setting_metering_mode*`, `BKID_APP_setting_face_detection_in_multi`, `BKID_APP_setting_spot_metering_link_to_focus_point`, `BKID_APP_setting_still_image_ael_w_shutter` |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `PP1..PP11`, `S-Cinetone`, `Creative Look`, `ST/PT/NT/VV/VV2/FL/IN/SH/BW/SE`, `Log Shooting`, `Cine EI`, `Cine EI Quick`, `Flexible ISO`, `<2500K`/`>9900K`, `Priority Set in AWB`, `Shutter AWB Lock`, `Shockless WB`, `Spot: Standard/Large`, `Entire Screen Avg.`, `Highlight`, `Face Priority in Multi Metering`, `Spot Metering Point`, `Focus Point Link`, `AEL w/ Shutter` |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `resid16` 1:1 parity across all Wave 48 `_f.uxc` records |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `resid16` 1:1 parity across all Wave 48 `_f.uxc` records |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `resid16` 1:1 parity across all Wave 48 `_f.uxc` records |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `D-Range Optimizer` (`0xe89c`, `Auto`/`Lv1..Lv5`), `White Balance` (`0xe5d4`), `Custom 1..3` (`0xe79d`/`0xe79b`/`0xe79c`), `C.Temp./Filter` (`0xe2ac`), `Metering Mode` (`0xe5cf`), `Multi` (`0xe631`), `Center` (`0xe787`), `Cloudy`/`Shade` (`0xe023`/`0xe800`) |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `0x6361` (`Different Set for Still/Mv` prompt), `0x6538` (Still Log `Gamma Display Assist` auto-on notice) |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records (`819` subsystems, `35,668` / `31,197` properties; checksums `0x018adbdb` & `0x09443bb1` PASS) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_USER_MENU_BASE_LOOK0..8`, `BKID_APP_SETTING_BASE_LOOK_{LUT_DISPLAY,OUTPUT}`, `BKID_APP_EXTERN_WHITEMEMORY{A,B}_ND*`, `BKID_APP_SETTING_ATW_MODE`, `BKID_APP_SETTING_MOVIE_SHOCKLESS_WB` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `S-Cinetone` (`0x20f5`), `Base Look` (`0x23f8`), `709tone` (`0x288f`), `HLG Live/Natural/Mild`, `ATW` (`0x207a`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Memory A` (`0x4b23`), `Memory B` (`0x4b24`), `Preset 3200K/4300K/5500K` (`0x4794..0x4799`), `S-Gamut3(3200K/4300K/5500K)` (`0x433f..0x4343`), `Shockless White` (`0x4404`) |

### 4.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` & `string_*.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Domain / Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x6830` | `Picture Profile` | `图片配置文件` | `相片設定檔` | `ﾋﾟｸﾁｬｰﾌﾟﾛﾌｧｲﾙ` | Color/Tone (`PP11` default) |
| `_f` `0x67ab` | `PP11` | `PP11` | `PP11` | `PP11` | Default FX3 Profile (`S-Cinetone`) |
| `_f` `0x6e61` | `S-Cinetone` | `S-Cinetone` | `S-Cinetone` | `S-Cinetone` | `PP11` Gamma & Color Mode |
| `_f` `0x62ee` | `Different Set for Still/Mv` | `静态/动态不同设置` | `不同靜像/影片設定` | `静止画/動画独立設定` | Still/Movie Split Gate |
| `_f` `0x6823` | `\ue662Creative Look` | `\ue662创意外观` | `\ue662風格外觀` | `\ue662ｸﾘｴｲﾃｨﾌﾞﾙｯｸ` | `ST` (`0x770c`)..`SE` (`0x7702`), `VV2` (`0x7864`) |
| `.uxc` `0xe89c` | `D-Range Optimizer` | `动态范围优化` | `動態範圍最佳化` | `Dﾚﾝｼﾞｵﾌﾟﾃｨﾏｲｻﾞｰ` | `Auto` (`0xea04`), `Lv1..Lv5` (`0xea38..0xe0be`) |
| `_f` `0x6020` | `Log Shooting` | `Log拍摄` | `Log拍攝` | `Log撮影` | `Flexible ISO` (`0x6c9a`), `Cine EI Quick` (`0x611e`), `Cine EI` (`0x6822`) |
| `_f` `0x643e` | `Select LUT` | `选择LUT` | `選取LUT` | `LUT選択` | `s709` (`0x6a3e`) default; `Display LUT` (`0x729a`) |
| `.uxc` `0xe5d4` | `White Balance` | `白平衡模式` | `白平衡` | `ホワイトバランス` | `Auto` (`0xe6da`) default |
| `.uxc` `0xe2ac` | `C.Temp./Filter` | `色温/滤光片` | `色溫/彩色濾鏡` | `色温度・ｶﾗｰﾌｨﾙﾀｰ` | `<2500K` (`0x6741`)..`>9900K` (`0x751f`) |
| `.uxc` `0xe79d`..`0xe79c` | `Custom 1` / `Custom 2` / `Custom 3` | `自定义 1/2/3` | `自訂 1/2/3` | `カスタム 1/2/3` | Memorized WB slots (excluded from `CAMSET`) |
| `_f` `0x67a7` | `Priority Set in AWB` | `AWB优先级设置` | `AWB優先順序設定` | `AWB時の優先設定` | `Standard` (`0x6500`), `Ambience` (`0x749f`), `White` (`0x6541`) |
| `_f` `0x66db` | `Shutter AWB Lock` | `快门AWB锁定` | `快門AWB鎖` | `ｼｬｯﾀｰAWBﾛｯｸ` | `Shutter Half Press` (`0x6373`), `Cont. Shooting` (`0x6a32`), `Off` (`0x61b3`) |
| `_f` `0x62fe` | `Shockless WB` | `减震WB` | `減震WB` | `ショックレスWB` | `1 (Fast)` (`0x6649`)..`3 (Slow)` (`0x6ef1`) |
| `.uxc` `0xe5cf` | `Metering Mode` | `测光模式` | `測光模式` | `測光モード` | `Multi` (`0xe631`), `Center` (`0xe787`), `Spot: Standard` (`0x630e`), `Spot: Large` (`0x7357`), `Entire Screen Avg.` (`0x6aa1`), `Highlight` (`0x6491`) |
| `_f` `0x69c7` | `Face Priority in Multi Metering` | `多重测光时人脸优先` | `多重測光時面孔優先` | `ﾏﾙﾁ測光時の顔優先` | `On` (`0x6aa2`, default) / `Off` (`0x61b3`) |
| `_f` `0x71b5` | `Spot Metering Point` | `点测光点` | `重點測光點` | `スポット測光位置` | `Center` (`0x7080`) / `Focus Point Link` (`0x625c`) |
| `_f` `0x669d` | `AEL w/ Shutter` | `快门AEL` | `半按快門AEL` | `ｼｬｯﾀｰ半押しAEL` | `Auto` (default) / `On` / `Off` (not resettable by Camera Reset) |
