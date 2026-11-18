# Phase 288 安全护栏报告（Task H334 · Wave-51 `122`-Gate Preflight）：`G121` / `G122` 与统一 `verify-122-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 288（Task H334，Wave-51）闭环交付，将官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01`（`5-024-458-18`）及共享 `BIONZ XR` `appFw.so` / 四语言 `.uxc` / `BK4` 实机情报转化为确定性安全门禁 `G121`、`G122` 与统一 `122` 门主预检引擎（`G01..G122`）**：
   - 新增模块 [`realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)（Schema `realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard_v1` `1.0.0`），零重复委托 `G01..G120` 给 [`evaluate_120gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard.py)（Phase 288 增量 11 项 `O_RDONLY` 审计实测耗时 **`0.0040s–0.0051s < 0.20s`**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/__init__.py)（完整导出 Phase 288 全部符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-dci4k-and-aspect-ratio-guard` / `verify-g121-dci4k-aspect-ratio`、`verify-custom-hold-camset-photo-capture-guard` / `verify-g122-custom-hold-camset-photo-capture` 与 `verify-122-gates`，且所有 `argparse` `help=` 字符串均将 `%` 转义为 `%%` 以兼容 Python 3.14）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/README.md) 第 61 节。
2. **三模式 80 项双模单测、`verify-122-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_122gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_122gate_guard.py) 共 **80 项**双模单元测试（满足 `>= 76` 项；全量 `subprocess` 使用 `sys.executable`，`argparse --help` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 超时窗），在 `LOCAL_DONOR_O_RDONLY`（`7.628s`）、`FX3_CLEAN_ROOM_TEST=1`（`8.104s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`8.702s`）下均 **`80/80 OK`**；
   - CLI `verify-122-gates`：默认离线模式通过 **`119/122`**（`VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 下均通过 **`122/122`**（`VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_122_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`423979ae049f1b81...` / `22c926c9a3c10b1e...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G121` 与 Gate `G122` 技术建模要点（Wave-51 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase288_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py) 严格通过 `os.open(..., os.O_RDONLY)` 审计 **11 份** Wave-51 donor 产物：
  - `FX3 appFw.so`（`79,015,712 B`，17 个 Wave-51 切片 `os.pread` SHA-256 `a4a80b0fa107fc04868b4b4cd95f1674209f9e6129bd795484edb3df38a6f73d`）；
  - `FX6 appFw.so`（`50,520,424 B`，9 个 Wave-51 切片 `os.pread` SHA-256 `3a9396b48d87fa4c755d8f2d59d4f7376295e0007c5c2281c399da320a0b25e1`）；
  - 四语言 `_f.uxc`（`EN`/`ZH-CN`/`ZH-TW`/`JA` `resid16` 对齐校验）、`FX3 string_english.uxc` / `string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`。
- `raw_firmware_bytes_leaked == 0`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G121`：`GATE_G121_DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD`
- **`[XAVC S-I DCI 4K]`（`4096×2160` `17:9` All-Intra `4:2:2 10bit`）+ 强制重启 `24.00p` 与 `1..48 fps` S&Q 边界**：
  - 实证支持 `23.98p` / `24.00p`（`240M`）、`25p`（`250M`）、`29.97p`（`300M`）、`50p`（`500M`）、`59.94p`（`600M`，须 `CFexpress VPG200+` 或 `SDXC V90+`）；`S&Q` 仅限 `1, 2, 3, 6, 12, 24, 48 fps`（严禁 `100fps`/`120fps`）；切换进出 `24.00p`（`0x75ce`）必须触发相机重启与回放隔离（`_g.uxc` `0x639b`/`0x63b6`，违规返回 `STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION`）。
- **Long-GOP `UHD 3840×2160` 边界与 `4264×2408` Type-A HDMI RAW**：
  - `XAVC HS 4K`（`0x76df`）、`XAVC S 4K`（`0x690c`）与 `XAVC S-I 4K`（`0x70ba`）严格锁定 `3840×2160`（`16:9` UHD），无 `4096×2160`、无 `24.00p`（亦拦截休眠 `xavc_hs_8k_24p` 误判，`STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION`）；Type-A HDMI RAW（`0x6e97`）输出 `4264×2408`（`23.98p..59.94p` 含 `24.00p`），强制 `[Log Shooting] != Off`。
- **Still `[Aspect Ratio]`（`3:2`/`4:3`/`16:9`/`1:1`）vs Still-less `ILME-FX6`**：
  - `0x757c`/`.uxc` `0xe680`：`3:2` `12M`（默认 `.uxc` `0xe4f8`）、`4:3` `11M`、`16:9` `10M`、`1:1` `8.0M`；`.ARW` RAW 完整保留 `3:2`（`4240×2832`）像素与裁剪元数据；`APS-C S35 = On` 将 `L` 降档为 `M`；`Camera Settings Reset` 复位至 `3:2` / `L`；对比无静态照片菜单的 `FX6`（仅提供 `Marker Custom Aspect Ratio`）。经 [`compute_dci4k_hdmi_raw_and_aspect_ratio_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

### 2.3 Gate `G122`：`GATE_G122_RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD`
- **`[Reg. Custom Shoot Set]`（`11` 个 `Hold` 复选框，仅限 Still `P/A/S/M`）**：
  - `_f.uxc` `0x7631`（`Recall Custom hold 1..3` `0x60b4`/`0x7581`/`0x725b`，对应 `FX3 appFw.so` `is_checked_recall_custom_hold0..10` 共 11 项参数），严禁用于 `Movie`/`S&Q`/`Intelligent Auto`/`MR`，不支持自拍定时，调出 `ISO` 或 `DRO Bracket` 时强制 `[HLG Still Image] = Off`，且跨越 `[Camera Settings Reset]` 留存（`STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION`）。
- **`[Camera Set. Memory]`（`1..3` + `M1..M4`）与卡路径防火墙**：
  - 实机路径契约：`FX3` 使用 `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`（`M1..M4`）与 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`（`CAMSET`，严格锁定 `Slot 1` 且 `MR` 禁用），拒绝任何伪造 `FX6` `PRIVATE/SONY/PRO/CAMERA` / `s/SONY/PRO/CAMERA/` 路径（`STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION`），并对 `Slot 1`（`M1..M4` & `CAMSET`）实施 `[Format]` 擦除保护；`[Camera Settings Reset]` 保留机身 `1..3`，同时将 `[Memory/Recall Media]` 复位回 `Slot 1`。
- **回放 `[Photo Capture]`（`DCI 4K` 锁定 `_g 0x60ce` + `Slot-1` 写保护防火墙）与 `[Enlarge Initial Mag./Position]`**：
  - `[Photo Capture]`（`0x6856`，`JPEG` 默认 / `HEIF(4:2:0)` / `HEIF(4:2:2)`，`8.3M` `3840×2160` UHD 4K / `2.1M` `1920×1080` HD）在 `XAVC S-I DCI 4K` 视频上硬禁用（`_g.uxc` `0x60ce`），且在 `Slot 1` 恢复保险库介质上硬禁用（会新建 `DCIM` 静态文件并改写 `MDB`/`AVF_INFO` 数据库，`STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION`）；同时校验 Still 专属 `[Enlarge Image]`（`.uxc` `0xe8cb`）及精确 `ilc/2210` 命名 `[Enlarge Initial Mag.]`（`0x6b6e`：`Standard. Mag.`/`Previous Mag.`）与 `[Enlarge Initial Position]`（`0x781f`：`Focused Position`/`Center`）跨越 `[Camera Settings Reset]` 留存。经 [`compute_custom_hold_camset_photo_and_enlarge_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py) 穷举验证全部 **`384`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`119/122`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 288 双模定向单测（80 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_122gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `80/80 OK`（Donor `7.628s`）+ `80/80 OK`（`FX3_CLEAN_ROOM_TEST=1` `8.104s`）+ `80/80 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `8.702s`） |
| CLI `G121` / `G122` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-dci4k-and-aspect-ratio-guard` / `verify-custom-hold-camset-photo-capture-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0`（11 份 donor 审计 `0.0040s–0.0051s`） |
| CLI `verify-122-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-122-gates` | `verified=119/122`（`VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-122-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-122-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=122/122`（`VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_122_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`423979ae049f1b81...`）+ `CLEAN_ROOM_SYNTHETIC`（`22c926c9a3c10b1e...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_*.py'` | `Ran 3155 tests in 125.409s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_122gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/outputs/fx3-safety/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_122gate_guard.py)
6. [`reports/2026-11-17-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h334-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/reports/2026-11-17-phase288-safety-122gates-dci4k-aspect-custom-hold-camset-photo-capture/README.md)
