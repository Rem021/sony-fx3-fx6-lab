#!/usr/bin/env python3
"""Phase 58 Test Suite — Stage 7 Non-Intrusive QMP Guest Introspection & USB-LAN PTP-IP Tracer.

Exercises 28 fast unit, protocol, policy, Stage 7 integration, CLI, and hygiene tests across
BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import struct
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import qmp_guest_introspection_tracer as p58  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p58.run_phase58_qmp_tracer_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase58DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY USB-LAN/PTP-IP donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_6_artifacts_and_sha256(self) -> None:
        audit = p58.inspect_usblan_ptpip_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p58.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p58.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p58.is_forced_clean_room(env))
        paths = p58.resolve_phase58_donor_paths(env=env)
        self.assertEqual(len(paths), 6)
        for path in paths.values():
            self.assertIn(p58.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p58.inspect_usblan_ptpip_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p58.is_forced_clean_room():
            audit = p58.inspect_usblan_ptpip_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p58.resolve_phase58_donor_paths()
        audit = p58.inspect_usblan_ptpip_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 6)
            for key, (expected_bytes, expected_sha) in p58.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p58.ENV_MAC_WORK_ROOT: "/nonexistent_phase58_mac_work_root",
            p58.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase58_main_work_root",
        }
        audit = p58.inspect_usblan_ptpip_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_guest_modification_and_zero_writes(self) -> None:
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
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestQmpProtocolAndGuestDecoders(unittest.TestCase):
    """Verify QMP JSON-RPC protocol negotiation, HMP xp, pmemsave decoders, and TCG/GDB specs."""

    def test_06_qmp_greeting_and_pre_capability_command_rejected(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        self.assertIn("QMP", client.greeting)
        self.assertIn("oob", client.greeting["QMP"]["capabilities"])
        self.assertFalse(transport.negotiated)
        with self.assertRaises(p58.QmpProtocolError):
            client.query_status()
        self.assertFalse(transport.negotiated)

    def test_07_qmp_capabilities_query_status_and_4_aarch64_vcpus(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        self.assertEqual(client.negotiate_capabilities(enable_oob=True), {})
        self.assertTrue(transport.negotiated)
        # Re-negotiation is disallowed by QMP
        with self.assertRaises(p58.QmpProtocolError):
            client.negotiate_capabilities()
        status = client.query_status()
        self.assertTrue(status["running"])
        self.assertEqual(status["status"], "running")
        cpus = client.query_cpus_fast()
        self.assertEqual(len(cpus), 4)
        self.assertTrue(all(cpu["target"] == "aarch64" for cpu in cpus))

    def test_08_qmp_hmp_info_registers_and_gva2gpa_mapping(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        client.negotiate_capabilities()
        regs = client.hmp("info registers")
        self.assertIn("PC=ffffff80", regs)
        self.assertIn("4658364c", regs)
        self.assertEqual(client.hmp("gva2gpa 0xffffff8041e00e00").strip(), f"gpa: 0x{p58.CTRL_MB_PHYS:x}")
        self.assertEqual(client.hmp("gva2gpa 0xffffff8041df0000").strip(), f"gpa: 0x{p58.KEY_MB_PHYS:x}")

    def test_09_qmp_hmp_rejects_mutating_or_unknown_commands(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        client.negotiate_capabilities()
        for bad_hmp in ("quit", "system_reset", "sendkey a", "stop", "cont"):
            with self.assertRaises(p58.QmpProtocolError):
                client.hmp(bad_hmp)
        with self.assertRaises(p58.QmpProtocolError):
            client.call("system_powerdown")

    def test_10_pmemsave_rejects_disk_targets_and_supports_mem_uri(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        client.negotiate_capabilities()
        with self.assertRaises(p58.QmpProtocolError):
            client.pmemsave_capture(p58.KEY_MB_PHYS, 64, "/tmp/should_not_write.bin")
        blob = client.pmemsave_capture(p58.KEY_MB_PHYS, 64, "mem://key_mb.bin")
        self.assertEqual(len(blob), 64)
        self.assertEqual(blob[:8], p58.KEY_MB_MAGIC_LE)

    def test_11_hmp_xp_and_decode_key_mailbox_srm3kye5(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        client.negotiate_capabilities()
        words = client.hmp_xp_u32(p58.KEY_MB_PHYS, 16)
        snap = p58.decode_key_mailbox_bytes(struct.pack("<16I", *words))
        self.assertTrue(snap.magic_valid)
        self.assertEqual(snap.magic_ascii, "SRM3KYE5")
        self.assertEqual(snap.phys_addr_hex, f"0x{p58.KEY_MB_PHYS:x}")
        self.assertEqual(snap.seq, 7)
        self.assertEqual(snap.ack_seq, 7)

    def test_12_hmp_xp_and_decode_ctrl_mailbox_fx6l_p4_nd_clear_and_bk4(self) -> None:
        transport = p58.SimulatedQmpGuestTransport()
        client = p58.QmpGuestIntrospectionClient(transport)
        client.negotiate_capabilities()
        words = client.hmp_xp_u32(p58.CTRL_MB_PHYS, p58.CTRL_MB_WORDS)
        ctrl = p58.decode_ctrl_mailbox_bytes(struct.pack(f"<{p58.CTRL_MB_WORDS}I", *words))
        self.assertTrue(ctrl.magic_valid)
        self.assertEqual(ctrl.ctrl_magic_hex, "0x4658364c")
        self.assertEqual(ctrl.nd_p4_locked_val, 0)
        self.assertTrue(ctrl.bk4_locked)
        self.assertTrue(ctrl.phase40_valid)
        self.assertEqual(ctrl.ei_iso_val, 800)
        self.assertEqual(ctrl.fx3_p10_hwcode_hex, "0x00137095")

    def test_13_pmemsave_gpe0_framebuffer_fx6_px_amber_parity(self) -> None:
        rep = _get_clean_room_audit()
        gpe = rep["guest_introspection"]["gpe0_probe"]
        self.assertEqual(gpe["phys_addr_hex"], f"0x{p58.GPE0_PHYS:x}")
        self.assertEqual(gpe["amber_px_hex"], "0xfff08018")
        self.assertTrue(gpe["fx6_px_amber_parity_ok"])
        self.assertGreater(gpe["nonzero_pixels_sampled"], 0)
        self.assertGreaterEqual(gpe["unique_colors_sampled"], 3)

    def test_14_pmemsave_mhlx_mmio_and_ring_buffer_slot_decoder(self) -> None:
        rep = _get_clean_room_audit()
        mhlx = rep["guest_introspection"]["mhlx_ring"]
        self.assertTrue(mhlx["magic_valid"])
        self.assertEqual(mhlx["mmio_base_hex"], f"0x{p58.MHLX_PHYS:x}")
        self.assertEqual(mhlx["shm_ring_phys_hex"], f"0x{p58.MHLX_RING_SHM_PHYS:x}")
        self.assertEqual(mhlx["cp_mutation_bytes"], 0)
        self.assertEqual(mhlx["ch0_tx_head"], 2)
        self.assertEqual(mhlx["ch0_rx_head"], 2)
        self.assertEqual(mhlx["decoded_slot_count"], 2)
        self.assertEqual(mhlx["decoded_opcodes_hex"], ["0x0416", "0x0400"])

    def test_15_decoders_reject_invalid_magic_or_truncated_buffers(self) -> None:
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_key_mailbox_bytes(b"\x00" * 16)
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_key_mailbox_bytes(b"BADMAGIC" + b"\x00" * 56)
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_ctrl_mailbox_bytes(b"\x00" * 16)
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_ctrl_mailbox_bytes(b"\x00" * p58.CTRL_MB_BYTES)
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_gpe0_framebuffer_slice(b"\x00" * 16, width=64, height=32)
        with self.assertRaises(p58.IntrospectionDecodeError):
            p58.decode_mhlx_ring_snapshot(b"\x00" * 0x180, b"\x00" * 64)

    def test_16_tcg_plugin_and_gdb_rsp_specs_zero_sw_breakpoints(self) -> None:
        specs = p58.build_tcg_plugin_and_gdb_specs()
        self.assertEqual(specs["nop_count"], 0)
        self.assertEqual(specs["guest_code_modification_bytes"], 0)
        self.assertEqual(specs["cp_mutation_bytes"], 0)
        self.assertEqual(specs["tcg_plugin_spec"]["header"], "include/plugins/qemu-plugin.h")
        self.assertIn("qemu_plugin_read_memory_hwaddr", specs["tcg_plugin_spec"]["callbacks"])
        self.assertEqual(specs["gdb_rsp_spec"]["physical_memory_mode_packet"], "Qqemu.PhyMemMode:1")
        self.assertEqual(specs["gdb_rsp_spec"]["guest_text_sw_breakpoints"], 0)
        self.assertTrue(specs["gdb_rsp_spec"]["unlimited_hw_watchpoints"])


class TestUsbLanP12IsolationAndPtpIpSafeChannel(unittest.TestCase):
    """Verify wired USB-LAN (CDC-NCM vs RNDIS) under P12 Airplane-Mode and PTP-IP 15740 gating."""

    def test_17_fx3_usblan_cdc_ncm_rtl8153_p12_airplane_wf12_immune(self) -> None:
        res = p58.evaluate_usblan_link_under_p12(
            camera_body="ILME-FX3",
            usb_class=p58.USB_CLASS_CDC_NCM,
            chipset="RTL8153",
            link_speed_mbps=1000,
            ip_mode="Manual",
            camera_ip="192.168.0.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.0.1",
            p12_airplane_mode=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "ALLOWED_USB_LAN_LINK_UP")
        self.assertTrue(res.p12_airplane_mode)
        self.assertTrue(res.wlan_disabled)
        self.assertTrue(res.bt_disabled)
        self.assertTrue(res.wf12_00342260_immune)
        self.assertTrue(res.gateway_same_subnet)
        self.assertEqual(res.wdt_resets, 0)
        self.assertTrue(any("Monitor & Control" in f for f in res.monitoring_features))

    def test_18_fx6_usblan_cdc_ncm_ax88179_p12_cbm_and_mc_up(self) -> None:
        res = p58.evaluate_usblan_link_under_p12(
            camera_body="ILME-FX6",
            usb_class=p58.USB_CLASS_CDC_NCM,
            chipset="AX88179",
            link_speed_mbps=1000,
            ip_mode="Auto",
            p12_airplane_mode=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.wf12_00342260_immune)
        self.assertTrue(any("Content Browser Mobile" in f for f in res.monitoring_features))

    def test_19_usblan_rejects_rndis_and_cdc_ecm(self) -> None:
        for usb_cls in (p58.USB_CLASS_RNDIS, p58.USB_CLASS_CDC_ECM):
            res = p58.evaluate_usblan_link_under_p12(
                camera_body="ILME-FX3",
                usb_class=usb_cls,
                chipset="RTL8153",
            )
            self.assertFalse(res.passed)
            self.assertEqual(res.status, f"REJECTED_UNSUPPORTED_USB_CLASS_{usb_cls}")

    def test_20_usblan_rejects_ax88179a_2_5g_and_non_1gbps_links(self) -> None:
        for bad_chip in p58.REJECTED_USBLAN_CHIPSETS:
            res = p58.evaluate_usblan_link_under_p12(chipset=bad_chip)
            self.assertFalse(res.passed)
            self.assertEqual(res.status, "REJECTED_INCOMPATIBLE_ADAPTER_CHIPSET_OR_SPEED")

        slow_link = p58.evaluate_usblan_link_under_p12(chipset="RTL8153", link_speed_mbps=2500)
        self.assertFalse(slow_link.passed)
        self.assertEqual(slow_link.status, "REJECTED_INCOMPATIBLE_ADAPTER_CHIPSET_OR_SPEED")

    def test_21_usblan_fx3_manual_ip_requires_same_subnet_gateway(self) -> None:
        missing_gw = p58.evaluate_usblan_link_under_p12(
            ip_mode="Manual",
            camera_ip="192.168.0.10",
            subnet_mask="255.255.255.0",
            default_gateway="",
        )
        self.assertFalse(missing_gw.passed)
        self.assertEqual(missing_gw.status, "MISCONFIGURED_MISSING_SAME_SUBNET_GATEWAY")

        wrong_subnet_gw = p58.evaluate_usblan_link_under_p12(
            ip_mode="Manual",
            camera_ip="192.168.0.10",
            subnet_mask="255.255.255.0",
            default_gateway="10.0.0.1",
        )
        self.assertFalse(wrong_subnet_gw.passed)
        self.assertEqual(wrong_subnet_gw.status, "MISCONFIGURED_MISSING_SAME_SUBNET_GATEWAY")

    def test_22_ptpip_15740_allows_readonly_telemetry_and_whitelisted_props(self) -> None:
        lv = p58.evaluate_ptpip_15740_packet(
            p58.build_ptpip_cmd_request_frame(opcode=p58.PTPIP_OPCODE_SONY_GET_LIVE_VIEW, tx_id=10)
        )
        self.assertTrue(lv.allowed)
        self.assertEqual(lv.decision, "ALLOWED_READONLY_TELEMETRY")
        self.assertEqual(lv.cp_mutation_bytes, 0)

        tf = p58.evaluate_ptpip_15740_packet(
            p58.build_ptpip_cmd_request_frame(
                opcode=p58.PTPIP_OPCODE_SONY_SET_DEVICE_PROP,
                tx_id=11,
                param1=0xD2C1,
            )
        )
        self.assertTrue(tf.allowed)
        self.assertEqual(tf.decision, "ALLOWED_SAFE_MONITOR_CONTROL")

    def test_23_ptpip_15740_blocks_fw_update_nvram_cal_unauth_and_bad_port(self) -> None:
        for fw_opcode in p58.BLOCKED_PTPIP_MUTATION_OPCODES:
            tr = p58.evaluate_ptpip_15740_packet(
                p58.build_ptpip_cmd_request_frame(opcode=fw_opcode, tx_id=20)
            )
            self.assertFalse(tr.allowed)
            self.assertEqual(tr.decision, "BLOCKED_FIRMWARE_UPDATE_OPCODE")
            self.assertEqual(tr.nvram_persistent_writes, 0)

        unauth = p58.evaluate_ptpip_15740_packet(
            p58.build_ptpip_cmd_request_frame(opcode=p58.PTPIP_OPCODE_SONY_GET_LIVE_VIEW, tx_id=21),
            authenticated=False,
        )
        self.assertFalse(unauth.allowed)
        self.assertEqual(unauth.decision, "BLOCKED_UNAUTHENTICATED_SESSION")

        bad_prop = p58.evaluate_ptpip_15740_packet(
            p58.build_ptpip_cmd_request_frame(
                opcode=p58.PTPIP_OPCODE_SONY_SET_DEVICE_PROP,
                tx_id=22,
                param1=0xFFFF,
            )
        )
        self.assertFalse(bad_prop.allowed)
        self.assertEqual(bad_prop.decision, "BLOCKED_UNWHITELISTED_PROP_MUTATION")

        bad_port = p58.evaluate_ptpip_15740_packet(
            p58.build_ptpip_cmd_request_frame(opcode=p58.PTPIP_OPCODE_GET_DEVICE_INFO, tx_id=23),
            tcp_port=8080,
        )
        self.assertFalse(bad_port.allowed)
        self.assertEqual(bad_port.decision, "BLOCKED_UNEXPECTED_TCP_PORT")

    def test_24_ptpip_15740_session_trace_5_allowed_4_blocked_zero_mutations(self) -> None:
        sess = p58.trace_ptpip_15740_session()
        self.assertEqual(sess["tcp_port"], 15740)
        self.assertEqual(sess["ssdp_udp_port"], 1900)
        self.assertEqual(sess["total_packets"], 9)
        self.assertEqual(sess["allowed_count"], 5)
        self.assertEqual(sess["blocked_count"], 4)
        self.assertTrue(sess["fw_update_opcodes_blocked"])
        self.assertEqual(sess["cp_mutation_bytes"], 0)
        self.assertEqual(sess["nvram_persistent_writes"], 0)
        self.assertEqual(sess["physical_device_writes"], 0)


class TestStage7CoEmulationSuiteCliAndHygiene(unittest.TestCase):
    """Verify Stage 7 audit determinism, co-emulation suite wiring, CLI, and source hygiene."""

    def test_25_phase58_audit_determinism_and_digest_verification(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p58.run_phase58_qmp_tracer_audit(force_clean_room=True)
        self.assertEqual(r1, r2)
        self.assertTrue(r1["all_checks_passed"])

        copy_rep = dict(r1)
        recorded = copy_rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_26_coemulation_suite_wires_stage7_and_allows_skip_phase58(self) -> None:
        rep_with = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_phase58_qmp_introspection=True,
            )
        )
        self.assertTrue(rep_with["all_checks_passed"])
        self.assertIn("stage7_phase58_qmp_introspection", rep_with)
        s7 = rep_with["stage7_phase58_qmp_introspection"]
        self.assertTrue(s7["all_checks_passed"])
        self.assertEqual(s7["nop_count"], 0)
        self.assertEqual(s7["guest_code_modification_bytes"], 0)
        self.assertEqual(s7["cp_mutation_bytes"], 0)
        self.assertEqual(s7["ptpip_allowed_count"], 5)
        self.assertEqual(s7["ptpip_blocked_count"], 4)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_phase58_qmp_introspection=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage7_phase58_qmp_introspection", rep_skip)

    def test_27_suite_cli_and_tracer_cli_summary_and_clean_room_json(self) -> None:
        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc = suite.main(
                [
                    "--clean-room",
                    "--skip-phase41",
                    "--skip-phase45",
                    "--skip-phase53",
                    "--skip-phase58",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage7_phase58_qmp_introspection", rep_skip)

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main(
                ["--clean-room", "--skip-phase41", "--skip-phase45", "--skip-phase53", "--summary"]
            )
        self.assertEqual(rc_sum, 0)
        self.assertIn("qmp=CLEAN_ROOM_SYNTHETIC(nop=0,ptpip=5ok/4blk)", buf_sum.getvalue())

        buf_p58 = io.StringIO()
        with contextlib.redirect_stdout(buf_p58):
            rc_p58 = p58.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc_p58, 0)
        self.assertIn("[PASS] Phase 58 QMP Guest Introspection & USB-LAN Tracer", buf_p58.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "qmp_guest_introspection_tracer.py"),
                "--clean-room",
                "--self-test",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], p58.PHASE_58_SCHEMA)
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["redlines"]["nop_count"], 0)
        self.assertEqual(payload["redlines"]["cp_mutation_bytes"], 0)

    def test_28_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        mod_src = (FX3_VM_DIR / "qmp_guest_introspection_tracer.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", mod_src)
        self.assertNotIn("os.O_WRONLY", mod_src)
        self.assertNotIn("os.O_RDWR", mod_src)
        self.assertNotIn(forbidden_port, mod_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertNotIn("pkill", mod_src)
        self.assertNotIn("killall", mod_src)
        self.assertIn("NOP_COUNT = 0", mod_src)
        self.assertIn("GUEST_CODE_MODIFICATION_BYTES = 0", mod_src)
        self.assertIn("CP_MUTATION_BYTES = 0", mod_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", mod_src)
        self.assertIn("CALIBRATION_MUTATION_BYTES = 0", mod_src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", mod_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", mod_src)


if __name__ == "__main__":
    unittest.main()
