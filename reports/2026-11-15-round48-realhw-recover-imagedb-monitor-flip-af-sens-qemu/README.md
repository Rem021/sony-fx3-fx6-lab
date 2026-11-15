# Round 48（第 48 个里程碑 / Wave-34 / 实机内核 QEMU 连续第 20 轮 · 累计 60+ 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Recover Image DB]`（低电量拒止、非删除 `AVF_INFO` 修复与 Slot-1 Tier-0 只读防火墙）、`[Monitor Flip Direction]` 跨 `[Camera Settings Reset]` 持久化与 `[Horizontal Flip]` 回放零反转、以及电影/S&Q 对焦运动学（`[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sensitivity]` `1..5` 完整拼写）对标静态照片专属 `[Interval Shoot Func.]`

> **日期**：2026-11-15 | **轮次**：**Round 48 Live ARM64 QEMU Rehearsal (`48th Milestone` / Wave-34)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r48a` / `r48b` / `r48c`）测得；**物理实体 `ILME-FX3` 机身上插入真实 CFexpress Type A / SDXC 存储卡执行 `[Recover Image DB]` 与低电量 `NP-FZ100` 门禁复核、翻转机身侧开屏触发 `[Monitor Flip Direction]=[Horizontal Flip]` 对照回放画面方向与外接 Type-A HDMI 协议分析仪采集、以及搭载 E 卡口镜头实测 `[AF Transition Speed]` `1..7` / `[AF Subj. Shift Sensitivity]` `1..5` 拉焦曲线与静态照片模式 `[Interval Shoot Func.]` 快门序列尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 48 轮三项实机预演总览（`r48a` / `r48b` / `r48c`）

| 实跑场景 | Run ID | `r48_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **48A：`[Recover Image DB]` 极低电量硬件拒止、Slot 2 非删除 `AVF_INFO` 修复与 Slot-1 Tier-0 只读防火墙** | `round48-recover-imagedb-vault` | `recover_imagedb_battery_vault` | Native ARM64 存储库恢复与卡槽防火墙探针实测：模拟 `extremely_depleted` `NP-FZ100` 极低电量（`rc=-11` `EAGAIN`）与掉电欠压护栏（`rc=-16` `EBUSY`），在触碰任何 FAT/exFAT 簇前立即拒止（`depleted_pre_touch_writes=0`, `depleted_zero_metadata_touch_ok=1`）；在电量充足条件下对 Slot 2 暂存卡执行非删除 `AVF_INFO`（`AVF00001.INP`/`.BNP` + `MEDIAPRO.XML`）重建，消除虚假零剩余可录容量（`slot2_avf_info_repaired_ok=1`, `false_zero_recordable_cleared_ok=1`）且 **零删除任何素材**（`deleted_clips=0`，`3/3` 段 XAVC S/S-I 素材 SHA-256 100% 完好 `slot2_clips_3of3_sha256_intact=1`）；验证一次性动作菜单项对 `[Camera Settings Reset]` 与 `[Initialize]` 完全免疫（`action_item_immune_cam_reset=1`, `action_item_immune_initialize=1`）；强制拦截对 Slot-1 Tier-0 备份卡的数据库写入（未核验备份拒止 `rc=-16` `EBUSY`、物理写保护拒止 `rc=-13` `EACCES`、内核只读挂载 `O_RDWR` 拒止 `rc=-30` `EROFS`，`slot1_imagedb_writes=0`, `slot1_vault_sha256_match=1`） | `13/13` 校验（早期存储库防火墙 C 探针退出） | 跳过（存储库防火墙 C 探针退出） | **`0`** / **`0`** / **`0`** | `6.5s` | — |
| **48B：`[Monitor Flip Direction]` 跨 `[Camera Settings Reset]` 存活、`[Horizontal Flip]` 回放零反转与 HDMI 干净流 + Big-6 Home** | `round48-monitor-flip-playback-big6` | `monitor_flip_playback_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`[Monitor Flip Direction]` 完整覆盖全部 `4` 档（默认 `Auto` `monitor_flip_default_auto_ok=1`、`Horizontal Flip`、`Vertical Flip`、`Off`，`monitor_flip_4modes_verified=4`；非法枚举返回 `rc=-22` `EINVAL`）；证实非默认 `3` 档翻转模式跨 `[Camera Settings Reset]` 完整持久化保留（`flip_modes_survive_cam_reset=3`, `survives_cam_settings_reset_ok=1`），仅在全机 `[Initialize]` 时复位回 `Auto`（`reset_only_by_initialize=1`, `initialize_restores_auto_ok=1`）；开启 `[Horizontal Flip]` 时，机身本地拍摄取景 LCD 执行全宽 `1024 px` 左右水平镜像（`shooting_lcd_hflip_active=1`, `shooting_lcd_mirror_px_verified=1024`），而切换回放模式遍历 `64` 帧回放画面时 **回放显示方向从不反转**（`playback_hflip_inverted_frames=0`, `playback_non_inversion_ok=1`），且外接 HDMI 干净监看流始终保持 `0` 帧翻转（`hdmi_flipped_frames=0`, `hdmi_clean_unflipped_ok=1`）；`p2:/setting` 与 `cnflasha` 只读保护（`rc=-30` `EROFS`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.39s` | [`r48b-monitor-flip-playback-big6-schinese-composited.png`](assets/r48b-monitor-flip-playback-big6-schinese-composited.png) |
| **48C：电影/S&Q 对焦运动学（`[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sensitivity]` `1..5` 完整拼写）对标静态专属 `[Interval Shoot Func.]` + `16/16 H0 == H3`** | `round48-af-sens-interval-h0-h3` | `af_sens_interval_still_h0_h3` | Native ARM64 对焦运动学与间隔拍摄边界探针证实：严格锁定 `ILME-FX3` 官方完整拼写 `[AF Subj. Shift Sensitivity]`（`1..5` 共 `5` 档，默认 `5` `af_sens_default_5_ok=1`, `af_subj_shift_sens_5steps_verified=5`；拒绝 FX6/Cinema Line 缩写别名 `"AF Subj. Shift Sens."` `abbrev_sens_alias_reject_rc=-22` `EINVAL`）与 `[AF Transition Speed]`（`1..7` 共 `7` 档，默认 `5` `af_trans_default_5_ok=1`, `af_trans_speed_7steps_verified=7`），仅在 Movie / S&Q 模式下生效（`af_kinematics_movie_sq_ok=1`，Still 模式调用返回 `rc=-95` `EOPNOTSUPP`），且执行 `[Camera Settings Reset]` 后双双精准复位回默认值 `5` 同时保留非重置项 `[Monitor Flip Direction]`（`cam_reset_restores_af_trans_5_ok=1`, `cam_reset_restores_af_sens_5_ok=1`, `cam_reset_preserves_monitor_flip_ok=1`）；核验 `[Interval Shoot Func.]`（启动延时 `1..5999s`、拍摄间隔 `1..60s`、张数 `1..9999`）严格限定于静态照片序列（`interval_still_seq_ok=1`, `in_camera_timelapse_movie_mux=0`），对视频/S&Q `Interval Rec` 请求硬拦截（配置 `rc=-22` `EINVAL`、执行 `rc=-1` `EPERM`）；同时通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_writes=0`） | `13/13` 校验（早期对焦与间隔边界 C 探针退出） | 跳过（对焦与间隔边界 C 探针退出） | **`0`** / **`0`** / **`0`** | `5.67s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Recover Image DB]` 低电量拒止、非删除 `AVF_INFO` 修复与 Slot-1 Tier-0 只读防火墙（`r48a`）
```text
FX6_R48_RECOVER_IMAGEDB_VAULT invalid_slot_reject_rc=-22 invalid_batt_reject_rc=-22
  depleted_batt_refusal_rc=-11 brownout_guard_refusal_rc=-16 depleted_pre_touch_writes=0
  depleted_zero_metadata_touch_ok=1 slot2_avf_info_repaired_ok=1
  false_zero_recordable_cleared_ok=1 deleted_clips=0 slot2_clips_3of3_sha256_intact=1
  action_item_immune_cam_reset=1 action_item_immune_initialize=1
  slot1_vault_unverified_block_rc=-16 slot1_vault_wp_block_rc=-13 slot1_ro_kernel_rc=-30
  slot1_imagedb_writes=0 slot1_vault_sha256_match=1 p2_write_blocked_rc=-30
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r48a_ok=1 verify_us=823604
```

### 2.2 `[Monitor Flip Direction]` 跨 `[Camera Settings Reset]` 持久化、`[Horizontal Flip]` 回放零反转与 Big-6 渲染（`r48b`）
```text
FX6_R48_MONITOR_FLIP_INIT monitor_flip_default_auto_ok=1 invalid_flip_reject_rc=-22
  monitor_flip_4modes_verified=4 flip_modes_survive_cam_reset=3
  survives_cam_settings_reset_ok=1 reset_only_by_initialize=1 initialize_restores_auto_ok=1
  shooting_lcd_hflip_active=1 shooting_lcd_mirror_px_verified=1024
  playback_frames_swept=64 playback_hflip_inverted_frames=0 playback_non_inversion_ok=1
  hdmi_flipped_frames=0 hdmi_clean_unflipped_ok=1 p2_write_blocked_rc=-30
  p2_sha256_match=1 cnflasha_sha256_match=1 cnflasha_writes=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r48_init_ok=1 verify_us=722954

FX6_R48_MONITOR_FLIP_BRIDGE monitor_flip_default_auto_ok=1 monitor_flip_4modes_verified=4
  survives_cam_settings_reset_ok=1 reset_only_by_initialize=1
  shooting_lcd_hflip_active=1 playback_hflip_inverted_frames=0 hdmi_flipped_frames=0
  monitor_flip_ok=1 emmc_write_count=0 p2_setting_writes=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `130` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.3 电影/S&Q 对焦运动学（`1..7` & `1..5` 完整拼写）对标静态照片 `[Interval Shoot Func.]` 及 `16/16 H0 == H3`（`r48c`）
```text
FX6_R48_AF_SENS_INTERVAL af_trans_default_5_ok=1 af_sens_default_5_ok=1
  exact_full_spelling_ok=1 abbrev_sens_alias_reject_rc=-22
  invalid_af_trans_reject_rc=-22 invalid_af_sens_reject_rc=-22
  af_trans_speed_7steps_verified=7 af_subj_shift_sens_5steps_verified=5
  af_kinematics_movie_sq_ok=1 af_kinematics_still_reject_rc=-95
  cam_reset_restores_af_trans_5_ok=1 cam_reset_restores_af_sens_5_ok=1
  cam_reset_preserves_monitor_flip_ok=1 initialize_resets_all_ok=1
  interval_still_seq_ok=1 invalid_interval_param_reject_rc=-22
  video_interval_rec_mode_reject_rc=-22 video_interval_rec_exec_reject_rc=-1
  in_camera_timelapse_movie_mux=0 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 emmc_write_count=0 r48c_ok=1 verify_us=194617
```

---

## 3. `r48b` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r48b` Alpha（`26.50 KiB` / `27,132 B`） | `r48b` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r48b Big6 Alpha](assets/r48b-monitor-flip-playback-big6-schinese-alpha.png) | ![r48b Big6 Composited](assets/r48b-monitor-flip-playback-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）插入真实 CFexpress Type A / SDXC 媒体，在 `NP-FZ100` 极低电量下实测 `[Recover Image DB]` 拒止提示，以及更换满电电池后重建受损 `AVF_INFO` 并回放原卡全部 XAVC S/S-I 素材片段。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）将 `[Monitor Flip Direction]` 设为 `[Horizontal Flip]`，实机核验拍摄取景屏水平镜像、回放模式图像方向永不反转、外接 Type-A HDMI 采集卡输出未翻转画面、以及跨 `[Camera Settings Reset]` 配置保留。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）挂载 E 卡口自动对焦镜头，在 Movie / S&Q 模式下实测 `[AF Transition Speed]` `1..7` 与 `[AF Subj. Shift Sensitivity]` `1..5` 拉焦速度与主体切换阻尼，并在静态照片模式下实测 `[Interval Shoot Func.]` 间隔快门拍摄与电脑端合成延时视频流程。

---

## 5. 复现命令与洁净室合规

```bash
# Run 48A: [Recover Image DB] Depleted-Battery Refusal, Non-Deleting AVF_INFO Repair & Slot-1 Tier-0 Vault Firewall
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 48 --r48-mode recover_imagedb_battery_vault --lang en \
  --run-id round48-recover-imagedb-vault --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r48-runs/r48a

# Run 48B: [Monitor Flip Direction] [Camera Settings Reset] Survival & [Horizontal Flip] Playback Non-Inversion + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 48 --r48-mode monitor_flip_playback_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round48-monitor-flip-playback-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r48-runs/r48b \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r48b-monitor-flip-playback-big6-schinese \
  --export-png-dir reports/2026-11-15-round48-realhw-recover-imagedb-monitor-flip-af-sens-qemu/assets

# Run 48C: Movie/S&Q AF Kinematics ([AF Transition Speed] 1..7 & [AF Subj. Shift Sensitivity] 1..5 Full Spelling) vs Still-Only [Interval Shoot Func.] + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 48 --r48-mode af_sens_interval_still_h0_h3 --lang en \
  --run-id round48-af-sens-interval-h0-h3 --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r48-runs/r48c

# Dual-Mode Unit Tests & Clean Audit
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
