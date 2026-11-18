# 全球 Sony 实机情报 Wave 63（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[HDMI Output Settings]` / `16-bit RAW Output` / `Rec. Media dur HDMI Output`、`[De-Squeeze Display]` 激活倍率与 4+ 互斥、`[REC Lamp]` 三灯 / `[Emphasized REC Display]` / `[Remain Shoot Display]` / `[Auto Review]`，以及 `[Anti-Flicker Shoot.]` vs 休眠 `[Var. Shutter]` + `[APS-C S35 Shooting]` 4K 锁死与 Reset 勘误）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *HDMI Output Settings (movie) / Outputting RAW movies to an external RAW recorder / HDMI Info. Display / De-Squeeze Display / REC Lamp / Emphasized REC Display / Remain Shoot Display / Auto Review / Anti-flicker Shoot. / APS-C S35 (Super 35mm) Shooting / Image Quality Settings / Movie Settings / S&Q Settings / Proxy Settings / List of default setting values*）
  - Sony `ILME-FX3` `Ver. 2.00 / 3.00 / 6.00 / 7.00 / 7.02` 官方固件发布说明
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0）与 `ILME-FX6` `Ver. 4.00 / 5.00 / 6.00 / 6.01` 固件说明
  - 并严格对照 `os.O_RDONLY` 本地 donor 二进制实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so` 及 `FX6 string_english.uxc` / `_2.uxc`；并交叉核验 [Wave 27](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave27-desqueeze-165x-4locks-external-focusmap-150fps-simult-autoswitch-shocklesswb-intel/README.md)、[Wave 28](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)、[Wave 29](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave29-file-settings-sdhc-shotmark-tc-regenerate-slot1-reclamp-coupled-tally-intel/README.md)、[Wave 35](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave35-emphasized-rec-grid-hdmi-split-touch-op-reset-persist-sunny-weather-intel/README.md)、[Wave 37](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave37-framing-settings-crop-full-usb-power-battery-lun-antiflicker-novarshutter-intel/README.md)、[Wave 40](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave40-milestone-diff-set-still-mv-8items-shutter-angle-custom-key-dial-remain-shoot-intel/README.md)、[Wave 41](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md) 与 [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md)）。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方 Help Guide 条目）与 **`推断`**（Tier-0 `Slot 1` 保险库边界与台架防护推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[HDMI Output Settings]`、`4264×2408` 16-bit `RAW Output` 与 `Rec. Media dur HDMI Output` 边界）**：
   - **实测事实（菜单树与 `Ver. 2.00+` 演进）**：`ILME-FX3 Ver. 7.02` 位于 `Setup -> [External Output] -> [HDMI Output Settings]`，整组设置**抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 复位）。共包含 **8 个活跃子项**：`[Rec. Media dur HDMI Output]`（`On` 默认/`Off(HDMI Only)`）、`[Output Resolution]`（`Auto` 默认/`2160p`/`1080p`/`1080i`）、`[4K Output Set.(HDMI Only)]`（仅 10-bit：`59.94p 10bit/50p 10bit` 默认、`29.97p`、`25p`、`23.98p`、`24.00p`）、`[RAW Output]`（`Off` 默认/`On`，`4264×2408` 16-bit 线性）、`[RAW Output Setting]`（`59.94p/50p` 默认/`29.97p`/`25p`/`23.98p`/`24.00p`）、`[Time Code Output]`（`Off` 默认/`On`）、`[REC Control]`（`Off` 默认/`On`，硬前置 `[Time Code Output] = On`）与 `[4ch Audio Output]`（`CH1/CH2` 默认/`CH3/CH4`）。注意：**`[Color Gamut for RAW Output]`（`BKID_APP_setting_color_gamut_for_raw_out`、`_f 0x6bdc`）已从 `Ver. 2.00..7.02`（`ilc/2210`）独立菜单移除**，因开启 HDMI RAW 已强制要求 `[Log Shooting] != Off`，色域改由 `[Log Shooting Setting] -> [Color Gamut]` 统一接管。
   - **实测事实 + 推断（`Slot 1` 保险库与并录矩阵）**：当 `[RAW Output] = On` 且 `[Rec. Media dur HDMI Output] = On` 时，FX3 无法机内录制 RAW，但**机内 XAVC 主码流与 Proxy（符合帧率条件时）仍正常写入 `[Recording Media]`**（`FX3 appFw.so` `VAL_HAITA_setting_rec_control_..._RAW_CONNECTED_REC_MEDIA_DURING_HDMI_OUTPUT_ON_RAW_OUTPUT_ON_MEDIA_MOUNT_STATE_SLOT1_MOUNT_...` 实证），同时强锁 `S-Log3`、禁用 `[Active]` 防抖并暂时关闭 `[HDMI Info. Display]`；一旦切换 `[Rec. Media dur HDMI Output] = Off(HDMI Only)`，**机内 Slot 1/2 主录与 Proxy 全部零写入**（计数不递增），且 `24.00p` 进出切换会触发系统重启（`_g 0x6034`/`0x61d3`/`0x63b6`）。对比 **`ILME-FX6 Ver. 6.01`** 支持 `12G-SDI RAW`（`4096×2160` / `3840×2160 "C"`，此时 HDMI 被降限至 `<= 1080p`）与 `RAW(HDMI)`（`4240×2392`，支持 `59.94..23.98Hz`、不含 `24Hz`），并在 `Project > SDI/HDMI Rec Control` 中显式分离无卡遥控 `SDI/HDMI Remote I/F` 与有卡同步 `Parallel Rec`。

2. **子系统 2（`[De-Squeeze Display]`：Ver. 7.00/7.02 激活 `1.5x` / `1.6x(1.65x)` vs 缺失 `1.8x`）**：
   - **实测事实（路径、版本与真实倍率）**：`[De-Squeeze Display]` 位于 **`Setup -> [Display Option] -> [De-Squeeze Display]`**（非 `Shooting` 页），**抗 `[Camera Settings Reset]`**（默认 `Off`）。**`Ver. 3.00` 引入 `Off` / `1.3x` / `2.0x`；`Ver. 7.00`（延续至 `Ver. 7.02`）正式激活 `1.5x` 与 `1.6x`**（实际执行 **`1.65x`** 水平拉伸还原 `2.39:1`：`_f 0x7d09` `'1.6x'`、`_f 0x7d0c` `'Set when an anamorphic lens with 1.65x compression is equipped.'`、`EXTERN_VAL_DE_SQUEEZE_DISP_1_65X`），而 **`1.8x` 在 `FX3 appFw.so`、UXC 与 `ilc/2210` 中为 `0` 命中（完全缺失）**。
   - **实测事实（4 项强锁与 6 类旁路）**：非 `Off` 时硬件强锁 `[Focus Mode] = Manual Focus`、`[Focus Area] = Wide`、`[SteadyShot] = Off`、`[Face Priority in Multi Metering] = Off`；仅在 Movie/S&Q 生效且**永不反挤压机内录制文件**；在 Still 模式按下 `MOVIE` 键录影、`[Remote Shooting]`、`[Photo Capture]`、`[Log Shooting] = Off`、`[RAW Output] = On`（HDMI）及 `[Rec. Media dur HDMI Output] = Off(HDMI Only)`（HDMI）下**自动旁路不反挤压**；`ilc/2210` 与 `FX3 appFw.so` 均证实 `[De-Squeeze Display]` 与 `[Focus Magnifier]` / `[Bright Monitoring]` 之间**无互锁禁用规则**。对比 **`ILME-FX6 Ver. 6.01`** 提供 `Monitoring > De-Squeeze > Ratio (HDMI/VF)`（`Off(1.0x)` / `1.3x` / `1.5x` [*Ver. 5.00 新增*] / `2.0x`，无 `1.6x`），仅作用于 **VF 与 HDMI**（**从不反挤压 SDI**），同样禁用 AF 与 Spot Focus。

3. **子系统 3（`[REC Lamp]` 三灯物理联动、`[Emphasized REC Display]`、`[Remain Shoot Display]` 与 Still `[Auto Review]`）**：
   - **实测事实（纠偏命名：`[REC Lamp]` 而非 `[Tally Light]`）**：`ILME-FX3 Ver. 7.02` 不存在 `[Tally Light]` 菜单（`TALLY` 在 `FX3 appFw.so` 门控与 `ilc/2210` 均无菜单暴露），官方项为 **`Setup -> [Setup Option] -> [REC Lamp]`**（抗 `[Camera Settings Reset]`）。机身虽有 **3 颗物理指示灯**（前侧灯、后侧灯、顶部透明 `REC` 按键环），但后灯与顶部 `REC` 键硬件联动，故菜单仅暴露 **`All On`（默认）**、**`Only Front Off`**（仅关前灯，保留后灯+顶键）、**`All Off`**（全关）三态（休眠 UXC `_f 0x743e` / `REC_LAMP_LIGHT_UP_ONLY_ONE` 未对 FX3 暴露），且**独立于 `[Silent Mode]`**（静音模式不自动关闭录制灯）。对比 **`ILME-FX6 Ver. 6.01`** 在 `Technical > Tally` 提供完全独立的 `Front Tally Lamp`、`Rear Tally Lamp`、`Tally Control`、`Tally Lamp Brightness` 与 `G/Y Tally Lamp`，并在 `Monitoring > Display On/Off > Tally` 提供 VF/SDI/HDMI OSD 指示。
   - **实测事实（三项录制/检视显示边界）**：`[Emphasized REC Display]`（`Shooting -> [Shooting Display]`，Movie/S&Q 红框，默认 `On`，**可 Reset**，仅在 `[HDMI Info. Display] = On` 且非 `RAW`/`HDMI Only` 时随信号输出 HDMI）；`[Remain Shoot Display]`（`Setup -> [Display Option]`，**在 FX3 上完全活跃**，Still 连拍余量指示：`Not Displayed` 默认/`Always Display`/`Shoot-Only Display`，**抗 Reset**）；`[Auto Review]`（`Setup -> [Display Option]`，**仅 Still**：`Off` 默认/`2 Sec`/`5 Sec`/`10 Sec`，间隔拍摄禁用，**抗 Reset**）。

4. **子系统 4（`[Anti-Flicker Shoot.]` vs 休眠 `[Var. Shutter]`，以及 `[APS-C S35 Shooting]` 4K/DCI 4K 锁死与 Wave 42 Reset 勘误）**：
   - **实测事实（休眠 `[Var. Shutter]` 铁证 vs FX6 `ECS`）**：`FX3 appFw.so` 与 `_f`/`_g.uxc` 虽包含共享 BIONZ XR 代码库的 `BKID_APP_setting_high_res_ss`、`launch_high_res_ss_set_{movie,still}`、`_f 0x6831` `'Var. Shutter'`、`_f 0x68e7` `'Anti-flicker Set.'` 与 `_g 0x60a8` `'Anti-flicker Tv Scan'`，但 `TYPE_MENU_ITEM_*HIGH_RES*` 与 `ilc/2210` 实机菜单均确认 **`[Var. Shutter]`（高频 LED 防闪烁小数快门）在 `ILME-FX3 Ver. 7.02` 上完全休眠未开放**；FX3 仅暴露 Still 机械快门专用的 `Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]`（`Off` 默认/`On`，**可 Reset**，仅测 100/120Hz，电子快门与 `[Silent Mode] = On` 下禁用）。对比 **`ILME-FX6 Ver. 6.01`** 提供广播级 **`ECS`（`Extended Clear Scan`）**，支持 **`23.99`–`8000 Hz`**（`FX6 ns1 0x26f2..0x26f4`）小数频率精调并与 `Shutter Mode`（`Speed` / `Angle` / `ECS`）平级切换。
   - **实测事实（CRITICAL 对 [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 的 Reset 勘误）**：`Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]`（`Auto` 默认/`On`/`Off`）在官方 `ilc/2210` *List of default setting values* 中明确标记 **`Resettable using [Camera Settings Reset]: Not available`**（**修正 Wave 42 第 1.1 节误写的“Resettable by `[Camera Settings Reset]`”，该项抗 Reset，须 `[Initialize]` 才复位**）。开启 `APS-C S35 = On` 时，由于 `12.1 MP`（`4240×2832`）全画幅传感器在 S35 窗口不足 4K 像素，**所有 4K 规格（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、`XAVC S-I DCI 4K`、`S&Q 4K` 与 `[4K Output Set.(HDMI Only)]`）全部锁死禁用**，仅剩 **`HD (1920×1080)`**（最高 `120p`；`FX3 appFw.so` `VAL_HAITA_..._apsc_restriction_imager_frame_rate_in_file_format_fhd_..._240FPS_..._OVER_240_200` 显示 `200/240fps` S&Q 在 FHD 帧率限制矩阵中被单独门控）；Still 静态照片下禁用 `L: 12M`（`4240×2832`）并降格为 **`M: 5.1M`（`2768×1848` 3:2 / `4.3M` 16:9，而非 4.2M）**。对比 **`ILME-FX6 Ver. 6.01`** 在 `Imager Scan Mode = S35` 下同样锁定 `1920×1080`（`1..120 fps`）并禁用 RAW，但全画幅 `4K` 下可通过 `Clear Image Zoom`（4K `1.5x` / HD `2.0x`）裁切适配 S35 镜头（代价是禁用 Face/Eye AF 与 RAW）。

---

## 1. 子系统 1：`[HDMI Output Settings]`、`4264×2408` 16-bit `RAW Output` 与 `Rec. Media dur HDMI Output` 边界

### 1.1 `ILME-FX3 Ver. 7.02` 全量菜单真值表与 Ver. 2.00+ 移除项实证（`实测事实`）

> [!IMPORTANT]
> **Ver. 1.x -> Ver. 2.00+ `[Color Gamut for RAW Output]` 演进实证（`ilc/2210` + `FX3 appFw.so`）**：
> 在 `FX3 appFw.so` 中可检索到 `BKID_APP_setting_color_gamut_for_raw_out` 与 `PRM_HAITA_setting_color_gamut_for_raw_out_...`，`_f.uxc` 亦保留 `0x6bdc` `'Color Gamut for RAW Output'`；但自 **`Ver. 2.00` 起至 `Ver. 7.02`（`ilc/2210`）**，Sony 强制要求输出 HDMI RAW 时必须开启 `[Log Shooting]`，因此将独立子项 `[Color Gamut for RAW Output]` 从 `[HDMI Output Settings]` 中移除，统一由 `Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Color Gamut]` 控制 RAW 输出色域。

| 菜单路径（`Setup -> [External Output] -> [HDMI Output Settings]`） | `FX3 Ver. 7.02` 真实选项、规格与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Rec. Media dur HDMI Output]`** | **`On`**（**默认**，机内卡同步录制+HDMI 输出） / **`Off(HDMI Only)`**（完全旁路机内卡；`S&Q` 下锁死 `On`） | **Not available**<br>*(抗 Reset，须 `[Initialize]`)* | `_f 0x6144` / `0x6573`；`BKID_APP_setting_rec_media_during_hdmi_output` |
| **`[Output Resolution]`** | **`Auto`**（**默认**） / `2160p` / `1080p` / `1080i`；仅当 `Rec. Media dur HDMI Output = On` 且 `RAW Output = Off` 时生效；**`Log Shooting != Off` 或 `PPLUT1..4` 时强制降频 `1080p`** | **Not available** | `_f 0x79ac` / `0x7839` / `base 0xe1d6, 0xe1d7`；`BKID_APP_setting_hdmi_resolution` |
| **`[4K Output Set.(HDMI Only)]`** | **`59.94p 10bit / 50p 10bit`**（**默认**）、`29.97p 10bit`、`25p 10bit`、`23.98p 10bit`、`24.00p 10bit`；**FX3 仅暴露 10-bit**（`_f 0x748a` `'24.00p 8bit'` 为跨机型休眠 UXC）；切入/切出 `24.00p` 触发**强制重启** | **Not available** | `_f 0x74d7` / `0x7195` / `0x6fc7` / `0x74e2` / `0x7a74` / `0x6842` / `0x731d`；`BKID_APP_setting_hdmi_4k_output_setting`；`VAL_..._HDMI_ONLY_4K_OUTPUT_SETTING_{60P,50P,30P,25P,24P,24_00P}_10BIT` |
| **`[RAW Output]`** | **`Off`**（**默认**） / **`On`**（通过 HDMI Type-A 输出 **`4264×2408`** 16-bit 线性 RAW；须 Premium High Speed HDMI 线；须 Movie 模式且 `[Log Shooting] != Off`；`S&Q` 下锁死 `Off`） | **Not available** | `_f 0x6e97`；`BKID_APP_setting_raw_output`；`FEATURE_MANAGER_menu_item_RAW_OUTPUT_ON_CONNECT_WITH_RAW_COMPATIBLE_DEVICE_CONNECTED_EXPOSURE_MODE_MOVIE_ALCIN_UUD` |
| **`[RAW Output Setting]`** | **`59.94p / 50p`**（**默认**）、`29.97p`、`25p`、`23.98p`、`24.00p`（选定后控制 RAW 输出帧率；仅 `RAW Output = On` 时生效） | **Not available** | `_f 0x78fd`；`BKID_APP_setting_raw_output_frame_rate`；`PRM_HAITA_raw_output_framerate_restriction` |
| **`[Color Gamut for RAW Output]`**<br>*(Ver. 1.x 历史项)* | **Ver. 2.00..7.02 已并入 `[Log Shooting Setting] -> [Color Gamut]`**，不再作为 `[HDMI Output Settings]` 独立菜单项 | — | `_f 0x6bdc` `'Color Gamut for RAW Output'`；`BKID_APP_setting_color_gamut_for_raw_out`（Ver. 1.x 遗留） |
| **`[Time Code Output]`** | **`Off`**（**默认**） / **`On`**（通过 HDMI 数字包嵌入时间码；`S&Q` 不可用；**`[REC Control]` 的硬性前置**） | **Not available** | `_f 0x72af`；`BKID_APP_setting_hdmi_tc_output` |
| **`[REC Control]`** | **`Off`**（**默认**） / **`On`**（向兼容外录机发送 `STBY`/`REC` 控制信号；须 `[Time Code Output] = On`） | **Not available** | `_f 0x76e1` / `0x6657`；`BKID_APP_setting_rec_control`；`PRM_HAITA_setting_rec_control_...` |
| **`[4ch Audio Output]`** | **`CH1/CH2`**（**默认**） / **`CH3/CH4`**（HDMI 物理协议仅载 2ch LPCM，选组输出） | **Not available** | `_f 0x6aa0` / `_f 0x713b` / `0x6bf6`；`BKID_APP_setting_4ch_output_ch` |

### 1.2 `[Rec. Media dur HDMI Output]`、`RAW Output = On` 耦合矩阵与 Tier-0 `Slot 1` 边界（`实测事实` + `推断`）

1. **`[RAW Output] = On` × `[Rec. Media dur HDMI Output]` 真实行为矩阵（`实测事实`）**：
   - **`[RAW Output] = On` + `[Rec. Media dur HDMI Output] = On`**：FX3 **不能把 RAW 写入存储卡**，但**机内 XAVC（含 `[Simult. Recording]` 与符合帧率条件的 `[Proxy Recording]`）仍正常写入 `[Recording Media]`**（`FX3 appFw.so` `VAL_HAITA_setting_rec_control_..._RAW_CONNECTED_REC_MEDIA_DURING_HDMI_OUTPUT_ON_RAW_OUTPUT_ON_MEDIA_MOUNT_STATE_SLOT1_MOUNT_MEDIA_MOUNT_STATE_SLOT2_MOUNT_EXPOSURE_MODE_MOVIE` 与 `ilc/2210` 相互印证）。此时机内伽马锁死 `S-Log3`、`[Active]` 防抖禁用、`[HDMI Info. Display]` 暂时强制 `Off`（不污染外录 RAW/Clean HDMI）、HDMI 不反挤压，且应优先使用机身 `REC` 键触发录制。
   - **`[RAW Output] = On` + `[Rec. Media dur HDMI Output] = Off(HDMI Only)`**：**完全绕过机内卡写入**（主录与 Proxy 均不落盘、余量/时长计数器不走），HDMI 输出 `4264×2408` 16-bit 线性 RAW；配合 `[Time Code Output] = On` + `[REC Control] = On` 驱动外录机。
   - **`[RAW Output] = Off` + `[Rec. Media dur HDMI Output] = Off(HDMI Only)`**：机内卡零写入，激活 `[4K Output Set.(HDMI Only)]` 10-bit 4K 输出（绕过 `[Log Shooting]` / `PPLUT1..4` 下机内录制的 `1080p` HDMI 降频陷阱，详见 [Wave 28](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)），同时暂时关闭 `[HDMI Info. Display]` 与 HDMI 反挤压。
   - **`[HDMI Info. Display] = On` 反向影响（`RAW = Off` 且 `Rec. Media = On` 时）**：所有 OSD 与 `[Emphasized REC Display]` 红框转移到外接 HDMI 监视器输出，并**强制熄灭 FX3 机身自带 LCD 屏幕**。
2. **Tier-0 `Slot 1` 只读保险库隔离推论（`推断`）**：
   - 在台架上必须严格区分 `Rec. Media dur HDMI Output = On` 与 `Off(HDMI Only)`：当 `[Rec. Media dur HDMI Output] = Off(HDMI Only)` 时，卡槽写入链路被主动旁路；而一旦其为 `On`（即使同时开了 `RAW Output = On`），任何 `REC` 触发都会经 `[Recording Media]`（含 `Slot 1` 或 `Simult. Recording`）尝试写入 `CLIP/`、`SUB/` 与 `AVF_INFO`。因此 Tier-0 只读 `Slot 1` 保险库保护策略在 `Rec. Media dur HDMI Output = On` 路径下必须维持 fail-closed `EROFS (errno 30)`，且不得将 `[HDMI Info. Display] = On` 误作 Clean Feed。

### 1.3 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 外录与 RAW 架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **RAW 输出接口与分辨率** | **仅 HDMI Type-A**：**`4264×2408`** 16-bit 线性 RAW（`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p`） | **双路独立机制**：① **12G-SDI `RAW` / `RAW & XAVC-I`**（`4096×2160` 或 `3840×2160` 裁切 `"C"`，16-bit，此时 **HDMI 强制降限 `<= 1080p`**）；② **`RAW(HDMI)` / `RAW(HDMI) & XAVC-I`**（`4240×2392`，支持 `59.94/50/29.97/25/23.98 Hz`，**不含 `24Hz`**，`FX6 ns1 0x2499/0x249b`） |
| **日志/EI 强制前置** | `[RAW Output] = On` 须 `[Log Shooting] != Off`，伽马锁 `S-Log3` | `Shooting Mode = Cine EI` / `Cine EI Quick`（RAW 输出锁定 `S-Log3` 基线与 EI 元数据） |
| **外录遥控与无卡状态机** | `[Rec. Media dur HDMI Output]`（`On` / `Off(HDMI Only)`）+ `[REC Control]`（硬前置 `[Time Code Output] = On`） | `Project > SDI/HDMI Rec Control > Setting`：**`Off`** / **`SDI/HDMI Remote I/F`**（**无卡时**仅外录触发，非帧精确同步）/ **`Parallel Rec`**（**插卡时**与机内录制同步触发）；`FX6 ns2 0x428d/0x4d77` |
| **机内同录能力** | `RAW = On` + `Rec. Media = On` 时同录机内 XAVC（+ Proxy，若满足帧率） | `RAW & XAVC-I`（SDI RAW）或 `RAW(HDMI) & XAVC-I`（HDMI RAW）下可同录 `3840×2160P` 或 `1920×1080P` XAVC-I |
| **4ch 音频透传差异** | HDMI 仅载 2ch（`[4ch Audio Output]` 选 `CH1/CH2` 或 `CH3/CH4`） | **12G-SDI 支持 4ch 24-bit 48kHz LPCM** 同步嵌入；HDMI 同样限 2ch |

---

## 2. 子系统 2：`[De-Squeeze Display]` 版本演进、实机倍率（`1.3x` / `1.5x` / `1.6x[1.65x]` / `2.0x` vs 缺失 `1.8x`）与 4+ 互斥矩阵

### 2.1 `ILME-FX3 Ver. 7.02` 路径、版本历史、倍率铁证与 Reset 边界（`实测事实`）

1. **精确菜单路径与 Reset 边界（`实测事实`）**：
   - 路径：`MENU -> (Setup) -> [Display Option] -> [De-Squeeze Display]`（`_f 0x7aba`、`_f 0x6253`、`_f 0x7d0a`、`_f 0x7d09`、`_f 0x674c`、`BKID_APP_setting_de_squeeze_disp`）。
   - 默认值：**`Off`**；位于 `(Setup)` 树下，**抗 `[Camera Settings Reset]`**（`Not available`，仅 `[Initialize]` 复位）。
2. **版本演进与 `1.5x` / `1.6x(1.65x)` / `1.8x` 实证核验（`实测事实`）**：
   - **`Ver. 3.00`**：首次引入 `[De-Squeeze Display]`，仅含 `Off`、`1.3x`、`2.0x`。
   - **`Ver. 7.00`（延续至 `Ver. 7.02`）**：官方新增 **`1.5x`** 与 **`1.6x`**，共 **5 档活跃状态**。其中菜单标签显示 **`1.6x`**（`_f 0x7d09`），但底层说明（`_f 0x7d0c`: `'Set when an anamorphic lens with 1.65x compression is equipped.'`）、`ilc/2210` 指南与 ELF 枚举（`VAL_DE_SQUEEZE_DISP_1_65X` / `VAL_HAITA_..._1_6X`）一致证实其**实际执行 `1.65x` 水平反挤压拉伸**以还原 `2.39:1` CinemaScope 监看比例。
   - **`1.8x` 核实完全缺失**：在 `FX3 appFw.so`、`FX3` 四语 UXC 全量包及 `ilc/2210` 文档中均 **`0` 命中 `1.8x`**，Ver. 7.02 实机绝不支持 `1.8x` 挡位。

### 2.2 4 项硬件强锁、6 类不反挤压旁路与 `Focus Magnifier` / `Bright Monitoring` 关系（`实测事实`）

| 约束类别 | 受控子系统 / 触发条件 | `ILME-FX3 Ver. 7.02` 真实行为与底层依据（`实测事实`） |
| :--- | :--- | :--- |
| **4 项硬件强锁**<br>*(当 `[De-Squeeze Display] != Off`)* | `[Focus Mode]`<br>`[Focus Area]`<br>`[SteadyShot]`<br>`[Face Priority in Multi Metering]` | 1. **`[Focus Mode]` 锁死 `[Manual Focus]`**（禁用全部 AF）；<br>2. **`[Focus Area]` 锁死 `[Wide]`**；<br>3. **`[SteadyShot]` 锁死 `[Off]`**（关闭机身防抖避免变形镜头拉伸畸变/果冻撕裂）；<br>4. **`[Face Priority in Multi Metering]` 锁死 `[Off]`**。 |
| **绝对隔离原则** | 机内录制文件 / 截帧 | **绝不改变写入存储卡的视频编码流**（机内永远保存原始挤压画面，仅做实时屏幕与合规 HDMI 监看反挤压）。 |
| **6 类旁路（不反挤压）** | `ilc/2210` 明文例外条件 | ① **`[Log Shooting] = Off`** 时（包括非 Log 普通图像配置）；<br>② **`[RAW Output] = On`** 时的 **HDMI 输出**；<br>③ **`[Rec. Media dur HDMI Output] = Off(HDMI Only)`** 时的 **HDMI 输出**；<br>④ 在 **Still 模式按 `MOVIE` 键**录制视频时；<br>⑤ **`[Remote Shooting]`** 远程监控画面；<br>⑥ 使用 **`[Photo Capture]`** 从视频提取静态照片时。 |
| **模式适用与放大/高亮** | Still vs Movie/S&Q、Focus Mag、Bright Mon | 仅在 **Movie 与 S&Q** 拍摄/回放时可用（Still 菜单置灰）；`ilc/2210` 与 `FX3 appFw.so` `HAITA` 均证实 **`[De-Squeeze Display]` 与 `[Focus Magnifier]` / `[Bright Monitoring]` 之间无互锁禁用**（反挤压后仍可按 `[Focus Magnifier]` `x4.0` 检焦，但注意 `[Focus Magnifier]` 激活时会隐藏 `[Marker Display]` 并禁用 `[Bright Monitoring]` 快捷键切换，见 [Wave 28](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)）。 |

### 2.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 反挤压架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so` + UXC) |
| :--- | :--- | :--- |
| **菜单路径与倍率** | `Setup -> [Display Option] -> [De-Squeeze Display]`：<br>`Off` / `1.3x` / `1.5x` / `1.6x(1.65x)` / `2.0x` | `Monitoring > De-Squeeze > Ratio (HDMI/VF)`：<br>`Off(1.0x)` / `1.3x` / **`1.5x`** *(Ver. 5.00 新增，`FX6 ns1 0x2a4f/0x32e4`)* / `2.0x`（**FX6 实机无 `1.6x/1.65x`**，UXC `0x301a/0x33c1` 与 `SDI (X-OCN) De-Squeeze` `0x2801` 属 CineAlta/BURANO 共享休眠字串） |
| **输出通路规则** | 机身 LCD + 合规 HDMI（`Log != Off` 且非 `RAW`/`HDMI Only`） | **仅作用于 VF（机内 LCD）与 HDMI**（`FX6 appFw.so` `BKID_APP_EXTERN_DE_SQUEEZE_LCD_MONITOR`、`de_squeeze_disp_hdmi_onoff`），**永不作用于 SDI**；且 HDMI 在输出 **RAW 或 SD 信号**时不反挤压 |
| **对焦与防抖锁定** | 强锁 MF + Wide + `SteadyShot = Off` + 人脸测光关 | 同样**禁用 Autofocus 与 Spot Focus**（FX6 无 IBIS 故不涉及 SteadyShot） |

---

## 3. 子系统 3：`[REC Lamp]`（非 `[Tally Light]`）三灯物理联动、`[Emphasized REC Display]`、`[Remain Shoot Display]` 与 Still `[Auto Review]`

### 3.1 `ILME-FX3 Ver. 7.02` 真值表、物理三灯拓扑与 Reset 边界（`实测事实`）

> [!NOTE]
> **菜单命名纠偏（`ilc/2210` + `FX3 appFw.so` 实证）**：
> `ILME-FX3 Ver. 7.02` 在机身菜单与官方文档中**从未使用 `[Tally Light]` 命名**（`TALLY` 在 `FX3 appFw.so` `BKID_APP_*` 中为 **`0` 命中**）；其正式名称为 **`[REC Lamp]`**，位于 `Setup -> [Setup Option] -> [REC Lamp]`（`_f 0x6e62`、`BKID_APP_setting_rec_lamp`）。

| 菜单路径 / 项（`ilc/2210` Ver. 7.02） | 真实选项、默认值与硬件交互 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[REC Lamp]`**<br>(`Setup -> Setup Option`) | **`All On`**（**默认**，前灯+后灯+顶部 `REC` 键全亮）<br>**`Only Front Off`**（仅关前灯防反光，**保持后灯与顶部 `REC` 键点亮**）<br>**`All Off`**（前/后/顶部 3 灯全部熄灭） | **Not available**<br>*(抗 Reset，须 `[Initialize]`)* | `_f 0x6e62` / `0x6337` / `0x727c` / `0x6d8c`；`BKID_APP_setting_rec_lamp`；`REC_LAMP_{ALL_LIGHTS_UP,ONLY_FRONT_OFF,ALL_LIGHTS_OUT}`；**注：`REC_LAMP_LIGHT_UP_ONLY_ONE` / `_f 0x743e` 在 FX3 上休眠** |
| **`[Emphasized REC Display]`**<br>(`Shooting -> Shooting Display`) | **`On`**（**默认**，Movie/S&Q 录制时屏幕四周显示醒目红色边框） / **`Off`** | **Can be reset**<br>*(可被 Reset 复位为 `On`)* | `_f 0x68cf`；`BKID_APP_setting_emphasis_dur_rec`；`VAL_setting_emphasis_dur_rec_EMPHASIS_DUR_REC_{ON,OFF}` |
| **`[Remain Shoot Display]`**<br>(`Setup -> Display Option`) | **在 FX3 上完全活跃（仅 Still 连拍缓冲余张数）**：<br>**`Not Displayed`**（**默认**）、`Always Display`、`Shoot-Only Display`（半按/连拍时显示） | **Not available** | `_f 0x604d`/`0x614f` / `0x613e` / `0x72b5` / `0x76eb`；`BKID_APP_setting_remain_shoot_display`（`Wave 40` 已确认并纳入 `DIFF_SET_STILL_MV` 独立项无关状态） |
| **`[Auto Review]`**<br>(`Setup -> Display Option`) | **仅 Still 静态照片**：**`Off`**（**默认**）、`2 Sec`、`5 Sec`、`10 Sec`；检视期间支持放大；**间隔拍摄时禁用** | **Not available** | `base 0xe155` / `0xe207..0xe209`；`BKID_APP_setting_auto_review`；`VAL_setting_auto_review_AUTO_REVIEW_{OFF,2SEC,5SEC,10SEC}` |

### 3.2 三灯耦合、`[Silent Mode]` 隔离与 `ILME-FX6` Tally 对比（`实测事实`）

1. **FX3 物理 3 灯与软件 3 态映射（`实测事实`）**：FX3 机身上分布有**前面板 Tally 灯**、**背部握把侧 Tally 灯**以及**顶部带透光环的 `REC` 键**，但后端 LED 与顶部 `REC` 键在驱动逻辑上绑定，因此用户无法单独关闭顶部键而保留后灯，只能通过 `Only Front Off` 单独屏蔽面向被摄体的前侧红灯（例如透过玻璃拍摄或暗场防反光），或通过 `All Off` 全灭。
2. **与 `[Silent Mode]` 严格解耦（`实测事实`）**：开启 `Shooting -> [Shutter/Silent] -> [Silent Mode] = On` 时，固件仅强锁电子快门与静音 `[Audio signals] = Off`，**不会自动关闭 `[REC Lamp]`**；全暗场静默台架必须显式配置 `[REC Lamp] = All Off`（搭配 `[Emphasized REC Display]` / `[Auto Review]` 需求）。
3. **`[Emphasized REC Display]` 与 HDMI 输出（`实测事实`）**：红框在 Movie 与 S&Q 录制期间于机身 LCD 渲染；当 `[HDMI Info. Display] = On`（且 `Rec. Media = On`、`RAW = Off`）时随叠加信息同步输出至外接 HDMI 监视器，在 `[HDMI Info. Display] = Off` / `RAW Output = On` / `Off(HDMI Only)` 下对 HDMI 完全隐身（Clean Feed 零污染）。
4. **`ILME-FX3` vs `ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
   - `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`）在 **`Technical > Tally`** 下提供全面分离的 Tally 控制：`Front Tally Lamp`（`On/Off`）、`Rear Tally Lamp`（`On/Off`）、`Tally Control`（含 `REMOTE` 端子控制互斥 `FX6 ns1 0x278e`）、`Tally Lamp Brightness`、`G Tally Lamp`（绿灯）与 `Y Tally Lamp`（黄灯），外加 **`Monitoring > Display On/Off > Tally`** 控制 VF/SDI/HDMI OSD 上的红色/绿色 Tally 指示（`FX6 ns2 0x5379..0x537c`）与低电/满卡闪烁告警（`Rec Tally Blink` `0x4ee1`）。

---

## 4. 子系统 4：`[Anti-Flicker Shoot.]` vs 休眠 `[Var. Shutter]` 及 `[APS-C S35 Shooting]` 4K/DCI 4K 锁死

### 4.1 `[Anti-Flicker Shoot.]` vs 休眠 `[Var. Shutter]`（高分解快门）及 `FX6 ECS` 实证（`实测事实`）

1. **休眠 `[Var. Shutter]` / `[Anti-flicker Set.]` 铁证（`实测事实`）**：
   - 在 `FX3 appFw.so` 与 `_f`/`_g.uxc` 中可以搜到完整的 BIONZ XR 高频闪烁抑制符号族：`BKID_APP_setting_high_res_ss`、`BKID_APP_MR_setting_high_res_ss`、`N5model21setting_high_res_ss_tE`、`launch_high_res_ss_set_{movie,still}`、`FUNC_reset_high_res_ss_base_value`、`VAL_launch_high_res_ss_set_HIGH_RES_SS_SET_VALUE_NOT_EXIST`，以及 UXC 词条 `_f 0x64cf`/`0x6831`（`'Var. Shutter'`）、`_f 0x6f9e`/`0x7af8`（`'Var. Shutter Set.'`）、`_f 0x6399`/`0x7924`（`'Var. Shutter Select'`）、`_f 0x68e7`（`'Anti-flicker Set.'`）与 `_g 0x60a8`（`'Anti-flicker Tv Scan'`）。
   - 然而，在 `FX3 appFw.so` 中 `TYPE_MENU_ITEM_*HIGH_RES*` 与 `FEATURE_MANAGER_*high_res*` 均为 **`0` 命中**，且官方 **`ilc/2210`（`Ver. 2.00..7.02`）从未开放 `[Var. Shutter]` 或 `[Anti-flicker Set.]` 菜单**——该小数微调快门功能仅属于同代码库的其他机型（如 `ILCE-7RM5`、`ILME-FX30`、`ILCE-7M4` v3.0+、`ILME-FX2` 等），在 **`ILME-FX3 Ver. 7.02` 上完全处于休眠不可用状态**。
2. **FX3 唯一活跃项 `[Anti-flicker Shoot.]` 规格（`实测事实`）**：
   - 路径：`MENU -> (Shooting) -> [Shutter/Silent] -> [Anti-flicker Shoot.]`（`_f 0x623d` / `0x6854` / `0x6eb8`、`BKID_APP_setting_anti_flicker_shoot`）。
   - 选项与复位：**`Off`（默认） / `On`**，**可由 `[Camera Settings Reset]` 复位**。
   - 硬限制：**仅支持 Still 静态照片机械快门**；仅检测 **100 Hz / 120 Hz** 传统工频荧光灯闪烁并通过微调快门释放时机避开暗波谷；在 **Movie / S&Q、`BULB`、`Electronic Shutter` 与 `[Silent Mode] = On` 下全面禁用**。
3. **对比 `ILME-FX6 Ver. 6.01` `ECS`（`Extended Clear Scan`）（`实测事实`）**：

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **高频 LED 闪烁微调** | **无（`[Var. Shutter]` 休眠不暴露）** | **`ECS`（`Extended Clear Scan`）**：`Shooting > Shutter > Mode = ECS` + `ECS Frequency` **`23.99` 至 `8000 Hz`** 小数频率精调（`FX6 ns1 0x26f2..0x26f4`、`BKID_APP_SETTING_ECS_FREQUENCY`） |
| **快门模式耦合与默认频率** | 仅传统快门速度（`1/8000`–`30"`）+ Ver. 6.00+ `[Shutter Angle]` | `Shutter Mode` 平级切换 **`Speed` / `Angle` / `ECS`**（启用 `ECS` 即替代 `Speed`/`Angle`）；各系统频率默认值：`59.94P -> 60.00Hz`、`50P -> 50.00Hz`、`29.97P -> 30.00Hz`、`25P -> 25.02Hz`、`24P -> 24.02Hz`、`23.98P -> 23.99Hz` |
| **传统工频快门释放避让** | `[Anti-flicker Shoot.]`（仅 Still 机械快门，100/120 Hz） | 无机械快门与 Still 模式（`ECS` 专攻视频 LED 屏幕/脉冲光源条纹消除） |

### 4.2 `[APS-C S35 Shooting]` 4K/DCI 4K/120p 锁死、Still `5.1M` 裁切与 Wave 42 Reset 勘误（`实测事实`）

> [!WARNING]
> **对 [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 的显式勘误（`ilc/2210` *List of default setting values* 实证）**：
> [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h385-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 第 1.1 节曾将 `[APS-C S35 Shooting]` 误记为 *"Resettable by `[Camera Settings Reset]`"*。经直接核对官方 `ilc/2210` *List of default setting values*：`[APS-C S35 Shooting]`（默认 `Auto`）的 **`Resettable using [Camera Settings Reset]` 列明确标注为 `Not available`**！即该设置**抗 `[Camera Settings Reset]`**，唯有执行 **`[Initialize]`** 才会还原为 `Auto`。

1. **`ILME-FX3 Ver. 7.02` `[APS-C S35 Shooting]` 互斥矩阵（`实测事实`）**：
   - **路径与选项**：`MENU -> (Shooting) -> [Image Quality/Rec] -> [APS-C S35 Shooting]`（`BKID_APP_setting_super_35mm`）：**`Auto`（默认）** / **`On`（~1.5x）** / **`Off`**；亦可通过兼容镜头 `[Function Ring(Lens)]` 快捷切换。
   - **视频 4K 全系硬锁死**：因 `12.1 MP` 全画幅传感器（有效 `4240×2832`）在 APS-C/S35 裁剪窗口内不足 `3840` 水平像素，当录制任何 4K 格式（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、**`XAVC S-I DCI 4K`**、`S&Q 4K`）或开启 **`4K Output Set.(HDMI Only)`** / **`RAW Output`** 时，`[APS-C S35 Shooting]` **被强制禁用并锁定为 `Off`**（`FX3 appFw.so` `PRM_HAITA_..._apsc_restriction_imager_frame_rate_in_file_format_4k` 覆盖 `XAVC_HS_4K`、`XAVC_S_4K`、`XAVC_SI_4K`、`XAVC_SI_DCI_4K` 及 `PRM_HAITA_hdmi_4k_outpute_apsc_restriction` 完整门控）。
   - **S35 可用视频域（仅 `HD 1920×1080`）**：将拍摄模式切为 `XAVC S HD` 或 `XAVC S-I HD` 时方可使用 `APS-C S35 = On`，支持常规 `100p / 119.88p` 等 HD 帧率；同时 `FX3 appFw.so` 存在 `VAL_HAITA_setting_menu_shooting_mode_setting_sq_frame_rate_setting_file_format_model_diff_apsc_restriction_imager_frame_rate_in_file_format_fhd_SHOOTING_MODE_SLOW_QUICK_MOTION_SQ_FRAME_RATE_240FPS_SETTING_FILE_FORMAT_XAVC_S_I_HD_IMAGER_FRAME_RATE_OVER_240_200`，对 S&Q `200fps/240fps` 施加了专门的 FHD APS-C 限制校验与 `Auto Framing`（`fixed_camera_framing`）互锁。
   - **静态照片（Still）像素裁切降格（纠偏 `5.1M` 而非 `4.2M`）**：`ilc/2210`（*JPEG/HEIF Image Size* 与 *About zoom scale*）明文规定，在 APS-C 尺寸下拍摄静止影像时，**禁止选择 `L: 12M`（`4240×2832` 3:2 / `L: 10M` 16:9）**，若原选 `L` 则临时自动切换为 **`M: 5.1M`（`2768×1848` 3:2 / `M: 4.3M` `2768×1560` 16:9 / `M: 4.6M` 4:3 / `M: 3.4M` 1:1）**，同时 `FX3 appFw.so` 包含 `backup_imaging_pxsz_apsc_raw0..2` 与 `VAL_HAITA_setting_zoom_setting_..._STILL_JPEG_IMAGE_SIZE_M_..._IMAGER_FRAME_SIZE_APSC` 处理裁切像素维度。
2. **`ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Imager Scan Mode` 对比（`实测事实`）**：

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **传感器裁切菜单** | `[APS-C S35 Shooting]`：`Auto`（默认）/ `On` / `Off`（**抗 Reset**） | `Project > Rec Format > Imager Scan Mode`：**`FF`** vs **`S35`**（`FX6 ns1 0x27cd/0x27ce`；注：`ns1 0x277c..0x31ea` 含 `FF 6K`/`S35 5.8K`/`S16 2K` 等 **VENICE/BURANO 休眠字串**，FX6 实机无此选项） |
| **S35 分辨率限制** | **仅 `HD (1920×1080)`**，禁用全部 4K / DCI 4K / HDMI 4K / RAW | **同样仅限 `1920×1080`（`1..120 fps`）**，禁用 `4K` / `4096×2160` 与全部 `RAW` 录制输出；录制/回放期间不可切换 |
| **全画幅 4K 120p 与 S35 镜头替代方案** | 全画幅 `4K 119.88p/100p` 伴随轻微传感器裁切视角；可开 `[Clear Image Zoom]`（4K `1.5x` / HD `2.0x`） | `FF` 下 `3840×2160` `100/120 fps` S&Q 与 `3840×2160` RAW 显示 `"C"` 裁切标记；用 S35 镜头拍 4K 的行业常规方案是在 `FF` 下开启 **`Clear Image Zoom`**（4K 最高 **`1.5x`** / HD **`2.0x`**，代价是 `>60fps` S&Q、`RAW` 不可用且禁用 Face/Eye AF） |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `HDMI Output Settings` 全套 `BKID_APP_*`/`VAL_HAITA_*`、`DE_SQUEEZE_DISP_{1_3X,1_5X,1_65X,2_0X}`、`REC_LAMP_*`、`emphasis_dur_rec`、`auto_review`、`high_res_ss` 休眠门控、`super_35mm` `apsc_restriction` |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | FX6 `de_squeeze_disp_hdmi_onoff`、`ECS` (`shutter_ecs_frequency`)、`front/rear/g/y_tally`、`imager_scanmode` 状态机 |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（不泄漏原始专有字节） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与说明英文包（`0x6000..0x7d3d`） |
| `FX3 string_english.uxc` / `_g.uxc` | `165,740` / `69,600` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 基础包（`Auto Review`、`1080p/i`）与扩展包（`24.00p` 重启提示、`Anti-flicker Tv Scan`） |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / 基础 / `_g` 三包四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / 基础 / `_g` 三包四语 `resid16` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语原厂 `_f` / 基础 / `_g` 三包四语 `resid16` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `De-Squeeze` (`1.3x`/`1.5x`/`2.0x`)、`ECS` (`23.99..8000Hz`)、`Tally` (`Front`/`Rear`/`G`/`Y`)、`RAW(HDMI)` 与 `Imager Scan Mode` |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，只读 `_f`/`base`/`_g` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x677e` / `0x6144` / `0x6573` | `HDMI Output Settings` / `Rec. Media dur HDMI Output` / `Off(HDMI Only)` | `HDMI输出设置` / `HDMI输出时的摄像媒体` / `关(仅HDMI)` | `HDMI輸出設定` / `HDMI輸出時錄製到記憶卡` / `關(僅限HDMI)` | `HDMI出力設定` / `HDMI出力時のﾒﾃﾞｨｱ記録` / `切(HDMIのみ)` | **活跃**（抗 Reset；`Off(HDMI Only)` 零卡写入） |
| `_f` `0x79ac` / `0x7839` / `base` `0xe1d6, 0xe1d7` | `Output Resolution` / `2160p` / `1080p` / `1080i` | `输出分辨率` / `2160p` / `1080p` / `1080i` | `輸出解析度` / `2160p` / `1080p` / `1080i` | `出力解像度` / `2160p` / `1080p` / `1080i` | **活跃**（`Log`/`PPLUT1..4` 下强制 `1080p`） |
| `_f` `0x74d7` / `0x7195` / `0x731d` / `0x748a` | `4K Output Set.(HDMI Only)` / `59.94p 10bit` / `24.00p 10bit` / `24.00p 8bit` | `4K输出设置(仅HDMI)` / `59.94p 10bit` / `24.00p 10bit` / `24.00p 8bit` | `4K輸出設定(僅限HDMI)` / `59.94p 10bit` / `24.00p 10bit` / `24.00p 8bit` | `4K出力設定(HDMIのみ)` / `59.94p 10bit` / `24.00p 10bit` / `24.00p 8bit` | **活跃（10-bit）**；`0x748a` 8-bit 在 FX3 **休眠** |
| `_f` `0x6e97` / `0x78fd` / `0x6bdc` | `RAW Output` / `RAW Output Setting` / `Color Gamut for RAW Output` | `RAW输出` / `RAW输出设置` / `RAW输出的色域` | `RAW輸出` / `RAW輸出設定` / `RAW輸出的色域` | `RAW出力` / `RAW出力設定` / `RAW出力時の色域設定` | **前 2 项活跃**（`4264×2408`）；`0x6bdc` **Ver. 2+ 并入 Log** |
| `_f` `0x72af` / `0x76e1` / `0x6aa0` / `0x713b` / `0x6bf6` | `Time Code Output` / `REC Control` / `4ch Audio Output` / `CH1/CH2` / `CH3/CH4` | `Time Code输出` / `REC控制` / `4ch音频输出` / `CH1/CH2` / `CH3/CH4` | `Time Code輸出` / `REC控制` / `4ch音訊輸出` / `CH1/CH2` / `CH3/CH4` | `Time Code出力` / `RECコントロール` / `4ch音声の出力` / `CH1/CH2` / `CH3/CH4` | **活跃**（`REC Control` 前置 TC On；HDMI 限 2ch） |
| `_f` `0x7aba` / `0x6253` / `0x7d0a` / `0x7d09` / `0x7d0c` / `0x674c` | `De-Squeeze Display` / `1.3x` / `1.5x` / `1.6x` / `...1.65x compression...` / `2.0x` | `反挤压显示` / `1.3x` / `1.5x` / `1.6x` / `配备有1.65x压缩的变宽镜头时设置。` / `2.0x` | `解壓縮顯示` / `1.3x` / `1.5x` / `1.6x` / `配備有1.65x壓縮的變形鏡頭時設定。` / `2.0x` | `デスクイーズ表示` / `1.3x` / `1.5x` / `1.6x` / `1.65倍圧縮のアナモフィックレンズを装着しているときに設定します` / `2.0x` | **活跃**（Ver. 7.00+ 含 `1.5x`/`1.6x[1.65x]`；**无 `1.8x`**） |
| `_f` `0x6e62` / `0x6337` / `0x727c` / `0x6d8c` / `0x743e` | `REC Lamp` / `All On` / `Only Front Off` / `All Off` / `Only the REC lamp on the rear side...` | `拍摄灯` / `全部打开` / `仅关闭前侧灯` / `全部关闭` / `录制期间仅打开后侧拍摄灯。` | `攝影燈` / `全部開啟` / `僅關閉前側燈` / `全部關閉` / `錄製期間僅後側攝影燈為開啟。` | `録画ランプ` / `全て点灯` / `前面のみ消灯` / `全て消灯` / `録画中に本体背面の録画ランプのみ点灯します` | **前 4 项活跃**（3 灯三态）；`0x743e` **休眠** |
| `_f` `0x68cf` / `0x604d` / `0x613e` / `0x72b5` / `0x76eb` | `Emphasized REC Display` / `Remain Shoot Display` / `Not Displayed` / `Always Display` / `Shoot-Only Display` | `录制时强调显示` / `剩余拍摄显示` / `不显示` / `总是显示` / `仅在拍摄时显示` | `強調錄製顯示框` / `剩餘拍攝顯示` / `不顯示` / `始終顯示` / `僅在拍攝時顯示` | `記録中の強調表示` / `撮影残量表示` / `表示しない` / `常に表示する` / `撮影中のみ表示` | **活跃**（前者可 Reset，后者 Still 活跃且抗 Reset） |
| `base` `0xe155` / `0xe207` / `0xe208` / `0xe209` | `Auto Review` / `2 Sec` / `5 Sec` / `10 Sec` | `自动检视` / `2秒` / `5秒` / `10秒` | `自動顯示影像` / `2秒` / `5秒` / `10秒` | `オートレビュー` / `2秒` / `5秒` / `10秒` | **活跃**（仅 Still，抗 Reset，默认 `Off`） |
| `_f` `0x623d` / `0x68e7` / `0x6831` / `0x6f9e` / `_g` `0x60a8` | `Anti-flicker Shoot.` / `Anti-flicker Set.` / `Var. Shutter` / `Var. Shutter Set.` / `Anti-flicker Tv Scan` | `防闪烁拍摄` / `防闪烁设置` / `可变快门` / `可变快门设置` / `防闪烁Tv扫描` | `抗光源閃爍拍攝` / `防止閃爍設定` / `可變快門` / `可變快門設定` / `抗光源閃爍Tv掃描` | `ﾌﾘｯｶｰﾚｽ撮影` / `ﾌﾘｯｶｰﾚｽ設定` / `高分解ｼｬｯﾀｰ` / `高分解ｼｬｯﾀｰ設定` / `ﾌﾘｯｶ-ﾚｽTvｽｷｬﾝ` | **仅 `0x623d` 活跃**；后 4 项在 FX3 Ver. 7.02 **完全休眠** |
| `_f` `0x6eba` / `0x6bba` / `0x73e8` / `0x76c9` | `APS-C/Super 35mm` / `APS-C Size Capture` / `Records in the range...` / `Sets whether or not...` | `APS-C/Super 35mm` / `APS-C画幅拍摄` / `拍摄静态影像时...` / `设定是否确定记录范围...` | `APS-C/Super 35mm` / `APS-C尺寸拍攝` / `拍攝靜態影像時...` / `設定是否要將錄製範圍...` | `APS-C/Super 35mm` / `APS-Cサイズ撮影` / `静止画撮影時は...` / `記録範囲を35mmフルサイズ...` | **活跃**（**抗 Reset**，禁全部 4K，Still 降 `5.1M`） |
