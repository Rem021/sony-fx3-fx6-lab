# Round 39：FX3 7.02 原厂内核真机准备实跑（Part 18）— 四模风扇 PWM（`Off in Rec` 待机 `MAX PWM` / 备份前 `Always Off` 拦截）、独立快门 `Speed/Angle`（`5.6°..64F / 360°`）与 `6.01` vs `7.02` `p2:/setting` User LUT 二进制槽防火墙

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r39a` / `r39b` / `r39c`）测得；**物理实体 `ILME-FX3` 机身内建涡轮风扇声学/转速台架、实机快门角度光学曝光积分测试图卡验证以及经 `6.00 -> 7.00 -> 7.02` 升级机身的实体卡双启动冷归位尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r39a` / `r39b` / `r39c`）

| 实跑场景 | Run ID | `r39_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **39A：四模 `[Fan Control]`（禁 `Auto1`/`Auto2`）+ `Off in Rec` 待机 `MAX PWM` + 备份前 `Always Off` 联锁 + Big-6 Home** | `r39a-fan-pwm-offinrec-big6-schinese` | `fan_pwm_offinrec_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接验证精确 4 模风扇状态机（`Auto` / `Minimum` `25%` / `Off in Rec` / `Always Off` 均 `rc=0`），硬拦截跨机型非法 `Auto1`/`Auto2`（`auto1_reject_rc=-22`, `auto2_reject_rc=-22` `EINVAL`）；证实 `Off in Rec` 待机驱动 **`100%` `MAX PWM`** 预冷、常目录制 `0% PWM` 静音、超温 `>=65 °C`（`68 °C`）强制拉满 `100% PWM`（`off_in_rec_thermal_override=1`）；拦截 `Always Off` 下进入 Tier-0 冷备份（`backup_while_always_off_rc=-16` `EBUSY`），直至强制切回 `Auto` 方放行（`backup_after_force_auto_rc=0`），并渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.38s` | [`r39a-fan-pwm-offinrec-big6-schinese-composited.png`](assets/r39a-fan-pwm-offinrec-big6-schinese-composited.png) |
| **39B：独立 `[Shutter Mode]`（`Speed` vs `Angle`）双槽持久化与帧率钳位（`5.6°..64F` vs `119.88p/100p` & `S&Q` `5.6°..360°`）** | `r39b-shutter-speed-angle-clamp` | `shutter_speed_angle_clamp` | Native ARM64 快门验证器在 `Speed`（`1/125`）与 `Angle`（`172.8°` = `1728 deci-deg`）间连续切换 `32` 次并叠加 `0.3EV` / `0.5EV` 曝光步进切换，证实两套底层槽位完全独立（`cross_clobber_events=0`, `exposure_step_drift_deci_deg=0`）；`<=59.94p`（`23.98p` / `59.94p`）放行 `5.6°..64F`（`23040 deci-deg`, `rc=0`），`<5.6°` 与 `>64F` 拒收（`rc=-34` `ERANGE`）；切入 `119.88p`/`100p` HFR 与 `S&Q` 时自动将 `64F` 钳位至 **`360.0°`**（`3600 deci-deg`）且保持 `Speed` 槽 `1/125` 不变，同时拒绝 HFR/`S&Q` 下写入 `>360°`（`64F`/`720°`, `rc=-34`）并锁定 `p2:/setting` 只读（`p2_write_blocked_rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期快门 `Speed/Angle` 校验退出） | 跳过（Shutter C 探针退出） | **`0`** / **`0`** / **`0`** | `5.47s` | — |
| **39C：`FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT 二进制格式防火墙与 `16/16 H0 == H3`** | `r39c-lut-601-vs-702-firewall` | `lut_601_vs_702_firewall` | 拦截 Stage-B `FX6 6.01` 旧版格式（`schema=0x0601`）向 `MS_RDONLY` `p2:/setting` 直接写入 `User1..User16` 槽位（`p2_lut_direct_write_rc=-30` `EROFS`, `16/16` 槽全数阻断）及跨 Schema ABI 混写（`lut_abi_mismatch_reject_rc=-80` `ELIBBAD`）；将 Stage-B `User1..User16` 注册全部重定向至易失性 `/tmp/fx6_lut_overlay`（`overlay_slots_registered=16`, `overlay_601_readback_ok=16`），模拟冷重启清空覆盖层（`overlay_post_reboot_residual=0`），核实原厂 `7.02`（`schema=0x0700`）`16/16` User LUT 槽头与 `Backup.bin` 零改动，通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期 LUT 防火墙校验退出） | 跳过（LUT Slot Firewall C 探针退出） | **`0`** / **`0`** / **`0`** | `4.89s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 四模 `[Fan Control]` 状态机、`Off in Rec` 待机 `MAX PWM` 与备份前 `Always Off` 联锁（`r39a`）
```text
FX6_R39_FAN_PWM_INIT fan_valid_modes=4 auto_rc=0 minimum_rc=0 off_in_rec_rc=0 always_off_rc=0
  auto1_reject_rc=-22 auto2_reject_rc=-22
  off_in_rec_standby_pwm=100 off_in_rec_rec_normal_pwm=0
  off_in_rec_rec_thermal_override_pwm=100 off_in_rec_thermal_override=1 minimum_pwm=25
  auto_power_off_temp_std_rc=0 auto_power_off_temp_high_rc=0
  backup_while_always_off_rc=-16 backup_after_force_auto_rc=0 forced_fan_mode=Auto
  libfan_present=1 appfw_present=1 shim_present=1 emmc_write_count=0 r39_init_ok=1 verify_us=589323

FX6_R39_FAN_PWM_BRIDGE fan_modes_count=4 auto1_reject_rc=-22 auto2_reject_rc=-22
  off_in_rec_standby_pwm=100 off_in_rec_rec_pwm=0 thermal_override_pwm=100
  always_off_backup_block_rc=-16 forced_auto_backup_rc=0
  fan_4mode_ok=1 off_in_rec_max_pwm_ok=1 pre_backup_interlock_ok=1 emmc_write_count=0 r39_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 独立 `[Shutter Mode]`（`Speed` vs `Angle`）双槽持久化与 HFR / `S&Q` 角度钳位（`r39b`）
```text
FX6_R39_SHUTTER_SPEED_ANGLE shutter_modes=Speed_Angle independent_slot_persistence=1
  speed_slot_preserved=1_125 angle_slot_preserved_deci=1728 mode_toggles_tested=32
  cross_clobber_events=0 exposure_step_drift_deci_deg=0 speed_preserved_post_clamp=1
  normal_5_6deg_accept_rc=0 normal_24p_64f_accept_rc=0 normal_5994p_64f_accept_rc=0
  under_5_6deg_reject_rc=-34 over_64f_reject_rc=-34
  clamped_11988p_deci_deg=3600 hfr_11988p_360deg_accept_rc=0
  hfr_11988p_64f_reject_rc=-34 hfr_11988p_720deg_reject_rc=-34
  hfr_100p_360deg_accept_rc=0 hfr_100p_64f_reject_rc=-34
  clamped_sq_deci_deg=3600 sq_5_6deg_accept_rc=0 sq_360deg_accept_rc=0 sq_64f_reject_rc=-34
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1
  appfw_shutter_ok=1 shim_elf_ok=1 emmc_write_count=0 r39b_ok=1 verify_us=584398
```

### 2.3 `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT 二进制槽防火墙（`r39c`）
```text
FX6_R39_LUT_601_702_FIREWALL donor_lut_schema=0x0601 stock_lut_schema=0x0700
  p2_lut_direct_write_rc=-30 p2_lut_slots_blocked=16 p2_backup_write_rc=-30
  lut_abi_mismatch_reject_rc=-80 overlay_dir=/tmp/fx6_lut_overlay
  overlay_slots_registered=16 overlay_601_readback_ok=16 overlay_post_reboot_residual=0
  stock_702_headers_intact=16 backup_h0_eq_h3=1 p2_setting_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  emmc_write_count=0 r39c_ok=1 verify_us=5051
```

---

## 3. `r39a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r39a` Alpha（`26.21 KiB` / `26,842 B`） | `r39a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r39a Big6 Alpha](assets/r39a-fan-pwm-offinrec-big6-schinese-alpha.png) | ![r39a Big6 Composited](assets/r39a-fan-pwm-offinrec-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身涡轮风扇声学与转速计台架实测：`[Fan Control] = Off in Rec` 待机 `100% MAX PWM` 预冷与录制 `0 RPM` 静音切换、真实 CMOS 升温下的热保护强启转速，以及强制 `[Fan Control] = Auto` 执行 Tier-0 备份期间的机身温升曲线。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在 `23.98p`/`59.94p`（`5.6°..64F`）与 `119.88p`/`100p` 及 `S&Q`（`5.6°..360°`）下切换 `[Shutter Mode] = Speed / Angle` 并通过光学测试图卡核验 `IMX510` 实际曝光积分时间。
3. 物理经 `Ver. 6.00 -> 7.00 -> 7.02` 升级的 `ILME-FX3` 机身导入 `User1..User16` 3D LUT 后，插入 SD 卡进入 Stage-B 双启动再拔卡冷启动返回原厂 `7.02` 的实体槽位零丢失复核。

---

## 5. 复现命令与洁净室合规

```bash
# Run 39A: 4-Mode Fan PWM + Off in Rec Standby MAX PWM + Pre-Backup Always Off Interlock + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 39 --r39-mode fan_pwm_offinrec_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r39a-fan-pwm-offinrec-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r39-runs/r39a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r39a-fan-pwm-offinrec-big6-schinese \
  --export-png-dir reports/2026-11-15-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu/assets

# Run 39B: Independent [Shutter Mode] (Speed vs Angle) Slot Persistence & Frame-Rate Clamping (5.6°..64F / 360°)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 39 --r39-mode shutter_speed_angle_clamp --lang en --run-id r39b-shutter-speed-angle-clamp \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r39-runs/r39b

# Run 39C: FX6 Ver. 6.01 vs Stock FX3 Ver. 7.00/7.02 p2:/setting User1..User16 LUT Binary Format Firewall & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 39 --r39-mode lut_601_vs_702_firewall --lang en --run-id r39c-lut-601-vs-702-firewall \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r39-runs/r39c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
