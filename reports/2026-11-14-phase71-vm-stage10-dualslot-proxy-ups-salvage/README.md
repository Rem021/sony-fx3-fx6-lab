# Phase 71 — Milestone Stage 10 Co-Emulation: Dual-Slot Relay/Simul/Sort Proxy, `NonRealTimeMeta.xml` Sidecar & `USB-PD -> NP-FZ100` UPS / `.RSV` Clip Salvage

**Date**: 2026-11-14  
**Scope**: `outputs/fx3-vm/` (Final Stage 10 Co-Emulation Module completing the 10-Stage Heterogeneous Co-Emulation Suite, 34 Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation**: [`outputs/fx3-vm/dualslot_proxy_ups_salvage_emulator.py`](../../outputs/fx3-vm/dualslot_proxy_ups_salvage_emulator.py)

---

## 1. Executive Summary

Phase 71 delivers **Stage 10** (`stage10_phase71_dualslot_ups_salvage`), completing the **10-Stage FX3/FX6 Heterogeneous Co-Emulation Suite** in [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) under strict `os.O_RDONLY` donor auditing and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **Dual-Slot (`Slot A` + `Slot B`) Seamless `Relay` / `Simultaneous` / `Sort` Ring-Buffer & 256 MiB DRAM Elastic FIFO**:
   - Models real-time `600 Mbps` `4K 59.94p XAVC S-I` (`1.25 MB/frame` GOP=1) + `16 Mbps` `1080p XAVC HS 10-bit Proxy` (`S03.MP4`) across virtualized exFAT `Slot A` and `Slot B`:
     - **`Relay` Auto-Switch**: `Slot A` fills to `0` free clusters mid-take, closes `A001C001_261114_FX3V.MP4` cleanly (`moov_finalized=True`, `VolumeDirty=0`), and the `256 MiB` DRAM Elastic FIFO absorbs the `85.0 ms` `Slot B` open/FAT-alloc latency (`6,545,000 B` peak = `2.44%` FIFO) with **`0` dropped frames**, seamlessly continuing onto `Slot B` (`A001C002_261114_FX3V.MP4`).
     - **`Simultaneous` Dual-Write**: Proves `Slot A == Slot B` frame-level CRC32 & SHA-256 parity and graceful single-card survival when `Slot B` is hot-yanked mid-take (`0` dropped frames on `Slot A`, `0` crashes/WDT resets).
     - **`Sort` (`CFexpress Type A VPG400` Main + `SDXC UHS-II V60` Proxy `S03.MP4`)**: Verifies normal concurrent proxy recording at `59.94p` and clean proxy auto-suspension (`SQ_OFF_SPEED_AUTO_SUSPEND`, `0` proxy writes) when `S&Q` off-speed (`120fps` / `240fps`) is engaged without stalling Main (`0` dropped frames).
2. **In-Memory `NonRealTimeMeta` (`*M01.XML`) + `RTMD 0xE304` Provenance Synchronizer**:
   - Synthesizes and parses Sony `NonRealTimeMeta` XML strictly in memory at clip close and cross-checks 100% of fields against live Stage 9/10 state and `RTMD 0xE304` (`Cine EI 800/12800`, `S-Gamut3.Cine / S-Log3`, `.cube` User LUT slot, `SMPTE 12M` `StartTimecode`, `SELP1635G`/`SELP28135G` focal length, Focus-Breathing FOV scale, and `IBIS` mode), preserving `c2pa_license_untouched == True` and `internal_emmc_writes == 0`.
3. **Mid-Take Power-Loss (`USB-PD 9V/3A` Yank -> `NP-FZ100` UPS vs Battery-Less `.RSV` Salvage)**:
   - **`PWR_USBPD_YANK_NPFZ100_UPS`**: `USB-PD` yanked with `NP-FZ100` at `65%` SoC (`7630 mV`) -> `0.4 ms` ideal-diode switchover (`< 8.5 ms` holdover margin), **`0` dropped frames**, continuous recording uninterrupted.
   - **`PWR_NPFZ100_CRITICAL_2PCT_FLUSH`**: `NP-FZ100` reaches critical `2%` (`6200 mV` brownout threshold) -> Stock-CP `PMIC` warning triggers controlled `libmpr` emergency flush, finalizing `moov` + `M01.XML` + exFAT `VolumeDirty=0` before shutdown (`0` corrupt clips).
   - **`PWR_BATTERYLESS_BROWNOUT_RSV`**: Instantaneous `battery_less` brownout drill in synthetic memory -> builds `.RSV` raw stream salvage container (`A001C001_261114_FX3V.RSV`) and recovers all committed ring frames (`salvageable_frames == committed_ring_frames = 114/114`, `VolumeDirty=0`, `p1_emmc_mutations == 0`, `persistent_emmc_writes_authorized == False`).

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity

All 10 compact donor binaries (`4,911,408 B` total) are verified strictly via `os.O_RDONLY` in Local Donor mode and matched deterministically via pinned SHA-256 contract baselines when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active:

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_libmpr_so` | FX3 `libmpr.so` | `3,517,008` | `NonRealTimeMeta+M01.XML+S03.MP4+Salvage+Relay+Simul+Proxy+moov` | `9aeef3b9edb3...` |
| `fx6_libinfra_fsys_so` | FX6 `libInfraFsys.so` | `687,816` | `PFEX_DRV_setVolumeDirty+force/salvage/nomedia` | `78e6f1d90139...` |
| `fx6_libinfra_media_common_so` | FX6 `libInfraMediaCommon.so` | `402,624` | `MediaCommon_Buf.c+MediaCommon_Dmm.c` | `acbabff1ac35...` |
| `fx6_libinfra_media_detect_so` | FX6 `libInfraMediaDetect.so` | `98,224` | `InfraMediaDetect::CallbackPoint` | `8883fef94a7b...` |
| `fx6_libinfra_media_mount_so` | FX6 `libInfraMediaMount.so` | `65,392` | `InfraMediaMount::CallbackPoint` | `ec4778170e9f...` |
| `fx6_libinfra_media_config_so` | FX6 `libInfraMediaConfig.so` | `52,312` | `InfraMediaConfig::GetMediaIDByAtrribute` | `9709656102d5...` |
| `fx6_libinfra_meta_supplier_so` | FX6 `libInfraMetaSupplier.so` | `23,048` | `InfraMetaSupplier_Init` | `566d12fe3e12...` |
| `fx6_libul_xml_so` | FX6 `libul_xml.so` | `72,784` | `ul_xmlparser.cpp` | `89deaca74a8f...` |
| `fx6_libbuspower_so` | FX6 `libBusPower.so` | `43,968` | `SetUSBPDSinkStatusToPowerManager+VBUS_CHANGED` | `d4f2ffe4e747...` |
| `fx6_libusbbuspower_so` | FX6 `libUsbBusPower.so` | `48,232` | `SetPortStatus+onVbusOffReceived` | `4215a9e989d2...` |

---

## 3. Verification Receipts & Timing

All commands were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `dualslot_proxy_ups_salvage_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `< 0.1s` | `62125abf0992...` |
| `dualslot_proxy_ups_salvage_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `< 0.1s` | `13949e956d2f...` |
| `fx3_vm_coemulation_suite.py --summary` (All 10 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.056s` (`< 1.5s`) | `cc658c428f26...` |
| `fx3_vm_coemulation_suite.py --summary` (All 10 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.297s` (`< 0.5s`) | `1ed7e8174f73...` |
| `unittest test_dualslot_proxy_ups_salvage_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `0.960s` | `34 / 34` tests |
| `unittest test_dualslot_proxy_ups_salvage_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.942s` | `34 / 34` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `LOCAL_DONOR_RDONLY` | PASS | `5.862s` | `280 / 280` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | PASS | `4.331s` | `280 / 280` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | PASS | Verified | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `nvram_persistent_writes == 0`, `physical_device_writes == 0`, `p1_emmc_mutations == 0`, `internal_emmc_writes == 0`.
- `c2pa_license_untouched == True`, `persistent_emmc_writes_authorized == False`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
