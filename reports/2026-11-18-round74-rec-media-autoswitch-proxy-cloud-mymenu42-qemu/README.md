# Round 74（Wave-60 · `47/47` 实机预演轮次 `R28..R74` · 第 `139..141` 次实跑 -> `141/141` 总实跑 · `94/94` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `[Recording Media]` 拆分与 `[Auto Switch Media]`（`BKID_APP_setting_relay_rec`、`VPG200/400`）vs 休眠 `[Prioritize Rec. Media]`、`[Proxy Settings]` `sq_proxy` + `M4ROOT/SUB/*S03.MP4`（`DCI 4K` 允许 vs `120p` 锁定）& `Slot 1` `EROFS=30`、`[Creators' Cloud]` `Initialize` 免疫 `*` & `[Cnct. while Power OFF]` 零射频 BLE vs 无蓝牙 FX6，以及 `6x7=42` 槽位 `[My Menu]` vs FX6 `20` 项 `[User Menu with Lock]`

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 74** 三路独立 QEMU 实机预演（`r74a` / `r74b` / `r74c`，达成 **`47/47` 实机预演轮次 `R28..R74` · `141/141` 次独立实跑 · `94/94` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dormant_prioritize_bypass_events == 0`、`dormant_prm_haita_proxy_bypass_events == 0`、`dormant_mymenu_oob_bypass_events == 0`、`slot1_spillover_events == 0`、`poweroff_ble_rf_tx_packets == 0`、`rf_tx_packets == 0`、`wireless_tx_packets == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r74c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r74a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 60 四大支柱门禁、休眠符号（`[Prioritize Rec. Media]` `_f 0x719e` `0` 命中、视频 `Sort Recording` `0` 命中、`CFexpress Type B` `0` 命中、`PRM_HAITA_*proxy*` `0` 命中、`16M/9M 4:2:0 8bit` Proxy 休眠、`BKID_APP_mymenu_group0`/`group7`/`list7` `0` 命中、`FX6` 蓝牙 `BKID_APP_SETTING_BLUETOOTH_FUNCTION` 休眠）的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-28 ENOSPC` / `-100 ENETDOWN` 拦截，Ver. 2.00+..7.02 拆分且免 `Camera Settings Reset` 复位的静态/视频 `[Recording Media]`（`BKID_APP_setting_still_recording_media` 支持 `Sort Recording` vs `BKID_APP_setting_movie_recording_media` 无 `Sort`）+ `[Auto Switch Media]`（`BKID_APP_setting_relay_rec`，Slot 2 满卡溢出至 Slot 1 由 Tier-0 Vault `-30 EROFS` 阻断）+ `CFexpress VPG200/VPG400` 速率门禁对比 `ILME-FX6` `Simul Rec` 与双录制键，`[Proxy Settings]` `sq_proxy`（默认 `XAVC S HD 6M 8bit` vs `XAVC HS HD 9M/16M 10bit`，**`XAVC S-I DCI 4K`（<= 59.94p/50p）允许录制代理**而仅 Movie/`S&Q` `119.88p/100p`/`120fps/100fps` 锁定，`/M4ROOT/SUB/<Clip>S03.MP4` 边车写入与关联删除在 `Slot 1` 触发 `-30 EROFS`）对比 `FX6` `1080p 9M AVC` + `Slot B Chunk`，`[Creators' Cloud]`（`Cloud Connection *` / `Cloud Information *` 甚至跨越 `[Initialize]` 持续留存，仅显式解绑可清除；`[Cnct. while Power OFF]` `_f 0x6ab3` + `Always Connected` `_f 0x6833` 在物理关机态维持 BLE 供电而于零射频模式被 `[Airplane Mode]=On` 阻断发包）对比无蓝牙 `FX6`，`[My Menu]` 精确 `6x7=42` NVRAM 槽位（`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`，非 30 或 36 槽，43 槽 `-28 ENOSPC`，回放项禁用 `-95`）对比 `FX6` `20` 项 `[User Menu]` + `[User Menu with Lock]`（`0000..9999` PIN），以及四态非对称复位层级（`Camera Settings Reset` / `Reset Network Set.` / `Initialize` / 显式 Cloud 解绑）；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（双卡槽 SDXC + CFexpress A VPG200/400 溢卡实写与写保护锁、XAVC S-I DCI 4K + `M4ROOT/SUB/*S03.MP4` 实时代理录制、RF 屏蔽箱关机 BLE 唤醒与 Creators' Cloud 配对、`42` 槽 My Menu 真机 NVRAM 持久性）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 74 (`47/47` Real-HW Rounds · Wave-60 · `139th..141st` Live Runs -> `141/141` Total Live Runs, `94/94` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-60 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel/README.md`](../2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 74 轮（Wave-60 · `47/47` 实机轮次 / `139th..141st` -> `141/141` 次实跑 / `94/94` PNG）三项实机预演总览（`r74a` / `r74b` / `r74c`）

| 实跑场景 | Run ID | `r74_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **74A（第 139 次实跑）：Wave-60 四大支柱 — 拆分 `[Recording Media]` + `[Auto Switch Media]` vs 休眠 `[Prioritize]`、`[Proxy Settings]` `sq_proxy` DCI 4K 允许/`120p` 锁定 + `S03.MP4` `Slot-1` `EROFS=30`、`[Creators' Cloud]` `*` 免疫复位 & 关机 BLE 零射频、`6x7=42` 槽位 `[My Menu]` vs FX6 `[User Menu with Lock]` + Big-6 Home** | `r74a` | `rec_media_autoswitch_proxy_cloud_mymenu42_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Rec. Media Settings]`** 拆分：静态 `BKID_APP_setting_still_recording_media`（`Slot 1`[def]/`Slot 2`/`Simult.`/`Sort Recording`）vs 视频 `BKID_APP_setting_movie_recording_media`（无视频 `Sort`，`0` 命中 `prioritize` -> `-95 EOPNOTSUPP`，`Simult.` 混合 exFAT/FAT32 `-22 EINVAL`）与 **`[Auto Switch Media]`**（`BKID_APP_setting_relay_rec`，Slot 2->Slot 1 溢出写被 `-30 EROFS` 阻断）+ `CFexpress VPG200/VPG400` 门禁（`-16 EBUSY`）；(2) 核验 **`[Proxy Settings]`** `sq_proxy`（`XAVC S HD 6M 8bit`[def] vs `XAVC HS HD 9M/16M 10bit`，**`XAVC S-I DCI 4K`（<=59.94p/50p）允许 `rc=0`** vs `120p`/`S&Q 120fps` `-16 EBUSY`，休眠 `PRM_HAITA_*proxy*` & `16M 8bit` `-95`，`M4ROOT/SUB/*S03.MP4` 在 `Slot 1` `-30 EROFS`）；(3) 核验 **`[Creators' Cloud]`** `Cloud Connection *` / `Cloud Information *`（免疫 `Initialize`，与 FTP 互斥 `-16`）& **`[Cnct. while Power OFF]`**（`_f 0x6ab3` + `Always Connected` `_f 0x6833` 在零射频模式下 `-100 ENETDOWN`, `poweroff_ble_rf_tx_packets=0`）对比无蓝牙 FX6（`-95`）；(4) 核验 **`[My Menu]`** 精确 **`6x7=42` 槽位**（`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`，`group0`/`group7`/`list7` `-95`，第 43 槽 `-28 ENOSPC`，回放项禁用 `-95`）对比 FX6 `20` 项 `User Menu` + `User Menu with Lock`，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r74_init_ok=1`, `r74_bridge_ok=1`, `verify_us=991962`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `78.18s` | [`r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-composited.png`](assets/r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-composited.png) |
| **74B（第 140 次实跑）：Fail-Closed Wave-60 防火墙 — 休眠 `Prioritize`/`CFexpress B`/`PRM_HAITA`/回放项/FX6 锁、`Simult.` 混格式、`VPG200/400` & `Proxy 120p` 互斥、关机 BLE 零射频阻断、`My Menu` `43` 槽 `ENOSPC` 与 `Slot-1` `S03.MP4`/溢出 `EROFS=30`** | `r74b` | `wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `[Prioritize Rec. Media]` / 视频 `Sort Recording` / `CFexpress B`（`-95 EOPNOTSUPP`）、`Simult.` exFAT+FAT32 混插（`-22 EINVAL`）、`SDXC S&Q 1200M VPG200` & `600M+Proxy VPG400` 门禁（`-16 EBUSY`）及 **`Slot-1` 溢出与 `Simult.` 写入（`-30 EROFS`）**；(2) 拦截 `120p` / `S&Q 120fps` Proxy & FX6 `Simul+Proxy` 互斥（`-16`）、休眠 `16M 8bit` / `9M 8bit` / `PRM_HAITA_*proxy*` / 机内回放 Proxy（`-95`）及 **`Slot-1` `M4ROOT/SUB/*S03.MP4` 写入与关联删除（`-30 EROFS`）**；(3) 拦截 `Cloud+FTP` 互斥（`-16`）、`[Cnct. while Power OFF]` BLE 零射频发包（`-100 ENETDOWN`, `poweroff_ble_rf_tx_packets=0`）及无蓝牙 FX6 BT（`-95`）；(4) 拦截 `My Menu` `group0`/`group7`/`list7` 越界与回放项（`-95`）、第 `43` 槽 & FX6 第 `21` 槽（`-28 ENOSPC`）、FX3 侧 `User Menu Lock PIN`（`-95`），以及 **`Slot-1` Wave-60 / `AVF_INFO` / `p12` / `P2` / `cnflasha` 写入（`-30 EROFS`）**（`slot1_vault_sha256_match=1`, `rf_tx_packets=0`, `wireless_tx_packets=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r74b_ok=1`, `verify_us=1003760`, `FX6_R74_WAVE60_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.3s` | — |
| **74C（第 141 次实跑 · `47/47` 实机轮次 closure）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-60 `[Camera Settings Reset]` / `[Reset Network Set.]` / `[Initialize]` / 显式 Cloud 解绑四态持久化验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r74c` | `clean_unmount_wave60_reset_h0_h3_big6` | Native ARM64 Wave-60 联合预演（**`47/47` 实机轮次 · 第 `141/141` 次独立实跑 · `94/94` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证四态非对称复位层级：**`[Camera Settings Reset]` 复位 `[Proxy Settings]` 为 `Off / XAVC S HD 6M 8bit`，同时完整保留免复位的 `[Recording Media]`、`[Auto Switch Media]`、`[Cnct. while Power OFF]`、全部 `42` 槽 `[My Menu]`、`[Airplane Mode]=On` 与 `[Creators' Cloud *]`**（`camreset_resets_proxy_preserves_media_ble_mymenu_cloud_ok=1`）；**`[Reset Network Set.]` 清除 `[Cnct. while Power OFF]` / `Always Connected` 同时严格保留 `[Cloud Connection *]`/`[Cloud Information *]`、`[Airplane Mode] = On` 零射频与介质/MyMenu 配置**（`nwreset_clears_poweroff_ble_preserves_cloud_star_and_airplane_ok=1`）；**`[Initialize]` 清除 `[Recording Media]`、`[Auto Switch Media]` 与全部 `42` 槽 `[My Menu]`，而 `[Cloud Connection *]`/`[Cloud Information *]` 依然留存直至显式执行 Cloud Information 解绑**（`initialize_clears_media_mymenu42_preserves_cloud_star_ok=1`, `explicit_cloud_unlink_clears_star_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `poweroff_ble_rf_tx_packets=0`, `rf_tx_packets=0`, `wireless_tx_packets=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`osd=65`，`verify_us=468434`，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.44s` | 同 `74A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-60 四大支柱初始化与 Stage-B 四路桥接（`r74a` — 第 139 次实跑）
```text
FX6_R74_WAVE60_INIT fx3_wave60_nodes_ok=1 uxc_tokens_ok=1 rec_media_autoswitch_vpg_ok=1
  proxy_sq_m4root_sub_ok=1 cloud_star_poweroff_ble_ok=1 mymenu42_fx6_lock_ok=1
  prioritize_dormant_rc=-95 movie_sort_absent_rc=-95 simult_mixed_fs_rc=-22
  slot1_spillover_erofs_rc=-30 vpg200_sdxc_sq_lock_rc=-16 vpg400_proxy_lock_rc=-16 cfex_b_dormant_rc=-95
  proxy_120p_lock_rc=-16 proxy_sq_120fps_lock_rc=-16 proxy_dci4k_ok_rc=0
  proxy_prm_haita_dormant_rc=-95 proxy_16m_8bit_dormant_rc=-95 proxy_slot1_s03_erofs_rc=-30
  cloud_ftp_excl_rc=-16 poweroff_ble_zerorf_tx_rc=-100 fx6_bt_dormant_rc=-95
  mymenu_group0_rc=-95 mymenu_group7_rc=-95 mymenu_list7_rc=-95 mymenu_43rd_full_rc=-28
  mymenu_playback_item_rc=-95 fx6_user_menu_lock_pin_rc=-95
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_prioritize_bypass_events=0 dormant_prm_haita_proxy_bypass_events=0 dormant_mymenu_oob_bypass_events=0
  slot1_spillover_events=0 poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r74_init_ok=1 verify_us=991962

FX6_STAGE_B_R74_BRIDGE round=74 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19
  rec_media_split_vs_dormant_prioritize_autoswitch_vpg=1
  proxy_sq_dci4k_vs_120p_m4root_sub_erofs30=1
  creators_cloud_star_init_persist_poweroff_ble_zerorf=1
  mymenu_6x7_42_slots_vs_fx6_20_user_menu_lock=1
  milestone_47th_realhw_141st_live_94_pngs=1
  dormant_prioritize_bypass_events=0 dormant_prm_haita_proxy_bypass_events=0 dormant_mymenu_oob_bypass_events=0
  slot1_spillover_events=0 poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0

FX6_R74_REC_MEDIA_AUTOSWITCH_VPG_BRIDGE split_rec_media_vs_dormant_prioritize_ok=1
  auto_switch_slot1_spillover_vpg_gates_ok=1 rec_media_autoswitch_vpg_ok=1
  dormant_prioritize_bypass_events=0 slot1_spillover_events=0 emmc_write_count=0 r74_bridge_ok=1

FX6_R74_PROXY_SQ_M4ROOT_SUB_EROFS_BRIDGE proxy_sq_dci4k_vs_120p_lockout_ok=1
  proxy_m4root_sub_s03_erofs30_ok=1 proxy_sq_m4root_sub_erofs_ok=1
  dormant_prm_haita_proxy_bypass_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R74_CLOUD_STAR_POWEROFF_BLE_ZERORF_BRIDGE cloud_star_init_persistence_ok=1
  poweroff_ble_zerorf_containment_ok=1 cloud_star_poweroff_ble_zerorf_ok=1
  poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0 cnflasha_writes=0 emmc_write_count=0

FX6_R74_MYMENU42_FX6_LOCK_BRIDGE mymenu_6x7_42_slots_nvram_ok=1
  fx6_20_user_menu_lock_diff_ok=1 mymenu42_fx6_lock_ok=1
  dormant_mymenu_oob_bypass_events=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `63` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`159` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-60 防火墙拦截明细（`r74b` — 第 140 次实跑）
```text
FX6_R74_WAVE60_GUARD prioritize_dormant_rc=-95 movie_sort_absent_rc=-95 simult_exfat_fat32_mix_rc=-22
  slot1_spillover_erofs_rc=-30 simult_erofs_rc=-30 sq_1200m_sdxc_vpg_rc=-16 proxy_600m_vpg400_lock_rc=-16
  cfex_b_dormant_rc=-95 proxy_120p_lock_rc=-16 proxy_sq_120fps_lock_rc=-16
  proxy_16m_8bit_dormant_rc=-95 proxy_9m_8bit_dormant_rc=-95 proxy_prm_haita_dormant_rc=-95
  proxy_playback_in_cam_rc=-95 proxy_slot1_s03_erofs_rc=-30 proxy_slot1_coupled_del_erofs_rc=-30
  fx6_simul_proxy_excl_rc=-16 cloud_ftp_excl_rc=-16
  poweroff_ble_zerorf_tx_rc=-100 poweroff_ble_containment_tx_rc=-100 fx6_bt_dormant_rc=-95
  mymenu_group0_oob_rc=-95 mymenu_group7_oob_rc=-95 mymenu_list7_oob_rc=-95
  mymenu_43rd_enospc_rc=-28 mymenu_playback_disallowed_rc=-95
  fx6_user_menu_lock_pin_rc=-95 fx6_user_menu_21st_enospc_rc=-28
  slot1_wave60_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_prioritize_bypass_events=0 dormant_prm_haita_proxy_bypass_events=0 dormant_mymenu_oob_bypass_events=0
  slot1_spillover_events=0 poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r74b_ok=1 verify_us=1003760
FX6_R74_WAVE60_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-60 四态复位与 `16/16 H0 == H3`（`r74c` — 第 141 次实跑）
```text
FX6_R74_CLEAN_UNMOUNT_WAVE60_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_proxy_preserves_media_ble_mymenu_cloud_ok=1
  nwreset_clears_poweroff_ble_preserves_cloud_star_and_airplane_ok=1
  initialize_clears_media_mymenu42_preserves_cloud_star_ok=1
  explicit_cloud_unlink_clears_star_ok=1
  dormant_prioritize_bypass_events=0 dormant_prm_haita_proxy_bypass_events=0 dormant_mymenu_oob_bypass_events=0
  slot1_spillover_events=0 poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r74c_ok=1 verify_us=468434
```

---

## 3. `r74a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r74a` Alpha（`26.50 KiB` / `27,132 B`） | `r74a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r74a Big6 Alpha](assets/r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-alpha.png) | ![r74a Big6 Composited](assets/r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）双卡槽 `SDXC UHS-II` + `CFexpress Type A`（`VPG200`/`VPG400`）台架（验证静态与视频 `[Recording Media]` 拆分、`[Auto Switch Media]` 满卡无缝切换至另一卡槽及 `Slot 1` 物理写保护 `EROFS=30`、exFAT/FAT32 混插拒绝与 `Simul.` 双卡同步写盘）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）`XAVC HS / S / S-I` 代理录卡台架（验证 `sq_proxy` 编码矩阵：`XAVC S HD 6M 8bit` 默认 vs `XAVC HS HD 9M/16M 10bit`、`XAVC S-I DCI 4K`（<= 59.94p/50p）允许代理 vs `120p`/`100p` 锁定、实时 `/M4ROOT/SUB/*S03.MP4` 边车写入与关联删除对比 `ILME-FX6` `Slot B Chunk`）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）射频屏蔽箱与 `Creators' Cloud` 配对台架（验证物理 `POWER=OFF` 下 `[Cnct. while Power OFF]` BLE 广播与手机端唤醒、`[Airplane Mode]=On` 零射频 Containment、`Cloud Connection *` / `Cloud Information *` 跨越 `[Initialize]` 留存凭证与显式解绑，以及 `6x7=42` 槽位 `[My Menu]` 真机 NVRAM 持久化）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 74A (139th Live Run): Wave-60 4-Pillar Split Rec. Media & Auto Switch (VPG200/400) vs Dormant Prioritize / sq_proxy DCI 4K vs 120p & M4ROOT/SUB/*S03.MP4 EROFS=30 / Initialize-Persistent Creators' Cloud * & Cnct. while Power OFF Zero-RF BLE / 6x7=42 NVRAM My Menu vs FX6 20-Item User Menu with Lock + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 74 --r74-mode rec_media_autoswitch_proxy_cloud_mymenu42_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r74a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round74-qemu/r74a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese \
  --export-png-dir reports/2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu/assets

# Run 74B (140th Live Run): Fail-Closed Wave-60 Guard (Dormant Prioritize/Movie Sort/CFex B EOPNOTSUPP, Spillover/S03.MP4 EROFS=30, Proxy 120p/VPG EBUSY, PowerOFF BLE Zero-RF ENETDOWN, MyMenu 43rd ENOSPC & OOB EOPNOTSUPP)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 74 --r74-mode wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r74b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round74-qemu/r74b

# Run 74C (141st Live Run — 47/47 Real-HW Rounds / 141/141 Live Runs / 94/94 PNGs): Clean Unmount Stock FX3 Restoration, Wave-60 4-State Reset Split (Camera Settings Reset / Reset Network Set. / Initialize / Explicit Cloud Unlink) + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 74 --r74-mode clean_unmount_wave60_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r74c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round74-qemu/r74c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_prioritize_bypass_events == 0`、`dormant_prm_haita_proxy_bypass_events == 0`、`dormant_mymenu_oob_bypass_events == 0`、`slot1_spillover_events == 0`、`poweroff_ble_rf_tx_packets == 0`、`rf_tx_packets == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
