# Round 44：FX3 7.02 原厂内核真机准备预演（Wave-30 里程碑）— `[Pixel Mapping]` 自动重启与 `cnflasha` 只读防火墙、`[NTSC/PAL Selector]` 跨 `[Camera Settings Reset]` 保持、`[Gamma Display Assist]` 与 `[Display LUT]` 分流

> **日期**：2026-11-15 | **轮次**：**Round 44 Live ARM64 QEMU Rehearsal (Wave-30 Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r44a` / `r44b` / `r44c`）测得；**物理实体 `ILME-FX3` 机身执行机械快门暗场闭合的 `[Auto Pixel Mapping]` / 手动 `[Pixel Mapping]` 与 PMIC 热重启脉冲、物理双卡槽插入 `CFexpress Type A` / `SDXC` 存储卡触发 NTSC ↔ PAL 跨制式 `M4ROOT` / `AVCHD` 数据库格式化提示弹窗、以及物理 Type-A HDMI 2.0 信号分析仪与机身 144 万点 LCD 实测 `[Gamma Display Assist]` vs `[Display LUT]` 显示管线尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 44 轮三项实机预演总览（`r44a` / `r44b` / `r44c`）

| 实跑场景 | Run ID | `r44_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **44A：`[Auto Pixel Mapping]` / 手动 `[Pixel Mapping]` 低电拒止、自动重启清空 `/tmp` 与 `cnflasha` 只读锁 + Big-6 Home** | `round44-pixelmap-cnflasha-big6` | `pixelmap_reboot_cnflasha_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[Auto Pixel Mapping]` 默认 `On`（`auto_pixel_map_default_on=1`），关机暗场标定时即使 `[Silent Mode]=[On]` 仍允许驱动机械快门闭合（`silent_mode_poweroff_shutter_ok=1`），设为 `Off` 满 `3` 天触发手动像素映射周期告警（`auto_off_3day_warn_ok=1`）；手动 `[Pixel Mapping]` 在低电量下拒止（`low_battery_reject_rc=-11` `EAGAIN`），标定执行期封锁全部机身按键输入（`op_lockout_during_cal_rc=-16` `EBUSY`），完成后强制自动重启并卸载/清空易失 `/tmp` Stage-B 绑定挂载层无痕回退至原厂 `FX3 7.02`（`auto_restart_tmp_wiped_ok=1`, `stock_h0_eq_h2_ok=1`）；对 `cnflasha` 传感器工厂校准分区的任何写打开与用户态写入均被 `-30`（`EROFS`）与 `-1`（`EPERM`）双重封堵（`cnflasha_write_count=0`, `cnflasha_sha256_match=1`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `78.14s` | [`r44a-pixelmap-cnflasha-big6-schinese-composited.png`](assets/r44a-pixelmap-cnflasha-big6-schinese-composited.png) |
| **44B：`[NTSC/PAL Selector]` 独占帧率/`DF-NDF` 表、开机横幅与 `[Camera Settings Reset]` 留存** | `round44-ntscpal-camreset` | `ntscpal_dfn_camreset_persist` | Native ARM64 制式与重置分层探针实测：`NTSC` 开放全部 `4` 档帧率（`23.98p` NTSC 独占、`29.97p`、`59.94p`、`119.88p`，`ntsc_rates_verified=4`）及 `[TC Format]` `DF` / `NDF`（`ntsc_tc_df_ndf_ok=1`，拒止 PAL `25p` `rc=-22`）；`PAL` 开放 `3` 档帧率（`25p`、`50p`、`100p`，`pal_rates_verified=3`），严拒 `23.98p` / `29.97p`（`rc=-22` `EINVAL`）并封锁 `[TC Format]` `DF` / `NDF`（`pal_tc_df_ndf_reject_rc=-95` `EOPNOTSUPP`）；当制式偏离区域出厂默认时开机准确弹出 `"Running on PAL."` / `"Running on NTSC."` 横幅（区域默认态静默 `default_banner_suppressed_ok=1`）；执行 `[Camera Settings Reset]` 后完整保留 `[NTSC/PAL Selector]` 当前制式（`ntsc_pal_survived_camera_reset=1`），唯独全量 `[Initialize]` 恢复区域出厂默认（`initialize_restored_default_ok=1`）；双槽 `M4ROOT` / `AVCHD` 跨制式混插返回 `-16` `EBUSY` 隔离保护（`dual_slot_m4root_avchd_sep_ok=1`），`p2:/setting` 只读不变（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期制式 C 探针退出） | 跳过（制式 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.01s` | — |
| **44C：`[Gamma Display Assist]` 4 档表 vs `[Log Shooting]` `[Display LUT]` 锁定、零 HDMI 外泄与 `16/16 H0 == H3`** | `round44-gammaassist-displaylut` | `gammaassist_displaylut_h0_h3` | Native ARM64 监看辅助分流探针证实：`[Gamma Disp. Assist Typ.]` 严格对齐 FX3 `7.02` 精确 4 档表（`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`，`gamma_assist_4modes_verified=4`），拒绝 FX3 `7.02` 不存在的 `S-Log2` 辅助项（`slog2_assist_reject_rc=-22` `EINVAL`）；在 `Picture Profile` 拍摄/回放及 `[HLG Still Image]=On` 静态照片回放中仅作用于机身内置 LCD，绝不套用至 HDMI 输出或录制文件（`lcd_gamma_assist_applied=1`, `hdmi_gamma_assist_applied=0`）；一旦开启 `[Log Shooting]` 任一模式（`Cine EI` / `Cine EI Quick` / `Flexible ISO`，`log_3modes_force_assist_off_ok=3`），立即将 `[Gamma Display Assist]` 硬锁为 `Off`（改写返回 `-16` `EBUSY`）并交由 `[Display LUT]` `On`/`Off` 自定义键接管监看（关闭 Log 后解锁恢复，且非 Log 态调用 `[Display LUT]` 返回 `-95`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期监看 C 探针退出） | 跳过（监看 C 探针退出） | **`0`** / **`0`** / **`0`** | `5.41s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Auto Pixel Mapping]` / 手动 `[Pixel Mapping]` 自动重启清 `/tmp` 与 `cnflasha` 只读防火墙（`r44a`）
```text
FX6_R44_PIXELMAP_CNFLASHA_INIT auto_pixel_map_default_on=1 silent_mode_poweroff_shutter_ok=1
  auto_off_3day_warn_ok=1 low_battery_reject_rc=-11 op_lockout_during_cal_rc=-16
  auto_restart_triggered=1 auto_restart_tmp_wiped_ok=1 stock_h0_eq_h2_ok=1
  cnflasha_ro_open_rc=-30 cnflasha_userspace_firewall_rc=-1 cnflasha_sha256_match=1
  cnflasha_write_count=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r44_init_ok=1 verify_us=1034652

FX6_R44_PIXELMAP_CNFLASHA_BRIDGE auto_pixel_map_default_on=1 silent_poweroff_shutter_ok=1
  auto_off_3day_warn_days=3 low_battery_reject_rc=-11 op_lockout_during_cal_rc=-16
  auto_restart_tmp_wiped_h0_eq_h2=1 cnflasha_ro_reject_rc=-30 cnflasha_firewall_rc=-1
  cnflasha_write_count=0 pixelmap_cnflasha_ok=1 emmc_write_count=0 r44_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `117` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[NTSC/PAL Selector]` 独占帧率/`DF-NDF`、`"Running on NTSC."` / `"Running on PAL."` 横幅与 `[Camera Settings Reset]` 留存（`r44b`）
```text
FX6_R44_NTSCPAL_CAMRESET ntsc_rates_verified=4 ntsc_2398p_exclusive_ok=1 ntsc_pal_25p_reject_rc=-22
  ntsc_tc_df_ndf_ok=1 invalid_tc_fmt_reject_rc=-22 pal_rates_verified=3 pal_2398p_reject_rc=-22
  pal_2997p_reject_rc=-22 pal_tc_df_ndf_reject_rc=-95 default_banner_suppressed_ok=1
  running_on_pal_banner_ok=1 running_on_ntsc_banner_ok=1 ntsc_pal_survived_camera_reset=1
  initialize_restored_default_ok=1 cross_region_db_mismatch_rc=-16 dual_slot_m4root_avchd_sep_ok=1
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1
  emmc_write_count=0 r44b_ok=1 verify_us=659645
```

### 2.3 `[Gamma Display Assist]` 4 档表 vs `[Log Shooting]` `[Display LUT]` 锁定、零 HDMI 外泄与 `16/16 H0 == H3`（`r44c`）
```text
FX6_R44_GAMMAASSIST_DISPLAYLUT gamma_assist_4modes_verified=4 slog2_assist_reject_rc=-22
  pp_shoot_pb_hlg_still_ok=1 lcd_gamma_assist_applied=1 hdmi_gamma_assist_applied=0
  lcd_only_zero_hdmi_scope_ok=1 log_3modes_force_assist_off_ok=3 gamma_assist_locked_in_log_rc=-16
  display_lut_on_off_switch_ok=1 display_lut_reject_when_log_off_rc=-95
  gamma_assist_unlocked_when_log_off_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r44c_ok=1 verify_us=4898
```

---

## 3. `r44a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r44a` Alpha（`26.21 KiB` / `26,842 B`） | `r44a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r44a Big6 Alpha](assets/r44a-pixelmap-cnflasha-big6-schinese-alpha.png) | ![r44a Big6 Composited](assets/r44a-pixelmap-cnflasha-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）实机上电测试关机 `[Auto Pixel Mapping]`（含 `[Silent Mode]=[On]` 下机械快门暗场闭合声学确认）以及手动触发 `[Pixel Mapping]` 后的 PMIC 自动硬件热重启周期。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）插入已录制片段的实体 `CFexpress Type A` / `SDXC` 卡切换 `[NTSC/PAL Selector]`，观测机身 `"Running on NTSC."` / `"Running on PAL."` 开机提示横幅、`M4ROOT` / `AVCHD` 管理数据库重建提示，以及执行 `[Camera Settings Reset]` vs `[Initialize]` 后的实机状态对比。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）连接 Type-A HDMI 2.0 波形/协议分析仪，实测 `Picture Profile` 模式下开启 `[Gamma Display Assist]`（`S-Log3->709(800%)` 等 4 档）时内置 144 万点 LCD 与纯净 HDMI 输出的对比，以及切换至 `Cine EI` / `Flexible ISO` 后 `[Gamma Display Assist]` 自动灰显并切换为 `[Display LUT]` 的实机色彩链路。

---

## 5. 复现命令与洁净室合规

```bash
# Run 44A: [Auto Pixel Mapping] / Manual [Pixel Mapping] Auto-Restart + cnflasha Read-Only Firewall + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 44 --r44-mode pixelmap_reboot_cnflasha_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round44-pixelmap-cnflasha-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r44-runs/r44a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r44a-pixelmap-cnflasha-big6-schinese \
  --export-png-dir reports/2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu/assets

# Run 44B: [NTSC/PAL Selector] Exclusive Frame-Rate / DF-NDF Tables, Startup Banner & [Camera Settings Reset] Survival
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 44 --r44-mode ntscpal_dfn_camreset_persist --lang en --run-id round44-ntscpal-camreset \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r44-runs/r44b

# Run 44C: [Gamma Display Assist] 4-Mode Table vs [Log Shooting] [Display LUT] Lockout, Zero-HDMI Scope & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 44 --r44-mode gammaassist_displaylut_h0_h3 --lang en --run-id round44-gammaassist-displaylut \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r44-runs/r44c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
