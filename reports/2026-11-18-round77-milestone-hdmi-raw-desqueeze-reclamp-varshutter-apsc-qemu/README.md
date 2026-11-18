# Round 77 Milestone（Wave-63 · **`50/50` 实机预演轮次 `R28..R77` · 第 `148..150` 次实跑 -> `150/150` 总实跑 · `100/100` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `[HDMI Output Settings]` `4264x2408` 16-bit 线性 RAW 与 `Rec. Media dur HDMI Output` 矩阵、`[De-Squeeze Display]` `1.5x`/`1.6x(1.65x)` vs 缺失 `1.8x` 与 4+6 互斥旁路、`[REC Lamp]` 三灯物理联动 / `[Emphasized REC Display]` / `[Remain Shoot Display]` / `[Auto Review]`，以及 `[Anti-flicker Shoot.]` vs 休眠 `[Var. Shutter]` + `[APS-C S35 Shooting]` 4K 锁死与 Reset 勘误闭环

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 77 Milestone** 三路独立 QEMU 实机预演（`r77a` / `r77b` / `r77c`，正式达成 **`50/50` 实机预演轮次 `R28..R77` · `150/150` 次独立实跑 · `100/100` 张 `<= 27,467 B` PNG 视觉凭证里程碑**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`slot1_data_sector_writes == 0`、`dormant_raw_gamut_bypass_events == 0`、`dormant_24p_8bit_bypass_events == 0`、`dormant_desqueeze_18x_bypass_events == 0`、`dormant_reclamp_only_one_bypass_events == 0`、`dormant_var_shutter_ecs_bypass_events == 0`、`recorded_card_stream_altered == 0`、`clean_hdmi_emph_rec_baked_pixels == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r77c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r77a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 63 四大支柱门禁、目录纠偏、Reset 勘误闭环与休眠符号（已移除 Ver. 1.x `[Color Gamut for RAW Output]` `_f 0x6bdc`、休眠 `24.00p 8bit` `_f 0x748a`、完全缺失的 `[De-Squeeze Display]` `1.8x`、`REC_LAMP_LIGHT_UP_ONLY_ONE` `_f 0x743e` 与前后顶灯拆分解耦、`[Var. Shutter]` / `[Anti-flicker Set.]` `BKID_APP_setting_high_res_ss` 与 FX6 `ECS`、`TALLY` 菜单，以及**修正 Wave 42 勘误：`[APS-C S35 Shooting]` 实为抗 `[Camera Settings Reset]`、仅 `[Initialize]` 复位**）的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-30 EROFS` / `-1 EPERM` 拦截：
  1. **`[HDMI Output Settings]`（8 项抗 Reset 子菜单、`4264x2408` 16-bit 线性 RAW 与 `[Rec. Media dur HDMI Output]` 矩阵）**：`[Rec. Media dur HDMI Output]`（`On` 默认 / `Off(HDMI Only)`；`S&Q` 锁死 `On`；当 `On` 且 `RAW Output = On` 时机内 XAVC/Proxy 仍写入 `[Recording Media]`，故 Tier-0 `Slot 1` 强制 `EROFS=-30` 阻断；`Off(HDMI Only)` 旁路机内写卡且零计数器递增）、`[Output Resolution]`（`Auto`/`2160p`/`1080p`/`1080i`；在 `Rec. Media=On` & `RAW=Off` 且 `Log != Off` 或 `PPLUT1..4` 时强降 `1080p`）、`[4K Output Set.(HDMI Only)]`（仅 10-bit：`59.94p/50p`/`29.97p`/`25p`/`23.98p`/`24.00p` 重启边界；休眠 `24.00p 8bit` `-95`）、`[RAW Output]`（`4264x2408` 16-bit 线性 HDMI Type-A，须 Movie + `Log != Off`，锁 `S-Log3` 并禁用 `Active` 防抖与 `HDMI Info. Display`）、已合并的 Ver. 1.x `[Color Gamut for RAW Output]`（`_f 0x6bdc`，独立写 `-95`）、`[Time Code Output]`（`[REC Control]` 硬前置；无 TC 开 `REC Control` 返回 `-16 EBUSY`）与 `[4ch Audio Output]`（`CH1/CH2` / `CH3/CH4` 2ch HDMI LPCM），对比 `ILME-FX6 Ver. 6.01` `12G-SDI RAW`（`4096x2160`/`3840x2160 "C"` 且限制 HDMI `<=1080p`、4ch 24-bit SDI LPCM）+ `RAW(HDMI)` `4240x2392`（无 `24Hz`）与 `SDI/HDMI Remote I/F` vs `Parallel Rec`；
  2. **`[De-Squeeze Display]`（`Setup -> [Display Option]`，抗 Reset）**：5 个激活档位（`Off`、`1.3x`、`1.5x`、`1.6x` 底层执行 `1.65x` `VAL_DE_SQUEEZE_DISP_1_65X` 还原 `2.39:1`、`2.0x`），**`1.8x` 完全缺失（`0` 命中 -> `-95 EOPNOTSUPP`）**；非 `Off` 强锁 4 项（`Focus Mode = MF`、`Focus Area = Wide`、`SteadyShot = Off`、`Face Priority in Multi Metering = Off`，违例 `-16 EBUSY`）；永不篡改机内录制码流，与 `Focus Magnifier`（`x4.0`）及 `Bright Monitoring` 共存，且在 `ilc/2210` 全部 6 种条件（`Log = Off`、`RAW Output = On` HDMI、`Off(HDMI Only)` HDMI、Still 模式 `MOVIE` 键、`Remote Shooting`、`Photo Capture`）下自动旁路；对比 `ILME-FX6`（无 `1.6x/1.65x` 且永不反挤压 SDI）；
  3. **`[REC Lamp]` 三灯硬件联动（`Setup -> [Setup Option]`，抗 Reset）、`[Emphasized REC Display]`、`[Remain Shoot Display]` 与 Still `[Auto Review]`**：正式项名为 `[REC Lamp]`（`0` `TALLY` 菜单命中）：`All On` / `Only Front Off`（关前灯，保留后灯+顶部透光 `REC` 键联动亮） / `All Off`（休眠 `REC_LAMP_LIGHT_UP_ONLY_ONE` `_f 0x743e` 与后/顶分拆 `-95`），与 `[Silent Mode]` 解耦（静音不关录制灯），对比 `FX6` `Technical > Tally`（Front/Rear/G/Y/Brightness）+ `Monitoring > Display On/Off > Tally`；`[Emphasized REC Display]`（默认 `On`，可 Reset，Clean-HDMI `0 px` 零污染）；`[Remain Shoot Display]`（激活态 Still 连拍余量，抗 Reset）；`[Auto Review]`（`Off`/`2/5/10 Sec`，仅 Still 且间隔拍摄禁用，抗 Reset）；
  4. **`[Anti-flicker Shoot.]` vs 休眠 `[Var. Shutter]` / FX6 `ECS` 与 `[APS-C S35 Shooting]` 4K 锁死及 Wave 42 Reset 勘误闭环**：休眠 `[Var. Shutter]` / `[Anti-flicker Set.]`（`BKID_APP_setting_high_res_ss`、`0` `TYPE_MENU_ITEM_*HIGH_RES*` 命中）与 FX6 `ECS`（`23.99..8000 Hz`）均 `-95 EOPNOTSUPP`；活跃项仅 Still 机械快门专用 `[Anti-flicker Shoot.]`（100/120 Hz，可 Reset，Movie/S&Q/BULB/电子快门/Silent Mode 下 `-16 EBUSY`）。**`[APS-C S35 Shooting]`（`Auto` 默认/`On`/`Off`，依 `ilc/2210` 勘误抗 `[Camera Settings Reset]`、仅 `[Initialize]` 复位）**锁死全部 4K/DCI 4K/S&Q 4K/HDMI 4K/RAW（`-16 EBUSY`），将 Movie 限制为 `HD 1920x1080`（`<=120p`，S&Q `200/240fps` 门控），Still 由 `12M` 降至 `M: 5.1M`（`2768x1848` 3:2 / `4.3M` 16:9）；
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（Type-A HDMI RAW 物理分析仪、变形镜头光学与 LCD/HDMI 监测、三灯与高光红框光学实测、高帧频 LED 防闪烁与 APS-C 实拍裁切）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 77 Milestone (`50/50` Real-HW Rounds · Wave-63 · `148th..150th` Live Runs -> `150/150` Total Live Runs, `100/100` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-63 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/README.md`](../2026-11-17-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 77 轮里程碑（Wave-63 · `50/50` 实机轮次 / `148th..150th` -> `150/150` 次实跑 / `100/100` PNG）三项实机预演总览（`r77a` / `r77b` / `r77c`）

| 实跑场景 | Run ID | `r77_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **77A（第 148 次实跑）：Wave-63 四大支柱 — `[HDMI Output Settings]` 8 项 `4264x2408` 16-bit RAW & `Rec. Media dur HDMI Output`、`[De-Squeeze Display]` `1.5x`/`1.6x(1.65x)` vs 缺 `1.8x` & 4+6 互斥旁路、`[REC Lamp]` 三灯联动 / `Emphasized REC Display` / `Remain Shoot` / `Auto Review`、`[Anti-flicker Shoot.]` vs 休眠 `[Var. Shutter]` + `[APS-C S35 Shooting]` 4K 锁死 & Reset 勘误 + Big-6 Home** | `r77a` | `hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[HDMI Output Settings]`** 8 项抗 Reset、`4264x2408` 16-bit 线性 RAW（锁 `S-Log3`、禁 `Active` 防抖与 `HDMI Info. Display`）、`[Rec. Media dur HDMI Output]` `On`（`RAW=On` 时仍写卡，`Slot 1` `-30 EROFS`）vs `Off(HDMI Only)`（零写卡；`S&Q` 锁 `On`）、`Log/PPLUT` `1080p` 降频、10-bit 4K `24.00p` 重启（`24.00p 8bit` `-95`）、已移除 `[Color Gamut for RAW Output]`（`-95`）、`TC Out -> REC Control`（`-16`）与 2ch `[4ch Audio Output]`；(2) 核验 **`[De-Squeeze Display]`** 5 档（`Off`/`1.3x`/`1.5x`/`1.6x[1.65x]`/`2.0x`）、缺失 `1.8x`（`-95`）、4 项硬锁（`MF`/`Wide`/`SteadyShot=Off`/`Face Prio=Off`）、零改写机内录制流、与 `Focus Magnifier` / `Bright Monitoring` 共存及 6 类 `ilc/2210` 自动旁路；(3) 核验 **`[REC Lamp]`**（`0` `TALLY` 命中，后+顶部 `REC` 联动、`REC_LAMP_LIGHT_UP_ONLY_ONE` `-95`、与 `Silent Mode` 解耦）、**`[Emphasized REC Display]`** Clean-HDMI `0 px`、**`[Remain Shoot Display]`** 与 Still **`[Auto Review]`**（间隔拍摄禁用 `-16`）；(4) 核验 Still 机械 **`[Anti-flicker Shoot.]`**（100/120Hz，Movie `-16`）、休眠 **`[Var. Shutter]`** / FX6 `ECS`（`-95`）与 **`[APS-C S35 Shooting]`** 4K/DCI 4K/RAW 锁死（`-16`）+ Still `5.1M` + Wave 42 Reset 勘误闭环，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r77_init_ok=1`, `r77_bridge_ok=1`, `verify_us=897256`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.73s` | [`r77_hdmi_raw_4264_recmedia_desqueeze_165x_preview.png`](r77_hdmi_raw_4264_recmedia_desqueeze_165x_preview.png) / [`r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png`](r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png) |
| **77B（第 149 次实跑）：Fail-Closed Wave-63 防火墙 — 移除项 `Color Gamut for RAW Output` / 休眠 `24.00p 8bit` / `De-Squeeze 1.8x` / `REC_LAMP_LIGHT_UP_ONLY_ONE` / `Var. Shutter` / `FX6 ECS`、HDMI/De-Squeeze/AutoReview/Anti-flicker/APS-C 全部互斥与 `Slot 1` `EROFS=-30` + `live_attach=-1 EPERM` 全面阻断** | `r77b` | `wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截已移除 `Color Gamut for RAW Output`、休眠 `24.00p 8bit`、FX6 `12G-SDI RAW`（`-95 EOPNOTSUPP`）、`S&Q Off(HDMI Only)` / 无 Log RAW / `Active` 防抖 / `HDMI Info=On` / 无 TC 开 `REC Control`（`-16 EBUSY`）及 `Rec. Media=On + RAW=On` 触发 `Slot 1` 写盘（`-30 EROFS`）；(2) 拦截缺失 `1.8x`、FX6 `1.65x`（`-95 EOPNOTSUPP`）、4 项 De-Squeeze 违规（`AF` / 非 `Wide` / `SteadyShot!=Off` / `Face Prio!=Off` `-16 EBUSY`）；(3) 拦截休眠 `REC_LAMP_LIGHT_UP_ONLY_ONE`、前后顶灯分拆与 `FX6 Tally` 菜单（`-95`）、Movie/Interval `Auto Review`（`-16`）；(4) 拦截休眠 `Var. Shutter` / `FX6 ECS`（`-95`）、Movie/E-Shutter/`BULB`/`Silent Mode` 下 `Anti-flicker`（`-16`）、`APS-C S35` 下 `XAVC HS 4K`/`DCI 4K`/`RAW`/`S&Q 240fps`（`-16`）、`NULL` 参数（`-22 EINVAL`）、`live_attach`（`-1 EPERM`）以及 `Slot 1`/`P12`/`P2`/`cnflasha` 写入（`-30 EROFS`，`slot1_vault_sha256_match=1`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `cnflasha_writes=0`, `r77b_ok=1`, `verify_us=984287`, `FX6_R77_WAVE63_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `10.15s` | — |
| **77C（第 150 次实跑 · **`50/50` 实机轮次里程碑闭环**）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-63 非对称复位与 Wave 42 `[APS-C S35 Shooting]` Reset 勘误闭环验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r77c` | `clean_unmount_wave63_reset_h0_h3_big6` | Native ARM64 Wave-63 联合里程碑预演（**`50/50` 实机轮次 · 第 `150/150` 次独立实跑 · `100/100` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证非对称复位层级与 Wave 42 勘误闭环：**`[Camera Settings Reset]` 复位 `[Emphasized REC Display]=On` 与 `[Anti-flicker Shoot.]=Off`，同时完整保留 `[HDMI Output Settings]` 8 项、`[De-Squeeze Display]`、`[REC Lamp]`、`[Remain Shoot Display]`、`[Auto Review]`、`[APS-C S35 Shooting]`（Wave 42 勘误实证！）与 `[Airplane Mode]=On`**（`camreset_resets_emph_rec_antiflicker_preserves_hdmi8_desq_reclamp_remain_autorev_apsc_airplane_ok=1`）；**`[Reset Network Set.]` 完整保留 Wave-63 全部项、`[APS-C S35 Shooting]` 与 `[Airplane Mode]=On`**（`nwreset_preserves_wave63_apsc_airplane_ok=1`）；**`[Initialize]` 恢复全部 Wave-63 与 `[APS-C S35 Shooting]=Auto` 默认值，同时依然保持 `[Airplane Mode]=On`**（`initialize_restores_wave63_defaults_preserves_airplane_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `slot1_data_sector_writes=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`osd=40`, `verify_us=492539`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.38s` | 同 `77A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-63 四大支柱初始化与 Stage-B 四路桥接（`r77a` — 第 148 次实跑）
```text
FX6_R77_WAVE63_INIT fx3_wave63_nodes_ok=1 uxc_tokens_ok=1 hdmi_raw_4264_recmedia_ok=1
  desqueeze_165x_4locks_ok=1 reclamp_3led_emph_rec_autorev_ok=1 antiflicker_no_varshutter_apsc_ok=1
  raw_gamut_removed_rc=-95 rec_ctrl_no_tc_rc=-16 raw_recmedia_on_slot1_erofs_rc=-30
  desq_18x_absent_rc=-95 desq_steadyshot_lock_rc=-16 reclamp_only_one_rc=-95
  autorev_interval_rc=-16 var_shutter_dormant_rc=-95 apsc_4k_lockout_rc=-16 antiflicker_movie_rc=-16
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_raw_gamut_bypass_events=0 dormant_24p_8bit_bypass_events=0
  dormant_desqueeze_18x_bypass_events=0 dormant_reclamp_only_one_bypass_events=0
  dormant_var_shutter_ecs_bypass_events=0 recorded_card_stream_altered=0
  clean_hdmi_emph_rec_baked_pixels=0 slot1_data_sector_writes=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r77_init_ok=1 verify_us=897256

FX6_STAGE_B_R77_BRIDGE round=77 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19
  hdmi_8items_4264_16bit_raw_recmedia_tc_2ch_audio=1
  desqueeze_5ratios_15x_165x_no_18x_4locks_6bypasses=1
  reclamp_3led_coupled_silent_decoupled_emph_rec_remain_autorev=1
  antiflicker_still_mech_no_varshutter_ecs_apsc_4k_lockout_reset_immune=1
  milestone_50th_realhw_150th_live_100_pngs=1
  dormant_raw_gamut_bypass_events=0 dormant_24p_8bit_bypass_events=0
  dormant_desqueeze_18x_bypass_events=0 dormant_reclamp_only_one_bypass_events=0
  dormant_var_shutter_ecs_bypass_events=0 recorded_card_stream_altered=0
  clean_hdmi_emph_rec_baked_pixels=0 slot1_write_count=0 slot1_data_sector_writes=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0

FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE hdmi_8items_4264_16bit_raw_ok=1
  rec_media_hdmi_only_zero_write_vs_erofs30_ok=1 tc_out_prereq_and_2ch_audio_ok=1
  hdmi_raw_4264_recmedia_ok=1 dormant_raw_gamut_bypass_events=0 dormant_24p_8bit_bypass_events=0
  slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0 r77_bridge_ok=1

FX6_R77_DESQUEEZE_165X_4LOCKS_BRIDGE desqueeze_5ratios_15x_165x_no_18x_ok=1
  desqueeze_4lockouts_6bypasses_zero_card_mut_ok=1 desqueeze_165x_4locks_ok=1
  dormant_desqueeze_18x_bypass_events=0 recorded_card_stream_altered=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R77_RECLAMP_3LED_EMPH_REC_AUTOREV_BRIDGE reclamp_3led_coupled_silent_decoupled_ok=1
  emph_rec_clean_hdmi_remain_autorev_ok=1 reclamp_3led_emph_rec_autorev_ok=1
  dormant_reclamp_only_one_bypass_events=0 clean_hdmi_emph_rec_baked_pixels=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R77_ANTIFLICKER_NO_VARSHUTTER_APSC_BRIDGE antiflicker_still_mech_no_varshutter_ecs_ok=1
  apsc_s35_4k_lockout_51m_reset_immune_ok=1 antiflicker_no_varshutter_apsc_ok=1
  dormant_var_shutter_ecs_bypass_events=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `50` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、实时多线程零崩溃。

### 2.2 Fail-Closed Wave-63 防火墙拦截明细（`r77b` — 第 149 次实跑）
```text
FX6_R77_WAVE63_GUARD raw_gamut_removed_rc=-95 hdmi_24p_8bit_dormant_rc=-95 fx6_sdi_raw_rc=-95
  sq_hdmi_only_lock_rc=-16 raw_no_log_rc=-16 raw_active_ss_rc=-16 raw_hdmi_info_rc=-16
  rec_ctrl_no_tc_rc=-16 raw_recmedia_on_slot1_erofs_rc=-30
  desq_18x_absent_rc=-95 fx6_desq_165x_absent_rc=-95
  desq_af_lock_rc=-16 desq_focus_area_lock_rc=-16 desq_steadyshot_lock_rc=-16 desq_face_prio_lock_rc=-16
  reclamp_only_one_rc=-95 reclamp_uncoupled_split_rc=-95 fx6_tally_menu_rc=-95
  autorev_movie_lock_rc=-16 autorev_interval_lock_rc=-16
  var_shutter_dormant_rc=-95 fx6_ecs_dormant_rc=-95
  antiflicker_movie_rc=-16 antiflicker_eshutter_rc=-16 antiflicker_bulb_rc=-16 antiflicker_silent_rc=-16
  apsc_4k_hs_lock_rc=-16 apsc_dci4k_lock_rc=-16 apsc_raw_out_lock_rc=-16 apsc_sq_240fps_lock_rc=-16
  null_cfg_einval_rc=-22 live_attach_eperm_rc=-1
  slot1_wave63_erofs_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_raw_gamut_bypass_events=0 dormant_24p_8bit_bypass_events=0
  dormant_desqueeze_18x_bypass_events=0 dormant_reclamp_only_one_bypass_events=0
  dormant_var_shutter_ecs_bypass_events=0 slot1_data_sector_writes=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r77b_ok=1 verify_us=984287
FX6_R77_WAVE63_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-63 非对称复位 / Wave-42 Reset 勘误与 `16/16 H0 == H3`（`r77c` — 第 150 次实跑）
```text
FX6_R77_CLEAN_UNMOUNT_WAVE63_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_emph_rec_antiflicker_preserves_hdmi8_desq_reclamp_remain_autorev_apsc_airplane_ok=1
  nwreset_preserves_wave63_apsc_airplane_ok=1
  initialize_restores_wave63_defaults_preserves_airplane_ok=1
  dormant_raw_gamut_bypass_events=0 dormant_24p_8bit_bypass_events=0
  dormant_desqueeze_18x_bypass_events=0 dormant_reclamp_only_one_bypass_events=0
  dormant_var_shutter_ecs_bypass_events=0 recorded_card_stream_altered=0
  clean_hdmi_emph_rec_baked_pixels=0 slot1_data_sector_writes=0 rf_tx_packets=0
  slot1_vault_ro_blocked_rc=-30 p12_write_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r77c_ok=1 verify_us=492539
```

---

## 3. `r77a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r77a` Alpha（`26.21 KiB` / `26,842 B`） | `r77a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r77a Big6 Alpha](r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png) | ![r77a Big6 Composited](r77_hdmi_raw_4264_recmedia_desqueeze_165x_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）Type-A HDMI 协议分析仪与外录机台架（验证 `[RAW Output]=On` 输出 `4264x2408` 16-bit 线性 RAW 锁定 `S-Log3` 并禁用 `Active` 防抖与 `HDMI Info. Display`、`[Rec. Media dur HDMI Output]=On` 时仍同步向 `Slot 1` 写入 XAVC/Proxy 而 `Off(HDMI Only)` 零写卡、`24.00p` 10-bit 强制重启边界，以及 `[Time Code Output]->[REC Control]` 触发对比 `ILME-FX6` `12G-SDI RAW` `4096x2160`/`3840x2160 "C"` 与 `4240x2392` HDMI RAW）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）变形镜头光学与 LCD/HDMI 监测台架（验证 `[De-Squeeze Display]` `1.3x`/`1.5x`/`1.6x(1.65x)`/`2.0x` 与缺失 `1.8x`、4 项硬件锁死 `MF`/`Wide`/`SteadyShot=Off`/`Face Priority in Multi Metering=Off`、机内录制码流零篡改、`Focus Magnifier`/`Bright Monitoring` 共存，以及全部 6 类 `ilc/2210` 自动旁路对比 `ILME-FX6` 仅 HDMI/VF 反挤压与零 SDI 反挤压）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）三灯/OSD 与快门/APS-C 台架（验证 `[REC Lamp]` `All On`/`Only Front Off`［后+顶 `REC` 键硬件联动］/`All Off` 且与 `[Silent Mode]` 解耦、`[Emphasized REC Display]` Clean-HDMI 零污染、`[Remain Shoot Display]`、Still `[Auto Review]`、Still 机械快门专用 `[Anti-flicker Shoot.]` `100/120Hz` 与休眠 `[Var. Shutter]` 对比 `FX6 ECS 23.99..8000Hz`，以及 `[APS-C S35 Shooting]` 4K/DCI 4K 锁死、Still `M: 5.1M` 裁切与抗 `[Camera Settings Reset]` 特性）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 77A (148th Live Run): Wave-63 4-Pillar [HDMI Output Settings] 8 Items / 4264x2408 16-bit RAW & Rec. Media dur HDMI Output, [De-Squeeze Display] 1.5x/1.6x(1.65x) vs Absent 1.8x & 4 Lockouts/6 Bypasses, [REC Lamp] 3-LED Coupled / Emphasized REC / Remain Shoot / Auto Review, [Anti-flicker Shoot.] vs Dormant Var. Shutter & [APS-C S35 Shooting] 4K Lockout + Reset Erratum Closure + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 77 --r77-mode hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r77a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round77-qemu/r77a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r77a-wave63-big6 \
  --export-png-dir <SCRATCH_ROOT>/round77-pngs

# Run 77B (149th Live Run): Fail-Closed Wave-63 Guard (Removed Color Gamut for RAW Output / 24.00p 8bit / De-Squeeze 1.8x / REC_LAMP_LIGHT_UP_ONLY_ONE / Var. Shutter / FX6 ECS EOPNOTSUPP, HDMI/De-Squeeze/AutoReview/Anti-flicker/APS-C 4K EBUSY, Slot-1 EROFS=-30, NULL EINVAL=-22, Live-Attach EPERM=-1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 77 --r77-mode wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard --sd-manifest-mode valid --lang en \
  --run-id r77b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round77-qemu/r77b

# Run 77C (150th Live Run — 50/50 Real-HW Rounds Milestone / 150/150 Live Runs / 100/100 PNGs <= 27,467 B): Clean Unmount Stock FX3 Restoration, Wave-63 Asymmetric Reset Split (Camera Settings Reset vs Reset Network Set. vs Initialize + Wave-42 APS-C S35 Reset Erratum Closure) + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 77 --r77-mode clean_unmount_wave63_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r77c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round77-qemu/r77c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_raw_gamut_bypass_events == 0`、`dormant_24p_8bit_bypass_events == 0`、`dormant_desqueeze_18x_bypass_events == 0`、`dormant_reclamp_only_one_bypass_events == 0`、`dormant_var_shutter_ecs_bypass_events == 0`、`recorded_card_stream_altered == 0`、`clean_hdmi_emph_rec_baked_pixels == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
