# Round 79（Wave-65 · **`52/52` 实机预演轮次 `R28..R79` · 第 `154..156` 次实跑 -> `156/156` 总实跑 · `104/104` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `[Zoom Range]` CIZ/数字变焦与 FX6 零数字变焦、`[Auto Slow Shutter]` 6 项互锁 / `[ISO Range Limit]` / 静态专属 `[ISO AUTO Min. SS]` / 双原生 Base ISO、静态 `ARW` 休眠 `Lossless Comp` 辟谣 / `[HLG Still Image]` / `[Sort Recording]` `Slot 1 EROFS=30`，以及 `[USB Connection Mode]` 4 档 / `[USB LUN Setting]=Single` 暴露 `Slot 1` 防护 / `NP-FZ100` PD 门控 / `FX3`/`FX6` 原生 `UVC` 双辟谣闭环

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 79** 三路独立 QEMU 实机预演（`r79a` / `r79b` / `r79c`，正式达成 **`52/52` 实机预演轮次 `R28..R79` · `156/156` 次独立实跑 · `104/104` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`dormant_fx6_digital_zoom_events == 0`、`dormant_movie_iso_auto_min_ss_events == 0`、`dormant_raw_lossless_comp_events == 0`、`dormant_uvc_fx3_events == 0`、`dormant_uvc_fx6_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r79c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r79a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均严格 `<= 27,467 B`）。
- **核心关联文件**：
  - 情报基线：[Wave 65 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/reports/2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel/README.md)
  - 遥测汇总：[summary.json](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/summary.json)
  - 视觉凭证：[r79_zoom_ciz_autoslow_iso_dualbase_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_zoom_ciz_autoslow_iso_dualbase_preview.png)（`27,467 B`）· [r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png)（`27,132 B`）
  - 源码与测试：[fx6-stage-a-verify.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/outputs/fx6-native-presenter-closure/fx6-stage-a-verify.c) · [libgrm-fbinit9.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/outputs/fx6-native-presenter-closure/libgrm-fbinit9.c) · [build_and_run_round.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/outputs/fx6-native-presenter-closure/build_and_run_round.py) · [test_round79_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_qemu.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h477-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/outputs/fx6-native-presenter-closure/tests/test_round79_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_qemu.py)
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 65 四大支柱门禁、休眠分支辟谣与 `Slot 1` `EROFS=-30` 隔离的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-30 EROFS` / `-1 EPERM` 护栏：
  1. **支柱 1（`[Zoom Range]` CIZ/Digital、8 档双段变焦速与 FX6 零数字变焦）**：FX3 `[Zoom Range]`（`Optical zoom only` 默认 / `ClearImage Zoom` `1.5x` 4K & `2.0x` HD / `Digital Zoom` `4.0x` Movie & `8.0x` Still S）与 `[Zoom Ring Rotate]` 均**抗 `[Camera Settings Reset]`**，而 8 档 `[Zoom Lever Speed]`（`1st=3`/`2nd=8 Fast`）、`[Custom Key Z. Speed]=3`、`[Remote Zoom Speed]=Variable/3` **可被 Reset**；非光学变焦在 Still `RAW`/`RAW+JPEG`/`RAW+HEIF`、Movie `119.88p/100p`、`S&Q >= 100/120fps` 强制禁用（`-16 EBUSY`），激活后禁用 `[Focus Area]`（中央优先 AF）、锁定 `[Metering Mode]=Multi` 并禁用 `Face/Eye Prior. in AF` 与 `Tracking`；对比 FX6 `Zoom Type` 仅 2 档（`Optical`/`CIZ`，**零 `Digital Zoom`** -> `-95 EOPNOTSUPP`）+ `Handle Zoom`（`High=8`/`Low=3`）。
  2. **支柱 2（`[Auto Slow Shutter]` 6 项互锁、`[ISO Range Limit]`、静态专属 `[ISO AUTO Min. SS]` 与双原生 Base ISO）**：`[Auto Slow Shutter]`（电影专属、默认 `On`、可 Reset）在全部 6 项官方条件（`S&Q`、`S`、`M`、手动固定 `ISO`、`Flex Exp. Shutter=Manual`、`Cine EI`/`Cine EI Quick`）及 `Shutter Mode=Angle` 下强制拦截（`-16 EBUSY`）；`[ISO Range Limit]` 仅限手动 ISO 且抗 Reset；`[ISO AUTO Min. SS]` 仅限静态 `P/A` + `ISO AUTO`（Movie/S&Q 返回 `-16 EBUSY`，FX6 无此项返回 `-95 EOPNOTSUPP`）；双原生 Base ISO 在 `Cine EI` 下显式切换 `800`/`12800`，非 `Cine EI` 按 Gamma 自动 `20×`（`+4.33 EV`）双增益跃迁（`S-Log3 640/12800`、`S-Cinetone/HLG/HLG3/Cine4 100/2000`、`PP Off/HLG2/Cine3 80/1600`、`Cine1 64/1280`、`HLG1/Cine2 50/1000`），对比 FX6 `Base Sensitivity=Low/High` + `AGC`。
  3. **支柱 3（静态 `ARW` 休眠 `Lossless Comp` 辟谣、`[HLG Still Image]` 与 `[Sort Recording]` `Slot 1 EROFS=-30`）**：FX3 Ver. 7.02 `[RAW File Type]` 严格仅暴露 `Compressed`（默认）与 `Uncompressed`（14-bit `.ARW`），休眠的 `Lossless Comp (L/M/S)`（`_f 0x6b56`/`0x7897`/`0x6bfd`/`0x7894`）统一阻断 `-95 EOPNOTSUPP`；`[HLG Still Image]`（`BKID_APP_setting_still_hlg_photo`、ELF 内部拼写 `STILL_HLD_PHOTO_*`）强制要求纯 `HEIF` + `P/A/S/M`，强制 `BT.2100` 与 ISO 下限 `100/125` 并禁用 PP/Creative Look/DRO；`[Sort Recording]` + `[Auto Switch Media]=On` 满卡溢出写向 `Slot 1` 严格返回 `-30 EROFS`（`slot1_writes=0`）。
  4. **支柱 4（`[USB Connection Mode]` 4 档、`[USB LUN Setting]=Single` 暴露 `Slot 1` 隐患、`NP-FZ100` PD 门控与双机身原生 `UVC` 辟谣）**：`[USB Connection Mode]` 仅 4 档（`Sel. When Connect` / `MSC` / `MTP` / `Remote Shooting`，全部 Setup 项抗 Reset）；`[USB LUN Setting]=Single`（`_f 0x6b19`/`0x776d`）暴露 **Slot 1 ONLY**（而非隐藏 Slot 1，`MTP` 亦映射 Slot 1），macOS 宿主机 `mds`/`fseventsd`/`Finder`/`fsck_exfat` 对 `Slot 1` 的写请求全部以 `-30 EROFS` 阻断（`usb_tx=0`, `slot1_writes=0`）；`[USB Power Supply]=On`（仅 USB-C）强依赖有电量的 `NP-FZ100` 电池（拔电池立即断电，除非 `DC-C1` + `>=65W PD` + `5A e-Marked` 线缆），对比 FX6 `19.5V DC IN`（`18.0-20.5V`，`DC Low Voltage1/2=16.5V/15.5V`，无电池可开机）；`FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 均无原生 `UVC/UAC USB Streaming`（`-95 EOPNOTSUPP`）；FX3 `Network Streaming`（`RTMP/RTMPS/SRT`）下的 `[Movie Rec During Streaming]`（`_f 0x79d5`，默认 `Disable`）独立于 HDMI `[Rec. Media dur HDMI Output]`（`_f 0x6144`），二者针对 `Slot 1` 的写卡均以 `-30 EROFS` 阻断。
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测尚未上电执行，详见 §4。**

> **日期**：2026-11-21 | **轮次**：**Round 79 (`52/52` Real-HW Rounds · Wave-65 · `154th..156th` Live Runs -> `156/156` Total Live Runs, `104/104` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-65 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel/README.md`](../2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 79 轮（Wave-65 · `52/52` 实机轮次 / `154th..156th` -> `156/156` 次实跑 / `104/104` PNG）三项实机预演总览（`r79a` / `r79b` / `r79c`）

| 实跑场景 | Run ID | `r79_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **79A（第 154 次实跑）：Wave-65 四大支柱 — `[Zoom Range]` CIZ/Digital 与 FX6 零数字变焦、`[Auto Slow Shutter]` 6 项互锁 / `[ISO Range Limit]` / 静态 `[ISO AUTO Min. SS]` / 双原生 Base ISO、静态 `ARW` 休眠 `Lossless Comp` 辟谣 / `[HLG Still Image]` / `[Sort Recording]` `Slot 1 EROFS=30`、4 档 USB 模式 / `USB LUN Single` `Slot 1` 防护 / `NP-FZ100` PD / 双 `UVC` 辟谣 + Big-6 Home** | `r79a` | `zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Zoom Range]`**（CIZ `1.5x` 4K / `2.0x` HD，Digital `4.0x` Movie / `8.0x` Still S，非光学 AF/Multi/Face/Tracking 互锁，FX6 零 Digital Zoom `-95 EOPNOTSUPP` + Handle Zoom `High=8/Low=3`）；(2) 核验 **`[Auto Slow Shutter]`** 6 项互锁 + Shutter Angle 互斥、静态专属 **`[ISO AUTO Min. SS]`** 与双原生 Base ISO 全矩阵（`Cine EI 800/12800` 及 5 组 Gamma `20×` 跃迁）；(3) 核验静态 **`[RAW File Type]`** 仅 `Compressed`/`Uncompressed`（休眠 `Lossless Comp` `-95`）、**`[HLG Still Image]`**（`BT.2100`, ISO `>=100`）与 **`[Sort Recording]`** `Slot 1` `-30 EROFS`；(4) 核验 **`[USB LUN Setting]=Single`** 暴露 `Slot 1` 防护（`.Spotlight-V100` `-30 EROFS`, `usb_tx=0`, `slot1_writes=0`）、**`NP-FZ100` PD 门控** vs `DC-C1 >=65W 5A` vs FX6 `19.5V DC IN`、**双机身 `UVC` 辟谣（`-95`）** 与 **`[Movie Rec During Streaming]`** `Slot 1` `-30 EROFS`，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r79_init_ok=1`, `r79_bridge_ok=1`, `verify_us=326925`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.01s` | [`r79_zoom_ciz_autoslow_iso_dualbase_preview.png`](r79_zoom_ciz_autoslow_iso_dualbase_preview.png) / [`r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png`](r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png) |
| **79B（第 155 次实跑）：Fail-Closed Wave-65 防火墙 — FX6 Digital Zoom / FX6 `ISO AUTO Min. SS` / 休眠 `Lossless Comp (L/M/S)` / FX6 Still ARW / 双机身原生 `UVC` / Micro-USB 供电（`-95`）、CIZ/Digital RAW/120p/S&Q / `Auto Slow Shutter` 6 项+Angle / `Min. SS` Movie&S&Q / 非 Cine EI 手动 `Base ISO` / `HLG` JPEG/RAW/iAuto / 无 `NP-FZ100` PD / `DC-C1 <65W` / FX6 `<15.5V`（`-16`）、越界速度/ISO/`NULL`（`-22`）、`live_attach`（`-1`）及 `Slot 1`（`Sort`/`MSC Single`/`MTP`/`mds`/`fseventsd`/`Streaming`/`HDMI`）/`P12`/`P2`/`cnflasha`（`-30 EROFS`）** | `r79b` | `wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard` | Native ARM64 Fail-Closed 注入阻断实测：46 项故障注入全部命中精确 POSIX `errno`（`-95`/`-16`/`-22`/`-30`/`-1`），实证 `slot1_vault_sha256_match=1`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `cnflasha_writes=0`, `r79b_ok=1`, `verify_us=859885`, `FX6_R79_WAVE65_GUARD_RC=0` | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `8.82s` | — |
| **79C（第 156 次实跑 · **`52/52` 实机轮次闭环**）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-65 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r79c` | `clean_unmount_wave65_reset_h0_h3_big6` | Native ARM64 Wave-65 联合预演（**`52/52` 实机轮次 · 第 `156/156` 次独立实跑 · `104/104` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位：**`[Camera Settings Reset]`** 复位变焦 8 档速度、`Auto Slow Shutter`、`ISO AUTO Min. SS`、`RAW File Type`、`JPEG/HEIF`、`HLG Still`、`Movie Rec During Streaming`，同时完整保留 **`Zoom Range`、`Zoom Ring Rotate`、`ISO Range Limit`、`Sort Recording`/`Auto Switch Media`、`USB Connection Mode`、`USB LUN Setting`、`USB Power Supply` 与 `Airplane Mode=On`**；**`[Reset Network Set.]`** 复位推流录卡同时保留全部 Shooting/Setup 项与 `Airplane Mode=On`；**`[Initialize]`** 还原 Wave-65 全部默认值同时保持 `Airplane Mode=On`；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=63`, `verify_us=1071790`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.91s` | 同 `79A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-65 四大支柱初始化与 Stage-B 四路桥接（`r79a` — 第 154 次实跑）
```text
FX6_R79_WAVE65_INIT fx3_wave65_nodes_ok=1 uxc_tokens_ok=1 zoom_ciz_speed8_ok=1
  autoslow6_iso_baseiso_ok=1 arw_lossless_hlg_sort_ok=1 usblun_pd_uvc_streaming_ok=1
  fx6_digital_zoom_rc=-95 ciz_120p_lock_rc=-16 autoslow_cineei_lock_rc=-16
  minss_movie_lock_rc=-16 raw_lossless_dormant_rc=-95 sort_slot1_erofs_rc=-30
  lun_single_slot1_erofs_rc=-30 slot1_spotlight_erofs_rc=-30 pd_no_fz100_ebusy_rc=-16
  fx3_uvc_dormant_rc=-95 fx6_uvc_dormant_rc=-95 stream_rec_slot1_erofs_rc=-30
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 dormant_fx6_digital_zoom_events=0
  dormant_movie_iso_auto_min_ss_events=0 dormant_raw_lossless_comp_events=0
  dormant_uvc_fx3_events=0 dormant_uvc_fx6_events=0 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 rf_tx_packets=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r79_init_ok=1 verify_us=326925

FX6_STAGE_B_R79_BRIDGE round=79 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19 zoom_ciz_15x_2x_digital_4x_fx6_zero_digital_ok=1
  autoslow_6way_iso_limit_still_min_ss_dualbase_ok=1
  arw_dormant_lossless_hlg_still_sort_erofs30_ok=1
  usb_mode4_lun_single_slot1_pd_fz100_dual_uvc_debunk_ok=1
  milestone_52nd_realhw_156th_live_104_pngs=1 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0
```

### 2.2 Fail-Closed Wave-65 防火墙拦截明细（`r79b` — 第 155 次实跑）
```text
FX6_R79_WAVE65_GUARD fx6_digital_zoom_rc=-95 fx3_ciz_still_raw_rc=-16 fx3_ciz_120p_rc=-16
  fx3_dig_sq120_rc=-16 fx6_ciz_sq120_rc=-16 fx6_ciz_raw_rc=-16 zoom_spd9_einval_rc=-22
  as_sq_lock_rc=-16 as_s_lock_rc=-16 as_m_lock_rc=-16 as_fixed_iso_lock_rc=-16
  as_flex_shutter_man_rc=-16 as_cineei_lock_rc=-16 as_angle_mutex_rc=-16
  iso_limit_auto_ebusy_rc=-16 iso_limit_bounds_einval_rc=-22 minss_movie_ebusy_rc=-16
  minss_sq_ebusy_rc=-16 fx6_minss_absent_rc=-95 non_cineei_baseiso_rc=-16
  raw_lossless_rc=-95 raw_lossless_l_rc=-95 raw_lossless_m_rc=-95 raw_lossless_s_rc=-95
  fx6_still_arw_rc=-95 hlg_jpeg_lock_rc=-16 hlg_raw_lock_rc=-16 hlg_iauto_lock_rc=-16
  sort_slot1_erofs_rc=-30 fx3_uvc_dormant_rc=-95 fx6_uvc_dormant_rc=-95 micro_usb_pwr_rc=-95
  lun_single_msc_slot1_erofs_rc=-30 mtp_slot1_erofs_rc=-30 pd_no_fz100_ebusy_rc=-16
  dcc1_under65w_ebusy_rc=-16 fx6_dcin_low_ebusy_rc=-16 stream_rec_slot1_erofs_rc=-30
  hdmi_rec_slot1_erofs_rc=-30 null_cfg_einval_rc=-22 live_attach_eperm_rc=-1
  slot1_mds_erofs_rc=-30 slot1_fseventsd_erofs_rc=-30 p12_write_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r79b_ok=1 verify_us=859885
FX6_R79_WAVE65_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-65 三层非对称复位与 `16/16 H0 == H3`（`r79c` — 第 156 次实跑）
```text
FX6_R79_CLEAN_UNMOUNT_WAVE65_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_speeds_autoslow_minss_arw_hlg_preserves_zoomrange_ring_isolimit_sort_usb_airplane_ok=1
  nwreset_resets_streamrec_preserves_wave65_setup_airplane_ok=1
  initialize_restores_wave65_defaults_preserves_airplane_ok=1
  dormant_fx6_digital_zoom_events=0 dormant_movie_iso_auto_min_ss_events=0
  dormant_raw_lossless_comp_events=0 dormant_uvc_fx3_events=0 dormant_uvc_fx6_events=0
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 rf_tx_packets=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r79c_ok=1 verify_us=1071790
```

---

## 3. `r79a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| Scene 2 Alpha（`26.50 KiB` / `27,132 B`） | Scene 1 Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r79a Big6 Alpha](r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png) | ![r79a Big6 Composited](r79_zoom_ciz_autoslow_iso_dualbase_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）变焦与曝光光学台架（验证 `ClearImage Zoom` `1.5x` 4K / `2.0x` HD、`Digital Zoom` `4.0x` Movie / `8.0x` Still S 对比 FX6 零 Digital Zoom、8 档双段变焦杆速度、非光学 AF/测光/跟踪互锁、`Auto Slow Shutter` 6 项锁死以及各 Gamma 曲线真实传感器双增益跃迁点）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）静态图像与双卡槽媒体台架（验证 14-bit `Compressed`/`Uncompressed` `.ARW` 且无 `Lossless Comp (L/M/S)`、`[HLG Still Image]` `BT.2100` `.HIF` + ISO `100/125` 下限，以及 `[Sort Recording]` + `[Auto Switch Media]` 满卡切换隔离）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）USB/供电/流式传输台架（验证 `[USB Connection Mode]` 4 档、`[USB LUN Setting]=Single` 物理写保护隔离 macOS `mds`/`fseventsd`/`Finder`/`fsck_exfat`、`NP-FZ100` PD 门控与 `DC-C1` `>=65W` `5A e-Marked` 对比 FX6 `19.5V DC IN` 无电池供电，以及双机身无原生 UVC/UAC 免驱枚举）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 79A (154th Live Run): Wave-65 4-Pillar Stage-A/B + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 79 --r79-mode zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r79a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round79-qemu/r79a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r79a-wave65-big6 \
  --export-png-dir <SCRATCH_ROOT>/round79-pngs

# Run 79B (155th Live Run): Fail-Closed Wave-65 Guard (-95/-16/-22/-30/-1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 79 --r79-mode wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard --sd-manifest-mode valid --lang en \
  --run-id r79b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round79-qemu/r79b

# Run 79C (156th Live Run — 52/52 Real-HW Rounds / 156/156 Live Runs / 104/104 PNGs <= 27,467 B): Clean Unmount + Wave-65 3-Tier Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 79 --r79-mode clean_unmount_wave65_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r79c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round79-qemu/r79c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_fx6_digital_zoom_events == 0`、`dormant_movie_iso_auto_min_ss_events == 0`、`dormant_raw_lossless_comp_events == 0`、`dormant_uvc_fx3_events == 0`、`dormant_uvc_fx6_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，所有硬件实机挂载/写盘/跨机刷写/SPI-NOR/EL3 标志均为 `False`，未包含任何专有固件原始字节。
