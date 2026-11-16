# Global Sony Real-Hardware Intelligence — Wave 28 (`ILME-FX3 Ver. 7.02` HDMI Log `1080p` vs `Off(HDMI Only)` `4K 10-bit`, `Px` Proxy Coupled Vault, and `Focus Magnifier` × `Bright Monitoring` Interlocks)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *HDMI Output Settings (movie)*, *HDMI Info. Display*, *Proxy Settings*, *Focus Magnifier*, *Initial Focus Mag. (movie / still image)*, *Bright Monitoring*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[HDMI Output Settings]` (`Rec. Media dur HDMI Output`) & `[Log Shooting]` / `PPLUT1–PPLUT4` `1080p` Downshift vs `Off(HDMI Only)` `4K 10-bit`

1. **`[Rec. Media dur HDMI Output]` Dual Modes**:
   - **`[On]` (Default)**: Records to internal memory card(s) and outputs HDMI simultaneously; color depth tracks `[Record Setting]` under `[Movie Settings]`, and `[Output Resolution]` offers `[Auto]` / `[2160p]` / `[1080p]` / `[1080i]` (when `[RAW Output]` = `[Off]`).
   - **`[Off(HDMI Only)]`**: **Completely disables internal memory-card movie recording** and unlocks `[4K Output Set.(HDMI Only)]` (`[59.94p 10bit]`, `[50p 10bit]`, `[29.97p 10bit]`, `[25p 10bit]`, `[23.98p 10bit]`, `[24.00p 10bit]`).
2. **Critical `[Log Shooting]` / `PPLUT1–PPLUT4` `1080p` Downshift Trap**:
   - When `[Rec. Media dur HDMI Output]` = `[On]` (and `[RAW Output]` = `[Off]`), activating **`[Log Shooting]`** (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) OR selecting **`[Picture Profile]` = `PPLUT1`–`PPLUT4`** forces HDMI output resolution down to **`1080p` (`1920×1080`) regardless of `[Output Resolution]`** (`[2160p]` / `[Auto]`).
   - Full **4K (`3840×2160`)** HDMI output during `[Log Shooting]` or `PPLUT1–PPLUT4` requires either switching `[Rec. Media dur HDMI Output]` to **`[Off(HDMI Only)]`** (sacrificing internal card recording!) or enabling **`[RAW Output]` = `[On]`** (`4264×2408` 16-bit linear).
3. **`[HDMI Info. Display]` Blank-LCD & `[Off(HDMI Only)]` Auto-Suppression**:
   - Setting `[Rec. Media dur HDMI Output]` = `[Off(HDMI Only)]` or `[RAW Output]` = `[On]` **temporarily forces `[HDMI Info. Display]` to `[Off]`** and disables HDMI `[De-Squeeze Display]`.
   - Conversely, when `[HDMI Info. Display]` = `[On]` (with internal card recording `[On]` and `[RAW Output]` = `[Off]`), shooting overlays and `[Emphasized REC Display]` red tally border appear on the external HDMI monitor while **blanking the FX3's built-in LCD panel** (zero image/OSD on camera LCD).

---

## 2. `[Proxy Settings]` (`Px` Dual-Codec Matrix, `119.88p`/`100p` & `>=120fps` Cutoffs, and Atomic Main+Proxy Delete/Protect Vault)

1. **Exact FX3 `Ver. 7.02` Proxy Codec & Bitrate Table**:
   - **`[XAVC HS HD]`**: `1920×1080`, Max `59.94p` / `50p`, MPEG-H HEVC/H.265, **`16M 4:2:0 10bit`** or **`9M 4:2:0 10bit`** *(format default)*.
   - **`[XAVC S HD]`** *(overall `[Proxy File Format]` default)*: `1280×720`, Max `59.94p` / `50p`, MPEG-4 AVC/H.264, **`6M 4:2:0 8bit`** only.
2. **Hard Frame-Rate & S&Q Cutoffs**:
   - Normal movie mode: `[Proxy Recording]` is **unavailable** when `[Rec Frame Rate]` is `[119.88p]` or `[100p]`.
   - Slow & Quick (`S&Q`) mode: `[Proxy Recording]` is **unavailable** when `[Rec Frame Rate]` is `[119.88p]` / `[100p]` OR when sensor `[Frame Rate]` is **`[120fps]` / `[100fps]` or higher** (`120fps` / `200fps` / `240fps`), and produces zero internal card files when `[Rec. Media dur HDMI Output]` = `[Off(HDMI Only)]`.
3. **Playback Exclusion & Atomic Coupled Delete/Protect Vault**:
   - Proxy `.MP4` files (`M4ROOT/SUB/`) **cannot be played back on the FX3** and are hidden from single-image/index playback screens; only the `(Px)` badge appears on the paired original clip (`M4ROOT/CLIP/`).
   - **Atomic Coupled Vault Rule**: In-camera **Delete** or **Protect** on a `(Px)` movie **atomically deletes or protects BOTH the original clip and its proxy clip**. Single-sided in-camera deletion/protection of only original or only proxy is impossible; backup/recovery vaults must preserve coupled `CLIP/` + `SUB/` pair integrity and detect orphaned proxy/main pairs.

---

## 3. `[Focus Magnifier]` (`x1.0`/`x4.0` Movie Scale) × `[Auto Magnifier in MF]` × `[Bright Monitoring]` Mutual Exclusion

1. **Movie vs Still Magnification Scales & `[Marker Display]` Suppression**:
   - **`[Initial Focus Mag.]` (movie)**: Strictly **`x1.0`** *(default)* or **`x4.0`** (`Focus Magnif. Time`: `2 Sec` / `5 Sec` / `No Limit` *[default]*).
   - **`[Initial Focus Mag.]` (still image)**: Full-Frame `x1.0` / `x2.1`; APS-C / Super 35mm `x1.0` / `x1.5`.
   - **`[Auto Magnifier in MF]`** (focus-ring triggered) is **disabled during movie shooting**; operators must invoke `[Focus Magnifier]` explicitly (e.g. Custom button 5 / `FOCUS MAG`), during which **`[Marker Display]` cannot be displayed**.
2. **`[Bright Monitoring]` MF + `P/A/S/M` Lock & Mutual Exclusion with Magnification**:
   - While `[Focus Magnifier]` or `[Auto Magnifier in MF]` is active, pressing the `[Bright Monitoring]` custom key **cannot turn `[Bright Monitoring]` on or off** (hard key-toggle lockout in `Ver. 2.00+` / `7.02`).
   - `[Bright Monitoring]` automatically forces `[Live View Display]` to **`[Setting Effect OFF]`** and is **automatically canceled** on camera power-off, leaving `P/A/S/M` exposure modes, or switching `[Focus Mode]` away from `Manual Focus (MF)`.
