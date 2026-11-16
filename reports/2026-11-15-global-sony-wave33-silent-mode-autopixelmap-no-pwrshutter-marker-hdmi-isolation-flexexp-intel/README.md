# Global Sony Real-Hardware Intelligence — Wave 33 (`ILME-FX3 Ver. 7.02` `Silent Mode Settings` `Auto Pixel Mapping` Target & `Shutter When Pwr OFF` Absence, `Marker Display` 15-Ratio Non-Resettable Persistence & Local-LCD-Only HDMI Isolation, and `Flexible Exp. Mode` `Av/Tv/ISO` Reset Split)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Silent Mode Settings (still image/movie)*, *Marker Display*, *Exposure Ctrl Type*, *Auto/Manual Swt. Set.*, *Auto Slow Shutter*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Silent Mode Settings]` (`[Auto Pixel Mapping]` Suppression Target, 5-Function Lockout & Hardware `[Shutter When Pwr OFF]` Absence)

1. **`[Silent Mode]` = `[On]` Automatic Locks & 5 Disqualifications**:
   - Path: `MENU` -> `Shooting` -> `[Shutter/Silent]` -> **`[Silent Mode Settings]`**.
   - Setting `[Silent Mode]` = **`[On]`** automatically locks **`[Shutter Type]`** and **`[Shutter Type in Interval]`** to **`[Electronic Shutter]`**, locks **`[Audio signals]`** to **`[Off]`**, and disables **5 shooting functions**:
     1. Flash shooting,
     2. `[Long Exposure NR]`,
     3. `[e-Front Curtain Shut.]`,
     4. `BULB` shooting,
     5. `[Anti-flicker Shoot.]`.
2. **`[Target Function Settings]` (`[Aperture Drive in AF]` & `[Auto Pixel Mapping]`)**:
   - Determines whether acoustic-emitting auxiliary subsystems are simultaneously altered in Silent Mode: **`[Aperture Drive in AF]`** and **`[Auto Pixel Mapping]`** (setting `[Not Target]` retains each function's setting even when `[Silent Mode]` = `[On]`; when targeted, Silent Mode suppresses power-off `[Auto Pixel Mapping]` mechanical shutter actuation).
   - **Bench Tier-0 Implication**: Enabling `[Silent Mode]` = `[On]` with `[Auto Pixel Mapping]` targeted provides a deterministic, non-invasive software interlock preventing unexpected power-off mechanical dark-frame calibration cycles (`cnflasha` touch) during controlled bench shutdowns.
3. **Hardware Absence of `[Shutter When Pwr OFF]` on `ILME-FX3` (`Ver. 2.00..7.02`)**:
   - Unlike Alpha still bodies with an anti-dust mechanical curtain menu option, `ILME-FX3` (`Ver. 2.00..7.02`) **does NOT expose `[Shutter When Pwr OFF]`** anywhere in Setup or Target Function Settings (only `[Sensor Cleaning]`, `[Auto Pixel Mapping]`, and `[Pixel Mapping]` exist). Any ported menu/safety contract must reject fabricated `[Shutter When Pwr OFF]` assertions on physical `ILME-FX3`.

---

## 2. `[Marker Display]` (`15` `Aspect Marker` Ratios in `Ver. 3.00+/7.02`, `[Camera Settings Reset]` Survival & Strict Local-Monitor-Only HDMI Isolation)

1. **Sub-Items & `Ver. 3.00+/7.02` `15`-Ratio `[Aspect Marker]` Table**:
   - Path: `MENU` -> `Shooting` -> **`[Marker Display]`**:
     - `[Marker Display]` (`[On]` / `[Off]`, default `Off`),
     - `[Center Marker]` (`[Off]` / `[On]`),
     - `[Aspect Marker]`: `[Off]` (default) plus **15 aspect ratios** (`9:16`, `4:5`, `1:1`, `4:3`, `13:9`, `14:9`, `15:9`, `16:9` *(Ver. 3.00+)*, `17:9`, `1.66:1`, `1.85:1`, `1.91:1`, `2:1`, `2.35:1`, `2.39:1`),
     - `[Safety Zone]` (`[Off]` / `[80%]` / `[90%]`),
     - `[Guideframe]` (`[Off]` / `[On]`).
2. **Non-Resettable Persistence Across `[Camera Settings Reset]`**:
   - Per Sony's *List of default setting values*, `[Aspect Marker]` / `[Marker Display]` configuration is **NOT reset** by `[Camera Settings Reset]` (*Resettable using `[Camera Settings Reset]`: `Not available`*; cleared only by `[Initialize]`).
3. **Strict Local-Monitor-Only HDMI Clean-Feed Rule**:
   - *"Markers are displayed on the camera monitor only and cannot be output externally"* — even when `[HDMI Info. Display]` = `[On]`, `ILME-FX3` never outputs `[Marker Display]` overlays (`Center`, `Aspect`, `Safety Zone`, `Guideframe`) onto HDMI (unlike `ILME-FX6` independent SDI/HDMI marker routing).

---

## 3. `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`), `[Auto/Manual Swt. Set.]` & `[Auto Slow Shutter]` Reset Split

1. **`[Exposure Ctrl Type]` (`MENU` -> `Shooting` -> `[Shooting Mode]` -> `[Exposure Ctrl Type]`)**:
   - Switches movie & S&Q exposure control between **`[P/A/S/M Mode]`** (`Program Auto`, `Aperture Priority`, `Shutter Priority`, `Manual Exposure`) and Cinema-style **`[Flexible Exp. Mode]`**.
2. **`[Auto/Manual Swt. Set.]` & `[Auto Slow Shutter]` (`[Camera Settings Reset]` Resettable Split)**:
   - Under `[Flexible Exp. Mode]`, **`[Auto/Manual Swt. Set.]`** independently switches **`Av Auto/Manual Switch`**, **`Tv Auto/Manual Switch`**, and **`ISO Auto/Manual Set`** (all 3 default to **`Manual`** and **ARE reset** to `Manual` by `[Camera Settings Reset]`).
   - **`[Auto Slow Shutter]`** defaults to **`On`** and **IS reset** to `On` by `[Camera Settings Reset]` — contrasting sharply with non-resettable `[Marker Display]` / `[Aspect Marker]`, `[Zebra Display]` / `[Zebra Level]`, and `[NTSC/PAL Selector]`.
