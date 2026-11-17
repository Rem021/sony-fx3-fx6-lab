# Round 54（Wave-40 / `R28..R54` 实机内核 QEMU 第 27 轮 · 累计第 81 次实跑里程碑）：FX3 7.02 原厂内核真机准备预演 — `[Different Set for Still/Mv]` 8 项状态切换与 `[Shutter Angle]` 独立覆盖、`[Custom Key/Dial Set.]` `ISO/EI` 与 `CAMSET01.DAT` 持久化、以及 `[Remain Shoot Display]` 静态连拍缓存边界与无 EVF 硬件拓扑

> **日期**：2026-11-15 | **轮次**：**Round 54 Live ARM64 QEMU Rehearsal (Wave-40 · 27th Real-HW Round / 81st Live Run Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r54a` / `r54b` / `r54c`，累计达成 `R28..R54` 第 **27** 轮实机内核预演与第 **81** 次独立实跑、`54` 张 `< 50 KiB` PNG 视觉凭证）测得；**物理实体 `ILME-FX3` 机身上手动拨盘切测 `[Different Set for Still/Mv]` 8 项规则与 `[Shutter Mode]=[Angle]`、双卡槽实际保存/读取 `CAMSET01.DAT`、以及高速连拍写入真卡测算 `[Remain Shoot Display]` 尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 54 轮（Wave-40 · 第 27 轮实机内核 / 第 81 次实跑）三项实机预演总览（`r54a` / `r54b` / `r54c`）

| 实跑场景 | Run ID | `r54_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **54A：`[Different Set for Still/Mv]` 精确 8 项非对称转换 + `[Shutter Mode]=[Angle]` 覆盖与双重置存活 + Big-6 Home** | `round54-diff-set-still-mv-shutter-angle-big6` | `diff_set_still_mv_shutter_angle_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` 真实菜单节点（`fx3_diff_set_node_ok=1`，默认全不勾选 `diff_set_default_unchecked_ok=1`），核验精确 `8` 项（`Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`，`diff_set_8items_verified=8`，第 9 项非法输入 `rc=-22` `EINVAL`）；证实 (1) `Common -> Separate` 复制当前值到 Still 与 Movie，但 **`Custom White Balance` 保持 Still 专属**（`common_to_separate_custom_wb_still_only_ok=1`）；(2) `Separate -> Common` 恢复 5 项为出厂默认（`separate_to_common_5items_reset_defaults_ok=1`），而 **`Aperture`、`Shutter Speed` 与 `Custom White Balance` 3 项保留 Still 当前值**（`separate_to_common_3exceptions_retain_still_ok=1`，`diff_set_transition_corruption_events=0`）；(3) **`[Shutter Mode]=[Angle]`（`Ver. 6.00+`/`7.02`）覆盖规则**：即使取消勾选 `Shutter Speed`（`common`），Still 快门速度与 Movie 快门角度仍完全独立运作（`shutter_angle_unchecked_common_independent_ok=1`, `shutter_angle_common_bleed_events=0`）；同时证实跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活、仅由 `[Initialize]` 恢复（`diff_set_survives_camreset_ok=1`, `diff_set_survives_netreset_ok=1`, `initialize_restores_diff_set_defaults_ok=1`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30` `EROFS`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.26s` | [`r54a-diff-set-customkey-big6-schinese-composited.png`](assets/r54a-diff-set-customkey-big6-schinese-composited.png) |
| **54B：`[Custom Key/Dial Set.]`（`Front dial=Aperture` / `Rear dial=ISO/EI` / `Control Wheel=Shutter Speed`、`[Follow Custom]`、`[My Dial 1..3]`、`[Recall Custom hold 1..3]`）双重置存活与 `CAMSET01.DAT` 闭环** | `round54-custom-key-dial-iso-ei-camset-persist` | `custom_key_dial_iso_ei_camset_persist_guard` | Native ARM64 自定义按键/拨盘与存储卡设定档门禁实测：核验 `MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]`（`fx3_custom_key_dial_node_ok=1`），确认出厂 Cinema-Line 默认映射 **`Front dial = Aperture`**（`front_dial_aperture_default_ok=1`）、**`Rear dial = ISO/EI`**（在 `ISO` 与 `Cine EI` 曝光指数间自动自适应 `rear_dial_iso_ei_default_ok=1`, `rear_dial_iso_ei_cine_ei_adapt_ok=1`）与 **`Control Wheel = Shutter Speed`**（`control_wheel_shutter_speed_default_ok=1`），覆盖全部 `3` 域（Still / Movie / Playback `custom_key_3domains_verified=3`），验证 Movie 继承 Still 的 `[Follow Custom]`（`follow_custom_movie_inherits_still_ok=1`）、`[My Dial 1..3]` 临时切盘与松开复位（`mydial_1_3_slots_verified=3`, `mydial_release_restores_base_dials_ok=1`）及 `[Recall Custom hold 1..3]`（`recall_custom_hold_1_3_verified=3`）；证实同时跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活、仅由 `[Initialize]` 清空（`custom_key_dial_survives_camreset_ok=1`, `custom_key_dial_survives_netreset_ok=1`, `initialize_restores_custom_key_dial_defaults_ok=1`），并经 `CAMSET01.DAT` 完整无损往返还原（`camset01_custom_key_dial_roundtrip_ok=1`），同时物理 `Slot-1` 保险库卡保持 `-EROFS`（`-30`）零写入（`slot1_vault_writes=0`, `slot1_vault_sha256_match=1`） | `13/13` 校验（早期自定义按键/拨盘与 `CAMSET01.DAT` C 探针退出） | 跳过（`Custom Key/Dial Set.` C 探针退出） | **`0`** / **`0`** / **`0`** | `8.00s` | — |
| **54C：Wave-40 综合预演（`[Remain Shoot Display]` 静态连拍缓存边界 + 无 EVF `ILME-FX3` 零 `[Finder/Monitor]` 伪造 + Big-6 `346,206` px + `16/16 H0 == H3`）** | `round54-remain-shoot-evf-less-integrated-big6` | `remain_shoot_evf_less_integrated_big6` | Native ARM64 Wave-40 全链路联合预演（累计第 **81** 次独立实跑）：核验 `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]`（`fx3_remain_shoot_node_ok=1`，出厂默认 `Not Displayed` `remain_shoot_default_not_displayed_ok=1`，`Not Displayed` / `Always Display` / `Shoot-Only Display` 三档 `remain_shoot_3modes_verified=3`，非法档位 `rc=-22` `EINVAL`），严格限定静态连续连拍缓存范围且绝不伪造视频剩余卡时长（`remain_shoot_still_buffer_scope_ok=1`, `remain_shoot_movie_card_time_spoof_events=0`），并跨 `[Camera Settings Reset]`/`[Reset Network Set.]` 存活（`remain_shoot_survives_camreset_netreset_ok=1`）；同步核验 **`ILME-FX3` 无内置 EVF 硬件拓扑**（`fx3_has_builtin_evf=0`, `finder_monitor_rejected_rc=-95` `EOPNOTSUPP`, `finder_monitor_eye_sensor_spoof_events=0`, `evf_less_fx3_topology_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 完整渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.73s` | 同 `54A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Different Set for Still/Mv]` 8 项状态切换、`[Shutter Angle]` 独立性与 Big-6 渲染（`r54a`）
```text
FX6_R54_DIFF_SET_INIT fx3_diff_set_node_ok=1 diff_set_default_unchecked_ok=1
  invalid_diff_item_rc=-22 diff_set_8items_verified=8
  common_to_separate_8items_copy_ok=1
  common_to_separate_custom_wb_still_only_ok=1
  separate_to_common_5items_reset_defaults_ok=1
  separate_to_common_3exceptions_retain_still_ok=1
  diff_set_transition_corruption_events=0
  shutter_angle_unchecked_common_independent_ok=1
  shutter_angle_common_bleed_events=0 diff_set_survives_camreset_ok=1
  diff_set_survives_netreset_ok=1 initialize_restores_diff_set_defaults_ok=1
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r54_init_ok=1 verify_us=917456

FX6_R54_DIFF_SET_BRIDGE diff_set_8items_verified=8
  common_to_separate_custom_wb_still_only_ok=1
  separate_to_common_3exceptions_retain_still_ok=1
  shutter_angle_unchecked_common_independent_ok=1
  shutter_angle_common_bleed_events=0
  diff_set_survives_camreset_netreset_ok=1 diff_set_ok=1
  emmc_write_count=0 r54_bridge_ok=1

FX6_R54_CUSTOM_KEY_DIAL_BRIDGE front_dial_aperture_ok=1 rear_dial_iso_ei_ok=1
  control_wheel_shutter_speed_ok=1 follow_custom_ok=1 mydial_1_3_verified=3
  recall_custom_hold_1_3_verified=3 custom_key_survives_camreset_netreset_ok=1
  camset01_roundtrip_slot1_ro_ok=1 slot1_vault_writes=0
  custom_key_dial_ok=1 emmc_write_count=0 p2_setting_writes=0

FX6_R54_REMAIN_SHOOT_EVF_BRIDGE remain_shoot_default_not_displayed_ok=1
  remain_shoot_3modes_verified=3 remain_shoot_still_buffer_only_ok=1
  remain_shoot_movie_card_time_spoof_events=0 fx3_has_builtin_evf=0
  finder_monitor_eye_sensor_spoof_events=0
  remain_shoot_survives_camreset_netreset_ok=1 remain_shoot_evf_ok=1
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `102` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Custom Key/Dial Set.]`（`ISO/EI`、`Follow Custom`、`My Dial 1..3`、`Recall Custom hold 1..3`）与 `CAMSET01.DAT` 持久化闭环（`r54b`）
```text
FX6_R54_CUSTOM_KEY_DIAL_PERSIST fx3_custom_key_dial_node_ok=1
  front_dial_aperture_default_ok=1 rear_dial_iso_ei_default_ok=1
  control_wheel_shutter_speed_default_ok=1
  rear_dial_iso_ei_cine_ei_adapt_ok=1 custom_key_3domains_verified=3
  follow_custom_movie_inherits_still_ok=1 mydial_1_3_slots_verified=3
  mydial_release_restores_base_dials_ok=1 recall_custom_hold_1_3_verified=3
  custom_key_dial_survives_camreset_ok=1 custom_key_dial_survives_netreset_ok=1
  initialize_restores_custom_key_dial_defaults_ok=1
  camset01_custom_key_dial_roundtrip_ok=1 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 slot1_vault_writes=0 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0
  emmc_write_count=0 r54b_ok=1 verify_us=983494
```

### 2.3 Wave-40 综合预演：`[Remain Shoot Display]` 静态连拍缓存 + 无 EVF 硬件拓扑 + Big-6 `346,206` px + `16/16 H0 == H3`（`r54c`）
```text
FX6_R54_REMAIN_SHOOT_EVF_INTEGRATED fx3_remain_shoot_node_ok=1
  remain_shoot_default_not_displayed_ok=1 invalid_remain_shoot_rc=-22
  remain_shoot_3modes_verified=3 remain_shoot_still_buffer_scope_ok=1
  remain_shoot_movie_card_time_spoof_events=0
  remain_shoot_survives_camreset_netreset_ok=1 fx3_has_builtin_evf=0
  finder_monitor_rejected_rc=-95 finder_monitor_eye_sensor_spoof_events=0
  evf_less_fx3_topology_ok=1 wave40_3pillars_integrated_ok=1
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r54c_ok=1 verify_us=414230
```

---

## 3. `r54a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r54a` Alpha（`26.50 KiB` / `27,132 B`） | `r54a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r54a Big6 Alpha](assets/r54a-diff-set-customkey-big6-schinese-alpha.png) | ![r54a Big6 Composited](assets/r54a-diff-set-customkey-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身菜单与拨盘实测：在 `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` 中逐一勾选/取消全部 8 项（`Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`），核验 `Common -> Separate`（`Custom White Balance` 仅限静态）、`Separate -> Common`（保留静态 `Aperture`/`Shutter Speed`/`Custom White Balance`），以及 `[Shutter Mode]=[Angle]` 在取消 `Shutter Speed` 勾选时仍保持静态快门与电影快门角度独立运行。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身按键拨盘与双卡槽实测：在真机 `[Custom Key/Dial Set.]` 上验证 `Front dial=Aperture`、`Rear dial=ISO/EI`、`Control Wheel=Shutter Speed`、`[Follow Custom]`、`[My Dial 1..3]` 与 `[Recall Custom hold 1..3]`，实测 `[Camera Settings Reset]` 存活与真实双卡槽 `CAMSET01.DAT` 导入导出边界。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）连续连拍缓存与无 EVF 侧翻液晶屏实测：开启 `[Remain Shoot Display]`（`[Not Displayed]` / `[Always Display]` / `[Shoot-Only Display]`）在真卡连拍下观测静态连拍缓存余量显示及录像模式下保持显示存储卡剩余时长，并实体确认 `ILME-FX3` 无内置 EVF 与 `[Finder/Monitor]` 眼控传感器。

---

## 5. 复现命令与洁净室合规

```bash
# Run 54A (79th Live Run): [Different Set for Still/Mv] 8-Item Transitions & [Shutter Angle] Override + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 54 --r54-mode diff_set_still_mv_shutter_angle_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round54-diff-set-still-mv-shutter-angle-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r54-runs/r54a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r54a-diff-set-customkey-big6-schinese \
  --export-png-dir reports/2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu/assets

# Run 54B (80th Live Run): [Custom Key/Dial Set.] (Front=Aperture, Rear=ISO/EI, Wheel=Shutter Speed) & CAMSET01.DAT Persistence
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 54 --r54-mode custom_key_dial_iso_ei_camset_persist_guard --lang en \
  --run-id round54-custom-key-dial-iso-ei-camset-persist --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r54-runs/r54b

# Run 54C (81st Live Run): Integrated Wave-40 Rehearsal ([Remain Shoot Display] Still Buffer + EVF-Less Topology + Big-6 346,206 px + 16/16 H0 == H3)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 54 --r54-mode remain_shoot_evf_less_integrated_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round54-remain-shoot-evf-less-integrated-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r54-runs/r54c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round54_realhw_diff_set_still_mv_custom_key_remain_shoot_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round54_realhw_diff_set_still_mv_custom_key_remain_shoot_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
