# Phase 237 安全护栏里程碑报告：`90/90` Safety Gates G89 / G90 与统一 `verify-90-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-35 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G89`、`G90` 与统一 `90/90` 里程碑主预检引擎（`G01..G90`）闭环交付**：
   - 新增模块 [`realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py)（将 `G01..G88` 直接委托给 [`evaluate_88gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L2041-L2263)，`100%` 保留 `verify-58-gates` 至 `verify-88-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase237_emphasized_rec_grid_hdmi_touch_sunny_90gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/tests/test_phase237_emphasized_rec_grid_hdmi_touch_sunny_90gate_guard.py) 共 **66 项**双模式单元测试（要求 `>=58`），在 `LOCAL_DONOR_O_RDONLY`（`5.793s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.190s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1997/1997` 全部通过（`124.885s`）**，Clean-Room 合成模式 **`1996` 项通过、`1` 项按设计跳过（`72.937s`）**；
   - CLI `verify-90-gates`：默认离线模式通过 **`87/90`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`90/90`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（零 `.pyc`、零专有固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G89 与 Gate G90 技术建模要点（Wave-35 规范映射）

### 2.1 Gate G89：`EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD`
- **`[Emphasized REC Display]` 与 `[Grid Line Display]` 的非对称重置分裂与 HDMI 路由能力**：
  - [`resolve_fx3_emphasized_rec_and_grid_hdmi_routing()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L1002-L1093) 与 [`verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L1096-L1479) 精确建模 `ILME-FX3` 显示辅助叠加层的路由与重置边界：
    - `[Emphasized REC Display]`（`MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]`，出厂默认 `On`）：仅在 Movie / S&Q 录制期间点亮四周红框（静止图像与待机为 `False`），且**会被 `[Camera Settings Reset]` 重置回 `On`**（违例阻断为 `BLOCKED_G89_EMPHASIZED_REC_INVALID_OR_RESET_MISMATCH`）；
    - `[Grid Line Display]`（出厂默认 `Off`）与 `[Grid Line Type]`（`Rule of 3rds Grid` 默认 / `Square Grid` / `Diag. + Square Grid`）：**在 `[Camera Settings Reset]` 后原样保留**，仅在 `[Initialize]` 时恢复出厂值（违例阻断为 `BLOCKED_G89_GRID_LINE_INVALID_OR_RESET_SURVIVAL_VIOLATION`）；
    - 当 `[HDMI Info. Display]=On` 且未触发硬件净流钳位时，`[Emphasized REC Display]` 红框与 `[Grid Line Display]` 网格线均可随 OSD 路由至外接 HDMI 监视器（同时机内 LCD 图像熄隐），与**始终仅限机内 LCD 显示**的 `[Marker Display]`、`[Zebra Display]`、`[Peaking Display]` 形成严格分层（任何本地专属辅助层泄漏至 HDMI 即触发 `BLOCKED_G89_LOCAL_ONLY_ASSIST_HDMI_LEAK_OR_ROUTING_MISMATCH`）。
- **`[Off(HDMI Only)]` 与 HDMI `RAW` 双硬件强制 Clean-Feed 钳位**：
  - 只要 `[Rec. Media dur HDMI Output]` 设为 `[Off(HDMI Only)]` **或**开启 HDMI `RAW` 短片输出，固件即在硬件层临时将生效 `[HDMI Info. Display]` 强制钳位为 `[Off]`，确保外接 HDMI 录机流中烧录的红框、网格线与 OSD 像素严格为 `0`（`hdmi_stream_baked_overlay_pixels == 0`，越界即触发 `BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_VIOLATION`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase237_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L844-L999) 以只读描述符校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成模式。

### 2.2 Gate G90：`TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD`
- **`[Touch Operation]` 全套 4 项跨 `[Camera Settings Reset]` 存活与无人值守台架防误触锁**：
  - [`resolve_fx3_touch_op_4item_reset_and_bench_lock()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L1565-L1611) 与 [`verify_touch_op_reset_and_sunny_weather_bench_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L1659-L1994) 完整覆盖 `MENU -> Setup -> [Touch Operation]` 4 项配置：
    - `[Touch Operation]`（`On` 默认 / `On: Playback Only` / `Off`）、`[Touch Sensitivity]`（`Standard` 默认 / `Sensitive`）、`[Swipe Up]`（`Open the Fn Menu` 默认 / `Off`）与 `[Touch Func. in Shooting]`（`Touch Tracking` 默认 / `Touch Focus` / `Off`）全部**跨 `[Camera Settings Reset]` 原样保留**，仅在 `[Initialize]` 时恢复出厂默认（违例阻断为 `BLOCKED_G90_TOUCH_OP_4ITEM_ENUM_OR_RESET_SURVIVAL_VIOLATION`）；
    - 在无人值守 Tier-0 冷备台架运行期间，强制要求 `[Touch Operation]` 锁定为 `Off`（或 `On: Playback Only`），严防排线接触或电容噪声意外触发上滑打开 `Fn` 菜单或激活 `Touch Tracking` / `Touch Focus`（违例阻断为 `BLOCKED_G90_UNATTENDED_BENCH_SHOOTING_TOUCH_UNLOCKED`）。
- **`[Monitor Brightness]` 重置存活与室内台架 `[Sunny Weather]` 禁令**：
  - [`resolve_fx3_monitor_brightness_reset_and_sunny_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py#L1614-L1656) 校验 `MENU -> Setup -> [Monitor] -> [Monitor Brightness]`（`Manual` `-2..+2` 默认 `±0` vs `Sunny Weather`）：
    - 在 `[Camera Settings Reset]` 后原样保留（若重置前遗留 `Sunny Weather`，重置后依旧处于高功耗高亮态），仅在 `[Initialize]` 时回到 `Manual (±0)`（违例阻断为 `BLOCKED_G90_MONITOR_BRIGHTNESS_ENUM_OR_RESET_VIOLATION`）；
    - 在室内 `NP-FZ100` 电池供电台架会话中严禁开启 `[Sunny Weather]`，避免画面过亮引发曝光误判并消除额外 LCD 背光发热与电池压降风险（违例阻断为 `BLOCKED_G90_INDOOR_NP_FZ100_BENCH_SUNNY_WEATHER_ACTIVE`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并零错误退出。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读（`G10..G12`）仍按设计处于离线待命阻断状态（`87/90`），唯有人工作业台架提供真机 SHA-256 回读收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 237 双模式定向单测（66 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase237_emphasized_rec_grid_hdmi_touch_sunny_90gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `66/66 OK`（`5.793s`）+ `66/66 OK`（`2.190s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1997 tests in 124.885s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1997 tests in 72.937s — OK (skipped=1)` |
| CLI `verify-90-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-90-gates`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=87/90`（`VERIFIED_87_OF_90_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-90-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-90-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=90/90`（`VERIFIED_ALL_90_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase237_emphasized_rec_grid_hdmi_touch_sunny_90gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/outputs/fx3-safety/tests/test_phase237_emphasized_rec_grid_hdmi_touch_sunny_90gate_guard.py)
6. [`reports/2026-11-15-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h263-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/reports/2026-11-15-phase237-safety-90gates-emphasized-rec-grid-hdmi-touch-sunny/README.md)
