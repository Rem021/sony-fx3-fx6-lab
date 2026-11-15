# Phase 249 安全护栏里程碑报告：`96/96` Safety Gates G95 / G96 与统一 `verify-96-gates` 预检引擎（`outputs/fx3-safety/`，Wave-38）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-38 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G95`、`G96` 与统一 `96/96` 主预检引擎（`G01..G96`）闭环交付**：
   - 新增模块 [`realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)（Schema `realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard_v1` `v1.0.0`），将 `G01..G94` 直接委托给 [`evaluate_94gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L1832-L2055)（`100%` 保留 `verify-58-gates` 至 `verify-94-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 249 符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-lock-op-parts-chord-guard`、`verify-audio-timing-exp-step-guard` 与 `verify-96-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase249_lock_op_parts_audio_timing_exp_step_96gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/tests/test_phase249_lock_op_parts_audio_timing_exp_step_96gate_guard.py) 共 **68 项**双模式单元测试（要求 `>=64` 且 `<5s`），在 `LOCAL_DONOR_O_RDONLY`（`3.501s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.585s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2197/2197` 全部通过（`141.176s`）**，Clean-Room 合成模式 **`2196` 项通过、`1` 项按设计跳过（`84.654s`）**；
   - CLI `verify-96-gates`：默认离线模式通过 **`93/96`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`96/96`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-233` 与 `make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测全绿（零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G95 与 Gate G96 技术建模要点（Wave-38 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase249_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L763-L914) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、`libgpe.so`、`FX3-CX95900_ALLLANG-Backup.bin`、`libInfraDial.so`、`libInfraInput.so` 与 `CX95898_NTSC.bin`），实测耗时 `0.036s`（`< 0.10s`）且保证 `raw_firmware_bytes_leaked == 0`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 路径缺省时自动切换为 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G95：`G95_lock_operation_parts_menu_fn_5s_chord_and_mydial_override_guard`
- **`[Lock Operation Parts]` 跨 `[Camera Settings Reset]` 留存契约**：
  - [`resolve_fx3_lock_operation_parts_and_chord_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L921-L980) 与 [`verify_lock_operation_parts_chord_and_mydial_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L983-L1346) 精确执行 `MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]`（默认 `Off`、`Multi-Selector Only` / `[Multi-Slct Only]`、`Dial + Wheel`、`All`）：作为 `[Setup]` 项在 `[Camera Settings Reset]` 后保持原设定不变，仅在 `[Initialize]` 时恢复为 `Off`（违例阻断：`BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION`）。
- **`Fn` 长按、`MENU + Fn` `5`s 整机物理控制锁 vs 破坏性 `MENU + Delete` `2`s 全盘格式化硬防火墙**：
  - 校验长按 `Fn` 按设定范围切换锁定并弹出 `"Locked."` 提示，再次长按解除（`Off` 下不锁定；违例阻断：`BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION`）；
  - 校验同时按住 **`MENU + Fn` 满 `5.0` 秒**锁定**除快门按钮外的全部机身按键、拨盘与拨轮**，并在无人值守 Tier-0 `pnflasha`/`cnflasha` 转储期间强制启用整机防误触锁（违例阻断：`BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION`、`BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED`）；
  - 硬防火墙 100% 拦截将破坏性 **`MENU + Delete` `2` 秒卡槽全盘格式化组合键**误用作锁键的行为（`destructive_menu_delete_confusions == 0`，违例阻断：`BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION`）；
  - 校验 **`My Dial` 临时召回解锁**：即使拨盘处于锁定态，召回 `My Dial` 期间临时解锁已分配拨盘并在释放后立即重新上锁（违例阻断：`BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION`）。

### 2.3 Gate G96：`G96_audio_out_timing_signals_persistence_and_exp_step_shutter_angle_guard`
- **`[Audio Out Timing]` vs `[Audio signals]` 复位分流与锁止契约**：
  - [`resolve_fx3_audio_timing_signals_and_exp_step_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L1438-L1506) 与 [`verify_audio_timing_signals_and_exp_step_shutter_angle_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L1509-L1942) 精确建模：
    - `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]`（默认 `Live` / `Lip Sync`）在 `[Camera Settings Reset]` 下复位为 `Live`（`BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION`），并在 `S&Q Motion` 或 `[Audio Recording]=Off` 时硬件锁止不可用（`BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION`）；
    - `MENU -> Setup -> [Sound Option] -> [Audio signals]`（默认 `On` / `Off`）跨 `[Camera Settings Reset]` 持久留存、仅受 `[Initialize]` 恢复为 `On`（`BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION`），但当 **`[Silent Mode]=On`** 时被硬件强制锁死为 `Off` 直至退出静音模式（`BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION`）。
- **`[Exposure step]`（`0.3EV` / `0.5EV`）与 `[Shutter Angle]` 恒定电影快门角度表正交免疫**：
  - 校验 `MENU -> Exposure/Color -> [Exposure Comp.] -> [Exposure step]`（默认 `0.3EV` / `0.5EV`，受 `[Camera Settings Reset]` 复位）仅控制 `[Shutter Speed]`、`Aperture` 与 `Exposure Comp.` 步进（`BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION`），而 **`[Shutter Mode]=Shutter Angle`（`Ver. 6.00+`）严格保持恒定电影快门角度表（`5.6°`..`360°`），完全不受 `[Exposure step]` 切换影响**（`shutter_angle_exposure_step_drift_events == 0`，违例阻断：`BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读门禁（`G10..G12`）在离线默认模式下按设计保持待命阻断（`93/96`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 249 双模式定向单测（68 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase249_lock_op_parts_audio_timing_exp_step_96gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `68/68 OK`（`3.501s`）+ `68/68 OK`（`1.585s`），均 `< 5s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2197 tests in 141.176s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2197 tests in 84.654s — OK (skipped=1)` |
| CLI `verify-96-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-96-gates`（及 `--force-clean-room`） | `verified=93/96`（`VERIFIED_93_OF_96_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-96-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-96-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=96/96`（`VERIFIED_ALL_96_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`58b78573227283a1...`）+ `CLEAN_ROOM_SYNTHETIC`（`4b1bf747fc3ebe7c...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`fc78fa0ab7269a8c...`）+ `CLEAN_ROOM_SYNTHETIC`（`fec5fe0bfd7482c5...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase249_lock_op_parts_audio_timing_exp_step_96gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/outputs/fx3-safety/tests/test_phase249_lock_op_parts_audio_timing_exp_step_96gate_guard.py)
6. [`reports/2026-11-15-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h280-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/reports/2026-11-15-phase249-safety-96gates-lock-op-parts-audio-timing-exp-step/README.md)
