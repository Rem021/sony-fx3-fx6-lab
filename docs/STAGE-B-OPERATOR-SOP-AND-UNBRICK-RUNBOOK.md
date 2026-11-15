# Stage-B Field Operator SOP, Rig Electrical Safety & Unbrick Runbook (`EN / 简体中文`)

> **Document Scope / 文档定位**: Authoritative field & bench safety Standard Operating Procedure (SOP) for **Milestone Phase 110 Stage-B (`P1..P12+Fan`, `G01..G32`, `10-Pillar Recovery` / `Tier-0..Tier-4`)** targeting **Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** with **ILME-FX6 (`Ver. 6.01`)** volatile RAM-overlay compatibility.  
> **Companion Documents / 配套文档**: [`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`](./STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [`docs/STAGE-A-HARDWARE-RUNBOOK.md`](./STAGE-A-HARDWARE-RUNBOOK.md) · [`docs/BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) · [`README.md`](../README.md)  
> **Quick Verification Gates / 快速门禁指令**: `make verify-rp2040-fixture` · `make verify-24-gates` · `make verify-32-gates` · `make verify-10pillar-recovery` · `make verify-tier0-backup` · `make verify-antirollback-guard` · `make verify-init2-escape` · `make verify-post-trial-audit` · `make verify-milestone-90` · `make verify-milestone-110`

> [!CAUTION]
> **HARD-LOCKED FLASH POSTURE / 硬件写入硬锁红线 (`persistent_emmc_writes_authorized = False`)**
> - `persistent_emmc_writes_authorized = False` · `persistent_write_release = False` · `allow_boot_partition_targeting = False` · `allow_destructive_fastboot = False` · `hardware_live_attachment_authorized = False`
> - `sector0_mutation_bytes = 0` · `wbi_mutation_bytes = 0` (`p5:/wbi` blocked) · `cp_mutation_bytes = 0` (`p8:/cpapp-b.bin` untouched) · `calibration_mutation_bytes = 0` (`C2PA 2.1` / `cnflasha` untouched) · `otp_fuse_touches = 0` · `rpmb_counter_increments = 0` · `passive_tx_bytes_emitted = 0`
> - **NEVER** attach an unverified `3.3V` push-pull UART adapter or standard Raspberry Pi Pico to the FX3 Multi-Port (`Gate G13`), **NEVER** transmit UART TX bytes on passive `1.8V` capture probes (`tx_bytes = 0`), **NEVER** run an unisolated V-Mount D-Tap + copper HDMI Type-A rig with loose ground (`Gate G19`), **NEVER** run battery-less `USB-PD` recording (`Gate G20`), **NEVER** hot-plug `XLR-H1 +48V` phantom or run unregulated sub-dewpoint `TEC` coolers (`Gates G21, G23`), **NEVER** exceed `900 mA` on `5V` PMIC (`Gate G24`), **NEVER** occlude fan intake/exhaust (`Gate G25`), mount `> 5.5 mm` 1/4-20 screws (`Gate G26`), point at Class-3B/4 lasers (`Gate G27`), place high-wattage wireless TX near unshielded harnesses (`Gate G29`), exceed PL-to-E cantilever torque without `15 mm` LWS rods (`Gate G31`), or plug an unregulated `14.8V/26V` V-Mount dummy battery (`> 8.4V` blowout, `Gate G32`).

---

# Part I — English Field Operator SOP & Unbrick Runbook

## 1. Bench Pre-Plug Checklist (`Camera Disconnected`, `Phase 59` / `Gate G13`)

Execute every multimeter check below **with the Sony FX3 camera physically disconnected** (`camera_connected == False`, `ltc_cable_connected == False`) before plugging any Multi-Port harness into the body.

| # | Bench Check Item | Mandatory Pass Threshold | Fail-Closed Rejection / Physical Risk |
| :---: | :--- | :--- | :--- |
| **1.1** | **Controller Hardware Identity** | **Waveshare `RP2040-Zero`** compiled with **`-DOPEN_DRAIN=1`** (`GP27/28/29` <-> Sony 15-pin Multi-Port `Pin 9 / Pin 7 / Pin 8`, `Pin 2 = GND`) | **REJECT** standard Raspberry Pi Pico (`GP29` hardwired to `VSYS/3` divider corrupts `UART_RX`) or any `3.3V`/`5V` FTDI/CH340 push-pull dongle. |
| **1.2** | **Open-Drain `1.8V` Pull-Up Swing** | Measure `UART_TX` (`Pin 7`), `UART_RX` (`Pin 8`), `XRESET` (`Pin 9`) idle open-circuit voltage to `Pin 2` (`GND`): **`V_idle in [1.71V, 1.89V]`** (`<= 1.89V`, target `1.80V`) | Any reading `> 1.98V` or `~3.3V` leakage (`FAIL_OVERVOLTAGE_HAZARD`) destroys `CXD90057` `1.8V` BootROM I/O pads. Verify PIO uses `pindirs` (not push-pull `out pins`/`set pins`). |
| **1.3** | **Rail Isolation Resistance (DMM Ohms)** | Power-off resistance from `VBUS (5.0V)` & `3.3V` to `UART_TX`, `UART_RX`, `ID`, and `XRESET` **`>= 1.0 MΩ`**; `Pin 2` GND continuity **`<= 2.0 Ω`** | `< 1.0 MΩ` bridge indicates solder whisker or flux short; do NOT connect to camera. |
| **1.4** | **Multi-Port `Pin 6` `ID` Keying & LTC Unplug** | Only `BOOTROM_UART_BOOT` or `CONSOLE_READONLY` `ID` keying present; **`VMC-BNCM1` (`680 kΩ` LTC) and `LANC` (`100 kΩ`) disconnected** | Simultaneous `VMC-BNCM1` LTC (`0.5–4.5 Vpp`) + `uart_boot` (`Pins 7/8/9`) creates electrical contention and latch-up. |
| **1.5** | **RP2040 PIO Fractional Divider** | `div = clk_sys / (8 * baud)`: `325 + 133/256` (`125 MHz @ 48000`) or `346 + 91/256` (`133 MHz @ 48000`) — baud error **`<= 0.05%`** (`0.0004%` actual) | Rejects integer-only truncation (`0.160%` drift breaks `CXD90057` BootROM `UB` CRC32 framing). |
| **1.6** | **Automated Bench Self-Test** | Run `make verify-rp2040-fixture` (and `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-rp2040-fixture` for CI parity) | Must exit `0` with `status=VERIFIED_BENCH_FIXTURE`, `all_passed=True`, `camera_connected=False`, `persistent_emmc_writes_authorized=False`. |

---

## 2. Cinema Rig Electrical, Optical & Environmental Safety (`Gates G14, G19..G32`)

### 2.1 Preventing V-Mount `D-Tap` + Copper `HDMI Type-A` Blowouts (`Gate G19`)

When a camera body and an external SDI/HDMI monitor/recorder share an **unisolated V-Mount / Gold-Mount D-Tap splitter** while linked via **copper HDMI Type-A**, an open/intermittent D-Tap negative (`-`) pin on either power lead forces up to `3–8 A` of return current through **HDMI Pin 17 (Shield/GND)** and burns out the `CXD90057` HDMI ESD transceiver array.

| Rig Topology | Status | Required Operator Rule |
| :--- | :---: | :--- |
| **`INTERNAL_NP_FZ100_ISOLATED_USBPD` + Separate Monitor Battery** | **ALLOW (Preferred)** | Power FX3 via internal `NP-FZ100` (and isolated `USB-PD 9V/3A` if desired) and power Atomos/SmallHD from its own independent NP-F / V-Mount battery. |
| **`OPTICAL_FIBER` HDMI Cable** | **ALLOW** | Galvanic copper isolation on TMDS/GND (`<= 55 mA` Pin-18 check still applies). |
| **`ISOLATED_DCDC_BOX`** | **ALLOW** | Use a transformer-isolated DC-DC power converter between shared battery plate and camera/monitor. |
| **Shared Unisolated V-Mount `D-Tap` + Copper `HDMI Type-A`** | **ALLOW ONLY WITH GROUND-FIRST LOCKING CONNECTOR / OTHERWISE BLOCK** | **BLOCKED (`BLOCKED_GROUND_LOOP_HAZARD`)** unless a verified **ground-first locking D-Tap / LEMO** connector guarantees negative return cannot open while `+14.8V` is live. |

- **Mandatory Power-ON Plug Sequence**:
  1. `CONNECT_POWER_CABLES` (lock D-Tap / USB-PD firmly first while both devices are OFF)
  2. `CONNECT_HDMI` (seat full-size HDMI Type-A while both camera and monitor are OFF; HDMI `+5V` Pin-18 backfeed must stay `<= 5.25V` / `<= 55 mA`)
  3. `POWER_ON_CAMERA`
  4. `POWER_ON_MONITOR`
- **Mandatory Power-OFF Unplug Sequence (Exact Reverse)**:
  1. `POWER_OFF_MONITOR`
  2. `POWER_OFF_CAMERA`
  3. `DISCONNECT_HDMI` (never hot-unplug or hot-plug copper HDMI while powered if sharing a rig power bus)
  4. `DISCONNECT_POWER_CABLES`

### 2.2 E-Mount `V_LENS` (`3.3V` / `5.0V`) Hot-Detach & IBIS Rules (`Gate G19`)

- **Do NOT hot-swap E-Mount lenses during `REC` or active Stage-B trials**. Always power down the FX3 cleanly before pressing the lens release button.
- If accidental bayonet twist occurs while powered, Sony's 10-pin E-Mount hardware sequence activates **`LENS_DET` (`Pin 9`) first-break interrupt**, firing the **`V_LENS_SERVO_5V0` crowbar to `0.0 mA` within `<= 2.0 ms`** (ahead of the `3.5 ms` contact wipe window), tri-stating `V_LENS_LOGIC_3V3`, and preserving Stock-CP **`0x0400` (`LiroSeq: Restore.`)** 5-axis IBIS Center-Lock park (`cp_mutation_bytes == 0`).

### 2.3 Thermal Envelope, `NP-FZ100 >= 15%` UPS Reserve & `.RSV` Salvage (`Gates G14, G20`)

- **Start Headroom (`G14`)**: `CXD90057 SoC < 62.0°C` before Stage-B launch; `InfoLITHIUM NP-FZ100 >= 80%` (`>= 7800 mV`) before `H0`/`H1` start (`BP-U 11500 mV` comparator blocked); `USB-PD 9V/3A` (`27,000 mW`) VBUS droop `<= 450 mV`.
- **`libfan.so @ 0x1dec` Active PWM Guard**: Even under `OFF_IN_REC`, `SoC >= 62.0°C` / `CFexpress >= 68.0°C` forces fan ramp-up; `>= 82.0°C` triggers amber HUD alert; `>= 90.0°C` forces clean XAVC trailer flush -> `exFAT` unmount -> reverse `12..1` LIFO `tmpfs` teardown.
- **UPS Battery Reserve Behind `USB-PD 9V/3A` (`G20`)**:
  - **NEVER remove the `NP-FZ100` battery while recording on `USB-PD`**. Battery-less `USB-PD` operation fails closed (`BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT`).
  - Keep a genuine `NP-FZ100` at **`>= 15%` SoC (`>= 6.8V` under load)** inside the grip at all times; if `USB-PD 9V/3A` is tripped mid-take (`4K 60p XAVC S-I 600 Mbps`), the `>= 15%` UPS reserve sustains seamless trailer closure (`moov` / `MXF FooterPartition`) with `0` dropped frames.
- **Unfinalized `.RSV` Emergency Salvage**: If power loss leaves a `.RSV` file (`ISO-BMFF` `ftyp`+`mdat` missing `moov`, or `MXF` missing `FooterPartition`), remove the card, copy strictly read-only (`os.O_RDONLY`, `physical_media_writes == 0`), and run offline inspection—never reformat or write in-place on the original media.

### 2.4 `XLR-H1` `+48V` Phantom Power & Hot-Plug Guard (`Gate G21`)

- **Mic-Type & Termination Rules**: Enable **`MIC+48V`** (`+48.0V / 6.81 kΩ` IEC 61937) **ONLY** for true condenser microphones or transformer-isolated active DIs. **NEVER** apply `+48V` to **passive ribbon microphones** or **unbalanced `3.5 mm TRS -> XLR` wireless receivers / timecode (`LTC`) feeds** (`BLOCKED_PHANTOM_48V_SOURCE_HAZARD`).
- **Mandatory Zero-Voltage Unplug Sequence**: Disable phantom (`+48V -> OFF`) via menu/physical toggle, wait for `CH1/CH2` ADC mute & capacitor bleed-down **`<= 1.0 V`** before unplugging or plugging any XLR cable (`hot_plug_while_48v_live=True` is blocked).

### 2.5 Gimbal Follow-Focus Torque, Venue Laser & Shutter Curtain Protection (`Gate G22`)

- **E-Mount Follow-Focus Torque & Single-Bus Arbitration**: Limit `14.8V` brushless focus/zoom motors (Tilta Nucleus / DJI Focus Pro) on plastic/metal E-Mount barrels to **`<= 0.35 N·m`** (or calibrate electronic end-stops / use `15 mm` rod clamps). Connect the gimbal via **ONLY ONE** control bus (`USB-C CrSDK` **OR** `Multi-Port RSS`—never both simultaneously) and keep `IBIS` in `Standard`/`Off` when gimbal-mounted.
- **Venue Laser Optical-Cut & Sensor Curtain Park**: Do not aim an uncovered sensor directly at Class-3B/4 show lasers; keep **`Shutter When Power Off = OFF` (`OPEN`)** so the mechanical focal-plane curtain never acts as an accidental barrier or catches dust/impact during Stage-B cold resets.

### 2.6 Tropical Dew-Point `TEC` Condensation & PMIC `5V 900 mA` Rail Budget (`Gates G23, G24`)

- **Magnus-Tetens Dew-Point Lock (`Gate G23`, $a=17.625, b=243.04^\circ\text{C}$)**: External clip-on Peltier `TEC` coolers (`Ulanzi`/`SmallRig`) MUST NEVER drive the rear LCD hinge cold-plate below **`T_dp + 2.0°C`** (e.g., at `31°C / 80% RH`, $T_{dp} \approx 27.1^\circ\text{C}$, a `11.0°C` cold plate triggers **`BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION`** and can short `MI-Shoe` or `HDMI` pins). Cold-to-warm transitions (`-5°C -> +26°C / 65% RH`) require sealed desiccant bagging until body temperature stabilizes above `T_dp`. Internal `libfan.so` centrifugal air cooling stays `>= T_amb > T_dp` with `0%` condensation risk.
- **PMIC `5V 900 mA` Accessory Rail Budget (`Gate G24`)**: Total simultaneous `5V` draw across `MI-Shoe XLR-H1` + `HDMI Pin-18 (<= 55 mA)` + `USB-C VBUS` + `Multi-Port` MUST stay **`<= 900.0 mA`** (exceeding e.g. `940 mA` without an externally powered USB-C PD hub triggers brownout shed `BLOCKED_PMIC_5V_OVERCURRENT`). Avoid un-E-marked `> 2 m` USB-C cables (`IR droop > 0.65V @ 3.0A`) and lock HDMI/USB-C strain-relief clamps on handheld/gimbal rigs (`make verify-24-gates`).

### 2.7 Fan Intake Occlusion, `1/4-20` Screw Depth & Sub-Zero / Altitude Derating (`Gates G25..G28`)

- **Sigma Fan Intake/Exhaust & Rain-Blimp Backpressure (`Gate G25`)**: Maintain **>= 15 mm clearance** around the FX3 Sigma top/side intake & exhaust vents; reject airtight rain covers/blimps without forced exhaust ventilation (backpressure > `2.0x` triggers `BLOCKED_FAN_INTAKE_OCCLUSION`).
- **`1/4-20` Tripod Thread Depth & Underwater Housing Vacuum (`Gate G26`)**: Limit cage / quick-release `1/4-20 UNC` screws into the FX3 chassis to **`<= 5.5 mm`** engagement (`<= 3.5 N·m`, protecting internal copper ground planes & ribbon flexes) and require verified underwater housing vacuum check + thermal conduction pad when submerged.
- **`IMX510` Curtain Shock, Sub-Zero `-20°C` Li-Ion ESR & `> 3,000m` Altitude Derating (`Gates G27, G28`)**: Enforce **`Shutter When Power Off = OFF` (`OPEN`)**, transport-lock IBIS during transit shocks, de-rate `NP-FZ100` open-circuit voltage/ESR below **`0°C.. -20°C`** (pre-warm batteries `>= 10°C` before high-bitrate `XAVC S-I` `REC`), and apply convective fan speed margins above **`3,000 m`** altitude.

### 2.8 Wireless TX Near-Field EMI, `> 6h` Endurance, Heavy PL Cantilever & V-Mount Dummy-Battery OVP (`Gates G29..G32`)

- **5GHz/6GHz TX Near-Field EMI & `> 6h` Zero-NVRAM-Churn (`Gates G29, G30`)**: Keep high-power Teradek/Hollyland `5GHz/6GHz` video transmitters separated (`>= 100 mm`) from unshielded HDMI/Multi-Port harnesses (`ESD` contact protection); verify CFexpress SMART wear & `> 6h` multi-gigabyte `exFAT` clip-spanning keeps volatile RAM-shadow state at **`0` persistent NVRAM writes**.
- **Heavy Cinema PL-to-E Cantilever (`15 mm` LWS) & V-Mount Dummy-Battery `> 8.4V` Blowout (`Gates G31, G32`)**:
  - Any PL/EF lens/matte-box rig exerting **`> 1.8 N·m`** E-Mount flange bending moment MUST lock onto **`15 mm` LWS baseplate rods + lens support** (`BLOCKED_PL_CANTILEVER_OVERLOAD`).
  - **NEVER plug an unregulated `14.8V` or `26V` V-Mount dummy battery directly into the FX3 grip**! Input exceeding **`8.45V`** triggers instant **`BLOCKED_DUMMY_BATTERY_OVP_BLOWOUT`** (`NP-FZ100` `7.2V` 2S spec requires an active buck-regulated `7.8–8.2V` coupler with authentic Sony `InfoLITHIUM` `NTC` thermistor ID). Run **`make verify-32-gates`**!

---

## 3. Media, Network, License & Firmware Anti-Rollback Isolation (`Gates G15..G18`, `10-Pillar Recovery`)

| Domain | Gate | Mandatory Field Rule | Verification Command / Redline |
| :--- | :---: | :--- | :--- |
| **Dedicated Blank Lab Card** | **`G17`** | Use a **dedicated blank lab CFexpress Type A / UHS-II SDXC card**. Never insert cards holding client footage (`XDROOT/Clip/*.MXF`, `PRIVATE/M4ROOT/CLIP/*.MP4`, `DCIM/*`), unfinalized `.RSV`, or `FOUND.000/*.CHK`. Verify Microsoft `exFAT` 12-sector `BootChecksum` (`Main == Backup`) & `VolumeDirty == 0` (`offset 106`). Match speed class: **`CFexpress VPG200/VPG400`** for `S&Q 4K120` / `XAVC S-I 600 Mbps`, **`SDXC V90+`** for `XAVC S-I 4K60`. Never confuse external `exFAT` with internal `p1` `FAT12`/`FAT16`. | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-media-guard` |
| **`P12` Airplane-Mode + Wired `USB-LAN`** | **`G16`**, **`G18`** | Keep Stage-B **`P12`** (`libWlanResource.so @ 0x70d4 -> rc=0`) + `/tmp/bk4_shadow` (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`) active so Wi-Fi & BT (`/dev/ttyAMA3`) stay 100% dark (`0` HCI TX, immune to Sony Notice `00342260` `WF-12`). For remote monitoring/control (*Monitor & Control* / `CrSDK`), use wired **`USB-LAN` (`CDC-NCM` `1 Gbps` `RTL8153` or original `AX88179`)** + **`PTP-IP TCP 15740`**. Reject `RNDIS`, `AX88179A/B`, `2.5G/5G/10G`, and remember FX3 `[Manual]` IPv4 requires a valid same-subnet `Default Gateway`. | `make verify-wireless-guard` & `make verify-32-gates` |
| **`C2PA 2.1` & Factory Calib Zero-Write** | **`G15`** | Strictly **zero writes or rw mounts** on `/dev/cnflasha*`, `RPMB`, TrustZone/OP-TEE, Sony **C2PA 2.1** (`RQ_LIC.DAT`, `sigcert.p12/.pfx`, `p12:/cert`), or per-body factory calibrations (`p2:/setting/Backup.bin`, `psd.bin`, `defdet.bin`, `p6:Jiritsu`, `p18:/lens/lensfile.bin`, SPI NOR `ddrtraining.dat`). | `make verify-32-gates` (`calibration_mutation_bytes == 0`, `c2pa_keystore_untouched == True`) |
| **10-Pillar Recovery, `GF(256)` & `OTP/RPMB` / `GPT` / `EXT_CSD` / `FDT`** | **Ph72–106** | Archive all 11 Tier-0 partitions into two **per-body** SHA-256 + `GF(2^8)` (`0x11d`) P+Q RAID-6 vaults (`CROSS_BODY_TRANSPLANT_FORBIDDEN`); keep `CXD90057` OTP (`otp_fuse_touches == 0`), `RPMB` counters (`rpmb_counter_increments == 0`), and `EXT_CSD[173/171]` Perm-WP fuses blocked; decode **`1.8V` passive RX-only UART `S0..S6`** (`passive_tx_bytes_emitted == 0`); audit **Ph94** `15`-part dual GPT CRC32 + `RPMB HMAC-SHA256` replay, **Ph101** `EXT_CSD[267..269]` Pre-EOL wear, and **Ph106** `FDT /chosen/bootargs` (`ro`) + ARM64 `0x644d5241` kernel `Image`. | `make verify-10pillar-recovery`, `make verify-antirollback-guard`, `make verify-milestone-110` |

---

## 4. 4-Layer Instant Escape & `Tier-0..Tier-4` Unbrick Decision Tree

### 4.1 4-Layer Instant Fail-Open Escape (`Phase 66` / `make verify-init2-escape`)

Every Stage-B volatile overlay executes inside `stage_b_init2_guard.sh` **before** extracting CPIO or executing `mount --bind`:

1. **Layer 1 — Zero-Cable SD / CFexpress Sentinel (`< 1 second`)**:
   - Insert **any** FAT32/exFAT SD or CFexpress card containing an empty sentinel file named **`FX3_SAFE_STOCK.FLG`** (or `DISABLE_STAGE_B.TXT`) in the card root (Slot A or Slot B).
   - `stage_b_init2_guard.sh` detects the sentinel *before* any `mount --bind`, logs zero mounts (`0` eMMC writes), and immediately `exec`s 100% stock Sony FX3 `v7.02` (`< 1 s`, zero USB/UART cables required).
2. **Layer 2 — Physical Body Key Chord Escape**:
   - Hold **`REC+MENU`** or **`SHUTTER`** during cold boot to trip the pre-mount GPIO bypass latch and boot stock FX3 `v7.02`.
3. **Layer 3 — Pre-Mount Integrity & Latch Fail-Open**:
   - Clear-Before-Exec immediately unlinks `/tmp/mod_arm_once` and checks one-shot `boot_attempts`; if `stage_b_overlay.cpio` fails `070701` magic or `13/13` SHA-256 verification, or `/etc/ld.so.preload` exists, or `PRODUCT_MODEL != 0x91030080`, or `tmpfs` headroom `< 48 MiB`, Stage-B aborts cleanly to stock `appFw.so`.
4. **Layer 4 — Crash-Loop Auto-Unmount & `CXD90057` WDT**:
   - If `procam_app` exits `>= 3` times within `15 s` in `/tmp/stage_b_crash.cnt`, the guard unmounts all `tmpfs` bind mounts in reverse LIFO order and `exec`s stock `procam_app`.
   - If the UI or kernel locks up completely, the **`CXD90057` hardware WDT** (`10,000 ms`) or cutting `NP-FZ100` power for `>= 60 s` wipes volatile `tmpfs` RAM cleanly (**`H0 == H2`** verified by `make verify-post-trial-audit`).

### 4.2 `Tier-0..Tier-4` Unbrick Escalation Decision Tree

```text
  [Anomaly / Boot Stall Observed]
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 0: Instant Field Recovery (Zero Cables, Zero Flash Writes)         │
  │  1. Pull NP-FZ100 + USB-PD >= 60s -> volatile tmpfs wiped -> Stock 7.02 │
  │  2. Or insert SD/CFexpress with FX3_SAFE_STOCK.FLG -> <1s stock boot    │
  │  3. Verify GF(256) vault, H0 == H2 & Milestone-110:                     │
  │     make verify-tier0-backup && make verify-post-trial-audit            │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ Camera still stuck in p1 updater loop or host MSC stall?
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 1: Host USB MSC Quiescence & U5 2-Step Updater Exit                │
  │  - macOS 26 IOUSBHost 0xe00002be: wait >= 350ms + [50..800ms] backoff   │
  │  - 0 retries on USB STALL (0xe000404f); Senser v2 RSA blocked           │
  │  - Sticky p1 loop: rm -f /setting/updater/mode* && sync &&              │
  │                    ud_send_lsi.elf 0 (mandatory U5 2-step exit)         │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ p1 refuses normal exit or v7.02 VMA check fails?
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 2: p1 FAT12/FAT16 Capsule, Shifted-VMA v7.02 & Anti-Rollback Lock  │
  │  - Verify FAT1 == FAT2, LFN checksums, 6-step fsync atomic staging      │
  │  - Resolve shifted v7.02 p1 sites via AArch64 ADRP/BL (p1_autolocator)  │
  │  - Enforce CXD90057 OTP/RPMB zero-touch & block <v7.00 / cross-SKU      │
  │  - Gate check: make verify-init2-escape && make verify-antirollback-guard│
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ Need passive S0..S6 UART logs or p3 & p1 dead on USB MSC?
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 3: Passive 1.8V RX-Only UART S0..S6 & 48000-Baud BootROM Fastboot  │
  │  - Passive capture: 1.8V RX-only S0..S6 (passive_tx_bytes_emitted == 0)│
  │  - UNPLUG VMC-BNCM1 LTC cable; NEVER use standard Pico GP29             │
  │  - Run bench test FIRST (camera unplugged): make verify-rp2040-fixture  │
  │  - Attach RP2040-Zero -DOPEN_DRAIN (1.8V, Pins 9/7/8 + Pin 2 GND)       │
  │  - Stage to 0x92028000 / 0xFE020000; ALLOW ONLY oem dumpbrom / dump     │
  │    (flash:* / erase:* / oem format remain HARD-BLOCKED)                 │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ BootROM / SPI NOR / eMMC bus unresponsive?
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 4: Offline O_RDONLY eMMC ISP, GPT/RPMB, Pre-EOL & FDT Forensics    │
  │  - Open strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK                     │
  │  - Audit Sector 0 ('8246'), 15-part GPT CRC32, RPMB HMAC-SHA256 replay  │
  │  - Audit EXT_CSD[179/173/171/267..269 Pre-EOL], FDT /chosen/bootargs ro │
  │  - Reject CMD42 forced-erase, Perm-WP traps & BOOT_PARTITION_ENABLE == 0│
  │  - 10-Pillar & Phase 110 Master Gates:                                  │
  │    make verify-10pillar-recovery && make verify-milestone-110           │
  └─────────────────────────────────────────────────────────────────────────┘
```

---
---

# 第二部分 — 简体中文现场操作规范（SOP）与救砖应急手册

> **核心安全前提**：本实验全程保持 **`persistent_emmc_writes_authorized = False`** 与 **`persistent_write_release = False`** 刚性硬锁。所有 Stage-B 叠加层均运行于易失性 `tmpfs` 内存盘，对内部 eMMC、`p2:/setting`、`p5:/wbi`、`p8:/cp`、`C2PA 2.1` 证书库与出厂校准区执行 **`0` 字节持久化写入**，且被动 `1.8V` 串口抓包强制 `passive_tx_bytes_emitted = 0`。

## 一、插机前工作台自检清单（`相机严禁接入`，`Phase 59` / `Gate G13`）

在将任何 Multi-Port 线束接入 Sony FX3 机身**之前**，必须在 `camera_connected == False`（相机完全断开）且 `ltc_cable_connected == False` 状态下完成以下全部万用表与脚本校验：

| 序号 | 检查项目 | 强制合格标准 | 失效关闭拦截条件与物理风险 |
| :---: | :--- | :--- | :--- |
| **1.1** | **治具主控选型与固件** | **Waveshare `RP2040-Zero`**，编译期开启 **`-DOPEN_DRAIN=1`**（`GP27/28/29` 对接 Multi-Port `Pin 9 / Pin 7 / Pin 8`，`Pin 2 = GND`） | **严禁使用普通树莓派 Pico**（其 `GP29` 接有 `VSYS/3` 分压电阻会拉偏 `UART_RX`）或任何 `3.3V`/`5V` 推挽式 USB-TTL 小板。 |
| **1.2** | **开漏 `1.8V` 上拉摆幅实测** | 万用表直测 `UART_TX`（`Pin 7`）、`UART_RX`（`Pin 8`）、`XRESET`（`Pin 9`）对 `Pin 2`（`GND`）空载电平：**`V_idle ∈ [1.71V, 1.89V]`**（`<= 1.89V`，标称 `1.80V`） | 任何 `> 1.98V` 或 `3.3V` 漏电（`FAIL_OVERVOLTAGE_HAZARD`）将直接击穿 `CXD90057` `1.8V` BootROM I/O 口。PIO 必须使用 `pindirs` 开漏驱动。 |
| **1.3** | **高压电源轨隔离电阻** | 断电测量 `VBUS (5.0V)` 及 `3.3V` 电源轨与 `UART_TX/RX/ID/XRESET` 间电阻 **`>= 1.0 MΩ`**；`Pin 2` 地线导通电阻 **`<= 2.0 Ω`** | `< 1.0 MΩ` 说明存在焊锡桥接或助焊剂漏电，严禁上机。 |
| **1.4** | **`Pin 6` `ID` 电阻与 LTC 拔除** | 仅允许 `BOOTROM_UART_BOOT` 或 `CONSOLE_READONLY` `ID` 阻值；**`VMC-BNCM1`（`680 kΩ` LTC 线）与 `LANC` 必须彻底拔除** | LTC 信号（`0.5–4.5 Vpp`）与 `uart_boot`（`Pin 7/8/9`）绝不可同时并接。 |
| **1.5** | **RP2040 PIO 小数分频精度** | `div = clk_sys / (8 * baud)`：`125 MHz @ 48000` 为 `325 + 133/256`、`133 MHz @ 48000` 为 `346 + 91/256`，波特率误差 **`<= 0.05%`**（实测 `0.0004%`） | 拒绝整数分频（`0.160%` 漂移会导致 BootROM `UB` CRC32 校验失败）。 |
| **1.6** | **工作台自动自检命令** | 执行 `make verify-rp2040-fixture`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-rp2040-fixture`） | 必须返回 `exit 0`、`all_passed=True`、`camera_connected=False`。 |

---

## 二、电影机套件电气、光学与环境安全规程（`Gates G14, G19..G32`）

### 2.1 防治 V 口电池 `D-Tap` + 铜缆 `HDMI Type-A` 烧接口（`Gate G19`）

当相机（含假电池/电源线）与外录监视器共用**非隔离 V-Mount D-Tap 分线器**并同时插入**铜芯 HDMI Type-A** 时，若 D-Tap 负极（`-`）发生虚接或开路，`3–8 A` 大电流将全部倒灌进 **HDMI Pin 17 屏蔽地线**，瞬间烧毁 `CXD90057` HDMI ESD 保护阵列与主板接口。

| 套件供电与视频拓扑 | 门禁结论 | 现场执行规范 |
| :--- | :---: | :--- |
| **`NP-FZ100` 机内电池（+ 隔离 `USB-PD 9V/3A`）+ 监视器独立供电** | **放行（最推荐）** | 相机与监视器各自独立电池供电，从物理上彻底消除共地回路。 |
| **光纤 `HDMI Type-A` 线缆** | **放行** | 具备 TMDS/GND 电气隔离（仍须校验 Pin-18 `<= 5.25V / <= 55 mA`）。 |
| **带变压器隔离的 `DC-DC` 电源盒** | **放行** | 使用原边/副边隔离型电源分配盒隔离相机与监视器地线。 |
| **共用非隔离 `D-Tap` + 铜缆 `HDMI`** | **仅限地线先接锁定接头，否则强制拦截** | 若无 **Ground-First 先接地锁定接头**，触发 `BLOCKED_GROUND_LOOP_HAZARD` 硬拦截。 |

- **强制上电插线顺序**：`① 连接供电线缆 (OFF 状态锁紧) -> ② 插入 HDMI Type-A -> ③ 开启相机电源 -> ④ 开启监视器电源`
- **强制下电拆线顺序（严格逆序）**：`① 关闭监视器 -> ② 关闭相机 -> ③ 拔出 HDMI Type-A -> ④ 断开供电线缆`（共电状态下严禁带电热插拔铜芯 HDMI！）

### 2.2 E 卡口 `V_LENS`（`3.3V / 5.0V`）热拆保护与 IBIS 规则（`Gate G19`）

- 录制中或 Stage-B 试验期间**严禁带电拧下 E 卡口镜头**；换镜头前务必关机待机。
- 发生意外旋动时，E 卡口 10 针触点由 **`Pin 9 (LENS_DET)` 率先断开触发中断**，在 `<= 2.0 ms` 内（早于 `3.5 ms` 滑刷接触窗口）将 `V_LENS_SERVO_5V0` 撬棍泄放至 `0.0 mA` 并三态隔离 `V_LENS_LOGIC_3V3`，同时由原厂 Stock-CP **`0x0400`（`LiroSeq: Restore.`）** 完成 5 轴防抖居中锁止（`cp_mutation_bytes == 0`）。

### 2.3 温控、`USB-PD` 下 `NP-FZ100 >= 15%` 留底电量与 `.RSV` 抢救（`Gates G14, G20`）

- **启动阈值（`G14`）**：`CXD90057 SoC < 62.0°C`，`InfoLITHIUM NP-FZ100 >= 80%`（`>= 7800 mV`），`USB-PD 9V/3A`（`27,000 mW`）压降 `<= 450 mV`；`libfan.so @ 0x1dec` 在 `62°C` 自动接管提速、`82°C` 琥珀警告、`90°C` 强制封口并逆序卸载。
- **`USB-PD 9V/3A` 供电子系统的强制 UPS 电池留底（`G20`）**：
  - **严禁拔掉机内电池仅靠 USB-PD 裸机录制**（`battery_less_usb_pd=True` 直接阻断 `BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT`）。
  - 机内必须安装真实 `NP-FZ100` 且电量 **`>= 15%`（带载 `>= 6.8V`）** 作为 UPS 后备；高码率 `4K 60p 600 Mbps` 录制时若 USB-PD 意外脱落，留底电量可确保无损写入 `moov` / `MXF FooterPartition`，实现 **0 丢帧安全封口**。
- **断电未封口 `.RSV` 只读抢救**：如意外生成 `.RSV` 残缺文件，立即停录并只读拷贝（`os.O_RDONLY`，`physical_media_writes == 0`）进行离线修复，绝不在原实验卡上进行就地写修复。

### 2.4 `XLR-H1` `+48V` 幻象供电与带电热插拔防护（`Gate G21`）

- **话筒选型与端接规则**：仅允许为真电容话筒或带变压器隔离的有源 DI 开启 **`MIC+48V`**（`+48.0V / 6.81 kΩ` IEC 61937）。**严禁**对**无源铝带话筒**或**非平衡 `3.5 mm TRS -> XLR` 无线接收机 / 时间码（`LTC`）输入**施加 `+48V`（触发 `BLOCKED_PHANTOM_48V_SOURCE_HAZARD`）。
- **强制零电压拔插流程**：先通过菜单或开关关闭幻象供电（`+48V -> OFF`），等待 `CH1/CH2` ADC 静音且电容泄放至 **`<= 1.0 V`** 后方可插拔卡农线（`hot_plug_while_48v_live=True` 硬拦截）。

### 2.5 稳定器跟焦扭矩、演出激光与机械快门帘幕保护（`Gate G22`）

- **E 卡口跟焦马达扭矩与单总线仲裁**：`14.8V` 无刷跟焦/变焦马达（Tilta Nucleus / DJI Focus Pro）必须限制在 **`<= 0.35 N·m`**（或标定电子软限位 / 使用 `15 mm` 导管夹固定）。稳定器仅允许通过**单一**控制总线连接（`USB-C CrSDK` **或** `Multi-Port RSS` 二选一，严禁双总线同时争抢），架上稳定器时关闭或设为 `Standard` IBIS。
- **演出激光滤光与快门帘幕常开规则**：严禁无防护直面 Class-3B/4 舞台激光；始终保持 **`Shutter When Power Off = OFF`（常开 `OPEN`）**，防止 Stage-B 冷复位时机械帘幕误闭合受损。

### 2.6 湿热露点 `TEC` 结露拦截与 PMIC `5V 900 mA` 配件总预算（`Gates G23, G24`）

- **Magnus-Tetens 露点门禁（`Gate G23`，`a=17.625, b=243.04°C`）**：外挂半导体制冷片 `TEC`（如 `Ulanzi`/`SmallRig`）冷面温度严禁低于 **`T_dp + 2.0°C`**（例如 `31°C / 80% RH` 环境下露点约为 `27.1°C`，`11.0°C` 冷板将立即触发 **`BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION`**，避免冷凝水沿 `MI` 热靴或 `HDMI` 短路）。冷进暖（`-5°C -> +26°C / 65% RH`）转场必须先密封干燥袋平衡至高于 `T_dp`。机内 `libfan.so` 离心风冷始终 `>= T_amb > T_dp`，**结露风险 0%**。
- **PMIC `5V 900 mA` 供电总线预算（`Gate G24`）**：`MI 热靴 XLR-H1` + `HDMI Pin-18 (<= 55 mA)` + `USB-C VBUS` + `Multi-Port` 的 `5V` 并发总电流必须 **`<= 900.0 mA`**（例如 `940 mA` 无外接带电 PD Hub 将触发过流卸载 `BLOCKED_PMIC_5V_OVERCURRENT`）。严禁使用无 E-Marker 且 `> 2 m` 的 `USB-C` 线缆（`3.0A` 压降 `> 0.65V`），并在手持/稳定器套件上锁紧抗拉线夹（`make verify-24-gates`）。

### 2.7 风扇进气遮挡、`1/4-20` 螺孔深度与 `-20°C`/高海拔降额（`Gates G25..G28`）

- **Sigma 风扇进排气口与防雨罩背压（`Gate G25`）**：机顶/机侧散热风道周围保持 **`>= 15 mm`** 净空，拒绝无主动排风口的气密防雨罩（背压 `> 2.0x` 触发 `BLOCKED_FAN_INTAKE_OCCLUSION`）。
- **`1/4-20` 螺孔深度与水下防水壳真空（`Gate G26`）**：兔笼/快装板 `1/4-20` 螺丝旋入深度限制在 **`<= 5.5 mm`**（扭矩 `<= 3.5 N·m`，避免顶伤内部屏蔽地层与排线）；水下壳下水前须完成负压抽真空密封与导热垫校验。
- **`IMX510` 帘幕防震、`-20°C` 锂电 ESR 与 `> 3,000 m` 高海拔降额（`Gates G27, G28`）**：维持 `Shutter When Power Off = OFF`（常开）、`> 10G` 运输震动时锁定 IBIS；`-20°C..0°C` 拍摄高码率前将 `NP-FZ100` 预热至 `>= 10°C`，海拔 `> 3,000 m` 启用低空气密度风扇转速补偿。

### 2.8 无线图传近场 EMI、`> 6h` 耐久、重型 PL 悬臂与假电池 `> 8.4V` OVP 防爆管（`Gates G29..G32`）

- **5GHz/6GHz 图传 EMI 与 `> 6h` 零 NVRAM 磨损（`Gates G29, G30`）**：大功率无线图传与非屏蔽 HDMI / Multi-Port 线束保持 `>= 100 mm` 间距并做好 ESD 保护；验证连续 `> 6h` 双卡槽 `exFAT` 跨越录制下 `BK4\0` 影子保持 `0` 持久化 NVRAM 写入。
- **重型 PL 卡口悬臂（`15 mm` LWS）与 V 口假电池 `> 8.4V` OVP 防爆管（`Gates G31, G32`）**：
  - 凡重型电影 PL/EF 转接镜头施加 **`> 1.8 N·m`** E 卡口弯矩，必须锁死 **`15 mm` LWS 导管底座与镜头托架**（`BLOCKED_PL_CANTILEVER_OVERLOAD`）。
  - **严禁将未稳压的 `14.8V` 或 `26V` V 口假电池直插 FX3 电池仓**！输入超过 **`8.45V`** 立即拦截 **`BLOCKED_DUMMY_BATTERY_OVP_BLOWOUT`**（必须使用经 `7.8–8.2V` 主动降压且带正版 Sony `InfoLITHIUM` `NTC` 热敏识别的假电池），上线前统一运行 **`make verify-32-gates`**！

---

## 三、存储介质、有线网络与 `C2PA` / 10 支柱防回滚隔离（`Gates G15..G18`，`10-Pillar Recovery`）

| 隔离域 | 门禁 | 现场操作铁律 | 自检与红线指标 |
| :--- | :---: | :--- | :--- |
| **专用空白实验卡** | **`G17`** | 必须使用**专用空白 CFexpress Type A / SDXC UHS-II 实验卡**；严禁插入存有客户素材（`XDROOT/Clip/*.MXF`、`PRIVATE/M4ROOT/CLIP/*.MP4`、`DCIM/*`）、未封口 `.RSV` 或 `FOUND.000/*.CHK` 的生产卡。要求 Microsoft `exFAT` 12 扇区 `BootChecksum` 一致、`VolumeDirty == 0`；高码率 `S&Q 4K120`/`600M` 须匹配 `VPG200/VPG400`（或 `V90`）。严格隔离外置 `exFAT` 与内部 `p1` `FAT12/FAT16`。 | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-media-guard` |
| **`P12` 飞行模式 + 有线 `USB-LAN`** | **`G16`**, **`G18`** | Stage-B **`P12`**（`libWlanResource.so @ 0x70d4 -> rc=0`）叠加 `/tmp/bk4_shadow`（`0x019e0012=00`、`0x0051000f=00`、`0x01a20002=00`）彻底关闭 Wi-Fi 与蓝牙（`0` HCI 发包，免疫 **`00342260` `WF-12` 无限重启**）。外联监看/控制统一通过 **有线 `USB-LAN`（`CDC-NCM` `1 Gbps` `RTL8153` 或原版 `AX88179`）+ `PTP-IP TCP 15740`**（拒绝 `RNDIS`/`AX88179A/B`/`2.5G+`；FX3 手动静态 IP 必须填写同网段默认网关），防火墙放行 *Monitor & Control* / `CrSDK` 安全指令并阻断刷机/NVRAM 操作码。 | `make verify-wireless-guard` 与 `make verify-32-gates` |
| **`C2PA 2.1` 密钥与出厂校准保护** | **`G15`** | 全程对 `/dev/cnflasha*`、`RPMB`、TrustZone/OP-TEE、Sony **`C2PA 2.1`**（`RQ_LIC.DAT`、`sigcert.p12`、`p12:/cert`）及出厂传感器/镜头校准区（`p2:/setting/Backup.bin`、`psd.bin`、`defdet.bin`、`p6:Jiritsu`、`p18:/lens/lensfile.bin`、SPI NOR `ddrtraining.dat`）保持 **0 字节修改、0 读写挂载**。 | `make verify-32-gates`（`calibration_mutation_bytes == 0`、`c2pa_keystore_untouched == True`） |
| **10 支柱救砖、`GF(256)` 与 `OTP/RPMB`/`GPT`/`EXT_CSD`/`FDT` 锁** | **Ph72–106** | 将全部 11 项 Tier-0 分区封存进两套**同机绑定** SHA-256 + `GF(2^8)`（`0x11d`）P+Q RAID-6 校验库（严防跨机移植）；严守 `CXD90057` OTP 0 触碰（`otp_fuse_touches == 0`）、`RPMB` 计数 0 递增及 `EXT_CSD[173/171]` 永久写保护陷阱拦截；以 **`1.8V` 被动只收 UART `S0..S6`** 解码日志（`passive_tx_bytes_emitted == 0`）；并核验 **Ph94** `15` 分区双 GPT CRC32 + `RPMB HMAC-SHA256` 防重放、**Ph101** `EXT_CSD[267..269]` Pre-EOL 寿命预警与 **Ph106** `FDT /chosen/bootargs` (`ro`) + ARM64 `0x644d5241` 内核 `Image`。 | `make verify-10pillar-recovery`、`make verify-antirollback-guard`、`make verify-milestone-110` |

---

## 四、4 层秒级逃生机制与 `Tier-0..Tier-4` 救砖决策树

### 4.1 4 层失稳即退（Fail-Open）现场逃生机制（`Phase 66` / `make verify-init2-escape`）

Stage-B 入口脚本 `stage_b_init2_guard.sh` 在解压 CPIO 或执行任何 `mount --bind` **之前**依次检查以下 4 道保险：

1. **第 1 层 —— 免拆线哨兵卡秒退（`< 1 秒`零线缆恢复原厂）**：
   - 将**任意一张根目录建有空文件 `FX3_SAFE_STOCK.FLG`（或 `DISABLE_STAGE_B.TXT`）的 SD 卡或 CFexpress 卡**插入 Slot A 或 Slot B 并开机。
   - `init2` 哨兵在执行任何挂载前立即中止 Stage-B（`0` 挂载、`0` eMMC 写入），**`< 1 秒` 内直接引导进入 100% 原厂 Sony FX3 `v7.02`**！
2. **第 2 层 —— 机身组合键逃生**：冷启动按住 **`REC+MENU`** 或 **`SHUTTER`** 触发物理 GPIO 绕过锁，直接进入原厂系统。
3. **第 3 层 —— 载荷完整性自动熔断**：Clear-Before-Exec 预先删除 `/tmp/mod_arm_once`；若 CPIO `070701` 魔数或 `13/13` SHA-256 校验失败、检测到 `/etc/ld.so.preload`、`PRODUCT_MODEL != 0x91030080` 或 `tmpfs` 剩余 `< 48 MiB`，立刻回落原厂 `appFw.so`。
4. **第 4 层 —— 崩溃循环自动卸载与 `CXD90057` 硬件看门狗**：若 `procam_app` 在 `15 秒` 内连续异常退出 `>= 3` 次（`/tmp/stage_b_crash.cnt`），守护逻辑立即逆序 LIFO 卸载全部 `tmpfs` 绑定挂载并拉起原厂 `procam_app`；若系统完全卡死，触发 `CXD90057` 硬件看门狗（`10,000 ms`）或**断电拆下 `NP-FZ100` 等待 `>= 60 秒`**，易失性 RAM 清空后自动恢复 **`H0 == H2` 原厂状态**（可通过 `make verify-post-trial-audit` 审计核验）。

### 4.2 `Tier-0..Tier-4` 救砖升级决策树（`Phase 47` + `Phase 59..110`）

```text
  [观测到异常 / 卡死 / 升级循环]
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 0：现场零线缆秒级恢复（0 持久化写入）                                │
  │  1. 拔除 NP-FZ100 与 USB-PD >= 60 秒 -> 易失性 tmpfs 清零 -> 原厂 v7.02  │
  │  2. 或插入含根目录 FX3_SAFE_STOCK.FLG 的存储卡 -> < 1 秒直达原厂系统     │
  │  3. 核验 GF(256) 备份库、H0 == H2 与 Phase 110：                         │
  │     make verify-tier0-backup && make verify-post-trial-audit            │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ 仍停留在 p1 升级模式循环或宿主机 MSC 挂载超时？
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 1：macOS 26 IOUSBHost 静默回退与 U5 两步退出 `p1`                   │
  │  - 遇 0xe00002be 独占冲突：静默 >= 350ms + [50..800ms] 指数退避         │
  │  - USB STALL (0xe000404f) 零重传；拦截 Senser v2 RSA                   │
  │  - 解除 p1 粘滞循环：rm -f /setting/updater/mode* && sync &&             │
  │                      ud_send_lsi.elf 0（强制 U5 两步复位）             │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ p1 容器异常或 v7.02 VMA 校验失败？
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 2：p1 FAT12/FAT16 原子胶囊、v7.02 4 锚点与防回滚硬锁                │
  │  - 校验 FAT1 == FAT2、LFN 校验和及 6 步 fsync 原子写                    │
  │  - AArch64 ADRP/BL 自动解析 v7.02 p1 地址（拒绝写死 v2.00 偏移）        │
  │  - 守护 CXD90057 OTP/RPMB 零写入并拦截 <v7.00 降级与跨机型镜像           │
  │  - 门禁校验：make verify-init2-escape && make verify-antirollback-guard │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ 需被动 S0..S6 串口诊断，或 p3 & p1 均无法通过 USB MSC 启动？
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 3：被动 1.8V RX-Only UART S0..S6 与 48000 波特率 BootROM Fastboot │
  │  - 被动抓包：1.8V 只收解码 S0..S6（passive_tx_bytes_emitted == 0）      │
  │  - 必须先拔除 VMC-BNCM1 LTC 线；严禁使用普通 Pico GP29                   │
  │  - 相机断开时先跑工作台自检：make verify-rp2040-fixture                  │
  │  - 接入 RP2040-Zero -DOPEN_DRAIN（1.8V，Pin 9/7/8 + Pin 2 GND）          │
  │  - 注入 0x92028000 / 0xFE020000；仅放行 oem dumpbrom / partition dump   │
  │    （flash:* / erase:* / oem format 全部硬拦截）                         │
  └──────┬──────────────────────────────────────────────────────────────────┘
         │ BootROM / SPI NOR / eMMC 总线无响应？
         ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ TIER 4：离线 O_RDONLY eMMC ISP、GPT/RPMB、Pre-EOL 与 FDT 取证诊断        │
  │  - 严格使用 O_RDONLY | O_NOFOLLOW | O_NONBLOCK 打开转储文件              │
  │  - 审计 Sector 0 ('8246')、15 分区 GPT CRC32 与 RPMB HMAC-SHA256 防重放 │
  │  - 审计 EXT_CSD[179/173/171/267..269 Pre-EOL] 与 FDT /chosen/bootargs ro│
  │  - 拦截 CMD42 强擦、永久写保护陷阱与 BOOT_PARTITION_ENABLE == 0          │
  │  - 10 支柱与 Phase 110 六柱总闸总验：                                    │
  │    make verify-10pillar-recovery && make verify-milestone-110           │
  └─────────────────────────────────────────────────────────────────────────┘
```
