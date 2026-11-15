# Global Sony Real-Hardware Intelligence — Wave 36 (`ILME-FX3 Ver. 7.02` `Shoe Audio Set.` `48kHz/24bit 4ch` vs `3.5mm`/`ANALOG`/`S&Q` Lockouts, `Wind Noise Reduct.` Built-In-Mic-Only Boundary, and `Save/Load Settings` `CAMSET` + `C3 Portal` Privacy/Calibration Exclusion Firewall)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Shoe Audio Set.*, *Audio Level Display*, *Wind Noise Reduct.*, *Audio Recording*, *Save/Load Settings*, *Using Creators' App / C3 Portal*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Shoe Audio Set.]` (`48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch`): 4-Channel Meter Expansion vs `3.5mm` Jack, `ANALOG` Handle Switch & `S&Q` Lockouts

1. **Menu Path, Modes & Reset Behavior**:
   - `MENU` -> `Shooting` -> `[Audio Recording]` -> **`[Shoe Audio Set.]`**:
     - **`[48kHz/16bit 2ch]`** (factory default);
     - **`[48kHz/24bit 2ch]`**;
     - **`[48kHz/24bit 4ch]`** (records `CH1`–`CH4` discrete digital LPCM tracks when a 4ch-capable Multi Interface Shoe digital audio accessory such as the **`XLR-H1` XLR Handle Unit** in `DIGITAL` mode or `ECM-M1` is attached).
   - **Reset Behavior**: `[Shoe Audio Set.]` **IS reset** to `[48kHz/16bit 2ch]` by `[Camera Settings Reset]`.
2. **Exact Hardware Coupling & Disqualification Rules**:
   - **4-Channel `[Audio Level Display]` Coupling**: When `[Shoe Audio Set.]` = `[48kHz/24bit 4ch]` with a compatible digital MI Shoe 4ch source, `[Audio Level Display]` automatically renders **4-channel (`CH1`..`CH4`) level meters** on the shooting OSD (`2ch` meters in `2ch` or analog modes).
   - **Three Hardware Override / Lockout Conditions**:
     1. **`[Audio Recording]` = `[Off]`** or **`S&Q Motion` mode**: audio recording is disabled (`0` audio tracks); `[Shoe Audio Set.]` is unavailable (`grayed out`).
     2. **Body `3.5mm` `MIC` terminal plug-in priority**: inserting a plug into the camera body's `3.5mm` stereo `MIC` jack overrides both the built-in mic and MI Shoe audio input, forcing `2ch` analog ADC capture and disabling `[Shoe Audio Set.]` digital `4ch`/`24bit` selection.
     3. **`XLR-H1` `[DIGITAL/ANALOG]` slide switch = `[ANALOG]`** (or analog MI Shoe mic): bypasses digital I2S/MI-Shoe `24bit`/`4ch` transport (`2ch` `48kHz/16bit` analog path only).

---

## 2. `[Wind Noise Reduct.]` (`[Off]` Default): Built-In Microphone Scope Only, Low-Cut Attenuation & External-Mic Non-Function

1. **Menu Path, Values & Reset Behavior**:
   - `MENU` -> `Shooting` -> `[Audio Recording]` -> **`[Wind Noise Reduct.]`**: **`[Off]`** (default) / **`[On]`** — **resettable** to `[Off]` by `[Camera Settings Reset]`.
2. **Two Exact Official Sony Acoustic & Routing Boundaries**:
   - **Built-In Microphone Only**: `[Wind Noise Reduct.]` applies a digital high-pass filter **exclusively to the camera body's built-in stereo microphone**. Sony explicitly documents that **`[Wind Noise Reduct.]` does NOT function when an external microphone is used** (neither `3.5mm` `MIC` jack microphones nor Multi Interface Shoe accessories such as `XLR-H1` — where physical hardware `[LOW CUT]` `Off`/`100Hz`/`300Hz` switches on the `XLR-H1` handle govern wind filtering instead).
   - **Indoor Bench Low-Volume Warning & `S&Q` Lockout**: Sony warns that setting `[Wind Noise Reduct.]` = `[On]` where wind is not blowing strongly causes normal low-frequency audio to be recorded at lower volume / altered timbre; `[Wind Noise Reduct.]` is also locked out when `[Audio Recording]` = `[Off]` or in `S&Q Motion`.

---

## 3. `[Save/Load Settings]` (`CAMSET01.DAT..CAMSET10.DAT` & `Cloud(Private)` / `Cloud(Share)`): Same-Model Firewall, Excluded Privacy/Calibration Items & Slot-1 Tier-0 Vault Guard

1. **Menu Path & Dual Storage Targets (`Ver. 4.00+` / `Ver. 7.02`)**:
   - `MENU` -> `Setup` -> `[Reset/Save Settings]` -> **`[Save/Load Settings]`**:
     - **`Media` (`Slot 1` / `Slot 2`)**: saves/loads up to **`10`** camera setting files per card (`CAMSET01.DAT` .. `CAMSET10.DAT`), strictly model-locked to **`ILME-FX3`** (`ILME-FX6` `.DAT` / `ALL File` settings are rejected and never cross-loaded);
     - **`Cloud(Private)` / `Cloud(Share)`**: cloud settings sync via `Creators' Cloud` / `C3 Portal` (`Ver. 4.00+`).
   - Action item: executing `[Save/Load Settings]` is not itself a stateful parameter, whereas `[Load]` overwrites target camera menu registers without touching excluded items below.
2. **Official Excluded-Items Firewall (Never Saved to or Loaded from `CAMSET*.DAT` / Cloud)**:
   - Per Sony Help Guide, `[Save/Load Settings]` **strictly excludes** device-specific calibration, identity, and network credential registers so shared `CAMSET*.DAT` / `Cloud(Share)` profiles cannot leak secrets or corrupt per-body calibration:
     1. **`[IPTC Information]`** & **`[Copyright Info]`** (`Write Copyright Info`, photographer/copyright owner strings);
     2. **`[Custom White Balance]` captured registers (`Custom 1`, `Custom 2`, `Custom 3`)**;
     3. **`[Face Memory]`** registered biometric face templates;
     4. **Network & Credential Stores**: `[FTP Transfer Func.]` server/account passwords, `[Streaming]` RTMP/RTMPS/SRT stream keys & destinations, registered `Wi-Fi` access point SSIDs/passphrases, static IP/DNS, and imported root/client TLS certificates.
3. **Slot-1 Tier-0 Vault Card Write Firewall**:
   - Selecting `[Save]` targeting **Slot 1** writes/overwrites `/PRIVATE/SONY/PRO/CAMERA/ILME-FX3/CAMSETxx.DAT` on the Slot 1 card; during Tier-0 forensic card vaulting (`pnflasha` / `cnflasha` / baseline `CAMSET01.DAT` preservation), `[Save]` to an unverified or non-write-protected Slot 1 Tier-0 vault card must be **blocked** (`[Load]` is `O_RDONLY` on the card, whereas `[Save]` mutates card sectors and requires either Slot 2 scratch media or post-hash verification).
