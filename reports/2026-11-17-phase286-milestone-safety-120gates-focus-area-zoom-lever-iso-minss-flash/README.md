# Phase 286 里程碑安全护栏报告（Task H330 · `120/120` Safety Gates Milestone!）：Wave-50 Safety Gates `G119` / `G120` 与统一 `verify-120-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 286（Task H330，`120/120` Safety Gates Milestone!）闭环交付，将 Wave-50 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01` 及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `BK4` 实机情报转化为确定性安全门禁 `G119`、`G120` 与统一 `120` 门主预检引擎（`G01..G120`）**：
   - 新增模块 [`realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)（Schema `realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard_v1` `1.0.0`），零重复委托 `G01..G118` 给 [`evaluate_118gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py)（Phase 286 增量 11 项 `O_RDONLY` 审计耗时 **`0.003608s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/__init__.py)（完整导出 Phase 286 全部符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-focus-area-and-zoom-lever-guard` / `verify-g119-focus-area-zoom-lever`、`verify-iso-minss-and-flash-guard` / `verify-g120-iso-minss-flash` 与 `verify-120-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/README.md) 第 60 节。
2. **三模式 80 项双模单测、`verify-120-gates`、Milestone 264 回归、全量 `3075` 项 `fx3-safety` 测试与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_focus_area_zoom_lever_iso_minss_flash_120gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_120gate_guard.py) 共 **80 项**双模单元测试（满足 `>= 76` 项；全量 `subprocess` 使用 `sys.executable`，`argparse` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`5.211s`）、`FX3_CLEAN_ROOM_TEST=1`（`5.216s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`5.226s`）下均 **`80/80 OK`**；
   - CLI `verify-120-gates`：默认离线模式通过 **`117/120`**（`VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 下均通过 **`120/120`**（`VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_120_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`f4430e0da1bed7f7...` / `112690ac8ab26771...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`，全量 `outputs/fx3-safety/tests` discovery 实测 **`Ran 3075 tests in 105.271s — OK`**。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G119` 与 Gate `G120` 技术建模要点（Wave-50 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase286_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **11 份** Wave-50 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，27 个 Wave-50 切片 `os.pread` SHA-256 `0bb1ce50139e29786603af8aad6810ae9ed12aa3914fd6475c2805655a621659`）；
  - `FX6 appFw.so`（`50,520,424 B`，9 个 Wave-50 切片 `os.pread` SHA-256 `b303cf26ccd7e44c6b3b8405badf89f833d36a9eccc9759fd13a233cd791f624`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` `resid16` 对齐校验，含日文半角片假名 UTF-8 实证词条）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- 实测耗时 **`0.003608s < 0.20s`**，`raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G119`：`GATE_G119_FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD`
- **完整 `14` 项 `[Focus Area]` 层级与 Movie `Touch Tracking` 隔离**：
  - `[Focus Area]`（`BKID_APP_setting_autofocus_area_contrast_detect_af`，`.uxc` `0xe0ad`）固定为 **7** 项 Still+Movie 共享对焦区域（`Wide` 默认、`Zone`、`Center Fix`、`Spot: S`、`Spot: M`、`Spot: L`、`Expand Spot`）+ **7** 项**仅 Still（`AF-C`）** `Tracking:` 菜单项（`Tracking: Wide`、`Tracking: Zone`、`Tracking: Center Fix`、`Tracking: Spot S/M/L`、`Tracking: Expand Spot`）；硬拦截 Movie/`S&Q` 选择菜单 `Tracking:`（`STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION` — Movie 使用 `Touch Tracking`），并对比 `ILME-FX6` 仅暴露 `Wide` / `Zone` / `Flexible Spot`。
- **`[Focus Area Limit]`、`[Focus Area Color]`、`[Circ. of Focus Point]` 与 `ilc/2210` `[AF Area Registration]`**：
  - 强制 `[Focus Area Limit]`（`0x6de2`/`0xe227`）至少启用 `>= 2` 项区域；`[Focus Area Color]`（`White`/`Red` `0x6af1`）与 Still 专用 `[AF Area Registration]`（`0x6b65`）跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 复位），且 `[AF Area Registration] = On` 自动锁定 `[Lock Operation Parts]` 为 `Off`（`STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION`）。
- **`XLR-H1` 无变焦拨杆辟谣与 `[Zoom Lever Speed]` / `[Remote Zoom Speed]` (`1..8`) vs `FX6` `0..99` 指示器**：
  - 实机核验 `ILME-FX3` 随附 **`XLR-H1` 音频手柄无变焦拨杆（NO zoom lever）、无录制按键（NO record button）、无 `ZOOM HOLD` 开关**（`STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION`）；FX3 仅存在机身 `W/T` 变焦拨杆 `[Zoom Lever Speed]`（`1st=3`、`2nd=8`，`1..8` `STBY`/`REC`，`0x6304`）、`[Custom Key Z. Speed]`（`1..8` 默认 `3`，`0x78e8`）、`[Remote Zoom Speed]`（`Variable`/`Fixed` `1..8`，`0x7128`）以及跨 `Camera Settings Reset` 留存、在 `RAW` 或 `119.88p`/`100p` 下锁定的 `[Zoom Range]`（`0x7164`）；对比 `ILME-FX6` Smart Handle 才具备 `Handle Zoom` + `Handle HOLD Switch` 且 `0..99` 为 `Zoom Position Display`（`0x22ce`）而非速度（`STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION`）。经 [`compute_focus_area_and_zoom_lever_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

### 2.3 Gate `G120`：`GATE_G120_ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD`
- **`[ISO Range Limit]` / `[ISO AUTO Min. SS]` vs `Cine EI` Base-ISO 锁定**：
  - `[ISO Range Limit]`（`0x72f8`，`50..409600` 硬件跨度，仅限手动 ISO，跨 `Camera Settings Reset` 留存）与 `[ISO AUTO Min. SS]`（`0x778b`，`Slower`/`Slow`/`Standard`/`Fast`/`Faster` 或 `1/8000..30"`，严格仅在 Still `P`/`A` + `ISO AUTO` 下生效，Movie/`S&Q` 禁用）；`Cine EI` / `Cine EI Quick` 严格将传感器录制感光度锁定至 Base **`ISO 800`** 或 **`ISO 12800`**（`STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION`）。
- **Still + 机械快门专属 `[Flash Mode]`、`<= 1/250 s` 同步与 `< 250V` MI-Shoe 过压保护 vs `[Video Light Mode]`**：
  - `[Flash Mode]`（`.uxc` `0xe5ce`：`Autoflash`、`Fill-flash`、`Slow Sync.`、`Rear Sync.`、`Flash Off`）、`[Flash Comp.]`（`-3.0..+3.0 EV` `0xe5d3`）、跨重置留存的 `[Exp.comp.set]`（`Ambient&flash`/`Ambient only` `0xe11a`）、`[Wireless Flash]`（`0x6201`）、`[Red Eye Reduction]`（`0x7ac9`）与 `[External Flash Set.]`（`0x6771`）严格受限于 **Still（`EXPOSURE_MODE_STILL`）且机械快门（`Silent Mode = Off`）且快门速度 `<= 1/250 s`**（非 HSS），MI-Shoe 中心触点要求 `< 250 V` 正极性（`STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION`）；与之对比，连续 `[Video Light Mode]`（`0x6211`：`Power Link`/`REC Link`/`REC Link&STBY`/`Auto`）在 Still/Movie/`S&Q` 全域有效，且 `FX6` 无任何 Still 闪光灯栈（仅保留 `Flash Band Reduce` `0x4215`）。经 [`compute_iso_minss_and_flash_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令（含全量 `3075` 项 `fx3-safety` 测试发现）均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`117/120`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 286 双模定向单测（80 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_120gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `80/80 OK`（Donor `5.211s`）+ `80/80 OK`（`FX3_CLEAN_ROOM_TEST=1` `5.216s`）+ `80/80 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `5.226s`） |
| CLI `G119` / `G120` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-focus-area-and-zoom-lever-guard` / `verify-iso-minss-and-flash-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 审计 `0.003608s`） |
| CLI `verify-120-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-120-gates` | `verified=117/120`（`VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-120-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-120-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=120/120`（`VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_120_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`f4430e0da1bed7f7...`）+ `CLEAN_ROOM_SYNTHETIC`（`112690ac8ab26771...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_*.py'` | `Ran 3075 tests in 105.271s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_120gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/outputs/fx3-safety/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_120gate_guard.py)
6. [`reports/2026-11-17-phase286-milestone-safety-120gates-focus-area-zoom-lever-iso-minss-flash/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h330-phase286-milestone-safety-120gates-focus-area-zoom-iso-flash/reports/2026-11-17-phase286-milestone-safety-120gates-focus-area-zoom-lever-iso-minss-flash/README.md)
