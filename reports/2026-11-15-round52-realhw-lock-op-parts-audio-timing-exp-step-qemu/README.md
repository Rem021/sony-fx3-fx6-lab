# Round 52（Wave-38 / `R28..R52` 实机内核 QEMU 第 25 轮 · 累计第 75 次实跑里程碑）：FX3 7.02 原厂内核真机准备预演 — `[Lock Operation Parts]`（`MENU + Fn` 5s 全机身锁定 vs `MENU + Delete` 2s 全格式化防混淆及 `My Dial 1..3` 临时越权解锁）、`[Audio Out Timing]` vs `[Audio signals]` 跨重置分层与 `[Silent Mode]` 硬静音锁、以及 `[Exposure step]` 四域步进重整化 vs `[Shutter Angle]` 恒定角度表豁免

> **日期**：2026-11-15 | **轮次**：**Round 52 Live ARM64 QEMU Rehearsal (Wave-38 · 25th Real-HW Round / 75th Live Run Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r52a` / `r52b` / `r52c`，累计达成 `R28..R52` 第 **25** 轮实机内核预演与第 **75** 次独立实跑）测得；**物理实体 `ILME-FX3` 机身上按压实体按键/拨轮实测 `MENU + Fn >= 5s` 全机身锁定（与 `>= 3s` 解除、快门键豁免）及 `[My Dial 1..3]` 临时拨轮越权、使用 3.5 mm 耳机延迟示波器与消音暗室实测 `[Audio Out Timing]` `Live`/`Lip Sync` 相位差与 `[Silent Mode]=On` 蜂鸣器物理静音、以及挂载 E 卡口镜头旋转物理拨轮实测 `[Exposure step]` `0.3EV`/`0.5EV` 对比 `[Shutter Mode]=[Angle]`（`5.6°..360°`）恒定角度表尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 52 轮（Wave-38 · 第 25 轮实机内核 / 第 75 次实跑）三项实机预演总览（`r52a` / `r52b` / `r52c`）

| 实跑场景 | Run ID | `r52_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **52A：`[Lock Operation Parts]` 4 档存活、`Fn` 3s 切换、`MENU+Fn` 5s/3s 全机身组合键防 `MENU+Delete` 2s 误格式化、`My Dial 1..3` 临时越权 + Big-6 Home** | `round52-lock-op-parts-mydial-big6` | `lock_op_parts_chord_mydial_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]` 真实菜单节点（`fx3_lock_op_node_ok=1`），核验 `Off`（出厂默认，`lock_op_default_off_ok=1`）/ `Multi-Slct Only` / `Dial/Wheel` / `Dial+Wheel+MSlct` 全部 `4` 档（`lock_op_4modes_verified=4`，非法枚举以 `rc=-22` `EINVAL` 拒绝），证实同时跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 持久化存活且仅由 `[Initialize]` 恢复 `Off`（`lock_op_survives_camreset_ok=1`, `lock_op_survives_netreset_ok=1`, `initialize_restores_lock_op_off_ok=1`）；核验长按 `Fn >= 3000 ms` 切换局部锁定（`<3s` 返回 `-EAGAIN`，`fn_hold_3s_toggle_ok=1`）及锁定状态下唤起 `[My Dial 1..3]` 临时解锁拨轮并在松开后立即重锁（`mydial_1_3_temp_override_verified=3`, `mydial_release_relocks_ok=1`）；核验 **`MENU + Fn >= 5000 ms`** 全机身锁定（快门键豁免 `shutter_exempt_ok=1`）与 **`MENU + Fn >= 3000 ms`** 解除（`menu_fn_5s_fullbody_lock_ok=1`, `menu_fn_3s_fullbody_release_ok=1`），并以 `-EPERM`（`-1`）硬拦截高危 **`MENU + Delete >= 2000 ms`** 双卡槽全格式化混淆（`destructive_menu_delete_confusions=0`, `slot1_vault_format_events=0`, `slot2_format_events=0`, `slot1_vault_sha256_match=1`）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.18s` | [`r52a-lock-op-parts-mydial-big6-schinese-composited.png`](assets/r52a-lock-op-parts-mydial-big6-schinese-composited.png) |
| **52B：`[Audio Out Timing]` vs `[Audio signals]` 跨重置分层与 `[Silent Mode]` 硬静音锁护栏** | `round52-audio-out-timing-vs-audio-signals-guard` | `audio_out_timing_vs_audio_signals_guard` | Native ARM64 音频监听与操作提示音门禁实测：核验 Shooting 层 `[Audio Out Timing]` 默认 `Live`（`audio_out_timing_default_live_ok=1`，`Live` 零延迟监听 / `Lip Sync` 音画同步双档 `audio_out_timing_2modes_verified=2`）对比 Setup 层 `[Audio signals]` 默认 `On: all`（`audio_signals_default_on_all_ok=1`，`On: all` / `On: shutter only` / `Off: all` 三档 `audio_signals_3modes_verified=3` 且 `shutter_only_selectivity_ok=1`；非法枚举均以 `rc=-22` `EINVAL` 拒绝）；证实执行 `[Camera Settings Reset]` 时 `[Audio Out Timing]` 恢复 `Live` 而 `[Audio signals]` 跨重置存活、仅在 `[Initialize]` 时双双恢复出厂默认（`shooting_vs_setup_audio_reset_split_ok=1`, `initialize_restores_audio_defaults_ok=1`）；证实 `S&Q Motion` 与 `[Audio Recording]=Off` 下以 `-EOPNOTSUPP`（`-95`）锁定 `[Audio Out Timing]`（`audio_out_timing_sq_or_recoff_bypass_events=0`），且开启 `[Silent Mode]=On` 时以 `-EBUSY`（`-16`）强制静音并锁定 `[Audio signals]`、关闭静音后无损恢复原档位（`silent_mode_audio_signal_leak_events=0`, `silent_off_restores_audio_signals_ok=1`） | `13/13` 校验（早期音频时序与提示音 C 探针退出） | 跳过（音频时序与提示音 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.62s` | — |
| **52C：`[Exposure step]` 四域步进重整化 vs `Ver. 7.02` `[Shutter Angle]` 恒定角度表豁免 + `16/16 H0 == H3`** | `round52-exposure-step-vs-shutter-angle-h0-h3` | `exposure_step_vs_shutter_angle_guard` | Native ARM64 曝光步进与电影快门角度独立性探针证实：核验 `[Exposure step]` 默认 `0.3EV`（`exposure_step_default_03ev_ok=1`）及 `0.3EV`/`0.5EV` 双档（`exposure_step_2modes_verified=2`，非法枚举 `rc=-22` `EINVAL`），经 `[Camera Settings Reset]` 与 `[Initialize]` 均恢复 `0.3EV`（`exposure_step_camreset_restores_03ev_ok=1`, `initialize_restores_03ev_ok=1`）；证实切换 `0.3EV <-> 0.5EV` 同步重量化 **光圈（Aperture）、快门速度（`[Shutter Mode]=[Speed]`）、ISO 与曝光补偿（Exposure Comp.）** 全部 `4` 个曝光域（`exp_step_domains_requantized=4`, `exp_step_4domains_requantized_ok=1`），而 `Ver. 7.02` **`[Shutter Mode]=[Angle]`**（`5.6°..360°`：含 `5.6°`、`90°`、`172.8°`、`180°`、`360°` 五大基准锚点 `shutter_angle_5anchors_verified=5`）保持 **100% 恒定电影快门角度表豁免**（`shutter_angle_constant_table_immune_ok=1`, `shutter_angle_exposure_step_drift_events=0`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_writes=0`） | `13/13` 校验（早期曝光步进与快门角度 C 探针退出） | 跳过（曝光步进与快门角度 C 探针退出） | **`0`** / **`0`** / **`0`** | `6.23s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Lock Operation Parts]`、`MENU + Fn` 5s/3s 全机身锁防 `MENU + Delete` 2s 误格式化、`My Dial 1..3` 临时越权与 Big-6 渲染（`r52a`）
```text
FX6_R52_LOCK_OP_INIT fx3_lock_op_node_ok=1 lock_op_default_off_ok=1
  invalid_lock_op_rc=-22 lock_op_4modes_verified=4
  lock_op_survives_camreset_ok=1 lock_op_survives_netreset_ok=1
  initialize_restores_lock_op_off_ok=1 fn_hold_3s_toggle_ok=1
  mydial_1_3_temp_override_verified=3 mydial_release_relocks_ok=1
  menu_fn_5s_fullbody_lock_ok=1 shutter_exempt_ok=1
  menu_fn_3s_fullbody_release_ok=1 menu_delete_2s_blocked_rc=-1
  destructive_menu_delete_confusions=0 slot1_vault_format_events=0
  slot2_format_events=0 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r52_init_ok=1 verify_us=918522

FX6_R52_LOCK_OP_PARTS_BRIDGE lock_op_default_off_ok=1
  lock_op_4modes_verified=4 lock_op_survives_camreset_netreset_ok=1
  fn_hold_3s_toggle_ok=1 menu_fn_5s_lock_3s_release_ok=1
  destructive_menu_delete_confusions=0 slot1_vault_format_events=0
  mydial_1_3_temp_override_verified=3 lock_op_parts_ok=1
  emmc_write_count=0 r52_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `109` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Audio Out Timing]` vs `[Audio signals]` 跨重置分层与 `[Silent Mode]` 强制静音门禁（`r52b`）
```text
FX6_R52_AUDIO_TIMING_SIGNALS_GUARD audio_out_timing_default_live_ok=1
  audio_signals_default_on_all_ok=1 invalid_audio_timing_rc=-22
  invalid_audio_signals_rc=-22 audio_out_timing_2modes_verified=2
  audio_signals_3modes_verified=3 shutter_only_selectivity_ok=1
  audio_out_timing_camreset_restores_live_ok=1 audio_signals_survives_camreset_ok=1
  shooting_vs_setup_audio_reset_split_ok=1 initialize_restores_audio_defaults_ok=1
  sq_motion_audio_timing_lock_rc=-95 audio_rec_off_timing_lock_rc=-95
  audio_out_timing_sq_or_recoff_bypass_events=0 silent_mode_audio_signals_lock_rc=-16
  silent_mode_audio_signal_leak_events=0 silent_off_restores_audio_signals_ok=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r52b_ok=1 verify_us=821608
```

### 2.3 `[Exposure step]` 四域重量化 vs `Ver. 7.02` `[Shutter Angle]` 恒定角度表豁免及 `16/16 H0 == H3`（`r52c`）
```text
FX6_R52_EXP_STEP_SHUTTER_ANGLE exposure_step_default_03ev_ok=1
  invalid_exposure_step_rc=-22 exposure_step_2modes_verified=2
  exposure_step_camreset_restores_03ev_ok=1 initialize_restores_03ev_ok=1
  exp_step_domains_requantized=4 exp_step_4domains_requantized_ok=1
  shutter_angle_min_deg10=56 shutter_angle_max_deg10=3600
  shutter_angle_5anchors_verified=5 shutter_angle_constant_table_immune_ok=1
  shutter_angle_exposure_step_drift_events=0 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 cnflasha_writes=0 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0
  r52c_ok=1 verify_us=238514
```

---

## 3. `r52a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r52a` Alpha（`26.50 KiB` / `27,132 B`） | `r52a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r52a Big6 Alpha](assets/r52a-lock-op-parts-mydial-big6-schinese-alpha.png) | ![r52a Big6 Composited](assets/r52a-lock-op-parts-mydial-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）实体按键与拨轮机械测试台实测：无人值守备份期间同时按住 `MENU + Fn >= 5s` 锁定除快门键外全部实体按键/拨轮（及 `MENU + Fn >= 3s` 解除）、长按 `Fn` 约 `3s` 切换 `[Off]` / `[Multi-Slct Only]` / `[Dial/Wheel]` / `[Dial+Wheel+MSlct]`，以及锁定状态下按住/切换 `[My Dial 1..3]` 自定义键时的物理前后拨轮临时越权响应。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）3.5 mm 监听耳机音频延迟示波器与消音暗室测试台实测：`[Audio Out Timing]` 在 `[Live]`（防回声零延迟）与 `[Lip Sync]`（匹配画面帧延迟）下的模拟耳机输出相位差、`S&Q` 与 `[Audio Recording]=Off` 下的灰显不可选表现，以及 `[Audio signals]`（`[On: all]` / `[On: shutter only]` / `[Off: all]`）在 `[Silent Mode]=On` 下的机身压电/扬声器零声压输出。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）挂载原生 E 卡口镜头旋转机身前后拨轮与控制转盘实测：`[Exposure step]` 在 `[0.3EV]` 与 `[0.5EV]` 间切换时对光圈、快门速度（`[Shutter Mode]=[Speed]`）、ISO 与曝光补偿的物理档位重整化，以及切换至 `[Shutter Mode]=[Angle]` 时 `5.6°..360°`（`90°`、`172.8°`、`180°`、`360°`）电影快门角度步进完全不受 `[Exposure step]` 影响的真机表现。

---

## 5. 复现命令与洁净室合规

```bash
# Run 52A (75th Live Run): [Lock Operation Parts] MENU+Fn 5s Chord vs MENU+Delete 2s & My Dial 1..3 Override + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 52 --r52-mode lock_op_parts_chord_mydial_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round52-lock-op-parts-mydial-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r52-runs/r52a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r52a-lock-op-parts-mydial-big6-schinese \
  --export-png-dir reports/2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu/assets

# Run 52B: [Audio Out Timing] (Live/Lip Sync) vs [Audio signals] (3 Modes + Silent Mode Mute Lock)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 52 --r52-mode audio_out_timing_vs_audio_signals_guard --lang en \
  --run-id round52-audio-out-timing-vs-audio-signals-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r52-runs/r52b

# Run 52C: [Exposure step] (0.3EV/0.5EV) 4-Domain Re-Quantization vs Ver. 7.02 [Shutter Angle] (5.6..360 deg) Immunity + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 52 --r52-mode exposure_step_vs_shutter_angle_guard --lang en \
  --run-id round52-exposure-step-vs-shutter-angle-h0-h3 --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r52-runs/r52c

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在 `work/_tests/` 受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
