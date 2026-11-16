# Global Sony Real-Hardware Intelligence — Wave 45 (`45th` Milestone: `ILME-FX3 Ver. 7.02` `Focus Magnifier` / `Auto Magnifier in MF` vs Legacy `MF Assist` & `Initial Focus Mag.` `x1.0`, `Area/Date/Time Setting` Creators' App Auto-Correction Isolation, and `Video Light Mode` `Power Link` / `HDMI Resolution` `Auto` Setup Persistence)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Focus Magnifier*, *Auto Magnifier in MF*, *Initial Focus Mag.*, *AF in Focus Mag.*, *Peaking Display*, *Area/Date/Time Setting*, *Video Light Mode*, *AF Illuminator*, *HDMI Resolution*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Focus Assistant]` (`Focus Magnifier`, `Auto Magnifier in MF`, `Initial Focus Mag.` `x1.0`, `AF in Focus Mag.`) & `[Peaking Display]`

1. **Exact `ILME-FX3` `Ver. 2.00+` / `Ver. 7.02` (`ilc/2210`) Focus Assistant Menu & Factory Defaults**:
   - `MENU` -> `Focus` -> **`[Focus Assistant]`**:
     - **`[Auto Magnifier in MF]`**: **`[On]`** (factory default — enlarges screen automatically when turning focus ring in `MF`/`DMF`; note `ILME-FX3` `ilc/2210` uses `[Auto Magnifier in MF]`, NOT legacy `"MF Assist"`).
     - **`[Focus Magnifier]`**: Assigned to **`Custom Button 5`** by default (also triggered by double-tapping LCD in `MF` when `Touch Operation = On`).
     - **`[Focus Magnif. Time]`**: **`[No Limit]`** (factory default; or `2 Sec` / `5 Sec`).
     - **`[Initial Focus Mag.]` (still image)** & **`[Initial Focus Mag.]` (movie)**: Separate Still and Movie registers, both defaulting to **`[x1.0]`** (`x1.0` / `x4.0`).
     - **`[AF in Focus Mag.]`** (still image): **`[On]`** (factory default — half-pressing shutter re-focuses on magnified area; `[Off]` cancels Focus Magnifier on half-press).
2. **`[Peaking Display]` (`MENU` -> `Focus` -> `[Peaking Display]`)**:
   - **`[Peaking Display]`**: **`[Off]`** (default; `[Peaking Display Select]` assigned to Control Wheel Right by default); **`[Peaking Level]`**: **`[Mid]`** (`High`/`Mid`/`Low`); **`[Peaking Color]`**: **`[White]`** (`Red`/`Yellow`/`Blue`/`White`), working alongside `[AF Assist]` manual focus override in Movie/`S&Q`.

---

## 2. `[Area/Date/Time Setting]` (`Setup > Area/Date`) & Zero-RF Smartphone Time/Area Sync Isolation

1. **Menu Path & Sub-Items**:
   - `MENU` -> `Setup` -> `[Area/Date]` -> **`[Area/Date/Time Setting]`** (exact `ilc/2210` title, NOT legacy `"Date/Time Setup"`): **`[Area Setting]`** (`—` initial unconfigured factory state), **`[Daylight Savings]`** (`[Off]` default / `[On]`), **`[Date/Time]`**, and **`[Date Format]`**.
2. **Reset Survival & Zero-RF Bench Rule**:
   - Resides under `[Setup]` -> **survives `[Camera Settings Reset]`** (cleared/re-prompted only on `[Initialize]` or RTC backup battery depletion).
   - Creators' App `[Location Information Linkage]` (`[Auto Time Correction]` / `[Auto Area Adjustment]`) requires Bluetooth/smartphone radio link -> **suppressed on our zero-RF bench posture (`[Airplane Mode] = [On]`, `passive_tx_bytes_emitted == 0`)**, preventing unexpected RTC/timezone jumps during `H0..H3` forensic timestamping.

---

## 3. `[Video Light Mode]` (`[Power Link]` Default), `[AF Illuminator]` (Still-Only) & `[HDMI Resolution]` (`[Auto]` Default)

1. **`[Video Light Mode]` (`[Power Link]` Default) & `[AF Illuminator]` (Still-Only)**:
   - **`[Video Light Mode]`**: Controls optional MI-Shoe `HVL-LBPC` LED video light across Still, Movie, and `S&Q` (`[Power Link]` factory default / `[REC Link]` / `[REC Link & STBY]` / `[Auto]`); survives `[Camera Settings Reset]` under `[Setup]`, and on `PMIC 5V <= 900 mA` bench checks (`Gate G24`), external MI-Shoe lighting load must never violate the `5V` accessory rail budget.
   - **`[AF Illuminator]`**: **`[Auto]`** default / **`[Off]`** — **Still-image AF only** (never fires during Movie / `S&Q` recording).
2. **`[HDMI Resolution]` (`MENU` -> `Setup` -> `[External Output]` -> `[HDMI Resolution]`)**:
   - Values: **`[Auto]`** (factory default — EDID handshake) / **`[2160p]`** / **`[1080p]`** / **`[1080i]`**; survives `[Camera Settings Reset]` under `[Setup]` (restored to `[Auto]` only by `[Initialize]`), while Log internal recording downshift (`1080p` unless `Rec. Media dur HDMI Output = Off(HDMI Only)`) overrides manual `2160p` per Sony hardware rules.
