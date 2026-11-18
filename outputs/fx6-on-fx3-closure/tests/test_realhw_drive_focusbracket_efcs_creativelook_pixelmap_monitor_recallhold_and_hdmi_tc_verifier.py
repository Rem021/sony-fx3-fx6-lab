"""Dual-mode unit tests (100 cases) for Phase 338 (`preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc`):
17th Real-Hardware Physical Bench Readiness Verifier across Waves 66-67 check groups (`A..D`)
covering Still [Drive Mode] (Hi+ 10fps / >F11 1st-frame AF lock), 100% Dormant [Focus Bracket]
myth-busting, 2-option [Shutter Type] (NO Auto, 1/250 s X-Sync), Reset-immune [e-Front Curtain Shut.]
(`front_curtaion_shutter`), [Long Exposure NR] / [High ISO NR] vs FX6 APR, 10-preset + 6-custom
[Creative Look] (asymmetric 0..9 Fade/Sharpness/Clarity) & dormant [Soft Skin Effect], Playback
[Delete]/[Protect]/[Recover Image DB] Slot-1 EROFS=30 firewall, [Auto Pixel Mapping] & manual
[Pixel Mapping] (`pixel_mappinng`/`excuted`) & Silent Mode shutdown click, myth-busting Setup ->
[Monitor] (3 Reset-immune items & thermal clamp; NOT [Finder/Monitor]) & dormant EVF, Still
P/A/S/M-only [Recall Custom hold 1-3] (11 slots, ZERO standalone WB), and Setup -> [External Output]
(`24.00p` reboot, `REC Control <- TC Output`, `ctrl_for_hmdi`, dormant `4K/2K` & `24p/60p`, Slot-1
`EROFS=30` firewall) + 16/16 `H0 == H3` Dual-Media 528B `FX3RCPT1` Tier-0 Gate.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and donorless CI (`work_root=None`) modes with
zero `.pyc` emission, zero persistent writes, and cross-platform CI headroom.
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
    REQUIRED_H0_BASELINE_KEYS,
    build_default_h0_baselines,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    SIXTEEN_STORAGE_SURFACES,
)
from fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier import (  # noqa: E402
    P338_ABSENT_XSYNC_1_320_HITS,
    P338_AUTO_PIXEL_MAPPING_RESID16_HEX,
    P338_BOUNDED_DONOR_PATHS,
    P338_CHECK_GROUP_A_ID,
    P338_CHECK_GROUP_B_ID,
    P338_CHECK_GROUP_C_ID,
    P338_CHECK_GROUP_D_ID,
    P338_CONT_AF_TRACK_MAX_APERTURE_F,
    P338_CONT_FPS_BY_TIER,
    P338_CONT_SPEED_EXACT_FOUR_TIERS,
    P338_CREATIVE_LOOK_CUSTOM_RESID16_HEX,
    P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES,
    P338_CREATIVE_LOOK_RESET_RESID16_HEX,
    P338_CREATIVE_LOOK_RESID16_HEX,
    P338_CREATIVE_LOOK_SIXTEEN_ELF_SLOTS,
    P338_CREATIVE_LOOK_SIX_CUSTOM_SLOTS,
    P338_CREATIVE_LOOK_TEN_PRESETS,
    P338_CTRL_FOR_HDMI_SONY_TYPO_BKID,
    P338_DELETE_BASE_RESID16_HEX,
    P338_DELETE_CONFIRM_OPTIONS,
    P338_DELETE_FIVE_SCOPES,
    P338_DISPLAY_MEDIA_INFO_BASE_RESID16_HEX,
    P338_DISPLAY_MEDIA_INFO_STILL_CAP,
    P338_DISPLAY_MEDIA_INFO_TYPO_SYMBOL,
    P338_DORMANT_ANTI_DISTORTION_SHUTTER_AUTO_RESID16_HEX,
    P338_DORMANT_EVF_MENU_ITEMS,
    P338_DORMANT_FOCUS_BRACKET_BKIDS,
    P338_DORMANT_FOCUS_BRACKET_ENUM,
    P338_DORMANT_FOCUS_BRACKET_UXC_RESIDS,
    P338_DORMANT_FX6_VF_ADJUST_FOUR_SUBITEMS,
    P338_DORMANT_HDMI_EXTERNAL_ITEMS,
    P338_DORMANT_SOFT_SKIN_BKID,
    P338_DORMANT_SOFT_SKIN_RESID16_HEX,
    P338_DRIVE_MODE_RESID16_HEX,
    P338_EFCS_RESID16_HEX,
    P338_EFCS_SONY_ELF_TYPO_BKID,
    P338_ERRNO_EOPNOTSUPP,
    P338_ERRNO_EROFS,
    P338_FLASH_XSYNC_DENOMINATOR,
    P338_FOCUS_BRACKET_ILC2210_HITS,
    P338_FOUR_K_OUTPUT_SET_TYPO_SYMBOL,
    P338_GA_ERR_DORMANT_FOCUS_BRACKET_MYTH,
    P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT,
    P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR,
    P338_GA_ERR_MODEL_OR_FW_FLOOR,
    P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE,
    P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT,
    P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS,
    P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT,
    P338_GB_ERR_DORMANT_SOFT_SKIN_EFFECT,
    P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING,
    P338_GC_ERR_DORMANT_EVF_OR_FX6_VF_ADJUST,
    P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP,
    P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR,
    P338_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT,
    P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS,
    P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS,
    P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE,
    P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
    P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS,
    P338_HIGH_ISO_NR_RESID16_HEX,
    P338_LONG_EXP_NR_MIN_SHUTTER_SECONDS,
    P338_LONG_EXP_NR_RESID16_HEX,
    P338_MANUAL_PIXEL_MAPPING_RESID16_HEX,
    P338_MONITOR_EXACT_THREE_ITEMS,
    P338_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P338_PIXEL_MAPPING_BATTERY_CHECK_SYMBOL,
    P338_PIXEL_MAPPING_MIN_BATTERY_PCT,
    P338_PIXEL_MAPPING_RECOMMENDED_INTERVAL_DAYS,
    P338_PIXEL_MAPPING_SONY_TYPO_NOTIFICATION_BKID,
    P338_PIXEL_MAPPING_SONY_TYPO_STATUS_BKID,
    P338_PROTECT_BASE_RESID16_HEX,
    P338_RECALL_CUSTOM_HOLD_ABSENT_WB_SYMBOL,
    P338_RECALL_CUSTOM_HOLD_ELF_PREFIX,
    P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS,
    P338_RECALL_CUSTOM_HOLD_STILL_EXPOSURE_MODES,
    P338_RECALL_CUSTOM_HOLD_UXC_RESIDS,
    P338_RECALL_CUSTOM_HOLD_WB_HITS,
    P338_RECOVER_IMAGE_DB_RESID16_HEX,
    P338_SCHEMA,
    P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS,
    P338_SHUTTER_TYPE_RESID16_HEX,
    P338_SILENT_AUTO_PM_SHUTTER_MUTE_SYMBOL,
    P338_SONY_HELP_GUIDE_ID,
    P338_STORAGE_SURFACE_COUNT,
    P338_VERSION,
    PHASE338_E_ND_ACTUATOR_TX_COUNT,
    PHASE338_PASSIVE_TX_BYTES_EMITTED,
    PHASE338_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE338_SLOT1_DATA_SECTOR_WRITES,
    PHASE338_USB_PACKETS_TRANSMITTED,
    PHASE338_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_338_CHECK_GROUP_IDS,
    PHASE_338_SCHEMA,
    PHASE_338_VERSION,
    _canonical_sha256_dict,
    build_simulated_phase338_tier0_receipts,
    evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr,
    evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb,
    evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf,
    evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0,
    evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight,
    inspect_phase338_donors_bounded,
    render_phase338_markdown,
    resolve_phase338_donor_file_or_none,
    run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight,
    verify_phase338_report,
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
            "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase338Preflight17Verifier(unittest.TestCase):
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
    # 01-14: Exports, Schema, Four-Mode Donorless CI & Determinism
    # ------------------------------------------------------------------

    def test_01_package_exports_and_schema_constants(self) -> None:
        self.assertTrue(
            hasattr(
                fx6_closure,
                "run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight",
            )
        )
        self.assertTrue(
            hasattr(
                fx6_closure,
                "evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight",
            )
        )
        self.assertEqual(P338_VERSION, PHASE_338_VERSION)
        self.assertEqual(P338_SCHEMA, PHASE_338_SCHEMA)
        self.assertEqual(P338_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_338_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_338_CHECK_GROUP_IDS,
            (
                P338_CHECK_GROUP_A_ID,
                P338_CHECK_GROUP_B_ID,
                P338_CHECK_GROUP_C_ID,
                P338_CHECK_GROUP_D_ID,
            ),
        )

    def test_02_locked_zero_telemetry_constants(self) -> None:
        self.assertEqual(PHASE338_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE338_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE338_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE338_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE338_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE338_E_ND_ACTUATOR_TX_COUNT, 0)

    def test_03_force_clean_room_env_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            res = inspect_phase338_donors_bounded()
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(res.donor_tree_present)
            self.assertEqual(res.bytes_read_total, 0)
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            self.assertTrue(res.within_budget)

    def test_04_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            res = inspect_phase338_donors_bounded()
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(res.donor_tree_present)
            self.assertEqual(res.bytes_read_total, 0)
            self.assertTrue(res.within_budget)

    def test_05_donorless_work_root_none_fallback(self) -> None:
        self.assertIsNone(resolve_phase338_donor_file_or_none(None, P338_BOUNDED_DONOR_PATHS[0][1]))
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "", "FX3_CLEAN_ROOM_TEST": ""}, clear=False):
            with mock.patch(
                "fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.iter_work_roots",
                return_value=(),
            ):
                res = inspect_phase338_donors_bounded(force_clean_room=False)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertFalse(res.donor_tree_present)
                self.assertEqual(res.bytes_read_total, 0)
                self.assertEqual(res.checked_paths, ())

    def test_06_nonexistent_work_root_fallback_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing_donor_root"
            res = inspect_phase338_donors_bounded(force_clean_room=False, work_root=missing)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(res.donor_tree_present)
            self.assertEqual(res.bytes_read_total, 0)

    def test_07_local_donor_bounded_o_rdonly_synthetic_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _lbl, rel in P338_BOUNDED_DONOR_PATHS:
                fpath = root / rel
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_bytes(b"\x7fELF" + b"\x00" * 128)
            res = inspect_phase338_donors_bounded(force_clean_room=False, work_root=root)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(res.donor_tree_present)
            self.assertTrue(res.fx3_appfw_present)
            self.assertTrue(res.fx6_appfw_present)
            self.assertTrue(res.fx3_uxc_present)
            self.assertEqual(len(res.checked_paths), len(P338_BOUNDED_DONOR_PATHS))
            self.assertEqual(res.bytes_read_total, 64 * len(P338_BOUNDED_DONOR_PATHS))
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            self.assertTrue(res.within_budget)

    def test_08_real_workspace_bounded_donor_check_if_present(self) -> None:
        res = inspect_phase338_donors_bounded(force_clean_room=False)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.within_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertLessEqual(res.bytes_read_total, 64 * len(P338_BOUNDED_DONOR_PATHS))

    def test_09_default_preflight_awaits_physical_tier0_receipt(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.overall_status, P338_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase338_report(rep).valid)

    def test_10_simulate_bench_dry_run_mode_passes_16_of_16_h0_h3(self) -> None:
        rep = evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase338_report(rep).valid)

    def test_11_deterministic_json_strips_elapsed_seconds_recursively(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        det_str = rep.to_deterministic_json()
        self.assertNotIn("elapsed_seconds", det_str)
        det_obj = json.loads(det_str)
        self.assertNotIn("elapsed_seconds", det_obj["donor_inspection"])
        self.assertTrue(verify_phase338_report(det_obj).valid)

    def test_12_deterministic_sha256_matches_across_runs_with_varied_timing(self) -> None:
        times = iter([10.0, 10.001, 200.0, 200.095])
        with mock.patch(
            "fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.time.monotonic",
            side_effect=lambda: next(times),
        ):
            r1 = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
            )
            r2 = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
            )
        self.assertNotEqual(r1.donor_inspection.elapsed_seconds, r2.donor_inspection.elapsed_seconds)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.to_deterministic_json(), r2.to_deterministic_json())
        self.assertEqual(
            hashlib.sha256(r1.to_deterministic_json().encode("utf-8")).hexdigest(),
            hashlib.sha256(r2.to_deterministic_json().encode("utf-8")).hexdigest(),
        )

    def test_13_donorless_preflight_works_cleanly(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "", "FX3_CLEAN_ROOM_TEST": ""}, clear=False):
            with mock.patch(
                "fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.iter_work_roots",
                return_value=(),
            ):
                rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
                    simulate_bench_dry_run=True,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
                self.assertTrue(verify_phase338_report(rep).valid)

    def test_14_markdown_renderer_contains_all_four_groups(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        md = render_phase338_markdown(rep)
        for g_id in PHASE_338_CHECK_GROUP_IDS:
            self.assertIn(g_id, md)
        self.assertIn("Phase 338", md)
        self.assertIn("16/16", md)
        self.assertIn(P338_EFCS_SONY_ELF_TYPO_BKID, md)
        self.assertIn(P338_CTRL_FOR_HDMI_SONY_TYPO_BKID, md)

    # ------------------------------------------------------------------
    # 15-38: Group A (Wave 66 §§1-2) Drive, Focus Bracket, Shutter Type, EFCS, NR
    # ------------------------------------------------------------------

    def test_15_ga_model_fw_and_help_guide_floor(self) -> None:
        res = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            body_model_id=0xDEADBEEF,
            body_fw="6.01",
            sony_help_guide_id="ilc/9999",
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P338_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_16_ga_cont_shooting_four_tiers_and_exact_fps(self) -> None:
        self.assertEqual(P338_CONT_SPEED_EXACT_FOUR_TIERS, ("HI_PLUS", "HI", "MID", "LO"))
        self.assertEqual(dict(P338_CONT_FPS_BY_TIER), {"HI_PLUS": 10, "HI": 8, "MID": 6, "LO": 3})
        for tier, fps in P338_CONT_FPS_BY_TIER.items():
            res = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                drive_mode="CONT_SHOOTING",
                cont_speed_tier=tier,
                long_exposure_nr="OFF",
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.cont_max_fps, fps)

    def test_17_ga_cont_above_f11_locks_af_on_first_frame(self) -> None:
        self.assertEqual(P338_CONT_AF_TRACK_MAX_APERTURE_F, 11.0)
        ok = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_SHOOTING",
            cont_speed_tier="HI_PLUS",
            aperture_f_number=16.0,
            long_exposure_nr="OFF",
            expect_af_tracks_all_frames_above_f11=False,
        )
        self.assertTrue(ok.passed)
        self.assertTrue(ok.af_first_frame_locked_above_f11)

        bad = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_SHOOTING",
            cont_speed_tier="HI",
            aperture_f_number=13.0,
            long_exposure_nr="OFF",
            expect_af_tracks_all_frames_above_f11=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_18_ga_uncompressed_raw_or_flash_reduces_burst_rate(self) -> None:
        bad_raw = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_SHOOTING",
            still_file_format="RAW",
            raw_file_type="UNCOMPRESSED",
            long_exposure_nr="OFF",
            expect_full_cont_fps_with_uncompressed_raw_or_flash=True,
        )
        self.assertFalse(bad_raw.passed)
        self._assert_err(bad_raw, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

        bad_flash = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_SHOOTING",
            flash_enabled=True,
            long_exposure_nr="OFF",
            expect_full_cont_fps_with_uncompressed_raw_or_flash=True,
        )
        self.assertFalse(bad_flash.passed)
        self._assert_err(bad_flash, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_19_ga_drive_mode_still_only_movie_sq_rejected(self) -> None:
        bad_movie = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            shoot_mode="MOVIE",
            drive_mode="CONT_SHOOTING",
            long_exposure_nr="OFF",
        )
        self.assertFalse(bad_movie.passed)
        self._assert_err(bad_movie, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)
        self._assert_err_contains(bad_movie, f"errno={P338_ERRNO_EOPNOTSUPP}")

        bad_sq = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            shoot_mode="S_AND_Q",
            claimed_drive_mode_active_in_movie_or_sq=True,
        )
        self.assertFalse(bad_sq.passed)
        self._assert_err(bad_sq, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_20_ga_drive_mode_resettable_and_interval_defaults_electronic(self) -> None:
        bad_reset = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            reset_action="CAMERA_SETTINGS_RESET",
            drive_mode="WB_BRACKET",
        )
        self.assertFalse(bad_reset.passed)
        self._assert_err(bad_reset, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

        bad_claim = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            claimed_drive_mode_resists_camera_reset=True,
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

        bad_interval = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            claimed_interval_default_mech_shutter=True,
        )
        self.assertFalse(bad_interval.passed)
        self._assert_err(bad_interval, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_21_ga_self_timer_single_and_cont_six_combos(self) -> None:
        for sec in (10, 5, 2):
            ok_s = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                drive_mode="SELF_TIMER_SINGLE",
                self_timer_sec=sec,
            )
            self.assertTrue(ok_s.passed)
            for cnt in (3, 5):
                ok_c = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                    drive_mode="SELF_TIMER_CONT",
                    self_timer_sec=sec,
                    self_timer_cont_images=cnt,
                )
                self.assertTrue(ok_c.passed)

        bad_cnt = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="SELF_TIMER_CONT",
            self_timer_sec=10,
            self_timer_cont_images=10,
        )
        self.assertFalse(bad_cnt.passed)
        self._assert_err(bad_cnt, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_22_ga_dro_bracket_locked_under_hlg_pp_log_and_cont_bracket_iauto(self) -> None:
        for kw in ({"hlg_still_image": "ON"}, {"picture_profile": "PP11"}, {"log_shooting_mode": "CINE_EI"}):
            bad_dro = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                drive_mode="DRO_BRACKET",
                **kw,
            )
            self.assertFalse(bad_dro.passed)
            self._assert_err(bad_dro, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

        bad_iauto = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="SINGLE_BRACKET",
            exposure_mode="INTELLIGENT_AUTO",
        )
        self.assertFalse(bad_iauto.passed)
        self._assert_err(bad_iauto, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_23_ga_fx6_has_no_still_drive_mode_menu(self) -> None:
        bad = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            fx6_has_still_drive_mode_menu_claimed=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT)

    def test_24_ga_dormant_focus_bracket_myth_busted_fx3_and_fx6(self) -> None:
        self.assertEqual(P338_DRIVE_MODE_RESID16_HEX, "0x7228")
        self.assertEqual(P338_DORMANT_FOCUS_BRACKET_UXC_RESIDS, ("0x7563", "0x6915"))
        self.assertEqual(len(P338_DORMANT_FOCUS_BRACKET_BKIDS), 6)
        self.assertEqual(P338_FOCUS_BRACKET_ILC2210_HITS, 0)
        self.assertIn("FOCUS_BRACKET", P338_DORMANT_FOCUS_BRACKET_ENUM)

        for flag in (
            "dormant_focus_bracket_requested",
            "fx3_focus_bracket_present_claimed",
            "fx6_focus_bracket_present_claimed",
            "claimed_focus_bracket_in_ilc2210",
        ):
            bad = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self.assertFalse(bad.fx3_focus_bracket_present)
            self.assertFalse(bad.fx6_focus_bracket_present)
            self._assert_err(bad, P338_GA_ERR_DORMANT_FOCUS_BRACKET_MYTH)
            self._assert_err_contains(bad, f"errno={P338_ERRNO_EOPNOTSUPP}")

    def test_25_ga_shutter_type_strictly_two_options_no_auto(self) -> None:
        self.assertEqual(P338_SHUTTER_TYPE_RESID16_HEX, "0x63db")
        self.assertEqual(P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS, ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER"))
        self.assertEqual(P338_DORMANT_ANTI_DISTORTION_SHUTTER_AUTO_RESID16_HEX, "0x66b8")

        bad_enum = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(shutter_type="AUTO")
        self.assertFalse(bad_enum.passed)
        self._assert_err(bad_enum, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

        bad_req = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            dormant_shutter_type_auto_requested=True
        )
        self.assertFalse(bad_req.passed)
        self._assert_err(bad_req, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

        bad_claim = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            fx3_shutter_type_auto_present_claimed=True
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

    def test_26_ga_flash_xsync_single_1_250_ceiling_no_1_320(self) -> None:
        self.assertEqual(P338_FLASH_XSYNC_DENOMINATOR, 250)
        self.assertEqual(P338_ABSENT_XSYNC_1_320_HITS, 0)

        bad_denom = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(flash_sync_denominator=320)
        self.assertFalse(bad_denom.passed)
        self._assert_err(bad_denom, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

        bad_claim = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            claimed_1_320_xsync_supported=True
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

    def test_27_ga_electronic_shutter_and_silent_mode_five_lockouts(self) -> None:
        ok_elec = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            shutter_type="ELECTRONIC_SHUTTER",
            long_exposure_nr="OFF",
        )
        self.assertTrue(ok_elec.passed, ok_elec.errors)

        for lock_kw in (
            {"flash_enabled": True},
            {"long_exposure_nr": "ON"},
            {"bulb_enabled": True, "long_exposure_nr": "OFF"},
            {"anti_flicker_shoot": True, "long_exposure_nr": "OFF"},
            {"efcs_active_claimed": True, "long_exposure_nr": "OFF"},
        ):
            bad_e = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                shutter_type="ELECTRONIC_SHUTTER",
                **lock_kw,
            )
            self.assertFalse(bad_e.passed, lock_kw)
            self._assert_err(bad_e, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

            bad_s = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
                silent_mode="ON",
                **lock_kw,
            )
            self.assertFalse(bad_s.passed, lock_kw)
            self._assert_err(bad_s, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

    def test_28_ga_efcs_sony_typo_and_reset_immunity(self) -> None:
        self.assertEqual(P338_EFCS_RESID16_HEX, "0x64c6")
        self.assertEqual(P338_EFCS_SONY_ELF_TYPO_BKID, "BKID_APP_setting_front_curtaion_shutter")

        ok_reset = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            reset_action="CAMERA_SETTINGS_RESET",
            e_front_curtain_shutter="OFF",
        )
        self.assertTrue(ok_reset.passed, ok_reset.errors)

        bad_init = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            reset_action="INITIALIZE",
            e_front_curtain_shutter="OFF",
        )
        self.assertFalse(bad_init.passed)
        self._assert_err(bad_init, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

        bad_claim = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            claimed_efcs_wiped_by_camera_reset=True
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE)

    def test_29_ga_long_exposure_nr_1s_threshold_and_lockouts(self) -> None:
        self.assertEqual(P338_LONG_EXP_NR_RESID16_HEX, "0x6465")
        self.assertEqual(P338_LONG_EXP_NR_MIN_SHUTTER_SECONDS, 1.0)

        bad_sub1s = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            shutter_seconds=0.5,
            claimed_long_exp_nr_active_below_1s=True,
        )
        self.assertFalse(bad_sub1s.passed)
        self._assert_err(bad_sub1s, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

        bad_cont = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_SHOOTING",
            long_exposure_nr="ON",
        )
        self.assertFalse(bad_cont.passed)
        self._assert_err(bad_cont, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

        bad_cb = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            drive_mode="CONT_BRACKET",
            long_exposure_nr="ON",
        )
        self.assertFalse(bad_cb.passed)
        self._assert_err(bad_cb, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

    def test_30_ga_high_iso_nr_three_options_and_no_arw_mutation(self) -> None:
        self.assertEqual(P338_HIGH_ISO_NR_RESID16_HEX, "0x650b")
        self.assertEqual(P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS, ("NORMAL", "LOW", "OFF"))

        for opt in P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS:
            ok = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(high_iso_nr=opt)
            self.assertTrue(ok.passed)

        bad_high = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            dormant_high_iso_nr_high_option_requested=True
        )
        self.assertFalse(bad_high.passed)
        self._assert_err(bad_high, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

        bad_arw = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            expect_high_iso_nr_modifies_arw_raw=True
        )
        self.assertFalse(bad_arw.passed)
        self._assert_err(bad_arw, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

    def test_31_ga_nr_resettable_iauto_lock_and_fx6_noise_suppression_apr(self) -> None:
        bad_reset = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            reset_action="CAMERA_SETTINGS_RESET",
            long_exposure_nr="OFF",
            high_iso_nr="OFF",
        )
        self.assertFalse(bad_reset.passed)
        self._assert_err(bad_reset, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

        bad_iauto = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            exposure_mode="INTELLIGENT_AUTO",
            long_exposure_nr="OFF",
        )
        self.assertFalse(bad_iauto.passed)
        self._assert_err(bad_iauto, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

        bad_fx6 = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
            fx6_noise_suppression_uses_still_nr_menu_claimed=True
        )
        self.assertFalse(bad_fx6.passed)
        self._assert_err(bad_fx6, P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR)

    # ------------------------------------------------------------------
    # 32-49: Group B (Wave 66 §§3-4) Creative Look, Soft Skin, Delete/Protect/Recover DB
    # ------------------------------------------------------------------

    def test_32_gb_creative_look_10_presets_and_6_custom_slots(self) -> None:
        self.assertEqual(P338_CREATIVE_LOOK_RESID16_HEX, "0x6823")
        self.assertEqual(P338_CREATIVE_LOOK_RESET_RESID16_HEX, "0x6c22")
        self.assertEqual(P338_CREATIVE_LOOK_CUSTOM_RESID16_HEX, "0x6c98")
        self.assertEqual(P338_CREATIVE_LOOK_TEN_PRESETS, ("ST", "PT", "NT", "VV", "VV2", "FL", "IN", "SH", "BW", "SE"))
        self.assertEqual(len(P338_CREATIVE_LOOK_SIX_CUSTOM_SLOTS), 6)
        self.assertEqual(len(P338_CREATIVE_LOOK_SIXTEEN_ELF_SLOTS), 16)

        for slot in (*P338_CREATIVE_LOOK_TEN_PRESETS, *P338_CREATIVE_LOOK_SIX_CUSTOM_SLOTS):
            ok = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(creative_look_slot=slot)
            self.assertTrue(ok.passed, f"{slot}: {ok.errors}")

        bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(creative_look_slot="CUSTOM_7")
        self.assertFalse(bad.passed)
        self._assert_err(bad, P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS)

    def test_33_gb_creative_look_exact_8_param_bounds_asymmetric_0_to_9(self) -> None:
        self.assertEqual(P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES["FADE"], (0, 9))
        self.assertEqual(P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES["SHARPNESS"], (0, 9))
        self.assertEqual(P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES["CLARITY"], (0, 9))
        self.assertEqual(P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES["SHARPNESS_RANGE"], (1, 5))
        self.assertEqual(P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES["CONTRAST"], (-9, 9))

        ok_edge = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            creative_look_contrast=-9,
            creative_look_highlights=9,
            creative_look_shadows=-9,
            creative_look_fade=9,
            creative_look_saturation=9,
            creative_look_sharpness=9,
            creative_look_sharpness_range=5,
            creative_look_clarity=9,
        )
        self.assertTrue(ok_edge.passed, ok_edge.errors)

        for neg_field in ("creative_look_fade", "creative_look_sharpness", "creative_look_clarity"):
            bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(**{neg_field: -1})
            self.assertFalse(bad.passed, neg_field)
            self._assert_err(bad, P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS)

        bad_range = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(creative_look_sharpness_range=0)
        self.assertFalse(bad_range.passed)
        self._assert_err(bad_range, P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS)

        bad_neg_claim = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            claimed_creative_look_fade_sharpness_clarity_accept_negative=True
        )
        self.assertFalse(bad_neg_claim.passed)
        self._assert_err(bad_neg_claim, P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS)

    def test_34_gb_creative_look_bw_se_saturation_and_movie_sharpness_range_lock(self) -> None:
        for mono in ("BW", "SE"):
            bad_sat = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
                creative_look_slot=mono,
                creative_look_saturation_adjusted=True,
            )
            self.assertFalse(bad_sat.passed)
            self._assert_err(bad_sat, P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT)

        for mode in ("MOVIE", "S_AND_Q"):
            bad_sr = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
                shoot_mode=mode,
                creative_look_sharpness_range_adjusted=True,
            )
            self.assertFalse(bad_sr.passed)
            self._assert_err(bad_sr, P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT)

    def test_35_gb_creative_look_locked_to_dash_under_pp_log_hlg_iauto_and_resettable(self) -> None:
        for kw in (
            {"picture_profile": "PP11"},
            {"log_shooting_mode": "CINE_EI"},
            {"hlg_still_image": "ON"},
            {"exposure_mode": "INTELLIGENT_AUTO"},
        ):
            ok_locked = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(**kw)
            self.assertTrue(ok_locked.passed)
            self.assertTrue(ok_locked.creative_look_locked_by_pp_log_hlg_iauto)

            bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
                expect_creative_look_active_under_pp_log_hlg_iauto=True,
                **kw,
            )
            self.assertFalse(bad.passed, kw)
            self._assert_err(bad, P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT)

        bad_reset = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            reset_action="CAMERA_SETTINGS_RESET",
            creative_look_slot="FL",
        )
        self.assertFalse(bad_reset.passed)
        self._assert_err(bad_reset, P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT)

        bad_claim = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            claimed_creative_look_resists_camera_reset=True
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT)

    def test_36_gb_dormant_soft_skin_effect_rejected_fx3_and_fx6(self) -> None:
        self.assertEqual(P338_DORMANT_SOFT_SKIN_RESID16_HEX, "0x76d9")
        self.assertEqual(P338_DORMANT_SOFT_SKIN_BKID, "BKID_APP_setting_soft_skin_effect")
        for flag in (
            "dormant_soft_skin_requested",
            "fx3_soft_skin_present_claimed",
            "fx6_soft_skin_present_claimed",
        ):
            bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self.assertFalse(bad.fx3_soft_skin_effect_present)
            self.assertFalse(bad.fx6_soft_skin_effect_present)
            self._assert_err(bad, P338_GB_ERR_DORMANT_SOFT_SKIN_EFFECT)

    def test_37_gb_delete_five_scopes_protect_skip_and_reset_immune_options(self) -> None:
        self.assertEqual(P338_DELETE_BASE_RESID16_HEX, "0xe504")
        self.assertEqual(P338_PROTECT_BASE_RESID16_HEX, "0xe2c9")
        self.assertEqual(len(P338_DELETE_FIVE_SCOPES), 5)
        self.assertEqual(P338_DELETE_CONFIRM_OPTIONS, ("CANCEL_FIRST", "DELETE_FIRST"))

        for scope in P338_DELETE_FIVE_SCOPES:
            ok = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
                delete_scope=scope,
                delete_write_requested=True,
                delete_write_slot=2,
            )
            self.assertTrue(ok.passed)

        bad_prot = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            protected_item_delete_attempted=True,
            slot_format_executed=False,
        )
        self.assertFalse(bad_prot.passed)
        self._assert_err(bad_prot, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)

        bad_copy = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            expect_copy_preserves_protect=True,
        )
        self.assertFalse(bad_copy.passed)
        self._assert_err(bad_copy, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)

        for flag in ("claimed_delete_confirm_wiped_by_camera_reset", "claimed_delete_twice_wiped_by_camera_reset"):
            bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(**{flag: True})
            self.assertFalse(bad.passed)
            self._assert_err(bad, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)

    def test_38_gb_recover_image_db_battery_gate_and_slot1_erofs30_firewall(self) -> None:
        self.assertEqual(P338_RECOVER_IMAGE_DB_RESID16_HEX, "0x711b")
        self.assertEqual(P338_DISPLAY_MEDIA_INFO_BASE_RESID16_HEX, "0xea2a")
        self.assertEqual(P338_DISPLAY_MEDIA_INFO_STILL_CAP, 40000)
        self.assertEqual(P338_DISPLAY_MEDIA_INFO_TYPO_SYMBOL, "NOT_DISPLAYNG")

        ok_slot2 = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            recover_image_db_requested=True,
            recover_image_db_slot=2,
            battery_soc_pct=85,
        )
        self.assertTrue(ok_slot2.passed)
        self.assertFalse(ok_slot2.slot1_tier0_vault_mutated)

        bad_low_bat = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
            recover_image_db_requested=True,
            recover_image_db_slot=2,
            battery_soc_pct=15,
        )
        self.assertFalse(bad_low_bat.passed)
        self._assert_err(bad_low_bat, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)

        for slot1_action in (
            {"recover_image_db_requested": True, "recover_image_db_slot": 1},
            {"delete_write_requested": True, "delete_write_slot": 1},
            {"protect_write_requested": True, "protect_write_slot": 1},
            {"slot1_data_sector_writes": 1},
        ):
            bad_s1 = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
                slot1_contains_tier0_dump=True,
                **slot1_action,
            )
            self.assertFalse(bad_s1.passed, slot1_action)
            self.assertTrue(bad_s1.slot1_tier0_vault_mutated)
            self._assert_err(bad_s1, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)
            self._assert_err_contains(bad_s1, f"errno={P338_ERRNO_EROFS}")

    def test_39_gb_recover_db_reset_init_immunity_and_display_media_info_40k(self) -> None:
        for flag in (
            "claimed_recover_db_wiped_by_reset_or_init",
            "claimed_display_media_info_mutates_media",
            "claimed_display_media_info_cap_not_40000",
        ):
            bad = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self._assert_err(bad, P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT)

    # ------------------------------------------------------------------
    # 40-54: Group C (Wave 67 §§1-2) Pixel Mapping, Silent Click, Setup->Monitor & EVF
    # ------------------------------------------------------------------

    def test_40_gc_auto_pixel_mapping_reset_immune_and_3day_advisory(self) -> None:
        self.assertEqual(P338_AUTO_PIXEL_MAPPING_RESID16_HEX, "0x7734")
        self.assertEqual(P338_MANUAL_PIXEL_MAPPING_RESID16_HEX, "0x61f7")
        self.assertEqual(P338_PIXEL_MAPPING_RECOMMENDED_INTERVAL_DAYS, 3)

        ok_reset = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            reset_action="CAMERA_SETTINGS_RESET",
            auto_pixel_mapping="OFF",
            days_since_pixel_mapping=5,
        )
        self.assertTrue(ok_reset.passed)
        self.assertTrue(len(ok_reset.warnings) >= 1)

        bad_init = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            reset_action="INITIALIZE",
            auto_pixel_mapping="OFF",
        )
        self.assertFalse(bad_init.passed)
        self._assert_err(bad_init, P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING)

        bad_claim = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            claimed_auto_pm_wiped_by_camera_reset=True
        )
        self.assertFalse(bad_claim.passed)
        self._assert_err(bad_claim, P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING)

    def test_41_gc_manual_pixel_mapping_lens_cap_battery_reboot_and_typos(self) -> None:
        self.assertEqual(
            P338_PIXEL_MAPPING_SONY_TYPO_NOTIFICATION_BKID,
            "BKID_APP_setting_notification_for_pixel_mappinng",
        )
        self.assertEqual(P338_PIXEL_MAPPING_SONY_TYPO_STATUS_BKID, "BKID_APP_pixel_mapping_excuted_status")
        self.assertEqual(P338_PIXEL_MAPPING_BATTERY_CHECK_SYMBOL, "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING")

        ok = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            manual_pixel_mapping_requested=True,
            lens_cap_attached=True,
            battery_soc_pct=P338_PIXEL_MAPPING_MIN_BATTERY_PCT,
        )
        self.assertTrue(ok.passed)
        self.assertIn(P338_PIXEL_MAPPING_SONY_TYPO_NOTIFICATION_BKID, ok.pixel_mapping_typo_bkids)
        self.assertIn(P338_PIXEL_MAPPING_SONY_TYPO_STATUS_BKID, ok.pixel_mapping_typo_bkids)

        for bad_kw in (
            {"lens_cap_attached": False},
            {"battery_soc_pct": 10},
            {"low_battery_warning": True},
            {"expect_manual_pm_without_reboot": True},
            {"unguarded_pm_calibration": True, "tier0_dump_active": True},
        ):
            bad = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
                manual_pixel_mapping_requested=True,
                **bad_kw,
            )
            self.assertFalse(bad.passed, bad_kw)
            self._assert_err(bad, P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING)

    def test_42_gc_pixel_mapping_no_usb_streaming_prm_haita(self) -> None:
        bad = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            claimed_usb_streaming_blocks_pixel_mapping_prm_haita=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING)

    def test_43_gc_silent_mode_target_auto_pm_shutdown_shutter_click_and_resettable(self) -> None:
        self.assertEqual(P338_SILENT_AUTO_PM_SHUTTER_MUTE_SYMBOL, "vdf_set_shutter_mute_by_pixel_mapping")

        ok_click = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            silent_mode="ON",
            silent_auto_pixel_mapping="ON",
        )
        self.assertTrue(ok_click.passed)
        self.assertTrue(ok_click.shutdown_shutter_click_triggered)

        bad_silence = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            silent_mode="ON",
            silent_auto_pixel_mapping="ON",
            expect_zero_shutter_sound_with_silent_auto_pm_on=True,
        )
        self.assertFalse(bad_silence.passed)
        self._assert_err(bad_silence, P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR)

        bad_reset = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            reset_action="CAMERA_SETTINGS_RESET",
            silent_auto_pixel_mapping="ON",
        )
        self.assertFalse(bad_reset.passed)
        self._assert_err(bad_reset, P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR)

        for flag in (
            "claimed_silent_auto_pm_resists_camera_reset",
            "fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed",
            "fx6_auto_black_balance_menu_present_claimed",
        ):
            bad = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self._assert_err(bad, P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR)

    def test_44_gc_setup_monitor_exact_three_reset_immune_items(self) -> None:
        self.assertEqual(
            P338_MONITOR_EXACT_THREE_ITEMS,
            ("MONITOR_BRIGHTNESS", "DISPLAY_QUALITY", "MONITOR_FLIP_DIRECTION"),
        )
        ok = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            reset_action="CAMERA_SETTINGS_RESET",
            monitor_brightness_mode="SUNNY_WEATHER",
            monitor_brightness_level=2,
            display_quality="HIGH",
            monitor_flip_direction="HORIZONTAL_FLIP",
        )
        self.assertTrue(ok.passed)

        bad_items = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            exposed_monitor_items=("MONITOR_BRIGHTNESS", "DISPLAY_QUALITY", "BRIGHT_MONITORING")
        )
        self.assertFalse(bad_items.passed)
        self._assert_err(bad_items, P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP)

        bad_level = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(monitor_brightness_level=5)
        self.assertFalse(bad_level.passed)
        self._assert_err(bad_level, P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP)

    def test_45_gc_display_quality_thermal_clamp_high_to_standard(self) -> None:
        ok_clamped = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            display_quality="HIGH",
            body_temp_elevated=True,
        )
        self.assertTrue(ok_clamped.passed)
        self.assertTrue(ok_clamped.display_quality_thermally_clamped)
        self.assertEqual(ok_clamped.display_quality, "STANDARD")

        bad_unclamped = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
            display_quality="HIGH",
            body_temp_elevated=True,
            expect_high_display_quality_unclamped_under_thermal=True,
        )
        self.assertFalse(bad_unclamped.passed)
        self._assert_err(bad_unclamped, P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP)

        for flag in ("claimed_monitor_3items_wiped_by_camera_reset", "claimed_bright_monitoring_in_setup_monitor"):
            bad = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self._assert_err(bad, P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP)

    def test_46_gc_dormant_evf_finder_monitor_and_fx6_vf_adjust_4subitems_rejected(self) -> None:
        self.assertEqual(len(P338_DORMANT_EVF_MENU_ITEMS), 4)
        self.assertEqual(P338_DORMANT_FX6_VF_ADJUST_FOUR_SUBITEMS, ("BACKLIGHT", "CONTRAST", "CHROMA", "COLOR_TEMP"))

        for flag_kw in (
            {"fx3_finder_monitor_menu_present_claimed": True},
            {"fx3_builtin_evf_present_claimed": True},
            {"dormant_evf_menu_requested": "VIEWFINDER_COLOR_TEMP"},
            {"fx6_vf_adjust_four_subitems_present_claimed": True},
        ):
            bad = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(**flag_kw)
            self.assertFalse(bad.passed, flag_kw)
            self.assertFalse(bad.fx3_builtin_evf_present)
            self.assertFalse(bad.fx3_finder_monitor_menu_present)
            self.assertFalse(bad.fx6_vf_adjust_four_subitems_present)
            self._assert_err(bad, P338_GC_ERR_DORMANT_EVF_OR_FX6_VF_ADJUST)
            self._assert_err_contains(bad, f"errno={P338_ERRNO_EOPNOTSUPP}")

    # ------------------------------------------------------------------
    # 47-72: Group D (Wave 67 §§3-4 & Tier-0) Recall Custom hold, HDMI/TC/REC, H0==H3
    # ------------------------------------------------------------------

    def test_47_gd_recall_custom_hold_strictly_still_pasm_only(self) -> None:
        self.assertEqual(P338_RECALL_CUSTOM_HOLD_UXC_RESIDS, ("0x60b4", "0x7581", "0x725b"))
        self.assertEqual(
            P338_RECALL_CUSTOM_HOLD_STILL_EXPOSURE_MODES,
            ("PROGRAM_AUTO", "APERTURE_PRIORITY", "SHUTTER_PRIORITY", "MANUAL_EXPOSURE"),
        )
        for em in P338_RECALL_CUSTOM_HOLD_STILL_EXPOSURE_MODES:
            for slot in (1, 2, 3):
                ok = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                    shoot_mode="PHOTO",
                    exposure_mode=em,
                    recall_custom_hold_active=True,
                    recall_custom_hold_slot=slot,
                )
                self.assertTrue(ok.passed, f"{em}/{slot}: {ok.errors}")

        for bad_kw in (
            {"shoot_mode": "MOVIE", "exposure_mode": "MANUAL_EXPOSURE"},
            {"shoot_mode": "S_AND_Q", "exposure_mode": "MANUAL_EXPOSURE"},
            {"shoot_mode": "PHOTO", "exposure_mode": "INTELLIGENT_AUTO"},
            {"shoot_mode": "MOVIE", "exposure_mode": "FLEXIBLE_EXP"},
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                recall_custom_hold_active=True,
                **bad_kw,
            )
            self.assertFalse(bad.passed, bad_kw)
            self._assert_err(bad, P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS)
            self._assert_err_contains(bad, f"errno={P338_ERRNO_EOPNOTSUPP}")

    def test_48_gd_recall_custom_hold_exact_11_slots_and_zero_standalone_wb(self) -> None:
        self.assertEqual(len(P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS), 11)
        self.assertEqual(P338_RECALL_CUSTOM_HOLD_ELF_PREFIX, "is_checked_recall_custom_hold")
        self.assertEqual(P338_RECALL_CUSTOM_HOLD_ABSENT_WB_SYMBOL, "shoot_set_registration_white_balance")
        self.assertEqual(P338_RECALL_CUSTOM_HOLD_WB_HITS, 0)

        bad_slots = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            recall_custom_hold_eleven_slots=(*P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS[:10], "white_balance")
        )
        self.assertFalse(bad_slots.passed)
        self._assert_err(bad_slots, P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS)

        for flag in (
            "recall_custom_hold_standalone_wb_requested",
            "fx3_recall_custom_hold_standalone_wb_present_claimed",
            "claimed_recall_custom_hold_wiped_by_camera_reset",
            "fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed",
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self._assert_err(bad, P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS)

    def test_49_gd_tracking_on_custom_key_still_afc_only(self) -> None:
        ok = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            shoot_mode="PHOTO",
            tracking_on_custom_key_active=True,
            tracking_on_custom_key_focus_mode="AF_C",
        )
        self.assertTrue(ok.passed)

        for bad_kw in (
            {"shoot_mode": "PHOTO", "tracking_on_custom_key_focus_mode": "AF_S"},
            {"shoot_mode": "MOVIE", "tracking_on_custom_key_focus_mode": "AF_C"},
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                tracking_on_custom_key_active=True,
                **bad_kw,
            )
            self.assertFalse(bad.passed, bad_kw)
            self._assert_err(bad, P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS)

    def test_50_gd_hdmi_rec_ctrl_requires_tc_output_on(self) -> None:
        ok = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            hdmi_tc_output="ON",
            hdmi_rec_control="ON",
        )
        self.assertTrue(ok.passed)

        bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            hdmi_tc_output="OFF",
            hdmi_rec_control="ON",
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

    def test_51_gd_hdmi_2400p_reboot_log_pplut_1080_clamp_and_sq_locks(self) -> None:
        bad_2400p = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            hdmi_4k_output_rate="24_00P",
            expect_2400p_no_reboot_or_mixed_playback=True,
        )
        self.assertFalse(bad_2400p.passed)
        self._assert_err(bad_2400p, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

        for kw in ({"log_shooting_mode": "CINE_EI"}, {"picture_profile": "PPLUT1"}):
            bad_2160 = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                rec_media_dur_hdmi_output="ON",
                hdmi_output_resolution="2160P",
                **kw,
            )
            self.assertFalse(bad_2160.passed, kw)
            self._assert_err(bad_2160, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

        for sq_bad in (
            {"rec_media_dur_hdmi_output": "OFF_HDMI_ONLY"},
            {"hdmi_raw_output": "ON"},
            {"hdmi_tc_output": "ON"},
        ):
            bad_sq = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                shoot_mode="S_AND_Q",
                **sq_bad,
            )
            self.assertFalse(bad_sq.passed, sq_bad)
            self._assert_err(bad_sq, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

    def test_52_gd_hdmi_info_display_raw_hdmi_only_ctrl_for_hmdi_typo_and_dormant_4k2k_24p60p(self) -> None:
        self.assertEqual(P338_CTRL_FOR_HDMI_SONY_TYPO_BKID, "BKID_APP_setting_ctrl_for_hmdi")
        self.assertEqual(P338_FOUR_K_OUTPUT_SET_TYPO_SYMBOL, "outpute")
        self.assertEqual(P338_DORMANT_HDMI_EXTERNAL_ITEMS, ("4K_2K_OUTPUT", "24P_60P_OUTPUT"))

        bad_info_raw = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            hdmi_raw_output="ON",
            expect_hdmi_info_display_active_with_raw_or_hdmi_only=True,
        )
        self.assertFalse(bad_info_raw.passed)
        self._assert_err(bad_info_raw, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

        bad_info_only = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            expect_hdmi_info_display_active_with_raw_or_hdmi_only=True,
        )
        self.assertFalse(bad_info_only.passed)
        self._assert_err(bad_info_only, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

        for flag in (
            "claimed_external_output_wiped_by_camera_reset",
            "dormant_4k_2k_or_24p_60p_requested",
            "fx3_4k_2k_output_present_claimed",
            "fx3_24p_60p_output_present_claimed",
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(**{flag: True})
            self.assertFalse(bad.passed, flag)
            self._assert_err(bad, P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT)

    def test_53_gd_rec_media_dur_hdmi_slot1_tier0_erofs30_firewall(self) -> None:
        for kw in (
            {"recording_media": "SLOT_1", "rec_target_slot": 1},
            {"recording_media": "SLOT_2", "rec_target_slot": 1},
            {"recording_media": "SIMULTANEOUS_RECORDING", "rec_target_slot": 2},
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
                rec_media_dur_hdmi_output="ON",
                slot1_contains_tier0_dump=True,
                **kw,
            )
            self.assertFalse(bad.passed, kw)
            self.assertTrue(bad.slot1_tier0_vault_mutated)
            self._assert_err(bad, P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS)
            self._assert_err_contains(bad, f"errno={P338_ERRNO_EROFS}")

        ok_hdmi_only = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            recording_media="SLOT_1",
            rec_target_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(ok_hdmi_only.passed)
        self.assertFalse(ok_hdmi_only.slot1_tier0_vault_mutated)

    def test_54_gd_fail_closed_redline_violations(self) -> None:
        for flag_kw in (
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"wireless_rf_packets_emitted": 1},
            {"usb_packets_transmitted": 1},
            {"slot1_data_sector_writes": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(**flag_kw)
            self.assertFalse(bad.passed, flag_kw)
            self._assert_err(bad, P338_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_55_gd_physical_dual_media_528b_receipt_files_distinct_st_dev_pass(self) -> None:
        sim = build_simulated_phase338_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            p_a = Path(tmp) / "FX3RCPT1_A.bin"
            p_b = Path(tmp) / "FX3RCPT1_B.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])

            rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
                force_clean_room=True,
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=2001,
                st_dev_b_override=2002,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
                h3_baselines=sim["h3_baselines"],
            )
            self.assertEqual(
                rep.go_no_go,
                P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
            )
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_528B")
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase338_report(rep).valid)

    def test_56_gd_same_st_dev_dual_media_rejected(self) -> None:
        sim = build_simulated_phase338_tier0_receipts()
        bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=42,
            st_dev_b_override=42,
        )
        self.assertFalse(bad.passed)
        self.assertFalse(bad.tier0_receipt_verified)
        self._assert_err(bad, P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_57_gd_corrupted_or_truncated_receipt_rejected(self) -> None:
        sim = build_simulated_phase338_tier0_receipts()
        raw_bad = bytearray(sim["receipt_a_bytes"])
        raw_bad[-1] ^= 0xFF

        bad_crc = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            receipt_a_bytes=bytes(raw_bad),
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(bad_crc.passed)
        self._assert_err(bad_crc, P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        bad_len = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            receipt_a_bytes=b"FX3RCPT1" + b"\x00" * 16,
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(bad_len.passed)
        self._assert_err(bad_len, P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_58_gd_h0_h3_drift_rejected(self) -> None:
        bad = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=1,
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.h0_equals_h3_count, 15)
        self.assertFalse(bad.tier0_receipt_verified)
        self._assert_err(bad, P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    # ------------------------------------------------------------------
    # 59-72: Report Verification & Tamper Detection
    # ------------------------------------------------------------------

    def test_59_verify_phase338_report_rejects_tampered_sha256(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        payload = rep.to_dict()
        payload["reset_action"] = "INITIALIZE"
        res = verify_phase338_report(payload)
        self.assertFalse(res.valid)
        self.assertTrue(any("report_sha256 mismatch" in e for e in res.errors))

    def test_60_verify_phase338_report_rejects_locked_booleans_and_telemetry(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        for bad_field, bad_val in (
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("cross_model_flash_authorized", True),
            ("fx3_focus_bracket_present", True),
            ("fx3_shutter_type_auto_present", True),
            ("fx3_soft_skin_effect_present", True),
            ("fx3_builtin_evf_present", True),
            ("fx3_finder_monitor_menu_present", True),
            ("fx3_recall_custom_hold_standalone_wb_present", True),
            ("fx3_4k_2k_output_present", True),
            ("fx3_24p_60p_output_present", True),
            ("emmc_write_count", 1),
            ("raw_firmware_bytes_leaked", 4),
            ("wireless_rf_packets_emitted", 1),
        ):
            payload = copy.deepcopy(rep.to_dict())
            payload[bad_field] = bad_val
            payload["report_sha256"] = _canonical_sha256_dict(payload)
            res = verify_phase338_report(payload)
            self.assertFalse(res.valid, f"{bad_field}={bad_val}")

    def test_61_failure_report_status_on_any_check_group_error(self) -> None:
        rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            dormant_focus_bracket_requested=True,
        )
        self.assertEqual(
            rep.overall_status,
            P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE,
        )
        self.assertEqual(
            rep.go_no_go,
            P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE,
        )
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertTrue(verify_phase338_report(rep).valid)

    # ------------------------------------------------------------------
    # 62-100: CLI In-Process & Subprocess End-to-End Matrix
    # ------------------------------------------------------------------

    def test_62_cli_help_succeeds_without_argparse_percent_crash(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("--simulate-bench-dry-run", proc.stdout)

    def test_63_cli_default_returns_rc2_awaiting_receipt(self) -> None:
        proc = _run_cli_subprocess(["--force-clean-room", "--json"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["overall_status"], P338_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertNotIn("elapsed_seconds", proc.stdout)

    def test_64_cli_simulate_bench_dry_run_returns_rc0(self) -> None:
        proc = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(payload["h0_equals_h3_count"], 16)
        self.assertTrue(verify_phase338_report(payload).valid)

    def test_65_cli_summary_flag_outputs_one_liner(self) -> None:
        proc = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--summary"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", proc.stdout)
        self.assertIn("check_groups=4/4", proc.stdout)
        self.assertIn("h0_eq_h3=16/16", proc.stdout)

    def test_66_cli_output_and_markdown_out_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "p338.json"
            out_md = Path(tmp) / "p338.md"
            proc = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--output",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase338_report(data).valid)
            self.assertIn("Phase 338", out_md.read_text(encoding="utf-8"))

    def test_67_cli_inprocess_dormant_focus_bracket_returns_rc2(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(
                [
                    "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--dormant-focus-bracket-requested",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["check_groups_passed"], 3)

    def test_68_cli_inprocess_dormant_shutter_auto_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-shutter-type-auto-requested",
            ]
        )
        self.assertEqual(rc, 2)

    def test_69_cli_inprocess_1_320_xsync_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--flash-sync-denominator",
                "320",
            ]
        )
        self.assertEqual(rc, 2)

    def test_70_cli_inprocess_efcs_camera_reset_survives_rc0(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--reset-action",
                "CAMERA_SETTINGS_RESET",
                "--e-front-curtain-shutter",
                "OFF",
            ]
        )
        self.assertEqual(rc, 0)

    def test_71_cli_inprocess_creative_look_fade_negative_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--creative-look-fade",
                "-1",
            ]
        )
        self.assertEqual(rc, 2)

    def test_72_cli_inprocess_dormant_soft_skin_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-soft-skin-requested",
            ]
        )
        self.assertEqual(rc, 2)

    def test_73_cli_inprocess_recover_image_db_slot1_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--recover-image-db-requested",
                "--recover-image-db-slot",
                "1",
            ]
        )
        self.assertEqual(rc, 2)

    def test_74_cli_inprocess_recover_image_db_slot2_returns_rc0(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--recover-image-db-requested",
                "--recover-image-db-slot",
                "2",
            ]
        )
        self.assertEqual(rc, 0)

    def test_75_cli_inprocess_manual_pixel_mapping_no_lens_cap_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--manual-pixel-mapping-requested",
                "--no-lens-cap-attached",
            ]
        )
        self.assertEqual(rc, 2)

    def test_76_cli_inprocess_silent_auto_pm_zero_sound_claim_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--silent-mode",
                "ON",
                "--long-exposure-nr",
                "OFF",
                "--silent-auto-pixel-mapping",
                "ON",
                "--expect-zero-shutter-sound-with-silent-auto-pm-on",
            ]
        )
        self.assertEqual(rc, 2)

    def test_77_cli_inprocess_display_quality_thermal_clamp_rc0_vs_claim_rc2(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc_ok = fx6_cli_main(
                [
                    "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--display-quality",
                    "HIGH",
                    "--body-temp-elevated",
                    "--json",
                ]
            )
        self.assertEqual(rc_ok, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["check_group_c"]["display_quality"], "STANDARD")
        self.assertTrue(payload["check_group_c"]["display_quality_thermally_clamped"])

        rc_bad = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--display-quality",
                "HIGH",
                "--body-temp-elevated",
                "--expect-high-display-quality-unclamped-under-thermal",
            ]
        )
        self.assertEqual(rc_bad, 2)

    def test_78_cli_inprocess_finder_monitor_claim_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--fx3-finder-monitor-menu-present-claimed",
            ]
        )
        self.assertEqual(rc, 2)

    def test_79_cli_inprocess_recall_custom_hold_in_movie_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--shoot-mode",
                "MOVIE",
                "--recall-custom-hold-active",
                "--recall-custom-hold-slot",
                "2",
            ]
        )
        self.assertEqual(rc, 2)

    def test_80_cli_inprocess_recall_custom_hold_standalone_wb_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--recall-custom-hold-standalone-wb-requested",
            ]
        )
        self.assertEqual(rc, 2)

    def test_81_cli_inprocess_hdmi_rec_ctrl_without_tc_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--hdmi-tc-output",
                "OFF",
                "--hdmi-rec-control",
                "ON",
            ]
        )
        self.assertEqual(rc, 2)

    def test_82_cli_inprocess_hdmi_rec_media_slot1_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--rec-media-dur-hdmi-output",
                "ON",
                "--rec-target-slot",
                "1",
            ]
        )
        self.assertEqual(rc, 2)

    def test_83_cli_inprocess_dormant_4k2k_24p60p_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-4k-2k-or-24p-60p-requested",
            ]
        )
        self.assertEqual(rc, 2)

    def test_84_cli_inprocess_live_attach_claim_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--claim-hardware-live-attach-authorized",
            ]
        )
        self.assertEqual(rc, 2)

    def test_85_cli_inprocess_custom_monitor_items_override_rejected(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--exposed-monitor-items",
                "MONITOR_BRIGHTNESS,DISPLAY_QUALITY",
            ]
        )
        self.assertEqual(rc, 2)

    def test_86_cli_inprocess_custom_recall_11_slots_override_rejected(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--recall-custom-hold-eleven-slots",
                "shooting_mode,aperture,white_balance",
            ]
        )
        self.assertEqual(rc, 2)

    def test_87_cli_subprocess_clean_room_test_env_rc0(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_CLEAN_ROOM_TEST": "1"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(verify_phase338_report(payload).valid)

    def test_88_cli_subprocess_force_clean_room_env_rc0(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(verify_phase338_report(payload).valid)

    def test_89_cli_inprocess_creative_look_movie_sharpness_range_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--creative-look-shoot-mode",
                "MOVIE",
                "--creative-look-sharpness-range-adjusted",
            ]
        )
        self.assertEqual(rc, 2)

    def test_90_cli_inprocess_creative_look_bw_saturation_returns_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--creative-look-slot",
                "BW",
                "--creative-look-saturation",
                "3",
            ]
        )
        self.assertEqual(rc, 2)

    def test_91_cli_inprocess_still_cont_hi_plus_f16_af_lock_rc0(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(
                [
                    "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--drive-mode",
                    "CONT_SHOOTING",
                    "--cont-speed-tier",
                    "HI_PLUS",
                    "--aperture-f-number",
                    "16.0",
                    "--long-exposure-nr",
                    "OFF",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["check_group_a"]["af_first_frame_locked_above_f11"])
        self.assertEqual(payload["check_group_a"]["cont_max_fps"], 10)

    def test_92_cli_inprocess_2400p_valid_with_reboot_ack_rc0(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--hdmi-4k-output-rate",
                "24_00P",
            ]
        )
        self.assertEqual(rc, 0)

    def test_93_cli_inprocess_2400p_no_reboot_claim_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--hdmi-4k-output-rate",
                "24_00P",
                "--expect-2400p-no-reboot-or-mixed-playback",
            ]
        )
        self.assertEqual(rc, 2)

    def test_94_cli_inprocess_hdmi_tc_and_rec_ctrl_on_rc0(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--hdmi-tc-output",
                "ON",
                "--hdmi-rec-control",
                "ON",
            ]
        )
        self.assertEqual(rc, 0)

    def test_95_cli_inprocess_delete_slot1_tier0_vault_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--delete-write-requested",
                "--delete-write-slot",
                "1",
            ]
        )
        self.assertEqual(rc, 2)

    def test_96_cli_inprocess_protect_slot1_tier0_vault_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--protect-write-requested",
                "--protect-write-slot",
                "1",
            ]
        )
        self.assertEqual(rc, 2)

    def test_97_cli_inprocess_model_id_mismatch_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--model-id",
                "0x91030099",
            ]
        )
        self.assertEqual(rc, 2)

    def test_98_cli_inprocess_h0_h3_drifted_surface_rc2(self) -> None:
        rc = fx6_cli_main(
            [
                "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--simulated-h0-h3-drifted-surfaces",
                "2",
            ]
        )
        self.assertEqual(rc, 2)

    def test_99_deterministic_sha256_differs_when_non_timing_field_changes(self) -> None:
        r1 = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            creative_look_slot="ST",
        )
        r2 = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            creative_look_slot="FL",
        )
        self.assertNotEqual(r1.report_sha256, r2.report_sha256)

    def test_100_default_h0_baselines_has_16_surfaces(self) -> None:
        sim = build_simulated_phase338_tier0_receipts()
        h0 = build_default_h0_baselines(body_serial=sim["body_serial"], emmc_cid=sim["emmc_cid"])
        self.assertEqual(len(SIXTEEN_STORAGE_SURFACES), 16)
        self.assertEqual(P338_STORAGE_SURFACE_COUNT, 16)
        self.assertEqual(len(h0), len(REQUIRED_H0_BASELINE_KEYS))
        self.assertEqual(len(sim["h3_baselines"]), len(REQUIRED_H0_BASELINE_KEYS))
        self.assertEqual(sim["h0_baselines_a"], sim["h3_baselines"])


if __name__ == "__main__":
    unittest.main()
