# Global Sony Real-Hardware Intelligence — Wave 38 (`ILME-FX3 Ver. 7.02` `Lock Operation Parts` & `MENU + Fn` 5s Chord, `Audio Out Timing` `Live`/`Lip Sync` vs `S&Q` Lockout, `Audio signals` Setup Survival vs `Silent Mode` Lock, and `Exposure step` `0.3EV`/`0.5EV` vs `Shutter Angle` Independence)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Lock Operation Parts*, *Changing the function of the dial temporarily (My Dial Settings)*, *Audio Out Timing*, *Audio signals*, *Silent Mode Settings (still image/movie)*, *Exposure step (still image/movie)*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Lock Operation Parts]` (`Fn` Long-Press, `MENU + Fn` 5-Second Full-Body Chord & `My Dial` Temporary Override)

1. **Menu Path, Modes & Non-Resettable `[Setup]` Persistence**:
   - `MENU` -> `Setup` -> `[Dial Customize]` -> **`[Lock Operation Parts]`**:
     - **`[Off]`** (default — pressing/holding `Fn` does not lock controls);
     - **`[Multi-Selector Only]`** (`[Multi-Slct Only]`);
     - **`[Dial + Wheel]`** (locks front dial, rear dial, and control wheel);
     - **`[All]`** (locks multi-selector, front dial, rear dial, and control wheel).
   - **Survives `[Camera Settings Reset]`**: As a `[Setup]` item, `[Lock Operation Parts]` is **NOT reset** by `[Camera Settings Reset]` (restored to `[Off]` only by `[Initialize]`).
2. **Three Exact Hardware Key-Chord & Override Rules**:
   - **`Fn` Hold Toggle**: Pressing and holding `Fn` engages the configured `[Lock Operation Parts]` scope until `"Locked."` appears on the monitor; holding `Fn` again releases it.
   - **`MENU` + `Fn` Simultaneous `5`-Second Full-Body Lock Chord**: Pressing and holding **`MENU` + `Fn` simultaneously for `5` seconds** locks/unlocks **all buttons, dials, and wheels except the shutter button** — providing a hardware physical-control lock during unattended Tier-0 `pnflasha`/`cnflasha` bench dumps (distinct from the destructive `MENU + Delete` `2`-second Slot Full Format chord!).
   - **`My Dial` Recall Temporary Unlock**: Even while dials/wheels are locked via `[Lock Operation Parts]`, recalling **`My Dial`** temporarily unlocks the assigned dials/wheels for the duration of the recall.

---

## 2. `[Audio Out Timing]` (`[Live]` vs `[Lip Sync]`) & `[Audio signals]` (`[Setup]` Persistence vs `[Silent Mode]` Hard Lock)

1. **`[Audio Out Timing]` (`MENU` -> `Shooting` -> `[Audio Recording]` -> `[Audio Out Timing]`)**:
   - **`[Live]`** (default — outputs headphone monitoring audio without delay to eliminate echo during live mic monitoring) vs **`[Lip Sync]`** (delays audio output to match video frame processing latency).
   - **Resettable** to `[Live]` via `[Camera Settings Reset]`; **hardware-unavailable during `S&Q Motion`** (slow-motion/quick-motion) and when `[Audio Recording]` = `[Off]`.
2. **`[Audio signals]` (`MENU` -> `Setup` -> `[Sound Option]` -> `[Audio signals]`)**:
   - **`[On]`** (default — emits AF confirmation / self-timer beeps) / **`[Off]`**.
   - **Survives `[Camera Settings Reset]`** (`[Setup]` item, reset only by `[Initialize]`), **EXCEPT** whenever **`[Silent Mode]` = `[On]`**, `[Audio signals]` is **hardware-locked to `[Off]`** until `[Silent Mode]` returns to `[Off]`.

---

## 3. `[Exposure step]` (`0.3EV` Default / `0.5EV`) vs `[Shutter Angle]` Constant-Increment Independence

1. **Menu Path, Values & Reset Behavior**:
   - `MENU` -> `Exposure/Color` -> `[Exposure Comp.]` -> **`[Exposure step]`**: **`[0.3EV]`** (default) / **`[0.5EV]`** — **resettable** to `[0.3EV]` via `[Camera Settings Reset]`.
2. **`[Shutter Angle]` (`Ver. 6.00+` / `Ver. 7.02`) Exemption Invariant**:
   - `[Exposure step]` adjusts step increments for **shutter speed (`[Shutter Speed]` mode), aperture (`F-stop`), and exposure compensation**, **whereas `[Shutter Angle]` (under `[Shutter Mode]` = `[Shutter Angle]`) is NOT affected by `[Exposure step]` and remains on its constant cine shutter-angle table** (`5.6°` .. `360°`).
