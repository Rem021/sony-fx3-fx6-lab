# Wave-14 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十四波全球索尼固件 / 虚拟化 / 救砖与 MXF-MP4 / PTPv2 / TSL UMD v5.0 情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 122 — Wave-14 Global Live Web Intelligence Sync & 24th Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified public technical references covering:
  1. **Sony FX6 `XAVC MXF OP1a` (`SMPTE ST 377-1 / RDD-09 / RDD-32 / ST 436 / KLV RDD-18`) vs FX3 `MP4` (`ISO-BMFF` + `rtmd` + `SPVC`) Container & Metadata Parity**
  2. **`SMPTE ST 2059-2` (`IEEE 1588-2008 PTPv2`) Sub-Microsecond Sync vs Sony FX6/FX3 `LTC` (`SMPTE 12M`) & `PTP-IP` Architectural Separation**
  3. **Broadcast `TSL UMD v5.0` (UDP/TCP ports `40003` / `5727` / `8900`) Tally & Dynamic Camera UMD Label Bridging onto FX3/FX6**
  4. **2025–2026 Sony `CXD90057` ARM64 Firmware RE, QEMU Virtualization & BootROM / eMMC Unbrick Advances**
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs and read-only (`os.O_RDONLY`) donor markers cited directly.

---

## English Technical Synthesis

### 1. Sony FX6 `XAVC MXF OP1a` vs FX3 `MP4` (`ISO-BMFF` / `rtmd`) Container & Metadata Architecture

1. **Container Wrapper & Elementary Stream Parity**:
   - **Sony FX6 (`ILME-FX6` v6.01)**: Encapsulates `XAVC-I` (H.264 High 4:2:2 Intra `AVC480_*_H422IP`) and `XAVC-L` in **MXF Operational Pattern 1a (OP1a)** frame-wrapped Generic Containers per **SMPTE RDD 32** (*XAVC MXF Mapping and Operating Points*) and **SMPTE ST 377-1 / RDD-09**. Per-frame acquisition metadata is transported via **SMPTE RDD 18** KLV packets carried inside **SMPTE ST 436** ANC data tracks, accompanied by `XDROOT/Clip/*M01.XML` (`NonRealTimeMeta`), `Take` `.SMIL`/`.XML`, and `MEDIAPRO.XML`.
   - **Sony FX3 (`ILME-FX3` v7.02)**: Encapsulates `XAVC S-I` (using the identical `CXD90057` High422Intra elementary encoder verified in `libmpr.so`), `XAVC S`, and `XAVC HS` in **MP4 (`ISO-BMFF` `mp42`/`iso2`/`XAVC`)** under `M4ROOT/CLIP`, carrying per-frame **SMPTE RDD 18** acquisition metadata in a dedicated **`rtmd` (`0x646D7472`, Timed Metadata Media Handler)** track plus C2PA / `SPVC` (`sony.private_cert.v1`) JUMBF integrity boxes and `*M01.XML` sidecars.
   - **Verified Official & Tool References**:
     - Sony Pro XAVC / MXF & NonRealTimeMeta ecosystem (`pro.sony`, `helpguide.sony.net`)
     - [ExifTool — Embedded `rtmd` & Sony MP4/MXF Tag Extraction (`-ee`)](https://exiftool.org/)
     - [SMPTE RDD 18 Acquisition Metadata Sets (SMPTE Standards)](https://www.smpte.org/)

2. **Key Cross-Container Metadata Elements (`ExposureIndex`, `CaptureGammaEquation`, `UMID`)**:
   - **`ExposureIndex` (`ExposureIndexOfPhotoMeter`)**: Registered under SMPTE UL `urn:smpte:ul:060e2b34.0101010e.04200103.010c0000`. In **Cine EI** / **Cine EI Quick**, sensor gain locks to Base ISO (`800` or `12800`) while the EI offset is stamped via FX6 `libmpr.so` (`setMetaData_ExposureIndexRDD18`) and FX3 `libmpr.so` (`XavcsMovieWriter::SetRealTimeMetaSampleInfo` + `NonRealTimeMeta v2.20`) so DaVinci Resolve / Catalyst Browse apply identical exposure offsets.
   - **`CaptureGammaEquation` (Tag `0x3210`) & `CaptureColorPrimaries`**: Encoded as 16-byte SMPTE ULs (e.g., `060E2B34040101010401010101020000` for Rec.709, plus Sony S-Log3 / S-Gamut3.Cine ULs) via FX6 `setMetaData_CaptureGammaRDD18` and FX3 `defStruct2sidb_CaptureGammaEquation`. Both bodies resolve `.cube` 3D LUT monitoring paths (`GetCubeFilePathForMXF` vs `GetCubeFilePath`).
   - **`UMID` (32-Byte Unique Material Identifier, SMPTE ST 330)**: Prefix `060A2B340101010501010D4313000000...` generated in shared `mpr::UMID::CreateBasicUMID` across both FX6 and FX3. Lossless container re-wrapping (`MXF OP1a` <-> `MP4 ISO-BMFF`) **preserves** the 32-byte source UMID in `packageid` / `TargetMaterial[@umidRef]`, whereas transcoding generates a new UMID.
   - **Inspection Utilities**: **MediaInfo (v24.01+)** parses both MXF ST 436 RDD-18 and MP4 `rtmd` (`CaptureGammaEquation_FirstFrame`, `ISOSensitivity_FirstFrame`); **ExifTool (`-ee`)**, **`SLogMetaRaw`**, and **`xavc_rtmd2srt`** extract per-frame `0x8000` (`FNumber`), `0x8106` (`FrameRate`), `0x8109` (`ExposureTime`), `0x810B` (`ISO`), `0xE303` (`WhiteBalance`), `0xE43B` (`PitchRollYaw`), and `0xE44B` (`Accelerometer`).

---

### 2. `SMPTE ST 2059-2` (`PTPv2`) vs Multi-Terminal `LTC` & `PTP-IP` Reality

1. **Critical Protocol Distinction (`PTPv2` vs `PTP-IP`)**:
   - **SMPTE ST 2059-2** is the broadcast profile of **IEEE 1588-2008 Precision Time Protocol (`PTPv2`)** for sub-microsecond TAI clock distribution over Ethernet/IP (used in SMPTE ST 2110 plants).
   - **Sony `PTP-IP` (`TCP/15740`)** in `libInfraPtpControl.so` (`PTPT_init_ip_remote`) and `CRSDK` is **Picture Transfer Protocol over IP** (ISO 15740) for remote camera control and file transfer — it is **not** IEEE 1588 `PTPv2` timing synchronization.
2. **FX6 & FX3 Hardware Synchronization Truth**:
   - Neither **ILME-FX6 (`v6.01/v6.02`)** nor **ILME-FX3 (`v7.02`)** has a **BNC Genlock (Reference In)** port or native hardware IEEE 1588 PHY timestamping (unlike FX9, FR7, BURANO, VENICE, or HDC-5500R).
   - **Verified Studio Integration Pipeline**:
     1. A PTPv2-locked Sync Pulse Generator (**Leader LT4670**, **Ross SPG9000**, or **Brainstorm DXD-8**) locks to the facility **SMPTE ST 2059-2** Grandmaster over wired Ethernet (`Domain 127`, `ST 2059-1` TAI-to-UTC epoch alignment with `37 s` leap-second offset) and emits phase-locked **SMPTE 12M LTC**.
     2. LTC feeds the FX6 bi-directional **BNC `TC IN/OUT`** (`Mode: Preset`, `Run: Free Run`, `EXT-LK`) or FX3 Multi-Port **`VMC-BNCM1` (`LTC IN`, Pin 3)** (`INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS` / `EXT_TC_LOCK_STATUS_LOCK`) for frame-accurate clip timecode (`< 0.5 ms` phase error).
     3. Downstream baseband switcher input frame syncs or **ST 2110 IP gateways** (e.g., AJA `IP25-R` / `IPT-10G2-SDI`) align asynchronous SDI/HDMI video to house PTPv2 (~1 frame buffering).
     4. Under **Stage-B `P12` Wi-Fi-OFF**, any software `PTPv2` follower/telemetry daemon on the host/bridge MUST bind exclusively to **wired `USB-LAN` (`CDC_NCM_RTL8153` / `CDC_NCM_AX88179` / `USB_RNDIS_WIRED`)** with `wf12_00342260_risk == 0`, while **`VMC-BNCM1` MUST remain disconnected during `H0` / `uart_boot` (Pins 7/8/9 safety guard)**.

---

### 3. Studio Broadcast `TSL UMD v5.0` Tally & Dynamic Camera UMD Label Protocol

1. **Official TSL UMD v5.0 Binary Wire Format**:
   - Reference: [TSL Products — UMD Protocol Specification (`tsl-umd-protocol.pdf`)](https://www.tslproducts.com/media/1959/tsl-umd-protocol.pdf)
   - All 16-bit integers are **little-endian**.
   - **Packet Layout**: `PBC (uint16)` | `VER (uint8 = 0x00)` | `FLAGS (uint8)` | `SCREEN (uint16)` | `<DMSG>...`
     - `FLAGS` Bit 0: `0 = ASCII`, `1 = UTF-16LE`; Bit 1: `0 = DMSG`, `1 = SCONTROL`.
     - `<DMSG>`: `INDEX (uint16, 0..65534 or 0xFFFF broadcast)` | `CONTROL (uint16)` | `LENGTH (uint16)` | `TEXT (variable)`.
     - `CONTROL` bitfield: Bits `0..1` = RH Tally, Bits `2..3` = Text Tally, Bits `4..5` = LH Tally (`0=Off, 1=Red, 2=Green, 3=Amber`), Bits `6..7` = Brightness (`0..3`), Bit 15 = `0` (`LENGTH`/`TEXT` follows).
   - **Transport & Ports**:
     - **UDP** (raw frames `<= 2048 bytes`): e.g. port **`40003`** (Softron Multicam Logger default), **`8900`** (Sony FR7 / BRC-AM7 / HDCU native TSL UMD v5.0 default, `tsl-umd-v5`), or `4492`.
     - **TCP** (byte-stream with `DLE`/`STX` framing `0xFE 0x02` and `0xFE -> 0xFE 0xFE` byte-stuffing; `PBC`/`LENGTH` exclude stuffing bytes): e.g. port **`5727`** / **`5728`** (Ross Carbonite/Ultrix/TallyView).
     - Open-source tooling: `tsl-umd-v5` (Node.js), `go-tsl-v5` (Go), `tslumd` (Python), `tsl_umd` (Rust), Bitfocus Companion `TSL Products - UMD protocol`.

2. **Sony Switcher & FX3/FX6 Physical Tally Translation**:
   - Sony **MVS/XVS** switchers emit Sony Serial Tally (RS-422 / TCP `8000`) bridged to TSL UMD v5.0 via **Sony `PWS-110NM1` (`PWSL-NM17`)**, TSL TallyMan, Riedel *hi*, EVS Cerebrum, Cyanview RIO/CI0, Skaarhoj Blue Pill, or Bitfocus Companion (while Sony **M2L-X** outputs TSL UMD v5.0 natively).
   - **FX6 vs FX3 Tally Hardware Asymmetry**:
     - FX6 `appFw.so` exposes `BKID_APP_SETTING_FRONT_TALLY`, `BKID_APP_SETTING_REAR_TALLY`, `BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS`, `BKID_APP_SETTING_TALLY_CONTROL`, and **`BKID_APP_SETTING_G_TALLY_LAMP`** (Green Tally).
     - FX3 `appFw.so` (`sequence_set_tally_status`) drives **single-color Red** Front + Top/Rear REC Tally LEDs only (no Green hardware LED).
     - **Stage-B P12-Safe Translator Contract**:
       - **`Red (1, PGM On-Air)`**: FX3 Front + Top/Rear Red Tally LEDs `ON` + `GPE0` OSD `RED` border (`#FF1E1E`).
       - **`Green (2, PVW Preview)`**: FX3 physical Red LEDs strictly **`OFF`** (prevents false on-air Red tally confusion!) + `GPE0` OSD **`GREEN` preview border (`#00E054`)**.
       - **`Amber (3, ISO/Aux)`**: Physical Red LEDs `OFF` + `GPE0` OSD `AMBER` border (`#FFB000`); **`Off (0)`**: LEDs `OFF` + OSD border `NONE`.
       - **`16-char` UMD Label**: Truncated/sanitized to `<= 16` printable characters (`CSI`/control-byte stripped) for `GPE0` OSD camera-ID badge (`e.g., CAM-A1 FX3-STAGEB`).
       - **`P12` Wi-Fi-OFF**: TSL UMD UDP/TCP listener bound strictly to wired `USB-LAN` (`CDC-NCM` / `RNDIS`), `wf12_00342260_risk == 0`.

---

### 4. 2025–2026 Sony Firmware RE, ARM64 QEMU Virtualization & BootROM / eMMC Unbrick Advances

| Project / 项目 | Focus / 方向 | Verified Technical Findings / 核心技术发现 | Canonical URL |
| :--- | :--- | :--- | :--- |
| `Rem021/sony-fx3-fx6-lab` | FX3 `7.02` & FX6 `6.01` QEMU Lab | Multi-agent Apple Silicon QEMU emulation reaching 180s FX6-on-FX3 media-start milestone with web UI & clean-room auditors. | https://github.com/Rem021/sony-fx3-fx6-lab |
| `DavidBuchanan314/ILCE-7M4-RE` | `CXD90057` BootROM & Fastboot | 48 KB BootROM has zero USB stack; RP2040 `uart_boot` (`48000 -> 115200` baud) injects Sony-signed `fastboot.bin` to `0x92028000` (`18d1:4ee0`, `oem partition`, `oem dumpbrom`, `boot0`-derived AES-XTS, `verifyKey()` patch). | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `Erlla/sony-a7m4-custom-firmware` | `CXD90057` eMMC Sparse Flashing | Non-fastboot & sparse eMMC flashing notes; highlights physical NOR / EXBL boundary outside eMMC backup scope. | https://github.com/Erlla/sony-a7m4-custom-firmware |
| `DavidBuchanan314/Sony-ILCE-7M4-Linux` | `CXD90057` Linux Kernel | Kernel `4.9.337` research on the shared `CXD90057` ("Mira") 4× Cortex-A35 + TOPPERS/FMP RTOS + SA DSP platform. | https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux |
| `leogenot/sony-a7iv-feature-research` | Shared `CXD90057` App Classes | Maps 27 product classes (`ALCIN_UUD` FX3 vs `PRODUCT_MODEL_OT_UUD` A7S III), `fwtool.py`, `Sony-PMCA-RE` properties & Cine EI gating. | https://github.com/leogenot/sony-a7iv-feature-research |
| `YuuLuo/a7c2-service-preload` | Service Auth & `ld.so.preload` | Documents A7C II service authentication, Jiritsu path resolution, and `ld.so.preload` runtime injection. | https://github.com/YuuLuo/a7c2-service-preload |
| `xyzhangxin/sony-a6700-powerful` | A6700 (`v2.00`) RP2040 Recovery | RP2040 Pico + Type-C CC wiring guide for RAM Fastboot & full eMMC backup before modification. | https://github.com/xyzhangxin/sony-a6700-powerful |
| `dino2048/zv-e10-toolkit` | ZV-E10 24 KiB BootROM & Recovery | 16-partition eMMC backup/restore excluding `boot0`/`boot1` + two-stage fastboot recovery. | https://github.com/dino2048/zv-e10-toolkit |
| `cokeenet/zve10-qemu` & `ivica00/sony-a6400-research` | ARMv7/ARM64 QEMU Harnesses | Offline QEMU boot patches, UART boot notes, and clean-room firmware memory-mapping harnesses. | https://github.com/cokeenet/zve10-qemu |
| `ma1co/Sony-PMCA-RE` | Service Shell & Region Notes | Tracks FX3A `serviceshell` auth timeouts (`#477/#524/#715`) & Japanese J1 FX3 `v6.2` NTSC/PAL lock (`#714`), plus FX3 `v6.00/6.02` & FX6 `v5.02->6.00` brick reports. | https://github.com/ma1co/Sony-PMCA-RE |

---

## 简体中文技术摘要

### 一、 FX6 `XAVC MXF OP1a` 与 FX3 `MP4` (`ISO-BMFF` / `rtmd`) 容器及元数据互转契约

1. **底层编码一致、外层封装分叉**：FX6（`v6.01`）通过 `libXavcMxf`（`MuxMxfFnlzPrm_GetVideoCompression`、`GetCubeFilePathForMXF`、`setMetaData_ExposureIndexRDD18`、`setMetaData_CaptureGammaRDD18`）生成符合 **SMPTE ST 377-1 / RDD-09 / RDD-32** 的 **MXF OP1a**（随 **ST 436** 轨携带 **RDD-18** KLV 帧级元数据）；FX3（`v7.02`）共享同一 `CXD90057` `AVC480_*_H422IP`（`XAVC-I` / `XAVC S-I`）核心编码器，但经 `libXavcMp4`（`GetCubeFilePath`、`SetRealTimeMetaSampleInfo`、`defStruct2sidb_CaptureGammaEquation`、`SPVC` JUMBF 签名盒）封装为 **MP4 (`ISO-BMFF`)** 与 **`rtmd` (`0x646D7472`)** 定时元数据轨。
2. **三大无损互转锚点**：
   - **32 字节 `SMPTE UMID`**（`mpr::UMID::CreateBasicUMID`）：无损重封装（Re-wrap）必须原样保留源 32 字节 UMID 及 `*M01.XML` `<TargetMaterial umidRef="..."/>` 关联，禁止触发重编码生成新 UMID；
   - **`ExposureIndex` 与 `CaptureGammaEquation`（Tag `0x3210`）**：将 RDD-18 UL（`060e2b34.0101010e.04200103.010c0000` EI 与 `S-Log3 / S-Gamut3.Cine` UL）无损映射至 `rtmd` 标签（`0x8106/0x8109/0x810B/0xE303`）及 `NonRealTimeMeta v2.20` XML，保证 DaVinci Resolve / Catalyst Browse 曝光与色彩一致；
   - **`SPVC` 签名防伪隔离**：Stage-B 禁止伪造 FX3 原生 `SPVC`（`sony.private_cert.v1`）或 C2PA 签名。

### 二、 `SMPTE ST 2059-2` (`PTPv2`) 亚微秒同步与多端口 `LTC` 相位对齐

- **严禁混淆 `PTP-IP` 与 `PTPv2`**：FX6 `libInfraPtpControl.so` 中的 `PTP-IP (TCP/15740)` 仅用于相机远程控制，并非 **IEEE 1588-2008 / SMPTE ST 2059-2** 时间同步协议。
- **FX6/FX3 无原生 Genlock / 硬件 PTP PHY**：标准广电链路需由锁定 `ST 2059-2` 主时钟的混合同步发生器（如 Leader `LT4670`、Ross `SPG9000`、Brainstorm `DXD-8`，处理 `37 s` TAI-UTC 闰秒偏移）输出相位锁定的 **SMPTE 12M `LTC`**，经 FX6 BNC `TC IN` 或 FX3 Multi-Port `VMC-BNCM1`（Pin 3）写入（`< 0.5 ms` 相位误差），视频帧同步交由下游切换台或 ST 2110 网关（如 AJA `IP25-R`）。
- **Stage-B `P12` 与 `H0` 安全护栏**：任何软件 PTPv2 监听仅允许运行在**有线 `USB-LAN`（`CDC-NCM` / `RNDIS`）**上（`wf12_00342260_risk == 0`），且在 `uart_boot` 刷机/恢复期间强制禁止接入 `VMC-BNCM1`（防 Pins 7/8/9 冲突）。

### 三、 广电演播室 `TSL UMD v5.0` Tally 与 16 字符 UMD 硬件安全映射

- **官方线协议格式（`tsl-umd-protocol.pdf`）**：全小端 16-bit 编码，`PBC | VER(0) | FLAGS(ASCII/UTF-16LE) | SCREEN | <DMSG>...`；UDP 原始帧上限 `2048 B`（典型端口 `40003` / `8900`），TCP 使用 `DLE/STX`（`0xFE 0x02`）帧定界与 `0xFE -> 0xFE 0xFE` 字节填充（典型端口 `5727` / `5728`）。
- **FX3 单色红灯防误导约束**：FX6 拥有绿色 Tally 配置（`BKID_APP_SETTING_G_TALLY_LAMP`），而 FX3 机身仅有单色红色前/顶后 REC Tally LED（`sequence_set_tally_status`）。因此 Stage-B 必须执行：
  - **`Red (1, PGM)`**：点亮 FX3 机身前/后红灯 + `GPE0` OSD 红色边框；
  - **`Green (2, PVW)`**：**强制熄灭 FX3 物理红灯**（防止播控误判为在播红灯！），仅在 `GPE0` OSD 绘制**绿色预览边框**；
  - **`Amber (3)` / `Off (0)`**：熄灭物理红灯 + OSD 琥珀色或无边框；同时将动态 UMD 台标清洗并截断至 `16` 个可打印字符，全程在 `P12` 有线隔离下运行。

### 四、 2025–2026 索尼 ARM64 `CXD90057` 逆向、QEMU 与 BootROM 救砖前沿

- 汇总 `Rem021/sony-fx3-fx6-lab`、`DavidBuchanan314/ILCE-7M4-RE`（48 KB BootROM 无 USB 栈，RP2040 `48000 -> 115200` 波特率串口注入 `fastboot.bin` 至 `0x92028000` 解锁 `18d1:4ee0`、`oem partition`、`oem dumpbrom` 与 `boot0` AES-XTS 密钥派生）、`Erlla/sony-a7m4-custom-firmware`、`leogenot/sony-a7iv-feature-research`（27 个机型类与 `ALCIN_UUD`）、`YuuLuo/a7c2-service-preload`、`xyzhangxin/sony-a6700-powerful` 与 `dino2048/zv-e10-toolkit`，持续强化实验室“严格 `os.O_RDONLY` 只读审计 + Stage-B `eMMC` 零写入防火墙”铁律。
