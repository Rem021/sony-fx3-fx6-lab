# Round 73（Wave-59 · `46/46` 实机预演轮次 `R28..R73` · 第 `136..138` 次实跑 -> `138/138` 总实跑 · `92/92` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — Ver. 7.00/7.02 `[BIG6]` Home `Fixed/Variable` 前置条件与纯元数据 `ND Filter` vs FX6 物理 `e-ND`、手动 `[Framing Settings]` vs 100% 休眠 `[Auto Framing]` `EOPNOTSUPP=95`、静态 `[Interval Shoot Func.]` `9,999` 张连拍 vs FX6 单 MXF `[Interval Rec]` & `Slot 1` `EROFS=30`、免复位 `[Time Code Make/Run]` & HDMI `[REC Control]` + `[4ch Audio Output]`，以及 Ver. 7.00+ `[Access Authen.]` SSH/PTP-IP + 4 档 `[Fan Control]`（零 `Max`）

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 73** 三路独立 QEMU 实机预演（`r73a` / `r73b` / `r73c`，达成 **`46/46` 实机预演轮次 `R28..R73` · `138/138` 次独立实跑 · `92/92` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dormant_auto_framing_bypass_events == 0`、`dormant_http_auth_bypass_events == 0`、`dormant_fan_max_bypass_events == 0`、`rf_tx_packets == 0`、`wireless_tx_packets == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r73c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r73a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 59 四大支柱门禁、休眠符号（`[Auto Framing]` / `AUTO_FRAMING_AFR` / `FRAMING_SIZE` / `PTZAUTOFRAMING_*`、`TC_MAKE_CLOCK`、已移除 `WEP`/`WPA-PSK`/`IPsec`、`HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS`、`FAN_CONTROL_MAX` 在 FX3 与 FX6 上均 `0` 命中、FX6 `FAN_CONTROL_ALWAYS_OFF` 休眠）的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-2 ENOENT` 拦截，Ver. 7.00/7.02 `[BIG6]` Home（`Mode Settings = Fixed/Variable` 硬前置、`Home (Lower Left)` 默认 `Aperture` vs 纯元数据 `ND Filter`、`update_big6_item_iso_ei`、`Select LUT`）与手动 `[Framing Settings]`（`Recording/Streaming` `Full`/`Crop` + `HDMI` `Crop`/`Full`，`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`），静态 `[Interval Shoot Func.]`（7 项支持 `Camera Settings Reset`、强制默认 `Electronic Shutter`、`1..9,999` 张连拍写卡爆发）对比 FX6 单 XAVC MXF `[Interval Rec]` 及 `Slot 1` 恢复保险库 `-30 EROFS` 防火墙，免 `[Camera Settings Reset]` 复位的 `[Time Code Make/Run]`（`Regenerate` 在 `Simult. Recording` 读取 `Slot 1` 并强制按 `Rec Run` 运行；`VMC-BNCM1` `EXT-LK` 严格要求 `Preset + Free Run`）与 HDMI `[REC Control]`（强制先设 `[Time Code Output] = On`，在 `Rec. Media dur HDMI Output = On` 与 `Off(HDMI Only)` 下均有效）+ `[4ch Audio Output]`（`CH1/CH2` / `CH3/CH4` 立体声二选一），Ver. 7.00+ `[Access Authen.]`（SSH `MSGID_SSHD_START_CMD` + `PTP-IP` + `[Import Root Certificate]` 仅用于 FTPS/RTMPS/Cloud 出站 TLS）+ `[Airplane Mode] = On` 零射频（`ENETDOWN=100`），4 档 `[Fan Control]`（`Auto`/`Minimum`/`Off in Rec`/`Always Off` vs FX6 3 档）+ `[Auto Power OFF Temp.]`（`Standard`/`High`），以及三层非对称复位层级（`Camera Settings Reset` / `Reset Network Set.` / `Initialize`）；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（传感器裁剪读出、9,999 张机械/电子快门连拍时序与 `Slot 1` 物理写保护、`VMC-BNCM1` LTC 发生器、HDMI 4ch 音频汇接、OpenSSH/PTP-IP 网络台架与热风道温控箱验证）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 73 (`46/46` Real-HW Rounds · Wave-59 · `136th..138th` Live Runs -> `138/138` Total Live Runs, `92/92` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-59 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave59-big6-home-framing-interval-shoot-tc-make-run-auth-intel/README.md`](../2026-11-17-global-sony-wave59-big6-home-framing-interval-shoot-tc-make-run-auth-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 73 轮（Wave-59 · `46/46` 实机轮次 / `136th..138th` -> `138/138` 次实跑 / `92/92` PNG）三项实机预演总览（`r73a` / `r73b` / `r73c`）

| 实跑场景 | Run ID | `r73_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **73A（第 136 次实跑）：Wave-59 四大支柱 — Ver. 7.00/7.02 `[BIG6]` Home + 手动 `[Framing Settings]` vs 休眠 `[Auto Framing]`、静态 `[Interval Shoot Func.]` vs FX6 MXF & Slot-1 `EROFS=30`、免复位 `[Time Code Make/Run]` & HDMI `[REC Control]`/`[4ch Audio]`、Ver. 7.00+ `[Access Authen.]` SSH/PTP-IP + 4 档 `[Fan Control]` 零 `Max` + Big-6 Home** | `r73a` | `big6_framing_interval_tc_make_ssh_auth_fan_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[BIG6]` Home**（硬前置 `Mode Settings = Fixed/Variable` `BKID_APP_setting_fps_fixed_variable_select`、`[HOME]` / `[Swipe Down]` 入口、`Home (Lower Left)` 默认 `Aperture` vs 纯元数据 `ND Filter` 且 `e_nd_actuator_tx_count=0`、`update_big6_item_iso_ei` / `Select LUT`）与手动 **`[Framing Settings]`**（`Recording/Streaming` `Full`[def]/`Crop`、`HDMI` `Crop`[def]/`Full`、`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`）对比 100% 休眠 **`[Auto Framing]`**（`AUTO_FRAMING_AFR` `0` 命中，`-95 EOPNOTSUPP`）；(2) 核验静态 **`[Interval Shoot Func.]`**（7 项支持 `Camera Settings Reset`、默认 `Electronic Shutter`、`1..9,999` 张静态连拍，`DCIM/` 至多 `19,998` 文件写盘）对比 `FX6` 单 MXF **`[Interval Rec]`**（`FX3` 返回 `-2 ENOENT`）及 `Slot 1` `-30 EROFS`；(3) 核验免复位 **`[Time Code Make/Run]`**（`Regenerate` 在 `Simult. Recording` 读 `Slot 1` 并强锁 `Rec Run`；`VMC-BNCM1` `EXT-LK` 需 `Preset + Free Run`）与 HDMI **`[REC Control]`**（须 `Time Code Output = On`，在 `Rec. Media = On` 与 `Off(HDMI Only)` 均有效）+ **`[4ch Audio Output]`**（`CH1/CH2` / `CH3/CH4`）；(4) 核验 **`[Access Authen.]`**（`SSH` `MSGID_SSHD_START_CMD` + `PTP-IP`，移除 `WEP`/`WPA-PSK`/`IPsec`，`HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS` `0` 命中，出站 `[Import Root Certificate]`）+ **`[Airplane Mode] = On`** 零射频（`ENETDOWN=-100`）+ 4 档 **`[Fan Control]`**（`Auto`/`Minimum`/`Off in Rec`/`Always Off` vs `FX6` 3 档且 `Always Off` 休眠，FX3/FX6 **均 `0` 命中 `FAN_CONTROL_MAX`**）+ `[Auto Power OFF Temp.]`，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r73_init_ok=1`, `r73_bridge_ok=1`, `verify_us=945430`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.58s` | [`r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-composited.png`](assets/r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-composited.png) |
| **73B（第 137 次实跑）：Fail-Closed Wave-59 防火墙 — 无 `Fixed/Variable` `BIG6` / 休眠 `[Auto Framing]` / `100p` & 录制中 `Framing` 锁定、`10000`/`61s` 越界 & `iAuto` 忙 & `Slot-1` 连拍爆发 `EROFS=30`、`VMC` 非法组合 & 无 `TC Output` `REC Control`、`WEP`/`IPsec`/`HTTP_DIGEST`/`FAN_CONTROL_MAX` & 飞行模式射频阻断** | `r73b` | `wave59_big6_framing_interval_tc_ssh_fan_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截无 `Fixed/Variable` 开启 `BIG6`（`-16 EBUSY`）、休眠 `[Auto Framing]`（FX3 与 FX6 均 `-95 EOPNOTSUPP`）、`>=100p` 与录制/流媒体下变更 `Framing`（`-16 EBUSY`）、`FX6` 无手动 `Framing Settings`（`-2 ENOENT`）；(2) 拦截 `[Interval Shoot Func.]` `10000` 张/`61s` 越界（`-22 EINVAL`）、`Intelligent Auto` 启用（`-16 EBUSY`）、`FX3` 请求 `Interval Rec` 单 MXF（`-2 ENOENT`）以及 **`Slot-1` 单卡/同时录制 `9,999` 张连拍写盘爆发（`-30 EROFS`）**；(3) 拦截 `FX3` 休眠 `TC Make Clock`（`-95`）、`VMC-BNCM1` `EXT-LK` 配 `Regenerate` / `Rec Run`（`-22 EINVAL`）、`TC Output=Off` 或 `S&Q` 下开启 HDMI `REC Control`（`-16 EBUSY`）；(4) 拦截已移除 `WEP`/`IPsec`（`-95`）、休眠 `HTTP_DIGEST`（`-95`）、休眠 `FAN_CONTROL_MAX`（FX3 与 FX6 均 `-95`）、`FX6` 休眠 `FAN_CONTROL_ALWAYS_OFF`（`-95`）、`[Airplane Mode]=On` 射频发送（`-100 ENETDOWN`），以及 **`Slot-1` Wave-59 / `AVF_INFO` / `p12` / `P2` / `cnflasha` 写入（`-30 EROFS`）**（`slot1_vault_sha256_match=1`, `rf_tx_packets=0`, `wireless_tx_packets=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r73b_ok=1`, `verify_us=954784`, `FX6_R73_WAVE59_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.27s` | — |
| **73C（第 138 次实跑 · `46/46` 实机轮次 closure）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-59 `[Camera Settings Reset]` / `[Reset Network Set.]` / `[Initialize]` 分层复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r73c` | `clean_unmount_wave59_reset_h0_h3_big6` | Native ARM64 Wave-59 联合预演（**`46/46` 实机轮次 · 第 `138/138` 次独立实跑 · `92/92` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位层级：**`[Camera Settings Reset]` 复位 `Mode Settings`、`Home (Lower Left)`、`Framing Settings` 全部 3 项及 `[Interval Shoot Func.]` 全部 7 项，同时完整保留免复位的 `[Time Code Make]`、`[Time Code Run]`、全部 `[HDMI Output Settings]`（`Rec. Media dur HDMI` / `TC Output` / `REC Control` / `4ch Audio Output`）、`[Access Authen. Settings]`、`[Import Root Certificate]`、`[Fan Control]`、`[Auto Power OFF Temp.]` 与 `[Airplane Mode]=On`**（`camreset_preserves_wave59_survivors_ok=1`）；**`[Reset Network Set.]` 清除 `Access Authen.` 与导入根证书同时严格保留 `[Airplane Mode] = On` 零射频及相机/TC/HDMI/风扇/温度配置**（`nwreset_clears_access_auth_preserves_airplane_ok=1`）；**`[Initialize]` 恢复全量 Wave-59 出厂默认值同时仍保留 `[Airplane Mode] = On`**（`initialize_restores_wave59_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `rf_tx_packets=0`, `wireless_tx_packets=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=69`，`verify_us=451608`，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.84s` | 同 `73A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-59 四大支柱初始化与 Stage-B 四路桥接（`r73a` — 第 136 次实跑）
```text
FX6_R73_WAVE59_INIT fx3_wave59_nodes_ok=1 uxc_tokens_ok=1 big6_framing_ok=1 interval_shoot_ok=1 tc_hdmi_ok=1 ssh_auth_fan_ok=1
  big6_no_fixvar_rc=-16 auto_framing_dormant_rc=-95 fx6_auto_framing_dormant_rc=-95 fx3_interval_rec_mxf_rc=-2
  interval_slot1_erofs_rc=-30 interval_simult_erofs_rc=-30 tc_clock_dormant_rc=-95 rec_ctrl_no_tcout_rc=-16
  removed_ipsec_rc=-95 http_digest_dormant_rc=-95 fan_max_dormant_rc=-95 fx6_fan_max_dormant_rc=-95
  fx6_fan_always_off_dormant_rc=-95 airplane_rf_blocked_rc=-100 p2_write_blocked_rc=-30
  p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_auto_framing_bypass_events=0 dormant_http_auth_bypass_events=0 dormant_fan_max_bypass_events=0
  rf_tx_packets=0 wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r73_init_ok=1 verify_us=945430

FX6_STAGE_B_R73_BRIDGE round=73 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1
  lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19
  big6_fixed_var_home_framing_vs_dormant_auto=1 interval_shoot_9999_vs_fx6_mxf_erofs30=1
  reset_immune_tc_make_run_hdmi_recctrl_4ch=1 ssh_access_auth_rootcert_4mode_fan_zeromax=1
  milestone_46th_realhw_138th_live_92_pngs=1 dormant_auto_framing_bypass_events=0 dormant_http_auth_bypass_events=0
  dormant_fan_max_bypass_events=0 rf_tx_packets=0 wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0

FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE big6_fixed_var_precond_home_lower_left_ok=1
  manual_framing_rec_hdmi_vs_dormant_auto_framing_ok=1 big6_home_framing_dormant_ok=1
  dormant_auto_framing_bypass_events=0 e_nd_actuator_tx_count=0 emmc_write_count=0 r73_bridge_ok=1

FX6_R73_INTERVAL_SHOOT_9999_EROFS_BRIDGE interval_shoot_7items_9999_eshutter_ok=1
  fx3_still_seq_vs_fx6_mxf_interval_rec_ok=1 slot1_interval_burst_tier0_erofs30_ok=1
  interval_shoot_9999_erofs_ok=1 slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0

FX6_R73_TC_MAKE_RUN_HDMI_4CH_BRIDGE tc_make_regen_recrun_vmc_ext_lk_ok=1
  hdmi_rec_ctrl_tcout_on_and_4ch_audio_ok=1 tc_make_run_hdmi_4ch_ok=1 cnflasha_writes=0 emmc_write_count=0

FX6_R73_SSH_ACCESS_AUTH_FAN_TEMP_BRIDGE ssh_ptpip_access_auth_root_cert_zerorf_ok=1
  fan_control_4mode_zero_max_auto_temp_ok=1 ssh_access_auth_fan_temp_ok=1
  dormant_http_auth_bypass_events=0 dormant_fan_max_bypass_events=0 rf_tx_packets=0 wireless_tx_packets=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `69` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`154` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-59 防火墙拦截明细（`r73b` — 第 137 次实跑）
```text
FX6_R73_WAVE59_GUARD big6_no_fixvar_rc=-16 auto_framing_dormant_rc=-95 framing_100p_lock_rc=-16
  framing_rec_lock_rc=-16 fx6_manual_framing_enoent_rc=-2 fx6_auto_framing_dormant_rc=-95
  interval_10000_oob_rc=-22 interval_61s_oob_rc=-22 interval_iauto_busy_rc=-16 fx3_interval_mxf_enoent_rc=-2
  interval_slot1_burst_erofs_rc=-30 interval_simult_burst_erofs_rc=-30 tc_clock_dormant_rc=-95
  vmc_regen_invalid_rc=-22 vmc_recrun_invalid_rc=-22 hdmi_rec_ctrl_no_tcout_rc=-16 hdmi_rec_ctrl_sq_busy_rc=-16
  wep_removed_rc=-95 ipsec_removed_rc=-95 http_digest_dormant_rc=-95 fan_max_dormant_rc=-95
  airplane_rf_tx_rc=-100 fx6_fan_max_dormant_rc=-95 fx6_fan_always_off_rc=-95
  slot1_wave59_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_auto_framing_bypass_events=0 dormant_http_auth_bypass_events=0 dormant_fan_max_bypass_events=0
  rf_tx_packets=0 wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r73b_ok=1 verify_us=954784
FX6_R73_WAVE59_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-59 分层复位与 `16/16 H0 == H3`（`r73c` — 第 138 次实跑）
```text
FX6_R73_CLEAN_UNMOUNT_WAVE59_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave59_survivors_ok=1
  nwreset_clears_access_auth_preserves_airplane_ok=1
  initialize_restores_wave59_defaults_ok=1
  dormant_auto_framing_bypass_events=0 dormant_http_auth_bypass_events=0 dormant_fan_max_bypass_events=0
  rf_tx_packets=0 wireless_tx_packets=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r73c_ok=1 verify_us=451608
```

---

## 3. `r73a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r73a` Alpha（`26.50 KiB` / `27,132 B`） | `r73a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r73a Big6 Alpha](assets/r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-alpha.png) | ![r73a Big6 Composited](assets/r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）`BIG6` Home UI 与手动 `[Framing Settings]` 传感器裁剪读出台架（验证 `Mode Settings = Fixed/Variable` 实时动态 6 格、纯元数据 `ND Filter` 标签且 0 物理电子 ND 衰减对比 `ILME-FX6` 内置物理 `e-ND`、手动 `Framing` `Full`/`Crop` 传感器裁剪与休眠 `[Auto Framing]` 零暴露）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）机械/电子快门与双卡槽台架（验证静态 `[Interval Shoot Func.]` `1..9,999` 张定时连拍时序、默认 `Electronic Shutter`、`Shoot Interval Priority` 与 `Slot 1` 物理写保护 `EROFS=30` 对比 `ILME-FX6` 单 XAVC MXF `[Interval Rec]`）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）`VMC-BNCM1` LTC 发生器、HDMI `[REC Control]` + `[4ch Audio Output]` 汇接、OpenSSH / PTP-IP 以太网/无线台架及热风道温控箱（验证 `4` 档 `[Fan Control]` `Auto`/`Minimum`/`Off in Rec`/`Always Off` 且零 `Max` 模式，与 `[Auto Power OFF Temp.]` `Standard`/`High` 续航温控保护）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 73A (136th Live Run): Wave-59 4-Pillar BIG6 Home Fixed/Variable & Manual Framing vs Dormant Auto Framing / Still Interval Shoot 9999 vs FX6 MXF & EROFS=30 / Reset-Immune TC Make-Run & HDMI REC Control-4ch / Ver. 7.00+ Access Authen. SSH+PTP-IP & 4-Mode Zero-Max Fan Control + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 73 --r73-mode big6_framing_interval_tc_make_ssh_auth_fan_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r73a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round73-qemu/r73a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r73a-big6-framing-interval-tc-ssh-fan-big6-schinese \
  --export-png-dir reports/2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu/assets

# Run 73B (137th Live Run): Fail-Closed Wave-59 Guard (BIG6 No-FixVar EBUSY, Dormant Auto Framing/HTTP Digest/FAN_CONTROL_MAX EOPNOTSUPP, Interval 9999 Slot-1 EROFS=30, VMC Invalid EINVAL, HDMI REC Control No-TCOUT EBUSY, Airplane Zero-RF ENETDOWN)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 73 --r73-mode wave59_big6_framing_interval_tc_ssh_fan_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r73b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round73-qemu/r73b

# Run 73C (138th Live Run — 46/46 Real-HW Rounds / 138/138 Live Runs / 92/92 PNGs): Clean Unmount Stock FX3 Restoration, Wave-59 Reset Split (Camera Settings Reset / Reset Network Set. / Initialize) + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 73 --r73-mode clean_unmount_wave59_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r73c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round73-qemu/r73c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_auto_framing_bypass_events == 0`、`dormant_http_auth_bypass_events == 0`、`dormant_fan_max_bypass_events == 0`、`rf_tx_packets == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
