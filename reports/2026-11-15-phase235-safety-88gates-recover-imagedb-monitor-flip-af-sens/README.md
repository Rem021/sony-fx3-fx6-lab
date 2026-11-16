# Phase 235 安全护栏报告：Gates G87 / G88 与统一 `verify-88-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-34 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G87`、`G88` 与统一 `88-Gate` 主预检引擎（`G01..G88`）闭环交付**：
   - 新增模块 [`realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py)（将 `G01..G86` 直接委托给 [`evaluate_86gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py#L2043-L2265)，`100%` 保留 `verify-58-gates` 至 `verify-86-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase235_recover_imagedb_monitor_flip_af_sens_88gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/tests/test_phase235_recover_imagedb_monitor_flip_af_sens_88gate_guard.py) 共 **64 项**双模式单元测试（要求 `>=56`），在 `LOCAL_DONOR_O_RDONLY`（`4.898s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.617s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1931/1931` 全部通过（`119.850s`）**，Clean-Room 合成模式 **`1930` 项通过、`1` 项按设计跳过（`78.231s`）**；
   - CLI `verify-88-gates`：默认离线模式通过 **`85/88`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`88/88`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.06s`（零 `.pyc`、零专有固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G87 与 Gate G86->G88 技术建模要点（Wave-34 规范映射）

### 2.1 Gate G87：`RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL`
- **`[Recover Image DB]` 非破坏索引修复、低电量硬件拒止与动作项免重置语义**：
  - [`resolve_fx3_recover_imagedb_battery_and_vault_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1010-L1072) 与 [`verify_recover_imagedb_depleted_battery_and_tier0_vault_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1075-L1331) 精确建模 `MENU -> Shooting -> [Media] -> [Recover Image DB]`：
    - 修复 `AVF_INFO` / 媒体管理数据库不一致（`"Image DataBase File error"`、误报 `"0"` 可拍张数、PC 侧编辑后索引失配）且**绝不删除任何已录制视频片段或照片**（`recorded_clips_deleted == 0`、`recorded_clips_after == recorded_clips_before`，违例阻断为 `BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH`）；
    - 当 `NP-FZ100` 电池处于极低电量（`battery_extremely_depleted == True`、`battery_soc_pct < 10` 或 `battery_mv < 6400`）时强制拒止执行，防止写卡中途断电导致 FAT/exFAT 目录断链（违例阻断为 `BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION`）；
    - 作为一次性即时动作项，严格免疫 `[Camera Settings Reset]` 与 `[Initialize]`，阻断任何将其伪造为可重置持久开关的错误声明（`BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM`）。
- **Slot 1 未校验 / `WP` 锁止 Tier-0 冷备卡只读防篡改防火墙**：
  - 由于 `[Recover Image DB]` 会向目标存储卡写入修复后的索引元数据，只要 Slot 1 插有活跃、处于 `WP` 硬件写保护锁止或尚未完成离机 SHA-256 哈希核验（`slot1_off_camera_sha256_verified == False`）的 Tier-0 冷备卡（`pnflasha` / `cnflasha` / `CAMSET01.DAT`），即硬锁禁止对 Slot 1 请求或执行 `[Recover Image DB]` 且要求 `slot1_metadata_sector_writes == 0`、`slot1_avf_info_mutated == False`（任何越界写均触发 `BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase235_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L858-L1001) 以只读描述符校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成模式。

### 2.2 Gate G88：`MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD`
- **`[Monitor Flip Direction]` 跨 `[Camera Settings Reset]` 存活与 `[Horizontal Flip]` 回放不翻转契约**：
  - [`resolve_fx3_monitor_flip_reset_and_playback()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1419-L1444) 与 [`verify_monitor_flip_playback_af_sens_and_interval_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1558-L1954) 校验 `MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]` 全部 4 个枚举值（`Auto` 出厂默认、`Horizontal Flip`、`Vertical Flip`、`Off`）：
    - 在 `[Camera Settings Reset]` 后原样保留，仅在 `[Initialize]` 时恢复为 `Auto`（违例阻断为 `BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION`）；
    - 即便设为 `[Horizontal Flip]`（实时取景画面水平镜像），**进入回放（Playback）模式时显示屏画面方向绝不翻转**（`playback_monitor_horizontally_inverted == False`、`playback_text_mirror_reversed == False`，违例阻断为 `BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION`）。
- **Movie / S&Q 自动对焦运动学完整菜单名与非对称重置分裂**：
  - [`resolve_fx3_af_transition_and_subj_shift_sensitivity()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1447-L1495) 强制核验 `ILME-FX3` 完整菜单字符串 **`[AF Subj. Shift Sensitivity]`**（`1(Locked on)..5(Responsive)`，出厂默认 `5(Responsive)`，严格拒止旧 α 机型的缩写幻觉 `"AF Subj. Shift Sens."`）与 **`[AF Transition Speed]`**（`1(Slow)..7(Fast)`，出厂默认 `5`），并验证二者均会被 `[Camera Settings Reset]` 重置回出厂默认 `5(Responsive)` / `5`，与同次重置下保持存活的 `[Monitor Flip Direction]` 形成严格的非对称重置分裂契约（`BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION`）。
- **`[Interval Shoot Func.]` 纯静态连拍边界（`1s..99m59s` 启动延迟、`1s..60s` 间隔）**：
  - [`resolve_fx3_interval_shoot_func_boundary()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py#L1498-L1555) 精确校验 `[Shooting Start Time]` `1s..99m59s`（`1..5999s`）、`[Shooting Interval]` `1s..60s`（`1..60s`）、`[Number of Shots]` `1..9999` 与纯静态图像（`JPEG`/`HEIF`/`RAW`）输出边界，需经 `Imaging Edge Desktop (Viewer)` 后期合成延时短片，严格拦截任何将 `ILME-FX3` 间隔拍摄误称为机内直出 `.MP4`/`.MXF` 或 FX6 `Interval Rec` 的违例声明（`BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并零错误退出。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读（`G10..G12`）仍按设计处于离线待命阻断状态（`85/88`），唯有人工作业台架提供真机 SHA-256 回读收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 235 双模式定向单测（64 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase235_recover_imagedb_monitor_flip_af_sens_88gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `64/64 OK`（`4.898s`）+ `64/64 OK`（`1.617s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1931 tests in 119.850s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1931 tests in 78.231s — OK (skipped=1)` |
| CLI `verify-88-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-88-gates`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=85/88`（`VERIFIED_85_OF_88_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-88-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-88-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=88/88`（`VERIFIED_ALL_88_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.06s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase235_recover_imagedb_monitor_flip_af_sens_88gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/outputs/fx3-safety/tests/test_phase235_recover_imagedb_monitor_flip_af_sens_88gate_guard.py)
6. [`reports/2026-11-15-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h261-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/reports/2026-11-15-phase235-safety-88gates-recover-imagedb-monitor-flip-af-sens/README.md)
