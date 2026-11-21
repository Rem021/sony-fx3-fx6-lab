# Milestone Round 80（Wave-66 · **`53/53` 实机预演轮次 `R28..R80` · 第 `157..159` 次实跑 -> `159/159` 总实跑 · `106/106` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备里程碑预演 — 静态 `[Drive Mode]` `10 fps` 连拍与休眠 `[Focus Bracket]` 辟谣、`[Shutter Type]` 严格双档无 `Auto` / `1/250 s` 单一 X-Sync / `[e-Front Curtain Shut.]`（`front_curtaion_shutter`）与降噪、`[Creative Look]` 10 预设 + 6 自定义 + 8 参数（`Clarity 0..9`）与休眠 `[Soft Skin Effect]` 辟谣，以及 `[Delete]` / `[Delete confirm.]` / `[Delete pressing twice]` / `[Protect]` / `[Recover Image DB]` `Slot 1` Tier-0 `EROFS=30` 防火墙闭环

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Milestone Round 80** 三路独立 QEMU 实机预演（`r80a` / `r80b` / `r80c`，正式达成 **`53/53` 实机预演轮次 `R28..R80` · `159/159` 次独立实跑 · `106/106` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`dormant_fx3_focus_bracket_events == 0`、`dormant_fx6_focus_bracket_events == 0`、`dormant_shutter_auto_events == 0`、`dormant_xsync_320_apsc_events == 0`、`dormant_fx3_soft_skin_events == 0`、`dormant_fx6_soft_skin_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r80c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r80a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `27,132 B` Alpha PNG 与 `27,467 B` Composited PNG（均严格 `<= 27,467 B`）。
- **核心关联文件**：
  - 情报基线：[Wave 66 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/reports/2026-11-17-global-sony-wave66-drive-focusbracket-shutter-efcs-creativelook-recoverdb-intel/README.md)
  - 遥测汇总：[summary.json](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/reports/2026-11-21-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/summary.json)
  - 视觉凭证：[r80_drive_10fps_focusbracket_shutter2_xsync250_efcs_nr_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/reports/2026-11-21-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/r80_drive_10fps_focusbracket_shutter2_xsync250_efcs_nr_preview.png)（`27,467 B`）· [r80_creativelook10_softskin_delete_protect_recoverdb_erofs_preview.png](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/reports/2026-11-21-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/r80_creativelook10_softskin_delete_protect_recoverdb_erofs_preview.png)（`27,132 B`）
  - 源码与测试：[fx6-stage-a-verify.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/outputs/fx6-native-presenter-closure/fx6-stage-a-verify.c) · [libgrm-fbinit9.c](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/outputs/fx6-native-presenter-closure/libgrm-fbinit9.c) · [build_and_run_round.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/outputs/fx6-native-presenter-closure/build_and_run_round.py) · [test_round80_milestone_drive_focusbracket_shutter_efcs_creativelook_recoverdb_qemu.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h484-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu/outputs/fx6-native-presenter-closure/tests/test_round80_milestone_drive_focusbracket_shutter_efcs_creativelook_recoverdb_qemu.py)
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 66 四大支柱门禁、休眠分支辟谣与 `Slot 1` `EROFS=-30` 隔离的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-13 EACCES` / `-11 EAGAIN` / `-30 EROFS` / `-1 EPERM` 护栏：
  1. **支柱 1（静态 `[Drive Mode]` `10 fps` 连拍与休眠 `[Focus Bracket]` 辟谣）**：FX3 `[Drive Mode]`（静态专属、支持 `[Camera Settings Reset]`）暴露 `Single Shooting`（默认）、`Cont. Shooting`（`Hi+ 10fps`、`Hi 8fps`、`Mid 6fps`、`Lo 3fps`；`Uncompressed RAW`/闪光灯导致降速；`> F11` 在 `Hi+/Hi/Mid` 首帧锁焦）、`Self-timer(Single/Cont)`（`10SEC_10IMAGES` 休眠 `-95`）、`Cont./Single Bracket`（`0.3..1.0 EV` × `3/5/9`、`2.0/3.0 EV` × `3/5`；`iAuto` 下禁用）、`WB bracket` 及 `DRO Bracket`（`[HLG Still Image]=On` 下禁用 `-16`）；休眠 `[Focus Bracket]`（`_f 0x7563`、`DRIVE_MODE_FOCUS_BRACKET`）在 `ILME-FX3 Ver. 7.02`（`ilc/2210` `0` 命中）与 `ILME-FX6 Ver. 6.01` 上双双严格拦截 `-95 EOPNOTSUPP`。
  2. **支柱 2（2 档 `[Shutter Type]` 无 `Auto`、`1/250 s` 单一 X-Sync、`[e-Front Curtain Shut.]` 与降噪）**：FX3 `[Shutter Type]` 严格仅 **2 档**：`Mechanical Shutter`（默认）与 `Electronic Shutter`（可 Reset），**无 `Auto` 档**（`STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO` 休眠阻断 `-95`，区别于 `[Interval Shoot Func.]` 独立默认 `Electronic Shutter`）；`Electronic Shutter` / `Silent Mode=On` 强制锁死 5 项（Flash、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.` -> `-16`）；闪光最高同步速度严格为单一 **`1/250 s`**（无 `1/320 s` APS-C 档 -> `-95`）；`[e-Front Curtain Shut.]`（默认 `On`，**抗 Camera Reset**，ELF 拼写错字 `BKID_APP_setting_front_curtaion_shutter`）；`[Long Exposure NR]`（`>= 1 s` 等时暗帧减除，默认 `On`，可 Reset）；`[High ISO NR]`（`Normal` 默认 / `Low` / `Off`，休眠 `HIGH` `-95`，不写入 `.ARW`）。对比 FX6 无机械快门 / 无 X-Sync（`-95`），改用 `Noise Suppression` 与 `Technical > APR`（未遮盖镜头阻断 `-16`）。
  3. **支柱 3（`[Creative Look]` 10 预设 + 6 自定义 + 8 参数与休眠 `[Soft Skin Effect]` 辟谣）**：FX3 `[Creative Look]`（可 Reset）暴露 10 预设（`ST` 默认、`PT`、`NT`、`VV`、`VV2`、`FL`、`IN`、`SH`、`BW`、`SE`）+ `Custom Look 1..6`（共 16 个 ELF 槽位分设 Still/Movie）+ 8 项微调参数（`Contrast/Highlights/Shadows/Saturation`: `-9..+9`；`Fade/Sharpness/Clarity`: **`0..9`** 非对称区间，`Clarity=-1` 阻断 `-22 EINVAL`；`Sharpness Range`: `1..5`）；`BW`/`SE` 锁定 `Saturation`（`-16`），Movie/`S&Q` 锁定 `Sharpness Range`（`-16`），`iAuto` / `PP != Off` / `Log Shooting != Off` / `HLG Still = On` 强制固定为 `[-]`（`-16`）；休眠 `[Soft Skin Effect]`（`_f 0x76d9`、`BKID_APP_setting_soft_skin_effect`）在 `FX3 7.02` 与 `FX6 6.01` 上双双拦截 `-95 EOPNOTSUPP`，对比 FX6 `Base Look` / `Scene File` / `Multi Matrix`。
  4. **支柱 4（`[Delete]` / `[Delete confirm.]` / `[Delete pressing twice]` / `[Protect]` / `[Recover Image DB]` `Slot 1` Tier-0 `EROFS=30` 防火墙）**：`[Delete confirm.]`（默认 `"Cancel" first` 抗 Reset）、`[Delete pressing twice]`（默认 `Off` 抗 Reset）、Proxy 同步删除/保护联动、`[Protect]` 与 `[Recover Image DB]`（重写 `AVF_INFO` 并清除 FTP 传输记录，**抗 Reset 且抗 Initialize**）—— 凡指向 Tier-0 `Slot 1` 的写/删/属性变更/数据库重建操作全部在协议与内核 VFS 层以 **`-30 EROFS`** 闭环阻断（`slot1_writes=0`、`slot1_data_sector_writes=0`、`slot1_avf_info_mutated=0`、`usb_tx=0`）；`[Display Media Info.]`（单卡最高显示 `40,000` 张）保持 `O_RDONLY` 只读安全通过；对比 FX6 `Thumbnail > Lock/Delete Clip`、`Restore Media(A)/(B)`（`ng_write_protected` -> `-30 EROFS`）与 `Media Status`。
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测尚未上电执行，详见 §4。**

> **日期**：2026-11-21 | **轮次**：**Milestone Round 80 (`53/53` Real-HW Rounds · Wave-66 · `157th..159th` Live Runs -> `159/159` Total Live Runs, `106/106` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-66 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave66-drive-focusbracket-shutter-efcs-creativelook-recoverdb-intel/README.md`](../2026-11-17-global-sony-wave66-drive-focusbracket-shutter-efcs-creativelook-recoverdb-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 80 轮里程碑（Wave-66 · `53/53` 实机轮次 / `157th..159th` -> `159/159` 次实跑 / `106/106` PNG）三项实机预演总览（`r80a` / `r80b` / `r80c`）

| 实跑场景 | Run ID | `r80_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **80A（第 157 次实跑）：Wave-66 四大支柱 — `[Drive Mode]` `10 fps` + 休眠 `[Focus Bracket]` 辟谣、`[Shutter Type]` 2 档无 `Auto` / `1/250 s` X-Sync / `front_curtaion_shutter` & NR、`[Creative Look]` 10 预设 + 6 自定义 + 8 参（`Clarity 0..9`）+ 休眠 `[Soft Skin Effect]` 辟谣、`[Delete]` / `[Protect]` / `[Recover Image DB]` `Slot 1 EROFS=30` + Big-6 Home** | `r80a` | `drive_focusbracket_shutter_efcs_creativelook_recoverdb_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Drive Mode]`**（`Hi+ 10fps / Hi 8fps / Mid 6fps / Lo 3fps`、`Uncompressed RAW`/闪光降速、`> F11` 首帧锁焦、`Cont./Single/WB/DRO Bracket`、休眠 `[Focus Bracket]` 在 FX3 & FX6 双 `-95 EOPNOTSUPP`）；(2) 核验 **`[Shutter Type]`** 仅 2 档无 `Auto`（`-95`）、电子快门/静音 5 项锁死、单一 `1/250 s` X-Sync（无 `1/320 s` APS-C `-95`）、`[e-Front Curtain Shut.]`（`front_curtaion_shutter`）、`[Long Exposure NR]`、`[High ISO NR]` 对比 FX6 零机械快门 + APR；(3) 核验 **`[Creative Look]`** 10 预设 + `Custom 1..6`（16 槽位 Still/Movie 独立）+ 8 参（`Clarity 0..9`、`BW/SE` 锁饱和、Movie 锁锐度范围、`PP/Log/iAuto/HLG` 锁 `[-]`）+ 休眠 `[Soft Skin Effect]` 双 `-95`；(4) 核验 **`[Delete]`/`[Delete pressing twice]`/`[Protect]`/`[Recover Image DB]`** `Slot 1` VFS 与协议双 `-30 EROFS`（`slot1_writes=0`, `slot1_avf_info_mutated=0`, `usb_tx=0`）+ `[Display Media Info.]` `40,000` 只读安全，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r80_init_ok=1`, `r80_bridge_ok=1`, `verify_us=307628`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `78.16s` | [`r80_drive_10fps_focusbracket_shutter2_xsync250_efcs_nr_preview.png`](r80_drive_10fps_focusbracket_shutter2_xsync250_efcs_nr_preview.png) / [`r80_creativelook10_softskin_delete_protect_recoverdb_erofs_preview.png`](r80_creativelook10_softskin_delete_protect_recoverdb_erofs_preview.png) |
| **80B（第 158 次实跑）：Fail-Closed Wave-66 防火墙 — FX3/FX6 休眠 `[Focus Bracket]` / FX6 静态 Drive / `10SEC_10IMAGES` / `[Shutter Type]=Auto` / `1/320 s` APS-C X-Sync / `High ISO NR=High` / FX6 机械快门 / FX3 & FX6 休眠 `[Soft Skin Effect]` / FX6 Creative Look（`-95`）、Movie/S&Q Drive / Bracket `iAuto` / DRO `HLG` / `>1/250s` X-Sync / 电子快门 & 静音 5 锁 / Long NR 连拍 & `iAuto Off` / RAW High ISO NR / FX6 未遮盖 APR / `BW/SE` 饱和 / Movie 锐度范围 / `iAuto/PP/Log/HLG` 锁（`-16`）、越界与 `Clarity=-1` / `NULL`（`-22`）、保护文件删片（`-13`）、低电建库（`-11`）、`live_attach`（`-1`）及 `Slot 1`（`Delete`/`Delete-twice`/`Protect`/`Recover DB`/`AVF_INFO`/`DCIM`）/ FX6 `ng_write_protected` / `P12` / `P2` / `cnflasha`（`-30 EROFS`）** | `r80b` | `wave66_drive_focusbracket_shutter_efcs_creativelook_recoverdb_guard` | Native ARM64 Fail-Closed 注入阻断实测：53 项故障注入全部命中精确 POSIX `errno`（`-95`/`-16`/`-22`/`-13`/`-11`/`-30`/`-1`），实证 `slot1_vault_sha256_match=1`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `emmc_write_count=0`, `cnflasha_writes=0`, `r80b_ok=1`, `verify_us=1001762`, `FX6_R80_WAVE66_GUARD_RC=0` | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `10.00s` | — |
| **80C（第 159 次实跑 · **`53/53` 实机轮次里程碑闭环**）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-66 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r80c` | `clean_unmount_wave66_reset_h0_h3_big6` | Native ARM64 Wave-66 联合预演（**`53/53` 实机轮次 · 第 `159/159` 次独立实跑 · `106/106` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位：**`[Camera Settings Reset]`** 复位 `Drive Mode`、`Shutter Type`、`Long Exposure NR`、`High ISO NR`、`Creative Look`，同时完整保留 **`e-Front Curtain Shut.`、`Delete confirm.`、`Delete pressing twice`、`Recover Image DB` 代际与 `Airplane Mode=On`**；**`[Reset Network Set.]`** 完整保留全部 Wave-66 设置与 `Airplane Mode=On`；**`[Initialize]`** 还原 `e-Front Curtain Shut.`、`Delete confirm.` 与 `Delete pressing twice` 默认值同时仍保留 **`Recover Image DB` 代际与 `Airplane Mode=On`**；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `usb_tx=0`, `slot1_writes=0`, `slot1_data_sector_writes=0`, `slot1_avf_info_mutated=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`osd=41`, `verify_us=1107448`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.84s` | 同 `80A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-66 四大支柱初始化与 Stage-B 四路桥接（`r80a` — 第 157 次实跑）
```text
FX6_R80_WAVE66_INIT fx3_wave66_nodes_ok=1 uxc_tokens_ok=1 drive_10fps_focusbracket_ok=1
  shutter2_xsync250_efcs_nr_ok=1 creativelook10_softskin_ok=1 delete_protect_recoverdb_erofs_ok=1
  fx3_focus_bracket_rc=-95 fx6_focus_bracket_rc=-95 shutter_auto_dormant_rc=-95
  xsync_320_apsc_rc=-95 eshutter_flash_lock_rc=-16 fx6_mech_shutter_rc=-95
  cl_clarity_neg1_rc=-22 cl_bw_sat_lock_rc=-16 cl_movie_srange_lock_rc=-16
  cl_pp_override_rc=-16 fx3_soft_skin_rc=-95 fx6_soft_skin_rc=-95
  slot1_delete_erofs_rc=-30 slot1_delete_twice_erofs_rc=-30 slot1_protect_erofs_rc=-30
  slot1_recoverdb_erofs_rc=-30 slot1_vfs_avf_erofs_rc=-30 slot1_unlink_erofs_rc=-30
  slot1_media_info_ro_rc=0 fx6_restore_wp_erofs_rc=-30 p2_write_blocked_rc=-30
  p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_fx3_focus_bracket_events=0 dormant_fx6_focus_bracket_events=0
  dormant_shutter_auto_events=0 dormant_xsync_320_apsc_events=0
  dormant_fx3_soft_skin_events=0 dormant_fx6_soft_skin_events=0
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r80_init_ok=1 verify_us=307628

FX6_STAGE_B_R80_BRIDGE round=80 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19 drive_10fps_dormant_focus_bracket_ok=1
  shutter2_no_auto_xsync250_efcs_nr_ok=1
  creativelook10_custom6_8param_dormant_softskin_ok=1
  delete_protect_recoverdb_slot1_erofs30_ok=1
  milestone_53rd_realhw_159th_live_106_pngs=1 usb_tx=0 slot1_writes=0
  slot1_write_count=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0
```

### 2.2 Fail-Closed Wave-66 防火墙拦截明细（`r80b` — 第 158 次实跑）
```text
FX6_R80_WAVE66_GUARD fx3_focus_bracket_rc=-95 fx6_focus_bracket_rc=-95 fx6_still_drive_rc=-95
  drive_movie_lock_rc=-16 drive_sq_lock_rc=-16 self_timer_10img_dormant_rc=-95
  bkt_2ev_9shots_einval_rc=-22 bkt_iauto_lock_rc=-16 dro_hlg_lock_rc=-16
  shutter_auto_rc=-95 xsync_320_apsc_rc=-95 xsync_500_over_rc=-16
  eshutter_flash_rc=-16 eshutter_longnr_rc=-16 eshutter_efcs_rc=-16
  eshutter_bulb_rc=-16 silent_antiflicker_rc=-16 longnr_cont_rc=-16
  longnr_iauto_off_rc=-16 highiso_dormant_high_rc=-95 highiso_raw_only_rc=-16
  fx6_mech_rc=-95 fx6_apr_uncapped_rc=-16 fx3_soft_skin_rc=-95 fx6_soft_skin_rc=-95
  fx6_creative_look_rc=-95 cl_slot16_einval_rc=-22 cl_clarity_neg1_rc=-22
  cl_fade_neg1_rc=-22 cl_srange_0_rc=-22 cl_bw_sat_rc=-16 cl_se_sat_rc=-16
  cl_movie_srange_rc=-16 cl_iauto_lock_rc=-16 cl_pp_lock_rc=-16 cl_log_lock_rc=-16
  cl_hlg_lock_rc=-16 slot1_del_erofs_rc=-30 slot1_del_twice_erofs_rc=-30
  slot1_prot_erofs_rc=-30 slot1_recoverdb_erofs_rc=-30 slot2_protected_del_rc=-13
  slot2_recoverdb_lowbatt_rc=-11 fx6_restore_wp_erofs_rc=-30 null_cfg_einval_rc=-22
  live_attach_eperm_rc=-1 slot1_avf_erofs_rc=-30 dcim_unlink_erofs_rc=-30
  dcim_chmod_erofs_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 usb_tx=0 slot1_writes=0
  slot1_data_sector_writes=0 slot1_avf_info_mutated=0 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r80b_ok=1 verify_us=1001762
FX6_R80_WAVE66_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-66 三层非对称复位与 `16/16 H0 == H3`（`r80c` — 第 159 次实跑）
```text
FX6_R80_CLEAN_UNMOUNT_WAVE66_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_drive_shutter_nr_creativelook_preserves_efcs_delete_recoverdb_airplane_ok=1
  nwreset_preserves_wave66_efcs_delete_recoverdb_airplane_ok=1
  initialize_restores_efcs_delete_preserves_recoverdb_airplane_ok=1
  dormant_fx3_focus_bracket_events=0 dormant_fx6_focus_bracket_events=0
  dormant_shutter_auto_events=0 dormant_xsync_320_apsc_events=0
  dormant_fx3_soft_skin_events=0 dormant_fx6_soft_skin_events=0
  usb_tx=0 slot1_writes=0 slot1_data_sector_writes=0 slot1_avf_info_mutated=0
  rf_tx_packets=0 slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0 dlopen_ok=1 surfaces_verified=16
  surfaces_h0_eq_h3=16 drift_bits=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 emmc_write_count=0
  r80c_ok=1 verify_us=1107448
```

---

## 3. `r80a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| Scene 2 Alpha（`26.50 KiB` / `27,132 B`） | Scene 1 Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r80a Big6 Alpha](r80_creativelook10_softskin_delete_protect_recoverdb_erofs_preview.png) | ![r80a Big6 Composited](r80_drive_10fps_focusbracket_shutter2_xsync250_efcs_nr_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）机械快门与静态连拍台架（验证 `10/8/6/3 fps` 连拍在 `Uncompressed RAW`/闪光下的速率下降、`> F11` 首帧锁焦、`[Focus Bracket]` 与 `[Shutter Type]=Auto` 的实机菜单缺席、单一 `1/250 s` 闪光同步上限、`[e-Front Curtain Shut.]` 焦外切边与抗 Reset 特性、`[Long Exposure NR]` `>= 1 s` 等时暗帧减除及 `[High ISO NR]` 对 `.ARW` 零写入）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）色彩管线台架（验证 `[Creative Look]` 10 预设 + 6 自定义 Still/Movie 独立槽位 + 8 项微调参数 `Clarity/Fade/Sharpness 0..9`、`BW/SE` 锁饱和、Movie 锁 `Sharpness Range`、`iAuto/PP/Log/HLG` 覆盖为 `[-]`，以及双机身 `[Soft Skin Effect]` 实机休眠缺席）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）与 `ILME-FX6`（`Ver. 6.01`）回放与媒体写保护台架（验证 `[Delete confirm.]`、`[Delete pressing twice]`、Proxy 同步删除/保护、`[Protect]`、`[Recover Image DB]` `AVF_INFO` 重建与 FTP 清除对比 Tier-0 `Slot 1` 物理写保护隔离，以及 `[Display Media Info.]` `40,000` 张只读遥测）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 80A (157th Live Run): Wave-66 4-Pillar Stage-A/B + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 80 --r80-mode drive_focusbracket_shutter_efcs_creativelook_recoverdb_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r80a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round80-qemu/r80a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r80a-wave66-big6 \
  --export-png-dir <SCRATCH_ROOT>/round80-pngs

# Run 80B (158th Live Run): Fail-Closed Wave-66 Guard (-95/-16/-22/-13/-11/-30/-1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 80 --r80-mode wave66_drive_focusbracket_shutter_efcs_creativelook_recoverdb_guard --sd-manifest-mode valid --lang en \
  --run-id r80b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round80-qemu/r80b

# Run 80C (159th Live Run — Milestone Round 80: 53/53 Real-HW Rounds / 159/159 Live Runs / 106/106 PNGs <= 27,467 B): Clean Unmount + Wave-66 3-Tier Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 80 --r80-mode clean_unmount_wave66_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r80c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round80-qemu/r80c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`usb_tx == 0`、`slot1_writes == 0`、`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == 0`、`e_nd_actuator_tx_count == 0`、`dormant_fx3_focus_bracket_events == 0`、`dormant_fx6_focus_bracket_events == 0`、`dormant_shutter_auto_events == 0`、`dormant_xsync_320_apsc_events == 0`、`dormant_fx3_soft_skin_events == 0`、`dormant_fx6_soft_skin_events == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，所有硬件实机挂载/写盘/跨机刷写/SPI-NOR/EL3 标志均为 `False`，未包含任何专有固件原始字节。
