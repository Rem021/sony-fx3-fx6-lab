# Global Sony Real-Hardware Intelligence — Wave 47 (`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`: `[USB Connection Mode]` 4-Mode & `Sel. When Connect` vs `[USB Streaming]`, `[HDMI Info. Display]` Clean-Feed Downscale vs OSD, `[Protect]` Playback Lock vs `[Format]` Override, and `[Reset Network Set.]` Exact Boundary)

- **Date**: `2026-11-17`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`) vs `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *USB Connection Mode*, *USB LUN Setting*, *USB Power Supply*, *Network Streaming (movie)*, *HDMI Info. Display*, *HDMI Output Settings (movie)*, *HDMI Resolution*, *Protecting recorded images*, *Format*, *Reset Network Set.*, *Camera Settings Reset*, *Initialize*, *List of default setting values*), Sony `ILME-FX6` Operating Instructions (`5-024-458-18`, Software Ver. 6.0) & Monitor & Control Help Guide, and strictly `os.O_RDONLY` local donor binary/string-pack cross-checks (`FX3 appFw.so`, `FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`, `FX3 usb_f_uvc.ko`, `FX3-CX95900_ALLLANG-Backup.bin`, `FX6 appFw.so`, `FX6 string_*.uxc` / `_2.uxc`, `FX6 usb_f_uvc.ko`)
- **Hardware Safety Posture**: Strictly `os.O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[USB Connection Mode]` (`MENU -> Setup -> [USB] -> [USB Connection Mode]`) & `[USB LUN Setting]` / `[USB Power Supply]` Interaction (`Ver. 2.00+` / `Ver. 7.02`)

1. **Exact 4 Modes Exposed on `ILME-FX3 Ver. 7.02` (`ilc/2210` + `appFw.so` + `string_*_f.uxc`)**:
   - Under `MENU` -> `(Setup)` -> `[USB]` -> **`[USB Connection Mode]`** (`BKID_APP_setting_usb_connection_method`, `resid16=0x69a2`), `ILME-FX3` (`Ver. 2.00` through `Ver. 7.02`) exposes **exactly 4 modes** (with `Sel. When Connect` pinned as **factory default** in Sony's *List of default setting values*):
     1. **`[Sel. When Connect]`** (**factory default**, `VAL_setting_usb_connection_method_USB_CONNECTION_SELECT_AFTER_CONNECTION`, `_f.uxc` `0x7738`): Each time a USB cable is connected, prompts the operator to select `[Image Transfer (MSC)]` (`0x67a2`), `[Image Transfer (MTP)]` (`0x72cd`), or `[Remote Shooting]` (`0x7c6f`).
     2. **`[MassStorage(MSC)]`** (`VAL_setting_usb_connection_method_USB_CONNECTION_MASS_STORAGE`, `_f.uxc` `0x6c54` / `0x7812`, `.uxc` `0xe7d4`, USB VID:PID `054C:0DA1`, `usbg_storage.ko`): Exposes memory card volumes (`DCIM`, `CLIP`, `SUB`, `M4ROOT`) as removable USB disk(s). *(Note: `appFw.so` preserves Sony's internal marker spelling `USB_CONNECTION_METHOD_MASS_STRAGE`.)*
     3. **`[MTP]`** (`VAL_setting_usb_connection_method_USB_CONNECTION_MTP`, `.uxc` `0xe24b`, `usbg_stillimage.ko`): Enumerates as an MTP media device targeting **memory card Slot 1**.
     4. **`[Remote Shooting]`** / **`[Remote Shoot (PC Remote)]`** (`VAL_setting_usb_connection_method_USB_CONNECTION_REMOTE_PC`, `_f.uxc` `0x7c6f` / `0x60aa`): Connects to *Imaging Edge Desktop (Remote)* on a host PC or *Creators' App* on a smartphone over USB (`Remote Shoot Setting` controls `Still Img. Save Dest.` and `Save Image Size`).
   - **Critical `NOUVC` Split — Dormant `[USB Streaming]` (`UVC`/`UAC`) Tokens vs `ILME-FX3` Reality**:
     - `helpguide.sony.net/ilc/2210/v1/en/` **does NOT include `[USB Streaming]`** under `[USB Connection Mode]` or `(Network) -> [Streaming]` (which exposes only `[Network Streaming]` over `RTMP`/`RTMPS`/`SRT` from `Ver. 6.00+`). Native UVC/UAC webcam streaming on `ILME-FX3` is absent (`NOUVC`), requiring *Imaging Edge Webcam* or an external HDMI-to-UVC capture adapter.
     - Yet `O_RDONLY` inspection of `FX3 Ver. 7.02` confirms the shared `BIONZ XR` firmware (`appFw.so` `79,015,712 B`, `string_*_f.uxc`, `string_*_g.uxc`, and `full-v4/regular-files/usr/kmod/`) carries the dormant compiled UVC assets for sibling bodies (`ILME-FX30`, `ILME-FX2`, `ILCE-7M4`, `ZV-E1`): `VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING`, `BKID_APP_shoot_mode_exclusion_for_usb_streaming`, `CAUTION_ID_FACTOR_MOVIE_RECORDING_{DISABLE,ENABLE}_MSG_USB_STREAMING`, `_f.uxc` `0x7399` (`\ue660USB Streaming`), `_g.uxc` `0x63f7` (`USB Streaming`), and `usb_f_uvc.ko` (`78,840 B`) / `usb_f_uac2.ko` / `g_webcam.ko`. On `ILME-FX3`, boot scripts do not `insmod` `g_webcam.ko`/`usb_f_uvc.ko` and the UI masks `USB Streaming` so `MSC (054C:0DA1)` / `MTP` / `Remote Shooting` remain intact. By contrast, `ILME-FX6 Ver. 6.01` exposes `Network > USB Tethering` (USB-C only, no hub) and ProCam UVC (`BKID_APP_SETTING_USB_STREAMING_PROCAM`, `usb_f_uvc.ko` `78,840 B`).

2. **`[USB LUN Setting]`, `[USB Power Supply]`, Reset Survival & Air-Gapped Tier-0 Rule**:
   - **`[USB LUN Setting]` (`MENU -> Setup -> [USB] -> [USB LUN Setting]`)**: `BKID_APP_setting_lun_settings` (`_f.uxc` `0x6b19`), values **`[Multi]` (factory default, `LUN_SETTING_MULTI`, `0x679d`/`0xe631`)** vs `[Single]` (`LUN_SETTING_SINGLE`, `_f.uxc` `0x69be`/`0x776d`). Limits LUN exposure in `MassStorage(MSC)` (`Single` is fallback-only when a host fails to mount `Multi`).
   - **`[USB Power Supply]` (`MENU -> Setup -> [USB] -> [USB Power Supply]`)**: `BKID_APP_setting_usb_supply` (`USB_SUPPLY_ON` / `USB_SUPPLY_OFF`, `_f.uxc` `0x721e`), **`[On]` (factory default)**. Requires an NP-FZ100 battery pack inserted and operates **exclusively through the USB Type-C port** (never Multi/Micro USB); `appFw.so` tracks `UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_{HIGH, LOW, UNKNOWN}` and `VAL_supplying_usb_power_state_SUPPLYING_USB_POWER_STATE_{ON, OFF}`.
   - **Reset Survival**: All `(Setup) -> [USB]` items (`[USB Connection Mode]`, `[USB LUN Setting]`, `[USB Power Supply]`) **survive `[Camera Settings Reset]`** and revert to defaults (`Sel. When Connect`, `Multi`, `On`) **only upon `[Initialize]`**.
   - **Air-Gapped Tier-0 Bench Rule**: Tier-0 offline benches **prohibit** `MassStorage(MSC)` (`054C:0DA1`), `MTP`, `Remote Shooting`, and `USB-LAN` host data enumeration to prevent host OS filesystem mounts, MTP locks, or unintended host control. Dumb `USB PD` power (`[USB Power Supply] = [On]` or `DC-C1` coupler) is permitted **only when USB data lines (`D+`/`D-` and SuperSpeed `TX/RX`) are physically isolated** (power-only PD brick / data-blocked cable).

---

## 2. `[HDMI Info. Display]` (`MENU -> Setup -> [External Output] -> [HDMI Info. Display]`)

1. **Factory Default, OSD/LCD Split & Letterbox Mirroring (`ilc/2210` + `appFw.so`)**:
   - **Menu Path**: `MENU` -> `(Setup)` -> `[External Output]` -> **`[HDMI Info. Display]`** (`BKID_APP_setting_hdmi_info_display`, `VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_{ON,OFF}`, `_f.uxc` `0x6e7c`).
   - **Options & Factory Default**:
     - **`[On]`** (**factory default** in Sony's *List of default setting values*): Outputs the image **plus** camera shooting info OSD overlays (including the `[Emphasized REC Display]` red tally border) to the external HDMI monitor/TV, while **blanking the FX3's built-in LCD monitor** (`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`, disabling LCD touch-focus). Because the OSD overlays mirror the camera's UI layout, the live image is framed inside a smaller inset/letterboxed viewport with black borders rather than a full-raster clean feed.
     - **`[Off]`**: Outputs a **clean feed** (recorded video/image only, zero OSD overlays) over HDMI while keeping both the live image and shooting info active on the built-in LCD (`_f.uxc` `0x755d`).

2. **Resolution / `1080p` Clamp, `[Rec. Media dur HDMI Output]` & `[RAW Output]` Interaction**:
   - **Internal Recording + `Log Shooting` / `PPLUT1..4` `1080` Clamp**: Under `[HDMI Output Settings]` (`BKID_APP_setting_rec_media_during_hdmi_output`), when `[Rec. Media dur HDMI Output] = [On]` (**default**) and `[RAW Output] = [Off]` (**default**), `[Output Resolution]` exposes `Auto` (**default**), `2160p`, `1080p`, `1080i` (`BKID_APP_setting_hdmi_resolution`). However, `ilc/2210` explicitly documents that **regardless of `[Output Resolution]`**, HDMI output drops to **`1080`** whenever `[Log Shooting]` != `[Off]` or `[Picture Profile]` is `PPLUT1..PPLUT4` while recording internally.
   - **Clean `4K` / `RAW` Forced-Off Override**: When `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` (`_f.uxc` `0x6573`, using `4K Output Set.(HDMI Only)` `59.94p/50p/29.97p/25p/23.98p/24.00p 10bit`, `BKID_APP_setting_hdmi_4k_output_setting`) OR when **`[RAW Output] = [On]`** (`_f.uxc` `0x6e97`, `16-bit` linear `4K`), the camera outputs **`4K`** and **automatically/temporarily forces `[HDMI Info. Display] = [Off]`** (guaranteed clean feed; note `S&Q` mode locks `Rec. Media = On` and `RAW Output = Off`).
   - **FX6 Parity & `(Setup)` Reset Survival**: `ILME-FX6 Ver. 6.01` separates `Monitoring > Output Display > HDMI` (`On`/`Off`, `BKID_APP_SETTING_HDMI_INFO_DISPLAY`) from `SDI` (`BKID_APP_SETTING_SDI_OUTPUT_DISPLAY`, `SDI Out2/HDMI Super` `0x4eea`). On `ILME-FX3`, `[HDMI Info. Display]` and `[HDMI Output Settings]` reside under `(Setup)` -> **survive `[Camera Settings Reset]`** and reset to factory defaults (`On`, `Auto`, `On`, `Off`) **only via `[Initialize]`**. *(Exception: `[Framing Settings (HDMI)] = Crop` is explicitly marked resettable by `[Camera Settings Reset]` in `ilc/2210`.)*

---

## 3. `[Protect]` (`MENU -> Playback -> [Selection/Memo] -> [Protect]`) vs `[Delete]` and `[Format]`

1. **Exact `ILME-FX3` Scopes, Key Mark & `[Delete]` Interlock (`ilc/2210` + `appFw.so`)**:
   - **Menu Path**: `MENU` -> `(Playback)` -> `[Selection/Memo]` (`_g.uxc` `0x6239`) -> **`[Protect]`** (`.uxc` `0xe2c9`).
   - **Verified Scopes (`ilc/2210` + `FUNC_protect_*` + `.uxc`/`_f.uxc`)**:
     - **Single Image / `Multiple Img.`** (`FUNC_protect_content`, `FUNC_protect_for_multipul_images`, `.uxc` `0xe2ca`): Select image(s) with center button check mark, then `MENU -> [OK]` (or assign `Protect` to a custom key; note `.uxc` `0xe34b` specifies movie files require menu Protect).
     - **`All in this Folder`** / **`Cancel All in this Folder`** (`_f.uxc` `0x6848` / `0x72d9`).
     - **`All with this date`** / **`Cancel All with this date`** (`FUNC_protect_all_contents_in_this_date`, `_f.uxc` `0x69f7` / `0x7339`).
     - **`All Images in This Group`** / **`Cancel All in This Group`** (`FUNC_protect_all_contents_in_this_group`, `.uxc` `0xe826` / `0xe553`).
   - **Indicator & `[Delete]` Behavior**: Protected items display the **key/protect icon** (`.uxc` `0xe306` `Image protected.`, `0xe66a` `File protected.`, `VAL_mr_memory_error_status_MR_MEMORY_ERROR_FILE_PROTECT`) and are skipped/blocked by `[Delete]` (`FUNC_delete_*`) and `[Delete pressing twice]` (`BKID_APP_setting_delete_by_delete_twice`). Copying a protected file to another card strips protection on the destination copy. (Also integrates with `[Image Jump Setting] = [Protect Only]` `0x72d1` and FTP `[Target Img (Protect)]` `0x694a`.)

2. **Why `[Protect]` Does NOT Prevent `[Format]` (`Slot 1` Vault Firewall Mandate)**:
   - **`[Format]` Overrides `[Protect]`**: Under `MENU -> (Shooting) -> [Media] -> [Format]` (`.uxc` `0xe449`, supporting Quick Format `0xe792` and Full Format `0xe8f5` toggled via the `Delete` button `0x6148`/`0x6255`), `ilc/2210` explicitly warns that **formatting permanently erases ALL data on the card, INCLUDING protected images and `M1..M4` registered settings** (`.uxc` `0xe414`: *"All data will be deleted. Format?"*).
   - **FX6 Ver. 6.01 Parity**: `ILME-FX6` exposes `Thumbnail > Lock/Unlock Clip` (`Select Clip`, `Lock All Clips` `0x413c`, `Unlock All Clips` `0x413e`, `BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP0..2`), which protects clips from `Delete Clip` yet is likewise wiped by `Format Media` (`0x4254`).
   - **Mandatory `Slot 1` Dual-Layer Defense**: Because software `[Protect]` is strictly file-attribute/delete-level and cannot block `[Format]`, `Slot 1` recovery media (`CAMSET`/`BODYDATA.DAT` vault) **must never rely on `[Protect]` alone**. It requires **(a) physical hardware SD Write-Protect (`WP`) lock** (`VAL_mr_memory_error_status_MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`, `CAUTION_ID_PROTECT_MS_SLOT1`) and **(b) our lab's hard `[Format]`/`[Delete]` firewall** (`slot1_format_hard_locked == True`, `slot1_vault_write_firewall_enforced == True`, `slot1_vault_delete_events == 0`).

---

## 4. `[Reset Network Set.]` (`MENU -> Network -> [Network Option] -> [Reset Network Set.]`) Exact Reset Scope vs `[Camera Settings Reset]` & `[Initialize]`

1. **Exact Firmware Mechanics & Automatic Reboot (`appFw.so` + `_f.uxc` `0x65d3`)**:
   - **Menu Path**: `MENU` -> `(Network)` -> `[Network Option]` (`_g.uxc` `0x61e1`) -> **`[Reset Network Set.]`** (`_f.uxc` `0x60d3` / `0x71b8`) -> `[Enter]`.
   - **Verified Firmware Sequence & Auto-Reboot**: `O_RDONLY` inspection of `FX3 appFw.so` confirms `FUNC_reset_network_settings`, `SETTING_RESET_NW`, `N5model37sequence_bluetooth_network_reset_doneE`, and **`BKID_APP_is_shutdown_factor_network_reset`**, matching `_f.uxc` `0x65d3` verbatim: *"Reset all network settings? (After initialization, reboots automatically.)"*. Executing `[Reset Network Set.]` always forces an automatic camera reboot.

2. **3-Way Reset Boundary (`[Reset Network Set.]` vs `[Camera Settings Reset]` vs `[Initialize]`)**:

| Menu Domain / Asset | `[Reset Network Set.]` (`SETTING_RESET_NW`) | `[Camera Settings Reset]` (`SETTING_RESET_CAMERA`) | `[Initialize]` (`FUNC_reset_all_initialize`) |
| :--- | :---: | :---: | :---: |
| **Wi-Fi SSIDs/PSKs, `Wi-Fi Direct`, Static IP/DNS** (`FUNC_reset_wifi_ssid_psk`) | **CLEARED** | Preserved | **CLEARED** |
| **Bluetooth Pairing, `Bluetooth Function`, `Bluetooth Rmt Ctrl`** | **CLEARED** (`Off`) | Preserved | **CLEARED** (`Off`) |
| **FTP Profiles (`0..8`), `Auto FTP`, `FTP Power Save`** | **CLEARED** | Preserved | **CLEARED** |
| **`Creators' Cloud` / `Remote Shoot` / `Access Authen.` / `IPsec` / `USB-LAN`** | **CLEARED** | Preserved | **CLEARED** |
| **`Network Streaming` (`RTMP`/`RTMPS`/`SRT`) & Root Certificates** | **CLEARED** | Preserved | **CLEARED** |
| **`[Airplane Mode]` (`BKID_APP_setting_airplane_mode`)** | **Reset to `Off`** (`ilc/2210` `(Network)` default; re-enable `On` post-reboot) | Preserved | **Reset to `Off`** |
| **`(Shooting)` / `(Exposure/Color)` / `(Focus)` & `Framing Settings (HDMI)`** | Preserved | **RESET** | **RESET** |
| **`(Setup)` (`[Language]`, `[Area/Date]`, `[USB]`, `[HDMI Info.]`, `[Volume]`)** | Preserved | Preserved | **RESET** |
| **`(Playback)` (`[Protect]`, `[Delete confirm.]`, `[Image Jump]`)** | Preserved | Preserved | **RESET** |
| **`CAMSET` (`M1..M4` on card), Registered Faces, User `.cube` LUTs** | Preserved | Preserved | **CLEARED** (faces/certs/privacy; card `M1..M4` untouched) |

   - **FX6 Ver. 6.01 Parity**: `ILME-FX6` exposes `Network > Network Reset > Reset` (`Execute` / `Cancel`, `_2.uxc` `0x4291` `Network Reset`, `BKID_APP_USER_MENU_NETWORK_RESET`, `BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET`) vs `Maintenance > All Reset` (`0x4271`).
   - **Air-Gapped Zero-RF Bench Preparation**: To guarantee zero wireless credentials and zero RF emission on an air-gapped bench, execute **`[Reset Network Set.]`** first (purging all Wi-Fi PSKs, BT pairings, FTP/Cloud tokens, and certificates, and allowing the mandatory `BKID_APP_is_shutdown_factor_network_reset` reboot to complete), and **then** set **`[Airplane Mode] = [On]`** (`BKID_APP_setting_airplane_mode = AIRPLANE_MODE_ON`, `_f.uxc` `0x6b05`/`0x6df9`) so `(Network)` reset to `Off` never leaves the radio enabled.

---

## 5. `O_RDONLY` Local Donor Audit Ledger & 4-Language `resid16` Parity (`raw_firmware_bytes_leaked = 0`)

### 5.1 Audited Donor Artifacts (`os.O_RDONLY`)

| Donor Artifact | Size (`B`) | SHA-256 | Verified Wave 47 Symbols / Evidence (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_usb_connection_method` (`USB_CONNECTION_{SELECT_AFTER_CONNECTION,MASS_STORAGE,MTP,REMOTE_PC,USB_STREAMING}`), `BKID_APP_setting_lun_settings` (`LUN_SETTING_{MULTI,SINGLE}`), `BKID_APP_setting_usb_supply` (`USB_SUPPLY_{ON,OFF}`), `BKID_APP_setting_hdmi_info_display`, `BKID_APP_setting_rec_media_during_hdmi_output`, `FUNC_protect_*`, `FUNC_reset_network_settings`, `SETTING_RESET_{NW,CAMERA}`, `BKID_APP_is_shutdown_factor_network_reset`, `BKID_APP_setting_airplane_mode` |
| `FX3 string_english_f.uxc` (`ns=227`) | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` records: `0x69a2` `USB Connection Mode`, `0x7738` `Sel. When Connect`, `0x6c54` `MassStorage(MSC)`, `0x60aa` `Remote Shoot (PC Remote)`, `0x6b19` `USB LUN Setting`, `0x721e` `USB Power Supply`, `0x6e7c` `HDMI Info. Display`, `0x6848` `All in this Folder`, `0x60d3` `Reset Network Set.`, `0x65d3` auto-reboot prompt, dormant `0x7399` `USB Streaming` |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | Exact `7,475`-record `resid16` 1:1 parity with `EN` |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `0xe24b` `MTP`, `0xe2c9` `Protect`, `0xe2ca` `Multiple Img.`, `0xe826` `All Images in This Group`, `0xe449` `Format`, `0xe414` `All data will be deleted. Format?`, `0xe07c` `On` (`入`), `0xe297` `Off` (`切`) |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `0x6239` `Selection/Memo`, `0x61e1` `Network Option`, `0x642a` `External Output`, dormant `0x63f7` `USB Streaming` |
| `FX3 usb_f_uvc.ko` (`full-v4/usr/kmod`) | `78,840` | `a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc` | Present in `4.9.337-scel+` tree yet un-`insmod`ed & UI-masked on `ILME-FX3` (`NOUVC`) |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | Dual `BK4\x00` seed baseline (`819` subsystems, checksums PASS) |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_HDMI_INFO_DISPLAY`, `BKID_APP_SETTING_USB_STREAMING_PROCAM`, `BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP0..2`, `BKID_APP_USER_MENU_NETWORK_RESET`, `BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `0x220f` `Format`, `0x29c9` `USB Tethering` (`5,044` strings) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `0x4291` `Network Reset`, `0x4271` `All Reset`, `0x42af` `Lock/Unlock Clip`, `0x413c` `Lock All Clips`, `0x4eea` `SDI Out2/HDMI Super`, `0x4254` `Format Media` (`5,915` strings) |
| `FX6 usb_f_uvc.ko` (`Ver. 6.01`) | `78,840` | `bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305` | Active ProCam UVC gadget module on `ILME-FX6` |

### 5.2 4-Language `resid16` Parity Matrix (`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`)

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | Role / Domain |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x69a2` | `USB Connection Mode` | `USB连接模式` | `USB連線模式` | `USB接続モード` | Setup -> USB |
| `_f` `0x7738` | `Sel. When Connect` | `连接时选择` | `連接時選擇` | `接続時に選択` | Default USB Mode |
| `_f` `0x6c54` | `MassStorage(MSC)` | `海量存储器(MSC)` | `大量儲存(MSC)` | `ﾏｽｽﾄﾚｰｼﾞ (MSC)` | MSC Disk Mode |
| `.uxc` `0xe24b` | `MTP` | `MTP` | `MTP` | `MTP` | MTP (Slot 1) |
| `_f` `0x60aa` | `Remote Shoot (PC Remote)` | `遥控拍摄(电脑遥控)` | `遙控拍攝(PC遙控)` | `リモート撮影 (PCリモート)` | Remote Shooting |
| `_f` `0x6b19` | `USB LUN Setting` | `USB LUN设定` | `USB LUN設定` | `USB LUN設定` | `Multi` (`0xe631`) / `Single` (`0x776d`) |
| `_f` `0x721e` | `USB Power Supply` | `USB电源供给` | `USB電源供給` | `USB給電` | Type-C PD Power (`On` default) |
| `_f` `0x7399` | `\ue660USB Streaming` | `\ue660USB流式传输` | `\ue660USB串流傳輸` | `\ue660USBストリーミング` | Dormant in FX3 (`NOUVC` masked) |
| `_f` `0x6e7c` | `HDMI Info. Display` | `HDMI信息显示` | `HDMI資訊顯示` | `HDMI情報表示` | `On` (`0xe07c`, default) / `Off` (`0xe297`) |
| `_f` `0x6144` | `Rec. Media dur HDMI Output` | `HDMI输出时的摄像媒体` | `HDMI輸出時錄製到記憶卡` | `HDMI出力時のﾒﾃﾞｨｱ記録` | `On` / `Off(HDMI Only)` (`0x6573`) |
| `_f` `0x6e97` | `RAW Output` | `RAW输出` | `RAW輸出` | `RAW出力` | Forces `HDMI Info. Display = Off` |
| `.uxc` `0xe2c9` | `Protect` | `保护` | `保護` | `プロテクト` | Playback -> `Selection/Memo` (`0x6239`) |
| `.uxc` `0xe2ca` | `Multiple Img.` | `多个影像` | `多個影像` | `画像選択` | Protect multiple items |
| `_f` `0x6848` | `All in this Folder` | `该文件夹内的全部影像` | `此資料夾中的所有影像` | `このフォルダーの全画像` | Protect folder (`Cancel`: `0x72d9`) |
| `_f` `0x69f7` | `All with this date` | `该日期的全部影像` | `此日期的所有影像` | `この日付の全画像` | Protect date (`Cancel`: `0x7339`) |
| `.uxc` `0xe826` | `All Images in This Group` | `该组内的所有影像` | `此群組中的所有影像` | `このグループの全画像` | Protect group (`Cancel`: `0xe553`) |
| `.uxc` `0xe449` | `Format` | `格式化` | `格式化` | `フォーマット` | Wipes **even `[Protect]` files** (`0xe414`) |
| `_f` `0x60d3` | `Reset Network Set.` | `复位网络设置` | `重設網路設定` | `ﾈｯﾄﾜｰｸ設定リセット` | Clears `(Network)` + auto-reboots (`0x65d3`) |
| `_f` `0x646b` | `Camera Settings Reset` | `相机设置复位` | `拍攝設定重設` | `撮影設定リセット` | Preserves `(Network)` & `(Setup)` |
| `_f` `0x6289` | `Initialize` | `初始化` | `初始化` | `初期化` | Full factory reset |
| `_f` `0x6df9` | `Airplane Mode` | `飞行模式` | `飛航模式` | `機内モード` | Mandatory `On` post-network-reset |
