# Round 72（Wave-58 · `45/45` 实机预演轮次 `R28..R72` · 第 `133..135` 次实跑 -> `135/135` 总实跑 · `90/90` 张 Big-6 PNG `<= 27,467 B` 里程碑）：FX3 7.02 原厂内核真机准备预演 — `[Bright Monitoring]` 快捷键独占 & `[Monitor Brightness]` vs FX6 `VF/Backlight`、`[Shot Mark 1/2]`/`[Edit]` vs 缺失 `[Divide]` & `Slot-1 EROFS=30`、零蓝牙 `[Timecode Link]` / `WPA3` / `USB-LAN` / `Airplane Mode` 零射频，以及机械 `[BULB]`/`DRO` vs 休眠 `[Bulb Timer]`/`[Auto HDR]`

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 72** 三路独立 QEMU 实机预演（`r72a` / `r72b` / `r72c`，达成 **`45/45` 实机预演轮次 `R28..R72` · `135/135` 次独立实跑 · `90/90` 张 `<= 27,467 B` PNG 视觉凭证里程碑**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`bright_mon_menu_spoof_events == 0`、`dormant_divide_extract_bypass_events == 0`、`bt_timecode_link_bypass_events == 0`、`dormant_bulb_timer_bypass_events == 0`、`dormant_auto_hdr_bypass_events == 0`、`wireless_tx_packets == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r72c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r72a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 58 四大支柱门禁、休眠符号（`BRIGHT_MONITORING` 菜单伪造 / `LCD_BRIGHTNESS_{AUTO,BRIGHT,NORMAL}` / `FX6 LCD/VF Backlight & NIGHTSHOT` / 缺失 `[Divide]` 与 `[Extract]` / `Cut to 15/30/60 seconds` / 零蓝牙 `[Timecode Link]` & `UltraSync BLUE` / 已移除 `WEP`/`WPA-PSK`/`IPsec` / `BKID_APP_setting_bulb_timer` / `[Auto HDR]`）的 fail-closed `-95 EOPNOTSUPP` / `-2 ENOENT` 拦截、`Ver. 7.00/7.02` `[Bright Monitoring]` + `[Focus Magnifier]`/`[Auto Magnifier in MF]` 协同、`[Shot Mark 1/2]`/`[Clip Flag]`/`Playback -> [Edit]`（`[Photo Capture]`/`[JPEG/HEIF Switch]`/`[Copy]`/`[Rotate]`/`[Create Divider Frame]`）与 `Slot 1` 恢复保险库 `-30 EROFS` 防火墙、`VMC-BNCM1` 有线外接 `EXT-LK` / `WPA2-PSK` & `WPA3-SAE` / `USB-LAN Cnct. Launch`（`cdc_ncm.ko`/`r8152.ko`/`ipheth.ko` 等）/ `[Airplane Mode] = On` 零射频（`p12/p13` `MS_RDONLY`，跨 `[Reset Network Set.]` 与 `[Initialize]` 均保留 `On`）、机械快门独占 Still `[BULB]`（`Electronic Shutter`/连拍/间隔回退 `30"`）与活跃 `[D-Range Optimizer]`（`Auto/Off/Lv1..Lv5` + `DRO Bracket`，由 `[HLG Still Image]` 替代休眠 `[Auto HDR]`），以及三层非对称复位层级（`Camera Settings Reset` / `Reset Network Set.` / `Initialize`）；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（暗光传感器积分、OLED 亮度计实测、XAVC 卡槽实际写入、`VMC-BNCM1` LTC 锁相、2.4/5 GHz 射频暗室、`USB-LAN` 千兆协商与机械快门 `BULB` 时序）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 72 (`45/45` Real-HW Rounds · Wave-58 · `133rd..135th` Live Runs -> `135/135` Total Live Runs, `90/90` PNGs `<= 27,467 B` Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-58 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave58-bright-monitoring-shot-mark-timecode-link-wifi-usblan-intel/README.md`](../2026-11-17-global-sony-wave58-bright-monitoring-shot-mark-timecode-link-wifi-usblan-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 72 轮（Wave-58 · `45/45` 实机轮次 / `133rd..135th` -> `135/135` 次实跑 / `90/90` PNG）三项实机预演总览（`r72a` / `r72b` / `r72c`）

| 实跑场景 | Run ID | `r72_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **72A（第 133 次实跑）：Wave-58 四大支柱 — `[Bright Monitoring]` 快捷键 + `[Monitor Brightness]` vs FX6 `VF/Backlight`、`[Shot Mark 1/2]`/`[Edit]` vs 缺失 `[Divide]` + Slot-1 `EROFS=30`、零蓝牙 `[Timecode Link]` / `WPA3` / `USB-LAN` / 零射频、机械 `[BULB]`/`DRO` vs 休眠 `[Bulb Timer]`/`[Auto HDR]` + Big-6 Home** | `r72a` | `bright_mon_shotmark_usblan_bulb_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Bright Monitoring]`**（`_f 0x701f`，仅限自定义键触发不进拍摄菜单，强切 `Setting Effect OFF`，`P/A/S/M + MF` 独占，Ver. 7.00/7.02 **`[Focus Magnifier]`/`[Auto Magnifier in MF]` 协同**）与仅 `Initialize` 复位的 **`[Monitor Brightness]`**（`Manual -2..+2 [def 0]` / `Sunny Weather`，休眠 `AUTO/BRIGHT/NORMAL` `-95`）对比 `FX6` `VF Setting > Brightness 1..15` 与 `AE Mode > Backlight`（休眠 `LCD/VF Backlight` 与 `NIGHTSHOT` `-95`）；(2) 核验 **`[Shot Mark 1/2]`**（`Add` / `Add/Delete`）、`[Image Jump Setting]`、`[Clip Flag]`（`OK/NG/KEEP`）与 `Playback -> [Edit]`（`[Photo Capture]`、`[JPEG/HEIF Switch]`、`[Copy]`、`[Rotate]`、`[Create Divider Frame]`），100% 缺失 **`[Divide]`/`[Extract]`**（`0` 命中）与休眠 `Cut to 15/30/60s`（`-95`），及 `Slot-1` `EROFS=30`；(3) 核验 **零蓝牙 `[Timecode Link]` / `UltraSync BLUE`**（`0` 命中）vs 有线 `VMC-BNCM1` LTC **`EXT-LK`**（`Preset + Free Run`）、`WW728473`/`WW558244` 频段分化、Ver. 7.00+ **`WPA2-PSK`/`WPA3-SAE`**（移除 `WEP`/`WPA-PSK`/`IPsec`）、**`[USB-LAN Cnct. Launch]`**（`cdc_ncm.ko`/`r8152.ko`/`ipheth.ko` 等）+ **`[Airplane Mode]=On`** 零射频（`p12/p13 MS_RDONLY`，`wireless_tx_packets=0`，USB-C 与 Multi-USB 互斥 `-16 EBUSY`）vs `FX6` 物理 `TC IN/OUT` BNC & 无蓝牙硬件；(4) 核验机械快门独占 Still **`[BULB]`**（`Electronic Shutter`/连拍/间隔回退 `30"`）与活跃 **`[D-Range Optimizer]`**（`Auto/Off/Lv1..Lv5` + `DRO Bracket`）vs 休眠 **`[Bulb Timer]`**（`BKID_APP_setting_bulb_timer` `-95`）与 **`[Auto HDR]`**（`-95`，由 `[HLG Still Image]` 替代），驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r72_init_ok=1`, `r72_bridge_ok=1`, `verify_us=985069`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.76s` | [`r72a-brightmon-shotmark-usblan-bulb-big6-schinese-composited.png`](assets/r72a-brightmon-shotmark-usblan-bulb-big6-schinese-composited.png) |
| **72B（第 134 次实跑）：Fail-Closed Wave-58 防火墙 — `Bright Monitoring` 菜单伪造 / 非 `P/A/S/M+MF` 拦截、缺失 `[Divide]`/`[Timecode Link]`/休眠 `[Bulb Timer]`/`[Auto HDR]`、电子快门 `BULB` 互斥、`Airplane Mode` 零射频与 `Slot-1` `EROFS=30` 拦截** | `r72b` | `wave58_bright_mon_shotmark_usblan_bulb_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 `Bright Monitoring` 拍摄菜单伪造（`-2 ENOENT`）、`AF` 与 `Auto` 模式下启用（`-16 EBUSY`）、曝光调节干扰（`-95`）、休眠 `Monitor Brightness Auto`（`-95`）与越界档位（`-22 EINVAL`）、`FX6` `VF Brightness` 越界（`-22`）及休眠 `Backlight`（`-95`）；(2) 拦截缺失 `[Divide]`/`[Extract]`/`Cut 15s`（`-95`）、越界 Shot Mark（`-22`）、`FX6` 休眠 Shot Mark（`-95`）以及 **`Slot-1` Shot Mark / Clip Flag / Photo Capture / Divider Frame 写入（`-30 EROFS`）**；(3) 拦截零蓝牙 `[Timecode Link]`（`-95`）、非法 TC Regen（`-22`）、已移除 `WEP`/`WPA-PSK`/`IPsec`（`-95`）、`WW558244` 5GHz（`-95`）、`Airplane Mode=On` 无线传输（`-100 ENETDOWN`）、USB-LAN 与 Multi-USB / Wi-Fi 并发互斥（`-16 EBUSY`）、非法 IPv4（`-22`）及 `FX6` USB-TC 休眠（`-95`）；(4) 拦截休眠 `[Bulb Timer]`（`-95`）、非 `M` 模式 `BULB`（`-22`）、电子快门 / 连拍 `BULB` 互斥（`-16 EBUSY`）、休眠 `[Auto HDR]`（`-95`）、`DRO` 受 `Picture Profile`/`HLG` 锁定（`-16 EBUSY`）、`FX6` BULB/DRO（`-95`），以及 **`Slot-1` Wave-58 写卡 / `AVF_INFO` / `p12` WLAN NVS / `P2` / `cnflasha` 写入（`-30 EROFS`）**（`slot1_vault_sha256_match=1`, `wireless_tx_packets=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r72b_ok=1`, `verify_us=936724`, `FX6_R72_WAVE58_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.36s` | — |
| **72C（第 135 次实跑 · `45/45` 实机轮次里程碑）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-58 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r72c` | `clean_unmount_wave58_reset_h0_h3_big6` | Native ARM64 Wave-58 联合预演（**`45/45` 实机轮次 · 第 `135/135` 次独立实跑 · `90/90` 张 PNG 里程碑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位层级：**`[Camera Settings Reset]` 复位 `Bright Monitoring` / `TC Make` / `BULB` / `DRO` / `DRO Bracket`，但完整保留 `[Monitor Brightness]`、`[Photo Capture]` JPEG/HEIF 与全部 `(Network)`（Wi-Fi/BT/USB-LAN/Airplane Mode）**（`camreset_preserves_wave58_survivors_ok=1`）；**`[Reset Network Set.]` 复位 Wi-Fi/BT/USB-LAN，但保留 `[Airplane Mode] = On` 零射频状态**（`nwreset_preserves_airplane_ok=1`）；**`[Initialize]` 恢复 `[Monitor Brightness]` 与 `[Photo Capture]` 默认值，同时仍严格保留 `[Airplane Mode] = On`**（`initialize_restores_wave58_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `wireless_tx_packets=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=59`，`verify_us=455590`，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.99s` | 同 `72A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-58 四大支柱初始化与 Stage-B 四路桥接（`r72a` — 第 133 次实跑）
```text
FX6_R72_WAVE58_INIT fx3_wave58_nodes_ok=1 uxc_tokens_ok=1
  bright_mon_ok=1 shotmark_edit_ok=1 tclink_usblan_ok=1 bulb_dro_dormant_ok=1
  bright_mon_menu_enoent_rc=-2 bright_mon_exp_rc=-95 mon_bright_dormant_auto_rc=-95
  fx6_dormant_backlight_rc=-95 divide_absent_rc=-95 extract_absent_rc=-95
  cut15_dormant_rc=-95 sm_slot1_erofs_rc=-30 clip_flag_slot1_erofs_rc=-30
  photocap_slot1_erofs_rc=-30 bt_tclink_absent_rc=-95 removed_wep_rc=-95
  airplane_wifi_blocked_rc=-100 usblan_vmc_mutex_rc=-16 bulb_timer_dormant_rc=-95
  eshutter_fallback_rc=-16 autohdr_dormant_rc=-95 p2_write_blocked_rc=-30
  p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_divide_extract_bypass_events=0 bt_timecode_link_bypass_events=0
  dormant_bulb_timer_bypass_events=0 dormant_auto_hdr_bypass_events=0
  wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r72_init_ok=1 verify_us=985069

FX6_R72_BRIGHT_MON_MAG_BRIGHTNESS_BRIDGE bright_mon_custom_key_setting_effect_off_ok=1
  ver700_focus_magnifier_coexistence_ok=1 mon_bright_manual_sunny_vs_fx6_vf_backlight_ok=1
  bright_mon_mag_brightness_ok=1 bright_mon_menu_spoof_events=0
  dormant_mon_bright_auto_bypass_events=0 emmc_write_count=0 r72_bridge_ok=1

FX6_R72_SHOTMARK_CLIPFLAG_EDIT_EROFS_BRIDGE shotmark12_clipflag_ok_ng_keep_ok=1
  pb_edit_photocap_divider_vs_absent_divide_ok=1 slot1_shotmark_edit_tier0_erofs30_ok=1
  shotmark_clipflag_edit_erofs_ok=1 dormant_divide_extract_bypass_events=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0

FX6_R72_TCLINK_VMC_WPA3_USBLAN_ZERORF_BRIDGE zero_bt_tclink_vs_vmc_bncm1_ext_lk_ok=1
  wpa2_wpa3_usblan_ko_stack_mutex_ok=1 airplane_zerorf_p12_p13_vs_fx6_bnc_nobt_ok=1
  tclink_vmc_usblan_zerorf_ok=1 bt_timecode_link_bypass_events=0
  wireless_tx_packets=0 passive_tx_bytes_emitted=0 cnflasha_writes=0 emmc_write_count=0

FX6_R72_BULB_DRO_DORMANT_HDR_BRIDGE mech_still_bulb_30s_fallback_ok=1
  dro_lv1_5_bracket_vs_dormant_autohdr_ok=1 dormant_bulb_timer_rejected_eopnotsupp_ok=1
  bulb_dro_dormant_hdr_ok=1 dormant_bulb_timer_bypass_events=0
  dormant_auto_hdr_bypass_events=0 p2_setting_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `68` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`156` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-58 防火墙拦截明细（`r72b` — 第 134 次实跑）
```text
FX6_R72_WAVE58_GUARD bright_mon_menu_rc=-2 bright_mon_af_rc=-16 bright_mon_auto_rc=-16
  bright_mon_autocancel_ok=1 bright_mon_exp_rc=-95 mon_bright_auto_rc=-95
  mon_bright_oob_rc=-22 fx6_vf_oob_rc=-22 fx6_backlight_dormant_rc=-95
  divide_absent_rc=-95 extract_absent_rc=-95 cut_15s_dormant_rc=-95
  sm_oob_rc=-22 slot1_sm_erofs_rc=-30 slot1_flag_erofs_rc=-30
  slot1_photocap_erofs_rc=-30 slot1_divider_erofs_rc=-30 fx6_sm_dormant_rc=-95
  bt_tclink_rc=-95 tc_regen_invalid_rc=-22 wep_removed_rc=-95 wpa_removed_rc=-95
  ipsec_removed_rc=-95 ww558244_5ghz_rc=-95 airplane_wifi_rc=-100
  usblan_multi_busy_rc=-16 usblan_wifi_busy_rc=-16 usblan_ip16_rc=-22
  fx6_usbtc_dormant_rc=-95 bulb_timer_rc=-95 bulb_non_m_rc=-22
  bulb_eshutter_rc=-16 bulb_cont_rc=-16 autohdr_rc=-95 dro_pp_lock_rc=-16
  dro_hlg_lock_rc=-16 fx6_bulb_rc=-95 fx6_dro_rc=-95
  slot1_wave58_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30
  p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_divide_extract_bypass_events=0 bt_timecode_link_bypass_events=0
  dormant_bulb_timer_bypass_events=0 dormant_auto_hdr_bypass_events=0
  wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r72b_ok=1 verify_us=936724
FX6_R72_WAVE58_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-58 三层复位与 `16/16 H0 == H3`（`r72c` — 第 135 次实跑）
```text
FX6_R72_CLEAN_UNMOUNT_WAVE58_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave58_survivors_ok=1
  nwreset_preserves_airplane_ok=1
  initialize_restores_wave58_defaults_ok=1
  dormant_divide_extract_bypass_events=0 bt_timecode_link_bypass_events=0
  dormant_bulb_timer_bypass_events=0 dormant_auto_hdr_bypass_events=0
  wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r72c_ok=1 verify_us=455590
```

---

## 3. `r72a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r72a` Alpha（`26.50 KiB` / `27,132 B`） | `r72a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r72a Big6 Alpha](assets/r72a-brightmon-shotmark-usblan-bulb-big6-schinese-alpha.png) | ![r72a Big6 Composited](assets/r72a-brightmon-shotmark-usblan-bulb-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）暗光传感器积分台架（验证自定义键 `[Bright Monitoring]` 在 `Setting Effect OFF` + `P/A/S/M + MF` 与 `Ver. 7.00+` `[Focus Magnifier]` / `[Auto Magnifier in MF]` 协同下的长帧读取提亮及 OLED `[Monitor Brightness]` `Manual -2..+2` / `Sunny Weather` 尼特亮度对比 `ILME-FX6 Ver. 6.01` `VF Setting > Brightness 1..15`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）XAVC 录制与双卡槽台架（验证 `[Shot Mark 1/2]`、`[Clip Flag]` `OK/NG/KEEP`、回放 `[Edit]` `[Photo Capture]` / `[Create Divider Frame]` 对 `M4ROOT/CLIP/*M01.XML` / `DCIM/` / `AVF_INFO` 的真实提交对比缺失 `[Divide]`/`[Extract]`，以及 `Slot-1` 物理写保护 `EROFS=30` 的硬拦截）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）射频暗室、`VMC-BNCM1` LTC 发生器、`USB-LAN` `CDC-NCM`/`RTL8152` 以太网与机械快门台架（验证 `EXT-LK` 锁相、`WPA2/WPA3` + `USB-LAN` + `[Airplane Mode]=On` 零射频、机械快门 `[BULB]` 与 `Electronic Shutter` `30"` 回退、`[D-Range Optimizer]` `Lv1..Lv5` 实景动态范围，以及休眠 `[Bulb Timer]` / `[Auto HDR]` 的零暴露）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 72A (133rd Live Run): Wave-58 4-Pillar Bright Monitoring / Shot Mark & Edit EROFS / Zero-BT Timecode Link & WPA3 USB-LAN Zero-RF / Mechanical BULB & DRO vs Dormant Bulb Timer & Auto HDR + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 72 --r72-mode bright_mon_shotmark_usblan_bulb_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r72a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round72-qemu/r72a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r72a-brightmon-shotmark-usblan-bulb-big6-schinese \
  --export-png-dir reports/2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu/assets

# Run 72B (134th Live Run): Fail-Closed Wave-58 Guard (Bright Monitoring Menu Spoof ENOENT, Absent Divide/BT Timecode Link/Bulb Timer/Auto HDR EOPNOTSUPP, Electronic Shutter BULB & Multi-USB Mutex EBUSY, Airplane Zero-RF ENETDOWN, Slot-1 EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 72 --r72-mode wave58_bright_mon_shotmark_usblan_bulb_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r72b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round72-qemu/r72b

# Run 72C (135th Live Run — 45/45 Real-HW Rounds / 135/135 Live Runs / 90/90 PNGs Milestone): Clean Unmount Stock FX3 Restoration, Wave-58 3-Tier Asymmetric Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 72 --r72-mode clean_unmount_wave58_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r72c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round72-qemu/r72c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`bright_mon_menu_spoof_events == 0`、`dormant_divide_extract_bypass_events == 0`、`bt_timecode_link_bypass_events == 0`、`dormant_bulb_timer_bypass_events == 0`、`dormant_auto_hdr_bypass_events == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
