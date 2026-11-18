"""Four-mode unit tests (108 cases) for Phase 354 Milestone (`preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset`):
21st Physical Bench Readiness Verifier (`21/21` Physical Bench Preflights Milestone!) across Global Sony Waves 73-74 check groups (`A..D`):
- Group A (Wave 73): `Setup -> [Dial Customize] -> [Lock Operation Parts]` (`Off`/`Multi-Selector Only`/`Dial + Wheel`/`All`, activated by `Fn` long-press, forced `Off` when `[AF Area Registration]=On`, temporarily bypassed during `My Dial 1..3`, Reset-immune) + `MENU + Fn` 5 s global lock reserving `SHUTTER` and leaving Touch under `[Touch Operation]`, dormant `UIBIZ_SLIKEY_LOCK` (`EOPNOTSUPP=95`), vs `ILME-FX6` dual physical `HOLD` switches + `User Menu with Lock` (`0000..9999`); Resettable `[Shockless WB]` (`Off/1(Fast)/2/3(Slow)`, Movie/`S&Q`-only), Resettable `[Priority Set in AWB]`, Still-only Reset-immune `[Shutter AWB Lock]` (`Shutter Half Press`/`Cont. Shooting`/`Off`, Movie Custom Key `AWB Lock Hold/Toggle`), vs `FX6` `ATW Speed 1..5` & `diadem_pro_settings_converter`.
- Group B (Wave 73): `Focus -> [Focus Assistant]` exact 4 Reset-immune items (Still-only `[Auto Magnifier in MF]`, `[Focus Magnif. Time]`, `[Initial Focus Mag.]` [Still FF `x1.0`/`x2.1`, `x4.1` 2nd press only; Still APS-C `x1.0`/`x1.5`; Movie `x1.0`/`x4.0`], Still-only `[AF in Focus Mag.]`) + dormant `[Focus Ring Rotate]` (`0` hits in `FX3 appFw.so` -> `EOPNOTSUPP=95`) vs `FX6` `AF Assist`, `PUSH AUTO`, VF/LCD `x3/x6` & Ver. 6.0 `HDMI Focus Mag x2/x4`; `[Delete]` 5 batch modes, `[Protect]` 7 modes with zero `"Cancel All Images"` & Proxy co-protection, read-only `[Display Media Info.]` `40,000` max, `[Recover Image DB]` `AVF_INFO/AVIN0001.{INP,BNP,INT}` boot-prompt hazard -> fail-closed `Slot 1 EROFS=30` firewall vs `FX6` `Update Media` / `Restore Media`.
- Group C (Wave 74): `Focus -> [AF/MF]` `[AF Transition Speed]` (`1..7`, def `5`), `[AF Subj. Shift Sens.]` (`1..5`, def `5`, `MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE` shared with `FX6` zero `6/7`), `[AF Assist]` (`SELP1650`/`SEL18200LE`/manual exclusion), `[Circ. of Focus Point]` (non-diagonal, Reset-immune), `[Focus Frame Color]` strictly `White`/`Red` (zero dormant colors, Reset-immune); Reset-immune `[Zebra Display]` `0 px` HDMI isolation (`70..100+`, `Custom1/2` `Std+Range`/`Lower Limit`, S-Log3 `41/61/94` IRE vs `Display LUT=On`), vs myth-busted `FX6` single-select `Off / Zebra 1 / Zebra 2` over `0%..109%`.
- Group D + Tier-0 (Wave 74): `15`-ratio `[Marker Display]` Clean-HDMI `0 px` isolation (Movie/`S&Q`-only, Reset-immune) vs `FX6` `Aspect Mask 0..15` & `User Box`; `[Save/Load Settings]` (`Slot 1`-locked `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, zero `PRO/CAMERA`, MR lockout, Ver. 1.xx reject, `EROFS=30` on Save/Delete against Tier-0 `Slot 1`) vs `[Camera Set. Memory]` (`1..3` NVRAM + `M1..M4` `CAMPR%02d%c.DAT` selectable `Slot 1/2`) vs `FX6` `Project > All File` (`Media(B)` 64 slots); plus `528 B FX3RCPT1` dual-media receipt gate & `16/16 H0 == H3` immutability.

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
from fx6_closure.realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier import (  # noqa: E402
    P354_AF_ASSIST_INCOMPATIBLE_LENSES,
    P354_AF_SUBJ_SHIFT_SENS_DEFAULT,
    P354_AF_SUBJ_SHIFT_SENS_MAX,
    P354_AF_SUBJ_SHIFT_SENS_MIN,
    P354_AF_SUBJ_SHIFT_SHARED_TYPO_SYMBOL,
    P354_AF_TRANSITION_SPEED_DEFAULT,
    P354_AF_TRANSITION_SPEED_MAX,
    P354_AF_TRANSITION_SPEED_MIN,
    P354_AWB_PRIORITY_DEFAULT,
    P354_AWB_PRIORITY_MODES,
    P354_BOUNDED_DONOR_PATHS,
    P354_CAMPR_CARD_SLOTS,
    P354_CAMPR_NVRAM_SLOTS,
    P354_CAMPR_PATH_TEMPLATE,
    P354_CHECK_GROUP_A_ID,
    P354_CHECK_GROUP_B_ID,
    P354_CHECK_GROUP_C_ID,
    P354_CHECK_GROUP_D_ID,
    P354_CIRC_FOCUS_POINT_DIAGONAL,
    P354_CIRC_FOCUS_POINT_MODES,
    P354_DELETE_CONFIRM_MODES,
    P354_DELETE_EXACT_FIVE_MODES,
    P354_DORMANT_LOCK_SYMBOLS,
    P354_ERRNO_EOPNOTSUPP,
    P354_ERRNO_EROFS,
    P354_FOCUS_ASSISTANT_EXACT_FOUR_ITEMS,
    P354_FOCUS_ASSISTANT_MENU_PATH,
    P354_FOCUS_FRAME_COLOR_DORMANT_COUNT,
    P354_FOCUS_FRAME_COLOR_MODES,
    P354_FOCUS_MAGNIF_TIME_DEFAULT,
    P354_FOCUS_MAGNIF_TIME_MODES,
    P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS,
    P354_FX3_FOCUS_RING_ROTATE_IMPLEMENTATIONS,
    P354_FX3_PHYSICAL_HOLD_SWITCH_COUNT,
    P354_FX3_PRO_CAMERA_HITS,
    P354_FX3_SAFETY_ZONE_MODES,
    P354_FX6_ALL_FILE_MEDIA,
    P354_FX6_ALL_FILE_MENU_PATH,
    P354_FX6_ALL_FILE_SLOTS_MAX,
    P354_FX6_ASPECT_MASK_DEFAULT,
    P354_FX6_ASPECT_MASK_MAX,
    P354_FX6_ASPECT_MASK_MIN,
    P354_FX6_ATW_SPEED_MAX,
    P354_FX6_ATW_SPEED_MIN,
    P354_FX6_CONVERTER_SYMBOL,
    P354_FX6_HDMI_FOCUS_MAG_RATIOS,
    P354_FX6_LCD_HOLD_SWITCH_PRESENT,
    P354_FX6_MARKER_ELEVEN_RATIOS,
    P354_FX6_MENU_LOCK_PASSCODE_DEFAULT,
    P354_FX6_PHYSICAL_HOLD_SWITCH_COUNT,
    P354_FX6_RESTORE_MEDIA_LABEL,
    P354_FX6_SHOCKLESS_WHITE_MODES,
    P354_FX6_UPDATE_MEDIA_LABEL,
    P354_FX6_USER_BOX_BOUNDS,
    P354_FX6_VF_FOCUS_MAG_RATIOS,
    P354_FX6_ZEBRA1_APERTURE_DEFAULT,
    P354_FX6_ZEBRA1_APERTURE_MAX,
    P354_FX6_ZEBRA1_APERTURE_MIN,
    P354_FX6_ZEBRA_DUAL_SIMULTANEOUS_SUPPORTED,
    P354_FX6_ZEBRA_SINGLE_SELECT_MODES,
    P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER,
    P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE,
    P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK,
    P354_GA_ERR_MODEL_OR_FW_FLOOR,
    P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK,
    P354_GB_ERR_DELETE_PROTECT_MEDIA_INFO_CONTRACT,
    P354_GB_ERR_DORMANT_FOCUS_RING_ROTATE_EOPNOTSUPP,
    P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET,
    P354_GB_ERR_SLOT1_RECOVER_IMAGE_DB_EROFS30,
    P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR,
    P354_GC_ERR_FX6_SINGLE_SELECT_ZEBRA_OR_RANGE,
    P354_GC_ERR_ZEBRA_CUSTOM_SLOG3_OR_HDMI_ISOLATION,
    P354_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P354_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P354_GD_ERR_MARKER_15_RATIOS_OR_CLEAN_HDMI,
    P354_GD_ERR_SAVELOAD_CAMSET_OR_CAMPR_CONTRACT,
    P354_GD_ERR_SLOT1_CAMSET_CAMPR_EROFS30,
    P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE,
    P354_GO_NO_GO_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_VERIFIED,
    P354_HEADER_READ_BYTES,
    P354_INITIAL_FOCUS_MAG_MOVIE_MODES,
    P354_INITIAL_FOCUS_MAG_STILL_APSC_MODES,
    P354_INITIAL_FOCUS_MAG_STILL_FF_MODES,
    P354_LOCK_OP_PARTS_BKID,
    P354_LOCK_OP_PARTS_DEFAULT,
    P354_LOCK_OP_PARTS_MENU_PATH,
    P354_LOCK_OP_PARTS_MODES,
    P354_MARKER_HDMI_PIXEL_COUNT,
    P354_MEDIA_INFO_MAX_STILL_IMAGES,
    P354_MENU_FN_LOCKS_SHUTTER,
    P354_MENU_FN_LOCKS_TOUCH,
    P354_MENU_FN_LOCK_HOLD_SECONDS,
    P354_MOVIE_AWB_LOCK_CUSTOM_KEYS,
    P354_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P354_PROTECT_EXACT_SEVEN_MODES,
    P354_PROTECT_HAS_CANCEL_ALL_IMAGES,
    P354_RECOVER_IMAGE_DB_FILES,
    P354_SAVELOAD_ACTIONS,
    P354_SAVELOAD_CAMSET_PATH_TEMPLATE,
    P354_SAVELOAD_CLOUD_SLOTS_MAX,
    P354_SAVELOAD_LOCAL_SLOTS_MAX,
    P354_SAVELOAD_LOCKED_SLOT,
    P354_SAVELOAD_MENU_PATH,
    P354_SCHEMA,
    P354_SHOCKLESS_WB_DEFAULT,
    P354_SHOCKLESS_WB_MODES,
    P354_SHUTTER_AWB_LOCK_DEFAULT,
    P354_SHUTTER_AWB_LOCK_MODES,
    P354_SLOG3_18PCT_GRAY_IRE,
    P354_SLOG3_90PCT_WHITE_IRE,
    P354_SLOG3_CLIP_CEILING_IRE,
    P354_SONY_HELP_GUIDE_ID,
    P354_STORAGE_SURFACE_COUNT,
    P354_TOUCH_OPERATION_MODES,
    P354_VERSION,
    P354_ZEBRA_HDMI_PIXEL_COUNT,
    P354_ZEBRA_IRE_MAX,
    P354_ZEBRA_IRE_MIN,
    P354_ZEBRA_LEVEL_ALL_OPTIONS,
    P354_ZEBRA_LEVEL_DEFAULT,
    P354_ZEBRA_LEVEL_FIXED_OPTIONS,
    P354_ZEBRA_RANGE_MAX,
    P354_ZEBRA_RANGE_MIN,
    PHASE354_EMMC_WRITE_COUNT,
    PHASE354_E_ND_ACTUATOR_TX_COUNT,
    PHASE354_PASSIVE_TX_BYTES_EMITTED,
    PHASE354_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE354_SLOT1_DATA_SECTOR_WRITES,
    PHASE354_USB_PACKETS_TRANSMITTED,
    PHASE354_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_354_CHECK_GROUP_IDS,
    PHASE_354_SCHEMA,
    PHASE_354_VERSION,
    REALHW_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_SAVELOAD_CAMSET_SCHEMA,
    _canonical_sha256_dict,
    build_simulated_phase354_tier0_receipts,
    evaluate_p354_check_group_a_lockop_menufn_and_wb,
    evaluate_p354_check_group_b_focus_assistant_and_media_db,
    evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra,
    evaluate_p354_check_group_d_marker_saveload_camset_and_tier0,
    evaluate_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight,
    inspect_phase354_donors_bounded,
    render_phase354_markdown,
    resolve_phase354_donor_file_or_none,
    run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight,
    verify_phase354_report,
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
            "preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestPhase354LockOpShocklessWbFocusMagAfSpeedZebraSaveLoadVerifier(unittest.TestCase):
    def _assert_err(self, res: object, code: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(any(code in e for e in errs), msg=f"Missing {code} in {errs}")

    def _assert_err_contains(self, res: object, sub: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(any(sub in e for e in errs), msg=f"Missing {sub!r} in {errs}")

    # ------------------------------------------------------------------
    # 01-12: Package Exports, 4-Mode Bounded Donor Inspection, Determinism
    # ------------------------------------------------------------------

    def test_001_package_all_exports_and_schema_constants(self) -> None:
        self.assertEqual(P354_SCHEMA, PHASE_354_SCHEMA)
        self.assertEqual(
            P354_SCHEMA,
            REALHW_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_SAVELOAD_CAMSET_SCHEMA,
        )
        self.assertEqual(P354_VERSION, PHASE_354_VERSION)
        self.assertEqual(P354_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(P354_STORAGE_SURFACE_COUNT, 16)
        self.assertEqual(len(PHASE_354_CHECK_GROUP_IDS), 4)
        for sym in (
            "P354_SCHEMA",
            "REALHW_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_SAVELOAD_CAMSET_SCHEMA",
            "build_simulated_phase354_tier0_receipts",
            "evaluate_p354_check_group_a_lockop_menufn_and_wb",
            "evaluate_p354_check_group_b_focus_assistant_and_media_db",
            "evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra",
            "evaluate_p354_check_group_d_marker_saveload_camset_and_tier0",
            "evaluate_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight",
            "run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight",
            "verify_phase354_report",
            "render_phase354_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_002_locked_zero_telemetry_constants(self) -> None:
        self.assertEqual(PHASE354_EMMC_WRITE_COUNT, 0)
        self.assertEqual(PHASE354_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(PHASE354_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE354_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE354_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE354_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE354_RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_003_bounded_donor_paths_count_and_64b_cap(self) -> None:
        self.assertEqual(len(P354_BOUNDED_DONOR_PATHS), 6)
        self.assertEqual(P354_HEADER_READ_BYTES, 64)

    def test_004_mode1_local_donor_o_rdonly_when_donors_present(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            insp = inspect_phase354_donors_bounded()
            self.assertEqual(insp.raw_firmware_bytes_leaked, 0)
            self.assertLessEqual(insp.bytes_read_total, 6 * P354_HEADER_READ_BYTES)
            if insp.donor_tree_present:
                self.assertEqual(insp.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertGreater(insp.donors_present, 0)
            else:
                self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_005_mode2_fx3_clean_room_test_env_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            insp = inspect_phase354_donors_bounded()
            self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(insp.donor_tree_present)
            self.assertEqual(insp.bytes_read_total, 0)
            self.assertEqual(insp.raw_firmware_bytes_leaked, 0)

    def test_006_mode3_fx3_fx6_force_clean_room_env_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
                simulate_bench_dry_run=True
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_007_mode4_donorless_ci_nonexistent_work_root(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            nonexistent = Path("/nonexistent/phase354/donor/root")
            self.assertIsNone(resolve_phase354_donor_file_or_none(None, "foo"))
            insp = inspect_phase354_donors_bounded(work_root=nonexistent)
            self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(insp.donor_tree_present)
            self.assertEqual(insp.donors_present, 0)
            self.assertEqual(insp.bytes_read_total, 0)

    def test_008_donor_override_dirs_allow_custom_o_rdonly_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fx6_dir = tmp_path / "fx6"
            fx3_dir = tmp_path / "fx3"
            fx6_dir.mkdir()
            fx3_dir.mkdir()
            (fx6_dir / "appFw.so").write_bytes(b"\x7fELF" + b"6" * 120)
            (fx3_dir / "appFw.so").write_bytes(b"\x7fELF" + b"3" * 120)
            (fx3_dir / "libmpr.so").write_bytes(b"\x7fELF" + b"m" * 120)
            (fx3_dir / "libSaveLoadSettings.so").write_bytes(b"\x7fELF" + b"s" * 120)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
                insp = inspect_phase354_donors_bounded(
                    force_clean_room=False,
                    work_root=Path("/nonexistent/phase354"),
                    fx6_lib_dir=fx6_dir,
                    fx3_modules_dir=fx3_dir,
                )
                self.assertEqual(insp.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(insp.donor_tree_present)
                self.assertGreaterEqual(insp.donors_present, 4)
                self.assertLessEqual(insp.bytes_read_total, 6 * P354_HEADER_READ_BYTES)
                self.assertEqual(insp.raw_firmware_bytes_leaked, 0)

    def test_009_default_offline_awaiting_receipts_never_authorizes_attach(self) -> None:
        rep = evaluate_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.overall_status, P354_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)

    def test_010_simulated_bench_dry_run_passes_4_of_4_and_16_of_16_attach_still_false(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase354_report(rep).valid)

    def test_011_deterministic_json_strips_elapsed_seconds_recursively(self) -> None:
        r1 = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        j1 = r1.to_deterministic_json()
        self.assertEqual(j1, r2.to_deterministic_json())
        self.assertNotIn("elapsed_seconds", j1)

    def test_012_canonical_sha256_ignores_nested_timing_fields(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["donor_inspection"]["elapsed_seconds"] = 999.123
        d["extra_elapsed_ms"] = 42
        self.assertEqual(_canonical_sha256_dict(d), rep.report_sha256)

    # ------------------------------------------------------------------
    # 13-36: Check Group A — Wave 73 [Lock Operation Parts], MENU+Fn 5s, WB
    # ------------------------------------------------------------------

    def test_013_group_a_model_fw_and_help_guide_floor(self) -> None:
        ga_ok = evaluate_p354_check_group_a_lockop_menufn_and_wb()
        self.assertTrue(ga_ok.passed)
        ga_bad_fw = evaluate_p354_check_group_a_lockop_menufn_and_wb(body_fw="6.01")
        ga_bad_id = evaluate_p354_check_group_a_lockop_menufn_and_wb(body_model_id=0x12345678)
        ga_bad_hg = evaluate_p354_check_group_a_lockop_menufn_and_wb(sony_help_guide_id="ilc/9999")
        for g in (ga_bad_fw, ga_bad_id, ga_bad_hg):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_014_lock_op_parts_path_bkid_and_exact_4_modes(self) -> None:
        self.assertEqual(
            P354_LOCK_OP_PARTS_MENU_PATH,
            "Setup -> [Dial Customize] -> [Lock Operation Parts]",
        )
        self.assertEqual(P354_LOCK_OP_PARTS_BKID, "BKID_APP_setting_device_lock")
        self.assertEqual(
            P354_LOCK_OP_PARTS_MODES,
            ("OFF", "MULTI_SELECTOR_ONLY", "DIAL_AND_WHEEL", "ALL"),
        )
        for m in P354_LOCK_OP_PARTS_MODES:
            self.assertTrue(evaluate_p354_check_group_a_lockop_menufn_and_wb(lock_op_parts=m).passed)
        ga_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(lock_op_parts="DIAL_PLUS_WHEEL")
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)

    def test_015_lock_op_parts_not_operation_customize_and_not_custom_key(self) -> None:
        g1 = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_lock_op_under_operation_customize=True
        )
        g2 = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_lock_op_via_custom_key=True
        )
        self.assertFalse(g1.passed)
        self.assertFalse(g2.passed)
        self._assert_err(g1, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)
        self._assert_err(g2, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)

    def test_016_lock_op_parts_reset_immune_and_initialize_resets_to_off(self) -> None:
        g_cam = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="ALL", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(g_cam.passed)
        self.assertTrue(g_cam.lock_op_parts_reset_immune)
        self.assertEqual(g_cam.effective_lock_op_parts, "ALL")

        g_init = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="ALL", reset_action="INITIALIZE"
        )
        self.assertTrue(g_init.passed)
        self.assertEqual(g_init.effective_lock_op_parts, "OFF")

        g_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_lock_op_wiped_by_camera_reset=True
        )
        self.assertFalse(g_bad.passed)
        self._assert_err(g_bad, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)

    def test_017_af_area_registration_on_forces_lock_op_parts_off(self) -> None:
        g_ok = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="ALL", af_area_registration="ON"
        )
        self.assertTrue(g_ok.passed)
        self.assertEqual(g_ok.effective_lock_op_parts, "OFF")

        g_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="ALL",
            af_area_registration="ON",
            expect_lock_op_active_when_af_area_reg_on=True,
        )
        self.assertFalse(g_bad.passed)
        self._assert_err(g_bad, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)

    def test_018_my_dial_temporarily_bypasses_lock_op_parts(self) -> None:
        g_ok = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="DIAL_AND_WHEEL", fn_long_press_active=True, my_dial_active=True
        )
        self.assertTrue(g_ok.passed)
        self.assertTrue(g_ok.lock_op_temporarily_bypassed)

        g_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="DIAL_AND_WHEEL", my_dial_active=True, expect_lock_op_blocks_my_dial=True
        )
        self.assertFalse(g_bad.passed)
        self._assert_err(g_bad, P354_GA_ERR_LOCK_OP_PARTS_PATH_OR_RULE)

    def test_019_menu_fn_5s_global_lock_requires_5s_and_preserves_shutter_touch(self) -> None:
        self.assertEqual(P354_MENU_FN_LOCK_HOLD_SECONDS, 5.0)
        self.assertFalse(P354_MENU_FN_LOCKS_SHUTTER)
        self.assertFalse(P354_MENU_FN_LOCKS_TOUCH)

        g_ok = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            menu_fn_global_lock_requested=True, menu_fn_5s_hold_seconds=5.0
        )
        self.assertTrue(g_ok.passed)
        self.assertTrue(g_ok.menu_fn_global_lock_active)
        self.assertTrue(g_ok.shutter_button_remains_active)

        g_short = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            menu_fn_global_lock_requested=True, menu_fn_5s_hold_seconds=4.5
        )
        self.assertFalse(g_short.passed)
        self._assert_err(g_short, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)

        g_shutter_touch = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            expect_menu_fn_5s_locks_shutter_or_touch=True
        )
        self.assertFalse(g_shutter_touch.passed)
        self._assert_err(g_shutter_touch, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)

    def test_020_touch_operation_modes_independent_of_menu_fn_5s(self) -> None:
        self.assertEqual(P354_TOUCH_OPERATION_MODES, ("ON", "ON_PLAYBACK_ONLY", "OFF"))
        for tm in P354_TOUCH_OPERATION_MODES:
            g = evaluate_p354_check_group_a_lockop_menufn_and_wb(
                menu_fn_global_lock_requested=True,
                menu_fn_5s_hold_seconds=5.0,
                touch_operation=tm,
            )
            self.assertTrue(g.passed)
            self.assertEqual(g.touch_operation, tm)
        g_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(touch_operation="EVF_ONLY")
        self.assertFalse(g_bad.passed)
        self._assert_err(g_bad, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)

    def test_021_dormant_uibiz_slikey_lock_rejected_eopnotsupp_95(self) -> None:
        self.assertIn("UIBIZ_SLIKEY_LOCK", P354_DORMANT_LOCK_SYMBOLS)
        self.assertEqual(P354_FX3_PHYSICAL_HOLD_SWITCH_COUNT, 0)
        g_dormant = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            dormant_sli_key_lock_requested=True
        )
        self.assertFalse(g_dormant.passed)
        self._assert_err(g_dormant, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)
        self._assert_err_contains(g_dormant, f"errno={P354_ERRNO_EOPNOTSUPP}")

        g_hold = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_fx3_has_physical_hold_switch=True
        )
        self.assertFalse(g_hold.passed)
        self._assert_err(g_hold, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)

    def test_022_fx6_dual_physical_hold_no_lcd_hold_and_4digit_pin(self) -> None:
        self.assertEqual(P354_FX6_PHYSICAL_HOLD_SWITCH_COUNT, 2)
        self.assertFalse(P354_FX6_LCD_HOLD_SWITCH_PRESENT)
        self.assertEqual(P354_FX6_MENU_LOCK_PASSCODE_DEFAULT, "0000")

        g_ok = evaluate_p354_check_group_a_lockop_menufn_and_wb(fx6_menu_lock_passcode="4273")
        self.assertTrue(g_ok.passed)

        for bad_pin in ("123", "12345", "abcd"):
            g_pin = evaluate_p354_check_group_a_lockop_menufn_and_wb(
                fx6_menu_lock_passcode=bad_pin
            )
            self.assertFalse(g_pin.passed)
            self._assert_err(g_pin, P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER)

        g_lcd = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_fx6_has_lcd_hold_switch=True
        )
        self.assertFalse(g_lcd.passed)
        self._assert_err(g_lcd, P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER)

    def test_023_shockless_wb_modes_resettable_and_movie_sq_only(self) -> None:
        self.assertEqual(P354_SHOCKLESS_WB_MODES, ("OFF", "1_FAST", "2", "3_SLOW"))
        self.assertEqual(P354_SHOCKLESS_WB_DEFAULT, "1_FAST")
        for mode in P354_SHOCKLESS_WB_MODES:
            g = evaluate_p354_check_group_a_lockop_menufn_and_wb(
                shoot_mode="MOVIE", shockless_wb=mode
            )
            self.assertTrue(g.passed)
            self.assertTrue(g.shockless_wb_active)
        g_reset = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shockless_wb="3_SLOW", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(g_reset.passed)
        self.assertEqual(g_reset.effective_shockless_wb_after_reset, "1_FAST")

        g_still = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shoot_mode="PHOTO", expect_shockless_wb_active_in_still=True
        )
        g_res_claim = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_shockless_wb_resists_camera_reset=True
        )
        self.assertFalse(g_still.passed)
        self.assertFalse(g_res_claim.passed)
        self._assert_err(g_still, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)
        self._assert_err(g_res_claim, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)

    def test_024_priority_set_in_awb_resettable_and_cine_ei_disabled(self) -> None:
        self.assertEqual(P354_AWB_PRIORITY_MODES, ("STANDARD", "AMBIENCE", "WHITE"))
        self.assertEqual(P354_AWB_PRIORITY_DEFAULT, "STANDARD")
        g_flex = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            log_shooting_mode="FLEXIBLE_ISO", awb_priority="WHITE"
        )
        self.assertTrue(g_flex.passed)
        self.assertTrue(g_flex.awb_priority_effective_in_pipeline)

        g_ei = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            log_shooting_mode="CINE_EI", awb_priority="AMBIENCE"
        )
        self.assertTrue(g_ei.passed)
        self.assertFalse(g_ei.awb_priority_effective_in_pipeline)

        g_ei_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            log_shooting_mode="CINE_EI_QUICK", expect_awb_effective_in_cine_ei=True
        )
        g_res_bad = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_awb_priority_resists_camera_reset=True
        )
        self.assertFalse(g_ei_bad.passed)
        self.assertFalse(g_res_bad.passed)
        self._assert_err(g_ei_bad, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)
        self._assert_err(g_res_bad, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)

    def test_025_shutter_awb_lock_still_only_reset_immune_and_movie_custom_key(self) -> None:
        self.assertEqual(
            P354_SHUTTER_AWB_LOCK_MODES,
            ("SHUTTER_HALF_PRESS", "CONT_SHOOTING", "OFF"),
        )
        self.assertEqual(
            P354_MOVIE_AWB_LOCK_CUSTOM_KEYS,
            ("NONE", "AWB_LOCK_HOLD", "AWB_LOCK_TOGGLE"),
        )
        g_still_reset = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shoot_mode="PHOTO",
            shutter_awb_lock="SHUTTER_HALF_PRESS",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(g_still_reset.passed)
        self.assertTrue(g_still_reset.shutter_awb_lock_active)
        self.assertTrue(g_still_reset.shutter_awb_lock_reset_immune)
        self.assertEqual(g_still_reset.effective_shutter_awb_lock_after_reset, "SHUTTER_HALF_PRESS")

        g_init = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shoot_mode="PHOTO",
            shutter_awb_lock="CONT_SHOOTING",
            reset_action="INITIALIZE",
        )
        self.assertTrue(g_init.passed)
        self.assertEqual(g_init.effective_shutter_awb_lock_after_reset, "OFF")

        g_bad_movie = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shoot_mode="MOVIE", expect_shutter_awb_lock_active_in_movie=True
        )
        g_bad_reset = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            claimed_shutter_awb_lock_wiped_by_camera_reset=True
        )
        self.assertFalse(g_bad_movie.passed)
        self.assertFalse(g_bad_reset.passed)
        self._assert_err(g_bad_movie, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)
        self._assert_err(g_bad_reset, P354_GA_ERR_WB_SHOCKLESS_AWB_SHUTTER_LOCK)

    def test_026_fx6_atw_speed_1_to_5_shockless_white_and_diadem_converter(self) -> None:
        self.assertEqual((P354_FX6_ATW_SPEED_MIN, P354_FX6_ATW_SPEED_MAX), (1, 5))
        self.assertEqual(P354_FX6_SHOCKLESS_WHITE_MODES, ("OFF", "1", "2", "3"))
        self.assertIn("diadem_pro_settings_converter", P354_FX6_CONVERTER_SYMBOL)
        for spd in range(1, 6):
            self.assertTrue(
                evaluate_p354_check_group_a_lockop_menufn_and_wb(fx6_atw_speed=spd).passed
            )
        for bad_spd in (0, 6, 7):
            g = evaluate_p354_check_group_a_lockop_menufn_and_wb(fx6_atw_speed=bad_spd)
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER)

        g_up7 = evaluate_p354_check_group_a_lockop_menufn_and_wb(claimed_fx6_atw_speed_up_to_7=True)
        g_conv = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            diadem_pro_settings_converter_warm_cool_verified=False
        )
        self.assertFalse(g_up7.passed)
        self.assertFalse(g_conv.passed)
        self._assert_err(g_up7, P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER)
        self._assert_err(g_conv, P354_GA_ERR_FX6_HOLD_PIN_OR_ATW_CONVERTER)

    def test_027_group_a_invalid_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(shockless_wb="SLOW_4").passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(awb_priority="WARM").passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(
                shutter_awb_lock="SHUT_HALF_DOWN"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(fx6_shockless_white="4").passed
        )

    def test_028_group_a_camera_reset_wipes_shockless_and_awb_priority_but_keeps_lock_and_shutter_awb(self) -> None:
        g = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            shoot_mode="PHOTO",
            reset_action="CAMERA_SETTINGS_RESET",
            lock_op_parts="MULTI_SELECTOR_ONLY",
            shockless_wb="3_SLOW",
            awb_priority="AMBIENCE",
            shutter_awb_lock="CONT_SHOOTING",
        )
        self.assertTrue(g.passed)
        self.assertEqual(g.effective_lock_op_parts, "MULTI_SELECTOR_ONLY")
        self.assertEqual(g.effective_shockless_wb_after_reset, "1_FAST")
        self.assertEqual(g.effective_awb_priority_after_reset, "STANDARD")
        self.assertEqual(g.effective_shutter_awb_lock_after_reset, "CONT_SHOOTING")

    def test_029_group_a_fn_long_press_and_menu_fn_5s_positive_combo(self) -> None:
        g = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            lock_op_parts="ALL",
            fn_long_press_active=True,
            menu_fn_global_lock_requested=True,
            menu_fn_5s_hold_seconds=5.5,
            touch_operation="ON_PLAYBACK_ONLY",
        )
        self.assertTrue(g.passed)
        self.assertTrue(g.menu_fn_global_lock_active)
        self.assertTrue(g.shutter_button_remains_active)

    def test_030_group_a_menu_fn_less_than_5s_claim_rejected(self) -> None:
        g = evaluate_p354_check_group_a_lockop_menufn_and_wb(
            expect_menu_fn_less_than_5s_locks=True
        )
        self.assertFalse(g.passed)
        self._assert_err(g, P354_GA_ERR_MENU_FN_5S_OR_DORMANT_SLIKEY_LOCK)

    # ------------------------------------------------------------------
    # 31-56: Check Group B — Wave 73 [Focus Assistant], Dormant Rotate, DB
    # ------------------------------------------------------------------

    def test_031_focus_assistant_exact_four_reset_immune_items(self) -> None:
        self.assertEqual(P354_FOCUS_ASSISTANT_MENU_PATH, "Focus -> [Focus Assistant]")
        self.assertEqual(
            P354_FOCUS_ASSISTANT_EXACT_FOUR_ITEMS,
            (
                "AUTO_MAGNIFIER_IN_MF",
                "FOCUS_MAGNIF_TIME",
                "INITIAL_FOCUS_MAG",
                "AF_IN_FOCUS_MAG",
            ),
        )
        gb = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gb.passed)
        self.assertTrue(gb.focus_assistant_reset_immune)
        self.assertEqual(len(gb.exposed_focus_assistant_items), 4)

        gb_bad_items = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            exposed_focus_assistant_items=(
                "AUTO_MAGNIFIER_IN_MF",
                "FOCUS_MAGNIF_TIME",
                "INITIAL_FOCUS_MAG",
                "FOCUS_RING_ROTATE",
            )
        )
        gb_bad_reset = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_focus_assistant_wiped_by_camera_reset=True
        )
        self.assertFalse(gb_bad_items.passed)
        self.assertFalse(gb_bad_reset.passed)
        self._assert_err(gb_bad_items, P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET)
        self._assert_err(gb_bad_reset, P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET)

    def test_032_auto_magnifier_and_af_in_focus_mag_are_still_only(self) -> None:
        gb_still = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            shoot_mode="PHOTO", focus_mode="MF"
        )
        self.assertTrue(gb_still.passed)
        self.assertTrue(gb_still.auto_magnifier_in_mf_active)
        self.assertTrue(gb_still.af_in_focus_mag_active)

        gb_movie = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            shoot_mode="MOVIE", focus_mode="MF"
        )
        self.assertTrue(gb_movie.passed)
        self.assertFalse(gb_movie.auto_magnifier_in_mf_active)
        self.assertFalse(gb_movie.af_in_focus_mag_active)

        g1 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            shoot_mode="MOVIE", expect_auto_magnifier_active_in_movie=True
        )
        g2 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            shoot_mode="S_AND_Q", expect_af_in_focus_mag_active_in_movie=True
        )
        self.assertFalse(g1.passed)
        self.assertFalse(g2.passed)
        self._assert_err(g1, P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET)
        self._assert_err(g2, P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET)

    def test_033_initial_focus_mag_ff_x21_not_x41_and_apsc_x15_and_movie_x40(self) -> None:
        self.assertEqual(P354_INITIAL_FOCUS_MAG_STILL_FF_MODES, ("X1_0", "X2_1"))
        self.assertEqual(P354_INITIAL_FOCUS_MAG_STILL_APSC_MODES, ("X1_0", "X1_5"))
        self.assertEqual(P354_INITIAL_FOCUS_MAG_MOVIE_MODES, ("X1_0", "X4_0"))
        gb_ok = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            initial_focus_mag_still_ff="X2_1",
            initial_focus_mag_still_apsc="X1_5",
            initial_focus_mag_movie="X4_0",
        )
        self.assertTrue(gb_ok.passed)

        gb_ff_x41 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            initial_focus_mag_still_ff="X4_1"
        )
        gb_ff_claim = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_still_ff_initial_mag_has_x4_1=True
        )
        gb_mov_x21 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            initial_focus_mag_movie="X2_1"
        )
        for g in (gb_ff_x41, gb_ff_claim, gb_mov_x21):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GB_ERR_FOCUS_ASSISTANT_4_ITEMS_OR_RESET)

    def test_034_focus_magnif_time_modes(self) -> None:
        self.assertEqual(P354_FOCUS_MAGNIF_TIME_MODES, ("2_SEC", "5_SEC", "NO_LIMIT"))
        for t in P354_FOCUS_MAGNIF_TIME_MODES:
            self.assertTrue(
                evaluate_p354_check_group_b_focus_assistant_and_media_db(
                    focus_magnif_time=t
                ).passed
            )
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                focus_magnif_time="10_SEC"
            ).passed
        )

    def test_035_dormant_focus_ring_rotate_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(P354_FX3_FOCUS_RING_ROTATE_IMPLEMENTATIONS, 0)
        g1 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            dormant_focus_ring_rotate_requested=True
        )
        g2 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_fx3_implements_focus_ring_rotate=True
        )
        for g in (g1, g2):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GB_ERR_DORMANT_FOCUS_RING_ROTATE_EOPNOTSUPP)
            self._assert_err_contains(g, f"errno={P354_ERRNO_EOPNOTSUPP}")

    def test_036_fx6_af_assist_push_auto_vf_x3_x6_and_ver6_hdmi_focus_mag_x2_x4(self) -> None:
        self.assertEqual(P354_FX6_VF_FOCUS_MAG_RATIOS, ("X3", "X6"))
        self.assertEqual(P354_FX6_HDMI_FOCUS_MAG_RATIOS, ("X2", "X4"))
        gb_ok = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            fx6_af_assist="ON", fx6_focus_mag_button_target="VF_AND_HDMI"
        )
        self.assertTrue(gb_ok.passed)
        self.assertTrue(gb_ok.fx6_push_auto_present)

        g1 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_fx6_lacks_ver6_hdmi_focus_mag=True
        )
        g2 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            fx6_push_auto_present=False
        )
        g3 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            fx6_focus_mag_button_target="SDI_ONLY"
        )
        for g in (g1, g2, g3):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GB_ERR_DORMANT_FOCUS_RING_ROTATE_EOPNOTSUPP)

    def test_037_delete_exact_5_batch_modes_and_delete_confirm(self) -> None:
        self.assertEqual(len(P354_DELETE_EXACT_FIVE_MODES), 5)
        self.assertEqual(P354_DELETE_CONFIRM_MODES, ("CANCEL_FIRST", "DELETE_FIRST"))
        gb_ok = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            delete_confirm="DELETE_FIRST", delete_pressing_twice="ON"
        )
        self.assertTrue(gb_ok.passed)

        gb_bad = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            exposed_delete_modes=("MULTIPLE_IMG", "ALL_IN_THIS_FOLDER")
        )
        self.assertFalse(gb_bad.passed)
        self._assert_err(gb_bad, P354_GB_ERR_DELETE_PROTECT_MEDIA_INFO_CONTRACT)

    def test_038_protect_exact_7_modes_zero_cancel_all_images_and_proxy_co_protect(self) -> None:
        self.assertEqual(len(P354_PROTECT_EXACT_SEVEN_MODES), 7)
        self.assertFalse(P354_PROTECT_HAS_CANCEL_ALL_IMAGES)

        g1 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_protect_has_cancel_all_images=True
        )
        g2 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            exposed_protect_modes=P354_PROTECT_EXACT_SEVEN_MODES[:6] + ("CANCEL_ALL_IMAGES",)
        )
        g3 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            proxy_co_protection_active=False
        )
        for g in (g1, g2, g3):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GB_ERR_DELETE_PROTECT_MEDIA_INFO_CONTRACT)

    def test_039_display_media_info_readonly_40000_still_cap(self) -> None:
        self.assertEqual(P354_MEDIA_INFO_MAX_STILL_IMAGES, 40000)
        self.assertTrue(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                media_info_still_count=40000
            ).passed
        )
        g_over = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            media_info_still_count=40001
        )
        g_claim = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            expect_media_info_over_40000=True
        )
        self.assertFalse(g_over.passed)
        self.assertFalse(g_claim.passed)
        self._assert_err(g_over, P354_GB_ERR_DELETE_PROTECT_MEDIA_INFO_CONTRACT)
        self._assert_err(g_claim, P354_GB_ERR_DELETE_PROTECT_MEDIA_INFO_CONTRACT)

    def test_040_recover_image_db_avf_info_slot1_erofs30_firewall(self) -> None:
        self.assertEqual(
            P354_RECOVER_IMAGE_DB_FILES,
            ("AVF_INFO/AVIN0001.INP", "AVF_INFO/AVIN0001.BNP", "AVF_INFO/AVIN0001.INT"),
        )
        self.assertEqual(P354_FX6_UPDATE_MEDIA_LABEL, "Update Media")
        self.assertEqual(P354_FX6_RESTORE_MEDIA_LABEL, "Restore Media")

        for kw in (
            {"avf_info_boot_prompt_active": True},
            {"recover_image_db_requested": True},
            {"delete_on_slot1_requested": True},
            {"protect_write_on_slot1_requested": True},
        ):
            gb = evaluate_p354_check_group_b_focus_assistant_and_media_db(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P354_GB_ERR_SLOT1_RECOVER_IMAGE_DB_EROFS30)
            self._assert_err_contains(gb, f"errno={P354_ERRNO_EROFS}")
            self.assertEqual(gb.slot1_data_sector_writes, 0)

    def test_041_recover_image_db_battery_gate_reset_immunity_and_ftp_reset(self) -> None:
        g1 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            slot1_contains_tier0_dump=False,
            recover_image_db_requested=True,
            battery_depleted=True,
        )
        g2 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            claimed_recover_db_wiped_by_reset_or_init=True
        )
        g3 = evaluate_p354_check_group_b_focus_assistant_and_media_db(
            resets_ftp_transfer_result=False
        )
        for g in (g1, g2, g3):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GB_ERR_SLOT1_RECOVER_IMAGE_DB_EROFS30)

    # ------------------------------------------------------------------
    # 42-68: Check Group C — Wave 74 AF Speed/Shift, Frame Color & Zebra
    # ------------------------------------------------------------------

    def test_042_af_transition_speed_1_to_7_default_5_and_reset(self) -> None:
        self.assertEqual(
            (P354_AF_TRANSITION_SPEED_MIN, P354_AF_TRANSITION_SPEED_MAX, P354_AF_TRANSITION_SPEED_DEFAULT),
            (1, 7, 5),
        )
        for spd in range(1, 8):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_transition_speed=spd, reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(gc.passed)
            self.assertEqual(gc.effective_af_transition_speed_after_reset, 5)
        for bad in (0, 8):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_transition_speed=bad
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

    def test_043_af_subj_shift_sens_1_to_5_shared_with_fx6_zero_6_7(self) -> None:
        self.assertEqual(
            (P354_AF_SUBJ_SHIFT_SENS_MIN, P354_AF_SUBJ_SHIFT_SENS_MAX, P354_AF_SUBJ_SHIFT_SENS_DEFAULT),
            (1, 5, 5),
        )
        self.assertEqual(P354_AF_SUBJ_SHIFT_SHARED_TYPO_SYMBOL, "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE")
        for val in range(1, 6):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_subj_shift_sens=val, fx6_af_subj_shift_sens=val
            )
            self.assertTrue(gc.passed)
        for bad in (0, 6, 7):
            g_fx3 = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_subj_shift_sens=bad
            )
            g_fx6 = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                fx6_af_subj_shift_sens=bad
            )
            self.assertFalse(g_fx3.passed)
            self.assertFalse(g_fx6.passed)
            self._assert_err(g_fx3, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)
            self._assert_err(g_fx6, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

        g_claim67 = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_fx6_af_subj_shift_sens_has_6_or_7=True
        )
        g_def = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_af_transition_speed_default_is_not_5=True
        )
        g_res = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_af_speed_or_shift_resists_camera_reset=True
        )
        for g in (g_claim67, g_def, g_res):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

    def test_044_af_assist_incompatible_lenses_and_mode_gating(self) -> None:
        self.assertEqual(
            P354_AF_ASSIST_INCOMPATIBLE_LENSES,
            ("SELP1650", "SEL18200LE", "MANUAL_NO_CONTACTS"),
        )
        gc_ok = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            shoot_mode="MOVIE", focus_mode="AF_C", af_assist="ON", lens_id="SEL2470GM2"
        )
        self.assertTrue(gc_ok.passed)
        self.assertTrue(gc_ok.af_assist_active)

        for bad_lens in P354_AF_ASSIST_INCOMPATIBLE_LENSES:
            gc_incompat = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_assist="ON", lens_id=bad_lens
            )
            self.assertTrue(gc_incompat.passed)
            self.assertFalse(gc_incompat.af_assist_active)
            gc_bad = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                lens_id=bad_lens, expect_af_assist_active_on_incompatible_lens=True
            )
            self.assertFalse(gc_bad.passed)
            self._assert_err(gc_bad, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

    def test_045_circ_of_focus_point_non_diagonal_and_reset_immune(self) -> None:
        self.assertEqual(P354_CIRC_FOCUS_POINT_MODES, ("DOES_NOT_CIRCULATE", "CIRCULATE"))
        self.assertFalse(P354_CIRC_FOCUS_POINT_DIAGONAL)
        gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            circ_of_focus_point="CIRCULATE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gc.passed)
        self.assertTrue(gc.circ_of_focus_point_reset_immune)
        self.assertFalse(gc.circ_of_focus_point_diagonal)

        g_diag = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            expect_focus_point_circulates_diagonally=True
        )
        self.assertFalse(g_diag.passed)
        self._assert_err(g_diag, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

    def test_046_focus_frame_color_strictly_white_or_red_zero_dormant_colors(self) -> None:
        self.assertEqual(P354_FOCUS_FRAME_COLOR_MODES, ("WHITE", "RED"))
        self.assertEqual(P354_FOCUS_FRAME_COLOR_DORMANT_COUNT, 0)
        for col in ("WHITE", "RED"):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                focus_frame_color=col
            )
            self.assertTrue(gc.passed)
            self.assertTrue(gc.focus_frame_color_reset_immune)
            self.assertEqual(gc.focus_frame_color_dormant_count, 0)

        for bad_col in ("GREEN", "YELLOW", "BLUE"):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                focus_frame_color=bad_col
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

        g_dorm = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_focus_frame_color_has_dormant_colors=True
        )
        g_wiped = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_focus_area_circ_or_color_wiped_by_camera_reset=True
        )
        self.assertFalse(g_dorm.passed)
        self.assertFalse(g_wiped.passed)
        self._assert_err(g_dorm, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)
        self._assert_err(g_wiped, P354_GC_ERR_AF_SPEED_SHIFT_ASSIST_OR_FRAME_COLOR)

    def test_047_fx3_zebra_fixed_presets_custom1_2_bounds_and_slog3_ire(self) -> None:
        self.assertEqual(
            P354_ZEBRA_LEVEL_FIXED_OPTIONS,
            ("70", "75", "80", "85", "90", "95", "100", "100_PLUS"),
        )
        self.assertEqual(
            (P354_SLOG3_18PCT_GRAY_IRE, P354_SLOG3_90PCT_WHITE_IRE, P354_SLOG3_CLIP_CEILING_IRE),
            (41, 61, 94),
        )
        for lvl in P354_ZEBRA_LEVEL_ALL_OPTIONS:
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                zebra_display="ON",
                zebra_level=lvl,
                zebra_custom1_type="STD_AND_RANGE",
                zebra_custom1_standard=41,
                zebra_custom1_range=2,
                zebra_custom2_type="LOWER_LIMIT",
                zebra_custom2_lower_limit=94,
            )
            self.assertTrue(gc.passed)
            self.assertTrue(gc.zebra_reset_immune)
            self.assertEqual(gc.zebra_hdmi_pixel_count, 0)

    def test_048_fx3_zebra_custom_overflow_hdmi_reset_and_display_lut_rejections(self) -> None:
        g_overflow = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            zebra_custom1_type="STD_AND_RANGE",
            zebra_custom1_standard=105,
            zebra_custom1_range=5,
        )
        g_range = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            zebra_custom1_range=11
        )
        g_ll = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            zebra_custom2_lower_limit=110
        )
        g_hdmi = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_zebra_outputs_over_hdmi=True
        )
        g_res = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            claimed_zebra_wiped_by_camera_reset=True
        )
        g_lut = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            display_lut_on=True, expect_slog3_ire_unchanged_with_display_lut_on=True
        )
        for g in (g_overflow, g_range, g_ll, g_hdmi, g_res, g_lut):
            self.assertFalse(g.passed)
            self._assert_err(g, P354_GC_ERR_ZEBRA_CUSTOM_SLOG3_OR_HDMI_ISOLATION)

    def test_049_fx6_single_select_zebra_off_zebra1_zebra2_debunks_dual_both_myth(self) -> None:
        self.assertEqual(P354_FX6_ZEBRA_SINGLE_SELECT_MODES, ("OFF", "ZEBRA1", "ZEBRA2"))
        self.assertFalse(P354_FX6_ZEBRA_DUAL_SIMULTANEOUS_SUPPORTED)
        self.assertEqual((P354_ZEBRA_IRE_MIN, P354_ZEBRA_IRE_MAX), (0, 109))
        self.assertEqual((P354_FX6_ZEBRA1_APERTURE_MIN, P354_FX6_ZEBRA1_APERTURE_MAX), (2, 20))

        for m in P354_FX6_ZEBRA_SINGLE_SELECT_MODES:
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                fx6_zebra_setting=m,
                fx6_zebra1_level=0,
                fx6_zebra1_aperture_level=2,
                fx6_zebra2_level=109,
            )
            self.assertTrue(gc.passed)
            self.assertFalse(gc.fx6_zebra_dual_simultaneous_supported)

        for kw in (
            {"fx6_zebra_setting": "BOTH"},
            {"fx6_dual_zebra_both_requested": True},
            {"claimed_fx6_supports_dual_simultaneous_zebra": True},
            {"claimed_fx6_zebra_min_is_50_or_max_107": True},
            {"fx6_zebra1_level": 110},
            {"fx6_zebra1_aperture_level": 1},
            {"fx6_zebra2_level": -1},
        ):
            gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P354_GC_ERR_FX6_SINGLE_SELECT_ZEBRA_OR_RANGE)

    # ------------------------------------------------------------------
    # 50-82: Check Group D — 15-Ratio Marker, Save/Load vs CAMPR & Tier-0
    # ------------------------------------------------------------------

    def test_050_marker_display_exact_15_ratios_clean_hdmi_0px_and_reset_immune(self) -> None:
        self.assertEqual(len(P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS), 15)
        self.assertEqual(P354_MARKER_HDMI_PIXEL_COUNT, 0)
        self.assertEqual(P354_FX3_SAFETY_ZONE_MODES, ("OFF", "80%", "90%"))

        for ratio in P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS:
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True,
                marker_display="ON",
                center_marker="ON",
                aspect_marker=ratio,
                safety_zone="90%",
                guideframe="ON",
                reset_action="CAMERA_SETTINGS_RESET",
            )
            self.assertTrue(gd.passed)
            self.assertEqual(gd.marker_hdmi_pixel_count, 0)
            self.assertTrue(gd.marker_reset_immune)

    def test_051_marker_display_rejects_wrong_ratios_still_hdmi_or_reset_claim(self) -> None:
        for kw in (
            {"exposed_aspect_marker_ratios": P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS[:14]},
            {"aspect_marker": "2.40:1"},
            {"expect_marker_outputs_over_hdmi": True},
            {"shoot_mode": "PHOTO", "expect_marker_active_in_still": True},
            {"claimed_marker_wiped_by_camera_reset": True},
            {"safety_zone": "92.5%"},
        ):
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P354_GD_ERR_MARKER_15_RATIOS_OR_CLEAN_HDMI)

    def test_052_fx6_marker_11_ratios_aspect_mask_0_to_15_and_user_box_bounds(self) -> None:
        self.assertEqual(len(P354_FX6_MARKER_ELEVEN_RATIOS), 11)
        self.assertEqual((P354_FX6_ASPECT_MASK_MIN, P354_FX6_ASPECT_MASK_MAX), (0, 15))
        self.assertEqual(P354_FX6_ASPECT_MASK_DEFAULT, 12)
        self.assertEqual(P354_FX6_USER_BOX_BOUNDS["width"], (3, 479))
        self.assertEqual(P354_FX6_USER_BOX_BOUNDS["height"], (3, 269))
        gd_ok = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            simulate_bench_dry_run=True,
            fx6_aspect_mask=15,
            fx6_user_box_width=479,
            fx6_user_box_height=269,
            fx6_user_box_h_pos=-476,
            fx6_user_box_v_pos=266,
        )
        self.assertTrue(gd_ok.passed)

        for kw in (
            {"fx6_aspect_mask": 16},
            {"fx6_user_box_width": 480},
            {"fx6_user_box_height": 2},
            {"fx6_user_box_h_pos": 477},
            {"fx6_user_box_v_pos": -267},
        ):
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P354_GD_ERR_MARKER_15_RATIOS_OR_CLEAN_HDMI)

    def test_053_saveload_settings_path_slot1_lock_camset_template_and_zero_pro_camera(self) -> None:
        self.assertEqual(
            P354_SAVELOAD_MENU_PATH,
            "Setup -> [Reset/Save Settings] -> [Save/Load Settings]",
        )
        self.assertEqual(P354_SAVELOAD_LOCKED_SLOT, 1)
        self.assertEqual(P354_SAVELOAD_CAMSET_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT")
        self.assertEqual(P354_SAVELOAD_LOCAL_SLOTS_MAX, 10)
        self.assertEqual(P354_SAVELOAD_CLOUD_SLOTS_MAX, 60)
        self.assertEqual(P354_FX3_PRO_CAMERA_HITS, 0)

        gd_load = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            simulate_bench_dry_run=True,
            saveload_action="LOAD_READONLY",
            saveload_source_fw="7.02",
        )
        self.assertTrue(gd_load.passed)

    def test_054_saveload_rejects_slot2_setup_option_pro_camera_ver1_mr_and_exclusions(self) -> None:
        for kw in (
            {"claimed_saveload_under_setup_option": True},
            {"saveload_slot": 2},
            {"claimed_saveload_supports_slot2": True},
            {"claimed_fx3_uses_pro_camera_path": True},
            {"claimed_camset_includes_network_or_iptc_or_custom_wb": True},
            {"claimed_cam_set_saveload_naming": True},
            {"claimed_fx6_all_file_under_tc_media": True},
            {"in_mr_mode": True, "saveload_action": "LOAD_READONLY"},
            {"saveload_action": "LOAD_READONLY", "saveload_source_fw": "1.01"},
        ):
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P354_GD_ERR_SAVELOAD_CAMSET_OR_CAMPR_CONTRACT)

    def test_055_campr_memory_recall_slot2_write_allowed_slot1_write_blocked_erofs30(self) -> None:
        self.assertEqual(P354_CAMPR_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT")
        self.assertEqual(P354_CAMPR_CARD_SLOTS, ("M1", "M2", "M3", "M4"))
        self.assertEqual(P354_CAMPR_NVRAM_SLOTS, ("1", "2", "3"))
        self.assertEqual(P354_FX6_ALL_FILE_MENU_PATH, "Project > All File")
        self.assertEqual(P354_FX6_ALL_FILE_MEDIA, "MEDIA_B")
        self.assertEqual(P354_FX6_ALL_FILE_SLOTS_MAX, 64)

        gd_slot2 = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            simulate_bench_dry_run=True,
            memory_recall_media_slot=2,
            campr_write_requested=True,
            campr_recall_requested=True,
        )
        self.assertTrue(gd_slot2.passed)

        for kw in (
            {"saveload_action": "SAVE"},
            {"saveload_action": "DELETE"},
            {"memory_recall_media_slot": 1, "campr_write_requested": True},
            {"slot1_write_requested": True},
        ):
            gd_blk = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd_blk.passed)
            self._assert_err(gd_blk, P354_GD_ERR_SLOT1_CAMSET_CAMPR_EROFS30)
            self._assert_err_contains(gd_blk, f"errno={P354_ERRNO_EROFS}")

    def test_056_fail_closed_zero_rf_and_hardware_redlines(self) -> None:
        for kw in (
            {"airplane_mode": "OFF"},
            {"wireless_rf_packets_emitted": 1},
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P354_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_057_tier0_single_receipt_missing_copy_b_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"], st_dev_a_override=1301
        )
        self.assertFalse(gd.passed)
        self.assertFalse(gd.tier0_receipt_verified)
        self._assert_err(gd, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_058_tier0_same_st_dev_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=999,
            st_dev_b_override=999,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_059_tier0_byte_parity_and_tamper_detection_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        tampered = bytearray(sim["receipt_a_bytes"])
        tampered[32] ^= 0xFF
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=bytes(tampered),
            receipt_b_bytes=bytes(tampered),
            st_dev_a_override=1301,
            st_dev_b_override=1302,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        gd_mismatch = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=bytes(tampered),
            st_dev_a_override=1301,
            st_dev_b_override=1302,
        )
        self.assertFalse(gd_mismatch.passed)
        self._assert_err(gd_mismatch, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_060_tier0_trivial_serial_or_cid_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        gd_ser = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1301,
            st_dev_b_override=1302,
            body_serial="00000000",
        )
        gd_cid = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1301,
            st_dev_b_override=1302,
            emmc_cid="0" * 32,
        )
        self.assertFalse(gd_ser.passed)
        self.assertFalse(gd_cid.passed)
        self._assert_err(gd_ser, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        self._assert_err(gd_cid, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_061_tier0_h0_h3_drift_detection_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        h3_drifted = dict(sim["h3_baselines"])
        h3_drifted[REQUIRED_H0_BASELINE_KEYS[0]] = "f" * 64
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1301,
            st_dev_b_override=1302,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=h3_drifted,
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_equals_h3_count, 15)
        self._assert_err(gd, P354_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_062_tier0_physical_receipt_files_verified_with_distinct_st_dev(self) -> None:
        sim = build_simulated_phase354_tier0_receipts(
            body_serial="FX3REAL7020354",
            emmc_cid="11010030303847333000a1b2c3d49354",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            p_a = tmp_path / "FX3RCPT1_A.bin"
            p_b = tmp_path / "FX3RCPT1_B.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])

            orig_stat = os.stat

            def fake_stat(path: object, *a: object, **kw: object) -> object:
                res = orig_stat(path, *a, **kw)
                if Path(str(path)) == p_a:
                    return os.stat_result((res.st_mode, res.st_ino, 8801, res.st_nlink, res.st_uid, res.st_gid, res.st_size, res.st_atime, res.st_mtime, res.st_ctime))
                if Path(str(path)) == p_b:
                    return os.stat_result((res.st_mode, res.st_ino, 8802, res.st_nlink, res.st_uid, res.st_gid, res.st_size, res.st_atime, res.st_mtime, res.st_ctime))
                return res

            with mock.patch("os.stat", side_effect=fake_stat):
                rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
                    force_clean_room=True,
                    receipt_a_path=p_a,
                    receipt_b_path=p_b,
                    body_serial="FX3REAL7020354",
                    emmc_cid="11010030303847333000a1b2c3d49354",
                    h0_baselines_a=sim["h0_baselines_a"],
                    h0_baselines_b=sim["h0_baselines_b"],
                    h3_baselines=sim["h3_baselines"],
                )
            self.assertEqual(
                rep.go_no_go,
                P354_GO_NO_GO_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_VERIFIED,
            )
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertTrue(verify_phase354_report(rep).valid)

    # ------------------------------------------------------------------
    # 63-92: Additional Cross-Matrix & Edge Boundary Tests
    # ------------------------------------------------------------------

    def test_063_full_orchestrator_failure_propagates_blocked_go_no_go(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            claimed_fx6_supports_dual_simultaneous_zebra=True,
        )
        self.assertEqual(
            rep.go_no_go,
            P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE,
        )
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase354_report(rep).valid)

    def test_064_verify_phase354_report_catches_sha_tamper_and_locked_flags(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertTrue(verify_phase354_report(rep).valid)

        d_sha = copy.deepcopy(rep.to_dict())
        d_sha["check_group_c"]["af_transition_speed"] = 1
        res_sha = verify_phase354_report(d_sha)
        self.assertFalse(res_sha.valid)
        self.assertTrue(any("report_sha256 mismatch" in e for e in res_sha.errors))

        for flag in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "cross_model_flash_authorized",
            "fx3_sli_key_lock_present",
            "fx6_lcd_hold_switch_present",
            "fx3_focus_ring_rotate_present",
            "fx3_protect_cancel_all_images_present",
            "fx3_focus_frame_dormant_colors_present",
            "fx6_zebra_dual_simultaneous_supported",
            "fx3_saveload_pro_camera_present",
        ):
            d_flag = copy.deepcopy(rep.to_dict())
            d_flag[flag] = True
            d_flag["report_sha256"] = _canonical_sha256_dict(d_flag)
            res_flag = verify_phase354_report(d_flag)
            self.assertFalse(res_flag.valid, msg=f"{flag}=True must fail verification")

    def test_065_verify_phase354_report_catches_nonzero_telemetry(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        for field in (
            "emmc_write_count",
            "e_nd_actuator_tx_count",
            "rf_packets_transmitted",
            "slot1_data_sector_writes",
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
        ):
            d = copy.deepcopy(rep.to_dict())
            d[field] = 1
            d["report_sha256"] = _canonical_sha256_dict(d)
            self.assertFalse(verify_phase354_report(d).valid)

    def test_066_render_phase354_markdown_contains_all_anchors(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase354_markdown(rep)
        self.assertIn("Phase 354", md)
        self.assertIn(P354_SCHEMA, md)
        self.assertIn("4/4", md)
        self.assertIn("16/16", md)
        self.assertIn(rep.report_sha256, md)
        self.assertIn(P354_CHECK_GROUP_A_ID, md)
        self.assertIn(P354_CHECK_GROUP_B_ID, md)
        self.assertIn(P354_CHECK_GROUP_C_ID, md)
        self.assertIn(P354_CHECK_GROUP_D_ID, md)

    def test_067_cli_help_returns_zero(self) -> None:
        cp = _run_cli_subprocess(["--help"])
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("--lock-op-parts", cp.stdout)
        self.assertIn("--shockless-wb", cp.stdout)
        self.assertIn("--fx6-zebra-setting", cp.stdout)
        self.assertIn("--saveload-slot", cp.stdout)

    def test_068_cli_default_offline_returns_rc2_awaiting_receipts(self) -> None:
        cp = _run_cli_subprocess(["--force-clean-room", "--summary"])
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        self.assertIn("OVERALL=READY_OFFLINE_AWAITING_BENCH_RECEIPTS", cp.stdout)
        self.assertIn("ready_attach=False", cp.stdout)

    def test_069_cli_simulate_bench_dry_run_and_force_clean_room_rc0(self) -> None:
        cp_dry = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(cp_dry.returncode, 0, msg=cp_dry.stderr)
        payload = json.loads(cp_dry.stdout)
        self.assertEqual(payload["schema_version"], P354_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(payload["check_groups_passed"], 4)
        self.assertEqual(payload["h0_equals_h3_count"], 16)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase354_report(payload).valid)

        cp_cr = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--summary"])
        self.assertEqual(cp_cr.returncode, 0, msg=cp_cr.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp_cr.stdout)

    def test_070_cli_output_and_markdown_out_artifacts_and_failure_rc2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_out = tmp_path / "p354.json"
            md_out = tmp_path / "p354.md"
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
            self.assertTrue(json_out.exists())
            self.assertTrue(md_out.exists())
            self.assertTrue(verify_phase354_report(json.loads(json_out.read_text(encoding="utf-8"))).valid)

            cp_fail = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--fx6-dual-zebra-both-requested",
                    "--summary",
                ]
            )
            self.assertEqual(cp_fail.returncode, 2, msg=cp_fail.stderr)
            self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp_fail.stdout)

    def test_071_cli_local_donor_mode_when_env_unset(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        payload = json.loads(cp.stdout)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertIn(
            payload["verification_mode"],
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )

    def test_072_cli_fx3_clean_room_test_env_1_mode(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--summary"],
            extra_env={"FX3_CLEAN_ROOM_TEST": "1"},
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp.stdout)

    def test_073_cli_saveload_save_on_slot1_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--saveload-action", "SAVE", "--summary"]
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp.stdout)

    def test_074_cli_recover_image_db_on_slot1_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--recover-image-db-requested", "--summary"]
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp.stdout)

    def test_075_cli_dormant_focus_ring_rotate_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--dormant-focus-ring-rotate-requested", "--summary"]
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp.stdout)

    def test_076_cli_dormant_slikey_lock_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--dormant-sli-key-lock-requested", "--summary"]
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp.stdout)

    def test_077_group_a_movie_awb_lock_custom_key_options(self) -> None:
        for k in P354_MOVIE_AWB_LOCK_CUSTOM_KEYS:
            self.assertTrue(
                evaluate_p354_check_group_a_lockop_menufn_and_wb(
                    movie_awb_lock_custom_key=k
                ).passed
            )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(
                movie_awb_lock_custom_key="SHUTTER_HALF"
            ).passed
        )

    def test_078_group_a_sq_mode_shockless_wb_active_and_shutter_awb_inactive(self) -> None:
        ga = evaluate_p354_check_group_a_lockop_menufn_and_wb(shoot_mode="S_AND_Q")
        self.assertTrue(ga.passed)
        self.assertTrue(ga.shockless_wb_active)
        self.assertFalse(ga.shutter_awb_lock_active)

    def test_079_group_b_delete_confirm_and_pressing_twice_invalid_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                delete_confirm="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                delete_pressing_twice="ALWAYS"
            ).passed
        )

    def test_080_group_b_apsc_initial_focus_mag_invalid_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                initial_focus_mag_still_apsc="X2_1"
            ).passed
        )

    def test_081_group_c_af_assist_inactive_in_mf_and_still(self) -> None:
        g_mf = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            shoot_mode="MOVIE", focus_mode="MF", af_assist="ON"
        )
        g_still = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            shoot_mode="PHOTO", focus_mode="AF_C", af_assist="ON"
        )
        self.assertTrue(g_mf.passed)
        self.assertTrue(g_still.passed)
        self.assertFalse(g_mf.af_assist_active)
        self.assertFalse(g_still.af_assist_active)

    def test_082_group_c_zebra_custom1_and_custom2_lower_limit_and_std_range_swap(self) -> None:
        gc = evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
            zebra_display="ON",
            zebra_level="CUSTOM2",
            zebra_custom1_type="LOWER_LIMIT",
            zebra_custom1_standard=85,
            zebra_custom2_type="STD_AND_RANGE",
            zebra_custom2_lower_limit=70,
        )
        self.assertTrue(gc.passed)

    def test_083_group_c_invalid_zebra_level_and_custom_types_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                zebra_level="50"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                zebra_custom1_type="DUAL"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                zebra_custom2_type="DUAL"
            ).passed
        )

    def test_084_group_d_marker_display_exact_15_ratios_content_check(self) -> None:
        expected = (
            "9:16",
            "4:5",
            "1:1",
            "4:3",
            "13:9",
            "14:9",
            "15:9",
            "16:9",
            "17:9",
            "1.66:1",
            "1.85:1",
            "1.91:1",
            "2:1",
            "2.35:1",
            "2.39:1",
        )
        self.assertEqual(P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS, expected)

    def test_085_group_d_memory_recall_slot_invalid_3_rejected(self) -> None:
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            simulate_bench_dry_run=True, memory_recall_media_slot=3
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_SAVELOAD_CAMSET_OR_CAMPR_CONTRACT)

    def test_086_group_d_load_readonly_v2_to_v7_allowed(self) -> None:
        for fw in ("2.00", "3.00", "4.00", "6.00", "7.02"):
            gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True,
                saveload_action="LOAD_READONLY",
                saveload_source_fw=fw,
            )
            self.assertTrue(gd.passed)

    def test_087_group_d_missing_receipt_files_fail_cleanly(self) -> None:
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_path=Path("/nonexistent/FX3RCPT1_A.bin"),
            receipt_b_path=Path("/nonexistent/FX3RCPT1_B.bin"),
        )
        self.assertFalse(gd.passed)
        self.assertFalse(gd.tier0_receipt_verified)
        self._assert_err(gd, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_088_group_d_short_receipt_length_fails(self) -> None:
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=b"FX3RCPT1" + b"\x00" * 16,
            receipt_b_bytes=b"FX3RCPT1" + b"\x00" * 16,
            st_dev_a_override=100,
            st_dev_b_override=200,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_089_group_d_simulated_h0_h3_drift_fails(self) -> None:
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=2
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_090_tier0_wrong_fw_or_model_id_fails(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        g_fw = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_fw="5.00",
        )
        g_mid = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_model_id=0x11112222,
        )
        self.assertFalse(g_fw.passed)
        self.assertFalse(g_mid.passed)
        self._assert_err(g_fw, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        self._assert_err(g_mid, P354_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_091_verify_phase354_report_rejects_bad_schema_and_help_guide(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["schema_version"] = "wrong"
        d["sony_help_guide_id"] = "ilc/0000"
        res = verify_phase354_report(d)
        self.assertFalse(res.valid)
        self.assertGreaterEqual(len(res.errors), 2)

    def test_092_verify_phase354_report_rejects_verified_with_less_than_4_groups(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["check_groups_passed"] = 3
        d["report_sha256"] = _canonical_sha256_dict(d)
        res = verify_phase354_report(d)
        self.assertFalse(res.valid)

    def test_093_verify_phase354_report_rejects_verified_with_unverified_tier0(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["tier0_receipt_verified"] = False
        d["report_sha256"] = _canonical_sha256_dict(d)
        res = verify_phase354_report(d)
        self.assertFalse(res.valid)

    def test_094_verify_phase354_report_rejects_verified_with_h0_h3_mismatch(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["h0_equals_h3_count"] = 15
        d["report_sha256"] = _canonical_sha256_dict(d)
        res = verify_phase354_report(d)
        self.assertFalse(res.valid)

    def test_095_verify_phase354_report_rejects_slot1_mutated(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["slot1_tier0_vault_mutated"] = True
        d["report_sha256"] = _canonical_sha256_dict(d)
        res = verify_phase354_report(d)
        self.assertFalse(res.valid)

    def test_096_slot1_tier0_vault_never_mutated_even_when_blocked(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            recover_image_db_requested=True,
            saveload_action="DELETE",
        )
        self.assertFalse(rep.slot1_tier0_vault_mutated)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_097_tier0_h0_a_b_mismatch_detected(self) -> None:
        sim = build_simulated_phase354_tier0_receipts()
        h0_b_bad = dict(sim["h0_baselines_b"])
        h0_b_bad[REQUIRED_H0_BASELINE_KEYS[1]] = "e" * 64
        gd = evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=h0_b_bad,
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P354_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_098_group_a_invalid_reset_shoot_log_af_area_reg_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(reset_action="FACTORY").passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(shoot_mode="AUTO").passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(log_shooting_mode="SLOG2").passed
        )
        self.assertFalse(
            evaluate_p354_check_group_a_lockop_menufn_and_wb(af_area_registration="MAYBE").passed
        )

    def test_099_group_b_invalid_on_off_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                auto_magnifier_in_mf="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                af_in_focus_mag="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_b_focus_assistant_and_media_db(
                fx6_af_assist="AUTO"
            ).passed
        )

    def test_100_group_c_invalid_on_off_and_circ_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                af_assist="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                circ_of_focus_point="DIAGONAL"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra(
                zebra_display="AUTO"
            ).passed
        )

    def test_101_group_d_invalid_marker_and_saveload_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, marker_display="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, center_marker="CROSS"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, guideframe="GRID"
            ).passed
        )
        self.assertFalse(
            evaluate_p354_check_group_d_marker_saveload_camset_and_tier0(
                simulate_bench_dry_run=True, saveload_action="FORMAT"
            ).passed
        )

    def test_102_cli_exposed_comma_separated_lists_parsed(self) -> None:
        cp_ok = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--exposed-focus-assistant-items",
                ",".join(P354_FOCUS_ASSISTANT_EXACT_FOUR_ITEMS),
                "--exposed-delete-modes",
                ",".join(P354_DELETE_EXACT_FIVE_MODES),
                "--exposed-protect-modes",
                ",".join(P354_PROTECT_EXACT_SEVEN_MODES),
                "--exposed-aspect-marker-ratios",
                ",".join(P354_FX3_ASPECT_MARKER_EXACT_15_RATIOS),
                "--summary",
            ]
        )
        self.assertEqual(cp_ok.returncode, 0, msg=cp_ok.stderr)

        cp_bad = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--exposed-aspect-marker-ratios",
                "16:9,4:3",
                "--summary",
            ]
        )
        self.assertEqual(cp_bad.returncode, 2)
        self.assertIn(f"OVERALL={P354_GO_NO_GO_BLOCKED_LOCKOP_SHOCKLESSWB_FOCUSMAG_AFSPEED_ZEBRA_CUSTOM_AND_SAVELOAD_CAMSET_FAILURE}", cp_bad.stdout)

    def test_103_cli_summary_shows_all_key_metrics(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--lock-op-parts",
                "ALL",
                "--shockless-wb",
                "2",
                "--af-transition-speed",
                "7",
                "--fx6-zebra-setting",
                "ZEBRA1",
                "--summary",
            ]
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        for tok in (
            "check_groups=4/4",
            "h0_eq_h3=16/16",
            "lock_op=ALL",
            "shockless_wb=2",
            "focus_ring_rot_impls=0",
            "af_speed=7",
            "fx6_zebra=ZEBRA1",
            "ratios=15",
            "saveload_slot=1",
            "leaked_bytes=0",
        ):
            self.assertIn(tok, cp.stdout)

    def test_104_cli_model_id_hex_and_serial_cid_flags(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--model-id",
                "0x91030080",
                "--body-fw",
                "7.02",
                "--body-serial",
                "FX3CLI7020354",
                "--emmc-cid",
                "11010030303847333000a1b2c3d49354",
                "--json",
            ]
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        payload = json.loads(cp.stdout)
        self.assertEqual(payload["check_group_d"]["receipt_body_serial"], "FX3CLI7020354")

    def test_105_cli_zero_pyc_under_worktree(self) -> None:
        cp = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--summary"])
        self.assertEqual(cp.returncode, 0)
        pyc_hits = list((REPO_ROOT / "outputs/fx6-on-fx3-closure").rglob("*.pyc"))
        self.assertEqual(pyc_hits, [])

    def test_106_donor_inspection_work_root_none_returns_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            with mock.patch(
                "fx6_closure.realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                insp = inspect_phase354_donors_bounded()
                self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(insp.donors_present, 0)
                self.assertEqual(insp.raw_firmware_bytes_leaked, 0)

    def test_107_fx6_atw_speed_and_shutter_awb_lock_summary_fields(self) -> None:
        rep = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            shoot_mode="PHOTO",
            shutter_awb_lock="SHUTTER_HALF_PRESS",
            fx6_atw_speed=1,
        )
        self.assertTrue(rep.check_group_a.passed)
        self.assertEqual(rep.check_group_a.fx6_atw_speed, 1)
        self.assertEqual(rep.check_group_a.shutter_awb_lock, "SHUTTER_HALF_PRESS")

    def test_108_render_markdown_includes_errors_and_warnings_when_present(self) -> None:
        rep_wait = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True
        )
        md_wait = render_phase354_markdown(rep_wait)
        self.assertIn("## Warnings", md_wait)

        rep_err = run_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            claimed_fx6_supports_dual_simultaneous_zebra=True,
        )
        md_err = render_phase354_markdown(rep_err)
        self.assertIn("## Errors", md_err)


if __name__ == "__main__":
    unittest.main()
