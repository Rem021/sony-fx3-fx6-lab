# Round 41：FX3 7.02 原厂内核真机准备预演 — `[De-Squeeze Display]`（`1.6x=1.65x` 与 4 项硬锁死 / HDMI RAW 旁路）、外置 `M&C Focus Map`（`>=150fps` 截断 / `1..6fps` 放行）与双卡 `[Simult. + Auto Switch]` / `[Shockless WB]`

> **日期**：2026-11-15 | **轮次**：**Round 41 Live ARM64 QEMU Rehearsal** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r41a` / `r41b` / `r41c`）测得；**物理实体 `ILME-FX3` 机身挂载变形宽银幕镜头切换 `[De-Squeeze Display]`（`1.3x` / `2.0x` / `1.5x` / `1.6x=1.65x`）与 HDMI 外录机采集、实体手机/平板运行 `Monitor & Control`（`Ver. 2.1.0+`）Wi-Fi/USB 订阅 `Focus Map` 景深图、以及实体双槽 `SDXC` / `CFexpress Type A` 存储卡写满单卡续航热拔插与实景光源切换 `[Shockless WB]` 尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 41 轮三项实机预演总览（`r41a` / `r41b` / `r41c`）

| 实跑场景 | Run ID | `r41_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **41A：`[De-Squeeze Display]` 五档比例状态机（`Off/1.3x/2.0x/1.5x/1.6x=1.65x`）+ 4 项相机硬锁死 + HDMI RAW / 纯净 HDMI 自动旁路 + Big-6 Home** | `r41a-desqueeze-165x-big6-schinese` | `desqueeze_165x_4locks_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接验证全部 5 档 `[De-Squeeze Display]` 比例（`Off=100`、`1.3x=130`、`2.0x=200`、`1.5x=150`、以及 `1.6x` 实套 **`1.65x`（`165`）CinemaScope `2.39:1`** 水平反挤压倍率，`ratios_verified=5`；非法档位拒止 `rc=-22` `EINVAL`）；证实开启非 `Off` 档位时硬锁死 4 项核心设置（`[Focus Mode]=MF`、`[Focus Area]=Wide`、`[SteadyShot]=Off`、`[Face Priority in Multi Metering]=Off`，篡改均拒止 `rc=-16` `EBUSY`，切回 `Off` 立即解锁 `unlocked_when_off_ok=1`）；证实在 `[RAW Output]=On`、`[Rec. Media dur HDMI Output]=Off(HDMI Only)`（同时强制 `[HDMI Info. Display]=Off`）、`[Log Shooting]=Off`、`[Remote Shooting]` 与拍照模式下自动回退为 `1.00x` 原始比例，并渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `73.13s` | [`r41a-desqueeze-165x-big6-schinese-composited.png`](assets/r41a-desqueeze-165x-big6-schinese-composited.png) |
| **41B：仅限外置 `Monitor & Control` 的 `[Focus Map]`（机身无菜单开关）与 `>=150fps` S&Q 截断（`200/240fps` 阻断 vs `1..6fps` 放行）** | `r41b-external-focusmap-150fps` | `external_focusmap_150fps_cutoff` | Native ARM64 `Focus Map` 门禁验证 `ILME-FX3`（`7.02`）机身本地菜单与本地 LCD 叠加层硬拒 `[Focus Map]` 开关（`rc=-95` `EOPNOTSUPP`, `local_lcd_overlay_draws=0`）；在外置 `Monitor & Control` 连接且搭载原生 E 卡口 PDAF 镜头时，对 `<150fps` 全帧率开放 PDAF 景深流（含 `1fps`、`6fps`、`24fps`、`60fps`、`120fps`、`149fps` 全部 `rc=0`——精确区分 FX3 放行 `<=6fps` S&Q `fx3_6fps_allowed=1` 与 FX6 在 `<=6fps` 阻断 `fx6_ref_6fps_reject_rc=-22` 的机型差异）；硬拒 `>=150fps` 高帧率（`150fps`/`200fps`/`240fps` 全部 `rc=-22` `EINVAL`, `sq_200fps_stream_active=0`, `sq_240fps_stream_active=0`）、转接环/非 PDAF/无镜头（`rc=-19` `ENODEV`）与回放模式（`rc=-16` `EBUSY`），且 `p2:/setting` 保持只读（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期 `Focus Map` 校验退出） | 跳过（`Focus Map` C 探针退出） | **`0`** / **`0`** / **`0`** | `6.76s` | — |
| **41C：双卡 `[Simult. Recording]` + `[Auto Switch Media]`（`Ver. 2.0+` 单卡无缝续录 vs `Off` 严格双份停机）与 `[Shockless WB]` 色温/微调零帧旁路 + `16/16 H0 == H3`** | `r41c-simult-shocklesswb` | `simult_autoswitch_shocklesswb` | Native ARM64 双卡与白平衡探针证实：`[Simult. Recording]` + `[Auto Switch Media]=On` 在 Slot 1 写满时自动无缝切至 Slot 2 单卡续录（`rc=0`, `single_slot_cont_active=1`, `cont_slot_mask=0x2`, `cont_dropped_frames=0`），热替换新卡后自动恢复双卡同录（`rc=0`, `resumed_slot_mask=0x3`, `dual_slot_resumed=1`；双卡皆满才返回 `-28` `ENOSPC`），而 `[Auto Switch Media]=Off` 在任一卡满时立即返回 `-28` `ENOSPC` 停机以严保双份冗余（`autoswitch_off_halted=1`）；验证 `[Shockless WB]`（`Off/1/2/3`）在 `24p..240fps` 全部 `6` 档帧率下平滑缩放预设切换帧数（`24p`: `12/24/48` 帧；`240fps` `3(Slow)`: `480` 帧），而手动调节 `[C.Temp./Filter]` Kelvin 色温与 `A–B / G–M` 色彩微调网格均以 **`0` 过渡帧**立即生效（`immediate_bypass=1`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期双卡/WB 校验退出） | 跳过（双卡/WB C 探针退出） | **`0`** / **`0`** / **`0`** | `5.07s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[De-Squeeze Display]` 五档比例（`1.6x=1.65x`）、4 项硬锁死与 HDMI RAW / 纯净 HDMI 自动旁路（`r41a`）
```text
FX6_R41_DESQUEEZE_165X_INIT ratios_verified=5 off_centi=100 r13x_centi=130 r20x_centi=200
  r15x_centi=150 r16x_actual_centi=165 cinemascope_aspect=2.39:1 invalid_ratio_reject_rc=-22
  focus_mode_locked_mf=1 focus_area_locked_wide=1 steadyshot_locked_off=1 face_priority_metering_locked_off=1
  af_mut_reject_rc=-16 area_mut_reject_rc=-16 ibis_mut_reject_rc=-16 face_mut_reject_rc=-16
  hard_locks_enforced=4 unlocked_when_off_ok=1
  raw_output_on_suppressed=1 hdmi_only_suppressed=1 hdmi_only_forces_info_off=1
  log_shooting_off_suppressed=1 remote_shooting_suppressed=1 photo_mode_suppressed=1
  appfw_present=1 shim_present=1 emmc_write_count=0 r41_init_ok=1 verify_us=575584

FX6_R41_DESQUEEZE_BRIDGE ratios_supported=5 ratio_1_6x_centi=165 cinemascope_target=2.39:1
  hard_locks_enforced=4 focus_mode_lock=MF focus_area_lock=Wide steadyshot_lock=Off
  face_priority_metering_lock=Off raw_output_suppress=1 hdmi_only_forces_info_off=1
  log_off_suppress=1 remote_shooting_suppress=1 desqueeze_state_ok=1 emmc_write_count=0 r41_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `135` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 外置专属 `Monitor & Control` `[Focus Map]` 与 `>=150fps` S&Q 截断 / `<=6fps` 放行对比（`r41b`）
```text
FX6_R41_EXTERNAL_FOCUSMAP_150FPS body_model=ILME-FX3 fw_ver=7.02 external_app=Monitor_and_Control
  inbody_menu_toggle_reject_rc=-95 stageb_local_overlay_guard_rc=-95 local_lcd_overlay_draws=0
  fps_1_sq_rc=0 fx3_1fps_allowed=1 fps_6_sq_rc=0 fx3_6fps_allowed=1 fx6_ref_6fps_reject_rc=-22
  fps_24_rc=0 fps_60_rc=0 fps_120_rc=0 fps_149_boundary_rc=0 sub_150fps_stream_active=1
  fps_150_cutoff_rc=-22 sq_200fps_reject_rc=-22 sq_240fps_reject_rc=-22
  sq_200fps_stream_active=0 sq_240fps_stream_active=0
  mount_adapter_reject_rc=-19 non_pdaf_lens_reject_rc=-19 no_lens_reject_rc=-19 playback_reject_rc=-16
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1
  emmc_write_count=0 r41b_ok=1 verify_us=589696
```

### 2.3 双卡 `[Simult. Recording]` + `[Auto Switch Media]` 单卡续录与 `[Shockless WB]` 零帧直通旁路（`r41c`）
```text
FX6_R41_SIMULT_SHOCKLESSWB dual_initial_mask=0x3
  autoswitch_on_slot1_full_rc=0 single_slot_cont_active=1 cont_slot_mask=0x2 cont_dropped_frames=0
  card_swap_dual_resume_rc=0 resumed_slot_mask=0x3 dual_slot_resumed=1 both_slots_full_rc=-28
  autoswitch_off_slot1_full_rc=-28 autoswitch_off_halted=1 autoswitch_off_slot_mask=0x0
  fps_sweep_verified=6 preset_24p_1_frames=12 preset_24p_2_frames=24 preset_24p_3_frames=48
  preset_240fps_3_frames=480 invalid_shockless_mode_rc=-22
  ctemp_kelvin_transition_frames=0 ctemp_kelvin_immediate_bypass=1
  ab_gm_grid_transition_frames=0 ab_gm_grid_immediate_bypass=1
  p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 emmc_write_count=0 r41c_ok=1 verify_us=4466
```

---

## 3. `r41a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r41a` Alpha（`26.21 KiB` / `26,842 B`） | `r41a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r41a Big6 Alpha](assets/r41a-desqueeze-165x-big6-schinese-alpha.png) | ![r41a Big6 Composited](assets/r41a-desqueeze-165x-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）挂载 `1.3x / 1.5x / 1.6x / 2.0x` 变形宽银幕镜头切换 `[Shooting] -> [Shooting Display] -> [De-Squeeze Display]`，核验机背 LCD 与外接 HDMI 监看器的 `1.65x` 水平反挤压画面、4 项灰显硬锁死及开启 `[RAW Output]` / `[Off(HDMI Only)]` 时的自动旁路。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）通过 Wi-Fi / USB 连接搭载 Sony `Monitor & Control`（`Ver. 2.1.0+`）的移动终端，实测 `1fps / 6fps / 24p / 60p / 120p` 下的实时 `Focus Map` 景深色块叠加与切入 `200fps / 240fps` `S&Q` 或安装转接环镜头时的断流提示。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）双槽插入不同容量 `SDXC` / `CFexpress Type A` 存储卡开启 `[Simult. Recording]` + `[Auto Switch Media]=On/Off` 进行写满续航与热换卡双录恢复实测，以及在实景双色温光源下切换白平衡预设与拧动 `[C.Temp./Filter]` 色温值核验 `[Shockless WB]` 过渡响应。

---

## 5. 复现命令与洁净室合规

```bash
# Run 41A: [De-Squeeze Display] 5-Ratio (1.6x=1.65x) + 4 Hard Locks + HDMI RAW / Clean-HDMI Suppression + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 41 --r41-mode desqueeze_165x_4locks_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r41a-desqueeze-165x-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r41-runs/r41a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r41a-desqueeze-165x-big6-schinese \
  --export-png-dir reports/2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu/assets

# Run 41B: External-Only Monitor & Control [Focus Map] (No In-Body FX3 Menu) & >=150fps S&Q Cutoff (1..6fps Allowed)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 41 --r41-mode external_focusmap_150fps_cutoff --lang en --run-id r41b-external-focusmap-150fps \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r41-runs/r41b

# Run 41C: Dual-Slot [Simult. Recording] + [Auto Switch Media] Continuation & [Shockless WB] Kelvin/Grid 0-Frame Bypass + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 41 --r41-mode simult_autoswitch_shocklesswb --lang en --run-id r41c-simult-shocklesswb \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r41-runs/r41c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
