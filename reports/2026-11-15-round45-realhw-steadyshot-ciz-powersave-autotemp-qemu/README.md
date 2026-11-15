# Round 45（第 45 个里程碑 / Wave-31）：FX3 7.02 原厂内核真机准备预演 — `[SteadyShot Active]` 约 1.1× 裁切与三大硬阻断、`[Clear Image Zoom]` 四重自动状态锁、`[Power Save Start Time]` 九重自动豁免与 `[Auto Power OFF Temp.]` 三脚架热连锁

> **日期**：2026-11-15 | **轮次**：**Round 45 Live ARM64 QEMU Rehearsal (`45th Milestone` / Wave-31)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r45a` / `r45b` / `r45c`）测得；**物理实体 `ILME-FX3` 机身五轴防抖陀螺仪与约 `1.1x` 电子防抖视角标板实拍及外接 Atomos Ninja V+ HDMI RAW 联动、物理 E 卡口电动变焦杆/变焦环越过光学变焦进入 `Clear Image Zoom` / `Digital Zoom` 时的实时 PDAF 对焦与点测光灰显、以及物理离网 `NP-FZ100` 电池休眠电流测量与三脚架安装态下 `[Auto Power OFF Temp.]=[High]` 外壳热电偶温升曲线尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 45 轮三项实机预演总览（`r45a` / `r45b` / `r45c`）

| 实跑场景 | Run ID | `r45_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **45A：`[SteadyShot]`（视频）`[Active]` `~1.1x` 窄视角与三大硬截止 + Big-6 Home** | `round45-steadyshot-ciz-powersave-big6` | `steadyshot_active_cutoffs_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[SteadyShot]`（视频）`Off`（`1.00x`）、`Standard`（`1.00x`）、`Active`（约 `1.10x` 窄视角 `active_crop_x100=110`）3 档完备校验（非法档位拒止 `rc=-22` `EINVAL`），普通视频 `<=59.94p/50p`（`24/25/30/50/60` 共 `5` 档）与 `S&Q` `60fps` 全部允许开启 `Active`；严格执行官方三大硬阻断：① 普通 `[Rec Frame Rate]` `119.88p` / `100p` 自动回退至 `Standard`（`100`）并拒止 `Active`（`rc=-22` `EINVAL`）；② `S&Q` `[Frame Rate]` `>=120fps/100fps`（`100/120/200/240fps` 共 `4` 档）全面拒止 `Active`（`rc=-22` `EINVAL`）；③ 外接 HDMI `[RAW Output]=[On]` 立即压制 `Active` 并拒止重开（`rc=-16` `EBUSY`），关闭 `RAW Output` 后自动恢复 `Active`（`raw_off_restores_active_ok=1`）；`p2:/setting` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `74.86s` | [`r45a-steadyshot-ciz-powersave-big6-schinese-composited.png`](assets/r45a-steadyshot-ciz-powersave-big6-schinese-composited.png) |
| **45B：`[Clear Image Zoom]` / `[Digital Zoom]` `RAW` 与高帧率阻断及四重相机自动状态锁** | `round45-ciz-4locks` | `ciz_4locks_hfr_raw_cutoffs` | Native ARM64 超光学变焦与对焦/测光锁探针实测：静态 `[File Format]` 为 `JPEG` / `HEIF` 时放行（`jpeg_heif_ciz_allowed=2`），在 `RAW` / `RAW & JPEG` / `RAW & HEIF` 三种格式下全面阻断 `Smart Zoom`、`Clear Image Zoom` 与 `Digital Zoom`（`raw_3formats_ciz_blocked=3`, `rc=-22` `EINVAL`）；普通视频 `119.88p` / `100p`（`2` 档）及 `S&Q` `100/120/200/240fps`（`4` 档，对比 `S&Q` `60fps` 放行）全面阻断 `Clear Image Zoom` 与 `Digital Zoom`（`rc=-22`）；一旦越过光学变焦倍率（`zoom_scale_x100 > 100`），同步激活官方四重自动状态锁：① `[Focus Area]` 禁用并切为中央优先 AF（`center_priority_af_active=1`, 改写返回 `rc=-16` `EBUSY`）；② `[Metering Mode]` 强锁 `[Multi]`（非 `Multi` 改写返回 `rc=-16` `EBUSY`）；③ `[Face/Eye Prior. in AF]` 与 `[Face Priority in Multi Metering]` 禁用（返回 `rc=-95` `EOPNOTSUPP`）；④ `Real-time Tracking` 禁用（返回 `rc=-95` `EOPNOTSUPP`）；退回光学变焦 `1.00x` 后四重锁全部无损恢复（`optical_zoom_unlocks_all_4_ok=1`），`p2:/setting` 只读不变（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期变焦锁 C 探针退出） | 跳过（变焦锁 C 探针退出） | **`0`** / **`0`** / **`0`** | `6.71s` | — |
| **45C：`[Power Save Start Time]` 九重自动豁免、离网 `75 MiB` `p3` 冷备门禁、`[Auto Power OFF Temp.]` 三脚架热连锁与 `16/16 H0 == H3`** | `round45-powersave-autotemp` | `powersave_9cond_autotemp_h0_h3` | Native ARM64 电源管理与温控连锁探针证实：菜单项全称严格为 `"Power Save Start Time"`（拒绝截断 `"Power Save"`，默认 `5 Min` = `300s`，`exact_menu_label_ok=1`）；逐项验证全部 `9` 种官方自动豁免条件（USB 供电、幻灯片回放、FTP 传输、视频录制中、电脑连接、TV/HDMI 连接、`[IR Remote Ctrl]=[On]`、`[Bluetooth Rmt Ctrl]=[On]`、流媒体 / Creators' Cloud，`powersave_9conds_deactivated=9`，条件解除后自动重武装 `rearmed_after_9conds_clear_ok=1`）；在纯机内 `NP-FZ100` 离网态执行 Tier-0 `75 MiB` `p3` 冷备份预检时严拒 `5 Min` / `2 Min` / `1 Min` 休眠定时（`rc=-16` `EBUSY`），强制锁定 `[Off]`（`0s`）或 `[30 Min]`（`1800s`）（`airgapped_off_or_30min_vault_ok=1`）；`[Auto Power OFF Temp.]` 默认 `[Standard]`，开启 `[High]` 时严拒手持模式（`handheld_high_temp_reject_rc=-1` `EPERM` 低温烫伤防线）与 `[Fan Control]=[Always Off]`（`rc=-16` `EBUSY`），仅在三脚架固定且主动风扇策略受控时放行（`tripod_high_temp_coupled_fan_ok=1`）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期电源/温控 C 探针退出） | 跳过（电源/温控 C 探针退出） | **`0`** / **`0`** / **`0`** | `5.15s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[SteadyShot]`（视频）`[Active]` `~1.1x` 窄视角与三大硬阻断（`r45a`）
```text
FX6_R45_STEADYSHOT_ACTIVE_INIT steadyshot_3modes_verified=3 active_crop_x100=110
  narrower_aov_active=1 invalid_ss_reject_rc=-22 normal_le60p_allowed=5
  normal_11988p_100p_cutoff_ok=1 normal_hfr_active_reject_rc=-22 sq_60fps_active_allowed=1
  sq_ge100_cutoffs_verified=4 sq_hfr_active_reject_rc=-22 hdmi_raw_active_reject_rc=-16
  raw_off_restores_active_ok=1 p2_write_blocked_rc=-30 p2_sha256_match=1
  appfw_present=1 shim_present=1 emmc_write_count=0 r45_init_ok=1 verify_us=702667

FX6_R45_STEADYSHOT_ACTIVE_BRIDGE steadyshot_3modes_verified=3 active_crop_x100=110
  narrower_aov_active=1 normal_hfr_active_reject_rc=-22 sq_ge100_cutoffs_verified=4
  sq_hfr_active_reject_rc=-22 hdmi_raw_active_reject_rc=-16 steadyshot_active_ok=1
  emmc_write_count=0 r45_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `135` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[Clear Image Zoom]` / `[Digital Zoom]` `RAW` 与高帧率阻断及四重自动状态锁（`r45b`）
```text
FX6_R45_CIZ_4LOCKS jpeg_heif_ciz_allowed=2 raw_3formats_ciz_blocked=3
  raw_format_zoom_reject_rc=-22 invalid_zoom_mode_reject_rc=-22
  normal_11988p_100p_ciz_blocked=2 normal_hfr_zoom_reject_rc=-22 sq_60fps_ciz_allowed=1
  sq_100_120_200_240_ciz_blocked=4 sq_hfr_zoom_reject_rc=-22 center_priority_af_active=1
  focus_area_locked_rc=-16 metering_locked_multi_ok=1 non_multi_metering_reject_rc=-16
  face_eye_af_reject_rc=-95 face_multi_metering_reject_rc=-95 realtime_tracking_reject_rc=-95
  digital_zoom_4locks_ok=1 optical_zoom_unlocks_all_4_ok=1 p2_write_blocked_rc=-30
  p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r45b_ok=1 verify_us=605468
```

### 2.3 `[Power Save Start Time]` 九重自动豁免、离网 `75 MiB` `p3` 冷备门禁、`[Auto Power OFF Temp.]` 三脚架热连锁与 `16/16 H0 == H3`（`r45c`）
```text
FX6_R45_POWERSAVE_AUTOTEMP exact_menu_label_ok=1 default_5min_sec=300
  invalid_timer_reject_rc=-22 idle_airgapped_sleep_armed=1 powersave_9conds_deactivated=9
  rearmed_after_9conds_clear_ok=1 airgapped_5min_vault_reject_rc=-16
  airgapped_off_or_30min_vault_ok=1 p3_cold_dump_mib=75 default_autotemp_standard=1
  invalid_autotemp_reject_rc=-22 handheld_high_temp_reject_rc=-1
  fan_always_off_high_temp_reject_rc=-16 tripod_high_temp_coupled_fan_ok=1
  p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 emmc_write_count=0 r45c_ok=1 verify_us=3734
```

---

## 3. `r45a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r45a` Alpha（`26.21 KiB` / `26,842 B`） | `r45a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r45a Big6 Alpha](assets/r45a-steadyshot-ciz-powersave-big6-schinese-alpha.png) | ![r45a Big6 Composited](assets/r45a-steadyshot-ciz-powersave-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）搭配 E 卡口镜头在光学标板前实测 `[SteadyShot]` `[Active]` 相对 `[Standard]` / `[Off]` 的约 `1.1x` 视场裁切比例，以及外接 Atomos Ninja V+ 开启 HDMI `[RAW Output]=[On]` 时菜单自动压制 `[Active]` 的真机握手链路。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）推动电动变焦拨杆（Zoom Rocker）或镜头变焦环跨越光学变焦末端进入 `[Clear Image Zoom]` / `[Digital Zoom]` 区间时，实机观测 `[Focus Area]` 中央对焦框锁定、`[Metering Mode]` 自动切回 `[Multi]`、以及人脸/眼部识别与实时追踪图标灰显退出。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在纯机内 `NP-FZ100` 电池供电且无外接线缆与遥控连接时实测 `[Power Save Start Time]` `5 Min` 自动休眠电流阶跃、逐项接入 9 类外设/无线协议验证休眠豁免，以及安装在三脚架上开启 `[Auto Power OFF Temp.]=[High]` 连续 4K60p 录制时的镁合金机身热电偶温升曲线。

---

## 5. 复现命令与洁净室合规

```bash
# Run 45A: [SteadyShot Active] ~1.1x Crop & 3 Hard Cutoffs + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 45 --r45-mode steadyshot_active_cutoffs_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round45-steadyshot-ciz-powersave-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r45-runs/r45a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r45a-steadyshot-ciz-powersave-big6-schinese \
  --export-png-dir reports/2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu/assets

# Run 45B: [Clear Image Zoom] / [Digital Zoom] RAW & HFR Cutoffs + 4 Automatic Camera State Locks
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 45 --r45-mode ciz_4locks_hfr_raw_cutoffs --lang en --run-id round45-ciz-4locks \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r45-runs/r45b

# Run 45C: [Power Save Start Time] 9-Condition Bypass + Air-Gapped 75 MiB p3 Lock + [Auto Power OFF Temp.] & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 45 --r45-mode powersave_9cond_autotemp_h0_h3 --lang en --run-id round45-powersave-autotemp \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r45-runs/r45c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
make verify-milestone-221
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在仓库外/受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 50 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
