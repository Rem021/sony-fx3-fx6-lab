# Phase 266 安全护栏报告（Task H300 第 300 项里程碑）：Safety Gates `G105` / `G106` 与统一 `verify-106-gates` 预检引擎（`outputs/fx3-safety/`，Wave-43）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-43 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）安全门禁 `G105`、`G106` 与统一 `106` 门主预检引擎（`G01..G106`）闭环交付**：
   - 新增模块 [`realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py)（Schema `realhw_release_wo_card_audio_meter_copyright_and_106gate_guard_v1` `v1.0.0`），将 `G01..G104` 直接委托给 [`evaluate_104gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py#L1867-L2096)（`100%` 保留 `G1..G104`、`evaluate_102gate_preflight` 与 `evaluate_104gate_preflight` 向后兼容），同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 `118` 个 Phase 266 专属符号及子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-release-wo-card-lens-audio-disp-guard` / `verify-g105-release-wo-card-audio-disp`、`verify-copyright-info-46char-exif-hygiene-guard` / `verify-g106-copyright-info-hygiene` 与 `verify-106-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/README.md)。
2. **双模式 70 项单测（均 `< 4.0s`）、Milestone 254 / 233 / 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase266_release_wo_card_audio_meter_copyright_106gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/tests/test_phase266_release_wo_card_audio_meter_copyright_106gate_guard.py) 共 **70 项**双模式单元测试（要求 `>= 68` 项且 `< 4.0s`），在 `LOCAL_DONOR_O_RDONLY`（`3.102s`）、`FX3_CLEAN_ROOM_TEST=1`（`1.131s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.112s`）下全部 `OK` 通过；
   - CLI `verify-106-gates`：默认离线模式通过 **`103/106`**（`VERIFIED_103_OF_106_AWAITING_PHYSICAL_TIER0`，3 道物理台架 Tier-0 收据门禁 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `--force-clean-room` 下均通过 **`106/106`**（`VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_106_gates_verified=True`）；
   - 跨模块里程碑与仓库卫生检查：`make verify-milestone-254`、`make verify-milestone-233` 与 `make verify-milestone-221` 双模均为 `status=OK`，`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`（零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G105` 与 Gate `G106` 技术建模要点（Wave-43 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与双环境变量 Clean-Room 兜底
- [`audit_phase266_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py#L822-L984) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（`cpapp-b.bin`、FX3 `libgpe.so`、FX3 `libSaveLoadSettings.so`、FX3 `FX3-CX95900_ALLLANG-Backup.bin`、FX6 `libInfraDial.so` 与 FX6 `CX95898_NTSC.bin`），实测耗时 `0.0226s < 0.10s` 且 `raw_firmware_bytes_leaked == 0`，并同时响应 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 切换为确定性 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate `G105`：`GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD`
- **`[Release w/o Card]` 仅静态照片作用域 vs 视频内录存储卡门控 & `[Release w/o Lens]` 零 `E-ND` / 零镜头串口流量护栏**：
  - [`compute_release_wo_card_and_lens_scope_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py#L991-L1042) 与 [`verify_release_wo_card_lens_and_v702_audio_disp_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py#L1216-L1569) 穷举验证全部 `96` 组状态组合：`MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]`（`Enable` 默认 / `Disable`）仅控制无卡静态快门释放（生产实拍强制 `[Disable]` 防漏拍，无卡诊断台架允许 `[Enable]` 且 `cardless_media_sector_writes == 0`），而双卡槽为空时内部视频/`S&Q` 录制始终硬阻断（`movie_cardless_internal_rec_bypass_events == 0`），外部 HDMI 录机录制由 `[Rec. Media dur HDMI Output]` 独立管辖；`[Release w/o Lens]`（`Enable` 默认 / `Disable`）覆盖 `Still` + `Movie` + `S&Q` 全模式，并在单机身/纯机械 PL 转接台架上强制 `e_nd_actuator_tx_count == 0` 与 `emount_lens_uart_tx_bytes == 0`。
- **`Ver. 2.00+`/`7.02`（`ilc/2210`）精确 5 项 `[Audio Recording]` 菜单 vs `Ver. 1.x`（`ilc/2035`）独立 `[Audio Level Display]` 移除与 `DISP` 电平表治理**：
  - 锁定 `MENU -> Shooting -> [Audio Recording]` 精确 5 项（`Audio Recording` `On`/`Off`、`Audio Rec Level` `0..31`、`Audio Out Timing` `Live`/`Lip Sync`、`Wind Noise Reduct.` `On`/`Off`、`Shoe Audio Set.`），拒绝伪造 `Ver. 1.x` 独立 `[Audio Level Display]` 菜单项（`legacy_v1_audio_level_menu_spoof_events == 0`），并验证 `2ch`/`4ch` 音频电平表显隐（`S&Q` 模式下硬件抑制）由 `MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]` 管辖且跨 `[Camera Settings Reset]` 留存。

### 2.3 Gate `G106`：`GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD`
- **`[Copyright Info]` `<= 46` 字符 ASCII 边界、纯静态照片 EXIF 作用域、跨复位留存与台架 PII 隐私卫生护栏**：
  - [`verify_copyright_info_46char_still_exif_and_pii_hygiene_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py#L1715-L1911) 建模 `MENU -> Shooting -> [File] -> [Copyright Info]` 精确 4 子项（`Write Copyright Info` `Off` 默认 / `On`、`Set Photographer` `<= 46` 可打印 ASCII 字符、`Set Copyright` `<= 46` 可打印 ASCII 字符、只读 `Disp. Copyright Info`），严格限定仅静态照片（`JPEG`/`HEIF`/`ARW`）写入 EXIF `0x013B` / `0x8298` 标签，绝不篡改 `XAVC`/`HDMI RAW` 视频流或 `Slot-1` 恢复保险库（`movie_or_raw_exif_mutation_bytes == 0`、`slot1_recovery_vault_mutation_bytes == 0`），验证字符串跨 `[Camera Settings Reset]` 留存、仅由 `[Initialize]` 清空、排除于 `CAMSET01..10.DAT` 导出之外，并强制无尘台架默认 `Write Copyright Info = Off` 与零操作员 PII 残留（`photographer_copyright_pii_leaked_bytes == 0`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`103/106`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 266 双模式定向单测（70 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase266_release_wo_card_audio_meter_copyright_106gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `70/70 OK`（Donor `3.102s`）+ `70/70 OK`（`FX3_CLEAN_ROOM_TEST=1` `1.131s`）+ `70/70 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `1.112s`），均 `< 4.0s` |
| Phase 263 前序 104 门回归单测 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase263_apsc_s35_face_eye_af_version_104gate_guard.py` | `68/68 OK`（`3.148s`） |
| CLI `verify-106-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-106-gates`（及 `--force-clean-room`） | `verified=103/106`（`VERIFIED_103_OF_106_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-106-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-106-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=106/106`（`VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_106_gates_verified=True`，`rc=0`） |
| Milestone 254 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY`（`05fa6e721dae20b7...`）+ `CLEAN_ROOM_SYNTHETIC`（`ad8a95e6bd685221...`）`status=OK` |
| Milestone 233 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233` | `LOCAL_DONOR_O_RDONLY`（`0256bc15302eeb69...`）+ `CLEAN_ROOM_SYNTHETIC`（`e51ebb88114fa37a...`）`status=OK` |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY`（`a9ba94510e1186e0...`）+ `CLEAN_ROOM_SYNTHETIC`（`34c022f1b3c8e315...`）`status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（零 `.pyc`、零固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase266_release_wo_card_audio_meter_copyright_106gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/outputs/fx3-safety/tests/test_phase266_release_wo_card_audio_meter_copyright_106gate_guard.py)
6. [`reports/2026-11-15-phase266-safety-106gates-release-wo-card-audio-meter-copyright/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h300-phase266-safety-106gates-release-wo-card-audio-meter-copyright/reports/2026-11-15-phase266-safety-106gates-release-wo-card-audio-meter-copyright/README.md)
