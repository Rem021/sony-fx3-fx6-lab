# Phase 230 安全护栏报告：Gates G85 / G86 与统一 `verify-86-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-33 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G85`、`G86` 与统一 `86-Gate` 主预检引擎（`G01..G86`）闭环交付**：
   - 新增模块 [`realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py)（将 `G01..G84` 直接委托给 [`evaluate_84gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1991-L2213)，`100%` 保留 `verify-58-gates` 至 `verify-84-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase230_silent_autopixelmap_marker_flexexp_86gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/tests/test_phase230_silent_autopixelmap_marker_flexexp_86gate_guard.py) 共 **62 项**双模式单元测试（要求 `>=56`），在 `LOCAL_DONOR_O_RDONLY`（`4.950s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.465s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1867/1867` 全部通过（`112.954s`）**，Clean-Room 合成模式 **`1866` 项通过、`1` 项按设计跳过（`68.459s`）**；
   - CLI `verify-86-gates`：默认离线模式通过 **`83/86`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`86/86`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G85 与 Gate G86 技术建模要点（Wave-33 规范映射）

### 2.1 Gate G85：`G85_SILENT_MODE_AUTO_PIXEL_MAPPING_TARGET_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD`
- **`[Silent Mode]` 强制快门/提示音锁与 5 项功能硬件级禁用矩阵**：
  - [`resolve_fx3_silent_mode_and_target_functions()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L999-L1091) 与 [`verify_silent_mode_autopixelmap_and_no_pwrshutter_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1094-L1396) 精确建模 `MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Silent Mode] = [On]`：启用静音模式后，强制将 `[Shutter Type]` 与 `[Shutter Type in Interval]` 锁死在 `[Electronic Shutter]`，将 `[Audio signals]` 锁死在 `[Off]`，并同时禁用全部 5 项冲突功能（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`）；任何绕过锁或禁用矩阵缺失均触发 `BLOCKED_G85_SILENT_MODE_LOCK_OR_DISABLED_5FUNC_VIOLATION`。
- **`[Target Function Settings]` 对 `[Aperture Drive in AF]` 与 `[Auto Pixel Mapping]` 的独立接管及台架断电暗场机械快门抑制**：
  - 精确校验 `[Target Function Settings]` 子菜单对 `[Aperture Drive in AF]`（`Not Target` / `Standard` / `Focus Priority` / `Silent Priority`）与 `[Auto Pixel Mapping]`（`Not Target` / `Off`）的联动语义：`[Not Target]` 保留常规设置，而在物理台架上下电循环期间强制将 `[Auto Pixel Mapping]` 设为 `[Off]`（或将基础 `[Auto Pixel Mapping]` 设为 `Off`），确定性抑制断电自动暗场机械快门闭合动作与潜在 `cnflasha` 坏点表更新访问（违例阻断为 `BLOCKED_G85_TARGET_FUNCTION_OR_BENCH_AUTO_PIXEL_MAPPING_VIOLATION`）。
- **物理 `ILME-FX3` 无 `[Shutter When Pwr OFF]` 菜单项防幻觉校验**：
  - 严格校验 `ILME-FX3`（`Ver. 2.00..7.02`）`MENU -> Setup -> [Setup Option]` 仅暴露 `[Sensor Cleaning]`、`[Auto Pixel Mapping]` 与 `[Pixel Mapping]` 3 项传感器维护入口，绝不存在 α7 IV / α1 / α7R V 系列的 `[Shutter When Pwr OFF]` 防尘快门菜单；任何伪造该菜单项或声称关机防尘快门常闭的输入均触发 `BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM`。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase230_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L843-L990) 以只读描述符校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成模式。

### 2.2 Gate G86：`G86_MARKER_DISPLAY_15RATIO_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD`
- **`[Marker Display]` 15 档画幅比例、机身本地 LCD 独占与跨 `[Camera Settings Reset]` 存活持久性**：
  - [`resolve_fx3_marker_display_hdmi_and_reset()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1484-L1552) 与 [`verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1609-L1946) 校验 `MENU -> Shooting -> [Marker Display]` 全量参数：
    - `[Center Marker]`（`Off`/`On`）、`[Safety Zone]`（`Off`/`80%`/`90%`）、`[Guideframe]`（`Off`/`On`）；
    - `[Aspect Marker]`：`Off` + 官方 `Ver. 3.00+ / 7.02` 全部 **15 种画幅比例**（`9:16`、`4:5`、`1:1`、`4:3`、`13:9`、`14:9`、`15:9`、`16:9`、`17:9`、`1.66:1`、`1.85:1`、`1.91:1`、`2:1`、`2.35:1`、`2.39:1`，其中竖拍/社交画幅 `9:16`/`4:5` 与 `2:1`/`1.66:1`/`1.91:1`/`17:9` 校验固件 `>= 3.00`）；
    - **本地 LCD 独占与 HDMI 零标记隔离**：所有构图标记绝不通过外接 HDMI 输出（`hdmi_marker_overlay_frames == 0`），即便开启 `[HDMI Info. Display] = [On]`（此时机身 LCD 黑屏，外接 HDMI 仅带文字信息 OSD 而不带构图框线，违例阻断为 `BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK_VIOLATION`）；
    - **非对称重置持久性**：`[Marker Display]` 与 `[Aspect Marker]` 在 `[Camera Settings Reset]` 后原样保留，仅在 `[Initialize]` 全量出厂重置时归零为 `Off`。
- **`[Exposure Ctrl Type]`（`P/A/S/M Mode` vs `Flexible Exp. Mode`）在 `[Camera Settings Reset]` 下的重置分裂语义**：
  - [`resolve_fx3_flexible_exp_reset_split()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L1555-L1606) 精确建模 `MENU -> Shooting -> [Shooting Mode] -> [Exposure Ctrl Type]`：当切入 `[Flexible Exp. Mode]` 时，`[Auto/Manual Swt. Set.]`（`Av Switch Set.` / `Tv Switch Set.` / `ISO Switch Set.` 出厂默认均为 `Manual`）与 `[Auto Slow Shutter]`（出厂默认 `On`，且仅在存在至少一项自动曝光轴且光圈/快门处于自动控制条件时生效）**会被 `[Camera Settings Reset]` 重置回出厂默认值**（`Manual` / `Manual` / `Manual` + `Auto Slow Shutter = On`），与同次 `[Camera Settings Reset]` 下保持不变的 `[Marker Display]` / `[Aspect Marker]` 形成严格的非对称重置分裂契约（违例阻断为 `BLOCKED_G86_MARKER_OR_FLEXIBLE_EXP_RESET_SPLIT_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并零错误退出。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读（`G10..G12`）仍按设计处于离线待命阻断状态（`83/86`），唯有人工台架提供真机 SHA-256 回读收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 230 双模式定向单测（62 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase230_silent_autopixelmap_marker_flexexp_86gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `62/62 OK`（`4.950s`）+ `62/62 OK`（`1.465s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1867 tests in 112.954s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1867 tests in 68.459s — OK (skipped=1)` |
| CLI `verify-86-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-86-gates`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=83/86`（`VERIFIED_83_OF_86_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-86-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-86-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=86/86`（`VERIFIED_ALL_86_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.04s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase230_silent_autopixelmap_marker_flexexp_86gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/outputs/fx3-safety/tests/test_phase230_silent_autopixelmap_marker_flexexp_86gate_guard.py)
6. [`reports/2026-11-15-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h255-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/reports/2026-11-15-phase230-safety-86gates-silent-autopixelmap-marker-flexexp/README.md)
