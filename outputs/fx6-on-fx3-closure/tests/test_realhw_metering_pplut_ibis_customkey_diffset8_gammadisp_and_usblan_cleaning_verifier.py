"""Four-mode unit tests (108 cases) for Phase 358 (`preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning`):
22nd Physical Bench Readiness Verifier across Global Sony Waves 75-76 check groups (`A..D`):
- Group A (Wave 75): `[Metering Mode]` 6 modes (`Multi` locked under CIZ/Digital Zoom), `[Face Priority in Multi Metering]` (`BKID_APP_setting_face_detection_in_multi`), `[Spot Metering Point]`, Still-only Reset-resistant `[AEL w/ Shutter]`, and `[Exposure step]` (`0.3EV`/`0.5EV`) Reset-resistant erratum (`Not available` under `[Camera Settings Reset]`, `[Initialize]`-only, `[Shutter Angle]` immune — Wave 75 G96 correction) vs `ILME-FX6` `Auto Exposure > Level -3.0..+3.0` (`0.25` step, 25 steps, disproving `-2.0..+2.0EV` rumor) + `Speed -99..+99` + `Detect Window 1..6/Custom`; `[Picture Profile]` `PP1..11` dual Reset/Initialize immunity vs `PPLUT1..4` Reset (`1080p` internal-rec HDMI), `[Manage User LUTs]` `User1..16` (`17/33-pt` `.cube` `<= 63 B` in `/Private/Sony/PRO/LUT` SD vs `/Sony/PRO/LUT` CFexpress-A), & MP4 `[Embed LUT File]` (`0` MXF, `0` sidecar `.cube`, SD/SDHC locked `Off`) vs FX6 `User1..16` (50-slot buffer) & 4-way `MLUT`.
- Group B (Wave 75): 5-axis IBIS `[SteadyShot]` (`Active ~1.1x`/`Standard`/`Off`, locked out at `120p`, `RAW=On`, `De-Squeeze!=Off`; Catalyst Gyro requires `Off` or `Active` & excludes `120p`/`S&Q`), exact 47-entry manual focal length table (`8mm..1000mm`), dormant `Dynamic/Intelligent/Super Active` (`EOPNOTSUPP=95`) vs FX6 zero physical IBIS (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`); Playback 5 zero-write Reset-resistant items (`display_rotatiton` typo); Movie `17-char` `Cam ID + Reel#` stem (`C999->D001` rollover) vs `37-char` `[Title Name Settings]` (`4..46` `Title Prefix` MXF on FX6) & Tier-0 `Slot 1` `EROFS=30` firewall.
- Group C (Wave 76): `XLR-H1` handle has `0` assignable custom buttons / `0` handle REC / `0` handle dials; 3 FX3 custom domains (Still `16`, Movie `16` factory defaults, Playback `7` skipping `C4=Delete` & adding `Fn Button`), dormant Alpha symbols (`EOPNOTSUPP=95`); `[Different Set for Still/Mv]` exact 8 items (`Common->Separate` Custom WB Still-only; `Separate->Common` preserves Still `Av`/`Tv`/`Custom WB`; `[Picture Profile]` checkbox survives BOTH Reset & Initialize!); `[Gamma Display Assist]` (dormant `S-Log2`, `0 px` HDMI/TV, hard-locked `Off` when `[Log Shooting]!=Off` handing off to `[Display LUT]` + `[Select LUT]`) vs FX6 zero UI `Gamma Display Assist` & 4-way `MLUT`.
- Group D + Tier-0 (Wave 76): `USB-LAN` (`libWiredLanResource.so` / `dhcpcd`, mutually exclusive with Multi/Micro USB & Wi-Fi, NOT blocked by `[Airplane Mode]=On`), `[Access Authen. Settings]=On` (`SSH + PTP-IP`), Ver. 7.00+ disabled `[Security(IPsec)]` (`0` FX6 IPsec UI bindings), `[Airplane Mode]=On` preserved across `[Reset Network Set.]` & reset to `Off` ONLY by `[Initialize]`; `[Sensor Cleaning]` `>=51%` battery gate + physical power-switch OFF vs dormant `[Anti-dust Function]`/`[Shutter When Pwr OFF]` (`0` UI items), front `#5` `[IR Remote Ctrl]`, Still-only `[Auto Review]` vs FX6 `APR` / `2.5mm LANC` / `Rec Review`; plus `528 B FX3RCPT1` dual-media receipt gate & `16/16 H0 == H3` immutability.

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
)
from fx6_closure.realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier import (  # noqa: E402
    P358_ACCESS_AUTHEN_DEFAULT,
    P358_ACCESS_AUTHEN_PASS_MAX_CHARS,
    P358_ACCESS_AUTHEN_PASS_MIN_CHARS,
    P358_ACCESS_AUTHEN_PROTOCOLS,
    P358_ACCESS_AUTHEN_USER_MAX_CHARS,
    P358_AEL_W_SHUTTER_DEFAULT,
    P358_AEL_W_SHUTTER_MODES,
    P358_AUTO_REVIEW_DEFAULT,
    P358_AUTO_REVIEW_MODES,
    P358_BOUNDED_DONOR_PATHS,
    P358_CHECK_GROUP_A_ID,
    P358_CHECK_GROUP_B_ID,
    P358_CHECK_GROUP_C_ID,
    P358_CHECK_GROUP_D_ID,
    P358_DIFF_SET_EXACT_8_ITEMS,
    P358_DISPLAY_ROTATION_BKID_TYPO,
    P358_DISPLAY_ROTATION_DEFAULT,
    P358_DISPLAY_ROTATION_OPTIONS,
    P358_DORMANT_CUSTOM_KEY_SYMBOLS,
    P358_DORMANT_STEADYSHOT_MODES,
    P358_EMBED_LUT_CONTAINER,
    P358_EMBED_LUT_FILE_MENU_PATH,
    P358_ERRNO_EOPNOTSUPP,
    P358_ERRNO_EROFS,
    P358_EXPOSURE_STEP_AFFECTS_SHUTTER_ANGLE,
    P358_EXPOSURE_STEP_DEFAULT,
    P358_EXPOSURE_STEP_MODES,
    P358_EXPOSURE_STEP_RESISTS_CAMERA_RESET,
    P358_FACE_PRIORITY_MULTI_BKID,
    P358_FILE_NAME_FORMAT_DEFAULT,
    P358_FILE_NAME_FORMATS,
    P358_FOCUS_AREAS_FORCING_SPOT_CENTER,
    P358_FX3_ANTI_DUST_UI_COUNT,
    P358_FX3_GAMMA_ASSIST_SLOG2_EXPOSED,
    P358_FX3_MXF_SUPPORTED,
    P358_FX3_SHUTTER_WHEN_PWR_OFF_UI_COUNT,
    P358_FX3_SIDECAR_CUBE_EMITTED,
    P358_FX6_AE_LEVEL_MAX,
    P358_FX6_AE_LEVEL_MIN,
    P358_FX6_AE_LEVEL_STEP,
    P358_FX6_AE_LEVEL_STEP_COUNT,
    P358_FX6_AE_MODES,
    P358_FX6_AE_SPEED_MAX,
    P358_FX6_AE_SPEED_MIN,
    P358_FX6_ASSIGNABLE_BUTTON_LABELS,
    P358_FX6_BODY_IBIS_COUNT,
    P358_FX6_BODY_IBIS_ULTRASONIC_CLEANING,
    P358_FX6_CLIP_PATH_TEMPLATE,
    P358_FX6_DETECT_WINDOW_MODES,
    P358_FX6_GAMMA_DISP_ASSIST_UI_COUNT,
    P358_FX6_IBIS_UNSUPPORTED_SYMBOL,
    P358_FX6_IPSEC_UI_BINDING_COUNT,
    P358_FX6_IR_REMOTE_UI_COUNT,
    P358_FX6_MLUT_CHANNELS,
    P358_FX6_STILL_AUTO_REVIEW_UI_COUNT,
    P358_FX6_STILL_MOVIE_SPLIT_SUPPORTED,
    P358_FX6_TITLE_PREFIX_MAX_CHARS,
    P358_FX6_TITLE_PREFIX_MIN_CHARS,
    P358_FX6_USER_LUT_INTERNAL_BUFFER_SLOTS,
    P358_FX6_USER_LUT_UI_SLOTS,
    P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE,
    P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW,
    P358_GA_ERR_METERING_OR_AEL_CONTRACT,
    P358_GA_ERR_MODEL_OR_FW_FLOOR,
    P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT,
    P358_GAMMA_DISP_ASSIST_HDMI_PIXEL_COUNT,
    P358_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
    P358_GAMMA_DISP_ASSIST_TYPES,
    P358_GB_ERR_DORMANT_STEADYSHOT_EOPNOTSUPP,
    P358_GB_ERR_FX6_ZERO_IBIS_CONTRACT,
    P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE,
    P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT,
    P358_GB_ERR_SLOT1_FILE_FOLDER_EROFS30,
    P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY,
    P358_GC_ERR_DORMANT_CUSTOM_KEY_EOPNOTSUPP,
    P358_GC_ERR_FX6_ASSIGNABLE_OR_4WAY_MLUT,
    P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF,
    P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS,
    P358_GD_ERR_AIRPLANE_RESET_SPLIT,
    P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P358_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6,
    P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST,
    P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED,
    P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE,
    P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED,
    P358_HEADER_READ_BYTES,
    P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    P358_IMAGE_INDEX_DEFAULT,
    P358_IMAGE_INDEX_OPTIONS,
    P358_IPSEC_MIN_DISABLED_FW_MAJOR,
    P358_METERING_MODE_DEFAULT,
    P358_METERING_MODES,
    P358_MOVIE_CAMID_REEL_STEM_LEN,
    P358_MOVIE_CUSTOM_CONTROL_COUNT,
    P358_MOVIE_CUSTOM_FACTORY_DEFAULTS,
    P358_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P358_PICTURE_PROFILE_DEFAULT,
    P358_PICTURE_PROFILE_OPTIONS,
    P358_PLAY_SPEED_DEFAULT,
    P358_PLAY_SPEED_MAX,
    P358_PLAY_SPEED_MIN,
    P358_PLAYBACK_5_READONLY_ITEMS,
    P358_PLAYBACK_CUSTOM_CONTROL_COUNT,
    P358_PLAYBACK_CUSTOM_CONTROLS,
    P358_PP_BASE_PROFILES,
    P358_PPLUT_FORCED_INTERNAL_REC_HDMI_RESOLUTION,
    P358_PPLUT_PROFILES,
    P358_SCHEMA,
    P358_SELECT_LUT_DEFAULT,
    P358_SELECT_LUT_OPTIONS,
    P358_SENSOR_CLEANING_MIN_BATTERY_PCT,
    P358_SONY_HELP_GUIDE_ID,
    P358_SPOT_METERING_POINT_DEFAULT,
    P358_SPOT_METERING_POINT_MODES,
    P358_STEADYSHOT_ACTIVE_CROP_FACTOR,
    P358_STEADYSHOT_ADJUST_DEFAULT,
    P358_STEADYSHOT_ADJUST_MODES,
    P358_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
    P358_STEADYSHOT_MOVIE_DEFAULT,
    P358_STEADYSHOT_MOVIE_MODES,
    P358_STEADYSHOT_STILL_DEFAULT,
    P358_STEADYSHOT_STILL_MODES,
    P358_STILL_CUSTOM_CONTROL_COUNT,
    P358_STILL_CUSTOM_CONTROLS,
    P358_STORAGE_SURFACE_COUNT,
    P358_TITLE_NAME_DEFAULT,
    P358_TITLE_NAME_MAX_CHARS,
    P358_USB_LAN_IP_MODES,
    P358_USB_LAN_KERNEL_MODULES,
    P358_USB_LAN_LIBS,
    P358_USB_LAN_MANUAL_FIELD_MAX_CHARS,
    P358_USER_LUT_CFEA_DIR,
    P358_USER_LUT_CUBE_POINTS,
    P358_USER_LUT_MAX_FILENAME_BYTES,
    P358_USER_LUT_SD_DIR,
    P358_USER_LUT_SLOT_MAX,
    P358_VERSION,
    P358_XLR_H1_ASSIGNABLE_BUTTON_COUNT,
    P358_XLR_H1_DIAL_COUNT,
    P358_XLR_H1_REC_BUTTON_COUNT,
    PHASE358_EMMC_WRITE_COUNT,
    PHASE358_E_ND_ACTUATOR_TX_COUNT,
    PHASE358_PASSIVE_TX_BYTES_EMITTED,
    PHASE358_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE358_SLOT1_DATA_SECTOR_WRITES,
    PHASE358_USB_PACKETS_TRANSMITTED,
    PHASE358_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_358_CHECK_GROUP_IDS,
    PHASE_358_SCHEMA,
    PHASE_358_VERSION,
    REALHW_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_USBLAN_CLEANING_SCHEMA,
    _canonical_sha256_dict,
    build_simulated_phase358_tier0_receipts,
    evaluate_p358_check_group_a_metering_expstep_pp_and_userlut,
    evaluate_p358_check_group_b_ibis_playback_and_file_slot1,
    evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp,
    evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0,
    evaluate_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight,
    inspect_phase358_donors_bounded,
    render_phase358_markdown,
    resolve_phase358_donor_file_or_none,
    run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight,
    verify_phase358_report,
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
            "preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestPhase358MeteringPpLutIbisCustomKeyDiffSet8GammaDispUsbLanCleaningVerifier(
    unittest.TestCase
):
    def _assert_err(self, res: object, code: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(any(code in e for e in errs), msg=f"Missing {code} in {errs}")

    def _assert_err_contains(self, res: object, sub: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(any(sub in e for e in errs), msg=f"Missing {sub!r} in {errs}")

    # ------------------------------------------------------------------
    # 01-12: Package Exports, 4-Mode Bounded Donor Inspection, Determinism
    # ------------------------------------------------------------------

    def test_001_package_all_exports_and_no_shadowing(self) -> None:
        self.assertEqual(P358_SCHEMA, PHASE_358_SCHEMA)
        self.assertEqual(
            P358_SCHEMA,
            REALHW_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_USBLAN_CLEANING_SCHEMA,
        )
        self.assertEqual(P358_VERSION, PHASE_358_VERSION)
        self.assertEqual(P358_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(P358_STORAGE_SURFACE_COUNT, 16)
        self.assertEqual(len(PHASE_358_CHECK_GROUP_IDS), 4)
        for sym in (
            "P358_SCHEMA",
            "PHASE_358_SCHEMA",
            "REALHW_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_USBLAN_CLEANING_SCHEMA",
            "build_simulated_phase358_tier0_receipts",
            "evaluate_p358_check_group_a_metering_expstep_pp_and_userlut",
            "evaluate_p358_check_group_b_ibis_playback_and_file_slot1",
            "evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp",
            "evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0",
            "evaluate_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight",
            "run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight",
            "verify_phase358_report",
            "render_phase358_markdown",
            # Verify Phase 354 & Milestone 349 exports were NOT shadowed
            "P354_SCHEMA",
            "verify_phase354_report",
            "REALHW_MILESTONE349_SCHEMA",
            "evaluate_realhw_milestone349_master_gate",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_002_locked_zero_telemetry_constants(self) -> None:
        self.assertEqual(PHASE358_EMMC_WRITE_COUNT, 0)
        self.assertEqual(PHASE358_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(PHASE358_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE358_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE358_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE358_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE358_RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_003_bounded_donor_paths_count_and_64b_cap(self) -> None:
        self.assertEqual(len(P358_BOUNDED_DONOR_PATHS), 8)
        self.assertEqual(P358_HEADER_READ_BYTES, 64)

    def test_004_mode1_local_donor_o_rdonly_when_donors_present(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            insp = inspect_phase358_donors_bounded()
            self.assertEqual(insp.raw_firmware_bytes_leaked, 0)
            self.assertLessEqual(insp.bytes_read_total, 8 * P358_HEADER_READ_BYTES)
            if insp.donor_tree_present:
                self.assertEqual(insp.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertGreater(insp.donors_present, 0)
            else:
                self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_005_mode2_fx3_clean_room_test_env_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            insp = inspect_phase358_donors_bounded()
            self.assertEqual(insp.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(insp.donor_tree_present)
            self.assertEqual(insp.bytes_read_total, 0)
            self.assertEqual(insp.raw_firmware_bytes_leaked, 0)

    def test_006_mode3_fx3_fx6_force_clean_room_env_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
                simulate_bench_dry_run=True
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_007_mode4_mocked_work_root_none_and_nonexistent_ci_path(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            self.assertIsNone(resolve_phase358_donor_file_or_none(None, "foo"))
            with mock.patch(
                "fx6_closure.realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                insp_none = inspect_phase358_donors_bounded(work_root=None)
                self.assertEqual(insp_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertFalse(insp_none.donor_tree_present)
                self.assertEqual(insp_none.bytes_read_total, 0)

            insp_missing = inspect_phase358_donors_bounded(
                work_root=Path("/nonexistent/phase358/donor/root")
            )
            self.assertEqual(insp_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(insp_missing.donors_present, 0)
            self.assertEqual(insp_missing.bytes_read_total, 0)

    def test_008_donor_override_dirs_allow_bounded_o_rdonly_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fx6_dir = tmp_path / "fx6"
            fx3_dir = tmp_path / "fx3"
            fx6_dir.mkdir()
            fx3_dir.mkdir()
            (fx6_dir / "appFw.so").write_bytes(b"\x7fELF" + b"6" * 120)
            (fx3_dir / "appFw.so").write_bytes(b"\x7fELF" + b"3" * 120)
            (fx3_dir / "libWiredLanResource.so").write_bytes(b"\x7fELF" + b"w" * 120)
            (fx3_dir / "libNetServiceEther.so").write_bytes(b"\x7fELF" + b"n" * 120)
            (fx3_dir / "libInfraAirplaneMode.so").write_bytes(b"\x7fELF" + b"a" * 120)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FX3_CLEAN_ROOM_TEST", None)
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
                insp = inspect_phase358_donors_bounded(
                    force_clean_room=False,
                    work_root=Path("/nonexistent/phase358"),
                    fx6_lib_dir=fx6_dir,
                    fx3_modules_dir=fx3_dir,
                )
                self.assertEqual(insp.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(insp.donor_tree_present)
                self.assertEqual(insp.donors_present, 5)
                self.assertEqual(insp.bytes_read_total, 5 * P358_HEADER_READ_BYTES)
                self.assertEqual(insp.raw_firmware_bytes_leaked, 0)

    def test_009_default_offline_awaiting_receipts_never_authorizes_attach(self) -> None:
        rep = evaluate_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.overall_status, P358_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)

    def test_010_simulated_bench_dry_run_passes_4_of_4_and_16_of_16_attach_false(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase358_report(rep).valid)

    def test_011_deterministic_json_strips_elapsed_seconds_recursively(self) -> None:
        r1 = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        j1 = r1.to_deterministic_json()
        self.assertEqual(j1, r2.to_deterministic_json())
        self.assertNotIn("elapsed_seconds", j1)

    def test_012_canonical_sha256_ignores_nested_timing_fields(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["donor_inspection"]["elapsed_seconds"] = 999.123
        d["extra_elapsed_ms"] = 42
        self.assertEqual(_canonical_sha256_dict(d), rep.report_sha256)

    # ------------------------------------------------------------------
    # 13-38: Check Group A — Wave 75 Metering, ExpStep Erratum, PP/PPLUT/LUT
    # ------------------------------------------------------------------

    def test_013_group_a_model_fw_and_help_guide_floor(self) -> None:
        self.assertTrue(evaluate_p358_check_group_a_metering_expstep_pp_and_userlut().passed)
        for kw in (
            {"body_fw": "6.01"},
            {"body_model_id": 0x12345678},
            {"sony_help_guide_id": "ilc/9999"},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_014_group_a_metering_mode_exact_6_modes_and_reset(self) -> None:
        self.assertEqual(
            P358_METERING_MODES,
            ("MULTI", "CENTER", "SPOT_STANDARD", "SPOT_LARGE", "ENTIRE_SCREEN_AVG", "HIGHLIGHT"),
        )
        for m in P358_METERING_MODES:
            ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(metering_mode=m)
            self.assertTrue(ga.passed)
            self.assertEqual(ga.effective_metering_mode, m)

        ga_reset = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            metering_mode="HIGHLIGHT", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ga_reset.passed)
        self.assertEqual(ga_reset.effective_metering_mode, "MULTI")

        ga_bad = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(metering_mode="SPOT")
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P358_GA_ERR_METERING_OR_AEL_CONTRACT)

    def test_015_group_a_ciz_or_digital_zoom_locks_metering_to_multi(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            metering_mode="SPOT_STANDARD", ciz_or_digital_zoom_active=True
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_metering_mode, "MULTI")
        self.assertEqual(ga.effective_face_priority_in_multi, "OFF")

        ga_bad = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            ciz_or_digital_zoom_active=True,
            expect_metering_not_locked_to_multi_under_zoom=True,
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P358_GA_ERR_METERING_OR_AEL_CONTRACT)

    def test_016_group_a_face_priority_multi_bkid_and_desqueeze_lockout(self) -> None:
        self.assertEqual(P358_FACE_PRIORITY_MULTI_BKID, "BKID_APP_setting_face_detection_in_multi")
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            face_priority_in_multi_metering="ON", desqueeze_display="1.33X"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_face_priority_in_multi, "OFF")
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                face_priority_in_multi_metering="AUTO"
            ).passed
        )

    def test_017_group_a_spot_metering_point_focus_area_coupling(self) -> None:
        self.assertEqual(P358_SPOT_METERING_POINT_MODES, ("CENTER", "FOCUS_POINT_LINK"))
        self.assertEqual(P358_FOCUS_AREAS_FORCING_SPOT_CENTER, ("WIDE", "ZONE", "CENTER_FIX"))
        ga_spot = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            spot_metering_point="FOCUS_POINT_LINK", focus_area="SPOT_M"
        )
        self.assertTrue(ga_spot.passed)
        self.assertEqual(ga_spot.effective_spot_metering_point, "FOCUS_POINT_LINK")

        for fa in P358_FOCUS_AREAS_FORCING_SPOT_CENTER:
            ga_fb = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                spot_metering_point="FOCUS_POINT_LINK", focus_area=fa
            )
            self.assertTrue(ga_fb.passed)
            self.assertEqual(ga_fb.effective_spot_metering_point, "CENTER")
            ga_err = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                focus_area=fa, expect_spot_point_links_on_wide_zone_or_center_fix=True
            )
            self.assertFalse(ga_err.passed)
            self._assert_err(ga_err, P358_GA_ERR_METERING_OR_AEL_CONTRACT)

    def test_018_group_a_ael_w_shutter_still_only_and_reset_immune(self) -> None:
        self.assertEqual(P358_AEL_W_SHUTTER_MODES, ("AUTO", "ON", "OFF"))
        ga_still = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            shoot_mode="PHOTO", ael_w_shutter="ON", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ga_still.passed)
        self.assertTrue(ga_still.ael_w_shutter_effective)
        self.assertTrue(ga_still.ael_w_shutter_reset_immune)

        ga_movie = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            shoot_mode="MOVIE", ael_w_shutter="ON"
        )
        self.assertTrue(ga_movie.passed)
        self.assertFalse(ga_movie.ael_w_shutter_effective)

        for kw in (
            {"expect_ael_w_shutter_active_in_movie": True},
            {"claimed_ael_w_shutter_wiped_by_camera_reset": True},
            {"ael_w_shutter": "INVALID"},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_METERING_OR_AEL_CONTRACT)

    def test_019_group_a_exposure_step_reset_resistant_erratum_and_shutter_angle_immune(self) -> None:
        self.assertEqual(P358_EXPOSURE_STEP_MODES, ("0.3EV", "0.5EV"))
        self.assertTrue(P358_EXPOSURE_STEP_RESISTS_CAMERA_RESET)
        self.assertFalse(P358_EXPOSURE_STEP_AFFECTS_SHUTTER_ANGLE)

        ga_cam = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            exposure_step="0.5EV", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ga_cam.passed)
        self.assertEqual(ga_cam.effective_exposure_step_after_reset, "0.5EV")

        ga_init = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            exposure_step="0.5EV", reset_action="INITIALIZE"
        )
        self.assertTrue(ga_init.passed)
        self.assertEqual(ga_init.effective_exposure_step_after_reset, "0.3EV")

        for kw in (
            {"claimed_exposure_step_wiped_by_camera_reset": True},
            {"expect_exposure_step_alters_shutter_angle": True},
            {"log_shooting_mode": "CINE_EI", "expect_mm_meter_changes_with_ei_in_cine_ei": True},
            {"exposure_step": "0.25EV"},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE)

    def test_020_group_a_fx6_ae_level_minus3_to_plus3_in_025_steps_disproves_2ev_rumor(self) -> None:
        self.assertEqual(P358_FX6_AE_LEVEL_MIN, -3.0)
        self.assertEqual(P358_FX6_AE_LEVEL_MAX, 3.0)
        self.assertEqual(P358_FX6_AE_LEVEL_STEP, 0.25)
        self.assertEqual(P358_FX6_AE_LEVEL_STEP_COUNT, 25)
        self.assertEqual(P358_FX6_AE_MODES, ("BACKLIGHT", "STANDARD", "SPOTLIGHT"))
        self.assertEqual(P358_FX6_DETECT_WINDOW_MODES, ("1", "2", "3", "4", "5", "6", "CUSTOM"))

        for i in range(25):
            lvl = -3.0 + i * 0.25
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(fx6_ae_level=lvl).passed
            )

        for kw in (
            {"fx6_ae_level": -3.25},
            {"fx6_ae_level": 3.25},
            {"fx6_ae_level": 0.1},
            {"fx6_ae_speed": -100},
            {"fx6_ae_speed": 100},
            {"fx6_ae_mode": "SPOT"},
            {"fx6_detect_window": "7"},
            {"fx6_detect_window_width": 39},
            {"fx6_detect_window_width": 1000},
            {"claimed_fx6_ae_level_limited_to_2ev": True},
            {"claimed_fx6_has_still_spot_or_ael_shutter": True},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW)

    def test_021_group_a_pp1_to_pp11_vs_pplut1_to_pplut4_reset_and_still_rules(self) -> None:
        self.assertEqual(len(P358_PP_BASE_PROFILES), 11)
        self.assertEqual(len(P358_PPLUT_PROFILES), 4)
        self.assertEqual(P358_PICTURE_PROFILE_DEFAULT, "PP11")
        ga_pplut = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            shoot_mode="MOVIE", picture_profile="PPLUT1", internal_rec_active=True
        )
        self.assertTrue(ga_pplut.passed)
        self.assertEqual(ga_pplut.pplut_forced_hdmi_resolution, "1080P")

        ga_hdmi_only = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            shoot_mode="MOVIE", picture_profile="PPLUT2", hdmi_only_output=True
        )
        self.assertTrue(ga_hdmi_only.passed)
        self.assertIsNone(ga_hdmi_only.pplut_forced_hdmi_resolution)

        for kw in (
            {"shoot_mode": "PHOTO", "picture_profile": "PPLUT1"},
            {"claimed_pplut_active_in_still": True},
            {"claimed_pp1_to_pp11_wiped_by_reset_or_init": True},
            {"claimed_pplut_resists_reset_or_init": True},
            {"picture_profile": "PPLUT3", "expect_4k_hdmi_with_pplut_internal_rec": True},
            {"log_shooting_mode": "CINE_EI", "claimed_pp_active_with_log_shooting_on": True},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT)

    def test_022_group_a_user_lut_dirs_cube_points_63b_and_mp4_embed_lut(self) -> None:
        self.assertEqual(P358_USER_LUT_SD_DIR, "/Private/Sony/PRO/LUT")
        self.assertEqual(P358_USER_LUT_CFEA_DIR, "/Sony/PRO/LUT")
        self.assertEqual(P358_EMBED_LUT_CONTAINER, "MP4")
        self.assertFalse(P358_FX3_MXF_SUPPORTED)
        self.assertFalse(P358_FX3_SIDECAR_CUBE_EMITTED)
        self.assertEqual(P358_FX6_USER_LUT_UI_SLOTS, 16)
        self.assertEqual(P358_FX6_USER_LUT_INTERNAL_BUFFER_SLOTS, 50)
        self.assertEqual(len(P358_FX6_MLUT_CHANNELS), 4)

        ga_sd = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            media_type="SDHC", embed_lut_file="ON"
        )
        self.assertTrue(ga_sd.passed)
        self.assertEqual(ga_sd.user_lut_dir, "/Private/Sony/PRO/LUT")
        self.assertEqual(ga_sd.effective_embed_lut_file, "OFF")

        ga_63 = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            user_lut_cube_points=17, user_lut_filename=("a" * 58) + ".cube"
        )
        self.assertTrue(ga_63.passed)
        self.assertEqual(ga_63.user_lut_filename_bytes, 63)

        for kw in (
            {"user_lut_slot_count": 17},
            {"user_lut_cube_points": 65},
            {"user_lut_filename": ("a" * 59) + ".cube"},
            {"user_lut_filename": "bad.3dl"},
            {"claimed_user_lut_wiped_by_camera_reset": True},
            {"media_type": "SDHC", "expect_embed_lut_enabled_on_sdhc": True},
            {"claimed_fx3_supports_mxf_or_sidecar_cube_embed": True},
            {"claimed_embed_lut_under_color_tone": True},
            {"claimed_fx6_user_lut_pool_not_50": True},
            {"select_lut": "SLOG2"},
        ):
            g = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT)

    def test_023_group_a_invalid_enum_inputs_rejected(self) -> None:
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(shoot_mode="AUTO").passed
        )
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(log_shooting_mode="SLOG2").passed
        )
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(reset_action="FACTORY").passed
        )
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(desqueeze_display="1.5X").passed
        )
        self.assertFalse(
            evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(media_type="NVME").passed
        )

    def test_024_group_a_log_shooting_forces_pp_off_when_not_reset(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            log_shooting_mode="FLEXIBLE_ISO", picture_profile="PP11"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_pp_index_after_reset, "OFF")

    def test_025_group_a_select_lut_all_19_options_valid(self) -> None:
        self.assertEqual(len(P358_SELECT_LUT_OPTIONS), 19)
        for opt in P358_SELECT_LUT_OPTIONS:
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(select_lut=opt).passed
            )

    def test_026_group_a_embed_lut_path_anchor(self) -> None:
        self.assertIn("[Log Shooting Setting]", P358_EMBED_LUT_FILE_MENU_PATH)
        self.assertNotIn("[Color/Tone]", P358_EMBED_LUT_FILE_MENU_PATH)

    # ------------------------------------------------------------------
    # 27-50: Check Group B — Wave 75 IBIS 47-Focal, PB 5 ReadOnly, File/Slot1
    # ------------------------------------------------------------------

    def test_027_group_b_steadyshot_modes_active_1_1x_and_resettable(self) -> None:
        self.assertEqual(P358_STEADYSHOT_MOVIE_MODES, ("ACTIVE", "STANDARD", "OFF"))
        self.assertEqual(P358_STEADYSHOT_ACTIVE_CROP_FACTOR, 1.1)
        self.assertEqual(P358_STEADYSHOT_STILL_MODES, ("ON", "OFF"))
        self.assertEqual(P358_STEADYSHOT_ADJUST_MODES, ("AUTO", "MANUAL"))

        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            steadyshot_movie="ACTIVE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_steadyshot_movie, "STANDARD")

        gb_bad = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            claimed_steadyshot_resists_camera_reset=True
        )
        self.assertFalse(gb_bad.passed)
        self._assert_err(gb_bad, P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE)

    def test_028_group_b_exact_47_entry_ibis_focal_table(self) -> None:
        self.assertEqual(len(P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM), 47)
        self.assertEqual(P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM[0], 8)
        self.assertEqual(P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM[-1], 1000)
        for mm in (8, 24, 35, 50, 85, 135, 200, 600, 1000):
            gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_adjust="MANUAL", steadyshot_focal_length_mm=mm
            )
            self.assertTrue(gb.passed)
            self.assertEqual(gb.focal_table_entry_count, 47)

        gb_bad_len = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            exposed_focal_lengths_mm=P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM[:-1]
        )
        gb_bad_val = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            steadyshot_focal_length_mm=22
        )
        self.assertFalse(gb_bad_len.passed)
        self.assertFalse(gb_bad_val.passed)
        self._assert_err(gb_bad_len, P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE)
        self._assert_err(gb_bad_val, P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE)

    def test_029_group_b_steadyshot_active_lockouts_120p_raw_desqueeze(self) -> None:
        for kw in (
            {"frame_rate_fps": 119.88},
            {"hdmi_raw_output": True},
            {"desqueeze_display": "1.65X"},
        ):
            gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_movie="ACTIVE", **kw
            )
            self.assertTrue(gb.passed)
            self.assertEqual(gb.effective_steadyshot_movie, "STANDARD")

            gb_fail = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_movie="ACTIVE", expect_steadyshot_active_under_lockout=True, **kw
            )
            self.assertFalse(gb_fail.passed)
            self._assert_err(gb_fail, P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE)

    def test_030_group_b_catalyst_gyro_metadata_matrix(self) -> None:
        for ss in ("OFF", "ACTIVE"):
            gb_ok = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                shoot_mode="MOVIE",
                steadyshot_movie=ss,
                frame_rate_fps=23.98,
                e_mount_sony_lens=True,
                expect_catalyst_gyro_available=True,
            )
            self.assertTrue(gb_ok.passed)
            self.assertTrue(gb_ok.catalyst_gyro_metadata_active)

        for bad_kw in (
            {"steadyshot_movie": "STANDARD"},
            {"frame_rate_fps": 119.88, "steadyshot_movie": "OFF"},
            {"shoot_mode": "S_AND_Q", "steadyshot_movie": "OFF"},
            {"e_mount_sony_lens": False, "steadyshot_movie": "OFF"},
        ):
            gb_bad = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                expect_catalyst_gyro_available=True, **bad_kw
            )
            self.assertFalse(gb_bad.passed)
            self._assert_err(gb_bad, P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE)

    def test_031_group_b_dormant_steadyshot_modes_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(
            P358_DORMANT_STEADYSHOT_MODES,
            ("DYNAMIC_ACTIVE", "INTELLIGENT_ACTIVE", "SUPER_ACTIVE"),
        )
        for mode in P358_DORMANT_STEADYSHOT_MODES:
            gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                dormant_steadyshot_mode_requested=mode
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P358_GB_ERR_DORMANT_STEADYSHOT_EOPNOTSUPP)
            self._assert_err_contains(gb, f"errno={P358_ERRNO_EOPNOTSUPP}")

    def test_032_group_b_fx6_zero_body_ibis_and_unsupported_symbol(self) -> None:
        self.assertEqual(P358_FX6_BODY_IBIS_COUNT, 0)
        self.assertEqual(
            P358_FX6_IBIS_UNSUPPORTED_SYMBOL, "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
        )
        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(claimed_fx6_has_body_ibis=True)
        self.assertFalse(gb.passed)
        self._assert_err(gb, P358_GB_ERR_FX6_ZERO_IBIS_CONTRACT)

    def test_033_group_b_playback_5_readonly_items_and_rotatiton_typo(self) -> None:
        self.assertEqual(len(P358_PLAYBACK_5_READONLY_ITEMS), 5)
        self.assertEqual(P358_DISPLAY_ROTATION_BKID_TYPO, "BKID_APP_setting_display_rotatiton")
        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            image_index="25_IMAGES",
            display_rotation="MANUAL",
            focus_frame_display="ON",
            cont_pb_for_interval="ON",
            play_speed_for_interval=9,
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.playback_media_sector_writes, 0)

        for kw in (
            {"exposed_playback_readonly_items": P358_PLAYBACK_5_READONLY_ITEMS[:-1]},
            {"image_index": "12_IMAGES"},
            {"display_rotation": "FLIP"},
            {"play_speed_for_interval": 0},
            {"play_speed_for_interval": 10},
            {"claimed_playback_5_wiped_by_camera_reset": True},
            {"claimed_interval_pb_generates_video_or_writes_card": True},
        ):
            g = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT)

    def test_034_group_b_camid_reel_17char_vs_37char_title_and_fx6_mxf(self) -> None:
        self.assertEqual(P358_MOVIE_CAMID_REEL_STEM_LEN, 17)
        self.assertEqual(P358_TITLE_NAME_MAX_CHARS, 37)
        self.assertEqual((P358_FX6_TITLE_PREFIX_MIN_CHARS, P358_FX6_TITLE_PREFIX_MAX_CHARS), (4, 46))
        self.assertEqual(P358_FX6_CLIP_PATH_TEMPLATE, "/XDROOT/Clip/*.MXF")

        gb_ok = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            file_name_format="CAM_ID_REEL",
            camid_reel_stem="A001D001_230101AB",
            title_name="T" * 37,
            fx6_title_prefix_chars=46,
        )
        self.assertTrue(gb_ok.passed)

        gb_sdhc = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            media_type="SDHC", file_name_format="CAM_ID_REEL"
        )
        self.assertTrue(gb_sdhc.passed)
        self.assertEqual(gb_sdhc.effective_file_name_format, "STANDARD")

        for kw in (
            {"file_name_format": "CUSTOM"},
            {"camid_reel_stem": "SHORT"},
            {"title_name": "T" * 38},
            {"fx6_title_prefix_chars": 3},
            {"fx6_title_prefix_chars": 47},
            {"claimed_camid_reel_stem_is_37_chars": True},
            {"media_type": "SDHC", "expect_camid_reel_allowed_on_sdhc": True},
            {"claimed_file_settings_wiped_by_camera_reset": True},
        ):
            g = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT)

    def test_035_group_b_slot1_file_folder_erofs30_firewall(self) -> None:
        for kw in (
            {"create_new_folder_on_slot1_requested": True},
            {"forced_file_no_reset_on_slot1_requested": True},
            {"select_rec_folder_write_on_slot1_requested": True},
            {"series_counter_reset_on_slot1_requested": True},
        ):
            gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(**kw)
            self.assertFalse(gb.passed)
            self.assertEqual(gb.slot1_data_sector_writes, 0)
            self._assert_err(gb, P358_GB_ERR_SLOT1_FILE_FOLDER_EROFS30)
            self._assert_err_contains(gb, f"errno={P358_ERRNO_EROFS}")

    # ------------------------------------------------------------------
    # 36-58: Check Group C — Wave 76 XLR-H1, Custom Key, DiffSet8, GammaAssist
    # ------------------------------------------------------------------

    def test_036_group_c_xlr_h1_zero_assignable_keys_rec_and_dials(self) -> None:
        self.assertEqual(P358_XLR_H1_ASSIGNABLE_BUTTON_COUNT, 0)
        self.assertEqual(P358_XLR_H1_REC_BUTTON_COUNT, 0)
        self.assertEqual(P358_XLR_H1_DIAL_COUNT, 0)
        gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp()
        self.assertTrue(gc.passed)
        self.assertEqual(gc.xlr_h1_assignable_button_count, 0)
        self.assertEqual(gc.xlr_h1_rec_button_count, 0)
        self.assertEqual(gc.xlr_h1_dial_count, 0)

        gc_bad = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            claimed_xlr_h1_has_custom_or_rec_keys=True
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS)

    def test_037_group_c_custom_key_3_domains_16_16_7_and_fn_playback_only(self) -> None:
        self.assertEqual(P358_STILL_CUSTOM_CONTROL_COUNT, 16)
        self.assertEqual(P358_MOVIE_CUSTOM_CONTROL_COUNT, 16)
        self.assertEqual(P358_PLAYBACK_CUSTOM_CONTROL_COUNT, 7)
        self.assertNotIn("C4", P358_PLAYBACK_CUSTOM_CONTROLS)
        self.assertIn("FN_BUTTON", P358_PLAYBACK_CUSTOM_CONTROLS)
        self.assertEqual(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS["C1"], "LPRESS_AV_AUTO_MANUAL")
        self.assertEqual(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS["C4"], "NOT_SET")
        self.assertEqual(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS["C5"], "FOCUS_MAGNIFIER")

        for kw in (
            {"still_custom_controls": P358_STILL_CUSTOM_CONTROLS[:-1]},
            {"movie_custom_factory_defaults": {**P358_MOVIE_CUSTOM_FACTORY_DEFAULTS, "C4": "AF_ON"}},
            {"playback_custom_controls": P358_PLAYBACK_CUSTOM_CONTROLS[:-1]},
            {"claimed_fn_assignable_in_still_or_movie": True},
            {"claimed_pb_includes_c4_delete": True},
            {"claimed_custom_key_wiped_by_camera_reset": True},
        ):
            g = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS)

    def test_038_group_c_dormant_alpha_custom_keys_rejected_eopnotsupp_95(self) -> None:
        self.assertIn("moviel_product_showcase_set_button", P358_DORMANT_CUSTOM_KEY_SYMBOLS)
        for sym in P358_DORMANT_CUSTOM_KEY_SYMBOLS:
            gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                dormant_custom_key_requested=sym
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P358_GC_ERR_DORMANT_CUSTOM_KEY_EOPNOTSUPP)
            self._assert_err_contains(gc, f"errno={P358_ERRNO_EOPNOTSUPP}")

    def test_039_group_c_diff_set_exact_8_items_and_pp_checkbox_survives_initialize(self) -> None:
        self.assertEqual(
            P358_DIFF_SET_EXACT_8_ITEMS,
            (
                "APERTURE",
                "SHUTTER_SPEED",
                "ISO",
                "EXPOSURE_COMP",
                "METERING_MODE",
                "WHITE_BALANCE",
                "PICTURE_PROFILE",
                "FOCUS_MODE",
            ),
        )
        gc_init = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            diff_set_pp_checkbox_checked=True, reset_action="INITIALIZE"
        )
        self.assertTrue(gc_init.passed)
        self.assertTrue(gc_init.effective_pp_checkbox_after_reset)

        gc_angle = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            shutter_mode="ANGLE"
        )
        self.assertTrue(gc_angle.passed)
        self.assertTrue(gc_angle.shutter_angle_splits_still_movie)

        for kw in (
            {"diff_set_items": P358_DIFF_SET_EXACT_8_ITEMS[:-1]},
            {"diff_set_transition": "INVALID"},
            {"claimed_pp_checkbox_wiped_by_reset_or_init": True},
            {"claimed_common_to_separate_copies_custom_wb_to_movie": True},
            {"claimed_separate_to_common_discards_still_av_tv_wb": True},
            {"claimed_shutter_angle_shared_when_diffset_unchecked": True},
            {"claimed_diff_set_saved_in_campr": True},
        ):
            g = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY)

    def test_040_group_c_gamma_disp_assist_log_lockout_dormant_slog2_and_0px_hdmi(self) -> None:
        self.assertEqual(
            P358_GAMMA_DISP_ASSIST_TYPES,
            ("AUTO", "SLOG3_TO_709_800", "HLG_BT2020", "HLG_709"),
        )
        self.assertFalse(P358_FX3_GAMMA_ASSIST_SLOG2_EXPOSED)
        self.assertEqual(P358_GAMMA_DISP_ASSIST_HDMI_PIXEL_COUNT, 0)

        gc_log = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            log_shooting_mode="CINE_EI", gamma_display_assist="ON"
        )
        self.assertTrue(gc_log.passed)
        self.assertEqual(gc_log.effective_gamma_display_assist, "OFF")

        gc_still_log = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            log_shooting_mode="CINE_EI", shooting_still_in_log_mode=True
        )
        self.assertTrue(gc_still_log.passed)
        self.assertEqual(gc_still_log.effective_gamma_display_assist, "ON")

        for kw in (
            {"dormant_gamma_assist_slog2_requested": True},
            {"log_shooting_mode": "FLEXIBLE_ISO", "claimed_gamma_assist_active_when_log_movie_on": True},
            {"claimed_gamma_assist_applies_to_hdmi_or_tv": True},
            {"claimed_gamma_assist_wiped_by_camera_reset": True},
            {"gamma_disp_assist_type": "SLOG2"},
        ):
            g = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF)

    def test_041_group_c_fx6_assignable_keys_and_4way_mlut(self) -> None:
        self.assertEqual(len(P358_FX6_ASSIGNABLE_BUTTON_LABELS), 9)
        self.assertFalse(P358_FX6_STILL_MOVIE_SPLIT_SUPPORTED)
        self.assertEqual(P358_FX6_GAMMA_DISP_ASSIST_UI_COUNT, 0)
        for kw in (
            {"claimed_fx6_lacks_assignable_or_has_still_split": True},
            {"claimed_fx6_has_gamma_display_assist_ui": True},
        ):
            g = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GC_ERR_FX6_ASSIGNABLE_OR_4WAY_MLUT)

    # ------------------------------------------------------------------
    # 42-70: Check Group D — Wave 76 USB-LAN, Auth, IPsec, Airplane, Cleaning
    # ------------------------------------------------------------------

    def test_042_group_d_usblan_dhcp_manual_ipv4_and_mutex(self) -> None:
        self.assertEqual(P358_USB_LAN_LIBS, ("libWiredLanResource.so", "libNetServiceEther.so"))
        self.assertIn("r8152", P358_USB_LAN_KERNEL_MODULES)
        self.assertEqual(P358_USB_LAN_IP_MODES, ("AUTO", "MANUAL"))
        self.assertEqual(P358_USB_LAN_MANUAL_FIELD_MAX_CHARS, 15)

        gd_manual = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            usb_lan_ip_mode="MANUAL", usb_lan_manual_ip="192.168.100.200"
        )
        self.assertTrue(gd_manual.passed)
        self.assertTrue(gd_manual.usb_lan_manual_ip_valid)

        for kw in (
            {"usb_lan_ip_mode": "STATIC"},
            {"usb_lan_ip_mode": "MANUAL", "usb_lan_manual_ip": "999.1.1.1"},
            {"usb_lan_ip_mode": "MANUAL", "usb_lan_manual_ip": "192.168.001.1001"},
            {"multi_usb_concurrent_active": True},
            {"wifi_concurrent_active": True},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED)

    def test_043_group_d_access_authen_and_ver7_disabled_ipsec(self) -> None:
        self.assertEqual(P358_ACCESS_AUTHEN_DEFAULT, "ON")
        self.assertEqual(P358_ACCESS_AUTHEN_PROTOCOLS, "SSH_AND_PTP_IP")
        self.assertEqual(P358_ACCESS_AUTHEN_USER_MAX_CHARS, 16)
        self.assertEqual((P358_ACCESS_AUTHEN_PASS_MIN_CHARS, P358_ACCESS_AUTHEN_PASS_MAX_CHARS), (8, 16))
        self.assertEqual(P358_IPSEC_MIN_DISABLED_FW_MAJOR, 7)
        self.assertEqual(P358_FX6_IPSEC_UI_BINDING_COUNT, 0)

        for kw in (
            {"ipsec_enabled": True},
            {"access_authen": "OFF", "ipsec_enabled": True, "body_fw": "7.02"},
            {"claimed_ipsec_available_on_ver7_or_authen_on": True},
            {"claimed_fx6_has_ipsec_menu": True},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED)

    def test_044_group_d_airplane_mode_usblan_bypass_and_reset_network_split(self) -> None:
        gd_net_reset = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            airplane_mode="ON", reset_action="RESET_NETWORK_SET", usb_lan_enabled=True
        )
        self.assertTrue(gd_net_reset.passed)
        self.assertEqual(gd_net_reset.effective_airplane_mode_after_reset, "ON")
        self.assertFalse(gd_net_reset.airplane_mode_blocks_usb_lan)

        gd_init = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            airplane_mode="ON", reset_action="INITIALIZE"
        )
        self.assertTrue(gd_init.passed)
        self.assertEqual(gd_init.effective_airplane_mode_after_reset, "OFF")

        for kw in (
            {"expect_airplane_mode_blocks_usb_lan": True},
            {"claimed_reset_network_set_wipes_airplane_mode": True},
            {"claimed_initialize_preserves_airplane_mode": True},
            {"airplane_mode": "AUTO"},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_AIRPLANE_RESET_SPLIT)

    def test_045_group_d_sensor_cleaning_51pct_gate_and_dormant_antidust(self) -> None:
        self.assertEqual(P358_SENSOR_CLEANING_MIN_BATTERY_PCT, 51)
        self.assertEqual(P358_FX3_ANTI_DUST_UI_COUNT, 0)
        self.assertEqual(P358_FX3_SHUTTER_WHEN_PWR_OFF_UI_COUNT, 0)

        gd_51 = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            sensor_cleaning_requested=True, battery_soc_pct=51, power_switch_turned_off_for_blower=True
        )
        self.assertTrue(gd_51.passed)

        for kw in (
            {"sensor_cleaning_requested": True, "battery_soc_pct": 50},
            {"sensor_cleaning_requested": True, "battery_soc_pct": 80, "power_switch_turned_off_for_blower": False},
            {"dormant_anti_dust_or_shutter_barrier_requested": True},
            {"claimed_fx3_has_shutter_when_pwr_off": True},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST)

    def test_046_group_d_ir_remote_fx3a_and_still_auto_review_vs_fx6(self) -> None:
        self.assertEqual(P358_AUTO_REVIEW_MODES, ("OFF", "2_SEC", "5_SEC", "10_SEC"))
        self.assertEqual(P358_AUTO_REVIEW_DEFAULT, "OFF")
        self.assertFalse(P358_FX6_BODY_IBIS_ULTRASONIC_CLEANING)
        self.assertEqual(P358_FX6_IR_REMOTE_UI_COUNT, 0)
        self.assertEqual(P358_FX6_STILL_AUTO_REVIEW_UI_COUNT, 0)

        gd_ok = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            ir_remote_ctrl="ON", fx3a_body_variant=False, auto_review="5_SEC"
        )
        self.assertTrue(gd_ok.passed)

        for kw in (
            {"ir_remote_ctrl": "ON", "fx3a_body_variant": True},
            {"ir_remote_ctrl": "ON", "bluetooth_rmt_ctrl": "ON"},
            {"ir_remote_ctrl": "ON", "power_save_expected_active": True},
            {"auto_review": "15_SEC"},
            {"expect_auto_review_triggers_after_movie": True},
            {"claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review": True},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6)

    def test_047_group_d_fail_closed_zero_rf_emmc_usb_and_slot1_redlines(self) -> None:
        for kw in (
            {"slot1_contains_tier0_dump": False},
            {"slot1_wp_locked": False},
            {"slot1_write_requested": True},
            {"airplane_mode": "OFF"},
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"wireless_rf_packets_emitted": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            g = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(**kw)
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    # ------------------------------------------------------------------
    # 48-68: Tier-0 528B FX3RCPT1 Dual-Media Receipt Gate & 16/16 H0 == H3
    # ------------------------------------------------------------------

    def test_048_tier0_physical_receipt_bytes_distinct_st_dev_verifies_16_of_16(self) -> None:
        sim = build_simulated_phase358_tier0_receipts(
            body_serial="FX3REAL7020358",
            emmc_cid="11010030303847333000a1b2c3d49358",
        )
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2001,
            st_dev_b_override=2002,
            body_serial="FX3REAL7020358",
            emmc_cid="11010030303847333000a1b2c3d49358",
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertEqual(
            rep.go_no_go,
            P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED,
        )
        self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_RECEIPT")
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase358_report(rep).valid)

    def test_049_tier0_receipt_paths_with_distinct_mocked_st_dev_pass(self) -> None:
        sim = build_simulated_phase358_tier0_receipts(
            body_serial="FX3REAL7020358",
            emmc_cid="11010030303847333000a1b2c3d49358",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            p_a = tmp_path / "copy_a.bin"
            p_b = tmp_path / "copy_b.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])

            real_stat = os.stat

            def fake_stat(path: object, *args: object, **kwargs: object) -> os.stat_result:
                res = real_stat(path, *args, **kwargs)  # type: ignore[arg-type]
                if Path(str(path)) == p_a:
                    return os.stat_result(
                        (res.st_mode, res.st_ino, 8801, res.st_nlink, res.st_uid, res.st_gid, res.st_size, res.st_atime, res.st_mtime, res.st_ctime)
                    )
                if Path(str(path)) == p_b:
                    return os.stat_result(
                        (res.st_mode, res.st_ino, 8802, res.st_nlink, res.st_uid, res.st_gid, res.st_size, res.st_atime, res.st_mtime, res.st_ctime)
                    )
                return res

            with mock.patch("os.stat", side_effect=fake_stat):
                rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
                    force_clean_room=True,
                    receipt_a_path=p_a,
                    receipt_b_path=p_b,
                    body_serial="FX3REAL7020358",
                    emmc_cid="110100303847333000a1b2c3d4935800"[:32],
                    h0_baselines_a=sim["h0_baselines_a"],
                    h0_baselines_b=sim["h0_baselines_b"],
                    h3_baselines=sim["h3_baselines"],
                )
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.check_group_d.st_dev_a, 8801)
            self.assertEqual(rep.check_group_d.st_dev_b, 8802)
            self.assertTrue(verify_phase358_report(rep).valid)

    def test_050_tier0_same_st_dev_and_partial_receipt_fail(self) -> None:
        sim = build_simulated_phase358_tier0_receipts()
        g_same = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=42,
            st_dev_b_override=42,
        )
        g_partial = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
        )
        self.assertFalse(g_same.passed)
        self.assertFalse(g_partial.passed)
        self._assert_err(g_same, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        self._assert_err(g_partial, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_051_tier0_byte_mismatch_corrupt_or_short_receipt_fails(self) -> None:
        sim = build_simulated_phase358_tier0_receipts()
        bad_b = bytearray(sim["receipt_b_bytes"])
        bad_b[-1] ^= 0xFF

        g_mismatch = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=bytes(bad_b),
            st_dev_a_override=1,
            st_dev_b_override=2,
        )
        g_corrupt = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=b"BADMAGIC" + b"\x00" * 520,
            receipt_b_bytes=b"BADMAGIC" + b"\x00" * 520,
            st_dev_a_override=1,
            st_dev_b_override=2,
        )
        g_short = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=b"FX3RCPT1" + b"\x00" * 16,
            receipt_b_bytes=b"FX3RCPT1" + b"\x00" * 16,
            st_dev_a_override=1,
            st_dev_b_override=2,
        )
        for g in (g_mismatch, g_corrupt, g_short):
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_052_tier0_missing_receipt_paths_and_trivial_serial_or_cid_fail(self) -> None:
        sim = build_simulated_phase358_tier0_receipts()
        g_miss = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_path=Path("/nonexistent/FX3RCPT1_A.bin"),
            receipt_b_path=Path("/nonexistent/FX3RCPT1_B.bin"),
        )
        g_ser = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial="00000000",
        )
        g_cid = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            emmc_cid="0" * 32,
        )
        for g in (g_miss, g_ser, g_cid):
            self.assertFalse(g.passed)
            self._assert_err(g, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_053_tier0_wrong_fw_or_model_id_fails(self) -> None:
        sim = build_simulated_phase358_tier0_receipts()
        g_fw = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_fw="5.00",
        )
        g_mid = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_model_id=0x11112222,
        )
        self.assertFalse(g_fw.passed)
        self.assertFalse(g_mid.passed)
        self._assert_err(g_fw, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        self._assert_err(g_mid, P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_054_tier0_h0_a_b_mismatch_h3_drift_and_sim_drift_fail(self) -> None:
        sim = build_simulated_phase358_tier0_receipts()
        h0_b_bad = dict(sim["h0_baselines_b"])
        h0_b_bad[REQUIRED_H0_BASELINE_KEYS[1]] = "e" * 64
        h3_bad = dict(sim["h3_baselines"])
        h3_bad[REQUIRED_H0_BASELINE_KEYS[0]] = "f" * 64

        g_ab = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=h0_b_bad,
            h3_baselines=sim["h3_baselines"],
        )
        g_h3 = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=h3_bad,
        )
        g_sim = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=2
        )
        for g in (g_ab, g_h3, g_sim):
            self.assertFalse(g.passed)
            self.assertLess(g.h0_equals_h3_count, 16)
            self._assert_err(g, P358_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    # ------------------------------------------------------------------
    # 55-70: Report Verifier, Markdown Rendering & Orchestrator Propagation
    # ------------------------------------------------------------------

    def test_055_orchestrator_failure_propagates_blocked_go_no_go(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            claimed_fx6_ae_level_limited_to_2ev=True,
        )
        self.assertEqual(
            rep.go_no_go,
            P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE,
        )
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase358_report(rep).valid)

    def test_056_verify_phase358_report_catches_sha_tamper_and_locked_flags(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertTrue(verify_phase358_report(rep).valid)

        d_sha = copy.deepcopy(rep.to_dict())
        d_sha["check_group_a"]["exposure_step"] = "0.5EV"
        res_sha = verify_phase358_report(d_sha)
        self.assertFalse(res_sha.valid)
        self.assertTrue(any("report_sha256 mismatch" in e for e in res_sha.errors))

        for flag in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "sd_physical_media_written",
            "cross_model_flash_authorized",
            "rf_nvs_p12_p13_writes_authorized",
            "fx6_body_ibis_present",
            "xlr_h1_assignable_keys_present",
            "fx3_gamma_assist_slog2_exposed",
            "fx3_ipsec_ver7_available",
            "fx3_anti_dust_shutter_barrier_exposed",
        ):
            d_flag = copy.deepcopy(rep.to_dict())
            d_flag[flag] = True
            d_flag["report_sha256"] = _canonical_sha256_dict(d_flag)
            res_flag = verify_phase358_report(d_flag)
            self.assertFalse(res_flag.valid, msg=f"{flag}=True must fail verification")

    def test_057_verify_phase358_report_catches_nonzero_telemetry(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        for field in (
            "emmc_write_count",
            "e_nd_actuator_tx_count",
            "e_nd_i2c_tx_bytes",
            "rf_packets_transmitted",
            "wireless_rf_packets_emitted",
            "rf_nvs_mutation_bytes",
            "slot1_data_sector_writes",
            "usb_packets_transmitted",
            "passive_tx_bytes_emitted",
            "raw_firmware_bytes_leaked",
        ):
            d = copy.deepcopy(rep.to_dict())
            d[field] = 1
            d["report_sha256"] = _canonical_sha256_dict(d)
            self.assertFalse(verify_phase358_report(d).valid)

    def test_058_verify_phase358_report_rejects_bad_schema_help_guide_and_go_no_go(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["schema_version"] = "wrong"
        d["sony_help_guide_id"] = "ilc/0000"
        d["go_no_go"] = "INVALID_GO_NO_GO"
        res = verify_phase358_report(d)
        self.assertFalse(res.valid)
        self.assertGreaterEqual(len(res.errors), 3)

    def test_059_verify_phase358_report_rejects_verified_with_missing_groups_tier0_h0h3_or_slot1(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        for patch in (
            {"check_groups_passed": 3},
            {"tier0_receipt_verified": False},
            {"h0_equals_h3_count": 15},
            {"slot1_tier0_vault_mutated": True},
        ):
            d = copy.deepcopy(rep.to_dict())
            d.update(patch)
            d["report_sha256"] = _canonical_sha256_dict(d)
            self.assertFalse(verify_phase358_report(d).valid)

    def test_060_render_phase358_markdown_contains_all_anchors(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase358_markdown(rep)
        self.assertIn("Phase 358", md)
        self.assertIn(P358_SCHEMA, md)
        self.assertIn("4/4", md)
        self.assertIn("16/16", md)
        self.assertIn(rep.report_sha256, md)
        for gid in PHASE_358_CHECK_GROUP_IDS:
            self.assertIn(gid, md)

    # ------------------------------------------------------------------
    # 61-76: CLI Subprocess Tests Across All 4 Modes & Fault Injections
    # ------------------------------------------------------------------

    def test_061_cli_help_returns_zero_and_exposes_key_flags(self) -> None:
        cp = _run_cli_subprocess(["--help"])
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        for flag in (
            "--metering-mode",
            "--exposure-step",
            "--fx6-ae-level",
            "--picture-profile",
            "--steadyshot-focal-length-mm",
            "--gamma-display-assist",
            "--usb-lan-ip-mode",
            "--battery-soc-pct",
            "--simulate-bench-dry-run",
        ):
            self.assertIn(flag, cp.stdout)

    def test_062_cli_default_offline_returns_rc2_awaiting_receipts(self) -> None:
        cp = _run_cli_subprocess(["--force-clean-room", "--summary"])
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        self.assertIn("OVERALL=READY_OFFLINE_AWAITING_BENCH_RECEIPTS", cp.stdout)
        self.assertIn("ready_attach=False", cp.stdout)

    def test_063_cli_simulate_bench_dry_run_and_force_clean_room_rc0(self) -> None:
        cp_dry = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(cp_dry.returncode, 0, msg=cp_dry.stderr)
        payload = json.loads(cp_dry.stdout)
        self.assertEqual(payload["schema_version"], P358_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(payload["check_groups_passed"], 4)
        self.assertEqual(payload["h0_equals_h3_count"], 16)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase358_report(payload).valid)

        cp_cr = _run_cli_subprocess(["--force-clean-room", "--simulate-bench-dry-run", "--summary"])
        self.assertEqual(cp_cr.returncode, 0, msg=cp_cr.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp_cr.stdout)

    def test_064_cli_output_and_markdown_out_artifacts_and_failure_rc2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_out = tmp_path / "p358.json"
            md_out = tmp_path / "p358.md"
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
            self.assertTrue(
                verify_phase358_report(json.loads(json_out.read_text(encoding="utf-8"))).valid
            )

            cp_fail = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--claimed-xlr-h1-has-custom-or-rec-keys",
                    "--summary",
                ]
            )
            self.assertEqual(cp_fail.returncode, 2, msg=cp_fail.stderr)
            self.assertIn(
                f"OVERALL={P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE}",
                cp_fail.stdout,
            )

    def test_065_cli_local_donor_mode_when_env_unset(self) -> None:
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

    def test_066_cli_fx3_clean_room_test_env_1_mode(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--summary"],
            extra_env={"FX3_CLEAN_ROOM_TEST": "1"},
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp.stdout)

    def test_067_cli_fx3_fx6_force_clean_room_env_1_mode(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--summary"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", cp.stdout)

    def test_068_cli_nonexistent_mac_work_root_falls_back_to_clean_room(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={
                "FX3_CLEAN_ROOM_TEST": "",
                "FX3_FX6_FORCE_CLEAN_ROOM": "",
                "FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase358_missing",
            },
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        payload = json.loads(cp.stdout)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)

    def test_069_cli_slot1_create_new_folder_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--create-new-folder-on-slot1-requested",
                "--summary",
            ]
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn(
            f"OVERALL={P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE}",
            cp.stdout,
        )

    def test_070_cli_dormant_steadyshot_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--dormant-steadyshot-mode-requested",
                "DYNAMIC_ACTIVE",
                "--summary",
            ]
        )
        self.assertEqual(cp.returncode, 2)

    def test_071_cli_sensor_cleaning_low_battery_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--sensor-cleaning-requested",
                "--battery-soc-pct",
                "50",
                "--summary",
            ]
        )
        self.assertEqual(cp.returncode, 2)

    def test_072_cli_ipsec_ver7_blocked_rc2(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--ipsec-enabled",
                "--summary",
            ]
        )
        self.assertEqual(cp.returncode, 2)

    # ------------------------------------------------------------------
    # 73-108: Cross-Matrix, Edge Boundary, Reset/Init & Negative Myth-Busters
    # ------------------------------------------------------------------

    def test_073_group_a_all_11_base_pp_and_off_valid_in_photo_and_movie(self) -> None:
        for mode in ("PHOTO", "MOVIE", "S_AND_Q"):
            for pp in ("OFF",) + P358_PP_BASE_PROFILES:
                self.assertTrue(
                    evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                        shoot_mode=mode, picture_profile=pp
                    ).passed
                )

    def test_074_group_a_pplut1_to_4_valid_in_movie_and_sq_rejected_in_photo(self) -> None:
        for pplut in P358_PPLUT_PROFILES:
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                    shoot_mode="MOVIE", picture_profile=pplut
                ).passed
            )
            self.assertFalse(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                    shoot_mode="PHOTO", picture_profile=pplut
                ).passed
            )

    def test_075_group_a_pplut_raw_output_on_does_not_force_1080p_hdmi(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            picture_profile="PPLUT4", internal_rec_active=True, hdmi_raw_output=True
        )
        self.assertTrue(ga.passed)
        self.assertIsNone(ga.pplut_forced_hdmi_resolution)

    def test_076_group_a_embed_lut_resets_to_on_on_cfexpress_and_sdxc(self) -> None:
        for mt in ("CFEXPRESS_A", "SDXC"):
            ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                media_type=mt, embed_lut_file="OFF", reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(ga.passed)
            self.assertEqual(ga.effective_embed_lut_file, "ON")

    def test_077_group_a_spot_point_resets_to_center_on_camera_reset(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            spot_metering_point="FOCUS_POINT_LINK",
            focus_area="SPOT_M",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_spot_metering_point, "CENTER")

    def test_078_group_a_ael_w_shutter_initialize_resets_to_auto(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            shoot_mode="PHOTO", ael_w_shutter="OFF", reset_action="INITIALIZE"
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.ael_w_shutter_effective)

    def test_079_group_a_fx6_ae_speed_boundaries_minus99_and_plus99(self) -> None:
        self.assertEqual((P358_FX6_AE_SPEED_MIN, P358_FX6_AE_SPEED_MAX), (-99, 99))
        for spd in (-99, 0, 99):
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(fx6_ae_speed=spd).passed
            )

    def test_080_group_a_fx6_detect_window_all_modes_and_custom_width_bounds(self) -> None:
        for w in P358_FX6_DETECT_WINDOW_MODES:
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(fx6_detect_window=w).passed
            )
        for width in (40, 500, 999):
            self.assertTrue(
                evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
                    fx6_detect_window="CUSTOM", fx6_detect_window_width=width
                ).passed
            )

    def test_081_group_b_steadyshot_47_table_spot_check_every_entry(self) -> None:
        for mm in P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM:
            self.assertTrue(
                evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                    steadyshot_adjust="MANUAL", steadyshot_focal_length_mm=mm
                ).passed
            )

    def test_082_group_b_invalid_steadyshot_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_movie="DYNAMIC"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_still="ACTIVE"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                steadyshot_adjust="SEMI_AUTO"
            ).passed
        )

    def test_083_group_b_playback_interval_speed_1_to_9_all_valid(self) -> None:
        self.assertEqual((P358_PLAY_SPEED_MIN, P358_PLAY_SPEED_MAX, P358_PLAY_SPEED_DEFAULT), (1, 9, 5))
        for spd in range(1, 10):
            self.assertTrue(
                evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                    play_speed_for_interval=spd
                ).passed
            )

    def test_084_group_b_all_5_file_name_formats_valid_on_cfexpress_and_sdxc(self) -> None:
        for mt in ("CFEXPRESS_A", "SDXC"):
            for fmt in P358_FILE_NAME_FORMATS:
                gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
                    media_type=mt, file_name_format=fmt
                )
                self.assertTrue(gb.passed)
                self.assertEqual(gb.effective_file_name_format, fmt)

    def test_085_group_b_slot1_unlocked_allows_no_error_but_keeps_zero_writes(self) -> None:
        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            slot1_contains_tier0_dump=False, create_new_folder_on_slot1_requested=True
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.slot1_data_sector_writes, 0)

    def test_086_group_c_invalid_gamma_and_display_lut_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                gamma_display_assist="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                display_lut="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                shutter_mode="DEGREE"
            ).passed
        )

    def test_087_group_c_select_lut_resets_on_camera_reset_while_gamma_assist_resists(self) -> None:
        gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            select_lut="USER3",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.effective_gamma_display_assist, "ON")
        self.assertEqual(gc.select_lut, "S709")

    def test_088_group_c_gamma_assist_initialize_resets_to_off(self) -> None:
        gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            reset_action="INITIALIZE",
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.effective_gamma_display_assist, "OFF")

    def test_089_group_c_diff_set_transitions_common_separate_and_back_valid(self) -> None:
        for tr in ("NONE", "COMMON_TO_SEPARATE", "SEPARATE_TO_COMMON"):
            self.assertTrue(
                evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                    diff_set_transition=tr
                ).passed
            )

    def test_090_group_c_diff_set_pp_checkbox_unchecked_also_survives_initialize(self) -> None:
        gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
            diff_set_pp_checkbox_checked=False, reset_action="INITIALIZE"
        )
        self.assertTrue(gc.passed)
        self.assertFalse(gc.effective_pp_checkbox_after_reset)

    def test_091_group_d_invalid_reset_shoot_connect_launch_and_authen_enums_rejected(self) -> None:
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                reset_action="FACTORY"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                shoot_mode="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                usb_lan_connect_launch="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                access_authen="AUTO"
            ).passed
        )

    def test_092_group_d_all_4_auto_review_modes_valid(self) -> None:
        for mode in P358_AUTO_REVIEW_MODES:
            self.assertTrue(
                evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                    auto_review=mode
                ).passed
            )

    def test_093_group_d_ir_remote_invalid_flag_and_bt_invalid_flag_rejected(self) -> None:
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                ir_remote_ctrl="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
                bluetooth_rmt_ctrl="AUTO"
            ).passed
        )

    def test_094_group_d_usb_lan_disabled_allows_wifi_or_multi_usb_in_airplane_mode_off_blocked(self) -> None:
        gd = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            usb_lan_enabled=False, wifi_concurrent_active=True, airplane_mode="ON"
        )
        self.assertTrue(gd.passed)

    def test_095_group_d_ipsec_blocked_even_on_fw_6_when_access_authen_on(self) -> None:
        gd = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            body_fw="6.01", access_authen="ON", ipsec_enabled=True
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED)

    def test_096_group_d_slot1_tier0_vault_never_mutated_even_on_failure(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            create_new_folder_on_slot1_requested=True,
            slot1_write_requested=True,
        )
        self.assertFalse(rep.slot1_tier0_vault_mutated)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_097_group_a_ciz_and_desqueeze_combined_face_priority_off(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            metering_mode="CENTER",
            face_priority_in_multi_metering="ON",
            ciz_or_digital_zoom_active=True,
            desqueeze_display="2.0X",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_metering_mode, "MULTI")
        self.assertEqual(ga.effective_face_priority_in_multi, "OFF")

    def test_098_group_a_sdxc_allows_embed_lut_on(self) -> None:
        ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
            media_type="SDXC", embed_lut_file="ON"
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_embed_lut_file, "ON")
        self.assertEqual(ga.user_lut_dir, "/Private/Sony/PRO/LUT")

    def test_099_group_b_camid_reel_c999_to_d001_rollover_accepted(self) -> None:
        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            file_name_format="CAM_ID_REEL", camid_reel_stem="A001D001_230101XY"
        )
        self.assertTrue(gb.passed)
        self.assertEqual(len(gb.camid_reel_stem), 17)

    def test_100_group_c_movie_custom_factory_defaults_have_all_16_controls(self) -> None:
        self.assertEqual(len(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS), 16)
        self.assertEqual(tuple(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS.keys()), P358_STILL_CUSTOM_CONTROLS)

    def test_101_group_d_tier0_receipt_verified_even_if_unrelated_gd_error_present(self) -> None:
        gd = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            simulate_bench_dry_run=True, ipsec_enabled=True
        )
        self.assertFalse(gd.passed)
        self.assertTrue(gd.tier0_receipt_verified)
        self.assertEqual(gd.h0_equals_h3_count, 16)

    def test_102_orchestrator_offline_has_no_errors_and_rc2_warning(self) -> None:
        rep = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.errors, ())
        self.assertTrue(any("528B FX3RCPT1" in w for w in rep.warnings))
        self.assertTrue(verify_phase358_report(rep).valid)

    def test_103_mode_equivalence_report_parity_between_clean_room_mechanisms(self) -> None:
        r_flag = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            r_env1 = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env2 = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
                simulate_bench_dry_run=True
            )
        r_none = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            work_root=Path("/nonexistent/phase358_parity"), simulate_bench_dry_run=True
        )
        self.assertEqual(r_flag.report_sha256, r_env1.report_sha256)
        self.assertEqual(r_flag.report_sha256, r_env2.report_sha256)
        self.assertEqual(r_flag.report_sha256, r_none.report_sha256)

    def test_104_markdown_error_and_warning_sections_rendered(self) -> None:
        rep_off = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True
        )
        md_off = render_phase358_markdown(rep_off)
        self.assertIn("## Warnings", md_off)

        rep_fail = run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True, ipsec_enabled=True
        )
        md_fail = render_phase358_markdown(rep_fail)
        self.assertIn("## Errors", md_fail)

    def test_105_group_b_active_steadyshot_24fps_raw_off_desqueeze_off_stays_active(self) -> None:
        gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
            steadyshot_movie="ACTIVE", frame_rate_fps=23.98, hdmi_raw_output=False, desqueeze_display="OFF"
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_steadyshot_movie, "ACTIVE")
        self.assertTrue(gb.catalyst_gyro_metadata_active)

    def test_106_group_c_gamma_disp_assist_all_4_types_valid(self) -> None:
        for t in P358_GAMMA_DISP_ASSIST_TYPES:
            self.assertTrue(
                evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
                    gamma_disp_assist_type=t
                ).passed
            )

    def test_107_group_d_manual_ip_boundary_15_chars_max_accepted(self) -> None:
        gd = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
            usb_lan_ip_mode="MANUAL", usb_lan_manual_ip="192.168.123.123"
        )
        self.assertTrue(gd.passed)
        self.assertEqual(len(gd.usb_lan_ip_mode), 6)
        self.assertTrue(gd.usb_lan_manual_ip_valid)

    def test_108_zero_pycache_emission_inside_fx6_closure(self) -> None:
        closure_pkg = REPO_ROOT / "outputs/fx6-on-fx3-closure/fx6_closure"
        pyc_files = list(closure_pkg.rglob("*.pyc"))
        self.assertEqual(pyc_files, [], msg=f"Unexpected .pyc files found: {pyc_files}")


if __name__ == "__main__":
    unittest.main()
