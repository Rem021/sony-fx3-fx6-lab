# Round 55（Wave-41 / `R28..R55` 实机内核 QEMU 第 28 轮 · 累计第 84 次实跑里程碑）：FX3 7.02 原厂内核真机准备预演 — `[Auto Slow Shutter]` 6 项非功能锁定与 `[Shutter Angle]` 互斥、`[HDMI Output Settings]`（`[REC Control]` ← `[Time Code Output]` 前置依赖、`[4ch Audio Output]` 声道路由与 `[Rec. Media dur HDMI Output]` 保险库隔离）以及 `[Lens Compensation]` → `[Breathing Comp.]` 电影镜头与 `RAW`/`240p` 边界

> **日期**：2026-11-17 | **轮次**：**Round 55 Live ARM64 QEMU Rehearsal (Wave-41 · 28th Real-HW Round / 84th Live Run Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r55a` / `r55b` / `r55c`，累计达成 `R28..R55` 第 **28** 轮实机内核预演与第 **84** 次独立实跑、`56` 张 `< 50 KiB` PNG 视觉凭证）测得；**物理实体 `ILME-FX3` 机身上实测 `[Auto Slow Shutter]` 6 项低照度快门延长锁定、外接 HDMI 录机 `[Time Code Output]` + `[REC Control]` + `4ch` 音频与内录关闭、以及符合条件的 Sony E 卡口镜头实际呼吸补偿裁剪与 `RAW` / `S&Q 240p` 锁定尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 55 轮（Wave-41 · 第 28 轮实机内核 / 第 84 次实跑）三项实机预演总览（`r55a` / `r55b` / `r55c`）

| 实跑场景 | Run ID | `r55_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **55A：`[Auto Slow Shutter]` 6 项锁定与 `[Shutter Angle]` 严格互斥 + `[HDMI Output Settings]` 正常态闭环 + Big-6 Home** | `round55-auto-slow-6locks-hdmi-reccontrol-big6` | `auto_slow_6locks_hdmi_reccontrol_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]` 真实菜单节点（`fx3_wave41_nodes_ok=1`，出厂默认 `[On]` `auto_slow_default_on_ok=1`，非法入参 `rc=-22` `EINVAL`），在 `P`/`A + ISO AUTO` 正常生效（`auto_slow_nominal_active_ok=1`），并在全部 **6** 项官方锁定条件（(1) `S&Q`、(2) `Shutter Priority (S)`、(3) `Manual Exposure (M)`、(4) 固定手动 `ISO != ISO AUTO`、(5) `Flexible Exp. Mode` 手动快门、(6) `Log Shooting = Cine EI / Cine EI Quick`）下严格锁定不工作（`auto_slow_6locks_verified=6`），且与 `[Shutter Mode]=[Angle]` 零重叠（`auto_slow_shutter_angle_overlap_events=0`）；同时验证 `[HDMI Output Settings]`（`MENU -> Setup -> [External Output] -> [HDMI Output Settings]`）在 `[Time Code Output]=[On]` 后合法使能 `[REC Control]=[On]`（`hdmi_nominal_tc_rec_ctrl_ok=1`）、`[4ch Audio Output]` 双声道对路由（`CH1/CH2` 默认 vs `CH3/CH4` `hdmi_4ch_audio_routing_verified=2`）、`[Rec. Media dur HDMI Output]=[Off]` 保护 Slot-1 保险库零写入（`hdmi_rec_media_off_blocks_internal_ok=1`），且跨 `[Camera Settings Reset]` 存活（`hdmi_setup_survives_camreset_ok=1`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30` `EROFS`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.65s` | [`r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png`](assets/r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png) |
| **55B：Fail-Closed 前置条件与非法锁定注入防线（无 TC 开启 REC Control / Angle+Auto Slow 并发 / RAW·240p·Still 下开启 Breathing Comp.）** | `round55-prerequisite-lockout-injection-guard` | `prerequisite_lockout_injection_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 注入 `[Time Code Output]=[Off]` 时强行开启 `[REC Control]=[On]` 被硬件门禁拒绝（`illegal_rec_ctrl_rc=-16` `EBUSY`，`hdmi_rec_ctrl_without_tc_violations=0`）；(2) 注入在 `P` 档开启 `[Shutter Angle]`（`angle_in_p_rc=-16`）或 `[Shutter Angle]` 状态下同时开启 `[Auto Slow Shutter]`（`auto_slow_in_angle_rc=-16`，`auto_slow_shutter_angle_overlap_events=0`）全数阻断；(3) `[Breathing Comp.]`（默认 `[Off]` `breathing_default_off_ok=1`，电影模式合规 Sony 镜头轻微视角裁剪 `breathing_comp_crop_applied_ok=1`）在注入 `[RAW Output]=[On]`（`4264x2408` 16-bit 线性 HDMI RAW `raw_on_inject_rc=-16`）、`S&Q 239.76p`（`sq_240p_inject_rc=-16`）与 `200p`（`sq_200p_inject_rc=-16`）以及静态照片（`still_inject_rc=-95` `EOPNOTSUPP`）与非合规镜头（`noncompliant_lens_rc=-95`）时全数 fail-closed 拦截（`breathing_comp_raw_240p_still_leak_events=0`），同时保持物理 `Slot-1` Tier-0 保险库只读零写入（`slot1_vault_hdmi_block_rc=-30`，`slot1_vault_writes=0`，`slot1_vault_sha256_match=1`） | `13/13` 校验（早期前置条件与锁定注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.30s` | — |
| **55C：`[Camera Settings Reset]` vs `[Initialize]` 复位分化边界 + Wave-41 联合预演（Big-6 `346,206` px + `16/16 H0 == H3`）** | `round55-camreset-vs-initialize-h0-h3-integrated-big6` | `camreset_vs_initialize_h0_h3_integrated_big6` | Native ARM64 Wave-41 联合预演（累计第 **84** 次独立实跑）：精确验证 `[Reset Network Set.]` 不影响三项特性（`wave41_survives_netreset_ok=1`）；执行 `[Camera Settings Reset]` 时 **`[Auto Slow Shutter]` 复位回 `[On]`**（`auto_slow_camreset_on_ok=1`）且 **`[Breathing Comp.]` 复位回 `[Off]`**（`breathing_camreset_off_ok=1`），而 **`[HDMI Output Settings]`（`Time Code Output` / `REC Control` / `4ch Audio Output` / `Rec. Media dur HDMI Output`）完整存活**（`hdmi_setup_survives_camreset_ok=1`），仅在全机 **`[Initialize]`** 后全部归位出厂默认（`initialize_restores_all_wave41_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 完整渲染简体中文 **Big-6 Home**（`346,206` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.55s` | 同 `55A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Auto Slow Shutter]` 6 项锁定、`[Shutter Angle]` 互斥与 `[HDMI Output Settings]` 闭环（`r55a`）
```text
FX6_R55_AUTO_SLOW_HDMI_INIT fx3_wave41_nodes_ok=1 auto_slow_default_on_ok=1
  invalid_auto_slow_rc=-22 auto_slow_camreset_on_ok=1
  auto_slow_nominal_active_ok=1 auto_slow_6locks_verified=6
  auto_slow_shutter_angle_overlap_events=0 hdmi_nominal_tc_rec_ctrl_ok=1
  hdmi_4ch_audio_routing_verified=2 hdmi_rec_media_off_blocks_internal_ok=1
  hdmi_setup_survives_camreset_ok=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r55_init_ok=1 verify_us=892256

FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE auto_slow_default_on_ok=1
  auto_slow_6locks_verified=6 auto_slow_shutter_angle_disjoint_ok=1
  auto_slow_shutter_angle_overlap_events=0 auto_slow_reset_camreset_ok=1
  auto_slow_ok=1 emmc_write_count=0 r55_bridge_ok=1

FX6_R55_HDMI_RECCONTROL_BRIDGE hdmi_tcout_prereq_enforced_ok=1
  hdmi_rec_ctrl_without_tc_violations=0 hdmi_4ch_audio_routing_ok=1
  hdmi_rec_media_off_slot1_vault_ok=1 hdmi_setup_survives_camreset_ok=1
  hdmi_setup_ok=1 slot1_vault_writes=0 emmc_write_count=0 p2_setting_writes=0

FX6_R55_BREATHING_COMP_BRIDGE breathing_default_off_ok=1
  breathing_movie_only_crop_ok=1 breathing_raw_240p_still_blocked_ok=1
  breathing_comp_raw_240p_still_leak_events=0 breathing_reset_camreset_ok=1
  breathing_ok=1 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `114` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed 前置条件与非法锁定注入拦截（`r55b`）
```text
FX6_R55_LOCKOUT_INJECTION_GUARD illegal_rec_ctrl_rc=-16
  hdmi_rec_ctrl_without_tc_violations=0 angle_in_p_rc=-16
  auto_slow_in_angle_rc=-16 auto_slow_shutter_angle_overlap_events=0
  breathing_default_off_ok=1 breathing_comp_crop_applied_ok=1
  raw_on_inject_rc=-16 sq_240p_inject_rc=-16 sq_200p_inject_rc=-16
  still_inject_rc=-95 noncompliant_lens_rc=-95
  breathing_comp_raw_240p_still_leak_events=0 slot1_vault_hdmi_block_rc=-30
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r55b_ok=1 verify_us=831861
```

### 2.3 `[Camera Settings Reset]` vs `[Initialize]` 复位分化与 `16/16 H0 == H3`（`r55c`）
```text
FX6_R55_CAMRESET_INIT_H0_H3_INTEGRATED wave41_survives_netreset_ok=1
  auto_slow_camreset_on_ok=1 breathing_camreset_off_ok=1
  hdmi_setup_survives_camreset_ok=1 initialize_restores_all_wave41_defaults_ok=1
  auto_slow_shutter_angle_overlap_events=0 hdmi_rec_ctrl_without_tc_violations=0
  breathing_comp_raw_240p_still_leak_events=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r55c_ok=1 verify_us=407928
```

---

## 3. `r55a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r55a` Alpha（`26.21 KiB` / `26,842 B`） | `r55a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r55a Big6 Alpha](assets/r55a-auto-slow-hdmi-reccontrol-big6-schinese-alpha.png) | ![r55a Big6 Composited](assets/r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]`（`[On]` 默认 / `[Off]`）：在真实低照度光路下验证 `P`/`A + ISO AUTO` 自动降快门延长时间，以及在 `S&Q`、`Shutter Priority (S)`、`Manual Exposure (M)`、固定手动 `ISO`、`Flexible Exp. Mode` 手动快门与 `Log Shooting = Cine EI / Cine EI Quick` 全部 6 项条件下实际退出并保持与 `[Shutter Mode]=[Angle]` 严格不重叠。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上连接外部 HDMI 录机实测 `MENU -> Setup -> [External Output] -> [HDMI Output Settings]`：验证 `[Time Code Output]=[On]` 与 `[REC Control]=[On]` 触发外部录机同步起停、`[4ch Audio Output]` 在 `CH1/CH2` 与 `CH3/CH4` 间的 HDMI 嵌音切换、`[Rec. Media dur HDMI Output]=[Off]` 时抑制机内 Slot-1/Slot-2 与 Proxy 录像，以及跨 `[Camera Settings Reset]` 持久化。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上挂载呼吸补偿兼容 Sony E 卡口镜头实测 `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`：验证电影模式下对焦呼吸裁剪补偿实拍，并核验在 `4264x2408` 16-bit 线性 HDMI `[RAW Output]=[On]`、`S&Q` `239.76p`/`200p` 与静态照片模式下被系统灰度禁用。

---

## 5. 复现命令与洁净室合规

```bash
# Run 55A (82nd Live Run): [Auto Slow Shutter] 6-Condition Lockouts & [Shutter Angle] Disjoint + [HDMI Output Settings] + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 55 --r55-mode auto_slow_6locks_hdmi_reccontrol_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round55-auto-slow-6locks-hdmi-reccontrol-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r55-runs/r55a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r55a-auto-slow-hdmi-reccontrol-big6-schinese \
  --export-png-dir reports/2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing/assets

# Run 55B (83rd Live Run): Fail-Closed Prerequisite & Lockout Injection Guard ([REC Control] w/o TC, Angle + Auto Slow, RAW/240p/Still Breathing Comp.)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 55 --r55-mode prerequisite_lockout_injection_guard --lang en \
  --run-id round55-prerequisite-lockout-injection-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r55-runs/r55b

# Run 55C (84th Live Run): [Camera Settings Reset] vs [Initialize] Survival Split + Integrated Wave-41 + Big-6 346,206 px + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 55 --r55-mode camreset_vs_initialize_h0_h3_integrated_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round55-camreset-vs-initialize-h0-h3-integrated-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r55-runs/r55c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round55_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round55_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
