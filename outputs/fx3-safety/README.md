# Sony FX3 Flash Safety, Boot Contract & Brick Recovery Suite (`fx3_safety` v2.0)

`outputs/fx3-safety/` provides the **defensive pre-flash verification, boot-contract validation, 5-level brick taxonomy diagnostic, and 4-layer fail-safe overlay/watchdog toolkit** for the **Sony ILME-FX3 (Ver. 7.02, Model ID `0x91030080`, SoC `CXD90057`)**.

---

## 1. Quick Start & CLI Commands

Run the unit test suite (8 tests covering `Sector 0`, `Backup.bin` `BK4\0` & `0xfa0080`, `LdrBkup.bin` `BKSB`, `0x02cf0214`/`0x02cf0218` boot-screen contract, all 5 brick levels, Tier-0 two-pass backup manifest verification, and the 12-Gate preflight evaluator):

```bash
PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```

### 1.1 Evaluate the 12-Gate Pre-Flash Safety Matrix (`evaluate-preflight`)
```bash
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety evaluate-preflight \
  --out outputs/fx3-safety/readiness-20261106-v2.json
```

### 1.2 Diagnose a Brick State & Select the Optimal Recovery Protocol (`diagnose-brick`)
```bash
# Example A: Userland appFw.so / im.elf crash with 4-Layer One-Shot Overlay active
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety diagnose-brick \
  --regions p15_usr --oneshot-overlay

# Example B: Main boot chain (p3) fault WITH /setting/updater/mode* pre-armed -> p1 SD/USB recovery
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety diagnose-brick \
  --regions p3_system --updater-armed

# Example C: Main boot chain (p3) fault WITHOUT p1 pre-armed -> no auto-failover in loader_nor.bin
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety diagnose-brick \
  --regions p3_system

# Example D: 5-blink / SPI NOR SPOF Hardware Brick
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety diagnose-brick \
  --led red_5_blinks --regions spi_nor --has-backup
```

### 1.3 Verify a 512-Byte Sony eMMC Sector 0 Partition Table (`verify-sector0`)
```bash
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-sector0 --input path/to/sector0.bin
```

### 1.4 Verify a Tier-0 Per-Body Two-Pass Backup Manifest (`verify-backup-manifest`)
```bash
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-backup-manifest --manifest path/to/manifest.json
```

### 1.5 Generate the Audited 4-Layer Fail-Safe Overlay & Watchdog Hook (`generate-failsafe-hook`)
```bash
PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety generate-failsafe-hook \
  --payload /log/mod/appFw.so --target /usr/lib/appFw.so --timeout 45
```

---

## 2. The 12-Gate Pre-Flash Safety Matrix (`readiness-20261106-v2.json`)

| Gate ID | Status | Technical Scope & Verification Evidence |
| :--- | :---: | :--- |
| **`G01_official_reference_integrity`** | `VERIFIED` | Official FX3 7.02 `appFw.so` (`545c5053...`), `libmpr.so` (`9aeef3b9...`), `cpapp-b.bin` (`c90d00d8...`), and 2.04/2.05 `p1` updater libraries verified. |
| **`G02_authenticated_usb_service_session`** | `VERIFIED_ON_HARDWARE` | Stage 285: 124-frame closed-loop MSC (`054C:0DA1`) $\to$ 7-round auth $\to$ `SERVICE` (`054C:0336`) $\to$ `read0` (88 B) $\to$ `STOP` $\to$ same-port MSC return (`native_return=0`). |
| **`G03_adjust_control_and_jiritsu_wire_contract`** | `VERIFIED_OFFLINE` | Stage 286 & 288: `AdjustControlFunc (0x0040, category 0x1001)` Phase 1/4/16 DMM lifecycle, `00` / `00 ff 00` prefixes, and `/tmp/jbusy` `ENOENT` precondition verified. |
| **`G04_offline_p1_recovery_and_rollback_engine`** | `VERIFIED_OFFLINE` | `fx3_recovery` v0.5: FAT12 cycle/cross-link check, SquashFS `pack_same_size` `Z_SYNC_FLUSH` length invariance, and byte-exact `rollback` restoration. |
| **`G05_static_aarch64_capture_workers`** | `VERIFIED_EMULATED` | Freestanding static AArch64 ELF workers (`fx3_p1_reader.c` & `fx3_boot_reader.c`) + custom `elflink.py` verified across 58 unit & fault-injection tests. |
| **`G06_bootloader_and_sector0_contract`** | `VERIFIED_STATIC` | Octal-SPI NOR sector map (`infomisc`/`DGU`/`LdrBkup`/`loader_nor`/`MIS+ddrtraining`/`cpapp-b`) and eMMC Sector 0 (`"8246"` `"2.00"` 30-entry table) audited. |
| **`G07_backup_bin_bk4_and_fa0080_contract`** | `VERIFIED_STATIC` | `loader_nor.bin` `BK4\0` selector (`0xfe04c7a8 -> 0xfe04d584`: `word4=0xaaaaaaaa`, `byte8=1`, signed `word2c`), `0xfa0080` 64-slot table, and `0x02cf0214`/`0218` contract verified. |
| **`G08_qemu_stage0_preflash_sandbox`** | `VERIFIED` | FX3 QEMU VM (AP70–AP105 Web UI `r10`–`r48`) + FX6 hybrid VM (180s zero-Oops `MEDIA_START`) + `detect_serial_faults.py` fail-closed assertion/fault detector. |
| **`G09_failsafe_4layer_overlay_and_watchdog`** | `VERIFIED_ARCHITECTURE` | Layer 1 RAM `mount --bind` + Layer 2 Clear-Before-Exec `/tmp/mod_arm_once` + Layer 3 45s BusyBox watchdog + Layer 4 3-strike `/setting/updater/mode+mode5` auto-arming. |
| **`G10_same_body_tier0_full_backup_checkpoint`** | `BLOCKED_PENDING_READBACK` | Requires two-pass idempotent readback dumps of physical camera `Sector 0`, `boot0/1`, `p1`, `p2` (`Backup.bin`/`psd.bin`/`defdet.bin`), `p6` (`Jiritsu`), `p12` (`/cert`), `p18` (`lensfile.bin`), and `SPI NOR` (`ddrtraining.dat`). |
| **`G11_independent_hardware_recovery_readiness`** | `DESIGN_VERIFIED_AWAITING_TIER0_BACKUP` | Proven that `loader_nor.bin` has **NO** auto-failover from `p3` to `p1` unless `/setting/updater/mode*` is armed; therefore `p1`-first staging or `init2` watchdog hook is mandatory before any `p15` trial. |
| **`G12_persistent_flash_write_authorization`** | `BLOCKED_BY_SAFETY_REDLINE` | Hard safety lock: persistent flash writes and cross-model partition flashing remain strictly prohibited until `G10` (Tier-0 full backup), `wireless_fault_isolation_ok`, `runtime_antibrick_ok`, and `multiport_tier3_harness_ok` are verified. |

---

## 3. Phase 28 End-to-End Phase H0 Hardware Rehearsal (`h0_hardware_rehearsal.py`)

Before plugging in a physical **ILME-FX3 (`0x91030080`)** body for read-only Tier-0 backup, run the 6-stage deterministic Phase H0 rehearsal pipeline:

```bash
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_safety.h0_hardware_rehearsal --unicorn
```

### 3.1 The 6 Rehearsal Stages (`run_h0_hardware_rehearsal`)
1. **Stage 1 (`multiport_bootrom_unbrick`)**: Validates the **Waveshare RP2040-Zero** (`-DOPEN_DRAIN`, `1.8V` open-drain High-Z, strict pinout `GP27 -> Pin 9 XReset`, `GP28 -> Pin 7 Cam UART RX`, `GP29 <- Pin 8 Cam UART TX`, `GND -> Pin 2`), rejects Raspberry Pi Pico `GP29` `VSYS/3` pull-down traps, tests the `48000`-baud `uart_boot` frame codec, enforces the `< 0xFFFFC000` BootROM WDT trap firewall, decodes `0x100D` (`13S`), and firewalls Fastboot (`18D1:4EE0`) to read-only inspection commands.
2. **Stage 2 (`macos_usb_transport_guard` / decoupled fallback)**: Exercises the macOS 26+ `IOUSBHost` `0xe00002be` (`kIOReturnExclusiveAccess`) quiescence (`>= 350 ms`) and bounded exponential backoff (`50/100/200/400/800 ms`), Vendor Control `(0x43, 1, 0x37FF, 0xD7AA)`, USB STALL non-retransmit guard, Senser v1 7-round auth (`054C:0DA1 -> 054C:0336`) vs Senser v2 RSA fail-closed rejection, and read-only Jiritsu (`0x40 / 0x1001`) firewall.
3. **Stage 3 (`runtime_antibrick_guards`)**: Audits the 4 field-proven 2026 BIONZ XR anti-brick invariants: `/etc/ld.so.preload` dynamic BusyBox deadlock ban + Clear-Before-Exec, Sony BusyBox `dd` truncation ban + 5-step atomic write contract, `nflasha10` (`12 MiB` VFAT) `0x10000009` headroom (`>= 2 MiB`), and `CAMSET` / `BK4\0` `PRODUCT_MODEL` (`ALCIN_UUD` enum `4`) NVRAM mutation lock.
4. **Stage 4 (`brick_classifier` v2)**: Verifies full symptom matrix classification (`5L+6S`, `7L+7S`, `6L+9S` `WF-12` Sony Notice `00342260`, `13S` `0x100D`, `0x10000009`, and `ld_so_preload_deadlock`) plus wireless fault isolation readiness.
5. **Stage 5 (`p1_symbol_autolocator` / decoupled fallback)**: Rehearses shifted-VMA `v7.02` `p1` 4-site autolocation (`libsdfileinputupdaterapi.so` + `libupdatercorecommon.so`) and byte-exact rollback restoration in synthetic `tmpfs` (with optional Unicorn AArch64 emulation via `--unicorn`).
6. **Stage 6 (`preflight.evaluate_12_safety_gates`)**: Evaluates all 12 safety gates including Gate `G12` redlines (`wireless_fault_isolation_ok`, `runtime_antibrick_ok`, `multiport_tier3_harness_ok`), guaranteeing `persistent_write_release == False` and deterministic `BLOCKED_*` fault-blocking.

### 3.2 Backward-Compatible Gate `G12` Extensions (`preflight.py`)

`evaluate_12_safety_gates(...)` adds three optional parameters defaulting to `None` (`wireless_fault_isolation_ok: Optional[bool] = None`, `runtime_antibrick_ok: Optional[bool] = None`, `multiport_tier3_harness_ok: Optional[bool] = None`). Leaving them `None` preserves 100% compatibility with existing callers; setting any of them to `False` deterministically blocks Gate `G12` with:
- `BLOCKED_BY_WIRELESS_FAULT_ISOLATION_REDLINE`
- `BLOCKED_BY_RUNTIME_ANTIBRICK_REDLINE`
- `BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE`

### 3.3 Public Package Exports (`fx3_safety/__init__.py`)
- Submodules: `boot_contracts`, `brick_classifier`, `crsdk_mishoe_ltc_spacc_guard`, `exfat_media_integrity_guard`, `h0_hardware_rehearsal`, `master_16gate_preflight`, `multiport_bootrom_unbrick`, `phantom48v_gimbal_and_22gate_guard`, `preflight`, `rig_groundloop_lensrail_and_20gate_guard`, `runtime_antibrick_guards`, `serial_fault_detector_v2`, `thermal_pwm_and_power_guard`, `usblan_ptpip_and_18gate_preflight`.
- Key entrypoints: `run_h0_hardware_rehearsal`, `H0RehearsalConfig`, `H0RehearsalReport`, `evaluate_12_safety_gates`, `evaluate_16_master_safety_gates`, `Master16GateReport`, `evaluate_18_master_safety_gates`, `Master18GateReport`, `evaluate_20gate_preflight`, `Master20GateReport`, `evaluate_22gate_preflight`, `Master22GateReport`, `evaluate_g13_multiport_and_mishoe_isolation`, `evaluate_g14_thermal_and_power_envelope`, `evaluate_g15_c2pa_and_calibration`, `evaluate_g16_stage_b_p12_and_wbi2_lock`, `evaluate_g17_exfat_and_client_media_isolation`, `evaluate_g18_usblan_ptpip_and_airplane_coexistence`, `evaluate_g19_rig_groundloop_and_lensrail`, `evaluate_g20_power_failover_and_rsv_salvage`, `evaluate_g21_xlr_phantom48v_and_hotpatch`, `evaluate_g22_gimbal_focus_torque_and_sensor_curtain`, `verify_c2pa_and_factory_calibration_immutability`, `verify_stage_b_p12_wf12_and_wbi2_lock`, `classify_brick_state`, `evaluate_runtime_antibrick_guards`, `validate_rp2040_multiport_harness`, `audit_fastboot_command_sequence`, `audit_serial_boot_telemetry`, `audit_round10_summary_telemetry`, `StreamingSerialFaultDetectorV2`, `verify_watchdog_budget`, `verify_multiport_ltc_vs_uart_boot`, `verify_mishoe_digital_audio_and_p11_coexistence`, `audit_crsdk_ptp2_session`, `audit_spacc_block_layer`, `evaluate_phase38_safety_guards`, `audit_donor_thermal_fan_power_contracts`, `verify_fan_thermal_envelope`, `verify_battery_and_usbpd_firewall`, `evaluate_thermal_pwm_and_power_guard`, `compute_exfat_boot_checksum`, `parse_exfat_vbr`, `verify_exfat_boot_region`, `inspect_sony_media_tree`, `verify_dual_slot_media_firewall`, `parse_p1_fat12_fat16_vbr`, `verify_p1_vs_exfat_filesystem_separation`, `evaluate_exfat_media_integrity_guard`, `audit_usblan_ptpip_donor_contracts`, `verify_usblan_wired_control_and_airplane_coexistence`, `classify_usblan_ptpip_or_mc_operation`, `evaluate_ptpip_15740_packet`, `audit_usblan_ptpip_and_mc_firewall`, `audit_rig_20gate_donor_contracts`, `verify_rig_power_sequence`, `verify_rig_dtap_hdmi_groundloop_firewall`, `verify_emount_hot_detach_rail_and_ibis_park`, `inspect_sony_rsv_salvage_structure`, `verify_power_failover_ups_and_rsv_salvage`, `audit_phase77_donor_contracts`, `verify_xlr_h1_channel`, `verify_xlr_h1_phantom_48v_firewall`, `verify_gimbal_focus_torque_and_laser_shutter_guard`.

### 3.4 Running Tests in Normal & Clean-Room Modes
```bash
# Normal mode (with fx3_recovery sibling integration, 326 tests in ~0.7s)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v

# Clean-Room mode (decoupled synthetic-only mode, 326 tests in ~0.7s)
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```

---

## 4. Phase 32 Fail-Closed Serial & Kernel Telemetry Fault Detector v2 (`serial_fault_detector_v2.py`)

`serial_fault_detector_v2.py` provides deterministic **streaming (`StreamingSerialFaultDetectorV2`)** and **batch (`audit_serial_boot_telemetry`)** fail-closed analysis across FX3 `4.9.337-scel+` serial logs and Stage-A/B telemetry:

1. **Kernel Panics, Oops & Sony Crash Traces**: Detects `Unable to handle kernel`, `Kernel panic`, `Internal error: Oops`, `SError Interrupt`, `BUG:`, `ZZTGKILL`, `ZZSTACK`, `ZZEXCSTACK`, `SIGSEGV`/`SIGABRT`, and `assert at`.
2. **Dynamic Linker & Device/Module Missing**: Detects `MISSSO`, `MISSDEV`, `IMOPEN`, `MODLOAD`, `error while loading shared libraries`, and `/etc/ld.so.preload` dynamic BusyBox deadlock markers.
3. **Sync & IPC Hangs**: Detects `ZZFUTEX`, `ZZCOMPLETE`, `INFO: task .* blocked for more than`, unpatched `WlanResourceMainThread` `0x70d4` `handleFatalError` loops, and unshimmed UIPC `0x92d2091c`/`0x91db059b` blocking timeouts.
4. **`TIMER-IP` `220.0s` & `90.0s` Stage-A Watchdog Budget Verifier (`verify_watchdog_budget`)**: Verifies `WDT_SET_STOP` and active (non-commented) Stage-A `/tmp/mod_arm_once` Clear-Before-Exec occur strictly `< 90.0s` (soft guard) and `< 220.0s` (`TIMER-IP` 3m40s hardware watchdog ceiling), strictly prior to overlay/appFw execution.
5. **Degraded-Safe vs Fatal Classifier + `brick_classifier.py` Cross-Links**:
   - Expected non-blocking degraded events (`WF12_DEGRADED_RADIO_OFF`, `BT_DEGRADED_DISABLED` `0xbb9`, `P11` detached-grip ACK `0x91db059b`, `P11` `/dev/rtc0` `open_ok=0` probe, `P4` ND `Clear`) $\rightarrow$ `ALLOWED_DEGRADED`.
   - Fatal abort events (`"System Error"`, `0x10000009` `nflasha10` VFAT exhaustion, Verify-Before-Mount SHA mismatch, `nop_count > 0` or substitution invariants in `FX6_NATIVE_FAITHFUL=1` mode) $\rightarrow$ `FAIL_CLOSED_ABORT` with automatic cross-links to `classify_brick_state(...)` recovery playbooks.
6. **Round 10 Telemetry Audit (`audit_round10_summary_telemetry`)**: Reads `reports/2026-11-14-round10-fx6-on-fx3-full-icon-presenter/summary.json` strictly with `os.O_RDONLY` (with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback) and verifies all 4 runs (`r10a`..`r10d`) under `4.9.337-scel+`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety.serial_fault_detector_v2 --round10-summary
```

---

## 5. Phase 38 Executable CrSDK PTP2, 24-Pin MI-Shoe, Multi-Port LTC & SPACC Guard (`crsdk_mishoe_ltc_spacc_guard.py`)

`crsdk_mishoe_ltc_spacc_guard.py` turns the four Phase 34 hardware/protocol safety findings into deterministic, fail-closed verifiers (keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked):

1. **Multi-Port 15-Pin `VMC-BNCM1` LTC vs `RP2040-Zero` `uart_boot` Guard (`verify_multiport_ltc_vs_uart_boot`)**:
   - Blocks simultaneous `VMC-BNCM1` LTC + `RP2040-Zero` `uart_boot` attachment (`BLOCKED_MULTIPORT_PIN_SHARING_HAZARD`), any `2Vpp-5Vpp` SMPTE LTC injection onto `CXD90057` `1.8V/3.15V` UART `Pin 7/8/9`, DC-coupled/overvoltage LTC (`BLOCKED_LTC_OVERVOLTAGE_HAZARD`), and wrong `Pin 6 <-> Pin 2` ID-resistor keying (`100 kOhm` LANC vs `680 kOhm` LTC -> `BLOCKED_WRONG_ID_RESISTOR_KEYING`).
   - Validates FX3 Multi-Port unidirectional LTC IN fallback (`Movie` + `Preset` + `Free Run` + fps match + `P11` `0x92d2091c` RTC shim) while rejecting TC OUT requests (`BLOCKED_FX3_NO_BNC_TC_OUT`).
2. **24-Pin MI-Shoe Digital Audio (`XLR-H1` / `ECM-B1M`) & `P11` `0x91db059b` Coexistence (`verify_mishoe_digital_audio_and_p11_coexistence`)**:
   - Verifies 6-bin `ID1..ID3` ladder, `LOGIC_VDD` (`2.8V-3.15V`), `UNREG` (`6.1V-8.4V <= 1.6A`), `48kHz / 24-bit` 4ch (`CH1..CH4`, `4,608,000 bps`) / 2ch PCM framing, `libInfraHotshoe.so` (`0x5d90`) `E_TMO = -50 -> 0x8000` non-blocking safety, and `P11` detached Smart Handle ACK (`0x91db059b` -> `0x88000002`, rejecting spoofed attached `0x88000001`).
3. **Sony `CrSDK` PTP2 (`0x9201..0x9209`) Remote Control Firewall (`audit_crsdk_ptp2_session`, `classify_crsdk_ptp2_request`)**:
   - Enforces Sony Vendor Extension `0x00000011` (blocking Nikon `0x920a..0x920f` collisions), 3-step `0x9201` `SDIOConnect` `(1,0,0)->(2,0,0)->(3,0,0)` handshake, `0xc8` (`SONY_PROTOCOL_2_00`) `libgphoto2#676` fallback, and permits safe live-shooting writes (`ExposureIndex`, `ShutterAngle` millidegrees, `WhiteBalance`, `LogShootingMode`, `MovieRec`) while blocking firmware updates, `PRODUCT_MODEL` (`ALCIN_UUD`) NVRAM tampering, and raw service-mode escalation (`054C:0336` / `SET_FILE_PATH` / `AdjustControl`).
4. **`CXD90057` `SPACC` (`0xf7fc0000`) `AES-XTS-256` Block-Layer Hazard Guard (`audit_spacc_block_layer`)**:
   - Enforces `/dev/cnflasha*` (SPACC sector-tweak decrypted plaintext) vs `/dev/nflasha*` (raw ciphertext on `type=5, flag&1` partitions), blocking raw `nflasha*` mounts/plaintext reads on XTS partitions, `cnflasha*` reads on plaintext/WBI partitions, mixed `nflasha`/`cnflasha` session access, and userland `SPACC` MMIO (`0xf7fc0000..0xf7fcffff`) access with `BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety.crsdk_mishoe_ltc_spacc_guard --self-check --json
```

---

## 6. Phase 44 FX3 Fan PWM Thermal Envelope, `NP-FZ100` vs `BP-U` & USB-PD Guard (`thermal_pwm_and_power_guard.py`)

`thermal_pwm_and_power_guard.py` closes cross-body thermal cooling and battery/USB-PD power-domain hazards between **ILME-FX6 (`14.4V` 4S `BP-U` / `19.5V` DC-IN + large blower)** and **ILME-FX3 (`7.2V` 2S `NP-FZ100` + `9V/3A` `27W` USB-PD + compact internal fan)** (keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked):

1. **`O_RDONLY` Donor Thermal/Fan/Power Audit (`audit_donor_thermal_fan_power_contracts`)**:
   - Reads FX3 `v7.02` and FX6 `v6.01` `libfan.so`, `libBusPower.so`, `libUsbBusPower.so`, `FX3-CX95900_ALLLANG-Backup.bin` / `CX95898_NTSC.bin` (`0x0238000a..0x0238006d` `g_bkup_dev_temp_bkid_list`), `appFw.so`, and `cpapp-b.bin` strictly via `os.O_RDONLY` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` pinned fallback.
2. **FX3 Compact Fan PWM Thermal Runaway Guard (`verify_fan_thermal_envelope`, `evaluate_fan_mode_matrix`)**:
   - Verifies the Stage-A/B `libfan.so` `@ 0x1dec` (`_Z19fan_i_bkup_is_validv` -> `mov w0, #1; ret`) handshake across all 4 menu fan modes (`AUTO1`, `AUTO2`, `MINIMUM`, `OFF_IN_REC`), enforcing mandatory active cooling override when `CXD90057` SoC `>= 62.0°C` or CFexpress Type A slot A/B `>= 68.0°C`, soft recording warning at `>= 82.0°C`, and fail-closed graceful unmount + RAM-overlay teardown at `>= 90.0°C`.
3. **`NP-FZ100` (`2S 7.2V`) vs `BP-U` (`4S 14.4V`) InfoLITHIUM Scaling & USB-PD `9V/3A` Firewall (`normalize_npfz100_infolithium_mv`, `verify_battery_and_usbpd_firewall`)**:
   - Proves `NP-FZ100` (`6200..8400 mV`) is normalized via InfoLITHIUM SOC (`%` + `remaining_minutes`) rather than raw `4S BP-U` `11500 mV` emergency-cutoff comparators (preventing false `0%` boot shutdowns), and enforces `>= 80%` SOC (`>= 7800 mV`) + stable USB-PD `9V/3A` (`>= 27W`, VBUS droop `<= 450 mV`) for `H0`/`H1` rehearsals.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-thermal-power-guard [--clean-room] [--json]
```

---

## 7. Phase 50 16-Gate Master Safety Preflight Engine (`master_16gate_preflight.py`)

`master_16gate_preflight.py` (`fx3-master-16gate-preflight-v1`) composes `preflight.evaluate_12_safety_gates` (`G01..G12`, leaving `preflight.py` untouched) with four deterministic Stage-B / Hardware-Session Safety Gates (`G13..G16`), keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **`G13` (`MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION`)**:
   - Integrates Phase 38 `evaluate_phase38_safety_guards` + `validate_rp2040_multiport_harness`: blocks simultaneous `VMC-BNCM1` LTC and `uart_boot` attachment (`Pin 7/8/9` & `680 kOhm` vs `100 kOhm` ID-resistor conflicts), enforces Waveshare `RP2040-Zero` `-DOPEN_DRAIN` (`1.8V/3.15V`, rejecting Raspberry Pi Pico `GP29 VSYS/3` pull-down & push-pull `3.3V`), preserves `P11` `0x91db059b -> 0x88000002` + `XLR-H1` MI-Shoe coexistence (`xlr_h1_preserved == True`), and enforces `CrSDK` PTP2 + `SPACC` `cnflasha*` XTS separation.
2. **`G14` (`THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE`)**:
   - Integrates Phase 44 `evaluate_thermal_pwm_and_power_guard`: enforces `CXD90057 SoC < 62.0°C` start headroom before launching a hardware/Stage-B session, FX3 compact fan PWM envelope (`libfan.so @ 0x1dec`, `82°C` warning, `90°C` graceful unmount & teardown), `NP-FZ100 >= 80% SOC / >= 7800 mV` InfoLITHIUM normalization (blocking `4S BP-U 11500 mV` false-`0%` comparators), and `USB-PD 9V/3A` (`>= 27W`) with VBUS droop `<= 450 mV`.
3. **`G15` (`C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY`)**:
   - Blocks any planned mount, write, or script targeting `/dev/cnflasha*`, `RPMB`, TrustZone/OP-TEE or Sony C2PA credentials (`RQ_LIC.DAT`, `sigcert.p12/.pfx`, `p12:/cert`, `/dev/tee*`), or factory IMX510/IBIS/lens calibration regions (`p2:/setting/{psd.bin,defdet.bin,Backup.bin}`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin`, `SPI NOR ddrtraining.dat`, `adjstctl A_*`); enforces `calibration_mutation_bytes == 0` and exFAT media power-loss hygiene (`VolumeDirty` VBR `0x6A` / unfinalized `.RSV`).
4. **`G16` (`STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK`)**:
   - Verifies FX6 `libWlanResource.so` `O_RDONLY` integrity (`56464 B`, SHA-256 `eb7785e0...`) and Stage-B `P12` `0x70d4` (`_Z16handleFatalErrorv` -> `00008052c0035fd6`, `patched_rc == 0`) + `BK4\0` Airplane-Mode RAM shadow (`{0x019e0012: 0, 0x0051000f: 0, 0x01a20002: 0}` for Sony Notice `00342260` `WF-12` bootloop immunity), `wbi_mutation_bytes == 0`, `cp_mutation_bytes == 0`, `nvram_persistent_writes == 0`, and hard-locked `persistent_emmc_writes_authorized == False`.

```bash
# Offline 13-gate check (G01..G09 + G13..G16) with local O_RDONLY donor audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-16-gates [--clean-room] [--dry-run-tier0] [--json]
```

---

## 8. Phase 57 Non-Journaled `exFAT` (`BootChecksum` / `VolumeDirty` / `.RSV`) & Dual CFexpress Firewall (`exfat_media_integrity_guard.py`)

`exfat_media_integrity_guard.py` (`fx3-exfat-media-integrity-guard-v1`) operationalizes Wave-4 Phase 50 non-journaled `exFAT` media safety so no Stage-A/B or `H0`/`H1` hardware rehearsal can risk live client footage or run with a dirty/corrupted media card (keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked):

1. **Pure-Python `exFAT` VBR (`EXFAT   `) & 12-Sector `BootChecksum` Verifier (`parse_exfat_vbr`, `compute_exfat_boot_checksum`, `verify_exfat_boot_region`)**:
   - Validates Main (`Sectors 0..11`) and Backup (`Sectors 12..23`) Boot Regions: `FileSystemName == b"EXFAT   "`, `MustBeZero` (`53` zero bytes), power-of-two `BytesPerSectorShift` (`9..12`, `512..4096 B`) and `SectorsPerClusterShift` (`<= 25 - BytesPerSectorShift`), `BootSignature == 0xAA55`, and volume geometry.
   - Computes exact Microsoft/SDA 32-bit rolling `BootChecksum` across Sectors `0..10` (`12..22` for Backup), explicitly skipping `VolumeFlags` (`106..107`) and `PercentInUse` (`112`), verifying uniform checksum slots in Sector `11`/`23`, and blocking `VolumeDirty` (`0x0002`) or `MediaFailure` (`0x0004`).
2. **Sony Camera Media Tree (`XDROOT` vs `PRIVATE/M4ROOT` + `.RSV`) & Dual-Slot Firewall (`inspect_sony_media_tree`, `verify_dual_slot_media_firewall`)**:
   - Inspects both `Slot A` and `Slot B` cards and **blocks `H0`/`H1` trial entry fail-closed** if non-empty FX6 `XDROOT/Clip/*.MXF`, FX3 `PRIVATE/M4ROOT/CLIP/*.MP4` / `M4ROOT/CLIP/*.MP4`, `DCIM/*`, unfinalized Sony `.RSV` power-loss recovery clips, or `FOUND.000/*.CHK` (`chkdsk /f` remnants) are present.
3. **Strict `p1` (`FAT12`/`FAT16`) vs External `exFAT` Separation (`parse_p1_fat12_fat16_vbr`, `verify_p1_vs_exfat_filesystem_separation`)**:
   - Audits internal `p1` (`nflasha1` via `os.O_RDONLY` in Local Donor mode or synthetic `FAT12` in `FX3_FX6_FORCE_CLEAN_ROOM=1` mode), rejects `EXFAT   `/`FAT32` on `p1`, and blocks any device/mount overlap or cross-domain write onto `/dev/nflasha*`, `/dev/cnflasha*`, `/setting`, or `/boot`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-media-guard [--clean-room] [--json]
```

---

## 9. Phase 61 Wired `USB-LAN` / `PTP-IP 15740` Security Firewall & 18-Gate Master Safety Preflight Engine (`usblan_ptpip_and_18gate_preflight.py`)

`usblan_ptpip_and_18gate_preflight.py` (`fx3-usblan-ptpip-18gate-preflight-v1`) operationalizes Phase 57 (`exfat_media_integrity_guard`) and Phase 58 (`Wave-5 USB-LAN / PTP-IP`) into an executable **18-Gate Master Safety Preflight (`G01..G18`)** while leaving `preflight.py` and `master_16gate_preflight.py` untouched and keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Wired `USB-LAN` (`CDC-NCM` / `RTL8153` / `AX88179`) & `P12` Airplane-Mode Coexistence (`verify_usblan_wired_control_and_airplane_coexistence`, `audit_usblan_ptpip_donor_contracts`)**:
   - Inspects the 7 compact FX6 donor artifacts (`cdc_ncm.ko`, `rndis_host.ko`, `libNetServiceEther.so`, `libInfraPtpControl.so`, `libptp.so`, `libSshInfraNetworkCommon.so`, `libWlanResource.so`) strictly via `os.O_RDONLY` (with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback).
   - Enforces wired-only `CDC-NCM` (`1000 Mbps` `RTL8153` or original `AX88179` on `eth0`/`usblan0`, rejecting `RNDIS`, `CDC-ECM`, `AX88179A/B`, `2.5G/5G/10G`, wireless interfaces, and missing FX3 Manual same-subnet gateways) while `P12` (`0x70d4 -> rc=0`) + `BK4\0` Airplane-Mode keeps Wi-Fi (`wifi_radio_enabled == False`) and Bluetooth (`/dev/ttyAMA3`, `bt_hci_tx_packets == 0`) 100% disabled (`wf12_00342260_immune == True`).
2. **`PTP-IP` (`TCP 15740`) & `Monitor & Control` (`UDP 1900`, `HTTP/HTTPS`) Fail-Closed Firewall (`classify_usblan_ptpip_or_mc_operation`, `evaluate_ptpip_15740_packet`, `audit_usblan_ptpip_and_mc_firewall`)**:
   - Whitelists safe shooting and monitoring operations (`GetDeviceInfo`, `GetEvent`, live-view/waveform streams, `ISO`/`EI`/`Shutter`/`WB`/AF touch-focus, SSDP `UDP 1900` `M-SEARCH`, `POST /sony/camera` safe shooting RPCs).
   - Hard-blocks fail-closed all restricted vendor opcodes (`0x9280..0x92FF`), `SendObjectInfo`/`SendObject` `.dat`/`.ufu` firmware payloads, HTTP `/fwupdate`, service-mode unlocks, NVRAM `BK4` writes, raw partition transfers, and raw `telnet`/`rsh` shells with `persistent_emmc_writes_authorized == False`.
3. **18-Gate Master Safety Preflight (`evaluate_18_master_safety_gates`)**:
   - **`G17` (`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`)**: Composes Phase 57 `exfat_media_integrity_guard` (blocking `H0`/`H1` on `VolumeDirty`, invalid 12-sector `BootChecksum`, client `XDROOT`/`M4ROOT` footage, `.RSV` unfinalized files, or `p1` filesystem overlap).
   - **`G18` (`USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE`)**: Enforces wired-only `USB-LAN` safe-opcode filtering + `P12` `BK4` Airplane-Mode wireless radio silence (`wifi_radio_enabled == False`, `persistent_emmc_writes_authorized == False`).

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-18-gates [--clean-room] [--dry-run-tier0] [--json]
```

---

## 10. Phase 69 Rig D-Tap/HDMI Ground-Loop Interlock, E-Mount Hot-Detach Rail Guard, Power-Loss `.RSV` Salvage & 20-Gate Master Preflight (`rig_groundloop_lensrail_and_20gate_guard.py`)

`rig_groundloop_lensrail_and_20gate_guard.py` (`fx3-rig-groundloop-lensrail-20gate-guard-v1`) composes `usblan_ptpip_and_18gate_preflight.py` (`G01..G18`, leaving `preflight.py`, `master_16gate_preflight.py`, and `usblan_ptpip_and_18gate_preflight.py` untouched) with two new physical cinema-rig and power-failover gates **`G19`** and **`G20`** into a deterministic **20-Gate Master Safety Preflight (`G01..G20`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **D-Tap / HDMI Type-A Common-Mode Ground-Loop & Hot-Plug ESD Firewall (`verify_rig_dtap_hdmi_groundloop_firewall`, `verify_rig_power_sequence`, Gate `G19`)**:
   - Models shared `14.8V` V-Mount / Gold-Mount cinema rigs (`FX3` via `USB-PD` / `NP-FZ100` dummy coupler + `Atomos Ninja` / `SmallHD` external HDMI monitor).
   - Detects the lethal **open-negative ground-return fault** (D-Tap `GND` disconnect before `+14.8V` forcing return current across HDMI `Pin-17` DDC/CEC/TMDS shield and threatening the `CXD90057` HDMI ESD array).
   - Enforces safe topologies (`INTERNAL_NP_FZ100_ISOLATED_USBPD`, `OPTICAL_FIBER` HDMI exemption, or `ISOLATED_DCDC_BOX` + strict canonical sequence `CONNECT_POWER_CABLES -> CONNECT_HDMI -> POWER_ON_CAMERA -> POWER_ON_MONITOR` and reversed teardown, or ground-first locking connector with warning), while hard-blocking `HDMI +5V Pin-18` reverse back-feed (`> 5.25V` or `> 55 mA`).
2. **E-Mount `V_LENS` (`3.3V` Logic / `5.0V` Actuator) Hot-Detach Crowbar & Stock-CP IBIS Park (`verify_emount_hot_detach_rail_and_ibis_park`, Gate `G19`)**:
   - Models the 10-pin Sony E-Mount bayonet contact array during live hot-detach: requires `LENS_DET` (Pin 9) interrupt to crowbar `V_LENS_SERVO_5V0` to `0.0 mA` within `<= 2.0 ms` (strictly inside the `3.5 ms` rotary contact-wipe window) and issue Stock-CP `0x0400` (`0x1400` completion) IBIS Center-Lock park with `cp_mutation_bytes == 0`.
3. **Sudden Power-Loss `.RSV` Clip-Salvage & `USB-PD` Battery-Less Trap Guard (`verify_power_loss_ups_and_rsv_salvage`, `inspect_sony_rsv_salvage_structure`, Gate `G20`)**:
   - Audits sudden `USB-PD 9V/3A` unplug during `4K 60p XAVC S-I` (`600 Mbps`) recording: verifies zero-drop `NP-FZ100` UPS failover when `soc_pct >= 15%` and `>= 6.8V` under load (`0` lost frames, clean `moov`/`MXF FooterPartition`), fails closed (`BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT`) on battery-less `USB-PD` or `< 15%` / `< 6.8V` / `< 10%` reserve, and performs read-only `.RSV` emergency salvage container structure inspection (`physical_media_writes == 0`, `persistent_emmc_writes_authorized == False`).
4. **20-Gate Master Safety Preflight (`evaluate_20gate_preflight`) & `verify-20-gates` CLI**:
   - **Offline default mode**: `17/20` gates pass (`G01..G09`, `G13..G20` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `20/20` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False` and `persistent_emmc_writes_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-20-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 11. Phase 77 `XLR-H1 +48V` Phantom Transducer Burnout Firewall, Gimbal / Follow-Focus Torque & Laser-CMOS Guard + 22-Gate Master Preflight (`phantom48v_gimbal_and_22gate_guard.py`)

`phantom48v_gimbal_and_22gate_guard.py` (`fx3-phantom48v-gimbal-22gate-preflight-v1`) composes `rig_groundloop_lensrail_and_20gate_guard.py` (`G01..G20`, leaving `preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, and `rig_groundloop_lensrail_and_20gate_guard.py` untouched) with two new physical audio-phantom and gimbal/laser/shutter gates **`G21`** and **`G22`** into a deterministic **22-Gate Master Safety Preflight (`G01..G22`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **`XLR-H1 +48V` Phantom Power Transducer Burnout & Hot-Patch Transient Firewall (`verify_xlr_h1_phantom_48v_firewall`, `verify_xlr_h1_channel`, Gate `G21`)**:
   - Models the 24-pin MI-Shoe `XLR-H1` top handle's dual XLR/TRS combo inputs (`INPUT1`, `INPUT2`: `LINE / MIC / MIC+48V`) plus `INPUT3` `3.5mm` stereo Plug-In-Power (`2.5V`).
   - Hard-blocks lethal `+48V` mismatches (`BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD`): passive ribbon microphones without Cloudlifter/transformer isolation on `MIC+48V`, unbalanced `3.5mm TRS -> XLR` wireless receivers (`DJI Mic`, `Rode`, `Sennheiser`) or SMPTE LTC timecode generators (`Tentacle Sync`, `Deity TC-1`) on `MIC+48V`, dynamic/line sources on `MIC+48V`, and XLR hot-plug/unplug events while `+48V` boost is energized or ADC mute is un-ramped or residual voltage `> 1.0V`.
   - Permits balanced condenser shotgun/boom mics (`Sennheiser MKH416`, `Sony ECM-VG1`, `Sony ECM-B10`, `Sony ECM-XM1`) on `MIC+48V`, and requires `LINE` or `MIC` (`48V OFF`) for wireless receivers, dynamic mics, unisolated ribbons, and LTC sources.
2. **Gimbal (`DJI RS3/RS4 Pro` `USB-C CrSDK` / `Multi-Port`), Follow-Focus Torque & Laser-CMOS / Shutter Curtain Guard (`verify_gimbal_focus_torque_and_laser_shutter_guard`, Gate `G22`)**:
   - **Follow-Focus Gear Motor Endpoint Calibration & Torque Guard**: Blocks uncalibrated infinite-spin `14.8V` focus motors on fly-by-wire E-Mount lenses without hard stops unless a lens-support rod clamp is installed OR motor torque limit `<= 0.35 N·m` with calibrated soft A/B stops (`BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR`).
   - **USB-C vs Multi-Port Dual-Control Conflict Guard**: Blocks simultaneous conflicting `REC/Zoom/Iris` commands on BOTH `USB-C CrSDK` AND `Multi-Port RSS` (`single_control_bus_arbitrated == True`), and enforces `IBIS Mode` in `Standard` or `Off` (blocking `Active` crop drift) when gimbal pan-follow is active.
   - **Class-3B/4 Venue Laser & Mechanical Shutter Dust-Curtain Park Check**: Flags and blocks high-risk concert/club laser environments (`venue_laser_present = True` or `CLASS_3B`/`CLASS_4` without optical laser-cut filter), and verifies FX3's focal-plane shutter remains parked `OPEN` (`shutter_when_power_off = "OFF"` default unless explicitly enabled with lens-cap swap rules).
3. **22-Gate Master Safety Preflight (`evaluate_22gate_preflight`) & `verify-22-gates` CLI**:
   - **Offline default mode**: `19/22` gates pass (`G01..G09`, `G13..G22` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `22/22` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False` and `persistent_emmc_writes_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-22-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```



