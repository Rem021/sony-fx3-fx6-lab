# Phase 299 里程碑安全护栏报告（Task H351 · Wave-55 `130/130` Safety Gates Milestone）：`G129` / `G130` 与统一 `verify-130-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 299（Task H351，Wave-55 — `130/130` 安全门禁里程碑）端到端闭环交付，将官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01`（`5-024-458-18`）及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `FX3-CX95900_ALLLANG-Backup.bin` 实机情报固化为确定性安全门禁 `G129`、`G130` 与统一 `130` 门主预检引擎（`G01..G130`）**：
   - 新增模块 [`realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py)（Schema `realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard_v1` `2026.11.17`），无重复委托 `G01..G128` 给 [`evaluate_128gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py)（Phase 299 增量 `11` 项 `O_RDONLY` 本地 donor 审计实测冷启动 **`0.0058s`**、缓存命中 **`0.003528s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/__init__.py)（导出 Phase 299 模块及全部非遮蔽符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-touch-shooting-and-disp-evf-absence-guard` / `verify-g129-touch-shooting-disp-evf`、`verify-ael-wireless-flash-and-interval-pb-edit-guard` / `verify-g130-ael-flash-interval-pb-edit` 与 `verify-130-gates`，支持 `--simulate-bench-dry-run` / `--json` / `--summary` / `--clean-room`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/README.md) 第 65 节。
2. **三模式 84 项双模单测、全量 3,493 项套件、`verify-130-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_touch_shooting_disp_evf_ael_flash_interval_pb_130gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/tests/test_realhw_touch_shooting_disp_evf_ael_flash_interval_pb_130gate_guard.py) 共 **84 项**双模单元测试（满足 `>= 80` 项要求；全量 `subprocess` 使用 `sys.executable`，覆盖 Python 3.14 `--help` 百分比 `%%` 转义校验与 `GITHUB_ACTIONS=true` `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`7.250s`）、`FX3_CLEAN_ROOM_TEST=1`（`1.605s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.560s`）下均 **`84/84 OK`**；
   - 全量 `outputs/fx3-safety/tests` 发现测试实测 **`Ran 3493 tests in 143.653s`**（`OK`，`rc=0`）；
   - CLI `verify-130-gates`：离线默认通过 **`127/130`**（`VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `--clean-room` 下均通过 **`130/130`**（`VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_130_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`7d517a97763a1f2d...` / `5f5c252d21487623...`），`scripts/run_all_lab_tests.py --clean-only` 与 `make clean-audit` 实测均 `ALL GREEN in 0.04s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G129` 与 Gate `G130` 技术建模要点（Wave-55 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase299_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` + 有界 `os.pread` 审计 **11 份** Wave-55 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，49 个 Wave-55 切片 `os.pread` SHA-256 `2303eca0bfd8a7c43eee832b6f084c77038eb97c9547c13559c23ab8072f8eea`）；
  - `FX6 appFw.so`（`50,520,424 B`，13 个 Wave-55 切片 `os.pread` SHA-256 `7f906640e7faa754f8790f1ac599cc77bc4f746fa3c9564ca32b5510279a7123`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` 1:1 校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- `raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G129`：`GATE_G129_TOUCH_OPERATION_DISP_4MODE_AND_ZERO_EVF_BLACKOUT_GUARD`
- **`[Touch Operation]` 4 项菜单与休眠触控陷阱阻断**：
  - `ILME-FX3 Ver. 7.02` 在 `MENU -> (Setup) -> [Touch Operation]`（`_g.uxc` `0x6345`）下仅暴露 4 项：**`[Touch Operation]`**（`On` 默认 / `On: Playback Only` / `Off`）、**`[Touch Sensitivity]`**（`Standard` 默认 / **`Sensitive`**，非 `Responsive`）、**`[Touch Func. in Shooting]`**（`Touch Focus` / **`Touch Tracking`** 默认 / `Off`，在 `Still` / `Movie` / `S&Q` 三模完全一致）与 **`[Swipe Up]`**（`Open the Fn Menu` 默认 / `Off`），全部 4 项**仅支持 `[Initialize]`**（跨 `[Camera Settings Reset]` 留存）；
  - 故障闭锁拦截共享 `appFw.so`/`.uxc` 中休眠的 `Touch Shutter`（`_f` `0x6a80`）、`Touch AE`（`_f` `0x702a`）、`Touch Panel/Pad` / `Touch Pad Settings`（`_f` `0x76ec`）、`Footer Icon Touch`（`_f` `0x70da`）与 `Swipe Left/Right`；严格隔离 `ILME-FX6` 的 `Technical > Touch Operation`（`On/Off`）与 `Shooting > Focus > Touch Function in MF`（`Spot Focus` / `Tracking AF`）。
- **`[DISP (Screen Disp) Set]`（`Operation Customize` 4 射/3 放页面）与零 EVF 黑屏软砖防火墙**：
  - 固化正确路径 **`MENU -> (Setup) -> [Operation Customize] -> [DISP (Screen Disp) Set]`**（`_g` `0x61c4 -> 0x61da`，拦截错误的 `Display Option` 归属声明），仅暴露 **4 个拍摄页面**（`Display All Info.`, `No Disp. Info.`, `Histogram`, `Level`）与 **3 个回放页面**（`Display Info.`, `Histogram`, `No Disp. Info.`），跨 `[Camera Settings Reset]` 留存；
  - 因 `ILME-FX3` **零内置 EVF、零眼部接近传感器、零物理 `FINDER/MONITOR` 按键**，对休眠键 `Select Finder/Monitor`（`_f` `0x74f9`）、`Finder/Monitor Sel.`、`For viewfinder`（`_f` `0x62d3` / `base` `0xe2e5`）、`Graphic Display`（`base` `0xe07a`）、`Monitor Off`、`DISP Button:Finder`（`_f` `0x6b57`）、`BKID_APP_setting_finder_monitor`、`BKID_APP_disp_mode_shoot_finder` 实施 fail-closed 拦截（`fx3_has_builtin_evf = False`、`evf_scanout_blocked = True`、`lcd_panel_scanout_preserved = True`），杜绝把 FX3 输出切往不存在的 EVF 导致黑屏假死；同时隔离 `ILME-FX6` 可拆卸 3.5" 触摸屏 `Viewfinder` + `Viewfinder Hood`（`TYPE_BUILTIN_EVF_NOT_EXIST`，绝不使用 `"Loupe"`）及 `Info. Disp. Mode Operation`（`Home Screen Priority` / `Direct Menu Priority`）；经 [`compute_touch_shooting_and_disp_evf_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py) 穷举验证全部 **`432`** 组状态（`all_invariants_hold = True`）。

### 2.3 Gate `G130`：`GATE_G130_AEL_WIRELESS_FLASH_INTERVAL_9SCALE_AND_PLAYBACK_EDIT_VAULT_GUARD`
- **Still 独占 `[AEL w/ Shutter]` 与 `[Flash]` 三子项（含 Reset 分化与 FX6 `Flash Band Reduce` 隔离）**：
  - 全部 4 项严格限制为 **`Still` 独占**（`Movie`/`S&Q` 不可用）：**`[AEL w/ Shutter]`**（`Exposure/Color -> [Metering]`：`Auto` 默认 / `On` / `Off`，`[AEL toggle]` 优先，`Initialize`-only）、**`[Exp.comp.set]`**（`Exposure/Color -> [Flash]`：`Ambient&flash` 默认 / `Ambient only`，`Initialize`-only）、**`[Wireless Flash]`**（`Exposure/Color -> [Flash]`：`Off` 默认 / `On`，**唯一支持 `[Camera Settings Reset]` 复位**）与 **`[External Flash Set.]`**（`Ext. Flash Firing Set.` / `Ext. Flash Cust. Set.`，`Initialize`-only，仅支持直插 MI 热靴，不支持引闪线离机）；
  - 严格隔离无闪光灯电影机 `ILME-FX6`（其唯一含 `"Flash"` 词条为抑制卷帘快门半帧条纹的 `Flash Band Reduce`，非闪光灯触发）。
- **间隔回放 `1..9` 刻度与回放 `[Edit]` `Slot-1` Tier-0 保险库防火墙**：
  - 固化路径 `MENU -> (Playback) -> [Viewing]`（`_g` `0x6033`，非 `Playback Option`）下的 **`[Cont. Play for Interval]`**（`_f` `0x78fa`，旧别名 `Cont. PB for Interval` `0x72e6`）与 **`[Play Speed for Interval]`**（`_f` `0x639e`，旧别名 `PB Speed for Interval` `0x72bd`）为精确 **`1..9` 级（默认 `5`，非 `1..5`）** 只读安全浏览（支持前/后拨轮与控制拨轮实时调速，不支持机内合成为视频）；
  - `MENU -> (Playback) -> [Edit]`（`_g` `0x6418`）在 FX3 上仅激活 4 项（`Rotate`、`Photo Capture`、`JPEG/HEIF Switch` [`JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)`]、`Copy`），fail-closed 拦截休眠 Alpha 陷阱 `[Beauty Effect]`（`_f` `0x7849`）与 `sequence_edit_trimming_*`，并对任何指向只读 `Slot 1` Tier-0 恢复保险库的 `Rotate` / `Photo Capture` / `Copy (Slot 2 -> Slot 1)` 写操作返回 **`EROFS` / `EOPNOTSUPP`**（`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`）；经 [`compute_ael_flash_and_interval_pb_edit_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py) 穷举验证全部 **`432`** 组状态（`all_invariants_hold = True`）。

---

## 3. 实测验证矩阵（Measured Facts vs Engineering Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`127/130`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 299 双模定向单测（84 项 × 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_touch_shooting_disp_evf_ael_flash_interval_pb_130gate_guard.py`（含 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `84/84 OK`（Donor `7.250s`）+ `84/84 OK`（`FX3_CLEAN_ROOM_TEST=1` `1.605s`）+ `84/84 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `1.560s`） |
| CLI `G129` / `G130` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-touch-shooting-and-disp-evf-absence-guard` / `verify-ael-wireless-flash-and-interval-pb-edit-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 冷启动 `0.0058s`，缓存 `0.003528s`） |
| CLI `verify-130-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-130-gates`（含 `--clean-room --summary --json`） | `verified=127/130`（`VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`cross_model_flash_authorized=False`，`rc=0`） |
| CLI `verify-130-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-130-gates --simulate-bench-dry-run`（含 `--clean-room --summary --json`） | `verified=130/130`（`VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_130_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`7d517a97763a1f2d...`）+ `CLEAN_ROOM_SYNTHETIC`（`5f5c252d21487623...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 3493 tests in 143.653s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | 均 `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_touch_shooting_disp_evf_ael_flash_interval_pb_130gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/outputs/fx3-safety/tests/test_realhw_touch_shooting_disp_evf_ael_flash_interval_pb_130gate_guard.py)
6. [`reports/2026-11-17-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h351-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/reports/2026-11-17-phase299-milestone-safety-130gates-touch-shooting-disp-evf-ael-flash-interval-pb/README.md)
