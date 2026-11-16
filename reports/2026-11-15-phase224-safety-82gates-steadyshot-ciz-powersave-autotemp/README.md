# Phase 224 安全护栏报告：Gates G81 / G82 与统一 `verify-82-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-31 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G81`、`G82` 与统一 `82-Gate` 主预检引擎（`G01..G82`）闭环交付**：
   - 新增模块 [`realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py)（将 `G01..G80` 直接委托给 [`evaluate_80gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py#L1443-L1672)，`100%` 保留 `verify-58-gates` 至 `verify-80-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/README.md)。
2. **双模式全量测试与 CLI 实测 100% 通过（实测事实）**：
   - 新增 [`test_phase224_steadyshot_ciz_powersave_autotemp_82gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/tests/test_phase224_steadyshot_ciz_powersave_autotemp_82gate_guard.py) 共 **60 项**双模式单元测试（要求 `>=50`），在 `LOCAL_DONOR_O_RDONLY`（`5.051s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.578s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1743/1743` 全部通过（`117.880s`）**，Clean-Room 合成模式 **`1743` 项运行通过、`1` 项按设计跳过（`77.266s`）**；
   - CLI `verify-82-gates`：默认离线模式通过 **`79/82`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`82/82`**；
   - BYOF 与字节码卫生审计：`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`（零 `.pyc`、零固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G81 与 Gate G82 技术建模要点

### 2.1 Gate G81：`G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD`
- **影片 `[SteadyShot]`（`Active` 窄视角裁切 `~1.1x` vs `Standard` / `Off`）三大禁用红线与手动焦距边界**：
  - [`resolve_fx3_steadyshot_movie_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L835-L870) 与 [`verify_steadyshot_active_cutoff_and_ciz_4lock_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L898-L1181) 严格建模 `MENU -> Shooting -> [Image Stabilization] -> [SteadyShot]`：在① 常规影片 `119.88p`/`100p`、② `S&Q` `[Frame Rate]` `>=120fps`/`100fps`（`100fps`/`120fps`/`200fps`/`240fps`）、③ 外接 HDMI `[RAW Output] = [On]` 任一条件下禁止启用 `[Active]`（`BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF`）；同时拦截 `[Active]` 下窄视角裁切抑制（`<1.08x`）及手动 `[SteadyShot Focal Len.]` 越界（限定 `8mm..1000mm` -> `BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION`）。
- **`[Clear Image Zoom]` / `[Digital Zoom]`（`[Zoom Range]`）RAW/HFR 阻断与 4 项强制状态锁**：
  - [`resolve_fx3_zoom_and_4locks()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L873-L895) 阻断静态 `[File Format]` 为 `RAW` / `RAW & JPEG` / `RAW & HEIF`、常规影片 `119.88p`/`100p`、`S&Q` `100fps`/`120fps`/`200fps`/`240fps` 下的非光学变焦，并校验 `4K` `1.5x` / `HD` `2.0x` `Clear Image Zoom` 与 `4.0x` `Digital Zoom` 倍率上限（`BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN`）；
  - 当任一非光学变焦激活时，强制校验全部 **4 项相机自动锁定状态**：① `[Focus Area]` 设置禁用并切至中心优先对焦、② `[Metering Mode]` 硬锁为 `[Multi]`、③ `[Face/Eye Prior. in AF]` 与 `[Face Priority in Multi Metering]` 禁用、④ `Real-time Tracking` 不可用（`BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase224_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L687-L828) 以 `os.open(..., os.O_RDONLY)` 校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 确定性合成兜底。

### 2.2 Gate G82：`G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD`
- **精确菜单项 `[Power Save Start Time]`、9 项自动休眠解除条件与离线 `NP-FZ100` Tier-0 `75 MiB` `p3` 冷备防休眠门禁**：
  - [`resolve_fx3_power_save_9cond_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L1266-L1298) 与 [`verify_powersave_9cond_and_autotemp_tripod_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L1350-L1496) 强制校验 `MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]` 精确字符串及 6 档选项（`Off`、`30 Min`、出厂默认 `5 Min`、`2 Min`、`1 Min`、`10 Sec` -> `BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID`）；
  - 完整建模 9 项自动解除自动休眠条件（USB 供电、幻灯片播放、FTP 传输、影片录制、PC 连接、TV/HDMI 连接、`[IR Remote Ctrl] = [On]`、`[Bluetooth Rmt Ctrl] = [On]`、流媒体 / Creators' Cloud 上传）并拦截不一致上报（`BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH`）；
  - 气隙隔离纯内置 `NP-FZ100` 电池（无 USB/HDMI/FTP/Remote/PC/Streaming）执行 Tier-0 `75 MiB` `p3` 冷备预检时，强制要求 `[Power Save Start Time]` 设为 `Off` 或 `30 Min`，严禁默认 `5 Min` 或更短档位在空闲阶段意外休眠中断备份（`BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD`）。
- **`[Auto Power OFF Temp.]`（`Standard` vs `High`）三脚架强制要求与 `[Fan Control]` 热安全耦合**：
  - [`resolve_fx3_auto_power_off_temp_and_fan()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L1301-L1347) 强制要求当 `[Auto Power OFF Temp.] = [High]` 时必须满足 `tripod_mounted == True` 且禁止长时间手持拍摄，阻断低温接触烫伤隐患（`BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD`）；同时禁止 `High` 模式下设置 `[Fan Control] = [Always Off]`，并联动 `>=62.0C` 录制风扇接管阈值与 `>=90.0C` 熔断上限（`BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts）

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 224 双模式定向单测（60 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_phase224_*.py'`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `60/60 OK`（`5.051s`）+ `60/60 OK`（`2.578s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 1743 tests in 117.880s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 1743 tests in 77.266s — OK (skipped=1)` |
| CLI `verify-82-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-82-gates`（及 `--force-clean-room`） | `verified=79/82`（`VERIFIED_79_OF_82_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-82-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-82-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=82/82`（`VERIFIED_ALL_82_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase224_steadyshot_ciz_powersave_autotemp_82gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/outputs/fx3-safety/tests/test_phase224_steadyshot_ciz_powersave_autotemp_82gate_guard.py)
6. [`reports/2026-11-15-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h248-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/reports/2026-11-15-phase224-safety-82gates-steadyshot-ciz-powersave-autotemp/README.md)
