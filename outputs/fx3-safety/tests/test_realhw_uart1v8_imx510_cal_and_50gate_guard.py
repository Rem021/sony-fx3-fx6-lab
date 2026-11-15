"""Fast dual-mode unit tests for Phase 158 — Real-Hardware Main Track Part 12:
Gate G49 (`1.8V CMOS ttyAMA0 460800 8N1` RX-Only Passive Tap, Multi-USB
`VMC-BNCM1` Timecode Contention Firewall & Off-Chip `1.8V 8-bit` eMMC ISP
Passive Read Guard), Gate G50 (`IMX510` `p2:/setting/psd.bin & defdet.bin`
Per-Sensor Calibration NVS Lock, Dual-Base ISO `800/12800` Gain Guard &
`.cube` 3D MLUT Non-Double-Bake Guard), and Unified 50-Gate Master Safety
Preflight (`G01..G50` / `verify-50-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import (
    REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA,
    SPI_NOR_WRITE_AUTHORIZED as PRIOR_SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE,
    STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION,
    evaluate_48gate_preflight,
)
from fx3_safety.realhw_uart1v8_imx510_cal_and_50gate_guard import (
    CUBE_DOMAIN_MAX_VALUE,
    CUBE_DOMAIN_MIN_VALUE,
    CUBE_VALID_GRID_SIZES,
    DEFAULT_SYNTHETIC_DEFDET_SHA256,
    DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    DEFAULT_SYNTHETIC_PSD_SHA256,
    EMMC_ISP_MAX_CLK_MHZ,
    EMMC_ISP_REQUIRED_BUS_WIDTH_BITS,
    EMMC_ISP_VCCQ_MAX_MV,
    EMMC_ISP_VCCQ_MIN_MV,
    EMMC_ISP_VCCQ_NOMINAL_MV,
    G49_GATE_CODE,
    G49_GATE_ID,
    G50_GATE_CODE,
    G50_GATE_ID,
    IMX510_BASE_ISO_HIGH,
    IMX510_BASE_ISO_LOW,
    IMX510_GAIN_MODE_HCG,
    IMX510_GAIN_MODE_LCG,
    IMX510_HCG_MAX_ANALOG_GAIN_DB,
    IMX510_HCG_MAX_ISO,
    IMX510_HCG_MIN_ANALOG_GAIN_DB,
    IMX510_HCG_MIN_ISO,
    IMX510_LCG_MAX_ANALOG_GAIN_DB,
    IMX510_LCG_MAX_ISO,
    IMX510_LCG_MIN_ANALOG_GAIN_DB,
    IMX510_LCG_MIN_ISO,
    IMX510_VALID_BASE_ISOS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_PHASE158_DONOR_SPECS,
    REALHW_UART1V8_IMX510_50GATE_SCHEMA,
    REALHW_UART1V8_IMX510_50GATE_VERSION,
    SENSOR_CAL_NVS_FILES,
    SLOG3_RECORDING_COLOR_SPACES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD,
    STATUS_BLOCKED_G49_TELEMETRY_INVALID,
    STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE,
    STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION,
    STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE,
    STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS,
    STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY,
    STATUS_BLOCKED_G50_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_SAFE,
    STATUS_VERIFIED_G49,
    STATUS_VERIFIED_G50,
    STATUS_VERIFIED_SAFE,
    UART_CANONICAL_BAUD,
    UART_CANONICAL_DEVICES,
    UART_CANONICAL_FRAMING,
    UART_IO_MAX_MV,
    UART_IO_MIN_MV,
    UART_IO_NOMINAL_MV,
    UART_MAX_BACKPOWER_LEAKAGE_UA,
    audit_phase158_donor_contracts,
    build_synthetic_identity_cube_text,
    evaluate_50_master_safety_gates,
    evaluate_50gate_preflight,
    evaluate_g49_uart1v8_isp,
    evaluate_g50_imx510_sensor_cal,
    main as module_cli_main,
    validate_cube_3dlut,
    validate_emmc_isp_1v8_passive_read,
    validate_imx510_dual_base_iso_gain,
    validate_sensor_calibration_nvs_lock,
    validate_uart_1v8_passive_rx,
    verify_imx510_sensor_cal_and_mlut_guard,
    verify_uart1v8_vmc_bncm1_and_emmc_isp_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwUart1v8Imx510CalAnd50GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PRIOR_SPI_NOR_WRITE_AUTHORIZED)
        self.assertEqual(
            REALHW_UART1V8_IMX510_50GATE_SCHEMA,
            "fx3-realhw-uart1v8-imx510-50gate-preflight-v1",
        )
        self.assertEqual(REALHW_UART1V8_IMX510_50GATE_VERSION, "1.0.0")
        self.assertEqual(
            SENSOR_CAL_NVS_FILES,
            ("p2:/setting/psd.bin", "p2:/setting/defdet.bin", "p18:/lens/LENSFILE.BIN"),
        )
        for sym in (
            "CUBE_DOMAIN_MAX_VALUE",
            "CUBE_DOMAIN_MIN_VALUE",
            "CUBE_VALID_GRID_SIZES",
            "DEFAULT_SYNTHETIC_DEFDET_SHA256",
            "DEFAULT_SYNTHETIC_LENSFILE_SHA256",
            "DEFAULT_SYNTHETIC_PSD_SHA256",
            "EMMC_ISP_MAX_CLK_MHZ",
            "EMMC_ISP_REQUIRED_BUS_WIDTH_BITS",
            "EMMC_ISP_VCCQ_MAX_MV",
            "EMMC_ISP_VCCQ_MIN_MV",
            "EMMC_ISP_VCCQ_NOMINAL_MV",
            "G49_GATE_ID",
            "G49_GATE_CODE",
            "G50_GATE_ID",
            "G50_GATE_CODE",
            "IMX510_BASE_ISO_LOW",
            "IMX510_BASE_ISO_HIGH",
            "IMX510_VALID_BASE_ISOS",
            "PINNED_PHASE158_DONOR_SPECS",
            "REALHW_UART1V8_IMX510_50GATE_SCHEMA",
            "REALHW_UART1V8_IMX510_50GATE_VERSION",
            "SENSOR_CAL_NVS_FILES",
            "SLOG3_RECORDING_COLOR_SPACES",
            "STATUS_VERIFIED_G49",
            "STATUS_VERIFIED_G50",
            "STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE",
            "STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION",
            "STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD",
            "STATUS_BLOCKED_G49_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY",
            "STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS",
            "STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE",
            "STATUS_BLOCKED_G50_TELEMETRY_INVALID",
            "UART_CANONICAL_BAUD",
            "UART_CANONICAL_DEVICES",
            "UART_CANONICAL_FRAMING",
            "UART_IO_MIN_MV",
            "UART_IO_NOMINAL_MV",
            "UART_IO_MAX_MV",
            "UART_MAX_BACKPOWER_LEAKAGE_UA",
            "Phase158DonorAuditResult",
            "Cube3dLutValidationResult",
            "Uart1v8VmcBncm1IspGuardResult",
            "Imx510SensorCalMlutGuardResult",
            "G49Uart1v8IspResult",
            "G50Imx510SensorCalResult",
            "Master50GateReport",
            "audit_phase158_donor_contracts",
            "build_synthetic_identity_cube_text",
            "validate_uart_1v8_passive_rx",
            "validate_emmc_isp_1v8_passive_read",
            "validate_sensor_calibration_nvs_lock",
            "validate_imx510_dual_base_iso_gain",
            "validate_cube_3dlut",
            "verify_uart1v8_vmc_bncm1_and_emmc_isp_guard",
            "verify_imx510_sensor_cal_and_mlut_guard",
            "evaluate_g49_uart1v8_isp",
            "evaluate_g50_imx510_sensor_cal",
            "evaluate_50gate_preflight",
            "evaluate_50_master_safety_gates",
            "realhw_uart1v8_imx510_cal_and_50gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing package export: {sym}")
        # Ensure prior colliding package-level constants remain untouched
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        clean_res = audit_phase158_donor_contracts(force_clean_room=True)
        self.assertTrue(clean_res.valid)
        self.assertEqual(clean_res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(clean_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_res.access_mode, "O_RDONLY")
        self.assertEqual(clean_res.files_inspected, 0)
        self.assertEqual(len(clean_res.checked_markers), len(PINNED_PHASE158_DONOR_SPECS))
        self.assertEqual(clean_res.missing_markers, ())
        self.assertTrue(clean_res.fx3_contracts_verified)
        self.assertTrue(clean_res.fx6_contracts_verified)

        # Missing donor root deterministically falls back to CLEAN_ROOM_SYNTHETIC
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_res = audit_phase158_donor_contracts(
                work_root=Path(tmpdir), force_clean_room=False
            )
            self.assertTrue(missing_res.valid)
            self.assertEqual(missing_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        # When local donors exist and FX3_FX6_FORCE_CLEAN_ROOM!=1, verify strict os.O_RDONLY
        orig_open = os.open
        seen_flags: list[int] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch(
            "fx3_safety.realhw_uart1v8_imx510_cal_and_50gate_guard.os.open",
            side_effect=spy_open,
        ):
            auto_res = audit_phase158_donor_contracts(repo_root=DEFAULT_REPO_ROOT)

        self.assertTrue(auto_res.valid)
        self.assertEqual(auto_res.access_mode, "O_RDONLY")
        if auto_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(auto_res.files_inspected, len(PINNED_PHASE158_DONOR_SPECS))
            self.assertEqual(len(seen_flags), len(PINNED_PHASE158_DONOR_SPECS))
            for fl in seen_flags:
                self.assertEqual(fl & 3, os.O_RDONLY)

        # Verify zero raw binary repr leakage in JSON output
        dumped = json.dumps(auto_res.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("b\"\\x7fELF", dumped)

    def test_03_donor_audit_fails_closed_on_tampered_sha_or_missing_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, toks, _lbl) in PINNED_PHASE158_DONOR_SPECS.items():
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(t + b"\x00" for t in toks)
                if len(payload) < size:
                    payload = payload + b"\x00" * min(128, size - len(payload))
                p.write_bytes(payload)

            tampered = audit_phase158_donor_contracts(work_root=work, force_clean_room=False)
            self.assertFalse(tampered.valid)
            self.assertEqual(tampered.status, STATUS_BLOCKED_DONOR_INTEGRITY)
            self.assertEqual(tampered.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertFalse(tampered.fx3_contracts_verified)
            self.assertFalse(tampered.fx6_contracts_verified)
            self.assertGreaterEqual(len(tampered.errors), len(PINNED_PHASE158_DONOR_SPECS))

            v49, r49 = evaluate_g49_uart1v8_isp(donor_audit=tampered)
            self.assertFalse(v49.passed)
            self.assertFalse(r49.valid)
            self.assertIn(STATUS_BLOCKED_DONOR_INTEGRITY, v49.violation_codes)

            v50, r50 = evaluate_g50_imx510_sensor_cal(donor_audit=tampered)
            self.assertFalse(v50.passed)
            self.assertFalse(r50.valid)
            self.assertIn(STATUS_BLOCKED_DONOR_INTEGRITY, v50.violation_codes)

    # --- 2. Pure Helper Function Unit Tests ---

    def test_04_helper_validate_uart_1v8_passive_rx(self) -> None:
        self.assertTrue(validate_uart_1v8_passive_rx())
        self.assertTrue(
            validate_uart_1v8_passive_rx(
                "ttyAMA0", 460800, "8N1", 1620.0, False, 5.0
            )
        )
        self.assertTrue(
            validate_uart_1v8_passive_rx(
                "/dev/ttyAMA0", 460800, "8n1", 1950.0, False, 0.0
            )
        )
        # Overvoltage 3.3V / 5.0V FTDI
        self.assertFalse(validate_uart_1v8_passive_rx(uart_io_voltage_mv=3300.0))
        self.assertFalse(validate_uart_1v8_passive_rx(uart_io_voltage_mv=5000.0))
        self.assertFalse(validate_uart_1v8_passive_rx(uart_io_voltage_mv=1950.1))
        self.assertFalse(validate_uart_1v8_passive_rx(uart_io_voltage_mv=1619.9))
        # TX connected or non-passive RX or backpower leakage > 5uA
        self.assertFalse(validate_uart_1v8_passive_rx(tx_line_connected=True))
        self.assertFalse(validate_uart_1v8_passive_rx(rx_high_z_passive=False))
        self.assertFalse(validate_uart_1v8_passive_rx(backpower_leakage_ua=5.1))
        # Wrong device, baud, or framing
        self.assertFalse(validate_uart_1v8_passive_rx(uart_device="/dev/ttyUSB0"))
        self.assertFalse(validate_uart_1v8_passive_rx(baud_rate=115200))
        self.assertFalse(validate_uart_1v8_passive_rx(framing="8E1"))

    def test_05_helper_validate_emmc_isp_1v8_passive_read(self) -> None:
        self.assertTrue(validate_emmc_isp_1v8_passive_read())
        self.assertTrue(
            validate_emmc_isp_1v8_passive_read(
                1800.0, 26.0, True, True, offchip_emmc_isp_active=True
            )
        )
        # Active ISP without RESET# low fails
        self.assertFalse(
            validate_emmc_isp_1v8_passive_read(
                1800.0, 24.0, False, True, offchip_emmc_isp_active=True
            )
        )
        # 3.3V VCCQ fails
        self.assertFalse(validate_emmc_isp_1v8_passive_read(isp_vccq_mv=3300.0))
        # Overclocked ISP clock > 26MHz fails
        self.assertFalse(validate_emmc_isp_1v8_passive_read(isp_clk_mhz=26.1))
        # Non-8-bit bus fails
        self.assertFalse(validate_emmc_isp_1v8_passive_read(isp_bus_width_bits=4))
        # Unblocked CMD24/CMD25 fails
        self.assertFalse(
            validate_emmc_isp_1v8_passive_read(isp_write_cmd24_cmd25_blocked=False)
        )
        # Mutation bytes > 0 fails
        self.assertFalse(validate_emmc_isp_1v8_passive_read(isp_mutation_bytes=512))

    def test_06_helper_validate_sensor_calibration_nvs_lock(self) -> None:
        self.assertTrue(validate_sensor_calibration_nvs_lock())
        self.assertFalse(validate_sensor_calibration_nvs_lock(p2_setting_ro_locked=False))
        self.assertFalse(validate_sensor_calibration_nvs_lock(p18_lens_ro_locked=False))
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(same_body_sensor_cal_sha256_match=False)
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(sensor_cal_mutation_bytes=64)
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(sensor_cal_writes_requested=1)
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(
                cross_body_or_fx6_cal_import_attempted=True
            )
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(psd_bin_sha256="f" * 64)
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(defdet_bin_sha256="f" * 64)
        )
        self.assertFalse(
            validate_sensor_calibration_nvs_lock(lensfile_bin_sha256="f" * 64)
        )

    def test_07_helper_validate_imx510_dual_base_iso_gain(self) -> None:
        ok1, r1 = validate_imx510_dual_base_iso_gain(800, "LCG", 800, 0.0)
        self.assertTrue(ok1)
        self.assertEqual(r1, "IMX510_LCG_BASE800_LEGAL")
        ok2, _ = validate_imx510_dual_base_iso_gain(800, "LCG", 160, -6.0)
        self.assertTrue(ok2)
        ok3, _ = validate_imx510_dual_base_iso_gain(800, "LCG", 10000, 22.0)
        self.assertTrue(ok3)
        ok4, r4 = validate_imx510_dual_base_iso_gain(12800, "HCG", 12800, 0.0)
        self.assertTrue(ok4)
        self.assertEqual(r4, "IMX510_HCG_BASE12800_LEGAL")
        ok5, _ = validate_imx510_dual_base_iso_gain(12800, "HCG", 409600, 30.2)
        self.assertTrue(ok5)

        # Illegal combinations
        self.assertFalse(validate_imx510_dual_base_iso_gain(3200, "LCG", 3200, 0.0)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(800, "HCG", 800, 0.0)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(12800, "LCG", 12800, 0.0)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(800, "LCG", 12800, 24.0)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(800, "LCG", 800, 22.5)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(12800, "HCG", 6400, 0.0)[0])
        self.assertFalse(validate_imx510_dual_base_iso_gain(12800, "HCG", 12800, 31.0)[0])

    def test_08_helper_validate_cube_3dlut_17_and_33_and_faults(self) -> None:
        cube17 = build_synthetic_identity_cube_text(17)
        res17 = validate_cube_3dlut(cube_text=cube17)
        self.assertTrue(res17.valid)
        self.assertEqual(res17.grid_size, 17)
        self.assertEqual(res17.expected_entries, 17**3)
        self.assertEqual(res17.parsed_entries, 4913)
        self.assertEqual(res17.nan_count, 0)
        self.assertEqual(res17.inf_count, 0)
        self.assertEqual(res17.out_of_range_count, 0)

        cube33 = build_synthetic_identity_cube_text(33)
        res33 = validate_cube_3dlut(cube_text=cube33)
        self.assertTrue(res33.valid)
        self.assertEqual(res33.grid_size, 33)
        self.assertEqual(res33.expected_entries, 33**3)
        self.assertEqual(res33.parsed_entries, 35937)

        # NaN / Inf / out-of-range injection
        res_nan = validate_cube_3dlut(
            cube_text=cube17.replace("0.000000 0.000000 0.000000", "nan 0.000000 0.000000", 1)
        )
        self.assertFalse(res_nan.valid)
        self.assertEqual(res_nan.nan_count, 1)

        res_inf = validate_cube_3dlut(
            cube_text=cube17.replace("0.000000 0.000000 0.000000", "inf 0.000000 0.000000", 1)
        )
        self.assertFalse(res_inf.valid)
        self.assertEqual(res_inf.inf_count, 1)

        res_oor = validate_cube_3dlut(
            cube_text=cube17.replace("1.000000 1.000000 1.000000", "1.250000 -0.050000 1.000000", 1)
        )
        self.assertFalse(res_oor.valid)
        self.assertEqual(res_oor.out_of_range_count, 2)

        # Unsupported grid size (e.g. 65 or 9) & truncated entry count
        res_bad_size = validate_cube_3dlut(grid_size=65)
        self.assertFalse(res_bad_size.valid)
        res_trunc = validate_cube_3dlut(cube_text="LUT_3D_SIZE 17\n0.0 0.0 0.0\n")
        self.assertFalse(res_trunc.valid)

    # --- 3. Gate G49 Fault-Injection & Verification Tests ---

    def test_09_g49_nominal_passive_1v8_rx_passes(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.uart_1v8_passive_rx_safe)
        self.assertTrue(res.vmc_bncm1_isolation_safe)
        self.assertTrue(res.emmc_isp_1v8_passive_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_10_g49_blocks_3v3_and_5v0_uart_adapter_overvoltage(self) -> None:
        for mv in (1951.0, 3300.0, 5000.0):
            res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_io_voltage_mv=mv)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
            )
            self.assertFalse(res.uart_1v8_passive_rx_safe)

    def test_11_g49_blocks_undervoltage_1v8_uart_adapter(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_io_voltage_mv=1500.0)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )

    def test_12_g49_blocks_active_tx_line_connected(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(tx_line_connected=True)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )
        self.assertIn("tx_line_connected=True", res.errors[0])

    def test_13_g49_blocks_non_high_z_rx_line(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(rx_high_z_passive=False)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )

    def test_14_g49_blocks_backpower_leakage_while_camera_vcc_zero(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            camera_vcc_mv=0.0,
            backpower_leakage_ua=12.5,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )

    def test_15_g49_blocks_wrong_uart_device_baud_or_framing(self) -> None:
        self.assertEqual(
            verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_device="/dev/ttyS0").status,
            STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE,
        )
        self.assertEqual(
            verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_baud_rate=115200).status,
            STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE,
        )
        self.assertEqual(
            verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_framing="7E1").status,
            STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE,
        )

    def test_16_g49_blocks_simultaneous_vmc_bncm1_and_uart_tap(self) -> None:
        res1 = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            uart_tap_attached=True,
            vmc_bncm1_attached=True,
        )
        self.assertFalse(res1.valid)
        self.assertEqual(
            res1.status, STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION
        )
        self.assertFalse(res1.vmc_bncm1_isolation_safe)
        self.assertTrue(res1.vmc_bncm1_simultaneous_attach)

        res2 = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            uart_tap_attached=False,
            vmc_bncm1_attached=True,
            vmc_bncm1_simultaneous_attach=True,
        )
        self.assertFalse(res2.valid)
        self.assertEqual(
            res2.status, STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION
        )

    def test_17_g49_allows_vmc_bncm1_alone_without_uart_tap(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            uart_tap_attached=False,
            uart_io_voltage_mv=0.0,
            vmc_bncm1_attached=True,
            vmc_bncm1_simultaneous_attach=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.vmc_bncm1_isolation_safe)

    def test_18_g49_allows_active_8bit_1v8_emmc_isp_read_with_rst_low(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            offchip_emmc_isp_active=True,
            isp_vccq_mv=1800.0,
            isp_clk_mhz=24.0,
            isp_bus_width_bits=8,
            emmc_rst_n_held_low=True,
            isp_write_cmd24_cmd25_blocked=True,
            isp_mutation_bytes=0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.emmc_isp_1v8_passive_safe)
        self.assertTrue(any("Off-chip 8-bit eMMC ISP" in w for w in res.warnings))

    def test_19_g49_blocks_emmc_isp_without_rst_low(self) -> None:
        res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            offchip_emmc_isp_active=True,
            emmc_rst_n_held_low=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD
        )
        self.assertFalse(res.emmc_isp_1v8_passive_safe)

    def test_20_g49_blocks_emmc_isp_3v3_vccq_or_overclock(self) -> None:
        res_v = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            offchip_emmc_isp_active=True,
            emmc_rst_n_held_low=True,
            isp_vccq_mv=3300.0,
        )
        self.assertFalse(res_v.valid)
        self.assertEqual(
            res_v.status, STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD
        )

        res_clk = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            offchip_emmc_isp_active=True,
            emmc_rst_n_held_low=True,
            isp_clk_mhz=52.0,
        )
        self.assertFalse(res_clk.valid)
        self.assertEqual(
            res_clk.status, STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD
        )

    def test_21_g49_blocks_emmc_isp_cmd24_cmd25_unblocked_or_wrong_width_or_mutation(self) -> None:
        for kw in (
            {"isp_write_cmd24_cmd25_blocked": False},
            {"isp_bus_width_bits": 1},
            {"isp_mutation_bytes": 4096},
        ):
            res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD
            )

    def test_22_g49_blocks_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        res_nan = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            uart_io_voltage_mv=float("nan"),
        )
        self.assertFalse(res_nan.valid)
        self.assertEqual(res_nan.status, STATUS_BLOCKED_G49_TELEMETRY_INVALID)

        res_bad_str = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(uart_device="  ")
        self.assertFalse(res_bad_str.valid)
        self.assertEqual(res_bad_str.status, STATUS_BLOCKED_G49_TELEMETRY_INVALID)

        res_wr = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(res_wr.valid)
        self.assertEqual(res_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 4. Gate G50 Fault-Injection & Verification Tests ---

    def test_23_g50_nominal_imx510_base800_and_base12800_pass(self) -> None:
        cube17 = build_synthetic_identity_cube_text(17)
        res800 = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=800,
            conversion_gain_mode="LCG",
            target_iso=800,
            analog_gain_db=0.0,
            cube_text=cube17,
        )
        self.assertTrue(res800.valid)
        self.assertEqual(res800.status, STATUS_SAFE)
        self.assertTrue(res800.sensor_cal_nvs_lock_safe)
        self.assertTrue(res800.dual_base_iso_gain_safe)
        self.assertTrue(res800.cube_3dlut_and_non_double_bake_safe)
        self.assertTrue(res800.mlut_double_bake_blocked)
        self.assertEqual(res800.cube_entries_verified, 17**3)

        res12800 = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=12800,
            conversion_gain_mode="HCG",
            target_iso=25600,
            analog_gain_db=6.0,
            cube_grid_size=33,
        )
        self.assertTrue(res12800.valid)
        self.assertEqual(res12800.cube_grid_size, 33)
        self.assertEqual(res12800.cube_entries_verified, 33**3)

    def test_24_g50_blocks_psd_bin_sha256_mismatch(self) -> None:
        res = verify_imx510_sensor_cal_and_mlut_guard(psd_bin_sha256="a" * 64)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )
        self.assertFalse(res.sensor_cal_nvs_lock_safe)

    def test_25_g50_blocks_defdet_bin_and_lensfile_sha256_mismatch(self) -> None:
        r_def = verify_imx510_sensor_cal_and_mlut_guard(defdet_bin_sha256="b" * 64)
        self.assertFalse(r_def.valid)
        self.assertEqual(
            r_def.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )

        r_lens = verify_imx510_sensor_cal_and_mlut_guard(lensfile_bin_sha256="c" * 64)
        self.assertFalse(r_lens.valid)
        self.assertEqual(
            r_lens.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )

    def test_26_g50_blocks_sensor_cal_mutation_or_write_request(self) -> None:
        r_mut = verify_imx510_sensor_cal_and_mlut_guard(sensor_cal_mutation_bytes=128)
        self.assertFalse(r_mut.valid)
        self.assertEqual(
            r_mut.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )

        r_req = verify_imx510_sensor_cal_and_mlut_guard(sensor_cal_writes_requested=1)
        self.assertFalse(r_req.valid)
        self.assertEqual(
            r_req.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )

    def test_27_g50_blocks_p2_or_p18_ro_unlocked_and_cross_body_import(self) -> None:
        for kw in (
            {"p2_setting_ro_locked": False},
            {"p18_lens_ro_locked": False},
            {"same_body_sensor_cal_sha256_match": False},
            {"cross_body_or_fx6_cal_import_attempted": True},
        ):
            res = verify_imx510_sensor_cal_and_mlut_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
            )

    def test_28_g50_blocks_imx510_illegal_base_iso_or_gain_mode_mismatch(self) -> None:
        # FX6 base ISO 3200 is invalid on FX3 IMX510 (800 / 12800)
        r_fx6 = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=3200, conversion_gain_mode="HCG", target_iso=3200, analog_gain_db=0.0
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(
            r_fx6.status, STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS
        )
        self.assertFalse(r_fx6.dual_base_iso_gain_safe)

        # Base 800 with HCG
        r_mix = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=800, conversion_gain_mode="HCG", target_iso=800, analog_gain_db=0.0
        )
        self.assertFalse(r_mix.valid)
        self.assertEqual(
            r_mix.status, STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS
        )

    def test_29_g50_blocks_imx510_analog_gain_or_target_iso_out_of_bounds(self) -> None:
        # LCG exceeded (> 22 dB / > ISO 10000)
        r_lcg = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=800, conversion_gain_mode="LCG", target_iso=16000, analog_gain_db=26.0
        )
        self.assertFalse(r_lcg.valid)
        self.assertEqual(
            r_lcg.status, STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS
        )

        # HCG exceeded (> 30.2 dB or > 409600)
        r_hcg = verify_imx510_sensor_cal_and_mlut_guard(
            base_iso=12800,
            conversion_gain_mode="HCG",
            target_iso=512000,
            analog_gain_db=32.0,
        )
        self.assertFalse(r_hcg.valid)
        self.assertEqual(
            r_hcg.status, STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS
        )

    def test_30_g50_blocks_nan_inf_or_out_of_range_cube_3dlut(self) -> None:
        cube17 = build_synthetic_identity_cube_text(17)
        for bad_cube in (
            cube17.replace("0.000000 0.000000 0.000000", "NaN 0.0 0.0", 1),
            cube17.replace("0.000000 0.000000 0.000000", "-inf 0.0 0.0", 1),
            cube17.replace("1.000000 1.000000 1.000000", "1.5 0.0 0.0", 1),
            "LUT_1D_SIZE 256\n0.0 0.0 0.0\n",
        ):
            res = verify_imx510_sensor_cal_and_mlut_guard(cube_text=bad_cube)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE
            )
            self.assertFalse(res.cube_3dlut_and_non_double_bake_safe)

    def test_31_g50_blocks_mlut_double_bake_into_slog3_xavc_master(self) -> None:
        res_burn = verify_imx510_sensor_cal_and_mlut_guard(
            recording_color_space="S-Log3/S-Gamut3.Cine",
            mlut_monitoring_enabled=True,
            mlut_burn_in_to_xavc_master=True,
            mlut_burn_in_authorized=False,
        )
        self.assertFalse(res_burn.valid)
        self.assertEqual(
            res_burn.status, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE
        )
        self.assertFalse(res_burn.mlut_double_bake_blocked)

        res_dbl = verify_imx510_sensor_cal_and_mlut_guard(mlut_double_bake_detected=True)
        self.assertFalse(res_dbl.valid)
        self.assertEqual(
            res_dbl.status, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE
        )

    def test_32_g50_allows_explicit_burn_in_override_when_no_double_bake(self) -> None:
        res = verify_imx510_sensor_cal_and_mlut_guard(
            recording_color_space="Rec.709",
            mlut_monitoring_enabled=False,
            mlut_burn_in_to_xavc_master=True,
            mlut_burn_in_authorized=True,
            mlut_double_bake_detected=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.mlut_double_bake_blocked)
        self.assertTrue(any("mlut_burn_in_authorized=True" in w for w in res.warnings))

    def test_33_g50_blocks_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        r_bad_sha = verify_imx510_sensor_cal_and_mlut_guard(psd_bin_sha256="not-hex")
        self.assertFalse(r_bad_sha.valid)
        self.assertEqual(r_bad_sha.status, STATUS_BLOCKED_G50_TELEMETRY_INVALID)

        r_nan_gain = verify_imx510_sensor_cal_and_mlut_guard(analog_gain_db=float("inf"))
        self.assertFalse(r_nan_gain.valid)
        self.assertEqual(r_nan_gain.status, STATUS_BLOCKED_G50_TELEMETRY_INVALID)

        r_wr = verify_imx510_sensor_cal_and_mlut_guard(request_persistent_emmc_writes=True)
        self.assertFalse(r_wr.valid)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 5. Gate Evaluators G49 & G50 ---

    def test_34_evaluate_g49_and_g50_clean_room_and_default_modes(self) -> None:
        v49_c, r49_c = evaluate_g49_uart1v8_isp(force_clean_room=True)
        self.assertTrue(v49_c.passed)
        self.assertEqual(v49_c.gate_id, G49_GATE_ID)
        self.assertEqual(v49_c.gate_code, G49_GATE_CODE)
        self.assertEqual(v49_c.status, STATUS_VERIFIED_G49)
        self.assertEqual(r49_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(r49_c.persistent_emmc_writes_authorized)

        v50_c, r50_c = evaluate_g50_imx510_sensor_cal(force_clean_room=True)
        self.assertTrue(v50_c.passed)
        self.assertEqual(v50_c.gate_id, G50_GATE_ID)
        self.assertEqual(v50_c.gate_code, G50_GATE_CODE)
        self.assertEqual(v50_c.status, STATUS_VERIFIED_G50)
        self.assertEqual(r50_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(r50_c.persistent_emmc_writes_authorized)

        # Auto mode (O_RDONLY when local donors present, else clean-room)
        v49_a, r49_a = evaluate_g49_uart1v8_isp(repo_root=DEFAULT_REPO_ROOT)
        v50_a, r50_a = evaluate_g50_imx510_sensor_cal(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(v49_a.passed)
        self.assertTrue(v50_a.passed)
        self.assertIn(r49_a.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertIn(r50_a.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_35_evaluate_g49_and_g50_propagate_guard_faults(self) -> None:
        v49, r49 = evaluate_g49_uart1v8_isp(
            force_clean_room=True,
            uart1v8_isp_kwargs={"uart_io_voltage_mv": 3300.0},
        )
        self.assertFalse(v49.passed)
        self.assertFalse(r49.valid)
        self.assertEqual(
            v49.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )

        v50, r50 = evaluate_g50_imx510_sensor_cal(
            force_clean_room=True,
            imx510_sensor_cal_kwargs={"mlut_burn_in_to_xavc_master": True},
        )
        self.assertFalse(v50.passed)
        self.assertFalse(r50.valid)
        self.assertEqual(
            v50.status, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE
        )

    # --- 6. Unified 50-Gate Master Preflight Tests ---

    def test_36_50gate_preflight_offline_default_47_of_50(self) -> None:
        rep = evaluate_50gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.schema, REALHW_UART1V8_IMX510_50GATE_SCHEMA)
        self.assertEqual(rep.version, REALHW_UART1V8_IMX510_50GATE_VERSION)
        self.assertEqual(len(rep.gates), 50)
        self.assertEqual(rep.summary["total_gates"], 50)
        self.assertEqual(rep.summary["verified_gates"], 47)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g48_verified"], 36)
        self.assertEqual(rep.summary["g49_to_g50_verified"], 2)
        self.assertTrue(rep.g49_to_g50_all_passed)
        self.assertTrue(rep.g13_to_g50_all_passed)
        self.assertTrue(rep.offline_47_gates_verified)
        self.assertFalse(rep.all_50_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_47_OF_50_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )
        self.assertEqual(rep.gates[48]["gate_id"], G49_GATE_ID)
        self.assertEqual(rep.gates[49]["gate_id"], G50_GATE_ID)

    def test_37_50gate_preflight_dry_run_50_of_50_hard_locked_no_writes(self) -> None:
        rep = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 50)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_50_gates_verified)
        self.assertTrue(rep.offline_47_gates_verified)
        self.assertTrue(rep.g13_to_g50_all_passed)
        self.assertTrue(rep.g49_to_g50_all_passed)
        # Hard redlines stay False even at 50/50 dry-run
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_50_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertIs(evaluate_50_master_safety_gates, evaluate_50gate_preflight)

    def test_38_50gate_preflight_propagates_g49_failure(self) -> None:
        rep = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            uart1v8_isp_kwargs={
                "uart_tap_attached": True,
                "vmc_bncm1_attached": True,
            },
        )
        self.assertFalse(rep.g49_to_g50_all_passed)
        self.assertFalse(rep.g13_to_g50_all_passed)
        self.assertFalse(rep.offline_47_gates_verified)
        self.assertFalse(rep.all_50_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION)

    def test_39_50gate_preflight_propagates_g50_failure(self) -> None:
        rep = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            imx510_sensor_cal_kwargs={
                "cross_body_or_fx6_cal_import_attempted": True,
            },
        )
        self.assertFalse(rep.g49_to_g50_all_passed)
        self.assertFalse(rep.g13_to_g50_all_passed)
        self.assertFalse(rep.offline_47_gates_verified)
        self.assertFalse(rep.all_50_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )

    def test_40_50gate_preflight_propagates_g47_g48_and_emmc_write_redline(self) -> None:
        rep_g47 = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            pnflasha_mtdro_kwargs={"mtd_device_node": "/dev/mtd0"},
        )
        self.assertFalse(rep_g47.g13_to_g50_all_passed)
        self.assertFalse(rep_g47.offline_47_gates_verified)
        self.assertEqual(rep_g47.status, STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE)

        rep_g48 = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            rfnvs_fan_power_kwargs={"fan_mode": "ALWAYS_OFF", "sensor_temp_c": 70.0},
        )
        self.assertFalse(rep_g48.g13_to_g50_all_passed)
        self.assertFalse(rep_g48.offline_47_gates_verified)
        self.assertEqual(
            rep_g48.status, STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION
        )

        rep_wr = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_wr.offline_47_gates_verified)
        self.assertFalse(rep_wr.all_50_gates_verified)
        self.assertFalse(rep_wr.h0_h1_trial_entry_allowed)
        self.assertEqual(rep_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_41_50gate_json_is_strictly_serializable_without_raw_firmware_bytes(self) -> None:
        rep = evaluate_50gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        payload = json.dumps(rep.to_dict(), ensure_ascii=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["summary"]["total_gates"], 50)
        self.assertEqual(parsed["summary"]["verified_gates"], 47)
        self.assertEqual(
            parsed["master_48_report"]["schema"],
            REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA,
        )
        self.assertNotIn("b'\\x7fELF", payload)

    def test_42_backward_compatibility_48gate_preflight_unchanged(self) -> None:
        rep48 = evaluate_48gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(rep48.gates), 48)
        self.assertEqual(rep48.summary["verified_gates"], 45)
        self.assertTrue(rep48.offline_45_gates_verified)

    # --- 7. CLI Entrypoint Tests ---

    def test_43_cli_verify_g49_uart1v8_isp_summary_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g49-uart1v8-isp", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(G49_GATE_ID, out)
        self.assertIn("4608008N1@1800mV", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = package_cli_main(["verify-g49-uart1v8-isp", "--clean-room", "--json"])
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G49)

    def test_44_cli_verify_g50_imx510_sensor_cal_summary_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g50-imx510-sensor-cal", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(G50_GATE_ID, out)
        self.assertIn("800/LCG", out)
        self.assertIn("mlut_non_double_bake=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = package_cli_main(["verify-g50-imx510-sensor-cal", "--clean-room", "--json"])
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G50)

    def test_45_cli_verify_50_gates_offline_and_dry_run_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-50-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=47/50", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_dr = io.StringIO()
        with contextlib.redirect_stdout(buf_dr):
            rc_dr = package_cli_main(
                ["verify-50-gates", "--clean-room", "--dry-run-simulated-backup"]
            )
        self.assertEqual(rc_dr, 0)
        out_dr = buf_dr.getvalue()
        self.assertIn("verified=50/50", out_dr)
        self.assertIn("all_50_gates_verified=True", out_dr)
        self.assertIn("overall_ready_for_hardware_attach=False", out_dr)
        self.assertIn("persistent_emmc_writes_authorized=False", out_dr)

    def test_46_cli_verify_50_gates_json_and_module_cli_parity(self) -> None:
        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(
                ["verify-50-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_pkg, 0)
        pkg_data = json.loads(buf_pkg.getvalue())
        self.assertEqual(pkg_data["summary"]["verified_gates"], 50)
        self.assertEqual(pkg_data["schema"], REALHW_UART1V8_IMX510_50GATE_SCHEMA)

        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_mod, 0)
        mod_data = json.loads(buf_mod.getvalue())
        self.assertEqual(mod_data["summary"]["verified_gates"], 50)
        self.assertFalse(mod_data["overall_ready_for_hardware_attach"])

    def test_47_cli_failure_exit_codes_propagate_cleanly(self) -> None:
        failing_rep = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            uart1v8_isp_kwargs={"uart_io_voltage_mv": 5000.0},
        )
        with patch(
            "fx3_safety.__main__.evaluate_50gate_preflight", return_value=failing_rep
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(["verify-50-gates", "--clean-room"])
            self.assertEqual(rc, 1)
            self.assertIn(STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE, buf.getvalue())

    def test_48_env_var_force_clean_room_controls_dual_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_50gate_preflight(DEFAULT_REPO_ROOT)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.clean_room_forced)
            self.assertTrue(rep.offline_47_gates_verified)


if __name__ == "__main__":
    unittest.main()
