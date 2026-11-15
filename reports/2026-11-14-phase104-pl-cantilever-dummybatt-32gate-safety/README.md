# Phase 104 — Heavy Cinema PL-to-E Adapter / Matte-Box Cantilever Bending-Moment & 15mm LWS Lens-Support Guard (`Gate G31`), Unregulated 14.8V/26V V-Mount -> NP-FZ100 Dummy-Battery Over-Voltage (>8.4V Blowout Trap!) Firewall (`Gate G32`), and Unified 32-Gate Master Safety Preflight (`G01..G32`)

# 第 104 阶段 — 重型电影 PL 转 E 卡口转接环 / 遮光斗悬臂弯矩与 15mm LWS 镜头托架门禁（`Gate G31`）、非稳压 14.8V/26V V 口假电池超压击穿（>8.4V 主板杀手）防火墙（`Gate G32`）及 32 门禁主安全预检（`G01..G32`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h104-phase104-safety-plmount-dummybatt-32gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`pl_cantilever_dummybatt_and_32gate_guard.py`](../../outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, prior gate modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`, `intake_occlusion_tripod_and_26gate_guard.py`, `sensor_curtain_subzero_and_28gate_guard.py`, `wireless_tx_emi_endurance_and_30gate_guard.py`) unmodified.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase104_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` lens-mount communication (`libInfraLensCommunicator.so`) and USB-PD / battery-state power management (`libBusPower.so`, `libUsbBusPower.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_infra_lens_comm` | FX3 | `libInfraLensCommunicator.so` | `14,544` | `e61bf145f050dd03...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx6_lib_infra_lens_comm` | FX6 | `libInfraLensCommunicator.so` | `14,544` | `8848b33084f71856...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState`, `InitUSBSourcePowerStateToPowerManager` |
| `fx6_lib_bus_power` | FX6 | `libBusPower.so` | `43,968` | `d4f2ffe4e74786b6...` | `SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState` |
| `fx3_lib_usb_bus_power` | FX3 | `libUsbBusPower.so` | `48,232` | `c606880c92ecf602...` | `GetCurrentBattState`, `GetCurrentLimit`, `IsVbusReady`, `SetWatchSWForceOFF` |
| `fx6_lib_usb_bus_power` | FX6 | `libUsbBusPower.so` | `48,232` | `4215a9e989d25896...` | `GetCurrentBattState`, `GetCurrentLimit`, `IsVbusReady` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`asrid_cau_battery_authentication_error_normal_english_`, `asrid_cau_incompatible_battery_normal_english_`, `No11_BatteryLevelNonInfoLitium`, `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`, `PRM_FEATURE_MANAGER_lens_mount`) and `cpapp-b.bin` (`BATT_AUTH_Snd`, `BATT_STATE1_Snd`, `BattCheckInfo_Rcv`, `ACV_BATT_Snd`, `C_LENS_XDETECT_BODY_INT_NO`, `C_LENS_CS_BODY_INT_NO`, `ID_FLG_CAM_LENS_MOUNT`) strictly via `os.O_RDONLY`.

### 1.2 Gate `G31`: Heavy Cinema PL-to-E Mount Adapter, Clamp-On Matte-Box & Cantilever Bending-Moment Guard (`verify_pl_cantilever_and_emount_flange_guard`)
- **English**: FX6 features a reinforced locking Cinema E-Mount and cage-integrated top handle, whereas FX3's 6-screw E-Mount flange (`18.00 mm` flange focal distance, `+/-0.01 mm` back-focus tolerance) warps or shears internal magnesium boss threads under heavy PL cine zooms / anamorphics + clamp-on `4x5.65` matte boxes. Gate `G31` computes static ($M_{static} = m \cdot g \cdot L_{cg}$) and `2.5G` dynamic shock ($M_{peak} = M_{static} \cdot \text{shock}_g$) cantilever moments, failing closed on:
  - `BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP`: `lens_plus_mattebox_kg > 1.2` or `static_moment_nm > 1.8` without `lws_15mm_y_support_engaged == True`.
  - `BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT`: `pl_to_e_adapter_used == True` and `adapter_foot_bolted_to_cage == False` and `lens_plus_mattebox_kg > 0.9`.
  - `BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL`: `clamp_on_mattebox == True` and `lens_front_rotates_or_telescopes == True` (requiring a 15mm LWS swing-away rod-mounted matte box).
- **中文摘要**：FX6 配备加强锁紧电影 E 卡口，而 FX3 仅采用 6 颗螺钉固定 E 卡口法兰（法兰距 `18.00 mm`，后焦公差仅 `+/-0.01 mm`）。在挂装重型 PL 电影变焦/变形镜头及夹式 `4x5.65` 遮光斗时，若未安装 15mm LWS 导管 Y 型镜头托架或未将 PL 转接环底座锁固至兔笼，极易产生法兰翘曲或内螺纹滑丝。门禁 `G31` 精确计算静态弯矩 $M_{static} = m \cdot g \cdot L_{cg}$ 与 `2.5G` 冲击峰值弯矩 $M_{peak}$，在以下情形强制 fail-closed 阻断：
  1. `lens_plus_mattebox_kg > 1.2` 或 `static_moment_nm > 1.8` 且未锁紧 `lws_15mm_y_support_engaged == True` $\rightarrow$ `BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP`；
  2. `pl_to_e_adapter_used == True`、`adapter_foot_bolted_to_cage == False` 且 `lens_plus_mattebox_kg > 0.9` $\rightarrow$ `BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT`；
  3. 夹式遮光斗安装于前组旋转或伸缩镜筒（`clamp_on_mattebox == True` 且 `lens_front_rotates_or_telescopes == True`）$\rightarrow$ `BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL`（强制要求 15mm 导管摇臂式遮光斗）。

### 1.3 Gate `G32`: Unregulated 14.8V / 26V V-Mount -> `NP-FZ100` Dummy-Battery Over-Voltage Blowout Firewall (`verify_dummy_battery_overvoltage_firewall`)
- **English**: The #1 real-world FX3/A7SIII mainboard killer is plugging an unregulated or buck-converter-shorted D-Tap -> `NP-FZ100` dummy battery (`14.8V..16.8V` or `26V` cinema V-Mount) into FX3's `7.2V` nominal / `8.40V` max battery bay, instantly destroying the `CXD90057` PMIC power tree (Sony Cinema SOP prefers regulated `9V/3A` USB-C PD + genuine internal `NP-FZ100` UPS). Gate `G32` fails closed on:
  - `BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT`: `dummy_battery_installed == True` and (`measured_open_circuit_v > 8.45` or `buck_regulator_ovp_crowbar_verified == False` or `v_mount_nominal_v >= 24.0`).
  - `BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP`: `dtap_source_used == True` and `reverse_polarity_diode_or_smart_dtap == False`.
  - `BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF`: `dummy_battery_installed == True` and `infolithium_thermistor_ntc_valid == False`.
- **中文摘要**：现实中最常见的 FX3 主板烧毁故障源于将非稳压或降压芯片击穿的 D-Tap 转 `NP-FZ100` 假电池（`14.8V..16.8V` 或 `26V` 电影 V 口电池）直接插入标称 `7.2V` / 最高 `8.40V` 的机内电池仓，瞬间击穿 `CXD90057` PMIC 电源树（官方影院规范推荐稳压 `9V/3A` USB-C PD 配合原装内电池 UPS）。门禁 `G32` 对以下风险强制阻断：
  1. 安装假电池且空载实测 `> 8.45V`、未验证过压撬棒（OVP crowbar）保护或使用 `>= 24.0V` 高压 V 口电池 $\rightarrow$ `BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT`；
  2. 使用 D-Tap 供电但缺少防反接二极管或智能防反插 D-Tap $\rightarrow$ `BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP`；
  3. 假电池缺少有效的 Sony InfoLITHIUM 认证及 NTC 热敏电阻反馈 $\rightarrow$ `BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF`。

### 1.4 Unified 32-Gate Master Safety Preflight (`evaluate_32gate_preflight` / `verify-32-gates`)
- Composes `evaluate_30gate_preflight` (`G01..G30`) with `G31` and `G32`:
  - **Offline default mode / 离线默认模式**: `29/32` gates pass (`G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `32/32` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_pl_cantilever_dummybatt_and_32gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `37/37` passed (`OK`) | `0.616s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_pl_cantilever_dummybatt_and_32gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `37/37` passed (`OK`) | `0.585s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `505/505` passed (`OK`) | `2.645s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `505` run, `504` passed, `1` skipped (`OK`) | `2.592s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-32-gates --json` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_29_OF_32_AWAITING_PHYSICAL_TIER0`, `verified=29/32`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-32-gates --dry-run-simulated-backup --json` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_32_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=32/32`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `<0.1s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_pl_cantilever_dummybatt_and_32gate_guard.py`
6. `reports/2026-11-14-phase104-pl-cantilever-dummybatt-32gate-safety/README.md`
