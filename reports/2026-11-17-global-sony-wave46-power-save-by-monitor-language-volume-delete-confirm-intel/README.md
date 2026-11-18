# Global Sony Real-Hardware Intelligence — Wave 46 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: `[Power Save by Monitor]` Firmware Tokens vs `ilc/2210` `Power Setting Option`, `[Language]` `BK_LANG` `0x02cf019c` & `.uxc` 4-Language Parity, `[Volume Settings]` `0..15` / `[4ch Audio Monitoring]`, and `[Delete confirm.]` `Slot-1` Vault Guard)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Power Save Start Time*, *Auto Power OFF Temp.*, *Language*, *Volume Settings*, *4ch Audio Monitoring (movie)*, *Delete confirm.*, *Delete pressing twice*, *Setting Reset*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0), sibling `helpguide.sony.net` vari-angle `BIONZ XR` references (`ILME-FX2`, `ILCE-7M4`, `ILCE-6700`, `ZV-E1`), and strictly `O_RDONLY` local donor binary/table cross-checks (`appFw.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `CX95898_NTSC.bin`, `CX95899_CN1.bin`, and `.uxc` localization packs)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Power Save by Monitor]` (`appFw.so` / Sibling `BIONZ XR` Bodies vs `ILME-FX3 Ver. 7.02` `Power Setting Option`) & `[Power Save Start Time]` Interaction

1. **Critical Reality Split (`ilc/2210` Help Guide vs Shared `FX3 Ver. 7.02` `appFw.so` / `string_*_f.uxc`)**:
   - **Official `ILME-FX3` (`helpguide.sony.net/ilc/2210/v1/en/`) Menu Scope**: Under `MENU` -> `(Setup)` -> **`[Power Setting Option]`**, `ILME-FX3` (Ver. 2.00 through Ver. 7.02) exposes **only two items**:
     - **`[Power Save Start Time]`**: `Off` / `30 Min` / **`5 Min` (factory default)** / `2 Min` / `1 Min` / `10 Sec`.
     - **`[Auto Power OFF Temp.]`**: **`Standard` (factory default)** / `High`.
     - `[Power Save by Monitor]` is **NOT exposed** in the `ILME-FX3` (or `ILME-FX3A` / `ILME-FX6`) user menu or `ilc/2210` Help Guide—folding the FX3 vari-angle LCD inward does not trigger a user-configurable monitor-sleep setting on stock `ILME-FX3 Ver. 7.02`.
   - **Compiled `BIONZ XR` Firmware Tokens (`O_RDONLY` `appFw.so` + `string_*_f.uxc`)**: Because Sony compiles `appFw.so` (`79,015,712 B`) and `string_*_f.uxc` (`373,820 B` EN) across multiple `CXD90057` / `BIONZ XR` bodies (`PRODUCT_MODEL_ALCIN_UUD`, `PRODUCT_MODEL_LS`, `PRODUCT_MODEL_LAX`, etc.), the full monitor power-linkage subsystem **is present in the binary**:
     - `appFw.so` symbols: `BKID_APP_setting_monitor_power_linkage`, `BKID_APP_MENU_MONITOR_POWER_LINKAGE`, `BKID_APP_setting_power_off_w_monitor`, `EXTERN_VAL_MONITOR_POWER_LINKAGE_{ON_ALL, ON_OPEN, ON_CLOSE, OFF}`, plus power-switch variants `MONITOR_POWER_LINKAGE_FOR_{SLIDE_POWER_SWITCH, TACT_POWER_KEY}_{ON_ALL, ON_OPEN, ON_CLOSE, OFF}`.
     - Exact **4** UI option strings verified in `string_english_f.uxc` (and matched 1:1 by `resid16` across `ZH-CN`, `ZH-TW`, `JA`):

| `resid16` | EN (`string_english_f.uxc`) | ZH-CN (`string_simplifiedchinese_f.uxc`) | ZH-TW (`string_traditionalchinese_f.uxc`) | JA (`string_japanese_f.uxc`) | `appFw.so` Enum / Behavior |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `0x60b9` | `Power Save by Monitor` | `通过显示屏节电` | `依據螢幕狀態省電` | `ﾓﾆﾀｰ開閉でﾊﾟﾜｰｾｰﾌﾞ` | Menu Title (`Setup -> Power Setting Option`) |
| `0x6db5` | `Both Linked` | `二者均连接` | `兩者都已連結` | `両方連動` | `ON_ALL` (**Factory default** on `ILME-FX2` / `ILCE-7M4` / `ZV-E1` / `ILCE-6700`) — wakes on open, sleeps on inward close |
| `0x6db6` | `Open: Return` | `打开: 恢复` | `打開: 返回` | `開:ﾊﾟﾜｰｾｰﾌﾞ復帰` | `ON_OPEN` — wakes on open; does **not** sleep when closed inward *(note: `"Open: On/Close: Off"` is absent from both `helpguide.sony.net` and `string_english_f.uxc`)* |
| `0x60a8` | `Close: Power Save` | `关闭: 节电` | `闔上: 省電` | `閉:ﾊﾟﾜｰｾｰﾌﾞ` | `ON_CLOSE` — enters power save when closed facing inward |
| `0x6b2e` | `Does Not Link` | `不连接` | `不連結` | `連動しない` | `OFF` — disables monitor open/close power-save linkage completely |

2. **Cinema Rig / Headless Bench Posture, `[Power Save Start Time]` Interaction & Reset Survival**:
   - **Headless / External HDMI Bench Rule**: On `BIONZ XR` bodies exposing `[Power Save by Monitor]` (`ILME-FX2`, `ILCE-7M4`, `ZV-E1`), **`[Does Not Link]`** (or `[Open: Return]`) is mandatory when folding the LCD inward during external HDMI/recorder capture or `Monitor & Control` operation so the camera never enters sleep on monitor close. (Note Sony's documented `ILCE-7M4 Ver. 6.00` regression where closing the LCD forced sleep regardless of `[Power Save by Monitor]` until `[Initialize]` / `Ver. 6.01`.)
   - **Interaction with `[Power Save Start Time]` on `ILME-FX3 Ver. 7.02`**: `BKID_APP_setting_start_power_saving` (`VAL_setting_start_power_saving_START_POWER_SAVING_{OFF, 10SEC, 1MIN, 2MIN, 5MIN, 30MIN}`) governs idle sleep (`5 Min` default) and is automatically bypassed by Sony's **9 deactivation conditions** (`USB power supply`, `slideshow playback`, `FTP transfer`, `movie recording`, `PC connection`, `TV/HDMI connection`, `[IR Remote Ctrl] = On`, `[Bluetooth Rmt Ctrl] = On`, `streaming / Creators' Cloud upload`). For air-gapped battery bench runs without HDMI/USB, `[Power Save Start Time]` must be `[Off]` or `[30 Min]`.
   - **Reset Survival**: Because `[Power Setting Option]` resides under `(Setup)`, both `[Power Save by Monitor]` (where exposed) and `[Power Save Start Time]` **survive `[Camera Settings Reset]`** and are restored to factory defaults **only by `[Initialize]`**.

---

## 2. `[Language]` (`MENU -> Setup -> [Area/Date] -> [Language]`, `BK_LANG` `0x02cf019c` & `.uxc` 4-Language Parity)

1. **Official `ILME-FX3` (`ilc/2210`) Behavior & Reset Persistence**:
   - **Menu Path**: `MENU` -> `(Setup)` -> `[Area/Date]` -> **`[Language]`** (default setting value in Sony's *List of default setting values*: `―`, prompted at initial out-of-box setup).
   - **Reset Boundary**: Resides under `(Setup)` -> **`[Language]` survives BOTH `[Camera Settings Reset]` and `[Reset Network Set.]`**, and is cleared/re-prompted **only by `[Initialize]`** (via `libSaveLoadSettings.so` `Backup_write` / `SaveLoadSettings::requestToWrite`, `18,760 B`, SHA-256 `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7`).
   - **Model Count Divergence (`FX3` `34` vs `FX6` `29`)**: `O_RDONLY` inspection of `FX3 appFw.so` confirms `34` `VAL_setting_language_LANGUAGE_*` enums paired 1:1 with `34` `string_<lang>_f.uxc` packs (`BKID_APP_setting_language`, `resid16=0xe397` `\ue802Language` in `string_*.uxc`), whereas `ILME-FX6 Ver. 6.01` (`Maintenance > Language` / `Language Select`, `BKID_APP_SETTING_LANGUAGE`) carries `29` `string_<lang>.uxc` (`ns=1`, `5,063` slots / `5,044` strings) + `29` `string_<lang>_2.uxc` (`ns=2`, `5,921` slots / `5,915` strings) packs.

2. **`BK4\x00` Seed Cross-Check (`0x02cf019c`) & Stage-B 4-Language Parity Matrix**:
   - **`FX3-CX95900_ALLLANG-Backup.bin`** (`2,229,740 B`, SHA-256 `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2`, dual `BK4\x00` records, `819` subsystems, `35,668` / `31,197` properties, checksums `25,877,467` / `155,466,673` PASS): `0x02cf019c` (`BK_LANG`) sits at file offset `0x90ff0` (`4 B`, value `0` = `LANGUAGE_ENGLISH` out-of-box `ALLLANG` seed).
   - **`FX6` `CX95898_NTSC.bin` vs Regional Seeds** (`2,253,333 B`, dual `BK4\x00` records, `840` subsystems, `40,647` / `35,088` properties, checksums PASS): `0x02cf019c` sits at file offset `0x89242` (`1 B`), verified `0x00` (`English`) in `CX95898_NTSC.bin` (SHA-256 `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e`), `CX95898_UC.bin`, `CX95899_CEE.bin`, and `CX95898_J.bin`, and **`0x19` (`25` = `LANGUAGE_CHINESE_SIMPLIFIED`)** in `CX95899_CN1.bin` (`0c98d1ad...`).

| Stage-B Language | `BK4 0x02cf019c` | `AppFw` Enum | `switchBank` (`Font`, `Str`) | `.ltt` Font Container | FX3 `string_<lang>_f.uxc` Size (`B`) | FX3 `string_<lang>.uxc` Size (`B`) | FX6 `string_<lang>.uxc` Size (`B`) |
| :--- | :---: | :--- | :---: | :--- | ---: | ---: | ---: |
| `en` (`english`) | `0x00` | `0x2b2f_LANGUAGE_ENGLISH` | `0`, `(4, 4)` | `UniversOTS-SJ_wIcon.ltt` | `373,820` | `165,740` | `118,208` |
| `schinese` (`simplifiedchinese`) | `0x19` | `0x2b45_CHINESE_SIMPLIFIED` | `23`, `(19, 19)` | `MYingHeiC-GB18030-SJ_wIcon.ltt` | `322,652` | `149,064` | `118,644` |
| `tchinese` (`traditionalchinese`) | `0x18` | `0x2b44_LANGUAGE_CHINESE_TRADITIONAL` | `27`, `(22, 22)` | `MYingHeiC-Big5HKSCS-SJ_wIcon.ltt` | `324,148` | `151,908` | `119,168` |
| `japanese` (`japanese`) | `0x01` | `0x2b30_LANGUAGE_JAPANESE` | `1`, `(12, 12)` | `HeiseiKakuGothW5-SJ_wIcon.ltt` | `447,840` | `208,564` | `141,692` |

---

## 3. `[Volume Settings]` (`0..15`, Default `7`), `[4ch Audio Monitoring]`, and `[Delete confirm.]` (`Slot-1` Vault Firewall)

1. **`[Volume Settings]` (`MENU -> Setup -> [Sound Option] -> [Volume Settings]`)**:
   - **Range & Default**: Official `ilc/2210` *List of default setting values* pins factory default **`[7]`**, while `O_RDONLY` inspection of `FX3 appFw.so` (`BKID_APP_setting_volume_settings`) confirms the exact `16`-level discrete enum **`VOLUME_SETTINGS_0` .. `VOLUME_SETTINGS_15`** (`0..15`). Localized across all 4 languages in `FX3 string_<lang>.uxc` (`resid16=0xe8c9`: `Volume Settings` / `音量设置` / `音量設定` / `音量設定`), distinct from `[Audio signals]` (`BKID_APP_setting_audio_signals`, `Audio Signal Volume` `0x7af6`, `On` default / `On: Shutter Only` / `Off`).
   - **Internal Speaker vs Headphone Behavior & FX6 Parity**: `[Volume Settings]` sets **movie playback sound volume** (also adjustable live via the movie playback operation panel by pressing Down on the control wheel). `ILME-FX3` routes playback audio to the rear monaural internal speaker or the side `3.5 mm` stereo headphone terminal; Sony explicitly warns to lower speaker volume or distance the `XLR-H1` microphone from the speaker to avoid acoustic feedback. Because `[Volume Settings]` resides under `(Setup)`, it **survives `[Camera Settings Reset]`** (restored to `7` only by `[Initialize]`). On `ILME-FX6 Ver. 6.01`, the equivalent controls are `Audio > Audio Output > Volume` (`BKID_APP_SETTING_MONITOR_VOLUME`) and `Monitor CH`.

2. **`[4ch Audio Monitoring]` (`MENU -> Setup -> [Sound Option] -> [4ch Audio Monitoring]`)**:
   - Active during 4-channel movie recording (via MI-Shoe `XLR-H1` handle unit or compatible 4ch MI-Shoe accessory) and 4-channel movie playback. `ilc/2210`, `FX3 appFw.so` (`BKID_APP_setting_audio_monitoring_ch`), and `string_*_f.uxc` verify all **5** monitoring routes:
     - **`[CH1/CH2]`** (`AUDIO_MONITORING_CH_1CH_2CH`, `resid16=0x713b`, **factory default**): `CH1 -> L`, `CH2 -> R`.
     - **`[CH3/CH4]`** (`AUDIO_MONITORING_CH_3CH_4CH`, `resid16=0x6bf6`): `CH3 -> L`, `CH4 -> R`.
     - **`[CH1+3/CH2+4]`** (`AUDIO_MONITORING_CH_MIX_ALL`, `resid16=0x6c2e`): `CH1+CH3 -> L`, `CH2+CH4 -> R`.
     - **`[CH1/CH1]`** (`AUDIO_MONITORING_CH_1CH`, `resid16=0x6f9c`): `CH1 -> L+R`.
     - **`[CH2/CH2]`** (`AUDIO_MONITORING_CH_2CH`, `resid16=0x7a26`): `CH2 -> L+R`.
   - **Hardware Boundaries**: The `3.5 mm` headphone terminal cannot output 4 discrete channels simultaneously (`2ch` stereo only), and `[4ch Audio Monitoring]` also governs which channels play through the camera's internal speaker. Distinct from HDMI `[4ch Audio Output]` (`BKID_APP_setting_4ch_output_ch`: `CH1/CH2` vs `CH3/CH4`, `resid16=0x6aa0`). Survives `[Camera Settings Reset]` under `(Setup)`.

3. **`[Delete confirm.]` (`MENU -> Playback -> [Delete] -> [Delete confirm.]`), `[Delete pressing twice]` & `Slot-1` Recovery Vault Firewall**:
   - **Exact Modes & `O_RDONLY` Parity**: Verified across `ilc/2210`, `FX3 appFw.so` (`BKID_APP_setting_delete_confirm`), `FX3 string_<lang>.uxc` (`ns=39`), and `string_<lang>_f.uxc`:
     - **`["Cancel" first]`** (`VAL_setting_delete_confirm_DELETE_CONFIRM_CANCEL_FIRST`, `resid16=0xe724` / `0x6a5e`: `默认为"取消"` / `"取消"優先` / `「キャンセル」が先`) — **factory default** (critical anti-fat-finger guard pre-focusing `[Cancel]` on the confirmation dialog).
     - **`["Delete" first]`** (`VAL_setting_delete_confirm_DELETE_CONFIRM_DELETE_FIRST`, `resid16=0xe725` / `0x6e0a`: `默认为"删除"` / `"刪除"優先` / `「削除」が先`).
   - **Companion Guard & Reset Persistence**: `[Delete pressing twice]` (`BKID_APP_setting_delete_by_delete_twice`, `resid16=0x74db`) defaults to **`[Off]`**. Both items reside under `(Playback)` -> **survive `[Camera Settings Reset]`** and reset to defaults **only via `[Initialize]`**.
   - **Hard `Slot-1` Vault Rule (`slot1_vault_delete_events == 0`)**: On all bench, emulator, and recovery workflows, any `[Delete]` (single, multiple, folder, date, or `Delete pressing twice`) or `[Format]` command targeting **`Slot 1`** is **hard-blocked** whenever `Slot 1` holds the read-only `CAMSET`/`BODYDATA.DAT` recovery vault (`slot1_vault_delete_events == 0`, `slot1_format_hard_locked == True`, `persistent_emmc_writes_authorized == False`).

---

## 4. `O_RDONLY` Local Donor Audit Ledger (Zero Raw Bytes Leaked)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 46 Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3` `string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `Power Save by Monitor` (`0x60b9`), `Both Linked` (`0x6db5`), `Open: Return` (`0x6db6`), `Close: Power Save` (`0x60a8`), `Does Not Link` (`0x6b2e`), `4ch Audio Monitoring`, `CH1+3/CH2+4` (`0x6c2e`), `"Cancel" first` (`0x6a5e`), `"Delete" first` (`0x6e0a`), `Delete pressing twice` (`0x74db`) |
| `FX3` `string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `\ue802Language` (`0xe397`), `Volume Settings` (`0xe8c9`), `Delete confirm.` (`0xe721`), `"Cancel" first` (`0xe724`), `"Delete" first` (`0xe725`) — 1:1 slot parity across `EN`/`ZH-CN`/`ZH-TW`/`JA` |
| `FX3` `appFw.so` (`Ver. 7.02`) | `79,015,712` | — | `BKID_APP_setting_monitor_power_linkage`, `MONITOR_POWER_LINKAGE_*`, `BKID_APP_setting_start_power_saving`, `BKID_APP_setting_language` (`34` enums), `BKID_APP_setting_volume_settings` (`VOLUME_SETTINGS_0..15`), `BKID_APP_setting_audio_monitoring_ch`, `BKID_APP_setting_4ch_output_ch`, `BKID_APP_setting_delete_confirm`, `BKID_APP_setting_delete_by_delete_twice` |
| `FX3` `libSaveLoadSettings.so` | `18,760` | `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7` | `Backup_get_datasize`, `Backup_read`, `Backup_write`, `SaveLoadSettings::requestTo{Read,Check,Write}` |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` records (`819` subsystems, checksums PASS); `0x02cf019c` (`BK_LANG`) = `0` (`4 B` @ `0x90ff0`) |
| `FX6` `CX95898_NTSC.bin` vs `CX95899_CN1.bin` | `2,253,333` | `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e` | Dual `BK4\x00` records (`840` subsystems, checksums PASS); `0x02cf019c` = `0x00` (`NTSC`/`UC`/`CEE`/`J`) vs `0x19` (`CN1`) @ `0x89242` (`1 B`) |
| `FX6` `string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Language Select` (`0x2f4d`), `Monitor CH`, `Delete Clip?` (`29`-language Stage-B parity) |
