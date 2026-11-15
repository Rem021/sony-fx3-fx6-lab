# Global Sony Real-Hardware Intelligence — Wave 37 (`ILME-FX3 Ver. 7.02` `Framing Settings` `Crop`/`Full` Routing, `USB Power Supply` Mandatory `NP-FZ100` Battery & `USB LUN Setting` `Multi`/`Single` Survival, and `Anti-flicker Shoot.` Mechanical-Still-Only vs No `Var. Shutter`)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Framing shooting using remote shooting (Framing Settings)*, *USB Power Supply*, *USB LUN Setting*, *Connecting the camera to a computer*, *Anti-flicker Shoot.*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Framing Settings]` (`Monitor & Control` Remote Crop vs Full Routing — Distinct from `ZV-E1` `[Autoframing Settings]`)

1. **Exact `ILME-FX3` (`ilc/2210`) Menu Path, Defaults & Reset Behavior**:
   - `MENU` -> `Shooting` -> **`[Framing Settings]`** (controlled on-camera or remotely via Sony *Monitor & Control*):
     - **`[Framing]`**: **`[Off]`** (default) / **`[On]`** — **resettable** via `[Camera Settings Reset]`;
     - **`[Recording/Streaming]`**: **`[Full]`** (default) / **`[Crop]`** — **resettable** via `[Camera Settings Reset]`;
     - **`[HDMI]`**: **`[Crop]`** (default) / **`[Full]`** — **resettable** via `[Camera Settings Reset]`.
2. **Dual-Stream Output Asymmetric Default & Model-Exact Naming**:
   - Notice the factory asymmetric split when `[Framing]` = `[On]`: internal memory-card **`[Recording/Streaming]`** defaults to **`[Full]`** (preserving full-frame master capture) while **`[HDMI]`** defaults to **`[Crop]`** (sending cropped framing to external HDMI monitoring).
   - Unlike consumer `ZV-E1` (`[Autoframing Settings]`), `ILME-FX3` (`ilc/2210`) exposes **`[Framing Settings]`** paired with *Monitor & Control*; HDMI RAW output cannot be combined with cropped `[Framing]` = `[On]`.

---

## 2. `[USB Power Supply]` (`NP-FZ100` Mandatory Insertion + `USB Type-C` Exclusivity) & `[USB LUN Setting]` (`[Multi]` vs `[Single]`) Setup Persistence

1. **Non-Resettable `[Setup]` -> `[USB]` Persistence**:
   - Per `List of default setting values`, all `[Setup]` -> `[USB]` items (**`[USB Connection Mode]`** = `Sel. When Connect`, **`[USB LUN Setting]`** = `Multi`, **`[USB Power Supply]`** = `On`) **survive `[Camera Settings Reset]`** and are restored to defaults **only** by `[Initialize]`.
2. **`[USB Power Supply]` Two Hardware Power Interlocks**:
   - **Mandatory Inserted Battery Pack**: *\"Turning the camera on without a battery pack inserted is unavailable. Insert the battery pack into the product to supply power via USB cable. Do not remove the battery pack while power is supplied from a wall outlet; if removed, the camera will turn off.\"* Even under USB PD wall power (`[USB Power Supply]` = `[On]`), removing the `NP-FZ100` battery pack causes an immediate unbuffered power-off (unless a `DC-C1` DC coupler occupies the battery bay).
   - **`USB Type-C` vs `Multi/Micro USB` Hardware Split**: `ILME-FX3` **cannot** be powered or charged via the **`Multi/Micro USB`** terminal; USB power delivery and internal battery charging operate **exclusively** over the **`USB Type-C`** port.
3. **`[USB LUN Setting]` (`[Multi]` vs `[Single]`) Dual-Slot Visibility**:
   - Under `[MassStorage(MSC)]`, **`[Multi]`** (default) exposes both Slot 1 and Slot 2 logical units, whereas **`[Single]`** restricts USB enumeration to a single primary slot for legacy host compatibility. On our lab bench, live host USB connection remains hard-blocked (`physical_usb_packets_emitted == 0`, `hardware_live_attachment_authorized == False`), using off-camera `WP`-locked SDXC readers for Tier-0 SHA-256 verification.

---

## 3. `[Anti-flicker Shoot.]` Mechanical-Still-Only Boundary & `ILME-FX3` Absence of `[Var. Shutter]`

1. **Mechanical-Shutter Still-Image Scope Only**:
   - `MENU` -> `Shooting` -> `[Shutter/Silent]` -> **`[Anti-flicker Shoot.]`**: **`[Off]`** (default) / **`[On]`** — **resettable** via `[Camera Settings Reset]`.
   - Detects `100 Hz` / `120 Hz` artificial lighting flicker **strictly during still-image shooting with the mechanical shutter**; it does **not** function during movie recording or when electronic shutter / `[Silent Mode]` = `[On]` is active.
2. **Model-Exact Absence of `[Var. Shutter]` on `ILME-FX3` (`ilc/2210`)**:
   - Unlike `ILME-FX30` (`ilc/2220`), `ILCE-6700` (`ilc/2320`), or `ILME-FX6` (`ECS` Extended Clear Scan), `ILME-FX3` (`ilc/2210` through `Ver. 7.02`) **does NOT implement `[Var. Shutter]` (high-resolution fractional variable shutter)** in its `[Shutter/Silent]` / `[Anti-flicker]` menu tree; firmware/UI validators must never assume `FX30` `[Var. Shutter]` or `FX6` `ECS` menu nodes exist natively on stock `ILME-FX3`.
