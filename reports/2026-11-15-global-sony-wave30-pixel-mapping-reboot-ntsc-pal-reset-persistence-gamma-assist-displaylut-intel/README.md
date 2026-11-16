# Global Sony Real-Hardware Intelligence — Wave 30 (`30th Milestone`: `ILME-FX3 Ver. 7.02` `Pixel Mapping` Auto-Restart & Low-Battery Lock, `NTSC/PAL Selector` `DF/NDF` & `Camera Settings Reset` Persistence, and `Gamma Display Assist` vs `Display LUT` Split)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Auto Pixel Mapping*, *Pixel Mapping*, *Silent Mode Settings*, *NTSC/PAL Selector*, *Initialize / Camera Settings Reset*, *Gamma Display Assist*, *Gamma Disp. Assist Typ.*, *Display LUT*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Auto Pixel Mapping]` & Manual `[Pixel Mapping]` Automatic Restart, Shutter Sound in `[Silent Mode]` & Low-Battery Lockout

1. **`[Auto Pixel Mapping]` (`[On]` Default vs 3-Day Cadence)**:
   - `MENU` -> `Setup` -> `[Setup Option]` -> `[Auto Pixel Mapping]` (`[On]` / `[Off]`, default `[On]`): optimizes the `IMX510` full-frame sensor automatically at regular intervals **during camera power-off**.
   - Even when `[Silent Mode]` = `[On]`, mechanical shutter dark-frame actuation sounds occur at power-off during `[Auto Pixel Mapping]` (normal hardware behavior, not a fault). When `[Auto Pixel Mapping]` = `[Off]`, manual `[Pixel Mapping]` is recommended every **3 days** to prevent hot bright spots.
2. **Manual `[Pixel Mapping]` Mandatory Reboot & Low-Battery Block**:
   - Executing `MENU` -> `Setup` -> `[Setup Option]` -> `[Pixel Mapping]` -> `[OK]` **blocks all camera operation during calibration and automatically restarts the camera when finished**, and is **blocked when battery charge is low**.
   - **Stage-B Volatile RAM Implication**: Because manual `[Pixel Mapping]` triggers a full warm/cold reboot, any volatile Stage-B `/tmp` RAM overlay unmounts cleanly back to stock `FX3 Ver. 7.02` (`H0 == H2`), while user-space Stage-B code is strictly forbidden from touching `cnflasha` factory calibration partitions (`persistent_emmc_writes_authorized = False`).

---

## 2. `[NTSC/PAL Selector]` Frame-Rate / `DF-NDF` Exclusivity, Startup Banner & `[Camera Settings Reset]` Persistence

1. **NTSC vs PAL Exclusive Frame-Rate & Timecode Tables**:
   - **`NTSC`**: Enables `23.98p` *(NTSC-exclusive)*, `29.97p`, `59.94p`, `119.88p` (`24.00p` DCI where configured) and unlocks **`[TC Format]` (`DF` / `NDF`)**.
   - **`PAL`**: Enables `25p`, `50p`, `100p`; `23.98p` and `[TC Format]` (`DF`/`NDF` toggle) are **unavailable**.
2. **Startup Notification & `[Camera Settings Reset]` Survival**:
   - Switching `[NTSC/PAL Selector]` away from the regional factory default displays *"Running on NTSC."* or *"Running on PAL."* on every startup screen.
   - **Reset Asymmetry**: `[Camera Settings Reset]` does **NOT** reset `[NTSC/PAL Selector]` (under `[Setup]`); only full **`[Initialize]`** restores regional `[Setup]` defaults, and Tier-0 `Backup.bin` / dual-slot media vaults must track NTSC vs PAL `AVCHD`/`M4ROOT` database state to avoid unintended card re-initialization prompts.

---

## 3. `[Gamma Display Assist]` (`S-Log3→709(800%)` / `HLG`) vs `[Log Shooting]` `[Display LUT]` Lockout & Camera-LCD-Only Scope

1. **4-Mode `[Gamma Disp. Assist Typ.]` Table (`Ver. 2.00+` / `7.02`)**:
   - `MENU` -> `Setup` -> `[Display Option]` -> `[Gamma Disp. Assist Typ.]` provides strictly **`[Auto]`**, **`[S-Log3→709(800%)]`**, **`[HLG(BT.2020)]`**, and **`[HLG(709)]`** (applicable to Picture Profile shooting & playback, plus HLG still playback when `[HLG Still Image]` = `[On]`).
2. **Hard Lockout Under `[Log Shooting]` & Zero-HDMI Scope**:
   - Whenever `[Log Shooting]` is active (`Cine EI` / `Cine EI Quick` / `Flexible ISO`, i.e. not `[Off]`), **`[Gamma Display Assist]` is hard-locked to `[Off]`**, and preview conversion is governed exclusively by **`[Display LUT]`** (`[On]` / `[Off]` / `[Display LUT Switch]` custom key).
   - **Built-in Monitor Only**: `[Gamma Display Assist]` is **never applied to external TVs or HDMI monitors** connected to the camera — operators relying on `[Gamma Display Assist]` (`Picture Profile` S-Log3/HLG) still send un-assisted gamma over HDMI!
