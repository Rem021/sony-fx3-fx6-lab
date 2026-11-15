# Phase 81 — Interactive Click-to-Track 627-pt PDAF Reticle, `Focus Magnifier x4.0`, `S-Log3` False Color / EL-Zone & `Clear Image Zoom` (`outputs/fx3-vm-trial`)

> **Date / 日期**：2026-11-14  
> **Scope / 范围**：`outputs/fx3-vm-trial/src/fx6_live_guest.c` · `outputs/fx3-vm-trial/run_fx6_menu_trial.py` · `outputs/fx3-vm-trial/tests/test_phase81_touchaf_falsecolor_ciz.py` · `outputs/fx3-vm-trial/README.md`  
> **Status / 状态**：Verified in Local Donor Mode (`183/183` unit tests + Isolated Live QEMU Port `18777`) and Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` + `scripts/run_all_lab_tests.py --clean-only`).

---

## 1. Executive Summary / 核心成果摘要

Phase 81 extends `outputs/fx3-vm-trial` with an interactive Cinema Line **Click-to-Track 627-pt PDAF Reticle, `Focus Magnifier x4.0`, `S-Log3` False Color / EL-Zone & `Clear Image Zoom` (`CIZ`)** subsystem, maintaining 100% backward compatibility across Phases 19–73 (`155/155` prior tests + `28` new Phase 81 tests = `183/183`):

1. **Host REST API (`GET/POST /api/touch_focus_ciz` & `/api/status`) & Mutual-Exclusion Coupling**：
   - **Touch Tracking AF (`touch_af_mode`, `touch_x`, `touch_y`)**：
     - Supports `off`, `touch_focus`, and `touch_tracking` (`Real-time Tracking AF`).
     - Maps `(touch_x: 0..959, touch_y: 0..539)` deterministically onto the `IMX510` `33 × 19 = 627`-pt PDAF grid (`pdaf_col: 0..32`, `pdaf_row: 0..18`, `pdaf_index: 0..626`).
     - Applies **anamorphic desqueeze / aspect-guide letterbox awareness**: when `assist_tools.desqueeze` is `1.3x` / `1.33x` (`y: 68..471`) or `2.0x` (`y: 135..404`) or `assist_tools.aspect_marker` adds matte bars (`2.39:1`, `1.85:1`, `9:16`), clicks outside the active sensor image area return `letterbox_ignored: True` without moving the prior AF target.
   - **`Focus Magnifier` (`focus_mag`: `"1.0x"`, `"2.0x"`, `"4.0x"`)**：
     - Centers live preview ROI on `(touch_x, touch_y)` (clamped within `960×540`) while enforcing `clean_hdmi_unmagnified: True` (recorded stream and HDMI clean feed remain `1.0x`).
   - **`S-Log3` False Color / EL-Zone (`false_color_mode`: `"off"`, `"slog3_ire"`, `"el_zone"`)**：
     - Exposes exact Sony `S-Log3` IRE landmark bands (`3.5%` black clip purple, `41.0%` `18%` middle-grey green, `52.0%` `+1EV` skin pink, `94.0%` sensor clip red) plus 7 `EL_ZONE_STOPS` (`-5EV`..`+5EV+`).
     - Couples dynamically with Phase 56/73: sets `slog3_zebra100_clip_warning: True` with a bilingual warning banner whenever `color_and_media.base_look` begins with `"S-Log3"` and `assist_tools.zebra_mode == "100%"` (since S-Log3 clips at `94%` IRE).
   - **`Clear Image Zoom` (`ciz_scale`: `1.00..2.00`, `ciz_res_mode`: `"4K"`/`"FHD"`, `zoom_rocker_speed`: `1..8`)**：
     - Enforces `4K` ceiling `1.50x` and `FHD` ceiling `2.00x`.
     - Automatically couples with Phase 64: whenever `cine_exposure.wired_io_mode == "hdmi_raw16"` OR (`cine_exposure.sq_enabled` and `cine_exposure.sq_fps >= 120`), clamps `effective_ciz_scale = 1.00` (`ciz_clamped_by_exclusion = True`) with a bilingual hardware exclusion reason.
   - Fails closed on invalid/out-of-range/non-object/malformed JSON inputs with HTTP `400` JSON (`{"ok": false, "error": "..."}`).

2. **In-Guest `GPE0` (`0x41e001000`) Native Rendering (`fx6_live_guest.c`)**：
   - Passes Phase 81 state via extended mailbox words `mb[36..39]` (`0x54414643` `'TAFC'` magic) to heap-free `fx6_render_phase81_touchaf_falsecolor_ciz_overlay()`.
   - Renders crisp Cinema Line **Touch Tracking AF double-frame reticle (`[ ⌜ ⌝ ]`)** at `(touch_x, touch_y)` (`#22C55E` bright green in `touch_tracking`, `#F8FAFC` white in `touch_focus`) with PDAF cell/index badge, **`S-Log3` False Color / EL-Zone colorized IRE band overlay + right-side IRE/EV legend bar**, **`[MAG x4.0] HDMI:1x`** orange border & badge, **`[CIZ]`** zoom bar badge, and `ZEB100% CLIP@94%` warning indicator.
   - Logged via `FX6_LIVE_FRAME ... TAFC=0x%08x:0x%08x:0x%08x` and hashed cleanly into `fx6_state_hash()`.

3. **Click-on-Canvas Web UI + CAMSET Round-Trip (`简体中文 / English`)**：
   - Extended `/api/camset_export` and `/api/camset_import` to persist `touch_focus_ciz` (100% backward-compatible with older CAMSET JSON; fail-closed on invalid `touch_focus_ciz`).
   - Added bilingual `#phase81-touchaf-ciz-card` (**触控跟焦 627点 PDAF / S-Log3 伪色曝光 / 超解析变焦 CIZ**) plus interactive **🎯 点击画面触控对焦 (Click-Canvas-to-Focus)** toggle and `#p81-canvas-reticle` HUD overlay on the live `960×540` preview canvas.

---

## 2. Verification Receipts / 验证实测记录

### 2.1 Dual-Mode Unit & HTTP Integration Tests (`183/183` PASS)
| Suite / Check Mode | Command | Result |
|---|---|---|
| Phase 81 Suite (`test_phase81_touchaf_falsecolor_ciz.py`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_phase81*.py"` | **`Ran 28 tests — OK` (0.349s)** |
| Local Donor Mode (Full `outputs/fx3-vm-trial/tests`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"` | **`Ran 183 tests — OK` (0 skipped, 6.158s)** |
| Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"` | **`Ran 183 tests — OK` (2 expected skips: donor/zig, 5.668s)** |
| Repo Clean-Room Hygiene Audit | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **`CLEAN (ALL GREEN)`** |

### 2.2 Isolated Live QEMU Verification (`--port 18777`, `--workdir /private/tmp/fx6-phase81-18777`)
- **Live Port `8768` (`PID 21491`) Protection**：Verified `PID 21491` `LIVE_GPE0_READY` both before and after the isolated `18777` test run; zero `pkill`/`killall` calls used; spawned child `PID 32395` on port `18777` cleanly terminated and `/private/tmp/fx6-phase81-18777` removed.
- **Guest Boot & Readiness**：`LIVE_GPE0_READY` in `72.8s` (`ack_seq=1`, `gpe0_nonzero_px=389799`).
- **Baseline `GPE0` (`off`)**：`2,211,840` bytes (`552,960` ARGB8888 pixels), `sha256=e02c9751ea787ee4500a6de9de7d630b9d8a7efa635a241d97038fa0e60fbec2`, `nonzero_px=389,436`.
- **`touch_tracking@(640,260)` + `slog3_ire` False Color + `CIZ 1.40x` (`4K`, speed `5`) `GPE0` Pixel Delta**：
  - `POST /api/touch_focus_ciz` -> `ok=True`, `guest_synced=True`, `ack_seq=2`.
  - Updated `GPE0`: `sha256=3b785f65a75eb9b92941ca06ce728f5c8b485ad02945112639c4d91cec10e523`, `nonzero_px=416,467`.
  - **Measured Delta vs Baseline**：**`312,372` changed pixels (`962,395` differing bytes)**!
- **`Focus Magnifier x4.0` + `EL-Zone` Switch Delta**：
  - `POST /api/touch_focus_ciz {"focus_mag": "4.0x", "false_color_mode": "el_zone"}` -> `guest_synced=True`, `ack_seq=3`, `sha256=961500fc8c822bf01f56f487507e835c33559ff36901d23c83bf52bf3f8e5091`, **`295,508` changed pixels** vs `slog3_ire`.
- **`HDMI RAW16` Mutual-Exclusion Clamp & `2.39:1` Letterbox Rejection**：
  - `POST /api/cine_exposure {"wired_io_mode": "hdmi_raw16"}` clamped `effective_ciz_scale = 1.00` (`ciz_clamped_by_exclusion = True`).
  - Under `aspect_marker = "2.39:1"`, `POST /api/touch_focus_ciz {"touch_x": 300, "touch_y": 12}` returned `letterbox_ignored = True` and kept AF locked at `(640, 260)`.
- **Guest Serial Log**：`5` `TAFC=` frames emitted (`0` `APPFW_SEGV`; final `FX6_LIVE_FRAME seq=6 ... nz=468658 text_ok=51 fill=38 icon=6 ... TAFC=0x4fd04a02:0x8c64d256:0x80000125`).

---

## 3. Workspace Ownership & Hygiene Checklist / 目录归属与洁净规范

- Strictly modified/created only the 5 owned Phase 81 files:
  - `outputs/fx3-vm-trial/src/fx6_live_guest.c`
  - `outputs/fx3-vm-trial/run_fx6_menu_trial.py`
  - `outputs/fx3-vm-trial/README.md`
  - `outputs/fx3-vm-trial/tests/test_phase81_touchaf_falsecolor_ciz.py`
  - `reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md`
- `persistent_emmc_writes_authorized = False` preserved; zero `.so`, `.elf`, `.ko`, `.cpio`, `.bin`, `.o`, `.pyc`, `__pycache__`, or `.png` artifacts tracked or left untracked.
