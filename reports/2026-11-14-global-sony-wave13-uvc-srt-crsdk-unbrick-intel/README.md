# Wave-13 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十三波全球索尼固件 / 虚拟化 / 救砖与 UVC-UAC / SRT-RTMPS / CRSDK PTP 情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 118 — Wave-13 Global Live Web Intelligence Sync & 23rd Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified official Sony documentation, Sony Camera Remote SDK (`CRSDK` / `Camera Remote Command`) PTP/PTP-IP reverse-engineering, FX3 (`v6.00..v7.02`) / FX6 (`v5.00..v6.02`) / FX30 / A7S III `UVC 1.5 / UAC 2.0` & `SRT / RTMPS` streaming internals, and 2025–2026 ARM64 QEMU USB/FunctionFS virtualization & eMMC/UART unbrick research across four technical axes:
  1. **Sony Camera Remote SDK (`CRSDK` v2.00+) & `Camera Remote Command` PTP (`0x054C`) / PTP-IP (`0x92xx`, `0xD2xx`) Protocol + USB Firmware-Update Opcodes**
  2. **USB-C `UVC 1.5 / UAC 2.0` Streaming (`4K30p` / `1080p60p` MJPEG/YUV420/YUY2 + `48 kHz` 2ch LPCM) Bandwidth Physics & FX3 vs FX30/A7S3/FX6 Matrix**
  3. **Direct `SRT` (`Caller/Listener`, `PBKEYLEN` AES-128/256, ARQ Latency) & `RTMPS` TLS 1.3 Live Streaming (`FX3 v6.00..v7.02` vs `FX6 v6.00..v6.02`) + Wired `USB-LAN` `P12` Containment**
  4. **ARM64 Firmware RE, QEMU USB FunctionFS / `cmtp-responder` Virtualization & BootROM / eMMC ISP Brick-Recovery Advances**
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs and read-only (`os.O_RDONLY`) donor markers cited directly.

---

## English Technical Synthesis

### 1. Sony `Camera Remote SDK` (`CRSDK`) & `Camera Remote Command` PTP / PTP-IP Reverse Engineering

1. **Two-Layer Official Architecture (`CRSDK` vs `Camera Remote Command`)**:
   - **Camera Remote SDK (`CRSDK` v2.00.00+)**: Sony's C++ SDK (`libCr_Core` / `SCRSDK`) supporting Windows 11, macOS (`14.1+ / 15.1+ / 26.0+`), and Linux (`x86_64 / ARMv8 / ARMv7`) over **USB**, **Wired LAN (PTP/IP `TCP/15740`)**, and **Wi-Fi** (`v1.12+`). Supports both `ILME-FX3` and `ILME-FX6V / ILME-FX6T` (since `CRSDK v1.06`, FX6 `v3.00+`).
   - **Camera Remote Command (Publicly Released April 2024)**: Official protocol documentation detailing Sony's proprietary vendor extensions over ISO 15740 **PTP** across PTP-2 and PTP-3 generations, complementing long-standing community reverse engineering in `gphoto/libgphoto2`, `ma1co/Sony-PMCA-RE`, `alpha-fairy`, and `Indukto/sony-liveview-usb`.
   - Verified Official & Reference Links:
     - [Sony Pro Camera Remote SDK Overview](https://pro.sony/ue_US/products/software-camera-remote-sdk)
     - [Johnnybyzhang/CrSDK-API-Reference (Mirrored API Reference)](https://github.com/Johnnybyzhang/CrSDK-API-Reference)

2. **Sony Vendor PTP Extension Opcodes (`Vendor Extension ID: 0x00000011`)**:
   - **`0x9201` (`PTP_OC_SONY_SDIO_Connect`)**: 3-phase session/authentication handshake (`(1,0,0)`, `(2,0,0)`, `(3,0,0)`) interleaved with `0x9202` after `OpenSession` / `GetDeviceInfo` / `GetStorageIDs`.
   - **`0x9202` (`SDIO_GetExtDeviceInfo`)**: Capability negotiation returning Sony extension protocol version (e.g. `0xC8`) and supported vendor `0xD2xx` property/control codes.
   - **`0x9204` (`PTP_OC_SONY_GetDevicePropertyValue`) & `0x9206` (`PTP_OC_SONY_GetControlDeviceDesc`)**: Single-property value and descriptor queries.
   - **`0x9205` (`SDIO_SetExtDevicePropValue` / `SetControlDeviceA`)**: Property write (`DevicePropValue`) for `0x5007` (F-Number) and `0xD2xx` Cinema/Exposure properties. Unsupported writes on older bodies can `STALL` the USB Bulk OUT pipe until power cycle.
   - **`0x9207` (`PTP_OC_SONY_SDIO_ControlDevice` / `SetControlDeviceB`)**: Momentary action commands (`SDIControlCode`: half-press, shutter release, movie REC start/stop, manual focus drive).
   - **`0x9209` (`SDIO_GetAllExtDevicePropInfo`)**: Bulk poll returning all active `DevicePropDesc` containers. Because `0x9209` spans multiple 512-byte USB Bulk packets, clients **must read in 512-byte aligned chunks** to avoid USB stream desynchronization; interrupt endpoint `0x83` pushes 16-byte PTP event containers (`0xC203`, `0xC224` `PTP_EC_Sony_MovieRecOperationsResult`) and live view uses virtual handle `0xFFFFC002`.
   - **`0x9280` (`PTP_OC_SonyDiExtCmd_write`), `0x9281` (`PTP_OC_SonyDiExtCmd_read`), `0x9282` (`PTP_OC_SonyReqReconnect`)**: Documented in `ma1co/Sony-PMCA-RE` (`pmca/usb/sony.py`) from `libInfraMtpServer.so` for Sony external commands (`DevInfoSender`, `ScalarExtCmdPlugIn_NotifyScalarDlmode = (5, 2)`, `NetworkServiceInfo`, updater reconnect `0x054C:0x033A / 0x03E2`).
   - Verified Community References:
     - [gphoto/libgphoto2 `camlibs/ptp2/ptp.h`](https://raw.githubusercontent.com/gphoto/libgphoto2/master/camlibs/ptp2/ptp.h)
     - [ma1co/Sony-PMCA-RE `pmca/usb/sony.py`](https://raw.githubusercontent.com/ma1co/Sony-PMCA-RE/master/pmca/usb/sony.py)
     - [Indukto/sony-liveview-usb](https://github.com/Indukto/sony-liveview-usb)
     - [alpha-fairy Camera Reverse Engineering Notes](https://github.com/oscar-dev/alpha-fairy)

3. **`CrDevicePropertyCode` Cinema Line Mapping & Remote Firmware-Update Brick Hazard**:
   - **Cinema Line Properties**: `CrDeviceProperty_BaseISOSwitchEI`, `CrDeviceProperty_GainBaseIsoSensitivity` (`800` / `12800`), `CrDeviceProperty_ExposureIndex`, `CrDeviceProperty_FNumber` (`0x0100` / `0x5007`), `CrDeviceProperty_ShutterAngle`, `CrDeviceProperty_SelectLUT` (`S709`/`R709`/`S-Log3`/`User1..16`), and `CrDeviceProperty_NDFilter` / `NDFilterMode` / `NDFilterOpticalDensityValue` (`0.3..2.1` OD on FX6 vs hardware-absent on FX3 -> **must clamp to `Clear` under `P4`**).
   - **Remote Firmware Update Hazard (`CRSDK v1.13.00+`)**: Sony added remote firmware update orchestration (`op_remote_firmware_update.html` in CRSDK API Reference) backed in `appFw.so` by `EVENT_REMOTE_REQUEST_START_BODY_UPDATE`, `EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON`, `EVENT_REMOTE_REQUEST_FIRMWARE_UPDATE_CHECK`, and `FIRMWARE_UPDATE_STATUS_ACCEPTING_DATA_UPLOAD`. On a **Stage-B hybrid FX6-on-FX3 environment**, allowing an attached host SDK or MTP client to invoke firmware-update opcodes (`0x9280` Scalar DL mode, `0x9282` updater reconnect, `EVENT_REMOTE_REQUEST_START_BODY_UPDATE`, or `SendObjectInfo`/`SendObject` carrying `.DAT`/`UDTRFIRM`/`\x89UFU`) risks triggering an unverified cross-model flash write (`5L+6S` brick!). Stage-B **must** interpose a hard **PTP Flash-Opcode Firewall** denying all firmware-update transitions while preserving read/control `0x9201..0x9209` telemetry.

---

### 2. USB-C `UVC 1.5 / UAC 2.0` Streaming Specs & Cross-Body Reality (`FX3` vs `FX30` vs `A7S III` vs `FX6`)

1. **Official Model Support Asymmetry (Verified in Sony Help Guides & Donor Binaries)**:
   - **ILME-FX3 (`Ver. 7.02`, released 2026-03-17) & ILME-FX3A (`Ver. 2.02`)**: Do **NOT** expose native `[USB Streaming]` (`UVC/UAC` over USB-C) in `[USB Connection Mode]` (only `MassStorage(MSC)`, `MTP`, `Remote Shooting`). Although shared `appFw.so` carries `VAL_HAITA_file_format_xavc_hs_streaming_restriction_UVC_FORMAT_30p` and `INFRA_NOTIFY_USB_STREAMING_STATE_CHANGED`, HAITA disables the native gadget. True 4K UVC output on FX3 uses an external **HDMI Type-A -> UVC capture adapter** (or Imaging Edge Webcam over `Remote Shooting` at lower res).
   - **ILME-FX30 & ILCE-7SM3 (`Ver. 5.00+`)**: Native driver-free `UVC / UAC` over USB-C:
     - **A7S III (`Ver. 5.00+`)**: `4K (3840x2160)` at `30p/25p/15p/12.5p` (`MJPEG` or `YUV420`), `1080p` at `60p/50p/30p/25p` (`MJPEG` or `YUV420`), `720p` at `30p/25p` (`MJPEG` only).
     - **FX30**: Capped at `4K 15p (14.99p) / 12.5p` over USB-C; `1080p` up to `60p/50p`.
     - **Audio (`UAC 2.0` / `1.0`)**: `LPCM 2ch, 48 kHz, 16-bit` (`1.536 Mbps`) or `24-bit` (`2.304 Mbps`).
     - **Link Speed Gate**: `SuperSpeed USB 3.2 (5 Gbps)` required above `720p`; USB `2.0 (480 Mbps)` clamps to `720p30p MJPEG`.
   - **Uncompressed `YUY2` (16 bpp) Bandwidth Physics**:
     - `3840x2160 @ 30p YUY2` = `3,981.312 Mbps` (+ `1.536 Mbps` UAC = `3,982.848 Mbps`), exceeding both USB 2.0 (`320 Mbps` usable) and USB 3.2 Gen 1 UVC practical bulk/isoc ceiling (`3,200 Mbps`), explaining why Sony cameras use `MJPEG` (`~150 Mbps`) or `YUV420 NV12` at `4K30p`!
     - `1920x1080 @ 60p YUY2` = `1,990.656 Mbps` (+ UAC = `1,992.192 Mbps`), which fits USB 3.2 Gen 1 (`5 Gbps`) but exceeds USB 2.0 (`480 Mbps`).
   - Verified Official References:
     - [Sony ILME-FX3 Firmware Ver. 7.02 Release & USB Connection Mode Help Guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885432.html)
     - [Sony ILME-FX30 USB Streaming Help Guide](https://helpguide.sony.net/ilc/2220/v1/en/contents/TP1000885442.html)
     - [Sony ILCE-7SM3 Ver. 5.00 USB Streaming Help Guide](https://helpguide.sony.net/ilc/2010/v1/en/contents/TP1000885442.html)

---

### 3. Direct `SRT` (`AES-128/256`, ARQ) & `RTMPS` Network Streaming (`FX3 v6.00..v7.02` vs `FX6 v6.00..v6.02`)

1. **FX3 Network Streaming Matrix (`Ver. 6.00 .. Ver. 7.02`)**:
   - **Supported Protocols**: **`SRT`** (`Caller` / `Listener`, `PBKEYLEN` **AES-128** & **AES-256** encryption via `10..79`-char passphrase, ARQ latency **`20..1000 ms`**), **`RTMP`**, and **`RTMPS`** (TLS 1.2 / 1.3 root CA validation).
   - **Exact Sony Bitrate & Resolution Envelope (`[Network Streaming] -> [Output Img. Quality Set]`)**:
     - **4K (`2160p`)**: `59.94p / 50p` fixed **`38 Mbps`**; `29.97p / 25p` **`13–38 Mbps`** (default `34 Mbps`).
     - **2K (`1440p`)**: `59.94p / 50p` **`9–38 Mbps`**; `29.97p / 25p` **`6–38 Mbps`**.
     - **HD (`1080p`)**: `59.94p / 50p` **`4.5–27 Mbps`**; `29.97p / 25p` **`3–18 Mbps`**.
     - **HD (`720p`)**: `59.94p / 50p` **`2.3–13.5 Mbps`**; `29.97p / 25p` **`1.5–9 Mbps`**.
   - **Recording Exclusion**: When `[Movie Rec During Streaming]` is enabled while streaming `4K` or `2K` at `59.94p/50p`, internal `[File Format]` cannot be set to 4K (`CXD90057` dual-encode ceiling).
   - **ILME-FX6 (`Ver. 6.00 / 6.01 / 6.02`) Asymmetry**: Official FX6 firmware (`v6.01` Sept 2026, `v6.02` Nov 2026) adds BIG6, Blackmagic RAW over HDMI, and Monitor & Control v2.5+ updates, but does **NOT** expose native SRT/RTMP/RTMPS streaming in camera UI (despite internal `BKID_APP_SETTING_SRT_SETTINGS1_*` / `DefInfraVericLiveStreaming` strings shared in `appFw.so`).
   - **Stage-B `P12` Wi-Fi-OFF Enforcement**: Because `P12` isolates Wi-Fi/BT RF (`wf12_00342260_risk == 0`), Stage-B permits SRT/RTMPS **strictly over Wired `USB-LAN` (`CDC-NCM` `RTL8153` / `AX88179` or wired USB `RNDIS` host link)** and hard-blocks `WIFI_WLAN0` / `BT_PAN`.
   - Verified Official References:
     - [Sony ILME-FX3 Network Streaming Help Guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1001598456.html)
     - [Sony ILME-FX6 Firmware Ver. 6.00 / 6.01 / 6.02 Release Notes](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx6v/software/00263653)

---

### 4. ARM64 Firmware RE, QEMU USB FunctionFS Virtualization & eMMC/UART Unbrick Research (2025–2026)

| Project / 项目 | Focus / 技术方向 | Key Verified Technical Findings / 核心进展 | Canonical URL |
| :--- | :--- | :--- | :--- |
| `DavidBuchanan314/ILCE-7M4-RE` | `BIONZ XR` (`CXD90057`) BootROM & Fastboot | BootROM serial boot via accessory RX (`uart_boot` RP2040), bare-metal USB fastboot (`payloads/fastboot`) for eMMC partition dump/flash, AES-XTS partition crypto (`parse_emmc_boot0.py`). | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `dino2048/zv-e10-toolkit` | Dual-Route Backup & Unbrick | USB service-mode Linux shell + RP2040 BootROM serial injection fastboot payload + watchdog disarm for full eMMC recovery preserving `boot0`/`boot1`. | https://github.com/dino2048/zv-e10-toolkit |
| `xyzhangxin/sony-a6700-powerful` | A6700 (`v2.00`) BootROM/Fastboot | RP2040 Pico + 24-pin USB-C test board injecting temporary payload into RAM for full eMMC backup before risky modifications. | https://github.com/xyzhangxin/sony-a6700-powerful |
| `OlliV/fx30_fw` | `ILME-FX30` (`v6.01`) Static Analysis | Unpacks `firmware.tar` (`nflasha15` ext4 `/usr`, `nflasha7` rootfs, `nflasha5` WBI2, `nflasha3/8` coprocessor FAT), maps `PRODUCT_MODEL_LAX` in `appFw.so` & `adjstctl.elf` Jiritsu commands. | https://github.com/OlliV/fx30_fw |
| `leogenot/sony-a7iv-feature-research` | A7 IV (`6.02`) vs FX3 (`7.02`) RE | AArch64 `libSysDef.so` (`MIRA_CETUS2`), `BK4` NVRAM DB (`bk4.py`), `BKID_APP_*` (`0x02cfXXXX`), read-only `GET_FILE2` extraction, Open-Gate/X-OCN gating. | https://github.com/leogenot/sony-a7iv-feature-research |
| `chocotan/a7c2-re` & `a7c2-qemu` | `ILCE-7CM2` ARM64 QEMU Model | QEMU `virt` + DTB patches + `ramfb` + software GPE raster/sprite (`gpe-raster.c`, `gpe-sprite.c`) + Sony LZ77 (`sony-lz77.c`) booting camera menus. | https://github.com/chocotan/a7c2-re |
| `cokeenet/zve10-qemu` | `CXD90045` QEMU & Brick Rescue | Stage2 eMMC fastboot (`18d1:4ee0`), real brick rescue via 1-byte `ld.so.preload` repair on `nflasha10` vfat, `WDT_SET_STOP` watchdog disarm. | https://github.com/cokeenet/zve10-qemu |
| Linux `FunctionFS` / `cmtp-responder` | Userspace USB PTP/MTP Gadgets | Kernel `/dev/usb-ffs/` + ConfigFS endpoints (`dwc3`/`dummy_hcd`) enabling isolated PTP/UVC protocol testing inside ARM64 QEMU without physical camera flash risk. | https://www.collabora.com/news-and-blog/blog/2018/05/16/writing-a-mtp-responder-for-linux/ |
| QEMU `eMMC` Device Docs | Multi-Partition eMMC Emulation | SDHCI-attached `boot0`, `boot1`, `RPMB`, and `UDA` alignment rules validating zero-write eMMC isolation in CI. | https://www.qemu.org/docs/master/system/devices/emmc.html |

---

## 简体中文技术摘要

### 1. 索尼 `Camera Remote SDK` (`CRSDK`) 与 `PTP / PTP-IP` (`0x92xx`, `0xD2xx`) 及刷机操作码防火墙

- **协议分层**：高层 C++ 库 `CRSDK`（`libCr_Core`）与 2024 年 4 月公开的底层 `Camera Remote Command`（ISO 15740 PTP 索尼厂商扩展 `Vendor ID 0x11`）。
- **核心索尼 PTP 扩展操作码**：
  - `0x9201` (`SDIO_Connect`) 三阶段握手 `(1,0,0)/(2,0,0)/(3,0,0)`；`0x9202` (`SDIO_GetExtDeviceInfo`) 查询能力集与 `0xC8` 版本；`0x9205` (`SDIO_SetExtDevicePropValue`) 写入属性；`0x9207` (`SDIO_ControlDevice`) 触发快门/录制等瞬态动作；`0x9209` (`SDIO_GetAllExtDevicePropInfo`) 批量拉取属性（USB Bulk 必须按 **512 字节对齐**读取以免包失步，同时持续排空中断端点 `0x83` 的 `0xC203`/`0xC224` 事件）。
  - `0x9280` / `0x9281` / `0x9282`（`SonyDiExtCmd_write/read` 与 `ReqReconnect`，见 `Sony-PMCA-RE` 与 `libInfraMtpServer.so`）用于外部扩展指令与重连进入刷机模式（`0x054C:0x033A/0x03E2`）。
- **`CrDeviceProperty` 电影机属性映射与 Stage-B 刷机防火墙**：
  - 将 `Cine EI`（`0x02CF1443`）、`Base ISO 800/12800`、`User 3D-LUT`（`0x02CF1453`）、`Shutter Angle`（`0x02CF1704`）、`Iris` 映射到 PTP 层；对 FX3 缺失电子无级 ND 的 `P4` 约束，将任何 `CRSDK NDFilter` 写入强制钳位至 **`Clear (0.0 OD)`**。
  - **致命风险拦截**：`CRSDK v1.13.00+` 新增远程固件升级序列，FX6/FX3 `appFw.so` 中亦存在 `EVENT_REMOTE_REQUEST_START_BODY_UPDATE`、`EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON` 与 `FIRMWARE_UPDATE_STATUS_ACCEPTING_DATA_UPLOAD`。Stage-B 混合系统**必须硬拦截所有 PTP/USB 刷机与 OTA 上传操作码**（包括 `0x9280` Scalar DL 模式、`0x9282` Updater 重连及携带 `.DAT`/`UDTRFIRM`/`\x89UFU` 的 `SendObject`），彻底杜绝外部主机 SDK 误触发跨机型变砖。

### 2. USB-C `UVC 1.5 / UAC 2.0` 带宽约束与跨机型真相

- **官方机型差异**：实测与官方文档均证实 **ILME-FX3（`Ver. 7.02`）不支持机身原生 USB-C `UVC/UAC` 推流**（仅 FX30 上限 `4K 15p` / `1080p60p` 与 A7S III `v5.00+` 支持 `4K 30p` / `1080p60p` `MJPEG`/`YUV420` + `48kHz 2ch 16-bit LPCM`）。
- **带宽物理边界**：`4K 30p YUY2 (16 bpp)` 需 **`3,981.312 Mbps`**（超出 USB 2.0 `320 Mbps` 十二倍以上，甚至超过 USB 3.2 `5 Gbps` 实际 UVC 净载荷上限 `3,200 Mbps`），因此 `4K30p` 必须采用 `MJPEG`（`~150 Mbps`）或 `YUV420`；`1080p60p YUY2` 需 `1,990.656 Mbps`（仅 SuperSpeed 可承载，USB 2.0 必须回退 `MJPEG`）。FX3 宿主下 Stage-B 必须以只读描述符仿真 + HDMI-to-UVC 桥接契约安全对齐。

### 3. `SRT` (`AES-128/256`, ARQ) 与 `RTMPS` (`TLS 1.3`) 网络推流及 `P12` 有线隔离

- **FX3 (`v6.00..v7.02`) vs FX6 (`v6.00..v6.02`)**：FX3 原生支持 **SRT**（`Caller/Listener`、`AES-128/256`、`20..1000 ms` ARQ、`4K 59.94p @ 38 Mbps` / `4K 29.97p @ 13–38 Mbps` / `1080p60p @ 4.5–27 Mbps`）与 **RTMP/RTMPS**，且 `4K/2K 59.94p` 推流时禁止机内同时 4K 录制；FX6 `v6.02` 虽内部共用 `appFw.so` SRT 符号但官方菜单未开放。
- **Stage-B `P12` 无线隔离铁律**：在 `P12` 飞行隔离下，`SRT` 与 `RTMPS` 严格绑定至**有线 `USB-LAN`（`CDC-NCM RTL8153/AX88179` 或有线 `RNDIS`）**，硬拦截一切 `WIFI_WLAN0` / `BT_PAN` 发包，确保 **`wf12_00342260_risk == 0`**。

### 4. ARM64 固件逆向、QEMU USB FunctionFS 仿真与 eMMC 救砖前沿

- 汇总 `DavidBuchanan314/ILCE-7M4-RE`、`dino2048/zv-e10-toolkit`、`OlliV/fx30_fw`、`leogenot/sony-a7iv-feature-research`、`chocotan/a7c2-qemu`、`cokeenet/zve10-qemu` 与 Linux `FunctionFS` / `cmtp-responder` / QEMU `eMMC` 最新公开成果，为本实验室“严守 `os.O_RDONLY` 只读审计 + Stage-B `eMMC` 零写入防火墙”提供持续外部验证支撑。
