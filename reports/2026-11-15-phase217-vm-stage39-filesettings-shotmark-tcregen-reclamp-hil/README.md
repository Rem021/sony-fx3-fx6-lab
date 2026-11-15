# Phase 217（VM Stage 39 `39/39`）：真机 `ILME-FX3` `[File Settings]` 37 字符 / `SDHC` 强制 `[Standard]` 锁定 + `Shot Mark1/2`、`[TC Regenerate]` 独占 Slot 1 & `EXT-LK` 解锁与 `[REC Lamp]` 后置+顶部 REC 键硬件耦合 Tally HIL 协同仿真报告

## 1. 结论先行

已在 `outputs/fx3-vm/` 独立完成 **Task H240 — Phase 217（VM Stage 39 `39/39` 里程碑）** 真实硬件主线协同仿真器开发、全板编排接入与双模全量验证：

- **交付物清单（严格受控 5 文件边界）**：
  1. 新增 Stage 39 核心模块：[realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py)
  2. 更新 39 阶段全板编排器（接入 `stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil` 与 `--skip-phase217`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 48 项双模单测套件（满足 `>= 45` 要求，含 `< 6.0s` 壁钟上限与源码只读/端口卫生断言）：[test_realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/tests/test_realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py)
  4. 更新虚拟机模块文档（Stage 39 `39/39` 章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/README.md)
  5. 参考索尼官方 `ILME-FX3 Ver. 7.02` 实测情报基线：[Wave-29 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/reports/2026-11-15-global-sony-wave29-file-settings-sdhc-shotmark-tc-regenerate-slot1-reclamp-coupled-tally-intel/README.md)

## 2. 核心子模型（`Sub-models A–C` + 硬安全红线）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 12 供体有界审计（实测冷启动 `3.91 ms < 0.02s`）与零字节泄露回退
- [`inspect_phase217_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py#L711-L802) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 定点 `lseek` 窗口读取并带进程内缓存，实测冷启动仅 **`0.00391s`**）；实证 `string_english_f.uxc`（`373,820 B`）、`fx3_appfw` 与 `fx3_libmpr` 包含全部 Wave-29 菜单词条与内部符号（`File Settings`、`File Name Format`、`Title Name Settings`、`Cam ID + Reel#`、`Shot Mark`、`Add Shot Mark1`、`Add Shot Mark2`、`Image Jump Setting`、`Only Shot Mark Mov.`、`Time Code Make`、`Regenerate`、`Time Code Output`、`REC Lamp`、`Only Front Off`、`Silent Mode`、`REGENERATE`、`REC_LAMP`、`SILENT_MODE`、`NonRealTimeMeta`、`LtcChangeTable`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动回退至确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Sub-model A — `[File Settings]` 5 种命名格式、37 字符 ASCII `[Title Name]`、`SDHC` 强制 `[Standard]` 锁定与 `Shot Mark1/2` `*M01.XML` 旁路车 HIL
- [`probe_file_settings_sdhc_lock_and_shotmark_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py#L853-L1038) 精确复刻 `MENU -> Shooting -> [File] -> [File Settings]`：
  - 完整协同仿真全部 5 种 `[File Name Format]`（`Standard`、`Cam ID + Reel#`、`Title`、`Date + Title`、`Title + Date`）以及跨 Slot 1 / Slot 2 的 `[File Number]`（`Series` 跨卡递增 vs `Reset` 新卡归 `0001` + `Series Counter Reset` 归零），且修改标题绝不追溯重命名卡上已录制的旧片段（`prior_clips_retroactively_renamed == False`）。
  - 严格执行 **`<= 37` 个允许 ASCII 字符**（`A-Za-z0-9` + `.-_@!#$%+=^~(),;[]`，共 80 字符；空标题、`>= 38` 字符溢出或空格/斜杠/非 ASCII 字符一律返回 `EINVAL = 22`）。
  - 当活动录制卡含 `SDHC`（`<= 32GB` FAT32）时强制锁定 `[File Name Format] = [Standard]`（尝试强行解锁非标准格式返回 `EOPNOTSUPP = 95`），并对尝试自定义 `/PRIVATE/M4ROOT/CLIP` 之外的视频目录返回 `EOPNOTSUPP = 95`（`sdhc_non_standard_filename_or_custom_folder_bypasses == 0`）。
  - 协同仿真录制实时打标（`Add Shot Mark1/2`）与回放切换增删（`Add/Delete Shot Mark1/2`）写入 `/PRIVATE/M4ROOT/CLIP/<Stem>M01.XML`（`NonRealTimeMeta`）旁路车，以及 `[Image Jump Setting]`（`Shot Mark Only` / `Shot Mark1 Only` / `Shot Mark2 Only` / `No Shot Mark`）与 FTP 传输过滤（`Only Shot Mark Mov.` / `Only Shot Mark`）。

### 2.3 Sub-model B — `[TC/UB]` `[Time Code Make: Regenerate]` 独占 Slot 1 主卡读取、强制 `Rec Run`、`VMC-BNCM1` `EXT-LK` 解锁与 `S&Q` HDMI 时间码阻断 HIL
- [`probe_tc_regenerate_slot1_extlk_and_sq_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py#L1141-L1291) 建模 `MENU -> Shooting -> [TC/UB] -> [Time Code Make]`：
  - 单卡录制下读取当前活动卡槽最末片段结束时间码，而在 **`[Simult. Recording]` 双卡同录下严格独占读取 `Slot 1`**（忽略不一致的 `Slot 2` 时间码，尝试强制从 `Slot 2` 再生返回 `EOPNOTSUPP = 95`，`slot2_simult_tc_regenerate_contamination_events == 0`），且无论 `[Time Code Run]` 原设何值均强制以 **`[Rec Run]`** 推进帧计数。
  - 验证 `VMC-BNCM1` 外部 `EXT-LK`（要求 `Movie` + `Preset` + `Free Run` 同步保持 `>= 10s`）一旦切换 `[Time Code Make]`、`[Time Code Run]`、进入 `S&Q`/`Photo` 或拔除适配器即刻释放外部锁定（`ext_lk_released == True`）；在 `S&Q` 模式下同时禁用 `[Time Code Run]` 与 HDMI `[Time Code Output]`（强行开启返回 `EOPNOTSUPP = 95`）。

### 2.4 Sub-model C & Redlines — `[REC Lamp]` 3 态后置+顶部 `REC` 键硬件耦合 Tally、`[Silent Mode]` 音频锁定与硬安全红线 HIL
- [`probe_rec_lamp_coupled_tally_and_silent_audio_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py#L1374-L1448) 协同仿真 `[REC Lamp]` 三态耦合：`[All On]` 点亮前置+后置+顶部 `REC` 按键 LED；**`[Only Front Off]` 仅关闭前置灯而同时保持后置灯与顶部 `REC` 按键红灯常亮**（拒绝电影机独占 `Only Rear Off` 等模式 `EINVAL = 22`，拒绝拆解顶部 `REC` 键与后置灯耦合 `EOPNOTSUPP = 95`，`decoupled_top_rec_button_vs_rear_tally_mismatches == 0`）；`[All Off]` 熄灭全部物理 LED，同时保持 `[Emphasized REC Display]` 红框 Tally 独立运行（`[HDMI Info. Display]=On` 时输出至 HDMI）；并验证 `[Silent Mode]=On` 硬锁 `[Audio signals]=Off`（尝试强行开启返回 `EOPNOTSUPP = 95`）。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h240-phase217-vm-stage39-filesettings-shotmark-tcregen-reclamp-hil/outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py#L1451-L1494) 硬锁全部 9 项禁止动作（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`sdhc_non_standard_filename_or_custom_folder_bypasses = 0`、`slot2_simult_tc_regenerate_contamination_events = 0`、`decoupled_top_rec_button_vs_rear_tally_mismatches = 0`）。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 39 独立自检 CLI | `LOCAL_DONOR_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（冷读取 `3.91 ms < 0.02s`；`digest=616e92d8d497` / `8f9d59a7fd97`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..39`） | 本地只读供体 / 洁净室合成 | `PASS`（`39/39` 全阶段通过，进程内本地 `1.87s < 2.0s`、洁净室 `0.512s < 0.6s`；`digest=61fa886deb59` / `1f35c9aab770`） |
| Stage 39 专项双模单测（48 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `48/48 OK`（`6.57s` / `3.83s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1516/1516 OK`（`106.15s` / `102.39s`，洁净室按预期 `skipped=3`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室门禁 | `ALL GREEN in 0.87s` |
