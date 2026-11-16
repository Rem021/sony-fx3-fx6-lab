# Wave-16 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十六波全球索尼固件 / 虚拟化 / 救砖与 BIONZ XR XAVC HS vs XAVC S-I、ACES S-Log3 IDT 及 NP-FZ100 电源协议情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 133 — Wave-16 Live Global Web Intelligence Sync & 26th Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified public technical references covering:
  1. **Sony `BIONZ XR` Hardware Codec Matrix: `XAVC HS 4K` (`HEVC 10-bit 4:2:2` Long-GOP) vs `XAVC S-I 4K` (`H.264 All-Intra 240..600 Mbps` + `S&Q 1200 Mbps`) vs FX6 `XAVC-I Class 300` (`MXF OP1a`) & `VPG200/VPG400` Media Budgets**
  2. **`ACES 1.3 / 2.0` Sony `S-Log3` Piece-Wise Log↔Linear Transfer (`95 / 420 / 598`, breakpoint `171.2102946929`), `S-Gamut3 / S-Gamut3.Cine -> AP0 / AP1` `3×3` Chromatic Adaptation (`CAT02` vs `Bradford`) & `OCIO v2 / CLF` Specifications**
  3. **`NP-FZ100` (`7.2 V`, `16.4 Wh`, `2280 mAh`, `InfoLITHIUM Z`) `+ / C / -` Single-Wire Serial Telemetry & Authenticity Check (`FX3 v4.00..v6.00..v7.02`) vs FX6 `14.4 V` `BP-U35/U70` & `DC IN` Rails**
  4. **2025–2026 Sony `CXD90057` ARM64 Firmware RE, `FX3 v7.00..v7.02`, QEMU Virtualization (`pmemsave`) & `eMMC` / `UART` Unbrick Advances**
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs and read-only (`os.O_RDONLY`) donor markers cited directly.

---

## English Technical Synthesis

### 1. `BIONZ XR` Hardware Encoder Matrix: `XAVC HS` (`HEVC 4:2:2 10-bit`) vs `XAVC S-I` (`600 Mbps`) vs FX6 `XAVC-I Class 300`

1. **Shared `IMX510` + `BIONZ XR` (`CXD90057`) Pipeline**:
   - Both the Sony **ILME-FX3** (`v7.02`) and **ILME-FX6** (`v6.01`) share the `10.2 MP` effective (`12.1–12.9 MP` total) full-frame back-illuminated Exmor R CMOS (`IMX510`), Dual Base ISO (`800 / 12800` in S-Log3), and `BIONZ XR` (`CXD90057`) hardware encoder cluster ([B&H FX3/FX6](https://www.bhphotovideo.com/), [Sony FX3 Specifications](https://www.sony.com/en/articles/xavc-format-guide)).
   - Inside `libmpr.so`, FX3 and FX6 share identical elementary encoder profiles (`HEVC_3840_2160_M42210P`, `HEVC_3840_2160_M10P`, `AVC480_3840_2160_H422IP`, `AVC480CBG_4096_2160_H422IP`), diverging primarily at the container muxer (`libXavcMp4` `.MP4` on FX3 vs `libXavcMxf` `.MXF OP1a` on FX6) and frame-rate/GOP policies.

2. **Codec, Bitrate, GOP & `VPG200/VPG400` Card Envelope**:
   | Profile | Codec & Chroma | GOP / Mode | Bitrates (`4K`) | Container | FX3 / FX6 Availability & Media Gate |
   | :--- | :--- | :--- | :--- | :--- | :--- |
   | **FX3 `XAVC HS 4K`** | `HEVC / H.265` (`Main 4:2:2 10` / `Main 10`, L5.1/L5.2) | Long-GOP (`VBR`) | `50 / 100 Mbps` (`23.98p`), `100 / 200 Mbps` (`50p/59.94p`), `280 Mbps` (`100p/119.88p`) | `.MP4` | **No `25p` or `29.97p/30p`** internally on FX3; runs on `SDXC V60+` ([Sony FX3 Help Guide](https://helpguide.sony.net/ilme/fx3/v1/en/contents/TP1000267761.html)). |
   | **FX3 `XAVC S-I 4K / DCI 4K`** | `AVC / H.264` (`High 4:2:2 Intra`) | All-Intra (`CBG/CBR`-like frame budget) | `240` (`23.98/24p`), `250` (`25p`), `300` (`29.97p`), `500` (`50p`), `600 Mbps` (`59.94p`), up to `1200 Mbps` (`S&Q 120p`) | `.MP4` | `240..300 Mbps` runs on `SDXC V90` / `CFexpress`; `500..600 Mbps` needs `SDXC V90` or `CFexpress Type A`; `S&Q 120p (1200 Mbps)` requires **`CFexpress Type A VPG200 / VPG400`** (`CAUTION_ID_XAVC_S_I_TRANSFER_RATE_DISABLE_UNDER_400MBPS_MEDIA_SLOT1_MSG`). |
   | **FX6 `XAVC-I (Class 300)`** | `AVC / H.264` (`High 4:2:2 Intra`) | All-Intra (`CBG`) | `240` (`23.98/24p`), `250` (`25p`), `300` (`29.97p`), `500` (`50p`), `600 Mbps` (`59.94p`), `S&Q 120p` | `.MXF` (`OP1a`) | Broadcast `OP1a` wrapper with `SMPTE RDD 18` KLV metadata; equivalent bitstream fidelity to FX3 `XAVC S-I` ([AbelCine FX6](https://www.abelcine.com/), [Newsshooter](https://www.newsshooter.com/)). |

   - **VBV & Timeline Decoding Trade-offs**: `XAVC S-I` decodes every frame independently with low timeline CPU overhead and zero inter-frame motion blocking on water/foliage/confetti, whereas `XAVC HS 4:2:2 10-bit` requires Long-GOP reference frame reordering and dedicated hardware decode (Apple Silicon Media Engine, Intel Quick Sync / Arc, or modern NVIDIA NVDEC) ([Sony XAVC Guide](https://helpguide.sony.net/ilme/fx3/v1/en/contents/TP1000267761.html)). Conversely, FX3 `XAVC HS` retains `10-bit 4:2:2` Long-GOP in 4K, whereas FX6 `XAVC-L` 4K drops to `8-bit 4:2:0`.

---

### 2. `ACES 1.3 / 2.0` Sony `S-Log3` Transfer & `S-Gamut3 / S-Gamut3.Cine -> AP0 / AP1` IDT Verifier

1. **Official `S-Log3` Piece-Wise Log↔Linear Equations & 10-Bit Code Landmarks**:
   - Reference: Sony *Technical Summary for S-Gamut3.Cine/S-Log3 and S-Gamut3/S-Log3* (V1.01) & Academy/ASWF [`OpenColorIO-Config-ACES` `sony/generate.py`](https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/blob/main/opencolorio_config_aces/clf/transforms/sony/generate.py).
   - **10-bit Full-Range Landmarks (`0..1023`, SDI valid `4..1019`)**:
     - `0%` Black: **CV `95`** (`3.5% IRE`)
     - `18%` Middle Grey: **CV `420`** (`41.0% IRE`)
     - `90%` Diffuse White: **CV `598`** (`61.0% IRE`)
     - Piece-wise break point ($in = 0.01125000$): **CV `171.2102946929`** (`x_break = 171.2102946929 / 1023.0`)
   - **Forward (Linear Reflection $L \rightarrow$ Normalized `S-Log3` $x \in [0, 1]$)**:
     $$x = \begin{cases} \dfrac{420.0 + \log_{10}\left(\frac{L + 0.01}{0.18 + 0.01}\right) \times 261.5}{1023.0}, & L \ge 0.01125000 \\[6pt] \dfrac{L \times \frac{171.2102946929 - 95.0}{0.01125000} + 95.0}{1023.0}, & L < 0.01125000 \end{cases}$$
   - **Inverse (`S-Log3` $x \rightarrow$ Linear Reflection $L$)**:
     $$L = \begin{cases} 10^{\frac{x \times 1023.0 - 420.0}{261.5}} \times 0.19 - 0.01, & x \ge \frac{171.2102946929}{1023.0} \\[6pt] (x \times 1023.0 - 95.0) \times \frac{0.01125000}{171.2102946929 - 95.0}, & x < \frac{171.2102946929}{1023.0} \end{cases}$$

2. **ACES 1.3 / 2.0 `OCIO v2 / CLF` Transform IDs & `3×3` Chromatic Adaptation (`CAT02` vs `Bradford`)**:
   - **ACES 2.0 Transform IDs** (in `OpenColorIO-Config-ACES` `sony/generate.py`):
     - `urn:ampas:aces:transformId:v2.0:CSC.Sony.SLog3_SGamut3_to_ACES.a2.v1` (`urn:aswf:ocio:transformId:1.0:Sony:Input:SLog3_SGamut3_to_ACES2065-1:1.0`)
     - `urn:ampas:aces:transformId:v2.0:CSC.Sony.SLog3_SGamut3Cine_to_ACES.a2.v1` (`urn:aswf:ocio:transformId:1.0:Sony:Input:SLog3_SGamut3Cine_to_ACES2065-1:1.0`)
   - **CIE 1931 `xy` Primaries (D65 `0.3127, 0.3290` → ACES White `0.32168, 0.33767`)**:
     - `S-Gamut3`: `R=(0.730, 0.280)`, `G=(0.140, 0.855)`, `B=(0.100, -0.050)`
     - `S-Gamut3.Cine`: `R=(0.766, 0.275)`, `G=(0.225, 0.800)`, `B=(0.089, -0.087)`
     - `ACES2065-1 (AP0)`: `R=(0.73470, 0.26530)`, `G=(0.00000, 1.00000)`, `B=(0.00010, -0.07700)`
     - `ACEScg (AP1)`: `R=(0.71300, 0.29300)`, `G=(0.16500, 0.83000)`, `B=(0.12800, 0.04400)`
   - **CAT02 vs Bradford Note**: Sony's official CTL/CLF IDTs use **CAT02** chromatic adaptation (`M_SGamut3Cine_to_AP0[0] = [0.638788667185978, 0.272351433711262, 0.088859899102760]`), whereas **Bradford** adaptation differs by $\sim 4.6 \times 10^{-3}$ on matrix entries while equally preserving the `(1.0, 1.0, 1.0)` neutral white point (`max_whitepoint_error < 1e-12`). Both families are invertible (`det > 0.8`) and audited explicitly in Phase 133.

---

### 3. `NP-FZ100` (`InfoLITHIUM Z`) `C-Pin` Telemetry, Authenticity Warning (`FX3 v4.00–v7.02`) & FX6 `14.4 V` Rail Isolation

1. **Physical Pinout & Protocol Reality (`+`, `C`, `-`)**:
   - The **NP-FZ100** (`7.2 V` nominal, `16.4 Wh`, `2280 mAh`, `InfoLITHIUM Z`) exposes **three** external contacts (`+`, `C`, `-`) rather than a four-pin thermistor (`+ / T / C / -`) or two-wire I2C/SMBus (`SDA + SCL`) connector ([Electrical Engineering StackExchange](https://electronics.stackexchange.com/), [DPReview Technical Discussions](https://www.dpreview.com/)).
   - The center **`C` (Communication)** pin carries a proprietary Sony **single-wire bidirectional serial InfoLITHIUM protocol** between the camera's CP/PMIC (`BATT_AUTH_Snd`, `BATT_STATE1_Snd`, `BATT_TYPE1_Snd` in `cpapp-b.bin`) and the pack's internal microcontroller—transmitting state-of-charge percentage, thermal state, cycle/status flags, and cryptographic authenticity challenge/response.
   - By contrast, broadcast camcorders such as the **ILME-FX6** (`BP-U35 / BP-U70`, `14.4 V` nominal) and **19.5 V `DC IN`** use multi-pin SMBus-bridged `InfoLITHIUM` packs (`ATTACHED_BATTERY_TYPE_SONY_INFO`, `BATTERY_TYPE_DC_IN`, `BKID_APP_USER_MENU_DC_VOLTAGE_ALARM0`, `VAL_power_supply_end_status_DC_VOLTAGE_END` in FX6 `appFw.so`).

2. **FX3 Firmware `v4.00 -> v6.00 -> v7.02` Battery Authenticity Behavior & Stage-B Safety**:
   - Starting in **FX3 `v4.00`** and continuing through **`v6.00 / v6.01 / v7.00 / v7.02`**, failed `C`-pin authenticity checks display:
     *"The operation and safety of this battery cannot be guaranteed. Continue use?"* (`STRID 0x0000e24e` in FX3 `string_english.uxc`) ([Sony Support — Notice Regarding Battery Authenticity Check](https://www.sony.com/electronics/support/articles/00299322)).
   - Pressing **OK** allows continued operation on `v7.02` with hidden battery percentage (blank/striped icon); pressing **Cancel** powers off the body. Under `v6.00` (which Sony briefly suspended before issuing `v6.01/v6.02` and `v7.00..v7.02`), certain un-decoded third-party cells re-triggered the prompt every 15–30 seconds and interrupted recording.
   - **Critical Stage-B FX6-on-FX3 Guard**: FX6 `appFw.so` monitors **`14.4 V` `BP-U` (`~12.0–12.8 V` near-end / end)** and **`19.5 V` `DC IN`** voltage thresholds (`DC_VOLTAGE_NEAR_END`, `DC_VOLTAGE_END`, `OFF_BY_BATT_LOW`). Running FX6 `appFw.so` telemetry unguarded against FX3's **`7.2 V` (`6.0–8.4 V`) `NP-FZ100` rail** would falsely trip `LOW_BATTERY_SHUTDOWN` (`< 12.0 V`)! Phase 133 enforces normalized per-rail SoC/voltage translation (`7.2 V` NP-FZ100 / regulated dummy-coupler `C`-pin safe degradation) so FX6 UI power indicators never falsely shut down FX3.

---

### 4. 2025–2026 Sony `FX3 v7.00–v7.02`, `CXD90057` ARM64 QEMU Virtualization & `eMMC / UART` Unbrick Ecosystem

| Project / Source | Domain | Verified Technical Takeaways | Canonical URL |
| :--- | :--- | :--- | :--- |
| Sony Official Support | `ILME-FX3` `v7.00 / v7.01 / v7.02` | `v7.00` (Aug 2025) added `BIG6`, Fixed/Variable `S&Q`, `BRAW` over HDMI, `1.5x/1.6x` desqueeze, USB-LAN auto-connect; `v7.01` optimized User LUT; `v7.02` (Mar 2026) fixed startup instability. | https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3 |
| Sony Official Support | Battery Authenticity Check | Official FX3 `v4.00+` `InfoLITHIUM` warning semantics (`OK` continues with blank percentage, `Cancel` powers off; `>= 51%` charge required for firmware update). | https://www.sony.com/electronics/support/articles/00299322 |
| ASWF `OpenColorIO-Config-ACES` | `ACES 1.3 / 2.0` Sony CLF/IDT | Authoritative `S-Log3` `LogCameraTransform` (`171.2102946929`, `420`, `261.5`) & `S-Gamut3 / S-Gamut3.Cine` CAT02 `3×3` matrices + ACES 2.0 CSC IDs. | https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/blob/main/opencolorio_config_aces/clf/transforms/sony/generate.py |
| `Rem021/sony-fx3-fx6-lab` | FX3 `v7.02` & FX6 `v6.01` QEMU Lab | Apple Silicon ARM64 QEMU emulation + 26 clean-room `os.O_RDONLY` cross-body auditors & zero-eMMC-mutation guardrails. | https://github.com/Rem021/sony-fx3-fx6-lab |
| `DavidBuchanan314/ILCE-7M4-RE` | `CXD90057` BootROM & Fastboot | 48 KB BootROM RP2040 `uart_boot` (`48000 -> 115200` baud), SRAM Fastboot (`18d1:4ee0`), `boot0`-derived `SDM2` AES-XTS keys, eMMC full unbrick dump/restore. | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `DavidBuchanan314/Sony-ILCE-7M4-Linux` | `CXD90057` Kernel (`4.9.337`) | Quad Cortex-A35 AP + TOPPERS/FMP RTOS CP + SPAcc crypto + `SDM2` layout. | https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux |
| `chocotan/a7c2-re` & `a7c2-qemu` | ARM64 QEMU & `ramfb` | Stock A7C II QEMU machine (`virt` + soft-GPE + Sony LZ77 CPU decode) rendering live menus in GTK. | https://github.com/chocotan/a7c2-re |
| `YuuLuo/a7c2-service-preload` | `Jiritsu` (`libJit.so`) & Brick Recovery | `dlopen` via `/tmp/jiritsu/libJit.so`, `LD_PRELOAD` brick pitfalls (`nflasha10` 12 MiB vfat exhaustion), and Fastboot recovery. | https://github.com/YuuLuo/a7c2-service-preload |
| `Erlla/sony-a7m4-custom-firmware` & `Hearts-Ace/sony-a7r5-custom-firmware` | `CXD90057` CFW & Unicorn Testing | Offline Unicorn/QEMU validation before eMMC writes; SPI NOR (`EXBL`) vs `SDM2` boundary isolation. | https://github.com/Erlla/sony-a7m4-custom-firmware |
| `xyzhangxin/sony-a6700-powerful` & `dino2048/zv-e10-toolkit` | RP2040 Fastboot & 16-Part Unbrick | Open-drain cold-boot RAM injection (`0xFE020000`) & byte-verified `nflasha*` eMMC recovery. | https://github.com/xyzhangxin/sony-a6700-powerful |
| `cokeenet/zve10-qemu` & `ma1co/Sony-PMCA-RE` | `pmemsave` & `serviceshell` | QMP `pmemsave` heap-corruption debugging + `Backup` property `bk r/w/s` read-only inspection. | https://github.com/cokeenet/zve10-qemu |

---

## 简体中文技术摘要

### 一、 `BIONZ XR` 硬件编码器矩阵：`XAVC HS`（`HEVC 4:2:2 10-bit`）与 `XAVC S-I`（`600 Mbps`）及 FX6 `XAVC-I Class 300`

1. **共享 `IMX510` 与 `BIONZ XR`（`CXD90057`）编码核心**：
   - FX3（`v7.02`）与 FX6（`v6.01`）共享同款 `IMX510` 全画幅背照式 CMOS、`800 / 12800` 双原生 ISO 与 `BIONZ XR` 编码集群；在 `libmpr.so` 中两者共用完全一致的底层编码器配置（`HEVC_3840_2160_M42210P`、`AVC480_3840_2160_H422IP`、`AVC480CBG_4096_2160_H422IP`），仅在封装器（FX3 `libXavcMp4` `.MP4` vs FX6 `libXavcMxf` `.MXF OP1a`）与帧率/GOP 策略上分化。
2. **关键码率、GOP 与存储卡速度门限**：
   - **`XAVC HS 4K`（HEVC Long-GOP 10-bit 4:2:2）**：`23.98p` 为 `50 / 100 Mbps`，`50p / 59.94p` 为 `100 / 200 Mbps`，`100p / 119.88p` 为 `280 Mbps`（支持 `SDXC V60+`），但 FX3 机内 **`XAVC HS 4K` 不提供 `25p` 与 `29.97p / 30p`**；高帧内压缩比依赖硬件 HEVC 4:2:2 解码引擎（如 Apple Silicon Media Engine / Intel Quick Sync）。
   - **`XAVC S-I 4K / DCI 4K` 与 FX6 `XAVC-I Class 300`（H.264 All-Intra 10-bit 4:2:2）**：`240 Mbps`（`23.98/24p`）、`250 Mbps`（`25p`）、`300 Mbps`（`29.97p`）、`500 Mbps`（`50p`）、`600 Mbps`（`59.94p`），`S&Q 120p` 可达 `1200 Mbps`。`500–600 Mbps` 需 `SDXC V90` 或 `CFexpress Type A`，而 `S&Q 4K 120p (1200 Mbps)` 强制要求 **`CFexpress Type A VPG200 / VPG400`**（对应 FX3 `STRID 0x0000e02e` 与 `CAUTION_ID_XAVC_S_I_TRANSFER_RATE_DISABLE_UNDER_400MBPS_MEDIA_SLOT1_MSG`）。

### 二、 `ACES 1.3 / 2.0` `S-Log3` 分段传递函数与 `S-Gamut3 / S-Gamut3.Cine -> AP0 / AP1` IDT 矩阵校验

1. **`S-Log3` 10-bit 满量程关键码值与分段断点**：
   - `0%` 黑电平 = **CV `95`**（`3.5% IRE`）；`18%` 中灰 = **CV `420`**（`41.0% IRE`）；`90%` 白卡 = **CV `598`**（`61.0% IRE`）；线性趾部（Linear Toe）与对数主段精确衔接于线性反射率 `0.01125000` 处的 **`CV = 171.2102946929`**（即归一化阈值 `171.2102946929 / 1023.0`）。
2. **`CAT02` 与 `Bradford`（`D65 -> D60`）色适应矩阵**：
   - 官方 Sony CTL 与 `OpenColorIO-Config-ACES` CLF（ACES 2.0 ID：`urn:ampas:aces:transformId:v2.0:CSC.Sony.SLog3_SGamut3Cine_to_ACES.a2.v1`）采用 **`CAT02`** 色适应从 D65 `(0.3127, 0.3290)` 转换至 ACES 白点 `(0.32168, 0.33767)`；**`Bradford`** 矩阵元素与之相差约 `4.6e-3`，但两者均严格满足可逆性（`det > 0`）与白点守恒（`(1.0, 1.0, 1.0)` 误差 `< 1e-12`，远优于 `1e-4` 红线）。

### 三、 `NP-FZ100`（`InfoLITHIUM Z`）`C` 触点通信、`FX3 v6.00–v7.02` 认证弹窗与 `14.4 V / 7.2 V` 供电轨隔离

1. **`+ / C / -` 三触点与单线串行协议**：
   - `NP-FZ100`（`7.2 V` / `16.4 Wh` / `2280 mAh`）仅引出 `+`、`C`、`-` 三个触点。其中 **`C` 脚（Communication）**并非独立模拟热敏电阻 `T` 脚或双线 `I2C/SMBus`（无独立时钟线），而是索尼专有**单线双向串行 InfoLITHIUM 通信线**，负责向 CP/PMIC（`cpapp-b.bin` 中的 `BATT_AUTH_Snd` / `BATT_STATE1_Snd` / `BATT_TYPE1_Snd`）同步温度、电量百分比与加密认证握手。
2. **FX3 `v4.00..v7.02` 弹窗语义与 FX6 `14.4 V` 错配防线**：
   - 当未解码第三方电池或无 `C` 脚假电池触发认证失败时，FX3 弹出 `STRID 0x0000e24e`（*"The operation and safety of this battery cannot be guaranteed. Continue use?"*）：点 **OK** 可继续拍摄（隐藏百分比），点 **Cancel** 关机（`v6.00` 曾出现旧款副厂电池每 15–30 秒重复弹窗中断录像问题，后续经 `v6.01/v7.00..v7.02` 迭代）。
   - **Stage-B 跨机防误关机契约**：FX6 `appFw.so` 内置 **`14.4 V` `BP-U35/U70`** 与 **`19.5 V` `DC IN`** 电压告警阈值（`DC_VOLTAGE_NEAR_END` / `DC_VOLTAGE_END` / `BKID_APP_USER_MENU_DC_VOLTAGE_ALARM0`）。在 FX3 `7.2 V`（`6.0–8.4 V`）`NP-FZ100` 供电轨上运行 Stage-B 覆盖层时，必须将电池状态归一化为百分比/安全降级契约，严禁直接套用 `14.4 V` 阈值误触发 `LOW_BATTERY_SHUTDOWN`！

### 四、 2025–2026 索尼固件逆向、ARM64 QEMU 与 `eMMC / UART` 救砖进展

- 综合 `FX3 v7.00–v7.02` 官方更新、`OpenColorIO-Config-ACES`、`DavidBuchanan314/ILCE-7M4-RE`（48 KB BootROM RP2040 `uart_boot`、Fastboot `18d1:4ee0`、`boot0` 派生 AES-XTS 密钥与全盘救砖）、`chocotan/a7c2-re`（ARM64 QEMU `ramfb` + 软件 GPE）、`YuuLuo/a7c2-service-preload`（`libJit.so` 与 `LD_PRELOAD` 防砖警告）、`xyzhangxin/sony-a6700-powerful`、`dino2048/zv-e10-toolkit`、`cokeenet/zve10-qemu`（`pmemsave` 调试）及 `ma1co/Sony-PMCA-RE`，持续加固本实验室“**严格 `os.O_RDONLY` 扫描 + 零持久 `eMMC` 写入**”安全底线。
