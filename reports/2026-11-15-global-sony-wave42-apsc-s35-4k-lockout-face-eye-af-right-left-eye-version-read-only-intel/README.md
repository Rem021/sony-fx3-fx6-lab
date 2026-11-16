# Global Sony Real-Hardware Intelligence — Wave 42 (`ILME-FX3 Ver. 7.02` `APS-C S35 Shooting` `12.1MP` `4K` Movie Lockout, `Face/Eye AF` `Right/Left Eye Select` & Clean-HDMI Frame Isolation, and `Version` Read-Only vs Hard-Blocked `BODYDATA.DAT` Flash)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *APS-C S35 (Super 35mm) Shooting (still image/movie)*, *Face/Eye Prior. in AF*, *Face/Eye Subject*, *Right/Left Eye Select*, *Face/Eye Frame Disp.*, *Version*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[APS-C S35 Shooting]` (`MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[APS-C S35 Shooting]`): `12.1MP` Sensor `4K` Movie Lockout

1. **Menu Path, Options & Reset Scope**:
   - `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> **`[APS-C S35 Shooting]`**: **`[Auto]`** (factory default), **`[On]`** (~`1.5x` APS-C / Super 35mm angle of view), **`[Off]`** (35mm full-frame).
   - Resettable by `[Camera Settings Reset]` (and `[Initialize]`).
2. **Critical `ILME-FX3` `12.1MP` Full-Frame Sensor Boundary**:
   - Because `ILME-FX3` (`ilc/2210`) uses a `12.1 MP` full-frame sensor (`4240 × 2832` effective still / `3840 × 2160` 1:1 4K readout), an APS-C / Super 35mm sub-window lacks horizontal resolution for 4K.
   - Consequently, **`[APS-C S35 Shooting]` is disabled and locked to `[Off]` whenever recording `4K` movies (`XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`) or `4264×2408` `HDMI RAW Output`** — Super 35mm movie capture is available **only** in **`HD` (`XAVC S HD` / `XAVC S-I HD`)** (`apsc_s35_4k_or_raw_bypass_events == 0`, strictly distinguishing `ILME-FX3` from native-S35 `ILME-FX30` and oversampled `ILCE-7RM5`/`ILCE-7M4`).

---

## 2. `[Face/Eye AF]` (`[Face/Eye Prior. in AF]`, `[Face/Eye Subject]`, `[Right/Left Eye Select]` & `[Face/Eye Frame Disp.]`): BIONZ XR Naming & Clean-HDMI Isolation

1. **Exact `ILME-FX3` (`ilc/2210`) Menu Hierarchy (Not Dedicated AI-Unit `[Subject Recog in AF]`)**:
   - `MENU` -> `Focus` -> **`[Face/Eye AF]`** (all items resettable by `[Camera Settings Reset]` except registered `[Face Memory]` database, which requires explicit deletion or `[Initialize]`):
     - **`[Face/Eye Prior. in AF]`**: `[On]` (default; locked `[On]` in `[Intelligent Auto]`) / `[Off]`;
     - **`[Face/Eye Subject]`**: `[Human]` (default) / `[Animal]` (with `Ver. 3.00+`/`7.02` `[Bird]` support);
     - **`[Right/Left Eye Select]`**: `[Auto]` (default) / `[Right Eye]` / `[Left Eye]` (subject's perspective; switchable via `[Switch Right/Left Eye]` custom key);
     - **`[Face/Eye Frame Disp.]`**: `[On]` / `[Off]` (cleared automatically after focus lock if `[AF Area Auto Clear] = [On]`).
2. **HDMI Clean-Feed Isolation**:
   - `[Face/Eye Frame Disp.]` overlays render only on the camera LCD (or HDMI with `[HDMI Info. Display] = [On]`) and are **never baked into `[HDMI Info. Display] = [Off]` or `HDMI RAW Output`** (`hdmi_clean_feed_eye_frame_baked_pixels == 0`).

---

## 3. `[Version]` (`MENU` -> `Setup` -> `[Setup Option]` -> `[Version]`): Read-Only Inspection vs Hard-Blocked `BODYDATA.DAT` Flash

1. **Read-Only `[Version]` Dialog & Zero-RF Notification Suppression**:
   - Displays `ILME-FX3` Body (`Ver. 7.02`), E-mount Lens, and Mount Adaptor versions without touching flash partitions; `Ver. 6.00+` / `Ver. 7.02` red update notification badge is suppressed on our zero-RF `Airplane Mode = On` bench (`passive_tx_bytes_emitted == 0`).
2. **Hard-Blocked System Software Update Redline**:
   - Executing SD/CFexpress Slot-1 `BODYDATA.DAT` firmware flashing (`persistent_emmc_writes_authorized = False`) remains **HARD-BLOCKED / NO-GO** for all automated agents (human physical bench requires `NP-FZ100 >= 3 bars / >= 51%` and unmodified Sony-signed `BODYDATA.DAT` only).
