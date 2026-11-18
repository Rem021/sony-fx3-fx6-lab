# 全球 Sony 实机情报 Wave 67（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Pixel Mapping]` / `[Auto Pixel Mapping]` vs FX6 `APR`、`[Monitor]` / `[Monitor Brightness]` / `[Display Quality]` 与休眠 EVF 辟谣 vs FX6 `VF Adjust`、`[AF On]` / `[Eye AF]` / `[Tracking On]` 与仅限静态 `[Recall Custom hold 1–3]`（无独立 WB）辟谣 vs FX6 `Push AF/AGC/Iris`、以及 `[External Output]` HDMI `Rec. Media dur HDMI Output` / `TC Output` / `REC Control` 与 `Slot-1` `EROFS=30` 护栏 vs FX6 `SDI/HDMI` 矩阵）

- **日期**：`2026-11-17`
- **任务 / 波次**：`H405` · **Wave 67（Global Sony Real-Hardware Empirical Intelligence Wave 67）**
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Pixel Mapping / Auto Pixel Mapping / Silent Mode Settings / Monitor Brightness / Display Quality / Monitor Flip Direction / Bright Monitoring / Reg. Custom Shoot Set (Recall Custom hold 1–3) / AF On / Eye AF / Tracking On / HDMI Resolution / HDMI Output Settings / HDMI Info. Display / CTRL FOR HDMI / List of default setting values / Resetting to default values*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Technical > APR (Auto Pixel Restore) / Monitoring > VF Setting / VF Adjust / VF Mode / MIRROR Switch / Assignable Button > Push AF / Push AGC / Push Auto Iris / TC/Media > HDMI TC Out / Monitoring > Output On/Off & Output Format / Project > SDI/HDMI Rec Control / Simultaneous RAW + SDI/HDMI Matrix*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)、[`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc)、[`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin)、[`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)、[`FX6 string_english.uxc` / `_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc)
  - 仓内安全守卫交叉对照：[`G85` Auto Pixel Mapping](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py)、[`G97` Display Quality & Monitor](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py)、[`G102` HDMI REC Control](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py)、[`G113` HDMI Info Display](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)、[`G122` Custom Hold & CAMSET](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方 Help Guide/说明书条目）与 **`推断`**（Tier-0 `Slot 1` 只读保险库、`EROFS=30` 拦截边界与模拟器台架风险推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`Setup -> [Setup Option] -> [Pixel Mapping]` & `[Auto Pixel Mapping]` vs FX6 `APR`）**：
   - **实测事实（菜单真相与双层抗复位机制）**：`ILME-FX3 Ver. 7.02` 在 `Setup -> [Setup Option]` 下暴露 **`[Auto Pixel Mapping]`**（`_f 0x7734`，出厂默认 **`On`** / `Off`，**不支持 `[Camera Settings Reset]`**，仅 `[Initialize]` 还原）与 **`[Pixel Mapping]`**（`_f 0x61f7`，手动触发并要求盖紧镜头盖遮光、完成后自动重启）。当设在 `Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Target Function Settings] -> [Auto Pixel Mapping]`（默认 `Off` / UXC `_f 0x64e7` `Not Target`，**可 Reset**）保持 `Off` 而 Setup 端为 `On` 时，关机后仍会按周期在关机阶段执行像素映射并**发出机械快门响声**（ELF `vdf_set_shutter_mute_by_pixel_mapping`）。
   - **实测事实（执行门控与符号拼写缺陷）**：`FX3 appFw.so` 实证存在电池电量门控（`INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`、`BATTERY_CHECK_FOR_PIXEL_MAPPING_{LOWER,UNKNOWN,UPPER}`），`_g 0x63f1` / `0x60e7` 实证遮光不足失败提示与重启要求；但 `ilc/2210` 文档与 `FX3 appFw.so`（`PRM_HAITA_*pixel_map*` 仅命中 `silent_mode` 互斥）**未记录**对 `Auto Pixel Mapping` 的独立 USB 流式传输或高温阻止表（不同于 FX3 `[Shutter When Pwr OFF]` 缺失）。ELF 内部存在两处 Sony 原厂拼写错字：**`BKID_APP_setting_notification_for_pixel_mappinng`**（双 `n`）与 **`BKID_APP_pixel_mapping_excuted_status`**（缺 `e`）。
   - **对比 `ILME-FX6 Ver. 6.01`**：使用 **`Technical > APR`（Auto Pixel Restoration）**（`FX6 ns1 0x2e4e..0x339c`、`ns2 0x40b5..0x4283`），要求关闭光圈/盖上镜头盖并用黑布完全遮光（`ns1 0x3324`，ELF `PIXEL_MAPPING_RESULT_{LIGHT_DETECTED,INVALID_TEMPERATURE}`）；**CMOS 架构的 FX6 官方不开放 CCD 时代的 `ABB`（Auto Black Balance）菜单**，但 `FX6 appFw.so` 与 `ns1 0x2494` / `ns2 0x4413, 0x4ec8` 仍残留休眠的 `auto_black_balance` 共享符号。

2. **子系统 2（`Setup -> [Monitor]` 组名纠偏、`[Monitor Brightness]` / `[Display Quality]` 与休眠 EVF 辟谣 vs FX6 `VF Adjust`）**：
   - **实测事实（`[Finder/Monitor]` 组名辟谣）**：无 EVF 机身 `ILME-FX3 Ver. 7.02` 的设置分组实为 **`Setup -> [Monitor]`**，**并非 `[Finder/Monitor]`**！该组下实装 **3 项**（**全部抗 `[Camera Settings Reset]`**，仅 `[Initialize]` 还原）：
     1. **`[Monitor Brightness]`**（`base 0xe44b`，`BKID_APP_setting_lcd_brightness`）：`Manual`（**默认**，`-2..+2`） / `Sunny Weather`（`_f 0x7a61` / `base 0xe1da`）。
     2. **`[Display Quality]`**（`_f 0x6c5e`，`BKID_APP_setting_display_quality`）：**`Standard`（默认**，续航最长） / `High`（高耗电，且官方明确**机身温度升高时会被强制锁定回 `Standard`**）。
     3. **`[Monitor Flip Direction]`**（`_f 0x6a24`，`BKID_APP_extern_menu_flip`）：**`Auto`（默认）** / `Horizontal Flip` / `180 Degree Flip` / `No Flip`（另配自定义键 `[Switch Monitor Flip Disp]` `_f 0x72d6`）。
   - **实测事实（休眠 EVF 符号全量辟谣）**：`FX3 appFw.so` 与 UXC 虽编译了 `Finder/Monitor Sel.`（`_f 0x6daf`）、`Viewfinder Bright.`（`_f 0x6935` / `base 0xe662`）、`Viewfinder Color Temp.`（`base 0xe38d`，`BKID_APP_setting_evf_adjustment` `MINUS_2..PLUS_2`）、`Finder Frame Rate`（`_f 0x604a` / `0x718c`，`STANDARD/HIGH/HI_PLUS`），但 **`ilc/2210` 实机菜单暴露数为 `0`**，全部为休眠 Alpha 共享代码。
   - **对比 `ILME-FX6 Ver. 6.01`**：FX6 暴露 **`Monitoring > VF Setting`**（`ns2 0x423c`：`Brightness` `1..15` 默认 `8`，`Color Mode` `Color/B&W`）、可分配按键 **`VF Adjust`**（`ns1 0x2223`，未接取景器弹窗 `ns1 0x26b5`）与 **`VF Mode`**，以及取景器硬件 **`MIRROR` 拨钮**（`Off / B/T / ROT`）；**并不存在 `VF Adjust > Backlight / Contrast / Chroma / Color Temp.` 四级子菜单**（`FX6 appFw.so` 另保留休眠 Alpha `setting_evf_adjustment`）。

3. **子系统 3（`[AF On]`、`[Eye AF]`、`[Tracking On]` 与仅限静态 `[Recall Custom hold 1–3]` 辟谣 vs FX6 `Push AF/AGC/Iris`）**：
   - **实测事实（静态限定 + 无独立 White Balance 辟谣）**：
     - `Shooting -> [Shooting Mode] -> [Reg. Custom Shoot Set]`（`_f 0x6282`/`0x7631`）下的 **`[Recall Custom hold 1..3]`**（`_f 0x60b4, 0x7581, 0x725b`）**严格仅限静态照片 `P/A/S/M` 模式**（`ilc/2210` 明确限定 `available only when the shooting mode is set to P/A/S/M`；`FX3 appFw.so` 中 `EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET{1..3}` 仅存于静态自定义键分发表，Movie/S&Q 下返回不可用 / 等效 `EOPNOTSUPP`）。
     - **精确 11 个可勾选参数位（`is_checked_recall_custom_hold0..10`）**：`shooting_mode`、`aperture`、`shutter_speed`、`exposure_comp`、`iso_sensitivity`（含 `iso_auto_rate_{min,max}`）、`metering_mode`（含 `_spot`）、`drive_mode`（**不含 Self-timer**，支持 Cont./Brackets）、`focus_mode`、`focus_area`、`af_on`、`still_af_track_sens`。**辟谣：`White Balance` 并非 `Recall Custom hold 1–3` 的独立可勾选参数**（`FX3 appFw.so` 中 `shoot_set_registration_white_balance` 命中 `0`；白平衡仅作为 `Drive Mode` 下 `WB bracket` 附属字段存在）。
     - `Reg. Custom Shoot Set` **抗 `[Camera Settings Reset]`**（`Not available`，仅 `[Initialize]` 清除），随 `Save/Load Settings` 持久化至 `CAMSET*.DAT`。
   - **对比 `ILME-FX6 Ver. 6.01`**：无 `Recall Custom hold 1–3`，改为 `Project > Assignable Button` 下的 **`Push AF`**（`Push AF Mode`：`AF` / `Single-shot AF(AF-S)` 及 `Push AF/Push MF`）、**`Push AGC`**（`Cine EI` / `Cine EI Quick` 与 `Bokeh Control = On` 下禁用）、**`Push Auto Iris`**（镜头 `MANUAL` 或 `Bokeh Control = On` 下禁用）与 `One Push AF / Auto Iris`；`High/Low Key`（`ns2 0x4b25`）在 FX6 上仅属休眠共享字面量。

4. **子系统 4（`Setup -> [External Output]` HDMI 深度拆解、休眠 `4K/2K`/`24p/60p` 辟谣、`Slot-1` `EROFS=30` 护栏 vs FX6 `SDI/HDMI` 矩阵）**：
   - **实测事实（精确菜单门控、24.00p 重启链与原厂 ELF 拼写错字）**：
     - `[HDMI Output Settings]` 包含 **`Rec. Media dur HDMI Output`**（默认 `On` / `Off(HDMI Only)`；`S&Q` 锁 `On`）、**`Output Resolution`**（默认 `Auto` / `2160p` / `1080p` / `1080i`；开启 `Log` 或 `PPLUT1..4` 且内录 `On` 时降为 `1080`）、**`4K Output Set.(HDMI Only)`**（`59.94p/50p/29.97p/25p/23.98p/24.00p 10bit`，其中 `24.00p` 切换与非 `24.00p` 强制重启且回放隔离 `_g 0x61d3/0x6413/0x6423`）、`RAW Output`（默认 `Off`）& `RAW Output Setting`、**`Time Code Output`**（默认 `Off`，`S&Q` 下禁用）、**`REC Control`**（默认 `Off`，**前置硬条件必须 `[Time Code Output] = On` + 兼容外部录机**，配合 `PRM_HAITA_setting_rec_control_*` 门控 HDMI 连接/媒体/USB 流式传输，屏幕显示 `(STBY)`/`(REC)`，受 `[REC w/ Shutter]` 触发）、`4ch Audio Output`（默认 `CH1/CH2` / `CH3/CH4`）。
     - `[HDMI Info. Display]`（默认 `On` 致机身 LCD 黑屏；`Off(HDMI Only)` 或 `RAW Output = On` 时**临时强制切为 `Off`**）；`[CTRL FOR HDMI]`（默认 `On`，**ELF 拼写错字 `BKID_APP_setting_ctrl_for_hmdi`**）。`Setup -> [External Output]` 全项**抗 `[Camera Settings Reset]`**。
     - **休眠辟谣**：`4K/2K Output` 与 `24p/60p Output` 在 `ilc/2210` 与 `FX3 appFw.so` 均为 **`0` 命中**（仅 `_f 0x632b`/`0x781c` 保留休眠 `24p/60p Output` UXC 词条）。
   - **实测事实与 Tier-0 推断（`Slot 1` `EROFS=30` 危险）**：当 `[Rec. Media dur HDMI Output] = On`（出厂默认，且 `S&Q` 锁 `On`）且录制目标指向 `Slot 1` 时，任何 `M4ROOT/CLIP/*.MP4` 或 `AVF_INFO` 写入若落到 Tier-0 只读 `Slot 1` 恢复保险库，**推断**台架必须拦截并返回 **`EROFS (errno 30)`**。
   - **对比 `ILME-FX6 Ver. 6.01`**：`TC/Media > HDMI TC Out`、`Monitoring > Output On/Off`（独立 `SDI`/`HDMI`）、`Project > SDI/HDMI Rec Control`（`Off` / 无卡时 `SDI/HDMI Remote I/F` / 有卡帧精确 `Parallel Rec`；HDMI 触发同样要求 `HDMI TC Out = On`），支持 `12G/6G/3G-SDI + HDMI` 同步双路输出矩阵（SDI `4K RAW` 可同步输出 `4K` HDMI；`RAW(HDMI) 4240×2392` 迫使 SDI 降为 `1920×1080`；`S&Q > 60fps` 且 `SDI=On` 或 `RAW` 时 HDMI 降为 FHD）。

---

## 1. 子系统 1：`Setup -> [Setup Option] -> [Pixel Mapping]` & `[Auto Pixel Mapping]` vs FX6 `APR`

### 1.1 `ILME-FX3 Ver. 7.02` 像素映射菜单、Reset/Initialize 边界与执行门控（`实测事实`）

1. **菜单路径与出厂持久化真值（`ilc/2210` + `FX3 appFw.so`）**：

| 菜单项（精确路径） | `FX3 Ver. 7.02` 选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | `[Initialize]` | UXC `resid16` / ELF 实证（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Auto Pixel Mapping]`**<br>(`Setup -> [Setup Option]`) | **`On`（默认）** / `Off`<br>*(设 `Off` 时提示每 3 天左右手动执行 1 次 `[Pixel Mapping]`)* | **Not available**<br>*(抗 Reset)* | **还原为 `On`** | `_f 0x7734` / `0x737f`；`_g 0x63fa`；`BKID_APP_setting_auto_pixel_mapping`、`VAL_..._AUTO_PIXEL_MAPPING_{ON,OFF}`、`PID_SET_AUTO_PIXEL_MAPPING` |
| **`[Pixel Mapping]`**<br>(`Setup -> [Setup Option]`) | 手动立即执行（确认 `[OK]`）；要求遮光，期间机身不可操作，完成后**自动重启** | —（执行动作） | — | `_f 0x61f7`；`_g 0x63f1` / `0x63f6` / `0x60e7` / `0x6265`；`FUNC_execute_manual_pixel_mapping`、`N5model30sequence_execute_pixel_mappingE`、`SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING` |
| **`[Target Function Settings] -> [Auto Pixel Mapping]`**<br>(`Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`) | **`Off`（默认，即不静音 `Not Target`）** / `On`<br>*(仅当 `[Silent Mode] = On` 生效)* | **Can be reset**<br>*(可复位为 `Off`)* | **还原为 `Off`** | `_f 0x64e7`（`Not Target`）；`_g 0x623d`；`BKID_APP_setting_silent_detail_setting_auto_pixel_mapping`、`PRM_HAITA_setting_silent_detail_setting_auto_pixel_mapping_setting_silent_mode` |
| **休眠 / 内部状态相关符号**<br>*(无独立用户开关)* | `[Pixel Map. Notification]` 与 `[Shutter When Pwr OFF]` 在 FX3 `ilc/2210` 均**不暴露** | — | — | `_f 0x693f` / `0x6fff` / `0x7979`；`_g 0x63ab`；**ELF 拼写错字：`BKID_APP_setting_notification_for_pixel_mappinng`**、**`BKID_APP_pixel_mapping_excuted_status`**（含 `_date_time_{year..second}`、`vdf_set_shutter_mute_by_pixel_mapping`） |

2. **关机自动映射与机械快门声（`实测事实`）**：
   - 当 `Setup -> [Auto Pixel Mapping] = On` 时，机身定期在**电源关闭时**自动优化影像传感器；即便已开启 `Shooting -> [Silent Mode] = On`，由于 `[Silent Mode Settings] -> [Target Function Settings] -> [Auto Pixel Mapping]` 出厂默认 **`Off`**（不作为静音目标），关机后仍会通过 `vdf_set_shutter_mute_by_pixel_mapping` 闭合机械快门并**发出快门声音**。
   - **电池与遮光门控**：ELF `sequence_execute_pixel_mapping` 联动 `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`（`BATTERY_CHECK_FOR_PIXEL_MAPPING_{LOWER,UNKNOWN,UPPER}`），电量不足时禁止执行像素映射；手动执行 `[Pixel Mapping]` 必须盖紧镜头盖（`_g 0x63f1`），遮光不严会失败并要求重试（`_g 0x60e7`）。
   - **对“USB/流式传输/过热阻断 Auto Pixel Mapping”说法的边界说明（`实测事实`）**：`ilc/2210` *Auto Pixel Mapping* / *Pixel Mapping* 页面仅明确指出电量不足时不执行以及完成后切勿断电/拔卡，**并未**单列 USB 供电/USB 流式传输阻止规则；`FX3 appFw.so` 内的 `PRM_HAITA_*pixel_map*` 亦仅命中 `silent_mode` 互斥（`0` 条 USB/streaming/temperature `PRM_HAITA` 条目与 `pixel_mapping` 绑定）。是否会在热关机/USB 供电待机期间延后，属于固件关机状态机内部调度（若未拆出运行时调度逻辑则不作臆断）。

### 1.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `APR` 与无 `ABB` 对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **菜单路径与命名** | `Setup -> [Setup Option] -> [Pixel Mapping]` / `[Auto Pixel Mapping]`<br>*（`_f 0x76b5` 虽含共享 `APR` 词条，UI 不使用）* | **`Technical > APR > Execute / Cancel`**（`Auto Pixel Restore` / `Auto Pixel Restoration`，`FX6 ns1 0x2e4e..0x339c`、`ns2 0x40b5..0x4283`） |
| **光学遮蔽与前条件** | 安装镜头盖遮光（`_g 0x63f1`），执行后自动重启（无需物理黑布说明） | **无内置机械快门/内置物理遮光帘**：`ns1 0x3324` 明文要求 **`"Cover the Lens to Exclude All Light. Then Execute Auto Pixel Restore."`**（`5-024-458-18` 要求盖镜头盖并加黑布完全遮光）；`FX6 appFw.so` 通过 `PIXEL_MAPPING_RESULT_LIGHT_DETECTED` 与 `PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE` 校验遮光与机身温度 |
| **传感器校准机制（无 `ABB`）** | 全自动关机周期或手动像素映射 | **CMOS 架构不支持 CCD 时代的 `ABB`（Auto Black Balance）菜单**：黑电平微调由 `Paint/Look > Black`（`Master Black` / `R/B Black`）负责，坏点补偿由 `APR` 完成；`FX6 appFw.so` 及 `ns1 0x2494` / `ns2 0x4413, 0x4ec8` 仍保留来自共享 ProCam 代码库的**休眠 `auto_black_balance` 符号**（实机菜单未暴露） |

---

## 2. 子系统 2：`Setup -> [Monitor]`（辟谣 `[Finder/Monitor]`）、`[Display Quality]` 与休眠 EVF vs FX6 `VF Adjust`

### 2.1 `ILME-FX3 Ver. 7.02` `Setup -> [Monitor]` 全量真值与休眠 EVF 符号辟谣（`实测事实`）

> [!CAUTION]
> **菜单组名与 EVF 功能双重辟谣（`实测事实`）**：
> 1. **无 `[Finder/Monitor]` 分组**：`ILME-FX3` 无电子取景器（EVF），`ilc/2210` 中 `Setup` 下的显示分组名称严格为 **`Setup -> [Monitor]`**，**并非 `[Finder/Monitor]`**。
> 2. **4 个 EVF 项在 `FX3 Ver. 7.02` 全部休眠**：`FX3 appFw.so` 与 UXC 中存在 `Finder/Monitor Sel.`（`_f 0x6daf`，`BKID_APP_setting_finder_monitor`）、`Viewfinder Bright.`（`_f 0x6935` / `base 0xe662`，`BKID_APP_setting_viewfinder_bright`）、`Viewfinder Color Temp.`（`base 0xe38d`，`BKID_APP_setting_evf_adjustment` `MINUS_2..PLUS_2`，`N5model27sequence_set_evf_color_tempE`）与 `Finder Frame Rate`（`_f 0x604a`/`0x7582`/`0x718c`，`BKID_APP_setting_finder_framerate` `STANDARD/HIGH/HI_PLUS`），但 **`ilc/2210` 实机菜单暴露数为 `0`**，均属与 `ILCE-7SM3`/`ILCE-7M4` 共源的休眠代码。

| 菜单项（`Setup -> [Monitor]`） | `FX3 Ver. 7.02` 真值选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | `[Initialize]` | ELF / UXC 实证与锁定规则（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Monitor Brightness]`** | **`Manual`（默认，`-2` 至 `+2`）** / `Sunny Weather`<br>*(注意：`Sunny Weather` 亮度极高，官方提示室内勿常开)* | **Not available** | **还原 `Manual`** | `base 0xe44b` / `0xe1da`、`_f 0x7a61`；`BKID_APP_setting_lcd_brightness`、`_brightness_setup_manual`；`CUSTOM_LCD_BRIGHTNESS_BRIGHTNESS_SETUP_{MANUAL,SUNNY_WEATHER}`；`INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT`（电源/热管理降亮通知） |
| **`[Display Quality]`** | **`Standard`（默认，续航最长）** / `High`<br>*(使用 `[High]` 功耗显著上升)* | **Not available** | **还原 `Standard`** | `_f 0x6c5e` / `0x7ac6` / `0x6664`；`BKID_APP_setting_display_quality`、`FINDERMONITOR_DISPLAY_QUALITY_{STANDARD,HIGH}`。**温度锁**：`ilc/2210` 明文指出**机身温度升高时 `[Display Quality]` 可能锁定在 `Standard`** |
| **`[Monitor Flip Direction]`** | **`Auto`（默认）** / `Horizontal Flip` / `180 Degree Flip` / `No Flip`<br>*(可配合自定义键 `[Switch Monitor Flip Disp]` 快捷切换)* | **Not available** | **还原 `Auto`** | `_f 0x6a24` / `0x7780` / `0x6fcc` / `0x7363` / `0x72d6`；`BKID_APP_extern_menu_flip`、`EVENT_FUNC_CUSTOM_MONITOR_FLIP_DISPLAY_SWITCH_{ON,OFF}` |
| *对比关联项：`[Bright Monitoring]`*<br>(`Shooting -> [Shooting Display]` / 自定义键) | 开/关取景增亮（夜景构图，延长曝光预览帧时间；**仅自定义键/拍摄显示，不在 `[Monitor]` 组**） | — | — | `_f 0x701f`；`EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_{ON,OFF}`、`CAUTION_ID_FACTOR_CAM_SET_BRIGHT_MONITORING_ON_MSG`（实证与 `[Monitor Brightness]` 分属不同模块，`PRM_HAITA_*lcd_brightness*` 命中为 `0`） |

### 2.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `VF Setting` & `VF Adjust` 辟谣对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **取景器硬件与菜单** | **无 EVF 机身**；EVF 菜单（含 `Viewfinder Color Temp.`、`Finder Frame Rate`）全部休眠 | 配备可拆卸 LCD 取景器；**`Monitoring > VF Setting`**（`FX6 ns2 0x423c`）仅暴露 **`Brightness`**（`1..15`，默认 `8`）与 **`Color Mode`**（`Color` / `B&W`） |
| **快捷键与物理镜像** | 仅屏幕翻转 `[Monitor Flip Direction]` | `Project > Assignable Button` 提供 **`VF Adjust`**（`ASSIGNABLE_SWITCH_VF_ADJUST`，`ns1 0x2223`，弹出 EVF 亮度条；未接取景器报 `ns1 0x26b5` `"Please connect the viewfinder."`）与 **`VF Mode`**（切换 `Color/B&W`）；反转由取景器本体物理 **`MIRROR` 拨钮**（`Off` / `B/T` / `ROT`）控制 |
| **`Backlight / Contrast / Chroma / Color Temp.` 辟谣** | — | **`VF Adjust` / `VF Setting` 下不存在这 4 个子项**：FX6 上 `Color Temp.` 属于白平衡（`ns2 0x4544`），`Backlight` 属于 AE 模式或 LCD/VF 背光开关；`FX6 appFw.so` 另保留休眠 Alpha `BKID_APP_setting_evf_adjustment`（`-2..+2`） |

---

## 3. 子系统 3：`[AF On]` / `[Eye AF]` / `[Tracking On]` 与仅限静态 `[Recall Custom hold 1–3]` 辟谣 vs FX6 `Push AF/AGC/Iris`

### 3.1 `FX3 Ver. 7.02` 保持类自定义键与 `[Recall Custom hold 1–3]` 实证（`实测事实`）

1. **保持类对焦自定义键矩阵（`ilc/2210` + UXC + `FX3 appFw.so`）**：

| 自定义键动作（UXC `resid16`） | 生效管线 | 实机行为与限制（`ilc/2210`） | ELF 符号实证（`实测事实`） |
| :--- | :---: | :--- | :--- |
| **`[AF On]`**（`_f 0x6df3`） | **Still / Movie / S&Q** | 按住触发自动对焦；Movie `MF` 下按住可临时执行 AF | `EVENT_FUNC_CUSTOM_AF_ON_{ON,OFF}` |
| **`[Eye AF]`**（`_f 0x794d`） | **Still / Movie** | 全画幅专职追踪人脸/人眼（未检测到人脸/眼时不自动退回普通区域对焦） | `EVENT_FUNC_CUSTOM_EYE_AF_{ON,OFF}` |
| **`[Tracking On]`**（`_f 0x7a60`）<br>`[Tracking on Toggle]`（`_f 0x6edc`）<br>`[Tracking On + AF On]`（`_f 0x70a8`） | **仅限 Still** | 需配合 `Focus Mode = AF-C`；在电影/S&Q 管线下不可用 | `EVENT_FUNC_CUSTOM_TRACKING_ON_{ON,OFF}` |
| **`[Recall Custom hold 1..3]`**<br>(`_f 0x60b4` / `0x7581` / `0x725b`) | **仅限 Still `P/A/S/M`** | 按住自定义键期间临时覆盖当前参数，松手即刻恢复原值；**Movie / S&Q / iAuto 下完全不可用**（详见下文） | `EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET{1,2,3}_{ON,OFF}`、`MODEL_REPROCESS_FUNC_CUSTOM_RECALL_SHOOT_SET{1..3}_ON` |

2. **对 `[Recall Custom hold 1–3]` 的两项核心辟谣（`实测事实`）**：

> [!IMPORTANT]
> **辟谣 ①：Movie / S&Q 下 `[Recall Custom hold 1–3]` 彻底不可用（等效 `EOPNOTSUPP`）**
> - 官方 `ilc/2210` *Registering shooting settings to a custom key (Reg. Custom Shoot Set)* 明文限定：**`"[Recall Custom hold 1] through [Recall Custom hold 3] are available only when the shooting mode is set to P/A/S/M."`**（且明确归类 `For still image shooting`）。
> - `FX3 appFw.so` 中回调符号名为 `EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET{1,2,3}_{ON,OFF}`，配合 `BKID_APP_shoot_set_registration_*` 仅向静态 `P/A/S/M` 管线注入，电影/S&Q 模式下不生效（参见 [`G122` 守卫](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h405-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)）。
>
> **辟谣 ②：精确 `11` 个可勾选参数组——不包含独立 `White Balance`！**
> - 通过扫描 `FX3 appFw.so` 中全部 `is_checked_recall_custom_hold{0..10}`（共 `11` 个索引）与 `BKID_APP_shoot_set_registration_*_available{0..3}`，**`Reg. Custom Shoot Set` 实际支持勾选的精确 11 项参数为**：
>   1. `shooting_mode`（P/A/S/M）
>   2. `aperture`（光圈）
>   3. `shutter_speed`（快门速度）
>   4. `exposure_comp`（曝光补偿）
>   5. `iso_sensitivity`（ISO 感光度，联动 `iso_auto_rate_{min,max}`）
>   6. `metering_mode`（测光模式，含 `_spot`）
>   7. `drive_mode`（过片模式：**`ilc/2210` 明确排除 Self-timer**，支持 Cont./Brackets；触发 `ISO` 或 `DRO Bracket` 时临时关闭 `[HLG Still Image]`）
>   8. `focus_mode`（对焦模式）
>   9. `focus_area`（对焦区域）
>   10. `af_on`（`RECALL_SHOOT_SET_AF_ON_{WORK,DOES_NOT_WORK}`）
>   11. `still_af_track_sens`（静态 AF 追踪灵敏度 `1_LOCKED_ON..5_RESPONSIVE`）
> - **`shoot_set_registration_white_balance` 在 `FX3 appFw.so` 命中为 `0`**（仅 `drive_mode_bracket_white_balance` 随 `Drive Mode` 的 `WB bracket` 存在），故将 `White Balance` 列为独立 `Recall Custom hold` 勾选参数属于常见误传。
> - **Reset 与持久化边界**：`ilc/2210` *List of default setting values* 实证 `Reg. Custom Shoot Set` 为 **`Not available`（抗 `[Camera Settings Reset]`）**，仅 `[Initialize]` 清除；并通过 `Save/Load Settings` 序列化到储存卡 **`SONY/SETTING/<Model>/CAMSET/*.DAT`**（区别于机身调出模式的 `Camera Set. Memory` `CAMPR*.DAT`）。

### 3.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Push AF / Push AGC / Push Auto Iris` 对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **一键暂态参数覆写** | `[Recall Custom hold 1–3]`（仅 Still `P/A/S/M`） | **无 `Recall Custom hold 1–3`**；改用 `Project > Assignable Button` 的独立单维 Push 键 |
| **对焦 Push 控制** | `[AF On]` / `[Tracking On + AF On]`（无 Push MF 切换键，改用 `AF/MF Ctrl Hold`） | **`Push AF`**（`ns1 0x3204`，`Push AF Mode`: `AF` / `Single-shot AF(AF-S)`）、**`Push AF/Push MF`**（`ns2 0x431a`，MF 下按住自动对焦，AF 下按住切 MF）与 **`One Push AF`**（`ns2 0x51b6`）；当镜头拨至手动对焦或 `De-Squeeze != Off(1.0x)` 时禁用 |
| **增益 / 光圈 Push 控制** | 无独立 `Push AGC` / `Push Auto Iris` | **`Push AGC`**（`ns1 0x32c1`：**`Cine EI` / `Cine EI Quick` 及 `Bokeh Control = On` 时禁止执行**）与 **`Push Auto Iris`**（`ns1 0x3366` / `One Push Auto Iris` `ns2 0x51b5`：**镜头切至 `MANUAL` 或 `Bokeh Control = On` 时禁止执行**） |
| **`High/Low Key` 辟谣** | 不存在 | `FX6 ns2 0x4b25` 存在休眠字面量 **`High/Low Key`**（承自 FS7/VENICE/BURANO 工程体系），`ILME-FX6 Ver. 6.01` 实机未开放该菜单项 |

---

## 4. 子系统 4：`Setup -> [External Output]` HDMI 深度拆解、`Slot-1` `EROFS=30` 护栏 vs FX6 `SDI/HDMI` 矩阵

### 4.1 `ILME-FX3 Ver. 7.02` `[External Output]` 全量菜单、门控与休眠项辟谣（`实测事实`）

1. **全量暴露项与 Reset/Initialize 边界（`ilc/2210` + `FX3 appFw.so`）**：`Setup -> [External Output]` 全项 **`[Camera Settings Reset]` 均为 `Not available`（抗 Reset）**，仅 `[Initialize]` 恢复出厂默认值。

| 菜单项（`Setup -> [External Output]`） | `FX3 Ver. 7.02` 真值选项与默认（`ilc/2210`） | UXC / ELF 实证与硬前置条件（`实测事实`） |
| :--- | :--- | :--- |
| **`[HDMI Resolution]`**（静态/回放） | **`Auto`（默认）** / `2160p` / `1080p` / `1080i` | `base 0xe1d5`、`_f 0x7817`/`0x79ba`；`BKID_APP_setting_hdmi_resolution`、`VAL_..._HDMI_RESOLUTION_{AUTO_SET,2160P,1080P,1080I}` |
| **`[HDMI Output Settings]` → `Rec. Media dur HDMI Output`** | **`On`（默认）** / `Off(HDMI Only)`<br>*(设为 `Off(HDMI Only)` 时**机内停止录卡且录制计时不走**)* | `_f 0x6144` / `0x6573`；`BKID_APP_setting_rec_media_during_hdmi_output`。**`S&Q` 模式下强制锁死 `On`**；设为 `Off(HDMI Only)` 或 `RAW Output = On` 时临时强制 `[HDMI Info. Display] = Off` |
| **`[HDMI Output Settings]` → `Output Resolution`** | **`Auto`（默认）** / `2160p` / `1080p` / `1080i` | `_f 0x79ac`；`BKID_APP_setting_output_resolution`。仅 `Rec. Media = On` & `RAW Output = Off` 可用；**`[Log Shooting] != Off` 或 `[Picture Profile] = PPLUT1–4` 时降级输出 `1080`**（除非改 `Off(HDMI Only)` 或开 `RAW`） |
| **`[HDMI Output Settings]` → `4K Output Set.(HDMI Only)`** | **`59.94p 10bit` / `50p 10bit`（默认）**、`29.97p 10bit`、`25p 10bit`、`23.98p 10bit`、`24.00p 10bit` | `_f 0x74d7`；`BKID_APP_setting_hdmi_4k_output_setting`。**`24.00p` 切换与非 `24.00p` 强制重启且导致另一帧率素材不可回放**（`_g 0x61d3 / 0x6413 / 0x6423`）；另受 `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`（原厂拼写 `outpute`）帧率/裁切门控 |
| **`[HDMI Output Settings]` → `RAW Output` & `RAW Output Setting`** | `RAW Output`：**`Off`（默认）** / `On`；帧率默认 `59.94p` / `50p`（可至 `24.00p`） | `S&Q` 模式下锁死 `Off`；需外部支持 RAW 录机且要求 `HDMI Info. Display` 临时关 |
| **`[HDMI Output Settings]` → `Time Code Output`** | **`Off`（默认）** / `On` | `_f 0x72af`；`BKID_APP_setting_hdmi_tc_output`。数字时码/User Bit 随 HDMI 数据流嵌入（非画面叠加）；**`S&Q` 模式下禁用**；开启后部分普通电视可能无法出图 |
| **`[HDMI Output Settings]` → `REC Control`** | **`Off`（默认）** / `On` | `_f 0x76e1`；`BKID_APP_setting_rec_control`、`_enabled_rec_control_{ENABLE,DISABLE}`、`PRM_HAITA_setting_rec_control_hdmi_connect_state_media_mount_state_slot1_2_setting_recording_to_media_usb_streaming_mode`。**硬前置条件：① 必须 `[Time Code Output] = On`；② 需兼容外部录机（Atomos 等）**。启用后屏显 `(STBY)`/`(REC)`，且配合 `[REC w/ Shutter] = On` 可用快门键触发外部录制 |
| **`[HDMI Output Settings]` → `4ch Audio Output`** | **`CH1/CH2`（默认）** / `CH3/CH4` | `_f 0x6aa0`；`BKID_APP_setting_mov_hdmi_audio_output`、`MOV_HDMI_AUDIO_OUTPUT_{ON,OFF}`（4ch 不可同时 4 路分轨经 HDMI 输出，必须二选一双声道混出） |
| **`[HDMI Info. Display]`** | **`On`（默认，插线后机身 LCD 黑屏）** / `Off` | `_f 0x6e7c`；`BKID_APP_setting_hdmi_info_display`、`PRM_HAITA_hdmi_connect_state_setting_hdmi_info_display` |
| **`[CTRL FOR HDMI]`** | **`On`（默认）** / `Off` | `base 0xe41f`；**ELF 拼写错字 `BKID_APP_setting_ctrl_for_hmdi`** + `EVENT_INPUT_KEY_CEC_*`（电视遥控器 CEC 控制相机回放） |
| **休眠辟谣：`4K/2K Output` & `24p/60p Output`** | **`ILME-FX3 Ver. 7.02` 均不存在** | `ilc/2210` 命中 `0`、`FX3 appFw.so` 命中 `0`；仅 `_f 0x632b`/`0x781c` 残存 `24p/60p Output` 休眠 UXC 词条 |

### 4.2 `Slot-1` Tier-0 恢复保险库 `EROFS (errno 30)` 危险与 `FX6 SDI/HDMI` 矩阵（`实测事实` + `推断`）

> [!CAUTION]
> **`[Rec. Media dur HDMI Output] = On` 引发 `Slot-1` `EROFS (errno 30)` 的硬护栏（`推断`，基于实测 ELF 门控表）**：
> 1. **实测事实**：`Rec. Media dur HDMI Output` 出厂默认 **`On`**，且在 `S&Q` 模式下**强行锁定为 `On`**；`FX3 appFw.so` 显式通过 **`PRM_HAITA_media_movie_recordable_state_slot2_media_movie_recordable_state_slot1_setting_rec_media_during_hdmi_output`** 联动 `Slot 1`/`Slot 2` 可录状态，并与 `REC Control`（`PRM_HAITA_setting_rec_control_..._media_mount_state_slot1_2_...`）协同。
> 2. **Tier-0 风险推断**：若 `Slot 1` 在台架上挂载为**只读 Tier-0 恢复保险库**，当操作者在未插 `Slot 2` 或默认 `Recording Media = Slot 1` 时开启 HDMI 录制触发（`[REC Control] = On` 且默认 `Rec. Media dur HDMI Output = On`），机身将同时尝试向 `Slot 1` 写入 `M4ROOT/CLIP/*.MP4` 与 `AVF_INFO` 数据库，**必须**在 VFS/块设备层强制截断并返回 **`EROFS (errno 30)`** fail-closed，严禁将纯外部监录请求透传成对 `Slot 1` 保险库的脏写。安全外录路径必须显式切为 **`Off(HDMI Only)`**（`S&Q` 除外）或定向至可写 `Slot 2`。

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC`） |
| :--- | :--- | :--- |
| **端口架构** | 单 Type-A HDMI 2.0（无 SDI） | **`12G/6G/3G-SDI` + `HDMI` 独立双物理口可同步输出**（`Monitoring > Output On/Off > SDI / HDMI`，`ns1 0x2f38` / `0x2f93`） |
| **HDMI 时码输出** | `HDMI Output Settings > Time Code Output`（默认 `Off`；`S&Q` 禁用） | **`TC/Media > HDMI TC Out > Setting: On/Off`**（`ns2 0x4245`） |
| **外部触发录制** | `HDMI Output Settings > REC Control`（必须 `Time Code Output = On`；配合 `Rec. Media = On` 或 `Off(HDMI Only)`） | **`Project > SDI/HDMI Rec Control`**（`ns2 0x428d`）：`Off` / **`SDI/HDMI Remote I/F`**（无卡时触发外录，非帧精确） / **`Parallel Rec`**（有卡时与机内帧精确同步触发）；**通过 HDMI 触发时同样硬性要求 `HDMI TC Out = On`** |
| **RAW 与双路分辨率矩阵** | 单口输出：SDI 不可用；`Log`/`PPLUT` 开机内录时 HDMI 降 `1080`，仅 `HDMI Only` 或 `RAW Output` 输出 4K/RAW | **① `RAW` / `RAW & XAVC-I`**：`SDI` 出 `4096×2160` 或 `3840×2160 (RAW)`，**`HDMI` 仍可同步出 `4K/UHD/FHD`**；<br>**② `RAW(HDMI)` / `RAW(HDMI) & XAVC-I`**：`HDMI` 出 **`4240×2392 (HDMI RAW)`**，**`SDI` 强制降至 `1920×1080P/i`**；<br>**③ `S&Q > 60fps`**：若 `SDI = On` 或 `Codec = RAW / RAW & XAVC-I`，**`HDMI` 强制降至 `1920×1080P` 或以下**（4K HDMI 选项置灰） |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `auto_pixel_mapping` / `pixel_mappinng` / `excuted`、`lcd_brightness` / `display_quality` / `extern_menu_flip` / 休眠 `evf_adjustment` & `finder_*`、`RECALL_SHOOT_SET{1..3}` & 11 项 `shoot_set_registration_*`（0 条独立 WB）、`hdmi_*` / `ctrl_for_hmdi` / `rec_control`（0 条 `4k_2k`/`24p_60p`） |
| [`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin) (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（零专有原始字节泄漏） |
| [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `APR`（`procam_msg_*_apr_controller`、`PIXEL_MAPPING_RESULT_*`）、休眠 `auto_black_balance`、`ASSIGNABLE_SWITCH_{VF_ADJUST,PUSH_AF_MODE,PUSH_AGC,PUSH_AUTO_IRIS}`、休眠 `evf_adjustment` |
| [`FX3 string_english_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc) / `.uxc` / `_g.uxc` | `373,820` / `165,740` / `69,600` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `_f`（`hdr_flag=15`, `7,475` 条） / `base`（`2,692` 条） / `_g`（`1,402` 条）全量包 |
| [`FX3 string_simplifiedchinese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc) / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / `base` / `_g` 精确映射 |
| [`FX3 string_traditionalchinese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc) / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / `base` / `_g` 精确映射 |
| [`FX3 string_japanese_f.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc) / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `_f` / `base` / `_g` 精确映射 |
| [`FX6 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc) / [`_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc) | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `FX6` `ns1`（`5,044` 条）/ `ns2`（`5,914` 条）：`APR`、`VF Adjust` / `VF Setting`、`Push AF/AGC/Auto Iris`、`HDMI TC Out`、`SDI/HDMI Rec Control`、休眠 `Auto Black Balance` & `High/Low Key` |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，`_f` / `base` / `_g` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x61f7` / `0x7734` / `0x64e7` | `Pixel Mapping` / `Auto Pixel Mapping` / `Not Target` | `像素映射` / `自动像素映射` / `非目标` | `像素映射` / `自動像素映射` / `不是目標` | `ピクセルマッピング` / `ｵｰﾄﾋﾟｸｾﾙﾏｯﾋﾟﾝｸﾞ` / `対象にしない` | **活跃**（Setup 抗 Reset；Silent 子项可 Reset） |
| `_f` `0x693f` / `0x76b5` | `Pixel Map. Notification` / `APR` | `像素映射通知` / `APR` | `像素映射通知` / `APR` | `ﾋﾟｸｾﾙﾏｯﾋﾟﾝｸﾞの通知` / `APR` | **FX3 上休眠/非暴露**（`_g 0x63ab` 提示属共享库） |
| `_g` `0x63f1` / `0x60e7` / `0x6265` | `Attach the lens cap...` / `...light shielding was insufficient.` / `Pixel mapping completed.` | `运行像素映射之前安装镜头盖...` / `由于遮光不足，像素映射失败...` / `像素映射完成。` | `運行像素映射前，先接上鏡頭蓋...` / `像素映射失敗，因為遮光不充分...` / `像素映射完成。` | `遮光のため、レンズキャップを装着...` / `遮光が不十分のため...失敗...` / `ピクセルマッピングが完了しました` | **活跃**（手动像素映射提示链） |
| `base` `0xe44b` / `0xe1da`（`_f 0x7a61`） | `Monitor Brightness` / `Sunny Weather` | `显示屏亮度` / `晴朗天气` | `螢幕亮度` / `晴朗天氣` | `モニター明るさ` / `屋外晴天` | **活跃**（位于 `Setup -> [Monitor]`；抗 Reset） |
| `_f` `0x6c5e` / `0x7ac6` / `0x6664` | `Display Quality` / `...standard. Longest battery life.` / `...high.` | `显示质量` / `...标准。最长电池寿命。` / `...高。` | `顯示畫質` / `...標準。延長電池續航力。` / `...高。` | `表示画質` / `...標準...電池を最も長く...` / `...高画質...` | **活跃**（`Standard` 默认；高温锁 `Standard`；抗 Reset） |
| `_f` `0x6a24` / `0x7780` / `0x6fcc` / `0x7363` / `0x72d6` | `Monitor Flip Direction` / `Horizontal Flip` / `180 Degree Flip` / `No Flip` / `Switch Monitor Flip Disp` | `显示屏翻转方向` / `水平翻转` / `180度翻转` / `无翻转` / `切换显示屏翻转显示` | `螢幕翻轉方向` / `水平翻轉` / `180度翻轉` / `無翻轉` / `切換螢幕翻轉顯示` | `モニター反転表示` / `左右反転` / `上下左右反転` / `反転しない` / `ﾓﾆﾀｰ反転表示切換` | **活跃**（`Auto` 默认；抗 Reset） |
| `_f` `0x6daf` / `0x6935`（`base 0xe662`）/ `base 0xe38d` / `_f 0x718c` | `Finder/Monitor Sel.` / `Viewfinder Bright.` / `Look at the viewfinder...color temperature...` / `Sets the finder frame rate...` | `取景器/显示屏选择` / `取景器亮度` / `设置取景器色温时观看取景器。` / `将取景器帧速率设置为...` | `觀景窗/螢幕選擇` / `觀景窗亮度` / `查看觀景窗，同時設定觀景窗色溫。` / `將觀景窗幀率設定為...` | `ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ切換` / `ファインダー明るさ` / `ファインダーの色温度設定中です...` / `ファインダーのフレームレートを...` | **FX3 7.02 全部休眠！**（无 EVF 硬件，`ilc/2210` 零暴露） |
| `_f` `0x6df3` / `0x794d` / `0x7a60` / `0x6edc` / `0x70a8` | `AF On` / `Eye AF` / `Tracking On` / `Tracking on Toggle` / `Tracking On + AF On` | `AF开启` / `眼部AF` / `跟踪开启` / `跟踪切换` / `跟踪开启+AF开启` | `對焦開啟` / `眼部對焦` / `追蹤開啟` / `追蹤切換` / `追蹤開啟+對焦開啟` | `AFオン` / `瞳AF` / `押す間トラッキング` / `再押しトラッキング` / `押す間ﾄﾗｯｷﾝｸﾞ+AFｵﾝ` | **活跃**（前 2 项跨管线；`Tracking*` 仅 Still `AF-C`） |
| `_f` `0x6282` / `0x60b4` / `0x7581` / `0x725b` | `Reg. Custom Shoot Set` / `Recall Custom hold 1` / `...2` / `...3` | `注册自定义拍摄设置` / `调出自定保持1` / `...2` / `...3` | `登錄自訂拍攝設定` / `回復自訂固定1` / `...2` / `...3` | `ｶｽﾀﾑ撮影設定登録` / `押す間ｶｽﾀﾑ設定呼出1` / `...2` / `...3` | **活跃但仅限 Still `P/A/S/M`**（11 项含不含独立 WB；抗 Reset） |
| `base` `0xe1d5` / `0xe41f` / `_f 0x6e7c` | `HDMI Resolution` / `CTRL FOR HDMI` / `HDMI Info. Display` | `HDMI分辨率` / `HDMI控制` / `HDMI信息显示` | `HDMI解析度` / `HDMI控制` / `HDMI資訊顯示` | `HDMI解像度` / `HDMI機器制御` / `HDMI情報表示` | **活跃**（均抗 Reset；ELF `ctrl_for_hmdi` 错字） |
| `_f` `0x6144` / `0x6573` / `0x79ac` / `0x74d7` / `0x72af` / `0x76e1` / `0x6aa0` | `Rec. Media dur HDMI Output` / `Off(HDMI Only)` / `Output Resolution` / `4K Output Set.(HDMI Only)` / `Time Code Output` / `REC Control` / `4ch Audio Output` | `HDMI输出时的摄像媒体` / `关(仅HDMI)` / `输出分辨率` / `4K输出设置(仅HDMI)` / `Time Code输出` / `REC控制` / `4ch音频输出` | `HDMI輸出時錄製到記憶卡` / `關(僅限HDMI)` / `輸出解析度` / `4K輸出設定(僅限HDMI)` / `Time Code輸出` / `REC控制` / `4ch音訊輸出` | `HDMI出力時のﾒﾃﾞｨｱ記録` / `切(HDMIのみ)` / `出力解像度` / `4K出力設定(HDMIのみ)` / `Time Code出力` / `RECコントロール` / `4ch音声の出力` | **活跃**（`Rec. Media = On` 须对 Tier-0 `Slot 1` 实施 **`EROFS=30`** 拦截） |
| `_f` `0x632b` / `0x781c` | `24p/60p Output` | `24p/60p输出切换` | `24p/60p輸出切換` | `24p/60p出力切換` | **FX3 7.02 休眠！**（`ilc/2210` & `FX3 appFw.so` 均 `0` 命中） |
