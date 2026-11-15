# Milestone Phase 120 — Unnegotiated 20V USB-C PD Trigger-Cable / Dual-Source D-Tap+USB-PD Cross-Feed & Isochronous UVC 1.5 Thermal Firewall (`Gate G37`), Sony 15-Pin Multi-Terminal LTC +5V Clash / 3.3V UART Over-Drive & Destructive CRSDK PTP Flash-Opcode Hardware Guard (`Gate G38`), and Unified 38-Gate Master Safety Preflight (`G01..G38`)

# 里程碑第 120 阶段 — 未协商 20V USB-C PD 诱骗线 / 双源 D-Tap+USB-PD 交叉馈电与等时 UVC 1.5 热饱和防火墙（`Gate G37`）、索尼 15-Pin Multi-Terminal LTC +5V 冲突 / 3.3V UART 过压驱动与破坏性 CRSDK PTP 刷写操作码硬件防护（`Gate G38`）及 38 门禁主安全预检（`G01..G38`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h124-phase120-safety-usbpd-multiterminal-38gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`usbpd_trigger_multiterminal_and_38gate_guard.py`](../../outputs/fx3-safety/fx3_safety/usbpd_trigger_multiterminal_and_38gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `overall_ready_for_hardware_attach = False` (offline & dry-run), prior gate modules (`G01..G36`) untouched.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase120_donor_contracts`)
Inspects FX3 `v7.02` & FX6 `v6.01` USB-PD bus-power management (`libBusPower.so`, `libUsbBusPower.so`), multi-port USB VBUS FSM control (`libUsbControl.so`), and multi-session PTP/CrSDK transport control (`libInfraPtpControl.so`) strictly via `os.open(..., os.O_RDONLY)` with deterministic synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_bus_power` | FX3 | `libBusPower.so` | `43,968` | `4c39d2789745a463...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT` |
| `fx6_lib_bus_power` | FX6 | `libBusPower.so` | `43,968` | `d4f2ffe4e74786b6...` | `_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT` |
| `fx3_lib_usb_bus_power` | FX3 | `libUsbBusPower.so` | `48,232` | `c606880c92ecf602...` | `_ZN11UsbBusPower11IsVbusReadyEv`, `_ZN11UsbBusPower22SetPowerContractStatusEi`, `_ZN11UsbBusPower15GetCurrentLimitEv`, `_ZN11UsbBusPower18SetWatchSWForceOFFEv` |
| `fx6_lib_usb_bus_power` | FX6 | `libUsbBusPower.so` | `48,232` | `4215a9e989d25896...` | `_ZN11UsbBusPower11IsVbusReadyEv`, `_ZN11UsbBusPower22SetPowerContractStatusEi`, `_ZN11UsbBusPower15GetCurrentLimitEv`, `_ZN11UsbBusPower18SetWatchSWForceOFFEv` |
| `fx3_lib_usb_control` | FX3 | `libUsbControl.so` | `135,424` | `2bf51f28fd5066e5...` | `_ZN12UsbIfWrapper20isMultiPortSupportedEv`, `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`, `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT` |
| `fx6_lib_usb_control` | FX6 | `libUsbControl.so` | `135,424` | `951d1da8a4366dc8...` | `_ZN12UsbIfWrapper20isMultiPortSupportedEv`, `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`, `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT` |
| `fx3_lib_infra_ptp_control` | FX3 | `libInfraPtpControl.so` | `165,320` | `445c83b36c7243a8...` | `InfraPtpControl_Init`, `PTPT_init`, `PTPT_open`, `_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv` |
| `fx6_lib_infra_ptp_control` | FX6 | `libInfraPtpControl.so` | `152,520` | `5af1afff957290bb...` | `InfraPtpControl_Init`, `PTPT_init`, `PTPT_open`, `_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv` |

When `include_large_binaries=True`, streams FX3 `appFw.so` (`79,015,712 B`: `DFS_FACTOR_UVC`, `PID_SET_EE_FRAME_RATE_MODE_BY_UVC`, `VAL_HAITA_file_format_xavc_hs_streaming_restriction_UVC_FORMAT_30p`, `AUTO_POFF_TEMP`, `VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_STANDARD`, `VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_HIGH`, `INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS`, `FIRMWARE_UPDATE_CHECK_MEDIA_NO_WRITABLE`) and `cpapp-b.bin` (`15,980,568 B`: `BATT_AUTH_S`, `BATT_STATE1_S`, `THERMISTOR_ADJ_START`, `FAN_EQ_ID`) strictly via `os.O_RDONLY` without embedding raw bytes or keys.

### 1.2 Gate `G37`: Unnegotiated `20V` USB-C PD Trigger-Cable, Dual-Source (`D-Tap` Dummy-Batt + `USB-PD` VBUS) Cross-Feed & Continuous `4K30p` `UVC 1.5` Thermal Saturation Firewall (`verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall`)
- **English**: Protects FX3's `SY-1129` USB Type-C CC/VBUS PMIC front-end and `CXD90057` SoC thermal envelope during external V-Mount rigging and long-form `4K30p` `UVC 1.5` USB streaming, failing closed on:
  1. `BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE`: `usbc_vbus_measured_v > 9.6` without valid `9V/3A` (`27W`) PD PDO contract (e.g., passive `12V/15V/20V` D-Tap-to-USB-C decoy cable forcing `14.8V..20V` onto VBUS before CC negotiation, or `cc_pin_short_to_vbus == True`).
  2. `BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED`: `unregulated_dummy_battery_active == True` and `usbc_pd_power_sink_active == True` and `common_vmount_battery_shared_without_dc_isolator == True`.
  3. `BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION`: `uvc_4k30p_streaming_hours >= 2.0` and `ambient_temp_c > 35.0` and `internal_np_fz100_charging_while_streaming == True` and `auto_power_off_temp_standard == True`.
- **中文摘要**：保护 FX3 `SY-1129` USB Type-C CC/VBUS PMIC 前端及 `CXD90057` SoC 在 V 口外接供电与长时间 `4K30p` `UVC 1.5` 推流下的电气与热安全性，在以下情形强制 fail-closed 阻断：
  1. `usbc_vbus_measured_v > 9.6` V 且缺乏合法 `9V/3A`（`27W`）PD PDO 协商（如被动 `12V/15V/20V` D-Tap 转 USB-C 诱骗线在 CC 协商前直接强加 `14.8V..20V`，或 `cc_pin_short_to_vbus == True`）$\rightarrow$ `BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE`；
  2. 无调节假电池与 USB-PD 供电同时接入且共用同一块 V 口电池但缺乏 DC-DC 隔离器（`unregulated_dummy_battery_active == True` 且 `usbc_pd_power_sink_active == True` 且 `common_vmount_battery_shared_without_dc_isolator == True`）$\rightarrow$ `BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED`；
  3. 连续 `4K30p` `UVC 1.5` 推流 `>= 2.0` 小时、环境温度 `> 35.0` $^\circ\text{C}$、同时开启机内 `NP-FZ100` 充电且自动关机温度仍设为标准档（`auto_power_off_temp_standard == True`）$\rightarrow$ `BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION`。

### 1.3 Gate `G38`: Sony `15-Pin Multi-Terminal` `LTC` BNC Adapter `+5V` Pin Clash, `3.3V/5V` UART Over-Drive (`1.8V` `CXD90057` Pad Limit) & Destructive `CRSDK` `PTP` Firmware-Flash Opcode Hardware Guard (`verify_multiterminal_ltc_uart_and_ptp_guard`)
- **English**: Protects FX3's `15-pin Multi/Micro-USB` connector (`LTC` Timecode-In, `LANC`/remote, composite/sense pins), `1.8V` `CXD90057` debug UART pads, and hybrid-mode USB PTP/CrSDK channel, failing closed on:
  1. `BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH`: `ltc_bnc_adapter_attached == True` and (`ltc_peak_to_peak_v > 5.0` or `third_party_non_sony_id_resistor_short == True`).
  2. `BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD`: `uart_probe_attached == True` and (`uart_logic_level_v > 1.95` or `uart_tx_line_physically_connected == True`), enforcing strictly `1.8V` passive RX-only monitoring.
  3. `BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE`: `usb_ptp_crsdk_session_active == True` and `ptp_fw_flash_opcodes_blocked_in_filter == False`.
- **中文摘要**：保护 FX3 精密 `15-pin Multi/Micro-USB` 复用接口（`LTC` 时间码输入、`LANC`/遥控及检测引脚）、`1.8V` `CXD90057` 调试 UART 焊盘及混合模式 USB PTP/CrSDK 通道，在以下情形强制 fail-closed 阻断：
  1. 接入 Multi-Terminal `LTC` BNC 适配器且 `ltc_peak_to_peak_v > 5.0` Vpp 或第三方非索尼 ID 电阻短路（`third_party_non_sony_id_resistor_short == True`）$\rightarrow$ `BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH`；
  2. 接入 UART 探针且电平 `> 1.95` V（如 `3.3V/5V` 适配器过驱 `1.8V` 焊盘）或物理连接了 TX 发送线（`uart_tx_line_physically_connected == True`），强制仅允许严格 `1.8V` 被动只读 RX 监听 $\rightarrow$ `BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD`；
  3. 处于 `USB PTP / CrSDK` 混合调试会话（`usb_ptp_crsdk_session_active == True`）但过滤器未拦截破坏性固件刷写操作码（`ptp_fw_flash_opcodes_blocked_in_filter == False`）$\rightarrow$ `BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE`。

### 1.4 Unified 38-Gate Master Safety Preflight (`evaluate_38gate_preflight` / `verify-38-gates`)
- Composes `evaluate_36gate_preflight` (`G01..G36`) with `G37` and `G38`:
  - **Offline default mode / 离线默认模式**: `35/38` gates pass (`offline_35_gates_verified = True`, `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `38/38` simulation gates pass (`all_38_gates_verified = True`, `dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_usbpd_trigger_multiterminal_and_38gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `42/42` passed (`OK`) | `1.283s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_usbpd_trigger_multiterminal_and_38gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `42/42` passed (`OK`) | `1.671s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Local Donor) | `623/623` passed (`OK`) | `6.174s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | Full Suite (Clean-Room) | `623` run, `622` passed, `1` skipped (`OK`) | `6.050s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-38-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_35_OF_38_AWAITING_PHYSICAL_TIER0`, `verified=35/38`, `g37_to_g38_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-38-gates --clean-room --dry-run-simulated-backup --json` | CLI Clean-Room Dry-Run Simulated Backup | `status=VERIFIED_ALL_38_GATES_DRY_RUN_SIMULATED_BACKUP`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `offline_35_gates_verified=True`, `all_38_gates_verified=True`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `0.04s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/usbpd_trigger_multiterminal_and_38gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_usbpd_trigger_multiterminal_and_38gate_guard.py`
6. `reports/2026-11-14-phase120-safety-usbpd-multiterminal-38gates/README.md`
