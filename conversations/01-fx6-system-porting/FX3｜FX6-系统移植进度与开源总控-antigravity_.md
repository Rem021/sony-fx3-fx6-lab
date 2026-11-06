# FX3｜FX6 系统移植进度与开源总控

- **Session ID**: `antigravity_0399b63f_b78a_42fa_a296_7c7bdd04179f`
- **Agent Provider**: `antigravity`
- **Orca Category Workspace**: `FX3｜FX6 系统移植与跨机型总览`
- **Orca Workspace ID**: `e52bdbc7-1cf3-4bc8-bdd4-f37b01044ebd::/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab`
- **Created At**: `2026-11-06T08:29:55.003Z`
- **Updated At**: `2026-11-06T13:43:05.913Z`
- **Captured Messages (User / Assistant)**: `2`

---

## 🤖 Assistant

The bilingual (English + Simplified Chinese) project overview and detailed development progress have been committed (`cb29aac6`) and pushed to your GitHub repository (`https://github.com/Rem021/sony-fx3-fx6-lab`) in [README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/README.md) and [docs/BYOF-REPRODUCTION.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/docs/BYOF-REPRODUCTION.md).

Below is the complete, unabridged **English** version followed by the complete **Simplified Chinese (简体中文)** version.

---

# Part I — Complete English Overview & Detailed Development Progress

## 1. Project Overview

**Sony FX3 & FX6 Virtual Machine, Cross-System Porting, and Hardware Recovery Research Lab** (`Rem021/sony-fx3-fx6-lab`, mirrored locally at [outputs/sony-fx3-fx6-lab](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab)) is an open-source systems engineering and reverse-engineering repository targeting the **Sony Cinema Line FX3 (`ILME-FX3`, v7.02, Model ID `0x91030080`)** and **FX6 (`ILME-FX6`, v6.01, Model ID `0x91040086`)** built on the **Sony CXD90057 ("Chaplin")** AArch64 platform.

The repository consolidates **19,572 open-source engineering files (~182.2 MiB)** organized across four parallel tracks:
1. **Track 1 — FX6-on-FX3 Cross-System Porting (`FX6 6.01 -> FX3 VM`)**: Booting and running the genuine FX6 6.01 Linux kernel (`4.9.135`), kernel modules (`.ko`), and Cinema Line application stack (`bootin`, `im.elf`, `appFw.so`, `libgrm.so`, `libuxengine.so`) inside the custom FX3 QEMU virtual machine.
2. **Track 2 — FX3 Native Virtual Machine & Interactive Web Menu Emulator (`AP70–AP105`, `r10–r48`)**: Custom QEMU AArch64 hardware emulation (`virt` high-DDR at `0x400000000`, ESRAM mailbox at `0xfe005000`, GICD, Sony timers, SCU, GPIO Bank5), userland OSD/GPE/DMM shims, and a one-click browser-based interactive camera menu emulator.
3. **Track 3 — FX6 6.01 Full-System Hardware Compatibility Matrix for FX3 7.02**: Byte-level comparison of Octal-SPI NOR flash layouts, Device Trees (`cxd90057.dtb`), eMMC UDA Sector 0 Sony Partition Tables (`partinf.conf`), rootfs architectures (`p7` vs. `p3`), and factory calibration redlines (`Jiritsu`, `lensfile.bin`, `ddrtraining.dat`).
4. **Track 4 — FX3 Offline Firmware Recovery Adapter (`v0.5`) & Stage 1–286 Verification Suite**: Offline inspection, build, verification, and rollback tools for the `p1` (`cnflasha1`) updater partition, plus standalone static AArch64 ELF read-only capture workers for `p1` and `boot0`/`boot1`.

---

## 2. Detailed Development Progress by Track

### Track 1: FX6 6.01 System Porting on the FX3 Virtual Machine (`FX6-on-FX3`)

- **Primary Evidence & Reports**:
  - [reports/2026-11-05-fx6-boot-gate-audit/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-05-fx6-boot-gate-audit/REPORT.md) — *Audit of Routes A, B, and C*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md) — *Independent Audit of the 180s Stable Run*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md) — *Boot-Screen `Backup.bin` Key Contract (`0x02cf0214` / `0x02cf0218`)*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json) — *Framed `/proc/<pid>/maps` Collector Review*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md) — *Automated Serial Fault & Assertion Detector*

#### 1.1 Evaluation of the Three Boot Routes
We systematically evaluated three ways to boot FX6 on the frozen FX3 VM baseline ([REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-05-fx6-boot-gate-audit/REPORT.md)):
- **Route A (FX3 Kernel + FX6 Upper Stack via Guest Veneer)**: Reached `appFw.so / Application_System_Init` dispatch on vCPU 03 and `im` `dlsym` return (`pc=0x405f10`, `x0=0x7f0377d044`), plus read-only observation of FX6 calling fixed FX3 MPR (`count=2` at `+0x268` vs. FX3 callback pointer at `+0x1d0`, returning `3`, and CAPID `initialized=0, owner=0` returning `-1021`). Blocked by strict source-freeze SHA checks on `guest_probe.py` and an automated provider security flag on the veneer loader task.
- **Route B (Address-Agnostic CP Helper + Hybrid FX6/FX3 CPIO)**: **Selected and actively advancing** (detailed in Milestones 1.2–1.7 below).
- **Route C (Direct FX6 Native `initrd.img` / Rootfs Replacement)**: Proven infeasible without platform changes because FX6's native `/sbin/init` mounts `/dev/nflasha2/3/7/8/10/11/12/15/18` block devices and loads hardware-dependent `dma330/emmc/pcieatu` kernel modules not present in the loader-only QEMU baseline.

#### 1.2 Breakthrough: Address-Agnostic CP Helper (`fx6_cp_backup_sync100_agnostic_v1`)
- **Problem**: The fixed FX3 CP backup helper hardcoded the FX3 kernel symbol `pcidma_transfer_async` at `0xffffff80083220c8`. In the FX6 6.01 kernel (`bc4925e7...`), `pcidma_transfer_async` is exported at `0xffffff8008322f70`, while `0xffffff80083220c8` lands inside `watchdog_touch_exception`. Furthermore, two hardcoded fallback addresses collided with `subsys_new_mm` and `watchdog_touch_exception`.
- **Solution**: Built [fx6-cp-backup-sync100-agnostic.c](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/cp-bind-fx6/fx6-cp-backup-sync100-agnostic.c) (`7e8d859ecb...`, 66,552 B), which validates the first `0x200` bytes of `pcidma_transfer_async` at either `0xffffff80083220c8` (FX3) or `0xffffff8008322f70` (FX6), pins the 16-byte entry, and dynamically computes `fallback_zero = api + 0x160` and `fallback_nonzero = api + 0x10`.
- **Result**: Verified in run `cp-bind-fc2ad401` (`FX3_BACKUP_CP_INSMOD_RC=0`, `FX6_SYNC100_AGNOSTIC_BIND`, `FX3_AP_NATURAL_BOOTIN_BEGIN`).

#### 1.3 Breakthrough: FX6 `appFw.so` Execution & CAPID `assert:1075` Resolution
- **Problem**: With the new CP helper and FX6 `bootin`/`im.elf`/`appFw.so` (`guest-hybrid-fx6kernel.cpio`), run `cp-bind-6e83a14a` mapped and executed `/usr/lib/appFw.so` but hit an assertion at `infra_wrapper_bb_procam_chaplin_base.cpp:1075` (`send_and_wait_cmp_i`) when sending a 10-byte audio command (`0d202d030a0001800000`, source `0x81cf6196`, target `0x92840747`) before CAPID initialization completed.
- **Solution**: Implemented `capid-preinit/fx3-capid-v50-preinit.so` (`c70fc778c9...`) scoped strictly to the 10-byte `0x032d200d` audio request, triggering `FX3_CAPID_AUDIO_PREINIT` and `FX3_HDMI_AUDIO_COMMIT command=0x32d completion=0x132d raw_status=0x580000`.
- **Result**: Verified in run `cp-bind-3f90423f` — execution advanced past the early `1075` stop into GRM graphics initialization.

#### 1.4 Breakthrough: FX6 Userland Graphics & UI Library Closure (`GRM` / `UXEngine`)
- **Problem**: Advancing past CAPID exposed missing symbols (`GRM_*`) and a null-pointer data abort (`signal 7, DABT at 0x0`) in thread `im.elf(I-AppRemoteBoar)`, followed by C++ RTTI missing symbol `_ZTIN6stella11ImageBufferE` between `liblibra.so` and FX3's older `libstella.so`.
- **Solution**: Assembled the full FX6 userland UI/graphics library closure into the hybrid CPIO (`grmreal3` through `grmreal10`):
  - `usr/lib/libgrm.so`, `usr/lib/libma.so`, `usr/lib/libgrm_bmp.so`, and kernel module `usr/kmod/grm_ma.ko`
  - `usr/lib/libInfraAppRemoteBoard.so`, `usr/lib/liblibra.so`, `usr/lib/libstella.so`
  - `usr/lib/libux_core.so`, `usr/lib/libuxengine.so`, `usr/lib/libux_wgtlay.so`, `usr/lib/libtriones.so`, `usr/lib/libandromeda.so`, `usr/lib/libgemini.so`, `usr/lib/libalcor.so`, `usr/lib/libtextrm.so`, `usr/lib/libwtle.so`, `usr/lib/libitype.so`
- **Result**: `I-AppRemoteBoar` crash and dynamic linker errors were completely eliminated; execution reached the main `im.elf(AppFw)` thread (`cp-bind-2f0f312b`).

#### 1.5 Deep Debugging of Blocking Primitives & Achieving 180-Second Zero-Oops Stability (`MEDIA_START`)
Once inside the `im.elf(AppFw)` main thread, we systematically diagnosed and resolved five sequential hardware/IPC dependencies:
1. **`grm::FrameBuffer::setSize` Null `this` & `UXEngine` Zero-Size Panic**:
   - Disassembly of `libgrm.so` at `0x2303c` (`strh w1, [x0, #0x14]`) and `0x22ab0` (`FBResourceManager::initializeFrameBuffer`) showed `[manager + 0x8]` (`FrameBuffer*`) was `NULL`. Constructing a minimal `FrameBuffer` (`libgrm-fbinit2..9.so`) avoided the SEGV, and intercepting `ux::gfxeng::Screen::setAreaInFramebuffer` (`libuxengine.so+0x7b6ac`) prevented `ux::core::sys_panic()` on `0x0` dimensions (using FX6's native `1024×540` area).
2. **Kernel `backup.ko` `Internal error` (`brk #0x3e8`)**:
   - Around 31s of guest uptime, `Backup_nread` / `backup_put_cp_wt_data` executed a hardcoded `brk #0x3e8` (`007d20d4`) at `.text+0x75c` (file offset `0x7c4`). Patching `.text+0x75c` to `b 0x700` (`e9ffff17` in `backup-bug-skip.ko`) eliminated the kernel panic (`grmreal21`, run `cp-bind-9e6527aa`).
3. **Unmasking the `std::future::get` Async Logging Blocker (`0x2159c50`)**:
   - When `AppFw` slept in `futex_wait` (`val=0x80000000`), we built a suite of custom interposition probes (`libpthread-diag.so`, `libcvdiag.so`, `libmutexdiag.so`, `libjoindiag.so`, `libatomicdiag.so`). `libatomicdiag.so` (`grmreal40`) pinpointed the exact caller: `c0 = appFw+0x1d6d104` (`_M_futex_wait_until`), `c1 = appFw+0x2159bd8` (`std::future::get` helper at `0x2159c50`), called exclusively from `0x20eca84` inside an asynchronous logging wrapper (`0x20eca5c`).
   - Bypassing `0x2159c50` (`mov w0, #0; ret` in `appFw-future-skip.so`, `grmreal41`) immediately unblocked `Application_System_Init` and **for the first time reached `FX3_MEDIA_START_BRANCH` (`eid=20`)**!
4. **Resolving `upm.ko` Sensor DFS Measurement Kernel Oops**:
   - Reaching `MEDIA_START` triggered `UPM_TSK_FRAMEWO` (PID 214) to call `upm_senser_dfs_measurement+0x4a0` (`blr x2` with an unmapped virtual address `0xffffff8a00905856`). Replacing the callsite at `+0x4a0` with `mov w0, #0` (`upm-callsite-skip.ko`, `grmreal46`) eliminated the kernel Oops.
   - In 180-second run `cp-bind-66ed0f78`, the system ran continuously for 180s with **0 Kernel Panics / 0 Oops**, emitting `5,508,980` bytes of serial logs, `FX3_MEDIA_START_BRANCH` ×2, `FX3_UI` ×3265, and `FX3_GPE` ×170.
5. **Removing the `fx3-ui-gate-v1.so` Wrapper (`grmreal54`)**:
   - `libconddiag.so` revealed that `fx3-ui-gate-v1.so` was intercepting `std::condition_variable::wait`; removing it from `LD_PRELOAD` (`grmreal54`) exposed the true native wait in `appFw.so+0x1acd984`.

#### 1.6 Breakthrough: Host-to-Native Key Input Injection Verified
- In runs `cp-bind-90cfb3b1` and `cp-bind-75cdd20e` on `grmreal54`, we used `gate_input96.InputGate` over QEMU's GDB physical memory interface (`0x41df00000`) to inject a 4-step key sequence:
  - Step 1: `0x1ab` (`MENU`)
  - Step 2: `0x30` (`DOWN`)
  - Step 3: `0x1ac` (`OK/UP`)
  - Step 4: `0x1af` (`LEFT`)
- **Result**: All 4 steps were accepted and processed by the native FX6 input worker (`FX3_KEY95_STEP_DONE` ×4, `FX3_KEY_CACHE` ×4, `native_receiver_queue_exists=1`, `wait_result=0`). This proved that the host-to-FX6 input pipeline is fully functional.

#### 1.7 Current Frontier: DMM Display Memory vs. GPE Capture & Boot-Screen Contract
Why did key injection succeed without producing visible menu pixels? Our latest rounds (`grmreal56`–`grmreal62` and parallel audits) established the exact reasons:
1. **DMM (Display Memory Manager) is the True Display Backend**:
   - Dumping the `FrameBuffer` object (`self=0x7faf3bf3c0` in `libgrm-fbinit11`) showed `word1` (pixel buffer pointer) = `0` because the minimal shim recorded `1024×540` without allocating backing BMP memory.
   - Dumping the two 1.25 MiB GPE `type=0x403` surfaces via QMP `pmemsave` (`phys=0x43ae96000`) yielded all zeros because `FX3_GPE_MODEL_INIT mode=request_capture` uses those surfaces for capture requests, not display scanout.
   - String and cross-reference extraction from FX6 `appFw.so` confirmed that real display surfaces are allocated via **DMM**: `dmm_alloc_and_open`, `dmm_open`, `dmm_mmap`, `dmm_get_unit_size`, `set_dmm_info`. Runs `grmreal60`–`grmreal62` ([run_gpecap9_once.py](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/cp-bind-fx6/run_gpecap9_once.py)) are actively probing `/proc/dmm_info`, `/proc/dmm_units`, `/proc/dmm_extents`, and `/proc/dmm_reserve` at 45s uptime.
2. **Independent Audit & Boot-Screen `Backup.bin` Contract (`0x02cf0214` / `0x02cf0218`)**:
   - Our independent read-only audit ([REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md)) identified 4 non-fatal C++ assertions in `cp-bind-66ed0f78`: `model_api.cpp:3147` (line 11688), `model_api.cpp:3176` (line 11738), and `infra_wrapper_bb_procam_chaplin_base.cpp:1075` (lines 14502 & 14734).
   - Static reverse-engineering ([REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md)) proved that `model::model_api::detail::set_model_for_boot_screen()` asserts because it reads Backup keys **`0x02cf0214`** and **`0x02cf0218`** and requires their values to be **`0` or `1`**. In the FX6 `Backup.bin` template, these keys are 1-byte records (`00` and `01`), whereas the FX3 seed populates 4-byte patterns (`16161616` and `19191919`).
3. **Offline-Accepted Diagnostic Packages Ready for Next Run**:
   - **Framed `/proc/<pid>/maps` Collector ([fx3_map_snapshot_v2.c](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-observer/src/fx3_map_snapshot_v2.c))**: Statically linked AArch64 ELF (`ET_EXEC`, 122,264 B, SHA `9df5a10a...`) integrated into `fx6-map-observer-grmreal46.cpio`, verified across 59 manifest hashes and a 4-stop HostRunner/QMP/RSP E2E simulation ([fx6-map-integration-coordinator-final-review.json](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json)).
   - **Serial Fault & Assertion Detector ([detect_serial_faults.py](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/detect_serial_faults.py))**: Verified across 26 manifest hashes and 7 unit tests to prevent any future run receipt from overlooking `assert at` lines ([REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md)).

---

### Track 2: FX3 Native Firmware Virtual Machine & Interactive Web Menu Emulator

- **Primary Evidence & Reports**:
  - [outputs/fx3-vm/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/README.md) & [reports/2026-11-01-fx3-vm-deployment/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-deployment/README.md) — *FX3 Minimal Research VM*
  - [reports/2026-11-01-fx3-vm-resumed-repair/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/README.md) — *AP70–AP105 Menu Bring-Up Progression*
  - [outputs/fx3-vm-trial/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/README.md) & [outputs/fx3-vm-trial/新版验收记录.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/新版验收记录.md) — *Deployed Web UI Trial (`r10`) & `r11`–`r48` Verification Records*

1. **Custom QEMU AArch64 Hardware Modeling**:
   - Patches QEMU's `virt` machine ([fx3-esram-high-ddr.patch](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) and [work/fx3-vm-20261101/host/patches](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/patches)) to place main DDR RAM at Sony's physical base `0x400000000` (up to 5 GiB), instantiate the 4 KiB ESRAM mailbox at `[0xfe005000, 0xfe006000)`, map the fixed GICD virtual address, and emulate Sony hardware timers (`FX3_VM_SONY_TIMER`), SCU requests (`FX3_VM_SCU_REQUEST`), and GPIO Bank5 (`FX3_VM_GPIO_BANK5`).
2. **AP70–AP105 Full Camera Menu Bring-Up**:
   - Over 35 iterative engineering stages documented in [reports/2026-11-01-fx3-vm-resumed-repair](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/README.md), we resolved every subsystem required for `im.elf` and `appFw.so` to render the genuine Sony FX3 menu:
     - **AP70–AP76**: LCD/OSD plane initialization, `icrypt` loading, ADF audio muting, GPE v13 command processor, beep registration, hardware timer observation, and `icdt` ADF file correlation.
     - **AP77–AP84**: UI start gate, timecode boot, VDF/HDMI tail, owned pin & deferred callbacks, `skd` hardware-unavailable UI clear, UUD second pin & DMM `0x1d9`, face DMM realcopy & GPE v14, and CPU clock speed scaling.
     - **AP85–AP92**: Software OSD ring buffer, OSD pool display, UUD queue first screen, CP backup reset/shutdown handling, backup replay first screen, GPE resource format-2 first text rendering, synthetic key input, and media slot detection/mount observation.
     - **AP93–AP105**: Empty media slots first-time setup (`Area/Date/Time`), offscreen child stretch (`GPE94`), host-step physical memory key input gate (`KEY95`/`KEY96`), R2 menu navigation, read-only date capture (`DATE98`/`DATE99`), native `/setting/Backup.bin` file sync (`AP100`/`AP101`), software LDEC LZ77 asset decompression (`AP103`), API16 clean shutdown restoration, and passive completion tracing (`AP104`/`AP105`).
3. **Deployed Interactive Web Menu Emulator (`r10`) & Ongoing Refinements (`r11`–`r48`)**:
   - **Deployed Entry (`r10`)**: Double-clicking [FX3菜单.command](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/FX3菜单.command) starts a local HTTP server (`127.0.0.1:<dynamic_port>`) with a 4096-key / 60-minute budget. Verified in a **32-key, 674.5-second live browser run ([NAV32-RESULT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/NAV32-RESULT.md))** navigating through Setup, Focus, and Playback menus with per-frame visual confirmation and 100% clean API16 restoration.
   - **Iterative Refinements (`r11`–`r48`)**:
     - `r15`–`r17`: Decoupled hot-path diagnostic counters in normal RAM from reserved-RAM snapshot publishing (`N1` vs `N64` fixed-layout 58,856-byte CPIO slot), achieving ~40.1s Start-to-first-OSD-frame latency.
     - `r18`–`r39`: Eliminated browser image-load vs. status-poll race conditions (`v25-r18-frame-admission`) and hardened single-execution cleanup evidence (`r39-cleanup-evidence-candidate`, 40 fault-injection tests).
     - `r41`–`r48`: Added command-entry timing instrumentation (`r41`), expanded automated step review budget from 20s to 60s (`r44`), and integrated runtime recovery/cleanup verification (`r47`/`r48`).

---

### Track 3: FX6 6.01 Full-System Hardware Compatibility Matrix for FX3 7.02

- **Primary Report**: [reports/2026-11-03-fx6-full-system-to-fx3/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-03-fx6-full-system-to-fx3/README.md)

Our static audit of the official FX6 6.01 (`0x91040086`) and FX3 7.02 (`0x91030080`) firmware packages established the following ground-truth hardware findings:

1. **100% Identical Bootloader & SoC Memory Map**:
   - `0800_appli/setting/cxd90057.dtb` (16,875 B, SHA256 `c5735ad9...`), `pformat_config.txt` (1,274 B, SHA256 `21cd5b29...`), and `LdrBkupList.txt` (650 B, SHA256 `ae537183...`, 65 Backup keys) are **100% byte-for-byte identical** between FX3 7.02 and FX6 6.01.
   - Octal-SPI NOR physical layout (`infomisc.dat` EXBL @ Sector 0, `DGU.bin` @ Sector 4 → `0xFE040800`, `LdrBkup.bin` @ Sector 68 → `0xFE048800`, `loader_nor.bin` @ Sector 72 → `0xFE049000`, `MIS.bin+ddrtraining.dat` @ Sector 512 → `0xFE080000`, `pcie_phy_fw.bin` @ Sector 768 → `0xFE0A0000`, `cpapp-b.bin` @ Sector 4096 → `0x00108000`) is completely isomorphic.
   - **Normal Cold Boot has zero cross-model signature or Model ID rejection**: `loader_nor.bin` reads the `0xfa0080` descriptor table in `p2:/Backup.bin` (where Bank 0 AP load addresses `0x400001000` / `0x400002000` / `0x400080000` / `0x401000000` / `0x408000000` are identical). Cross-model gates (`dat2` Model ID `91030080` vs `91040086`, `dat3` Region, and ECDSA/AES signature checks) exist **only** in the `p1` Updater userland (`sauu` / `sdfileinput.elf`).
2. **eMMC UDA Sector 0 Partition Table (`partinf.conf`) & Rootfs Divergence**:
   - Logical partitions `/dev/nflasha1..30` are defined by a 512-byte Sony Partition Table (magic `"8246"`, version `"2.00"`, 30 entries) written to **eMMC UDA Sector 0** by `edisx.elf` and parsed by `emmc.ko`.
   - Partitions `p1` through `p11` have identical start sectors and sizes on FX3 and FX6.
   - **Rootfs Architecture (`p7` vs `p3`)**: FX3 mounts `/dev/nflasha7` (`p7`, ext2) via `/sbin/initrc/setup_rootfs` and `pivot_root`s into `/rootfs`. FX6 has **no `nflasha7` image and no `setup_rootfs`**; FX6 runs `/sbin/init2` directly from the `p3` RAM disk (`/dev/ram0`) and mounts `/dev/nflasha15` (`p15`) at `/usr`.
   - **Partition Shift & Missing `p20`/`p21` on FX3**: Starting at `p12` (`/cert`), FX6 shrinks `p12` from 40 MiB to 20 MiB, shifting `p13`, `p15` (`/usr`, 500 MiB), and `p18` (`/lens`, 20 MiB) forward by 20 MiB (`0xA000` sectors). Crucially, FX6 introduces **`p20`** (100 MiB `/usr/data/lut`, hardcoded in `libInfraSetupFile.so` & `appFw.so`) and **`p21`** (44.5 MiB `/etc/opelog`, hardcoded in `libInfraKikiLogGenerator.so` & `kikilog.ko`), whereas on FX3 `p20` and `p21` have size `0` (FX3 stores LUTs in `p30`).
3. **Mandatory Calibration Redlines & Two-Stage Reversible Hardware Plan**:
   - **Never overwrite without full backup**: `p6` (`Jiritsu`), `p18` (`/lens/lensfile.bin`), `/setting/psd.bin`, `/setting/defdet.bin`, and SPI NOR `ddrtraining.dat` (offset `0x3e210fc`) contain per-camera factory sensor/lens/DDR calibration data.
   - **Hard Stop Rule**: No cross-partition flash or `edisx.elf` Sector 0 modification is permitted until full readback backups of FX3 Sector 0, `p1/2/3/5/6/7/8/12/13/15/18/23/30`, and SPI NOR are verified.

---

### Track 4: FX3 Offline Firmware Recovery Adapter (`v0.5`) & Stage 1–286 Verification Suite

- **Primary Evidence & Reports**:
  - [outputs/fx3-recovery-adapter/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-recovery-adapter/README.md) & [reports/2026-11-01-fx3-recovery-adapter-v05/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-recovery-adapter-v05/README.md)
  - [reports/2026-11-04-fx3-firmware-recovery/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-04-fx3-firmware-recovery/README.md) — *Stages 1–286 Complete Verification Chain*

1. **Offline Recovery Adapter (`v0.5`)**:
   - Provides four deterministic subcommands (`inspect`, `build`, `verify`, `rollback`) via [fx3_recovery_adapter.py](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-recovery-adapter/bin/fx3_recovery_adapter.py) for offline modification of the FX3 `0700_part_image_nflasha1.cramfs` (`p1` updater partition).
   - Injects a read-only SD diagnostic script (`/etc/init.d/rcS`) into a standard Linux CramFS image while generating a bit-for-bit verified rollback manifest.
2. **Stage 1–286 Hardware-Boundary & Capture Worker Suite**:
   - Documents the complete evolution from dual-layer encryption analysis (`FUP1` outer wrapper + `PFU2` inner payload) and `sauu` state-machine reverse engineering to standalone static AArch64 ELF read-only capture workers (`fx3_p1_capture_worker` for `/dev/nflasha1` and `fx3_boot_capture_worker` for `/dev/nflashaB0`/`B1`) verified under `qemu-aarch64` emulation.

---

# 第二部分 — 简体中文完整项目简介与详细开发进度

## 1. 项目总览

**Sony FX3 / FX6 虚拟机、跨机型系统移植与固件恢复研究实验室**（GitHub 仓库：`https://github.com/Rem021/sony-fx3-fx6-lab`，本地镜像路径：[outputs/sony-fx3-fx6-lab](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab)）是一个面向 **Sony Cinema Line FX3（`ILME-FX3`，固件 v7.02，Model ID `0x91030080`）** 与 **FX6（`ILME-FX6`，固件 v6.01，Model ID `0x91040086`）**（均基于 **Sony CXD90057 "Chaplin"** AArch64 平台）的开源系统工程与逆向研究仓库。

本仓库共汇集了 **19,572 个自研工程文件（约 182.2 MiB）**，涵盖四大核心研发主线：
1. **主线一：FX6 系统向 FX3 虚拟机的跨机型移植（`FX6 6.01 -> FX3 VM`）**：在自研 FX3 QEMU 虚拟机上直接引导并运行 FX6 6.01 原生 Linux 内核（`4.9.135`）、内核模块（`.ko`）及 Cinema Line 完整上层相机主程序栈（`bootin`、`im.elf`、`appFw.so`、`libgrm.so`、`libuxengine.so`）。
2. **主线二：FX3 原生固件虚拟机与交互式网页菜单模拟器（`AP70–AP105`、`r10–r48`）**：定制 QEMU AArch64 硬件建模（`0x400000000` 高地址 5 GiB DDR、`0xfe005000` ESRAM 邮箱、GICD、Sony 硬件定时器、SCU、GPIO Bank5）、用户态 OSD/GPE/DMM 兼容层，以及支持双击启动的浏览器交互式 FX3 菜单试用版。
3. **主线三：FX6 6.01 全系统刷入 FX3 7.02 硬件兼容性评估矩阵**：从 Octal-SPI NOR 闪存布局、设备树（`cxd90057.dtb`）、eMMC UDA 0 扇区索尼私有分区表（`partinf.conf`）、根文件系统架构（`p7` 对比 `p3`）到单机出厂校准红线（`Jiritsu`、`lensfile.bin`、`ddrtraining.dat`）的字节级对比与两阶段无损验证方案。
4. **主线四：FX3 离线固件恢复适配器（`v0.5`）与 Stage 1–286 固件恢复验证体系**：针对 `p1`（`cnflasha1`）升级分区的离线检查、构建、校验与回滚工具，以及针对 `p1` 和 `boot0`/`boot1` 的独立静态链接 AArch64 ELF 只读导出程序。

---

## 2. 四大主线详细开发进度

### 主线一：FX6 6.01 系统在 FX3 模拟器上的移植进度（`FX6-on-FX3`）

- **核心技术报告与证据链**：
  - [reports/2026-11-05-fx6-boot-gate-audit/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-05-fx6-boot-gate-audit/REPORT.md) — *路线 A / B / C 三路冷启动门禁审计*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md) — *180 秒零 Oops 稳定运行独立审计报告*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md) — *Boot-Screen `Backup.bin` 键值契约逆向报告（`0x02cf0214` / `0x02cf0218`）*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json) — *进程映射采集器集成验收报告*
  - [work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md) — *串口故障与断言自动检测器报告*

#### 1.1 三条启动路线的全面评估
在 [REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-05-fx6-boot-gate-audit/REPORT.md) 中，我们对在冻结的 FX3 虚拟机基线上启动 FX6 进行了三条路线的严格实测对比：
- **路线 A（FX3 内核 + Guest Veneer 加载 FX6 上层应用栈）**：已实测将执行流推进至 vCPU 03 上的 `appFw.so / Application_System_Init` 分发与 `im` 的 `dlsym` 返回（`pc=0x405f10`，`x0=0x7f0377d044`），并只读观测到 FX6 调用固定 FX3 MPR（`+0x268` 处 `count=2` 对比 FX3 `+0x1d0` 回调指针，返回 `3`）及 CAPID（`initialized=0, owner=0` 返回 `-1021`）。受限于 `guest_probe.py` 源码冻结 SHA 校验及 Veneer 加载任务触发的上游安全拦截，转入路线 B 主攻。
- **路线 B（地址无关 CP 辅助模块 + FX6/FX3 混合 CPIO 根文件系统）**：**当前主力推进路线**，已取得从内核到主界面状态机及按键响应的全面突破（详见下文 1.2–1.7）。
- **路线 C（直接替换 FX6 原生 `initrd.img` / Rootfs）**：已证实不可直接用于无块设备加载基线，因为 FX6 原生 `/sbin/init` 强依赖 `/dev/nflasha2/3/7/8/10/11/12/15/18` 分区挂载与 `dma330/emmc/pcieatu` 硬件内核模块。

#### 1.2 里程碑突破一：攻克内核符号偏移冲突（`fx6_cp_backup_sync100_agnostic_v1`）
- **问题根因**：原 FX3 专用 CP 辅助模块将内核符号 `pcidma_transfer_async` 硬编码在 FX3 内核地址 `0xffffff80083220c8`。而在 FX6 6.01 内核（`bc4925e7...`）中，`pcidma_transfer_async` 位于 `0xffffff8008322f70`，旧地址 `0xffffff80083220c8` 恰好落入 `watchdog_touch_exception` 函数体内部；同时两个硬编码回退地址也与 `subsys_new_mm` 发生冲突。
- **解决方案**：开发地址无关内核辅助模块 [fx6-cp-backup-sync100-agnostic.c](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/cp-bind-fx6/fx6-cp-backup-sync100-agnostic.c)（`7e8d859ecb...`，66,552 字节），自动校验 `0xffffff80083220c8`（FX3）与 `0xffffff8008322f70`（FX6）的前 `0x200` 字节指令特征并锁定 16 字节入口，动态计算 `fallback_zero = api + 0x160` 与 `fallback_nonzero = api + 0x10`。
- **实测结果**：在运行 `cp-bind-fc2ad401` 中一次通过，日志确认 `FX3_BACKUP_CP_INSMOD_RC=0`、`FX6_SYNC100_AGNOSTIC_BIND`、`FX3_AP_NATURAL_BOOTIN_BEGIN`。

#### 1.3 里程碑突破二：打通 FX6 `appFw.so` 初始化与 CAPID 音频预初始化（解决早期 `assert:1075`）
- **问题根因**：载入 FX6 原生 `bootin`、`im.elf` 与 `/usr/lib/appFw.so`（`guest-hybrid-fx6kernel.cpio`）后，运行 `cp-bind-6e83a14a` 成功映射并执行 `appFw.so`，但在发送 10 字节音频命令（`0d202d030a0001800000`，源 `0x81cf6196`，目标 `0x92840747`）时因 CAPID 尚未就绪，触发 `infra_wrapper_bb_procam_chaplin_base.cpp:1075`（`send_and_wait_cmp_i`）断言停止。
- **解决方案**：编写精确作用于该 10 字节 `0x032d200d` 音频请求的 `capid-preinit/fx3-capid-v50-preinit.so`（`c70fc778c9...`），在请求到达时完成 `FX3_CAPID_AUDIO_PREINIT` 与 `FX3_HDMI_AUDIO_COMMIT command=0x32d completion=0x132d raw_status=0x580000`。
- **实测结果**：运行 `cp-bind-3f90423f` 成功跨越早期 `1075` 断言，首次进入 FX6 图形与 UI 初始化阶段。

#### 1.4 里程碑突破三：补齐 FX6 用户态图形与 UI 动态库完整依赖闭环（`GRM` / `UXEngine`）
- **问题根因**：跨过 CAPID 后，先后��露出 `GRM_*` 符号缺失、`im.elf(I-AppRemoteBoar)` 线程空指针数据中止（`signal 7, DABT at 0x0`），以及 `liblibra.so` 与 FX3 旧版 `libstella.so` 之间的 C++ RTTI 符号 `_ZTIN6stella11ImageBufferE` 不匹配。
- **解决方案**：在 `grmreal3` 至 `grmreal10` 迭代中，将 FX6 原生图形与 UI 库完整闭环打包进混合 CPIO：
  - `usr/lib/libgrm.so`、`usr/lib/libma.so`、`usr/lib/libgrm_bmp.so` 及内核模块 `usr/kmod/grm_ma.ko`
  - `usr/lib/libInfraAppRemoteBoard.so`、`usr/lib/liblibra.so`、`usr/lib/libstella.so`
  - `usr/lib/libux_core.so`、`usr/lib/libuxengine.so`、`usr/lib/libux_wgtlay.so`、`usr/lib/libtriones.so`、`usr/lib/libandromeda.so`、`usr/lib/libgemini.so`、`usr/lib/libalcor.so`、`usr/lib/libtextrm.so`、`usr/lib/libwtle.so`、`usr/lib/libitype.so`
- **实测结果**：彻底消除 `I-AppRemoteBoar` 崩溃与动态链接错误，执行流顺利进入主线程 `im.elf(AppFw)`（`cp-bind-2f0f312b`）。

#### 1.5 里程碑突破四：逐一攻克 5 大底层阻塞点，实现 180 秒零 Oops 稳定运行并进入 `MEDIA_START`
进入 `im.elf(AppFw)` 主线程后，我们通过反汇编与自定义探针逐一诊断并解决了 5 个串联阻塞：
1. **`grm::FrameBuffer::setSize` 空指针与 `UXEngine` 零尺寸崩溃**：
   - 反汇编 `libgrm.so` 的 `0x2303c`（`strh w1, [x0, #0x14]`）与 `0x22ab0`（`FBResourceManager::initializeFrameBuffer`）发现 `[manager + 0x8]`（`FrameBuffer*`）为空。通过构造最小 `FrameBuffer` 对象（`libgrm-fbinit2..9.so`）并在 `ux::gfxeng::Screen::setAreaInFramebuffer`（`libuxengine.so+0x7b6ac`）中将 `0×0` 修正为 FX6 原生 `1024×540`，消除了 SEGV 与 `ux::core::sys_panic()`。
2. **修复内核模块 `backup.ko` 硬编码断点崩溃（`brk #0x3e8`）**：
   - 系统运行至约 31 秒时，`Backup_nread` / `backup_put_cp_wt_data` 触发 `.text+0x75c`（文件偏移 `0x7c4`）处的 `brk #0x3e8`（`007d20d4`）导致内核 Panic。将该处修补为跳转到统一错误返回出口 `b 0x700`（`e9ffff17`，`backup-bug-skip.ko`）后，内核 Panic 彻底消失（`grmreal21`，`cp-bind-9e6527aa`）。
3. **定位并解除 `std::future::get` 异步日志死锁（`0x2159c50`）**：
   - 针对 `AppFw` 在 `futex_wait`（`val=0x80000000`）处的挂起，开发了 `libpthread-diag.so`、`libcvdiag.so`、`libmutexdiag.so`、`libjoindiag.so`、`libatomicdiag.so` 系列诊断探针。在 `grmreal40` 中通过 `libatomicdiag.so` 精确定位调用栈：`c0 = appFw+0x1d6d104`（`_M_futex_wait_until`），`c1 = appFw+0x2159bd8`（`0x2159c50` 处的 `std::future::get` 辅助函数），其唯一调用方位于 `0x20eca84`（异步日志包装器 `0x20eca5c`）。
   - 在 `appFw-future-skip.so`（`grmreal41`）中将 `0x2159c50` 旁路为 `mov w0, #0; ret` 后，`Application_System_Init` 立即解除阻塞，**首次成功抵达相机媒体启动主状态机分支 `FX3_MEDIA_START_BRANCH`（`eid=20`）**！
4. **修复 `upm.ko` 传感器 DFS 测量内核 Oops**：
   - 进入 `MEDIA_START` 后唤醒了内核线程 `UPM_TSK_FRAMEWO`（PID 214），在 `upm_senser_dfs_measurement+0x4a0` 处执行 `blr x2`（寄存器 `x2=0xffffff8a00905856` 为未映射虚拟地址）触发 Oops。将 `+0x4a0` 调用点替换为 `mov w0, #0`（`upm-callsite-skip.ko`，`grmreal46`）后，内核 Oops 彻底消除。
   - 在随后的 180 秒长稳测试 `cp-bind-66ed0f78` 中，FX6 内核与主程序连续稳定运行 180 秒，**0 Panic / 0 Oops**，输出 `5,508,980` 字节串口日志，触发 `FX3_MEDIA_START_BRANCH` 2 次、`FX3_UI` 3265 次、`FX3_GPE` 170 次。
5. **移除 `fx3-ui-gate-v1.so` 拦截层（`grmreal54`）**：
   - 通过 `libconddiag.so` 发现 `fx3-ui-gate-v1.so` 拦截了 `std::condition_variable::wait`；在 `grmreal54` 中将其从 `LD_PRELOAD` 移除后，暴露出 `appFw.so+0x1acd984` 的原生事件循环等待。

#### 1.6 里程碑突破五：宿主机向 FX6 原生输入队列注入物理按键验证成功
- 在基于 `grmreal54` 的运行 `cp-bind-90cfb3b1` 与 `cp-bind-75cdd20e` 中，通过 `gate_input96.InputGate` 经由 QEMU GDB 物理内存接口（`0x41df00000`）向虚拟机连续注入 4 步按键序列：
  - 第 1 步：`0x1ab`（`MENU` 菜单键）
  - 第 2 步：`0x30`（`DOWN` 下方向键）
  - 第 3 步：`0x1ac`（`OK/UP` 确认/上方向键）
  - 第 4 步：`0x1af`（`LEFT` 左方向键）
- **实测结果**：全部 4 步按键均被 FX6 原生按键接收线程成功消费并确认（`FX3_KEY95_STEP_DONE` ×4、`FX3_KEY_CACHE` ×4、`native_receiver_queue_exists=1`、`wait_result=0`），证明宿主机到 FX6 的按键输入链路已完全跑通。

#### 1.7 当前最新研发前沿：DMM 显示内存扫描输出与 Boot-Screen 备份键值契约
为什么按键已经成功送达 FX6 内部，但导出的画面表面仍是全 0？我们在最新一轮实验（`grmreal56`–`grmreal62`）与并行审计中查明了根本原因：
1. **DMM（Display Memory Manager）才是 FX6 真正的显示扫描后端**：
   - 导出 `FrameBuffer` 对象内存（`libgrm-fbinit11` 中的 `self=0x7faf3bf3c0`）发现其 `word1`（像素缓冲区指针）为 `0`，因为早期最小桩仅记录了 `1024×540` 尺寸而未分配底层位图内存。
   - 通过 QMP `pmemsave` 导出两个 1.25 MiB 的 GPE `type=0x403` 表面（`phys=0x43ae96000`）全为 0，是因为日志 `FX3_GPE_MODEL_INIT mode=request_capture` 表明它们仅用于捕获请求（`request_capture`），而非显示输出。
   - 对 FX6 `appFw.so` 的字符串与交叉引用分析证实，真实显示平面是通过 **DMM（Display Memory Manager）** 分配的：`dmm_alloc_and_open`、`dmm_open`、`dmm_mmap`、`dmm_get_unit_size`、`set_dmm_info`。最新运行 `grmreal60`–`grmreal62`（[run_gpecap9_once.py](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/cp-bind-fx6/run_gpecap9_once.py)）正在 45 秒时间点探测 `/proc/dmm_info`、`/proc/dmm_units`、`/proc/dmm_extents` 与 `/proc/dmm_reserve`。
2. **独立审计与 Boot-Screen `Backup.bin` 键值契约（`0x02cf0214` / `0x02cf0218`）**：
   - 独立只读审计（[REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md)）在 180 秒日志中识别出 4 处非致命 C++ 断言：`model_api.cpp:3147`（第 11688 行）、`model_api.cpp:3176`（第 11738 行）以及 `infra_wrapper_bb_procam_chaplin_base.cpp:1075`（第 14502 与 14734 行）。
   - 静态逆向报告（[REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md)）证明：`model::model_api::detail::set_model_for_boot_screen()` 之所以触发断言，是因为它读取了 Backup 键 **`0x02cf0214`** 与 **`0x02cf0218`**，并严格要求其值只能为 **`0` 或 `1`**。在 FX6 原生 `Backup.bin` 模板中这两个键是 1 字节记录（`00` 和 `01`），而当前混用的 FX3 种子填入的是 4 字节模式（`16161616` 和 `19191919`）。将该两项修正为 `0`/`1` 是解锁开机首屏状态机的关键一步。
3. **已通过离线验收、随时可投入下一轮运行的诊断组件**：
   - **进程映射采集器（[fx3_map_snapshot_v2.c](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-observer/src/fx3_map_snapshot_v2.c)）**：静态链接 AArch64 ELF（`ET_EXEC`，122,264 字节，SHA `9df5a10a...`），已集成至 `fx6-map-observer-grmreal46.cpio`，通过 59 项哈希校验与 4 停靠点端到端模拟测试（[fx6-map-integration-coordinator-final-review.json](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-map-integration-coordinator-final-review.json)）。
   - **串口故障与断言自动检测器（[detect_serial_faults.py](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/detect_serial_faults.py)）**：通过 26 项清单哈希校验与 7 项单元测试，确保后续任何运行回执都不会遗漏 `assert at` 断言（[REPORT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/REPORT.md)）。

---

### 主线二：FX3 原生固件虚拟机与交互式网页菜单模拟器（`AP70–AP105`、`r10–r48`）

- **核心技术报告与证据链**：
  - [outputs/fx3-vm/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/README.md) 与 [reports/2026-11-01-fx3-vm-deployment/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-deployment/README.md) — *FX3 最小研究虚拟机*
  - [reports/2026-11-01-fx3-vm-resumed-repair/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/README.md) — *AP70–AP105 菜单完整点亮演进报告*
  - [outputs/fx3-vm-trial/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/README.md) 与 [outputs/fx3-vm-trial/新版验收记录.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/新版验收记录.md) — *已部署网页版试用入口（`r10`）及 `r11`–`r48` 持续优化验收记录*

1. **定制 QEMU AArch64 硬件建模**：
   - 通过补丁（[fx3-esram-high-ddr.patch](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) 及 [work/fx3-vm-20261101/host/patches](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/patches)）改造 QEMU `virt` 机型：将主 DDR 内存映射至索尼物理基址 `0x400000000`（最高 5 GiB），在 `[0xfe005000, 0xfe006000)` 实例化 4 KiB ESRAM 共享邮箱，映射固定 GICD 虚拟地址，并模拟索尼硬件定时器（`FX3_VM_SONY_TIMER`）、SCU 请求（`FX3_VM_SCU_REQUEST`）与 GPIO Bank5（`FX3_VM_GPIO_BANK5`）。
2. **AP70–AP105 相机完整菜单点亮工程**：
   - 在 [reports/2026-11-01-fx3-vm-resumed-repair](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/README.md) 记录的 35 个连续工程阶段中，打通了 `im.elf` 与 `appFw.so` 渲染真实 FX3 菜单所需的全部子系统：
     - **AP70–AP76**：LCD/OSD 显示平面初始化、`icrypt` 加载、ADF 音频静音、GPE v13 命令处理器、蜂鸣器注册、硬件定时器观测及 `icdt` 关联。
     - **AP77–AP84**：UI 启动门禁、时间码启动、VDF/HDMI 尾部初始化、延迟回调、无硬件状态下 `skd` 菜单遮罩清除、UUD 二次绑定与 DMM `0x1d9`、人脸 DMM 真实拷贝与 GPE v14、CPU 时钟频率调节。
     - **AP85–AP92**：软件 OSD 环形缓冲区、OSD 缓冲池显示、UUD 队列首屏、CP 备份复位/关机处理、备份回放首屏、GPE 格式 2 首次文字渲染、合成按键输入及存储卡槽检测观测。
     - **AP93–AP105**：空卡槽首次开机设置（区域/日期/时间）、离屏子表面拉伸（`GPE94`）、宿主机物理内存按键门禁（`KEY95`/`KEY96`）、R2 菜单导航、只读日期捕获（`DATE98`/`DATE99`）、原生 `/setting/Backup.bin` 文件同步（`AP100`/`AP101`）、软件 LDEC LZ77 图标资源解压（`AP103`）、API16 干净停机恢复及被动完成追踪（`AP104`/`AP105`）。
3. **已部署交互式网页菜单模拟器（`r10`）与后续迭代（`r11`–`r48`）**：
   - **双击即用入口（`r10`）**：双击 [FX3菜单.command](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/FX3菜单.command) 即可启动本地网页控制台（`127.0.0.1:<动态端口>`，支持 4096 键 / 60 分钟连续操作）。已在 **32 键、674.5 秒真实浏览器端到端巡航测试（[NAV32-RESULT.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm-trial/NAV32-RESULT.md)）** 中完整遍历设置、对焦、回放等菜单并完成 API16 100% 干净恢复。
   - **持续优化迭代（`r11`–`r48`）**：
     - `r15`–`r17`：将热路径诊断计数器与保留内存快照发布解耦（`N1` 与 `N64` 固定 58,856 字节 CPIO 槽位），实现点击 Start 后约 40.1 秒出首帧。
     - `r18`–`r39`：消除浏览器图片加载与状态轮询的竞态条件（`v25-r18-frame-admission`），并通过 40 项故障注入测试加固单次清理证据链（`r39-cleanup-evidence-candidate`）。
     - `r41`–`r48`：新增启动入口耗时埋点（`r41`）、将自动步进验收时间预算从 20 秒扩展至 60 秒（`r44`），并集成运行时恢复/清理双重校验（`r47`/`r48`）。

---

### 主线三：FX6 6.01 全系统刷入 FX3 7.02 硬件兼容性评估矩阵

- **核心技术报告**：[reports/2026-11-03-fx6-full-system-to-fx3/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-03-fx6-full-system-to-fx3/README.md)

通过对 FX6 6.01（`0x91040086`）与 FX3 7.02（`0x91030080`）官方固件包的完整解包与静态逆向，确立了以下硬件级事实：

1. **100% 字节级一致的 Bootloader 与 SoC 内存映射**：
   - `0800_appli/setting/cxd90057.dtb`（16,875 字节，SHA256 `c5735ad9...`）、`pformat_config.txt`（1,274 字节，SHA256 `21cd5b29...`）以及 `LdrBkupList.txt`（650 字节，SHA256 `ae537183...`，含 65 个 Backup 键）在 FX3 7.02 与 FX6 6.01 之间 **100% 字节级完全相同**。
   - Octal-SPI NOR 物理分区布局（Sector 0 `infomisc.dat` EXBL、Sector 4 `DGU.bin` → `0xFE040800`、Sector 68 `LdrBkup.bin` → `0xFE048800`、Sector 72 `loader_nor.bin` → `0xFE049000`、Sector 512 `MIS.bin+ddrtraining.dat` → `0xFE080000`、Sector 768 `pcie_phy_fw.bin` → `0xFE0A0000`、Sector 4096 `cpapp-b.bin` → `0x00108000`）完全同构。
   - **正常冷启动链路无任何跨机型签名或 Model ID 拦截**：`loader_nor.bin` 仅读取 `p2:/Backup.bin` 中的 `0xfa0080` 描述符表（两机型的 Bank 0 AP 加载地址 `0x400001000` / `0x400002000` / `0x400080000` / `0x401000000` / `0x408000000` 完全一致）。跨机型拦截（`dat2` Model ID `91030080` vs `91040086`、`dat3` 区域码及 ECDSA/AES 签名校验）**仅存在于 `p1` 升级程序用户态（`sauu` / `sdfileinput.elf`）中**。
2. **eMMC UDA 0 扇区索尼私有分区表（`partinf.conf`）与根文件系统架构差异**：
   - `/dev/nflasha1..30` 逻辑分区由写入在 **eMMC UDA 0 扇区** 的 512 字节索尼私有分区表（魔数 `"8246"`，版本 `"2.00"`，共 30 项，由 `edisx.elf` 写入、`emmc.ko` 解析）定义。
   - `p1` 至 `p11` 的起始扇区与容量在两机型上 100% 一致。
   - **根文件系统差异（`p7` 对比 `p3`）**：FX3 通过 `/sbin/initrc/setup_rootfs` 挂载 `/dev/nflasha7`（`p7`，ext2）并 `pivot_root` 切换根文件系统；而 **FX6 没有 `nflasha7` 镜像，也没有 `setup_rootfs`**，FX6 直接以 `p3` 的 RAM Disk（`/dev/ram0`）作为最终根文件系统运行 `/sbin/init2`，并将 `/dev/nflasha15`（`p15`）挂载到 `/usr`。
   - **分区偏移错位与 FX6 新增的 `p20`/`p21`**：从 `p12`（`/cert`）开始，FX6 将 `p12` 从 40 MiB 缩减为 20 MiB，导致后续 `p13`、`p15`（`/usr`，500 MiB）、`p18`（`/lens`，20 MiB）整体前移 20 MiB（`0xA000` 扇区）。此外，FX6 新增了 **`p20`**（100 MiB `/usr/data/lut`，硬编码于 `libInfraSetupFile.so` 与 `appFw.so`）和 **`p21`**（44.5 MiB `/etc/opelog`，硬编码于 `libInfraKikiLogGenerator.so` 与 `kikilog.ko`），而 FX3 原生分区表中 `p20`、`p21` 大小为 `0`（FX3 将 LUT 存放在 `p30`）。
3. **单机出厂校准数据红线与两阶段可逆验证方案**：
   - **严禁无备份覆盖的红线分区**：`p6`（`Jiritsu` 传感器校准）、`p18`（`/lens/lensfile.bin` 镜头校准）、`/setting/psd.bin`、`/setting/defdet.bin` 以及 SPI NOR 中的 `ddrtraining.dat`（偏移 `0x3e210fc`）包含每台相机独有的出厂校准数据。
   - **硬性停机准则**：在未完整导出并校验目标 FX3 的 eMMC Sector 0、`p1/2/3/5/6/7/8/12/13/15/18/23/30` 镜像及 SPI NOR 备份之前，严禁执行任何跨分区刷写或 `edisx.elf` 分区表重写操作。

---

### 主线四：FX3 离线固件恢复适配器（`v0.5`）与 Stage 1–286 固件恢复验证体系

- **核心技术报告与证据链**：
  - [outputs/fx3-recovery-adapter/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-recovery-adapter/README.md) 与 [reports/2026-11-01-fx3-recovery-adapter-v05/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-recovery-adapter-v05/README.md)
  - [reports/2026-11-04-fx3-firmware-recovery/README.md](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-04-fx3-firmware-recovery/README.md) — *Stage 1–286 完整固件恢复验证链*

1. **离线固件恢复适配器（`v0.5`）**：
   - 通过 [fx3_recovery_adapter.py](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-recovery-adapter/bin/fx3_recovery_adapter.py) 提供 `inspect`（检查）、`build`（构建）、`verify`（校验）、`rollback`（无损回滚）四大确定性子命令，支持对 FX3 `0700_part_image_nflasha1.cramfs`（`p1` 升级分区）进行离线定制。
   - 在标准 Linux CramFS 镜像中注入只读 SD 卡诊断脚本（`/etc/init.d/rcS`），并生成逐字节验证的回滚清单。
2. **Stage 1–286 硬件边界与只读导出工具链**：
   - 完整记录了从双层加密结构解析（外层 `FUP1` + 内层 `PFU2`）与 `sauu` 升级状态机逆向，到独立静态链接 AArch64 ELF 只读导出工具（针对 `/dev/nflasha1` 的 `fx3_p1_capture_worker` 与针对 `/dev/nflashaB0`/`B1` 的 `fx3_boot_capture_worker`）并在 `qemu-aarch64` 下完成闭环验证的全过程。

---

## 👤 User / Coordinator

全面把FX3和FX5FX6这些系统相关的研究，在ORCA里面新开一个项目，然后把这些对话全部归类在里面，然后全部实时上传github。

---
