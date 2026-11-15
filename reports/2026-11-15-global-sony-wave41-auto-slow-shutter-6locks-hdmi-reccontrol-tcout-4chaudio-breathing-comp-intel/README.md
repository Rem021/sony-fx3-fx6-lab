# Global Sony Real-Hardware Intelligence — Wave 41 (`ILME-FX3 Ver. 7.02` `Auto Slow Shutter` 6-Condition Lockout & `Cine EI` / `Shutter Angle` Disjointness, `HDMI Output Settings` `REC Control` <- `Time Code Output` Gate & `4ch Audio Output`, and `Breathing Comp.` Lens Boundary)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Auto Slow Shutter (`TP1000668443`)*, *Shutter Mode (movie)*, *HDMI Output Settings (movie)*, *Outputting RAW movies to an external RAW recorder*, *Lens Compensation (still image/movie)*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Auto Slow Shutter]` (`MENU` -> `Exposure/Color` -> `[Exposure]` -> `[Auto Slow Shutter]`): 6 Exact Non-Function Lockouts & `[Shutter Angle]` Disjointness

1. **Menu Path, Factory Default & Reset Scope**:
   - `MENU` -> `Exposure/Color` -> `[Exposure]` -> **`[Auto Slow Shutter]`**: **`[On]`** (factory default) / **`[Off]`**.
   - **Resettable by `[Camera Settings Reset]`** (and `[Initialize]`); unaffected by `[Reset Network Set.]`.
2. **Exact 6 Official Hardware Lockout / Non-Function Conditions**:
   - Cannot be used / does not function in:
     1. **Slow-motion / Quick-motion (`S&Q`)** shooting;
     2. **`Shutter Priority` (`S`)** mode;
     3. **`Manual Exposure` (`M`)** mode;
     4. **`[ISO]` set to anything other than `[ISO AUTO]`** (fixed manual ISO);
     5. **`[Exposure Ctrl Type]` = `[Flexible Exp. Mode]`** when shutter speed adjustment is set to **`[Manual]`**;
     6. **`[Log Shooting]`** set to **`[Cine EI Quick]`** or **`[Cine EI]`** (including Big-6 `Cine EI` home operation).
   - **Strict Hardware Disjointness with `[Shutter Mode]` = `[Angle]`**: Because `[Angle]` (`Ver. 6.00+` / `Ver. 7.02`) is active **only** in `Shutter Priority`, `Manual Exposure`, or `Flexible Exp. Mode` (manual shutter), `[Auto Slow Shutter]` and `[Shutter Angle]` can **never** simultaneously govern exposure time (`auto_slow_shutter_angle_overlap_events == 0`).

---

## 2. `[HDMI Output Settings]` (`[REC Control]` <- `[Time Code Output]` Prerequisite, `[4ch Audio Output]` Routing & `[Rec. Media dur HDMI Output]` Vault Guard)

1. **Menu Path & Non-Resettable `[Setup]` Survival**:
   - `MENU` -> `Setup` -> `[External Output]` -> **`[HDMI Output Settings]`**: **Survives `[Camera Settings Reset]`** and `[Reset Network Set.]` (cleared **only** by `[Initialize]`).
2. **Exact Hardware Dependency & Channel-Routing Rules**:
   - **`[REC Control]`** (`[Off]` default / `[On]`): **Cannot be set when `[Time Code Output]` is set to `[Off]`** (`[Time Code Output] = [On]` is a mandatory hardware prerequisite; `hdmi_rec_ctrl_without_tc_violations == 0`).
   - **`[4ch Audio Output]`** (`[CH1/CH2]` default -> outputs Ch1=L / Ch2=R; `[CH3/CH4]` -> outputs Ch3=L / Ch4=R over HDMI when 4-channel MI-shoe audio is active).
   - **`[Rec. Media dur HDMI Output]`** (`[On]` / `[Off]`): When `[Off]`, internal Slot-1/Slot-2 card recording and `[Proxy Recording]` are inhibited during HDMI output, protecting Slot-1 Tier-0 recovery media from unintended clip writes.

---

## 3. `[Lens Compensation]` -> `[Breathing Comp.]` (`Ver. 3.00+` / `Ver. 7.02`): Movie-Only Compliant-Lens Crop & `RAW` / `240p` Lockout

1. **Menu Path, Default & Reset Scope**:
   - `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[Lens Compensation]` -> **`[Breathing Comp.]`**: **`[Off]`** (default) / **`[On]`** (resettable by `[Camera Settings Reset]`).
2. **Hardware Constraints**:
   - Movie-only (does not apply to still images), requires a breathing-compensation-compliant Sony E-mount lens (applies slight angle-of-view crop), and is locked out when `[RAW Output] = [On]` (`4264x2408` 16-bit linear HDMI RAW) or in `S&Q` `239.76p`/`200p` high-frame-rate modes.
