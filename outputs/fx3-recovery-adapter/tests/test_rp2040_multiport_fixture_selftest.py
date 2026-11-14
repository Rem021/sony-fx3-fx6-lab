"""Dual-mode unit tests for Phase 59 RP2040-Zero -DOPEN_DRAIN 1.8V Multi-Port Bench Fixture Self-Test.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real FX3 `2.05/nflasha1` via `os.O_RDONLY`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic anchor)
Designed for `<0.5s` execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import ROOT, is_forced_clean_room, resolve_donor_path
from fx3_recovery.rp2040_multiport_fixture_selftest import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    CAMERA_ATTACHED_ALLOWED_FOR_BENCH_SELFTEST,
    DEFAULT_CMAKE_OPEN_DRAIN_FLAGS,
    DEFAULT_CMAKE_SNIPPET,
    DEFAULT_OPEN_DRAIN_PIO_PROGRAM,
    DONOR_P1_205_RELPATH,
    FASTBOOT_UART_BAUD,
    LANC_ID_RESISTOR_OHM,
    MIN_ISOLATION_OHM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    RP2040_CLK_SYS_133MHZ_HZ,
    RP2040_CLK_SYS_DEFAULT_HZ,
    RP2040_FIXTURE_SELFTEST_SCHEMA,
    STATUS_FAIL_CAMERA_CONNECTED,
    STATUS_FAIL_CMAKE_BUILD_FLAGS,
    STATUS_FAIL_FORBIDDEN_BOARD,
    STATUS_FAIL_GND_CONTINUITY,
    STATUS_FAIL_ID_KEYING_CONFLICT,
    STATUS_FAIL_IDLE_OUT_OF_BAND,
    STATUS_FAIL_ISOLATION_SHORT,
    STATUS_FAIL_LOOPBACK_INTEGRITY,
    STATUS_FAIL_LOW_SINK_LEVEL,
    STATUS_FAIL_OVERVOLTAGE_HAZARD,
    STATUS_FAIL_PIO_PUSH_PULL,
    STATUS_FAIL_PIO_TIMING_DRIFT,
    STATUS_FAIL_UNDERVOLTAGE_PULLDOWN,
    STATUS_VERIFIED_BENCH_FIXTURE,
    UART_BOOT_BAUD,
    VMC_BNCM1_ID_RESISTOR_OHM,
    OhmmeterMeasurementSpec,
    audit_cmake_open_drain_flags,
    audit_ohmmeter_isolation,
    audit_pio_open_drain_program,
    compute_pio_uart_clkdiv,
    run_rp2040_multiport_fixture_selftest,
    simulate_uart_loopback_and_handshake,
    verify_multiport_id_keying,
    verify_open_drain_1v8_swing,
)


class Rp2040MultiportFixtureSelftestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-rp2040-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(CAMERA_ATTACHED_ALLOWED_FOR_BENCH_SELFTEST)
        self.assertEqual(fx3_recovery.RP2040_FIXTURE_SELFTEST_SCHEMA, RP2040_FIXTURE_SELFTEST_SCHEMA)
        for symbol in (
            "audit_ohmmeter_isolation",
            "verify_open_drain_1v8_swing",
            "verify_multiport_id_keying",
            "compute_pio_uart_clkdiv",
            "audit_pio_open_drain_program",
            "audit_cmake_open_drain_flags",
            "simulate_uart_loopback_and_handshake",
            "run_rp2040_multiport_fixture_selftest",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_ohmmeter_clean_bench_isolation_and_gnd_continuity_pass(self) -> None:
        res = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(camera_connected=False))
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_BENCH_FIXTURE)
        self.assertTrue(res.camera_disconnected_verified)
        self.assertTrue(res.ltc_cable_disconnected_verified)
        self.assertGreaterEqual(res.min_measured_isolation_ohm, MIN_ISOLATION_OHM)
        self.assertLessEqual(res.gnd_continuity_ohm, 2.0)

    def test_03_ohmmeter_blocks_when_camera_connected(self) -> None:
        res = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(camera_connected=True))
        self.assertFalse(res.passed)
        self.assertFalse(res.camera_disconnected_verified)
        self.assertEqual(res.status, STATUS_FAIL_CAMERA_CONNECTED)

    def test_04_ohmmeter_blocks_when_ltc_cable_connected(self) -> None:
        res = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(ltc_cable_connected=True))
        self.assertFalse(res.passed)
        self.assertFalse(res.ltc_cable_disconnected_verified)
        self.assertEqual(res.status, STATUS_FAIL_ID_KEYING_CONFLICT)

    def test_05_ohmmeter_blocks_vbus_5v_and_3v3_shorts_below_1_megohm(self) -> None:
        for field_name, bad_ohm in (
            ("vbus_to_uart_tx_ohm", 500_000.0),
            ("vbus_to_uart_rx_ohm", 0.5),
            ("vbus_to_id_ohm", 999_999.0),
            ("v3v3_to_uart_tx_ohm", 10_000.0),
            ("v3v3_to_uart_rx_ohm", 200_000.0),
            ("v3v3_to_xreset_ohm", 0.0),
        ):
            spec = OhmmeterMeasurementSpec(**{field_name: bad_ohm})
            res = audit_ohmmeter_isolation(spec)
            self.assertFalse(res.passed)
            self.assertEqual(res.status, STATUS_FAIL_ISOLATION_SHORT)
            self.assertIn(field_name, res.failed_rails)

    def test_06_ohmmeter_blocks_pin_to_pin_shorts_and_handles_inf(self) -> None:
        short_tx_rx = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(uart_tx_to_uart_rx_ohm=120.0))
        self.assertFalse(short_tx_rx.passed)
        self.assertEqual(short_tx_rx.status, STATUS_FAIL_ISOLATION_SHORT)

        short_gnd = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(uart_rx_to_gnd_ohm=0.0))
        self.assertFalse(short_gnd.passed)

        open_inf = audit_ohmmeter_isolation(
            OhmmeterMeasurementSpec(
                vbus_to_uart_tx_ohm=math.inf,
                vbus_to_uart_rx_ohm=math.inf,
                vbus_to_id_ohm=math.inf,
                vbus_to_xreset_ohm=math.inf,
                v3v3_to_uart_tx_ohm=math.inf,
                v3v3_to_uart_rx_ohm=math.inf,
                v3v3_to_id_ohm=math.inf,
                v3v3_to_xreset_ohm=math.inf,
                uart_tx_to_uart_rx_ohm=math.inf,
                uart_tx_to_gnd_ohm=math.inf,
                uart_rx_to_gnd_ohm=math.inf,
                xreset_to_gnd_ohm=math.inf,
            )
        )
        self.assertTrue(open_inf.passed, open_inf.errors)
        self.assertIsNone(open_inf.min_measured_isolation_ohm)

    def test_07_ohmmeter_blocks_gnd_open_circuit_or_high_resistance(self) -> None:
        bad_gnd = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(gnd_continuity_ohm=5.5))
        self.assertFalse(bad_gnd.passed)
        self.assertEqual(bad_gnd.status, STATUS_FAIL_GND_CONTINUITY)

        missing_gnd = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(gnd_continuity_ohm=None))
        self.assertFalse(missing_gnd.passed)
        self.assertEqual(missing_gnd.status, STATUS_FAIL_GND_CONTINUITY)

    def test_08_ohmmeter_blocks_forbidden_pico_boards_and_swapped_gpio(self) -> None:
        for bad_board in ("pico", "pico_w", "pico_2", "raspberry_pi_pico"):
            res = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(), board=bad_board)
            self.assertFalse(res.passed)
            self.assertEqual(res.status, STATUS_FAIL_FORBIDDEN_BOARD)

        swapped = audit_ohmmeter_isolation(
            OhmmeterMeasurementSpec(),
            gpio_mapping={27: "PIN9_XRESET", 28: "PIN8_CAM_TX", 29: "PIN7_CAM_RX"},
        )
        self.assertFalse(swapped.passed)

    def test_09_open_drain_1v8_swing_passes_inside_171_to_189_band(self) -> None:
        for v in (1.71, 1.80, 1.89):
            res = verify_open_drain_1v8_swing(
                v_idle_tx_v=v,
                v_idle_rx_v=v,
                v_idle_xreset_v=v,
                v_low_tx_v=0.08,
                v_low_xreset_v=0.12,
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.status, STATUS_VERIFIED_BENCH_FIXTURE)
            self.assertFalse(res.overvoltage_hazard)
            self.assertTrue(res.open_drain_enforced)

    def test_10_open_drain_1v8_swing_triggers_fail_overvoltage_hazard_above_198v(self) -> None:
        for v_bad in (1.981, 2.50, 3.30):
            res = verify_open_drain_1v8_swing(v_idle_tx_v=v_bad)
            self.assertFalse(res.passed)
            self.assertTrue(res.overvoltage_hazard)
            self.assertEqual(res.status, STATUS_FAIL_OVERVOLTAGE_HAZARD)

    def test_11_open_drain_swing_rejects_push_pull_and_active_high_drive(self) -> None:
        r1 = verify_open_drain_1v8_swing(drive_mode="push_pull")
        self.assertFalse(r1.passed)
        self.assertTrue(r1.overvoltage_hazard)
        self.assertEqual(r1.status, STATUS_FAIL_OVERVOLTAGE_HAZARD)

        r2 = verify_open_drain_1v8_swing(open_drain=False)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.status, STATUS_FAIL_OVERVOLTAGE_HAZARD)

        r3 = verify_open_drain_1v8_swing(active_high_drive=True)
        self.assertFalse(r3.passed)
        self.assertEqual(r3.status, STATUS_FAIL_OVERVOLTAGE_HAZARD)

    def test_12_open_drain_swing_rejects_190_to_198_undervoltage_and_high_vlow(self) -> None:
        out_band = verify_open_drain_1v8_swing(v_idle_rx_v=1.93)
        self.assertFalse(out_band.passed)
        self.assertFalse(out_band.overvoltage_hazard)
        self.assertEqual(out_band.status, STATUS_FAIL_IDLE_OUT_OF_BAND)

        under = verify_open_drain_1v8_swing(v_idle_xreset_v=1.65)
        self.assertFalse(under.passed)
        self.assertEqual(under.status, STATUS_FAIL_UNDERVOLTAGE_PULLDOWN)

        high_low = verify_open_drain_1v8_swing(v_low_tx_v=0.55)
        self.assertFalse(high_low.passed)
        self.assertEqual(high_low.status, STATUS_FAIL_LOW_SINK_LEVEL)

    def test_13_id_keying_matrix_bootrom_uart_boot_and_console_readonly(self) -> None:
        bootrom_ok = verify_multiport_id_keying(requested_mode="BOOTROM_UART_BOOT", id_resistor_ohm=None)
        self.assertTrue(bootrom_ok.passed, bootrom_ok.errors)
        self.assertEqual(bootrom_ok.detected_keying, "OPEN_HIZ_UART_SAFE")
        self.assertTrue(bootrom_ok.xreset_enabled)
        self.assertTrue(bootrom_ok.uart_tx_enabled)

        console_ok = verify_multiport_id_keying(requested_mode="CONSOLE_READONLY", id_resistor_ohm=2_000_000.0)
        self.assertTrue(console_ok.passed, console_ok.errors)
        self.assertFalse(console_ok.xreset_enabled)
        self.assertFalse(console_ok.uart_tx_enabled)

        console_bad_rst = verify_multiport_id_keying(
            requested_mode="CONSOLE_READONLY", id_resistor_ohm=None, xreset_enabled=True
        )
        self.assertFalse(console_bad_rst.passed)
        self.assertEqual(console_bad_rst.status, STATUS_FAIL_ID_KEYING_CONFLICT)

    def test_14_id_keying_matrix_blocks_vmc_bncm1_680k_and_lanc_100k_conflicts(self) -> None:
        for r_ohm, expected_det in (
            (float(VMC_BNCM1_ID_RESISTOR_OHM), "VMC_BNCM1_LTC_ADAPTER"),
            (612_000.0, "VMC_BNCM1_LTC_ADAPTER"),
            (748_000.0, "VMC_BNCM1_LTC_ADAPTER"),
            (float(LANC_ID_RESISTOR_OHM), "LANC_REMOTE"),
            (90_000.0, "LANC_REMOTE"),
            (110_000.0, "LANC_REMOTE"),
            (0.0, "UNKNOWN_OR_SHORTED_ID_RESISTOR"),
            (47_000.0, "UNKNOWN_OR_SHORTED_ID_RESISTOR"),
        ):
            res = verify_multiport_id_keying(requested_mode="BOOTROM_UART_BOOT", id_resistor_ohm=r_ohm)
            self.assertFalse(res.passed)
            self.assertTrue(res.conflict_detected)
            self.assertEqual(res.status, STATUS_FAIL_ID_KEYING_CONFLICT)
            self.assertEqual(res.detected_keying, expected_det)

    def test_15_pio_clkdiv_125mhz_48000_and_115200_baud_exact_math(self) -> None:
        d48 = compute_pio_uart_clkdiv(RP2040_CLK_SYS_DEFAULT_HZ, UART_BOOT_BAUD)
        self.assertTrue(d48.passed, d48.errors)
        self.assertEqual(d48.clkdiv_int, 325)
        self.assertEqual(d48.clkdiv_frac, 133)
        self.assertAlmostEqual(d48.ideal_bit_period_us, 20.833333, places=3)
        self.assertLessEqual(d48.baud_error_pct, 0.05)

        d115 = compute_pio_uart_clkdiv(RP2040_CLK_SYS_DEFAULT_HZ, FASTBOOT_UART_BAUD)
        self.assertTrue(d115.passed, d115.errors)
        self.assertEqual(d115.clkdiv_int, 135)
        self.assertEqual(d115.clkdiv_frac, 162)
        self.assertAlmostEqual(d115.ideal_bit_period_us, 8.680556, places=3)
        self.assertLessEqual(d115.baud_error_pct, 0.05)

    def test_16_pio_clkdiv_133mhz_48000_and_115200_baud_exact_math(self) -> None:
        d48 = compute_pio_uart_clkdiv(RP2040_CLK_SYS_133MHZ_HZ, UART_BOOT_BAUD)
        self.assertTrue(d48.passed, d48.errors)
        self.assertEqual(d48.clkdiv_int, 346)
        self.assertEqual(d48.clkdiv_frac, 91)
        self.assertLessEqual(d48.baud_error_pct, 0.05)

        d115 = compute_pio_uart_clkdiv(RP2040_CLK_SYS_133MHZ_HZ, FASTBOOT_UART_BAUD)
        self.assertTrue(d115.passed, d115.errors)
        self.assertEqual(d115.clkdiv_int, 144)
        self.assertEqual(d115.clkdiv_frac, 80)
        self.assertLessEqual(d115.baud_error_pct, 0.05)

    def test_17_pio_clkdiv_rejects_integer_only_truncation_and_unsupported_rates(self) -> None:
        int_only = compute_pio_uart_clkdiv(
            RP2040_CLK_SYS_DEFAULT_HZ, UART_BOOT_BAUD, force_integer_only=True
        )
        self.assertFalse(int_only.passed)
        self.assertEqual(int_only.status, STATUS_FAIL_PIO_TIMING_DRIFT)
        self.assertGreater(int_only.baud_error_pct, 0.05)

        bad_clk = compute_pio_uart_clkdiv(48_000_000, UART_BOOT_BAUD)
        self.assertFalse(bad_clk.passed)
        self.assertEqual(bad_clk.status, STATUS_FAIL_PIO_TIMING_DRIFT)

        bad_baud = compute_pio_uart_clkdiv(RP2040_CLK_SYS_DEFAULT_HZ, 9600)
        self.assertFalse(bad_baud.passed)

    def test_18_pio_program_audit_passes_default_pindirs_program(self) -> None:
        res = audit_pio_open_drain_program(DEFAULT_OPEN_DRAIN_PIO_PROGRAM)
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_BENCH_FIXTURE)
        self.assertTrue(res.uses_pindirs_direction_toggle)
        self.assertFalse(res.drives_pins_high)
        self.assertEqual(res.pins_init_level, 0)
        self.assertEqual(res.cycles_per_bit, 8)

    def test_19_pio_program_audit_rejects_push_pull_pins_and_bad_sideset(self) -> None:
        push_pull_prog = (
            ".program bad_uart_tx",
            ".side_set 1 opt",
            "    pull block side 1 [7]",
            "    out pins, 1",
        )
        res = audit_pio_open_drain_program(push_pull_prog)
        self.assertFalse(res.passed)
        self.assertTrue(res.drives_pins_high)
        self.assertEqual(res.status, STATUS_FAIL_PIO_PUSH_PULL)

        bad_init = audit_pio_open_drain_program(DEFAULT_OPEN_DRAIN_PIO_PROGRAM, pins_init_level=1)
        self.assertFalse(bad_init.passed)
        self.assertEqual(bad_init.status, STATUS_FAIL_PIO_PUSH_PULL)

        set_pins_high = audit_pio_open_drain_program(
            (".side_set 1 opt pindirs", "set pins, 1 side 0 [7]")
        )
        self.assertFalse(set_pins_high.passed)

    def test_20_cmake_audit_enforces_open_drain_equals_1_and_rp2040_zero(self) -> None:
        ok = audit_cmake_open_drain_flags(
            board="waveshare_rp2040_zero",
            compile_flags=DEFAULT_CMAKE_OPEN_DRAIN_FLAGS,
            cmake_text=DEFAULT_CMAKE_SNIPPET,
        )
        self.assertTrue(ok.passed, ok.errors)
        self.assertTrue(ok.open_drain_equals_one)

        missing = audit_cmake_open_drain_flags(compile_flags=("-DUART_BOOT_BAUD=48000",))
        self.assertFalse(missing.passed)
        self.assertEqual(missing.status, STATUS_FAIL_CMAKE_BUILD_FLAGS)

        zero_flag = audit_cmake_open_drain_flags(compile_flags=("-DOPEN_DRAIN=0",))
        self.assertFalse(zero_flag.passed)
        self.assertEqual(zero_flag.status, STATUS_FAIL_CMAKE_BUILD_FLAGS)

        bare_flag = audit_cmake_open_drain_flags(compile_flags=("-DOPEN_DRAIN",), require_equals_one=True)
        self.assertFalse(bare_flag.passed)

        pico_cmake = audit_cmake_open_drain_flags(
            board="waveshare_rp2040_zero",
            compile_flags=("-DOPEN_DRAIN=1",),
            cmake_text="set(PICO_BOARD pico)\ntarget_compile_definitions(x PRIVATE OPEN_DRAIN=1)",
        )
        self.assertFalse(pico_cmake.passed)
        self.assertEqual(pico_cmake.status, STATUS_FAIL_FORBIDDEN_BOARD)

    def test_21_loopback_48000_and_115200_8n1_and_bootrom_handshake_echo(self) -> None:
        for baud in (UART_BOOT_BAUD, FASTBOOT_UART_BAUD):
            res = simulate_uart_loopback_and_handshake(b"MIRA_FX3_LOOPBACK_OK", baud_rate=baud)
            self.assertTrue(res.passed, res.errors)
            self.assertTrue(res.bit_exact_match)
            self.assertEqual(res.tx_hex, res.rx_hex)
            self.assertTrue(res.handshake_echo_verified)
            self.assertTrue(res.bootrom_read_echo_verified)
            self.assertTrue(res.wdt_trap_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_22_loopback_even_and_odd_parity_and_parity_error_rejection(self) -> None:
        for p in ("E", "O"):
            ok = simulate_uart_loopback_and_handshake(b"\x55\xaa\x0f\xf0", parity=p)
            self.assertTrue(ok.passed, ok.errors)
            self.assertEqual(ok.parity_errors, 0)

            bad = simulate_uart_loopback_and_handshake(
                b"\x55\xaa", parity=p, inject_parity_error=True, run_bootrom_echo=False
            )
            self.assertFalse(bad.passed)
            self.assertGreaterEqual(bad.parity_errors, 1)
            self.assertEqual(bad.status, STATUS_FAIL_LOOPBACK_INTEGRITY)

    def test_23_loopback_rejects_start_bit_glitch(self) -> None:
        res = simulate_uart_loopback_and_handshake(
            b"GLITCH_TEST", inject_start_glitch=True, run_bootrom_echo=False
        )
        self.assertFalse(res.passed)
        self.assertGreaterEqual(res.glitch_rejections, 1)
        self.assertEqual(res.status, STATUS_FAIL_LOOPBACK_INTEGRITY)

    def test_24_loopback_rejects_stop_bit_framing_error(self) -> None:
        res = simulate_uart_loopback_and_handshake(
            b"FRAME_ERR", inject_stop_bit_error=True, run_bootrom_echo=False
        )
        self.assertFalse(res.passed)
        self.assertGreaterEqual(res.framing_errors, 1)
        self.assertEqual(res.status, STATUS_FAIL_LOOPBACK_INTEGRITY)

    def test_25_loopback_rejects_stuck_low_break_and_open_wire(self) -> None:
        brk = simulate_uart_loopback_and_handshake(
            b"BREAK", inject_stuck_low_break=True, run_bootrom_echo=False
        )
        self.assertFalse(brk.passed)
        self.assertGreaterEqual(brk.framing_errors, 1)

        opn = simulate_uart_loopback_and_handshake(
            b"OPEN", inject_open_wire=True, run_bootrom_echo=False
        )
        self.assertFalse(opn.passed)
        self.assertEqual(opn.bytes_received, 0)

    def test_26_loopback_forbids_persistent_emmc_writes_authorized_override(self) -> None:
        res = simulate_uart_loopback_and_handshake(
            b"SAFE", persistent_emmc_writes_authorized=True
        )
        self.assertFalse(res.passed)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_27_dual_mode_selftest_125mhz_and_133mhz_deterministic_json(self) -> None:
        r1 = run_rp2040_multiport_fixture_selftest(force_clean_room=True, clk_sys_hz=RP2040_CLK_SYS_DEFAULT_HZ)
        r2 = run_rp2040_multiport_fixture_selftest(force_clean_room=True, clk_sys_hz=RP2040_CLK_SYS_DEFAULT_HZ)
        self.assertTrue(r1.all_passed, r1.errors)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.to_dict(), r2.to_dict())
        self.assertFalse(r1.camera_connected)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertTrue(r1.glitch_rejection_verified)
        self.assertTrue(r1.framing_error_rejection_verified)
        encoded = json.dumps(r1.to_dict(), sort_keys=True, allow_nan=False)
        self.assertIn(STATUS_VERIFIED_BENCH_FIXTURE, encoded)

        r133 = run_rp2040_multiport_fixture_selftest(force_clean_room=True, clk_sys_hz=RP2040_CLK_SYS_133MHZ_HZ)
        self.assertTrue(r133.all_passed, r133.errors)

        auto_rep = run_rp2040_multiport_fixture_selftest()
        self.assertTrue(auto_rep.all_passed, auto_rep.errors)
        donor_p1 = resolve_donor_path(DONOR_P1_205_RELPATH)
        if not is_forced_clean_room() and donor_p1.is_file():
            self.assertEqual(auto_rep.verification_mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(auto_rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_28_cli_verify_rp2040_fixture_clean_room_json_and_out_dir(self) -> None:
        self._sandbox.parent.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox

        buf_sum = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-rp2040-fixture", "--clean-room"]):
            with redirect_stdout(buf_sum):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_BENCH_FIXTURE", buf_sum.getvalue())
        self.assertIn("camera_connected=False", buf_sum.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_sum.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(ROOT / "outputs" / "fx3-recovery-adapter")
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                "-m",
                "fx3_recovery",
                "verify-rp2040-fixture",
                "--clean-room",
                "--json",
                "--out",
                str(out_dir),
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(payload["camera_connected"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertTrue((out_dir / "rp2040-fixture-report.json").is_file())

    def test_29_cli_no_raw_bytes_repr_in_stdout_or_report(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-rp2040-fixture", "--clean-room", "--json"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertNotIn("b'\\x", out)
        self.assertNotIn('b"\\x', out)

    def test_30_total_selftest_runtime_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_rp2040_multiport_fixture_selftest()
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertLess(elapsed, 0.5)


if __name__ == "__main__":
    unittest.main()
