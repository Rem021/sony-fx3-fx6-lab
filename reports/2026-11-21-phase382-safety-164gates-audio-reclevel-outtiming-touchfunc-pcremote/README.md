# Phase 382（`Task H490`，Wave-72，`164/164` 硬件安全门禁）：`[Audio Rec Level]` / `XLR-H1` 物理抢占与常驻 Limiter + `[Audio Out Timing]` / 抗复位 `[Volume Settings]` / 精确 5 项 `[4ch Audio Monitoring]`（`G163`），及 `[Touch Func. in Shooting]` 4 活跃抗复位子项 vs 100% 休眠触控特征 + `[Remote Shoot Setting]` PTP/PTP-IP 与 Tier-0 `Slot 1` `EROFS=30` 防火墙（`G164`）

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H490` · **Phase 382（`164/164` 硬件安全门禁）**
- **核心结论（`实测事实`）**：
  1. 已交付门禁 **`G163`**（[`verify_audio_reclevel_outtiming_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py)）与 **`G164`**（[`verify_touchfunc_pcremote_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py)）及统一预检引擎 **`verify-164-gates`**（[`evaluate_164gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py) / `verify_real_hardware_164gate_readiness`）。
  2. 离线默认模式实测通过 **`161/164`** 项门禁（`VERIFIED_161_OF_164_AWAITING_PHYSICAL_TIER0`，因 Tier-0 物理台架收据 `G10..G12` 未连机而 fail-closed，`overall_ready_for_hardware_attach = False`）；`--simulate-bench-dry-run --force-clean-room` 模拟干跑模式通过 **`164/164`** 项（`VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP`），所有物理写盘/跨机型刷机/实时连机红线恒锁 `False` 与 `0`（`raw_firmware_bytes_leaked = 0`、`usb_packets_transmitted = 0`、`cross_model_flash_authorized = False`）。
  3. 4 模式 164 门禁单元测试（`108/108` × 4：`47.39s` / `52.38s` / `47.70s` / `51.57s`）、全量 `outputs/fx3-safety/tests`（`5,146` 项测试，Normal `5,146/5,146 OK` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` `5,146 OK (skipped=10)` 双模均 `0` 失败）、双模 `make verify-milestone-375`（自动发现 `gate160=161/164`、`leaked=0`）及 `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 全部通过（`ALL GREEN`，零 `.pyc`）。
- **Wave-72 实证基线**：[Wave-72 调研报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/reports/2026-11-18-global-sony-wave72-audio-reclevel-outtiming-touchfunc-pcremote-intel/README.md)
- **硬件安全态势**：对 `23` 个本地 donor 构件（含 `FX3 appFw.so` `36` 个有界切片、`libptp.so`、`libInfraPtpControl.so`、`libInfraPtpExtCmd.so`、`libInfraRemote.so`、`libInfraMtpServer.so`、`FX3-CX95900_ALLLANG-Backup.bin`、4 语种 UXC 与 `FX6 appFw.so` `24` 个切片 / `libptp.so` / `libInfraPtpControl.so` / `libInfraRemote.so` / `string_english*.uxc` 零 `"MONITOR VOL"` 核验）严格执行只读 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` + `os.pread`（实测耗时 `0.0099s <= 2.0s`）并内置显式 `work_root is None` 防护与无盘 `CLEAN_ROOM_SYNTHETIC` 回退（`raw_firmware_bytes_leaked == 0`、`emmc_writes_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`usb_packets_transmitted == 0`）。

---

## 1. 交付物清单（严格 6 个受控文件）

1. 门禁与 164 门禁统一预检模块：[`realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py)
2. 包导出注册（212 项非遮蔽符号）：[`fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/__init__.py)
3. CLI 注册（`verify-audio-reclevel-outtiming-guard` / `verify-g163`、`verify-touchfunc-pcremote-guard` / `verify-g164`、`verify-164-gates`）：[`fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/fx3_safety/__main__.py)
4. 安全套件文档更新（新增 §82）：[`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/README.md)
5. 4 模式单元测试套件（`108` 项测试）：[`test_realhw_audio_reclevel_outtiming_touchfunc_pcremote_164gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/outputs/fx3-safety/tests/test_realhw_audio_reclevel_outtiming_touchfunc_pcremote_164gate_guard.py)
6. 中文工程收尾报告（本文件）：[`reports/2026-11-21-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h490-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/reports/2026-11-21-phase382-safety-164gates-audio-reclevel-outtiming-touchfunc-pcremote/README.md)

---

## 2. 新增安全门禁与实测 / 推断边界

### 2.1 门禁 `G163`：`AUDIO_RECLEVEL_XLRH1_PREEMPTION_LIMITER_OUTTIMING_VOLUME_4CH_MONITORING_FIREWALL`
- **`实测事实`（`[Audio Rec Level]`、3 层硬件抢占与常驻 Limiter）**：
  - 精确路径 `Shooting -> [Audio Recording] -> [Audio Rec Level]`（`_f 0x63b9`/`0x6f0a`），量程 `0..31`（32 档），出厂默认 `26`（`adj_audio_rec_level_defult` 原厂拼写；`Delete` 键归位 `26`；`Can be reset`），仅作用于机身内置立体声麦与机身 `3.5mm MIC`（机身限幅器永久运行不可关闭，任何关闭请求返 **`EOPNOTSUPP=95`**）。
  - 严格执行 3 层硬件抢占链：(a) `3.5mm MIC` 插入抢占 MI 靴（`[Shoe Audio Set.]` 变灰、`[Wind Noise Reduct.]` 旁路）；(b) 无 `3.5mm MIC` 且 `XLR-H1 HANDLE AUDIO = ON` 抢占机身 `[Audio Rec Level]`（`UIBIZ_INP_HOTSHOE_XLRMIC`），由手柄物理开关主导（`LINE` 锁死 `+4 dBu` 且 `ATT` 无效、`MIC`/`MIC+48V` `ATT 0/10/20 dB` 对应 `-60/-50/-40 dBu`、`AUTO`/`MAN`/`LINK`）；(c) `S&Q Motion` 强制 `0ch` 静音并锁死全部 4 个录音调节项。
- **`实测事实`（`[Audio Out Timing]`、抗复位 `Setup -> [Sound Option]` 与精确 5 项 `[4ch Audio Monitoring]` vs FX6）**：
  - `[Audio Out Timing]`（`Shooting -> [Audio Recording]`，`Live` 默认 / `Lip Sync`，`Can be reset`，`S&Q` 下禁用）。
  - `Setup -> [Sound Option]` 下 **`[Volume Settings]`（`0..15`，默认 `7`）与 `[4ch Audio Monitoring]`（默认 `CH1/CH2`）均抗 `[Camera Settings Reset]`**（Wave-72 纠偏 Wave-62，仅 `[Initialize]` 还原）；精确 5 项枚举 **`CH1/CH2`、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`**（任何杜撰标签如 `"CH1/CH2 mono mix"` / `"CH1+2/CH3+4"` / `"All"` 均返 **`EOPNOTSUPP=95`**），与 HDMI `[4ch Audio Output]`（`CH1/CH2`/`CH3/CH4`）完全独立，3.5mm 耳机孔硬件限于 2ch。
  - 对照 `ILME-FX6 Ver. 6.01` `Audio > Audio Input/Output`：3 级 Reference（`INPUT1/2 MIC Reference` 6 档、`Line Input Reference` 4 档、`Reference Level` **5 档**含 `-16dB`/`EBUL`）、**6 档** `Limiter Mode`（`Off/-6/-9/-12/-15/-17 dB`）、**7 项** `Monitor CH`、`Headphone Out`（`Stereo`/`Mono`）、`Volume 0..50`（核验 `"MONITOR VOL +/-"` 物理侧键命中 **`0`**，请求返 **`EOPNOTSUPP=95`**），以及 `SDI OUT` 4ch vs `HDMI` 2ch 成对输出（`480` 状态矩阵全通过）。
- **`推断`**：将 `Setup -> [Sound Option]` 误判为可随 `[Camera Settings Reset]` 复位或向 FX3 写入杜撰 4ch 监听枚举会导致台架监听错路与 `XLR-H1` 后置扬声器啸叫风险，故由 `G163` 硬性拦截。

### 2.2 门禁 `G164`：`TOUCH_FUNC_4ACTIVE_VS_DORMANT_PAD_SHUTTER_AE_AND_REMOTE_SHOOT_PTP_SLOT1_EROFS_FIREWALL`
- **`实测事实`（`[Touch Func. in Shooting]` 4 活跃抗复位子项 vs 100% 休眠触控与 FX6 对比）**：
  - `Setup -> [Touch Operation]` 严格仅暴露 **4** 个活跃子项（全部抗 `[Camera Settings Reset]`，仅 `[Initialize]` 还原）：`[Touch Operation]`（`On` 默认 / `On: Playback Only` / `Off`）、`[Touch Sensitivity]`（`Standard` 默认 / `Sensitive`）、`[Touch Func. in Shooting]`（`Touch Focus` / `Touch Tracking` 默认 / `Off`，Still/Movie/`S&Q` 三模式完全一致）与 `[Swipe Up]`（`Open the Fn Menu` 默认 / `Off`）。
  - 4 项 100% 休眠触控功能均硬返 **`EOPNOTSUPP=95`**：`[Touch Panel/Pad]`（`_f 0x76ec`）、`[Touch Pad (vertical)]`（`_f 0x7312`）、`[Touch Shutter]`（`_f 0x6a80`）与 `[Touch AE]`（`_f 0x702a`）；点测光联动走 `[Spot Metering Point]`（`Center` vs `Focus Point Link`），追踪启动后锚定起始点且不跟随移动框。对照 FX6 `Touch Operation`、`Touch Function in MF`（`Spot Focus` 在 MF 镜头 / `De-Squeeze != Off (1.0x)` / `Focus Magnifier` 下禁用、`Tracking AF`）及 Ver. 6.00+ `BIG6` 触控。
- **`实测事实`（`[Remote Shoot Setting]` PTP/PTP-IP 与 Tier-0 `Slot 1` `EROFS=30` 防火墙）**：
  - Ver. 2.00..7.02 `Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]`（4 子项全部抗 `[Camera Settings Reset]`，仅 `[Initialize]` 或 `[Reset Network Set.]` 还原）：`[Still Img. Save Dest.]`（`Destination Only` / **`Dest.+Camera` 出厂默认！** / `Camera Only`）、`[Save Image Size]`（`Original`/`2M` 默认）、`[RAW+J Save Image]`（`JPEG Only` 默认）、`[RAW+H Save Image]`（`HEIF Only` 默认）；连接态修改保存目的地返 **`EBUSY=16`**（`PRM_HAITA_*`）。
  - PTP-over-USB（`/dev/usb/sicd_{core,data,event}`，`libInfraPtpControl.so`）与 PTP-IP（`TCP 15740`，`libInfraRemote.so`）强锁 **Tier-0 `Slot 1` `EROFS=30` 防火墙**：唯有 `Destination Only` 通过 DRAM 零写卡直传（`slot1_writes == 0`，支持无卡释放）；出厂默认 **`Dest.+Camera`** 与 **`Camera Only`**（含 `[Reset Network Set.]` 后自动回落默认）面向 Tier-0 `Slot 1` 写卡时最高优先级硬返 **`EROFS (errno 30)`**。对照 FX6 `Network Client Mode` / `Camera Remote Control` 零 `Still Img. Save Dest.` UI（返 `EOPNOTSUPP=95`，`432` 状态矩阵全通过）。
- **`推断`**：实机台架若在执行 `[Reset Network Set.]` 后未重新锁定 `Destination Only`，出厂默认 `Dest.+Camera` 将直接向金卡 `Slot 1` 写入 `DCIM/` 与 `AVF_INFO` 增量，故 `G164` 将 `EROFS=30` 置于最高拦截优先级。

---

## 3. 实测验证结果（`实测事实`）

| 检查项 / 命令 | 覆盖范围 | 执行模式 | 实测结果 |
| :--- | :--- | :--- | :--- |
| `test_realhw_audio_reclevel_outtiming_touchfunc_pcremote_164gate_guard.py` | `108` 项单元测试（4 模式） | Normal / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / Donorless (`work_root=None`) | 全部 PASS（`108/108` × 4：`47.39s` / `52.38s` / `47.70s` / `51.57s`，`0` 失败） |
| `python3 -B -m fx3_safety verify-g163 --summary` & `verify-g164 --summary` | 单门禁 CLI 校验 | `LOCAL_DONOR_O_RDONLY` | PASS（`G163` 与 `G164` 均 `valid=True`，`23` donor `0.0099s <= 2.0s`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-164-gates --summary` | `G01..G164` 统一预检 | 离线默认 NO-GO（`LOCAL_DONOR_O_RDONLY`） | PASS（`161/164`，`VERIFIED_161_OF_164_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-164-gates --simulate-bench-dry-run --force-clean-room --summary` | `G01..G164` 统一预检 | 离线模拟干跑（`CLEAN_ROOM_SYNTHETIC`） | PASS（`164/164`，`VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP`，`usb_tx=0`，`cross_model_flash_authorized=False`） |
| 全量 `outputs/fx3-safety/tests` discovery | `5,146` 项安全测试 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（Normal `5,146/5,146 OK` `1069.87s`；Clean-Room `5,146 OK (skipped=10)` `920.75s`，`0` 失败） |
| `make verify-milestone-375`（双模） | 上游主闭环自动发现 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（`status=OK`，`pillars=6/6`，自动发现 `gate160=161/164`，`leaked=0`） |
| `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | 仓库洁净度与字节码审计 | 离线 | `ALL GREEN`（零未跟踪二进制，零 `.pyc`，仅含 6 个受控文件） |
