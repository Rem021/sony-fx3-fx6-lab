# Phase 121 — Stage 21 Virtual Camera Co-Emulation Report / 虚拟相机第 21 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 21 (`outputs/fx3-vm/`) — USB-C `UVC 1.5` (`4K30p MJPEG`, `1080p60p YUY2/MJPEG`) & `UAC 2.0` (`48kHz` 16-bit 2ch PCM) SuperSpeed `5 Gbps` vs High-Speed `480 Mbps` Negotiator, Wired `P12`-Safe `USB-LAN` (`CDC-NCM / RNDIS`) `SRT` (`Caller/Listener`, `AES-128/256`, `20..1000 ms` ARQ recovering `8%` loss with `0` dropped GOPs) & `RTMPS` TLS 1.3 Live Streaming, Sony `CRSDK` `PTP / PTP-IP` (`0x054C` / `0xD2xx`) Property Translator + Destructive `0x9280..` Flash-Opcode Firewall, and `G37` (`20V` USB-PD Decoy OVP `< 35 us` / `9V/3A 27W` PDO / `D-Tap + USB-PD` Isolator) & `G38` (`15-pin Multi-Terminal` `LTC > 5.0 Vpp` Clamp & `1.8V` Passive RX-Only UART `tx_bytes == 0`) HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 121 delivers **Stage 21** ([`usb_uvc_uac_srt_crsdk_usbpd_emulator.py`](../../outputs/fx3-vm/usb_uvc_uac_srt_crsdk_usbpd_emulator.py)) and integrates it into the unified 21-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase121_uvc_srt_crsdk_usbpd_hil: bool = True`, `--skip-phase121` backward-compatible flag). All 21 stages complete in **`1.155s < 1.8s` (Local Donor `O_RDONLY`)** and **`0.278s < 0.7s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**, backed by **40** new fast dual-mode unit tests (**684** total tests passing across `outputs/fx3-vm/tests` in both modes). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `EMMC_FLASH_MUTATION_BYTES = 0`, `WF12_00342260_HITS = 0`, `CXD90057_PAD_DAMAGE_EVENTS = 0`, `UVC_OSD_BURN_IN_FRAMES = 0`, `SRT_DROPPED_GOPS = 0`, `UART_TX_BYTES = 0`).
- **中文**: Phase 121 交付 **Stage 21**（[`usb_uvc_uac_srt_crsdk_usbpd_emulator.py`](../../outputs/fx3-vm/usb_uvc_uac_srt_crsdk_usbpd_emulator.py)）并接入统一 21 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase121_uvc_srt_crsdk_usbpd_hil: bool = True`，支持 `--skip-phase121` 向后兼容）。全板 21 阶段运行耗时严格优于性能预算：**`1.155s < 1.8s`**（本地只读供体模式 `LOCAL_DONOR_RDONLY`）与 **`0.278s < 0.7s`**（洁净室合成模式 `CLEAN_ROOM_SYNTHETIC`），新增 **40** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **684** 项全绿），全程锁定零写入与零损坏红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`EMMC_FLASH_MUTATION_BYTES = 0`、`WF12_00342260_HITS = 0`、`CXD90057_PAD_DAMAGE_EVENTS = 0`、`UVC_OSD_BURN_IN_FRAMES = 0`、`SRT_DROPPED_GOPS = 0`、`UART_TX_BYTES = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Pillar / 支柱 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 12 compact FX3 `v7.02` & FX6 `v6.01` binaries (`string_english_g.uxc`, FX6 `string_english.uxc`, `string_english_2.uxc`, `libInfraVericLiveStreaming.so`, `libInfraPtpControl.so` x2, `libptp.so`, `libNetServiceEther.so`, `cdc_ncm.ko`, `rndis_host.ko`, `libUsbBusPower.so`, `libBusPower.so`) SHA-256 & 36+ markers verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths absent (`mutation_bytes == 0`). | **PASS** |
| **Pillar A — USB-C `UVC 1.5` & `UAC 2.0` Negotiator** | 44-byte CRC32-checked `UVC 1.5` (`0x0150`) + `UAC 2.0` (`0x0200`, `48 kHz` 16-bit 2ch PCM = `1.536 Mbps`) descriptor bundle; SuperSpeed `5 Gbps` (`4K30p MJPEG` @ `151.536 Mbps`, `1080p60p YUY2` @ `1992.192 Mbps`) vs High-Speed `480 Mbps` USB 2.0 cable automatic resolution/codec step-down (`1080p60p YUY2 -> 1080p60p MJPEG` @ `76.536 Mbps < 480 Mbps`); clean feed free of OSD burn-in (`uvc_osd_burn_in_frames = 0`) & fail-closed S&Q / HDMI RAW16 / no-stepdown guards. | **PASS** |
| **Pillar B — Wired `USB-LAN` `SRT` / `RTMPS` (`P12`-Safe)** | Enforces wired `CDC-NCM` (`RTL8153` / `AX88179`) or wired `USB_RNDIS_WIRED`; hard-blocks `WIFI_WLAN0`, `WIFI_DIRECT_P2P`, `BT_PAN`, `MODEM_CELLULAR` (`wf12_00342260_hits = 0`); validates `SRT Caller/Listener` (`AES-128/256`, `20..1000 ms` ARQ) recovering up to **`8%` packet loss across 10 GOPs with `0` dropped GOPs**, plus `RTMPS TLS 1.3` Root-CA verification & plaintext `RTMP` rejection. | **PASS** |
| **Pillar C — Sony `CRSDK` `PTP / PTP-IP` & Flash Firewall** | Translates `0x054C` / `0xD2xx` controls (`Cine EI` `0xD243`, `Base ISO 800/12800` `0xD244`, `User 3D-LUT` `0xD253`, `Shutter Angle` `0xD20D`, `Rec` `0xD215`) across `USB_PTP` (`512 B` bulk aligned) & `WIRED_PTPIP_15740`, clamping `ILME-FX3` `P4` Variable ND (`0xD25A`) -> `Clear (0)`; hard-rejects destructive `0x9280..0x928F`, `0x100C/0x100D`, `0x9805`, `0x92F0..0x92F2` opcodes & `\x89UFU`/`BODYDATA.DAT` payloads in hybrid Stage-B mode (`emmc_flash_mutation_bytes = 0`). | **PASS** |
| **Pillar D — `G37` USB-PD Decoy & `G38` Multi-Term / UART HIL** | `G37`: Valid `9V/3A` (`27W`) PD PDO vs unnegotiated `20V` D-Tap-to-USB-C decoy VBUS OVP crowbar in **`18.2 us < 35 us`** (`pmic_clamped_peak_v = 8.92V < 9.6V`), plus dual-source `D-Tap + USB-PD` ground/cross-feed isolator (`0.0 mA` cross-feed). `G38`: `15-pin Multi-Terminal` `LTC > 5.0 Vpp` (`6.2 Vpp`) clamped to `3.30V <= 3.35V`, and `3.3V/5.0V` UART overdrive & active TX rejected enforcing **`1.8V` passive RX-only `tx_bytes = 0`** with **`cxd90057_pad_damage_events = 0`**. | **PASS** |

---

## 3. Observed Metrics & Digests / 实测指标与审计摘要

- **21-Stage Suite Runtime (Measured)**:
  - `LOCAL_DONOR_RDONLY`: **`1.155s`** (budget `< 1.8s`), Stage 21 digest `43f1aed6d3e7...`, Suite digest `d9698dfbe6ee...`
  - `CLEAN_ROOM_SYNTHETIC`: **`0.278s`** (budget `< 0.7s`), Stage 21 digest `123f3b089119...`, Suite digest `7f54062a301d...`
- **Unit Tests**: `40` new Phase 121 tests (`outputs/fx3-vm/tests/test_usb_uvc_uac_srt_crsdk_usbpd_emulator.py`), **`684`** total tests in `outputs/fx3-vm/tests` passing in both `LOCAL_DONOR_RDONLY` (`24.713s`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` (`22.247s`).
- **Clean-Room Hygiene Audit**: `scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN` (`0.05s`, zero `.pyc` or stray binaries).

---

## 4. Verification Commands / 复现校验命令

```sh
# 1. Unit test discovery across all 684 tests (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 2. Stage 1..21 full-board co-emulation (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
