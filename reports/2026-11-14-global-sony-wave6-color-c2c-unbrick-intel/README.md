# Phase 65 — Wave-6 Global Sony Cinema Color Science, ARM64 V4L2/DMA-BUF Virtualization & Unbrick/Fail-Open Intelligence Sync

# 第 65 阶段 — Wave-6 全球索尼电影机色彩科学、ARM64 相机虚拟化与救砖/失效开放逃生公开情报同步

> **Date / 日期**: `2026-11-14`  
> **Task / 任务**: `Phase 65 (task_a66509c44452)` · **Worktree**: `h59-phase65-wave6-intel-wb-colormatrix-auditor`  
> **Target Baseline / 对齐基线**: `ILME-FX6 v6.01/v6.02 -> ILME-FX3 v7.00/v7.02` (`CXD90057` + `IMX510`)  
> **Clean-Room Compliance / 洁净室声明**: All external facts are synthesized from live web searches (`2026-11-14`) of official Sony manuals/firmware notices, ASWF OpenColorIO documentation, Linux/QEMU upstream docs, and public embedded systems references. Zero proprietary keys or third-party binaries were copied or committed.

---

## 1. Bilingual Executive Analysis / 中英双语执行摘要

### English Executive Summary

Wave-6 synchronizes current public technical documentation (`2025–2026-11`) across three engineering domains that directly govern the **12th Firmware-Lab Auditor** ([`wb_color_matrix_and_look_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/wb_color_matrix_and_look_auditor.py)) and our **FX6-on-FX3** clean-room architecture:

1. **Sony Firmware & Cinema Line Color Science (`FX3 v7.00–v7.02` vs `FX6 v6.00–v6.02`)**:
   - **Firmware Parity Trajectory**: Sony FX3 **v7.00** (Aug 2025) introduced the **BIG6** home screen, fixed/variable FPS selection, `1.5x`/`1.6x` anamorphic de-squeeze, HDMI Blackmagic RAW output, direct Creators' Cloud / `Monitor & Control` wired USB-LAN workflows, and WPA2/WPA3 security hardening; **v7.01** (Sep 2025) fixed user 3D LUT recording lockups, and **v7.02** (Mar 2026) stabilized operation. On the FX6 side, **v6.00** (Mar 2026) added BIG6, `HLG Mild`, Paint+Look combined Scene File import/export, 3D LUT quality refinements, and `Monitor & Control` (`v2.5.0+`) S&Q/network low-res monitoring; **v6.01** (Sep 2026) improved color reproduction in highly saturated regions; and **v6.02** (Nov 5, 2026) fixed dual-slot simultaneous recording error propagation.
   - **Color Pipeline & OCIO v2 / ACES**: Both bodies share the `IMX510` Dual Base ISO (`800`/`12,800`) **`S-Gamut3.Cine / S-Log3`** (15+ stops), **`S-Cinetone`** (VENICE-derived skin/highlight roll-off), **`709(800%)`** monitoring LUT, and **`HLG Live` / `HLG Natural`** transforms. In post-production, `OpenColorIO-Config-ACES` expresses the Sony `S-Log3 S-Gamut3.Cine` Input Device Transform (`urn:aswf:ocio:transformId:1.0:Sony:Input:SLog3_SGamut3Cine_to_ACES2065-1:1.0`) analytically via `<LogCameraTransform>` (`lin_side_break: 0.01125`) + `<MatrixTransform>` (4×4 to `ACES2065-1` AP0), accelerated in **OCIO v2.5.0+** via its Vulkan GPU renderer.
   - **White Balance & Paint Matrix (`R-G..B-G`)**: FX6 provides a physical 3-position `WHT BAL` (`B/A/PRST`) switch, `ATW` (Auto Tracing WB + `ATW Speed` + `ATW Hold`), and `Shockless White` (`Off / 1 / 2 / 3`). FX3 lacks the physical slide switch and uses `Shockless WB` (`Off / 1 / 2 / 3`) + `[Auto]` WB / `AWB Lock`, requiring clean soft-mapping onto FX3 Assignable Buttons + `Fn`/Big6 (`0` missing-GPIO faults). FX6's Paint Menu `User Matrix` (`R-G..B-G`), `Multi-Matrix`, `Knee` (`75.0%..109.0%`), and `Black Gamma` require strict **row-sum = `1.0`** in the 3×3 linear matrix so neutral grey `[1, 1, 1]` never tint-shifts.

2. **ARM64 Camera Virtualization (`QEMU AArch64` + `V4L2` / `DMA-BUF` + Dual-Domain RTOS/Linux)**:
   - On `qemu-system-aarch64` (`-M virt`, Cortex-A35, KVM/TCG), **`virtio-media`** and QEMU 11.2+ **`vhost-device-media`** (`vhost-user-media-pci`) relay V4L2 ioctls/buffers from host `/dev/videoN` into little-endian 64-bit ARM64 guests. While native host V4L2 supports zero-copy `V4L2_MEMORY_DMABUF` import into Vulkan / OCIO v2.5+, upstream `virtio-media` and `vhost-device-media` currently transfer frames via `MMAP` / `USERPTR` (with VirtIO UUID `DMABUF` shared-object backing pending), whereas guest-to-host display scanout zero-copy uses `vhost-user-gpu` (`VhostUserGpuDMABUFScanout`) over Unix domain sockets.
   - Asymmetric AP/CP dual-domain camera control emulation bridges Linux (`virt` + `ivshmem-doorbell`) to Cortex-R5 RTOS (`ivshmem-flat` MMIO `INTRMASK`/`INTRSTATUS`/`DOORBELL`) via **OpenAMP** (`libmetal` + `VirtIO`/`RPMsg`) and emerging `virtio-msg`, keeping Stock-CP (`cpapp-b.bin`) read-only (`cp_mutation_bytes == 0`).

3. **Camera Unbrick & Fail-Open Escape (`SD Sentinel` / `FAT12/16` / `renameat2` / `WDT`)**:
   - **Non-Invasive SD/CFexpress Sentinel Bypass**: Early `init2` / pre-bind-mount sentinel checks on removable media allow a camera to skip `mount --bind` / `ld.so.preload` overlays before dynamically linked `/bin/busybox` or `appFw.so` locks up.
   - **FAT12/FAT16 BootROM & Atomic Directory Swaps**: Immutable camera BootROMs (Canon CHDK/400plus, Fujifilm, TI OMAP, Raspberry Pi) recognize **FAT12 / FAT16 / FAT32** (often requiring `mkfs.vfat -a` under `dosfstools 4.2+`), never exFAT. On Linux rootfs/overlays, atomic directory replacement requires `renameat2(RENAME_EXCHANGE)` (`mv --exchange -T` in coreutils 9.5+) rather than racy 3-step `mv`, layered over read-only `overlayroot`.
   - **Watchdog Boot-Loop Recovery**: Production embedded OTA pairs atomic pointer swaps with a persistent boot counter and hardware watchdog (`BOOT_WATCHDOG_TIMEOUT` / Sony `TIMER-IP` 3m40s `WDT_SET_STOP`), automatically rolling back to the golden slot or dropping to U-Boot (`appauto 0`) / Multi-port `48000` baud `uart_boot` escape when boot attempts exceed threshold.

### 中文执行摘要

Wave-6 同步了 `2025–2026-11` 全球三大关键方向的最新公开技术资料，直接支撑第 12 号统一固件实验室审计器 [`wb_color_matrix_and_look_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/wb_color_matrix_and_look_auditor.py) 与 **FX6-on-FX3** 洁净室架构：

1. **索尼固件演进与电影机色彩科学（`FX3 v7.00–v7.02` vs `FX6 v6.00–v6.02`）**：
   - **固件对齐脉络**：FX3 `v7.00`（2025-08）正式引入 **BIG6** 主界面、固定/可变帧率模式、`1.5x/1.6x` 变形宽银幕反挤压、HDMI Blackmagic RAW 输出、`Creators' Cloud` / `Monitor & Control` 有线 USB-LAN 协同与 WPA2/WPA3 安全加固；`v7.01`（2025-09）修复用户 3D LUT 录屏卡死缺陷；`v7.02`（2026-03）进一步提升稳定性。FX6 `v6.00`（2026-03）同步引入 BIG6、`HLG Mild`、Paint+Look 合并场景文件导入/导出、`Monitor & Control v2.5.0+` S&Q 与低分辨率网络监看；`v6.01`（2026-09）优化高饱和度区域色彩还原；`v6.02`（2026-11-05）修复双卡同步录制时单卡报错连带停录另一卡槽的隐患。
   - **色彩管线与 `OCIO v2` / `ACES`**：两款机身共享 `IMX510` 双原生 ISO（`800 / 12800`）与 **`S-Gamut3.Cine / S-Log3`**（15+ 档动态范围）、**`S-Cinetone`**、**`709(800%)`**、`HLG Live`、`HLG Natural` 色彩科学。`OpenColorIO-Config-ACES` 采用纯解析 `<LogCameraTransform>` + `<MatrixTransform>`（4×4 AP0 矩阵）实现 Sony `S-Log3 S-Gamut3.Cine` IDT，并在 **OCIO v2.5.0+** 中通过 Vulkan GPU 渲染器实现硬件加速。
   - **白平衡与 Paint 矩阵（`R-G..B-G`）**：FX6 拥有实体三段 `WHT BAL`（`B/A/PRST`）拨钮、`ATW`（`ATW Speed`/`ATW Hold`）与 `Shockless White`（`Off/1/2/3`）；FX3 无实体拨钮，必须通过自定义按键 + `Fn`/Big6 软映射实现零 GPIO 报错切换，同时在 Paint 3×3 线性色彩矩阵中强制**每行元素之和恒等于 `1.0`**，确保中性灰 `[1, 1, 1]` 绝不发生偏色漂移。

2. **ARM64 相机虚拟化（`QEMU AArch64` + `V4L2/DMA-BUF` + 异构双域）**：
   - `qemu-system-aarch64`（`-M virt`, Cortex-A35）通过 `virtio-media` 与 QEMU 11.2+ `vhost-device-media`（`vhost-user-media-pci`）向 ARM64 客户机透传 `/dev/videoN`；宿主机原生支持 `V4L2_MEMORY_DMABUF` 零拷贝送入 Vulkan / OCIO v2.5+，而虚拟化跨边界当前以 `MMAP`/`USERPTR` 为主（VirtIO UUID `DMABUF` 共享对象规范已定义、驱动待合入；显示侧由 `vhost-user-gpu` `VhostUserGpuDMABUFScanout` 传递 `dmabuf fd`）。
   - AP Linux（`ivshmem-doorbell`）与 CP RTOS（`ivshmem-flat` MMIO 门铃）通过 **OpenAMP**（`libmetal` + `RPMsg`）及 `virtio-msg` 实现异构协同，确保 Stock-CP 零修改（`cp_mutation_bytes == 0`）。

3. **相机救砖与失效开放逃生（`SD 哨兵` / `FAT12/16` / 原子目录交换 / 看门狗恢复）**：
   - 在 `init2` 早期 `mount --bind` 之前检查可移动存储卡（SD/CFexpress）哨兵逃生标志，可在动态链接 `busybox` 或覆盖层异常时无损退回原厂系统；不可变 BootROM 仅识别 **FAT12 / FAT16 / FAT32**（`dosfstools 4.2+` 需注意 `-a` 参数）；Linux 目录切换采用 `renameat2(RENAME_EXCHANGE)`（`mv --exchange -T`）配合只读 `overlayroot` 与硬件看门狗启动计数器（超限自动回滚黄金分区或进入 UART/Multi 口恢复模式）。

---

## 2. Domain 1: Sony Firmware (`FX3 v7.00–v7.02` vs `FX6 v6.00–v6.02`) & Cinema Line Color Science

### 2.1 Firmware Alignment & Color / WB Feature Matrix

| Capability / 功能维度 | `ILME-FX3` (`v7.00 -> v7.02`) | `ILME-FX6` (`v6.00 -> v6.02`) | Phase 65 Clean-Room Enforced Contract |
| :--- | :--- | :--- | :--- |
| **Latest Firmware Baseline** | `v7.00` (Aug 26, 2025: BIG6, 1.5x/1.6x de-squeeze, HDMI BRAW, USB-LAN auto) -> `v7.01` (User LUT fix) -> `v7.02` (Mar 17, 2026) | `v6.00` (Mar 18, 2026: BIG6, `HLG Mild`, Paint+Look Scene File, M&C v2.5.0+) -> `v6.01` (Sep 1, 2026: saturated color accuracy) -> `v6.02` (Nov 5, 2026: dual-slot error fix) | Cross-body audit across `FX3 v7.02` & `FX6 v6.01` `appFw.so`, `libmpr.so`, `cpapp-b.bin`, and `.uxc` string packs. |
| **Base Look & Gamma/Gamut** | `S-Cinetone`, `S-Log3 / S-Gamut3.Cine`, `S-Log3 / S-Gamut3`, `ITU709`, `709(800%)` (Gamma Display Assist), `HLG/HLG1-3`, `User 3D LUT` (16 slots) | `S-Cinetone`, `S-Log3 / S-Gamut3.Cine`, `S-Log3 / S-Gamut3`, `ITU709`, `709(800%)`, `709tone`, `HLG Live`, `HLG Natural`, `HLG Mild`, `User 3D LUT (MLUT)` | All 8 canonical Base Looks verified (`FX6_V601_FX3_V702_PARITY`), with SDR/HDR target display & 1..16 slot checks. |
| **White Balance Control** | `Preset` (Daylight/Incandescent/Color Temp `2500K–9900K`), `Custom 1–3`, `[Auto]` WB + `AWB Lock Hold/Toggle`, `Shockless WB` (`Off / 1 / 2 / 3`) | Physical `WHT BAL` (`B/A/PRST`) switch, `Preset` (`3200K/4300K/5600K`), `Memory A/B` (`2000K–15000K` + `CC MG/GR`), `ATW` (`ATW Speed`, `ATW Hold`), `Shockless White` (`Off / 1 / 2 / 3`) | Mired-space exponential slew (`tau = 0 / 0.65 / 1.60 / 3.20 s`) + FX3 Assignable/`Fn`/Big6 soft-map (`0` missing-GPIO faults). |
| **Paint Menu Matrix & Knee** | Picture Profile `Knee Mode/Point/Slope`, `Black Level`, `Black Gamma` (`Narrow/Middle/Wide`) | `User Matrix` (`R-G, R-B, G-R, G-B, B-R, B-G`, Level, Phase), 16-axis `Multi Matrix`, `Knee` (`75.0%..109.0%`, Slope `-99..+99`), `Black Level` / `Black Gamma` | Exact 3×3 matrix row-sum white-point verifier (`sum(row) == 1.0`, `det(M) > 0.05`) + Knee/Black bounds. |
| **Monitor & Control / Cloud** | Wired USB-LAN (`CDC-NCM`) + `Monitor & Control` (`v2.5+`/`v3.0` EL Zone, Waveform, False Color, Focus Map), `OK/NG/KEEP` clip flags, Creators' Cloud | Wired LAN / USB-LAN + `Monitor & Control` (`v2.5.0+` low-res net monitoring, S&Q control, 3D LUT mgmt, up to 20-cam multi-view) | Metadata & LUT/WB state read-only observability without persistent flash writes. |
| **Factory Sensor Calibration** | `IMX510` per-unit WB gain, shading, defect-pixel calibration in `cnflasha` / Stock-CP | Shared `IMX510` CP driver (`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`) + `WBGainR/G/B/Std` | `calibration_mutation_bytes == 0`, `cp_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`. |

### 2.2 OpenColorIO (`OCIO v2`) & ACES Analytical Sony IDT

- **Transform ID**: `urn:aswf:ocio:transformId:1.0:Sony:Input:SLog3_SGamut3Cine_to_ACES2065-1:1.0` (aliases: `slog3_sgamut3cine`, `Input - Sony - S-Log3 - S-Gamut3.Cine`).
- **Stage 1 — Inverse `<LogCameraTransform>` (S-Log3 -> Linear)**:
  - `base: 10`, `log_side_slope: 0.255620723362659`, `log_side_offset: 0.410557184750733`, `lin_side_slope: 5.26315789473684`, `lin_side_offset: 0.0526315789473684`, `lin_side_break: 0.01125`, `linear_slope: 6.62194371177582`.
- **Stage 2 — `<MatrixTransform>` (Linear S-Gamut3.Cine -> ACES2065-1 AP0)**:
  - 4×4 matrix rows: `[0.638788667185978, 0.272351433711262, 0.0888598991027595, 0]`, `[-0.00391590602528224, 1.0880732308974, -0.0841573248721177, 0]`, `[-0.0299072021239151, -0.0264325799101947, 1.05633978203411, 0]`, `[0, 0, 0, 1]`. Notice each RGB row sums to `1.0` (`~1.000000000000000`), preserving the achromatic white point!
- **GPU Acceleration**: OCIO `v2.5.0+` adds ACES 2.0 built-in configs and a native **Vulkan GPU renderer**, pairing cleanly with native Linux `V4L2_MEMORY_DMABUF` zero-copy frame import.

**Public Citations (Domain 1)**:
- Sony FX3 Ver. 7.00 / 7.01 / 7.02 Release Notes & Help Guide: <https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/downloads>, <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000285051.html> (Shockless WB), <https://www.newsshooter.com/2025/08/26/sony-fx3-v7-00-and-fx30-v6-00-firmware-updates/>
- Sony FX6 Ver. 6.00 / 6.01 / 6.02 Release Notes & Color/WB Guides: <https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx6v/downloads>, <https://sony-cinematography.com/articles/white-balance-modes-on-the-fx6/>, <https://www.sony.com/en/articles/fx6-cine-ei-and-base-look/>
- Sony *Monitor & Control* Help Guide (`v2.5.0+` / `v3.0` EL Zone): <https://helpguide.sony.net/promobile/mc/v1/en/contents/supported_camera.html>, <https://helpguide.sony.net/promobile/mc/v1/en/contents/shooting_assist_functions.html>
- Academy Software Foundation (`ASWF`) OpenColorIO v2.5+ & `OpenColorIO-Config-ACES`: <https://opencolorio.org/>, <https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES>, <https://opencolorio.readthedocs.io/en/latest/guides/authoring/aces.html>

---

## 3. Domain 2: ARM64 Camera Virtualization (`QEMU AArch64` + `V4L2/DMA-BUF` + Dual-Domain RTOS/Linux)

| Layer / 层次 | Upstream Technology / 上游技术 | Current Capability & Constraints / 现状与边界 | FX3/FX6 Lab Relevance / 实验室对齐意义 |
| :--- | :--- | :--- | :--- |
| **QEMU AArch64 Guest** | `qemu-system-aarch64 -M virt` + `cortex-a35` + KVM/TCG | Standard 64-bit little-endian ARM64 virtual platform for Sony CE Linux `4.9.337-scel+` & ISP/color-pipeline simulation. | Matches our `fx3-vm` AArch64 AP guest topology (`5120 MiB` RAM, `gic-version=2`). |
| **V4L2 Virtualization** | Linux `virtio-media` & QEMU 11.2+ `vhost-device-media` (`vhost-user-media-pci`) | Relays V4L2 ioctls/buffers (`--backend v4l2-proxy`) to ARM64 LE guests without a VB2 hardware driver; `MMAP` and `USERPTR` operational. | Enables host webcam/synthetic `IMX510` Bayer/YUV test feeds into virtualized AP `libmpr.so` / `appFw.so` pipelines. |
| **DMA-BUF Zero-Copy** | `V4L2_MEMORY_DMABUF` (Host Vulkan/DRM) vs `vhost-user-gpu` (`VhostUserGpuDMABUFScanout`) | Host V4L2 exports `dmabuf` fds zero-copy into Vulkan/OCIO v2.5+; inside `virtio-media`/`vhost-device-media`, VirtIO UUID `DMABUF` backing is defined in spec but not yet implemented (falls back to `MMAP`/`USERPTR`). On ARM64 without `dev_is_dma_coherent()`, `dma-contig` disables CPU caching (`pgprot_writecombine()`). | Guides zero-copy host presentation (`vhost-user-gpu` / `ramfb`) vs guest capture buffer staging in `fx3-vm`. |
| **Dual-Domain AP+CP** | `ivshmem-doorbell` (AP PCI) + `ivshmem-flat` (CP MMIO) + **OpenAMP** (`libmetal` + `RPMsg`) + `virtio-msg` | Bridges AP Linux `virt` to Cortex-R5 RTOS (`cpapp-b.bin`) via `INTRMASK`/`INTRSTATUS`/`DOORBELL` shared memory and `<200 us` interrupt signaling. | Validates `cp_mutation_bytes == 0` Stock-CP isolation during ISP/WB/LUT UIPC dispatch. |

**Public Citations (Domain 2)**:
- QEMU System AArch64 `virt` Documentation: <https://www.qemu.org/docs/master/system/arm/virt.html>
- `virtio-media` Linux Kernel Driver & Specification: <https://lwn.net/Articles/999000/>, <https://github.com/chromeos/virtio-media>
- `rust-vmm/vhost-device` (`vhost-device-media` / `vhost-user-media-pci`): <https://github.com/rust-vmm/vhost-device/tree/main/vhost-device-media>
- QEMU `vhost-user-gpu` (`VhostUserGpuDMABUFScanout`) & `V4L2_MEMORY_DMABUF`: <https://www.qemu.org/docs/master/interop/vhost-user-gpu.html>, <https://docs.kernel.org/userspace-api/media/v4l/dmabuf.html>
- OpenAMP Dual-QEMU IVSHMEM (`ivshmem-flat` + `libmetal`/`RPMsg`): <https://github.com/OpenAMP/openamp-system-reference>

---

## 4. Domain 3: Camera Unbrick & Fail-Open Escape (`SD Sentinel` / `FAT12/16` / `renameat2` / `WDT`)

1. **Non-Invasive SD/CFexpress Sentinel Escape (`init2` Early Bypass)**:
   - On BIONZ XR cameras, `/bin/busybox` and `/bin/sh` are dynamically linked; a corrupt `/etc/ld.so.preload` or broken `mount --bind` over `/usr/lib/appFw.so` causes unrecoverable userspace init lockups.
   - **Fail-Open Design Rule**: Any experimental Stage-B loader MUST inspect a non-persistent **SD/CFexpress sentinel flag** (e.g., presence of an escape marker file on `/mnt/sd*` or `/mnt/cfexpress*`) inside the early pre-mount `init2` hook **before** issuing `mount --bind` or loading overlays, cleanly falling open to stock `appFw.so` without touching eMMC.
2. **FAT12 / FAT16 BootROM Partition Constraints & Atomic Directory Swaps**:
   - Immutable camera/SoC BootROMs (Canon CHDK/400plus `EOS_DEVELOP`/`BOOTDISK`, Fujifilm SD dual-boot, TI OMAP `MLO`, Raspberry Pi `start.elf`) recognize only **FAT12, FAT16, or FAT32** (never exFAT), and `dosfstools 4.2+` often requires `-a` alignment compatibility for embedded ROMs.
   - Inside Linux rootfs/partition trees (and guarding against Sony `nflasha10` 12 MiB VFAT full-disk `0x10000009` errors), multi-step `mv` leaves a crash/power-loss window where the target path vanishes. Linux **`renameat2(..., RENAME_EXCHANGE)`** (`mv --exchange -T <dirA> <dirB>` in GNU coreutils `9.5+`) atomically swaps directories on ext4/Btrfs/tmpfs, ideally paired with read-only `overlayroot` so reboots discard transient state.
3. **Hardware Watchdog Boot-Loop Recovery**:
   - Production embedded rollback pairs atomic slot pointers with a persistent boot counter and hardware watchdog (`BOOT_WATCHDOG_TIMEOUT` -> `kernel_watchdog_timeout`; Sony `TIMER-IP` 3m40s `WDT_SET_STOP`). If firmware hangs before clearing the counter, the WDT resets the SoC and the bootloader rolls back to the golden recovery slot or drops to U-Boot (`appauto 0`) / Sony Multi-port `48000` baud `uart_boot` (`RP2040-Zero` `RX/TX/XReset` + `eSRAM 0xFE020000`) for keyless external recovery.

**Public Citations (Domain 3)**:
- CHDK / Fujifilm / TI OMAP / Raspberry Pi FAT12/FAT16/FAT32 BootROM Rules & `dosfstools -a`: <https://chdk.fandom.com/wiki/Prepare_your_SD_card>, <https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes>
- Linux `renameat2(2)` `RENAME_EXCHANGE` & `mv --exchange` Atomic Directory Swap: <https://man7.org/linux/man-pages/man2/rename.2.html>, <https://www.gnu.org/software/coreutils/manual/html_node/mv-invocation.html>
- Thingino / OpenIPC / Sony `ILCE-7M4-RE` BootROM Recovery & Watchdog Rollback: <https://github.com/DavidBuchanan314/ILCE-7M4-RE>, <https://github.com/wl-thingino/thingino-firmware>, <https://openipc.org/supported-hardware>
