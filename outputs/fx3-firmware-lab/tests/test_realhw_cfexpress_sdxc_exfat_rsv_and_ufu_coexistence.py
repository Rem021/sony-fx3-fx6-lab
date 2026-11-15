"""Phase 159 Dual-Mode Unit Tests (48 tests): Real-Hardware Dual-Slot
`CFexpress Type A (PCIe Gen3 x1 NVMe)` + `SDXC UHS-II (V90/V60/V30)` Media Bridge,
Card-Door Interrupt Flush & `.RSV` Clip Salvage, and Official Sony `BODYDATA.DAT`
(`\\x89UFU\\r\\n\\x1a\\n`, `811,876,768 B`) Updater Coexistence & Anti-Brick Guard.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor import (
    BODYDATA_EXPECTED_DEND_LEN,
    BODYDATA_EXPECTED_FDAT_LEN,
    BODYDATA_EXPECTED_FDAT_OFFSET,
    BODYDATA_EXPECTED_TOTAL_BYTES,
    BODYDATA_EXPECTED_UDID_COUNT,
    BODYDATA_STAGE_A_BYPASS_BUDGET_US,
    BODYDATA_UFU_MAGIC,
    CARD_DOOR_CAPACITOR_HOLD_MS,
    EXPECTED_FX3_APPFW_BYTES_P159,
    EXPECTED_FX3_MPR_BYTES_P159,
    EXPECTED_FX3_MPR_EXPORTS_P159,
    EXPECTED_FX3_UPDATERUFP_BYTES_P159,
    EXPECTED_FX6_APPFW_BYTES_P159,
    EXPECTED_FX6_MPR_BYTES_P159,
    EXPECTED_FX6_MPR_EXPORTS_P159,
    EXPECTED_FX6_UPDATERUFP_BYTES_P159,
    EXPECTED_UPDATERUFP_EXPORTS_P159,
    MIN_FREE_SPACE_BYTES_P159,
    MIN_VALID_RSV_BYTES,
    PHASE_159_SCHEMA,
    PHASE_159_VERSION,
    ROOTFS_MEDIA_KMODS,
    SLOT_DEVICE_MATRIX,
    UPDATER_MODES_P159,
    analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence,
    build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures,
    build_phase159_media_ufu_matrix,
    evaluate_card_door_flush_sequence,
    evaluate_dual_slot_exfat_coexistence,
    evaluate_p1_official_update_clean_uninstall,
    evaluate_phase159_write_guard,
    evaluate_rsv_clip_salvage,
    evaluate_speed_class_bitrate_gate,
    evaluate_stage_a_bodydata_auto_bypass,
    parse_bodydata_ufu_header_tail,
    realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict,
)
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor.py"
)


class TestRealhwCfexpressSdxcExfatRsvAndUfuCoexistence(unittest.TestCase):
    """Comprehensive dual-mode tests (48 tests) for the 33rd unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_159_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_159_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertTrue(rep.dual_slot_exfat_coexistence_verified)
        self.assertTrue(rep.speed_class_gate_verified)
        self.assertTrue(rep.kernel_io_stall_prevented)
        self.assertTrue(rep.card_door_flush_and_rsv_verified)
        self.assertTrue(rep.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(rep.h0_equals_h3_clean_uninstall_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertTrue(rep.pillar1_dual_slot_exfat.passed)
        self.assertTrue(rep.pillar2_speed_class_gate.passed)
        self.assertTrue(rep.pillar3_card_door_rsv_salvage.passed)
        self.assertTrue(rep.pillar4_bodydata_ufu_coexistence.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), EXPECTED_FX3_APPFW_BYTES_P159)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), EXPECTED_FX6_APPFW_BYTES_P159)
            self.assertEqual(rep.donor_file_sizes.get("fx3_mpr"), EXPECTED_FX3_MPR_BYTES_P159)
            self.assertEqual(rep.donor_file_sizes.get("fx6_mpr"), EXPECTED_FX6_MPR_BYTES_P159)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), 377_328)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), 401_952)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), 15_980_568)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), 17_952_816)
            self.assertEqual(
                rep.donor_file_sizes.get("fx3_updaterufp"), EXPECTED_FX3_UPDATERUFP_BYTES_P159
            )
            self.assertEqual(
                rep.donor_file_sizes.get("fx6_updaterufp"), EXPECTED_FX6_UPDATERUFP_BYTES_P159
            )
            self.assertEqual(rep.donor_file_sizes.get("fx3_insmod_drv2"), 1_298)
            self.assertEqual(rep.donor_file_sizes.get("fx3_fstab"), 1_085)
            self.assertEqual(rep.donor_file_sizes.get("bodydata_dat"), BODYDATA_EXPECTED_TOTAL_BYTES)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_no_raw_bytes_repr_leak(self) -> None:
        rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=True)
        payload = realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict(rep)
        dumped = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(dumped), "Unexpected raw bytes repr in JSON")
        self.assertNotIn("BEGIN RSA PRIVATE KEY", dumped)
        self.assertIn(PHASE_159_SCHEMA, dumped)

    def test_06_ast_enforces_strictly_o_rdonly_and_zero_writes(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_attrs = {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND", "ACCESS_WRITE"}
        forbidden_calls = {"write", "write_bytes", "write_text"}
        os_open_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_attrs)
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr == "open"
                ):
                    os_open_count += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "open")
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
        self.assertGreaterEqual(os_open_count, 3)

    def test_07_package_init_exports_and_all(self) -> None:
        required = (
            "PHASE_159_SCHEMA",
            "PHASE_159_VERSION",
            "BODYDATA_UFU_MAGIC",
            "BODYDATA_EXPECTED_TOTAL_BYTES",
            "SLOT_DEVICE_MATRIX",
            "MEDIA_SPEED_CLASS_PROFILES",
            "CODEC_SPEED_GATE_PROFILES",
            "BodydataUfuHeaderSummary",
            "DualSlotExfatEvalResult",
            "SpeedClassGateEvalResult",
            "CardDoorFlushEvalResult",
            "RsvClipSalvageEvalResult",
            "StageABodydataBypassEvalResult",
            "P1CleanUninstallEvalResult",
            "Phase159WriteGuardResult",
            "MediaUfuCompatMatrixSummary",
            "RealhwCfexpressSdxcExfatRsvAndUfuCoexistenceReport",
            "parse_bodydata_ufu_header_tail",
            "build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures",
            "evaluate_dual_slot_exfat_coexistence",
            "evaluate_speed_class_bitrate_gate",
            "evaluate_card_door_flush_sequence",
            "evaluate_rsv_clip_salvage",
            "evaluate_stage_a_bodydata_auto_bypass",
            "evaluate_p1_official_update_clean_uninstall",
            "evaluate_phase159_write_guard",
            "build_phase159_media_ufu_matrix",
            "analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence",
            "realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict",
        )
        for name in required:
            self.assertTrue(hasattr(lab, name), f"Missing export {name} in fx3_firmware_lab")
            self.assertIn(name, lab.__all__, f"Missing {name} in fx3_firmware_lab.__all__")

    def test_08_run_audit_all_and_cli_integration(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-cfexpress-sdxc-ufu", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_159_SCHEMA)
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])

        all_summary = run_audit_all(clean_room=True)
        self.assertTrue(all_summary["all_checks_passed"])
        self.assertIn("realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit", all_summary)
        audit_keys = [k for k in all_summary.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 33)

    def test_09_cli_audit_all_clean_room_smoke(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit", parsed)

    def test_10_clean_room_fixtures_structure_valid(self) -> None:
        fx = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()
        expected_keys = {
            "fx3_appfw",
            "fx6_appfw",
            "fx3_mpr",
            "fx6_mpr",
            "fx3_sencore",
            "fx6_sencore",
            "fx3_updaterufp",
            "fx6_updaterufp",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_insmod_drv2",
            "fx3_fstab",
            "bodydata_head",
            "bodydata_tail",
        }
        self.assertEqual(set(fx.keys()), expected_keys)
        self.assertEqual(len(fx["bodydata_head"]), 256)
        self.assertEqual(len(fx["bodydata_tail"]), 64)
        self.assertEqual(fx["bodydata_head"][:8], BODYDATA_UFU_MAGIC)

    # ---- Pillar 1: Dual Hybrid CFexpress Type A / SDXC UHS-II & ExFAT Coexistence ----

    def test_11_slot_a_cfexpress_type_a_nvme_parity(self) -> None:
        res = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_A", media_type="CFEXPRESS_TYPE_A", active_profile="STAGE_B_FX6"
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.block_device, "/dev/nvme0n1p1")
        self.assertEqual(res.mount_point, "/mnt/sd")
        self.assertTrue(res.user_clips_preserved)
        self.assertTrue(res.dual_boot_wipe_prevented)
        self.assertEqual(res.status, "DUAL_CONTAINER_EXFAT_COEXISTENCE_OK")

    def test_12_slot_b_cfexpress_type_a_nvme_parity(self) -> None:
        res = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_B", media_type="CFEXPRESS_TYPE_A", active_profile="STOCK_FX3"
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.block_device, "/dev/nvme1n1p1")
        self.assertEqual(res.mount_point, "/mnt/sd2")
        self.assertTrue(res.user_clips_preserved)

    def test_13_slot_a_and_b_sdxc_uhs_ii_device_nodes(self) -> None:
        res_a = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_A", media_type="SDXC_UHS_II", active_profile="STOCK_FX3"
        )
        res_b = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_B", media_type="SDXC_UHS_II", active_profile="STAGE_B_FX6"
        )
        self.assertTrue(res_a.valid and res_b.valid)
        self.assertEqual(res_a.block_device, "/dev/mmcblk1p1")
        self.assertEqual(res_b.block_device, "/dev/mmcblk2p1")

    def test_14_single_m4root_container_accepted_cleanly(self) -> None:
        res = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_A",
            media_type="CFEXPRESS_TYPE_A",
            existing_containers=("PRIVATE/M4ROOT/CLIP", "PRIVATE/M4ROOT/MEDIAPRO.XML"),
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "SINGLE_CONTAINER_EXFAT_OK")

    def test_15_reformat_on_dual_boot_switch_blocked(self) -> None:
        res = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_A",
            media_type="CFEXPRESS_TYPE_A",
            active_profile="STAGE_B_FX6",
            reformat_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.user_clips_preserved)
        self.assertFalse(res.dual_boot_wipe_prevented)
        self.assertTrue(any("WIPE" in e for e in res.errors))

    def test_16_internal_emmc_block_device_override_blocked(self) -> None:
        for bad_blk in ("/dev/nflasha15", "/dev/cnflasha2", "/dev/mmcblk0p1"):
            res = evaluate_dual_slot_exfat_coexistence(
                slot_id="SLOT_A",
                media_type="CFEXPRESS_TYPE_A",
                block_device_override=bad_blk,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.emmc_media_format_blocked)
            self.assertTrue(any("EMMC_MEDIA_MOUNT_HAZARD" in e for e in res.errors))

    def test_17_non_exfat_filesystem_blocked(self) -> None:
        res = evaluate_dual_slot_exfat_coexistence(
            slot_id="SLOT_A", media_type="CFEXPRESS_TYPE_A", filesystem="ext4"
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("UNSUPPORTED_FILESYSTEM" in e for e in res.errors))

    def test_18_invalid_slot_media_type_or_profile_blocked(self) -> None:
        self.assertFalse(evaluate_dual_slot_exfat_coexistence(slot_id="SLOT_C").valid)
        self.assertFalse(evaluate_dual_slot_exfat_coexistence(media_type="SDHC_CLASS4").valid)
        self.assertFalse(evaluate_dual_slot_exfat_coexistence(active_profile="UNKNOWN").valid)

    def test_19_rootfs_insmod_drv2_kmods_verified_in_report(self) -> None:
        rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=True)
        p1 = rep.pillar1_dual_slot_exfat
        self.assertTrue(p1.kmod_load_order_verified)
        self.assertTrue(p1.fx3_fstab_p15_ro_verified)
        self.assertEqual(len(ROOTFS_MEDIA_KMODS), 6)
        self.assertIn("SLOT_A", SLOT_DEVICE_MATRIX)
        self.assertIn("SLOT_B", SLOT_DEVICE_MATRIX)

    # ---- Pillar 2: Speed-Class Bitrate Admission Gating ----

    def test_20_cfexpress_vpg400_and_vpg200_admitted_for_4k120_sq(self) -> None:
        r400 = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_A", media_class="CFEXPRESS_A_VPG400", codec_profile="XAVC_SI_4K_120P_SQ"
        )
        r200 = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_A", media_class="CFEXPRESS_A_VPG200", codec_profile="XAVC_SI_4K_120P_SQ"
        )
        self.assertTrue(r400.valid and r200.valid)
        self.assertGreater(r400.headroom_ratio, 5.0)
        self.assertGreater(r200.headroom_ratio, 2.5)
        self.assertTrue(r400.kernel_io_stall_prevented and r400.buffer_overrun_prevented)

    def test_21_sdxc_v90_admitted_for_4k60_and_4k120_intra(self) -> None:
        r60 = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_II_V90", codec_profile="XAVC_SI_4K_60P"
        )
        r120 = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_II_V90", codec_profile="XAVC_SI_4K_120P_SQ"
        )
        self.assertTrue(r60.valid and r120.valid)
        self.assertEqual(r60.sustained_write_mbps, 720.0)
        self.assertGreater(r60.headroom_ratio, 1.1)

    def test_22_sdxc_v60_admitted_for_xavcs_200m_and_rejected_for_600m_intra(self) -> None:
        ok = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_II_V60", codec_profile="XAVC_S_4K_60P_200M"
        )
        bad = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_II_V60", codec_profile="XAVC_SI_4K_60P"
        )
        self.assertTrue(ok.valid)
        self.assertFalse(bad.valid)
        self.assertTrue(any("SLOW_CARD_SPEED_CLASS" in e for e in bad.errors))

    def test_23_sdxc_v30_admitted_for_xavchs_150m_and_rejected_for_xavcs_and_si(self) -> None:
        ok = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_I_V30", codec_profile="XAVC_HS_4K_60P_150M"
        )
        bad_s = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_I_V30", codec_profile="XAVC_S_4K_120P_280M"
        )
        bad_si = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B", media_class="SDXC_UHS_I_V30", codec_profile="XAVC_SI_4K_24P"
        )
        self.assertTrue(ok.valid)
        self.assertFalse(bad_s.valid)
        self.assertFalse(bad_si.valid)

    def test_24_sd_write_protect_lock_blocks_admission(self) -> None:
        res = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_B",
            media_class="SDXC_UHS_II_V90",
            codec_profile="XAVC_SI_4K_60P",
            sd_write_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.sd_write_protected)
        self.assertTrue(any("WRITE_PROTECT" in e for e in res.errors))

    def test_25_slot_overcurrent_blocks_admission(self) -> None:
        res = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_A",
            media_class="CFEXPRESS_A_VPG400",
            codec_profile="XAVC_SI_4K_60P",
            overcurrent_detected=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.overcurrent_detected)
        self.assertTrue(any("OVERCURRENT" in e for e in res.errors))

    def test_26_insufficient_free_space_blocks_admission(self) -> None:
        res = evaluate_speed_class_bitrate_gate(
            slot_id="SLOT_A",
            media_class="CFEXPRESS_A_VPG400",
            codec_profile="XAVC_SI_4K_60P",
            free_space_bytes=MIN_FREE_SPACE_BYTES_P159 - 1,
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("INSUFFICIENT_MEDIA_FREE_SPACE" in e for e in res.errors))

    def test_27_unknown_media_class_or_codec_rejected(self) -> None:
        self.assertFalse(evaluate_speed_class_bitrate_gate(media_class="FAKE_CARD").valid)
        self.assertFalse(evaluate_speed_class_bitrate_gate(codec_profile="RAW_8K_UNCOMPRESSED").valid)

    # ---- Pillar 3: Card-Door Interrupt Flush & .RSV Clip Salvage ----

    def test_28_card_door_hall_irq_flushes_and_unmounts_within_capacitor_hold(self) -> None:
        res = evaluate_card_door_flush_sequence(
            slot_id="SLOT_A",
            door_open_irq_ms=0.0,
            mpr_fifo_flush_ms=4.5,
            unmount_latency_ms=2.0,
            power_rail_drop_ms=CARD_DOOR_CAPACITOR_HOLD_MS,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.fifo_flushed)
        self.assertTrue(res.unmounted_before_power_drop)
        self.assertFalse(res.rsv_fallback_triggered)
        self.assertEqual(res.unmount_complete_ms, 6.5)

    def test_29_instant_battery_pull_before_unmount_triggers_rsv_fallback(self) -> None:
        res = evaluate_card_door_flush_sequence(
            slot_id="SLOT_B",
            door_open_irq_ms=0.0,
            mpr_fifo_flush_ms=14.0,
            unmount_latency_ms=3.0,
            power_rail_drop_ms=15.0,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.unmounted_before_power_drop)
        self.assertTrue(res.rsv_fallback_triggered)
        self.assertEqual(res.status, "UNGRACEFUL_POWER_DROP_RSV_FALLBACK")

    def test_30_rsv_salvage_to_mp4_on_slot_a_zero_nflasha_writes(self) -> None:
        res = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A",
            rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0009.RSV",
            target_container="MP4",
            rsv_size_bytes=512 * 1024 * 1024,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.repaired_path, "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0009.MP4")
        self.assertTrue(res.moov_ftyp_restored)
        self.assertTrue(res.mediapro_xml_updated)
        self.assertEqual(res.nflasha_writes, 0)

    def test_31_rsv_salvage_to_mxf_on_slot_b_zero_nflasha_writes(self) -> None:
        res = evaluate_rsv_clip_salvage(
            slot_id="SLOT_B",
            rsv_path="/mnt/sd2/XDROOT/Clip/A002C015.RSV",
            target_container="MXF",
            rsv_size_bytes=1024 * 1024 * 1024,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.repaired_path, "/mnt/sd2/XDROOT/Clip/A002C015.MXF")
        self.assertEqual(res.nflasha_writes, 0)

    def test_32_rsv_salvage_rejects_tiny_truncated_or_corrupt_nal(self) -> None:
        tiny = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A",
            rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.RSV",
            rsv_size_bytes=MIN_VALID_RSV_BYTES - 1,
        )
        no_nal = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A",
            rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.RSV",
            has_valid_nal_frames=False,
        )
        self.assertFalse(tiny.valid)
        self.assertEqual(tiny.repaired_path, "")
        self.assertFalse(no_nal.valid)

    def test_33_rsv_salvage_rejects_internal_emmc_or_non_rsv_path(self) -> None:
        emmc = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A", rsv_path="/dev/nflasha15/C0001.RSV", target_container="MP4"
        )
        non_ext = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A", rsv_path="/tmp/C0001.RSV", target_container="MP4"
        )
        bad_ext = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A", rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4", target_container="MP4"
        )
        bad_tgt = evaluate_rsv_clip_salvage(
            slot_id="SLOT_A", rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.RSV", target_container="AVI"
        )
        self.assertFalse(emmc.valid or non_ext.valid or bad_ext.valid or bad_tgt.valid)

    # ---- Pillar 4: BODYDATA.DAT (\x89UFU) Coexistence & p1 Clean-Uninstall Guard ----

    def test_34_parse_bodydata_ufu_bounded_header_and_tail_exact_geometry(self) -> None:
        fx = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()
        summary = parse_bodydata_ufu_header_tail(
            total_bytes=BODYDATA_EXPECTED_TOTAL_BYTES,
            head_bytes=fx["bodydata_head"],
            tail_bytes=fx["bodydata_tail"],
            source_mode="TEST_SYNTHETIC",
        )
        self.assertTrue(summary.valid, summary.errors)
        self.assertTrue(summary.ufu_magic_ok)
        self.assertEqual(summary.total_bytes, BODYDATA_EXPECTED_TOTAL_BYTES)
        self.assertEqual(summary.udid_count, BODYDATA_EXPECTED_UDID_COUNT)
        self.assertEqual(summary.fx3_usb_pids_present, ("0x054c:0x0da0", "0x054c:0x0da1"))
        self.assertEqual(summary.fdat_offset, BODYDATA_EXPECTED_FDAT_OFFSET)
        self.assertEqual(summary.fdat_payload_bytes, BODYDATA_EXPECTED_FDAT_LEN)
        self.assertTrue(summary.dend_trailer_ok)
        self.assertTrue(summary.geometry_exact)
        self.assertEqual(
            summary.fdat_offset + 8 + summary.fdat_payload_bytes + BODYDATA_EXPECTED_DEND_LEN,
            BODYDATA_EXPECTED_TOTAL_BYTES,
        )

    def test_35_parse_bodydata_rejects_bad_magic_missing_dend_and_truncated(self) -> None:
        fx = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()
        bad_head = b"BADMAGIC" + fx["bodydata_head"][8:]
        s_magic = parse_bodydata_ufu_header_tail(
            total_bytes=BODYDATA_EXPECTED_TOTAL_BYTES,
            head_bytes=bad_head,
            tail_bytes=fx["bodydata_tail"],
            source_mode="TEST",
        )
        s_dend = parse_bodydata_ufu_header_tail(
            total_bytes=BODYDATA_EXPECTED_TOTAL_BYTES,
            head_bytes=fx["bodydata_head"],
            tail_bytes=b"\x00" * 64,
            source_mode="TEST",
        )
        s_short = parse_bodydata_ufu_header_tail(
            total_bytes=128, head_bytes=b"\x89UFU\r\n\x1a\n" + b"\x00" * 16, tail_bytes=b"", source_mode="TEST"
        )
        self.assertFalse(s_magic.valid)
        self.assertFalse(s_dend.valid)
        self.assertFalse(s_short.valid)

    def test_36_parse_bodydata_rejects_missing_fx3_usb_pid(self) -> None:
        fx = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()
        head = bytearray(fx["bodydata_head"])
        for idx in range(BODYDATA_EXPECTED_UDID_COUNT):
            struct.pack_into(">HHI", head, 0x2C + idx * 8, 0x0999, 0x054C, 0x01000000)
        summary = parse_bodydata_ufu_header_tail(
            total_bytes=BODYDATA_EXPECTED_TOTAL_BYTES,
            head_bytes=bytes(head),
            tail_bytes=fx["bodydata_tail"],
            source_mode="TEST",
        )
        self.assertFalse(summary.valid)
        self.assertTrue(any("MISSING_FX3_USB_UDID_ENTRY" in e for e in summary.errors))

    def test_37_stage_a_auto_bypass_on_slot_a_bodydata_dat(self) -> None:
        res = evaluate_stage_a_bodydata_auto_bypass(
            slot_a_bodydata_magic=BODYDATA_UFU_MAGIC,
            slot_b_bodydata_magic=None,
            bypass_latency_us=35.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.slot_a_bodydata_present)
        self.assertFalse(res.slot_b_bodydata_present)
        self.assertTrue(res.ufu_magic_valid)
        self.assertTrue(res.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(res.stock_fx3_userland_booted)
        self.assertFalse(res.corrupt_ufu_magic_flagged)

    def test_38_stage_a_auto_bypass_on_slot_b_bodydata_dat(self) -> None:
        res = evaluate_stage_a_bodydata_auto_bypass(
            slot_a_bodydata_magic=None,
            slot_b_bodydata_magic=BODYDATA_UFU_MAGIC,
            bypass_latency_us=48.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.slot_b_bodydata_present)
        self.assertTrue(res.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(res.stock_fx3_userland_booted)

    def test_39_stage_a_corrupt_bodydata_dat_fails_closed_to_stock_fx3(self) -> None:
        res = evaluate_stage_a_bodydata_auto_bypass(
            slot_a_bodydata_magic=b"CORRUPT!",
            slot_b_bodydata_magic=None,
            bypass_latency_us=41.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.corrupt_ufu_magic_flagged)
        self.assertFalse(res.ufu_magic_valid)
        self.assertTrue(res.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(res.stock_fx3_userland_booted)
        self.assertEqual(res.status, "CORRUPT_BODYDATA_DAT_FAIL_CLOSED_TO_STOCK")

    def test_40_stage_a_no_bodydata_dat_allows_stage_b(self) -> None:
        res = evaluate_stage_a_bodydata_auto_bypass(
            slot_a_bodydata_magic=None,
            slot_b_bodydata_magic=None,
            bypass_latency_us=25.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.stage_b_blocked_on_bodydata_dat)
        self.assertFalse(res.stock_fx3_userland_booted)
        self.assertEqual(res.status, "NO_BODYDATA_DAT_STAGE_B_ELIGIBLE")

    def test_41_stage_a_bypass_over_100us_budget_fails(self) -> None:
        res = evaluate_stage_a_bodydata_auto_bypass(
            slot_a_bodydata_magic=BODYDATA_UFU_MAGIC,
            bypass_latency_us=BODYDATA_STAGE_A_BYPASS_BUDGET_US + 5.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("LATENCY_EXCEEDED" in e for e in res.errors))

    def test_42_p1_official_update_requires_h0_eq_h3_clean_uninstall(self) -> None:
        for mode in UPDATER_MODES_P159:
            ok = evaluate_p1_official_update_clean_uninstall(
                updater_mode=mode,
                p15_clean_uninstalled=True,
                h0_equals_h3=True,
                p15_residual_files=0,
                orig_backup_verified=True,
                battery_soc_pct=80,
            )
            self.assertTrue(ok.valid and ok.safe_for_sony_p1_updater and ok.sector0_p2_p18_untouched)

    def test_43_p1_official_update_blocked_when_p15_dirty_or_h0_ne_h3(self) -> None:
        dirty = evaluate_p1_official_update_clean_uninstall(
            updater_mode="mode5",
            p15_clean_uninstalled=False,
            h0_equals_h3=False,
            p15_residual_files=1,
        )
        residuals = evaluate_p1_official_update_clean_uninstall(
            updater_mode="mode5",
            p15_clean_uninstalled=True,
            h0_equals_h3=True,
            p15_residual_files=3,
        )
        no_orig = evaluate_p1_official_update_clean_uninstall(
            updater_mode="mode5",
            orig_backup_verified=False,
        )
        self.assertFalse(dirty.valid or residuals.valid or no_orig.valid)
        self.assertFalse(dirty.safe_for_sony_p1_updater)

    def test_44_p1_official_update_blocked_below_51_pct_battery_or_unknown_mode(self) -> None:
        low_batt = evaluate_p1_official_update_clean_uninstall(
            updater_mode="mode5", battery_soc_pct=50
        )
        bad_mode = evaluate_p1_official_update_clean_uninstall(
            updater_mode="mode99", battery_soc_pct=90
        )
        self.assertFalse(low_batt.valid or bad_mode.valid)
        self.assertTrue(any("BATTERY_BELOW_51_PCT" in e for e in low_batt.errors))

    def test_45_write_guard_allows_volatile_ram_and_external_clips_only(self) -> None:
        for p in (
            "/tmp/stage_b_media_probe.json",
            "ram://rsv_salvage_map.bin",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/sd2/XDROOT/Clip/A001C001.MXF",
        ):
            res = evaluate_phase159_write_guard(p)
            self.assertTrue(res.valid, f"Expected volatile/ext clip allowed: {p}")
            self.assertTrue(res.volatile_or_ext_allowed)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)

    def test_46_write_guard_blocks_bodydata_p15_sector0_p2_p18_and_spinor(self) -> None:
        forbidden = (
            "/mnt/sd/BODYDATA.DAT",
            "/mnt/sd2/BODYDATA.DAT",
            "/dev/nflasha15",
            "/dev/cnflasha2",
            "/dev/mmcblk0p1",
            "p2:/Backup.bin",
            "p2:/psd.bin",
            "p2:/defdet.bin",
            "p18:/lensfile.bin",
            "sector0:sdm2",
            "spi_nor:/loader_nor.bin",
            "/usr/bin/im.elf",
            "/setting/updater/dat4",
        )
        for tgt in forbidden:
            res = evaluate_phase159_write_guard(tgt)
            self.assertFalse(res.valid, f"Expected persistent/BODYDATA write blocked: {tgt}")
            self.assertTrue(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)

    def test_47_compatibility_matrix_has_12_touchpoints_and_4_classes(self) -> None:
        matrix = build_phase159_media_ufu_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(len(matrix.touchpoints), 12)
        self.assertEqual(
            set(matrix.class_counts.keys()),
            {
                BRIDGE_CLASS_NATIVE_PASSTHROUGH,
                BRIDGE_CLASS_SHIM_TRANSLATED,
                BRIDGE_CLASS_MASKED_ABSENT_HW,
                BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            },
        )
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_NATIVE_PASSTHROUGH], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_SHIM_TRANSLATED], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_MASKED_ABSENT_HW], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_HARD_WRITE_PROTECTED], 0)
        self.assertEqual(sum(matrix.subsystem_counts.values()), 12)

    def test_48_elf_abi_export_counts_verified_in_report(self) -> None:
        rep = analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=True)
        p4 = rep.pillar4_bodydata_ufu_coexistence
        self.assertEqual(p4.fx3_updaterufp_summary.export_count, EXPECTED_UPDATERUFP_EXPORTS_P159)
        self.assertEqual(p4.fx6_updaterufp_summary.export_count, EXPECTED_UPDATERUFP_EXPORTS_P159)
        self.assertEqual(p4.fx3_mpr_summary.export_count, EXPECTED_FX3_MPR_EXPORTS_P159)
        self.assertEqual(p4.fx6_mpr_summary.export_count, EXPECTED_FX6_MPR_EXPORTS_P159)
        self.assertTrue(p4.bodydata_ufu_summary.valid)
        self.assertTrue(p4.slot_a_bodydata_bypass_eval.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(p4.slot_b_bodydata_bypass_eval.stage_b_blocked_on_bodydata_dat)
        self.assertTrue(p4.clean_uninstall_p1_approved_eval.safe_for_sony_p1_updater)
        self.assertFalse(p4.dirty_p15_p1_blocked_eval.safe_for_sony_p1_updater)


if __name__ == "__main__":
    unittest.main()
