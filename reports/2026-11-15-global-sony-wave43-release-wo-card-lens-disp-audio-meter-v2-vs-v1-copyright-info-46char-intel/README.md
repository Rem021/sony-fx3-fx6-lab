# Global Sony Real-Hardware Intelligence — Wave 43 (`ILME-FX3 Ver. 7.02` `Release w/o Card` Still-Only vs Movie Media Gate & `Release w/o Lens`, `Ver. 2.00+`/`7.02` `DISP (Screen Disp) Set` Audio Meter Integration vs `Ver. 1.x`, and `Copyright Info` `46`-Char Still EXIF Boundary)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Release w/o Card*, *Release w/o Lens (still image/movie)*, *Audio Recording / Shoe Audio Set.*, *DISP (Screen Disp) Set*, *Copyright Info*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Release w/o Card]` vs `[Release w/o Lens]` (`MENU` -> `Shooting` -> `[Shutter/Silent]`): Cardless Bench Safety & Still-vs-Movie Scope

1. **`[Release w/o Card]` (`[Enable]` Default / `[Disable]`, Still-Image Scope)**:
   - `MENU` -> `Shooting` -> `[Shutter/Silent]` -> **`[Release w/o Card]`**: **`[Enable]`** (factory default — shutter releases without a card, images not saved) / **`[Disable]`** (blocks shutter release when no card is inserted).
   - **Bench Safety Rule**: Setting `[Release w/o Card] = [Disable]` in production prevents accidental unrecorded shoots, whereas on a cardless diagnostic bench (`Slot-1`/`Slot-2` empty so zero media writes can occur), `[Enable]` permits shutter-actuation testing while movie internal recording remains blocked unless a card is inserted (external HDMI capture remains governed by `[Rec. Media dur HDMI Output]`).
2. **`[Release w/o Lens]` (`[Enable]` Default / `[Disable]`, Still + Movie + `S&Q` Scope)**:
   - `MENU` -> `Shooting` -> `[Shutter/Silent]` -> **`[Release w/o Lens]`**: **`[Enable]`** (default — permits body-only bench, cinema PL-mount mechanical adapter, or telescope operation with `0` E-mount `E-ND` / lens UART traffic) / **`[Disable]`** (blocks release without electronic E-mount lens).
   - Both `[Release w/o Card]` and `[Release w/o Lens]` survive `[Camera Settings Reset]` on `Setup`/persist lists or follow official default `Enable` on `[Initialize]`.

---

## 2. `Ver. 2.00+` / `Ver. 7.02` `[Audio Recording]` 5-Item Menu vs `Ver. 1.x` `[Audio Level Display]` Removal

1. **Exact `ILME-FX3` `Ver. 2.00+` / `Ver. 7.02` (`ilc/2210`) Menu Structure**:
   - Under `MENU` -> `Shooting` -> **`[Audio Recording]`**, the exact 5 items are: **`[Audio Recording]`** (`On`/`Off`), **`[Audio Rec Level]`** (`0..31`), **`[Audio Out Timing]`** (`Live`/`Lip Sync`), **`[Wind Noise Reduct.]`** (`On`/`Off`), and **`[Shoe Audio Set.]`**.
   - **Critical `Ver. 1.x` (`ilc/2035`) vs `Ver. 7.02` (`ilc/2210`) Split**: Standalone `[Audio Level Display]` from `Ver. 1.x` is **absent** in `Ver. 2.00+`/`7.02`; audio level meter visibility (2ch or 4ch during 4-channel MI-shoe recording, suppressed during `S&Q`) is governed by **`DISP (Screen Disp) Set`** (`MENU` -> `Setup` -> `[Operation Customize]` -> `[DISP (Screen Disp) Set]`) (`legacy_v1_audio_level_menu_spoof_events == 0`).

---

## 3. `[Copyright Info]` (`MENU` -> `Shooting` -> `[File]` -> `[Copyright Info]`): `46`-Char Still EXIF Scope & Privacy Hygiene

1. **Menu Path & Sub-Items**:
   - `MENU` -> `Shooting` -> `[File]` -> **`[Copyright Info]`**: **`[Write Copyright Info]`** (`[Off]` default / `[On]`), **`[Set Photographer]`** (`<= 46` alphanumeric/symbol characters), **`[Set Copyright]`** (`<= 46` alphanumeric/symbol characters), and **`[Disp. Copyright Info]`**.
2. **Still-Image EXIF Scope & C3/Fleet Privacy Guard**:
   - Writes EXIF copyright tags onto **still images** (`Write Copyright Info = Off` default on clean-room benches so zero operator PII leaks into test artifacts; `photographer_copyright_pii_leaked_bytes == 0`), and `[Set Photographer]` / `[Set Copyright]` strings survive `[Camera Settings Reset]` (cleared by `[Initialize]`).
