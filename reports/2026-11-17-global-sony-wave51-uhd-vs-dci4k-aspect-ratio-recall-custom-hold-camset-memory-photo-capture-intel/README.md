# Global Sony Real-Hardware Intelligence — Wave 51 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: Internal `UHD 3840x2160` vs `XAVC S-I DCI 4K 4096x2160` & `4264x2408` HDMI RAW, Still `[Aspect Ratio]` `3:2/4:3/16:9/1:1`, `[Reg. Custom Shoot Set]` `Recall Custom hold 1..3`, `[Camera Set. Memory]` `1..3` + `M1..M4` vs FX6 `Scene/User/All File`, and `[Playback]` `[Photo Capture]` `8.3M/2.1M` / `[Enlarge Image]`)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *File Format (movie)*, *Movie Settings (movie)*, *Outputting RAW movies to an external RAW recorder*, *HDMI Output Settings (movie)*, *Shutter Mode*, *Aspect Ratio*, *JPEG Image Size/HEIF Image Size*, *HLG Still Image*, *Reg. Custom Shoot Set*, *Camera Set. Memory*, *Recall Camera Setting*, *Memory/Recall Media*, *Save/Load Settings*, *Format*, *Setting Reset*, *Photo Capture*, *JPEG/HEIF Switch (Photo Capture)*, *Enlarge Image*, *Enlarge Initial Mag.*, *Enlarge Initial Position*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_english.uxc` / `_2.uxc`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. Internal `UHD 3840×2160` (`16:9`) vs `XAVC S-I DCI 4K` (`4096×2160`, `17:9`) + `4264×2408` HDMI RAW & Still `[Aspect Ratio]`

### 1.1 Critical Empirical Correction: `XAVC S-I DCI 4K` (`4096×2160`) **IS** Present in `ILME-FX3 Ver. 3.00+` (`Ver. 7.02`), Absent in Long-GOP & `120p`

A naive assumption that `ILME-FX3` lacks *all* internal DCI 4K recording is **refuted** by both `helpguide.sony.net/ilc/2210/v1/en/` (*File Format (movie)* `TP1000868279.html`, *Movie Settings (movie)* `TP1000868278.html`) and `FX3 Ver. 7.02 appFw.so` / `_f.uxc` (`0x7336`, `0x61ce`):
- **Where DCI 4K IS present on `ILME-FX3 Ver. 7.02`**: Firmware `Ver. 3.00 or later` added **`[XAVC S-I DCI 4K]`** (`4096×2160`, `17:9`, All-Intra `4:2:2 10bit`) alongside **`24.00p`** (`240M 4:2:2 10bit`, NTSC & PAL) and **`[Shutter Mode] = [Angle]`** (`Ver. 6.00+`, `TP1001690662.html`, `_f.uxc` `0x7c7c`, `VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6..360_POINT_0` / `2F..64F`).
- **Where DCI 4K IS absent on `ILME-FX3 Ver. 7.02`**:
  1. **All Long-GOP 4K codecs (`[XAVC HS 4K]` HEVC & `[XAVC S 4K]` H.264)** and **`[XAVC S-I 4K]`** remain strictly **`3840×2160` (`16:9` UHD)** (`_f.uxc` `0x6924`, `0x62dc`, `0x782a`, `0x74c8`). Neither `4096×2160` nor `24.00p` is selectable in `XAVC HS 4K` or `XAVC S 4K` or `XAVC S-I 4K` (note: dormant `xavc_hs_8k_24p` symbols in `appFw.so` are inherited Alpha engine strings unused on `FX3`'s 12MP sensor).
  2. **No `119.88p` / `100p` in `XAVC S-I DCI 4K`**: `XAVC S-I DCI 4K` tops out at `59.94p`/`50p` (`600M`/`500M`); `[120fps]` and `[100fps]` are locked out in `[S&Q Settings]` under `XAVC S-I DCI 4K` (`VAL_setting_sq_frame_rate_xavc_s_i_dci_4k_*` only exposes `1, 2, 3, 6, 12, 24, 48 fps`).
  3. **Mandatory Reboot & Playback Isolation on `24.00p`**: Switching into or out of `24.00p` triggers a **camera reboot** and segregates playback (`_g.uxc` `0x639b`/`0x63b6`: *"Reboots if changed to this shooting mode. Movies recorded in recording frame rate 24.00p cannot be played back if changed."*; `_g.uxc` `0x63d7`).
  4. **Playback/Edit Lockout on `XAVC S-I DCI 4K`**: `_g.uxc` `0x60ce` explicitly blocks certain playback operations (such as `[Photo Capture]`) on `XAVC S-I DCI 4K` clips (*"Cannot perform this operation for movies recorded with their 'File Format' set to 'XAVC S-I DCI 4K'"*).

| Format / Output Path | `ILME-FX3 Ver. 7.02` Resolution & Aspect | Frame Rates / Bitrates | `ILME-FX6 Ver. 6.01` Cinema Contrast (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- | :--- |
| **Internal Long-GOP 4K** | **`3840×2160` (`16:9` UHD only)** (`XAVC HS 4K` / `XAVC S 4K`) | `XAVC HS 4K`: `23.98p/50p/59.94p/100p/119.88p` (`30M–280M`); `XAVC S 4K`: `23.98p–119.88p` (`60M–280M`); **NO `24.00p`, NO `4096×2160`** | **`XAVC-L QFHD`**: strictly **`3840×2160`** (`16:9`, `4:2:0 8-bit`, `35–150 Mbps`, `23.98p–59.94p`); `FX6` likewise has **NO `4096×2160` in Long-GOP `XAVC-L`** |
| **Internal All-Intra UHD** | **`3840×2160` (`16:9` UHD)** (`XAVC S-I 4K`, `.mp4`) | `23.98p` (`240M`), `25p` (`250M`), `29.97p` (`300M`), `50p` (`500M`), `59.94p` (`600M`), S&Q `1–120fps` | **`XAVC-I QFHD`**: **`3840×2160`** (`MXF`, `Class300`, `4:2:2 10-bit`, `23.98p–59.94p`, S&Q `1–120fps`) |
| **Internal All-Intra DCI 4K** | **`4096×2160` (`17:9` DCI 4K)** (`XAVC S-I DCI 4K`, `Ver. 3.00+`, `_f.uxc` `0x7336`/`0x61ce`) | `23.98p`/`24.00p` (`240M`), `25p` (`250M`), `29.97p` (`300M`), `50p` (`500M`), `59.94p` (`600M`); **`CFexpress VPG200+` or `SDXC V90+`** at `600M`; S&Q `1–48fps` (no `100/120fps`); `24.00p` forces reboot | **`XAVC-I DCI 4K`**: native **`4096×2160`** (`MXF`, `4:2:2 10-bit`, `23.98p/24p/25p/29.97p/50p/59.94p`, S&Q `1–60fps` `BKID_APP_EXTERN_DCI_4K_REC_FRAME_RATE`) without `24.00p` playback quarantine |
| **External RAW Output** | **`4264×2408` (`16:9` Type-A HDMI RAW only)** (`TP1002078215.html`) | `59.94p/50p/29.97p/25p/23.98p/24.00p` (`VAL_setting_raw_output_frame_rate_RAW_OUTPUT_FRAME_RATE_24_00P`); requires `[Log Shooting] != Off`, locks gamma to `S-Log3`, disables `SteadyShot Active` & `[De-Squeeze Display]` | **SDI / HDMI RAW** (`RAW` or `RAW & XAVC-I`): native **`4096×2160`** (`FF RAW 4096`, `23.98p–59.94p` incl. `24p`) & **`3840×2160`** (`FF RAW 3840`) |

### 1.2 Still `[Aspect Ratio]` (`3:2` / `4:3` / `16:9` / `1:1`) & `RAW` Metadata Boundary

- **Menu Path**: `MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[Aspect Ratio]`** (`BKID_APP_setting_aspect_ratio`, `_f.uxc` `0x757c`/`0x78a4`/`0x691f`, `.uxc` `0xe680`/`0xe648`).
- **Factory Default & Reset**: **`[3:2]`** (`Can be reset` via `[Camera Settings Reset]`, `TP1000888852.html`). Paired `[JPEG Image Size]` / `[HEIF Image Size]` defaults to **`L`** for the active aspect ratio (`Can be reset`).

| `[Aspect Ratio]` (`ilc/2210`) | `L` Size (`Full-Frame`) | `M` Size *(Also `APS-C S35` Max)* | `S` Size | `appFw.so` Enum & `RAW` Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **`3:2`** (**Default**, `.uxc` `0xe4f8`) | **`12M`** (`4240×2832`, `_f` `0x6f85`) | **`5.1M`** (`2768×1848`, `_f` `0x6c35`) | **`3.0M`** (`2128×1416`, `_f` `0x71bc`) | `VAL_setting_aspect_ratio_ASPECT_RATIO_3_2`; native full-sensor `3:2` |
| **`4:3`** (`_f` `0x7826`, `.uxc` `0xe14f`) | **`11M`** (`3776×2832`, `_f` `0x703f`) | **`4.6M`** (`2464×1848`, `_f` `0x7746`) | **`2.7M`** (`1888×1416`, `_f` `0x7546`) | `VAL_setting_aspect_ratio_ASPECT_RATIO_4_3`; `RAW` retains full `3:2` pixels with `4:3` crop metadata; JPEG/HEIF cropped |
| **`16:9`** (`_f` `0x787d`, `.uxc` `0xe475`) | **`10M`** (`4240×2384`, `_f` `0x7040`/`0x6004`) | **`4.3M`** (`2768×1560`, `_f` `0x6dd5`) | **`2.6M`** (`2128×1200`, `_f` `0x7547`) | `VAL_setting_aspect_ratio_ASPECT_RATIO_16_9`; `RAW` retains full `3:2` pixels with `16:9` crop metadata; JPEG/HEIF cropped |
| **`1:1`** (`.uxc` `0xe0d9`) | **`8.0M`** (`2832×2832`, `_f` `0x7a2f`) | **`3.4M`** (`1840×1840`) | **`2.0M`** (`1408×1408`, `_f` `0x715c`) | `VAL_setting_aspect_ratio_ASPECT_RATIO_1_1`; `RAW` retains full `3:2` pixels with `1:1` crop metadata; JPEG/HEIF cropped |

- **Hardware & Mode Coupling**:
  - `VAL_HAITA_System_mode_Setting_aspect_ratio_REC_MOVIE_ASPECT_RATIO_NOT_16_9` segregates still aspect selection from movie recording (`16:9` UHD or `17:9` DCI 4K).
  - Under `[APS-C S35 Shooting] = [On]`, `L` is unavailable and JPEG/HEIF output temporarily steps down to `M`.
  - **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` has **no** still `[Aspect Ratio]` setting (`SETTING_ASPECT_RATIO` in `FX6 appFw.so` is dormant Alpha C++ dead-code); `FX6` exposes strictly movie viewfinder frame-line `[Marker]` / `[Custom Aspect Ratio]` (`BKID_APP_MARKER_ASPECT_CUSTOM_RATIO_{WIDTH,HEIGHT}`).

---

## 2. `[Reg. Custom Shoot Set]` (`Recall Custom hold 1..3`) vs `[Camera Set. Memory]` (`1..3` + `M1..M4`) vs `ILME-FX6` `Scene/User/All File`

### 2.1 `[Reg. Custom Shoot Set]` (`Recall Custom hold 1..3`, Still `P/A/S/M` Temporary Hold Override)

- **Menu Path**: `MENU` -> `(Shooting)` -> `[Shooting Mode]` -> **`[Reg. Custom Shoot Set]`** (`_f.uxc` `0x7631`/`0x6282`) -> **`[Recall Custom hold 1]`** (`0x60b4`, default cursor), **`[Recall Custom hold 2]`** (`0x7581`), **`[Recall Custom hold 3]`** (`0x725b`).
- **Factory Default & Reset**: `[Recall Custom hold 1]` cursor default; **`Not available`** for `[Camera Settings Reset]` (requires `[Initialize]` to wipe registered slots).
- **Operational Scope & Constraints (`TP1000881010.html` + `TP1000885387.html` + `FX3 appFw.so`)**:
  - **Still `P/A/S/M` Only**: Unavailable in `Movie`, `S&Q Motion`, `Intelligent Auto`, or `MR` (`Recall Camera Setting`). Assigned to a physical button via `[Custom Key/Dial Set.]`; pressing and **holding** the key activates `SHOOT_SET_REGISTRATION_RECALL_STATUS_REGIST{1,2,3}` (`shoot_set_registration_recall_start`), and releasing immediately restores the baseline settings (`shoot_set_registration_recall_end`).
  - **UI Actions**: Supports individual parameter checkboxes (`is_checked_recall_custom_hold0..10`), **`[Import Current Setting]`** (`_f.uxc` `0x7404`/`0x690f`, `shoot_set_registration_import_current_setting`), and **`[Register]`** (`_f.uxc` `0x7ab8`).
  - **`[HLG Still Image]` Lockout**: Per `TP1000885387.html`, temporarily recalling `ISO` or `DRO Bracket` via `[Reg. Custom Shoot Set]` forces **`[HLG Still Image]` = `[Off]`** while held.
  - **Empirical Checkbox Audit (`11` `BKID_APP_shoot_set_registration_*` Keys in `FX3 Ver. 7.02 appFw.so`)**: While Sony's Help Guide summarizes selectable parameters under three broad groups (*Exposure*, *Focus setting*, *Drive mode (other than self-timer)*), `FX3 appFw.so` exposes **11** distinct `*_available{0..3}` checkbox keys matching `is_checked_recall_custom_hold0..10`:
    1. `shooting_mode` (`Shoot Mode` `P/A/S/M`)
    2. `aperture` (`Aperture`)
    3. `shutter_speed` (`Shutter Speed` / `BULB`)
    4. `exposure_comp` (`Exposure Comp.`)
    5. `iso_sensitivity` (`ISO` + `iso_auto_rate_min/max`)
    6. `metering_mode` (`Metering Mode`)
    7. `drive_mode` (`Drive Mode` — continuous / `DRO Bracket` / `WB Bracket`, excluding self-timer)
    8. `focus_mode` (`Focus Mode`)
    9. `focus_area` (`Focus Area`)
    10. `af_on` (`AF On`, `_f.uxc` `0x6443`)
    11. `still_af_track_sens` (`AF Track Sens.` `1 Locked on` .. `5 Responsive`)

### 2.2 `[Camera Set. Memory]` (`1..3` Body NVRAM + `M1..M4` Card) vs `[Save/Load Settings]` & Empirical Card Paths

| Feature / Property | `[Reg. Custom Shoot Set]` (`Recall Custom hold 1..3`) | `[Camera Set. Memory]` Body **`1..3`** | `[Camera Set. Memory]` Card **`M1..M4`** | `[Save/Load Settings]` (`CAMSET01..10.DAT`) |
| :--- | :--- | :--- | :--- | :--- |
| **Menu Path** | `(Shooting) -> [Shooting Mode] -> [Reg. Custom Shoot Set]` | `(Shooting) -> [Shooting Mode] -> [Camera Set. Memory]` (`BKID_APP_setting_memory_recall`) | `(Shooting) -> [Shooting Mode] -> [Camera Set. Memory]` (`M1..M4`) | `(Setup) -> [Reset/Save Settings] -> [Save/Load Settings]` |
| **Mode Scope** | **Still `P/A/S/M` only** | **Still, Movie, & `S&Q`** | **Still, Movie, & `S&Q`** | Full camera profile (disabled while in `MR` mode) |
| **Recall Trigger** | Hold assigned Custom Key (temporary override; reverts on release) | `MODE` button (`MR1/MR2/MR3`) or `[Recall Camera Setting]` | `[Recall Camera Setting]` menu only (`M1..M4` not on `MODE` screen directly unless via menu) | `[Save/Load Settings] -> [Load]` (`Media` / `Cloud(Private/Share)`) |
| **Storage Target & Exact `appFw.so` Path** | Camera NVRAM | Camera internal NVRAM | `[Memory/Recall Media]` (`Slot 1` default / `Slot 2`): **`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`** | **Strictly `Slot 1`** (max `10`/card): **`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`** (`SD`: `/PRIVATE/SONY/SETTING/FX3/CAMSET/`; `CFexpress`: `/SONY/SETTING/FX3/CAMSET/`) |
| **`PRIVATE/SONY/PRO/CAMERA` Present?** | **No** | **No** | **No** (`FX6`-only path!) | **No** (`FX6`-only path!) |
| **Card `[Format]` Impact (`TP1000843993.html`)** | Unaffected | Unaffected | **Permanently erased** by quick/full `[Format]` on selected slot | **Permanently erased** by `[Format]` on `Slot 1` |
| **`[Camera Settings Reset]` Impact** | **Survives** (`Not available`) | **Survives** (`Not available`) | Card files intact, **but** `[Memory/Recall Media]` resets to **`Slot 1`** | Card files intact |
| **`[Initialize]` Impact** | **Wiped** | **Wiped** | Card files remain on card | Card files remain on card |
| **Exclusions** | Self-timer; `HLG Still` off during ISO/DRO-BKT hold | `Custom Key/Dial Set.`, `Program Shift` | `Custom Key/Dial Set.`, `Program Shift` | `Custom WB 1..3`, `FTP`, `Network Streaming`, `IP/Cert`, `Date/Time` |

- **Critical Empirical Finding on Card Path (`FX3 appFw.so` `0x3907faa..0x390801d` vs `FX6 appFw.so`)**:
  - `FX3 Ver. 7.02 appFw.so` contains **zero** occurrences of `PRIVATE/SONY/PRO/CAMERA`. Instead, both `[Save/Load Settings]` (`CAMSET`) and card-based `[Camera Set. Memory]` (`M1..M4`) live under **`%c:%s/SONY/SETTING/%s/`**: `CAMSET/%s.DAT` (`CAMSET01..10.DAT`, Slot-1 locked) and **`CAMPR%02d%c.DAT`** (`M1..M4`, governed by `[Memory/Recall Media]` `Slot 1` / `Slot 2`), where `%s` resolves to `/PRIVATE` on SD/SDHC/SDXC and `""` on CFexpress Type A.
  - By contrast, **`FX6 Ver. 6.01 appFw.so`** explicitly implements **`s/SONY/PRO/CAMERA/`** (`User File` & `All File`) and **`s/SONY/PRO/SCENE/`** (`Scene File`).

### 2.3 `ILME-FX6 Ver. 6.01` Contrast: `Scene File`, `User File`, `All File`, & `Cam ID`

- **`Paint/Look > Scene File`**: Stores/recalls look & color-matrix presets internally (`Store`/`Recall`/`Delete`) or to SD/Utility SD (`s/SONY/PRO/SCENE/`), alongside 4 SDR + 2 HDR presets and 16 User 3D LUT (`.cube`) slots (`BKID_APP_IS_EXIST_SCENE_FILE_{HDR,SDR}_SCN0..15`). Disabled in `Cine EI` mode.
- **`Project > User File` & `Project > All File`**: Saves/loads configuration data (up to `64` `All File` `.ALL` profiles) strictly via **Slot B** (`Save to Media(B)` / `Load from Media(B)`) under `s/SONY/PRO/CAMERA/` or Cloud (`Creators' App for Enterprise`), **forcing a camera reboot upon load** (`5-024-458-18`).
- **`Project > Rec > Clip > Cam ID + Reel#`**: Assigns cinema camera-unit ID + reel metadata (`FX6 string_english_2.uxc`: `Cam ID + Reel#`) rather than consumer shooting-mode memory banks (`1..3`/`M1..M4` and `Reg. Custom Shoot Set` are absent from `FX6`).

---

## 3. `[Playback]` `[Photo Capture]` (`8.3M` / `2.1M`) & `[Enlarge Image]` (`Enlarge Initial Mag.` / `Enlarge Initial Position`)

### 3.1 `[Photo Capture]` (`MENU -> Playback -> [Edit] -> [Photo Capture]`)

- **Menu Path & Sub-items**:
  - `MENU` -> `(Playback)` -> `[Edit]` -> **`[Photo Capture]`** (`BKID_APP_is_edit_photo_capture`, `enter_photo_capture_mode`, `_f.uxc` `0x6856`/`0x64a6`).
  - `MENU` -> `(Playback)` -> `[Edit]` -> **`[JPEG/HEIF Switch]`** (`BKID_APP_setting_photo_capture_file_type`, `_f.uxc` `0x6938`/`0x7175`).
- **Format & Resolution Matrix (`FX3 appFw.so` + `_f.uxc` + `TP1000876564.html` / `TP1000885434.html`)**:
  - **Output File Types (`VAL_setting_photo_capture_file_type_*`)**: **`JPEG`** (**Default**, `_f` `0x612f`), **`HEIF(4:2:0)`** (`10-bit`, `0x79f9`), **`HEIF(4:2:2)`** (`10-bit`, `0x796b`).
  - **Output Pixel Dimensions**: **`8.3M` (`3840×2160`)** from `4K` UHD movies (`_f.uxc` `0x6f54`/`0x78a6`) vs **`2.1M` (`1920×1080`)** from `HD` movies (`_f.uxc` `0x7b04`). Cancels any active `[Playback Filter Condition]` on capture.
- **Empirical Hardware & Slot Boundaries**:
  1. **`XAVC S-I DCI 4K` Lockout (`_g.uxc` `0x60ce`)**: Movies recorded in **`[XAVC S-I DCI 4K]` (`4096×2160`, `17:9`)** trigger `0x60ce` (*"Cannot perform this operation for movies recorded with their 'File Format' set to 'XAVC S-I DCI 4K'"*) — restricting frame grabs strictly to `16:9` `3840×2160` (`8.3M`) or `1920×1080` (`2.1M`) streams.
  2. **`Slot 1` Write Hazard**: Because both `[Rec. Media Settings]` and `[Select Playback Media]` default to **`Slot 1`** (`TP1000888852.html`), grabbing still frames from a movie stored on `Slot 1` writes new `DCIM` still files and mutates the playback database (`MDB`/`AVF_INFO`) on the live cinema media card itself (and fails if `Slot 1` is write-locked `base 0xe967` or full).
  3. **Reset Rule**: `(Playback)` settings are **excluded from `[Camera Settings Reset]`** (`TP1000888852.html`); resetting `[JPEG/HEIF Switch]` requires `[Initialize]`.

### 3.2 `[Enlarge Image]`, `[Enlarge Initial Mag.]`, & `[Enlarge Initial Position]`

- **Exact Sony `ilc/2210` Naming**: Official `ILME-FX3` menus and Help Guide spell these **`[Enlarge Initial Mag.]`** (`_f.uxc` `0x6b6e`, `BKID_APP_setting_magnif_set_in_large`) and **`[Enlarge Initial Position]`** (`_f.uxc` `0x781f`, `BKID_APP_setting_position_set_in_large`) — not abbreviated `Init.`.

| Setting (`MENU -> Playback -> [Magnification]`) | Options (`ilc/2210`) | Factory Default | `[Camera Settings Reset]` | `appFw.so` Key / Enum & Hardware Behavior |
| :--- | :--- | :---: | :---: | :--- |
| **`[Enlarge Image]`** *(Still-only action)* | Slide body `W/T` lever (`T` in / `W` out), touch pinch/double-tap, or Custom Key | — | — | `EVENT_FUNC_ENLARGE_IMAGE_{ON,OFF,REPEAT}`, `SINGLE_PLAYBACK_SCREEN_TYPE_ENLARGE`; **Still-image playback only** (disabled on movies); rotate front/rear dial to switch prev/next still keeping zoom scale; exit via `MENU` or wheel center |
| **`[Enlarge Initial Mag.]`** | **`Standard. Mag.`** (`_f` `0x674d`/`0x764f`) / **`Previous Mag.`** (`_f` `0x6546`/`0x7b2c`) | **`Standard. Mag.`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_magnif_set_in_large`: `MAGNIF_SET_IN_LARGE_ACTUAL` (default) vs `MAGNIF_SET_IN_LARGE_LAST` (retains last zoom factor even after closing zoom view) |
| **`[Enlarge Initial Position]`** | **`Focused Position`** (`_f` `0x602e`/`0x77b2`) / **`Center`** (`.uxc` `0xe1ce`) | **`Focused Position`** | **Not available** *(needs `[Initialize]`)* | `BKID_APP_setting_position_set_in_large`: `POSITION_SET_IN_LARGE_FROM_FOCUSED` (falls back to center if AF point metadata absent) vs `POSITION_SET_IN_LARGE_FROM_CENTER_OF_SCREEN` |

- **`ILME-FX6 Ver. 6.01` Contrast**: `FX6` has **zero** `[Photo Capture]` and **zero** playback `[Enlarge Image]` / `[Enlarge Initial Mag.]` / `[Enlarge Initial Position]` (`PHOTO_CAPTURE`, `MAGNIF_SET_IN_LARGE`, `POSITION_SET_IN_LARGE` in `FX6 appFw.so` are dormant unreferenced Alpha symbols; `FX6`'s `Enlarge Screen` in `string_english.uxc` refers strictly to live shooting focus magnification).

---

## 4. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 4.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 51 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_movie_rec_frame_rate_xavc_s_i_dci_4k`, `VAL_setting_movie_record_setting_xavc_s_i_dci_4k_{24_00p,24p,25p,30p,50p,60p}_*`, `VAL_setting_sq_frame_rate_xavc_s_i_dci_4k_*` (`1..48fps`), `VAL_setting_raw_output_frame_rate_RAW_OUTPUT_FRAME_RATE_24_00P`, `VAL_setting_shutter_angle_*`, `BKID_APP_setting_aspect_ratio` (`3_2`, `4_3`, `16_9`, `1_1`), `BKID_APP_shoot_set_registration_*_available{0..3}` (`11` keys matching `is_checked_recall_custom_hold0..10`), `BKID_APP_setting_memory_recall` (`1..3`, `M1..M4`), `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`, `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, `BKID_APP_setting_photo_capture_file_type` (`JPEG`/`HEIF_420`/`HEIF_422`), `BKID_APP_setting_magnif_set_in_large`, `BKID_APP_setting_position_set_in_large` |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` sequential `0x1e1c` records (`0x6000..0x7d3d`): `XAVC S-I DCI 4K` (`0x7336`, `0x61ce`), `XAVC HS 4K` (`0x76df`), `XAVC S 4K` (`0x690c`), `XAVC S-I 4K` (`0x70ba`), `24.00p` (`0x75ce`), `Shutter Mode` (`0x7c7c`), `RAW Output` (`0x6e97`), `Aspect Ratio` (`0x757c`), `Reg. Custom Shoot Set` (`0x7631`), `Recall Custom hold 1..3` (`0x60b4`/`0x7581`/`0x725b`), `Camera Set. Memory` (`0x75a6`), `Memory/Recall Media` (`0x763c`), `Photo Capture` (`0x6856`), `8.3M` (`0x6f54`/`0x78a6`), `2.1M` (`0x7b04`), `Enlarge Initial Mag.` (`0x6b6e`), `Enlarge Initial Position` (`0x781f`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` records: `Aspect Ratio` (`0xe680`), `3:2` (`0xe4f8`), `4:3` (`0xe14f`), `16:9` (`0xe475`), `1:1` (`0xe0d9`), `Enlarge Image` (`0xe8cb`), `Center` (`0xe1ce`), `SLOT 1`/`SLOT 2` (`0xe96e`/`0xe96d`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | Exact `2,692`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` records: `XAVC S-I DCI 4K` operation lockout (`0x60ce`), `24.00p` reboot & playback quarantine (`0x639b`, `0x63b6`, `0x63d7`), `Slot 1`/`Slot 2` (`0x608f`/`0x6090`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | Exact `1,390`-record `resid16` 1:1 parity with `EN` |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records at `0xc` and `0xd200c` (`819` subsystems, `0x018adbdb` & `0x09443bb1`) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_EXTERN_DCI_4K_REC_FRAME_RATE`, `BKID_APP_IS_EXIST_SCENE_FILE_{HDR,SDR}_SCN0..15`, `BKID_APP_USER_MENU_ALL_FILE0..7`, `BKID_APP_USER_MENU_USER_FILE0..4`, `s/SONY/PRO/CAMERA/`, `s/SONY/PRO/SCENE/`, zero FX3-style `Photo Capture` / `Camera Set. Memory` / `Reg. Custom Shoot Set` `BKID_APP_*` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `FF RAW 4096`, `FF RAW 3840`, `Scene File`, `User File: Load/Save Media(B)`, `All File: Load/Save Media(B)`, `Custom Aspect Ratio`, `Enlarge Screen` |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `XAVC 4096` (`60P/30P/24P/50P/25P`), `XAVC 3840`, `XAVC QFHD Class480/300`, `Cam ID + Reel#` |

### 4.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Domain / Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x7336` | `XAVC S-I DCI 4K` | `XAVC S-I DCI 4K` | `XAVC S-I DCI 4K` | `XAVC S-I DCI 4K` | Ver. 3.00+ internal `4096×2160` `17:9` All-Intra (`0x61ce`) |
| `_f` `0x70ba` | `XAVC S-I 4K` | `XAVC S-I 4K` | `XAVC S-I 4K` | `XAVC S-I 4K` | Internal `3840×2160` `16:9` All-Intra (`_f` `0x79d3`) |
| `_f` `0x76df` | `XAVC HS 4K` | `XAVC HS 4K` | `XAVC HS 4K` | `XAVC HS 4K` | Internal `3840×2160` HEVC Long-GOP |
| `_f` `0x690c` | `XAVC S 4K` | `XAVC S 4K` | `XAVC S 4K` | `XAVC S 4K` | Internal `3840×2160` H.264 Long-GOP |
| `_f` `0x75ce` | `24.00p` | `24.00p` | `24.00p` | `24.00p` | True cinema `24.00p` (`0x731d` 10bit; reboot `_g` `0x639b`) |
| `_f` `0x7c7c` | `Shutter Mode` | `快门模式` | `快門模式` | `シャッターモード` | `Speed` vs `Angle` (`Ver. 6.00+`) |
| `_f` `0x6e97` | `RAW Output` | `RAW输出` | `RAW輸出` | `RAW出力` | External HDMI `4264×2408` RAW output |
| `_f` `0x757c` | `\ue08cAspect Ratio` | `\ue08c纵横比` | `\ue08c長寬比` | `\ue08c横縦比` | Still aspect ratio (`0x691f`; `.uxc` `0xe680`) |
| `.uxc` `0xe4f8` | `3:2` | `3:2` | `3:2` | `3:2` | Default still aspect (`L: 12M` `_f` `0x6f85`) |
| `_f` `0x7826` | `4:3` | `4:3` | `4:3` | `4:3` | Still aspect (`L: 11M` `_f` `0x703f`, `.uxc` `0xe14f`) |
| `_f` `0x787d` | `16:9` | `16:9` | `16:9` | `16:9` | Still aspect (`L: 10M` `_f` `0x7040`, `.uxc` `0xe475`) |
| `.uxc` `0xe0d9` | `1:1` | `1:1` | `1:1` | `1:1` | Still aspect (`L: 8.0M` `_f` `0x7a2f`) |
| `_f` `0x7631` | `Reg. Custom Shoot Set` | `注册自定义拍摄设置` | `登錄自訂拍攝設定` | `ｶｽﾀﾑ撮影設定登録` | Still `P/A/S/M` temporary hold override |
| `_f` `0x60b4` | `Recall Custom hold 1` | `调出自定保持1` | `回復自訂固定1` | `押す間ｶｽﾀﾑ設定呼出1` | Hold slot 1 (`2`: `0x7581`, `3`: `0x725b`) |
| `_f` `0x7404` | `Import Current Setting` | `导入当前设置` | `匯入目前的設定` | `現在の設定を取り込む` | Imports active camera settings into hold bank (`Register`: `0x7ab8`) |
| `_f` `0x75a6` | `\ue5c1Camera Set. Memory` | `\ue5c1拍摄设置存储` | `\ue5c1拍攝設定記憶` | `\ue5c1撮影設定登録` | Body `1..3` + Card `M1..M4` memory banks |
| `_f` `0x7219` | `\ue5c1Recall Camera Setting` | `\ue5c1调出拍摄设置` | `\ue5c1回復拍攝設定` | `\ue5c1撮影設定呼び出し` | Recall `1..3` / `M1..M4` (`Recall Camera Set. 1` `0x7908`, `M1` `0x6238`) |
| `_f` `0x763c` | `\ue5c1Memory/Recall Media` | `\ue5c1选择媒体` | `\ue5c1記憶/回復插槽` | `\ue5c1登録/呼出ﾒﾃﾞｨｱ` | `M1..M4` card slot selector (`Slot 1` `_g` `0x608f` / `Slot 2` `0x6090`) |
| `_f` `0x6856` | `Photo Capture` | `照片捕获` | `照片攝取` | `動画から静止画作成` | Movie-frame still extraction (`8.3M` `0x6f54` / `2.1M` `0x7b04`) |
| `_f` `0x6938` | `\ue61cJPEG/HEIF Switch` | `\ue61cJPEG/HEIF切换` | `\ue61cJPEG/HEIF切換` | `\ue61cJPEG/HEIF切換` | Photo Capture `JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)` (`0x7175`) |
| `.uxc` `0xe8cb` | `\ueb0fEnlarge Image` | `\ueb0f放大` | `\ueb0f放大` | `\ueb0f拡大` | Still playback magnification (`0xe576`) |
| `_f` `0x6b6e` | `\ueb0fEnlarge Initial Mag.` | `\ueb0f放大初始放大倍率` | `\ueb0f放大初始放大率` | `\ueb0f拡大の初期倍率` | `Standard. Mag.` (`0x764f`) / `Previous Mag.` (`0x7b2c`) |
| `_f` `0x781f` | `\ueb0fEnlarge Initial Position` | `\ueb0f放大初始位置` | `\ueb0f放大初始位置` | `\ueb0f拡大の初期位置` | `Focused Position` (`0x77b2`) / `Center` (`.uxc` `0xe1ce`) |
| `_g` `0x60ce` | `Cannot perform this operation for movies recorded with their "\ue660File Format" set to "XAVC S-I DCI 4K".` | `无法对"\ue660文件格式"被设为"XAVC S-I DCI 4K"的动态影像执行此操作。` | `無法對"\ue660檔案格式"被設為"XAVC S-I DCI 4K"的影片執行此操作。` | `「\ue660記録方式」を「XAVC S-I DCI 4K」に設定して記録した動画では、この操作を実行できません` | `XAVC S-I DCI 4K` playback/edit lockout |
