# Round 47（第 47 个里程碑 / Wave-33）：FX3 7.02 原厂内核真机准备预演 — `[Silent Mode Settings]`（`[Auto Pixel Mapping]` 靶向抑制、5 项禁用硬锁与无 `[Shutter When Pwr OFF]` 硬件边界）、`[Marker Display]` 15 比例跨重置持久化与 HDMI 零叠加隔离、以及 `[Flexible Exp. Mode]` / `[Auto Slow Shutter]` 重置分层

> **日期**：2026-11-15 | **轮次**：**Round 47 Live ARM64 QEMU Rehearsal (`47th Milestone` / Wave-33)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r47a` / `r47b` / `r47c`）测得；**物理实体 `ILME-FX3` 机身关机时机械快门声学静默复核、E 卡口镜头 `[Aperture Drive in AF]=[Silent Priority]` 光圈马达步进噪声测量、外接 Type-A HDMI 协议分析仪逐像素零构图标记（`0` `[Marker Display]` 叠加像素）核验、以及物理自定义键切换 `[Av/Tv/ISO Auto/Manual Switch]` 与 `[Camera Settings Reset]` 实机卡片测试尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 47 轮三项实机预演总览（`r47a` / `r47b` / `r47c`）

| 实跑场景 | Run ID | `r47_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **47A：`[Silent Mode Settings]` `[Auto Pixel Mapping]` 靶向抑制、5 项禁用硬锁与无 `[Shutter When Pwr OFF]` 校验 + Big-6 Home** | `round47-silent-autopixelmap-marker-big6` | `silent_autopixelmap_5locks_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[Silent Mode]=[On]` 自动强制将 `[Shutter Type]` 与 `[Shutter Type in Interval]` 锁入 `[Electronic Shutter]` 并将 `[Audio signals]` 锁入 `[Off]`（`auto_locks_electronic_and_audio_off_ok=1`；修改尝试全部被拦截 `rc=-16` `EBUSY`），同时完整禁用官方 5 项冲突功能：`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB` 与 `Anti-flicker Shoot.`（`silent_5disabled_verified=5`, `rc=-95` `EOPNOTSUPP`；`[Silent Mode]=[Off]` 时全部恢复 `normal_5funcs_unlocked_ok=1`）；核验 `[Target Function Settings]` 双靶标耦合：`[Aperture Drive in AF]`（`Standard` / `Silent Priority` / `Not Target`, `target_aperture_drive_af_ok=1`）与 `[Auto Pixel Mapping]`（设为 `[Off]` 时在静音模式下拦截关机机械快门暗场校准与 `cnflasha` 触碰：`target_autopixelmap_suppresses_pwroff_cal_ok=1`, `pwroff_mech_shutter_actuations=0`, `pwroff_cnflasha_touches=0`；设为 `[Not Target]` 时保留 `[Auto Pixel Mapping]=[On]` `autopixelmap_not_target_retains_ok=1`；退出静音模式后自动恢复 `silent_off_restores_autopixelmap_ok=1`）；验证 `ILME-FX3 Ver. 7.02` 硬件与菜单均无 α7S III / FX30 专属 `[Shutter When Pwr OFF]` 防尘快门幕选项（Setup 与 `[Target Function Settings]` 查询均返回 `rc=-2` `ENOENT`，关机传感器常开）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.5s` | [`r47a-silent-autopixelmap-marker-big6-schinese-composited.png`](assets/r47a-silent-autopixelmap-marker-big6-schinese-composited.png) |
| **47B：`[Marker Display]` 15 比例跨 `[Camera Settings Reset]` 持久化与本地 LCD 隔离（HDMI 零叠加）** | `round47-marker-15ratio-hdmi` | `marker_15ratio_persist_hdmi_isolation` | Native ARM64 构图标记与干净 HDMI 隔离探针实测：`[Marker Display]`（默认 `Off`）、`[Center Marker]`（`Off/On` `2` 档）、`[Aspect Marker]`（`Off` + Ver. 3.00+/7.02 完整 **`15` 种画幅比例** `9:16` / `4:5` / `1:1` / `4:3` / `13:9` / `14:9` / `15:9` / `16:9` / `17:9` / `1.66:1` / `1.85:1` / `1.91:1` / `2:1` / `2.35:1` / `2.39:1`，共 `16` 态，含 Ver. 3.00 新增 `16:9` `ver300_16_9_ratio_verified=1`）、`[Safety Zone]`（`Off/80%/90%` `3` 档）与 `[Guideframe]`（`Off/On` `2` 档）在执行 `[Camera Settings Reset]` 后跨全部 `15` 种画幅比例完整保留（`marker_15ratios_survive_cam_reset=15`, `marker_survives_cam_settings_reset_ok=1`），仅在全机 `[Initialize]` 时复位回全 `Off`（`initialize_resets_marker_all_off_ok=1`）；在 `[HDMI Info. Display]=[On]` 开启状态下遍历全部 `32` 种标记组合：机身本地 LCD 正常绘制构图框（`lcd_marker_overlay_px=16256`），而外接 HDMI 输出始终保持 **`0` 像素构图标记叠加**（`hdmi_marker_overlay_px=0`, `hdmi_clean_feed_combos_verified=32`），`p2:/setting` 只读不变（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期构图隔离 C 探针退出） | 跳过（构图隔离 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.6s` | — |
| **47C：`[Exposure Ctrl Type]`（`P/A/S/M Mode` vs `Flexible Exp. Mode`）、`Av/Tv/ISO` 与 `[Auto Slow Shutter]` 重置分层及 `16/16 H0 == H3`** | `round47-flexexp-reset-split` | `flexexp_avtviso_autoslowshutter_h0_h3` | Native ARM64 曝光控制体制与双层重置探针证实：`[Exposure Ctrl Type]` 支持在 `[P/A/S/M Mode]`（`Program Auto` / `Aperture Priority` / `Shutter Priority` / `Manual Exposure` `4` 子模式，`pasm_4submodes_verified=4`）与 `[Flexible Exp. Mode]` 两种体制间无损切换（`exp_ctrl_2types_verified=2`；`P/A/S/M` 下直接调用 `Av/Tv/ISO` Auto/Manual Switch 返回 `rc=-95` `EOPNOTSUPP`，`Flexible Exp. Mode` 下选 `P/A/S/M` 子模式返回 `rc=-16` `EBUSY`）；核验 `[Auto/Manual Swt. Set.]`（`[Av Auto/Manual Switch]`、`[Tv Auto/Manual Switch]`、`[ISO Auto/Manual Switch]` 默认全部 `Manual` `av_tv_iso_defaults_manual_ok=1`，遍历全部 `2^3 = 8` 种 `Auto/Manual` 组合 `av_tv_iso_8combos_verified=8`）与 `[Auto Slow Shutter]`（默认 `On` `auto_slow_shutter_default_on_ok=1`）；执行 `[Camera Settings Reset]` 后，`Av/Tv/ISO` 开关精准复位回 `Manual` 且 `[Auto Slow Shutter]` 复位回 `On`（`cam_reset_restores_av_tv_iso_manual_ok=1`, `cam_reset_restores_auto_slow_shutter_on_ok=1`），同时跨重置保留 `[Marker Display]` / `[Zebra Display]` / `[NTSC/PAL Selector]`（`cam_reset_preserves_marker_zebra_ntscpal_ok=1`），全机 `[Initialize]` 则同时复位两层配置（`initialize_resets_all_ok=1`）；同时通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期曝光分层 C 探针退出） | 跳过（曝光分层 C 探针退出） | **`0`** / **`0`** / **`0`** | `6.0s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Silent Mode Settings]`、`[Auto Pixel Mapping]` 靶向抑制与无 `[Shutter When Pwr OFF]` 硬件边界（`r47a`）
```text
FX6_R47_SILENT_AUTOPIXELMAP_INIT invalid_silent_reject_rc=-22 normal_5funcs_unlocked_ok=1
  auto_locks_electronic_and_audio_off_ok=1 silent_locks_shutter_type_rc=-16
  silent_locks_interval_shutter_rc=-16 silent_locks_audio_signals_rc=-16
  silent_5disabled_verified=5 dis_flash_rc=-95 dis_lenr_rc=-95 dis_efcs_rc=-95
  dis_bulb_rc=-95 dis_antiflicker_rc=-95 target_aperture_drive_af_ok=1
  autopixelmap_not_target_retains_ok=1 target_autopixelmap_suppresses_pwroff_cal_ok=1
  silent_off_restores_autopixelmap_ok=1 pwroff_mech_shutter_actuations=0
  pwroff_cnflasha_touches=0 valid_fx3_sensor_items_ok=3
  shutter_when_pwroff_setup_reject_rc=-2 shutter_when_pwroff_target_reject_rc=-2
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  appfw_present=1 shim_present=1 emmc_write_count=0 r47_init_ok=1 verify_us=909100

FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE silent_locks_shutter_type_rc=-16
  silent_locks_interval_shutter_rc=-16 silent_locks_audio_signals_rc=-16
  silent_5disabled_verified=5 target_aperture_drive_af_ok=1
  target_autopixelmap_suppresses_pwroff_cal_ok=1 autopixelmap_not_target_retains_ok=1
  pwroff_cnflasha_touches=0 shutter_when_pwroff_reject_rc=-2
  silent_autopixelmap_ok=1 emmc_write_count=0 r47_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `104` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Marker Display]` 15 比例跨 `[Camera Settings Reset]` 存活与 HDMI 干净流隔离（`r47b`）
```text
FX6_R47_MARKER_15RATIO_HDMI marker_defaults_off_ok=1 invalid_marker_disp_reject_rc=-22
  invalid_center_reject_rc=-22 invalid_aspect_reject_rc=-22 invalid_safety_reject_rc=-22
  invalid_guideframe_reject_rc=-22 center_marker_2modes_verified=2
  aspect_marker_off_plus_15ratios_verified=16 aspect_marker_15ratios_verified=15
  ver300_16_9_ratio_verified=1 safety_zone_3modes_verified=3 guideframe_2modes_verified=2
  marker_15ratios_survive_cam_reset=15 marker_survives_cam_settings_reset_ok=1
  initialize_resets_marker_all_off_ok=1 hdmi_info_display_on=1
  lcd_marker_overlay_px=16256 hdmi_marker_overlay_px=0
  hdmi_clean_feed_combos_verified=32 hdmi_info_on_zero_marker_ok=1
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1
  emmc_write_count=0 r47b_ok=1 verify_us=723491
```

### 2.3 `[Exposure Ctrl Type]`（`P/A/S/M Mode` vs `Flexible Exp. Mode`）、`Av/Tv/ISO` 与 `[Auto Slow Shutter]` 重置分层及 `16/16 H0 == H3`（`r47c`）
```text
FX6_R47_FLEXEXP_RESET_SPLIT av_tv_iso_defaults_manual_ok=1 auto_slow_shutter_default_on_ok=1
  invalid_exp_ctrl_reject_rc=-22 exp_ctrl_2types_verified=2 pasm_4submodes_verified=4
  flex_sw_in_pasm_reject_rc=-95 pasm_submode_in_flex_reject_rc=-16
  invalid_av_tv_iso_reject_rc=-22 invalid_auto_slow_shutter_reject_rc=-22
  av_tv_iso_8combos_verified=8 cam_reset_restores_av_tv_iso_manual_ok=1
  cam_reset_restores_auto_slow_shutter_on_ok=1 cam_reset_preserves_marker_zebra_ntscpal_ok=1
  initialize_resets_all_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  emmc_write_count=0 r47c_ok=1 verify_us=153838
```

---

## 3. `r47a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r47a` Alpha（`26.50 KiB` / `27,132 B`） | `r47a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r47a Big6 Alpha](assets/r47a-silent-autopixelmap-marker-big6-schinese-alpha.png) | ![r47a Big6 Composited](assets/r47a-silent-autopixelmap-marker-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）开启 `[Silent Mode]=[On]` 且将 `[Target Function Settings -> Auto Pixel Mapping]` 设为 `[Off]` 后执行真实拨杆关机，声学核验关机零机械快门闭合声、测量 E 卡口镜头 `[Aperture Drive in AF]=[Silent Priority]` 对焦光圈步进噪声、以及目视确认关机后无防尘机械快门幕遮挡传感器（`ILME-FX3` 无 `[Shutter When Pwr OFF]`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）同时开启 `[HDMI Info. Display]=[On]` 与 `[Marker Display]=[On]`（遍历 `9:16`..`2.39:1` 全部 `15` 种 `[Aspect Marker]`、`[Center Marker]`、`[Safety Zone]` `80%/90%` 与 `[Guideframe]`），外接 Type-A HDMI 采集卡逐帧比对机身翻转屏与 HDMI 信号，实测外接 HDMI 零构图标记像素叠加。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在 `[Flexible Exp. Mode]` 下通过机身自定义键切换 `[Av Auto/Manual Switch]`、`[Tv Auto/Manual Switch]`、`[ISO Auto/Manual Switch]` 为 `[Auto]` 并将 `[Auto Slow Shutter]` 改为 `[Off]`，执行 `[Camera Settings Reset]` 后实机确认三项曝光开关复位回 `[Manual]`、`[Auto Slow Shutter]` 复位回 `[On]` 且 `[Marker Display]` 画幅框继续保留。

---

## 5. 复现命令与洁净室合规

```bash
# Run 47A: Ver. 7.02 [Silent Mode Settings] [Auto Pixel Mapping] Target, 5-Lock Matrix & No [Shutter When Pwr OFF] + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 47 --r47-mode silent_autopixelmap_5locks_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round47-silent-autopixelmap-marker-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r47-runs/r47a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r47a-silent-autopixelmap-marker-big6-schinese \
  --export-png-dir reports/2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu/assets

# Run 47B: [Marker Display] 15-Ratio [Camera Settings Reset] Persistence & Local-Monitor-Only HDMI Clean-Feed Isolation
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 47 --r47-mode marker_15ratio_persist_hdmi_isolation --lang en --run-id round47-marker-15ratio-hdmi \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r47-runs/r47b

# Run 47C: [Exposure Ctrl Type] (P/A/S/M vs Flexible Exp. Mode), Av/Tv/ISO & [Auto Slow Shutter] Reset Split + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 47 --r47-mode flexexp_avtviso_autoslowshutter_h0_h3 --lang en --run-id round47-flexexp-reset-split \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r47-runs/r47c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
make verify-milestone-221
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
