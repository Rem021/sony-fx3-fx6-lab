# Wave-15 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十五波全球索尼固件 / 虚拟化 / 救砖与虚拟制片 LED 墙、FreeD 镜头追踪及 Art-Net 4 / sACN 情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 128 — Wave-15 Live Global Web Intelligence Sync & 25th Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified public technical references covering:
  1. **Sony Virtual Production `Crystal LED` (`VERONA` / `CAPRI`), `Brompton Tessera SX40` & `Megapixel HELIOS` PWM Anti-Banding vs `IMX510` Rolling-Shutter (`8.7 ms / 13.2 ms`) & Fractional `ECS` Shutter**
  2. **`FreeD` (`0xD1` 29-Byte UDP) Camera & E-Mount 12-Pin (`Zoom / Focus / Iris`) Tracking Telemetry into Unreal Engine `LiveLinkFreeD`**
  3. **`Art-Net 4` (`UDP 6454`, `OpDmx 0x5000` / `ArtSync 0x5200`) & `sACN` (`ANSI E1.31`, `UDP 5568`) DMX Lighting-Cue Frame-Boundary Shutter Sync under `P12` Wired Isolation**
  4. **2025–2026 Sony `CXD90057` ARM64 Firmware RE, QEMU Virtualization & `eMMC` / `UART` Unbrick Advances**
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs and read-only (`os.O_RDONLY`) donor markers cited directly.

---

## English Technical Synthesis

### 1. Virtual Production LED-Volume Anti-Banding, `IMX510` Readout Skew & Fractional `ECS`

1. **LED Volume Refresh & Scan-Multiplexing Physics (`Crystal LED` + `Brompton` / `Megapixel`)**:
   - **Sony Crystal LED VERONA** (`ZRD-VP15EB` / `ZRD-VP23EB` for Brompton, `ZRD-VP15EM` / `ZRD-VP23EM` for Megapixel, 1.56 mm / 2.31 mm pitch) and **CAPRI** (`ZRD-VS25FB` / `ZRD-VS25FM`, 2.5 mm pitch) operate up to **7,680 Hz** refresh with 22-bit internal processing and deep-black anti-reflection surfaces.
   - **Megapixel HELIOS** ([https://www.megapixelvr.com/helios/](https://www.megapixelvr.com/helios/)) exposes **Camera Mode**, **Sub-Frame Slices**, **GhostFrame**, and **Advanced Sync** to phase-align LED driver PWM cycles to cinema camera exposures; **Brompton Tessera SX40** provides **ShutterSync**, fine phase offset, and extended bit depth.
   - Although LED drivers pulse at high carrier PWM (`960..7680 Hz`), matrix-driven cabinets use **scan-line multiplexing** (`1/8`, `1/16`, `1/32` mux ratio), making the effective full-row refresh cycle:
     $$f_{\text{mux}} = \frac{f_{\text{PWM}}}{N_{\text{mux}}}$$
     For example, a `7680 Hz` panel with `1/16` scan multiplexing yields $f_{\text{mux}} = 480\text{ Hz}$ ($T_{\text{mux}} = 2.083\text{ ms}$). Any camera exposure shorter than $T_{\text{mux}}$ or not locked to an integer subharmonic $k \ge 1$ of $f_{\text{mux}}$ captures partially scanned LED rows as visible dark/bright horizontal bands or traveling roll bars.

2. **Sony FX3 (`ILME-FX3`) / FX6 (`ILME-FX6`) `IMX510` Readout vs `ECS` (Extended Clear Scan)**:
   - The shared full-frame **IMX510** BSI CMOS sensor exhibits a ~`8.7 ms` 4K DCI/UHD line-by-line rolling-shutter readout in standard `24p–60p` full-frame (`~13.2 ms` full-height / oversampled reference mode, `~4.35 ms` in `4K 120p`, `~2.20 ms` in `FHD 240p` — notably faster than FX9 `~22.2 ms` or BURANO `14.8–18.9 ms`, while slower than VENICE 2 `< 3 ms`).
   - Because FX3 (`v7.02`) and FX6 (`v6.01`) lack a BNC Genlock Reference Input port, Virtual Production workflows rely on **fractional Extended Clear Scan (`ECS` / FX3 `HighResolutionShutterSpeedMode` / `Anti-flicker Tv Scan`, `23.98..7680.0 Hz`)** tuned precisely to an integer subharmonic $f_{\text{ECS}} \approx f_{\text{mux}} / k$ (e.g., `48.00 Hz` or `43.64 Hz` against $f_{\text{mux}} = 480\text{ Hz}$) with harmonic error $< 1.0\%$, eliminating intra-frame scanline banding across the entire `8.7 ms / 13.2 ms` readout window.

---

### 2. Wired `FreeD` (`0xD1` 29-Byte UDP) Camera & E-Mount 12-Pin Lens Telemetry -> Unreal Engine `LiveLink`

1. **Official `FreeD` `D1` (`0xD1`) 29-Byte Wire Format**:
   - Reference: [Unreal Engine Documentation — FreeD Live Link](https://dev.epicgames.com/documentation/en-us/unreal-engine/freed-live-link-in-unreal-engine) (default Unreal Engine `LiveLinkFreeD` receiver port: **UDP `40000`**).
   - Fixed 29-byte big-endian datagram (`D1` Position/Orientation/Lens packet):
     | Byte Range | Field | Encoding / Scale |
     | --- | --- | --- |
     | `0` | Packet Type | `0xD1` |
     | `1` | Camera ID | `uint8` (`0..255`) |
     | `2..4` | Pan | signed 24-bit (`degrees * 32768`) |
     | `5..7` | Tilt | signed 24-bit (`degrees * 32768`) |
     | `8..10` | Roll | signed 24-bit (`degrees * 32768`) |
     | `11..13` | X Position | signed 24-bit (`mm * 64`) |
     | `14..16` | Y Position | signed 24-bit (`mm * 64`) |
     | `17..19` | Z Position | signed 24-bit (`mm * 64`) |
     | `20..22` | Zoom | unsigned 24-bit (`0x000000..0xFFFFFF`) |
     | `23..25` | Focus | unsigned 24-bit (`0x000000..0xFFFFFF`) |
     | `26..27` | Spare / User Defined | `uint16` (Sony profile: lower 12 bits Iris `0x000..0xFFF`, upper 4 bits rolling counter `0..15`) |
     | `28` | Checksum | `(0x40 - sum(packet[0:28])) & 0xFF` |

2. **Sony E-Mount 12-Pin Telemetry Bridge under `P12` Wired Isolation**:
   - While Sony **ILME-FR7** streams `FreeD D1` (and OpenTrackIO) natively, **ILME-FX3 / ILME-FX6** expose E-Mount 12-pin focus distance, focal length, and aperture telemetry via `lens_comm.ko` / `Mount_DividedInfo` / Camera Remote SDK (`CRSDK`) or external FIZ encoders (`VIVE Mars FIZTrack`, `LOLED Indiemark`, `Preston MDR`).
   - All `FreeD` UDP telemetry bridges MUST bind strictly to wired **USB-LAN** (`CDC_NCM_RTL8153`, `CDC_NCM_AX88179`, `USB_RNDIS_WIRED`) under Stage-B **P12 Wi-Fi-OFF** (`wf12_00342260_risk == 0`), never over `WLAN0` or `BT_PAN`.

---

### 3. `Art-Net 4` (`UDP 6454`) & `sACN` (`ANSI E1.31`, `UDP 5568`) Lighting-Cue Frame-Boundary Shutter Sync

1. **Official DMX-over-IP Wire Contracts**:
   - Reference: [Unreal Engine Documentation — DMX in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/dmx-in-unreal-engine).
   - **Art-Net 4** (`UDP 6454`): `"Art-Net\0"` (8-byte magic) + `OpCode` LE (`OpDmx = 0x5000`, `OpSync = 0x5200` `ArtSync`) + `ProtVer = 14` BE + `Sequence` + `Physical` + `SubUni` (`(SubNet << 4) | Universe`) + `Net` (`0..127`, 15-bit Port-Address = `32,768` universes) + `Length` BE (`2..512`, even) + DMX512 payload. **`ArtSync` (`0x5200`)** holds multi-universe buffers until simultaneous latching to prevent spatial DMX tearing across LED pixel bars and DMX fixtures.
   - **sACN (`ANSI E1.31`, `UDP 5568`)**: Root Layer (`Preamble 0x0010`, `Post-amble 0x0000`, ACN PID `"ASC-E1.17\0\0\0"`), Universe `1..63999`, IPv4 Multicast `239.255.(u>>8).(u&0xFF)`, Priority `0..200` (default `100`), plus **E1.31 Synchronization Universe** for frame-locked execution.

2. **Rolling-Shutter Strobe / Flash Tear Prevention**:
   - If a high-contrast DMX lighting flash or intensity step fires inside the active `8.7 ms` or `13.2 ms` `IMX510` sensor readout window (mid-frame rather than during the vertical blanking / frame-boundary interval), the top rows and bottom rows capture completely different exposure states (horizontal flash tear).
   - The Phase 128 auditor verifies frame-boundary alignment, `ArtSync` / `E1.31 Sync` multi-universe lock, jitter bounds, and strict **P12 wired `USB-LAN`** binding (`wf12_00342260_risk == 0`).

---

### 4. 2025–2026 Sony `CXD90057` Firmware RE, ARM64 QEMU Virtualization & `eMMC` / `UART` Unbrick Advances

| Project / Source | Domain | Verified Technical Takeaways | Canonical URL |
| :--- | :--- | :--- | :--- |
| `Rem021/sony-fx3-fx6-lab` | FX3 `v7.02` & FX6 `v6.01` QEMU Lab | Apple Silicon ARM64 QEMU emulation achieving 180s FX6-on-FX3 media-start milestone with web UI and 25 clean-room `os.O_RDONLY` auditors. | https://github.com/Rem021/sony-fx3-fx6-lab |
| `DavidBuchanan314/ILCE-7M4-RE` | `CXD90057` BootROM & Fastboot | Documents 48 KB BootROM (no USB stack), RP2040 `uart_boot` (`48000 -> 115200` baud) injecting Sony-signed `fastboot.bin` to `0x92028000` (`18d1:4ee0`, `oem partition`, `oem dumpbrom`), `boot0`-derived eMMC AES-XTS per-512B sector tweak, and `verifyKey()` patch analysis. | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `DavidBuchanan314/Sony-ILCE-7M4-Linux` | `CXD90057` Linux Kernel | Kernel `4.9.337` bring-up notes on shared `CXD90057` (`"Mira"`) 4× Cortex-A35 + TOPPERS/FMP RTOS + SA DSP architecture. | https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux |
| `Erlla/sony-a7m4-custom-firmware` | `CXD90057` eMMC Flashing | Sparse eMMC flashing workflows and physical SPI NOR (`EXBL`) boundary isolation outside regular eMMC dumps. | https://github.com/Erlla/sony-a7m4-custom-firmware |
| `leogenot/sony-a7iv-feature-research` | `CXD90057` App Class Matrix | Maps 27 Sony product classes (`ALCIN_UUD` FX3 vs `PRODUCT_MODEL_OT_UUD` A7S III), `fwtool.py`, and Cine EI gating properties. | https://github.com/leogenot/sony-a7iv-feature-research |
| `YuuLuo/a7c2-service-preload` | Service Auth & `ld.so.preload` | A7C II service authentication flow, Jiritsu path verification, and `ld.so.preload` runtime hook analysis. | https://github.com/YuuLuo/a7c2-service-preload |
| `xyzhangxin/sony-a6700-powerful` | A6700 (`v2.00`) RP2040 Recovery | RP2040 Pico + Type-C CC pin wiring for RAM fastboot launch and mandatory full eMMC backup prior to edits. | https://github.com/xyzhangxin/sony-a6700-powerful |
| `dino2048/zv-e10-toolkit` | ZV-E10 BootROM & 16-Part Backup | 24 KiB BootROM analysis, 16-partition eMMC backup/restore excluding `boot0`/`boot1`, and two-stage fastboot recovery. | https://github.com/dino2048/zv-e10-toolkit |
| `cokeenet/zve10-qemu` & `ivica00/sony-a6400-research` | ARMv7/ARM64 QEMU & UART | Offline QEMU boot harnesses, UART boot traces, and clean-room firmware address-space mapping. | https://github.com/ivica00/sony-a6400-research |
| `ma1co/Sony-PMCA-RE` | PMCA-RE & Service Shell | Tracks `serviceshell` authentication changes and region/firmware brick post-mortems across recent Sony bodies. | https://github.com/ma1co/Sony-PMCA-RE |

---

## 简体中文技术摘要

### 一、 虚拟制片 LED 墙（Crystal LED / Brompton / Megapixel）抗扫描条纹与 `IMX510` 分数快门 `ECS`

1. **高刷与扫描复用（Scan Multiplexing）物理本质**：
   - Sony **Crystal LED VERONA**（`ZRD-VP15EB/23EB` 适配 Brompton；`ZRD-VP15EM/23EM` 适配 Megapixel）与 **CAPRI**（`ZRD-VS25FB/FM`）支持高达 **7,680 Hz** 刷新率与 22-bit 内部处理，配合 **Megapixel HELIOS**（`Camera Mode` / `Sub-Frame Slices` / `GhostFrame` / `Advanced Sync`）与 **Brompton Tessera SX40**（`ShutterSync`）使用。
   - LED 箱体采用行列扫描复用（`1/8`、`1/16`、`1/32`），实际等效整行刷新周期频率为 $f_{\text{mux}} = f_{\text{PWM}} / N_{\text{mux}}$（例如 `7680 Hz` 配合 `1/16` 扫描，等效 $f_{\text{mux}} = 480\text{ Hz}$，单次扫频周期 $T_{\text{mux}} = 2.083\text{ ms}$）。若相机曝光时间短于 $T_{\text{mux}}$ 或与 $f_{\text{mux}}$ 非整数分频锁定，画面将出现明暗横纹或滚动条纹。
2. **FX3 / FX6 `IMX510` 卷帘读出与分数级 `ECS` 求解**：
   - FX3（`v7.02`）与 FX6（`v6.01`）搭载同款全画幅 `IMX510` 传感器，全画幅 4K 标准读出时间约 **`8.7 ms`**（全高超采样参考约 **`13.2 ms`**，`4K 120p` 约 `4.35 ms`，`FHD 240p` 约 `2.20 ms`）。
   - 在无 BNC Genlock 参考口的前提下，利用 `ECS`（Extended Clear Scan / FX3 `HighResolutionShutterSpeedMode` / `Anti-flicker Tv Scan`，范围 `23.98..7680.0 Hz`）求解最接近目标快门角的整数分频频率 $f_{\text{ECS}} \approx f_{\text{mux}} / k$（谐波误差 `< 1.0%`），可有效消除 LED 墙扫描条纹（并显式审计无 Genlock 下的相位告警）。

### 二、 有线 `FreeD`（`0xD1` 29 字节 UDP）与 E 卡口 12 针镜头实时编码器桥接

- **标准 `0xD1` 29 字节大端报文**：遵循 Unreal Engine `LiveLinkFreeD`（默认 **UDP `40000`**）：Byte `0 = 0xD1`，Byte `1 = CameraID`，Pan/Tilt/Roll 为有符号 24-bit（`角度 * 32768`），X/Y/Z 为有符号 24-bit（`毫米 * 64`），Zoom/Focus 为无符号 24-bit（`0..0xFFFFFF`），Bytes `26..27` Spare（低 12 位编码 Sony 光圈 `Iris 0..4095`，高 4 位滚动帧计数 `0..15`），Byte `28` 为 `(0x40 - sum(pkt[0:28])) & 0xFF` 校验和。
- **FX3/FX6 E 卡口桥接与 `P12` 有线隔离**：FX3/FX6 可通过 E 卡口 12 针通讯（`lens_comm.ko` / `Mount_DividedInfo` / `CRSDK`）或外置 FIZ 编码器（`VIVE Mars FIZTrack`、`LOLED Indiemark`、`Preston MDR`）合成 `FreeD D1` 报文，且强制绑定有线 **`USB-LAN`**（`CDC_NCM_RTL8153` / `CDC_NCM_AX88179` / `USB_RNDIS_WIRED`），严禁经由 `Wi-Fi` 或蓝牙传输（`wf12_00342260_risk == 0`）。

### 三、 `Art-Net 4`（`UDP 6454`）与 `sACN`（`ANSI E1.31`，`UDP 5568`）灯光同步帧边界防护

- **`Art-Net 4` (`UDP 6454`)**：`"Art-Net\0"` 魔数、`OpDmx = 0x5000`（小端）、`ProtVer = 14`（大端）、15-bit Port-Address（`Net`/`SubNet`/`Universe` 共 32,768 个域），配合 `ArtSync`（`0x5200`）防止多域画面撕裂。
- **`sACN` (`ANSI E1.31`, `UDP 5568`)**：`"ASC-E1.17\0\0\0"` 根层标识、域 `1..63999`、组播地址 `239.255.H.L`、优先级 `0..200` 及 `E1.31 Sync` 同步域。
- **卷帘闪光撕裂拦截**：任何 DMX 频闪/切光指令若落在 `IMX510` 有效读出窗口（`8.7 ms / 13.2 ms`）内部而非帧边界消隐区（Frame-Boundary Blanking），都会导致单帧上下半区曝光断层——第 128 阶段审计器对此执行硬拦截，并确保零持久化 eMMC/校准分区写入。

### 四、 2025–2026 索尼固件逆向、ARM64 QEMU 与 BootROM / eMMC 救砖前沿

- 综合 `Rem021/sony-fx3-fx6-lab`、`DavidBuchanan314/ILCE-7M4-RE`（`CXD90057` 48 KB BootROM 无 USB 栈、RP2040 `uart_boot` 注入 `fastboot.bin`、`boot0` 派生 eMMC AES-XTS 扇区密钥）、`Sony-ILCE-7M4-Linux`、`Erlla/sony-a7m4-custom-firmware`、`leogenot/sony-a7iv-feature-research`、`YuuLuo/a7c2-service-preload`、`xyzhangxin/sony-a6700-powerful`、`dino2048/zv-e10-toolkit`、`cokeenet/zve10-qemu`、`ivica00/sony-a6400-research` 与 `ma1co/Sony-PMCA-RE`，持续加固“严格 `os.O_RDONLY` 只读审计 + Stage-B 零持久化 `eMMC` 写入防火墙”工程基线。
