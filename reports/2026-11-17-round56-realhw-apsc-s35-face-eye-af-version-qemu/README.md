# Round 56（Wave-42 / `R28..R56` 实机内核 QEMU 第 29 轮 · 累计第 87 次实跑里程碑）：FX3 7.02 原厂内核真机准备预演 — `[APS-C S35 Shooting]` `12.1MP` HD `1.5x` 与 `4K`/`HDMI RAW` 强制锁定、BIONZ XR `[Face/Eye AF]`（`Right/Left Eye Select` 与 Clean-HDMI 防烧录隔离）以及 `[Version]` 只读核验 vs `BODYDATA.DAT` 刷机硬阻断

> **日期**：2026-11-17 | **轮次**：**Round 56 Live ARM64 QEMU Rehearsal (Wave-42 · 29th Real-HW Round / 87th Live Run Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r56a` / `r56b` / `r56c`，累计达成 `R28..R56` 第 **29** 轮实机内核预演与第 **87** 次独立实跑、`58` 张 `< 50 KiB` PNG 视觉凭证）测得；**物理实体 `ILME-FX3` 机身上实测 `[APS-C S35 Shooting]` HD 光学裁切视角与 `4K` 锁定、`[Face/Eye AF]` 实景人眼/动物/鸟类追焦与外接 HDMI 洁净画面、以及物理 `[Version]` 对话框（含真机手动更新红线）尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 56 轮（Wave-42 · 第 29 轮实机内核 / 第 87 次实跑）三项实机预演总览（`r56a` / `r56b` / `r56c`）

| 实跑场景 | Run ID | `r56_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **56A：`[APS-C S35 Shooting]` HD `1.5x` & `4K`/`HDMI RAW` 锁定 + BIONZ XR `[Face/Eye AF]` & `[Version]` 只读 + Big-6 Home** | `round56-apsc-s35-face-eye-af-version-big6` | `apsc_s35_hd_face_eye_af_version_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]` 真实节点（`fx3_wave42_nodes_ok=1`，默认 `[Auto]` `apsc_default_auto_ok=1`，`[On]`/`[Off]`，非法入参 `rc=-22` `EINVAL`），仅在 **`HD`（`XAVC S HD` / `XAVC S-I HD`）** 下约 `1.5x` 裁切生效（`apsc_hd_15x_ok=1`），并在 `ILME-FX3` `12.1MP` 全画幅传感器边界下对 `XAVC HS 4K` / `XAVC S 4K` / `XAVC S-I 4K` / `4264x2408 HDMI RAW` 全部锁定 `[Off]`（`apsc_4k_lockouts_verified=4`，`apsc_s35_4k_or_raw_bypass_events=0`）；核验 BIONZ XR `MENU -> Focus -> [Face/Eye AF]`（`[Face/Eye Prior. in AF]=On` 默认、`[Face/Eye Subject]` 3 类 `Human`/`Animal`/`Bird`、`[Right/Left Eye Select]` 3 项 `Auto`/`Right Eye`/`Left Eye` 及 `[Switch Right/Left Eye]`、`[Face/Eye Frame Disp.]` Clean-HDMI 零烧录 `hdmi_clean_feed_eye_frame_baked_pixels=0`）；核验 `MENU -> Setup -> [Setup Option] -> [Version]`（`Ver. 7.02` 只读、`version_inspect_flash_writes=0`、`passive_tx_bytes_emitted=0`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.78s` | [`r56a-apsc-s35-face-eye-af-big6-schinese-composited.png`](assets/r56a-apsc-s35-face-eye-af-big6-schinese-composited.png) |
| **56B：Fail-Closed `4K`/`HDMI RAW` `[APS-C S35]` 越权旁路、Clean-HDMI 眼框烧录与 `Slot-1` `BODYDATA.DAT` 刷机注入阻断** | `round56-apsc-4k-raw-cleanhdmi-bodydata-guard` | `apsc_4k_raw_cleanhdmi_bodydata_flash_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 注入在 `XAVC HS 4K`（`hs_4k_inject_rc=-16` `EBUSY`）、`XAVC S 4K`（`s_4k_inject_rc=-16`）、`XAVC S-I 4K`（`si_4k_inject_rc=-16`）与 `4264x2408` `HDMI RAW Output`（`hdmi_raw_inject_rc=-16`）期间强制开启 `[APS-C S35 Shooting]=[On]` 全部被拒绝（`apsc_s35_4k_or_raw_bypass_events=0`）；(2) 注入将 `[Face/Eye Frame Disp.]` 眼控方框烧录到 `[HDMI Info. Display]=[Off]`（`bake_hdmi_off_rc=-1`）及 `HDMI RAW`（`bake_hdmi_raw_rc=-1`）均被拦截（`hdmi_clean_feed_eye_frame_baked_pixels=0`）；(3) 拒绝虚假专用 AI 单元 `[Subject Recog in AF]` 菜单节点（`ai_unit_node_rejected_rc=-2` `ENOENT`）；(4) 模拟 `Slot-1` `BODYDATA.DAT` 固件刷机触发被强制硬阻断（`bodydata_flash_blocked_rc=-30` `EROFS`，`persistent_emmc_writes_authorized=0`，`bodydata_flash_attempts_succeeded=0`，`slot1_vault_writes=0`，`slot1_vault_sha256_match=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.51s` | — |
| **56C：`[Camera Settings Reset]` vs 已注册 `[Face Memory]` / `[Initialize]` 复位分化 + `16/16 H0 == H3` + Wave-42 联合预演** | `round56-camreset-face-memory-init-h0-h3-big6` | `camreset_face_memory_initialize_h0_h3_big6` | Native ARM64 Wave-42 联合预演（累计第 **87** 次独立实跑）：验证 `[Reset Network Set.]` 不影响 Wave-42 菜单项（`wave42_survives_netreset_ok=1`）；执行 `[Camera Settings Reset]` 时 **`[APS-C S35 Shooting]` 复位回 `[Auto]`**（`apsc_camreset_auto_ok=1`）且 **`[Face/Eye AF]` 四项菜单复位回出厂默认**（`face_eye_af_camreset_ok=1`），而 **已注册 `[Face Memory]` 数据库在 `[Camera Settings Reset]` 后完整存活**（`face_memory_survives_camreset_ok=1`），仅在显式删除（`face_memory_explicit_delete_ok=1`）或全机 **`[Initialize]`**（`initialize_clears_face_memory_and_defaults_ok=1`）时清除；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.32s` | 同 `56A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[APS-C S35 Shooting]` HD `1.5x`/`4K` 锁定、`[Face/Eye AF]` Clean-HDMI 与 `[Version]` 只读核验（`r56a`）
```text
FX6_R56_APSC_FACE_EYE_VERSION_INIT fx3_wave42_nodes_ok=1 apsc_default_auto_ok=1
  invalid_apsc_rc=-22 apsc_hd_15x_ok=1 apsc_4k_lockouts_verified=4
  apsc_s35_4k_or_raw_bypass_events=0 face_eye_defaults_ok=1 subjects_verified=3
  eyes_verified=3 switch_ok=1 clean_hdmi_isolated_ok=1
  hdmi_clean_feed_eye_frame_baked_pixels=0 version_readonly_ok=1
  version_inspect_flash_writes=0 passive_tx_bytes_emitted=0
  update_badge_suppressed_ok=1 slot1_vault_writes=0 p2_write_blocked_rc=-30
  p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r56_init_ok=1
  verify_us=828508

FX6_R56_APSC_S35_4K_LOCK_BRIDGE apsc_default_auto_ok=1 apsc_hd_15x_ok=1
  apsc_4k_lockouts_verified=4 apsc_s35_4k_or_raw_bypass_events=0
  apsc_reset_camreset_ok=1 apsc_s35_ok=1 emmc_write_count=0 r56_bridge_ok=1

FX6_R56_FACE_EYE_AF_HDMI_BRIDGE face_eye_defaults_ok=1 face_eye_subjects_3_ok=1
  face_eye_rl_3_ok=1 hdmi_clean_feed_eye_frame_baked_pixels=0
  face_memory_survives_camreset_ok=1 face_eye_af_ok=1 emmc_write_count=0
  p2_setting_writes=0

FX6_R56_VERSION_BODYDATA_GUARD_BRIDGE version_702_readonly_ok=1
  version_inspect_flash_writes=0 passive_tx_bytes_emitted=0
  bodydata_flash_hard_blocked_ok=1 slot1_vault_writes=0 version_ro_ok=1
  cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `106` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed `4K`/`HDMI RAW` 旁路、Clean-HDMI 隔离与 `BODYDATA.DAT` 刷机拦截（`r56b`）
```text
FX6_R56_APSC_4K_BODYDATA_GUARD hs_4k_inject_rc=-16 s_4k_inject_rc=-16
  si_4k_inject_rc=-16 hdmi_raw_inject_rc=-16 apsc_s35_4k_or_raw_bypass_events=0
  bake_hdmi_off_rc=-1 bake_hdmi_raw_rc=-1
  hdmi_clean_feed_eye_frame_baked_pixels=0 ai_unit_node_rejected_rc=-2
  bodydata_flash_blocked_rc=-30 persistent_emmc_writes_authorized=0
  bodydata_flash_attempts_succeeded=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 slot1_vault_writes=0 p2_write_blocked_rc=-30
  cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0
  emmc_write_count=0 r56b_ok=1 verify_us=779659
```

### 2.3 `[Camera Settings Reset]` vs `[Face Memory]` / `[Initialize]` 分化与 `16/16 H0 == H3`（`r56c`）
```text
FX6_R56_CAMRESET_FACE_MEM_H0_H3 wave42_survives_netreset_ok=1
  apsc_camreset_auto_ok=1 face_eye_af_camreset_ok=1
  face_memory_survives_camreset_ok=1 face_memory_explicit_delete_ok=1
  initialize_clears_face_memory_and_defaults_ok=1
  apsc_s35_4k_or_raw_bypass_events=0
  hdmi_clean_feed_eye_frame_baked_pixels=0 version_inspect_flash_writes=0
  passive_tx_bytes_emitted=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r56c_ok=1 verify_us=295148
```

---

## 3. `r56a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r56a` Alpha（`26.50 KiB` / `27,132 B`） | `r56a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r56a Big6 Alpha](assets/r56a-apsc-s35-face-eye-af-big6-schinese-alpha.png) | ![r56a Big6 Composited](assets/r56a-apsc-s35-face-eye-af-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]`（`[Auto]`/`[On]`/`[Off]`）：验证 `12.1MP` 全画幅传感器在 `HD`（`XAVC S HD` / `XAVC S-I HD`）下实际约 `1.5x` S35 光学裁切视角，以及在 `4K` 电影格式（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`）和 `4264x2408` `HDMI RAW Output` 下强制锁定 `[Off]` 的机内 UI 表现。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Focus -> [Face/Eye AF]`：验证 `[Face/Eye Prior. in AF]`（`[On]`/`[Off]`）、`[Face/Eye Subject]`（`Human`/`Animal`/`Bird`）、`[Right/Left Eye Select]`（`Auto`/`Right Eye`/`Left Eye` 与 `[Switch Right/Left Eye]` 自定义键）实时追焦与外接 HDMI 录机洁净画面（`[HDMI Info. Display] = [Off]` 不含 `[Face/Eye Frame Disp.]` 方框）及 `[Face Memory]` 在 `[Camera Settings Reset]` vs `[Initialize]` 下的实机持久化行为。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上只读核验 `MENU -> Setup -> [Setup Option] -> [Version]` 对话框（Body/Lens/Mount Adaptor 版本显示与零 RF 下更新提示抑制）；真实 `Slot-1` `BODYDATA.DAT` 刷机操作对所有自动化 Agent **永久 HARD-BLOCKED / NO-GO**（若人工操作仅允许满电 `NP-FZ100 >= 3 bars / >= 51%` 与 Sony 官方签名包）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 56A (85th Live Run): [APS-C S35 Shooting] HD/4K Lockout + [Face/Eye AF] + [Version] Read-Only + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 56 --r56-mode apsc_s35_hd_face_eye_af_version_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round56-apsc-s35-face-eye-af-version-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r56-runs/r56a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r56a-apsc-s35-face-eye-af-big6-schinese \
  --export-png-dir reports/2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu/assets

# Run 56B (86th Live Run): Fail-Closed 4K/HDMI RAW Bypass, Clean-HDMI Bake & BODYDATA.DAT Flash Injection Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 56 --r56-mode apsc_4k_raw_cleanhdmi_bodydata_flash_guard --lang en \
  --run-id round56-apsc-4k-raw-cleanhdmi-bodydata-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r56-runs/r56b

# Run 56C (87th Live Run): [Camera Settings Reset] vs [Face Memory]/[Initialize] Survival + Big-6 346,686 px + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 56 --r56-mode camreset_face_memory_initialize_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round56-camreset-face-memory-init-h0-h3-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r56-runs/r56c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round56_realhw_apsc_s35_face_eye_af_version_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round56_realhw_apsc_s35_face_eye_af_version_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
