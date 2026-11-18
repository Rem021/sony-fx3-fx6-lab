# Round 61 Milestone（`100+` 次实机内核 QEMU 里程碑 · Wave-47 / `R28..R61` `34/34` 实机预演轮次 · 第 `100..102` 次实跑 -> `102/102` 总实跑 · `68/68` 张 Big-6 PNG）：FX3 7.02 原厂内核真机准备预演 — `[USB Connection Mode]` `4` 模式与 `NOUVC` / Type-C `PD` 隔离、`[HDMI Info. Display]` 净馈送/`Log 1080p` 降档、回放 `[Protect]` vs `[Format]` `Slot-1` 防火墙及 `[Reset Network Set.]` 自动重启 + `[Airplane Mode]=[On]` 零射频隔离

> **日期**：2026-11-17 | **轮次**：**Round 61 Historic 100+ Live QEMU Runs Milestone (Wave-47 · `34/34` Real-HW Rounds · `100th..102nd` Live Runs -> `102/102` Total Live Runs, `68/68` PNGs)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r61a` / `r61b` / `r61c`，正式跨越 **100+ 次独立实机运行里程碑**，累计达成 `R28..R61` **`34/34` 轮实机内核预演**、**第 `100..102` 次 -> `102/102` 次独立实跑**、**`68/68` 张 `< 50 KiB`（本轮 `< 28 KiB`）PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 USB-C 协议分析仪与无数据 `PD` 供电隔离台架、`Atomos`/HDMI 外录机净馈送与 `1080p` 降档实测、`Slot-1` 物理写保护开关 `[Protect]`/`[Delete]`/`[Format]` 交互，以及 `[Reset Network Set.]` 自动重启后紧接 `[Airplane Mode]=[On]` 的射频频谱分析仪零发射实测尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 61 轮历史性 `100+` 次实跑里程碑（Wave-47 · `34/34` 实机轮次 / `100th..102nd` -> `102/102` 次实跑 / `68/68` PNG）三项实机预演总览（`r61a` / `r61b` / `r61c`）

| 实跑场景 | Run ID | `r61_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **61A（历史性第 100 次实跑！）：`[USB Connection Mode]` `NOUVC`/`PD`、`[HDMI Info. Display]`、`[Protect]` vs `[Format]`、`[Reset Network Set.]` + Big-6 Home** | `r61a` | `usb_hdmi_protect_netreset_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：(1) 核验 **`[USB Connection Mode]`**（`BKID_APP_setting_usb_connection_method`, `_f.uxc 0x69a2`）：精确 `4` 模式（`Sel. When Connect` `0x7738` 默认、`MassStorage(MSC)` `0x6c54` `054C:0DA1`、`MTP` `.uxc 0xe24b` Slot 1、`Remote Shoot (PC Remote)` `0x60aa`），而沉睡 **`USB Streaming`**（`0x7399` / `usb_f_uvc.ko` `78,840 B`）在 FX3 端 `NOUVC` 掩码屏蔽（FX6 为活跃 `ProCam UVC`）；`[USB LUN Setting]`（`Multi` `0xe631` 默认 / `Single` `0x776d`）与仅限 Type-C（需 `NP-FZ100`）的 **`[USB Power Supply]`**（`On` `0x721e` 默认）跨 `[Camera Settings Reset]` 存活，Tier-0 台架禁止 USB 数据枚举（`usb_data_tx_events=0`）；(2) 核验 **`[HDMI Info. Display]`**（`BKID_APP_setting_hdmi_info_display`, `0x6e7c`）：`On`（`0xe07c` 默认：熄灭机身 LCD 并在 HDMI 叠加内缩 OSD）vs `Off`（`0xe297`：HDMI 净馈送 + LCD 激活）；`Internal Rec + Log/PPLUT1..4` 强制降档 HDMI 至 `1080p`，而 `Off(HDMI Only)`（`0x6573`）或 `RAW Output=On`（`0x6e97`）强制 `HDMI Info. Display=Off` 输出 `4K` 净馈送；(3) 核验回放 **`[Protect]`**（`.uxc 0xe2c9` `4` 作用域：`Multiple Img.` `0xe2ca` / `All in this Folder` `0x6848` / `All with this date` `0x69f7` / `All Images in This Group` `0xe826`）仅屏蔽 `[Delete]`，**`[Format]`（`0xe449`/`0xe414`）会连同 `[Protect]` 片段一并擦除**，Slot-1 恢复库 `[Protect]` 切换与 `[Format]` 均只读阻断（`-30 EROFS`）；(4) 核验 **`[Reset Network Set.]`**（`0x60d3`, `FUNC_reset_network_settings`）仅清除 `(Network)` Wi-Fi/BT/FTP/证书、强制触发 `BKID_APP_is_shutdown_factor_network_reset` 自动重启（`0x65d3`）并紧接 **`[Airplane Mode]=[On]`**（`0x6df9`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r61_init_ok=1`, `r61_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.13s` | [`r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-composited.png`](assets/r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-composited.png) |
| **61B（第 101 次实跑）：Fail-Closed Wave-47 防火墙 — `NOUVC` 伪造、`Log 2160p` 旁路、`Slot-1` `[Protect]`/`[Format]` 与未重启无感 RF 拦截** | `r61b` | `nouvc_hdmi1080_slot1_protect_nwreset_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拒绝 `NOUVC` `USB Streaming` 菜单/流伪造（`uvc_spoof_rc=-2`, `menu_uvc_rc=-2 ENOENT`），拦截 Tier-0 下 `MSC`/`MTP`/`Remote` 主机数据枚举（`tier0_msc_rc=-1 EPERM`），拦截 `Multi/Micro USB` 供电与无 `NP-FZ100`/未断数据线 PD（`multi_usb_pd_rc=-95`, `no_batt_pd_rc=-22`, `non_isolated_pd_rc=-1`, `usb_data_enumeration_events=0`）；(2) 拦截 `HDMI Info=On` 下机身 LCD 触控对焦（`lcd_touch_blanked_rc=-16`）、`Log+Internal Rec` `2160p` 旁路（`log_2160p_bypass_rc=-16 EBUSY`, `log_1080p_clamp_bypass_events=0`）、`S&Q` 下 `Off(HDMI Only)`/`RAW`（`sq_raw_lockout_rc=-95`）及净馈送 OSD 烘焙（`clean_osd_bake_rc=-1 EPERM`）；(3) 对只读 `Slot-1` Tier-0 恢复保险库（`BODYDATA.DAT`/`CAMSET01.DAT`）阻断 `[Protect]` 属性改写、`[Delete]` 与 `[Format]`（`slot1_protect_rc=-30`, `slot1_delete_rc=-30`, `slot1_format_rc=-30 EROFS`, `slot1_vault_sha256_match=1`），并在 `Slot-2` 上仅屏蔽受保护片段 `[Delete]`（`slot2_protected_del_rc=-13 EACCES`）；(4) 拦截跳过自动重启的 `[Reset Network Set.]`（`nw_skip_reboot_rc=-11 EAGAIN`）并验证 `[Airplane Mode]=[On]` 后全程零射频发射（`rf_before_airplane_rc=-1`, `rf_after_airplane_rc=-1 EPERM`, `post_reset_rf_leak_events=0`, `p2_write_blocked_rc=-30`, `cnflasha_ro_blocked_rc=-30`, `emmc_write_count=0`, `r61b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.28s` | — |
| **61C（第 102 次实跑 · 里程碑收官）：洁净卸载 `/tmp` Stage-B 覆盖层 + `[Reset Network Set.]` 自动重启/`Airplane Mode=On` vs `[Camera Settings Reset]` vs `[Initialize]` + `16/16 H0 == H3`** | `r61c` | `clean_unmount_nwreset_reboot_airplane_h0_h3_big6` | Native ARM64 Wave-47 联合预演（**第 `61` 轮 / `34/34` 轮实机预演 · 第 `102/102` 次独立实跑收官**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Reset Network Set.]` 仅清空 `(Network)` Wi-Fi/BT/FTP/证书并触发强制自动重启且保留 `Setup [USB]`/`[HDMI Info. Display]`/`[Framing Settings Crop]`，重启后由 `[Airplane Mode]=[On]` 恢复零射频隔离（`nw_quarantine_ok=1`）；实证 `[Camera Settings Reset]` 保留 `Setup [USB]` 与 `[HDMI Info. Display]` 而仅复位例外项 `[Framing Settings (HDMI)] Crop`（`camreset_preserves_setup_ok=1`）；实证 `[Initialize]` 全量恢复 Wave-47 出厂默认后重臂 `Airplane Mode=On`（`initialize_restores_wave47_ok=1`, `zero_rf_final_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.76s` | 同 `61A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-47 四大支柱初始化与 Stage-B 桥接（`r61a` — 历史性第 100 次实跑）
```text
FX6_R61_WAVE47_INIT fx3_wave47_nodes_ok=1 uxc_tokens_ok=1
  usb_nouvc_4mode_pd_ok=1 hdmi_info_clean_clamp_ok=1
  protect_vs_format_vault_ok=1 reset_network_reboot_airplane_ok=1
  uvc_spoof_rc=-2 msc_enum_rc=-1 touch_blank_rc=-16 log_2160p_rc=-16
  slot1_protect_rc=-30 slot1_format_rc=-30 nw_no_reboot_rc=-11
  rf_tx_blocked_rc=-1 p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1 usb_data_tx_events=0
  slot1_protect_mutation_events=0 slot1_format_events=0
  post_reset_rf_leak_events=0 passive_tx_bytes_emitted=0 cnflasha_writes=0
  e_nd_actuator_tx_count=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r61_init_ok=1 verify_us=897509

FX6_R61_USB_NOUVC_PD_BRIDGE usb_4mode_nouvc_ok=1
  usb_lun_multi_single_ok=1 usb_typec_pd_isolated_ok=1
  usb_nouvc_pd_ok=1 usb_data_tx_events=0
  emmc_write_count=0 r61_bridge_ok=1

FX6_R61_HDMI_INFO_CLEAN_CLAMP_BRIDGE hdmi_info_on_blanks_lcd_ok=1
  hdmi_log_1080p_clamp_ok=1 hdmi_only_raw_4k_clean_ok=1
  hdmi_info_clean_clamp_ok=1 log_1080p_clamp_bypass_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R61_PROTECT_FORMAT_NWRESET_BRIDGE protect_4scopes_delete_only_ok=1
  slot1_protect_format_ro_ok=1 nwreset_autoreboot_airplane_ok=1
  protect_format_nwreset_ok=1 slot1_protect_mutation_events=0
  slot1_format_events=0 post_reset_rf_leak_events=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `81` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`157` 实时线程零崩溃。

### 2.2 Fail-Closed `NOUVC`、`Log 1080p` 旁路、`Slot-1` `[Protect]`/`[Format]` 与网络复位零射频拦截（`r61b` — 第 101 次实跑）
```text
FX6_R61_WAVE47_GUARD uvc_spoof_rc=-2 menu_uvc_rc=-2 tier0_msc_rc=-1
  multi_usb_pd_rc=-95 no_batt_pd_rc=-22 non_isolated_pd_rc=-1
  lcd_touch_blanked_rc=-16 log_2160p_bypass_rc=-16 sq_raw_lockout_rc=-95
  clean_osd_bake_rc=-1 slot1_protect_rc=-30 slot1_delete_rc=-30
  slot1_format_rc=-30 slot2_protected_del_rc=-13 nw_skip_reboot_rc=-11
  rf_before_airplane_rc=-1 rf_after_airplane_rc=-1
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  usb_data_enumeration_events=0 log_1080p_clamp_bypass_events=0
  slot1_protect_mutation_events=0 slot1_format_events=0
  post_reset_rf_leak_events=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r61b_ok=1 verify_us=961852
```

### 2.3 洁净卸载还原原厂、三层复位边界与 `16/16 H0 == H3`（`r61c` — 第 102 次实跑）
```text
FX6_R61_CLEAN_UNMOUNT_NWRESET_H0_H3 stock_unmount_restored_ok=1
  nw_quarantine_ok=1 camreset_preserves_setup_ok=1
  initialize_restores_wave47_ok=1 zero_rf_final_ok=1
  usb_data_tx_events=0 slot1_protect_mutation_events=0
  slot1_format_events=0 post_reset_rf_leak_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0
  r61c_ok=1 verify_us=406403
```

---

## 3. `r61a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r61a` Alpha（`26.50 KiB` / `27,132 B`） | `r61a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r61a Big6 Alpha](assets/r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-alpha.png) | ![r61a Big6 Composited](assets/r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）Type-C USB 总线分析与供电隔离台架实测（验证 `[USB Connection Mode]` `4` 模式枚举与 `NOUVC` 缺失 vs `054C:0DA1` MSC / MTP / PC Remote、`[USB LUN Setting]` Multi/Single，以及插着 `NP-FZ100` 且物理断开 `D+/D-`/`SuperSpeed TX/RX` 时的仅供电 Type-C PD）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）外接 `Atomos`/HDMI 协议分析仪实测（验证 `[HDMI Info. Display]=On` 熄灭机身 LCD + 内缩信箱式 OSD vs `Off` 净馈送、`Log`/`PPLUT1..4` 内录时强制 `1080p` 降档，以及 `Off(HDMI Only)`/`RAW Output=On` 强制 `4K` 净输出）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）`Slot-1` 物理写保护锁与 `[Protect]` vs `[Delete]` vs `[Format]` 台架实操，以及 `[Reset Network Set.]` 自动重启后紧接开启 `[Airplane Mode]=[On]` 的射频频谱分析仪零发射检测。

---

## 5. 复现命令与洁净室合规

```bash
# Run 61A (Historic 100th Live Run!): Wave-47 USB Mode/NOUVC/PD + HDMI Info/1080p Clamp + Protect vs Format + Reset Network Set. + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 61 --r61-mode usb_hdmi_protect_netreset_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r61a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round61-qemu/r61a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r61a-usb-hdmi-protect-netreset-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu/assets

# Run 61B (101st Live Run): Fail-Closed NOUVC Spoof, Log 2160p Bypass, Slot-1 Protect/Format & Post-Reset RF Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 61 --r61-mode nouvc_hdmi1080_slot1_protect_nwreset_guard --sd-manifest-mode valid --lang en \
  --run-id r61b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round61-qemu/r61b

# Run 61C (102nd Live Run — 100+ Live QEMU Runs Milestone Closure!): Clean Unmount Stock FX3 Restoration, Reset Tiers + Airplane Mode + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 61 --r61-mode clean_unmount_nwreset_reboot_airplane_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r61c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round61-qemu/r61c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`usb_data_tx_events == 0`、`slot1_protect_mutation_events == 0`、`slot1_format_events == 0`、`post_reset_rf_leak_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
