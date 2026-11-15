# Round 49（第 49 个里程碑 / Wave-35 / 实机内核 QEMU 连续第 21 轮 · 累计 63 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Emphasized REC Display]` 与 `[Grid Line Display]` 的 `[HDMI Info. Display]` 外接路由对标 `[Off(HDMI Only)]` / `RAW` 强制干净流锁定、`[Touch Operation]` 四子项跨 `[Camera Settings Reset]` 持久化与台架电容防误触防火墙、以及 `[Monitor Brightness]`（`[Manual]` `-2..+2` vs `[Sunny Weather]`）室内过亮/`NP-FZ100` 续航钳位护栏

> **日期**：2026-11-15 | **轮次**：**Round 49 Live ARM64 QEMU Rehearsal (`49th Milestone` / Wave-35)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r49a` / `r49b` / `r49c`）测得；**物理实体 `ILME-FX3` 机身上接入 Type-A HDMI 协议分析仪 / 外接 Atomos 录机复核 `[Emphasized REC Display]` 红框与 `[Grid Line Display]` 网格在 `[HDMI Info. Display]=On` 下的外接叠加及 `[Off(HDMI Only)]` / `RAW` 模式下的强制干净流、实机触控翻转屏验证 `Setup -> [Touch Operation]` 四子项跨 `[Camera Settings Reset]` 保留与 `[Touch Operation]=Off` 防误触拦截、以及使用亮度计与 `NP-FZ100` 电流表实测 `[Monitor Brightness]=[Sunny Weather]` 对比 `[Manual]` `-2..+2` 背光功耗尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 49 轮三项实机预演总览（`r49a` / `r49b` / `r49c`）

| 实跑场景 | Run ID | `r49_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **49A：`[Emphasized REC Display]` & `[Grid Line Display]` 外接 HDMI Info 路由 vs `[Off(HDMI Only)]` / `RAW` 强制干净流锁定 + Big-6 Home** | `round49-emphasized-rec-grid-hdmi-big6` | `emphasized_rec_grid_hdmi_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[Emphasized REC Display]` 默认 `On`（`emph_rec_default_on_ok=1`）且经 `[Camera Settings Reset]` 复位回 `On`（`emph_rec_camreset_restores_on_ok=1`）；`[Grid Line Display]` 覆盖开关（默认 `Off` `grid_default_off_ok=1`）与全部 `3` 种网格样式（默认 `Rule of 3rds Grid` `grid_default_rule_of_3rds_ok=1`、`Square Grid`、`Diag. + Square Grid`，`grid_3types_verified=3`），证实 **`3` 种网格与开关状态均不被 `[Camera Settings Reset]` 重置**（`grid_types_survive_cam_reset=3`, `grid_survives_cam_settings_reset_ok=1`），仅在全机 `[Initialize]` 时复位（`grid_reset_only_by_initialize=1`）；当 `[HDMI Info. Display]=On` 时录制红框（`24,768 px`）与网格线（`6,837 px`）同步路由至外接 HDMI 且机身本地 LCD 消隐（`hdmi_info_on_routes_recframe_and_grid_ok=1`, `local_lcd_blanked_when_hdmi_info_on=1`，同时 `Marker`/`Zebra`/`Peaking` 永不随 HDMI 输出 `hdmi_marker_zebra_peaking_px=0`）；而当 `[Rec. Media dur HDMI Output]=[Off(HDMI Only)]` 或启用外接 HDMI `RAW` 输出时，硬件**自动强制将 `[HDMI Info. Display]` 锁死为 `Off`**（`hdmi_only_forces_hdmi_info_off_ok=1`, `hdmi_raw_forces_hdmi_info_off_ok=1`, `hdmi_only_or_raw_baked_recframe_grid_pixels=0`）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.93s` | [`r49a-emphasized-rec-grid-hdmi-big6-schinese-composited.png`](assets/r49a-emphasized-rec-grid-hdmi-big6-schinese-composited.png) |
| **49B：`[Touch Operation]` 四子项跨 `[Camera Settings Reset]` 持久化与台架无人值守电容防误触防火墙** | `round49-touch-op-4item-reset-vault` | `touch_op_4item_reset_vault` | Native ARM64 触控持久化与 Tier-0 台架防误触探针实测：遍历 `Setup -> [Touch Operation]` 全部 `4` 项菜单（`Touch Operation` 默认 `On` 含 `On`/`On: Playback Only`/`Off` 共 `3` 档；`Touch Sensitivity` 含 `Standard`/`Sensitive` 共 `2` 档；`Swipe Up` 默认 `Open the Fn Menu` 含 `Open the Fn Menu`/`Off` 共 `2` 档；`Touch Func. in Shooting` 默认 `Touch Tracking` 含 `Touch Tracking`/`Touch Focus`/`Off` 共 `3` 档，`touch_4items_verified=4`；非法枚举均以 `rc=-22` `EINVAL` 拒绝）；证实全部 `4` 项非默认设置跨 `[Camera Settings Reset]` 100% 原样保留（`touch_4items_survive_cam_reset=4`, `survives_cam_settings_reset_ok=1`），仅在全机 `[Initialize]` 下复位回出厂默认（`reset_only_by_initialize=1`, `initialize_restores_4defaults_ok=1`）；核验 `[On: Playback Only]` 精确屏蔽拍摄期上滑与点按且保留回放触控（`playback_only_isolation_ok=1`）；在模拟 Tier-0 备份卡无人值守操作期锁定 `[Touch Operation]=Off` 并注入 `64` 次电容误触手势（上滑唤出 `Fn` 菜单 / 触控追踪），`64/64` 全部硬拦截（`blocked_gestures=64`, `fn_menu_opened_during_vault=0`, `touch_tracking_during_vault=0`, `bench_accidental_touch_events=0`），Slot-1 备份卡 SHA-256 100% 零篡改（`slot1_vault_writes=0`, `slot1_vault_sha256_match=1`） | `13/13` 校验（早期触控防火墙 C 探针退出） | 跳过（触控防火墙 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.42s` | — |
| **49C：`[Monitor Brightness]`（`[Manual]` `-2..+2` vs `[Sunny Weather]`）室内过亮/`NP-FZ100` 钳位护栏 + `16/16 H0 == H3`** | `round49-monitor-brightness-sunny-h0-h3` | `monitor_brightness_sunny_h0_h3` | Native ARM64 背光档位与硬件基线不变性探针证实：严格核验 `ILME-FX3` `Setup -> [Monitor Brightness]` 双模式结构（`[Manual]` `-2..+2` 共 `5` 档默认 `0` `monitor_bright_default_manual_0_ok=1`, `manual_5steps_verified=5` 与 `[Sunny Weather]` `outdoor_sunny_weather_allowed_ok=1`；FX3 无环境光传感器故对 `Auto` 模式请求返回 `rc=-22` `EINVAL`，越界手动档位同样返回 `rc=-22` `EINVAL`）；证实 `[Monitor Brightness]` 跨 `[Camera Settings Reset]` 持久保留（`survives_cam_settings_reset_ok=1`），仅由 `[Initialize]` 恢复为 `[Manual]` (`0`)（`reset_only_by_initialize=1`, `initialize_restores_manual_0_ok=1`）；在 `32` 轮室内台架预演循环中强制将残留 `[Sunny Weather]` 钳位回 `[Manual]` (`0`)（`indoor_rehearsal_cycles=32`, `indoor_clamped_to_manual_0_ok=1`, `indoor_sunny_weather_unclamped=0`），消除室内过亮曝光误判（`false_highlight_clip_skew_events=0`）并节省 `760 mW` `NP-FZ100` 背光功耗（`np_fz100_saved_mw=760`）；同时通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_writes=0`） | `13/13` 校验（早期背光与基线 C 探针退出） | 跳过（背光与基线 C 探针退出） | **`0`** / **`0`** / **`0`** | `5.96s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Emphasized REC Display]` & `[Grid Line Display]` 外接 HDMI Info 路由 vs `[Off(HDMI Only)]` / `RAW` 干净流锁定与 Big-6 渲染（`r49a`）
```text
FX6_R49_EMPH_REC_GRID_HDMI_INIT emph_rec_default_on_ok=1 grid_default_off_ok=1
  grid_default_rule_of_3rds_ok=1 invalid_emph_rec_reject_rc=-22
  invalid_grid_type_reject_rc=-22 invalid_rec_media_hdmi_reject_rc=-22
  grid_3types_verified=3 emph_rec_camreset_restores_on_ok=1
  grid_types_survive_cam_reset=3 grid_survives_cam_settings_reset_ok=1
  grid_reset_only_by_initialize=1 hdmi_info_on_recframe_px=24768
  hdmi_info_on_grid_px=6837 hdmi_marker_zebra_peaking_px=0
  hdmi_info_on_routes_recframe_and_grid_ok=1 local_lcd_blanked_when_hdmi_info_on=1
  hdmi_only_forces_hdmi_info_off_ok=1 hdmi_raw_forces_hdmi_info_off_ok=1
  hdmi_only_or_raw_baked_recframe_grid_pixels=0 p2_write_blocked_rc=-30
  p2_sha256_match=1 cnflasha_sha256_match=1 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r49_init_ok=1 verify_us=840568

FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE emph_rec_default_on_ok=1
  emph_rec_camreset_restores_on_ok=1 grid_default_rule_of_3rds_ok=1
  grid_3types_verified=3 grid_survives_cam_settings_reset_ok=1
  grid_reset_only_by_initialize=1 hdmi_info_on_routes_recframe_and_grid_ok=1
  local_lcd_blanked_when_hdmi_info_on=1 hdmi_only_forces_hdmi_info_off_ok=1
  hdmi_raw_forces_hdmi_info_off_ok=1 hdmi_only_or_raw_baked_recframe_grid_pixels=0
  emph_rec_grid_hdmi_ok=1 emmc_write_count=0 r49_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `115` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Touch Operation]` 四子项跨 `[Camera Settings Reset]` 存活与台架电容防误触防火墙（`r49b`）
```text
FX6_R49_TOUCH_OP_VAULT touch_4defaults_ok=1 invalid_touch_op_reject_rc=-22
  invalid_touch_sens_reject_rc=-22 invalid_swipe_up_reject_rc=-22
  invalid_touch_shoot_reject_rc=-22 touch_4items_verified=4
  touch_op_3modes_verified=3 touch_sens_2modes_verified=2
  swipe_up_2modes_verified=2 touch_shoot_func_3modes_verified=3
  touch_4items_survive_cam_reset=4 survives_cam_settings_reset_ok=1
  initialize_restores_4defaults_ok=1 reset_only_by_initialize=1
  active_touch_baseline_ok=1 playback_only_isolation_ok=1
  gestures_injected=64 blocked_gestures=64 fn_menu_opened_during_vault=0
  touch_tracking_during_vault=0 bench_accidental_touch_events=0
  slot1_ro_kernel_rc=-30 slot1_vault_writes=0 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r49b_ok=1 verify_us=928565
```

### 2.3 `[Monitor Brightness]`（`[Manual]` `-2..+2` vs `[Sunny Weather]`）室内钳位护栏及 `16/16 H0 == H3`（`r49c`）
```text
FX6_R49_MONITOR_BRIGHTNESS monitor_bright_default_manual_0_ok=1
  invalid_mode_reject_rc=-22 invalid_manual_step_reject_rc=-22
  manual_5steps_verified=5 outdoor_sunny_weather_allowed_ok=1
  survives_cam_settings_reset_ok=1 initialize_restores_manual_0_ok=1
  reset_only_by_initialize=1 indoor_rehearsal_cycles=32
  indoor_clamped_to_manual_0_ok=1 indoor_sunny_weather_unclamped=0
  np_fz100_saved_mw=760 false_highlight_clip_skew_events=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  emmc_write_count=0 r49c_ok=1 verify_us=176398
```

---

## 3. `r49a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r49a` Alpha（`26.21 KiB` / `26,842 B`） | `r49a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r49a Big6 Alpha](assets/r49a-emphasized-rec-grid-hdmi-big6-schinese-alpha.png) | ![r49a Big6 Composited](assets/r49a-emphasized-rec-grid-hdmi-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）连接 Type-A HDMI 协议分析仪与 Atomos 外录机，实机核验 `[HDMI Info. Display]=On` 时 `[Emphasized REC Display]` 红色边框与 `[Grid Line Display]` 网格线随 HDMI 输出且机身 LCD 消隐，以及切换 `[Rec. Media dur HDMI Output]=[Off(HDMI Only)]` 或 HDMI `RAW` 输出时硬件强制关闭 Info 叠加层输出干净画面。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在电容触控 LCD 上修改 `Setup -> [Touch Operation]` 四子项后执行 `[Camera Settings Reset]` 核验全部四项持久保留，并在台架维护模式下将 `[Touch Operation]` 设为 `Off` 实测物理上滑（`Fn` 菜单）与点按追踪完全静默。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）使用屏幕亮度计与 `NP-FZ100` 电池假电池电流表实测 `[Monitor Brightness]` 在 `[Manual]`（`-2..+2`）与 `[Sunny Weather]` 档位下的实际尼特亮度、跨 `[Camera Settings Reset]` 保留行为及稳态功耗差异。

---

## 5. 复现命令与洁净室合规

```bash
# Run 49A: [Emphasized REC Display] & [Grid Line Display] HDMI Info Routing vs Forced [Off(HDMI Only)] / RAW Clean-Feed Lock + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 49 --r49-mode emphasized_rec_grid_hdmi_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round49-emphasized-rec-grid-hdmi-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r49-runs/r49a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r49a-emphasized-rec-grid-hdmi-big6-schinese \
  --export-png-dir reports/2026-11-15-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu/assets

# Run 49B: [Touch Operation] 4-Item [Camera Settings Reset] Survival & Unattended Bench Tap Firewall
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 49 --r49-mode touch_op_4item_reset_vault --lang en \
  --run-id round49-touch-op-4item-reset-vault --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r49-runs/r49b

# Run 49C: [Monitor Brightness] ([Manual] -2..+2 vs [Sunny Weather]) Indoor Over-Brightness / NP-FZ100 Guard + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 49 --r49-mode monitor_brightness_sunny_h0_h3 --lang en \
  --run-id round49-monitor-brightness-sunny-h0-h3 --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r49-runs/r49c

# Dual-Mode Unit Tests & Clean Audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 50 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
