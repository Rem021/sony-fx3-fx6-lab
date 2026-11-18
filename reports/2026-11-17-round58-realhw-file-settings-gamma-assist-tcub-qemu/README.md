# Round 58（Wave-44 / `R28..R58` 第 31 轮实机内核 QEMU 预演 · 第 93 次实跑）：FX3 7.02 原厂内核真机准备预演 — Movie `[File Settings]`（`Cam ID + Reel#` 与 `37` 字符标题）vs Still `[File/Folder Settings]`（`DSC` 前缀与 `Slot-1` DCIM 防护）、`[Gamma Display Assist]`（`Log` 锁死与 LCD 专属）vs `[Display LUT]` `User1..16`、`[Auto Review]=Off` 及 6 项 `[TC/UB]` 非复位持久化

> **日期**：2026-11-17 | **轮次**：**Round 58 Live ARM64 QEMU Rehearsal (Wave-44 · 31st Real-HW Round / 93rd Live Run)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r58a` / `r58b` / `r58c`，累计达成 `R28..R58` **第 `31` 轮实机内核预演**与 **第 `93` 次独立实跑**、**`62` 张 `< 50 KiB` PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 Movie `[File Settings]` / Still `[File/Folder Settings]`、外接 HDMI 显示器 `[Gamma Display Assist]` vs `[Display LUT]` `User1..16` 以及 `[Auto Review]` / 6 项 `[TC/UB]` 真机同步尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 58 轮（Wave-44 · 第 31 轮实机预演 / 第 93 次实跑）三项实机预演总览（`r58a` / `r58b` / `r58c`）

| 实跑场景 | Run ID | `r58_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **58A：电影序列号/场记板 `Cam ID + Reel#`、37 字符标题 vs 照片 `DSC`、`Gamma Display Assist` / `Display LUT` `User1..16`、`Auto Review=Off` 与 6 项 `TC/UB` + Big-6 Home** | `round58-file-settings-gamma-assist-tcub-big6` | `file_settings_camid_gamma_assist_tcub_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：核验 **Movie `[File Settings]`**（`MENU -> Shooting -> [File] -> [File Settings]`：`Series` 默认、`[File Name Format]` 含 `Cam ID + Reel#` `A..Z`/`001..999`/`C|L|R`、`37` 字符 `[Title Name Settings]` `"C"` 默认、不可变 `PRIVATE/M4ROOT/CLIP`）vs **Still `[File/Folder Settings]`**（`3` 字符 `DSC` 默认且禁止首位 `_`、`100MSDCF` Standard Form / Date Form、`-EROFS` 守护 `Slot-1`）；核验 **`[Gamma Display Assist]`**（`Off` 默认、`Auto`/`S-Log3→709(800%)`/`HLG(BT.2020)`/`HLG(709)`、`Log Shooting != Off` 时锁死 `Off`、仅限 LCD 不烧录外接 HDMI）vs **`[Display LUT]`**（`On` 默认）+ **`[Select LUT]`**（`S-Log3`/`s709`/`709(800%)`/`User1..User16`）；核验 **`[Auto Review]=[Off]`** 与全部 **6 项 `[TC/UB]`**（`Time Code Preset` `00:00:00.00`、`User Bit Preset` `00 00 00 00`、`Time Code Format` `DF`/`NDF` 及 `24.00p`/PAL 强制 `NDF`、`Time Code Run` `Rec Run`、`Time Code Make` `Preset`、`User Bit Time Rec` `Off` + `[TC/UB Disp. Setting]=TC`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.15s` | [`r58a-file-settings-gamma-assist-big6-schinese-composited.png`](assets/r58a-file-settings-gamma-assist-big6-schinese-composited.png) |
| **58B：Fail-Closed 非法注入 — `Slot-1` DCIM 修改、前导 `_` 命名、超 37 字符标题与 `Log` 下绕过开启 `Gamma Display Assist` 拦截** | `round58-slot1-dcim-prefix-log-gamma-guard` | `slot1_dcim_prefix_log_gamma_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 针对只读 `Slot-1` 保险箱注入 `[Forced File Number Reset]` 与 `[Create New Folder]` 均返回 `-EROFS`（`slot1_forced_reset_rc=-30`, `slot1_new_folder_rc=-30`, `slot1_vault_folder_mutation_events=0`）；(2) 拦截 Still `[Set File Name]` 手动前导 `_`（`still_leading_underscore_rc=-22`, `leading_underscore_prefix_events=0`）、拦截 `>37` 字符（38 字符）Movie `[Title Name Settings]`（`movie_title_38char_rc=-22`, `title_over_37char_events=0`）与 Movie 路径定制（`movie_folder_custom_rc=-95`）；(3) 拦截 `[Log Shooting]=[Cine EI]` 期间强开 `[Gamma Display Assist]=[On]`（`log_gamma_assist_on_rc=-16`, `log_gamma_assist_bypass_events=0`）及外部 HDMI 辅助 LUT 烧录（`hdmi_assist_bake_rc=-1`, `hdmi_clean_feed_assist_baked_pixels=0`）；(4) 拦截 `24.00p` 下非法 `DF` 帧率模式（`tc_df_24p_rc=-22`），保持只读保险箱零写入（`slot1_vault_writes=0`, `cnflasha_writes=0`, `emmc_write_count=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.33s` | — |
| **58C：`[Camera Settings Reset]` 非复位持久化全覆盖 + `[Initialize]` 还原 + `16/16 H0 == H3`（第 31 轮 / 第 93 次实跑收官）** | `round58-camreset-file-gamma-tcub-h0-h3-big6` | `camreset_file_gamma_tcub_init_h0_h3_big6` | Native ARM64 Wave-44 联合预演（**第 `31` 轮实机预演 / 第 `93` 次独立实跑**）：实证 Movie `[File Settings]`、Still `[File/Folder Settings]`、`[Gamma Display Assist]`/`[Display LUT]`、`[Auto Review]` 以及全部 **6 项 `[TC/UB]`** 参数均在 **`[Camera Settings Reset]`** 与 **`[Reset Network Set.]`** 后完整存活（`movie_file_settings_survive_camreset_ok=1`、`still_file_folder_survive_camreset_ok=1`、`setup_gamma_lut_autoreview_survive_camreset_ok=1`、`tcub_6items_survive_camreset_ok=1`），仅在 **`[Initialize]`** 时统一恢复出厂默认值（`initialize_restores_all_wave44_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.84s` | 同 `58A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Movie/Still 文件命名、`Gamma Display Assist` / `Display LUT` `User1..16` 与 6 项 `TC/UB`（`r58a`）
```text
FX6_R58_FILE_GAMMA_TCUB_INIT fx3_wave44_nodes_ok=1
  movie_file_settings_camid_37char_ok=1 still_file_folder_dsc_ok=1
  gamma_assist_log_lockout_lcd_only_ok=1 display_lut_user16_ok=1
  auto_review_off_default_ok=1 tcub_6items_defaults_ok=1
  wave44_survives_camreset_ok=1 title_38char_rejected_rc=-22
  leading_underscore_rejected_rc=-22 slot1_forced_reset_rc=-30
  log_gamma_assist_on_rc=-16 hdmi_assist_bake_rc=-1
  slot1_vault_folder_mutation_events=0 leading_underscore_prefix_events=0
  log_gamma_assist_bypass_events=0 hdmi_clean_feed_assist_baked_pixels=0
  e_nd_actuator_tx_count=0 slot1_vault_writes=0 p2_write_blocked_rc=-30
  p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r58_init_ok=1 verify_us=812676

FX6_R58_FILE_SETTINGS_CAMID_BRIDGE mv_camid_reel_37char_ok=1
  mv_folder_immutable_ok=1 st_dsc_prefix_no_leading_us_ok=1
  st_slot1_vault_mutation_blocked_ok=1 slot1_vault_folder_mutation_events=0
  leading_underscore_prefix_events=0 file_settings_survive_camreset_ok=1
  file_settings_camid_ok=1 emmc_write_count=0 r58_bridge_ok=1

FX6_R58_GAMMA_ASSIST_DISPLAY_LUT_BRIDGE gamma_assist_log_lockout_ok=1
  hdmi_clean_feed_assist_baked_pixels=0 log_gamma_assist_bypass_events=0
  display_lut_user16_ok=1 auto_review_off_default_ok=1
  gamma_lut_autoreview_camreset_ok=1 gamma_assist_display_lut_ok=1
  emmc_write_count=0 p2_setting_writes=0

FX6_R58_TCUB_6ITEMS_NONRESET_BRIDGE tcub_6items_verified=6
  tcub_24p_pal_ndf_lock_ok=1 tcub_6items_survive_camreset_ok=1
  tcub_disp_survives_camreset_ok=1 initialize_restores_all_wave44_ok=1
  tcub_6items_nonreset_ok=1 slot1_vault_writes=0 cnflasha_writes=0
  emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `106` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed `Slot-1` DCIM 修改、前导 `_` 与 `Log` `Gamma Display Assist` 拦截（`r58b`）
```text
FX6_R58_SLOT1_DCIM_LOG_GAMMA_GUARD slot1_forced_reset_rc=-30
  slot1_new_folder_rc=-30 slot1_vault_folder_mutation_events=0
  still_leading_underscore_rc=-22 leading_underscore_prefix_events=0
  movie_title_38char_rc=-22 title_over_37char_events=0
  movie_folder_custom_rc=-95 movie_folder_custom_events=0
  log_gamma_assist_on_rc=-16 log_gamma_assist_bypass_events=0
  hdmi_assist_bake_rc=-1 hdmi_clean_feed_assist_baked_pixels=0
  tc_df_24p_rc=-22 e_nd_actuator_tx_count=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r58b_ok=1 verify_us=732289
```

### 2.3 `[Camera Settings Reset]` 非复位持久化与 `16/16 H0 == H3`（`r58c`）
```text
FX6_R58_CAMRESET_FILE_GAMMA_TCUB_H0_H3 wave44_survives_netreset_ok=1
  movie_file_settings_survive_camreset_ok=1
  still_file_folder_survive_camreset_ok=1
  setup_gamma_lut_autoreview_survive_camreset_ok=1
  tcub_6items_survive_camreset_ok=1
  initialize_restores_all_wave44_defaults_ok=1
  slot1_vault_folder_mutation_events=0 leading_underscore_prefix_events=0
  log_gamma_assist_bypass_events=0 hdmi_clean_feed_assist_baked_pixels=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 emmc_write_count=0
  r58c_ok=1 verify_us=322832
```

---

## 3. `r58a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r58a` Alpha（`26.50 KiB` / `27,132 B`） | `r58a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r58a Big6 Alpha](assets/r58a-file-settings-gamma-assist-big6-schinese-alpha.png) | ![r58a Big6 Composited](assets/r58a-file-settings-gamma-assist-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 Movie `[File Settings]`（`Series`/`Reset`、`[Cam ID + Reel#]` `A..Z`/`001..999`/`C|L|R`、`37` 字符 `Title Name`、`PRIVATE/M4ROOT/CLIP` 不可变）与 Still `[File/Folder Settings]`（`3` 字符 `DSC` 前缀、`100MSDCF`/`Date Form`、可写 `Slot-2` 上 `[Forced File Number Reset]`/`[Create New Folder]` DCIM 目录生成）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 LCD 与外接 HDMI 监视器对比：验证 `[Log Shooting] != [Off]` 时 `[Gamma Display Assist]` 锁定 `Off`、外接 HDMI 无辅助曲线烧录，以及 `[Display LUT]`（`On` 默认）+ `[Select LUT]`（`S-Log3`、`s709`、`709(800%)`、`User1..16` `.cube` LUT 槽位）实拍监看。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `[Auto Review]=[Off]` 影院默认值以及全部 6 项 `[TC/UB]` 参数跨 `[Camera Settings Reset]` 保留与 `[Initialize]` 恢复出厂设置的行为。

---

## 5. 复现命令与洁净室合规

```bash
# Run 58A (91st Live Run): Wave-44 Movie/Still File Settings + Gamma Display Assist/LUT User1..16 + Auto Review Off + 6-Item TC/UB + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 58 --r58-mode file_settings_camid_gamma_assist_tcub_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round58-file-settings-gamma-assist-tcub-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r58-runs/r58a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r58a-file-settings-gamma-assist-big6-schinese \
  --export-png-dir reports/2026-11-17-round58-realhw-file-settings-gamma-assist-tcub-qemu/assets

# Run 58B (92nd Live Run): Fail-Closed Slot-1 DCIM Mutation, Leading-_, >37-Char Title, & Log Gamma Assist Bypass Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 58 --r58-mode slot1_dcim_prefix_log_gamma_guard --lang en \
  --run-id round58-slot1-dcim-prefix-log-gamma-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r58-runs/r58b

# Run 58C (93rd Live Run / 31st Real-HW Round): Non-Resettable Wave-44 Persistence vs [Initialize] + 16/16 H0 == H3 + Big-6 346,206 px
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 58 --r58-mode camreset_file_gamma_tcub_init_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round58-camreset-file-gamma-tcub-h0-h3-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r58-runs/r58c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round58_realhw_file_settings_gamma_assist_tcub_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round58_realhw_file_settings_gamma_assist_tcub_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
