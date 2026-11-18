# 全球 Sony 实机情报 Wave 68（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`Setup -> [Area/Date]` 时区表/夏令时/日期格式与 RTC 备电持久化 vs FX6 `Clock Set`、`[Grid Line Display]`/`[Grid Line Type]` Clean-HDMI 隔离 vs `[Marker Display] -> [Guideframe]` / FX6 `Guide Frame`、`[Save/Load Settings]` `CAMSET01..10.DAT` `Slot-1` `EROFS=30` 护栏/排除清单/`libSaveLoadSettings.so` 与 `Camera Set. Memory` `1..3` vs `M1..M4` vs FX6 `Project > All File`、以及无物理 `Sync Terminal` 辟谣 / MI-Shoe `[Video Light Mode]` 与 `XLR-H1` 物理互斥 vs FX6 `TC IN/OUT` BNC 与无 `GENLOCK`）

- **日期**：`2026-11-17`
- **任务 / 波次**：`H408` · **Wave 68（Global Sony Real-Hardware Empirical Intelligence Wave 68）**
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Area/Date/Time Setting / Performing initial setup for the camera / Grid Line Display / Grid Line Type / Marker Display / Save/Load Settings / Camera Set. Memory / Memory/Recall Media / External Flash Set. / Flash Mode / Video Light Mode / Multi Interface Shoe / Attaching the supplied XLR handle unit / Setting Reset (Camera Settings Reset vs Initialize) / List of default setting values*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0+ —— *Maintenance > Clock Set / Monitoring > Marker (Guide Frame & Center Marker) / Project > All File & User File / Paint/Look > Scene File / Technical > Video Light Set / TC IN/OUT BNC & 无 GENLOCK BNC（对比 PXW-FX9）*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)、[`FX3 libSaveLoadSettings.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so)、[`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc)、[`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin)、[`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)、[`FX6 string_english.uxc` / `_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc)
  - 仓内安全守卫交叉对照：[`G89/G90` Grid Line HDMI & Sunny Weather](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py)、[`G92` Save/Load Settings & Tier-0](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py)、[`G110` Area/Date/Time & Video Light](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)、[`G120` Flash & Video Light](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)、[`G122` Recall Custom Hold & CAMPR/CAMSET](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)、[`G142` Marker Display & Aspect Marker](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py)
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF 符号、SHA-256 账本与官方 Help Guide/说明书条目）与 **`推断`**（Tier-0 `Slot 1` 只读保险库、`EROFS=30` 拦截边界与模拟器台架风险推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`Setup -> [Area/Date]` 时区/DST/日期格式、RTC 备电与首次引导 vs FX6 `Maintenance > Clock Set`）**：
   - **实测事实（FX3 Ver. 7.02 结构与 ELF 证据）**：`Setup -> [Area/Date] -> [Area/Date/Time Setting]`（`_f 0x6a9c`，取代旧版 `base 0xe87f` `Date/Time Setup`）下设 4 项：**`[Area Setting]`**（`base 0xe91a`，对应 `FX3 appFw.so` 内 **30 个 `AREA_GMT_*` 时区条目** `GMT_M_11_0` 至 `GMT_P_12_0`，含 6 个半小时偏移区 `M_03_5`/`P_03_5`/`P_04_5`/`P_05_5`/`P_06_5`/`P_09_5`）、**`[Daylight Savings]`**（`base 0xe917`，`Off` 默认/`On`；ELF 原厂拼写错字 **`convert_setting_daylight_saving_to_saylight_saving`** 与 `BKID_APP_setting_daylight_saving`）、**`[Date/Time]`**（`_f 0x73b5`）、**`[Date Format]`**（`_f 0x670d`，仅提供 **`Y-M-D`** / **`M-D-Y`** / **`D-M-Y`** 三项，`BKID_APP_setting_date_format`）。
   - **实测事实（Reset vs Initialize 与 RTC 备电）**：`[Camera Settings Reset]` **不复位** `[Area/Date/Time Setting]`；唯有 **`[Initialize]`** 复位所有 `[Setup]` 项（含隐私协议并重新触发初始向导 `37dlg_rec203_initial_setting_controller` / `PRM_launch_date_time_setup_area_setting`）。机身内置**可充电备用电池**（非用户可更换 CR2032 纽扣槽）：装入满电 `NP-FZ100` 并**关机静置 24 小时以上**即可充满；若未在初始设置中注册手机或内部备电完全放空，开机自动弹出 `Area/Date/Time Setting`（注：`~3 个月`断电保持时间出自部分兄弟 Alpha 机型说明书，**不在 `ilc/2210` 文本中**）。
   - **对比 `ILME-FX6 Ver. 6.01`**：入口为 **`Maintenance > Clock Set`**（`FX6 ns2 0x426c`，`BKID_APP_USER_MENU_CLOCK_SET0..6`），暴露 `Time Zone`（`UTC -12:00` 至 `UTC +14:00` 按 **30 分钟**步进，`ns2 0x4a55..0x4abd`）、`Date Mode`（`YYMMDD` / `MMDDYY` / `DDMMYY`）、`12h/24h`、`Date`、`Time`。FX6 UI **无独立 `Summer Time` / `Daylight Saving Time` 开关**（`ns2 0x564d` 与 ELF `summer_time_name_dst` 均为休眠字面量）；同样采用**内置可充电备用电池**（耗尽开机强制锁死 `Clock Set` 直到完成，或报 `ns2 0x411f` `Backup Battery End`）。

2. **子系统 2（`[Marker Display] -> [Guideframe]` vs `[Grid Line Display]` / `[Grid Line Type]` 与 Clean-HDMI 隔离 vs FX6 `Guide Frame`）**：
   - **实测事实（双系统严格解耦与统一后痕迹）**：
     - **`[Grid Line Display]`**（`_f 0x6f9d`，默认 `Off` / `On`，`BKID_APP_setting_grid_line_display`）与 **`[Grid Line Type]`**（`_f 0x69c9`，默认 **`Rule of 3rds Grid`** / **`Square Grid`** / **`Diag. + Square Grid`**，`BKID_APP_setting_grid_line_type`）位于 `Shooting -> [Shooting Display]`，**全管线（Still / Movie / S&Q）可用**，配合自定义键 `[Grid Line Display Select]`（`_f 0x70c5`）一键切换。ELF 中残留 `BKID_APP_deleted_setting_grid_line_{display,type}_movie`，证实 Sony 已将早期分离的视频网格寄存器合并为全管线单一状态位。
     - **`[Marker Display]`**（`_f 0x61b2`，`BKID_APP_setting_marker_display`）位于 `Shooting -> [Marker Display]`，**仅限 Movie / S&Q 管线**（`PRM_HAITA_setting_marker_display_exposure_mode`），含 `[Center Marker]`、15 比例 `[Aspect Marker]`、`[Safety Zone]` 与 **`[Guideframe]`**（`_f 0x62f9`，默认 `Off` / `On`，`BKID_APP_setting_guide_frame`），在 `[Focus Magnifier]` 下不可显示。
   - **实测事实（Reset 行为与 Clean-HDMI 关键分水岭）**：`ilc/2210` *List of default setting values* 证实 **`[Grid Line Display/Type]` 与 `[Marker Display]` 全部 5 项在 `[Camera Settings Reset]` 下均为 `Not available`（抗 Reset，仅 `[Initialize]` 归零）**。但 HDMI 输出路由截然相反：**`[Marker Display]` 仅限机背屏幕显示、绝不输出到 HDMI（`0` 像素注入）**；而 **`[Grid Line Display]` 在 `[HDMI Info. Display] = On` 时会透传至外部 HDMI**，仅在 `[Rec. Media dur HDMI Output] = Off(HDMI Only)` 或 `[RAW Output] = On` 强制 Clean-Feed 时被临时抑制为 `Off`。
   - **对比 `ILME-FX6 Ver. 6.01`**：使用 **`Monitoring > Marker`**（`BKID_APP_USER_MENU_MARKER0..19`），含 `Guide Frame`（`On/Off`，`ns2 0x4520`）与 **`Center Marker`**（**`1 / 2 / 3 / 4 / Off`**，`ns2 0x450a`）、`Safety Zone/Area`、`Aspect Marker`、`100% Marker`、`User Box`；**无** FX3 的 3 模式静态构图网格 UI（尽管 `FX6 appFw.so` 休眠保留 `GUIDE_FRAME_{RULE_OF_3RD,SQUARE,DIAG_SQUARE,GOLDEN_RATIO}_GRID`）。

3. **子系统 3（`[Save/Load Settings]` `CAMSET01..10.DAT`、`Slot-1` `EROFS=30`、排除列表与 `Camera Set. Memory` `1..3` vs `M1..M4` vs FX6 `All File`）**：
   - **实测事实（精确卡内目录路径与 `libSaveLoadSettings.so` 机制）**：`Setup -> [Reset/Save Settings] -> [Save/Load Settings]`（`_f 0x6254`）卡侧**仅限 `Slot 1`**（**不可切换 `Slot 2`**），每张卡最多存 **10 份** `CAMSET01.DAT`..`CAMSET10.DAT`（ELF `CAMSET%02d`），另可经 `Ver. 4.00+` C3 Portal / Creators' App for enterprise 存至 `Cloud(Private)` / `Cloud(Share)`（上限 60 份）。**纠偏实证**：`FX3 appFw.so` 真实路径模板为 **`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`**（SD 卡 `/PRIVATE/SONY/SETTING/<model>/CAMSET/CAMSET01.DAT`，CFexpress Type A 卡 `/SONY/SETTING/<model>/CAMSET/CAMSET01.DAT`），`FX3` 全库对 `PRO/CAMERA` 命中 **`0`** 次！独立动态库 [`libSaveLoadSettings.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so)（`18,760 B`）导出 `SaveLoadSettingsIf::requestTo{Read,Check,Write}` 与 `Backup_{get_datasize,read,write}`，强校验同机型 `ILME-FX3` 与固件版本（如 `Ver. 1.01` 及更早配置无法载入 `Ver. 2.00+`；不同版本跨载可能失败报 `_g 0x61d7` / `0x624d`），载入成功后提示自动重启（`_g 0x62dd`），且 `MR` 调出模式下禁止执行。
   - **实测事实（官方全量排除清单与 `1..3` vs `M1..M4` 分立）**：`CAMSET*.DAT` **绝不保存** `IPTC Information`、`Copyright Info`、`External Flash Set.`、`White Balance`（`Custom 1/2/3`）、`Face Memory`、全部网络/证书项（`FTP Transfer Func.` 另由 `[Save/Load FTP Settings]` `_f 0x71ae` 写入 **`SONY/SETTING/%s/FTPSET/%s.DAT`**、`Network Streaming`、`Cloud Connection`、`WPS Push`、`Access Point Set.`、`Wi-Fi Frequency Band`、`IP Address Setting`、`Edit Device Name`、`Import Root Certificate`、`Access Authen. Settings`、`Security(IPsec)`）、`Language` 及 `Area/Date/Time Setting`。另一侧，`Shooting -> [Shooting Mode] -> [Camera Set. Memory]` 提供机身 **`1..3`**（随 NVRAM 存在并随 `CAMSET*.DAT` 打包，抗 `[Camera Settings Reset]`）与存储卡 **`M1..M4`**（路径 **`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`**，可通过 `[Memory/Recall Media]` `_f 0x763c` 选 `Slot 1` 默认或 `Slot 2`；均不保存 `Custom Key/Dial Set.` 与 `Program Shift`）。
   - **推断（`Slot-1` Tier-0 保险库 `EROFS=30` 危险）**：由于 `[Save/Load Settings]` 的 `[Media]` 路径硬锁定 `Slot 1` 而不可改 `Slot 2`，若在挂载只读 Tier-0 恢复保险库的 `Slot 1` 上执行 `[Save]`/`[Delete]`，台架必须在 VFS/块设备层强制拦截并返回 **`EROFS (errno 30)`**；仅 `[Load]` 可通过只读打开卡文件完成（仍会覆盖机身 NVRAM 并触发重启）。
   - **对比 `ILME-FX6 Ver. 6.01`**：FX6 **无顶层 `File` 菜单**，由 **`Project > All File`**（`%c:%s/SONY/PRO/CAMERA/%s/%s.ALL`，卡槽 **`Media(B)`** 上限 64 份，支持 `All File Load Network Data` 开关与加载重启）、**`Project > User File`**（`.USRF`）、**`Paint/Look > Scene File`**（`%c:%s/SONY/PRO/SCENE/%s.SCN`，Ver. 6.00+ 合并原 Paint/Look）及 **`User 3D LUT`**（最多 16 份 `.cube`）承担。**`Reference File`**（`FX6 ns2 0x429b` / `0x4d52`）在 `FX6 appFw.so` 命中 **`0`** 次，属休眠继承词条（`FX6 appFw.so` 同时休眠残留 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`）。

4. **子系统 4（无物理 `Sync Terminal` 辟谣、`[External Flash Set.]` / `[Video Light Mode]` 与 `XLR-H1` MI-Shoe 物理互斥 vs FX6 `TC IN/OUT` & 无 `GENLOCK` BNC）**：
   - **实测事实（`Sync Terminal` 辟谣与休眠符号边界）**：`ILME-FX3` 机身**完全没有物理 PC 闪光同步端子（`(Flash sync) terminal`）**（与同源的 `ILCE-7SM3` 一致；Alpha 阵列中仅 `ILCE-1` / `ILCE-7RM5` / `ILCE-9*` 配备该物理端子）。虽然 `FX3 appFw.so` 与 UXC 残留休眠共享条目 `Flash Sync Spd. Prty.`（`_f 0x6b31`，`BKID_APP_setting_flash_sync_spd_priority`）与 `_g 0x645e`（`SYNCHRO_TERMINAL_OUTPUT_SET_ON`），但 `FX3 appFw.so` 内 **`SYNCHRO_TERMINAL*` 符号数为 `0`**，且 `ilc/2210` 对 `Sync Terminal` / `Flash Sync Spd. Prty.` **零页面暴露**。
   - **实测事实（MI-Shoe 外置闪光灯 & `[Video Light Mode]` 与 `XLR-H1` 互斥）**：闪光灯仅能经机身顶部 **Multi Interface Shoe（MI 热靴）**连接，`Exposure/Color -> [Flash] -> [External Flash Set.]`（`_f 0x6771`）与 `[Flash Mode]`（`base 0xe5ce`，5 模式）**仅限 Still 机械快门**（最高同步速度 `1/250 s`，严禁 `>= 250 V` 或反极性高压引闪），且 `External Flash Set.` 不随 `CAMSET*.DAT` 保存也不受 `[Camera Settings Reset]` 复位。视频灯配置位于 `Setup -> [Setup Option] -> [Video Light Mode]`（`_f 0x6211`，`BKID_APP_setting_video_light_set`），针对 **`HVL-LBPC`** 提供 4 模式：**`Power Link`**（默认）、`REC Link`、`REC Link&STBY` 与 **`Auto`**（`VIDEO_LIGHT_SET_AUTO_LOW_LIGHT`）。**物理与供电双互斥**：随机附带的 **`XLR-H1`** 手柄独占机身唯一的电气 MI 热靴，其附属 Accessory Shoe Kit 仅提供**无触点纯机械冷靴（passive cold shoe）**，因此 **`XLR-H1` 与由 MI 热靴供电/通信的 `HVL-LBPC`（或 MI 热靴闪光灯）无法同时直插 MI Shoe 联控**；直接挂载时仍须遵守 Stage-B `PMIC 5V <= 900 mA`（[`G24`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py) / [`G110`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)）功率预算。
   - **对比 `ILME-FX6 Ver. 6.01`**：FX6 `Technical > Video Light Set`（`ns2 0x4289`）仅提供 `Power Link` / `Rec Link` / `Rec Link + Stby`（**无 `Auto` 模式**，`VAL_setting_video_light_set_*` 共 4 符，不含 `AUTO`），且**无任何 Still `[Flash]` UI**（尽管 `FX6 appFw.so` 残留 1 条休眠 `SYNCHRO_TERMINAL`）；硬件同步方面，FX6 配备单颗可切换 **`TC IN / TC OUT` BNC**（`IN` 态触发 `EXT-LK` 外部时码锁相），但**没有物理 `GENLOCK IN / REF OUT` BNC**（此为 `ILME-FX6` 与 **`PXW-FX9`** 的核心分水岭，即使 `FX6 appFw.so` 休眠编译了 **107 条 `GENLOCK` 符号**且 `ns2 0x4262, 0x56d5..0x56d7` 保留完整 Genlock 提示串）。

---

## 1. 子系统 1：`Setup -> [Area/Date]`、`[Area/Date/Time Setting]`、RTC 备电与首次启动 vs FX6 `Maintenance > Clock Set`

### 1.1 `ILME-FX3 Ver. 7.02` `[Area/Date]` 菜单拓扑、30 时区表与 ELF 证据（`实测事实`）

1. **菜单真值表与 Reset / Initialize 持久性（`ilc/2210` + `FX3 appFw.so`）**：

| 菜单项（精确路径：`Setup -> [Area/Date]`） | `FX3 Ver. 7.02` 选项与出厂默认（`ilc/2210`） | `[Camera Settings Reset]` | `[Initialize]` | UXC `resid16` / ELF 实证（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Area/Date/Time Setting]`** | 总入口页（取代早期固件 `Date/Time Setup` 命名） | **Not available**<br>*(抗 Reset)* | **重置并触发向导** | `_f 0x6a9c`（对比旧词条 `base 0xe87f` `Date/Time Setup`）、`_g 0x6108` `Area/Date`、`PRM_launch_date_time_setup_area_setting` |
| ↳ **`[Area Setting]`** | **未设（`—`）**；按城市/GMT 偏移选择区域 | **Not available** | **重置** | `base 0xe91a`；`FX3 appFw.so` 实测 **30 条 `AREA_GMT_*`**（`GMT_M_11_0` 至 `GMT_P_12_0`，含 `M_03_5`/`P_03_5`/`P_04_5`/`P_05_5`/`P_06_5`/`P_09_5` 半时区） |
| ↳ **`[Daylight Savings]`** | **`Off`（默认）** / `On`（开启时时钟前进 `+1` 小时） | **Not available** | **还原 `Off`** | `base 0xe917`；`BKID_APP_setting_daylight_saving`；**Sony 原厂 ELF 拼写错字：`convert_setting_daylight_saving_to_saylight_saving`** |
| ↳ **`[Date/Time]`** | **`—`**（手动设置年/月/日/时/分；或由 Creators' App 蓝牙同步） | **Not available** | **重置** | `_f 0x73b5` / `0x7a9a`；`BKID_APP_date_time_set_status`、`BKID_APP_setting_auto_sync_sever_date_time`（原厂 `sever` 拼写） |
| ↳ **`[Date Format]`** | **`—`**（可选 **`Y-M-D`** / **`M-D-Y`** / **`D-M-Y`**；无 `YYYY-MM-DD` 独立选项） | **Not available** | **重置** | `_f 0x670d`、`0x7416` / `0x7976` / `0x65da`（`base 0xe888` / `0xe887` / `0xe97e`）；`BKID_APP_setting_date_format` |

2. **首次开机弹窗、初始向导与内部 RTC 充电备电规范（`实测事实` vs 外部口径边界）**：
   - **开机强弹窗逻辑（`ilc/2210` + ELF）**：开箱或执行 `[Initialize]` 后进入初始引导控制器 `37dlg_rec203_initial_setting_controller`（含 `_g 0x64a8` `"Initial Setting with Creators' App"`）。`ilc/2210` *Area/Date/Time Setting* 明文规定：**若初始设置期间未通过手机 App 注册/同步，或内置可充电备用电池完全放电，则每次开机自动弹出 `[Area/Date/Time Setting]`**；此外，依赖有效时间戳的功能（如特定服务器/网络同步）在时钟未设定时会触发 `_g 0x63a6`（`"Sets the “Area/Date/Time Setting” to perform this function."`）。
   - **内部可充电备用电池 vs 无 CR2032 纽扣槽**：`ILME-FX3` 主板**无用户可自行更换的 CR2032 纽扣电池仓**，由机内焊接式可充电备用电池（二次锂纽扣电容/电池）维持 RTC。`ilc/2210` *Performing initial setup for the camera* 明确写明充电方法：**装入已充满的主电池（`NP-FZ100`），将相机电源开关置于 `OFF` 并静置 `24 小时或更久（24 hours or more）`**；若每次为主电池充电后日期时间都会归零，说明内部备用电池已老化耗尽，须送修 Sony 服务中心。
   - **文献边界严格声明（`实测事实`）**：虽然 Sony 部分早年 Alpha 机型（如 ILCE-7 系列）说明书曾出现“充满电可维持约 3 个月”的经验说明，但 **`ILME-FX3` 官方 `ilc/2210` Help Guide 正文并未给出“3 个月”的具体放电时长数字**，仅规范了 `>= 24 hours` 关机充电周期与每次换电后重置即判定损坏的排查标准。

### 1.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Maintenance > Clock Set` 对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **菜单路径** | `Setup -> [Area/Date] -> [Area/Date/Time Setting]` | **`Maintenance > Clock Set`**（`FX6 ns2 0x426c`，`BKID_APP_USER_MENU_CLOCK_SET0..6`） |
| **时区步进与范围** | `Area Setting`：30 个 `AREA_GMT_*`（`GMT -11:00` 至 `GMT +12:00`，含 6 个 `:30` 时区） | **`Time Zone`**：`UTC -12:00` 至 `UTC +14:00` 按 **30 分钟**步进（`FX6 ns2 0x4a55..0x4abd`，覆盖 `UTC +13:30` / `UTC +14:00`） |
| **夏令时（DST）机制** | 独立菜单开关 **`[Daylight Savings]`**（`On / Off`） | **无独立 `Summer Time` / `Daylight Saving Time` UI 开关**：改用手动调整 `Time Zone` 偏移实现（`ns2 0x564d` `"Daylight Saving Time"` 与 `FX6 appFw.so` 中 `summer_time_name_dst` 为休眠符号） |
| **日期与时间格式** | `Date Format`：`Y-M-D` / `M-D-Y` / `D-M-Y`（24 小时制显示） | **`Date Mode`**：`YYMMDD` / `MMDDYY` / `DDMMYY` + 独立 **`12h/24h`** 切换（`12h` / `24h`） |
| **RTC 备电硬件与失效行为** | 内置可充电备用电池（非可换 CR2032）；关机插主电池 `>= 24h` 充电；放空开机跳 `Area/Date/Time Setting` | 同样为**内置可充电备用电池**（无外部用户 CR2032 门盖）；长期断电放空后开机**强锁 `Clock Set` 初始屏**（除关机外禁止一切操作），老化时报错 **`ns2 0x411f` `"Backup Battery End"`**（`Backup Battery End. Please Change.`） |

---

## 2. 子系统 2：`Shooting -> [Marker Display]`（`[Guideframe]`）vs `[Grid Line Display]` / `[Grid Line Type]` 与 Clean-HDMI 隔离 vs FX6 `Guide Frame`

### 2.1 两套“参考线”系统的深度解耦：全管线 `[Grid Line]` vs 仅视频 `[Marker Display]`（`实测事实`）

许多操作手册与二次转述容易混淆 `[Grid Line Display]` 与 `[Marker Display] -> [Guideframe]`。`ilc/2210` 与 `FX3 appFw.so` 实证二者分属不同菜单路径、不同拍摄模式门控、不同 HDMI 合成管线：

| 对比维度 | `Shooting -> [Shooting Display] -> [Grid Line Display]` & `[Grid Line Type]` | `Shooting -> [Marker Display]`（含 `[Guideframe]`） |
| :--- | :--- | :--- |
| **适用模式** | **Still / Movie / S&Q 全管线共享**（ELF 已删除旧视频专用 `BKID_APP_deleted_setting_grid_line_{display,type}_movie`） | **仅限 Movie / S&Q**（Still 模式下不显示，`PRM_HAITA_setting_marker_display_exposure_mode`） |
| **精确菜单与子项** | **`[Grid Line Display]`**（`_f 0x6f9d`，默认 **`Off`** / `On`）<br>**`[Grid Line Type]`**（`_f 0x69c9`，默认 **`Rule of 3rds Grid`** / **`Square Grid`** / **`Diag. + Square Grid`**） | **`[Marker Display]`**（`_f 0x61b2`，总开关 默认 **`Off`** / `On`）下辖 4 项（默认全 **`Off`**）：<br>① `Center Marker`；② 15 比例 `Aspect Marker`；③ `Safety Zone`（`Off/80%/90%`）；④ **`[Guideframe]`**（`_f 0x62f9`，水平/垂直参考框） |
| **自定义键支持** | **`[Grid Line Display Select]`**（`_f 0x70c5`，`EVENT_FUNC_CUSTOM_GRID_LINE_DISPLAY_SEL_{ON,OFF}`、`FUNC_set_grid_line_display_select_seq`）开关显示；**`[Grid Line Type]`** 亦可绑定自定义键 | `Marker Display` 可绑定自定义键（`EVENT_FUNC_CUSTOM_MOVIE_MARKER_DISPLAY_{ON,OFF}`、`FUNC_marker_display_switch_seq`）；`Guideframe` 仅作为其下属子项随动 |
| **Reset vs Initialize** | **`[Camera Settings Reset]` = `Not available`**（抗 Reset）；仅 **`[Initialize]`** 还原（`Off` + `Rule of 3rds Grid`） | **`[Camera Settings Reset]` = `Not available`**（全 5 项均抗 Reset！）；仅 **`[Initialize]`** 全部还原 `Off` |
| **Focus Magnifier 下行为** | 仅受 HDMI 规则约束 | `ilc/2210` 明确规定**开启 `[Focus Magnifier]` 时所有 Marker 均不显示** |
| **Clean-HDMI / HDMI 输出行为** | **随 `[HDMI Info. Display]` 路由至外部 HDMI**：<br>• `[HDMI Info. Display] = On` 且内录（`Rec. Media dur HDMI Output = On`）时**输出至 HDMI 画面**；<br>• 若 `[HDMI Info. Display] = Off`，或因 `Rec. Media = Off(HDMI Only)` / `RAW Output = On` 触发强制洁净输出（Clean-Feed），则网格在 HDMI 端被完全剥离（[`G89` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py)） | **绝对 Clean-HDMI 隔离（机内监视器独占）**：<br>`ilc/2210` *Marker Display* 明确标注 **`\"Markers appear only on the monitor and cannot be output.\"`**——即使 `[HDMI Info. Display] = On`，`Guideframe` / `Center Marker` / `Aspect Marker` / `Safety Zone` **也绝不会叠加到 HDMI 输出流** |
| **ELF 枚举实证** | `GRID_LINE_DISPLAY_{OFF,ON}`、`GRID_LINE_TYPE_{RULE_OF_3RD_GRID,SQUARE_GRID,DIAG_SQUARE_GRID}` | `BKID_APP_setting_marker_display`、`BKID_APP_setting_guide_frame`、`BKID_APP_setting_marker_display_aspect`、`GUIDE_FRAME_{OFF,ON}` |

> [!IMPORTANT]
> **常见误区纠偏（`实测事实`）**：
> 1. **`[Camera Settings Reset]` 并不复位 `[Marker Display]`**：不同于直觉猜测“视频菜单都随 Camera Settings Reset 复位”，官方 `ilc/2210` *List of default setting values* 明确列出 **`Marker Display`、`Center Marker`、`Aspect Marker`、`Safety Zone`、`Guideframe` 与 `Grid Line Display/Type` 一样，全部标为 `Camera Settings Reset: Not available`**，唯有 `[Initialize]` 会将其归零。
> 2. **Clean-HDMI 监看验收要分流**：向外部录机/推流卡输出 Clean-HDMI 时，仅仅关闭 `Marker Display` 是不够的（它本来就不上 HDMI），真正会“污染”外部 HDMI 画面的是 `Shooting Display -> [Grid Line Display]`（以及 `[HDMI Info. Display] = On` 下的 OSD 叠加），必须在台架或录机侧显式设为 `Off(HDMI Only)` 或关闭 `[HDMI Info. Display]`。

### 2.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Monitoring > Marker` 对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **主菜单与子项** | 拆分为两套：`[Grid Line Display/Type]`（3 图案） + `[Marker Display]`（Center/15-Aspect/Safety 80%/90%/Guideframe） | 单一菜单 **`Monitoring > Marker`**（`BKID_APP_USER_MENU_MARKER0..19`）：<br>`Setting`（`On/Off`）、`Color`（7 色可选）、**`Center Marker`**（`1 / 2 / 3 / 4 / Off`，`ns2 0x450a`）、**`Guide Frame`**（`On / Off`，`ns2 0x4520`）、`Safety Zone` + `Safety Area`（`80% / 90% / 92.5% / 95%`）、`Aspect Marker`（`Line / Mask / Off`）、`100% Marker`、`User Box` |
| **3 模式构图网格与黄金分割** | 实装 3 模式（三分/方格/对角+方格）；无黄金分割选项 | **本机菜单不暴露 `Rule of 3rds` / `Square` / `Diag+Square` 3 模式网格**（`FX6 appFw.so` 内休眠保留 `GUIDE_FRAME_{RULE_OF_3RD,SQUARE,DIAG_SQUARE,GOLDEN_RATIO}_GRID`）；`Grid Line` 在 *Monitor & Control* App 外接监看端独立提供 |
| **SDI/HDMI 叠加隔离** | `Marker Display` 仅本地屏；`Grid Line Display` 随 `HDMI Info. Display` 透传 | `VF / SDI / HDMI` 各自拥有独立的 `Display On/Off > Marker` 开关门控，可精细指定仅 SDI/仅 VF 显示标记 |

---

## 3. 子系统 3：`Setup -> [Reset/Save Settings] -> [Save/Load Settings]`（`CAMSET01..10.DAT`）、`libSaveLoadSettings.so` 与 `[Camera Set. Memory]`（`1..3` vs `M1..M4`）vs FX6 `All File`

### 3.1 `CAMSET01..10.DAT` 卡内精确路径、`Slot-1` 硬锁定与 `libSaveLoadSettings.so` 实证（`实测事实`）

1. **路径模板纠偏（`FX3 appFw.so` `os.O_RDONLY` 实测）**：
   - `FX3 appFw.so` 字符串表中存在 **3 条**精确 `SONY/SETTING` 路径模板，同时对 `PRO/CAMERA` 命中数为 **`0`**：
     - **全机配置保存（`Save/Load Settings`）**：**`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`** + 文件名模板 **`CAMSET%02d`**（范围 `CAMSET01.DAT` .. `CAMSET10.DAT`）。其中 `%s` 前缀随介质类型动态展开：在 SDXC/SDHC 卡上为 `/PRIVATE`（即 **`/PRIVATE/SONY/SETTING/<Model>/CAMSET/CAMSET01.DAT`**），在 CFexpress Type A 卡上为 `""`（即 **`/SONY/SETTING/<Model>/CAMSET/CAMSET01.DAT`**）；每张存储卡上限 **10 个槽位**，另在 `Ver. 4.00+` 新增 **`Cloud(Private)`** 与 **`Cloud(Share)`**（`_f 0x7c53`/`0x7c5a`，需 C3 Portal 合约与 Creators' App for enterprise，云端总容量 **60 份**，跨机身仅限同型号）。
     - **存储卡拍摄配置调用（`Camera Set. Memory` `M1..M4`）**：**`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`**。
     - **FTP 独立配置保存（`[Save/Load FTP Settings]` `_f 0x71ae`）**：**`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT`** + **`FTPSET%02d`**（弥补 `CAMSET` 排除 `FTP Transfer Func.` 的缺口）。
2. **`libSaveLoadSettings.so` 动态库与兼容性硬约束（`实测事实`）**：
   - 独立共享库 [`libSaveLoadSettings.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so)（`18,760 B`，SHA-256 `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7`）导出核心 C++/C ABI 接口：
     - `SaveLoadSettingsIf::{requestToRead, requestToCheck, requestToWrite}` 与 `SaveLoadSettings::{procRead, procCheck, procWrite}`（读取前强制经 `procCheck` 校验头信息与校验和）；
     - 底层 NVRAM 块桥梁 `Backup_get_datasize`、`Backup_read`、`Backup_write`（对应 `appFw.so` `BKID_APP_save_load_settings_infra_data{,_size}` 及 `infra_mr_data0..8`）；
     - 回调表分流 `infra_getCallbackFuncTable` vs **`infra_getCallbackFuncTableFtp`**，经 `MWF::EventWrapper::SendAndRecv` 与主控进程通信。
   - **机型与跨固件版本硬限制（`ilc/2210` + UXC）**：
     - **严格同机型锁定**：仅可跨同型号 `ILME-FX3` 机身加载（`ilc/2210`：*Settings can only be loaded from a camera of the same model*），跨机型或损坏文件经 `requestToCheck` 拦截并弹出 `_g 0x624d`（`"This file cannot be loaded."`）或 `_g 0x61d7`（`"Loading failed."`）。
     - **跨固件版本不兼容门控**：Sony 在 `ilc/2210` 明文警告，**不同系统软件版本之间保存的配置文件可能无法加载**——典型硬断代为 **Ver. 1.01 及更早固件保存的 `CAMSET*.DAT` 无法加载至 Ver. 2.00 及以上固件机身**。
     - **运行态禁止与加载重启**：当机身处于 **`MR`（Recall Camera Setting）模式**下，`[Save/Load Settings]` 不可执行；加载操作会覆盖本机设定，并在确认后触发自动重启（`_g 0x62dd`：`"Load?\nOverwrites the device's settings.\nReboots after loading.\nFile: ${v1}"`）。

### 3.2 `CAMSET*.DAT` 官方完整排除清单与 `Slot-1` Tier-0 `EROFS (errno 30)` 护栏

1. **官方 `ilc/2210` *Save/Load Settings* 完整排除参数清单（`实测事实`，绝不随 `CAMSET01..10.DAT` 导出）**：

| 排除类别 | 官方排除项精确名称（`ilc/2210`） | 工程后果与替代备份机制 |
| :--- | :--- | :--- |
| **身份与版权元数据** | `IPTC Information`、`Copyright Info` | 防止把甲摄影师身份/机构署名批量污染到乙机身；须通过 *Creators' App* / XMP 单独配置 |
| **闪光灯与自定义白平衡** | `External Flash Set.`、`White Balance`（`Custom 1` / `Custom 2` / `Custom 3`） | 自定义白平衡标定矩阵仅留在本机 NVRAM（且抗 `[Camera Settings Reset]`，仅 `[Initialize]` 清除） |
| **生物识别库** | `Face Memory` | 已注册人脸特征数据涉隐私且绑定机身 NVRAM（`[Initialize]` 才销毁） |
| **FTP 与全部网络/安全凭据** | `FTP Transfer Func.`、`Network Streaming`、`Cloud Connection`、`WPS Push`、`Access Point Set.`、`Wi-Fi Frequency Band`、`IP Address Setting`、`Edit Device Name`、`Import Root Certificate`、`Access Authen. Settings`、`Security(IPsec)` | `FTP` 服务器配置由独立菜单 **`[Save/Load FTP Settings]`** 写入 `FTPSET/FTPSET01..DAT`；Wi-Fi 密码/根证书/设备名/IPsec/访问认证密码均属机密凭证，永不进 `CAMSET*.DAT` |
| **基础系统区域项** | `Language`、`Area/Date/Time Setting` | 防止跨时区/跨语种团队互导配置时意外篡改系统语言与时间基准 |

2. **`Slot-1` 硬锁定与 Tier-0 保险库 `EROFS (errno 30)` 边界（`实测事实` + `推断`）**：
   - **实测事实**：在 `[Save/Load Settings]` 菜单中，`[Media]` 介质源**硬锁定为 `Slot 1`**（菜单内**不存在**切换到 `Slot 2` 的子选项）；而在 `[Camera Set. Memory]` 中，`M1..M4` 可通过同级 **`[Memory/Recall Media]`**（`_f 0x763c`，默认 `Slot 1`）显式切换为 **`Slot 2`**。
   - **推断（Tier-0 恢复台架护栏）**：若测试台架将 `Slot 1` 挂载为受保护的**只读 Tier-0 恢复保险库**，任何通过 `[Save/Load Settings] -> [Save]`（写 `CAMSET01..10.DAT`）或 `[Delete]` 发起的写/删请求，以及 `[Memory/Recall Media] = Slot 1` 下的 `[Camera Set. Memory]` 写 `M1..M4`（`CAMPR*.DAT`），均**必须**在模拟 VFS/块设备层被强制阻断并返回 **`EROFS (errno 30)`**（参见 [`G92` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py)）；唯 `[Load]` 对 `Slot 1` 卡文件本身为只读读取（仍须阻断对宿主持久化 eMMC 的真实改写）。

### 3.3 `[Camera Set. Memory]`（`1..3` 机身 vs `M1..M4` 插卡）与 `FX6` `Project > All File` / `Scene File` 对照（`实测事实`）

| 对比维度 | `FX3` `Camera Set. Memory` 机身 `1..3` | `FX3` `Camera Set. Memory` 存储卡 `M1..M4` | `FX6 Ver. 6.01` `All File` / `User File` / `Scene File` |
| :--- | :--- | :--- | :--- |
| **存储载体与精确路径** | 机身内部 NVRAM（随 `CAMSET*.DAT` 一并保存/恢复） | 存储卡 **`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`**（经 `[Memory/Recall Media]` 可选 **`Slot 1`** 默认或 **`Slot 2`**） | **`Project > All File`**：`%c:%s/SONY/PRO/CAMERA/%s/%s.ALL`（**Slot B `Media(B)`** 最多 64 份 / 云端 / Mobile App / Utility SD）<br>**`Project > User File`**：`.USRF`；**`Paint/Look > Scene File`**：`%c:%s/SONY/PRO/SCENE/%s.SCN`；**`User 3D LUT`**：最多 16 份 `.cube` |
| **调出方式与重启需求** | `MODE` 键或 `[Recall Camera Setting]`；**实时生效，不重启** | `MODE` 键或 `[Recall Camera Setting]`；**实时生效，不重启**；若卡丢失/未插则不可调出 | `All File` 加载后**自动重启**；支持 **`All File Load Network Data`** 开关决定是否排除网络配置 |
| **Reset / Format 影响** | 抗 `[Camera Settings Reset]`；仅 **`[Initialize]`** 清除 | 随存储卡 **`[Format]`** 一并抹除；可跨同型号 FX3 迁移 | 随 `Media(B)` 格式化清除；另可导出至独立 Utility SD |
| **内容排除边界** | 均**不包含 `Custom Key/Dial Set.` 与 `Program Shift`** | 均**不包含 `Custom Key/Dial Set.` 与 `Program Shift`** | **`Reference File`**（`FX6 ns2 0x429b`/`0x4d52`）在 `FX6 appFw.so` 命中 **`0`** 次——属休眠 XDCAM 继承词条；`FX6 appFw.so` 亦休眠保留 Alpha `CAMSET/%s.DAT` |

---

## 4. 子系统 4：无物理 `Sync Terminal` 辟谣、`[External Flash Set.]` / `[Video Light Mode]` 与 `XLR-H1` 互斥 vs FX6 `TC IN/OUT` & 无 `GENLOCK`

### 4.1 彻底辟谣：`ILME-FX3` 无物理 PC 闪光同步端子（`Sync Terminal`），与休眠 ELF/UXC 残留严格隔离（`实测事实`）

> [!CAUTION]
> **常见误区辟谣（`实测事实`：`ILME-FX3` 机身无物理 `(Flash sync) terminal`）**：
> - **硬件端口事实**：与同源机身 `ILCE-7SM3`（Alpha 7S III）一致，**`ILME-FX3` 机身侧面完全没有物理 PC 闪光同步接口（`(Flash sync) terminal`）**（Alpha 家族中仅 `ILCE-1`、`ILCE-7RM5`、`ILCE-9` 系列等高阶静止画旗舰配备该物理同轴端子）。
> - **固件休眠残留实证**：在 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 与 UXC 中确能扫出 **`Flash Sync Spd. Prty.`**（`_f 0x6b31`，`BKID_APP_setting_flash_sync_spd_priority`、`BKID_APP_MR_setting_flash_sync_spd_priority`）及 **`SYNCHRO_TERMINAL_OUTPUT_SET_ON`**（`_g 0x645e`，简/繁中文串甚至为空 `""`），但 **`FX3 appFw.so` 内 `SYNCHRO_TERMINAL*` 符号命中数为 `0`**，且官方 `ilc/2210` Help Guide 对 `Sync Terminal` 与 `Flash Sync Spd. Prty.` **均为 `0` 页面暴露**。凡宣称 FX3 可配置机侧 `Sync Terminal` 同步端子的代码或文档均属把休眠共享代码误当现网接口的错判。

### 4.2 MI-Shoe `[External Flash Set.]` / `[Flash Mode]` 与 `[Video Light Mode]`（`HVL-LBPC` vs `XLR-H1` 物理互斥）（`实测事实`）

| 子项（精确路径） | `FX3 Ver. 7.02` 真值约束（`ilc/2210` + UXC + ELF） | 硬件安全与物理接口边界 |
| :--- | :--- | :--- |
| **`Exposure/Color -> [Flash] -> [Flash Mode]`**（`base 0xe5ce`） | 5 项：`Flash Off` / `Autoflash` / `Fill-flash` / `Slow Sync.` / `Rear Sync.`；**仅限 Still 静态照片模式** | 仅经机身顶部 **Multi Interface Shoe（MI 热靴）**触发；**必须使用机械快门**（电子快门下禁用闪光，最高同步速度 `1/250 s`；高于 `1/4000 s` 提示条纹风险）；严禁接 `>= 250 V` 高压或反极性第三方闪光灯（[`G120` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)） |
| **`Exposure/Color -> [Flash] -> [External Flash Set.]`**（`_f 0x6771`） | 包含 **`[Ext. Flash Firing Set.]`**（`_f 0x671d`）与 **`[Ext. Flash Cust. Set.]`**（`_f 0x705f`）；需闪光灯升级最新固件方可机内控参 | **`[Camera Settings Reset]` = `Not available`**，且**明文被排除在 `CAMSET01..10.DAT` 保存清单之外** |
| **`Setup -> [Setup Option] -> [Video Light Mode]`**（`_f 0x6211`） | **Still / Movie / S&Q 全管线支持**，专用于 **`HVL-LBPC`** LED 视频灯（`BKID_APP_setting_video_light_set`）：<br>① **`Power Link`**（`_f 0x651b`，**出厂默认**：随相机开关机联动）；<br>② **`REC Link`**（`_f 0x652f`：仅录制起停联动）；<br>③ **`REC Link&STBY`**（`_f 0x647a`：录制点亮、待机转为 STBY 低亮待命）；<br>④ **`Auto`**（ELF `VIDEO_LIGHT_SET_AUTO_LOW_LIGHT`，`_f 0x698e`：低照度自动点亮） | **MI-Shoe 与 `XLR-H1` 物理绝对互斥**：`FX3` 随机 **`XLR-H1`** 音频手柄通过底部带双侧锁紧螺丝的电气底座**独占机身唯一的 MI 热靴**，且安装到 `XLR-H1` 顶部的 Accessory Shoe Kit 仅为一颗**无电气触点的纯机械冷靴（passive cold shoe）**——因此 **`XLR-H1` 与需 MI 热靴通信/联控的 `HVL-LBPC`（或 MI 热靴闪光灯）物理上无法同时直插 MI Shoe 联用**。拆除 `XLR-H1` 后直插 MI Shoe 亦受 Stage-B **`PMIC 5V <= 900 mA`** 供电上限保护（[`G110` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)） |

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` & `PXW-FX9`：Video Light、`TC IN/OUT` BNC 与无 `GENLOCK` 分水岭（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） | `PXW-FX9`（行业定位对照） |
| :--- | :--- | :--- | :--- |
| **Video Light 模式集** | `Setup -> [Setup Option] -> [Video Light Mode]`：**4 模式**（`Power Link` / `REC Link` / `REC Link&STBY` / **`Auto`**） | `Technical > Video Light Set`（`ns2 0x4289`）：**仅 3 模式**（`Power Link` / `Rec Link` / `Rec Link + Stby`；`VAL_setting_video_light_set_*` **无 `Auto` 模式**） | `Technical > Video Light Set`：3 模式（`HVL-LBPC`） |
| **Flash 闪光灯体系** | 有 Still 专用 `[Flash]` 菜单（MI 热靴，`1/250 s`）；**无物理 PC `Sync Terminal`** | **无任何 Still `[Flash]` UI**；仅 `FX6 appFw.so` 休眠残留 `1` 条 `SYNCHRO_TERMINAL`（且保留视频防闪条纹 `Flash Band Reduce` `ns2 0x4215`） | 纯电影机无 Still Flash |
| **时码同步物理端口** | **无 BNC**；依赖机侧 `Multi/Micro USB` 转接 Sony 时码线输入（无内建 TC BNC 锁相输出） | **配备单颗可切换 `TC IN / TC OUT` BNC**：设为 `IN` 时进入外部锁相（`EXT-LK`），设为 `OUT` 时对外输出 TC | **配备可切换 `TC IN / TC OUT` BNC** |
| **Genlock / REF 同步** | **无** | **无物理 `GENLOCK` BNC 端口**（核心产品线降级刀法！尽管 `FX6 appFw.so` 编译保留 **107 条休眠 `GENLOCK` 符号**且 `ns2 0x4262, 0x56d5..0x56d7` 存在完整 Genlock 状态串） | **配备独立可切换 `GENLOCK IN / REF OUT` BNC**，支持多机位基带帧同步 |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `30` 个 `AREA_GMT_*`、错字 `convert_setting_daylight_saving_to_saylight_saving`、`37dlg_rec203_initial_setting_controller`、`BKID_APP_setting_{grid_line_display,grid_line_type,marker_display,guide_frame}` & 已删 `_movie` 键、`%c:%s/SONY/SETTING/%s/{CAMSET,CAMPR,FTPSET}`（`0` 条 `PRO/CAMERA`）、`VIDEO_LIGHT_SET_*`（含 `AUTO_LOW_LIGHT`）、`0` 条 `SYNCHRO_TERMINAL` |
| [`FX3 libSaveLoadSettings.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so) | `18,760` | `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7` | `SaveLoadSettingsIf::requestTo{Read,Check,Write}`、`SaveLoadSettings::proc{Read,Check,Write}`、`Backup_{get_datasize,read,write}`、`infra_getCallbackFuncTable{,Ftp}`、`MWF::EventWrapper` |
| [`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin) (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（零专有原始字节泄漏） |
| [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `USER_MENU_CLOCK_SET0..6`、休眠 `summer_time_name_dst`、`USER_MENU_MARKER0..19`、`PRO/CAMERA/%s/%s.{ALL,USRF}` & `PRO/SCENE/%s.SCN`（`0` 条 `REFERENCE_FILE`）、`VAL_setting_video_light_set_*`（无 `Auto`）、`107` 条休眠 `GENLOCK` 符号 |
| [`FX3 string_english_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc) / `.uxc` / `_g.uxc` | `373,820` / `165,740` / `69,600` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `_f`（`7,475` 条，`0x1e1c`）/ `base`（`0x1e04`）/ `_g`（`0x1e00`）全量包 |
| [`FX3 string_simplifiedchinese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc) / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / `base` / `_g` 精确映射 |
| [`FX3 string_traditionalchinese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc) / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / `base` / `_g` 精确映射 |
| [`FX3 string_japanese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc) / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `_f` / `base` / `_g` 精确映射 |
| [`FX6 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc) / [`_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc) | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `FX6` `ns1`（`5,044` 条）/ `ns2`（`5,916` 条）：`Clock Set` & `UTC -12:00..+14:00`、`Guide Frame` & `Center Marker`、`All File / User File / Scene File`、休眠 `Reference File` & `Genlock` & `Daylight Saving Time` |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，`_f` / `base` / `_g` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x6a9c` / `base` `0xe91a` / `base` `0xe917` | `Area/Date/Time Setting` / `Area Setting` / `Daylight Savings` | `区域/日期/时间设置` / `区域设置` / `夏时制` | `區域/日期/時間設定` / `區域設定` / `日光節約時間` | `エリア/日時設定` / `エリア設定` / `サマータイム` | **活跃**（抗 Reset，仅 `[Initialize]` 重置；取代 `base 0xe87f` `Date/Time Setup`） |
| `_f` `0x670d` / `0x7416` / `0x7976` / `0x65da` | `Date Format` / `Y-M-D` / `M-D-Y` / `D-M-Y` | `日期格式` / `年-月-日` / `月-日-年` / `日-月-年` | `日期格式` / `年-月-日` / `月-日-年` / `日-月-年` | `表示形式` / `年-月-日` / `月-日-年` / `日-月-年` | **活跃**（同步对应 `base 0xe888/0xe887/0xe97e`） |
| `_g` `0x64a8` / `0x63a6` | `Initial Setting with Creators' App` / `Sets the “Area/Date/Time Setting”...` | `使用Creators' App进行初始设置` / `设置"区域/日期/时间设置"以执行...` | `使用Creators' App進行初始設定` / `設定"區域/日期/時間設定"以執行...` | `Creators' Appで初期設定` / `本機能を行うためには「エリア/日時設定」...` | **活跃**（初始向导与未设时钟阻断提示） |
| `_f` `0x6f9d` / `0x69c9` / `0x70c5` | `Grid Line Display` / `Grid Line Type` / `Grid Line Display Select` | `网格线显示` / `网格线类型` / `网格线显示选择` | `格線顯示` / `格線類型` / `格線顯示選擇` | `ｸﾞﾘｯﾄﾞﾗｲﾝ表示` / `ｸﾞﾘｯﾄﾞﾗｲﾝの種類` / `ｸﾞﾘｯﾄﾞﾗｲﾝ表示切換` | **活跃**（全管线可用；开 `HDMI Info.` 时出 HDMI；抗 Reset） |
| `_f` `0x78ae` / `0x715a` / `0x786c` | `Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid` | `三等分线网格` / `方形网格` / `对角 + 方形网格` | `九宮格` / `方格` / `對角線+方格` | `3分割` / `方眼` / `対角+方眼` | **活跃**（同步对应 `base 0xe809/0xe806/0xe807`） |
| `_f` `0x6803` / `0x62f9`（`_g 0x62a0`） | `Marker Display` / `Guideframe` | `标记显示` / `引导框` | `錄影輔助標誌顯示` / `水平導引框` | `マーカー表示` / `ガイドフレーム` | **活跃**（仅 Movie/S&Q；**绝不输出 HDMI**；抗 Reset） |
| `_f` `0x6254` / `0x7c53` / `0x7c5a` / `0x763c` / `0x71ae` | `Save/Load Settings` / `Cloud(Private)` / `Cloud(Share)` / `Memory/Recall Media` / `Save/Load FTP Settings` | `保存/加载设置` / `云端(私有)` / `云端(共享)` / `选择媒体` / `保存/加载FTP设置` | `儲存/載入設定` / `雲端(私有)` / `雲端(共享)` / `記憶/回復插槽` / `儲存/載入FTP設定` | `設定の保存/読込` / `クラウド(個人)` / `クラウド(共通)` / `登録/呼出ﾒﾃﾞｨｱ` / `FTP設定の保存/読込` | **活跃**（`Save/Load` 锁死 `Slot 1`；`Camera Set. Memory` 可选 `Slot 2`） |
| `_g` `0x62dd` / `0x624d` / `0x61d7` | `Load?...Reboots after loading.` / `This file cannot be loaded.` / `Loading failed.` | `加载?...加载后重启。` / `无法加载该文件。` / `加载失败。` | `載入?...載入後重新開機。` / `無法載入此檔案。` / `載入失敗。` | `読み込みますか？...再起動...` / `読み込めないファイルです` / `読み込みに失敗しました` | **活跃**（`libSaveLoadSettings.so` 校验拦截与载入重启提示） |
| `_f` `0x6b31` / `_g` `0x645e` | `Flash Sync Spd. Prty.` / `SYNCHRO_TERMINAL_OUTPUT_SET_ON` | `闪光同步速度优先` / `""` *(空串)* | `閃光同步速度優先` / `""` *(空串)* | `ﾌﾗｯｼｭ同調速優先` / `SYNCHRO_TERMINAL_OUTPUT_SET_ON` | **FX3 7.02 休眠！**（无物理 PC 同步端子，`ilc/2210` 零暴露） |
| `_f` `0x6771` / `0x671d` / `0x705f` / `base` `0xe5ce` | `External Flash Set.` / `Ext. Flash Firing Set.` / `Ext. Flash Cust. Set.` / `Flash Mode` | `外置闪光灯设置` / `外置闪光灯闪光设置` / `外闪光灯自定义设置` / `闪光模式` | `外接閃光燈設定` / `外接閃光燈閃光設定` / `外接閃光燈自設設定` / `閃光燈模式` | `外部フラッシュ設定` / `外部ﾌﾗｯｼｭ発光設定` / `外部ﾌﾗｯｼｭｶｽﾀﾑ設定` / `フラッシュモード` | **活跃**（仅 Still 机械快门 MI-Shoe；排除出 `CAMSET*.DAT`） |
| `_f` `0x6211` / `0x651b` / `0x652f` / `0x647a` / `0x698e` | `Video Light Mode` / `Power Link` / `REC Link` / `REC Link&STBY` / `...automatically turns on when it is dark.` | `视频灯模式` / `电源联动` / `拍摄联动` / `拍摄联动+STBY` / `光线黑暗时视频灯自动打开。` | `視訊燈模式` / `電源連結` / `拍攝連結` / `拍攝連結與STBY` / `視訊燈在黑暗環境中自動開啟。` | `ビデオライトモード` / `電源連動` / `録画連動` / `録画連動+STBY点灯` / `暗いときに自動でビデオライトが点灯します` | **活跃**（4 模式全管线；与占用 MI Shoe 的 `XLR-H1` 物理互斥） |

---

## 6. 仓内安全守卫（`fx3-safety`）交叉对照与 H408 结论闭环

1. **仓内守卫落地与本次新增高价值发现对齐（`实测事实`）**：
   - **`[Grid Line]` Clean-HDMI 隔离 vs `[Marker Display]` 抗 Reset**：对照 [`G89/G90`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py) 与 [`G142`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py)——`[Grid Line Display]` 是唯一受 `[HDMI Info. Display]` 影响可透传到外部 HDMI 的构图参考线，而 `[Marker Display] -> [Guideframe]` 绝对机内独占且**5 个子项全部抗 `[Camera Settings Reset]`**。
   - **`[Save/Load Settings]` `Slot-1` 硬锁定、`libSaveLoadSettings.so` 与排除边界**：对照 [`G92`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py) 与 [`G122`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)——实证 `CAMSET01..10.DAT` 严格落于 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`（非 `PRO/CAMERA`）且卡槽锁死 `Slot 1`，对只读 Tier-0 保险库执行保存/删除必须返回 `EROFS (errno 30)`；完整官方排除清单确保凭据、白平衡矩阵、`External Flash Set.`、`Area/Date/Time Setting` 与 `Language` 永不泄露或被跨机覆盖。
   - **`[Area/Date/Time Setting]`、MI-Shoe `[Video Light Mode]` 与无 `Sync Terminal`**：对照 [`G110`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py) 与 [`G120`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h408-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)——补全了 `30` 时区表、ELF 错字 `saylight`、RTC `>= 24h` 关机充电周期、无物理 `Sync Terminal` 实证，以及 **`XLR-H1` 独占电气 MI 热靴与 `HVL-LBPC` 物理互斥**的工程闭环。
2. **严格边界声明**：本波次（`H408`）严格单文件交付本调研报告，未修改任何现有 Python 守卫脚本或模拟器代码；所有本地 donor 读取均以 `os.O_RDONLY` 只读执行，`raw_firmware_bytes_leaked = 0`。
