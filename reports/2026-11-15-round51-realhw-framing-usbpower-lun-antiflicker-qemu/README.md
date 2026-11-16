# Round 51（Wave-37 / `R28..R51` 实机内核 QEMU 第 24 轮 · 累计 72 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Framing Settings]`（`Recording/Streaming=Full` vs `HDMI=Crop` 非对称默认、拒绝 ZV-E1 `[Autoframing Settings]` 混淆及 `HDMI RAW Output` 锁定）、`[USB Power Supply]` 强制 `NP-FZ100` 电池 + `USB Type-C` 独占与 `[USB LUN Setting]`（`Multi`/`Single`）跨 `[Camera Settings Reset]` 存活、以及 `[Anti-flicker Shoot.]` 机械快门拍照专属与无 `[Var. Shutter]` 门禁

> **日期**：2026-11-15 | **轮次**：**Round 51 Live ARM64 QEMU Rehearsal (Wave-37)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r51a` / `r51b` / `r51c`）测得；**物理实体 `ILME-FX3` 机身上同时对比机内卡槽录制（`[Recording/Streaming]=Full`）与外接 HDMI 监视器输出（`[HDMI]=Crop`）及 Atomos Ninja V+ `HDMI RAW Output` 锁定、使用 USB-PD 功率计与双卡槽大容量存储枚举台架实测 `USB Type-C` + `NP-FZ100` / `DC-C1` 电流曲线对比 `Multi/Micro USB` 零供电与老旧宿主 `[USB LUN Setting]=[Single]` 兼容回退、以及在 `100 Hz`/`120 Hz` 频闪灯箱下实测机械快门静态照片 `[Anti-flicker Shoot.]=On` 对齐尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 51 轮（Wave-37）三项实机预演总览（`r51a` / `r51b` / `r51c`）

| 实跑场景 | Run ID | `r51_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **51A：`[Framing Settings]` `Full`/`Crop` 非对称默认、拒绝 ZV-E1 `[Autoframing Settings]`、`HDMI RAW` 冲突锁 + Big-6 Home** | `round51-framing-crop-hdmi-big6` | `framing_settings_crop_hdmi_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Shooting -> [Image Stabilization] -> [Framing Stabilizer] -> [Framing Settings]` 真实树节点（`fx3_framing_node_ok=1`），严格以 `-ENOENT`（`-2`）拒绝将 `ZV-E1` 专属 `[Autoframing Settings]` 混淆进 `ILME-FX3`（`zve1_autoframing_conflation_events=0`）；核验非对称出厂默认（`[Framing]=Off`、`[Recording/Streaming]=Full` 机内全幅 vs `[HDMI]=Crop` 外监构图裁切，`asymmetric_full_rec_crop_hdmi_ok=1`）及全部 `4` 种 `Full/Crop` 路由组合（`framing_4routing_combos_verified=4`；非法枚举返回 `rc=-22` `EINVAL`），且经 `[Camera Settings Reset]` 与 `[Initialize]` 均恢复出厂默认（`framing_camreset_restores_defaults_ok=1`, `initialize_restores_defaults_ok=1`）；开启 `HDMI RAW Output` 时自动钳位关闭并以 `-EBUSY`（`-16`）锁定 `[Framing Settings]`（`raw_enable_clamps_framing_off_ok=1`, `hdmi_raw_framing_lock_rc=-16`, `framing_raw_conflict_events=0`）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.33s` | [`r51a-framing-crop-hdmi-big6-schinese-composited.png`](assets/r51a-framing-crop-hdmi-big6-schinese-composited.png) |
| **51B：`[USB Power Supply]` 强制 `NP-FZ100` 电池 + `USB Type-C` 独占与 `[USB LUN Setting]` 跨重置存活护栏** | `round51-usb-power-npfz100-lun-guard` | `usb_power_npfz100_and_usb_lun_guard` | Native ARM64 USB 供电与大容量存储枚举安全探针实测：核验 `[USB Power Supply]` 默认 `On`（`usb_power_default_on_ok=1`，`On`/`Off` 双档 `usb_power_2modes_verified=2`）与 `[USB LUN Setting]` 默认 `Multi`（`usb_lun_default_multi_ok=1`：`Multi=2 LUNs` Slot 1+2 vs `Single=1 LUN` 老旧宿主兼容回退 `usb_lun_2modes_verified=2`；非法枚举均以 `rc=-22` `EINVAL` 拒绝）；证实 `[USB Power Supply]` **必须插入充好电的 `NP-FZ100` 电池或 `DC-C1` 假电池耦合器**——空电池仓上电以 `-ENODEV`（`-19`）拒绝，无保护拔电池立即掉电（`raw_pull_causes_immediate_poweroff_ok=1`），并在 `32` 轮运行期护栏测试中以 `-EBUSY`（`-16`）拦截带电拔除 `NP-FZ100`（`unbuffered_battery_pull_events=0`）；证实仅支持 **USB Type-C** 口供电而 **Multi/Micro USB** 端子以 `-EOPNOTSUPP`（`-95`）硬拒绝（`multi_micro_usb_power_bypass_events=0`）；证实两项 Setup 层 USB 设置均跨 `[Camera Settings Reset]` 存活且仅由 `[Initialize]` 恢复默认（`usb_power_survives_camreset_ok=1`, `usb_lun_survives_camreset_ok=1`, `initialize_restores_usb_defaults_ok=1`, `physical_usb_packets_emitted=0`） | `13/13` 校验（早期 USB 供电与 LUN C 探针退出） | 跳过（USB 供电与 LUN C 探针退出） | **`0`** / **`0`** / **`0`** | `7.46s` | — |
| **51C：`[Anti-flicker Shoot.]` 机械快门静态照片专属、无 `[Var. Shutter]` 门禁 + `16/16 H0 == H3`** | `round51-antiflicker-no-var-shutter-h0-h3` | `antiflicker_mech_still_no_var_shutter_guard` | Native ARM64 快门频闪门禁与硬件基线不变性探针证实：核验 `ILME-FX3`（`ilc/2210`）`[Anti-flicker Shoot.]` 默认 `Off`（`antiflicker_default_off_ok=1`）及 `Off`/`On` 双档、`100Hz`/`120Hz` 双频闪检测频率（`antiflicker_2modes_verified=2`, `flicker_100hz_120hz_verified=2`，经 `[Camera Settings Reset]` 与 `[Initialize]` 恢复 `Off`）；严格限定仅在**机械快门静态照片模式**生效（`mech_still_antiflicker_active_ok=1`），而在 **Movie 视频模式**、**`S&Q` 升格/降格模式**及 **`[Silent Mode]=On` 电子快门**下均以 `-EOPNOTSUPP`（`-95`）硬锁定（`movie_mode_lock_rc=-95`, `sq_mode_lock_rc=-95`, `silent_eshutter_lock_rc=-95`, `antiflicker_movie_or_eshutter_bypass_events=0`）；跨机型严格证实 `ILME-FX3` **不存在** `FX30`/`FX2`/`ZV-E1`/`α7 IV`/`FX6` 的高分辨率电子快门微调菜单 `[Var. Shutter]` / `ECS`（查找返回 `-ENOENT` `-2`，`fx3_has_var_shutter=0`, `false_var_shutter_events=0`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_writes=0`） | `13/13` 校验（早期防闪烁与无可变快门 C 探针退出） | 跳过（防闪烁与无可变快门 C 探针退出） | **`0`** / **`0`** / **`0`** | `5.74s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Framing Settings]` `Full`/`Crop` 非对称默认、拒绝 ZV-E1 `[Autoframing Settings]` 与 Big-6 渲染（`r51a`）
```text
FX6_R51_FRAMING_INIT fx3_framing_node_ok=1 zve1_autoframing_reject_rc=-2
  zve1_autoframing_conflation_events=0 framing_default_off_ok=1
  invalid_framing_enum_reject_rc=-22 asymmetric_full_rec_crop_hdmi_ok=1
  framing_4routing_combos_verified=4 framing_camreset_restores_defaults_ok=1
  initialize_restores_defaults_ok=1 raw_enable_clamps_framing_off_ok=1
  hdmi_raw_framing_lock_rc=-16 framing_raw_conflict_events=0
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r51_init_ok=1 verify_us=850878

FX6_R51_FRAMING_BRIDGE framing_default_off_ok=1 rec_stream_default_full_ok=1
  hdmi_default_crop_ok=1 asymmetric_full_rec_crop_hdmi_ok=1
  framing_4routing_combos_verified=4 framing_camreset_restores_defaults_ok=1
  zve1_autoframing_conflation_events=0 hdmi_raw_framing_lock_rc=-16
  framing_raw_conflict_events=0 framing_crop_hdmi_ok=1 emmc_write_count=0
  r51_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `113` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[USB Power Supply]` 强制 `NP-FZ100` 电池 + `USB Type-C` 独占与 `[USB LUN Setting]` 存活护栏（`r51b`）
```text
FX6_R51_USB_POWER_LUN_GUARD usb_power_default_on_ok=1 usb_lun_default_multi_ok=1
  invalid_usb_power_rc=-22 invalid_usb_lun_rc=-22 usb_power_2modes_verified=2
  usb_lun_2modes_verified=2 lun_multi_exposed_units=2 lun_single_exposed_units=1
  usb_typec_pd_power_ok=1 dcc1_coupler_supported_ok=1
  poweron_without_battery_reject_rc=-19 raw_pull_causes_immediate_poweroff_ok=1
  live_battery_pull_guard_rc=-16 unbuffered_battery_pull_events=0
  multi_micro_usb_power_reject_rc=-95 multi_micro_usb_power_bypass_events=0
  usb_power_survives_camreset_ok=1 usb_lun_survives_camreset_ok=1
  shooting_tier_reset_split_ok=1 initialize_restores_usb_defaults_ok=1
  physical_usb_packets_emitted=0 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r51b_ok=1 verify_us=830706
```

### 2.3 `[Anti-flicker Shoot.]` 机械快门拍照专属、无 `[Var. Shutter]` 门禁及 `16/16 H0 == H3`（`r51c`）
```text
FX6_R51_ANTIFLICKER_NO_VAR antiflicker_default_off_ok=1 invalid_antiflicker_rc=-22
  antiflicker_2modes_verified=2 flicker_100hz_120hz_verified=2
  mech_still_antiflicker_active_ok=1 antiflicker_camreset_restores_off_ok=1
  initialize_restores_off_ok=1 movie_mode_lock_rc=-95 sq_mode_lock_rc=-95
  silent_eshutter_lock_rc=-95 antiflicker_movie_or_eshutter_bypass_events=0
  var_shutter_lookup_rc=-2 fx6_ecs_lookup_rc=-2 fx3_has_var_shutter=0
  false_var_shutter_events=0 cross_model_var_shutter_contrast_ok=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  emmc_write_count=0 r51c_ok=1 verify_us=240386
```

---

## 3. `r51a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r51a` Alpha（`26.50 KiB` / `27,132 B`） | `r51a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r51a Big6 Alpha](assets/r51a-framing-crop-hdmi-big6-schinese-alpha.png) | ![r51a Big6 Composited](assets/r51a-framing-crop-hdmi-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学运动测试台同时对比机内 CFexpress Type A / SDXC 录制（`[Recording/Streaming]=Full`）与外接 HDMI 采集卡输出（`[HDMI]=Crop`）在 `[Framing Stabilizer] -> [Framing Settings]` 下的实际画幅裁切，以及连接 Atomos Ninja V+ 开启 `HDMI RAW Output` 时的物理锁定行为。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）接入 USB-PD 协议功率计与老旧单 LUN 读卡宿主设备，实测插入 `NP-FZ100` 电池或 `DC-C1` 假电池耦合器时 `USB Type-C` 供电电流曲线、`Multi/Micro USB` 端子零供电隔离，以及 `[USB LUN Setting]` 在 `[Multi]`（双盘符）与 `[Single]`（单盘符兼容回退）下的物理 USB Mass Storage 枚举表现。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在 `100 Hz` / `120 Hz` 受控人造光源频闪暗室中，对比机械快门静态照片开启 `[Anti-flicker Shoot.]=On` 前后的条纹抑制效果，以及在 Movie、`S&Q` 与 `[Silent Mode]=On` 电子快门下仅能手动设定 `1/50`、`1/60`、`1/100`、`1/120` 快门速度的物理表现。

---

## 5. 复现命令与洁净室合规

```bash
# Run 51A: [Framing Settings] Full/Crop Split, No ZV-E1 Autoframing & HDMI RAW Lockout + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 51 --r51-mode framing_settings_crop_hdmi_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round51-framing-crop-hdmi-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r51-runs/r51a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r51a-framing-crop-hdmi-big6-schinese \
  --export-png-dir reports/2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/assets

# Run 51B: [USB Power Supply] Mandatory NP-FZ100 + USB Type-C Exclusivity & [USB LUN Setting] Multi/Single Survival Guard
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 51 --r51-mode usb_power_npfz100_and_usb_lun_guard --lang en \
  --run-id round51-usb-power-npfz100-lun-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r51-runs/r51b

# Run 51C: [Anti-flicker Shoot.] Mechanical-Shutter Still-Only, No [Var. Shutter] Guard + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 51 --r51-mode antiflicker_mech_still_no_var_shutter_guard --lang en \
  --run-id round51-antiflicker-no-var-shutter-h0-h3 --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r51-runs/r51c

# Dual-Mode Unit Tests & Clean Audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
