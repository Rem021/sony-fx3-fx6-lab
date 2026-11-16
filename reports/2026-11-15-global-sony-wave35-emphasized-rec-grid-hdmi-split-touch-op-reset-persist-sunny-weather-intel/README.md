# Global Sony Real-Hardware Intelligence — Wave 35 (`ILME-FX3 Ver. 7.02` `Emphasized REC Display` & `Grid Line` HDMI Info Routing vs Forced `Off(HDMI Only)` / `RAW` Suppression, `Touch Operation` 4-Item `[Camera Settings Reset]` Survival, and `Monitor Brightness` `Manual` vs `Sunny Weather`)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Emphasized REC Display*, *Grid Line Display (still image/movie)*, *Grid Line Type*, *HDMI Info. Display*, *HDMI Output Settings (movie)*, *Touch Operation*, *Touch Func. in Shooting*, *Touch Sensitivity*, *Monitor Brightness*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Emphasized REC Display]` & `[Grid Line Display]` HDMI Info Routing vs Forced `[Off(HDMI Only)]` / `RAW` Clean-Feed Lock

1. **`[Emphasized REC Display]` (`MENU` -> `Shooting` -> `[Shooting Display]` -> `[Emphasized REC Display]`)**:
   - Displays a bold **red frame** around monitor edges during movie and S&Q recording (`[On]` default on `ILME-FX3`, **resettable** via `[Camera Settings Reset]`).
   - **External HDMI Output Capability**: Unlike `[Marker Display]`, `[Zebra Display]`, and `[Peaking Display]` (which are strictly local-LCD-only), the `[Emphasized REC Display]` red frame **and `[Grid Line Display]`** (`[Rule of 3rds Grid]` default, `[Square Grid]`, `[Diag. + Square Grid]` — **NOT reset** by `[Camera Settings Reset]`) **CAN be output to an external HDMI monitor** when **`[HDMI Info. Display]` = `[On]`** (which blanks the built-in camera LCD and routes OSD overlays to HDMI).
2. **Two Automatic Hardware `[HDMI Info. Display]` -> `[Off]` Clamps**:
   - Whenever **`[Rec. Media dur HDMI Output]`** is set to **`[Off(HDMI Only)]`** OR while outputting **RAW movies** over HDMI, `[HDMI Info. Display]` is **temporarily forced to `[Off]`**, guaranteeing external HDMI recorders never ingest baked-in red REC borders, grid lines, or status text into recorded master streams.

---

## 2. `[Touch Operation]` 4-Item Non-Resettable Persistence Across `[Camera Settings Reset]` & Bench Accidental-Tap Guard

1. **Four Setup Touch Items Immune to `[Camera Settings Reset]`**:
   - Under `MENU` -> `Setup` -> `[Touch Operation]`:
     1. **`[Touch Operation]`**: `[On]` (default) / `[On: Playback Only]` / `[Off]` — **NOT reset** by `[Camera Settings Reset]`;
     2. **`[Touch Sensitivity]`**: `[Standard]` (default) / `[Sensitive]` — **NOT reset** by `[Camera Settings Reset]`;
     3. **`[Swipe Up]`**: `[Open the Fn Menu]` (default) — **NOT reset** by `[Camera Settings Reset]`;
     4. **`[Touch Func. in Shooting]`**: `[Touch Tracking]` (default) / `[Touch Focus]` / `[Off]` — **NOT reset** by `[Camera Settings Reset]`.
   - All 4 items are restored to factory defaults **only** by `[Initialize]`.
2. **Bench Tier-0 Implication**:
   - During unattended physical bench rehearsals or Tier-0 card vault dumps, setting `[Touch Operation]` = `[Off]` (or `[On: Playback Only]`) prevents accidental capacitive screen touches (`Swipe Up` opening `Fn` menu or triggering `Touch Tracking`) and persists across `[Camera Settings Reset]` test cycles.

---

## 3. `[Monitor Brightness]` (`[Manual]` `-2..+2` vs `[Sunny Weather]` Indoor Over-Brightness Warning & Non-Resettable Persistence)

1. **Menu Path & Modes**:
   - `MENU` -> `Setup` -> `[Monitor]` -> **`[Monitor Brightness]`**:
     - **`[Manual]`** (default): adjusts LCD backlight across **`-2` .. `+2`**;
     - **`[Sunny Weather]`**: boosts maximum LCD luminance for outdoor daylight visibility, but Sony explicitly warns **`[Sunny Weather]` is too bright for indoor shooting** (skewing manual visual exposure judgment on the local LCD and raising panel thermal/power draw on internal `NP-FZ100` battery).
2. **Setup Persistence**:
   - Like `[Monitor Flip Direction]`, `[Monitor Brightness]` is a Setup monitor parameter **not reset** by `[Camera Settings Reset]` (cleared only by `[Initialize]`); bench indoor rehearsals should lock `[Monitor Brightness]` to `[Manual]` (`0`) to conserve `NP-FZ100` energy and avoid false highlight clipping perception.
