# Global Sony Real-Hardware Intelligence — Wave 31 (`ILME-FX3 Ver. 7.02` `SteadyShot Active` `119.88p/120fps/RAW` Cutoffs, `Clear Image Zoom` Center-AF & `[Multi]` Metering Lock, and `Power Save Start Time` 9-Condition Bypass + `Auto Power OFF Temp.`)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *SteadyShot (movie)*, *HDMI Output Settings — RAW Output*, *The zoom features available with this product*, *Power Save Start Time*, *Auto Power OFF Temp.*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[SteadyShot]` (Movie) `[Active]` Mode Angle-of-View Crop & 3 Hard Cutoffs (`119.88p/100p`, S&Q `>=120fps/100fps`, HDMI `RAW Output`)

1. **`[Active]` vs `[Standard]` / `[Off]`**:
   - Selecting `[SteadyShot]` = **`[Active]`** provides enhanced gyro+IBIS electronic-optical stabilization with a **narrower angle of view** (`~1.1x` crop).
2. **Three Exact `[Active]` Disqualification Conditions**:
   - **Normal movie shooting**: `[Rec Frame Rate]` set to **`[119.88p]` / `[100p]`** or higher;
   - **Slow & Quick (`S&Q`) shooting**: `[Frame Rate]` set to **`[120fps]` / `[100fps]`** or higher (`120fps` / `200fps` / `240fps`);
   - **External RAW Output**: while outputting **RAW movies** via `[HDMI Output Settings]` (`[RAW Output]` = `[On]`), `[Active]` SteadyShot cannot be used.

---

## 2. `[Clear Image Zoom]` / `[Digital Zoom]` (`[Zoom Range]`) Frame-Rate/RAW Cutoffs & AF/Metering/Tracking Locks

1. **Unavailable Modes**:
   - `Smart Zoom`, `Clear Image Zoom`, and `Digital Zoom` are **unavailable** when `[File Format]` is `RAW` / `RAW & JPEG` / `RAW & HEIF`, Normal `[Rec Frame Rate]` is `[119.88p]` / `[100p]`, or S&Q `[Frame Rate]` is `[120fps]` / `[100fps]` or `[240fps]` / `[200fps]`.
2. **Four Automatic Camera State Locks Beyond Optical Zoom**:
   - **`[Focus Area]`** setting is **disabled** (AF operates with priority on and around the center area);
   - **`[Metering Mode]`** is hard-locked to **`[Multi]`**;
   - **`[Face/Eye Prior. in AF]`** and **`[Face Priority in Multi Metering]`** are **unavailable**;
   - **Real-time Tracking** function is **unavailable**.

---

## 3. `[Power Setting Option]` (`[Power Save Start Time]` Default `5 Min` 9-Condition Bypass & `[Auto Power OFF Temp.]` Tripod Interlock)

1. **Exact Menu String & 9 Automatic Deactivation Conditions (`[Power Save Start Time]`)**:
   - Spelled in full on `ILME-FX3` (`MENU` -> `Setup` -> `[Power Setting Option]` -> **`[Power Save Start Time]`**, default **`5 Min`**).
   - Automatically **deactivated** during: (1) USB power supply, (2) slideshow playback, (3) FTP transfer, (4) movie recording, (5) computer connection, (6) TV / HDMI connection, (7) `[IR Remote Ctrl]` = `[On]`, (8) `[Bluetooth Rmt Ctrl]` = `[On]`, and (9) streaming or Creators' Cloud upload.
   - **Tier-0 Backup Implication**: During air-gapped internal-battery (`NP-FZ100`, no USB/HDMI/FTP/Remote) preflight or `75 MiB` `p3` cold dumps, `[Power Save Start Time]` must be set to `[Off]` or `[30 Min]` so an idle `5 Min` sleep timer never interrupts card operations.
2. **`[Auto Power OFF Temp.]` (`[Standard]` Default vs `[High]` Tripod Requirement)**:
   - Setting `[Auto Power OFF Temp.]` = **`[High]`** raises the thermal auto-shutdown threshold above `[Standard]`, **mandating tripod mounting** (prohibiting prolonged hand-held operation due to low-temperature burn hazard) and coupling with `[Fan Control]` thermal protection.
