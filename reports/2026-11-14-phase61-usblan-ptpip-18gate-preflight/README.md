# Phase 61 — Wired `USB-LAN` (`CDC-NCM`/`RTL8153` + `PTP-IP 15740` / `Monitor & Control`) Security Firewall & 18-Gate Master Safety Preflight Engine (`G01..G18`)

# 第 61 阶段 — 有线 `USB-LAN`（`CDC-NCM`/`RTL8153` + `PTP-IP 15740` / `Monitor & Control`）安全防火墙与 18 门主安全预检引擎（`G01..G18`）

> **Date / 日期**: `2026-11-14`  
> **Owner / 负责代理**: Hydrogen-54 (`antigravity`, isolated child worktree)  
> **Primary Module / 核心模块**: [`outputs/fx3-safety/fx3_safety/usblan_ptpip_and_18gate_preflight.py`](../../outputs/fx3-safety/fx3_safety/usblan_ptpip_and_18gate_preflight.py)  
> **CLI Entrypoint / 命令行入口**: [`outputs/fx3-safety/fx3_safety/__main__.py`](../../outputs/fx3-safety/fx3_safety/__main__.py) (`verify-18-gates [--clean-room] [--dry-run-tier0] [--json]`)  
> **Unit Tests / 单元测试**: [`outputs/fx3-safety/tests/test_usblan_ptpip_and_18gate_preflight.py`](../../outputs/fx3-safety/tests/test_usblan_ptpip_and_18gate_preflight.py) (`30` dual-mode tests; `260` total tests in `outputs/fx3-safety/tests/`)  
> **Safety Redlines / 硬件安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `os.O_RDONLY` only, zero raw `bytes` repr output (`.hex()` only).

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 61 operationalizes Phase 57 ([`exfat_media_integrity_guard.py`](../../outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py)) and Phase 58 (`Wave-5 USB-LAN / PTP-IP`) into an executable **Wired `USB-LAN` / `PTP-IP 15740` / `Monitor & Control` Security Firewall** and **18-Gate Master Safety Preflight Engine (`G01..G18`)**, leaving `preflight.py` (`G01..G12`) and `master_16gate_preflight.py` (`G01..G16`) completely untouched:

1. **Wired `USB-LAN` (`CDC-NCM` / `RTL8153` / `AX88179`) & `P12` Airplane-Mode Coexistence**:
   - Inspects the 7 pinned FX6 donor artifacts (`cdc_ncm.ko`, `rndis_host.ko`, `libNetServiceEther.so`, `libInfraPtpControl.so`, `libptp.so`, `libSshInfraNetworkCommon.so`, `libWlanResource.so`) strictly via `os.O_RDONLY` (with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback).
   - Enforces wired-only `CDC-NCM` (`1000 Mbps` `RTL8153` or original `AX88179` on `eth0`/`usblan0`), rejecting `RNDIS`, `CDC-ECM`, `AX88179A/B`, `2.5G/5G/10G` adapters, wireless interfaces (`wlan0`/`p2p0`), and missing FX3 Manual same-subnet gateways, while `P12` (`0x70d4 -> rc=0`) + `BK4\0` Airplane-Mode keeps Wi-Fi (`wifi_radio_enabled == False`) and Bluetooth (`/dev/ttyAMA3`, `bt_hci_tx_packets == 0`) 100% disabled (`wf12_00342260_immune == True`, Sony Notice `00342260` `WF-12` bootloop immune).
2. **`PTP-IP` (`TCP 15740`) & `Monitor & Control` (`UDP 1900`, `HTTP/HTTPS`) Fail-Closed Security Firewall**:
   - Whitelists safe shooting/monitoring operations (`GetDeviceInfo`, `GetEvent`, live-view/waveform streams, `ISO`/`EI`/`Shutter`/`WB`/AF touch-focus, SSDP `UDP 1900` `M-SEARCH`, `Monitor & Control` `/sony/camera` safe shooting RPCs).
   - **Blocks fail-closed** all restricted opcodes (`0x9280..0x92FF`), `SendObjectInfo`/`SendObject` `.dat`/`.ufu` firmware payloads, HTTP `/fwupdate`, service-mode unlocks (`054C:0336` / `AdjustControl`), NVRAM `BK4` persistent writes, raw partition transfers (`/dev/nflasha*` / `sector0`), and raw `telnet`/`rsh` shells with `persistent_emmc_writes_authorized == False`.
3. **18-Gate Master Safety Preflight (`evaluate_18_master_safety_gates`)**:
   - Composes `evaluate_16_master_safety_gates` (`G01..G16`) with:
     - **`G17` (`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`)**: Blocks `H0`/`H1` entry if `VolumeDirty`, invalid 12-sector `BootChecksum`, client `XDROOT`/`M4ROOT` clips, unfinalized `.RSV` files, or `p1` filesystem overlap exist on `Slot A`/`Slot B`.
     - **`G18` (`USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE`)**: Enforces wired-only `USB-LAN` safe-opcode filtering + `P12` `BK4` Airplane-Mode wireless radio silence (`wifi_radio_enabled == False`, `persistent_emmc_writes_authorized == False`).

**中文摘要**:  
第 61 阶段将第 57 阶段（`exFAT BootChecksum` 与生产素材隔离防火墙）与第 58 阶段（Wave-5 `USB-LAN` / `PTP-IP` 协议分析）工程化落地为**有线 `USB-LAN` / `PTP-IP 15740` / `Monitor & Control` 安全防火墙**与**18 门主安全预检引擎（`G01..G18`）**（保持 `preflight.py` 与 `master_16gate_preflight.py` 零改动）：
1. **有线 `USB-LAN` 与 `P12` 飞行模式共存校验**：严格基于 `os.O_RDONLY`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室基线）核验 7 个 FX6 供体模块，强制要求有线 `CDC-NCM`（`1 Gbps` `RTL8153` 或原版 `AX88179`）与同网段 FX3 手动网关，同时通过 `P12` (`0x70d4 -> rc=0`) + `BK4\0` 影分身保持 Wi-Fi（`wifi_radio_enabled == False`）与蓝牙（`/dev/ttyAMA3`、`bt_hci_tx_packets == 0`）100% 静默，彻底免疫索尼 `00342260` `WF-12` 死循环。
2. **`PTP-IP`（`TCP 15740`）与 `Monitor & Control` 失效关闭防火墙**：放行安全拍摄与监看操作（`GetDeviceInfo`、`GetEvent`、实时监看/波形图、`ISO`/`EI`/快门/白平衡/触控对焦），对 `0x9280..0x92FF`、`SendObjectInfo` `.dat`/`.ufu` 固件载荷、HTTP `/fwupdate`、服务模式解锁、NVRAM `BK4` 持久写入、裸分区传输及 `telnet`/`rsh` 远控壳实施失效关闭（fail-closed）拦截，且 `persistent_emmc_writes_authorized == False`。
3. **18 门主安全预检（`G01..G18`）**：在 `G01..G16` 基础上串联 `G17`（`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`）与 `G18`（`USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE`），并接入 CLI `verify-18-gates [--clean-room] [--json]` 与 30 项双模式快速单元测试（`outputs/fx3-safety/tests/` 总计 **260 项测试**）。

---

## 2. Technical Architecture & Deliverables / 技术交付详情

| Component / 模块 | Entrypoints / 关键接口 | Enforced Invariants / 强制不变量 |
| :--- | :--- | :--- |
| **1. `O_RDONLY` Donor Audit** | `audit_usblan_ptpip_donor_contracts` | Verifies 7 FX6 artifacts (`cdc_ncm.ko`, `rndis_host.ko`, `libNetServiceEther.so`, `libInfraPtpControl.so`, `libptp.so`, `libSshInfraNetworkCommon.so`, `libWlanResource.so`) via `os.O_RDONLY` with `CLEAN_ROOM_SYNTHETIC` fallback. |
| **2. Wired `USB-LAN` + `P12` Airplane-Mode** | `verify_usblan_wired_control_and_airplane_coexistence` | Enforces `CDC-NCM` + `1000 Mbps` `RTL8153`/`AX88179` on `eth0`/`usblan0`, FX3 Manual same-subnet gateway, `wifi_radio_enabled=False`, `bluetooth_uart_enabled=False` (`/dev/ttyAMA3`), `bt_hci_tx_packets=0`, `wf12_00342260_immune=True`. |
| **3. `PTP-IP 15740` & `Monitor & Control` Firewall** | `classify_usblan_ptpip_or_mc_operation`, `evaluate_ptpip_15740_packet`, `audit_usblan_ptpip_and_mc_firewall` | Allows safe shooting/telemetry (`GetDeviceInfo`, `GetEvent`, live-view/waveform, `ISO`/`EI`/`Shutter`/`WB`/AF touch-focus, SSDP `1900`, `/sony/camera`); blocks `0x9280..0x92FF`, `SendObjectInfo` `.dat`/`.ufu`, HTTP `/fwupdate`, service unlock, `BK4` NVRAM writes, raw partitions, `telnet`/`rsh`. |
| **4. Gate `G17` (`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`)** | `evaluate_g17_exfat_and_client_media_isolation` | Integrates Phase 57 `evaluate_exfat_media_integrity_guard`; blocks `H0`/`H1` on `VolumeDirty`, invalid 12-sector `BootChecksum`, `XDROOT`/`M4ROOT` client clips, `.RSV`, or `p1` `EXFAT   ` spoof. |
| **5. Gate `G18` & Master 18-Gate Engine** | `evaluate_g18_usblan_ptpip_and_airplane_coexistence`, `evaluate_18_master_safety_gates` | Composes `G01..G16` + `G17` + `G18`; enforces `persistent_emmc_writes_authorized == False`, `persistent_write_release == False`. |
| **6. CLI & Dual-Mode Tests** | `python3 -m fx3_safety verify-18-gates [--clean-room] [--dry-run-tier0] [--json]`, `test_usblan_ptpip_and_18gate_preflight.py` | 30 new unit tests (`0.092s`), bringing `outputs/fx3-safety/tests/` from 230 to **260 passing tests** (`<0.45s`). |

---

## 3. Verification Receipts / 实测验证记录

1. **CLI Verification (`verify-18-gates`)**:
   - Local Donor (`O_RDONLY`):
     `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-18-gates` ->  
     `status=VERIFIED_G01_G09_AND_G13_G18_AWAITING_PHYSICAL_TIER0 mode=LOCAL_DONOR_O_RDONLY verified=15/18 g17_to_g18_all_passed=True all_18_gates_verified=False h0_h1_trial_entry_allowed=True persistent_emmc_writes_authorized=False` (`rc=0`).
   - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1 --dry-run-tier0 --json`):
     `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-18-gates --clean-room --dry-run-tier0 --json` ->  
     `schema="fx3-usblan-ptpip-18gate-preflight-v1"`, `verification_mode="CLEAN_ROOM_SYNTHETIC"`, `verified_gates=18/18`, `all_18_gates_verified=true`, `h0_h1_trial_entry_allowed=true`, `persistent_emmc_writes_authorized=false` (`rc=0`).
2. **Unit Tests (Dual-Mode / 双模式单元测试)**:
   - `test_usblan_ptpip_and_18gate_preflight.py`: **30 tests in 0.092s — OK**.
   - Full `outputs/fx3-safety/tests` (Local Donor mode): **260 tests in 0.429s — OK**.
   - Full `outputs/fx3-safety/tests` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **260 tests in 0.402s — OK (skipped=1)**.
3. **Repository Hygiene**:
   - `make clean-audit` verified clean (zero untracked `.pcap`/`.bin`/`.so`/`.pyc` or `__pycache__` artifacts; `preflight.py` and `master_16gate_preflight.py` untouched).
