# Round 69（Wave-55 · `42/42` 实机预演轮次 `R28..R69` · 第 `124..126` 次实跑 -> `126/126` 总实跑 · `84/84` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `Setup -> [Touch Operation]` 4 项 `Initialize` 树与休眠 `Touch Shutter/AE/Pad/Footer` 拦截、`[DISP (Screen Disp) Set]` 4+3 页面与零 EVF 黑屏防火墙、Still `[AEL w/ Shutter]` / `[Exp.comp.set]` / `[External Flash Set.]` vs `[Wireless Flash]` 非对称复位分割，以及 `9` 档 `[Play Speed for Interval]` + 有效 `[Edit]` vs 休眠 `[Beauty Effect]`/`[Trimming]` & Slot-1 `EROFS=30`

## 结论先行

- **实测结论**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 Round 69 三路独立 QEMU 实机预演（`r69a` / `r69b` / `r69c`，达成 **`42/42` 实机预演轮次 `R28..R69`、`126/126` 次独立实跑、`84/84` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dormant_touch_bypass_events == 0`、`zero_evf_black_screen_events == 0`、`wireless_flash_reset_split_breach == 0`、`dormant_edit_bypass_events == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r69c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r69a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 55 四大支柱门禁、休眠符号（`Touch Shutter` / `Touch AE` / `Touch Panel/Pad` / `Footer Icon Touch` / `Select Finder/Monitor` / `For viewfinder` / `Graphic Display` / `Monitor Off` / `Beauty Effect` / `Trimming`）的 fail-closed `-95 EOPNOTSUPP` 拦截、Still 4 项闪光/AEL 菜单的非对称复位边界（仅 `[Wireless Flash]` 支持 `[Camera Settings Reset]`），以及针对 `Slot 1` 的 `[Rotate]`/`[Photo Capture]`/`[Copy]` Tier-0 保险库 `-30 EROFS` 拦截；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台台架动作（电容触控屏 `Sensitive` 灵敏度与上划 `Fn` 手势、后背板 3.0" LCD `DISP` 4+3 轮巡与 zero-EVF 安全、MI 热靴 TTL 光学/无线电闪光灯联动、`9` 档间隔回放前后拨轮调速与视频抽帧 `Photo Capture` + 物理 `Slot-1` 写保护拦截 `AVF_INFO` 变更）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 69 (`42/42` Real-HW Rounds · Wave-55 · `124th..126th` Live Runs -> `126/126` Total Live Runs, `84/84` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-55 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave55-milestone-touch-shooting-disp-btn-evf-absence-ael-wireless-flash-intel/README.md`](../2026-11-17-global-sony-wave55-milestone-touch-shooting-disp-btn-evf-absence-ael-wireless-flash-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 69 轮 `42/42` 实机预演（Wave-55 · `42/42` 实机轮次 / `124th..126th` -> `126/126` 次实跑 / `84/84` PNG）三项实机预演总览（`r69a` / `r69b` / `r69c`）

| 实跑场景 | Run ID | `r69_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **69A（第 124 次实跑）：Wave-55 四大支柱 — 4 项 `[Touch Operation]` 与休眠 `Touch Shutter/AE/Pad/Footer`、4+3 `[DISP (Screen Disp) Set]` & 零 EVF 黑屏防线、Still `[AEL w/ Shutter]`/`[Exp.comp.set]`/`[External Flash Set.]` vs `[Wireless Flash]` 复位分割、`9` 速间隔回放 & 有效 `[Edit]` vs 休眠 `Beauty/Trimming` + Slot-1 `EROFS=30` + Big-6 Home** | `r69a` | `touch4_disp_flash_reset_interval_edit_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 `Setup -> [Touch Operation]` **仅 `Initialize` 复位 4 项树**：`Touch Operation`（`On` 默认 / `On: Playback Only` `_f 0x6cde` / `Off`，`_g 0x6345`）、`Touch Sensitivity`（`_f 0x739f`：`Standard` 默认 / **`Sensitive`** `_f 0x7205` — **非** `Responsive` `-22 EINVAL`）、`Touch Func. in Shooting`（`_f 0x7575`：`Touch Focus` `0x7427` / `Touch Tracking` `0x69ee` 默认 / `Off`，Still/Movie/`S&Q` 全一致）、`Swipe Up`（`_f 0x7518`：`Open the Fn Menu` `_f 0x7281` 默认 / `Off`），拒绝休眠 `Touch Shutter` (`_f 0x6a80`) / `Touch AE` (`_f 0x702a`) / `Touch Panel/Pad` (`_f 0x76ec`) / `Footer Icon Touch` (`_f 0x70da`)（`-95 EOPNOTSUPP`），对比 `ILME-FX6`（`Technical > Touch Operation` + `Touch Function in MF` `Spot Focus / Tracking AF` `0x254e`，无灵敏度/上划）；(2) 核验 `Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]`（`_g 0x61c4 -> _g 0x61da`，`Initialize`-only：`4` 拍摄页 `Display All Info. 0xea0e` / `No Disp. Info. 0xe9f9` / `Histogram 0xe07b` / `Level 0xe8bc`；`3` 回放页 `Display Info.` / `Histogram` / `No Disp. Info.`）+ **零 EVF 黑屏防线**拒绝 `Select Finder/Monitor` (`_f 0x74f9`) / `For viewfinder` (`_f 0x62d3`) / `Graphic Display` (`0xe07a`) / `Monitor Off`（`-95 EOPNOTSUPP`），对比 `FX6` 可拆卸 3.5" LCD `Viewfinder` + `Viewfinder Hood` + `Home Screen / Direct Menu Priority`；(3) 核验仅限 Still 的 **`[AEL w/ Shutter]`**（`_f 0x669d`：`Auto[def]/On/Off`，`Initialize`-only）、**`[Flash] -> [Exp.comp.set]`**（`_f 0x73c2`：`Ambient&flash[def]/Ambient only`，`Initialize`-only）与 **`[External Flash Set.]`**（`_f 0x6771`：仅 MI 热靴直插，`Initialize`-only）vs **`[Wireless Flash]`**（`_f 0x6201`：`Off[def]/On` — **四者中唯一支持 `[Camera Settings Reset]`**），对比 `FX6` 零机械快门/闪光（仅 `Flash Band Reduce`）；(4) 核验 `Playback -> [Viewing] -> [Cont. Play for Interval]`（`_f 0x78fa`）+ **`9` 档 `[Play Speed for Interval]`**（`_f 0x639e`：`1..9` 默认 **`5`**，`Initialize`-only，机内不可合成视频）+ 有效 `[Edit]`（`Rotate 0xe5ae`, `Photo Capture _f 0x6856`, `JPEG/HEIF Switch _f 0x6938`, `Copy _f 0x79fc`）vs 休眠 `Beauty Effect` (`_f 0x7849`) / `Trimming`（`-95 EOPNOTSUPP`），以及针对 `Slot 1` 的 Tier-0 保险库 **`-30 EROFS` 防火墙**（`slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r69_init_ok=1`, `r69_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.6s` | [`r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-composited.png`](assets/r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-composited.png) |
| **69B（第 125 次实跑）：Fail-Closed Wave-55 防火墙 — 休眠触控/编辑、错词 `Responsive`、零 EVF 黑屏切屏、`S&Q`/同步线/缺热靴闪光、1..9 越界速率与 `Slot-1` `Rotate`/`Photo Capture`/`Copy` `EROFS=30` 拦截** | `r69b` | `wave55_touch4_disp_zero_evf_flash_interval_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `Touch Shutter` / `Touch AE` / `Touch Panel/Pad` / `Footer Icon Touch`（`-95 EOPNOTSUPP`）、错词 `Responsive` 触控灵敏度（`-22 EINVAL`）、`Touch Operation=Off` 时 `Swipe Up`（`-16 EBUSY`）及 `FX6` 无灵敏度/上划（`-2 ENOENT`）vs `Touch Function in MF` 成功（`0`）；(2) 拦截 `DISP` 空掩码（`-22 EINVAL`）、`DISP` 含休眠项（`-95 EOPNOTSUPP`）、零 EVF 黑屏项 `Select Finder/Monitor` / `For viewfinder` / `Graphic Display` / `Monitor Off` / `DISP Button:Finder`（`-95 EOPNOTSUPP`）及 `FX3` 查 `FX6` `Viewfinder Hood`（`-2 ENOENT`）；(3) 拦截 `S&Q` 模式下全 4 项闪光/AEL（`-16 EBUSY`）、`[AEL toggle]` 自定义键抢占半按（`-16 EBUSY`）、同步线离机（`-95 EOPNOTSUPP`）、菜单复位外闪（`-95 EOPNOTSUPP`）、未插 MI 热靴（`-19 ENODEV`）与 `FX6` AEL/Wireless Flash 缺失（`-2 ENOENT`）；(4) 拦截 `[Play Speed for Interval]` 越界 `0`/`10`（`-22 EINVAL`）、机内合成间隔视频（`-95 EOPNOTSUPP`）、休眠 `Beauty Effect` / `Trimming`（`-95 EOPNOTSUPP`）、`FX6` `Photo Capture`（`-95 EOPNOTSUPP`）以及针对 `Slot-1` 的 `[Rotate]` / `[Photo Capture]` / `[Copy]` 与 `AVF_INFO` / `P2` / `cnflasha` 写入（**`-30 EROFS`**, `slot1_vault_sha256_match=1`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r69b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `8.27s` | — |
| **69C（第 126 次实跑）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-55 非对称复位层级验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r69c` | `clean_unmount_wave55_reset_h0_h3_big6` | Native ARM64 Wave-55 联合预演（**`42/42` 实机轮次 · 第 `126/126` 次独立实跑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` **仅复位 `[Wireless Flash]->Off` 与 `[Select Playback Media]->Slot 1`**，而**全 4 项 `[Touch Operation]`（`On/Sensitive/Touch Tracking/Open the Fn Menu`）、`[DISP (Screen Disp) Set]` 掩码、`[AEL w/ Shutter]`、`[Exp.comp.set]`、`[External Flash Set.]`、`[Play Speed for Interval]` 及 `[JPEG/HEIF Switch]` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave55_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave55_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.64s` | 同 `69A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-55 四大支柱初始化与 Stage-B 四路桥接（`r69a` — 第 124 次实跑）
```text
FX6_R69_WAVE55_INIT fx3_wave55_nodes_ok=1 uxc_tokens_ok=1 touch_tree_ok=1
  disp_zero_evf_ok=1 ael_flash_reset_ok=1 interval_edit_erofs_ok=1
  touch_dormant_shutter_rc=-95 touch_dormant_ae_rc=-95 touch_dormant_pad_rc=-95
  touch_dormant_footer_rc=-95 touch_sens_invalid_rc=-22
  zero_evf_sel_finder_rc=-95 zero_evf_for_vf_rc=-95 zero_evf_graphic_rc=-95 zero_evf_monoff_rc=-95
  flash_movie_ebusy_rc=-16 interval_oob_rc=-22 beauty_dormant_rc=-95 trimming_dormant_rc=-95
  slot1_rotate_erofs_rc=-30 slot1_photocap_erofs_rc=-30
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_touch_bypass_events=0 zero_evf_black_screen_events=0
  wireless_flash_reset_split_breach=0 dormant_edit_bypass_events=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r69_init_ok=1 verify_us=949989

FX6_R69_TOUCH4_DORMANT_GUARD_BRIDGE touch4_initonly_sensitive_vs_fx6_ok=1
  dormant_touch_shutter_ae_pad_footer_rejected_ok=1 fx6_touch_mf_spot_tracking_ok=1
  touch4_dormant_guard_ok=1 dormant_touch_bypass_events=0 emmc_write_count=0 r69_bridge_ok=1

FX6_R69_DISP_4PLUS3_ZERO_EVF_BRIDGE disp_4shoot_3pb_pages_initonly_ok=1
  zero_evf_finder_graphic_monoff_blocked_ok=1 fx6_vf_hood_home_direct_priority_ok=1
  disp_4plus3_zero_evf_ok=1 zero_evf_black_screen_events=0 emmc_write_count=0 p2_setting_writes=0

FX6_R69_AEL_FLASH_RESET_SPLIT_BRIDGE still_only_ael_expcomp_extflash_initonly_ok=1
  wireless_flash_only_camreset_split_ok=1 fx6_zero_flash_flashband_only_ok=1
  ael_flash_reset_split_ok=1 wireless_flash_reset_split_breach=0 cnflasha_writes=0 emmc_write_count=0

FX6_R69_INTERVAL_PB_EDIT_EROFS_BRIDGE interval_9speed_1to9_def5_initonly_ok=1
  active_edit_vs_dormant_beauty_trimming_ok=1 slot1_edit_tier0_erofs30_ok=1
  interval_pb_edit_erofs_ok=1 dormant_edit_bypass_events=0 slot1_avf_info_mutated=0
  slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `77` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`160` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-55 防火墙拦截明细（`r69b` — 第 125 次实跑）
```text
FX6_R69_WAVE55_GUARD touch_shutter_rc=-95 touch_ae_rc=-95 touch_pad_rc=-95 touch_footer_rc=-95
  touch_responsive_rc=-22 swipe_off_ebusy_rc=-16 fx6_sens_rc=-2 fx6_swipe_rc=-2 fx6_touch_mf_ok_rc=0
  disp_empty_mask_rc=-22 disp_dormant_mask_rc=-95 evf_sel_finder_rc=-95 evf_for_vf_rc=-95
  evf_graphic_rc=-95 evf_monoff_rc=-95 evf_disp_finder_rc=-95 fx3_fx6_vf_hood_rc=-2
  sq_ael_rc=-16 sq_expcomp_rc=-16 sq_wireless_rc=-16 sq_extflash_rc=-16
  ael_toggle_override_rc=-16 ext_synccord_rc=-95 ext_camreset_rc=-95 ext_unmounted_rc=-19
  fx6_ael_rc=-2 fx6_wireless_rc=-2 speed_zero_rc=-22 speed_ten_rc=-22 interval_synth_rc=-95
  beauty_dormant_rc=-95 trimming_dormant_rc=-95 slot1_rotate_erofs_rc=-30
  slot1_photocap_erofs_rc=-30 slot1_copy_erofs_rc=-30 fx6_photocap_rc=-95
  slot1_wave55_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_touch_bypass_events=0 zero_evf_black_screen_events=0 wireless_flash_reset_split_breach=0
  dormant_edit_bypass_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r69b_ok=1 verify_us=818364
```

### 2.3 洁净卸载还原原厂、Wave-55 复位层级与 `16/16 H0 == H3`（`r69c` — 第 126 次实跑）
```text
FX6_R69_CLEAN_UNMOUNT_WAVE55_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave55_survivors_ok=1 initialize_restores_wave55_defaults_ok=1
  dormant_touch_bypass_events=0 zero_evf_black_screen_events=0
  wireless_flash_reset_split_breach=0 dormant_edit_bypass_events=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r69c_ok=1 verify_us=448128
```

---

## 3. `r69a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r69a` Alpha（`26.21 KiB` / `26,842 B`） | `r69a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r69a Big6 Alpha](assets/r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-alpha.png) | ![r69a Big6 Composited](assets/r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）电容触摸屏与 Fn 上划手势台架（实测 4 项 `Setup -> [Touch Operation]` 树：`On / On: Playback Only / Off`、`Touch Sensitivity` `Standard / Sensitive`、`Touch Func. in Shooting` `Touch Focus / Touch Tracking / Off` 跨 Still/Movie/`S&Q`、`Swipe Up` `Open the Fn Menu / Off`，以及确认机内不存在 `Touch Shutter` / `Touch AE` / `Touch Panel/Pad` / `Footer Icon Touch`，对比 `ILME-FX6 Ver. 6.01` 可拆卸触摸屏 `Technical > Touch Operation` + `Touch Function in MF` `Spot Focus / Tracking AF`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）后背板 LCD 与 MI 热靴台架（实测 `Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]` 4 个拍摄页 + 3 个回放页循环、zero-EVF 机身无黑屏死机、Still 模式下 `[AEL w/ Shutter]`、`[Flash] -> [Exp.comp.set]` `Ambient&flash / Ambient only`、`[External Flash Set.]` MI 热靴直连与 `[Wireless Flash]` 唯一支持 `[Camera Settings Reset]` 的非对称复位，对比 `ILME-FX6` `Viewfinder` / `Viewfinder Hood` + `Home Screen / Direct Menu Priority` 及仅有的 `Flash Band Reduce`）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）双槽 CFexpress/SDXC 回放与编辑台架（实测 `Playback -> [Viewing] -> [Cont. Play for Interval]` 与 `1..9` 档默认 `5` `[Play Speed for Interval]` 前后拨轮调速、`[Edit]` 下 `[Rotate]`/`[Photo Capture]`/`[JPEG/HEIF Switch]`/`[Copy]` 实机写入行为与休眠 `Beauty Effect`/`Trimming` 缺席，以及物理 `Slot-1` 只读保护拦截 `AVF_INFO` 与数据扇区写入）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 69A (124th Live Run): Wave-55 4-Pillar Touch Operation 4-Item / 4+3 DISP & Zero-EVF Guard / Still AEL & Flash Reset Split / 9-Speed Interval PB & Edit Slot-1 EROFS=30 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 69 --r69-mode touch4_disp_flash_reset_interval_edit_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r69a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round69-qemu/r69a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r69a-touch-disp-flash-intervalpb-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu/assets

# Run 69B (125th Live Run): Fail-Closed Wave-55 Guard (Dormant Touch Shutter/AE/Pad/Footer, Responsive EINVAL, Zero-EVF Finder/Graphic/MonOff EOPNOTSUPP, S&Q/SyncCord/Unmounted Flash, 9-Speed OOB & Beauty/Trimming EOPNOTSUPP, Slot-1 Edit EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 69 --r69-mode wave55_touch4_disp_zero_evf_flash_interval_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r69b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round69-qemu/r69b

# Run 69C (126th Live Run — 42/42 Real-HW Rounds): Clean Unmount Stock FX3 Restoration, Wave-55 Asymmetric Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 69 --r69-mode clean_unmount_wave55_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r69c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round69-qemu/r69c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_touch_bypass_events == 0`、`zero_evf_black_screen_events == 0`、`wireless_flash_reset_split_breach == 0`、`dormant_edit_bypass_events == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
