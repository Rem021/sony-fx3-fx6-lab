# Global Sony Real-Hardware Intelligence — Wave 32 (`ILME-FX3 Ver. 7.02` `[Mode Settings]` `Fixed/Variable` FPS vs `S&Q Settings` Lockouts, `Zebra`/`Peaking` Non-Resettable Persistence & HDMI Overlay Isolation, `Audio Out Timing` `Live`/`Lip Sync`, and `MENU + Delete` 2s / `Full Format` Tier-0 Vault Guardrail)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *S&Q Settings*, *Mode Settings / FPS (Ver. 7.00 or later)*, *Proxy Settings*, *Zebra Display*, *Peaking Display*, *Audio Out Timing*, *Format (Quick formatting & Full formatting)*, *Resetting to default settings*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. Ver. 7.00+/7.02 `[Mode Settings]` (`[Fixed/Variable]`) vs `[S&Q Settings]` & 6 Hardware S&Q Lockouts

1. **Ver. 7.00+/7.02 `[Mode Settings]` (`[Fixed/Variable]`) Menu Lock**:
   - On `ILME-FX3` System Software `Ver. 7.00` / `7.02`, when `[Mode Settings]` (`S&Q Mode Settings`) is set to **`[Fixed/Variable]`**, legacy `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> **`[S&Q Settings]`** is **unavailable/locked**; capture frame rate is controlled directly via **`[FPS]`** (including Big6 `Home (FPS)`), while codec/bit-rate follow `[Movie Settings]` and `[File Format]`.
2. **Six Hard S&Q Recording Disqualifications**:
   - **Zero Audio Capture**: Sound is **not recorded** (`0ch`) during S&Q motion recording.
   - **`[Audio Out Timing]` Disabled**: `MENU` -> `Shooting` -> `[Audio Recording]` -> `[Audio Out Timing]` (`[Live]` default zero-delay vs `[Lip Sync]` video-aligned) cannot be used during S&Q shooting.
   - **Timecode Freeze/Drop**: Both **`[Time Code Run]`** and **`[Time Code Output]`** are unavailable during S&Q recording.
   - **`240fps` / `200fps` 4K Block**: `[240fps]` (NTSC) / `[200fps]` (PAL) **cannot be selected** when `[File Format]` is `XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`, or `XAVC S-I DCI 4K` (requires HD `XAVC S HD` / `XAVC S-I HD`).
   - **`120fps` / `100fps` DCI 4K Block**: `[120fps]` (NTSC) / `[100fps]` (PAL) **cannot be selected** when `[File Format]` is **`XAVC S-I DCI 4K`** (`4096x2160`).
   - **Proxy (`Px`) S&Q Cutoff**: Simultaneous `[Proxy Recording]` (`XAVC HS HD` `16M/9M 4:2:0 10bit` or `XAVC S HD` `6M 4:2:0 8bit`) is **blocked** in S&Q whenever `[Rec Frame Rate]` is `[119.88p]`/`[100p]` OR shooting `[Frame Rate]` is `[120fps]`/`[100fps]` or higher.

---

## 2. `[Zebra Display]` Non-Resettable Persistence (`[Camera Settings Reset]` Survival) & `[Zebra]` + `[Peaking]` Strict HDMI Clean-Feed Isolation

1. **`[Zebra Display]` & `[Zebra Level]` Survive `[Camera Settings Reset]`**:
   - `MENU` -> `Exposure/Color` -> `[Zebra Display]`:
     - `[Zebra Display]` (`[Off]` default / `[On]`, mapped to Control Wheel Left `[Zebra Display Select]` by default) and `[Zebra Level]` (`[70]` default, `75`, `80`, `85`, `90`, `95`, `100`, `100+`, plus `[Custom 1]` Standard+Range correct-exposure band and `[Custom 2]` Minimum/Lower-Limit overexposure threshold) are **NOT reset** by `[Camera Settings Reset]` — only `[Initialize]` clears them back to `Off` / `70`.
2. **Hardware HDMI Assist-Overlay Suppression (`Zebra` & `Peaking` Local-LCD-Only Rule)**:
   - Even when `[HDMI Info. Display]` is `[On]`, **neither Zebra stripes nor Peaking outlines** (`MENU` -> `Focus` -> `[Peaking Display]`: `On/Off` default `Off`, `Peaking Level` `High/Mid/Low` default `Mid`, `Peaking Color` `Red/Yellow/Blue/White` default `White`, Control Wheel Right `[Peaking Display Select]`) are ever rendered onto the HDMI output signal (*"The zebra pattern is not displayed on devices connected via HDMI"* / *"The outline of in-focus ranges is not enhanced on devices connected via HDMI"*).
   - This guarantees external HDMI recorders/monitors never suffer baked-in focus-peaking halos or zebra stripes, whereas operator exposure/focus assist overlays remain strictly confined to the camera's local LCD panel (`fb0`/OSD plane).

---

## 3. `[Format]` (`Quick Format` vs `(Delete)`-Toggled `Full Format`) & `MENU + (Delete)` 2-Second Chord Vault Guardrail

1. **Quick Formatting vs Full Formatting (`(Delete)` Key Toggle)**:
   - Opening `MENU` -> `Shooting` -> `[Media]` -> `[Format]` -> Slot `1`/`2`:
     - Selecting `[Enter]` directly executes **Quick Format** (reinitializes filesystem management metadata only).
     - Pressing the **`(Delete)`** button on the confirmation dialog switches to **Full Format**, initializing **all data blocks** across the CFexpress Type A / SDXC card in addition to management metadata (restoring degraded card write speed and permanently wiping residual sectors).
     - Canceling Full Format mid-process leaves previously stored data **erased** while keeping the card formatted and immediately usable.
2. **Physical `MENU + (Delete)` (~2s) Direct Format Chord Lockout for Tier-0 Vaults**:
   - Holding **`MENU` + `(Delete)`** simultaneously for **~2 seconds** on the shooting screen jumps straight into the `[Format]` confirmation dialog.
   - **Mandatory Tier-0 Bench Safety Gate (`G84` / Pillar `34`)**: While Slot 1 holds an unverified or active Tier-0 read-only eMMC/NOR dump (`pnflasha` / `cnflasha` / `CAMSET01.DAT` golden recovery vault), both `MENU` -> `[Format]` (Quick & `(Delete)` Full Format) and the `MENU + (Delete)` 2-second hardware button chord must be treated as **hard-locked destructive operations** until off-camera SHA-256 vault verification completes and the physical SDXC WP switch (or read-only vault card swap) is engaged.
