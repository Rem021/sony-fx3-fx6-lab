# Phase 89 — Wave-9 Global Sony `RTMD` / `Gyroflow` / Anamorphic IBIS / ARM64 IIO IMU Virtualization & Non-Invasive `1.8V` RX-Only Recovery Intelligence Sync

# 第 89 阶段 — Wave-9 全球索尼 `RTMD` / `Gyroflow` / 变形镜头防抖 / ARM64 IIO IMU 虚拟化与非侵入式 `1.8V` 只收串口恢复情报同步

**Date / 日期**: `2026-11-14`  
**Owner / 负责代理**: `gemini-4-hydrogen` (isolated Orca child worktree)  
**Target Lab Auditor / 对应固件实验室审计器**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/metadata_gyro_catalyst_and_anamorphic_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/metadata_gyro_catalyst_and_anamorphic_auditor.py) (`17th` unified auditor)  
**Phase 89 Verification Report / 阶段验收报告**: [`reports/2026-11-14-phase89-gyroflow-rtmd-anamorphic-ibis-auditor/README.md`](../2026-11-14-phase89-gyroflow-rtmd-anamorphic-ibis-auditor/README.md)  
**Safety Redlines / 安全红线**: `os.O_RDONLY` only, `imu_calibration_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`, zero proprietary keys/binaries committed, live port `8768` untouched.

---

## 1. Executive Summary / 执行摘要

**English**:  
Wave-9 synthesizes current public engineering research and open-source ecosystem specifications across three tightly coupled domains that govern FX6-on-FX3 Cinema Line stabilization, metadata interoperability, co-emulation timing, and non-invasive hardware diagnostics:
1. **Sony `RTMD` (`0xE304` / `0xE43B` / `0xE44B`) & `Gyroflow` / `Catalyst Browse` Stabilization**: Verifies the `2000 Hz` 6-axis IMU sample cadence (`83/84` samples/frame at `23.976p`, `80` at `25p`, `33/34` at `59.94p`), `IMX510` full-width `~8.70 ms` 4K readout vs `~4.35 ms` `4K 120p` crop readout, `IBIS = Off (Center-Lock 0x0400)` vs IBIS-aware post-stabilization constraints, and the asymmetric yaw-gain hazard (`f_x = f / S`, `f_y = f`) for `1.3x..2.0x` anamorphic lenses.
2. **ARM64 IMU / IIO (`Industrial I/O`) Sensor Virtualization**: Establishes how upstream Linux/QEMU virtualizes MEMS IMUs (`BMI270` / `ICM-42688-P`) via `VirtIO SCMI` (`CONFIG_IIO_SCMI` / `vhost-device-scmi`) or `vhost-user-i2c`/`spi`/`gpio`, using hardware FIFO timestamps (`Sensortime` / `TMST_RES = 1 us`) and `FSYNC` / `VSYNC` SOF/EOF pulse tagging so KVM/socket jitter does not corrupt visual-inertial phase alignment.
3. **Non-Invasive Camera Recovery & Read-Only Diagnostics**: Documents `1.8 V` RX-only passive UART tapping on Sony's 15-pin Multi/Micro-USB (`Pin 8 UART_TX`, `Pin 9 UART_RX / BOOT_IN`, `Pin 7 XRESET_REQ`) with host `TX` strictly open/disconnected so BootROM `48000 baud` `uart_boot` is never accidentally latched, paired with official blind SD/CFexpress `BODYDATA.DAT` recovery (`nflasha1`).

**中文摘要**：  
Wave-9 汇总并同步了围绕索尼 FX6-on-FX3 电影机防抖、元数据互操作、QEMU 协同仿真时序与非侵入式硬件诊断的三大前沿公开技术研究：
1. **索尼 `RTMD`（`0xE304` / `0xE43B` / `0xE44B`）与 `Gyroflow` / `Catalyst Browse` 增稳**：明确 `2000 Hz` 六轴 IMU 采样率（`23.976p` 每帧 `83/84` 样本、`25p` 精确 `80` 样本、`59.94p` `33/34` 样本）、`IMX510` 全画幅 4K `~8.70 ms` 与 `4K 120p` `~4.35 ms` 卷帘快门读出时长、`IBIS = Off（0x0400 中心锁定）` 与带 IBIS 元数据感知的后期增稳约束，以及 `1.3x..2.0x` 变形镜头在 5 轴机身防抖上的水平偏航过驱动隐患（必须按 $f_x = f / S, f_y = f$ 非对称补偿或回退 `0x0400` 中心锁定）。
2. **ARM64 IMU / IIO（`Industrial I/O`）传感器虚拟化**：明确 QEMU/Linux 生态通过 `VirtIO SCMI`（`CONFIG_IIO_SCMI` / `vhost-device-scmi`）或 `vhost-user-i2c`/`spi`/`gpio` 虚拟化 `BMI270` / `ICM-42688-P` 六轴传感器，并依托硬件带时间戳 FIFO（`Sensortime` / `1 us` `TMST_RES`）与相机 `VSYNC` SOF/EOF `FSYNC` 脉冲标记，消除虚拟化中断与套接字抖动对视惯同步的破坏。
3. **非侵入式相机恢复与只读诊断**：明确索尼 15 针 Multi/Micro-USB 接口（`Pin 8 UART_TX`、`Pin 9 UART_RX / BOOT_IN`、`Pin 7 XRESET_REQ`）的 `1.8 V` 只收（RX-only）被动串口监听规范——宿主适配器 `TX` 必须悬空断开以防误触发 BootROM `48000 baud` `uart_boot`，并结合官方 SD/CFexpress `BODYDATA.DAT` 盲刷恢复链路（`nflasha1`）。

---

## 2. Pillar 1 Intel: Sony `RTMD` (`0xE304` / `0xE4xx`), `Gyroflow`, `IMX510` Rolling Shutter & Anamorphic IBIS

### 2.1 Open-Source `Gyroflow` (`telemetry-parser` & `sony.rs`) Reverse-Engineering Synthesis

| Technical Axis / 技术维度 | Public Spec & Observed Reality / 公开规范与实测事实 | Lab & Firmware Engineering Takeaway / 实验室工程结论 |
|---|---|---|
| **RTMD Container & `telemetry-parser`** | Gyroflow delegates container parsing to the pure-Rust [`AdrianEddy/telemetry-parser`](https://github.com/AdrianEddy/telemetry-parser) crate (with `gyro2bb --dump` CLI & PyPI bindings), extracting Sony MP4 `rtmd` timed metadata tracks (`src/core/gyro_source/sony.rs`). | Matches Sony `libmpr.so` `mpr::KlvConverter` (`Rdd18KeyCameraUnit`, `Rdd18KeyLensUnit`, `UDAMKeyUnit`, `UDAMSetGyroscopeValue`, `UDAMSetAccelerometerValue`). |
| **RTMD KLV Tags (`0xE304`, `0xE43B`, `0xE44B`)** | ExifTool / `telemetry-parser` decode exposure/time tags (`0x8000` FNumber, `0x8106` FrameRate, `0x8109` ExposureTime, `0x810B` ISO, `0xE303` WhiteBalance, `0xE304` DateTime/unit tag) and **`0xE4xx` IMU motion blocks**: **`0xE43B`** (`PitchRollYaw` / Gyroscope) and **`0xE44B`** (`Accelerometer`), plus `LensDistortion` & focal/zoom records. | Phase 37/89 `RTMD` KLV verifier validates both `0xE43B`/`0xE44B` raw 2000 Hz sample blocks and our `0xE304` IBIS Center-Lock coherence payload (`0x000F`). |
| **`2000 Hz` IMU Cadence** | Sony FX3 / FX6 sample internal 6-axis MEMS IMU at **`2000 Hz`** (~2,000 ~30-byte samples/s vs GoPro 200 Hz, DJI/Insta360 1000 Hz). Standard modes embed full telemetry; certain S&Q / high-speed modes omit gyro metadata. | Rational sample accumulator `((n+1)*2000*den)//num - (n*2000*den)//num` guarantees exact per-frame counts (`83/84` @ `23.976p`, `80` @ `25p`, `33/34` @ `59.94p`, `16/17` @ `119.88p`) with zero drift. |
| **`IMX510` Rolling-Shutter Readout** | FX3, FX6, a7S III, and ZV-E1 share the **IMX510** 48 MP Quad Bayer (`2x2` binned -> 12 MP / 10.2 MP 16:9) BSI CMOS. Full-width 4K readout (24–60p / 100p) is **`~8.70 ms`**; `4K 120p` (~1.1x crop) drops to **`~4.35 ms`**; `FHD 240p` drops to **`~2.20 ms`**. | FX6 `libmpr.so` (`MetaConverterImpl::ConvertReadoutDuration`, `NormalImageControl_EffectivePixelReadoutTime`) must stamp mode-accurate readout durations so `rs-sync` & skew correction never over/under-shear verticals. |
| **IBIS-Off (`0x0400`) vs IBIS-On** | Gyroflow v1.6/v1.7 added support for Sony IBIS/OIS/EIS + lens breathing metadata (`Standard` IBIS recommended if IBIS is enabled, avoiding `Active`/`Dynamic Active` crop). However, **preview jitter** and optical-center translation still occur whenever IBIS shifts the sensor relative to a fixed lens distortion center. | **Deterministic Rule**: For **full 3D Gyroflow lens-profile stabilization** (requiring fixed optical center for radial distortion + perspective warp), enforce **`IBIS = Off (Center-Lock 0x0400 -> 0x1400)`**; allow `Standard`/`Active` only under IBIS-metadata-aware `GYROFLOW_V17_IBIS_METADATA_AWARE` or `Catalyst Browse`. |
| **Anamorphic (`1.3x..2.0x`) Stabilization Pitfalls** | Anamorphic optics produce non-isotropic camera matrices (`fx != fy`). Standalone Gyroflow (`gyroflow#809`) requires custom aspect calibration, while `gyroflow-plugins` OpenFX (PR #63 / #186 `AddAnamorphicMode` + DaVinci Resolve stretch-disable) explicitly handles squeeze factor `S`. | **FX6 vs FX3 Physical Divergence**: FX6 `De-Squeeze` (`1.3x`/`2.0x`) is **display-monitoring-only** (rigid CMOS, `PRM_is_imager_stabilization_unit_fixed`). On FX3's physical 5-axis IBIS, feeding spherical focal length `f` to yaw over-drives horizontal translation by **`S x`** (`100%` error at `2.0x`!). Safe containment requires `f_x = f / S, f_y = f` OR auto-engaging `IBIS = Off (Center-Lock 0x0400)` for manual anamorphics. |

**Verified Public Citations / 已核验公开参考链接**:
- Gyroflow Documentation — Supported Cameras (Sony FX3/FX6, 2000 Hz IMU, IBIS/OIS/EIS & Breathing Comp.): <https://docs.gyroflow.xyz/app/getting-started/supported-cameras/sony>
- Gyroflow `telemetry-parser` (Pure-Rust Sony `rtmd` / GPMF / Blackbox Parser & Python Bindings): <https://github.com/AdrianEddy/telemetry-parser>
- ExifTool Sony `rtmd` Tag Reference (`0xE304`, `0xE43B`, `0xE44B`, exposure & lens tags): <https://exiftool.org/TagNames/Sony.html>
- Gyroflow Rolling-Shutter Calibration & `rs-sync` Documentation: <https://docs.gyroflow.xyz/app/getting-started/basic-usage/synchronization> & <https://github.com/gyroflow/rollingshutter>
- Gyroflow Anamorphic Issues & OpenFX `AddAnamorphicMode` (`gyroflow#809`, `gyroflow-plugins`): <https://github.com/gyroflow/gyroflow/issues/809> & <https://github.com/gyroflow/gyroflow-plugins>
- CineD Lab Test — Sony FX3 / FX6 `IMX510` Rolling Shutter (`8.7 ms` 4K readout): <https://www.cined.com/sony-fx3-lab-test-rolling-shutter-dynamic-range-and-latitude/>

---

## 3. Pillar 2 Intel: ARM64 IMU / IIO (`Industrial I/O`) Sensor Virtualization

### 3.1 VirtIO / QEMU Sensor Virtualization & Deterministic `VSYNC` Timestamping

| Virtualization Layer / 虚拟化层级 | Upstream QEMU / Linux Mechanism / 上游机制 | Engineering Relevance to FX3/FX6 Co-Emulation / 对 FX3/FX6 仿真的工程意义 |
|---|---|---|
| **Protocol-Level: `VirtIO SCMI` + Linux `IIO SCMI`** | OASIS VirtIO v1.2/v1.3 Section 5.17 defines `virtio-scmi`; Linux uses `virtio_scmi` + `CONFIG_IIO_SCMI` (`/sys/bus/iio/devices/iio:deviceX`). QEMU `-device vhost-user-scmi-pci` pairs with `rust-vmm/vhost-device-scmi` (`-d iio,...` or synthetic mock channels). | Cleanest high-level abstraction for injecting synthetic `2000 Hz` accel/gyro streams into an ARM64 Linux guest without low-level SPI/I2C bit-banging overhead. |
| **Bus-Level: `vhost-user-i2c` / `vhost-user-spi` / `vhost-user-gpio`** | OASIS VirtIO v1.2 Sec. 5.16 (`i2c-virtio.c`, `CONFIG_I2C_VIRTIO`), `spi-virtio.c` (`CONFIG_SPI_VIRTIO`), and `vhost-user-gpio-pci` (`libgpiod`) proxy I2C/SPI transfers and GPIO `INT`/`FSYNC` edges. Custom software-only IMUs in QEMU require an `I2CSlave` or SPI peripheral attached to the SoC bus controller. | Mirrors Stock-CP (`cpapp-b.bin`) SPI/I2C MEMS polling and allows deterministic fault/disconnect testing without real hardware. |
| **Bosch `BMI270` (`drivers/iio/imu/bmi270/`)** | SPI up to 10 MHz / I2C, up to 6.4 kHz gyro / 1.6 kHz accel ODR, 2–6 KB hardware FIFO, `Sensortime` (< 40 us host-IMU alignment), and `FIFO_CONFIG_1.fifo_tag_int1_en` / `int2_en` external sync frame tagging. | Reference model for `INT1`/`INT2` VSYNC edge tagging directly inside the IMU FIFO stream. |
| **TDK InvenSense `ICM-42688-P` (`drivers/iio/imu/inv_icm42600/`)** | SPI up to 24 MHz / I3C 12.5 MHz, up to 32 kHz ODR, 20-bit high-res FIFO, **`1 us` FIFO timestamps (`TMST_RES = 0`)**, and Pin 9 multiplexed **`FSYNC` (camera VSYNC frame boundary)** or **`CLKIN` (32.768 kHz RTC clock)**. Linux `inv_icm42600_timestamp.c` (`inv_icm42600_timestamp_apply_odr`) smooths interrupt jitter. | **Ideal Co-Emulation Timing Pattern**: Injected `2000 Hz` IMU FIFO packets carry monotonic `1 us` hardware timestamps + `FSYNC` camera `VSYNC` SOF/EOF markers so KVM exits and `vhost-user` `eventfd`/`irqfd` latency cannot skew gyro-to-frame sync. |

**Verified Public Citations / 已核验公开参考链接**:
- OASIS VirtIO Specification v1.2 / v1.3 (`virtio-i2c` Sec. 5.16, `virtio-scmi` Sec. 5.17): <https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html>
- QEMU `vhost-user` Devices (`vhost-user-i2c`, `vhost-user-spi`, `vhost-user-gpio`, `vhost-user-scmi`): <https://www.qemu.org/docs/master/system/devices/vhost-user.html>
- `rust-vmm/vhost-device` (`vhost-device-scmi`, `vhost-device-i2c`, `vhost-device-spi`, `vhost-device-gpio`): <https://github.com/rust-vmm/vhost-device>
- Linux Kernel IIO Core, `inv_icm42600` (`inv_icm42600_timestamp.c`) & `bmi270`: <https://docs.kernel.org/driver-api/iio/buffers.html>
- TDK InvenSense `ICM-42688-P` Datasheet (`FSYNC`, `CLKIN`, `TMST_RES`): <https://invensense.tdk.com/products/motion-tracking/6-axis/icm-42688-p/>
- Bosch Sensortec `BMI270` Datasheet (`Sensortime`, `fifo_tag_int1_en`): <https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi270/>

---

## 4. Pillar 3 Intel: Non-Invasive `1.8V` RX-Only UART Boot Tapping & Safe SD Recovery

### 4.1 Sony Multi/Micro-USB Pinout & `1.8 V` RX-Only Passive Tap Discipline

| Pin / 引脚 | Signal / 信号 | Electrical & BootROM Constraint / 电气与 BootROM 约束 | Safe Diagnostic Rule / 安全诊断规则 |
|---|---|---|---|
| **Pin 5 / 14** | `GND` / `AV_GND` | Common signal reference | Connect first before probing any UART pin. |
| **Pin 7** | `XRESET_REQ` | Power/reset control input | Leave untouched during passive RX-only monitoring. |
| **Pin 8** | **`UART_TX`** (Camera -> Host) | **1.8 V logic domain** (idles high near `~1.8 V`; 3.3 V push-pull risks SoC ESD/IO damage) | Connect **ONLY host adapter `RX`** via native `1.8 V` `VCCIO` FTDI (`FT232H`/`FT4232H`/`FT232RNL`) or `LSF0108` level shifter + `470 Ω..1 kΩ` series resistor. |
| **Pin 9** | **`UART_RX` / `BOOT_IN`** (Host -> Camera) | Sampled by BIONZ XR BootROM immediately post-reset at **`48000 baud`** (`0x100D` 13-blink parity error on invalid data; `115200 baud` `[mira] fastboot ready` after signed SRAM loader). | **HOST ADAPTER `TX` MUST REMAIN OPEN / DISCONNECTED** during passive boot logging so BootROM `uart_boot` is NEVER accidentally latched! Active recovery uses `-DOPEN_DRAIN` only under explicit Tier-3/H0 gate. |

### 4.2 Non-Invasive Blind SD / CFexpress Recovery (`BODYDATA.DAT`)
- **FX6 (`ILME-FX6`)**: Strip all accessories (`SDI/HDMI`, handle, grip, third-party plates), power strictly via official Sony DC-IN AC adapter, format exFAT card with **only** official `BODYDATA.DAT` (exact filename, no `(1)` suffix) in **Media Slot A** root, power on, and monitor Slot A LED while screen remains dark.
- **FX3 (`ILME-FX3`)**: Place **only** `BODYDATA.DAT` in **Slot 1** root with a charged battery, power on (community/Sony recovery includes 30s shutter-hold and `1 -> 3 -> 5` blink sequence monitoring; wait 5 min with battery/card removed before retrying if blink stalls).
- **Updater Architecture (`nflasha1`)**: `BODYDATA.DAT` updates boot into FAT12 recovery partition `nflasha1` (`/boot/initrd.img` zlib SquashFS 4.0 + `libsdfileinputupdaterapi.so` / `sdfileinput.elf` signature verification), completely separate from factory calibration (`cnflasha` / `p2:/Backup.bin` / `p2:/psd.bin` / `p6:Jiritsu`).

**Verified Public Citations / 已核验公开参考链接**:
- `DavidBuchanan314/ILCE-7M4-RE` (BIONZ XR BootROM `48000 baud` `uart_boot`, `115200 baud` `fastboot`, `nflasha` analysis): <https://github.com/DavidBuchanan314/ILCE-7M4-RE>
- `Erlla/sony-a7m4-custom-firmware` (`docs/wiring.md`, `-DOPEN_DRAIN` 1.8V safety): <https://github.com/Erlla/sony-a7m4-custom-firmware>
- `cokeenet/zve10-qemu` (`docs/ANTIBRICK_SYSTEM.md`, `BODYDATA.DAT` & `nflasha1` recovery analysis): <https://github.com/cokeenet/zve10-qemu>
- `xyzhangxin/sony-a6700-powerful` (470 Ω / 56 kΩ open-drain protection): <https://github.com/xyzhangxin/sony-a6700-powerful>
- `gyroflow/flowshutter` (`doc/sony-multi-terminal.md` 15-pin Multi-terminal reference): <https://github.com/gyroflow/flowshutter>
- `ma1co/Sony-PMCA-RE` & `masterflai/pmca-re-reloaded`: <https://github.com/ma1co/Sony-PMCA-RE>
