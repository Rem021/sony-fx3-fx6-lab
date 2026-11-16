"""Clean-room unit tests for FX3 Multi-Port 48000-Baud BootROM Tier-3 Unbrick Verifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fx3_safety.multiport_bootrom_unbrick import (
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BAD_UART_BLINK_CODE,
    BOOTROM_SIZE_BYTES,
    BOOTROM_START,
    DDR_TRAINING_ENTRY,
    ESRAM_PAYLOAD_START,
    ESRAM_STACK_OVERFLOW_PTR,
    FASTBOOT_UART_BAUD,
    FASTBOOT_USB_VID_PID,
    MIRA_SRAM_START,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    SET_UNLOCK_MAGIC_DEAD,
    SET_UNLOCK_MAGIC_REAL,
    UART_BOOT_BAUD,
    WDT_TRAP_START,
    UartBootOpcode,
    audit_fastboot_command_sequence,
    audit_rp2040_firmware_spec,
    decode_bootrom_diagnostic_code,
    decode_uart_boot_frame,
    encode_uart_boot_frame,
    estimate_uart_transfer_time_ms,
    generate_rp2040_zero_open_drain_probe_spec,
    validate_bootrom_read_range,
    validate_mem_write_range,
    validate_rp2040_multiport_harness,
)


class MultiportBootromUnbrickTests(unittest.TestCase):
    def test_hard_locked_module_safety_flags(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)

    def test_valid_rp2040_zero_open_drain_harness(self) -> None:
        res = validate_rp2040_multiport_harness(
            board="RP2040-Zero",
            compile_flags=("-DOPEN_DRAIN", "-O2"),
            open_drain=True,
            gpio_drive_mode="open_drain",
            io_voltage_v=1.8,
            baud_rate=UART_BOOT_BAUD,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "VERIFIED_SAFE")
        self.assertTrue(res.open_drain_enforced)
        self.assertEqual(res.errors, [])

    def test_valid_explicit_1v8_open_drain_buffer_harness(self) -> None:
        ok = validate_rp2040_multiport_harness(
            board="explicit_1v8_open_drain_buffer",
            compile_flags=("-DOPEN_DRAIN",),
            open_drain=True,
            io_voltage_v=1.8,
        )
        self.assertTrue(ok.valid)
        bad_v = validate_rp2040_multiport_harness(
            board="explicit_1v8_open_drain_buffer",
            compile_flags=("-DOPEN_DRAIN",),
            open_drain=True,
            io_voltage_v=3.0,
        )
        self.assertFalse(bad_v.valid)
        self.assertEqual(bad_v.status, "BLOCKED_ELECTRICAL_HAZARD")

    def test_reject_standard_raspberry_pi_pico_gp29_vsys3_hazard(self) -> None:
        for pico_name in ("Raspberry Pi Pico", "pico", "pico_w", "rp2040-pico"):
            res = validate_rp2040_multiport_harness(
                board=pico_name,
                compile_flags=("-DOPEN_DRAIN",),
                open_drain=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_ELECTRICAL_HAZARD")
            self.assertTrue(any("VSYS/3" in e and "GP29" in e for e in res.errors))

    def test_reject_missing_open_drain_flag_or_push_pull_drive(self) -> None:
        no_flag = validate_rp2040_multiport_harness(
            board="rp2040_zero",
            compile_flags=("-O2",),
            open_drain=True,
        )
        self.assertFalse(no_flag.valid)
        self.assertEqual(no_flag.status, "BLOCKED_ELECTRICAL_HAZARD")

        no_od = validate_rp2040_multiport_harness(
            board="rp2040_zero",
            compile_flags=("-DOPEN_DRAIN",),
            open_drain=False,
        )
        self.assertFalse(no_od.valid)
        self.assertEqual(no_od.status, "BLOCKED_ELECTRICAL_HAZARD")

        push_pull = validate_rp2040_multiport_harness(
            board="rp2040_zero",
            compile_flags=("-DOPEN_DRAIN",),
            open_drain=True,
            gpio_drive_mode="push_pull_3v3",
        )
        self.assertFalse(push_pull.valid)
        self.assertEqual(push_pull.status, "BLOCKED_ELECTRICAL_HAZARD")

    def test_reject_overvoltage_missing_gnd_and_swapped_uart_pins(self) -> None:
        high_v = validate_rp2040_multiport_harness(io_voltage_v=3.3)
        self.assertFalse(high_v.valid)
        self.assertEqual(high_v.status, "BLOCKED_ELECTRICAL_HAZARD")

        no_gnd = validate_rp2040_multiport_harness(gnd_connected=False)
        self.assertFalse(no_gnd.valid)
        self.assertEqual(no_gnd.status, "BLOCKED_ELECTRICAL_HAZARD")

        swapped = validate_rp2040_multiport_harness(
            gpio_mapping={27: "PIN9_XRESET", 28: "PIN8_CAM_TX", 29: "PIN7_CAM_RX"}
        )
        self.assertFalse(swapped.valid)
        self.assertEqual(swapped.status, "BLOCKED_ELECTRICAL_HAZARD")

    def test_reject_wrong_initial_baud_rate(self) -> None:
        res = validate_rp2040_multiport_harness(baud_rate=FASTBOOT_UART_BAUD)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_ELECTRICAL_HAZARD")

    def test_mem_write_mira_sram_route_a_valid_and_bounds(self) -> None:
        ok = validate_mem_write_range(MIRA_SRAM_START, 0x10000, route="mira")
        self.assertTrue(ok.valid)
        self.assertEqual(ok.route, "mira")

        wrong_route = validate_mem_write_range(MIRA_SRAM_START, 0x1000, route="esram")
        self.assertFalse(wrong_route.valid)
        self.assertEqual(wrong_route.status, "BLOCKED_OUT_OF_BOUNDS_ADDRESS")

        oob = validate_mem_write_range(MIRA_SRAM_START, 0x1000000, route="mira")
        self.assertFalse(oob.valid)
        self.assertEqual(oob.status, "BLOCKED_OUT_OF_BOUNDS_ADDRESS")

    def test_mem_write_esram_route_b_valid_and_bounds(self) -> None:
        ok = validate_mem_write_range(ESRAM_PAYLOAD_START, 0x8000, route="esram")
        self.assertTrue(ok.valid)
        self.assertEqual(ok.route, "esram")

        ok_ptr = validate_mem_write_range(ESRAM_STACK_OVERFLOW_PTR, 4, route="auto")
        self.assertTrue(ok_ptr.valid)
        self.assertEqual(ok_ptr.route, "esram")

        ddr_collision = validate_mem_write_range(DDR_TRAINING_ENTRY, 0x1000, route="auto")
        self.assertFalse(ddr_collision.valid)
        self.assertEqual(ddr_collision.status, "BLOCKED_OUT_OF_BOUNDS_ADDRESS")

    def test_mem_write_blocks_wdt_trap_bootrom_and_unaligned(self) -> None:
        wdt = validate_mem_write_range(WDT_TRAP_START, 4)
        self.assertFalse(wdt.valid)
        self.assertEqual(wdt.status, "BLOCKED_WDT_TRAP_HAZARD")

        rom = validate_mem_write_range(BOOTROM_START, 64)
        self.assertFalse(rom.valid)
        self.assertEqual(rom.status, "BLOCKED_IMMUTABLE_BOOTROM")

        unaligned = validate_mem_write_range(MIRA_SRAM_START + 2, 16)
        self.assertFalse(unaligned.valid)
        self.assertEqual(unaligned.status, "BLOCKED_ALIGNMENT_ERROR")

    def test_bootrom_read_range_valid_48kib_and_blocks_wdt_trap(self) -> None:
        full_rom = validate_bootrom_read_range(BOOTROM_START, BOOTROM_SIZE_BYTES)
        self.assertTrue(full_rom.valid)
        self.assertEqual(full_rom.end_address, 0xFFFFBFFF)

        trap_edge = validate_bootrom_read_range(0xFFFFB000, 0x1001)
        self.assertFalse(trap_edge.valid)
        self.assertEqual(trap_edge.status, "BLOCKED_WDT_TRAP_HAZARD")

        below_rom = validate_bootrom_read_range(0xFFFE0000, 0x1000)
        self.assertFalse(below_rom.valid)
        self.assertEqual(below_rom.status, "BLOCKED_OUT_OF_BOUNDS_ADDRESS")

    def test_uart_boot_frame_codec_roundtrip_all_opcodes(self) -> None:
        f_unlock = encode_uart_boot_frame(
            UartBootOpcode.SET_UNLOCK,
            address=ESRAM_STACK_OVERFLOW_PTR,
            arg=SET_UNLOCK_MAGIC_REAL,
        )
        d_unlock = decode_uart_boot_frame(f_unlock)
        self.assertEqual(d_unlock.opcode, UartBootOpcode.SET_UNLOCK)
        self.assertEqual(d_unlock.arg, SET_UNLOCK_MAGIC_REAL)

        f_unlock2 = encode_uart_boot_frame(UartBootOpcode.SET_UNLOCK, arg=SET_UNLOCK_MAGIC_DEAD)
        self.assertEqual(decode_uart_boot_frame(f_unlock2).arg, SET_UNLOCK_MAGIC_DEAD)

        payload = b"\x01\x02\x03\x04" * 16
        f_write = encode_uart_boot_frame(
            UartBootOpcode.MEM_WRITE,
            address=ESRAM_PAYLOAD_START,
            arg=1,
            payload=payload,
        )
        d_write = decode_uart_boot_frame(f_write)
        self.assertEqual(d_write.opcode, UartBootOpcode.MEM_WRITE)
        self.assertEqual(d_write.address, ESRAM_PAYLOAD_START)
        self.assertEqual(d_write.payload, payload)

        f_read = encode_uart_boot_frame(UartBootOpcode.MEM_READ, address=BOOTROM_START, arg=512)
        d_read = decode_uart_boot_frame(f_read)
        self.assertEqual(d_read.opcode, UartBootOpcode.MEM_READ)
        self.assertEqual(d_read.arg, 512)

        f_jump = encode_uart_boot_frame(UartBootOpcode.JUMP_EXEC, address=MIRA_SRAM_START)
        self.assertEqual(decode_uart_boot_frame(f_jump).address, MIRA_SRAM_START)

    def test_uart_boot_frame_codec_rejects_corrupt_and_unsafe_frames(self) -> None:
        valid_frame = encode_uart_boot_frame(
            UartBootOpcode.MEM_WRITE,
            address=MIRA_SRAM_START,
            payload=b"ABCD",
        )
        tampered = bytearray(valid_frame)
        tampered[-1] ^= 0xFF
        with self.assertRaises(ValueError):
            decode_uart_boot_frame(bytes(tampered))

        bad_magic = b"XX" + valid_frame[2:]
        with self.assertRaises(ValueError):
            decode_uart_boot_frame(bad_magic)

        with self.assertRaises(ValueError):
            decode_uart_boot_frame(valid_frame + b"\x00")

        with self.assertRaises(ValueError):
            encode_uart_boot_frame(UartBootOpcode.MEM_READ, address=WDT_TRAP_START, arg=16)

        with self.assertRaises(ValueError):
            encode_uart_boot_frame(UartBootOpcode.SET_UNLOCK, arg=0x12345678)

        # Decode-time safety bound check even if raw frame was forged without enforce_bounds
        unsafe_raw = encode_uart_boot_frame(
            UartBootOpcode.MEM_READ,
            address=WDT_TRAP_START,
            arg=16,
            enforce_bounds=False,
        )
        with self.assertRaises(ValueError):
            decode_uart_boot_frame(unsafe_raw, enforce_bounds=True)

    def test_estimate_uart_transfer_time_ms_48000_baud(self) -> None:
        self.assertEqual(estimate_uart_transfer_time_ms(4800, UART_BOOT_BAUD), 1000.0)
        with self.assertRaises(ValueError):
            estimate_uart_transfer_time_ms(-1)

    def test_decode_0x100d_bad_uart_diagnostic_by_code_and_blinks(self) -> None:
        by_int = decode_bootrom_diagnostic_code(code=BAD_UART_BLINK_CODE)
        self.assertTrue(by_int.recognized)
        self.assertEqual(by_int.code_hex, "0x100D")
        self.assertEqual(by_int.short_blinks, 13)
        self.assertEqual(by_int.category, "BAD_UART_HANDSHAKE")
        self.assertTrue(any("RP2040-Zero" in s for s in by_int.remediation_steps))

        by_hex = decode_bootrom_diagnostic_code(code="0x100d")
        self.assertEqual(by_hex.category, "BAD_UART_HANDSHAKE")

        by_blinks = decode_bootrom_diagnostic_code(short_blinks=13)
        self.assertEqual(by_blinks.code_hex, "0x100D")
        self.assertEqual(by_blinks.category, "BAD_UART_HANDSHAKE")

    def test_decode_handshake_ok_wdt_trap_and_unknown_fail_closed(self) -> None:
        ok = decode_bootrom_diagnostic_code(code=0x0000)
        self.assertTrue(ok.recognized)
        self.assertEqual(ok.category, "HANDSHAKE_OK")

        wdt = decode_bootrom_diagnostic_code(code="wdt_trap")
        self.assertTrue(wdt.recognized)
        self.assertEqual(wdt.category, "WDT_TRAP_RESET")

        unk = decode_bootrom_diagnostic_code(code=0x9999, short_blinks=4)
        self.assertFalse(unk.recognized)
        self.assertEqual(unk.category, "UNKNOWN_BOOTROM_DIAGNOSTIC")

    def test_fastboot_firewall_permits_readonly_probe_and_backup_commands(self) -> None:
        audit = audit_fastboot_command_sequence(
            [
                "getvar:version",
                "oem dumpbrom",
                "oem dumpbrom 0xffff0000 0xc000",
                "oem partition dump",
                "oem cetus dumpnor",
                "oem cetus peek 0x1000",
            ]
        )
        self.assertTrue(audit.allowed)
        self.assertEqual(audit.status, "PERMITTED_READONLY_SESSION")
        self.assertFalse(audit.persistent_emmc_writes_authorized)
        self.assertFalse(audit.allow_destructive_fastboot)
        self.assertEqual(len(audit.permitted_commands), 6)
        self.assertEqual(audit.blocked_commands, [])

    def test_fastboot_firewall_blocks_destructive_commands(self) -> None:
        for cmd in (
            "flash:nflasha1",
            "erase:nflasha2",
            "oem format",
            "oem cetus poke 0x00108000 0x0",
            "oem cetus exec 0x00108000",
            "download:00010000",
        ):
            audit = audit_fastboot_command_sequence(["getvar:version", cmd])
            self.assertFalse(audit.allowed)
            self.assertEqual(audit.status, "BLOCKED_DESTRUCTIVE_COMMAND")
            self.assertIn(cmd, audit.blocked_commands)
            self.assertIn("getvar:version", audit.permitted_commands)

    def test_fastboot_firewall_hard_locks_authorization_even_if_caller_requests_true(self) -> None:
        audit = audit_fastboot_command_sequence(
            ["flash:nflasha1"],
            persistent_emmc_writes_authorized=True,
            allow_destructive_fastboot=True,
        )
        self.assertFalse(audit.allowed)
        self.assertFalse(audit.persistent_emmc_writes_authorized)
        self.assertFalse(audit.allow_destructive_fastboot)
        self.assertEqual(audit.status, "BLOCKED_DESTRUCTIVE_COMMAND")
        self.assertTrue(any("hard-locks both to False" in w for w in audit.warnings))

    def test_fastboot_firewall_blocks_wdt_trap_and_unknown_or_wrong_usb_id(self) -> None:
        wdt_audit = audit_fastboot_command_sequence(["oem dumpbrom 0xffffb000 0x2000"])
        self.assertFalse(wdt_audit.allowed)
        self.assertEqual(wdt_audit.decisions[0].status, "BLOCKED_WDT_TRAP_HAZARD")

        unk_audit = audit_fastboot_command_sequence(["oem arbitrary_vendor_cmd"])
        self.assertFalse(unk_audit.allowed)
        self.assertEqual(unk_audit.decisions[0].status, "BLOCKED_UNKNOWN_COMMAND")

        bad_usb = audit_fastboot_command_sequence(["getvar:version"], usb_vid_pid="054C:0DA1")
        self.assertFalse(bad_usb.allowed)
        self.assertEqual(bad_usb.status, "BLOCKED_USB_IDENTITY")

    def test_generate_rp2040_zero_open_drain_probe_spec_and_self_audit(self) -> None:
        spec = generate_rp2040_zero_open_drain_probe_spec()
        self.assertEqual(spec["board"], "waveshare_rp2040_zero")
        self.assertIn("-DOPEN_DRAIN", spec["compile_flags"])
        self.assertFalse(spec["persistent_emmc_writes_authorized"])
        self.assertFalse(spec["allow_destructive_fastboot"])
        self.assertEqual(spec["baud_rate"], UART_BOOT_BAUD)
        self.assertEqual(spec["handoff_baud_rate"], FASTBOOT_UART_BAUD)
        self.assertEqual(spec["routes"]["route_a_mira_sram"]["usb_enumeration"], FASTBOOT_USB_VID_PID)
        audit = audit_rp2040_firmware_spec(spec)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.status, "VERIFIED_SAFE")

    def test_audit_rp2040_firmware_spec_rejects_tampered_snippet_or_pico(self) -> None:
        spec = generate_rp2040_zero_open_drain_probe_spec()
        bad_snippet = dict(spec)
        bad_snippet["firmware_c_snippet"] = "/* stripped open drain guard */"
        res1 = audit_rp2040_firmware_spec(bad_snippet)
        self.assertFalse(res1.valid)
        self.assertEqual(res1.status, "BLOCKED_ELECTRICAL_HAZARD")

        pico_spec = dict(spec)
        pico_spec["board"] = "raspberry_pi_pico"
        res2 = audit_rp2040_firmware_spec(pico_spec)
        self.assertFalse(res2.valid)
        self.assertEqual(res2.status, "BLOCKED_ELECTRICAL_HAZARD")


if __name__ == "__main__":
    unittest.main()
