# Global Sony Real-Hardware Intelligence — Wave 40 (`40th` Milestone: `ILME-FX3 Ver. 7.02` `Different Set for Still/Mv` 8-Item Asymmetric Transition & `Shutter Angle` Split, `Custom Key/Dial Set.` `ISO/EI` Persistence, and `Remain Shoot Display` Still-Buffer Boundary)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Different Set for Still/Mv*, *Assigning frequently used functions to buttons and dials (Custom Key/Dial Set.)*, *Remain Shoot Display (still image)*, *Shutter Mode (movie)*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Different Set for Still/Mv]` (`MENU` -> `Setup` -> `[Operation Customize]` -> `[Different Set for Still/Mv]`): 8 Items, Asymmetric Transitions & `[Shutter Angle]` Override

1. **Exact 8 Configurable Items & Non-Resettable `[Setup]` Persistence**:
   - Checkable items: **`Aperture`**, **`Shutter Speed`**, **`ISO`**, **`Exposure Comp.`**, **`Metering Mode`**, **`White Balance`**, **`Picture Profile`**, and **`Focus Mode`**.
   - **Survives `[Camera Settings Reset]`**: Restored to factory defaults **only** by `[Initialize]`.
2. **Three Exact Sony Hardware State-Transition Rules**:
   - **Common -> Separate**: Current parameter values copy to both Still and Movie registers, **EXCEPT `Custom White Balance`**, which applies only to still-image shooting.
   - **Separate -> Common**: Parameter values return to their initial factory defaults, **EXCEPT `Aperture`, `Shutter Speed`, and `Custom White Balance`**, which retain the values set for **still-image shooting**.
   - **`[Shutter Mode]` = `[Angle]` (`Ver. 6.00+` / `Ver. 7.02`) Override**: Whenever movie `[Shutter Mode]` is set to **`[Angle]`** (`Shutter Angle`), still-image shutter speed and movie shutter angle **operate as independent settings even if `Shutter Speed` is unchecked (set to common) in `[Different Set for Still/Mv]`**.

---

## 2. `[Custom Key/Dial Set.]` (`Front Dial`=`Aperture`, `Rear Dial`=`ISO/EI`, `Control Wheel`=`Shutter Speed`): 3-Domain Keymaps & `[Setup]` Survival

1. **Menu Path & Factory Cinema-Line Dial Defaults**:
   - `MENU` -> `Setup` -> `[Operation Customize]` -> **`[Custom Key/Dial Set.]`** (separate Still, Movie, and Playback assignments across Custom Buttons `1`–`6`, Multi-Selector, Lens Focus Hold, and Dials/Wheel):
     - **`Front dial`**: **`Aperture`** (default);
     - **`Rear dial`**: **`ISO/EI`** (default — automatically adapts between `ISO` and `Cine EI` Exposure Index);
     - **`Control Wheel`**: **`Shutter Speed`** (default).
   - Supports `[Follow Custom]` (Movie inheriting Still assignment), `[My Dial 1]`–`[3]` temporary dial swap, and `[Recall Custom hold 1]`–`[3]`.
2. **Reset Survival**:
   - All `[Custom Key/Dial Set.]` mappings **survive `[Camera Settings Reset]`** and `[Reset Network Set.]` (cleared only by `[Initialize]`, and preserved across `ILME-FX3` `CAMSET01.DAT` `[Save/Load Settings]`).

---

## 3. `[Remain Shoot Display]` (`[Not Displayed]` Default): Still-Image Continuous Buffer Scope & EVF-Less `ILME-FX3` Monitor Topology

1. **Menu Path, Options & Still-Only Scope**:
   - `MENU` -> `Setup` -> `[Display Option]` -> **`[Remain Shoot Display]`**: **`[Not Displayed]`** (default), **`[Always Display]`**, **`[Shoot-Only Display]`**.
   - Displays remaining continuous-shooting still-image buffer capacity only (does not display movie recording remaining card time) and **survives `[Camera Settings Reset]`** (reset only by `[Initialize]`).
2. **EVF-Less `ILME-FX3` Hardware Topology**:
   - Unlike `ILCE-7SM3` (`Alpha 7S III`), `ILME-FX3` (`ilc/2210`) has **no built-in EVF** and **no `[Finder/Monitor]` eye-sensor switch** (`Setup -> [Monitor]` / `[Display Option]` governs the vari-angle LCD directly).
