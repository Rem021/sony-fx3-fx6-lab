# Phase 82 — Wave-8 Global Sony Fleet (`CAMSET`/`Monitor & Control`/4ch LPCM), ARM64 Audio/PTP Virtualization & eMMC Anti-Rollback/Overlay Recovery Intelligence Sync

# 第 82 阶段 — Wave-8 全球索尼多机位工作流（`CAMSET`/`Monitor & Control`/4ch LPCM）、ARM64 音频与 PTP 虚拟化及 eMMC 防回滚/易失覆盖恢复公开情报同步

> **Date / 日期**: `2026-11-14`  
> **Task / 任务**: `Phase 82 (task_4a985707d146)` · **Worktree**: `h78-phase82-wave8-intel-vm-stage12-camset-lpcm`  
> **Target Baseline / 对齐基线**: `ILME-FX6 v6.00/v6.01/v6.02 (A-Cam) -> ILME-FX3 v7.00/v7.02 (B-Cam Stage-B)` (`CXD90057` + `XLR-H1` + `VMC-BNCM1`)  
> **Clean-Room Compliance / 洁净室声明**: All external findings are synthesized from live web searches (`2026-11-14`) of official Sony Help Guides/compatibility tables, QEMU `virtio-sound` & ALSA `snd-aloop` kernel documentation, IEEE 1588 / `ptp_kvm` / SMPTE ST 12 & ST 2059 specs, and JEDEC eMMC `RPMB`/`PERM_WP`/`overlayroot` recovery literature. Zero proprietary keys or third-party binaries were copied or committed.

---

## 1. Bilingual Executive Synthesis / 中英双语工程摘要

### English Executive Summary

Wave-8 synthesizes public engineering intelligence (`2025–2026-11`) across the three technical pillars powering **Stage 12** of our heterogeneous full-board virtual camera suite ([`outputs/fx3-vm/camset_lpcm_tcub_emulator.py`](../../outputs/fx3-vm/camset_lpcm_tcub_emulator.py)):

1. **Sony Multi-Camera Fleet Workflows (`CAMSET01.DAT` vs `ALL` Files, `Monitor & Control` v2+, and 4-ch `24-bit / 48 kHz` Safety-Track Audio)**:
   - **Cross-Body Profile Portability (`FX6 ALL` -> `FX3 CAMSET01.DAT` Clamping)**: Sony FX3 saves up to 10 `CAMSET01.DAT..CAMSET10.DAT` presets exclusively on **Slot 1** (`/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT` on SD or `/SONY/SETTING/ILME-FX3/CAMSET/` on CFexpress), excluding Custom WB 1–3, Face Memory, Date/Time, IPTC, and most Network/FTP keys; whereas FX6 saves Cinema Line `.ALL` files on **Media Slot B** under `/PRIVATE/SONY/PRO/CAMERA/`. Because Sony strictly forbids loading cross-model binary setting files directly, a Stage-B A-Cam (`FX6`) -> B-Cam (`FX3`) fleet profile loader **must** sanitize and clamp FX6 hardware-absent or RF-forbidden fields (`nd_preset -> "Clear"`, `sdi_out -> "CONTAINED_DISABLED"`, `vf_zebra` redirected to LCD, and `wlan_ap -> False` under `P12` Airplane-Mode) inside a volatile RAM shadow (`bk4_persistent_nvram_writes == 0`) while preserving 100% of shared Cinema Line imaging parameters (`Cine EI 800/12800`, `S-Gamut3.Cine/S-Log3`, `User1.cube`, `23.98p 180.0°`, `5600K`).
   - **`Monitor & Control` v2.0 / v2.1+ Wired Multi-Cam Monitoring**: `Monitor & Control` v2.0+ enables up to **4 cameras** simultaneously on iPadOS with **False Color** (`Pattern1 (SDR)` & `Pattern2 (S-Log3)`), Waveform, Histogram, Zebra, and Focus Map. Crucially for `P12` RF-silent rigs: FX3 supports both direct **USB-C (`Remote Shooting`)** via a powered USB hub (with Timecode display / Focus Map / LUT import limitations over direct USB) and full-featured **1 Gbps Wired LAN** (`CDC-NCM` USB-C to Ethernet adapter) through a shared router/switch, whereas FX6 uses Wired LAN over USB-C Ethernet (with a manual Subnet Mask + **Gateway** required even on isolated switch networks).
   - **4-Channel `24-bit / 48 kHz` LPCM & `-20 dB` Safety-Track Practices**: Both FX3 (`XLR-H1` via `MI Shoe Audio Set -> 48kHz/24bit 4ch`) and FX6 record 4-channel `24-bit / 48 kHz` LPCM. On `XLR-H1`, `INPUT SELECT` (`IN1` / `IN1·IN2` / `IN3`) routes `INPUT1/2` XLR (+48V phantom-capable) and `INPUT3` 3.5 mm stereo into `CH1..CH4`. Setting `CH1/CH2` for primary boom/lavalier and `CH3/CH4` at **`-20.0 dB` safety pad** (or internal stereo fallback on `XLR-H1` hot-detach) prevents irreversible `int24` (`[-8388608, +8388607]`) clipping/wrap-around during `+12 dBFS` transient overloads, while off-speed `S&Q` automatically mutes all 4 audio channels.
   - **SMPTE 12M `User-Bits` (`BG1..BG8`) & `TC IN -> HDMI TC OUT`**: SMPTE ST 12-1/12-2 encodes 32-bit `User-Bits` across 8 nibbles (`BG1..BG8`) alongside `HH:MM:SS:FF` BCD time address, enabling fleet tagging (`CamID`, `Reel`, `MasterCam`, sync flags) even when file naming uses separate `CamID + Reel#`. FX3 ingests external LTC exclusively via `VMC-BNCM1` on the body **Multi-Port** (`EXT-LK`, sharing the physical connector housing with `uart_boot` pins that must stay electrically isolated), and re-transmits embedded Timecode + `BG1..BG8` User-Bits over Type-A **`HDMI TC OUT`**.

2. **ARM64 Audio & Timecode Virtualization (`QEMU virtio-sound` + `snd-aloop` + `ptp_kvm` / SMPTE ST 2059)**:
   - On `qemu-system-aarch64` (`virt` machine, `CONFIG_SND_VIRTIO`), QEMU 8.2+ exposes `virtio-sound-pci` / `virtio-sound-device` (max 10 streams). Because QEMU `-audiodev` maps `VIRTIO_SND_PCM_FMT_S24` / `S32` to `AudioFormat` (`s8`, `s16`, `s32`, `u8`, `u16`, `u32`, `f32`) and QEMU 9.0 hit an assertion bug (#2416) on unmapped 24-bit formats, deterministic `24-bit / 48 kHz` virtualization pairs **`s32` (`S32_LE` 32-bit container) or packed `S24_3LE`** with `period_bytes` evenly dividing `buffer_bytes` (`buffer_bytes % period_bytes == 0`).
   - On Linux hosts/guests, **`snd-aloop`** (`timer_source` hardware/udriven lock + `PCM Rate Shift 100000` ±20% clock skew control) and `alsaloop` prevent buffer underruns/drift, while ARM64 **`ptp_kvm`** (`ARM_SMCCC_VENDOR_HYP_KVM_PTP_FUNC_ID: 0x86000001` -> `/dev/ptp*`) transfers host TAI timestamps to KVM guests with sub-microsecond accuracy, allowing deterministic derivation of 48 kHz AES67 / ST 2110-30 sample clocks and SMPTE 12M timecode per **SMPTE ST 2059-1/-2**.

3. **Bootloader Anti-Rollback, `mmc-utils` `PERM_WP` Hazards & Non-Destructive Overlay Recovery**:
   - Modern ARM SoCs enforce monotonic rollback floors using **SoC OTP eFuses** (primary RoT key hash, lifecycle, anti-rollback floor) and **eMMC `RPMB`** (256-bit OTP-programmed HMAC-SHA256 key + monotonic 4-byte write counter). Flashing an older or cross-SKU bootloader trips an unrecoverable verification abort or blows irreversible OTP ratchets.
   - Worse, JEDEC JESD84-B51 defines **`PERM_WRITE_PROTECT` (`CSD[13]`)**, **`B_PERM_WP_EN` (`EXT_CSD[173]` bit 2)**, and **`US_PERM_WP_EN` (`EXT_CSD[171]` bit 2)** — enabled in `mmc-utils` only with `CFLAGS=-DDANGEROUS_COMMANDS_ENABLED`. Once asserted, no standard JEDEC command (`CLR_WRITE_PROT` fails) can clear permanent WP: flashing `dd`/`fastboot` fails permanently and only BGA eMMC replacement (or eMMC 5.1 **`SECURE_WP_INFO` `EXT_CSD[211]`** RPMB-authenticated WP if used instead) avoids bricking.
   - **Why Volatile Userspace RAM Overlays Stay Immune**: Mounting eMMC strictly read-only (`lowerdir`) and directing all Stage-B customizations (`CAMSET` fleet profiles, `Big6` layouts, bind-mounts) to a volatile `tmpfs` / RAM **`OverlayFS`** (`upperdir` in RAM) yields `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, and `persistent_emmc_writes_authorized = False`, making bootloader anti-rollback ratchets and `PERM_WP` flash bricks structurally impossible.

### 中文工程摘要

Wave-8 同步了 `2025–2026-11` 期间三大领域的最新公开技术情报，直接支撑全板第 12 阶段协同仿真模块（[`outputs/fx3-vm/camset_lpcm_tcub_emulator.py`](../../outputs/fx3-vm/camset_lpcm_tcub_emulator.py)）：

1. **索尼多机位协同工作流（`CAMSET01.DAT` / `Monitor & Control` v2+ / 4 声道 `24-bit 48kHz` 安全音轨 / `User-Bits`）**：
   - **跨机身配置文件净化**：FX3 在 **Slot 1** 存储 `CAMSET01.DAT`（`/PRIVATE/SONY/SETTING/FX3/CAMSET/`，最多 10 组，不含自定义白平衡/人脸/日期/IPTC/网络），而 FX6 在 **Slot B** 存储 `.ALL` 文件（`/PRIVATE/SONY/PRO/CAMERA/`）。由于官方严禁跨机型直接加载二进制配置文件，A 机（FX6）向 B 机（FX3 Stage-B）同步配置文件时，必须在易失性 RAM 影子层（`bk4_persistent_nvram_writes == 0`）中100%继承共享电影机参数（`Cine EI 800/12800`、`S-Gamut3.Cine/S-Log3`、`User1.cube`、`23.98p 180.0°`、`5600K`），同时将 FX3 缺失或射频禁用的字段确定性钳位（`nd_preset -> "Clear"`、`sdi_out -> "CONTAINED_DISABLED"`、`vf_zebra` 重定向至 LCD、`wlan_ap -> False` 强制执行 `P12` 飞行模式）。
   - **`Monitor & Control` v2.0/v2.1+ 有线多机位监看**：`v2.0+` 支持 iPadOS 最多 **4 机位同屏监看**与 **False Color（`Pattern1 SDR` / `Pattern2 S-Log3`）**；在 `P12` 无线静默环境下，FX3 支持 USB-C 直连（带供电 Hub 多机位，但直连会禁用 TC 显示与 Focus Map）和 `CDC-NCM` 有线千兆网卡，FX6 支持 USB-C 有线以太网（手动静态 IP 必须同时填写子网掩码和默认网关）。
   - **4 声道 `24-bit / 48 kHz` LPCM 与 `-20 dB` 安全音轨**：FX3 需配合 `XLR-H1` 开启 `48kHz/24bit 4ch`，`CH1/CH2` 录主麦克风、`CH3/CH4` 作为 **`-20.0 dB` 安全备份轨**（或在 `XLR-H1` 热拔出时通过 `P11` 隔离无缝回落至机身内置立体声麦），确保在 `+12 dBFS` 瞬态过载下通过砖墙限幅器实现 **`0` 次 `int24` 溢出回绕**，并在升格 `S&Q` 模式下自动静音。
   - **SMPTE 12M `User-Bits`（`BG1..BG8`）与 `TC IN -> HDMI TC OUT`**：32 位 `BG1..BG8` 八半字节承载 `CamID`/`Reel`/`MasterCam`/同步标志；FX3 通过机身 `Multi-Port`（`VMC-BNCM1`，需在阶段 38 严格隔离 `uart_boot` `1.8V` 引脚竞争）锁定外部 `EXT-LK`，并将内嵌时间码与 `BG1..BG8` 无损透传至 Type-A `HDMI TC OUT`。

2. **ARM64 音频与时间码虚拟化（`QEMU virtio-sound` + `snd-aloop` + `ptp_kvm` / SMPTE ST 2059）**：
   - `QEMU 8.2+` ARM64 `virt` 支持 `virtio-sound-pci`/`virtio-sound-device`（最多 10 条流），`virtio-snd` 需配合 `s32`（32 位容器承载 24-bit 有效样本，规避 QEMU 9.0 #2416 未映射格式断言）及整除周期帧（`buffer_bytes % period_bytes == 0`）。
   - Linux `snd-aloop` 通过 `timer_source` 与 `PCM Rate Shift 100000`（±20% 速率微调）避免时钟漂移；ARM64 `ptp_kvm` 通过 SMCCC 超调用 `0x86000001` 暴露 `/dev/ptp*`，结合 **SMPTE ST 2059** 由 PTP TAI 纪元精确导出 48 kHz 采样时钟与 SMPTE 12M 时间码。

3. **防回滚熔丝、`mmc-utils` `PERM_WP` 变砖风险与无损易失覆盖恢复**：
   - SoC **OTP eFuse** 与 eMMC **`RPMB`**（256-bit 一次性认证密钥 + 单调 4 字节写计数器 + HMAC-SHA256）强制执行启动链单调版本号，跨型号或降级刷写会永久锁死或触发启动拒绝。
   - JEDEC `PERM_WRITE_PROTECT`（`CSD[13]`）、`B_PERM_WP_EN`（`EXT_CSD[173]`）与 `US_PERM_WP_EN`（`EXT_CSD[171]`）一旦通过 `mmc-utils`（需 `DDANGEROUS_COMMANDS_ENABLED`）置位，标准 JEDEC 命令无法清除（仅 eMMC 5.1 `SECURE_WP_INFO` 可经 RPMB 撤销），物理闪烁即不可逆变砖。
   - **用户态 RAM 绑定覆盖的免疫性**：将内部 eMMC 严格保持只读 `lowerdir`，把所有 Stage-B 定制、配置文件影子与音频/时间码状态全部放入易失性 `tmpfs`/`OverlayFS` `upperdir`，可实现 `otp_fuse_touches == 0`、`rpmb_counter_increments == 0` 且完全免疫防回滚棘轮与永久写保护陷阱。

---

## 2. Domain 1: Sony Multi-Camera Fleet Workflows (`CAMSET`, `Monitor & Control`, 4-ch LPCM & `BG1..BG8`)

| Workflow Axis / 工作流维度 | `ILME-FX6` (A-Cam `v6.00–v6.02`) | `ILME-FX3` (B-Cam `v7.00–v7.02`) | Stage 12 Co-Emulation Contract / 第 12 阶段契约 |
| :--- | :--- | :--- | :--- |
| **Settings Persistence / 配置导出** | `Project -> All File` (`*.ALL`) on **Slot B** (`/PRIVATE/SONY/PRO/CAMERA/`) | `Setup -> Save/Load Settings` (`CAMSET01..10.DAT`) on **Slot 1** (`/PRIVATE/SONY/SETTING/FX3/CAMSET/`) | Cross-body sanitizer imports shared Cine EI / S-Log3 / LUT / WB / Shutter / FPS while scrubbing `ND`, `12G-SDI`, `VF`, and `Wi-Fi AP` in volatile RAM (`bk4_persistent_nvram_writes == 0`). |
| **Multi-Cam Wired Monitoring / 有线多机监看** | Wired USB-C Ethernet (Belkin USB-C LAN, requires Subnet + Gateway); no direct USB M&C on iPad/Mac | Direct USB-C (`Remote Shooting`, powered hub) OR USB-C Ethernet (`CDC-NCM`, Subnet + Gateway); M&C `v2.0/v2.1+` up to 4 cams + False Color (`SDR` / `S-Log3`) | `P12` Airplane-Mode disables Wi-Fi/BT (`wlan_ap=False`), routing multi-cam telemetry over wired `CDC-NCM` / USB-C without RF wakeups. |
| **4-ch `24-bit 48 kHz` Audio / 四声道安全音轨** | Native 4ch LPCM (Handle dual XLR + MI Shoe + internal mic); SDI 4ch / HDMI 2ch; Proxy 2ch AAC-LC | `XLR-H1` (`48kHz/24bit 4ch`); `INPUT SELECT` (`IN1` / `IN1·IN2` / `IN3`); `CH1+3/CH2+4` headphone mix; `S&Q` mutes audio | `CH1/CH2` capture primary `XLR-H1` (`+48V` gated per Phase 77), `CH3/CH4` capture `-20.0 dB` safety pad (`0` `int24` wraparounds under `+12 dBFS` overload); hot-detach falls back to `INTERNAL_STEREO`; `S&Q` mutes all 4 channels. |
| **SMPTE 12M `BG1..BG8` & `TC IN -> HDMI TC OUT`** | Bidirectional BNC `TC IN/OUT`; `Users Bit` (`Fix`/`Time`); `HDMI TC Out` | `Multi-Port` `VMC-BNCM1` **TC IN only** (`EXT-LK`); `User Bit Preset`/`Time Rec`; `HDMI Output -> TC Output` embeds TC + User Bits | Packs `CamID` + `Reel` + `MasterCam` + flags into 32-bit `BG1..BG8` inside 80-bit LTC (`0x3FFD`), locks `0` frame offset, isolates `Multi-Port` `uart_boot`, and regenerates clean `HDMI TC OUT`. |

**Public Citations (Domain 1)**:
- Sony FX3 Help Guide — Save/Load Settings (`CAMSET01.DAT`), 4ch Audio (`XLR-H1`), TC/UB (`VMC-BNCM1` & `HDMI TC Output`), Wired LAN & Monitor & Control:
  - <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000267806.html>
  - <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000436835.html>
  - <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000285051.html>
- Sony Monitor & Control App Compatibility, USB-C / Wired LAN Multi-Cam & False Color (`v2.0.0` / `v2.1.0+`):
  - <https://support.d-imaging.sony.co.jp/app/monitorandcontrol/en/devices/index.html>
  - <https://helpguide.sony.net/di/mc/v1/en/contents/201h_false_color.html>
  - <https://helpguide.sony.net/di/mc/v1/en/contents/201h_multi_cam.html>
- Sony ILME-FX6 `All File`, 4-ch Audio & `HDMI TC Out` Documentation:
  - <https://helpguide.sony.net/pro/fx6/v1/en/contents/TP1000180054.html>
  - <https://pro.sony/ue_US/products/handheld-camcorders/ilme-fx6>

---

## 3. Domain 2: ARM64 Audio & Timecode Virtualization (`virtio-sound`, `snd-aloop`, `ptp_kvm`, SMPTE ST 2059)

| Virtualization Layer / 虚拟化层 | Mechanism & Constraints / 机制与约束 | Deterministic Parameter Contract / 确定性参数契约 |
| :--- | :--- | :--- |
| **QEMU `virtio-sound` (`aarch64`)** | `virtio-sound-pci` / `virtio-sound-device` (QEMU 8.2+, max 10 streams, `CONFIG_SND_VIRTIO`); `-audiodev alsa` maps VirtIO `S24`/`S32` to QEMU `AudioFormat` (`s32` avoids QEMU 9.0 #2416 unmapped-format assert) | `48000 Hz`, `s32` (`S32_LE` 32-bit container) or packed `S24_3LE`, `buffer_bytes % period_bytes == 0` (e.g., `10 ms` = `480` frames/period) |
| **ALSA Loopback (`snd-aloop` / `alsaloop`)** | Cross-connected `hw:Loopback,0,x <-> hw:Loopback,1,x` with no hardware SRC; first opener locks rate/format | `timer_source` (`hw:0,0` or `SNDRV_TIMER_GLOBAL_UDRIVEN`) + `PCM Rate Shift 100000` (`80000..120000`, ±20% drift compensation) |
| **ARM64 `ptp_kvm` & SMPTE ST 2059 / 12M** | KVM SMCCC hypercall `ARM_SMCCC_VENDOR_HYP_KVM_PTP_FUNC_ID` (`0x86000001`) exposes host TAI clock via `/dev/ptp*` to `chrony`/`phc2sys` | PTP TAI epoch (`1970-01-01T00:00:00`) deterministically derives 48 kHz AES67/ST 2110-30 sample phase & SMPTE 12M `HH:MM:SS:FF` + `BG1..BG8` (<10 µs audio alignment) |

**Public Citations (Domain 2)**:
- QEMU `virtio-sound` Device & `-audiodev` Documentation / OASIS VirtIO Sound Specification:
  - <https://www.qemu.org/docs/master/system/devices/virtio-snd.html>
  - <https://docs.oasis-open.org/virtio/virtio/v1.2/csd01/virtio-v1.2-csd01.html#x1-49700014>
  - <https://gitlab.com/qemu-project/qemu/-/issues/2416>
- Linux ALSA `snd-aloop`, `timer_source`, `PCM Rate Shift` & Timestamping Docs:
  - <https://docs.kernel.org/sound/designs/timestamping.html>
  - <https://www.alsa-project.org/wiki/Matrix:Module-aloop>
- ARM64 `ptp_kvm` (`0x86000001`), `linuxptp`, & SMPTE ST 2059 / ST 12-1 / ST 2110-30:
  - <https://docs.kernel.org/virt/kvm/arm/ptp_kvm.html>
  - <https://www.smpte.org/standards/st2059>

---

## 4. Domain 3: Bootloader Anti-Rollback, `mmc-utils` `PERM_WP` Hazards & Non-Destructive Overlay Recovery

| Hazard / Recovery Layer | Hardware / Flash Mechanism / 底层机制 | Operational Consequence / 后果与安全性 |
| :--- | :--- | :--- |
| **SoC OTP eFuses & eMMC `RPMB`** | SoC eFuses store immutable RoT key hashes & anti-rollback floor; `RPMB` stores a 256-bit OTP-programmed HMAC-SHA256 key and monotonic 4-byte write counter | Flashing downgraded or cross-SKU bootloaders triggers secure-boot rejection or permanently increments anti-rollback epochs; `RPMB` writes cannot be erased |
| **JEDEC `PERM_WP` (`mmc-utils`)** | `CSD[13]` (`PERM_WRITE_PROTECT`), `EXT_CSD[173]` bit 2 (`B_PERM_WP_EN`), `EXT_CSD[171]` bit 2 (`US_PERM_WP_EN`); requires `CFLAGS=-DDANGEROUS_COMMANDS_ENABLED` in `mmc-utils` | **Irreversible flash brick**: `CLR_WRITE_PROT` fails and JEDEC defines no reset command; recovery requires BGA eMMC chip replacement (only eMMC 5.1 `EXT_CSD[211]` `SECURE_WP_INFO` via RPMB avoids permanent lock) |
| **Volatile `OverlayFS` / RAM Bind-Overlay** | Mounts eMMC strictly read-only (`lowerdir`) and places Stage-B overlays, `CAMSET` profiles, and `Big6` state in volatile `tmpfs` (`upperdir`) | **`otp_fuse_touches == 0`**, **`rpmb_counter_increments == 0`**, **`persistent_emmc_writes_authorized = False`** — completely immune to anti-rollback ratchets and `PERM_WP` traps |

**Public Citations (Domain 3)**:
- JEDEC eMMC `RPMB` & `mmc-utils` Permanent Write Protection (`EXT_CSD[171]/[173]/[211]`):
  - <https://docs.kernel.org/driver-api/mmc/mmc-tools.html>
  - <https://git.kernel.org/pub/scm/utils/mmc/mmc-utils.git/>
  - <https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html>
- SoC OTP Fuse / AVB Anti-Rollback & Read-Only `overlayroot` Non-Destructive Recovery:
  - <https://source.android.com/docs/security/features/verifiedboot/avb>
  - <https://docs.armbian.com/User-Guide_Overlayroot/>
