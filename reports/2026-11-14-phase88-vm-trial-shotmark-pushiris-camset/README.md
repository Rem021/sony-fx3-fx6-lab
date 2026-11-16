# Phase 88 — Live `ShotMark1/2` (`<EssenceMark>` in `M01.XML`), `Push Auto Iris` (`1/8`-Stop `41% IRE`) & `ILME-FX6`-to-`ILME-FX3` Fleet `CAMSET` Sanitizer (`outputs/fx3-vm-trial`)

> **Date / 日期**：2026-11-14  
> **Scope / 范围**：`outputs/fx3-vm-trial/src/fx6_live_guest.c` · `outputs/fx3-vm-trial/run_fx6_menu_trial.py` · `outputs/fx3-vm-trial/tests/test_phase88_shotmark_pushiris_camset.py` · `outputs/fx3-vm-trial/README.md` · `reports/2026-11-14-phase88-vm-trial-shotmark-pushiris-camset/README.md`  
> **Status / 状态**：Verified in Local Donor Mode (`211/211` unit tests + Isolated Live QEMU Port `18778`) and Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` + `scripts/run_all_lab_tests.py --clean-only`).

---

## 1. Executive Summary / 核心成果摘要

Phase 88 extends `outputs/fx3-vm-trial` with a production Cinema Line **Live `ShotMark1/2` (`<EssenceMark>` in `M01.XML`), `Cine EI` `Push Auto Iris` (`1/8`-Stop `41% IRE`), 4-Ch `24-bit` `-20 dB` Safety-Track Pad, `SMPTE 12M` `User-Bits`, & A-Cam `ILME-FX6` -> B-Cam `ILME-FX3` Fleet `CAMSET` Sanitizer** subsystem while preserving 100% backward compatibility across Phases 19–81 (`183/183` prior tests + `28` new Phase 88 tests = `211/211`):

1. **Host REST API (`GET/POST /api/shotmark_and_iris` + `<EssenceMark>` in `GET /api/xml_sidecar`)**：
   - **Live `ShotMark1` (`OK`) & `ShotMark2` (`KEEP`) Frame Marker Deck**：
     - Supports `add_shotmark1`, `add_shotmark2`, `clear_shotmarks`, and full `shotmarks` list assignment `[{"type": "ShotMark1"|"ShotMark2", "frame": int, "tc": "HH:MM:SS:FF", "label": "OK"|"KEEP"}]`.
     - Deduplicates cleanly by `(type, frame)` and enforces a `64`-mark ceiling per clip.
     - Automatically injects `<KlvPacketTable>` / `<EssenceMark name="_ShotMark1|_ShotMark2" start="<frame>" tc="..." value="OK|KEEP" />` into `GET /api/xml_sidecar` (`urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20`) ready for DaVinci Resolve / Catalyst Browse ingest.
   - **`Cine EI` `Push Auto Iris` (`1/8`-Stop `1.4..22.0`) & Photometry Mode (`multi` / `center` / `spot` / `highlight`)**：
     - Computes quantized E-Mount `1/8`-stop `iris_fstop` from `scene_ev` (`0.0..18.0`), active Phase 64 `EI` & shutter angle/speed, and `ae_shift_ev` (`-2.0..+2.0`) so `18%` middle grey lands on **`41.0% IRE`** in `S-Log3` (or stops down to keep specular highlights **`< 94.0% IRE`** in `"highlight"` metering mode), always reporting `p4_nd_motor_faults: 0` and `target_ire: 41.0`.
   - **4-Ch `24-bit` Safety-Track Audio Pad (`ch34_safety_pad_db`: `0` | `-20`) & `SMPTE 12M` `User-Bits`**：
     - Applies `-20 dB` attenuation across CH3/CH4 (`ch3_effective_db`, `ch4_effective_db`) for clipped-dialog protection.
     - Auto-packs `User-Bits` from Phase 73 `cam_id` + `reel_num` + `clip_seq` (e.g., `A0:01:00:01`) when `user_bits_hex == "auto_camid_reel"` or accepts explicit `AA:BB:CC:DD` hex input.
   - Fails closed with HTTP `400` JSON on invalid actions, non-integer/bool inputs, out-of-range f-stops/EV shifts, or malformed JSON.

2. **A-Cam `ILME-FX6` -> B-Cam `ILME-FX3` Fleet `CAMSET` Sanitizer (`POST /api/camset_import`)**：
   - Detects A-Cam `ILME-FX6` fleet profiles (`source_model == "ILME-FX6"`, `sanitize_fx6_fleet == True`, or FX6-specific keys such as `fx6_nd_preset`, `sdi_12g_out`, `wifi_ap_enabled`, `vf_peaking`, `nd_auto_mode`, `timecode_bnc_in`, `genlock_in`).
   - Scrubs and clamps FX6 hardware-only settings cleanly onto `ILME-FX3` (`nd_preset -> "Clear"`, `sdi_out -> "CONTAINED_DISABLED"`, `wifi_bt_rf_disabled -> True`, `P4` ND Lock & `P12` `BK4` Airplane Mode Lock preserved with `p4_nd_motor_faults: 0`) and returns `sanitized_fx6_fields: [...]` in the JSON receipt.
   - Preserves 100% of existing strict validation (`invalid_camset_schema`, `p4_nd_reject_count` increment) whenever non-fleet strict import is used.

3. **In-Guest `GPE0` (`0x41e001000`) Native HUD Badges (`fx6_live_guest.c`) & Bilingual Web UI**：
   - Passes Phase 88 state via mailbox words `mb[40..43]` (`0x534d524b` `'SMRK'` magic) to heap-free `fx6_render_phase88_shotmark_iris_overlay()`.
   - Renders Cinema Line HUD badges onto `GPE0`:
     - Gold **`[★M1 / ★M2]`** ShotMark pill & counts when `shotmark_count > 0`,
     - **`[F.. AUTO-IRIS 41%IRE]`** / metering pill (`[MULTI]` / `[CTR]` / `[SPOT]` / `[HI-LIGHT]`) + **`[CH3/4 -20dB SAFE]`** safety-track pill.
   - Logged via `FX6_LIVE_FRAME ... SMRK=0x%08x:0x%08x:0x%08x` and included in `fx6_state_hash()`.
   - Added bilingual Cinema-Line styled card `#phase88-shotmark-iris-card` (**场记打点 ShotMark1/2 / 一键自动光圈 41%IRE / FX6->FX3 多机位配置克隆 (ShotMark, Push Auto Iris & Fleet CAMSET)**) and one-click `Import FX6 Fleet Preset` control to the Web UI.

---

## 2. Verification Receipts / 验证实测记录

### 2.1 Dual-Mode Unit & HTTP Integration Tests (`211/211` PASS)
| Suite / Check Mode | Command | Result |
|---|---|---|
| Phase 88 Suite (`test_phase88_shotmark_pushiris_camset.py`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_phase88*.py"` | **`Ran 28 tests — OK` (0.240s)** |
| Local Donor Mode (Full `outputs/fx3-vm-trial/tests`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py" -v` | **`Ran 211 tests — OK` (0 skipped, 6.284s)** |
| Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py" -v` | **`Ran 211 tests — OK` (2 expected skips, 5.928s)** |
| Repo Clean-Room Hygiene Audit | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **`CLEAN (ALL GREEN)`** |

### 2.2 Isolated Live QEMU Verification (`--port 18778`, `--workdir /private/tmp/fx6-phase88-18778`)
- **Live Port `8768` (`PID 34405`) Protection**：Verified `PID 34405` untouched both before and after the isolated `18778` test run; zero `pkill`/`killall` calls used; spawned child on `18778` cleanly stopped via `SIGTERM` and `/private/tmp/fx6-phase88-18778` deleted.
- **Guest Boot & Readiness**：`LIVE_GPE0_READY` reached at `67.0s` (`71.18s` total check start-to-ready).
- **Baseline `GPE0` Frame**：`sha256=a31beb43bd43835a880d71c009e51802bac9966ff7dd2cfd61d615be0364599e`.
- **`ShotMark1` + `Push Auto Iris (F4.0 Highlight)` + `CH3/4 -20dB` + `User-Bits B0:02:00:07` `GPE0` Delta**：
  - `POST /api/shotmark_and_iris` (`add_shotmark1` `frame=240`, `tc="01:02:03:04"` -> `shotmark_count=1`; `push_auto_iris` + `iris_fstop=4.0`, `metering_mode="highlight"`, `ch34_safety_pad_db=-20`, `user_bits_hex="B0:02:00:07"`).
  - Updated `GPE0` Frame: `sha256=7b637dc950cac995bbd96782b0d1678f044c4b5e8207bcdcd617915a24ddbf2` (`sha_changed=True`).
  - **Measured Decoded PNG IDAT Pixel Buffer Delta vs Baseline**：**`68,453` differing bytes**!
- **`GET /api/xml_sidecar` `<EssenceMark>` Verification**：Confirmed `<KlvPacketTable>` and `<EssenceMark name="_ShotMark1" start="240" ... />` emitted live.
- **A-Cam `ILME-FX6` -> B-Cam `ILME-FX3` Live `POST /api/camset_import`**：Submitted `source_model="ILME-FX6"`, `fx6_nd_preset="1/16"`, `sdi_12g_out="On"`, `wifi_ap_enabled=True`, `vf_peaking="On"` -> `ok=True`, `sanitized_fx6_fields=["fx6_nd_preset", "sdi_12g_out", "wifi_ap_enabled", "vf_peaking"]`, `p4_nd_motor_faults=0`.
- **Guest Serial Log**：`4` `SMRK=` frames emitted (`0` `APPFW_SEGV`; final `FX6_LIVE_FRAME seq=5 page=0 sel=4 cat=2 item=0 depth=0 nz=401545 text_ok=42 fill=38 icon=6 lang=0 ibis_xlr=0 lut_meta=0x00000000 p40=0x00000303 CINE_EXP=0x8003000c:0x01800708:0 WB_MEDIA=0xc0c6af02:0xa0020020:0x00000000 TAFC=0x4e50e780:0x64648250:0x80000004 SMRK=0x78200081:0xa9c43190:0xb0020007`).

---

## 3. Workspace Ownership & Hygiene Checklist / 目录归属与洁净规范

- Strictly modified/created only the 5 owned Phase 88 files:
  - `outputs/fx3-vm-trial/src/fx6_live_guest.c`
  - `outputs/fx3-vm-trial/run_fx6_menu_trial.py`
  - `outputs/fx3-vm-trial/README.md`
  - `outputs/fx3-vm-trial/tests/test_phase88_shotmark_pushiris_camset.py`
  - `reports/2026-11-14-phase88-vm-trial-shotmark-pushiris-camset/README.md`
- `persistent_emmc_writes_authorized = False` preserved; zero `.so`, `.elf`, `.ko`, `.cpio`, `.bin`, `.o`, `.pyc`, `__pycache__`, or `.png` artifacts tracked or left untracked.
