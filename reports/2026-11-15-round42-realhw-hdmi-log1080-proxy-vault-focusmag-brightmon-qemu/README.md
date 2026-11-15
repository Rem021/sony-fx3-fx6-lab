# Round 42：FX3 7.02 原厂内核真机准备预演 — `[HDMI Output Settings]`（`[Log Shooting]`/`PPLUT1..4` `1080p` 降格 vs `Off(HDMI Only)` `4K 10-bit` 与机背关屏）、`Px` Proxy 原子保险库（`119.88p/100p` & `S&Q >=120fps` 截断）与 `[Focus Magnifier]` × `[Bright Monitoring]`

> **日期**：2026-11-15 | **轮次**：**Round 42 Live ARM64 QEMU Rehearsal** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r42a` / `r42b` / `r42c`）测得；**物理实体 `ILME-FX3` 机身连接 Type-A HDMI 4K 外录机实测 `[Log Shooting]`/`PPLUT1..4` `1080p` 降格与 `[Off(HDMI Only)]` `4K 10-bit` 输出、实体 `SDXC`/`CFexpress Type A` 双卡写入 `M4ROOT/CLIP/`+`M4ROOT/SUB/` `(Px)` 代理文件验证 `119.88p`/`100p` 与 `S&Q >=120fps` 截断及机内原子联动删保、以及实体机身 MF `P/A/S/M` 实景测试 `[Focus Magnifier]` × `[Bright Monitoring]` 锁互斥与 `[Setting Effect OFF]` 自动退出尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 42 轮三项实机预演总览（`r42a` / `r42b` / `r42c`）

| 实跑场景 | Run ID | `r42_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **42A：`[HDMI Output Settings]`（`[Log Shooting]`/`PPLUT1..4` `1080p` 降格 vs `[Off(HDMI Only)]` `4K 10-bit` 6 模式 + 机内禁录 + 机背 LCD 关屏）+ Big-6 Home** | `round42-hdmi-log1080-big6` | `hdmi_log1080_hdmionly_4k_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接验证：`[Rec. Media dur HDMI Output]=On` 且 `RAW Output=Off` 时，开启 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`，`log_3modes_1080p=3`）或选择 `PPLUT1..PPLUT4`（`pplut1_to_4_1080p=4`）即使 `[Output Resolution]` 为 `2160p`/`Auto` 仍强制 HDMI 输出降为 `1920×1080`（`1080p`）；仅开启 `RAW Output=On`（`4264×2408` 16-bit）或切换 `[Rec. Media dur HDMI Output]=Off(HDMI Only)` 可解除 4K 限制并解锁全部 6 档 `[4K Output Set.(HDMI Only)]`（`59.94p/50p/29.97p/25p/23.98p/24.00p 10bit` at `3840×2160`，`hdmi_only_6_4k_modes_verified=6`，非法档位 `rc=-22`），同时完全禁用机内插卡录制（`internal_card_recording_active=0`, `rc=-1` `EPERM`）、临时强制 `[HDMI Info. Display]=Off` 并抑制 HDMI `[De-Squeeze]`；而 `[HDMI Info. Display]=On` 时叠加拍摄信息与红框 `Emphasized REC` 并将机背内置 LCD 熄屏（`camera_lcd_blanked_when_info_on=1`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `73.54s` | [`r42a-hdmi-log1080-big6-schinese-composited.png`](assets/r42a-hdmi-log1080-big6-schinese-composited.png) |
| **42B：`[Proxy Settings]` 双编码矩阵、`119.88p/100p` & `S&Q >=120fps` 截断与 `CLIP/`+`SUB/` 原子保险库** | `round42-proxy-vault` | `proxy_vault_119p_atomic_pair` | Native ARM64 `tmpfs` Slot 1 / Slot 2 `M4ROOT/CLIP/` + `M4ROOT/SUB/` 实测：`XAVC HS HD`（`1920×1080` 10-bit HEVC `16M`/`9M`，上限 `59.94p/50p`）与 `XAVC S HD`（`1280×720` 8-bit AVC `6M`，上限 `59.94p/50p`；非法 `16M` `rc=-22`）；实证 Normal `119.88p`/`100p`、S&Q `119.88p`/`100fps`/`120fps`/`200fps`/`240fps` 全数返回 `-22` `EINVAL` 截断，且 `[Off(HDMI Only)]` 返回 `-1` `EPERM` 零写卡（`hdmi_only_card_files=0`）；机内回放屏蔽 proxy 仅在主剪辑显示 `(Px)`（`proxy_playback_reject_rc=-95` `EOPNOTSUPP`）；单边破坏性删保全部被原子保险库拦截（`uncoupled_delete_clip_only_rc=-18` `EXDEV`, `uncoupled_delete_sub_only_rc=-18`, `uncoupled_protect_sub_only_rc=-1` `EPERM`），仅允许双边原子 Protect / Delete（`orphan_files_remaining=0`），`p2:/setting` 只读不变（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期 Proxy C 探针退出） | 跳过（Proxy C 探针退出） | **`0`** / **`0`** / **`0`** | `7.39s` | — |
| **42C：`[Focus Magnifier]` `x1.0`/`x4.0` 视频倍率、`[Auto Magnifier in MF]` 禁用、`[Bright Monitoring]` 锁互斥与 `16/16 H0 == H3`** | `round42-focusmag-brightmon` | `focusmag_brightmon_h0_h3` | Native ARM64 对焦放大与夜视增亮互锁探针证实：`[Initial Focus Mag.]` 视频模式严格限定 `x1.0`/`x4.0`（拒绝照片倍率 `x2.1`/`x1.5` `rc=-22`），照片模式区分全画幅 `x1.0`/`x2.1` 与 APS-C/S35 `x1.0`/`x1.5`；视频模式下 `[Auto Magnifier in MF]` 硬禁用（`rc=-95` `EOPNOTSUPP`），放大期间自动抑制 `[Marker Display]` 并于退出放大后恢复；`[Focus Magnifier]` 或 `[Auto Magnifier in MF]` 激活期间自定义按键切换 `[Bright Monitoring]` 均被硬拒（`rc=-16` `EBUSY`）；激活 `[Bright Monitoring]` 强制锁定 `[Live View Display]=[Setting Effect OFF]`，并在切出 `P/A/S/M`、切离 `MF` 或关机时自动取消；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期 FocusMag C 探针退出） | 跳过（FocusMag C 探针退出） | **`0`** / **`0`** / **`0`** | `5.87s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[HDMI Output Settings]`：`[Log Shooting]` / `PPLUT1..4` `1080p` 降格 vs `[Off(HDMI Only)]` `4K 10-bit` 与机背关屏（`r42a`）
```text
FX6_R42_HDMI_LOG1080_INIT baseline_4k_ok=1 log_3modes_1080p=3 pplut1_to_4_1080p=4
  raw_on_4264_override_ok=1 locked_4k_mode_rc=-16 hdmi_only_6_4k_modes_verified=6
  hdmi_only_width=3840 hdmi_only_height=2160 hdmi_only_bit_depth=10 invalid_4k_mode_reject_rc=-22
  hdmi_only_internal_rec_reject_rc=-1 internal_card_recording_active=0
  hdmi_only_forces_info_off=1 hdmi_only_suppresses_desqueeze=1
  camera_lcd_blanked_when_info_on=1 emphasized_tally_on_hdmi=1 lcd_active_when_info_off=1
  appfw_present=1 shim_present=1 emmc_write_count=0 r42_init_ok=1 verify_us=659806

FX6_R42_HDMI_LOG1080_BRIDGE log_pplut_1080p_forced=1 hdmi_only_6_modes_4k10b=6
  hdmi_only_internal_rec_rc=-1 hdmi_only_forces_info_off=1 hdmi_only_suppresses_desqueeze=1
  hdmi_info_on_blanks_lcd=1 hdmi_log1080_ok=1 emmc_write_count=0 r42_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `117` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`160` 实时线程零崩溃。

### 2.2 `[Proxy Settings]` 双编码矩阵、`119.88p/100p` & `>=120fps` 截断与 `CLIP/`+`SUB/` 原子保险库（`r42b`）
```text
FX6_R42_PROXY_VAULT xavc_hs_hd_1080p_16m_9m_ok=1 xavc_s_hd_720p_6m_ok=1 s_16m_reject_rc=-22
  normal_11988p_reject_rc=-22 normal_100p_reject_rc=-22 sq_11988p_reject_rc=-22
  sq_100fps_reject_rc=-22 sq_120fps_reject_rc=-22 sq_200fps_reject_rc=-22 sq_240fps_reject_rc=-22
  hdmi_only_rec_reject_rc=-1 hdmi_only_card_files=0 proxy_playback_reject_rc=-95
  px_badge_on_main_only=1 slot1_pair_created=1 slot2_pair_created=1
  uncoupled_delete_clip_only_rc=-18 uncoupled_delete_sub_only_rc=-18
  uncoupled_protect_sub_only_rc=-1 coupled_protect_both_ok=1 protected_delete_reject_rc=-1
  coupled_delete_both_ok=1 slot2_coupled_del_rc=0 orphan_files_remaining=0
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1
  emmc_write_count=0 r42b_ok=1 verify_us=699180
```

### 2.3 `[Focus Magnifier]` `x1.0`/`x4.0`、`[Auto Magnifier in MF]` 禁用、`[Bright Monitoring]` 锁互斥与 `16/16 H0 == H3`（`r42c`）
```text
FX6_R42_FOCUSMAG_BRIGHTMON movie_mag_10_40_ok=1 movie_reject_21_rc=-22 movie_reject_15_rc=-22
  still_ff_mag_21_ok=1 still_apsc_mag_15_ok=1 auto_mag_mf_movie_reject_rc=-95
  auto_mag_mf_still_rc=0 brightmon_blocked_while_automag_rc=-16
  marker_display_suppressed_while_mag=1 brightmon_blocked_while_focusmag_rc=-16
  marker_display_restored_after_mag=1 brightmon_forces_setting_effect_off=1
  brightmon_autocancel_non_pasm=1 brightmon_autocancel_non_mf=1
  brightmon_autocancel_poweroff=1 p2_write_blocked_rc=-30 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0
  r42c_ok=1 verify_us=6554
```

---

## 3. `r42a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r42a` Alpha（`26.21 KiB` / `26,842 B`） | `r42a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r42a Big6 Alpha](assets/r42a-hdmi-log1080-big6-schinese-alpha.png) | ![r42a Big6 Composited](assets/r42a-hdmi-log1080-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）通过 Type-A HDMI 线缆连接外部 4K 监视器/录机，在 `[Rec. Media dur HDMI Output]=[On]` + `[Log Shooting]`/`PPLUT1..4` 下实测外接屏幕 `1080p` 降格与切换 `[Off(HDMI Only)]` 后 6 档 `3840×2160 10-bit`（`59.94p/50p/29.97p/25p/23.98p/24.00p`）输出、机内禁录与 `[HDMI Info. Display]=On` 时机背 LCD 熄屏现象。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）插入 Slot 1 / Slot 2 `SDXC` / `CFexpress Type A` 存储卡实测 `XAVC HS HD`（`1920×1080 10-bit 16M/9M`）与 `XAVC S HD`（`1280×720 8-bit 6M`）代理同步录制、`119.88p/100p` 与 `S&Q >=120fps` 截断、`(Px)` 徽标与代理禁用回放，以及机内 Protect / Delete 对 `M4ROOT/CLIP/` + `M4ROOT/SUB/` 的原子同步操作。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在 `P/A/S/M` + `MF` 模式下实测 `[Focus Magnifier]`（视频 `x1.0`/`x4.0` vs 照片全画幅 `x2.1` / APS-C `x1.5`）、放大期间 `[Marker Display]` 隐藏，以及 `[Bright Monitoring]` 自定义键在放大激活期间的互斥锁定与切离 `P/A/S/M` / `MF` / 关机自动退出行为。

---

## 5. 复现命令与洁净室合规

```bash
# Run 42A: [HDMI Output Settings] Log/PPLUT 1080p Downshift vs Off(HDMI Only) 4K 10-bit + Blank LCD + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 42 --r42-mode hdmi_log1080_hdmionly_4k_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round42-hdmi-log1080-big6 --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r42-runs/r42a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r42a-hdmi-log1080-big6-schinese \
  --export-png-dir reports/2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu/assets

# Run 42B: [Proxy Settings] Dual-Codec Matrix, 119.88p/100p & S&Q >=120fps Cutoff, and Atomic CLIP/+SUB/ Vault
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 42 --r42-mode proxy_vault_119p_atomic_pair --lang en --run-id round42-proxy-vault \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r42-runs/r42b

# Run 42C: [Focus Magnifier] x1.0/x4.0, [Auto Magnifier in MF] Block, [Bright Monitoring] Lockout & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 42 --r42-mode focusmag_brightmon_h0_h3 --lang en --run-id round42-focusmag-brightmon \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r42-runs/r42c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
