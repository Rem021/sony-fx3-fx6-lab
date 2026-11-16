# Global Sony Real-Hardware Intelligence — Wave 34 (`ILME-FX3 Ver. 7.02` `Recover Image DB` Depleted-Battery Block & Read-Only Tier-0 Vault Guard, `Monitor Flip Direction` Non-Resettable Persistence & `Horizontal Flip` Playback Non-Inversion, and `AF Transition Speed` / `AF Subj. Shift Sensitivity` + `Interval Shoot Func.` Still-Only Boundary)

- **Date**: `2026-11-15`
- **Target Hardware Baseline**: Sony `ILME-FX3` (`Ver. 7.02`, `Linux 4.9.337-scel+`) vs `ILME-FX6` (`Ver. 6.01`)
- **Authoritative Primary Sources**: Official Sony `ILME-FX3` Help Guide (`helpguide.sony.net/ilc/2210/v1/en/` — *Recover Image DB (still image/movie)*, *Warning messages*, *Number of recordable images*, *Monitor Flip Direction*, *AF Transition Speed*, *AF Subj. Shift Sensitivity*, *Interval Shoot Func.*, *List of default setting values*)
- **Hardware Safety Posture**: Strictly `O_RDONLY` local donor analysis & synthetic clean-room parity (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`).

---

## 1. `[Recover Image DB]` (`MENU` -> `Shooting` -> `[Media]` -> `[Recover Image DB]`): Depleted-Battery Refusal, Non-Deleting Repair & Read-Only Tier-0 Vault Guard

1. **Non-Deleting Database Repair & Depleted-Battery Hardware Block**:
   - Repairs `AVF_INFO` / media management database inconsistencies after host computer file transfers (`"Image DataBase File error"` or false `"0"` recordable images) **without deleting recorded clips/stills**.
   - **Depleted-Battery Interlock**: *"If the battery pack is extremely depleted, image database files cannot be repaired. Use a sufficiently charged battery pack."* Attempting `[Recover Image DB]` on an exhausted `NP-FZ100` pack is hardware-refused to prevent mid-journal FAT/exFAT metadata corruption.
   - **Action Item Immunity**: Not reset by either `[Camera Settings Reset]` or `[Initialize]`.
2. **Tier-0 Vault Read-Only Mutation Firewall (`Pillar 36` / `G87`)**:
   - Because `[Recover Image DB]` **writes repaired database index files onto the target memory card**, executing `[Recover Image DB]` on an unverified Slot 1 Tier-0 dump card (`pnflasha` / `cnflasha` / `CAMSET01.DAT`) mutates card filesystem sectors prior to off-camera forensic hashing.
   - Therefore, Slot 1 Tier-0 vault protocol must block `[Recover Image DB]` until off-camera SHA-256 verification succeeds and physical SDXC write-protect (`WP`) is engaged.

---

## 2. `[Monitor Flip Direction]` (`Auto` Default): `[Camera Settings Reset]` Survival & `[Horizontal Flip]` Playback Non-Inversion

1. **Menu Path & Values**:
   - `MENU` -> `Setup` -> `[Monitor]` -> **`[Monitor Flip Direction]`**: `[Auto]` (default, hinge/orientation sensor driven), `[Horizontal Flip]`, `[Vertical Flip]`, `[Off]`.
2. **Two Exact Hardware Invariants**:
   - **Survives `[Camera Settings Reset]`**: Listed under Setup items **not reset** by `[Camera Settings Reset]` (restored to `Auto` only by `[Initialize]`).
   - **Playback Non-Inversion Under `[Horizontal Flip]`**: Even when `[Monitor Flip Direction]` is explicitly set to **`[Horizontal Flip]`**, **the monitor display direction during playback is NOT inverted** (*"Even if set to [Horizontal Flip], the monitor display direction during playback will not be inverted"*), preventing mirror-reversed timecode/clip-name text inspection during on-set playback review.

---

## 3. Movie/S&Q AF Kinematics (`[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sensitivity]` `1..5`) vs Still-Only `[Interval Shoot Func.]`

1. **Exact `ILME-FX3` Menu Spellings, Ranges & Reset Behavior**:
   - **`[AF Transition Speed]`** (`MENU` -> `Focus` -> `[AF/MF]` -> `[AF Transition Speed]`): **`1 (Slow)` .. `7 (Fast)`**, default **`5`**, movie & S&Q scoped, **resettable** via `[Camera Settings Reset]`.
   - **`[AF Subj. Shift Sensitivity]`** (`MENU` -> `Focus` -> `[AF/MF]` -> `[AF Subj. Shift Sensitivity]` — spelled in full *Sensitivity*, not abbreviated *Sens.*): **`1(Locked on)` .. `5(Responsive)`**, default **`5(Responsive)`**, movie & S&Q scoped, **resettable** via `[Camera Settings Reset]`.
2. **`[Interval Shoot Func.]` Still-Image-Only Recording Scope**:
   - `MENU` -> `Shooting` -> `[Drive Mode]` -> **`[Interval Shoot Func.]`** (`Shooting Start Time` `1s..99m59s`, `Shooting Interval` `1s..60s`, `Number of Shots`): captures a **sequence of still images** (requiring external *Imaging Edge Desktop (Viewer)* to assemble time-lapse movies), contrasting with `ILME-FX6` in-camera `Interval Rec` video frame-burst MXF/MP4 recording.
