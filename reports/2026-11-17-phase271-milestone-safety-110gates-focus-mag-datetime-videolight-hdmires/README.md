# Phase 271 里程碑安全护栏报告（Task H306，`110/110` Safety Gates）：Wave-45 Safety Gates `G109` / `G110` 与统一 `verify-110-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 `110/110` 安全门禁里程碑（Phase 271 / Task H306）闭环交付，将 Wave-45 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）实机情报转化为确定性安全门禁 `G109`、`G110` 与统一 `110` 门主预检引擎（`G01..G110`）**：
   - 新增模块 [`realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)（Schema `realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard_v1` `v1.0.0`），将 `G01..G108` 直接委托给 [`evaluate_108gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_file_settings_gamma_assist_tcub_and_108gate_guard.py#L2289-L2509)（`100%` 保留 `G01..G108` 与历史预检命令向后兼容）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 271 专属符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-focus-mag-peaking-af-illuminator-guard` / `verify-g109-focus-mag-peaking`、`verify-area-datetime-videolight-hdmires-guard` / `verify-g110-datetime-videolight-hdmires` 与 `verify-110-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/README.md)。
2. **三模式 74 项双模单测、Milestone 264 回归、CLI `verify-110-gates` 与 BYOF/字节码卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase271_focus_mag_datetime_videolight_hdmires_110gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/tests/test_phase271_focus_mag_datetime_videolight_hdmires_110gate_guard.py) 共 **74 项**双模单元测试（要求 `>= 70` 项，全部 subprocess 调用使用 `sys.executable`、微基准断言含 `GITHUB_ACTIONS == "true"` 裕量），在 `LOCAL_DONOR_O_RDONLY`（`3.487s`）、`FX3_CLEAN_ROOM_TEST=1`（`1.660s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.637s`）下全部 `OK` 通过；
   - CLI `verify-110-gates`：默认离线模式通过 **`107/110`**（`VERIFIED_107_OF_110_AWAITING_PHYSICAL_TIER0`，物理台架 Tier-0 收据门禁 `G10..G12` fail-closed 待命），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `--force-clean-room` 下均通过 **`110/110`**（`VERIFIED_ALL_110_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_110_gates_verified=True`）；
   - 前序回归与仓级卫生：`test_phase268` `72/72 OK`（`2.814s`）、`make verify-milestone-264` 双模 `status=OK`（`c02f5e0117fb3300...` / `9b43ed7538702b4a...`）、`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.03s`。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G109` 与 Gate `G110` 技术建模要点（Wave-45 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与双环境变量 Clean-Room 兜底
- [`audit_phase271_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py#L449-L579) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 6 个本地固件工件（FX3 `cpapp-b.bin`、`libgpe.so`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 FX6 `libInfraDial.so`、`CX95898_NTSC.bin`），实测耗时 `0.0393s < 0.10s`、`raw_firmware_bytes_leaked == 0`，并在 `FX3_CLEAN_ROOM_TEST=1` 或 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时确定性切换为 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate `G109`：`GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD`
- **`[Focus Assistant]` 精确菜单命名、默认绑定与独立倍率寄存器**：
  - [`compute_focus_mag_peaking_af_illuminator_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py#L586-L633) 与 [`verify_focus_mag_peaking_af_illuminator_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py#L712-L977) 穷举验证全部 `144` 组状态：
  - 锁定 `ILME-FX3 Ver. 7.02`（`ilc/2210`）`MENU -> Focus -> [Focus Assistant]`：`[Auto Magnifier in MF] = [On]` 默认（严厉拒绝旧机型 `"MF Assist"` 命名伪造：`legacy_mf_assist_spoof_events == 0`）、`[Focus Magnifier]` 默认绑定 `Custom Button 5`、`[Focus Magnif. Time] = [No Limit]` 默认（`2 Sec` / `5 Sec` / `No Limit`）、静态照片与视频各自独立的 `[Initial Focus Mag.]` 寄存器且均默认 `[x1.0]`（`x1.0` / `x4.0` 互不串扰），以及纯静态 `[AF in Focus Mag.] = [On]` 默认（Movie/`S&Q` 中 `0` 次触发）。
- **`[Peaking Display]` 干净 HDMI 隔离与纯静态 `[AF Illuminator]` 约束**：
  - 锁定 `[Peaking Display]`（`Off` 默认、`[Peaking Level] = [Mid]`、`[Peaking Color] = [White]`、默认分配至 `Control Wheel Right`）与对焦放大叠层在 `[HDMI Info. Display] = [Off]` 或 `HDMI RAW` 下的干净 HDMI 隔离（`hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`），以及 `[AF Illuminator]`（`Auto` 默认 / `Off`）严格限于静态照片自动对焦（`movie_sq_af_illuminator_fire_events == 0`）。

### 2.3 Gate `G110`：`GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD`
- **`[Area/Date/Time Setting]` 命名防伪、跨复位留存与零射频 Creators' App 抑制**：
  - [`compute_area_datetime_videolight_hdmires_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py#L1044-L1101) 与 [`verify_area_datetime_videolight_hdmires_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py#L1177-L1486) 穷举验证全部 `256` 组状态：
  - 锁定 `MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]`（严厉拒绝旧命名 `"Date/Time Setup"` 伪造：`legacy_datetime_setup_spoof_events == 0`；含 `[Area Setting]`、`[Daylight Savings] = [Off]` 默认、`[Date/Time]`、`[Date Format]` 4 项），验证跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 留存（仅 `[Initialize]` 或 RTC 备电丢失清零并要求重设），并在零射频台架（`[Airplane Mode] = [On]`）下强制屏蔽 Creators' App `[Auto Time Correction]` / `[Auto Area Adjustment]`（`passive_tx_bytes_emitted == 0`、`unsolicited_rtc_timezone_jump_events == 0`）。
- **`[Video Light Mode]` MI-Shoe `900 mA` 预算与 `[HDMI Resolution]` Log 内录 `1080p` 强降档规则**：
  - 验证 `[Video Light Mode]`（`[Power Link]` 默认 / `[REC Link]` / `[REC Link & STBY]` / `[Auto]`）属 `[Setup]` 跨 `[Camera Settings Reset]` 留存及 MI-Shoe `5V <= 900 mA`（`G24`）供电上限护栏（`mishoe_5v_overcurrent_events == 0`）；
  - 验证 `[HDMI Resolution]`（`[Auto]` 默认 / `2160p` / `1080p` / `1080i`）跨 `[Camera Settings Reset]` 留存，以及在开启 `[Log Shooting]` 且内录激活并设 `Rec. Media dur HDMI Output = On` 时硬件强制 `1080p` 降档覆写手动 `2160p` 的逻辑（`hdmi_res_log_internal_rec_2160p_bypass_events == 0`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`107/110`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 271 双模定向单测（74 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase271_focus_mag_datetime_videolight_hdmires_110gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `74/74 OK`（Donor `3.487s`）+ `74/74 OK`（`FX3_CLEAN_ROOM_TEST=1` `1.660s`）+ `74/74 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `1.637s`） |
| Phase 268 前序 108 门回归单测 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase268_file_settings_gamma_assist_tcub_108gate_guard.py` | `72/72 OK`（`2.814s`） |
| CLI `G109` / `G110` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-g109-focus-mag-peaking` / `verify-g110-datetime-videolight-hdmires` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0` |
| CLI `verify-110-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-110-gates` | `verified=107/110`（`VERIFIED_107_OF_110_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-110-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-110-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=110/110`（`VERIFIED_ALL_110_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_110_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`c02f5e0117fb3300...`）+ `CLEAN_ROOM_SYNTHETIC`（`9b43ed7538702b4a...`）均 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.03s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase271_focus_mag_datetime_videolight_hdmires_110gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/outputs/fx3-safety/tests/test_phase271_focus_mag_datetime_videolight_hdmires_110gate_guard.py)
6. [`reports/2026-11-17-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h306-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/reports/2026-11-17-phase271-milestone-safety-110gates-focus-mag-datetime-videolight-hdmires/README.md)
