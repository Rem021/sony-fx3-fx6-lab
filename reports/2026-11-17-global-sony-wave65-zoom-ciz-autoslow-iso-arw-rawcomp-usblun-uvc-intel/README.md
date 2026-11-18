# 全球 Sony 实机情报 Wave 65（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Zoom Range]` 清晰影像/数字变焦与 8 档双段速度、`[Auto Slow Shutter]` / `[ISO Range Limit]` / 静态专属 `[ISO AUTO Min. SS]` 与双原生 Base ISO 真值、静态 `ARW` `Uncompressed`/`Compressed` 对照休眠 `Lossless Comp` 辟谣与 `[HLG Still Image]`，以及 `[USB Connection Mode]` / `[USB LUN Setting]` `Slot 1` 主机挂载隐患 / `NP-FZ100` USB-PD 门控 / `UVC` 流式传输实证）

- **日期**：`2026-11-17`
- **任务 / 波次**：`H397` · **Wave 65（Global Sony Real-Hardware Empirical Intelligence Wave 65）**
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Zoom / Zoom Range / About zoom scale / Zoom Ring Rotate / Zoom Lever Speed / Custom Key Z. Speed / Remote Zoom Speed / Auto Slow Shutter / ISO / ISO Range Limit / ISO AUTO Min. SS / Base ISO / RAW File Type / JPEG/HEIF Switch / HLG Still Image / Rec. Media Settings / USB Connection Mode / USB LUN Setting / USB Power Supply / Network Streaming / Movie Rec During Streaming / Rec. Media dur HDMI Output / List of default setting values*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Technical > Zoom > Zoom Type (p.116)*、*Technical > Handle Zoom*、*Shooting > Base ISO / Base Sensitivity / AGC*、*Project > Rec Format*、*DC IN 19.5V / DC Low Voltage*）及 Sony `ILME-FX6` *Monitor & Control Help Guide*
  - 并严格对照 `os.O_RDONLY` 本地 donor 二进制实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX3 usr/kmod/{usbg_storage.ko, usbg_stillimage.ko, usb_f_uvc.ko, g_webcam.ko}`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc` 及 `FX6 kmod/`）
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、内核模块符号、SHA-256 账本与官方 Help Guide/说明书条目）与 **`推断`**（Tier-0 `Slot 1` 保险库边界、`EROFS=30` 防护与台架防污染推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`Shooting -> [Zoom]` 与 `Setup -> [Zoom Ring Rotate]`：`[Zoom Range]` 三档倍率、8 档待机/录制分速与 AF/RAW 互锁）**：
   - **实测事实（菜单、Reset 与倍率）**：`ILME-FX3 Ver. 7.02` 在 `Shooting -> [Zoom]` 下暴露 `[Zoom]`、`[Zoom Range]`（**`Optical zoom only`（默认）** / `ClearImage Zoom` / `Digital Zoom`）、`[Zoom Lever Speed]`（`1st Zoom Spd.` 默认 **`3`**、`2nd Zoom Spd.` 默认 **`8 Fast`**，1–8 档分待机与视频录制）、`[Custom Key Z. Speed]`（`Fixed Speed` 1–8 档默认 **`3`** 分待机/录制）、`[Remote Zoom Speed]`（`Speed Type` 默认 **`Variable`** / `Fixed`，`Fixed Speed` 1–8 档默认 **`3`** 分待机/录制）；并在 `Setup -> [Operation Customize]` 下提供 `[Zoom Ring Rotate]`（**`Left(W)/Right(T)`（默认）** / `Right(W)/Left(T)`）。关键 Reset 分化：`[Zoom Lever Speed]` / `[Custom Key Z. Speed]` / `[Remote Zoom Speed]` **可被 `[Camera Settings Reset]` 复位（`Can be reset`）**，而 **`[Zoom Range]` 与 `[Zoom Ring Rotate]` 均标注 `Not available`（仅 `[Initialize]` 还原）**。
   - **实测事实（CIZ / Digital 倍率、锁死条件与 `ILME-FX6` 对比）**：电影模式下 Clear Image Zoom 为 **`Approx. 1.5x`（4K）/ `Approx. 2x`（HD）**，Digital Zoom 为 **`Approx. 4x`**（FF 与 APS-C 通用；Smart Zoom 电影不可用）；静态 3:2 下 FF `L (12M)` 依次为 `— / 2x / 4x`，`M (5.1M)` 为 `1.5x / 3.1x / 6.1x`，`S (3.0M)` 为 `2x / 4x / 8x`。当静态 `[File Format]` 含 `RAW`、电影 `119.88p/100p` 或 `S&Q 240fps/200fps/120fps/100fps` 时，Clear Image / Digital Zoom **不可用**；激活非光学变焦期间，**`[Focus Area]` 禁用（AF 中央优先）、`[Metering Mode]` 锁定 `[Multi]`、且 `Face/Eye Prior. in AF` / `Face Priority in Multi Metering` / `Tracking` 全部失效**。对比 `ILME-FX6 Ver. 6.01`（`5-024-458-18` p.116）：`Technical > Zoom > Zoom Type` 仅暴露 `Optical Zoom Only` 与 `On(Clear Image Zoom)`（`1.5x` 4K / `2x` HD），**完全没有 `Digital Zoom`**（`FX6 appFw.so` `VAL_setting_zoom_setting_*` 仅含 `OPTICAL_ZOOM_ONLY` 与 `CLEAR_IMAGE_ZOOM_ON`），并在 `S&Q > 60fps` 或 `Codec` 含 `RAW` 时禁用；其双摇杆控制通过握把与手柄 `Handle Zoom`（`Off / Low / High / Variable`，`High=1..8` 默认 `8`、`Low=1..8` 默认 `3`）实现。

2. **子系统 2（`Exposure/Color -> [Exposure]`：`[Auto Slow Shutter]` 6+ 项互锁、静态专属 `[ISO AUTO Min. SS]` 与双原生 Base ISO 真值）**：
   - **实测事实（`[Auto Slow Shutter]` 与 `[ISO Range Limit]` / `[ISO AUTO Min. SS]`）**：
     - `[Auto Slow Shutter]`（`BKID_APP_setting_auto_slow_shutter`）仅限电影模式，**默认 `On`**（可被 `[Camera Settings Reset]` 复位），在 6 种官方条件下面板强制禁用：`S&Q` 运动模式、`Shutter Priority (S)`、`Manual Exposure (M)`、`[ISO]` 非 `ISO AUTO`、`[Flexible Exp. Mode]` 快门设为 `Manual`、`[Log Shooting]` = `Cine EI Quick` 或 `Cine EI`（且在逻辑上与仅限 `S`/`M`/手动快门下的 `[Shutter Mode] = Angle` 完全互斥）。
     - `[ISO Range Limit]`（`BKID_APP_setting_iso_range_limit_{min,max}_{still,movie}`）**抗 `[Camera Settings Reset]`**（`Not available`），仅限制**手动 ISO** 范围（`[ISO AUTO]` 上下限独立在 `[ISO] -> [ISO AUTO]` 右拨轮设置）。
     - `[ISO AUTO Min. SS]`（`_f 0x778b`, `BKID_APP_setting_iso_auto_min_s_s`）**严格仅限静态照片 `P`/`A` + `ISO AUTO`**（在电影与 `S&Q` 下完全禁用/不可用，闪光灯下被 `1/250 s` 覆盖），提供 `SLOWER (-2 EV)` / `SLOW (-1 EV)` / **`STD`（默认，按镜头焦距联动）** / `FAST (+1 EV)` / `FASTER (+2 EV)` 或手动 `1/8000" .. 30"`，可被 Reset。
   - **实测事实（`FX3 Ver. 7.02` vs `FX6 Ver. 6.01` 双原生 Base ISO 真值）**：在 `Cine EI` / `Cine EI Quick`（`S-Log3`）下，`FX3` 通过 `MENU -> (Exposure/Color) -> [Exposure] -> [Base ISO]`（`_f 0x78ce`）直接暴露 **`ISO 800`（默认，EI `200..3200`）** 与 **`ISO 12800`（EI `3200..51200`）** 两档（4 档差），与 `FX6` `Cine EI`（`800 / 12800`）对齐；在非 `Cine EI` 模式下 `Base ISO` 开关**不可见**，硬件随各 Gamma 曲线自动切换高低双增益基线（高原生约为低原生 `20×` 即 `+4.33 EV`），`FX3 appFw.so` `VAL_HAITA_model_diff_normal_iso_range_min_*` 实证各曲线低/高原生 ISO 对应为：`S-Log3` / `S-Log2` / `ITU709(800%)` 为 `640`（`800` Cine EI）/ `12800`、`S-Cinetone (PP11)`（`gamma_schrome`）与 `HLG` / `HLG3` / `Cine4` 为 **`100` / `2000`**、`HLG1` / `Cine2` 为 **`50` / `1000`**、`Cine1` 为 **`64` / `1280`**、`PP Off` / `Movie` / `Still` / `HLG2` / `Cine3` 为 **`80` / `1600`**（静态或部分档位低点亦可为 `100`/`2000`）。对比 `FX6 Ver. 6.01`：在 `Custom` 模式下不提供静态 `ISO AUTO Min. SS`，而是通过 **`Base Sensitivity` = `Low` / `High`（`Dual Gain`）**（`FX6 ns1 0x2268`, `0x318d`, `0x3190`）与 `AGC` 实现自动增益控制。

3. **子系统 3（`Shooting -> [Image Quality/Rec]` 静态 `ARW` `Lossless Comp` 休眠辟谣、`HEIF` / `[HLG Still Image]` 与 `Sort Recording` `Slot 1` 边界）**：
   - **实测事实（`[Lossless Comp]` `L/M/S` 在 `FX3 Ver. 7.02` 上确认为休眠固件资产）**：`FX3 appFw.so` 与 `_f.uxc` 确实同时编译了 `RAW_FILE_TYPE_LOSSLESS`、`LOSSLESS_L`、`LOSSLESS_M`、`LOSSLESS_S`（`_f 0x6b56` / `0x7897` / `0x6bfd` / `0x7894`）；**然而** Sony 官方 `ilc/2210`（*RAW File Type* 及 *List of default setting values*）实机确认 `ILME-FX3 Ver. 7.02`（`12.1MP` / `10.2MP` 传感器）向用户**严格仅暴露 `Compressed`（默认）与 `Uncompressed`** 两项（14-bit `.ARW`，可被 Reset），**无损压缩 `Lossless Comp (L/M/S)` 属于与 `ILCE-7M4` / `ILCE-7RM5` / `ZV-E1` 共享代码库中的休眠分支**！
   - **实测事实（`HEIF 4:2:0 / 4:2:2`、`[HLG Still Image]` 与 `[Sort Recording]`）**：`[JPEG/HEIF Switch]`（`_f 0x742a`）支持 **`JPEG`（默认）** / `HEIF(4:2:0)` / `HEIF(4:2:2)`（10-bit `.HIF`）；开启 `[HLG Still Image]`（`_f 0x76c8`, `BKID_APP_setting_still_hlg_photo` —— ELF 枚举含内部拼写错字 `STILL_HLD_PHOTO_{OFF,ON}`）需同时满足 `HEIF` 切换开启、`[File Format] = HEIF`（选 `RAW` 或 `RAW & HEIF` 时强制 `Off`）及 `P/A/S/M` 模式，启用后强制将色彩空间切为 `BT.2100`（`BT.2020`）并上移正常 ISO 下限至 `100/125`（ELF `VAL_HAITA_model_diff_normal_iso_range_min_in_still_hlg_photo_on_*`）。在 `[Rec. Media Settings] -> [Recording Media] = [Sort Recording]` 下可将 `RAW` 与 `JPEG/HEIF` 分槽录制，但一旦触发 `[Auto Switch Media]` 满卡接力，剩余卡槽会接管**全部两类格式**；因此若 `Slot 1` 为只读恢复保险库，必须对一切 `.ARW`/`.JPG`/`.HIF` 落盘请求执行 **`EROFS (errno 30)`** 拦截。对比 `ILME-FX6 Ver. 6.01` 为纯电影摄影机，无静态 `RAW File Type` / `HLG Still Image` / `DCIM` 管线。

4. **子系统 4（`Setup -> [USB]` 与 `Streaming`：`[USB LUN Setting] = Single` 仍暴露 `Slot 1` 主机威胁、`NP-FZ100` PD 门控与 `FX3`/`FX6` `UVC` 双双辟谣）**：
   - **实测事实（`[USB Connection Mode]` 四档与 `[USB LUN Setting]` `Slot 1` 主机挂载隐患）**：`Setup -> [USB] -> [USB Connection Mode]` 在 `ILME-FX3 Ver. 7.02` 严格暴露 4 项：**`Sel. When Connect`（默认）** / `MassStorage(MSC)` / `MTP` / `Remote Shooting`（全部 Setup 项**抗 `[Camera Settings Reset]`**）。关键安全陷阱：**`[USB LUN Setting]`（`_f 0x6b19`, `BKID_APP_setting_lun_settings`）设为 `Multi`（默认）时向主机暴露 `Slot 1 + Slot 2` 双 LUN；设为 `Single`（`_f 0x776d`）时暴露的是“仅 Slot 1”，而非“隐藏 Slot 1”**（且 `MTP` 同样默认锁定 `Slot 1`）！结合 `FX3 usbg_storage.ko`（`atapi_dvd_read_write` / `pInfoLun`）导出可读写块设备，一旦将 FX3 MSC 接入 macOS 主机，`Spotlight`（`mds`）、`fseventsd` 与 `fsck_exfat`/`fsck_msdos` 将直接向 `Slot 1` 写入 `.Spotlight-V100` / `.fseventsd` / 脏标志，必须通过台架禁止主机 MSC 直连或以硬件只读卡槽/LUN 守卫隔离。
   - **实测事实（`[USB Power Supply]` `NP-FZ100` 门控 vs `FX6` `19.5V DC IN`）**：`[USB Power Supply]`（`_f 0x721e`）默认 **`On`**（抗 Reset），**仅限 USB Type-C 接口输入**，且在 `FX3` 上**即使接入 USB-C PD（`9V/3A`）也必须插入有电量的 `NP-FZ100` 电池包才能开机/录制**（拔出电池立即断电；真正无电池直流供电需使用 Sony **`DC-C1` 假电池耦合器** + `>=65W PD` + `5A e-Marked` 线缆）。对比 `ILME-FX6 Ver. 6.01` 原生配备 **`19.5V DC IN`（`18.0–20.5V` EIAJ 圆口，`DC Low Voltage1/2 = 16.5V/15.5V`）**，无需装入 `BP-U` 电池即可直接开机并长期稳定运行。
   - **实测事实（`FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 原生 `UVC/UAC USB Streaming` 双双辟谣与 `[Movie Rec During Streaming]`）**：**`ILME-FX3 Ver. 7.02` 菜单中不存在原生 `[USB Streaming]`（`UVC/UAC`）功能**（`ilc/2210` 无 `USB Streaming` 页，`(Network) -> [Streaming]` 仅含 `Ver. 6.00+` 新增的 `[Network Streaming]`（`RTMP/RTMPS/SRT`）与 **`[Movie Rec During Streaming]`**（`_f 0x79d5`，`Enable` / **`Disable`（默认）**，注意非“Rec. Media dur Streaming”，后者实为 HDMI 菜单下的 `[Rec. Media dur HDMI Output]` `_f 0x6144`））。虽然 `FX3 appFw.so`（`USB_CONNECTION_USB_STREAMING` / `PRM_HAITA_*_usb_streaming_mode`）、`_f.uxc`（`0x6216` `Live Stream(USB Streaming)`、`0x6194` `Output Res/Frame Rate`）与 `usr/kmod/`（`usb_f_uvc.ko`、`g_webcam.ko`）携带了与 **`ILME-FX30` (`ilc/2220`)** / `ILCE-7M4` 共源的休眠 UVC 资产（后者暴露 `4K 15p/14.99p/12.5p`、`1080p 60p..25p`、`720p 30p/29.97p/25p` `MJPEG/YUV420` + `PCM 48kHz 16-bit 2ch`），在 `FX3 Ver. 7.02` 上仍处于休眠门控状态。同理，**`ILME-FX6 Ver. 6.01` 也无用户可见原生 UVC USB Streaming**（`Monitor & Control` 明确标注 USB-C 仅作 `USB Tethering` 网络推流与控制，直连 USB 监看为 `–`，需外部 HDMI-to-UVC 采集盒），`FX6 appFw.so` 中的 `BKID_APP_SETTING_USB_STREAMING_PROCAM`（`1280x720`/`1920x1080`/`3840x2160`）与 `kmod/usb_f_uvc.ko` 同样为休眠 ProCam 资产。

---

## 1. 子系统 1：`Shooting -> [Zoom]`、`[Zoom Range]`、8 档分速与 `Setup -> [Zoom Ring Rotate]`

### 1.1 `ILME-FX3 Ver. 7.02` 变焦菜单全表与 Reset 持久化（`实测事实`）

1. **菜单路径与 `[Camera Settings Reset]` 对照（`ilc/2210` *List of default setting values* + `FX3 appFw.so`）**：
   - `Shooting -> [Zoom]` 下包含 5 个核心设置项；`Setup -> [Operation Customize]` 下包含 1 个镜头变焦环方向项。注意同一子系统内 **`Reset` 行为并不统一**：

| 菜单项（路径） | `FX3 Ver. 7.02` 真值选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | ELF 备份键 / 枚举与 UXC `resid16`（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Zoom]`**<br>(`Shooting -> [Zoom]`) | 执行型面板动作（仅在安装电动变焦镜头或开启非光学变焦时可用；以控制拨轮 `W`/`T` 变焦） | — | `_f 0x7453` / `0x7b0a` / `base 0xe0cf` / `_g 0x6045`；`BKID_APP_setting_zoom_speed` |
| **`[Zoom Range]`**<br>(`Shooting -> [Zoom]`) | **`Optical zoom only`（默认）**<br>`ClearImage Zoom`（无画质明显劣化电子扩焦）<br>`Digital Zoom`（最高画质劣化电子扩焦） | **Not available** | `_f 0x7164` / `0x774e`；`Optical`: `_f 0x73f2` / `0x74c9`；`CIZ`: `_f 0x70e0` / `0x70e1`；`Digital`: `_f 0x796c` / `0x796d` / `base 0xe06b`。<br>`BKID_APP_setting_zoom_setting`、`VAL_setting_zoom_setting_ZOOM_SETTING_{OPTICAL_ZOOM_ONLY, CLEAR_IMAGE_ZOOM_ON, DIGITAL_ZOOM_ON}` *(`SMART_ZOOM_ONLY` 仅作静态低像素/内部枚举分支)* |
| **`[Zoom Lever Speed]`**<br>(`Shooting -> [Zoom]`) | 分 **`Standby`** 与 **`Movie Rec`** 两段：<br>• `1st Zoom Spd.`：`1`..`8`（**默认 `3`**，待机与录制均默认 `3`）<br>• `2nd Zoom Spd.`：`1`..`8 Fast`（**默认 `8 Fast`**，待机与录制均默认 `8 Fast`） | **Can be reset** | `_f 0x6079` / `0x6304`；`1st`: `_f 0x6fc0` / `0x753f`；`2nd`: `_f 0x78f0`。<br>`BKID_APP_setting_{1st,2nd}_zoom_spd_{stby,rec}`。**仅控制机身变焦杆**，不影响镜头变焦环或镜头自带电动变焦杆 |
| **`[Custom Key Z. Speed]`**<br>(`Shooting -> [Zoom]`) | 分 **`Standby`** 与 **`Movie Rec`** 两段：<br>• `Fixed Speed`：`1`（慢）..`8`（快）（**默认 `3`**） | **Can be reset** | `_f 0x6ccf` / `0x78e8`、`0x6fdb`；`BKID_APP_setting_fixed_zoom_speed_{stby,rec}`。控制自定义键（`Zoom Operation (T)` / `(W)` `_f 0x7338`/`0x76fc`）或菜单拨轮变焦速度 |
| **`[Remote Zoom Speed]`**<br>(`Shooting -> [Zoom]`) | • `Speed Type`：**`Variable`（默认）** / `Fixed`<br>• `Fixed Speed`（`Standby` & `Movie Rec`）：`1`..`8`（**默认 `3`**） | **Can be reset** | `_f 0x7128`；`Variable`: `_f 0x728a` / `0x7435`；`BKID_APP_setting_fixed_zoom_speed_type` + `BKID_APP_setting_remote_fixed_zoom_speed_{stby,rec}` |
| **`[Zoom Ring Rotate]`**<br>(`Setup -> [Operation Customize]`) | **`Left(W)/Right(T)`（默认）**<br>`Right(W)/Left(T)` | **Not available** | `_f 0x6be7`、`0x7a01`（`Left(W)/Right(T)`）、`0x7a9e`（`Right(W)/Left(T)`）。<br>`BKID_APP_setting_zoom_direction`、`VAL_setting_zoom_direction_ZOOM_DIRECTION_{LEFT_RIGHT, RIGHT_LEFT}`（兼容兼容电动变焦镜头） |

### 1.2 清晰影像 / 数字变焦倍率、AF/RAW/HFR 锁死与 `ILME-FX6` 对比（`实测事实`）

1. **电影与静态 3:2 精确变焦倍率表（`ilc/2210` *About zoom scale* & FX3 官方规格）**：
   - **电影模式（Movie / S&Q）**：`Clear Image Zoom` 为 **`Approx. 1.5x`（4K）** / **`Approx. 2x`（HD）**；`Digital Zoom` 为 **`Approx. 4x`**（Full-frame 与 APS-C 通用）。Smart Zoom 在电影模式下**不可用**。
   - **静态 3:2 模式下（`ilc/2210` *About zoom scale*）**：
     - 全画幅 `L (12M)`：Smart Zoom `—`（不可用）/ Clear Image Zoom **`2x`** / Digital Zoom **`4x`**；
     - 全画幅 `M (5.1M)`：Smart Zoom `1.5x` / Clear Image Zoom **`3.1x`** / Digital Zoom **`6.1x`**；
     - 全画幅 `S (3.0M)`：Smart Zoom `2x` / Clear Image Zoom **`4x`** / Digital Zoom **`8x`**；
     - APS-C `M (5.1M)`：`1.3x` / `2.6x` / `5.2x`；APS-C `S (3.0M)`：`2x` / `4x` / `8x`。
2. **明确禁用条件与主动激活后的功能互锁（`ilc/2210` + `FX3 appFw.so` `PRM_HAITA_setting_zoom_setting_*`）**：
   - **进入前直接禁用（不可使用 Smart/Clear Image/Digital Zoom）**：
     1. 静态 `[File Format]` 设为 **`RAW`** 或 **`RAW & JPEG` / `RAW & HEIF`**（ELF：`PRM_HAITA_setting_zoom_setting_still_setting_still_heif_image_size_setting_still_file_format_*`）；
     2. 普通电影 `[Rec Frame Rate]` 设为 **`119.88p / 100p`**（`120p`）；
     3. `S&Q Motion` `[Frame Rate]` 设为 **`240fps / 200fps`** 或 **`120fps / 100fps`**；
     4. 另有电影外部 16-bit `RAW Output`、`Breathing Comp.` 耦合等高负载路径限制（详见 Wave 31/64）。
   - **非光学变焦倍率生效期间的实时互锁**：
     1. **`[Focus Area]` 禁用**：自动对焦强制优先**画面中央区域**；
     2. **`[Metering Mode]` 锁定 `[Multi]`**：点测光/中央重点/高亮测光均不可用；
     3. **`Face/Eye Prior. in AF`、`Face Priority in Multi Metering` 与 `Tracking`（跟踪对焦）全部不可用**；
     4. Smart Zoom 本身亦关闭上述人脸/跟踪与区域测光，且仅对 `M`/`S` 尺寸 JPEG/HEIF 生效。
3. **`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 变焦系统实测对照（`实测事实`）**：

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` p.116 + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **菜单路径与档位** | `Shooting -> [Zoom] -> [Zoom Range]`：**3 档**（`Optical zoom only` / `ClearImage Zoom` / `Digital Zoom`） | `Technical > Zoom > Zoom Type`（`FX6 ns1 0x23c7`/`0x2c72`）：**仅 2 档**（`Optical Zoom Only` `0x23c9` / `On(Clear Image Zoom)` `0x23cb`） |
| **`Digital Zoom` 支持** | 支持最高 **`4.0x`（Movie）/ `8.0x`（Still S）** `Digital Zoom` | **零 `Digital Zoom`**（`FX6 appFw.so` `VAL_setting_zoom_setting_*` 仅编译 `OPTICAL_ZOOM_ONLY` 与 `CLEAR_IMAGE_ZOOM_ON`） |
| **Clear Image Zoom 倍率与互锁** | 电影 **`1.5x` (4K) / `2.0x` (HD)**；禁用条件：`119.88p/100p`、`S&Q >=100/120fps`、Still `RAW` | 电影 **`1.5x` (4K) / `2.0x` (HD)**；禁用条件：`S&Q Frame Rate > 60fps` 或 `Rec Format > Codec` 含 **`RAW`**（且 `FX6 ns1 0x29d3` 禁用存储 Preset Position） |
| **速度控制架构** | 机身摇杆 `1st/2nd Spd.`（`1..8` 分 Standby/Rec）、自定义键定速（`1..8`）与遥控速度（`Variable`/`Fixed 1..8`）；不支持机内手柄第二摇杆 | 双物理摇杆（握把遥控 + 智能手柄）：`Technical > Handle Zoom`（`FX6 ns2 0x569b..0x56d4`：`Off / Low / High / Variable`，`High=1..8` 默认 `8`、`Low=1..8` 默认 `3`；`0..99` 为缩放位置读数显示） |

---

## 2. 子系统 2：`Exposure/Color -> [Exposure]`：`[Auto Slow Shutter]`、`[ISO Range Limit]`、静态 `[ISO AUTO Min. SS]` 与双原生 Base ISO 真值

### 2.1 `[Auto Slow Shutter]` 6+ 项互锁与 `[ISO Range Limit]` / `[ISO AUTO Min. SS]`（`实测事实`）

1. **`[Auto Slow Shutter]`（`MENU -> (Exposure/Color) -> [Exposure] -> [Auto Slow Shutter]`）**：
   - **UXC 与 ELF（`实测事实`）**：`_f 0x632f` / `0x6483` / `0x76ee`；`BKID_APP_setting_auto_slow_shutter`、`VAL_setting_auto_slow_shutter_AUTO_SLOW_SHUTTER_{ON, OFF}`。**电影模式专属**，出厂默认 **`On`**，**可被 `[Camera Settings Reset]` 复位（`Can be reset`）**。低照度下自动将快门拉长至低于当前帧率倒数（如 `60p` 降至 `1/30s`）。
   - **官方 6+ 项禁用锁死条件（`ilc/2210` *Auto Slow Shutter*）**：
     1. 处于 **`S&Q Motion`**（`S&Q` 档）时不可用；
     2. 曝光模式设为 **`Shutter Priority (S)`** 时不可用；
     3. 曝光模式设为 **`Manual Exposure (M)`** 时不可用；
     4. `[ISO]` **未设为 `[ISO AUTO]`**（即处于任何固定手动 ISO）时不可用；
     5. `[Flexible Exp. Mode]` 下 **`[Shutter]` 设为 `Manual`** 时不可用；
     6. `[Log Shooting]` 设为 **`Cine EI Quick`** 或 **`Cine EI`** 时不可用（且与仅在 `S` / `M` / 手动快门激活的 `[Shutter Mode] = Angle` 存在结构性互斥，因为 `Cine EI` 下无法切入自动快门）。
2. **`[ISO]` 与 `[ISO Range Limit]`（`MENU -> (Exposure/Color) -> [Exposure]`）**：
   - **`[ISO]`**：总范围覆盖 `ISO AUTO` 与 `40..409600`（标准电影下限 `80..409600`，Log 视曲线定）。注意 **`[ISO AUTO]` 的自动上下限不在 `[ISO Range Limit]` 中设置**，而是在 `[ISO] -> 选择 [ISO AUTO] -> 按控制拨轮右键` 进行配置（`base 0xe88c` / `0xe69b`）。
   - **`[ISO Range Limit]`**（`_f 0x69cb` / `0x6d8b` / `0x72f8` / `0x75a0`；`Minimum` `_f 0x6d0d`/`0x7028`、`Maximum` `_f 0x6c4e`；`BKID_APP_setting_iso_range_limit_{min,max}_{still,movie}`）：**仅限制手动设定的 `[ISO]` 范围**，且 **`Resettable using [Camera Settings Reset]: Not available`**（仅 `[Initialize]` 还原）。
3. **`[ISO AUTO Min. SS]`（`MENU -> (Exposure/Color) -> [Exposure] -> [ISO AUTO Min. SS]`）**：
   - **严格静态专属门控（`实测事实`）**：`_f 0x6717` / `0x778b`；`BKID_APP_setting_iso_auto_min_s_s`、`BKID_APP_setting_iso_auto_min_s_s_auto`。根据 `ilc/2210` *ISO AUTO Min. SS*，该项**仅在静态照片（Still）的 `Program Auto (P)` 或 `Aperture Priority (A)` 且 `[ISO] = [ISO AUTO]` 时有效**；**在电影模式与 `S&Q` 模式下彻底禁用/不可用**（在静态闪光灯下即使设定低于 `1/250 s` 亦以闪光同步速率优先）。
   - **可选档位与默认**：`SLOWER (-2 EV)` / `SLOW (-1 EV)` / **`STD`（默认，按镜头焦距自适应设定最低安全快门）** / `FAST (+1 EV)` / `FASTER (+2 EV)`，或手动锁定具体快门值 `1/8000" .. 30"`；**可被 `[Camera Settings Reset]` 复位（`Can be reset`）**。

### 2.2 `FX3 Ver. 7.02` vs `FX6 Ver. 6.01` 双原生 Base ISO 真值矩阵（`实测事实`）

> [!IMPORTANT]
> **对双原生 Base ISO（Dual Base ISO）机内表现的实证辨析（`实测事实`）**：
> 在 `ILME-FX3 Ver. 7.02` 上，**仅当 `Log Shooting` 设为 `Cine EI` 或 `Cine EI Quick`（固定 `S-Log3`）时，菜单 `[Exposure] -> [Base ISO]`（`_f 0x78ce`, `BKID_APP_setting_base_iso`）才向用户开放显式二选一开关：`ISO 800`（默认）与 `ISO 12800`**。
> 在 `Flexible ISO`（`S-Log3` 可调 ISO）或普通/PP 模式下，`[Base ISO]` 菜单项**不可见/不可手动锁定**；此时相机根据所选 Gamma 曲线的**低原生 Base ISO（非扩展最低正常 ISO）**与 **`+4.33 EV`（`20×` 传感器双转换增益跃迁点）的高原生 Base ISO** 自动完成电路级增益切换。

1. **`FX3 appFw.so` `VAL_HAITA_model_diff_normal_iso_range_min_*` 与官方规格交叉实证（`实测事实`）**：

| 拍摄/色彩模式（`FX3 Ver. 7.02`） | `appFw.so` 实测正常 ISO 下限符号（`VAL_HAITA_model_diff_normal_iso_range_min_*`） | 低原生 Base ISO（`Low`） | 高原生 Base ISO（`High`, 约 `20×`） | 菜单是否暴露 `[Base ISO]` 手动切换 & `FX6 Ver. 6.01` 对照 |
| :--- | :--- | :---: | :---: | :--- |
| **`Cine EI` / `Cine EI Quick`** (`S-Log3`) | `BKID_APP_setting_base_iso` / `BKID_APP_setting_base_iso_switch_ei` | **`ISO 800`**（默认，EI `200..3200`） | **`ISO 12800`**（EI `3200..51200`） | **是**（`_f 0x78ce` / `0x696b`）；**与 `FX6 Cine EI`（`ISO 800 / 12800`）完全一致** |
| **`Flexible ISO` (`S-Log3`) / `PP` (`S-Log3` / `S-Log2` / `ITU709 800%`)** | `...in_gamma_slog3_ISO_SENSITIVITY_{640,800}` / `slog2_{640,800}` / `itu709_800_{640,800}` | **`ISO 640`** *（或 `800`）* | **`ISO 12800`** | **否**（随 ISO 跨越 `12800` 自动进入高增益）；`FX6 Custom` 模式下则为 **`Base Sensitivity = Low / High`**（`FX6 ns1 0x2268`/`0x318d`/`0x3190`，`Dual Gain`） |
| **`S-Cinetone (PP11)` / `HLG` / `HLG3` / `Cine4`** | `...in_gamma_schrome_ISO_SENSITIVITY_{100,125}` / `hlg_{100,125}` / `hlg3_{100,125}` / `cine4_{100,125}` | **`ISO 100`** | **`ISO 2000`** | **否**（`PP11` 下最低非扩展 ISO 为 `100`，`100 -> 2000` 正好 `20×`）；`FX6` 电影下使用 `Base Sensitivity` + `dB / ISO` |
| **`PP Off`（`Still` / `Movie`） / `HLG2` / `Cine3` / `ITU709`** | `...movie_ISO_SENSITIVITY_{80,100}` / `gamma_still_{80,100}` / `gamma_hlg2_{80,100}` / `gamma_cine3_{80,100}` | **`ISO 80`** *（部分静态/档位 `100`）* | **`ISO 1600`** *（对应 `2000`）* | **否**；注意开启 `[HLG Still Image] = On` 后，静态低点强制上移至 **`ISO 100 / 125`**（`...in_still_hlg_photo_on_ISO_SENSITIVITY_{100,125}`） |
| **`Cine1`** | `...in_gamma_cine1_ISO_SENSITIVITY_{64,80}` | **`ISO 64`** | **`ISO 1280`** | **否**（非对称内部模拟增益起点对应 `20×` 跃迁） |
| **`HLG1` / `Cine2`** | `...in_gamma_hlg1_ISO_SENSITIVITY_{50,64}` / `cine2_{50,64}` | **`ISO 50`** | **`ISO 1000`** | **否** |

- **补充实测对比（`ILME-FX6 Ver. 6.01`）**：`FX6` 在 `Custom` 模式下除 `Base Sensitivity = Low / High`（`VAL_setting_base_sensitivity_menu_BASE_SENSITIVITY_MENU_{LOW, LOW_DUAL_GAIN, MID, HIGH}`）外，采用 **`AGC`（Auto Gain Control）** 与 **`AGC Limit`**，**不存在静态照片的 `[ISO AUTO Min. SS]` 菜单项**（`FX6 appFw.so` 中 `ISO_AUTO_MIN` 命中数为 `0`）。

---

## 3. 子系统 3：`Shooting -> [Image Quality/Rec]` 静态 `RAW`/`JPEG`/`HEIF` 矩阵、`Lossless Comp` 休眠辟谣与 `Slot 1` 边界

### 3.1 `[RAW File Type]` 休眠 `Lossless Comp` 辟谣（`实测事实`）

> [!CAUTION]
> **对常见“FX3 支持无损压缩 RAW”传言的实证辟谣（`实测事实`）**：
> 虽然在 `FX3 appFw.so` 与 `string_*_f.uxc` 中可以检索到 `Lossless Comp`、`Lossless Comp (L)/(M)/(S)`（`_f 0x6b56` / `0x7897` / `0x6bfd` / `0x7894`）以及完整的 ELF 枚举 `VAL_setting_still_raw_file_type_RAW_FILE_TYPE_{LOSSLESS, LOSSLESS_L, LOSSLESS_M, LOSSLESS_S}`；**但经交叉核对 Sony 官方 `ILME-FX3` Help Guide（`ilc/2210` *RAW File Type* 及 *List of default setting values*）实机确认：`ILME-FX3 Ver. 7.02` 向用户严格仅暴露 `Compressed`（默认）与 `Uncompressed` 两项（14-bit `.ARW`）！**
> `Lossless Comp (L/M/S)` 在 `ILME-FX3 Ver. 7.02`（`PRODUCT_MODEL_ALCIN_UUD`）上为**彻底休眠的跨机身共享代码**，实际向用户开放该选项的是后续静态/混合 Alpha 机身（如 `ILCE-7M4`、`ILCE-7RM5`、`ILCE-1`、`ZV-E1` 等）。

### 3.2 `HEIF (4:2:0 / 4:2:2)`、`[HLG Still Image]` 与 `[Sort Recording]` `Slot 1` 保护（`实测事实` + `推断`）

1. **静态画质与色彩全量真值表（`ilc/2210` + `FX3 appFw.so`）**：

| 菜单项（`Shooting -> [Image Quality/Rec]`） | `FX3 Ver. 7.02` 实机可用值与默认（`ilc/2210`） | `[Camera Settings Reset]` | ELF / UXC 实证与硬性互锁（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[File Format]`**（Still） | **`JPEG`（默认）** / `HEIF`（随切换变更） / `RAW` / `RAW & JPEG`（或 `RAW & HEIF`） | **Can be reset** | `BKID_APP_setting_still_file_format_slot1/slot2`；`RAW` 与 `RAW & *` 均锁死禁止 Clear Image / Digital Zoom |
| **`[RAW File Type]`** | **`Compressed`（默认）** / **`Uncompressed`** *（`Lossless Comp L/M/S` **休眠**！）* | **Can be reset** | `_f 0x6ff2`；`Compressed`（`_f 0x6327`/`0x6f67`）、`Uncompressed`（`_f 0x67a9`/`0x6f5b`）；`BKID_APP_setting_still_raw_file_type{_slot1,_slot2}` |
| **`[JPEG/HEIF Switch]`** | **`JPEG`（默认）** / `HEIF(4:2:0)` / `HEIF(4:2:2)`（10-bit `.HIF`） | **Can be reset** | `_f 0x742a`、`0x6e14`、`0x7959`、`0x6057`；`BKID_APP_setting_jh_file_type`；切换即改变 `[File Format]` 与 `[Quality]` 中的格式显示 |
| **`[HLG Still Image]`** | **`Off`（默认）** / `On` | **Can be reset** | `_f 0x76c8`；`BKID_APP_setting_still_hlg_photo`（内部枚举拼写误作 **`STILL_HLD_PHOTO_{OFF, ON}`**）。<br>**3 项前提条件**：① `[JPEG/HEIF Switch]` 为 `HEIF(4:2:0)` 或 `HEIF(4:2:2)`；② `[File Format]` 为纯 `HEIF`（若含 `RAW` 强制 `Off`）；③ 曝光模式限 `P/A/S/M`（`iAuto`、`[DRO Bracket]` 或开启 `[Reg. Custom Shoot Set]` ISO 覆写时强制 `Off`）。<br>**激活副作用**：`[Color Space]` 强切 `BT.2100`（`BT.2020`），正常 ISO 下限升至 `100/125`，并禁用 `[Picture Profile]`、`[Creative Look]`、`[DRO]` 与 `[DRO Bracket]` |
| **`[Recording Media]` = `[Sort Recording]`**（`Rec. Media Settings`） | `Slot 1` / `Slot 2` / `Simult. Recording` / **`Sort Recording`** | **Not available** | `_f 0x7916`；按 `[Still Media]` 选 `RAW` 与 `JPEG/HEIF` 分卡落盘；两卡槽仍共享同一组 `[RAW File Type]` 与画质/尺寸设置 |

2. **`[Sort Recording]` + `[Auto Switch Media]` 对 `Slot 1` Tier-0 保险库的渗透风险（`实测事实` + `推断`）**：
   - **实测事实**：根据 `ilc/2210` *Rec. Media Settings*，当 `[Recording Media]` 设为 `[Sort Recording]` 且 **`[Auto Switch Media]`（`_f 0x6dd9`）设为 `[On]`** 时，只要任意一张存储卡（例如 `Slot 2`）写满，系统会**自动切换到在剩余的另一张卡（即 `Slot 1`）上同时录制 `RAW` 与 `JPEG/HEIF`**！
   - **台架推论（`推断`）**：即便台架尝试通过 `Sort Recording` 将测试静态图像定向到 `Slot 2`，若 `Slot 2` 容量耗尽或未就绪，`Auto Switch Media` 会将 `.ARW`/`.JPG`/`.HIF` 旁路写回 `Slot 1`。因此 **`Slot 1` Tier-0 只读保险库守卫必须无条件对所有 `DCIM/*.ARW`、`*.JPG`、`*.HIF` 及数据库 `avf` 写入返回 `EROFS (errno 30)`**。
3. **`ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：`FX6` 为纯电影摄影机（无机械快门，`FX6 appFw.so` 对 `raw_file_type`、`still_hlg_photo` 命中数为 `0`），**不支持任何静态 `.ARW`、`HEIF`、`[HLG Still Image]` 或静态 `Sort Recording`**。

---

## 4. 子系统 4：`Setup -> [USB]`、`[USB LUN Setting] = Single` 主机威胁、`NP-FZ100` PD 门控与 `UVC` 辟谣

### 4.1 `[USB Connection Mode]` 四档、`[USB LUN Setting]` `Slot 1` 暴露隐患与 `usbg_storage.ko`（`实测事实` + `推断`）

1. **`Setup -> [USB]` 全量实测表（`ilc/2210` *List of default setting values* + `FX3 appFw.so`）**：
   - `Setup -> [USB]` 下**所有项目**均标为 `Resettable using [Camera Settings Reset]: Not available`（抗 Reset，仅 `[Initialize]` 还原）：

| 菜单项（`Setup -> [USB]`） | `FX3 Ver. 7.02` 实机选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | ELF / 内核与 UXC `resid16`（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[USB Connection Mode]`** | 严格仅暴露 **4 项**：<br>• **`Sel. When Connect`（默认）**<br>• `MassStorage(MSC)`<br>• `MTP`<br>• `Remote Shooting` | **Not available** | `_f 0x69a2`；`Sel.`: `_f 0x7738`；`MSC`: `_f 0x6c54`/`0x7812`/`base 0xe7d4`；`MTP`: `base 0xe24b`；`Remote`: `_f 0x7c6f`。<br>`BKID_APP_setting_usb_connection_method`（注意：虽然 ELF 中还编译了 `USB_CONNECTION_USB_STREAMING`，但该模式在 FX3 7.02 用户菜单中**未向用户暴露**！） |
| **`[USB LUN Setting]`** | **`Multi`（默认）**（同时向 PC 暴露 `Slot 1` 与 `Slot 2`）<br>`Single`（**向 PC 仅暴露 `Slot 1`！**） | **Not available** | `_f 0x6b19`；`Multi`: `_f 0x679d`/`0x6cec`/`base 0xe631`；`Single`: `_f 0x69be`/`0x776d`；`BKID_APP_setting_lun_settings`。<br>配合 `FX3 usbg_storage.ko`（`104,288 B`）导出 `pInfoLun`、`sony_storage_dev`、`atapi_dvd_read_write`、`atapi_dvd_set_write_protect` |
| **`[USB Power Supply]`** | **`On`（默认）** / `Off` | **Not available** | `_f 0x721e`；`BKID_APP_setting_usb_supply`。仅接受 **USB Type-C** 端口供电（Multi/Micro USB 无供电能力） |

2. **`[USB LUN Setting] = Single` 与 `MTP` 对 `Slot 1` Tier-0 保险库的严重主机威胁（`实测事实` + `推断`）**：
   - **关键实测事实（`ilc/2210` *USB LUN Setting* & *USB Connection Mode*）**：Sony 官方明确说明：`[Multi]` 同时显示 `Slot 1` 与 `Slot 2` 的内容；**而选择 `[Single]` 时，显示的是“仅插槽 1 存储卡内的影像”（*Displays the images on the memory card in Slot 1 only*），并非隐藏 Slot 1**！此外，**`[MTP]` 模式同样默认仅向主机映射 `Slot 1`**。
   - **macOS 主机挂载灾备风险推论（`推断`）**：在 `Mass Storage (MSC)`（USB VID/PID `054C:0DA1`）下，`usbg_storage.ko`（`atapi_dvd_read_write`）以可读写标准块设备挂载至宿主机。若将真机直接以 MSC 接入 macOS（无论 `Multi` 还是 `Single`！），macOS 内核与后台进程将自动向 **`Slot 1`（Tier-0 恢复卡）** 触发：
     1. **`mds` / `mdworker`（Spotlight）** 尝试创建/更新 `.Spotlight-V100` 索引；
     2. **`fseventsd`** 尝试创建 `.fseventsd` 日志目录；
     3. **`Finder` / 废纸篓** 写入 `.Trashes` / `._*` AppleDouble 扩展属性；
     4. **`fsck_exfat` / `fsck_msdos`** 在挂载/异常断开时清零或改写 FAT/exFAT 卷脏位（Dirty Bit）。
     因此，在任何涉及 `Slot 1` 恢复保险库的操作中，**绝对禁止在未开启物理写保护/LUN 拦截的情况下以 `MSC`（含 `Single`）直连 macOS 宿主机**。

### 4.2 `[USB Power Supply]` `NP-FZ100` 强制门控 vs `FX6` `19.5V DC IN`（`实测事实`）

1. **`ILME-FX3 Ver. 7.02` 的 `NP-FZ100` 强制门控（`ilc/2210` *Supplying power from a wall outlet / Notes on USB Power Supply*）**：
   - **实测事实**：`FX3` 的 `[USB Power Supply] = On` **仅在机内已插入带有剩余电量的 `NP-FZ100` 电池包时才允许开机与连续供电**（即便外接 `9V/3A` USB-C PD 电源适配器，若拔掉电池或在无电池状态下插线，相机均无法工作或立即非安全断电；且当充电器/电脑无法提供足够功耗如 `< 9V/3A` PD 时仍会持续消耗机内电池电量，长期高负载建议先以 `PD 9V/3A` 或使用 **`DC-C1` 直流耦合器** + `>=65W PD` + `5A e-Marked` USB-C 线缆实现无电池外部直流供电）。
2. **`ILME-FX6 Ver. 6.01` 对比（`5-024-458-18`）**：
   - **实测事实**：`FX6` 配备专用 **`DC IN 19.5V` 圆口直流输入**（额定 `18.0–20.5V`，配 `DC Low Voltage1 = 16.5V` / `DC Low Voltage2 = 15.5V` 告警，`FX6 ns2 0x4603..0x4606`），**原生支持在完全不插入 `BP-U35/U70/U100` 电池的情况下直接上电录制**。

### 4.3 `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 原生 `UVC/UAC USB Streaming` 双双辟谣与流式录卡风险（`实测事实` + `推断`）

> [!WARNING]
> **对 `FX3` 与 `FX6`“机内免采集卡 UVC USB 流式传输”的实证双辟谣（`实测事实`）**：
> 1. **`ILME-FX3 Ver. 7.02` 没有原生 `[USB Streaming]`（`UVC/UAC`）菜单**：虽然 `FX3 appFw.so`、`string_*_f.uxc`（`_f 0x6216` `Live Stream(USB Streaming)`、`_f 0x6194` `Output Res/Frame Rate`）、`_g.uxc`（`_g 0x63f7` `USB Streaming`、`0x61af`、`0x61e5`）及 `usr/kmod/`（`usb_f_uvc.ko` `78,840 B`、`g_webcam.ko` `13,728 B`）中存在完整休眠 UVC 固件组件，但 `ilc/2210` 官方文档实证 `FX3` `[USB Connection Mode]` 只有 4 档（无 `Live Stream(USB Streaming)`）；该 UVC 栈仅在同源分支 **`ILME-FX30` (`ilc/2220`)** / `ILCE-7M4` / `ZV-E1` 上对用户激活（开放 `4K 15p/14.99p/12.5p`、`1080p 60p/59.94p/50p/30p/29.97p/25p`、`720p 30p/29.97p/25p`、`MJPEG`/`YUV420`（`720p` 仅 MJPEG）、`PCM 48kHz 16-bit 2ch`）。
> 2. **`ILME-FX3 Ver. 7.02` 的 `[Streaming]` 为 `Ver. 6.00+` 网络推流（`Network Streaming`）**：`MENU -> (Network) -> [Streaming]` 仅支持 Wi-Fi / USB-LAN / USB 网络共享下的 `RTMP/RTMPS/SRT`；其同页内置开关的精确官方名称为 **`[Movie Rec During Streaming]`**（`_f 0x79d5`, `BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution`，选项 `Enable` / **`Disable`（默认）**）。
> 3. **命名辨析与 `Slot 1` 写入风险**：用户常混用的 `"Rec. Media dur Streaming"` 在 Sony `FX3` 固件中实际分为两个独立键——流媒体下的 **`[Movie Rec During Streaming]`**（`_f 0x79d5`，控制推流同时写入存储卡）与 HDMI 下的 **`[Rec. Media dur HDMI Output]`**（`_f 0x6144`, `BKID_APP_setting_rec_media_during_hdmi_output`，选项 `On` / `Off(HDMI Only)`）。在 `FX3 appFw.so` 中二者均通过 `PRM_HAITA_media_movie_recordable_state_slot1_*` 直接关联 `Slot 1`，一旦开启均会在 `Slot 1` 触发写盘，台架必须对 `Slot 1` 执行 `EROFS (errno 30)` 阻断。
> 4. **`ILME-FX6 Ver. 6.01` 同样无原生 UVC USB Streaming**：`5-024-458-18` 与 *Monitor & Control Help Guide* 实证 `FX6` 的 USB-C 仅支持网络共享（`USB Tethering`）、媒体管理或远程协议（直连 USB 实时监看标记 `–`），**不向主机暴露 UVC/UAC 免驱摄像头设备**（尽管 `FX6 appFw.so` 携带 `BKID_APP_SETTING_USB_STREAMING_PROCAM` `1280x720`/`1920x1080`/`3840x2160` 及 `kmod/{usb_f_uvc.ko, g_webcam.ko}` 休眠资产）；需要标准 UVC 输入电脑时必须外接 HDMI/SDI 采集卡。

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `zoom_setting`/`zoom_spd`、`auto_slow_shutter`、`iso_range_limit`/`iso_auto_min_s_s`、`normal_iso_range_min_in_gamma_*`、休眠 `LOSSLESS`、`still_hlg_photo`（`STILL_HLD_PHOTO_*`）、`usb_connection_method`/`lun_settings`/`usb_supply`、`movie_rec_dur_distribution` |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（零专有原始字节泄漏） |
| `FX3 usbg_storage.ko` (`full-v4/.../usr/kmod/usbg_storage.ko`) | `104,288` | `b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255` | `pInfoLun`、`sony_storage_dev`、`atapi_dvd_read_write`、`atapi_dvd_set_write_protect` |
| `FX3 usbg_stillimage.ko` (`.../usr/kmod/usbg_stillimage.ko`) | `49,448` | `0ef9132f6e043bd38a376519f0f130545e4c8ae68473b1b9d97b1228fa2829a5` | `MTP` / `PTP` 静态图像传输内核驱动 |
| `FX3 usb_f_uvc.ko` / `g_webcam.ko` (`.../usr/kmod/`) | `78,840` / `13,728` | `a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc` / `9d8df09a035d288673dbc59daac186959fe826fdddb613a7cecc57d321164792` | `FX3` 携带但用户菜单休眠的 `UVC` Gadget 内核模块 |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `FX6` `OPTICAL_ZOOM_ONLY`/`CLEAR_IMAGE_ZOOM_ON`（无 `DIGITAL_ZOOM`）、`BASE_SENSITIVITY_MENU_*`、休眠 `USB_STREAMING_PROCAM` |
| `FX6 kmod/{usbg_storage.ko, usbg_stillimage.ko, usb_f_uvc.ko, g_webcam.ko}` | `104,288` / `49,448` / `78,840` / `13,728` | `fc6de444414c9931dc33ac9702aa9a8113e8d41bdf09d818de8fd0524783aa1e` / `c62b1b698f552f7476df08407cf754abaa796e91deb694ec1239ea079dc19caa` / `bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305` / `bec168eebeba90e4b5f6a35e1c4e12bfc0a70242c4a99ad01fde4c29462110d0` | `FX6` USB 存储与休眠 `UVC` 内核驱动 |
| `FX3 string_english_f.uxc` / `.uxc` / `_g.uxc` | `373,820` / `165,740` / `69,600` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `_f`（`hdr_flag=15`）/ `base` / `_g` 全量包 |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / `base` / `_g` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / `base` / `_g` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `_f` / `base` / `_g` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `FX6` `Zoom Type`、`Handle Zoom`、`Base Sensitivity`、`DC Low Voltage` 对照 |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，只读 `_f`/`base`/`_g` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x7164` / `0x73f2` / `0x70e1` / `0x796c` | `Zoom Range` / `Optical zoom only` / `ClearImage Zoom` / `Digital Zoom` | `变焦范围` / `仅光学变焦` / `清晰影像缩放` / `数字变焦` | `變焦範圍` / `僅光學變焦` / `清晰影像縮放` / `數位變焦` | `ズーム範囲` / `光学ズームのみ` / `全画素超解像ズーム` / `デジタルズーム` | **活跃**（抗 Reset；`1.5x` 4K/`2x` HD / `4x` Digital） |
| `_f` `0x6304` / `0x6fc0` / `0x78f0` / `0x78e8` / `0x7128` | `Zoom Lever Speed` / `1st Zoom Spd.` / `2nd Zoom Spd.` / `Custom Key Z. Speed` / `Remote Zoom Speed` | `变焦杆速度` / `第1变焦速度` / `第2变焦速度` / `自定义键变焦速度` / `遥控变焦速度` | `變焦控制桿速度` / `第1變焦速度` / `第2變焦速度` / `自訂鍵變焦速度` / `遙控變焦速度` | `ｽﾞｰﾑﾚﾊﾞｰｽﾋﾟｰﾄﾞ` / `1段目スピード` / `2段目スピード` / `ｶｽﾀﾑｷｰｽﾞｰﾑｽﾋﾟｰﾄﾞ` / `ﾘﾓｰﾄｽﾞｰﾑｽﾋﾟｰﾄﾞ` | **活跃**（可 Reset；`1..8` 分待机/录制） |
| `_f` `0x6be7` / `0x7a01` / `0x7a9e` | `Zoom Ring Rotate` / `Left(W)/Right(T)` / `Right(W)/Left(T)` | `变焦环旋转` / `左(W)/右(T)` / `右(W)/左(T)` | `變焦環旋轉` / `左(W)/右(T)` / `右(W)/左(T)` | `ｽﾞｰﾑﾘﾝｸﾞ操作方向` / `左回転(W)/右回転(T)` / `右回転(W)/左回転(T)` | **活跃**（抗 Reset；Setup 树） |
| `_f` `0x76ee` / `0x69cb` / `0x778b` / `0x78ce` | `Auto Slow Shutter` / `ISO Range Limit` / `ISO AUTO Min. SS` / `Base ISO` | `自动低速快门` / `ISO范围限制` / `ISO AUTO最小速度` / `Base ISO` | `自動慢速快門` / `ISO範圍限制` / `ISO AUTO快門速度` / `Base ISO` | `ｵｰﾄｽﾛｰｼｬｯﾀｰ` / `ISO感度範囲限定` / `ISO AUTO低速限界` / `Base ISO` | **活跃**（`Min. SS` 仅静态；`Base ISO` 仅 `Cine EI`） |
| `_f` `0x6ff2` / `0x6f5b` / `0x6f67` / `0x6b56` / `0x7897` / `0x6bfd` / `0x7894` | `RAW File Type` / `Uncompressed` / `Compressed` / `Lossless Comp` / `(L)` / `(M)` / `(S)` | `RAW文件类型` / `未压缩` / `已压缩` / `无损压缩` / `(L)` / `(M)` / `(S)` | `RAW檔案類型` / `未壓縮` / `已壓縮` / `已無損壓縮` / `(L)` / `(M)` / `(S)` | `RAW記録方式` / `非圧縮` / `圧縮` / `ロスレス圧縮` / `(L)` / `(M)` / `(S)` | **前 3 项活跃；后 4 项 `Lossless` 在 FX3 7.02 休眠** |
| `_f` `0x742a` / `0x7959` / `0x6057` / `0x76c8` / `0x7916` | `JPEG/HEIF Switch` / `HEIF(4:2:0)` / `HEIF(4:2:2)` / `HLG Still Image` / `Sort Recording` | `JPEG/HEIF切换` / `HEIF(4:2:0)` / `HEIF(4:2:2)` / `HLG静态影像` / `分类记录` | `JPEG/HEIF切換` / `HEIF(4:2:0)` / `HEIF(4:2:2)` / `HLG靜態影像` / `排序錄製` | `JPEG/HEIF切換` / `HEIF(4:2:0)` / `HEIF(4:2:2)` / `HLG静止画` / `振り分け` | **活跃**（`HLG Still` 仅限纯 `HEIF` + `P/A/S/M`） |
| `_f` `0x69a2` / `0x7738` / `0x6c54` / `base 0xe24b` / `_f 0x7c6f` | `USB Connection Mode` / `Sel. When Connect` / `MassStorage(MSC)` / `MTP` / `Remote Shooting` | `USB连接模式` / `连接时选择` / `海量存储器(MSC)` / `MTP` / `遥控拍摄` | `USB連線模式` / `連接時選擇` / `大量儲存(MSC)` / `MTP` / `遙控拍攝` | `USB接続モード` / `接続時に選択` / `ﾏｽｽﾄﾚｰｼﾞ (MSC)` / `MTP` / `リモート撮影` | **活跃**（全部抗 Reset；4 档真实暴露） |
| `_f` `0x6b19` / `0x6cec` / `0x776d` / `0x721e` | `USB LUN Setting` / `Multi` / `Single` / `USB Power Supply` | `USB LUN设定` / `多个` / `单个` / `USB电源供给` | `USB LUN設定` / `多種` / `單一` / `USB電源供給` | `USB LUN設定` / `マルチ` / `シングル` / `USB給電` | **活跃**（`Single` 暴露 **Slot 1 ONLY**；PD 需 `NP-FZ100`） |
| `_f` `0x6216` / `0x6194` / `_g 0x63f7` / `_f 0x79d5` / `0x6144` | `Live Stream(USB Streaming)` / `Output Res/Frame Rate` / `USB Streaming` / `Movie Rec During Streaming` / `Rec. Media dur HDMI Output` | `实时流式传输(USB流式传输)` / `输出分辨率/帧速率` / `USB流式传输` / `流式传输动态影像录制` / `HDMI输出时的摄像媒体` | `即時串流傳輸(USB串流傳輸)` / `輸出解析度/幀率` / `USB串流傳輸` / `串流傳輸動態影像錄製` / `HDMI輸出時錄製到記憶卡` | `ﾗｲﾌﾞｽﾄﾘｰﾐﾝｸﾞ (USBｽﾄﾘｰﾐﾝｸﾞ)` / `出力解像度/ﾌﾚｰﾑﾚｰﾄ` / `USBストリーミング` / `ｽﾄﾘｰﾐﾝｸﾞ時の動画記録` / `HDMI出力時のﾒﾃﾞｨｱ記録` | **`USB Streaming` 在 FX3/FX6 休眠**；后 2 项活跃且写卡须受 `Slot 1 EROFS=30` 拦截 |
