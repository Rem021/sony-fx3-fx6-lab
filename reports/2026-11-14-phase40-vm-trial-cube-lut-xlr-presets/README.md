# Phase 40 — Interactive `.cube` 3D LUT Live Import & Sanitizer, 4-Ch `XLR-H1` Audio VU Meter & `CAMSET` Scene Presets (`--port 18772`)

- **Date**: 2026-11-14
- **Lane / Worker**: Hydrogen-32 (`h32-phase40-vm-trial-lut-upload-xlr-presets`)
- **Isolated Verification Port**: `127.0.0.1:18772` (port-scoped workdir `/private/tmp/fx6-live-gpe0-run-18772`, PID `73536`; live user session PID `31304` on port `8768` untouched)
- **Live QEMU Kernel/Guest**: `LIVE_GPE0_READY` in `44.8s` (`nz=357888`), rebuilt from `outputs/fx3-vm-trial/src/fx6_live_guest.c` via AArch64 Zig 0.17.0 without mutating donor archives (`O_RDONLY`).

## Summary of Implemented Deliverables

1. **Anti-Crash `.cube` 3D LUT Live Import & `GPE0` Swatch Strip (`GET/POST /api/lut_upload`)**
   - Supports JSON `{"slot": "User1".."User4", "name": "...", "cube_text": "..."}` as well as built-in presets (`709_typeA`, `teal_orange`, `film_2383`, `slog3_bypass`).
   - Fail-closed pre-guest validation (`validate_and_sanitize_cube_lut`): enforces `LUT_3D_SIZE` (`17` or `33` by default; `2` permitted only when `allow_mini_grid=True`), exact `N^3` RGB triplets, rejects `LUT_1D_SIZE`, `NaN`/`Inf`, `DOMAIN_MIN >= DOMAIN_MAX`, header-after-data, control characters, path-traversal names, and malformed JSON with HTTP `400` + structured error code before touching guest state (`libmpr.so::SetLutData` crash guard).
   - Computes canonical `sha256` and trilinear `(0.5, 0.5, 0.5)` mid-gray RGB tint preview, packs `mb[19..25]` (slot metadata, tint swatch RGB, 24-byte ASCII name), and renders the live swatch + User LUT name into `GPE0` (`0x41e001000`) via `fx6_render_phase40_hud_strip()` in `outputs/fx3-vm-trial/src/fx6_live_guest.c`.

2. **4-Ch `XLR-H1` MI-Shoe Audio Controls + `RTMD 0xE304` Telemetry (`POST /api/cinema_param`)**
   - Added `ch1_db..ch4_db` (`[-60..+12]` dB clamp, bool/NaN rejected), `xlr_phantom_48v`, `xlr_handle_attached`, and `rtmd_0xe304_ibis_lock` (`ACTIVE_5AXIS`, `OFF_CENTER_LOCKED`, `STANDARD`) synced bidirectionally with `ibis` / `xlr` Cinema Line parameters and `stage_b_telemetry["P11"]`.
   - When `xlr_handle_attached == False`, gracefully auto-falls back `CH1/CH2` to `Internal Stereo` per `P11` `0x91db059b` contract without crashing, updating `mb[26..27]` and the `GPE0` VU/route strip.
   - Extended `HTML_UI` in `outputs/fx3-vm-trial/run_fx6_menu_trial.py` with live 4-Ch audio trim sliders + VU bars, XLR attach/+48V toggles, `RTMD 0xE304` selector, `.cube` file/text/preset uploader with tint swatch, and `CAMSET` export/import/P4-tamper bar while preserving all Phase 19/23/30 endpoints and UI elements.

3. **`CAMSET` Scene File Preset Export & Import (`GET /api/preset_export`, `POST /api/preset_import`)**
   - Deterministic `fx6_on_fx3_camset_v1` JSON snapshot with canonical sorted `preset_sha256`.
   - Import validates schema, Cinema Line choices, audio/RTMD values, and any embedded `.cube` payloads before applying state, strictly enforcing `P4` ND-Clear Hardware Lock (clamping any optical/electronic ND attempt to `Clear [FX3 P4 Locked]` and incrementing `p4_nd_reject_count`) and preserving `P12` `BK4` Airplane-Mode shadow lock.

## Isolated Live QEMU Stress Verification (`--port 18772`)

- **Total stress commands executed**: `18` (`0` failed, `crashed=false`, final `ack_seq == cmd_seq == 15`, `gpe0_nonzero_px=333680`).
- **Multilingual cycle**: `zh` (`seq=2`) -> `ja` (`seq=3`) -> `en` (`seq=4`), all `nz=357888`, `0` crashes.
- **`.cube` `17^3` live uploads & real `GPE0` pixel diffs**:
  - `User1` (`teal_orange`, `TealOrange17`, `sha256=b440cb2a8b2069eb06a28971edec59315047116856a0dc3b6dfb24377e6baff4`, tint `#af8673`): **`9,129` changed framebuffer bytes** vs S-Cinetone baseline.
  - `User2` (raw `17^3` `film_2383`, `Kodak2383_17`, `sha256=34cf6a4a9f68cd5c6ad0adb0e0c8eef8ba9d37884a71866c71b09c2b63d708c0`, tint `#62aa95`): **`6,153` changed framebuffer bytes** vs `User1`.
- **Fail-closed malformed `.cube` & JSON rejections (HTTP `400`, `0` crashes)**:
  - `nan_triplet` -> HTTP `400` (`nan_or_inf_triplet`)
  - `wrong_count` -> HTTP `400` (`triplet_count_mismatch`)
  - `lut_1d` -> HTTP `400` (`unsupported_lut_1d_size`)
  - `bad_json` -> HTTP `400` (`invalid_json`)
- **`XLR-H1` detach & `CAMSET` P4/P12 tamper verification**:
  - Detached `XLR-H1` with trims `[-6, -9, -24, -30]` -> `audio_route=INTERNAL_STEREO_FALLBACK` (`0x91db059b`), `rtmd_0xe304_ibis_lock=OFF_CENTER_LOCKED`.
  - Exported `CAMSET` (`preset_sha256=b5d5aeaf8ea0e7dc21f0392c859b65f771419adb268e3a9d34b8e3a607940c09`), mutated live state, tampered `cinema_params.nd="1/16 ND"` & `p12_bk4_airplane_mode_locked=false`, then imported: `p4_nd_rejected=True`, `p4_nd_reject_count=1`, `nd="Clear [FX3 P4 Locked]"`, `p12_bk4_airplane_mode_locked=True`, and prior LUT/audio/RTMD state restored.

## Captured `GPE0` (`1024x540`) PNG Receipts (`< 90 KiB` each)

| Receipt PNG | Dimensions | Size (Bytes) | Captured State |
|---|---:|---:|---|
| [p40_receipt_1_cube_user1_big6.png](p40_receipt_1_cube_user1_big6.png) | `1024x540` | `25,695` | Page 0 Big-6 Home with `User1` `TealOrange17` (`#af8673`) swatch + LUT HUD strip |
| [p40_receipt_2_hud_xlr_fallback_rtmd.png](p40_receipt_2_hud_xlr_fallback_rtmd.png) | `1024x540` | `63,157` | Page 16 HUD with `User2` `Kodak2383_17` (`#62aa95`), `INT-ST` (`0x91db059b` fallback), `E304:LOCK`, `BK4:LOCK` |
| [p40_receipt_3_tc_audio_xlr48v_user4.png](p40_receipt_3_tc_audio_xlr48v_user4.png) | `1024x540` | `13,783` | Page 17 TC/Audio Meter with `XLR-H1` re-attached `+48V`, `E304:5AX`, and `User4` `Rec709_TypeA` |

## Dual-Mode Automated Tests

- `outputs/fx3-vm-trial/tests/test_vm_trial.py` expanded from 37 to **59 tests** (`22` new `TestPhase40CubeLutXlrAudioAndCamset` tests).
- Verified passing (`59/59 OK`) in both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode via `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm-trial/tests/test_vm_trial.py -v`.
