# Global Sony Real-Hardware Intelligence — Wave 29 (`ILME-FX3 Ver. 7.02` `File Settings` 37-Char & SDHC Lock + `Shot Mark1/2`, `TC Regenerate` Slot-1 & `EXT-LK` Release, and `REC Lamp` Coupled Rear+Top Tally)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *File Settings*, *Title Name Settings*, *Add Shot Mark1/2*, *Image Jump Setting*, *TC/UB — Time Code Make*, *Matching the time code with other devices*, *HDMI Output Settings — Time Code Output*, *REC Lamp*, *Audio signals*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[File Settings]` (`Cam ID + Reel#` / 37-Char `Title Name` / SDHC `[Standard]` Lock) & `Shot Mark1/2` XML Sidecar Vault

1. **5-Mode `[File Name Format]` & `[File Number]` (`Series` / `Reset`)**:
   - Applies across both Slot 1 and Slot 2: `[Standard]` (`C0001`), `[Cam ID + Reel#]`, `[Title]`, `[Date + Title]`, `[Title + Date]`, paired with `[File Number]` (`[Series]` persistent counter across card swaps vs `[Reset]` per card, plus `[Series Counter Reset]`).
   - **`[Title Name Settings]`**: Maximum **37 ASCII characters** (`A–Z`, `a–z`, `0–9`, and `. - _ @ ! # $ % + = ^ ~ ( ) , ; [ ]`; default `C`), applied strictly to clips recorded *after* configuration.
   - **SDHC Hardware/Filesystem Lock**: Inserting an **SDHC** card (`<=32 GB` FAT32, vs SDXC/CFexpress Type A exFAT) **force-locks `[File Name Format]` to `[Standard]`**, and movie folder names cannot be customized.
2. **`[Shot Mark]` (`Shot Mark1` / `Shot Mark2`) Recording, Playback & FTP Filter**:
   - Recorded live via `[Add Shot Mark1]` / `[Add Shot Mark2]` custom keys or toggled post-take via `[Add/Delete Shot Mark1]` / `[Add/Delete Shot Mark2]` in `M4ROOT/CLIP/*M01.XML` non-real-time metadata.
   - Drives `[Image Jump Setting]` (`Shot Mark Only`, `Shot Mark1 Only`, `Shot Mark2 Only`, `No Shot Mark`) and `[Select on Cam & Send]` / `[FTP Transfer]` `[Target Movie]` = `[Only Shot Mark Mov.]` / `[Only Shot Mark]`.

---

## 2. `[TC/UB]` (`[Time Code Make]`: `Regenerate` Slot-1 Master Read, Forced `Rec Run`, `EXT-LK` Release & S&Q HDMI `Time Code Output` Block)

1. **`[Regenerate]` Slot-1 Source & Forced `[Rec Run]`**:
   - `[Time Code Make]` = `[Regenerate]` reads the ending timecode of the previous clip on the active `[Recording Media]` card and continues sequentially, **forcing advancement in `[Rec Run]` mode regardless of `[Time Code Run]`**.
   - When `[Recording Media]` = **`[Simult. Recording]`**, `[Regenerate]` reads the reference last timecode **exclusively from Slot 1**.
2. **`VMC-BNCM1` `EXT-LK` Release Condition & S&Q Lockout**:
   - External TC jam-sync (`EXT-LK` via `VMC-BNCM1` on body Multi/Micro USB) requires `[Movie]` mode + `[Time Code Make]` = **`[Preset]`** + `[Time Code Run]` = **`[Free Run]`**; changing `[Time Code Make]` (e.g. to `Regenerate`) or `[Time Code Run]` **immediately drops `EXT-LK` external lock**.
   - During **Slow & Quick (`S&Q`)** shooting, both `[Time Code Run]` and HDMI `[Time Code Output]` (`[On]`/`[Off]`, digital HDMI packet stream, default `Off`) are **unavailable**.

---

## 3. Physical `[REC Lamp]` 3-State Coupled Rear+Top-REC-Button Tally & `[Silent Mode]` -> `[Audio signals]` Lock

1. **Coupled Rear + Top `REC` Button Tally Topology (`All On` / `Only Front Off` / `All Off`)**:
   - Unlike cinema bodies with independent front/rear/handle tally switches, `ILME-FX3` `[REC Lamp]` (`MENU` -> `Setup` -> `[Setup Option]` -> `[REC Lamp]`) exposes strictly **`[All On]`**, **`[Only Front Off]`**, and **`[All Off]`**.
   - Hardware coupling rule: the **top `REC` button lamp lights in lockstep with the rear recording lamp** (`[Only Front Off]` disables only the front tally LED to prevent glass reflections while keeping BOTH rear + top `REC` button LEDs active; `[All Off]` extinguishes all physical LEDs while `[Emphasized REC Display]` red OSD frame remains independent and outputs to HDMI when `[HDMI Info. Display]` = `[On]`).
2. **`[Silent Mode]` -> `[Audio signals]` Hard `[Off]` Lock**:
   - Enabling `[Silent Mode]` = `[On]` **locks `[Audio signals]` (`MENU` -> `Setup` -> `[Sound Option]`) to `[Off]`**, silencing AF lock and self-timer countdown beeps.
