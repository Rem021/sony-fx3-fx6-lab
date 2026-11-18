# Round 57（Wave-43 / `R28..R57` 第 30 轮实机内核 QEMU 里程碑 · 第 90 次实跑）：FX3 7.02 原厂内核真机准备预演 — `[Release w/o Card]` / `[Release w/o Lens]`（Still vs Movie & PL 转接环）、Ver. 7.02 五项 `[Audio Recording]` + `DISP` 电平表（对比 `Ver. 1.x` 移除）与 `[Copyright Info]` `46` 字符零 PII 卫生

> **日期**：2026-11-17 | **轮次**：**Round 57 Live ARM64 QEMU Rehearsal (Wave-43 · 30th Real-HW Milestone / 90th Live Run!)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r57a` / `r57b` / `r57c`，累计达成 `R28..R57` **第 `30` 轮实机内核里程碑**与 **第 `90` 次独立实跑**、**`60` 张 `< 50 KiB` PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机身上实测 `[Release w/o Card]`/`[Release w/o Lens]` 无卡无镜头快门与内录拦截、`Ver. 7.02` 五项 `[Audio Recording]` 与 `[DISP (Screen Disp) Set]` 2ch/4ch 电平表、以及 `[Copyright Info]` Still EXIF 与 `[Camera Settings Reset]`/`[Initialize]` 尚待物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 57 轮（Wave-43 · 第 30 轮里程碑 / 第 90 次实跑）三项实机预演总览（`r57a` / `r57b` / `r57c`）

| 实跑场景 | Run ID | `r57_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **57A：无卡/无镜头诊断台架、Ver. 7.02 五项 `[Audio Recording]` + `DISP` 电平表、`[Copyright Info]` 46 字符卫生 + Big-6 Home** | `round57-release-wo-card-audio-meter-copyright-big6` | `release_wo_card_lens_audio_meter_copyright_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Shooting -> [Shutter/Silent]` 真实节点（`fx3_wave43_nodes_ok=1`）下的 **`[Release w/o Card]`**（默认 `[Enable]` / `[Disable]`，仅限 Still 静态快门，Slot-1/2 空卡槽下机内录像仍硬拦截 `cardless_movie_internal_rec_events=0`）与 **`[Release w/o Lens]`**（默认 `[Enable]` / `[Disable]`，覆盖 Still + Movie + `S&Q` PL 机械转接/纯机身台架，`e_nd_actuator_tx_count=0`）；精准核验 **`ILME-FX3 Ver. 7.02`（`ilc/2210`）五项 `[Audio Recording]` 菜单**（`Audio Recording`、`Audio Rec Level` `0..31` 默认 `26`、`Audio Out Timing` `Live`/`Lip Sync`、`Wind Noise Reduct.`、`Shoe Audio Set.`），确认 2ch/4ch MI-Shoe 音频电平表由 `[DISP (Screen Disp) Set]` 控制且在 `S&Q` 下自动抑制（`legacy_v1_audio_level_menu_spoof_events=0`）；核验 **`[Copyright Info]`**（`Write Copyright Info=Off` 默认、`<=46` 字符 `Set Photographer`/`Set Copyright` Still-EXIF 专属写入、`copyright_47char_rejected_rc=-22`、`photographer_copyright_pii_leaked_bytes=0`、`movie_copyright_tag_writes=0`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.95s` | [`r57a-release-wo-card-audio-meter-big6-schinese-composited.png`](assets/r57a-release-wo-card-audio-meter-big6-schinese-composited.png) |
| **57B：Fail-Closed 伪造注入 — 无卡内录、无镜头禁用、Ver. 1.x 旧菜单伪造、PII/超长版权与视频容器标签拒绝** | `round57-cardless-v1-audio-copyright-guard` | `cardless_movie_v1_audio_spoof_copyright_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) `Slot-1`/`Slot-2` 空卡槽下即使 `[Release w/o Card]=[Enable]`，机内录像仍被阻断（`cardless_movie_rec_rc=-123` `ENOMEDIUM`，`cardless_movie_internal_rec_events=0`）；(2) `[Release w/o Lens]=[Disable]` 在 Still/Movie/`S&Q` 全域拦截（`lensless_still_rc=-19`, `lensless_movie_rc=-19`, `lensless_sq_rc=-19` `ENODEV`，`lensless_disable_bypass_events=0`）；(3) 拒绝遗留 `Ver. 1.x`（`ilc/2035`）独立 `[Audio Level Display]` 节点伪造（`legacy_v1_audio_node_rc=-2` `ENOENT`，`legacy_v1_audio_level_menu_spoof_events=0`）；(4) 拒绝超 `46` 字符（47 字符）`Set Photographer`/`Set Copyright`（`rc=-22` `EINVAL`）、未脱敏 PII 注入（`pii_inject_rc=-1` `EPERM`）与 Movie 容器版权标签注入（`movie_copyright_tag_rc=-95` `EOPNOTSUPP`），保持 `photographer_copyright_pii_leaked_bytes=0`、`movie_copyright_tag_writes=0` 及只读保险箱零写入（`rc=-30` `EROFS`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.55s` | — |
| **57C：`[Camera Settings Reset]` vs `[Initialize]` 持久化分化 + `16/16 H0 == H3` + 30 轮 / 90 次里程碑收官** | `round57-camreset-copyright-disp-h0-h3-big6` | `camreset_copyright_disp_init_h0_h3_big6` | Native ARM64 Wave-43 联合预演（**第 `30` 轮里程碑 / 第 `90` 次独立实跑**）：验证 `[Reset Network Set.]` 保留全部 Wave-43 项（`wave43_survives_netreset_ok=1`）；执行 `[Camera Settings Reset]` 时，**五项 `[Audio Recording]` 与 `[Write Copyright Info]` 复位回出厂默认**（`audio_5items_camreset_ok=1`、`write_copyright_camreset_off_ok=1`），而 **`[Set Photographer]` / `[Set Copyright]` 字符串、`[DISP (Screen Disp) Set]` 以及 `[Release w/o Card]`/`[Release w/o Lens]` 完整存活**（`copyright_strings_survive_camreset_ok=1`、`disp_audio_meter_survives_camreset_ok=1`、`release_wo_survives_camreset_ok=1`），仅在 **`[Initialize]`** 时全部清空与复位（`initialize_clears_copyright_and_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `75.75s` | 同 `57A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 无卡/无镜头诊断、Ver. 7.02 五项 `[Audio Recording]` + `DISP` 电平表与 `[Copyright Info]` 卫生（`r57a`）
```text
FX6_R57_RELEASE_AUDIO_COPYRIGHT_INIT fx3_wave43_nodes_ok=1
  release_wo_defaults_enable_ok=1 release_wo_card_still_only_ok=1
  release_wo_lens_pl_bench_ok=1 cardless_movie_internal_rec_events=0
  audio_5items_verified=5 audio_rec_level_0_31_ok=1
  disp_audio_meter_modes_ok=1 legacy_v1_audio_level_menu_spoof_events=0
  write_copyright_off_default_ok=1 copyright_46char_hygiene_ok=1
  copyright_47char_rejected_rc=-22 photographer_copyright_pii_leaked_bytes=0
  movie_copyright_tag_writes=0 e_nd_actuator_tx_count=0 slot1_vault_writes=0
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r57_init_ok=1 verify_us=832999

FX6_R57_RELEASE_WO_CARD_LENS_BRIDGE release_wo_defaults_enable_ok=1
  release_wo_card_still_only_ok=1 cardless_movie_internal_rec_events=0
  release_wo_lens_pl_bench_ok=1 e_nd_actuator_tx_count=0
  release_wo_survives_camreset_ok=1 release_wo_card_lens_ok=1
  emmc_write_count=0 r57_bridge_ok=1

FX6_R57_AUDIO_V2_DISP_METER_BRIDGE audio_5items_verified=5
  audio_rec_level_0_31_ok=1 disp_audio_meter_modes_ok=1
  legacy_v1_audio_level_menu_spoof_events=0 audio_5items_camreset_ok=1
  disp_audio_meter_survives_camreset_ok=1 audio_v2_disp_meter_ok=1
  emmc_write_count=0 p2_setting_writes=0

FX6_R57_COPYRIGHT_46CHAR_HYGIENE_BRIDGE write_copyright_off_default_ok=1
  copyright_46char_hygiene_ok=1 photographer_copyright_pii_leaked_bytes=0
  movie_copyright_tag_writes=0 write_copyright_camreset_off_ok=1
  copyright_strings_survive_camreset_ok=1 copyright_46char_hygiene_bridge_ok=1
  slot1_vault_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `102` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed 无卡内录、Ver. 1.x 旧菜单伪造与 PII/超长版权拦截（`r57b`）
```text
FX6_R57_CARDLESS_V1_COPYRIGHT_GUARD cardless_movie_rec_rc=-123
  cardless_movie_internal_rec_events=0 lensless_still_rc=-19
  lensless_movie_rc=-19 lensless_sq_rc=-19 lensless_disable_bypass_events=0
  legacy_v1_audio_node_rc=-2 legacy_v1_audio_level_menu_spoof_events=0
  photographer_47char_rc=-22 copyright_47char_rc=-22 pii_inject_rc=-1
  movie_copyright_tag_rc=-95 photographer_copyright_pii_leaked_bytes=0
  movie_copyright_tag_writes=0 e_nd_actuator_tx_count=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1 slot1_vault_writes=0
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1
  cnflasha_writes=0 emmc_write_count=0 r57b_ok=1 verify_us=821024
```

### 2.3 `[Camera Settings Reset]` vs `[Initialize]` 与 `16/16 H0 == H3`（`r57c` — 第 90 次实跑里程碑）
```text
FX6_R57_CAMRESET_COPYRIGHT_DISP_H0_H3 wave43_survives_netreset_ok=1
  audio_5items_camreset_ok=1 write_copyright_camreset_off_ok=1
  copyright_strings_survive_camreset_ok=1 disp_audio_meter_survives_camreset_ok=1
  release_wo_survives_camreset_ok=1 initialize_clears_copyright_and_defaults_ok=1
  cardless_movie_internal_rec_events=0 legacy_v1_audio_level_menu_spoof_events=0
  photographer_copyright_pii_leaked_bytes=0 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r57c_ok=1 verify_us=327012
```

---

## 3. `r57a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r57a` Alpha（`26.21 KiB` / `26,842 B`） | `r57a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r57a Big6 Alpha](assets/r57a-release-wo-card-audio-meter-big6-schinese-alpha.png) | ![r57a Big6 Composited](assets/r57a-release-wo-card-audio-meter-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]`（`[Enable]`/`[Disable]` 仅限 Still 快门释放 vs 空卡槽机内录像拦截）与 `[Release w/o Lens]`（`[Enable]`/`[Disable]` Still + Movie + `S&Q` PL 机械转接环无触点实拍表现）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Shooting -> [Audio Recording]` 精准 5 项菜单（`Audio Recording`、`Audio Rec Level` `0..31`、`Audio Out Timing` `Live`/`Lip Sync`、`Wind Noise Reduct.`、`Shoe Audio Set.`）以及 `MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]` 控制机身 LCD/外接 HDMI 2ch/4ch MI-Shoe 音频电平表显隐及 `S&Q` 抑制行为。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身上实测 `MENU -> Shooting -> [File] -> [Copyright Info]`（`Write Copyright Info` 默认 `Off`、`<=46` 字符 `Set Photographer` / `Set Copyright` 仅写入 Still JPEG/ARW EXIF 而不写入视频容器）在 `[Camera Settings Reset]` vs `[Initialize]` 下的实机持久化行为。

---

## 5. 复现命令与洁净室合规

```bash
# Run 57A (88th Live Run): [Release w/o Card/Lens] + Ver. 7.02 5-Item [Audio Recording] + DISP Meter + [Copyright Info] + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 57 --r57-mode release_wo_card_lens_audio_meter_copyright_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round57-release-wo-card-audio-meter-copyright-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r57-runs/r57a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r57a-release-wo-card-audio-meter-big6-schinese \
  --export-png-dir reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/assets

# Run 57B (89th Live Run): Fail-Closed Cardless Movie, Lensless Disable, Legacy Ver. 1.x Audio Menu Spoof & >46-Char/PII Copyright Guard
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 57 --r57-mode cardless_movie_v1_audio_spoof_copyright_guard --lang en \
  --run-id round57-cardless-v1-audio-copyright-guard --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r57-runs/r57b

# Run 57C (90th Live Run / 30th Milestone!): [Camera Settings Reset] vs [Initialize] + 16/16 H0 == H3 + Big-6 346,686 px
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 57 --r57-mode camreset_copyright_disp_init_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round57-camreset-copyright-disp-h0-h3-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r57-runs/r57c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round57_realhw_release_wo_card_audio_meter_copyright_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round57_realhw_release_wo_card_audio_meter_copyright_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
