# Global Sony Real-Hardware Intelligence — Wave 49 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: Still `[Image Quality Settings]` `RAW` / `JPEG` / `HEIF 4:2:2` & `[HLG Still Image]`, `[Color Space]` `AdobeRGB` `_DSC` Prefix Rule, `[Shutter Type]` `Mechanical` vs `Electronic` & `[e-Front Curtain Shut.]`, and `[Long Exposure NR]` / `[High ISO NR]` / `[Drive Mode]` `10 fps` Boundaries)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *JPEG/HEIF Switch*, *Image Quality Settings: File Format (still image)*, *Image Quality Settings: RAW File Type*, *Image Quality Settings: JPEG Quality/HEIF Quality*, *Image Quality Settings: JPEG Image Size/HEIF Image Size*, *HLG Still Image*, *Color Space*, *File/Folder Settings*, *Shutter Type*, *e-Front Curtain Shut.*, *Silent Mode Settings*, *Interval Shoot Func.*, *ISO AUTO Min. SS*, *Long Exposure NR*, *High ISO NR*, *Drive Mode*, *Cont. Shooting*, *Specifications*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_english.uxc` / `_2.uxc`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. Still `[Image Quality Settings]` (`RAW` / `JPEG` / `HEIF`), `[RAW File Type]`, & `[HLG Still Image]` vs Movie-Only `ILME-FX6 Ver. 6.01`

### 1.1 `[JPEG/HEIF Switch]` & `[Image Quality Settings]` Matrix (`ilc/2210` + `appFw.so`)

- **Menu Paths**:
  - `MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[JPEG/HEIF Switch]`** (`BKID_APP_setting_jh_file_type`, `_f.uxc` `0x742a`/`0x6938`; *Note: a separate `[JPEG/HEIF Switch]` exists under `MENU -> (Playback) -> [Edit]` via `BKID_APP_setting_photo_capture_file_type` for frame-grabs from movies*).
  - `MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[Image Quality Settings]`** (`_f.uxc` `0x6ade`).

| Setting (`MENU -> Shooting -> [Image Quality/Rec]`) | Exposed Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key / Notes |
| :--- | :--- | :--- | :---: | :--- |
| **`[JPEG/HEIF Switch]`** | `JPEG`, `HEIF(4:2:0)`, `HEIF(4:2:2)` | **`JPEG`** | **Can be reset** | `BKID_APP_setting_jh_file_type` (`JH_FILE_TYPE_{JPEG, HEIF_420, HEIF_422}`); `HEIF` encodes 10-bit `.HIF` |
| **`[File Format]`** | `RAW`, `RAW & JPEG` / `RAW & HEIF`, `JPEG` / `HEIF` | **`JPEG/HEIF`** | **Can be reset** | `BKID_APP_setting_still_file_format` (+ `_slot1` / `_slot2` under `Sort Recording`) |
| **`[RAW File Type]`** | **`Compressed`**, **`Uncompressed`** | **`Compressed`** | **Can be reset** | `BKID_APP_setting_still_raw_file_type` (`14-bit` `.ARW`, always `3:2` `L`; shared across Slot 1 & Slot 2) |
| **`[JPEG Quality]` / `[HEIF Quality]`** | `Extra fine`, `Fine`, `Standard` | **`Fine`** | **Can be reset** | `BKID_APP_setting_still_{jpeg,heif}_quality` (`EXTRA_FINE`, `FINE`, `STD`) |
| **`[JPEG Image Size]` / `[HEIF Image Size]`** | `L` (`12M` 3:2 / `11M` 4:3 / `10M` 16:9 / `8.0M` 1:1), `M`, `S` | **`L: 12M` (3:2)** | **Can be reset** | `BKID_APP_setting_still_{jpeg,heif}_image_size` (`L`, `M`, `S`) |

- **Empirical Dormant-Enum Distinction (`[RAW File Type]` `Lossless Comp` Trap)**:
  - `O_RDONLY` inspection of `FX3 appFw.so` (`79,015,712 B`) and `string_*_f.uxc` confirms Sony's shared `BIONZ XR` codebase compiles `RAW_FILE_TYPE_LOSSLESS`, `RAW_FILE_TYPE_LOSSLESS_L/M/S` alongside `_f.uxc` `0x6b56` (`Lossless Comp`) and `0x7897`/`0x6bfd`/`0x7894` (`Lossless Comp (L)/(M)/(S)`).
  - **However**, official `helpguide.sony.net/ilc/2210/v1/en/` (*Image Quality Settings: RAW File Type*, *Cont. Shooting*, *List of default setting values*) confirms **`ILME-FX3` (`PRODUCT_MODEL_ALCIN_UUD`, 12 MP `IMX510`) exposes ONLY `[Uncompressed]` and `[Compressed]`** — `Lossless Comp` is gated to sibling high-MP/stacked bodies (`ILCE-7M4`, `ILCE-7RM5`, `ILCE-1`, `ZV-E1`) and yields zero matches in `ilc/2210`.

### 1.2 `[HLG Still Image]` Prerequisites & Mutual-Exclusivity vs `ILME-FX6 Ver. 6.01`

- **Menu Path & Default**: `MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[HLG Still Image]`** (`BKID_APP_setting_still_hlg_photo`, `_f.uxc` `0x76c8`), factory default **`Off`** (`Can be reset`).
- **Strict Activation Prerequisites (`ilc/2210` + `VAL_HAITA_setting_still_hlg_photo_*`)**:
  1. **`[JPEG/HEIF Switch]` MUST be `[HEIF(4:2:0)]` or `[HEIF(4:2:2)]`** — fixed to `[Off]` whenever `[JPEG]` is active.
  2. **`[File Format]` MUST be `[HEIF]` only** — fixed to `[Off]` whenever `[File Format]` is `[RAW]` or `[RAW & HEIF]`.
  3. **Shooting Mode MUST be `P` / `A` / `S` / `M`** — fixed to `[Off]` in `Intelligent Auto` or non-`P/A/S/M` modes, and forced `[Off]` when ISO sensitivity or `[DRO Bracket]` is temporarily activated by `[Reg. Custom Shoot Set]`.
- **Downstream Lockouts & Monitoring When `[HLG Still Image] = [On]`**:
  - **Locked Out**: `[Picture Profile]`, `[Creative Look]`, `[D-Range Optimizer]`, and `[DRO Bracket]` (`Drive Mode`) are unavailable. *(Note: On `ILME-FX3`, `[Log Shooting Setting]` applies to Movie and S&Q modes only, though `appFw.so` carries sibling key `BKID_APP_setting_still_log_shooting`; in movie mode `[Log Shooting]` locks `[Picture Profile]` to `Off` and `[Gamma Display Assist]` to `Off`, whereas in still mode `[HLG Still Image] = [On]` uses `[Gamma Display Assist]` with `[Gamma Disp. Assist Typ.] = [Auto]` or `[HLG(BT.2020)]` per `VAL_HAITA_*_STILL_HLD_PHOTO_ON`.)*
  - **ISO & Gamut Override**: Shifts available still ISO bounds (`VAL_HAITA_*_iso_sensitivity_{min,max}_in_still_hlg_photo_on`) and overrides `[Color Space]` to **`BT.2100` color space / `BT.2020` color gamut**.
- **`ILME-FX6 Ver. 6.01` Still-Less Cinema Contrast**:
  - `ILME-FX6` (`PRODUCT_MODEL_CHAPLIN`) has **zero** `DCIM` still-photo pipeline, zero `.ARW` / `.JPG` / `.HIF` (`HEIF`) still capture, zero `[HLG Still Image]`, and `mechanical_shutter = False`. Its `RAW` (`BKID_APP_SETTING_RAW_OUTPUT_FORMAT`) is strictly 16-bit linear movie RAW over SDI/HDMI (`RAW 4096×2160` / `3840×2160` / `4240×2392`), and its `HLG` (`HDR(HLG)`: `HLG Live`, `HLG Natural`, `HLG Mild`) is exclusively movie `BT.2020` / `HLG_BT.2100`.

---

## 2. `[Color Space]` (`sRGB` Default vs `AdobeRGB`) & DCF 2.0 `_DSC` Filename Prefix Rule

### 2.1 Exact Menu Path, Options, & Reset Boundary (`ilc/2210` + `appFw.so`)

- **Verified Menu Path**: `MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[Color Space]`** (`BKID_APP_setting_still_color_space`, `_f.uxc` `0x68b7`/`0x689d`). *(Note: Located under `(Shooting) -> [Image Quality/Rec]`, not `(Exposure/Color) -> [Color/Tone]`.)*
- **Options & Factory Default**:
  - **`[sRGB]`** (**factory default**, `VAL_setting_still_color_space_STILL_COLOR_SPACE_SRGB`, `.uxc` `0xe07d`, `Can be reset` via `[Camera Settings Reset]`): Standard consumer digital color space.
  - **`[AdobeRGB]`** (`VAL_setting_still_color_space_STILL_COLOR_SPACE_ADOBE_RGB`, `.uxc` `0xe07e`): Wide-gamut DCF 2.0 option color space for vivid greens/reds in color-managed workflows; displays desaturated on non-color-managed viewers.

### 2.2 DCF 2.0 `_DSC` Leading-Underscore Rule & `[Set File Name]` Interaction

- **Automatic Leading-Underscore Mutation**: Under JEITA DCF 2.0 (`100MSDCF` folder in `appFw.so`), selecting `[AdobeRGB]` automatically mutates the still-image filename prefix by prepending `_`:
  - `sRGB`: **`DSC00001.JPG`** / **`DSC00001.ARW`** (using `[Set File Name]` default `DSC`)
  - `AdobeRGB`: **`_DSC0001.JPG`** / **`_DSC0001.ARW`** (`.uxc` `0xe895`: *"Uses Adobe RGB... File names begin with `_DSC.`"*)
- **Why `[Set File Name]` Forbids a Leading `_`**:
  - Under `MENU` -> `(Shooting)` -> `[File]` -> `[File/Folder Settings]` -> **`[Set File Name]`** (`BKID_APP_set_file_name_prefix_still`, `_f.uxc` `0x6993`, factory default **`DSC`**, **`Reset not available` under `[Camera Settings Reset]`** — persists until `[Initialize]` or manual edit), operators can customize the 3-character prefix using capital letters (`A–Z`), digits (`0–9`), and underscores (`_`) — **but `_` cannot be entered as the 1st character**, reserving the leading underscore exclusively for DCF 2.0 `AdobeRGB` identification. (Changes apply non-retroactively to subsequent shots across both Slot 1 and Slot 2.)
- **`HEIF` & `[HLG Still Image]` Override**: When shooting in `HEIF` (`[JPEG/HEIF Switch]` = `HEIF(4:2:0)` or `HEIF(4:2:2)`), `[Color Space]` (`sRGB` / `AdobeRGB`) is **invalid/ignored**: `ILME-FX3` records `sRGB` when `[HLG Still Image] = [Off]`, and **`BT.2100` (`BT.2020`)** when `[HLG Still Image] = [On]`.

---

## 3. `[Shutter Type]`, `[e-Front Curtain Shut.]`, `[Silent Mode Settings]`, & Flash Sync Lockouts

### 3.1 Exact 2-Option `[Shutter Type]` on `ILME-FX3` vs Sibling `Auto` Models

- **Menu Path**: `MENU` -> `(Shooting)` -> `[Shutter/Silent]` -> **`[Shutter Type]`** (`BKID_APP_setting_still_shutter_type`, `_f.uxc` `0x7aa9`/`0x6aeb`) and **`[e-Front Curtain Shut.]`** (`BKID_APP_setting_front_curtaion_shutter` [Sony binary spelling], `_f.uxc` `0x64c6`/`0x782c`).
- **Critical Empirical Finding (`No [Auto] Option` on `ILME-FX3`)**:
  - `O_RDONLY` inspection of `FX3 appFw.so` reveals both a 2-option shutter key (`BKID_APP_setting_still_shutter_type` -> `STILL_SHUTTER_TYPE_MECHANICAL` / `STILL_SHUTTER_TYPE_ELECTRONIC`) and a 3-option stacked-sensor anti-distortion key (`BKID_APP_setting_still_shutter_type_anti_distortion_shutter` -> `AUTO` / `MECHANICAL_SHUT` / `ELECTORONIC_SHUT`).
  - Official `ilc/2210` (*Shutter Type* & *List of default setting values*) confirms **`ILME-FX3` exposes ONLY the 2-option `[Shutter Type]`**:
    1. **`[Mechanical Shutter]`** (**factory default**, `Can be reset` via `[Camera Settings Reset]`).
    2. **`[Electronic Shutter]`** (silent readout, high shutter speeds, maximum burst performance; selectable only in `P / A / S / M`).
  - `[Auto]` under `[Shutter Type]` exists on stacked/compact siblings (`ILCE-1`, `ILCE-9`, `DSC-RX100M7`, `ZV-1`), **not** `ILME-FX3`. (Similarly, `[Shutter Type in Interval]` under `[Interval Shoot Func.]` exposes `[Mechanical Shutter]` vs `[Electronic Shutter]`, defaulting to **`[Electronic Shutter]`**.)

### 3.2 `[e-Front Curtain Shut.]`, `[Silent Mode Settings]`, & `1/250 s` Flash Sync Lockouts

| Setting (`MENU -> Shooting -> [Shutter/Silent]`) | Options | Factory Default | `[Camera Settings Reset]` | Key Constraints (`ilc/2210`) |
| :--- | :--- | :--- | :---: | :--- |
| **`[Shutter Type]`** | `Mechanical Shutter`, `Electronic Shutter` | **`Mechanical Shutter`** | **Can be reset** | Selectable only in `P/A/S/M`; locked to `Electronic Shutter` when `Silent Mode = On` |
| **`[e-Front Curtain Shut.]`** | `On`, `Off` | **`On`** | **Not available** *(needs `[Initialize]`)* | Unavailable when `Shutter Type = Electronic Shutter` or `Silent Mode = On`; high SS + wide aperture can clip bokeh |
| **`[Silent Mode]`** (`[Silent Mode Settings]`) | `On`, `Off` | **`Off`** | **Can be reset** | Forces `Shutter Type = Electronic`, `Shutter Type in Interval = Electronic`, `Audio signals = Off`; optional targets `Aperture Drive in AF` (`Standard` default) & `Auto Pixel Mapping` (`Off` default) |

- **Flash Sync Ceiling (`1/250 s` Only) & Electronic Shutter Lockout**:
  - `ilc/2210` *Specifications* and *ISO AUTO Min. SS* pin `ILME-FX3`'s mechanical flash sync speed at **`1/250 second`** (`_f.uxc` `0x759b`; no separate `1/320 s` APS-C sync speed exists on `ILME-FX3`, unlike `ILCE-7RM5`/`ILCE-7M5`).
  - Whenever **`[Shutter Type] = [Electronic Shutter]`** OR **`[Silent Mode] = [On]`**, `ILME-FX3` **locks out all 5 functions**:
    1. **Flash shooting** (complete lockout; no electronic-shutter flash sync),
    2. **`[Long Exposure NR]`**,
    3. **`[e-Front Curtain Shut.]`**,
    4. **`BULB` shooting**,
    5. **`[Anti-flicker Shoot.]`**.
  - *(Note: Even in `[Electronic Shutter]` or `[Silent Mode] = [On]`, mechanical shutter sound can still occur on power-off if `[Auto Pixel Mapping] = [On]` or when registering a face with `[Face Memory]`.)*

---

## 4. `[Long Exposure NR]`, `[High ISO NR]`, & `[Drive Mode]` (`10 fps` `Hi+` & Bracket Boundaries)

### 4.1 `[Long Exposure NR]` (`On` Default) & `[High ISO NR]` (`Normal` Default)

- **`[Long Exposure NR]` (`MENU -> (Shooting) -> [Image Quality/Rec] -> [Long Exposure NR]`)**:
  - `BKID_APP_setting_still_long_exposure_nr` (`ON` / `OFF`), factory default **`On`** (`Can be reset`).
  - At shutter speeds **`>= 1 second`** (including `BULB`), captures a post-exposure dark frame of equal duration (`t_NR == t_shutter`) during which a processing banner appears and **subsequent capture is blocked**.
  - **Lockouts**: Unavailable whenever `[Shutter Type] = [Electronic Shutter]`, `[Silent Mode] = [On]`, or `[Drive Mode]` = `[Cont. Shooting]` or `[Cont. Bracket]`. Cannot be set to `[Off]` in `[Intelligent Auto]`.
- **`[High ISO NR]` (`MENU -> (Shooting) -> [Image Quality/Rec] -> [High ISO NR]`)**:
  - `BKID_APP_setting_still_high_iso_nr` (`NORMAL` / `LOW` / `OFF`), factory default **`Normal`** (`Can be reset`).
  - **RAW Immunity & Lockout**: Unavailable when `[File Format] = [RAW]`; ignored for the `.ARW` output when `[File Format]` = `[RAW & JPEG]` or `[RAW & HEIF]` (applies strictly to the processed JPEG/HEIF). Fixed to `[Normal]` in `[Intelligent Auto]`.

### 4.2 `[Drive Mode]` (`10 fps` `Cont. Shooting: Hi+`, Brackets, & Speed/AF Couplings)

- **Menu Path & Default**: `MENU` -> `(Shooting)` -> `[Drive Mode]` -> **`[Drive Mode]`** (`BKID_APP_setting_menu_drive_mode`, `_f.uxc` `0x7228`), factory default **`Single Shooting`** (`Can be reset`).
- **All 8 Exposed Modes (`ilc/2210` + `VAL_setting_menu_drive_mode_*`)**:
  1. **`Single Shooting`** (**default**)
  2. **`Cont. Shooting`**: **`Hi+`** (max approx. **`10 fps`**), **`Hi`** (max approx. **`8 fps`**), **`Mid`** (max approx. **`6 fps`**), **`Lo`** (max approx. **`3 fps`**) (`BKID_APP_setting_drive_mode_cont_shooting`)
  3. **`Self-timer(Single)`** (`2 s`, `5 s`, `10 s`)
  4. **`Self-timer(Cont)`**
  5. **`Cont. Bracket`** (`0.3`–`3.0 EV` steps, `3`/`5`/`7`/`9` frames)
  6. **`Single Bracket`**
  7. **`WB bracket`** (`Lo` / `Hi`)
  8. **`DRO Bracket`** (`Lo` / `Hi`; disabled when `[HLG Still Image] = [On]`)
- **Real-Hardware Speed, Buffer & Focus Couplings (`ilc/2210`)**:
  - **RAW & Flash Speed Drop**: Continuous shooting speed drops below `10 fps` when shooting **`[Uncompressed]` RAW** (whereas **`[Compressed]` RAW** sustains full `Hi+` `10 fps`) or when firing a **flash**.
  - **Buffer Depth (`SLOW`)**: On a Sony `CEA-G160T` CFexpress Type A card (`L: 12M`), `Hi+` sustains **approx. 1,000+ images** across JPEG/HEIF (`Fine`), `Compressed` RAW, and `Uncompressed` RAW (including `RAW & JPEG/HEIF`) before buffer saturation displays **`SLOW`** and throttles burst rate.
  - **Monitor & `F > F11` AF Lock**: In `Cont. Shooting: Hi+`, live real-time subject view is not displayed on the monitor (slideshow/post-view cadence). In `Hi+`, `Hi`, and `Mid`, **when aperture is stopped down beyond `F11` (`> F11`), focus is locked to the first shot**.

---

## 5. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 5.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 49 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_jh_file_type` (`JPEG`, `HEIF_420`, `HEIF_422`), `BKID_APP_setting_still_file_format` (`RAW`, `RAW_JPEG`, `RAW_HEIF`, `JPEG`, `HEIF`), `BKID_APP_setting_still_raw_file_type`, `BKID_APP_setting_still_hlg_photo`, `BKID_APP_setting_still_color_space` (`SRGB`, `ADOBE_RGB`), `BKID_APP_set_file_name_prefix_still`, `BKID_APP_setting_still_shutter_type` (`MECHANICAL`, `ELECTRONIC`), `BKID_APP_setting_front_curtaion_shutter`, `BKID_APP_setting_silent_mode`, `BKID_APP_setting_still_long_exposure_nr`, `BKID_APP_setting_still_high_iso_nr`, `BKID_APP_setting_drive_mode_cont_shooting` (`HI_PLUS`, `HI`, `MID`, `LOW`) |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` sequential `0x1e1c` records (`0x6000..0x7d3d`): `Image Quality Settings`, `JPEG/HEIF Switch`, `HEIF(4:2:0)`, `RAW File Type`, `HLG Still Image`, `Color Space`, `Set File Name`, `Shutter Type`, `Mechanical Shutter`, `Electronic Shutter`, `e-Front Curtain Shut.`, `Silent Mode Settings`, `Long Exposure NR`, `High ISO NR`, `Drive Mode`, `Cont. Shooting: Hi+`, `1/250`, plus dormant sibling `Lossless Comp` (`0x6b56`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` records: `sRGB` (`0xe07d`), `AdobeRGB` (`0xe07e`), `0xe895` (`_DSC.` hint), `RAW`/`RAW & JPEG`/`RAW & HEIF`/`HEIF`, `Extra fine`/`Fine`/`Standard`, `Normal`/`Low`/`Off`, `Single Shooting`/`Cont. Shooting`/`Cont. Bracket`/`Single Bracket`/`WB bracket`/`DRO Bracket` |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` records: `Image Quality/Rec` (`0x601d`), `Drive Mode` (`0x616e`), `Image Quality` (`0x6181`), `Silent Mode` (`0x6079`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records (`819` subsystems, `35,668` / `31,197` properties; checksums `0x018adbdb` & `0x09443bb1` PASS) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | Still-less `PRODUCT_MODEL_CHAPLIN`: movie `BKID_APP_SETTING_RAW_OUTPUT_FORMAT` & `BKID_APP_SETTING_SHUTTER_SELECT` (`Speed`/`Angle`); zero still `HEIF`/`AdobeRGB`/`e-Front`/`Long Exposure NR`/`High ISO NR` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `RAW Output Format` (`0x218d`), `RAW 4096×2160` (`0x2197`), `HDR(HLG)` (`0x2212`), `HLG Live/Natural/Mild` (`0x21a3..0x21dc`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Shutter Mode` (`0x43be`), `Shutter Speed` (`0x4d94`), `Shutter Angle` (`0x4d96`), `Slow Shutter` (`0x4210`), `HLG_BT.2100` (`0x431e`) |

### 5.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Domain / Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_g` `0x601d` | `Image Quality/Rec` | `影像质量/记录` | `影像畫質/錄製` | `画質/記録` | Shooting submenu |
| `_f` `0x742a` | `JPEG/HEIF Switch` | `JPEG/HEIF切换` | `JPEG/HEIF切換` | `JPEG/HEIF切換` | `JPEG` (default) / `HEIF(4:2:0)` (`0x7959`) / `HEIF(4:2:2)` |
| `_f` `0x6ade` | `Image Quality Settings` | `影像质量设置` | `影像畫質設定` | `画質/画像ｻｲｽﾞ設定` | Still image quality container |
| `.uxc` `0xe73d` | `File Format` | `文件格式` | `檔案格式` | `記録方式` | `RAW` (`0xe738`), `RAW & JPEG` (`0xe739`), `RAW & HEIF` (`0xe1fc`), `HEIF` (`0xe7ff`) |
| `_f` `0x6ff2` | `RAW File Type` | `RAW文件类型` | `RAW檔案類型` | `RAW記録方式` | `Compressed` (`0x6f67`, default) / `Uncompressed` (`0x67a9`/`0x6f5b`); dormant `Lossless Comp` (`0x6b56`) |
| `_f` `0x76c8` | `HLG Still Image` | `HLG静态影像` | `HLG靜態影像` | `HLG静止画` | `Off` (default) / `On` -> `HLG(BT.2020)` (`0x79e1`) |
| `_f` `0x68b7` | `Color Space` | `色彩空间` | `色彩空間` | `色空間` | `sRGB` (`.uxc` `0xe07d`, default) / `AdobeRGB` (`.uxc` `0xe07e`) |
| `_f` `0x6993` | `Set File Name` | `设置文件名` | `設定檔案名稱` | `ファイル名設定` | `DSC` default (leading `_` forbidden manually) |
| `_f` `0x7aa9` | `\ue08cShutter Type` | `\ue08c快门类型` | `\ue08c快門類型` | `\ue08cシャッター方式` | `Mechanical Shutter` (`0x6ddb`, default) / `Electronic Shutter` (`0x60a1`) |
| `_f` `0x64c6` | `e-Front Curtain Shut.` | `电子前帘快门` | `電子式前簾快門` | `電子先幕ｼｬｯﾀｰ` | `On` (default; NOT reset by Camera Settings Reset) |
| `_f` `0x7a53` | `Silent Mode` | `静音模式` | `靜音模式` | `サイレントモード` | Forces Electronic Shutter (`_g` `0x6079`) |
| `_f` `0x6cd7` | `\ue08cLong Exposure NR` | `\ue08c长时曝光降噪` | `\ue08c消除長曝雜訊` | `\ue08c長秒時NR` | `On` (default); `>= 1 s` dark frame |
| `_f` `0x650b` | `High ISO NR` | `高ISO降噪` | `高ISO雜訊消除` | `高感度ノイズ低減` | `Normal` (`.uxc` `0xe9ae`, default) / `Low` (`0xe06e`) / `Off` (`0xe6d8`) |
| `_f` `0x7228` | `Drive Mode` | `拍摄模式` | `過片模式` | `ドライブモード` | `Single Shooting` (`.uxc` `0xe842`, default) |
| `_f` `0x68d1` | `Cont. Shooting: Hi+` | `连拍：Hi+` | `連拍：Hi+` | `連続撮影: Hi+` | `10 fps` (`Hi` `0x6c00`, `Mid` `0x6f48`, `Lo` `0x6a0b`) |
| `.uxc` `0xe8f7` | `Cont. Bracket` | `连续阶段曝光` | `連拍包圍式曝光` | `連続ブラケット` | Locks out `Long Exposure NR`; siblings `Single Bracket` (`0xe190`), `WB bracket` (`0xe7cf`), `DRO Bracket` (`0xe18f`) |
