# Phase 67 — Stage 9 Co-Emulation: Multi-Camera SMPTE 12M TC `EXT-LK`, E-Mount PZ Servo/Breathing & `libpaint` 3x3 Color Matrix

**Date**: 2026-11-14  
**Scope**: `outputs/fx3-vm/` (Stage 9 Co-Emulation Module, Dual-Mode Suite Integration, 33 Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation**: [`outputs/fx3-vm/tc_genlock_lens_paint_emulator.py`](../../outputs/fx3-vm/tc_genlock_lens_paint_emulator.py)

---

## 1. Executive Summary

Phase 67 adds **Stage 9** (`stage9_phase67_tc_lens_paint`) to the FX3/FX6 Heterogeneous Co-Emulation Suite in [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py), closing three cinema-production co-emulation domains under strict read-only donor auditing (`os.O_RDONLY`) and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **Multi-Camera SMPTE 12M LTC `EXT-LK` PLL & Drop-Frame/NDF Engine**:
   - Models `23.98p` (`23.976`), `24.00p`, `25.00p`, `29.97p_ndf`, `29.97p_df`, `50.00p`, `59.94p_ndf`, and `59.94p_df` timebases, 80-bit SMPTE 12M LTC framing with forward (`0x3FFD`) / reverse (`0xBFFC`) sync words and biphase even-parity bits, and exact `29.97 DF` minute-10 drop-frame math (`00:00:59;29 -> 00:01:00;02`, `00:09:59;29 -> 00:10:00;00`).
   - Proves `VMC-BNCM1` (`680 kΩ` Multi Port ID) `EXT-LK` PLL lock keeps drift at **`0.0` frames** (`2.5 µs` phase error) over a 12-hour multi-cam shoot vs **`0.5179` frames** (`21.6 ms`) `Free-Run` crystal drift (`±0.5 ppm` TCXO), retains **`0.2589` frames** (`PSEUDOLOCK`) across a `6-hour` BNC unplug holdover, and strictly enforces **Phase 38 `uart_boot` `1.8V` electrical isolation** (blocking `0.5..4.5 Vpp` LTC injection whenever `bootrom_uart_boot_latched=True`).
2. **E-Mount `libInfraLensCommunicator` PZ Servo, Breathing Crop LUT & Stock-CP 5-Axis IBIS Fusion**:
   - Models `SELP1635G` (`16–35mm`) and `SELP28135G` (`28–135mm`) over the `MHLX 0x0210 -> 0x8210` lens channel: jerk-limited 8-speed Power Zoom (`PZ 1..8`) trapezoidal velocity ramps with **`0.0 mm` overshoot**, Focus-Breathing Compensation dynamic FOV scale (`1.000x` at infinity to `1.075x` at `0.28 m`) packed/unpacked into `RTMD 0xE304` metadata, and Stock-CP `cpapp-b.bin` 5-Axis IBIS (`Active` / `Standard` / `Off 0x0400 Center-Lock`) + Lens OSS axis-split arbitration (`cp_mutation_bytes == 0`).
3. **`libpaint` Cinema Line Color Pipeline (`S-Log3` / `S-Cinetone` / 3x3 Paint Matrix / Knee)**:
   - Models 16-bit linear `IMX510` sensor samples (`18%` gray `0.18 * 65535 = 11796`) through the exact Sony `S-Log3` OETF/EOTF (`420.0` 10-bit at `18%`), `S-Cinetone` + highlight `Knee` rolloff (`590` 10-bit), and white-point-preserving 3x3 Paint Matrices (`sum(row) == 1.0`, `neutral_achromatic_delta <= 5.55e-17`), verifying exact bit-identical `HDMI RAW16` MLUT bypass vs `HDMI 4:2:2 10-bit` `MLUT=On` bake with FX6 `12G-SDI` safely no-op contained (`sdi_contained_noop=True`), `calibration_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity

All 10 compact donor binaries (`2,706,848 B` total) are verified strictly via `os.O_RDONLY` in Local Donor mode and matched deterministically via SHA-256 contract baselines when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active:

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_lens_comm_so` | FX3 `libInfraLensCommunicator.so` | `14,544` | `GetMountedLensInfo` | `e61bf145f050...` |
| `fx3_cam_movie_rec_so` | FX3 `CAMERA_SCN_MOVIE_REC_START.so` | `69,264` | `Convert(SCN_TC_MODE)` | `a258365bddea...` |
| `fx6_lens_comm_so` | FX6 `libInfraLensCommunicator.so` | `14,544` | `GetMountedLensInfo` | `8848b33084f7...` |
| `fx6_lanc_so` | FX6 `libInfraLanc.so` | `51,848` | `InfraLanc::Init` | `99e02239a918...` |
| `fx6_multi_if_so` | FX6 `libInfraMultiIF.so` | `194,240` | `InfraMultiIF_Init` | `4f18de86260c...` |
| `fx6_osal_udate_so` | FX6 `libosal_udate.so` | `27,344` | `udate_open_uif` | `358798c8352d...` |
| `fx6_hotshoe_so` | FX6 `libInfraHotshoe.so` | `47,808` | `WaitRecvCompMsgFromHotshoeRsrc` | `0bf55367c034...` |
| `fx6_avbb_video_so` | FX6 `AVBB_SCN_START_VIDEO.so` | `268,088` | `TC+Lens+Matrix+Knee` | `f3aa48395762...` |
| `fx6_avbb_panelevf_so` | FX6 `AVBB_SCN_START_PANELEVF.so` | `275,968` | `SET_MONITOR_MLUT` | `36d98e83611f...` |
| `fx6_infra_avbbc_so` | FX6 `libInfraAvbbc.so` | `1,743,200` | `ParamInfraPaintImage` | `4ea694694cd7...` |

---

## 3. Verification Receipts & Timing

All commands were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `tc_genlock_lens_paint_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `< 0.3s` | `343b05768c70...` |
| `tc_genlock_lens_paint_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `< 0.2s` | `4de30e7551bd...` |
| `fx3_vm_coemulation_suite.py` (All 9 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.175s` (`< 1.4s`) | `ad2cbd8df766...` |
| `fx3_vm_coemulation_suite.py` (All 9 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.326s` (`< 1.4s`) | `4ab0eaded50f...` |
| `fx3_vm_coemulation_suite.py --clean-room --skip-phase67 --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `< 0.3s` | `4e3c532ea6bd...` |
| `unittest test_tc_genlock_lens_paint_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `0.611s` | `33 / 33` tests |
| `unittest test_tc_genlock_lens_paint_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.619s` | `33 / 33` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `LOCAL_DONOR_RDONLY` | PASS | `4.609s` | `246 / 246` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | PASS | `3.203s` | `246 / 246` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | PASS | `0.26s` | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `nvram_persistent_writes == 0`, `physical_device_writes == 0`, `persistent_emmc_writes_authorized == False`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
