# Phase 256 里程碑安全护栏报告：`100/100` GRAND MILESTONE Safety Gates G99 / G100 与统一 `verify-100-gates` 预检引擎（`outputs/fx3-safety/`，Wave-40）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-40 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）安全门禁 `G99`、第 `100` 道大里程碑门禁 `G100` 与统一 `100/100` 主预检引擎（`G01..G100`）闭环交付**：
   - 新增模块 [`realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py)（Schema `realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard_v1` `v1.0.0`），将 `G01..G98` 直接委托给 [`evaluate_98gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L1809-L2035)（`100%` 保留 `verify-58-gates` 至 `verify-98-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 256 符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-diff-set-still-mv-shutter-angle-guard` / `verify-g99-diff-set-still-mv`、`verify-custom-key-dial-remain-shoot-guard` / `verify-g100-custom-key-remain-shoot` 与 `verify-100-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase256_milestone_100gate_diff_set_custom_key_remain_shoot_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/tests/test_phase256_milestone_100gate_diff_set_custom_key_remain_shoot_guard.py) 共 **70 项**双模式单元测试（要求 `< 4s`），在 `LOCAL_DONOR_O_RDONLY`（`3.869s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.600s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2335/2335` 全部通过（`157.865s`）**，Clean-Room 合成模式 **`2334` 项通过、`1` 项按设计跳过（`88.845s`）**；
   - CLI `verify-100-gates`：默认离线模式通过 **`97/100`**（`VERIFIED_97_OF_100_AWAITING_PHYSICAL_TIER0`，仅 3 道物理台架 Tier-0 收据门禁待接入真机离线只读证据），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`100/100`**（`VERIFIED_ALL_100_GATES_DRY_RUN_SIMULATED_BACKUP`）；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-233` 与 `make verify-milestone-221` 双模 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（`0.04s`，零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G99 与 Gate G100 技术建模要点（Wave-40 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase256_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L696-L819) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、FX3 `libgpe.so`、FX3 `libSaveLoadSettings.so`、FX3 `FX3-CX95900_ALLLANG-Backup.bin`、FX6 `libInfraDial.so` 与 FX6 `libInfraInput.so`），保证 `< 0.10s` 与 `raw_firmware_bytes_leaked == 0`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 缺省时自动切换为确定性 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G99：`G99_diff_set_still_mv_8item_transitions_and_shutter_angle_override_guard`
- **精确 8 项可勾选目录与跨双复位留存**：
  - [`resolve_fx3_diff_set_still_mv_and_shutter_angle_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L827-L959) 与 [`verify_diff_set_still_mv_and_shutter_angle_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L962-L1254) 严格锁定 `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` 精确 8 项（`Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`），跨 **`[Camera Settings Reset]` 与 `[Reset Network Set.]`** 完整留存，仅在 **`[Initialize]`** 时恢复为未勾选出厂默认（违例阻断：`BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION`）。
- **非对称双向状态跃迁与 `[Shutter Mode] = [Angle]` 独立覆盖**：
  - `Common -> Separate` 将当前值复制到照片与视频寄存器，**唯独 `Custom White Balance` 仅作用于照片拍摄**（违例阻断：`BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION`）；
  - `Separate -> Common` 将参数恢复为初始出厂默认，**唯独 `Aperture`、`Shutter Speed` 与 `Custom White Balance` 保留照片端设定值**（`diff_set_transition_corruption_events == 0`，违例阻断：`BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION`）；
  - 当 `Ver. 6.00+` / `Ver. 7.02` 视频 `[Shutter Mode] = [Angle]` 时，即便 `Shutter Speed` 未勾选（设为 Common），照片快门速度与视频快门角度依然独立运行（`shutter_angle_common_bleed_events == 0`，违例阻断：`BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION`）。

### 2.3 Gate G100（第 `100` 道里程碑门禁）：`G100_custom_key_dial_iso_ei_firewall_and_remain_shoot_evf_less_guard`
- **`[Custom Key/Dial Set.]` 三域键位、`ISO/EI` 自适应与 Slot-1 `CAMSET01.DAT` `O_RDONLY` 防火墙**：
  - [`resolve_fx3_custom_key_dial_and_remain_shoot_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L1343-L1429) 与 [`verify_custom_key_dial_iso_ei_and_remain_shoot_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L1432-L1705) 完整校验 `Still`/`Movie`/`Playback` 三域键位、电影机线三拨轮出厂默认（`Front dial=Aperture`、`Rear dial=ISO/EI` 在 `Off`/`Flexible ISO` 与 `Cine EI`/`Cine EI Quick` 间自动切换 `ISO` 与 `Exposure Index (EI)`、`Control Wheel=Shutter Speed`）、视频 `[Follow Custom]` 继承、`[My Dial 1..3]` / `[Recall Custom hold 1..3]`、跨双复位持久留存，以及 Slot-1 Tier-0 `CAMSET01.DAT`..`CAMSET10.DAT` `os.O_RDONLY` 只读加载防火墙（`slot1_custom_key_vault_mutation_bytes == 0`，违例阻断：`BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION`）。
- **`[Remain Shoot Display]` 连拍缓存边界与无 EVF `ILME-FX3`（`ilc/2210`）监视拓扑护栏**：
  - 严格建模 `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]`（`Not Displayed` 出厂默认 / `Always Display` / `Shoot-Only Display`）仅表征照片连拍缓存余量（`displays_movie_card_remaining_time == False`）且跨双复位留存；同时硬锁 `ILME-FX3` 无内置 EVF、无 `[Finder/Monitor]` 切换与眼控传感器（`fx3_has_builtin_evf == False`、`evf_finder_monitor_spoof_events == 0`，违例阻断：`BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 冷备与恢复检查点门禁在离线默认模式下按设计保持待命阻断（`97/100`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 256 双模式定向单测（70 项 $\times$ 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase256_milestone_100gate_diff_set_custom_key_remain_shoot_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `70/70 OK`（`3.869s`）+ `70/70 OK`（`1.600s`），均 `< 4s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2335 tests in 157.865s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2335 tests in 88.845s — OK (skipped=1)` |
| CLI `verify-100-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-100-gates`（及 `--force-clean-room`） | `verified=97/100`（`VERIFIED_97_OF_100_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-100-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-100-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=100/100`（`VERIFIED_ALL_100_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`85d439e5e7bd7585...`）+ `CLEAN_ROOM_SYNTHETIC`（`f8c954d005686053...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`d319eb98ba63141d...`）+ `CLEAN_ROOM_SYNTHETIC`（`3ffbdc61203295f7...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（`0.04s`，零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase256_milestone_100gate_diff_set_custom_key_remain_shoot_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/outputs/fx3-safety/tests/test_phase256_milestone_100gate_diff_set_custom_key_remain_shoot_guard.py)
6. [`reports/2026-11-15-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h288-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/reports/2026-11-15-phase256-milestone-safety-100gates-diff-set-still-mv-custom-key-remain-shoot/README.md)
