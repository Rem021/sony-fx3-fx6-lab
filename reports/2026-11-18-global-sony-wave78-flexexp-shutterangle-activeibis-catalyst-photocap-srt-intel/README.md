# 全球 Sony 实机情报 Wave 78（`78th Wave`：`78/78 Waves` 收官 · `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `[Exposure Ctrl Type]` / `[Auto/Manual Swt. Set.]` / `[Shutter Mode]` 角度、`[Image Stabilization]` 与 `Catalyst` 陀螺元数据、`Playback -> [Photo Capture]` / `[View Mode]` / `[Rating]` vs `Clip Flag`，以及 `[USB Streaming]` 证伪与 `RTMP/RTMPS/SRT` 推流深度审计）

- **日期**：`2026-11-18`
- **任务 / 波次**：`H453` · **Global Sony Real-Hardware Empirical Intelligence Wave 78**（`78th Wave` / `78/78 Waves` 收官审计）
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`，`Linux 4.9.337-scel+`，`PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）
- **承接与关键勘误声明**：
  - 本 Wave 78 报告承接 [Wave 51（UXC 4 语与 Streaming/Shutter 早期基线）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/reports/2026-11-15-global-sony-real-hardware-empirical-intel/README.md)、[Wave 57（SteadyShot / SRT / RTMP 深度基线）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/reports/2026-11-15-global-sony-wave57-real-hardware-empirical-intel/README.md)、[Wave 65（No-UVC 与 Creators' App 门禁）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/reports/2026-11-17-global-sony-wave65-streaming-photo-capture-rating-folder-naming-intel/README.md)、[Wave 76（Custom Key / Different Set 8 / USB-LAN）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/reports/2026-11-18-global-sony-wave76-customkey-diffset8-gammadisp-mlut-usblan-ipsec-cleaning-intel/README.md) 与 [Wave 77（Movie Settings / AWB / Touch / Screen Reader / Version）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/reports/2026-11-18-global-sony-wave77-movieset-vpg-awbprio-atw-touchpad-screenreader-version-intel/README.md)。
  - 基于官方 Sony `ILME-FX3` Help Guide（`ilc/2210` Ver. 7.02）、官方 `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB` Ver. 6.0）以及严格 `os.O_RDONLY` 只读本地 donor 二进制实证，本次审计**显式揭穿与修正了 5 项跨机型误区与仓内守卫精度勘误**：
    1. **`[Exposure Ctrl Type]` 抗 `[Camera Settings Reset]` 边界补全（`G86` 漏项）**：[`G86`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1550-L1606) 正确建模了 `[Auto/Manual Swt. Set.]`（`Av`/`Tv`/`ISO` 复位回 `Manual`）与 `[Auto Slow Shutter]`（复位回 `On`）均 **`Can be reset`**，但遗漏了父项 **`[Exposure Ctrl Type]`** 本身——`ilc/2210` *List of default setting values* 实证：**`[Exposure Ctrl Type]` 默认 `Flexible Exp. Mode`，在 `[Camera Settings Reset]` 下为 `Not available`（即若切至 `P/A/S/M Mode` 后执行相机设置复位仍保持 `P/A/S/M Mode`，仅 `[Initialize]` 才退回 `Flexible Exp. Mode`）**。
    2. **`[USB Streaming]`（UVC/UAC `4K 30p/25p/24p`）双重证伪（`ilc/2210` & `FX3 appFw.so`）**：尽管外部常误传 FX3 支持 `4K 30p/25p/24p` 原生 `[USB Streaming]`，官方 `ilc/2210` 与 Sony *Monitor & Control* 手册明确标注 **`"Connection via UVC is not supported on the ILME-FX3 / ILME-FX3A / ILCE-7SM3"`**，实机 `[USB Connection Mode]` 仅暴露 4 项（`Sel. When Connect` / `MassStorage(MSC)` / `MTP` / `Remote Shooting`）；且 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中休眠 Alpha UVC 枚举 `VAL_setting_output_format_OUTPUT_FORMAT_*` 亦仅有 `4K_12_5P` / `4K_15P` / `FULLHD_{25,30,50,60}P` / `HD720_{25,30}P`（**无 `4K 30p/25p/24p`**）。而 `_f 0x79d5` **`[Movie Rec During Streaming]` 实机专属于 `[Network Streaming]`**，并非 USB Streaming。
    3. **`[Network Streaming]` `SRT Caller` vs `Listener` 架构澄清（`FX3 appFw.so` + `libInfraSrtLiveStreaming.so`）**：`ILME-FX3 Ver. 6.00..7.02` 与 `Creators' App` 仅支持**出站 `SRT Caller`**（由相机向外部 `SRT Listener` 发起连接，在 `Creators' App` 中分栏填写 `Connecting Server URL` 与 `Port` 并拒绝 `:port` / `?streamid=` 语法），**机内与 `Creators' App` 均不提供 `SRT Listener`（监听/入站等待）模式切换**（区别于专业广播机型的 `SRT Caller/Listener` 双向菜单）。
    4. **`[SteadyShot]` `Active >= 200mm` 文档演进 & `ILME-FX6` OSS 实机枚举（`5-024-458-18` vs `FX6 ns2`）**：FX3 早年 Ver. 1 手册曾注记 `200mm` 及以上推荐改用 `Standard`，Ver. 2.00+ `ilc/2210` 已移除 `200mm` 注记并将 `120p` 更新为 `[119.88p]/[100p]` 限制；同时 `ILME-FX6 Ver. 6.01` 虽具备**零机内传感器位移 IBIS**（`FX6 ns1 0x2fa5` `"The SteadyShot mechanism is fixed."`），但 **`5-024-458-18` 实证 FX6 菜单 `Shooting > SteadyShot > Setting` 对兼容光学防抖（OSS）E 卡口镜头依然暴露 `Active / Standard / Off` 3 档**（`FX6 ns2 0x4759/0x475a` + `ASSIGNABLE_SWITCH_STEADYSHOT_{ACTIVE,STANDARD}`），仅 `Dynamic Active` 与 `SteadyShot Focal Length` 为休眠符号（纠正部分资料误称 FX6 镜头防抖只有 `On/Off` 两档之偏误）。
    5. **`[View Mode]` 实机 3 项完整枚举（`G126` 覆盖缺口补全）**：`ilc/2210` p.392 实证 `Playback -> [Playback Target] -> [View Mode]` 暴露 **3 项**：`Date View`（`base 0xe3b8`，默认）、`Folder View(Still)`（`base 0xe3b9`）与 **`Movie View`**（`_f 0x7468`）；`Folder View(MP4)`（`base 0xe3ba`）、`AVCHD View`（`base 0xe3bb`）及 `VIEW_MODE_XAVC_S_*_VIEW` 均为休眠 Alpha 符号；当前 [`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 虽已完整覆盖 `[Rating]` 与 `Slot 1` 防火墙，但尚存在 **`0` 项 `[View Mode]`（`Movie View` vs 休眠 `AVCHD/MP4`）专项规则**。
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Exposure Ctrl Type / Auto/Manual Swt. Set. / Shutter Mode / Anti-flicker Shoot. / SteadyShot / SteadyShot Adjust. / Focal Length / Photo Capture / JPEG/HEIF Switch (Playback) / View Mode / Rating / Network Streaming / Movie Rec During Streaming / Output Img. Quality Set / List of default setting values (`TP1000888852`)*）与 *Sony Creators' App / Catalyst Prepare / Monitor & Control* 官方兼容矩阵
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Iris/ISO/Gain/Shutter/Full Auto Physical Keys / Shutter Mode (Angle/Speed/ECS/Off) / Shooting > SteadyShot / Catalyst Prepare Gyro Constraints / Thumbnail > Set Clip Flag / Network & CBK-WA100 External Streaming*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：
    - [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)（`79,015,712` B，`sha256: 545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`）
    - [`FX3 libInfraSrtLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraSrtLiveStreaming.so)（`90,248` B）、[`libInfraRtmpLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreaming.so)（`85,960` B）、[`libInfraVericLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericLiveStreaming.so)（`182,472` B）、[`libInfraVericEsCodecLibrary.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericEsCodecLibrary.so)（`22,912` B）、[`libInfraRtmpLiveStreamingUtilCommon.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreamingUtilCommon.so)（`10,336` B）、[`libInfraVericUtilCommon.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericUtilCommon.so)（`18,744` B）
    - FX3 4 语全量 `.uxc` 包（`english` / `simplifiedchinese` / `traditionalchinese` / `japanese` 各含 `base` / `_f` / `_g`，共 12 个文件）
    - [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)（`50,520,424` B，`sha256: a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`）与 FX6 4 语 `base` / `_2` `.uxc` 包（共 8 个文件）
  - 仓内安全守卫交叉对照：[`G65`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py)、[`G67/G68`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py)、[`G70`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py)、[`G81`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py)、[`G86`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py)、[`G121/G122`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)、[`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)、[`G133/G134`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) 与 [`G150`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py)。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`CAUTION_ID_*` 符号、SHA-256 账本、Reset/Initialize 持久性与官方 `ilc/2210` / `5-024-458-18` 条目）与 **`推断`**（Tier-0 隔离策略、台架合规边界及跨机型架构映射判断）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Exposure Ctrl Type]`、`[Auto/Manual Swt. Set.]` 与 Ver. 6.00+ `[Shutter Mode]` 角度 vs `ILME-FX6` 物理曝光键与 `Shutter Mode`）**：
   - **实测事实（FX3 灵活曝光与复位 split）**：`ILME-FX3 Ver. 7.02` 仅在 Movie / S&Q 模式下提供 `Exposure/Color -> [Exposure] -> [Exposure Ctrl Type]`（`_f 0x787e`：`Flexible Exp. Mode` `_f 0x730f` 默认 vs `P/A/S/M Mode` `_f 0x758a`），且 **`[Exposure Ctrl Type]` 本身在 `[Camera Settings Reset]` 下为 `Not available`（抗 Reset，仅 `[Initialize]` 归位）**；而其下属 `[Auto/Manual Swt. Set.]`（`_f 0x6e04`：`Av` / `Tv` / `ISO` 各自独立的 Auto/Manual 切换及 `L.Press` 长按自定义键）默认均为 `Manual` 且 **`Can be reset`**。
   - **实测事实（FX3 Ver. 6.00+ `[Shutter Mode]` 角度系统）**：`[Shutter Mode]`（`_f 0x7c7c`：`Speed` 默认 vs `Angle` `_f 0x7c86`）**严格仅限 Movie & S&Q**（`Can be reset`），提供 `5.6°`–`360.0°`（18 档标准角 + 高帧率下受限于总曝光时间的 `2F`..`64F` 多帧等效角）；`Speed` 与 `Angle` 分存独立寄存器（`BK4` `0x01120024` vs `0x01120028`），且 `[Exposure step]` 不影响快门角度；切至 `Angle` 时 `[Different Set for Still/Mv]` 强制独立保持 Still 快门速度。Still 专属 `[Anti-flicker Shoot.]`（`_f 0x780d`）仅在 Still 下可用，`_f 0x7924/0x7af8` `Var. Shutter` 在 FX3 为休眠 Alpha 符号（`0` 实机暴露）。
   - **实测事实（`ILME-FX6 Ver. 6.01`）**：机侧直接配备 **`IRIS`、`ISO/GAIN`、`SHUTTER` 三路物理拨盘/按键 + `FULL AUTO` 切换键**；`Shutter Mode` 暴露 **4 项**：`Angle` / `Speed` / **`ECS`**（`Extended Clear Scan` 微调频率 `fx6_2 0x4b56/0x4d98`）/ `Off`（直通单帧曝光）。

2. **子系统 2（`[Image Stabilization]` 深度耦合与 `Catalyst` 陀螺元数据 vs `ILME-FX6` 无机身 IBIS）**：
   - **实测事实（FX3 `[SteadyShot]` 与 `200mm` / `120p` / `De-Squeeze` 互斥）**：Movie `[SteadyShot]`（`_f 0x6a99`）含 `Active`（约 `1.104x` 裁切、强制 `[Distortion Comp.] = Auto`）、`Standard`（默认）、`Off`；`Dynamic active`（`_f 0x741c`）、`Intelligent Active`（`_f 0x6fdd`）与 `Super Active`（`_f 0x71eb`）均在 `FX3` 休眠。`Active` 在 **`119.88p/100p`**、`S&Q >= 100fps`、`HDMI RAW Output = On`、`[De-Squeeze Display] != Off` 4 种条件下硬锁灰；老版 Ver. 1 手册建议 `>=200mm` 改用 `Standard`，Ver. 2.00+ `ilc/2210` 已移除 `200mm` 注记。`[SteadyShot Adjust.]`（`Auto` 默认 / `Manual`）+ `[Focal Length]`（`8mm` 默认，精确 `47` 档 `8..1000mm`）供转接 PL/全手动电影头使用，全部 4 项 IS 设置均 **`Can be reset`**。
   - **实测事实（`Catalyst Browse/Prepare` 陀螺 `RTMD` 与 `ILME-FX6`）**：Sony 官方 `Catalyst Prepare` 机内增稳仅支持 `[SteadyShot] = Off` 或 `Active`（不支持 `Standard`）+ 具备电子通讯的 E 卡口镜头，且 **`S&Q` 全帧率与正常拍摄 `119.88p/100p (120p)` 均不记录可用的 `Catalyst` 陀螺元数据**。对比 `ILME-FX6 Ver. 6.01`：**零机内传感器位移 IBIS**（`FX6 ns1 0x2fa5` `"The SteadyShot mechanism is fixed."`），但菜单对兼容光学 OSS 镜头依然暴露 `Active / Standard / Off`（需在用 Catalyst 时关闭镜头 OSS 开关）。

3. **子系统 3（`Playback -> [Photo Capture]`、`[View Mode]`、`[Rating]` vs `ILME-FX6` `Clip Flag`）**：
   - **实测事实（FX3 机内抓帧、播放视图与分级）**：`Playback -> [Edit] -> [Photo Capture]`（`_f 0x6856`）从暂停的 XAVC Movie / S&Q 提取 **`8.3M`（`3840×2160`）** 或 **`2.1M`（`1920×1080`）** 静态帧，对 **`XAVC S-I DCI 4K` 硬阻断**（`_g 0x60ce`）；其专属 `[JPEG/HEIF Switch]`（`_f 0x6938`：`JPEG` 默认 / `HEIF(4:2:0)` / `HEIF(4:2:2)`，HLG 视频可转存 HLG HEIF）**抗 `[Camera Settings Reset]`**（不同于 Shooting 侧的同名词条）。`[View Mode]`（`base 0xe3b7`）实机暴露 **`Date View` / `Folder View(Still)` / `Movie View`** 3 项（`MP4` / `AVCHD` 为休眠符号）；`[Rating]`（`_f 0x684f`，1..5 星）驱动 XMP 与 FTP 筛选且同样抗 `[Camera Settings Reset]`。Tier-0 台架将上述写入卡槽 1 的操作（向 `Slot 1` 保存抓帧或改写 `Slot 1` XMP/AVF 分级）均纳入 **`Slot 1 EROFS=30` 防火墙硬阻断**。
   - **实测事实（`ILME-FX6 Ver. 6.01`）**：**零机内静态抓帧**（`FX6 appFw.so` 无有效 Photo Capture 绑定），改用电影机 `Thumbnail > Set Clip Flag`（`OK` / `NG` / `KEEP` essence marks + `Delete Clip Flag` 与 `Filter Clips`）。

4. **子系统 4（`Network -> [Streaming]`：`[USB Streaming]` 证伪与 `Ver. 6.00..7.02` `[Network Streaming]` `RTMP/RTMPS/SRT` vs `ILME-FX6`）**：
   - **实测事实（`[USB Streaming]` 零 UVC 铁证）**：`ILME-FX3 Ver. 7.02` **无原生 UVC/UAC `[USB Streaming]` 菜单**（`ilc/2210` 与 *Monitor & Control* 明文否定，ELF 中 UVC 输出枚举仅留休眠 Alpha 时代 `4K_12_5P/15P` / `FHD 60P..25P` / `HD720 30P/25P`）；`[Movie Rec During Streaming]` 实机专用于 `[Network Streaming]`。
   - **实测事实（`[Network Streaming]` `RTMP/RTMPS/SRT` 实机矩阵）**：需蓝牙联动 **`Creators' App`** 注入配置（`_g 0x63f5/0x648f/0x64be/0x64c1`），支持 `RTMP`（H.264）、`RTMPS`（H.264 + 根证书校验）与 `SRT`（H.265/HEVC 或 H.264、`AES-128/256`、`48kHz 16-bit 2ch` 音频；仅出站 **`SRT Caller`**）。码率矩阵锁定 `59.94p/50p/29.97p/25p`（**禁用 `23.98p/24p/120p`**），峰值 `38 Mbps`，`[Movie Rec During Streaming]`（默认 `Disable`）在 `4K` 或 `2K 60p/50p` 推流时禁止机内 4K 录卡。对比 `ILME-FX6 Ver. 6.01`：**无原生 UVC、无内置 RTMP/SRT/QoS 直推**（依赖外接 `CBK-WA100` / `CBK-RPU7` / `PDT-FP1` 或外部推流编码器），ELF/UXC 中的 `RTMP_SETTINGS1..8` / `SRT_SETTINGS1..8` / `QoS Streaming` 属休眠同源 Procam 串。

---

## 1. 子系统 1：`[Exposure Ctrl Type]`、`[Auto/Manual Swt. Set.]` 与 Ver. 6.00+ `[Shutter Mode]` 角度 vs `ILME-FX6`

### 1.1 `ILME-FX3 Ver. 7.02` 灵活曝光（`Flexible Exp. Mode` vs `P/A/S/M Mode`）与复位实证（`实测事实`）

菜单路径：`MENU -> (Shooting) -> [Exposure/Color] -> [Exposure] -> [Exposure Ctrl Type]` 与 `[Auto/Manual Swt. Set.]`（仅 Movie / S&Q 可见；Still 模式始终遵循传统 `P/A/S/M` 逻辑）。对照 `ilc/2210` *Exposure Ctrl Type*、*Auto/Manual Swt. Set.*、*List of default setting values*（`TP1000888852`）及 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)：

| 菜单项（UXC `resid16`） | 实机选项与出厂默认 | ELF 核心符号（`FX3 appFw.so`） | 适用模式与互斥 | `Camera Settings Reset` 真值 |
| :--- | :--- | :--- | :--- | :--- |
| **`[Exposure Ctrl Type]`**<br>（`_f 0x787e`） | • **`Flexible Exp. Mode`**（`_f 0x730f`，**出厂默认**）<br>• `P/A/S/M Mode`（`_f 0x758a`） | `EVENT_REMOTE_EXPOSURE_CTRL_TYPE`<br>`VAL_exposure_mode_EXPOSURE_MODE_{MOVIE,SQ}_FLEXIBLE_EXPOSURE_MODE`<br>`VAL_HAITA_exposure_mode_flexible_EXPOSURE_MODE_{FLEXIBLE,NOT_FLEXIBLE}` | 仅 **Movie & S&Q**；`Auto`（智能自动）独立于此项，可通过 `[Different Set for Still/Mv]`/`_g 0x642b` 分离 | **`Not available`**（切换 `P/A/S/M Mode` 后抗 `[Camera Settings Reset]`，仅 `[Initialize]` 回 `Flexible Exp. Mode`；**补全 [`G86`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1550-L1606) 漏项**） |
| **`[Auto/Manual Swt. Set.]`**<br>（`_f 0x6e04`） | • `Av Auto/Manual Switch`（`_f 0x6224`）：`Auto` / **`Manual`（默认）**<br>• `Tv Auto/Manual Switch`（`_f 0x6b35`）：`Auto` / **`Manual`（默认）**<br>• `ISO Auto/Manual Set`（`_f 0x6a25`）：`Auto` / **`Manual`（默认）** | `VAL_HAITA_setting_aperture_a_m_switching_exposure_mode_*`<br>`VAL_HAITA_setting_shutter_speed_a_m_switching_exposure_mode_*`<br>`VAL_HAITA_setting_iso_a_m_switching_exposure_mode_*` | 仅 `Flexible Exp. Mode` 下生效；自定义键配套 `L.PressAv/Tv/ISO Auto/Manual`（`_f 0x7851 / 0x691a / 0x731e`，出厂默认 Movie `C1=L.PressAv`, `C3=L.PressISO`）与直接切换 `Av/Tv/ISO Auto/Manual Swt.` | **`Can be reset`**（与 `[Auto Slow Shutter] = On` 同随相机设置复位回归 `Manual`；`G86` 正确建模） |

### 1.2 `ILME-FX3 Ver. 6.00..7.02` `[Shutter Mode]`（`Speed` vs `Angle`）、`Anti-flicker` 与 `Var. Shutter` 边界（`实测事实`）

1. **`[Shutter Mode]`（`_f 0x7c7c`，Ver. 6.00 新增）**：
   - **选项与复位**：`Speed`（`_f 0x7c80`，**出厂默认**）/ `Angle`（`_f 0x7c86`），**`Can be reset`** 于 `[Camera Settings Reset]`。
   - **仅限 Movie & S&Q**：`ilc/2210` 明确 Still 拍摄模式无快门角度模式，仅支持 `Shutter Speed`（与 `Still -> [Shutter/Silent]` 链路彻底分离）。
   - **实机角度枚举（[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) `VAL_setting_shutter_angle_SHUTTER_ANGLE_*` 共 28 项值）**：
     - **18 档标准角度（`5.6°..360.0°`）**：`5.6°`、`11.25°`、`22.5°`、`30.0°`、`45.0°`、`72.0°`、`86.4°`、`90.0°`、`120.0°`、`144.0°`、`150.0°`、`172.8°`、`180.0°`、`210.0°`、`216.0°`、`240.0°`、`270.0°`、`300.0°`、`360.0°`（注：共 19 个枚举符号名；实机随录制/S&Q 帧率暴露相应标准角子集）；
     - **10 档慢速多帧等效角（`2F..64F`）**：`2F`、`3F`、`4F`、`5F`、`6F`、`7F`、`8F`、`16F`、`32F`、`64F`（高帧率下受帧周期上限约束，如 `119.88p/240fps` 钳位不可用慢速多帧角，与 [`G70`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L244-L265) 吻合）。
   - **寄存器隔离与耦合规则**：
     - `BK4` 槽位 `0x01120024`（`Speed`）与 `0x01120028`（`Angle`）**互相独立保存**，切换 `[Shutter Mode]` 不会覆盖另一侧寄存值；
     - `[Exposure step]`（`0.3 EV` / `0.5 EV`）**不影响 `Shutter Angle` 步进档位**；
     - 在 `Flexible Exp. Mode` 下当 `Tv = Auto` 时仍可显示但不能手动调角（需切至 `Manual` 或 `S/M` 模式）；
     - 启用 `[Shutter Mode] = Angle` 时，即使 `[Different Set for Still/Mv]` 中未勾选 `Shutter Speed`，**Still 与 Movie 快门设置依然强制独立**（`ilc/2210`）。
2. **`[Anti-flicker Shoot.]` vs 休眠 `Var. Shutter`（`FX3 appFw.so` + `ilc/2210`）**：
   - **`[Anti-flicker Shoot.]`**（`BKID_APP_setting_anti_flicker_shoot`，`On` / `Off` 默认，`Can be reset`）：**严格 Still 专属**（`Shutter/Silent -> [Anti-flicker Set.]`），**在 Movie / S&Q 模式下完全不可用**（因此与 Movie `[Shutter Mode] = Angle` 不发生运行态冲突）。
   - **`Var. Shutter`（高频抗闪烁微调快门，`HIGH_RES_SS`）**：虽然 `FX3 appFw.so` 存在 Alpha 共线符号 `ANTI_FLICKER_SET_HIGH_RES_SS_{OFF,ON}` 及 `_f 0x7924/0x7af8`（`\ue61eVar. Shutter Select` / `Var. Shutter Set.`），但 `ilc/2210` **全篇 `0` 处暴露 `Var. Shutter`**——`ILME-FX3 Ver. 7.02` 实机**不支持 `Var. Shutter`（高频电子快门微调）**，此项属休眠 Alpha 遗产串。

### 1.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 曝光架构与快门模式横向对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **曝光控制总架构** | `Exposure Ctrl Type`：`Flexible Exp. Mode`（`Av`/`Tv`/`ISO` 各自 Auto/Manual 独立切换）vs `P/A/S/M Mode`；无内置物理 ND | 机侧直接配备 **`IRIS`、`ISO/GAIN`、`SHUTTER` 三路独立 Auto/Manual 物理按键与拨盘 + `FULL AUTO` 总开关 + 电子无级 `ND FILTER`** |
| **`Shutter Mode` 选项** | 2 项（Movie/S&Q）：`Speed` / **`Angle`**（`5.6°..360°` + `2F..64F`） | **4 项**：**`Angle`**（`fx6_2 0x46fa/0x4d96`）/ **`Speed`**（`0x4d94`）/ **`ECS`**（`Extended Clear Scan` `0x4b56` + `ECS Frequency` `0x4d98`）/ **`Off`**（默认，单帧基准快门） |
| **高频抗闪烁微调** | **不支持 `Var. Shutter`**（`HIGH_RES_SS` 休眠）；`[Anti-flicker Shoot.]` 仅限 Still | 支持 **`ECS`（Extended Clear Scan）**，以细粒度频率调节消除 LED 屏/投影/工频灯带条纹 |
| **Reset 持久性** | `[Exposure Ctrl Type]` **抗 `Camera Settings Reset`**（仅 `Initialize` 复位）；`[Auto/Manual Swt. Set.]` 与 `[Shutter Mode]` **`Can be reset`** | 菜单复位由 `Maintenance > All Reset` 统一初始化（物理拨杆状态开机直读硬件位置） |

---

## 2. 子系统 2：`[Image Stabilization]` 深度耦合与 `Catalyst` 陀螺元数据 vs `ILME-FX6`

### 2.1 `ILME-FX3 Ver. 7.02` `[SteadyShot]`、`[SteadyShot Adjust.]` 与休眠扩展模式（`实测事实`）

菜单路径：`MENU -> (Shooting) -> [Image Stabilization]`（`_g 0x6214`）-> `[SteadyShot]`（Movie `_f 0x6a99` / Still `_f 0x6f45`）、`[SteadyShot Adjust.]`（`_f 0x7880`）、`[Focal Length]`（`_f 0x65b1` / `_f 0x625a`）。实证如下：

1. **Movie `[SteadyShot]` 3 档与硬互斥矩阵（`ilc/2210` + `G81`/`G133`）**：
   - **实机暴露 3 项**：**`Active`**（`_f 0x714f`，机身 5 轴 + 电子防抖约 **`1.104x` 裁切**，并强制 `[Distortion Comp.] = Auto`）/ **`Standard`**（**出厂默认**，纯机身 5 轴光学传感器位移 + 镜头 OSS 协同，无视角裁切）/ **`Off`**（关闭机内与镜头联动防抖，用于三脚架或 `Catalyst` 机外增稳）。
   - **休眠防抖模式证伪**：`FX3 appFw.so` 与 `_f.uxc` 虽遗留 `VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`、`_f 0x741c` `Dynamic active`（`动态增强`）、`_f 0x6fdd` `Intelligent Active`、`0x71eb` `Super Active`，但 **`ILME-FX3 Ver. 7.02` 均不暴露**（`Dynamic active` 属于 ZV-E1 / FX2 / 后续新机硬件链路）。
   - **`Active` 模式的 4 大实机互斥锁**：在以下任一条件成立时，`Active` 自动灰显禁用或强制回落：
     1. `[Rec Frame Rate] = [119.88p] / [100p]`；
     2. `[S&Q Settings]` 帧率设置为 `100fps / 120fps / 200fps / 240fps`；
     3. `[RAW Output Setting]` / `HDMI Output -> RAW Output = On`；
     4. `[Shooting Display] -> [De-Squeeze Display] != Off`（`1.3x / 1.5x / 1.6x(1.65x) / 1.8x / 2.0x` 变形宽银幕显示开启时，[`G133`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py#L210-L310) 吻合）。
   - **关于 `>=200mm` 长焦限制的文档演进**：早期 Ver. 1 FX3 手册曾特别提示安装 **`200mm` 及以上焦距镜头时建议切回 `Standard`**（避免长焦下电子防抖 `Active` 边缘裁切晃动/呼吸畸变）；**Ver. 2.00+ 至 Ver. 7.02 `ilc/2210` 官方帮助文档已删除 `200mm` 提示**，并将原 `120p` 统一规范为 `[119.88p]/[100p]`（纠正 [`G81`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L212) 仍沿用 `200mm` 软提示的旧版文档引用）。

2. **`[SteadyShot Adjust.]` 与 `[Focal Length]`（适配无电子触点电影/PL 镜头）**：
   - **`[SteadyShot Adjust.]`**（`BKID_APP_setting_steadyshot_adjustment`）：**`Auto`**（默认，经 E 卡口触点自动读取镜头焦距；若镜头带物理 `STEADYSHOT` 开关且拨向 `OFF`，机身端随之锁定 `Off` `CAUTION_ID_FACTOR_CAM_FIXED_FOCAL_LENGTH_LENS_MSG` / `STEADYSHOT_OFF`）/ **`Manual`**（针对老式手动头或无触点 PL/EF 转接环手动设定焦距以驱动 5 轴 IBIS）。
   - **`[Focal Length]`**（`BKID_APP_setting_steady_focal_length`）：仅在 `Manual` 下生效，**默认 `8mm`**，[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 实测精确编译 **`47` 档离散焦距**：
     `8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105, 120, 135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000 mm`（与 [`G133`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py#L236-L241) 100% 吻合）。
   - **Reset 行为**：Still `[SteadyShot]`（`On` 默认）、Movie `[SteadyShot]`（`Standard` 默认）、`[SteadyShot Adjust.]`（`Auto` 默认）与 `[Focal Length]`（`8mm` 默认）**全部为 `Can be reset` 于 `[Camera Settings Reset]`**。

### 2.2 `Catalyst Browse/Prepare` 陀螺仪 `RTMD` 元数据限制 vs `ILME-FX6` 无 IBIS 对比（`实测事实`）

1. **`ILME-FX3` `Catalyst`（注：Sony 已于 2026 年 8 月将 `Catalyst Browse` 合并整合进 `Catalyst Prepare`）陀螺采集硬限制（`ilc/2210` + Sony Catalyst 官方规范）**：
   - **`[SteadyShot]` 状态限制**：Sony 官方 `Catalyst` **仅当机内 `[SteadyShot]` 设为 `Off` 或 `Active` 时支持后制陀螺增稳**；设为 **`Standard` 时 Sony 官方不支持 `Catalyst` 增稳**（注：第三方开源软件如 Gyroflow 1.7.0+ 可实验性读取 `Standard` 下的 IBIS+IMU 数据，但不在 Sony 官方保证链内）；若使用**无电子触点的手动/电影转接镜头**，Sony `Catalyst` 官方不支持自动防抖（缺少镜头焦距与光学畸变/OSS 反馈元数据）。
   - **帧率与模式硬阻断**：**`S&Q` 慢动作与快动作（全帧率）** 以及 **常规录制 `119.88p / 100p (120p)`** **不记录可用 `Catalyst` 陀螺仪增稳元数据**（此外外部 HDMI 录机如 Atomos/BM 等录制流亦不含机内 XAVC MP4 `RTMD` 陀螺包）。
2. **`ILME-FX3` vs `ILME-FX6 Ver. 6.01` 防抖架构对比（`5-024-458-18` + `FX6 ELF/UXC`）**：

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **机身传感器位移 IBIS** | **具备 5 轴机身传感器位移 IBIS**（兼驱动 `[Sensor Cleaning]` 超声微振） | **零机内传感器位移 IBIS**（`FX6 appFw.so`：`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`；`FX6 ns1 0x2fa5` `"The SteadyShot mechanism is fixed."`） |
| **`SteadyShot` 菜单选项** | Movie：`Active` / `Standard`（默认）/ `Off`；`Dynamic active` 休眠 | **`Shooting > SteadyShot > Setting`：`Active` / `Standard` / `Off`**（`FX6 ns2 0x4759/0x475a` + `ASSIGNABLE_SWITCH_STEADYSHOT_{ACTIVE,STANDARD}` + `BKID_APP_SETTING_MOVIE_STEADYSHOT`）**——仅在安装兼容光学防抖（OSS）E 卡口镜头且镜头 OSS 开关拨 `ON` 时生效**；无 IBIS 机型下 `Dynamic Active`（`ns1 0x30ab`）为休眠串 |
| **无触点手动头焦距补偿** | `[SteadyShot Adjust.] = Manual` + `47` 档 `8..1000mm` | **无实用机内 IBIS 焦距补偿**（`BKID_APP_SETTING_STEADYSHOT_ADJUSTMENT` / `STEADY_FOCAL_LENGTH` 属共享代码树符号，物理传感器固定） |
| **`Catalyst` 陀螺增稳要求** | `[SteadyShot]` 设为 `Off` 或 `Active`；禁用 `S&Q` 与 `119.88p/100p` | **机身内 `SteadyShot` 与镜头物理 OSS 开关均必须拨至 `OFF`**（仅靠纯 IMU 陀螺记录，防止未反馈位移的 OSS 镜片干扰）；`S&Q` 全帧率与超过 `60p` 帧率同样禁用 `Catalyst` 陀螺增稳 |

---

## 3. 子系统 3：`Playback -> [Photo Capture]`、`[View Mode]`、`[Rating]` vs `ILME-FX6` `Clip Flag`

### 3.1 `ILME-FX3 Ver. 7.02` `[Photo Capture]`、播放专属 `[JPEG/HEIF Switch]`、`[View Mode]` 与 `[Rating]`（`实测事实`）

1. **`Playback -> [Edit] -> [Photo Capture]`（`_f 0x6856`，`VAL_is_edit_photo_capture_*`）**：
   - **核心能力**：在暂停播放的视频（Movie / S&Q）帧上抓取独立静态照片并保存至当前回放卡槽（可在操作中切换目标媒体）；
   - **分辨率映射**：从 `4K`（`3840×2160`）视频抓帧输出 **`8.3M`（`3840×2160`）**（`_f 0x6f54 / 0x78a6`）；从 `HD`（`1920×1080`）视频抓帧输出 **`2.1M`（`1920×1080`）**（`_f 0x7b04`）；
   - **`XAVC S-I DCI 4K` 硬阻断**：`FX3 _g 0x60ce`（`'Cannot perform this operation for movies recorded with their "File Format" set to "XAVC S-I DCI 4K".'`）实证 **`DCI 4K`（`4096×2160`）素材严禁使用 `[Photo Capture]`**（与 [`G122`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py#L354-L429) 完全一致）；
   - **Playback 专属 `[JPEG/HEIF Switch]`（`_f 0x6938` `\ue61cJPEG/HEIF Switch`，`BKID_APP_setting_photo_capture_file_type`）**：
     - 枚举 3 项：**`JPEG`**（默认）/ `HEIF(4:2:0)`（`_f 0x7959`）/ `HEIF(4:2:2)`（`_f 0x6057`）；HLG（BT.2100）视频设为 `HEIF(4:2:0)` / `HEIF(4:2:2)` 时输出 HLG HEIF 静态图，设为 `JPEG` 时转为标准 SDR JPEG。
     - **关键 Reset 边界区分**：`Shooting -> [Image Quality/Rec] -> [JPEG/HEIF Switch]` 属于 **`Can be reset`**，而 **`Playback -> [Edit] -> [JPEG/HEIF Switch]`（专用于 `[Photo Capture]`）为 `Not available` 于 `[Camera Settings Reset]`**（仅 `[Initialize]` 回 `JPEG`，[`G122` L1869-L1876](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py#L1869-L1876) 精准建模此例外）。

2. **`Playback -> [Playback Target] -> [View Mode]`（`base 0xe3b7`，`BKID_APP_setting_menu_view_mode`）**：
   - **`ilc/2210` 实机暴露 3 项**：**`Date View`**（`base 0xe3b8`，**出厂默认**）/ **`Folder View(Still)`**（`base 0xe3b9`）/ **`Movie View`**（`_f 0x7468` `\ue08bMovie View`）。
   - **休眠遗留枚举**：`base 0xe3ba` `Folder View(MP4)`、`base 0xe3bb` `AVCHD View` 以及 ELF 中的 `VIEW_MODE_XAVC_S_4K_VIEW` / `VIEW_MODE_XAVC_S_HD_VIEW` / `VIEW_MODE_XAVC_S_VIEW` 均不在 `ILME-FX3 Ver. 7.02` UI 中暴露（`ilc/2210` 全篇 `0` 处支持 AVCHD）。
   - **Reset 行为**：`Not available` 于 `[Camera Settings Reset]`（仅 `[Initialize]` 恢复 `Date View`）。

3. **`Playback -> [Selection/Memo] -> [Rating]` 与 `[Rating Set(Custom Key)]`（`_f 0x684f / 0x66c1 / 0x766e`）**：
   - 支持 **`1..5` 星**（`VALID_RATING_{1..5}_SELECTING_VALID`，`_g 0x634a` `Added a Rating(\ue5c6).`）对静态图或 XAVC 视频附加 XMP 分级；
   - **FTP / 传输联动**：直接驱动 `BKID_APP_is_valid_ftp_transfer_target_image_rating_{1..5,off}` 与 `BKID_APP_is_valid_send_to_smartphone_target_image_rating_{1..5,off}`（实现仅自动传输特定星级素材）；
   - **Reset 行为**：`[Rating Set(Custom Key)]`（`1..5` 选中掩码）**`Not available` 于 `[Camera Settings Reset]`**（仅 `[Initialize]` 归位）。

4. **推断（Tier-0 `Slot 1 EROFS=30` 写入防火墙策略）**：
   - 在实验室自动化台架下，`Slot 1` 挂载只读 Vault / 基线介质，任何将 `[Photo Capture]` 抓帧写入 `Slot 1` 或通过 `[Rating]` 改写 `Slot 1` AVF/XMP 元数据索引的动作均被拦截并返还 **`EROFS=30`**（`Slot 2` 作为独立可写测试卡槽，[`G122`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py#L171) & [`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py#L358)）。

### 3.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 回放与素材标记架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **机内视频静态抓帧** | **`Playback -> [Edit] -> [Photo Capture]`**：输出 `8.3M`（4K）或 `2.1M`（HD）JPEG/HEIF（禁 DCI 4K） | **零机内静态抓帧功能**（`FX6` 仅录像无 Still 管线；`PHOTO_CAPTURE_*` 属休眠共享符号） |
| **回放视图组织** | `[View Mode]`：`Date View` / `Folder View(Still)` / `Movie View`（3 项） | **`Thumbnail` 缩略图界面**：按 `All Clips` / `Filter Clips`（按 `OK` / `NG` / `KEEP` 旗标或无旗标筛选）组织，**无 Still 文件夹** |
| **素材筛选标记体系** | **`[Rating]` `1..5` 星** + 视频内打点 `[Shot Mark1 / Shot Mark2]`（Playback & Custom Key） | **`Thumbnail > Set Clip Flag`**：电影机 essence mark **`OK` / `NG` / `KEEP`**（`fx6_2 0x4fdb / 0x4a0d / 0x4a0f / 0x4a11`、`ASSIGNABLE_SWITCH_CLIP_FLAG_{OK,NG,KEEP}`）+ `Delete Clip Flag`（`0x4f1d`）+ 录制中/回放 `Shot Mark` |

---

## 4. 子系统 4：`Network -> [Streaming]`：`[USB Streaming]` 证伪与 `Ver. 6.00..7.02` `[Network Streaming]`（`RTMP/RTMPS/SRT`）vs `ILME-FX6`

### 4.1 `[USB Streaming]`（UVC/UAC）深度证伪：为何 `FX3 Ver. 7.02` 零暴露（`实测事实`）

1. **官方权威否定证据**：Sony 官方 `ILME-FX3` Help Guide（`ilc/2210`）与 Sony *Monitor & Control* 官方规格表均明文指出：**`"Connection via UVC is not supported on the ILME-FX3 / ILME-FX3A / ILCE-7SM3"`**；`ilc/2210` 下 `Setup -> [USB] -> [USB Connection Mode]`（`_f 0x69a2`）仅暴露 **4 项**：`Sel. When Connect`（默认）、`MassStorage(MSC)`、`MTP`（`base 0xe24b`）、`Remote Shooting`（[`G150`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py#L480-L492)）。
2. **`FX3 appFw.so` 休眠残留实证（揭穿 `4K 30p/25p/24p` 传言）**：
   - 虽然 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 与 `_f/_g.uxc` 中存在从同代 Alpha 相机（如 A7 IV / ZV-E1 / FX30）继承编译的休眠字符串 `_f 0x7399`（`\ue660USB Streaming`）、`_f 0x6216`（`Live Stream(USB Streaming)`）、`VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING` 与 `VAL_HAITA_setting_recording_to_media_usb_streaming_mode_*`，**但其休眠输出枚举 `VAL_setting_output_format_OUTPUT_FORMAT_*` 实测仅包含**：
     - `4K_12_5P`、`4K_15P`（注意：并**没有 `4K 30p/25p/24p`**，12.5p/15p 系 Alpha 7 IV 早期 USB Streaming 的 MJPEG 4K 规格！）、`FULLHD_{25P, 30P, 50P, 60P}`、`HD720_{25P, 30P}`。
   - **实测结论**：`ILME-FX3 Ver. 7.02` 不支持 USB UVC/UAC 免驱推流（外接电脑取流需用 Type-A HDMI 采集卡或有线/无线网络协议），且 `_f 0x79d5` **`[Movie Rec During Streaming]` 在 FX3 实机上 100% 服务于 `[Network Streaming]`**，并非 USB Streaming。

### 4.2 `ILME-FX3 Ver. 6.00..7.02` `[Network Streaming]`（`RTMP/RTMPS/SRT`）全量实证（`实测事实`）

菜单路径：`MENU -> (Network) -> [Streaming] -> [Network Streaming]`（`_f 0x6cb2`）、`[Output Img. Quality Set]`（`_f 0x7065`）、`[Movie Rec During Streaming]`（`_f 0x79d5`）、`[Emphasized Output Display]`（`_f 0x6661`）。

1. **传输栈与 `Creators' App` 强绑定链路**：
   - **专用 `.so` 推流管线实证**：FX3 ap-projection 固件中实际内置 6 个独立 GStreamer/Veric 推流动态库：[`libInfraSrtLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraSrtLiveStreaming.so)（`SRT`、`AES128/AES256`、`EsAudioSrt`、`EsVideoSrt`、`EsMetaSrt`）、[`libInfraRtmpLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreaming.so)（`RTMP/RTMPS` + `ERR_CERTIFICATION_*` TLS 根证书校验，对应 `BKID_APP_setting_movie_network_streaming_root_certificate_error`）、[`libInfraVericLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericLiveStreaming.so)（`VericAudio/Video/MetaDistributor` 跨芯片数据流分发）。
   - **强制蓝牙配对 + `Creators' App` 下发**：`FX3 _g 0x63f5 / 0x648f / 0x64be / 0x64c1` 实证，FX3 **无法纯机内键盘输入推流服务器 URL / Stream Key / Passphrase**，必须通过蓝牙配对手机端 **`Creators' App`** 进行推流目的地配置（支持 `Wi-Fi`、`USB Tethering` 智能手机共享、以及 Ver. 6.00+ 支持的 `USB-LAN` 有线以太网适配器，与 `[Airplane Mode] = On` 蓝牙封锁在台架下形成射频隔离边界）。
   - **`SRT Caller` vs `Listener` 实证**：`Creators' App` 与机内 UI 仅提供 `Connecting Server URL`、`Port`、可选 `Stream ID` 及 `Encryption (AES-128/256)` + `Pass Phrase`（机内 `_g 0x63f5/0x648f` 对应），**相机恒定作为 `SRT Caller` 主动外连远端 `SRT Listener`（接收端/云导播台）**；不支持把 FX3 本机设为被连接方的 `SRT Listener`。

2. **实机协议、编码、分辨率、帧率与 8 组 `BKID_APP_video_stream_bit_rate_*` 矩阵（`ilc/2210` + `FX3 appFw.so`）**：
   - **支持协议与音视频格式**：
     - **`RTMP` / `RTMPS`**：视频 `H.264/AVC`（MPEG-4 AVC），音频 `AAC-LC 48 kHz 16-bit 2ch`；`RTMPS` 强制校验已导入的根证书有效性（过期/缺失触发 `ERR_CERTIFICATION_*`）；
     - **`SRT`**：视频 `H.265/HEVC` 或 `H.264/AVC`（可在 Creators' App 选择），加密可选 `None / AES-128 / AES-256`，音频 `AAC-LC 48 kHz 16-bit 2ch`。
   - **分辨率 × 帧率 × 码率精确矩阵**（`VAL_setting_delivery_image_quality_set_frame_rate_*` **仅开放 `59.94p / 50p / 29.97p / 25p`**，**彻底禁用 `23.98p / 24.00p / 119.88p / 100p`**；自定义档 `Custom` 码率对应 `FX3 appFw.so` 8 个 `BKID_APP_video_stream_bit_rate_*` 寄存器）：

| `[Resolution]` | `[Frame Rate]` | `High` / `Standard` / `Low` 预设行为 | `Custom` 码率范围与默认值（`ilc/2210` & `FX3 appFw.so`） | `[Movie Rec During Streaming]` 机内同录限制 |
| :--- | :--- | :--- | :--- | :--- |
| **`4K (2160p)`** | `59.94p / 50p` | 受帧率与发热限制仅单档上限 | **`38 Mbps`**（`BKID_APP_video_stream_bit_rate_4k_2160p_60p_50p`） | **禁用 `4K` 机内同录**（仅可关闭同录或降为高清内录规则） |
| **`4K (2160p)`** | `29.97p / 25p` | 3 档预设 | **`38 Mbps – 13 Mbps`**，默认 **`34 Mbps`**（`..._4k_2160p_30p_25p`） | **禁用 `4K` 机内同录** |
| **`2K (1440p)`** | `59.94p / 50p` | 3 档预设 | **`38 Mbps – 9 Mbps`**，默认 **`18 Mbps`**（`..._2k_1440p_60p_50p`） | **禁用 `4K` 机内同录** |
| **`2K (1440p)`** | `29.97p / 25p` | 3 档预设 | **`38 Mbps – 6 Mbps`**，默认 **`13 Mbps`**（`..._2k_1440p_30p_25p`） | 允许内录，内录帧率锁定等于推流帧率 |
| **`HD (1080p)`** *(默认)* | `59.94p / 50p` | 3 档预设 | **`27 Mbps – 4.5 Mbps`**，默认 **`9 Mbps`**（`..._hd_1080p_60p_50p`） | 允许内录，内录帧率锁定等于推流帧率 |
| **`HD (1080p)`** | `29.97p / 25p` | 3 档预设 | **`18 Mbps – 3 Mbps`**，默认 **`6 Mbps`**（`..._hd_1080p_30p_25p`） | 允许内录，内录帧率锁定等于推流帧率 |
| **`HD (720p)`** | `59.94p / 50p` | 3 档预设 | **`13.5 Mbps – 2.3 Mbps`**，默认 **`6 Mbps`**（`..._hd_720p_60p_50p`） | 允许内录，内录帧率锁定等于推流帧率 |
| **`HD (720p)`** | `29.97p / 25p` | 3 档预设 | **`9 Mbps – 1.5 Mbps`**，默认 **`4 Mbps`**（`..._hd_720p_30p_25p`） | 允许内录，内录帧率锁定等于推流帧率 |

   - **`[Movie Rec During Streaming]` 规则（`_f 0x79d5`，`Disable` 默认 / `Enable`）**：设为 `Enable` 时，**`S&Q` 无法推流**，机内录制分辨率/帧率强制锁定跟随推流帧率（且禁用 `Proxy` / 特定 `XAVC HS` 并发限制）；`[Network Streaming]` 相关配置归属 `Network` 树，**随 `[Reset Network Set.]` 与 `[Initialize]` 复位，抗 `[Camera Settings Reset]`**；启用机内同录时，在实验室台架下**严禁写入 `Slot 1`（`EROFS=30` 防火墙阻断）**。

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 流媒体架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **原生 USB UVC/UAC 推流** | **不支持**（`USB_STREAMING` 休眠、`4K_12_5P/15P` 死代码） | **不支持**（`BKID_APP_SETTING_USB_STREAMING_{FORMAT,AUDIO}_PROCAM` 休眠，`0` 暴露） |
| **机内直推协议（RTMP/SRT/QoS）** | **Ver. 6.00+ 内置 `RTMP / RTMPS / SRT (Caller)`**（经 `Creators' App` 注入参数，峰值 `38 Mbps`，`Wi-Fi / USB-LAN / USB Tethering`） | **无内置原生 `RTMP / SRT / QoS` 直推功能**：`5-024-458-18` Ver. 6.0 机内网络仅覆 `Monitor & Control`、C3 Portal、Auto Upload FTP 及 `Streaming` 休眠遗产串（`BKID_APP_RTMP_SETTINGS1..8`、`BKID_APP_SETTING_SRT_SETTINGS1..8`、`QoS Streaming` 属共线 PXW/FX9 树遗产，`0` `USER_MENU_SRT/RTMP/QOS` 绑定） |
| **广播级外置推流链路** | — | 需经 SDI/HDMI 或专用外设接入 **`CBK-WA100` 无线适配器 / `CBK-RPU7` / `PDT-FP1` / 外部推流盒** 执行广播级 QoS / SRT 传输 |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 校验矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | Wave 78 实证覆盖符号 / 关键证据 |
| :--- | ---: | :--- | :--- |
| [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `FLEXIBLE_EXPOSURE_MODE`、`SHUTTER_ANGLE_{5_POINT_6..360_POINT_0,2F..64F}`、休眠 `HIGH_RES_SS`、`MOVIE_STEADYSHOT_{ACTIVE,STANDARD,OFF}` & 休眠 `HYBRID`、`47` 档 `STEADYSHOT_FOCAL_LENGTH`、`PHOTO_CAPTURE_FILE_TYPE_{JPEG,HEIF_420,HEIF_422}`、`VIEW_MODE_{DATE,FOLDER_STILL,MOVIE}`、`VALID_RATING_{1..5}`、`BKID_APP_video_stream_bit_rate_*`（8 档）、休眠 `OUTPUT_FORMAT_{4K_12_5P,4K_15P,FULLHD_*,HD720_*}` |
| [`FX3 libInfraSrtLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraSrtLiveStreaming.so) | `90,248` | `97292f569f1a9dbf63e1e888267ecbce34a767511da43cc15f1213119169447e` | `InfraSrtLiveStreaming_{Init,Exit}`、`AES128` / `AES256`、`EsAudioSrt` / `EsMetaSrt` / `EsDmacSrt` |
| [`FX3 libInfraRtmpLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreaming.so) | `85,960` | `9a6f65df052086ed198c69c55fbd35feaa4393d5a64acce6d17d48862f890104` | `InfraRtmpLiveStreaming_{Init,Exit}`、`ERR_CERTIFICATION_{ERROR,HAS_EXPIRED,IS_NOT_YET_VALID}`、`EsAudioRtmp` |
| [`FX3 libInfraVericLiveStreaming.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericLiveStreaming.so) | `182,472` | `cce66e647be7444af73a54b0132e100972b32b43e1db13ab3a719819192597ae` | `VericVideo/Audio/MetaDistributor`、`VericProtocolHeaderCreator`、`convertCryptoAlgo` |
| [`FX3 libInfraVericEsCodecLibrary.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericEsCodecLibrary.so) | `22,912` | `70c8ffb1a7da9114eb5c3375628997d839dd6b2983a269e67aed6725abc4a4ca` | 推流编码打包与 ES 编解码辅助库 |
| [`FX3 libInfraRtmpLiveStreamingUtilCommon.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreamingUtilCommon.so) | `10,336` | `2802e2b0cb1a07f1585c82721b90043c0ac1c9aabf95a15b714133feb4e30ebf` | RTMP 通用工具库 |
| [`FX3 libInfraVericUtilCommon.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraVericUtilCommon.so) | `18,744` | `241194a00038cf000ad2665ccc3f4a797b82d07bf85b96075bcd9d12cbac2a2b` | Veric 协议通用工具库 |
| [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_{MODE_SHUTTER,SHUTTER_ANGLE,ECS_FREQUENCY}`、`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`、`ASSIGNABLE_SWITCH_STEADYSHOT_{ACTIVE,STANDARD}`、`ASSIGNABLE_SWITCH_CLIP_FLAG_{OK,NG,KEEP}`、休眠 `RTMP_SETTINGS1..8` / `SRT_SETTINGS1..8` / `USB_STREAMING_FORMAT_PROCAM` |
| [`FX3 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc) / `_f` / `_g` | `165,740` / `373,820` / `69,600` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX3 string_simplifiedchinese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc) / `_f` / `_g` | `149,064` / `322,652` / `61,296` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX3 string_traditionalchinese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc) / `_f` / `_g` | `151,908` / `324,148` / `61,372` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX3 string_japanese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc) / `_f` / `_g` | `208,564` / `447,840` / `89,428` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX6 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc) / [`_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc) | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 EN `ns1` / `ns2`（SC：`ba060e85...` / `058c0906...`；TC：`8c34b415...` / `07fa20ae...`；JA：`9b47630e...` / `98315732...`） |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，`_f` / `base` / `_g` & `FX6 ns2` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 实机状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f 0x787e` / `0x730f` / `0x758a` | `Exposure Ctrl Type` / `Flexible Exp. Mode` / `P/A/S/M Mode` | `曝光控制类型` / `灵活曝光模式` / `P/A/S/M模式` | `曝光控制類型` / `靈活曝光模式` / `P/A/S/M模式` | `露出制御方式` / `ﾌﾚｷｼﾌﾞﾙ露出ﾓｰﾄﾞ` / `P/A/S/Mモード` | **活跃**（仅 Movie/S&Q；**抗 Camera Reset**） |
| `_f 0x6e04` / `0x6224` / `0x6b35` / `0x6a25` | `Auto/Manual Swt. Set.` / `Av Auto/Manual Switch` / `Tv Auto/Manual Switch` / `ISO Auto/Manual Set` | `自动/手动切设` / `Av自动/手动切换` / `Tv自动/手动切换` / `ISO自动/手动切换` | `自動/手動切設` / `Av自動/手動切換` / `Tv自動/手動切換` / `ISO自動/手動切換` | `ｵｰﾄ/ﾏﾆｭｱﾙ切換設定` / `Avｵｰﾄ/ﾏﾆｭｱﾙ切換` / `Tvｵｰﾄ/ﾏﾆｭｱﾙ切換` / `ISOｵｰﾄ/ﾏﾆｭｱﾙ切換` | **活跃**（`Flexible Exp.` 专属；可 Reset） |
| `_f 0x7c7c` / `0x7c80` / `0x7c86` | `Shutter Mode` / `Speed` / `Angle` | `快门模式` / `速度` / `角度` | `快門模式` / `速度` / `角度` | `シャッターモード` / `スピード` / `角度` | **活跃**（Ver. 6.00+ Movie/S&Q；可 Reset） |
| `_f 0x780d` / `0x7924` / `0x7af8` | `Anti-flicker Shoot Sel.` / `\ue61eVar. Shutter Select` / `\ue61eVar. Shutter Set.` | `防闪烁拍摄选择` / `\ue61e可变快门选择` / `\ue61e可变快门设置` | `抗光源閃爍拍攝選擇` / `\ue61e可變快門選擇` / `\ue61e可變快門設定` | `ﾌﾘｯｶｰﾚｽ撮影切換` / `\ue61e高分解ｼｬｯﾀｰ切換` / `\ue61e高分解ｼｬｯﾀｰ設定` | `Anti-flicker` **仅 Still**；`Var. Shutter` **休眠** |
| `_f 0x6a99` / `0x714f` / `0x7880` / `0x65b1` | `\ue660SteadyShot` / `Active` / `SteadyShot Adjust.` / `\ue662\ue22fFocal Length` | `\ue660SteadyShot` / `增强` / `SteadyShot调整` / `\ue662\ue22f焦距` | `\ue660SteadyShot` / `積極` / `SteadyShot調整` / `\ue662\ue22f焦距` | `\ue660手ブレ補正` / `アクティブ` / `手ブレ補正調整` / `\ue662\ue22f焦点距離` | **活跃**（`47` 档 `8..1000mm`；全部可 Reset） |
| `_f 0x741c` / `0x6fdd` / `0x71eb` | `Dynamic active` / `Intelligent Active` / `Super Active` | `动态增强` / `智能增强` / `超级增强` | `動態積極` / `智慧式進階` / `超級積極` | `ﾀﾞｲﾅﾐｯｸｱｸﾃｨﾌﾞ` / `ｲﾝﾃﾘｼﾞｪﾝﾄｱｸﾃｨﾌﾞ` / `ｽｰﾊﾟｰｱｸﾃｨﾌﾞ` | **休眠**（`FX3` 无混合动态防抖） |
| `_f 0x6856` / `0x6938` / `_g 0x60ce` | `Photo Capture` / `\ue61cJPEG/HEIF Switch` / *(DCI 4K 禁用提示)* | `照片捕获` / `\ue61cJPEG/HEIF切换` / *("XAVC S-I DCI 4K"不可执行)* | `照片攝取` / `\ue61cJPEG/HEIF切換` / *(無法對"XAVC S-I DCI 4K"執行)* | `動画から静止画作成` / `\ue61cJPEG/HEIF切換` / *(XAVC S-I DCI 4Kでは実行できません)* | **活跃**（`8.3M/2.1M`；抗 Camera Reset） |
| `base 0xe3b7..0xe3b9` / `_f 0x7468` | `View Mode` / `Date View` / `Folder View(Still)` / `\ue08bMovie View` | `观看模式` / `日期视窗` / `文件夹视窗(静态影像)` / `\ue08b动态影像视窗` | `觀看模式` / `日期檢視` / `資料夾檢視(靜態影像)` / `\ue08b影片檢視` | `ビューモード` / `日付ビュー` / `ﾌｫﾙﾀﾞｰﾋﾞｭｰ（静止画）` / `\ue08b動画ビュー` | **活跃**（实机 3 项；`0xe3ba/0xe3bb` **休眠**） |
| `_f 0x684f` / `0x66c1` / `_g 0x634a` | `Rating` / `Rating Set(Custom Key)` / `Added a Rating(\ue5c6).` | `分级` / `分级设置(自定义键)` / `已添加分级(\ue5c6)。` | `等級` / `等級設定（自訂鍵）` / `已新增等級(\ue5c6)。` | `レーティング` / `ﾚｰﾃｨﾝｸﾞ設定(ｶｽﾀﾑｷｰ)` / `レーティング(\ue5c6)を追加しました` | **活跃**（1..5 星；抗 Camera Reset） |
| `_f 0x6cb2` / `0x7065` / `0x79d5` / `_g 0x64be` | `\ue660Network Streaming` / `Output Img. Quality Set` / `Movie Rec During Streaming` / *(Creators' App 提示)* | `\ue660网络流式传输` / `输出影像质量设置` / `流式传输动态影像录制` / *(通过Creators' App开始设置)* | `\ue660網路串流傳輸` / `輸出影像品質設定` / `串流傳輸動態影像錄製` / *(從Creators' App開始設定)* | `\ue660ﾈｯﾄﾜｰｸｽﾄﾘｰﾐﾝｸﾞ` / `出力画質設定` / `ｽﾄﾘｰﾐﾝｸﾞ時の動画記録` / *(Creators' Appから設定開始)* | **活跃**（`RTMP/RTMPS/SRT Caller`） |
| `_f 0x7399` / `0x6216` / `_g 0x63f7` | `\ue660USB Streaming` / `Live Stream(USB Streaming)` / `USB Streaming` | `\ue660USB流式传输` / `实时流式传输(USB流式传输)` / `USB流式传输` | `\ue660USB串流傳輸` / `即時串流傳輸(USB串流傳輸)` / `USB串流傳輸` | `\ue660USBストリーミング` / `ﾗｲﾌﾞｽﾄﾘｰﾐﾝｸﾞ (USBｽﾄﾘｰﾐﾝｸﾞ)` / `USBストリーミング` | **休眠**（FX3 无 UVC；仅 4 种 USB 模式） |
| `fx6_2 0x43be/0x4b56/0x4759/0x4fdb` | `Shutter Mode` / `ECS` / `SteadyShot: Active` / `Set Clip Flag` | `快门模式` / `ECS` / `SteadyShot:动态` / `设置片段旗标` | `快門模式` / `ECS` / `SteadyShot:動態` / `設定短片旗標` | `シャッターモード` / `ECS` / `手ブレ補正: アクティブ` / `クリップフラグ設定` | **FX6 活跃**（`0x51e6 QoS Streaming` **休眠**） |

---

## 6. 仓内安全守卫（`fx3-safety`）交叉对照与精密勘误登记

对照任务要求核查的安全守卫（[`G65`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py)、[`G67/G68`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py)、[`G70`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py)、[`G81`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py)、[`G86`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py)、[`G121/G122`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)、[`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)、[`G133/G134`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) 与 [`G150`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py)）：

1. **已准确锚定并延续的不变量（`实测事实`）**：
   - **`G65` & `G150`**：精准拦截 `USB Streaming`（UVC/UAC）误暴露，强制 `[USB Connection Mode]` 仅 4 项（`Sel. When Connect` / `MSC` / `MTP` / `Remote Shooting`）；
   - **`G67/G68` & `G70`**：精准锚定 `BK4` `0x01120024`（`Speed`）与 `0x01120028`（`Angle`）双槽隔离、`5.6°..360°` + `2F..64F` 档位、`[Exposure step]` 无关性，以及 FX6 `Clip Flag` (`OK/NG/KEEP`) vs 休眠 `RTMP/SRT` 边界；
   - **`G86`**：准确验证 `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO` -> `Manual`) 与 `[Auto Slow Shutter]` (`-> On`) 随 `[Camera Settings Reset]` 复位；
   - **`G121/G122` & `G126`**：准确建模 `[Photo Capture]` `8.3M/2.1M`、对 `XAVC S-I DCI 4K` 的硬锁、Playback `[JPEG/HEIF Switch]` 抗 `[Camera Settings Reset]` 例外、`[Rating]` `1..5` 星与 `Slot 1 EROFS=30` 防火墙；
   - **`G133/G134`**：准确覆盖 `47` 档 `[Focal Length]`（`8..1000mm`）、休眠 `Dynamic active` 拦截、`De-Squeeze != Off` 禁用 `Active`、以及 `[Network Streaming]`（`RTMP/RTMPS/SRT`、`59.94p/50p/29.97p/25p`、禁用 `23.98p/24p/120p`、峰值 `38 Mbps`、`[Airplane Mode] = On` 射频零发射与 `[Movie Rec During Streaming]` `Slot 1` 防火墙）。

2. **显式发现的既有守卫缺口与后续微调建议（`实测事实` + `推断`）**：
   - **勘误 #1（`G86` 补充 `[Exposure Ctrl Type]` 抗 Reset 规则）**：[`G86`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1550-L1606) 的 `resolve_fx3_flexible_exp_reset_split()` 仅对 `Av`/`Tv`/`ISO` 与 `Auto Slow Shutter` 做复位断言；建议后续补入 **`[Exposure Ctrl Type]` 本身在 `[Camera Settings Reset]` 后保持原值（`Not available`），仅 `[Initialize]` 归位 `Flexible Exp. Mode`**。
   - **勘误 #2（`G81` `200mm` 软提示与 Ver. 7.02 `ilc/2210` 对齐）**：[`G81`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L212) 仍保留早期 Ver. 1 手册的 `200mm` 提示；建议降级为历史兼容性备注而非 Ver. 7.02 硬阻断。
   - **缺口 #3（`G126` 补建 `[View Mode]` 3 项枚举与 `Movie View` 守卫）**：[`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 当前无 `View Mode` 校验；建议补充实机 3 项（`Date View` / `Folder View(Still)` / `Movie View`）并拦截休眠 `AVCHD View` / `Folder View(MP4)`。
   - **缺口 #4（`G134` 显式锚定 `SRT Caller` 单向性）**：建议在 [`G134`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h453-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py#L441-L450) 显式拒绝将 FX3 宣称为支持机内 `SRT Listener` 入站模式，同时在 `FX6` 对比字段中将 `SteadyShot` 光学 OSS 修正为支持 `Active / Standard / Off`（零机身 IBIS）。

---

## 7. `78/78 Waves` 收官状态与单文件所有权声明

- **Wave 78 收官结论**：至此 **Global Sony Real-Hardware Empirical Intelligence Waves (`1/78 .. 78/78`)** 全系列实机深度审计已全部闭环，覆盖 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的全量菜单拓扑、ELF/UXC 休眠遗产剥离、`Reset/Initialize` 持久性真值、卡速/格式/帧率硬互斥、`Catalyst`/`Creators' App`/`SRT`/`RTMP` 链路及 `Tier-0 Slot 1 EROFS=30` 防火墙边界。
- **严格单文件所有权**：本波次（`H453` / `Wave 78`）仅创建并提交 `reports/2026-11-18-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/README.md`，未修改任何 Python 源代码、测试、安全守卫、`Makefile` 或其他报告。
- **取证与清理合规**：全部本地二进制检索严格经 `os.O_RDONLY` 只读完成（`raw_firmware_bytes_leaked = 0`），零临时脚本及 `.pyc` 残留，已通过 `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 全量绿灯校验。
