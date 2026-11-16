#!/usr/bin/env python3
"""Phase 33 Test Suite — Unified `outputs/fx3-vm/` Full-Board Co-Emulation Orchestrator & CLI.

Exercises 24 unit, integration, and CLI tests across BOTH Local Donor (`O_RDONLY`)
and `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic modes, strictly offline and hardware-free.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import dual_ap_cp_ivshmem_bridge as p24  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402
import soft_gpe_and_bt_rom_emulator as p29  # noqa: E402


_REPORT_CACHE: dict = {}


def _get_default_report() -> dict:
    key = ("default", p24.is_forced_clean_room())
    if key not in _REPORT_CACHE:
        _REPORT_CACHE[key] = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(), env=os.environ)
    return _REPORT_CACHE[key]


def _get_clean_room_report() -> dict:
    key = ("clean_room", True)
    if key not in _REPORT_CACHE:
        _REPORT_CACHE[key] = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True),
            env=os.environ,
        )
    return _REPORT_CACHE[key]


class TestFullBoardCoEmulationPipeline(unittest.TestCase):
    """Verify full 3-stage co-emulation pipeline across Default and Clean-Room modes."""

    default_report: dict
    clean_room_report: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_report = _get_default_report()
        cls.clean_room_report = _get_clean_room_report()

    def test_01_full_board_default_mode_passes_all_three_stages(self) -> None:
        rep = self.default_report
        self.assertEqual(rep["schema"], suite.PHASE_33_SCHEMA)
        self.assertEqual(rep["version"], suite.PHASE_33_VERSION)
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])

        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_02_stage1_ap_vm_manifest_and_bt_baseline(self) -> None:
        s1 = self.default_report["stage1_coldboot_and_bt"]
        m = s1["ap_vm_manifest"]
        self.assertTrue(m["manifest_present"])
        self.assertTrue(m["run_probe_present"])
        self.assertEqual(m["schema"], "fx3-mac-vm-minimal-research-v1")
        self.assertEqual(m["memory_mib"], 2048)
        self.assertEqual(m["disabled_initcalls_count"], 7)
        self.assertEqual(m["model_env"], {"FX3_VM_ESRAM_RAM": "1", "FX3_VM_HIGH_DDR": "1"})
        self.assertEqual(tuple(m["profiles"]), ("app-loader", "minimal-linux"))

        self.assertTrue(s1["bt_donor_inspection"]["all_markers_satisfied"])
        bt = s1["active_bt_result"]
        self.assertTrue(bt["passed"])
        self.assertTrue(bt["bsa_ready"])
        self.assertEqual(bt["bd_addr"], "58:36:57:00:29:01")
        self.assertEqual(bt["final_baudrate"], 3000000)
        self.assertEqual(bt["degraded_state"], "BSA_HEALTHY_READY")

        matrix = s1["bt_containment_matrix"]
        self.assertEqual(set(matrix.keys()), set(p29.ALL_BT_OPERATING_MODES))
        for mode_name, res in matrix.items():
            self.assertTrue(res["passed"], msg=f"BT matrix mode {mode_name} failed")
            self.assertFalse(res["system_error_abort"])
            self.assertEqual(res["wdt_resets"], 0)
            self.assertTrue(res["shooting_unaffected"])
            self.assertTrue(res["recording_unaffected"])

    def test_03_stage2_dual_isa_p11_isolation_and_cp_immutability(self) -> None:
        s2 = self.default_report["stage2_dual_isa_cp_shooting"]
        self.assertEqual(s2["cp_mutation_bytes"], 0)
        self.assertTrue(s2["cp_immutability"]["immutable"])
        self.assertEqual(
            s2["cp_immutability"]["sha256_before"],
            s2["cp_immutability"]["sha256_after"],
        )

        receipts = s2["receipts"]
        rtc_r, handle_r = receipts[0], receipts[1]
        self.assertEqual(rtc_r["queue_id"], "0x92d2091c")
        self.assertTrue(rtc_r["intercepted_by_p11"])
        self.assertFalse(rtc_r["tx_enqueued"])
        self.assertFalse(rtc_r["cp_executed"])
        self.assertEqual(rtc_r["rx_completion_hex"], "0300")

        self.assertEqual(handle_r["queue_id"], "0x91db059b")
        self.assertTrue(handle_r["intercepted_by_p11"])
        self.assertFalse(handle_r["tx_enqueued"])
        self.assertFalse(handle_r["cp_executed"])

        tel = s2["telemetry"]
        self.assertEqual(tel["cp_verified_0x92840747"], 1)
        self.assertEqual(tel["cp_verified_load_base"], 1)
        self.assertEqual(tel["p11_local_rtc_count"], 1)
        self.assertEqual(tel["p11_local_handle_count"], 1)

    def test_04_stage2_cine_ei_lut_dma_and_ibis_receipts(self) -> None:
        s2 = self.default_report["stage2_dual_isa_cp_shooting"]
        self.assertEqual(s2["cine_ei_iso"], 800)
        self.assertEqual(s2["dual_native_iso_bases"], [800, 12800])
        self.assertEqual(s2["lut_mode"], "8bit")
        self.assertEqual(s2["lut_bytes"], p24.LUT_8BIT_ALIGNED_BYTES)
        self.assertTrue(s2["ibis_center_lock_energized"])

        # Receipts 2..7: 0x0416, 0x0169, 0x016a, 0x0165, 0x0166, 0x0400
        cp_receipts = s2["receipts"][2:]
        self.assertEqual(len(cp_receipts), 6)
        expected_ops = ["0x8416", "0x8169", "0x816a", "0x8165", "0x8166", "0x8400"]
        self.assertEqual([r["rx_completion_opcode"] for r in cp_receipts], expected_ops)
        self.assertEqual(cp_receipts[3]["lut_dma_acked_bytes"], p24.LUT_8BIT_ALIGNED_BYTES)
        for r in cp_receipts:
            self.assertTrue(r["tx_enqueued"])
            self.assertTrue(r["ap_doorbell_to_cp"])
            self.assertTrue(r["cp_executed"])
            self.assertTrue(r["cp_doorbell_to_ap"])
            self.assertTrue(r["ibis_center_lock_energized"])
            self.assertEqual(r["cp_mutation_bytes"], 0)

        tel = s2["telemetry"]
        self.assertEqual(tel["cp_doorbell_irq_count"], 6)
        self.assertEqual(tel["ap_doorbell_irq_count"], 6)
        self.assertEqual(tel["lut_dma_ack_count"], 1)
        self.assertEqual(tel["ibis_steadyshot_mode"], p24.VALID_STEADYSHOT_MODES["Active"])

    def test_05_stage3_soft_gpe_hud_big6_and_hosdap02_ramfb(self) -> None:
        s3 = self.default_report["stage3_soft_gpe_hud_ramfb"]
        self.assertTrue(s3["fx6_px_rb_parity_ok"])
        self.assertEqual(s3["amber_accent_px_hex"], "0xfff08018")
        self.assertEqual(s3["bt_badge_px_hex"], "0xff28c878")
        self.assertTrue(s3["hosdap02_header_hex"].startswith(p29.HOSDAP02_MAGIC.hex()))
        self.assertGreaterEqual(s3["decoded_sprites_composited"], 2)

        ramfb = s3["ramfb_scanout"]
        self.assertEqual(ramfb["hosdap02_magic"], "HOSDAP02")
        self.assertEqual(ramfb["gpe0_phys"], "0x41e001000")
        self.assertEqual(ramfb["ramfb_phys"], "0x41e100000")
        self.assertEqual(ramfb["width"], 1024)
        self.assertEqual(ramfb["height"], 540)
        self.assertEqual(ramfb["nonzero_gpe0_pixels"], p29.GPE0_PIXEL_COUNT)
        self.assertEqual(ramfb["ramfb_bytes"], p29.GPE0_BYTES)
        self.assertGreaterEqual(ramfb["unique_gpe0_colors"], 8)

    def test_06_clean_room_forced_pipeline_passes_with_synthetic_fixtures(self) -> None:
        rep = self.clean_room_report
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["clean_room_forced"])
        self.assertEqual(
            rep["stage1_coldboot_and_bt"]["bt_donor_inspection"]["source_mode"],
            "CLEAN_ROOM_SYNTHETIC",
        )
        self.assertEqual(
            rep["stage2_dual_isa_cp_shooting"]["source_mode"],
            "CLEAN_ROOM_SYNTHETIC",
        )
        self.assertEqual(rep["stage2_dual_isa_cp_shooting"]["cp_mutation_bytes"], 0)
        self.assertEqual(
            rep["stage3_soft_gpe_hud_ramfb"]["source_mode"],
            "CLEAN_ROOM_SYNTHETIC",
        )
        self.assertEqual(rep["stage3_soft_gpe_hud_ramfb"]["total_sprites"], 5)
        self.assertEqual(rep["stage3_soft_gpe_hud_ramfb"]["nine_patch_sprites"], 1)

    def test_07_local_donor_mode_when_present_or_clean_room_parity(self) -> None:
        if p24.is_forced_clean_room():
            self.assertTrue(self.default_report["clean_room_forced"])
            self.assertEqual(
                self.default_report["stage2_dual_isa_cp_shooting"]["source_mode"],
                "CLEAN_ROOM_SYNTHETIC",
            )
            return

        p24_donors = p24.resolve_phase24_donor_paths()
        p29_donors = p29.resolve_phase29_donor_paths()
        if not (all(p.is_file() for p in p24_donors.values()) and all(p.is_file() for p in p29_donors.values())):
            self.skipTest("Optional local Sony BYOF donor binaries absent on this host")

        self.assertFalse(self.default_report["clean_room_forced"])
        s2 = self.default_report["stage2_dual_isa_cp_shooting"]
        self.assertEqual(s2["source_mode"], "LOCAL_DONOR_READONLY")
        self.assertEqual(s2["cp_inspection"]["byte_length"], p24.EXPECTED_FX3_CPAPP_BYTES)
        self.assertEqual(s2["cp_inspection"]["sha256"], p24.EXPECTED_FX3_CPAPP_SHA256)
        s3 = self.default_report["stage3_soft_gpe_hud_ramfb"]
        self.assertEqual(s3["source_mode"], "LOCAL_DONOR_RDONLY")
        self.assertEqual(s3["total_sprites"], 1610)
        self.assertEqual(s3["nine_patch_sprites"], 22)

    def test_08_qemu_topology_summary_parity(self) -> None:
        topo = self.default_report["qemu_topology_summary"]
        self.assertIn("ivshmem-server", topo["ivshmem_server_cmd"][0])
        self.assertEqual(topo["peer0_ap_device"], "ivshmem-doorbell")
        self.assertEqual(topo["peer1_cp_device"], "ivshmem-flat")
        self.assertEqual(topo["cp_load_base"], "0x00108000")
        self.assertTrue(topo["cp_read_only"])

    def test_09_audit_digest_sha256_is_valid_and_reproducible(self) -> None:
        rep = dict(self.clean_room_report)
        recorded = rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

        # Stage 1 + Stage 2 determinism check across two independent clean-room runs
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s1_a = suite.run_stage1_bt_and_coldboot(cfg)
        s1_b = suite.run_stage1_bt_and_coldboot(cfg)
        self.assertEqual(s1_a, s1_b)
        s2_a = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        s2_b = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertEqual(s2_a, s2_b)


class TestCoEmulationConfigurationAndFaultContainment(unittest.TestCase):
    """Verify BT fault containment isolation, Cine EI/LUT/IBIS matrix, and error handling."""

    def test_10_config_validation_rejects_invalid_bt_iso_lut_ibis(self) -> None:
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(bt_mode="INVALID_BT").validate()
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(cine_ei_iso=3200).validate()
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(lut_mode="32bit").validate()
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(ibis_mode="Turbo").validate()

    def test_11_bt_p12_uart_timeout_0x0bb9_never_blocks_stage2_shooting(self) -> None:
        cfg = suite.CoEmulationConfig(
            bt_mode=p29.BT_MODE_UART_TIMEOUT,
            cine_ei_iso=12800,
            lut_mode="8bit",
            ibis_mode="Standard",
            include_bt_containment_matrix=False,
            force_clean_room=True,
        )
        s1 = suite.run_stage1_bt_and_coldboot(cfg)
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s1["all_checks_passed"])
        self.assertEqual(s1["active_bt_result"]["hal_error_code"], 0x0BB9)
        self.assertEqual(s1["active_bt_result"]["degraded_state"], "BT_DEGRADED_DISABLED")
        self.assertTrue(s1["active_bt_result"]["shooting_unaffected"])
        self.assertTrue(s2["all_checks_passed"])
        self.assertEqual(s2["cp_mutation_bytes"], 0)

    def test_12_bt_patchram_nack_00342260_latch_never_blocks_stage2_shooting(self) -> None:
        cfg = suite.CoEmulationConfig(
            bt_mode=p29.BT_MODE_PATCHRAM_NACK,
            include_bt_containment_matrix=False,
            force_clean_room=True,
        )
        s1 = suite.run_stage1_bt_and_coldboot(cfg)
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s1["all_checks_passed"])
        self.assertEqual(s1["active_bt_result"]["notice_id"], "00342260")
        self.assertEqual(s1["active_bt_result"]["degraded_state"], "NOTICE_00342260_AIRPLANE_LATCHED")
        self.assertTrue(s1["active_bt_result"]["airplane_latched"])
        self.assertEqual(s1["active_bt_result"]["wdt_resets"], 0)
        self.assertTrue(s2["all_checks_passed"])
        self.assertEqual(s2["cp_mutation_bytes"], 0)

    def test_13_bt_airplane_shadow_bk4_gate_never_blocks_stage2_shooting(self) -> None:
        cfg = suite.CoEmulationConfig(
            bt_mode=p29.BT_MODE_AIRPLANE_GATED,
            bkid_0x019e0012=0x00,
            bkid_0x01a20002=0x00,
            include_bt_containment_matrix=False,
            force_clean_room=True,
        )
        s1 = suite.run_stage1_bt_and_coldboot(cfg)
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s1["all_checks_passed"])
        self.assertEqual(s1["active_bt_result"]["tx_packets"], 0)
        self.assertEqual(s1["active_bt_result"]["tx_bytes"], 0)
        self.assertTrue(s1["active_bt_result"]["airplane_latched"])
        self.assertTrue(s2["all_checks_passed"])
        self.assertEqual(s2["cp_mutation_bytes"], 0)

    def test_14_stage3_hud_reflects_degraded_bt_and_cine_ei_12800_off_states(self) -> None:
        cfg = suite.CoEmulationConfig(
            bt_mode=p29.BT_MODE_PATCHRAM_NACK,
            cine_ei_iso=12800,
            lut_mode="off",
            ibis_mode="Off",
            include_bt_containment_matrix=False,
            force_clean_room=True,
        )
        s1 = suite.run_stage1_bt_and_coldboot(cfg)
        s3 = suite.run_stage3_soft_gpe_hud_composite(
            cfg,
            bt_result=s1,
            cp_result={"all_checks_passed": True},
        )
        self.assertTrue(s3["all_checks_passed"])
        self.assertEqual(s3["bt_badge_px_hex"], "0xffb83c46")
        self.assertEqual(s3["amber_accent_px_hex"], "0xfff08018")

    def test_15_stage2_cine_ei_12800_and_16bit_33cube_lut_dma(self) -> None:
        cfg = suite.CoEmulationConfig(
            cine_ei_iso=12800,
            lut_mode="16bit",
            ibis_mode="Active",
            force_clean_room=True,
        )
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s2["all_checks_passed"])
        self.assertEqual(s2["cine_ei_iso"], 12800)
        self.assertEqual(s2["lut_bytes"], p24.LUT_16BIT_BYTES)
        self.assertEqual(s2["telemetry"]["lut_dma_last_bytes"], p24.LUT_16BIT_BYTES)
        self.assertEqual(s2["telemetry"]["lut_dma_ack_count"], 1)
        self.assertEqual(s2["cp_mutation_bytes"], 0)

    def test_16_stage2_lut_off_mode_disables_lut_without_dma(self) -> None:
        cfg = suite.CoEmulationConfig(
            lut_mode="off",
            force_clean_room=True,
        )
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s2["all_checks_passed"])
        self.assertFalse(s2["lut_enabled"])
        self.assertEqual(s2["lut_bytes"], 0)
        self.assertEqual(s2["telemetry"]["lut_dma_ack_count"], 0)
        self.assertEqual(s2["telemetry"]["cp_doorbell_irq_count"], 5)
        self.assertEqual(s2["receipts"][-2]["rx_completion_opcode"], "0x8166")

    def test_17_stage2_ibis_off_standard_active_keep_center_lock_energized(self) -> None:
        for mode_name, mode_id in p24.VALID_STEADYSHOT_MODES.items():
            cfg = suite.CoEmulationConfig(
                ibis_mode=mode_name,
                lut_mode="off",
                force_clean_room=True,
            )
            s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
            self.assertTrue(s2["all_checks_passed"], msg=f"IBIS {mode_name} failed")
            self.assertTrue(s2["ibis_center_lock_energized"])
            self.assertEqual(s2["ibis_mode_id"], mode_id)
            self.assertEqual(s2["telemetry"]["ibis_steadyshot_mode"], mode_id)

    def test_18_stage2_p11_rtc_invalid_returns_0301_without_cp_leak(self) -> None:
        cfg = suite.CoEmulationConfig(
            rtc_valid=False,
            lut_mode="off",
            force_clean_room=True,
        )
        s2 = suite.run_stage2_dual_isa_shooting_cycle(cfg)
        self.assertTrue(s2["all_checks_passed"])
        rtc_r = s2["receipts"][0]
        self.assertTrue(rtc_r["intercepted_by_p11"])
        self.assertFalse(rtc_r["cp_executed"])
        self.assertEqual(rtc_r["rx_completion_hex"], "0301")

    def test_19_read_file_readonly_and_missing_manifest_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = suite.inspect_ap_vm_manifest(Path(tmpdir))
            self.assertFalse(missing.manifest_present)
            self.assertFalse(missing.run_probe_present)
            self.assertEqual(missing.memory_mib, 0)

        manifest_bytes = suite.read_file_readonly_bytes(FX3_VM_DIR / "manifest.json")
        parsed = json.loads(manifest_bytes.decode("utf-8"))
        self.assertEqual(parsed["memory_mib"], 2048)


class TestCliAndSourceHygiene(unittest.TestCase):
    """Verify CLI JSON determinism, flags, and strict clean-room / O_RDONLY hygiene."""

    def test_20_cli_default_and_clean_room_emit_deterministic_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        expected = json.dumps(_get_clean_room_report(), indent=2) + "\n"
        self.assertEqual(buf.getvalue(), expected)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], suite.PHASE_33_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertTrue(parsed["clean_room_forced"])

    def test_21_cli_subprocess_clean_room_invocation(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--bt-mode",
                p29.BT_MODE_UART_TIMEOUT,
                "--cine-ei-iso",
                "12800",
                "--ibis-mode",
                "Standard",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["stage1_coldboot_and_bt"]["active_bt_mode"], p29.BT_MODE_UART_TIMEOUT)
        self.assertEqual(payload["stage2_dual_isa_cp_shooting"]["cine_ei_iso"], 12800)
        self.assertEqual(payload["stage2_dual_isa_cp_shooting"]["ibis_mode"], "Standard")
        self.assertEqual(payload["redlines"]["cp_mutation_bytes"], 0)

    def test_22_cli_topology_and_invalid_arg_handling(self) -> None:
        buf_topo = io.StringIO()
        with contextlib.redirect_stdout(buf_topo):
            rc_topo = suite.main(["--topology"])
        self.assertEqual(rc_topo, 0)
        topo = json.loads(buf_topo.getvalue())
        self.assertEqual(topo["schema"], p24.PHASE_24_SCHEMA)
        self.assertEqual(topo["peer1_cp_cetus"]["cp_mutation_bytes"], 0)

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                suite.main(["--bt-mode", "NO_SUCH_MODE"])
            self.assertNotEqual(ctx.exception.code, 0)

    def test_23_cli_summary_rtc_invalid_and_lut_off_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(
                ["--clean-room", "--summary", "--lut-mode", "off", "--rtc-invalid", "--ibis-mode", "Off"]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn("lut=off(0B)", out)
        self.assertIn("ibis=Off", out)
        self.assertIn("cp_mut=0", out)

    def test_24_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        suite_src = (FX3_VM_DIR / "fx3_vm_coemulation_suite.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", suite_src)
        self.assertNotIn("os.O_WRONLY", suite_src)
        self.assertNotIn("os.O_RDWR", suite_src)
        self.assertNotIn(forbidden_port, suite_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", suite_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", suite_src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", suite_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", suite_src)


if __name__ == "__main__":
    unittest.main()
