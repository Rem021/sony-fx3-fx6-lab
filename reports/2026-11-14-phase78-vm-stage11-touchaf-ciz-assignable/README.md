# Phase 78 — Stage 11 Co-Emulation: Capacitive Multi-Touch 627-pt PDAF Tracking, `Clear Image Zoom` (`CIZ`) Scaler & Assignable Button Dispatcher

**Date**: 2026-11-14  
**Scope**: `outputs/fx3-vm/` (Stage 11 Co-Emulation Module wired into the 11-Stage Heterogeneous Co-Emulation Suite, 36 Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation**: [`outputs/fx3-vm/touch_af_ciz_assignable_emulator.py`](../../outputs/fx3-vm/touch_af_ciz_assignable_emulator.py)

---

## 1. Executive Summary

Phase 78 delivers **Stage 11** (`stage11_phase78_touchaf_ciz_assignable`), extending [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) to **11 co-emulated stages** (`--skip-phase78` backward compatibility preserved) under strict `os.O_RDONLY` donor auditing and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **Linux `evdev` (`ABS_MT_POSITION_X/Y`) Capacitive Touch -> Stock-CP `IMX510` 627-Point (`33x19`) `PDAF` Window & Anamorphic Inverse Mapping**:
   - Models `960x540` `GPE0` multi-touch `evdev` packets (`24B` `struct input_event` `<QQHHi`) for `touch_down`, `drag`, and `double_tap_cancel` routed across the `MHLX` Linux<->Stock-CP mailbox (`0x0310..0x0314 -> 0x8310..0x8314`, `0` mailbox stalls) into `IMX510`'s `33 x 19 = 627` phase-detect AF grid (`95%` active sensor coverage `[0.025..0.975]`).
   - **Anamorphic Desqueeze Inverse Mapping (`1.3x` & `2.0x`)**: Maps letterboxed active display regions (`1.3x`: `y in [62.3077..477.6923]`, `2.0x`: `y in [135.0..405.0]`) back to exact optical sensor `(u, v)` coordinates and cleanly drops touches inside top/bottom letterbox matte bars (`OUTSIDE_ACTIVE_IMAGE_LETTERBOX_IGNORED`, `mhlx_dispatched=False`) instead of mis-focusing on sensor edges.
   - **`Focus Magnifier` (`1.0x -> 4.0x -> 1.0x`) Live Crop Pan & `HDMI RAW16` Clean-Feed**: Verifies `GPE0` preview magnifies `4.0x` centered on the active `PDAF` point (and pans smoothly across `drag` updates) while keeping recorded `XAVC` (`1.0x`) and `HDMI RAW16` clean-feed (`1.0x`) completely uncropped (`clean_feed_invariant=True`), with deterministic auto-exit / toggle restore per Cinema Line rules.
2. **Body `T/W` Zoom Rocker (`8-Step` Curve) + `Clear Image Zoom` (`CIZ` `1.5x` `4K` / `2.0x` `FHD`) Runtime Arbitrator**:
   - Emulates the full `8`-speed `T/W` rocker curve (`PZ 1..8`) transitioning seamlessly across `Optical PZ Servo` (`1.00x`, driving `SELP1635G` `16..35mm`) -> `Clear Image Zoom` (`1.00x..1.50x` in `4K`, `1.00x..2.00x` in `FHD`, retaining 627-pt `PDAF` and Real-Time Eye Tracking) -> `Digital Zoom` (`> 1.50x/2.00x`, transitioning AF area to `CENTER_SPOT_CONTRAST_ONLY` per real Sony ISP behavior).
   - **Runtime Mutual Exclusion**: Dynamically toggling `HDMI RAW16` or `S&Q >= 120fps` (`120fps`, `240fps`) smoothly resets `ciz_scale` back to `1.00x` (`CIZ_CLAMPED_BY_MODE_EXCLUSION`) with `0` mailbox stalls, while `S&Q <= 60fps` preserves `CIZ`.
3. **Runtime Assignable Button (`Custom 1..6` + `Lens Hold` + `XLR-H1 Handle` + `Big6` Volatile Shadow) Dispatcher**:
   - Simulates every FX3 physical button (`CUSTOM_1..6`, `LENS_FOCUS_HOLD`, `XLR_H1_HANDLE`) mapped to FX6 Cinema Line actions (`Base ISO 800<->12800`, `Zebra Toggle`, `Peaking Toggle`, `S&Q Toggle`, `Focus Magnifier`, `Status Check`, `Big6 Home`) plus volatile RAM-shadow state updates (`ram://tmp/camset_big6_shadow.json`).
   - Proves attempted triggers of hardware-absent FX6 actions (`ND Preset`, `Auto ND`, `VF Adjust`) return safe `CONTAINED_NO_OP_TOAST` with `null_gpio_derefs == 0`, `bk4_persistent_nvram_writes == 0`, `cp_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity

All 10 compact donor binaries (`613,744 B` total) are verified strictly via `os.O_RDONLY` in Local Donor mode and matched deterministically via pinned SHA-256 contract baselines when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active:

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_lens_comm_so` | FX3 `libInfraLensCommunicator.so` | `14,544` | `InfraLensCommunicator` (`SELP1635G` / PZ control) | `e61bf145f050...` |
| `fx3_global_xdb` | FX3 `global.xdb` | `11,664` | `GPE0`/global DB schema baseline | `55fe6b9f81af...` |
| `fx3_str_en_g_uxc` | FX3 `string_english.g.uxc` | `69,600` | FX3 English UI strings (`Touch Focus` / `Zoom`) | `a4a15a548f7e...` |
| `fx6_lens_comm_so` | FX6 `libInfraLensCommunicator.so` | `14,544` | `InfraLensCommunicator` (FX6 lens contract) | `8848b33084f7...` |
| `fx6_tp_so` | FX6 `libInfraTp.so` | `47,776` | Capacitive Touch Panel (`ABS_MT_POSITION` / TP IPC) | `ea1c123412fc...` |
| `fx6_input_so` | FX6 `libInfraInput.so` | `93,448` | `InfraInput` button/assignable dispatcher | `1851e2dc8515...` |
| `fx6_dial_so` | FX6 `libInfraDial.so` | `31,232` | `InfraDial` / `Big6` volatile input routing | `b2034d6c8537...` |
| `fx6_gpioctrl_so` | FX6 `libul_GpioCtrl.so` | `10,064` | `GpioCtrl` absent-hardware guard markers | `0f88a164acbf...` |
| `fx6_setupfile_so` | FX6 `libInfraSetupFile.so` | `202,664` | `InfraSetupFile` (`Big6` volatile shadow schema) | `b489c64adef1...` |
| `fx6_str_en_uxc` | FX6 `string_english.uxc` | `118,208` | FX6 English UI strings (`Clear Image Zoom`, `Base ISO`) | `5e88dd707cb4...` |

---

## 3. Verification Receipts & Timing

All commands were executed with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` in both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `touch_af_ciz_assignable_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `0.059s` | `73ce6d30f926...` |
| `touch_af_ciz_assignable_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.058s` | `c3f1ffcfb1b7...` |
| `fx3_vm_coemulation_suite.py --summary` (All 11 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.193s` (`< 1.4s`) | `97da91b5e7bc...` |
| `fx3_vm_coemulation_suite.py --summary` (All 11 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.337s` (`< 0.5s`) | `3b9ba748e8f2...` |
| `unittest test_touch_af_ciz_assignable_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `0.973s` | `36 / 36` tests |
| `unittest test_touch_af_ciz_assignable_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.971s` | `36 / 36` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `LOCAL_DONOR_RDONLY` | PASS | `6.462s` | `316 / 316` tests |
| `unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | PASS | `4.767s` | `316 / 316` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | PASS | Verified | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `bk4_persistent_nvram_writes == 0`, `null_gpio_derefs == 0`, `mailbox_stalls == 0`, `physical_device_writes == 0`, `p1_emmc_mutations == 0`, `internal_emmc_writes == 0`.
- `c2pa_license_untouched == True`, `persistent_emmc_writes_authorized == False`, `xavc_recorded_crop_scale == 1.0`, `hdmi_raw16_clean_feed_crop_scale == 1.0`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
