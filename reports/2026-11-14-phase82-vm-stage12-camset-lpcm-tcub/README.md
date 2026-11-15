# Phase 82 — Stage 12 Co-Emulation: Cross-Body `CAMSET` FX6->FX3 Sanitizer, 4-Channel `24-bit/48 kHz` LPCM (`-20 dB` Safety-Track + Limiter) & SMPTE 12M `User-Bits` / `HDMI TC OUT` Regenerator

**Date**: 2026-11-14  
**Scope**: `outputs/fx3-vm/` (Stage 12 Co-Emulation Module wired into the 12-Stage Heterogeneous Co-Emulation Suite, 36 Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation**: [`outputs/fx3-vm/camset_lpcm_tcub_emulator.py`](../../outputs/fx3-vm/camset_lpcm_tcub_emulator.py)  
**Wave-8 Intelligence Sync**: [`reports/2026-11-14-global-sony-wave8-camset-alsa-unbrick-intel/README.md`](../2026-11-14-global-sony-wave8-camset-alsa-unbrick-intel/README.md)

---

## 1. Executive Summary

Phase 82 delivers **Stage 12** (`stage12_phase82_camset_lpcm_tcub`), extending [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) to **12 co-emulated stages** (`--skip-phase82` backward compatibility preserved) under strict `os.O_RDONLY` donor auditing and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **Cross-Body `CAMSET` A-Cam `ILME-FX6` -> B-Cam `ILME-FX3` Fleet Profile Sanitizer & Volatile Shadow Loader**:
   - Imports an A-Cam `ILME-FX6` `v6.01` scene/camera profile (`Cine EI 800`, `S-Gamut3.Cine/S-Log3`, `User1.cube`, `23.98p 180.0°`, `5600K`, plus FX6-specific `ND 1/16`, `12G-SDI 4K 23.98p`, `VF Zebra`, `Wi-Fi AP=On`) onto B-Cam `ILME-FX3` Stage-B inside a volatile RAM shadow (`ram://tmp/camset_bcam_fx3_shadow.json`, SHA-256 `7f4d73e6835ef934...`).
   - Preserves **100.0%** of shared Cinema Line imaging parameters (`shooting_mode`, `base_iso`, `exposure_index`, `color_gamut`, `gamma_curve`, `user_lut_name`, `lut_embedded`, `fps_label`, `shutter_angle_deg`, `white_balance_k`, `codec`, `tc_run`, `tc_make`) while deterministically clamping/scrubbing hardware-absent and RF-forbidden fields (`nd_preset -> "Clear"`, `sdi_out -> "CONTAINED_DISABLED"`, `vf_zebra -> LCD redirected`, `wlan_ap -> False` with `P12` Airplane-Mode shadow `0x019e0012=00` & `0x01a20002=00`, `bt_tx_packets == 0`, `bk4_persistent_nvram_writes == 0`, and persistent `/dev/nflasha*` / `bk4://persistent` targets explicitly blocked).
2. **4-Channel `24-bit / 48 kHz` LPCM (`XLR-H1` CH1/CH2 + `-20 dB` Safety-Track CH3/CH4) & Brickwall Peak Limiter**:
   - Models sample-accurate `int24` (`[-8388608, +8388607]`) `480`-frame (`10 ms`) `S24_3LE` (`5,760 B`, SHA-256 `3aa7b517fa1933fb...`) and QEMU `virtio-sound` `S32_LE` (`7,680 B`) containers:
     - **Brickwall Peak Limiter + `-20.0 dB` Backup Safety Track**: Under `+12 dBFS` transient overload, the `-0.5 dBFS` brickwall limiter engages (`106` clipped peak samples clamped cleanly at `7,919,356` with **`0` `int24` overflow wrap-arounds**), while `CH3/CH4` capture an unclipped `-20.0 dB` backup pad (`3,339,565` peak, `0` clipped samples).
     - **Phase 77 `+48V` Phantom Firewall**: Permits `+48V` on `BALANCED_CONDENSER` while rejecting `PASSIVE_RIBBON_UNISOLATED`, `UNBALANCED_TRS_WIRELESS`, `SMPTE_LTC_SOURCE`, and `LINE`-mode inputs (`BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD`).
     - **`XLR-H1` Hot-Detach & Off-Speed `S&Q` Mute**: Detaching `XLR-H1` drops `+48V` VBUS to `0.25 V` and switches atomically via `P11` isolation (`0` `IVSHMEM` leaks) to `INTERNAL_STEREO_FALLBACK`; `S&Q` `120fps`/`240fps` off-speed mutes all 4 channels cleanly (`nonzero_samples == 0`).
3. **SMPTE 12M `User-Bits` (`BG1..BG8`) Fleet Tagging & `TC IN` (`Multi-Port`) -> `HDMI TC OUT` Regenerator**:
   - Encodes `CamID=B`, `Reel=002`, `MasterCam=A`, and sync flags (`EXT-LK`, `HDMI TC OUT`, `Drop-Frame`, nibble parity) into 32-bit Binary Groups (`BG1..BG8` = `42 00 24 13`) inside 80-bit `0x3FFD` LTC frames (`4020000820401130fcbf`), locks to A-Cam via `VMC-BNCM1` `Multi-Port` with **`0` frame offset**, enforces Phase 38 `uart_boot` `1.8V` isolation (`BLOCKED_MULTIPORT_UART_BOOT_CONTENTION`, `uart_boot_contention_events == 0`), and regenerates clean `HDMI TC OUT` downstream.

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity

All 10 compact FX3 `v7.02` & FX6 `v6.01` donor binaries (`750,680 B` total) are audited strictly via `os.O_RDONLY` in Local Donor mode and matched deterministically via pinned SHA-256 contracts when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active:

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_backup_mgr_so` | FX3 `libBackupManager.so` | `10,272` | `_Z11BkDmn_writejPKvi` + `Backup_read` | `ef95ca41dadc...` |
| `fx3_ext_backup_comm_so` | FX3 `libInfraExtBackupCommunicator.so` | `22,960` | `ExtBackupCommunicator_Init` + `ReadBackup` | `3c774e9d4bec...` |
| `fx3_backup_so` | FX3 `libbackup.so` | `14,232` | `Backup_read` + `Backup_write` | `6a3c5f606762...` |
| `fx3_wlan_res_so` | FX3 `libWlanResource.so` | `56,464` | `wlanResource_init` + `ChangeInhFactorStatus` | `76fe66f7c763...` |
| `fx3_str_en_g_uxc` | FX3 `string_english_g.uxc` | `69,600` | `Airplane` + `HDMI` UI strings | `a4a15a548f7e...` |
| `fx6_setupfile_so` | FX6 `libInfraSetupFile.so` | `202,664` | `SetupFile::loadSetupFile` + `LutFileBackup` | `b489c64adef1...` |
| `fx6_backup_so` | FX6 `libbackup.so` | `14,232` | `Backup_read` + `Backup_write` | `e003e2d8a1f4...` |
| `fx6_multiif_so` | FX6 `libInfraMultiIF.so` | `194,240` | `InfraMultiIF_Init` + `InfraMultiIFManager` | `4f18de86260c...` |
| `fx6_hotshoe_so` | FX6 `libInfraHotshoe.so` | `47,808` | `WaitRecvCompMsgFromHotshoeRsrc` + `SHOEINFO_EVT` | `0bf55367c034...` |
| `fx6_str_en_uxc` | FX6 `string_english.uxc` | `118,208` | `48kHz` + `24bit` + `Timecode` + `XLR` | `5e88dd707cb4...` |

---

## 3. Verification Receipts & Timing

All commands were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `camset_lpcm_tcub_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `0.061s` | `f4120f67706e...` |
| `camset_lpcm_tcub_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.062s` | `8b0d75bd9fa7...` |
| `fx3_vm_coemulation_suite.py --summary` (All 12 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.206s` (`< 1.4s`) | `009f41ecacaa...` |
| `fx3_vm_coemulation_suite.py --summary` (All 12 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.356s` (`< 0.5s`) | `ecd960e17c39...` |
| `fx3_vm_coemulation_suite.py --skip-phase82 --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | Backward-compat | `13ce41ef29a8...` |
| `unittest test_camset_lpcm_tcub_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `1.061s` | `36 / 36` tests |
| `unittest test_camset_lpcm_tcub_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.978s` | `36 / 36` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `LOCAL_DONOR_RDONLY` | PASS | `7.494s` | `352 / 352` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | PASS | `5.783s` | `352 / 352` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | PASS | `0.43s` | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `bk4_persistent_nvram_writes == 0`, `nvram_persistent_writes == 0`, `null_gpio_derefs == 0`, `mailbox_stalls == 0`, `uart_boot_contention_events == 0`, `physical_device_writes == 0`.
- `persistent_emmc_writes_authorized == False`, `p12_airplane_mode_enforced == True` (`bk4_shadow_0x019e0012 == 0x00`, `bk4_shadow_0x01a20002 == 0x00`), `int24_overflow_wraparounds == 0`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
