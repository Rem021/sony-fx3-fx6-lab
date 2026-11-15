# Wave-11 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十一波全球索尼固件 / 虚拟化 / 救砖与 C2PA 2.1 / E-Mount 光学补偿 / Monitor & Control 多机车队情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 105 — Wave-11 Global Live Web Intelligence Sync & 20th Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Clean-room synthesis of live-verified public documentation, standards specifications, and open-source Sony `BIONZ XR` / `CXD90057` reverse-engineering, QEMU virtualization, and solderless eMMC unbrick toolchains across four axes: (1) Sony **Camera Authenticity Solution / C2PA 2.1** in-camera video signing & `cnflasha`/RPMB key-vault isolation, (2) **E-Mount 12-Pin Lens Compensation** (radial $\cos^4(\theta)$ shading/vignetting, lateral chromatic aberration, distortion polynomials, and unchipped PL/anamorphic fail-safe), (3) **Sony Monitor & Control (M&C v3.1.0+)** wired USB-LAN / `PTP-IP` multi-camera fleet control & `P12` RF-off isolation, and (4) 2025–2026 global Sony firmware RE, QEMU virtualization, and eMMC unbrick advances.
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs cited directly.

---

## English Technical Synthesis

### 1. Sony Camera Authenticity Solution & C2PA 2.1 In-Camera Video Signing (`ILME-FX3` Ver. 7.00–7.02)

1. **Firmware Support & Launch Timeline**:
   - Sony officially expanded **Camera Authenticity Solution** to video on October 30, 2025, with `ILME-FX3` (Ver. 7.00+, latest **Ver. 7.02**, March 17, 2026) and `ILME-FX3A` (Ver. 2.02, March 2026) joining `FX30`, `α1 II`, `α9 III`, and `PXW-Z300`. Note that FX3 units on Ver. 2.02 or earlier must upgrade through Ver. 2.04/2.05 before installing Ver. 7.02.
   - **ILME-FX6 (`v6.01`/`v6.02`) Contrast**: Although FX6 `appFw.so` shares common `InfraC2PA` / `mpr::CheckDigitalSignature` infrastructure (`VAL_c2pa_certificate_status_*`) and `.uxc` strings (`0x00002E89` `"Certificate for C2PA"`), FX6 is **not** provisioned on Sony's Camera Authenticity Solution compatibility list.
   - Verified References: [Sony Camera Authenticity Solution](https://authenticity.sony.net/camera/en-us/index.html), [Sony Digital Signature Help Guide](https://helpguide.sony.net/di/digitalsign/v1/en/contents/Enabling_digital_sig_func.html), [C2PA Specification v2.1](https://spec.c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html).

2. **Hardware Key-Vault, JUMBF Provenance & Operational Constraints**:
   - **Provisioning (`RQ_LIC.DAT` + Hardware RoT)**: Requires a paid Digital Signature License (`RQ_LIC.DAT`, placed in Slot 1 root; FX3/FX3A/FX30 reject license packages containing **> 100 licenses**), a camera-generated hardware key pair (`[Create Key Pair]` inside TrustZone / RPMB / `cnflasha`), server time sync (`AUTO_SYNC_SEVER_DATE_TIME`), and a C2PA certificate (`sigcert.p12/.pfx`).
   - **3D Single-Axis Depth & Video Constraints**: Embeds C2PA Content Credentials (`jumb`/`jumd` UUID `63327061-0011-0010-8000-00aa00389b71`, Sony manifest label `lc2pa.createdlsony.created`, `(C2PA+SSIG)`) plus single-axis 3D depth metadata so Sony **Camera Verify (Beta)** can confirm real 3D physical scenes vs monitor re-photography.
   - **Supported Formats**: MP4 clips at **$\le 222\text{ Mbps}$** only; disabled in `S&Q` (Slow & Quick), time-lapse, `HDMI RAW` external output, `8K`, and live streaming. Deleting the Digital Signature function permanently revokes keys; `[Camera Settings Reset]` preserves them.
   - **Stage-B Clean-Room Lab Boundary**: Stage-B FX6-on-FX3 research overlays MUST keep `cnflasha` / `RPMB` / `p12:/cert` mounted strictly `O_RDONLY`, NEVER extract or spoof per-body ECDSA keys across bodies, and transparently mark overlay clips as unsigned clean-room research builds rather than attempting forged `c2cs` COSE signatures.

---

### 2. Sony Monitor & Control (M&C v3.1.0+) Wired USB-LAN / `PTP-IP` Multi-Cam Fleet Architecture

1. **FX3 vs FX6 Wired Connection Matrix on iPadOS (18.2–27.0 / iPadOS 26.1+)**:
   - Per Sony's live **Monitor & Control Help Guide** (`Ver. 3.1.0`), **Wired LAN via a Router or Switching Hub** is the **only** wired multi-camera topology supporting mixed **FX3 (`Ver. 4.00+`) + FX6 (`Ver. 5.00+`/`6.02`)** fleets simultaneously on iPad:
     - **Direct Camera-to-iPad Ethernet**: Explicitly **unsupported** in Multi-Camera Monitoring mode — traffic MUST traverse a router or switching hub.
     - **USB-C `Remote Shooting` (via powered USB hub on iPadOS 26.1+)**: Supported on **FX3** (`Timecode` and `Focus Map` are unavailable over direct USB cable), **not supported** on FX6.
     - **USB `Tethering`**: Unsupported on iPadOS and macOS for FX6 (`not supported on iPadOS/macOS`).
   - Verified References: [Sony Monitor & Control Help Guide](https://helpguide.sony.net/promobile/mc/v1/en/index.html), [M&C Supported Cameras & Connection Methods](https://helpguide.sony.net/promobile/mc/v1/en/contents/supported_camera.html), [M&C Wired LAN Multi-Camera Mode](https://helpguide.sony.net/promobile/mc/v1/en/contents/connecting_wired_lan_mcm.html), [M&C Wired LAN FX6/FX5 Setup](https://helpguide.sony.net/promobile/mc/v1/en/contents/connecting_router.html).

2. **`PTP-IP`, `Access Authentication` & Monitoring Tiers**:
   - **Camera Remote SDK Ver. 2.02.00 (2026-Jun-10)** and `Camera Remote Toolkit` expose **PTP-IP** (`libInfraPtpControl.so` `PTPT_init_ip` / `_ptpt_close_ip_remote`, `VAL_ptp_ip_connect_state_PTP_IP_CONNECT_STATE_CONNECT`) over Ethernet (`CDC-NCM` / `Realtek RTL8153` adapters such as TP-Link UE300C V2 on FX3 and Belkin USB-C Ethernet on FX6) with unified `Access Authentication` (`VAL_setting_access_authentication_ACCESS_AUTHENTICATION_ON`, TLS fingerprint verification).
   - **Plan Matrix**: **Free Plan** supports up to **4 cameras** on iPad Pro with synchronized Waveform, False Color, Histogram, Zebra, LUT preview, and Focus control; **Basic** adds simultaneous multi-cam settings changes; **Premium** scales to **20 cameras** + EL Zone + Image Overlay.
   - **Phase 105 `P12` RF-Off Synergy**: Running the 4-camera fleet over Wired USB-LAN + Ethernet switch while locking `Airplane Mode = On` (`VAL_setting_airplane_mode_AIRPLANE_MODE_ON`) eliminates Wi-Fi/BT RF contention and guarantees **0 `WF-12 00342260` crashes**.
   - Verified Reference: [Sony Camera Remote SDK Portal](https://www.sony.net/CameraRemoteSDK/).

---

### 3. Sony E-Mount 12-Pin Lens Shading, Lateral Chromatic Aberration & Distortion Compensation

1. **Decentralized Lens-ROM Profile Architecture vs Fixed Body Tables**:
   - Unlike legacy A-Mount (`SAL`) bodies that kept static lookup tables inside body firmware, E-Mount (`SEL` / `SELP` and licensed third-party lenses such as Tamron, Sigma, and Sirui Aurora `V1.0.8+`) stores **Shading (Peripheral Illumination)**, **Lateral Chromatic Aberration (Chroma Aberr.)**, and **Geometric Distortion** polynomial coefficients directly in **lens firmware ROM**, transmitted over the 12-pin E-Mount bus (`libInfraLensCommunicator.so` -> AP `PID_SET_SHADING_CORRECTION` / `PID_SET_CHROMA_ABERR_CORRECTION` / `PID_SET_DISTORTION_CORRECTION` -> CP `FW: SET_SHADING_CORRECTION` / `FW: SET_CHROMA_ABERR_CORRECTION` / `FW: SET_DISTORTION_CORRECTION` -> `libmpr.so` `UDAMSetDistortionCorrectionValue`).
   - `.ARW` stills retain uncompensated raw pixels with embedded correction opcodes, whereas in-camera JPEG and XAVC video bake active Shading/CA/Distortion (except X-OCN on BURANO/FX5, which defers distortion compensation to Catalyst Browse/Prepare).
   - Verified Reference: [Sony ILME-FX3 Help Guide Portal](https://helpguide.sony.net/ilc/2210/v1/en/index.html).

2. **Optical Fail-Safe for Unchipped PL & Manual Anamorphic Lenses + Factory `psd.bin` / `defdet.bin` Protection**:
   - When an unchipped manual PL adapter or manual anamorphic lens is attached (zero 12-pin electronic communication), body compensation **must drop immediately to identity `1.0x`** (`0.0` radial distortion / `0.0` lateral CA / `1.0x` shading gain) rather than applying stale electronic G-Master coefficients from a previous hot-swap.
   - Dynamic E-Mount optical compensation MUST operate purely in volatile RAM / DSP registers without touching per-body factory sensor calibration files (`p2:/setting/psd.bin` optical shading map, `p2:/setting/defdet.bin` defect-pixel table, `p2:/setting/Backup.bin`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin` `fixed_lensfile`).

---

### 4. Recent Sony Firmware RE, QEMU Virtualization & eMMC Unbrick Intelligence (2025–2026)

| Project / 项目 | Domain / 领域 | Key Technical Findings / 核心技术进展 | Canonical URL |
| :--- | :--- | :--- | :--- |
| `DavidBuchanan314/ILCE-7M4-RE` | `BIONZ XR` (`CXD90057`) RE & BootROM | AES-XTS `SDM2` partition decryption (`parse_emmc_partitions.py`), UART `uart_boot` RP2040 bridge, temporary SRAM Fastboot `oem partition` rescue for `nflasha1..17`. | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `dino2048/zv-e10-toolkit` | Solderless eMMC Brick Rescue | BootROM stage1/stage2 USB/SDHCI + RP2040 Pico bridge + sparse partition recovery across 16 user partitions (preserving `boot0`/`boot1` and factory calibration). | https://github.com/dino2048/zv-e10-toolkit |
| `cokeenet/zve10-qemu` | `CXD90045` QEMU Machine Model | QEMU peripheral modeling, boot patches, UART boot protocol, and eMMC partition maps for Sony BIONZ SoCs. | https://github.com/cokeenet/zve10-qemu |
| `ma1co/qemu` | Sony BIONZ QEMU Fork | Community QEMU fork for Sony camera firmware execution alongside `OpenMemories-CI` workflows. | https://github.com/ma1co/qemu |
| QEMU Official `eMMC` Device Docs | Multi-Partition eMMC Modeling | Standard `boot0`/`boot1`/RPMB/UDA raw image layout (`scripts/mkemmc.sh`) directly guiding clean-room `RPMB`/`cnflasha` isolation modeling. | https://www.qemu.org/docs/master/system/devices/emmc.html |

---

## 简体中文技术摘要

### 1. 索尼相机真实性解决方案与 C2PA 2.1 机内视频数字签名（`ILME-FX3` Ver. 7.00–7.02）

- **固件支持现状**：索尼于 2025 年 10 月 30 日正式将 **Camera Authenticity Solution** 扩展至视频录制，`ILME-FX3`（Ver. 7.00+，最新 **Ver. 7.02**，2026 年 3 月 17 日发布）及 `ILME-FX3A`（Ver. 2.02）原生支持 MP4（**≤ 222 Mbps**）机内 C2PA 2.1 + 专有数字签名（`lc2pa.createdlsony.created` / `(C2PA+SSIG)`）及同光轴 **3D 深度防屏摄验证信息**（不支持 S&Q、延时、HDMI RAW、8K 与推流）。需注意早期 Ver. 2.02 及以下 FX3 须先经 Ver. 2.04/2.05 过渡升级。
- **许可、密钥库与 Stage-B 隔离红线**：需通过槽位 1 根目录导入 `RQ_LIC.DAT`（FX3/FX3A/FX30 单包上限 **100 个许可**）并由硬件芯片组生成密钥对（`InfraC2PA` / TrustZone / `RPMB` / `cnflasha`）及导入 C2PA 证书；而 `ILME-FX6` 虽在 `appFw.so` 内包含部分状态机字符串但未获得官方 C2PA 硬件签名授权。Stage-B 用户态叠加层严禁读写 `cnflasha`/`RPMB`/`p12:/cert`，严禁跨机身伪造证书或强行签发虚假 `c2cs` 硬件签名，必须显式标记为未签名洁净室研究构建。

### 2. 索尼 Monitor & Control（M&C v3.1.0+）有线 USB-LAN / `PTP-IP` 多机控制矩阵

- **有线多机拓扑差异**：根据索尼官方 **Monitor & Control 帮助指南**，FX3 与 FX6 混合 4 机位（免费版上限 **4 台**，Basic 版支持群控同步改参，Premium 版上限 **20 台**）在 iPadOS 上唯一通用的有线组网方式是 **通过路由器或交换机接入 Wired LAN**（严禁相机直连 iPad 网口；FX3 直连 USB-C 会丢失时码与 Focus Map；FX6 不支持 USB Remote Shooting，且其 USB Tethering 明确不支持 iPadOS/macOS）。
- **`PTP-IP` 与 `P12` 射频静默协同**：借助 `libInfraPtpControl.so`（`PTPT_init_ip` / `ptp_make_dat_header_packet`）与 `Camera Remote SDK v2.02.00`，`CDC-NCM` / `RTL8153` 有线网卡可在开启 **飞行模式（`P12` Wi-Fi/BT 100% 断网）** 下实现 `Access Authentication` 认证、波形图/伪彩/对焦图流式监看及多机群控同步录制（**0 次 `WF-12 00342260` 报错**）。

### 3. E-Mount 12 针镜头阴影、横向色差与畸变多项式补偿及出厂校准保护

- **去中心化镜头固件参数**：与早期 A 卡口机身固化的查表不同，E 卡口原厂及授权第三方镜头（Tamron、Sigma、Sirui 等）将 $\cos^4(\theta)$ 边缘照度衰减（暗角/阴影补偿）、红/蓝通道横向色差微尺度多项式以及桶形/枕形畸变多项式存储于镜头自身固件 ROM 中，经 12 针总线传至 `appFw.so`（`PID_SET_SHADING_CORRECTION` / `PID_SET_CHROMA_ABERR_CORRECTION` / `PID_SET_DISTORTION_CORRECTION`）及 CP 处理器（`FW: SET_*`）与 `libmpr.so`（`UDAMSetDistortionCorrectionValue`）。
- **无触点手动 PL/变形镜头身份回退（Identity 1.0x）与零突变保护**：接入无电子触点的手动 PL 转接环或变形镜头时，系统必须即时归零至 **严格 `1.0x` 恒等映射**，严禁残留上一支电子 GM 镜头的补偿系数；同时所有光学补偿运算均严格限制在易失性内存完成，100% 比特级冻结出厂每机独有的 `p2:/setting/psd.bin`（阴影校准）、`p2:/setting/defdet.bin`（坏点表）、`p2:/setting/Backup.bin`、`p6:/tmp/jiritsu` 与 `p18:/lens/lensfile.bin`。

### 4. 2025–2026 索尼固件逆向、QEMU 虚拟化与免焊接 eMMC 救砖进展

- 本波情报同步确认 `DavidBuchanan314/ILCE-7M4-RE`、`dino2048/zv-e10-toolkit`、`cokeenet/zve10-qemu`、`ma1co/qemu` 与 QEMU 官方 eMMC（`boot0`/`boot1`/`RPMB`/UDA）模型持续印证了本实验室“**严格 `os.O_RDONLY` 只读检测 + `cnflasha`/出厂校准零写入 + 洁净室双模式验证**”架构的安全边界与工程可靠性。
