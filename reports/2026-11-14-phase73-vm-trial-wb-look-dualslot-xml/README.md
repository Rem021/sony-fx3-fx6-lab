# Phase 73 — Live White Balance (`Shockless WB` / Kelvin / Tint), Base Look (`S-Cinetone` / `S-Log3`), Dual-Slot `CamID/Reel` & One-Click `NonRealTimeMeta M01.XML` Sidecar Export (`outputs/fx3-vm-trial`)

> **Date / 日期**：2026-11-14  
> **Scope / 范围**：`outputs/fx3-vm-trial/src/fx6_live_guest.c` · `outputs/fx3-vm-trial/run_fx6_menu_trial.py` · `outputs/fx3-vm-trial/tests/test_phase73_wb_look_dualslot_xml.py` · `outputs/fx3-vm-trial/README.md`  
> **Status / 状态**：Verified in Local Donor Mode (`155/155` unit tests + Isolated Live QEMU Port `18776`) and Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` + `scripts/run_all_lab_tests.py --clean-only`).

---

## 1. Executive Summary / 核心成果摘要

Phase 73 extends `outputs/fx3-vm-trial` with a Cinema Line **Live White Balance, Base Look, Dual-Slot Media Naming & Resolve `NonRealTimeMeta M01.XML` Export** subsystem, preserving 100% backward compatibility with Phases 19–64 (`129/129` existing tests pass unchanged + `26` new Phase 73 tests):

1. **Host REST API (`GET/POST /api/color_and_media`, `GET /api/xml_sidecar` & `/api/status`)**：
   - **White Balance (`wb_mode`, `kelvin`, `tint_gm`, `shockless_wb`)**：
     - Supports `preset_3200k`, `preset_4300k`, `preset_5600k`, `mem_a`, `mem_b`, and `atw` (`fx3_wb_switch_soft_mapped: True`, reflecting the absence of a physical `B/A/PRST` toggle switch on `ILME-FX3`).
     - Presets lock `kelvin` (`3200` / `4300` / `5600`), while `mem_a` / `mem_b` / `atw` allow `[2000, 15000]` Kelvin snapped cleanly to `50K` increments; `tint_gm` supports `[-99, +99]` `CC MG/GR` green-magenta tint; `shockless_wb` supports `off`, `1`, `2`, `3`.
   - **Base Look / NLE Color Pipeline (`base_look`)**：
     - Supports `S-Cinetone`, `S-Log3 / S-Gamut3.Cine`, `S-Log3 / S-Gamut3`, `ITU709`, `709(800%)`, `HLG Live`, and `User 3D LUT` (linking seamlessly to active `.cube` LUTs in `User1..User4`), deriving exact `capture_gamma_equation` & `capture_color_primaries`.
   - **Cinema Line Clip Naming, Dual-Slot Modes & S&Q Proxy Coupling**：
     - Validates `cam_id` (`A..Z`), `reel_num` (`1..999`), `cam_pos` (`C|L|R`), `clip_seq` (`1..999`) to synthesize live main/proxy/sidecar names (e.g., `B004C012_261114_FX3B.MP4`, `B004C012_261114_FX3BS03.MP4`, `B004C012_261114_FX3BM01.XML`), `dual_slot_mode` (`simul`, `relay`, `sort_main_proxy`, `single_slot_a`), and `proxy_mode` (`xavc_hs_1080p_16m`, `xavc_hs_1080p_9m`, `xavc_s_720p_6m`, `off`).
     - Couples directly with Phase 64: whenever `cine_exposure.sq_enabled == True`, reports `proxy_effective_active = False` and `proxy_auto_suspended_by_sq = True`.
   - **One-Click `GET /api/xml_sidecar` (`*M01.XML`)**：
     - Serves deterministic Sony `urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20` XML (`Content-Type: application/xml; charset=utf-8` download or JSON wrapper via `?format=json`) containing live `Cine EI` (`ei_index` / `BaseISO`), `base_look` (`CaptureGammaEquation` / `CaptureColorPrimaries`), `WhiteBalance`, `Shutter/S&Q`, active `.cube` LUT metadata, and `ILME-FX3` Stage-B volatile RAM provenance (`c2pa_spoofed = False`, `persistent_emmc_writes_authorized = False`).
     - Invalid inputs fail closed with HTTP `400` JSON (`{"ok": false, "error": "..."}`).

2. **In-Guest `GPE0` (`0x41e001000`) Native HUD Telemetry (`fx6_live_guest.c`)**：
   - Added heap-free `fx6_render_phase73_wb_look_dualslot_overlay()` driven by extended mailbox words `mb[32..35]` (`0x57424c4d` `'WBLM'` magic) and hashed into `fx6_state_hash()`.
   - Renders Cinema Line White Balance + Base Look pill (e.g., `5600K+0 S-Cinetone` / `3200K-5 S-Log3.Cine`) and Dual-Slot + Clip ID + Proxy status pill (e.g., `[A+B SIMUL] A001C001 PRX` / `[A->B RELAY] B004C012 PRX:OFF(S&Q)`), logging `WB_MEDIA=0x%08x:0x%08x:0x%08x` to guest serial output.

3. **CAMSET Round-Trip & Bilingual Web Console Card**：
   - Extended `/api/camset_export` and `/api/camset_import` (100% backward-compatible with older CAMSET payloads; fail-closed validation on invalid `color_and_media`).
   - Added bilingual Cinema-Line Web UI card `#phase73-color-media-card` (**色彩白平衡 / 双卡槽场记命名 & 达芬奇 M01.XML 导出**) with one-click `M01.XML` download and live XML preview.

---

## 2. Verification Receipts / 验证实测记录

### 2.1 Dual-Mode Unit & HTTP Integration Tests (`155/155` PASS)
| Suite / Check Mode | Command | Result |
|---|---|---|
| Local Donor Mode (`outputs/fx3-vm-trial/tests`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -v` | **`Ran 155 tests — OK` (0 skipped)** (129 existing + 26 new Phase 73 tests; includes ARM64 `zig` compile of `fx6_live_guest.c`) |
| Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -v` | **`Ran 155 tests — OK` (2 expected skips: `zig`)** |
| Repo Clean-Room Hygiene Audit | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **`CLEAN (ALL GREEN)`** |

### 2.2 Isolated Live QEMU Verification (`--port 18776`, `--workdir /private/tmp/fx6-phase73-18776`)
- **Live Port `8768` (`PID 18787`) Protection**：Verified `PID 18787` alive before and after the run; zero global kills used; spawned child on `18776` cleanly stopped and `/private/tmp/fx6-phase73-18776` deleted (`CLEANED_18776_WORKDIR: True`).
- **Guest Boot & Readiness**：`live_ready=True` in `58.83s` (`ack_seq=1`).
- **`3200K-5 S-Log3 / S-Gamut3.Cine + B004C012 RELAY` `GPE0` Pixel Diff**：
  - `POST /api/color_and_media` -> `ok=True`, `wrote_mailbox=True`, `guest_synced=True`, `crashed=False`, `ack_seq=2`.
  - **`GPE0` (`0x41e001000`) Pixel Delta vs Default (`5600K S-Cinetone A001C001 SIMUL`)**：**`27,578` changed pixels** (`81,728` diff bytes out of `552,960` total pixels / `2,211,840` bytes).
- **S&Q `120fps` Proxy Auto-Suspend Coupling (`PRX:OFF(S&Q)`) `GPE0` Pixel Diff**：
  - `POST /api/cine_exposure {"sq_enabled": true, "base_fps": 23.98, "sq_fps": 120}` -> `proxy_auto_suspended_by_sq=True`, `proxy_effective_active=False`, `wrote_mailbox=True`, `guest_synced=True`, `ack_seq=3`.
  - **`GPE0` Pixel Delta (`PRX` active vs `PRX:OFF(S&Q)`)**：**`21,498` changed pixels** (`64,492` diff bytes).
- **Live `M01.XML` Sidecar, Fail-Closed `400`, CAMSET & Guest Serial Receipts**：
  - `GET /api/xml_sidecar`: `B004C012_261114_FX3BM01.XML`, `Content-Type: application/xml; charset=utf-8`, `c2pa_spoofed=False`, `sha256=5df0d960ed82220b236aebee2e98d0d2fbc71d926fb66f77620eae9a2ba7edec`, valid `NonRealTimeMeta v2.20` XML root.
  - `POST /api/color_and_media {"kelvin": 1500, "wb_mode": "mem_a"}` -> HTTP `400` `invalid_kelvin`.
  - `/api/camset_export` -> reset -> `/api/camset_import` restored `B004C012` / `3200K-5` / `S-Log3 / S-Gamut3.Cine` with `guest_synced=True`.
  - Guest `serial.log`: `4` `WB_MEDIA=` frames logged (`seq=2..5`, `WB_MEDIA=0xccbc6400:0xa8180081:0x00000000`, `WB_MEDIA=0xccbc6400:0x28180081:0x00000001`).

---

## 3. Workspace Ownership & Hygiene Checklist / 目录归属与洁净规范

- Strictly modified/created only the 5 assigned Phase 73 files:
  - `outputs/fx3-vm-trial/src/fx6_live_guest.c`
  - `outputs/fx3-vm-trial/run_fx6_menu_trial.py`
  - `outputs/fx3-vm-trial/README.md`
  - `outputs/fx3-vm-trial/tests/test_phase73_wb_look_dualslot_xml.py`
  - `reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md`
- `persistent_emmc_writes_authorized = False` untouched; zero proprietary binaries, keys, `.so`, `.cpio`, `.png`, `.pyc`, or `__pycache__` committed.
