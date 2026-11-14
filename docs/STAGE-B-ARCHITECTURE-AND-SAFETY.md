# Stage-B (`P1..P12+Fan`) & Full-Lab Architecture, 16-Gate Safety Engine & Tier-0..4 Recovery Reference (`EN / 简体中文`)

> **Document Scope / 文档定位**: Authoritative bilingual architectural & safety reference for **`sony-fx3-fx6-lab`** across **Waves 1–8 (`Phases 1–50`, `Rounds 1–11`, `7` Unified Verification Suites / `1,045` Automated Tests)** targeting **Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** & **ILME-FX6 (`Ver. 6.01`, Model ID `0x91040086`, `CHAPLIN`)** on **CXD90057 (`AArch64` AP) + CXD90058 (`ARMv7-R` CP)**.  
> **Companion Runbooks / 配套手册**: [`docs/BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) · [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](./STAGE-A-HARDWARE-RUNBOOK.md) · [`README.md`](../README.md) · [`README.en.md`](../README.en.md) · [`README.zh-CN.md`](../README.zh-CN.md)

> [!CAUTION]
> **HARD-LOCKED HARDWARE FLASH LOCK / 硬件写入硬锁状态: `NO-GO` FOR PERSISTENT FLASHING**
> - `persistent_emmc_writes_authorized = False` · `persistent_write_release = False` · `allow_boot_partition_targeting = False` · `allow_destructive_fastboot = False` · `edisx_repartition_forbidden = True` (`sector0_mutation_bytes = 0`)
> - `p8_cp_mutation_forbidden = True` (`cp_mutation_bytes = 0`) · `wbi_p5_write_and_hibernation_forbidden = True` (`wbi_mutation_bytes = 0`) · `calibration_mutation_bytes = 0` · `kmod_mutation_count = 0` · `nvram_persistent_writes = 0`
> - **All Stage-A and Stage-B overlays reside exclusively in volatile Linux DDR (`tmpfs`, `< 48 MiB` Stage-B overlay + read-only SD loop bind for `appFw.so`), strictly verify `13/13` SHA-256 digests before any mount, execute `os.O_RDONLY` on all donor blobs, and revert instantaneously to 100% stock Sony ILME-FX3 `Ver. 7.02` upon power removal.**

---

# Part I — English Architectural & Safety Reference

## 1. Full-Lab Architecture Map (`Waves 1–8`, `Phases 1–50` & `Rounds 1–11`)

```text
+======================================================================================================+
|                    sony-fx3-fx6-lab : Waves 1..8 / Phases 1..50 / Rounds 1..11                        |
+======================================================================================================+
| [7] Firmware Lab (`fx3-firmware-lab`, 157 tests)     | [1] Recovery Adapter (`fx3-recovery-adapter`,167)|
|  - Keyless UFU/FDAT/UDTRFIRM/SDM2 (`5L+6S` guard)    |  - Tier-0..4 Unbrick Escalation Ladder (`S01..12`)|
|  - `ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4` Differ     |  - `p1` FAT12/16 VFAT Atomic Capsule + `fsync`  |
|  - 62 `.uxc` (29 langs) + 6 CJK `.ltt`/`.ttf` + LDEC |  - Shifted-VMA `v7.02` `p1` 4-Site Autolocator   |
|  - `IMX510` / Dual ISO / XAVC & `.cube` / `RTMD`     |  - macOS 26 `IOUSBHost` + `O_RDONLY` eMMC Forensic|
|  - `WBI2`/`hibdrv` EL1 Guard + `global.xdb` 128-page |  - Freestanding AArch64 `fx3_p1/boot_reader`     |
+------------------------------------------------------+-----------------------------------------------+
| [3] Stage-A & Stage-B Closure (`fx6-on-fx3-closure`, 279 tests)                                      |
|  - Stage-A (`P1..P9+Fan`, `U1..U5` Closed) -> Stage-B (`P1..P12+Fan`, 13/13 SHA-256, 8 ELF/18 sites) |
|  - `P10` 24B FX3 Button Remap (`e2bc2619...`) + `P11` UIPC-CP Shim (`0x92d2091c`/`0x91db059b`+XLR-H1)|
|  - `P12` `libWlanResource.so` `0x70d4` `WF-12` Guard (`47fec188...`) + `BK4\0` Airplane/CJK Shadow   |
|  - `stage_b_ram_overlay_packager` (`070701` CPIO + 9/9 `/bin/sh` `init2`) & `S01..S10` Lifecycle     |
+------------------------------------------------------+-----------------------------------------------+
| [2] Safety Engine (`fx3-safety`, 200 tests)          | [6] Co-Emulation VM (`fx3-vm`, 127 tests)       |
|  - 16-Gate Master Preflight (`G01..G16`)             |  - Stage 1: Cold-Boot + `virtual-rom-v1` BT H4   |
|  - 6-Stage `H0` Rehearsal + `serial_fault_detector_v2` |  - Stage 2: Dual-ISA `AArch64`<->`IVSHMEM`<->`CP`|
|  - `RP2040-Zero -DOPEN_DRAIN` `48000` UART + `VMC-BNCM1`|  - Stage 3: `Soft-GPE0` (`0x41E001000`) + `ramfb`|
|  - `CrSDK` PTP2, MI-Shoe `XLR-H1`, `SPACC` `cnflasha`|  - Stage 4: Pure-Py FDT `0xd00dfeed` + `MHLX`    |
|  - C2PA `RQ_LIC.DAT`/Calib Immutability + Fan/USB-PD  |  - Stage 5: `IMX510`/XAVC/`RTMD 0xE304`/CFexpress|
+------------------------------------------------------+-----------------------------------------------+
| [4] Interactive Web Console (`fx3-vm-trial`, 81)     | [5] Native Presenter (`fx6-native-presenter`,34)|
|  - Live QEMU `8768` (`1024x540` `GPE0`), `60/60` 0SEGV|  - Real FX3 `7.02` `4.9.337-scel+` Kernel Boot   |
|  - LRU 128-Page Pool + `简体中文/EN/日本語` Live Switch|  - `nop_count = 0`, `13/13` Verify-Before-Mount  |
|  - `P10` Deck + Cine EI/`P4` ND Lock + `.cube` Uploader|  - Rounds 1..7 (`r1a..r7c`) + Rounds 8..11 (`r8..r11`)|
|  - 4-Ch `XLR-H1` VU + `CAMSET` + 128p Search + Diffs |  - `MYingHeiC` GB18030 + `LDEC103`, `476` colors |
+======================================================================================================+
```

### Wave 1–8 Milestone Progression (`Phases 1–50` & `Rounds 1–11`)

| Wave / Scope | Phases / Rounds | Key Engineering Deliverables | Verification Target |
| :--- | :--- | :--- | :--- |
| **Wave 1–2 (Core VM & Stage-A Foundation)** | `Phases 1–16`, `Rounds 1–8` | FX3 minimal VM (`AP70–AP105`), FX6 `nop_count=0` cold-boot (`r1a..r7c`), Round 8 Stage-A hybrid boot (`r8a..r8b`), `P1..P9+Fan` compatibility matrix, `U1..U5` Blueprint closure, `p1` Bridge, Stage-A Atomic Orchestrator & `WBI` redline, `.ko`/ABI closure, Tier-0 worker, `H0->H1->H2` drill | `make dry-run`, `make readiness-packet`, `make lifecycle-drill` |
| **Wave 3 (Stage-B Peripherals, `P10`/`P11`/`P12`, Icons & Multilingual Web UI)** | `Phases 17–26`, `Rounds 9–10` | `P10` FX3 physical keymap (`e2bc2619...`), `P11` AP-side `0x92d2091c` `/dev/rtc0->udate` + `0x91db059b` Smart-Handle ACK preserving `XLR-H1` & 5-axis IBIS lock, `P12` `libWlanResource.so` `0x70d4` `WF-12` guard (`47fec188...`) + `BK4\0` Airplane shadow, Phase 19 `image_00_169.uxc` & `60/60` `0 SEGV`, Phase 23 LRU 128-page ZH/EN & FX3 deck, Phase 24 Dual-ISA `IVSHMEM` bridge, Phase 25 `v7.02` `p1` autolocator & anti-brick guards, Rounds 9–10 real-kernel presenters (`r9a..r10d`) | `make verify-stage-b-p10`, `make verify-uipc-cp-shim`, `make verify-wireless-guard` |
| **Wave 4–5 (Clean-Room Lab, Rehearsal, Co-Emulation & S-Chinese Round 11)** | `Phases 27–37`, `Round 11` | 62 `.uxc` + 6 CJK font verifier, 6-stage `H0` rehearsal, `Soft-GPE0` + `virtual-rom-v1` BT, live Cine EI/`P4` ND/`EN/ZH/JA` Web UI (`8768`), `IMX510`/XAVC matrix, `serial_fault_detector_v2`, 3-stage co-emulation suite, Phase 35 `S01..S10` Stage-B lifecycle drill, Phase 36 BYOF `57+57` parity, Phase 37 `.cube`/`RTMD` verifier, Round 11 `13/13` SHA-256 + Simplified Chinese `MYingHeiC` (`476` colors) | `make stage-b-lifecycle-drill`, `make verify-coemulation`, `make verify-byof` |
| **Wave 6–8 (Hardware Guardrails, FDT/IMX510 Pipeline, Stage-B Overlay & 16-Gate C2PA/exFAT Sync)** | `Phases 38–50` | `CrSDK` PTP2 + MI-Shoe + `VMC-BNCM1` LTC + `SPACC` guards, Phase 39 `stage_b_readiness_packet_v2`, Phase 40 `.cube` uploader + 4-Ch `XLR-H1` VU + `CAMSET` presets, Phase 41 Pure-Py FDT `0xd00dfeed` + `MHLX` + `MmioWindowBus`, Phase 42 `O_RDONLY` eMMC forensics, Phase 43 `WBI2`/`hibdrv` & ELF64 ABI diff, Phase 44 Thermal PWM + `NP-FZ100`/`USB-PD` guard, Phase 45 `IMX510`/XAVC/CFexpress pipeline, Phase 46 `global.xdb` 128p audit, Phase 47 Tier-0..4 12-scenario ladder & `p1` VFAT capsules, Phase 48 Stage-B SVR4 `070701` packager & 9/9 `init2` sandbox, Phase 49 128p bilingual search & `EN/ZH/JA` diff + `HardenedThreadingHTTPServer`, Phase 50 Wave-4 C2PA/`exFAT`/16-Gate Master Preflight (`G01..G16`) | `make test` (`1,045` tests / `7` suites), `make verify-firmware-lab` |

---

## 2. Stage-B (`P1..P12 + Fan`) Compatibility Adaptation Matrix (`13/13` Items)

Stage-B builds cleanly atop Stage-A (`P1..P9+Fan`) without altering Stage-A's deterministic CPIO contracts (`include_p10_keymap=False`), expanding coverage to **13 lock-table items** (`8` ELF64/module specs across `18` non-overlapping sites + `opelog.vfat` + `P5/P6`, `P7`, `P11` runtime contracts + `BK4\0` shadow) with **100% bit-exact SHA-256 rollback** and `0` persistent writes.

| ID | Target Binary / Contract | Site(s) / VMA / Offset | Adaptation & Behavioral Contract | Byte Delta / Scope | FX3 Hardware Safety Predicate |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`P1`** | `libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so` | `0x25E9C`, `0x4DFCB`, `0x86FE`, `0x25896CE` (`PF_R`) | Remaps User 3D LUT path `"/dev/nflasha20"` -> `"/dev/nflasha30"` (`'2'` -> `'3'`), isolating FX6 `p20` onto FX3 `48.00 MiB` `p30` (`+32.04 MiB` free headroom for 16x `33^3` `.cube` LUTs). | `4 B` across 4 `.so` files | Zero Sector-0 repartitioning (`U1`). |
| **`P2`** | `images/opelog.vfat` (`VFAT` loopback) | `/dev/loop7` -> `/etc/opelog` | Pure-Python deterministic `FAT16` (`8 / 16 / 44.5 MiB`) with dual FATs & `/OPE/{00,01}` directories; eliminates `nflasha21` mount failures cleanly. | `8 MiB` in `tmpfs` | Never touches physical `nflasha*`. |
| **`P3`** | `libInfraAppRemoteBoard.so` | `0x157C` (`execRcvMsg`), `0x1700` (`MainThread`) (`PF_R\|PF_X`) | Replaces blocking `BK4 0x00fa01a3/01a4` + `osal_wai_sem_tmo(0x810708dc, -1)` wait with `mov w0, #0; ret`. | `16 B` (`2` sites) | Prevents boot hang when FX6 remote board is absent. |
| **`P4`** | `appFw.so` | `0x2111358` (`cbnz->nop`), `0x21113F0` (`cbz->b 0x211145c`) | Locks Electronic Variable ND Filter state to **`Clear` (`mode=4`, `(1,1)`)** across all `576/576` Unicorn enum combinations. | `8 B` (`2` sites) | Prevents FX3 camera without e-ND hardware from entering illegal ND states. |
| **`P5`** | `0x92840747` UIPC Queue | Opcode `0x032d` -> `0x132d` | Deterministic completion synthesis (`P5`/`P6` JSON rule contract) preserving audio/HDMI `0x00580000` init flow. | Contract (`1,811 B` JSON) | Zero `cpapp-b.bin` mutation (`cp_mutation_bytes=0`). |
| **`P6`** | `0x92840747` UIPC Queue | `0x0400->0x1400`, `0x0402->0x1402`, `0x0404->0x1404`, `0x0152->0x1152` | Completion synthesis for FX6-specific Timecode/Peaking/CP queries (`send_and_wait_cmp_i` @ `0x20ef604..0x20ef7ec`). | Contract (shared with `P5`) | Keeps stock FX3 `cpapp-b.bin` untouched. |
| **`P7`** | Kernel `pcidma_transfer_async` | FX3 `0xffffff80083220c8` / FX6 `0xffffff8008322f70` | Address-agnostic Sync100 Backup DMA trampoline (`40 B` `dst=0x903e0811`, `op=0x30`, `fallback_zero=api+0x160`, `fallback_nonzero=api+0x10`). | Contract (`255 B` JSON) | Stock FX3 kernel remains unmodified. |
| **`P8`** | `appFw.so` | `0x2159C50` (`PF_R\|PF_X`) | Replaces blocking async log wait with `mov w0, #0; ret` (`2`-instruction non-blocking return). | `8 B` (`1` site) | Prevents stall on absent FX6 log sink. |
| **`P9`** | FX3 `upm.ko` (`ET_REL`) | `.text+0x136B8` (file `0x13720`, `SHF_ALLOC\|SHF_EXECINSTR`) | Replaces null sensor callback `blr x2` with `mov w0, #0` inside volatile RAM-mounted FX3 `upm.ko` (`slot #24`). | `4 B` (`1` site) | Zero FX6 `.ko` modules loaded (`fx6_kmod_loaded_count=0`). |
| **`Fan`** | `libfan.so` | `0x1DEC` (`_Z19fan_i_bkup_is_validv`) | Patches to `mov w0, #1; ret` so FX3 compact fan PWM thermal curve checks succeed cleanly under `AUTO1`/`AUTO2`/`MINIMUM`/`OFF_IN_REC`. | `8 B` (`1` site) | Enforces `G14` `>=62°C` override, `82°C` warning, `90°C` teardown. |
| **`P10`** *(Stage-B)* | `appFw.so` | `.rodata` `0x2245A84..0x2246134` (`6` table slots, `PF_R`) | Remaps FX3 physical buttons without page aliasing (`Fn->HOME 0x184`, `C1->KURU_PON 0x029`, `C2->MENU_CANCEL 0x192`, `C3->DISP_SEL 0x199`, `PLAY->THUMBNAIL 0x183`, `DELETE->USER 0x185`); combined `P1+P4+P8+P10` `appFw.so` SHA-256 = `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`. | `24 B` (`6` sites; `41 B` total on `appFw.so`) | Verified across `21/21` keys (`15` native + `6` remapped) in Unicorn & Round 9–11 QEMU. |
| **`P11`** *(Stage-B)* | AP-side `UipcCpShimRuntime` | Queues `0x92d2091c` & `0x91db059b` + `developing_mode_FHD` | Translates `0x92d2091c` (`/dev/rtc0 -> udate`) unblocking `std::promise<bool>`, emits detached-grip ACK (`0x81000001`/`0x88000002`, event `551`) on `0x91db059b`, preserves `XLR-H1` (`libInfraHotshoe.so` `0x5d90`), bridges `developing_mode_FHD` + `0x0165`/`0x0166` `33^3` LUT DMA + Cine EI `800/12800` + 5-axis IBIS center-lock. | Contract (`354 B` JSON) | Zero `cpapp-b.bin` writes; FX3 IBIS actuators stay energized & center-locked. |
| **`P12`** *(Stage-B)* | `libWlanResource.so` + `/tmp/bk4_shadow` (`BK4\0`) | `0x70D4` (`_Z16handleFatalErrorv`) + `BK4` keys | Patches `while (1) usleep(1_000_000)` hang at `0x70d4` to `mov w0, #0; ret` (SHA-256 `eb7785e0...` -> `47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995`) + Airplane-Mode RAM shadow (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`) + selectable `BK_LANG` (`0x02cf019c`: `en=0x00`, `ja=0x01`, `zh_tw=0x18`, `zh_cn=0x19`). | `7 B` (`1` site) + `20,824 B` `BK4\0` | Immune to Sony Notice `00342260` (`WF-12` Wi-Fi/BT bootloop) with `0` NVRAM writes. |

---

## 3. 16-Gate Master Safety Preflight Engine (`G01..G16`)

Implemented in [`outputs/fx3-safety/fx3_safety/preflight.py`](../outputs/fx3-safety/fx3_safety/preflight.py) (`G01..G12`) and [`outputs/fx3-safety/fx3_safety/master_16gate_preflight.py`](../outputs/fx3-safety/fx3_safety/master_16gate_preflight.py) (`G01..G16`, schema `fx3-master-16gate-preflight-v1`). All gates fail closed and keep `persistent_emmc_writes_authorized = False` hard-locked.

| Gate | Canonical ID & Domain | Core Verification Contract | Fail-Closed Trigger Conditions |
| :---: | :--- | :--- | :--- |
| **`G01`** | `G01_official_reference_integrity` | Verifies official FX3 `7.02` (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) & `2.04`/`2.05` `p1` SHA-256 digests (`O_RDONLY`). | Any missing/mismatched baseline digest. |
| **`G02`** | `G02_authenticated_usb_service_session` | Verifies closed-loop MSC (`054C:0DA1`) -> 7-round auth -> Service Mode (`054C:0336`) -> MSC return (`native_return=0`). | Unauthenticated or non-clean-return service session. |
| **`G03`** | `G03_adjust_control_and_jiritsu_wire_contract` | Verifies `AdjustControlFunc` (`0x0040`, category `0x1001`) read-only wire envelope & `/tmp/jbusy` precondition. | Destructive `FORMAT`/`FIRMUP`/`DEBUG`/`SET_FILE` opcodes (`0x4003`/`0x4005`/`0x4006`/`0x4007`). |
| **`G04`** | `G04_offline_p1_recovery_and_rollback_engine` | Audits `fx3_recovery` `FAT12/16`, `SquashFS` `Z_SYNC_FLUSH` same-size packing & byte-exact rollback. | FAT cycle/cross-link or rollback SHA mismatch. |
| **`G05`** | `G05_static_aarch64_capture_workers` | Verifies zero-libc freestanding `fx3_p1_reader.c` / `fx3_boot_reader.c` + custom `elflink.py` workers in Unicorn. | Dynamic imports or write flags in worker trace. |
| **`G06`** | `G06_bootloader_and_sector0_contract` | Audits Octal-SPI NOR map & eMMC Sector 0 (`'8246' '2.00'` 30-entry table, `LBA >= 0x80`, zero overlap). | Sector-0 magic/overlap error or FX6 `p18@0x312000` shift hazard. |
| **`G07`** | `G07_backup_bin_bk4_and_fa0080_contract` | Verifies `loader_nor.bin` `BK4\0` (`0xfe04c7a8 -> 0xfe04d584`), `0xfa0080` 64-slot Bank 0/1 & `0x02cf0214/0218`. | Any Bank 0/1 DDR overlap or invalid `BK4\0` checksum. |
| **`G08`** | `G08_qemu_stage0_preflash_sandbox` | Requires passing QEMU Stage-0 sandboxes (`FX3` + `FX6` hybrid) and `detect_serial_faults.py` / `v2` watchdog audit. | Kernel `Oops`, `APPFW_SEGV`, or watchdog timeout. |
| **`G09`** | `G09_failsafe_4layer_overlay_and_watchdog` | Verifies 4-Layer Fail-Safe: (1) `mount --bind` in RAM, (2) `rm -f /tmp/mod_arm_once` Clear-Before-Exec, (3) BusyBox watchdog, (4) `/setting/updater/mode5` fallback. | Missing/misordered Clear-Before-Exec or direct `/dev/*nflasha*` writes. |
| **`G10`** | `G10_same_body_tier0_full_backup_checkpoint` | Requires two-pass idempotent `O_RDONLY | O_NOFOLLOW` dumps of all **11 mandatory Tier-0 partitions/calibrations** + `p8_tomco.txt` + `p5_wbi_header.bin`. | Missing item, synthetic/placeholder body tag, or `pass1_sha256 != pass2_sha256`. |
| **`G11`** | `G11_independent_hardware_recovery_readiness` | Validates `verify_failsafe_hook_script` ordering & `p1`-first / one-shot overlay recovery entry (`loader_nor.bin` lacks auto `p3 -> p1` failover). | `init2` hook mounts before clearing `/tmp/mod_arm_once`. |
| **`G12`** | `G12_persistent_flash_write_authorization` | Aggregates `U1..U5` closure, `.ko`/ABI closure, `P1..P12+Fan`, `P10`/`P11`/`P12`, runtime anti-brick (`ld.so.preload`, `dd`, `nflasha10`, `PRODUCT_MODEL`) & dry-run status. | Any redline false or attempt to flip `persistent_write_release` to `True`. |
| **`G13`** | `G13_multi_port_and_mishoe_fixture_isolation` | Enforces `RP2040-Zero -DOPEN_DRAIN` (`1.8V/3.15V`), blocks `VMC-BNCM1` LTC + `uart_boot` pin-sharing (`Pins 7/8/9`), verifies `P11` `0x91db059b` + `XLR-H1` coexistence & `CrSDK` PTP2 (`0x9201..0x9209`) + `SPACC` isolation. | Standard Pico `GP29` (`VSYS/3`), push-pull `3.3V`, Nikon `0x920a..0x920f`, or simultaneous LTC+UART cable. |
| **`G14`** | `G14_thermal_pwm_and_npfz100_usbpd_envelope` | Enforces `CXD90057 SoC < 62.0°C` start headroom, FX3 `libfan.so @ 0x1dec` 4-mode PWM (`82°C` warn, `90°C` graceful teardown), `NP-FZ100 >= 80% / >= 7800 mV` InfoLITHIUM normalization, and `USB-PD 9V/3A` droop `<= 450 mV`. | Raw `BP-U 11500 mV` comparator, `FAN_CONTROL_ALWAYS_OFF`, SoC `>= 90°C`, or VBUS brownout. |
| **`G15`** | `G15_c2pa_keystore_and_factory_calibration_immutability` | Locks `cnflasha*`, `RPMB`, TrustZone/OP-TEE, Sony **C2PA** (`RQ_LIC.DAT`, `sigcert.p12/.pfx`, `p12:/cert`, `/dev/tee*`), and factory calibration (`psd.bin`, `defdet.bin`, `Backup.bin`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin`, `SPI NOR ddrtraining.dat`); validates `exFAT` hygiene (`VolumeDirty=0`, zero `.RSV`). | Any write/mount targeting C2PA/calibration/RPMB, `calibration_mutation_bytes != 0`, or dirty `exFAT` / unfinalized `.RSV`. |
| **`G16`** | `G16_stage_b_p12_wf12_and_wbi2_cold_boot_lock` | Audits FX6 `libWlanResource.so` `P12` `0x70d4` (`00008052c0035fd6`, `patched_rc=0`), `BK4\0` Airplane shadow (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`), `wbi_mutation_bytes == 0`, `cp_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`. | Tampered `P12` patch, missing Airplane-Mode shadow keys, or any `WBI2`/`CP`/NVRAM mutation. |

---

## 4. `Tier-0..Tier-4` Recovery & Unbrick Escalation Ladder

Implemented in [`outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py`](../outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py) (`12` deterministic scenarios `S01..S12`, `p1` `FAT12`/`FAT16` atomic rollback capsule verifier, and CLI `verify-unbrick-ladder`):

| Tier | Recovery Domain & Mechanism | Physical Trigger / Fault Profile | Executed Action & Mandatory Guards | Escalation Exit |
| :---: | :--- | :--- | :--- | :--- |
| **`TIER_0`** | **Volatile Power-Cycle / One-Shot Latch** | Clean Stage-A/B exit, `0x100D` early `appFw` abort, `WF-12` (`00342260`) unpatched hang, or thermal/VBUS brownout | Cut power / remove `NP-FZ100` `>= 60s`; `/tmp/mod_arm_once` was already unlinked before mount (`Clear-Before-Exec`), or `p1` VFAT `boot_attempts >= 1` trips one-shot skip -> instant stock `FX3 v7.02` boot (`0` eMMC writes). | Escalate to `TIER_1` if host MSC transport stalls. |
| **`TIER_1`** | **macOS 26 `IOUSBHost` MSC Quiescence & `U5` 2-Step Exit** | macOS 26 `IOUSBHost` `0xe00002be` (`kIOReturnExclusiveAccess`) during `H0`, or camera sticky in `p1` updater loop | Enforce `>= 350 ms` MSC quiescence + bounded exponential backoff `[50,100,200,400,800 ms]`, `0` retries on USB STALL (`0xe000404f`), reject Senser v2 RSA (`fail-closed`), or run mandatory 2-step `U5` exit (`rm -f /setting/updater/mode* && sync && ud_send_lsi.elf 0`). | Escalate to `TIER_2` if `p1` container validation fails. |
| **`TIER_2`** | **`p1` VFAT Capsule & Shifted-VMA `v7.02` 4-Site Autolocator** | Shifted-VMA FX3 `v7.02` `p1` (`isVersionOK`, `VerifySignature`, `chkFirmInfo`), `ld.so.preload` hazard, or cross-body `WBI2` rejection | Enforce 4-site AArch64 `ADRP/BL` autolocation (`p1_symbol_autolocator.py`), reject hardcoded `v2.00` offsets, verify `FAT1==FAT2` + `8.3`/LFN checksums + 6-step `fsync` (`O_CREAT\|O_EXCL\|O_NOFOLLOW` + two-pass `O_RDONLY` SHA-256), and block `ld.so.preload`/cross-body `WBI2`. | Escalate to `TIER_3` if `p3` & `p1` both fail to boot via USB MSC. |
| **`TIER_3`** | **Screwless Multi-Port `48000`-Baud BootROM `uart_boot` + Read-Only Fastboot v0.5 (`18D1:4EE0`)** | Hard AP/Linux boot failure with intact `48 KiB` Octal-SPI BootROM (`0xFFFF0000..0xFFFFBFFF`) | **`RP2040-Zero` (`-DOPEN_DRAIN`, `GP27/28/29` <-> Multi `Pin 9/7/8`, `Pin 2 GND`) ONLY** (unplug `VMC-BNCM1`, ban Pico `GP29` `VSYS/3`), stage to `0x92028000` (Mira SRAM) or `0xFE020000` (eSRAM), firewall `>= 0xFFFFC000` WDT trap, allow read-only `oem dumpbrom`/`oem partition dump` ONLY (`flash:*`/`erase:*`/`oem format` blocked). | Escalate to `TIER_4` if BootROM/SPI NOR or eMMC bus is unresponsive. |
| **`TIER_4`** | **Offline `O_RDONLY` eMMC 5.1 ISP Forensic Verification** | Stuck `0x00`/`0xFF` bus dumps, `EXT_CSD[179]` (`PART_CONFIG` `0xB3`) boot-partition faults, or `CMD42` lock risks | Open strictly `O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`, run bus/entropy check (`ALL_ZERO`, `ALL_FF`, `>=16` `0xFF` pull-up pages, `cnflasha` AES-XTS `<7.75` entropy), validate `Sector 0` / `BK4\0` (`0x91030080`) / `WBI2` / `cpapp-b.bin`, reject `BOOT_PARTITION_ENABLE == 0` & `CMD42` forced-erase unconditionally. | Bench hardware repair / board replacement. |

---

## 5. Stage-B RAM-Overlay Packaging, `S01..S10` Lifecycle & Dual-ISA Co-Emulation

1. **Stage-B Volatile RAM-Overlay Packager v2 (`stage_b_ram_overlay_packager.py`, Phase 48)**:
   - Deterministically packages an `8`-entry SVR4 `cpio newc` (`070701`, `mtime=0`, `uid=0`, `gid=0`, 4-byte aligned, `TRAILER!!!`, `~39.5 KiB`) embedding `stage_b_overlay_manifest.json` (`13/13` SHA-256 lock table), `p11_uipc_cp_shim.json`, `tmp/bk4_shadow` (`BK4\0` Airplane-Mode + `BK_LANG` `0x02cf019c` for `en`/`japanese`/`tchinese`/`schinese`), and POSIX `/bin/sh` `stage_b_init2_guard.sh`.
   - **`tmpfs` DDR Budget**: Only `~9.21 MiB` (`LOCAL_DONOR`) / `~8.11 MiB` (`CLEAN_ROOM`) inside `< 48.00 MiB` `tmpfs` cap (`38.79 MiB` headroom inside FX3 `2048 MiB` DDR), while `50.52 MiB` `appFw.so` (`e2bc2619...`) binds via `ro_sd_loop_bind`.
   - **9/9 POSIX `/bin/sh` Sandbox Drills**: Verifies `/tmp/mod_arm_once` unlink + `boot_attempts >= 1` latch before any mount, absence of `/etc/ld.so.preload`, `PRODUCT_MODEL == 0x91030080`, `BK4\0` magic, thermal/battery preflight, and `13/13` SHA-256 Verify-Before-Mount before the `8` read-only bind mounts.
2. **Stage-B `H0 -> H1 -> H2` 10-Scenario Lifecycle & Readiness Dossier (`Phases 35 & 39`)**:
   - `stage_b_lifecycle_verifier.py` (`make stage-b-lifecycle-drill`) validates `S01..S10` through `serial_fault_detector_v2` (`TIMER-IP` `220s`/`90s`), `12`-step forward & reverse LIFO teardown, and `13/13` (`11+2`) `H0 == H2` cryptographic zero-drift receipts.
   - `stage_b_master_readiness_packet.py` aggregates all verdicts into self-authenticating `stage_b_readiness_packet_v2` JSON (`verify_stage_b_master_readiness_packet` checks canonical `packet_sha256` plus every safety redline).
3. **5-Stage Full-Board Virtual Camera Co-Emulation (`outputs/fx3-vm/fx3_vm_coemulation_suite.py`, `127` tests)**:
   - **Stage 1**: AP cold-boot + `virtual-rom-v1` Bluetooth HCI H4 UART (`/dev/ttyAMA3`, `BD_ADDR 58:36:57:00:29:01`, `WF-12` `0x0BB9` & `00342260` NACK + `BK4\0` gating).
   - **Stage 2**: Dual-ISA `AArch64` AP (`CXD90057`) <-> PCI `ivshmem-doorbell` (`0x1000_0000`/`0x1010_0000`) <-> `ARM32 Thumb-2` unmodified `cpapp-b.bin` (`@ 0x00108000`, `cp_mutation_bytes = 0`), running `P11` AP isolation (`0x92d2091c`/`0x91db059b` zero leak to CP) and `0x92840747` ProCam/LUT/IBIS round-trips.
   - **Stage 3**: `Soft-GPE0` (`0x41E001000`) + `ramfb` (`0x41E100000`, `HOSDAP02`), rendering `image_00_169.uxc` `1,610` sprites + `9-patch` via pure-CPU Sony LDEC LZ77.
   - **Stage 4**: Pure-Python `CXD90057` FDT v17 (`0xd00dfeed`, `4,614 B`, `29` nodes) + `MmioWindowBus` (`0xf0000000..0xf8ffffff`) + 8-channel `mhlx`/`ipcu` rings + `shm_Loader` cold/warm handshakes (`0x4101->0xc101`, `0x4102->0xc102`) + `SPACC` userland trap.
   - **Stage 5**: Frame-accurate `IMX510` VSYNC (`24000/1001..240000/1001`), `libmpr` XAVC-I (`MXF`) / XAVC S-I (`MP4`) / XAVC HS, per-frame `SMPTE RDD 18` `RTMD` (`0xE304` + `0x8108` + `0xE400..0xE450`), and dual CFexpress Type A / SDXC slot simulation (`SIMULTANEOUS`, `RELAY`, `SORT_PROXY`, `SPEED_CLASS_REJECT`).

---

## 6. Wave 1–4 Global Public Research Alignment Summary

| Wave | Global Domain & Public Sources | Verified Lab Contract & Guard |
| :---: | :--- | :--- |
| **Wave 1** | Sony BIONZ XR `UFU`/`FDAT`/`UDTRFIRM`/`SDM2`, `pmca-re-reloaded`, `a7c2-qemu`/`zve10-qemu`, `48000`-baud `uart_boot` (`ILCE-7M4-RE`) | Keyless `fx3-firmware-lab`, macOS 26 `0xe00002be` & Senser v2 guards, `RP2040-Zero -DOPEN_DRAIN` verifier (`outputs/fx3-recovery-adapter`, `outputs/fx3-safety`). |
| **Wave 2** | `CrSDK v1.06–v2.02` & `libgphoto2` PTP2 (`0x9201..0x922F`, Nikon `0x920a..0x920f` collision), `24-pin MI-Shoe` (`XLR-H1`), `VMC-BNCM1` LTC (`Pin 3/2`, `680 kOhm`), `RTMD` (`AdrianEddy/telemetry-parser` `RDD 18`, `0x8108` `1/60°` vs CrSDK `1/1000°`), `CXD90057 SPACC @ 0xF7FC0000` | Executable Phase 38 guards (`G13`), `cube_lut_and_rtmd_verifier.py` (`17^3->33^3` + `RTMD 0xE304`), `imx510_xavc_cfexpress_pipeline_emulator.py`. |
| **Wave 3** | `BL1 -> BL2 -> BL31 -> OP-TEE BL32`, `WBI2`/`hibdrv` (`wbi2`/`WBI3` vs zero-mutation), `JEDEC JESD84-B51` `EXT_CSD[179]` (`PART_CONFIG` `0xB3`), `CMD42` voltage-glitching (*Hugget et al., FSI:DI 2026*), `OpenIPC/qemu-bench`, `qemu-eos` | `wbi_hibdrv_and_elf_abi_differ.py` (`BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH`), `emmc_dump_forensic_verifier.py` (`EXT_CSD[179]` & `CMD42` bans), `unbrick_ladder_and_capsule_verifier.py`. |
| **Wave 4** | **Sony FX3 v7.00+ C2PA Content Authenticity** (`RQ_LIC.DAT`, `Create Key Pair` TrustZone/RPMB/`p12:/cert`, `sigcert.p12`, `[Delete Signature Func.]` hazard), **Microsoft `exFAT` Spec** (`VolumeFlags` offset `106`/`0x6A` `VolumeDirty`, torn `.RSV` vs `chkdsk /f`), **Heterogeneous Co-Emulation** (`QEMU ivshmem-flat`, `Avatar2`, `Renode`, `Icicle`) | `master_16gate_preflight.py` **`G15` C2PA/Calibration/exFAT Gate** + **`G16` `P12`/WF-12/`WBI2` Lock** + validation of Lab Hybrid VM (`QEMU AArch64` + `IVSHMEM` + `ARMv7-R cpapp-b.bin`). |

---
---

# 第二部分 — 简体中文架构与安全参考

> [!CAUTION]
> **硬件写入硬锁红线 (`persistent_emmc_writes_authorized = False` / `NO-GO`)**
> - 本实验室严格锁定 `persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）、`p8_cp_mutation_forbidden = True`（`cp_mutation_bytes = 0`）、`wbi_p5_write_and_hibernation_forbidden = True`（`wbi_mutation_bytes = 0`）与 `calibration_mutation_bytes = 0`。
> - 所有 Stage-A / Stage-B 适配仅运行在易失性 Linux DDR（`tmpfs`，Stage-B 覆盖包 `< 48 MiB` + `appFw.so` 只读循环挂载）之上，在首次挂载前强制完成 `13/13` SHA-256 校验；断开电源即可瞬间 100% 恢复原厂 Sony ILME-FX3 `Ver. 7.02`。

## 一、全实验室七套件架构总览（`Wave 1..8` · `Phases 1..50` · `Rounds 1..11`）

| 受控工程包 / 模块 | 覆盖阶段 | 自动化测试数 (`make test`) | 核心工程能力与边界 |
| :--- | :--- | :---: | :--- |
| **[`outputs/fx3-recovery-adapter`](../outputs/fx3-recovery-adapter/README.md)** | `Phases 11, 25, 42, 47` | **167** *(skipped=1)* | `Tier-0..Tier-4` 救砖阶梯（`S01..S12`）、`p1` `FAT12`/`FAT16` VFAT 原子回滚胶囊与 6 步 `fsync`、偏移 VMA `v7.02` `p1` 4 锚点自动定位、macOS 26 `IOUSBHost` + Senser v1/v2 防护、`O_RDONLY` eMMC ISP 取证审计（`EXT_CSD[179]`/`CMD42` 拦截）与无 libc AArch64 采集器。 |
| **[`outputs/fx3-safety`](../outputs/fx3-safety/)** | `Phases 1–16, 25, 28, 30, 32, 38, 44, 50` | **200** | **`G01..G16` 16 门禁主安全预检引擎**、6 阶段 `H0` 只读预演、`serial_fault_detector_v2`（`220s`/`90s` 看门狗）、`RP2040-Zero -DOPEN_DRAIN` `48000` 波特率 `uart_boot` 与 `VMC-BNCM1` LTC 防火墙、`CrSDK` PTP2、24 针 MI 热靴 `XLR-H1`、`SPACC` XTS、C2PA `RQ_LIC.DAT`/校准分区锁定、FX3 风扇 PWM 与 `NP-FZ100`/`USB-PD` 防火墙。 |
| **[`outputs/fx6-on-fx3-closure`](../outputs/fx6-on-fx3-closure/README.md)** | `Phases 1–22, 26, 35, 39, 48` | **279** | Stage-A（`P1..P9+Fan`）与 Stage-B（`P1..P12+Fan` **`13/13` 锁表** / `8` 模块 `18` 锚点）：`P10` 24B 物理按键表（`appFw.so` `e2bc2619...`）、`P11` AP 侧 UIPC-CP 垫片（`0x92d2091c` `/dev/rtc0` + `0x91db059b` 保留 `XLR-H1` + 5 轴 IBIS 居中锁止）、`P12` `libWlanResource.so` `0x70d4` `WF-12` 断环补丁（`47fec188...`）+ `BK4\0` 飞行/中文影子、`U1..U5` 全清零、`S01..S10` 生命周期、`stage_b_ram_overlay_packager`（`070701` + `9/9` `init2`）与 `stage_b_readiness_packet_v2`。 |
| **[`outputs/fx3-vm-trial`](../outputs/fx3-vm-trial/README.md)** | `Phases 19, 23, 30, 40, 49` | **81** | 端口 `8768` 实时 QEMU `1024×540` `GPE0` Web 控制台（`FX6菜单.command`）：原生 `image_00_169.uxc` 渲染与 `60/60` 零崩溃修复、LRU 128 页零卡死池、`简体中文 / EN / 日本語` 实时切换、`P10` 机身按键台、Cine EI / 快门角 / `P4` ND-Clear 锁、`.cube` `17³/33³` 3D LUT 导入器、4 通道 `XLR-H1` VU 表、`RTMD 0xE304`、`CAMSET` 预设、11 分类 128 页双语搜索直跳、机内三语 `GPE0` 像素差验真与 `HardenedThreadingHTTPServer`。 |
| **[`outputs/fx6-native-presenter-closure`](../outputs/fx6-native-presenter-closure/README.md)** | `Rounds 1–11` | **34** | `FX6_NATIVE_FAITHFUL=1`（`nop_count=0`、`subst_*=0`）原厂冷启动（`r1a..r7c`）+ FX3 7.02 原厂内核 `4.9.337-scel+` 混合态真机启动（`r8a..r11d`）：`13/13` Verify-Before-Mount SHA-256、`MYingHeiC-GB18030-SJ_wIcon.ltt` 原生简体中文（`bank 19/23`）+ `LDEC103` 物理池精灵贴图，峰值 **`476` 色 / `24,891` 字形块**（`r11d`）。 |
| **[`outputs/fx3-vm`](../outputs/fx3-vm/README.md)** | `Phases 24, 29, 33, 41, 45` | **127** | 5 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py`）：Stage 1 冷启动 + `virtual-rom-v1` `/dev/ttyAMA3` 蓝牙 HCI；Stage 2 双架构 `AArch64` AP ↔ `IVSHMEM` ↔ 未修改 `ARM32 Thumb-2` `cpapp-b.bin`（`@ 0x00108000`，`cp_mutation_bytes=0`）；Stage 3 `Soft-GPE0` + `ramfb`；Stage 4 纯 Python `CXD90057` FDT `0xd00dfeed`（`4,614 B`）+ `MmioWindowBus` + `MHLX` 8 通道环；Stage 5 `IMX510`/XAVC/`RTMD 0xE304`/双 CFexpress & SDXC 流水线。 |
| **[`outputs/fx3-firmware-lab`](../outputs/fx3-firmware-lab/README.md)** | `Phases 27, 31, 37, 43, 46` | **157** | 8 大净室无密钥审计器（`audit-all`）：`UFU`/`FDAT`/`UDTRFIRM`/`SDM2`（`5L+6S` 门控）、`ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4` 差异与 `5016×3344` 负向证明、62 包 29 语言 `.uxc` + 6 套 CJK `.ltt`/`.ttf` + 1,610 精灵 CPU `LDEC`、`IMX510`/双原生 ISO/XAVC 矩阵、`.cube` `17³→33³` + `RTMD 0xE304`、`WBI2`/`hibdrv` EL1 失配拦截 + ELF64 `.dynsym` 差异与 `global.xdb` 128 页菜单树审计。 |
| **合计 (`make test`)** | **`Phases 1..50`, `Rounds 1..11`** | **`1,045`** | 同步执行 [`docs/BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) 57+57 指纹对齐审计 + `git status --porcelain` 净室零二进制/零 `.pyc` 残留门禁。 |

---

## 二、Stage-B `P1..P12 + Fan` 兼容补丁矩阵（`13/13` 锁表）

Stage-B 在完全保持 Stage-A（`P1..P9+Fan`，`include_p10_keymap=False`）确定性 SHA-256 与 CPIO 契约不变的基础上，扩展至 **`13/13` 项 Stage-B 锁定清单**（`8` 份 ELF64/内核模块规格共 `18` 个非重叠锚点 + `opelog.vfat` + `P5/P6`、`P7`、`P11` 运行时契约 + `BK4\0` 影子），支持 **100% 逐比特无损 SHA-256 回滚**：

| 补丁项 | 目标库 / 契约 | 锚点 / 地址 | 功能与净室安全边界 |
| :--- | :--- | :--- | :--- |
| **`P1..P4`** | `libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `opelog.vfat`, `libInfraAppRemoteBoard.so`, `appFw.so` | `/dev/nflasha20 -> 30`、`opelog.vfat`、`0x157C/0x1700`、`0x2111358/0x21113F0` | LUT 分区重映射至 FX3 `48 MiB` `p30`（`+32.04 MiB` 余量）；`8 MiB` 内存回环日志；剪除远程面板阻塞；`P4` 将可变电子 ND 锁定为 `Clear`（`576/576` Unicorn 验证）。 |
| **`P5..P9+Fan`** | `0x92840747` UIPC、`pcidma_transfer_async`、`appFw.so`、`upm.ko`、`libfan.so` | `0x032d`/`0x0400..0x0152`、Sync100 跳板、`0x2159C50`、`.text+0x136B8`、`0x1DEC` | 保持 FX3 原厂内核与原厂 CP `0 B` 改动；解除异步日志阻塞；内存补丁 FX3 `upm.ko` 空指针保护（`0` 个 FX6 `.ko` 加载）；`libfan.so` 返回 `1` 保留四档温控。 |
| **`P10`** *(Stage-B)* | `appFw.so`（与 `P1+P4+P8` 零重叠合并，`41 B` / `10` 锚点） | `.rodata` `0x2245A84..0x2246134` | 将 FX3 机身物理按键重映射至 FX6 功能：`Fn→HOME`、`C1→KURU_PON`、`C2→MENU_CANCEL`、`C3→DISP_SEL`、`PLAY→THUMBNAIL`、`DELETE→USER`，合并 SHA-256 = `e2bc2619...`。 |
| **`P11`** *(Stage-B)* | AP 侧 `UipcCpShimRuntime`（不改 CP） | `0x92d2091c`、 `0x91db059b`、`developing_mode_FHD` | `/dev/rtc0 → udate` 解除 `std::promise` 挂起；对 FX6 手柄队列 `0x91db059b` 合成脱离手柄 ACK（`551`）从而**完整保留 `XLR-H1`（`0x5d90`）热靴音频**；打通 Cine EI / `33³` LUT DMA（`0x0165`/`0x0166`）与 FX3 **5 轴 IBIS 通电居中锁止**。 |
| **`P12`** *(Stage-B)* | `libWlanResource.so` + `/tmp/bk4_shadow`（`BK4\0`） | `0x70D4`（`_Z16handleFatalErrorv`）+ `BK4` 键表 | 将 `while (1) usleep(1_000_000)` 死循环替换为 `mov w0, #0; ret`（`7 B` 差异，SHA-256 `47fec188...`）免疫 Sony 通告 **`00342260` (`WF-12`) 无限重启**；叠加冷启飞行模式 RAM 影子（`0x019e0012=00`、`0x0051000f=00`、`0x01a20002=00`）与 `BK_LANG`（`0x02cf019c`: `en=0x00`/`ja=0x01`/`tchinese=0x18`/`schinese=0x19`）。 |

---

## 三、`G01..G16` 16 门禁主安全预检引擎与 `Tier-0..Tier-4` 救砖阶梯

### 3.1 `G01..G16` 安全门禁摘要（详见 `outputs/fx3-safety/fx3_safety/master_16gate_preflight.py`）
- **`G01..G09`（离线固件、服务通道、Boot 契约与 4 层容错架构）**：校验 FX3 `7.02` 基准哈希、USB 服务认证闭环、只读 `AdjustControl`（拦截 `0x4003..0x4007`）、`p1` 回滚引擎、静态 Tier-0 采集器、SPI NOR / Sector-0、Bank 0/1 无重叠表、QEMU 沙盒 / `serial_fault_detector_v2`，以及 **4 层免变砖架构**（`mount --bind` + 清空 `/tmp/mod_arm_once` Clear-Before-Exec + 看门狗 + `/setting/updater/mode5` 回退）。
- **`G10..G12`（同机 Tier-0 只读双遍校验与红线汇总）**：强制真机采集全部 **11 项 Tier-0 关键分区/校准 + `p8_tomco.txt` + `p5_wbi_header.bin`**（`pass1_sha256 == pass2_sha256`、`os.O_RDONLY | O_NOFOLLOW`），并汇总 `U1..U5`、`.ko`/ABI、Stage-B 与运行时红线（`ld.so.preload` / `dd` / `nflasha10` / `PRODUCT_MODEL`）。
- **`G13`（Multi-Port 与 MI 热靴物理隔离）**：强制 `RP2040-Zero -DOPEN_DRAIN`（`1.8V/3.15V`），严禁 `VMC-BNCM1` LTC 线与 `uart_boot`（`Pin 7/8/9`）并接及标准 Pico `GP29`（`VSYS/3`）；验证 `P11` `0x91db059b` 与 `XLR-H1` 共存、`CrSDK` PTP2 与 `SPACC` `cnflasha` 隔离。
- **`G14`（散热风扇 PWM 与 `NP-FZ100` / `USB-PD` 供电包络）**：要求 `CXD90057 SoC < 62.0°C` 启动余量、验证 `libfan.so @ 0x1dec`（`62°C` 强制升速、`82°C` 告警、`90°C` 强制卸载）、强制 InfoLITHIUM `NP-FZ100 >= 80% / >= 7800 mV`（拦截 `BP-U 11500 mV` 误关机）及 `USB-PD 9V/3A` 压降 `<= 450 mV`。
- **`G15`（C2PA 签名库、出厂校准分区不可变性与 `exFAT` 掉电卫生）**：严禁任何挂载/写入触及 `cnflasha*`、`RPMB`、TrustZone/OP-TEE、Sony **C2PA**（`RQ_LIC.DAT`、`sigcert.p12/.pfx`、`p12:/cert`）或出厂校准区（`psd.bin`、`defdet.bin`、`Backup.bin`、`p6:/tmp/jiritsu`、`p18:/lens/lensfile.bin`、`SPI NOR ddrtraining.dat`），并拦截携带 `VolumeDirty=1`（VBR `0x6A`）或未封口 `.RSV` 的介质进入实验流。
- **`G16`（Stage-B `P12` `WF-12` 与 `WBI2` 冷启动硬锁）**：核验 `libWlanResource.so` `0x70d4` 与 `BK4\0` 飞行影子，锁死 `wbi_mutation_bytes = 0`、`cp_mutation_bytes = 0`、`nvram_persistent_writes = 0` 与 `persistent_emmc_writes_authorized = False`。

### 3.2 `Tier-0..Tier-4` 救砖升级阶梯（12 场景 `S01..S12`，详见 `unbrick_ladder_and_capsule_verifier.py`）
1. **`TIER_0`（断电与一次性锁存自愈）**：由于 `Clear-Before-Exec` 在挂载前已删除 `/tmp/mod_arm_once`，或 `p1` VFAT `boot_attempts >= 1` 触发自动跳过，移除电源/电池 `>= 60s` 即可 100% 零残余回归原厂 `FX3 v7.02`。
2. **`TIER_1`（macOS 26 `IOUSBHost` 静默等待与 `U5` 二步退出）**：解决 `0xe00002be` 占用冲突（`>= 350ms` 静默 + `[50..800ms]` 指数退避，STALL 零重传，拒绝 Senser v2 RSA）以及手动 `p1` 退出（`rm -f /setting/updater/mode* && sync && ud_send_lsi.elf 0`）。
3. **`TIER_2`（`p1` VFAT 原子胶囊与 `v7.02` 4 锚点自动定位）**：强制 AArch64 `ADRP/BL` 自动解析 `v7.02` 偏移、校验 `FAT1==FAT2` / LFN 校验和与 6 步 `fsync` 原子落盘，并阻断 `ld.so.preload` / 跨机型 `WBI2` 注入。
4. **`TIER_3`（免拆机 Multi-Port `48000` 波特率 BootROM + 只读 Fastboot v0.5）**：仅允许 **`RP2040-Zero -DOPEN_DRAIN`**（拔除 `VMC-BNCM1`、禁用 Pico `GP29`），注入 `0x92028000`（Mira SRAM）/ `0xFE020000`（eSRAM），拦截 `>= 0xFFFFC000` WDT 陷阱，防火墙仅放行 `oem dumpbrom` / `oem partition dump` 等只读命令。
5. **`TIER_4`（离线只读 eMMC 5.1 ISP 取证审计）**：严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 检测全 `0x00`/全 `0xFF`/总线拉死、AES-XTS 熵坍塌、`Sector 0` / `BK4\0`（`0x91030080`）/ `WBI2` / `cpapp-b.bin` 魔数、`EXT_CSD[179]`（`BOOT_PARTITION_ENABLE == 0` 变砖拦截）与禁用 `CMD42` 强擦。
