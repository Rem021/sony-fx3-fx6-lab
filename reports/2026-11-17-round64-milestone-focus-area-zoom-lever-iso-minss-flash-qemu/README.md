# Round 64（`64th` 轮 2 的幂总里程碑 · Wave-50 / `R28..R64` `37/37` 实机预演轮次 · 第 `109..111` 次实跑 -> `111/111` 总实跑 · `74/74` 张 Big-6 PNG）：FX3 7.02 原厂内核真机准备预演 — 14 区 `[Focus Area]` 静态 vs 视频 `Tracking:` 分离与 `[Focus Area Limit]`（`>= 2`）/ `[AF Area Registration]`、机身 `W/T` `[Zoom Lever Speed]`（`1st=3`/`2nd=8`）与 `XLR-H1` 无变焦拨杆证伪 vs `FX6` `Handle Zoom`（`1..8`）+ `0..99` `Zoom Position Display`、`[ISO Range Limit]` 与静态专属 `[ISO AUTO Min. SS]` vs `Cine EI` Base-ISO 锁定、机械快门静态 `[Flash Mode]`（`<= 1/250 s`）vs 4 模式 `[Video Light Mode]` MI-Shoe 保护

> **日期**：2026-11-17 | **轮次**：**Round 64 (Wave-50 · `64th` Round Power-of-Two Grand Milestone · `37/37` Real-HW Rounds · `109th..111th` Live Runs -> `111/111` Total Live Runs, `74/74` PNGs)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r64a` / `r64b` / `r64c`，正式达成 **第 `64` 轮 `2^6` 总里程碑**、**`R28..R64` `37/37` 轮实机内核预演**、**第 `109..111` 次 -> `111/111` 次独立实跑**、**`74/74` 张 `< 50 KiB`（本轮 `<= 27,467 B`：`27,132 B` 与 `27,467 B`）PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身相位对焦台架、`XLR-H1` 与电动变焦镜头实体、`[ISO Range Limit]` / `P`/`A` `[ISO AUTO Min. SS]` / `Cine EI` 实拍增益标定，以及机械快门 `1/250 s` 闪光同步与 MI-Shoe `5V <= 900mA` 视频灯实测尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 64 轮 `64th` 总里程碑 / `37/37` 实机预演（Wave-50 · `37/37` 实机轮次 / `109th..111th` -> `111/111` 次实跑 / `74/74` PNG）三项实机预演总览（`r64a` / `r64b` / `r64c`）

| 实跑场景 | Run ID | `r64_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **64A（第 109 次实跑）：Wave-50 四大支柱 — 14 区 `[Focus Area]`/`[Focus Area Limit]`/`[AF Area Registration]`、机身 `W/T` `[Zoom Lever Speed]` vs `XLR-H1` & `FX6` `1..8`/`0..99`、`[ISO Range Limit]`/`[ISO AUTO Min. SS]` vs `Cine EI`、机械静态 `[Flash Mode]` vs `[Video Light Mode]` + Big-6 Home** | `r64a` | `focus_area_zoom_iso_flash_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **14 区 `[Focus Area]`**（`_g.uxc 0x61f1` / `.uxc 0xe0ad`：7 非跟踪 + 7 **`Tracking:` 仅限静态 `AF-C`**，Movie/`S&Q` 返回 `-16 EBUSY`，`movie_tracking_focus_area_bypass_events=0`）、**`[Focus Area Limit]`**（`0x6de2` 强制 `>= 2` 勾选，`< 2` 返回 `-22 EINVAL`）、`[Focus Area Color]`（`White`/`Red` 跨复位存活）与 **`[AF Area Registration]`**（`0x6b65` 静态召回并锁定 `[Lock Operation Parts]=Off`），对比仅 3 区的 `ILME-FX6`（`-2 ENOENT`）；(2) 核验机身 `W/T` **`[Zoom Lever Speed]`**（`0x6304`：`1st=3`/`2nd=8`，`1..8` 分 `STBY`/`REC`）、证伪 `XLR-H1` 无变焦杆/无录像键/无 `ZOOM HOLD` 开关（`-19 ENODEV`，`xlr_h1_zoom_spoof_events=0`）、`[Zoom Range]`（`Optical`/`ClearImage`/`Digital`）在 `RAW`/`119.88p` 拦截（`-16 EBUSY`），对比 `FX6` `Handle Zoom` `1..8` + `0..99` `Zoom Position Display` 与 `Rec Button Only` `HOLD`；(3) 核验 **`[ISO Range Limit]`**（`0x72f8` 仅限手动 ISO，`HLG Still On` 底限 `>= 100`）与静态 `P`/`A` 专属 **`[ISO AUTO Min. SS]`**（`0x778b` `SLOWER..FASTER`/`1/8000..30"`）vs `Cine EI`/`Cine EI Quick` 硬锁 Base ISO `800`/`12800`（`-16 EBUSY`）；(4) 核验静态机械快门 **`[Flash Mode]`**（`0xe5ce` 5 模式，`<= 1/250 s`、沉睡 `ADVANCED_FLASH`/`WIRELESS` `-95`、`< 250V` 中心触点）vs 4 模式 **`[Video Light Mode]`**（`0x6211` `5V <= 900mA` MI-Shoe PMIC）+ `Slot-1` `-EROFS`，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r64_init_ok=1`, `r64_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.32s` | [`r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png`](assets/r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png) |
| **64B（第 110 次实跑）：Fail-Closed Wave-50 防火墙 — Movie `Tracking:`、`<2` 区域限制、`XLR-H1` 变焦伪造、`Cine EI` 增益、超同步/高电压闪光、MI-Shoe 过流与 `Slot-1` 只读拦截** | `r64b` | `wave50_focus_zoom_iso_flash_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 Movie/`S&Q` 下选择 `Tracking:` 对焦区（`-16 EBUSY`）、`< 2` `[Focus Area Limit]`（`-22 EINVAL`）及 `FX6` 无 `Tracking:`/`Limit`/`AF Reg`（`-2 ENOENT`）；(2) 拦截 `XLR-H1` 手柄变焦/`HOLD` 伪造（`xlr_h1_zoom_spoof_rc=-19`, `xlr_h1_hold_spoof_rc=-19 ENODEV`）、`FX6` `speed=99` 伪造（`-22 EINVAL`）与 `RAW`/`119.88p` 下 `ClearImage`/`Digital Zoom`（`-16 EBUSY`）；(3) 拦截 Movie/`S&Q`/`S`/`M` 下 `[ISO AUTO Min. SS]`（`-16`）、`Cine EI` 下手动/自动 ISO 与 `[Auto Slow Shutter]` 覆盖（`-16`）、`FX6` `Min. SS`（`-2`）与 `HLG Still` `ISO<100`（`-22`）；(4) 拦截 Movie/`S&Q` 闪光（`-16`）、电子快门/静音模式/沉睡 `ADVANCED_FLASH`/`WIRELESS` 闪光（`-95 EOPNOTSUPP`）、`1/320s` 超同步闪光（`-22 EINVAL`）、`>= 250V`/反极性触发与 `> 900mA` 视频灯过流（`-75 EOVERFLOW`）、`FX6` 静态闪光（`-2`），以及只读 `Slot-1`/`P2`/`cnflasha` 写入（`-30 EROFS`, `slot1_vault_sha256_match=1`, `emmc_write_count=0`, `r64b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.70s` | — |
| **64C（第 111 次实跑 · 闭环）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-50 复位层级不对称验证 + `XLR-H1`/`FX6` `Rec Button Only` + `16/16 H0 == H3`** | `r64c` | `clean_unmount_wave50_reset_h0_h3_big6` | Native ARM64 Wave-50 联合预演（**第 `64` 轮 `2^6` 总里程碑 / `37/37` 实机轮次 · 第 `111/111` 次独立实跑闭环**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 将 `[Focus Area]`/`[Focus Area Limit]`/`[Switch V/H AF Area]`/`[Circ. of Focus Point]`/变焦杆与遥控速度/`[ISO AUTO Min. SS]`/`[Flash Mode]`/`[Flash Comp.]`/`[Wireless Flash]`/`[Red Eye Reduction]` 复位，而 **`[Focus Area Color]`、`[AF Area Registration]`、`[Zoom Range]`、`[ISO Range Limit]`、`[Exp.comp.set]`、`[External Flash Set.]` 与 `[Video Light Mode]` 跨复位存活**（`camreset_preserves_wave50_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave50_defaults_ok=1`）；核验 `XLR-H1` 与 `FX6` `Handle HOLD Switch = Rec Button Only`（`xlrh1_and_fx6_handle_hold_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.09s` | 同 `64A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-50 四大支柱初始化与 Stage-B 四路桥接（`r64a` — 第 109 次实跑）
```text
FX6_R64_WAVE50_INIT fx3_wave50_nodes_ok=1 uxc_tokens_ok=1
  focus_area_14mode_ok=1 zoom_lever_xlrh1_fx6_ok=1
  iso_limit_minss_cineei_ok=1 flash_still_videolight_ok=1
  movie_tracking_fa_rc=-16 fa_limit_lt2_rc=-22 xlr_h1_zoom_rc=-19
  fx6_zoom99_rc=-22 movie_iso_minss_rc=-16 cineei_gain_rc=-16
  flash_movie_rc=-16 flash_eshutter_rc=-95 flash_sync320_rc=-22
  flash_dormant_rc=-95 flash_250v_rc=-75 videolight_950ma_rc=-75
  fx6_still_flash_rc=-2 p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  movie_tracking_focus_area_bypass_events=0 xlr_h1_zoom_spoof_events=0
  cine_ei_gain_override_events=0 still_flash_lockout_bypass_events=0
  pmic_5v_overcurrent_events=0 slot1_wave50_write_events=0
  passive_tx_bytes_emitted=0 cnflasha_writes=0 e_nd_actuator_tx_count=0
  appfw_present=1 shim_present=1 emmc_write_count=0
  r64_init_ok=1 verify_us=793098

FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE focus_14area_still_afc_split_ok=1
  focus_area_limit_ge2_color_circ_ok=1 af_area_reg_fx6_3area_enoent_ok=1
  focus_area_14mode_ok=1 movie_tracking_focus_area_bypass_events=0
  emmc_write_count=0 r64_bridge_ok=1

FX6_R64_ZOOM_LEVER_XLRH1_FX6_BRIDGE body_wt_zoom_lever_1st3_2nd8_ok=1
  xlr_h1_zoom_less_enodev_ok=1 fx6_handle_zoom_1_8_pos_0_99_hold_ok=1
  zoom_lever_xlrh1_fx6_ok=1 xlr_h1_zoom_spoof_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R64_ISO_LIMIT_MINSS_CINEEI_BRIDGE iso_range_limit_manual_hlg_ok=1
  still_pa_iso_auto_min_ss_ok=1 cine_ei_base_iso_pin_lock_ok=1
  iso_limit_minss_cineei_ok=1 cine_ei_gain_override_events=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R64_FLASH_STILL_VIDEOLIGHT_PMIC_BRIDGE still_flash_mech_sync_250v_ok=1
  dormant_adv_flash_wireless_guard_ok=1 video_light_4mode_5v_900ma_slot1_erofs_ok=1
  flash_still_videolight_ok=1 still_flash_lockout_bypass_events=0
  pmic_5v_overcurrent_events=0 slot1_wave50_write_events=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `103` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed `Tracking:`、`<2` 区域、`XLR-H1` 变焦伪造、`Cine EI` 增益、超同步/高电压闪光与 `Slot-1` 隔离拦截（`r64b` — 第 110 次实跑）
```text
FX6_R64_WAVE50_GUARD movie_tracking_wide_rc=-16 movie_tracking_spot_rc=-16
  sq_tracking_zone_rc=-16 fa_limit_1_rc=-22 fa_limit_0_rc=-22
  fx6_tracking_rc=-2 fx6_fa_limit_rc=-2 fx6_af_reg_rc=-2
  xlr_h1_zoom_spoof_rc=-19 xlr_h1_hold_spoof_rc=-19 fx6_speed_99_rc=-22
  ciz_raw_rc=-16 dig_119p_rc=-16 minss_movie_rc=-16 minss_sq_rc=-16
  minss_still_s_rc=-16 minss_still_m_rc=-16 cineei_manual_iso_rc=-16
  cineei_auto_iso_rc=-16 cineei_autoslow_rc=-16 fx6_minss_rc=-2 hlg_iso_50_rc=-22
  flash_movie_rc=-16 flash_sq_rc=-16 flash_eshutter_rc=-95 flash_silent_rc=-95
  flash_sync320_rc=-22 flash_adv_dormant_rc=-95 flash_wireless_dormant_rc=-95
  flash_250v_rc=-75 flash_revpol_rc=-75 videolight_950ma_rc=-75
  fx6_still_flash_rc=-2 slot1_wave50_erofs_rc=-30
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  movie_tracking_focus_area_bypass_events=0 xlr_h1_zoom_spoof_events=0
  cine_ei_gain_override_events=0 still_flash_lockout_bypass_events=0
  pmic_5v_overcurrent_events=0 slot1_wave50_write_events=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r64b_ok=1 verify_us=782369
```

### 2.3 洁净卸载还原原厂、Wave-50 复位层级与 `16/16 H0 == H3`（`r64c` — 第 111 次实跑）
```text
FX6_R64_CLEAN_UNMOUNT_WAVE50_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave50_survivors_ok=1
  initialize_restores_wave50_defaults_ok=1
  xlrh1_and_fx6_handle_hold_ok=1
  movie_tracking_focus_area_bypass_events=0 xlr_h1_zoom_spoof_events=0
  cine_ei_gain_override_events=0 still_flash_lockout_bypass_events=0
  pmic_5v_overcurrent_events=0 slot1_wave50_write_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0
  r64c_ok=1 verify_us=361006
```

---

## 3. `r64a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r64a` Alpha（`26.50 KiB` / `27,132 B`） | `r64a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r64a Big6 Alpha](assets/r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-alpha.png) | ![r64a Big6 Composited](assets/r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）相位检测自动对焦光学台架（实测 14 区 `[Focus Area]`——7 非跟踪与 7 静态 `AF-C` 专属 `Tracking:` 选项、`[Focus Area Limit]` `>= 2` 勾选轮换、`[Focus Area Color]` `White`/`Red` 对焦框着色、`[Circ. of Focus Point]` 边界循环与 `[AF Area Registration]` 召回锁定 `[Lock Operation Parts]=Off`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）+ `XLR-H1` 手柄与电动变焦镜头台架（实测机身 `W/T` `[Zoom Lever Speed]` `1st=3`/`2nd=8` `STBY`/`REC` 两段式摇杆速度、`XLR-H1` 物理上无变焦杆/无录像键/无 `ZOOM HOLD` 开关、`[Zoom Range]` `Optical`/`ClearImage`/`Digital` 在 `RAW` 与 `119.88p` 下的互斥截止，以及 `ILME-FX6` `Ver. 6.01` `Handle Zoom` `1..8` + `0..99` `Zoom Position Display`）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）曝光与 MI-Shoe 光电台架（实测 `[ISO Range Limit]` 仅限手动 ISO 及 `HLG Still On` `>= 100` 下限、静态 `P`/`A` 专属 `[ISO AUTO Min. SS]`、`[Cine EI]`/`[Cine EI Quick]` `800`/`12800` Base-ISO 硬锁定、`1/250 s` 机械快门闪光同步上限 `< 250 V` 触发，以及 4 模式 `[Video Light Mode]` `5 V <= 900 mA` MI-Shoe 电源预算）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 64A (109th Live Run): Wave-50 4-Pillar Focus Area + Zoom Lever/XLR-H1 + ISO Limit/Min. SS/Cine EI + Flash/Video Light + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 64 --r64-mode focus_area_zoom_iso_flash_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r64a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round64-qemu/r64a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r64a-focus-area-zoom-iso-flash-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/assets

# Run 64B (110th Live Run): Fail-Closed Wave-50 Guard (Tracking, <2 Limit, XLR-H1 Spoof, Cine EI Gain, Flash Sync/Voltage/PMIC, Slot-1 EROFS)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 64 --r64-mode wave50_focus_zoom_iso_flash_guard --sd-manifest-mode valid --lang en \
  --run-id r64b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round64-qemu/r64b

# Run 64C (111th Live Run — 64th Power-of-Two & 37/37 Real-HW Closure): Clean Unmount Stock FX3 Restoration, Wave-50 Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 64 --r64-mode clean_unmount_wave50_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r64c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round64-qemu/r64c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`movie_tracking_focus_area_bypass_events == 0`、`xlr_h1_zoom_spoof_events == 0`、`cine_ei_gain_override_events == 0`、`still_flash_lockout_bypass_events == 0`、`pmic_5v_overcurrent_events == 0`、`slot1_wave50_write_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
