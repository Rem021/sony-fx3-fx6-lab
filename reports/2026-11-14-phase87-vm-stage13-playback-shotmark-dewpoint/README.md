# Phase 87 — Stage 13 Co-Emulation: Playback/Thumbnail Shuttle, `ShotMark1/2` `<EssenceMark>` Sync, `Cine EI` `Push Auto Iris` & Dewpoint/PMIC HIL

**Date**: 2026-11-14  
**Scope**: `outputs/fx3-vm/` (Stage 13 Co-Emulation Module wired into the 13-Stage Heterogeneous Co-Emulation Suite, 36 Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation**: [`outputs/fx3-vm/playback_shotmark_dewpoint_emulator.py`](../../outputs/fx3-vm/playback_shotmark_dewpoint_emulator.py)  
**Co-Emulation Suite**: [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)  
**Unit Tests**: [`outputs/fx3-vm/tests/test_playback_shotmark_dewpoint_emulator.py`](../../outputs/fx3-vm/tests/test_playback_shotmark_dewpoint_emulator.py)

---

## 1. Executive Summary

Phase 87 delivers **Stage 13** (`stage13_phase87_playback_shotmark_dewpoint`), extending [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) to **13 co-emulated stages** (`--skip-phase87` backward compatibility preserved) under strict `os.O_RDONLY` donor auditing and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **Thumbnail / Playback Shuttle (`1x, 2x, 5x, 15x` Fwd/Rev), `ShotMark1 / ShotMark2` `<EssenceMark>` Sync & Internal eMMC `p1` Media Isolation**:
   - Models `PlaybackShotmarkMediaSession` across `Slot A` and `Slot B` clips (`A001C001..A001C008`), deterministic transitions across `SHOOTING_LIVE_VIEW <-> THUMBNAIL_INDEX <-> PLAYBACK_SHUTTLE`, and `1x, 2x, 5x, 15x` forward/reverse shuttle clamping cleanly to clip bounds.
   - Punches live `ShotMark1` (`OK`) and `ShotMark2` (`KEEP`) markers during both `REC` (`SHOOTING_LIVE_VIEW`) and `PLAYBACK_SHUTTLE`, and round-trips frame-accurate `<EssenceMarkTable>` / `<EssenceMark>` elements into the in-memory `NonRealTimeMeta` (`*M01.XML`) sidecar with **100.0%** parity (`4` punched marks synced cleanly).
   - Proves `Delete Clip` on protected clips (`ClipProtected=True`: `A001C002`, `A001C006`) and `Format Media` targeting internal `/dev/mmcblk0p1` (`p1` eMMC) are **100% blocked fail-closed** (`internal_emmc_format_blocked == True`, `persistent_emmc_writes_authorized == False`, `p1_emmc_mutations == 0`, `internal_emmc_writes == 0`).
2. **`Cine EI` `Push Auto Iris` (`1/8`-Stop Servo Convergence to `41.0% IRE` `S-Log3` Middle Grey / `< 94.0% IRE` Highlight-Clip Guard) with `0` `P4` ND Faults**:
   - Emulates holding FX3's `Push Auto Iris` assignable button under `Cine EI` (`Base 800`, `180.0°` shutter angle locked) during a `+3.5 EV` illumination surge.
   - Smoothly steps E-Mount aperture (`T1.4 -> T4.8`) over `28` `1/8`-stop (`0.125 EV`) increments via `MHLX` lens servo packets (`0x0220 -> 0x8220`) until an `18%` grey card converges to **`41.02% IRE` `S-Log3`** (and `HIGHLIGHT` metering mode settles at `T5.2` keeping peak specular highlights at `92.31% IRE < 94.0% IRE`), with **`0` `P4` Variable ND motor calls** and **`p4_nd_motor_faults == 0`**.
3. **Environmental Dew-Point (`TEC` Condensation Trap) & PMIC `5V` Accessory Current-Budget HIL Co-Emulation**:
   - Models tropical set humidity (`31.0°C / 80.0% RH`, Magnus-Tetens `T_dp = 27.14°C`, safe floor `29.14°C`) and hot-plugged accessories (`XLR-H1 +48V` `360 mA` + active optical HDMI `160 mA` + bus-powered USB-C LAN `420 mA` = `940 mA > 900 mA`).
   - Verifies that sub-dewpoint external `TEC` cooling (`11.0°C < T_dp`) triggers `BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD` with immediate `TEC` shedding (`condensation_risk_pct == 0.0`, `pmic_rail_faults == 0`) and `> 900 mA` unpowered `5V` draw triggers `BLOCKED_PMIC_5V_OVERBUDGET_SHED_BEFORE_RAIL_FAULT` (`post_shed_5v_draw_ma = 520 mA`, `pmic_rail_faults == 0`), while internal `libfan.so` air cooling (`39.5°C`) and a powered USB-PD hub (`520 mA`) run `100%` green.

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity

All 10 compact FX3 `v7.02` & FX6 `v6.01` donor binaries (`505,144 B` total) are audited strictly via `os.O_RDONLY` in Local Donor mode and matched deterministically via pinned SHA-256 contracts when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active:

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_libinfraccpf_static_so` | FX3 `libInfraCCPFStatic.so` | `122,160` | `CCPF` Playback/Media Control (`ELF64`) | `b991137ce1e8...` |
| `fx3_libinfra_media_config_so` | FX3 `libInfraMediaConfig.so` | `52,312` | `MediaConfig` Slot/Clip Schema (`ELF64`) | `483548d53dfb...` |
| `fx3_libinfra_media_mount_so` | FX3 `libInfraMediaMount.so` | `65,392` | `MediaMount` Format/Protect Guard (`ELF64`) | `33b4c61c39f7...` |
| `fx3_libinfra_lens_comm_so` | FX3 `libInfraLensCommunicator.so` | `14,544` | E-Mount `MHLX` Iris Servo (`ELF64`) | `e61bf145f050...` |
| `fx3_libfan_so` | FX3 `libfan.so` | `27,280` | Internal Centrifugal Fan Control (`ELF64`) | `c607fc8d3ea3...` |
| `fx3_libbuspower_so` | FX3 `libBusPower.so` | `43,968` | `5V` PMIC Bus Power Rail (`ELF64`) | `4c39d2789745...` |
| `fx3_libusbbuspower_so` | FX3 `libUsbBusPower.so` | `48,232` | USB-C VBUS Budget Monitor (`ELF64`) | `c606880c92ec...` |
| `fx6_libinfra_lanc_so` | FX6 `libInfraLanc.so` | `51,848` | Playback/ShotMark Remote Protocol (`ELF64`) | `99e02239a918...` |
| `fx6_libfan_so` | FX6 `libfan.so` | `31,176` | Cinema Line Thermal Fan Curve (`ELF64`) | `d4f01ff36a2d...` |
| `fx6_libusbbuspower_so` | FX6 `libUsbBusPower.so` | `48,232` | USB-PD / VBUS Power Policy (`ELF64`) | `4215a9e989d2...` |

---

## 3. Verification Receipts & Timing

All commands were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `playback_shotmark_dewpoint_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `0.06s` | `86a8ddcb2f22...` |
| `playback_shotmark_dewpoint_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.06s` | `a397a9748be8...` |
| `fx3_vm_coemulation_suite.py --summary` (All 13 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.18s` (`< 1.5s`) | `9543093f6b25...` |
| `fx3_vm_coemulation_suite.py --summary` (All 13 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.36s` (`< 0.5s`) | `d243e8125ce6...` |
| `fx3_vm_coemulation_suite.py --skip-phase87 --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | Backward-compat | `4f81d8ab4c62...` |
| `unittest test_playback_shotmark_dewpoint_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `0.982s` | `36 / 36` tests |
| `unittest test_playback_shotmark_dewpoint_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.994s` | `36 / 36` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `LOCAL_DONOR_RDONLY` | PASS | `9.126s` | `388 / 388` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | PASS | `6.830s` | `388 / 388` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | PASS | `0.45s` | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `bk4_persistent_nvram_writes == 0`, `nvram_persistent_writes == 0`, `null_gpio_derefs == 0`, `mailbox_stalls == 0`, `physical_device_writes == 0`.
- `persistent_emmc_writes_authorized == False`, `internal_emmc_format_blocked == True`, `internal_emmc_writes == 0`, `p1_emmc_mutations == 0`, `c2pa_license_untouched == True`, `p4_nd_motor_faults == 0`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
