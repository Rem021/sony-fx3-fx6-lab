# Phase 252 安全护栏里程碑报告：`98/98` Safety Gates G97 / G98 与统一 `verify-98-gates` 预检引擎（`outputs/fx3-safety/`，Wave-39）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-39 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）安全门禁 `G97`、`G98` 与统一 `98/98` 主预检引擎（`G01..G98`）闭环交付**：
   - 新增模块 [`realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py)（Schema `realhw_display_quality_bt_rmt_mymenu_and_98gate_guard_v1` `v1.0.0`），将 `G01..G96` 直接委托给 [`evaluate_96gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py#L2030-L2264)（`100%` 保留 `verify-58-gates` 至 `verify-96-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 252 符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-display-quality-bt-rmt-guard` / `verify-g97-display-quality-bt-rmt`、`verify-mymenu-camset-firewall-guard` / `verify-g98-mymenu-camset` 与 `verify-98-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase252_display_quality_bt_rmt_mymenu_98gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/tests/test_phase252_display_quality_bt_rmt_mymenu_98gate_guard.py) 共 **68 项**双模式单元测试（要求 `< 4s`），在 `LOCAL_DONOR_O_RDONLY`（`3.416s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.243s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2265/2265` 全部通过（`132.893s`）**，Clean-Room 合成模式 **`2264` 项通过、`1` 项按设计跳过（`85.591s`）**；
   - CLI `verify-98-gates`：默认离线模式通过 **`95/98`**（`VERIFIED_95_OF_98_AWAITING_PHYSICAL_TIER0`，仅物理台架 Tier-0 冷备回读门禁待接入真机收据），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`98/98`**（`VERIFIED_ALL_98_GATES_DRY_RUN_SIMULATED_BACKUP`）；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-233` 与 `make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测全绿（零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G97 与 Gate G98 技术建模要点（Wave-39 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase252_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L612-L735) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、FX3 `libInfraBluetooth.so`、FX3 `libInfraAirplaneMode.so`、FX3 `libSaveLoadSettings.so`、FX6 `libInfraBluetooth.so` 与 FX6 `libInfraSircs.so`），保证 `< 0.10s` 与 `raw_firmware_bytes_leaked == 0`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 路径缺省时自动切换为确定性 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G97：`G97_display_quality_battery_conservation_and_bt_rmt_ctrl_ir_lockout_guard`
- **`[Display Quality]` 跨双复位持久留存与内置 `NP-FZ100` 电池 Tier-0 节电钳位**：
  - [`resolve_fx3_display_quality_and_bt_rmt_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L743-L828) 与 [`verify_display_quality_battery_and_bt_rmt_ir_lockout_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L831-L1101) 精确执行 `MENU -> Setup -> [Monitor] -> [Display Quality]`（默认 `Standard` / `High`）：跨 **`[Camera Settings Reset]` 与 `[Reset Network Set.]`** 保持不变，仅在 **`[Initialize]`** 时恢复为 `Standard`（违例阻断：`BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION`）；
  - 在内置 `NP-FZ100` 电池驱动的 Tier-0 `pnflasha`/`cnflasha` 转储期间，强制钳位 `[Display Quality] = Standard` + `[Monitor Brightness] = Manual(0)`（`tier0_battery_high_display_violations == 0`，违例阻断：`BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN`）。
- **`[Bluetooth Rmt Ctrl]` 射频先决条件、红外遥控 `SIRCS` 互斥与三向复位分流**：
  - 精确建模 `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]`（默认 `Off` / `On`）：需同时满足 `[Bluetooth Function]=On` 与 `[Airplane Mode]=Off`（在零射频台架 `[Airplane Mode]=On` 下自动抑制且 `passive_tx_bytes_emitted == 0`；违例阻断：`BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION`）；
  - 当 `[Bluetooth Rmt Ctrl]=On` 时硬件互斥锁止红外遥控器（`SIRCS` 不可用，`bt_rmt_ir_lockout_violations == 0`，违例阻断：`BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION`）；
  - 精确执行三向复位分流：**跨 `[Camera Settings Reset]` 存活**，但在 **`[Reset Network Set.]` 与 `[Initialize]` 下均复位为 `Off`**（违例阻断：`BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION`）。

### 2.3 Gate G98：`G98_mymenu_6op_persistence_and_slot1_camset01_firewall_guard`
- **`[My Menu Setting]` 6 项子操作、`6×6=36` 容量上限与跨双复位非易失留存**：
  - [`resolve_fx3_mymenu_and_camset_firewall_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L1173-L1249) 与 [`verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py#L1252-L1501) 完整校验 `MENU -> My Menu -> [My Menu Setting]` 全部 6 项操作（`Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All` 与 `[Display From My Menu]` `Off`/`On`，上限 `6` 页 × `6` 项 `= 36` 项），并验证注册页面与 `[Display From My Menu]` **同时跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 持久留存**，仅由显式 `Delete All`/`Delete Page` 或全量 `[Initialize]` 清空（违例阻断：`BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION`、`BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION`、`BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION`）。
- **Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY` 只读加载防火墙**：
  - 保护期强制 Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT` 仅允许同机型 `ILME-FX3` `LOAD_O_RDONLY`（`os.O_RDONLY`）加载，`100%` 拦截 `SAVE_OVERWRITE`、任何写标志位、跨机型 `ILME-FX6` 设置文件及任何非零写入（`slot1_mymenu_vault_mutation_bytes == 0`，违例阻断：`BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **架构推断（Engineering Inference）**：物理真机 Tier-0 冷备回读门禁在离线默认模式下按设计保持待命阻断（`95/98`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 252 双模式定向单测（68 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase252_display_quality_bt_rmt_mymenu_98gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `68/68 OK`（`3.416s`）+ `68/68 OK`（`1.243s`），均 `< 4s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2265 tests in 132.893s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2265 tests in 85.591s — OK (skipped=1)` |
| CLI `verify-98-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-98-gates`（及 `--force-clean-room`） | `verified=95/98`（`VERIFIED_95_OF_98_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-98-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-98-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=98/98`（`VERIFIED_ALL_98_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`49e751b5e2be6d38...`）+ `CLEAN_ROOM_SYNTHETIC`（`04fbf6681dd457bd...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`225bc94946a1f7a2...`）+ `CLEAN_ROOM_SYNTHETIC`（`6d62e1bd50fd4f0b...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase252_display_quality_bt_rmt_mymenu_98gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/outputs/fx3-safety/tests/test_phase252_display_quality_bt_rmt_mymenu_98gate_guard.py)
6. [`reports/2026-11-15-phase252-safety-98gates-display-quality-bt-rmt-mymenu/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h283-phase252-safety-98gates-display-quality-bt-rmt-mymenu/reports/2026-11-15-phase252-safety-98gates-display-quality-bt-rmt-mymenu/README.md)
