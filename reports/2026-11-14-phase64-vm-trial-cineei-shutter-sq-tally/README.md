# Phase 64 — Cinema Line Cine EI, Shutter Angle/ECS, S&Q (1–240fps), REC Tally & Wired I/O Deck (`outputs/fx3-vm-trial`)

> **Date / 日期**：2026-11-14  
> **Scope / 范围**：`outputs/fx3-vm-trial/src/fx6_live_guest.c` · `outputs/fx3-vm-trial/run_fx6_menu_trial.py` · `outputs/fx3-vm-trial/tests/test_phase64_cine_exposure_deck.py` · `outputs/fx3-vm-trial/README.md`  
> **Status / 状态**：Verified in Local Donor Mode (129/129 unit tests + Isolated Live QEMU Port `18775`) and Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` + `scripts/run_all_lab_tests.py --clean-only`).

---

## 1. Executive Summary / 核心成果摘要

Phase 64 extends the FX6-on-FX3 live console (`outputs/fx3-vm-trial`) with a complete **Cinema Line Exposure, Motion & Wired I/O Control Deck**, while preserving 100% backward compatibility with Phases 19, 23, 30, 40, 49, and 56:

Phase 64 为 `outputs/fx3-vm-trial` 控制台新增完整的 **Cinema Line 曝光、升格/降格与有线 I/O 控制面板**，并 100% 向后兼容 Phase 19/23/30/40/49/56 全部契约与接口：

1. **Host REST API (`GET/POST /api/cine_exposure` & `/api/status`)**：
   - **Dual Base Cine EI & 14.0-Stop Latitude**：Low Base `"800"` (`200..3200 EI`, 13 steps) and High Base `"12800"` (`3200..51200 EI`, 13 steps), computing exact dynamic latitude (`over_stops`, `under_stops`, summing to `14.0` stops centered on `+6.0 / -8.0` at Base ISO, e.g., `400 EI -> +5 / -9`, `1600 EI -> +7 / -7`).
   - **Shutter Angle / Speed / ECS Anti-Flicker**：`"angle"` (`[5.6°, 360.0°]`, presets `180.0°, 172.8°, 90.0°, 45.0°, 360.0°`), `"speed"` (`1/24..1/8000`), and `"ecs"` (`[23.98, 7900.0] Hz`, e.g., `100.2 Hz` LED-wall anti-flicker sync).
   - **S&Q Motion (`1–240fps`) & Audio Mute Invariant**：6 project base frame rates (`23.98, 24.00, 25.00, 29.97, 50.00, 59.94`), `sq_fps` in `1..240`, exact `motion_ratio` (`120 / 23.98 -> 5.00x Slow`, `4 / 24.0 -> 0.17x Quick`), and `audio_rec_muted_by_sq: True` whenever `sq_enabled` is active.
   - **REC State, Live TC & Tally Stealth Control**：`rec_state` (`"STBY"` / `"REC"`) with live `rec_tc_frames` / `rec_tc` progression, plus `tally_lamp_mode` (`"on"`, `"front_only"`, `"rear_only"`, `"off"` Tally Stealth) driving `tally_front_lit` and `tally_rear_lit`.
   - **Wired I/O & Hardware Safety Locks**：`wired_io_mode` (`"off"`, `"usblan_ptpip"` USB `CDC-NCM + PTP-IP 15740`, `"hdmi_raw16"` `4264x2408 16-bit Linear RAW` Atomos EDID + `MLUT` clean-feed) with strict `P12` Airplane-Mode RF-OFF (`wifi_bt_rf_disabled: True`, rejecting `wifi_enabled=True` / `bt_enabled=True` with HTTP `400`) and `P4` Electronic Variable ND hardware-absence lock (`nd_preset="Clear"`, rejecting non-Clear presets with HTTP `400` and incrementing `p4_nd_reject_count`).

2. **In-Guest `GPE0` (`0x41e001000`) Native Cinema Line HUD (`fx6_live_guest.c`)**：
   - Added heap-free `fx6_render_phase64_cine_exposure_overlay(uint64_t appfw, uint32_t page)` driven by extended mailbox words `mb[28..31]` (`0x43494e45` `'CINE'` magic) and logged via `CINE_EXP=0x%08x:0x%08x:%u` in guest serial output.
   - Renders 5 live HUD badges onto physical `GPE0` (`0x41e001000`): `REC MM:SS:FF` / `STBY` + Front/Rear Tally dots, `<EI>EI (B800|B12800 +over/-under)`, Shutter/ECS badge, `S&Q <fps>fps (<ratio>x) [CH1-4 MUTE]` (or `[P4:ND-CLR]`), and `[HDMI RAW16 4.2K]` / `[LAN PTP-IP P12-SAFE]`.

3. **CAMSET Round-Trip (`/api/camset_export` & `/api/camset_import`) & Bilingual Web Console**：
   - Extended `fx6_on_fx3_camset_v1` CAMSET export/import (both `/api/camset_*` and `/api/preset_*` routes) to persist and restore `cine_exposure` while remaining 100% compatible with legacy CAMSET JSON lacking `cine_exposure`, failing closed on malformed fields, and clamping any P4/P12 tamper attempts.
   - Added the compact Cinema-Line styled **Phase 64 control deck** (`#phase64-cine-exposure-card`) with `EN / 简体中文 / 繁體中文 / 日本語` cues, quick preset pills, and instant `GPE0` frame refresh.

---

## 2. Verification Receipts / 验证实测记录

### 2.1 Dual-Mode Unit & HTTP Integration Tests (`129/129` PASS)
| Suite / Check Mode | Command | Result |
|---|---|---|
| Local Donor Mode (`outputs/fx3-vm-trial/tests`) | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -v` | **`Ran 129 tests — OK` (0 skipped)** (103 existing + 26 new Phase 64 tests; includes ARM64 `zig` compile of `fx6_live_guest.c`) |
| Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -v` | **`Ran 129 tests — OK` (1 expected skip: `zig`)** |

### 2.2 Isolated Live QEMU Verification (`--port 18775`, `--workdir /private/tmp/fx6-phase64-18775`)
- **Live Port `8768` (`PID 65517`) Protection**：Verified `PID 65517` alive before and after the run (`True` -> `True`); zero global kills used; temporary `--workdir /private/tmp/fx6-phase64-18775` removed cleanly after stopping PID on `18775`.
- **Guest Boot & Readiness**：`live_ready=True` in `41.36s` (`page=0`, `nz=364007`).
- **Live `REC` + `1600 EI` + `ECS 100.2Hz` + `S&Q 120fps` + `HDMI RAW16` GPE0 Delta**：
  - `POST /api/cine_exposure`: `ok=True`, `wrote_mailbox=True`, `guest_synced=True`
  - `cine_exp_cmd`: `CINE_EXP base=800 ei=1600 lat=+7/-7 shutter=ecs:100.20Hz sq=1:23.98:120 rec=REC tally=on io=hdmi_raw16 nd=Clear p12=1`
  - **`GPE0` (`0x41e001000`) `STBY -> REC` Pixel Diff**：**`23,926` changed pixels** (`71,844` diff bytes out of `552,960` total pixels / `2,211,840` bytes).
  - **Guest `serial.log` Receipt**：`4` `CINE_EXP=` frames logged (latest: `FX6_LIVE_FRAME seq=5 page=0 ... nz=363993 ... CINE_EXP=0x800378d2:0x07802724:2`).
- **USB-LAN PTP-IP + Tally Stealth + Fail-Closed 400 + CAMSET Round-Trip**：
  - `usblan_ptpip` + `tally_lamp_mode="off"` -> `ptpip_port=15740`, `usb_class="CDC-NCM"`, `wifi_off=True`, `bt_off=True`, `tally_front_lit=False`.
  - `nd_preset="1/16 ND"` -> HTTP `400` `p4_nd_hardware_absent`; `wifi_enabled=True` -> HTTP `400` `p12_airplane_mode_locked`.
  - `/api/camset_export` -> reset -> `/api/camset_import` restored `wired_io_mode="usblan_ptpip"`, `sq_fps=120` with `guest_synced=True` (`sha256` prefix `cb16710f38fcac62`).

---

## 3. Workspace Ownership & Hygiene Checklist / 目录归属与洁净规范

- Only modified/created files inside the assigned Phase 64 scope:
  - `outputs/fx3-vm-trial/src/fx6_live_guest.c`
  - `outputs/fx3-vm-trial/run_fx6_menu_trial.py`
  - `outputs/fx3-vm-trial/README.md`
  - `outputs/fx3-vm-trial/tests/test_phase64_cine_exposure_deck.py`
  - `reports/2026-11-14-phase64-vm-trial-cineei-shutter-sq-tally/README.md`
- `persistent_emmc_writes_authorized = False` untouched; zero proprietary binaries, keys, `.so`, `.cpio`, `.png`, or `__pycache__` committed.
