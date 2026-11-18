# Phase 294 里程碑安全护栏报告（Task H343 · Wave-53 `126`-Gate Preflight）：`G125` / `G126` 与统一 `verify-126-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 294（Task H343，Wave-53）端到端闭环交付，将官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01`（`5-024-458-18`）及共享 `BIONZ XR` `appFw.so` / `libInfraLensCommunicator.so` / 四语言 `.uxc` / `BK4` 实机情报固化为确定性安全门禁 `G125`、`G126` 与统一 `126` 门主预检引擎（`G01..G126`）**：
   - 新增模块 [`realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)（Schema `realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard_v1` `2026.11.17`），无重复委托 `G01..G124` 给 [`evaluate_124gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py)（Phase 294 增量 12 项 `O_RDONLY` 本地 donor 审计实测冷启动 **`0.0050s`**、缓存命中 **`0.0028s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/__init__.py)（导出 Phase 294 模块及全部非遮蔽符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-lens-comp-and-af-illuminator-guard` / `verify-g125-lens-comp-af-illuminator`、`verify-aperture-drive-and-folder-rating-guard` / `verify-g126-aperture-drive-folder-rating` 与 `verify-126-gates`，支持 `--simulate-bench-dry-run` / `--json` / `--summary` / `--clean-room`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/README.md) 第 63 节。
2. **三模式 86 项双模单测、全量 3,323 项套件、`verify-126-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_126gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/tests/test_realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_126gate_guard.py) 共 **86 项**双模单元测试（超过 `>= 80` 项要求；全量 `subprocess` 使用 `sys.executable`，覆盖 Python 3.14 `--help` 百分比转义校验与 `GITHUB_ACTIONS=true` `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`2.234s`）、`FX3_CLEAN_ROOM_TEST=1`（`2.213s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.090s`）下均 **`86/86 OK`**；
   - 全量 `outputs/fx3-safety/tests` 发现测试实测 **`Ran 3323 tests in 133.684s`**（`OK`，`rc=0`）；
   - CLI `verify-126-gates`：离线默认通过 **`123/126`**（`VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `--clean-room` 下均通过 **`126/126`**（`VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_126_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`a88204f582a971f0...` / `c0676f35ead1dec6...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.16s`，`make clean-audit` 实测 `ALL GREEN in 0.04s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G125` 与 Gate `G126` 技术建模要点（Wave-53 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase294_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **12 份** Wave-53 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，32 个 Wave-53 切片 `os.pread` SHA-256 `60493b7d79182ded886f14b1cbf2511397d21d1af1cbe0bd987777f460b2def1`）；
  - `libInfraLensCommunicator.so`（`14,544 B`，SHA-256 `e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab`）；
  - `FX6 appFw.so`（`50,520,424 B`，12 个 Wave-53 切片 `os.pread` SHA-256 `b216aa327cd26f1112ee52af151a0510640743d1eca9fa02ae4a3bd14996b261`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` 1:1 校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- `raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G125`：`GATE_G125_LENS_COMP_AF_ASSIST_AND_FRONT_AF_ILLUMINATOR_GUARD`
- **`[Lens Compensation]`（`Auto/Off` 严格双档 vs 休眠 `Auto: Low`，E 卡口/`SteadyShot Active` 强锁与 `FX6 Technical > Lens` 隔离）**：
  - `ILME-FX3 Ver. 7.02` `(Shooting) -> [Image Quality/Rec] -> [Lens Compensation]`（`_f.uxc` `0x75c8`）对 `Shading Comp.`（默认 `Auto`）、`Chromatic Aberration Comp.`（默认 `Auto`）与 `Distortion Comp.`（默认 `Off`）仅暴露 `Auto` 与 `Off`，故障闭锁拦截共享 `appFw.so` / `_f.uxc` `0x6c9c` 中的休眠枚举 `LENS_COMP_SHADING_AUTO_LOW`（`'Auto: Low'`，`STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION`）；三者均跨 `[Camera Settings Reset]` 留存，而 Movie 专用 `[Breathing Comp.]`（`On/Off`，默认 `Off`）随重置清空，且外录 HDMI RAW 时不可用。
  - 强制 E 卡口依赖数字校正镜头（`SELP1650`、`FE 28-70mm`，`LENS_SELECT_DISTORTION_NOT_SUPPORTED`）与视频 `[SteadyShot] = [Active]` 时 `[Distortion Comp.]` 锁定 `Auto`，禁止切至 `Off`；无电子触点纯手动镜头锁死菜单调节；对比 `ILME-FX6 Ver. 6.01` `Technical > Lens`（随 `All File` 保存，并在 `Distortion Comp. = Off`、`S&Q = On` 或 `Codec` 含 `RAW` 时强制锁定 `Breathing Compensation = Off`）。
- **Movie `[AF Transition Speed]` / `[AF Subj. Shift Sensitivity]` / `[AF Assist]` 与 `[AF Illuminator]` 机身前 LED 硬件实证纠偏**：
  - 限定 Movie/`S&Q` 生效 `[AF Transition Speed]`（`1 (Slow)..7 (Fast)`，默认 `5`）、`[AF Subj. Shift Sensitivity]`（`1(Locked on)..5(Responsive)`，默认 `5`，固件原生符号 `MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`）与 `[AF Assist]`（`On/Off`，仅限 Movie `AF-C`/`MOVIE_AUTO`，官方不兼容 `SELP1650`/`SEL18200LE`）。
  - 固化核心硬件纠偏：`ILME-FX3` 正面**确实内置** `AF illuminator/Self-timer lamp` LED（`Front side #8`，`0.3..3.0 m`）+ MI 热靴闪光灯辅助照明双通路（Still `Auto/Off`，在 `Movie`/`S&Q`/`AF-C`/运动中 `AF-A`/`Focus Magnifier`/卡口适配器下锁定），而 **`ILME-FX6` 才彻底缺失内置 AF 辅助照明 LED 与菜单**（拦截 `FX6 appFw.so` 中休眠 `N5model36setting_still_image_af_illuminator_tE` 符号）；经 [`compute_lens_comp_and_af_illuminator_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 穷举验证全部 `384` 组状态。

### 2.3 Gate `G126`：`GATE_G126_APERTURE_DRIVE_FOCUS_FRAME_AND_SLOT1_FOLDER_RATING_GUARD`
- **Still 5 项 AF/对焦框设置（仅 `[Initialize]` 可重置 vs `FX6 Iris`）**：
  - 门控 Still 专用 `[Aperture Drive in AF]`（`Focus Priority` / `Standard`[默认] / `Silent Priority`，及 `Silent Mode Settings` 独立子项 `Standard / Silent Priority`）、Still 专用 `[AF w/ Shutter]`（`On` 默认/`Off`）、Still 专用 `[Pre-AF]`（`Off` 默认/`On`，受 `LENS_PRE_AF_SUPPORT` 镜头位门控）、全模式 `[Circ. of Focus Point]`（`Does Not Circulate` 默认/`Circulate`，仅正交折返、无对角循环）与 `[Focus Area Color]`（`White` 默认/`Red`，区分 `ilc/2210` 正式名与 `BKID_APP_setting_focus_frame_color` 遗留名）；全部 5 项均不随 `[Camera Settings Reset]` 重置（仅 `[Initialize]` 还原），且在 `ILME-FX6` 上全部缺席（改用电影机 `Auto Iris / Manual / Push Auto Iris / Iris Override`）。
- **`[File/Folder Settings]` 与回放 `[Rating]`（`★1..★5`）`Slot-1` Tier-0 保险库写防火墙**：
  - 强校验 `[Folder Name]`（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` `100_MMDD` 禁用 `[Select REC Folder]`）、`[Set File Name]`（3 字符 `[A-Z0-9][A-Z0-9_]{2}`）、单文件夹 `4,000` 张上限（`STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`）与双卡同目录规则；
  - 只要 `Slot 1` 持有只读/写保护 Tier-0 恢复保险库，任何波及 `Slot 1` 的 `[Create New Folder]`、`[Forced File Number Reset]`、Playback `[Rating]`（`★1..★5`）、拍摄界面 `[Add Rating]`（同时拦截 Movie、重复加星及后台传输 `EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING`）及双卡联动建夹均故障闭锁返回 **`EROFS` / `EOPNOTSUPP`**，确保 `slot1_metadata_sector_writes == 0` 且 `slot1_avf_info_mutated == False`；经 [`compute_aperture_drive_and_folder_rating_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 穷举验证全部 `384` 组状态。

---

## 3. 实测验证矩阵（Measured Facts vs Engineering Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`123/126`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 294 双模定向单测（86 项 × 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_126gate_guard.py`（含 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `86/86 OK`（Donor `2.234s`）+ `86/86 OK`（`FX3_CLEAN_ROOM_TEST=1` `2.213s`）+ `86/86 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `2.090s`） |
| CLI `G125` / `G126` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-lens-comp-and-af-illuminator-guard` / `verify-aperture-drive-and-folder-rating-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（12 份 donor 冷启动 `0.0050s`，缓存 `0.0028s`） |
| CLI `verify-126-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-126-gates --summary --json`（及不带 `--json`） | `verified=123/126`（`VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`cross_model_flash_authorized=False`，`rc=0`） |
| CLI `verify-126-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-126-gates --simulate-bench-dry-run`（及 `--clean-room --summary --json`） | `verified=126/126`（`VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_126_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`a88204f582a971f0...`）+ `CLEAN_ROOM_SYNTHETIC`（`c0676f35ead1dec6...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 3323 tests in 133.684s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | `ALL GREEN in 0.16s` & `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_126gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/outputs/fx3-safety/tests/test_realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_126gate_guard.py)
6. [`reports/2026-11-17-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h343-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/reports/2026-11-17-phase294-safety-126gates-lens-comp-af-illuminator-aperture-drive-folder-rating/README.md)
