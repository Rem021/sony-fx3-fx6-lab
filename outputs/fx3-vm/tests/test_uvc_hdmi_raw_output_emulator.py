#!/usr/bin/env python3
"""Phase 63 Test Suite — Stage 8 HDMI Type-A 4264x2408 16-bit Linear RAW EDID,
MLUT Clean-Feed & USB-C Gadget Mode Arbitrator.

Exercises 30 fast unit, protocol, arbitration, Stage 8 integration, CLI, and
source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import uvc_hdmi_raw_output_emulator as p63  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p63.run_phase63_hdmi_uvc_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase63DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p63.inspect_hdmi_uvc_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p63.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p63.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p63.is_forced_clean_room(env))
        paths = p63.resolve_phase63_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p63.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p63.inspect_hdmi_uvc_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p63.is_forced_clean_room():
            audit = p63.inspect_hdmi_uvc_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p63.resolve_phase63_donor_paths()
        audit = p63.inspect_hdmi_uvc_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p63.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p63.ENV_MAC_WORK_ROOT: "/nonexistent_phase63_mac_work_root",
            p63.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase63_main_work_root",
        }
        audit = p63.inspect_hdmi_uvc_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_emmc_writes_zero_sdi_faults(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["sdi_transceiver_faults"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestEdidSynthesisAndHdmiRaw16Handshake(unittest.TestCase):
    """Verify 256B E-EDID synthesis, checksums, RAW16 handshake, MLUT clean-feed, and 12G-SDI containment."""

    def test_06_pnp_id_roundtrip_and_invalid_rejected(self) -> None:
        for code in ("ATM", "SHD", "SNY"):
            raw2 = p63.encode_pnp_id(code)
            self.assertEqual(len(raw2), 2)
            self.assertEqual(p63.decode_pnp_id(raw2), code)
        with self.assertRaises(p63.EdidValidationError):
            p63.encode_pnp_id("atm")
        with self.assertRaises(p63.EdidValidationError):
            p63.encode_pnp_id("A1")

    def test_07_atomos_ninja_raw16_edid_256b_header_and_mod256_checksum(self) -> None:
        hpd, edid = p63.read_sink_edid(p63.HDMI_SINK_ATOMOS_NINJA_RAW16)
        self.assertEqual(hpd, 1)
        self.assertEqual(len(edid), 256)
        self.assertEqual(edid[:8], bytes.fromhex("00ffffffffffff00"))
        self.assertEqual(sum(edid[:128]) % 256, 0)
        self.assertEqual(sum(edid[128:256]) % 256, 0)

        parsed = p63.parse_and_verify_edid(edid)
        self.assertTrue(parsed.valid)
        self.assertEqual(parsed.manufacturer_id, "ATM")
        self.assertEqual(parsed.monitor_name, "ATOMOS NINJA")
        self.assertEqual(parsed.extension_count, 1)
        self.assertTrue(parsed.ycbcr422_supported)
        self.assertTrue(parsed.hdmi_vsdb_present)
        self.assertTrue(parsed.hf_vsdb_present)
        self.assertTrue(parsed.prores_raw_vsdb_present)
        self.assertEqual((parsed.raw16_width, parsed.raw16_height), (4264, 2408))
        self.assertEqual(parsed.raw16_max_fps_label, "59.94p")
        self.assertTrue(parsed.smpte_12m_tc_trigger_supported)

    def test_08_smallhd_cine_10bit_422_edid_256b_header_and_mod256_checksum(self) -> None:
        hpd, edid = p63.read_sink_edid(p63.HDMI_SINK_SMALLHD_CINE_10BIT_422)
        self.assertEqual(hpd, 1)
        self.assertEqual(len(edid), 256)
        self.assertEqual(edid[:8], bytes.fromhex("00ffffffffffff00"))
        self.assertEqual(sum(edid[:128]) % 256, 0)
        self.assertEqual(sum(edid[128:256]) % 256, 0)

        parsed = p63.parse_and_verify_edid(edid)
        self.assertTrue(parsed.valid)
        self.assertEqual(parsed.manufacturer_id, "SHD")
        self.assertEqual(parsed.monitor_name, "SMALLHD CINE")
        self.assertTrue(parsed.ycbcr422_supported)
        self.assertFalse(parsed.prores_raw_vsdb_present)
        self.assertEqual((parsed.raw16_width, parsed.raw16_height), (0, 0))
        self.assertIn(97, parsed.cea_vics)
        self.assertIn(16, parsed.cea_vics)

    def test_09_edid_parser_rejects_corrupt_block0_and_block1_checksums(self) -> None:
        base = bytearray(p63.synthesize_sink_edid(p63.HDMI_SINK_ATOMOS_NINJA_RAW16))
        bad_b0 = bytearray(base)
        bad_b0[127] ^= 0x01
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(bytes(bad_b0))

        bad_b1 = bytearray(base)
        bad_b1[255] ^= 0x01
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(bytes(bad_b1))

    def test_10_edid_parser_rejects_bad_header_length_ext_count_and_cea_tag(self) -> None:
        valid = p63.synthesize_sink_edid(p63.HDMI_SINK_SMALLHD_CINE_10BIT_422)
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(valid[:128])

        bad_hdr = bytearray(valid)
        bad_hdr[0] = 0xFF
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(bytes(bad_hdr))

        bad_ext = bytearray(valid)
        bad_ext[0x7E] = 0
        bad_ext[127] = p63.compute_edid_checksum(bytes(bad_ext[:127]))
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(bytes(bad_ext))

        bad_tag = bytearray(valid)
        bad_tag[128] = 0x70
        bad_tag[255] = p63.compute_edid_checksum(bytes(bad_tag[128:255]))
        with self.assertRaises(p63.EdidValidationError):
            p63.parse_and_verify_edid(bytes(bad_tag))

    def test_11_atomos_ninja_negotiates_4264x2408_16bit_raw_5994p_and_smpte_12m_tc(self) -> None:
        res = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_ATOMOS_NINJA_RAW16,
            requested_mode=p63.HDMI_MODE_RAW16,
            requested_resolution="4264x2408",
            requested_fps="59.94p",
            hdmi_tc_on=True,
            rec_trigger_active=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "HDMI_TYPE_A_RAW16_4264x2408_NEGOTIATED")
        self.assertEqual(res.hpd, 1)
        self.assertTrue(res.edid_valid)
        self.assertTrue(res.raw16_active)
        self.assertFalse(res.raw16_rejected)
        self.assertFalse(res.fallback_used)
        self.assertEqual(res.negotiated_resolution, "4264x2408")
        self.assertEqual(res.negotiated_fps, "59.94p")
        self.assertTrue(res.prores_raw_vsdb_present)
        self.assertTrue(res.smpte_12m_tc_trigger_active)
        self.assertFalse(res.black_screen)

    def test_12_atomos_raw16_keeps_lcd_mlut_independent_and_hdmi_mlut_off(self) -> None:
        res = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_ATOMOS_NINJA_RAW16,
            requested_mode=p63.HDMI_MODE_RAW16,
            lcd_mlut_on=True,
            hdmi_mlut_on=True,  # Linear RAW must not burn LUT into HDMI feed
        )
        self.assertTrue(res.raw16_active)
        self.assertTrue(res.lcd_mlut_active)
        self.assertFalse(res.hdmi_mlut_active)
        self.assertTrue(res.hdmi_clean_feed)

    def test_13_smallhd_cine_4k_and_1080p_10bit_422_mlut_on_off_and_clean_feed_toggle(self) -> None:
        r_clean = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_SMALLHD_CINE_10BIT_422,
            requested_mode=p63.HDMI_MODE_10BIT_422,
            requested_resolution="3840x2160",
            requested_fps="59.94p",
            lcd_mlut_on=True,
            hdmi_mlut_on=True,
            hdmi_info_display_on=False,
        )
        self.assertEqual(r_clean.negotiated_resolution, "3840x2160")
        self.assertEqual(r_clean.negotiated_mode, p63.HDMI_MODE_10BIT_422)
        self.assertTrue(r_clean.hdmi_mlut_active)
        self.assertTrue(r_clean.lcd_mlut_active)
        self.assertTrue(r_clean.hdmi_clean_feed)

        r_osd = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_SMALLHD_CINE_10BIT_422,
            requested_mode=p63.HDMI_MODE_10BIT_422,
            requested_resolution="1920x1080",
            requested_fps="23.98p",
            lcd_mlut_on=True,
            hdmi_mlut_on=False,
            hdmi_info_display_on=True,
        )
        self.assertEqual(r_osd.negotiated_resolution, "1920x1080")
        self.assertEqual(r_osd.negotiated_fps, "23.98p")
        self.assertFalse(r_osd.hdmi_mlut_active)
        self.assertTrue(r_osd.lcd_mlut_active)
        self.assertFalse(r_osd.hdmi_clean_feed)

    def test_14_smallhd_rejects_16bit_raw_cleanly_with_ycbcr422_fallback_no_black_screen(self) -> None:
        res = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_SMALLHD_CINE_10BIT_422,
            requested_mode=p63.HDMI_MODE_RAW16,
            requested_resolution="4264x2408",
            requested_fps="59.94p",
            hdmi_mlut_on=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "HDMI_RAW16_REJECTED_FALLBACK_YCBCR_422")
        self.assertFalse(res.raw16_active)
        self.assertTrue(res.raw16_rejected)
        self.assertTrue(res.fallback_used)
        self.assertFalse(res.black_screen)
        self.assertTrue(res.hdmi_output_active)
        self.assertEqual(res.negotiated_mode, p63.HDMI_MODE_10BIT_422)
        self.assertEqual(res.negotiated_resolution, "3840x2160")

    def test_15_hdmi_hot_unplug_mid_recording_returns_to_gpe0_1024x540_zero_dropped_frames(self) -> None:
        hpd, blob = p63.read_sink_edid(p63.HDMI_SINK_DISCONNECTED)
        self.assertEqual(hpd, 0)
        self.assertEqual(blob, b"")

        res = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_DISCONNECTED,
            requested_mode=p63.HDMI_MODE_RAW16,
            recording_active=True,
            lcd_mlut_on=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "HDMI_HPD_0_RETURNED_TO_INTERNAL_LCD_GPE0")
        self.assertEqual(res.hpd, 0)
        self.assertFalse(res.hdmi_output_active)
        self.assertTrue(res.internal_lcd_active)
        self.assertEqual(res.internal_lcd_resolution, "1024x540")
        self.assertEqual(res.internal_lcd_gpe0_phys, "0x41e001000")
        self.assertEqual(res.dropped_internal_xavc_frames, 0)
        self.assertFalse(res.black_screen)
        self.assertEqual(res.wdt_resets, 0)

    def test_16_corrupt_sink_edid_falls_back_safely_without_black_screen_or_wdt(self) -> None:
        bad = bytearray(p63.synthesize_sink_edid(p63.HDMI_SINK_ATOMOS_NINJA_RAW16))
        bad[127] ^= 0x55
        res = p63.negotiate_hdmi_type_a_handshake(
            sink_id=p63.HDMI_SINK_ATOMOS_NINJA_RAW16,
            requested_mode=p63.HDMI_MODE_RAW16,
            edid_override=bytes(bad),
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "EDID_CHECKSUM_INVALID_SAFE_FALLBACK")
        self.assertFalse(res.edid_valid)
        self.assertTrue(res.fallback_used)
        self.assertFalse(res.black_screen)
        self.assertEqual(res.negotiated_resolution, "1920x1080")
        self.assertEqual(res.wdt_resets, 0)

    def test_17_fx6_12g_sdi_sub_output_settings_safely_contained_noop_on_fx3(self) -> None:
        for sink_id in p63.ALL_HDMI_SINKS:
            res = p63.negotiate_hdmi_type_a_handshake(
                sink_id=sink_id,
                fx6_sdi_sub_output_requested=True,
            )
            self.assertFalse(res.sdi_hw_supported)
            self.assertEqual(res.sdi_feature_manager_state, p63.FX3_SDI_FEATURE_STATUS)
            self.assertTrue(res.sdi_contained_noop)
            self.assertEqual(res.sdi_transceiver_faults, 0)

    def test_18_hdmi_invalid_sink_mode_or_fps_raises_config_error(self) -> None:
        with self.assertRaises(p63.HdmiConfigError):
            p63.negotiate_hdmi_type_a_handshake(sink_id="UNKNOWN_MONITOR")
        with self.assertRaises(p63.HdmiConfigError):
            p63.negotiate_hdmi_type_a_handshake(
                sink_id=p63.HDMI_SINK_ATOMOS_NINJA_RAW16,
                requested_mode="8BIT_CVBS",
            )
        with self.assertRaises(p63.HdmiConfigError):
            p63.negotiate_hdmi_type_a_handshake(
                sink_id=p63.HDMI_SINK_ATOMOS_NINJA_RAW16,
                requested_fps="144p",
            )


class TestUsbCGadgetModeArbitrator(unittest.TestCase):
    """Verify USB-C mutual exclusion, UVC/UAC profiles, P12 wireless silence, and MSC/DFU locks."""

    def test_19_usbc_uvc_uac_4k30_and_1080p60_binding_and_kernel_modules(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        r4k = arb.bind_mode(p63.USB_MODE_UVC_UAC, uvc_profile=p63.UVC_PROFILE_4K30)
        self.assertTrue(r4k.allowed)
        self.assertEqual(r4k.resulting_mode, p63.USB_MODE_UVC_UAC)
        self.assertEqual(r4k.active_gadgets_count, 1)
        self.assertEqual(r4k.uvc_resolution, "3840x2160")
        self.assertEqual(r4k.uvc_fps, "29.97p")
        self.assertIn("usb_f_uvc.ko", r4k.bound_kernel_modules)
        self.assertIn("usb_f_uac2.ko", r4k.bound_kernel_modules)

        r1080 = arb.switch_mode(p63.USB_MODE_UVC_UAC, uvc_profile=p63.UVC_PROFILE_1080P60)
        self.assertTrue(r1080.allowed)
        self.assertEqual(r1080.uvc_resolution, "1920x1080")
        self.assertEqual(r1080.uvc_fps, "59.94p")
        self.assertEqual(r1080.active_gadgets_count, 1)

    def test_20_usbc_strict_mutual_exclusion_rejects_second_gadget_without_detach(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        arb.bind_mode(p63.USB_MODE_UVC_UAC, uvc_profile=p63.UVC_PROFILE_1080P60)
        conflict = arb.bind_mode(p63.USB_MODE_USB_LAN_NCM)
        self.assertFalse(conflict.allowed)
        self.assertEqual(conflict.status, "BLOCKED_MUTUAL_EXCLUSION_ACTIVE_GADGET")
        self.assertEqual(conflict.resulting_mode, p63.USB_MODE_UVC_UAC)
        self.assertEqual(conflict.active_gadgets_count, 1)

        det = arb.detach()
        self.assertTrue(det.allowed)
        self.assertEqual(det.resulting_mode, p63.USB_MODE_DETACHED)
        self.assertEqual(det.active_gadgets_count, 0)

        ok = arb.bind_mode(p63.USB_MODE_USB_LAN_NCM, shooting_active=True, recording_active=True)
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.active_gadgets_count, 1)

    def test_21_usbc_switch_mode_atomically_transitions_uvc_to_usblan_ncm_to_crsdk_ptp(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        arb.bind_mode(p63.USB_MODE_UVC_UAC, uvc_profile=p63.UVC_PROFILE_4K30)
        r_ncm = arb.switch_mode(p63.USB_MODE_USB_LAN_NCM, shooting_active=True, recording_active=True)
        self.assertTrue(r_ncm.allowed)
        self.assertEqual(r_ncm.resulting_mode, p63.USB_MODE_USB_LAN_NCM)
        self.assertIn("cdc_ncm.ko", r_ncm.bound_kernel_modules)
        self.assertEqual(r_ncm.active_gadgets_count, 1)

        r_ptp = arb.switch_mode(p63.USB_MODE_CRSDK_PTP, shooting_active=True, recording_active=True)
        self.assertTrue(r_ptp.allowed)
        self.assertEqual(r_ptp.resulting_mode, p63.USB_MODE_CRSDK_PTP)
        self.assertIn("usbg_stillimage.ko", r_ptp.bound_kernel_modules)
        self.assertEqual(r_ptp.active_gadgets_count, 1)

    def test_22_usbc_blocks_msc_during_shooting_and_preserves_active_safe_mode(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        arb.bind_mode(p63.USB_MODE_CRSDK_PTP, shooting_active=True, recording_active=True)
        blocked = arb.switch_mode(p63.USB_MODE_MSC, shooting_active=True, recording_active=True)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.status, "BLOCKED_MSC_DURING_SHOOTING")
        self.assertEqual(blocked.resulting_mode, p63.USB_MODE_CRSDK_PTP)
        self.assertFalse(blocked.persistent_emmc_writes_authorized)
        self.assertEqual(blocked.cp_mutation_bytes, 0)
        self.assertEqual(blocked.wbi_mutation_bytes, 0)

    def test_23_usbc_blocks_dfu_raw_flash_and_persistent_emmc_writes_unconditionally(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        dfu = arb.bind_mode(p63.USB_MODE_DFU_FLASH, shooting_active=False, recording_active=False)
        self.assertFalse(dfu.allowed)
        self.assertEqual(dfu.status, "BLOCKED_DFU_RAW_FLASH_FORBIDDEN")
        self.assertEqual(dfu.active_gadgets_count, 0)
        self.assertFalse(dfu.persistent_emmc_writes_authorized)

        emmc = arb.bind_mode(p63.USB_MODE_MSC, shooting_active=False, emmc_write_requested=True)
        self.assertFalse(emmc.allowed)
        self.assertEqual(emmc.status, "BLOCKED_PERSISTENT_EMMC_WRITE_FORBIDDEN")
        self.assertFalse(emmc.persistent_emmc_writes_authorized)

    def test_24_usbc_idle_msc_is_strictly_readonly_emmc_unauthorized(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        idle_msc = arb.bind_mode(p63.USB_MODE_MSC, shooting_active=False, recording_active=False)
        self.assertTrue(idle_msc.allowed)
        self.assertEqual(idle_msc.resulting_mode, p63.USB_MODE_MSC)
        self.assertIn("usb_f_mass_storage.ko", idle_msc.bound_kernel_modules)
        self.assertFalse(idle_msc.persistent_emmc_writes_authorized)
        self.assertEqual(idle_msc.cp_mutation_bytes, 0)
        self.assertEqual(idle_msc.wbi_mutation_bytes, 0)

    def test_25_usbc_blocks_uvc_while_internal_xavc_recording_active(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        blocked = arb.bind_mode(
            p63.USB_MODE_UVC_UAC,
            uvc_profile=p63.UVC_PROFILE_4K30,
            shooting_active=True,
            recording_active=True,
        )
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.status, "BLOCKED_UVC_WHILE_INTERNAL_XAVC_RECORDING")
        self.assertEqual(blocked.active_gadgets_count, 0)

    def test_26_usbc_enforces_p12_bk4_airplane_silence_and_wf12_immunity(self) -> None:
        arb = p63.UsbCGadgetArbitrator(p12_airplane_mode=True)
        rec = arb.bind_mode(p63.USB_MODE_USB_LAN_NCM, shooting_active=True, recording_active=True)
        self.assertTrue(rec.allowed)
        self.assertTrue(rec.p12_airplane_mode)
        self.assertEqual(rec.bk4_0x019e0012, 0x00)
        self.assertEqual(rec.bk4_0x01a20002, 0x00)
        self.assertFalse(rec.wlan_enabled)
        self.assertEqual(rec.bt_tx_packets, 0)
        self.assertTrue(rec.wf12_00342260_immune)

    def test_27_usbc_arbitration_matrix_all_10_steps_invariant(self) -> None:
        mat = p63.run_usbc_arbitration_matrix()
        self.assertTrue(mat["passed"])
        self.assertEqual(mat["total_transitions"], 10)
        self.assertEqual(mat["allowed_transitions"], 6)
        self.assertEqual(mat["blocked_transitions"], 4)
        self.assertEqual(mat["max_concurrent_gadgets"], 1)
        self.assertTrue(mat["p12_bk4_silent_all_steps"])
        self.assertFalse(mat["persistent_emmc_writes_authorized"])
        self.assertEqual(mat["cp_mutation_bytes"], 0)
        self.assertEqual(mat["wbi_mutation_bytes"], 0)


class TestStage8CoEmulationSuiteCliAndHygiene(unittest.TestCase):
    """Verify Phase 63 audit determinism, Stage 8 suite wiring, CLI, and source hygiene."""

    def test_28_phase63_audit_determinism_and_digest_verification(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p63.run_phase63_hdmi_uvc_audit(force_clean_room=True)
        self.assertEqual(r1, r2)
        self.assertTrue(r1["all_checks_passed"])

        copy_rep = dict(r1)
        recorded = copy_rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_29_coemulation_suite_wires_stage8_and_allows_skip_phase63(self) -> None:
        rep_with = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_phase58_qmp_introspection=False,
                include_phase63_hdmi_raw_uvc=True,
            )
        )
        self.assertTrue(rep_with["all_checks_passed"])
        self.assertIn("stage8_phase63_hdmi_raw_uvc", rep_with)
        s8 = rep_with["stage8_phase63_hdmi_raw_uvc"]
        self.assertTrue(s8["all_checks_passed"])
        self.assertEqual(s8["cp_mutation_bytes"], 0)
        self.assertEqual(s8["wbi_mutation_bytes"], 0)
        self.assertFalse(s8["persistent_emmc_writes_authorized"])
        self.assertEqual(s8["sdi_transceiver_faults"], 0)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_phase58_qmp_introspection=False,
                include_phase63_hdmi_raw_uvc=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage8_phase63_hdmi_raw_uvc", rep_skip)

    def test_30_cli_flags_and_source_hygiene_o_rdonly_no_forbidden_writes_or_port(self) -> None:
        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc = suite.main(
                [
                    "--clean-room",
                    "--skip-phase41",
                    "--skip-phase45",
                    "--skip-phase53",
                    "--skip-phase58",
                    "--skip-phase63",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage8_phase63_hdmi_raw_uvc", rep_skip)

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main(
                [
                    "--clean-room",
                    "--skip-phase41",
                    "--skip-phase45",
                    "--skip-phase53",
                    "--skip-phase58",
                    "--summary",
                ]
            )
        self.assertEqual(rc_sum, 0)
        self.assertIn("hdmi_uvc=CLEAN_ROOM_SYNTHETIC(raw16=4264x2408@59.94p", buf_sum.getvalue())

        buf_p63 = io.StringIO()
        with contextlib.redirect_stdout(buf_p63):
            rc_p63 = p63.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc_p63, 0)
        self.assertIn("[PASS] Phase 63 HDMI RAW16 EDID & USB-C Arbitrator", buf_p63.getvalue())

        buf_edid = io.StringIO()
        with contextlib.redirect_stdout(buf_edid):
            rc_edid = p63.main(["--clean-room", "--edid-info"])
        self.assertEqual(rc_edid, 0)
        edid_info = json.loads(buf_edid.getvalue())
        self.assertEqual(edid_info["atomos_ninja_raw16"]["raw16_width"], 4264)

        forbidden_port = "87" + "68"
        mod_src = (FX3_VM_DIR / "uvc_hdmi_raw_output_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", mod_src)
        self.assertNotIn("os.O_WRONLY", mod_src)
        self.assertNotIn("os.O_RDWR", mod_src)
        self.assertNotIn(forbidden_port, mod_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertNotIn("pkill", mod_src)
        self.assertNotIn("killall", mod_src)
        self.assertIn("CP_MUTATION_BYTES = 0", mod_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", mod_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", mod_src)
        self.assertIn("SDI_TRANSCEIVER_FAULTS = 0", mod_src)


if __name__ == "__main__":
    unittest.main()
