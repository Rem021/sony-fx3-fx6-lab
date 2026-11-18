# Round 59（Wave-45 / `R28..R59` 第 32 轮实机内核 QEMU 预演 · 第 96 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Focus Magnifier]` / `[Auto Magnifier in MF]`、`[Area/Date/Time Setting]` 零射频隔离、`[Video Light Mode]` PMIC 5V 门禁与 `[HDMI Resolution]` Log 1080p 降档

> **日期**：2026-11-17 | **轮次**：**Round 59 Live ARM64 QEMU Rehearsal (Wave-45 · 32nd Real-HW Round / 96th Live Run)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r59a` / `r59b` / `r59c`，累计达成 `R28..R59` **第 `32` 轮实机内核预演**与 **第 `96` 次独立实跑**、**`64` 张 `< 50 KiB` PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 `[Focus Magnifier]`/`[Auto Magnifier in MF]` 光学对焦、RTC/BLE 零射频 `[Area/Date/Time Setting]`、`[Video Light Mode]` MI-Shoe PMIC 5V 负载及外接 HDMI 监视器 `[HDMI Resolution]` 尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 59 轮（Wave-45 · 第 32 轮实机预演 / 第 96 次实跑）三项实机预演总览（`r59a` / `r59b` / `r59c`）

| 实跑场景 | Run ID | `r59_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **59A：`[Focus Assistant]`、`[Area/Date/Time Setting]` 零射频、`[Video Light Mode]` PMIC 5V 与 `[HDMI Resolution]` Log 1080p + Big-6 Home** | `round59-focus-mag-datetime-videolight-hdmires-big6` | `focus_mag_datetime_videolight_hdmires_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：核验 **`[Focus Assistant]`**（`MENU -> Focus -> [Focus Assistant]`：`Focus Magnifier` 默认 `Custom Button 5`、`Auto Magnifier in MF=[On]` 默认且无旧版 `"MF Assist"`、`Focus Magnif. Time` `No Limit`/`2 Sec`/`5 Sec`、照片与视频独立 `Initial Focus Mag.` `x1.0`/`x4.0`、照片 `AF in Focus Mag.` `On`/`Off`、`[Peaking Display]` `Off`/`Mid`/`White` 且零外接 HDMI 叠加烧录 `hdmi_clean_feed_baked_overlay_pixels=0`）；核验 **`[Area/Date/Time Setting]`**（`Area Setting`/`Daylight Savings`/`Date/Time`/`Date Format`，无旧版 `"Date/Time Setup"`，`[Setup]` 跨 `[Camera Settings Reset]` 存活，`Airplane Mode = On` 下 Creators' App `Auto Time Correction`/`Auto Area Adjustment` 零射频抑制 `passive_tx_bytes_emitted=0`）；核验 **`[Video Light Mode]`**（`Power Link` 默认 / `REC Link` / `REC Link & STBY` / `Auto` + `PMIC 5V <= 900 mA` 配件供电门禁 + 仅限照片 `[AF Illuminator]`）；核验 **`[HDMI Resolution]`**（`Auto` 默认 / `2160p` / `1080p` / `1080i` + Log 内录 `1080p` 降档覆盖）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.86s` | [`r59a-focus-mag-videolight-big6-schinese-composited.png`](assets/r59a-focus-mag-videolight-big6-schinese-composited.png) |
| **59B：Fail-Closed 非法注入 — Movie/`S&Q` `AF Illuminator`、飞行模式蓝牙授时、MI-Shoe >900 mA 过载、Log `2160p` 绕过与 `Slot-1` 写入拦截** | `round59-af-illum-bt-sync-pmic-5v-hdmi-2160p-guard` | `af_illum_bt_sync_pmic_5v_hdmi_2160p_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 Movie 与 `S&Q` 模式下触发 `[AF Illuminator]`（`movie_af_illum_rc=-95`, `sq_af_illum_rc=-95`, `af_illuminator_movie_sq_fire_events=0`）；(2) 拦截 `[Airplane Mode]=[On]` 下 Creators' App 蓝牙时间/时区跳变（`bt_sync_airplane_rc=-1`, `bt_sync_under_airplane_events=0`, `passive_tx_bytes_emitted=0`）；(3) 拦截 MI-Shoe `> 900 mA` PMIC 5V 过载注入（`pmic_5v_overload_rc=-95`, `pmic_5v_overcurrent_events=0`）；(4) 拦截 `Rec. Media dur HDMI Output = On` 时 Log 内录强开 HDMI `2160p` 绕过（`log_2160p_bypass_rc=-16`, `log_2160p_hdmi_bypass_events=0`）；(5) 拒绝旧版 `"MF Assist"` / `"Date/Time Setup"` 伪造（`legacy_mf_assist_rc=-2`, `legacy_dt_setup_rc=-2`）与干净 HDMI 叠加烧录（`hdmi_overlay_bake_rc=-1`, `hdmi_clean_feed_baked_overlay_pixels=0`）；(6) 保持物理 `Slot-1` `BODYDATA.DAT`、`p2:/setting` 与 `cnflasha` 只读零写入（`slot1_vault_ro_blocked_rc=-30`, `p2_write_blocked_rc=-30`, `cnflasha_ro_blocked_rc=-30`, `emmc_write_count=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.50s` | — |
| **59C：洁净卸载 `/tmp` Stage-B 覆盖层 + `[Camera Settings Reset]` vs `[Reset Network Set.]` vs `[Initialize]` + `16/16 H0 == H3`（第 32 轮 / 第 96 次实跑收官）** | `round59-clean-unmount-camreset-vs-init-h0-h3-big6` | `clean_unmount_camreset_vs_init_h0_h3_big6` | Native ARM64 Wave-45 联合预演（**第 `32` 轮实机预演 / 第 `96` 次独立实跑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Focus Magnifier]` / `[Peaking Display]` 在 **`[Camera Settings Reset]`** 后复位出厂（`focus_peaking_reset_by_camreset_ok=1`），而 `[Setup]` 域 **`[Area/Date/Time Setting]`**、**`[Video Light Mode]`** 与 **`[HDMI Resolution]`** 跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活（`setup_datetime_vl_hdmi_survive_camreset_ok=1`），仅在 **`[Initialize]`** 时统一还原（`initialize_restores_all_wave45_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.73s` | 同 `59A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Focus Assistant]`、`[Area/Date/Time Setting]` 零射频、`[Video Light Mode]` PMIC 5V 与 `[HDMI Resolution]`（`r59a`）
```text
FX6_R59_WAVE45_INIT fx3_wave45_nodes_ok=1 focus_assist_peaking_ok=1
  area_datetime_zerorf_ok=1 videolight_pmic_af_illum_ok=1
  hdmi_res_log_downshift_ok=1 setup_survives_camreset_ok=1
  bt_sync_blocked_rc=-1 pmic_overload_blocked_rc=-95 af_illum_movie_rc=-95
  af_illum_sq_rc=-95 log_2160p_bypass_rc=-16 hdmi_overlay_bake_rc=-1
  hdmi_clean_feed_baked_overlay_pixels=0 passive_tx_bytes_emitted=0
  pmic_5v_overcurrent_events=0 af_illuminator_movie_sq_fire_events=0
  log_2160p_hdmi_bypass_events=0 e_nd_actuator_tx_count=0 slot1_vault_writes=0
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r59_init_ok=1 verify_us=1014772

FX6_R59_FOCUS_ASSIST_PEAKING_BRIDGE focus_mag_custom5_auto_mf_on_ok=1
  legacy_mf_assist_absent_ok=1 still_movie_init_mag_sep_ok=1
  peaking_display_clean_hdmi_ok=1 hdmi_clean_feed_baked_overlay_pixels=0
  focus_assist_peaking_ok=1 emmc_write_count=0 r59_bridge_ok=1

FX6_R59_AREA_DATETIME_ZERORF_BRIDGE area_datetime_4items_ok=1
  legacy_datetime_setup_absent_ok=1 setup_survives_camreset_ok=1
  zerorf_airplane_bt_blocked_ok=1 passive_tx_bytes_emitted=0
  area_datetime_zerorf_ok=1 emmc_write_count=0 p2_setting_writes=0

FX6_R59_VIDEOLIGHT_PMIC_HDMIRES_BRIDGE videolight_power_link_default_ok=1
  pmic_5v_900ma_guard_ok=1 af_illuminator_still_only_ok=1
  hdmi_res_log_1080p_downshift_ok=1 videolight_pmic_hdmires_ok=1
  slot1_vault_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `95` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed Movie/`S&Q` `AF Illuminator`、飞行模式蓝牙授时、PMIC 5V 过载与 Log `2160p` 拦截（`r59b`）
```text
FX6_R59_AF_ILLUM_BT_PMIC_HDMI_GUARD movie_af_illum_rc=-95 sq_af_illum_rc=-95
  af_illuminator_movie_sq_fire_events=0 bt_sync_airplane_rc=-1
  bt_sync_under_airplane_events=0 passive_tx_bytes_emitted=0
  pmic_5v_overload_rc=-95 pmic_5v_overcurrent_events=0
  log_2160p_bypass_rc=-16 log_2160p_hdmi_bypass_events=0
  legacy_mf_assist_rc=-2 legacy_dt_setup_rc=-2 hdmi_overlay_bake_rc=-1
  hdmi_clean_feed_baked_overlay_pixels=0 e_nd_actuator_tx_count=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r59b_ok=1 verify_us=1040377
```

### 2.3 洁净卸载还原原厂与 `16/16 H0 == H3`（`r59c`）
```text
FX6_R59_CLEAN_UNMOUNT_CAMRESET_H0_H3 stock_unmount_restored_ok=1
  wave45_survives_netreset_ok=1 focus_peaking_reset_by_camreset_ok=1
  setup_datetime_vl_hdmi_survive_camreset_ok=1
  initialize_restores_all_wave45_defaults_ok=1
  hdmi_clean_feed_baked_overlay_pixels=0 passive_tx_bytes_emitted=0
  pmic_5v_overcurrent_events=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 emmc_write_count=0
  r59c_ok=1 verify_us=327338
```

---

## 3. `r59a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r59a` Alpha（`26.21 KiB` / `26,842 B`） | `r59a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r59a Big6 Alpha](assets/r59a-focus-mag-videolight-big6-schinese-alpha.png) | ![r59a Big6 Composited](assets/r59a-focus-mag-videolight-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `[Focus Magnifier]` `Custom Button 5` 物理按键触发、`[Auto Magnifier in MF]=[On]` 镜头对焦环转动自动放大、照片/视频各自独立 `[Initial Focus Mag.]`（`x1.0`/`x4.0`）以及 `[Peaking Display]` 外接 HDMI 零叠加隔离。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 RTC 备电保持与 BLE 共存台架：验证 `[Area/Date/Time Setting]` 跨 `[Camera Settings Reset]` 保留以及 `[Airplane Mode]=[On]` 下 Creators' App 蓝牙零射频静默。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 MI-Shoe `HVL-LBPC` LED 补光灯 PMIC 5V `<= 900 mA` 负载（`[Video Light Mode]` 四档及仅限照片 `[AF Illuminator]`）与外接 Atomos/监视器 HDMI 分析仪实测（`[HDMI Resolution]` `Auto`/`2160p`/`1080p`/`1080i` 与 Log 内录 `1080p` 降档）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 59A (94th Live Run): Wave-45 Focus Assistant + Area/Date/Time Zero-RF + Video Light PMIC 5V + HDMI Resolution + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 59 --r59-mode focus_mag_datetime_videolight_hdmires_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round59-focus-mag-datetime-videolight-hdmires-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r59-runs/r59a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r59a-focus-mag-videolight-big6-schinese \
  --export-png-dir reports/2026-11-17-round59-realhw-focus-mag-datetime-videolight-hdmires-qemu/assets

# Run 59B (95th Live Run): Fail-Closed Movie/S&Q AF Illuminator, Airplane BT Time-Sync, MI-Shoe >900mA PMIC, & Log 2160p Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 59 --r59-mode af_illum_bt_sync_pmic_5v_hdmi_2160p_guard --lang en \
  --run-id round59-af-illum-bt-sync-pmic-5v-hdmi-2160p-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r59-runs/r59b

# Run 59C (96th Live Run): Clean Unmount Stock FX3 Restoration, Reset Tiers & 16/16 H0 == H3 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 59 --r59-mode clean_unmount_camreset_vs_init_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round59-clean-unmount-camreset-vs-init-h0-h3-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r59-runs/r59c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
