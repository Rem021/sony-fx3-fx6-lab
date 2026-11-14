# Phase 17 Audit: FX3 Physical Input, Display Routing & Digital Audio Handle Compatibility

**Date**: 2026-11-14  
**Phase / Agent**: Phase 17 — Hydrogen-3 (`FX6-on-FX3` Stage-A Compatibility Closure)  
**Architecture Baseline**: Stage-A (`Stock-CP` unmodified `p8:/cpapp-b.bin` & kernel; userland adapted FX6 `6.01` `im.elf` + `appFw.so` + `libInfra*.so` + RAM-Shadow `BK4\0`)  
**Terminology Note**: ABI compatibility verification, input keymap translation adapter (`P10`), and graceful peripheral fallback auditing.

---

## 1. Executive Summary

| Domain | Compatibility Verdict | Key Finding | Adaptation / Contract | Unicorn AArch64 Proof |
| :--- | :--- | :--- | :--- | :--- |
| **1A. Body Keys & Dials** (`InfraInput` ↔ `appFw.so`) | **Pass with P10** | `15` core FX3 inputs (`D-pad`, `ENTER`, `MENU` short/long `>=1000ms`, `REC`, `POWER`, `C5/C6`, Front/Rear dials, vari-angle LCD sensors) map `1:1`; `6` controls (`Fn`, `C1`, `C2`, `C3`, `PLAY`, `DELETE`) hit unmapped FX6 dispatch slots | **P10 Keymap Translation Adapter**: `24 B` across 6 `PF_R` `.rodata` slots (`0x2245a10` table); 0 `.text` edits; byte-exact SHA-256 rollback | `appFw.so` real C++ `std::unordered_map` ctor (`0xc0b778`) + lookup (`0xc0b6e8`): `Fn`: `0x8d -> 0x184` (`HOME`), `C1->0x29`, `C2->0x192`, `C3->0x199`, `PLAY->0x183`, `DELETE->0x185` |
| **1B. Touch Panel** (`libInfraTp.so` vs FX3 `libObj.so`) | **Native 1:1 Pass** | Shared UIPC queue `0x807b002b`, `/dev/tp`, `InfraTPUIPCDataRecord`, and identical `0x007a0001` `BIN!` modes `3..6` (`528 / 336 / 496 / 32 B`) | Zero binary patching required; coordinates bound via `SetTpSize` | `libInfraTp.so` `_ZN7InfraTp9SetTpSizeEii` (`0x55b8`): `(1024,540) -> rc=1`, `(0,540) -> rc=0`, `(640,-1) -> rc=0` |
| **2. Display & HDMI Routing** (`LCD` / `HDMI` vs absent `EVF`/`SDI`) | **Pass with RAM-Shadow BK4** | `0x02cf0214`/`0x02cf0218` differ (`1 B` enum in FX6 vs `4 B` repeated in FX3), already normalized by RAM-Shadow `BK4\0`; `appFw.so` explicitly gates SDI (`SDI_OUTPUT_NOT_SUPPORT`); vari-angle sensors (`0x71c3..0x71c5`) active; `GpeInit` + `SeqQueueDispSwitch` / `SeqQueueHdmiConnect` intact | Zero additional binary patch needed; relies on RAM-Shadow `BK4\0` + `P5` (`0x032d`) | `AVBB_SCN_START_PANELEVF.so` `_Z12GetOutputSelhPh` (`0x173c`): `sel {1,3,4} -> out=1 (LCD)`, `{2,5} -> out=2 (EVF)`, `16 -> out=3 (Mirror)`, invalid `-> rc=0` |
| **3. Audio & MI Hotshoe** (`XLR-H1` vs FX6 Handle) | **Pass with P5 (`0x032d`)** | `EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON` (`XLR-H1` 4ch/2ch digital MI audio) is natively present in both FX3 & FX6; FX6 handle dials `CH1..4` (`0x7124..0x7127`) are purely event-driven (`ev_rep/off == NULL`); hotshoe IPC waits use bounded `osal_rcv_msg_tmo` | No blocking boot wait on missing FX6 handle; relies on existing `P5` (`0x032d` CAPID preinit reply on `0x92840747`) | `libInfraHotshoe.so` `WaitRecvCompMsgFromHotshoeRsrc` (`0x5d90`): `osal_rc=0 -> rc=0` (freed msg), `osal_rc=-50 (E_TMO) -> rc=0x8000` (graceful timeout) |

---

## 2. Pinned Read-Only Donor Integrity Inventory (FX6 6.01)

| Artifact | Size (Bytes) | SHA-256 Digest | Role |
| :--- | :---: | :--- | :--- |
| `appFw.so` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | Core UI/Input/Display/Audio event & sequence engine |
| `libInfraInput.so` | `93,448` | `1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02` | Physical input UIPC forwarder (`0x807a0020 -> 0x005503e0`) |
| `libInfraTp.so` | `47,776` | `ea1c123412fc048d93bd7492bdcc59a7fab0d472c895b73a60d463d5fafe8652` | Capacitive touch driver IPC (`0x807b002b`, `/dev/tp`) |
| `libInfraHotshoe.so` | `47,808` | `0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6` | MI hotshoe IPC manager & bounded wait handlers |
| `libgpe.so` | `106,520` | `4541f6e22d7c598c3eacedee553015fb12dc35d5068e1f76cddc07dd82cfd79d` | `GPE0` OSD compositing & `GpeInit` engine |
| `AVBB_SCN_START_PANELEVF.so` | `275,968` | `36d98e83611f3e26c7db4d84a7e045fceafc370470744352598db62f54b09b2b` | Panel/EVF display routing & brightness/VDF scenarios |
| `AVBB_SCN_START_AUDIO.so` | `70,096` | `96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a` | Audio ADF path & anti-clip setup scenarios |

---

## 3. Domain 1: Physical Input Keymap Translation (`P10`) & Touch Panel Audit

### 3.1 FX6 `appFw.so` Key Dispatch Pipeline
- **Table 1 (`infra_key_id -> app_key`)**: `0x2245a10 .. 0x2247ce8` (`PT_LOAD[0]` `PF_R`, `1,115` `<II` pairs, `1,109` unique `infra_key_id` keys). Loaded at boot by `0xb1a460` calling `0xc0b778` (`std::unordered_map<uint32_t, uint32_t>` at `0x303dad0`).
- **Reverse Table (`app_key -> infra_key_id`)**: Separate static array at `0x2247ce8 .. 0x2249f00` (`1,091` `<II` pairs), loaded into `0x303da98`. Because `0x2245a10` and `0x2247ce8` are disjoint, adapting `app_key` targets inside `0x2245a10` never corrupts reverse indexing.
- **Table 2 (`app_key -> (ev_on, ev_rep, ev_off)`)**: `PT_LOAD[1]` VMA `0x2ef2c08` (file offset `0x2ee2c08 .. 0x2ee3698`, `169` `<4I` dispatch entries), queried via `0xc0f0dc`.
- **Table 3 (Long-press table)**: `0x224e468` (`<6I` records, `threshold_ms = 1000`). Confirms FX3 **`MENU` (`0x01ab` -> `ak=0x13` -> `0x02010015`)** maps short-press (`Status`) and long-press `>= 1000 ms` (`0x02010017` `EVENT_INPUT_TACT_MENU_LONG_PRESS` -> Full 3-layer Menu) natively without modification.

### 3.2 Native 1:1 Controls vs Blind Spots & P10 Translation Spec (`24 B`, `PF_R` only)

| FX3 Physical Button | `infra_key_id` | Unpatched FX6 `app_key` | Unpatched `ev_on` | P10 Target `app_key` (File Offset) | Post-P10 FX6 Event (`ev_on`) | Engineering Purpose |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `POWER` / `UP` / `DOWN` / `LEFT` / `RIGHT` / `ENTER` | `0x0002`, `0x0003`, `0x0030`, `0x0015`, `0x01af`, `0x01ac` | `0x01, 0x02, 0x06, 0x04, 0x16, 0x14` | `0x02010098 .. 0x02010010` | *(unmodified)* | *(native 1:1)* | Full 5-way navigation & power |
| `MENU` (short / `>=1000ms` long) | `0x01ab` | `0x13` | `0x02010015` (long `0x02010017`) | *(unmodified)* | *(native 1:1)* | Status / Full 3-layer Menu |
| `REC` / `C5` / `C6` / Front & Rear Dials | `0x01f0`, `0x7049`, `0x704a`, `0x04000011`, `0x04000013` | `0x1c, 0x40, 0x41, 0x382, 0x383` | Active (`0x02010101`, `0x0201006a/c`, dials) | *(unmodified)* | *(native 1:1)* | Tally Rec, Assign5/6, Exposure/Iris dials |
| `Vari-angle LCD Sensors` | `0x71c3`, `0x71c4`, `0x71c5` | `0x1bb, 0x1bc, 0x1bd` | Active | *(unmodified)* | *(native 1:1)* | Flip-screen orientation & backlight |
| **`Fn`** | `0x7095` | `0x8d` | *Dropped (`None`)* | **`0x184`** (`@0x2245e7c`) | `0x020102d1` (`EVENT_INPUT_KEY_TACT_HOME_ON`) | **Opens Big6 Home Screen (`sid=0x0a`)** |
| **`C1`** | `0x0066` | `0x0e` | *Dropped (`None`)* | **`0x029`** (`@0x2245a84`) | `0x02010157` (`EVENT_INPUT_KEY_OTHER_KURU_PON_ON`) | Multi-selector / Big6 direct focus |
| **`C2`** | `0x70e7` | `0xdf` | *Dropped (`None`)* | **`0x192`** (`@0x224610c`) | `0x02010107` (`EVENT_INPUT_KEY_TACT_MENU_CANCEL_ON`) | **Cancel / Back out of menus & Big6** |
| **`C3`** | `0x70ec` | `0xe4` | *Dropped (`None`)* | **`0x199`** (`@0x2246134`) | `0x020100e6` (`EVENT_INPUT_KEY_TACT_DISP_SEL_ON`) | Clean feed / OSD overlay toggle |
| **`PLAY`** | `0x01f7` | `0x22` | *Dropped (`None`)* | **`0x183`** (`@0x2245b24`) | `0x020100e9` (`EVENT_INPUT_KEY_TACT_THUMBNAIL_ON`) | Enters Thumbnail / Playback mode |
| **`DELETE`** | `0x01f8` | `0x23` | *Dropped (`None`)* | **`0x185`** (`@0x2245b2c`) | `0x020102cb` (`EVENT_INPUT_KEY_TACT_USER_ON`) | Extra User-Assignable shortcut |

- **P10 Byte Summary**: `6` sites x `4 B` = **`24 B` total**, strictly within `PT_LOAD[0]` `PF_R` `.rodata`. Rollback restores the exact SHA-256 digest `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`.

### 3.3 Touch Panel (`libInfraTp.so` vs FX3 `libObj.so`)
- Both firmwares implement identical `[INFRATP] InfraTPUIPCDataRecord` IPC formatting over UIPC queue `0x807b002b` and kernel device `/dev/tp`, reading `BK4\0` property `0x007a0001` whose touch sub-tables (`BIN!` modes `3, 4, 5, 6` of sizes `528, 336, 496, 32 B`) match identically across FX6 (`CX95898_NTSC.bin`) and FX3 (`FX3-CX95900_ALLLANG-Backup.bin`).
- **Unicorn AArch64 (`_ZN7InfraTp9SetTpSizeEii` @ `0x55b8`, `8` words `0x7100003f..0xd65f03c0`)**:
  - `(1024, 540)` -> returns `w0 = 1`, stores `(1024, 540)` at `[x0 + 0x78]`.
  - `(0, 540)` and `(640, -1)` -> returns `w0 = 0`, preserves `[x0 + 0x78] == (0, 0)`.

---

## 4. Domain 2: Display Panel (`LCD` / `EVF`) & HDMI Routing Audit

- **NVRAM Schema Normalization (`0x02cf0214`, `0x02cf0218`)**: In FX6 `CX95898_NTSC.bin`, keys `0x02cf0214` and `0x02cf0218` are `1`-byte enumerations (`0x00`, `0x01`), whereas FX3 `FX3-CX95900_ALLLANG-Backup.bin` stores `4`-byte repeated bytes (`0x16161616`, `0x19191919`). Stage-A RAM-Shadow `BK4\0` synthesis normalizes these records into exact `1 B` FX6 format in RAM (`0` flash writes).
- **SDI Absence Guard (`Mew` FPGA absent on FX3)**: `appFw.so` `sequence/sequence_sdi1_sdi2_hdmi_connect.cpp` (`0x203c1ec..0x203c3fc`) handles `VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT` without stalling HDMI (`SeqQueueHdmiConnect`) or panel output (`SeqQueueDispSwitch`, `sequence/sequence_display_setup.cpp` @ `0x1d00b44` / `0x1d00d10`).
- **GPE0 OSD Layer**: `libgpe.so` exposes `GpeInit` (`0xe254`) and `gpe0_info` (`0x297e8`) for primary OSD compositing independent of SDI output routing.
- **Unicorn AArch64 (`AVBB_SCN_START_PANELEVF.so` `_Z12GetOutputSelhPh` @ `0x173c`, `22` words)**:
  - Selector `{1, 3, 4}` -> `rc = 1, *out = 1` (**Panel / LCD route**)
  - Selector `{2, 5}` -> `rc = 1, *out = 2` (**EVF route**)
  - Selector `{16}` -> `rc = 1, *out = 3` (**Simultaneous mirror**)
  - Selector `{0, 6..15, >=17}` -> `rc = 0, *out = 0` (**Safe invalid rejection**)

---

## 5. Domain 3: Audio Subsystem & MI Hotshoe (`XLR-H1` vs FX6 Handle) Audit

- **Digital MI Hotshoe Protocol Parity**: FX6 `appFw.so` natively includes `EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON` (`0x2745fe9`) and `VAL_connect_shoe_mic_CONNECT_SHOE_MIC_DIGITAL_XLR` (`0x26ba1da`) matching FX3 `XLR-H1` 24-bit 4ch/2ch MI digital audio protocol (`0x2108000` `INFRA_HOTSHOE_UIPC_SHOEINFO_EVT`).
- **Non-Blocking Absent Handle Behavior**: FX6 top-handle analog CH1..CH4 volume switches (`0x7124..0x7127` -> `app_key 0x11c..0x11f` -> `0x02010153..0x02010156`) have `ev_rep = 0x20000001` (`NULL`) and `ev_off = 0x20000001` (`NULL`) — strictly event-driven, never polled synchronously during startup. Pre-init audio synchronization remains handled by `P5` (`0x032d` -> `0x132d` CAPID reply on queue `0x92840747`).
- **Unicorn AArch64 (`libInfraHotshoe.so` `WaitRecvCompMsgFromHotshoeRsrc` @ `0x5d90`, `252 B`)**:
  - When `osal_rcv_msg_tmo@plt` (`0x2b30`) returns `0`: invokes `osal_free_msg@plt` (`0x2ed0`) and returns **`w0 = 0`**.
  - When `osal_rcv_msg_tmo@plt` returns timeout `E_TMO` (`-50`, simulating absent FX6 handle): logs `e:RCMHR_TMO` via `InfraDebugRecord@plt` (`0x2b70`) and returns **`w0 = 0x8000`** gracefully with zero assertions or hangs.

---

## 6. Dual-Mode Verification Runs

Executed all **18** `unittest` cases in [`test_phase17_peripheral_ux.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase17_peripheral_ux.py) against [`peripheral_ux_compatibility_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/peripheral_ux_compatibility_verifier.py):
1. **Local Read-Only Donor Mode (`LOCAL_DONOR_AND_UNICORN_VERIFIED`)**: `18/18` passed (`exit 0`).
2. **Clean-Room Synthetic Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `CLEAN_ROOM_SYNTHETIC_VERIFIED`)**: `18/18` passed (`exit 0`).
