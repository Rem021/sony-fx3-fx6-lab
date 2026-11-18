# Round 63（`36/36` 轮实机内核预演 · Wave-49 / `R28..R63` `36/36` 实机预演轮次 · 第 `106..108` 次实跑 -> `108/108` 总实跑 · `72/72` 张 Big-6 PNG）：FX3 7.02 原厂内核真机准备预演 — 静态 `[Image Quality Settings]`（`RAW` `Compressed`/`Uncompressed` vs 沉睡 `Lossless Comp`、10-bit `HEIF 4:2:0`/`4:2:2`、`[HLG Still Image]` vs 无拍照 FX6）、`[Color Space]`（`sRGB` `DSC` vs `AdobeRGB` `_DSC` 与 `[Set File Name]` 首字符禁用下划线）、双模式 `[Shutter Type]`（`Mechanical`/`Electronic` 无 `Auto`）+ `NR` + `10 fps` `Drive Mode` + `Slot-1` Tier-0 隔离库

> **日期**：2026-11-17 | **轮次**：**Round 63 (Wave-49 · `36/36` Real-HW Rounds · `106th..108th` Live Runs -> `108/108` Total Live Runs, `72/72` PNGs)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r63a` / `r63b` / `r63c`，正式达成 **`R28..R63` `36/36` 轮实机内核预演**、**第 `106..108` 次 -> `108/108` 次独立实跑**、**`72/72` 张 `< 50 KiB`（本轮 `<= 27,467 B`：`26,842 B` 与 `27,147 B`）PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 `.ARW` / `.HIF` (`HEIF` 4:2:0 / 4:2:2 10-bit) / `HLG Still Image` EXIF 与 `BT.2100` 元数据、存储卡 `DCF` 文件名 `DSC`/`_DSC` 与 `[Set File Name]`、以及物理快门帘幕 `1/250 s` 闪光同步、>=1s `[Long Exposure NR]` 与 `10 fps Hi+` 连拍台架实测尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 63 轮 `36/36` 实机预演（Wave-49 · `36/36` 实机轮次 / `106th..108th` -> `108/108` 次实跑 / `72/72` PNG）三项实机预演总览（`r63a` / `r63b` / `r63c`）

| 实跑场景 | Run ID | `r63_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **63A（第 106 次实跑）：Wave-49 静态画质（`RAW`/10-bit `HEIF`/`[HLG Still Image]`）、`[Color Space]` `DSC`/`_DSC` + `[Set File Name]`、双模式 `[Shutter Type]`/`NR`/`10 fps` + Big-6 Home** | `r63a` | `still_raw_heif_colorspace_shutter_drive_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：(1) 核验 **`[Image Quality Settings]`**（`_f.uxc 0x59ec`）：`[RAW File Type]`（`0xe4fb`）仅暴露 **`Compressed` 与 `Uncompressed`**，沉睡 Alpha 字符串 `Lossless Comp` / `(L)/(M)/(S)` 均拒绝为 **`-95 EOPNOTSUPP`**（`lossless_comp_bypass_events=0`）；`[JPEG/HEIF Switch]`（`0xe515`）支持 `JPEG` vs `10-bit HEIF(4:2:0)` / `HEIF(4:2:2)`；`[HLG Still Image]`（`0x67ba`）仅在 `HEIF` 单格式 + `P/A/S/M` + `PP=Off` 下激活 `BT.2100`/`BT.2020` 并锁定 `Creative Look`/`DRO`/`DRO Bracket`，对比无静态拍照管线的 `ILME-FX6`（`-2 ENOENT`）；(2) 核验 **`[Color Space]`**（`0xe4fa`：`sRGB` 前缀 `DSC` vs `AdobeRGB` 自动首字符置 `_` 得 **`_DSC0001.JPG`** / `_A_30042.ARW`）与 **`[Set File Name]`**（`0xe6d6`）**首字符禁用 `_`**（`-22 EINVAL`，跨 `[Camera Settings Reset]` 保留，仅 `[Initialize]` 复位）；(3) 核验 **2 模式 `[Shutter Type]`**（`0xe4fc` 仅 **`Mechanical Shutter`** 与 **`Electronic Shutter`**，无 Alpha 3 模式 `Auto` -> `-95 EOPNOTSUPP`），`[Silent Mode]=On` 强制 `Electronic Shutter`（与 `Interval` 独立），闪光灯（上限 `1/250 s`）与 `BULB` 强制依赖 `Mechanical Shutter`，`[Long Exposure NR]`（`>=1s`）与 `[High ISO NR]`（`RAW` 锁定），8 模式 `[Drive Mode]`（`Hi+` `10 fps`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r63_init_ok=1`, `r63_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.28s` | [`r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png`](assets/r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png) |
| **63B（第 107 次实跑）：Fail-Closed Wave-49 防火墙 — 沉睡无损压缩 `RAW`、未达前置 `HLG Still`、`Set File Name` 首字符 `_`、`Auto` 快门伪造与 `Slot-1` 只读拦截** | `r63b` | `still_raw_heif_colorspace_shutter_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截沉睡 `Lossless Comp` 基础态及 `L`/`M`/`S` 变体（`lossless_base/l/m/s_rc=-95 EOPNOTSUPP`）、`ILME-FX6` 静态拍照伪造（`fx6_still_rc=-2 ENOENT`）与 `JPEG`/`RAW+HEIF`/`PP!=Off`/`DRO Bracket` 下解锁 `[HLG Still Image]`（`-16 EBUSY`）；(2) 拦截 `[Set File Name]` 首字符 `_`（`leading_under_dsc_rc=-22`, `leading_under_abc_rc=-22`）及小写字母非法前缀（`lowercase_prefix_rc=-22 EINVAL`）；(3) 拦截沉睡 3 模式 **`Auto` `[Shutter Type]`**（`auto_shutter_rc=-95`）、伪造 `1/320s` 闪光同步（`flash_320_spoof_rc=-22`）、`Electronic Shutter` 闪光（`eshutter_flash_rc=-95`）、`Silent`/`Cont.` 下解锁 `[Long Exposure NR]`（`-16`）与纯 `RAW` 下篡改 `[High ISO NR]`（`-16`）；(4) 拦截对只读 **`Slot-1` Tier-0 隔离库** 的静态 `.ARW`/`.HIF` 连拍写入（`slot1_still_raw_erofs_rc=-30 EROFS`, `slot1_still_write_events=0`, `slot1_vault_sha256_match=1`, `emmc_write_count=0`, `r63b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.36s` | — |
| **63C（第 108 次实跑 · 闭环）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-49 复位层级（`Set File Name` / `e-Front Curtain` 豁免）+ `AdobeRGB` `_DSC` + `16/16 H0 == H3`** | `r63c` | `clean_unmount_still_reset_h0_h3_big6` | Native ARM64 Wave-49 联合预演（**第 `63` 轮 / `36/36` 实机轮次 · 第 `108/108` 次独立实跑闭环**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 将 `RAW`/`HEIF`/`HLG`/`Color Space`/`Shutter Type`/`Silent`/`LENR`/`High ISO NR`/`Drive` 复位为出厂默认，而 **`[Set File Name]` 与 `[e-Front Curtain Shut.]` 跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_filename_efront_ok=1`），仅 `[Initialize]` 将其恢复默认 `DSC` / `On`（`initialize_restores_filename_efront_ok=1`）；实证 `AdobeRGB` 对标准 `DSC` 与自定义 `FX3` 稳定输出 `_DSC0001.JPG` / `_FX30007.JPG`（`adobergb_underscore_dcf_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.09s` | 同 `63A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-49 三大支柱初始化与 Stage-B 桥接（`r63a` — 第 106 次实跑）
```text
FX6_R63_WAVE49_INIT fx3_wave49_nodes_ok=1 uxc_tokens_ok=1
  still_raw_heif_hlg_ok=1 colorspace_dsc_ban_ok=1
  shutter_nr_drive_ok=1 lossless_dormant_rc=-95
  fx6_still_less_rc=-2 leading_under_ban_rc=-22
  auto_shutter_rc=-95 high_iso_nr_raw_lock_rc=-16
  p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  lossless_comp_bypass_events=0 leading_underscore_prefix_events=0
  auto_shutter_type_bypass_events=0 slot1_still_write_events=0
  passive_tx_bytes_emitted=0 cnflasha_writes=0
  e_nd_actuator_tx_count=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r63_init_ok=1 verify_us=771688

FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE raw_2mode_no_lossless_ok=1
  jh_heif_420_422_10bit_ok=1 hlg_still_bt2100_fx6_enoent_ok=1
  still_raw_heif_hlg_ok=1 lossless_comp_bypass_events=0
  emmc_write_count=0 r63_bridge_ok=1

FX6_R63_COLORSPACE_FILENAME_BRIDGE srgb_dsc_vs_adobergb_udsc_ok=1
  set_filename_leading_under_ban_ok=1 camreset_preserves_prefix_efront_ok=1
  colorspace_filename_ok=1 leading_underscore_prefix_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R63_SHUTTER_2MODE_NR_DRIVE_BRIDGE shutter_2mode_no_auto_ok=1
  silent_flash_bulb_lenr_hisor_lock_ok=1 drive_8mode_hi_plus_10fps_slot1_erofs_ok=1
  shutter_2mode_nr_drive_ok=1 auto_shutter_type_bypass_events=0
  slot1_still_write_events=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `103` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed 沉睡 `Lossless Comp`、首字符 `_` 禁令、2 模式快门与 `Slot-1` 隔离拦截（`r63b` — 第 107 次实跑）
```text
FX6_R63_WAVE49_GUARD lossless_base_rc=-95 lossless_l_rc=-95
  lossless_m_rc=-95 lossless_s_rc=-95 fx6_still_rc=-2
  hlg_under_jpeg_rc=-16 hlg_under_raw_heif_rc=-16
  hlg_under_pp_rc=-16 dro_bracket_under_hlg_rc=-16
  leading_under_dsc_rc=-22 leading_under_abc_rc=-22
  lowercase_prefix_rc=-22 auto_shutter_rc=-95
  flash_320_spoof_rc=-22 eshutter_flash_rc=-95
  lenr_under_silent_rc=-16 lenr_under_cont_rc=-16
  high_iso_nr_raw_rc=-16 slot1_still_raw_erofs_rc=-30
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  lossless_comp_bypass_events=0 leading_underscore_prefix_events=0
  auto_shutter_type_bypass_events=0 slot1_still_write_events=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r63b_ok=1 verify_us=825114
```

### 2.3 洁净卸载还原原厂、Wave-49 复位不对称、`AdobeRGB` `_DSC` 与 `16/16 H0 == H3`（`r63c` — 第 108 次实跑）
```text
FX6_R63_CLEAN_UNMOUNT_STILL_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_filename_efront_ok=1 adobergb_underscore_dcf_ok=1
  initialize_restores_filename_efront_ok=1 lossless_comp_bypass_events=0
  leading_underscore_prefix_events=0 auto_shutter_type_bypass_events=0
  slot1_still_write_events=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0
  r63c_ok=1 verify_us=367987
```

---

## 3. `r63a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r63a` Alpha（`26.21 KiB` / `26,842 B`） | `r63a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r63a Big6 Alpha](assets/r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-alpha.png) | ![r63a Big6 Composited](assets/r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）实拍静态样张读写与 EXIF/Box 解析台架（验证 `[RAW File Type]` 仅暴露 `Compressed`/`Uncompressed` 而无 Alpha `Lossless Comp`、`[JPEG/HEIF Switch]` 10-bit `HEIF 4:2:0`/`4:2:2` `.HIF` 编码、以及 `[HLG Still Image]=On` 下 `BT.2100`/`BT.2020` 元数据与与无拍照管线 `ILME-FX6` 的差异）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）存储卡 `DCIM/100MSDCF` 文件名与菜单输入法实测（验证 `[Color Space]=sRGB` 下 `DSC` vs `AdobeRGB` 下 `_DSC` 首字符加 `_` 规则、`[Set File Name]` 首字符禁用 `_`，以及 `[Camera Settings Reset]` 后保留自定义前缀与 `[e-Front Curtain Shut.]`）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学与机械快门台架（验证仅 `Mechanical Shutter`/`Electronic Shutter` 两模式、`[Silent Mode]=On` 强制切换、`1/250 s` 机械闪光同步上限与 `BULB` 锁定、`>= 1 s` `[Long Exposure NR]` 等长暗场扣减、`[High ISO NR]` `RAW` 免疫与 `10 fps` `Cont. Shooting: Hi+` 连拍对实际写入卡槽的影响）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 63A (106th Live Run): Wave-49 Still RAW/HEIF/HLG + Color Space/Set File Name + 2-Mode Shutter/NR/10fps Drive + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 63 --r63-mode still_raw_heif_colorspace_shutter_drive_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r63a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round63-qemu/r63a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r63a-raw-heif-colorspace-shutter-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/assets

# Run 63B (107th Live Run): Fail-Closed Dormant Lossless RAW, Underscore Prefix Ban, Auto Shutter Spoof & Slot-1 Tier-0 Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 63 --r63-mode still_raw_heif_colorspace_shutter_guard --sd-manifest-mode valid --lang en \
  --run-id r63b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round63-qemu/r63b

# Run 63C (108th Live Run — 36/36 Real-HW Closure): Clean Unmount Stock FX3 Restoration, Reset Tiers + AdobeRGB _DSC + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 63 --r63-mode clean_unmount_still_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r63c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round63-qemu/r63c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`lossless_comp_bypass_events == 0`、`leading_underscore_prefix_events == 0`、`auto_shutter_type_bypass_events == 0`、`slot1_still_write_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
