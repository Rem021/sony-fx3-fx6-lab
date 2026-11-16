# Phase 108 — Coastal Salt-Spray / Studio Glycol-Haze Fan Ingestion Firewall (`Gate G33`), Wireless Follow-Focus Hard-Stop Lens-Barrel Torque & Gimbal Dynamic CoG Shift Guard (`Gate G34`), and Unified 34-Gate Master Safety Preflight (`G01..G34`)

# 第 108 阶段 — 沿海盐雾 / 碱尘与影棚油雾乙二醇烟雾风扇吸入防火墙（`Gate G33`）、无线跟焦硬限位镜头扭矩与稳定器动态重心偏移门禁（`Gate G34`）及 34 门禁主安全预检（`G01..G34`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h109-phase108-safety-saltspray-followfocus-34gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`saltspray_haze_followfocus_and_34gate_guard.py`](../../outputs/fx3-safety/fx3_safety/saltspray_haze_followfocus_and_34gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, prior gate modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`, `intake_occlusion_tripod_and_26gate_guard.py`, `sensor_curtain_subzero_and_28gate_guard.py`, `wireless_tx_emi_endurance_and_30gate_guard.py`, `pl_cantilever_dummybatt_and_32gate_guard.py`) unmodified.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase108_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` Sigma centrifugal cooling (`libfan.so`), E-Mount lens communication (`libInfraLensCommunicator.so`), and external command transport (`libInfraExtCmdSvc.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_fan` | FX3 | `libfan.so` | `27,280` | `c607fc8d3ea3b46e...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx6_lib_fan` | FX6 | `libfan.so` | `31,176` | `d4f01ff36a2d3d45...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx3_lib_infra_lens_comm` | FX3 | `libInfraLensCommunicator.so` | `14,544` | `e61bf145f050dd03...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx6_lib_infra_lens_comm` | FX6 | `libInfraLensCommunicator.so` | `14,544` | `8848b33084f71856...` | `GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup` |
| `fx3_lib_infra_ext_cmd_svc` | FX3 | `libInfraExtCmdSvc.so` | `26,960` | `6ed99a632f6646e3...` | `ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync` |
| `fx6_lib_infra_ext_cmd_svc` | FX6 | `libInfraExtCmdSvc.so` | `26,960` | `94e8916baa891c13...` | `ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`FAN_CONTROL_AUTO`, `FAN_CONTROL_MINIMUM`, `OFF_BY_IM_THERMAL`, `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`, `PRM_FEATURE_MANAGER_lens_mount`, `FOCUS_MODE`, `STEADY_SHOT`, `ZOOM`) and `cpapp-b.bin` (`FAN_EQ_ID`, `SET_S1_STEADY_SHOT_MODE`, `C_LENS_XDETECT_BODY_INT_NO`, `THERMISTOR_ADJ_START`) strictly via `os.O_RDONLY`.

### 1.2 Gate `G33`: Coastal Salt-Spray / Fine Desert Silica Dust & Studio Mineral-Oil / Glycol Haze Sigma Blower Ingestion Firewall (`verify_saltspray_alkali_dust_and_haze_firewall`)
- **English**: FX3's internal Sigma centrifugal cooling duct isolates the mainboard via a graphite-heatsink partition, yet active air suction pulls salt-laden surf mist, fine Sahara/playa alkali dust (<10 um), or heavy soundstage mineral-oil/glycol haze directly onto the fan impeller bearing and heatsink fins, caking sticky conductive residue or seizing the Hall-sensor bearing. Gate `G33` computes cumulative haze exposure dose ($\text{mg}\cdot\text{min}/\text{m}^3$) and estimated ingested aerosol mass ($\mu\text{g}$), failing closed on:
  - `BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT`: `coastal_salt_spray_env == True` and `hydrophobic_vent_membrane_or_housing == False`.
  - `BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD`: `pm10_dust_ug_m3 > 600.0` and `intake_hepa_mesh_installed == False`.
  - `BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING`: `studio_haze_density_mg_m3 > 25.0` and `continuous_fan_exposure_min > 45.0` and `post_wrap_isopropyl_duct_purge_scheduled == False`.
- **中文摘要**：FX3 机身内部 Sigma 离心散热风道虽通过石墨散热隔板与主板隔离，但主动进气吸力会将海浪盐雾、沙漠/盐碱滩细颗粒硅尘（`<10 um`）或影棚高浓度矿物油/乙二醇烟雾直接吸入叶轮轴承与散热鳍片表面，造成导电粘垢板结或霍尔传感器轴承卡死。门禁 `G33` 量化累计烟雾暴露剂量（$\text{mg}\cdot\text{min}/\text{m}^3$）与风道吸入气溶胶质量（$\mu\text{g}$），在以下情形强制 fail-closed 阻断：
  1. `coastal_salt_spray_env == True` 且未启用疏水透气膜/防水防雾壳（`hydrophobic_vent_membrane_or_housing == False`）$\rightarrow$ `BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT`；
  2. `pm10_dust_ug_m3 > 600.0` 且进气口未加装 HEPA 防尘滤网（`intake_hepa_mesh_installed == False`）$\rightarrow$ `BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD`；
  3. 影棚烟雾浓度 `studio_haze_density_mg_m3 > 25.0` 且连续风扇暴露 `continuous_fan_exposure_min > 45.0` 分钟但未安排收工后异丙醇风道清洗（`post_wrap_isopropyl_duct_purge_scheduled == False`）$\rightarrow$ `BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING`。

### 1.3 Gate `G34`: High-Torque Wireless Follow-Focus (`Nucleus-M / Preston / Tilta` `> 2.5 N*m`) Uncalibrated Hard-Stop Gear Stripping & Telescoping-Zoom Gimbal Motor Oscillation Guard (`verify_followfocus_hardstop_and_gimbal_cog_guard`)
- **English**: Cinema wireless follow-focus motors (`2.5 N*m .. 5.0 N*m`) mounted on a single 15mm rod without automatic/manual A-B hard-stop calibration slam Sony fly-by-wire E-Mount plastic helicoids or vintage cine brass stops, stripping focus gears or flexing the single rod (`delta = F * L^3 / (3 * EI)`) and misaligning `0.8 MOD` gear mesh. Furthermore, external-zooming lenses (`24-70 / 200-600`) shift CoG `> 15 mm` during zoom on compact 3-axis gimbals (`RS3/RS4`), inducing violent `40..90 Hz` roll/pitch PID oscillation that saturates FX3's IBIS voice coils. Gate `G34` fails closed on:
  - `BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE`: `wireless_fiz_motor_torque_nm > 1.2` and `hard_stops_calibrated == False` and `fly_by_wire_infinite_ring == False`.
  - `BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP`: `wireless_fiz_motor_torque_nm > 1.8` and `dual_rod_or_cage_bridge_clamp == False`.
  - `BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION`: `gimbal_mounted == True` and `zoom_cog_shift_mm > 15.0` and `gimbal_autotune_after_zoom == False`.
- **中文摘要**：无线电影跟焦马达（`Nucleus-M / Preston / Tilta`，扭矩可达 `2.5..5.0 N*m`）若在单根 15mm 导管上未完成 A-B 硬限位自动/手动标定即驱动带机械止点的镜头，将直接打滑或打断索尼 E 卡口塑料对焦螺杆及复古电影镜头黄铜齿圈，或令单根导管产生 Euler-Bernoulli 悬臂挠度变形导致 `0.8 MOD` 齿轮脱齿；此外，外变焦镜头（`24-70 / 200-600`）在紧凑型三轴稳定器（`RS3/RS4`）上变焦引发超过 `15 mm` 的重心前移，会激发 `40..90 Hz` 剧烈俯仰/横滚 PID 自激振荡并击穿 FX3 机身五轴防抖音圈电机。门禁 `G34` 对以下风险强制阻断：
  1. `wireless_fiz_motor_torque_nm > 1.2` 且未校准硬限位（`hard_stops_calibrated == False`）且非电控无限旋转环（`fly_by_wire_infinite_ring == False`）$\rightarrow$ `BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE`；
  2. `wireless_fiz_motor_torque_nm > 1.8` 且未配备双导管或兔笼桥接夹具（`dual_rod_or_cage_bridge_clamp == False`）$\rightarrow$ `BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP`；
  3. 稳定器搭载（`gimbal_mounted == True`）、变焦重心偏移 `zoom_cog_shift_mm > 15.0` 且变焦后未执行稳定器自整定（`gimbal_autotune_after_zoom == False`）$\rightarrow$ `BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION`。

### 1.4 Unified 34-Gate Master Safety Preflight (`evaluate_34gate_preflight` / `verify-34-gates`)
- Composes `evaluate_32gate_preflight` (`G01..G32`) with `G33` and `G34`:
  - **Offline default mode / 离线默认模式**: `31/34` gates pass (`G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `34/34` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_saltspray_haze_followfocus_and_34gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `36/36` passed (`OK`) | `0.804s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_saltspray_haze_followfocus_and_34gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `36/36` passed (`OK`) | `0.774s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `541/541` passed (`OK`) | `3.837s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `541` run, `540` passed, `1` skipped (`OK`) | `3.693s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-34-gates --json` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_31_OF_34_AWAITING_PHYSICAL_TIER0`, `verified=31/34`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-34-gates --dry-run-simulated-backup --json` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_34_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=34/34`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `<0.1s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/saltspray_haze_followfocus_and_34gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_saltspray_haze_followfocus_and_34gate_guard.py`
6. `reports/2026-11-14-phase108-saltspray-followfocus-34gate-safety/README.md`
