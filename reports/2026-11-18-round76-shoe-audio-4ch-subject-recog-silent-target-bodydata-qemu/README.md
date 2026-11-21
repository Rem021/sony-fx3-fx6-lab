# Round 76（Wave-62 · **`49/49` 实机预演轮次 `R28..R76` · 第 `145..147` 次实跑 -> `147/147` 总实跑 · `98/98` 张 Big-6 PNG `<= 27,467 B`**）：FX3 7.02 原厂内核真机准备预演 — `[Shoe Audio Set.]` 4ch 24-bit / `XLR-H1` 优先抢占与 `[Audio Out Timing]`、`[Face/Eye Subject]` 仅 `Human`/`Animal` 破谣言与 8 槽 `[Face Memory]`、`[Silent Mode Settings]` 2 项 `[Target Function Settings]` 与休眠 `[Shutter When Pwr OFF]`，以及 `[Version]` 只读与 `BODYDATA.DAT` `Slot 1` `EROFS`/`EPERM` `NO-GO` 防火墙

## 结论先行

- **实测结果（`实测事实`）**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 76** 三路独立 QEMU 实机预演（`r76a` / `r76b` / `r76c`，达成 **`49/49` 实机预演轮次 `R28..R76` · `147/147` 次独立实跑 · `98/98` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`bodydata_slot1_write_count == 0`、`slot1_data_sector_writes == 0`、`dormant_audio_level_display_bypass_events == 0`、`dormant_fx6_32bit_float_bypass_events == 0`、`dormant_bird_subject_bypass_events == 0`、`dormant_insect_car_airplane_bypass_events == 0`、`dormant_shutter_when_pwr_off_bypass_events == 0`、`target_function_3rd_item_bypass_events == 0`、`hdmi_eye_frame_baked_pixels == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r76c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r76a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`，`sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界（`推断`）**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 62 四大支柱门禁、路径纠偏与休眠符号（Ver. 2.00..7.02 已移除独立开关的 `[Audio Level Display]` `_f 0x7a36`、误归 `Setup` 的 `[Audio Out Timing]`、FX6 休眠 `4ch/48kHz/32bit float` `ns1 0x3215`、**修正 Wave 42 笔误确认 FX3 `ilc/2210` 仅开放 `Human` + Still-Only `Animal` 而零 `Bird`/`Insect`/`Car/Train`/`Airplane`**、`[Target Function Settings]` 第 3 项以及休眠 `[Shutter When Pwr OFF]` `_f 0x709f` / `[Anti-dust Function]` `_f 0x7495`）的 fail-closed `-95 EOPNOTSUPP` / `-16 EBUSY` / `-22 EINVAL` / `-28 ENOSPC` / `-30 EROFS` / `-11 EAGAIN` / `-1 EPERM` 拦截：
  1. `[Shoe Audio Set.]`（`48kHz/16bit 2ch` 默认 / `24bit 2ch` / `24bit 4ch` 经 `XLR-H1` `DIGITAL` `HANDLE AUDIO=ON` 覆盖全部 6 种主录编码；`Proxy` 强制 `MPEG-4 AAC-LC 2ch 128 kbps` 且 `>=100p/120p` 禁用；`3.5mm MIC` 插入以 `-16 EBUSY` 抢占 MI 靴；`ANALOG` 限 `16bit 2ch`；`HANDLE AUDIO=OFF` 回退机内麦；`[Wind Noise Reduct.]` 仅限机内麦；`[Audio Out Timing]` `Live/Lip Sync` 位于 `Shooting -> [Audio Recording]` 而非 `Setup`；`[Audio Rec Level]` `0..31` 默认 `26`、`adj_audio_rec_level_defult` 拼写细节与常开内置 Limiter）对比 `ILME-FX6 Ver. 6.01` 物理 `CH1..CH4` 旋钮、6 档 `Limiter Mode` 与休眠 `32bit float`；
  2. `[Face/Eye Subject]` **仅 `Human` + `Animal`（零 `Bird` / `Insect` / `Car/Train` / `Airplane`）**、`Animal Eye AF` 仅 Still 有效（Movie 报错 `TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` -> `-95 EOPNOTSUPP`）、`[Right/Left Eye Select]`、`[Face/Eye Frame Disp.]` 默认 `Off` 且 Clean HDMI/RAW `0 px`、**8 槽抗 `[Camera Settings Reset]` 且排除 `CAMSET*.DAT` 的 `[Face Memory]`**（第 9 槽 `-28 ENOSPC`）对比 `FX6` 仅 `Human` 与临时会话 `Saved Tracking Face`；
  3. `[Silent Mode Settings]` 二级菜单（Still 独占、`5` 项硬锁定 Flash/Long Exp NR/e-Front Curtain Shut./BULB/Anti-flicker Shoot. + `Audio signals` 静音而保留 `[AF Illuminator]`）+ **仅 2 项 `[Target Function Settings]`**（`[Aperture Drive in AF]` & `[Auto Pixel Mapping]`，`Off` 默认阻断关机快门与 `cnflasha` 写入）+ 零 `[Shutter When Pwr OFF]` 对比无机械快门 `ILME-FX6` `Auto Pixel Restore`；
  4. `Setup -> [Setup Option] -> [Version]` 只读弹窗（`Body Ver. 7.02`/Lens/Mount Adaptor，Zero-RF `Airplane Mode=On` 静音 `_g 0x6516` 更新徽标）与 **`BODYDATA.DAT` `Slot 1` 根目录门禁 + `NP-FZ100 >= 51%` + `<=2.02` 必经 `2.04/2.05` 跳板 + `Slot 1` `-30 EROFS` 与物理刷机/跨机型刷写 `-1 EPERM` `NO-GO` 红线**对比 `FX6` `Slot B` + `AC Adaptor`；
  **物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台硬件实测（`XLR-H1` 4ch 声学录波、E 卡口 `Human/Animal` 对焦实拍、静音光圈与 `Slot 1` 物理卡槽升级门禁）尚未上电执行，详见 §4。**

> **日期**：2026-11-18 | **轮次**：**Round 76 (`49/49` Real-HW Rounds · Wave-62 · `145th..147th` Live Runs -> `147/147` Total Live Runs, `98/98` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-62 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/README.md`](../2026-11-17-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 76 轮（Wave-62 · `49/49` 实机轮次 / `145th..147th` -> `147/147` 次实跑 / `98/98` PNG）三项实机预演总览（`r76a` / `r76b` / `r76c`）

| 实跑场景 | Run ID | `r76_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **76A（第 145 次实跑）：Wave-62 四大支柱 — `[Shoe Audio Set.]` 4ch 24-bit / `XLR-H1` 优先抢占 / `[Audio Out Timing]`、`[Face/Eye Subject]` 仅 `Human`+`Animal`（零 `Bird`）& 8 槽 `[Face Memory]`、`[Silent Mode Settings]` 2 项 `[Target Function Settings]` & 休眠 `[Shutter When Pwr OFF]`、`[Version]` 只读 & `BODYDATA.DAT` `Slot 1` `NO-GO` + Big-6 Home** | `r76a` | `shoe_audio_4ch_subject_recog_silent_version_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`[Shoe Audio Set.]`** `48kHz/16bit 2ch`（默认）/ `24bit 2ch` / `24bit 4ch`（`XLR-H1 DIGITAL HANDLE AUDIO=ON` 覆盖全 6 主录编码，`Proxy` 锁定 `AAC-LC 2ch 128 kbps`）、`3.5mm MIC` 抢占 MI 靴（`-16 EBUSY`）、`[Audio Out Timing]` 位于 `Shooting -> [Audio Recording]`（`Setup` 路径 `-95`）、已移除 `[Audio Level Display]`（`-95`）、`[Audio Rec Level]` `0..31`（def `26`）与常开 Limiter；(2) 核验 **`[Face/Eye Subject]`** 仅 `Human`+`Animal`（修正 Wave 42 误记：`Bird` `-95`）、`Animal Eye AF` Still-only（Movie `-95`）、`[Right/Left Eye Select]` & Clean-HDMI `0 px`、`8` 槽抗 Reset `[Face Memory]`（第 9 槽 `-28 ENOSPC`）；(3) 核验 **`[Silent Mode Settings]`** Still-only 5 项硬锁定 + 仅 2 项 **`[Target Function Settings]`**（第 3 项 `-95`）+ 休眠 `[Shutter When Pwr OFF]`（`-95`）与 `cnflasha_writes=0`；(4) 核验 **`[Version]`** 只读与 `Airplane Mode=On` 徽标静默、`BODYDATA.DAT` `Slot 1` `-30 EROFS` 与物理刷机/跨机型 `-1 EPERM` `NO-GO` 防火墙，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r76_init_ok=1`, `r76_bridge_ok=1`, `verify_us=979957`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.12s` | [`r76_shoe_audio_4ch_subject_recog_human_animal_preview.png`](r76_shoe_audio_4ch_subject_recog_human_animal_preview.png) / [`r76_silent_target_2items_version_bodydata_nogo_preview.png`](r76_silent_target_2items_version_bodydata_nogo_preview.png) |
| **76B（第 146 次实跑）：Fail-Closed Wave-62 防火墙 — 移除 `[Audio Level Display]` / `Setup [Audio Out Timing]` / FX6 `32bit float`、`3.5mm` 抢占 / `ANALOG` 降级 / `S&Q` / `Proxy 120p`、休眠 `Bird`/`Insect`/`Car`/`Airplane` / Movie `Animal Eye AF` / `CAMSET` `Face Memory`、`Shutter When Pwr OFF` / 第 3 目标项 / `FX6` 机械快门、`BODYDATA.DAT` `Slot 1` `EROFS=30` & 刷机 `EPERM=1` 全面阻断** | `r76b` | `wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截已移除 `[Audio Level Display]` / `Setup` 路径 `[Audio Out Timing]` / FX6 `32bit float` 4ch / 关闭 Limiter / `Proxy 4ch`（`-95 EOPNOTSUPP`）、Level `32` 越界（`-22 EINVAL`）、`3.5mm` 抢占 / `HANDLE AUDIO=OFF` / `ANALOG` 4ch / 外接麦风噪 / `S&Q` / `Proxy 120p`（`-16 EBUSY`）；(2) 拦截 `Bird` / `Animal-Bird` / `Insect` / `Car-Train` / `Airplane` / Movie `Animal Eye AF` / `CAMSET*.DAT` 导出 `Face Memory` / FX6 `Animal` & `Face Memory`（`-95 EOPNOTSUPP`）、`Animal + Regist. Faces Priority`（`-16 EBUSY`）；(3) 拦截休眠 `[Shutter When Pwr OFF]` / `[Anti-dust Function]` / `[Target Function Settings]` 第 3 项 / FX6 机械快门（`-95 EOPNOTSUPP`）、Silent 模式下 Movie/Flash/BULB/Audio Signals 解静音（`-16 EBUSY`）；(4) 拦截 `Slot 1` `BODYDATA.DAT` / `P12` / `P2` / `cnflasha` 写入（`-30 EROFS`）、`Slot 2` `BODYDATA.DAT`（`-22`）、电量 `<51%`（`-11 EAGAIN`）、`<=2.02` 缺 `2.04/2.05` 跳板（`-22`）、真机刷机与 FX6<->FX3 跨机型刷写（`-1 EPERM`，`bodydata_slot1_write_count=0`, `slot1_data_sector_writes=0`, `slot1_vault_sha256_match=1`, `emmc_write_count=0`, `cnflasha_writes=0`, `r76b_ok=1`, `verify_us=1034114`, `FX6_R76_WAVE62_GUARD_RC=0`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `8.92s` | — |
| **76C（第 147 次实跑 · `49/49` 实机轮次 closure）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-62 三态非对称持久化验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r76c` | `clean_unmount_wave62_reset_h0_h3_big6` | Native ARM64 Wave-62 联合预演（**`49/49` 实机轮次 · 第 `147/147` 次独立实跑 · `98/98` 张 PNG**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证三态非对称复位层级：**`[Camera Settings Reset]` 复位 `[Audio Rec Level]=26`、`[Shoe Audio Set.]=48kHz/16bit 2ch`、`[Audio Out Timing]=Live`、`[Face/Eye Subject]=Human`、`[Face/Eye Frame Disp.]=Off`、`[Silent Mode]=Off`、`[Aperture Drive in AF]=Standard` 与 `[Auto Pixel Mapping]=Off`，同时完整保留全部 `8` 槽 `[Face Memory]` 与 `[Airplane Mode]=On`**（`camreset_resets_audio_silent_subject_preserves_8facemem_airplane_ok=1`）；**`[Reset Network Set.]` 完整保留全部 `8` 槽 `[Face Memory]` 与 `[Airplane Mode]=On`**（`nwreset_preserves_8facemem_airplane_ok=1`）；**`[Initialize]` 清除全部 `8` 槽 `[Face Memory]` 并恢复全部默认值，同时依然保持 `[Airplane Mode]=On`**（`initialize_clears_8facemem_preserves_airplane_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `bodydata_slot1_write_count=0`, `slot1_data_sector_writes=0`, `rf_tx_packets=0`, `passive_tx_bytes_emitted=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=59`, `verify_us=467312`, `emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `79.58s` | 同 `76A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-62 四大支柱初始化与 Stage-B 四路桥接（`r76a` — 第 145 次实跑）
```text
FX6_R76_WAVE62_INIT fx3_wave62_nodes_ok=1 uxc_tokens_ok=1 shoe_audio_4ch_out_timing_ok=1
  subject_recog_human_animal_facemem_ok=1 silent_target_2items_no_pwrshutter_ok=1 version_slot1_bodydata_nogo_ok=1
  audio_35mm_preempt_rc=-16 audio_level_disp_removed_rc=-95 audio_timing_setup_err_rc=-95
  facemem_9th_slot_rc=-28 subj_bird_dormant_rc=-95 animal_eye_movie_rc=-95
  shutter_pwr_off_dormant_rc=-95 target_3rd_item_rc=-95 silent_flash_lock_rc=-16
  bodydata_slot1_erofs_rc=-30 bodydata_exec_nogo_rc=-1 cross_model_flash_rc=-1
  p2_write_blocked_rc=-30 p2_sha256_match=1 p12_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_audio_level_display_bypass_events=0 dormant_fx6_32bit_float_bypass_events=0
  dormant_bird_subject_bypass_events=0 dormant_insect_car_airplane_bypass_events=0
  dormant_shutter_when_pwr_off_bypass_events=0 target_function_3rd_item_bypass_events=0
  hdmi_eye_frame_baked_pixels=0 bodydata_slot1_write_count=0 slot1_data_sector_writes=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r76_init_ok=1 verify_us=979957

FX6_STAGE_B_R76_BRIDGE round=76 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1
  p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED
  font_bank=23 str_bank=19
  shoe_audio_4ch_24bit_out_timing_shooting_no_level_disp=1
  subject_recog_human_animal_only_zero_bird_movie_lockout_8slot_facemem=1
  silent_mode_5locks_2target_items_no_pwr_off_shutter=1
  version_readonly_bodydata_slot1_nogo_firewall=1
  milestone_49th_realhw_147th_live_98_pngs=1
  dormant_audio_level_display_bypass_events=0 dormant_fx6_32bit_float_bypass_events=0
  proxy_4ch_leak_events=0 sq_shoe_audio_leak_events=0 external_mic_wind_reduct_leak_events=0
  dormant_bird_subject_bypass_events=0 dormant_insect_car_airplane_bypass_events=0
  movie_animal_eye_af_bypass_events=0 hdmi_eye_frame_baked_pixels=0
  dormant_shutter_when_pwr_off_bypass_events=0 target_function_3rd_item_bypass_events=0
  silent_mode_flash_bulb_nr_efcs_flicker_leak_events=0 silent_mode_audio_signal_leak_events=0
  bodydata_slot1_flash_attempts_blocked=0 cross_model_flash_attempts_blocked=0
  slot1_write_count=0 slot1_data_sector_writes=0 rf_tx_packets=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 cnflasha_writes=0 emmc_write_count=0

FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE shoe_audio_4ch_24bit_xlrh1_ok=1
  audio_out_timing_shooting_no_level_disp_ok=1 audio_rec_level_26_limiter_on_ok=1
  shoe_audio_4ch_out_timing_ok=1 dormant_audio_level_display_bypass_events=0
  dormant_fx6_32bit_float_bypass_events=0 proxy_4ch_leak_events=0 sq_shoe_audio_leak_events=0
  external_mic_wind_reduct_leak_events=0 cnflasha_writes=0 emmc_write_count=0 r76_bridge_ok=1

FX6_R76_SUBJECT_RECOG_HUMAN_ANIMAL_FACEMEM_BRIDGE face_eye_human_animal_only_zero_bird_ok=1
  animal_eye_still_only_8slot_facemem_ok=1 subject_recog_human_animal_facemem_ok=1
  dormant_bird_subject_bypass_events=0 dormant_insect_car_airplane_bypass_events=0
  movie_animal_eye_af_bypass_events=0 hdmi_eye_frame_baked_pixels=0 cnflasha_writes=0 emmc_write_count=0

FX6_R76_SILENT_TARGET_2ITEMS_NO_PWRSHUTTER_BRIDGE silent_mode_5lockouts_2target_items_ok=1
  dormant_shutter_when_pwr_off_zero_cnflasha_ok=1 silent_target_2items_no_pwrshutter_ok=1
  dormant_shutter_when_pwr_off_bypass_events=0 target_function_3rd_item_bypass_events=0
  silent_mode_flash_bulb_nr_efcs_flicker_leak_events=0 silent_mode_audio_signal_leak_events=0
  cnflasha_writes=0 emmc_write_count=0

FX6_R76_VERSION_SLOT1_BODYDATA_NOGO_BRIDGE version_readonly_airplane_badge_silenced_ok=1
  bodydata_slot1_nogo_firewall_armed_ok=1 version_slot1_bodydata_nogo_ok=1
  bodydata_slot1_flash_attempts_blocked=0 cross_model_flash_attempts_blocked=0
  slot1_write_count=0 slot1_data_sector_writes=0 rf_tx_packets=0 passive_tx_bytes_emitted=0
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `61` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`151` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-62 防火墙拦截明细（`r76b` — 第 146 次实跑）
```text
FX6_R76_WAVE62_GUARD audio_level_disp_removed_rc=-95 audio_32bit_float_rc=-95
  audio_timing_setup_err_rc=-95 audio_limiter_off_rc=-95 audio_level_32_oob_rc=-22
  audio_35mm_preempt_rc=-16 audio_xlr_handle_off_rc=-16 audio_xlr_analog_cap_rc=-16
  audio_wind_ext_mic_rc=-16 audio_sq_lock_rc=-16 audio_proxy_4ch_rc=-95 audio_proxy_120p_rc=-16
  subj_bird_rc=-95 subj_animal_bird_rc=-95 subj_insect_rc=-95 subj_car_train_rc=-95 subj_airplane_rc=-95
  animal_eye_movie_rc=-95 animal_regist_prio_rc=-16 facemem_camset_excl_rc=-95
  fx6_animal_rc=-95 fx6_facemem_rc=-95
  shutter_pwr_off_rc=-95 antidust_dormant_rc=-95 target_3rd_item_rc=-95
  silent_movie_lock_rc=-16 silent_flash_lock_rc=-16 silent_bulb_lock_rc=-16
  silent_signals_unmute_rc=-16 fx6_mech_shutter_rc=-95
  bodydata_slot1_write_erofs_rc=-30 bodydata_slot2_reject_rc=-22 bodydata_low_batt_rc=-11
  bodydata_202_no_step_rc=-22 bodydata_exec_eperm_rc=-1 cross_model_flash_eperm_rc=-1
  slot1_wave62_erofs_rc=-30 slot1_bodydata_ro_blocked_rc=-30 p12_write_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_audio_level_display_bypass_events=0 dormant_fx6_32bit_float_bypass_events=0
  dormant_bird_subject_bypass_events=0 dormant_insect_car_airplane_bypass_events=0
  dormant_shutter_when_pwr_off_bypass_events=0 target_function_3rd_item_bypass_events=0
  hdmi_eye_frame_baked_pixels=0 bodydata_slot1_write_count=0 slot1_data_sector_writes=0
  rf_tx_packets=0 passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r76b_ok=1 verify_us=1034114
FX6_R76_WAVE62_GUARD_RC=0
```

### 2.3 洁净卸载还原原厂、Wave-62 三态复位与 `16/16 H0 == H3`（`r76c` — 第 147 次实跑）
```text
FX6_R76_CLEAN_UNMOUNT_WAVE62_H0_H3 stock_unmount_restored_ok=1
  camreset_resets_audio_silent_subject_preserves_8facemem_airplane_ok=1
  nwreset_preserves_8facemem_airplane_ok=1
  initialize_clears_8facemem_preserves_airplane_ok=1
  dormant_audio_level_display_bypass_events=0 dormant_fx6_32bit_float_bypass_events=0
  dormant_bird_subject_bypass_events=0 dormant_insect_car_airplane_bypass_events=0
  dormant_shutter_when_pwr_off_bypass_events=0 target_function_3rd_item_bypass_events=0
  hdmi_eye_frame_baked_pixels=0 bodydata_slot1_write_count=0 slot1_data_sector_writes=0
  rf_tx_packets=0 slot1_vault_ro_blocked_rc=-30 slot1_bodydata_ro_blocked_rc=-30
  p12_write_blocked_rc=-30 slot1_vault_sha256_match=1 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r76c_ok=1 verify_us=467312
```

---

## 3. `r76a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r76a` Alpha（`26.21 KiB` / `26,842 B`） | `r76a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r76a Big6 Alpha](r76_silent_target_2items_version_bodydata_nogo_preview.png) | ![r76a Big6 Composited](r76_shoe_audio_4ch_subject_recog_human_animal_preview.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 `ILME-FX3`（`Ver. 7.02`）+ `XLR-H1` MI 靴与 `3.5mm` `MIC` 声学台架（验证全 6 种主录编码下 `48kHz/24bit 4ch` LPCM 录音、`Proxy` `MPEG-4 AAC-LC 2ch 128 kbps` 与 `>=100p/120p` 禁用、`3.5mm` 插入抢占 MI 靴、`HANDLE AUDIO=OFF` 回退机内麦、`ANALOG` 降级 `16bit 2ch`、`[Wind Noise Reduct.]` 机内麦独占，以及 `Shooting -> [Audio Recording] -> [Audio Out Timing]` `Live` vs `Lip Sync` 延迟对比 `FX6` `CH1..CH4` 旋钮与 6 档 `Limiter Mode`）。
2. 物理 `ILME-FX3`（`Ver. 7.02`）光学 AF 与 HDMI 分析仪台架（验证 `[Face/Eye Subject]` 仅 `Human`+`Animal` 而零 `Bird`/`Insect`/`Car/Train`/`Airplane`、`Animal Eye AF` 仅 Still 有效、8 槽 `[Face Memory]` 抗 `[Camera Settings Reset]` 且排除 `CAMSET*.DAT`、Still 独占 `[Silent Mode Settings]` 5 项硬锁定 + 仅 2 项 `[Target Function Settings]`，以及零 `[Shutter When Pwr OFF]` 对比无机械快门 `FX6` `Auto Pixel Restore`）。
3. 物理 `ILME-FX3`（`Ver. 7.02`）`[Version]` UI 与 `Slot 1` SD 卡槽门禁台架（验证只读机身/镜头/手柄版本弹窗、`Airplane Mode=On` 隐藏更新徽标，以及 `BODYDATA.DAT` `Slot 1` 根目录、`NP-FZ100 >= 51%` 与 `Ver. 2.04/2.05` 跳板门槛对比 `FX6` `Slot B` + `AC Adaptor` —— **物理真机 eMMC/Flash 刷写与跨机型烧录永久处于 `NO-GO / BLOCKED` 阻断状态**）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 76A (145th Live Run): Wave-62 4-Pillar [Shoe Audio Set.] 4ch 24-bit / XLR-H1 / Audio Out Timing (Shooting), [Face/Eye Subject] Human+Animal-Only (Zero Bird) & 8-Slot Face Memory, [Silent Mode Settings] 5-Lockout + 2-Item Target Function & Zero Shutter When Pwr OFF, [Version] Read-Only & BODYDATA.DAT Slot-1 NO-GO Firewall + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 76 --r76-mode shoe_audio_4ch_subject_recog_silent_version_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r76a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round76-qemu/r76a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r76a-wave62-big6 \
  --export-png-dir <SCRATCH_ROOT>/round76-pngs

# Run 76B (146th Live Run): Fail-Closed Wave-62 Guard (Removed Audio Level Display / Setup Audio Out Timing / FX6 32bit-float / Bird-Insect-Car-Airplane / Movie Animal Eye AF / Shutter When Pwr OFF / Target 3rd Item EOPNOTSUPP, 3.5mm Preemption & Silent 5-Lockout EBUSY, BODYDATA.DAT Slot-1 EROFS=30 & Update/Cross-Model Flash EPERM=1)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 76 --r76-mode wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard --sd-manifest-mode valid --lang en \
  --run-id r76b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round76-qemu/r76b

# Run 76C (147th Live Run — 49/49 Real-HW Rounds / 147/147 Live Runs / 98/98 PNGs): Clean Unmount Stock FX3 Restoration, Wave-62 3-Tier Asymmetric Reset Split (Camera Settings Reset / Reset Network Set. / Initialize) + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 76 --r76-mode clean_unmount_wave62_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r76c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round76-qemu/r76c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`bodydata_slot1_write_count == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_audio_level_display_bypass_events == 0`、`dormant_fx6_32bit_float_bypass_events == 0`、`dormant_bird_subject_bypass_events == 0`、`dormant_insect_car_airplane_bypass_events == 0`、`dormant_shutter_when_pwr_off_bypass_events == 0`、`target_function_3rd_item_bypass_events == 0`、`hdmi_eye_frame_baked_pixels == 0`、`rf_tx_packets == 0`、`passive_tx_bytes_emitted == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
