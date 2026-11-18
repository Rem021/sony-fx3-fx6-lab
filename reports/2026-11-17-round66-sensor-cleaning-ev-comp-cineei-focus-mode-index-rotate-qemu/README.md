# Round 66（Wave-52 · `R28..R66` `39/39` 实机预演轮次 · 第 `115..117` 次实跑 -> `117/117` 总实跑 · `78/78` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `[Sensor Cleaning]` `>= 51%` 电量与关机门禁 vs `FX6` e-ND/APR、`[Exposure Comp.]` `±5.0/±2.0 EV` 与 `Cine EI` 锁定、`[Focus Mode]` 5 静态 vs 2 视频拆分，以及回放 `9/25` 索引与 `[Rotate]` `Slot-1` `EROFS=30` 保险库

## 结论先行

- **实测结论**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 Round 66 三路独立 QEMU 实机预演（`r66a` / `r66b` / `r66c`，累计 **`39/39` 实机预演轮次 `R28..R66`、`117/117` 次独立实跑、`78/78` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_i2c_tx_bytes == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r66c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r66a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了四大支柱门禁、沉睡 Alpha 符号拦截与复位不对称性；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台台架动作（真实 IBIS 超声波抖尘、物理 `NP-FZ100` 电量门槛与强制关机、物理 E-Mount 对焦环 `AF Assist` / `AF Illuminator` LED、物理 CFexpress/SDXC `Slot-1` EXIF 旋转写入及 `FX6` e-ND 实体机械校准）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 66 (Wave-52 · `39/39` Real-HW Rounds · `115th..117th` Live Runs -> `117/117` Total Live Runs, `78/78` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-52 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave52-cleaning-mode-ev-comp-reset-playback-view-group-focus-mode-intel/README.md`](../2026-11-17-global-sony-wave52-cleaning-mode-ev-comp-reset-playback-view-group-focus-mode-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 66 轮 `39/39` 实机预演（Wave-52 · `39/39` 实机轮次 / `115th..117th` -> `117/117` 次实跑 / `78/78` PNG）三项实机预演总览（`r66a` / `r66b` / `r66c`）

| 实跑场景 | Run ID | `r66_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **66A（第 115 次实跑）：Wave-52 四大支柱 — `[Sensor Cleaning]` `>= 51%` 电量与关机门禁 vs `FX6` e-ND/APR、`[Exposure Comp.]` `±5.0/±2.0 EV` & `Cine EI` 锁定、`[Focus Mode]` 5 静态 vs 2 视频拆分、回放 `9/25` 索引与 `[Rotate]` `Slot-1` `-EROFS` + Big-6 Home** | `r66a` | `cleaning_evcomp_focusmode_rotate_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Sensor Cleaning]`**（`_f.uxc 0x67d6` / 旧 `Cleaning Mode` `0xe7d7`）`get_battery_status_for_cleaning_mode`（`LOWER/UNKNOWN/UPPER`）：`NP-FZ100 >= 51%` 放行 `sequence_set_cleaning_mode` 并弹出 `_g.uxc 0x6221` 强制物理关机提示，`< 51%` 拒斥并提示 `0xe574 Power insufficient.`（`-11 EAGAIN`），对比零 IBIS 的 `FX6`（前置电控可变 ND `1/4..1/128` + `Technical > APR`，`CrCommandId_SensorCleaning` `-95 EOPNOTSUPP`，`e_nd_i2c_tx_bytes=0`）；(2) 核验 **`[Exposure Comp.]`** 静态 `±5.0 EV` vs 视频/S&Q `±2.0 EV`（`M + ISO AUTO` 生效 vs `M + Fixed ISO` 锁定 `-16 EBUSY`）、`[Exposure step]`（`0.3EV`/`0.5EV`，仅 `[Initialize]` 复位、不影响 `Shutter Mode=Angle`）、沉睡 Alpha `[Reset EV Comp.]`（`BKID_APP_setting_exposure_compensation_reset_save` `-2 ENOENT`）及 `Cine EI` / `Cine EI Quick` 彻底锁定（固定 `Base ISO 800/12800`，仅通过 `[Exposure Index]` 调节）；(3) 核验 **`[Focus Mode]`** 5 静态（`AF-S/AF-A/AF-C/DMF/MF`）vs 2 视频（`AF-C=MOVIE_AUTO`/`MF`）拆分并拒斥沉睡 `PF`/`SEMI_MANUAL`（`-95`）、静态且仅 `[Initialize]` 复位的 `[Priority Set in AF-S/AF-C]`、`[AF Illuminator]`（`Auto/Off`，随 `[Camera Settings Reset]` 复位）对比 `FX6` `AF/MF` + `Push AF Mode` + `AF Assist`；(4) 核验回放 **`[View Mode]`**（`Date/Folder(Still)/Movie` vs 沉睡 `AVCHD/MP4` `-95`）、**`[Image Index]`**（`9/25` vs 沉睡 `12/30` `0x6e7a` `-95`）、`[Display as Group]`、`[Display Rotation]`（精确 ELF 拼写 `BKID_APP_setting_display_rotatiton`）及默认 `Slot-1` **`[Rotate]`** `-30 EROFS` 保险库防火墙，并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r66_init_ok=1`, `r66_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.69s` | [`r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png`](assets/r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png) |
| **66B（第 116 次实跑）：Fail-Closed Wave-52 防火墙 — 低电量清洁、盲吹未关机、`FX6` `SensorCleaning`、`Cine EI` 曝光补偿、视频 `AF-S/AF-A/DMF`、沉睡 `12/30` 索引与 `Slot-1` `[Rotate]` 拦截** | `r66b` | `wave52_cleaning_evcomp_focusmode_rotate_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 `NP-FZ100 <= 50%` 与 Ver.1 `2` 格电量清洁（`-11 EAGAIN`）、`UNKNOWN` 电量（`-22 EINVAL`）、未关机盲吹（`-16 EBUSY`）、`FX6 CrCommandId_SensorCleaning`（`-95 EOPNOTSUPP`）；(2) 拦截 `iAuto` / `M + Fixed ISO` / `Cine EI` / `Cine EI Quick` 曝光补偿（`-16 EBUSY`）、视频越界 `+3.0 EV`（`-22 EINVAL`）、沉睡 `[Reset EV Comp.]` 与 `FX6 Exposure Comp.`（`-2 ENOENT`）；(3) 拦截视频/S&Q 启用 `AF-S/AF-A/DMF`（`-16 EBUSY`）、沉睡 `PF/SEMI_MANUAL`（`-95 EOPNOTSUPP`）、`S&Q` `[Priority Set]`（`-16 EBUSY`）、`S&Q`/`AF-C`/放大下 `[AF Illuminator]`（`-16 EBUSY`）；(4) 拦截沉睡 `MP4/AVCHD View` 与 `12/30` 索引（`-95 EOPNOTSUPP`）、视频 `[Rotate]`（`-95`）及后台传输期间 `[Rotate]`（`-16`），以及向只读 `Slot-1` 保险库/`P2`/`cnflasha` 写入 EXIF 旋转或 Wave-52 状态（`-30 EROFS`, `slot1_vault_sha256_match=1`, `e_nd_i2c_tx_bytes=0`, `emmc_write_count=0`, `r66b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.79s` | — |
| **66C（第 117 次实跑 · `39/39` 闭环）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-52 复位层级不对称验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r66c` | `clean_unmount_wave52_reset_h0_h3_big6` | Native ARM64 Wave-52 联合预演（**`39/39` 实机轮次 · 第 `117/117` 次独立实跑闭环**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 复位 `[Exposure Comp.]`、`[Focus Mode]->AF-A`、`[AF Illuminator]->Auto` 与 `[Select Playback Media]->Slot 1`，而 **`[Exposure step]`、`[Exposure Std. Adjust]`、`[Priority Set in AF-S/AF-C]`、`[View Mode]`、`[Image Index]`、`[Display as Group]` 与 `[Display Rotation]` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave52_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave52_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_i2c_tx_bytes=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.98s` | 同 `66A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-52 四大支柱初始化与 Stage-B 四路桥接（`r66a` — 第 115 次实跑）
```text
FX6_R66_WAVE52_INIT fx3_wave52_nodes_ok=1 uxc_tokens_ok=1 sensor_cleaning_ok=1
  ev_comp_cine_ei_ok=1 focus_mode_split_ok=1 playback_index_rotate_ok=1
  clean_low_bat_rc=-11 blower_on_rc=-16 fx6_clean_cr_rc=-95
  manual_fixed_iso_rc=-16 dormant_reset_ev_rc=-2 cine_ei_ev_rc=-16
  movie_afs_rc=-16 dormant_pf_rc=-95 illum_afc_rc=-16
  dormant_avchd_rc=-95 dormant_30_rc=-95 rotate_slot1_rc=-30 rotate_movie_rc=-95
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  low_bat_cleaning_bypass_events=0 cine_ei_ev_comp_bypass_events=0
  movie_focus_mode_bypass_events=0 dormant_index_bypass_events=0 slot1_wave52_write_events=0
  passive_tx_bytes_emitted=0 e_nd_i2c_tx_bytes=0 cnflasha_writes=0 e_nd_actuator_tx_count=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r66_init_ok=1 verify_us=899423

FX6_R66_CLEANING_BATTERY_END_BRIDGE cleaning_battery_51pct_gate_poweroff_ok=1
  fx6_no_ibis_end_apr_cr_eopnotsupp_ok=1 cleaning_battery_end_ok=1
  low_bat_cleaning_bypass_events=0 e_nd_i2c_tx_bytes=0 emmc_write_count=0 r66_bridge_ok=1

FX6_R66_EV_COMP_STEP_CINEEI_BRIDGE ev_comp_still5_movie2_manual_isoauto_ok=1
  exp_step_initialize_only_no_angle_ok=1 dormant_reset_ev_comp_and_cineei_lockout_ok=1
  ev_comp_step_cineei_ok=1 cine_ei_ev_comp_bypass_events=0 emmc_write_count=0 p2_setting_writes=0

FX6_R66_FOCUS_MODE_5VS2_ILLUM_BRIDGE focus_mode_5still_2movie_no_pf_semimanual_ok=1
  prio_af_s_c_still_init_and_af_illum_lockouts_ok=1 fx6_af_mf_push_af_assist_contrast_ok=1
  focus_mode_5vs2_illum_ok=1 movie_focus_mode_bypass_events=0 cnflasha_writes=0 emmc_write_count=0

FX6_R66_PLAYBACK_VIEW_INDEX_ROTATE_BRIDGE view_mode_3_and_image_index_9_25_ok=1
  display_group_and_rotatiton_elf_ok=1 rotate_slot1_erofs_30_vault_ok=1
  playback_view_index_rotate_ok=1 dormant_index_bypass_events=0 slot1_wave52_write_events=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `84` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`159` 实时线程零崩溃。

### 2.2 Fail-Closed 低电量清洁、`Cine EI` EV 锁、视频对焦模式、沉睡 `12/30` 索引与 `Slot-1` 旋转防火墙（`r66b` — 第 116 次实跑）
```text
FX6_R66_WAVE52_GUARD clean_50pct_rc=-11 clean_unknown_rc=-22 clean_v1_2bars_rc=-11
  blower_no_poweroff_rc=-16 fx6_sensor_cleaning_rc=-95
  ev_iauto_rc=-16 ev_m_fixed_iso_rc=-16 ev_movie_30_rc=-22 ev_cine_ei_rc=-16
  ev_cine_ei_quick_rc=-16 dormant_reset_ev_rc=-2 fx6_ev_comp_rc=-2
  fm_movie_afs_rc=-16 fm_movie_afa_rc=-16 fm_movie_dmf_rc=-16
  fm_dormant_pf_rc=-95 fm_dormant_semi_rc=-95 prio_sq_rc=-16
  illum_sq_rc=-16 illum_afc_rc=-16 illum_mag_rc=-16
  view_mp4_rc=-95 view_avchd_rc=-95 idx_12_rc=-95 idx_30_rc=-95
  rot_movie_rc=-95 rot_bg_xfer_rc=-16 rot_slot1_rc=-30 slot1_wave52_erofs_rc=-30
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  low_bat_cleaning_bypass_events=0 cine_ei_ev_comp_bypass_events=0
  movie_focus_mode_bypass_events=0 dormant_index_bypass_events=0 slot1_wave52_write_events=0
  passive_tx_bytes_emitted=0 e_nd_i2c_tx_bytes=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r66b_ok=1 verify_us=808680
```

### 2.3 洁净卸载还原原厂、Wave-52 复位层级与 `16/16 H0 == H3`（`r66c` — 第 117 次实跑）
```text
FX6_R66_CLEAN_UNMOUNT_WAVE52_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave52_survivors_ok=1 initialize_restores_wave52_defaults_ok=1
  low_bat_cleaning_bypass_events=0 cine_ei_ev_comp_bypass_events=0
  movie_focus_mode_bypass_events=0 dormant_index_bypass_events=0 slot1_wave52_write_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_i2c_tx_bytes=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0 r66c_ok=1 verify_us=341058
```

---

## 3. `r66a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r66a` Alpha（`26.21 KiB` / `26,842 B`） | `r66a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r66a Big6 Alpha](assets/r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-alpha.png) | ![r66a Big6 Composited](assets/r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）5 轴 IBIS 清洁与 `NP-FZ100` 供电台架（实测 `[Sensor Cleaning]` `>= 51%` 超声波抖尘、`< 51%` 弹出 `Power insufficient.` `0xe574`、完成后 `_g.uxc 0x6221` 强制物理开关机提示，以及对比物理 `ILME-FX6 Ver. 6.01` 前置电控可变 ND `1/4..1/128` 机构与 `Technical > APR` 黑参考校准）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学测光与曝光台架（实测 `[Exposure Comp.]` 静态 `±5.0 EV` vs 视频/S&Q `±2.0 EV`、`M + ISO AUTO` 生效 vs `M + Fixed ISO` 锁定、`[Exposure step]` `0.3/0.5 EV` 仅随 `[Initialize]` 复位且不干扰 `[Shutter Mode]=Angle`，以及 `Cine EI` / `Cine EI Quick` 锁定 `Base ISO 800/12800` 与 `Exposure Index` 监看移位）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）E-Mount 镜头通讯与双槽存储卡台架（实测 5 静态 vs 2 视频 `[Focus Mode]` 切换、`[Priority Set in AF-S/AF-C]`、`[AF Illuminator]` 辅助灯实光锁定条件、回放 `[View Mode]` / `[Image Index]` `9` vs `25` 缩略图 / `[Display as Group]` / `[Display Rotation]` (`rotatiton`)，以及物理 CFexpress/SDXC `Slot-1` 写保护下 `[Rotate]` EXIF 拒绝写入）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 66A (115th Live Run): Wave-52 4-Pillar Sensor Cleaning / EV Comp & Cine EI / Focus Mode 5-vs-2 / Playback Index & Rotate + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 66 --r66-mode cleaning_evcomp_focusmode_rotate_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r66a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round66-qemu/r66a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/assets

# Run 66B (116th Live Run): Fail-Closed Wave-52 Guard (Battery < 51%, FX6 CrCommandId_SensorCleaning, Cine EI EV Comp., Movie AF-S/AF-A/DMF, 12/30 Index, Slot-1 Rotate EROFS)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 66 --r66-mode wave52_cleaning_evcomp_focusmode_rotate_guard --sd-manifest-mode valid --lang schinese \
  --run-id r66b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round66-qemu/r66b

# Run 66C (117th Live Run — 39/39 Real-HW Closure): Clean Unmount Stock FX3 Restoration, Wave-52 Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 66 --r66-mode clean_unmount_wave52_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r66c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round66-qemu/r66c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_i2c_tx_bytes == 0`、`e_nd_actuator_tx_count == 0`、`low_bat_cleaning_bypass_events == 0`、`cine_ei_ev_comp_bypass_events == 0`、`movie_focus_mode_bypass_events == 0`、`dormant_index_bypass_events == 0`、`slot1_wave52_write_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
