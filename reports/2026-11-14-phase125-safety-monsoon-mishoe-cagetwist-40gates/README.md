# Milestone Phase 125 — Tropical Monsoon Rain / Wet MI-Shoe 24-Pin Contact Short-Circuit Firewall (`Gate G39`), FX3 Top-Plate `1/4"-20` Thread Shear / `XLR-H1` Whip-Leverage & Asymmetric Cage-Twist E-Mount `18.00 mm` Flange-Focal-Distance Guard (`Gate G40`), and Unified 40-Gate Master Safety Preflight (`G01..G40`)

# 里程碑第 125 阶段 — 热带季风暴雨 / 湿润 MI 热靴 24-Pin 触点短路防火墙（`Gate G39`）、FX3 顶板 `1/4"-20` 螺纹滑丝 / `XLR-H1` 甩动杠杆剪切与非对称兔笼扭转 E 卡口 `18.00 mm` 法兰距形变防护（`Gate G40`）及 40 门禁主安全预检（`G01..G40`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h131-phase125-safety-rain-cage-40gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`monsoon_mishoe_cagetwist_and_40gate_guard.py`](../../outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `overall_ready_for_hardware_attach = False` (offline & dry-run), prior gate modules (`G01..G38`) untouched.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase125_donor_contracts`)
Inspects FX6 `v6.01` MI-Shoe power sequencing (`libInfraHotshoe.so`), FX3 `v7.02` & FX6 `v6.01` E-Mount lens communication (`libInfraLensCommunicator.so`), external command dispatch (`libInfraExtCmdSvc.so`), and bus power monitoring (`libBusPower.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx6_lib_infra_hotshoe` | FX6 | `libInfraHotshoe.so` | `47,808` | `0bf55367c0345341...` | `_ZN12InfraHotshoe13QueryShoeIdOnEij`, `_ZN12InfraHotshoe17SetShoeLogicPwrOnEb`, `_ZN12InfraHotshoe27SetShoeUnregOnWaitStabilityEbjj`, `INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON` |
| `fx3_lib_infra_lens_comm` | FX3 | `libInfraLensCommunicator.so` | `14,544` | `e61bf145f050dd03...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx6_lib_infra_lens_comm` | FX6 | `libInfraLensCommunicator.so` | `14,544` | `8848b33084f71856...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx3_lib_infra_ext_cmd_svc` | FX3 | `libInfraExtCmdSvc.so` | `26,960` | `6ed99a632f6646e3...` | `ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`, `SndMsgToLowerSync` |
| `fx6_lib_infra_ext_cmd_svc` | FX6 | `libInfraExtCmdSvc.so` | `26,960` | `94e8916baa891c13...` | `ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`, `SndMsgToLowerSync` |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT` |
| `fx6_lib_bus_power` | FX6 | `libBusPower.so` | `43,968` | `d4f2ffe4e74786b6...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`79,015,712 B`: `VAL_hotshoe_xlr_mic_connection_status_XLR_MIC_CONNECT_ON`, `PID_SET_HOTSHOE_VIDEOLIGHT`, `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`, `VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED`, `OFF_BY_BATT_OVERCURRENT`) and `cpapp-b.bin` (`15,980,568 B`: `8AccyFifoI17ACCY_MI_SHOE_TYPEE`, `7AdfFifoIN21AdfShoePowerSequencer38SHOE_POWER_SEQUENCER_RESERVE_CALL_BACKEE`, `MSGQ_GID_HOTSHOE_INFRA1`, `ID_FLG_CAM_LENS_MOUNT`, `SET_S1_STEADY_SHOT_MODE`) strictly via `os.O_RDONLY` without embedding raw bytes or keys.

### 1.2 Gate `G39`: Tropical Monsoon Rain Ingress, Uncapped Wet 24-Pin MI-Shoe Gold-Finger Galvanic Short-Circuit & Open Port-Flap Capillary Guard (`verify_monsoon_rain_mishoe_firewall`)
- **English**: Protects FX3's unsealed top-plate recessed 24-pin Multi-Interface (MI) Shoe (`+3.15V/+5V` accessory power, `I2S` audio clocks, and detect pins facing upward) and side I/O rubber port bays against tropical rain ingress and galvanic pin corrosion/shorting, failing closed on:
  1. `BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT`: (`precipitation_mm_hr > 0.5` and `mi_shoe_accessory_attached == False` and `mi_shoe_weather_cap_installed == False`), or (`mi_shoe_contact_resistance_kohm < 50.0` while `mi_shoe_power_rail_enabled == True`).
  2. `BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN`: `precipitation_mm_hr > 2.0` and `mi_shoe_accessory_attached == True` and `mi_shoe_silicone_perimeter_gasket_sealed == False` and `rain_cover_installed == False`.
  3. `BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS`: (`precipitation_mm_hr > 0.5` or `water_spray_rig == True`) and `open_rubber_port_flaps_count > 0` and `weather_sealed_cable_gland_or_rain_slicker == False`.
- **中文摘要**：保护 FX3 非全密封顶板凹槽式 24-Pin 多功能热靴（向上暴露 `+3.15V/+5V` 供电、`I2S` 音频时钟与检测引脚）及机身侧面橡胶接口盖在热带暴雨与泼水环境下的电化学短路与毛细渗水风险，在以下情形强制 fail-closed 阻断：
  1. `precipitation_mm_hr > 0.5` mm/h 且未连接热靴附件也未安装原厂热靴防尘防潮盖（`mi_shoe_weather_cap_installed == False`），或热靴电源轨使能状态下（`mi_shoe_power_rail_enabled == True`）针脚间湿桥等效阻抗 `< 50.0` k$\Omega$ $\rightarrow$ `BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT`；
  2. `precipitation_mm_hr > 2.0` mm/h 下已安装热靴附件，但既无硅胶周边密封圈（`mi_shoe_silicone_perimeter_gasket_sealed == False`）也未套防雨罩（`rain_cover_installed == False`）$\rightarrow$ `BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN`；
  3. 在降雨（`precipitation_mm_hr > 0.5`）或喷淋水雾造景（`water_spray_rig == True`）工况下，仍有侧面橡胶端口盖敞开（`open_rubber_port_flaps_count > 0`）且未启用密封走线压盖/全包雨衣（`weather_sealed_cable_gland_or_rain_slicker == False`）$\rightarrow$ `BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS`。

### 1.3 Gate `G40`: FX3 Top-Plate `2x M4` `XLR-H1` Handle Whip-Leverage Shear, `1/4"-20` Magnesium-Chassis Thread Strip (`> 3.5 N*m`) & Asymmetric Cage-Twist E-Mount `18.00 mm` Flange-Focal-Distance (`FFD`) Warpage Guard (`verify_xlr_h1_quarter20_and_cage_twist_guard`)
- **English**: Protects FX3's internal magnesium-alloy chassis (`5x 1/4"-20` mounting threads + `2x M4` MI-Shoe handle screws) and `18.00 mm` (`±0.015 mm`) E-Mount optical flange plane, failing closed on:
  1. `BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR`: `xlr_h1_handle_installed == True` and (`total_rig_mass_suspended_from_xlr_h1_kg > 2.8` or `top_handle_monitor_moment_nm > 3.2`) and `metal_cage_nato_top_handle_reinforcement == False`.
  2. `BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP`: `body_thread_fastener_torque_nm > 3.5` (exceeding magnesium `1/4"-20` thread boss yield limit).
  3. `BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE`: `cage_multi_point_locked == True` and `unshimmed_side_screw_gap_mm > 0.25` causing `estimated_emount_ffd_tilt_um > 12.0` (decentering fast `T1.4` cinema primes).
- **中文摘要**：保护 FX3 镁合金内骨架（机顶/底 `5x 1/4"-20` 螺孔及 `XLR-H1` 手柄 `2x M4` 锁孔）与 `18.00 mm`（`±0.015 mm`）E 卡口法兰平面光学精度，在以下情形强制 fail-closed 阻断：
  1. 已安装 `XLR-H1` 音频提手且提手悬吊总重 `> 2.8` kg 或提手前端监视器甩动力矩 `> 3.2` N$\cdot$m，同时未使用金属兔笼 NATO 顶提手加固分散载荷（`metal_cage_nato_top_handle_reinforcement == False`）$\rightarrow$ `BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR`；
  2. 机身 `1/4"-20` 安装螺丝拧紧力矩 `> 3.5` N$\cdot$m（超出镁合金螺孔屈服阈值）$\rightarrow$ `BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP`；
  3. 多点锁紧兔笼（`cage_multi_point_locked == True`）时侧面未加垫片间隙 `> 0.25` mm，导致推算 E 卡口法兰距倾斜形变 `> 12.0` $\mu$m（足以使 `T1.4` 电影定焦出现明显偏心像场倾斜）$\rightarrow$ `BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE`。

### 1.4 Unified 40-Gate Master Safety Preflight (`evaluate_40gate_preflight` / `verify-40-gates`)
- Composes `evaluate_38gate_preflight` (`G01..G38`) with `G39` and `G40`:
  - **Offline default mode / 离线默认模式**: `37/40` gates pass (`offline_37_gates_verified = True`, `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `40/40` simulation gates pass (`all_40_gates_verified = True`, `dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_monsoon_mishoe_cagetwist_and_40gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `42/42` passed (`OK`) | `1.447s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_monsoon_mishoe_cagetwist_and_40gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `42/42` passed (`OK`) | `1.430s` |
| `PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `665/665` passed (`OK`) | `7.790s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `665` run, `664` passed, `1` skipped (`OK`) | `7.546s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-40-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_37_OF_40_AWAITING_PHYSICAL_TIER0`, `verified=37/40`, `g39_to_g40_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-40-gates --clean-room --dry-run-simulated-backup --json` | CLI Clean-Room Dry-Run Simulated Backup | `status=VERIFIED_ALL_40_GATES_DRY_RUN_SIMULATED_BACKUP`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `offline_37_gates_verified=True`, `all_40_gates_verified=True`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `0.95s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_monsoon_mishoe_cagetwist_and_40gate_guard.py`
6. `reports/2026-11-14-phase125-safety-monsoon-mishoe-cagetwist-40gates/README.md`
