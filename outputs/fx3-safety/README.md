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
- Submodules: `boot_contracts`, `brick_classifier`, `crsdk_mishoe_ltc_spacc_guard`, `dewpoint_tec_usbc_and_24gate_guard`, `exfat_media_integrity_guard`, `h0_hardware_rehearsal`, `hdmi_aoc_5v_cfexpress_and_36gate_guard`, `intake_occlusion_tripod_and_26gate_guard`, `master_16gate_preflight`, `monsoon_mishoe_cagetwist_and_40gate_guard`, `multiport_bootrom_unbrick`, `phantom48v_gimbal_and_22gate_guard`, `pl_cantilever_dummybatt_and_32gate_guard`, `preflight`, `realhw_c2pa_tc_gyro_and_56gate_guard`, `realhw_cfexpress_ufu_el3_and_52gate_guard`, `realhw_cxd90058_sabin_seal_and_54gate_guard`, `realhw_dualmedia_bench_interlock_and_58gate_guard`, `realhw_jiritsu_cnflasha_and_44gate_guard`, `realhw_pnflasha_mtdro_rfnvs_and_48gate_guard`, `realhw_service0336_mpr_ibis_and_46gate_guard`, `realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard`, `realhw_uart1v8_imx510_cal_and_50gate_guard`, `rig_groundloop_lensrail_and_20gate_guard`, `runtime_antibrick_guards`, `saltspray_haze_followfocus_and_34gate_guard`, `sensor_curtain_subzero_and_28gate_guard`, `serial_fault_detector_v2`, `thermal_pwm_and_power_guard`, `usbpd_trigger_multiterminal_and_38gate_guard`, `usblan_ptpip_and_18gate_preflight`, `vp_strobe_vehiclerig_ibis_and_42gate_guard`, `wireless_tx_emi_endurance_and_30gate_guard`.
- Key entrypoints: `run_h0_hardware_rehearsal`, `H0RehearsalConfig`, `H0RehearsalReport`, `evaluate_12_safety_gates`, `evaluate_16_master_safety_gates`, `Master16GateReport`, `evaluate_18_master_safety_gates`, `Master18GateReport`, `evaluate_20gate_preflight`, `Master20GateReport`, `evaluate_22gate_preflight`, `Master22GateReport`, `evaluate_24gate_preflight`, `Master24GateReport`, `evaluate_26gate_preflight`, `Master26GateReport`, `evaluate_28gate_preflight`, `Master28GateReport`, `evaluate_30gate_preflight`, `evaluate_30_master_safety_gates`, `Master30GateReport`, `evaluate_32gate_preflight`, `evaluate_32_master_safety_gates`, `Master32GateReport`, `evaluate_34gate_preflight`, `evaluate_34_master_safety_gates`, `Master34GateReport`, `evaluate_36gate_preflight`, `evaluate_36_master_safety_gates`, `Master36GateReport`, `evaluate_38gate_preflight`, `evaluate_38_master_safety_gates`, `Master38GateReport`, `evaluate_40gate_preflight`, `evaluate_40_master_safety_gates`, `Master40GateReport`, `evaluate_42gate_preflight`, `evaluate_42_master_safety_gates`, `Master42GateReport`, `evaluate_44gate_preflight`, `evaluate_44_master_safety_gates`, `Master44GateReport`, `evaluate_46gate_preflight`, `evaluate_46_master_safety_gates`, `Master46GateReport`, `evaluate_48gate_preflight`, `evaluate_48_master_safety_gates`, `Master48GateReport`, `evaluate_50gate_preflight`, `evaluate_50_master_safety_gates`, `Master50GateReport`, `evaluate_52gate_preflight`, `evaluate_52_master_safety_gates`, `Master52GateReport`, `evaluate_54gate_preflight`, `evaluate_54_master_safety_gates`, `Master54GateReport`, `evaluate_56gate_preflight`, `evaluate_56_master_safety_gates`, `Master56GateReport`, `evaluate_58gate_preflight`, `evaluate_58_master_safety_gates`, `Master58GateReport`, `evaluate_60gate_preflight`, `evaluate_60_master_safety_gates`, `Master60GateReport`, `evaluate_g13_multiport_and_mishoe_isolation`, `evaluate_g14_thermal_and_power_envelope`, `evaluate_g15_c2pa_and_calibration`, `evaluate_g16_stage_b_p12_and_wbi2_lock`, `evaluate_g17_exfat_and_client_media_isolation`, `evaluate_g18_usblan_ptpip_and_airplane_coexistence`, `evaluate_g19_rig_groundloop_and_lensrail`, `evaluate_g20_power_failover_and_rsv_salvage`, `evaluate_g21_xlr_phantom48v_and_hotpatch`, `evaluate_g22_gimbal_focus_torque_and_sensor_curtain`, `evaluate_g23_dewpoint_and_tec_condensation`, `evaluate_g24_pmic_5v_and_usbc_strain`, `evaluate_g25_sigma_fan_intake_exhaust`, `evaluate_g26_tripod_torque_and_housing_vacuum`, `evaluate_g27_sensor_curtain_and_ibis_transport`, `evaluate_g28_subzero_esr_and_altitude`, `evaluate_g29_wireless_tx_emi_and_hotplug_esd`, `evaluate_g30_longform_endurance_and_nvram`, `evaluate_g31_pl_cantilever_and_lws_support`, `evaluate_g32_dummy_battery_overvoltage_firewall`, `evaluate_g33_saltspray_alkali_dust_and_haze`, `evaluate_g34_followfocus_hardstop_and_gimbal_cog`, `evaluate_g35_hdmi_aoc_5v_and_port_shear`, `evaluate_g36_cfexpress_vpg_thermal_and_door_flush`, `evaluate_g37_usbpd_trigger_and_uvc_thermal`, `evaluate_g38_multiterminal_ltc_uart_and_ptp`, `evaluate_g39_monsoon_rain_and_mishoe`, `evaluate_g40_xlr_h1_quarter20_and_cage_twist`, `evaluate_g41_vp_strobe_and_genlock`, `evaluate_g42_vehiclerig_ibis_and_tether`, `evaluate_g43_jiritsu_service`, `evaluate_g44_cnflasha_dualboot`, `evaluate_g45_service_0336_canary`, `evaluate_g46_mpr_ibis_p18_guard`, `evaluate_g47_pnflasha_mtdro_vault`, `evaluate_g48_rfnvs_fan_power_guard`, `evaluate_g49_uart1v8_isp`, `evaluate_g50_imx510_sensor_cal`, `evaluate_g51_cfexpress_ufu`, `evaluate_g52_5tier_el3_guard`, `evaluate_g53_cxd90058_sabin`, `evaluate_g54_factory_seal`, `evaluate_g55_c2pa_cert`, `evaluate_g56_tc_gyro_meta`, `evaluate_g57_dualmedia_vault`, `evaluate_g58_bench_interlock`, `evaluate_g59_ssboot_wbi2_guard`, `evaluate_g60_slot1_ufu_c2pa_guard`, `verify_c2pa_and_factory_calibration_immutability`, `verify_stage_b_p12_wf12_and_wbi2_lock`, `classify_brick_state`, `evaluate_runtime_antibrick_guards`, `validate_rp2040_multiport_harness`, `audit_fastboot_command_sequence`, `audit_serial_boot_telemetry`, `audit_round10_summary_telemetry`, `StreamingSerialFaultDetectorV2`, `verify_watchdog_budget`, `verify_multiport_ltc_vs_uart_boot`, `verify_mishoe_digital_audio_and_p11_coexistence`, `audit_crsdk_ptp2_session`, `audit_spacc_block_layer`, `evaluate_phase38_safety_guards`, `audit_donor_thermal_fan_power_contracts`, `verify_fan_thermal_envelope`, `verify_battery_and_usbpd_firewall`, `evaluate_thermal_pwm_and_power_guard`, `compute_exfat_boot_checksum`, `parse_exfat_vbr`, `verify_exfat_boot_region`, `inspect_sony_media_tree`, `verify_dual_slot_media_firewall`, `parse_p1_fat12_fat16_vbr`, `verify_p1_vs_exfat_filesystem_separation`, `evaluate_exfat_media_integrity_guard`, `audit_usblan_ptpip_donor_contracts`, `verify_usblan_wired_control_and_airplane_coexistence`, `classify_usblan_ptpip_or_mc_operation`, `evaluate_ptpip_15740_packet`, `audit_usblan_ptpip_and_mc_firewall`, `audit_rig_20gate_donor_contracts`, `verify_rig_power_sequence`, `verify_rig_dtap_hdmi_groundloop_firewall`, `verify_emount_hot_detach_rail_and_ibis_park`, `inspect_sony_rsv_salvage_structure`, `verify_power_failover_ups_and_rsv_salvage`, `audit_phase77_donor_contracts`, `verify_xlr_h1_channel`, `verify_xlr_h1_phantom_48v_firewall`, `verify_gimbal_focus_torque_and_laser_shutter_guard`, `audit_phase84_donor_contracts`, `compute_magnus_tetens_dew_point_c`, `verify_dewpoint_tec_condensation_firewall`, `verify_pmic_5v_accessory_and_usbc_strain_guard`, `audit_phase92_donor_contracts`, `verify_sigma_fan_intake_exhaust_firewall`, `verify_tripod_screw_torque_and_housing_vacuum_guard`, `audit_phase97_donor_contracts`, `compute_arrhenius_npfz100_esr_ohm`, `compute_isa_atmosphere`, `predict_npfz100_terminal_voltage_v`, `verify_sensor_curtain_and_ibis_transport_guard`, `verify_subzero_esr_and_altitude_firewall`, `audit_phase100_donor_contracts`, `compute_nearfield_efield_v_per_m`, `estimate_recording_footprint_gib`, `compute_emmc_nvram_wear_cycles`, `verify_wireless_tx_emi_and_hotplug_esd_guard`, `verify_longform_exfat_smart_and_nvram_guard`, `audit_phase104_donor_contracts`, `compute_cantilever_bending_moment_nm`, `compute_pmic_overvoltage_stress_ratio`, `verify_pl_cantilever_and_emount_flange_guard`, `verify_dummy_battery_overvoltage_firewall`, `audit_phase108_donor_contracts`, `compute_haze_fin_fouling_dose_mg_min_m3`, `compute_estimated_ingested_aerosol_ug`, `compute_fiz_gear_tangential_force_n`, `compute_single_rod_deflection_mm`, `compute_gimbal_cog_torque_imbalance_nm`, `verify_saltspray_alkali_dust_and_haze_firewall`, `verify_followfocus_hardstop_and_gimbal_cog_guard`, `audit_phase115_donor_contracts`, `compute_hdmi_pin18_power_mw`, `compute_hdmi_type_a_cantilever_moment_nm`, `compute_required_sustained_write_mb_s`, `verify_hdmi_aoc_5v_and_port_shear_firewall`, `verify_cfexpress_vpg_thermal_and_door_guard`, `audit_phase120_donor_contracts`, `compute_uart_pad_overdrive_ratio`, `compute_usbpd_contract_watts`, `estimate_uvc_4k30p_thermal_rise_c`, `verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall`, `verify_multiterminal_ltc_uart_and_ptp_guard`, `audit_phase125_donor_contracts`, `compute_mishoe_galvanic_leakage_current_ma`, `estimate_mishoe_pin_electrolysis_power_mw`, `compute_xlr_h1_whip_moment_nm`, `estimate_emount_ffd_tilt_um`, `verify_monsoon_rain_mishoe_firewall`, `verify_xlr_h1_quarter20_and_cage_twist_guard`, `audit_phase131_donor_contracts`, `estimate_imx510_microlens_flash_temp_rise_c`, `compute_led_wall_ecs_beat_ratio`, `estimate_ibis_voice_coil_excursion_mm`, `compute_tether_static_safety_factor`, `verify_vp_strobe_uvarc_and_genlock_firewall`, `verify_vehiclerig_vibration_ibis_and_tether_guard`, `audit_phase142_donor_contracts`, `compute_p6_quota_utilization_pct`, `validate_elf_64k_alignment_and_hash`, `classify_spacc_block_device`, `validate_tier0_cold_backup_receipt`, `default_verified_tier0_sha256_receipts`, `verify_jiritsu_service_session_and_p6_guard`, `verify_cnflasha_spacc_sd_escape_and_p1_p3_guard`, `audit_phase148_donor_contracts`, `validate_op_ff_ram_canary`, `validate_fx3s0ok_packet_header`, `validate_ibis_coil_park_state`, `compute_dmm_pool_utilization_pct`, `verify_service0336_canary_64k_unlink_and_msc_return`, `verify_stageb_p18_ibis_park_and_dmmcfg_guard`, `audit_phase153_donor_contracts`, `validate_dual_layer_cipher_pairing`, `validate_camera_cid_binding`, `validate_mtd_readonly_guard`, `compute_cpapp_fan_override_pwm_pct`, `evaluate_npfz100_6100mv_encwfistop`, `verify_pnflasha_cnflasha_cid_and_mtdro_guard`, `verify_rfnvs_msc_fan_override_and_power_guard`, `audit_phase158_donor_contracts`, `validate_uart_1v8_passive_rx`, `validate_emmc_isp_1v8_passive_read`, `validate_sensor_calibration_nvs_lock`, `validate_imx510_dual_base_iso_gain`, `validate_cube_3dlut`, `build_synthetic_identity_cube_text`, `verify_uart1v8_vmc_bncm1_and_emmc_isp_guard`, `verify_imx510_sensor_cal_and_mlut_guard`, `audit_phase161_donor_contracts`, `compute_required_media_write_mb_s`, `validate_dual_slot_media_bitrate`, `validate_card_door_gpio_flush`, `validate_user_clip_dirs_untouched`, `validate_bodydata_ufu_and_clean_uninstall`, `validate_5tier_recovery_ladder`, `validate_fx3_model_id_bodydata_lock`, `validate_cxd90057_el3_readonly_guard`, `verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard`, `verify_5tier_recovery_model_id_and_el3_ro_guard`, `audit_phase165_donor_contracts`, `default_verified_16_surface_seal_hashes`, `find_h0_h3_surface_mismatches`, `validate_cxd90058_and_sabin_immutability`, `validate_mira_cetus_intersoc_link`, `validate_sdi_raw_mew_mask`, `validate_memcfg_xavc_encoder_pool`, `validate_16_surface_h0_h3_seal`, `validate_zero_bench_residuals`, `validate_otp_rpmb_and_updater_flags`, `verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard`, `verify_post_bench_factory_seal_and_official_readiness_guard`, `audit_phase170_donor_contracts`, `default_verified_rq_lic_h0_to_h3_hashes`, `build_synthetic_nrtm_gyro_xml`, `validate_p12_cert_ms_rdonly_lock`, `validate_rq_lic_h0_to_h3_preservation`, `validate_c2pa_cross_model_signing_firewall`, `validate_vmc_bncm1_ltc_and_uart_mux`, `validate_fx6_tc_out_bnc_mask`, `validate_imx510_gyro_nrtm_integrity`, `verify_c2pa_rq_lic_and_cross_model_signing_guard`, `verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard`, `audit_phase173_donor_contracts`, `gf256_mul`, `gf256_inv`, `gf256_div`, `encode_gf256_pq_parity`, `recover_gf256_pq_chunks`, `build_synthetic_16_surface_chunks`, `default_verified_16_surface_hashes`, `validate_dual_media_device_id_separation`, `validate_dual_media_16_surface_sha256_parity`, `validate_gf256_bitrot_scrub_guard`, `verify_dual_media_vault_and_gf256_scrub_guard`, `verify_two_step_bench_interlock_guard`, `audit_phase177_donor_contracts`, `build_synthetic_wbi2_sector0`, `parse_firmware_version_tuple`, `validate_wbi2_tier0_receipt`, `validate_wbi2_stageb_ro_protection`, `validate_ssboot_resume_bypass_guard`, `validate_wbi2_clean_uninstall_h0_h3`, `validate_fx3_body_firmware_floor`, `validate_slot1_root_and_duplicate_guard`, `validate_c2pa_100_license_and_p12_lock`, `validate_v700_wireless_security_floor`, `verify_ssboot_wbi2_prsvimg_and_liro_guard`, `verify_fx3_702_ufu_floor_and_slot1_c2pa_guard`.

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


