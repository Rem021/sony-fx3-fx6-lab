"""Dual-mode unit tests (86 cases) for Phase 307 (`preflight-dial-customize-lut-embed-steadyshot-and-streaming`):
12th Real-Hardware Physical Bench Readiness Verifier across Waves 56-57 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `15.0s` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
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
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_dial_customize_lut_embed_steadyshot_and_streaming_verifier import (  # noqa: E402
    P307_ACTIVE_LOCKOUT_MIN_FPS,
    P307_CHECK_GROUP_A_ID,
    P307_CHECK_GROUP_B_ID,
    P307_CHECK_GROUP_C_ID,
    P307_CHECK_GROUP_D_ID,
    P307_DIAL_CUSTOMIZE_FIVE_ITEMS,
    P307_DIAL_CUSTOMIZE_LEGACY_SYMBOLS,
    P307_DORMANT_DYNAMIC_ACTIVE_RESID16_HEX,
    P307_DORMANT_MOVIE_SELFTIMER_RESID16_HEX,
    P307_DORMANT_REAR_DIAL_LR_RESIDS,
    P307_EMBED_LUT_RESID16_HEX,
    P307_EMBED_LUT_SDHC_LOCK_RESID16_HEX,
    P307_ERRNO_EBUSY,
    P307_ERRNO_EOPNOTSUPP,
    P307_ERRNO_EROFS,
    P307_FN_MENU_MOVIE_SLOTS,
    P307_FN_MENU_STILL_SLOTS,
    P307_FORBIDDEN_STREAMING_FPS,
    P307_FTP_TRANSFER_FUNC_RESID16_HEX,
    P307_FX3_THREE_PHYSICAL_DIALS,
    P307_FX6_IBIS_UNSUPPORTED_ENUM,
    P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP,
    P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID,
    P307_GA_ERR_MODEL_OR_FW_FLOOR,
    P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12,
    P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT,
    P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE,
    P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL,
    P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI,
    P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET,
    P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF,
    P307_GC_ERR_STREAMING_OR_FTP_SLOT1_VAULT_FIREWALL,
    P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL,
    P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P307_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE,
    P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED,
    P307_GRID_LINE_THREE_TYPES,
    P307_LIVE_VIEW_DISPLAY_SUBITEMS,
    P307_MOVIE_REC_DURING_STREAMING_RESID16_HEX,
    P307_MY_DIAL_SLOTS,
    P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P307_PEAKING_FOUR_COLORS,
    P307_PEAKING_THREE_LEVELS,
    P307_PPLUT_PROFILES,
    P307_SCHEMA,
    P307_SONY_HELP_GUIDE_ID,
    P307_STEADYSHOT_47_FOCAL_LENGTHS_MM,
    P307_STREAMING_RESID16_HEX,
    P307_USER_LUT_CFEXPRESS_DIR,
    P307_USER_LUT_CUBE_SIZES,
    P307_USER_LUT_MAX_FILENAME_CHARS,
    P307_USER_LUT_SD_DIR,
    P307_VALID_STREAMING_FPS,
    P307_VALID_STREAMING_PROTOCOLS,
    P307_VERSION,
    P307_ZEBRA_CUSTOM_SLOTS,
    P307_ZEBRA_CUSTOM_TYPES,
    P307_ZEBRA_FIXED_PRESETS,
    PHASE_307_CHECK_GROUP_IDS,
    PHASE307_PASSIVE_TX_BYTES_EMITTED,
    PHASE307_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE_307_SCHEMA,
    PHASE307_SLOT1_DATA_SECTOR_WRITES,
    PHASE307_USB_PACKETS_TRANSMITTED,
    PHASE_307_VERSION,
    PHASE307_WIRELESS_RF_PACKETS_EMITTED,
    RealHwDialCustomizeLutEmbedSteadyshotStreamingReport,
    _canonical_sha256_dict,
    build_simulated_phase307_tier0_receipts,
    evaluate_p307_check_group_a_dial_customize_liveview_grid_lut,
    evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking,
    evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall,
    evaluate_p307_check_group_d_physical_bench_and_tier0,
    evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness,
    inspect_phase307_donors_bounded,
    render_phase307_markdown,
    run_dial_customize_lut_embed_steadyshot_and_streaming_preflight,
    verify_phase307_report,
)


def _timing_budget(base_sec: float) -> float:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return base_sec + 15.0
    return base_sec


def _pythonpath_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(REPO_ROOT / rel)
        for rel in (
            "outputs/fx6-on-fx3-closure",
            "outputs/fx3-safety",
            "outputs/fx3-recovery-adapter",
            "outputs/fx3-firmware-lab",
            "outputs/fx3-vm",
        )
    )
    if extra:
        env.update(extra)
    return env


def _run_cli_subprocess(
    args: list[str], *, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "fx6_closure",
            "preflight-dial-customize-lut-embed-steadyshot-and-streaming",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=_pythonpath_env(extra_env),
        capture_output=True,
        text=True,
        timeout=_timing_budget(20.0),
        check=False,
    )


class TestPhase307DialCustomizeLutEmbedSteadyShotAndStreamingVerifier(unittest.TestCase):
    """86 dual-mode unit tests covering Phase 307 Waves 56-57 physical bench verifier."""

    # ------------------------------------------------------------------
    # 01-08: Exports, Constants & Bounded Donor Inspection
    # ------------------------------------------------------------------

    def test_01_package_all_exports_and_non_duplicate_contract(self) -> None:
        self.assertEqual(len(fx6_closure.__all__), len(set(fx6_closure.__all__)))
        for sym in (
            "PHASE_307_SCHEMA",
            "P307_SCHEMA",
            "P307_SONY_HELP_GUIDE_ID",
            "P307_DIAL_CUSTOMIZE_FIVE_ITEMS",
            "P307_FX3_THREE_PHYSICAL_DIALS",
            "P307_STEADYSHOT_47_FOCAL_LENGTHS_MM",
            "evaluate_p307_check_group_a_dial_customize_liveview_grid_lut",
            "evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking",
            "evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall",
            "evaluate_p307_check_group_d_physical_bench_and_tier0",
            "evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness",
            "run_dial_customize_lut_embed_steadyshot_and_streaming_preflight",
            "verify_phase307_report",
            "render_phase307_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_02_module_constants_and_redline_zeroes(self) -> None:
        self.assertEqual(
            PHASE_307_SCHEMA, "realhw_dial_customize_lut_embed_steadyshot_and_streaming_verifier_v1"
        )
        self.assertEqual(P307_SCHEMA, PHASE_307_SCHEMA)
        self.assertEqual(PHASE_307_VERSION, "307.0.0")
        self.assertEqual(P307_VERSION, "307.0.0")
        self.assertEqual(P307_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(PHASE307_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE307_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE307_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE307_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE307_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(P307_ERRNO_EBUSY, 16)
        self.assertEqual(P307_ERRNO_EROFS, 30)
        self.assertEqual(P307_ERRNO_EOPNOTSUPP, 95)

    def test_03_check_group_ids_exact_four(self) -> None:
        self.assertEqual(len(PHASE_307_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_307_CHECK_GROUP_IDS,
            (
                P307_CHECK_GROUP_A_ID,
                P307_CHECK_GROUP_B_ID,
                P307_CHECK_GROUP_C_ID,
                P307_CHECK_GROUP_D_ID,
            ),
        )

    def test_04_donor_inspection_synthetic_clean_room_fast(self) -> None:
        t0 = time.perf_counter()
        res = inspect_phase307_donors_bounded(synthetic_clean_room=True)
        dt = time.perf_counter() - t0
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(res.within_150ms_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.appfw_is_aarch64_elf)
        self.assertTrue(res.upm_ko_is_aarch64_elf)
        self.assertEqual(res.errors, ())
        self.assertLessEqual(dt, _timing_budget(1.0))

    def test_05_donor_inspection_respects_clean_room_env_and_local_donor_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            r_cr = inspect_phase307_donors_bounded()
            self.assertTrue(r_cr.passed)
            self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r_force = inspect_phase307_donors_bounded()
            self.assertTrue(r_force.passed)
            self.assertEqual(r_force.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        r_auto = inspect_phase307_donors_bounded(force_clean_room=None)
        self.assertTrue(r_auto.passed)
        self.assertIn(r_auto.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(r_auto.raw_firmware_bytes_leaked, 0)

    def test_06_donor_inspection_missing_donors_forced_local_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bogus = Path(td) / "nonexistent"
            res = inspect_phase307_donors_bounded(
                fx6_lib_dir=bogus,
                fx3_modules_dir=bogus,
                force_clean_room=False,
            )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(any("missing" in e.lower() for e in res.errors))

    def test_07_top_level_alias_points_to_orchestrator(self) -> None:
        self.assertIs(
            run_dial_customize_lut_embed_steadyshot_and_streaming_preflight,
            evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness,
        )

    def test_08_canonical_sha256_excludes_report_sha256_and_elapsed_seconds(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True
        )
        d1 = rep.to_dict()
        d2 = copy.deepcopy(d1)
        d2["report_sha256"] = "0" * 64
        d2["donor_inspection"]["elapsed_seconds"] = 99.123
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    # ------------------------------------------------------------------
    # 09-30: Check Group A (Wave 56)
    # ------------------------------------------------------------------

    def test_09_ga_default_nominal_passes(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut()
        self.assertTrue(ga.passed)
        self.assertEqual(ga.check_group_id, P307_CHECK_GROUP_A_ID)
        self.assertEqual(ga.sony_help_guide_id, "ilc/2210")
        self.assertEqual(ga.dial_customize_item_count, 5)
        self.assertEqual(ga.fx3_physical_dial_count, 3)
        self.assertFalse(ga.fx3_four_dial_rear_lr_present)
        self.assertTrue(ga.dormant_dial_symbols_rejected)
        self.assertTrue(ga.my_dial_lock_override_verified)
        self.assertEqual(ga.fn_menu_still_slots, 12)
        self.assertEqual(ga.fn_menu_movie_slots, 12)
        self.assertTrue(ga.slot1_lut_vault_firewall_enforced)
        self.assertEqual(ga.slot1_data_sector_writes, 0)
        self.assertEqual(ga.errors, ())

    def test_10_ga_rejects_bad_model_fw_below_204_and_wrong_help_guide_id(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            body_model_id=0xDEADBEEF,
            body_fw="1.01",
            sony_help_guide_id="ilc/1999",
            reset_action="BAD_RESET",
            shoot_mode="BAD_SHOOT",
        )
        self.assertFalse(ga.passed)
        err_blob = "\n".join(ga.errors)
        self.assertIn(P307_GA_ERR_MODEL_OR_FW_FLOOR, err_blob)
        self.assertGreaterEqual(len(ga.errors), 5)

    def test_11_ga_exact_5_dial_customize_items_and_reject_missing_item(self) -> None:
        self.assertEqual(len(P307_DIAL_CUSTOMIZE_FIVE_ITEMS), 5)
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            exposed_dial_customize_items=P307_DIAL_CUSTOMIZE_FIVE_ITEMS[:4]
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(
            any(P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP in e for e in ga_bad.errors)
        )

    def test_12_ga_rejects_legacy_v1_dial_setup_and_dial_wheel_lock_traps(self) -> None:
        for legacy in P307_DIAL_CUSTOMIZE_LEGACY_SYMBOLS:
            ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
                exposed_dial_customize_items=(legacy,) + P307_DIAL_CUSTOMIZE_FIVE_ITEMS[1:]
            )
            self.assertFalse(ga.passed)
            self.assertFalse(ga.dormant_dial_symbols_rejected)
        ga_flag = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            dormant_dial_setup_or_wheel_lock_requested=True
        )
        self.assertFalse(ga_flag.passed)
        self.assertFalse(ga_flag.dormant_dial_symbols_rejected)
        self.assertTrue(any("EOPNOTSUPP=95" in e for e in ga_flag.errors))

    def test_13_ga_av_tv_rotate_function_ring_lens_and_lock_operation_parts(self) -> None:
        ga_ok = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            av_tv_rotate="REVERSE",
            function_ring_lens="APSC_S35_FF",
            lock_operation_parts="DIAL_PLUS_WHEEL",
        )
        self.assertTrue(ga_ok.passed)
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            av_tv_rotate="MIRROR",
            function_ring_lens="IRIS",
            lock_operation_parts="HALF",
        )
        self.assertFalse(ga_bad.passed)
        self.assertEqual(len(ga_bad.errors), 3)

    def test_14_ga_dial_customize_initialize_only_and_rejects_fx6_topology(self) -> None:
        ga_reset_ok = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_dial_customize_wiped_by_camera_reset=False,
        )
        self.assertTrue(ga_reset_ok.passed)
        ga_reset_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_dial_customize_wiped_by_camera_reset=True,
        )
        self.assertFalse(ga_reset_bad.passed)
        ga_fx6 = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            fx6_dial_topology_claimed=True
        )
        self.assertFalse(ga_fx6.passed)

    def test_15_ga_exact_3_physical_dials_passes_and_rejects_missing_dial(self) -> None:
        self.assertEqual(P307_FX3_THREE_PHYSICAL_DIALS, ("FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"))
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            exposed_physical_dials=("FRONT_DIAL", "CONTROL_WHEEL")
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(
            any(P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12 in e for e in ga_bad.errors)
        )

    def test_16_ga_rejects_dormant_4dial_rear_dial_lr_phantom_0x6a5c_0x680d(self) -> None:
        self.assertEqual(P307_DORMANT_REAR_DIAL_LR_RESIDS, ("0x6a5c", "0x680d"))
        for kwargs in (
            {"fx3_four_dial_rear_lr_present": True},
            {"dormant_rear_dial_lr_requested": True},
            {"exposed_physical_dials": ("FRONT_DIAL", "REAR_DIAL_L", "REAR_DIAL_R", "CONTROL_WHEEL")},
        ):
            ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(**kwargs)
            self.assertFalse(ga.passed)
            self.assertFalse(ga.dormant_dial_symbols_rejected)
            self.assertFalse(ga.fx3_four_dial_rear_lr_present)
            self.assertTrue(any("0x6a5c" in e and "0x680d" in e for e in ga.errors))

    def test_17_ga_my_dial_1_to_3_override_lock_and_reject_slot_4(self) -> None:
        for slot in P307_MY_DIAL_SLOTS:
            ga_ok = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
                my_dial_slot=slot,
                my_dial_active_recalled=True,
                lock_operation_parts="ALL",
                expect_lock_blocks_recalled_my_dial=False,
            )
            self.assertTrue(ga_ok.passed)
            self.assertTrue(ga_ok.my_dial_lock_override_verified)
        ga_bad_slot = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(my_dial_slot=4)
        self.assertFalse(ga_bad_slot.passed)
        ga_bad_lock = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            my_dial_active_recalled=True,
            lock_operation_parts="DIAL_PLUS_WHEEL",
            expect_lock_blocks_recalled_my_dial=True,
        )
        self.assertFalse(ga_bad_lock.passed)
        self.assertFalse(ga_bad_lock.my_dial_lock_override_verified)

    def test_18_ga_fn_menu_12_still_plus_12_movie_split_and_reject_not_set_trap(self) -> None:
        self.assertEqual(P307_FN_MENU_STILL_SLOTS, 12)
        self.assertEqual(P307_FN_MENU_MOVIE_SLOTS, 12)
        ga_split = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            fn_menu_still_slots=10, fn_menu_movie_slots=12
        )
        self.assertFalse(ga_split.passed)
        ga_notset = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            fn_menu_all_not_set_claimed=True
        )
        self.assertFalse(ga_notset.passed)
        self.assertTrue(any("0x6220" in e for e in ga_notset.errors))

    def test_19_ga_live_view_3_subitems_and_bright_monitoring_forces_setting_effect_off(self) -> None:
        self.assertEqual(len(P307_LIVE_VIEW_DISPLAY_SUBITEMS), 3)
        ga_ok = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            bright_monitoring_active=True,
            live_view_display="SETTING_EFFECT_OFF",
        )
        self.assertTrue(ga_ok.passed)
        self.assertTrue(ga_ok.bright_monitoring_active)

        ga_bad_on = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            bright_monitoring_active=True,
            live_view_display="SETTING_EFFECT_ON",
        )
        self.assertFalse(ga_bad_on.passed)
        self.assertTrue(
            any(P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID in e for e in ga_bad_on.errors)
        )

        ga_bad_sub = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            exposed_live_view_subitems=("LIVE_VIEW_DISPLAY", "EXPOSURE_EFFECT")
        )
        self.assertFalse(ga_bad_sub.passed)

    def test_20_ga_live_view_reset_boundary_two_items_survive_camera_reset(self) -> None:
        ga_ok = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_live_view_two_items_wiped_by_camera_reset=False,
        )
        self.assertTrue(ga_ok.passed)
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_live_view_two_items_wiped_by_camera_reset=True,
        )
        self.assertFalse(ga_bad.passed)

    def test_21_ga_grid_line_3_types_clean_hdmi_isolated_and_rejects_fx6_png(self) -> None:
        for gtype in P307_GRID_LINE_THREE_TYPES:
            ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
                grid_line_display="ON",
                grid_line_type=gtype,
            )
            self.assertTrue(ga.passed)
            self.assertTrue(ga.grid_clean_hdmi_isolated)
        ga_hdmi = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            grid_line_display="ON",
            expect_grid_line_on_clean_hdmi=True,
        )
        self.assertFalse(ga_hdmi.passed)
        self.assertFalse(ga_hdmi.grid_clean_hdmi_isolated)
        ga_png = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            dormant_fx6_custom_png_grid_requested=True
        )
        self.assertFalse(ga_png.passed)

    def test_22_ga_user_lut_import_cfexpress_and_sdxc_read_only_valid_paths(self) -> None:
        ga_cf = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            user_lut_slot=16,
            user_lut_import_requested=True,
            user_lut_source_media_type="CFEXPRESS_A",
            user_lut_source_dir=P307_USER_LUT_CFEXPRESS_DIR,
            user_lut_filename="SLog3_Cine709_33.cube",
            user_lut_cube_size=33,
        )
        self.assertTrue(ga_cf.passed)
        self.assertTrue(ga_cf.user_lut_readonly_import_safe)

        ga_sd = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            user_lut_slot=1,
            user_lut_import_requested=True,
            user_lut_source_media_type="SDXC",
            user_lut_source_dir=P307_USER_LUT_SD_DIR,
            user_lut_filename="ShowLUT_17pt.cube",
            user_lut_cube_size=17,
        )
        self.assertTrue(ga_sd.passed)

    def test_23_ga_user_lut_rejects_bad_slot_ext_64chars_grid_and_dir_mismatch(self) -> None:
        self.assertEqual(P307_USER_LUT_MAX_FILENAME_CHARS, 63)
        self.assertEqual(P307_USER_LUT_CUBE_SIZES, (17, 33))
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            user_lut_slot=17,
            user_lut_import_requested=True,
            user_lut_source_media_type="CFEXPRESS_A",
            user_lut_source_dir="/Private/Sony/PRO/LUT",
            user_lut_filename=("a" * 60) + ".txt",
            user_lut_cube_size=65,
        )
        self.assertFalse(ga_bad.passed)
        self.assertGreaterEqual(len(ga_bad.errors), 5)

    def test_24_ga_embed_lut_file_on_cfexpress_and_sdxc_passes_non_pixel_baking(self) -> None:
        for media in ("CFEXPRESS_A", "SDXC"):
            ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
                log_shooting_mode="CINE_EI_QUICK",
                embed_lut_file="ON",
                embed_lut_media_type=media,
            )
            self.assertTrue(ga.passed)
            self.assertEqual(ga.embed_lut_file, "ON")

    def test_25_ga_embed_lut_file_locked_off_on_sdhc_0x61a0(self) -> None:
        ga_bad = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            embed_lut_file="ON",
            embed_lut_media_type="SDHC",
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(
            any(P307_EMBED_LUT_RESID16_HEX in e and P307_EMBED_LUT_SDHC_LOCK_RESID16_HEX in e for e in ga_bad.errors)
        )
        ga_off = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            embed_lut_file="OFF",
            embed_lut_media_type="SDHC",
        )
        self.assertTrue(ga_off.passed)

    def test_26_ga_rejects_embed_lut_under_color_tone_or_pixel_baking_claim(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            claimed_embed_lut_under_color_tone=True,
            expect_embed_lut_bakes_pixels=True,
        )
        self.assertFalse(ga.passed)
        self.assertEqual(len(ga.errors), 2)

    def test_27_ga_pplut1_to_4_movie_only_irreversible_baking_and_reset_clear(self) -> None:
        for pplut in P307_PPLUT_PROFILES:
            ga_mv = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
                shoot_mode="MOVIE",
                picture_profile=pplut,
            )
            self.assertTrue(ga_mv.passed)
        ga_still = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            shoot_mode="PHOTO",
            picture_profile="PPLUT1",
            expect_pplut_preserves_unbaked_slog3=True,
            claimed_pplut_survives_reset=True,
        )
        self.assertFalse(ga_still.passed)
        self.assertEqual(len(ga_still.errors), 3)

    def test_28_ga_slot1_tier0_vault_blocks_user_lut_writeback_fail_closed_erofs30(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            user_lut_config_writeback_to_slot1=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.user_lut_readonly_import_safe)
        self.assertFalse(ga.slot1_lut_vault_firewall_enforced)
        self.assertEqual(ga.slot1_data_sector_writes, 0)
        self.assertTrue(any(P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT in e for e in ga.errors))

    def test_29_ga_slot1_tier0_vault_blocks_embed_lut_or_pplut_rec_slot1_erofs30(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            embed_lut_or_pplut_rec_requested=True,
            rec_target_slot=1,
            slot1_wp_locked=True,
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.slot1_lut_vault_firewall_enforced)
        self.assertTrue(any("EROFS=30" in e for e in ga.errors))

    def test_30_ga_rec_to_slot2_allowed_with_slot1_vault_locked(self) -> None:
        ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
            embed_lut_or_pplut_rec_requested=True,
            rec_target_slot=2,
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=True,
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.slot1_lut_vault_firewall_enforced)
        self.assertEqual(ga.slot1_data_sector_writes, 0)

    # ------------------------------------------------------------------
    # 31-52: Check Group B (Wave 57 §§1-3)
    # ------------------------------------------------------------------

    def test_31_gb_default_nominal_passes(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking()
        self.assertTrue(gb.passed)
        self.assertEqual(gb.check_group_id, P307_CHECK_GROUP_B_ID)
        self.assertEqual(gb.focal_length_table_count, 47)
        self.assertTrue(gb.dormant_dynamic_active_rejected)
        self.assertTrue(gb.steadyshot_active_4lock_enforced)
        self.assertTrue(gb.fx3_builtin_5axis_ibis_present)
        self.assertFalse(gb.fx6_builtin_ibis_present)
        self.assertFalse(gb.fx3_movie_selftimer_present)
        self.assertTrue(gb.dormant_movie_selftimer_rejected)
        self.assertEqual(gb.errors, ())

    def test_32_gb_steadyshot_active_passes_when_unlocked_and_distortion_comp_auto(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_mode="ACTIVE",
            distortion_comp="AUTO",
            rec_fps=23.98,
            sq_mode_enabled=False,
            hdmi_raw_output=False,
            desqueeze_display="OFF",
        )
        self.assertTrue(gb.passed)
        self.assertTrue(gb.steadyshot_active_4lock_enforced)

    def test_33_gb_steadyshot_active_requires_distortion_comp_auto(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_mode="ACTIVE",
            distortion_comp="OFF",
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any("Distortion Comp." in e for e in gb.errors))

    def test_34_gb_steadyshot_active_lockout_1_high_fps_11988_and_100(self) -> None:
        self.assertEqual(P307_ACTIVE_LOCKOUT_MIN_FPS, 100.0)
        for fps in (100.0, 119.88):
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                steadyshot_mode="ACTIVE",
                distortion_comp="AUTO",
                rec_fps=fps,
            )
            self.assertFalse(gb.passed)
            self.assertFalse(gb.steadyshot_active_4lock_enforced)

    def test_35_gb_steadyshot_active_lockout_2_sq_ge_100_120fps(self) -> None:
        for sq_fps in (100.0, 120.0):
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                steadyshot_mode="ACTIVE",
                distortion_comp="AUTO",
                sq_mode_enabled=True,
                sq_fps=sq_fps,
            )
            self.assertFalse(gb.passed)
            self.assertFalse(gb.steadyshot_active_4lock_enforced)

    def test_36_gb_steadyshot_active_lockout_3_hdmi_raw_output_on(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_mode="ACTIVE",
            distortion_comp="AUTO",
            hdmi_raw_output=True,
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gb.steadyshot_active_4lock_enforced)

    def test_37_gb_steadyshot_active_lockout_4_desqueeze_display_1_3x_to_2_0x(self) -> None:
        for ratio in ("1.3x", "1.5x", "1.6x", "1.8x", "2.0x"):
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                steadyshot_mode="ACTIVE",
                distortion_comp="AUTO",
                desqueeze_display=ratio,
            )
            self.assertFalse(gb.passed)
            self.assertFalse(gb.steadyshot_active_4lock_enforced)

    def test_38_gb_rejects_dormant_dynamic_active_0x741c_eopnotsupp95(self) -> None:
        self.assertEqual(P307_DORMANT_DYNAMIC_ACTIVE_RESID16_HEX, "0x741c")
        for kwargs in (
            {"dormant_dynamic_active_requested": True},
            {"steadyshot_mode": "DYNAMIC_ACTIVE"},
        ):
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(**kwargs)
            self.assertFalse(gb.passed)
            self.assertFalse(gb.dormant_dynamic_active_rejected)
            self.assertTrue(any("0x741c" in e and "EOPNOTSUPP=95" in e for e in gb.errors))

    def test_39_gb_exact_47_entry_focal_length_table_8_to_1000mm(self) -> None:
        self.assertEqual(len(P307_STEADYSHOT_47_FOCAL_LENGTHS_MM), 47)
        self.assertEqual(P307_STEADYSHOT_47_FOCAL_LENGTHS_MM[0], 8)
        self.assertEqual(P307_STEADYSHOT_47_FOCAL_LENGTHS_MM[-1], 1000)
        for mm in (8, 35, 50, 85, 200, 1000):
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                steadyshot_adjust="MANUAL",
                steadyshot_focal_mm=mm,
            )
            self.assertTrue(gb.passed)
            self.assertEqual(gb.steadyshot_focal_mm, mm)

    def test_40_gb_rejects_wrong_focal_table_or_out_of_table_focal_mm(self) -> None:
        gb_short = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            exposed_focal_length_table=P307_STEADYSHOT_47_FOCAL_LENGTHS_MM[:46]
        )
        self.assertFalse(gb_short.passed)
        gb_bad_mm = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_adjust="MANUAL",
            steadyshot_focal_mm=42,
        )
        self.assertFalse(gb_bad_mm.passed)

    def test_41_gb_fx3_has_5axis_ibis_and_rejects_fx6_builtin_ibis_claim(self) -> None:
        gb_no_fx3 = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            fx3_builtin_5axis_ibis_present=False
        )
        self.assertFalse(gb_no_fx3.passed)
        gb_fx6 = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            fx6_builtin_ibis_claimed=True
        )
        self.assertFalse(gb_fx6.passed)
        self.assertFalse(gb_fx6.fx6_builtin_ibis_present)
        self.assertTrue(any(P307_FX6_IBIS_UNSUPPORTED_ENUM in e for e in gb_fx6.errors))

    def test_42_gb_rejects_dormant_movie_selftimer_0x7192_eopnotsupp95(self) -> None:
        self.assertEqual(P307_DORMANT_MOVIE_SELFTIMER_RESID16_HEX, "0x7192")
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            dormant_movie_selftimer_requested=True
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gb.fx3_movie_selftimer_present)
        self.assertFalse(gb.dormant_movie_selftimer_rejected)
        self.assertTrue(any("0x7192" in e and "EOPNOTSUPP=95" in e for e in gb.errors))

    def test_43_gb_still_selftimer_with_front_led8_blink_passes_and_rejects_movie(self) -> None:
        for mode in ("SELF_TIMER_SINGLE", "SELF_TIMER_CONT", "BRACKET"):
            gb_ok = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                shoot_mode="PHOTO",
                still_drive_mode=mode,
                front_led8_selftimer_blink_expected=True,
            )
            self.assertTrue(gb_ok.passed)
        gb_bad_movie = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            shoot_mode="MOVIE",
            still_drive_mode="SELF_TIMER_SINGLE",
            front_led8_selftimer_blink_expected=True,
        )
        self.assertFalse(gb_bad_movie.passed)

    def test_44_gb_silent_mode_on_suppresses_audio_signals_to_off(self) -> None:
        gb_ok = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            silent_mode="ON",
            audio_signals="OFF",
        )
        self.assertTrue(gb_ok.passed)
        gb_bad = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            silent_mode="ON",
            audio_signals="ON",
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(
            any(P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE in e for e in gb_bad.errors)
        )

    def test_45_gb_rejects_dormant_audio_volume_reset_claim_and_fx6_cache_rec(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            reset_action="CAMERA_SETTINGS_RESET",
            dormant_audio_signal_volume_requested=True,
            claimed_audio_signals_wiped_by_camera_reset=True,
            fx6_picture_cache_or_interval_rec_in_fx3_claimed=True,
        )
        self.assertFalse(gb.passed)
        self.assertEqual(len(gb.errors), 3)

    def test_46_gb_zebra_fixed_presets_and_custom1_std_range_0_to_109_pm_1_to_10(self) -> None:
        for preset in P307_ZEBRA_FIXED_PRESETS:
            gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                zebra_display="ON",
                zebra_preset=preset,
            )
            self.assertTrue(gb.passed)
        gb_c1 = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            zebra_display="ON",
            zebra_preset="CUSTOM_1",
            zebra_custom_slot="CUSTOM_1",
            zebra_custom_type="STD_RANGE",
            zebra_level_ire=55,
            zebra_range_plus_minus=10,
        )
        self.assertTrue(gb_c1.passed)
        self.assertEqual(gb_c1.zebra_level_spec, "CUSTOM_1(55+-10)")

    def test_47_gb_zebra_custom2_lower_limit_and_rejects_out_of_range_ire_or_pm(self) -> None:
        gb_c2 = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            zebra_display="ON",
            zebra_preset="CUSTOM_2",
            zebra_custom_slot="CUSTOM_2",
            zebra_custom_type="LOWER_LIMIT",
            zebra_level_ire=109,
        )
        self.assertTrue(gb_c2.passed)
        gb_bad = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            zebra_display="ON",
            zebra_preset="CUSTOM_1",
            zebra_custom_type="STD_RANGE",
            zebra_level_ire=110,
            zebra_range_plus_minus=11,
        )
        self.assertFalse(gb_bad.passed)
        self.assertEqual(len(gb_bad.errors), 2)

    def test_48_gb_peaking_4_colors_passes_and_rejects_fx6_bw_spoof(self) -> None:
        self.assertEqual(P307_PEAKING_FOUR_COLORS, ("RED", "YELLOW", "BLUE", "WHITE"))
        for lvl in P307_PEAKING_THREE_LEVELS:
            for col in P307_PEAKING_FOUR_COLORS:
                gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
                    peaking_display="ON",
                    peaking_level=lvl,
                    peaking_color=col,
                )
                self.assertTrue(gb.passed)
        gb_bw = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            peaking_display="ON",
            peaking_color="BW",
        )
        self.assertFalse(gb_bw.passed)
        self.assertTrue(
            any(P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI in e for e in gb_bw.errors)
        )

    def test_49_gb_rejects_zebra_peaking_clean_hdmi_fx6_both_and_camera_reset_wipe(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            reset_action="CAMERA_SETTINGS_RESET",
            expect_zebra_or_peaking_on_clean_hdmi=True,
            fx6_zebra_both_mode_claimed=True,
            claimed_zebra_peaking_wiped_by_camera_reset=True,
        )
        self.assertFalse(gb.passed)
        self.assertEqual(len(gb.errors), 3)

    def test_50_gb_invalid_enum_values_fail_closed(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_adjust="WARP",
            desqueeze_display="3.0x",
            still_drive_mode="HYPER_BURST",
            silent_mode="MAYBE",
            audio_signals="LOUD",
            zebra_display="ALWAYS",
            zebra_preset="CUSTOM_9",
            zebra_custom_slot="CUSTOM_3",
            zebra_custom_type="PEAK",
            peaking_display="ALWAYS",
            peaking_level="ULTRA",
        )
        self.assertFalse(gb.passed)
        self.assertGreaterEqual(len(gb.errors), 11)

    def test_51_gb_sq_below_100fps_allows_steadyshot_active(self) -> None:
        gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            steadyshot_mode="ACTIVE",
            distortion_comp="AUTO",
            sq_mode_enabled=True,
            sq_fps=60.0,
        )
        self.assertTrue(gb.passed)
        self.assertTrue(gb.steadyshot_active_4lock_enforced)

    def test_52_gb_zebra_level_spec_formatting_fixed_vs_custom(self) -> None:
        gb_fixed = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            zebra_preset="95"
        )
        self.assertEqual(gb_fixed.zebra_level_spec, "95")
        gb_cust = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
            zebra_preset="CUSTOM_1", zebra_level_ire=70, zebra_range_plus_minus=5
        )
        self.assertEqual(gb_cust.zebra_level_spec, "CUSTOM_1(70+-5)")

    # ------------------------------------------------------------------
    # 53-68: Check Group C (Wave 57 §4 + Critical Zero-RF & Slot-1 Firewalls)
    # ------------------------------------------------------------------

    def test_53_gc_default_nominal_zero_rf_passes(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall()
        self.assertTrue(gc.passed)
        self.assertEqual(gc.check_group_id, P307_CHECK_GROUP_C_ID)
        self.assertEqual(gc.airplane_mode, "ON")
        self.assertEqual(gc.wireless_rf_packets_emitted, 0)
        self.assertFalse(gc.rf_nvs_p12_p13_writes_authorized)
        self.assertTrue(gc.zero_rf_airplane_firewall_enforced)
        self.assertTrue(gc.slot1_streaming_ftp_firewall_enforced)
        self.assertEqual(gc.slot1_data_sector_writes, 0)
        self.assertFalse(gc.slot1_avf_info_mutated)
        self.assertEqual(gc.errors, ())

    def test_54_gc_streaming_rtmp_rtmps_srt_over_usb_lan_cdc_ncm_with_airplane_on(self) -> None:
        self.assertEqual(P307_STREAMING_RESID16_HEX, "0x6cb2")
        self.assertEqual(P307_MOVIE_REC_DURING_STREAMING_RESID16_HEX, "0x79d5")
        self.assertEqual(P307_FTP_TRANSFER_FUNC_RESID16_HEX, "0x6317")
        for proto in ("RTMP", "RTMPS", "SRT"):
            for fps in P307_VALID_STREAMING_FPS:
                gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
                    streaming_protocol=proto,
                    streaming_resolution="HD_1080P",
                    streaming_fps=fps,
                    airplane_mode="ON",
                    network_transport="USB_LAN_CDC_NCM",
                )
                self.assertTrue(gc.passed)
                self.assertTrue(gc.zero_rf_airplane_firewall_enforced)

    def test_55_gc_rejects_forbidden_2398p_and_2400p_streaming_fps(self) -> None:
        self.assertEqual(P307_FORBIDDEN_STREAMING_FPS, (23.98, 24.0))
        for bad_fps in (23.98, 24.0, 12.0):
            gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
                streaming_protocol="SRT",
                streaming_fps=bad_fps,
            )
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF in e for e in gc.errors)
            )

    def test_56_gc_movie_rec_during_streaming_slot2_matching_fps_passes(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            streaming_protocol="RTMPS",
            streaming_resolution="HD_1080P",
            streaming_fps=59.94,
            movie_rec_during_streaming="ENABLE",
            internal_rec_resolution_class="HD",
            internal_rec_fps=59.94,
            movie_rec_during_streaming_slot=2,
            network_transport="USB_LAN_CDC_NCM",
        )
        self.assertTrue(gc.passed)
        self.assertTrue(gc.slot1_streaming_ftp_firewall_enforced)

    def test_57_gc_movie_rec_during_streaming_rejects_fps_mismatch_4k_and_sq(self) -> None:
        gc_fps = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            streaming_protocol="RTMP",
            streaming_fps=29.97,
            movie_rec_during_streaming="ENABLE",
            internal_rec_fps=59.94,
            sq_mode_enabled=True,
        )
        self.assertFalse(gc_fps.passed)
        self.assertEqual(len(gc_fps.errors), 2)

        for res, fps in (("4K_2160P", 29.97), ("2K_1440P", 50.0), ("2K_1440P", 59.94)):
            gc_4k = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
                streaming_protocol="SRT",
                streaming_resolution=res,
                streaming_fps=fps,
                movie_rec_during_streaming="ENABLE",
                internal_rec_resolution_class="4K",
                internal_rec_fps=fps,
                movie_rec_during_streaming_slot=2,
            )
            self.assertFalse(gc_4k.passed)

    def test_58_gc_rejects_fx6_builtin_rtmp_srt_claim(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            fx6_builtin_rtmp_srt_claimed=True
        )
        self.assertFalse(gc.passed)
        self.assertTrue(any("BKID_APP_RTMP_SETTINGS" in e for e in gc.errors))

    def test_59_gc_ftp_passive_over_usb_lan_passes_and_rejects_active_mode(self) -> None:
        gc_ok = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            ftp_transfer_func="ON",
            airplane_mode="ON",
            network_transport="USB_LAN_CDC_NCM",
        )
        self.assertTrue(gc_ok.passed)
        gc_bad = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            ftp_transfer_func="ON",
            ftp_active_mode_requested=True,
        )
        self.assertFalse(gc_bad.passed)
        self.assertTrue(
            any(P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET in e for e in gc_bad.errors)
        )

    def test_60_gc_3way_network_reset_boundary(self) -> None:
        gc_cam_ok = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_network_wiped_by_camera_reset=False,
        )
        self.assertTrue(gc_cam_ok.passed)
        gc_cam_bad = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_network_wiped_by_camera_reset=True,
        )
        self.assertFalse(gc_cam_bad.passed)
        gc_net_bad = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            reset_action="RESET_NETWORK_SET",
            claimed_network_survives_reset_network_set=True,
        )
        self.assertFalse(gc_net_bad.passed)

    def test_61_gc_critical_zero_rf_firewall_blocks_airplane_mode_off(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            airplane_mode="OFF"
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.zero_rf_airplane_firewall_enforced)
        self.assertEqual(gc.wireless_rf_packets_emitted, 0)
        self.assertTrue(any(P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL in e for e in gc.errors))

    def test_62_gc_critical_zero_rf_firewall_blocks_wireless_transport_streaming_ftp(self) -> None:
        for kwargs in (
            {"network_transport": "WIRELESS_RF"},
            {"wireless_streaming_requested": True},
            {"wireless_ftp_requested": True},
        ):
            gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(**kwargs)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.zero_rf_airplane_firewall_enforced)

    def test_63_gc_critical_zero_rf_firewall_blocks_nonzero_rf_and_p12_p13_nvs(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            wireless_rf_packets_emitted=1,
            rf_nvs_p12_p13_writes_requested=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.zero_rf_airplane_firewall_enforced)
        self.assertFalse(gc.rf_nvs_p12_p13_writes_authorized)
        self.assertEqual(gc.wireless_rf_packets_emitted, 0)

    def test_64_gc_critical_slot1_vault_blocks_movie_rec_during_streaming_slot1_erofs30(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            streaming_protocol="RTMP",
            streaming_fps=29.97,
            movie_rec_during_streaming="ENABLE",
            internal_rec_fps=29.97,
            movie_rec_during_streaming_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.slot1_streaming_ftp_firewall_enforced)
        self.assertEqual(gc.slot1_data_sector_writes, 0)
        self.assertFalse(gc.slot1_avf_info_mutated)
        self.assertTrue(
            any(P307_GC_ERR_STREAMING_OR_FTP_SLOT1_VAULT_FIREWALL in e for e in gc.errors)
        )

    def test_65_gc_critical_slot1_vault_blocks_ftp_slot1_write_erofs30(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            ftp_transfer_func="ON",
            ftp_slot1_write_requested=True,
            slot1_wp_locked=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.slot1_streaming_ftp_firewall_enforced)
        self.assertTrue(any("EROFS=30" in e and "EBUSY=16" in e for e in gc.errors))

    def test_66_gc_invalid_streaming_and_network_enums_fail_closed(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            streaming_protocol="HLS",
            streaming_resolution="8K",
            movie_rec_during_streaming="MAYBE",
            ftp_transfer_func="AUTO",
            airplane_mode="HALF",
            network_transport="CELLULAR",
        )
        self.assertFalse(gc.passed)
        self.assertGreaterEqual(len(gc.errors), 6)

    def test_67_gc_zero_rf_and_slot1_invariants_always_locked_in_result(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            airplane_mode="OFF",
            wireless_rf_packets_emitted=42,
            ftp_slot1_write_requested=True,
        )
        self.assertEqual(gc.wireless_rf_packets_emitted, 0)
        self.assertEqual(gc.slot1_data_sector_writes, 0)
        self.assertFalse(gc.rf_nvs_p12_p13_writes_authorized)
        self.assertFalse(gc.slot1_avf_info_mutated)

    def test_68_gc_4k_internal_allowed_with_hd_1080p_streaming_slot2(self) -> None:
        gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
            streaming_protocol="SRT",
            streaming_resolution="HD_1080P",
            streaming_fps=29.97,
            movie_rec_during_streaming="ENABLE",
            internal_rec_resolution_class="4K",
            internal_rec_fps=29.97,
            movie_rec_during_streaming_slot=2,
            network_transport="USB_LAN_CDC_NCM",
        )
        self.assertTrue(gc.passed)

    # ------------------------------------------------------------------
    # 69-78: Check Group D, Orchestrator, Dual FX3RCPT1, Tamper & Markdown
    # ------------------------------------------------------------------

    def test_69_orchestrator_offline_awaiting_bench_receipts_and_verified(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True
        )
        self.assertIsInstance(rep, RealHwDialCustomizeLutEmbedSteadyshotStreamingReport)
        self.assertEqual(rep.overall_status, P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertTrue(rep.all_4_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        vr = verify_phase307_report(rep.to_dict())
        self.assertTrue(vr.valid, vr.errors)

    def test_70_orchestrator_simulate_bench_dry_run_and_alias(self) -> None:
        for flag_kwargs in (
            {"simulate_bench_dry_run": True},
            {"simulate_ready_bench": True},
        ):
            rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
                synthetic_clean_room=True,
                **flag_kwargs,
            )
            self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertTrue(rep.simulate_bench_dry_run)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertTrue(rep.check_group_d_physical_bench_and_tier0.distinct_physical_media_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            vr = verify_phase307_report(rep.to_dict())
            self.assertTrue(vr.valid, vr.errors)

    def test_71_orchestrator_valid_dual_device_528b_fx3rcpt1_receipts(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase307_tier0_receipts()
        self.assertEqual(len(rcpt_a), 528)
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True,
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(
            rep.go_no_go, P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED
        )
        self.assertEqual(
            rep.overall_status, P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        vr = verify_phase307_report(rep.to_dict())
        self.assertTrue(vr.valid, vr.errors)

    def test_72_gd_rejects_same_st_dev_corrupt_len_or_missing_copy_b(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase307_tier0_receipts()
        gd_same_dev, errs_dev = evaluate_p307_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=777,
            st_dev_b_override=777,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_same_dev.tier0_receipt_verified)
        self.assertFalse(gd_same_dev.distinct_physical_media_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in errs_dev))

        gd_one, errs_one = evaluate_p307_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=rcpt_a
        )
        self.assertFalse(gd_one.tier0_receipt_verified)
        self.assertTrue(any("Copy A and Copy B" in e for e in errs_one))

        gd_corrupt, errs_bad = evaluate_p307_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=b"BAD" * 10,
            receipt_b_bytes=b"BAD" * 10,
        )
        self.assertFalse(gd_corrupt.tier0_receipt_verified)
        self.assertTrue(any("size/byte mismatch" in e for e in errs_bad))

    def test_73_gd_rejects_trivial_serial_cid_or_mismatched_h0_baselines(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase307_tier0_receipts()
        bad_h0 = dict(h0)
        first_key = next(iter(bad_h0))
        bad_h0[first_key] = "0" * 64
        gd, errs = evaluate_p307_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial="0000000",
            emmc_cid="0" * 32,
            h0_baselines_a=h0,
            h0_baselines_b=bad_h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertGreaterEqual(len(errs), 3)

    def test_74_gd_rejects_h0_h3_drift_passive_tx_and_redline_claims(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True,
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=2,
            simulated_passive_tx_bytes=4,
            claim_hardware_live_attach_authorized=True,
            claim_persistent_emmc_writes_authorized=True,
            claim_cross_model_flash_authorized=True,
        )
        self.assertEqual(
            rep.go_no_go, P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE
        )
        self.assertEqual(rep.h0_equals_h3_count, 14)
        self.assertFalse(rep.check_group_d_physical_bench_and_tier0.passed)
        err_blob = "\n".join(rep.errors)
        self.assertIn(P307_GD_ERR_H0_H3_IMMUTABILITY_DRIFT, err_blob)
        self.assertIn(P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION, err_blob)

    def test_75_verify_phase307_report_tamper_detection_safety_locks_and_zero_counters(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        base = rep.to_dict()
        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "cross_model_flash_authorized",
            "fx3_four_dial_rear_lr_present",
            "fx3_movie_selftimer_present",
            "fx6_builtin_ibis_present",
            "slot1_tier0_vault_mutated",
            "rf_nvs_p12_p13_writes_authorized",
        ):
            tampered = copy.deepcopy(base)
            tampered[lock_key] = True
            res = verify_phase307_report(tampered)
            self.assertFalse(res.valid, f"expected tamper detection for {lock_key}")

        for zero_key in (
            "wireless_rf_packets_emitted",
            "slot1_data_sector_writes",
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            tampered = copy.deepcopy(base)
            tampered[zero_key] = 1
            res = verify_phase307_report(tampered)
            self.assertFalse(res.valid, f"expected zero-counter tamper detection for {zero_key}")

    def test_76_verify_phase307_report_tamper_detection_sha_and_verdict_mismatch(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        tampered = rep.to_dict()
        tampered["go_no_go"] = P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED
        res = verify_phase307_report(tampered)
        self.assertFalse(res.valid)
        self.assertTrue(any("dry-run" in e.lower() for e in res.errors))

    def test_77_render_phase307_markdown_contains_all_4_groups_and_sha256(self) -> None:
        rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase307_markdown(rep)
        for token in (
            PHASE_307_SCHEMA,
            P307_CHECK_GROUP_A_ID,
            P307_CHECK_GROUP_B_ID,
            P307_CHECK_GROUP_C_ID,
            P307_CHECK_GROUP_D_ID,
            rep.report_sha256,
            "ready_attach=False",
        ):
            self.assertIn(token, md)

    def test_78_report_deterministic_json_roundtrip_under_clean_room_modes(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            r1 = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
                simulate_bench_dry_run=True
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r2 = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
                simulate_bench_dry_run=True
            )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        parsed = json.loads(r1.to_deterministic_json())
        self.assertTrue(verify_phase307_report(parsed).valid)

    # ------------------------------------------------------------------
    # 79-86: CLI End-to-End Integration
    # ------------------------------------------------------------------

    def test_79_cli_help_exits_0_and_no_argparse_percent_crash(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("0..109%", proc.stdout)
        self.assertIn("--simulate-bench-dry-run", proc.stdout)

    def test_80_cli_offline_awaiting_receipts_returns_exit_2(self) -> None:
        proc = _run_cli_subprocess(
            ["--force-clean-room", "--json"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["overall_status"], P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertTrue(payload["all_4_check_groups_passed"])
        self.assertTrue(verify_phase307_report(payload).valid)

    def test_81_cli_simulate_bench_dry_run_json_returns_exit_0_clean_room_and_donor(self) -> None:
        proc_cr = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc_cr.returncode, 0, proc_cr.stderr)
        payload_cr = json.loads(proc_cr.stdout)
        self.assertEqual(payload_cr["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload_cr["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase307_report(payload_cr).valid)

        proc_def = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc_def.returncode, 0, proc_def.stderr)
        payload_def = json.loads(proc_def.stdout)
        self.assertEqual(payload_def["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase307_report(payload_def).valid)

    def test_82_cli_summary_and_markdown_modes_return_exit_0(self) -> None:
        for extra_flags in (["--summary"], ["--json", "--summary"], []):
            proc_sum = _run_cli_subprocess(
                ["--force-clean-room", "--simulate-bench-dry-run", *extra_flags],
                extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
            )
            self.assertEqual(proc_sum.returncode, 0, proc_sum.stderr)
            self.assertIn(f"OVERALL={GO_NO_GO_DRY_RUN_SIMULATED_READY}", proc_sum.stdout)
            self.assertIn("check_groups=4/4", proc_sum.stdout)
            self.assertIn("rear_lr=False", proc_sum.stdout)
            self.assertIn("rf_pkts=0", proc_sum.stdout)
            self.assertIn("slot1_writes=0", proc_sum.stdout)
            self.assertIn("leaked_bytes=0", proc_sum.stdout)

    def test_83_cli_writes_markdown_out_and_output_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            md_path = Path(td) / "p307.md"
            json_path = Path(td) / "p307.json"
            proc = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--markdown-out",
                    str(md_path),
                    "--output",
                    str(json_path),
                ],
                extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(md_path.is_file())
            self.assertTrue(json_path.is_file())
            written = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase307_report(written).valid)
            self.assertIn(written["report_sha256"], md_path.read_text(encoding="utf-8"))

    def test_84_cli_negative_firewall_flags_return_exit_2_rear_lr_dynamic_active_sdhc(self) -> None:
        proc = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-rear-dial-lr-requested",
                "--dormant-dynamic-active-requested",
                "--embed-lut-file",
                "ON",
                "--embed-lut-media-type",
                "SDHC",
                "--json",
            ],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["go_no_go"],
            P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE,
        )
        self.assertFalse(payload["check_group_a_dial_customize_liveview_grid_lut"]["passed"])
        self.assertFalse(payload["check_group_b_steadyshot_selftimer_zebra_peaking"]["passed"])

    def test_85_cli_negative_firewall_flags_return_exit_2_zero_rf_and_slot1_streaming(self) -> None:
        proc = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--airplane-mode",
                "OFF",
                "--wireless-streaming-requested",
                "--movie-rec-during-streaming",
                "ENABLE",
                "--movie-rec-during-streaming-slot",
                "1",
                "--json",
            ],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        payload = json.loads(proc.stdout)
        gc = payload["check_group_c_streaming_ftp_zero_rf_slot1_firewall"]
        self.assertFalse(gc["passed"])
        self.assertFalse(gc["zero_rf_airplane_firewall_enforced"])
        self.assertFalse(gc["slot1_streaming_ftp_firewall_enforced"])

    def test_86_cli_same_st_dev_receipt_files_fail_closed_exit_2(self) -> None:
        rcpt_a, rcpt_b, _ = build_simulated_phase307_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "copy_a.bin"
            pb = Path(td) / "copy_b.bin"
            pa.write_bytes(rcpt_a)
            pb.write_bytes(rcpt_b)
            proc = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--receipt-a",
                    str(pa),
                    "--receipt-b",
                    str(pb),
                    "--body-serial",
                    DEFAULT_TARGET_BODY_SERIAL,
                    "--emmc-cid",
                    DEFAULT_TARGET_EMMC_CID,
                    "--json",
                ],
                extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertFalse(payload["tier0_receipt_verified"])
            self.assertTrue(
                any("st_dev_a == st_dev_b" in e for e in payload["errors"])
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
