# Phase 263 安全护栏报告：Safety Gates G103 / G104 与统一 `verify-104-gates` 预检引擎（`outputs/fx3-safety/`，Wave-42）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-42 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）安全门禁 `G103`、`G104` 与统一 `104` 门主预检引擎（`G01..G104`）闭环交付**：
   - 新增模块 [`realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py)（Schema `realhw_apsc_s35_face_eye_af_version_and_104gate_guard_v1` `v1.0.0`），将 `G01..G102` 直接委托给 [`evaluate_102gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py#L2216-L2439)（`100%` 保留 `verify-58-gates` 至 `verify-102-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 263 符号）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-apsc-s35-face-eye-af-guard` / `verify-g103-apsc-s35-face-eye-af`、`verify-version-readonly-bodydata-flash-block-guard` / `verify-g104-version-bodydata-block` 与 `verify-104-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/README.md)。
2. **双模式 68 项单测、Milestone 254 / 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/tests/test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py) 共 **68 项**双模式单元测试（要求 `< 4s`），在 `LOCAL_DONOR_O_RDONLY`（`3.444s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.857s`）双模式下全部 `OK` 通过；
   - CLI `verify-104-gates`：默认离线模式通过 **`101/104`**（`VERIFIED_101_OF_104_AWAITING_PHYSICAL_TIER0`，3 道物理台架 Tier-0 收据门禁待接入真机离线只读证据），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`104/104`**（`VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP`）；
   - 跨模块里程碑与 BYOF 卫生检查：`make verify-milestone-254`、`make verify-milestone-233` 与 `make verify-milestone-221` 双模均为 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（`0.07s`，零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G103 与 Gate G104 技术建模要点（Wave-42 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase263_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L752-L912) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、FX3 `libgpe.so`、FX3 `libSaveLoadSettings.so`、FX3 `FX3-CX95900_ALLLANG-Backup.bin`、FX6 `libInfraDial.so` 与 FX6 `CX95898_NTSC.bin`），保证 `< 0.10s` 与 `raw_firmware_bytes_leaked == 0`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 缺省时自动切换为确定性 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G103：`G103_apsc_s35_12mp_4k_lockout_and_face_eye_af_clean_hdmi_guard`
- **`[APS-C S35 Shooting]` `12.1MP` 全画幅传感器 `4K` 视频 / `4264x2408` `HDMI RAW` 强制锁断**：
  - [`compute_apsc_s35_movie_format_lockout_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L920-L965)、[`resolve_fx3_apsc_s35_and_face_eye_af_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L968-L1119) 与 [`verify_apsc_s35_and_face_eye_af_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L1122-L1442) 建模 `MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]`（`Auto` 出厂默认 / `On` ~`1.5x` Super 35mm / `Off` 35mm 全画幅，受 `[Camera Settings Reset]` 与 `[Initialize]` 复位、不受 `[Reset Network Set.]` 影响），在全部 `60` 组视频状态下强制证明：`ILME-FX3`（`ilc/2210`，`12.1MP`）在录制 `4K` 视频（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`）或开启 `4264x2408` `HDMI RAW Output` 时将 `[APS-C S35 Shooting]` 锁定为 `[Off]`，Super 35mm 视频录制仅限 `HD`（`XAVC S HD` / `XAVC S-I HD`；`apsc_s35_4k_or_raw_bypass_events == 0`）。
- **`[Face/Eye AF]` BIONZ XR 菜单层级、纯净 HDMI 隔离与 `[Face Memory]` 跨复位留存**：
  - 严格锁定 `MENU -> Focus -> [Face/Eye AF]`（拒绝伪造独立 AI 芯片机型 `[Subject Recog in AF]`，`ai_unit_subject_recog_spoof_events == 0`），覆盖 `[Face/Eye Prior. in AF]`（`Intelligent Auto` 锁定 `On`）、`[Face/Eye Subject]`（`Human` / `Animal` / `Ver. 3.00+` `Bird`）、`[Right/Left Eye Select]`（含 `[Switch Right/Left Eye]` 自定义键切换）、`[Face/Eye Frame Disp.]`（`[HDMI Info. Display] = [Off]` 与 `HDMI RAW Output` 绝不烧录对焦框，`hdmi_clean_feed_eye_frame_baked_pixels == 0`），并校验已注册 `[Face Memory]` 数据库在 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 下完整留存（仅由显式删除或 `[Initialize]` 清空）。

### 2.3 Gate G104：`G104_version_readonly_airplane_badge_and_bodydata_flash_block_guard`
- **`[Version]` 只读查看与零射频台架更新红点抑制**：
  - [`resolve_fx3_version_readonly_and_bodydata_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L1527-L1589) 与 [`verify_version_readonly_and_bodydata_flash_block_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L1592-L1801) 建模 `MENU -> Setup -> [Setup Option] -> [Version]` 对机身（`Ver. 7.02`）、E 卡口镜头与卡口转接环版本的纯只读查看（`version_dialog_flash_writes == 0`），并强制零射频台架（`Airplane Mode = On`）抑制 `Ver. 6.00+`/`7.02` 固件更新通知红点（`passive_tx_bytes_emitted == 0`）。
- **Slot-1 `BODYDATA.DAT` 自动固件刷写硬阻断（HARD-BLOCKED / NO-GO）**：
  - 面向一切自动化 Agent 强制阻断 Slot-1 `BODYDATA.DAT` 刷写（`persistent_emmc_writes_authorized == False`、`bodydata_flash_attempts_blocked >= 1`、`slot1_bodydata_vault_mutation_bytes == 0`），人工物理升级前置条件（`NP-FZ100 >= 3 格 / >= 51%` 与原厂签名 `BODYDATA.DAT`）仅作只读咨询校核、绝不授予自动化刷写权限。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 冷备与恢复检查点门禁在离线默认模式下按设计保持待命阻断（`101/104`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 263 双模式定向单测（68 项 $\times$ 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `68/68 OK`（`3.444s`）+ `68/68 OK`（`1.857s`），均 `< 4s` |
| Phase 259 前序 102 门回归单测 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase259_auto_slow_shutter_hdmi_reccontrol_breathing_102gate_guard.py` | `68/68 OK`（`4.544s`） |
| CLI `verify-104-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-104-gates`（及 `--force-clean-room`） | `verified=101/104`（`VERIFIED_101_OF_104_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-104-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-104-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=104/104`（`VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 254 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY`（`286e0541437c8d7b...`）+ `CLEAN_ROOM_SYNTHETIC`（`f433a8af9e8f8238...`）`status=OK` |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`ad61d0de3fa05e71...`）+ `CLEAN_ROOM_SYNTHETIC`（`5fd5916b8095c202...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`dd0d32f3a4f51aa0...`）+ `CLEAN_ROOM_SYNTHETIC`（`5d035d2b5ec6c1d7...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（`0.07s`，零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/outputs/fx3-safety/tests/test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py)
6. [`reports/2026-11-15-phase263-safety-104gates-apsc-s35-face-eye-af-version/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h296-phase263-safety-104gates-apsc-s35-face-eye-af-version/reports/2026-11-15-phase263-safety-104gates-apsc-s35-face-eye-af-version/README.md)
