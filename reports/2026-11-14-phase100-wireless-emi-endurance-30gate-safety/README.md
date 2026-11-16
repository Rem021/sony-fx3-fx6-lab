# Milestone Phase 100 — Cinema Wireless Video TX 5GHz/6GHz Near-Field EMI & D-Tap/HDMI Hot-Plug ESD Guard (`Gate G29`), Long-Form (>6h) Continuous Recording exFAT Clip-Spanning & CFexpress SMART Wear / Zero-NVRAM-Churn Endurance Guard (`Gate G30`) & Unified 30-Gate Master Safety Preflight (`G01..G30`)

# 第 100 阶段里程碑 — 电影无线图传 5GHz/6GHz 近场 EMI 与 D-Tap/HDMI 热插拔 ESD 防护（门禁 `G29`）、超长连续录制（>6h）exFAT 跨文件无缝衔接与 CFexpress SMART 损耗 / 零 NVRAM 擦写耐久防火墙（门禁 `G30`）及 30 门禁主安全预检（`G01..G30`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h99-phase100-safety-wireless-emi-endurance-30gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`wireless_tx_emi_endurance_and_30gate_guard.py`](../../outputs/fx3-safety/fx3_safety/wireless_tx_emi_endurance_and_30gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, prior gate modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`, `intake_occlusion_tripod_and_26gate_guard.py`, `sensor_curtain_subzero_and_28gate_guard.py`) unmodified.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase100_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` media-health/SMART, backup/NVRAM write, filesystem spanning, and hot-plug FSM libraries strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_infra_media_mount` | FX3 | `libInfraMediaMount.so` | `65,392` | `33b4c61c39f724e0...` | `GetMediaLifeInfo`, `IMM_GetMediaLifeInfo`, `mcmn_drv_updatelifeinfo` |
| `fx3_lib_infra_media_common` | FX3 | `libInfraMediaCommon.so` | `402,624` | `1ddec7e4d903eaca...` | `mcmn_drv_nvme_getlifeinfofromsmartinfo`, `mcmn_drv_nvme_getlogpage_smartinformation`, `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_dmm_hotplug` |
| `fx3_lib_backup` | FX3 | `libbackup.so` | `14,232` | `6a3c5f6067620c00...` | `Backup_read`, `Backup_write`, `Backup_sync_all`, `Backup_protect` |
| `fx3_lib_backup_manager` | FX3 | `libBackupManager.so` | `10,272` | `ef95ca41dadcad9a...` | `_ZNK13BackupManager13BackupManager11writeBackupEtjPKv`, `_ZNK13BackupManager13BackupManager20readBackupDecryptionEjPv` |
| `fx3_lib_infra_fsys` | FX3 | `libInfraFsys.so` | `683,632` | `ec0dcdfa2bd0bb92...` | `flash_span`, `fsysDepLog_DriveIOQueueIOVecCountLimitOverflow` |
| `fx6_lib_hotplug` | FX6 | `libHotplug.so` | `64,776` | `5697dcca69ea80ba...` | `MakeObjEject`, `MakeObjInsert`, `guardAcvOn` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`EXFAT_MEDIA_FILESYSTEM_SLOT1_FAT`, `EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT`, `FAT32_CFE_SLOT1`, `CAUTION_ID_FACTOR_RELAY_REC_ON_FUNCTION`, `EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC`, `HPD`) and `cpapp-b.bin` (`DETECT_HPD`, `OBSERVE_HPD`, `HPD_DISABLE`, `HPD_ENABLE`, `BACKUP_WRITE`, `BACKUP_READ`, `EXTERNALTC_LOCK`, `LTC`) strictly via `os.O_RDONLY`.

### 1.2 Gate `G29`: Cinema Wireless Video TX 5GHz/6GHz Near-Field EMI, D-Tap/HDMI Hot-Plug ESD & Multi-Port LTC Impedance Guard (`verify_wireless_tx_emi_and_hotplug_esd_guard`)
- **English**: Cinema B-cam rigs frequently mount `500 mW – 1000 mW` 5 GHz / 6 GHz / DFS wireless video transmitters (Teradek / Hollyland / DJI SDR) onto the FX3 top plate or cold shoe, where near-field E-field ($E = \frac{\sqrt{30 P_W G}}{r_m}$) couples into MI-Shoe audio ADC lines or HDMI TMDS clock pairs, and hot-plugging HDMI with a D-Tap-powered TX having an ungrounded floating return destroys `CXD90057` HDMI ESD diodes:
  - `BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE`: `wireless_tx_power_mw > 250.0` and `antenna_to_mishoe_or_hdmi_mm < 35.0` and `shielded_coax_hdmi_cable == False`.
  - `BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE`: (`dtap_powered_wireless_tx == True` and `power_on_sequence != 'GND_POWER_FIRST_SIGNAL_LAST'`) or `hot_plug_while_dtap_live_unisolated == True`.
  - `BLOCKED_TIMECODE_BNC_OVER_VOLTAGE`: `multiport_tc_input_vpp > 5.0` (protects FX3 Multi-Port `3.3 V`-tolerant TC pin from studio `+12 V` RS-422 / high-level LTC feeds).
- **中文摘要**：针对电影 B 机位常在 FX3 机顶/冷靴安装 `500 mW – 1000 mW` 5GHz/6GHz/DFS 无线图传（Teradek / Hollyland / DJI SDR）的工程风险：当发射功率 `> 250.0 mW`、天线距 MI 热靴或 HDMI `< 35.0 mm` 且未使用屏蔽同轴 HDMI 线时触发 `BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE`；当图传由 D-Tap 供电且上电顺序非 `GND_POWER_FIRST_SIGNAL_LAST` 或在 D-Tap 带电非隔离下热插拔 HDMI 时触发 `BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE`（防止虚地回流浪涌击穿 `CXD90057` HDMI ESD 二极管）；当 Multi-Port TC 输入 `> 5.0 Vpp`（如 `+12 V` RS-422/高电平 LTC）时触发 `BLOCKED_TIMECODE_BNC_OVER_VOLTAGE` 保护 `3.3 V` 耐压时间码引脚。

### 1.3 Gate `G30`: Long-Form (`>6h..24h`) Continuous Recording exFAT Seamless Spanning, CFexpress SMART Wear & Zero-eMMC-NVRAM-Churn Endurance Guard (`verify_longform_exfat_smart_and_nvram_guard`)
- **English**: Protects documentary/concert FX6-on-FX3 6–24 hour non-stop runs from file-system truncation, flash wear exhaustion, and runtime internal eMMC `BKID` wear:
  - `BLOCKED_FAT32_4GIB_SPANNING_TRAP`: `planned_continuous_min > 10.0` and `filesystem != 'exFAT'`.
  - `BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION`: `smart_percentage_used > 90` or `spare_blocks_pct < 10.0` or `media_nand_temp_c > 78.0`.
  - `BLOCKED_PERIODIC_EMMC_NVRAM_CHURN`: `runtime_nvram_flush_hz > 0.0` (or `ram_shadow_bkid_enabled == False`), enforcing 100% RAM-shadow `BKID` state so FX3's internal eMMC `p13..p15` endures zero wear cycles during Stage-B trial runs.
- **中文摘要**：面向 6–24 小时纪录片/演唱会连续录制场景：当连续录制 `> 10.0 min` 且存储卡文件系统不为 `exFAT` 时阻断 FAT32 `4 GiB` 断点陷阱（`BLOCKED_FAT32_4GIB_SPANNING_TRAP`）；当 CFexpress/SDXC 卡 `smart_percentage_used > 90`、备用块 `spare_blocks_pct < 10.0%` 或 NAND 温度 `> 78.0°C` 时触发 `BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION`；当运行时存在 `runtime_nvram_flush_hz > 0.0`（或关闭 RAM 影子 `BKID` 状态）时触发 `BLOCKED_PERIODIC_EMMC_NVRAM_CHURN`，强制保证机内 eMMC `p13..p15` 零擦写损耗。

### 1.4 Unified 30-Gate Master Safety Preflight (`evaluate_30gate_preflight` / `verify-30-gates`)
- Composes `evaluate_28gate_preflight` (`G01..G28`) with `G29` and `G30`:
  - **Offline default mode / 离线默认模式**: `27/30` gates pass (`G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `30/30` simulation gates pass (`dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_wireless_tx_emi_endurance_and_30gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `38/38` passed (`OK`) | `0.630s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_wireless_tx_emi_endurance_and_30gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `38/38` passed (`OK`) | `0.624s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `468/468` passed (`OK`) | `2.499s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `468` run, `467` passed, `1` skipped (`OK`) | `2.462s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-30-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_27_OF_30_AWAITING_PHYSICAL_TIER0`, `verified=27/30`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-30-gates --dry-run-simulated-backup` | CLI Dry-Run Simulated Backup | `status=VERIFIED_ALL_30_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=30/30`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.2s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `<0.1s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/wireless_tx_emi_endurance_and_30gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_wireless_tx_emi_endurance_and_30gate_guard.py`
6. `reports/2026-11-14-phase100-wireless-emi-endurance-30gate-safety/README.md`
