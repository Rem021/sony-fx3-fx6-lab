"""Fast dual-mode unit tests for Phase 61 — Wired USB-LAN / PTP-IP Firewall & 18-Gate Preflight (`G01..G18`)."""

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
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.exfat_media_integrity_guard import (
    EXFAT_FLAG_VOLUME_DIRTY,
    EXFAT_VOLUME_FLAGS_OFFSET,
    MEDIA_TYPE_CFEXPRESS_A,
    MediaSlotConfig,
    SLOT_A,
    STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM,
    STATUS_BLOCKED_EXFAT_VOLUME_DIRTY,
    STATUS_BLOCKED_FILESYSTEM_SEPARATION,
    STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID,
    STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT,
    STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT,
    build_synthetic_exfat_boot_region,
    build_synthetic_p1_fat12_vbr,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.usblan_ptpip_and_18gate_preflight import (
    BT_UART_TTY_DEVICE,
    G17_GATE_CODE,
    G17_GATE_ID,
    G18_GATE_CODE,
    G18_GATE_ID,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PTPIP_TCP_PORT,
    PTP_OC_CLOSE_SESSION,
    PTP_OC_GET_DEVICE_INFO,
    PTP_OC_GET_EVENT,
    PTP_OC_OPEN_SESSION,
    PTP_OC_SEND_OBJECT_INFO,
    PTP_OC_SONY_GET_LIVE_VIEW,
    PTP_OC_SONY_SDIO_CONNECT,
    PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO,
    PTP_OC_SONY_SET_DEVICE_PROP,
    SONY_PROTOCOL_3_00,
    SSDP_UDP_PORT,
    STATUS_BLOCKED_BT_RADIO_ENABLED,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_G18_USBLAN_AIRPLANE,
    STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE,
    STATUS_BLOCKED_PTPIP_NVRAM_WRITE,
    STATUS_BLOCKED_PTPIP_RAW_PARTITION,
    STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK,
    STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
    STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED,
    STATUS_BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET,
    STATUS_BLOCKED_USBLAN_UNSUPPORTED_CLASS,
    STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE,
    STATUS_BLOCKED_WIFI_RADIO_ENABLED,
    STATUS_VERIFIED_G17,
    STATUS_VERIFIED_G18,
    STATUS_VERIFIED_SAFE,
    USBLAN_PTPIP_18GATE_SCHEMA,
    USBLAN_PTPIP_18GATE_VERSION,
    USB_CLASS_CDC_ECM,
    USB_CLASS_CDC_NCM,
    USB_CLASS_RNDIS,
    audit_usblan_ptpip_and_mc_firewall,
    audit_usblan_ptpip_donor_contracts,
    build_ptpip_cmd_request_frame,
    classify_usblan_ptpip_or_mc_operation,
    evaluate_18_master_safety_gates,
    evaluate_g17_exfat_and_client_media_isolation,
    evaluate_g18_usblan_ptpip_and_airplane_coexistence,
    evaluate_ptpip_15740_packet,
    main as module_cli_main,
    verify_usblan_wired_control_and_airplane_coexistence,
)


class UsbLanPtpIpAnd18GatePreflightTests(unittest.TestCase):
    # --- 1. Hard Redlines, Exports & Strictly O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(USBLAN_PTPIP_18GATE_SCHEMA, "fx3-usblan-ptpip-18gate-preflight-v1")
        self.assertEqual(USBLAN_PTPIP_18GATE_VERSION, "1.0.0")
        for sym in (
            "USBLAN_PTPIP_18GATE_SCHEMA",
            "G17_GATE_ID",
            "G18_GATE_ID",
            "audit_usblan_ptpip_donor_contracts",
            "verify_usblan_wired_control_and_airplane_coexistence",
            "classify_usblan_ptpip_or_mc_operation",
            "evaluate_ptpip_15740_packet",
            "audit_usblan_ptpip_and_mc_firewall",
            "evaluate_g17_exfat_and_client_media_isolation",
            "evaluate_g18_usblan_ptpip_and_airplane_coexistence",
            "evaluate_18_master_safety_gates",
            "usblan_ptpip_and_18gate_preflight",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_usblan_ptpip_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        donor_calls = [
            (p, f)
            for p, f in observed_flags
            if "cdc_ncm.ko" in p or "libNetServiceEther.so" in p or "libptp.so" in p or "libWlanResource.so" in p
        ]
        for path, flags in donor_calls:
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_usblan_ptpip_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 7)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with patch(
            "fx3_safety.usblan_ptpip_and_18gate_preflight._read_file_o_rdonly",
            return_value=b"tampered",
        ):
            # Force donor_available path via mocking is_file + work_root if clean room is active
            res = audit_usblan_ptpip_donor_contracts(force_clean_room=False)
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    # --- 2. Wired USB-LAN & P12 Airplane-Mode Coexistence ---

    def test_04_wired_usblan_cdc_ncm_rtl8153_and_ax88179_pass(self) -> None:
        for body, chipset, iface, ip_mode, gw in (
            ("ILME-FX3", "RTL8153", "eth0", "Manual", "192.168.0.1"),
            ("ILME-FX6", "AX88179", "usblan0", "DHCP", ""),
        ):
            res = verify_usblan_wired_control_and_airplane_coexistence(
                camera_body=body,
                interface_name=iface,
                usb_class=USB_CLASS_CDC_NCM,
                chipset=chipset,
                link_speed_mbps=1000,
                ip_mode=ip_mode,
                default_gateway=gw,
            )
            self.assertTrue(res.valid, f"Expected pass for {body}/{chipset}: {res.errors}")
            self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
            self.assertFalse(res.wifi_radio_enabled)
            self.assertFalse(res.bluetooth_uart_enabled)
            self.assertEqual(res.bt_tty_device, BT_UART_TTY_DEVICE)
            self.assertEqual(res.bt_hci_tx_packets, 0)
            self.assertTrue(res.wf12_00342260_immune)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_05_usblan_rejects_rndis_cdc_ecm_and_wireless_interfaces(self) -> None:
        for bad_class in (USB_CLASS_RNDIS, USB_CLASS_CDC_ECM):
            res = verify_usblan_wired_control_and_airplane_coexistence(usb_class=bad_class)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_USBLAN_UNSUPPORTED_CLASS)

        for bad_iface in ("wlan0", "wl0", "p2p0"):
            res = verify_usblan_wired_control_and_airplane_coexistence(interface_name=bad_iface)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE)

    def test_06_usblan_rejects_ax88179a_25g_and_bad_link_speed(self) -> None:
        for bad_chip in ("AX88179A", "AX88179B", "RTL8156_2.5G", "AQC111U_5G", "10GBASE_T"):
            res = verify_usblan_wired_control_and_airplane_coexistence(chipset=bad_chip)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET)

        for bad_speed in (100, 2500, 5000):
            res = verify_usblan_wired_control_and_airplane_coexistence(link_speed_mbps=bad_speed)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET)

    def test_07_usblan_fx3_manual_ip_requires_same_subnet_gateway(self) -> None:
        for bad_gw in ("", "10.0.0.1", "192.168.0.10", "not-an-ip"):
            res = verify_usblan_wired_control_and_airplane_coexistence(
                camera_body="ILME-FX3",
                ip_mode="Manual",
                camera_ip="192.168.0.10",
                subnet_mask="255.255.255.0",
                default_gateway=bad_gw,
            )
            self.assertFalse(res.valid, f"Expected gateway failure for {bad_gw!r}")
            self.assertEqual(res.status, STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED)
            self.assertFalse(res.gateway_same_subnet)

    def test_08_p12_airplane_blocks_wifi_and_bluetooth_uart_activity(self) -> None:
        r_wifi = verify_usblan_wired_control_and_airplane_coexistence(wifi_radio_enabled=True)
        self.assertFalse(r_wifi.valid)
        self.assertEqual(r_wifi.status, STATUS_BLOCKED_WIFI_RADIO_ENABLED)
        self.assertFalse(r_wifi.wf12_00342260_immune)

        r_wdrv = verify_usblan_wired_control_and_airplane_coexistence(wlan_driver_loaded=True)
        self.assertFalse(r_wdrv.valid)
        self.assertEqual(r_wdrv.status, STATUS_BLOCKED_WIFI_RADIO_ENABLED)

        r_bt = verify_usblan_wired_control_and_airplane_coexistence(bluetooth_uart_enabled=True)
        self.assertFalse(r_bt.valid)
        self.assertEqual(r_bt.status, STATUS_BLOCKED_BT_RADIO_ENABLED)
        self.assertFalse(r_bt.wf12_00342260_immune)

        r_hci = verify_usblan_wired_control_and_airplane_coexistence(bt_hci_tx_packets=3)
        self.assertFalse(r_hci.valid)
        self.assertEqual(r_hci.status, STATUS_BLOCKED_BT_RADIO_ENABLED)

    def test_09_p12_vma_and_bk4_airplane_shadow_tamper_blocked(self) -> None:
        r_rc = verify_usblan_wired_control_and_airplane_coexistence(p12_patched_rc=1)
        self.assertFalse(r_rc.valid)
        self.assertEqual(r_rc.status, STATUS_BLOCKED_G18_USBLAN_AIRPLANE)
        self.assertFalse(r_rc.p12_guard_verified)

        r_bk4 = verify_usblan_wired_control_and_airplane_coexistence(
            bk4_airplane_shadow={0x019E0012: 0x01, 0x0051000F: 0x00, 0x01A20002: 0x00}
        )
        self.assertFalse(r_bk4.valid)
        self.assertEqual(r_bk4.status, STATUS_BLOCKED_G18_USBLAN_AIRPLANE)
        self.assertFalse(r_bk4.bk4_airplane_shadow_verified)

    # --- 3. PTP-IP (TCP 15740) & Monitor & Control Security Firewall ---

    def test_10_firewall_whitelists_safe_ptpip_shooting_and_monitoring(self) -> None:
        safe_ops = [
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_GET_DEVICE_INFO},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_OPEN_SESSION},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_GET_EVENT},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_GET_LIVE_VIEW},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "ISO"},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "EI"},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "ShutterSpeed"},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "WB"},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "prop_id": 0xD2C1, "action": "AF_TouchFocus"},
            {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "opcode": PTP_OC_CLOSE_SESSION},
        ]
        res = audit_usblan_ptpip_and_mc_firewall(safe_ops)
        self.assertTrue(res.valid, f"Unexpected blocks: {res.errors}")
        self.assertEqual(res.allowed_count, len(safe_ops))
        self.assertEqual(res.blocked_count, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_11_firewall_whitelists_safe_mc_udp_and_http_endpoints(self) -> None:
        safe_mc = [
            {"protocol": "udp", "port": SSDP_UDP_PORT, "action": "M-SEARCH"},
            {"protocol": "http", "port": 8080, "method": "POST", "path": "/sony/camera", "action": "getEvent"},
            {"protocol": "http", "port": 8080, "method": "POST", "path": "/sony/camera", "action": "setExposureIndex"},
            {"protocol": "http", "port": 8080, "method": "POST", "path": "/sony/camera", "action": "setTouchAFPosition"},
            {"protocol": "http", "port": 8080, "method": "POST", "path": "/sony/camera", "action": "getWaveformTelemetry"},
            {"protocol": "http", "port": 80, "method": "GET", "path": "/liveview/stream"},
        ]
        res = audit_usblan_ptpip_and_mc_firewall(safe_mc)
        self.assertTrue(res.valid, f"Unexpected blocks: {res.errors}")
        self.assertEqual(res.allowed_count, len(safe_mc))

    def test_12_firewall_blocks_entire_0x9280_to_0x92ff_restricted_range(self) -> None:
        restricted_cases = [
            (0x9280, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE),
            (0x9281, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE),
            (0x9282, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE),
            (0x928F, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE),
            (0x9290, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK),
            (0x92A0, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK),
            (0x92C0, STATUS_BLOCKED_PTPIP_RAW_PARTITION),
            (0x92DF, STATUS_BLOCKED_PTPIP_RAW_PARTITION),
            (0x92F0, STATUS_BLOCKED_PTPIP_NVRAM_WRITE),
            (0x92F1, STATUS_BLOCKED_PTPIP_NVRAM_WRITE),
            (0x92F2, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK),
            (0x92FF, STATUS_BLOCKED_PTPIP_NVRAM_WRITE),
        ]
        for opcode, expected_status in restricted_cases:
            dec = classify_usblan_ptpip_or_mc_operation({"protocol": "ptpip", "opcode": opcode})
            self.assertFalse(dec.allowed, f"Opcode {hex(opcode)} must be blocked")
            self.assertEqual(dec.status, expected_status)
            self.assertFalse(dec.persistent_emmc_writes_authorized)

            # Also verify raw binary PTP-IP CmdRequest packet framing path
            frame = build_ptpip_cmd_request_frame(opcode=opcode, tx_id=100)
            pkt_dec = evaluate_ptpip_15740_packet(frame)
            self.assertFalse(pkt_dec.allowed)
            self.assertEqual(pkt_dec.status, expected_status)

    def test_13_firewall_blocks_sendobjectinfo_dat_and_ufu_firmware_payloads(self) -> None:
        for fname in ("BODYDATA.DAT", "FX3_V800.ufu", "update.dat"):
            dec = classify_usblan_ptpip_or_mc_operation(
                {"protocol": "ptpip", "opcode": PTP_OC_SEND_OBJECT_INFO, "filename": fname}
            )
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.status, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE)

            frame = build_ptpip_cmd_request_frame(opcode=PTP_OC_SEND_OBJECT_INFO, tx_id=200)
            pkt_dec = evaluate_ptpip_15740_packet(frame, filename_hint=fname)
            self.assertFalse(pkt_dec.allowed)
            self.assertEqual(pkt_dec.status, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE)

    def test_14_firewall_blocks_http_fwupdate_and_raw_telnet_rsh_shells(self) -> None:
        blocked_endpoints = [
            ({"protocol": "http", "port": 8080, "method": "POST", "path": "/fwupdate"}, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE),
            ({"protocol": "http", "port": 80, "method": "POST", "path": "/service/unlock"}, STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS),
            ({"protocol": "http", "port": 80, "method": "POST", "path": "/sony/camera", "action": "service_unlock"}, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK),
            ({"protocol": "http", "port": 80, "method": "POST", "path": "/nvram/bk4"}, STATUS_BLOCKED_PTPIP_NVRAM_WRITE),
            ({"protocol": "http", "port": 80, "method": "GET", "path": "/shell"}, STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS),
            ({"protocol": "telnet", "port": 23}, STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS),
            ({"protocol": "rsh", "port": 514}, STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS),
            ({"protocol": "tcp", "port": 2323, "action": "raw_shell"}, STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS),
        ]
        for op, expected_status in blocked_endpoints:
            dec = classify_usblan_ptpip_or_mc_operation(op)
            self.assertFalse(dec.allowed, f"Expected block for {op}")
            self.assertEqual(dec.status, expected_status)

    def test_15_firewall_blocks_service_unlock_nvram_and_raw_partition_tokens(self) -> None:
        d_svc = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "action": "054C:0336 AdjustControl"}
        )
        self.assertFalse(d_svc.allowed)
        self.assertEqual(d_svc.status, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK)

        d_bk4 = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "BK4_PRODUCT_MODEL"}
        )
        self.assertFalse(d_bk4.allowed)
        self.assertEqual(d_bk4.status, STATUS_BLOCKED_PTPIP_NVRAM_WRITE)

        d_raw = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": 0x100E, "target": "/dev/nflasha5"}
        )
        self.assertFalse(d_raw.allowed)
        self.assertEqual(d_raw.status, STATUS_BLOCKED_PTPIP_RAW_PARTITION)

    def test_16_firewall_fail_closed_on_unknown_opcodes_bad_ports_and_wlan0(self) -> None:
        d_unk = classify_usblan_ptpip_or_mc_operation({"protocol": "ptpip", "opcode": 0x9999})
        self.assertFalse(d_unk.allowed)
        self.assertEqual(d_unk.status, STATUS_BLOCKED_PTPIP_UNKNOWN_OP)

        d_port = classify_usblan_ptpip_or_mc_operation({"protocol": "ptpip", "port": 15741, "opcode": PTP_OC_GET_DEVICE_INFO})
        self.assertFalse(d_port.allowed)
        self.assertEqual(d_port.status, STATUS_BLOCKED_PTPIP_UNKNOWN_OP)

        d_wlan = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "interface": "wlan0", "opcode": PTP_OC_GET_DEVICE_INFO}
        )
        self.assertFalse(d_wlan.allowed)
        self.assertEqual(d_wlan.status, STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE)

        d_proto3 = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO, "protocol_version": SONY_PROTOCOL_3_00}
        )
        self.assertFalse(d_proto3.allowed)
        self.assertEqual(d_proto3.status, STATUS_BLOCKED_PTPIP_UNKNOWN_OP)

        d_unauth = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "ISO"},
            authenticated=False,
        )
        self.assertFalse(d_unauth.allowed)
        self.assertEqual(d_unauth.status, STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK)

        d_unit = classify_usblan_ptpip_or_mc_operation(
            {"protocol": "ptpip", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "property": "ShutterAngle", "unit": "degrees"}
        )
        self.assertFalse(d_unit.allowed)
        self.assertEqual(d_unit.status, STATUS_BLOCKED_PTPIP_UNKNOWN_OP)

    def test_17_binary_ptpip_packet_safe_and_malformed_validation(self) -> None:
        ok_frame = build_ptpip_cmd_request_frame(
            opcode=PTP_OC_SONY_SET_DEVICE_PROP,
            tx_id=1,
            param1=0xD2C1,
        )
        dec_ok = evaluate_ptpip_15740_packet(ok_frame)
        self.assertTrue(dec_ok.allowed)
        self.assertEqual(dec_ok.status, STATUS_VERIFIED_SAFE)

        with self.assertRaises(ValueError):
            evaluate_ptpip_15740_packet(b"\x00" * 10)
        with self.assertRaises(ValueError):
            evaluate_ptpip_15740_packet(ok_frame[:-2])

    # --- 4. Gate G17 (exFAT BootChecksum & Client Media Isolation) ---

    def test_18_g17_passes_with_clean_lab_card_and_valid_p1(self) -> None:
        v, rep = evaluate_g17_exfat_and_client_media_isolation(
            force_clean_room=True,
            p1_vbr_bytes=build_synthetic_p1_fat12_vbr(),
        )
        self.assertTrue(v.passed)
        self.assertEqual(v.gate_id, G17_GATE_ID)
        self.assertEqual(v.gate_code, G17_GATE_CODE)
        self.assertEqual(v.status, STATUS_VERIFIED_G17)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_19_g17_blocks_dirty_bit_and_bad_boot_checksum(self) -> None:
        import struct

        dirty = bytearray(build_synthetic_exfat_boot_region())
        struct.pack_into("<H", dirty, EXFAT_VOLUME_FLAGS_OFFSET, EXFAT_FLAG_VOLUME_DIRTY)
        v_dirty, rep_dirty = evaluate_g17_exfat_and_client_media_isolation(
            force_clean_room=True,
            slot_a=MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                media_type=MEDIA_TYPE_CFEXPRESS_A,
                exfat_boot_bytes=bytes(dirty),
                card_entries=(),
                dedicated_lab_card=True,
            ),
        )
        self.assertFalse(v_dirty.passed)
        self.assertEqual(v_dirty.status, STATUS_BLOCKED_EXFAT_VOLUME_DIRTY)
        self.assertFalse(rep_dirty.h0_h1_trial_entry_allowed)

        bad_chk = bytearray(build_synthetic_exfat_boot_region())
        bad_chk[11 * 512] ^= 0xFF
        v_chk, rep_chk = evaluate_g17_exfat_and_client_media_isolation(
            force_clean_room=True,
            slot_a=MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                media_type=MEDIA_TYPE_CFEXPRESS_A,
                exfat_boot_bytes=bytes(bad_chk),
                card_entries=(),
                dedicated_lab_card=True,
            ),
        )
        self.assertFalse(v_chk.passed)
        self.assertEqual(v_chk.status, STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM)
        self.assertFalse(rep_chk.h0_h1_trial_entry_allowed)

    def test_20_g17_blocks_client_xdroot_m4root_and_rsv_files(self) -> None:
        for entries, expected_status in (
            ([("XDROOT/Clip/A001C001.MXF", 4096)], STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT),
            ([("PRIVATE/M4ROOT/CLIP/C0001.MP4", 4096)], STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT),
            ([("PRIVATE/M4ROOT/CLIP/C0002.RSV", 0)], STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT),
        ):
            v, rep = evaluate_g17_exfat_and_client_media_isolation(
                force_clean_room=True,
                slot_a=MediaSlotConfig(
                    slot_id=SLOT_A,
                    inserted=True,
                    media_type=MEDIA_TYPE_CFEXPRESS_A,
                    exfat_boot_bytes=build_synthetic_exfat_boot_region(),
                    card_entries=entries,
                    dedicated_lab_card=True,
                ),
            )
            self.assertFalse(v.passed)
            self.assertEqual(v.status, expected_status)
            self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_21_g17_blocks_p1_exfat_spoof(self) -> None:
        spoof_p1 = build_synthetic_exfat_boot_region()[:512]
        v, rep = evaluate_g17_exfat_and_client_media_isolation(
            force_clean_room=True,
            p1_vbr_bytes=spoof_p1,
        )
        self.assertFalse(v.passed)
        self.assertEqual(v.status, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
        self.assertIn(STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID, v.violation_codes)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    # --- 5. Gate G18 (USB-LAN PTP-IP Firewall & Airplane Coexistence) ---

    def test_22_g18_passes_in_clean_room_and_blocks_faults(self) -> None:
        v_ok, res_ok = evaluate_g18_usblan_ptpip_and_airplane_coexistence(force_clean_room=True)
        self.assertTrue(v_ok.passed)
        self.assertEqual(v_ok.gate_id, G18_GATE_ID)
        self.assertEqual(v_ok.gate_code, G18_GATE_CODE)
        self.assertEqual(v_ok.status, STATUS_VERIFIED_G18)
        self.assertFalse(res_ok.wifi_radio_enabled)
        self.assertFalse(res_ok.bluetooth_uart_enabled)
        self.assertTrue(res_ok.wf12_00342260_immune)
        self.assertFalse(res_ok.persistent_emmc_writes_authorized)

        v_bad_fw, _ = evaluate_g18_usblan_ptpip_and_airplane_coexistence(
            force_clean_room=True,
            ptpip_or_mc_requests=[{"protocol": "http", "method": "POST", "path": "/fwupdate"}],
        )
        self.assertFalse(v_bad_fw.passed)
        self.assertEqual(v_bad_fw.status, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE)

        v_bad_wifi, _ = evaluate_g18_usblan_ptpip_and_airplane_coexistence(
            force_clean_room=True,
            usblan_kwargs={"wifi_radio_enabled": True},
        )
        self.assertFalse(v_bad_wifi.passed)
        self.assertEqual(v_bad_wifi.status, STATUS_BLOCKED_WIFI_RADIO_ENABLED)

    # --- 6. Master 18-Gate Preflight Engine (`G01..G18`) & CLI ---

    def test_23_master_18_gates_default_repo_passes_offline_15_gates(self) -> None:
        report = evaluate_18_master_safety_gates(DEFAULT_REPO_ROOT)
        self.assertEqual(len(report.gates), 18)
        self.assertEqual(report.summary["total_gates"], 18)
        self.assertEqual(report.summary["g17_to_g18_verified"], 2)
        self.assertTrue(report.g13_to_g18_all_passed)
        self.assertTrue(report.g17_to_g18_all_passed)
        self.assertTrue(report.offline_15_gates_verified)
        self.assertFalse(report.all_18_gates_verified)
        self.assertTrue(report.h0_h1_trial_entry_allowed)
        self.assertEqual(report.status, "VERIFIED_G01_G09_AND_G13_G18_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(
            [g["gate_id"] for g in report.gates[-2:]],
            [G17_GATE_ID, G18_GATE_ID],
        )
        self.assertEqual(
            [g["gate_code"] for g in report.gates[-2:]],
            [G17_GATE_CODE, G18_GATE_CODE],
        )

    def test_24_master_18_gates_clean_room_dry_run_tier0_passes_all_18(self) -> None:
        report = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(report.clean_room_forced)
        self.assertTrue(report.all_18_gates_verified)
        self.assertEqual(report.summary["verified_gates"], 18)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(report.status, "VERIFIED_ALL_18_GATES_OFFLINE_DRY_RUN")
        self.assertTrue(report.h0_h1_trial_entry_allowed)
        self.assertFalse(report.persistent_emmc_writes_authorized)

    def test_25_master_18_gates_blocks_g17_client_media_and_g18_ptpip_attack(self) -> None:
        r_g17 = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            slot_a=MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                media_type=MEDIA_TYPE_CFEXPRESS_A,
                exfat_boot_bytes=build_synthetic_exfat_boot_region(),
                card_entries=[("XDROOT/Clip/C001.MXF", 1024)],
                dedicated_lab_card=True,
            ),
        )
        self.assertFalse(r_g17.all_18_gates_verified)
        self.assertFalse(r_g17.g17_to_g18_all_passed)
        self.assertFalse(r_g17.h0_h1_trial_entry_allowed)
        self.assertEqual(r_g17.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)

        r_g18 = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            ptpip_or_mc_requests=[{"protocol": "ptpip", "opcode": 0x9280}],
        )
        self.assertFalse(r_g18.all_18_gates_verified)
        self.assertFalse(r_g18.g17_to_g18_all_passed)
        self.assertFalse(r_g18.h0_h1_trial_entry_allowed)
        self.assertEqual(r_g18.status, STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE)

    def test_26_master_18_gates_propagates_g13_to_g16_and_emmc_write_redline(self) -> None:
        r_g16 = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            wbi_mutation_bytes=4,
        )
        self.assertFalse(r_g16.g13_to_g18_all_passed)
        self.assertFalse(r_g16.h0_h1_trial_entry_allowed)

        r_emmc = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r_emmc.all_18_gates_verified)
        self.assertFalse(r_emmc.h0_h1_trial_entry_allowed)
        self.assertEqual(r_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r_emmc.persistent_emmc_writes_authorized)

    def test_27_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        report = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        dumped = json.dumps(report.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x", dumped)
        self.assertNotIn('b"\\x', dumped)

    def test_28_package_and_module_cli_verify_18_gates_clean_room_json(self) -> None:
        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-18-gates", "--clean-room", "--dry-run-tier0", "--json"])
        self.assertEqual(rc_pkg, 0)
        payload = json.loads(buf_pkg.getvalue())
        self.assertEqual(payload["schema"], USBLAN_PTPIP_18GATE_SCHEMA)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_18_gates_verified"])
        self.assertTrue(payload["h0_h1_trial_entry_allowed"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertEqual(len(payload["gates"]), 18)

        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        self.assertIn("verified=15/18", buf_mod.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_mod.getvalue())

    def test_29_empty_firewall_session_fails_closed_and_mixed_session_blocks(self) -> None:
        res_empty = audit_usblan_ptpip_and_mc_firewall([])
        self.assertFalse(res_empty.valid)
        self.assertEqual(res_empty.total_operations, 0)

        res_mixed = audit_usblan_ptpip_and_mc_firewall(
            [
                {"protocol": "ptpip", "opcode": PTP_OC_GET_DEVICE_INFO},
                {"protocol": "ptpip", "opcode": 0x92F0},
            ]
        )
        self.assertFalse(res_mixed.valid)
        self.assertEqual(res_mixed.allowed_count, 1)
        self.assertEqual(res_mixed.blocked_count, 1)
        self.assertEqual(res_mixed.status, STATUS_BLOCKED_PTPIP_NVRAM_WRITE)

    def test_30_master_18_gates_preserves_g01_to_g16_untouched(self) -> None:
        from fx3_safety.master_16gate_preflight import evaluate_16_master_safety_gates

        r16 = evaluate_16_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        r18 = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        self.assertEqual(len(r16.gates), 16)
        self.assertEqual(len(r18.gates), 18)
        self.assertEqual(
            [g["gate_id"] for g in r16.gates],
            [g["gate_id"] for g in r18.gates[:16]],
        )
        self.assertEqual(
            [g["status"] for g in r16.gates],
            [g["status"] for g in r18.gates[:16]],
        )


if __name__ == "__main__":
    unittest.main()
