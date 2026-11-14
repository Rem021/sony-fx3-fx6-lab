#!/usr/bin/env python3
"""Phase 41 Test Suite — CXD90057 Pure-Python FDT/DTB Synthesizer, `mhlx` Ring & `0xf0000000..0xf8ffffff` MMIO Emulator.

Exercises 28 unit, integration, fault-injection, CLI, and hygiene tests across
BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes,
strictly offline and without writing binary artifacts into the tracked repo.
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
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import cxd90057_dtb_and_mhlx_emulator as p41  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402


class TestDonorAuditAndCleanRoomFallback(unittest.TestCase):
    """Verify O_RDONLY FX3 v7.02 / FX6 v6.01 donor audit and clean-room fallback."""

    def test_01_clean_room_donor_audit_verifies_all_seven_subsystems(self) -> None:
        audit = p41.inspect_donor_kernel_mmio_contracts(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertTrue(audit.dtb_identity_verified)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertEqual(audit.fx3_dtb_sha256, p41.PINNED_CXD90057_DTB_SHA256)
        self.assertEqual(audit.fx6_dtb_sha256, p41.PINNED_CXD90057_DTB_SHA256)
        self.assertEqual(audit.fx3_cpapp_bytes, p41.PINNED_FX3_CPAPP_BYTES)
        subsystems = tuple(c.subsystem for c in audit.subsystem_contracts)
        self.assertEqual(
            subsystems,
            ("mhlx", "ipcu", "shm", "gpe", "spacc", "timer", "ttyAMA0..ttyAMA3"),
        )

    def test_02_force_clean_room_env_disables_local_donor_resolution(self) -> None:
        env = {p41.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p41.is_forced_clean_room(env))
        paths = p41.resolve_phase41_donor_paths(env=env)
        for path in paths.values():
            self.assertIn(p41.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p41.inspect_donor_kernel_mmio_contracts(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room_fallback(self) -> None:
        if p41.is_forced_clean_room():
            audit = p41.inspect_donor_kernel_mmio_contracts()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p41.resolve_phase41_donor_paths()
        if not all(p.is_file() for p in paths.values()):
            audit = p41.inspect_donor_kernel_mmio_contracts()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(audit.all_contracts_verified)
            return

        audit = p41.inspect_donor_kernel_mmio_contracts()
        self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
        self.assertTrue(audit.dtb_identity_verified)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(audit.donor_files_inspected, 16)
        self.assertEqual(audit.fx3_vmlinux_sha256, p41.PINNED_FX3_VMLINUX_SHA256)
        self.assertEqual(audit.fx3_cpapp_sha256, p41.PINNED_FX3_CPAPP_SHA256)

    def test_04_missing_donor_directory_falls_back_gracefully_to_clean_room(self) -> None:
        env = {
            p41.ENV_MAC_WORK_ROOT: "/nonexistent_fx3_work_root_phase41",
            p41.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_fx3_main_root_phase41",
        }
        audit = p41.inspect_donor_kernel_mmio_contracts(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)


class TestPurePythonFdtSynthesizerAndParser(unittest.TestCase):
    """Verify pure-Python FDT v17 compiler, `.dts` generator, and strict parser."""

    def test_05_compile_cxd90057_hybrid_fdt_header_and_determinism(self) -> None:
        c1 = p41.compile_cxd90057_hybrid_fdt()
        c2 = p41.compile_cxd90057_hybrid_fdt()
        self.assertEqual(c1.fdt_bytes, c2.fdt_bytes)
        self.assertEqual(c1.fdt_sha256, c2.fdt_sha256)
        self.assertEqual(c1.dts_source, c2.dts_source)
        self.assertTrue(c1.dts_source.startswith("/dts-v1/;"))

        hdr = c1.parsed.header
        self.assertEqual(hdr.magic, p41.FDT_MAGIC)
        self.assertEqual(hdr.version, 17)
        self.assertEqual(hdr.last_comp_version, 16)
        self.assertEqual(hdr.totalsize, len(c1.fdt_bytes))
        self.assertEqual(hdr.off_mem_rsvmap, 40)
        self.assertEqual(hdr.off_dt_struct % 4, 0)
        self.assertEqual(hdr.size_dt_struct % 4, 0)

    def test_06_hybrid_fdt_contains_all_required_cxd90057_and_virt_nodes(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        ver = p41.verify_hybrid_fdt_topology(compiled)
        self.assertTrue(ver["all_checks_passed"])
        self.assertEqual(ver["missing_nodes"], [])
        self.assertTrue(ver["reserved_memory_zero_overlap"])
        self.assertTrue(ver["cortex_a53_ok"])
        self.assertTrue(ver["mmio_bounds_ok"])

        nmap = compiled.parsed.node_map()
        mem_base, mem_sz = struct.unpack(">QQ", nmap["/memory@40000000"].prop_dict()["reg"])
        self.assertEqual(mem_base, 0x40000000)
        self.assertEqual(mem_sz, 0x80000000)

        bt_uart = nmap["/soc/serial@f0203000"].prop_dict()
        self.assertIn(b"virtual-rom-v1", bt_uart["compatible"])
        self.assertEqual(bt_uart["sony,uart-device"], b"/dev/ttyAMA3\x00")
        self.assertEqual(nmap["/soc/spacc@f7fc0000"].prop_dict()["sony,aes-xts-isolation"], b"cnflasha\x00")

    def test_07_tempfile_fdt_roundtrip_without_repo_binary_writes(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        with tempfile.TemporaryDirectory() as tmpdir:
            dtb_file = Path(tmpdir) / "cxd90057_hybrid_test.dtb"
            dtb_file.write_bytes(compiled.fdt_bytes)
            reloaded = p41.read_donor_bytes_readonly(dtb_file)
            parsed = p41.parse_fdt_blob(reloaded)
            self.assertEqual(parsed.header.magic, p41.FDT_MAGIC)
            self.assertEqual(len(parsed.nodes), compiled.node_count)
            self.assertEqual(parsed.total_property_count, compiled.property_count)

    def test_08_fdt_parser_rejects_corrupt_magic_and_short_buffer(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(b"\x00" * 16)

        bad_magic = bytearray(compiled.fdt_bytes)
        struct.pack_into(">I", bad_magic, 0, 0xDEADBEEF)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad_magic))

    def test_09_fdt_parser_rejects_truncated_totalsize_and_unaligned_struct(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        bad_total = bytearray(compiled.fdt_bytes)
        struct.pack_into(">I", bad_total, 4, len(compiled.fdt_bytes) + 64)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad_total))

        bad_align = bytearray(compiled.fdt_bytes)
        struct.pack_into(">I", bad_align, 8, compiled.parsed.header.off_dt_struct + 1)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad_align))

    def test_10_fdt_parser_rejects_missing_fdt_end_token(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        hdr = compiled.parsed.header
        bad = bytearray(compiled.fdt_bytes)
        end_off = hdr.off_dt_struct + hdr.size_dt_struct - 4
        self.assertEqual(struct.unpack_from(">I", bad, end_off)[0], p41.FDT_END)
        struct.pack_into(">I", bad, end_off, p41.FDT_NOP)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad))

    def test_11_fdt_parser_rejects_out_of_bounds_nameoff_and_unterminated_rsvmap(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        hdr = compiled.parsed.header
        # Corrupt first FDT_PROP nameoff (root node has properties right after FDT_BEGIN_NODE + 4B)
        first_prop_off = hdr.off_dt_struct + 8
        self.assertEqual(struct.unpack_from(">I", compiled.fdt_bytes, first_prop_off)[0], p41.FDT_PROP)
        bad_nameoff = bytearray(compiled.fdt_bytes)
        struct.pack_into(">I", bad_nameoff, first_prop_off + 8, hdr.size_dt_strings + 100)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad_nameoff))

        # Corrupt mem_rsvmap sentinel
        bad_rsv = bytearray(compiled.fdt_bytes)
        sentinel_off = hdr.off_mem_rsvmap + len(compiled.parsed.mem_rsvmap) * 16
        struct.pack_into(">QQ", bad_rsv, sentinel_off, 0x1000, 0x1000)
        with self.assertRaises(p41.FdtFormatError):
            p41.parse_fdt_blob(bytes(bad_rsv))

    def test_12_fdt_parser_accepts_fdt_nop_and_rejects_duplicate_nodes(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt()
        hdr = compiled.parsed.header
        # Insert FDT_NOP inside dt_struct before FDT_END
        end_off = hdr.off_dt_struct + hdr.size_dt_struct - 4
        with_nop = bytearray(
            compiled.fdt_bytes[:end_off]
            + struct.pack(">I", p41.FDT_NOP)
            + compiled.fdt_bytes[end_off:]
        )
        # Update totalsize, off_dt_strings, size_dt_struct
        struct.pack_into(">I", with_nop, 4, hdr.totalsize + 4)
        struct.pack_into(">I", with_nop, 12, hdr.off_dt_strings + 4)
        struct.pack_into(">I", with_nop, 36, hdr.size_dt_struct + 4)
        parsed = p41.parse_fdt_blob(bytes(with_nop))
        self.assertEqual(len(parsed.nodes), compiled.node_count)

        # Duplicate child rejected by packer
        dup_root = p41.FdtNodeSpec(
            unit_name="",
            children=(p41.FdtNodeSpec("dup"), p41.FdtNodeSpec("dup")),
        )
        with self.assertRaises(p41.FdtFormatError):
            p41.pack_fdt_blob((), dup_root)

    def test_13_fdt_bt_mode_annotation_propagates_to_serial3(self) -> None:
        compiled = p41.compile_cxd90057_hybrid_fdt(bt_mode="PATCHRAM_CORRUPT_NACK")
        bt_props = compiled.parsed.node_map()["/soc/serial@f0203000"].prop_dict()
        self.assertEqual(bt_props["sony,bt-mode"], b"PATCHRAM_CORRUPT_NACK\x00")


class TestMmioWindowAndMhlxMailboxEmulator(unittest.TestCase):
    """Verify `0xf0000000..0xf8ffffff` MMIO bus, MHLX ring, SPAcc guard, and `shm_Loader`."""

    def test_14_mmio_window_bounds_and_64bit_access(self) -> None:
        bus = p41.MmioWindowBus()
        self.assertEqual(bus.read32(p41.MHLX_BASE + p41.MHLX_REG_ID), p41.MHLX_MAGIC)
        id_ver = bus.read64(p41.MHLX_BASE + p41.MHLX_REG_ID)
        self.assertEqual(id_ver & 0xFFFF_FFFF, p41.MHLX_MAGIC)
        self.assertEqual((id_ver >> 32) & 0xFFFF_FFFF, p41.MHLX_VERSION)

        with self.assertRaises(p41.MmioAccessError):
            bus.read32(p41.MMIO_WINDOW_START - 4)
        with self.assertRaises(p41.MmioAccessError):
            bus.read32(p41.MMIO_WINDOW_END)
        with self.assertRaises(p41.MmioAccessError):
            bus.write64(p41.MMIO_WINDOW_END - 4, 0)

    def test_15_timer_ip_wdt_kick_prevents_reset_and_expiry_increments(self) -> None:
        bus = p41.MmioWindowBus()
        bus.write32(p41.TIMER_IP_BASE + p41.TIMER_REG_WDT_TIMEOUT, 1000)
        bus.advance_timer_ticks(800)
        bus.write32(p41.TIMER_IP_BASE + p41.TIMER_REG_WDT_KICK, p41.WDT_KICK_MAGIC)
        bus.advance_timer_ticks(800)
        self.assertEqual(bus.read32(p41.TIMER_IP_BASE + p41.TIMER_REG_WDT_RESET_COUNT), 0)
        self.assertEqual(bus.wdt_kick_count, 1)

        # Un-kicked expiry triggers deterministic WDT reset counter
        bus.advance_timer_ticks(500)
        self.assertEqual(bus.read32(p41.TIMER_IP_BASE + p41.TIMER_REG_WDT_RESET_COUNT), 1)

    def test_16_ttyama0_to_ttyama3_uart_tx_streams(self) -> None:
        bus = p41.MmioWindowBus()
        for idx, ch in enumerate(b"FX3"):
            bus.write32(p41.UART0_BASE + p41.UART_REG_DR, ch)
        for ch in b"\x01\x03\x0c\x00":
            bus.write32(p41.UART3_BT_BASE + p41.UART_REG_DR, ch)
        self.assertEqual(bytes(bus.uart_tx_streams[0]), b"FX3")
        self.assertEqual(bytes(bus.uart_tx_streams[3]).hex(), "01030c00")

    def test_17_spacc_f7fc0000_blocks_userland_and_allows_kernel(self) -> None:
        bus = p41.MmioWindowBus()
        self.assertEqual(bus.read32(p41.SPACC_BASE + p41.SPACC_REG_VERSION, ring="kernel"), p41.SPACC_VERSION_MAGIC)
        self.assertEqual(bus.read32(p41.SPACC_BASE + p41.SPACC_REG_KEY_LOCK, ring="kernel"), 1)
        with self.assertRaises(p41.MmioAccessError):
            bus.read32(p41.SPACC_BASE + p41.SPACC_REG_XTS_MODE, ring="userland")
        with self.assertRaises(p41.MmioAccessError):
            bus.write32(p41.SPACC_BASE + p41.SPACC_REG_XTS_MODE, 0, ring="userland")
        self.assertEqual(bus.spacc_blocked_userland_ops, 2)
        self.assertEqual(bus.spacc_kernel_ops, 2)

    def test_18_mhlx_irq_mask_and_w1c_ack_clear_registers(self) -> None:
        bus = p41.MmioWindowBus()
        # Mask off channel 2 -> global IRQ_STATUS hides bit 2 until unmasked
        bus.write32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_MASK, 0xFF & ~(1 << 2))
        bus.write32(p41.MHLX_BASE + p41.MHLX_REG_DOORBELL_SEND, (1 << 16) | 2)
        self.assertEqual(bus.read32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_STATUS), 0)

        bus.write32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_MASK, 0xFF)
        self.assertEqual(bus.read32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_STATUS), 1 << 2)

        # W1C clear via MHLX_REG_IRQ_CLEAR
        bus.write32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_CLEAR, 1 << 2)
        self.assertEqual(bus.read32(p41.MHLX_BASE + p41.MHLX_REG_IRQ_STATUS), 0)

    def test_19_mhlx_ring_push_pop_and_backpressure_recovery(self) -> None:
        bus = p41.MmioWindowBus()
        ch = p41.MHLX_CH_IPCU_SYS
        usable_slots = p41.MHLX_RING_CAPACITY - 1  # circular ring reserves 1 sentinel slot
        for i in range(usable_slots):
            bus.push_ring(ch, "tx", 0x0500 + i, struct.pack("<I", i))

        with self.assertRaises(p41.MhlxMailboxError):
            bus.push_ring(ch, "tx", 0x05FF, b"overflow")
        self.assertEqual(bus.mhlx_backpressure_count, 1)

        # Drain 1 and verify recovery push succeeds
        first = bus.pop_ring(ch, "tx")
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.opcode, 0x0500)
        seq_after = bus.push_ring(ch, "tx", 0x05FF, b"ok")
        self.assertGreater(seq_after, usable_slots)

    def test_20_mhlx_rejects_oversized_payload_and_disabled_channel(self) -> None:
        bus = p41.MmioWindowBus()
        with self.assertRaises(p41.MhlxMailboxError):
            bus.push_ring(0, "tx", 0x0416, b"x" * (p41.MHLX_MAX_PAYLOAD_BYTES + 1))

        ch_en_addr = p41.MHLX_BASE + p41.MHLX_CH_BASE + 4 * p41.MHLX_CH_STRIDE + p41.MHLX_CH_OFF_ENABLE
        bus.write32(ch_en_addr, 0)
        with self.assertRaises(p41.MhlxMailboxError):
            bus.push_ring(4, "tx", 0x0100, b"disabled")

    def test_21_shm_loader_cold_and_warm_handshakes_preserve_zero_cp_mutation(self) -> None:
        bus = p41.MmioWindowBus()
        cold = bus.run_shm_loader_handshake(mode="cold_boot")
        self.assertTrue(cold.passed)
        self.assertEqual(cold.request_opcode, "0x4101")
        self.assertEqual(cold.ack_opcode, "0xc101")
        self.assertEqual(cold.cp_mutation_bytes, 0)
        self.assertEqual(cold.wbi_mutation_bytes, 0)
        self.assertEqual(cold.cp_sha256_before, cold.cp_sha256_after)
        self.assertTrue(cold.ap_tx_doorbell_fired)
        self.assertTrue(cold.cp_irq_acked_w1c)
        self.assertTrue(cold.cp_rx_doorbell_fired)
        self.assertTrue(cold.ap_irq_acked_w1c)
        self.assertEqual(cold.shm_loader_status, p41.SHM_LOADER_STATE_COLD_READY)

        warm = bus.run_shm_loader_handshake(mode="warm_boot")
        self.assertTrue(warm.passed)
        self.assertEqual(warm.request_opcode, "0x4102")
        self.assertEqual(warm.ack_opcode, "0xc102")
        self.assertEqual(warm.cp_mutation_bytes, 0)
        self.assertEqual(warm.wbi_mutation_bytes, 0)
        self.assertEqual(warm.shm_loader_status, p41.SHM_LOADER_STATE_WARM_RESUMED)

    def test_22_shm_loader_rejects_unknown_boot_mode(self) -> None:
        bus = p41.MmioWindowBus()
        with self.assertRaises(p41.MhlxMailboxError):
            bus.run_shm_loader_handshake(mode="factory_wipe")


class TestCoEmulationIntegrationCliAndHygiene(unittest.TestCase):
    """Verify suite wiring, CLI modes, deterministic digests, and clean-room hygiene."""

    def test_23_phase41_audit_deterministic_digest_in_clean_room(self) -> None:
        r1 = p41.run_phase41_emulator_audit(force_clean_room=True)
        r2 = p41.run_phase41_emulator_audit(force_clean_room=True)
        self.assertEqual(r1, r2)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(r1["redlines"]["wbi_mutation_bytes"], 0)

        copy_rep = dict(r1)
        recorded = copy_rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_24_coemulation_suite_wires_stage4_phase41_and_allows_skip(self) -> None:
        rep_with = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_bt_containment_matrix=False)
        )
        self.assertTrue(rep_with["all_checks_passed"])
        self.assertIn("stage4_phase41_dtb_mhlx", rep_with)
        s4 = rep_with["stage4_phase41_dtb_mhlx"]
        self.assertTrue(s4["all_checks_passed"])
        self.assertEqual(s4["cp_mutation_bytes"], 0)
        self.assertEqual(s4["wbi_mutation_bytes"], 0)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage4_phase41_dtb_mhlx", rep_skip)

    def test_25_cli_subprocess_self_test_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "cxd90057_dtb_and_mhlx_emulator.py"),
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
        self.assertEqual(payload["schema"], p41.PHASE_41_SCHEMA)
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["redlines"]["cp_mutation_bytes"], 0)

    def test_26_cli_dts_fdt_info_and_summary_flags(self) -> None:
        buf_dts = io.StringIO()
        with contextlib.redirect_stdout(buf_dts):
            rc_dts = p41.main(["--dts"])
        self.assertEqual(rc_dts, 0)
        dts_txt = buf_dts.getvalue()
        self.assertIn("/dts-v1/;", dts_txt)
        self.assertIn("mhlx@f0800000", dts_txt)
        self.assertIn("spacc@f7fc0000", dts_txt)
        self.assertIn("gpe0_fb@41e001000", dts_txt)

        buf_info = io.StringIO()
        with contextlib.redirect_stdout(buf_info):
            rc_info = p41.main(["--fdt-info"])
        self.assertEqual(rc_info, 0)
        info = json.loads(buf_info.getvalue())
        self.assertTrue(info["all_checks_passed"])
        self.assertEqual(info["fdt_magic"], "0xd00dfeed")

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p41.main(["--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 41 CXD90057 DTB+MHLX+MMIO", buf_sum.getvalue())

    def test_27_suite_cli_skip_phase41_flag_and_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--skip-phase41", "--json"])
        self.assertEqual(rc, 0)
        rep = json.loads(buf.getvalue())
        self.assertTrue(rep["all_checks_passed"])
        self.assertNotIn("stage4_phase41_dtb_mhlx", rep)

    def test_28_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        mod_src = (FX3_VM_DIR / "cxd90057_dtb_and_mhlx_emulator.py").read_text(encoding="utf-8")
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
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", mod_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", mod_src)


if __name__ == "__main__":
    unittest.main()
