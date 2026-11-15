# Milestone Phase 131 — Virtual Production High-Energy DMX Strobe / UV-Arc `IMX510` CMOS Sensor Overload & External Tri-Level Sync / Multi-Terminal Backfeed Firewall (`Gate G41`), Vehicle / Helicopter Hard-Mount High-Frequency Vibration (`20..200 Hz`) `IBIS` Voice-Coil Thermal Resonance & Secondary Steel-Tether Guard (`Gate G42`), and Unified 42-Gate Master Safety Preflight (`G01..G42`)

# 里程碑第 131 阶段 — 虚拟制作高能 DMX 频闪 / UV 电弧 `IMX510` CMOS 传感器过载与外部三电平同步 / Multi-Terminal 倒灌防火墙（`Gate G41`）、车载 / 直升机硬装高频振动（`20..200 Hz`）`IBIS` 音圈热共振与二级钢索护栏（`Gate G42`）及 42 门禁主安全预检（`G01..G42`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h138-phase131-safety-vpled-strobe-vehiclerig-42gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`vp_strobe_vehiclerig_ibis_and_42gate_guard.py`](../../outputs/fx3-safety/fx3_safety/vp_strobe_vehiclerig_ibis_and_42gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `overall_ready_for_hardware_attach = False` (offline & dry-run), prior gate modules (`G01..G40`) untouched.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase131_donor_contracts`)
Inspects FX6 `v6.01` Multi-Interface & LANC strobe metadata (`libInfraMultiIF.so`, `libInfraLanc.so`), FX3 `v7.02` & FX6 `v6.01` multi-port USB VBUS control (`libUsbControl.so`), and external command transport dispatch (`libInfraExtCmdSvc.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx6_lib_infra_multi_if` | FX6 | `libInfraMultiIF.so` | `194,240` | `4f18de86260ccd1a...` | `InfraMultiIF_Init`, `InfraMultiIF_Exit`, `_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv`, `_ZN12InfraMultiIF19InfraMultiIFManager8finalizeEv` |
| `fx6_lib_infra_lanc` | FX6 | `libInfraLanc.so` | `51,848` | `99e02239a918fff0...` | `InfraDebugPrintfLanc`, `_ZN16InfraLancCommand17GetLANCStrobeInfoEP19InfraLancStrobeInfo`, `_ZN9InfraLanc16eventGetCallbackEPvS0_`, `_ZN9InfraLanc20eventLancApiCallbackEPvS0_` |
| `fx3_lib_usb_control` | FX3 | `libUsbControl.so` | `135,424` | `2bf51f28fd5066e5...` | `_ZN12UsbIfWrapper20isMultiPortSupportedEv`, `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`, `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT` |
| `fx6_lib_usb_control` | FX6 | `libUsbControl.so` | `135,424` | `951d1da8a4366dc8...` | `_ZN12UsbIfWrapper20isMultiPortSupportedEv`, `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`, `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT` |
| `fx3_lib_infra_ext_cmd_svc` | FX3 | `libInfraExtCmdSvc.so` | `26,960` | `6ed99a632f6646e3...` | `ExtCmdSvc_Create`, `_ZN9ExtCmdSvc22IntrRegistTransportCmdEP16__extcmd_svc_msgj`, `_ZN9ExtCmdSvc17SndMsgToUpperSyncEPvS0_j`, `_ZN9ExtCmdSvc17SndMsgToLowerSyncEPvS0_j` |
| `fx6_lib_infra_ext_cmd_svc` | FX6 | `libInfraExtCmdSvc.so` | `26,960` | `94e8916baa891c13...` | `ExtCmdSvc_Create`, `_ZN9ExtCmdSvc22IntrRegistTransportCmdEP16__extcmd_svc_msgj`, `_ZN9ExtCmdSvc17SndMsgToUpperSyncEPvS0_j`, `_ZN9ExtCmdSvc17SndMsgToLowerSyncEPvS0_j` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`79,015,712 B`: `ANTI_FLICKER_SET_HIGH_RES_SS_ON`, `STROBE_CONTROL_MODE`, `TIMECODE_EXT_NOTIFY`, `INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS`, `STEADY_SHOT_MODE`, `VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED`) and `cpapp-b.bin` (`15,980,568 B`: `GENLOCK_SetGenlockEnable`, `GENLOCK_CBID_VSYNC`, `GENLOCK_CBID_LOST`, `SET_S1_STEADY_SHOT_MODE`, `STEADY_SHOT_MODE`) strictly via `os.O_RDONLY` without embedding raw firmware bytes or keys.

### 1.2 Gate `G41`: Virtual Production High-Irradiance DMX Xenon/LED Strobe / Unfiltered UV-Arc `IMX510` Microlens Thermal Hazard & External `75-Ohm` Tri-Level Genlock -> `Multi-Terminal` Pin Mismatch Firewall (`verify_vp_strobe_uvarc_and_genlock_firewall`)
- **English**: Protects FX3's `IMX510` BSI CMOS microlens/color-filter array and `15-pin Multi-Terminal` when rigged in LED volumes or broadcast studio bays (where operators may accidentally feed `±300 mV` / `1 Vpp` `75-Ohm` BNC Tri-Level Genlock, PAL/NTSC Blackburst, or `5V` TTL Word-Clock into FX3's `LTC-only` Multi-Terminal adapter, or expose the unprotected sensor to close-range DMX strobes / arc welders), failing closed on:
  1. `BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD`: `peak_irradiance_w_cm2 > 0.35` or (`uv_arc_welding_or_pyro_scene == True` and `uv_ir_cut_and_protective_nd_installed == False`).
  2. `BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL`: `connected_to_fx3_multiterminal == True` and `bnc_sync_signal_type in {"TRILEVEL_GENLOCK", "BLACKBURST_PAL_NTSC", "WORDCLOCK_5V_TTL"}` (FX3 lacks FX6's hardware `Genlock` PLL BNC input; `5V` TTL Word-Clock overdrives the `LTC` pin).
  3. `BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK`: `led_volume_active == True` and `led_pwm_refresh_hz < 1920.0` and `ecs_fractional_shutter_locked == False`.
- **中文摘要**：在 LED 虚拟制作影棚与演播室环境下保护 FX3 的 `IMX510` 背照式 CMOS 微透镜/滤色片阵列及 `15-pin Multi-Terminal`（防止操作员误将 `75-Ohm` BNC `±300 mV` / `1 Vpp` 三电平 Genlock、黑场信号或 `5V` TTL 字时钟接入仅支持 `LTC` 的 Multi-Terminal 转接线，或无防护直面近距高能 DMX 频闪/电弧焊），在以下情形强制 fail-closed 阻断：
  1. 传感器表面峰值辐照度 `peak_irradiance_w_cm2 > 0.35` W/cm²，或处于电弧焊/烟火高能场景（`uv_arc_welding_or_pyro_scene == True`）却未加装 UV-IR Cut 与保护性 ND 滤镜（`uv_ir_cut_and_protective_nd_installed == False`）$\rightarrow$ `BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD`；
  2. 将 `TRILEVEL_GENLOCK`、`BLACKBURST_PAL_NTSC` 或 `WORDCLOCK_5V_TTL` 接入 FX3 `Multi-Terminal`（`connected_to_fx3_multiterminal == True`）$\rightarrow$ `BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL`；
  3. LED 背景墙启用（`led_volume_active == True`）且 PWM 刷新率 `< 1920.0` Hz 时未开启高分辨率分数快门同步（`ecs_fractional_shutter_locked == False`）$\rightarrow$ `BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK`。

### 1.3 Gate `G42`: Car-Rig / Motorcycle / Helicopter Hard-Mount High-Frequency Vibration (`20..200 Hz`) 5-Axis `IBIS` Voice-Coil Thermal Runaway & Secondary Stainless Safety-Tether Guard (`verify_vehiclerig_vibration_ibis_and_tether_guard`)
- **English**: Prevents 5-axis `IBIS` floating sensor carriage end-stop slamming (`±1.5 mm` mechanical stops) and voice-coil thermal runaway under continuous chase-car, motorcycle, or helicopter `20..200 Hz` engine/road vibration while enforcing exterior secondary retention:
  1. `BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR`: `vibration_rms_g > 1.8` (`20..200 Hz`) and `wire_rope_or_elastomer_isolator_stage == False`.
  2. `BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE`: `vibration_rms_g > 1.2` and `dominant_vibration_hz >= 35.0` and `ibis_steadyshot_mode != "OFF_MECHANICAL_PARK"` (enforces `SteadyShot OFF` mechanical park + post `Gyroflow` `RTMD` stabilization).
  3. `BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER`: `vehicle_or_aerial_exterior_mount == True` and (`secondary_steel_safety_cable_rated_kg < 25.0` or `suction_cup_count < 3`).
- **中文摘要**：在跟拍车、摩托车车架或直升机滑橇硬装工况下，防止 `20..200 Hz` 持续高频振动引发 FX3 五轴 `IBIS` 悬浮模组撞击 `±1.5 mm` 机械限位及音圈过热烧毁，并强制外挂二级防坠冗余：
  1. 振动 `vibration_rms_g > 1.8` g RMS 且未安装钢丝绳/弹性体减震隔离台（`wire_rope_or_elastomer_isolator_stage == False`）$\rightarrow$ `BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR`；
  2. 持续引擎共振频段（`vibration_rms_g > 1.2` g RMS 且 `dominant_vibration_hz >= 35.0` Hz）下未将防抖切换为机械锁止停泊（`ibis_steadyshot_mode != "OFF_MECHANICAL_PARK"`）$\rightarrow$ `BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE`；
  3. 车辆或航空器外挂架设（`vehicle_or_aerial_exterior_mount == True`）时，二级不锈钢安全绳额定载荷 `< 25.0` kg 或真空吸盘数量 `< 3` $\rightarrow$ `BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER`。

### 1.4 Unified 42-Gate Master Safety Preflight (`evaluate_42gate_preflight` / `verify-42-gates`)
- Composes `evaluate_40gate_preflight` (`G01..G40`) with `G41` and `G42`:
  - **Offline default mode / 离线默认模式**: `39/42` gates pass (`offline_39_gates_verified = True`, `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `42/42` simulation gates pass (`all_42_gates_verified = True`, `dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_vp_strobe_vehiclerig_ibis_and_42gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `42/42` passed (`OK`) | `1.580s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_vp_strobe_vehiclerig_ibis_and_42gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `42/42` passed (`OK`) | `1.574s` |
| `PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `707/707` passed (`OK`) | `9.343s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `707` run, `706` passed, `1` skipped (`OK`) | `8.391s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-42-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_39_OF_42_AWAITING_PHYSICAL_TIER0`, `verified=39/42`, `g41_to_g42_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-42-gates --clean-room --dry-run-simulated-backup --json` | CLI Clean-Room Dry-Run Simulated Backup | `status=VERIFIED_ALL_42_GATES_DRY_RUN_SIMULATED_BACKUP`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `offline_39_gates_verified=True`, `all_42_gates_verified=True`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `0.27s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/vp_strobe_vehiclerig_ibis_and_42gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_vp_strobe_vehiclerig_ibis_and_42gate_guard.py`
6. `reports/2026-11-14-phase131-safety-vpstrobe-vehiclerig-42gates/README.md`
