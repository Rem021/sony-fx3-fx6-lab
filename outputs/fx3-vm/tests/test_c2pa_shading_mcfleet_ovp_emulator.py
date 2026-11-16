#!/usr/bin/env python3
"""Phase 107 Test Suite — Stage 18 C2PA 2.1 `cnflasha` Key-Vault Firewall,
E-Mount 12-Pin Lens Shading/CA/Distortion Polynomial vs Unchipped PL-Mount
Arbitrator, Monitor & Control 4-Cam Wired Gigabit USB-LAN Fleet Sync, &
G31/G32 Dummy-Battery OVP Crowbar + PL Cantilever HIL.

Exercises 36 fast unit, simulation, fail-closed guard, Stage 18 suite
integration, CLI, and source-hygiene tests across BOTH Local Donor
(`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import c2pa_shading_mcfleet_ovp_emulator as p107  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p107.run_phase107_c2pa_shading_mcfleet_ovp_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase107DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p107.inspect_phase107_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 30)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p107.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p107.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p107.is_forced_clean_room(env))
        paths = p107.resolve_phase107_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p107.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p107.inspect_phase107_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p107.is_forced_clean_room():
            audit = p107.inspect_phase107_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p107.resolve_phase107_donor_paths()
        audit = p107.inspect_phase107_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p107.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p107.ENV_MAC_WORK_ROOT: "/nonexistent_phase107_mac_work_root",
            p107.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase107_main_work_root",
        }
        audit = p107.inspect_phase107_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_key_reads_and_zero_damage(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["cnflasha_mutation_bytes"], 0)
        self.assertEqual(red["private_key_reads"], 0)
        self.assertEqual(red["private_key_exports"], 0)
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["cxd90057_pmic_damage_events"], 0)
        self.assertEqual(red["emount_flange_damage_events"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestC2paCnflashaKeyVaultFirewall(unittest.TestCase):
    """Verify C2PA 2.1 cnflasha/RPMB key-vault read-only sandbox & non-forgery guard."""

    def test_06_stage_b_clean_room_finalize_tags_honest_nonrealtimemeta_with_zero_vault_reads(self) -> None:
        v = p107.evaluate_c2pa_cnflasha_firewall(
            operation="FINALIZE_CLIP",
            target_path="tmpfs://stage_b/C0001M01.XML",
            requested_identity="FX3_CLEAN_ROOM_RESEARCH",
            claim_hardware_attestation=False,
            clip_id="C0001",
        )
        self.assertTrue(v.passed)
        self.assertEqual(v.status, "VERIFIED_SANDBOXED_RESEARCH_PROVENANCE")
        self.assertEqual(v.c2pa_spec_version, "2.1")
        self.assertEqual(v.cnflasha_mutations, 0)
        self.assertEqual(v.rpmb_mutations, 0)
        self.assertEqual(v.private_key_reads, 0)
        self.assertEqual(v.private_key_exports, 0)
        self.assertFalse(v.hardware_attestation_claimed)
        self.assertEqual(v.provenance_mode, "CLEAN_ROOM_RESEARCH_UNATTESTED")
        self.assertIn("<C2PAVersion>2.1</C2PAVersion>", v.nonrealtimemeta_tag_xml)
        self.assertIn("<HardwareAttestationClaimed>false</HardwareAttestationClaimed>", v.nonrealtimemeta_tag_xml)
        self.assertIn("<KeyVaultIsolation>CNFLASHA_RPMB_ZERO_ACCESS</KeyVaultIsolation>", v.nonrealtimemeta_tag_xml)

    def test_07_private_key_read_and_export_operations_blocked_fail_closed(self) -> None:
        for op in ("READ_KEY", "EXPORT_KEY"):
            v = p107.evaluate_c2pa_cnflasha_firewall(
                operation=op,
                target_path="/cert/device_priv.key",
                requested_identity="FX3_CLEAN_ROOM_RESEARCH",
            )
            self.assertFalse(v.passed)
            self.assertIn("BLOCKED_C2PA_PRIVATE_KEY_ACCESS", v.violation_codes)
            self.assertEqual(v.private_key_reads, 0)
            self.assertEqual(v.private_key_exports, 0)

    def test_08_cnflasha_rpmb_spacc_rq_lic_write_and_mount_rw_blocked_fail_closed(self) -> None:
        for path in ("/dev/cnflasha0", "/dev/mmcblk0rpmb", "/tmp/RQ_LIC.DAT", "0xf7fc0000"):
            v = p107.evaluate_c2pa_cnflasha_firewall(
                operation="WRITE_VAULT",
                target_path=path,
                requested_identity="FX3_CLEAN_ROOM_RESEARCH",
            )
            self.assertFalse(v.passed)
            self.assertIn("BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION", v.violation_codes)
            self.assertEqual(v.cnflasha_mutations, 0)
            self.assertEqual(v.rpmb_mutations, 0)

    def test_09_cross_body_fx6_or_forged_cert_spoofing_blocked_fail_closed(self) -> None:
        for bad_id in ("FX6_FACTORY_ATTESTED_SIGNER", "SONY_PRODUCTION_CA_FORGED"):
            v = p107.evaluate_c2pa_cnflasha_firewall(
                operation="FINALIZE_CLIP",
                target_path="tmpfs://stage_b/C0009M01.XML",
                requested_identity=bad_id,
            )
            self.assertFalse(v.passed)
            self.assertTrue(v.cross_body_spoof_blocked)
            self.assertIn("BLOCKED_CROSS_BODY_CERT_SPOOFING", v.violation_codes)
            self.assertEqual(v.nonrealtimemeta_tag_xml, "")

    def test_10_claiming_hardware_attestation_blocked_as_provenance_forgery(self) -> None:
        v = p107.evaluate_c2pa_cnflasha_firewall(
            operation="FINALIZE_CLIP",
            target_path="tmpfs://stage_b/C0010M01.XML",
            requested_identity="FX3_CLEAN_ROOM_RESEARCH",
            claim_hardware_attestation=True,
        )
        self.assertFalse(v.passed)
        self.assertIn("BLOCKED_C2PA_PROVENANCE_FORGERY", v.violation_codes)
        self.assertFalse(v.hardware_attestation_claimed)

    def test_11_fx6_on_fx3_clean_room_research_identity_allowed_with_honest_tag(self) -> None:
        v = p107.evaluate_c2pa_cnflasha_firewall(
            operation="FINALIZE_CLIP",
            target_path="tmpfs://stage_b/C0011M01.XML",
            requested_identity="FX6_ON_FX3_CLEAN_ROOM_RESEARCH",
            claim_hardware_attestation=False,
            clip_id="C0011",
        )
        self.assertTrue(v.passed)
        self.assertIn("<SignerIdentity>FX6_ON_FX3_CLEAN_ROOM_RESEARCH</SignerIdentity>", v.nonrealtimemeta_tag_xml)

    def test_12_invalid_c2pa_operation_or_path_traversal_raises_domain_error(self) -> None:
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.evaluate_c2pa_cnflasha_firewall(operation="NUKE_VAULT")
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.evaluate_c2pa_cnflasha_firewall(target_path="../../dev/cnflasha0")
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.evaluate_c2pa_cnflasha_firewall(clip_id="   ")


class TestEmountShadingAndUnchippedPlArbitrator(unittest.TestCase):
    """Verify 12-pin E-mount shading/CA/distortion vs unchipped PL <1-frame identity reset."""

    def test_13_sony_fe_24_70_gm2_applies_cos4_vignetting_ca_distortion_and_breathing(self) -> None:
        poly = p107.compute_lens_polynomial_at_radius(p107.LENS_SONY_FE_24_70_GM2, normalized_r=0.85)
        self.assertGreater(poly["shading_gain"], 1.25)
        self.assertGreater(poly["ca_r_scale"], 1.0)
        self.assertLess(poly["ca_b_scale"], 1.0)
        self.assertLess(poly["distortion_k1"], 0.0)
        self.assertGreater(poly["breathing_scale"], 1.0)

    def test_14_hotswap_gm2_to_unchipped_pl_anamorphic_resets_to_identity_under_one_frame(self) -> None:
        res = p107.simulate_lens_shading_hotswap(
            from_lens=p107.LENS_SONY_FE_24_70_GM2,
            to_lens=p107.LENS_MANUAL_PL_ANAMORPHIC_40MM,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_UNCHIPPED_PL_IDENTITY_RESET_LT_1FRAME")
        self.assertEqual(res.from_pins, 12)
        self.assertEqual(res.to_pins, 0)
        self.assertFalse(res.uart_active_after_swap)
        self.assertGreater(res.shading_corner_gain_before, 1.25)
        self.assertEqual(res.shading_corner_gain_after, 1.0)
        self.assertEqual(res.ca_r_scale_after, 1.0)
        self.assertEqual(res.ca_b_scale_after, 1.0)
        self.assertEqual(res.distortion_k1_after, 0.0)
        self.assertEqual(res.distortion_k2_after, 0.0)
        self.assertEqual(res.breathing_scale_after, 1.0)
        self.assertTrue(res.identity_tables_restored)
        self.assertTrue(res.reset_under_one_frame)
        self.assertLess(res.identity_reset_latency_ms, res.frame_period_ms)
        self.assertEqual(res.stale_gm_frames_leaked, 0)
        self.assertEqual(res.calibration_mutation_bytes, 0)

    def test_15_hotswap_reverse_pl_to_gm2_restores_12pin_polynomials(self) -> None:
        res = p107.simulate_lens_shading_hotswap(
            from_lens=p107.LENS_MANUAL_PL_ANAMORPHIC_40MM,
            to_lens=p107.LENS_SONY_FE_24_70_GM2,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_12PIN_EMOUNT_POLYNOMIAL_APPLIED")
        self.assertTrue(res.uart_active_after_swap)
        self.assertEqual(res.shading_corner_gain_before, 1.0)
        self.assertGreater(res.shading_corner_gain_after, 1.25)
        self.assertGreater(res.ca_r_scale_after, 1.0)
        self.assertEqual(res.stale_gm_frames_leaked, 0)

    def test_16_stale_gm_coefficient_retention_fault_blocked_with_zero_leaked_frames(self) -> None:
        res = p107.simulate_lens_shading_hotswap(
            from_lens=p107.LENS_SONY_FE_24_70_GM2,
            to_lens=p107.LENS_MANUAL_PL_PRIME_50MM,
            inject_stale_coeff_retention=True,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_STALE_GM_SHADING_ON_UNCHIPPED_PL")
        self.assertEqual(res.shading_corner_gain_after, 1.0)
        self.assertEqual(res.stale_gm_frames_leaked, 0)

    def test_17_corrupt_12pin_lens_uart_eeprom_fails_closed_to_identity(self) -> None:
        corrupt_gm2 = p107.LensOpticalProfile(
            lens_id="SEL2470GM2_CORRUPT_EEPROM",
            mount_type="E_MOUNT_12PIN",
            electronic_pins_active=12,
            focal_length_mm=24.0,
            aperture_t_or_f=2.8,
            focus_distance_m=0.5,
            cos4_theta_corner_rad=0.425,
            ca_r_delta=0.0018,
            ca_b_delta=-0.0016,
            distortion_k1=-0.042,
            distortion_k2=0.011,
            breathing_coeff=0.045,
            eeprom_checksum_valid=False,
        )
        res = p107.simulate_lens_shading_hotswap(
            from_lens=p107.LENS_MANUAL_PL_PRIME_50MM,
            to_lens=corrupt_gm2,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_CORRUPT_LENS_UART_EEPROM")
        self.assertEqual(res.shading_corner_gain_after, 1.0)
        self.assertFalse(res.uart_active_after_swap)

    def test_18_cos4_vignetting_gain_increases_monotonically_with_radius(self) -> None:
        g_center = p107.compute_lens_polynomial_at_radius(p107.LENS_SONY_FE_24_70_GM2, normalized_r=0.0)["shading_gain"]
        g_mid = p107.compute_lens_polynomial_at_radius(p107.LENS_SONY_FE_24_70_GM2, normalized_r=0.5)["shading_gain"]
        g_edge = p107.compute_lens_polynomial_at_radius(p107.LENS_SONY_FE_24_70_GM2, normalized_r=1.0)["shading_gain"]
        self.assertEqual(g_center, 1.0)
        self.assertLess(g_center, g_mid)
        self.assertLess(g_mid, g_edge)

    def test_19_invalid_lens_radius_or_pin_count_raises_domain_error(self) -> None:
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.compute_lens_polynomial_at_radius(p107.LENS_SONY_FE_24_70_GM2, normalized_r=1.2)
        bad_pins = p107.LensOpticalProfile(
            lens_id="BAD_PINS",
            mount_type="E_MOUNT_12PIN",
            electronic_pins_active=8,
            focal_length_mm=35.0,
            aperture_t_or_f=1.4,
            focus_distance_m=0.5,
            cos4_theta_corner_rad=0.2,
            ca_r_delta=0.0,
            ca_b_delta=0.0,
            distortion_k1=0.0,
            distortion_k2=0.0,
            breathing_coeff=0.0,
        )
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.compute_lens_polynomial_at_radius(bad_pins)


class TestMonitorControl4CamWiredFleetSync(unittest.TestCase):
    """Verify 4-camera wired Gigabit USB-LAN Monitor & Control fleet sync under P12."""

    def test_20_4cam_wired_gigabit_cdc_ncm_fleet_sync_passes_under_p12_rf_fence(self) -> None:
        res = p107.simulate_mc_4cam_wired_fleet_sync()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_4CAM_WIRED_GIGABIT_FLEET_SYNC")
        self.assertEqual(res.camera_count, 4)
        self.assertEqual(res.master_camera_id, "A-Cam")
        self.assertEqual(res.nic_driver, "CDC_NCM_RTL8153")
        self.assertEqual(res.link_speed_mbps, 1000)
        self.assertEqual(res.ptp_ip_port, 15740)
        self.assertLess(res.gang_rec_start_skew_ms, 1.0)
        self.assertLess(res.gang_rec_stop_skew_ms, 1.0)
        self.assertEqual(res.frame_sync_offset_frames, 0)
        self.assertEqual(res.synchronized_streams, ("FALSE_COLOR", "WAVEFORM", "FOCUS_MAP"))
        self.assertGreater(res.telemetry_packets_sent, 2000)
        self.assertTrue(res.p12_rf_fenced)
        self.assertTrue(res.bk4_airplane_shadow_active)
        self.assertEqual(res.wifi_rf_tx_packets, 0)
        self.assertEqual(res.bt_rf_tx_packets, 0)
        self.assertEqual(res.wf12_00342260_hits, 0)

    def test_21_wifi_fallback_or_bt_rf_enabled_blocked_by_p12_with_zero_wf12_hits(self) -> None:
        res_fb = p107.simulate_mc_4cam_wired_fleet_sync(allow_wifi_fallback=True)
        self.assertFalse(res_fb.passed)
        self.assertIn("BLOCKED_P12_RF_FENCE_BREACH", res_fb.violation_codes)
        self.assertEqual(res_fb.wf12_00342260_hits, 0)

        rf_node = p107.FleetCameraNode(
            camera_id="C-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.103",
            nic_driver="CDC_NCM_RTL8153",
            link_speed_mbps=1000,
            ptp_offset_us=50.0,
            wifi_rf_enabled=True,
        )
        res_rf = p107.simulate_mc_4cam_wired_fleet_sync(
            fleet=(p107.DEFAULT_4CAM_FLEET[0], p107.DEFAULT_4CAM_FLEET[1], rf_node, p107.DEFAULT_4CAM_FLEET[3])
        )
        self.assertFalse(res_rf.passed)
        self.assertIn("BLOCKED_P12_RF_FENCE_BREACH", res_rf.violation_codes)

    def test_22_unsupported_rndis_nic_or_sub_gigabit_or_missing_gateway_blocked(self) -> None:
        res_gw = p107.simulate_mc_4cam_wired_fleet_sync(gateway_ip="")
        self.assertFalse(res_gw.passed)
        self.assertIn("BLOCKED_FLEET_USB_NIC_POLICY", res_gw.violation_codes)

        bad_nic = p107.FleetCameraNode(
            camera_id="D-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.104",
            nic_driver="CDC_ECM_LEGACY",
            link_speed_mbps=100,
            ptp_offset_us=40.0,
        )
        res_nic = p107.simulate_mc_4cam_wired_fleet_sync(
            fleet=(p107.DEFAULT_4CAM_FLEET[0], p107.DEFAULT_4CAM_FLEET[1], p107.DEFAULT_4CAM_FLEET[2], bad_nic)
        )
        self.assertFalse(res_nic.passed)
        self.assertIn("BLOCKED_FLEET_USB_NIC_POLICY", res_nic.violation_codes)

    def test_23_duplicate_camera_ip_or_ptp_skew_over_threshold_blocked(self) -> None:
        dup_ip = p107.FleetCameraNode(
            camera_id="B-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.101",
            nic_driver="CDC_NCM_RTL8153",
            link_speed_mbps=1000,
            ptp_offset_us=45.0,
        )
        res_dup = p107.simulate_mc_4cam_wired_fleet_sync(
            fleet=(p107.DEFAULT_4CAM_FLEET[0], dup_ip, p107.DEFAULT_4CAM_FLEET[2], p107.DEFAULT_4CAM_FLEET[3])
        )
        self.assertFalse(res_dup.passed)
        self.assertIn("BLOCKED_FLEET_SYNC_SKEW_OR_COLLISION", res_dup.violation_codes)

        high_skew = p107.FleetCameraNode(
            camera_id="B-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.102",
            nic_driver="CDC_NCM_RTL8153",
            link_speed_mbps=1000,
            ptp_offset_us=1200.0,
        )
        res_skew = p107.simulate_mc_4cam_wired_fleet_sync(
            fleet=(p107.DEFAULT_4CAM_FLEET[0], high_skew, p107.DEFAULT_4CAM_FLEET[2], p107.DEFAULT_4CAM_FLEET[3])
        )
        self.assertFalse(res_skew.passed)
        self.assertIn("BLOCKED_FLEET_SYNC_SKEW_OR_COLLISION", res_skew.violation_codes)

    def test_24_incomplete_false_color_waveform_focus_map_telemetry_blocked(self) -> None:
        no_wf = p107.FleetCameraNode(
            camera_id="D-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.104",
            nic_driver="CDC_NCM_RTL8153",
            link_speed_mbps=1000,
            ptp_offset_us=60.0,
            waveform_active=False,
        )
        res = p107.simulate_mc_4cam_wired_fleet_sync(
            fleet=(p107.DEFAULT_4CAM_FLEET[0], p107.DEFAULT_4CAM_FLEET[1], p107.DEFAULT_4CAM_FLEET[2], no_wf)
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_FLEET_TELEMETRY_STREAM_INCOMPLETE", res.violation_codes)

    def test_25_invalid_fleet_size_or_negative_ptp_offset_raises_domain_error(self) -> None:
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.simulate_mc_4cam_wired_fleet_sync(fleet=p107.DEFAULT_4CAM_FLEET[:2])
        neg_ptp = p107.FleetCameraNode(
            camera_id="B-Cam",
            body_profile="FX6_ON_FX3",
            ip_addr="192.168.10.102",
            nic_driver="CDC_NCM_RTL8153",
            link_speed_mbps=1000,
            ptp_offset_us=-5.0,
        )
        with self.assertRaises(p107.C2paShadingMcFleetOvpError):
            p107.simulate_mc_4cam_wired_fleet_sync(
                fleet=(p107.DEFAULT_4CAM_FLEET[0], neg_ptp, p107.DEFAULT_4CAM_FLEET[2], p107.DEFAULT_4CAM_FLEET[3])
            )


class TestG31G32OvpCrowbarAndPlCantileverHil(unittest.TestCase):
    """Verify G31/G32 16.8V/26V dummy-battery OVP crowbar (<50us) & PL cantilever interlock."""

    def test_26_nominal_7v8_and_light_115nm_lens_pass_without_crowbar_or_interlock(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(
            dummy_batt_input_v=7.8,
            lens_cantilever_torque_nm=1.15,
            rod_support_engaged=False,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_PMIC_AND_EMOUNT_SAFE")
        self.assertFalse(res.ovp_crowbar_tripped)
        self.assertFalse(res.boot_rail_isolated)
        self.assertFalse(res.mount_interlock_tripped)
        self.assertFalse(res.ibis_coil_energize_blocked)
        self.assertEqual(res.cxd90057_pmic_damage_events, 0)
        self.assertEqual(res.emount_flange_damage_events, 0)

    def test_27_g31_16v8_unregulated_dummy_battery_trips_ovp_crowbar_under_50us(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(dummy_batt_input_v=16.8)
        self.assertFalse(res.passed)
        self.assertEqual(res.dummy_batt_fault_tag, "G31_16V8_UNREGULATED")
        self.assertTrue(res.ovp_crowbar_tripped)
        self.assertTrue(res.boot_rail_isolated)
        self.assertLess(res.ovp_isolation_latency_us, p107.OVP_CROWBAR_MAX_LATENCY_US)
        self.assertLess(res.pmic_rail_peak_v, p107.CXD90057_PMIC_ABS_MAX_V)
        self.assertIn("BLOCKED_G31_G32_DUMMY_BATT_OVP_CROWBAR", res.violation_codes)
        self.assertEqual(res.cxd90057_pmic_damage_events, 0)

    def test_28_g32_26v_surge_trips_ovp_crowbar_under_50us_with_zero_pmic_damage(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(dummy_batt_input_v=26.0)
        self.assertFalse(res.passed)
        self.assertEqual(res.dummy_batt_fault_tag, "G32_26V_SURGE")
        self.assertTrue(res.ovp_crowbar_tripped)
        self.assertTrue(res.boot_rail_isolated)
        self.assertLess(res.ovp_isolation_latency_us, 25.0)
        self.assertLess(res.pmic_rail_peak_v, p107.CXD90057_PMIC_ABS_MAX_V)
        self.assertIn("BLOCKED_G31_G32_DUMMY_BATT_OVP_CROWBAR", res.violation_codes)
        self.assertEqual(res.cxd90057_pmic_damage_events, 0)

    def test_29_unsupported_pl_cantilever_over_1v8_nm_trips_mount_and_ibis_interlock(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(
            dummy_batt_input_v=7.8,
            lens_cantilever_torque_nm=2.60,
            rod_support_engaged=False,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.mount_interlock_tripped)
        self.assertTrue(res.ibis_coil_energize_blocked)
        self.assertGreater(res.effective_flange_torque_nm, p107.EMOUNT_CANTILEVER_MAX_NM)
        self.assertIn("BLOCKED_UNSUPPORTED_PL_CANTILEVER_OVERLOAD", res.violation_codes)
        self.assertEqual(res.emount_flange_damage_events, 0)

    def test_30_15mm_rod_support_reduces_effective_flange_torque_below_1v8_nm(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(
            dummy_batt_input_v=7.8,
            lens_cantilever_torque_nm=2.60,
            rod_support_engaged=True,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.mount_interlock_tripped)
        self.assertLess(res.effective_flange_torque_nm, p107.EMOUNT_CANTILEVER_MAX_NM)
        self.assertEqual(res.emount_flange_damage_events, 0)

    def test_31_combined_g32_26v_and_pl_cantilever_overload_accumulates_both_codes(self) -> None:
        res = p107.simulate_g31_g32_ovp_and_cantilever_hil(
            dummy_batt_input_v=26.0,
            lens_cantilever_torque_nm=3.40,
            rod_support_engaged=False,
        )
        self.assertFalse(res.passed)
        self.assertEqual(len(res.violation_codes), 2)
        self.assertIn("BLOCKED_G31_G32_DUMMY_BATT_OVP_CROWBAR", res.violation_codes)
        self.assertIn("BLOCKED_UNSUPPORTED_PL_CANTILEVER_OVERLOAD", res.violation_codes)
        self.assertEqual(res.cxd90057_pmic_damage_events, 0)
        self.assertEqual(res.emount_flange_damage_events, 0)


class TestStage18SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 18 suite integration, CLI flags, determinism & strict hygiene."""

    def test_32_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p107.run_phase107_c2pa_shading_mcfleet_ovp_audit(force_clean_room=True)
        rep2 = p107.run_phase107_c2pa_shading_mcfleet_ovp_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_33_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--c2pa-matrix"],
            ["--clean-room", "--shading-matrix"],
            ["--clean-room", "--mcfleet-matrix"],
            ["--clean-room", "--ovp-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p107.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_34_suite_in_process_stage18_and_skip_phase107_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage18_phase107_c2pa_shading_mcfleet_ovp", rep_on)
        self.assertTrue(rep_on["stage18_phase107_c2pa_shading_mcfleet_ovp"]["all_checks_passed"])

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase107_c2pa_shading_mcfleet_ovp=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage18_phase107_c2pa_shading_mcfleet_ovp", rep_skip)

    def test_35_suite_subprocess_summary_and_skip_phase107_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("c2pa_shad_mc_ovp=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase107",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("c2pa_shad_mc_ovp=", proc_skip.stdout)

    def test_36_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "c2pa_shading_mcfleet_ovp_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
