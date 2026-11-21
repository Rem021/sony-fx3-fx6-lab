# Round 81（Wave-67 · **`54/54` 实机预演轮次 `R28..R81` · 第 `160..162` 次实跑 -> `162/162` 总实跑 · `108/108` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `[Pixel Mapping]` / `[Auto Pixel Mapping]` vs FX6 `APR`、`Setup -> [Monitor]` 3 项分组与 4 项休眠 EVF 辟谣 vs FX6 `VF Setting/Adjust`、保持类自定义键与仅限静态 `[Recall Custom hold 1–3]` 精确 11 位 / 零独立 WB vs FX6 `Push AF/AGC/Iris`，以及 `Setup -> [External Output]` HDMI `Rec. Media` / `TC Output -> REC Control` / `24.00p` 重启 / 休眠 `4K/2K` & `24p/60p` 辟谣 / `Slot 1 EROFS=30` 防火墙 vs FX6 `SDI/HDMI` 矩阵

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 81** 三路独立 QEMU 实机预演（`r81a` / `r81b` / `r81c`，正式达成 **`54/54` 实机预演轮次 `R28..R81` · `162/162` 次独立实跑 · `108/108` 张 `<= 27,467 B` PNG 视觉凭证**，`overall_status="PASS"`、`synthetic_fallback=False`），全部 **`crashes == 0`、`emmc_write_count == 0`、`emmc_writes == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`usb_tx_bytes == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`dormant_fx6_abb_events == 0`、`dormant_fx3_evf_events == 0`、`dormant_fx6_vf_4subitems_events == 0`、`dormant_recallhold_movie_events == 0`、`dormant_recallhold_wb_events == 0`、`dormant_fx6_high_low_key_events == 0`、`dormant_hdmi_4k2k_events == 0`、`dormant_hdmi_24p60p_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r81c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r81a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `27,467 B` Composited PNG 与 `27,132 B` Alpha PNG（均严格 `<= 27,467 B`）。
- **核心关联文件**：
  - 情报基线：[Wave 67 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/reports/2026-11-17-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/README.md)
  - 遥测汇总：[summary.json](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/summary.json)
  - 视觉凭证：[r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png)（`27,467 B`）· [r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png)（`27,132 B`）
  - 源码与测试：[fx6-stage-a-verify.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/outputs/fx6-native-presenter-closure/fx6-stage-a-verify.c) · [libgrm-fbinit9.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/outputs/fx6-native-presenter-closure/libgrm-fbinit9.c) · [build_and_run_round.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/outputs/fx6-native-presenter-closure/build_and_run_round.py) · [test_round81_pixelmap_monitor_recallhold_hdmi_recctrl_qemu.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h488-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/outputs/fx6-native-presenter-closure/tests/test_round81_pixelmap_monitor_recallhold_hdmi_recctrl_qemu.py)
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 67 四大支柱门禁、休眠分支辟谣与 `Slot 1` `EROFS=-30` 隔离的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-11 EAGAIN` / `-19 ENODEV` / `-2 ENOENT` / `-30 EROFS` / `-1 EPERM` 护栏：
  1. **支柱 A（`Pixel Mapping` / `Auto Pixel Mapping` vs FX6 `APR`）**：`Setup -> [Setup Option] -> [Auto Pixel Mapping]`（`_f 0x7734`，默认 `On`，**抗 `[Camera Settings Reset]`**）、手动 `[Pixel Mapping]`（`_f 0x61f7`，镜头盖遮光校验 `_g 0x63f1`/`0x60e7` + 电量门控 `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING` `-11 EAGAIN` + 自动重启）与静音目标子项 `[Auto Pixel Mapping]`（`_f 0x64e7` `Not Target`/`Off` 默认、**可 Reset**，保持 `Off` 时关机通过 `vdf_set_shutter_mute_by_pixel_mapping` 发出机械快门声），同步核验 Sony ELF 原厂拼写错字 `BKID_APP_setting_notification_for_pixel_mappinng` 与 `BKID_APP_pixel_mapping_excuted_status`；对比 FX6 `Technical > APR`（需镜头盖 + 黑布遮光 `ns1 0x3324`，无 CCD 时代 `ABB` 菜单 -> `-95 EOPNOTSUPP`）。
  2. **支柱 B（`Setup -> [Monitor]` 3 项分组与 4 项休眠 EVF 辟谣 vs FX6 `VF Setting/Adjust`）**：辟谣无 EVF 机身不存在 `[Finder/Monitor]` 组名（`-95`），验证精确 3 项抗 Reset 实装项（`[Monitor Brightness]` `Manual -2..+2`/`Sunny Weather`、`[Display Quality]` `Standard`/`High` 高温强制锁回 `Standard` `-16`、`[Monitor Flip Direction]` `Auto`/`Horizontal Flip`/`180 Degree Flip`/`No Flip`），全部 4 项休眠 EVF 条目（`Finder/Monitor Sel.`、`Viewfinder Bright.`、`Viewfinder Color Temp.`、`Finder Frame Rate`）严格阻断 `-95 EOPNOTSUPP`；对比 FX6 `Monitoring > VF Setting`（`Brightness 1..15` 默认 `8`、`Color/B&W`）、`VF Adjust`（未接取景器 `-19 ENODEV`）、硬件 `MIRROR` 拨钮（`Off/B-T/ROT`）与 4 项子菜单辟谣（`-95`）。
  3. **支柱 C（保持类自定义键与仅限静态 `[Recall Custom hold 1–3]` 精确 11 位 / 零独立 WB vs FX6 `Push AF/AGC/Iris`）**：`[AF On]`（Still/Movie/S&Q）、`[Eye AF]`（Still/Movie）、`[Tracking On]`（仅 Still `AF-C`）；`[Recall Custom hold 1..3]` 严格限定 **Still `P/A/S/M`**（Movie/S&Q/iAuto 阻断 `-95`），精确 **`11` 个可勾选位**（`is_checked_recall_custom_hold0..10 = 0x07FF`，`drive_mode` 排除 Self-timer），**零独立 `White Balance` 勾选位（`-95`）**，抗 Reset 且持久化至 `CAMSET*.DAT`（写 `Slot 1` 阻断 `-30 EROFS`）；对比 FX6 `Push AF`/`Push AF/Push MF`/`Push AGC`（`Cine EI`/`Bokeh Control=On` 阻断 `-16`）/`Push Auto Iris`（`MANUAL`/`Bokeh Control=On` 阻断 `-16`）及休眠 `High/Low Key`（`-95`）。
  4. **支柱 D（`Setup -> [External Output]` HDMI 矩阵、`TC Output -> REC Control`、`24.00p` 重启、休眠 `4K/2K` & `24p/60p` 辟谣、`Slot 1 EROFS=30` 与 FX6 `SDI/HDMI` 矩阵）**：`[External Output]` 全项抗 Reset；`[Rec. Media dur HDMI Output]`（默认 `On`，`S&Q` 锁 `On`，`Off(HDMI Only)` 或 `RAW=On` 强制 `[HDMI Info. Display]=Off`）、`[Output Resolution]`（`Log`/`PPLUT1..4` + `Rec. Media=On` 降为 `1080`）、`[4K Output Set.(HDMI Only)]`（`24.00p` 强制重启与回放隔离 + ELF 错字 `outpute`）、`[Time Code Output]`（默认 `Off`、`S&Q` 禁用）为 `[REC Control]` 硬前置条件、`[4ch Audio Output]`（`CH1/CH2` vs `CH3/CH4`）、`[CTRL FOR HDMI]`（ELF 错字 `ctrl_for_hmdi`）、休眠 `4K/2K` & `24p/60p` 阻断 `-95`；凡 `Rec. Media dur HDMI Output=On` 或 `CAMSET*.DAT` 指向 Tier-0 `Slot 1` 全部在协议与 Linux 内核 VFS 层返回 **`-30 EROFS`**；对比 FX6 `12G/6G/3G-SDI + HDMI` 双路输出矩阵（`RAW(HDMI) 4240x2392 -> SDI 1080`、`S&Q > 60fps -> HDMI 1080`、`SDI/HDMI Remote I/F` vs `Parallel Rec`）。
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测尚未上电执行，详见 §4。**

> **日期**：2026-11-21 | **轮次**：**Round 81 (`54/54` Real-HW Rounds · Wave-67 · `160th..162nd` Live Runs -> `162/162` Total Live Runs, `108/108` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-67 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/README.md`](../2026-11-17-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 81 轮（Wave-67 · `54/54` 实机轮次 / `160th..162nd` -> `162/162` 次实跑 / `108/108` PNG）三项实机预演总览（`r81a` / `r81b` / `r81c`）

| 实跑场景 | Run ID | `r81_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **81A（第 160 次实跑）：Wave-67 四大支柱 — `Pixel Mapping`/`Auto Pixel Mapping` vs FX6 `APR`、`Setup -> [Monitor]` 3 项与 4 项休眠 EVF 辟谣 vs FX6 `VF Setting/Adjust`、保持键与仅限静态 `[Recall Custom hold 1–3]` 11 位 / 零 WB vs FX6 `Push AF/AGC/Iris`、`Setup -> [External Output]` HDMI 矩阵 & `Slot 1 EROFS=30` vs FX6 `SDI/HDMI` + Big-6 Home** | `r81a` | `pixelmap_monitor_recallhold_hdmi_recctrl_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Auto Pixel Mapping]`**（抗 Reset 默认 `On`）、手动 **`[Pixel Mapping]`**（遮光/低电 `-11`/自动重启）、静音目标默认 `Not Target` 关机快门声与 ELF 错字（`pixel_mappinng`、`excuted_status`）vs FX6 `APR`（零 `ABB` `-95`）；(2) 核验 **`Setup -> [Monitor]`** 3 项抗 Reset 实装项 + 4 项休眠 EVF & `[Finder/Monitor]` 组名全阻断 `-95` vs FX6 `VF Setting`/`VF Adjust`/`MIRROR`（零 4 项子菜单 `-95`）；(3) 核验 **`[AF On]`/`[Eye AF]`/`[Tracking On]`** 与仅限 Still `P/A/S/M` **`[Recall Custom hold 1–3]`**（精确 11 位 `0x07FF`、零独立 WB `-95`、Movie/S&Q/iAuto `-95`、抗 Reset、`CAMSET*.DAT`）vs FX6 `Push AF/AGC/Iris`（零 `High/Low Key` `-95`）；(4) 核验 **`[External Output]`** HDMI 全项抗 Reset、`Log/PPLUT 1080`、`24.00p` 重启与回放隔离 + `outpute`/`ctrl_for_hmdi`、`TC Output -> REC Control`、休眠 `4K/2K` & `24p/60p` `-95`、`Slot 1` 协议与 VFS 双 `-30 EROFS` 及 FX6 `SDI/HDMI` 矩阵，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r81_init_ok=1`, `r81_bridge_ok=1`, `verify_us=319666`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.34s` | [`r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png`](r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png) / [`r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png`](r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png) |
| **81B（第 161 次实跑）：Fail-Closed Wave-67 防火墙 — FX3/FX6 休眠 `ABB` / `[Finder/Monitor]` / 4 休眠 EVF / FX6 VF 4 子项 / `Tracking On` Movie / `Recall Custom hold` Movie-S&Q-iAuto & 独立 WB / FX6 `Recall` & `High/Low Key` / FX3 SDI / 休眠 `4K/2K` & `24p/60p`（`-95`）、遮光/高温锁/`Eye AF S&Q`/非 AF-C/Self-timer/FX6 Push 锁/`S&Q` HDMI-RAW-TC 锁/无 TC `REC Control`/FX6 `RAW(HDMI)->SDI 1080` & `S&Q>60->HDMI 1080`（`-16`）、低电/温度（`-11`）、未接 VF（`-19`）、无卡 Parallel Rec（`-2`）、越界与 `NULL`（`-22`）、`live_attach`（`-1`）及 `Slot 1`（`Rec. Media=On`/`CAMSET*.DAT`/FX6 Parallel/`M4ROOT`/`AVF_INFO`/`CAMSET` VFS）/`P12`/`P2`/`cnflasha`（`-30 EROFS`）** | `r81b` | `wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard` | Native ARM64 Fail-Closed 注入阻断实测：55 项故障注入全部命中精确 POSIX `errno`（`-95`/`-16`/`-11`/`-19`/`-2`/`-22`/`-30`/`-1`），实证 `slot1_vault_sha256_match=1`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `emmc_write_count=0`, `cnflasha_writes=0`, `r81b_ok=1`, `verify_us=877796`, `FX6_R81_WAVE67_GUARD_RC=0` | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.36s` | — |
| **81C（第 162 次实跑 · **`54/54` 实机轮次闭环**）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-67 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r81c` | `clean_unmount_wave67_reset_h0_h3_big6` | Native ARM64 Wave-67 联合预演（**`54/54` 实机轮次 · 第 `162/162` 次独立实跑 · `108/108` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位：**`[Camera Settings Reset]`** 复位 `Silent Mode` 与静音目标 `[Auto Pixel Mapping]`，同时完整保留 **`Setup -> [Auto Pixel Mapping]`、全部 3 项 `[Monitor]`、`[Reg. Custom Shoot Set]` 11 位 `Recall Custom hold`、全部 `[External Output]` HDMI 项、像素映射执行计数与 `Airplane Mode=On`**；**`[Reset Network Set.]`** 完整保留全部 Wave-67 设置与 `Airplane Mode=On`；**`[Initialize]`** 还原 Wave-67 Setup/Monitor/RecallHold/HDMI 默认值同时保留像素映射执行计数与 `Airplane Mode=On`；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`osd=53`, `verify_us=1075813`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.15s` | 同 `81A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-67 四大支柱初始化与 Stage-B 四路桥接（`r81a` — 第 160 次实跑）
```text
FX6_R81_WAVE67_INIT fx3_wave67_nodes_ok=1 uxc_tokens_ok=1 pixelmap_apr_ok=1
  monitor3_evf_debunk_ok=1 recallhold11_pushaf_ok=1 hdmi_tc_recctrl_sdi_erofs_ok=1
  pm_lowbatt_rc=-11 pm_uncapped_rc=-16 fx6_abb_dormant_rc=-95 mon_thermal_lock_rc=-16
  evf_group_debunk_rc=-95 evf_sel_dormant_rc=-95 evf_bright_dormant_rc=-95
  evf_ctemp_dormant_rc=-95 evf_fps_dormant_rc=-95 fx6_vf_4sub_debunk_rc=-95
  recall_movie_rc=-95 recall_sq_rc=-95 recall_iauto_rc=-95 recall_wb_debunk_rc=-95
  recall_camset_slot1_erofs_rc=-30 fx6_highlow_dormant_rc=-95 rec_ctrl_no_tc_rc=-16
  hdmi_4k2k_dormant_rc=-95 hdmi_24p60p_dormant_rc=-95 slot1_hdmi_recmedia_erofs_rc=-30
  fx6_raw_hdmi_sdi1080_rc=-16 fx6_sq_gt60_hdmi1080_rc=-16
  slot1_vfs_m4root_erofs_rc=-30 slot1_vfs_camset_erofs_rc=-30 p2_write_blocked_rc=-30
  p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_fx6_abb_events=0 dormant_fx3_evf_events=0 dormant_fx6_vf_4subitems_events=0
  dormant_recallhold_movie_events=0 dormant_recallhold_wb_events=0
  dormant_fx6_high_low_key_events=0 dormant_hdmi_4k2k_events=0 dormant_hdmi_24p60p_events=0
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r81_init_ok=1 verify_us=319666

FX6_STAGE_B_R81_BRIDGE round=81 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19 pixelmap_apr_zero_abb_ok=1 monitor3_dormant_evf4_vfadjust_ok=1
  recallhold11_still_pasm_zero_wb_pushaf_ok=1
  hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs30_ok=1
  milestone_54th_realhw_162nd_live_108_pngs=1 usb_tx=0 slot1_writes=0
  slot1_write_count=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0
```

### 2.2 Fail-Closed Wave-67 防火墙拦截明细（`r81b` — 第 161 次实跑）
```text
FX6_R81_WAVE67_GUARD fx3_pm_lowbatt_rc=-11 fx3_pm_uncapped_rc=-16 fx3_abb_dormant_rc=-95
  fx6_abb_dormant_rc=-95 fx6_apr_no_cloth_rc=-16 fx6_apr_bad_temp_rc=-11 evf_group_rc=-95
  evf_sel_rc=-95 evf_bright_rc=-95 evf_ctemp_rc=-95 evf_fps_rc=-95 mon_bright_oob_rc=-22
  mon_disp_qual_heat_rc=-16 fx6_vf_4sub_rc=-95 fx6_vf_unconn_rc=-19 fx6_vf_bright_oob_rc=-22
  eye_af_sq_rc=-16 track_movie_rc=-95 track_non_afc_rc=-16 recall_movie_rc=-95
  recall_sq_rc=-95 recall_iauto_rc=-95 recall_wb_bit_rc=-95 recall_selftimer_rc=-16
  recall_camset_slot1_rc=-30 fx6_recall_rc=-95 fx6_push_af_desq_rc=-16
  fx6_push_agc_cineei_rc=-16 fx6_push_agc_bokeh_rc=-16 fx6_push_iris_manual_rc=-16
  fx6_push_iris_bokeh_rc=-16 fx6_highlow_rc=-95 fx3_sdi_port_rc=-95 hdmi_4k2k_rc=-95
  hdmi_24p60p_rc=-95 sq_hdmi_only_off_rc=-16 sq_raw_hdmi_rc=-16 sq_tc_out_rc=-16
  rec_ctrl_no_tc_rc=-16 rec_ctrl_incompat_rc=-16 slot1_hdmi_rec_erofs_rc=-30
  fx6_raw_hdmi_sdi4k_rc=-16 fx6_sq_gt60_hdmi4k_rc=-16 fx6_rec_ctrl_no_tc_rc=-16
  fx6_parallel_nocard_rc=-2 fx6_parallel_slot1_erofs_rc=-30 null_cfg_einval_rc=-22
  live_attach_eperm_rc=-1 slot1_m4root_erofs_rc=-30 slot1_avf_erofs_rc=-30
  slot1_camset_vfs_erofs_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 slot1_avf_info_mutated=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r81b_ok=1 verify_us=877796
FX6_R81_WAVE67_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-67 三层非对称复位与 `16/16 H0 == H3`（`r81c` — 第 162 次实跑）
```text
FX6_R81_CLEAN_UNMOUNT_WAVE67_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_silent_target_preserves_autopm_monitor3_recallhold_hdmi_airplane_ok=1
  nwreset_preserves_wave67_all_setup_recallhold_hdmi_airplane_ok=1
  initialize_restores_wave67_defaults_preserves_pm_count_airplane_ok=1
  dormant_fx6_abb_events=0 dormant_fx3_evf_events=0 dormant_fx6_vf_4subitems_events=0
  dormant_recallhold_movie_events=0 dormant_recallhold_wb_events=0
  dormant_fx6_high_low_key_events=0 dormant_hdmi_4k2k_events=0 dormant_hdmi_24p60p_events=0
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  rf_tx_packets=0 slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0 dlopen_ok=1 surfaces_verified=16
  surfaces_h0_eq_h3=16 drift_bits=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 emmc_write_count=0
  r81c_ok=1 verify_us=1075813
```

---

## 3. `r81a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| Scene 1 Composited（`26.82 KiB` / `27,467 B`） | Scene 2 Alpha（`26.50 KiB` / `27,132 B`） |
| :---: | :---: |
| ![r81a Big6 Composited](r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png) | ![r81a Big6 Alpha](r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）传感器像素映射与 APR 台架（验证 `Auto Pixel Mapping=On` 且静音目标为 `Off` 时的关机机械快门响声、手动 `Pixel Mapping` 遮光/低电检测与自动重启，以及 FX6 `Technical > APR` 镜头盖 + 黑布遮光且无 `ABB` 菜单）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）显示屏与自定义保持键台架（验证 `Setup -> [Monitor]` 3 项抗 Reset、`Display Quality` 高温强制锁回 `Standard`、无 EVF 机身 4 项休眠 EVF 缺席、仅限静态 `P/A/S/M` 的 `[Recall Custom hold 1–3]` 11 位覆写与零独立 WB、`CAMSET*.DAT` 持久化，以及 FX6 `VF Setting/Adjust`、`MIRROR` 拨钮与 `Push AF/AGC/Iris` 锁止条件）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）外部输出 HDMI / SDI 与媒体写保护台架（验证 `Rec. Media dur HDMI Output=On` 默认与 `S&Q` 锁 `On`、`Log`/`PPLUT` 1080 降级、`24.00p` 重启与回放隔离、`Time Code Output -> REC Control` 外部录机触发、`4ch Audio` 双声道选择、Tier-0 `Slot 1` 物理写保护隔离，以及 FX6 `12G/6G/3G-SDI + HDMI` 双路输出矩阵）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 81A (160th Live Run): Wave-67 4-Pillar Stage-A/B + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 81 --r81-mode pixelmap_monitor_recallhold_hdmi_recctrl_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r81a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round81-qemu/r81a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r81a-wave67-big6 \
  --export-png-dir <SCRATCH_ROOT>/round81-pngs

# Run 81B (161st Live Run): Fail-Closed Wave-67 Guard (-95/-16/-11/-19/-2/-22/-30/-1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 81 --r81-mode wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard --sd-manifest-mode valid --lang en \
  --run-id r81b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round81-qemu/r81b

# Run 81C (162nd Live Run — Round 81: 54/54 Real-HW Rounds / 162/162 Live Runs / 108/108 PNGs <= 27,467 B): Clean Unmount + Wave-67 3-Tier Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 81 --r81-mode clean_unmount_wave67_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r81c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round81-qemu/r81c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`overall_status == "PASS"`、`synthetic_fallback == False`、`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`emmc_writes == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`usb_tx_bytes == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`e_nd_actuator_tx_count == 0`、`dormant_fx6_abb_events == 0`、`dormant_fx3_evf_events == 0`、`dormant_fx6_vf_4subitems_events == 0`、`dormant_recallhold_movie_events == 0`、`dormant_recallhold_wb_events == 0`、`dormant_fx6_high_low_key_events == 0`、`dormant_hdmi_4k2k_events == 0`、`dormant_hdmi_24p60p_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，所有硬件实机挂载/写盘/跨机刷写/SPI-NOR/EL3 标志均为 `False`，未包含任何专有固件原始字节。
