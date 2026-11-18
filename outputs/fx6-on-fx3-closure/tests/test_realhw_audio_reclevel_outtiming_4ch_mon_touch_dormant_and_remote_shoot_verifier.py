"""Four-mode unit tests (105 cases) for Phase 345 Milestone (`preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot`):
20th Physical Bench Readiness Verifier (`20/20` Physical Bench Preflights Milestone!) across Global Sony Wave 72 check groups (`A..D`):
- Group A: `Shooting -> [Audio Recording] -> [Audio Rec Level]` (`0..31` 32 steps, default `26` `adj_audio_rec_level_defult`, `Delete` key reset, `Can be reset`), active ONLY for internal stereo mic & body `3.5mm MIC` (`3.5mm MIC` preemption over MI shoe), permanently active body limiter (zero menu Off switch), `XLR-H1 HANDLE AUDIO=ON` hardware override (`LINE +4 dBu`, `MIC/MIC+48V ATT 0/10/20 dB = -60/-50/-40 dBu`, `AUTO/MAN/LINK`, `0..10` dials), `S&Q` `0ch` 4-item lockout, vs `ILME-FX6 Ver. 6.01` `CH1..CH4 Input Select`, 3-tier Reference (`Reference Level` exact 5 options), and **6-mode `Limiter Mode`** (`OFF/-6dB/-9dB/-12dB/-15dB/-17dB`).
- Group B: `[Audio Out Timing]` (`Live` def / `Lip Sync`, Resettable, disabled in `S&Q`), Reset-immune `Setup -> [Sound Option] -> [Volume Settings]` (`0..15` def `7`, acoustic feedback hazard near `XLR-H1`) & `[4ch Audio Monitoring]` exact **5** options (`CH1/CH2`, `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2` — debunking `"CH1/CH2 mono mix"` / `CH1+2/CH3+4` / `All` myths!), vs `FX6` `Monitor CH` 7 options incl. `MIX ALL`, `Headphone Out`, `Volume 0..50` (debunking `"MONITOR VOL +/-"` side buttons: `0` hits in `5-024-458-18`), and `SDI OUT` 4ch vs `HDMI` 2ch pair.
- Group C: Exact **4**-item Reset-immune `Setup -> [Touch Operation]` (`[Touch Operation]`, `[Touch Sensitivity]`, `[Touch Func. in Shooting]` shared across Still/Movie/`S&Q`, `[Swipe Up]`) vs 100% dormant EVF/Alpha (`[Touch Panel/Pad]`, `[Touch Pad (vertical)]`, `[Touch Shutter]`, `[Touch AE]` -> `EOPNOTSUPP=95`), static `[Spot Metering Point]`, vs `FX6` `Touch Function in MF` + Ver. 6.00+ `BIG6` & full-menu touch.
- Group D + Tier-0: Ver. 2.00..7.02 `[Remote Shoot Setting]` (`[Still Img. Save Dest.]` `Destination Only` RAM-to-PTP vs factory-default `Dest.+Camera` & `Camera Only` `Slot 1` `EROFS=30` firewall, `EBUSY=16` live change mutex, Zero-RF `Airplane Mode=On`), vs `FX6` zero `Still Img. Save Dest.` UI, + `16/16 H0 == H3` dual-media `528 B FX3RCPT1` receipt gate.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and donorless CI (`work_root=None`) modes with
zero `.pyc` emission and zero persistent writes.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
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
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    REQUIRED_H0_BASELINE_KEYS,
    build_default_h0_baselines,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    SIXTEEN_STORAGE_SURFACES,
)
from fx6_closure.realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier import (  # noqa: E402
    P345_4CH_MON_BKID,
    P345_4CH_MON_UXC_RESID16,
    P345_AUDIO_OUT_TIMING_BKID,
    P345_AUDIO_OUT_TIMING_DEFAULT,
    P345_AUDIO_OUT_TIMING_MENU_PATH,
    P345_AUDIO_REC_LEVEL_DEFAULT,
    P345_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL,
    P345_AUDIO_REC_LEVEL_MAX,
    P345_AUDIO_REC_LEVEL_MENU_PATH,
    P345_AUDIO_REC_LEVEL_MIN,
    P345_AUDIO_REC_LEVEL_STEP_COUNT,
    P345_BOUNDED_DONOR_PATHS,
    P345_CHECK_GROUP_A_ID,
    P345_CHECK_GROUP_B_ID,
    P345_CHECK_GROUP_C_ID,
    P345_CHECK_GROUP_D_ID,
    P345_DORMANT_TOUCH_SYMBOLS,
    P345_ERRNO_EBUSY,
    P345_ERRNO_EOPNOTSUPP,
    P345_ERRNO_EROFS,
    P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS,
    P345_FX3_BUILTIN_EVF_PRESENT,
    P345_FX3_BUILTIN_LIMITER_ALWAYS_ON,
    P345_FX3_BUILTIN_LIMITER_DISABLEABLE,
    P345_FX3_TOUCH_AE_PRESENT,
    P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS,
    P345_FX3_TOUCH_PANEL_PAD_PRESENT,
    P345_FX3_TOUCH_SHUTTER_PRESENT,
    P345_FX6_HDMI_AUDIO_CHANNELS,
    P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS,
    P345_FX6_MANUAL_MONITOR_VOL_HITS,
    P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS,
    P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS,
    P345_FX6_SDI_AUDIO_CHANNELS,
    P345_FX6_SIDE_MONITOR_VOL_BUTTONS_PRESENT,
    P345_FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED,
    P345_FX6_VOLUME_MAX,
    P345_FX6_VOLUME_MIN,
    P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET,
    P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK,
    P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH,
    P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER,
    P345_GA_ERR_MODEL_OR_FW_FLOOR,
    P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH,
    P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ,
    P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL,
    P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK,
    P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP,
    P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6,
    P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY,
    P345_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY,
    P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE,
    P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30,
    P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P345_GD_ERR_ZERO_RF_AIRPLANE_MODE_VIOLATION,
    P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED,
    P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE,
    P345_HEADER_READ_BYTES,
    P345_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P345_PTPIP_TCP_PORT,
    P345_PTP_MUTEX_SYMBOL,
    P345_PTP_NO_PSEUDO_REC_SYMBOL,
    P345_PTP_USB_DEV_NODES,
    P345_REMOTE_SHOOT_EXACT_FOUR_ITEMS,
    P345_REMOTE_SHOOT_MENU_PATH,
    P345_SCHEMA,
    P345_SONY_HELP_GUIDE_ID,
    P345_SPOT_METERING_FOLLOWS_TRACKING_BOX,
    P345_STILL_IMG_SAVE_DEST_FACTORY_DEFAULT,
    P345_STORAGE_SURFACE_COUNT,
    P345_TOUCH_OPERATION_MENU_PATH,
    P345_VERSION,
    P345_VOLUME_SETTINGS_DEFAULT,
    P345_VOLUME_SETTINGS_MAX,
    P345_VOLUME_SETTINGS_MIN,
    P345_XLR_H1_ATT_TO_DBU,
    P345_XLR_H1_LINE_LEVEL_DBU,
    PHASE345_EMMC_WRITE_COUNT,
    PHASE345_E_ND_ACTUATOR_TX_COUNT,
    PHASE345_PASSIVE_TX_BYTES_EMITTED,
    PHASE345_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE345_SLOT1_DATA_SECTOR_WRITES,
    PHASE345_USB_PACKETS_TRANSMITTED,
    PHASE345_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_345_CHECK_GROUP_IDS,
    PHASE_345_SCHEMA,
    PHASE_345_VERSION,
    _canonical_sha256_dict,
    build_simulated_phase345_tier0_receipts,
    evaluate_p345_check_group_a_audio_reclevel_and_limiter,
    evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon,
    evaluate_p345_check_group_c_touch_dormant_and_spot_link,
    evaluate_p345_check_group_d_remote_shoot_and_tier0,
    evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight,
    inspect_phase345_donors_bounded,
    render_phase345_markdown,
    resolve_phase345_donor_file_or_none,
    run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight,
    verify_phase345_report,
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
            "preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase345Preflight20Verifier(unittest.TestCase):
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
    # 01-15: Exports, Schema, Four-Mode CI & Determinism
    # ------------------------------------------------------------------

    def test_001_package_exports_and_schema_constants(self) -> None:
        self.assertEqual(
            P345_SCHEMA,
            "realhw_preflight20_audio_reclevel_outtiming_4ch_touch_remoteshoot_v1",
        )
        self.assertEqual(PHASE_345_SCHEMA, P345_SCHEMA)
        self.assertEqual(P345_VERSION, "phase345_v1")
        self.assertEqual(PHASE_345_VERSION, "phase345_v1")
        self.assertEqual(P345_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_345_CHECK_GROUP_IDS), 4)
        self.assertTrue(
            hasattr(
                fx6_closure,
                "run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight",
            )
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase345_report"))
        self.assertTrue(hasattr(fx6_closure, "render_phase345_markdown"))

    def test_002_default_run_blocks_awaiting_tier0_receipt_with_4_of_4_groups(self) -> None:
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.overall_status, P345_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.check_group_count, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase345_report(rep).valid)

    def test_003_simulate_bench_dry_run_passes_and_keeps_attach_false(self) -> None:
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertTrue(verify_phase345_report(rep).valid)

    def test_004_physical_dual_media_receipt_passes_with_distinct_stdev(self) -> None:
        sim = build_simulated_phase345_tier0_receipts(
            body_serial="FX3REAL70200345",
            emmc_cid="11010030303847333000a1b2c3d48345",
        )
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
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
            P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase345_report(rep).valid)

    def test_005_resolve_phase345_donor_file_or_none_handles_none_work_root(self) -> None:
        for _lbl, rel in P345_BOUNDED_DONOR_PATHS:
            self.assertIsNone(resolve_phase345_donor_file_or_none(None, rel))

    def test_006_four_mode_determinism_and_recursive_elapsed_seconds_stripping(self) -> None:
        rep_clean = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep_cr_env = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep_force_env = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch(
            "fx6_closure.realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier._resolve_work_root_or_none",
            return_value=None,
        ):
            rep_donorless = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
                force_clean_room=False, simulate_bench_dry_run=True
            )
        self.assertEqual(rep_donorless.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(rep_donorless.donor_inspection.donor_tree_present)
        self.assertEqual(rep_clean.report_sha256, rep_cr_env.report_sha256)
        self.assertEqual(rep_clean.report_sha256, rep_force_env.report_sha256)
        self.assertEqual(rep_clean.report_sha256, rep_donorless.report_sha256)
        js = rep_clean.to_deterministic_json()
        self.assertNotIn("elapsed_seconds", js)
        self.assertNotIn("elapsed_ms", js)

    def test_007_canonical_sha256_strips_nested_timing_fields(self) -> None:
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d1 = copy.deepcopy(rep.to_dict())
        d2 = copy.deepcopy(rep.to_dict())
        d2["donor_inspection"]["elapsed_seconds"] = 999.999
        d2["check_group_a"]["nested_elapsed_ms"] = 12345
        d2["check_group_d"]["sub_elapsed_s"] = 3.14
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_008_local_donor_o_rdonly_bounded_inspection_if_present(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            donor = inspect_phase345_donors_bounded(force_clean_room=False)
            self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
            self.assertLessEqual(donor.elapsed_seconds, 2.0)
            if donor.donor_tree_present:
                self.assertEqual(donor.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertGreater(donor.bytes_read_total, 0)
                self.assertLessEqual(donor.bytes_read_total, 10 * P345_HEADER_READ_BYTES)
            else:
                self.assertEqual(donor.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_009_clean_room_mode_zero_leaked_bytes(self) -> None:
        donor = inspect_phase345_donors_bounded(force_clean_room=True)
        self.assertEqual(donor.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(donor.bytes_read_total, 0)
        self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
        self.assertEqual(donor.donors_checked, len(P345_BOUNDED_DONOR_PATHS))

    def test_010_locked_zero_telemetry_constants(self) -> None:
        self.assertEqual(PHASE345_EMMC_WRITE_COUNT, 0)
        self.assertEqual(PHASE345_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(PHASE345_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE345_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE345_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE345_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE345_RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_011_wrong_body_model_id_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(body_model_id=0x91030099)
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_012_wrong_body_fw_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(body_fw="6.00")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_013_wrong_sony_help_guide_id_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(sony_help_guide_id="ilc/9999")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_014_invalid_reset_action_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(reset_action="FACTORY_WIPE")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)

    def test_015_invalid_shoot_mode_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(shoot_mode="TIMELAPSE")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK)

    # ------------------------------------------------------------------
    # 16-40: Check Group A — Audio Rec Level, Limiter, XLR-H1 & FX6
    # ------------------------------------------------------------------

    def test_016_audio_rec_level_exact_constants(self) -> None:
        self.assertEqual(P345_AUDIO_REC_LEVEL_MIN, 0)
        self.assertEqual(P345_AUDIO_REC_LEVEL_MAX, 31)
        self.assertEqual(P345_AUDIO_REC_LEVEL_STEP_COUNT, 32)
        self.assertEqual(P345_AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertEqual(P345_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL, "adj_audio_rec_level_defult")
        self.assertEqual(
            P345_AUDIO_REC_LEVEL_MENU_PATH,
            "Shooting -> [Audio Recording] -> [Audio Rec Level]",
        )

    def test_017_audio_rec_level_boundaries_0_and_31_pass(self) -> None:
        self.assertTrue(evaluate_p345_check_group_a_audio_reclevel_and_limiter(audio_rec_level=0).passed)
        self.assertTrue(evaluate_p345_check_group_a_audio_reclevel_and_limiter(audio_rec_level=31).passed)

    def test_018_audio_rec_level_out_of_range_fails(self) -> None:
        ga_low = evaluate_p345_check_group_a_audio_reclevel_and_limiter(audio_rec_level=-1)
        ga_high = evaluate_p345_check_group_a_audio_reclevel_and_limiter(audio_rec_level=32)
        self.assertFalse(ga_low.passed)
        self.assertFalse(ga_high.passed)
        self._assert_err(ga_low, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)
        self._assert_err(ga_high, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)

    def test_019_delete_key_not_resetting_to_26_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(delete_key_resets_to_26=False)
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)

    def test_020_claimed_wrong_menu_path_shooting_audio_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            claimed_menu_path_is_shooting_audio=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)

    def test_021_camera_settings_reset_resets_audio_rec_level_to_26(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            audio_rec_level=12, reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.audio_rec_level_resettable)
        self.assertEqual(ga.effective_audio_rec_level_after_reset, 26)

    def test_022_claimed_audio_rec_level_resists_camera_reset_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            claimed_audio_rec_level_resists_camera_reset=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET)

    def test_023_internal_stereo_mic_default_allows_audio_rec_level(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            mic_35mm_inserted=False, xlr_h1_handle_audio="OFF"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.active_audio_source, "INTERNAL_STEREO_MIC")
        self.assertTrue(ga.audio_rec_level_active)
        self.assertEqual(ga.audio_channels, 2)

    def test_024_35mm_mic_preempts_xlr_h1_and_uses_audio_rec_level(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            mic_35mm_inserted=True, xlr_h1_attached=True, xlr_h1_handle_audio="ON"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.active_audio_source, "BODY_3_5MM_MIC")
        self.assertTrue(ga.audio_rec_level_active)
        self.assertTrue(ga.shoe_audio_grayed_out)
        self.assertEqual(ga.audio_channels, 2)

    def test_025_expect_xlr_h1_wins_over_35mm_mic_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            mic_35mm_inserted=True,
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            expect_xlr_h1_active_over_35mm_mic=True,
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK)

    def test_026_xlr_h1_handle_audio_on_grays_out_audio_rec_level_and_gives_4ch(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            mic_35mm_inserted=False, xlr_h1_attached=True, xlr_h1_handle_audio="ON"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.active_audio_source, "XLR_H1_MI_SHOE")
        self.assertFalse(ga.audio_rec_level_active)
        self.assertEqual(ga.audio_channels, 4)

    def test_027_expect_audio_rec_level_controls_xlr_h1_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            expect_audio_rec_level_controls_xlr_h1=True,
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK)

    def test_028_xlr_h1_line_mode_locks_plus4_dbu(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            xlr_h1_handle_audio="ON", xlr_h1_input_mode="LINE"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.xlr_h1_reference_level_dbu, P345_XLR_H1_LINE_LEVEL_DBU)
        self.assertEqual(ga.xlr_h1_reference_level_dbu, 4)

    def test_029_xlr_h1_mic_att_db_mapping_exact(self) -> None:
        self.assertEqual(P345_XLR_H1_ATT_TO_DBU, {0: -60, 10: -50, 20: -40})
        for att, dbu in P345_XLR_H1_ATT_TO_DBU.items():
            ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
                xlr_h1_handle_audio="ON",
                xlr_h1_input_mode="MIC_PLUS_48V",
                xlr_h1_att_db=att,
            )
            self.assertTrue(ga.passed)
            self.assertEqual(ga.xlr_h1_reference_level_dbu, dbu)

    def test_030_xlr_h1_invalid_att_gain_or_dial_fails(self) -> None:
        self.assertFalse(
            evaluate_p345_check_group_a_audio_reclevel_and_limiter(xlr_h1_att_db=15).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_a_audio_reclevel_and_limiter(xlr_h1_gain_mode="BOOST").passed
        )
        self.assertFalse(
            evaluate_p345_check_group_a_audio_reclevel_and_limiter(xlr_h1_audio_level=11).passed
        )

    def test_031_sq_mode_forces_0ch_and_locks_audio(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(shoot_mode="S_AND_Q")
        self.assertTrue(ga.passed)
        self.assertEqual(ga.active_audio_source, "SQ_0CH_LOCKED")
        self.assertEqual(ga.audio_channels, 0)
        self.assertFalse(ga.audio_rec_level_active)
        self.assertTrue(ga.shoe_audio_grayed_out)

    def test_032_expect_audio_active_in_sq_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            shoot_mode="S_AND_Q", expect_audio_active_in_sq=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK)

    def test_033_fx3_builtin_limiter_permanently_active_cannot_disable(self) -> None:
        self.assertTrue(P345_FX3_BUILTIN_LIMITER_ALWAYS_ON)
        self.assertFalse(P345_FX3_BUILTIN_LIMITER_DISABLEABLE)
        ga1 = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            fx3_disable_builtin_limiter_requested=True
        )
        ga2 = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            claimed_fx3_builtin_limiter_has_menu_off=True
        )
        self.assertFalse(ga1.passed)
        self.assertFalse(ga2.passed)
        self._assert_err(ga1, P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH)
        self._assert_err(ga2, P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH)

    def test_034_fx6_ch1_ch4_input_select_valid_combinations(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            fx6_ch1_input="SHOE_CH1",
            fx6_ch2_input="INTERNAL_MIC",
            fx6_ch3_input="INPUT1",
            fx6_ch4_input="SHOE_CH2",
        )
        self.assertTrue(ga.passed)

    def test_035_fx6_invalid_ch3_input_select_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(fx6_ch3_input="INPUT2")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER)

    def test_036_fx6_three_tier_reference_options_pass(self) -> None:
        self.assertEqual(len(P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS), 5)
        for ref in P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS:
            ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
                fx6_input_mic_reference="-80dB",
                fx6_line_input_reference="EBUL",
                fx6_reference_level=ref,
            )
            self.assertTrue(ga.passed)

    def test_037_fx6_claimed_reference_level_only_3_options_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            claimed_fx6_reference_level_only_3_options=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER)

    def test_038_fx6_limiter_mode_exact_6_options_pass(self) -> None:
        self.assertEqual(
            P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS,
            ("OFF", "-6dB", "-9dB", "-12dB", "-15dB", "-17dB"),
        )
        for mode in P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS:
            self.assertTrue(
                evaluate_p345_check_group_a_audio_reclevel_and_limiter(fx6_limiter_mode=mode).passed
            )

    def test_039_fx6_claimed_limiter_mode_only_4_options_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
            claimed_fx6_limiter_mode_only_4_options=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER)

    def test_040_fx6_invalid_limiter_mode_fails(self) -> None:
        ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(fx6_limiter_mode="-20dB")
        self.assertFalse(ga.passed)
        self._assert_err(ga, P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER)

    # ------------------------------------------------------------------
    # 41-62: Check Group B — Audio Out Timing, Volume & 4ch Monitoring
    # ------------------------------------------------------------------

    def test_041_audio_out_timing_constants_and_live_default(self) -> None:
        self.assertEqual(P345_AUDIO_OUT_TIMING_DEFAULT, "LIVE")
        self.assertEqual(P345_AUDIO_OUT_TIMING_BKID, "BKID_APP_setting_audio_output_timing")
        self.assertEqual(
            P345_AUDIO_OUT_TIMING_MENU_PATH,
            "Shooting -> [Audio Recording] -> [Audio Out Timing]",
        )
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon()
        self.assertTrue(gb.passed)
        self.assertEqual(gb.audio_out_timing, "LIVE")
        self.assertTrue(gb.audio_out_timing_resettable)

    def test_042_audio_out_timing_lip_sync_emits_warning_and_resets_under_camera_reset(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            audio_out_timing="LIP_SYNC", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_audio_out_timing_after_reset, "LIVE")
        self.assertTrue(any("Lip Sync" in w for w in gb.warnings))

    def test_043_invalid_audio_out_timing_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(audio_out_timing="DIRECT")
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ)

    def test_044_claimed_audio_out_timing_under_setup_or_reset_immune_fails(self) -> None:
        gb1 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_audio_out_timing_under_setup=True
        )
        gb2 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_audio_out_timing_resists_camera_reset=True
        )
        self.assertFalse(gb1.passed)
        self.assertFalse(gb2.passed)
        self._assert_err(gb1, P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ)
        self._assert_err(gb2, P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ)

    def test_045_audio_out_timing_disabled_in_sq_and_claim_active_fails(self) -> None:
        gb_ok = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(shoot_mode="S_AND_Q")
        self.assertTrue(gb_ok.passed)
        self.assertFalse(gb_ok.audio_out_timing_active)
        gb_bad = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            shoot_mode="S_AND_Q", expect_audio_out_timing_active_in_sq=True
        )
        self.assertFalse(gb_bad.passed)
        self._assert_err(gb_bad, P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ)

    def test_046_volume_settings_0_to_15_default_7(self) -> None:
        self.assertEqual(P345_VOLUME_SETTINGS_MIN, 0)
        self.assertEqual(P345_VOLUME_SETTINGS_MAX, 15)
        self.assertEqual(P345_VOLUME_SETTINGS_DEFAULT, 7)
        self.assertTrue(evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(volume_settings=0).passed)
        self.assertTrue(evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(volume_settings=15).passed)

    def test_047_volume_settings_out_of_range_fails(self) -> None:
        self.assertFalse(
            evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(volume_settings=-1).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(volume_settings=16).passed
        )

    def test_048_volume_settings_resists_camera_reset_and_clears_on_initialize(self) -> None:
        gb_cam = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            volume_settings=12, reset_action="CAMERA_SETTINGS_RESET"
        )
        gb_init = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            volume_settings=12, reset_action="INITIALIZE"
        )
        self.assertTrue(gb_cam.volume_settings_reset_immune)
        self.assertEqual(gb_cam.effective_volume_settings_after_reset, 12)
        self.assertEqual(gb_init.effective_volume_settings_after_reset, 7)

    def test_049_claimed_volume_settings_wiped_by_camera_reset_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_volume_settings_wiped_by_camera_reset=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK)

    def test_050_acoustic_feedback_hazard_high_speaker_near_xlr_h1_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            volume_settings=14,
            speaker_monitor_unmuted_near_mic=True,
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
        )
        self.assertFalse(gb.passed)
        self.assertTrue(gb.acoustic_feedback_hazard_detected)
        self._assert_err(gb, P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK)

    def test_051_4ch_audio_monitoring_exact_five_options_pass(self) -> None:
        self.assertEqual(P345_4CH_MON_UXC_RESID16, "0x70dd")
        self.assertEqual(P345_4CH_MON_BKID, "BKID_APP_setting_audio_monitoring_ch")
        self.assertEqual(
            P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS,
            ("CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"),
        )
        for opt in P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS:
            self.assertTrue(
                evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
                    four_ch_audio_monitoring=opt
                ).passed
            )

    def test_052_4ch_monitoring_wrong_exposed_options_count_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            exposed_4ch_monitoring_options=("CH1/CH2", "CH3/CH4", "CH1+2/CH3+4", "All")
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH)

    def test_053_4ch_monitoring_myth_selection_or_claim_fails(self) -> None:
        gb1 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            four_ch_audio_monitoring="CH1+2/CH3+4"
        )
        gb2 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all=True
        )
        self.assertFalse(gb1.passed)
        self.assertFalse(gb2.passed)
        self._assert_err(gb1, P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH)
        self._assert_err(gb2, P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH)

    def test_054_4ch_monitoring_reset_immune_under_camera_reset(self) -> None:
        gb_cam = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            four_ch_audio_monitoring="CH1+3/CH2+4", reset_action="CAMERA_SETTINGS_RESET"
        )
        gb_init = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            four_ch_audio_monitoring="CH1+3/CH2+4", reset_action="INITIALIZE"
        )
        self.assertTrue(gb_cam.four_ch_monitoring_reset_immune)
        self.assertEqual(gb_cam.effective_4ch_monitoring_after_reset, "CH1+3/CH2+4")
        self.assertEqual(gb_init.effective_4ch_monitoring_after_reset, "CH1/CH2")

    def test_055_claimed_4ch_monitoring_wiped_by_camera_reset_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_4ch_monitoring_wiped_by_camera_reset=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH)

    def test_056_fx6_monitor_ch_exact_seven_options_pass(self) -> None:
        self.assertEqual(
            P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS,
            ("CH1", "CH2", "CH3", "CH4", "CH1/CH2", "CH3/CH4", "MIX_ALL"),
        )
        for ch in P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS:
            self.assertTrue(
                evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_monitor_ch=ch).passed
            )

    def test_057_fx6_invalid_monitor_ch_fails(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_monitor_ch="CH1+3/CH2+4")
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL)

    def test_058_fx6_headphone_out_stereo_mono_and_invalid(self) -> None:
        self.assertTrue(
            evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_headphone_out="MONO").passed
        )
        self.assertFalse(
            evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_headphone_out="DUAL").passed
        )

    def test_059_fx6_volume_0_to_50_boundaries_and_overflow(self) -> None:
        self.assertEqual(P345_FX6_VOLUME_MIN, 0)
        self.assertEqual(P345_FX6_VOLUME_MAX, 50)
        self.assertTrue(evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_volume=0).passed)
        self.assertTrue(evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_volume=50).passed)
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(fx6_volume=51)
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL)

    def test_060_fx6_claimed_side_monitor_vol_buttons_fails_zero_manual_hits(self) -> None:
        self.assertFalse(P345_FX6_SIDE_MONITOR_VOL_BUTTONS_PRESENT)
        self.assertEqual(P345_FX6_MANUAL_MONITOR_VOL_HITS, 0)
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_fx6_has_side_monitor_vol_buttons=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL)

    def test_061_fx6_hdmi_2ch_vs_sdi_4ch_contrasts(self) -> None:
        self.assertEqual(P345_FX6_HDMI_AUDIO_CHANNELS, 2)
        self.assertEqual(P345_FX6_SDI_AUDIO_CHANNELS, 4)
        gb1 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_fx6_hdmi_carries_4ch_audio=True
        )
        gb2 = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
            claimed_fx6_sdi_limited_to_2ch_audio=True
        )
        self.assertFalse(gb1.passed)
        self.assertFalse(gb2.passed)
        self._assert_err(gb1, P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL)
        self._assert_err(gb2, P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL)

    def test_062_group_b_default_exposes_exact_five_options(self) -> None:
        gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon()
        self.assertEqual(len(gb.exposed_4ch_monitoring_options), 5)
        self.assertEqual(gb.fx6_sdi_audio_channels, 4)
        self.assertEqual(gb.fx6_hdmi_audio_channels, 2)

    # ------------------------------------------------------------------
    # 63-82: Check Group C — Touch Operation 4 Items vs Dormant EVF/Alpha
    # ------------------------------------------------------------------

    def test_063_touch_operation_exact_four_items_and_path(self) -> None:
        self.assertEqual(P345_TOUCH_OPERATION_MENU_PATH, "Setup -> [Touch Operation]")
        self.assertEqual(
            P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS,
            ("TOUCH_OPERATION", "TOUCH_SENSITIVITY", "TOUCH_FUNC_IN_SHOOTING", "SWIPE_UP"),
        )
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link()
        self.assertTrue(gc.passed)
        self.assertEqual(len(gc.exposed_touch_operation_items), 4)

    def test_064_extra_or_missing_touch_operation_item_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            exposed_touch_operation_items=("TOUCH_OPERATION", "TOUCH_SENSITIVITY", "TOUCH_SHUTTER")
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY)

    def test_065_touch_operation_modes_and_invalid_rejected(self) -> None:
        for mode in ("ON", "ON_PLAYBACK_ONLY", "OFF"):
            self.assertTrue(
                evaluate_p345_check_group_c_touch_dormant_and_spot_link(touch_operation=mode).passed
            )
        self.assertFalse(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                touch_operation="EVF_ONLY"
            ).passed
        )

    def test_066_touch_sensitivity_and_swipe_up_valid_and_invalid(self) -> None:
        self.assertTrue(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                touch_sensitivity="SENSITIVE", swipe_up="OFF"
            ).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                touch_sensitivity="ULTRA"
            ).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(swipe_up="CUSTOM").passed
        )

    def test_067_touch_func_in_shooting_shared_across_still_movie_sq(self) -> None:
        for shoot in ("PHOTO", "MOVIE", "S_AND_Q"):
            for func in ("TOUCH_FOCUS", "TOUCH_TRACKING", "OFF"):
                self.assertTrue(
                    evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                        shoot_mode=shoot, touch_func_in_shooting=func
                    ).passed
                )

    def test_068_mf_mode_switches_touch_tracking_to_touch_focus_on_tap(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            focus_mode="MF", touch_func_in_shooting="TOUCH_TRACKING"
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.effective_touch_func_in_shooting, "TOUCH_FOCUS")

    def test_069_claimed_touch_func_differs_in_movie_or_sq_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            claimed_touch_func_differs_in_movie_or_sq=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY)

    def test_070_touch_operation_is_reset_immune_and_claimed_wiped_fails(self) -> None:
        gc_cam = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            touch_func_in_shooting="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gc_cam.passed)
        self.assertTrue(gc_cam.touch_operation_reset_immune)
        self.assertEqual(gc_cam.effective_touch_func_in_shooting, "OFF")
        gc_bad = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            claimed_touch_operation_wiped_by_camera_reset=True
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY)

    def test_071_dormant_touch_panel_pad_rejected_eopnotsupp_95(self) -> None:
        self.assertFalse(P345_FX3_TOUCH_PANEL_PAD_PRESENT)
        self.assertEqual(P345_DORMANT_TOUCH_SYMBOLS["TOUCH_PANEL_PAD"][2], 0)
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            dormant_touch_panel_pad_requested=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP)
        self._assert_err_contains(gc, f"errno={P345_ERRNO_EOPNOTSUPP}")

    def test_072_dormant_touch_pad_vertical_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(P345_DORMANT_TOUCH_SYMBOLS["TOUCH_PAD_VERTICAL"][2], 0)
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            dormant_touch_pad_vertical_requested=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP)

    def test_073_dormant_touch_shutter_rejected_eopnotsupp_95(self) -> None:
        self.assertFalse(P345_FX3_TOUCH_SHUTTER_PRESENT)
        self.assertEqual(P345_DORMANT_TOUCH_SYMBOLS["TOUCH_SHUTTER"][2], 0)
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            dormant_touch_shutter_requested=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP)

    def test_074_dormant_touch_ae_rejected_eopnotsupp_95(self) -> None:
        self.assertFalse(P345_FX3_TOUCH_AE_PRESENT)
        self.assertEqual(P345_DORMANT_TOUCH_SYMBOLS["TOUCH_AE"][2], 0)
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            dormant_touch_ae_requested=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP)

    def test_075_claimed_fx3_dormant_touch_or_builtin_evf_fails(self) -> None:
        self.assertFalse(P345_FX3_BUILTIN_EVF_PRESENT)
        for kw in (
            {"claimed_fx3_touch_panel_pad_present": True},
            {"claimed_fx3_touch_shutter_present": True},
            {"claimed_fx3_touch_ae_present": True},
            {"claimed_fx3_has_builtin_evf": True},
        ):
            gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP)

    def test_076_spot_metering_point_modes_valid(self) -> None:
        self.assertFalse(P345_SPOT_METERING_FOLLOWS_TRACKING_BOX)
        self.assertTrue(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                spot_metering_point="FOCUS_POINT_LINK"
            ).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                spot_metering_point="TRACKING_BOX"
            ).passed
        )

    def test_077_expect_spot_metering_follows_tracking_box_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            spot_metering_point="FOCUS_POINT_LINK",
            expect_spot_metering_follows_tracking_box=True,
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6)

    def test_078_fx6_touch_function_in_mf_spot_focus_and_tracking_af(self) -> None:
        self.assertTrue(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                fx6_touch_function_in_mf="TRACKING_AF"
            ).passed
        )
        self.assertFalse(
            evaluate_p345_check_group_c_touch_dormant_and_spot_link(
                fx6_touch_function_in_mf="TOUCH_SHUTTER"
            ).passed
        )

    def test_079_fx6_spot_focus_in_mf_lockouts_report_disabled(self) -> None:
        for kw in (
            {"fx6_manual_lens": True},
            {"fx6_desqueeze_not_off": True},
            {"fx6_focus_magnifier_active": True},
        ):
            gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(**kw)
            self.assertTrue(gc.passed)
            self.assertTrue(gc.fx6_spot_focus_in_mf_disabled)

    def test_080_expect_fx6_spot_focus_in_mf_during_lockout_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            fx6_desqueeze_not_off=True,
            expect_fx6_spot_focus_in_mf_during_lockout=True,
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6)

    def test_081_claimed_fx6_lacks_big6_or_mf_touch_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
            claimed_fx6_lacks_big6_or_mf_touch=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6)

    def test_082_group_c_invalid_fx6_touch_operation_fails(self) -> None:
        gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(fx6_touch_operation="AUTO")
        self.assertFalse(gc.passed)
        self._assert_err(gc, P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6)

    # ------------------------------------------------------------------
    # 83-105: Check Group D, Tier-0 FX3RCPT1, Verifier & CLI Subprocess
    # ------------------------------------------------------------------

    def test_083_remote_shoot_constants_and_factory_default_dest_plus_camera(self) -> None:
        self.assertEqual(
            P345_REMOTE_SHOOT_MENU_PATH,
            "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]",
        )
        self.assertEqual(len(P345_REMOTE_SHOOT_EXACT_FOUR_ITEMS), 4)
        self.assertEqual(P345_STILL_IMG_SAVE_DEST_FACTORY_DEFAULT, "DEST_PLUS_CAMERA")
        self.assertEqual(P345_PTPIP_TCP_PORT, 15740)
        self.assertEqual(len(P345_PTP_USB_DEV_NODES), 3)
        self.assertIn("stillrec_running_without_pseudo_rec_t", P345_PTP_NO_PSEUDO_REC_SYMBOL)
        self.assertFalse(P345_FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED)

    def test_084_destination_only_streams_from_ram_without_card(self) -> None:
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            still_img_save_dest="DESTINATION_ONLY",
            card_inserted=False,
            release_wo_card="ENABLE",
            remote_shoot_capture_requested=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(gd.passed)
        self.assertTrue(gd.zero_card_ram_streaming_active)
        self.assertFalse(gd.slot1_tier0_vault_mutated)
        self.assertEqual(gd.slot1_data_sector_writes, 0)

    def test_085_camera_reset_preserves_destination_only_while_network_reset_restores_default(self) -> None:
        gd_cam = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            still_img_save_dest="DESTINATION_ONLY",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        gd_net = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            still_img_save_dest="DESTINATION_ONLY",
            reset_action="RESET_NETWORK_SET",
        )
        self.assertTrue(gd_cam.passed)
        self.assertEqual(gd_cam.effective_still_img_save_dest_after_reset, "DESTINATION_ONLY")
        self.assertTrue(gd_net.passed)
        self.assertEqual(gd_net.effective_still_img_save_dest_after_reset, "DEST_PLUS_CAMERA")

    def test_086_claimed_factory_default_is_destination_only_or_wiped_by_cam_reset_fails(self) -> None:
        for kw in (
            {"claimed_still_img_save_dest_default_is_destination_only": True},
            {"claimed_remote_shoot_wiped_by_camera_reset": True},
            {"claimed_remote_shoot_retains_ver1_pc_remote_menu": True},
        ):
            gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE)

    def test_087_dest_plus_camera_capture_on_slot1_blocked_erofs_30(self) -> None:
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            still_img_save_dest="DEST_PLUS_CAMERA",
            card_inserted=True,
            recording_media_slot=1,
            remote_shoot_capture_requested=True,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30)
        self._assert_err_contains(gd, f"errno={P345_ERRNO_EROFS}")

    def test_088_camera_only_without_card_or_slot1_write_blocked(self) -> None:
        gd1 = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            still_img_save_dest="CAMERA_ONLY",
            card_inserted=False,
            remote_shoot_capture_requested=True,
        )
        gd2 = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            slot1_write_requested=True,
        )
        self.assertFalse(gd1.passed)
        self.assertFalse(gd2.passed)
        self._assert_err(gd1, P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30)
        self._assert_err(gd2, P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30)

    def test_089_expect_dest_plus_camera_zero_card_write_or_camera_only_no_card_fails(self) -> None:
        gd1 = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True, expect_dest_plus_camera_zero_card_write=True
        )
        gd2 = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True, expect_camera_only_shoots_without_card=True
        )
        self.assertFalse(gd1.passed)
        self.assertFalse(gd2.passed)
        self._assert_err(gd1, P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30)
        self._assert_err(gd2, P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30)

    def test_090_ptp_mutex_ebusy_16_live_save_dest_change_blocked(self) -> None:
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            pc_remote_connected=True,
            change_save_dest_while_connected_requested=True,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY)
        self._assert_err_contains(gd, f"errno={P345_ERRNO_EBUSY}")
        self._assert_err_contains(gd, P345_PTP_MUTEX_SYMBOL)

    def test_091_ptp_usb_requires_remote_shooting_and_ptp_ip_usblan_allowed(self) -> None:
        gd_bad = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            remote_transport="PTP_USB",
            usb_connection_mode="MASS_STORAGE",
        )
        gd_ok = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True,
            remote_transport="PTP_IP_USBLAN",
            usb_connection_mode="SEL_WHEN_CONNECT",
        )
        self.assertFalse(gd_bad.passed)
        self._assert_err(gd_bad, P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY)
        self.assertTrue(gd_ok.passed)

    def test_092_zero_rf_airplane_mode_and_wireless_rf_blocked(self) -> None:
        for kw in (
            {"airplane_mode": "OFF"},
            {"remote_transport": "WIRELESS_RF"},
            {"wireless_rf_packets_emitted": 1},
        ):
            gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P345_GD_ERR_ZERO_RF_AIRPLANE_MODE_VIOLATION)

    def test_093_claimed_fx6_exposes_still_img_save_dest_ui_fails(self) -> None:
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            simulate_bench_dry_run=True, claimed_fx6_exposes_still_img_save_dest_ui=True
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY)

    def test_094_fail_closed_hardware_write_and_auth_redlines(self) -> None:
        for kw in (
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P345_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_095_tier0_single_receipt_missing_copy_b_fails(self) -> None:
        sim = build_simulated_phase345_tier0_receipts()
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            st_dev_a_override=1001,
        )
        self.assertFalse(gd.passed)
        self.assertFalse(gd.tier0_receipt_verified)
        self._assert_err(gd, P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_096_tier0_same_st_dev_fails(self) -> None:
        sim = build_simulated_phase345_tier0_receipts()
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=777,
            st_dev_b_override=777,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_097_tier0_tampered_receipt_integrity_fails(self) -> None:
        sim = build_simulated_phase345_tier0_receipts()
        tampered = bytearray(sim["receipt_a_bytes"])
        tampered[20] ^= 0xFF
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=bytes(tampered),
            receipt_b_bytes=bytes(tampered),
            st_dev_a_override=2001,
            st_dev_b_override=2002,
        )
        self.assertFalse(gd.passed)
        self.assertFalse(gd.tier0_receipt_verified)
        self._assert_err(gd, P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_098_tier0_trivial_serial_or_cid_fails(self) -> None:
        sim = build_simulated_phase345_tier0_receipts()
        gd_ser = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2001,
            st_dev_b_override=2002,
            body_serial="00000000",
        )
        gd_cid = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2001,
            st_dev_b_override=2002,
            emmc_cid="0" * 32,
        )
        self.assertFalse(gd_ser.passed)
        self.assertFalse(gd_cid.passed)
        self._assert_err(gd_ser, P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        self._assert_err(gd_cid, P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_099_tier0_h0_h3_drift_detection_fails(self) -> None:
        sim = build_simulated_phase345_tier0_receipts()
        h3_drifted = dict(sim["h3_baselines"])
        first_key = REQUIRED_H0_BASELINE_KEYS[0]
        h3_drifted[first_key] = "f" * 64
        gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2001,
            st_dev_b_override=2002,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=h3_drifted,
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_equals_h3_count, 15)
        self._assert_err(gd, P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_100_verify_phase345_report_catches_tamper_and_locked_flags(self) -> None:
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertTrue(verify_phase345_report(rep).valid)

        d_sha = copy.deepcopy(rep.to_dict())
        d_sha["check_group_a"]["audio_rec_level"] = 10
        res_sha = verify_phase345_report(d_sha)
        self.assertFalse(res_sha.valid)
        self.assertTrue(any("report_sha256 mismatch" in e for e in res_sha.errors))

        d_flag = copy.deepcopy(rep.to_dict())
        d_flag["overall_ready_for_hardware_attach"] = True
        d_flag["report_sha256"] = _canonical_sha256_dict(d_flag)
        res_flag = verify_phase345_report(d_flag)
        self.assertFalse(res_flag.valid)
        self.assertTrue(
            any("overall_ready_for_hardware_attach" in e for e in res_flag.errors)
        )

    def test_101_render_phase345_markdown_contains_required_anchors(self) -> None:
        rep = run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase345_markdown(rep)
        self.assertIn("Phase 345", md)
        self.assertIn(P345_SCHEMA, md)
        self.assertIn("4/4", md)
        self.assertIn("16/16", md)
        self.assertIn(rep.report_sha256, md)

    def test_102_cli_help_returns_zero(self) -> None:
        cp = _run_cli_subprocess(["--help"])
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("--audio-rec-level", cp.stdout)
        self.assertIn("--still-img-save-dest", cp.stdout)

    def test_103_cli_default_blocks_rc2_awaiting_receipts(self) -> None:
        cp = _run_cli_subprocess(["--force-clean-room", "--summary"])
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        self.assertIn("OVERALL=READY_OFFLINE_AWAITING_BENCH_RECEIPTS", cp.stdout)
        self.assertIn("ready_attach=False", cp.stdout)

    def test_104_cli_simulate_bench_dry_run_and_force_clean_room_rc0(self) -> None:
        cp_dry = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(cp_dry.returncode, 0, msg=cp_dry.stderr)
        payload = json.loads(cp_dry.stdout)
        self.assertEqual(payload["schema_version"], P345_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(payload["check_groups_passed"], 4)
        self.assertEqual(payload["h0_equals_h3_count"], 16)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase345_report(payload).valid)

        cp_cr = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--summary"])
        self.assertEqual(cp_cr.returncode, 0, msg=cp_cr.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp_cr.stdout)

    def test_105_cli_output_and_markdown_out_artifacts_and_failure_rc2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_out = tmp_path / "p345.json"
            md_out = tmp_path / "p345.md"
            cp_ok = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--output",
                    str(json_out),
                    "--markdown-out",
                    str(md_out),
                    "--summary",
                ]
            )
            self.assertEqual(cp_ok.returncode, 0, msg=cp_ok.stderr)
            self.assertTrue(json_out.is_file())
            self.assertTrue(md_out.is_file())
            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase345_report(loaded).valid)
            self.assertIn("Phase 345", md_out.read_text(encoding="utf-8"))

        cp_fail = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-touch-shutter-requested",
                "--summary",
            ]
        )
        self.assertEqual(cp_fail.returncode, 2)
        self.assertIn(
            f"go_no_go={P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE}",
            cp_fail.stdout,
        )


if __name__ == "__main__":
    unittest.main()
