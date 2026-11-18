# Phase 297 里程碑安全护栏报告（Task H347 · Wave-54 `128/128` Power-of-Two Safety Gates Milestone）：`G127` / `G128` 与统一 `verify-128-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 297（Task H347，Wave-54 — `128/128` 2 的幂次安全门禁里程碑）端到端闭环交付，将官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01`（`5-024-458-18`）及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `FX3-CX95900_ALLLANG-Backup.bin` 实机情报固化为确定性安全门禁 `G127`、`G128` 与统一 `128` 门主预检引擎（`G01..G128`）**：
   - 新增模块 [`realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py)（Schema `realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard_v1` `2026.11.17`），无重复委托 `G01..G126` 给 [`evaluate_126gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)（Phase 297 增量 `11` 项 `O_RDONLY` 本地 donor 审计实测冷启动 **`0.0050s`**、缓存命中 **`0.0030s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/__init__.py)（导出 Phase 297 模块及全部非遮蔽符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-switch-vh-af-and-exposure-stdadj-guard` / `verify-g127-switch-vh-af-exposure-stdadj`、`verify-tcub-format-and-playback-copy-slot-guard` / `verify-g128-tcub-playback-copy-slot` 与 `verify-128-gates`，支持 `--simulate-bench-dry-run` / `--json` / `--summary` / `--clean-room`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/README.md) 第 64 节。
2. **三模式 86 项双模单测、全量 3,409 项套件、`verify-128-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_128gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/tests/test_realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_128gate_guard.py) 共 **86 项**双模单元测试（超过 `>= 80` 项要求；全量 `subprocess` 使用 `sys.executable`，覆盖 Python 3.14 `--help` 百分比 `%%` 转义校验与 `GITHUB_ACTIONS=true` `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`6.996s`）、`FX3_CLEAN_ROOM_TEST=1`（`1.614s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.617s`）下均 **`86/86 OK`**；
   - 全量 `outputs/fx3-safety/tests` 发现测试实测 **`Ran 3409 tests in 130.740s`**（`OK`，`rc=0`）；
   - CLI `verify-128-gates`：离线默认通过 **`125/128`**（`VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `--clean-room` 下均通过 **`128/128`**（`VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_128_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`af1df3f7d4d2c9f0...` / `1bb7697a5f91564c...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.04s`，`make clean-audit` 实测 `ALL GREEN in 0.03s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G127` 与 Gate `G128` 技术建模要点（Wave-54 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase297_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` + 有界 `os.pread` 审计 **11 份** Wave-54 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，48 个 Wave-54 切片 `os.pread` SHA-256 `670730eb10ed17c9446da4b6c1228ba76e538d37a3d5814b77af8a8fc23d57f6`）；
  - `FX6 appFw.so`（`50,520,424 B`，14 个 Wave-54 切片 `os.pread` SHA-256 `8e2a4a756a844453a7d087998083e9c2904639e95132916632e14decae65fa14`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` 1:1 校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- `raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G127`：`GATE_G127_SWITCH_VH_AF_FOCUS_LIMIT_EXPOSURE_STD_ADJ_AND_BRACKET_GUARD`
- **`[Switch V/H AF Area]`（Still `AF-C` 三姿态 `0°/90°/270°` vs `INVALID` 俯仰 & 8 项锁定）与 `[Focus Area Limit]`（精确 14 项复选框 & `>= 2` 下限 vs 休眠 `XL/XS/Custom1..3`）**：
  - `[Switch V/H AF Area]`（`Off` 默认 / `AF Point Only` / `AF Point + AF Area`，`_f.uxc` `0x73ae`）**仅在静态照片（Still）`[Focus Mode] = AF-C`** 下依赖机内 3 态重力方向传感器（`0°` / `90°` / `270°`）自动切换；镜头垂直朝上/朝下返回 `INVALID` 不切换；在 `Movie/S&Q`、非 `AF-C`、`iAuto`、数码变焦、AF 激活中、连拍、自拍倒计时与 `[Focus Magnifier]` 下禁止切换（`STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_INVALID_PITCH`）；更改模式会清空三方向已记忆对焦点，且受 `[Camera Settings Reset]` 重置；
  - `[Focus Area Limit]`（`_f.uxc` `0x6de2`）在 FX3 上**精确暴露 14 个复选框**（`Wide`, `Zone`, `Center Fix`, `Spot: S/M/L`, `Expand Spot` 及其 7 项 `Tracking:*`），故障闭锁拦截共享 `appFw.so` 中休眠的 `model::focus_area_limit_flexible_spot_{xl,xs}` / `custom_{1..3}`，通过 `.uxc` `0xea28` 强制至少勾选 `>= 2` 项区域，并在 Movie/`S&Q` 中禁用 `[Tracking]` 选区；同时覆盖 `[Focus Area Color]`（`White` 默认 / `Red`，仅 `[Initialize]` 重置）。
- **`[Exposure Std. Adjust]`（精确 5 种测光模式 `-1..+1 EV` @ `1/6 EV` & `Initialize` 独占持久化）与 Still `[Bracket Settings]`**：
  - 固化消歧定论：`[Exposure Std. Adjust]`（`_f.uxc` `0x6114`，进入警告 `.uxc` `0xe567`）校准**全部 5 种测光模式**（`Multi`, `Center`, `Spot`, `Entire Screen Avg.`, `Highlight`，每项 13 档 `-1..+1 EV` @ `1/6 EV` 步进），独立写入 EXIF 并偏移 `M.M.` 与 Spot AEL（不叠加进 `Exposure Comp.`），包围曝光中途调整会重置已拍张数，且**跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 可恢复 `±0`）**；
  - Still `[Bracket Settings]`（`[Selftimer during Bracket]`: `Off`/`2 Sec`/`5 Sec`/`10 Sec`；`[Bracket order]`: `0->-->+` / `-->0->+`）仅限 Still 使用，并故障闭锁拦截 `ILME-FX6 appFw.so` 中休眠的 `bracket_*` 跨机接线；经 [`compute_switch_vh_af_and_exposure_stdadj_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py) 穷举验证全部 `384` 组状态。

### 2.3 Gate `G128`：`GATE_G128_TCUB_FORMAT_AND_PLAYBACK_COPY_SLOT_GUARD`
- **`[TC/UB]` 6 项 `[Initialize]` 独占持久化、`[Time Code Format]`（NTSC `23.98p/24.00p` `NDF` 锁定与 PAL 隐藏）与 `[TC/UB Disp. Setting]`**：
  - `MENU -> (Shooting) -> [TC/UB]` 全部 6 项（`Time Code Preset`, `User Bit Preset`, `Time Code Format` / `TC Format`, `Time Code Run`, `Time Code Make`, `User Bit Time Rec`）及 `(Setup) -> [Display Option] -> [TC/UB Disp. Setting]`（`Counter` / `TC` 默认 / `U-Bit`，回放期间仅支持动态影像切换，`.uxc` `0xe728`）**全部跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 可清除）**；
  - `[Time Code Format]`（`DF` 默认 / `NDF`）仅限 `NTSC` 可用：在 `23.98p` / `24.00p` 下强制锁定 `NDF`（显示 `[-]`，拒绝 `DF`），在 `PAL` 下隐藏不可调；并与 `ILME-FX6` 物理 BNC `TC IN/TC OUT` + `EXT-LK` 架构严格隔离。
- **回放 `[Copy]` 双向写方向不对称防火墙（`Slot 2 -> Slot 1` Tier-0 保险库写拦截）与 `[Slide Show]` 休眠旁路感知**：
  - `MENU -> (Playback) -> [Edit] -> [Copy]`（`FUNC_copy_content`）**始终以当前 `[Select Playback Media]` 为源、将文件写入对侧槽位**：当 `[Select Playback Media] = Slot 1` 时从 `Slot 1 -> Slot 2` 只读复制（且目标卡去除 `Protect` 保护标志）；**一旦 `[Select Playback Media] = Slot 2`，`[Copy]` 反向写入 `Slot 1`（`Slot 2 -> Slot 1`），只要 `Slot 1` 持有只读 Tier-0 恢复保险库，门禁 MUST fail-closed 拦截并返回 `EROFS` / `EBUSY`，保证 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`**！
  - 同步门控 `get_battery_status_for_copy` 电量检测、动态影像复制目标卡速率门槛（`.uxc` `0xe80e` / `0xe8ca`：`SDXC Class10/U1/V10`+ 或 `CFexpress`）、`[Slide Show]`（仅 `Date View` / `Folder View(Still)`，`Interval` `1/3/5/10/30 Sec`）自动旁路 `[Power Save Start Time]` 的功耗/热风险感知，以及 `ILME-FX6` 休眠 `Copy Clip` 菜单排除；经 [`compute_tcub_and_playback_copy_slot_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py) 穷举验证全部 `384` 组状态。

---

## 3. 实测验证矩阵（Measured Facts vs Engineering Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`125/128`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 297 双模定向单测（86 项 × 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_128gate_guard.py`（含 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `86/86 OK`（Donor `6.996s`）+ `86/86 OK`（`FX3_CLEAN_ROOM_TEST=1` `1.614s`）+ `86/86 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `1.617s`） |
| CLI `G127` / `G128` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-switch-vh-af-and-exposure-stdadj-guard` / `verify-tcub-format-and-playback-copy-slot-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 冷启动 `0.0050s`，缓存 `0.0030s`） |
| CLI `verify-128-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-128-gates --summary --json`（及不带 `--json`） | `verified=125/128`（`VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`cross_model_flash_authorized=False`，`rc=0`） |
| CLI `verify-128-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-128-gates --simulate-bench-dry-run`（及 `--clean-room --summary --json`） | `verified=128/128`（`VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_128_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`af1df3f7d4d2c9f0...`）+ `CLEAN_ROOM_SYNTHETIC`（`1bb7697a5f91564c...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 3409 tests in 130.740s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | `ALL GREEN in 0.04s` & `ALL GREEN in 0.03s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_128gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/outputs/fx3-safety/tests/test_realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_128gate_guard.py)
6. [`reports/2026-11-17-phase297-milestone-safety-128gates-switch-vh-af-stdadj-bracket-tcub-copy-slot/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h347-phase297-milestone-safety-128gates-switch-vh-af-stdadj-tcub-copy-slot/reports/2026-11-17-phase297-milestone-safety-128gates-switch-vh-af-stdadj-bracket-tcub-copy-slot/README.md)
