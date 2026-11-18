# Round 75（Wave-61 · **`48/48` 实机预演轮次 `R28..R75` · 第 `142..144` 次实跑 -> `144/144` 总实跑 · `96/96` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `[FTP Transfer Func.]` `9` 服务器槽位 / `FTP`+`FTPES` / 零 `SFTP` / 休眠 `Transfer JPEG Size` / `Slot 1` `AVF_INFO` `EROFS=30` & `USB-LAN` 零射频、`[White Balance]` `Custom 1..3` 排除 `CAMSET*.DAT` / 抗复位 `[Shutter AWB Lock]` / `[Shockless WB]` / `Cine EI`、`Movie AF` 共有刻度（`1..7` / `1..5`）& App 独占 `[Focus Map]`（`>=150fps` 禁用），以及 `15` 比例 `[Marker Display]` & `4` 色 `[Peaking Display]` 抗复位与 Clean-HDMI 零像素隔离

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 75** 三路独立 QEMU 实机预演（`r75a` / `r75b` / `r75c`，达成 **`48/48` 实机预演轮次 `R28..R75` · `144/144` 次独立实跑 · `96/96` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dormant_sftp_bypass_events == 0`、`dormant_active_ftp_bypass_events == 0`、`dormant_transfer_jpeg_size_bypass_events == 0`、`dormant_inbody_focus_map_bypass_events == 0`、`dormant_uvc_bypass_events == 0`、`dormant_af_shift_7_bypass_events == 0`、`hdmi_marker_baked_pixels == 0`、`hdmi_peaking_baked_pixels == 0`、`rf_tx_packets == 0`、`usb_lan_tx_packets == 0`、`wireless_tx_packets == 0`、`slot1_ftp_trans_stat_writes == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r75c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r75a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 61 四大支柱门禁、休眠符号（`SFTP` 协议 `_f 0x6e83` / `FX3 appFw.so` `0` 命中 `sftp`、`0` 命中 `passive_mode` Active FTP 模式、休眠 `[Transfer JPEG Size]` `_f 0x6aed` & `[Transfer HEIF Size]` `_f 0x63dd`、`FX3` 机身 `[Focus Map]` `BKID_APP_USER_MENU_FOCUS_MAP` = `0` 命中、`FX3` & `FX6` 共同缺失的 `[AF Subj. Shift Sens.]` `6`/`7` 级 = `0` 命中、FX3 缺失 UVC USB Streaming）的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-30 EROFS` / `-100 ENETDOWN` 拦截：`[FTP Transfer Func.]` `Server 1..9`（`BKID_APP_ftp_server_settings_*0..8`）、明文 `FTP` + `FTPES` Explicit TLS（`SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`）、`Slot 1` 根目录 `cacert.pem`、`Slot 1` `AVF_INFO`（`CONTENT_INFO_FTP_TRANS_STAT` / `save_ftp_transfer_list_to_media`）由 Tier-0 Vault `-30 EROFS` 阻断、`[Airplane Mode]=On` + `[USB-LAN/Tethering]` 断开双层零射频/零有线隔离对比 `FX6` `File Transfer`（`Passive Mode On/Off`、`Slot B` `certification.pem`、`Auto Upload (Proxy): Chunk` 互斥 `Simul/Relay`）；`[White Balance]` `2500K..9900K`（100K 步进）、`Custom 1..3` 排除在 `CAMSET*.DAT` 之外、跨模式可复位 `[Priority Set in AWB]`、Still 独占抗复位 `[Shutter AWB Lock]`（仅 `[Initialize]` 清除）、Movie `[Shockless WB]`、Log/`S-Log3` `Custom WB Error` 及 `Cine EI` Auto/Underwater Auto 锁定对比 `FX6` `Memory A..H` 与 `ATW Speed 1..5`；Movie AF `[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sens.]` `1..5` **在 FX3 与 FX6 上完全同源一致**、`[AF Assist]`（不兼容 `SELP1650`/`SEL18200LE`）、Ver. 6.00+ *Monitor & Control* App 独占 `[Focus Map]`（`>= 150 fps` 含 `240fps`/Playback/Auto Framing/非 PDAF/USB 远程锁定，而 `100p/119.88p/120fps` 允许）对比 `FX6` 机身原生 `Focus Map`；以及 `[Marker Display]`（`Off` + `15` 种画幅比例 = `16` 态、`Safety Zone` `Off/80%/90%`、`Guideframe`）与 `4` 色 `[Peaking Display]`（`Red/Yellow/Blue/White`）**全部 `8` 项抗 `[Camera Settings Reset]` 与 `[Reset Network Set.]`（仅 `[Initialize]` 复位）且随 Clean HDMI 输出 `0` 像素** 对比 `FX6` `User Box`（`W 3..479, H 3..269`）+ `Aspect Mask`（`0..15`）及 `B&W/Red/Yellow/Blue` 峰值；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（Wi-Fi/USB-LAN 真机 FTP/FTPES 传输、`Slot 1` 物理只读与 `cacert.pem` 导入、传感器实拍 Custom WB / Cine EI / E-mount AF / *Monitor & Control* App `Focus Map` 与 HDMI 分析仪 `0` 像素监看）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 75 (`48/48` Real-HW Rounds · Wave-61 · `142nd..144th` Live Runs -> `144/144` Total Live Runs, `96/96` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-61 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md`](../2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 75 轮（Wave-61 · `48/48` 实机轮次 / `142nd..144th` -> `144/144` 次实跑 / `96/96` PNG）三项实机预演总览（`r75a` / `r75b` / `r75c`）

| 实跑场景 | Run ID | `r75_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **75A（第 142 次实跑）：Wave-61 四大支柱 — `[FTP Transfer Func.]` `9` 槽/`FTP`+`FTPES`/零 `SFTP`/`Slot 1` `AVF_INFO` `EROFS=30` & `USB-LAN` 零射频、`[White Balance]` `Custom 1..3` 排除 `CAMSET*.DAT`/抗复位 `Shutter AWB Lock`/`Shockless WB`/`Cine EI`、`Movie AF` `1..7` / `1..5` 同源 & App 独占 `Focus Map`、`Marker` `15` 比例 & `Peaking` `4` 色 Clean-HDMI `0 px` + Big-6 Home** | `r75a` | `ftp_ftpes_customwb_afspeed_focusmap_marker_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[FTP Transfer Func.]`** `Server 1..9`（`BKID_APP_ftp_server_settings_*0..8`，第 10 槽 `-95`）、`FTP` + `FTPES` Explicit TLS（`SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`）、零 `SFTP` / 零 Active Mode / 休眠 `Transfer JPEG Size`（均 `-95`）、`cacert.pem` `Slot 1` 根目录导入（`Slot 2` `-22`）、**`Slot 1` `CONTENT_INFO_FTP_TRANS_STAT` / `AVF_INFO` 写阻断（`-30 EROFS`）**与 **`Airplane Mode=On` + `USB-LAN` 断开零射频/零有线阻断（`-100 ENETDOWN`, `rf_tx_packets=0`, `usb_lan_tx_packets=0`）**；(2) 核验 **`[White Balance]`** `2500K..9900K`、`Custom 1..3` 排除 `CAMSET*.DAT`（`-95`）、`[Priority Set in AWB]`、Still 抗复位 `[Shutter AWB Lock]`、Movie `[Shockless WB]`、Log/`S-Log3` `Custom WB Error` 与 `Cine EI` Auto 锁定（`-16 EBUSY`）、FX6 `ATW` 在 FX3 阻断（`-95`）；(3) 核验 **`Movie AF`** `[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sens.]` **`1..5`（FX3 与 FX6 均止于 5 级，`6`/`7` 均 `-95`）**、`[AF Assist]`、*Monitor & Control* App 独占 `[Focus Map]`（`120fps` 允许 `rc=0` vs `240fps` `>=150fps` 锁定 `-16`，机身内 Focus Map 与 UVC 均 `-95`）；(4) 核验 **`[Marker Display]`**（`Off` + `15` 比例 = `16` 态、`Safety Zone`、`Guideframe`）& **`4` 色 `[Peaking Display]`**（`Red/Yellow/Blue/White`，`hdmi_marker_baked_pixels=0`, `hdmi_peaking_baked_pixels=0`，FX6 `User Box` & `B&W` Peaking 在 FX3 `-95`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r75_init_ok=1`, `r75_bridge_ok=1`, `verify_us=988336`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.63s` | [`r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-composited.png`](assets/r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-composited.png) |
| **75B（第 143 次实跑）：Fail-Closed Wave-61 防火墙 — 休眠 `SFTP`/Implicit990/ActiveFTP/`Transfer JPEG Size`/第 10 槽、`Slot 2` `cacert`、`Cloud`/`FX6 Chunk` 互斥、`Slot 1` `AVF_INFO` `EROFS=30` & `USB-LAN` 零射频、`Custom WB` `CAMSET` & `Cine EI`/`2400K`/`10000K`、`AF Shift 6/7` & 机身 `Focus Map`/`UVC`/`240fps`、`FX6 User Box`/`B&W` Peaking 全面阻断** | `r75b` | `wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `SFTP` / Implicit FTPS 990 / Active FTP / `Transfer JPEG Size` / 第 `10` FTP 槽位（`-95 EOPNOTSUPP`）、`Slot 2` `cacert.pem`（`-22 EINVAL`）、`Cloud<->FTP` & FX6 `Chunk<->Simul/Relay` 互斥（`-16 EBUSY`）、**`Slot 1` `AVF_INFO` `CONTENT_INFO_FTP_TRANS_STAT`（`-30 EROFS`）**与 **`Airplane Mode=On` + `USB-LAN` 零射频/零有线 Containment（`-100 ENETDOWN`, `rf_tx_packets=0`, `usb_lan_tx_packets=0`）**；(2) 拦截 `2400K`/`10000K` 越界（`-22`）、`Custom 1..3` 写入 `CAMSET*.DAT`（`-95`）、`Cine EI` Auto/UW-Auto & `S-Log3` `Custom WB Error`（`-16`）、FX6 `ATW`（`-95`）；(3) 拦截 AF Speed `8` 越界（`-22`）、**FX3 `AF Shift 6` & FX6 `AF Shift 7`（`-95`）**、`SELP1650` `AF Assist`/机身 `Focus Map`/休眠 `UVC`（`-95`）、*M&C* `Focus Map` `240fps`/Playback/Auto Framing/非 PDAF（`-16`）；(4) 拦截 FX6 `User Box`/`B&W` Peaking/UM 3 格网格（`-95`）、Aspect `16` 越界（`-22`），以及 **`Slot-1` Wave-61 / `AVF_INFO` / `p12` / `P2` / `cnflasha` 写入（`-30 EROFS`）**（`slot1_vault_sha256_match=1`, `rf_tx_packets=0`, `usb_lan_tx_packets=0`, `wireless_tx_packets=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r75b_ok=1`, `verify_us=1038846`, `FX6_R75_WAVE61_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `10.73s` | — |
| **75C（第 144 次实跑 · `48/48` 实机轮次 closure）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-61 `[Camera Settings Reset]` / `[Reset Network Set.]` / `[Initialize]` 三态非对称持久化验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r75c` | `clean_unmount_wave61_reset_h0_h3_big6` | Native ARM64 Wave-61 联合预演（**`48/48` 实机轮次 · 第 `144/144` 次独立实跑 · `96/96` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三态非对称复位层级：**`[Camera Settings Reset]` 复位活动 `WB`（`Auto`）、`Priority Set in AWB`、`Shockless WB`、`AF Transition Speed`/`Subj. Shift Sens.`/`AF Assist` 及 *M&C* `Focus Map`，同时完整保留 Still 独占抗复位 `[Shutter AWB Lock]`、`Custom 1..3` 校准槽、全部 `8` 项 `[Marker Display]` + `[Peaking Display]`、`[FTP Transfer Func.]`/Server `1..9`/`cacert.pem` 与 `[Airplane Mode]=On`**（`camreset_resets_wb_af_focusmap_preserves_shutterlock_8markerpeak_ftp_ok=1`）；**`[Reset Network Set.]` 清除 `FTP Function`/`Server 1..9`/`cacert.pem`/`FTP Power Save` 同时严格保留 `[Airplane Mode]=On`、`[Shutter AWB Lock]` 与全部 `8` 项 Marker+Peaking**（`nwreset_clears_ftp9_cacert_preserves_marker8_shutterlock_airplane_ok=1`）；**`[Initialize]` 清除 `[Shutter AWB Lock]`、`Custom 1..3` 与全部 `8` 项 Marker+Peaking 同时依然保持 `[Airplane Mode]=On`**（`initialize_clears_shutterlock_customwb_8markerpeak_preserves_airplane_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `rf_tx_packets=0`, `usb_lan_tx_packets=0`, `wireless_tx_packets=0`, `slot1_ftp_trans_stat_writes=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=51`, `verify_us=486604`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `80.84s` | 同 `75A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-61 四大支柱初始化与 Stage-B 四路桥接（`r75a` — 第 142 次实跑）
```text
FX6_R75_WAVE61_INIT fx3_wave61_nodes_ok=1 uxc_tokens_ok=1 ftp_ftpes_zerorf_erofs_ok=1
  customwb_awblock_shockless_cineei_ok=1 af_speed_sens_focusmap_app_ok=1 marker15_peaking4_clean_hdmi_ok=1
  ftp_10th_slot_rc=-95 ftp_sftp_dormant_rc=-95 ftp_active_mode_rc=-95 ftp_jpeg_size_dormant_rc=-95
  ftp_slot2_cert_rc=-22 ftp_slot1_erofs_rc=-30 ftp_zerorf_tx_rc=-100
  wb_custom_camset_excl_rc=-95 wb_cineei_auto_lock_rc=-16 wb_slog3_custom_err_rc=-16 fx6_atw_fx3_rc=-95
  af_inbody_focusmap_rc=-95 af_shift_7_fx3_rc=-95 af_shift_7_fx6_rc=-95 af_uvc_dormant_rc=-95
  af_focusmap_240fps_lock_rc=-16 af_focusmap_120fps_ok=1
  fx6_userbox_fx3_rc=-95 fx6_peaking_bw_fx3_rc=-95
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_sftp_bypass_events=0 dormant_active_ftp_bypass_events=0 dormant_transfer_jpeg_size_bypass_events=0
  dormant_inbody_focus_map_bypass_events=0 dormant_uvc_bypass_events=0 dormant_af_shift_7_bypass_events=0
  hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0
  rf_tx_packets=0 usb_lan_tx_packets=0 wireless_tx_packets=0
  slot1_ftp_trans_stat_writes=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r75_init_ok=1 verify_us=988336

FX6_STAGE_B_R75_BRIDGE round=75 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19
  ftp_9servers_ftpes_passive_vs_zero_sftp_erofs30=1
  customwb_awblock_reset_immune_shockless_cineei=1
  af_speed_1_7_sens_1_5_app_focusmap_150fps=1
  marker_15ratio_peaking_4color_reset_immune_clean_hdmi=1
  milestone_48th_realhw_144th_live_96_pngs=1
  dormant_sftp_bypass_events=0 dormant_active_ftp_bypass_events=0 dormant_transfer_jpeg_size_bypass_events=0
  dormant_inbody_focus_map_bypass_events=0 dormant_uvc_bypass_events=0 dormant_af_shift_7_bypass_events=0
  hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0
  rf_tx_packets=0 usb_lan_tx_packets=0 wireless_tx_packets=0
  slot1_ftp_trans_stat_writes=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0

FX6_R75_FTP_FTPES_ZERORF_EROFS_BRIDGE ftp_9servers_ftpes_passive_only_ok=1
  slot1_avf_erofs_and_usblan_zerorf_ok=1 ftp_ftpes_zerorf_erofs_ok=1
  dormant_sftp_bypass_events=0 dormant_active_ftp_bypass_events=0 dormant_transfer_jpeg_size_bypass_events=0
  slot1_ftp_trans_stat_writes=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  rf_tx_packets=0 usb_lan_tx_packets=0 wireless_tx_packets=0 emmc_write_count=0 r75_bridge_ok=1

FX6_R75_CUSTOMWB_AWBLOCK_SHOCKLESS_CINEEI_BRIDGE customwb_2500_9900k_camset_excl_ok=1
  awblock_reset_immune_shockless_cineei_ok=1 customwb_awblock_shockless_cineei_ok=1 cnflasha_writes=0 emmc_write_count=0

FX6_R75_AF_SPEED_SENS_FOCUSMAP_APP_BRIDGE af_speed_1_7_sens_1_5_shared_ok=1
  focusmap_mc_app_only_150fps_cutoff_ok=1 af_speed_sens_focusmap_app_ok=1
  dormant_inbody_focus_map_bypass_events=0 dormant_uvc_bypass_events=0 dormant_af_shift_7_bypass_events=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R75_MARKER15_PEAKING4_CLEAN_HDMI_BRIDGE marker_15_ratio_8_reset_immune_ok=1
  peaking_4color_clean_hdmi_0px_ok=1 marker15_peaking4_clean_hdmi_ok=1
  hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `60` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`154` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-61 防火墙拦截明细（`r75b` — 第 143 次实跑）
```text
FX6_R75_WAVE61_GUARD ftp_sftp_dormant_rc=-95 ftp_implicit990_rc=-95 ftp_active_mode_rc=-95
  ftp_jpeg_size_dormant_rc=-95 ftp_10th_slot_rc=-95 ftp_slot2_cert_rc=-22 ftp_cloud_excl_rc=-16
  ftp_slot1_avf_erofs_rc=-30 ftp_zerorf_tx_rc=-100 ftp_usblan_containment_rc=-100 fx6_chunk_simul_excl_rc=-16
  wb_2400k_oob_rc=-22 wb_10000k_oob_rc=-22 wb_custom_camset_excl_rc=-95 wb_cineei_auto_lock_rc=-16
  wb_cineei_uw_lock_rc=-16 wb_slog3_custom_err_rc=-16 fx6_atw_fx3_rc=-95
  af_speed_8_oob_rc=-22 af_shift_6_fx3_rc=-95 af_shift_7_fx6_rc=-95 af_assist_selp1650_rc=-95
  af_inbody_focusmap_rc=-95 af_uvc_dormant_rc=-95 af_focusmap_240fps_lock_rc=-16
  af_focusmap_pb_lock_rc=-16 af_focusmap_autoframe_lock_rc=-16 af_focusmap_nonpdaf_lock_rc=-16
  fx6_userbox_fx3_rc=-95 fx6_peaking_bw_fx3_rc=-95 um_3grid_fx3_rc=-95 aspect_16_oob_rc=-22
  slot1_wave61_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_sftp_bypass_events=0 dormant_active_ftp_bypass_events=0 dormant_transfer_jpeg_size_bypass_events=0
  dormant_inbody_focus_map_bypass_events=0 dormant_uvc_bypass_events=0 dormant_af_shift_7_bypass_events=0
  hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0
  rf_tx_packets=0 usb_lan_tx_packets=0 wireless_tx_packets=0
  slot1_ftp_trans_stat_writes=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r75b_ok=1 verify_us=1038846
FX6_R75_WAVE61_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-61 三态复位与 `16/16 H0 == H3`（`r75c` — 第 144 次实跑）
```text
FX6_R75_CLEAN_UNMOUNT_WAVE61_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_wb_af_focusmap_preserves_shutterlock_8markerpeak_ftp_ok=1
  nwreset_clears_ftp9_cacert_preserves_marker8_shutterlock_airplane_ok=1
  initialize_clears_shutterlock_customwb_8markerpeak_preserves_airplane_ok=1
  dormant_sftp_bypass_events=0 dormant_active_ftp_bypass_events=0 dormant_transfer_jpeg_size_bypass_events=0
  dormant_inbody_focus_map_bypass_events=0 dormant_uvc_bypass_events=0 dormant_af_shift_7_bypass_events=0
  hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0
  rf_tx_packets=0 usb_lan_tx_packets=0 wireless_tx_packets=0
  slot1_ftp_trans_stat_writes=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r75c_ok=1 verify_us=486604
```

---

## 3. `r75a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r75a` Alpha（`26.50 KiB` / `27,132 B`） | `r75a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r75a Big6 Alpha](assets/r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-alpha.png) | ![r75a Big6 Composited](assets/r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）Wi-Fi / `USB-LAN` / 以太网台架（验证 `Server 1..9` 实网 `FTP` 与 `FTPES` Explicit TLS 上传、`Slot 1` 根目录 `cacert.pem` 导入、Passive-only 数据端口与零 `SFTP` / 零 Active Mode、`[Airplane Mode]=On` + `[USB-LAN/Tethering]` 断开零射频/零有线 Containment，以及 `Slot 1` `AVF_INFO` 写保护 `EROFS=30` 对比 `FX6` `Chunk` 与 `Slot B` `certification.pem`）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）光学/传感器白平衡台架（验证 `Custom WB 1..3` 实拍采白不写入 `CAMSET*.DAT`、Still 独占抗 `[Camera Settings Reset]` 的 `[Shutter AWB Lock]`、Movie `[Shockless WB]` 过渡、`Log`/`S-Log3` `Custom WB Error` 告警与 `Cine EI` Auto/Underwater Auto 锁定，对比 `FX6` `Memory A..H` 与 `ATW Speed 1..5`）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）E 卡口镜头 AF、*Monitor & Control* App 与 HDMI 分析仪台架（验证 `[AF Transition Speed]` `1..7`、`[AF Subj. Shift Sens.]` `1..5`、`[AF Assist]` 对 `SELP1650`/`SEL18200LE` 的门禁、*M&C* App 独占 `[Focus Map]` 在 `>= 150 fps` / 回放 / Auto Framing 下的锁定、`15` 比例 `[Marker Display]` + `4` 色 `[Peaking Display]` 抗 Reset 持久化，以及 Clean/Info HDMI 输出 `0` 叠加像素隔离）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 75A (142nd Live Run): Wave-61 4-Pillar [FTP Transfer Func.] 9 Servers / FTP+FTPES / Zero SFTP / Slot 1 AVF_INFO EROFS=30 & USB-LAN Zero-RF, [White Balance] Custom 1..3 / Reset-Immune Shutter AWB Lock / Shockless WB / Cine EI, Movie AF 1..7 & 1..5 Shared + M&C App-Only Focus Map, and 15-Ratio Marker + 4-Color Peaking Clean-HDMI 0px + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 75 --r75-mode ftp_ftpes_customwb_afspeed_focusmap_marker_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r75a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round75-qemu/r75a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese \
  --export-png-dir reports/2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu/assets

# Run 75B (143rd Live Run): Fail-Closed Wave-61 Guard (Dormant SFTP/Implicit990/Active/TransferJPEGSize/10th Slot EOPNOTSUPP, Slot 1 AVF_INFO EROFS=30, Airplane+USB-LAN Zero-RF ENETDOWN, CustomWB CAMSET/Cine EI, AF Shift 6/7 FX3&FX6 EOPNOTSUPP, App Focus Map 240fps EBUSY, FX6 UserBox/B&W Peaking EOPNOTSUPP)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 75 --r75-mode wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r75b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round75-qemu/r75b

# Run 75C (144th Live Run — 48/48 Real-HW Rounds / 144/144 Live Runs / 96/96 PNGs): Clean Unmount Stock FX3 Restoration, Wave-61 3-Tier Asymmetric Reset Split (Camera Settings Reset / Reset Network Set. / Initialize) + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 75 --r75-mode clean_unmount_wave61_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r75c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round75-qemu/r75c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_sftp_bypass_events == 0`、`dormant_active_ftp_bypass_events == 0`、`dormant_transfer_jpeg_size_bypass_events == 0`、`dormant_inbody_focus_map_bypass_events == 0`、`dormant_uvc_bypass_events == 0`、`dormant_af_shift_7_bypass_events == 0`、`hdmi_marker_baked_pixels == 0`、`hdmi_peaking_baked_pixels == 0`、`rf_tx_packets == 0`、`usb_lan_tx_packets == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_ftp_trans_stat_writes == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
