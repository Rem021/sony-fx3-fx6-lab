"""Dual-mode unit tests (96 cases) for Phase 321 (`preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes`):
14th Real-Hardware Physical Bench Readiness Verifier across Waves 60-61 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `15.0s` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx6-on-fx3-closure",
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    TARGET_MODEL_ID_INT,
    build_default_h0_baselines,
)
from fx6_closure.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier import (  # noqa: E402
    P321_AF_ASSIST_INCOMPATIBLE_LENSES,
    P321_AF_SUBJ_SHIFT_SENS_MAX,
    P321_AF_TRANSITION_SPEED_MAX,
    P321_ASPECT_MARKER_16_STATES,
    P321_AUTO_SWITCH_MEDIA_RESID16_HEX,
    P321_CACERT_MAX_BYTES,
    P321_CHECK_GROUP_A_ID,
    P321_CHECK_GROUP_B_ID,
    P321_CHECK_GROUP_C_ID,
    P321_CHECK_GROUP_D_ID,
    P321_CNCT_WHILE_POWER_OFF_RESID16_HEX,
    P321_CUSTOM_WB_ERROR_RESID16_HEX,
    P321_DORMANT_PRIORITIZE_REC_MEDIA_RESID16_HEX,
    P321_DORMANT_PROXY_16M_8BIT_RESID16_HEX,
    P321_ERRNO_EOPNOTSUPP,
    P321_ERRNO_EROFS,
    P321_FTPES_TLS_RESID16_HEX,
    P321_FX3_FTP_SERVER_MAX,
    P321_FX3_PEAKING_FOUR_COLORS,
    P321_FX6_USER_MENU_MAX_ITEMS,
    P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE,
    P321_GA_ERR_MODEL_OR_FW_FLOOR,
    P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT,
    P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT,
    P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH,
    P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION,
    P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU,
    P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD,
    P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE,
    P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS,
    P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE,
    P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS,
    P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET,
    P321_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P321_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC,
    P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE,
    P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED,
    P321_MC_FOCUS_MAP_FPS_CUTOFF,
    P321_MYMENU_EXACT_PAGES,
    P321_MYMENU_EXACT_SLOTS_PER_PAGE,
    P321_MYMENU_EXACT_TOTAL_SLOTS,
    P321_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P321_SCHEMA,
    P321_SONY_HELP_GUIDE_ID,
    P321_STILL_RECORDING_MEDIA_FOUR_MODES,
    P321_MOVIE_RECORDING_MEDIA_THREE_MODES,
    PHASE321_E_ND_ACTUATOR_TX_COUNT,
    PHASE321_PASSIVE_TX_BYTES_EMITTED,
    PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE321_SLOT1_DATA_SECTOR_WRITES,
    PHASE321_USB_PACKETS_TRANSMITTED,
    PHASE321_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_321_CHECK_GROUP_IDS,
    PHASE_321_SCHEMA,
    _canonical_sha256_dict,
    build_simulated_phase321_tier0_receipts,
    evaluate_p321_check_group_a_rec_media_overflow_and_proxy,
    evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu,
    evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb,
    evaluate_p321_check_group_d_af_focus_map_marker_and_tier0,
    evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
    inspect_phase321_donors_bounded,
    render_phase321_markdown,
    run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
    verify_phase321_report,
)


def _run_cli_subprocess(
    args: list[str],
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(REPO_ROOT / p)
        for p in (
            "outputs/fx6-on-fx3-closure",
            "outputs/fx3-safety",
            "outputs/fx3-recovery-adapter",
            "outputs/fx3-firmware-lab",
            "outputs/fx3-vm",
        )
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "fx6_closure",
            "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase321Preflight14Verifier(unittest.TestCase):
    # ------------------------------------------------------------------
    # 01-10: Exports, Schema, Modes & Bounded O_RDONLY Donor Safety
    # ------------------------------------------------------------------

    def test_01_top_level_package_exports_phase321_symbols(self) -> None:
        self.assertEqual(fx6_closure.PHASE_321_SCHEMA, P321_SCHEMA)
        self.assertEqual(fx6_closure.P321_SCHEMA_VERSION, "realhw_preflight14_rec_media_proxy_cloud_mymenu_ftpes_v1")
        self.assertIs(
            fx6_closure.run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
            run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
        )
        self.assertIs(fx6_closure.verify_phase321_report, verify_phase321_report)

    def test_02_offline_default_blocks_live_attach_awaiting_tier0(self) -> None:
        rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight()
        self.assertEqual(rep.overall_status, P321_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.check_group_count, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertTrue(verify_phase321_report(rep).valid)

    def test_03_simulate_bench_dry_run_passes_without_live_auth(self) -> None:
        rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep.simulate_bench_dry_run)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "DRY_RUN_SIMULATED")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.e_nd_i2c_tx_bytes, 0)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase321_report(rep.to_dict()).valid)

    def test_04_physical_dual_media_receipts_verify_with_distinct_st_dev(self) -> None:
        ser = "FX3702BENCH321"
        cid = "150100424a4e42345201020304050607"
        sim = build_simulated_phase321_tier0_receipts(body_serial=ser, emmc_cid=cid)
        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "slot_a_FX3RCPT1.bin"
            p_b = Path(td) / "slot_b_FX3RCPT1.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])
            rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=1001,
                st_dev_b_override=2002,
                body_serial=ser,
                emmc_cid=cid,
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
                h3_baselines=sim["h3_baselines"],
            )
        self.assertEqual(rep.go_no_go, P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_528B")
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase321_report(rep).valid)

    def test_05_forced_clean_room_never_touches_disk_and_zeros_leaks(self) -> None:
        donor = inspect_phase321_donors_bounded(force_clean_room=True)
        self.assertEqual(donor.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(donor.donor_tree_present)
        self.assertEqual(donor.checked_paths, ())
        self.assertEqual(donor.bytes_read_total, 0)
        self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
        self.assertTrue(donor.within_budget)

    def test_06_donorless_work_root_and_none_dir_safe_for_linux_ci(self) -> None:
        with tempfile.TemporaryDirectory() as empty_dir:
            donor = inspect_phase321_donors_bounded(
                force_clean_room=False,
                work_root=Path(empty_dir),
                fx6_lib_dir=None,
                fx3_modules_dir=None,
            )
            self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
            self.assertTrue(donor.within_budget)
        with mock.patch(
            "fx6_closure.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier._resolve_work_root_or_none",
            return_value=None,
        ):
            donor_ci = inspect_phase321_donors_bounded(
                force_clean_room=False,
                work_root=None,
                fx6_lib_dir=None,
                fx3_modules_dir=None,
            )
            self.assertEqual(donor_ci.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(donor_ci.bytes_read_total, 0)
            self.assertEqual(donor_ci.raw_firmware_bytes_leaked, 0)

    def test_07_bounded_donor_read_fast_budget_under_50ms_with_headroom(self) -> None:
        t0 = time.monotonic()
        donor = inspect_phase321_donors_bounded()
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
        self.assertLessEqual(donor.bytes_read_total, 5 * 64)
        self.assertLess(elapsed_ms, 15000.0)
        self.assertIn(donor.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_08_schema_constants_and_check_group_ids_exact(self) -> None:
        self.assertEqual(P321_SCHEMA, "realhw_preflight14_rec_media_proxy_cloud_mymenu_ftpes_v1")
        self.assertEqual(P321_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_321_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_321_CHECK_GROUP_IDS,
            (
                P321_CHECK_GROUP_A_ID,
                P321_CHECK_GROUP_B_ID,
                P321_CHECK_GROUP_C_ID,
                P321_CHECK_GROUP_D_ID,
            ),
        )

    def test_09_zero_telemetry_constants_locked_zero(self) -> None:
        self.assertEqual(PHASE321_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE321_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE321_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE321_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE321_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE321_E_ND_ACTUATOR_TX_COUNT, 0)

    def test_10_model_id_fw_and_help_guide_floor_enforced(self) -> None:
        ga_bad_model = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(body_model_id=0x99999999)
        ga_bad_fw = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(body_fw="6.01")
        ga_bad_guide = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(sony_help_guide_id="ilc/2000")
        for ga in (ga_bad_model, ga_bad_fw, ga_bad_guide):
            self.assertFalse(ga.passed)
            self.assertTrue(any(P321_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga.errors))

    # ------------------------------------------------------------------
    # 11-31: Check Group A — Wave 60 Rec. Media Overflow Trap, Card Speed & Proxy
    # ------------------------------------------------------------------

    def test_11_ga_dormant_prioritize_rec_media_0x719e_rejected_eopnotsupp(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            dormant_prioritize_rec_media_requested=True
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.fx3_prioritize_rec_media_present)
        self.assertIn(P321_DORMANT_PRIORITIZE_REC_MEDIA_RESID16_HEX, ga.errors[0])
        self.assertIn(str(P321_ERRNO_EOPNOTSUPP), ga.errors[0])

    def test_12_ga_claimed_prioritize_rec_media_present_rejected(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            fx3_prioritize_rec_media_present_claimed=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT in e for e in ga.errors))

    def test_13_ga_still_4_modes_vs_movie_3_modes_and_movie_sort_rejected(self) -> None:
        self.assertEqual(len(P321_STILL_RECORDING_MEDIA_FOUR_MODES), 4)
        self.assertEqual(len(P321_MOVIE_RECORDING_MEDIA_THREE_MODES), 3)
        ga_movie_sort = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            shoot_mode="MOVIE",
            recording_media="SORT_RECORDING",
            slot1_contains_tier0_dump=False,
        )
        self.assertFalse(ga_movie_sort.passed)
        self.assertTrue(
            any(P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT in e for e in ga_movie_sort.errors)
        )
        ga_still_sort = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            shoot_mode="PHOTO",
            recording_media="SORT_RECORDING",
            slot1_contains_tier0_dump=False,
        )
        self.assertTrue(ga_still_sort.passed, ga_still_sort.errors)

    def test_14_ga_claimed_fx3_movie_sort_recording_present_rejected(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            fx3_movie_sort_recording_present_claimed=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT in e for e in ga.errors))

    def test_15_ga_simult_recording_enforces_matching_exfat_or_fat32(self) -> None:
        ga_mismatch = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            recording_media="SIMULTANEOUS_RECORDING",
            slot1_contains_tier0_dump=False,
            slot1_fs="EXFAT",
            slot2_fs="FAT32",
        )
        self.assertFalse(ga_mismatch.passed)
        self.assertTrue(
            any(P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH in e for e in ga_mismatch.errors)
        )
        ga_match = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            recording_media="SIMULTANEOUS_RECORDING",
            slot1_contains_tier0_dump=False,
            slot1_fs="EXFAT",
            slot2_fs="EXFAT",
        )
        self.assertTrue(ga_match.passed, ga_match.errors)

    def test_16_ga_auto_switch_media_0x6dd9_survives_camera_settings_reset(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            claimed_auto_switch_wiped_by_camera_reset=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P321_AUTO_SWITCH_MEDIA_RESID16_HEX[2:] in e or "0x6dd9" in e for e in ga.errors))

    def test_17_ga_slot2_to_slot1_overflow_trap_blocks_slot1_and_simult_when_vault_present(self) -> None:
        for bad_media in ("SLOT_1", "SIMULTANEOUS_RECORDING"):
            ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
                recording_media=bad_media,
                slot1_contains_tier0_dump=True,
            )
            self.assertFalse(ga.passed)
            self.assertFalse(ga.slot1_overflow_trap_locked_off)
            self.assertTrue(any(str(P321_ERRNO_EROFS) in e for e in ga.errors))

    def test_18_ga_slot2_to_slot1_overflow_trap_blocks_auto_switch_on(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            recording_media="SLOT_2",
            auto_switch_media="ON",
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.slot1_overflow_trap_locked_off)
        self.assertTrue(any("Overflow Trap" in e for e in ga.errors))

    def test_19_ga_slot1_unlocked_wp_or_rec_write_or_nonzero_sectors_blocked(self) -> None:
        ga_wp = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(slot1_wp_locked=False)
        ga_rec = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(slot1_rec_write_requested=True)
        ga_sec = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(slot1_data_sector_writes=1)
        for ga in (ga_wp, ga_rec, ga_sec):
            self.assertFalse(ga.passed)
        self.assertTrue(ga_rec.slot1_tier0_vault_mutated)
        self.assertTrue(ga_sec.slot1_tier0_vault_mutated)

    def test_20_ga_fx6_rec_button_slot_set_and_relay_mutual_exclusions_rejected(self) -> None:
        ga_recbtn = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            fx3_independent_rec_button_slot_set_claimed=True
        )
        ga_relay = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            fx6_relay_with_proxy_streaming_chunk_claimed=True
        )
        for ga in (ga_recbtn, ga_relay):
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH in e for e in ga.errors)
            )

    def test_21_ga_cfexpress_type_b_rejected(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            media_speed_grade="CFEXPRESS_TYPE_B"
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE in e for e in ga.errors))

    def test_22_ga_sq_all_i_1200_and_890_mbps_require_cfexpress_vpg200_plus(self) -> None:
        ga_v90 = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            shoot_mode="S_AND_Q",
            sq_enabled=True,
            sq_fps=120.0,
            movie_file_format="XAVC_S_I_4K",
            movie_bitrate_mbps=1200,
            media_speed_grade="SDXC_V90",
        )
        self.assertFalse(ga_v90.passed)
        self.assertTrue(any(P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE in e for e in ga_v90.errors))
        ga_vpg200 = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            shoot_mode="S_AND_Q",
            sq_enabled=True,
            sq_fps=120.0,
            movie_file_format="XAVC_S_I_4K",
            movie_bitrate_mbps=1200,
            media_speed_grade="CFEXPRESS_A_VPG200",
        )
        self.assertTrue(ga_vpg200.passed, ga_vpg200.errors)

    def test_23_ga_all_i_4k_rejects_v60_and_280mbps_rejects_v30(self) -> None:
        ga_all_i_v60 = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            movie_file_format="XAVC_S_I_4K",
            movie_bitrate_mbps=600,
            media_speed_grade="SDXC_V60",
        )
        ga_280_v30 = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            movie_file_format="XAVC_S_4K",
            movie_bitrate_mbps=280,
            media_speed_grade="SDXC_V30",
        )
        self.assertFalse(ga_all_i_v60.passed)
        self.assertFalse(ga_280_v30.passed)

    def test_24_ga_vpg400_0xe224_caution_requires_ack_at_600mbps_plus_proxy(self) -> None:
        ga_unack = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            media_speed_grade="CFEXPRESS_A_VPG200",
            movie_file_format="XAVC_S_I_4K",
            movie_bitrate_mbps=600,
            proxy_recording="ON",
            vpg400_caution_acknowledged=False,
        )
        self.assertFalse(ga_unack.passed)
        self.assertTrue(any("0xe224" in e for e in ga_unack.errors))
        ga_ack = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            media_speed_grade="CFEXPRESS_A_VPG200",
            movie_file_format="XAVC_S_I_4K",
            movie_bitrate_mbps=600,
            proxy_recording="ON",
            vpg400_caution_acknowledged=True,
        )
        self.assertTrue(ga_ack.passed, ga_ack.errors)
        self.assertTrue(any("0xe224" in w for w in ga_ack.warnings))

    def test_25_ga_sdhc_4gb_split_false_claim_rejected(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(claimed_sdhc_no_4gb_split=True)
        self.assertFalse(ga.passed)
        self.assertTrue(any("4 GB" in e for e in ga.errors))

    def test_26_ga_dormant_8bit_fhd_proxy_0x6b8f_rejected(self) -> None:
        ga_flag = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            dormant_proxy_8bit_fhd_requested=True
        )
        ga_setting = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_file_format="XAVC_HS_HD",
            proxy_record_setting="1920x1080_16M_8BIT",
        )
        self.assertFalse(ga_flag.passed)
        self.assertFalse(ga_setting.passed)
        self.assertIn(P321_DORMANT_PROXY_16M_8BIT_RESID16_HEX, ga_flag.errors[0])

    def test_27_ga_proxy_format_and_record_setting_pairing_enforced(self) -> None:
        ga_bad_s = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON",
            proxy_file_format="XAVC_S_HD",
            proxy_record_setting="1920x1080_9M_10BIT",
        )
        ga_bad_hs = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON",
            proxy_file_format="XAVC_HS_HD",
            proxy_record_setting="1280x720_6M_8BIT",
        )
        ga_ok_hs = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON",
            proxy_file_format="XAVC_HS_HD",
            proxy_record_setting="1920x1080_16M_10BIT",
        )
        self.assertFalse(ga_bad_s.passed)
        self.assertFalse(ga_bad_hs.passed)
        self.assertTrue(ga_ok_hs.passed, ga_ok_hs.errors)

    def test_28_ga_proxy_blocked_at_100p_119_88p_and_sq_100_120fps(self) -> None:
        ga_100p = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON", rec_fps=100.0
        )
        ga_119p = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON", rec_fps=119.88
        )
        ga_sq120 = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_recording="ON", sq_enabled=True, sq_fps=120.0
        )
        for ga in (ga_100p, ga_119p, ga_sq120):
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT in e for e in ga.errors)
            )

    def test_29_ga_proxy_allowed_on_xavc_si_dci4k_le_59_94p(self) -> None:
        ga_ok = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            movie_file_format="XAVC_S_I_DCI_4K",
            movie_bitrate_mbps=600,
            rec_fps=59.94,
            proxy_recording="ON",
            vpg400_caution_acknowledged=True,
        )
        self.assertTrue(ga_ok.passed, ga_ok.errors)
        self.assertTrue(ga_ok.proxy_allowed_on_dci4k_le60p)
        ga_false_claim = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            claimed_proxy_blocked_on_dci4k_60p=True
        )
        self.assertFalse(ga_false_claim.passed)

    def test_30_ga_m4root_sub_s03_mp4_coupled_delete_on_slot1_blocked_erofs(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            proxy_slot1_write_or_coupled_delete_requested=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any("M4ROOT/SUB/*S03.MP4" in e and str(P321_ERRNO_EROFS) in e for e in ga.errors))

    def test_31_ga_proxy_reset_persistence_claim_and_fx6_chunk_claim_rejected(self) -> None:
        ga_reset = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            claimed_proxy_resists_camera_reset=True
        )
        ga_chunk = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            claimed_fx3_has_fx6_chunk_upload=True
        )
        self.assertFalse(ga_reset.passed)
        self.assertFalse(ga_chunk.passed)

    # ------------------------------------------------------------------
    # 32-47: Check Group B — Cloud/C3, Zero-RF Power-OFF BLE & 6x7=42 My Menu
    # ------------------------------------------------------------------

    def test_32_gb_cloud_connection_and_ftp_mutual_exclusion_enforced(self) -> None:
        gb_both = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            cloud_connection="ON", ftp_transfer_func="ON"
        )
        self.assertFalse(gb_both.passed)
        self.assertTrue(any("CLOUD_CONNECTION_ON_FTP_OFF" in e for e in gb_both.errors))

    def test_33_gb_zero_rf_bench_forbids_cloud_connection_and_c3_portal(self) -> None:
        gb_cloud = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(cloud_connection="ON")
        gb_c3 = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(c3_portal_enabled=True)
        self.assertFalse(gb_cloud.passed)
        self.assertFalse(gb_c3.passed)
        self.assertTrue(any(P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION in e for e in gb_cloud.errors))
        self.assertTrue(any(P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION in e for e in gb_c3.errors))

    def test_34_gb_cloud_star_persistence_survives_both_reset_and_initialize(self) -> None:
        gb_rst = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_cloud_wiped_by_camera_reset=True
        )
        gb_init = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_cloud_wiped_by_initialize=True
        )
        self.assertFalse(gb_rst.passed)
        self.assertFalse(gb_init.passed)

    def test_35_gb_c3_portal_ver400_and_cloud_ftp_claim_checks(self) -> None:
        gb_v4 = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_c3_portal_before_v400=True
        )
        gb_ftp = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_fx3_cloud_does_not_exclude_ftp=True
        )
        self.assertFalse(gb_v4.passed)
        self.assertFalse(gb_ftp.passed)

    def test_36_gb_clip_flag_filter_ver700_values_accepted_invalid_rejected(self) -> None:
        for flag in ("NONE", "OK", "NG", "KEEP"):
            gb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(clip_flag_filter=flag)
            self.assertTrue(gb.passed, gb.errors)
        gb_bad = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(clip_flag_filter="STAR5")
        self.assertFalse(gb_bad.passed)

    def test_37_gb_cnct_while_power_off_0x6ab3_on_blocked_even_with_airplane_on(self) -> None:
        gb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            airplane_mode="ON",
            cnct_while_power_off="ON",
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any(P321_CNCT_WHILE_POWER_OFF_RESID16_HEX in e for e in gb.errors))

    def test_38_gb_airplane_mode_off_blocked(self) -> None:
        gb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(airplane_mode="OFF")
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD in e for e in gb.errors)
        )

    def test_39_gb_bluetooth_on_or_wifi_on_blocked(self) -> None:
        gb_bt = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(bluetooth_function="ON")
        gb_wf = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(wifi_enabled=True)
        self.assertFalse(gb_bt.passed)
        self.assertFalse(gb_wf.passed)

    def test_40_gb_rf_packets_and_p12_p13_nvs_writes_blocked(self) -> None:
        gb_pkt = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(wireless_rf_packets_emitted=1)
        gb_nvs = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            rf_nvs_p12_p13_writes_requested=True
        )
        self.assertFalse(gb_pkt.passed)
        self.assertFalse(gb_nvs.passed)
        self.assertFalse(gb_nvs.rf_nvs_p12_p13_writes_authorized)

    def test_41_gb_cnct_while_power_off_reset_survival_and_fx6_zero_bt(self) -> None:
        gb_rst = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_cnct_while_power_off_wiped_by_camera_reset=True
        )
        gb_fx6 = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(fx6_has_bluetooth_claimed=True)
        self.assertFalse(gb_rst.passed)
        self.assertFalse(gb_fx6.passed)

    def test_42_gb_mymenu_exact_6_by_7_equals_42_slots_enforced(self) -> None:
        gb_ok = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu()
        self.assertTrue(gb_ok.passed)
        self.assertEqual(gb_ok.mymenu_pages, P321_MYMENU_EXACT_PAGES)
        self.assertEqual(gb_ok.mymenu_slots_per_page, P321_MYMENU_EXACT_SLOTS_PER_PAGE)
        self.assertEqual(gb_ok.mymenu_total_slots, P321_MYMENU_EXACT_TOTAL_SLOTS)
        for kwargs in (
            {"mymenu_pages": 5, "mymenu_total_slots": 35},
            {"mymenu_slots_per_page": 6, "mymenu_total_slots": 36},
            {"mymenu_total_slots": 30},
            {"fx3_mymenu_30_or_36_slots_only_claimed": True},
        ):
            gb_bad = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(**kwargs)
            self.assertFalse(gb_bad.passed)
            self.assertTrue(
                any(P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU in e for e in gb_bad.errors)
            )

    def test_43_gb_mymenu_disallows_playback_items_and_survives_reset(self) -> None:
        gb_pb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            mymenu_playback_item_requested=True
        )
        gb_rst = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_mymenu_wiped_by_camera_reset=True
        )
        self.assertFalse(gb_pb.passed)
        self.assertFalse(gb_rst.passed)

    def test_44_gb_fx6_user_menu_20_items_4digit_pin_valid_and_invalid(self) -> None:
        gb_ok = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(fx6_user_menu_pin="9876")
        self.assertTrue(gb_ok.passed)
        self.assertEqual(gb_ok.fx6_user_menu_max_items, P321_FX6_USER_MENU_MAX_ITEMS)
        self.assertTrue(gb_ok.fx6_user_menu_pin_valid)
        for bad_pin in ("123", "12345", "ABCD", ""):
            gb_bad = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(fx6_user_menu_pin=bad_pin)
            self.assertFalse(gb_bad.passed)
            self.assertFalse(gb_bad.fx6_user_menu_pin_valid)

    def test_45_gb_fx3_lacks_pin_user_menu_and_fx6_pin_excluded_from_all_file(self) -> None:
        gb1 = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_fx3_has_pin_user_menu_with_lock=True
        )
        gb2 = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            claimed_fx6_user_menu_pin_included_in_all_file=True
        )
        self.assertFalse(gb1.passed)
        self.assertFalse(gb2.passed)

    # ------------------------------------------------------------------
    # 46-64: Check Group C — Passive FTP/FTPES 9-Server, USB-LAN Bypass, WB/Cine EI
    # ------------------------------------------------------------------

    def test_46_gc_ftp_server_slot_1_to_9_enforced(self) -> None:
        for slot in (1, 9):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(ftp_server_slot=slot)
            self.assertTrue(gc.passed, gc.errors)
        for bad_slot in (0, 10):
            gc_bad = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(ftp_server_slot=bad_slot)
            self.assertFalse(gc_bad.passed)
            self.assertTrue(
                any(P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE in e for e in gc_bad.errors)
            )

    def test_47_gc_sftp_rejected_eopnotsupp_and_ftpes_0x6553_ftp_allowed(self) -> None:
        for proto in ("FTP", "FTPES", "NONE"):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(ftp_protocol=proto)
            self.assertTrue(gc.passed, gc.errors)
        gc_sftp = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(ftp_protocol="SFTP")
        gc_sftp_claim = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            fx3_sftp_present_claimed=True
        )
        self.assertFalse(gc_sftp.passed)
        self.assertFalse(gc_sftp_claim.passed)
        self.assertFalse(gc_sftp.fx3_ftp_sftp_present)
        self.assertIn(P321_FTPES_TLS_RESID16_HEX, gc_sftp.errors[0])

    def test_48_gc_active_ftp_mode_rejected_passive_only(self) -> None:
        for bad_kwargs in (
            {"ftp_transfer_mode": "ACTIVE"},
            {"ftp_active_mode_requested": True},
            {"fx3_ftp_active_mode_present_claimed": True},
        ):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.fx3_ftp_active_mode_present)

    def test_49_gc_dormant_transfer_jpeg_heif_size_rejected(self) -> None:
        gc_req = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            dormant_transfer_jpeg_heif_size_requested=True
        )
        gc_claim = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            fx3_transfer_jpeg_heif_size_present_claimed=True
        )
        self.assertFalse(gc_req.passed)
        self.assertFalse(gc_claim.passed)
        self.assertFalse(gc_req.fx3_ftp_transfer_jpeg_size_present)

    def test_50_gc_fx6_certification_pem_slot_b_and_3_server_cap_claims_rejected(self) -> None:
        gc1 = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            claimed_fx3_uses_certification_pem_slot_b=True
        )
        gc2 = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            claimed_fx3_ftp_limited_to_3_servers=True
        )
        self.assertFalse(gc1.passed)
        self.assertFalse(gc2.passed)

    def test_51_gc_slot1_avf_info_ftp_transfer_list_write_blocked_erofs(self) -> None:
        gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            ftp_slot1_write_or_transfer_list_requested=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(gc.passed)
        self.assertTrue(gc.slot1_tier0_vault_mutated)
        self.assertTrue(any(str(P321_ERRNO_EROFS) in e for e in gc.errors))

    def test_52_gc_cacert_pem_size_1_to_1mib_and_slot1_write_blocked(self) -> None:
        gc_ok = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            cacert_pem_size_bytes=P321_CACERT_MAX_BYTES
        )
        self.assertTrue(gc_ok.passed, gc_ok.errors)
        for bad_sz in (0, P321_CACERT_MAX_BYTES + 1):
            gc_bad = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(cacert_pem_size_bytes=bad_sz)
            self.assertFalse(gc_bad.passed)
        gc_s1 = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            cacert_write_to_slot1_requested=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(gc_s1.passed)
        self.assertTrue(gc_s1.slot1_tier0_vault_mutated)

    def test_53_gc_critical_usb_lan_airplane_mode_bypass_firewall(self) -> None:
        for kwargs in (
            {"usb_lan_tethering": "ON"},
            {"usb_lan_cnct_launch": "ON"},
            {"ftp_transfer_func": "ON"},
            {"network_transport": "USB_LAN"},
            {"claimed_airplane_mode_blocks_usb_lan": True},
        ):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(**kwargs)
            self.assertFalse(gc.passed, f"Expected USB-LAN bypass block for {kwargs}")
            self.assertTrue(
                any(P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS in e for e in gc.errors)
            )

    def test_54_gc_wb_kelvin_2500_to_9900_100k_step_and_ab_gm_shift_bounds(self) -> None:
        gc_min = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            wb_kelvin_k=2500, wb_ab_shift=-7, wb_gm_shift=7
        )
        gc_max = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            wb_kelvin_k=9900, wb_ab_shift=7, wb_gm_shift=-7
        )
        self.assertTrue(gc_min.passed, gc_min.errors)
        self.assertTrue(gc_max.passed, gc_max.errors)
        for bad_kwargs in (
            {"wb_kelvin_k": 2400},
            {"wb_kelvin_k": 10000},
            {"wb_kelvin_k": 5650},
            {"wb_ab_shift": -8},
            {"wb_gm_shift": 8},
        ):
            gc_bad = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(**bad_kwargs)
            self.assertFalse(gc_bad.passed, f"Expected WB bounds failure for {bad_kwargs}")

    def test_55_gc_cine_ei_locks_out_auto_and_underwater_auto_wb(self) -> None:
        for log_mode in ("CINE_EI", "CINE_EI_QUICK"):
            for wb_mode in ("AUTO", "UNDERWATER_AUTO"):
                gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
                    log_shooting_mode=log_mode, wb_mode=wb_mode
                )
                self.assertFalse(gc.passed)
                self.assertTrue(
                    any(P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE in e for e in gc.errors)
                )

    def test_56_gc_custom_wb_setup_triggers_0x0220_under_log_slog3_pplut(self) -> None:
        for kwargs in (
            {"log_shooting_mode": "CINE_EI"},
            {"log_shooting_mode": "FLEXIBLE_ISO"},
            {"log_shooting_mode": "OFF", "picture_profile": "PP8"},
            {"log_shooting_mode": "OFF", "picture_profile": "PP9"},
            {"log_shooting_mode": "OFF", "picture_profile": "PPLUT1"},
            {"log_shooting_mode": "OFF", "picture_profile": "PPLUT4"},
        ):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
                custom_wb_setup_requested=True, **kwargs
            )
            self.assertFalse(gc.passed)
            self.assertTrue(any(P321_CUSTOM_WB_ERROR_RESID16_HEX in e for e in gc.errors))
        gc_ok = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            custom_wb_setup_requested=True,
            log_shooting_mode="OFF",
            picture_profile="OFF",
            wb_mode="CUSTOM_1",
        )
        self.assertTrue(gc_ok.passed, gc_ok.errors)

    def test_57_gc_custom_1_3_excluded_from_camset_and_survive_reset(self) -> None:
        gc1 = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            claimed_custom_wb_saved_in_camset=True
        )
        gc2 = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            claimed_custom_wb_wiped_by_camera_reset=True
        )
        self.assertFalse(gc1.passed)
        self.assertFalse(gc2.passed)

    def test_58_gc_shutter_awb_lock_vs_shockless_wb_reset_split_and_fx6_wht_bal(self) -> None:
        for flag in (
            "claimed_shutter_awb_lock_wiped_by_camera_reset",
            "claimed_shockless_wb_resists_camera_reset",
            "claimed_fx3_has_atw_speed_or_memory_ah",
        ):
            gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(**{flag: True})
            self.assertFalse(gc.passed)

    # ------------------------------------------------------------------
    # 59-79: Check Group D — Movie AF 1..7 & 1..5, External Focus Map, 16-State Marker, Tier-0
    # ------------------------------------------------------------------

    def test_59_gd_af_transition_speed_1_to_7_and_subj_shift_sens_1_to_5(self) -> None:
        gd_ok = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            af_transition_speed=P321_AF_TRANSITION_SPEED_MAX,
            af_subj_shift_sens=P321_AF_SUBJ_SHIFT_SENS_MAX,
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)
        for bad_kwargs in (
            {"af_transition_speed": 0},
            {"af_transition_speed": 8},
            {"af_subj_shift_sens": 0},
            {"af_subj_shift_sens": 6},
            {"af_subj_shift_sens": 7},
            {"fx3_af_subj_shift_7_levels_claimed": True},
            {"fx6_af_subj_shift_7_levels_claimed": True},
        ):
            gd_bad = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(**bad_kwargs)
            self.assertFalse(gd_bad.passed, f"Expected AF bounds failure for {bad_kwargs}")
            self.assertFalse(gd_bad.fx3_af_subj_shift_7_levels_present)

    def test_60_gd_af_assist_incompatible_with_selp1650_and_sel18200le_and_resets(self) -> None:
        for lens in P321_AF_ASSIST_INCOMPATIBLE_LENSES:
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                af_assist="ON", lens_model=lens
            )
            self.assertFalse(gd.passed)
            self.assertTrue(
                any(P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS in e for e in gd.errors)
            )
        gd_rst = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            claimed_af_assist_resists_camera_reset=True
        )
        self.assertFalse(gd_rst.passed)

    def test_61_gd_zero_in_body_focus_map_and_zero_uvc_on_fx3(self) -> None:
        for flag in (
            "in_body_focus_map_requested",
            "fx3_in_body_focus_map_present_claimed",
            "fx3_uvc_streaming_present_claimed",
        ):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(**{flag: True})
            self.assertFalse(gd.passed)
            self.assertFalse(gd.fx3_in_body_focus_map_present)
            self.assertFalse(gd.fx3_uvc_streaming_present)
            self.assertTrue(
                any(P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC in e for e in gd.errors)
            )

    def test_62_gd_mc_focus_map_allowed_at_119_88p_and_blocked_at_150fps_plus(self) -> None:
        gd_119 = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            mc_focus_map_enabled=True, mc_focus_map_fps=119.88
        )
        self.assertTrue(gd_119.passed, gd_119.errors)
        gd_150 = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            mc_focus_map_enabled=True, mc_focus_map_fps=P321_MC_FOCUS_MAP_FPS_CUTOFF
        )
        gd_240 = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            mc_focus_map_enabled=True, mc_focus_map_fps=240.0
        )
        gd_false_120 = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            claimed_mc_focus_map_blocked_at_120p=True
        )
        self.assertFalse(gd_150.passed)
        self.assertFalse(gd_240.passed)
        self.assertFalse(gd_false_120.passed)

    def test_63_gd_mc_focus_map_blocks_wifi_playback_non_pdaf_auto_framing_usb(self) -> None:
        for flag_kwargs in (
            {"mc_focus_map_over_wifi_requested": True},
            {"playback_control_active": True},
            {"lens_pdaf_capable": False},
            {"auto_framing_claimed": True},
            {"usb_remote_or_uvc_active": True},
        ):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                mc_focus_map_enabled=True, mc_focus_map_fps=23.98, **flag_kwargs
            )
            self.assertFalse(gd.passed, f"Expected M&C Focus Map rejection for {flag_kwargs}")

    def test_64_gd_aspect_marker_exact_16_states_and_4color_peaking(self) -> None:
        self.assertEqual(len(P321_ASPECT_MARKER_16_STATES), 16)
        self.assertEqual(P321_ASPECT_MARKER_16_STATES[0], "OFF")
        for ratio in P321_ASPECT_MARKER_16_STATES:
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(aspect_marker=ratio)
            self.assertTrue(gd.passed, f"{ratio}: {gd.errors}")
        for color in P321_FX3_PEAKING_FOUR_COLORS:
            gd_c = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                peaking_display="ON", peaking_color=color
            )
            self.assertTrue(gd_c.passed, gd_c.errors)
        gd_bad_count = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            exposed_aspect_markers=P321_ASPECT_MARKER_16_STATES[:-1]
        )
        gd_bad_color = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            peaking_display="ON", peaking_color="BLACK_WHITE"
        )
        self.assertFalse(gd_bad_count.passed)
        self.assertFalse(gd_bad_color.passed)

    def test_65_gd_marker_peaking_hdmi_isolation_focus_mag_hide_and_reset_survival(self) -> None:
        for kwargs in (
            {"expect_marker_or_peaking_on_hdmi": True},
            {"focus_magnifier_active": True, "expect_marker_visible_during_focus_magnifier": True},
            {"claimed_marker_or_peaking_wiped_by_camera_reset": True},
            {"claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking": True},
        ):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(**kwargs)
            self.assertFalse(gd.passed)
            self.assertTrue(
                any(
                    P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET in e
                    for e in gd.errors
                )
            )

    def test_66_gd_redlines_block_all_tx_and_unauthorized_attach_flags(self) -> None:
        for kwargs in (
            {"e_nd_actuator_tx_count": 1},
            {"wireless_rf_packets_emitted": 1},
            {"slot1_data_sector_writes": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(**kwargs)
            self.assertFalse(gd.passed, f"Expected redline block for {kwargs}")
            self.assertTrue(any(P321_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION in e for e in gd.errors))

    def test_67_gd_h0_h3_drift_detected_via_count_or_baseline_mismatch(self) -> None:
        gd_cnt = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(gd_cnt.passed)
        self.assertEqual(gd_cnt.h0_equals_h3_count, 15)
        self.assertTrue(any(P321_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd_cnt.errors))

        h0 = build_default_h0_baselines(
            body_serial="FX3702BENCH321",
            emmc_cid="150100424a4e42345201020304050607",
        )
        h3 = dict(h0)
        first_key = next(iter(h3.keys()))
        h3[first_key] = "f" * 64
        gd_map = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            h0_baselines_a=h0, h3_baselines=h3
        )
        self.assertFalse(gd_map.passed)
        self.assertEqual(gd_map.h0_equals_h3_count, 15)

    def test_68_gd_single_receipt_copy_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            st_dev_a_override=101,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.receipt_mode, "INVALID_RECEIPT_SINGLE_COPY")

    def test_69_gd_wrong_receipt_length_and_checksum_tamper_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        gd_len = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"][:512],
            receipt_b_bytes=sim["receipt_b_bytes"][:512],
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        bad_bytes = bytearray(sim["receipt_a_bytes"])
        bad_bytes[16] ^= 0xFF
        gd_crc = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=bytes(bad_bytes),
            receipt_b_bytes=bytes(bad_bytes),
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertFalse(gd_len.passed)
        self.assertFalse(gd_crc.passed)

    def test_70_gd_same_st_dev_and_copy_a_b_mismatch_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        gd_dev = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=777,
            st_dev_b_override=777,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        b_alt = bytearray(sim["receipt_b_bytes"])
        b_alt[-1] ^= 0x01
        gd_diff = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=bytes(b_alt),
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertFalse(gd_dev.passed)
        self.assertFalse(gd_diff.passed)

    def test_71_gd_trivial_serial_and_trivial_cid_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        for bad_ser in ("00000000", "TEST", ""):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=101,
                st_dev_b_override=202,
                body_serial=bad_ser,
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
            )
            self.assertFalse(gd.passed)
        for bad_cid in ("0" * 32, "f" * 32, "bad"):
            gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=101,
                st_dev_b_override=202,
                body_serial=sim["body_serial"],
                emmc_cid=bad_cid,
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
            )
            self.assertFalse(gd.passed)

    def test_72_gd_symlink_and_missing_receipt_paths_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            real_a = Path(td) / "a.bin"
            real_a.write_bytes(sim["receipt_a_bytes"])
            sym_b = Path(td) / "sym_b.bin"
            sym_b.symlink_to(real_a)
            gd_sym = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                receipt_a_path=real_a,
                receipt_b_path=sym_b,
                st_dev_a_override=101,
                st_dev_b_override=202,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
            )
            gd_missing = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
                receipt_a_path=Path(td) / "missing_a.bin",
                receipt_b_path=Path(td) / "missing_b.bin",
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
            )
            self.assertFalse(gd_sym.passed)
            self.assertFalse(gd_missing.passed)

    def test_73_gd_missing_or_trivial_h0_baselines_rejected_with_physical_receipts(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        gd_none = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        bad_h0 = dict(sim["h0_baselines_a"])
        first_k = next(iter(bad_h0.keys()))
        bad_h0[first_k] = "0" * 64
        gd_triv = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=bad_h0,
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertFalse(gd_none.passed)
        self.assertFalse(gd_triv.passed)

    # ------------------------------------------------------------------
    # 74-84: Report Verification, Tamper Detection, Determinism, Markdown
    # ------------------------------------------------------------------

    def test_74_verify_phase321_report_detects_all_tampered_fields(self) -> None:
        rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        base = rep.to_dict()
        self.assertTrue(verify_phase321_report(base).valid)
        for field, bad_val in (
            ("schema_version", "tampered_schema"),
            ("sony_help_guide_id", "ilc/9999"),
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("sd_physical_media_written", True),
            ("cross_model_flash_authorized", True),
            ("rf_nvs_p12_p13_writes_authorized", True),
            ("fx3_prioritize_rec_media_present", True),
            ("fx3_movie_sort_recording_present", True),
            ("fx3_mymenu_30_or_36_slots_only", True),
            ("fx3_ftp_sftp_present", True),
            ("fx3_ftp_active_mode_present", True),
            ("fx3_ftp_transfer_jpeg_size_present", True),
            ("fx3_in_body_focus_map_present", True),
            ("fx3_uvc_streaming_present", True),
            ("fx3_af_subj_shift_7_levels_present", True),
            ("e_nd_actuator_tx_count", 1),
            ("e_nd_i2c_tx_bytes", 1),
            ("rf_packets_transmitted", 1),
            ("wireless_rf_packets_emitted", 1),
            ("slot1_data_sector_writes", 1),
            ("usb_packets_transmitted", 1),
            ("passive_tx_bytes_emitted", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("go_no_go", P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED),
            ("report_sha256", "a" * 64),
        ):
            tampered = copy.deepcopy(base)
            tampered[field] = bad_val
            vr = verify_phase321_report(tampered)
            self.assertFalse(vr.valid, f"Expected tamper rejection for {field}={bad_val!r}")

    def test_75_canonical_sha256_ignores_donor_elapsed_seconds(self) -> None:
        rep = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d1 = rep.to_dict()
        d2 = copy.deepcopy(d1)
        d2["donor_inspection"]["elapsed_seconds"] = 999.123
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_76_render_markdown_deterministic_and_contains_all_groups(self) -> None:
        rep = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md1 = render_phase321_markdown(rep)
        md2 = render_phase321_markdown(rep)
        self.assertEqual(md1, md2)
        self.assertIn(P321_SCHEMA, md1)
        self.assertIn("4/4", md1)
        self.assertIn("16/16", md1)
        self.assertIn("6x7=42", md1)
        self.assertIn("`16` states", md1)

    def test_77_group_failure_sets_blocked_verdict_and_verifies_report(self) -> None:
        rep = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            dormant_prioritize_rec_media_requested=True,
            cnct_while_power_off="ON",
            usb_lan_tethering="ON",
            in_body_focus_map_requested=True,
        )
        self.assertEqual(
            rep.go_no_go, P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE
        )
        self.assertEqual(rep.check_groups_passed, 0)
        self.assertGreaterEqual(len(rep.errors), 4)
        self.assertTrue(verify_phase321_report(rep).valid)

    def test_78_determinism_identical_inputs_yield_identical_sha256(self) -> None:
        r1 = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            movie_file_format="XAVC_S_I_DCI_4K",
            movie_bitrate_mbps=600,
            proxy_recording="ON",
            aspect_marker="2.39:1",
            safety_zone="80PCT",
            peaking_display="ON",
            peaking_color="RED",
        )
        r2 = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            movie_file_format="XAVC_S_I_DCI_4K",
            movie_bitrate_mbps=600,
            proxy_recording="ON",
            aspect_marker="2.39:1",
            safety_zone="80PCT",
            peaking_display="ON",
            peaking_color="RED",
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.to_deterministic_json(), r2.to_deterministic_json())

    def test_79_json_roundtrip_deterministic_and_sorted(self) -> None:
        rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        parsed = json.loads(rep.to_deterministic_json())
        self.assertEqual(parsed["schema_version"], P321_SCHEMA)
        self.assertTrue(verify_phase321_report(parsed).valid)

    def test_80_group_a_b_c_d_errors_isolated_to_failing_group_count(self) -> None:
        rep = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            dormant_prioritize_rec_media_requested=True,
            fx3_af_subj_shift_7_levels_claimed=True,
        )
        self.assertFalse(rep.check_group_a.passed)
        self.assertTrue(rep.check_group_b.passed)
        self.assertTrue(rep.check_group_c.passed)
        self.assertFalse(rep.check_group_d.passed)
        self.assertEqual(rep.check_groups_passed, 2)

    def test_81_invalid_reset_action_and_shoot_mode_fail_closed(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            reset_action="FACTORY_FLASH", shoot_mode="TIMELAPSE_RAW"
        )
        self.assertFalse(ga.passed)
        self.assertGreaterEqual(len(ga.errors), 2)

    def test_82_invalid_enum_inputs_across_groups_fail_closed(self) -> None:
        gb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
            cloud_connection="MAYBE", clip_flag_filter="BAD"
        )
        gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
            ftp_transfer_func="AUTO",
            ftp_protocol="WEBDAV",
            wb_mode="FLUORESCENT_UV",
            priority_set_in_awb="CYAN",
            shutter_awb_lock="HALF_ONLY",
            shockless_wb="4_FASTEST",
        )
        gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            af_assist="AUTO",
            aspect_marker="21:10",
            safety_zone="95PCT",
            peaking_display="FLASHING",
            peaking_level="ULTRA",
            peaking_color="GREEN",
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gc.passed)
        self.assertFalse(gd.passed)

    def test_83_model_fw_receipt_mismatch_rejected(self) -> None:
        sim = build_simulated_phase321_tier0_receipts()
        gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_model_id=0x11111111,
            body_fw="6.01",
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertFalse(gd.passed)
        self.assertTrue(
            any(P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in gd.errors)
        )

    def test_84_no_slot1_vault_allows_slot2_or_slot1_without_vault_error(self) -> None:
        ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
            slot1_contains_tier0_dump=False,
            slot1_wp_locked=False,
            recording_media="SLOT_1",
        )
        self.assertTrue(ga.passed, ga.errors)

    # ------------------------------------------------------------------
    # 85-96: Direct CLI & Isolated Subprocess Dual-Mode Verification
    # ------------------------------------------------------------------

    def test_85_cli_help_succeeds_zero_errors_no_percent_crash(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes", proc.stdout)
        self.assertIn("80%", proc.stdout)

    def test_86_cli_clean_room_offline_awaiting_receipt_exits_2(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = fx6_cli_main(
                [
                    "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(data["overall_status"], P321_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertTrue(verify_phase321_report(data).valid)

    def test_87_cli_clean_room_simulate_bench_dry_run_json_exits_0(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = fx6_cli_main(
                [
                    "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["schema_version"], P321_SCHEMA)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertTrue(verify_phase321_report(data).valid)

    def test_88_cli_summary_writes_json_and_markdown_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            json_out = td_path / "p321.json"
            md_out = td_path / "p321.md"
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--summary",
                        "--output",
                        str(json_out),
                        "--markdown-out",
                        str(md_out),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", stdout.getvalue())
            self.assertTrue(json_out.is_file())
            self.assertTrue(md_out.is_file())
            parsed = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase321_report(parsed).valid)
            self.assertIn(P321_SCHEMA, md_out.read_text(encoding="utf-8"))

    def test_89_cli_negative_flags_group_a_b_c_d_exit_2(self) -> None:
        for extra_flags in (
            ["--dormant-prioritize-rec-media-requested"],
            ["--recording-media", "SLOT_1"],
            ["--auto-switch-media", "ON"],
            ["--proxy-slot1-write-or-coupled-delete-requested"],
            ["--cnct-while-power-off", "ON"],
            ["--mymenu-total-slots", "36"],
            ["--ftp-protocol", "SFTP"],
            ["--ftp-active-mode-requested"],
            ["--usb-lan-tethering", "ON"],
            ["--in-body-focus-map-requested"],
            ["--fx6-af-subj-shift-7-levels-claimed"],
        ):
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        *extra_flags,
                    ]
                )
            self.assertEqual(rc, 2, f"Expected exit 2 for {extra_flags}")
            data = json.loads(stdout.getvalue())
            self.assertEqual(
                data["go_no_go"],
                P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE,
            )
            self.assertTrue(verify_phase321_report(data).valid)

    def test_90_cli_exposed_aspect_markers_override_valid_and_invalid(self) -> None:
        stdout_ok = io.StringIO()
        with mock.patch("sys.stdout", stdout_ok):
            rc_ok = fx6_cli_main(
                [
                    "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--exposed-aspect-markers",
                    ",".join(P321_ASPECT_MARKER_16_STATES),
                ]
            )
        self.assertEqual(rc_ok, 0)
        stdout_bad = io.StringIO()
        with mock.patch("sys.stdout", stdout_bad):
            rc_bad = fx6_cli_main(
                [
                    "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--exposed-aspect-markers",
                    "OFF,16:9,2.39:1",
                ]
            )
        self.assertEqual(rc_bad, 2)

    def test_91_cli_subprocess_forced_clean_room_dry_run_exits_0(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase321_report(data).valid)

    def test_92_cli_subprocess_offline_default_exits_2(self) -> None:
        proc = _run_cli_subprocess(["--json"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase321_report(data).valid)

    def test_93_cli_dci4k_60p_with_proxy_and_mc_focus_map_119_88p_passes(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = fx6_cli_main(
                [
                    "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--movie-file-format",
                    "XAVC_S_I_DCI_4K",
                    "--movie-bitrate-mbps",
                    "600",
                    "--rec-fps",
                    "59.94",
                    "--proxy-recording",
                    "ON",
                    "--mc-focus-map-enabled",
                    "--mc-focus-map-fps",
                    "119.88",
                    "--aspect-marker",
                    "2.39:1",
                ]
            )
        self.assertEqual(rc, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)

    def test_94_cli_negative_redline_authorize_claims_exit_2(self) -> None:
        for flag in (
            "--claim-hardware-live-attach-authorized",
            "--claim-persistent-emmc-writes-authorized",
            "--claim-cross-model-flash-authorized",
        ):
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        flag,
                    ]
                )
            self.assertEqual(rc, 2)
            data = json.loads(stdout.getvalue())
            self.assertFalse(data["hardware_live_attachment_authorized"])
            self.assertFalse(data["persistent_emmc_writes_authorized"])
            self.assertFalse(data["cross_model_flash_authorized"])

    def test_95_cli_physical_receipt_same_volume_rejected_exit_2(self) -> None:
        ser = "FX3702BENCH321"
        cid = "150100424a4e42345201020304050607"
        sim = build_simulated_phase321_tier0_receipts(body_serial=ser, emmc_cid=cid)
        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "a.bin"
            p_b = Path(td) / "b.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                        "--force-clean-room",
                        "--json",
                        "--receipt-a",
                        str(p_a),
                        "--receipt-b",
                        str(p_b),
                        "--body-serial",
                        ser,
                        "--emmc-cid",
                        cid,
                    ]
                )
        self.assertEqual(rc, 2)
        data = json.loads(stdout.getvalue())
        self.assertFalse(data["tier0_receipt_verified"])

    def test_96_cli_markdown_only_output_writes_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            md_path = Path(td) / "phase321_cert.md"
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            content = md_path.read_text(encoding="utf-8")
            self.assertIn("Phase 321", content)
            self.assertIn("16/16", content)


if __name__ == "__main__":
    unittest.main()
