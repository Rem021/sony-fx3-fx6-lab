# Round 68（Wave-54 · `41/41` 实机预演轮次 `R28..R68` · 第 `121..123` 次实跑 -> `123/123` 总实跑 · `82/82` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `[Switch V/H AF Area]` / `14` 复选框 `[Focus Area Limit]` / `[Focus Area Color]`、`5` 测光 `[Exposure Std. Adjust]` (`1/6 EV`) & Still `[Bracket Settings]`、`6` 项 `[TC/UB]` & `[TC/UB Disp. Setting]`，以及 `[Select Playback Media]` + `[Copy]` `Slot-2 -> Slot-1` 反向 `EROFS=30` 保险库护栏 & `[Slide Show]`

## 结论先行

- **实测结论**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 Round 68 三路独立 QEMU 实机预演（`r68a` / `r68b` / `r68c`，达成 **`41/41` 实机预演轮次 `R28..R68`、`123/123` 次独立实跑、`82/82` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`limit14_dormant_bypass_events == 0`、`stdadj_camreset_wipe_events == 0`、`fx3_bnc_spoof_events == 0`、`reverse_copy_slot1_write_events == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r68c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r68a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了四大支柱门禁、休眠符号拦截、`[Exposure Std. Adjust]` 全 `5` 测光模式独立复位隔离，以及 `[Select Playback Media] = Slot 2` 触发反向 `Slot 2 -> Slot 1` `[Copy]` 时对 Tier-0 保险库的 `EROFS=30` fail-closed 拦截；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台台架动作（真实机身重力姿态 IMU 垂直朝上/朝下 `INVALID` 判定、`1/6 EV` 光学测光基准偏移及 EXIF/`M.M.`/`Spot AEL` 联动、NTSC/PAL 实机信号制式时码发生器与 `FX6` 物理 BNC `TC IN/OUT` 开关、以及物理 CFexpress/SDXC 双槽下 `Slot-1` 写保护拦截卡间 `[Copy]` 与 `AVF_INFO` 重建）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 68 (`41/41` Real-HW Rounds · Wave-54 · `121st..123rd` Live Runs -> `123/123` Total Live Runs, `82/82` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-54 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave54-switch-vh-af-focus-limit-bracket-stdadj-copy-slot-intel/README.md`](../2026-11-17-global-sony-wave54-switch-vh-af-focus-limit-bracket-stdadj-copy-slot-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 68 轮 `41/41` 实机预演（Wave-54 · `41/41` 实机轮次 / `121st..123rd` -> `123/123` 次实跑 / `82/82` PNG）三项实机预演总览（`r68a` / `r68b` / `r68c`）

| 实跑场景 | Run ID | `r68_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **68A（第 121 次实跑）：Wave-54 四大支柱 — Still `AF-C` `[Switch V/H AF Area]` / `14` 复选框 `[Focus Area Limit]` / `[Focus Area Color]`、`5` 测光 `[Exposure Std. Adjust]` & `[Bracket Settings]`、`6` 项 `[TC/UB]` & `[TC/UB Disp. Setting]`、`[Select Playback Media]` + `[Copy]` `Slot-1 -> Slot-2` vs `Slot-2 -> Slot-1` `EROFS=30` & `[Slide Show]` + Big-6 Home** | `r68a` | `switch_vh_af_limit14_stdadj_tc_copy_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 Still `AF-C` 专用 **`[Switch V/H AF Area]`**（`_f.uxc 0x73ae`：`Off` 默认 / `AF Point Only` / `AF Point + AF Area`，支持 `[Camera Settings Reset]`，`0°/90°/270°` 3 态重力方向切换 vs 垂直朝上/朝下 `INVALID` `-22 EINVAL`，8 项锁定含非 `AF-C`/`Movie`/`iAuto`/数码变焦/AF 激活/连拍/自拍/`Focus Magnifier` `-16 EBUSY`，模式变更清空记忆对焦位置）、精确 **`14` 复选框 `[Focus Area Limit]`**（`_f.uxc 0x6de2`：`7` 项基础 + `7` 项 `Tracking:*`，拒绝休眠 `Spot: XL/XS` 与 `Custom 1..3` `-95 EOPNOTSUPP`，最少 `2` 项限制 `.uxc 0xea28` `-22 EINVAL`）与仅 `Initialize` 复位 **`[Focus Area Color]`**（`_f.uxc 0x74ad`：`White`/`Red`），对比 `ILME-FX6`（无 V/H 切换与 `14` 项裁剪，移动对焦框变橙色 + `Focus Area Ind.(AF-S)`）；(2) 核验全 **`5` 种测光模式 `[Exposure Std. Adjust]`**（`Multi`/`Center`/`Spot`/`Entire Screen Avg.`/`Highlight` `-1..+1 EV @ 1/6 EV` `13` 档，`.uxc 0xe567` 确认弹窗，独立写 EXIF 不改 `[Exposure Comp.]`，偏移 `M.M.` 零点与 `Spot AEL`，重置进行中的包围曝光张数，**仅 `Initialize` 复位**）+ 可复位 Still **`[Bracket Settings]`**（`[Selftimer during Bracket]` `Off/2/5/10 Sec`，`[Bracket order]` `0->-->+` / `-->0->+`），对比 `FX6`（`exposure_standard` `0` 命中 `-2 ENOENT`，休眠 `setting_bracket_*` `-95 EOPNOTSUPP`）；(3) 核验 **`6` 项 `[TC/UB]` 均仅 `Initialize` 复位**（`Time Code Preset`/`User Bit Preset`/`Time Code Format` `DF/NDF` 仅 NTSC 且 `23.98p/24.00p` 锁 `NDF` `-16 EBUSY`、`PAL` 隐藏 `-95 EOPNOTSUPP`/`Time Code Run`/`Time Code Make`/`User Bit Time Rec`）与 **`[TC/UB Disp. Setting]`**（`Counter`/`TC`/`U-Bit`，回放仅动态影像切换 `.uxc 0xe728`），对比 `FX6` 物理 BNC `TC IN/OUT` 拨动开关（`EXT-LK`）；(4) 核验 **`[Select Playback Media]`**（默认 `Slot 1`）+ **`[Copy]`**（`Slot 1 -> Slot 2` 只读源安全执行 `slot1_data_sector_writes=0`，而 **`Slot 2 -> Slot 1` 反向 `[Copy]` 触发 Tier-0 保险库 `-30 EROFS` fail-closed 拦截**）与仅 `Initialize` 复位 **`[Slide Show]`**（`Repeat Off/On`，`Interval 1/3/5/10/30 Sec`，仅 `Date/Folder View(Still)`，旁路 `[Power Save Start Time]`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r68_init_ok=1`, `r68_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.4s` | [`r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-composited.png`](assets/r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-composited.png) |
| **68B（第 122 次实跑）：Fail-Closed Wave-54 防火墙 — V/H 8 锁定 & 垂直重力、14 项 Limit 最小 2 项/休眠、1/6 EV 弹窗与越界、24p/PAL TC Format、`Slot-2 -> Slot-1` 反向 `[Copy]` `EROFS=30` 拦截** | `r68b` | `wave54_switch_vh_af_limit14_stdadj_tc_copy_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 V/H 垂直朝上/朝下 `INVALID` 重力（`-22 EINVAL`）与全 8 项锁定（非 `AF-C`/`Movie`/`iAuto`/数码变焦/AF 激活/连拍/自拍/`Focus Magnifier` `-16 EBUSY`）、`Focus Area Limit` 仅剩 1 项（`.uxc 0xea28` `-22 EINVAL`）、Movie `Tracking:*`（`-16 EBUSY`）、休眠 `Spot XL/XS` & `Custom 1..3`（`-95 EOPNOTSUPP`）与 `FX6` V/H/Limit/Color 缺失（`-2 ENOENT`）；(2) 拦截 `[Exposure Std. Adjust]` 未确认 `.uxc 0xe567`（`-11 EAGAIN`）及 `±7/6 EV` 越界（`-22 EINVAL`）、非包围/Movie `[Bracket Settings]`（`-16 EBUSY`）、`FX6` `exposure_standard`（`-2 ENOENT`）及休眠 `bracket_*`（`-95 EOPNOTSUPP`）；(3) 拦截 `24.00p` 下修改 `TC Format`（`-16 EBUSY`）、`PAL` 制式（`-95 EOPNOTSUPP`）、静态照片回放切换 `[TC/UB Disp. Setting]`（`.uxc 0xe728` `-16 EBUSY`）及 `FX3` 无物理 BNC 时码口探测（`-2 ENOENT`）；(4) 拦截 `[Copy]` 低电量（`-11 EAGAIN`）、低速卡（`-22 EINVAL`）、`Movie View` 启动 `[Slide Show]`（`-16 EBUSY`）、`FX6` 休眠 `Copy Clip`（`-95 EOPNOTSUPP`）/`Slide Show`（`-2 ENOENT`），以及 **`Slot-2 -> Slot-1` 反向 `[Copy]` 与只读 `Slot-1`/`AVF_INFO`/`P2`/`cnflasha` 写入（`-30 EROFS`, `slot1_vault_sha256_match=1`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r68b_ok=1`）** | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `8.76s` | — |
| **68C（第 123 次实跑）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-54 复位层级不对称验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r68c` | `clean_unmount_wave54_reset_h0_h3_big6` | Native ARM64 Wave-54 联合预演（**`41/41` 实机轮次 · 第 `123/123` 次独立实跑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 复位 `[Switch V/H AF Area]->Off`、`[Focus Area Limit]->14 项全选`、`[Bracket Settings]->Off / 0->-->+`、`[Select Playback Media]->Slot 1`，而 **`[Focus Area Color]`、全 `5` 项 `[Exposure Std. Adjust]`、全 `6` 项 `[TC/UB]`、`[TC/UB Disp. Setting]` 及 `[Slide Show]` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave54_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave54_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.81s` | 同 `68A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-54 四大支柱初始化与 Stage-B 四路桥接（`r68a` — 第 121 次实跑）
```text
FX6_R68_WAVE54_INIT fx3_wave54_nodes_ok=1 uxc_tokens_ok=1 switch_vh_limit_color_ok=1
  exp_stdadj_bracket_ok=1 tcub_disp_ok=1 copy_slideshow_ok=1 vh_invalid_orient_rc=-22
  limit_1area_rc=-22 limit_dormant_rc=-95 stdadj_nodlg_rc=-11 stdadj_oob_rc=-22
  tc_24p_lock_rc=-16 tc_pal_hide_rc=-95 tc_disp_still_pb_rc=-16 fx3_bnc_enoent_rc=-2
  copy_reverse_slot1_erofs_rc=-30 p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1 limit14_dormant_bypass_events=0
  stdadj_camreset_wipe_events=0 fx3_bnc_spoof_events=0 reverse_copy_slot1_write_events=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r68_init_ok=1 verify_us=821464

FX6_R68_SWITCH_VH_LIMIT14_COLOR_BRIDGE switch_vh_3orient_8locks_ok=1 focus_limit_14chk_min2_ok=1
  focus_color_initonly_vs_fx6_ok=1 switch_vh_limit14_color_ok=1 limit14_dormant_bypass_events=0
  emmc_write_count=0 r68_bridge_ok=1

FX6_R68_EXP_STDADJ_5MODE_BRACKET_BRIDGE exp_stdadj_5modes_1_6ev_ok=1 stdadj_initonly_and_mm_ael_ok=1
  bracket_settings_resettable_vs_fx6_ok=1 exp_stdadj_5mode_bracket_ok=1 stdadj_camreset_wipe_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R68_TC_UB_FORMAT_DISP_BRIDGE tcub_6items_initonly_ok=1 tc_format_ntsc_24p_pal_ok=1
  tcub_disp_moviepb_vs_fx6_bnc_ok=1 tc_ub_format_disp_ok=1 fx3_bnc_spoof_events=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R68_COPY_REVERSE_SLIDESHOW_BRIDGE copy_slot1_to_slot2_ro_ok=1 reverse_copy_slot2_to_slot1_erofs_ok=1
  slideshow_initonly_powersave_bypass_ok=1 copy_reverse_slideshow_ok=1 reverse_copy_slot1_write_events=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `81` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`158` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-54 防火墙拦截明细（`r68b` — 第 122 次实跑）
```text
FX6_R68_WAVE54_GUARD vh_invalid_orient_rc=-22 vh_non_afc_rc=-16 vh_movie_rc=-16 vh_iauto_rc=-16
  vh_dzoom_rc=-16 vh_af_active_rc=-16 vh_burst_rc=-16 vh_selftimer_rc=-16 vh_focusmag_rc=-16
  limit_1area_rc=-22 limit_dormant_rc=-95 limit_movie_track_rc=-16
  fx6_vh_rc=-2 fx6_limit_rc=-2 fx6_color_rc=-2
  stdadj_nodlg_rc=-11 stdadj_oob_pos_rc=-22 stdadj_oob_neg_rc=-22
  brk_non_brk_timer_rc=-16 brk_movie_rc=-16 fx6_stdadj_rc=-2 fx6_brk_rc=-95
  tc_24p_lock_rc=-16 tc_pal_hide_rc=-95 tc_disp_still_pb_rc=-16 fx3_bnc_enoent_rc=-2
  copy_low_bat_rc=-11 copy_slow_card_rc=-22 copy_reverse_slot1_erofs_rc=-30
  slideshow_movie_view_rc=-16 fx6_copy_clip_rc=-95 fx6_slideshow_rc=-2
  slot1_wave54_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  limit14_dormant_bypass_events=0 stdadj_camreset_wipe_events=0 fx3_bnc_spoof_events=0
  reverse_copy_slot1_write_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r68b_ok=1 verify_us=809212
```

### 2.3 洁净卸载还原原厂、Wave-54 复位层级与 `16/16 H0 == H3`（`r68c` — 第 123 次实跑）
```text
FX6_R68_CLEAN_UNMOUNT_WAVE54_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave54_survivors_ok=1 initialize_restores_wave54_defaults_ok=1
  limit14_dormant_bypass_events=0 stdadj_camreset_wipe_events=0 fx3_bnc_spoof_events=0
  reverse_copy_slot1_write_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r68c_ok=1 verify_us=389805
```

---

## 3. `r68a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r68a` Alpha（`26.21 KiB` / `26,842 B`） | `r68a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r68a Big6 Alpha](assets/r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-alpha.png) | ![r68a Big6 Composited](assets/r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）重力姿态传感器 IMU 与 AF 对焦台架（实测 Still `AF-C` 下 `[Switch V/H AF Area]` `0°/90°/270°` 自动切换对焦点/区域与垂直朝上/朝下 `INVALID`、8 项实时锁定条件及切换选项清空历史坐标、14 复选框 `[Focus Area Limit]` 最少 `2` 项限制 `.uxc 0xea28` 与 `[Focus Area Color]` `White/Red` 框色，对比 `ILME-FX6 Ver. 6.01` 移动橙框与 `Focus Area Ind.(AF-S)`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学测光与驱动马达台架（实测 `[Exposure Std. Adjust]` 全 `5` 测光模式 `Multi`/`Center`/`Spot`/`Entire Screen Avg.`/`Highlight` `-1..+1 EV @ 1/6 EV` `13` 档校准、`0xe567` 对话框、独立 EXIF 标记不叠加 `Exposure Comp.`、`M.M.` 与 `Spot AEL` 偏移、包围拍摄途中修改清空已拍张数及仅 `[Initialize]` 复位，与 Still `[Bracket Settings]` 定时/顺序及 `ILME-FX6` 对比）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）NTSC/PAL 时码发生器与双槽 CFexpress/SDXC 读写台架（实测 `6` 项仅 `[Initialize]` 复位 `[TC/UB]` 参数、`[Time Code Format]` `DF/NDF` 在 `23.98p/24.00p` 强制 `NDF` 与 `PAL` 隐藏、动态影像回放专用 `[TC/UB Disp. Setting]` `.uxc 0xe728` 对比 `FX6` 物理 BNC `TC IN/OUT` 开关 `EXT-LK`；以及物理 `Slot-1` 只读保护下 `[Select Playback Media] = Slot 2` 发起 `[Copy]` 反向写入与 `AVF_INFO` 重建阻断、`[Slide Show]` 旁路 `[Power Save Start Time]`）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 68A (121st Live Run): Wave-54 4-Pillar Switch V/H AF / 14-Chk Focus Limit / Exposure Std. Adjust / 6-Item TC/UB / Copy Slot-2->Slot-1 EROFS Firewall + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 68 --r68-mode switch_vh_af_limit14_stdadj_tc_copy_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r68a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round68-qemu/r68a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu/assets

# Run 68B (122nd Live Run): Fail-Closed Wave-54 Guard (V/H 8-Lockouts & Gravity INVALID, 14-Chk Min-2 & Dormant XL/XS/Custom1..3, 5-Mode 1/6 EV OOB/NoDlg, 24p/PAL TC Format, Slot-2 -> Slot-1 Reverse Copy EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 68 --r68-mode wave54_switch_vh_af_limit14_stdadj_tc_copy_guard --sd-manifest-mode valid --lang en \
  --run-id r68b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round68-qemu/r68b

# Run 68C (123rd Live Run — 41/41 Real-HW Rounds): Clean Unmount Stock FX3 Restoration, Wave-54 Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 68 --r68-mode clean_unmount_wave54_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r68c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round68-qemu/r68c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`limit14_dormant_bypass_events == 0`、`stdadj_camreset_wipe_events == 0`、`fx3_bnc_spoof_events == 0`、`reverse_copy_slot1_write_events == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
