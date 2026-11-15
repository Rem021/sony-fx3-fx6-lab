# Global Sony Real-Hardware Intelligence — Wave 39 (`ILME-FX3 Ver. 7.02` `Display Quality` `Standard`/`High` Battery Drain & Setup Survival, `Bluetooth Rmt Ctrl` Infrared Lockout & `Reset Network Set.` Split, and `My Menu` / `Display From My Menu` Persistence)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Display Quality*, *Bluetooth Rmt Ctrl*, *Display From My Menu*, *My Menu Setting*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Display Quality]` (`[Standard]` Default vs `[High]` Battery Consumption & `[Setup]` Survival)

1. **Menu Path, Modes & Power Trade-Off**:
   - `MENU` -> `Setup` -> `[Monitor]` -> **`[Display Quality]`**:
     - **`[Standard]`** (factory default — standard live-view refresh/decimation power envelope);
     - **`[High]`** (high-resolution monitor rendering; Sony explicitly notes **`[High]` increases `NP-FZ100` battery consumption**).
2. **Reset Matrix & Tier-0 Bench Rule**:
   - **`[Display Quality]`** is **NOT reset** by `[Camera Settings Reset]` and **NOT reset** by `[Reset Network Set.]` — restored to `[Standard]` **only** by `[Initialize]`.
   - During internal-battery (`NP-FZ100`) Tier-0 `pnflasha`/`cnflasha` dumps, keeping `[Display Quality]` = `[Standard]` alongside `[Monitor Brightness]` = `[Manual]` (`0`) minimizes live-view SoC/panel current draw.

---

## 2. `[Bluetooth Rmt Ctrl]` (`[Off]` Default): Prerequisite `[Bluetooth Function]`, Infrared Remote Lockout & 3-Way Reset Split

1. **Menu Path, Prerequisites & Mutual Exclusion**:
   - `MENU` -> `Network` -> `[Bluetooth]` -> **`[Bluetooth Rmt Ctrl]`**: **`[Off]`** (default) / **`[On]`**.
   - **Radio Prerequisite**: Requires `[Bluetooth Function]` = `[On]` and `[Airplane Mode]` = `[Off]` (on our zero-RF bench posture `[Airplane Mode]` = `[On]` / `passive_tx_bytes_emitted == 0`, keeping `[Bluetooth Rmt Ctrl]` suppressed).
   - **Infrared Remote Commander Mutual Exclusion**: Sony explicitly documents that **an infrared remote commander cannot be used while `[Bluetooth Rmt Ctrl]` is set to `[On]`**.
2. **Exact 3-Reset Domain Split (`Camera Settings Reset` vs `Reset Network Set.` vs `Initialize`)**:
   - Unlike `[Setup]` or `[My Menu]` items, **`[Network]`** items such as `[Bluetooth Rmt Ctrl]` **survive `[Camera Settings Reset]`**, **ARE reset to `[Off]` by `[Reset Network Set.]`**, and **ARE reset to `[Off]` by `[Initialize]`**.

---

## 3. `[My Menu Setting]` & `[Display From My Menu]` (`[Off]` Default): 6 Sub-Operations & Non-Resettable Persistence

1. **Menu Path & Sub-Options**:
   - `MENU` -> `My Menu` -> **`[My Menu Setting]`**:
     - `Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, and **`[Display From My Menu]`** (`[Off]` default — opens most recently displayed menu tab when pressing `MENU`; `[On]` — opens `My Menu` first when pressing `MENU`).
2. **Reset Survival & `CAMSET` Round-Trip**:
   - **`[Display From My Menu]`** and registered `My Menu` pages **survive both `[Camera Settings Reset]` and `[Reset Network Set.]`**, clearing only via `[Delete All]` / `[Delete Page]` or full **`[Initialize]`** (and round-tripping cleanly through `ILME-FX3` `CAMSET01.DAT` `[Save/Load Settings]`).
