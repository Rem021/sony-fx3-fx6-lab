# Global Sony Real-Hardware Intelligence — Wave 44 (`ILME-FX3 Ver. 7.02` Movie `File Settings` `Cam ID + Reel#` & `37`-Char `Title Name` vs Still `File/Folder Settings` `DSC` Prefix, `Gamma Display Assist` `Log Shooting` Lockout vs `Display LUT` / `Select LUT` `User1..16`, and `Auto Review` `Off` Default & `TC/UB` Non-Resettable Persistence)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *File Settings (movie)*, *File/Folder Settings (still image)*, *Gamma Display Assist*, *Gamma Disp. Assist Typ.*, *Select LUT*, *Display LUT*, *Auto Review*, *TC/UB*, *TC/UB Disp. Setting*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char Title) vs Still `[File/Folder Settings]` (`3`-Char `DSC` Prefix & `Slot-1` Vault Guard)

1. **Movie `[File Settings]` (`MENU` -> `Shooting` -> `[File]` -> `[File Settings]`)**:
   - **`[File Number]`**: **`[Series]`** (factory default — sequential across `Slot 1` and `Slot 2` even when swapping cards) / **`[Reset]`**, plus **`[Series Counter Reset]`**.
   - **`[File Name Format]`** (`Ver. 3.00+` / `Ver. 7.02` cinema slate naming):
     - **`[Standard]`** (factory default, e.g. `C0001.MP4`),
     - **`[Cam ID + Reel#]`** (`[Camera ID]` `A..Z`, `[Reel Number]` `001..999`, `[Camera Position]` `C` / `L` / `R` — aligns `ILME-FX3` multi-cam A/B/C slate naming with `ILME-FX6`!),
     - **`[Title]`**, **`[Date + Title]`**, **`[Title + Date]`**.
   - **`[Title Name Settings]`**: Up to **`37` characters** (letters, numbers, permitted symbols; factory default **`"C"`**). Movie folder paths (`PRIVATE/M4ROOT/CLIP`) **cannot be customized**.
2. **Still `[File/Folder Settings]` (`MENU` -> `Shooting` -> `[File]` -> `[File/Folder Settings]`)**:
   - **`[File Number]`**: **`[Series]`** (factory default) / **`[Reset]`**, plus **`[Forced File Number Reset]`** (creates a new folder and resets sequence to `0001`).
   - **`[Set File Name]`**: First **`3` characters** (`A–Z`, `0–9`, `_`; factory default **`"DSC"`**; **underscore `_` cannot be the first character**).
   - **`[Folder Name]`**: **`[Standard Form]`** (factory default, `3-digit folder# + 5 chars`, e.g. `100MSDCF`) / **`[Date Form]`** (`3-digit folder# + YMMDD`, e.g. `10020405`).
3. **Reset Persistence & `Slot-1` Recovery Vault Firewall**:
   - Per Sony's official *List of default setting values*, **ALL** items under both `[File Settings]` (`File Number`, `File Name Format`, `Title Name Settings`) and `[File/Folder Settings]` (`File Number`, `Set File Name`, `Folder Name`) are **NOT reset by `[Camera Settings Reset]`** (restored only by **`[Initialize]`**).
   - **`Slot-1` Vault Rule**: `[Forced File Number Reset]` and `[Create New Folder]` mutate the active still-image card's DCIM directory table and **must be hard-blocked on `Slot 1`** whenever `Slot 1` holds the read-only `CAMSET`/`BODYDATA.DAT` recovery vault (`slot1_vault_folder_mutation_events == 0`).

---

## 2. `[Gamma Display Assist]` (`Log Shooting` Lockout & Clean External HDMI) vs `[Display LUT]` / `[Select LUT]` (`3` Presets + `User1..User16`)

1. **`[Gamma Display Assist]` & `[Gamma Disp. Assist Typ.]` (`MENU` -> `Setup` -> `[Display Option]`)**:
   - **`[Gamma Display Assist]`**: **`[Off]`** (factory default) / **`[On]`**.
   - **`[Gamma Disp. Assist Typ.]`**: **`[Auto]`** (factory default) / **`[S-Log3→709(800%)]`** / **`[HLG(BT.2020)]`** / **`[HLG(709)]`**.
   - **Two Critical Hardware Boundaries**:
     1. **`[Log Shooting]` Hard Lockout**: **`[Gamma Display Assist]` is locked to `[Off]` whenever `[Log Shooting]` (`Cine EI`, `Cine EI Quick`, or `Flexible ISO`) is set to anything other than `[Off]`**.
     2. **Monitor-Only Scope (Clean External HDMI)**: `[Gamma Display Assist]` applies **only** to the camera's LCD monitor (live view & internal movie playback) and is **NOT applied to movies output to an external TV/HDMI monitor**.
2. **`[Display LUT]` (`[On]` Default) & `[Select LUT]` (`MENU` -> `Exposure/Color` -> `[Color/Tone]` -> `[Select LUT]`)**:
   - During `[Log Shooting] != [Off]`, monitoring conversion is governed instead by **`[Display LUT]`** (**`[On]`** factory default / `[Off]`) and **`[Select LUT]`** (`[S-Log3]`, `[s709]`, `[709(800%)]`, plus **`User1..User16`** — up to `16` registered `.cube` user LUTs).
   - Because `[Gamma Display Assist]`, `[Gamma Disp. Assist Typ.]`, and `[Display LUT]` reside under **`[Setup]`**, all three **survive `[Camera Settings Reset]`** and reset to `Off` / `Auto` / `On` **only via `[Initialize]`**.

---

## 3. `[Auto Review]` (`[Off]` Cinema Default) & `[TC/UB]` (`6` Non-Resettable Timecode Parameters + `[TC/UB Disp. Setting]`)

1. **`[Auto Review]` (`MENU` -> `Setup` -> `[Display Option]` -> `[Auto Review]`, Still-Image Only)**:
   - Values: **`[Off]`** (cinema-centric factory default on `ILME-FX3`, unlike alpha still bodies!) / **`[2 Sec]`** / **`[5 Sec]`** / **`[10 Sec]`**.
   - Resides under `[Setup]` -> survives `[Camera Settings Reset]` (restored to `[Off]` only by `[Initialize]`), and keeping `[Auto Review] = [Off]` avoids post-release live-view interruption on cinema rigs.
2. **`[TC/UB]` (`MENU` -> `Shooting` -> `[TC/UB]`) & `[TC/UB Disp. Setting]` (`MENU` -> `Setup` -> `[Display Option]`)**:
   - Exact 6 `[TC/UB]` parameters and factory defaults on `ILME-FX3 Ver. 7.02`:
     - **`[Time Code Preset]`**: `00:00:00.00`
     - **`[User Bit Preset]`**: `00 00 00 00`
     - **`[Time Code Format]`**: **`[DF]`** (Drop Frame default, NTSC `29.97p`/`59.94p`) / **`[NDF]`** (Non-Drop Frame; forced `NDF` on `24.00p` / PAL `25p`/`50p`)
     - **`[Time Code Run]`**: **`[Rec Run]`** (factory default) / **`[Free Run]`**
     - **`[Time Code Make]`**: **`[Preset]`** (factory default) / **`[Regenerate]`**
     - **`[User Bit Time Rec]`**: **`[Off]`** (factory default) / **`[On]`**
   - **Critical Reset Rule**: Even though `[TC/UB]` sits under the `Shooting` menu tab, Sony explicitly marks **all 6 `[TC/UB]` items as `Not available` for `[Camera Settings Reset]`** — preserving multi-camera free-run/jammed timecode across `[Camera Settings Reset]` and resetting only via **`[Initialize]`** (while `[TC/UB Disp. Setting]` defaults to **`[TC]`** under `[Setup]`).
