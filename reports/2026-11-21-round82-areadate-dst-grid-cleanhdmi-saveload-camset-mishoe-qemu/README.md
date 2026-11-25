# Round 82（Wave-68 · **`55/55` 实机预演轮次 `R28..R82` · 第 `163..165` 次实跑 -> `165/165` 总实跑 · `110/110` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `Setup -> [Area/Date]` 30 时区 / `[Daylight Savings]` / `[Date Format]` / `>= 24h` RTC 备电 vs FX6 `Clock Set`、`[Grid Line Display/Type]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI 隔离 vs FX6 `Monitoring > Marker`、`[Save/Load Settings]` `CAMSET01..10.DAT`（仅 `Slot 1` + `EROFS=30` + 排除清单 + `libSaveLoadSettings.so`）& `Camera Set. Memory`（`1..3` vs `M1..M4`）vs FX6 `All File`，以及无物理 `Sync Terminal` 辟谣 / MI-Shoe `[Video Light Mode]` 与 `XLR-H1` 物理互斥 vs FX6 `TC IN/OUT` BNC & 零 `GENLOCK`

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 82** 三路独立 QEMU 实机预演（`r82a` / `r82b` / `r82c`，正式达成 **`55/55` 实机预演轮次 `R28..R82` · `165/165` 次独立实跑 · `110/110` 张 `<= 27,467 B` PNG 视觉凭证**，`overall_status="PASS"`、`synthetic_fallback=False`），全部 **`crashes == 0`、`emmc_write_count == 0`、`emmc_writes == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`usb_tx_bytes == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`marker_hdmi_pixels_injected == 0`、`camset_excluded_leaked_count == 0`、`dormant_fx3_cr2032_events == 0`、`dormant_fx6_dst_ui_events == 0`、`dormant_fx6_grid3_ui_events == 0`、`dormant_fx3_pro_camera_events == 0`、`dormant_fx6_ref_file_events == 0`、`dormant_fx3_sync_terminal_events == 0`、`dormant_fx6_genlock_events == 0`、`xlrh1_mishoe_mutex_violations == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r82c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r82a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `27,467 B` Composited PNG 与 `27,132 B` Alpha PNG（均严格 `<= 27,467 B`）。
- **核心关联文件**：
  - 情报基线：[Wave 68 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/reports/2026-11-17-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/README.md)
  - 遥测汇总：[summary.json](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/summary.json)
  - 视觉凭证：[r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png)（`27,467 B`）· [r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png)（`27,132 B`）
  - 源码与测试：[fx6-stage-a-verify.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/outputs/fx6-native-presenter-closure/fx6-stage-a-verify.c) · [libgrm-fbinit9.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/outputs/fx6-native-presenter-closure/libgrm-fbinit9.c) · [build_and_run_round.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/outputs/fx6-native-presenter-closure/build_and_run_round.py) · [test_round82_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_qemu.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h491-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/outputs/fx6-native-presenter-closure/tests/test_round82_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_qemu.py)
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 68 四大支柱门禁、休眠分支辟谣与 `Slot 1` `EROFS=-30` 隔离的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-11 EAGAIN` / `-28 ENOSPC` / `-22 EINVAL` / `-30 EROFS` / `-1 EPERM` 护栏：
  1. **支柱 A（`Setup -> [Area/Date]` vs FX6 `Maintenance > Clock Set`）**：30 个 `AREA_GMT_*` 时区（`GMT_M_11_0..GMT_P_12_0` 含 6 个半小时区，`>= 30` 越界 `-22 EINVAL`）、`[Daylight Savings]`（`Off` 默认/`On` + Sony ELF 原厂错字 `convert_setting_daylight_saving_to_saylight_saving`）、`[Date Format]`（`Y-M-D`/`M-D-Y`/`D-M-Y`）、抗 `[Camera Settings Reset]`（仅 `[Initialize]` 重置并重装初始向导 `37dlg_rec203_initial_setting_controller`）及机身内置可充电 RTC 备电（`>= 24h` 关机充电，不足或放空 `-11 EAGAIN`，无用户可换 CR2032 -> `-95 EOPNOTSUPP`）；对比 FX6 `Maintenance > Clock Set`（`UTC -12:00..+14:00` 30 分钟步进、无 DST UI 开关 `-95`、`12h/24h`、`Backup Battery End` `ns2 0x411f` `-16 EBUSY`）。
  2. **支柱 B（`[Grid Line Display/Type]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI 隔离 vs FX6 `Monitoring > Marker`）**：全管线统一（Still/Movie/S&Q）`[Grid Line Display]`/`[Grid Line Type]`（3 种图案：`Rule of 3rds`/`Square`/`Diag.+Square`，休眠黄金分割 `-95`，`HDMI Info. Display=On` 时透传外部 HDMI，唯 `Off(HDMI Only)` 或 `RAW Output=On` 强制 Clean-Feed 抑制）对比仅限 Movie/S&Q `[Marker Display]`（`Center`/`15-Aspect`/`Safety Zone 80%/90%`/`[Guideframe]`，全部 5 项抗 Reset、`Focus Magnifier` 下隐藏、**绝对 `0` 像素 HDMI 注入** `-95`）；对比 FX6 `Monitoring > Marker`（`Center Marker 1..4/Off`、`Guide Frame`、无 3 模式网格 UI -> `-95`）。
  3. **支柱 C（`[Save/Load Settings]` `CAMSET01..10.DAT` 仅 `Slot 1` & `Camera Set. Memory` `1..3` vs `M1..M4` + Tier-0 `Slot 1 EROFS=30` 防火墙 vs FX6 `All File`）**：真实路径 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`（`FX3 appFw.so` 对 `PRO/CAMERA` 命中 `0` 次 -> `-95`）、`libSaveLoadSettings.so`（同机型 & FW `v2+` 校验、`MR` 模式 `-16 EBUSY`、加载自动重启 `_g 0x62dd`）、硬锁 `Slot 1`（切 `Slot 2` -> `-95`）、10 文件上限（`> 10` -> `-28 ENOSPC`）、官方排除清单（IPTC/Copyright/Ext Flash/Custom WB/Face Memory/全网络与根证书/Language/Area-Date -> `-95`，FTP 走独立 `FTPSET`）、`Camera Set. Memory` 机身 `1..3` vs 存储卡 `M1..M4`（`CAMPR%02d%c.DAT` 可选 `Slot 1/2`），凡指向 Tier-0 `Slot 1` 的写/删请求（`CAMSET`/`CAMPR`/`FTPSET` 协议层与真实 Linux 内核 VFS 层）一律返回 **`-30 EROFS`**（`slot1_data_sector_writes == 0`）；对比 FX6 `Project > All File`（`Media(B)` 64 份 `.ALL`）、`Scene File`（`.SCN`）及休眠 `Reference File`（`-95`）。
  4. **支柱 D（无物理 `Sync Terminal` 辟谣、MI-Shoe `[Video Light Mode]` 与 `XLR-H1` 物理互斥 vs FX6 `TC IN/OUT` BNC & 零 `GENLOCK`）**：辟谣 FX3 无物理 PC 同步端子（`SYNCHRO_TERMINAL* == 0`，休眠 `Flash Sync Spd. Prty.` `_f 0x6b31` & `_g 0x645e` `-95`），Still 机械快门 `1/250 s` MI-Shoe 闪光灯（`< 250 V`，`>= 250 V`/反极性 `-1 EPERM`），`[Video Light Mode]`（`HVL-LBPC` 4 模式含 `Auto`）与独占电气 MI 热靴的 `XLR-H1` 物理/供电双互斥（Accessory Shoe Kit 为纯机械冷靴 -> `-16 EBUSY`，直插遵守 `PMIC 5V <= 900 mA` -> `> 900 mA` `-16 EBUSY`）；对比 FX6 `Video Light Set`（3 模式无 `Auto` -> `-95`）、`TC IN/OUT` BNC（`EXT-LK`）及零 `GENLOCK` BNC（尽管存在 107 条休眠 ELF 符号 -> `-95`）。
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测尚未上电执行，详见 §4。**

> **日期**：2026-11-21 | **轮次**：**Round 82 (`55/55` Real-HW Rounds · Wave-68 · `163rd..165th` Live Runs -> `165/165` Total Live Runs, `110/110` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-68 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/README.md`](../2026-11-17-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 82 轮（Wave-68 · `55/55` 实机轮次 / `163rd..165th` -> `165/165` 次实跑 / `110/110` PNG）三项实机预演总览（`r82a` / `r82b` / `r82c`）

| 实跑场景 | Run ID | `r82_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **82A（第 163 次实跑）：Wave-68 四大支柱 — `Setup -> [Area/Date]` 30 时区/DST/RTC `>=24h` vs FX6 `Clock Set`、`[Grid Line]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI 隔离 vs FX6 `Marker`、`[Save/Load Settings]` `CAMSET01..10.DAT`（仅 `Slot 1` + `EROFS=30` + 排除清单）& `Camera Set. Memory` vs FX6 `All File`、无 `Sync Terminal` 辟谣 / MI-Shoe `[Video Light Mode]` 与 `XLR-H1` 互斥 vs FX6 `TC BNC` & 零 `GENLOCK` + Big-6 Home** | `r82a` | `areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`Setup -> [Area/Date]`** 30 时区、`[Daylight Savings]` + ELF 错字 `saylight`、`[Date Format]` 3 项、抗 Reset、内置 `>= 24h` 可充 RTC 备电与零 CR2032 (`-95`) vs FX6 `Clock Set`（`UTC -12:00..+14:00`、零 DST UI `-95`、`Backup Battery End` `-16`）；(2) 核验全管线 **`[Grid Line Display/Type]`**（3 模式、`HDMI Info=On` 透传 vs `Off(HDMI Only)`/`RAW=On` Clean-Feed 抑制）对比 Movie/S&Q **`[Marker Display]`**（5 项全抗 Reset、`Focus Magnifier` 隐藏、`0` HDMI 像素注入）vs FX6 `Marker`（零 3 模式网格 UI `-95`）；(3) 核验 **`[Save/Load Settings]`** `CAMSET01..10.DAT`（锁 `Slot 1`、`0` 命中 `PRO/CAMERA`、`libSaveLoadSettings.so`、官方排除清单、`Slot 1` 写/删双层 `-30 EROFS`）& `Camera Set. Memory` `1..3`/`M1..M4` vs FX6 `All File`（`Media(B)` 64 份、休眠 `Reference File` `-95`）；(4) 核验无 `Sync Terminal` 辟谣（`SYNCHRO_TERMINAL*==0`）、Still 机械快门 `1/250s` `<250V`、MI-Shoe 4 模式 `[Video Light Mode]` 与 `XLR-H1` 物理互斥（`PMIC 5V <=900 mA`）vs FX6 3 模式 `Video Light Set`、`TC BNC` 及零 `GENLOCK` BNC（107 休眠符号 `-95`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r82_init_ok=1`, `r82_bridge_ok=1`, `verify_us=314778`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `78.87s` | [`r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png`](r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png) / [`r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png`](r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png) |
| **82B（第 164 次实跑）：Fail-Closed Wave-68 防火墙 — FX3/FX6 CR2032 / FX6 DST UI / 黄金分割网格 / Still Marker & Marker HDMI / FX6 3 模式网格 / `PRO/CAMERA` / Save-Load Slot 2 / `CAMSET` 排除项 / Memory CustomKey / FX6 `Reference File` / FX3 `Sync Terminal`-`GENLOCK`-`TC BNC`-Movie Flash / FX6 Video Light `Auto`-Still Flash-`GENLOCK` BNC（`-95`）、FX6 `Backup Battery End` / Grid Clean-Feed / FocusMag Marker / MR 模式 / 电子快门 & `>1/250s` / `XLR-H1` MI-Shoe 互斥 / `PMIC >900 mA`（`-16`）、RTC `<24h`/放空/未设时钟（`-11`）、`CAMSET >10` & FX6 `All File >64`（`-28`）、越界与跨机/`v1.01`/`NULL`（`-22`）、`>=250V`/反极性/`live_attach`（`-1`）及 `Slot 1`（`CAMSET` Save-Delete/`CAMPR`/`FTPSET`/FX6 `All File` 协议与真实 VFS/`P12`/`P2`/`cnflasha` `-30 EROFS`）** | `r82b` | `wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard` | Native ARM64 Fail-Closed 注入阻断实测：60 项故障注入全部命中精确 POSIX `errno`（`-95`/`-16`/`-11`/`-28`/`-22`/`-30`/`-1`），实证 `slot1_vault_sha256_match=1`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `emmc_write_count=0`, `cnflasha_writes=0`, `r82b_ok=1`, `verify_us=944362`, `FX6_R82_WAVE68_GUARD_RC=0` | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `10.18s` | — |
| **82C（第 165 次实跑 · **`55/55` 实机轮次闭环**）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-68 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r82c` | `clean_unmount_wave68_reset_h0_h3_big6` | Native ARM64 Wave-68 联合预演（**`55/55` 实机轮次 · 第 `165/165` 次独立实跑 · `110/110` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位：**`[Camera Settings Reset]`** 复位 Still `[Flash Mode]`，同时完整保留 **`[Area/Date]`、`[Grid Line]`、全部 5 项 `[Marker Display]`、机身 `Camera Set. Memory 1..3`、`[Memory/Recall Media]`、`[External Flash Set.]`、`[Video Light Mode]`、网络凭据与 `Airplane Mode=On`**；**`[Reset Network Set.]`** 清除网络凭据同时完整保留全部 Wave-68 设置与 `Airplane Mode=On`；**`[Initialize]`** 还原 Wave-68 默认值并重装初始向导同时保留 RTC 备电充电时长、`Slot 2 CAMPR` 计数与 `Airplane Mode=On`；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=41`, `verify_us=1195224`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.17s` | 同 `82A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-68 四大支柱初始化与 Stage-B 四路桥接（`r82a` — 第 163 次实跑）
```text
FX6_R82_WAVE68_INIT fx3_wave68_nodes_ok=1 uxc_tokens_ok=1 areadate30_dst_clockset_ok=1
  grid3_cleanhdmi_marker_ok=1 saveload_camset10_erofs_ok=1 sync_debunk_mishoe_xlrh1_ok=1
  fx3_zone_oob_rc=-22 fx3_cr2032_rc=-95 fx3_rtc_under24h_rc=-11 fx6_dst_dormant_rc=-95
  fx6_rtc_end_rc=-16 marker_still_rc=-95 marker_hdmi_rc=-95 fx6_grid3_dormant_rc=-95
  camset_slot1_save_erofs_rc=-30 camset_slot1_del_erofs_rc=-30 camset_slot2_blocked_rc=-95
  camset_pro_camera_rc=-95 camset_over10_rc=-28 camset_excl_rc=-95 camset_fw_v1_rc=-22
  campr_slot1_erofs_rc=-30 fx6_ref_file_dormant_rc=-95 fx3_sync_debunk_rc=-95
  fx3_xlrh1_mutex_rc=-16 fx3_pmic_over900_rc=-16 fx3_hv_flash_rc=-1 fx6_vlight_auto_rc=-95
  fx6_genlock_dormant_rc=-95 slot1_vfs_camset_erofs_rc=-30
  slot1_vfs_camset_unlink_erofs_rc=-30 slot1_vfs_campr_erofs_rc=-30 p2_write_blocked_rc=-30
  p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  marker_hdmi_pixels_injected=0 camset_excluded_leaked_count=0
  dormant_fx3_cr2032_events=0 dormant_fx6_dst_ui_events=0 dormant_fx6_grid3_ui_events=0
  dormant_fx3_pro_camera_events=0 dormant_fx6_ref_file_events=0
  dormant_fx3_sync_terminal_events=0 dormant_fx6_genlock_events=0
  xlrh1_mishoe_mutex_violations=0 usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0
  slot1_avf_info_mutated=0 rf_tx_packets=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r82_init_ok=1 verify_us=314778

FX6_STAGE_B_R82_BRIDGE round=82 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19 areadate30_dst_rtc24h_clockset_ok=1
  grid3_cleanhdmi_marker5_zero_hdmi_ok=1
  saveload_camset10_slot1_only_erofs30_allfile64_ok=1
  sync_debunk_mishoe_vlight4_xlrh1_mutex_zero_genlock_ok=1
  milestone_55th_realhw_165th_live_110_pngs=1 usb_tx=0 slot1_writes=0
  slot1_write_count=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0
```

### 2.2 Fail-Closed Wave-68 防火墙拦截明细（`r82b` — 第 164 次实跑）
```text
FX6_R82_WAVE68_GUARD fx3_zone_neg_rc=-22 fx3_zone_30_rc=-22 fx3_datefmt_oob_rc=-22
  fx3_cr2032_rc=-95 fx3_rtc_23h_rc=-11 fx3_rtc_depleted_rc=-11 fx3_unset_ts_op_rc=-11
  fx6_tz_oob_rc=-22 fx6_dst_ui_rc=-95 fx6_cr2032_rc=-95 fx6_rtc_end_rc=-16
  fx3_grid_golden_rc=-95 fx3_grid_clean_hdmionly_rc=-16 fx3_grid_clean_raw_rc=-16
  fx3_marker_still_rc=-95 fx3_marker_hdmi_rc=-95 fx3_marker_focusmag_rc=-16
  fx3_aspect_oob_rc=-22 fx3_safety_oob_rc=-22 fx6_grid3_ui_rc=-95 fx6_center_oob_rc=-22
  camset_pro_camera_rc=-95 camset_slot2_rc=-95 camset_over10_rc=-28 camset_mr_busy_rc=-16
  camset_xmodel_rc=-22 camset_v101_rc=-22 camset_excl_iptc_rc=-95 camset_excl_net_rc=-95
  camset_excl_areadate_rc=-95 camset_slot1_save_rc=-30 camset_slot1_del_rc=-30
  campr_slot1_erofs_rc=-30 ftpset_slot1_erofs_rc=-30 mem_customkey_rc=-95
  fx6_ref_file_rc=-95 fx6_allfile_over64_rc=-28 fx6_allfile_slot1_erofs_rc=-30
  fx3_sync_term_rc=-95 fx3_genlock_rc=-95 fx3_tc_bnc_rc=-95 fx3_flash_movie_rc=-95
  fx3_flash_eshut_rc=-16 fx3_flash_over250_rc=-16 fx3_flash_hv250v_rc=-1
  fx3_flash_revpol_rc=-1 fx3_xlrh1_mutex_rc=-16 fx3_pmic_901ma_rc=-16
  fx6_vlight_auto_rc=-95 fx6_still_flash_rc=-95 fx6_genlock_bnc_rc=-95
  null_cfg_einval_rc=-22 live_attach_eperm_rc=-1 slot1_camset_vfs_erofs_rc=-30
  slot1_camset_del_vfs_erofs_rc=-30 slot1_campr_vfs_erofs_rc=-30
  slot1_ftpset_vfs_erofs_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 slot1_avf_info_mutated=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r82b_ok=1 verify_us=944362
FX6_R82_WAVE68_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-68 三层非对称复位与 `16/16 H0 == H3`（`r82c` — 第 165 次实跑）
```text
FX6_R82_CLEAN_UNMOUNT_WAVE68_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_flash_preserves_areadate_grid_marker5_mem_vlight_airplane_ok=1
  nwreset_clears_netcreds_preserves_wave68_setup_grid_marker5_mem_airplane_ok=1
  initialize_restores_wave68_defaults_rearms_wizard_preserves_rtc_slot2_airplane_ok=1
  marker_hdmi_pixels_injected=0 camset_excluded_leaked_count=0
  dormant_fx3_cr2032_events=0 dormant_fx6_dst_ui_events=0 dormant_fx6_grid3_ui_events=0
  dormant_fx3_pro_camera_events=0 dormant_fx6_ref_file_events=0
  dormant_fx3_sync_terminal_events=0 dormant_fx6_genlock_events=0
  xlrh1_mishoe_mutex_violations=0 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 slot1_avf_info_mutated=0 rf_tx_packets=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0
  emmc_write_bytes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r82c_ok=1 verify_us=1195224
```

---

## 3. `r82a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| Scene 1 Composited（`26.82 KiB` / `27,467 B`） | Scene 2 Alpha（`26.50 KiB` / `27,132 B`） |
| :---: | :---: |
| ![r82a Big6 Composited](r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png) | ![r82a Big6 Alpha](r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）时钟与 RTC 备电台架（验证 30 个 `AREA_GMT_*` 时区、`[Daylight Savings]` `+1h` 切换、`[Date Format]` 3 项、`>= 24h` 关机主电池充内置备电、无用户 CR2032 仓、`[Initialize]` 重装初始向导，以及 FX6 `Maintenance > Clock Set` `UTC -12:00..+14:00` 与 `Backup Battery End`）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）Clean-HDMI 构图参考线与标记隔离台架（验证 `[Grid Line Display/Type]` 在 `HDMI Info. Display=On` 下透传外部录机、在 `Off(HDMI Only)`/`RAW Output=On` 下洁净剥离，`[Marker Display] -> [Guideframe]` 绝对 `0` 像素 HDMI 注入与 `Focus Magnifier` 隐藏，以及 FX6 `Monitoring > Marker`）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）配置存取与 MI 热靴电气台架（验证 `Slot 1` 硬锁定 `CAMSET01..10.DAT` 与排除清单、`libSaveLoadSettings.so` 版本/同机型拦截与加载重启、`Slot 1` 物理写保护隔离、`Camera Set. Memory` `1..3` vs `M1..M4`、Still 机械快门 `1/250 s` `< 250 V` 闪光同步、`HVL-LBPC` `[Video Light Mode]` 4 模式与 `XLR-H1` 物理互斥及 `PMIC 5V <= 900 mA` 预算，以及 FX6 `All File`、`TC IN/OUT` BNC 与零 `GENLOCK` BNC）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 82A (163rd Live Run): Wave-68 4-Pillar Stage-A/B + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 82 --r82-mode areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r82a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round82-qemu/r82a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r82a-wave68-big6 \
  --export-png-dir <SCRATCH_ROOT>/round82-pngs

# Run 82B (164th Live Run): Fail-Closed Wave-68 Guard (-95/-16/-11/-28/-22/-30/-1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 82 --r82-mode wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard --sd-manifest-mode valid --lang en \
  --run-id r82b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round82-qemu/r82b

# Run 82C (165th Live Run — Round 82: 55/55 Real-HW Rounds / 165/165 Live Runs / 110/110 PNGs <= 27,467 B): Clean Unmount + Wave-68 3-Tier Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 82 --r82-mode clean_unmount_wave68_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r82c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round82-qemu/r82c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`overall_status == "PASS"`、`synthetic_fallback == False`、`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`emmc_writes == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`usb_tx_bytes == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`marker_hdmi_pixels_injected == 0`、`camset_excluded_leaked_count == 0`、`e_nd_actuator_tx_count == 0`、`dormant_fx3_cr2032_events == 0`、`dormant_fx6_dst_ui_events == 0`、`dormant_fx6_grid3_ui_events == 0`、`dormant_fx3_pro_camera_events == 0`、`dormant_fx6_ref_file_events == 0`、`dormant_fx3_sync_terminal_events == 0`、`dormant_fx6_genlock_events == 0`、`xlrh1_mishoe_mutex_violations == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，所有硬件实机挂载/写盘/跨机刷写/SPI-NOR/EL3 标志均为 `False`，未包含任何专有固件原始字节。
