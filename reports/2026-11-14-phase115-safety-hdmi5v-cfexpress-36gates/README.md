# Phase 115 — Active Optical HDMI (AOC) Pin-18 +5V Over-Current / Reverse Backfeed & Unclamped Type-A Port Shear Firewall (`Gate G35`), CFexpress Type-A / UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal-Throttle & Door-Open Flush Guard (`Gate G36`), and Unified 36-Gate Master Safety Preflight (`G01..G36`)

# 第 115 阶段 — 主动光学 HDMI (AOC) Pin-18 +5V 过流 / 反向倒灌与未锁紧 Type-A 接口剪力防火墙（`Gate G35`）、CFexpress Type-A / UHS-II 双卡槽 VPG 持续写入、NVMe 热降频与开盖落盘保护（`Gate G36`）及 36 门禁主安全预检（`G01..G36`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h118-phase115-safety-hdmi5v-cfexpress-36gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`hdmi_aoc_5v_cfexpress_and_36gate_guard.py`](../../outputs/fx3-safety/fx3_safety/hdmi_aoc_5v_cfexpress_and_36gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `overall_ready_for_hardware_attach = False` (offline & dry-run), prior gate modules (`G01..G34`) untouched.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase115_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` HDMI display/media temperature control (`libInfraAdjMedia.so`), dual-slot media configuration (`libInfraMediaConfig.so`), media temperature event detection (`libInfraMediaDetect.so`), and CFexpress/NVMe/VPG common storage driver (`libInfraMediaCommon.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_infra_adj_media` | FX3 | `libInfraAdjMedia.so` | `318,152` | `caae47cd50a72816...` | `AVBB_SCN_START_HDMI`, `AVBB_SCN_STOP_HDMI`, `DisableMediaTemperatureInfoNotification`, `GetTemp` |
| `fx6_lib_infra_adj_media` | FX6 | `libInfraAdjMedia.so` | `334,536` | `2dba0c9931017db4...` | `AVBB_SCN_START_HDMI`, `AVBB_SCN_STOP_HDMI`, `DisableMediaTemperatureInfoNotification`, `GetTemp` |
| `fx3_lib_infra_media_config` | FX3 | `libInfraMediaConfig.so` | `52,312` | `483548d53dfbe941...` | `ADJ_SLOT_1`, `ADJ_SLOT_2`, `CTRL_TEMP`, `SLOT_SSD` |
| `fx6_lib_infra_media_config` | FX6 | `libInfraMediaConfig.so` | `52,312` | `9709656102d582bd...` | `ADJ_SLOT_1`, `ADJ_SLOT_2`, `CTRL_TEMP`, `SLOT_SSD` |
| `fx3_lib_infra_media_detect` | FX3 | `libInfraMediaDetect.so` | `98,224` | `4c1dbb303cf9d2d7...` | `IMD_Starttemp`, `IMD_Stoptemp`, `NotifyTempEvent`, `_ZN24InfraMediaDetectThreadRM7GetTempEjPv` |
| `fx6_lib_infra_media_detect` | FX6 | `libInfraMediaDetect.so` | `98,224` | `8883fef94a7ba9e8...` | `IMD_Starttemp`, `IMD_Stoptemp`, `NotifyTempEvent`, `_ZN24InfraMediaDetectThreadRM7GetTempEjPv` |
| `fx3_lib_infra_media_common` | FX3 | `libInfraMediaCommon.so` | `402,624` | `1ddec7e4d903eaca...` | `CFexpress`, `FSYS_GTEST_VPGP4_AU_SIZE`, `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_drv_nvme_getlogpage_smartinformation`, `mcmn_dmm_hotplug` |
| `fx6_lib_infra_media_common` | FX6 | `libInfraMediaCommon.so` | `402,624` | `acbabff1ac3595a3...` | `CFexpress`, `FSYS_GTEST_VPGP4_AU_SIZE`, `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_drv_nvme_getlogpage_smartinformation`, `mcmn_dmm_hotplug` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`79,015,712 B`: `HDMI`, `RAW_OUTPUT`, `OFF_BY_MEDIA_THERMAL`, `FAN_CONTROL_MINIMUM`, `FAN_CONTROL_OFF_IN_REC`, `EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT`, `EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC`) and `cpapp-b.bin` (`15,980,568 B`: `DETECT_HPD`, `OBSERVE_HPD`, `FAN_EQ_ID`, `THERMISTOR_ADJ_START`) strictly via `os.O_RDONLY` without embedding raw bytes or keys.

### 1.2 Gate `G35`: Active Optical HDMI (AOC) Pin-18 `+5V` Over-Current / Reverse Backfeed & Unclamped Type-A Port Shear Firewall (`verify_hdmi_aoc_5v_and_port_shear_firewall`)
- **English**: Protects FX3's `SY-1129` mainboard full-size HDMI Type-A receptacle and `+5V` load switch (`55 mA` nominal limit) during external ProRes RAW / BRAW recorder rigging (`Atomos Ninja`, `Blackmagic Video Assist`, `SmallHD`). Computes Pin-18 power draw (`compute_hdmi_pin18_power_mw`) and cantilever shear moment (`compute_hdmi_type_a_cantilever_moment_nm`), failing closed on:
  1. `BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR`: `hdmi_pin18_draw_ma > 55.0` and `external_hdmi_5v_power_injector == False`.
  2. `BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD`: `sink_backfeed_voltage_v > 5.35` or (`camera_power_off == True` and `sink_pin18_backfeed_ma > 2.0` and `hdmi_reverse_blocking_diode_verified == False`).
  3. `BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR`: (`hdmi_cable_bend_moment_nm > 1.2` or `heavy_braided_or_coiled_hdmi_cable == True`) and `cage_hdmi_cable_clamp_locked == False`.
- **中文摘要**：保护外接 ProRes RAW / BRAW 录机（`Atomos Ninja`、`Blackmagic Video Assist`、`SmallHD`）布线时 FX3 `SY-1129` 主板全尺寸 HDMI Type-A 母座焊盘及 `+5V` 限流开关。门禁 `G35` 量化 Pin-18 功耗（$\text{mW}$）与接口悬臂弯矩（$\text{N}\cdot\text{m}$），在以下情形强制 fail-closed 阻断：
  1. `hdmi_pin18_draw_ma > 55.0` 且未接入外部 HDMI `+5V` 供电注入器（`external_hdmi_5v_power_injector == False`）$\rightarrow$ `BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR`；
  2. 接收端倒灌电压 `sink_backfeed_voltage_v > 5.35` V，或相机断电（`camera_power_off == True`）且反向倒灌电流 `sink_pin18_backfeed_ma > 2.0` mA 但未核验防倒灌阻塞二极管（`hdmi_reverse_blocking_diode_verified == False`）$\rightarrow$ `BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD`；
  3. 线缆弯矩 `hdmi_cable_bend_moment_nm > 1.2` $\text{N}\cdot\text{m}$ 或使用粗重编织/弹簧卷线（`heavy_braided_or_coiled_hdmi_cable == True`）且兔笼 HDMI 线夹未锁紧（`cage_hdmi_cable_clamp_locked == False`）$\rightarrow$ `BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR`。

### 1.3 Gate `G36`: CFexpress Type-A / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal-Throttle & Door-Open Flush Guard (`verify_cfexpress_vpg_thermal_and_door_guard`)
- **English**: Protects `XAVC S-I 4K 120p` (`600 Mbps`) and simultaneous dual-slot relay/backup recording against silent frame drops, NAND thermal throttling, and exFAT/FAT commit corruption. Computes effective required write floor (`compute_required_sustained_write_mb_s`) including VPG200/VPG400 certification floor and dual-slot simultaneous overhead margin (`1.25x`), failing closed on:
  1. `BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC`: `sustained_p99_write_mb_s < required_min_write_mb_s` (or uncertified VPG profile under dual-slot/high-bitrate load).
  2. `BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT`: `cfexpress_controller_temp_c > 82.0` or (`dual_slot_simultaneous_4k120p == True` and `ambient_temp_c > 38.0` and `sigma_fan_mode in {"OFF_IN_REC", "MINIMUM"}`).
  3. `BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH`: `slot_door_open_detected == True` and `media_flush_or_fat_commit_pending == True`.
- **中文摘要**：保护 `XAVC S-I 4K 120p`（`600 Mbps`）及双卡槽同步/接力备份录制免受隐性丢帧、NVMe/NAND 过热降频及 exFAT/FAT 元数据落盘损坏。门禁 `G36` 计算含双卡同步开销裕度（`1.25x`）与 VPG200/VPG400 认证底线的最低持续写入阈值，在以下情形强制 fail-closed 阻断：
  1. 实测 P99 持续写入速率 `sustained_p99_write_mb_s < required_min_write_mb_s`（或 VPG 认证/规格不满足高码率与双卡同步需求）$\rightarrow$ `BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC`；
  2. CFexpress 主控温度 `cfexpress_controller_temp_c > 82.0` $^\circ\text{C}$，或启用双卡同步 4K 120p（`dual_slot_simultaneous_4k120p == True`）且环境温度 `ambient_temp_c > 38.0` $^\circ\text{C}$ 同时 Sigma 风扇设为 `OFF_IN_REC` / `MINIMUM` $\rightarrow$ `BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT`；
  3. 检测到存储卡仓盖打开（`slot_door_open_detected == True`）且存在待刷新缓存或 FAT/exFAT 落盘提交（`media_flush_or_fat_commit_pending == True`）$\rightarrow$ `BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH`。

### 1.4 Unified 36-Gate Master Safety Preflight (`evaluate_36gate_preflight` / `verify-36-gates`)
- Composes `evaluate_34gate_preflight` (`G01..G34`) with `G35` and `G36`:
  - **Offline default mode / 离线默认模式**: `33/36` gates pass (`offline_33_gates_verified = True`, `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `36/36` simulation gates pass (`all_36_gates_verified = True`, `dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_hdmi_aoc_5v_cfexpress_and_36gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `40/40` passed (`OK`) | `0.941s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_hdmi_aoc_5v_cfexpress_and_36gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `40/40` passed (`OK`) | `0.959s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `581/581` passed (`OK`) | `4.292s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `581` run, `580` passed, `1` skipped (`OK`) | `4.256s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-36-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_33_OF_36_AWAITING_PHYSICAL_TIER0`, `verified=33/36`, `g35_to_g36_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-36-gates --clean-room --dry-run-simulated-backup --json` | CLI Clean-Room Dry-Run Simulated Backup | `status=VERIFIED_ALL_36_GATES_DRY_RUN_SIMULATED_BACKUP`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `offline_33_gates_verified=True`, `all_36_gates_verified=True`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `<0.2s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/hdmi_aoc_5v_cfexpress_and_36gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_hdmi_aoc_5v_cfexpress_and_36gate_guard.py`
6. `reports/2026-11-14-phase115-safety-hdmi5v-cfexpress-36gates/README.md`
