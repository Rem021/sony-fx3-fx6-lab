"""Four-mode unit tests (120 cases) for Phase 381
(`preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback`
+ short alias `preflight-phase381`):
26th Physical Bench Readiness Verifier (`26/26`, Global Sony Waves 83-84) across Check Groups A-D:
- Group A (Wave 83.1-83.2): `[Creative Look]` 10+6 / `354` NVRAM keys (`2` main + `352` option
  keys incl. `look`/`look_still`/`look_movie`), asymmetric `0..9` `Fade`/`Sharpness`/`Clarity`,
  `1..5` `Sharpness Range` (locked in Movie/S&Q), `Saturation` locked in `BW`/`SE`, 4 hard
  lockouts (`PP11`, `Log != Off`, `HLG Still = On`, `iAuto`), dormant `[Soft Skin Effect]`
  (`EOPNOTSUPP=95`), FX6 `Base Look` + `User 1..16`; Still `[Drive Mode]` 8 modes (`Hi+` 10fps
  no live-view, `> F11` AF lock NOT `F8`, CFexpress `CEA-G160T` `>= 1000` buffer), exact 16 EV
  bracket combos (zero `9 Image` for `2.0/3.0 EV`), dormant `[Focus Bracket]` (`129` FX3 / `98`
  FX6 Wave 83 `G151` erratum), `[Interval Shoot Func.]` exact 7 resettable items + Ver. 7.02
  `[Shutter Type in Interval]` (`Electronic Shutter` default), FX6 zero `Frame Rec`.
- Group B (Wave 83.3-83.4): `libUsbBusPower.so` (`48,232 B`, 11 PMIC `.ko` drivers), mandatory
  in-slot `NP-FZ100` (`7.2 V`), USB-PD `9V/3A` `HIGH` (zero ON-state charging, OFF-state
  `10-30 C` `>= 18 W`), `5V/1.5A` `LOW` drain, `Sony DC-C1` (`>= 65 W + 5A`), hot-pull power-loss
  redline (`SequenceAsync_PowerOff` / `mcmn_drv_writeandflush`/`fsync`), FX6 `19.5V` EIAJ `DC IN`
  & hot-replug reboot trap; `[Power Setting Option]` exact 2 anti-Reset items, FX3 `9` vs
  `ILME-FX3A` `8` bypasses, dormant `[Power Save by Monitor]` (`EOPNOTSUPP=95`), `ILME-FX3A`
  (`ilc/2510`, `2.36M`-dot LCD) IR & NFC removal, FX3 IR/BLE mutex, Ver. 7.00+ `[USB-LAN Cnct.
  Launch]`, FX6 `2.5 mm` LANC + `3.5 mm` grip remote.
- Group C (Wave 84.1-84.2): `[My Menu]` exact `6 x 7 = 42` slots (Wave 84 `G98` erratum),
  Playback blacklist, 6 anti-Reset ops + `[Display From My Menu]` (`Off` def), Slot 1 `CAMSET`
  Save/Delete `EROFS=30`; `[Fn Menu Settings]` `12+12` independent slots, ZERO `Follow Custom`,
  all-`Not set` `_f 0x6220` block, `XLR-H1` zero `Fn`/`MENU`/REC keys, FX6 `User Menu` (`20`
  items, PIN excluded from `All File`); `[Focus Mode]` Still `5` vs Movie/`S&Q` locked `2`,
  Still anti-Reset `[AF w/ Shutter]`/`[Pre-AF]` & resettable `[AF Tracking Sensitivity]` (`3`),
  Movie `[AF Transition Speed]` (`5`) & `[AF Subj. Shift Sensitivity]` default `5(Responsive)`
  NOT `3` (`MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`), `14`-item `[Focus Area Limit]` (min 2),
  anti-Reset orthogonal `[Circ. of Focus Point]` (8 movable areas), FX6 `Face/Eye Detection AF`.
- Group D + Tier-0 (Wave 84.3-84.4 + `16/16 H0 == H3`): `[Exposure Comp.]` (`±5.0`/`±2.0 EV`,
  lockouts), anti-Reset `[Exposure step]` (independent of `Shutter Angle`), ALL `5` metering
  modes `[Exposure Std. Adjust]` (`-6..+6` sixths, anti-Reset), Still anti-Reset `[AEL w/
  Shutter]`, `[Spot Metering Point]` exact `8` linked (initial point only in Tracking) / `6`
  center-locked (Wave 84 `G116` erratum), FX6 `Auto Exposure Level` (`±3.0 EV @ 0.25`, ZERO
  `AE Shift`) & `AGC Limit` (`3..36 dB`, `12` ISO groups); Playback exact 3 `[View Mode]`,
  `[Display Rotation]` default `Auto` (`BKID_APP_setting_display_rotatiton`), `[Image Index]`
  `9/25`, `[Display as Group]`, `[Enlarge Initial Mag./Position]` anti-Reset; `[Protect]` exact
  `7` menu items ZERO `"Single"` (Wave 84 `G114` erratum, syncs `M4ROOT/SUB/*S03.MP4`) &
  `[Rating]` `0..5` Slot 1 `EROFS=30`; `[Select on Cam & Send]` Zero-RF `[Airplane Mode]=On`
  block; FX6 `Thumbnail`/`OK-NG-KEEP`/`Shot Mark 1-2`/`Lock-Unlock Clip`; dual-media `528 B
  FX3RCPT1` Tier-0 receipt gate (`overall_ready_for_hardware_attach=False`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and mocked donorless (`work_root=None`) modes with
zero `.pyc` emission and zero persistent writes.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import ast
import collections
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
    build_default_h0_baselines,
)
from fx6_closure.realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier import (  # noqa: E402
    P381_BOUNDED_DONOR_PATHS,
    P381_CHECK_GROUP_A_ID,
    P381_CHECK_GROUP_B_ID,
    P381_CHECK_GROUP_C_ID,
    P381_CHECK_GROUP_D_ID,
    P381_CREATIVE_LOOK_ALL_16_SLOTS,
    P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS,
    P381_DISPLAY_ROTATION_BKID_TYPO,
    P381_ERRNO_EINVAL,
    P381_ERRNO_EOPNOTSUPP,
    P381_ERRNO_EPERM,
    P381_ERRNO_EROFS,
    P381_EV_BRACKET_EXACT_16_COMBOS,
    P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES,
    P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS,
    P381_FX3A_POWER_SAVE_EXACT_8_BYPASSES,
    P381_FX3_POWER_SAVE_EXACT_9_BYPASSES,
    P381_FX6_SPECIAL_REC_EXACT_3,
    P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT,
    P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16,
    P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM,
    P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC,
    P381_GA_ERR_MODEL_OR_FW_FLOOR,
    P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK,
    P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC,
    P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP,
    P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR,
    P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION,
    P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU,
    P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF,
    P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE,
    P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30,
    P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116,
    P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12,
    P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET,
    P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30,
    P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL,
    P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P381_GO_NO_GO_BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE,
    P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED,
    P381_HEADER_READ_BYTES,
    P381_INTERVAL_EXACT_7_ITEMS,
    P381_LIBUSBBUSPOWER_EXACT_11_KMODS,
    P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL,
    P381_MY_MENU_EXACT_6_OPS,
    P381_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P381_POWER_SAVE_START_TIME_EXACT_6_OPTIONS,
    P381_POWER_SETTING_OPTION_EXACT_2_ITEMS,
    P381_PROTECT_MENU_EXACT_7_ITEMS,
    P381_SCHEMA,
    P381_SONY_HELP_GUIDE_ID,
    P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS,
    P381_SPOT_METERING_LINKED_EXACT_8_AREAS,
    P381_STILL_DRIVE_EXACT_8_MODES,
    P381_STORAGE_SURFACE_COUNT,
    P381_VERSION,
    P381_VIEW_MODE_EXACT_3_STATES,
    PHASE_381_CHECK_GROUP_IDS,
    RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport,
    build_simulated_phase381_tier0_receipts,
    evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval,
    evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes,
    evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14,
    evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0,
    evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight,
    inspect_phase381_donors_bounded,
    render_phase381_markdown,
    run_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight,
    verify_phase381_report,
)

PYTHONPATH_ENV = ":".join(
    str(REPO_ROOT / p)
    for p in (
        "outputs/fx6-on-fx3-closure",
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
    )
)
VERIFIER_MOD = (
    "fx6_closure.realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier"
)
CLI_CMD_LONG = "preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback"
CLI_CMD_ALIAS = "preflight-phase381"


class TestPhase381Preflight26Verifier(unittest.TestCase):
    def _assert_err(self, res: object, code: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(
            any(code in e for e in errs),
            msg=f"Expected error prefix {code!r} in {errs!r}",
        )

    def _run_cli(
        self,
        args: list[str],
        *,
        env_overrides: dict[str, str] | None = None,
        clear_clean_room_env: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if clear_clean_room_env:
            env.pop("FX3_CLEAN_ROOM_TEST", None)
            env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            env.pop("FX3_FX6_MAC_WORK_ROOT", None)
        if env_overrides:
            env.update(env_overrides)
        env["PYTHONPATH"] = PYTHONPATH_ENV
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "-m", "fx6_closure", *args],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    # ------------------------------------------------------------------
    # 1. Exports, Non-Shadowing & Bounded O_RDONLY / 4-Mode Parity (12)
    # ------------------------------------------------------------------

    def test_001_package_exports_and_all_contain_phase381_symbols(self) -> None:
        required = (
            "P381_SCHEMA",
            "P381_VERSION",
            "evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval",
            "evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes",
            "evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14",
            "evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0",
            "evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight",
            "run_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight",
            "verify_phase381_report",
            "render_phase381_markdown",
            "build_simulated_phase381_tier0_receipts",
            "inspect_phase381_donors_bounded",
            "resolve_phase381_donor_file_or_none",
            "RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport",
        )
        for sym in required:
            self.assertTrue(hasattr(fx6_closure, sym), msg=f"Missing export {sym}")
            self.assertIn(sym, fx6_closure.__all__, msg=f"Missing __all__ entry {sym}")

    def test_002_zero_ast_duplicates_and_no_shadowing_of_prior_phases(self) -> None:
        init_path = REPO_ROOT / "outputs/fx6-on-fx3-closure/fx6_closure/__init__.py"
        tree = ast.parse(init_path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.append(alias.asname or alias.name)
        dup_imp = [k for k, v in collections.Counter(imported).items() if v > 1]
        dup_all = [k for k, v in collections.Counter(fx6_closure.__all__).items() if v > 1]
        self.assertEqual(dup_imp, [])
        self.assertEqual(dup_all, [])
        self.assertGreaterEqual(len(fx6_closure.__all__), 4500)
        for prior in (
            "P374_SCHEMA",
            "P371_SCHEMA",
            "P368_SCHEMA",
            "verify_phase374_report",
            "verify_phase371_report",
        ):
            self.assertTrue(hasattr(fx6_closure, prior))

    def test_003_schema_version_and_group_ids(self) -> None:
        self.assertEqual(P381_VERSION, "phase381_v1")
        self.assertEqual(
            P381_SCHEMA,
            "realhw_preflight26_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_playback_v1",
        )
        self.assertEqual(P381_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(
            PHASE_381_CHECK_GROUP_IDS,
            (
                P381_CHECK_GROUP_A_ID,
                P381_CHECK_GROUP_B_ID,
                P381_CHECK_GROUP_C_ID,
                P381_CHECK_GROUP_D_ID,
            ),
        )

    def test_004_donor_inspection_force_clean_room(self) -> None:
        res = inspect_phase381_donors_bounded(force_clean_room=True)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.donor_tree_present)
        self.assertEqual(res.donors_checked, len(P381_BOUNDED_DONOR_PATHS))
        self.assertEqual(res.donors_present, 0)
        self.assertEqual(res.bytes_read_total, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_005_donor_inspection_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            res = inspect_phase381_donors_bounded()
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.bytes_read_total, 0)

    def test_006_donor_inspection_force_clean_room_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            res = inspect_phase381_donors_bounded()
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.donors_present, 0)

    def test_007_donor_inspection_nonexistent_work_root(self) -> None:
        res = inspect_phase381_donors_bounded(
            force_clean_room=False,
            work_root=Path("/nonexistent/phase381_missing"),
        )
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.donor_tree_present)
        self.assertEqual(res.bytes_read_total, 0)

    def test_008_donor_inspection_mocked_work_root_none(self) -> None:
        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            res = inspect_phase381_donors_bounded(force_clean_room=False)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.donors_present, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_009_donor_inspection_bounded_o_rdonly_nofollow_max_64b(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx6_dir = Path(tmp) / "fx6"
            fx3_dir = Path(tmp) / "fx3"
            fx6_dir.mkdir()
            fx3_dir.mkdir()
            (fx6_dir / "appFw.so").write_bytes(b"\x7fELF" + b"6" * 512)
            (fx3_dir / "appFw.so").write_bytes(b"\x7fELF" + b"3" * 512)
            (fx3_dir / "libUsbBusPower.so").symlink_to(fx3_dir / "appFw.so")
            res = inspect_phase381_donors_bounded(
                force_clean_room=False,
                work_root=Path("/nonexistent/phase381_missing"),
                fx6_lib_dir=fx6_dir,
                fx3_modules_dir=fx3_dir,
            )
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(res.donor_tree_present)
        self.assertEqual(res.donors_present, 2)
        self.assertEqual(res.bytes_read_total, 2 * P381_HEADER_READ_BYTES)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_010_default_offline_preflight_blocks_awaiting_tier0_receipt(self) -> None:
        rep = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            force_clean_room=True
        )
        self.assertIsInstance(
            rep, RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport
        )
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.overall_status, P381_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase381_report(rep).valid)

    def test_011_dry_run_preflight_passes_deterministically(self) -> None:
        r1 = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        r2 = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        self.assertEqual(r1.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(r1.check_groups_passed, 4)
        self.assertEqual(r1.h0_equals_h3_count, P381_STORAGE_SURFACE_COUNT)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertFalse(r1.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase381_report(r1).valid)

    def test_012_run_alias_and_markdown_renderer(self) -> None:
        r1 = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        r2 = run_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase381_markdown(r1)
        self.assertIn("Phase 381", md)
        self.assertIn("26/26", md)
        self.assertIn(r1.report_sha256, md)

    # ------------------------------------------------------------------
    # 2. Check Group A — Wave 83.1-83.2 Creative Look & Drive Mode (24)
    # ------------------------------------------------------------------

    def test_013_group_a_default_pass(self) -> None:
        ga = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval()
        self.assertTrue(ga.passed)
        self.assertEqual(ga.creative_look_nvram_total_keys, P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS)
        self.assertTrue(ga.creative_look_locked_to_dash)
        self.assertEqual(ga.effective_creative_look, "-")
        self.assertFalse(ga.fx3_soft_skin_effect_supported)
        self.assertFalse(ga.fx3_focus_bracket_supported)
        self.assertFalse(ga.fx6_frame_rec_supported)
        self.assertEqual(ga.ev_bracket_combo_count, 16)

    def test_014_group_a_reject_wrong_model_fw_helpguide_enums(self) -> None:
        for kw in (
            {"body_model_id": 0x91030099},
            {"body_fw": "7.01"},
            {"body_fw": "7.x"},
            {"sony_help_guide_id": "ilc/9999"},
            {"shoot_mode": "TIMELAPSE"},
            {"exposure_mode": "MAGIC"},
            {"log_shooting_mode": "SLOG2"},
            {"reset_action": "WIPE"},
        ):
            ga = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P381_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_015_group_a_creative_look_all_16_slots_unlocked(self) -> None:
        for slot in P381_CREATIVE_LOOK_ALL_16_SLOTS:
            ga = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                picture_profile="OFF",
                creative_look_slot=slot,
            )
            self.assertTrue(ga.passed, msg=f"slot {slot} should pass")
            self.assertEqual(ga.effective_creative_look, slot)

    def test_016_group_a_creative_look_reject_invalid_slot_and_wrong_nvram_count(self) -> None:
        for kw in (
            {"creative_look_slot": "CUSTOM_7"},
            {"creative_look_nvram_total_keys": 352},
        ):
            ga = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_017_group_a_creative_look_symmetric_param_bounds(self) -> None:
        ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            picture_profile="OFF",
            creative_look_contrast=-9,
            creative_look_highlights=9,
            creative_look_shadows=-9,
            creative_look_saturation=9,
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"creative_look_contrast": -10},
            {"creative_look_highlights": 10},
            {"creative_look_shadows": -10},
            {"creative_look_saturation": 10},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_018_group_a_creative_look_asymmetric_nonnegative_0_to_9_bounds(self) -> None:
        ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            picture_profile="OFF",
            creative_look_fade=0,
            creative_look_sharpness=9,
            creative_look_clarity=5,
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"creative_look_fade": -1},
            {"creative_look_sharpness": -1},
            {"creative_look_clarity": -1},
            {"creative_look_fade": 10},
            {"claimed_creative_look_fade_sharpness_clarity_accept_negative": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_019_group_a_creative_look_sharpness_range_1_to_5_and_movie_lock(self) -> None:
        for kw in (
            {"creative_look_sharpness_range": 0},
            {"creative_look_sharpness_range": 6},
            {"shoot_mode": "MOVIE", "creative_look_sharpness_range_adjusted": True},
            {"shoot_mode": "S_AND_Q", "creative_look_sharpness_range_adjusted": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_020_group_a_creative_look_saturation_locked_in_bw_and_se(self) -> None:
        for slot in ("BW", "SE"):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                picture_profile="OFF",
                creative_look_slot=slot,
                creative_look_saturation_adjusted=True,
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_021_group_a_creative_look_4_hard_lockouts(self) -> None:
        for kw in (
            {"picture_profile": "PP11", "expect_creative_look_active_under_lockout": True},
            {"picture_profile": "OFF", "log_shooting_mode": "CINE_EI", "expect_creative_look_active_under_lockout": True},
            {"picture_profile": "OFF", "hlg_still_image": "ON", "expect_creative_look_active_under_lockout": True},
            {"picture_profile": "OFF", "exposure_mode": "INTELLIGENT_AUTO", "expect_creative_look_active_under_lockout": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_022_group_a_creative_look_can_be_reset(self) -> None:
        rst = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            picture_profile="OFF",
            creative_look_slot="FL",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_creative_look_after_reset, "ST")
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            claimed_creative_look_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT)

    def test_023_group_a_reject_dormant_soft_skin_effect_eopnotsupp95(self) -> None:
        for kw in (
            {"dormant_soft_skin_effect_requested": True},
            {"claimed_fx3_or_fx6_has_soft_skin_effect": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK)
            self.assertTrue(any(f"EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP}" in e for e in bad.errors))

    def test_024_group_a_fx6_base_look_user16_contrast(self) -> None:
        for kw in (
            {"fx6_base_look_user_lut_slots": 8},
            {"claimed_fx6_has_creative_look_menu": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK)

    def test_025_group_a_still_drive_mode_exact_8_and_reset(self) -> None:
        for mode in P381_STILL_DRIVE_EXACT_8_MODES:
            ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                still_drive_mode=mode
            )
            self.assertTrue(ok.passed)
        rst = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            still_drive_mode="CONT_SHOOTING", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_still_drive_mode_after_reset, "SINGLE_SHOOTING")
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            claimed_drive_mode_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_026_group_a_cont_shooting_hi_plus_10fps_no_live_view(self) -> None:
        ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            cont_speed_tier="HI_PLUS"
        )
        self.assertEqual(ok.cont_speed_max_fps, 10)
        self.assertFalse(ok.cont_live_view_active)
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            cont_speed_tier="HI_PLUS", expect_hi_plus_live_view=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_027_group_a_cont_shooting_af_lock_above_f11_not_f8(self) -> None:
        ok_f11 = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            cont_speed_tier="HI_PLUS", aperture_f_number=11.0
        )
        self.assertFalse(ok_f11.cont_af_locked_first_frame)
        ok_lo_f13 = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            cont_speed_tier="LO", aperture_f_number=13.0, expect_af_tracks_all_frames_above_f11=True
        )
        self.assertTrue(ok_lo_f13.passed)
        self.assertFalse(ok_lo_f13.cont_af_locked_first_frame)
        for tier in ("HI_PLUS", "HI", "MID"):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                cont_speed_tier=tier,
                aperture_f_number=13.0,
                expect_af_tracks_all_frames_above_f11=True,
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)
        bad_f8 = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            claimed_af_lock_threshold_is_f8=True
        )
        self.assertFalse(bad_f8.passed)
        self._assert_err(bad_f8, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_028_group_a_cfexpress_cea_g160t_buffer_and_nvme_vs_mmcb(self) -> None:
        for bus in ("CFEXPRESS_TYPE_A_NVME", "SDXC_UHS_II_MMCB"):
            ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                drive_media_bus=bus
            )
            self.assertTrue(ok.passed)
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            drive_media_bus="CFEXPRESS_TYPE_A_NVME", cfexpress_buffer_min_images=500
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_029_group_a_ev_bracket_exact_16_combos_pass(self) -> None:
        self.assertEqual(len(P381_EV_BRACKET_EXACT_16_COMBOS), 16)
        for ev, shots in P381_EV_BRACKET_EXACT_16_COMBOS:
            ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                ev_bracket_step_ev=ev, ev_bracket_shot_count=shots
            )
            self.assertTrue(ok.passed, msg=f"combo ({ev}, {shots}) should pass")

    def test_030_group_a_ev_bracket_reject_2ev_3ev_9shots_and_dormant_steps(self) -> None:
        for ev, shots in ((2.0, 9), (3.0, 9), (1.3, 3), (1.0, 7), (0.3, 2)):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
                ev_bracket_step_ev=ev, ev_bracket_shot_count=shots
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_031_group_a_dormant_focus_bracket_and_wave83_g151_erratum(self) -> None:
        ga_ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval()
        self.assertEqual(ga_ok.fx3_dormant_focus_bracket_symbols, 129)
        self.assertEqual(ga_ok.fx6_dormant_focus_bracket_symbols_g151_full, 98)
        for kw in (
            {"dormant_focus_bracket_requested": True},
            {"claimed_fx3_or_fx6_exposes_focus_bracket": True},
            {"claimed_g151_fx6_focus_bracket_full_scan_is_56": True},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM)

    def test_032_group_a_interval_7_items_all_resettable(self) -> None:
        rst = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            interval_shutter_type="MECHANICAL_SHUTTER",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.interval_items_exposed, P381_INTERVAL_EXACT_7_ITEMS)
        self.assertEqual(rst.effective_interval_shutter_after_reset, "ELECTRONIC_SHUTTER")
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            claimed_interval_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC)

    def test_033_group_a_interval_v702_name_and_no_in_camera_synthesis(self) -> None:
        for kw in (
            {"claimed_interval_shutter_name_is_legacy_silent_shoot": True},
            {"claimed_interval_in_camera_movie_synthesis": True},
            {"interval_items_exposed": ("Interval Shooting", "Silent Shoot. in Interval")},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC)

    def test_034_group_a_fx6_special_rec_3_modes_and_zero_frame_rec(self) -> None:
        ok = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval()
        self.assertEqual(ok.fx6_special_rec_modes, P381_FX6_SPECIAL_REC_EXACT_3)
        self.assertFalse(ok.fx6_frame_rec_supported)
        for kw in (
            {"dormant_fx6_frame_rec_requested": True},
            {"claimed_fx6_has_frame_rec": True},
            {"fx6_special_rec_modes": ("S&Q Motion", "Interval Rec", "Frame Rec")},
        ):
            bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC)

    def test_035_group_a_still_drive_modes_exposed_mismatch(self) -> None:
        bad = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            still_drive_modes_exposed=("SINGLE_SHOOTING", "FOCUS_BRACKET")
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)

    def test_036_group_a_invalid_cont_tier_and_interval_shutter_type(self) -> None:
        b1 = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            cont_speed_tier="ULTRA_30FPS"
        )
        self.assertFalse(b1.passed)
        self._assert_err(b1, P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16)
        b2 = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
            interval_shutter_type="AUTO"
        )
        self.assertFalse(b2.passed)
        self._assert_err(b2, P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC)

    # ------------------------------------------------------------------
    # 3. Check Group B — Wave 83.3-83.4 USB-PD PMIC & Power Save FX3/FX3A (24)
    # ------------------------------------------------------------------

    def test_037_group_b_default_pass(self) -> None:
        gb = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes()
        self.assertTrue(gb.passed)
        self.assertEqual(gb.libusbbuspower_bytes, 48232)
        self.assertEqual(gb.pmic_kmods_exposed, P381_LIBUSBBUSPOWER_EXACT_11_KMODS)
        self.assertEqual(gb.power_setting_option_items, P381_POWER_SETTING_OPTION_EXACT_2_ITEMS)
        self.assertEqual(gb.power_save_bypass_count, 9)
        self.assertFalse(gb.fx3_power_save_by_monitor_supported)
        self.assertTrue(gb.ir_receiver_present)
        self.assertTrue(gb.nfc_present)
        self.assertFalse(gb.on_state_charging_possible)

    def test_038_group_b_reject_wrong_libusbbuspower_size_or_pmic_kmods(self) -> None:
        for kw in (
            {"libusbbuspower_bytes": 4096},
            {"pmic_kmods_exposed": ("usb_bd91407gw.ko",)},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_039_group_b_reject_missing_np_fz100_under_usb_pd(self) -> None:
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_profile="USB_PD_9V_3A_HIGH", np_fz100_inserted=False
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_040_group_b_reject_multi_micro_usb_power_terminal(self) -> None:
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_terminal="MULTI_MICRO_USB"
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_041_group_b_dc_c1_requires_65w_and_5a_cable(self) -> None:
        ok = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_profile="SONY_DC_C1_COUPLER",
            np_fz100_inserted=False,
            dc_c1_pd_watts=65,
            dc_c1_cable_amps=5,
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"usb_power_profile": "SONY_DC_C1_COUPLER", "np_fz100_inserted": False, "dc_c1_pd_watts": 45, "dc_c1_cable_amps": 5},
            {"usb_power_profile": "SONY_DC_C1_COUPLER", "np_fz100_inserted": False, "dc_c1_pd_watts": 65, "dc_c1_cable_amps": 3},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_042_group_b_5v_1_5a_low_drains_warning_and_block(self) -> None:
        warn = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_profile="USB_5V_1_5A_LOW"
        )
        self.assertTrue(warn.passed)
        self.assertGreaterEqual(len(warn.warnings), 1)
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_profile="USB_5V_1_5A_LOW", expect_5v_1_5a_sustains_4k_recording=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_043_group_b_reject_on_state_charging_claim(self) -> None:
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            expect_on_state_battery_charging=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_044_group_b_off_state_charging_10_to_30c_and_9v2a_min(self) -> None:
        ok = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            off_state_charging_active=True, ambient_temp_c=25.0, off_charge_pd_watts=18.0
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"off_state_charging_active": True, "ambient_temp_c": 5.0},
            {"off_state_charging_active": True, "ambient_temp_c": 35.0},
            {"off_state_charging_active": True, "off_charge_pd_watts": 7.5},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_045_group_b_usb_power_supply_anti_camera_reset(self) -> None:
        rst = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_supply="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_usb_power_supply_after_reset, "OFF")
        ini = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_supply="OFF", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_usb_power_supply_after_reset, "ON")
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            claimed_usb_power_supply_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_046_group_b_tier0_hot_pull_np_fz100_power_loss_redline(self) -> None:
        for kw in (
            {"hot_pull_np_fz100_requested": True},
            {"claimed_hot_pull_runs_poweroff_and_fsync": True},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP)

    def test_047_group_b_fx6_dc_in_18_to_20_5v_hot_replug_and_no_usbc_power(self) -> None:
        for kw in (
            {"fx6_dc_in_voltage_v": 17.5},
            {"fx6_dc_in_voltage_v": 21.0},
            {"fx6_hot_replug_dc_in_during_rec": True},
            {"claimed_fx6_supports_usbc_power_supply": True},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP)

    def test_048_group_b_power_save_start_time_exact_6_options(self) -> None:
        for opt in P381_POWER_SAVE_START_TIME_EXACT_6_OPTIONS:
            ok = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
                power_save_start_time=opt
            )
            self.assertTrue(ok.passed)
        for bad_opt in ("20_SEC", "NO_LIMIT"):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
                dormant_power_save_time_requested=bad_opt
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)

    def test_049_group_b_power_setting_option_2_items_anti_reset(self) -> None:
        rst = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            power_save_start_time="30_MIN",
            auto_power_off_temp="HIGH",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertEqual(rst.effective_power_save_start_time_after_reset, "30_MIN")
        self.assertEqual(rst.effective_auto_power_off_temp_after_reset, "HIGH")
        ini = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            power_save_start_time="30_MIN",
            auto_power_off_temp="HIGH",
            reset_action="INITIALIZE",
        )
        self.assertEqual(ini.effective_power_save_start_time_after_reset, "5_MIN")
        self.assertEqual(ini.effective_auto_power_off_temp_after_reset, "STANDARD")
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            claimed_power_setting_option_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)

    def test_050_group_b_auto_power_off_temp_high_tripod_only_warning_and_block(self) -> None:
        warn = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            auto_power_off_temp="HIGH", handheld_bare_skin_operation=True
        )
        self.assertTrue(warn.passed)
        self.assertGreaterEqual(len(warn.warnings), 1)
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            auto_power_off_temp="HIGH",
            handheld_bare_skin_operation=True,
            expect_high_temp_safe_handheld=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)

    def test_051_group_b_dormant_power_save_by_monitor_eopnotsupp95(self) -> None:
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            dormant_power_save_by_monitor_requested=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)
        self.assertTrue(any(f"EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP}" in e for e in bad.errors))

    def test_052_group_b_fx3_9_vs_fx3a_8_power_save_bypasses(self) -> None:
        fx3 = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3"
        )
        self.assertTrue(fx3.passed)
        self.assertEqual(fx3.power_save_bypass_count, 9)
        fx3a = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3A"
        )
        self.assertTrue(fx3a.passed)
        self.assertEqual(fx3a.power_save_bypass_count, 8)
        self.assertFalse(fx3a.ir_receiver_present)
        self.assertFalse(fx3a.nfc_present)

    def test_053_group_b_reject_mismatched_bypass_count_between_fx3_and_fx3a(self) -> None:
        b1 = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3",
            power_save_bypasses_exposed=P381_FX3A_POWER_SAVE_EXACT_8_BYPASSES,
        )
        self.assertFalse(b1.passed)
        self._assert_err(b1, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)
        b2 = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3A",
            power_save_bypasses_exposed=P381_FX3_POWER_SAVE_EXACT_9_BYPASSES,
        )
        self.assertFalse(b2.passed)
        self._assert_err(b2, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)

    def test_054_group_b_fx3a_ir_and_nfc_physically_removed(self) -> None:
        for kw in (
            {"camera_revision": "ILME_FX3A", "ir_remote_ctrl": "ON"},
            {"camera_revision": "ILME_FX3A", "nfc_requested": True},
            {"camera_revision": "ILME_FX3A", "claimed_fx3a_has_ir_or_nfc": True},
            {"camera_revision": "ILME_FX3", "claimed_fx3a_has_ir_or_nfc": True},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC)

    def test_055_group_b_original_fx3_ir_and_ble_remote_mutually_exclusive(self) -> None:
        ok_ir = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3", ir_remote_ctrl="ON", bluetooth_rmt_ctrl="OFF"
        )
        self.assertTrue(ok_ir.passed)
        ok_bt = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3", ir_remote_ctrl="OFF", bluetooth_rmt_ctrl="ON"
        )
        self.assertTrue(ok_bt.passed)
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3", ir_remote_ctrl="ON", bluetooth_rmt_ctrl="ON"
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC)

    def test_056_group_b_usb_lan_cnct_launch_ver700_reset_boundary(self) -> None:
        rst = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_lan_cnct_launch="ON", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_usb_lan_cnct_launch_after_reset, "ON")
        net = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_lan_cnct_launch="ON", reset_action="RESET_NETWORK_SET"
        )
        self.assertEqual(net.effective_usb_lan_cnct_launch_after_reset, "OFF")

    def test_057_group_b_fx6_lanc_and_grip_remote_zero_ble_ir(self) -> None:
        for kw in (
            {"claimed_fx6_has_ble_or_ir_remote": True},
            {"fx6_wired_remote_ports": ("BLE_REMOTE",)},
        ):
            bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC)

    def test_058_group_b_invalid_power_setting_option_list(self) -> None:
        bad = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            power_setting_option_items=("Power Save Start Time", "Auto Power OFF Temp.", "Power Save by Monitor")
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR)

    def test_059_group_b_invalid_camera_revision_and_usb_profile(self) -> None:
        b1 = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX9"
        )
        self.assertFalse(b1.passed)
        self._assert_err(b1, P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC)
        b2 = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            usb_power_profile="D_TAP_14V"
        )
        self.assertFalse(b2.passed)
        self._assert_err(b2, P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION)

    def test_060_group_b_fx3a_allows_ble_remote(self) -> None:
        ok = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
            camera_revision="ILME_FX3A", bluetooth_rmt_ctrl="ON", ir_remote_ctrl="OFF"
        )
        self.assertTrue(ok.passed)

    # ------------------------------------------------------------------
    # 4. Check Group C — Wave 84.1-84.2 My Menu 42, Fn 12+12 & Focus (24)
    # ------------------------------------------------------------------

    def test_061_group_c_default_pass(self) -> None:
        gc = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14()
        self.assertTrue(gc.passed)
        self.assertEqual(gc.my_menu_total_slots, 42)
        self.assertEqual(gc.my_menu_ops_exposed, P381_MY_MENU_EXACT_6_OPS)
        self.assertEqual(gc.fn_menu_still_slots, 12)
        self.assertEqual(gc.fn_menu_movie_slots, 12)
        self.assertFalse(gc.fx3_fn_menu_follow_custom_supported)
        self.assertFalse(gc.xlr_h1_has_fn_menu_or_rec_keys)
        self.assertEqual(gc.movie_af_subj_shift_sensitivity, 5)
        self.assertEqual(gc.movie_af_subj_shift_responsice_symbol, P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL)
        self.assertEqual(gc.focus_area_limit_items_exposed, P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS)

    def test_062_group_c_mymenu_42_debunks_30_and_36_wave84_g98_erratum(self) -> None:
        for kw in (
            {"my_menu_pages": 5, "my_menu_items_per_page": 6, "my_menu_total_slots": 30},
            {"my_menu_pages": 6, "my_menu_items_per_page": 6, "my_menu_total_slots": 36},
            {"claimed_mymenu_capacity_30_or_36_g98": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)

    def test_063_group_c_mymenu_playback_blacklist_einval22(self) -> None:
        bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            mymenu_add_playback_item_requested=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)
        self.assertTrue(any(f"EINVAL={P381_ERRNO_EINVAL}" in e for e in bad.errors))

    def test_064_group_c_mymenu_6_ops_and_display_from_mymenu_anti_reset(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            display_from_my_menu="ON", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_display_from_my_menu_after_reset, "ON")
        ini = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            display_from_my_menu="ON", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_display_from_my_menu_after_reset, "OFF")
        bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            claimed_mymenu_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)

    def test_065_group_c_camset_slot1_load_readonly_pass_and_save_delete_erofs30(self) -> None:
        ok_load = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            camset_operation="LOAD_READONLY", camset_target_slot=1
        )
        self.assertTrue(ok_load.passed)
        for op in ("SAVE", "DELETE"):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                camset_operation=op, camset_target_slot=1
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)
            self.assertTrue(any(f"EROFS={P381_ERRNO_EROFS}" in e for e in bad.errors))

    def test_066_group_c_camset_slot2_rejected_slot1_exclusive(self) -> None:
        bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            camset_operation="LOAD_READONLY", camset_target_slot=2
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)

    def test_067_group_c_fn_menu_12_plus_12_zero_follow_custom(self) -> None:
        for kw in (
            {"fn_menu_still_slots": 10},
            {"fn_menu_movie_slots": 16},
            {"claimed_fn_menu_has_follow_custom": True},
            {"claimed_fn_menu_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU)

    def test_068_group_c_fn_menu_all_not_set_blocked_0x6220(self) -> None:
        for kw in (
            {"fn_menu_all_not_set_requested": True},
            {"fn_menu_active_slots": 0},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU)

    def test_069_group_c_xlr_h1_zero_fn_menu_rec_keys_and_fx6_user_menu(self) -> None:
        for kw in (
            {"claimed_xlr_h1_has_fn_menu_or_rec_keys": True},
            {"fx6_user_menu_max_items": 42},
            {"claimed_fx6_user_menu_lock_in_all_file_or_fn12": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU)

    def test_070_group_c_focus_mode_still_5_states_pass(self) -> None:
        for fm in ("AF_S", "AF_A", "AF_C", "DMF", "MF"):
            ok = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                shoot_mode="PHOTO", focus_mode=fm
            )
            self.assertTrue(ok.passed)

    def test_071_group_c_focus_mode_movie_and_sq_locked_to_afc_mf(self) -> None:
        for sm in ("MOVIE", "S_AND_Q"):
            for ok_fm in ("AF_C", "MF"):
                ok = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                    shoot_mode=sm, focus_mode=ok_fm
                )
                self.assertTrue(ok.passed)
            for bad_fm in ("AF_S", "AF_A", "DMF"):
                bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                    shoot_mode=sm, focus_mode=bad_fm
                )
                self.assertFalse(bad.passed)
                self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_072_group_c_still_afa_requires_pdaf_lens(self) -> None:
        bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            shoot_mode="PHOTO", focus_mode="AF_A", lens_pdaf_supported=False
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_073_group_c_af_w_shutter_and_pre_af_anti_reset_emount(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            af_w_shutter="OFF", pre_af="ON", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_af_w_shutter_after_reset, "OFF")
        self.assertEqual(rst.effective_pre_af_after_reset, "ON")
        ini = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            af_w_shutter="OFF", pre_af="ON", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_af_w_shutter_after_reset, "ON")
        self.assertEqual(ini.effective_pre_af_after_reset, "OFF")
        for kw in (
            {"pre_af": "ON", "lens_is_e_mount": False},
            {"claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_074_group_c_still_af_tracking_sensitivity_resettable_default3(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            still_af_tracking_sensitivity=1, reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_still_af_tracking_sens_after_reset, 3)
        for bad_v in (0, 6):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                still_af_tracking_sensitivity=bad_v
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_075_group_c_movie_af_transition_speed_1_to_7_default5(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            movie_af_transition_speed=2, reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_movie_af_transition_speed_after_reset, 5)
        for bad_v in (0, 8):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                movie_af_transition_speed=bad_v
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_076_group_c_movie_af_subj_shift_default5_responsice_not_3(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            movie_af_subj_shift_sensitivity=1, reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_movie_af_subj_shift_sens_after_reset, 5)
        for kw in (
            {"movie_af_subj_shift_sensitivity": 0},
            {"movie_af_subj_shift_sensitivity": 6},
            {"claimed_movie_af_subj_shift_default_is_3": True},
            {"movie_af_subj_shift_responsice_symbol": "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSIVE"},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)

    def test_077_group_c_focus_area_limit_exact_14_and_min2_switch(self) -> None:
        ok2 = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            focus_area_limit_checked_count=2
        )
        self.assertTrue(ok2.passed)
        for kw in (
            {"focus_area_limit_checked_count": 1},
            {"focus_area_limit_checked_count": 15},
            {"focus_area_limit_items_exposed": ("Wide", "Zone")},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF)

    def test_078_group_c_circ_of_focus_point_orthogonal_anti_reset(self) -> None:
        rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            circ_of_focus_point="CIRCULATE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_circ_of_focus_point_after_reset, "CIRCULATE")
        self.assertEqual(rst.circ_movable_areas_count, 8)
        ini = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            circ_of_focus_point="CIRCULATE", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_circ_of_focus_point_after_reset, "DOES_NOT_CIRCULATE")
        for kw in (
            {"expect_diagonal_focus_circulation": True},
            {"claimed_circ_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF)

    def test_079_group_c_fx6_face_eye_af_3_modes_and_no_still_af(self) -> None:
        for fm in ("FACE_EYE_ONLY_AF", "FACE_EYE_PRIORITY_AF", "OFF"):
            ok = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
                fx6_face_eye_af_mode=fm
            )
            self.assertTrue(ok.passed)
        for kw in (
            {"fx6_face_eye_af_mode": "ANIMAL_EYE_AF"},
            {"claimed_fx6_has_still_af_s_afa_dmf_or_pre_af": True},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF)

    def test_080_group_c_reject_nonzero_slot1_sector_writes(self) -> None:
        bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            slot1_sector_writes=1
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)

    def test_081_group_c_invalid_mymenu_ops_and_camset_op(self) -> None:
        for kw in (
            {"my_menu_ops_exposed": ("Add Item",)},
            {"camset_operation": "FORMAT"},
        ):
            bad = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30)

    def test_082_group_c_focus_mode_reset_per_shoot_mode(self) -> None:
        still_rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            shoot_mode="PHOTO", focus_mode="MF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(still_rst.effective_focus_mode_after_reset, "AF_A")
        movie_rst = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            shoot_mode="MOVIE", focus_mode="MF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(movie_rst.effective_focus_mode_after_reset, "AF_C")

    def test_083_group_c_invalid_focus_mode_and_circ_enum(self) -> None:
        b1 = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            focus_mode="SEMI_MANUAL"
        )
        self.assertFalse(b1.passed)
        self._assert_err(b1, P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE)
        b2 = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            circ_of_focus_point="DIAGONAL"
        )
        self.assertFalse(b2.passed)
        self._assert_err(b2, P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF)

    def test_084_group_c_fn_menu_1_active_slot_passes(self) -> None:
        ok = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
            fn_menu_active_slots=1
        )
        self.assertTrue(ok.passed)

    # ------------------------------------------------------------------
    # 5. Check Group D + Tier-0 — Wave 84.3-84.4 Exposure, Playback & Receipts (24)
    # ------------------------------------------------------------------

    def test_085_group_d_default_pass(self) -> None:
        gd = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed)
        self.assertEqual(gd.exposure_std_adjust_modes_exposed, P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES)
        self.assertEqual(gd.spot_metering_linked_areas, P381_SPOT_METERING_LINKED_EXACT_8_AREAS)
        self.assertEqual(gd.spot_metering_center_locked_areas, P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS)
        self.assertFalse(gd.fx6_ae_shift_menu_supported)
        self.assertEqual(gd.view_mode_options_exposed, P381_VIEW_MODE_EXACT_3_STATES)
        self.assertEqual(gd.display_rotation, "AUTO")
        self.assertEqual(gd.display_rotation_bkid_typo, P381_DISPLAY_ROTATION_BKID_TYPO)
        self.assertEqual(gd.protect_menu_items_exposed, P381_PROTECT_MENU_EXACT_7_ITEMS)
        self.assertEqual(gd.h0_equals_h3_count, 16)

    def test_086_group_d_exposure_comp_still_5ev_movie_2ev_and_lockouts(self) -> None:
        ok_s = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, shoot_mode="PHOTO", exposure_comp_ev=-5.0
        )
        self.assertTrue(ok_s.passed)
        ok_m = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, shoot_mode="MOVIE", exposure_comp_ev=2.0
        )
        self.assertTrue(ok_m.passed)
        for kw in (
            {"shoot_mode": "PHOTO", "exposure_comp_ev": 5.3},
            {"shoot_mode": "MOVIE", "exposure_comp_ev": 2.3},
            {"exposure_mode": "INTELLIGENT_AUTO", "exposure_comp_ev": 0.3},
            {"exposure_mode": "MANUAL_EXPOSURE", "iso_mode": "MANUAL_ISO", "exposure_comp_ev": 0.3},
            {"log_shooting_mode": "CINE_EI", "exposure_comp_ev": 0.3},
            {"log_shooting_mode": "CINE_EI_QUICK", "expect_exposure_comp_active_under_lockout": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116)

    def test_087_group_d_exposure_step_anti_reset_and_independent_of_shutter_angle(self) -> None:
        rst = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True,
            exposure_step="0.5EV",
            shutter_mode="ANGLE",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_exposure_step_after_reset, "0.5EV")
        ini = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, exposure_step="0.5EV", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_exposure_step_after_reset, "0.3EV")
        for kw in (
            {"expect_exposure_step_alters_shutter_angle": True},
            {"claimed_exposure_step_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116)

    def test_088_group_d_exposure_std_adjust_all_5_modes_13_steps_anti_reset(self) -> None:
        for mode in P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES:
            ok = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True,
                exposure_std_adjust_mode=mode,
                exposure_std_adjust_sixths=-6,
                reset_action="CAMERA_SETTINGS_RESET",
            )
            self.assertTrue(ok.passed)
            self.assertEqual(ok.effective_exposure_std_adjust_sixths_after_reset, -6)
        for kw in (
            {"exposure_std_adjust_sixths": -7},
            {"exposure_std_adjust_sixths": 7},
            {"claimed_exp_std_adjust_only_4_modes_missing_highlight": True},
            {"claimed_exp_std_adjust_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116)

    def test_089_group_d_ael_w_shutter_still_only_anti_reset(self) -> None:
        rst = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, ael_w_shutter="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertEqual(rst.effective_ael_w_shutter_after_reset, "OFF")
        for kw in (
            {"shoot_mode": "MOVIE", "expect_ael_w_shutter_in_movie_or_sq": True},
            {"claimed_ael_w_shutter_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116)

    def test_090_group_d_spot_metering_8_linked_vs_6_center_locked_g116(self) -> None:
        ok_link = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True,
            spot_metering_point="FOCUS_POINT_LINK",
            spot_metering_focus_area="Tracking: Spot M",
        )
        self.assertTrue(ok_link.passed)
        self.assertTrue(ok_link.spot_metering_linked_active)
        ok_center = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True,
            spot_metering_point="FOCUS_POINT_LINK",
            spot_metering_focus_area="Tracking: Wide",
        )
        self.assertTrue(ok_center.passed)
        self.assertFalse(ok_center.spot_metering_linked_active)
        for kw in (
            {"expect_spot_metering_follows_moving_tracking_subject": True},
            {"claimed_g116_center_locked_only_3_omitting_tracking": True},
            {"spot_metering_center_locked_areas_exposed": ("Wide", "Zone", "Center Fix")},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116)

    def test_091_group_d_fx6_ae_level_25_steps_zero_ae_shift_and_agc12(self) -> None:
        ok = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, fx6_ae_level_ev=-2.75, fx6_agc_limit_db=36
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"fx6_ae_level_ev": 3.25},
            {"fx6_ae_level_ev": 0.3},
            {"claimed_fx6_has_ae_shift_menu": True},
            {"fx6_agc_limit_db": 4},
            {"fx6_agc_limit_db": 39},
            {"fx6_agc_iso_groups": 6},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12)

    def test_092_group_d_view_mode_exact_3_states_zero_xavc_codec_views(self) -> None:
        for vm in P381_VIEW_MODE_EXACT_3_STATES:
            ok = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, view_mode=vm
            )
            self.assertTrue(ok.passed)
        for kw in (
            {"dormant_xavc_codec_view_mode_requested": True},
            {"view_mode": "XAVC_HS_4K_VIEW"},
            {"view_mode_options_exposed": ("DATE_VIEW", "XAVC_S_4K_VIEW")},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET)

    def test_093_group_d_display_rotation_default_auto_and_rotatiton_typo(self) -> None:
        ini = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, display_rotation="OFF", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_display_rotation_after_reset, "AUTO")
        for kw in (
            {"claimed_display_rotation_default_is_off": True},
            {"display_rotation_bkid_typo": "BKID_APP_setting_display_rotation"},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET)

    def test_094_group_d_playback_display_options_all_anti_reset(self) -> None:
        rst = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True,
            view_mode="MOVIE_VIEW",
            display_rotation="MANUAL",
            image_index="25_IMAGES",
            display_as_group="ON",
            enlarge_initial_mag="PREVIOUS_MAG",
            enlarge_initial_position="CENTER",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_view_mode_after_reset, "MOVIE_VIEW")
        self.assertEqual(rst.effective_display_rotation_after_reset, "MANUAL")
        self.assertEqual(rst.effective_image_index_after_reset, "25_IMAGES")
        self.assertEqual(rst.effective_display_as_group_after_reset, "ON")
        self.assertEqual(rst.effective_enlarge_initial_mag_after_reset, "PREVIOUS_MAG")
        self.assertEqual(rst.effective_enlarge_initial_position_after_reset, "CENTER")
        for kw in (
            {"dormant_image_index_12_or_30_requested": True},
            {"claimed_playback_display_options_wiped_by_camera_reset": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET)

    def test_095_group_d_protect_7_menu_items_zero_single_wave84_g114_erratum(self) -> None:
        for kw in (
            {"claimed_protect_menu_has_single_g114": True},
            {"protect_menu_items_exposed": ("Single", "Multiple Img.")},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30)

    def test_096_group_d_protect_and_rating_slot1_erofs30_vs_slot2_pass(self) -> None:
        ok_s2 = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True,
            protect_write_requested=True,
            rating_write_requested=True,
            rating_stars=5,
            playback_target_slot=2,
        )
        self.assertTrue(ok_s2.passed)
        for kw in (
            {"protect_write_requested": True, "playback_target_slot": 1},
            {"rating_write_requested": True, "rating_stars": 3, "playback_target_slot": 1},
            {"rating_write_requested": True, "rating_stars": 0, "playback_target_slot": 1},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30)
            self.assertTrue(any(f"EROFS={P381_ERRNO_EROFS}" in e for e in bad.errors))

    def test_097_group_d_rating_bounds_and_movie_during_recording_block(self) -> None:
        for kw in (
            {"rating_stars": -1},
            {"rating_stars": 6},
            {"rating_movie_during_recording_requested": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30)

    def test_098_group_d_select_on_cam_and_send_zero_rf_airplane_block_and_fx6_thumbnail(self) -> None:
        for kw in (
            {"select_on_cam_and_send_requested": True},
            {"airplane_mode": "OFF"},
            {"cnct_while_power_off": "ON"},
            {"claimed_fx6_has_5star_rating_or_display_as_group": True},
            {"fx6_clip_flag": "FIVE_STARS"},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL)

    def test_099_group_d_reject_nonzero_telemetry_redlines(self) -> None:
        for kw in (
            {"slot1_sector_writes": 1},
            {"slot1_data_sector_writes": 1},
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"rf_tx_packets": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_100_group_d_reject_live_attach_emmc_and_cross_model_claims(self) -> None:
        for kw in (
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            bad = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_101_physical_dual_media_receipts_verify_while_locking_attach_false(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        rep = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0xA101,
            st_dev_b_override=0xB202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertEqual(
            rep.go_no_go,
            P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertTrue(verify_phase381_report(rep).valid)

    def test_102_reject_same_st_dev_dual_media_receipts(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        rep = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0x7777,
            st_dev_b_override=0x7777,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        self.assertEqual(
            rep.go_no_go,
            P381_GO_NO_GO_BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE,
        )
        self._assert_err(rep, P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_103_reject_single_copy_wrong_size_mismatch_and_corrupt_receipts(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        cases = (
            {"receipt_a_bytes": sim["receipt_a_bytes"], "receipt_b_bytes": None},
            {"receipt_a_bytes": sim["receipt_a_bytes"][:-1], "receipt_b_bytes": sim["receipt_b_bytes"]},
            {
                "receipt_a_bytes": sim["receipt_a_bytes"],
                "receipt_b_bytes": bytes([sim["receipt_b_bytes"][0] ^ 0xFF]) + sim["receipt_b_bytes"][1:],
            },
            {"receipt_a_bytes": b"Z" * 528, "receipt_b_bytes": b"Z" * 528},
        )
        for kw in cases:
            gd = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                st_dev_a_override=1,
                st_dev_b_override=2,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                **kw,
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_104_reject_trivial_or_missing_serial_and_cid(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        for kw in (
            {"body_serial": "00000000", "emmc_cid": sim["emmc_cid"]},
            {"body_serial": "000000000000", "emmc_cid": sim["emmc_cid"]},
            {"body_serial": sim["body_serial"], "emmc_cid": "0" * 32},
            {"body_serial": None, "emmc_cid": sim["emmc_cid"]},
        ):
            gd = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=1,
                st_dev_b_override=2,
                **kw,
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_105_reject_h0_h3_immutability_drift(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        g1 = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

        drifted_h3 = dict(sim["h3_baselines"])
        first_key = next(iter(drifted_h3.keys()))
        drifted_h3[first_key] = "f" * 64
        g2 = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=drifted_h3,
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_106_verify_report_rejects_tampered_sha_and_locked_flags(self) -> None:
        rep = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        d_sha = copy.deepcopy(rep.to_dict())
        d_sha["report_sha256"] = "0" * 64
        self.assertFalse(verify_phase381_report(d_sha).valid)

        for fld in (
            "overall_ready_for_hardware_attach",
            "emmc_writes_authorized",
            "cross_model_flash_authorized",
            "fx3_soft_skin_effect_supported",
            "fx3_focus_bracket_supported",
            "fx6_frame_rec_supported",
            "fx3_power_save_by_monitor_supported",
            "fx3a_ir_or_nfc_supported",
            "fx3_fn_menu_follow_custom_supported",
            "fx6_ae_shift_menu_supported",
        ):
            d = copy.deepcopy(rep.to_dict())
            d[fld] = True
            self.assertFalse(verify_phase381_report(d).valid)

        d_tel = copy.deepcopy(rep.to_dict())
        d_tel["slot1_data_sector_writes"] = 1
        self.assertFalse(verify_phase381_report(d_tel).valid)

    def test_107_receipt_path_loading_and_missing_path_error(self) -> None:
        sim = build_simulated_phase381_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "copy_a.bin"
            pb = Path(tmp) / "copy_b.bin"
            pa.write_bytes(sim["receipt_a_bytes"])
            pb.write_bytes(sim["receipt_b_bytes"])
            gd_ok = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                receipt_a_path=pa,
                receipt_b_path=pb,
                st_dev_a_override=10,
                st_dev_b_override=20,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=build_default_h0_baselines(
                    body_serial=sim["body_serial"], emmc_cid=sim["emmc_cid"]
                ),
            )
            self.assertTrue(gd_ok.passed)
            self.assertTrue(gd_ok.tier0_receipt_verified)

            gd_miss = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
                receipt_a_path=Path(tmp) / "missing_a.bin",
                receipt_b_path=pb,
                st_dev_a_override=10,
                st_dev_b_override=20,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
            )
            self.assertFalse(gd_miss.passed)
            self._assert_err(gd_miss, P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_108_deterministic_json_strips_elapsed_timing_fields(self) -> None:
        rep = evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        raw = rep.to_deterministic_json()
        self.assertNotIn("elapsed_seconds", raw)
        self.assertNotIn("elapsed_ms", raw)
        parsed = json.loads(raw)
        self.assertTrue(verify_phase381_report(parsed).valid)

    # ------------------------------------------------------------------
    # 6. CLI Integration, Short Alias Parity & 4-State Determinism (12)
    # ------------------------------------------------------------------

    def test_109_cli_help_long_and_alias_return_zero(self) -> None:
        p1 = self._run_cli([CLI_CMD_LONG, "--help"])
        self.assertEqual(p1.returncode, 0, msg=p1.stderr)
        p2 = self._run_cli([CLI_CMD_ALIAS, "--help"])
        self.assertEqual(p2.returncode, 0, msg=p2.stderr)
        self.assertIn("--simulate-bench-dry-run", p1.stdout)
        self.assertIn("--camera-revision", p2.stdout)

    def test_110_cli_offline_json_returns_rc2_blocked_awaiting_receipt(self) -> None:
        proc = self._run_cli([CLI_CMD_LONG, "--json"])
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase381_report(data).valid)

    def test_111_cli_dry_run_json_returns_rc0(self) -> None:
        proc = self._run_cli([CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(verify_phase381_report(data).valid)

    def test_112_cli_long_and_short_alias_byte_identical_report_sha256(self) -> None:
        p_long = self._run_cli(
            [CLI_CMD_LONG, "--force-clean-room", "--simulate-bench-dry-run", "--json"]
        )
        p_alias = self._run_cli(
            [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json"]
        )
        self.assertEqual(p_long.returncode, 0, msg=p_long.stderr)
        self.assertEqual(p_alias.returncode, 0, msg=p_alias.stderr)
        d_long = json.loads(p_long.stdout)
        d_alias = json.loads(p_alias.stdout)
        self.assertEqual(d_long["report_sha256"], d_alias["report_sha256"])
        self.assertEqual(p_long.stdout, p_alias.stdout)

    def test_113_cli_force_clean_room_offline_and_dry_run(self) -> None:
        p_off = self._run_cli([CLI_CMD_LONG, "--force-clean-room", "--json"])
        self.assertEqual(p_off.returncode, 2, msg=p_off.stderr)
        d_off = json.loads(p_off.stdout)
        self.assertEqual(d_off["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d_off["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)

        p_dry = self._run_cli(
            [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json"]
        )
        self.assertEqual(p_dry.returncode, 0, msg=p_dry.stderr)
        d_dry = json.loads(p_dry.stdout)
        self.assertEqual(d_dry["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d_dry["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)

    def test_114_cli_summary_output_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "p381.json"
            out_md = Path(tmp) / "p381.md"
            proc = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--output",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", proc.stdout)
            loaded = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase381_report(loaded).valid)
            md = out_md.read_text(encoding="utf-8")
            self.assertIn(loaded["report_sha256"], md)

    def test_115_cli_group_a_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--dormant-soft-skin-effect-requested"],
            ["--dormant-focus-bracket-requested"],
            ["--dormant-fx6-frame-rec-requested"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_a"]["passed"])

    def test_116_cli_group_b_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--hot-pull-np-fz100-requested"],
            ["--dormant-power-save-by-monitor-requested"],
            ["--camera-revision", "ILME_FX3A", "--ir-remote-ctrl", "ON"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_b"]["passed"])

    def test_117_cli_group_c_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--claimed-mymenu-capacity-30-or-36-g98"],
            ["--camset-operation", "SAVE", "--camset-target-slot", "1"],
            ["--claimed-movie-af-subj-shift-default-is-3"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_c"]["passed"])

    def test_118_cli_group_d_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--protect-write-requested", "--playback-target-slot", "1"],
            ["--select-on-cam-and-send-requested"],
            ["--claimed-g116-center-locked-only-3-omitting-tracking"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_d"]["passed"])

    def test_119_cli_donorless_env_deterministic_parity(self) -> None:
        p1 = self._run_cli(
            [CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase381_missing"},
            clear_clean_room_env=True,
        )
        p2 = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase381_missing"},
            clear_clean_room_env=True,
        )
        self.assertEqual(p1.returncode, 0, msg=p1.stderr)
        self.assertEqual(p2.returncode, 0, msg=p2.stderr)
        self.assertEqual(
            json.loads(p1.stdout)["report_sha256"], json.loads(p2.stdout)["report_sha256"]
        )

    def test_120_zero_pyc_under_fx6_on_fx3_closure(self) -> None:
        closure_root = REPO_ROOT / "outputs/fx6-on-fx3-closure"
        pycs = list(closure_root.rglob("*.pyc"))
        self.assertEqual(pycs, [], msg=f"Found unexpected .pyc files: {pycs}")


if __name__ == "__main__":
    unittest.main()
