# Phase 97 — IMX510 Sensor Laser/Solar Burnout, Anti-Dust Curtain-at-Power-Off & IBIS Transport Lock Guard (`Gate G27`), Sub-Zero NP-FZ100 ESR Sag & High-Altitude Convective Cooling Derating Firewall (`Gate G28`) & 28-Gate Master Safety Preflight (`G01..G28`)

# 第 97 阶段 — IMX510 传感器激光/直射太阳烧伤、关机防尘帘脆弱叶片与未上电 IBIS 运输锁保护（门禁 `G27`）、零下 `-20°C` NP-FZ100 锂电 ESR 压降欠压与高海拔 `>3,000m` 空气密度散热降额防火墙（门禁 `G28`）及 28 门禁主安全预检（`G01..G28`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h96-phase97-safety-sensor-subzero-altitude-28gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`sensor_curtain_subzero_and_28gate_guard.py`](../../outputs/fx3-safety/fx3_safety/sensor_curtain_subzero_and_28gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, prior gate modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`, `intake_occlusion_tripod_and_26gate_guard.py`) unmodified.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase97_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` `libfan.so`, `libBusPower.so`, `libUsbBusPower.so`, and `BK4\0` over-temperature threshold tables strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Thresholds |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_libfan` | FX3 | `libfan.so` | `27,280` | `c607fc8d3ea3b46e...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx6_libfan` | FX6 | `libfan.so` | `31,176` | `d4f01ff36a2d3d45...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState` |
| `fx3_lib_usb_bus_power` | FX3 | `libUsbBusPower.so` | `48,232` | `c606880c92ecf602...` | `GetCurrentBattState`, `GetCurrentLimit` |
| `fx3_bk4` | FX3 | `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd...` | `BK4\0` `0x02380007..0x02380009` (`40°C` / `55°C` / `82°C`) |
| `fx6_bk4` | FX6 | `CX95898_NTSC.bin` | `2,253,333` | `e2eafd4e950ead94...` | `BK4\0` `0x02380007..0x02380009` (`49°C` / `54°C` / `76°C`) |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER`, `VAL_system_mode_option_SYSTEM_MODE_OPTION_CLEANING`, `OFF_BY_BATT_END`, `ND_FILTER_MANUAL_SET_0_3`) and `cpapp-b.bin` (`SET_S1_STEADY_SHOT_MODE`, `BATT_AUTH_S`, `FAN_EQ_ID`, `THERMISTOR_ADJ_START`) strictly via `os.O_RDONLY`.

### 1.2 Gate `G27`: IMX510 Sensor Laser/Solar Burnout, Anti-Dust Curtain-at-Power-Off & IBIS Transport Lock Guard (`verify_sensor_curtain_and_ibis_transport_guard`)
- **English**: Because FX3 lacks FX6's internal electronic variable ND glass protecting the sensor cavity, the `IMX510` sensor sits directly behind the E-mount throat (or behind delicate `0.04 mm` focal-plane shutter blades when `'Shutter When Power Off = On'`):
  - `BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD`: `concert_show_laser_or_automotive_lidar_env == True` without a laser-rated optical filter OR `uncapped_fast_lens_pointed_at_direct_sun == True` (prevents permanent `IMX510` microlens/CFA stripe burnout).
  - `BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE`: `shutter_when_power_off == True` and (`manual_swab_or_rocket_blower_active == True` or `outdoor_direct_sun_lens_off == True`) — prevents focused sunlight from warping/melting closed black blades and blower tips/swabs from puncturing `0.04 mm` curtains.
  - `BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION`: `vehicle_hard_mount_vibration_grms > 1.8` and `power_off_ibis_parking_verified == False` — protects unenergized floating IBIS voice-coil stages from slamming against mechanical stops.
- **中文摘要**：由于 FX3 不具备 FX6 机身内部用于防护传感器腔体的电子无级 ND 玻璃，`IMX510` CMOS 直接暴露在 E 卡口喉部后方（或在开启 `关机防尘帘 = 开` 时暴露 `0.04 mm` 极薄焦平面快门帘幕）：当存在演唱会激光/车载 LiDAR 且未加装激光防护滤镜、或无盖大光圈镜头直对烈日时触发 `BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD`；当关机防尘帘闭合且进行手动拭子/气吹清洁或户外烈日下拆镜头换镜时触发 `BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE`；当车载硬安装振动 `> 1.8 Grms` 且未校验断电 IBIS 锁止归位时触发 `BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION`。

### 1.3 Gate `G28`: Sub-Zero (`-20°C..0°C`) NP-FZ100 Li-Ion ESR Voltage-Sag Brownout & High-Altitude (`>3,000m`) Air-Density Convective Cooling Derating Firewall (`verify_subzero_esr_and_altitude_firewall`)
- **English**: Models Arrhenius sub-zero Li-Ion DC internal resistance $R_{int}(T) = R_{25}\exp\!\left(\frac{E_a}{R}\left(\frac{1}{T_K}-\frac{1}{298.15}\right)\right)$ (`3.1x–6.2x` ESR rise across `-5°C..-20°C`), constant-power terminal voltage $V_{term} = V_{oc} - I \cdot R_{int}(T)$, and ISA standard atmosphere (`0..6,000 m`) air-density $\rho(h)$ convective fan mass-flow derating above `3,000 m` ($P_{atm} < 70\text{ kPa}$):
  - `BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK`: `battery_cell_temp_c < 0.0` and predicted `v_term_min_v < 6.25` (`6.0 V` PMIC UVLO + margin, e.g., `-20°C` at `45%` SoC under `8.5 W` peak load $\rightarrow 5.66\text{ V}$) without insulated USB-PD / heated V-Mount backup.
  - `BLOCKED_LIION_SUBZERO_CHARGING_PLATING`: `usb_pd_charging_enabled == True` and `battery_cell_temp_c <= 0.0` (prevents irreversible metallic lithium dendrite plating).
  - `BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING`: `altitude_m > 3000.0` and `fan_mass_flow_ratio * cooling_headroom_watts < workload_thermal_watts`.
- **中文摘要**：基于 Arrhenius 方程精确建模 NP-FZ100 在零下低温时内阻 `3x–6x` 激增导致的峰值负载压降 $V_{term} = V_{oc} - I \cdot R_{int}(T)$：当电芯温度 `< 0°C` 且无保温 USB-PD/加热 V 口供电时，若预测最低端电压 `< 6.25 V`（逼近 `6.0 V` PMIC 欠压锁定阈值）即阻断 `BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK`；在 `<= 0°C` 开启 USB-PD 充电即阻断 `BLOCKED_LIION_SUBZERO_CHARGING_PLATING` 以防止锂枝晶析锂；结合 ISA 标准大气压与空气密度 $\rho(h)$ 曲线，在海拔 `> 3,000 m`（气压 `< 70 kPa`、空气密度下降 `>25%..43%`）且降额风扇散热量低于录制热功耗负载时阻断 `BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING`。

### 1.4 Unified 28-Gate Master Safety Preflight (`evaluate_28gate_preflight` / `verify-28-gates`)
- Composes `evaluate_26gate_preflight` (`G01..G26`) with `G27` and `G28`:
  - **Offline default mode / 离线默认模式**: `25/28` gates pass (`G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `28/28` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_sensor_curtain_subzero_and_28gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `36/36` passed (`OK`) | `0.445s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_sensor_curtain_subzero_and_28gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `36/36` passed (`OK`) | `0.422s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `430/430` passed (`OK`) | `1.774s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `430` run, `429` passed, `1` skipped (`OK`) | `1.702s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-28-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_25_OF_28_AWAITING_PHYSICAL_TIER0`, `verified=25/28`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-28-gates --dry-run-simulated-backup` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_28_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=28/28`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `<0.1s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/sensor_curtain_subzero_and_28gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_sensor_curtain_subzero_and_28gate_guard.py`
6. `reports/2026-11-14-phase97-sensor-curtain-subzero-28gate-safety/README.md`
