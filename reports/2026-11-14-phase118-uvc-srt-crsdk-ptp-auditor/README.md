# Phase 118 — 23rd Unified `fx3-firmware-lab` Auditor: USB-C UVC 1.5 / UAC 2.0 Streaming, Wired P12-Safe SRT / RTMPS Streaming, & Sony CRSDK PTP / PTP-IP Flash-Opcode Firewall
# 第 118 阶段 — 第 23 个统一 `fx3-firmware-lab` 审计器：USB-C UVC 1.5 / UAC 2.0 推流、有线 P12 安全 SRT / RTMPS 网络推流与索尼 CRSDK PTP / PTP-IP 属性映射及固件刷写拦截防火墙

- **Date / 日期**: 2026-11-14
- **Schema / 架构版本**: `fx3_firmware_lab_phase118_uvc_srt_crsdk_ptp_v1` (`118.0.0`)
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/usb_uvc_uac_srt_and_crsdk_ptp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/usb_uvc_uac_srt_and_crsdk_ptp_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-uvc-srt-crsdk` (and 23rd auditor inside `audit-all`)
- **Related Wave-13 Research / 关联情报报告**: [`reports/2026-11-14-global-sony-wave13-uvc-srt-crsdk-unbrick-intel/README.md`](../2026-11-14-global-sony-wave13-uvc-srt-crsdk-unbrick-intel/README.md)

---

## English Technical Report

### 1. Executive Summary & Clean-Room Compliance

Phase 118 delivers the **23rd unified clean-room auditor** (`usb_uvc_uac_srt_and_crsdk_ptp_auditor.py`) for the Sony `ILME-FX3` (`v7.02`) + `ILME-FX6` (`v6.01`) Cinema Line firmware compatibility lab, grounded in the Wave-13 live web intelligence sync.

- **Zero Embedded Keys / Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`)**: In Local Donor mode (`LOCAL_DONOR_VERIFIED`), the auditor inspects 13 local FX3 `v7.02` & FX6 `v6.01` donor binaries, `global.xdb` (`uxa\x07`) registries, and `.uxc` string packs strictly via `os.O_RDONLY` and section-scoped `.rodata`/`.dynstr` `mmap.ACCESS_READ` scans without creating `.pyc` or modifying any binary on disk.
- **Deterministic Clean-Room Fallback (`CLEAN_ROOM_SYNTHETIC`)**: Under `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or missing donor files, `build_clean_room_uvc_srt_crsdk_fixtures()` synthesizes self-contained ELF64, `global.xdb`, and `.uxc` fixtures carrying the verified symbol contracts.

### 2. Verified Observed Metrics & Dual-Mode Digests

| Metric | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) |
| --- | --- | --- |
| Phase 118 `all_checks_passed` | `True` (`errors = ()`) | `True` (`errors = ()`) |
| Phase 118 Standalone Runtime | `0.1129 s` cold / `0.1101 s` warm (`< 0.35 s`) | `0.0021 s` warm (`< 0.02 s`) |
| Phase 118 `report_sha256` | `b9a2fd3b0b6f3595be4bebbdde10528b3488362554dd1d0b3c55158317f8e722` | `1c318c13526382194b5994fa12190c3385276b9d61ecab71bcd1b153d6071551` |
| `audit-all --json` Verdict | `23/23` green in `9.522 s` | `23/23` green in `0.518 s` |
| Full Lab `unittest` Suite | `673` tests OK in `22.662 s` | `673` tests OK in `12.309 s` |
| Phase 118 Unit Tests (`test_usb_uvc_uac_srt_and_crsdk_ptp.py`) | `42` tests OK in `0.539 s` | Included in `673` clean-room pass |
| `scripts/run_all_lab_tests.py --clean-only` | — | `CLEAN / ALL GREEN` in `0.05 s` |

#### Verified Donor File Sizes (`os.O_RDONLY`)
- `fx3_appfw`: `79,015,712` B | `fx6_appfw`: `50,520,424` B
- `fx3_libmpr`: `3,517,008` B | `fx6_libmpr`: `28,921,824` B
- `fx6_libinfra_ptp`: `152,520` B | `fx6_libnet_ether`: `175,376` B | `fx6_libveric_live`: `182,496` B
- `fx3_global_xdb`: `11,664` B | `fx6_global_xdb`: `1,792` B
- `fx3_str_en`: `165,740` B | `fx3_str_en_g`: `69,600` B | `fx6_str_en_1`: `118,208` B | `fx6_str_en_2`: `118,676` B

### 3. Four-Pillar Technical Architecture

1. **Pillar 1 — USB-C `UVC 1.5` / `UAC 2.0` Descriptor, Bandwidth & Stage-B Compatibility Contract**:
   - Builds and CRC32-verifies 44-byte `UVC 1.5` (`0x0150`, class `0x0E`) + `UAC 2.0` (`0x0200`, class `0x01`, `48 kHz` 2-ch `16/24-bit` LPCM) interface bundles for Sony VID `0x054C`.
   - Enforces physical USB link ceilings (`USB3_SUPERSPEED_5G` `3200.0 Mbps` usable vs `USB2_HIGHSPEED_480M` `320.0 Mbps` usable):
     - `4K30P_MJPEG` (`151.536 Mbps`) & `1080P60P_MJPEG` (`76.536 Mbps`) fit both USB 3.2 and USB 2.0.
     - `1080P60P_YUY2` (`1992.96 Mbps` with 24-bit UAC) passes USB 3.2 SuperSpeed but fails closed on USB 2.0 (`BLOCKED_USB2_HS_480M_BANDWIDTH_EXCEEDED`).
     - `4K30P_YUY2` (`3982.848 Mbps`) exceeds even USB 3.2 Gen 1 usable payload ceiling (`BLOCKED_USB3_SS_5G_BANDWIDTH_EXCEEDED`).
   - Enforces FX3 `v7.02` Stage-B hardware truth: blocks `DIRECT_FX3_NATIVE_UVC_GADGET` (`BLOCKED_FX3_NATIVE_UVC_GADGET_ABSENT`), routes via `HDMI_TO_UVC_BRIDGE` / `FX30_A7S3_UVC_DESCRIPTOR_SIM`, and blocks UVC during `S&Q Motion` or `16-bit HDMI RAW`.

2. **Pillar 2 — Wired `USB-LAN` (`CDC-NCM` / `RNDIS`) `SRT` & `RTMPS` TLS 1.3 Auditor with `P12` Wi-Fi-OFF**:
   - Audits `SRT_CALLER`, `SRT_LISTENER`, and `RTMPS_TLS13` strictly over wired USB-LAN NIC drivers (`CDC_NCM_RTL8153`, `CDC_NCM_AX88179`, `USB_RNDIS_WIRED`) with `wf12_00342260_risk == 0` and `hci_rf_tx_packets == 0`.
   - Any RF transport (`WIFI_WLAN0`, `WIFI_DIRECT_P2P`, `BT_PAN`, `MODEM_CELLULAR`) fails closed under `P12` (`BLOCKED_P12_RF_OFF_VIOLATION_00342260`).
   - Validates Sony FX3 streaming bitrate envelopes (`4K_5994P` `38.0 Mbps` through `720P_5994P`), blocks simultaneous internal 4K recording during `4K_5994P` streaming (`BLOCKED_4K5994_INTERNAL_4K_REC_EXCLUSION`), enforces `AES-128`/`AES-256` (`10..79`-char passphrase) and ARQ `20..1000 ms` (`>= 3x RTT`) for SRT, and enforces TLS `1.2/1.3` + root CA verification for RTMPS.

3. **Pillar 3 — `CRSDK` `PTP` / `PTP-IP` Translator & Stage-B Destructive Firmware-Update Flash-Opcode Firewall**:
   - Translates 8 Cinema Line `CRSDK` properties (`CINE_EI_LOG_MODE` `0xD243`/`0x02CF1443`, `BASE_ISO` `800/12800` `0xD244`, `EXPOSURE_INDEX` `0xD245`, `USER_3D_LUT` `0xD253`, `SHUTTER_ANGLE_X10` `0xD20D`, `IRIS_FNUMBER_X100` `0x5007`, `ND_FILTER_OD_X10` `0xD25A`, `REC_CONTROL` `0xD215`) across `USB_PTP` (`512 B` bulk packet alignment check) and `WIRED_PTPIP_15740`.
   - Clamps FX6 `P4` Electronic Variable ND (`0.3..2.1 OD`) deterministically to `Clear (0)` on `ILME-FX3` (`P4_ABSENT_ND_CLAMPED_CLEAR`).
   - **Destructive Flash-Opcode Firewall**: Fail-closed block on `0x9280` (Scalar DL write), `0x9282` (updater reconnect), `0x100C`/`0x100D` (MTP firmware upload), `0x9805`, `EVENT_REMOTE_REQUEST_START_BODY_UPDATE`, `EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON`, and firmware magic/target patterns (`\x89UFU`, `UDTRFIRM`, `BODYDATA.DAT`, `/dev/nflasha*`) with `emmc_mutation_bytes == 0` and `brick_risk_prevented == True`.

4. **Pillar 4 — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration Mutation Proof**:
   - Verifies both FX3 & FX6 `global.xdb` (`uxa\x07`) read-only, permits only volatile staging prefixes (`/tmp/`, `ram://`, `memory://`), and blocks `/mnt/sd/BODYDATA.DAT`, `/dev/nflasha15`, `/dev/cnflasha0`, `p2:/setting/Backup.bin`, `psd.bin`, `defdet.bin`, and `jiritsu` (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `firmware_flash_opcodes_blocked == True`, `persistent_emmc_writes_authorized == False`).

---

## 中文技术报告

### 一、 摘要与净室只读合规性

第 118 阶段基于第十三波全球实时情报同步，完成并集成了 `fx3-firmware-lab` 的 **第 23 个统一净室审计器**（[`usb_uvc_uac_srt_and_crsdk_ptp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/usb_uvc_uac_srt_and_crsdk_ptp_auditor.py)）。

- **零内置密钥 / 严格只读（`os.O_RDONLY` + `mmap.ACCESS_READ`）**：本地供体模式仅以 `os.O_RDONLY` 与 `mmap.ACCESS_READ` 按 ELF64 `.rodata`/`.dynstr` 区段读取 FX3 `v7.02` 与 FX6 `v6.01` 的 13 个核心二进制、`.uxc` 字符包与 `global.xdb`（`uxa\x07`），绝不产生任何持久化修改或 `.pyc` 缓存污染。
- **确定性净室回退（`CLEAN_ROOM_SYNTHETIC`）**：当设置 `FX3_FX6_FORCE_CLEAN_ROOM=1`、`--clean-room` 或本地供体缺失时，自动合成完整 ELF64 / `global.xdb` / `.uxc` 夹具并运行完全一致的四支柱验证流水线（热运行仅 `0.0021 秒`）。

### 二、 实测指标与双模式验证结果

- **本地供体全量测试**：`673` 项单元测试全部通过（耗时 `22.662s`），`audit-all --json` **`23/23` 全绿**（耗时 `9.522s`，Phase 118 报告 SHA-256：`b9a2fd3b0b6f3595be4bebbdde10528b3488362554dd1d0b3c55158317f8e722`）。
- **强制净室全量测试**：`673` 项单元测试全部通过（耗时 `12.309s`），`audit-all --json` **`23/23` 全绿**（耗时 `0.518s`，Phase 118 报告 SHA-256：`1c318c13526382194b5994fa12190c3385276b9d61ecab71bcd1b153d6071551`）。
- **Phase 118 专项单元测试**：`42` 项双模式测试全部通过（`0.539s`）；`scripts/run_all_lab_tests.py --clean-only` 检查 `CLEAN / ALL GREEN`（`0.05s`）。

### 三、 四支柱核心防砖与兼容性契约

1. **支柱 1 — USB-C `UVC 1.5 / UAC 2.0` 描述符、带宽预算与 FX6-on-FX3 Stage-B 契约**：精确验证 44 字节 `UVC 1.5 + UAC 2.0 (48kHz 2ch LPCM)` 描述符 CRC32；验证 `4K30p YUY2 (3982.8 Mbps)` 超出 USB 3.2 Gen 1 可用上限（`3200 Mbps`）而被拒绝，`1080p60p YUY2 (1992.2 Mbps)` 在 USB 3.2 放行并在 USB 2.0（`320 Mbps`）拦截；确认 FX3 `v7.02` 原生固件未开启 `[USB Streaming]`（拒绝 `DIRECT_FX3_NATIVE_UVC_GADGET`），统一走 `HDMI_TO_UVC_BRIDGE` 或 `FX30_A7S3_UVC_DESCRIPTOR_SIM`，并强制 `S&Q` 与 `16-bit HDMI RAW` 互斥隔离。
2. **支柱 2 — 有线 `USB-LAN` `SRT` / `RTMPS` 推流与 `P12` Wi-Fi-OFF 零风险门控**：强制使用有线网卡驱动（`CDC_NCM_RTL8153` / `CDC_NCM_AX88179` / `USB_RNDIS_WIRED`），对 `WIFI_WLAN0` / `BT_PAN` 等射频链路触发 `BLOCKED_P12_RF_OFF_VIOLATION_00342260` 拦截，确保 `wf12_00342260_risk == 0`；核验 `SRT` `AES-128/256`、`ARQ 20..1000 ms (≥3×RTT)`、`RTMPS TLS 1.3` 根证书校验及 `4K 59.94p @ 38 Mbps` 与机内 4K 录制的互斥约束。
3. **支柱 3 — `CRSDK` `PTP / PTP-IP` 属性转换与 Stage-B 破坏性固件刷写指令防火墙**：实现 `Cine EI`、`Base ISO 800/12800`、`User 3D-LUT`、`Shutter Angle`、`Iris`、`Rec Control` 向 Sony PTP (`0x054C` / `0x9201..0x9209` / `0xD2xx` 及 `512 B` 批量读对齐) 与 `PTP-IP (TCP/15740)` 的无损翻译；将 FX6 `P4` 电子可变 ND 在 FX3 上确定性钳位为 `Clear (0)`；同时在防火墙层**彻底封锁** `0x9280`（Scalar DL）、`0x9282`（Updater 重连）、`0x100C`/`0x100D`（`.DAT`/`UDTRFIRM`/`\x89UFU` 上传）、`EVENT_REMOTE_REQUEST_START_BODY_UPDATE` 及 `SET_FIRMWARE_UPDATE_MODE_ON`，杜绝宿主机 SDK 误触跨机型刷写变砖。
4. **支柱 4 — 易失性 RAM 暂存与持久 `eMMC` / 校准分区零修改证明**：只读校验双方 `global.xdb`，仅放行 `/tmp/`、`ram://`、`memory://` 暂存路径，硬阻断 `BODYDATA.DAT`、`/dev/nflasha15`、`/dev/cnflasha0`、`Backup.bin`、`psd.bin`、`defdet.bin` 与 `jiritsu`，保证 `emmc_mutation_bytes == 0` 与 `calibration_mutation_bytes == 0`。

---

## Owned 7-File Inventory / 本阶段七文件交付清单

1. [`reports/2026-11-14-global-sony-wave13-uvc-srt-crsdk-unbrick-intel/README.md`](../2026-11-14-global-sony-wave13-uvc-srt-crsdk-unbrick-intel/README.md) — Wave-13 live global web intelligence report (EN/ZH-CN, cited URLs)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/usb_uvc_uac_srt_and_crsdk_ptp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/usb_uvc_uac_srt_and_crsdk_ptp_auditor.py) — 23rd unified `fx3-firmware-lab` auditor
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) — Phase 118 symbol exports and `__all__`
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) — `audit-uvc-srt-crsdk` CLI subcommand & 23rd auditor in `run_audit_all`
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md) — Phase 118 documentation & CLI usage examples
6. [`outputs/fx3-firmware-lab/tests/test_usb_uvc_uac_srt_and_crsdk_ptp.py`](../../outputs/fx3-firmware-lab/tests/test_usb_uvc_uac_srt_and_crsdk_ptp.py) — 42 dual-mode unit tests
7. [`reports/2026-11-14-phase118-uvc-srt-crsdk-ptp-auditor/README.md`](README.md) — Phase 118 bilingual technical report
