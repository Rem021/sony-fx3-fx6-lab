# Round 71（Wave-57 · `44/44` 实机预演轮次 `R28..R71` · 第 `130..132` 次实跑 -> `132/132` 总实跑 · `88/88` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `[SteadyShot]` 47 档焦距与 4 重锁死 IBIS vs FX6 固定机身、`Self-timer` 休眠 Movie vs Still `#8` 指示灯/提示音、`Custom 1-2 Zebra` IRE + 4 色 `Peaking` 清洁 HDMI，以及 `RTMP/RTMPS/SRT` 零射频 / Slot-1 `EROFS=30` 防火墙

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 71** 三路独立 QEMU 实机预演（`r71a` / `r71b` / `r71c`，达成 **`44/44` 实机预演轮次 `R28..R71` · `132/132` 次独立实跑 · `88/88` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dynamic_active_bypass_events == 0`、`dormant_movie_selftimer_bypass_events == 0`、`hdmi_clean_feed_zebra_peaking_baked_pixels == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r71c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r71a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 57 四大支柱门禁、休眠符号（`Dynamic active` / `BKID_APP_setting_movie_self_timer` / `Single Burst Self-timer` / `Self-portrait 3-sec` / `Audio Signal(Start/End)` / `Audio Signal Volume` / `FX6 Zebra Both` / `FX6 RTMP/SRT/QoS Streaming`）的 fail-closed `-95 EOPNOTSUPP` 拦截、`47` 档 `[Focal Length]`（`8mm..1000mm`）枚举、Movie `[Active]` 4 重互斥锁死（`119.88p/100p`、`S&Q >= 120/100fps`、`RAW Output = On`、`De-Squeeze != Off`）+ `[Clear Image Zoom]` HFR 锁死、Still `[Self-timer(Single/Cont)]` / `[Selftimer during Bracket]` 前灯 `#8` 与 `[Audio signals]` 抑制、`Custom1` `Std+Range` / `Custom2` `Lower Limit` 与 S-Log3 `41%/61%/94%` vs `[Display LUT] = On` 后置测量、`[Peaking]` 4 色清洁 HDMI 隔离、`[Network Streaming]`（`RTMP`/`RTMPS`/`SRT` AES-128/256、仅 `59.94/50/29.97/25p` 禁用 `23.98/24p`、`[Movie Rec During Streaming]` 4K/2K60 机内 4K 锁死）与 FTP Passive（`PASV`）、三层非对称复位层级（`Camera Settings Reset` / `Reset Network Set.` / `Initialize`），以及 Tier-0 `[Airplane Mode] = On` 零射频与 `Slot 1` 恢复保险库 `-30 EROFS` 拦截；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（5 轴 IBIS 音圈执行器物理行程、前部 `#8` 自拍灯与扬声器蜂鸣、`Display LUT` 实时斑马与外录机 Clean HDMI、真实 2.4/5 GHz RF 暗室零发包、`USB-LAN CDC-NCM` 推流与物理 `Slot-1` 写保护）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 71 (`44/44` Real-HW Rounds · Wave-57 · `130th..132nd` Live Runs -> `132/132` Total Live Runs, `88/88` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-57 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave57-steadyshot-ibis-movie-selftimer-custom-zebra-streaming-intel/README.md`](../2026-11-17-global-sony-wave57-steadyshot-ibis-movie-selftimer-custom-zebra-streaming-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 71 轮（Wave-57 · `44/44` 实机轮次 / `130th..132nd` -> `132/132` 次实跑 / `88/88` PNG）三项实机预演总览（`r71a` / `r71b` / `r71c`）

| 实跑场景 | Run ID | `r71_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **71A（第 130 次实跑）：Wave-57 四大支柱 — `[SteadyShot]` 47 档焦距与 4 重 `[Active]` 锁死 vs FX6 固定机身、休眠 Movie vs Still `Self-timer #8` LED/提示音、`Custom 1-2 Zebra` IRE + 4 色 `Peaking` 清洁 HDMI、`RTMP/RTMPS/SRT` 零射频 + Slot-1 `EROFS=30` + Big-6 Home** | `r71a` | `steadyshot_47focal_selftimer_zebra_streaming_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 Movie **`[SteadyShot]`**（`Active` 自动 `[Distortion Comp.]=Auto` / `Standard` 默认 / `Off`，`ALCIN_UUD` 上 `Dynamic active` 零激活）、Still **`[SteadyShot]`**（`On` 默认 / `Off`）、**`[SteadyShot Adjust.]`**（`Auto` 默认 / `Manual`）与精确 **47 档 `[Focal Length]`（`8mm..1000mm`）**，核验 `[Active]` 4 重互斥锁死（Movie `>= 119.88p/100p`、`S&Q >= 120/100fps`、`RAW Output = On`、`De-Squeeze != Off`）及 `[Clear Image Zoom]` HFR 锁死，对比 `ILME-FX6` 固定传感器（`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED` + 6 轴 Catalyst 陀螺仪）；(2) 核验休眠 Movie `BKID_APP_setting_movie_self_timer`（`-95 EOPNOTSUPP`）vs Still **`[Self-timer(Single)]`**（`10/5/2s`）、**`[Self-timer(Cont)]`**（`10/5/2s x 3/5 Img.`）与 **`[Selftimer during Bracket]`**（`Off/2/5/10s`）+ 前部 **`#8` 灯**（分离于红 REC 灯）+ **`[Audio signals]`** 抑制（`Silent Mode = On` / Movie HDMI 音频）；(3) 核验仅 `Initialize` 复位的 **`[Zebra Display]`/`[Zebra Level]`**（`70..100+`、`Custom1` `Std+Range 0..109% +- 1..10%`、`Custom2` `Lower Limit 0..109+`，S-Log3 `41%/61%/94%` vs `[Display LUT]=On` 后置信号测量）与 4 色 **`[Peaking]`**（`White/Red/Yellow/Blue`，Clean HDMI `0` 烘焙像素）vs `FX6` `Off/Zebra1/Zebra2` 三选一独占器（无 `Both`）及 `B&W/Red/Yellow/Blue`；(4) 核验 **`[Network Streaming]`**（`RTMP`/`RTMPS`/`SRT` AES-128/256、仅 `59.94/50/29.97/25p` 无 `23.98/24p`、38 Mbps、`[Movie Rec During Streaming]` 4K/2K60 机内 4K 锁死）+ FTP Passive（`PASV`）+ Tier-0 **`[Airplane Mode]=On` 零射频（`p12/p13` `MS_RDONLY`、`wireless_tx_packets=0`）** & **`Slot-1` `EROFS=30` 防火墙**，并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r71_init_ok=1`, `r71_bridge_ok=1`, `verify_us=1094768`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.83s` | [`r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-composited.png`](assets/r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-composited.png) |
| **71B（第 131 次实跑）：Fail-Closed Wave-57 防火墙 — 休眠自拍与 `Dynamic active` 拦截、非 47 档焦距与 4 重锁死、非 4 推流帧率、`Airplane Mode` 零射频与 `Slot-1` `EROFS=30` 拦截** | `r71b` | `wave57_steadyshot_selftimer_zebra_streaming_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `Dynamic active`（`-95 EOPNOTSUPP`）、非 47 档表外焦距 `7/22/1200mm`（`-22 EINVAL`）、`[Active]` 四重互斥场景（`100p` / `S&Q 100fps` / `RAW=On` / `De-Squeeze!=Off`，`-16 EBUSY`）、`FX6` 无机身 IBIS（`-2 ENOENT` / `-95 EOPNOTSUPP`）与 OSS 开启时启用 Catalyst（`-16 EBUSY`）；(2) 拦截休眠 `Movie Self-timer` / `Single Burst Self-timer` / `Self-portrait 3-sec`（`-95 EOPNOTSUPP`）、动态/S&Q 下 Still 自拍（`-16 EBUSY`）与 `FX6` `PID_SET_SELF_TIMER` / `Audio signals` 缺失（`-95` / `-2`）；(3) 拦截无效 Zebra preset `107` / `Custom1` range `11` / `Custom2` `111` / 无效 Peaking 色（`-22 EINVAL`）与 `FX6` 双斑马 `Both`（`-95 EOPNOTSUPP`）；(4) 拦截推流 `23.98/24.00p` / `40 Mbps`（`-22 EINVAL`）、`S&Q` 同录与 `2K60` 下机内 `4K` 录影（`-16 EBUSY`）、`FX6` 原生 RTMP/SRT（`-95`）、`Airplane Mode = On`（无 USB-LAN 时 `-100 ENETDOWN`）、FTP `PORT` 主动模式（`-95 EOPNOTSUPP`）以及 **`Slot-1` 流媒体录影 / FTP 写入 / Vault / `AVF_INFO` / `p12` WLAN NVS / `P2` / `cnflasha` 写入（`-30 EROFS`）**（`slot1_vault_sha256_match=1`, `wireless_tx_packets=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r71b_ok=1`, `verify_us=968351`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.37s` | — |
| **71C（第 132 次实跑 · `44/44` 实机轮次）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-57 三层非对称复位验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r71c` | `clean_unmount_wave57_reset_h0_h3_big6` | Native ARM64 Wave-57 联合预演（**`44/44` 实机轮次 · 第 `132/132` 次独立实跑 · `88/88` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三层非对称复位层级：**`[Camera Settings Reset]` 复位 `[SteadyShot]`/`[Drive Mode]`/`[Selftimer during Bracket]` 但完整保留 `[Audio signals]`、全部 `[Zebra]`/`[Peaking]` 及全部 `(Network)`（Streaming / FTP / Airplane Mode）**（`camreset_preserves_wave57_survivors_ok=1`）；**`[Reset Network Set.]` 复位 Streaming 与 FTP 但保留 `[Airplane Mode] = On` 零射频状态**（`nwreset_preserves_airplane_ok=1`）；**`[Initialize]` 恢复含 `[Airplane Mode] -> Off` 在内的全部默认项**（`initialize_restores_wave57_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `wireless_tx_packets=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=57`，`verify_us=489802`，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.28s` | 同 `71A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-57 四大支柱初始化与 Stage-B 四路桥接（`r71a` — 第 130 次实跑）
```text
FX6_R71_WAVE57_INIT fx3_wave57_nodes_ok=1 uxc_tokens_ok=1
  steadyshot_47focal_ok=1 selftimer_audio_ok=1 zebra_peaking_ok=1 streaming_zerorf_erofs_ok=1
  focal_22_invalid_rc=-22 dyn_active_rc=-95 lock_119p_rc=-16 lock_sq120_rc=-16
  lock_raw_rc=-16 lock_desq_rc=-16 fx6_body_ibis_rc=-95
  movie_st_dormant_rc=-95 fx6_zebra_both_rc=-95
  airplane_rf_blocked_rc=-100 stream_2398_rc=-22 stream_4k_int4k_rc=-16
  stream_slot1_erofs_rc=-30 ftp_slot1_erofs_rc=-30
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dynamic_active_bypass_events=0 dormant_movie_selftimer_bypass_events=0
  hdmi_clean_feed_zebra_peaking_baked_pixels=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r71_init_ok=1 verify_us=1094768

FX6_R71_STEADYSHOT_47FOCAL_LOCKOUT_BRIDGE movie_ss_3mode_active_standard_off_ok=1
  focal_47_steps_8_to_1000mm_ok=1 four_active_lockouts_vs_fx6_fixed_ok=1
  steadyshot_47focal_guard_ok=1 dynamic_active_bypass_events=0
  ciz_hfr_bypass_events=0 emmc_write_count=0 r71_bridge_ok=1

FX6_R71_SELFTIMER_LED8_AUDIO_BRIDGE dormant_movie_selftimer_rejected_ok=1
  still_selftimer_single_cont_bracket_front8_ok=1 audio_signals_silent_hdmi_suppressed_ok=1
  selftimer_led8_audio_ok=1 dormant_movie_selftimer_bypass_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R71_ZEBRA_CUSTOM12_PEAKING_HDMI_BRIDGE zebra_custom1_std_range_custom2_lower_ok=1
  slog3_41_61_94_vs_display_lut_post_ok=1 peaking_4color_reset_immune_clean_hdmi_ok=1
  zebra_peaking_hdmi_ok=1 hdmi_clean_feed_zebra_peaking_baked_pixels=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R71_STREAMING_ZERORF_EROFS_BRIDGE rtmp_rtmps_srt_4fps_no_24p_ok=1
  rec_during_stream_4k_lockout_and_ftp_pasv_ok=1
  airplane_zero_rf_p12_p13_slot1_erofs30_ok=1 streaming_zerorf_erofs_ok=1
  wireless_tx_packets=0 passive_tx_bytes_emitted=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `54` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`119` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-57 防火墙拦截明细（`r71b` — 第 131 次实跑）
```text
FX6_R71_WAVE57_GUARD dyn_active_rc=-95 focal_7_rc=-22 focal_22_rc=-22 focal_1200_rc=-22
  lock_100p_rc=-16 lock_sq100_rc=-16 lock_raw_rc=-16 lock_desq_rc=-16
  fx6_ss_rc=-2 fx6_ibis_unsup_rc=-95 fx6_catalyst_oss_busy_rc=-16
  movie_st_rc=-95 single_burst_dormant_rc=-95 portrait_dormant_rc=-95
  movie_still_st_rc=-16 fx6_st_rc=-95 fx6_audio_sig_rc=-2
  zebra_bad_preset_rc=-22 zebra_c1_bad_range_rc=-22 zebra_c2_oob_rc=-22
  peaking_bad_col_rc=-22 fx6_zebra_both_rc=-95
  stream_2398_rc=-22 stream_2400_rc=-22 stream_40mbps_rc=-22
  stream_sq_rec_rc=-16 stream_2k60_int4k_rc=-16
  airplane_stream_rc=-100 airplane_ftp_rc=-100 ftp_active_port_rc=-95
  slot1_stream_erofs_rc=-30 slot1_ftp_erofs_rc=-30 fx6_stream_rc=-95
  slot1_wave57_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30
  p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dynamic_active_bypass_events=0 dormant_movie_selftimer_bypass_events=0
  hdmi_clean_feed_zebra_peaking_baked_pixels=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r71b_ok=1 verify_us=968351
```

### 2.3 洁净卸载还原原厂、Wave-57 三层复位与 `16/16 H0 == H3`（`r71c` — 第 132 次实跑）
```text
FX6_R71_CLEAN_UNMOUNT_WAVE57_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave57_survivors_ok=1
  nwreset_preserves_airplane_ok=1
  initialize_restores_wave57_defaults_ok=1
  dynamic_active_bypass_events=0 dormant_movie_selftimer_bypass_events=0
  hdmi_clean_feed_zebra_peaking_baked_pixels=0 wireless_tx_packets=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r71c_ok=1 verify_us=489802
```

---

## 3. `r71a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r71a` Alpha（`26.21 KiB` / `26,842 B`） | `r71a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r71a Big6 Alpha](assets/r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-alpha.png) | ![r71a Big6 Composited](assets/r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）5 轴 IBIS 音圈执行器与陀螺仪台架（验证 Movie `[SteadyShot]` `Active`/`Standard`/`Off`、无电子触点老镜头手动 47 档 `[Focal Length]` `8mm..1000mm` 机械补偿精度、`[Active]` 在 `119.88p/100p`、`S&Q 120/100fps`、`RAW Output=On` 与 `De-Squeeze != Off` 下的真实灰显锁死，对比 `ILME-FX6 Ver. 6.01` 固定传感器 + 6 轴 Catalyst 陀螺仪元数据录制）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）前部 `#8` 自拍灯、扬声器蜂鸣与清洁 HDMI 分析仪台架（验证 Still `[Self-timer(Single/Cont)]` / `[Selftimer during Bracket]` 触发 `#8` 指示灯加速闪烁与 `[Audio signals]` 在 `[Silent Mode]=On` / Movie HDMI 音频输出下的静音抑制；验证 `S-Log3` 下 `Custom1` `Std+Range` / `Custom2` `Lower Limit` 与 `[Display LUT]=On` 后置信号测量切换，以及 4 色 `[Peaking]` 在 Clean HDMI 外录画面中的零叠加像素）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）射频屏蔽箱、`USB-LAN CDC-NCM` 推流与双卡槽媒体台架（验证 `[Network Streaming]` `RTMP`/`RTMPS`/`SRT` AES-128/256 在 `59.94/50/29.97/25p` 真实网络吞吐、`[Movie Rec During Streaming]` 机内 4K 锁死、FTP Passive 断点续传、`[Airplane Mode]=On` 在 `[Reset Network Set.]` 后保持零射频、以及物理 `Slot-1` 写保护对 `AVF_INFO`/数据扇区的硬拦截）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 71A (130th Live Run): Wave-57 4-Pillar SteadyShot 47-Focal / Self-timer #8 / Custom 1-2 Zebra + 4-Color Peaking Clean-HDMI / RTMP-RTMPS-SRT Zero-RF + Slot-1 EROFS=30 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 71 --r71-mode steadyshot_47focal_selftimer_zebra_streaming_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r71a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round71-qemu/r71a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r71a-steadyshot-selftimer-zebra-streaming-big6-schinese \
  --export-png-dir reports/2026-11-17-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu/assets

# Run 71B (131st Live Run): Fail-Closed Wave-57 Guard (Dormant Dynamic active & Movie Self-timer EOPNOTSUPP, Off-table Focal EINVAL, 4 Active Lockouts EBUSY, Streaming 23.98/24p EINVAL, Airplane Mode Zero-RF ENETDOWN, Slot-1 EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 71 --r71-mode wave57_steadyshot_selftimer_zebra_streaming_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r71b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round71-qemu/r71b

# Run 71C (132nd Live Run — 44/44 Real-HW Rounds / 132/132 Live Runs / 88/88 PNGs): Clean Unmount Stock FX3 Restoration, Wave-57 3-Tier Asymmetric Reset + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 71 --r71-mode clean_unmount_wave57_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r71c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round71-qemu/r71c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dynamic_active_bypass_events == 0`、`dormant_movie_selftimer_bypass_events == 0`、`hdmi_clean_feed_zebra_peaking_baked_pixels == 0`、`wireless_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
