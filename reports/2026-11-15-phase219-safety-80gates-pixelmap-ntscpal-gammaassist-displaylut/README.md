# Phase 219（`80/80` 里程碑）安全护栏报告：Gates G79 / G80 与统一 `verify-80-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-30 官方 `ILME-FX3 Ver. 7.02` 里程碑安全门禁 `G79`、`G80` 与统一 `80-Gate` 主预检引擎（`G01..G80`）闭环交付**：
   - 新增模块 [`realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py)（将 `G01..G78` 直接委托给 [`evaluate_78gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L1580-L1808)，`100%` 保留 `verify-58-gates` 至 `verify-78-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/README.md)。
2. **双模式全量测试与 CLI 实测 100% 通过（实测事实）**：
   - 新增 [`test_phase219_pixelmap_ntscpal_gammaassist_displaylut_80gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/tests/test_phase219_pixelmap_ntscpal_gammaassist_displaylut_80gate_guard.py) 共 **60 项**双模式单元测试（要求 `>=50`），在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下全部 `OK` 通过（`0.910s`）；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1683/1683` 全部通过（`88.503s`）**，Clean-Room 合成模式 **`1683` 项通过、`1` 项按设计跳过（`60.261s`）**；
   - CLI `verify-80-gates`：默认离线模式通过 **`77/80`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`80/80`**；
   - BYOF 与字节码卫生审计：`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`（零 `.pyc`、零固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G79 与 Gate G80 技术建模要点

### 2.1 Gate G79：`G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD`
- **`[Auto Pixel Mapping]` 关机机械快门动作声与 `Off` 状态 `3` 天人工维护周期**：
  - [`resolve_fx3_pixel_mapping_lifecycle()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L773-L797) 与 [`verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L800-L988) 精确建模 `MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]`（默认 `On`）：关机时定期遮蔽传感器采集暗场校准，即使 `[Silent Mode] = [On]` 仍会发出正常机械快门动作声（拦截任何“静音模式可屏蔽关机快门声”的错误假设 -> `BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION`）；当 `[Auto Pixel Mapping] = [Off]` 且距上次像素映射超过 `3` 天未执行手动映射时触发阻断。
- **手动 `[Pixel Mapping]` 低电量锁死、执行期全操控锁死、完成后强制自动重启（`H0 == H2`）与 `cnflasha` 只读防火墙**：
  - 低电量锁死：当 `NP-FZ100` 电量 `< 20%` 或低电量告警激活时拒绝执行手动 `[Pixel Mapping]`（`BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT`）；
  - 执行期操控锁死：执行期间严格禁止一切菜单/录制/按键并发操作（`BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION`）；
  - 强制自动重启与 `/tmp` 挂载卸载：手动 `[Pixel Mapping]` 完成后机身必定自动重启（`auto_camera_restart_on_completion == True`），干净卸载一切易失性 Stage-B `/tmp` RAM bind-mount 覆盖层并恢复原厂 `FX3 Ver. 7.02` `H0 == H2` 哈希等价（`BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH`）；
  - `cnflasha` 原厂校准只读红线：硬锁 `cnflasha_userspace_write_blocked == True`、`cnflasha_calibration_mutation_bytes == 0` 与 `persistent_emmc_writes_authorized == False`（`BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase219_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L630-L765) 以 `os.open(..., os.O_RDONLY)` 校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成兜底。

### 2.2 Gate G80：`G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD`
- **`[NTSC/PAL Selector]` 独占帧率/时间码矩阵、开机横幅与 `[Camera Settings Reset]` 跨重置持久化**：
  - [`resolve_fx3_ntscpal_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L1074-L1108) 与 [`verify_ntscpal_persistence_and_gamma_assist_displaylut_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L1138-L1355) 强制校验：`NTSC` 支持 `23.98p`（**NTSC 独占**）、`24.00p`、`29.97p`、`59.94p`、`119.88p` 及 `[TC Format]` `DF`/`NDF`；`PAL` 仅支持 `25p`、`50p`、`100p`，严禁 `23.98p` 及 `DF`/`NDF` 选择（`BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION`）；
  - 非区域默认制式每次开机强制显示 `"Running on NTSC."` 或 `"Running on PAL."` 横幅并跟踪双卡媒体库制式状态（`BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION`）；
  - 重置不对称性：`[Camera Settings Reset]` **保留**当前 `[NTSC/PAL Selector]` 制式，唯有完整 `[Initialize]` 才将其重置回机身区域出厂默认制式（`BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION`）。
- **`[Gamma Display Assist]` 四档（零 `S-Log2`）、`[Log Shooting]` 硬锁 `[Off]` / `[Display LUT]` 分流与内置 LCD 作用域隔离**：
  - 严格限定 `Ver. 7.02` `[Gamma Disp. Assist Typ.]` 四档（`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`），彻底拦截旧机型遗留的 `S-Log2` 选项（`BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN`）；
  - [`resolve_fx3_gamma_assist_and_display_lut_split()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L1111-L1135) 强制：只要处于 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`），`[Gamma Display Assist]` 立即硬锁为 `[Off]`，监看转换完全交由 `[Display LUT]` 接管（`BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION`）；
  - 内置机身 LCD 独占作用域：`[Gamma Display Assist]` 绝不作用于外接电视或 HDMI 监视器（硬锁 `external_hdmi_gamma_assist_applied == False` -> `BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts）

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 219 双模式定向单测（60 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_phase219_*.py'`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `60/60 OK` + `60/60 OK`（`0.910s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_*.py'` | `Ran 1683 tests in 88.503s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_*.py'` | `Ran 1683 tests in 60.261s — OK (skipped=1)` |
| CLI `verify-80-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-80-gates` | `verified=77/80`（`VERIFIED_77_OF_80_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-80-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-80-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=80/80`（`VERIFIED_ALL_80_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase219_pixelmap_ntscpal_gammaassist_displaylut_80gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/outputs/fx3-safety/tests/test_phase219_pixelmap_ntscpal_gammaassist_displaylut_80gate_guard.py)
6. [`reports/2026-11-15-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h242-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/reports/2026-11-15-phase219-safety-80gates-pixelmap-ntscpal-gammaassist-displaylut/README.md)
