# Phase 246 安全护栏里程碑报告：`94/94` Safety Gates G93 / G94 与统一 `verify-94-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-37 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G93`、`G94` 与统一 `94/94` 里程碑主预检引擎（`G01..G94`）闭环交付**：
   - 新增模块 [`realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py)（Schema `realhw_framing_usbpower_lun_antiflicker_and_94gate_guard_v1` `v1.0.0`），将 `G01..G92` 直接委托给 [`evaluate_92gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py#L2031-L2264)（`100%` 保留 `verify-58-gates` 至 `verify-92-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase246_framing_usbpower_lun_antiflicker_94gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/tests/test_phase246_framing_usbpower_lun_antiflicker_94gate_guard.py) 共 **66 项**双模式单元测试（要求 `>=62` 且 `<5s`），在 `LOCAL_DONOR_O_RDONLY`（`3.118s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.557s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`2129/2129` 全部通过（`135.280s`）**，Clean-Room 合成模式 **`2128` 项通过、`1` 项按设计跳过（`74.439s`）**；
   - CLI `verify-94-gates`：默认离线模式通过 **`91/94`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`94/94`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`（零 `.pyc`、零专有固件字节泄露）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G93 与 Gate G94 技术建模要点（Wave-37 规范映射）

### 2.1 有界 `< 0.10s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase246_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L740-L890) 严格通过 `os.open(..., os.O_RDONLY)` 只读校验 5 个本地固件工件（`cpapp-b.bin`、`libUsbBusPower.so`、`libInfraMscServer.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`），保证 `raw_firmware_bytes_leaked == 0` 且 `< 0.10s`，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地 Donor 路径缺省时自动切换为 `CLEAN_ROOM_SYNTHETIC` 等价校验。

### 2.2 Gate G93：`G93_framing_asymmetric_crop_full_and_antiflicker_no_varshutter_guard`
- **`[Framing Settings]` 双路非对称 `Full`/`Crop` 默认值、重置行为与 `ZV-E1` 混淆拦截**：
  - [`resolve_fx3_framing_and_antiflicker_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L898-L984) 与 [`verify_framing_asymmetric_and_antiflicker_no_varshutter_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L987-L1305) 精确建模 `MENU -> Shooting -> [Framing Settings]`（配合 Sony *Monitor & Control* 控制）：
    - 出厂与重置契约：`[Framing]=Off`、`[Recording/Streaming]=Full`（机内存储卡保留全画幅主素材）、`[HDMI]=Crop`（外部监看输出裁切构图），三者在 `[Camera Settings Reset]` 与 `[Initialize]` 下均恢复出厂默认值（违例阻断：`BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION`）；
    - HDMI `RAW` 互斥锁：当 `[Framing]=On` 时严禁开启 HDMI `RAW` 输出（违例阻断：`BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT`）；
    - 机型精确命名防火墙：`ILME-FX3`（`ilc/2210`）仅提供 `[Framing Settings]`，拒绝将消费级 `ZV-E1`（`ilc/2330`）的 `[Autoframing Settings]` 混入校验（违例阻断：`BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION`）。
- **`[Anti-flicker Shoot.]` 仅限机械快门静态照片作用域与原厂无 `[Var. Shutter]` 防火墙**：
  - 建模 `MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]`（`Off` 默认 / `On`，`[Camera Settings Reset]` 可重置）：仅在 `Still` 静态拍摄 + `Mechanical` 机械快门 + `[Silent Mode]=Off` 下检测 `100 Hz` / `120 Hz` 频闪；在 `Movie` / `S&Q Motion` 或电子快门 / `[Silent Mode]=On` 下完全不生效（违例阻断：`BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION`）；
  - 硬锁原厂 `ILME-FX3`（`ilc/2210` 至 `Ver. 7.02`）无 `[Var. Shutter]` 菜单项（`fx3_has_var_shutter == False`），拦截任何误套用 `ILME-FX30`（`ilc/2220` `[Var. Shutter]`）、`ILCE-6700`（`ilc/2320`）或 `ILME-FX6`（`ECS`）的跨机型假设（违例阻断：`BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION`）。

### 2.3 Gate G94：`G94_usb_power_npfz100_typec_interlock_and_usb_lun_setup_persistence_guard`
- **`[Setup] -> [USB]` 跨 `[Camera Settings Reset]` 持久存活契约**：
  - [`resolve_fx3_usb_power_interlock_and_lun_persistence_state()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L1397-L1479) 与 [`verify_usb_power_npfz100_typec_and_lun_persistence_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py#L1482-L1728) 精确执行：`[USB Connection Mode]`（默认 `Sel. When Connect`）、`[USB LUN Setting]`（默认 `Multi`）与 `[USB Power Supply]`（默认 `On`）在 `[Camera Settings Reset]` 后保持原值不变，仅在 `[Initialize]` 时恢复出厂默认（违例阻断：`BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION`）。
- **`[USB Power Supply]` 两大硬件互锁**：
  - **强制插入 `NP-FZ100` 电池（或 `DC-C1` 假电池耦合器）**：未插入电池时无法仅靠 USB 墙插供电开机（`BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE`）；在 USB 供电运行途中拔出 `NP-FZ100` 会立即触发无缓冲掉电关机（`BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF`）；
  - **`USB Type-C` 独占供电/充电**：`Multi/Micro USB` 端子不支持供电或机内充电（`BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED`）。
- **`[USB LUN Setting]` 双卡槽可见性与台架主机 USB 硬阻断**：
  - 校验 `[MassStorage(MSC)]` 下 `Multi`（`2` LUN：Slot 1 + Slot 2）与 `Single`（`1` LUN：主记录槽）枚举契约（`BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH`），同时硬锁台架禁止直连主机 USB（`usb_packets_transmitted == 0`、`hardware_live_attachment_authorized == False`、`BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN`），强制使用离线 `WP` 写保护读卡器完成 Tier-0 SHA-256 核验。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读门禁（`G10..G12`）在离线默认模式下按设计保持待命阻断（`91/94`），唯有人工台架提供真机离线只读 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 246 双模式定向单测（66 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase246_framing_usbpower_lun_antiflicker_94gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `66/66 OK`（`3.118s`）+ `66/66 OK`（`1.557s`），均 `< 5s` |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2129 tests in 135.280s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 2129 tests in 74.439s — OK (skipped=1)` |
| CLI `verify-94-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-94-gates`（及 `--force-clean-room`） | `verified=91/94`（`VERIFIED_91_OF_94_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-94-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-94-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=94/94`（`VERIFIED_ALL_94_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase246_framing_usbpower_lun_antiflicker_94gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/outputs/fx3-safety/tests/test_phase246_framing_usbpower_lun_antiflicker_94gate_guard.py)
6. [`reports/2026-11-15-phase246-safety-94gates-framing-usbpower-lun-antiflicker/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h276-phase246-safety-94gates-framing-usbpower-lun-antiflicker/reports/2026-11-15-phase246-safety-94gates-framing-usbpower-lun-antiflicker/README.md)
