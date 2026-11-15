# Phase 92 — Sigma Cooling Fan Intake/Exhaust Occlusion & Rain-Cover Backpressure Firewall (`Gate G25`), 1/4-20 Tripod Screw Depth / Cage Torque / Underwater Housing Vacuum Guard (`Gate G26`) & 26-Gate Master Safety Preflight (`G01..G26`)

# 第 92 阶段 — Sigma 离心风道进排气遮挡与防雨罩/消音罩热回流防火墙（门禁 `G25`）、1/4-20 脚架螺丝底孔限位 / 兔笼扭矩 / 潜水壳真空检漏门禁（门禁 `G26`）与 26 门禁主安全预检（`G01..G26`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h90-phase92-safety-intake-tripod-26gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`intake_occlusion_tripod_and_26gate_guard.py`](../../outputs/fx3-safety/fx3_safety/intake_occlusion_tripod_and_26gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, prior gate modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`) unmodified.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase92_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` `libfan.so` ELF symbols and `BK4\0` over-temperature threshold tables strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Thresholds |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_libfan` | FX3 | `libfan.so` | `27,280` | `c607fc8d3ea3b46e...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx6_libfan` | FX6 | `libfan.so` | `31,176` | `d4f01ff36a2d3d45...` | `fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list` |
| `fx3_bk4` | FX3 | `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd...` | `BK4\0` `0x02380007..0x02380009` (`40°C` / `55°C` / `82°C`) |
| `fx6_bk4` | FX6 | `CX95898_NTSC.bin` | `2,253,333` | `e2eafd4e950ead94...` | `BK4\0` `0x02380007..0x02380009` (`49°C` / `54°C` / `76°C`) |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`FAN_CONTROL_AUTO`, `FAN_CONTROL_MINIMUM`, `FAN_CONTROL_OFF_IN_REC`, `FAN_CONTROL_ALWAYS_OFF`, `AUTO1`, `AUTO2`, `OFF_BY_IM_THERMAL`, `OFF_BY_MEDIA_THERMAL`) and `cpapp-b.bin` (`FAN_EQ_ID`, `THERMISTOR_ADJ_START`) strictly via `os.O_RDONLY`.

### 1.2 Gate `G25`: Sigma Centrifugal Fan Intake/Exhaust Occlusion & Rain-Cover / Blimp Recirculation Firewall (`verify_sigma_fan_intake_exhaust_firewall`)
- **English**: Protects FX3's internal Sigma-shaped graphite-isolated centrifugal air duct against mechanical airflow occlusion, impeller jam, `Off_in_Rec` high-load thermal runaway, and closed-loop hot air recirculation inside sealed rain covers or sound blimps:
  - `BLOCKED_FAN_TACHOMETER_ROTOR_STALL`: `pwm_duty_pct >= 25%` and `measured_rpm < min_expected_rpm` (default `1800 RPM`).
  - `BLOCKED_DUCT_OCCLUSION_BACKPRESSURE`: `intake_clearance_mm < 5.0` or `exhaust_clearance_mm < 5.0` (flush V-mount battery plate / cheeseplate blocking side vents).
  - `BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD`: `fan_mode == 'Off_in_Rec'` with `workload in ('4K_120p', '4K_60p_RAW_HDMI', 'XAVC_S_I_4K60_DUALSLOT')` and `clip_duration_min > 8.0`.
  - `BLOCKED_SEALED_BLIMP_RECIRCULATION`: `enclosure_sealed_blimp_or_raincover == True` and `internal_enclosure_temp_c > 42.0`.
- **中文摘要**：针对 FX3 机身内部 Σ 型石墨隔热离心风道（单侧进风、对侧排风）建立四项故障闭锁检查：PWM 占空比 `>= 25%` 且霍尔测速 `measured_rpm < min_expected_rpm` 时拦截叶轮卡滞（`BLOCKED_FAN_TACHOMETER_ROTOR_STALL`）；进风或出风间隙 `< 5.0 mm` 时拦截背压堵风（`BLOCKED_DUCT_OCCLUSION_BACKPRESSURE`）；在 `4K_120p` / `4K_60p_RAW_HDMI` / `XAVC_S_I_4K60_DUALSLOT` 高负载下开启 `Off_in_Rec` 且录制超过 `8.0 min` 时拦截热失控（`BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD`）；密封防雨罩/消音罩内部温度 `> 42.0°C` 时拦截热风回流（`BLOCKED_SEALED_BLIMP_RECIRCULATION`）。

### 1.3 Gate `G26`: 1/4-20 Tripod Screw Depth Bottom-Out, Cage Torque & Underwater Housing Vacuum Leak Guard (`verify_tripod_screw_torque_and_housing_vacuum_guard`)
- **English**: Enforces ISO 1222 mechanical mounting limits on FX3's magnesium bottom chassis and underwater cinema housing leak protection:
  - `BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE`: `effective_screw_protrusion_mm > 5.5` (prevents warping the bottom magnesium pocket into internal PCB/IBIS flex assembly).
  - `BLOCKED_MOUNTING_OVER_TORQUE_HAZARD`: `applied_torque_nm > 3.5` or `single_screw_no_anti_twist_pin_heavy_lens == True`.
  - `BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE`: `underwater_housing_mode == True` and (`vacuum_pressure_drop_mbar_per_10min > 1.5` or `moisture_sensor_triggered == True` or `vacuum_check_elapsed_min < 10.0`), asserting `immediate_power_off_abort_required = True`.
- **中文摘要**：严格限制索尼 ILME-FX3 底部镁合金 `1/4"-20 UNC` 螺孔深度上限 `<= 5.5 mm`（超过即触发 `BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE`，防止顶穿底壳损伤内部 PCB 与 IBIS 排线）；紧固力矩 `> 3.5 N·m` 或重镜头单螺丝未装防偏转定位销触发 `BLOCKED_MOUNTING_OVER_TORQUE_HAZARD`；水下摄影壳体（Nauticam / Seafrogs 等）启用时，若 10 分钟真空压降 `> 1.5 mbar`、湿度试纸报警或保压时间 `< 10.0 min`，立即触发 `BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE` 并要求紧急断电停机。

### 1.4 Unified 26-Gate Master Safety Preflight (`evaluate_26gate_preflight` / `verify-26-gates`)
- Composes `evaluate_24gate_preflight` (`G01..G24`) with `G25` and `G26`:
  - **Offline default mode / 离线默认模式**: `23/26` gates pass (`G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `26/26` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_intake_occlusion_tripod_and_26gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `34/34` passed (`OK`) | `0.382s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_intake_occlusion_tripod_and_26gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `34/34` passed (`OK`) | `0.373s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `394/394` passed (`OK`) | `1.329s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `394` run, `393` passed, `1` skipped (`OK`) | `1.287s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `0.03s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-26-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_23_OF_26_AWAITING_PHYSICAL_TIER0`, `verified=23/26`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-26-gates --dry-run-simulated-backup` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_26_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=26/26`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/intake_occlusion_tripod_and_26gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_intake_occlusion_tripod_and_26gate_guard.py`
6. `reports/2026-11-14-phase92-intake-occlusion-tripod-26gate-safety/README.md`
