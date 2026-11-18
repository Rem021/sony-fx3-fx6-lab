# Round 60 Milestone（第 60 轮里程碑 · Wave-46 / `R28..R60` 第 33 轮实机内核 QEMU 预演 · 第 99 次实跑！）：FX3 7.02 原厂内核真机准备预演 — `[Power Setting Option]` 现实差异（`Power Save by Monitor` 沉睡枚举）、`[Language]` `BK_LANG` `0x02cf019c` 34 vs 29 与 4 语种对齐、`[Volume Settings]` `0..15` / `[4ch Audio Monitoring]` 及 `[Delete confirm.]` `Slot-1` 保险库保护

> **日期**：2026-11-17 | **轮次**：**Round 60 Milestone Live ARM64 QEMU Rehearsal (60th Round Milestone / Wave-46 · 33rd Real-HW Round / 99th Live Run!)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r60a` / `r60b` / `r60c`，累计达成 `R28..R60` **第 `60` 轮里程碑 / 第 `33` 轮实机内核预演（`33/33`）**、**第 `99` 次独立实跑（`99/99`）**、**`66` 张 `< 50 KiB`（本轮 `< 28 KiB`）PNG 视觉凭证（`66/66`）**）测得；**物理实体 `ILME-FX3` 机身上实测 LCD 翻折与电池放电功耗、`[Language]` `34` 语种菜单切换、扬声器/`3.5mm` 耳机/`XLR-H1` 实音监听以及 `Slot-1`/`Slot-2` 实体按键 `[Delete confirm.]` / `[Delete pressing twice]` 尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 60 轮里程碑（Wave-46 · 第 33 轮实机预演 / 第 99 次实跑）三项实机预演总览（`r60a` / `r60b` / `r60c`）

| 实跑场景 | Run ID | `r60_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **60A：`[Power Setting Option]` 现实差异、`[Language]` `0x02cf019c`、`[Volume Settings]`/`[4ch Audio Monitoring]`、`[Delete confirm.]` + Big-6 Home** | `round60-power-save-monitor-lang-vol-delete-big6` | `power_save_monitor_lang_vol_delete_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：(1) 核验 **`[Power Setting Option]` 现实差异**：`ILME-FX3 Ver. 7.02` (`ilc/2210`) UI 仅暴露 **`[Power Save Start Time]`**（`Off`/`30 Min`/`5 Min` 默认/`2 Min`/`1 Min`/`10 Sec`）与 **`[Auto Power OFF Temp.]`**（`Standard` 默认/`High`），而共享 `appFw.so`/`string_*_f.uxc` 保留未暴露的 `0x60b9` **`[Power Save by Monitor]`** 4 选项（`0x6db5` `Both Linked` / `0x6db6` `Open: Return` / `0x60a8` `Close: Power Save` / `0x6b2e` `Does Not Link`，无虚构 `"Open: On/Close: Off"`）及 **9 项自动休眠解除条件**；(2) 核验 **`[Language]`**：`BK_LANG 0x02cf019c` 四语映射（`0x00 EN`、`0x19 ZH-CN`、`0x18 ZH-TW`、`0x01 JA`）、`FX3 34` 套 vs `FX6 29` 套 `.uxc` 语言包差异，以及跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活（仅 `[Initialize]` 清零重提示）；(3) 核验 **`[Volume Settings]`**（`0..15` 16 档，默认 `7`）+ **`[4ch Audio Monitoring]`**（`CH1/CH2` 默认、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2` 五路监听，`3.5mm` 仅支持 2ch 立体声）+ **`[Delete confirm.]`**（`"Cancel" first` 默认 vs `"Delete" first`，伴随 `[Delete pressing twice]` 默认 `Off`）；(4) `p2:/setting`、`cnflasha` 与 `Slot-1` 恢复保险库全程只读锁定（`rc=-30`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r60_init_ok=1`, `r60_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.64s` | [`r60a-language-volume-4ch-big6-schinese-composited.png`](assets/r60a-language-volume-4ch-big6-schinese-composited.png) |
| **60B：Fail-Closed 非法注入防火墙 — 沉睡 `Power Save by Monitor` 强制休眠、`Slot-1` 双击/`"Delete"` 优先擦除、`Backup.bin` 持久化与 `4ch` 耳机旁路拦截** | `round60-dormant-monitor-sleep-slot1-delete-guard` | `dormant_monitor_sleep_slot1_delete_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 Tier-0 `p3` 空冷电池转储期间触发沉睡 `Power Save by Monitor` 合屏强制休眠（`dormant_mon_sleep_rc=-95 EOPNOTSUPP`）及 `5 Min` 空闲休眠（`p3_airgap_5min_rc=-16 EBUSY`, `dormant_monitor_forced_sleep_events=0`）；(2) 拒绝 `ILME-FX3` 未暴露菜单 `"Power Save by Monitor"` 与虚构项 `"Open: On/Close: Off"`（`unexposed_mon_menu_rc=-2 ENOENT`, `hallucinated_open_on_rc=-2 ENOENT`）；(3) 拦截超出 `[0..15]` 的音量 `-1`/`16`（`vol_neg1_rc=-22`, `vol_16_rc=-22 EINVAL`）及 `3.5mm` 耳机 4ch 离散输出伪造（`headphone_4ch_bypass_events=0`）；(4) 拦截以 `Slot-1` 只读恢复保险库（`pnflasha`/`cnflasha`/`CAMSET01.DAT`/`BODYDATA.DAT`）为目标的 `"Delete" first`、`Delete pressing twice` 与 `Format` 擦除请求（`slot1_del_first_rc=-30`, `slot1_del_twice_rc=-30`, `slot1_format_rc=-30 EROFS`, `slot1_vault_delete_events=0`, `slot1_vault_sha256_match=1`）；(5) 拦截 `Backup.bin` 持久化写入（`persistent_nvram_rc=-30 EROFS`, `persistent_nvram_write_events=0`, `p2_write_blocked_rc=-30`, `cnflasha_ro_blocked_rc=-30`, `emmc_write_count=0`, `r60b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.55s` | — |
| **60C：洁净卸载 `/tmp` Stage-B 覆盖层 + `[Camera Settings Reset]` vs `[Reset Network Set.]` vs `[Initialize]` + `16/16 H0 == H3`（第 60 轮里程碑 / 第 33 轮 / 第 99 次实跑收官）** | `round60-clean-unmount-reset-tiers-h0-h3-big6` | `clean_unmount_reset_tiers_h0_h3_big6` | Native ARM64 Wave-46 联合预演（**第 `60` 轮里程碑 · 第 `33` 轮实机内核预演 / 第 `99` 次独立实跑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；验证 4 语 `BK_LANG 0x02cf019c` 与 FX3 `34` vs FX6 `29` 语言包对齐（`lang_4way_34vs29_ok=1`）；实证 `[Language]`、`[Power Setting Option]`、`[Volume Settings]`、`[4ch Audio Monitoring]`、`[Delete confirm.]` 及 `[Delete pressing twice]` **同时跨 `[Reset Network Set.]`（`wave46_survives_netreset_ok=1`）与 `[Camera Settings Reset]`（`wave46_survives_camreset_ok=1`）完整存活**，且**仅在 `[Initialize]` 时全量恢复出厂默认并重触发首次语言向导**（`initialize_restores_all_wave46_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.88s` | 同 `60A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-46 四大支柱初始化与 Stage-B 桥接（`r60a`）
```text
FX6_R60_WAVE46_INIT fx3_wave46_nodes_ok=1 powersave_reality_split_ok=1
  powersave_deactivation_9cond_ok=1 lang_bk_02cf019c_4lang_34vs29_ok=1
  volume_0_15_4ch_5routes_ok=1 delete_confirm_cancel_first_vault_ok=1
  setup_playback_survives_camreset_ok=1 dormant_mon_sleep_blocked_rc=-95
  p3_5min_blocked_rc=-16 vol_oob_blocked_rc=-22 slot1_del_first_rc=-30
  slot1_del_twice_rc=-30 slot1_vault_writes=0 slot1_vault_delete_events=0
  dormant_monitor_forced_sleep_events=0 p2_write_blocked_rc=-30
  p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  cnflasha_writes=0 e_nd_actuator_tx_count=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r60_init_ok=1 verify_us=794173

FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE ilc2210_2items_only_ok=1
  dormant_monitor_4opts_appfw_ok=1 open_return_not_open_on_ok=1
  sleep_deactivation_9cond_ok=1 tier0_p3_airgap_guard_ok=1
  powersave_reality_split_ok=1 dormant_monitor_forced_sleep_events=0
  emmc_write_count=0 r60_bridge_ok=1

FX6_R60_LANG_34_29_PARITY_BRIDGE bk_lang_02cf019c_4way_ok=1
  fx3_34_vs_fx6_29_packs_ok=1 survives_camreset_netreset_ok=1
  reset_on_initialize_only_ok=1 lang_34_29_parity_ok=1
  emmc_write_count=0 p2_setting_writes=0

FX6_R60_VOL_4CH_DELETE_VAULT_BRIDGE volume_0_15_def7_ok=1
  audio_4ch_5routes_ok=1 delete_confirm_cancel_first_ok=1
  delete_twice_off_def_ok=1 slot1_vault_ro_blocked_ok=1
  vol_4ch_delete_vault_ok=1 slot1_vault_delete_events=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `105` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed 沉睡显示器节电、`Slot-1` 擦除与 NVRAM 持久化拦截（`r60b`）
```text
FX6_R60_DORMANT_MON_SLOT1_DEL_GUARD dormant_mon_sleep_rc=-95
  p3_airgap_5min_rc=-16 dormant_monitor_forced_sleep_events=0
  unexposed_mon_menu_rc=-2 hallucinated_open_on_rc=-2
  dormant_4opts_uxc_parity_ok=1 vol_neg1_rc=-22 vol_16_rc=-22
  headphone_4ch_bypass_events=0 slot1_del_first_rc=-30
  slot1_del_twice_rc=-30 slot1_format_rc=-30 slot1_vault_delete_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  persistent_nvram_rc=-30 persistent_nvram_write_events=0
  e_nd_actuator_tx_count=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r60b_ok=1 verify_us=760274
```

### 2.3 洁净卸载还原原厂、复位层级与 `16/16 H0 == H3`（`r60c`）
```text
FX6_R60_CLEAN_UNMOUNT_RESET_H0_H3 stock_unmount_restored_ok=1
  lang_4way_34vs29_ok=1 wave46_survives_netreset_ok=1
  wave46_survives_camreset_ok=1 initialize_restores_all_wave46_defaults_ok=1
  dormant_monitor_forced_sleep_events=0 slot1_vault_delete_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 emmc_write_count=0
  r60c_ok=1 verify_us=374258
```

---

## 3. `r60a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r60a` Alpha（`26.50 KiB` / `27,132 B`） | `r60a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r60a Big6 Alpha](assets/r60a-language-volume-4ch-big6-schinese-alpha.png) | ![r60a Big6 Composited](assets/r60a-language-volume-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测翻转 LCD 屏幕闭合/开启与空冷电池续航休眠行为（验证真机 UI 不暴露 `[Power Save by Monitor]`，以及 `[Power Save Start Time]` 与 9 项自动休眠解除条件的实机供电功耗曲线）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `Setup -> [Area/Date] -> [Language]`（核对 `34` 语种实时切换、`BK_LANG 0x02cf019c` 与 `[Camera Settings Reset]`/`[Reset Network Set.]` 保留特性及 `[Initialize]` 初次向导复现）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测声学与存储实操台架（`[Volume Settings]` `0..15` 默认 `7` 机背单声道扬声器 vs `3.5mm` 立体声耳机回放及 `XLR-H1` 下 `[4ch Audio Monitoring]` 5 路监听切换，以及 `Playback` 下 `Slot-1`/`Slot-2` `[Delete confirm.]` 与 `[Delete pressing twice]` 实体按键交互）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 60A (97th Live Run): Wave-46 Power Save Monitor Split + BK_LANG 34vs29 + Volume/4ch + Delete confirm. + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 60 --r60-mode power_save_monitor_lang_vol_delete_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round60-power-save-monitor-lang-vol-delete-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r60-runs/r60a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r60a-language-volume-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu/assets

# Run 60B (98th Live Run): Fail-Closed Dormant Power Save Monitor Sleep, Slot-1 Delete/Format & NVRAM Persistence Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 60 --r60-mode dormant_monitor_sleep_slot1_delete_guard --sd-manifest-mode valid --lang en \
  --run-id round60-dormant-monitor-sleep-slot1-delete-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r60-runs/r60b

# Run 60C (99th Live Run — 60th Round Milestone!): Clean Unmount Stock FX3 Restoration, Reset Tiers & 16/16 H0 == H3 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 60 --r60-mode clean_unmount_reset_tiers_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round60-clean-unmount-reset-tiers-h0-h3-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r60-runs/r60c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`slot1_vault_delete_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
