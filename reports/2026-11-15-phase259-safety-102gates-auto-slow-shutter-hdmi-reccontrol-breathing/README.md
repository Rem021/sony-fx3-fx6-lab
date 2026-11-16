# Phase 259 安全护栏报告：Safety Gates G101 / G102 与统一 `verify-102-gates` 预检引擎（`outputs/fx3-safety/`，Wave-41）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-41 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）安全门禁 `G101`、`G102` 与统一 `102` 门主预检引擎（`G01..G102`）闭环交付**：
   - 新增模块 [`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py)（Schema `realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard_v1` `v1.0.0`），将 `G01..G100` 直接委托给 [`evaluate_100gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py#L2077-L2327)（`100%` 保留 `verify-58-gates` 至 `verify-100-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 259 符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-auto-slow-shutter-breathing-comp-guard` / `verify-g101-auto-slow-shutter-breathing`、`verify-hdmi-reccontrol-tcout-4chaudio-guard` / `verify-g102-hdmi-reccontrol-4chaudio` 与 `verify-102-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/tests/test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py) 共 **68 项**双模式单元测试（要求 `< 4s`），在 `LOCAL_DONOR_O_RDONLY`（`3.926s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.535s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2403/2403` 全部通过（`152.354s`）**，Clean-Room 合成模式 **`2402` 项通过、`1` 项按设计跳过（`99.237s`）**；
   - CLI `verify-102-gates`：默认离线模式通过 **`99/102`**（`VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0`，3 道物理台架 Tier-0 收据门禁待接入真机离线只读证据），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`102/102`**（`VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP`）；
   - 跨模块里程碑与 BYOF 卫生检查：`make verify-milestone-233` 与 `make verify-milestone-221` 双模 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（`0.06s`，零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G101 与 Gate G102 技术建模要点（Wave-41 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase259_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L822-L982) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、FX3 `libgpe.so`、FX3 `libSaveLoadSettings.so`、FX3 `FX3-CX95900_ALLLANG-Backup.bin`、FX6 `libInfraDial.so` 与 FX6 `CX95898_NTSC.bin`），保证 `< 0.10s` 与 `raw_firmware_bytes_leaked == 0`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 缺省时自动切换为确定性 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G101：`G101_auto_slow_shutter_6lock_angle_disjoint_and_breathing_comp_guard`
- **`[Auto Slow Shutter]` 6 项精确禁能互锁与 `[Shutter Mode] = [Angle]` 严格互斥证明**：
  - [`resolve_fx3_auto_slow_shutter_and_breathing_comp_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L1094-L1187) 与 [`verify_auto_slow_shutter_and_breathing_comp_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L1191-L1590) 建模 `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]`（`On` 出厂默认 / `Off`，受 `[Camera Settings Reset]` 与 `[Initialize]` 复位、不受 `[Reset Network Set.]` 影响），强制执行索尼官方全部 6 项禁能条件（`S&Q`、`Shutter Priority`、`Manual Exposure`、`[ISO] != [ISO AUTO]`、`[Flexible Exp. Mode]` 手动快门、`[Log Shooting]` = `Cine EI Quick` / `Cine EI`；`auto_slow_shutter_lockout_bypass_events == 0`），并通过 [`compute_auto_slow_shutter_angle_disjointness_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L1043-L1091) 穷举 `320` 组视频曝光状态证明其与 `Ver. 7.02` `[Shutter Mode] = [Angle]` 严格互斥（`auto_slow_shutter_angle_overlap_events == 0`）。
- **`[Lens Compensation] -> [Breathing Comp.]` 视频专属兼容镜头裁切与 `4264x2408` `RAW` / `S&Q` `239.76p`/`200p` 锁定**：
  - 建模 `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（`Off` 出厂默认 / `On`，受 `[Camera Settings Reset]` 复位），仅在 `Movie` 模式且装载支持呼吸补偿的索尼 E 卡口镜头时启用轻微视角裁切，并在 `4264x2408` `RAW Output` 及 `S&Q` `239.76p`/`200p` 下强制禁能（`breathing_comp_raw_or_240p_bypass_events == 0`）。

### 2.3 Gate G102：`G102_hdmi_rec_control_tcout_4chaudio_and_slot1_rec_media_vault_guard`
- **`[HDMI Output Settings]` 跨双复位持久留存与 `[REC Control]` <- `[Time Code Output] = [On]` 前置依赖**：
  - [`resolve_fx3_hdmi_reccontrol_tcout_4chaudio_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L1677-L1758) 与 [`verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L1762-L2119) 校验 `MENU -> Setup -> [External Output] -> [HDMI Output Settings]` 跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存（仅由 `[Initialize]` 恢复出厂默认），并强制 `[REC Control]`（`Off` 默认 / `On`）必须在 `[Time Code Output] = [On]` 时方可启用（`hdmi_rec_ctrl_without_tc_violations == 0`）。
- **`[4ch Audio Output]` 声道映射与 `[Rec. Media dur HDMI Output]` Slot-1 Tier-0 恢复金库防写保护**：
  - 校验 `[4ch Audio Output]` 在 4 声道 MI 热靴音频激活时按 `CH1/CH2`（默认 -> `CH1=L/CH2=R`）与 `CH3/CH4`（`CH3=L/CH4=R`）路由 HDMI 立体声对；当 `[Rec. Media dur HDMI Output] = [Off]` 时抑制机内 Slot-1/Slot-2 素材与 `[Proxy Recording]` 代理写入，确保 Slot-1 Tier-0 恢复金库 `slot1_hdmi_rec_vault_mutation_bytes == 0`。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 冷备与恢复检查点门禁在离线默认模式下按设计保持待命阻断（`99/102`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 259 双模式定向单测（68 项 $\times$ 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `68/68 OK`（`3.926s`）+ `68/68 OK`（`1.535s`），均 `< 4s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2403 tests in 152.354s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2403 tests in 99.237s — OK (skipped=1)` |
| CLI `verify-102-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-102-gates`（及 `--force-clean-room`） | `verified=99/102`（`VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-102-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-102-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=102/102`（`VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`4a81cc38afb8460e...`）+ `CLEAN_ROOM_SYNTHETIC`（`408ca0ba5b976baa...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`df1ca089d7bd19dd...`）+ `CLEAN_ROOM_SYNTHETIC`（`a18ab79f958d6cf0...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（`0.06s`，零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/outputs/fx3-safety/tests/test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py)
6. [`reports/2026-11-15-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h292-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/reports/2026-11-15-phase259-safety-102gates-auto-slow-shutter-hdmi-reccontrol-breathing/README.md)
