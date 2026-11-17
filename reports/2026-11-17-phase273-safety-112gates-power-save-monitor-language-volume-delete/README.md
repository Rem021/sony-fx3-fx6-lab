# Phase 273 安全护栏报告（Task H309，`112/112` Safety Gates）：Wave-46 Safety Gates `G111` / `G112` 与统一 `verify-112-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 273（Task H309，`112/112` Safety Gates）闭环交付，将 Wave-46 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01` 与共享 `BIONZ XR` `appFw.so` 实机情报转化为确定性安全门禁 `G111`、`G112` 及统一 `112` 门主预检引擎（`G01..G112`）**：
   - 新增模块 [`realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py)（Schema `realhw_power_save_monitor_language_volume_delete_and_112gate_guard_v1` `1.0.0`），将 `G01..G110` 零重复委托给 [`evaluate_110gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py)（`Phase 273` 增量审计与 `G111`/`G112` 仅新增 **`0.0055s`（5.5 ms）**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 273 专属符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-power-save-monitor-language-guard` / `verify-g111-power-save-monitor-language`、`verify-volume-4chmon-delete-confirm-guard` / `verify-g112-volume-4chmon-delete-confirm` 与 `verify-112-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/README.md) 第 56 节。
2. **三模式 76 项双模单测、`verify-112-gates`、Milestone 264 回归与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_power_save_monitor_language_volume_delete_112gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/tests/test_realhw_power_save_monitor_language_volume_delete_112gate_guard.py) 共 **76 项**双模单元测试（满足 `>= 70` 项；全量 subprocess 均使用 `sys.executable`，`argparse` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 充裕时间窗），在 `LOCAL_DONOR_O_RDONLY`（`3.404s`）、`FX3_CLEAN_ROOM_TEST=1`（`3.441s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`3.459s`）下均 **`76/76 OK`**；
   - CLI `verify-112-gates`：默认离线模式通过 **`109/112`**（`VERIFIED_109_OF_112_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` 按安全规则 fail-closed 待命），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `--force-clean-room` 下均通过 **`112/112`**（`VERIFIED_ALL_112_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_112_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`b67ab83b7ed048d3...` / `84b509a0b7ef1f83...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.69s`，且全量 `outputs/fx3-safety/tests` discovery 实测 **`Ran 2763 tests in 96.947s — OK`**。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G111` 与 Gate `G112` 技术建模要点（Wave-46 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase273_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py) 严格使用 `os.open(..., os.O_RDONLY)`，并对 `79,015,712 B` 共享 `appFw.so` 采用有界定点 `os.pread`（16 个 Wave-46 切片 SHA-256 `8724dfd01427cb55...`）与其余 7 份 donor（`string_english_f.uxc`、FX3 `string_english.uxc`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` `BK_LANG @ 0x90ff0 = 0`、FX6 `CX95898_NTSC.bin` `BK_LANG @ 0x89242 = 0x00`、`CX95899_CN1.bin` `BK_LANG @ 0x89242 = 0x19`、FX6 `string_english.uxc`）进行完整校验。
- 实测耗时 **`0.0052s < 0.20s`**，`spoof_open_on_close_off_absent_in_uxc == True`，`raw_firmware_bytes_leaked == 0`，并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G111`：`GATE_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD`
- **`[Power Save by Monitor]` 实机 UI 现实分裂与 `appFw.so` 4 模式建模**：
  - 锁定原厂 `ILME-FX3 Ver. 7.02`（`ilc/2210`）`[Setup] -> [Power Setting Option]` **仅暴露 2 项**（`[Power Save Start Time]` 与 `[Auto Power OFF Temp.]`），`fx3_ui_exposes_power_save_by_monitor == False`，严厉拦截任何伪造 `"Open: On/Close: Off"` 字符串或虚假 UI 暴露（`STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION`）。
  - 精确建模共享 `BIONZ XR` `appFw.so`（`BKID_APP_setting_monitor_power_linkage`）+ `string_*_f.uxc`（`0x60b9`）编译的 4 种模式：`Both Linked`（`0x6db5` / `ON_ALL`）、`Open: Return`（`0x6db6` / `ON_OPEN`）、`Close: Power Save`（`0x60a8` / `ON_CLOSE`）、`Does Not Link`（`0x6b2e` / `OFF`）；在暴露该项的兄弟机身无头合屏 HDMI 台架审计中，强制要求 `Does Not Link` 或 `Open: Return`（`STATUS_BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD`）。
- **`[Power Save Start Time]` 9 大官方去激活条件台架护栏**：
  - 完整建模 `Off` / `30 Min` / `5 Min`（默认）/ `2 Min` / `1 Min` / `10 Sec` 与 Sony 官方 **9 项**去激活绕过条件（`USB power supply`、`slideshow playback`、`FTP transfer`、`movie recording`、`PC connection`、`TV/HDMI connection`、`IR Remote Ctrl = On`、`Bluetooth Rmt Ctrl = On`、`streaming / Creators' Cloud upload`）；当无任何激活绕过条件的隔空电池台架启用 `< 30 Min` 休眠档位时拦截为 `STATUS_BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD`。
- **`[Language]` `BK_LANG`（`0x02cf019c`）34-vs-29 对齐与 `(Setup)` 跨复位留存**：
  - 校验 `FX3` `34` 语种（`0x90ff0` 4B LE `= 0`）与 `FX6` `29` 语种（`0x89242` 1B `NTSC=0x00` / `CN1=0x19`）、Stage-B 4 语种（`en=0x00`、`schinese=0x19`、`tchinese=0x18`、`japanese=0x01`）及 `(Setup)` 跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 留存、仅 `[Initialize]` 清零，且经 [`compute_power_save_monitor_and_language_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py) 穷举验证全部 **`192`** 组状态组合。

### 2.3 Gate `G112`：`GATE_G112_VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD`
- **`[Volume Settings]`（`0..15`，默认 `7`）与 `XLR-H1` 声学啸叫护栏**：
  - 锁定 `MENU -> Setup -> [Sound Option] -> [Volume Settings]`（`resid16=0xe8c9`，离散 `0..15`，默认 `7`），严格隔离 `[Audio signals]` 混淆，并在开启 `XLR-H1` MI-Shoe 麦克风且未插耳机使用机内扬声器播放时限制 `volume <= 7`（`STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION`）。
- **`[4ch Audio Monitoring]`（5 路由）与 `3.5 mm` 2ch 物理边界**：
  - 锁定全部 **5** 项监听路由（`CH1/CH2` 默认 `0x713b`、`CH3/CH4` `0x6bf6`、`CH1+3/CH2+4` `0x6c2e`、`CH1/CH1` `0x6f9c`、`CH2/CH2` `0x7a26`），区别于 HDMI `[4ch Audio Output]`（`CH1/CH2` / `CH3/CH4`，`0x6aa0`），严禁声明 `3.5 mm` 物理口输出离散 4 声道（`STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION`）。
- **`[Delete confirm.]` `"Cancel" first` 默认与 `Slot-1` 恢复保险库删除/格式化防火墙**：
  - 锁定 `[Delete confirm.]`（`"Cancel" first` 默认 `0xe724`/`0x6a5e` vs `"Delete" first` `0xe725`/`0x6e0a`）与 `[Delete pressing twice]`（`Off` 默认 `0x74db`）跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 重置），硬锁拦截任何指向 `Slot 1` 恢复保险库的单张/多选/目录/日期删除、`Delete pressing twice` 或格式化请求（`slot1_vault_delete_events == 0`、`slot1_format_hard_locked == True`、`STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION`），并穷举验证全部 **`240`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令（含全量 `2763` 项 `fx3-safety` 测试发现）均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`109/112`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 273 双模定向单测（76 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_power_save_monitor_language_volume_delete_112gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `76/76 OK`（Donor `3.404s`）+ `76/76 OK`（`FX3_CLEAN_ROOM_TEST=1` `3.441s`）+ `76/76 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `3.459s`） |
| CLI `G111` / `G112` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-power-save-monitor-language-guard` / `verify-volume-4chmon-delete-confirm-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0` |
| CLI `verify-112-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-112-gates` | `verified=109/112`（`VERIFIED_109_OF_112_AWAITING_PHYSICAL_TIER0`，`rc=0`，Phase 273 增量耗时 `0.0055s`） |
| CLI `verify-112-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-112-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=112/112`（`VERIFIED_ALL_112_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_112_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`b67ab83b7ed048d3...`）+ `CLEAN_ROOM_SYNTHETIC`（`84b509a0b7ef1f83...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 2763 tests in 96.947s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.69s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_power_save_monitor_language_volume_delete_112gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/outputs/fx3-safety/tests/test_realhw_power_save_monitor_language_volume_delete_112gate_guard.py)
6. [`reports/2026-11-17-phase273-safety-112gates-power-save-monitor-language-volume-delete/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h309-phase273-safety-112gates-power-save-monitor-language-volume-delete/reports/2026-11-17-phase273-safety-112gates-power-save-monitor-language-volume-delete/README.md)
