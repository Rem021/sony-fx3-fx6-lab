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
- Submodules: `boot_contracts`, `brick_classifier`, `crsdk_mishoe_ltc_spacc_guard`, `dewpoint_tec_usbc_and_24gate_guard`, `exfat_media_integrity_guard`, `h0_hardware_rehearsal`, `hdmi_aoc_5v_cfexpress_and_36gate_guard`, `intake_occlusion_tripod_and_26gate_guard`, `master_16gate_preflight`, `monsoon_mishoe_cagetwist_and_40gate_guard`, `multiport_bootrom_unbrick`, `phantom48v_gimbal_and_22gate_guard`, `pl_cantilever_dummybatt_and_32gate_guard`, `preflight`, `realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard`, `realhw_c2pa_tc_gyro_and_56gate_guard`, `realhw_cfexpress_ufu_el3_and_52gate_guard`, `realhw_cxd90058_sabin_seal_and_54gate_guard`, `realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard`, `realhw_dualmedia_bench_interlock_and_58gate_guard`, `realhw_emount_info3d_hdmi_braw_and_62gate_guard`, `realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard`, `realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard`, `realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard`, `realhw_framing_usbpower_lun_antiflicker_and_94gate_guard`, `realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard`, `realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard`, `realhw_jiritsu_cnflasha_and_44gate_guard`, `realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard`, `realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard`, `realhw_pnflasha_mtdro_rfnvs_and_48gate_guard`, `realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard`, `realhw_service0336_mpr_ibis_and_46gate_guard`, `realhw_shoe_audio_wind_saveload_c3_and_92gate_guard`, `realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard`, `realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard`, `realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard`, `realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard`, `realhw_uart1v8_imx510_cal_and_50gate_guard`, `realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard`, `rig_groundloop_lensrail_and_20gate_guard`, `runtime_antibrick_guards`, `saltspray_haze_followfocus_and_34gate_guard`, `sensor_curtain_subzero_and_28gate_guard`, `serial_fault_detector_v2`, `thermal_pwm_and_power_guard`, `usbpd_trigger_multiterminal_and_38gate_guard`, `usblan_ptpip_and_18gate_preflight`, `vp_strobe_vehiclerig_ibis_and_42gate_guard`, `wireless_tx_emi_endurance_and_30gate_guard`.
- Key entrypoints: `run_h0_hardware_rehearsal`, `H0RehearsalConfig`, `H0RehearsalReport`, `evaluate_12_safety_gates`, `evaluate_16_master_safety_gates`, `Master16GateReport`, `evaluate_18_master_safety_gates`, `Master18GateReport`, `evaluate_20gate_preflight`, `Master20GateReport`, `evaluate_22gate_preflight`, `Master22GateReport`, `evaluate_24gate_preflight`, `Master24GateReport`, `evaluate_26gate_preflight`, `Master26GateReport`, `evaluate_28gate_preflight`, `Master28GateReport`, `evaluate_30gate_preflight`, `evaluate_30_master_safety_gates`, `Master30GateReport`, `evaluate_32gate_preflight`, `evaluate_32_master_safety_gates`, `Master32GateReport`, `evaluate_34gate_preflight`, `evaluate_34_master_safety_gates`, `Master34GateReport`, `evaluate_36gate_preflight`, `evaluate_36_master_safety_gates`, `Master36GateReport`, `evaluate_38gate_preflight`, `evaluate_38_master_safety_gates`, `Master38GateReport`, `evaluate_40gate_preflight`, `evaluate_40_master_safety_gates`, `Master40GateReport`, `evaluate_42gate_preflight`, `evaluate_42_master_safety_gates`, `Master42GateReport`, `evaluate_44gate_preflight`, `evaluate_44_master_safety_gates`, `Master44GateReport`, `evaluate_46gate_preflight`, `evaluate_46_master_safety_gates`, `Master46GateReport`, `evaluate_48gate_preflight`, `evaluate_48_master_safety_gates`, `Master48GateReport`, `evaluate_50gate_preflight`, `evaluate_50_master_safety_gates`, `Master50GateReport`, `evaluate_52gate_preflight`, `evaluate_52_master_safety_gates`, `Master52GateReport`, `evaluate_54gate_preflight`, `evaluate_54_master_safety_gates`, `Master54GateReport`, `evaluate_56gate_preflight`, `evaluate_56_master_safety_gates`, `Master56GateReport`, `evaluate_58gate_preflight`, `evaluate_58_master_safety_gates`, `Master58GateReport`, `evaluate_60gate_preflight`, `evaluate_60_master_safety_gates`, `Master60GateReport`, `evaluate_62gate_preflight`, `evaluate_62_master_safety_gates`, `Master62GateReport`, `evaluate_64gate_preflight`, `evaluate_64_master_safety_gates`, `Master64GateReport`, `run_66_gate_preflight`, `evaluate_66gate_preflight`, `evaluate_66_master_safety_gates`, `Master66GateReport`, `run_68_gate_preflight`, `evaluate_68gate_preflight`, `evaluate_68_master_safety_gates`, `Master68GateReport`, `run_70_gate_preflight`, `evaluate_70gate_preflight`, `evaluate_70_master_safety_gates`, `Master70GateReport`, `run_72_gate_preflight`, `evaluate_72gate_preflight`, `evaluate_72_master_safety_gates`, `Master72GateReport`, `run_74_gate_preflight`, `evaluate_74gate_preflight`, `evaluate_74_master_safety_gates`, `Master74GateReport`, `run_76_gate_preflight`, `evaluate_76gate_preflight`, `evaluate_76_master_safety_gates`, `Master76GateReport`, `run_78_gate_preflight`, `evaluate_78gate_preflight`, `evaluate_78_master_safety_gates`, `Master78GateReport`, `run_80_gate_preflight`, `evaluate_80gate_preflight`, `evaluate_80_master_safety_gates`, `Master80GateReport`, `run_82_gate_preflight`, `evaluate_82gate_preflight`, `evaluate_82_master_safety_gates`, `Master82GateReport`, `run_84_gate_preflight`, `evaluate_84gate_preflight`, `evaluate_84_master_safety_gates`, `Master84GateReport`, `run_86_gate_preflight`, `evaluate_86gate_preflight`, `evaluate_86_master_safety_gates`, `Master86GateReport`, `run_88_gate_preflight`, `evaluate_88gate_preflight`, `evaluate_88_master_safety_gates`, `Master88GateReport`, `run_90_gate_preflight`, `evaluate_90gate_preflight`, `evaluate_90_master_safety_gates`, `Master90GateReport`, `run_92_gate_preflight`, `evaluate_92gate_preflight`, `evaluate_92_master_safety_gates`, `Master92GateReport`, `run_94_gate_preflight`, `evaluate_94gate_preflight`, `evaluate_94_master_safety_gates`, `Master94GateReport`, `G63`, `G64`, `G65`, `G66`, `G67`, `G68`, `G69`, `G70`, `G71`, `G72`, `G73`, `G74`, `G75`, `G76`, `G77`, `G78`, `G79`, `G80`, `G81`, `G82`, `G83`, `G84`, `G85`, `G86`, `G87`, `G88`, `G89`, `G90`, `G91`, `G92`, `G93`, `G94`, `evaluate_g13_multiport_and_mishoe_isolation`, `evaluate_g14_thermal_and_power_envelope`, `evaluate_g15_c2pa_and_calibration`, `evaluate_g16_stage_b_p12_and_wbi2_lock`, `evaluate_g17_exfat_and_client_media_isolation`, `evaluate_g18_usblan_ptpip_and_airplane_coexistence`, `evaluate_g19_rig_groundloop_and_lensrail`, `evaluate_g20_power_failover_and_rsv_salvage`, `evaluate_g21_xlr_phantom48v_and_hotpatch`, `evaluate_g22_gimbal_focus_torque_and_sensor_curtain`, `evaluate_g23_dewpoint_and_tec_condensation`, `evaluate_g24_pmic_5v_and_usbc_strain`, `evaluate_g25_sigma_fan_intake_exhaust`, `evaluate_g26_tripod_torque_and_housing_vacuum`, `evaluate_g27_sensor_curtain_and_ibis_transport`, `evaluate_g28_subzero_esr_and_altitude`, `evaluate_g29_wireless_tx_emi_and_hotplug_esd`, `evaluate_g30_longform_endurance_and_nvram`, `evaluate_g31_pl_cantilever_and_lws_support`, `evaluate_g32_dummy_battery_overvoltage_firewall`, `evaluate_g33_saltspray_alkali_dust_and_haze`, `evaluate_g34_followfocus_hardstop_and_gimbal_cog`, `evaluate_g35_hdmi_aoc_5v_and_port_shear`, `evaluate_g36_cfexpress_vpg_thermal_and_door_flush`, `evaluate_g37_usbpd_trigger_and_uvc_thermal`, `evaluate_g38_multiterminal_ltc_uart_and_ptp`, `evaluate_g39_monsoon_rain_and_mishoe`, `evaluate_g40_xlr_h1_quarter20_and_cage_twist`, `evaluate_g41_vp_strobe_and_genlock`, `evaluate_g42_vehiclerig_ibis_and_tether`, `evaluate_g43_jiritsu_service`, `evaluate_g44_cnflasha_dualboot`, `evaluate_g45_service_0336_canary`, `evaluate_g46_mpr_ibis_p18_guard`, `evaluate_g47_pnflasha_mtdro_vault`, `evaluate_g48_rfnvs_fan_power_guard`, `evaluate_g49_uart1v8_isp`, `evaluate_g50_imx510_sensor_cal`, `evaluate_g51_cfexpress_ufu`, `evaluate_g52_5tier_el3_guard`, `evaluate_g53_cxd90058_sabin`, `evaluate_g54_factory_seal`, `evaluate_g55_c2pa_cert`, `evaluate_g56_tc_gyro_meta`, `evaluate_g57_dualmedia_vault`, `evaluate_g58_bench_interlock`, `evaluate_g59_ssboot_wbi2_guard`, `evaluate_g60_slot1_ufu_c2pa_guard`, `evaluate_g61_emount_breathing_guard`, `evaluate_g62_hdmi_raw_guard`, `evaluate_g63_fx3a_branch_firewall`, `evaluate_g64_xlrh1_mishoe_guard`, `evaluate_g65_nouvc_dcc1_pd_guard`, `evaluate_g66_lut_path_cineei_bt_guard`, `evaluate_g67_usblan_rtmp_guard`, `evaluate_g68_clipflag_anamorphic_guard`, `evaluate_g69_fan_pwm_thermal_guard`, `evaluate_g70_lut_split_shutter_angle_guard`, `evaluate_g71_big6_noend_camset_slot1_guard`, `evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard`, `evaluate_g73_desqueeze_focusmap_guard`, `evaluate_g74_simult_autoswitch_shocklesswb_guard`, `evaluate_g75_hdmi_log1080_hdmionly_guard`, `evaluate_g76_proxy_focusmag_brightmon_guard`, `evaluate_g77_filesettings_shotmark_guard`, `evaluate_g78_tcregen_reclamp_guard`, `evaluate_g79_pixelmap_reboot_cnflasha_guard`, `evaluate_g80_ntscpal_gammaassist_displaylut_guard`, `evaluate_g81_steadyshot_ciz_guard`, `evaluate_g82_powersave_autotemp_guard`, `evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard`, `evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard`, `evaluate_g85_silent_autopixelmap_no_pwrshutter_guard`, `evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard`, `evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard`, `evaluate_g88_monitor_flip_af_sens_and_interval_guard`, `evaluate_g89_emphasized_rec_and_grid_hdmi_guard`, `evaluate_g90_touch_op_reset_and_sunny_weather_guard`, `evaluate_g91_shoe_audio_and_wind_noise_guard`, `evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard`, `evaluate_g93_framing_and_antiflicker_guard`, `evaluate_g94_usb_power_and_lun_persistence_guard`, `verify_c2pa_and_factory_calibration_immutability`, `verify_stage_b_p12_wf12_and_wbi2_lock`, `classify_brick_state`, `evaluate_runtime_antibrick_guards`, `validate_rp2040_multiport_harness`, `audit_fastboot_command_sequence`, `audit_serial_boot_telemetry`, `audit_round10_summary_telemetry`, `StreamingSerialFaultDetectorV2`, `verify_watchdog_budget`, `verify_multiport_ltc_vs_uart_boot`, `verify_mishoe_digital_audio_and_p11_coexistence`, `audit_crsdk_ptp2_session`, `audit_spacc_block_layer`, `evaluate_phase38_safety_guards`, `audit_donor_thermal_fan_power_contracts`, `verify_fan_thermal_envelope`, `verify_battery_and_usbpd_firewall`, `evaluate_thermal_pwm_and_power_guard`, `compute_exfat_boot_checksum`, `parse_exfat_vbr`, `verify_exfat_boot_region`, `inspect_sony_media_tree`, `verify_dual_slot_media_firewall`, `parse_p1_fat12_fat16_vbr`, `verify_p1_vs_exfat_filesystem_separation`, `evaluate_exfat_media_integrity_guard`, `audit_usblan_ptpip_donor_contracts`, `verify_usblan_wired_control_and_airplane_coexistence`, `classify_usblan_ptpip_or_mc_operation`, `evaluate_ptpip_15740_packet`, `audit_usblan_ptpip_and_mc_firewall`, `audit_rig_20gate_donor_contracts`, `verify_rig_power_sequence`, `verify_rig_dtap_hdmi_groundloop_firewall`, `verify_emount_hot_detach_rail_and_ibis_park`, `inspect_sony_rsv_salvage_structure`, `verify_power_failover_ups_and_rsv_salvage`, `audit_phase77_donor_contracts`, `verify_xlr_h1_channel`, `verify_xlr_h1_phantom_48v_firewall`, `verify_gimbal_focus_torque_and_laser_shutter_guard`, `audit_phase84_donor_contracts`, `compute_magnus_tetens_dew_point_c`, `verify_dewpoint_tec_condensation_firewall`, `verify_pmic_5v_accessory_and_usbc_strain_guard`, `audit_phase92_donor_contracts`, `verify_sigma_fan_intake_exhaust_firewall`, `verify_tripod_screw_torque_and_housing_vacuum_guard`, `audit_phase97_donor_contracts`, `compute_arrhenius_npfz100_esr_ohm`, `compute_isa_atmosphere`, `predict_npfz100_terminal_voltage_v`, `verify_sensor_curtain_and_ibis_transport_guard`, `verify_subzero_esr_and_altitude_firewall`, `audit_phase100_donor_contracts`, `compute_nearfield_efield_v_per_m`, `estimate_recording_footprint_gib`, `compute_emmc_nvram_wear_cycles`, `verify_wireless_tx_emi_and_hotplug_esd_guard`, `verify_longform_exfat_smart_and_nvram_guard`, `audit_phase104_donor_contracts`, `compute_cantilever_bending_moment_nm`, `compute_pmic_overvoltage_stress_ratio`, `verify_pl_cantilever_and_emount_flange_guard`, `verify_dummy_battery_overvoltage_firewall`, `audit_phase108_donor_contracts`, `compute_haze_fin_fouling_dose_mg_min_m3`, `compute_estimated_ingested_aerosol_ug`, `compute_fiz_gear_tangential_force_n`, `compute_single_rod_deflection_mm`, `compute_gimbal_cog_torque_imbalance_nm`, `verify_saltspray_alkali_dust_and_haze_firewall`, `verify_followfocus_hardstop_and_gimbal_cog_guard`, `audit_phase115_donor_contracts`, `compute_hdmi_pin18_power_mw`, `compute_hdmi_type_a_cantilever_moment_nm`, `compute_required_sustained_write_mb_s`, `verify_hdmi_aoc_5v_and_port_shear_firewall`, `verify_cfexpress_vpg_thermal_and_door_guard`, `audit_phase120_donor_contracts`, `compute_uart_pad_overdrive_ratio`, `compute_usbpd_contract_watts`, `estimate_uvc_4k30p_thermal_rise_c`, `verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall`, `verify_multiterminal_ltc_uart_and_ptp_guard`, `audit_phase125_donor_contracts`, `compute_mishoe_galvanic_leakage_current_ma`, `estimate_mishoe_pin_electrolysis_power_mw`, `compute_xlr_h1_whip_moment_nm`, `estimate_emount_ffd_tilt_um`, `verify_monsoon_rain_mishoe_firewall`, `verify_xlr_h1_quarter20_and_cage_twist_guard`, `audit_phase131_donor_contracts`, `estimate_imx510_microlens_flash_temp_rise_c`, `compute_led_wall_ecs_beat_ratio`, `estimate_ibis_voice_coil_excursion_mm`, `compute_tether_static_safety_factor`, `verify_vp_strobe_uvarc_and_genlock_firewall`, `verify_vehiclerig_vibration_ibis_and_tether_guard`, `audit_phase142_donor_contracts`, `compute_p6_quota_utilization_pct`, `validate_elf_64k_alignment_and_hash`, `classify_spacc_block_device`, `validate_tier0_cold_backup_receipt`, `default_verified_tier0_sha256_receipts`, `verify_jiritsu_service_session_and_p6_guard`, `verify_cnflasha_spacc_sd_escape_and_p1_p3_guard`, `audit_phase148_donor_contracts`, `validate_op_ff_ram_canary`, `validate_fx3s0ok_packet_header`, `validate_ibis_coil_park_state`, `compute_dmm_pool_utilization_pct`, `verify_service0336_canary_64k_unlink_and_msc_return`, `verify_stageb_p18_ibis_park_and_dmmcfg_guard`, `audit_phase153_donor_contracts`, `validate_dual_layer_cipher_pairing`, `validate_camera_cid_binding`, `validate_mtd_readonly_guard`, `compute_cpapp_fan_override_pwm_pct`, `evaluate_npfz100_6100mv_encwfistop`, `verify_pnflasha_cnflasha_cid_and_mtdro_guard`, `verify_rfnvs_msc_fan_override_and_power_guard`, `audit_phase158_donor_contracts`, `validate_uart_1v8_passive_rx`, `validate_emmc_isp_1v8_passive_read`, `validate_sensor_calibration_nvs_lock`, `validate_imx510_dual_base_iso_gain`, `validate_cube_3dlut`, `build_synthetic_identity_cube_text`, `verify_uart1v8_vmc_bncm1_and_emmc_isp_guard`, `verify_imx510_sensor_cal_and_mlut_guard`, `audit_phase161_donor_contracts`, `compute_required_media_write_mb_s`, `validate_dual_slot_media_bitrate`, `validate_card_door_gpio_flush`, `validate_user_clip_dirs_untouched`, `validate_bodydata_ufu_and_clean_uninstall`, `validate_5tier_recovery_ladder`, `validate_fx3_model_id_bodydata_lock`, `validate_cxd90057_el3_readonly_guard`, `verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard`, `verify_5tier_recovery_model_id_and_el3_ro_guard`, `audit_phase165_donor_contracts`, `default_verified_16_surface_seal_hashes`, `find_h0_h3_surface_mismatches`, `validate_cxd90058_and_sabin_immutability`, `validate_mira_cetus_intersoc_link`, `validate_sdi_raw_mew_mask`, `validate_memcfg_xavc_encoder_pool`, `validate_16_surface_h0_h3_seal`, `validate_zero_bench_residuals`, `validate_otp_rpmb_and_updater_flags`, `verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard`, `verify_post_bench_factory_seal_and_official_readiness_guard`, `audit_phase170_donor_contracts`, `default_verified_rq_lic_h0_to_h3_hashes`, `build_synthetic_nrtm_gyro_xml`, `validate_p12_cert_ms_rdonly_lock`, `validate_rq_lic_h0_to_h3_preservation`, `validate_c2pa_cross_model_signing_firewall`, `validate_vmc_bncm1_ltc_and_uart_mux`, `validate_fx6_tc_out_bnc_mask`, `validate_imx510_gyro_nrtm_integrity`, `verify_c2pa_rq_lic_and_cross_model_signing_guard`, `verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard`, `audit_phase173_donor_contracts`, `gf256_mul`, `gf256_inv`, `gf256_div`, `encode_gf256_pq_parity`, `recover_gf256_pq_chunks`, `build_synthetic_16_surface_chunks`, `default_verified_16_surface_hashes`, `validate_dual_media_device_id_separation`, `validate_dual_media_16_surface_sha256_parity`, `validate_gf256_bitrot_scrub_guard`, `verify_dual_media_vault_and_gf256_scrub_guard`, `verify_two_step_bench_interlock_guard`, `audit_phase177_donor_contracts`, `build_synthetic_wbi2_sector0`, `parse_firmware_version_tuple`, `validate_wbi2_tier0_receipt`, `validate_wbi2_stageb_ro_protection`, `validate_ssboot_resume_bypass_guard`, `validate_wbi2_clean_uninstall_h0_h3`, `validate_fx3_body_firmware_floor`, `validate_slot1_root_and_duplicate_guard`, `validate_c2pa_100_license_and_p12_lock`, `validate_v700_wireless_security_floor`, `verify_ssboot_wbi2_prsvimg_and_liro_guard`, `verify_fx3_702_ufu_floor_and_slot1_c2pa_guard`, `audit_phase181_donor_contracts`, `is_sony_first_party_breathing_lens`, `parse_semver_tuple`, `validate_emount_info7_8_3d_packets`, `validate_breathing_02cf0232_lens_filter`, `validate_focus_map_readonly_telemetry`, `validate_p18_lensfile_ro_and_cinealta_block`, `validate_hdmi_4264x2408_16bit_raw_spec`, `validate_braw_video_assist_12g_compat`, `validate_atomos_ninja_prores_raw_compat`, `validate_fx6_12gsdi_mmio_mask`, `verify_emount_info3d_and_breathing_02cf0232_guard`, `verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard`, `audit_phase187_donor_contracts`, `validate_fx3_vs_fx3a_body_hardware_signature`, `validate_fx3_lcd_nfc_ir_hardware_parity`, `validate_bodydata_fx3_vs_fx3a_branch`, `validate_camset_branch_isolation`, `validate_xlrh1_mishoe_digital_audio_routing`, `validate_body_35mm_jack_override_and_sq_mute`, `validate_xlrh1_phantom_48v_stage_handoff`, `validate_xlrh1_no_fake_usb_firmware_payload`, `verify_fx3_vs_fx3a_branch_firewall`, `verify_xlrh1_mishoe_4ch_vs_35mm_override_guard`, `audit_phase191_donor_contracts`, `validate_fx3_nouvc_usb_gadget_firewall`, `validate_usbpd_body_vs_dcc1_power_supply`, `validate_user_cube_lut_and_media_path_asymmetry`, `validate_cine_ei_base_iso_bounds`, `validate_rmt_p1bt_bt_ir_mutual_exclusion`, `verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard`, `verify_dualmedia_lut_path_cineei_and_bt_guard`, `audit_phase196_donor_contracts`, `validate_usblan_poweron_autoconnect`, `validate_network_streaming_rtmp_srt_and_tls`, `validate_creators_cloud_clip_flag_hygiene`, `validate_anamorphic_desqueeze_and_hdmi_raw_lock`, `validate_bright_monitoring_and_focus_magnifier_cxd90057`, `verify_usblan_autoconnect_and_rtmp_srt_guard`, `verify_clipflag_anamorphic_and_bright_magnifier_guard`, `audit_phase199_donor_contracts`, `compute_fx3_702_fan_pwm_duty_pct`, `classify_user_lut_slot_binary_format`, `validate_fx3_4mode_fan_enum_and_off_in_rec_pwm`, `validate_prebackup_fan_and_auto_power_off_temp`, `validate_lut_601_vs_702_p2_setting_split_firewall`, `validate_independent_shutter_speed_angle_bounds`, `verify_fx3_4mode_fan_pwm_and_prebackup_guard`, `verify_lut_601_702_split_and_shutter_angle_guard`, `audit_phase201_donor_contracts`, `resolve_fx3_camset_slot1_directory`, `compute_vmcbncm1_ext_lk_state`, `validate_fx3_big6_home_zero_end_actuator`, `validate_slot1_camset_dualmedia_and_crossmodel_firewall`, `verify_fx3_big6_zero_end_and_slot1_camset_guard`, `validate_vmcbncm1_body_multi_usb_tcin_and_ext_lk`, `validate_digital_hdmi_type_a_only_tcout`, `verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard`, `audit_phase206_donor_contracts`, `verify_fx3_desqueeze_4locks_and_external_focusmap_guard`, `verify_simult_autoswitch_parity_and_shockless_wb_guard`, `audit_phase210_donor_contracts`, `resolve_effective_fx3_hdmi_output`, `verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard`, `compute_fx3_proxy_cutoff_reasons`, `verify_proxy_coupled_vault_and_focusmag_brightmon_guard`, `audit_phase214_donor_contracts`, `validate_fx3_title_name`, `resolve_effective_fx3_file_name_format`, `evaluate_shotmark_jump_and_transfer_match`, `verify_file_settings_sdhc_37char_and_shotmark_guard`, `resolve_tc_regenerate_slot_and_extlk`, `resolve_fx3_rec_lamp_coupled_tally`, `verify_tc_regenerate_extlk_and_reclamp_tally_guard`, `audit_phase219_donor_contracts`, `resolve_fx3_pixel_mapping_lifecycle`, `verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard`, `resolve_fx3_ntscpal_state`, `resolve_fx3_gamma_assist_and_display_lut_split`, `verify_ntscpal_persistence_and_gamma_assist_displaylut_guard`, `audit_phase224_donor_contracts`, `resolve_fx3_steadyshot_movie_state`, `resolve_fx3_zoom_and_4locks`, `verify_steadyshot_active_cutoff_and_ciz_4lock_guard`, `resolve_fx3_power_save_9cond_state`, `resolve_fx3_auto_power_off_temp_and_fan`, `verify_powersave_9cond_and_autotemp_tripod_guard`, `audit_phase228_donor_contracts`, `resolve_fx3_mode_settings_and_sq_6locks`, `resolve_fx3_zebra_peaking_hdmi_cleanfeed`, `verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard`, `resolve_fx3_zebra_reset_survival`, `resolve_fx3_slot1_format_and_chord_vault_lock`, `verify_zebra_reset_survival_and_fullformat_chord_vault_guard`, `audit_phase230_donor_contracts`, `resolve_fx3_silent_mode_and_target_functions`, `verify_silent_mode_autopixelmap_and_no_pwrshutter_guard`, `resolve_fx3_marker_display_hdmi_and_reset`, `resolve_fx3_flexible_exp_reset_split`, `verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard`, `audit_phase235_donor_contracts`, `parse_fx3_duration_seconds`, `resolve_fx3_recover_imagedb_battery_and_vault_state`, `verify_recover_imagedb_depleted_battery_and_tier0_vault_guard`, `resolve_fx3_monitor_flip_reset_and_playback`, `resolve_fx3_af_transition_and_subj_shift_sensitivity`, `resolve_fx3_interval_shoot_func_boundary`, `verify_monitor_flip_playback_af_sens_and_interval_guard`, `audit_phase237_donor_contracts`, `resolve_fx3_emphasized_rec_and_grid_hdmi_routing`, `verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard`, `resolve_fx3_touch_op_4item_reset_and_bench_lock`, `resolve_fx3_monitor_brightness_reset_and_sunny_guard`, `verify_touch_op_reset_and_sunny_weather_bench_guard`, `audit_phase241_donor_contracts`, `resolve_fx3_shoe_audio_and_wind_noise_state`, `verify_shoe_audio_4ch_and_wind_noise_guard`, `classify_saveload_excluded_items`, `resolve_fx3_saveload_c3_and_slot1_vault_state`, `verify_saveload_camset_c3_exclusions_and_slot1_vault_guard`, `audit_phase246_donor_contracts`, `resolve_fx3_framing_and_antiflicker_state`, `verify_framing_asymmetric_and_antiflicker_no_varshutter_guard`, `resolve_fx3_usb_power_interlock_and_lun_persistence_state`, `verify_usb_power_npfz100_typec_and_lun_persistence_guard`.

### 3.4 Running Tests in Normal & Clean-Room Modes
```bash
# Normal mode (with fx3_recovery sibling integration, 360 tests in <0.9s)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v

# Clean-Room mode (decoupled synthetic-only mode, 360 tests in <0.9s)
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

---

## 12. Phase 84 Sub-Dewpoint Peltier TEC Condensation Firewall, PMIC `5V` Accessory Current-Budget / USB-C Strain Guard & 24-Gate Master Preflight (`dewpoint_tec_usbc_and_24gate_guard.py`)

`dewpoint_tec_usbc_and_24gate_guard.py` (`fx3-dewpoint-tec-usbc-24gate-preflight-v1`) composes `phantom48v_gimbal_and_22gate_guard.py` (`G01..G22`, leaving `preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`, and `phantom48v_gimbal_and_22gate_guard.py` untouched) with two new psychrometric condensation and PMIC/USB-C electrical/mechanical gates **`G23`** and **`G24`** into a deterministic **24-Gate Master Safety Preflight (`G01..G24`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Magnus-Tetens Dew-Point Condensation & External Peltier (`TEC`) Cooler Short-Circuit Firewall (`compute_magnus_tetens_dew_point_c`, `verify_dewpoint_tec_condensation_firewall`, Gate `G23`)**:
   - Computes exact psychrometric dew point $T_{dp}(T_{amb}, RH\%)$ via the Magnus-Tetens formula ($a=17.625, b=243.04^\circ\text{C}$).
   - Hard-blocks unregulated or sub-dewpoint external Peltier (`TEC`) semiconductor backplate coolers (`BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD`) whenever `tec_cold_plate_c < dew_point_c + 2.0` (e.g., `30°C / 75% RH` $\rightarrow T_{dp} = 25.08^\circ\text{C}$, blocking `10°C` Peltier coolers that condense liquid water onto the FX3 magnesium rear chassis and LCD hinge flex).
   - Hard-blocks rapid Cold-to-Warm unbagged thermal shock (`BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK`) when moving a `-5°C` outdoor camera directly into a `+26°C / 65% RH` indoor room without a sealed acclimation bag until `body_temp_c >= dew_point_c + 2.0`.
   - Proves FX3's internal `libfan.so` centrifugal Sigma-shaped blower (`cooling_method == "internal_centrifugal_air"`) never drops chassis temperature below ambient dew point ($T_{chassis} \ge T_{amb} > T_{dp} \rightarrow 0\%$ condensation risk).
2. **PMIC `5V` Accessory Current-Budget, Non-Compliant USB-C PD Cable Droop & Cage Strain-Relief Guard (`verify_pmic_5v_accessory_and_usbc_strain_guard`, Gate `G24`)**:
   - Models simultaneous `5V` rail draw across `24-pin MI-Shoe` (`XLR-H1` digital ADC + dual `+48V` phantom boost under `10 mA` dual condenser load), `HDMI Type-A Pin-18 +5V` (`<= 55 mA`), `USB-C VBUS` host-mode (`RTL8153`/`AX88179` Gigabit Ethernet or USB-C SSD), and `Multi-Port` accessory logic draw.
   - Fails closed (`BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET`) when cumulative `5V` accessory draw exceeds `900 mA` without an external powered USB-C PD hub.
   - Detects high-resistance / un-E-marked `>2m` USB-C cables (`cable_ir_drop_v > 0.65V` at `3.0A` causing `9V` PD rail oscillation $\rightarrow$ `BLOCKED_USBC_PD_CABLE_IR_DROOP`) and unclamped heavy USB-C/HDMI cables during handheld/gimbal rigs (`require_cage_cable_clamp == True` $\rightarrow$ `BLOCKED_UNCLAMPED_USBC_HDMI_STRAIN_HAZARD`).
3. **24-Gate Master Safety Preflight (`evaluate_24gate_preflight`) & `verify-24-gates` CLI**:
   - **Offline default mode**: `21/24` gates pass (`G01..G09`, `G13..G24` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `24/24` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False` and `persistent_emmc_writes_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-24-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 13. Phase 92 Sigma Cooling Fan Intake/Exhaust Occlusion & Rain-Cover Backpressure Firewall, 1/4-20 Tripod Screw Depth / Cage Torque / Underwater Housing Vacuum Guard & 26-Gate Master Preflight (`intake_occlusion_tripod_and_26gate_guard.py`)

`intake_occlusion_tripod_and_26gate_guard.py` (`fx3-intake-occlusion-tripod-26gate-preflight-v1`) composes `dewpoint_tec_usbc_and_24gate_guard.py` (`G01..G24`, leaving all prior gate modules untouched) with two new mechanical airflow/thermal-recirculation and mounting/housing gates **`G25`** and **`G26`** into a deterministic **26-Gate Master Safety Preflight (`G01..G26`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Sigma Centrifugal Fan Intake/Exhaust Occlusion, Tachometer Stall & Sealed Rain-Cover / Blimp Thermal Recirculation Firewall (`verify_sigma_fan_intake_exhaust_firewall`, Gate `G25`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libfan.so` and `BK4\0` (`0x02380007..0x02380009` over-temperature thresholds `82°C` vs `76°C`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback.
   - Fails closed on:
     - `BLOCKED_FAN_TACHOMETER_ROTOR_STALL` when `pwm_duty_pct >= 25.0` and `measured_rpm < min_expected_rpm` (foreign debris / jammed impeller),
     - `BLOCKED_DUCT_OCCLUSION_BACKPRESSURE` when `intake_clearance_mm < 5.0` or `exhaust_clearance_mm < 5.0` (flush V-mount battery plate / cheeseplate blocking FX3 side vents),
     - `BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD` when `fan_mode == 'Off_in_Rec'` and `workload in ('4K_120p', '4K_60p_RAW_HDMI', 'XAVC_S_I_4K60_DUALSLOT')` and `clip_duration_min > 8.0`,
     - `BLOCKED_SEALED_BLIMP_RECIRCULATION` when `enclosure_sealed_blimp_or_raincover == True` and `internal_enclosure_temp_c > 42.0`.
2. **1/4-20 Tripod Screw Depth Bottom-Out (`5.5 mm` ISO 1222 Magnesium Pocket Limit), Cage Over-Torque & Underwater Housing Vacuum Leak Guard (`verify_tripod_screw_torque_and_housing_vacuum_guard`, Gate `G26`)**:
   - Fails closed on:
     - `BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE` when `effective_screw_protrusion_mm > 5.5` (prevents warping the bottom magnesium plate into the internal PCB / IBIS flex assembly),
     - `BLOCKED_MOUNTING_OVER_TORQUE_HAZARD` when `applied_torque_nm > 3.5` or `single_screw_no_anti_twist_pin_heavy_lens == True`,
     - `BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE` when `underwater_housing_mode == True` and (`vacuum_pressure_drop_mbar_per_10min > 1.5` or `moisture_sensor_triggered == True` or `vacuum_check_elapsed_min < 10.0`), asserting immediate power-off abort before water reaches eMMC/mainboard.
3. **26-Gate Master Safety Preflight (`evaluate_26gate_preflight`) & `verify-26-gates` CLI**:
   - **Offline default mode**: `23/26` gates pass (`G01..G09`, `G13..G26` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `26/26` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False` and `persistent_emmc_writes_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-26-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 14. Phase 97 IMX510 Sensor Laser/Solar Burnout, Anti-Dust Curtain-at-Power-Off & IBIS Transport Lock Guard (`Gate G27`), Sub-Zero NP-FZ100 ESR Sag & High-Altitude Convective Cooling Firewall (`Gate G28`) & 28-Gate Master Preflight (`sensor_curtain_subzero_and_28gate_guard.py`)

`sensor_curtain_subzero_and_28gate_guard.py` (`fx3-sensor-curtain-subzero-28gate-preflight-v1`) composes `intake_occlusion_tripod_and_26gate_guard.py` (`G01..G26`, leaving all prior gate modules untouched) with two new optical/mechanical sensor-stage and extreme-environment power/cooling gates **`G27`** and **`G28`** into a deterministic **28-Gate Master Safety Preflight (`G01..G28`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **IMX510 Sensor Laser/Solar Burnout, 'Shutter When Power Off' Fragile Blade Puncture & Unpowered IBIS Transport Lock Guard (`verify_sensor_curtain_and_ibis_transport_guard`, Gate `G27`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libfan.so`, `libBusPower.so`, `libUsbBusPower.so`, `BK4\0` (`0x02380007..0x02380009`), and optionally (`include_large_binaries=True`) `appFw.so` (`EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER`, `VAL_system_mode_option_SYSTEM_MODE_OPTION_CLEANING`, `OFF_BY_BATT_END`, `ND_FILTER_MANUAL_SET_0_3`) & `cpapp-b.bin` (`SET_S1_STEADY_SHOT_MODE`, `BATT_AUTH_S`, `FAN_EQ_ID`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback.
   - Fails closed on:
     - `BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD`: concert/show laser or automotive LiDAR environment without a laser-rated optical filter OR uncapped fast lens pointed at direct sun (FX3 lacks FX6's internal e-VND glass protecting the sensor cavity),
     - `BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE`: `shutter_when_power_off == True` (`0.04 mm` delicate shutter blades closed) combined with `manual_swab_or_rocket_blower_active == True` or `outdoor_direct_sun_lens_off == True`,
     - `BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION`: `vehicle_hard_mount_vibration_grms > 1.8` when `power_off_ibis_parking_verified == False`.
2. **Sub-Zero (-20C..0C) NP-FZ100 Li-Ion ESR Voltage-Sag Brownout & High-Altitude (>3,000m..5,500m) Air-Density Convective Cooling Derating Firewall (`verify_subzero_esr_and_altitude_firewall`, Gate `G28`)**:
   - Models Arrhenius Li-Ion internal DC resistance $R_{int}(T) = R_{25} \exp\!\left(\frac{E_a}{R}\left(\frac{1}{T_K} - \frac{1}{298.15}\right)\right)$ (`3x–6x+` sub-zero ESR spike) and constant-power PMIC terminal voltage $V_{term} = V_{oc} - I \cdot R_{int}(T)$ plus ISA standard atmosphere barometric air-density $\rho(h)$ convective mass-flow derating above `3,000 m` ($P_{atm} < 70\text{ kPa}$).
   - Fails closed on:
     - `BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK`: `battery_cell_temp_c < 0.0` and predicted `v_term_min_v < 6.25` (`6.0 V` PMIC UVLO + margin, e.g. `-20C` at `45%` SoC under `8.5 W` peak load) without insulated USB-PD / heated V-Mount backup,
     - `BLOCKED_LIION_SUBZERO_CHARGING_PLATING`: `usb_pd_charging_enabled == True` and `battery_cell_temp_c <= 0.0` (preventing metallic lithium dendrite plating),
     - `BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING`: `altitude_m > 3000.0` and `fan_mass_flow_ratio * cooling_headroom_watts < workload_thermal_watts`.
3. **28-Gate Master Safety Preflight (`evaluate_28gate_preflight`) & `verify-28-gates` CLI**:
   - **Offline default mode**: `25/28` gates pass (`G01..G09`, `G13..G28` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `28/28` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False` and `persistent_emmc_writes_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-28-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 15. Milestone Phase 100 Cinema Wireless Video TX 5GHz/6GHz Near-Field EMI & D-Tap/HDMI Hot-Plug ESD Guard (`Gate G29`), Long-Form (>6h) Continuous Recording exFAT Clip-Spanning & CFexpress SMART Wear / Zero-NVRAM-Churn Endurance Guard (`Gate G30`) & 30-Gate Master Preflight (`wireless_tx_emi_endurance_and_30gate_guard.py`)

`wireless_tx_emi_endurance_and_30gate_guard.py` (`fx3-wireless-tx-emi-endurance-30gate-preflight-v1`) composes `sensor_curtain_subzero_and_28gate_guard.py` (`G01..G28`, leaving all prior gate modules untouched) with two new RF-EMI/ESD and long-form recording endurance gates **`G29`** and **`G30`** into a deterministic **30-Gate Master Safety Preflight (`G01..G30`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Cinema Wireless Video TX 5GHz/6GHz Near-Field EMI, D-Tap/HDMI Hot-Plug ESD & Multi-Port LTC Impedance Guard (`verify_wireless_tx_emi_and_hotplug_esd_guard`, Gate `G29`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libInfraMediaMount.so` (`GetMediaLifeInfo`, `IMM_GetMediaLifeInfo`, `mcmn_drv_updatelifeinfo`), `libInfraMediaCommon.so` (`mcmn_drv_nvme_getlifeinfofromsmartinfo`, `mcmn_drv_nvme_getlogpage_smartinformation`, `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_dmm_hotplug`), `libbackup.so` (`Backup_read`, `Backup_write`, `Backup_sync_all`, `Backup_protect`), `libBackupManager.so` (`writeBackup`, `readBackupDecryption`), `libInfraFsys.so` (`flash_span`, `fsysDepLog_DriveIOQueueIOVecCountLimitOverflow`), and FX6 `libHotplug.so` (`MakeObjEject`, `MakeObjInsert`, `guardAcvOn`), plus optional (`include_large_binaries=True`) `appFw.so` & `cpapp-b.bin` tokens (`DETECT_HPD`, `OBSERVE_HPD`, `BACKUP_WRITE`, `EXTERNALTC_LOCK`, `LTC`, `EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT`, `EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback.
   - Models near-field RF electric field $E = \frac{\sqrt{30 P_W G}}{r_m}$ (`compute_nearfield_efield_v_per_m`) for high-power `500 mW – 1000 mW` 5 GHz / 6 GHz / DFS cinema wireless video transmitters (Teradek / Hollyland / DJI SDR) mounted near FX3 MI-Shoe / HDMI ports.
   - Fails closed on:
     - `BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE`: `wireless_tx_power_mw > 250.0` and `antenna_to_mishoe_or_hdmi_mm < 35.0` and `shielded_coax_hdmi_cable == False`,
     - `BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE`: (`dtap_powered_wireless_tx == True` and `power_on_sequence != 'GND_POWER_FIRST_SIGNAL_LAST'`) or `hot_plug_while_dtap_live_unisolated == True` (protecting `CXD90057` HDMI ESD diodes from ungrounded D-Tap floating-return surges),
     - `BLOCKED_TIMECODE_BNC_OVER_VOLTAGE`: `multiport_tc_input_vpp > 5.0` (protecting FX3 Multi-Port `3.3 V`-tolerant TC pin from studio `+12 V` RS-422 / high-level LTC feeds).
2. **Long-Form (`>6h..24h`) Continuous Recording exFAT Seamless Spanning, CFexpress SMART Spare-Block Endurance & Zero-eMMC-NVRAM-Churn Guard (`verify_longform_exfat_smart_and_nvram_guard`, Gate `G30`)**:
   - Fails closed on:
     - `BLOCKED_FAT32_4GIB_SPANNING_TRAP`: `planned_continuous_min > 10.0` and `filesystem != 'exFAT'`,
     - `BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION`: `smart_percentage_used > 90` or `spare_blocks_pct < 10.0` or `media_nand_temp_c > 78.0`,
     - `BLOCKED_PERIODIC_EMMC_NVRAM_CHURN`: `runtime_nvram_flush_hz > 0.0` (or `ram_shadow_bkid_enabled == False`), enforcing 100% RAM-shadow `BKID` state so FX3's internal eMMC `p13..p15` endures zero runtime wear cycles.
3. **30-Gate Master Safety Preflight (`evaluate_30gate_preflight`) & `verify-30-gates` CLI**:
   - **Offline default mode**: `27/30` gates pass (`G01..G09`, `G13..G30` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `30/30` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-30-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 16. Phase 104 Heavy Cinema PL-to-E Cantilever Bending-Moment & 15mm LWS Lens-Support Guard (`Gate G31`), Unregulated 14.8V/26V V-Mount -> NP-FZ100 Dummy-Battery Over-Voltage Blowout Firewall (`Gate G32`) & 32-Gate Master Preflight (`pl_cantilever_dummybatt_and_32gate_guard.py`)

`pl_cantilever_dummybatt_and_32gate_guard.py` (`fx3-pl-cantilever-dummybatt-32gate-preflight-v1`) composes `wireless_tx_emi_endurance_and_30gate_guard.py` (`G01..G30`, leaving all prior gate modules untouched) with two new physical-rig cantilever & battery-bay power-rail safety gates **`G31`** and **`G32`** into a deterministic **32-Gate Master Safety Preflight (`G01..G32`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Heavy Cinema PL-to-E Mount Adapter, Clamp-On Matte-Box & Cantilever Bending-Moment Guard (`verify_pl_cantilever_and_emount_flange_guard`, Gate `G31`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libInfraLensCommunicator.so` (`GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup`), `libBusPower.so`, and `libUsbBusPower.so` strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` for `BATT_AUTH_Snd`, `C_LENS_XDETECT_BODY_INT_NO`, `asrid_cau_battery_authentication_error_normal_english_`, `No11_BatteryLevelNonInfoLitium`, `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`) and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback.
   - Computes exact static ($M_{static} = m \cdot g \cdot L_{cg}$) and `2.5G` dynamic shock ($M_{peak} = M_{static} \cdot \text{shock}_g$) cantilever bending moments on FX3's 6-screw E-Mount flange (`18.00 mm` flange focal distance, `+/-0.01 mm` back-focus tolerance), failing closed on:
     - `BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP`: `lens_plus_mattebox_kg > 1.2` or `static_moment_nm > 1.8` without `lws_15mm_y_support_engaged == True`,
     - `BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT`: `pl_to_e_adapter_used == True` and `adapter_foot_bolted_to_cage == False` and `lens_plus_mattebox_kg > 0.9`,
     - `BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL`: `clamp_on_mattebox == True` and `lens_front_rotates_or_telescopes == True` (requiring a swing-away rod-mounted matte box).
2. **Unregulated 14.8V / 26V V-Mount -> `NP-FZ100` Dummy-Battery Over-Voltage Blowout Firewall (`verify_dummy_battery_overvoltage_firewall`, Gate `G32`)**:
   - Guards FX3's `7.2V` nominal / `8.40V` max battery bay against the #1 real-world `CXD90057` PMIC mainboard blowout (unregulated `14.8V..16.8V` or `26V` V-Mount dummy couplers), recommending Sony Cinema SOP regulated `9V/3A` USB-C PD + genuine internal `NP-FZ100` UPS, failing closed on:
     - `BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT`: `dummy_battery_installed == True` and (`measured_open_circuit_v > 8.45` or `buck_regulator_ovp_crowbar_verified == False` or `v_mount_nominal_v >= 24.0`),
     - `BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP`: `dtap_source_used == True` and `reverse_polarity_diode_or_smart_dtap == False`,
     - `BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF`: `dummy_battery_installed == True` and `infolithium_thermistor_ntc_valid == False`.
3. **32-Gate Master Safety Preflight (`evaluate_32gate_preflight`) & `verify-32-gates` CLI**:
   - **Offline default mode**: `29/32` gates pass (`G01..G09`, `G13..G32` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `32/32` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-32-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 17. Phase 108 Coastal Salt-Spray / Studio Glycol-Haze Fan Ingestion Firewall (`Gate G33`), Wireless Follow-Focus Hard-Stop Lens-Barrel Torque & Gimbal Dynamic CoG Shift Guard (`Gate G34`) & 34-Gate Master Preflight (`saltspray_haze_followfocus_and_34gate_guard.py`)

`saltspray_haze_followfocus_and_34gate_guard.py` (`fx3-saltspray-haze-followfocus-34gate-preflight-v1`) composes `pl_cantilever_dummybatt_and_32gate_guard.py` (`G01..G32`, leaving all prior gate modules untouched) with two new environmental-aerosol & motorized-rigging safety gates **`G33`** and **`G34`** into a deterministic **34-Gate Master Safety Preflight (`G01..G34`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Coastal Salt-Spray / Fine Desert Silica Dust & Studio Mineral-Oil / Glycol Haze Sigma Blower Ingestion Firewall (`verify_saltspray_alkali_dust_and_haze_firewall`, Gate `G33`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libfan.so` (`fan_infra_init`, `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list`), `libInfraLensCommunicator.so` (`GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup`), and `libInfraExtCmdSvc.so` (`ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`) strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Quantifies cumulative haze exposure dose ($\text{mg}\cdot\text{min}/\text{m}^3$) and estimated Sigma blower aerosol ingestion ($\mu\text{g}$), failing closed on:
     - `BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT`: `coastal_salt_spray_env == True` and `hydrophobic_vent_membrane_or_housing == False`,
     - `BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD`: `pm10_dust_ug_m3 > 600.0` and `intake_hepa_mesh_installed == False`,
     - `BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING`: `studio_haze_density_mg_m3 > 25.0` and `continuous_fan_exposure_min > 45.0` and `post_wrap_isopropyl_duct_purge_scheduled == False`.
2. **High-Torque Wireless Follow-Focus (`Nucleus-M / Preston / Tilta` `> 2.5 N*m`) Uncalibrated Hard-Stop Gear Stripping & Telescoping-Zoom Gimbal Motor Oscillation Guard (`verify_followfocus_hardstop_and_gimbal_cog_guard`, Gate `G34`)**:
   - Computes tangential gear tooth force ($F = \tau / r$), Euler-Bernoulli 15mm single-rod cantilever deflection ($\delta = F L^3 / (3 EI)$), and gimbal zoom CoG torque imbalance ($\tau_{imb} = m \cdot g \cdot \Delta_{cog}$), failing closed on:
     - `BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE`: `wireless_fiz_motor_torque_nm > 1.2` and `hard_stops_calibrated == False` and `fly_by_wire_infinite_ring == False`,
     - `BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP`: `wireless_fiz_motor_torque_nm > 1.8` and `dual_rod_or_cage_bridge_clamp == False`,
     - `BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION`: `gimbal_mounted == True` and `zoom_cog_shift_mm > 15.0` and `gimbal_autotune_after_zoom == False` (preventing `40..90 Hz` roll/pitch PID oscillation from saturating FX3's IBIS voice coils).
3. **34-Gate Master Safety Preflight (`evaluate_34gate_preflight`) & `verify-34-gates` CLI**:
   - **Offline default mode**: `31/34` gates pass (`G01..G09`, `G13..G34` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `34/34` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-34-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 18. Phase 115 Active Optical HDMI (AOC) Pin-18 `+5V` Over-Current / Reverse Backfeed & Unclamped Type-A Port Shear Firewall (`Gate G35`), CFexpress Type-A / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal-Throttle & Door-Open Flush Guard (`Gate G36`) & 36-Gate Master Preflight (`hdmi_aoc_5v_cfexpress_and_36gate_guard.py`)

`hdmi_aoc_5v_cfexpress_and_36gate_guard.py` (`fx3-hdmi-aoc-5v-cfexpress-36gate-preflight-v1`) composes `saltspray_haze_followfocus_and_34gate_guard.py` (`G01..G34`, leaving all prior gate modules untouched) with two new external-recorder HDMI `+5V`/port-shear and dual-slot CFexpress/SDXC endurance gates **`G35`** and **`G36`** into a deterministic **36-Gate Master Safety Preflight (`G01..G36`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Active Optical HDMI (AOC) Pin-18 `+5V` Over-Current / Reverse Backfeed & Unclamped Type-A Port Shear Firewall (`verify_hdmi_aoc_5v_and_port_shear_firewall`, Gate `G35`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libInfraAdjMedia.so` (`AVBB_SCN_START_HDMI`, `AVBB_SCN_STOP_HDMI`, `DisableMediaTemperatureInfoNotification`, `GetTemp`), `libInfraMediaConfig.so` (`ADJ_SLOT_1`, `ADJ_SLOT_2`, `CTRL_TEMP`, `SLOT_SSD`), `libInfraMediaDetect.so` (`IMD_Starttemp`, `IMD_Stoptemp`, `NotifyTempEvent`, `GetTemp`), and `libInfraMediaCommon.so` (`CFexpress`, `FSYS_GTEST_VPGP4_AU_SIZE`, `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_drv_nvme_getlogpage_smartinformation`, `mcmn_dmm_hotplug`) strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Protects FX3 `SY-1129` mainboard HDMI Type-A receptacle and `+5V` load switch during external ProRes RAW / BRAW recorder rigging, failing closed on:
     - `BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR`: `hdmi_pin18_draw_ma > 55.0` and `external_hdmi_5v_power_injector == False`,
     - `BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD`: `sink_backfeed_voltage_v > 5.35` or (`camera_power_off == True` and `sink_pin18_backfeed_ma > 2.0` and `hdmi_reverse_blocking_diode_verified == False`),
     - `BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR`: (`hdmi_cable_bend_moment_nm > 1.2` or `heavy_braided_or_coiled_hdmi_cable == True`) and `cage_hdmi_cable_clamp_locked == False`.
2. **CFexpress Type-A / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal-Throttle & Door-Open Flush Guard (`verify_cfexpress_vpg_thermal_and_door_guard`, Gate `G36`)**:
   - Protects `XAVC S-I 4K 120p` (`600 Mbps`) and simultaneous dual-slot relay/backup recording against silent frame drops, NAND thermal throttling, and exFAT/FAT commit corruption, failing closed on:
     - `BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC`: `sustained_p99_write_mb_s < required_min_write_mb_s` (including dual-slot simultaneous overhead margin `1.20x` and `VPG200`/`VPG400` certification & floor validation),
     - `BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT`: `cfexpress_controller_temp_c > 82.0` or (`dual_slot_simultaneous_4k120p == True` and `ambient_temp_c > 38.0` and `sigma_fan_mode in {"OFF_IN_REC", "MINIMUM"}`),
     - `BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH`: `slot_door_open_detected == True` and `media_flush_or_fat_commit_pending == True`.
3. **36-Gate Master Safety Preflight (`evaluate_36gate_preflight`) & `verify-36-gates` CLI**:
   - **Offline default mode**: `33/36` gates pass (`G01..G09`, `G13..G36` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `36/36` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-36-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 19. Milestone Phase 120 Unnegotiated 20V USB-C PD Trigger-Cable / Dual-Source D-Tap+USB-PD Cross-Feed & UVC 1.5 Thermal Firewall (`Gate G37`), Sony 15-Pin Multi-Terminal LTC +5V Clash / 1.8V UART Over-Drive & CRSDK PTP Flash-Opcode Guard (`Gate G38`) & 38-Gate Master Preflight (`usbpd_trigger_multiterminal_and_38gate_guard.py`)

`usbpd_trigger_multiterminal_and_38gate_guard.py` (`fx3-usbpd-trigger-multiterminal-38gate-preflight-v1`) composes `hdmi_aoc_5v_cfexpress_and_36gate_guard.py` (`G01..G36`, leaving all prior gate modules untouched) with two new USB-C PD/UVC thermal and Multi-Terminal/UART/PTP hardware-protection gates **`G37`** and **`G38`** into a deterministic **38-Gate Master Safety Preflight (`G01..G38`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Unnegotiated `20V` USB-C PD Trigger-Cable, Dual-Source (`D-Tap` Dummy-Batt + `USB-PD` VBUS) Cross-Feed & Continuous `4K30p` `UVC 1.5` Thermal Saturation Firewall (`verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall`, Gate `G37`)**:
   - Inspects FX3 `v7.02` & FX6 `v6.01` `libBusPower.so` (`_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT`), `libUsbBusPower.so` (`_ZN11UsbBusPower11IsVbusReadyEv`, `_ZN11UsbBusPower22SetPowerContractStatusEi`, `_ZN11UsbBusPower15GetCurrentLimitEv`, `_ZN11UsbBusPower18SetWatchSWForceOFFEv`), `libUsbControl.so` (`_ZN12UsbIfWrapper20isMultiPortSupportedEv`, `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`, `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT`), and `libInfraPtpControl.so` (`InfraPtpControl_Init`, `PTPT_init`, `PTPT_open`, `_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv`) strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Protects FX3 `SY-1129` USB Type-C CC/VBUS PMIC front-end and `CXD90057` SoC thermal envelope, failing closed on:
     - `BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE`: `usbc_vbus_measured_v > 9.6` without valid `9V/3A` (`27W`) PD PDO contract (e.g. passive `12V/15V/20V` D-Tap-to-USB-C decoy cable forcing `14.8V..20V` onto VBUS before CC negotiation, or `cc_pin_short_to_vbus == True`),
     - `BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED`: `unregulated_dummy_battery_active == True` and `usbc_pd_power_sink_active == True` and `common_vmount_battery_shared_without_dc_isolator == True`,
     - `BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION`: `uvc_4k30p_streaming_hours >= 2.0` and `ambient_temp_c > 35.0` and `internal_np_fz100_charging_while_streaming == True` and `auto_power_off_temp_standard == True`.
2. **Sony `15-Pin Multi-Terminal` `LTC` BNC Adapter `+5V` Pin Clash, `3.3V/5V` UART Over-Drive (`1.8V` `CXD90057` Pad Limit) & Destructive `CRSDK` `PTP` Firmware-Flash Opcode Hardware Guard (`verify_multiterminal_ltc_uart_and_ptp_guard`, Gate `G38`)**:
   - Protects FX3's `15-pin Multi/Micro-USB` connector (`LTC` Timecode-In, `LANC`/remote, sense pins) and `1.8V` debug UART pads, failing closed on:
     - `BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH`: `ltc_bnc_adapter_attached == True` and (`ltc_peak_to_peak_v > 5.0` or `third_party_non_sony_id_resistor_short == True`),
     - `BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD`: `uart_probe_attached == True` and (`uart_logic_level_v > 1.95` or `uart_tx_line_physically_connected == True`), enforcing strictly `1.8V` passive RX-only monitoring,
     - `BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE`: `usb_ptp_crsdk_session_active == True` and `ptp_fw_flash_opcodes_blocked_in_filter == False`.
3. **38-Gate Master Safety Preflight (`evaluate_38gate_preflight`) & `verify-38-gates` CLI**:
   - **Offline default mode**: `35/38` gates pass (`G01..G09`, `G13..G38` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `38/38` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-38-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 20. Milestone Phase 125 Tropical Monsoon Rain / Wet MI-Shoe 24-Pin Contact Short-Circuit Firewall (`Gate G39`), FX3 Top-Plate `1/4"-20` Thread Shear / `XLR-H1` Whip-Leverage & Asymmetric Cage-Twist E-Mount `18.00 mm` Flange-Focal-Distance Guard (`Gate G40`) & 40-Gate Master Preflight (`monsoon_mishoe_cagetwist_and_40gate_guard.py`)

`monsoon_mishoe_cagetwist_and_40gate_guard.py` (`fx3-monsoon-mishoe-cagetwist-40gate-preflight-v1`) composes `usbpd_trigger_multiterminal_and_38gate_guard.py` (`G01..G38`, leaving all prior gate modules untouched) with two new environmental moisture/galvanic and mechanical rigging/flange-warpage gates **`G39`** and **`G40`** into a deterministic **40-Gate Master Safety Preflight (`G01..G40`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Tropical Monsoon Rain Ingress, Uncapped Wet 24-Pin MI-Shoe Gold-Finger Galvanic Short-Circuit & Open Port-Flap Capillary Guard (`verify_monsoon_rain_mishoe_firewall`, Gate `G39`)**:
   - Inspects FX6 `v6.01` `libInfraHotshoe.so` (`_ZN12InfraHotshoe13QueryShoeIdOnEij`, `_ZN12InfraHotshoe17SetShoeLogicPwrOnEb`, `_ZN12InfraHotshoe27SetShoeUnregOnWaitStabilityEbjj`, `INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON`), FX3 `v7.02` & FX6 `v6.01` `libInfraLensCommunicator.so` (`GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup`), FX3 `v7.02` & FX6 `v6.01` `libInfraExtCmdSvc.so` (`ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`, `SndMsgToLowerSync`), and FX3 `v7.02` & FX6 `v6.01` `libBusPower.so` (`_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`, `_ZN8BusPower27NotifyUSBPowerContractStateEi`, `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT`) strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Protects FX3's unsealed top-plate recessed 24-pin Multi-Interface (MI) Shoe (`+3.15V/+5V` logic/power, `I2S` clocks, `ID1..ID3` detect pins) and side port bays against tropical rain galvanic electrolysis and capillary ingress, failing closed on:
     - `BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT`: (`precipitation_mm_hr > 0.5` and `mi_shoe_accessory_attached == False` and `mi_shoe_weather_cap_installed == False`) or (`mi_shoe_contact_resistance_kohm < 50.0` and `mi_shoe_power_rail_enabled == True`),
     - `BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN`: `precipitation_mm_hr > 2.0` and `mi_shoe_accessory_attached == True` and `mi_shoe_silicone_perimeter_gasket_sealed == False` and `rain_cover_installed == False`,
     - `BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS`: (`precipitation_mm_hr > 0.5` or `water_spray_rig == True`) and `open_rubber_port_flaps_count > 0` and `weather_sealed_cable_gland_or_rain_slicker == False`.
2. **FX3 Top-Plate `2x M4` `XLR-H1` Handle Whip-Leverage Shear, `1/4"-20` Magnesium-Chassis Thread Strip (`> 3.5 N*m`) & Asymmetric Cage-Twist E-Mount `18.00 mm` Flange-Focal-Distance (`FFD`) Warpage Guard (`verify_xlr_h1_quarter20_and_cage_twist_guard`, Gate `G40`)**:
   - Protects FX3's internal magnesium-alloy chassis (`5x 1/4"-20` mounting bosses + `2x M4` MI-Shoe handle screws) and `18.00 mm` (`±0.015 mm`) E-Mount optical flange plane, failing closed on:
     - `BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR`: `xlr_h1_handle_installed == True` and (`total_rig_mass_suspended_from_xlr_h1_kg > 2.8` or `top_handle_monitor_moment_nm > 3.2`) and `metal_cage_nato_top_handle_reinforcement == False`,
     - `BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP`: `body_thread_fastener_torque_nm > 3.5`,
     - `BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE`: `cage_multi_point_locked == True` and `unshimmed_side_screw_gap_mm > 0.25` causing `estimated_emount_ffd_tilt_um > 12.0`.
3. **40-Gate Master Safety Preflight (`evaluate_40gate_preflight`) & `verify-40-gates` CLI**:
   - **Offline default mode**: `37/40` gates pass (`G01..G09`, `G13..G40` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `40/40` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-40-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 21. Phase 131 Virtual Production High-Energy DMX Strobe / UV-Arc `IMX510` Sensor Overload & Tri-Level Genlock -> Multi-Terminal Firewall (`Gate G41`), Vehicle / Aerial Hard-Mount Vibration (`20..200 Hz`) `IBIS` Thermal Resonance & Steel-Tether Guard (`Gate G42`) & 42-Gate Master Preflight (`vp_strobe_vehiclerig_ibis_and_42gate_guard.py`)

`vp_strobe_vehiclerig_ibis_and_42gate_guard.py` (`fx3-vp-strobe-vehiclerig-ibis-42gate-preflight-v1`) composes `monsoon_mishoe_cagetwist_and_40gate_guard.py` (`G01..G40`, leaving all prior gate modules untouched) with two new virtual-production optical/sync and vehicle/aerial vibration-isolation gates **`G41`** and **`G42`** into a deterministic **42-Gate Master Safety Preflight (`G01..G42`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and `PERSISTENT_WRITE_RELEASE = False` hard-locked:

1. **Virtual Production High-Irradiance DMX Strobe / Unfiltered UV-Arc `IMX510` Sensor Hazard, `75-Ohm` Tri-Level Genlock -> `Multi-Terminal` Pin Mismatch & LED-Wall `ECS` Aliasing Firewall (`verify_vp_strobe_uvarc_and_genlock_firewall`, Gate `G41`)**:
   - Inspects FX6 `v6.01` `libInfraMultiIF.so` (`InfraMultiIF_Init`, `InfraMultiIF_Exit`, `_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv`, `_ZN12InfraMultiIF19InfraMultiIFManager8finalizeEv`), `libInfraLanc.so` (`InfraDebugPrintfLanc`, `_ZN16InfraLancCommand17GetLANCStrobeInfoEP19InfraLancStrobeInfo`, `_ZN9InfraLanc16eventGetCallbackEPvS0_`, `_ZN9InfraLanc20eventLancApiCallbackEPvS0_`), and FX3 `v7.02` & FX6 `v6.01` `libUsbControl.so` / `libInfraExtCmdSvc.so` strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Protects FX3's `IMX510` BSI CMOS microlens/CFA array and `15-pin Multi-Terminal` inside LED volumes and studio sync bays, failing closed on:
     - `BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD`: `peak_irradiance_w_cm2 > 0.35` or (`uv_arc_welding_or_pyro_scene == True` and `uv_ir_cut_and_protective_nd_installed == False`),
     - `BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL`: `connected_to_fx3_multiterminal == True` and `bnc_sync_signal_type in {"TRILEVEL_GENLOCK", "BLACKBURST_PAL_NTSC", "WORDCLOCK_5V_TTL"}` (FX3 lacks hardware `Genlock` PLL input unlike FX6; `5V` TTL Word-Clock overdrives the `LTC` pin),
     - `BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK`: `led_volume_active == True` and `led_pwm_refresh_hz < 1920.0` and `ecs_fractional_shutter_locked == False`.
2. **Car-Rig / Motorcycle / Helicopter Hard-Mount High-Frequency Vibration (`20..200 Hz`) 5-Axis `IBIS` Voice-Coil Thermal Resonance & Secondary Stainless Steel-Tether Guard (`verify_vehiclerig_vibration_ibis_and_tether_guard`, Gate `G42`)**:
   - Protects FX3's floating 5-axis `IBIS` sensor carriage (`±1.5 mm` mechanical stops) and exterior suction/clamp mounts under sustained `20..200 Hz` chassis vibration, failing closed on:
     - `BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR`: `vibration_rms_g > 1.8` (`20..200 Hz`) and `wire_rope_or_elastomer_isolator_stage == False`,
     - `BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE`: `vibration_rms_g > 1.2` and `dominant_vibration_hz >= 35.0` and `ibis_steadyshot_mode != "OFF_MECHANICAL_PARK"` (enforcing `SteadyShot OFF` mechanical park + post `Gyroflow` `RTMD` stabilization),
     - `BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER`: `vehicle_or_aerial_exterior_mount == True` and (`secondary_steel_safety_cable_rated_kg < 25.0` or `suction_cup_count < 3`).
3. **42-Gate Master Safety Preflight (`evaluate_42gate_preflight`) & `verify-42-gates` CLI**:
   - **Offline default mode**: `39/42` gates pass (`G01..G09`, `G13..G42` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `42/42` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-42-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 22. Phase 142 Real-Hardware Main Track Part 9: `AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical, `jbusy` & `p6` `25 MiB` Quota Guard (`Gate G43`), `/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Guard (`Gate G44`), and 44-Gate Master Preflight (`realhw_jiritsu_cnflasha_and_44gate_guard.py`)

`realhw_jiritsu_cnflasha_and_44gate_guard.py` (`fx3-realhw-jiritsu-cnflasha-44gate-preflight-v1`) composes `vp_strobe_vehiclerig_ibis_and_42gate_guard.py` (`G01..G42`, leaving all prior gate modules untouched) with two real-hardware deployment and backup safety gates **`G43`** and **`G44`** into a deterministic **44-Gate Master Safety Preflight (`G01..G44`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **`AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical, `/tmp/jbusy` & `p6` `25 MiB` Quota Guard (`verify_jiritsu_service_session_and_p6_guard`, Gate `G43`)**:
   - Inspects FX3 `v7.02` `libJiritsu.so`, `ld-2.25.so`, `partinf.conf`, `mount.conf`, `p2` `kemco.txt`, `up.sh`, `loader_nor.bin`, and FX6 `p1` `kemco.txt` strictly via `os.open(..., os.O_RDONLY)` (with optional `include_large_binaries=True` scan of `appFw.so` & `cpapp-b.bin` and deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback).
   - Enforces `NP-FZ100` SoC `>= 75%` (`>= 7.4V` under load) OR regulated USB-PD (`>= 8.55V`, `>= 27W`), `/tmp/jbusy` `ENOENT` `0x11` precheck (blocking `0x10000011`), `00 ff 00` wire framing (`selector != 2`, zero `MODE`/`START`/`FORMAT`/`MOUNT` opcodes), ELF `PT_LOAD` `64 KiB` (`0x10000`) alignment + `DT_HASH (1,1,0,0)` + constructor `unlinkat` self-delete, and `p6` (`/dev/nflasha6`, `25 MiB` = `26,214,400 B`) staging quota (`peak_p6_bytes <= 8 MiB` and `p6_residual_files == 0`).
2. **`/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Guard (`verify_cnflasha_spacc_sd_escape_and_p1_p3_guard`, Gate `G44`)**:
   - Requires verified **Tier-0 Complete Cold-Backup SHA-256 Receipt** (`Sector 0` `"8246"`/`"2.00"`, `p1` `dat2=91030080`/`dat3`, `p2` `Backup.bin`/`psd.bin`/`defdet.bin`, `p6`, `p12`, `p18` `lensfile.bin`, SPI NOR `ddrtraining.dat` `@ 0x3e210fc`).
   - Enforces SPACC transparent-encryption block device boundary: any `type=5, flag=1` target (`p3`, `p7`, `p8`, `p12`, `p15`, `p23`, `p30`) MUST go through `/dev/nflashaN` or `/dev/cnflashaN`, **hard-blocking** raw plaintext `/dev/pnflashaN` writes, `nor_loader_writer.sh` SPI NOR overwrite, `us_spi_firmup.sh` (`mew.bin`), `us_darwin_firm.sh` (`darwin` ND), and `edisx.elf` Sector-0 repartitioning.
   - Enforces **SD-Card Physical Escape Hatch** (`eject SD card -> 47 us bypass to stock /usr/bin/im.elf.orig`, `< 50 ms`) and **`p1` vs `p3` Mutual-Exclusion Law** (`never modify p1 and p3 in the same transaction`; `p1` `kemco.txt` `cfg.uart=1` & line-1 `rm -f /setting/updater/mode* && sync`).
3. **44-Gate Master Safety Preflight (`evaluate_44gate_preflight`) & Phase 142 CLI Subcommands**:
   - **Offline default mode**: `41/44` gates pass (`G01..G09`, `G13..G44` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `44/44` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g43-jiritsu-service [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g44-cnflasha-dualboot [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-44-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 23. Phase 148 Real-Hardware Main Track Part 10: `054C:0DA1 -> 054C:0336` `SERVICE` `op=0xFF` RAM Canary, Single-Flight `SenserPacket`, `64 KiB` ELF Self-Unlink + `528B` `FX3S0OK` & Deterministic `MSC` Return Guard (`Gate G45`), Stage-B `p18:/lens` `MS_RDONLY` Lock, 5-Axis IBIS Safe Coil Park & Stock `66,796B` `DmmCfg.bin` 20-Pool Guard (`Gate G46`), and 46-Gate Master Preflight (`realhw_service0336_mpr_ibis_and_46gate_guard.py`)

`realhw_service0336_mpr_ibis_and_46gate_guard.py` (`fx3-realhw-service0336-mpr-ibis-46gate-preflight-v1`) composes `realhw_jiritsu_cnflasha_and_44gate_guard.py` (`G01..G44`, leaving all prior gate modules untouched) with two real-hardware `SERVICE` protocol and Stage-B peripheral/IBIS/DMM gates **`G45`** and **`G46`** into a deterministic **46-Gate Master Safety Preflight (`G01..G46`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **`054C:0DA1 -> 054C:0336` `SERVICE` Session Canary, `64 KiB` ELF Self-Unlink & Mandatory `MSC` Return Guard (`verify_service0336_canary_64k_unlink_and_msc_return`, Gate `G45`)**:
   - Inspects FX3 `v7.02` `libsencore.so`, `libJiritsu.so`, `libmpr.so`, AP `DmmCfg.bin` (`66,796 B`, `for ilc32g12m-ipsxmp`), `cpapp-b.bin`, and `p18` `lens/lensfile.bin` (`262,592 B`, `VX8900..`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Mandatory Stage-286 Branch-A `op=0xFF` pure RAM slot echo canary (`slot <= 0x11`, `1 <= size <= 5 MiB`, `sys_mount_calls == 0`, `dlopen_calls == 0`) BEFORE any `op=0x00` (`/tmp/jiritsu/libJit.so`) frame may be queued (`BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE`);
     2. Exclusive single-flight `SenserPacket` (`pFunc=0x0040`, `0x1001`) `seq` serialization (`concurrent_inflight_packets <= 1`, `seq_monotonic_strict == True`, `inconcurrent_lock_held == True`, failing closed with `BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT`);
     3. `64 KiB`-aligned (`p_align = 0x10000`) `libJit.so` entry `unlinkat` + non-truncating `528 B` `FX3S0OK` verification (`BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID`);
     4. Deterministic teardown watchdog (`STOP 0336:7 -> release 0336:8 -> 054C:0DA1 MSC re-enumeration 0da1:9` within `<= 5000 ms`, failing closed with `BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336`).
2. **Stage-B `p18:/lens` Optical Calibration RO Lock, 5-Axis IBIS Safe Coil Park & Stock `DmmCfg.bin` Pool Guard (`verify_stageb_p18_ibis_park_and_dmmcfg_guard`, Gate `G46`)**:
   - Enforces:
     1. `p18` (`/dev/nflasha18` `/lens` factory E-Mount shading/distortion calibration, `lensfile.bin` `262,592 B`) strictly `MS_RDONLY` with `p18_write_attempts_blocked == True`, `p18_mutation_bytes == 0`, and `p18_writes_requested == 0` (`BLOCKED_G46_P18_LENS_RO_OR_MUTATION`);
     2. Physical FX3 5-axis IBIS voice-coil actuators explicitly parked / held in safe `Standard` / `Off` / `CENTER_LOCK_PARK` servo state across Stage-B boot, sleep, and shutdown (`ibis_floating_coil_fault == False`, `coil_current_ma <= safe_limit_ma`, `0x0400 -> 0x1400`, `fx6_rigid_sensor_query_masked == True`, failing closed with `BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD`);
     3. Stock FX3 `66,796 B` AP `DmmCfg.bin` (`20` shared MAIN pools `for ilc32g12m-ipsxmp`) protected against FX6 `12G-SDI` / `SDI-RAW` / `Darwin-ND` pool over-allocation (`dmm_pool_overflow_bytes == 0`, `sdi_blocking_wait_ms == 0`, `fx6_sdi_raw_darwin_pools_masked == True`, failing closed with `BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING`).
3. **46-Gate Master Safety Preflight (`evaluate_46gate_preflight`) & Phase 148 CLI Subcommands**:
   - **Offline default mode**: `43/46` gates pass (`G01..G09`, `G13..G46` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `46/46` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g45-service-0336-canary [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g46-mpr-ibis-p18-guard [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-46-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 24. Phase 153 Real-Hardware Main Track Part 11: Dual-Layer `pnflasha/cnflasha` SPACC Cipher-Pairing, Per-Camera `CID` OTP Binding & `/dev/mtd0ro` SPI-NOR Guard (`Gate G47`), `p12/p13` RF Regulatory NVS Firewall, `USB MSC 054C:0DA1` Preservation, `Off-in-Rec` `>=65°C` `100% PWM` Thermal Override & `<=6100 mV` `EncWfiStop` Guard (`Gate G48`), and 48-Gate Master Preflight (`realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py`)

`realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py` (`fx3-realhw-pnflasha-mtdro-rfnvs-48gate-preflight-v1`) composes `realhw_service0336_mpr_ibis_and_46gate_guard.py` (`G01..G46`, leaving all prior gate modules untouched) with two Phase 149–152 physical-hardware boundary gates **`G47`** and **`G48`** into a deterministic **48-Gate Master Safety Preflight (`G01..G48`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **Dual-Layer `pnflasha/cnflasha` SPACC Cipher-Pairing, Per-Camera `CID` OTP Binding & `/dev/mtd0ro` SPI-NOR Guard (`verify_pnflasha_cnflasha_cid_and_mtdro_guard`, Gate `G47`)**:
   - Inspects FX3 `v7.02` `libsencore.so` (`377,328 B`), `libmpr.so` (`3,517,008 B`), `im.elf` (`40,920 B`), `cpapp-b.bin` (`15,980,568 B`), and `Backup.bin` (`2,229,740 B`, `BK4\0`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Strict same-domain cipher-pairing between `SPACC_CNFLASHA_LOGICAL` (`/dev/cnflasha*`) and `RAW_PNFLASHA_ISP` (`/dev/pnflasha*`), hard-blocking cross-domain restore (`BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH`);
     2. Per-camera eMMC `CID` SHA-256 OTP key binding (`backup_camera_cid_sha256 == target_camera_cid_sha256` & `cid_otp_key_binding_verified == True`), hard-blocking cross-body ciphertext restore (`BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH`);
     3. `/dev/mtd0ro` SPI-NOR immutability (`^/dev/mtd\d+ro$`, `O_RDONLY`, `spi_nor_write_authorized == False`, zero `MEMERASE`/`MEMWRITEOOB` ioctls, failing closed with `BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE`).
2. **`p12/p13` RF Regulatory NVS Firewall, `USB MSC 054C:0DA1` Preservation, `Off-in-Rec` `>=65°C` `100% PWM` Thermal Override & `<=6100 mV` `EncWfiStop` Guard (`verify_rfnvs_msc_fan_override_and_power_guard`, Gate `G48`)**:
   - Enforces:
     1. `p12` (`/dev/nflasha12`) and `p13` (`/dev/nflasha13`) strictly `MS_RDONLY` with `rf_nvs_write_attempts_blocked == True`, `rf_nvs_mutation_bytes == 0`, `rf_nvs_writes_requested == 0`, and zero MAC/regdomain overrides (`BLOCKED_G48_RF_NVS_OR_MAC_MUTATION`);
     2. `USB MSC 054C:0DA1` recovery reachability with active USB PHY and unspoofed descriptors (`BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE`);
     3. `cpapp-b.bin` `SET_FAN_EQ_ID` thermal override (`>=58°C -> >=45% PWM`, `>=65°C -> 100% PWM`, `>=72°C -> EncWfiStop`, rejecting `ALWAYS_OFF`, failing closed with `BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION`);
     4. `NP-FZ100` (`7.2V`) `<=6100 mV` (`2%`) graceful `EncWfiStop` (`6350 mV`/`5%` `NEAR_END`) with `18V/19.5V` DC-IN comparator masked and `false_19v5_dcin_alarms == 0` (`BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM`).
3. **48-Gate Master Safety Preflight (`evaluate_48gate_preflight`) & Phase 153 CLI Subcommands**:
   - **Offline default mode**: `45/48` gates pass (`G01..G09`, `G13..G48` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `48/48` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g47-pnflasha-mtdro-vault [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g48-rfnvs-fan-power-guard [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-48-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 25. Phase 158 Real-Hardware Main Track Part 12: `1.8V CMOS ttyAMA0 (460800 8N1)` Passive RX-Only Tap, Multi-USB `VMC-BNCM1` Timecode Contention & Off-Chip `1.8V 8-bit` eMMC ISP Guard (`Gate G49`), `IMX510` `p2:/setting/psd.bin & defdet.bin` Sensor Calibration NVS Lock, Dual-Base ISO `800/12800` & `.cube` 3D MLUT Non-Double-Bake Guard (`Gate G50`), and 50-Gate Master Preflight (`realhw_uart1v8_imx510_cal_and_50gate_guard.py`)

`realhw_uart1v8_imx510_cal_and_50gate_guard.py` (`fx3-realhw-uart1v8-imx510-50gate-preflight-v1`) composes `realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py` (`G01..G48`, leaving all prior gate modules untouched) with two Phase 158 bench electrical & imaging-sensor NVS boundary gates **`G49`** and **`G50`** into a deterministic **50-Gate Master Safety Preflight (`G01..G50`)**, keeping `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **`1.8V CMOS ttyAMA0 (460800 8N1)` Passive RX-Only Tap, Multi-USB `VMC-BNCM1` Contention Firewall & Off-Chip `1.8V 8-bit` eMMC ISP Passive Read Guard (`verify_uart1v8_vmc_bncm1_and_emmc_isp_guard`, Gate `G49`)**:
   - Inspects both FX3 `v7.02` and FX6 `v6.01` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin` & `CX95898_NTSC.bin`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Strict `1.8V` CMOS UART logic (`1620..1950 mV`), `ttyAMA0` `460800 8N1` passive high-Z `RX + GND` tap (`tx_line_connected == False`, `backpower_leakage_ua <= 5.0 uA`), hard-blocking `3.3V/5.0V` FTDI/CP2102 pad overdrive and `TX` backpower latch-up (`BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE`);
     2. Mutual exclusion between Multi-USB UART tap and `VMC-BNCM1` BNC Timecode adapter (`vmc_bncm1_simultaneous_attach == False`, failing closed with `BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION`);
     3. Off-chip `8-bit` eMMC ISP low-VCCQ (`1.8V`, `1650..1950 mV`) passive read parameters (`isp_clk_mhz <= 26.0`, `emmc_rst_n_held_low == True` when ISP active, `isp_write_cmd24_cmd25_blocked == True`, `isp_mutation_bytes == 0`, failing closed with `BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD`).
2. **`IMX510` `p2:/setting/psd.bin & defdet.bin` Sensor Calibration NVS Lock, Dual-Base ISO `800/12800` Gain Guard & `.cube` 3D MLUT Non-Double-Bake Guard (`verify_imx510_sensor_cal_and_mlut_guard`, Gate `G50`)**:
   - Enforces:
     1. Per-sensor `p2:/setting/psd.bin`, `p2:/setting/defdet.bin`, and E-Mount `p18:/lens/LENSFILE.BIN` immutability (`p2_setting_ro_locked == True`, `p18_lens_ro_locked == True`, `same_body_sensor_cal_sha256_match == True`, `sensor_cal_mutation_bytes == 0`, `cross_body_or_fx6_cal_import_attempted == False`, failing closed with `BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY`);
     2. `IMX510` Dual-Base ISO (`800` LCG `[-6.0, 22.0] dB` / `ISO 160..10000`, `12800` HCG `[0.0, 30.2] dB` / `ISO 12800..409600`) legal analog gain bounds (`BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS`);
     3. `.cube` 3D LUT (`17^3` or `33^3`, rejecting NaN/Inf/out-of-range samples) and hard-block on double-baking a monitoring MLUT into the recorded `S-Log3 / S-Gamut3.Cine` XAVC master when `mlut_burn_in_authorized == False` (`BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE`).
3. **50-Gate Master Safety Preflight (`evaluate_50gate_preflight`) & Phase 158 CLI Subcommands**:
   - **Offline default mode**: `47/50` gates pass (`G01..G09`, `G13..G50` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `50/50` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g49-uart1v8-isp [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g50-imx510-sensor-cal [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-50-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 26. Phase 161 Real-Hardware Main Track Part 13: Dual-Slot `CFexpress Type A / SDXC V90` Bitrate, Card-Door GPIO Flush & `BODYDATA.DAT` (`\x89UFU`) Pre-Update Guard (`Gate G51`), 5-Tier Unbrickable Recovery Escalation Ladder, `ILME-FX3` (`0x91030080`) Model-ID Lock & `CXD90057` EL3 (`0xfe020000`) Read-Only Guard (`Gate G52`), and 52-Gate Master Preflight (`realhw_cfexpress_ufu_el3_and_52gate_guard.py`)

`realhw_cfexpress_ufu_el3_and_52gate_guard.py` (`fx3-realhw-cfexpress-ufu-el3-52gate-preflight-v1`) composes `realhw_uart1v8_imx510_cal_and_50gate_guard.py` (`G01..G50`, leaving all prior gate modules untouched) with two Phase 161 dual-slot media, official `BODYDATA.DAT` coexistence, and 5-tier unbrickable recovery escalation gates **`G51`** and **`G52`** into a deterministic **52-Gate Master Safety Preflight (`G01..G52`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **Dual-Slot `CFexpress Type A / SDXC V90` Bitrate Gate, Card-Door GPIO Flush & Official `BODYDATA.DAT` (`\x89UFU`) Pre-Update Guard (`verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard`, Gate `G51`)**:
   - Inspects FX3 `v7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via `os.open(..., os.O_RDONLY)` (plus optional bounded `4096 B` header check of `fx3-7.02-BODYDATA.DAT`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Media speed-class bitrate gate (`XAVC S-I 4K 120p 600 Mbps` rejected on `< V90` or non-`CFexpress Type A` cards on any active recording slot, failing closed with `BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT`);
     2. Card-door open GPIO FIFO flush before unmount (`card_door_gpio_irq_armed == True`, `fifo_flushed_before_umount == True`, `unflushed_fifo_bytes_on_door_open == 0`, `umount_completed_before_power_cut == True`, failing closed with `BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO`);
     3. User clip directory preservation (`PRIVATE/M4ROOT` & `XDROOT` untouched across dual-boot switches, `m4root_mutation_bytes == 0`, `xdroot_mutation_bytes == 0`, failing closed with `BLOCKED_G51_USER_CLIP_DIR_MUTATION`);
     4. Stage-A `< 100 µs` stock bypass whenever `/mnt/sd/BODYDATA.DAT` (`\x89UFU\r\n\x1a\n`, hex `895546550d0a1a0a`) is detected on Slot A/B, plus hard-blocking official firmware update launch until `p15:/usr` `.orig` clean-uninstall `H0 == H3` is verified (`BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD`).
2. **5-Tier Unbrickable Recovery Escalation Ladder, `ILME-FX3` (`0x91030080`) `BODYDATA.DAT` Model-ID Lock & `CXD90057` EL3 (`0xfe020000`) Read-Only Guard (`verify_5tier_recovery_model_id_and_el3_ro_guard`, Gate `G52`)**:
   - Enforces:
     1. All 5 non-destructive recovery escalation tiers in exact order (`Tier-1 SD 47 µs` $\to$ `Tier-2 p15 .orig` $\to$ `Tier-3 same-model BODYDATA.DAT` $\to$ `Tier-4 Multi-USB 1.8V UART EL3 read-only` $\to$ `Tier-5 CID-matched eMMC ISP`), failing closed with `BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE`;
     2. Hard-block on cross-model `BODYDATA.DAT` (`target_model_id != 0x91030080` or `target_model_name != "ILME-FX3"` or `cross_model_bodydata_attempted == True`), failing closed with `BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH`;
     3. `CXD90057` EL3 (`0xfe020000`) strict `READ_ONLY` monitor lock (`el3_uart_tx_bytes == 0`, hard-locking `el3_payload_transmit_authorized == False`, `spi_nor_write_authorized == False`, and `persistent_emmc_writes_authorized == False`, failing closed with `BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED`).
3. **52-Gate Master Safety Preflight (`evaluate_52gate_preflight`) & Phase 161 CLI Subcommands**:
   - **Offline default mode**: `49/52` gates pass (`G01..G09`, `G13..G52` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `52/52` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g51-cfexpress-ufu [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g52-5tier-el3-guard [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-52-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 27. Phase 165 Real-Hardware Main Track Part 14: `CXD90057` *Mira* + `CXD90058` *Cetus* Dual-BIONZ-XR Inter-SoC Link & `sabin` SA-DSP Immutability Guard (`Gate G53`), Post-Bench `16/16 H0 == H3` Factory Seal & Zero `/tmp/jiritsu` Residual Guard (`Gate G54`), and 54-Gate Master Preflight (`realhw_cxd90058_sabin_seal_and_54gate_guard.py`)

`realhw_cxd90058_sabin_seal_and_54gate_guard.py` (`fx3-realhw-cxd90058-sabin-seal-54gate-preflight-v1`) composes `realhw_cfexpress_ufu_el3_and_52gate_guard.py` (`G01..G52`, leaving all prior gate modules untouched) with two Phase 165 dual-SoC co-processor immutability and post-bench factory-seal / official-update readiness gates **`G53`** and **`G54`** into a deterministic **54-Gate Master Safety Preflight (`G01..G54`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **`CXD90057` (*Mira*) + `CXD90058` (*Cetus*) Dual-BIONZ-XR Inter-SoC Link, `sabin` 32-bit SA-DSP Immutability, FX6 `16-bit SDI RAW` / `mew.bin` FPGA Output Mask & `1,724.00 MiB` `memcfg=` Encoder Pool Guard (`verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard`, Gate `G53`)**:
   - Inspects FX3 `v7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Zero mutation to `p8:/cpapp-b.bin` (pinned SHA-256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`), `CXD90058` secondary co-processor boot blobs (`cxd90058_mutation_bytes == 0`), and `sabin` 32-bit SA-DSP microcode (`sabin_dsp_mutation_bytes == 0`), failing closed with `BLOCKED_G53_CXD90058_OR_SABIN_MUTATION`;
     2. Healthy `CXD90057 <-> CXD90058` inter-SoC link (`SLVS-EC` / `IVSHMEM` / `UIPC_CP_IPC`) tied to `p8:/cpapp-b.bin`, failing closed with `BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION`;
     3. Fail-closed masking of FX6-only `16-bit SDI RAW` / `mew.bin` FPGA output paths (`output_path` restricted to FX3 paths without `SDI`/`MEW`), failing closed with `BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED`;
     4. Valid `XAVC-I` / `XAVC S-I` / `XAVC HS` hardware encoder pool alignment (`>= 4 KiB` power-of-2 alignment, `memcfg_overflow_bytes == 0`) within FX3's exact `1,724.00 MiB` `memcfg=` budget, failing closed with `BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW`.
2. **Post-Bench `16/16 H0 == H3` Bit-Identical Factory Seal, Zero `.orig`/`/tmp/jiritsu`/`p6` Residual & Pre-Official-Update Cleanliness Guard (`verify_post_bench_factory_seal_and_official_readiness_guard`, Gate `G54`)**:
   - Enforces:
     1. Bit-identical restoration (`SHA256(H0) == SHA256(H3)`) across all 16 canonical storage surfaces (`sector0`, `emmc_boot0`, `emmc_boot1`, `p1_updater`, `p2_setting`, `p3_system`, `p5_wbi`, `p6_jiritsu`, `p7_rootfs`, `p8_cpapp`, `p10_vfat`, `p12_cert`, `p13_rf_nvs`, `p15_usr`, `p18_lens`, `spi_nor_ro`), failing closed with `BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH`;
     2. Zero leftover `/usr/bin/im.elf.orig`, `/etc/ld.so.preload`, `/tmp/jiritsu/*`, or `p6` chunk residual (`residual_artifact_count == 0`), failing closed with `BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT`;
     3. Clean warranty / official-update readiness (`OTP == 0`, `RPMB == 0`, `/setting/updater/mode* == 0`, `official_update_ready == True`), failing closed with `BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY`.
3. **54-Gate Master Safety Preflight (`evaluate_54gate_preflight`) & Phase 165 CLI Subcommands**:
   - **Offline default mode**: `51/54` gates pass (`G01..G09`, `G13..G54` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `54/54` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g53-cxd90058-sabin [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g54-factory-seal [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-54-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 28. Phase 170 Real-Hardware Main Track Part 15: `p12:/cert/RQ_LIC.DAT` C2PA Read-Only Lock & Cross-Model Signing Firewall (`Gate G55`), `VMC-BNCM1` `EXT-LK` SMPTE-12M LTC / `1.8V UART` Mux, `TC-OUT` BNC Mask & `IMX510` 6-Axis IMU Gyro `NonRealTimeMeta.xml` Guard (`Gate G56`), and 56-Gate Master Preflight (`realhw_c2pa_tc_gyro_and_56gate_guard.py`)

`realhw_c2pa_tc_gyro_and_56gate_guard.py` (`fx3-realhw-c2pa-tc-gyro-56gate-preflight-v1`) composes `realhw_cxd90058_sabin_seal_and_54gate_guard.py` (`G01..G54`, leaving all prior gate modules untouched) with two Phase 170 C2PA authenticity license, Multi-Port SMPTE-12M LTC / UART mux, and `IMX510` 6-axis IMU gyro stabilization metadata gates **`G55`** and **`G56`** into a deterministic **56-Gate Master Safety Preflight (`G01..G56`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **`p12:/cert/RQ_LIC.DAT` C2PA Authenticity License Read-Only Lock & Cross-Body/Cross-Model Signing Firewall (`verify_c2pa_rq_lic_and_cross_model_signing_guard`, Gate `G55`)**:
   - Inspects FX3 `v7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Strict `MS_RDONLY` mount and zero mutation on `p12:/cert` (`/dev/nflasha12`, `c2pa_cert_mutation_bytes == 0`, `c2pa_cert_write_requested == False`, failing closed with `BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION`);
     2. Same-body `p12:/cert/RQ_LIC.DAT` SHA-256 preservation across `H0..H3` (`H0 == H1 == H2 == H3`, `1 <= c2pa_license_count <= 100`, failing closed with `BLOCKED_G55_RQ_LIC_SHA256_DRIFT`);
     3. Hard-block on cross-body or cross-model C2PA signing key usage (`target_model_id == 0x91030080`, `target_model_name == "ILME-FX3"`, `signing_key_body_match == True`, `c2pa_cross_model_signing_blocked == True`, failing closed with `BLOCKED_G55_CROSS_MODEL_SIGNING_KEY`).
2. **`VMC-BNCM1` (`EXT-LK` SMPTE-12M LTC `0.5V–4.5V p-p`) Electrical Bounds, Multi-USB `1.8V UART` Mutual Exclusion, FX6 `TC-OUT` BNC Mask & `IMX510` 6-Axis IMU Gyro `NonRealTimeMeta.xml` Integrity Guard (`verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard`, Gate `G56`)**:
   - Enforces:
     1. Electrical bounds (`500..4500 mV` AC-coupled `SMPTE-12M` `EXT-LK`, hard-blocking `ltc_peak_to_peak_mv > 5000`, `680 kOhm ± 10%` ID resistor) and strict mutual exclusion with Multi-USB `1.8V UART` tap (`multi_usb_uart_1v8_active == False` when `VMC-BNCM1` attached, failing closed with `BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH`);
     2. Fail-closed masking of FX6-only dedicated BNC `TC-OUT` drive (`fx6_tc_out_bnc_masked == True`, `tc_out_bnc_drive_requested == False`, `tc_direction == "IN"`, failing closed with `BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED`);
     3. `IMX510` `8.7 ms` rolling-shutter + `6`-axis IMU (`2000 Hz`) gyro packet CRC/monotonicity and `MXF/MP4` `NonRealTimeMeta.xml` (`v2.20`) integrity for Catalyst Browse / DaVinci Resolve stabilization (failing closed with `BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT`).
3. **56-Gate Master Safety Preflight (`evaluate_56gate_preflight`) & Phase 170 CLI Subcommands**:
   - **Offline default mode**: `53/56` gates pass (`G01..G09`, `G13..G56` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `56/56` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g55-c2pa-cert [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g56-tc-gyro-meta [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-56-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 29. Phase 173 Real-Hardware Main Track Part 16: Dual-Media Independent Tier-0 Cold-Backup Device-ID Separation & `GF(256)` Bit-Rot Scrub Guard (`Gate G57`), Two-Step Explicit Human Bench Authorization & Zero-Auto-Flash Interlock (`Gate G58`), and Unified 58-Gate Master Preflight (`realhw_dualmedia_bench_interlock_and_58gate_guard.py`)

`realhw_dualmedia_bench_interlock_and_58gate_guard.py` (`fx3-realhw-dualmedia-bench-58gate-preflight-v1`) composes `realhw_c2pa_tc_gyro_and_56gate_guard.py` (`G01..G56`, leaving all prior gate modules untouched) with two Phase 173 real-hardware dual-media Tier-0 backup isolation and human bench interlock gates **`G57`** and **`G58`** into a deterministic **58-Gate Master Safety Preflight (`G01..G58`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, and `overall_ready_for_hardware_attach = False` hard-locked:

1. **Dual-Media Independent Tier-0 Cold-Backup Device-ID Separation & `GF(256)` RAID-6 Bit-Rot Scrub Guard (`verify_dual_media_vault_and_gf256_scrub_guard`, Gate `G57`)**:
   - Inspects FX3 `v7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Physical storage independence across Media A and Media B (`media_a_st_dev != media_b_st_dev`, distinct non-overlapping mount roots and device/volume IDs, failing closed on single-disk / same-filesystem pseudo-backups with `BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV`);
     2. `16/16` canonical Tier-0 storage surface SHA-256 parity across both cold-backup vaults (`parity_matched_count == 16`, failing closed with `BLOCKED_G57_16_SURFACE_SHA256_MISMATCH`);
     3. Pure-Python `GF(2^8)` (`0x11d`) RAID-6 P+Q parity generation, bit-rot scrub verification, and erasure/corruption recovery (`unrecoverable_chunk_count == 0`, recovering 1- or 2-shard loss/corruption cleanly while failing closed on `>= 3` simultaneous shard losses or unhealed bit-rot with `BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS`).
2. **Two-Step Explicit Human Bench Authorization, Pre-Install `NP-FZ100 >= 80%` (`>= 7400 mV`) & Zero-Auto-Flash Interlock (`verify_two_step_bench_interlock_guard`, Gate `G58`)**:
   - Enforces:
     1. Hard zero-auto-flash interlock (`agent_auto_flash_blocked == True`, `auto_flash_requested == False`, `ai_agent_self_authorize_attempted == False`, repository constants hard-locked `False`, failing closed with `BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION`);
     2. Pre-install `NP-FZ100` battery health bounds (`>= 80%` SOC and `>= 7400 mV` terminal voltage, failing closed with `BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD`);
     3. Verified `op=0xFF` RAM canary `FX3S0OK` (`528 B`) receipt with clean MSC `054C:0DA1` return and dual-media `FX3RCPT1` (`528 B`) cold-backup receipt match (failing closed with `BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED`), plus explicit two-step human confirmation (`EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE`) whenever live bench execution is requested (failing closed with `BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING`).
3. **58-Gate Master Safety Preflight (`evaluate_58gate_preflight`) & Phase 173 CLI Subcommands**:
   - **Offline default mode**: `55/58` gates pass (`G01..G09`, `G13..G58` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated-backup` rehearsal mode**: `58/58` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, and `physical_flash_auto_exec_authorized = False` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g57-dualmedia-vault [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g58-bench-interlock [--clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-58-gates [--clean-room] [--dry-run-simulated-backup] [--json]
```

---

## 30. Phase 177 Real-Hardware Main Track Part 17: `ssboot` / `WBI2` `prsv-img` Bootloader-Bypass Guard (`Gate G59`), `FX3 7.02` `>=2.04` UFU Floor & Slot-1 C2PA 100-License Guard (`Gate G60`), and 60-Gate Milestone Master Preflight (`realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py`)

`realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py` (`fx3-realhw-ssboot-wbi2-slot1-ufu-60gate-preflight-v1`) composes `realhw_dualmedia_bench_interlock_and_58gate_guard.py` (`G01..G58`, keeping `evaluate_58gate_preflight` and CLI `verify-58-gates` 100% intact) with two Wave-21 real-hardware safety gates **`G59`** and **`G60`** into the milestone **60-Gate Master Safety Preflight (`G01..G60`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **Sony SCEL `ssboot` / `WBI2` `prsv-img` Bootloader-Bypass Guard (`verify_ssboot_wbi2_prsvimg_and_liro_guard`, Gate `G59`)**:
   - Inspects FX3 `v7.02` `liro.ko`, `init2`, `fstab`, `im.elf`, `libmpr.so`, and the `4,096 B` header of `fx3-7.02-BODYDATA.DAT` strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Tier-0 cold-backup receipt (`FX3RCPT1`, `528 B`) capturing BOTH the exact `512 B` sector-0 `WBI2` (`57 42 49 32 00 00 00 00`) header AND full `/dev/nflasha5` (`~232.5 MiB`, LZO `prsv-img`) SHA-256 baseline (`H0`) prior to dual-boot activation (`BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING`);
     2. Stage-B read-only lock (`BLKROSET=1` on both `/dev/nflasha5` and `/dev/pnflasha5`) plus `/proc/udm` & `PM_SUSPEND_DISK` (`disk`) write-blocking so FX6 userland cannot overwrite Stock FX3's `WBI2` snapshot (`wbi_persistent_writes == 0`, `stageb_snapshot_save_blocked == True`, failing closed with `BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED`);
     3. Active/unhandled `WBI2` resume trap guard ensuring `/sbin/init` (`fx6-stage-a-verify`) is never bypassed (`BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP`);
     4. Bit-exact Clean Uninstall (`H2 -> H3`) restoration (`H0 == H3` on both `512 B` `WBI2` sector-0 header and full `nflasha5`, preserving Stock FX3 `0.5s` warm-boot, failing closed with `BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH`).
2. **`FX3 7.02` `>= Ver. 2.04` UFU Floor, Slot-1 Root & Duplicate Filename Guard, C2PA 100-License Ceiling & `Ver. 7.00+` Wireless Security Floor (`verify_fx3_702_ufu_floor_and_slot1_c2pa_guard`, Gate `G60`)**:
   - Enforces:
     1. Body firmware version floor `>= Ver. 2.04` (hard-blocking `<= Ver. 2.02` which causes `7 long + 7 short` LED blink failure on real FX3), `7.02` target (`BODYDATA.DAT`, `811,876,768 B`, `\x89UFU\r\n\x1a\n`, Model ID `0x91030080`, failing closed with `BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR`);
     2. **Slot 1 root only** placement for `BODYDATA.DAT` and C2PA license/cert imports, rejecting Slot-2 attempts, subdirectory paths, and duplicate/renamed files such as `BODYDATA (1).DAT` / `BODYDATA_OLD.DAT` (`BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA`);
     3. C2PA hardware ceiling (`<= 100` licenses per package) and `p12:/cert/RQ_LIC.DAT` `BLKROSET=1` + `MS_RDONLY` protection during Stage-B (`BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO`);
     4. `Ver. 7.00+` wireless security floor rejecting deprecated `WEP`, `WPA1`, and legacy `IPsec` profiles while permitting `WPA2`, `WPA3`, and `Access Authentication` (`BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC`).
3. **60-Gate Milestone Master Preflight (`evaluate_60gate_preflight`) & Phase 177 CLI Subcommands**:
   - **Offline default mode**: `57/60` gates pass (`G01..G09`, `G13..G60` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `60/60` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g59-ssboot-wbi2-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g60-slot1-ufu-c2pa-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-60-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 31. Phase 181 Real-Hardware Main Track Part 18: `MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` Breathing Guard (`Gate G61`), Type-A HDMI `4264x2408` 16-bit RAW vs `12G-SDI` Mask Guard (`Gate G62`), and 62-Gate Master Preflight (`realhw_emount_info3d_hdmi_braw_and_62gate_guard.py`)

`realhw_emount_info3d_hdmi_braw_and_62gate_guard.py` (`fx3-realhw-emount-info3d-hdmi-braw-62gate-preflight-v1`) composes `realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py` (`G01..G60`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `verify-58-gates`, and `verify-60-gates` 100% intact) with two Wave-22 `MIRA_CETUS2` real-hardware safety gates **`G61`** and **`G62`** into the **62-Gate Master Safety Preflight (`G01..G62`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` Breathing Guard (`verify_emount_info3d_and_breathing_02cf0232_guard`, Gate `G61`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `appFw.so` (`79,015,712 B`), and `p18:/lens/LENSFILE.BIN` (`262,592 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. `MIRA_CETUS2` E-mount serial packet integrity (`info7` 16-bit lens ID, `info8` focus/iris drive parameters, `info3D` extended optical profile & CRC, failing closed with `BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT`);
     2. Sony first-party lens capability filter `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)` for `BKID_APP_MR_SETTING_LENS_COMP_BREATHING` (`0x02cf0232`) and lossless Stage-B passthrough (`BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED`);
     3. Monitor & Control `Ver. 2.1.0+` Focus Map strictly read-only depth telemetry (`focus_map_emmc_writes == 0`, `focus_map_cp_mutation_bytes == 0`, failing closed with `BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE`);
     4. `BLKROSET=1` + `MS_RDONLY` on `p18:/lens/LENSFILE.BIN` (`lens_partition_writes == 0`) while blocking legacy CineAlta manual `LENSFILE` slot writes (`BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE`).
2. **Type-A HDMI `4264x2408` 16-bit Linear RAW `.braw` / `ProRes RAW` vs `12G-SDI` Mask Guard (`verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard`, Gate `G62`)**:
   - Enforces:
     1. FX3 `7.02` full-size Type-A HDMI `4264 × 2408` (`16:9` up to `60p`) 16-bit linear RAW specification alongside simultaneous internal `XAVC S / HS / S-I + Proxy` recording (`BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID`);
     2. `Blackmagic Video Assist 12G HDR` (`3.22+`, `BRAW 5.1+`, `DaVinci Resolve 20.2+`) compatibility—rejecting `3G` models, enforcing `.braw` ISO capture-state lock, and rejecting expectations of private Blackmagic sensor profiles (`BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED`);
     3. `Atomos Ninja` (`AtomOS 10.64+`, `DaVinci Resolve 20.2+`) `ProRes RAW` WB/ISO offset metadata verification (`BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID`);
     4. Hard-masking FX6's non-existent `12G-SDI` BNC hardware MMIO/driver probes (`sdi_mmio_probes_emitted == 0`, `fx6_12gsdi_raw_enabled == False`, `hdmi_raw_pipeline_routed == True`, failing closed with `BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED`).
3. **62-Gate Master Preflight (`evaluate_62gate_preflight`) & Phase 181 CLI Subcommands**:
   - **Offline default mode**: `59/62` gates pass (`G01..G09`, `G13..G62` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `62/62` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g61-emount-breathing-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g62-hdmi-raw-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-62-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 32. Phase 187 Real-Hardware Main Track Part 19: `ILME-FX3` vs `ILME-FX3A` Hardware-Branch Firewall (`Gate G63`), `XLR-H1` MI-Shoe `48kHz/24bit 4ch` vs Body `3.5mm` Override Guard (`Gate G64`), and 64-Gate Master Preflight (`realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py`)

`realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py` (`fx3-realhw-fx3a-firewall-xlrh1-mishoe-64gate-preflight-v1`) composes `realhw_emount_info3d_hdmi_braw_and_62gate_guard.py` (`G01..G62`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`, `verify-58-gates`, `verify-60-gates`, and `verify-62-gates` 100% intact) with two Wave-23 Sony real-hardware safety gates **`G63`** and **`G64`** into the **64-Gate Master Safety Preflight (`G01..G64`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` vs `ILME-FX3A` LCD/NFC/IR Hardware-Branch & `BODYDATA.DAT`/`CAMSET` Isolation Firewall (`verify_fx3_vs_fx3a_branch_firewall`, Gate `G63`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `appFw.so` (`79,015,712 B`), and FX6 donor `libInfraHotshoe.so` (`47,808 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Original **`ILME-FX3` (`0x91030080`, `Ver. 7.02`, `1,440,000-dot` LCD, NFC present, IR receiver present)** parity vs **`ILME-FX3A` (`2025` hardware revision, `Ver. 2.02`, `2,359,296-dot` XGA LCD, NFC & IR physically omitted)** and **`ILME-FX30` (`0x91030084`)**—failing closed with `BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE` or `BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH` (`< 50 µs` fail-closed ceiling);
     2. Rejection of `FX3A` `Ver. 1.xx/2.xx` `BODYDATA.DAT` packages and non-`FX3` `BODYDATA.DAT` targets (`BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X`);
     3. Strict `CAMSET` settings isolation blocking cross-branch `FX3 <-> FX3A` imports (`BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT`).
2. **`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Digital Audio Safety & Routing vs Body `3.5mm` Override Guard (`verify_xlrh1_mishoe_4ch_vs_35mm_override_guard`, Gate `G64`)**:
   - Enforces:
     1. Verified `XLR-H1` MI-Shoe digital audio routing & format profiles (`48KHZ_24BIT_4CH`, `48KHZ_24BIT_2CH`, `48KHZ_16BIT_2CH`; `HANDLE AUDIO = ON`; `IN1/IN2` XLR -> `CH1_CH2`, `IN3` 3.5mm -> `CH3_CH4`; `4ch Audio Monitoring` headphone matrix `CH1_2`, `CH3_4`, `CH1+3_CH2+4`; post-`BODYDATA.DAT` `16bit/2ch` reset reconciliation, failing closed with `BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID`);
     2. Body `3.5mm` mic-jack plug-in physical override detection (`[MI Shoe Audio Set.]` grayed/locked out -> `BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE`) and `S&Q` audio mute consistency (`BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY`);
     3. Phantom-power `+48V` glitch & slew-rate/ADC soft-mute guard during `STAGE_A_TO_STAGE_B` handoff (`BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH`);
     4. Hard rejection of fake standalone `XLR-H1` USB firmware payloads (`BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD`).
3. **64-Gate Master Preflight (`evaluate_64gate_preflight`) & Phase 187 CLI Subcommands**:
   - **Offline default mode**: `61/64` gates pass (`G01..G09`, `G13..G64` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `64/64` simulation gates pass (`dry_run_rehearsal_only = True`) while `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g63-fx3a-branch-firewall [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g64-xlrh1-mishoe-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-64-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 33. Phase 191 Real-Hardware Main Track Part 20: `ILME-FX3` No-UVC Gadget Firewall & `USB-PD` (`NP-FZ100`) / `DC-C1` (`>=65W / 5A`) Electrical Interlock (`Gate G65`), Dual-Media `.cube` User LUT Path-Asymmetry (`SD` vs `CFexpress-A`), `Cine EI` `800/12800` & `RMT-P1BT` BT/IR Mutual-Exclusion Guard (`Gate G66`), and 66-Gate Master Preflight (`realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py`)

`realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py` (`fx3-realhw-nouvc-dcc1-pd-lut-path-66gate-preflight-v1`) composes `realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py` (`G01..G64`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`, `evaluate_64gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`, and `verify-64-gates` 100% intact) with two Wave-24 Sony real-hardware safety gates **`G65`** and **`G66`** into the **66-Gate Master Safety Preflight (`G01..G66` / `run_66_gate_preflight` / `evaluate_66gate_preflight`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `HUMAN_HARDWARE_ATTACH_TOKEN = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` (`0x91030080`) No-UVC USB Gadget Firewall & `USB-PD` (`NP-FZ100`) / `DC-C1` (`>=65W / 5A`) Electrical Interlock (`verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard`, Gate `G65`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `appFw.so` (`79,015,712 B`), and `libUsbBusPower.so` (`48,232 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Hard-blocking any Stage-B attempt to configure or bind a UVC/UAC `[USB Streaming]` composite gadget on `ILME-FX3` / `ILME-FX3A` (`4.9.337-scel+`), permitting strictly `Sel. When Connect`, `MassStorage(MSC)`, `MTP`, `Remote Shooting`, and `USB-LAN` (`RNDIS`/`CDC-NCM`), while routing 4K streaming strictly via Network Streaming (`RTMP/RTMPS/SRT <= 38 Mbps`) or Type-A HDMI (`BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN`, `BLOCKED_G65_INVALID_STREAMING_TRANSPORT`);
     2. Physical power-supply interlock before Tier-0 cold backup or Stage-B rehearsal:
        - `power_source == "USB_PD_BODY"`: requires `np_fz100_inserted == True`, `battery_pct >= 51` (`>= 3 bars`), and rejects Micro-USB power (`BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT`, `BLOCKED_G65_MICRO_USB_POWER_REJECTED`);
        - `power_source == "DC_C1_COUPLER"`: requires `usb_pd_watts >= 65` and `emarked_5a_cable == True` (`cable_max_amps >= 5.0`), rejecting `<65W` or `3A` cables that trigger `DC-C1` blinking-LED brownout (`BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE`).
2. **Dual-Media `.cube` User LUT Path-Asymmetry (`SD` vs `CFexpress-A`), `Cine EI` (`800 / 12800`) & `RMT-P1BT` BT/IR Mutual-Exclusion Guard (`verify_dualmedia_lut_path_cineei_and_bt_guard`, Gate `G66`)**:
   - Enforces:
     1. Exact `.cube` User LUT rules (`LUT_3D_SIZE` strictly `17` or `33`, ASCII filename `<= 63` bytes including `.cube`, max `16` slots `User1..User16`, `AE Level Offset` `0.0..+2.0 EV` in `1/3` EV steps -> `BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING`);
     2. Dual-media path asymmetry (`SD`/`SDXC`: `/Private/Sony/PRO/LUT/`, `CFexpress Type A`: `/Sony/PRO/LUT/`), rejecting swapped paths or direct writes into Stock `p2:/setting` during Stage-B (`BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE`);
     3. `Cine EI` base sensitivity lock (`800` -> `200..3200 EI`, `12800` -> `3200..51200 EI`, `±2 EV`, zero CMOS analog gain mutation -> `BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS`);
     4. `Bluetooth Rmt Ctrl = On` (`RMT-P1BT` BT `4.2`) automatic mutual-exclusion lock disabling IR remote & smartphone GPS location linking (`BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION`).
3. **66-Gate Master Preflight (`run_66_gate_preflight` / `evaluate_66gate_preflight`) & Phase 191 CLI Subcommands**:
   - **Offline default mode**: `63/66` gates pass (`G01..G09`, `G13..G66` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `66/66` simulation gates pass (`dry_run_rehearsal_only = True`) while `human_hardware_attach_token = False`, `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g65-nouvc-dcc1-pd [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g66-lut-path-cineei-bt [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-66-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 34. Phase 196 Real-Hardware Main Track Part 21: `ILME-FX3` (`Ver. 7.02`) Power-On `USB-LAN` (`RNDIS/CDC-NCM`) Auto-Connect & Network Streaming (`RTMP/RTMPS/SRT <= 38 Mbps`) Guard (`Gate G67`), `Creators' Cloud` Clip-Flag (`OK/NG/KEEP`) & Anamorphic (`1.5x/1.6x`) / Bright-Monitoring Focus-Magnifier Guard (`Gate G68`), and 68-Gate Master Preflight (`realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py`)

`realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py` (`fx3-realhw-usblan-rtmp-clipflag-anamorphic-68gate-preflight-v1`) composes `realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py` (`G01..G66`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`, `evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`, `verify-64-gates`, and `verify-66-gates` 100% intact) with two Wave-24 real-hardware safety gates **`G67`** and **`G68`** into the **68-Gate Master Safety Preflight (`G01..G68` / `run_68_gate_preflight` / `evaluate_68gate_preflight`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `HUMAN_HARDWARE_ATTACH_TOKEN = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` (`Ver. 7.00 / 7.02`) Power-On `USB-LAN` (`RNDIS/CDC-NCM`) Auto-Connect & Network Streaming (`RTMP/RTMPS/SRT <= 38 Mbps` `3840x2160 59.94p`) Guard (`verify_usblan_autoconnect_and_rtmp_srt_guard`, Gate `G67`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `appFw.so` (`79,015,712 B`), and `libNetServiceEther.so` (`114,384 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. `Ver. 7.00+` power-on USB-LAN adapter auto-connection (`CDC-NCM` / `ASIX` `AX88179` / `RTL8153` / `RNDIS` over `USB Type-C` powered via `NP-FZ100 >= 51%` or `DC-C1 >= 65W` + `5A` e-Marked cable, rejecting unsupported `AX88179A/B` / `RTL8156` / `CDC-ECM` adapters -> `BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE`);
     2. Zero Stage-B overwrite of Stock `/setting` / `p2:/setting` / `/dev/nflasha2` network profiles (`BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE`);
     3. Network Streaming bitrate & codec ceiling (`RTMP` / `RTMPS` / `SRT` `<= 38.0 Mbps`, `<= 3840x2160 @ 59.94p`, `H.265/HEVC` or `H.264/AVC` -> `BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION`);
     4. Strict TLS certificate read-only (`EROFS` / `MS_RDONLY`, `0 B` mutation) verification for `RTMPS` (`BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED`).
2. **`Creators' Cloud` (`Creators' App >= 3.1.0` / `M&C >= 2.4.0`) `OK/NG/KEEP` Clip-Flag Metadata Hygiene & `1.5x / 1.6x` Anamorphic De-Squeeze / Bright-Monitoring Focus-Magnifier Guard (`verify_clipflag_anamorphic_and_bright_magnifier_guard`, Gate `G68`)**:
   - Enforces:
     1. Non-destructive MXF/XML sidecar clip-flag (`OK`, `NG`, `KEEP`) filtering with `video_essence_modified == False`, `video_essence_mutation_bytes == 0`, and SHA-256 essence invariance (`BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR`);
     2. `1.3x / 1.5x / 1.6x / 2.0x` monitoring-only anamorphic de-squeeze lock that automatically disables during HDMI RAW output so `4264x2408` linear RAW stays unscaled (`BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE`);
     3. Focus Magnifier (`1x/2x/4x/8x`) coexistence with Bright Monitoring on `CXD90057` (`BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT`).
3. **68-Gate Master Preflight (`run_68_gate_preflight` / `evaluate_68gate_preflight`) & Phase 196 CLI Subcommands**:
   - **Offline default mode**: `65/68` gates pass (`G01..G09`, `G13..G68` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `68/68` simulation gates pass (`dry_run_rehearsal_only = True`) while `human_hardware_attach_token = False`, `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g67-usblan-rtmp [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g68-clipflag-anamorphic [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-68-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 35. Phase 199 Real-Hardware Main Track Part 22: `ILME-FX3` (`Ver. 7.02`) Exact 4-Mode `[Fan Control]` (`Off in Rec` Standby `100% MAX PWM` / `Always Off` Pre-Backup Block) Guard (`Gate G69`), `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` User LUT Binary Split & Independent Shutter `Speed/Angle` Guard (`Gate G70`), and 70-Gate Master Preflight (`realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py`)

`realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py` (`fx3-realhw-fan-pwm-shutter-angle-lut-split-70gate-preflight-v1`) composes `realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py` (`G01..G68`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`, `evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `evaluate_68gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`, `verify-64-gates`, `verify-66-gates`, and `verify-68-gates` 100% intact) with two Wave-25 real-hardware safety gates **`G69`** and **`G70`** into the **70-Gate Master Safety Preflight (`G01..G70` / `run_70_gate_preflight` / `evaluate_70gate_preflight`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `HUMAN_HARDWARE_ATTACH_TOKEN = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` (`Ver. 7.02`) Exact 4-Mode `[Fan Control]` (`Auto`, `Minimum`, `Off in Rec`, `Always Off` — Rejecting `Auto1/Auto2`) & Pre-Backup Thermal Guard (`verify_fx3_4mode_fan_pwm_and_prebackup_guard`, Gate `G69`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `libfan.so` (`27,280 B`), `FX3-CX95900_ALLLANG-Backup.bin` (`2,229,740 B`), and FX6 `6.01` `CX95898_NTSC.bin` (`2,253,333 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Exact 4-mode `ILME-FX3` `[Fan Control]` menu enum (`Auto`, `Minimum`, `Off in Rec`, `Always Off` — rejecting non-FX3 studio/Lumix `Auto1`/`Auto2` tokens -> `BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2`);
     2. `Off in Rec` PWM physics (`0%` PWM during normal recording `< 78.0°C`, `100%` emergency thermal override at `>= 78.0°C` in Rec, and `100% MAX PWM` active heat-purge during Standby -> `BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION`);
     3. Fail-closed pre-backup (`AdjustControl 0x40` `75 MiB` `p3` cold backup) / high-load dual-system rehearsal guard when `[Fan Control] == Always Off` (`BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED`) or non-`Auto` (`BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO`), with `[Auto Power OFF Temp.] = Standard / High` thermal ceiling awareness protecting `CXD90057 / CXD90058` (`BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT`).
2. **`FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT Binary Format Split Firewall & Independent `[Shutter Mode]` (`Speed` vs `Angle`) Bounds (`verify_lut_601_702_split_and_shutter_angle_guard`, Gate `G70`)**:
   - Enforces:
     1. `<= 6.01` (`LEGACY_V601_USER_LUT_BIN`) vs `7.00+` (`OPTIMIZED_V700_PLUS_USER_LUT_BIN`) `User1..User16` binary slot split firewall blocking direct Stage-B `FX6 Ver. 6.01` writes into Stock `FX3 Ver. 7.02` `p2:/setting` (`BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE`), requiring volatile `/tmp/fx6_lut_overlay` redirection, stale `<= 6.01` LUT re-registration hygiene (`BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID`), and `H0 == H3` `p2:/setting` SHA-256 invariance (`BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT`);
     2. Independent `[Shutter Mode]` `Speed` vs `Angle` `Backup.bin` slot storage (`0x01120024` vs `0x01120028`) without inactive-slot toggle mutation and full immunity to `[Exposure step]` (`0.3EV` / `0.5EV`) (`BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION`);
     3. Exact shutter angle bounds (`5.6°..64F` in normal `23.98p..59.94p` Movie vs clamped `5.6°..360.0°` at `119.88p / 100p` and in `S&Q` -> `BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS`).
3. **70-Gate Master Preflight (`run_70_gate_preflight` / `evaluate_70gate_preflight`) & Phase 199 CLI Subcommands**:
   - **Offline default mode**: `67/70` gates pass (`G01..G09`, `G13..G70` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `70/70` simulation gates pass (`dry_run_rehearsal_only = True`) while `human_hardware_attach_token = False`, `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g69-fan-pwm-thermal [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g70-lut-601-702-shutter-angle [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-70-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 36. Phase 201 Real-Hardware Main Track Part 23: `ILME-FX3` (`Ver. 7.02`) `BIG6` (`[Home (Lower Left)]`) Zero Physical e-ND Actuator & Slot-1 `CAMSET` Dual-Media Firewall (`Gate G71`), `VMC-BNCM1` Body-Only `TC IN` (`EXT-LK`) / `XLR-H1` Handle Micro-USB Block / Digital HDMI-Only `TC OUT` Guard (`Gate G72`), and 72-Gate Master Preflight (`realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.py`)

`realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.py` (`fx3-realhw-big6-noend-camset-slot1-vmcbncm1-72gate-preflight-v1`) composes `realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py` (`G01..G70`, keeping `evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`, `evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `evaluate_68gate_preflight`, `evaluate_70gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`, `verify-64-gates`, `verify-66-gates`, `verify-68-gates`, and `verify-70-gates` 100% intact) with two Wave-26 real-hardware safety gates **`G71`** and **`G72`** into the **72-Gate Master Safety Preflight (`G01..G72` / `run_72_gate_preflight` / `evaluate_72gate_preflight`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `HUMAN_HARDWARE_ATTACH_TOKEN = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` (`Ver. 7.02`) `BIG6` (`[Mode Settings] = [Fixed/Variable]`) Zero Physical e-ND Actuator Firewall & Slot-1 `CAMSET01..10.DAT` Dual-Media Isolation (`verify_fx3_big6_zero_end_and_slot1_camset_guard`, Gate `G71`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `libSaveLoadSettings.so` (`18,760 B`), `libUsbControl.so` (`135,424 B`), `FX3-CX95900_ALLLANG-Backup.bin` (`2,229,740 B`), and FX6 `6.01` `CX95898_NTSC.bin` (`2,253,333 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. `Ver. 7.00+` `BIG6` (`Home`) 6-cell + 7th status bar topology (`[Mode Settings] = [Fixed/Variable]`, `[HOME]` custom key assigned, `[Home (Lower Left)]` = `Aperture` default or virtual `ND Filter` metadata -> `BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID`) and strict `e_nd_actuator_tx_count == 0` blocking `FX6` variable e-ND (`1/4..1/128`) CP motor commands on `ILME-FX3` (`BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN`);
     2. Slot-1-only `[Save/Load Settings]` (`Slot 2` rejected, disabled in `MR` Recall Camera Setting mode -> `BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN`), max `10` `.DAT` files (`CAMSET01.DAT .. CAMSET10.DAT`, machine-bound `WB Custom 1/2/3`, `FTP`, streaming, IP/TLS certs, and clock stripped -> `BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED`);
     3. Asymmetric dual-media root split (`SD / SDHC / SDXC`: `/PRIVATE/SONY/SETTING/FX3/CAMSET/` vs `CFexpress Type A`: `/SONY/SETTING/FX3/CAMSET/` -> `BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH`), cross-model (`ILME-FX3` vs `ILME-FX3A` vs `ILME-FX6`) `.DAT` header rejection (`BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED`), and Stage-B `/tmp/fx6_camset_overlay` sandboxing with `H0 == H3` invariance (`BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT`).
2. **`VMC-BNCM1` (`A-5051-506-A`) Body-Only `TC IN` (`EXT-LK`), `XLR-H1` Handle Micro-USB Block & Digital HDMI-Only `TC OUT` Guard (`verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard`, Gate `G72`)**:
   - Enforces:
     1. Fail-closed block on plugging `VMC-BNCM1` (`0.2m`) into the `XLR-H1` handle unit's side Micro-USB port (`BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN`), permitting `VMC-BNCM1` strictly on the camera body `Multi/Micro USB` port;
     2. Unidirectional `TC IN` enforcement blocking reverse LTC/BNC `TC OUT` drive on `Multi/Micro USB` and requiring Stage-B `FX6` BNC `TC OUT` masking (`EOPNOTSUPP` -> `BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN`);
     3. External timecode lock (`EXT-LK`) physics requiring `[Movie]` + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]` + `>= 10.0s` continuous LTC sync, with immediate lock release on `S&Q` entry or `TC Make/Run/Preset` change (`BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED`);
     4. Digital Type-A HDMI-only `TC OUT` (`[HDMI Output Settings] -> [Time Code Output] = [On]`, auto-disabled in `S&Q` -> `BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION`).
3. **72-Gate Master Preflight (`run_72_gate_preflight` / `evaluate_72gate_preflight`) & Phase 201 CLI Subcommands**:
   - **Offline default mode**: `69/72` gates pass (`G01..G09`, `G13..G72` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `72/72` simulation gates pass (`dry_run_rehearsal_only = True`) while `human_hardware_attach_token = False`, `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g71-big6-noend-camset-slot1 [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g72-vmcbncm1-tcin-hdmi-tcout [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-72-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 37. Phase 206 Real-Hardware Main Track Part 24: `ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x=1.65x` 4-Locks / HDMI RAW Bypass) & External `M&C Focus Map` (`>=150fps` Cutoff) Guard (`Gate G73`), `[Simult. + Auto Switch]` Parity & `[Shockless WB]` Immediate-Bypass Guard (`Gate G74`), and 74-Gate Master Preflight (`realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py`)

`realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py` (`fx3-realhw-desqueeze-focusmap-simult-shocklesswb-74gate-preflight-v1`) composes `realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.py` (`G01..G72`, keeping `verify-58-gates` through `verify-72-gates` 100% intact) with two Wave-27 real-hardware safety gates **`G73`** and **`G74`** into the **74-Gate Master Safety Preflight (`G01..G74` / `run_74_gate_preflight` / `evaluate_74gate_preflight`)**, keeping `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`, `HUMAN_HARDWARE_ATTACH_TOKEN = False`, `overall_ready_for_hardware_attach = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` hard-locked:

1. **`ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`Off / 1.3x / 2.0x / 1.5x / 1.6x=1.65x`) 4-Setting Lock & External-Only `M&C Focus Map` (`>=150fps` Cutoff) Guard (`verify_fx3_desqueeze_4locks_and_external_focusmap_guard`, Gate `G73`)**:
   - Inspects FX3 `7.02` `cpapp-b.bin` (`15,980,568 B`), `libSaveLoadSettings.so` (`18,760 B`), `FX3-CX95900_ALLLANG-Backup.bin` (`2,229,740 B`), and FX6 `6.01` `CX95898_NTSC.bin` (`2,253,333 B`) strictly via `os.open(..., os.O_RDONLY)` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` clean-room fallback and zero raw Sony firmware bytes in JSON output.
   - Enforces:
     1. Exact `[De-Squeeze Display]` horizontal stretch mapping (`Off -> 1.0x`, `1.3x -> 1.3x`, `2.0x -> 2.0x`, and `Ver. 7.00+` `1.5x -> 1.5x` & `1.6x -> 1.65x` CinemaScope `2.39:1` horizontal restoration -> `BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH`);
     2. Exact 4-setting lock whenever `[De-Squeeze Display] != Off` (`[Focus Mode] = Manual Focus`, `[Focus Area] = Wide`, `[SteadyShot] = Off`, `[Face Priority in Multi Metering] = Off` -> `BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION`);
     3. Automatic de-squeeze suppression to `1.0x` unscaled monitoring under `[RAW Output] = On`, `[Rec. Media dur HDMI Output] = Off(HDMI Only)` (forcing `[HDMI Info. Display] = Off`), `[Log Shooting] = Off`, `[Remote Shooting]`, or `Still` mode, with zero recorded-essence or `4264x2408` linear HDMI RAW pixel stretch (`BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION`);
     4. Hard fail-closed rejection of non-existent in-body `ILME-FX3` `[Focus Map]` menu items or Stage-B local LCD/HDMI Focus Map overlays (`BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN`), plus external `Monitor & Control` (`M&C`) PDAF `Focus Map` cutoffs (`>= 150 fps`, non-PDAF / mount-adapter / missing lens, or camera Playback -> `BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION`).
2. **Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]` (`Ver. 2.00+` Single-Card Fallback vs `Off` Strict Dual-Vault Parity) & `[Shockless WB]` Immediate-Bypass Guard (`verify_simult_autoswitch_parity_and_shockless_wb_guard`, Gate `G74`)**:
   - Enforces:
     1. `[Auto Switch Media] = Off` whenever strict dual-card cold-vault / redundant parity is required, preventing `Ver. 2.00+` `[Simult. Recording]` + `[Auto Switch Media] = On` from silently degrading to single-card recording when one slot fills (`BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF`, `BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD`, `BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH`);
     2. `[Shockless WB]` (`Off / 1 / 2 / 3`) validation across full `1..240 fps` (`23.98p..120p` and `S&Q` up to `240fps` -> `BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID`), with immediate `0`-frame smoothing bypass on `[C.Temp./Filter]` Kelvin (`2500K..9900K`) edits and `A-B / G-M` fine-tuning grid shifts (`BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION`).
3. **74-Gate Master Preflight (`run_74_gate_preflight` / `evaluate_74gate_preflight`) & Phase 206 CLI Subcommands**:
   - **Offline default mode**: `71/74` gates pass (`G01..G09`, `G13..G74` pass; physical Tier-0 `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--dry-run-simulated` rehearsal mode**: `74/74` simulation gates pass (`dry_run_rehearsal_only = True`) while `human_hardware_attach_token = False`, `overall_ready_for_hardware_attach = False`, `el3_payload_transmit_authorized = False`, `spi_nor_write_authorized = False`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `physical_usb_packets_emitted = 0`, and `raw_firmware_bytes_leaked = 0` remain hard-locked.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g73-desqueeze-focusmap [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g74-simult-autoswitch-shocklesswb [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-74-gates [--force-clean-room] [--dry-run-simulated] [--json]
```

---

## 38. Phase 210 Real-Hardware Main Track Part 25: `ILME-FX3` (`Ver. 7.02`) `[HDMI Output Settings]` Log/PPLUT `1080p` Downshift & `[Off(HDMI Only)]` 4K / Blank-LCD Guard (`Gate G75`), `[Proxy Settings]` Coupled `CLIP+SUB` Vault & `[Focus Magnifier]` / `[Bright Monitoring]` Interlock Guard (`Gate G76`), and Unified 76-Gate Master Preflight (`realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py`)

`realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py` (`fx3-realhw-hdmi-log1080-proxy-focusmag-brightmon-76gate-preflight-v1`) delegates `G01..G74` directly to `evaluate_74gate_preflight()` (`keeping verify-58-gates` through `verify-74-gates` 100% intact) and adds Wave-28 real-hardware safety gates **`G75`** and **`G76`** into the unified **76-Gate Master Safety Preflight (`G01..G76` / `run_76_gate_preflight` / `evaluate_76gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[HDMI Output Settings]` Log/PPLUT `1080p` Downshift, `[Off(HDMI Only)]` 4K Zero-Card-Rec & Camera LCD Blanking Guard (`verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard`, Gate `G75`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `[Rec. Media dur HDMI Output]` (`[On]` vs `[Off(HDMI Only)]`) and `[4K Output Set.(HDMI Only)]` (`59.94p 10bit`, `50p 10bit`, `29.97p 10bit`, `25p 10bit`, `23.98p 10bit`, `24.00p 10bit`), `[Log Shooting]` (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) and `PPLUT1..PPLUT4` `1080p` HDMI downshift when `[Rec. Media dur HDMI Output] = [On]` & `[RAW Output] = [Off]`, `[Off(HDMI Only)]` zero-internal-card-recording lockout, automatic `[HDMI Info. Display] -> [Off]` & HDMI `[De-Squeeze Display]` suppression under `[Off(HDMI Only)]` / `[RAW Output] = [On]`, and camera built-in LCD blanking (`camera_lcd_panel_blanked == True`) whenever `[HDMI Info. Display] = [On]`.
2. **`ILME-FX3` (`Ver. 7.02`) `[Proxy Settings]` Exact 2-Format/3-Setting Table, Coupled `M4ROOT/CLIP/` + `M4ROOT/SUB/` Vault Parity & `[Focus Magnifier]` / `[Bright Monitoring]` Interlock Guard (`verify_proxy_coupled_vault_and_focusmag_brightmon_guard`, Gate `G76`)**:
   - Enforces exact FX3 `[Proxy Settings]` (`XAVC HS HD` `1920x1080` 10-bit HEVC `16M`/`9M` `<=59.94p/50p`; `XAVC S HD` `1280x720` 8-bit AVC `6M` `<=59.94p/50p`), blocking `[Proxy Recording]` at Normal `119.88p`/`100p`, S&Q `119.88p`/`100p` or sensor `>=100fps/120fps`, and `[Off(HDMI Only)]`, plus atomic coupled `M4ROOT/CLIP/` + `M4ROOT/SUB/` Delete/Protect parity and on-camera proxy playback exclusion.
   - Enforces `[Initial Focus Mag.]` movie (`x1.0`/`x4.0` only) vs still (`x1.0`/`x2.1` FF, `x1.0`/`x1.5` APS-C/S35), `[Auto Magnifier in MF]` movie lockout, `[Marker Display]` suppression while magnified, and `[Bright Monitoring]` custom-key toggle lockout while magnified plus auto-cancel outside `P/A/S/M` or `MF` (`[Live View Display]` forced to `[Setting Effect OFF]`).
3. **Unified 76-Gate Master Preflight (`evaluate_76gate_preflight` / `verify-76-gates`)**:
   - **Offline default mode**: `73/76` gates pass (`G01..G09`, `G13..G76` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `76/76` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g75-hdmi-log1080-hdmionly [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g76-proxy-focusmag-brightmon [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-76-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 39. Phase 214 Real-Hardware Main Track Part 26: `ILME-FX3` (`Ver. 7.02`) `[File Settings]` 5-Mode / 37-Char Title / SDHC `[Standard]` Lock & `[Shot Mark]` `*M01.XML` / Transfer Filter Guard (`Gate G77`), `[TC/UB]` `[Regenerate]` Slot-1 Master / `VMC-BNCM1` `EXT-LK` Release & `[REC Lamp]` Coupled Tally Guard (`Gate G78`), and Unified 78-Gate Master Preflight (`realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py`)

`realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py` (`fx3-realhw-filesettings-shotmark-tcregen-reclamp-78gate-preflight-v1`) delegates `G01..G76` directly to `evaluate_76gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-76-gates`) and adds Wave-29 real-hardware safety gates **`G77`** and **`G78`** into the unified **78-Gate Master Safety Preflight (`G01..G78` / `run_78_gate_preflight` / `evaluate_78gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[File Settings]` 5-Mode `[File Name Format]`, 37-Char ASCII `[Title Name Settings]`, SDHC `[Standard]` Lock & `[Shot Mark]` `*M01.XML` / Transfer Filter Guard (`verify_file_settings_sdhc_37char_and_shotmark_guard`, Gate `G77`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces all 5 `[File Name Format]` modes (`Standard`, `Cam ID + Reel#`, `Title`, `Date + Title`, `Title + Date`) uniformly across Slot 1 & Slot 2, `[File Number]` (`Series` / `Reset` + `Series Counter Reset`), `[Title Name Settings]` max `37` characters and exact allowed ASCII character set (`A-Za-z0-9` + `.-_@!#$%+=^~(),;[]`, forward-only for subsequent clips), SDHC card (`<=32GB` FAT32) forced lock to `[Standard]`, and custom movie folder prohibition (`M4ROOT/CLIP/` only).
   - Enforces `[Shot Mark]` (`Add Shot Mark1/2` during Rec, `Add/Delete Shot Mark1/2` during Playback) `M4ROOT/CLIP/*M01.XML` non-real-time metadata sidecar persistence (zero MP4 essence mutation, unavailable in Still mode), `[Image Jump Setting]` (`Shot Mark Only` / `Shot Mark1 Only` / `Shot Mark2 Only` / `No Shot Mark`), and `[Only Shot Mark Mov.]` / `[Only Shot Mark]` FTP & Smartphone transfer filter semantics.
2. **`ILME-FX3` (`Ver. 7.02`) `[TC/UB]` `[Regenerate]` Forced `[Rec Run]` & Exclusive Slot-1 Read, `VMC-BNCM1` `EXT-LK` Release, S&Q Lockout, 3-State Coupled `[REC Lamp]` & `[Silent Mode]` Audio-Signals Lock Guard (`verify_tc_regenerate_extlk_and_reclamp_tally_guard`, Gate `G78`)**:
   - Enforces `[TC/UB]` `[Time Code Make] = [Regenerate]` forcing `[Rec Run]` advancement regardless of `[Time Code Run]` and reading the last recorded timecode exclusively from **Slot 1** under `[Simult. Recording]`.
   - Enforces `VMC-BNCM1` `EXT-LK` prerequisite (`Movie` mode + `[Preset]` + `[Free Run]`) and immediate `EXT-LK` release upon switching `[Time Code Make]` (e.g. to `Regenerate`) or `[Time Code Run]`, plus `S&Q` lockout of `[Time Code Run]` and HDMI `[Time Code Output]`.
   - Enforces FX3 `[REC Lamp]` 3-state hardware coupling (`All On`, `Only Front Off` keeping **both** rear lamp and top `REC` button LED lit, `All Off` with independent `[Emphasized REC Display]` HDMI red frame when `[HDMI Info. Display] = [On]`) and `[Silent Mode] = [On] -> [Audio signals] = [Off]` hard lock.
3. **Unified 78-Gate Master Preflight (`evaluate_78gate_preflight` / `verify-78-gates`)**:
   - **Offline default mode**: `75/78` gates pass (`G01..G09`, `G13..G78` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `78/78` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g77-filesettings-shotmark [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g78-tcregen-reclamp [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-78-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 40. Phase 219 (`80/80` Milestone) Real-Hardware Main Track Part 27: `ILME-FX3` (`Ver. 7.02`) `[Auto Pixel Mapping]` / `[Pixel Mapping]` Mandatory Reboot, Low-Battery Lockout & `cnflasha` Read-Only Firewall (`Gate G79`), `[NTSC/PAL Selector]` Reset Persistence & `[Gamma Display Assist]` / `[Display LUT]` Split Guard (`Gate G80`), and Unified 80-Gate Master Preflight (`realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py`)

`realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py` (`fx3-realhw-pixelmap-ntscpal-gammaassist-displaylut-80gate-preflight-v1`) delegates `G01..G78` directly to `evaluate_78gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-78-gates`) and adds Wave-30 milestone real-hardware safety gates **`G79`** and **`G80`** into the unified **80-Gate Milestone Master Safety Preflight (`G01..G80` / `run_80_gate_preflight` / `evaluate_80gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Auto Pixel Mapping]` / `[Pixel Mapping]` Low-Battery Lockout, Operator-Control Lockout, Mandatory Camera Reboot & `cnflasha` Read-Only Firewall (`verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard`, Gate `G79`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Models `[Auto Pixel Mapping]` (`MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]`, `On` default, mechanical shutter actuation sound at power-off even when `[Silent Mode] = [On]`, and `<= 3`-day manual `[Pixel Mapping]` cadence guidance when `Off`).
   - Enforces manual `[Pixel Mapping]` (`MENU -> Setup -> [Setup Option] -> [Pixel Mapping]`) low-battery lockout (`< 20%` SoC or low-battery warning active), complete operator-control lockout during execution, mandatory **automatic camera restart** upon completion (unmounting volatile Stage-B `/tmp` RAM bind-mounts cleanly back to stock `FX3 Ver. 7.02` `H0 == H2`), and absolute `cnflasha` factory calibration read-only firewall (`cnflasha_userspace_write_blocked == True`, `persistent_emmc_writes_authorized == False`).
2. **`ILME-FX3` (`Ver. 7.02`) `[NTSC/PAL Selector]` Exclusive Matrix & Reset Persistence Asymmetry + `[Gamma Display Assist]` vs `[Log Shooting]` `[Display LUT]` Split & Built-in-LCD Scope Guard (`verify_ntscpal_persistence_and_gamma_assist_displaylut_guard`, Gate `G80`)**:
   - Enforces `[NTSC/PAL Selector]` exclusive frame-rate & timecode matrix (`NTSC`: `23.98p` NTSC-exclusive, `24.00p`, `29.97p`, `59.94p`, `119.88p` + `[TC Format]` `DF`/`NDF`; `PAL`: `25p`, `50p`, `100p`, with `23.98p` and `[TC Format]` `DF`/`NDF` blocked), startup `"Running on NTSC."` / `"Running on PAL."` notification banner when non-default, and `[Camera Settings Reset]` persistence (only `[Initialize]` resets `[NTSC/PAL Selector]`).
   - Enforces `[Gamma Display Assist]` (`[Gamma Disp. Assist Typ.]`: `Auto`, `S-Log3->709(800%)`, `HLG(BT.2020)`, `HLG(709)` — zero `S-Log2` in `Ver. 7.02`) hard lock to `[Off]` whenever `[Log Shooting]` (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) is active (where `[Display LUT]` `On`/`Off` governs preview), and enforces built-in-LCD-only scope (`external_hdmi_gamma_assist_applied == False`).
3. **Unified `80/80` Milestone 80-Gate Master Preflight (`evaluate_80gate_preflight` / `verify-80-gates`)**:
   - **Offline default mode**: `77/80` gates pass (`G01..G09`, `G13..G80` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `80/80` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g79-pixelmap-cnflasha [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g80-ntscpal-gammaassist-displaylut [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-80-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 41. Phase 224 Real-Hardware Main Track Part 28: `ILME-FX3` (`Ver. 7.02`) `[SteadyShot]` `[Active]` RAW/HFR Cutoff & `[Clear Image Zoom]` / `[Digital Zoom]` 4-Locks Guard (`Gate G81`), `[Power Save Start Time]` 9-Condition Bypass / Air-Gapped Tier-0 Pre-Check & `[Auto Power OFF Temp.]` Tripod Guard (`Gate G82`), and Unified 82-Gate Master Preflight (`realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py`)

`realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py` (`fx3-realhw-steadyshot-ciz-powersave-autotemp-82gate-preflight-v1`) delegates `G01..G80` directly to `evaluate_80gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-80-gates`) and adds Wave-31 real-hardware safety gates **`G81`** and **`G82`** into the unified **82-Gate Master Safety Preflight (`G01..G82` / `run_82_gate_preflight` / `evaluate_82gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[SteadyShot]` `[Active]` 3-Condition Disqualification & Narrower AoV Crop + `[Clear Image Zoom]` / `[Digital Zoom]` RAW/HFR Cutoff & 4 Mandatory State Locks Guard (`verify_steadyshot_active_cutoff_and_ciz_4lock_guard`, Gate `G81`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Models movie `[SteadyShot]` (`Active` narrower angle-of-view crop `~1.1x` vs `Standard` / `Off`), enforcing all 3 `[Active]` disqualification conditions: Normal movie `119.88p`/`100p`, `S&Q` `[Frame Rate]` `>=120fps`/`100fps` (`100fps`/`120fps`/`200fps`/`240fps`), and external HDMI `[RAW Output] = [On]`, plus manual `[SteadyShot Focal Len.]` (`8mm..1000mm`) validation.
   - Models `[Clear Image Zoom]` / `[Digital Zoom]` (`[Zoom Range]`): blocks non-optical zoom when still `[File Format]` is `RAW` / `RAW & JPEG` / `RAW & HEIF`, Normal movie `119.88p`/`100p`, or `S&Q` `120fps/100fps`/`240fps/200fps`, and enforces all 4 automatic camera state locks whenever non-optical zoom is active: `[Focus Area]` disabled (center-priority AF), `[Metering Mode]` hard-locked to `[Multi]`, `[Face/Eye Prior. in AF]` & `[Face Priority in Multi Metering]` disabled, and `Real-time Tracking` unavailable.
2. **`ILME-FX3` (`Ver. 7.02`) `[Power Save Start Time]` Exact Menu Item, 9 Automatic Deactivation Conditions, Air-Gapped `NP-FZ100` Tier-0 `75 MiB` `p3` Dump Pre-Check & `[Auto Power OFF Temp.]` `[High]` Tripod / `[Fan Control]` Thermal Guard (`verify_powersave_9cond_and_autotemp_tripod_guard`, Gate `G82`)**:
   - Enforces exact `ILME-FX3` menu item `[Power Save Start Time]` (`MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]`, default `5 Min`; options `Off`, `30 Min`, `5 Min`, `2 Min`, `1 Min`, `10 Sec`) and its 9 automatic sleep-deactivation conditions (USB power supply, slideshow playback, FTP transfer, movie recording, PC connection, TV/HDMI connection, `[IR Remote Ctrl] = [On]`, `[Bluetooth Rmt Ctrl] = [On]`, streaming / Creators' Cloud upload), plus air-gapped internal-battery (`NP-FZ100` without USB/HDMI/FTP/Remote/PC/Streaming) Tier-0 `75 MiB` `p3` dump pre-check requiring `[Power Save Start Time]` = `Off` or `30 Min`.
   - Enforces `[Auto Power OFF Temp.]` (`Standard` default vs `High`): requires `tripod_mounted == True` whenever `[Auto Power OFF Temp.] = [High]` (blocking prolonged hand-held low-temperature contact burn hazard) and couples with `[Fan Control]` thermal safety (`Always Off` forbidden under `High`, `>=62.0C` override / `>=90.0C` fail-closed ceiling enforced).
3. **Unified 82-Gate Master Preflight (`evaluate_82gate_preflight` / `verify-82-gates`)**:
   - **Offline default mode**: `79/82` gates pass (`G01..G09`, `G13..G82` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `82/82` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g81-steadyshot-ciz [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g82-powersave-autotemp [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-82-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 42. Phase 228 Real-Hardware Main Track Part 29: `ILME-FX3` (`Ver. 7.02`) `[Mode Settings]` (`[Fixed/Variable]`) S&Q 6-Lock Matrix & `[Zebra Display]` / `[Peaking Display]` HDMI Clean-Feed Guard (`Gate G83`), `[Zebra Display]` Reset Survival & `[Format]` (`Quick` / `Full` / `MENU+Delete` 2s Chord) Tier-0 Vault Guard (`Gate G84`), and Unified 84-Gate Master Preflight (`realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py`)

`realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py` (`fx3-realhw-sq-fixedvar-zebra-peaking-fullformat-84gate-preflight-v1`) delegates `G01..G82` directly to `evaluate_82gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-82-gates`) and adds Wave-32 real-hardware safety gates **`G83`** and **`G84`** into the unified **84-Gate Master Safety Preflight (`G01..G84` / `run_84_gate_preflight` / `evaluate_84gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Mode Settings] = [Fixed/Variable]` Legacy `[S&Q Settings]` Lockout, 6-Lock S&Q Disqualification Matrix & `[Zebra Display]` / `[Peaking Display]` Local-LCD-Only HDMI Clean-Feed Guard (`verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard`, Gate `G83`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `Ver. 7.00+` / `7.02` `[Mode Settings] = [Fixed/Variable]` (`MENU -> Shooting -> [Shooting Mode] -> [Shoot Mode] -> [S&Q(Slow&Quick Motion)] -> [Mode Settings]`), locking legacy `MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]` in favor of direct `[FPS]` (`Home (FPS)`) capture frame-rate control while codec/bit-rate follow `[Movie Settings]` & `[File Format]`.
   - Enforces all 6 official `ILME-FX3` S&Q disqualifications: (1) `0ch` no sound recorded, (2) `[Audio Out Timing]` (`Live` default zero-delay vs `Lip Sync` video-aligned) disabled in S&Q, (3) `[Time Code Run]` & HDMI `[Time Code Output]` unavailable in S&Q, (4) `240fps`/`200fps` blocked on `XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`, and `XAVC S-I DCI 4K` (requires `XAVC S HD` / `XAVC S-I HD`), (5) `120fps`/`100fps` blocked on `XAVC S-I DCI 4K` (`4096x2160`), and (6) `[Proxy Recording]` blocked in S&Q when `Rec Frame Rate` is `119.88p`/`100p` OR `Frame Rate >= 120fps`/`100fps`.
   - Enforces hardware HDMI assist-overlay suppression: neither `[Zebra Display]` stripes nor `[Peaking Display]` (`On`/`Off`, `High`/`Mid`/`Low`, `Red`/`Yellow`/`Blue`/`White`, Control Wheel Right `[Peaking Display Select]`) outlines are ever output over HDMI even when `[HDMI Info. Display] = [On]`.
2. **`ILME-FX3` (`Ver. 7.02`) `[Zebra Display]` / `[Zebra Level]` `[Camera Settings Reset]` Survival & Slot-1 `[Format]` (`Quick` / `(Delete)` `Full` / `MENU+Delete` 2s Chord) Tier-0 Vault Lockout Guard (`verify_zebra_reset_survival_and_fullformat_chord_vault_guard`, Gate `G84`)**:
   - Verifies `[Zebra Display]` (`Off`/`On`, Control Wheel Left default `[Zebra Display Select]`) and `[Zebra Level]` (`70..100+`, `Custom 1` Standard+Range exposure band, `Custom 2` Minimum/Lower-Limit overexposure threshold) survive `[Camera Settings Reset]` and are cleared back to factory `Off` / `70` exclusively by `[Initialize]`.
   - Enforces hard-lock on Slot 1 `[Format]` — covering `[Enter]` **Quick Format** (metadata-only), `(Delete)`-toggled **Full Format** (all data blocks + metadata, plus mid-cancel data-already-erased / card-remains-usable semantics), and the physical **`MENU + (Delete)` (`~2s`) shooting-screen chord** — whenever Slot 1 holds an unverified or active Tier-0 recovery vault (`pnflasha` / `cnflasha` / `CAMSET01.DAT`).
3. **Unified 84-Gate Master Preflight (`evaluate_84gate_preflight` / `verify-84-gates`)**:
   - **Offline default mode**: `81/84` gates pass (`G01..G09`, `G13..G84` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `84/84` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g83-sq-fixedvar-zebra-peaking [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g84-zebra-reset-fullformat-chord [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-84-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 43. Phase 230 Real-Hardware Main Track Part 30: `ILME-FX3` (`Ver. 7.02`) `[Silent Mode Settings]` `[Auto Pixel Mapping]` Suppression Target, 5-Function Lockout & Hardware `[Shutter When Pwr OFF]` Absence Guard (`Gate G85`), `[Marker Display]` 15-Ratio Non-Resettable Persistence, Local-LCD-Only HDMI Isolation & `[Flexible Exp. Mode]` Reset Split Guard (`Gate G86`), and Unified 86-Gate Master Preflight (`realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py`)

`realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.py` (`fx3-realhw-silent-autopixelmap-marker-flexexp-86gate-v1`) delegates `G01..G84` directly to `evaluate_84gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-84-gates`) and adds Wave-33 real-hardware safety gates **`G85`** and **`G86`** into the unified **86-Gate Master Safety Preflight (`G01..G86` / `run_86_gate_preflight` / `evaluate_86gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Silent Mode Settings]` `[Auto Pixel Mapping]` Suppression Target, 5-Function Lockout & Hardware `[Shutter When Pwr OFF]` Absence Guard (`verify_silent_mode_autopixelmap_and_no_pwrshutter_guard`, Gate `G85`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `[Silent Mode] = [On]` (`MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`): automatically locks `[Shutter Type]` & `[Shutter Type in Interval]` to `[Electronic Shutter]`, locks `[Audio signals]` to `[Off]`, and disables all 5 shooting functions (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`).
   - Enforces `[Target Function Settings]` targeting `[Aperture Drive in AF]` (`Not Target` / `Standard` / `Focus Priority` / `Silent Priority`) and `[Auto Pixel Mapping]` (`Off` / `Not Target`): selecting `[Not Target]` retains normal behavior, whereas targeting `[Auto Pixel Mapping]` (`Off`) deterministically suppresses power-off mechanical shutter dark-frame actuation and prevents unscheduled `cnflasha` calibration touches during controlled bench shutdowns.
   - Rejects any fabricated `[Shutter When Pwr OFF]` menu or target assertion fail-closed on physical `ILME-FX3` (`Ver. 2.00..7.02` exposes only `[Sensor Cleaning]`, `[Auto Pixel Mapping]`, and `[Pixel Mapping]` in `Setup`).
2. **`ILME-FX3` (`Ver. 7.02`) `[Marker Display]` 15-Ratio Non-Resettable Persistence, Local-LCD-Only HDMI Isolation & `[Flexible Exp. Mode]` `Av`/`Tv`/`ISO` + `[Auto Slow Shutter]` Reset Split Guard (`verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard`, Gate `G86`)**:
   - Enforces `[Marker Display]` (`MENU -> Shooting -> [Marker Display]`: `[Center Marker]` `Off/On`, `[Aspect Marker]` `Off` + all 15 `Ver. 3.00+/7.02` ratios `9:16`, `4:5`, `1:1`, `4:3`, `13:9`, `14:9`, `15:9`, `16:9` [`Ver. 3.00+`], `17:9`, `1.66:1`, `1.85:1`, `1.91:1`, `2:1`, `2.35:1`, `2.39:1`, `[Safety Zone]` `Off/80%/90%`, `[Guideframe]` `Off/On`) local-monitor-only HDMI isolation (`0` external HDMI marker output even when `[HDMI Info. Display] = [On]`) and survival across `[Camera Settings Reset]` (cleared back to factory `Off` exclusively by `[Initialize]`).
   - Enforces `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`) reset split: `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO` all factory-default `Manual`) and `[Auto Slow Shutter]` (factory-default `On`) **are reset** by `[Camera Settings Reset]`, directly contrasting with non-resettable `[Marker Display]` / `[Aspect Marker]`.
3. **Unified 86-Gate Master Preflight (`evaluate_86gate_preflight` / `verify-86-gates`)**:
   - **Offline default mode**: `83/86` gates pass (`G01..G09`, `G13..G86` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `86/86` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g85-silent-autopixelmap-no-pwrshutter [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g86-marker-hdmi-flexexp-reset [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-86-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 44. Phase 235 Real-Hardware Main Track Part 31: `ILME-FX3` (`Ver. 7.02`) `[Recover Image DB]` Depleted-Battery Refusal, Non-Deleting Repair & Unverified Slot-1 Tier-0 Vault Read-Only Mutation Firewall (`Gate G87`), `[Monitor Flip Direction]` Reset Survival + `[Horizontal Flip]` Playback Non-Inversion & `[AF Subj. Shift Sensitivity]` / `[Interval Shoot Func.]` Still-Only Boundary (`Gate G88`), and Unified 88-Gate Master Preflight (`realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py`)

`realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.py` (`fx3-realhw-recover-imagedb-monitor-flip-af-sens-88gate-v1`) delegates `G01..G86` directly to `evaluate_86gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-86-gates`) and adds Wave-34 real-hardware safety gates **`G87`** and **`G88`** into the unified **88-Gate Master Safety Preflight (`G01..G88` / `run_88_gate_preflight` / `evaluate_88gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Recover Image DB]` Depleted-Battery Refusal, Non-Deleting Repair & Unverified Slot-1 Tier-0 Vault Read-Only Mutation Firewall (`verify_recover_imagedb_depleted_battery_and_tier0_vault_guard`, Gate `G87`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Media] -> [Recover Image DB]` repairing `AVF_INFO` / media management DB inconsistencies (`"Image DataBase File error"`, false `"0"` recordable images, or PC-edited media index divergence) **without deleting any recorded clips or stills** (`recorded_clips_deleted == 0`, `recorded_clips_after == recorded_clips_before`), refusing execution whenever the `NP-FZ100` battery pack is extremely depleted (`< 10%` or `< 6400 mV` or `battery_extremely_depleted == True`), and remaining immune to both `[Camera Settings Reset]` and `[Initialize]`.
   - Enforces a strict **Slot-1 Tier-0 Vault Read-Only Mutation Firewall**: because `[Recover Image DB]` writes repaired index files onto the target memory card, any `[Recover Image DB]` execution or metadata write on Slot 1 (`slot1_metadata_sector_writes == 0`, `slot1_avf_info_mutated == False`) is hard-blocked whenever an active, unverified (`slot1_off_camera_sha256_verified == False`), or `WP`-locked Tier-0 dump card (`pnflasha` / `cnflasha` / `CAMSET01.DAT`) is inserted in Slot 1 prior to off-camera SHA-256 verification.
2. **`ILME-FX3` (`Ver. 7.02`) `[Monitor Flip Direction]` `[Camera Settings Reset]` Survival + `[Horizontal Flip]` Playback Non-Inversion & `[AF Subj. Shift Sensitivity]` / `[AF Transition Speed]` + `[Interval Shoot Func.]` Still-Only Boundary (`verify_monitor_flip_playback_af_sens_and_interval_guard`, Gate `G88`)**:
   - Enforces `MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]` (`Auto` factory default, `Horizontal Flip`, `Vertical Flip`, `Off`) surviving `[Camera Settings Reset]` (restored to `Auto` exclusively by `[Initialize]`) and **not inverting monitor display direction during playback** (`playback_monitor_horizontally_inverted == False`) even when set to `[Horizontal Flip]` (which mirrors live shooting view).
   - Enforces exact full `ILME-FX3` menu string `[AF Subj. Shift Sensitivity]` (`1(Locked on)..5(Responsive)`, default `5(Responsive)`, rejecting abbreviated `"AF Subj. Shift Sens."`) and `[AF Transition Speed]` (`1(Slow)..7(Fast)`, default `5`) Movie/S&Q resettable semantics (both reset by `[Camera Settings Reset]`, directly contrasting with non-resettable `[Monitor Flip Direction]`), plus `[Interval Shoot Func.]` (`1s..99m59s` start delay, `1s..60s` interval, `1..9999` shots) still-image-only capture scope (`JPEG`/`HEIF`/`RAW`, post-assembled via `Imaging Edge Desktop (Viewer)`, rejecting false in-camera `.MP4`/`.MXF` interval video claims on `ILME-FX3`).
3. **Unified 88-Gate Master Preflight (`evaluate_88gate_preflight` / `verify-88-gates`)**:
   - **Offline default mode**: `85/88` gates pass (`G01..G09`, `G13..G88` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `88/88` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g87-recover-imagedb-battery-vault [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g88-monitor-flip-af-sens-interval [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-88-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 45. Phase 237 (`90/90` Milestone) Real-Hardware Main Track Part 32: `ILME-FX3` (`Ver. 7.02`) `[Emphasized REC Display]` & `[Grid Line]` HDMI Info Routing vs Forced `[Off(HDMI Only)]`/`RAW` Clean-Feed Suppression (`Gate G89`), `[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival + Bench Accidental-Tap Lock & `[Monitor Brightness]` `Manual` vs `Sunny Weather` Indoor Guard (`Gate G90`), and Unified 90-Gate Master Preflight (`realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py`)

`realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.py` (`fx3-realhw-emphasized-rec-grid-hdmi-touch-sunny-90gate-v1`) delegates `G01..G88` directly to `evaluate_88gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-88-gates`) and adds Wave-35 real-hardware milestone safety gates **`G89`** and **`G90`** into the unified **`90/90` Milestone Master Safety Preflight (`G01..G90` / `run_90_gate_preflight` / `evaluate_90gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Emphasized REC Display]` & `[Grid Line]` HDMI Info Routing vs Forced `[Off(HDMI Only)]` / `RAW` Clean-Feed Suppression (`verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard`, Gate `G89`)**:
   - Performs a bounded `< 0.15s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]` (`On` factory default on `ILME-FX3`, bold red border during Movie and `S&Q` recording, **resettable** via `[Camera Settings Reset]`) versus `[Grid Line Display]` (`Off` factory default) and `[Grid Line Type]` (`Rule of 3rds Grid` default, `Square Grid`, `Diag. + Square Grid` — **NOT reset** by `[Camera Settings Reset]`, cleared exclusively by `[Initialize]`), plus external HDMI routing when effective `[HDMI Info. Display] = [On]` (blanking the built-in camera LCD), contrasting directly with strictly local-LCD-only `[Marker Display]`, `[Zebra Display]`, and `[Peaking Display]`.
   - Enforces the **2 automatic hardware clean-feed clamps**: whenever `[Rec. Media dur HDMI Output]` = `[Off(HDMI Only)]` OR HDMI `RAW` movie output (`[RAW Output] = [On]`) is active, `[HDMI Info. Display]` is temporarily forced to `[Off]`, guaranteeing `0` red REC border, `0` grid lines, and `0` status OSD pixels (`hdmi_baked_overlay_pixels == 0`) are baked into external HDMI recorder streams.
2. **`ILME-FX3` (`Ver. 7.02`) `[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival + Bench Accidental-Tap Lock & `[Monitor Brightness]` `Manual` `-2..+2` vs `Sunny Weather` Indoor Guard (`verify_touch_op_reset_and_sunny_weather_bench_guard`, Gate `G90`)**:
   - Enforces all 4 `MENU -> Setup -> [Touch Operation]` settings (`[Touch Operation]` `On`/`On: Playback Only`/`Off`, `[Touch Sensitivity]` `Standard`/`Sensitive`, `[Swipe Up]` `Open the Fn Menu`/`Off`, `[Touch Func. in Shooting]` `Touch Tracking`/`Touch Focus`/`Off`) surviving `[Camera Settings Reset]` (restored exclusively by `[Initialize]`), and requires `[Touch Operation]` in `("Off", "On: Playback Only")` during unattended Tier-0 vault bench runs so accidental capacitive taps cannot trigger `Fn` swipe or shooting tracking/focus.
   - Enforces `MENU -> Setup -> [Monitor] -> [Monitor Brightness]` (`Manual` `-2..+2` default `0` vs `Sunny Weather`) surviving `[Camera Settings Reset]` and blocking `[Sunny Weather]` during indoor `NP-FZ100` bench runs (preventing indoor visual exposure misjudgment and excess LCD backlight thermal/power draw).
3. **Unified `90/90` Milestone Master Preflight (`evaluate_90gate_preflight` / `verify-90-gates`)**:
   - **Offline default mode**: `87/90` gates pass (`G01..G09`, `G13..G90` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `90/90` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g89-emphasized-rec-grid-hdmi [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-g90-touch-op-sunny-weather [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-90-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 46. Phase 241 Real-Hardware Main Track Part 33: `ILME-FX3` (`Ver. 7.02`) `[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter/Routing Guard & `[Wind Noise Reduct.]` Built-In-Mic-Only Boundary (`Gate G91`), `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Firewall & Slot-1 Tier-0 Vault Write Guard (`Gate G92`), and Unified 92-Gate Master Preflight (`realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py`)

`realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.py` (`realhw_shoe_audio_wind_saveload_c3_and_92gate_guard_v1`) delegates `G01..G90` directly to `evaluate_90gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-90-gates`) and adds Wave-36 real-hardware safety gates **`G91`** and **`G92`** into the unified **`92`-Gate Master Safety Preflight (`G01..G92` / `run_92_gate_preflight` / `evaluate_92gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter/Routing Guard & `[Wind Noise Reduct.]` Built-In-Mic-Only Boundary (`verify_shoe_audio_4ch_and_wind_noise_guard`, Gate `G91`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]` (`48kHz/16bit 2ch` factory default, `48kHz/24bit 2ch`, `48kHz/24bit 4ch` — **resettable** via `[Camera Settings Reset]`): automatic `4ch` (`CH1..CH4`) `[Audio Level Display]` meter expansion when `48kHz/24bit 4ch` is active with a digital MI Shoe `4ch` accessory (`XLR-H1` in `DIGITAL` mode or `ECM-M1`), plus deterministic lockout/override across all **3 disqualifying conditions**: (a) `[Audio Recording]=Off` or `S&Q Motion` (`0` audio tracks), (b) body `3.5mm` `MIC` jack plug-in override (`2ch` analog ADC), and (c) `XLR-H1` `[DIGITAL/ANALOG]` slide switch = `[ANALOG]` (`2ch` `48kHz/16bit` fallback).
   - Enforces `MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]` (`Off` factory default / `On`, **resettable** via `[Camera Settings Reset]`): applies exclusively to the camera body's built-in stereo microphone (`external_mic_wind_reduct_effective == False` across `3.5mm` `MIC` and MI Shoe `XLR-H1` inputs; `XLR-H1` uses hardware `LOW CUT` `OFF / 100Hz / 300Hz`), blocks indoor low-wind bench `[On]` low-frequency attenuation hazards, and locks out in `S&Q Motion` / `[Audio Recording]=Off`.
2. **`ILME-FX3` (`Ver. 7.02`) `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Privacy/Calibration Firewall & Slot-1 Tier-0 Vault Write Guard (`verify_saveload_camset_c3_exclusions_and_slot1_vault_guard`, Gate `G92`)**:
   - Enforces `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]` across `Media(Slot 1)` / `Media(Slot 2)` (`/PRIVATE/SONY/PRO/CAMERA/ILME-FX3/CAMSET01.DAT..CAMSET10.DAT`, max `10` per card, strict `ILME-FX3` same-model lock rejecting cross-model `ILME-FX6` `.DAT`) and `Cloud(Private)` / `Cloud(Share)` (`C3 Portal` `Ver. 4.00+` firmware floor).
   - Enforces the Sony Help Guide **Excluded-Items Firewall**: `[Save/Load Settings]` NEVER exports or overwrites `[IPTC Information]`, `[Copyright Info]`, `[Custom White Balance]` (`Custom 1..3`), `[Face Memory]`, or Network credentials (`FTP`, `RTMP/SRT Streaming` keys, `Wi-Fi` SSIDs/passphrases, static IP/DNS, `TLS` certificates).
   - Enforces the **Slot-1 Tier-0 Vault Write Firewall**: `[Load]` remains strictly `O_RDONLY` card-safe (`0` sector writes), whereas `[Save]` targeting an unverified or non-`WP`-locked Slot 1 Tier-0 forensic card (`pnflasha`/`cnflasha`/baseline `CAMSET01.DAT`) is deterministically blocked (`slot1_unverified_camset_save_blocked == True`).
3. **Unified `92`-Gate Master Preflight (`evaluate_92gate_preflight` / `verify-92-gates`)**:
   - **Offline default mode**: `89/92` gates pass (`G01..G09`, `G13..G92` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `92/92` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-shoe-audio-wind-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-saveload-c3-exclusions-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-92-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 47. Phase 246 Real-Hardware Main Track Part 34: `ILME-FX3` (`Ver. 7.02`) `[Framing Settings]` Asymmetric `Full`/`Crop` Stream Guard & `[Anti-flicker Shoot.]` Mechanical-Still-Only / No-`Var. Shutter` Firewall (`Gate G93`), `[USB Power Supply]` Mandatory `NP-FZ100` Insertion + `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence Guard (`Gate G94`), and Unified 94-Gate Master Preflight (`realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py`)

`realhw_framing_usbpower_lun_antiflicker_and_94gate_guard.py` (`realhw_framing_usbpower_lun_antiflicker_and_94gate_guard_v1`) delegates `G01..G92` directly to `evaluate_92gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-92-gates`) and adds Wave-37 real-hardware safety gates **`G93`** and **`G94`** into the unified **`94`-Gate Master Safety Preflight (`G01..G94` / `run_94_gate_preflight` / `evaluate_94gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Framing Settings]` Asymmetric `Full`/`Crop` Stream Guard & `[Anti-flicker Shoot.]` Mechanical-Still-Only / No-`Var. Shutter` Firewall (`verify_framing_asymmetric_and_antiflicker_no_varshutter_guard`, Gate `G93`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Framing Settings]` (`Framing`: `Off` default / `On`, `Recording/Streaming`: `Full` default / `Crop`, `HDMI`: `Crop` default / `Full` — all **resettable** via `[Camera Settings Reset]`): preserves the factory asymmetric dual-stream default (`Recording/Streaming=Full` internal master capture vs `HDMI=Crop` external monitor framing), blocks HDMI `RAW` output combination with cropped `[Framing]=On`, and rejects consumer `ZV-E1` (`ilc/2330`) `[Autoframing Settings]` conflation on `ILME-FX3` (`ilc/2210`).
   - Enforces `MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]` (`Off` default / `On` — **resettable** via `[Camera Settings Reset]`): functions strictly for mechanical-shutter still images (`100 Hz` / `120 Hz` flicker detection; non-functional in `Movie` / `S&Q Motion` and `[Silent Mode]=On` / electronic shutter) and enforces stock `ILME-FX3` (`ilc/2210`) absence of `[Var. Shutter]` (`fx3_has_var_shutter == False`, blocking false `FX30` `ilc/2220` `[Var. Shutter]` or `FX6` `ECS` menu assumptions).
2. **`ILME-FX3` (`Ver. 7.02`) `[USB Power Supply]` Mandatory `NP-FZ100` Insertion + `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence Guard (`verify_usb_power_npfz100_typec_and_lun_persistence_guard`, Gate `G94`)**:
   - Enforces non-resettable `MENU -> Setup -> [USB]` persistence (`[USB Connection Mode]=Sel. When Connect`, `[USB LUN Setting]=Multi`, `[USB Power Supply]=On` **survive `[Camera Settings Reset]`** and reset **only** via `[Initialize]`).
   - Enforces both `[USB Power Supply]` hardware power interlocks: (a) powering on without an inserted `NP-FZ100` battery pack (or `DC-C1` coupler) is hardware-unavailable, and mid-session battery removal under USB wall power triggers immediate unbuffered power-off, and (b) `Multi/Micro USB` cannot supply power or charge (`USB Type-C` exclusive).
   - Enforces `[USB LUN Setting]` (`Multi` `2`-LUN dual-slot vs `Single` `1`-LUN legacy primary-slot) visibility while keeping physical live host USB attachment hard-blocked (`usb_packets_transmitted == 0`, `hardware_live_attachment_authorized == False`, requiring off-camera `WP`-locked SDXC readers for Tier-0 SHA-256 verification).
3. **Unified `94`-Gate Master Preflight (`evaluate_94gate_preflight` / `verify-94-gates`)**:
   - **Offline default mode**: `91/94` gates pass (`G01..G09`, `G13..G94` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `94/94` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-framing-antiflicker-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-usbpower-lun-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-94-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 48. Phase 249 Real-Hardware Main Track Part 35: `ILME-FX3` (`Ver. 7.02`) `[Lock Operation Parts]` (`Fn` Hold, `MENU + Fn` 5s Full-Body Lock Chord vs Destructive `MENU + Delete` 2s & `My Dial` Temporary Override) Bench Guard (`Gate G95`), `[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]` Setup Persistence & `[Exposure step]` (`0.3EV`/`0.5EV`) vs `[Shutter Angle]` Constant-Table Guard (`Gate G96`), and Unified 96-Gate Master Preflight (`realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py`)

`realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.py` (`realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard_v1`) delegates `G01..G94` directly to `evaluate_94gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-94-gates`) and adds Wave-38 real-hardware safety gates **`G95`** and **`G96`** into the unified **`96`-Gate Master Safety Preflight (`G01..G96` / `run_96_gate_preflight` / `evaluate_96gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Lock Operation Parts]` (`Fn` Hold, `MENU + Fn` 5s Full-Body Lock Chord vs Destructive `MENU + Delete` 2s & `My Dial` Temporary Override) Bench Guard (`verify_lock_operation_parts_chord_and_mydial_guard`, Gate `G95`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]` (`Off` factory default, `Multi-Selector Only` / `[Multi-Slct Only]`, `Dial + Wheel`, `All` — **surviving `[Camera Settings Reset]`** and restored to `Off` **exclusively by `[Initialize]`**).
   - Enforces `Fn` hold lock/unlock toggle (`"Locked."` OSD banner), `MENU + Fn` simultaneous `5`-second full-body physical control lock (locking all buttons, dials, and wheels **except the shutter button** during unattended Tier-0 `pnflasha`/`cnflasha` dumps), `My Dial` temporary recall unlock (relocking immediately on release), and a hard firewall rejecting any confusion with the destructive `MENU + Delete` `2`-second Slot Full Format chord (`destructive_menu_delete_confusions == 0`).
2. **`ILME-FX3` (`Ver. 7.02`) `[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]` Setup Persistence & `[Exposure step]` (`0.3EV`/`0.5EV`) vs `[Shutter Angle]` Constant-Table Guard (`verify_audio_timing_signals_and_exp_step_shutter_angle_guard`, Gate `G96`)**:
   - Enforces `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]` (`Live` factory default / `Lip Sync`, **resettable** via `[Camera Settings Reset]`, hardware-locked out in `S&Q Motion` and when `[Audio Recording]=Off`) versus `MENU -> Setup -> [Sound Option] -> [Audio signals]` (`On` factory default / `Off`, **surviving `[Camera Settings Reset]`** while **hardware-locked to `Off`** whenever `[Silent Mode]=On`).
   - Enforces `MENU -> Exposure/Color -> [Exposure Comp.] -> [Exposure step]` (`0.3EV` factory default / `0.5EV`, **resettable** via `[Camera Settings Reset]`) governing `[Shutter Speed]`, `Aperture`, and `Exposure Comp.` increments while **`[Shutter Angle]` (`[Shutter Mode]=Shutter Angle`, `Ver. 6.00+`) remains strictly unaffected on its constant cine angle table** (`5.6°` .. `360°`, `shutter_angle_exposure_step_drift_events == 0`).
3. **Unified `96`-Gate Master Preflight (`evaluate_96gate_preflight` / `verify-96-gates`)**:
   - **Offline default mode**: `93/96` gates pass (`G01..G09`, `G13..G96` pass; physical Tier-0 `G10..G12` await receipt $\rightarrow$ `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `96/96` simulation gates pass (`dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-lock-op-parts-chord-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-audio-timing-exp-step-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-96-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 49. Phase 252 Real-Hardware Main Track Part 36: `ILME-FX3` (`Ver. 7.02`) `[Display Quality]` (`Standard`/`High`) Battery Conservation & `[Bluetooth Rmt Ctrl]` Infrared Remote (`SIRCS`) Lockout + `Reset Network Set.` Split Guard (`Gate G97`), `[My Menu Setting]` 6-Operation Persistence & Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY` Firewall Guard (`Gate G98`), and Unified 98-Gate Master Preflight (`realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py`)

`realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.py` (`realhw_display_quality_bt_rmt_mymenu_and_98gate_guard_v1`) delegates `G01..G96` directly to `evaluate_96gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-96-gates`) and adds Wave-39 real-hardware safety gates **`G97`** and **`G98`** into the unified **`98`-Gate Master Safety Preflight (`G01..G98` / `run_98_gate_preflight` / `evaluate_98gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Display Quality]` (`Standard`/`High`) Battery Conservation & `[Bluetooth Rmt Ctrl]` Infrared Remote (`SIRCS`) Lockout + `Reset Network Set.` Split Guard (`verify_display_quality_battery_and_bt_rmt_ir_lockout_guard`, Gate `G97`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libInfraBluetooth.so`, `libInfraAirplaneMode.so`, `libSaveLoadSettings.so`, and `libInfraSircs.so` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Setup -> [Monitor] -> [Display Quality]` (`Standard` factory default / `High` — **surviving both `[Camera Settings Reset]` and `[Reset Network Set.]`**, restored to `Standard` **exclusively by `[Initialize]`**) and clamps internal `NP-FZ100` battery Tier-0 bench dumps to `[Display Quality] = Standard` + `[Monitor Brightness] = Manual(0)` (`tier0_battery_high_display_violations == 0`).
   - Enforces `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]` (`Off` factory default / `On`), requiring `[Bluetooth Function]=On` + `[Airplane Mode]=Off` (blocked/suppressed on our zero-RF `Airplane Mode=On` bench with `passive_tx_bytes_emitted == 0`), enforcing Infrared Remote (`SIRCS`) mutual exclusion whenever `[Bluetooth Rmt Ctrl]=On` (`bt_rmt_ir_lockout_violations == 0`), and enforcing the exact 3-way reset split (survives `[Camera Settings Reset]`, reset to `Off` by **both** `[Reset Network Set.]` and `[Initialize]`).
2. **`ILME-FX3` (`Ver. 7.02`) `[My Menu Setting]` 6-Operation Persistence & Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY` Firewall Guard (`verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard`, Gate `G98`)**:
   - Enforces `MENU -> My Menu -> [My Menu Setting]` (`Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, up to `6` pages $\times$ `6` items `= 36` items, and `[Display From My Menu]` `Off` factory default / `On`), verifying non-resettable survival across **both `[Camera Settings Reset]` and `[Reset Network Set.]`** (cleared only by `[Delete All]` / `[Delete Page]` or full `[Initialize]`).
   - Enforces the Slot-1 Tier-0 `CAMSET01.DAT` `os.O_RDONLY` load-only firewall (`slot1_mymenu_vault_mutation_bytes == 0`, rejecting `SAVE_OVERWRITE`, any write open flags, and cross-model `ILME-FX6` camera-settings blobs).
3. **Unified `98`-Gate Master Preflight (`evaluate_98gate_preflight` / `verify-98-gates`)**:
   - **Offline default mode**: `95/98` gates pass (`overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `98/98` simulation gates pass (`VERIFIED_ALL_98_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-display-quality-bt-rmt-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-mymenu-camset-firewall-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-98-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 50. Phase 256 Grand Milestone (`100/100` Safety Gates): `ILME-FX3` (`Ver. 7.02`) `[Different Set for Still/Mv]` 8-Item Asymmetric Transitions & `[Shutter Mode] = [Angle]` Override Guard (`Gate G99`), `[Custom Key/Dial Set.]` `ISO/EI` Firewall & `[Remain Shoot Display]` EVF-Less Guard (`Gate G100`), and Unified 100-Gate Master Preflight (`realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py`)

`realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.py` (`realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard_v1`) delegates `G01..G98` directly to `evaluate_98gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-98-gates`) and adds Wave-40 real-hardware safety gates **`G99`** and **`G100`** (`100th` Grand Milestone Gate) into the unified **`100`-Gate Master Safety Preflight (`G01..G100` / `run_100_gate_preflight` / `evaluate_100gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Different Set for Still/Mv]` 8-Item Asymmetric State Transitions, Reset Survival & `[Shutter Mode] = [Angle]` Independence Override Guard (`verify_diff_set_still_mv_and_shutter_angle_guard`, Gate `G99`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `libInfraInput.so` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` across the exact `8` checkable items (`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture Profile`, `Focus Mode`), verifying survival across **both `[Camera Settings Reset]` and `[Reset Network Set.]`** (restored to unchecked factory defaults **exclusively by `[Initialize]`**).
   - Enforces `Common -> Separate` (copies current values to Still & Movie **except `Custom White Balance`**, which applies only to Still), `Separate -> Common` (returns items to initial factory defaults **except `Aperture`, `Shutter Speed`, and `Custom White Balance`**, which retain Still values; `diff_set_transition_corruption_events == 0`), and `Ver. 6.00+` / `Ver. 7.02` `[Shutter Mode] = [Angle]` override (Still Shutter Speed and Movie Shutter Angle remain independent even when `Shutter Speed` is Common; `shutter_angle_common_bleed_events == 0`).
2. **`ILME-FX3` (`Ver. 7.02`) `[Custom Key/Dial Set.]` 3-Domain Keymaps / `ISO/EI` Auto-Adapt / Slot-1 `CAMSET01.DAT` `O_RDONLY` Firewall & `[Remain Shoot Display]` Still-Buffer + EVF-Less Topology Guard (`verify_custom_key_dial_iso_ei_and_remain_shoot_guard`, Gate `G100`)**:
   - Enforces `MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]` (`Still` / `Movie` / `Playback` keymaps, Cinema-Line factory dial defaults `Front dial = Aperture`, `Rear dial = ISO/EI` auto-adapting between `ISO` and `Exposure Index (EI)`, `Control Wheel = Shutter Speed`, `[Follow Custom]` Movie inheritance, `[My Dial 1..3]`, `[Recall Custom hold 1..3]`), surviving **both `[Camera Settings Reset]` and `[Reset Network Set.]`** and enforcing the Slot-1 Tier-0 `CAMSET01.DAT` `os.O_RDONLY` load-only firewall (`slot1_custom_key_vault_mutation_bytes == 0`).
   - Enforces `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]` (`Not Displayed` factory default / `Always Display` / `Shoot-Only Display` still-buffer-only scope, surviving `[Camera Settings Reset]` and `[Reset Network Set.]`) and guards the EVF-less `ILME-FX3` (`ilc/2210`) monitor topology (`fx3_has_builtin_evf == False`, `evf_finder_monitor_spoof_events == 0`).
3. **Unified `100`-Gate Grand Milestone Master Preflight (`evaluate_100gate_preflight` / `verify-100-gates`)**:
   - **Offline default mode**: `97/100` gates pass (`VERIFIED_97_OF_100_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `100/100` simulation gates pass (`VERIFIED_ALL_100_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-diff-set-still-mv-shutter-angle-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-custom-key-dial-remain-shoot-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-100-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 51. Phase 259 (Wave-41): `ILME-FX3` (`Ver. 7.02`) `[Auto Slow Shutter]` 6-Condition Lockout, `[Shutter Mode] = [Angle]` Disjointness & `[Breathing Comp.]` Guard (`Gate G101`), `[HDMI Output Settings]` `REC Control` <- `Time Code Output` Gate, `4ch Audio Output` & `Rec. Media dur HDMI Output` Vault Guard (`Gate G102`), and Unified 102-Gate Master Preflight (`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py`)

`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.py` (`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard_v1`) delegates `G01..G100` directly to `evaluate_100gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-100-gates`) and adds Wave-41 real-hardware safety gates **`G101`** and **`G102`** into the unified **`102`-Gate Master Safety Preflight (`G01..G102` / `run_102_gate_preflight` / `evaluate_102gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Auto Slow Shutter]` 6-Condition Non-Function Lockout, `[Shutter Mode] = [Angle]` Disjointness & `[Breathing Comp.]` Guard (`verify_auto_slow_shutter_and_breathing_comp_guard`, Gate `G101`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]` (`On` factory default / `Off`, resettable by `[Camera Settings Reset]` and `[Initialize]`, unaffected by `[Reset Network Set.]`) across all `6` official Sony hardware non-function lockouts (`S&Q`, `Shutter Priority`, `Manual Exposure`, `[ISO] != [ISO AUTO]`, `[Exposure Ctrl Type] = [Flexible Exp. Mode]` with manual shutter, and `[Log Shooting] = [Cine EI Quick]` / `[Cine EI]`; `auto_slow_shutter_lockout_bypass_events == 0`), and exhaustively proves strict `320`-state hardware disjointness with `Ver. 7.02` `[Shutter Mode] = [Angle]` (`auto_slow_shutter_angle_overlap_events == 0`).
   - Enforces `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]` (`Off` factory default / `On`, resettable by `[Camera Settings Reset]`, movie-only compliant Sony E-mount FOV crop, locked out during `4264x2408` `RAW Output` and `S&Q` `239.76p`/`200p`; `breathing_comp_raw_or_240p_bypass_events == 0`).
2. **`ILME-FX3` (`Ver. 7.02`) `[HDMI Output Settings]` Non-Resettable `[Setup]` Survival, `[REC Control]` <- `[Time Code Output]` Prerequisite, `[4ch Audio Output]` Routing & `[Rec. Media dur HDMI Output]` Vault Guard (`verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard`, Gate `G102`)**:
   - Enforces `MENU -> Setup -> [External Output] -> [HDMI Output Settings]` survival across **both `[Camera Settings Reset]` and `[Reset Network Set.]`** (cleared **only** by `[Initialize]`).
   - Enforces `[REC Control]` (`Off` default / `On`) mandatory prerequisite `[Time Code Output] = [On]` (`hdmi_rec_ctrl_without_tc_violations == 0`), `[4ch Audio Output]` channel routing (`CH1/CH2` default -> `CH1=L/CH2=R` vs `CH3/CH4` -> `CH3=L/CH4=R` when 4-channel MI-shoe audio is active), and `[Rec. Media dur HDMI Output] = [Off]` inhibition of internal Slot-1/Slot-2 clip and `[Proxy Recording]` writes (`slot1_hdmi_rec_vault_mutation_bytes == 0`).
3. **Unified `102`-Gate Master Preflight (`evaluate_102gate_preflight` / `verify-102-gates`)**:
   - **Offline default mode**: `99/102` gates pass (`VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `102/102` simulation gates pass (`VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-auto-slow-shutter-breathing-comp-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-hdmi-reccontrol-tcout-4chaudio-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-102-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 52. Phase 263 (Wave-42): `ILME-FX3` (`Ver. 7.02`) `[APS-C S35 Shooting]` `12.1MP` Sensor `4K` Movie Lockout & `[Face/Eye AF]` Clean-HDMI Isolation Guard (`Gate G103`), `[Version]` Read-Only Inspection, Zero-RF Badge Suppression & Hard-Blocked `BODYDATA.DAT` Flash Guard (`Gate G104`), and Unified 104-Gate Master Preflight (`realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py`)

`realhw_apsc_s35_face_eye_af_version_and_104gate_guard.py` (`realhw_apsc_s35_face_eye_af_version_and_104gate_guard_v1`) delegates `G01..G102` directly to `evaluate_102gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-102-gates`) and adds Wave-42 real-hardware safety gates **`G103`** and **`G104`** into the unified **`104`-Gate Master Safety Preflight (`G01..G104` / `run_104_gate_preflight` / `evaluate_104gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[APS-C S35 Shooting]` `12.1MP` `4K` Movie Lockout & `[Face/Eye AF]` Clean-HDMI Isolation Guard (`verify_apsc_s35_and_face_eye_af_guard`, Gate `G103`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]` (`Auto` default / `On` ~`1.5x` Super 35mm / `Off` 35mm full-frame, resettable by `[Camera Settings Reset]`): on `ILME-FX3` (`ilc/2210`, `12.1MP` sensor), `4K` movie formats (`XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`) and `4264x2408` `HDMI RAW Output` strictly force `[APS-C S35 Shooting]` to `[Off]` across all `60` movie states so Super 35mm movie capture operates **only** in `HD` (`XAVC S HD` / `XAVC S-I HD`; `apsc_s35_4k_or_raw_bypass_events == 0`).
   - Enforces `MENU -> Focus -> [Face/Eye AF]` BIONZ XR hierarchy (rejecting dedicated AI-unit `[Subject Recog in AF]`, `ai_unit_subject_recog_spoof_events == 0`: `[Face/Eye Prior. in AF]`, `[Face/Eye Subject]` `Human`/`Animal`/`Bird`, `[Right/Left Eye Select]`, `[Face/Eye Frame Disp.]` clean-HDMI isolation `hdmi_clean_feed_eye_frame_baked_pixels == 0`, and `[Face Memory]` surviving `[Camera Settings Reset]`).
2. **`ILME-FX3` (`Ver. 7.02`) `[Version]` Read-Only Inspection, Zero-RF Update Badge Suppression & Hard-Blocked `BODYDATA.DAT` Flash Guard (`verify_version_readonly_and_bodydata_flash_block_guard`, Gate `G104`)**:
   - Enforces `MENU -> Setup -> [Setup Option] -> [Version]` read-only Body (`Ver. 7.02`), E-mount Lens, and Mount Adaptor version inspection with zero flash partition writes (`version_dialog_flash_writes == 0`).
   - Enforces `Ver. 6.00+`/`7.02` update notification badge suppression on our zero-RF `Airplane Mode = On` bench (`passive_tx_bytes_emitted == 0`), and hard-blocks all automated Slot-1 `BODYDATA.DAT` firmware flash execution (`persistent_emmc_writes_authorized == False`, `bodydata_flash_attempts_blocked >= 1`, `slot1_bodydata_vault_mutation_bytes == 0`).
3. **Unified `104`-Gate Master Preflight (`evaluate_104gate_preflight` / `verify-104-gates`)**:
   - **Offline default mode**: `101/104` gates pass (`VERIFIED_101_OF_104_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `104/104` simulation gates pass (`VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-apsc-s35-face-eye-af-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-version-readonly-bodydata-flash-block-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-104-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 53. Phase 266 (Task H300 Milestone, Wave-43): `ILME-FX3` (`Ver. 7.02`) `[Release w/o Card]` & `[Release w/o Lens]` Scope + `Ver. 7.02` 5-Item `[Audio Recording]` vs `[DISP (Screen Disp) Set]` Audio Meter Guard (`Gate G105`), `[Copyright Info]` `46`-Char Still EXIF & Clean-Room Bench PII Hygiene Guard (`Gate G106`), and Unified 106-Gate Master Preflight (`realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py`)

`realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.py` (`realhw_release_wo_card_audio_meter_copyright_and_106gate_guard_v1`) delegates `G01..G104` directly to `evaluate_104gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-104-gates`) and adds Wave-43 real-hardware safety gates **`G105`** and **`G106`** into the unified **`106`-Gate Master Safety Preflight (`G01..G106` / `run_106_gate_preflight` / `evaluate_106gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Release w/o Card]` Still-Only vs Movie Internal Media Gate, `[Release w/o Lens]` Zero-`E-ND` / Zero-E-Mount-UART Guard & `Ver. 7.02` 5-Item `[Audio Recording]` vs `DISP` Audio Meter Guard (`verify_release_wo_card_lens_and_v702_audio_disp_guard`, Gate `G105`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]` (`Enable` default / `Disable`, Still-only scope vs Movie internal media gate across all `96` scope states; production posture requires `[Disable]` anti-unrecorded-shoot protection while cardless diagnostic bench `[Enable]` emits `0` media sector writes and internal Movie/`S&Q` recording stays strictly blocked when both slots are empty while external HDMI capture remains governed by `[Rec. Media dur HDMI Output]`).
   - Enforces `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Lens]` (`Enable` default / `Disable`, Still + Movie + `S&Q` scope with `e_nd_actuator_tx_count == 0` and `0` E-mount lens UART bytes on body-only/PL-mount bench), plus `Ver. 2.00+`/`7.02` (`ilc/2210`) exact `5`-item `[Audio Recording]` menu (`Audio Recording`, `Audio Rec Level` `0..31`, `Audio Out Timing`, `Wind Noise Reduct.`, `Shoe Audio Set.`) rejecting `Ver. 1.x` (`ilc/2035`) standalone `[Audio Level Display]` (`legacy_v1_audio_level_menu_spoof_events == 0`) and verifying `2ch`/`4ch` audio meter visibility (suppressed during `S&Q`) under `MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]`.
2. **`ILME-FX3` (`Ver. 7.02`) `[Copyright Info]` `46`-Char Printable ASCII Bounds, Still-EXIF-Only Scope, Reset Survival & Clean-Room Bench PII Hygiene Guard (`verify_copyright_info_46char_still_exif_and_pii_hygiene_guard`, Gate `G106`)**:
   - Enforces `MENU -> Shooting -> [File] -> [Copyright Info]` (`Write Copyright Info` `Off` default / `On`, `Set Photographer` `<= 46` printable ASCII chars, `Set Copyright` `<= 46` printable ASCII chars, read-only `Disp. Copyright Info`), Still-JPEG/HEIF/ARW EXIF-only scope (`0x013B` Artist / `0x8298` Copyright, never mutating XAVC/RAW movie streams or `Slot-1` recovery vault), `[Camera Settings Reset]` string survival vs `[Initialize]` wipe, `[Save/Load Settings]` exclusion, and clean-room bench PII hygiene (`Write Copyright Info = Off` default on bench, `photographer_copyright_pii_leaked_bytes == 0`).
3. **Unified `106`-Gate Master Preflight (`evaluate_106gate_preflight` / `verify-106-gates`)**:
   - **Offline default mode**: `103/106` gates pass (`VERIFIED_103_OF_106_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `106/106` simulation gates pass (`VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-release-wo-card-lens-audio-disp-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-copyright-info-46char-exif-hygiene-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-106-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 54. Phase 268 (Task H302, Wave-44): `ILME-FX3` (`Ver. 7.02`) Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char `Title Name` + Fixed `PRIVATE/M4ROOT/CLIP`) vs Still `[File/Folder Settings]` (`3`-Char `DSC` Prefix & `Slot-1` Vault Guard) (`Gate G107`), `[Gamma Display Assist]` `[Log Shooting]` Lockout vs `[Display LUT]` / `[Select LUT]`, `[Auto Review]` `Off` Default & `6`-Item `[TC/UB]` Persistence Guard (`Gate G108`), and Unified 108-Gate Master Preflight (`realhw_file_settings_gamma_assist_tcub_and_108gate_guard.py`)

`realhw_file_settings_gamma_assist_tcub_and_108gate_guard.py` (`realhw_file_settings_gamma_assist_tcub_and_108gate_guard_v1`) delegates `G01..G106` directly to `evaluate_106gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-106-gates`) and adds Wave-44 real-hardware safety gates **`G107`** and **`G108`** into the unified **`108`-Gate Master Safety Preflight (`G01..G108` / `run_108_gate_preflight` / `evaluate_108gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char `Title Name` + Fixed `PRIVATE/M4ROOT/CLIP`) vs Still `[File/Folder Settings]` (`3`-Char `DSC` Prefix & `Slot-1` Recovery Vault Guard) (`verify_movie_file_settings_still_dsc_and_slot1_vault_guard`, Gate `G107`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` synthetic fallback.
   - Enforces `MENU -> Shooting -> [File] -> [File Settings]` (`[File Number]` `Series` default / `Reset` + `[Series Counter Reset]`, `[File Name Format]` `Standard` default, `Cam ID + Reel#` with `Camera ID` `A..Z`, `Reel Number` `001..999`, `Camera Position` `C`/`L`/`R`, `Title`, `Date + Title`, `Title + Date` on `Ver. 3.00+`, `[Title Name Settings]` `"C"` default `<= 37` printable ASCII chars, and fixed movie clip folder topology `PRIVATE/M4ROOT/CLIP` rejecting custom movie folder paths) alongside `MENU -> Shooting -> [File] -> [File/Folder Settings]` (`[File Number]` `Series` default / `Reset`, `[Set File Name]` `"DSC"` default exact `3` chars `A-Z`/`0-9`/`_` rejecting `_` at index `0`, `[Folder Name]` `Standard Form` `NNN+5chars` default / `Date Form` `NNN+YMMDD`).
   - Enforces non-resettable survival across `[Camera Settings Reset]` (restored only by `[Initialize]`) and hard-blocks `[Forced File Number Reset]` / `[Create New Folder]` on `Slot 1` whenever `Slot 1` holds the read-only `CAMSET`/`BODYDATA.DAT` recovery vault (`slot1_vault_folder_mutation_events == 0` across all `360` matrix states).
2. **`ILME-FX3` (`Ver. 7.02`) `[Gamma Display Assist]` `[Log Shooting]` Lockout & Clean External HDMI vs `[Display LUT]` / `[Select LUT]`, `[Auto Review]` `Off` Cinema Default & `6`-Item `[TC/UB]` Non-Resettable Persistence Guard (`verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard`, Gate `G108`)**:
   - Enforces `MENU -> Setup -> [Display Option] -> [Gamma Display Assist]` (`Off` default / `On`) & `[Gamma Disp. Assist Typ.]` (`Auto` default, `S-Log3->709(800%)`, `HLG(BT.2020)`, `HLG(709)`), hard-locking `[Gamma Display Assist]` to `Off` whenever `[Log Shooting]` (`Cine EI`, `Cine EI Quick`, `Flexible ISO`) `!= Off` (monitoring governed instead by `[Display LUT]` `On` default / `Off` and `[Select LUT]` `S-Log3`, `s709`, `709(800%)`, `User1..User16`) and enforcing camera-LCD-only scope (`hdmi_gamma_assist_leak_frames == 0` across all `128` matrix states).
   - Enforces `MENU -> Setup -> [Display Option] -> [Auto Review]` (`Off` cinema default / `2 Sec` / `5 Sec` / `10 Sec`, Still-only with `0` movie interruptions) and all `6` `MENU -> Shooting -> [TC/UB]` parameters (`Time Code Preset` `00:00:00.00`, `User Bit Preset` `00 00 00 00`, `Time Code Format` `DF`/`NDF` with `24.00p` & PAL `25p`/`50p` forced `NDF`, `Time Code Run` `Rec Run` default / `Free Run`, `Time Code Make` `Preset` default / `Regenerate`, `User Bit Time Rec` `Off` default / `On`) plus `[TC/UB Disp. Setting]` (`TC` default / `U-Bit`), verifying survival across `[Camera Settings Reset]` (reset only via `[Initialize]`).
3. **Unified `108`-Gate Master Preflight (`evaluate_108gate_preflight` / `verify-108-gates`)**:
   - **Offline default mode**: `105/108` gates pass (`VERIFIED_105_OF_108_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `108/108` simulation gates pass (`VERIFIED_ALL_108_GATES_DRY_RUN_SIMULATED_BACKUP`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-file-settings-dsc-slot1-vault-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-gamma-disp-assist-auto-review-tcub-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-108-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```

---

## 55. Phase 271 Milestone (`110/110` Safety Gates, Task H306, Wave-45): `ILME-FX3` (`Ver. 7.02`) `[Focus Assistant]` (`[Auto Magnifier in MF]`, `Custom Button 5`, `[Initial Focus Mag.]` `x1.0`), `[Peaking Display]` Clean-HDMI Isolation & Still-Only `[AF Illuminator]` Guard (`Gate G109`), `[Area/Date/Time Setting]` Zero-RF Sync Suppression, `[Video Light Mode]` (`Power Link` + `5V <= 900 mA`) & `[HDMI Resolution]` (`Auto` + Log `1080p` Downshift) Guard (`Gate G110`), and Unified 110-Gate Master Preflight (`realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py`)

`realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.py` (`realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard_v1`) delegates `G01..G108` directly to `evaluate_108gate_preflight()` (preserving `100%` backward compatibility across `verify-58-gates` through `verify-108-gates`) and adds Wave-45 real-hardware safety gates **`G109`** and **`G110`** into the unified **`110`-Gate Master Safety Preflight (`G01..G110` / `run_110_gate_preflight` / `evaluate_110gate_preflight`)**, hard-locking `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`, `SPI_NOR_WRITE_AUTHORIZED = False`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`, `USB_PACKETS_TRANSMITTED = 0`, `RAW_FIRMWARE_BYTES_LEAKED = 0`, and `overall_ready_for_hardware_attach = False`:

1. **`ILME-FX3` (`Ver. 7.02`) `[Focus Assistant]`, `[Peaking Display]` Clean-HDMI Isolation & Still-Only `[AF Illuminator]` Guard (`verify_focus_mag_peaking_af_illuminator_guard`, Gate `G109`)**:
   - Performs a bounded `< 0.10s` `os.open(..., os.O_RDONLY)` local donor audit across `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin` (`raw_firmware_bytes_leaked == 0`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` synthetic fallback.
   - Enforces `MENU -> Focus -> [Focus Assistant]` exact `ilc/2210` nomenclature (`[Auto Magnifier in MF] = [On]` default, rejecting legacy `"MF Assist"` nomenclature spoofing with `legacy_mf_assist_spoof_events == 0`; `[Focus Magnifier]` assigned to `Custom Button 5`; `[Focus Magnif. Time] = [No Limit]` default across `2 Sec` / `5 Sec` / `No Limit`; separate Still & Movie `[Initial Focus Mag.]` registers defaulting to `[x1.0]` across `x1.0` / `x4.0`; Still-only `[AF in Focus Mag.] = [On]` default) and `[Peaking Display]` (`Off` default, `[Peaking Level] = [Mid]`, `[Peaking Color] = [White]`, `[Peaking Display Select] = Control Wheel Right`).
   - Enforces clean-HDMI isolation (`[HDMI Info. Display] = [Off]` or `HDMI RAW` -> `hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`) and strictly Still-only `[AF Illuminator]` (`Auto` default / `Off` -> `movie_sq_af_illuminator_fire_events == 0`) across all `144` matrix states.
2. **`ILME-FX3` (`Ver. 7.02`) `[Area/Date/Time Setting]` Zero-RF Sync Suppression, `[Video Light Mode]` `Power Link` + `5V <= 900 mA` & `[HDMI Resolution]` Log `1080p` Downshift Guard (`verify_area_datetime_videolight_hdmires_guard`, Gate `G110`)**:
   - Enforces `MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]` (rejecting legacy `"Date/Time Setup"` spoofing with `legacy_datetime_setup_spoof_events == 0`; `[Area Setting]` `—`, `[Daylight Savings] = [Off]` default, `[Date/Time]`, `[Date Format]`), survival across `[Camera Settings Reset]` (cleared only by `[Initialize]` or RTC battery loss), and zero-RF bench hard suppression of Creators' App `[Auto Time Correction]` / `[Auto Area Adjustment]` under `[Airplane Mode] = [On]` (`passive_tx_bytes_emitted == 0`, `unsolicited_rtc_timezone_jump_events == 0`).
   - Enforces `[Video Light Mode]` (`[Power Link]` default / `[REC Link]` / `[REC Link & STBY]` / `[Auto]`) `[Setup]` reset survival and MI-Shoe `5V <= 900 mA` (`G24`) rail budget (`mishoe_5v_overcurrent_events == 0`), plus `[HDMI Resolution]` (`[Auto]` default / `2160p` / `1080p` / `1080i`) `[Setup]` reset survival and hardware Log internal-recording `1080p` downshift override when `Rec. Media dur HDMI Output = On` (`hdmi_res_log_internal_rec_2160p_bypass_events == 0`) across all `256` matrix states.
3. **Unified `110`-Gate Master Milestone Preflight (`evaluate_110gate_preflight` / `verify-110-gates`)**:
   - **Offline default mode**: `107/110` gates pass (`VERIFIED_107_OF_110_AWAITING_PHYSICAL_TIER0`, `overall_ready_for_hardware_attach = False`).
   - **`--simulate-bench-dry-run` rehearsal mode**: `110/110` simulation gates pass (`VERIFIED_ALL_110_GATES_DRY_RUN_SIMULATED_BACKUP`, `all_110_gates_verified = True`, `dry_run_rehearsal_only = True`) while all hardware write/live-attach redlines remain `False` and `usb_packets_transmitted == 0`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-focus-mag-peaking-af-illuminator-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-area-datetime-videolight-hdmires-guard [--force-clean-room] [--json]
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety \
  /usr/bin/python3 -B -m fx3_safety verify-110-gates [--force-clean-room] [--simulate-bench-dry-run] [--json]
```





