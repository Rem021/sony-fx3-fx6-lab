# Phase 280 安全护栏报告（280th Milestone · Task H321 · `116/116` Safety Gates）：Wave-48 Safety Gates `G115` / `G116` 与统一 `verify-116-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 280（第 280 里程碑，Task H321，`116/116` Safety Gates）闭环交付，将 Wave-48 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01` 及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `BK4` 实机情报转化为确定性安全门禁 `G115`、`G116` 与统一 `116` 门主预检引擎（`G01..G116`）**：
   - 新增模块 [`realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py)（Schema `realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard_v1` `1.0.0`），零重复委托 `G01..G114` 给 [`evaluate_114gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)（Phase 280 增量 11 项 `O_RDONLY` 审计耗时 **`0.0041s`**，`G115` + `G116` 矩阵评估 **`0.0027s`**，总增量 **`0.0068s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 280 符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-pp-scinetone-creativelook-dro-guard` / `verify-g115-pp-scinetone-creativelook-dro`、`verify-wb-cineei-and-metering-guard` / `verify-g116-wb-cineei-metering` 与 `verify-116-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/README.md) 第 58 节。
2. **三模式 78 项双模单测、`verify-116-gates`、Milestone 264 回归、全量 `2917` 项 `fx3-safety` 测试与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_pp_scinetone_creativelook_dro_wb_metering_116gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/tests/test_realhw_pp_scinetone_creativelook_dro_wb_metering_116gate_guard.py) 共 **78 项**双模单元测试（满足 `>= 74` 项；全量 `subprocess` 使用 `sys.executable`，`argparse` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 充足超时窗），在 `LOCAL_DONOR_O_RDONLY`（`4.297s`）、`FX3_CLEAN_ROOM_TEST=1`（`4.616s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`4.134s`）下均 **`78/78 OK`**；
   - CLI `verify-116-gates`：默认离线模式通过 **`113/116`**（`VERIFIED_113_OF_116_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `--force-clean-room` 下均通过 **`116/116`**（`VERIFIED_ALL_116_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_116_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`ebec24b79215f2f1...` / `09a3677a92a19253...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.04s`，全量 `outputs/fx3-safety/tests` discovery 实测 **`Ran 2917 tests in 91.699s — OK`**。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G115` 与 Gate `G116` 技术建模要点（Wave-48 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase280_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **11 份** Wave-48 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，22 个 Wave-48 切片 `os.pread` SHA-256 `75212aef523a945536f70f0902403a4f95e9b2dfd6e2528ad3b86e5a67642e35`）；
  - `FX6 appFw.so`（`50,520,424 B`，6 个 Wave-48 切片 `os.pread` SHA-256 `9b172e4557d92e55848d0d7ed7f25ee3ce3d61c48fb22deb6a4c8a2cfa5eb5ad`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` `resid16` 对齐校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- 实测耗时 **`0.0041s < 0.20s`**，`raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G115`：`GATE_G115_PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD`
- **开箱默认 `PP11`（`S-Cinetone`）与 `[Creative Look]` / `[DRO]` 互斥护栏**：
  - 锁定 `ILME-FX3` 出厂默认 `[Picture Profile]`（`BKID_APP_setting_picture_profile`，`_f.uxc` `0x6830`）为 **`PP11`（`S-Cinetone`，`0x67ab`/`0x6e61`）**，且默认未勾选 `[Different Set for Still/Mv]`（`0x62ee`），故 Movie 与 Still 同步激活 `PP11`；只要 `[Picture Profile] != Off`，`[Creative Look]`（`0x6823`：10 预设 `ST/PT/NT/VV/VV2/FL/IN/SH/BW/SE` + `CREATIVE_BOX_1..6` + 8 微调参数）硬锁为 `'-'` 且 `[D-Range Optimizer]`（`0xe89c`：`Auto`/`Lv1..Lv5`）硬锁为 `Off`（`STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION`）。
- **`[Log Shooting]` 双重 Log/烘焙防呆与 `PPLUT1..4` 限制**：
  - `[Log Shooting]`（`Flexible ISO`、`Cine EI Quick`、`Cine EI`，`0x6020`）硬锁 `[Picture Profile] -> Off`、`[Creative Look] -> '-'`、`[D-Range Optimizer] -> Off` 及短片 `[Gamma Display Assist] -> Off`（`STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION`）；`PPLUT1..4` 仅限 Movie/S&Q，并在机内录制时将 HDMI 输出钳位至 `1080p`（`STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION`）。
- **复位陷阱防护（`[Camera Settings Reset]` / `[Initialize]` vs `[PPx] -> [Reset]`）**：
  - `[Camera Settings Reset]` 仅恢复活动槽位选择器到 `PP11`，但 `PP1..PP11` 已改内部参数与 `[Different Set for Still/Mv]` 勾选框会**穿透** `[Camera Settings Reset]` 与 `[Initialize]` 留存，必须逐槽位显式执行 `[PPx] -> [Reset]` 方可清零（`STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP`）；经 [`compute_pp_scinetone_creativelook_dro_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py) 穷举验证全部 **`512`** 组状态组合，对比 `FX6 Ver. 6.01`（`Base Look` `Custom` 默认 `S-Cinetone`）。

### 2.3 Gate `G116`：`GATE_G116_WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD`
- **`[White Balance]` 全域参数、色温步进与 `Cine EI` / `Custom Setup` 护栏**：
  - 建模 `Auto`（默认，`Priority Set in AWB`：`Standard`/`Ambience`/`White` `0x67a7`）、固定预设、`C.Temp./Filter`（`2500K..9900K` `100K` 步进共 `75` 档 + `A7..B7`/`G7..M7` `[-7..+7]`）、`Custom 1..3`（`0xe79d..0xe79c`）、静态 `[Shutter AWB Lock]`（默认 `Off`，不随 `Camera Settings Reset` 复位）及短片 `[Shockless WB]`（默认 `1 (Fast)`）。
  - 在 `Cine EI` / `Cine EI Quick` 下硬拦截 `[Auto]` 与 `[Underwater Auto]`（`STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION`）；当 `[Log Shooting] != Off` 或 `S-Log3`/`PPLUT1..4` 激活时执行 `[Custom Setup]` 触发白平衡捕获错误拦截（`STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP`）；锁定 `Custom 1..3` 数据跨 `[Camera Settings Reset]` 留存且**无法存入 `Save/Load Settings`（`CAMSET`）**（`STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION`）。
- **`[Metering Mode]` 6 模式、`De-Squeeze` 人脸优先联锁与 `Cine EI` 被动 `M.M.` 不变性**：
  - 校验精确 **6** 项测光模式（`Multi` 默认、`Center`、`Spot: Standard`、`Spot: Large`、`Entire Screen Avg.`、`Highlight`），`[Face Priority in Multi Metering]`（默认 `On` `0x69c7` — 当 `[De-Squeeze Display] != Off` 时硬锁 `Off`），`[Spot Metering Point]`（`Center`/`Focus Point Link` `0x625c` — `Wide`/`Zone`/`Center Fix` 下硬锁 `Center`），静态 `[AEL w/ Shutter]`（默认 `Auto` `0x669d`，不随 `Camera Settings Reset` 复位），及 `Cine EI` 基础 ISO（`800`/`12800`）下测光仅驱动 `M.M.` 监视指示而不改写录制 ISO/增益（`STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION`）；经 [`compute_wb_cineei_and_metering_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py) 穷举验证全部 **`288`** 组状态组合，对比 `FX6 Ver. 6.01`（`Memory A`/`B`/`ATW` 与 `3200K/4300K/5500K` `Cine EI` 预设）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令（含全量 `2917` 项 `fx3-safety` 测试发现）均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`113/116`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 280 双模定向单测（78 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_pp_scinetone_creativelook_dro_wb_metering_116gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `78/78 OK`（Donor `4.297s`）+ `78/78 OK`（`FX3_CLEAN_ROOM_TEST=1` `4.616s`）+ `78/78 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `4.134s`） |
| CLI `G115` / `G116` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-pp-scinetone-creativelook-dro-guard` / `verify-wb-cineei-and-metering-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 审计 `0.0041s`，两门禁评估 `0.0027s`） |
| CLI `verify-116-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-116-gates` | `verified=113/116`（`VERIFIED_113_OF_116_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-116-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-116-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=116/116`（`VERIFIED_ALL_116_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_116_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`ebec24b79215f2f1...`）+ `CLEAN_ROOM_SYNTHETIC`（`09a3677a92a19253...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 2917 tests in 91.699s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_pp_scinetone_creativelook_dro_wb_metering_116gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/outputs/fx3-safety/tests/test_realhw_pp_scinetone_creativelook_dro_wb_metering_116gate_guard.py)
6. [`reports/2026-11-17-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h321-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/reports/2026-11-17-phase280-milestone-safety-116gates-pp-scinetone-wb-metering/README.md)
