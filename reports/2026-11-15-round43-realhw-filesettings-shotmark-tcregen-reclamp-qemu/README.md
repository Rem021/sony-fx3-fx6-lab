# Round 43：FX3 7.02 原厂内核真机准备预演 — `[File Settings]`（5 种命名、37 字符 `Title Name`、SDHC `[Standard]` 锁与 `Shot Mark1/2` XML）、`[TC Regenerate]` Slot 1 主读与 `EXT-LK` 释放、`[REC Lamp]` 后置+顶键联动 Tally 与 `[Silent Mode]`

> **日期**：2026-11-15 | **轮次**：**Round 43 Live ARM64 QEMU Rehearsal** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r43a` / `r43b` / `r43c`）测得；**物理实体 `ILME-FX3` 机身插入 `SDXC`/`CFexpress Type A` 与 `<=32GB` FAT32 `SDHC` 存储卡验证 5 档 `[File Name Format]`、37 字符 `[Title Name Settings]` 与 `*M01.XML` `Shot Mark1/2` 写入及 FTP `[Only Shot Mark Mov.]` 筛选、实体双卡同步录制下跨断电验证 `[Time Code Make: Regenerate]` 读取 Slot 1 末帧时码与 `VMC-BNCM1` `EXT-LK` 释放、以及实体机身光学观测 `[REC Lamp]`（`[All On]` / `[Only Front Off]` 后置与顶部 `REC` 键联动常亮 / `[All Off]`）与 `[Silent Mode]=[On]` 锁定 `[Audio signals]=[Off]` 尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 43 轮三项实机预演总览（`r43a` / `r43b` / `r43c`）

| 实跑场景 | Run ID | `r43_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **43A：`[File Settings]` 5 档命名、37 字符 `Title Name`、SDHC `[Standard]` 锁 + `Shot Mark1/2` XML 与 Big-6 Home** | `round43-filesettings-shotmark-big6` | `filesettings_shotmark_big6` | Native ARM64 Stage-A `tmpfs` Slot 1 / Slot 2 与 `libgrm-fbinit9.so` 桥接验证：`[File Name Format]` 全部 5 档（`Standard` `C0001`、`Cam ID + Reel#` `A001C0002`、`Title` `UNITB0003`、`Date + Title` `261115UNITB0004`、`Title + Date` `UNITB2611150005`，`fnf_5modes_verified=5`，非法模式 `rc=-22`）及 `[File Number]`（`Series` 跨换卡递增 + `[Series Reset]` vs `Reset` 换空卡回 `0001`）且改名不改动已录旧文件（`prior_clip_untouched_ok=1`）；`[Title Name Settings]` 严格执行 `<=37` 单字节 ASCII 合法字符集（37 字符通过 `title_37char_max_ok=1`，`38` 字符与空格/`/`/`*` 非法字符返回 `-22` `EINVAL`）；`<=32GB` FAT32 `SDHC` 强制锁定 `[Standard]`（非 `Standard` 返回 `-22`）；视频禁止自建文件夹（`custom_movie_folder_reject_rc=-1` `EPERM`）；实证录制中 `Add Shot Mark1` / `Add Shot Mark2` 与回放中 `Add/Delete Shot Mark1/2` 持久化写入 `*M01.XML`、`[Image Jump Setting]` 4 档跳转与 FTP `[Only Shot Mark Mov.]` 过滤（`ftp_only_shotmark_mov=3`），同时驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `73.49s` | [`r43a-filesettings-shotmark-big6-schinese-composited.png`](assets/r43a-filesettings-shotmark-big6-schinese-composited.png) |
| **43B：`[TC/UB]` `[Regenerate]` Slot 1 主读、强制 `Rec Run`、`EXT-LK` 释放与 `S&Q` HDMI `TC Output` 阻断** | `round43-tc-regenerate` | `tc_regenerate_slot1_extlk` | Native ARM64 时码与 `tmpfs` 双槽探针实测：单卡模式下 `[Time Code Make: Regenerate]` 续读当前激活卡（Slot 1 或 Slot 2）末段剪辑结束时码，而开启 `[Simult. Recording]` 双卡同录时即使 Slot 2 存在更大时码（`09:59:59:23`）仍**唯一读取 Slot 1** 末帧时码（`01:15:20:10`，`simult_reads_slot1_only_ok=1`, `simult_slot2_ignored=1`）；`[Regenerate]` 下无论 `[Time Code Run]` 之前设为 `Free Run` 还是 `Rec Run` 均强制按 `[Rec Run]` 推进（待机 `standby_ticks_advanced=0`，录制 `rec_ticks_advanced=24`）；`VMC-BNCM1` 在 `Movie`+`Preset`+`Free Run` 建立 `EXT-LK` 后，切换 `[Time Code Make]` 至 `Regenerate` 或改动 `[Time Code Run]` 立即释放外锁（`ext_lk_active_after_regen=0`, `ext_lk_dropped_on_tc_run_change=1`，且 `Regenerate` 下重锁返回 `-22`）；HDMI `[Time Code Output]` 默认 `Off`，`S&Q` 模式下同时封锁 `[Time Code Run]` 与 HDMI `[Time Code Output]`（`rc=-95` `EOPNOTSUPP`），`p2:/setting` 只读不变（`rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期 TC C 探针退出） | 跳过（TC C 探针退出） | **`0`** / **`0`** / **`0`** | `7.60s` | — |
| **43C：`[REC Lamp]` 三态后置+顶键联动 Tally、`[Silent Mode]` 锁死 `[Audio signals]` 与 `16/16 H0 == H3`** | `round43-reclamp-silent` | `reclamp_coupled_tally_h0_h3` | Native ARM64 Tally LED 与静音互锁探针证实：`[REC Lamp]` 严格实现三态硬件耦合映射——`[All On]` 点亮前灯+后灯+机身顶部 `REC` 键红灯（`1/1/1`），`[Only Front Off]` 仅熄灭镜头侧前灯而将机背后灯与顶部 `REC` 键灯保持联动点亮（`0/1/1`, `only_front_off_011_coupled_ok=1`，不存在“关后灯留顶灯”或拆分的伪第 4 态 `uncoupled_split_reject_rc=-22`），`[All Off]` 全灭机身三处实体灯（`0/0/0`）且当 `[HDMI Info. Display]=On` 时 `[Emphasized REC Display]` HDMI 红框 Tally 仍独立正常输出（`emphasized_rec_hdmi_independent_ok=1`）；开启 `[Silent Mode]=On` 强制锁死 `[Audio signals]=Off`（改写返回 `-16` `EBUSY`，关闭后恢复原设置）；通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期 Tally C 探针退出） | 跳过（Tally C 探针退出） | **`0`** / **`0`** / **`0`** | `5.82s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[File Settings]` 5 档命名、37 字符 `Title Name`、SDHC `[Standard]` 锁与 `Shot Mark1/2` XML（`r43a`）
```text
FX6_R43_FILESETTINGS_SHOTMARK_INIT fnf_5modes_verified=5 invalid_fnf_mode_reject_rc=-22
  title_37char_max_ok=1 title_38char_reject_rc=-22 title_illegal_char_reject_rc=-22
  prior_clip_untouched_ok=1 series_persist_ok=1 reset_per_card_ok=1
  sdhc_forces_standard_ok=1 sdhc_non_standard_reject_rc=-22 custom_movie_folder_reject_rc=-1
  shotmark_rec_pb_xml_ok=1 image_jump_4modes_ok=4 invalid_jump_reject_rc=-22
  ftp_only_shotmark_mov=3 ftp_only_shotmark_filter_ok=1 appfw_present=1 shim_present=1
  emmc_write_count=0 r43_init_ok=1 verify_us=788992

FX6_R43_FILESETTINGS_SHOTMARK_BRIDGE fnf_5modes_verified=5 title_37char_max_ok=1
  title_38char_reject_rc=-22 sdhc_forces_standard=1 custom_folder_reject_rc=-1
  shotmark_xml_jump_ftp_ok=1 filesettings_shotmark_ok=1 emmc_write_count=0 r43_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `123` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[TC/UB]` `[Time Code Make: Regenerate]` Slot 1 主读、强制 `Rec Run`、`EXT-LK` 释放与 `S&Q` 阻断（`r43b`）
```text
FX6_R43_TC_REGENERATE hdmi_tc_output_default_off=1 regen_single_slot1_ok=1 regen_single_slot2_ok=1
  simult_reads_slot1_only_ok=1 simult_slot2_ignored=1 standby_ticks_advanced=0
  rec_ticks_advanced=24 regen_forced_rec_run_ok=1 ext_lk_locked_ok=1
  ext_lk_dropped_on_regen=1 ext_lk_active_after_regen=0 ext_lk_dropped_on_tc_run_change=1
  ext_lk_reject_when_regen_rc=-22 movie_hdmi_tc_out_on_rc=0 invalid_hdmi_tc_out_rc=-22
  sq_tc_run_reject_rc=-95 sq_hdmi_tc_output_reject_rc=-95 p2_write_blocked_rc=-30
  p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r43b_ok=1 verify_us=679276
```

### 2.3 `[REC Lamp]` 三态耦合后置+顶键 Tally、`[Silent Mode]` 锁死 `[Audio signals]` 与 `16/16 H0 == H3`（`r43c`）
```text
FX6_R43_RECLAMP_SILENT standby_leds_off_ok=1 reclamp_all_on_111_ok=1
  only_front_off_011_coupled_ok=1 reclamp_all_off_000_ok=1
  emphasized_rec_hdmi_independent_ok=1 uncoupled_split_reject_rc=-22
  silent_forces_audio_signals_off=1 audio_signals_locked_while_silent_rc=-16
  audio_signals_restored_when_silent_off=1 p2_write_blocked_rc=-30 dlopen_ok=1
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r43c_ok=1 verify_us=5097
```

---

## 3. `r43a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r43a` Alpha（`26.21 KiB` / `26,842 B`） | `r43a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r43a Big6 Alpha](assets/r43a-filesettings-shotmark-big6-schinese-alpha.png) | ![r43a Big6 Composited](assets/r43a-filesettings-shotmark-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）分别插入 `SDXC` / `CFexpress Type A`（exFAT）与 `<=32GB` FAT32 `SDHC` 卡，实测 `[File Name Format]` 5 档命名、`[Title Name Settings]` 37 字符 ASCII 上限、SDHC 强制锁定 `[Standard]`，以及录制/回放自定义键写入 `*M01.XML` `Shot Mark1/2` 与 Catalyst Browse / FTP `[Only Shot Mark Mov.]` 筛选传输。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）在 `[Simult. Recording]` 双卡同录下实测 `[Time Code Make: Regenerate]` 跨断电唯一读取 Slot 1 末帧时码并强制按 `[Rec Run]` 走字，以及外接物理 `VMC-BNCM1` BNC 时码线建立 `EXT-LK` 后切至 `Regenerate` 或修改 `[Time Code Run]` 时的脱锁行为与 `S&Q` 下 HDMI `[Time Code Output]` 屏蔽。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身光学目视检查 `[REC Lamp]` 三档（`[All On]`、`[Only Front Off]` 验证后置灯与顶部 `REC` 按键灯联动同亮、`[All Off]` 下外接 HDMI 监视器 `[Emphasized REC Display]` 红框独立显示）及 `[Silent Mode]=[On]` 对 `[Audio signals]=[Off]` 的强制互锁。

---

## 5. 复现命令与洁净室合规

```bash
# Run 43A: [File Settings] 5-Mode Naming, 37-Char Title Name, SDHC [Standard] Lock + Shot Mark1/2 XML + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 43 --r43-mode filesettings_shotmark_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round43-filesettings-shotmark-big6 --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r43-runs/r43a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r43a-filesettings-shotmark-big6-schinese \
  --export-png-dir reports/2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu/assets

# Run 43B: [TC/UB] [Time Code Make: Regenerate] Slot-1 Master Read, Forced Rec Run, EXT-LK Release & S&Q Block
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 43 --r43-mode tc_regenerate_slot1_extlk --lang en --run-id round43-tc-regenerate \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r43-runs/r43b

# Run 43C: [REC Lamp] 3-State Coupled Rear+Top Tally, [Silent Mode] -> [Audio signals] Lock & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 43 --r43-mode reclamp_coupled_tally_h0_h3 --lang en --run-id round43-reclamp-silent \
  --duration 35 --run-dir <SCRATCH_ROOT>/fx6-r43-runs/r43c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
