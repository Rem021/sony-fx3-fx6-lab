# Wave-12 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十二波全球索尼固件 / 虚拟化 / 救砖与 ProRes RAW-BRAW / 呼吸补偿 / MI热靴时钟同步情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 114 — Wave-12 Global Live Web Intelligence Sync & 22nd Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified official Sony documentation, external RAW recorder specifications, and 2025–2026 open-source Sony `BIONZ XR` / `CXD90057` / `CXD90045` firmware RE, QEMU virtualization, and solderless eMMC unbrick research across four technical axes:
  1. **Sony FX3/FX6 16-Bit Linear RAW over HDMI/SDI -> Atomos ProRes RAW (12-Bit Log) & Blackmagic BRAW Metadata Handshake**
  2. **Sony E-Mount Focus Breathing Compensation (`1.06x..1.13x` Dynamic FOV Crop) vs HDMI RAW / S&Q 120p Mutual Exclusion**
  3. **24-Pin Multi-Interface (MI) Shoe Digital Audio (`48 kHz / 24-bit 4ch` `XLR-H1` I2S Master-Clock PLL & NTSC `23.976/29.97/59.94` Drift Control)**
  4. **2025–2026 Sony Firmware RE, QEMU Virtualization & Solderless eMMC Brick-Recovery Advances**
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs cited directly.

---

## English Technical Synthesis

### 1. Sony FX3 / FX6 16-Bit Linear HDMI/SDI RAW -> Atomos ProRes RAW & Blackmagic BRAW Metadata Handshake

1. **Camera 16-Bit Linear RAW Output Geometry & Constraints**:
   - **ILME-FX3 (`Ver. 7.02`)**: Outputs **16-bit scene-linear Bayer RAW** over full-size **HDMI Type-A** at **`4264 × 2408`** (`4.2K` sensor readout, or `4240 × 2385` via Atomos Sony Metadata Crop to 16:9) up to **`59.94p`** (`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p`).
   - **ILME-FX6 (`Ver. 6.00+ / 6.01`)**: Outputs 16-bit linear RAW over **12G-SDI** (`4096 × 2160` 4K DCI or `3840 × 2160` UHD up to `59.94p`) and **HDMI 2.0** (`4264 × 2408` up to `59.94p`), with FX6 Ver. 6.00 (March 2026) adding Blackmagic RAW HDMI signaling alongside Atomos ProRes RAW.
   - **Mandatory Firmware Guards (Verified in Official Sony FX3 Help Guide)**:
     - `[Log Shooting]` under `[Log Shooting Setting]` **must** be enabled (`!= Off`); gamma is locked to `S-Log3` and `[Color Gamut]` (`S-Gamut3.Cine` / `S-Gamut3`) is stamped as metadata onto the HDMI RAW stream.
     - `[HDMI Info. Display]` is **automatically forced to `Off`** during RAW output so OSD telemetry never contaminates the Bayer stream.
     - Slow & Quick Motion (`S&Q`) **locks `[RAW Output]` to `Off`**, and `SteadyShot [Active]` electronic EIS is disabled during HDMI RAW output.
   - Verified Official References:
     - [Sony ILME-FX3 Help Guide: Outputting RAW movies to an external RAW recorder](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1002078215.html)
     - [Sony ILME-FX3 Help Guide: HDMI Output Settings (movie)](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885432.html)

2. **Atomos ProRes RAW (12-Bit Log Companding) vs Blackmagic BRAW (Video Assist 3.22/3.23) Metadata Asymmetry**:
   - **16-Bit Linear -> 12-Bit Log Packing**: Atomos Ninja series recorders ingest Sony's 16-bit linear `[0..65535]` HDMI feed and encode **12-bit non-linear log Apple ProRes RAW / ProRes RAW HQ** `[0..4095]` using a piecewise shadow-linear / highlight-log companding curve that preserves `>= 14.5` stops of scene-linear dynamic range without shadow posterization.
   - **ProRes RAW Metadata (`N3VDF29DevHdmiRawMetaConverterAtomosE`)**: Atomos embeds Sony's `WhiteBalanceKelvin`, `Tint`, `ISO` (`Base 800 / 12800` or `Base 640 / 12800`), `ExposureIndex`, and `ColorMatrix_SGamut3Cine` atoms cleanly for:
     - **Final Cut Pro**: Native Color Temp / Tint & Exposure Offset / ISO sliders.
     - **DaVinci Resolve (`v20.2+`)**: Native ProRes RAW Temp / Tint, `±2 stop` ISO override, and Highlight Recovery.
     - **Adobe Premiere Pro (2026 Source Settings Update)**: Native WB Color Temp, ISO Sensitivity, and Capture Gamma/Gamut controls.
   - **Blackmagic BRAW (`N3VDF39DevHdmiRawMetaConverterBlackmagicDesignE`)**: Supported on FX3 (`Ver. 7.00+`) / FX3A (`Ver. 2.00+`) with Blackmagic Video Assist `12G HDR` (`Ver. 3.22` / `3.23`). Because Sony's HDMI stream omits the full BRAW camera-profile calibration packet, DaVinci Resolve's Camera RAW tab locks ISO, White Balance, and Highlight Recovery to in-camera values while exposing **Decode Gamma / Gamut (`S-Gamut3.Cine / S-Log3`)** — requiring white balance and exposure grading via linear gain / chromatic adaptation nodes.
   - **Dual Base ISO Hardware Boundary**: Analog dual-gain switching (`800 / 12800` in Cine EI; `640 / 12800` in Flexible ISO) occurs in the `IMX510` ADC front-end prior to HDMI serialization; post-production ISO sliders apply digital gain offsets only.
   - Verified Reference: [Blackmagic Design Professional Cameras Support Center](https://www.blackmagicdesign.com/support/family/professional-cameras)

---

### 2. Focus Breathing Compensation (`1.06x..1.13x` Dynamic FOV Crop) & RAW / S&Q Exclusion

1. **Lens Compatibility & Optical Exclusion Rules (Official Sony Compatibility Matrix)**:
   - Focus Breathing Compensation corrects focus-distance (`u_mm`) angle-of-view shifts during movie recording on **ILME-FX3 (`Ver. 3.00+`)**, **ILME-FX3A**, and **ILME-FX6T/FX6V (`Ver. 2.00+`, extended in `Ver. 5.00+`)** across **46+ supported E-Mount G/GM/ZEISS lenses** (including `SEL14F18GM`, `SEL24F14GM`, `SEL35F14GM`, `SEL50F12GM`, `SEL1635GM2`, `SEL2470GM2`, `SEL70200GM2`, `SELP28135G`, `SEL100400GM`, `SEL200600G`, `SEL400800G`).
   - **Explicit Lens/Adapter Exclusions**:
     - Cannot be used when a **teleconverter (`SEL14TC` / `SEL20TC`)** is mounted.
     - Cannot be used on `SEL100F28GM` when the macro switching ring is set to **`0.57m–1.0m`**.
     - **Unchipped manual / PL-adapted lenses** report zero E-Mount 12-pin `DividedInfoBreathingCorrectionData`, requiring strict `1.000x` identity bypass with zero stale GM polynomial leakage.
   - Verified Official References:
     - [Sony Official Compatibility Chart: Breathing Compensation (`fnc=1001`)](https://support.d-imaging.sony.co.jp/www/cscs/function/compatibility.php?fnc=1001&area=gb&lang=en&ref=1)
     - [Sony ILME-FX3 Help Guide: Lens Compensation (`Breathing Comp.`)](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882810.html)

2. **Why HDMI RAW & High-Frame-Rate S&Q Bypass Dynamic FOV Crop**:
   - Breathing Compensation applies a focus-distance-driven **dynamic magnification crop (`~1.06x .. 1.13x`, e.g. `1.000x .. 1.125x`)** inside the `CXD90057` ISP geometric resampler (`BreathingCorrection_AppliedBasePointDistortionRatio` / `MaximumBreathingScaleRatio`), causing a slight change in angle of view and resolution.
   - Because **16-bit HDMI RAW** exports un-demosaiced Bayer sensor readout (`4264 × 2408`) *upstream* of the ISP geometric resampler and **S&Q 120p/240p** hits ISP pixel-throughput ceilings, `[Breathing Comp.]` **must fail-safe bypass (`1.000x`)** whenever `HDMI RAW` or `S&Q 120p+` is active.

---

### 3. 24-Pin MI-Shoe Digital Audio (`48 kHz / 24-bit 4ch`) I2S Master-Clock PLL & NTSC Fractional Sync

1. **MI-Shoe Digital I2S Bus & `XLR-H1` Handle Architecture**:
   - Both FX3 (`XLR-H1` handle unit) and FX6 (`Smart Handle`) carry Sony's **24-pin Multi Interface (MI) Shoe** digital audio interface (`INFRA_HOTSHOE_UIPC_SETCTRL_BCK_LRCK`, `i2s_48k_24bit_4ch`, `4,608,000 bps` uncompressed LPCM across `CH1..CH4`).
   - **Priority & Hardware Exclusions (Official Sony FX3 Help Guide)**:
     - Connecting an analog mic to the body 3.5mm `MIC` jack overrides `[Shoe Audio Set.]`.
     - Switching the handle `DIGITAL/ANALOG` switch or hot-detaching during recording breaks stream continuity (`P11 0x91db059b` `0x88000002` + `libInfraHotshoe.so` `E_TMO = -50 -> 0x8000` handles safe internal-mic fallback).
     - `[Shoe Audio Set.]` is **unavailable during S&Q shooting** (`rec_fps != sensor_fps`).
   - Verified Official References:
     - [Sony ILME-FX3 Help Guide: Shoe Audio Set.](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885442.html)
     - [Sony ILME-FX3 Help Guide: Recording audio using the XLR adaptor of the supplied handle](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000886832.html)

2. **`CXD90057` Fractional-N PLL Clock Coupling (`27.000 MHz / 1.001` vs `48.000 kHz`)**:
   - In NTSC fractional frame rates (`23.976p`, `29.97p`, `59.94p`), the `CXD90057` video timing generator (`MTG`) divides down by `1.001` (`27.000 MHz / 1.001 = 26,973,026.97 Hz`) while the `XLR-H1` I2S ADC remains locked to **exact `48,000 Hz`** word clock (`LRCK`).
   - To maintain `< 0.1 ms` lip-sync drift across a **6-hour (`21,600 s`) continuous take**, the audio PLL locks coherently to the same master crystal (`GENLOCK_CID_PLLLOCK`), producing exact rational sample-per-frame cadences:
     - **`23.976p` (`24000/1001`)**: `48000 * 1001 / 24000 = 2002` exact samples/frame (`0` drift).
     - **`29.97p` (`30000/1001`)**: `48000 * 1001 / 30000 = 1601.6` samples/frame -> **5-frame NTSC cadence `1602, 1601, 1602, 1601, 1602`** (`8,008` samples per 5 frames).
     - **`59.94p` (`60000/1001`)**: `48000 * 1001 / 60000 = 800.8` samples/frame -> **5-frame cadence `801, 801, 801, 801, 800`** (`4,004` samples per 5 frames).
   - Unsynchronized `1000 ppm` crystal slip (`1.001x` mismatch) would cause **`21.578 seconds` (`21,578 ms`)** of lip-sync drift over 6 hours!

---

### 4. Recent Sony Firmware RE, QEMU Virtualization & Solderless eMMC Unbrick Intelligence (2025–2026)

| Project / 项目 | Platform / 平台 | Key Verified Findings / 核心技术进展 | Canonical URL |
| :--- | :--- | :--- | :--- |
| `DavidBuchanan314/ILCE-7M4-RE` | `BIONZ XR` (`CXD90057`) | BootROM `0xffff_0000..0xffff_bfff` (key scrambling table at `0xffff_b800`), `SPACC` `0xf7fc_0000`, eMMC `0xf10d_6000`, `uart_boot` RP2040 injection, AES-XTS partition crypto without signature checks, bare-metal fastboot backup/restore. | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `dino2048/zv-e10-toolkit` | `ZV-E10` (`2.02`/`2.03`) | `2.03` Jiritsu RAM-buffer backup averaging `1.989 MiB/s`, fastboot watchdog bypass enabling persistent single-session eMMC reads/writes beyond ~4 minutes, 16-partition recovery preserving `boot0`/`boot1` and factory calibration. | https://github.com/dino2048/zv-e10-toolkit |
| `cokeenet/zve10-qemu` | `CXD90045` QEMU & Rescue | Full BootROM -> bare-metal fastboot (`18d1:4ee0`) -> stage2 rescue; real brick recovery by clearing `ld.so.preload` size (1-byte BPB repair); TIMER-IP `~3 min 40 s` watchdog disarmed via `WDT_SET_STOP`; QEMU running `im.elf` + `liro` (~280 threads) + software `Render2DWalker` / `OffScreenRender3D`. | https://github.com/cokeenet/zve10-qemu |
| `ma1co/qemu` | Sony BIONZ QEMU Fork | Community QEMU fork supporting Sony camera SoC experimentation. | https://github.com/ma1co/qemu |
| QEMU `eMMC` Device Docs | Multi-Partition eMMC | Standard `boot0`/`boot1`/RPMB/UDA raw image layout guiding clean-room calibration/eMMC zero-mutation boundaries. | https://www.qemu.org/docs/master/system/devices/emmc.html |

---

## 简体中文技术摘要

### 1. 索尼 FX3 / FX6 HDMI 16-Bit 线性 RAW -> Atomos ProRes RAW 与 Blackmagic BRAW 元数据握手

- **机外 16-Bit RAW 输出规格与强制约束**：
  - **ILME-FX3（Ver. 7.02）** 通过全尺寸 HDMI Type-A 输出 **`4264 × 2408` 16-bit 线性 Bayer RAW**（Atomos 可开启 Sony Metadata Crop 裁切为 `4240 × 2385` 16:9），最高支持 **`59.94p`**；**ILME-FX6（Ver. 6.00+ / 6.01）** 同时支持 12G-SDI（`4096×2160` / `3840×2160` 最高 `59.94p`）与 HDMI 2.0 `4264×2408` 16-bit RAW，并于 2026 年 3 月 Ver. 6.00 新增对 Blackmagic RAW HDMI 输出信号的支持。
  - **官方强制门禁**（见 [FX3 RAW 输出帮助指南](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1002078215.html) 与 [HDMI 输出设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885432.html)）：开启 RAW 输出必须先开启 `[Log Shooting]`（非 `Off`），Gamma 锁定为 `S-Log3`；`[HDMI Info. Display]` 强制关闭以防止 OSD 字符污染 Bayer 流；`S&Q` 升格模式强制锁定 `[RAW Output] = Off` 且禁用电子防抖 `SteadyShot [Active]`。
- **16-Bit 线性 -> 12-Bit 非线性 Log 打包与 Atomos / BRAW 元数据差异**：
  - **Atomos ProRes RAW（`N3VDF29DevHdmiRawMetaConverterAtomosE`）**：将 16-bit 线性 `[0..65535]` 经分段暗部线性 + 高光对数曲线压缩打包为 **12-bit Log ProRes RAW / RAW HQ** `[0..4095]`（保留 `>= 14.5` 档动态范围），并将索尼 `WhiteBalanceKelvin`、`Tint`、`ISO`（双原生 `800/12800` 或 `640/12800`）、`ExposureIndex` 及 `ColorMatrix_SGamut3Cine` 写入封装原子，在 Final Cut Pro、DaVinci Resolve `v20.2+` 及 Adobe Premiere Pro（2026 Source Settings 更新）中可原生调节色温、色调与 ISO 曝光偏移。
  - **Blackmagic BRAW（`N3VDF39DevHdmiRawMetaConverterBlackmagicDesignE`）**：FX3 Ver. 7.00+ 配合 Video Assist 12G HDR（`3.22/3.23`）可录制 BRAW，但因索尼 HDMI 码流不包含 BRAW 所需的完整传感器标定包，Resolve 的 Camera RAW 面板会锁定机内白平衡、ISO 与高光恢复，仅开放解码色彩空间（`S-Gamut3.Cine / S-Log3`）。

### 2. 呼吸效应补偿（`1.06x..1.13x` 动态视场裁切）与 HDMI RAW / S&Q 120p 互斥防火墙

- **官方镜头兼容与光学禁用边界**（见 [索尼官方呼吸补偿兼容性列表](https://support.d-imaging.sony.co.jp/www/cscs/function/compatibility.php?fnc=1001&area=gb&lang=en&ref=1) 与 [FX3 镜头补偿指南](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882810.html)）：
  - FX3（`Ver. 3.00+`）、FX3A 及 FX6（`Ver. 2.00+`/`5.00+`）支持超过 46 支原厂 E 卡口镜头（如 `SEL24F14GM`、`SEL35F14GM`、`SEL50F12GM`、`SEL1635GM2`、`SEL2470GM2`、`SEL70200GM2` 等），挂载 **`SEL14TC` / `SEL20TC` 增距镜**、`SEL100F28GM` 微距环置于 `0.57m–1.0m` 或无电子触点手动 PL 镜头时必须强制关闭（严格保持 `1.000x` 无裁切）。
- **与 HDMI RAW / S&Q 120p 的强制互斥**：呼吸补偿依靠 `CXD90057` ISP 几何重采样器随对焦距离 `u_mm` 施加 `1.000x..1.125x` 动态裁切缩放；而 HDMI 16-bit RAW 直接输出未经 ISP 几何重采样的原始 Bayer 数据（S&Q 120p 亦受限于 ISP 吞吐），因此开启 `HDMI RAW` 或 `S&Q 120p` 时必须自动安全旁路（`1.000x`）。

### 3. 24 针 MI 热靴数字音频（`48 kHz / 24-bit 4ch`）I2S 主时钟 PLL 与长录声画同步漂移审计

- **MI 热靴数字接口**：`XLR-H1` 通过 24 针 MI 热靴传输 `48 kHz / 24-bit / 4ch`（`4,608,000 bps`）未压缩 LPCM I2S 音频流（`INFRA_HOTSHOE_UIPC_SETCTRL_BCK_LRCK`，见 [Shoe Audio Set. 指南](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885442.html)）。
- **小数帧率 PLL 锁相数学证明**：NTSC 小数帧率（`23.976p / 29.97p / 59.94p`）下视频主时钟运行于 `27.000 MHz / 1.001`，而音频 ADC 保持精确 `48,000 Hz` 字时钟。在 `29.97p`（`30000/1001 fps`）下，每帧平均音频采样为 `1601.6`（5 帧标准 NTSC 节奏序列 **`1602, 1601, 1602, 1601, 1602`**，合计 `8008` 样本；`59.94p` 下为 `800.8` 样本/帧，`5` 帧 `4004` 样本）。通过 `CXD90057` 同源分数分频 PLL 锁相（`GENLOCK_CID_PLLLOCK`），可确保连续录制 **6 小时（`21,600 s`）** 音画漂移严格 `< 0.1 ms`，并彻底拦截未锁相 `1000 ppm` 晶振失配导致的 `21.578 秒` 灾难性音画不同步。

### 4. 2025–2026 全球索尼固件逆向、QEMU 仿真与免焊接 eMMC 救砖最新进展

- **`cokeenet/zve10-qemu`** 与 **`dino2048/zv-e10-toolkit`**：公开验证了 `BIONZ` 裸机 Fastboot 喂狗绕过（解除约 3 分 40 秒 `TIMER-IP` `WDT_SET_STOP` 重启限制）、单字节修复 BPB `ld.so.preload` 大小字段救砖实测，以及 QEMU 内运行 `im.elf` + `liro`（4-MUSASHI ~280 线程）与纯软件 `Render2DWalker` / `OffScreenRender3D` 遍历，持续印证本实验室“**严格 `os.O_RDONLY` 只读审计 + 出厂 `OB-Clamp` / `psd.bin` / `defdet.bin` / `Backup.bin` / `cnflasha` 零写入防火墙**”的安全性与必要性。
