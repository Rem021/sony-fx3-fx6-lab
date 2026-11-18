# Round 67（Wave-53 · `40/40` 实机预演里程碑 `R28..R67` · 第 `118..120` 次实跑 -> `120/120` 总实跑 · `80/80` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `[Lens Compensation]` Shading `Auto/Off` vs 休眠 `Auto: Low`、内置正面 `#8` `[AF Illuminator]` vs 零辅助灯 `FX6`、`5` 项仅 `[Initialize]` 复位焦点/光圈设置，以及 `[Create New Folder]` + `[Rating]` `1..5★` `Slot-1` `EROFS=30` 保险库

## 结论先行

- **实测结论**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 Round 67 三路独立 QEMU 实机预演（`r67a` / `r67b` / `r67c`，正式达成 **`40/40` 实机预演轮次里程碑 `R28..R67`、`120/120` 次独立实跑、`80/80` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`slot1_wave53_write_events == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r67c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r67a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了四大支柱门禁、休眠 Alpha 符号拦截与复位不对称性；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台台架动作（真实 E 卡口镜头光学畸变/暗角表、Front Module `#8` `[AF Illuminator]` LED 实光与 MI 热靴外闪协同、真实步进光圈驱动与 `5-024-458-18` `FX6` Iris 机构，以及物理 CFexpress/SDXC `Slot-1` 写保护下 `100MSDCF..999MSDCF` 建夹与 `★1..★5` EXIF/XMP/`AVF_INFO` 写入）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 67 (`40/40` Real-HW Rounds Milestone! · Wave-53 · `118th..120th` Live Runs -> `120/120` Total Live Runs, `80/80` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-53 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave53-lens-comp-af-assist-aperture-drive-folder-rating-intel/README.md`](../2026-11-17-global-sony-wave53-lens-comp-af-assist-aperture-drive-folder-rating-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 67 轮 `40/40` 实机预演里程碑（Wave-53 · `40/40` 实机轮次 / `118th..120th` -> `120/120` 次实跑 / `80/80` PNG）三项实机预演总览（`r67a` / `r67b` / `r67c`）

| 实跑场景 | Run ID | `r67_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **67A（第 118 次实跑）：Wave-53 四大支柱 — `[Lens Compensation]` Shading `Auto/Off` vs 休眠 `Auto: Low` + Movie `[Breathing Comp.]`、内置正面 `#8` `[AF Illuminator]` `4`-Lockout & Movie AF 曲线 vs `FX6`、`5` 项仅 `Initialize` 复位焦点/光圈设置 vs `FX6` Iris、`[File/Folder Settings]` + `[Create New Folder]`/`[Rating]` `Slot-1` `-EROFS` + Big-6 Home** | `r67a` | `lens_comp_af_illum_init5_rating_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Lens Compensation]`**（`_f.uxc 0x75c8` / `0x631f`）：`Shading Comp.`（`0x64e1` `Auto` 默认 / `Off`）、`Chromatic Aberration Comp.`（`0x68cd` `Auto` 默认 / `Off`）与 `Distortion Comp.`（`0x6200` `Off` 默认，挂载 `SELP1650`/`FE 28-70mm` 或 `SteadyShot=Active` 时强制锁死 `Auto` `-16 EBUSY`），以 `-95 EOPNOTSUPP` 拒绝休眠枚举 **`LENS_COMP_SHADING_AUTO_LOW`**（`_f.uxc 0x6c9c` `'Auto: Low'`），并核验仅 Movie 可用的可复位 `[Breathing Comp.]`（`0x73ea` `On/Off`），对比 `ILME-FX6` **`Technical > Lens`**（`Distortion=Off`、`S&Q=On` 或 `Codec=RAW` 时强锁 `Breathing=Off` `-16 EBUSY`）；(2) 核验 **`ILME-FX3` 内置正面模块 `#8` + MI 热靴外闪 `[AF Illuminator]`**（`BKID_APP_setting_still_image_af_illuminator` `0xe07f` `Auto/Off`）：仅 Still 有效且在 `Movie`/`S&Q`、`AF-C`/移动 `AF-A`、`Focus Magnifier` 与 `Mount Adaptor`（`LA-EA*`）四条件锁死（`-16 EBUSY`），核验 Movie `[AF Transition Speed]`（`1..7` def `5`）、`[AF Subj. Shift Sensitivity]`（`1..5` def `5_RESPONSICE`）与 `[AF Assist]`（`On/Off` def `Off`），对比无任何正面辅助灯 LED 的 `ILME-FX6`（`-2 ENOENT`）；(3) 核验 **`5` 项仅 `[Initialize]` 复位焦点与光圈设置**：`[Aperture Drive in AF]`（`Focus Priority`/`Standard`/`Silent Priority`）、`[AF w/ Shutter]`（`On/Off`）、`[Pre-AF]`（`On/Off`）、`[Circ. of Focus Point]`（水平/垂直折返、禁止对角 `-22 EINVAL`）与 `[Focus Area Color]`（`White/Red`、`BKID_APP_setting_focus_frame_color`）全部跨 `[Camera Settings Reset]` 存活，对比 `FX6` `Auto/Push Auto/Override Iris` 与休眠 `FX6_2 0x4fc3`（`-2 ENOENT`）；(4) 核验 **`[File/Folder Settings]`**（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`、单夹 `4,000` 张上限）与 `Slot 2` 可写 vs **`Slot-1` Tier-0 保险库 `-30 EROFS` 防火墙**（拦截 `[Create New Folder]`、`[Forced File Number Reset]` 与回放 `[Rating]` `★1..★5` EXIF/XMP + `AVF_INFO` 改写，`slot1_wave53_write_events=0`, `slot1_avf_info_mutated=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r67_init_ok=1`, `r67_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.42s` | [`r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-composited.png`](assets/r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-composited.png) |
| **67B（第 119 次实跑）：Fail-Closed Wave-53 防火墙 — 休眠 `Auto: Low`、`SELP1650` 畸变解锁、`FX6` 零辅助灯伪造、Movie `Aperture Drive`/`Pre-AF`、`4,001` 上限及 `Slot-1` 建夹/标星拦截** | `r67b` | `wave53_lens_comp_af_illum_init5_rating_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `LENS_COMP_SHADING_AUTO_LOW`（`-95 EOPNOTSUPP`）、`SELP1650` 与 `Active SteadyShot` 解锁 `Distortion=Off`（`-16 EBUSY`）、无触点手动镜头补正（`-19 ENODEV`）、Still / `HDMI RAW` / `S&Q 240p` 下开启 `[Breathing Comp.]`（`-16 EBUSY`）及 `FX6` `S&Q` 呼吸补偿（`-16 EBUSY`）；(2) 拦截正面 `#8` `[AF Illuminator]` 在 `S&Q`、`AF-C`、移动 `AF-A`、`Focus Magnifier` 与 `LA-EA*` 转接环下触发（`-16 EBUSY`）、`FX6` 零 LED 辅助灯伪造（`-2 ENOENT`）、`MF` 与 `SELP1650` 下 `[AF Assist]`（`-16 EBUSY` / `-19 ENODEV`）；(3) 拦截 Movie 下 `[Aperture Drive in AF]`/`[AF w/ Shutter]`/`[Pre-AF]`（`-16 EBUSY`）、`LENS_PRE_AF_NA` 镜头（`-19 ENODEV`）、对角折返（`-22 EINVAL`）与休眠 `FX6_2 0x4fc3` `'Close Iris to F2.4 for AF'`（`-2 ENOENT`）；(4) 拦截 `_` 开头文件前缀（`-22 EINVAL`）、`Date Form` 下 `[Select REC Folder]`（`-16 EBUSY`）、`4,001` 超上限建夹（`-28 ENOSPC`）、重复 `[Add Rating]`（`-17 EEXIST`）、录像中 `[Add Rating]`（`-95 EOPNOTSUPP`）、后台传输中 `[Rating]`（`-16 EBUSY`）以及向只读 **`Slot-1` 保险库 / `AVF_INFO` / `P2` / `cnflasha`** 执行 `[Create New Folder]`/`[Forced File Number Reset]`/`[Rating]` 写入（`-30 EROFS`, `slot1_vault_sha256_match=1`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r67b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.83s` | — |
| **67C（第 120 次实跑 · `40/40` 里程碑闭环）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-53 复位层级不对称验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r67c` | `clean_unmount_wave53_reset_h0_h3_big6` | Native ARM64 Wave-53 联合预演（**`40/40` 实机预演轮次里程碑 · 第 `120/120` 次独立实跑闭环**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 复位 `[Breathing Comp.]->Off`、`[AF Illuminator]->Auto`、`[AF Transition Speed]->5`、`[AF Subj. Shift Sensitivity]->5`、`[AF Assist]->Off`，而 **`[Shading/Chromatic Aberration/Distortion Comp.]`、全部 `5` 项仅 `Initialize` 复位焦点/光圈设置（`Aperture Drive in AF`/`AF w/ Shutter`/`Pre-AF`/`Circ. of Focus Point`/`Focus Area Color`）及 `[Folder Name]`/`[File Number]`/`[Set File Name]` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave53_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave53_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.36s` | 同 `67A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-53 四大支柱初始化与 Stage-B 四路桥接（`r67a` — 第 118 次实跑）
```text
FX6_R67_WAVE53_INIT fx3_wave53_nodes_ok=1 uxc_tokens_ok=1 lens_comp_ok=1 af_illum_curves_ok=1
  init5_iris_ok=1 folder_rating_ok=1 shading_auto_low_rc=-95 dist_selp1650_lock_rc=-16
  dist_active_ss_lock_rc=-16 fx6_breath_dist_off_rc=-16 illum_afc_rc=-16 illum_movie_rc=-16
  fx6_illum_rc=-2 circ_diag_rc=-22 fx6_dormant_f24_rc=-2 new_folder_slot1_rc=-30
  rating_slot1_rc=-30 p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 shading_auto_low_bypass_events=0 zero_illum_fx6_spoof_events=0
  init5_camreset_wipe_events=0 slot1_wave53_write_events=0 slot1_avf_info_mutated=0
  slot1_data_sector_writes=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r67_init_ok=1 verify_us=793754

FX6_R67_LENS_COMP_SHADING_BRIDGE shading_2opt_reject_auto_low_ok=1 distortion_lock_and_arw_raw_ok=1
  fx6_technical_lens_breathing_lock_ok=1 lens_comp_shading_ok=1 shading_auto_low_bypass_events=0
  emmc_write_count=0 r67_bridge_ok=1

FX6_R67_AF_ILLUM_MOVIE_CURVES_BRIDGE front8_af_illum_4lockouts_ok=1
  movie_af_curves_5_responsice_assist_ok=1 fx6_zero_illuminator_enoent_ok=1
  af_illum_movie_curves_ok=1 zero_illum_fx6_spoof_events=0 emmc_write_count=0 p2_setting_writes=0

FX6_R67_INIT5_FOCUS_APERTURE_BRIDGE init5_survives_camreset_ok=1
  circ_nondiag_and_focus_priority_ok=1 fx6_iris_and_dormant_f24_ok=1
  init5_focus_aperture_ok=1 init5_camreset_wipe_events=0 cnflasha_writes=0 emmc_write_count=0

FX6_R67_FOLDER_RATING_SLOT1_VAULT_BRIDGE folder_name_date_and_4000_cap_ok=1
  create_folder_fnum_reset_slot1_erofs_ok=1 rating_1to5_slot1_erofs_avf_ok=1
  folder_rating_slot1_vault_ok=1 slot1_wave53_write_events=0 slot1_avf_info_mutated=0
  slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `94` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`160` 实时线程零崩溃。

### 2.2 Fail-Closed 休眠 `Auto: Low`、正面 `#8` `[AF Illuminator]` 4-Lockout、5 项仅 `Initialize` 设置与 `Slot-1` 建夹/标星防火墙（`r67b` — 第 119 次实跑）
```text
FX6_R67_WAVE53_GUARD shading_auto_low_rc=-95 dist_selp1650_rc=-16 dist_active_ss_rc=-16
  unchipped_rc=-19 breath_still_rc=-16 breath_raw_rc=-16 breath_sq240_rc=-16 fx6_breath_sq_rc=-16
  illum_sq_rc=-16 illum_afc_rc=-16 illum_afa_mov_rc=-16 illum_mag_rc=-16 illum_laea_rc=-16
  fx6_illum_rc=-2 assist_mf_rc=-16 assist_incompat_rc=-19
  ap_movie_rc=-16 af_shutter_movie_rc=-16 pre_af_movie_rc=-16 pre_af_na_rc=-19
  circ_diag_rc=-22 fx6_dormant_f24_rc=-2 prefix_underscore_rc=-22 select_date_rc=-16
  folder_cap_4001_rc=-28 folder_slot1_rc=-30 fnum_reset_slot1_rc=-30 simult_new_folder_rc=-30
  rating_slot1_rc=-30 add_rating_dup_rc=-17 add_rating_rec_rc=-95 rating_bg_xfer_rc=-16
  slot1_wave53_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  shading_auto_low_bypass_events=0 zero_illum_fx6_spoof_events=0 init5_camreset_wipe_events=0
  slot1_wave53_write_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r67b_ok=1 verify_us=754012
```

### 2.3 洁净卸载还原原厂、Wave-53 复位层级与 `16/16 H0 == H3`（`r67c` — 第 120 次实跑 / `40/40` 里程碑闭环）
```text
FX6_R67_CLEAN_UNMOUNT_WAVE53_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave53_survivors_ok=1 initialize_restores_wave53_defaults_ok=1
  shading_auto_low_bypass_events=0 zero_illum_fx6_spoof_events=0 init5_camreset_wipe_events=0
  slot1_wave53_write_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r67c_ok=1 verify_us=408594
```

---

## 3. `r67a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r67a` Alpha（`26.21 KiB` / `26,842 B`） | `r67a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r67a Big6 Alpha](assets/r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-alpha.png) | ![r67a Big6 Composited](assets/r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）E 卡口镜头光学与 ISP 补偿台架（实测 `[Lens Compensation]` Shading `Auto/Off` 默认 `Auto` 与 `.ARW` 原始暗角增益作用、Chromatic Aberration `Auto/Off`、Distortion `Auto/Off` 在 `SELP1650`/`FE 28-70mm` 与 `SteadyShot=Active` 下的物理锁定、`[Breathing Comp.]` `On/Off` 视角裁切及仅 `[Initialize]` 复位行为，对比 `ILME-FX6 Ver. 6.01` `Technical > Lens` 在 `Distortion=Off` / `S&Q=On` / `RAW` 下的强制 `Off`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）Front Module `#8` LED 与 MI 热靴外接闪光灯台架（实测内置正面 `#8` `[AF Illuminator]` `Auto/Off` 物理点亮距离 `0.3–3.0 m` 与 `Movie`/`S&Q`、`AF-C`/移动 `AF-A`、`Focus Magnifier`、`LA-EA*` 转接环 4 重真实锁定、Movie `[AF Transition Speed]` `1..7` / `[AF Subj. Shift Sensitivity]` `1..5` `5_RESPONSICE` / `[AF Assist]` 实拍合焦曲线，以及零内置 AF 辅助灯 `ILME-FX6` 对比）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）E 卡口光圈驱动与双槽卡台架（实测 5 项仅 `[Initialize]` 复位设置 `[Aperture Drive in AF]` `Focus Priority`/`Standard`/`Silent Priority` 声响与连拍降速、`[AF w/ Shutter]`、`[Pre-AF]`、`[Circ. of Focus Point]` 水平/垂直非对角折返、`[Focus Area Color]` `White/Red` 对比 `FX6` `Auto/Push Auto/Override Iris`；以及物理 `CFexpress/SDXC` 卡槽 `Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`、`4,000` 张目录上限、物理 `Slot-1` 写保护下 `[Create New Folder]`/`[Forced File Number Reset]`/`[Rating]` `★1..★5` EXIF/XMP 与 `AVF_INFO` 拒绝改写）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 67A (118th Live Run): Wave-53 4-Pillar Lens Comp / Front #8 AF Illuminator & Movie Curves / 5 Initialize-Only Focus-Aperture / Folder & Rating Slot-1 EROFS + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 67 --r67-mode lens_comp_af_illum_init5_rating_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r67a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round67-qemu/r67a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu/assets

# Run 67B (119th Live Run): Fail-Closed Wave-53 Guard (Auto: Low -95, SELP1650/Active SS Distortion Lock, Front #8 4-Lockouts & FX6 Zero-LED, Movie Focus/Aperture Lockouts & FX6_2 0x4fc3, Date Form / 4000 Cap / Slot-1 Folder+Reset+Rating EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 67 --r67-mode wave53_lens_comp_af_illum_init5_rating_guard --sd-manifest-mode valid --lang schinese \
  --run-id r67b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round67-qemu/r67b

# Run 67C (120th Live Run — 40/40 Real-HW Milestone Closure): Clean Unmount Stock FX3 Restoration, Wave-53 Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 67 --r67-mode clean_unmount_wave53_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r67c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round67-qemu/r67c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`shading_auto_low_bypass_events == 0`、`zero_illum_fx6_spoof_events == 0`、`init5_camreset_wipe_events == 0`、`slot1_wave53_write_events == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
