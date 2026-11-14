#!/usr/bin/env python3
"""Phase 24 Test Suite — Dual-ISA (`CXD90057` AArch64 <-> `CXD90058` ARM32 Thumb-2) IVSHMEM Bridge.

Exercises >= 20 unit & Dual-ISA Unicorn co-execution tests across BOTH Local Donor (`O_RDONLY`)
and `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic modes, strictly offline & clean-room compliant.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import os
import struct
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import unicorn as U  # noqa: E402
from unicorn import arm_const as A32  # noqa: E402

import dual_ap_cp_ivshmem_bridge as bridge  # noqa: E402


class TestIvshmemHardwareRegisters(unittest.TestCase):
    """Verify QEMU `ivshmem-doorbell` / `ivshmem-flat` MMIO register hardware semantics."""

    def test_01_ivposition_readonly_and_peer_identities(self) -> None:
        bus = bridge.IvshmemBus()
        p0 = bus.peers[bridge.PEER_ID_AP_MIRA]
        p1 = bus.peers[bridge.PEER_ID_CP_CETUS]
        self.assertEqual(p0.read32(bridge.IVSHMEM_REG_IVPOSITION), 0)
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_IVPOSITION), 1)
        # Writes to IVPOSITION must be ignored by hardware
        p0.write32(bridge.IVSHMEM_REG_IVPOSITION, 0xDEADBEEF, bus)
        p1.write32(bridge.IVSHMEM_REG_IVPOSITION, 0xCAFEBABE, bus)
        self.assertEqual(p0.read32(bridge.IVSHMEM_REG_IVPOSITION), 0)
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_IVPOSITION), 1)

    def test_02_doorbell_encoding_and_intrstatus_clear_on_read(self) -> None:
        bus = bridge.IvshmemBus()
        p0 = bus.peers[bridge.PEER_ID_AP_MIRA]
        p1 = bus.peers[bridge.PEER_ID_CP_CETUS]

        # AP rings Doorbell targeting Peer 1, vector 3
        p0.write32(bridge.IVSHMEM_REG_DOORBELL, (1 << 16) | 3, bus)
        self.assertEqual(p1.irq_received_count, 1)
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_INTRSTATUS), 1 << 3)
        # Second read returns 0 (clear-on-read)
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_INTRSTATUS), 0)

        # CP rings Doorbell targeting Peer 0, vector 0
        p1.write32(bridge.IVSHMEM_REG_DOORBELL, (0 << 16) | 0, bus)
        self.assertEqual(p0.irq_received_count, 1)
        self.assertEqual(p0.read32(bridge.IVSHMEM_REG_INTRSTATUS), 1)
        self.assertEqual(p0.read32(bridge.IVSHMEM_REG_INTRSTATUS), 0)

    def test_03_intrmask_blocks_irq_delivery_until_unmasked(self) -> None:
        bus = bridge.IvshmemBus()
        p0 = bus.peers[bridge.PEER_ID_AP_MIRA]
        p1 = bus.peers[bridge.PEER_ID_CP_CETUS]

        p1.write32(bridge.IVSHMEM_REG_INTRMASK, 0x00000000, bus)
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_INTRMASK), 0)
        p0.write32(bridge.IVSHMEM_REG_DOORBELL, (1 << 16) | 0, bus)
        self.assertEqual(bus.masked_doorbell_count, 1)
        self.assertEqual(p1.irq_received_count, 0)
        self.assertNotIn(bridge.PEER_ID_CP_CETUS, bus.pending_irq_peers)
        # Status bit is latched pending even while masked
        self.assertEqual(p1.read32(bridge.IVSHMEM_REG_INTRSTATUS), 1)

        # Unmask vector 0 and ring again
        p1.write32(bridge.IVSHMEM_REG_INTRMASK, 0x00000001, bus)
        p0.write32(bridge.IVSHMEM_REG_DOORBELL, (1 << 16) | 0, bus)
        self.assertEqual(p1.irq_received_count, 1)
        self.assertIn(bridge.PEER_ID_CP_CETUS, bus.pending_irq_peers)

    def test_04_doorbell_invalid_target_peer_is_tracked_safely(self) -> None:
        bus = bridge.IvshmemBus()
        p0 = bus.peers[bridge.PEER_ID_AP_MIRA]
        p0.write32(bridge.IVSHMEM_REG_DOORBELL, (7 << 16) | 1, bus)
        self.assertEqual(bus.invalid_doorbell_count, 1)
        self.assertEqual(bus.doorbell_trace[-1].delivered_irq, False)
        self.assertEqual(bus.doorbell_trace[-1].reason, "unknown_target_peer_7")


class TestDualIsaUnicornCoEmulation(unittest.TestCase):
    """Verify Dual-ISA (`AArch64` <-> `Doorbell` <-> `Thumb-2`) Unicorn co-execution."""

    def setUp(self) -> None:
        self.session = bridge.create_dual_ap_cp_session()

    def test_05_zero_copy_shm_coherence_between_aarch64_and_thumb2(self) -> None:
        magic_word = self.session.cp_uc.mem_read(bridge.IVSHMEM_CP_SHM_BASE, 8)
        ap_word = self.session.ap_uc.mem_read(bridge.IVSHMEM_AP_SHM_BASE, 8)
        self.assertEqual(bytes(magic_word), bytes(ap_word))
        magic, ver = struct.unpack("<II", bytes(magic_word))
        self.assertEqual(magic, bridge.SHM_MAGIC)
        self.assertEqual(ver, bridge.SHM_VERSION)

        # Write from AArch64 and immediately observe on ARM32 Thumb-2
        probe_off = 0x0800
        self.session.ap_uc.mem_write(bridge.IVSHMEM_AP_SHM_BASE + probe_off, b"FX3_DUAL_ISA")
        seen_cp = bytes(self.session.cp_uc.mem_read(bridge.IVSHMEM_CP_SHM_BASE + probe_off, 12))
        self.assertEqual(seen_cp, b"FX3_DUAL_ISA")

    def test_06_cp_load_base_0x00108000_mmu_read_only_and_sha256_immutable(self) -> None:
        immut_before = self.session.verify_cp_immutability()
        self.assertTrue(immut_before.immutable)
        self.assertEqual(immut_before.cp_mutation_bytes, 0)

        # Unicorn MMU must physically reject any write to mapped cpapp-b.bin @ 0x00108000
        with self.assertRaises(U.UcError) as ctx:
            # Attempt write via ARM32 code or check protection; mem_write bypasses guest MMU,
            # so test guest STR instruction attempting to mutate 0x00108000!
            bad_code = (
                bridge._encode_thumb2_movw(0, 0x8000)
                + bridge._encode_thumb2_movt(0, 0x0010)
                + struct.pack("<H", 0x6000)  # str r0, [r0]
            )
            self.session.cp_uc.mem_write(bridge.CP_ISR_BASE + 0x4000, bad_code)
            self.session.cp_uc.emu_start(
                (bridge.CP_ISR_BASE + 0x4000) | 1,
                bridge.CP_ISR_BASE + 0x4000 + len(bad_code),
            )
        self.assertEqual(ctx.exception.errno, U.UC_ERR_WRITE_PROT)
        self.assertEqual(self.session.verify_cp_immutability().cp_mutation_bytes, 0)

    def test_07_cp_thumb2_verifies_0x92840747_and_completion_constants_in_mapped_memory(self) -> None:
        pkt = bridge.build_0x92840747_packet(bridge.OPCODE_VIDEO_MODE_PROCAM)
        rcpt = self.session.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, pkt)
        self.assertTrue(rcpt.cp_executed)
        tel = self.session.telemetry_snapshot()
        self.assertEqual(tel["cp_verified_0x92840747"], 1)
        self.assertEqual(tel["cp_verified_load_base"], 1)
        self.assertIn(
            tel["cp_verified_completion_imm"],
            (
                bridge.OPCODE_LUT_DMA | bridge.UIPC_BB_HW_COMPLETION_MASK,
                bridge.OPCODE_LUT_DMA | bridge.UIPC_BB_COMPLETION_BIT,
            ),
        )

    def test_08_roundtrip_developing_fhd_0x0416_and_cine_ei_dual_base_iso(self) -> None:
        r_416 = self.session.send_uipc_from_ap(
            bridge.UIPC_BB_TARGET_QUEUE,
            bridge.build_0x92840747_packet(bridge.OPCODE_VIDEO_MODE_PROCAM),
        )
        r_169 = self.session.send_uipc_from_ap(
            bridge.UIPC_BB_TARGET_QUEUE,
            bridge.build_0x92840747_packet(bridge.OPCODE_DEVELOP_A, struct.pack("<BBH", 1, 0, 800)),
        )
        r_16a = self.session.send_uipc_from_ap(
            bridge.UIPC_BB_TARGET_QUEUE,
            bridge.build_0x92840747_packet(bridge.OPCODE_DEVELOP_B, struct.pack("<HH", 12800, 1)),
        )
        for op, rcpt in ((0x0416, r_416), (0x0169, r_169), (0x016A, r_16a)):
            self.assertFalse(rcpt.intercepted_by_p11)
            self.assertTrue(rcpt.tx_enqueued)
            self.assertTrue(rcpt.ap_doorbell_to_cp)
            self.assertTrue(rcpt.cp_executed)
            self.assertTrue(rcpt.cp_doorbell_to_ap)
            self.assertEqual(rcpt.rx_completion_bytes, 12)
            self.assertEqual(rcpt.rx_completion_opcode, f"0x{op | 0x8000:04x}")
            self.assertEqual(rcpt.rx_hw_1000_alias_opcode, f"0x{op | 0x1000:04x}")
            self.assertEqual(rcpt.cp_mutation_bytes, 0)

    def test_09_roundtrip_33cube_3d_lut_dma_8bit_and_16bit_and_toggle(self) -> None:
        for lut_sz in (bridge.LUT_8BIT_RAW_BYTES, bridge.LUT_8BIT_ALIGNED_BYTES, bridge.LUT_16BIT_BYTES):
            lut_buf = (b"\x11\x22\x33\x44" * ((lut_sz // 4) + 1))[:lut_sz]
            pkt_dma = bridge.build_0x0165_lut_dma_packet(lut_bytes=lut_sz)
            r_dma = self.session.send_uipc_from_ap(
                bridge.UIPC_BB_TARGET_QUEUE,
                pkt_dma,
                stage_lut_bytes=lut_buf,
            )
            self.assertTrue(r_dma.cp_executed)
            self.assertEqual(r_dma.rx_completion_opcode, "0x8165")
            self.assertEqual(r_dma.rx_hw_1000_alias_opcode, "0x1165")
            self.assertEqual(r_dma.lut_dma_acked_bytes, lut_sz)

            r_on = self.session.send_uipc_from_ap(
                bridge.UIPC_BB_TARGET_QUEUE,
                bridge.build_0x0166_lut_toggle_packet(enable=True),
            )
            self.assertEqual(r_on.rx_completion_opcode, "0x8166")

            r_off = self.session.send_uipc_from_ap(
                bridge.UIPC_BB_TARGET_QUEUE,
                bridge.build_0x0166_lut_toggle_packet(enable=False),
            )
            self.assertEqual(r_off.rx_completion_opcode, "0x8166")

        self.assertEqual(self.session.telemetry_snapshot()["lut_dma_ack_count"], 3)

    def test_10_roundtrip_ibis_steadyshot_off_standard_active_center_lock(self) -> None:
        for mode_name, mode_val in bridge.VALID_STEADYSHOT_MODES.items():
            pkt = bridge.build_0x92840747_packet(
                bridge.OPCODE_TC_MODE,
                struct.pack("<BBH", mode_val, 1, 0),
            )
            rcpt = self.session.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, pkt)
            self.assertTrue(rcpt.cp_executed, msg=f"IBIS mode {mode_name} failed CP execution")
            self.assertEqual(rcpt.rx_completion_opcode, "0x8400")
            # FX3 Stock-CP keeps Hall/Gyro voice-coil center-lock energized even when SteadyShot is Off
            self.assertTrue(rcpt.ibis_center_lock_energized)
            self.assertEqual(self.session.telemetry_snapshot()["ibis_steadyshot_mode"], mode_val)

    def test_11_p11_rtc_0x92d2091c_isolated_on_ap_never_leaks_to_cp(self) -> None:
        cp_irqs_before = self.session.telemetry_snapshot()["cp_doorbell_irq_count"]
        tx_head_before = self.session.telemetry_snapshot()["tx_head"]

        # Valid /dev/rtc0 -> [0x03, 0x00]
        self.session.set_ap_rtc_valid(True)
        r_ok = self.session.send_uipc_from_ap(bridge.RTC_QUEUE_ID, bytes((0x03, 0x00)))
        self.assertTrue(r_ok.intercepted_by_p11)
        self.assertFalse(r_ok.tx_enqueued)
        self.assertFalse(r_ok.ap_doorbell_to_cp)
        self.assertFalse(r_ok.cp_executed)
        self.assertEqual(r_ok.rx_completion_hex, "0300")

        # Unset /dev/rtc0 -> [0x03, 0x01]
        self.session.set_ap_rtc_valid(False)
        r_unset = self.session.send_uipc_from_ap(bridge.RTC_QUEUE_ID, bytes((0x03, 0x00)))
        self.assertTrue(r_unset.intercepted_by_p11)
        self.assertFalse(r_unset.cp_executed)
        self.assertEqual(r_unset.rx_completion_hex, "0301")

        tel = self.session.telemetry_snapshot()
        self.assertEqual(tel["p11_local_rtc_count"], 2)
        self.assertEqual(tel["cp_doorbell_irq_count"], cp_irqs_before)
        self.assertEqual(tel["tx_head"], tx_head_before)

    def test_12_p11_smart_handle_0x91db059b_isolated_on_ap_never_leaks_to_cp(self) -> None:
        cp_irqs_before = self.session.telemetry_snapshot()["cp_doorbell_irq_count"]
        cb_qid = 0x81CC0501

        r_reg = self.session.send_uipc_from_ap(
            bridge.HANDLE_QUEUE_ID,
            struct.pack("<III", bridge.HANDLE_REG_CMD, 0, cb_qid),
        )
        r_unreg = self.session.send_uipc_from_ap(
            bridge.HANDLE_QUEUE_ID,
            struct.pack("<III", bridge.HANDLE_UNREG_CMD, 0, cb_qid),
        )
        self.assertTrue(r_reg.intercepted_by_p11)
        self.assertTrue(r_unreg.intercepted_by_p11)
        self.assertFalse(r_reg.cp_executed)
        self.assertFalse(r_unreg.cp_executed)
        self.assertEqual(
            r_reg.rx_completion_hex,
            struct.pack("<III", bridge.HANDLE_REG_CMD | bridge.HANDLE_ACK_MASK, 0, cb_qid).hex(),
        )
        self.assertEqual(
            r_unreg.rx_completion_hex,
            struct.pack("<III", bridge.HANDLE_UNREG_CMD | bridge.HANDLE_ACK_MASK, 0, cb_qid).hex(),
        )
        tel = self.session.telemetry_snapshot()
        self.assertEqual(tel["p11_local_handle_count"], 2)
        self.assertEqual(tel["cp_doorbell_irq_count"], cp_irqs_before)

    def test_13_ring_full_backpressure_and_recovery_drain(self) -> None:
        pkt = bridge.build_0x92840747_packet(bridge.OPCODE_COLOR_BARS)
        for i in range(bridge.SHM_RING_CAPACITY):
            r = self.session.enqueue_tx_without_cp_drain(pkt)
            self.assertTrue(r.tx_enqueued, msg=f"Slot {i} should enqueue cleanly")
            self.assertFalse(r.backpressure_rejected)

        # 17th push must be rejected by Peer 0 AArch64 backpressure check
        r_full = self.session.enqueue_tx_without_cp_drain(pkt)
        self.assertFalse(r_full.tx_enqueued)
        self.assertTrue(r_full.backpressure_rejected)
        self.assertEqual(self.session.telemetry_snapshot()["backpressure_count"], 1)

        # Now drain all 16 frames on Peer 1 Thumb-2 and verify RX completion & ring recovery
        processed = self.session.run_cp_isr()
        self.assertEqual(processed, bridge.SHM_RING_CAPACITY)
        tel = self.session.telemetry_snapshot()
        self.assertEqual(tel["tx_head"], bridge.SHM_RING_CAPACITY)
        self.assertEqual(tel["tx_tail"], bridge.SHM_RING_CAPACITY)
        self.assertEqual(tel["rx_head"], bridge.SHM_RING_CAPACITY)

        # Consume all 16 RX frames on Peer 0 AArch64 and verify a new enqueue succeeds
        for _ in range(bridge.SHM_RING_CAPACITY):
            poll_rc, _ = self.session._run_ap_poll_rx()
            self.assertEqual(poll_rc, 0)
        r_after = self.session.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, pkt)
        self.assertTrue(r_after.tx_enqueued)
        self.assertTrue(r_after.cp_executed)
        self.assertEqual(r_after.rx_completion_opcode, "0x8112")

    def test_14_malformed_frame_fault_injection_rejected_by_thumb2_cp(self) -> None:
        bad_magic = struct.pack("<HHHH", 0xDEAD, bridge.OPCODE_DEVELOP_A, 8, bridge.UIPC_BB_FLAGS)
        bad_len = struct.pack("<HHHH", bridge.UIPC_BB_MAGIC, bridge.OPCODE_DEVELOP_A, 99, bridge.UIPC_BB_FLAGS)
        bad_flags = struct.pack("<HHHH", bridge.UIPC_BB_MAGIC, bridge.OPCODE_DEVELOP_A, 8, 0x1234)
        bad_0165_len = bridge.build_0x92840747_packet(bridge.OPCODE_LUT_DMA, b"\x00" * 4)
        bad_0166_len = bridge.build_0x92840747_packet(bridge.OPCODE_LUT_TOGGLE, b"\x00" * 6)

        for idx, bad_pkt in enumerate((bad_magic, bad_len, bad_flags, bad_0165_len, bad_0166_len), start=1):
            rcpt = self.session.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, bad_pkt)
            self.assertTrue(rcpt.tx_enqueued)
            self.assertTrue(rcpt.cp_executed)
            self.assertTrue(rcpt.malformed_dropped, msg=f"Bad frame #{idx} was not dropped")
            self.assertEqual(rcpt.rx_completion_bytes, 0)

        tel = self.session.telemetry_snapshot()
        self.assertEqual(tel["malform_drop_count"], 5)
        self.assertEqual(tel["last_error_code"], 0xE001)
        self.assertEqual(tel["rx_head"], 0)
        self.assertEqual(self.session.verify_cp_immutability().cp_mutation_bytes, 0)

    def test_15_unsupported_queue_rejected_on_ap_without_touching_ring(self) -> None:
        rcpt = self.session.send_uipc_from_ap(0x905A0048, b"\x01\x02\x03\x04")
        self.assertFalse(rcpt.intercepted_by_p11)
        self.assertFalse(rcpt.tx_enqueued)
        self.assertFalse(rcpt.cp_executed)
        self.assertEqual(self.session.telemetry_snapshot()["tx_head"], 0)


class TestDualModeAndQemuTopology(unittest.TestCase):
    """Verify Dual-Mode Clean-Room vs Local Donor parity, O_RDONLY hygiene, and QEMU CLI spec."""

    def test_16_clean_room_synthetic_mode_passes_full_audit(self) -> None:
        rep = bridge.run_phase24_co_emulation_audit(force_clean_room=True)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["cp_mutation_bytes"], 0)
        self.assertTrue(rep["cp_inspection"]["tomco_present"])
        self.assertTrue(rep["cp_inspection"]["has_0x92840747"])
        self.assertEqual(len(rep["cp_inspection"]["completion_0x8000_opcodes"]), len(bridge.SUPPORTED_0X92840747_OPCODES))
        self.assertFalse(rep["cp_inspection"]["p11_rtc_present_in_cp"])
        self.assertFalse(rep["cp_inspection"]["p11_handle_present_in_cp"])

    def test_17_clean_room_env_flag_disables_local_donor_resolution(self) -> None:
        paths = bridge.resolve_phase24_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        for k, p in paths.items():
            self.assertIn(bridge.CLEAN_ROOM_SENTINEL_DIRNAME, str(p), msg=f"Clean-room bypass for {k}")
            self.assertFalse(p.exists())

    def test_18_local_donor_mode_when_present_or_skip_gracefully(self) -> None:
        if bridge.is_forced_clean_room():
            # Under FX3_FX6_FORCE_CLEAN_ROOM=1, verify clean-room audit directly without failing
            rep = bridge.run_phase24_co_emulation_audit(env=os.environ)
            self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep["all_checks_passed"])
            return

        donor_paths = bridge.resolve_phase24_donor_paths()
        if not all(p.is_file() for p in donor_paths.values()):
            self.skipTest("Optional local Sony BYOF donor binaries absent on this host")

        rep = bridge.run_phase24_co_emulation_audit(force_clean_room=False)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "LOCAL_DONOR_READONLY")
        self.assertEqual(rep["cp_mutation_bytes"], 0)
        self.assertEqual(rep["cp_inspection"]["byte_length"], bridge.EXPECTED_FX3_CPAPP_BYTES)
        self.assertEqual(rep["cp_inspection"]["sha256"], bridge.EXPECTED_FX3_CPAPP_SHA256)
        self.assertGreaterEqual(rep["cp_inspection"]["queue_0x92840747_hit_count"], 250)
        self.assertFalse(rep["cp_inspection"]["p11_rtc_present_in_cp"])
        self.assertFalse(rep["cp_inspection"]["p11_handle_present_in_cp"])
        self.assertTrue(rep["ap_inspection"]["appfw_has_0x92840747"])
        self.assertTrue(rep["ap_inspection"]["appfw_has_p11_rtc"])
        self.assertTrue(rep["ap_inspection"]["appfw_has_p11_handle"])
        self.assertTrue(rep["ap_inspection"]["uipc_has_dev_uipc"])

    def test_19_qemu_topology_spec_generation_and_validation(self) -> None:
        topo = bridge.build_dual_qemu_ivshmem_topology_spec(
            socket_path="/tmp/fx3-p24.sock",
            shm_size_mib=4,
            vectors=2,
        )
        self.assertEqual(topo.schema, bridge.PHASE_24_SCHEMA)
        self.assertIn("ivshmem-server", topo.ivshmem_server_cmd[0])
        self.assertIn("ivshmem-doorbell,chardev=fx3_ivshmem_chr,vectors=2", topo.peer0_ap_mira["argv"])
        self.assertEqual(topo.peer0_ap_mira["peer_id"], 0)
        self.assertEqual(topo.peer1_cp_cetus["peer_id"], 1)
        self.assertEqual(topo.peer1_cp_cetus["cp_load_base"], "0x00108000")
        self.assertTrue(topo.peer1_cp_cetus["cp_read_only"])
        self.assertEqual(topo.peer1_cp_cetus["cp_mutation_bytes"], 0)
        self.assertTrue(any("ivshmem-flat" in str(a) for a in topo.peer1_cp_cetus["argv"]))
        self.assertIn("cortex-r5", topo.peer1_cp_cetus["argv"])
        self.assertIn("addr=0x00108000", " ".join(topo.peer1_cp_cetus["argv"]))

        with self.assertRaises(bridge.IvshmemBridgeError):
            bridge.build_dual_qemu_ivshmem_topology_spec(shm_size_mib=3)
        with self.assertRaises(bridge.IvshmemBridgeError):
            bridge.build_dual_qemu_ivshmem_topology_spec(socket_path="/tmp/" + "x" * 110)

    def test_20_all_supported_0x92840747_opcodes_complete_with_0x8000_bit(self) -> None:
        sess = bridge.create_dual_ap_cp_session(force_clean_room=True)
        for op in bridge.SUPPORTED_0X92840747_OPCODES:
            if op == bridge.OPCODE_LUT_DMA:
                pkt = bridge.build_0x0165_lut_dma_packet(lut_bytes=bridge.LUT_8BIT_ALIGNED_BYTES)
                lut = b"\xAA" * bridge.LUT_8BIT_ALIGNED_BYTES
            elif op == bridge.OPCODE_LUT_TOGGLE:
                pkt = bridge.build_0x0166_lut_toggle_packet(enable=True)
                lut = None
            else:
                pkt = bridge.build_0x92840747_packet(op, b"\x01\x02\x03\x04")
                lut = None
            rcpt = sess.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, pkt, stage_lut_bytes=lut)
            self.assertTrue(rcpt.cp_executed, msg=f"Opcode 0x{op:04x} failed")
            self.assertEqual(rcpt.rx_completion_opcode, f"0x{op | 0x8000:04x}")
            self.assertEqual(rcpt.rx_hw_1000_alias_opcode, f"0x{op | 0x1000:04x}")
            self.assertEqual(rcpt.cp_mutation_bytes, 0)

    def test_21_cp_intrmask_gates_doorbell_co_execution_in_unicorn(self) -> None:
        sess = bridge.create_dual_ap_cp_session(force_clean_room=True)
        # Mask IRQ on Peer 1 via Thumb-2 MMIO write to INTRMASK (0x6780_0000)
        mask_code = (
            bridge._encode_thumb2_movw(0, 0x0000)
            + bridge._encode_thumb2_movt(0, 0x6780)
            + bridge._encode_thumb2_movw(1, 0x0000)
            + struct.pack("<H", 0x6001)  # str r1, [r0]
        )
        sess.cp_uc.mem_write(bridge.CP_ISR_BASE + 0x5000, mask_code)
        sess.cp_uc.emu_start(
            (bridge.CP_ISR_BASE + 0x5000) | 1,
            bridge.CP_ISR_BASE + 0x5000 + len(mask_code),
        )
        self.assertEqual(sess.bus.peers[bridge.PEER_ID_CP_CETUS].intrmask, 0)

        pkt = bridge.build_0x92840747_packet(bridge.OPCODE_VDF_PEAKING, b"\x01\x00")
        rcpt = sess.send_uipc_from_ap(bridge.UIPC_BB_TARGET_QUEUE, pkt)
        self.assertTrue(rcpt.tx_enqueued)
        self.assertFalse(rcpt.ap_doorbell_to_cp)
        self.assertFalse(rcpt.cp_executed)
        self.assertEqual(sess.bus.masked_doorbell_count, 1)

    def test_22_source_hygiene_o_rdonly_and_no_forbidden_writes(self) -> None:
        src = (FX3_VM_DIR / "dual_ap_cp_ivshmem_bridge.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertIn("CP_MUTATION_BYTES = 0", src)
        self.assertIn("U.UC_PROT_READ | U.UC_PROT_EXEC", src)


if __name__ == "__main__":
    unittest.main()
