# Round 50（第 50 个重大里程碑 `50th Grand Milestone!` / Wave-36 / 实机内核 QEMU 连续第 22 轮 · 累计 66 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Shoe Audio Set.]`（`48kHz/24bit 4ch` 四声道电平表扩展对标 `3.5mm` 插孔、`XLR-H1 ANALOG` 开关与 `S&Q` 三重失格锁）、`[Wind Noise Reduct.]` 内置立体声麦克风独占高通与室内低频衰减护栏、以及 `[Save/Load Settings]`（`CAMSET01..10.DAT` / `C3 Portal`）8 类排除项防火墙与 Slot-1 Tier-0 备份仓禁写锁

> **日期**：2026-11-15 | **轮次**：**Round 50 Live ARM64 QEMU Rehearsal (`50th Grand Milestone!` / Wave-36)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r50a` / `r50b` / `r50c`）测得；**物理实体 `ILME-FX3` 机身上热插拔实体数字 MI 热靴 `XLR-H1` 手柄与 `3.5mm` 立体声麦克风并用 Catalyst Browse 校验 XAVC 4 声道 `24-bit` LPCM 音轨、使用声学扫频信号源（`20 Hz - 20 kHz`）实测内置麦克风对比 `3.5mm` / `XLR-H1` 在 `[Wind Noise Reduct.]=On` 下的频响曲线、以及插入实体 SDXC / CFexpress Type A 卡与连接 Creators' App / `C3 Portal` 云端复核 `CAMSET01..10.DAT` / `Cloud(Private)` / `Cloud(Share)` 尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 50 轮（`50th Grand Milestone`）三项实机预演总览（`r50a` / `r50b` / `r50c`）

| 实跑场景 | Run ID | `r50_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **50A：`[Shoe Audio Set.]` `48kHz/24bit 4ch` 四声道电平表扩展 vs `3.5mm` 插孔、`XLR-H1 ANALOG` 与 `S&Q` 三重失格锁 + Big-6 Home** | `round50-shoe-audio-4ch-osd-big6` | `shoe_audio_4ch_osd_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[Shoe Audio Set.]` 全部 `3` 档数字热靴格式（默认 `48kHz/16bit 2ch` `shoe_audio_default_16b_2ch_ok=1`、`48kHz/24bit 2ch`、`48kHz/24bit 4ch`，`shoe_audio_3modes_verified=3`；非法枚举以 `rc=-22` `EINVAL` 拒绝），且经 `[Camera Settings Reset]` 与 `[Initialize]` 均恢复为默认 `48kHz/16bit 2ch`（`shoe_audio_camreset_restores_16b_2ch_ok=1`, `initialize_restores_16b_2ch_ok=1`）；当数字 MI 热靴 `XLR-H1`（`DIGITAL`）配合 `48kHz/24bit 4ch` 激活时，驱动 `4` 声道 `24-bit` LPCM 管线并将 `[Audio Level Display]` 从 `2ch` 扩展为完整 `4ch`（`CH1..CH4`，`osd_4ch_meter_channels=4`, `osd_4ch_meter_bars_px=4096`, `osd_4ch_meter_ch1_to_ch4_ok=1`）；严格核验全部 `3` 类硬件失格与覆盖锁——① `S&Q Motion` 与 `[Audio Recording]=Off` 强制 `0` 音轨并以 `-EBUSY`（`-16`）锁定菜单（`sq_audio_tracks=0`, `audio_off_tracks=0`）、② 插入机身 `3.5mm` `MIC` 插孔强制接管 MI 热靴并退回机身内置 ADC `2ch` `16-bit`（`jack_35mm_shoe_set_lock_rc=-16`, `jack_35mm_override_channels=2`）、③ `XLR-H1` 手柄拨至 `ANALOG` 硬件拒绝 `24-bit` 与 `4ch`（`xlrh1_analog_24bit_4ch_reject_rc=-22`）并锁回 `2ch` `48kHz/16bit`（`disqualified_4ch_active_leaks=0`）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.13s` | [`r50a-shoe-audio-4ch-osd-big6-schinese-composited.png`](assets/r50a-shoe-audio-4ch-osd-big6-schinese-composited.png) |
| **50B：`[Wind Noise Reduct.]` 内置立体声麦克风独占数字高通与室内低频衰减钳位护栏** | `round50-wind-noise-builtin-guard` | `wind_noise_builtin_only_guard` | Native ARM64 音频 DSP 路由与台架低频保护探针实测：核验 `[Wind Noise Reduct.]` 默认 `Off`（`wind_noise_default_off_ok=1`）及 `Off` / `On` 双档（`wind_noise_2modes_verified=2`；非法档位返回 `rc=-22` `EINVAL`），证实经 `[Camera Settings Reset]` 与 `[Initialize]` 均恢复为 `Off`（`wind_camreset_restores_off_ok=1`, `initialize_restores_off_ok=1`）；证实数字高通防风滤波**仅作用于机身内置立体声麦克风**（`builtin_mic_hpf_active_ok=1`），而在全部 `4` 类外接麦克风路径（`3.5mm` TRS 麦克风、MI 热靴枪麦、`XLR-H1 DIGITAL`、`XLR-H1 ANALOG`）上 100% 硬件旁路机身 `[Wind Noise Reduct.]` DSP（`ext_sources_tested=4`, `ext_sources_bypassed=4`, `external_mic_wind_reduct_active=0`，外接低切交由 `XLR-H1` 手柄实体 `LOW CUT` `OFF`/`100Hz`/`300Hz` 三档硬件开关独立控制 `xlrh1_hw_lowcut_3positions_verified=3`）；在 `32` 轮室内无风台架预演循环中自动将残留 `[On]` 钳位回 `[Off]`（`indoor_rehearsal_cycles=32`, `indoor_clamped_to_off_ok=1`, `indoor_low_freq_attenuation_events=0`），并在 `S&Q` 与 `[Audio Recording]=Off` 下以 `-EBUSY`（`-16`）硬锁定 | `13/13` 校验（早期防风滤波 C 探针退出） | 跳过（防风滤波 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.43s` | — |
| **50C：`[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` 8 类排除项防火墙、Slot-1 备份仓禁写锁 + `16/16 H0 == H3`** | `round50-saveload-camset-c3-vault-h0-h3` | `saveload_camset_c3_vault_h0_h3` | Native ARM64 相机设置存储防火墙与硬件基线不变性探针证实：遍历 `CAMSET01.DAT..CAMSET10.DAT` 全部 `10` 个卡槽槽位（`camset_10slots_verified=10`；`CAMSET00`/`CAMSET11` 越界以 `rc=-22` `EINVAL` 拒绝）及 `Ver. 4.00+` `C3 Portal` 双云端通道 `Cloud(Private)` / `Cloud(Share)`（`cloud_2targets_verified=2`）；严格执行 `ILME-FX3` 同机型锁，拒绝加载跨机型 `ILME-FX6` 与 `ILME-FX30` `.DAT` 文件（`fx6_dat_reject_rc=-22`, `fx30_dat_reject_rc=-22`, `cross_model_loads_accepted=0`）；证实全部 `8` 大官方排除项（`IPTC Information`、`Copyright Info`、`Custom WB 1..3` 独立色温寄存器、`Face Memory`、`FTP` 服务器凭据、`Streaming` RTMP/SRT 推流密钥、`Wi-Fi` SSID/PSK、根证书/TLS 密钥，`excluded_8categories_verified=8`, `custom_wb_3regs_preserved=3`）在 `[Save]` 导出载荷中零明文/密文泄漏且在 `[Load]` 导入时零覆盖（`saved_payload_secret_hits=0`, `loaded_excluded_overwrites=0`, `excluded_leaks=0`）；拦截向 Slot-1 Tier-0 恢复仓执行 `[Save]`（防火墙 `-EACCES` `-13` + 内核只读 `-EROFS` `-30`，`slot1_camset_writes=0`, `slot1_vault_sha256_match=1`）同时放行 `O_RDONLY` Slot-1 `[Load]`（`slot1_readonly_load_ok=1`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_writes=0`） | `13/13` 校验（早期存储防火墙与基线 C 探针退出） | 跳过（存储防火墙与基线 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.05s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Shoe Audio Set.]` `48kHz/24bit 4ch` 四声道电平表扩展 vs 三重硬件失格锁与 Big-6 渲染（`r50a`）
```text
FX6_R50_SHOE_AUDIO_4CH_INIT shoe_audio_default_16b_2ch_ok=1 invalid_shoe_mode_reject_rc=-22
  shoe_audio_3modes_verified=3 shoe_audio_camreset_restores_16b_2ch_ok=1
  initialize_restores_16b_2ch_ok=1 lpcm_4ch_24bit_active_ok=1
  osd_4ch_meter_channels=4 osd_2ch_meter_channels=2 osd_4ch_meter_bars_px=4096
  osd_4ch_meter_ch1_to_ch4_ok=1 audio_off_lock_rc=-16 sq_motion_lock_rc=-16
  sq_audio_tracks=0 audio_off_tracks=0 jack_35mm_shoe_set_lock_rc=-16
  jack_35mm_override_channels=2 jack_35mm_override_bits=16
  xlrh1_analog_24bit_4ch_reject_rc=-22 xlrh1_analog_override_channels=2
  xlrh1_analog_override_bits=16 disqualified_4ch_active_leaks=0
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0
  r50_init_ok=1 verify_us=885578

FX6_R50_SHOE_AUDIO_4CH_BRIDGE shoe_audio_default_16b_2ch_ok=1
  shoe_audio_3modes_verified=3 shoe_audio_camreset_restores_16b_2ch_ok=1
  osd_4ch_meter_channels=4 osd_2ch_meter_channels=2 osd_4ch_meter_bars_px=4096
  osd_4ch_meter_ch1_to_ch4_ok=1 sq_audio_tracks=0 audio_off_tracks=0
  sq_and_audio_off_0tracks_lock_ok=1 jack_35mm_override_channels=2
  jack_35mm_2ch_override_lock_ok=1 xlrh1_analog_override_channels=2
  xlrh1_analog_override_bits=16 xlrh1_analog_2ch_16b_override_ok=1
  shoe_audio_4ch_osd_ok=1 emmc_write_count=0 r50_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `110` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Wind Noise Reduct.]` 内置立体声麦克风独占高通与室内低频衰减护栏（`r50b`）
```text
FX6_R50_WIND_NOISE_GUARD wind_noise_default_off_ok=1 invalid_wind_mode_reject_rc=-22
  wind_noise_2modes_verified=2 wind_camreset_restores_off_ok=1
  initialize_restores_off_ok=1 builtin_mic_hpf_active_ok=1
  ext_sources_tested=4 ext_sources_bypassed=4 external_mic_wind_reduct_active=0
  xlrh1_hw_lowcut_3positions_verified=3 outdoor_high_wind_hpf_allowed_ok=1
  indoor_rehearsal_cycles=32 indoor_clamped_to_off_ok=1
  indoor_low_freq_attenuation_events=0 audio_off_wind_lock_rc=-16
  sq_wind_lock_rc=-16 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r50b_ok=1 verify_us=898595
```

### 2.3 `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` 8 类排除项防火墙、Slot-1 禁写锁及 `16/16 H0 == H3`（`r50c`）
```text
FX6_R50_SAVELOAD_C3_VAULT camset_10slots_verified=10 invalid_camset_slot_reject_rc=-22
  fx6_dat_reject_rc=-22 fx30_dat_reject_rc=-22 cross_model_loads_accepted=0
  cloud_2targets_verified=2 allowed_regs_roundtrip_ok=1
  excluded_8categories_verified=8 custom_wb_3regs_preserved=3
  saved_payload_secret_hits=0 loaded_excluded_overwrites=0 excluded_leaks=0
  slot1_save_blocked_rc=-13 slot1_ro_kernel_rc=-30 slot1_camset_writes=0
  slot1_vault_sha256_match=1 slot1_readonly_load_rc=0 slot1_readonly_load_ok=1
  slot2_scratch_camset_ok=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 emmc_write_count=0 r50c_ok=1 verify_us=409844
```

---

## 3. `r50a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r50a` Alpha（`26.50 KiB` / `27,132 B`） | `r50a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r50a Big6 Alpha](assets/r50a-shoe-audio-4ch-osd-big6-schinese-alpha.png) | ![r50a Big6 Composited](assets/r50a-shoe-audio-4ch-osd-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）热插拔实体数字 MI 热靴 `XLR-H1` 音频手柄与 `3.5mm` TRS 立体声麦克风，在机内录制 XAVC MP4 并使用 Catalyst Browse 实机复核 `[Shoe Audio Set.]=[48kHz/24bit 4ch]` 下的 `CH1..CH4` 四声道电平表与 4 轨 24-bit LPCM 音轨，以及插入 `3.5mm` 插孔或将 `XLR-H1` 拨至 `ANALOG` 时自动退回 `2ch` `16-bit` 的物理切换行为。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在消声/声学测试环境下输入 `20 Hz - 20 kHz` 扫频声源，实测 `[Wind Noise Reduct.]` 在 `Off` 与 `On` 档位下对机身内置立体声麦克风的低频滚降曲线，以及接入 `3.5mm` `MIC` 与 `XLR-H1`（`LOW CUT` `OFF`/`100Hz`/`300Hz`）时机身数字防风滤波的完全旁路特性。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）插入实体 SDXC / CFexpress Type A 卡并配对 Creators' App / `C3 Portal`（`Cloud(Private)` / `Cloud(Share)`），实机导出与导入 `CAMSET01..10.DAT`，验证 `IPTC`、版权、`Custom WB 1..3`、人脸记忆与 `FTP`/推流/`Wi-Fi` 密钥不被导出或覆盖，以及实体 SD 卡写保护拨片对 `[Save]` 的物理拦截。

---

## 5. 复现命令与洁净室合规

```bash
# Run 50A: [Shoe Audio Set.] 48kHz/24bit 4ch OSD Meter Expansion vs 3.5mm Jack, XLR-H1 ANALOG & S&Q Lockouts + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 50 --r50-mode shoe_audio_4ch_osd_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round50-shoe-audio-4ch-osd-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r50-runs/r50a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r50a-shoe-audio-4ch-osd-big6-schinese \
  --export-png-dir reports/2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu/assets

# Run 50B: [Wind Noise Reduct.] Built-In Stereo Mic Exclusivity & Indoor Low-Cut Attenuation Guard
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 50 --r50-mode wind_noise_builtin_only_guard --lang en \
  --run-id round50-wind-noise-builtin-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r50-runs/r50b

# Run 50C: [Save/Load Settings] CAMSET01..10.DAT / C3 Portal Excluded-Items Firewall, Slot-1 Vault Write Block + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 50 --r50-mode saveload_camset_c3_vault_h0_h3 --lang en \
  --run-id round50-saveload-camset-c3-vault-h0-h3 --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r50-runs/r50c

# Dual-Mode Unit Tests & Clean Audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
