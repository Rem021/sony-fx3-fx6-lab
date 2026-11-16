"""Phase 152 Dual-Mode Unit Tests (46 tests): Real-Hardware Wi-Fi (802.11ac) RF NVS
p12/p13 Lock, BLE Creators' App vs FX6 Content Browser / Monitor & Control Non-Blocking
Daemon Bridge, USB Type-C Multi-Role (MSC 054C:0DA1, SERVICE 054C:0336, MTP/PTP Remote,
UVC/UAC HDMI Bridge), and Wired USB-LAN Gigabit Ethernet FTP / Monitor & Control Bridge.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
)
from fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor import (
    BT_APPFW_FX3_MARKERS,
    BT_APPFW_FX6_MARKERS,
    BT_CORE_MARKERS,
    BT_CP_SHARED_MARKERS,
    BT_SENCORE_SHARED_MARKERS,
    ETHER_FTP_SHARED_MARKERS,
    ETHER_NETSERVICE_FX6_EXTRA_MARKERS,
    ETHER_NETSERVICE_SHARED_MARKERS,
    ETHER_SENCORE_FX3_MARKERS,
    ETHER_SENCORE_FX6_EXTRA_MARKERS,
    EXPECTED_FX3_BLE_EXPORTS,
    EXPECTED_FX3_BT_CORE_EXPORTS,
    EXPECTED_FX3_ETHER_EXPORTS,
    EXPECTED_FX6_BLE_EXPORTS,
    EXPECTED_FX6_BT_CORE_EXPORTS,
    EXPECTED_FX6_ETHER_EXPORTS,
    EXPECTED_MSC_SERVER_BYTES,
    EXPECTED_MSC_SERVER_EXPORTS,
    EXPECTED_MSC_SERVER_IMPORTS,
    EXPECTED_USB_CONTROL_BYTES,
    EXPECTED_USB_CONTROL_EXPORTS,
    EXPECTED_USB_CONTROL_IMPORTS,
    EXPECTED_WLAN_ADJUST_BYTES,
    EXPECTED_WLAN_ADJUST_EXPORTS,
    EXPECTED_WLAN_ADJUST_IMPORTS,
    EXPECTED_WLAN_RESOURCE_BYTES,
    EXPECTED_WLAN_RESOURCE_EXPORTS,
    EXPECTED_WLAN_RESOURCE_IMPORTS,
    MSC_SERVER_MARKERS,
    PHASE_152_SCHEMA,
    PHASE_152_VERSION,
    RF_NVS_IMMUTABLE_PARTITIONS,
    USB_APPFW_FX3_MARKERS,
    USB_APPFW_FX6_MARKERS,
    USB_CMN_MARKERS,
    USB_CONTROL_MARKERS,
    USB_PID_FX3_MSC_HEX,
    USB_PID_FX3_SERVICE_HEX,
    USB_VID_SONY_HEX,
    VALID_BT_BRIDGE_SCENARIOS,
    VALID_ETHER_ADAPTERS,
    VALID_USB_ROLES,
    VALID_WIFI_MODES,
    WIFI_APPFW_FX3_MARKERS,
    WIFI_APPFW_FX6_MARKERS,
    WIFI_CP_SHARED_MARKERS,
    WIFI_SENCORE_SHARED_MARKERS,
    WIFI_SUPPORTED_BANDS,
    WLAN_ADJUST_MARKERS,
    WLAN_RESOURCE_MARKERS,
    analyze_realhw_wifi_bt_usb_uvc_network_bridge,
    build_clean_room_realhw_wifi_bt_usb_network_fixtures,
    build_phase152_network_usb_matrix,
    evaluate_bt_ble_daemon_bridge,
    evaluate_phase152_write_guard,
    evaluate_usb_multi_role_bridge,
    evaluate_wifi_rf_nvs_isolation,
    evaluate_wired_ether_ftp_mc_bridge,
    realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_wifi_bt_usb_uvc_network_bridge_auditor.py"
)


class TestRealhwWifiBtUsbUvcNetworkBridge(unittest.TestCase):
    """Comprehensive dual-mode tests (46 tests) for the 31st unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_152_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_152_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(rep.rf_nvs_mutation_bytes, 0)
        self.assertTrue(rep.usb_msc_0da1_recovery_intact)
        self.assertTrue(rep.bt_hci_blocking_wait_eliminated)
        self.assertEqual(rep.bt_hci_blocking_wait_ms, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertTrue(rep.pillar1_wifi_rf_nvs.passed)
        self.assertTrue(rep.pillar2_bt_ble_bridge.passed)
        self.assertTrue(rep.pillar3_usb_multi_role.passed)
        self.assertTrue(rep.pillar4_wired_ether_ftp_mc.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), 79_015_712)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), 50_520_424)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), 377_328)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), 401_952)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), 15_980_568)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), 17_952_816)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), 2_229_740)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), 2_253_333)
            self.assertEqual(rep.donor_file_sizes.get("fx3_msc_server"), EXPECTED_MSC_SERVER_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_msc_server"), EXPECTED_MSC_SERVER_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx3_usb_control"), EXPECTED_USB_CONTROL_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_usb_control"), EXPECTED_USB_CONTROL_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx3_wlan_adjust"), EXPECTED_WLAN_ADJUST_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_wlan_adjust"), EXPECTED_WLAN_ADJUST_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx3_wlan_resource"), EXPECTED_WLAN_RESOURCE_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_wlan_resource"), EXPECTED_WLAN_RESOURCE_BYTES)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        payload = realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_152_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in (
            "os.O_WRONLY",
            "os.O_RDWR",
            "os.O_CREAT",
            "mmap.ACCESS_WRITE",
            ".write_bytes(",
            ".write_text(",
        ):
            self.assertNotIn(forbidden, src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in (
                "O_WRONLY",
                "O_RDWR",
                "O_CREAT",
                "ACCESS_WRITE",
            ):
                self.fail(f"Forbidden write attribute {node.attr} in auditor AST")

    def test_07_package_exports_and_all_include_phase152_symbols(self) -> None:
        expected_symbols = (
            "PHASE_152_SCHEMA",
            "PHASE_152_VERSION",
            "USB_VID_SONY_HEX",
            "USB_PID_FX3_MSC_HEX",
            "USB_PID_FX3_SERVICE_HEX",
            "EXPECTED_MSC_SERVER_BYTES",
            "EXPECTED_USB_CONTROL_BYTES",
            "EXPECTED_WLAN_ADJUST_BYTES",
            "EXPECTED_WLAN_RESOURCE_BYTES",
            "EXPECTED_FX3_BT_CORE_EXPORTS",
            "EXPECTED_FX6_BT_CORE_EXPORTS",
            "EXPECTED_FX3_BLE_EXPORTS",
            "EXPECTED_FX6_BLE_EXPORTS",
            "EXPECTED_FX3_ETHER_EXPORTS",
            "EXPECTED_FX6_ETHER_EXPORTS",
            "WIFI_SUPPORTED_BANDS",
            "VALID_WIFI_MODES",
            "VALID_BT_BRIDGE_SCENARIOS",
            "VALID_USB_ROLES",
            "VALID_ETHER_ADAPTERS",
            "RF_NVS_IMMUTABLE_PARTITIONS",
            "RealhwWifiBtUsbUvcNetworkBridgeReport",
            "analyze_realhw_wifi_bt_usb_uvc_network_bridge",
            "build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            "build_phase152_network_usb_matrix",
            "evaluate_wifi_rf_nvs_isolation",
            "evaluate_bt_ble_daemon_bridge",
            "evaluate_usb_multi_role_bridge",
            "evaluate_wired_ether_ftp_mc_bridge",
            "evaluate_phase152_write_guard",
            "realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        self.assertEqual(len(fx), 30)
        for key, buf in fx.items():
            self.assertIsInstance(buf, bytes, key)
            self.assertGreater(len(buf), 64, key)

    def test_09_cli_audit_realhw_network_usb_bridge_clean_room_and_auto(self) -> None:
        for argv in (
            ["audit-realhw-network-usb-bridge", "--clean-room", "--json"],
            ["audit-realhw-network-usb-bridge", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            obj = json.loads(buf.getvalue())
            self.assertTrue(obj["all_checks_passed"])
            self.assertTrue(obj["o_rdonly_enforced"])
            self.assertFalse(obj["rf_nvs_p12_p13_writes_permitted"])
            self.assertEqual(obj["rf_nvs_mutation_bytes"], 0)
            self.assertTrue(obj["usb_msc_0da1_recovery_intact"])
            self.assertTrue(obj["bt_hci_blocking_wait_eliminated"])
            self.assertEqual(obj["bt_hci_blocking_wait_ms"], 0)
            self.assertFalse(obj["persistent_emmc_writes_authorized"])

    def test_10_run_audit_all_reaches_31_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 31)
        self.assertIn("realhw_wifi_bt_usb_uvc_network_bridge_audit", summary)
        self.assertEqual(
            summary["realhw_wifi_bt_usb_uvc_network_bridge_audit"]["schema_version"],
            PHASE_152_SCHEMA,
        )

    def test_11_cli_audit_all_clean_room_returns_zero_with_31_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 31)

    # ---- Pillar 1: Wi-Fi 802.11ac & p12/p13 RF NVS Isolation ----

    def test_12_pillar1_report_wifi_markers_wlan_abi_and_backup(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p1 = rep.pillar1_wifi_rf_nvs
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_appfw_wifi_hits, len(WIFI_APPFW_FX3_MARKERS))
        self.assertEqual(p1.fx6_appfw_wifi_hits, len(WIFI_APPFW_FX6_MARKERS))
        self.assertEqual(p1.fx3_sencore_wifi_hits, len(WIFI_SENCORE_SHARED_MARKERS))
        self.assertEqual(p1.fx6_sencore_wifi_hits, len(WIFI_SENCORE_SHARED_MARKERS))
        self.assertEqual(p1.fx3_cp_wifi_hits, len(WIFI_CP_SHARED_MARKERS))
        self.assertEqual(p1.fx6_cp_wifi_hits, len(WIFI_CP_SHARED_MARKERS))
        self.assertTrue(p1.wlan_adjust_abi_identical)
        self.assertEqual(p1.fx3_wlan_adjust.export_count, EXPECTED_WLAN_ADJUST_EXPORTS)
        self.assertEqual(p1.fx6_wlan_adjust.export_count, EXPECTED_WLAN_ADJUST_EXPORTS)
        self.assertEqual(p1.fx3_wlan_resource.export_count, EXPECTED_WLAN_RESOURCE_EXPORTS)
        self.assertEqual(p1.fx6_wlan_resource.export_count, EXPECTED_WLAN_RESOURCE_EXPORTS)
        self.assertEqual(p1.fx3_backup_subsystems, 819)
        self.assertEqual(p1.fx6_backup_subsystems, 840)
        self.assertTrue(p1.fx3_backup_checksums_valid)
        self.assertTrue(p1.fx6_backup_checksums_valid)
        self.assertFalse(p1.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(p1.rf_nvs_mutation_bytes, 0)

    def test_13_pillar1_wlan_resource_and_adjust_markers_present(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p1 = rep.pillar1_wifi_rf_nvs
        for tok in WLAN_RESOURCE_MARKERS:
            self.assertGreater(p1.fx3_wlan_resource.marker_hits.get(tok, 0), 0, tok)
            self.assertGreater(p1.fx6_wlan_resource.marker_hits.get(tok, 0), 0, tok)
        for tok in WLAN_ADJUST_MARKERS:
            self.assertGreater(p1.fx3_wlan_adjust.marker_hits.get(tok, 0), 0, tok)
            self.assertGreater(p1.fx6_wlan_adjust.marker_hits.get(tok, 0), 0, tok)

    def test_14_pillar1_airplane_ap_and_station_modes_safe(self) -> None:
        air = evaluate_wifi_rf_nvs_isolation(wifi_mode="AIRPLANE_ISOLATED_P12", band="5GHZ_80211AC")
        self.assertTrue(air.valid)
        self.assertTrue(air.p12_airplane_mode)
        self.assertFalse(air.rf_tx_enabled)
        self.assertFalse(air.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(air.rf_nvs_mutation_bytes, 0)
        self.assertEqual(air.blocking_wait_ms, 0)
        self.assertEqual(air.classification, BRIDGE_CLASS_SHIM_TRANSLATED)

        for mode, band in (("AP_DIRECT", "5GHZ_80211AC"), ("STATION_ROUTER", "2.4GHZ_80211N")):
            res = evaluate_wifi_rf_nvs_isolation(wifi_mode=mode, band=band)
            self.assertTrue(res.valid, (mode, band))
            self.assertTrue(res.rf_tx_enabled)
            self.assertFalse(res.rf_nvs_p12_p13_writes_permitted)
            self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_15_pillar1_rf_nvs_write_attempt_and_blocking_wait_rejected(self) -> None:
        wr = evaluate_wifi_rf_nvs_isolation(
            wifi_mode="RF_NVS_CALIB_WRITE_ATTEMPT", rf_nvs_write_requested=True
        )
        self.assertFalse(wr.valid)
        self.assertFalse(wr.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(wr.rf_nvs_mutation_bytes, 0)
        self.assertEqual(wr.status, "BLOCKED_P12_P13_RF_NVS_WRITE")
        self.assertEqual(wr.classification, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

        wait = evaluate_wifi_rf_nvs_isolation(wifi_mode="AP_DIRECT", blocking_wait_ms=1500)
        self.assertFalse(wait.valid)
        self.assertEqual(wait.status, "BLOCKED_WIFI_DAEMON_BLOCKING_WAIT")

        bad_band = evaluate_wifi_rf_nvs_isolation(band="6GHZ_WIFI6E")
        self.assertFalse(bad_band.valid)
        self.assertEqual(bad_band.status, "BLOCKED_UNSUPPORTED_WIFI_BAND")

        bad_mode = evaluate_wifi_rf_nvs_isolation(wifi_mode="MESH_UNKNOWN")
        self.assertFalse(bad_mode.valid)
        self.assertEqual(bad_mode.status, "BLOCKED_UNKNOWN_WIFI_MODE")

    # ---- Pillar 2: BLE Creators' App vs FX6 No-BT Non-Blocking Bridge ----

    def test_16_pillar2_report_bt_markers_core_and_ble_exports(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p2 = rep.pillar2_bt_ble_bridge
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_appfw_bt_hits, len(BT_APPFW_FX3_MARKERS))
        self.assertEqual(p2.fx6_appfw_bt_hits, len(BT_APPFW_FX6_MARKERS))
        self.assertEqual(p2.fx3_sencore_bt_hits, len(BT_SENCORE_SHARED_MARKERS))
        self.assertEqual(p2.fx6_sencore_bt_hits, len(BT_SENCORE_SHARED_MARKERS))
        self.assertEqual(p2.fx3_cp_hci_hits, len(BT_CP_SHARED_MARKERS))
        self.assertEqual(p2.fx6_cp_hci_hits, len(BT_CP_SHARED_MARKERS))
        self.assertEqual(p2.fx3_bt_core.export_count, EXPECTED_FX3_BT_CORE_EXPORTS)
        self.assertEqual(p2.fx6_bt_core.export_count, EXPECTED_FX6_BT_CORE_EXPORTS)
        self.assertEqual(p2.fx3_ble_le.export_count, EXPECTED_FX3_BLE_EXPORTS)
        self.assertEqual(p2.fx6_ble_le.export_count, EXPECTED_FX6_BLE_EXPORTS)
        self.assertEqual(p2.bt_hci_blocking_wait_ms, 0)
        self.assertTrue(p2.bt_hci_blocking_wait_eliminated)

    def test_17_pillar2_bt_core_markers_present_both_bodies(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p2 = rep.pillar2_bt_ble_bridge
        for tok in BT_CORE_MARKERS:
            self.assertGreater(p2.fx3_bt_core.marker_hits.get(tok, 0), 0, tok)
            self.assertGreater(p2.fx6_bt_core.marker_hits.get(tok, 0), 0, tok)

    def test_18_pillar2_fx6_no_ble_masked_nonblocking_returns_0ms(self) -> None:
        masked = evaluate_bt_ble_daemon_bridge(
            scenario="FX6_NO_BLE_NONBLOCK_MASKED",
            bt_hci_blocking_wait_ms=0,
            mask_fx6_daemon_mismatch=True,
        )
        self.assertTrue(masked.valid)
        self.assertTrue(masked.fx6_daemon_masked)
        self.assertEqual(masked.bt_hci_blocking_wait_ms, 0)
        self.assertTrue(masked.bt_hci_blocking_wait_eliminated)
        self.assertFalse(masked.ble_creators_app_active)
        self.assertEqual(masked.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)

        p12 = evaluate_bt_ble_daemon_bridge(scenario="AIRPLANE_P12_BT_OFF")
        self.assertTrue(p12.valid)
        self.assertTrue(p12.bt_hci_blocking_wait_eliminated)

    def test_19_pillar2_fx3_creators_ble_and_unmasked_hang_blocked(self) -> None:
        fx3_ble = evaluate_bt_ble_daemon_bridge(scenario="FX3_CREATORS_BLE_PAIRING_HOST")
        self.assertTrue(fx3_ble.valid)
        self.assertTrue(fx3_ble.ble_creators_app_active)
        self.assertEqual(fx3_ble.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

        hang = evaluate_bt_ble_daemon_bridge(
            scenario="FX6_DAEMON_BLOCKING_WAIT_UNMASKED",
            bt_hci_blocking_wait_ms=5000,
            mask_fx6_daemon_mismatch=False,
        )
        self.assertFalse(hang.valid)
        self.assertFalse(hang.bt_hci_blocking_wait_eliminated)
        self.assertEqual(hang.status, "BLOCKED_BT_DAEMON_UNMASKED_HANG")

        nonzero_wait = evaluate_bt_ble_daemon_bridge(
            scenario="FX6_NO_BLE_NONBLOCK_MASKED", bt_hci_blocking_wait_ms=250
        )
        self.assertFalse(nonzero_wait.valid)
        self.assertEqual(nonzero_wait.status, "BLOCKED_BT_HCI_BLOCKING_WAIT")

        bdaddr_wr = evaluate_bt_ble_daemon_bridge(
            scenario="BT_NVS_BDADDR_WRITE_ATTEMPT", rf_nvs_write_requested=True
        )
        self.assertFalse(bdaddr_wr.valid)
        self.assertEqual(bdaddr_wr.rf_nvs_mutation_bytes, 0)
        self.assertEqual(bdaddr_wr.status, "BLOCKED_BT_BDADDR_NVS_WRITE")

        bad_scen = evaluate_bt_ble_daemon_bridge(scenario="CLASSIC_A2DP_SINK")
        self.assertFalse(bad_scen.valid)
        self.assertEqual(bad_scen.status, "BLOCKED_UNKNOWN_BT_SCENARIO")

    # ---- Pillar 3: USB Type-C Multi-Role (MSC 054C:0DA1, MTP, UVC/UAC) ----

    def test_20_pillar3_report_msc_and_usb_control_abi_identical(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p3 = rep.pillar3_usb_multi_role
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_appfw_usb_hits, len(USB_APPFW_FX3_MARKERS))
        self.assertEqual(p3.fx6_appfw_usb_hits, len(USB_APPFW_FX6_MARKERS))
        self.assertTrue(p3.msc_server_abi_identical)
        self.assertTrue(p3.usb_control_abi_identical)
        self.assertEqual(p3.fx3_msc_server.export_count, EXPECTED_MSC_SERVER_EXPORTS)
        self.assertEqual(p3.fx3_msc_server.import_count, EXPECTED_MSC_SERVER_IMPORTS)
        self.assertEqual(p3.fx3_usb_control.export_count, EXPECTED_USB_CONTROL_EXPORTS)
        self.assertEqual(p3.fx3_usb_control.import_count, EXPECTED_USB_CONTROL_IMPORTS)
        self.assertEqual(p3.fx3_usb_cmn.export_count, 479)
        self.assertEqual(p3.fx6_usb_cmn.export_count, 503)
        self.assertEqual(p3.fx3_ptp_control.export_count, 456)
        self.assertEqual(p3.fx6_ptp_control.export_count, 435)
        self.assertTrue(p3.usb_msc_0da1_recovery_intact)

    def test_21_pillar3_usb_markers_present_in_cmn_ctrl_and_msc(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p3 = rep.pillar3_usb_multi_role
        for tok in MSC_SERVER_MARKERS:
            self.assertGreater(p3.fx3_msc_server.marker_hits.get(tok, 0), 0, tok)
        for tok in USB_CONTROL_MARKERS:
            self.assertGreater(p3.fx3_usb_control.marker_hits.get(tok, 0), 0, tok)
        for tok in USB_CMN_MARKERS:
            self.assertGreater(p3.fx3_usb_cmn.marker_hits.get(tok, 0), 0, tok)

    def test_22_pillar3_msc_0da1_and_service_0336_and_mtp_passthrough(self) -> None:
        self.assertEqual(USB_VID_SONY_HEX, "0x054C")
        self.assertEqual(USB_PID_FX3_MSC_HEX, "0x0DA1")
        self.assertEqual(USB_PID_FX3_SERVICE_HEX, "0x0336")

        msc = evaluate_usb_multi_role_bridge(usb_role="MSC_RECOVERY_054C_0DA1")
        self.assertTrue(msc.valid)
        self.assertEqual(msc.usb_vid_pid, "054C:0DA1")
        self.assertTrue(msc.usb_msc_0da1_recovery_intact)
        self.assertTrue(msc.service_0336_reachable)
        self.assertEqual(msc.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

        svc = evaluate_usb_multi_role_bridge(usb_role="SERVICE_HANDSHAKE_054C_0336")
        self.assertTrue(svc.valid)
        self.assertEqual(svc.usb_vid_pid, "054C:0336")
        self.assertTrue(svc.service_0336_reachable)

        mtp = evaluate_usb_multi_role_bridge(usb_role="MTP_PTP_REMOTE_SHOOTING")
        self.assertTrue(mtp.valid)
        self.assertTrue(mtp.usb_msc_0da1_recovery_intact)
        self.assertEqual(mtp.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_23_pillar3_uvc_hdmi_bridge_and_msc_hijack_blocked(self) -> None:
        uvc_ext = evaluate_usb_multi_role_bridge(usb_role="UVC_UAC_HDMI_CAPTURE_BRIDGE")
        self.assertTrue(uvc_ext.valid)
        self.assertTrue(uvc_ext.uvc_via_hdmi_bridge_only)
        self.assertTrue(uvc_ext.usb_msc_0da1_recovery_intact)
        self.assertEqual(uvc_ext.classification, BRIDGE_CLASS_SHIM_TRANSLATED)

        uvc_masked = evaluate_usb_multi_role_bridge(
            usb_role="FX6_NATIVE_USB_STREAMING_MASKED", mask_fx6_native_uvc=True
        )
        self.assertTrue(uvc_masked.valid)
        self.assertTrue(uvc_masked.usb_msc_0da1_recovery_intact)
        self.assertEqual(uvc_masked.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)

        hijack = evaluate_usb_multi_role_bridge(
            usb_role="UNMASKED_UVC_HIJACKING_MSC", preserve_msc_0da1=False
        )
        self.assertFalse(hijack.valid)
        self.assertFalse(hijack.usb_msc_0da1_recovery_intact)
        self.assertEqual(hijack.status, "BLOCKED_MSC_0DA1_RECOVERY_BREAK")

        unmasked_fx6_uvc = evaluate_usb_multi_role_bridge(
            usb_role="FX6_NATIVE_USB_STREAMING_MASKED", mask_fx6_native_uvc=False
        )
        self.assertFalse(unmasked_fx6_uvc.valid)
        self.assertEqual(unmasked_fx6_uvc.status, "BLOCKED_UNMASKED_FX6_USB_STREAMING")

        bad_rc = evaluate_usb_multi_role_bridge(non_blocking_stub_rc=-50)
        self.assertFalse(bad_rc.valid)
        self.assertEqual(bad_rc.status, "BLOCKED_USB_STUB_NONZERO_RC")

        bad_role = evaluate_usb_multi_role_bridge(usb_role="ADB_GADGET")
        self.assertFalse(bad_role.valid)
        self.assertEqual(bad_role.status, "BLOCKED_UNKNOWN_USB_ROLE")

    # ---- Pillar 4: Wired USB-LAN Gigabit Ethernet FTP & Monitor & Control ----

    def test_24_pillar4_report_ether_ftp_sencore_and_im_elf(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p4 = rep.pillar4_wired_ether_ftp_mc
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fx3_sencore_ether_hits, len(ETHER_SENCORE_FX3_MARKERS))
        self.assertEqual(p4.fx6_sencore_wol_extra_hits, len(ETHER_SENCORE_FX6_EXTRA_MARKERS))
        self.assertGreaterEqual(p4.fx3_cp_ether_hits, 1)
        self.assertEqual(p4.fx3_net_ether.export_count, EXPECTED_FX3_ETHER_EXPORTS)
        self.assertEqual(p4.fx6_net_ether.export_count, EXPECTED_FX6_ETHER_EXPORTS)
        self.assertEqual(p4.fx3_ftp_client.export_count, 599)
        self.assertEqual(p4.fx6_ftp_client.export_count, 605)
        self.assertTrue(p4.im_elf_abi_identical)
        self.assertTrue(p4.wired_usblan_passthrough_verified)

    def test_25_pillar4_netservice_and_ftp_markers_present(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p4 = rep.pillar4_wired_ether_ftp_mc
        for tok in ETHER_NETSERVICE_SHARED_MARKERS:
            self.assertGreater(p4.fx3_net_ether.marker_hits.get(tok, 0), 0, tok)
            self.assertGreater(p4.fx6_net_ether.marker_hits.get(tok, 0), 0, tok)
        for tok in ETHER_NETSERVICE_FX6_EXTRA_MARKERS:
            self.assertGreater(p4.fx6_net_ether.marker_hits.get(tok, 0), 0, tok)
        for tok in ETHER_FTP_SHARED_MARKERS:
            self.assertGreater(p4.fx3_ftp_client.marker_hits.get(tok, 0), 0, tok)
            self.assertGreater(p4.fx6_ftp_client.marker_hits.get(tok, 0), 0, tok)

    def test_26_pillar4_gigabit_cdc_ncm_ftp_mc_and_p12_isolation(self) -> None:
        for prof in ("CDC_NCM_RTL8153_GIGABIT", "CDC_NCM_AX88179_GIGABIT"):
            res = evaluate_wired_ether_ftp_mc_bridge(adapter_profile=prof, p12_airplane_mode_on=True)
            self.assertTrue(res.valid, prof)
            self.assertEqual(res.link_speed_mbps, 1000)
            self.assertTrue(res.p12_rf_off_compliant)
            self.assertTrue(res.ftp_ftpes_supported)
            self.assertTrue(res.monitor_control_ptpip_supported)
            self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

        teth = evaluate_wired_ether_ftp_mc_bridge(
            adapter_profile="USB_TETHERING_CDC_NCM", p12_airplane_mode_on=True
        )
        self.assertTrue(teth.valid)
        self.assertEqual(teth.link_speed_mbps, 480)
        self.assertEqual(teth.classification, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_27_pillar4_absent_wol_unplugged_nonblock_and_p12_violations_blocked(self) -> None:
        wol_masked = evaluate_wired_ether_ftp_mc_bridge(
            adapter_profile="FX6_WIREDLAN_WOL_DOCK_ABSENT", mask_absent_wol_hw=True
        )
        self.assertTrue(wol_masked.valid)
        self.assertEqual(wol_masked.blocking_wait_ms, 0)
        self.assertEqual(wol_masked.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)

        wol_unmasked = evaluate_wired_ether_ftp_mc_bridge(
            adapter_profile="FX6_WIREDLAN_WOL_DOCK_ABSENT", mask_absent_wol_hw=False
        )
        self.assertFalse(wol_unmasked.valid)
        self.assertEqual(wol_unmasked.status, "BLOCKED_UNMASKED_FX6_WOL_HW")

        wifi_under_p12 = evaluate_wired_ether_ftp_mc_bridge(
            adapter_profile="WIFI_WLAN0_UNDER_P12", p12_airplane_mode_on=True
        )
        self.assertFalse(wifi_under_p12.valid)
        self.assertFalse(wifi_under_p12.p12_rf_off_compliant)
        self.assertEqual(wifi_under_p12.status, "BLOCKED_WIFI_WLAN0_UNDER_P12")

        wait = evaluate_wired_ether_ftp_mc_bridge(
            adapter_profile="UNPLUGGED_ETHER_DONGLE_NONBLOCK", blocking_wait_ms=1000
        )
        self.assertFalse(wait.valid)
        self.assertEqual(wait.status, "BLOCKED_ETHER_BLOCKING_WAIT")

        unk = evaluate_wired_ether_ftp_mc_bridge(adapter_profile="FIBRE_SFP_10G")
        self.assertFalse(unk.valid)
        self.assertEqual(unk.status, "BLOCKED_UNKNOWN_ETHER_PROFILE")

    # ---- Compatibility Matrix & Persistent Write-Guard ----

    def test_28_compatibility_matrix_12_touchpoints_and_four_classes(self) -> None:
        matrix = build_phase152_network_usb_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(len(matrix.touchpoints), 12)
        self.assertEqual(sum(matrix.class_counts.values()), 12)
        self.assertEqual(sum(matrix.subsystem_counts.values()), 12)
        for cls in (
            BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            BRIDGE_CLASS_SHIM_TRANSLATED,
            BRIDGE_CLASS_MASKED_ABSENT_HW,
            BRIDGE_CLASS_HARD_WRITE_PROTECTED,
        ):
            self.assertGreater(matrix.class_counts[cls], 0, cls)
        for sub in ("WIFI_RF", "BT_BLE", "USB_MULTI_ROLE", "WIRED_ETHER_FTP"):
            self.assertGreater(matrix.subsystem_counts[sub], 0, sub)
        for tp in matrix.touchpoints:
            self.assertTrue(tp.blocking_wait_eliminated, tp.touchpoint_id)
            self.assertTrue(tp.write_protected, tp.touchpoint_id)

    def test_29_write_guard_allows_volatile_ram_staging_only(self) -> None:
        for path in (
            "/tmp/stage_b/wifi_bt_shadow.json",
            "/var/run/wpa_supplicant_stageb.pid",
            "ram://stage_b/usb_role_mask.json",
        ):
            res = evaluate_phase152_write_guard(path)
            self.assertTrue(res.valid, path)
            self.assertTrue(res.volatile_ram_staged)
            self.assertFalse(res.persistent_write_blocked)
            self.assertFalse(res.rf_nvs_p12_p13_writes_permitted)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertEqual(res.rf_nvs_mutation_bytes, 0)

    def test_30_write_guard_blocks_p12_p13_rf_nvs_backup_and_emmc(self) -> None:
        for bad_path in (
            "p12:/cert/device_cert.bin",
            "p13:/rf_nvs/tx_power.bin",
            "/dev/nflasha12",
            "/dev/cnflasha13",
            "/dev/nflasha23/INFO/WIFI_INF.TXT",
            "/dev/nflasha23/INFO/WPS_PIN.TXT",
            "p2:/Backup.bin",
            "/dev/mmcblk0p12",
            "/tmp/rf_nvs_dump.bin",
            "/tmp/bdaddr.bin",
        ):
            res = evaluate_phase152_write_guard(bad_path)
            self.assertFalse(res.valid, bad_path)
            self.assertFalse(res.volatile_ram_staged)
            self.assertTrue(res.persistent_write_blocked)
            self.assertFalse(res.rf_nvs_p12_p13_writes_permitted)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertEqual(res.rf_nvs_mutation_bytes, 0)
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_RF_NVS_OR_EMMC_WRITE")

    # ---- Enum Coverage, Corrupted Fixture Rejection & Cross-Invariants ----

    def test_31_all_valid_wifi_modes_handled_consistently(self) -> None:
        self.assertEqual(len(VALID_WIFI_MODES), 4)
        self.assertEqual(WIFI_SUPPORTED_BANDS, ("2.4GHZ_80211N", "5GHZ_80211AC"))
        for mode in VALID_WIFI_MODES:
            res = evaluate_wifi_rf_nvs_isolation(wifi_mode=mode)
            if mode == "RF_NVS_CALIB_WRITE_ATTEMPT":
                self.assertFalse(res.valid)
            else:
                self.assertTrue(res.valid, mode)

    def test_32_all_valid_bt_scenarios_handled_consistently(self) -> None:
        self.assertEqual(len(VALID_BT_BRIDGE_SCENARIOS), 5)
        for scen in VALID_BT_BRIDGE_SCENARIOS:
            is_bad = scen in ("FX6_DAEMON_BLOCKING_WAIT_UNMASKED", "BT_NVS_BDADDR_WRITE_ATTEMPT")
            res = evaluate_bt_ble_daemon_bridge(
                scenario=scen,
                mask_fx6_daemon_mismatch=(scen != "FX6_DAEMON_BLOCKING_WAIT_UNMASKED"),
            )
            self.assertEqual(res.valid, not is_bad, scen)

    def test_33_all_valid_usb_roles_handled_consistently(self) -> None:
        self.assertEqual(len(VALID_USB_ROLES), 7)
        for role in VALID_USB_ROLES:
            res = evaluate_usb_multi_role_bridge(usb_role=role)
            if role == "UNMASKED_UVC_HIJACKING_MSC":
                self.assertFalse(res.valid)
            else:
                self.assertTrue(res.valid, role)

    def test_34_all_valid_ether_adapters_handled_consistently(self) -> None:
        self.assertEqual(len(VALID_ETHER_ADAPTERS), 6)
        for prof in VALID_ETHER_ADAPTERS:
            res = evaluate_wired_ether_ftp_mc_bridge(adapter_profile=prof, p12_airplane_mode_on=True)
            if prof == "WIFI_WLAN0_UNDER_P12":
                self.assertFalse(res.valid)
            else:
                self.assertTrue(res.valid, prof)

    def test_35_rf_nvs_immutable_partitions_all_blocked_by_write_guard(self) -> None:
        self.assertGreaterEqual(len(RF_NVS_IMMUTABLE_PARTITIONS), 8)
        for part in RF_NVS_IMMUTABLE_PARTITIONS:
            res = evaluate_phase152_write_guard(part)
            self.assertTrue(res.persistent_write_blocked, part)
            self.assertFalse(res.rf_nvs_p12_p13_writes_permitted, part)

    def test_36_im_elf_dt_needed_and_sencore_counts_parity(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p4 = rep.pillar4_wired_ether_ftp_mc
        self.assertEqual(p4.fx3_im_elf.dt_needed, p4.fx6_im_elf.dt_needed)
        self.assertEqual(p4.fx3_im_elf.export_count, 11)
        self.assertEqual(p4.fx3_im_elf.import_count, 85)
        self.assertEqual(EXPECTED_SENCORE_EXPORTS, 355)
        self.assertEqual(EXPECTED_SENCORE_IMPORTS, 130)

    def test_37_report_dict_top_level_keys_complete(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        d = realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict(rep)
        for key in (
            "schema_version",
            "phase_version",
            "mode",
            "all_checks_passed",
            "o_rdonly_enforced",
            "rf_nvs_p12_p13_writes_permitted",
            "rf_nvs_mutation_bytes",
            "usb_msc_0da1_recovery_intact",
            "bt_hci_blocking_wait_eliminated",
            "bt_hci_blocking_wait_ms",
            "persistent_emmc_writes_authorized",
            "emmc_mutation_bytes",
            "calibration_mutation_bytes",
            "donor_file_sizes",
            "pillar1_wifi_rf_nvs",
            "pillar2_bt_ble_bridge",
            "pillar3_usb_multi_role",
            "pillar4_wired_ether_ftp_mc",
            "compatibility_matrix",
            "volatile_guard_ok",
            "forbidden_p12_guard_blocked",
            "forbidden_p13_guard_blocked",
            "forbidden_backup_guard_blocked",
            "report_sha256",
            "errors",
        ):
            self.assertIn(key, d)

    def test_38_corrupted_backup_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx["fx3_backup"] = b"\x00" * 64
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar1_wifi_rf_nvs.passed)

    def test_39_corrupted_cpapp_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx["fx3_cpapp"] = b"\x00" * 128
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar1_wifi_rf_nvs.passed)
        self.assertFalse(rep.pillar2_bt_ble_bridge.passed)
        self.assertFalse(rep.pillar4_wired_ether_ftp_mc.passed)

    def test_40_corrupted_msc_server_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx["fx6_msc_server"] = fx["fx3_wlan_resource"]
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar3_usb_multi_role.passed)

    def test_41_corrupted_net_ether_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx["fx6_net_ether"] = fx["fx3_net_ether"]
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar4_wired_ether_ftp_mc.passed)

    def test_42_corrupted_wlan_adjust_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx["fx6_wlan_adjust"] = fx["fx3_wlan_resource"]
        with mock.patch(
            "fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor.build_clean_room_realhw_wifi_bt_usb_network_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar1_wifi_rf_nvs.passed)

    def test_43_auto_mode_sha256_deterministic_across_runs(self) -> None:
        r1 = analyze_realhw_wifi_bt_usb_uvc_network_bridge()
        r2 = analyze_realhw_wifi_bt_usb_uvc_network_bridge()
        self.assertEqual(r1.mode, r2.mode)
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_44_write_guards_in_report_consistent(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        self.assertTrue(rep.volatile_guard_ok.valid)
        self.assertTrue(rep.volatile_guard_ok.volatile_ram_staged)
        self.assertTrue(rep.forbidden_p12_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_p13_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_backup_guard_blocked.persistent_write_blocked)

    def test_45_cross_body_export_delta_invariants(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=True)
        p2 = rep.pillar2_bt_ble_bridge
        p3 = rep.pillar3_usb_multi_role
        p4 = rep.pillar4_wired_ether_ftp_mc
        # FX3 BLE has more exports than FX6 (1340 vs 1053), while FX6 Ether has more than FX3 (480 vs 286)
        self.assertGreater(p2.fx3_ble_le.export_count, p2.fx6_ble_le.export_count)
        self.assertGreater(p4.fx6_net_ether.export_count, p4.fx3_net_ether.export_count)
        self.assertGreater(p3.fx6_usb_cmn.export_count, p3.fx3_usb_cmn.export_count)
        self.assertGreater(p3.fx3_ptp_control.export_count, p3.fx6_ptp_control.export_count)

    def test_46_local_donor_specific_invariants_when_present(self) -> None:
        rep = analyze_realhw_wifi_bt_usb_uvc_network_bridge()
        if rep.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Local BYOF donors absent in clean-room environment")
        self.assertEqual(rep.donor_file_sizes.get("fx3_bt_core"), 267_592)
        self.assertEqual(rep.donor_file_sizes.get("fx6_bt_core"), 267_576)
        self.assertEqual(rep.donor_file_sizes.get("fx3_ble_le"), 648_328)
        self.assertEqual(rep.donor_file_sizes.get("fx6_ble_le"), 530_488)
        self.assertEqual(rep.donor_file_sizes.get("fx3_net_ether"), 114_384)
        self.assertEqual(rep.donor_file_sizes.get("fx6_net_ether"), 175_376)
        self.assertEqual(rep.donor_file_sizes.get("fx3_ftp_client"), 232_368)
        self.assertEqual(rep.donor_file_sizes.get("fx6_ftp_client"), 231_816)
        self.assertEqual(rep.donor_file_sizes.get("fx3_ptp_control"), 165_320)
        self.assertEqual(rep.donor_file_sizes.get("fx6_ptp_control"), 152_520)
        self.assertEqual(rep.donor_file_sizes.get("fx3_usb_cmn"), 159_504)
        self.assertEqual(rep.donor_file_sizes.get("fx6_usb_cmn"), 164_144)


if __name__ == "__main__":
    unittest.main()
