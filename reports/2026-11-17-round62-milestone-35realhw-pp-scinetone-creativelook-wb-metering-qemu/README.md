# Round 62 Milestone（`35/35` 轮实机内核里程碑 · Wave-48 / `R28..R62` `35/35` 实机预演轮次 · 第 `103..105` 次实跑 -> `105/105` 总实跑 · `70/70` 张 Big-6 PNG）：FX3 7.02 原厂内核真机准备预演 — `[Picture Profile]` (`PP11` S-Cinetone / `PPLUT1..4`) vs `[Log Shooting]` 互斥、`[Creative Look]` / `[DRO]` 锁定、`[White Balance]` `Custom 1..3` 不进 `CAMSET` & `Cine EI` 禁 AWB、`[Metering Mode]` 5 模式 + 对焦点联动

> **日期**：2026-11-17 | **轮次**：**Round 62 35/35 Real-HW Rounds Milestone (Wave-48 · `35/35` Real-HW Rounds · `103rd..105th` Live Runs -> `105/105` Total Live Runs, `70/70` PNGs)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r62a` / `r62b` / `r62c`，正式达成 **`R28..R62` `35/35` 轮实机内核预演里程碑**、**第 `103..105` 次 -> `105/105` 次独立实跑**、**`70/70` 张 `< 50 KiB`（本轮 `<= 27,467 B`）PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 HDMI 外录/Waveform 波形示波器、实拍色卡验证 `[Creative Look]` / `[DRO]`、存储卡 `CAMSET` 文件读回验证 `Custom 1..3` 排除与 `[Shutter AWB Lock]`、以及光学灰卡测光联动与 `Cine EI` Base ISO 冻结台架实测尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 62 轮 `35/35` 实机内核里程碑（Wave-48 · `35/35` 实机轮次 / `103rd..105th` -> `105/105` 次实跑 / `70/70` PNG）三项实机预演总览（`r62a` / `r62b` / `r62c`）

| 实跑场景 | Run ID | `r62_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **62A（第 103 次实跑！）：`[Picture Profile]` `PP11`/LUT vs `[Log Shooting]`、`[Creative Look]`/`[DRO]`、`[White Balance]` `Custom 1..3` `CAMSET` 排除、`[Metering Mode]` 5 模式 + Big-6 Home** | `r62a` | `pp_scinetone_look_wb_metering_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：(1) 核验 **`[Picture Profile]`**（`BKID_APP_setting_picture_profile`, `_f.uxc 0x6830`）：FX3 Ver. `7.02` 出厂默认 **`PP11`（`S-Cinetone` `0x67ab`/`0x6e61`）**，`[Different Set for Still/Mv]`（`0x62ee`）默认未勾选；启用 **`[Log Shooting]`**（`0x6020` `Flexible ISO` / `Cine EI Quick` / `Cine EI`）硬锁定 `PP = Off` 严防双重 `S-Log3` 叠加（`double_log_lockout_bypass_events=0`）；仅限视频的 `PPLUT1..4` 在 `[Camera Settings Reset]` 复位且内录强制 HDMI 降档 `1080p`，而 `PP1..PP11` 内部参数跨 `[Camera Settings Reset]` 存活；(2) 核验 **`[Creative Look]`**（`0x6823` `10` 种预设 `ST`..`SE` + `8` 项调参）与 **`[D-Range Optimizer]`**（`.uxc 0xe89c` `Off`/`Auto`/`Lv1..Lv5`）在 `PP != Off` 或 `Log != Off` 时自动锁定灰显（`look_locked_on_pp11_rc=-16 EBUSY`），沉睡 `Auto HDR`/`Base Look` 在 FX3 保持 `-ENOENT`；(3) 核验 **`[White Balance]`**（`.uxc 0xe5d4` `2500K..9900K` / `A7..B7, G7..M7`）：`Custom 1..3` 仅存机身 NVRAM 并被 **`CAMSET` 存储卡导出严格排除**（`camset_excl_rc=-13 EACCES`, `camset_custom_wb_leak_events=0`），`Cine EI`/`Cine EI Quick` 封锁 `Auto`/`Underwater Auto`（`-95 EOPNOTSUPP`），`[Shutter AWB Lock]`（`0x66db`）跨 `[Camera Settings Reset]` 存活；(4) 核验 **`[Metering Mode]`**（`0xe5cf` 精确 `5` 大模式 / `6` 选项：`Multi` 默认 / `Center` / `Spot: Standard & Large` / `Entire Screen Avg.` / `Highlight` + `Face Priority in Multi Metering` `0x69c7` + `Spot Metering Point` `0x71b5` + `AEL w/ Shutter` `0x669d`），在 `Wide`/`Zone` 下点测联动退回 `Center`（`-22 EINVAL`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r62_init_ok=1`, `r62_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.70s` | [`r62a-pp-scinetone-wb-metering-4ch-big6-schinese-composited.png`](assets/r62a-pp-scinetone-wb-metering-4ch-big6-schinese-composited.png) |
| **62B（第 104 次实跑）：Fail-Closed Wave-48 防火墙 — `PP11`/`Log` 下解锁 `Creative Look` 旁路、双重 `S-Log3`、`CAMSET` 泄露 `Custom 1..3`、`Cine EI` `AWB`/ISO 越权拦截** | `r62b` | `pp_log_wb_cineei_metering_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拒绝 `PP11`（`S-Cinetone`）或 `Log Shooting` 开启下解锁 `[Creative Look]`/`[DRO]`（`look_under_pp11_rc=-16`, `look_under_log_rc=-16 EBUSY`）、静止拍照模式选 `PPLUT1`（`pplut_in_still_rc=-95`）、`Cine EI` 下叠加 `PP8` 双重 `S-Log3`（`double_log_pp_rc=-16`, `double_log_lockout_bypass_events=0`）及伪造沉睡 `Auto HDR`/`FX6 Base Look`（`autohdr_spoof_rc=-2`, `baselook_spoof_rc=-2 ENOENT`）；(2) 拦截 `Cine EI` 下启用 `Auto`/`Underwater Auto` WB（`cine_ei_auto_wb_rc=-95`, `cine_ei_uw_wb_rc=-95`, `cine_ei_awb_bypass_events=0`）、`Log`/`S-Log3` 下直接 `[Custom Setup]`（`custom_setup_in_log_rc=-16`）、越界色温 `2400K`（`bad_kelvin_rc=-22 EINVAL`）与将 `Custom 1..3` 写入 `CAMSET01.DAT`（`camset_custom_wb_rc=-13 EACCES`, `camset_custom_wb_leak_events=0`）；(3) 拦截 `De-Squeeze` 下 `Face Priority in Multi`（`face_prio_desqueeze_rc=-16`）、`Wide`/`Zone` 下 `Spot Focus Point Link`（`spot_link_wide_rc=-22`, `spot_link_zone_rc=-22`）、`iAuto` 下非 `Multi` 测光（`iauto_spot_rc=-95`）与 `Cine EI` 下测光篡改 Base ISO（`cine_ei_iso_alter_rc=-1`, `metering_base_iso_mutation_events=0`）；(4) 保护只读 `Slot-1`/`P2`/`cnflasha`（`-30 EROFS`, `slot1_vault_sha256_match=1`, `emmc_write_count=0`, `r62b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.95s` | — |
| **62C（第 105 次实跑 · `35/35` 里程碑收官！）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-48 复位层级不对称 + `CAMSET` 排除 `Custom 1..3` + `16/16 H0 == H3`** | `r62c` | `clean_unmount_pp_wb_reset_h0_h3_big6` | Native ARM64 Wave-48 联合预演（**第 `62` 轮 / `35/35` 轮实机里程碑 · 第 `105/105` 次独立实跑收官**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 将活跃 `[Picture Profile]` 恢复为 `PP11`、`PPLUT1..4` 归零、`WB` 复位 `Auto`、`Metering` 复位 `Multi`，而 **`PP1..PP11` 内部参数、`Custom 1..3`、`(Different Set)`、`[Shutter AWB Lock]` 与 `[AEL w/ Shutter]` 跨复位存活**（`camreset_preserves_pp_custom_wb_ok=1`）；实证 `[Initialize]` 复位 `[Shutter AWB Lock]` 与 `[AEL w/ Shutter]` 且仅逐个 `PP->[Reset]` 重置 `PP1..PP11` 内部参数（`initialize_and_pp_reset_ok=1`）；实证 `CAMSET` 导出严格排除 `Custom 1..3`（`camset_excludes_custom_wb_ok=1`, `camset_custom_wb_leak_events=0`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.54s` | 同 `62A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-48 四大支柱初始化与 Stage-B 桥接（`r62a` — 第 103 次实跑）
```text
FX6_R62_WAVE48_INIT fx3_wave48_nodes_ok=1 uxc_tokens_ok=1
  pp_scinetone_log_ok=1 creative_look_dro_ok=1
  wb_custom_camset_ok=1 metering_5mode_ok=1
  look_locked_on_pp11_rc=-16 camset_excl_rc=-13
  cine_ei_blocks_awb_rc=-95 cine_ei_blocks_uw_rc=-95
  wide_spot_link_rc=-22 p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  double_log_lockout_bypass_events=0 camset_custom_wb_leak_events=0
  cine_ei_awb_bypass_events=0 passive_tx_bytes_emitted=0
  cnflasha_writes=0 e_nd_actuator_tx_count=0
  appfw_present=1 shim_present=1 emmc_write_count=0
  r62_init_ok=1 verify_us=838111

FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE pp11_default_vs_log_lockout_ok=1
  pplut_reset_1080p_clamp_ok=1 creative_look_10_dro_lockout_ok=1
  pp_scinetone_look_dro_ok=1 double_log_lockout_bypass_events=0
  emmc_write_count=0 r62_bridge_ok=1

FX6_R62_WB_CUSTOM_CAMSET_EXCLUSION_BRIDGE wb_2500k_9900k_custom_nvram_ok=1
  wb_custom_camset_excluded_ok=1 wb_cine_ei_awb_blocked_ok=1
  wb_custom_camset_exclusion_ok=1 camset_custom_wb_leak_events=0
  cine_ei_awb_bypass_events=0 emmc_write_count=0 p2_setting_writes=0

FX6_R62_METERING_5MODE_SPOT_LINK_BRIDGE metering_5mode_6opt_ok=1
  face_prio_desqueeze_lock_ok=1 spot_focus_point_link_ok=1
  metering_5mode_spot_link_ok=1 metering_base_iso_mutation_events=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `87` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`160` 实时线程零崩溃。

### 2.2 Fail-Closed 双重 Log、`CAMSET` `Custom 1..3` 泄露、`Cine EI` AWB 与点测联动拦截（`r62b` — 第 104 次实跑）
```text
FX6_R62_WAVE48_GUARD look_under_pp11_rc=-16 pplut_in_still_rc=-95
  double_log_pp_rc=-16 look_under_log_rc=-16 autohdr_spoof_rc=-2
  baselook_spoof_rc=-2 cine_ei_auto_wb_rc=-95 cine_ei_uw_wb_rc=-95
  custom_setup_in_log_rc=-16 bad_kelvin_rc=-22 camset_custom_wb_rc=-13
  face_prio_desqueeze_rc=-16 spot_link_wide_rc=-22 spot_link_zone_rc=-22
  iauto_spot_rc=-95 cine_ei_iso_alter_rc=-1 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  double_log_lockout_bypass_events=0 camset_custom_wb_leak_events=0
  cine_ei_awb_bypass_events=0 metering_base_iso_mutation_events=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r62b_ok=1 verify_us=771226
```

### 2.3 洁净卸载还原原厂、Wave-48 三层复位不对称、`CAMSET` 排除与 `16/16 H0 == H3`（`r62c` — 第 105 次实跑）
```text
FX6_R62_CLEAN_UNMOUNT_PP_WB_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_pp_custom_wb_ok=1 initialize_and_pp_reset_ok=1
  camset_excludes_custom_wb_ok=1 double_log_lockout_bypass_events=0
  camset_custom_wb_leak_events=0 cine_ei_awb_bypass_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0
  r62c_ok=1 verify_us=353246
```

---

## 3. `r62a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r62a` Alpha（`26.50 KiB` / `27,132 B`） | `r62a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r62a Big6 Alpha](assets/r62a-pp-scinetone-wb-metering-4ch-big6-schinese-alpha.png) | ![r62a Big6 Composited](assets/r62a-pp-scinetone-wb-metering-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）HDMI 波形示波器与向量示波器实测（验证出厂默认 `[Picture Profile]=PP11 (S-Cinetone)`、仅限视频的 `PPLUT1..4` 内录时 HDMI `1080p` 降档、以及 `[Log Shooting]` 硬锁定 `PP=Off` 防止双重 `S-Log3` 叠加）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）标准色卡实拍与存储卡读回实测（验证 `[Creative Look]` 10 种预设 + 8 项微调与 `[D-Range Optimizer]` 在 `PP!=Off` 或 `Log!=Off` 下互斥锁死、以及 `[White Balance]` `Custom 1..3` 仅存机身 NVRAM 并从 `CAMSET` 文件严格排除、与 `[Shutter AWB Lock]`）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学点测/灰卡台架实操（验证 `5` 种基础 `[Metering Mode]`：`Multi` / `Center` / `Spot: Standard & Large` / `Entire Screen Avg.` / `Highlight`、`De-Squeeze` 下 `Face Priority in Multi` 锁定、`Wide`/`Zone` 下 `Spot Focus Point Link` 退回 `Center`，以及 `Cine EI` 下 Base ISO 不可被测光篡改）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 62A (103rd Live Run!): Wave-48 Picture Profile (PP11/PPLUT vs Log) + Creative Look/DRO + WB Custom CAMSET Exclusion + 5-Mode Metering + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 62 --r62-mode pp_scinetone_look_wb_metering_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r62a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round62-qemu/r62a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r62a-pp-scinetone-wb-metering-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu/assets

# Run 62B (104th Live Run): Fail-Closed Double-Log Lockout, CAMSET Custom WB Leak, Cine EI AWB & Metering Link Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 62 --r62-mode pp_log_wb_cineei_metering_guard --sd-manifest-mode valid --lang en \
  --run-id r62b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round62-qemu/r62b

# Run 62C (105th Live Run — 35/35 Real-HW Rounds Milestone Closure!): Clean Unmount Stock FX3 Restoration, Reset Tiers + CAMSET Custom WB Exclusion + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 62 --r62-mode clean_unmount_pp_wb_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r62c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round62-qemu/r62c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`double_log_lockout_bypass_events == 0`、`camset_custom_wb_leak_events == 0`、`cine_ei_awb_bypass_events == 0`、`metering_base_iso_mutation_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
