# Phase 63 — Stage 8 `outputs/fx3-vm/` HDMI Type-A `4264x2408 16-bit Linear RAW` EDID Negotiation, `MLUT` Clean-Feed & USB-C Mode Arbitrator

# 第 63 阶段 — Stage 8 `outputs/fx3-vm/` HDMI Type-A `4264x2408 16-bit Linear RAW` EDID 协商、`MLUT` 净流与 USB-C 模式仲裁器

**Date / 日期**: `2026-11-14`  
**Owner / 负责代理**: Hydrogen-57 (`antigravity`, isolated child worktree)  
**Target Module / 目标模块**: [`outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py`](../../outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py)  
**Suite Orchestrator / 联合编排器**: [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`Stage 8`, `--skip-phase63`)  
**Unit Tests / 单元测试**: [`outputs/fx3-vm/tests/test_uvc_hdmi_raw_output_emulator.py`](../../outputs/fx3-vm/tests/test_uvc_hdmi_raw_output_emulator.py) (`30` dual-mode tests; `213` total tests in `outputs/fx3-vm/tests/`)  
**Hard Safety Redlines / 硬性安全红线**: `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `nvram_persistent_writes == 0`, `physical_device_writes == 0`, `persistent_emmc_writes_authorized == False`, `sdi_transceiver_faults == 0`, `nop_count == 0`, `os.O_RDONLY` only.

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 63 extends `outputs/fx3-vm/` to an **8-stage unified full-board virtual camera co-emulation stack** by implementing [`uvc_hdmi_raw_output_emulator.py`](../../outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py) and wiring **Stage 8** (`stage8_phase63_hdmi_raw_uvc`) backward-compatibly into [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) with an optional `--skip-phase63` flag (default enabled):
1. **Pure-Python VESA E-EDID / CEA-861 `256B` (`128B+128B`) Synthesizer & External Recorder Handshake**:
   - Synthesizes and strictly checksum-verifies (`00ffffffffffffff00` header + Block 0 & Block 1 mod-256 checksum `== 0`) E-EDID payloads for `ATOMOS_NINJA_RAW16` (`4264x2408 16-bit Linear RAW` up to `59.94p` + `ProRes RAW` VSDB + `SMPTE 12M` HDMI Timecode Rec-Trigger), `SMALLHD_CINE_10BIT_422` (`3840x2160` / `1920x1080` `10-bit YCbCr 4:2:2` + independent `MLUT` On/Off + OSD Clean-Feed toggle + graceful `16-bit RAW` rejection fallback without black-screening), and `HDMI_DISCONNECTED` (`HPD == 0` hot-unplug mid-recording returning seamlessly to internal `GPE0` `1024x540` LCD with `0` dropped XAVC frames).
   - Proves FX6-only `12G-SDI` sub-output/main settings remain safely contained as no-ops on FX3 (`sdi_transceiver_faults == 0`).
2. **USB-C Gadget Mode Arbitrator (`UVC/UAC` `4K30/1080p60` vs `USB-LAN CDC-NCM` vs `CrSDK PTP` vs `MSC`)**:
   - Models strict single-function mutual exclusion (`max_concurrent_gadgets <= 1`), enforces `P12` `BK4\0` Airplane-Mode wireless silence (`0` BT TX packets, WLAN off, `00342260` immune), `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False` (blocking `MSC` during shooting and `DFU` raw flash unconditionally).

**中文摘要**:  
第 63 阶段落地 [`uvc_hdmi_raw_output_emulator.py`](../../outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py)，并将 **Stage 8**（`stage8_phase63_hdmi_raw_uvc`，支持 `--skip-phase63` 默认开启）向后兼容地接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)，将 `outputs/fx3-vm/` 扩展为 **8 阶段**统一虚拟相机协同仿真栈：
1. **纯 Python VESA/CEA-861 `256B`（`128B+128B`）`EDID` 合成校验与外录握手**：完整覆盖 `ATOMOS_NINJA_RAW16`（`4264x2408 16-bit Linear RAW @ 59.94p` + `ProRes RAW` VSDB + `SMPTE 12M` HDMI TC 触发）、`SMALLHD_CINE_10BIT_422`（`4K`/`1080p` `10-bit YCbCr 4:2:2` + `MLUT` On/Off + OSD Clean-Feed 切换，并验证拒绝 `16-bit RAW` 时零黑屏优雅回退）、`HDMI_DISCONNECTED`（录像中 `HPD == 0` 热拔出零丢帧回落 `GPE0` `1024x540`）以及 FX6 `12G-SDI` 子输出设置无操作安全隔离（`sdi_transceiver_faults == 0`）。
2. **USB-C Gadget 模式仲裁器**：验证 `UVC/UAC`（`4K30`/`1080p60`）、`USB-LAN CDC-NCM`、`CrSDK PTP` 与 `MSC` 之间的严格单功能互斥状态机，全程保持 `P12` `BK4\0` 飞行模式无线静默、`cp_mutation_bytes == 0`、`wbi_mutation_bytes == 0` 与 `persistent_emmc_writes_authorized == False`。

---

## 2. Strictly Read-Only (`os.O_RDONLY`) FX6 Donor Artifact Receipts / 严格只读供体核验记录

| Key / 键名 | Donor Relative Path / 相对路径 | Size / 大小 | Verified SHA-256 / 校验和 | Verified Marker / 校验标记 |
| :--- | :--- | :---: | :--- | :--- |
| `fx6_usb_f_uvc_ko` | `nflasha15-files/kmod/usb_f_uvc.ko` | `78,840 B` | `bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305` | `uvc_function_bind` |
| `fx6_usb_f_uac2_ko` | `nflasha15-files/kmod/usb_f_uac2.ko` | `23,328 B` | `e5238ea8ff27590a7a28ff059a5b217a0ec010637fe967845e7b14e1557bd2dc` | `uac2_pcm_ioctl` |
| `fx6_g_webcam_ko` | `nflasha15-files/kmod/g_webcam.ko` | `13,728 B` | `bec168eebeba90e4b5f6a35e1c4e12bfc0a70242c4a99ad01fde4c29462110d0` | `usb_f_uvc` |
| `fx6_usb_f_mass_storage_ko` | `nflasha15-files/kmod/usb_f_mass_storage.ko` | `51,696 B` | `4eb4af6713b9a706854b4b3a2fd376101b5dc0b7d1b0fa5bb1a7000712419b57` | `fsg_config_from_params` |
| `fx6_g_mass_storage_ko` | `nflasha15-files/kmod/g_mass_storage.ko` | `11,240 B` | `870232b80763566ebf5ed9f53ca93898ea29e6235557cb04ca63e21cb50a18be` | `usb_f_mass_storage` |
| `fx6_usbg_stillimage_ko` | `nflasha15-files/kmod/usbg_stillimage.ko` | `49,448 B` | `c62b1b698f552f7476df08407cf754abaa796e91deb694ec1239ea079dc19caa` | `usbg_still_main` |
| `fx6_cdc_ncm_ko` | `nflasha15-files/kmod/cdc_ncm.ko` | `32,208 B` | `8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2` | `cdc_ncm_rx_verify_nth16` |
| `fx6_libusb_control_so` | `nflasha15-files/lib/libUsbControl.so` | `135,424 B` | `951d1da8a4366dc8cf7bf475181344ea487e661869701218a2343e9c9ecf1483` | `MSGID_SETCONFIG_MASSSTORAGE_EVT` |
| `fx6_libinfra_usb_cmn_so` | `nflasha15-files/lib/libInfraUsbCmn.so` | `164,144 B` | `a81404ed2f2c0a29fff34d53a2d145fa52632fa0a8796cee096353f4c8220d65` | `massstorage` |
| `fx6_avbb_panelevf_so` | `nflasha15-files/scenario/AVBB_SCN_START_PANELEVF.so` | `275,968 B` | `36d98e83611f3e26c7db4d84a7e045fceafc370470744352598db62f54b09b2b` | `AVBB_SCN_START_HDMI` |

---

## 3. Verification Receipts / 实测验证记录

1. **Standalone Phase 63 Emulator CLI (`uvc_hdmi_raw_output_emulator.py`)**:
   - Local Donor (`O_RDONLY`): `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py --self-test --summary`  
     -> `[PASS] Phase 63 HDMI RAW16 EDID & USB-C Arbitrator | mode=LOCAL_DONOR_RDONLY cp_mut=0 sdi_faults=0 | raw16=4264x2408@59.94p usbc=6ok/4blk | digest=beba52b054cc`
   - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py --self-test --summary`  
     -> `[PASS] Phase 63 HDMI RAW16 EDID & USB-C Arbitrator | mode=CLEAN_ROOM_SYNTHETIC cp_mut=0 sdi_faults=0 | raw16=4264x2408@59.94p usbc=6ok/4blk | digest=2cea3d26832b`
2. **8-Stage Co-Emulation Suite (`make verify-coemulation`)**:
   - Local Donor (`O_RDONLY`): `make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, **`1.179s`** (`< 2.5s` target).
   - Clean-Room: `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, **`0.335s`** (`< 2.5s` target).
3. **Unit Tests (`30` new Phase 63 tests + `213` total `outputs/fx3-vm/tests` dual-mode suite)**:
   - Phase 63 (`test_uvc_hdmi_raw_output_emulator.py`): `30` passed in **`0.216s`** (Local Donor) / **`0.206s`** (Clean-Room).
   - Full `outputs/fx3-vm/tests/`: **`213` tests passed** in **`4.434s`** (Local Donor) / **`2.940s`** (Clean-Room) — both `< 5s`.
4. **Hygiene & Safety Audit (`make clean-audit`)**:
   - Zero `.edid`/`.raw`/`.bin`/`.so`/`.elf`/`.ko`/`.cpio`/`.vfat`/`.pyc` or `__pycache__` artifacts.
