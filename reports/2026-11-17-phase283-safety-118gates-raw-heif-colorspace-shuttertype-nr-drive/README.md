# Phase 283 安全护栏报告（Task H326 · `118/118` Safety Gates）：Wave-49 Safety Gates `G117` / `G118` 与统一 `verify-118-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 283（Task H326，`118/118` Safety Gates）闭环交付，将 Wave-49 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01` 及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `BK4` 实机情报转化为确定性安全门禁 `G117`、`G118` 与统一 `118` 门主预检引擎（`G01..G118`）**：
   - 新增模块 [`realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py)（Schema `realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard_v1` `1.0.0`），零重复委托 `G01..G116` 给 [`evaluate_116gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.py)（Phase 283 增量 11 项 `O_RDONLY` 审计耗时 **`0.0038s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 283 符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-raw-heif-colorspace-guard` / `verify-g117-raw-heif-colorspace`、`verify-shutter-type-nr-drive-guard` / `verify-g118-shutter-type-nr-drive` 与 `verify-118-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/README.md) 第 59 节。
2. **三模式 78 项双模单测、`verify-118-gates`、Milestone 264 回归、全量 `2995` 项 `fx3-safety` 测试与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_raw_heif_colorspace_shuttertype_nr_drive_118gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_118gate_guard.py) 共 **78 项**双模单元测试（满足 `>= 74` 项；全量 `subprocess` 使用 `sys.executable`，`argparse` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`4.396s`）、`FX3_CLEAN_ROOM_TEST=1`（`4.259s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`4.253s`）下均 **`78/78 OK`**；
   - CLI `verify-118-gates`：默认离线模式通过 **`115/118`**（`VERIFIED_115_OF_118_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 下均通过 **`118/118`**（`VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_118_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`2c1395312c48110c...` / `b4adff6b95b683d9...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`，全量 `outputs/fx3-safety/tests` discovery 实测 **`Ran 2995 tests in 98.953s — OK`**。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G117` 与 Gate `G118` 技术建模要点（Wave-49 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase283_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **11 份** Wave-49 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，20 个 Wave-49 切片 `os.pread` SHA-256 `05c19a167f199e6b1ed585800dc317c512e2c72cc76864f4ce7ae579b7a5ba6e`）；
  - `FX6 appFw.so`（`50,520,424 B`，4 个 Wave-49 切片 `os.pread` SHA-256 `cf09f85d788d4f42fb040e695ebfc6c3288c3f23d40860cf070f9481ad07c06e`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` `resid16` 对齐校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- 实测耗时 **`0.00379s < 0.20s`**，`raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G117`：`GATE_G117_RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD`
- **`[RAW File Type]` 二元选项与休眠 `Lossless Comp` 陷阱防伪**：
  - 锁定 `ILME-FX3`（`12MP IMX510`、`Ver. 7.02`、`ilc/2210`）`[RAW File Type]`（`BKID_APP_setting_still_raw_file_type`，`_f.uxc` `0x6ff2`）仅暴露 **`Compressed`（默认）** 与 **`Uncompressed`** 14-bit `.ARW`；硬拦截任何伪造的休眠 `Lossless Comp`（`_f.uxc` `0x6b56` / `RAW_FILE_TYPE_LOSSLESS`，`STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION`），并与零 `DCIM`/`.ARW`/`.JPG`/`.HIF` 静态流水线的 `ILME-FX6`（`PRODUCT_MODEL_CHAPLIN`，`fx6_still_pipeline_supported == False`、`fx6_mechanical_shutter == False`）形成显式机型对比。
- **`[JPEG/HEIF Switch]`（`4:2:0`/`4:2:2`）与 `[HLG Still Image]` 前置条件 / 下游互斥锁死**：
  - `[JPEG/HEIF Switch]`（`JPEG` 默认、`HEIF(4:2:0)`、`HEIF(4:2:2)`，`0x742a`）与 `[HLG Still Image]`（`Off` 默认，`0x76c8`）：开启 `[HLG Still Image] = [On]` 必须同时满足 `HEIF` + `File Format = HEIF`（非 `RAW` / `RAW & HEIF`）+ `P/A/S/M` 模式（且未被 `[Reg. Custom Shoot Set]` 临时接管），自动锁死 `[Picture Profile]`、`[Creative Look]`、`[D-Range Optimizer]` 与 `[DRO Bracket]`，并将色彩空间覆盖为 `BT.2100/BT.2020`（`STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION`）。
- **`[Color Space]` DCF 2.0 `AdobeRGB` `_DSC` 自动下划线规则与 `[Set File Name]` 边界**：
  - 路径 `MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]`（`0x68b7`）：`sRGB`（`0xe07d` 默认 -> `DSC00001`）vs `AdobeRGB`（`0xe07e` -> DCF 2.0 自动前导下划线 `_DSC0001`）；强制 `[Set File Name]`（`0x6993`，3 字符 `A-Z0-9_`）禁止手工输入前导 `_` 且跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 复位）；`HEIF` 忽略 `sRGB`/`AdobeRGB` 选择且绝不生成 `_DSC` 前缀（`STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION`）。经 [`compute_raw_heif_hlg_colorspace_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py) 穷举验证全部 **`648`** 组状态组合。

### 2.3 Gate `G118`：`GATE_G118_SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD`
- **二元 `[Shutter Type]`（无 `Auto`！）与 `[e-Front Curtain Shut.]` 复位边界**：
  - 锁定 `ILME-FX3` `[Shutter Type]`（`BKID_APP_setting_still_shutter_type`，`_f.uxc` `0x7aa9`）仅暴露 **`Mechanical Shutter`（默认）** 与 **`Electronic Shutter`**（仅 `P/A/S/M` 可选；当 `[Silent Mode] = [On]` `0x7a53` 时强制切至 `Electronic Shutter`），拦截任何伪造 `Auto` 快门模式（`STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION`）；锁定 `[e-Front Curtain Shut.]`（`BKID_APP_setting_front_curtaion_shutter` `0x64c6`，`On` 默认）穿透 `[Camera Settings Reset]` 留存并仅随 `[Initialize]` 复位。
- **`1/250 s` 机械闪光同步上限与电子快门 5 项联锁禁用**：
  - 强制 `ILME-FX3` 机械闪光同步天花板严格为 **`1/250 s`**（`0x759b`，不存在 `1/320 s` APS-C 同步），且一旦 `[Electronic Shutter]` 或 `[Silent Mode] = [On]` 生效即硬锁全部 **5** 项功能：`Flash shooting`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`（`STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION`）。
- **`[Long Exposure NR]` / `[High ISO NR]` / `[Drive Mode]` `10 fps` 与 `> F11` AF 锁定耦合**：
  - `[Long Exposure NR]`（`On` 默认 `0x6cd7`，`>= 1 s` 等时暗帧降噪，在 `Cont. Shooting`/`Cont. Bracket`/`Electronic Shutter` 下禁用）；`[High ISO NR]`（`Normal` 默认 `0x650b`，纯 `RAW` 不可用且永不改写 `.ARW` 原始数据）；`[Drive Mode]`（全 **8** 模式，`Cont. Shooting: Hi+` `10 fps` `0x68d1` 在 `Uncompressed` RAW 或闪光灯触发时低于 `10 fps`，`Hi+/Hi/Mid` 在光圈 `> F11` 时锁死 AF 于首帧，且 `DRO Bracket` 在 `[HLG Still Image] = [On]` 时禁用，`STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION`）。经 [`compute_shutter_type_nr_drive_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令（含全量 `2995` 项 `fx3-safety` 测试发现）均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`115/118`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 283 双模定向单测（78 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_118gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `78/78 OK`（Donor `4.396s`）+ `78/78 OK`（`FX3_CLEAN_ROOM_TEST=1` `4.259s`）+ `78/78 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `4.253s`） |
| CLI `G117` / `G118` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-raw-heif-colorspace-guard` / `verify-shutter-type-nr-drive-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 审计 `0.00379s`） |
| CLI `verify-118-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-118-gates` | `verified=115/118`（`VERIFIED_115_OF_118_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-118-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m fx3_safety verify-118-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=118/118`（`VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_118_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`2c1395312c48110c...`）+ `CLEAN_ROOM_SYNTHETIC`（`b4adff6b95b683d9...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 2995 tests in 98.953s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_118gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/outputs/fx3-safety/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_118gate_guard.py)
6. [`reports/2026-11-17-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h326-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/reports/2026-11-17-phase283-safety-118gates-raw-heif-colorspace-shuttertype-nr-drive/README.md)
