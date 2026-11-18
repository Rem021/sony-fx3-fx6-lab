# 全球 Sony 实机情报 Wave 79（`79th Wave`：`79/79 Waves` 收官 · `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `Shooting -> [Zoom]` 8 档变速架构、`[Dial Customize]` 5 项矩阵与 `My Dial 1..3` / `[Function Ring(Lens)]`、`[Operation Customize]` 独立位掩码与零 EVF `[Finder/Monitor]` 边界，以及 `[External Output]` HDMI 4K/10-bit/RAW 与 12G-SDI 双管线深度审计）

- **日期**：`2026-11-18`
- **任务 / 波次**：`H456` · **Global Sony Real-Hardware Empirical Intelligence Wave 79**（`79th Wave` / `79/79 Waves` 全系列收官审计）
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`，`Linux 4.9.337-scel+`，`PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）
- **承接与关键勘误声明**：
  - 本 Wave 79 报告承接 [Wave 76（Custom Key / Different Set 8 / USB-LAN）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/reports/2026-11-18-global-sony-wave76-customkey-diffset8-gammadisp-mlut-usblan-ipsec-cleaning-intel/README.md)、[Wave 77（Movie Settings / AWB / Touch / Screen Reader / Version）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/reports/2026-11-18-global-sony-wave77-movieset-vpg-awbprio-atw-touchpad-screenreader-version-intel/README.md) 与 [Wave 78（Flexible Exp. / Shutter Angle / Active IBIS / Catalyst / Photo Capture / SRT）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/reports/2026-11-18-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/README.md)。
  - 基于官方 Sony `ILME-FX3` Help Guide（`ilc/2210` Ver. 7.02）、官方 `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB` Ver. 6.0）以及严格 `os.O_RDONLY` 只读本地 donor 二进制实证，本次审计**显式揭穿与修正了 6 项常见跨机型迷思与仓内细节偏差**：
    1. **`[Custom Key Z. Speed]` 无 `Variable` 模式 vs `[Remote Zoom Speed]` 专属 `Speed Type`（`ilc/2210` & `FX3 appFw.so`）**：实机中 `Shooting -> [Zoom] -> [Custom Key Z. Speed]`（`_f 0x78e8`）**仅暴露 `Fixed Speed`（`Standby` `1..8` 默认 `3` / `REC` `1..8` 默认 `3`），根本不存在 `Variable Speed Type`**；而 **`[Remote Zoom Speed]`**（`_f 0x7128`）才暴露 `Speed Type`（`Variable` 默认 vs `Fix`）+ `Fixed Speed`（`1..8` 默认 `3`）。有趣的是 Sony 在 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中将上述类型键命名为 `BKID_APP_setting_fixed_zoom_speed_type`（实控 Remote 而非 Custom Key）。此外，`ILME-FX6` `Technical > Zoom` 并**无** `Speed 1..99` 菜单——`0..99` 是 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) `BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY`（`0` 广角–`99` 长焦）的 HUD 焦距位置读数，手柄变焦挡位菜单位于 **`Technical > Handle Zoom`**（`Off` / `Low 1..8` 默认 `3` / `High 1..8` 默认 `8` / `Variable`）。
    2. **`[Dial Setup]` 与 `[Dial/Wheel Lock]` 在 FX3 Ver. 2.00..7.02 已退役休眠（`FX3 appFw.so` + `G131`）**：`Setup -> [Dial Customize]`（`_g 0x62ed`）实机**仅暴露 5 项**（`[Custom Key/Dial Set.]`、`[My Dial Settings]`、`[Av/Tv Rotate]`、`[Function Ring(Lens)]`、`[Lock Operation Parts]`）；`_f 0x79d1` `[Dial Setup]`（`BKID_APP_setting_dial_setup`，`Av/Tv` vs `Tv/Av`）、`base 0xe352` `[Dial / Wheel Lock]` 以及 4 拨轮 `Rear Dial L/R`（`_f 0x6a5c`/`0x680d`）均为 Ver. 1.xx 或其他 Alpha 机型的休眠遗留符号。
    3. **`[DISP (Screen Disp) Set]` 归属、零 `Graphic Display` 与零 `[Finder]` 分支（`ilc/2210` + `G129`）**：FX3 `[DISP (Screen Disp) Set]`（`_g 0x61da`）位于 `[Operation Customize]`（`_g 0x61c4`）下，实机拍摄仅暴露 **4 页**（`Display All Info.` / `No Disp. Info.` / `Histogram` / `Level`），回放仅暴露 3 页；**`Graphic Display`（`base 0xe07a`）、`For viewfinder`（`base 0xe2e5`/`_f 0x62d3`）、`Monitor Off`（`VAL_disp_mode_shoot_monitor_DISP_MODE_SHOOT_MONITOR_MONITOR_OFF`）及整个 `[Finder/Monitor]`（`_g 0x63fc` / `BKID_APP_setting_finder_monitor` / `BKID_APP_disp_mode_shoot_finder`）在无 EVF 的 FX3 上 100% 休眠未暴露**。
    4. **`[HDMI Resolution]` 仅 4 档（无 `720p`）与 `[4K Output Set.(HDMI Only)]` 无 `4:2:0`（`ilc/2210` + `FX3 appFw.so`）**：`Setup -> [External Output] -> [HDMI Resolution]`（Still & Playback）**仅暴露 `Auto`（默认）/ `2160p` / `1080p` / `1080i` 4 项**（ELF 中 `HDMI_RESOLUTION_720P_480P` 休眠，`720p` 仅存于 Network Streaming）；`[4K Output Set.(HDMI Only)]`（`_f 0x74d7`）**仅暴露 6 档 `10bit`（`4:2:2 10bit`）**，不存在 `4:2:0` vs `4:2:2` 开关（`_f 0x748a` `24.00p 8bit` 在 UXC 休眠且 ELF 枚举零出现）。
    5. **`24p/60p Output` 在 `ILME-FX3 Ver. 7.02` 为 100% 休眠遗留串（`FX3 appFw.so` = `0` hits）**：尽管 `_f.uxc` 保留 `0x632b`/`0x781c` `24p/60p Output` 词条，[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 与 `ilc/2210` 均**零命中**，FX3 的 `24.00p` 真 24p 切换已并入 `[Movie Settings]`/`[4K Output Set.(HDMI Only)]`/`[RAW Output Setting]` 的重启门禁（`PRM_HAITA_setting_hdmi_4k_output_setting_*`）。
    6. **`[HDMI Info. Display] = On` 熄屏条件与 Sony ELF 双拼写错误（`ilc/2210` + `G113` + `G154`）**：`[HDMI Info. Display] = On`（`_f 0x6e7c`，默认）仅在 **`[Rec. Media dur HDMI Output] = On` 且 `[RAW Output] = Off`** 时将 FX3 机内 LCD 强制黑屏（外部显示器接管 OSD）；一旦设为 `Off(HDMI Only)` 或 `RAW Output = On`，机内自动临时降为 `HDMI Info. Display = Off`（Clean HDMI + 机内 LCD 恢复预览）。Sony [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 内部存在 3 个著名拼写错误符号：`BKID_APP_setting_ctrl_for_hmdi`（`hmdi`）、`PRM_HAITA_hdmi_4k_outpute_apsc_restriction`（`outpute`）以及 `BKID_APP_setting_4ch_output_ch`（替代 `4ch_audio_output`）。
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Zoom Range / Zoom Lever Speed / Custom Key Z. Speed / Remote Zoom Speed / Zoom Ring Rotate / Custom Key/Dial Set. / My Dial Settings / Av/Tv Rotate / Function Ring(Lens) / Lock Operation Parts / Different Set for Still/Mv / Fn Menu Settings / DISP (Screen Disp) Set / Gamma Display Assist / Select LUT / HDMI Resolution / HDMI Output Settings / HDMI Info. Display / CTRL FOR HDMI / List of default setting values (`TP1000888852`)*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Technical > Zoom & Handle Zoom / Project > Assignable Dial & Multi Function Dial / Monitoring > Display On/Off & Output Format / Project > SDI/HDMI Rec Control*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)（`79,015,712` B）+ FX3 4 语全量 `base`/`_f`/`_g` `.uxc`（12 个文件）与 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)（`50,520,424` B）+ FX6 4 语全量 `ns1`/`_2` `.uxc`（8 个文件），合计 **22 个 donor 工件**。
  - 仓内安全守卫交叉对照：[`G95/G96`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)、[`G99/G100`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py)、[`G110`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)、[`G113`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)、[`G119`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)、[`G129`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py)、[`G131/G132`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py)、[`G145`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py)、[`G149`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py) 与 [`G153/G154`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.py)。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（UXC `resid16`、ELF 符号、SHA-256 账本、Reset/Initialize 持久性与官方 `ilc/2210`/`5-024-458-18` 条目）与 **`推断`**（跨机型架构映射判断与守卫微调建议）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`Shooting -> [Zoom]` 完整变焦控制体系 vs `ILME-FX6 Ver. 6.01`）**：
   - **实测事实（FX3 菜单与速度体系 split）**：`ILME-FX3 Ver. 7.02` 暴露 `[Zoom Range]`（`_f 0x7164`：`Optical zoom only` 默认 / `ClearImage Zoom` [`4K 1.5x` / `HD 2.0x` / `Still L 2.0x`..`S 4.0x`] / `Digital Zoom` [`Movie 4.0x` / `Still S 8.0x`]；`Smart Zoom` 仅限 Still `M/S`、Movie 禁用）、**`[Zoom Lever Speed]`**（`_f 0x6304`：机身二段式 W/T 变焦杆，`1st Zoom Spd.` 默认 `3`、`2nd Zoom Spd.` 默认 `8 (Fast)`，Standby/REC 分设，对镜头变焦环或 PZ 镜头自带推杆无效）、**`[Custom Key Z. Speed]`**（`_f 0x78e8`：**仅 `Fixed Speed` `1..8` 默认 `3`，Standby/REC 分设，无 `Variable` 模式**）与 **`[Remote Zoom Speed]`**（`_f 0x7128`：**暴露 `Speed Type` [`Variable` 默认 / `Fix`] + `Fixed Speed` `1..8` 默认 `3`**），外加 `Setup -> [Operation Customize] -> [Zoom Ring Rotate]`（`_f 0x6be7`：`Left(W)/Right(T)` 默认 / `Right(W)/Left(T)`）。
   - **实测事实（Reset 分裂、E 卡口 PZ 协同与 CIZ 退化约束）**：`[Zoom Range]` 与 `[Zoom Ring Rotate]` 抗 `[Camera Settings Reset]`（`Not available`，仅 `[Initialize]` 归位），而三项速度设置（Lever / Custom Key / Remote）均 **`Can be reset`**。非光学变焦在 Still `RAW`/`RAW & JPEG`/`RAW & HEIF`、Movie `119.88p/100p`、`S&Q >= 100fps` 或 HDMI `RAW` 下预禁用；激活后强行禁用 `[Focus Area]`（退化为中心区域优先对焦）、锁定 `[Metering Mode] = Multi` 并禁用人脸/人眼 AF 优先、Multi 测光人脸优先及 `Tracking`。电动变焦镜头（如 `SELP1635G`/`SELP28135G` 等，手册统称 *power zoom lens*）无缝由光学长焦端衔接至 CIZ/Digital，定焦镜头则直接从 `1.0x` 起步。
   - **实测事实（`ILME-FX6 Ver. 6.01`）**：`Technical > Zoom > Zoom Type` 仅暴露 `Optical Zoom Only` 与 `On(Clear Image Zoom)`（**零 `Digital Zoom`**）；握把变焦杆按压力无级变速，顶部手柄变焦杆由 **`Technical > Handle Zoom`** 控制（`Off` / `Low 1..8` 默认 `3` / `High 1..8` 默认 `8` / `Variable`）；`0..99` 仅是 `Zoom Position` HUD 显示范围。

2. **子系统 2（`Setup -> [Dial Customize]` 5 项深度控制矩阵 vs `ILME-FX6 Ver. 6.01`）**：
   - **实测事实（FX3 Ver. 7.02 精确 5 项与物理 3 拨轮）**：`[Dial Customize]`（`_g 0x62ed`）仅含 5 项且**全部抗 `[Camera Settings Reset]`（`Initialize`-only）**：① `[Custom Key/Dial Set.]`（`_f 0x6290`，Still/Movie/Playback 独立映射 `Front Dial`/`Rear Dial`/`Control Wheel`）；② `[My Dial Settings]`（`_f 0x6538`：`My Dial 1..3` 临时映射库，经 `My Dial 1..3 during Hold` / `Toggle My Dial 1..3` / `My Dial 1→2→3` 召回并临时解锁 `[Lock Operation Parts]`）；③ `[Av/Tv Rotate]`（`_f 0x72e3`：`Normal` 默认 / `Reverse`）；④ `[Function Ring(Lens)]`（`_f 0x715e`：`Power Focus` 默认 vs `APS-C/Super 35 mm / Full Frame` 视角切换，兼容带功能环的 GM/G 镜头）；⑤ `[Lock Operation Parts]`（`_f 0x6904`：`Off` / `Multi-Selector Only` / `Dial + Wheel` / `All`）。
   - **实测事实（休眠剥离与 `ILME-FX6`）**：`[Dial Setup]`（`_f 0x79d1` `Av/Tv` vs `Tv/Av`）、`[Dial / Wheel Lock]`（`base 0xe352`）及 `Rear Dial L/R` 在 FX3 均属休眠符号。`ILME-FX6` 通过 `Project > Assignable Dial`（`Grip/Remote Dial` & `Handle Dial` 默认 `IRIS`，含 `ND Filter` 与 `Multi Function Dial`）及 `Project > Multi Function Dial > Default Function`（默认 `Off`，**不含 `ND Filter`**）配合机身侧物理 `IRIS`/`ND` 拨盘实现全硬件化控制。

3. **子系统 3（`Setup -> [Operation Customize]` & `[Finder/Monitor]` 休眠边界与 LUT 交互）**：
   - **实测事实（`[Different Set for Still/Mv]` 8 项位掩码 vs `Fn` `12+12` 槽位）**：`[Different Set for Still/Mv]`（`_f 0x62ee` / `BKID_APP_setting_different_set_for_s_q_mv`）精确独立控制 **8 项参数**（`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture Profile`, `Focus Mode`），且 **`[Picture Profile]` 勾选框抗 BOTH Reset 和 Initialize**；`[Fn Menu Settings]`（`_g 0x614b`）与之独立维护 **`12` Still + `12` Movie** 槽位（`BKID_APP_fn_menu_item_ids_for_{still,movie}0..11`）。
   - **实测事实（`[DISP (Screen Disp) Set]` 4 页与零 EVF 边界、`Gamma Display Assist` vs `[Select LUT]`）**：`[DISP (Screen Disp) Set]` 仅暴露 Monitor 4 个拍摄页（`Display All Info.` / `No Disp. Info.` / `Histogram` / `Level`），**`Graphic Display` 与整个 `[Finder]`/`[Finder/Monitor]` 休眠**。在 `Cine EI` / `Flexible ISO` 下显示 LUT 由 **`[Select LUT]`**（`_f 0x643e`：`S-Log3` / `s709` 默认 / `709(800%)` / `User1..16`）与 `[Display LUT]`（`_f 0x729a`）接管，**`[Gamma Display Assist]`（`_f 0x707b`）在 Log Shooting 启用时自动失效，主要服务关闭 Log Shooting 时的 `PP(S-Log3/HLG)` 或静态 Log/HLG 图像**（`_f 0x6538` 实证）。对比 `ILME-FX6 Ver. 6.01`：物理 `DISPLAY` 键与 `Monitoring > Display On/Off` 暴露多达 **60 路 ELF `BKID_APP_SETTING_*_DISPLAY`（`24+` 独立 HUD 开关）**，含 `Rec/Play Status`、`Tally`、`Video Signal Monitor`（波形/矢量/直方图）、`RAW Output Control Status`、`SDI/HDMI Rec Control` 等。

4. **子系统 4（`Setup -> [External Output]` HDMI 4K/10-bit/RAW 与 `ILME-FX6` 12G-SDI 矩阵）**：
   - **实测事实（FX3 `[External Output]` 4 大项全抗 Reset、`720p`/`4:2:0`/`24p/60p` 证伪）**：
     - `[HDMI Resolution]`（Still/Playback）：**`Auto` / `2160p` / `1080p` / `1080i`**（**无 `720p`**）；
     - `[HDMI Output Settings]`（8 项）：`[Rec. Media dur HDMI Output]`（`On` 默认 / `Off(HDMI Only)`）、`[Output Resolution]`（`Auto` / `2160p` / `1080p` / `1080i`，`On`+`RAW=Off` 且开启 Log/`PPLUT1..4` 时降档至 `1080`）、`[4K Output Set.(HDMI Only)]`（**6 档 `10bit` `4:2:2`，无 `4:2:0` 选项，无 `24.00p 8bit`**，`24.00p` 强制重启）、`[RAW Output]`（`4264×2408` 16-bit）+ `[RAW Output Setting]`、`[Time Code Output]`、`[REC Control]`（强依赖 `TC Output = On`）、`[4ch Audio Output]`（`CH1/CH2` 默认 vs `CH3/CH4`，经由 `BKID_APP_setting_4ch_output_ch`）；
     - `[HDMI Info. Display]`（`On` 默认且在 `Rec. Media=On & RAW=Off` 时熄灭机内 LCD）与 `[CTRL FOR HDMI]`（`On` 默认，ELF `BKID_APP_setting_ctrl_for_hmdi`）；`24p/60p Output` 在 FX3 为 `0` 命中休眠串。
   - **实测事实（`ILME-FX6 Ver. 6.01` `12G/6G/3G-SDI + HDMI` 双管线）**：`Monitoring > Output Format` 支持 `12G/6G/3G-SDI (Level A/B)` 与 `HDMI` 同步独立矩阵（25 项 `VAL_setting_output_format_sdi_hdmi_*` 组合）：`RAW`/`RAW & XAVC-I` 经 SDI 输出 `4096×2160`/`3840×2160` 16-bit RAW 并允许 HDMI 同步输出最高 4K 监视信号；`RAW(HDMI)` 经 HDMI 输出 `4240×2392` RAW 并强制 SDI 锁为 `1080P/i`（不含 `24Hz`）；`S&Q > 60fps` 在开启 SDI 或 RAW 时强制将 HDMI 限幅至 `<= 1080p`；`Project > SDI/HDMI Rec Control` 区分 `Off` / `SDI/HDMI Remote I/F` / `Parallel Rec`。

---

## 1. 子系统 1：`Shooting -> [Zoom]` 完整控制架构与 AF/帧率互锁 vs `ILME-FX6 Ver. 6.01`

### 1.1 `ILME-FX3 Ver. 7.02` `[Zoom]` 菜单全集、速度分级与 Reset 分裂（`实测事实`）

菜单路径：`MENU -> (Shooting) -> [Zoom]`（`_f 0x7453`）及 `MENU -> (Setup) -> [Operation Customize] -> [Zoom Ring Rotate]`（`_f 0x6be7`）。对照 Sony `ilc/2210` 与 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 实证如下：

| 菜单项（UXC `resid16`） | 实机暴露选项与出厂默认 | ELF 核心符号（`FX3 appFw.so`） | 硬件/操作范围与语义 | `Camera Settings Reset` |
| :--- | :--- | :--- | :--- | :--- |
| **`[Zoom Range]`**<br>（`_f 0x7164`） | • **`Optical zoom only`**（`_f 0x73f2`，**默认**；Still `M/S` 附带 `Smart Zoom` `_f 0x78bf`）<br>• `ClearImage Zoom`（`_f 0x70e1`）<br>• `Digital Zoom`（`base 0xe06b`） | `BKID_APP_MR_setting_zoom_setting`<br>`VAL_setting_zoom_setting_ZOOM_SETTING_{OPTICAL_ZOOM_ONLY,SMART_ZOOM_ONLY,CLEAR_IMAGE_ZOOM_ON,DIGITAL_ZOOM_ON}` | **倍率实证（`ilc/2210`）**：<br>• **Movie/S&Q**：CIZ `4K ≈ 1.5×` / `HD ≈ 2.0×`；Digital `4.0×`<br>• **Still 3:2 FF**：L(`12M`) `CIZ 2.0×` / `Dig 4.0×`；M(`5.1M`) `Smart 1.5×` / `CIZ 3.1×` / `Dig 6.1×`；S(`3.0M`) `Smart 2.0×` / `CIZ 4.0×` / `Dig 8.0×`<br>• **Still APS-C**：M `1.3×/2.6×/5.2×`；S `2.0×/4.0×/8.0×` | **`Not available`**<br>（抗 Camera Reset，仅 `Initialize` 归位） |
| **`[Zoom Lever Speed]`**<br>（`_f 0x6304`） | • **`1st Zoom Spd.`**（`_f 0x6fc0`）：Standby `1..8`（**默认 `3`**）；REC `1..8`（**默认 `3`**）<br>• **`2nd Zoom Spd.`**（`_f 0x78f0`）：Standby `1..8`（**默认 `8 (Fast)`**）；REC `1..8`（**默认 `8 (Fast)`**） | `BKID_APP_setting_1st_zoom_spd_{stby,rec}`<br>`BKID_APP_setting_2nd_zoom_spd_{stby,rec}`<br>`VAL_setting_zoom_speed_*` | 机身快门环周围 **二段式物理 W/T 变焦拨杆** 轻推（第 1 挡）与推到底（第 2 挡）独立控速；**不影响镜头自带变焦环或 Power Zoom 镜头侧面拨杆速度** | **`Can be reset`** |
| **`[Custom Key Z. Speed]`**<br>（`_f 0x78e8`） | • **仅 `Fixed Speed`**：<br>  - Standby：`1 (Slow)..8 (Fast)`（**默认 `3`**）<br>  - REC：`1 (Slow)..8 (Fast)`（**默认 `3`**）<br>（**无 `Variable Speed Type` 选项！**） | `BKID_APP_setting_fixed_zoom_speed_{stby,rec}`<br>`VAL_setting_fixed_zoom_speed_{stby,rec}_1..8` | 专控映射至自定义按键的 `[Zoom]` / `[Zoom Operation (T)]` / `[Zoom Operation (W)]`（单按即以预设固定速度变焦） | **`Can be reset`** |
| **`[Remote Zoom Speed]`**<br>（`_f 0x7128`） | • **`Speed Type`**（`_f 0x6b9e`）：**`Variable`**（`_f 0x7435`，**默认**）/ **`Fix`**（`_f 0x77fd`）<br>• **`Fixed Speed`**：Standby `1..8`（**默认 `3`**）/ REC `1..8`（**默认 `3`**） | `BKID_APP_setting_fixed_zoom_speed_type`（注：ELF 名含 `fixed`，实控 Remote Speed Type）<br>`VAL_setting_fixed_zoom_speed_type_ZOOM_SPEED_TYPE_{VARIABLE,FIXED}`<br>`BKID_APP_setting_remote_fixed_zoom_speed_{stby,rec}` | 控外部 Bluetooth（如 GP-VPT2BT / RMT-P1BT）、IR、USB 多功能接口或 LAN / Smartphone 遥控变焦速度；兼容变档遥控器在 `Variable` 下可压感变速 | **`Can be reset`** |
| **`[Zoom Ring Rotate]`**<br>（`_f 0x6be7`） | • **`Left(W)/Right(T)`**（`_f 0x7a01`，**默认**）<br>• `Right(W)/Left(T)`（`_f 0x7a9e`） | `BKID_APP_extern_menu_ring_zoom_direction_mode` | 反转兼容 Power Zoom 镜头变焦环旋转方向（Located under `[Operation Customize]`） | **`Not available`**<br>（抗 Camera Reset） |

### 1.2 Power Zoom 电动变焦 vs 定焦 CIZ 退化机制与互锁锁死（`实测事实`）

1. **Power Zoom（`SELP1635G` / `SELP28135G` 等电动变焦镜头）vs 无电动变焦镜头行为差异（`ilc/2210`）**：
   - 挂载 Power Zoom 镜头时，拨动机身上的 W/T 变焦杆、镜头自带拨杆或转动电子变焦环，系统首先驱动光学马达变焦至光学长焦端（Tele 尽头），随后**无缝（seamlessly）接续进入 `ClearImage Zoom` 或 `Digital Zoom`**（`Zoom Bar` 上以 `1.0x` 起步并在光学段之后标记 `C`/`D` 段分界）。
   - 挂载**定焦镜头或普通机械变焦镜头**时，光学变焦段（`Optical`）处于锁定状态，变焦条滑块停留在 `×1.0` 左端；一旦启用 `ClearImage Zoom` 或 `Digital Zoom`，拨动机身 W/T 拨杆、Custom Key 或遥控器立即从 `1.0×` 起步进行电子变焦。
   - **重要物理边界**：FX3 原装 `XLR-H1` 顶部手柄**无物理 W/T 变焦拨杆**、无 `Zoom Hold` 开关且无独立手柄 `REC` 锁，区别于 `ILME-FX6` 的 Smart Handle（[`G119`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py#L298-L303)）。

2. **非光学变焦（`Smart` / `ClearImage` / `Digital Zoom`）的前置硬禁用与激活后 AF/测光退化（`ilc/2210` + `G149`）**：
   - **4 大前置不可用锁死（灰色禁用或退回 `Optical zoom only`）**：
     1. Still `[File Format]` 设为 **`[RAW]`**、**`[RAW & JPEG]`** 或 **`[RAW & HEIF]`**；
     2. Movie `[Rec Frame Rate]` 设为 **`[119.88p]` / `[100p]`**（4K 120p 采样无裕度）；
     3. `[S&Q Settings]` 帧率设为 **`100fps / 120fps / 200fps / 240fps`**；
     4. `[External Output] -> [HDMI Output Settings] -> [RAW Output] = [On]`（16-bit 线性 RAW 直出）。
   - **激活非光学变焦后的 5 项联动退化约束（`ilc/2210` *The zoom features available with this product*）**：
     - **`[Focus Area]` 被禁用**：无论原先选定 `Zone`、`Spot: S/M/L`、`Expand Spot` 还是 `Tracking:*`，进入非光学变焦区间后**自动退化为中心区域优先对焦（Center priority AF）**；
     - **`[Metering Mode]` 强制锁定 `[Multi]`**；
     - **`[Face/Eye Prior. in AF]`**、**`[Face Priority in Multi Metering]`** 以及 **`[Tracking]`（包括 `Touch Tracking` 在切至 MF 时退化为 `Touch Focus`）全部禁用**。

### 1.3 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 变焦系统横向对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 ELF`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 ELF/UXC`） |
| :--- | :--- | :--- |
| **菜单路径与类型枚举** | `Shooting -> [Zoom] -> [Zoom Range]`：`Optical zoom only` / `ClearImage Zoom` / `Digital Zoom`（Still 含 `Smart Zoom`） | `Technical > Zoom > Zoom Type`（`fx6_2 0x5240`）：仅 **`Optical Zoom Only`** 与 **`On(Clear Image Zoom)`**（`1.5×` 4K / `2.0×` HD），**零用户可开启 `Digital Zoom`** |
| **机身/握把/手柄变焦硬件** | 机身二段式 W/T 变焦杆（`[Zoom Lever Speed]` `1st` def `3`、`2nd` def `8`）；`XLR-H1` 无变焦杆 | 机身侧 Grip 变焦杆（**按压力无级变速**）+ Smart Handle 顶部手柄变焦杆（独立开关与拨杆） |
| **手柄 / 自定义 / 遥控调速** | `[Custom Key Z. Speed]`（**仅 Fixed `1..8`** def `3`）；`[Remote Zoom Speed]`（`Variable` / `Fix 1..8` def `3`） | **`Technical > Handle Zoom`**（`fx6_2 0x4219/0x569b..0x56d4`）：`Setting`（`Off`/`Low`/`High`/`Variable`）、**`High`（`1..8` 默认 `8`）**、**`Low`（`1..8` 默认 `3`）**；另有 User Menu `Speed Zoom`（`0x421a`）与 BT 遥控 `1..8` |
| **`0..99` 数值真相澄清** | 无 `0..99` 变焦刻度菜单，HUD 仅显示 `1.0×..8.0×` 或焦距 `mm` | **`Technical > Zoom` 并无 `Speed 1..99` 设置**；`0..99` 实为 `Zoom Position Display`（`BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY`：`Bar` / `Number` `0..99` / `Focal Length`）的广角-长焦位置读数 |
| **变焦环方向设置** | `Setup -> [Operation Customize] -> [Zoom Ring Rotate]` | `Technical > Lens > Zoom Ring Direction`（`fx6_2 0x4f64`） |

---

## 2. 子系统 2：`Setup -> [Dial Customize]` 5 项深度控制矩阵与 `My Dial 1..3` / `[Function Ring(Lens)]` vs `ILME-FX6`

### 2.1 `ILME-FX3 Ver. 7.02` `[Dial Customize]` 精确 5 项与物理 3 拨轮拓扑（`实测事实`）

菜单路径：`MENU -> (Setup) -> [Dial Customize]`（`_g 0x62ed`）。结合 `ilc/2210`、`TP1000888852` 与 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) / [`G131`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 实证，FX3 Ver. 2.00..7.02 **精确仅暴露以下 5 项**（且**全部在 `[Camera Settings Reset]` 下保持不变，`Initialize`-only**）：

1. **`[Custom Key/Dial Set.]`**（`_f 0x6290` / `0x73a0`，替代 Ver. 1.xx `[Dial Setup]` / `[Dial/Wheel Setup]` `_f 0x6a89`）：
   - 分 **Still Image**（默认 `Front Dial`/`Rear Dial`/`Control Wheel` 均为 `Follow Custom`）、**Movie**（Movie 出厂默认：**`Front dial = Aperture`**、`Rear dial = ISO/EI`、**`Control Wheel = Shutter Speed`**，另有 `ISO` / `Exposure Comp.` / `White Balance` / `Picture Profile` / `Metering Mode` / `Not set` 等可指派项）与 **Playback**（`Image Jump Setting` `Front/Rear dial` 默认 `One by one`）三套独立键值表；
   - **物理 3 拨轮硬边界**：FX3 仅存在 `Front Dial`（机顶前拨轮）、单颗 `Rear Dial`（后滚轮）与 `Control Wheel`（五向转轮）；[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中大量出现的 **`Rear Dial L` / `Rear Dial R`**（`_f 0x6a5c`/`0x680d`、`BKID_APP_setting_custom_key_*_rear_dial_{l,r}`、`BKID_APP_mydial_rear_dial_{left,right}_setting_list0..2`）均属于四拨轮 Alpha 机身（如 A7RV/A1II）的共线休眠符号。

2. **`[My Dial Settings]`**（`_f 0x6538`）：
   - 内置 **3 组临时拨轮映射库**：`[My Dial 1]`（`_f 0x67da`）、`[My Dial 2]`（`_f 0x64ec`）、`[My Dial 3]`（`_f 0x6936`），每组均可分别重映射 `Front dial`、`Rear dial` 与 `Control Wheel`（`BKID_APP_mydial_{front_dial,control_wheel}_setting_list0..2`）；
   - **3 种自定义按键召回方式**：
     - **`My Dial 1..3 during Hold`**（`_f 0x66fe/0x66fc/0x66fd`）：按住期间临时激活，松开即复原；
     - **`Toggle My Dial 1..3`**（`_f 0x6bc0/0x67e5/0x67e4`）：按一下锁定切换、再按退出；
     - **`My Dial 1→2→3`**（`_f 0x7987`）：循环切换三组银行，**自动跳过全 `Not set` 的空配置组**（`ilc/2210`）。
   - **锁机联动覆盖**：处于 `My Dial 1..3` 临时激活期间，**临时自动解除 `[Lock Operation Parts]` 对被映射拨轮的锁定**（[`G95`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)）。

3. **`[Av/Tv Rotate]`**（`_f 0x72e3`、`BKID_APP_setting_av_tv_rotate`）：
   - 选项：`Normal`（`_f 0x688f`，**默认**）vs `Reverse`（`_f 0x6175`），同步反转光圈与快门调节方向（`get_av_tv_rotate_coefficient`）。

4. **`[Function Ring(Lens)]`**（`_f 0x715e`、`BKID_APP_setting_function_ring`）：
   - **实机暴露 2 项**（适用于 Still / Movie / S&Q）：
     - **`Power Focus`**（`_f 0x767f`，**默认**）：右转将焦点推向无穷远（∞），左转拉向近景，电动平滑追焦；
     - **`APS-C/Super 35 mm / Full Frame`**（`_f 0x62e7` `\ue5ca/Full Frame`、`_f 0x76dd` `\ue5ca/Full Frame Select`，ELF `VAL_setting_function_ring_FUNCTION_RING_SUPER_35MM_SEL`）：向任意方向扭转镜头功能环即瞬间切换全画幅与 APS-C/Super 35mm 视角（注：切换受 `4K/DCI 4K` 模式防裁剪约束，若当前格式不支持 S35 则无效）。
   - **兼容镜头矩阵（`实测事实` + `推断`）**：`ilc/2210` 说明该功能仅在配备**电子功能环（Function Ring）**的兼容 E 卡口 GM/G 镜头上生效；ELF 中的 `VAL_setting_function_ring_FUNCTION_RING_INVALID` 用于无环镜头状态回退。

5. **`[Lock Operation Parts]`**（`_f 0x6904`）：
   - 选项：`Off`（**默认**）/ `Multi-Selector Only`（`_f 0x686b`）/ `Dial + Wheel`（`_f 0x61bb`）/ `All`（锁定摇杆、拨轮与转轮）。通过长按 `Fn` 或 `MENU + Fn` 5 秒（或配置锁定策略）在拍摄界面触发/解除锁定。

### 2.2 休眠遗留拨轮符号证伪与 `ILME-FX6 Ver. 6.01` 拨盘矩阵对比（`实测事实`）

- **FX3 休眠拨轮符号证伪**：
  - **`[Dial Setup]`**（`_f 0x79d1`，`BKID_APP_setting_dial_setup`：`Av/Tv` vs `Tv/Av`）：Ver. 1.xx 旧式 `M` 档固定对调项（`VAL_setting_dial_setup_*` 在 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中为 **`0` 命中**！），自 Ver. 2.00 起彻底被 `[Custom Key/Dial Set.]` 取代（仅留 `_f 0x6b1d` `Av/Tv Assign in M` 串）。
  - **`[Dial / Wheel Lock]`**（`base 0xe352`）：旧 Alpha 菜单名，FX3 Ver. 7.02 已完全由 `[Lock Operation Parts]` 取代。
- **`ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`）物理拨盘矩阵**：

| 控制节点（FX6） | 菜单路径 | 可指派功能与默认（`FX6 appFw.so` + `5-024-458-18`） | `FX3` 对应边界 |
| :--- | :--- | :--- | :--- |
| **`Multi Function Dial`**<br>（机身前多用拨盘） | `Project > Multi Function Dial > Default Function`（`ns1 0x22e0`） | **默认 `Off`**；可选：`Off` / `ISO/Gain/EI` / `IRIS` / `Auto Exposure Level` / `Audio Input Level`（**不含 `ND Filter`**；调 ND 需进 Direct Menu `ND Filter Value` 或拨物理 ND 轮）。菜单开启期间自动禁用。 | 对应 FX3 `Front Dial`（Movie 默认 `Aperture`，`[Custom Key/Dial Set.]` 映射） |
| **`Grip/Remote Dial`**<br>（侧握把/RM-30BP 拨盘） | `Project > Assignable Dial > Grip/Remote Dial`（`ns1 0x239b`） | **默认 `IRIS`**；可选：`Off` / `ISO/Gain/EI` / **`ND Filter`** / `IRIS` / `Auto Exposure Level` / `Audio Input Level` / `Multi Function Dial`；独立方向 `Grip Dial Direction`（`Normal`/`Opposite`） | FX3 无侧握把拨盘，亦无内置电子 ND |
| **`Handle Dial`**<br>（顶部手柄拨盘） | `Project > Assignable Dial > Handle Dial`（`ns1 0x239f`） | **默认 `IRIS`**；可选范围同 `Grip/Remote Dial`（含 `ND Filter` 与 `Multi Function Dial`）；独立方向 `Handle Dial Direction`（`ns1 0x23a1`） | FX3 `XLR-H1` 顶部手柄无拨盘 |
| **`IRIS Dial` / `ND Dial`** | 机身独立实体物理拨盘 | 专用 `IRIS` 拨盘（支持 `IRIS` 锁）+ 专用内置电子无级 `ND FILTER` 拨盘/增减键（`1/4..1/128` + `Auto ND`） | FX3 无机身实体 ND，无独立光圈拨盘 |

---

## 3. 子系统 3：`Setup -> [Operation Customize]` & `[Finder/Monitor]` 休眠边界与 Display LUT 交互

### 3.1 `[Different Set for Still/Mv]` 8 项位掩码 vs `[Fn Menu Settings]` `12+12` 槽位（`实测事实`）

1. **`[Different Set for Still/Mv]`（`_f 0x62ee`、`BKID_APP_setting_different_set_for_s_q_mv`）精确 8 项位掩码**：
   - `ilc/2210` 与 [`G99`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L140-L152) 实证，仅控制精确 **8 项**拍摄参数在 Still 与 Movie/S&Q 间是否独立存储：
     1. `Aperture` · 2. `Shutter Speed` · 3. `ISO` · 4. `Exposure Comp.` · 5. `Metering Mode` · 6. `White Balance` · 7. `Picture Profile` · 8. `Focus Mode`
   - **关键硬边界与罕见 Reset 例外（`ilc/2210` *Setting Reset*）**：
     - 当 `[Shutter Mode]` 设为 **`Angle`** 时，无论 `[Different Set for Still/Mv]` 中是否勾选 `Shutter Speed`，**Still 与 Movie 快门设置均强制独立**；
     - 在 8 个勾选框中，**唯独 `[Picture Profile]` 的勾选状态在执行 `[Camera Settings Reset]` 与 `[Initialize]` 时均不复位**（其余 7 项仅在 `[Initialize]` 归位，抗 `[Camera Settings Reset]`）。

2. **`[Fn Menu Settings]`（`_g 0x614b`）独立 `12+12` 槽位机制**：
   - 经由 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 实证，Fn 菜单在 NVRAM 中维护 **24 个完全独立的槽位**：`BKID_APP_fn_menu_item_ids_for_still0..11`（12 格 Still Fn 面板）与 `BKID_APP_fn_menu_item_ids_for_movie0..11`（12 格 Movie/S&Q Fn 面板），不依赖 `[Different Set for Still/Mv]` 位掩码即可恒定隔离 Still 与 Movie 快捷面板（同样抗 `[Camera Settings Reset]`）。若当前模式 12 格全设为 `Not set`（`base 0xe0ac`），按 `Fn` 键弹出 `_f 0x6220` 提示警告并拒绝空面板激活（[`G131`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py#L225-L234)）。

### 3.2 `[DISP (Screen Disp) Set]` 4 页范围与 100% 休眠 `[Finder/Monitor]` 边界（`实测事实`）

- **`[DISP (Screen Disp) Set]`（`_g 0x61da`，位于 `[Operation Customize]` `_g 0x61c4` 下，而非 `[Display Option]`）**：
  - **Monitor 拍摄页（仅暴露 4 项勾选）**：`Display All Info.`（`base 0xea0e`）、`No Disp. Info.`（`base 0xe9f9`）、`Histogram`（`base 0xe07b`）、`Level`（`base 0xe8bc`）；
  - **Monitor 回放页（仅暴露 3 项）**：`Display Info.`、`Histogram`、`No Disp. Info.`；抗 `[Camera Settings Reset]`。
- **100% 休眠/未暴露符号防火墙（无 EVF 的 FX3 硬边界，[`G129`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py#L251-L270)）**：
  - `Graphic Display`（`base 0xe07a`）：`ilc/2210` 零引用，FX3 拍摄页不暴露经典单反图形盘面；
  - `For viewfinder`（`base 0xe2e5`/`_f 0x62d3`）与 `Monitor Off`（`VAL_disp_mode_shoot_monitor_DISP_MODE_SHOOT_MONITOR_MONITOR_OFF`）：在 `FX3` 机内禁用（防无 EVF 机型黑屏死锁）；
  - **`[Finder/Monitor]` 整条分支**（`_g 0x63fc` `Finder/Monitor`、`_f 0x6daf` `Finder/Monitor Sel.`、`_f 0x74f9` `Select Finder/Monitor`、`BKID_APP_setting_finder_monitor`、`BKID_APP_disp_mode_shoot_finder` 及 `VAL_disp_mode_shoot_finder_*`）：在无内置电子取景器的 `ILME-FX3` 上 **100% 休眠未暴露**。

### 3.3 `[Gamma Display Assist]` vs Ver. 6.00+ `[Select LUT]` 交互与 `ILME-FX6` 对比（`实测事实`）

1. **`ILME-FX3 Ver. 7.02` 监看辅助分工（`ilc/2210` + `_f 0x6538`）**：
   - **传统 `[Gamma Display Assist]`**（`Setup -> [Display Option] -> [Gamma Display Assist]` `_f 0x707b`，默认 `Off`；`[Gamma Disp. Assist Typ.]` `_f 0x6d90`：`Auto` 默认 / `S-Log3→709(800%)` / `HLG(BT.2020)` / `HLG(709)`）：应用于 Still / Movie / S&Q；在**未启用 `Log Shooting` 而改用 `Picture Profile`（如 PP8/PP9 S-Log3 或 HLG）录制，或拍摄静态 HLG/Log 照片时**还原 Rec.709 对比度。`_f 0x6538` 实证提示：*`"Use Gamma Display Assist instead of LUT when Log shooting still images. 'Gamma Display Assist' set to 'On'."`*
   - **Ver. 6.00+ 电影机管线 `[Select LUT]`**（`Exposure/Color -> [Color/Tone] -> [Select LUT]` `_f 0x643e`，仅 Movie / S&Q）：在 `[Log Shooting]` = **`Flexible ISO`** 或 **`Cine EI`** / **`Cine EI Quick`** 下激活，提供 `S-Log3` / **`s709`**（默认）/ `709(800%)` 及多达 16 个自定义 17pt/33pt `.cube` 槽位（`User1..User16`），配合 `[Display LUT]`（`_f 0x729a`）与独立于 `[Color/Tone]` 的 `[Log Shooting Setting] -> [Embed LUT File]`（`_f 0x680f`）完成无损监看与封装元数据写入。**一旦开启 `Log Shooting`（`Cine EI` / `Flexible ISO`），视频监看自动由 `[Select LUT]` / `[Display LUT]` 接管，`[Gamma Display Assist]` 不再对视频起作用。**

2. **`ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`）VF `DISPLAY` 与 `Monitoring > Display On/Off` 对比**：
   - FX6 配备机身物理 `DISPLAY` 切换按键与 `Monitoring > Display On/Off`（`fx6_2 0x4241`），[`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) 中存在 **`60` 个 `BKID_APP_SETTING_*_DISPLAY` 与 `104` 个 `BKID_APP_USER_MENU_DISPLAY_ON_OF0..103` 开关符号**，实机对 **`24+` 项独立 HUD 元素** 提供颗粒化 `On/Off` 控制（远超 FX3 的 4 页整包切换）：
     - 核心状态与录制：`Rec/Play Status`（`Always On` / `Always On (Minimum)` / `On` / `Off`，保证 Slot A/B 与 Rec 状态在按下 `DISPLAY` 键隐藏 OSD 时仍常驻）、`Tally`、`Media Status`、`Battery Remain`、`Timecode`、`Clip Name`、`Clip Number`；
     - 曝光/色彩/镜头辅助：`Base Look/LUT` / `Look Name`、`Gamma Display Assist`（**在 `Cine EI` / Log 模式下硬锁 `Off`，仅 `Custom` + `Target Display = HDR(HLG)` 时可设 `On`**）、`AE Level` / `AE Mode`、`Iris Position`、`Gain Setting`、`ND Filter Position`、`Shutter Setting`、`White Balance Mode`、`SteadyShot`、`Lens Info` / `Zoom Position` / `Focus Position`；
     - 高级监看与输出状态：`Video Signal Monitor`（机内集成 Waveform 波形图 / Vectorscope 矢量示波器 / Histogram 直方图，含橙色 Zebra 线）、`Focus Area Ind.(AF-S)`（不受 `DISPLAY` 键隐藏）、`Face/Eye Detection Frame`、`RAW Output Control Status`、`SDI/HDMI Rec Control`、`SDI/HDMI Output Display`、`Network Status`、`File Transfer Status`、`Proxy Status`、`USB Stream Status`、`Digital Extender` 等。

---

## 4. 子系统 4：`Setup -> [External Output]` 完整视频矩阵 vs `ILME-FX6` `12G/6G/3G-SDI + HDMI` 双管线

### 4.1 `ILME-FX3 Ver. 7.02` `[External Output]` 4 大项全矩阵（`实测事实`）

菜单路径：`MENU -> (Setup) -> [External Output]`（`_g 0x642a`）。`ilc/2210`、`TP1000888852` 与 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 实证：**该目录全部设置项均抗 `[Camera Settings Reset]`（`Initialize`-only）**。

| 菜单层级与项目（UXC `resid16`） | 实机暴露选项与出厂默认 | ELF 核心符号与拼写真相（`FX3 appFw.so`） | 硬互锁、降档与黑屏规则（`ilc/2210`） |
| :--- | :--- | :--- | :--- |
| **`[HDMI Resolution]`**<br>（`base 0xe1d5` / `_f 0x7817`，Still & Playback） | • **`Auto`**（**默认**）<br>• `2160p`（`_f 0x7839`）<br>• `1080p`（`base 0xe1d6`）<br>• `1080i`（`base 0xe1d7`）<br>（**无 `720p`！**） | `BKID_APP_setting_hdmi_resolution`<br>`VAL_setting_hdmi_resolution_HDMI_RESOLUTION_{AUTO_SET,2160P,1080P,1080I}`<br>（休眠：`4320P_2160P`/`720P_480P`/`480I`/`576I`） | 控制待机/回放/静态拍照输出；连接电视或 4K 监视器自动握手 EDID。 |
| **`[HDMI Output Settings]` -> `[Rec. Media dur HDMI Output]`**（`_f 0x6144`） | • **`On`**（**默认**）<br>• `Off(HDMI Only)`（`_f 0x6573`） | `BKID_APP_setting_rec_media_during_hdmi_output`<br>`VAL_setting_rec_media_during_hdmi_output_REC_MEDIA_DURING_HDMI_OUTPUT_{ON,OFF}` | `On`：机内插卡同步录制 + HDMI 输出（HDMI 位深跟随 `[Movie Settings]`）；`Off(HDMI Only)`：纯外录不写卡；**在 `S&Q` 模式下硬锁 `On`**。 |
| **`[HDMI Output Settings]` -> `[Output Resolution]`**（`_f 0x79ac`） | • **`Auto`**（**默认**） / `2160p` / `1080p` / `1080i` | `BKID_APP_setting_output_resolution` | 仅在 `Rec. Media = On` 且 `RAW Output = Off` 生效；**当开启 `Log Shooting` 或 `PPLUT1..4` 且同时内录时，即使设为 `Auto`/`2160p`，HDMI 输出仍被硬件管线强降为 `1080`（[`G110`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)/[`G145`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py)）**。 |
| **`[HDMI Output Settings]` -> `[4K Output Set.(HDMI Only)]`**（`_f 0x74d7`） | • **`59.94p 10bit / 50p 10bit`**（**默认**）<br>• `29.97p 10bit` / `25p 10bit`<br>• `23.98p 10bit` / `24.00p 10bit`（`_f 0x731d`） | `BKID_APP_setting_hdmi_4k_output_setting`<br>`VAL_setting_hdmi_4k_output_setting_HDMI_ONLY_4K_OUTPUT_SETTING_{60P,50P,30P,25P,24P,24_00P}_10BIT`<br>`PRM_HAITA_hdmi_4k_outpute_apsc_restriction`（`outpute` 拼写错） | 仅在 `Rec. Media = Off(HDMI Only)` 且 `RAW = Off` 生效；**固定输出 10-bit 4:2:2，不存在 `4:2:0` 切换且无 `_f 0x748a` `24.00p 8bit`**；选 `24.00p` 强制重启且回放隔离（`_f 0x61fb/0x639b`）；`APS-C S35 = On` 时锁定禁用。 |
| **`[HDMI Output Settings]` -> `[RAW Output]` & `[RAW Output Setting]`**（`_f 0x6e97`/`0x78fd`） | • `RAW Output`：**`Off`**（**默认**）/ `On`<br>• `RAW Output Setting`：**`59.94p/50p`**（**默认**）/ `29.97p` / `25p` / `23.98p` / `24.00p` | `BKID_APP_setting_raw_output`<br>`BKID_APP_setting_raw_output_frame_rate` | 输出 `4264×2408` 16-bit 线性 RAW；要求 `Movie` 模式 + `Log Shooting != Off`；强制禁用 `Active SteadyShot`、`ClearImage/Digital Zoom` 与 `De-Squeeze Display`；独立 `[Color Gamut for RAW Output]`（`_f 0x6bdc`）自 Ver. 2.00+ 已移除。 |
| **`[HDMI Output Settings]` -> `[Time Code Output]` & `[REC Control]`**（`_f 0x72af`/`0x76e1`） | • `Time Code Output`：**`Off`**（**默认**）/ `On`<br>• `REC Control`：**`Off`**（**默认**）/ `On` | `BKID_APP_setting_rec_control`<br>`PRM_HAITA_enabled_rec_control_movie_recording_state` | `TC Output` 在 `S&Q` 下禁用；**`[REC Control] = On` 严苛要求 `[Time Code Output] = On`** 才能触发 Atomos/BM 等外录机起停。 |
| **`[HDMI Output Settings]` -> `[4ch Audio Output]`**（`_f 0x6aa0`） | • **`CH1/CH2`**（`_f 0x713b`，**默认**）<br>• `CH3/CH4`（`_f 0x6bf6`） | **`BKID_APP_setting_4ch_output_ch`**（注：非 `4ch_audio_output`）<br>`BKID_APP_setting_mov_hdmi_audio_output` | HDMI 物理标准帧通道带宽在当前输出模式下仅承载 **2 声道 LPCM**，因此拍摄 4ch 音频时需二选一路由 `CH1/CH2` 或 `CH3/CH4` 送出至 HDMI。 |
| **`[HDMI Info. Display]`**<br>（`_f 0x6e7c`） | • **`On`**（**默认**）/ `Off` | `BKID_APP_setting_hdmi_info_display`<br>`VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_{ON,OFF}` | **`On` 在 `Rec. Media = On` 且 `RAW = Off` 时强制熄灭 FX3 机内 LCD 屏**（OSD+画面仅外屏可见）；而在 `Off(HDMI Only)` 或 `RAW Output = On` 下自动强制临时切为 `Off`（外屏干净画面、机内 LCD 恢复）。 |
| **`[CTRL FOR HDMI]`**<br>（`base 0xe41f`） | • **`On`**（**默认**）/ `Off` | **`BKID_APP_setting_ctrl_for_hmdi`**（Sony 著名 `hmdi` 拼写错误） | 允许连接电视时通过电视遥控器 CEC 控制相机菜单与回放；接电视期间机内菜单部分受限。 |
| *(休眠证伪)* `24p/60p Output`（`_f 0x632b`/`0x781c`） | —（未暴露） | `0` hits in `FX3 appFw.so` & `ilc/2210` | 100% 休眠 Alpha 遗留词条（FX3 由 `[4K Output Set.]` 与 `[Movie Settings]` `24.00p` 菜单接管）。 |

### 4.2 `ILME-FX6 Ver. 6.01` `12G/6G/3G-SDI + HDMI` 双管线矩阵对比（`实测事实`）

对照 `5-024-458-18`（pp. 108–110）与 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) `VAL_setting_output_format_sdi_hdmi_OUTPUT_FORMAT_*`（共 25 个枚举符号）：

1. **`Monitoring > Output Format > SDI/HDMI`（`fx6_2 0x4236`）核心同时输出矩阵（59.94/50/29.97/25/23.98Hz）**：
   - **常规 Video 录制（`XAVC-I` / `XAVC-L` `4096×2160` 或 `3840×2160`）**：
     - **SDI OUT**（`12G/6G/3G-SDI` BNC）：可独立配置为 `4096×2160P`、`3840×2160P`、`1920×1080P (Level A)`（**默认**）、`1920×1080P (Level B)` 或 `1920×1080i`（含 PSF 枚举）；
     - **HDMI OUT**：可与 SDI **同步（Simultaneous）** 输出 `4096×2160P` / `3840×2160P` / `1920×1080P` / `1920×1080i`（**且 FX6 内置 3.5" LCD Viewfinder 与机内 XAVC 10-bit 4:2:2 录制保持全时亮屏与满帧输出，不会因 Log/`Display On/Off` 而强制将外屏降至 `1080` 或熄灭内置屏幕**）。
   - **SDI RAW 双管线（`Project > Rec Format > Codec = RAW` 或 `RAW & XAVC-I`）**：
     - 选 `4096×2160 (RAW)`：**SDI OUT 直出 16-bit `4096×2160 RAW`**，同时 **HDMI OUT 同步提供 `4096×2160P` / `3840×2160P` / `1920×1080P` / `1920×1080i`**；
     - 选 `3840×2160 (RAW)`（传感器裁剪）：**SDI OUT 直出 `3840×2160 RAW`**，HDMI OUT 同步最高 `3840×2160P`；
     - `24Hz` 系统频率下支持 `4096×2160 (RAW)`。
   - **HDMI RAW 管线（`Codec = RAW(HDMI)` 或 `RAW(HDMI) & XAVC-I`）**：
     - **HDMI OUT 输出 `4240×2392` 16-bit RAW**（不含 `24Hz`），此时 **SDI OUT 被强制降级约束为 `1920×1080P (Level A/B)` 或 `1920×1080i`**（无法同时出 4K SDI）。
   - **`S&Q > 60fps` 硬件降幅边界（`5-024-458-18` p.109–110）**：
     - 当 `S&Q Motion = On` 且 `Frame Rate > 60fps`，同时 **`Codec = RAW / RAW & XAVC-I` 或 `Monitoring > Output On/Off > SDI = On`** 时，**HDMI `4096×2160P` 与 `3840×2160P` 选项灰显禁用，HDMI 输出降至 `<= 1920×1080`**（且 HDMI 口本身不支持 S&Q RAW 录制）。
2. **`Project > SDI/HDMI Rec Control`（`fx6_2 0x428d`）三模式 vs FX3**：
   - **`Off`**：禁用触发；
   - **`SDI/HDMI Remote I/F`**：机内不插卡状态下由机身按键远程起停外录机（与机内卡无帧同步）；
   - **`Parallel Rec`**（`0x544f`）：**与机内 CFexpress/SD 录制精确并行同步起停**（FX3 仅单一 `[REC Control]` `On/Off`，需 `[Time Code Output] = On` 前置）。
3. **音频通道与 OSD 隔离差异**：FX6 支持 4 通道 24-bit 48kHz LPCM SDI 嵌入输出及 `Monitoring > Output Display` 对 **SDI / HDMI 各自独立开关 OSD 叠加**（不必以熄灭机内 LCD 为代价）。

---

## 5. 本地只读（`os.O_RDONLY`）Donor 二进制取证账本与四语言 UXC `resid16` 校验矩阵

### 5.1 22 份 Donor 工件 SHA-256 只读台账（`raw_firmware_bytes_leaked = 0`）

| Donor 工件 | 精确字节数（Bytes） | SHA-256 摘要（`os.O_RDONLY` 实测） | 核心验证符号 / 覆盖范围 |
| :--- | ---: | :--- | :--- |
| [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_fixed_zoom_speed_type`、`BKID_APP_setting_function_ring`、`BKID_APP_setting_different_set_for_s_q_mv`、`BKID_APP_setting_4ch_output_ch`、`BKID_APP_setting_ctrl_for_hmdi`、`PRM_HAITA_hdmi_4k_outpute_apsc_restriction` |
| [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_HANDLE_ZOOM_{HIGH,LOW}`、`BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY`、`ASSIGNABLE_DIAL_*`、`60` 路 `BKID_APP_SETTING_*_DISPLAY`、`VAL_setting_output_format_sdi_hdmi_*` |
| [`FX3 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc) / `_f` / `_g` | `165,740` / `373,820` / `69,600` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `base`（2,692 条）/ `_f`（7,475 条）/ `_g`（1,390 条）全量 UXC 包 |
| [`FX3 string_simplifiedchinese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc) / `_f` / `_g` | `149,064` / `322,652` / `61,296` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX3 string_traditionalchinese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc) / `_f` / `_g` | `151,908` / `324,148` / `61,372` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX3 string_japanese.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc) / `_f` / `_g` | `208,564` / `447,840` / `89,428` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `base` / `_f` / `_g` 全量 UXC 包 |
| [`FX6 string_english.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc) / [`_2.uxc`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc) | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 EN `ns1`（5,044 条）/ `ns2`（5,915 条） |
| `FX6 string_{sc,tc,ja}{,_2}.uxc`（6 个） | SC `118,644`/`122,084`<br>TC `119,168`/`121,824`<br>JA `141,692`/`144,720` | SC: `ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f` / `058c09066cd7cd4eb5d68fa4228255fa7d2ad195a4088f145ac647e3577e58a3`<br>TC: `8c34b415ce4d19fd40ca22d00c4543c64eb4741b96250de13b93ec473b25b18b` / `07fa20ae03457465a8c4922f479d6cfe1280980a70ac43797081e87654680c6d`<br>JA: `9b47630ebe8e011a9d0bdb7a2fda06574f5187222b92d60bf6887042fe186d35` / `98315732d7e29078a98dc32c077a799f8831d8bb3d96ec26ca2110ed8e36aa26` | FX6 简中 / 繁中 / 日文 `ns1` & `ns2` 全量校验 |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，FX3 `_f` / `base` / `_g` & FX6 `ns1` / `_2`）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 实机状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f 0x7164` / `0x73f2` / `0x70e1` / `base 0xe06b` | `Zoom Range` / `Optical zoom only` / `ClearImage Zoom` / `Digital Zoom` | `变焦范围` / `仅光学变焦` / `清晰影像缩放` / `数字变焦` | `變焦範圍` / `僅光學變焦` / `清晰影像縮放` / `數位變焦` | `ズーム範囲` / `光学ズームのみ` / `全画素超解像ズーム` / `デジタルズーム` | **活跃**（抗 Camera Reset；Still M/S 含 `_f 0x78bf Smart zoom only`） |
| `_f 0x6304` / `0x6fc0` / `0x78f0` | `Zoom Lever Speed` / `\ue6281st Zoom Spd.\ue62a` / `\ue6282nd Zoom Spd.\ue62a` | `变焦杆速度` / `\ue628第1变焦速度\ue62a` / `\ue628第2变焦速度\ue62a` | `變焦控制桿速度` / `\ue628第1變焦速度\ue62a` / `\ue628第2變焦速度\ue62a` | `ｽﾞｰﾑﾚﾊﾞｰｽﾋﾟｰﾄﾞ` / `\ue6281段目スピード\ue62a` / `\ue6282段目スピード\ue62a` | **活跃**（1..8 Standby/REC；可 Reset） |
| `_f 0x78e8` / `0x7128` / `0x6b9e` / `0x7435` / `0x77fd` | `Custom Key Z. Speed` / `Remote Zoom Speed` / `\ue629Speed Type` / `Variable` / `Fix` | `自定义键变焦速度` / `遥控变焦速度` / `\ue629速度类型` / `可变` / `固定` | `自訂鍵變焦速度` / `遙控變焦速度` / `\ue629速度類型` / `變量` / `固定` | `ｶｽﾀﾑｷｰｽﾞｰﾑｽﾋﾟｰﾄﾞ` / `ﾘﾓｰﾄｽﾞｰﾑｽﾋﾟｰﾄﾞ` / `\ue629スピードタイプ` / `可変` / `固定` | **活跃**（`Custom Key` 仅 Fixed 1..8；`Remote` 含 Speed Type） |
| `_f 0x6be7` / `0x7a01` / `0x7a9e` | `Zoom Ring Rotate` / `Left(W)/Right(T)` / `Right(W)/Left(T)` | `变焦环旋转` / `左(W)/右(T)` / `右(W)/左(T)` | `變焦環旋轉` / `左(W)/右(T)` / `右(W)/左(T)` | `ｽﾞｰﾑﾘﾝｸﾞ操作方向` / `左回転(W)/右回転(T)` / `右回転(W)/左回転(T)` | **活跃**（位于 Operation Customize；抗 Camera Reset） |
| `_g 0x62ed` / `_f 0x73a0` / `0x6538` / `0x7987` | `Dial Customize` / `\ue660Custom Key/Dial Set.` / `My Dial Settings` / `My Dial 1→2→3` | `转盘自定义` / `\ue660自定键/转盘设置` / `我的转盘设置` / *(顺序轮替)* | `轉盤客製化` / `\ue660自訂鍵/轉盤設定` / `我的轉盤設定` / *(順序輪替)* | `ﾀﾞｲﾔﾙｶｽﾀﾏｲｽﾞ` / `\ue660ｶｽﾀﾑｷｰ/ﾀﾞｲﾔﾙ設定` / `マイダイヤル設定` / *(循環)* | **活跃**（全部 5 项均抗 Camera Reset；`My Dial 1..3` 临时解琐） |
| `_f 0x72e3` / `0x688f` / `0x6175` / `0x6904` | `Av/Tv Rotate` / `Normal` / `Reverse` / `Lock Operation Parts` | `Av/Tv旋转` / `标准` / `翻转` / `锁定操作的部件` | `Av/Tv旋轉` / `一般` / `翻轉` / `操作鈕鎖定` | `Av/Tvの回転方向` / `通常` / `反転` / `操作部のロック` | **活跃**（`base 0xe352 Dial / Wheel Lock` & `_f 0x79d1 Dial Setup` **休眠**） |
| `_f 0x715e` / `0x767f` / `0x62e7` | `Function Ring(Lens)` / `Power Focus` / `\ue5ca/Full Frame` | `功能环(镜头)` / `电动对焦` / `\ue5ca/全幅选择` | `功能環(鏡頭)` / `電動對焦` / `\ue5ca/全幅選擇` | `ﾌｧﾝｸｼｮﾝﾘﾝｸﾞ(ﾚﾝｽﾞ)` / `パワーフォーカス` / `\ue5ca/ﾌﾙｻｲｽﾞ` | **活跃**（S35/FF 切换或电动对焦；抗 Camera Reset） |
| `_g 0x61c4` / `_f 0x62ee` / `_g 0x614b` / `0x61da` | `Operation Customize` / `Different Set for Still/Mv` / `Fn Menu Settings` / `DISP (Screen Disp) Set` | `操作自定义` / `静态/动态不同设置` / `Fn菜单设置` / `DISP(画面显示)设置` | `操作客製化` / `不同靜像/影片設定` / `Fn功能表設定` / `DISP(畫面顯示)設定` | `操作カスタマイズ` / `静止画/動画独立設定` / `Fnメニュー設定` / `DISP(画面表示)設定` | **活跃**（`8` 项独立掩码；`Fn` `12+12`；`DISP` 4 页） |
| `base 0xe07a` / `_g 0x63fc` / `_f 0x6daf` / `0x62d3` | `Graphic Display` / `Finder/Monitor` / `Finder/Monitor Sel.` / `\ue381For viewfinder` | `图形显示` / `取景器/显示屏` / `取景器/显示屏选择` / `\ue381取景器` | `圖形顯示` / `觀景窗/螢幕` / `觀景窗/螢幕選擇` / `\ue381適合觀景窗` | `グラフィック表示` / `ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ` / `ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ切換` / `\ue381ﾌｧｲﾝﾀﾞｰ撮影用` | **100% 休眠**（无 EVF 机型禁用；`DISP` 仅 `0xea0e/0xe9f9/0xe07b/0xe8bc`） |
| `_f 0x707b` / `0x6d90` / `0x643e` / `0x729a` | `Gamma Display Assist` / `Gamma Disp. Assist Typ.` / `Select LUT` / `\ue664Display LUT` | `Gamma显示辅助` / `Gamma显示辅助类型` / `选择LUT` / `\ue664显示LUT` | `Gamma顯示輔助` / `Gamma顯示輔助類型` / `選取LUT` / `\ue664顯示LUT` | `ｶﾞﾝﾏ表示ｱｼｽﾄ` / `ｶﾞﾝﾏ表示ｱｼｽﾄ方式` / `LUT選択` / `\ue664LUT表示` | **活跃**（Log Shooting 由 `Select LUT` 接管；Still Log 用 Gamma Assist） |
| `_g 0x642a` / `base 0xe1d5` / `_f 0x6144` / `0x74d7` | `External Output` / `HDMI Resolution` / `Rec. Media dur HDMI Output` / `4K Output Set.(HDMI Only)` | `外部输出` / `HDMI分辨率` / `HDMI输出时的摄像媒体` / `4K输出设置(仅HDMI)` | `外部輸出` / `HDMI解析度` / `HDMI輸出時錄製到記憶卡` / `4K輸出設定(僅限HDMI)` | `外部出力` / `HDMI解像度` / `HDMI出力時のﾒﾃﾞｨｱ記録` / `4K出力設定(HDMIのみ)` | **活跃**（仅 `Auto/2160p/1080p/1080i` & `10bit`；抗 Camera Reset） |
| `_f 0x6e97` / `0x72af` / `0x76e1` / `0x6aa0` / `0x6e7c` / `base 0xe41f` | `RAW Output` / `Time Code Output` / `REC Control` / `4ch Audio Output` / `HDMI Info. Display` / `CTRL FOR HDMI` | `RAW输出` / `Time Code输出` / `REC控制` / `4ch音频输出` / `HDMI信息显示` / `HDMI控制` | `RAW輸出` / `Time Code輸出` / `REC控制` / `4ch音訊輸出` / `HDMI資訊顯示` / `HDMI控制` | `RAW出力` / `Time Code出力` / `RECコントロール` / `4ch音声の出力` / `HDMI情報表示` / `HDMI機器制御` | **活跃**（`_f 0x748a 24.00p 8bit` & `_f 0x781c 24p/60p Output` **休眠**） |
| `fx6_2 0x4219/0x56d4` / `fx6_1 0x239b` / `fx6_2 0x4241/0x4236/0x428d` | `Handle Zoom` / `Grip/Remote Dial` / `Display On/Off` / `Output Format` / `SDI/HDMI Rec Control` | `手柄变焦` / `手柄/遥控拨盘` / `显示开/关` / `输出格式` / `SDI/HDMI录制控制` | `手柄變焦` / `手把/遙控轉盤` / `顯示開/關` / `輸出格式` / `SDI/HDMI錄製控制` | `ハンドルズーム` / `グリップ/リモートダイヤル` / `画面表示On/Off設定` / `出力フォーマット` / `SDI/HDMI記録制御` | **FX6 活跃**（60 路 `_DISPLAY`；12G-SDI + HDMI 双矩阵） |

---

## 6. 仓内安全守卫（`fx3-safety`）交叉对照与精密勘误登记

对照本波次关联的全部 `fx3-safety` 守卫（[`G95/G96`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)、[`G99/G100`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py)、[`G110`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)、[`G113`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)、[`G119`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)、[`G129`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py)、[`G131/G132`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py)、[`G145`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py)、[`G149`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.py) 与 [`G154`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.py)）：

1. **已准确锚定并延续的不变量（`实测事实`）**：
   - **`G119` & `G149`（变焦体系）**：准确锚定 `[Zoom Range]`/`[Zoom Ring Rotate]` 抗 Reset vs 三类速度可 Reset、`1st=3`/`2nd=8`、`Custom Key=3`、`Remote=Variable/3`、`XLR-H1` 无变焦杆、FX6 `0..99` 仅作 `Zoom Position` 显示而非速度菜单、以及 `CIZ/Digital` 对 `[Focus Area]`/`[Metering Mode]`/`Tracking`/`RAW`/`120p`/`HDMI RAW` 互锁；
   - **`G95`、`G100` & `G131`（拨轮体系）**：准确锚定 `[Dial Customize]` 精确 5 项与全抗 Reset、FX3 物理 3 拨轮防火墙（拒绝休眠 `Rear Dial L/R` / `Dial Setup` / `Dial / Wheel Lock`）、`My Dial 1..3` 临时解琐 `[Lock Operation Parts]`、`[Function Ring(Lens)]` 2 选项与 `INVALID` 拒真；
   - **`G99`、`G129` & `G132`（操作自定义与监看）**：准确锚定 `[Different Set for Still/Mv]` 8 项位掩码（含 `Angle` 强制独立）、`[Fn Menu Settings]` `12+12` 槽位、`[DISP]` 4 拍摄页 + 零 EVF / 零 `Graphic Display` / 零 `Finder` 黑屏防火墙、`[Select LUT]` 16 槽位 vs `[Embed LUT File]` 归属；
   - **`G110`、`G113`、`G145` & `G154`（HDMI 外输出与 SDI 对比）**：准确锚定 `[HDMI Resolution]` 4 项、Log 内录 `1080` 降档、`[HDMI Output Settings]` 8 项（`24.00p 10bit` 重启、`24.00p 8bit` 休眠、`REC Control` 强依赖 `TC Output=On`、`CH1/CH2` vs `CH3/CH4`）、`[HDMI Info. Display] = On` 熄灭 LCD 条件、`Slot 1 EROFS=30` 防火墙、`ctrl_for_hmdi` / `outpute` 拼写与 FX6 `12G-SDI + HDMI` 矩阵。

2. **显式登记的细节补充与文档勘误（`实测事实` + `推断`）**：
   - **勘误/补充 #1（`G99` 补充 `[Different Set for Still/Mv]` `[Picture Profile]` 抗 `Initialize` 例外）**：建议后续在 [`G99`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L140-L152) 显式区分 `Picture Profile` 勾选框在 `Initialize` 下亦保留（其余 7 项随 `Initialize` 归位）；
   - **勘误/补充 #2（`G149` 显式标明 `[Custom Key Z. Speed]` 无 `Speed Type = Variable`）**：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 将 `BKID_APP_setting_fixed_zoom_speed_type` 命名带 `fixed`，实测 `ilc/2210` 与 UI 仅将其暴露于 `[Remote Zoom Speed]`，而 `[Custom Key Z. Speed]` 恒定为 `Fixed Speed` `1..8`（不可设为 `Variable`）；同时明确 FX6 并无 `Speed 1..99` 菜单项；
   - **勘误/补充 #3（`G132` 显式联动 `[Gamma Display Assist]` 在 Log Shooting 时的静/动态分流）**：建议在 [`G132`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h456-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 注释中补入 `_f 0x6538`（静态 Log 照片启用 `[Gamma Display Assist]`、动态 Log 视频由 `[Select LUT]`/`[Display LUT]` 接管）以及 `FX3` 休眠 `720p` HDMI 分辨率与 `24p/60p Output`（`_f 0x781c`）零 ELF 命中说明。

---

## 7. `79/79 Waves` 收官状态与单文件所有权声明

- **Wave 79 收官结论**：至此 **Global Sony Real-Hardware Empirical Intelligence Waves（`1/79 .. 79/79`）** 全系列实机深度审计已全部闭环，完整覆盖 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 的变焦控制、拨轮自定义、操作自定义与无 EVF 显示边界、`Select LUT` vs `Gamma Display Assist`，以及 HDMI 4K/10-bit/RAW 与 12G-SDI 双管线。
- **严格单文件所有权**：本波次（`H456` / `Wave 79`）仅创建并提交 `reports/2026-11-18-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/README.md`，未修改任何 Python 源代码、测试、安全守卫、`Makefile` 或其他报告。
- **取证与清理合规**：全部本地二进制检索严格经 `os.O_RDONLY` 只读完成（`raw_firmware_bytes_leaked = 0`），零临时脚本及 `.pyc` 残留，已通过 `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 全量绿灯校验。
