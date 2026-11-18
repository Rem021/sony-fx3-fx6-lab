# Phase 290 里程碑安全护栏报告（290th Phase Milestone · Task H337 · Wave-52 `124`-Gate Preflight）：`G123` / `G124` 与统一 `verify-124-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 290（第 290 期里程碑 · Task H337，Wave-52）闭环交付，将官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01`（`5-024-458-18`）及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `BK4` 实机情报转化为确定性安全门禁 `G123`、`G124` 与统一 `124` 门主预检引擎（`G01..G124`）**：
   - 新增模块 [`realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py)（Schema `realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard_v1` `1.0.0`），零重复委托 `G01..G122` 给 [`evaluate_122gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)（Phase 290 增量 11 项 `O_RDONLY` 审计实测冷启动 **`0.0041s`**、缓存命中 **`0.0020s–0.0021s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/__init__.py)（完整导出 Phase 290 模块及 184 项非遮蔽符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-sensor-cleaning-and-ev-comp-guard` / `verify-g123-sensor-cleaning-ev-comp`、`verify-focus-mode-and-playback-rotate-guard` / `verify-g124-focus-mode-playback-rotate` 与 `verify-124-gates`，支持 `--simulate-bench-dry-run` / `--json` / `--summary` / `--clean-room`，且全部 `argparse` `help=`/`description=` 字符串均将 `%` 转义为 `%%` 以兼容 Python 3.14）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/README.md) 第 62 节。
2. **三模式 82 项双模单测、全量 3,237 项套件、`verify-124-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_124gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_124gate_guard.py) 共 **82 项**双模单元测试（满足 `>= 80` 项；全量 `subprocess` 使用 `sys.executable`，覆盖 `--help` Python 3.14 百分比转义校验，`GITHUB_ACTIONS=true` 含 `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`8.868s`）、`FX3_CLEAN_ROOM_TEST=1`（`8.755s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`8.924s`）下均 **`82/82 OK`**；
   - 全量 `outputs/fx3-safety/tests` 发现测试实测 **`Ran 3237 tests in 115.145s`**（`OK`，`rc=0`）；
   - CLI `verify-124-gates`：默认离线模式通过 **`121/124`**（`VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `--clean-room` 下均通过 **`124/124`**（`VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_124_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`4b3877f3bbd763d4...` / `9a76f92abb392134...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.04s`，`make clean-audit` 实测 `ALL GREEN in 0.04s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G123` 与 Gate `G124` 技术建模要点（Wave-52 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase290_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **11 份** Wave-52 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，23 个 Wave-52 切片 `os.pread` SHA-256 `6a8a875d77ef5bc5efb835613e9c1ac3478f3632af9f1973e543d2f48f2db318`）；
  - `FX6 appFw.so`（`50,520,424 B`，6 个 Wave-52 切片 `os.pread` SHA-256 `37104e43426ca7f3a6af36fbba7dd0f1ecef8f85a6dcd8cab9ead5160ace71f2`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` `resid16` 对齐校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- `raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G123`：`GATE_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_GUARD`
- **`[Sensor Cleaning]`（`>= 51%` `NP-FZ100` 电量门槛 & 强制物理关机 `OFF` vs `FX6` e-ND 光学组件隔离）**：
  - 对应 `ILME-FX3 Ver. 2.00+/7.02` `MENU -> Setup -> [Setup Option] -> [Sensor Cleaning]`（`_f.uxc` `0x67d6`；旧 `.uxc` `0xe7d7` `Cleaning Mode`、`FUNC_set_cleaning_mode`）：要求 `NP-FZ100 >= 51%` 剩余电量（pre-Ver. 2.00 为 `>= 3` 格；`< 51%` 通过 `INSUFFICIENT_BATTERY_CLEANING_MODE` / `Power insufficient.` `.uxc` `0xe574` 故障闭锁拒绝）；触发 5 轴 IBIS 载台微振与居中锁定，并强制要求物理电源开关 **`OFF`**（`_g.uxc` `0x6221`）后方可使用手动气吹清洁（严禁压缩空气，严禁在活跃 Tier-0 `p3` 备份、开放挂载或录制中执行，`BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION`）。
  - 故障闭锁对比 `ILME-FX6 Ver. 6.01`（`CHAPLIN`）：**无 IBIS**（`fx6_has_ibis=False`），CMOS 传感器前方为 **电子无级 ND 滤镜总成（`1/4..1/128` + `CLEAR`）**，提供 `Technical > APR`，且 Sony CrSDK 标记 `CrCommandId_SensorCleaning`（`320`）不受支持（严禁将 FX3 IBIS 清洁指令交叉映射至 FX6 e-ND 硬件，`BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION`）。
- **`[Exposure Comp.]`（Still `±5.0 EV` / Movie `±2.0 EV`、`[Exposure step]`、`M` + 固定 ISO 禁用、及 `[Cine EI]`/`[Cine EI Quick]` 100% 锁死）**：
  - 强制 Still `-5.0 EV .. +5.0 EV` 与 Movie/`S&Q` `-2.0 EV .. +2.0 EV` 边界、`[Exposure step]`（`0.3EV` 默认 / `0.5EV`，跨 `[Camera Settings Reset]` 保留且不改变 `[Shutter Mode] = [Angle]`）、`[Exposure Std. Adjust]`（`-1.0 .. +1.0 EV` 按 `1/6 EV` 步进），拦截无拨盘 FX3 `ilc/2210` 已剔除的休眠 Alpha `[Reset EV Comp.]`（`Maintain`/`Reset`）伪造；
  - 在 `Intelligent Auto (iAuto)` 禁用，在 `M` 模式下**仅当 `ISO = ISO AUTO` 时生效**（`M` + 固定数值 ISO 禁用，`BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION`），并在 **`[Log Shooting] = Cine EI` / `Cine EI Quick` 下 100% 锁死**（强制 `EXPOSURE_MODE_MOVIE_M` + `Base ISO 800 / 12800`，预览亮度唯一路由至 `[Exposure Index]` + `[Display LUT]`，`BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION`）。经 [`compute_sensor_cleaning_and_ev_comp_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

### 2.3 Gate `G124`：`GATE_G124_FOCUS_MODE_AND_PLAYBACK_ROTATE_SLOT1_GUARD`
- **`[Focus Mode]` Still 5 模式 vs Movie/`S&Q` 2 模式分离、`[Priority Set in AF-S/AF-C]`、`[AF Assist]` 与 `[AF Illuminator]`**：
  - Still 支持 5 模式（`Single-shot AF`、`Automatic AF` 默认、`Continuous AF`、`DMF`、`Manual Focus`；拦截休眠 `PF` / `SEMI_MANUAL`），而 Movie/`S&Q` 严格收敛为 **2 模式**（`Continuous AF` 内部枚举编码为 `MOVIE_AUTO` + `Manual Focus`；拒绝 Movie/`S&Q` 下的 `AF-S` / `AF-A` / `DMF`，`BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION`）；
  - `[AF Assist]`（`On/Off`，`_f.uxc` `0x64a9`）严格限定于 Movie/`S&Q` `AF-C`（`MOVIE_AUTO`）；Still 专属 `[Priority Set in AF-S/AF-C]`（`AF / Release / Balanced Emphasis`，跨 `[Camera Settings Reset]` 保留）；Still 专属 `[AF Illuminator]`（`Auto/Off`，`.uxc` `0xe07f`）在 Movie/`S&Q`/`AF-C`/对焦放大/卡口转接环下硬锁定（`BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION`）；并对比 `ILME-FX6 Ver. 6.01` 的 `AF/MF` 与 `Push AF Mode`（无 `AF-A`/`DMF`/`AF Illuminator`）。
- **`[Playback]` `[View Mode]`、`[Image Index]`（`9/25` vs 休眠 `12/30`）、`[Display as Group]`、`[Display Rotation]` 与 `[Rotate]` `Slot-1` 只读保险库防火墙**：
  - 强制 `[View Mode]` 仅限 `Date View`（默认）、`Folder View(Still)`、`Movie View`（拦截休眠 `AVCHD View` / `Folder View(MP4)` / `Mov. View by File Format`）；`[Image Index]` 仅限 `9 Images`（默认）与 `25 Images`（拦截休眠 `12_IMAGES` / `30 Images` `_f.uxc` `0x6e7a`，`BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION`）；
  - 记录 `[Display as Group]` 群组删除将连带删除整组连拍/间隔拍摄照片，以及 `[Display Rotation]`（`Auto/Manual/Off`，`BKID_APP_setting_display_rotatiton`）；由于 `[Select Playback Media]` 默认指向 `Slot 1` 且 `[Rotate]`（`FUNC_rotate_content`）会直接原地改写存储卡文件 EXIF 方向元数据，一旦 `Slot 1` 为只读/写保护或承载 Tier-0 恢复保险库即硬阻断 `[Rotate]` 与群组删除（返回 `EROFS`；后台传输或影片文件返回 `EBUSY`/`EINVAL`，`BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION`）。经 [`compute_focus_mode_and_playback_rotate_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`121/124`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 290 双模定向单测（82 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_124gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `82/82 OK`（Donor `8.868s`）+ `82/82 OK`（`FX3_CLEAN_ROOM_TEST=1` `8.755s`）+ `82/82 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `8.924s`） |
| CLI `G123` / `G124` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-sensor-cleaning-and-ev-comp-guard` / `verify-focus-mode-and-playback-rotate-guard`（含 `--summary --json`） | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 冷启动 `0.0041s`，缓存 `0.0020s–0.0021s`） |
| CLI `verify-124-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-124-gates --summary --json`（及 `--clean-room`） | `verified=121/124`（`VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`cross_model_flash_authorized=False`，`rc=0`） |
| CLI `verify-124-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-124-gates --simulate-bench-dry-run --summary --json`（及 `--clean-room`） | `verified=124/124`（`VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_124_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`4b3877f3bbd763d4...`）+ `CLEAN_ROOM_SYNTHETIC`（`9a76f92abb392134...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_*.py'` | `Ran 3237 tests in 115.145s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | `ALL GREEN in 0.04s` & `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_124gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/outputs/fx3-safety/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_124gate_guard.py)
6. [`reports/2026-11-17-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h337-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/reports/2026-11-17-phase290-milestone-safety-124gates-sensor-cleaning-ev-comp-focus-mode-playback-rotate/README.md)
