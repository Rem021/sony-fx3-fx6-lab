"""Clean-room unit tests for Phase 38 CrSDK PTP2, MI-Shoe, Multi-Port LTC & SPACC Guard."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.boot_contracts import (
    FX3_KEY_PARTITIONS,
    PartitionEntry,
    SONY_PTBL_ENTRY_COUNT,
    build_sector0_from_partitions,
)
from fx3_safety.crsdk_mishoe_ltc_spacc_guard import (
    CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA,
    LANC_ID_RESISTOR_OHM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PTP_OC_SONY_GET_DEVICE_PROPERTY_VALUE,
    PTP_OC_SONY_SDIO_CONNECT,
    PTP_OC_SONY_SDIO_CONTROL_DEVICE,
    PTP_OC_SONY_SDIO_GET_ALL_EXT_DEVICE_PROP_INFO,
    PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO,
    PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE,
    SMART_HANDLE_EVT_ATTACHED_CMD,
    SMART_HANDLE_EVT_DETACHED_CMD,
    SONY_PROTOCOL_2_00,
    SONY_PROTOCOL_3_00,
    SONY_PTP_VENDOR_EXT_ID,
    SPACC_MMIO_BASE,
    STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
    STATUS_BLOCKED_CRSDK_FIRMWARE_FLASH,
    STATUS_BLOCKED_CRSDK_NO_MEDIA_CARD,
    STATUS_BLOCKED_CRSDK_NVRAM_TAMPER,
    STATUS_BLOCKED_CRSDK_PROTOCOL_REGRESSION,
    STATUS_BLOCKED_CRSDK_SERVICE_ESCALATION,
    STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
    STATUS_BLOCKED_FX3_NO_BNC_TC_OUT,
    STATUS_BLOCKED_HOTSHOE_TIMEOUT_HANG,
    STATUS_BLOCKED_LTC_OVERVOLTAGE,
    STATUS_BLOCKED_LTC_SYNC_CONTRACT,
    STATUS_BLOCKED_MISHOE_AUDIO_FRAMING,
    STATUS_BLOCKED_MISHOE_ELECTRICAL,
    STATUS_BLOCKED_MISHOE_ID_LADDER,
    STATUS_BLOCKED_MULTIPORT_PIN_SHARING,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PTP_VENDOR_COLLISION,
    STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE,
    STATUS_BLOCKED_SMART_HANDLE_COLLISION,
    STATUS_BLOCKED_WRONG_ID_RESISTOR,
    STATUS_VERIFIED_SAFE,
    VMC_BNCM1_ID_RESISTOR_OHM,
    audit_crsdk_ptp2_session,
    audit_spacc_block_layer,
    classify_crsdk_ptp2_request,
    evaluate_phase38_safety_guards,
    is_aes_xts_partition,
    main as cli_main,
    verify_mishoe_digital_audio_and_p11_coexistence,
    verify_multiport_ltc_vs_uart_boot,
)


def _build_synthetic_fx3_sector0() -> bytes:
    entries = []
    for idx in range(1, SONY_PTBL_ENTRY_COUNT + 1):
        if idx in FX3_KEY_PARTITIONS:
            start_s, size_s, ptype, flag, _ = FX3_KEY_PARTITIONS[idx]
        else:
            start_s, size_s, ptype, flag = (0, 0, 0, 0)
        entries.append(
            PartitionEntry(
                index=idx,
                start_sector=start_s,
                size_sectors=size_s,
                part_type=ptype,
                flag=flag,
            )
        )
    return build_sector0_from_partitions(entries)


class CrSdkMiShoeLtcSpaccGuardTests(unittest.TestCase):
    def test_01_safety_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        for name in (
            "CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA",
            "STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH",
            "verify_multiport_ltc_vs_uart_boot",
            "verify_mishoe_digital_audio_and_p11_coexistence",
            "classify_crsdk_ptp2_request",
            "audit_crsdk_ptp2_session",
            "audit_spacc_block_layer",
            "is_aes_xts_partition",
            "evaluate_phase38_safety_guards",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name))

    # --- Domain 1: Multi-Port VMC-BNCM1 LTC vs uart_boot ---

    def test_02_multiport_ltc_valid_fx3_vmc_bncm1_fallback(self) -> None:
        res = verify_multiport_ltc_vs_uart_boot(
            ltc_cable_attached=True,
            uart_boot_harness_attached=False,
            id_resistor_ohm=VMC_BNCM1_ID_RESISTOR_OHM,
            ltc_vpp=2.5,
            ac_coupled=True,
            bnc_tc_port_present=False,
            ltc_direction="IN",
            camera_mode="MOVIE",
            tc_preset_mode="PRESET",
            tc_run_mode="FREE_RUN",
            ltc_fps=23.976,
            shooting_fps=23.976,
            p11_rtc_shim_active=True,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertTrue(res.fx3_fallback_active)
        self.assertFalse(res.bnc_tc_in_out_available)
        self.assertTrue(res.ext_lk_ready)

    def test_03_multiport_ltc_blocks_simultaneous_uart_boot_harness(self) -> None:
        res = verify_multiport_ltc_vs_uart_boot(
            ltc_cable_attached=True,
            uart_boot_harness_attached=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
        self.assertIn(STATUS_BLOCKED_MULTIPORT_PIN_SHARING, res.violation_codes)

    def test_04_multiport_ltc_blocks_injection_onto_uart_pins_7_8_9(self) -> None:
        for uart_pin in (7, 8, 9):
            res = verify_multiport_ltc_vs_uart_boot(
                ltc_pin_mapping={2: "GND_LTC", uart_pin: "LTC_IN_PLUS", 6: "ID_680K_TO_PIN2"}
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)

        swapped_p3 = verify_multiport_ltc_vs_uart_boot(
            ltc_pin_mapping={2: "GND_LTC", 3: "CAM_UART_RX", 6: "ID_680K_TO_PIN2"}
        )
        self.assertFalse(swapped_p3.valid)
        self.assertEqual(swapped_p3.status, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)

        no_gnd = verify_multiport_ltc_vs_uart_boot(gnd_connected=False)
        self.assertFalse(no_gnd.valid)
        self.assertEqual(no_gnd.status, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)

    def test_05_multiport_ltc_blocks_overvoltage_and_dc_coupled_above_3v15(self) -> None:
        too_high = verify_multiport_ltc_vs_uart_boot(ltc_vpp=6.2, ac_coupled=True)
        self.assertFalse(too_high.valid)
        self.assertEqual(too_high.status, STATUS_BLOCKED_LTC_OVERVOLTAGE)

        dc_high = verify_multiport_ltc_vs_uart_boot(ltc_vpp=4.5, ac_coupled=False)
        self.assertFalse(dc_high.valid)
        self.assertEqual(dc_high.status, STATUS_BLOCKED_LTC_OVERVOLTAGE)

        weak = verify_multiport_ltc_vs_uart_boot(ltc_vpp=0.1, ac_coupled=True)
        self.assertTrue(weak.valid)
        self.assertTrue(len(weak.warnings) >= 1)

    def test_06_multiport_ltc_blocks_100k_lanc_and_wrong_id_resistor_keying(self) -> None:
        lanc = verify_multiport_ltc_vs_uart_boot(id_resistor_ohm=LANC_ID_RESISTOR_OHM)
        self.assertFalse(lanc.valid)
        self.assertEqual(lanc.status, STATUS_BLOCKED_WRONG_ID_RESISTOR)
        self.assertTrue(any("LANC" in e for e in lanc.errors))

        missing = verify_multiport_ltc_vs_uart_boot(id_resistor_ohm=None)
        self.assertFalse(missing.valid)
        self.assertEqual(missing.status, STATUS_BLOCKED_WRONG_ID_RESISTOR)

        wrong_val = verify_multiport_ltc_vs_uart_boot(id_resistor_ohm=470_000)
        self.assertFalse(wrong_val.valid)
        self.assertEqual(wrong_val.status, STATUS_BLOCKED_WRONG_ID_RESISTOR)

    def test_07_multiport_ltc_blocks_fx3_tc_out_and_sync_contract_mismatches(self) -> None:
        tc_out = verify_multiport_ltc_vs_uart_boot(
            bnc_tc_port_present=False,
            ltc_direction="OUT",
        )
        self.assertFalse(tc_out.valid)
        self.assertEqual(tc_out.status, STATUS_BLOCKED_FX3_NO_BNC_TC_OUT)

        bad_fps = verify_multiport_ltc_vs_uart_boot(ltc_fps=25.0, shooting_fps=23.976)
        self.assertFalse(bad_fps.valid)
        self.assertEqual(bad_fps.status, STATUS_BLOCKED_LTC_SYNC_CONTRACT)

        bad_mode = verify_multiport_ltc_vs_uart_boot(camera_mode="STILL")
        self.assertFalse(bad_mode.valid)
        self.assertEqual(bad_mode.status, STATUS_BLOCKED_LTC_SYNC_CONTRACT)

        no_rtc_shim = verify_multiport_ltc_vs_uart_boot(p11_rtc_shim_active=False)
        self.assertFalse(no_rtc_shim.valid)
        self.assertEqual(no_rtc_shim.status, STATUS_BLOCKED_LTC_SYNC_CONTRACT)

    # --- Domain 2: 24-Pin MI-Shoe Digital Audio & P11 0x91db059b ---

    def test_08_mishoe_xlr_h1_48khz_24bit_4ch_and_p11_detached_ack_passes(self) -> None:
        res = verify_mishoe_digital_audio_and_p11_coexistence(
            accessory_model="XLR-H1",
            sample_rate_hz=48000,
            bit_depth=24,
            channels=4,
            id_resistors_ohm=(22_000, 56_000, 150_000),
            p11_smart_handle_shimmed=True,
            p11_smart_handle_ack_cmd=SMART_HANDLE_EVT_DETACHED_CMD,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertTrue(res.xlr_h1_preserved)
        self.assertEqual(res.audio_format_label, "PCM_48KHZ_24BIT_4CH")
        self.assertEqual(res.pcm_bitrate_bps, 4_608_000)
        self.assertEqual(res.frame_bytes_per_sample_period, 12)
        self.assertTrue(res.libinfrahotshoe_timeout_safe)

    def test_09_mishoe_ecm_b1m_24bit_2ch_and_16bit_2ch_profiles_pass(self) -> None:
        for depth in (24, 16):
            res = verify_mishoe_digital_audio_and_p11_coexistence(
                accessory_model="ECM-B1M",
                sample_rate_hz=48000,
                bit_depth=depth,
                channels=2,
                id_resistors_ohm=(0, 470_000, None),
            )
            self.assertTrue(res.valid, res.errors)
            self.assertTrue(res.xlr_h1_preserved)

    def test_10_mishoe_blocks_invalid_id_ladder_and_rail_overcurrent(self) -> None:
        bad_id = verify_mishoe_digital_audio_and_p11_coexistence(id_resistors_ohm=(33_000, 56_000, 150_000))
        self.assertFalse(bad_id.valid)
        self.assertEqual(bad_id.status, STATUS_BLOCKED_MISHOE_ID_LADDER)

        overcurrent = verify_mishoe_digital_audio_and_p11_coexistence(unreg_current_a=1.85)
        self.assertFalse(overcurrent.valid)
        self.assertEqual(overcurrent.status, STATUS_BLOCKED_MISHOE_ELECTRICAL)

        bad_vdd = verify_mishoe_digital_audio_and_p11_coexistence(logic_vdd_v=3.8)
        self.assertFalse(bad_vdd.valid)
        self.assertEqual(bad_vdd.status, STATUS_BLOCKED_MISHOE_ELECTRICAL)

        no_pgnd = verify_mishoe_digital_audio_and_p11_coexistence(pgnd_connected=False)
        self.assertFalse(no_pgnd.valid)
        self.assertEqual(no_pgnd.status, STATUS_BLOCKED_MISHOE_ELECTRICAL)

    def test_11_mishoe_blocks_bad_i2s_framing_and_xlr_h1_channel_mismatch(self) -> None:
        bad_sr = verify_mishoe_digital_audio_and_p11_coexistence(sample_rate_hz=44100)
        self.assertFalse(bad_sr.valid)
        self.assertEqual(bad_sr.status, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)

        xlr_2ch = verify_mishoe_digital_audio_and_p11_coexistence(accessory_model="XLR-H1", channels=2)
        self.assertFalse(xlr_2ch.valid)
        self.assertEqual(xlr_2ch.status, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)

    def test_12_mishoe_blocks_p11_spoofed_attached_ack_and_unshimmed_queue(self) -> None:
        spoofed_attached = verify_mishoe_digital_audio_and_p11_coexistence(
            p11_smart_handle_shimmed=True,
            p11_smart_handle_ack_cmd=SMART_HANDLE_EVT_ATTACHED_CMD,
        )
        self.assertFalse(spoofed_attached.valid)
        self.assertFalse(spoofed_attached.xlr_h1_preserved)
        self.assertEqual(spoofed_attached.status, STATUS_BLOCKED_SMART_HANDLE_COLLISION)

        unshimmed = verify_mishoe_digital_audio_and_p11_coexistence(p11_smart_handle_shimmed=False)
        self.assertFalse(unshimmed.valid)
        self.assertFalse(unshimmed.xlr_h1_preserved)
        self.assertEqual(unshimmed.status, STATUS_BLOCKED_SMART_HANDLE_COLLISION)

    def test_13_mishoe_blocks_libinfrahotshoe_timeout_hang(self) -> None:
        hang = verify_mishoe_digital_audio_and_p11_coexistence(hotshoe_wait_blocks_forever=True)
        self.assertFalse(hang.valid)
        self.assertFalse(hang.libinfrahotshoe_timeout_safe)
        self.assertEqual(hang.status, STATUS_BLOCKED_HOTSHOE_TIMEOUT_HANG)

        wrong_rc = verify_mishoe_digital_audio_and_p11_coexistence(hotshoe_wait_rc_on_tmo=0)
        self.assertFalse(wrong_rc.valid)
        self.assertEqual(wrong_rc.status, STATUS_BLOCKED_HOTSHOE_TIMEOUT_HANG)

    # --- Domain 3: Sony CrSDK PTP2 Firewall ---

    def test_14_crsdk_ptp2_safe_live_shooting_properties_and_controls_pass(self) -> None:
        reqs = [
            {"opcode": PTP_OC_SONY_SDIO_CONNECT, "phase": 1},
            {"opcode": PTP_OC_SONY_SDIO_CONNECT, "phase": 2},
            {"opcode": PTP_OC_SONY_SDIO_CONNECT, "phase": 3},
            {"opcode": PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO, "protocol_version": SONY_PROTOCOL_2_00},
            {"opcode": PTP_OC_SONY_SDIO_GET_ALL_EXT_DEVICE_PROP_INFO},
            {"opcode": PTP_OC_SONY_GET_DEVICE_PROPERTY_VALUE, "property": "CrDeviceProperty_ExposureIndex"},
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_ExposureIndex", "value": 12800},
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_ShutterAngle", "value": 180000, "unit": "millidegrees"},
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_WhiteBalance", "value": 5600},
            {"opcode": PTP_OC_SONY_SDIO_CONTROL_DEVICE, "action": "MovieRec"},
            {"opcode": 0x9200, "api": "SCRSDK::ImportLUTFile", "media_card_inserted": True},
        ]
        res = audit_crsdk_ptp2_session(reqs, sdio_connect_phases=())
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertTrue(res.sdio_handshake_complete)
        self.assertEqual(len(res.permitted_requests), len(reqs))
        self.assertEqual(res.blocked_requests, ())

    def test_15_crsdk_ptp2_blocks_incomplete_or_out_of_order_sdio_connect(self) -> None:
        incomplete = audit_crsdk_ptp2_session(
            [
                {"opcode": PTP_OC_SONY_SDIO_CONNECT, "phase": 1},
                {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_ExposureIndex", "value": 800},
            ],
            sdio_connect_phases=(),
        )
        self.assertFalse(incomplete.valid)
        self.assertEqual(incomplete.status, STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE)

        out_of_order = audit_crsdk_ptp2_session(
            [
                {"opcode": PTP_OC_SONY_SDIO_CONNECT, "phase": 2},
            ],
            sdio_connect_phases=(),
        )
        self.assertFalse(out_of_order.valid)
        self.assertEqual(out_of_order.status, STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE)

    def test_16_crsdk_ptp2_blocks_nikon_collision_and_wrong_vendor_ext(self) -> None:
        wrong_vendor = audit_crsdk_ptp2_session(
            [{"opcode": PTP_OC_SONY_SDIO_GET_ALL_EXT_DEVICE_PROP_INFO}],
            vendor_extension_id=0x0000000A,
        )
        self.assertFalse(wrong_vendor.valid)
        self.assertEqual(wrong_vendor.status, STATUS_BLOCKED_PTP_VENDOR_COLLISION)

        nikon_collision = classify_crsdk_ptp2_request(
            {"opcode": 0x920C, "action": "NikonStartMovieRec", "interpreted_as_nikon": True},
            vendor_extension_id=SONY_PTP_VENDOR_EXT_ID,
        )
        self.assertFalse(nikon_collision.allowed)
        self.assertEqual(nikon_collision.status, STATUS_BLOCKED_PTP_VENDOR_COLLISION)

    def test_17_crsdk_ptp2_enforces_protocol_2_00_fallback_against_3_00_regression(self) -> None:
        res = audit_crsdk_ptp2_session(
            [{"opcode": PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO, "protocol_version": SONY_PROTOCOL_3_00}],
            protocol_version=SONY_PROTOCOL_3_00,
            allow_protocol_3_00=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_CRSDK_PROTOCOL_REGRESSION)

    def test_18_crsdk_ptp2_blocks_firmware_update_format_and_camset_writes(self) -> None:
        for req in (
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "StartFirmwareUpdate"},
            {"opcode": PTP_OC_SONY_SDIO_CONTROL_DEVICE, "action": "FormatMedia"},
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "SCRSDK::UploadSettingFile_CAMSET"},
        ):
            res = audit_crsdk_ptp2_session([req])
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_CRSDK_FIRMWARE_FLASH)

        no_card = classify_crsdk_ptp2_request(
            {"opcode": 0x9200, "api": "SCRSDK::ImportLUTFile", "media_card_inserted": False}
        )
        self.assertFalse(no_card.allowed)
        self.assertEqual(no_card.status, STATUS_BLOCKED_CRSDK_NO_MEDIA_CARD)

    def test_19_crsdk_ptp2_blocks_nvram_product_model_and_service_escalation(self) -> None:
        nvram = audit_crsdk_ptp2_session(
            [{"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "PRODUCT_MODEL_ALCIN_UUD", "value": 4}]
        )
        self.assertFalse(nvram.valid)
        self.assertEqual(nvram.status, STATUS_BLOCKED_CRSDK_NVRAM_TAMPER)

        for esc in (
            {"opcode": PTP_OC_SONY_SDIO_CONTROL_DEVICE, "action": "054C:0336_SERVICE_MODE"},
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "SET_FILE_PATH_0x400f"},
            {"opcode": PTP_OC_SONY_SDIO_CONTROL_DEVICE, "action": "AdjustControl_0x0040"},
        ):
            res = audit_crsdk_ptp2_session([esc])
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_CRSDK_SERVICE_ESCALATION)

    def test_20_crsdk_ptp2_fail_closed_on_unknown_property_or_shutter_unit_mismatch(self) -> None:
        unknown_prop = classify_crsdk_ptp2_request(
            {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_MysteryWrite"}
        )
        self.assertFalse(unknown_prop.allowed)
        self.assertEqual(unknown_prop.status, STATUS_BLOCKED_CRSDK_UNKNOWN_OP)

        unknown_op = classify_crsdk_ptp2_request({"opcode": 0x9999, "property": "Unknown"})
        self.assertFalse(unknown_op.allowed)
        self.assertEqual(unknown_op.status, STATUS_BLOCKED_CRSDK_UNKNOWN_OP)

        rtmd_unit = classify_crsdk_ptp2_request(
            {
                "opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE,
                "property": "CrDeviceProperty_ShutterAngle",
                "value": 10800,
                "unit": "rtmd_1_60_deg",
            }
        )
        self.assertFalse(rtmd_unit.allowed)
        self.assertEqual(rtmd_unit.status, STATUS_BLOCKED_CRSDK_UNKNOWN_OP)

    # --- Domain 4: CXD90057 SPACC AES-XTS-256 Block-Layer Guard ---

    def test_21_spacc_allows_valid_cnflasha_xts_and_pnflasha_plaintext_reads(self) -> None:
        self.assertTrue(is_aes_xts_partition(5, 1))
        self.assertFalse(is_aes_xts_partition(4, 1))
        self.assertFalse(is_aes_xts_partition(6, 1))
        res = audit_spacc_block_layer(
            operations=[
                {"device": "/dev/cnflasha3", "operation": "read_plaintext"},
                {"device": "/dev/cnflasha15", "operation": "mount_ro"},
                {"device": "/dev/pnflasha1", "operation": "read_plaintext"},
                {"device": "/dev/pnflasha2", "operation": "read_plaintext"},
                {"device": "/dev/pnflasha6", "operation": "read_plaintext"},
                {"device": "/dev/pnflasha18", "operation": "read_plaintext"},
            ]
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertIn(15, res.xts_partitions)
        self.assertIn(2, res.plaintext_partitions)

    def test_22_spacc_blocks_raw_nflasha_mount_or_plaintext_read_on_xts_partition(self) -> None:
        res = audit_spacc_block_layer(
            operations=[{"device": "/dev/nflasha15", "operation": "mount"}]
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

        script_res = audit_spacc_block_layer(
            script_text="mount -t ext2 -o ro /dev/nflasha15 /mnt/usr\n"
        )
        self.assertFalse(script_res.valid)
        self.assertEqual(script_res.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

    def test_23_spacc_blocks_cnflasha_on_plaintext_or_wbi_partition(self) -> None:
        for dev in ("/dev/cnflasha2", "/dev/cnflasha5", "/dev/cnflasha18"):
            res = audit_spacc_block_layer(operations=[{"device": dev, "operation": "read_plaintext"}])
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

    def test_24_spacc_blocks_mixed_nflasha_vs_cnflasha_reads_and_scripts(self) -> None:
        mixed_op = audit_spacc_block_layer(
            operations=[
                {"device": "/dev/nflasha15", "operation": "compare_with", "other_device": "/dev/cnflasha15"}
            ]
        )
        self.assertFalse(mixed_op.valid)
        self.assertEqual(mixed_op.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

        mixed_session = audit_spacc_block_layer(
            operations=[
                {"device": "/dev/cnflasha2", "operation": "read_plaintext"},
            ],
            script_text="sha256sum /dev/nflasha2 /dev/cnflasha2\n",
        )
        self.assertFalse(mixed_session.valid)
        self.assertEqual(mixed_session.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

    def test_25_spacc_blocks_userland_mmio_0xf7fc0000_in_ops_and_scripts(self) -> None:
        mmio_op = audit_spacc_block_layer(
            operations=[{"mmio_addr": SPACC_MMIO_BASE, "size": 4, "ring": "userland", "operation": "mmio_read"}]
        )
        self.assertFalse(mmio_op.valid)
        self.assertEqual(mmio_op.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

        mmio_script = audit_spacc_block_layer(script_text="devmem 0xf7fc0010 32\n")
        self.assertFalse(mmio_script.valid)
        self.assertEqual(mmio_script.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

        kernel_ok = audit_spacc_block_layer(
            operations=[{"mmio_addr": SPACC_MMIO_BASE, "size": 4, "ring": "kernel_spacc_driver", "operation": "mmio_read"}]
        )
        self.assertTrue(kernel_ok.valid, kernel_ok.errors)

    def test_26_spacc_uses_real_sector0_table_and_blocks_emmc_writes(self) -> None:
        sec0 = _build_synthetic_fx3_sector0()
        res_ok = audit_spacc_block_layer(
            operations=[
                {"device": "/dev/cnflasha8", "operation": "read_plaintext"},
                {"device": "/dev/pnflasha18", "operation": "read_plaintext"},
            ],
            sector0_bytes=sec0,
        )
        self.assertTrue(res_ok.valid, res_ok.errors)

        write_blocked = audit_spacc_block_layer(
            operations=[{"device": "/dev/cnflasha15", "operation": "write", "writable": True}],
            sector0_bytes=sec0,
        )
        self.assertFalse(write_blocked.valid)
        self.assertEqual(write_blocked.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- Unified Evaluator, Clean-Room Parity & CLI ---

    def test_27_unified_evaluator_and_clean_room_parity(self) -> None:
        normal_rep = evaluate_phase38_safety_guards()
        self.assertTrue(normal_rep.all_passed, normal_rep.errors)
        self.assertEqual(normal_rep.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(normal_rep.schema, CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA)
        self.assertFalse(normal_rep.persistent_emmc_writes_authorized)
        self.assertFalse(normal_rep.persistent_write_release)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cr_rep = evaluate_phase38_safety_guards()
        self.assertTrue(cr_rep.clean_room_forced)
        self.assertTrue(cr_rep.all_passed, cr_rep.errors)
        self.assertEqual(cr_rep.status, STATUS_VERIFIED_SAFE)
        serialized = json.dumps(cr_rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'", serialized)

    def test_28_cli_self_check_json_and_exit_code(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["--self-check", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA)
        self.assertTrue(payload["all_passed"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertFalse(payload["persistent_write_release"])


if __name__ == "__main__":
    unittest.main()
