"""Dual-mode unit tests (100 cases) for Phase 334 (`preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun`):
16th Real-Hardware Physical Bench Readiness Verifier across Waves 64-65 check groups (`A..D`)
covering Breathing Comp., Movie File Settings (Cam ID + Reel# / 37-char Title / SDHC 4 GB),
Round-57 Copyright 46-char Errata, Power Save 9-Cond & NTSC/PAL Slot-1 Guard,
Zoom CIZ / 8-Step Speed / Auto Slow Shutter / Dual Base ISO, Dormant Lossless RAW,
USB LUN Single Slot-1 Hazard, NP-FZ100 / DC-C1 PD Gate, and Dormant UVC.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and donorless CI (`work_root=None`) modes with
zero `.pyc` emission, zero persistent writes, and cross-platform CI headroom.
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
from fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier import (  # noqa: E402
    P334_BREATHING_COMP_HIGH_FPS_CUTOFF,
    P334_BREATHING_COMP_RESID16_HEX,
    P334_CHECK_GROUP_A_ID,
    P334_CHECK_GROUP_B_ID,
    P334_CHECK_GROUP_C_ID,
    P334_CHECK_GROUP_D_ID,
    P334_CIZ_MOVIE_4K_MAX_ZOOM,
    P334_CIZ_MOVIE_HD_MAX_ZOOM,
    P334_COPYRIGHT_EXACT_FOUR_ITEMS,
    P334_COPYRIGHT_MAX_CHARS,
    P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    P334_DC_C1_MIN_CABLE_AMPS,
    P334_DC_C1_MIN_PD_WATTS,
    P334_DIGITAL_MOVIE_MAX_ZOOM,
    P334_DORMANT_LOSSLESS_RAW_RESID16_HEX,
    P334_DORMANT_POWER_SAVE_BY_MONITOR_RESIDS,
    P334_DORMANT_UVC_RESIDS,
    P334_ERRNO_EOPNOTSUPP,
    P334_ERRNO_EROFS,
    P334_FX3_RAW_TWO_OPTIONS,
    P334_FX6_DC_IN_NOMINAL_VOLTS,
    P334_FX6_TITLE_PREFIX_MAX_CHARS,
    P334_FX6_TITLE_PREFIX_MIN_CHARS,
    P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST,
    P334_GA_ERR_MODEL_OR_FW_FLOOR,
    P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH,
    P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT,
    P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS,
    P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE,
    P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA,
    P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS,
    P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION,
    P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL,
    P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1,
    P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT,
    P334_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P334_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE,
    P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE,
    P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
    P334_MOVIE_REC_DURING_STREAMING_RESID16_HEX,
    P334_NTSCPAL_RESID16_HEX,
    P334_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P334_POWER_OPTION_EXACT_TWO_ITEMS,
    P334_POWER_SAVE_NINE_BYPASS_CONDITIONS,
    P334_REC_MEDIA_DUR_HDMI_RESID16_HEX,
    P334_REMOTE_ZOOM_FIXED_DEFAULT,
    P334_SCHEMA,
    P334_SDHC_SPLIT_GB,
    P334_SONY_HELP_GUIDE_ID,
    P334_TITLE_MAX_CHARS,
    P334_USB_CONN_EXACT_FOUR_MODES,
    P334_WRITE_SERIAL_BKID,
    P334_ZOOM_LEVER_1ST_DEFAULT,
    P334_ZOOM_LEVER_2ND_DEFAULT,
    PHASE334_E_ND_ACTUATOR_TX_COUNT,
    PHASE334_PASSIVE_TX_BYTES_EMITTED,
    PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE334_SLOT1_DATA_SECTOR_WRITES,
    PHASE334_USB_PACKETS_TRANSMITTED,
    PHASE334_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_334_CHECK_GROUP_IDS,
    PHASE_334_SCHEMA,
    _canonical_sha256_dict,
    build_simulated_phase334_tier0_receipts,
    evaluate_p334_check_group_a_breathing_camid_and_sdhc,
    evaluate_p334_check_group_b_copyright_powersave_and_ntscpal,
    evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso,
    evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0,
    evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight,
    inspect_phase334_donors_bounded,
    render_phase334_markdown,
    run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight,
    verify_phase334_report,
)
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
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
            "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase334Preflight16Verifier(unittest.TestCase):
    def _assert_err(self, res: object, err_prefix: str) -> None:
        errors = getattr(res, "errors")
        self.assertTrue(
            any(e == err_prefix or e.startswith(f"{err_prefix}:") for e in errors),
            f"Expected error starting with {err_prefix!r} in {errors!r}",
        )

    def _assert_err_contains(self, res: object, token: str) -> None:
        errors = getattr(res, "errors")
        self.assertTrue(
            any(token in e for e in errors),
            f"Expected substring {token!r} in {errors!r}",
        )

    # ------------------------------------------------------------------
    # 01-12: Exports, Schema, Dual-Modes, Donorless CI & Determinism
    # ------------------------------------------------------------------

    def test_01_package_exports_and_schema_constants(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight"))
        self.assertEqual(P334_SCHEMA, PHASE_334_SCHEMA)
        self.assertEqual(P334_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_334_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_334_CHECK_GROUP_IDS,
            (P334_CHECK_GROUP_A_ID, P334_CHECK_GROUP_B_ID, P334_CHECK_GROUP_C_ID, P334_CHECK_GROUP_D_ID),
        )

    def test_02_locked_zero_constants(self) -> None:
        self.assertEqual(PHASE334_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE334_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE334_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE334_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE334_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE334_E_ND_ACTUATOR_TX_COUNT, 0)

    def test_03_clean_room_donor_inspection_reads_zero_bytes(self) -> None:
        res = inspect_phase334_donors_bounded(force_clean_room=True)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.donor_tree_present)
        self.assertEqual(res.bytes_read_total, 0)
        self.assertEqual(res.checked_paths, ())
        self.assertTrue(res.within_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_04_donorless_ci_work_root_none_guard(self) -> None:
        with mock.patch(
            "fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.iter_work_roots",
            return_value=(),
        ):
            res = inspect_phase334_donors_bounded(force_clean_room=False)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.bytes_read_total, 0)
        self.assertTrue(res.within_budget)

    def test_05_nonexistent_mac_work_root_falls_back_cleanly(self) -> None:
        with mock.patch(
            "fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.iter_work_roots",
            return_value=(Path("/nonexistent/phase334_ci_missing_root"),),
        ):
            rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
                simulate_bench_dry_run=True,
                force_clean_room=False,
            )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)

    def test_06_env_vars_force_clean_room_mode(self) -> None:
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}, clear=False):
                res = inspect_phase334_donors_bounded()
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.bytes_read_total, 0)

    def test_07_default_offline_blocks_awaiting_physical_receipt(self) -> None:
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            force_clean_room=True,
        )
        self.assertEqual(rep.overall_status, P334_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase334_report(rep).valid)

    def test_08_simulate_bench_dry_run_passes_cleanly(self) -> None:
        rep = run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "DRY_RUN_SIMULATED")
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertTrue(verify_phase334_report(rep).valid)

    def test_09_physical_dual_media_receipts_verify_and_grant_go(self) -> None:
        bundle = build_simulated_phase334_tier0_receipts()
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            force_clean_room=True,
            receipt_a_bytes=bundle["receipt_a_bytes"],
            receipt_b_bytes=bundle["receipt_b_bytes"],
            st_dev_a_override=111,
            st_dev_b_override=222,
            body_serial=bundle["body_serial"],
            emmc_cid=bundle["emmc_cid"],
            h0_baselines_a=bundle["h0_baselines_a"],
            h0_baselines_b=bundle["h0_baselines_b"],
            h3_baselines=bundle["h3_baselines"],
        )
        self.assertEqual(
            rep.overall_status,
            P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
        )
        self.assertEqual(
            rep.go_no_go,
            P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
        )
        self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_528B")
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase334_report(rep).valid)

    def test_10_determinism_zeroes_nested_timing_fields_and_identical_sha256(self) -> None:
        r1 = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
        )
        r2 = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.to_deterministic_json(), r2.to_deterministic_json())
        d1 = r1.to_dict()
        d2 = copy.deepcopy(d1)
        d2["donor_inspection"]["elapsed_seconds"] = 0.123456
        d2["elapsed_seconds"] = 9.876543
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_11_fake_donor_directory_bounded_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fx6_lib = root / "fx6_lib"
            fx3_mod = root / "fx3_mod"
            fx6_lib.mkdir()
            fx3_mod.mkdir()
            (fx6_lib / "appFw.so").write_bytes(b"\x7fELF" + b"A" * 200)
            (fx3_mod / "upm.ko").write_bytes(b"\x7fELF" + b"B" * 200)
            with mock.patch(
                "fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.resolve_work_subpath",
                side_effect=lambda rel, require_file=True: root / rel,
            ):
                res = inspect_phase334_donors_bounded(
                    force_clean_room=False,
                    work_root=root,
                    fx6_lib_dir=fx6_lib,
                    fx3_modules_dir=fx3_mod,
                )
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(res.donor_tree_present)
        self.assertTrue(res.fx6_appfw_present)
        self.assertEqual(res.bytes_read_total, 128)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_12_empirical_constants_match_waves_64_65(self) -> None:
        self.assertEqual(P334_BREATHING_COMP_RESID16_HEX, "0x73ea")
        self.assertEqual(P334_BREATHING_COMP_HIGH_FPS_CUTOFF, 100.0)
        self.assertEqual(P334_TITLE_MAX_CHARS, 37)
        self.assertEqual(P334_SDHC_SPLIT_GB, 4)
        self.assertEqual((P334_FX6_TITLE_PREFIX_MIN_CHARS, P334_FX6_TITLE_PREFIX_MAX_CHARS), (4, 46))
        self.assertEqual(P334_COPYRIGHT_MAX_CHARS, 46)
        self.assertEqual(len(P334_COPYRIGHT_EXACT_FOUR_ITEMS), 4)
        self.assertEqual(len(P334_POWER_OPTION_EXACT_TWO_ITEMS), 2)
        self.assertEqual(len(P334_POWER_SAVE_NINE_BYPASS_CONDITIONS), 9)
        self.assertEqual(len(P334_DORMANT_POWER_SAVE_BY_MONITOR_RESIDS), 5)
        self.assertEqual(P334_NTSCPAL_RESID16_HEX, "0x6b6f")
        self.assertEqual((P334_CIZ_MOVIE_4K_MAX_ZOOM, P334_CIZ_MOVIE_HD_MAX_ZOOM, P334_DIGITAL_MOVIE_MAX_ZOOM), (1.5, 2.0, 4.0))
        self.assertEqual((P334_ZOOM_LEVER_1ST_DEFAULT, P334_ZOOM_LEVER_2ND_DEFAULT, P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT, P334_REMOTE_ZOOM_FIXED_DEFAULT), (3, 8, 3, 3))
        self.assertEqual(P334_FX3_RAW_TWO_OPTIONS, ("COMPRESSED", "UNCOMPRESSED"))
        self.assertEqual(P334_DORMANT_LOSSLESS_RAW_RESID16_HEX, "0x6b56")
        self.assertEqual(len(P334_USB_CONN_EXACT_FOUR_MODES), 4)
        self.assertEqual((P334_DC_C1_MIN_PD_WATTS, P334_DC_C1_MIN_CABLE_AMPS, P334_FX6_DC_IN_NOMINAL_VOLTS), (65.0, 5.0, 19.5))
        self.assertEqual(P334_DORMANT_UVC_RESIDS, ("0x6216", "0x6194"))
        self.assertEqual(P334_MOVIE_REC_DURING_STREAMING_RESID16_HEX, "0x79d5")
        self.assertEqual(P334_REC_MEDIA_DUR_HDMI_RESID16_HEX, "0x6144")

    # ------------------------------------------------------------------
    # 13-32: Check Group A (Wave 64 §§1-2: Breathing Comp & File Settings)
    # ------------------------------------------------------------------

    def test_13_group_a_default_passes(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc()
        self.assertTrue(res.passed, res.errors)

    def test_14_group_a_rejects_wrong_model_fw_or_help_guide(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(body_model_id=0x0398)
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GA_ERR_MODEL_OR_FW_FLOOR)
        res2 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(sony_help_guide_id="ilc/9999")
        self._assert_err(res2, P334_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_15_group_a_breathing_comp_120p_100p_lockout(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(breathing_comp="ON", rec_fps=119.88)
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST)
        res_100 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(breathing_comp="ON", rec_fps=100.0)
        self.assertFalse(res_100.passed)

    def test_16_group_a_breathing_comp_sq_cutoff_below_100fps_allowed_above_blocked(self) -> None:
        ok_60 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            breathing_comp="ON", shoot_mode="S_AND_Q", sq_enabled=True, sq_fps=60.0
        )
        self.assertTrue(ok_60.passed, ok_60.errors)
        bad_120 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            breathing_comp="ON", shoot_mode="S_AND_Q", sq_enabled=True, sq_fps=120.0
        )
        self.assertFalse(bad_120.passed)
        self._assert_err(bad_120, P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST)

    def test_17_group_a_breathing_comp_blocks_still_raw_ciz_auto_framing_and_tc(self) -> None:
        for kw in (
            {"shoot_mode": "PHOTO"},
            {"hdmi_raw_output": "ON"},
            {"zoom_range": "CLEAR_IMAGE_ZOOM"},
            {"auto_framing_claimed": True},
            {"non_compliant_or_teleconverter_lens": True},
        ):
            res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(breathing_comp="ON", **kw)
            self.assertFalse(res.passed, kw)
            self._assert_err(res, P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST)

    def test_18_group_a_breathing_comp_resets_via_camera_settings_reset_unlike_static_comp(self) -> None:
        ok = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            reset_action="CAMERA_SETTINGS_RESET", breathing_comp="OFF"
        )
        self.assertTrue(ok.passed, ok.errors)
        bad_on = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            reset_action="CAMERA_SETTINGS_RESET", breathing_comp="ON"
        )
        self.assertFalse(bad_on.passed)
        bad_claim = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_breathing_comp_resists_camera_reset=True
        )
        self.assertFalse(bad_claim.passed)
        bad_static = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_static_lens_comp_reset_by_camera_reset=True
        )
        self.assertFalse(bad_static.passed)

    def test_19_group_a_fx6_breathing_and_fx3_sub100fps_claims_rejected(self) -> None:
        r1 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_fx3_blocks_breathing_below_100fps_sq=True
        )
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed=True
        )
        self.assertFalse(r2.passed)

    def test_20_group_a_catalyst_prepare_vs_browse_and_distortion_comp_auto(self) -> None:
        ok = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            post_breathing_comp_requested=True,
            catalyst_app="CATALYST_PREPARE",
            distortion_comp="AUTO",
        )
        self.assertTrue(ok.passed, ok.errors)
        bad_browse = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            post_breathing_comp_requested=True,
            catalyst_app="CATALYST_BROWSE",
            distortion_comp="AUTO",
        )
        self.assertFalse(bad_browse.passed)
        bad_dist = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            post_breathing_comp_requested=True,
            catalyst_app="CATALYST_PREPARE_PLUGIN",
            distortion_comp="OFF",
        )
        self.assertFalse(bad_dist.passed)
        bad_claim = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_catalyst_browse_supports_breathing_comp=True
        )
        self.assertFalse(bad_claim.passed)

    def test_21_group_a_movie_file_settings_cam_id_reel_valid(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="CAM_ID_REEL",
            camera_id="C",
            reel_number=999,
            camera_position="R",
            slot2_fs="EXFAT",
        )
        self.assertTrue(res.passed, res.errors)

    def test_22_group_a_cam_id_reel_boundary_rejections(self) -> None:
        for bad_kw in (
            {"camera_id": "AB"},
            {"camera_id": "1"},
            {"reel_number": 0},
            {"reel_number": 1000},
            {"camera_position": "X"},
            {"expect_rollover_mutates_cam_id_menu": True},
            {"claimed_cam_id_reel_uses_yyyymmdd_date": True},
            {"claimed_file_number_reset_resets_reel": True},
        ):
            res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
                file_name_format="CAM_ID_REEL", **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH)

    def test_23_group_a_title_37_char_limit_and_allowed_charset(self) -> None:
        ok_37 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="TITLE", title_name="A" * 37
        )
        self.assertTrue(ok_37.passed, ok_37.errors)
        bad_38 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="TITLE", title_name="A" * 38
        )
        self.assertFalse(bad_38.passed)
        self._assert_err(bad_38, P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH)
        bad_space = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="DATE_TITLE", title_name="BAD TITLE"
        )
        self.assertFalse(bad_space.passed)

    def test_24_group_a_movie_file_settings_initialize_only_and_no_custom_folder(self) -> None:
        bad_reset = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_movie_file_settings_reset_by_camera_reset=True
        )
        self.assertFalse(bad_reset.passed)
        bad_folder = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            claimed_custom_movie_folder_supported=True
        )
        self.assertFalse(bad_folder.passed)
        bad_fx6 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            fx6_clip_naming_uses_project_menu_or_37char_claimed=True
        )
        self.assertFalse(bad_fx6.passed)

    def test_25_group_a_sdhc_forces_standard_and_4gb_split(self) -> None:
        ok_sdhc = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            recording_media="SLOT_2",
            slot2_media_type="SDHC",
            slot2_fs="FAT32",
            file_name_format="STANDARD",
        )
        self.assertTrue(ok_sdhc.passed, ok_sdhc.errors)
        bad_camid = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            recording_media="SLOT_2",
            slot2_media_type="SDHC",
            slot2_fs="FAT32",
            file_name_format="CAM_ID_REEL",
        )
        self.assertFalse(bad_camid.passed)
        self._assert_err(bad_camid, P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT)
        bad_nosplit = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            recording_media="SLOT_2",
            slot2_media_type="SDHC",
            slot2_fs="FAT32",
            claimed_sdhc_no_4gb_split=True,
        )
        self.assertFalse(bad_nosplit.passed)

    def test_26_group_a_sdhc_blocks_simultaneous_recording_with_exfat(self) -> None:
        bad = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            recording_media="SIMULTANEOUS_RECORDING",
            slot1_media_type="SDXC",
            slot1_fs="EXFAT",
            slot2_media_type="SDHC",
            slot2_fs="FAT32",
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT)

    def test_27_group_a_sdhc_must_use_fat32_not_exfat(self) -> None:
        bad = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            slot2_media_type="SDHC", slot2_fs="EXFAT"
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT)

    def test_28_group_a_slot1_tier0_vault_erofs_blocks_counter_or_series_reset_or_writes(self) -> None:
        for bad_kw in (
            {"series_counter_reset_slot": 1},
            {"movie_file_counter_write_slot": 1},
            {"recording_media": "SLOT_1"},
            {"slot1_data_sector_writes": 1},
        ):
            res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT)
            self.assertTrue(res.slot1_tier0_vault_mutated)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EROFS}")

    def test_29_group_a_slot2_series_counter_reset_allowed(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_number_mode="RESET",
            series_counter_reset_slot=2,
            movie_file_counter_write_slot=2,
            recording_media="SLOT_2",
        )
        self.assertTrue(res.passed, res.errors)

    def test_30_group_a_invalid_file_number_or_name_mode_rejected(self) -> None:
        r1 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(file_number_mode="INVALID")
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(file_name_format="INVALID")
        self.assertFalse(r2.passed)

    def test_31_group_a_initialize_allows_default_breathing_off(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            reset_action="INITIALIZE", breathing_comp="OFF"
        )
        self.assertTrue(res.passed, res.errors)

    def test_32_group_a_date_title_and_title_date_valid(self) -> None:
        res = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="DATE_TITLE", title_name="CAM_A_SCENE01"
        )
        self.assertTrue(res.passed, res.errors)
        res2 = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
            file_name_format="TITLE_DATE", title_name="CAM_B_ROLL02"
        )
        self.assertTrue(res2.passed, res2.errors)

    # ------------------------------------------------------------------
    # 33-50: Check Group B (Wave 64 §§3-4: Round-57 Copyright, Power Save, NTSC/PAL)
    # ------------------------------------------------------------------

    def test_33_group_b_default_passes(self) -> None:
        res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal()
        self.assertTrue(res.passed, res.errors)

    def test_34_group_b_copyright_46_char_boundary(self) -> None:
        ok = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            write_copyright_info="ON",
            set_photographer="P" * 46,
            set_copyright="C" * 46,
            disp_copyright_info_requested=True,
        )
        self.assertTrue(ok.passed, ok.errors)
        bad_p = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            set_photographer="P" * 47
        )
        self.assertFalse(bad_p.passed)
        self._assert_err(bad_p, P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA)
        bad_c = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            set_copyright="C" * 47
        )
        self.assertFalse(bad_c.passed)

    def test_35_group_b_copyright_exact_4_items_required(self) -> None:
        bad = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            exposed_copyright_items=("WRITE_COPYRIGHT_INFO", "SET_PHOTOGRAPHER")
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA)

    def test_36_group_b_round57_errata_copyright_and_serial_resist_camera_settings_reset(self) -> None:
        ok = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            reset_action="CAMERA_SETTINGS_RESET",
            write_copyright_info="ON",
            set_photographer="KAFU",
            write_serial_number="ON",
        )
        self.assertTrue(ok.passed, ok.errors)
        for bad_kw in (
            {"claimed_copyright_wiped_by_camera_reset": True},
            {"claimed_write_serial_wiped_by_camera_reset": True},
            {"claimed_write_serial_still_only_in_v702": True},
            {"claimed_copyright_saved_in_camset": True},
            {"claimed_write_serial_excluded_from_camset": True},
            {"fx6_has_copyright_info_menu_claimed": True},
        ):
            res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA)

    def test_37_group_b_write_serial_bkid_confirmed(self) -> None:
        self.assertEqual(P334_WRITE_SERIAL_BKID, "BKID_APP_setting_write_serial_number_still_movie")

    def test_38_group_b_power_option_exact_two_items(self) -> None:
        bad = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            exposed_power_option_items=("POWER_SAVE_START_TIME", "AUTO_POWER_OFF_TEMP", "POWER_SAVE_BY_MONITOR")
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)

    def test_39_group_b_power_save_valid_timers_and_dormant_timers_rejected(self) -> None:
        for t in ("OFF", "30_MIN", "5_MIN", "2_MIN", "1_MIN", "10_SEC"):
            ok = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(power_save_start_time=t)
            self.assertTrue(ok.passed, (t, ok.errors))
        for dt in ("20_SEC", "NO_LIMIT", "30_SEC", "60_MIN", "240_MIN"):
            bad = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
                dormant_power_save_timer_requested=dt
            )
            self.assertFalse(bad.passed, dt)
            self._assert_err(bad, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)

    def test_40_group_b_power_save_9_bypass_conditions(self) -> None:
        ok = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            power_save_active_bypass_conditions=("TV_HDMI_CONNECTION", "STREAMING_OR_CREATORS_CLOUD_UPLOAD"),
            power_save_sleep_expected_during_bypass=False,
        )
        self.assertTrue(ok.passed, ok.errors)
        bad = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            power_save_active_bypass_conditions=("USB_POWER_SUPPLY",),
            power_save_sleep_expected_during_bypass=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)
        bad_ign = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            claimed_power_save_ignores_9_conditions=True
        )
        self.assertFalse(bad_ign.passed)

    def test_41_group_b_auto_power_off_temp_high_handheld_gate(self) -> None:
        ok_tripod = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            auto_power_off_temp="HIGH", handheld_bare_skin_unacknowledged=False
        )
        self.assertTrue(ok_tripod.passed, ok_tripod.errors)
        bad_handheld = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            auto_power_off_temp="HIGH", handheld_bare_skin_unacknowledged=True
        )
        self.assertFalse(bad_handheld.passed)
        self._assert_err(bad_handheld, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)

    def test_42_group_b_dormant_power_save_by_monitor_eopnotsupp(self) -> None:
        for bad_kw in (
            {"dormant_power_save_by_monitor_requested": True},
            {"fx3_power_save_by_monitor_present_claimed": True},
            {"fx3_builtin_evf_present": True},
            {"claimed_power_option_wiped_by_camera_reset": True},
        ):
            res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)
            self.assertFalse(res.fx3_power_save_by_monitor_present)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EOPNOTSUPP}")

    def test_43_group_b_ntsc_pal_switch_requires_reboot_and_blocks_cross_playback(self) -> None:
        ok_pal = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            video_system="PAL", ntsc_pal_switch_requested=True, slot1_format_requested=False
        )
        self.assertTrue(ok_pal.passed, ok_pal.errors)
        bad_noreboot = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            ntsc_pal_switch_requested=True, expect_ntsc_pal_no_reboot=True
        )
        self.assertFalse(bad_noreboot.passed)
        self._assert_err(bad_noreboot, P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS)
        bad_cross = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            expect_cross_system_playback_without_switch=True
        )
        self.assertFalse(bad_cross.passed)

    def test_44_group_b_ntsc_pal_resists_camera_reset_and_fx6_lacks_selector(self) -> None:
        r1 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            claimed_ntsc_pal_wiped_by_camera_reset=True
        )
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            fx6_has_ntsc_pal_selector_claimed=True
        )
        self.assertFalse(r2.passed)

    def test_45_group_b_slot1_format_guard_blocks_base_uxc_format_prompt_erofs(self) -> None:
        for bad_kw in (
            {"slot1_format_requested": True},
            {"slot1_data_sector_writes": 1},
        ):
            res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS)
            self.assertTrue(res.slot1_tier0_vault_mutated)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EROFS}")

    def test_46_group_b_slot1_must_remain_wp_locked_and_hold_tier0_dump(self) -> None:
        r1 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(slot1_wp_locked=False)
        self.assertFalse(r1.passed)
        self._assert_err(r1, P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS)
        r2 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(slot1_contains_tier0_dump=False)
        self.assertFalse(r2.passed)
        self._assert_err(r2, P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS)

    def test_47_group_b_initialize_clears_optional_warning_not_errors(self) -> None:
        res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            reset_action="INITIALIZE", write_copyright_info="OFF", write_serial_number="OFF"
        )
        self.assertTrue(res.passed, res.errors)

    def test_48_group_b_invalid_video_system_rejected(self) -> None:
        res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(video_system="SECAM")
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS)

    def test_49_group_b_invalid_power_save_or_temp_rejected(self) -> None:
        r1 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(power_save_start_time="BOGUS")
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(auto_power_off_temp="EXTREME")
        self.assertFalse(r2.passed)

    def test_50_group_b_invalid_bypass_condition_rejected(self) -> None:
        res = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
            power_save_active_bypass_conditions=("NOT_A_REAL_CONDITION",)
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE)

    # ------------------------------------------------------------------
    # 51-70: Check Group C (Wave 65 §§1-2: Zoom CIZ, Slow Shutter, Dual Base ISO)
    # ------------------------------------------------------------------

    def test_51_group_c_default_passes(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso()
        self.assertTrue(res.passed, res.errors)

    def test_52_group_c_ciz_4k_1_5x_and_digital_4x(self) -> None:
        ok_4k = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_scale=1.5,
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertTrue(ok_4k.passed, ok_4k.errors)
        bad_4k = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_scale=2.0,
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(bad_4k.passed)
        self._assert_err(bad_4k, P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL)

        ok_dig = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="DIGITAL_ZOOM",
            zoom_scale=4.0,
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertTrue(ok_dig.passed, ok_dig.errors)
        bad_dig = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="DIGITAL_ZOOM",
            zoom_scale=4.5,
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(bad_dig.passed)

    def test_53_group_c_ciz_forces_center_af_multi_metering_and_blocks_face_tracking(self) -> None:
        for bad_kw in (
            {"focus_area": "WIDE", "metering_mode": "MULTI", "face_eye_prior_in_af": "OFF"},
            {"focus_area": "CENTER_FIX", "metering_mode": "SPOT", "face_eye_prior_in_af": "OFF"},
            {"focus_area": "CENTER_FIX", "metering_mode": "MULTI", "face_eye_prior_in_af": "ON"},
            {"focus_area": "CENTER_FIX", "metering_mode": "MULTI", "face_eye_prior_in_af": "OFF", "tracking_af_active": True},
        ):
            res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
                zoom_range="CLEAR_IMAGE_ZOOM", zoom_scale=1.3, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL)

    def test_54_group_c_ciz_blocks_movie_120p_sq_and_still_raw(self) -> None:
        bad_120p = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM", zoom_scale=1.2, rec_fps=119.88,
            focus_area="CENTER_FIX", metering_mode="MULTI", face_eye_prior_in_af="OFF",
        )
        self.assertFalse(bad_120p.passed)
        bad_sq = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM", zoom_scale=1.2, shoot_mode="S_AND_Q", sq_enabled=True, sq_fps=120.0,
            focus_area="CENTER_FIX", metering_mode="MULTI", face_eye_prior_in_af="OFF",
        )
        self.assertFalse(bad_sq.passed)
        ok_sq_60 = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM", zoom_scale=1.2, shoot_mode="S_AND_Q", sq_enabled=True, sq_fps=60.0,
            focus_area="CENTER_FIX", metering_mode="MULTI", face_eye_prior_in_af="OFF",
        )
        self.assertTrue(ok_sq_60.passed, ok_sq_60.errors)
        bad_still_raw = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM", zoom_scale=1.2, shoot_mode="PHOTO", still_file_format="RAW",
            focus_area="CENTER_FIX", metering_mode="MULTI", face_eye_prior_in_af="OFF",
        )
        self.assertFalse(bad_still_raw.passed)

    def test_55_group_c_still_jpeg_ciz_allowed(self) -> None:
        ok = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_scale=1.5,
            shoot_mode="PHOTO",
            still_file_format="JPEG",
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertTrue(ok.passed, ok.errors)

    def test_56_group_c_zoom_8step_speed_bounds_and_fx6_zero_digital_zoom(self) -> None:
        for bad_kw in (
            {"zoom_lever_stby_speed": 0},
            {"zoom_lever_rec_speed": 9},
            {"zoom_lever_2nd_speed": 9},
            {"custom_key_zoom_stby_speed": 0},
            {"remote_zoom_fixed_rec_speed": 9},
            {"expect_smart_zoom_in_movie": True},
            {"fx6_has_digital_zoom_claimed": True},
            {"claimed_zoom_range_wiped_by_camera_reset": True},
            {"claimed_zoom_ring_rotate_wiped_by_camera_reset": True},
            {"claimed_zoom_speeds_resist_camera_reset": True},
        ):
            res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL)

    def test_57_group_c_zoom_ring_rotate_and_remote_fixed_valid(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_ring_rotate="RIGHT_W_LEFT_T",
            remote_zoom_speed_type="FIXED",
            remote_zoom_fixed_stby_speed=5,
            remote_zoom_fixed_rec_speed=2,
            zoom_lever_stby_speed=1,
            zoom_lever_2nd_speed=8,
        )
        self.assertTrue(res.passed, res.errors)

    def test_58_group_c_auto_slow_shutter_6_lockouts(self) -> None:
        ok = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            shoot_mode="MOVIE",
            exposure_mode="APERTURE_PRIORITY",
            shutter_mode="SHUTTER_SPEED",
            log_shooting_mode="OFF",
            iso_mode="ISO_AUTO",
            auto_slow_shutter="ON",
            expect_auto_slow_shutter_active=True,
        )
        self.assertTrue(ok.passed, ok.errors)
        for bad_kw in (
            {"exposure_mode": "MANUAL_EXPOSURE", "log_shooting_mode": "OFF", "expect_auto_slow_shutter_active": True},
            {"exposure_mode": "SHUTTER_PRIORITY", "log_shooting_mode": "OFF", "expect_auto_slow_shutter_active": True},
            {"exposure_mode": "APERTURE_PRIORITY", "log_shooting_mode": "OFF", "shoot_mode": "S_AND_Q", "sq_enabled": True, "expect_auto_slow_shutter_active": True},
            {"exposure_mode": "APERTURE_PRIORITY", "log_shooting_mode": "OFF", "shutter_mode": "SHUTTER_ANGLE", "expect_auto_slow_shutter_active": True},
            {"exposure_mode": "APERTURE_PRIORITY", "log_shooting_mode": "CINE_EI", "expect_auto_slow_shutter_active": True},
            {"exposure_mode": "FLEXIBLE_EXP", "log_shooting_mode": "OFF", "flexible_shutter_mode": "MANUAL", "expect_auto_slow_shutter_active": True},
            {"claimed_auto_slow_shutter_resists_reset": True},
        ):
            res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS)

    def test_59_group_c_iso_range_limit_initialize_only_and_manual_only(self) -> None:
        ok = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            iso_range_limit_min=100, iso_range_limit_max=12800
        )
        self.assertTrue(ok.passed, ok.errors)
        bad_order = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            iso_range_limit_min=6400, iso_range_limit_max=800
        )
        self.assertFalse(bad_order.passed)
        self._assert_err(bad_order, P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION)
        bad_auto = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            expect_iso_range_limit_caps_iso_auto=True
        )
        self.assertFalse(bad_auto.passed)
        bad_reset = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            claimed_iso_range_limit_wiped_by_camera_reset=True
        )
        self.assertFalse(bad_reset.passed)

    def test_60_group_c_iso_auto_min_ss_still_pa_only_and_flash_lock(self) -> None:
        ok_pa = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            shoot_mode="PHOTO", exposure_mode="APERTURE_PRIORITY", iso_auto_min_ss="1/125"
        )
        self.assertTrue(ok_pa.passed, ok_pa.errors)
        for bad_kw in (
            {"expect_iso_auto_min_ss_in_movie_or_sq": True},
            {"shoot_mode": "PHOTO", "exposure_mode": "APERTURE_PRIORITY", "flash_enabled": True, "expect_iso_auto_min_ss_active_with_flash": True},
            {"claimed_iso_auto_min_ss_resists_reset": True},
        ):
            res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS)

    def test_61_group_c_dual_base_iso_cine_ei_scinetone_off(self) -> None:
        for profile, lo, hi in (
            ("CINE_EI", 800, 12800),
            ("PP11_SCINETONE", 100, 2000),
            ("PP_OFF", 80, 1600),
        ):
            ok = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
                gamma_base_profile=profile, dual_base_iso_low=lo, dual_base_iso_high=hi
            )
            self.assertTrue(ok.passed, (profile, ok.errors))

    def test_62_group_c_dual_base_iso_mismatch_or_fx6_agc_rejected(self) -> None:
        for bad_kw in (
            {"gamma_base_profile": "CINE_EI", "dual_base_iso_low": 800, "dual_base_iso_high": 3200},
            {"gamma_base_profile": "PP11_SCINETONE", "dual_base_iso_low": 800, "dual_base_iso_high": 12800},
            {"gamma_base_profile": "PP_OFF", "dual_base_iso_low": 100, "dual_base_iso_high": 2000},
            {"claimed_base_iso_menu_outside_cine_ei": True},
            {"fx3_has_fx6_agc_claimed": True},
        ):
            res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(**bad_kw)
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION)

    def test_63_group_c_flexible_exposure_auto_shutter_allows_auto_slow_shutter(self) -> None:
        ok = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            shoot_mode="MOVIE",
            exposure_mode="FLEXIBLE_EXP",
            flexible_shutter_mode="AUTO",
            shutter_mode="SHUTTER_SPEED",
            log_shooting_mode="OFF",
            iso_mode="ISO_AUTO",
            auto_slow_shutter="ON",
            expect_auto_slow_shutter_active=True,
        )
        self.assertTrue(ok.passed, ok.errors)

    def test_64_group_c_zoom_scale_below_1_rejected(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(zoom_scale=0.5)
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL)

    def test_65_group_c_optical_only_above_1x_rejected(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="OPTICAL_ONLY", zoom_scale=1.5
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL)

    def test_66_group_c_ciz_2_1x_exceeded_rejected(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_scale=2.1,
            focus_area="CENTER_FIX",
            metering_mode="MULTI",
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(res.passed)

    def test_67_group_c_iso_bounds_50_to_409600_enforced(self) -> None:
        r1 = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(iso_range_limit_min=25)
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(iso_range_limit_max=819200)
        self.assertFalse(r2.passed)

    def test_68_group_c_invalid_iso_auto_min_ss_mode_rejected(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(iso_auto_min_ss="1/9999")
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS)

    def test_69_group_c_invalid_zoom_range_and_ring_rotate_rejected(self) -> None:
        r1 = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(zoom_range="SMART_ZOOM")
        self.assertFalse(r1.passed)
        r2 = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(zoom_ring_rotate="INVALID")
        self.assertFalse(r2.passed)

    def test_70_group_c_auto_slow_shutter_invalid_option_rejected(self) -> None:
        res = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(auto_slow_shutter="AUTO")
        self.assertFalse(res.passed)

    # ------------------------------------------------------------------
    # 71-90: Check Group D (Wave 65 §§3-4: Lossless RAW, USB LUN, PD, UVC, Tier-0)
    # ------------------------------------------------------------------

    def test_71_group_d_dry_run_default_passes(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(simulate_bench_dry_run=True)
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.h0_equals_h3_count, 16)

    def test_72_group_d_dormant_lossless_raw_myth_busted_eopnotsupp(self) -> None:
        for bad_kw in (
            {"raw_file_type": "LOSSLESS_COMP"},
            {"dormant_lossless_comp_requested": True},
            {"fx3_lossless_comp_present_claimed": True},
            {"claimed_raw_file_type_resists_reset": True},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1)
            self.assertFalse(res.fx3_lossless_comp_raw_present)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EOPNOTSUPP}")

    def test_73_group_d_hlg_still_requires_heif_and_pasm(self) -> None:
        ok = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            hlg_still_image="ON",
            jh_file_type="HEIF_422",
            still_file_format="HEIF",
            exposure_mode="APERTURE_PRIORITY",
        )
        self.assertTrue(ok.passed, ok.errors)
        bad_jpeg = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            hlg_still_image="ON",
            jh_file_type="JPEG",
            still_file_format="JPEG",
            exposure_mode="APERTURE_PRIORITY",
        )
        self.assertFalse(bad_jpeg.passed)
        self._assert_err(bad_jpeg, P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1)

    def test_74_group_d_sort_and_auto_switch_slot1_vault_erofs(self) -> None:
        for bad_kw in (
            {"recording_media": "SORT_RECORDING"},
            {"recording_media": "SIMULTANEOUS_RECORDING"},
            {"auto_switch_media": "ON"},
            {"auto_switch_failover_to_slot1_requested": True},
            {"rec_target_slot": 1},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self.assertTrue(res.slot1_tier0_vault_mutated, bad_kw)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EROFS}")

    def test_75_group_d_usb_lun_single_exposes_slot1_not_slot2_hazard(self) -> None:
        bad_single = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True, usb_lun_setting="SINGLE"
        )
        self.assertFalse(bad_single.passed)
        self._assert_err(bad_single, P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE)
        bad_claim = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True, claimed_usb_lun_single_exposes_slot2=True
        )
        self.assertFalse(bad_claim.passed)

    def test_76_group_d_host_msc_spotlight_fseventsd_fsck_isolation_required(self) -> None:
        for bad_kw in (
            {"host_msc_isolated": False},
            {"host_spotlight_fseventsd_fsck_unblocked": True},
            {"air_gapped_bench": False},
            {"claimed_usb_settings_wiped_by_camera_reset": True},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE)

    def test_77_group_d_np_fz100_and_dc_c1_65w_5a_pd_gate(self) -> None:
        ok_dcc1 = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            power_source="DC_C1_COUPLER",
            np_fz100_inserted=False,
            dc_c1_coupler_inserted=True,
            dc_c1_pd_watts=65.0,
            dc_c1_cable_amps=5.0,
        )
        self.assertTrue(ok_dcc1.passed, ok_dcc1.errors)

        bad_under_watt = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            power_source="DC_C1_COUPLER",
            np_fz100_inserted=False,
            dc_c1_coupler_inserted=True,
            dc_c1_pd_watts=45.0,
            dc_c1_cable_amps=5.0,
        )
        self.assertFalse(bad_under_watt.passed)
        self._assert_err(bad_under_watt, P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE)

        bad_usb_pd_nobatt = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            power_source="USB_PD_BODY",
            np_fz100_inserted=False,
        )
        self.assertFalse(bad_usb_pd_nobatt.passed)

        bad_claim = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            expect_batteryless_usb_pd_without_dc_c1=True,
        )
        self.assertFalse(bad_claim.passed)

    def test_78_group_d_dormant_uvc_on_both_fx3_and_fx6_eopnotsupp(self) -> None:
        for bad_kw in (
            {"dormant_uvc_streaming_requested": True},
            {"fx3_native_uvc_present_claimed": True},
            {"fx6_native_uvc_present_claimed": True},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT)
            self.assertFalse(res.fx3_native_uvc_present)
            self.assertFalse(res.fx6_native_uvc_present)
            self._assert_err_contains(res, f"errno={P334_ERRNO_EOPNOTSUPP}")

    def test_79_group_d_streaming_and_rec_media_during_hdmi_block_slot1(self) -> None:
        bad_stream = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            streaming_protocol="RTMPS",
            movie_rec_during_streaming="ENABLE",
            rec_target_slot=1,
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
        )
        self.assertFalse(bad_stream.passed)
        self._assert_err(bad_stream, P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT)

        bad_hdmi_slot1 = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            rec_media_dur_hdmi_output="ON",
            rec_target_slot=1,
        )
        self.assertFalse(bad_hdmi_slot1.passed)
        self._assert_err(bad_hdmi_slot1, P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT)

    def test_80_group_d_h0_h3_immutability_drift_rejected(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=1,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)
        self.assertEqual(res.h0_equals_h3_count, 15)

    def test_81_group_d_dual_media_receipt_distinct_st_dev_enforced(self) -> None:
        bundle = build_simulated_phase334_tier0_receipts()
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            receipt_a_bytes=bundle["receipt_a_bytes"],
            receipt_b_bytes=bundle["receipt_b_bytes"],
            st_dev_a_override=101,
            st_dev_b_override=101,
            body_serial=bundle["body_serial"],
            emmc_cid=bundle["emmc_cid"],
            h0_baselines_a=bundle["h0_baselines_a"],
            h0_baselines_b=bundle["h0_baselines_b"],
            h3_baselines=bundle["h3_baselines"],
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_82_group_d_trivial_serial_or_cid_rejected(self) -> None:
        bundle = build_simulated_phase334_tier0_receipts()
        for bad_kw in (
            {"body_serial": "000000000000"},
            {"emmc_cid": "0" * 32},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                receipt_a_bytes=bundle["receipt_a_bytes"],
                receipt_b_bytes=bundle["receipt_b_bytes"],
                st_dev_a_override=101,
                st_dev_b_override=202,
                body_serial=bad_kw.get("body_serial", bundle["body_serial"]),
                emmc_cid=bad_kw.get("emmc_cid", bundle["emmc_cid"]),
                h0_baselines_a=bundle["h0_baselines_a"],
                h0_baselines_b=bundle["h0_baselines_b"],
                h3_baselines=bundle["h3_baselines"],
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_83_group_d_single_receipt_missing_copy_b_rejected(self) -> None:
        bundle = build_simulated_phase334_tier0_receipts()
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            receipt_a_bytes=bundle["receipt_a_bytes"],
            st_dev_a_override=101,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_84_group_d_file_based_dual_media_receipts_distinct_files(self) -> None:
        bundle = build_simulated_phase334_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            p_a = Path(tmp) / "copy_a.bin"
            p_b = Path(tmp) / "copy_b.bin"
            p_a.write_bytes(bundle["receipt_a_bytes"])
            p_b.write_bytes(bundle["receipt_b_bytes"])
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=301,
                st_dev_b_override=302,
                body_serial=bundle["body_serial"],
                emmc_cid=bundle["emmc_cid"],
                h0_baselines_a=bundle["h0_baselines_a"],
                h0_baselines_b=bundle["h0_baselines_b"],
                h3_baselines=bundle["h3_baselines"],
            )
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.tier0_receipt_verified)

    def test_85_group_d_fail_closed_redlines_all_blocked(self) -> None:
        for bad_kw in (
            {"e_nd_actuator_tx_count": 1},
            {"wireless_rf_packets_emitted": 1},
            {"slot1_data_sector_writes": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(res.passed, bad_kw)
            self._assert_err(res, P334_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_86_group_d_invalid_usb_conn_mode_rejected(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True, usb_connection_mode="USB_STREAMING"
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE)

    def test_87_group_d_dc_c1_under_5a_cable_rejected(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True,
            power_source="DC_C1_COUPLER",
            np_fz100_inserted=False,
            dc_c1_coupler_inserted=True,
            dc_c1_pd_watts=100.0,
            dc_c1_cable_amps=3.0,
        )
        self.assertFalse(res.passed)

    def test_88_group_d_missing_receipt_path_rejected(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            receipt_a_path=Path("/nonexistent/copy_a.bin"),
            receipt_b_path=Path("/nonexistent/copy_b.bin"),
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_89_group_d_uncompressed_raw_allowed(self) -> None:
        res = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
            simulate_bench_dry_run=True, raw_file_type="UNCOMPRESSED"
        )
        self.assertTrue(res.passed, res.errors)

    def test_90_group_d_orchestrator_failure_sets_blocked_go_no_go(self) -> None:
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
            usb_lun_setting="SINGLE",
        )
        self.assertEqual(
            rep.go_no_go,
            P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE,
        )
        self.assertLess(rep.check_groups_passed, 4)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    # ------------------------------------------------------------------
    # 91-100: Tamper Verify, Markdown, In-Process & Subprocess CLI
    # ------------------------------------------------------------------

    def test_91_verify_phase334_report_detects_sha256_tamper(self) -> None:
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        tampered = rep.to_dict()
        tampered["report_sha256"] = "0" * 64
        vr = verify_phase334_report(tampered)
        self.assertFalse(vr.valid)
        self.assertTrue(any("report_sha256 mismatch" in e for e in vr.errors))

    def test_92_verify_phase334_report_detects_locked_boolean_or_zero_tamper(self) -> None:
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        tampered = rep.to_dict()
        tampered["overall_ready_for_hardware_attach"] = True
        tampered["raw_firmware_bytes_leaked"] = 4
        vr = verify_phase334_report(tampered)
        self.assertFalse(vr.valid)
        self.assertTrue(any("overall_ready_for_hardware_attach" in e for e in vr.errors))
        self.assertTrue(any("raw_firmware_bytes_leaked" in e for e in vr.errors))

    def test_93_render_phase334_markdown_contains_all_wave64_65_sections(self) -> None:
        rep = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        md = render_phase334_markdown(rep)
        for token in (
            "Phase 334",
            rep.schema_version,
            "Cam ID + Reel#",
            "Round-57",
            "Power Save by Monitor",
            "Lossless Comp",
            "Slot 1 ONLY hazard",
            rep.report_sha256,
        ):
            self.assertIn(token, md)

    def test_94_in_process_cli_default_returns_rc2(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main([
                "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun",
                "--force-clean-room",
                "--json",
            ])
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["overall_status"], P334_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(payload["check_groups_passed"], 4)

    def test_95_in_process_cli_simulate_dry_run_returns_rc0(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main([
                "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--summary",
            ])
        self.assertEqual(rc, 0)
        self.assertIn("DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", buf.getvalue())

    def test_96_cli_writes_json_and_markdown_out_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jpath = Path(tmp) / "p334.json"
            mpath = Path(tmp) / "p334.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = fx6_cli_main([
                    "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun",
                    "--simulate-bench-dry-run",
                    "--force-clean-room",
                    "--output",
                    str(jpath),
                    "--markdown-out",
                    str(mpath),
                    "--summary",
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(jpath.is_file())
            self.assertTrue(mpath.is_file())
            loaded = json.loads(jpath.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], P334_SCHEMA)
            self.assertTrue(verify_phase334_report(loaded).valid)

    def test_97_subprocess_cli_help_exits_0(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("simulate-bench-dry-run", proc.stdout)

    def test_98_subprocess_cli_default_exits_2_clean_room(self) -> None:
        proc = _run_cli_subprocess(["--summary"], extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", proc.stdout)

    def test_99_subprocess_cli_dry_run_clean_room_test_env_exits_0(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_CLEAN_ROOM_TEST": "1"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase334_report(payload).valid)

    def test_100_subprocess_cli_dry_run_local_donor_mode_exits_0(self) -> None:
        proc = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn(payload["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase334_report(payload).valid)


if __name__ == "__main__":
    unittest.main()
