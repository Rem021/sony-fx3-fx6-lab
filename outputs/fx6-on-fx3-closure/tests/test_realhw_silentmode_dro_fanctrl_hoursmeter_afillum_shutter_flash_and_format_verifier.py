"""Four-mode unit tests (116 cases) for Phase 374
(`preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format`
+ short alias `preflight-phase374`):
25th Physical Bench Readiness Verifier (`25/25` Milestone) across Global Sony Waves 81-82
check groups (`A..D`):
- Group A (Wave 81.1-81.2): Silent Mode exact 2-item `[Target Function Settings]`
  (`Aperture Drive in AF` + `Auto Pixel Mapping`, ALL 3 under Silent Mode `Can be reset`;
  only top-level `Setup -> [Auto Pixel Mapping]` anti-reset; dormant `Shutter When Pwr OFF`
  / `Anti-dust Function` `EOPNOTSUPP=95`; 5-item lockouts) & `[D-Range Optimizer]` (locked
  OFF out-of-box by stock `PP11` / `Log Shooting != Off` / `HLG Still Image = On`; zero
  `Auto HDR` / `Multi Frame NR`) vs FX6 shutterless electronic shutter & `Custom`-only
  `Paint/Look` `Black` & `Knee` (zero UI `Black Gamma`/`White Clip`).
- Group B (Wave 81.3-81.4): Wave 81 `G85` erratum 2-option `[Audio signals]` (`On`/`Off`,
  anti-Camera-Reset), Wave 81 `G82` erratum 4-mode `[Fan Control]` (`Auto`/`Minimum`/
  `Off in Rec`/`Always Off`, zero `Auto1`/`Auto2`, anti-Camera-Reset) vs FX6 3-mode
  `Fan Control` (zero `Max`, zero UI `Always Off`) + `Alarm Level` (`0..7`), `[Version]`
  `/BODYDATA.DAT` & `LENSDATA.DAT`/UUD `NO-GO / BLOCKED` (`Slot 1 EROFS=30`), region-gated
  `[Certification Logo]`, and FX6 `Hours(System)` (permanent) vs `Hours(Reset)` vs FX3 0-UI.
- Group C (Wave 82.1-82.2): Physical front `AF Illuminator` LED (`0.3-3.0 m`, `Can be reset`,
  Still-only, NOT disabled by `Silent Mode=On`), 3 anti-reset Still `Focus -> [AF/MF]`
  controls (`Aperture Drive in AF`, `AF w/ Shutter`, `Pre-AF`) vs FX6 `Push AF Mode`,
  2-option `[Shutter Type]` (`Mechanical Shutter`/`Electronic Shutter`, ZERO `Auto`,
  `1/8000 s` max both, `BULB` mech-only), and anti-reset `[e-Front Curtain Shut.]`
  (`BKID_APP_setting_front_curtaion_shutter`, high-speed bokeh / 3rd-party lens guidance)
  vs FX6 shutterless `ECS`.
- Group D + Tier-0 (Wave 82.3-82.4 + `16/16 H0 == H3`): Wave 82 `G156` erratum strict
  `1/250 s` MI Shoe mechanical X-sync (zero `1/320 s`, zero `1/160 s`/`1/200 s` EFCS,
  `<250V` positive, zero PC sync, Electronic/Silent lockout, HSS `>1/250 s`), anti-reset
  `[Exp.comp.set]`, `[External Flash Set.]` 0 body `BKID` excluded from `CAMSET*.DAT`, zero
  `[Reg. Flash Shooting Set.]`, `[Long Exposure NR]` & 3-level `[High ISO NR]` (`Normal`/
  `Low`/`Off`, never mutates `.ARW`), `[Format]` Quick (`:/AVF_INFO`) vs Full
  (`fsysDepMCmn_EraseDataFull`) `Slot 1 EROFS=30`, and dual-media `528 B FX3RCPT1` Tier-0
  gate (`overall_ready_for_hardware_attach=False`).

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
from fx6_closure.realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier import (  # noqa: E402
    P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS,
    P374_AF_ILLUMINATOR_MODES,
    P374_BODY_UPDATE_FILENAME,
    P374_BOUNDED_DONOR_PATHS,
    P374_CHECK_GROUP_A_ID,
    P374_CHECK_GROUP_B_ID,
    P374_CHECK_GROUP_C_ID,
    P374_CHECK_GROUP_D_ID,
    P374_DRO_MODES,
    P374_EFCS_BKID_TYPO,
    P374_ERRNO_EINVAL,
    P374_ERRNO_EOPNOTSUPP,
    P374_ERRNO_EROFS,
    P374_FULL_FORMAT_ERASE_SYMBOL,
    P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES,
    P374_FX3_FAN_CONTROL_EXACT_4_MODES,
    P374_FX3_FLASH_XSYNC_MAX_DENOM,
    P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS,
    P374_FX6_FAN_CONTROL_EXACT_3_MODES,
    P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR,
    P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY,
    P374_GA_ERR_MODEL_OR_FW_FLOOR,
    P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT,
    P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER,
    P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM,
    P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER,
    P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM,
    P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30,
    P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT,
    P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY,
    P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS,
    P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB,
    P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR,
    P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT,
    P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH,
    P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL,
    P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P374_GO_NO_GO_BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE,
    P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED,
    P374_HEADER_READ_BYTES,
    P374_LENS_UPDATE_FILENAME,
    P374_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P374_QUICK_FORMAT_AVF_INFO_PATH,
    P374_SCHEMA,
    P374_SHUTTER_TYPE_EXACT_2_OPTIONS,
    P374_SILENT_MODE_EXACT_5_LOCKOUTS,
    P374_SILENT_TARGET_EXACT_2_ITEMS,
    P374_SONY_HELP_GUIDE_ID,
    P374_STORAGE_SURFACE_COUNT,
    P374_VERSION,
    P374_VERSION_EXACT_3_ENTITIES,
    PHASE_374_CHECK_GROUP_IDS,
    RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport,
    build_simulated_phase374_tier0_receipts,
    evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook,
    evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter,
    evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs,
    evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0,
    evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight,
    inspect_phase374_donors_bounded,
    render_phase374_markdown,
    run_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight,
    verify_phase374_report,
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
    "fx6_closure.realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier"
)
CLI_CMD_LONG = "preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format"
CLI_CMD_ALIAS = "preflight-phase374"


class TestPhase374Preflight25Verifier(unittest.TestCase):
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

    def test_001_package_exports_and_all_contain_phase374_symbols(self) -> None:
        required = (
            "P374_SCHEMA",
            "P374_VERSION",
            "evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook",
            "evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter",
            "evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs",
            "evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0",
            "evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight",
            "run_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight",
            "verify_phase374_report",
            "render_phase374_markdown",
            "build_simulated_phase374_tier0_receipts",
            "inspect_phase374_donors_bounded",
            "resolve_phase374_donor_file_or_none",
            "RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport",
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
        for prior in ("P371_SCHEMA", "P368_SCHEMA", "verify_phase371_report", "verify_phase368_report"):
            self.assertTrue(hasattr(fx6_closure, prior))

    def test_003_schema_version_and_group_ids(self) -> None:
        self.assertEqual(P374_VERSION, "phase374_v1")
        self.assertEqual(
            P374_SCHEMA,
            "realhw_preflight25_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_format_v1",
        )
        self.assertEqual(P374_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(
            PHASE_374_CHECK_GROUP_IDS,
            (
                P374_CHECK_GROUP_A_ID,
                P374_CHECK_GROUP_B_ID,
                P374_CHECK_GROUP_C_ID,
                P374_CHECK_GROUP_D_ID,
            ),
        )

    def test_004_donor_inspection_force_clean_room(self) -> None:
        res = inspect_phase374_donors_bounded(force_clean_room=True)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.donor_tree_present)
        self.assertEqual(res.donors_checked, len(P374_BOUNDED_DONOR_PATHS))
        self.assertEqual(res.donors_present, 0)
        self.assertEqual(res.bytes_read_total, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_005_donor_inspection_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            res = inspect_phase374_donors_bounded()
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.bytes_read_total, 0)

    def test_006_donor_inspection_force_clean_room_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            res = inspect_phase374_donors_bounded()
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.donors_present, 0)

    def test_007_donor_inspection_nonexistent_work_root(self) -> None:
        res = inspect_phase374_donors_bounded(
            force_clean_room=False,
            work_root=Path("/nonexistent/phase374_missing"),
        )
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.donor_tree_present)
        self.assertEqual(res.bytes_read_total, 0)

    def test_008_donor_inspection_mocked_work_root_none(self) -> None:
        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            res = inspect_phase374_donors_bounded(force_clean_room=False)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.donors_present, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_009_donor_inspection_bounded_o_rdonly_reads_max_64b(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx6_dir = Path(tmp) / "fx6"
            fx3_dir = Path(tmp) / "fx3"
            fx6_dir.mkdir()
            fx3_dir.mkdir()
            (fx6_dir / "appFw.so").write_bytes(b"\x7fELF" + b"6" * 512)
            (fx3_dir / "appFw.so").write_bytes(b"\x7fELF" + b"3" * 512)
            res = inspect_phase374_donors_bounded(
                force_clean_room=False,
                work_root=Path("/nonexistent/phase374_missing"),
                fx6_lib_dir=fx6_dir,
                fx3_modules_dir=fx3_dir,
            )
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(res.donor_tree_present)
        self.assertEqual(res.donors_present, 2)
        self.assertEqual(res.bytes_read_total, 2 * P374_HEADER_READ_BYTES)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_010_default_offline_preflight_blocks_awaiting_tier0_receipt(self) -> None:
        rep = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            force_clean_room=True
        )
        self.assertIsInstance(
            rep, RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport
        )
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.overall_status, P374_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase374_report(rep).valid)

    def test_011_dry_run_preflight_passes_deterministically(self) -> None:
        r1 = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        r2 = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        self.assertEqual(r1.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(r1.check_groups_passed, 4)
        self.assertEqual(r1.h0_equals_h3_count, P374_STORAGE_SURFACE_COUNT)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertFalse(r1.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase374_report(r1).valid)

    def test_012_run_alias_and_markdown_renderer(self) -> None:
        r1 = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        r2 = run_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase374_markdown(r1)
        self.assertIn("Phase 374", md)
        self.assertIn("25/25", md)
        self.assertIn(r1.report_sha256, md)

    # ------------------------------------------------------------------
    # 2. Check Group A — Wave 81.1-81.2 Silent Mode Target-2 & DRO (22)
    # ------------------------------------------------------------------

    def test_013_group_a_default_pass(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook()
        self.assertTrue(ga.passed)
        self.assertEqual(ga.silent_target_items_exposed, P374_SILENT_TARGET_EXACT_2_ITEMS)
        self.assertEqual(ga.silent_mode_lockouts_enforced, P374_SILENT_MODE_EXACT_5_LOCKOUTS)
        self.assertTrue(ga.dro_locked_off_by_pp_log_or_hlg)
        self.assertEqual(ga.effective_dro_mode, "OFF")
        self.assertFalse(ga.fx3_auto_hdr_supported)
        self.assertFalse(ga.fx3_multi_frame_nr_supported)
        self.assertFalse(ga.fx3_shutter_when_pwr_off_supported)

    def test_014_group_a_reject_wrong_model_id(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            body_model_id=0x91030099
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_015_group_a_reject_fw_below_7_02_or_malformed(self) -> None:
        for fw in ("7.01", "6.00", "7.x"):
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(body_fw=fw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P374_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_016_group_a_reject_wrong_help_guide_id(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            sony_help_guide_id="ilc/9999"
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_017_group_a_reject_invalid_enums(self) -> None:
        for kw in (
            {"shoot_mode": "TIMELAPSE"},
            {"log_shooting_mode": "SLOG2"},
            {"reset_action": "FACTORY_NUKE"},
            {"hlg_still_image": "AUTO"},
        ):
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P374_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_018_group_a_reject_non_exact_2_target_function_items(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            silent_target_items_exposed=(
                "Aperture Drive in AF",
                "Auto Pixel Mapping",
                "Shutter When Pwr OFF",
            )
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER)

    def test_019_group_a_reject_dormant_shutter_when_pwr_off(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            dormant_silent_target_item_requested="Shutter When Pwr OFF"
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER)
        self.assertTrue(any(f"EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP}" in e for e in ga.errors))

    def test_020_group_a_reject_dormant_antidust_function(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            dormant_silent_target_item_requested="Anti-dust Function"
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER)

    def test_021_group_a_silent_target_aperture_modes_and_invalid(self) -> None:
        for mode in ("STANDARD", "SILENT_PRIORITY", "NOT_TARGET"):
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
                silent_target_aperture_drive=mode
            )
            self.assertTrue(ga.passed)
        bad = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            silent_target_aperture_drive="FOCUS_PRIORITY"
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER)

    def test_022_group_a_silent_target_auto_pixel_map_shutdown_click_warning(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            silent_mode="ON",
            silent_target_auto_pixel_mapping="NOT_TARGET",
            setup_auto_pixel_mapping="ON",
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.shutdown_pixel_map_shutter_click_possible)
        self.assertTrue(len(ga.warnings) >= 1)

    def test_023_group_a_reset_boundary_all3_silent_reset_while_setup_apm_survives(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            reset_action="CAMERA_SETTINGS_RESET",
            silent_mode="ON",
            silent_target_aperture_drive="SILENT_PRIORITY",
            silent_target_auto_pixel_mapping="NOT_TARGET",
            setup_auto_pixel_mapping="OFF",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_silent_mode_after_reset, "OFF")
        self.assertEqual(ga.effective_silent_target_aperture_after_reset, "STANDARD")
        self.assertEqual(ga.effective_silent_target_auto_pixel_map_after_reset, "OFF")
        # Top-level Setup -> [Auto Pixel Mapping] resists Camera Settings Reset
        self.assertEqual(ga.effective_setup_auto_pixel_mapping_after_reset, "OFF")

    def test_024_group_a_reject_inverted_silent_and_setup_apm_reset_claims(self) -> None:
        g1 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            claimed_silent_mode_or_target2_resists_camera_reset=True
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT)
        g2 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            claimed_setup_auto_pixel_mapping_wiped_by_camera_reset=True
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT)

    def test_025_group_a_setup_auto_pixel_mapping_resets_only_on_initialize(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            reset_action="INITIALIZE",
            setup_auto_pixel_mapping="OFF",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_setup_auto_pixel_mapping_after_reset, "ON")

    def test_026_group_a_silent_mode_5_item_lockout_enforcement(self) -> None:
        g1 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            silent_mode="ON",
            expect_silent_lockout_feature_active=True,
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT)
        g2 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            silent_mode_lockouts_enforced=("FLASH_SHOOTING", "BULB")
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT)

    def test_027_group_a_dro_unlocked_when_pp_off_log_off_hlg_off(self) -> None:
        for mode in P374_DRO_MODES:
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
                picture_profile="OFF",
                log_shooting_mode="OFF",
                hlg_still_image="OFF",
                dro_mode=mode,
            )
            self.assertTrue(ga.passed, msg=f"DRO mode {mode} should pass when unlocked")
            self.assertFalse(ga.dro_locked_off_by_pp_log_or_hlg)
            self.assertEqual(ga.effective_dro_mode, mode)

    def test_028_group_a_dro_locked_off_out_of_box_by_stock_pp11(self) -> None:
        g1 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            picture_profile="PP11", dro_mode="AUTO"
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)
        g2 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            picture_profile="PP11",
            dro_mode="OFF",
            expect_dro_active_under_pp11_log_or_hlg=True,
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)

    def test_029_group_a_dro_and_dro_bracket_locked_by_log_and_hlg(self) -> None:
        g1 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            picture_profile="OFF", log_shooting_mode="CINE_EI", dro_mode="LV3"
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)
        g2 = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            picture_profile="OFF", hlg_still_image="ON", dro_mode="OFF", dro_bracket_mode="HI"
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)

    def test_030_group_a_dro_can_be_reset_under_camera_reset(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            picture_profile="OFF",
            dro_mode="LV5",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.effective_dro_after_reset, "AUTO")
        bad = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            claimed_dro_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)

    def test_031_group_a_reject_dormant_auto_hdr_and_multi_frame_nr(self) -> None:
        for kw in (
            {"dormant_auto_hdr_requested": True},
            {"dormant_multi_frame_nr_requested": True},
            {"claimed_fx3_has_auto_hdr_or_mfnr": True},
        ):
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR)

    def test_032_group_a_reject_fx6_mechanical_shutter_or_silent_mode_claim(self) -> None:
        ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            claimed_fx6_has_mech_shutter_or_silent_mode=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY)

    def test_033_group_a_fx6_paint_look_custom_only_and_knee_black_bounds(self) -> None:
        ok_cine = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
            fx6_shooting_mode="CINE_EI", fx6_paint_look_active=False
        )
        self.assertTrue(ok_cine.passed)
        for kw in (
            {"fx6_shooting_mode": "CINE_EI", "fx6_paint_look_active": True},
            {"fx6_knee_point_pct": 74},
            {"fx6_knee_point_pct": 110},
            {"fx6_knee_slope": 100},
            {"fx6_master_black": -100.0},
        ):
            bad = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY)

    def test_034_group_a_reject_fx6_dormant_black_gamma_and_white_clip(self) -> None:
        for kw in (
            {"dormant_fx6_paint_item_requested": "BLACK_GAMMA"},
            {"dormant_fx6_paint_item_requested": "WHITE_CLIP"},
            {"claimed_fx6_ui_has_black_gamma_or_white_clip": True},
        ):
            ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY)

    # ------------------------------------------------------------------
    # 3. Check Group B — Wave 81.3-81.4 Audio, Fan 4-vs-3, Version & Hours (22)
    # ------------------------------------------------------------------

    def test_035_group_b_default_pass(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter()
        self.assertTrue(gb.passed)
        self.assertEqual(gb.audio_signals_options_exposed, P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES)
        self.assertEqual(gb.fx3_fan_control_options_exposed, P374_FX3_FAN_CONTROL_EXACT_4_MODES)
        self.assertEqual(gb.fx6_fan_control_options_exposed, P374_FX6_FAN_CONTROL_EXACT_3_MODES)
        self.assertEqual(gb.version_entities_exposed, P374_VERSION_EXACT_3_ENTITIES)
        self.assertFalse(gb.fx3_hours_meter_ui_exposed)

    def test_036_group_b_wave81_g85_erratum_reject_dormant_audio_signals(self) -> None:
        for bad_opt in ("ON_ALL", "ON_SHUTTER_ONLY", "ON_ESHUTTER_ONLY"):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                dormant_audio_signals_g85_mode_requested=bad_opt
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM)
        bad_list = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            audio_signals_options_exposed=("ON_ALL", "ON_SHUTTER_ONLY", "OFF")
        )
        self.assertFalse(bad_list.passed)
        self._assert_err(bad_list, P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM)

    def test_037_group_b_audio_signals_anti_camera_reset(self) -> None:
        gb_rst = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            audio_signals="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gb_rst.passed)
        self.assertEqual(gb_rst.effective_audio_signals_after_reset, "OFF")
        gb_init = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            audio_signals="OFF", reset_action="INITIALIZE"
        )
        self.assertEqual(gb_init.effective_audio_signals_after_reset, "ON")
        bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            claimed_audio_signals_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM)

    def test_038_group_b_silent_mode_mutes_audio_signals(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            silent_mode="ON", audio_signals="ON"
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_audio_signals, "OFF")
        bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            silent_mode="ON", expect_audio_signals_audible_under_silent_mode=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM)

    def test_039_group_b_fx3_fan_control_exact_4_modes(self) -> None:
        for mode in P374_FX3_FAN_CONTROL_EXACT_4_MODES:
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                fx3_fan_control=mode
            )
            self.assertTrue(gb.passed, msg=f"FX3 fan mode {mode} should be valid")

    def test_040_group_b_wave81_g82_erratum_reject_auto1_auto2_max(self) -> None:
        for bad_mode in ("AUTO1", "AUTO2", "MAX"):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                dormant_fx3_fan_g82_mode_requested=bad_mode
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)
            self.assertTrue(any(f"EINVAL={P374_ERRNO_EINVAL}" in e for e in gb.errors))
        bad_list = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx3_fan_control_options_exposed=("AUTO1", "AUTO2", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF")
        )
        self.assertFalse(bad_list.passed)
        self._assert_err(bad_list, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)

    def test_041_group_b_fan_control_and_auto_temp_anti_camera_reset(self) -> None:
        gb_rst = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx3_fan_control="OFF_IN_REC",
            auto_power_off_temp="HIGH",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(gb_rst.passed)
        self.assertEqual(gb_rst.effective_fx3_fan_control_after_reset, "OFF_IN_REC")
        self.assertEqual(gb_rst.effective_auto_power_off_temp_after_reset, "HIGH")
        gb_init = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx3_fan_control="OFF_IN_REC",
            auto_power_off_temp="HIGH",
            reset_action="INITIALIZE",
        )
        self.assertEqual(gb_init.effective_fx3_fan_control_after_reset, "AUTO")
        self.assertEqual(gb_init.effective_auto_power_off_temp_after_reset, "STANDARD")
        bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            claimed_fan_or_autotemp_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)

    def test_042_group_b_sustained_bench_recording_always_off_blocked(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx3_fan_control="ALWAYS_OFF",
            sustained_bench_recording_under_always_off=True,
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)

    def test_043_group_b_fx6_fan_control_exact_3_modes_zero_max_zero_always_off(self) -> None:
        for mode in P374_FX6_FAN_CONTROL_EXACT_3_MODES:
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                fx6_fan_control=mode
            )
            self.assertTrue(gb.passed)
        for kw in (
            {"fx6_fan_control": "ALWAYS_OFF"},
            {"fx6_fan_control": "MAX"},
            {"dormant_fx6_fan_mode_requested": "MAX"},
            {"dormant_fx6_fan_mode_requested": "ALWAYS_OFF"},
            {"claimed_fx6_fan_has_max_or_ui_always_off": True},
        ):
            bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)

    def test_044_group_b_fx6_alarm_level_bounds(self) -> None:
        for lvl in (0, 4, 7):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                fx6_alarm_level=lvl
            )
            self.assertTrue(gb.passed)
        for bad_lvl in (-1, 8):
            bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
                fx6_alarm_level=bad_lvl
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM)

    def test_045_group_b_version_entities_and_dat_filenames(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter()
        self.assertEqual(gb.body_update_filename, P374_BODY_UPDATE_FILENAME)
        self.assertEqual(gb.lens_update_filename, P374_LENS_UPDATE_FILENAME)
        bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            version_entities_exposed=("Body", "MI Shoe")
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)

    def test_046_group_b_block_bodydata_dat_update_nogo(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            bodydata_dat_update_requested=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)
        self.assertTrue(any(f"EROFS={P374_ERRNO_EROFS}" in e for e in gb.errors))

    def test_047_group_b_block_lensdata_dat_update_nogo(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            lensdata_dat_update_requested=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)

    def test_048_group_b_block_usb_uud_lens_update_nogo(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            usb_uud_lens_update_requested=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)

    def test_049_group_b_block_fx6_slot_b_and_claimed_lens_safe(self) -> None:
        for kw in (
            {"fx6_slot_b_version_up_requested": True},
            {"claimed_lens_update_safe_on_tier0_bench": True},
        ):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)

    def test_050_group_b_block_nonzero_slot1_sector_writes(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            slot1_sector_writes=1
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30)

    def test_051_group_b_cert_logo_region_gate(self) -> None:
        jp = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            cert_logo_region="JP_DOMESTIC"
        )
        self.assertTrue(jp.passed)
        self.assertTrue(jp.cert_logo_visible)
        us = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            cert_logo_region="US_EU_INTL"
        )
        self.assertTrue(us.passed)
        self.assertFalse(us.cert_logo_visible)
        bad = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            cert_logo_region="US_EU_INTL", expect_cert_logo_visible_in_us_eu=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER)

    def test_052_group_b_fx6_hours_meter_reset_clears_only_reset_counter(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx6_hours_system=350,
            fx6_hours_reset=42,
            fx6_hours_meter_reset_action="HOURS_METER_RESET",
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_fx6_hours_system, 350)
        self.assertEqual(gb.effective_fx6_hours_reset, 0)

    def test_053_group_b_fx6_hours_system_survives_all_reset(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            fx6_hours_system=500,
            fx6_hours_reset=20,
            fx6_hours_meter_reset_action="ALL_RESET",
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_fx6_hours_system, 500)

    def test_054_group_b_reject_fx6_hours_system_reset_and_all_file_claims(self) -> None:
        for kw in (
            {"claimed_fx6_hours_system_resettable": True},
            {"claimed_fx6_hours_saved_in_all_file": True},
        ):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER)

    def test_055_group_b_reject_invalid_fx6_hours_counters(self) -> None:
        for kw in (
            {"fx6_hours_system": 10, "fx6_hours_reset": 20},
            {"fx6_hours_system": -1, "fx6_hours_reset": 0},
        ):
            gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER)

    def test_056_group_b_reject_fx3_hours_meter_ui_claim(self) -> None:
        gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
            claimed_fx3_exposes_hours_meter_ui=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER)

    # ------------------------------------------------------------------
    # 4. Check Group C — Wave 82.1-82.2 AF Illuminator, AF Triad, Shutter2, EFCS (22)
    # ------------------------------------------------------------------

    def test_057_group_c_default_pass(self) -> None:
        gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs()
        self.assertTrue(gc.passed)
        self.assertTrue(gc.fx3_physical_af_illuminator_led_present)
        self.assertTrue(gc.af_illuminator_allowed_under_silent_mode)
        self.assertEqual(gc.focus_af_triad_items, P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS)
        self.assertEqual(gc.shutter_type_options_exposed, P374_SHUTTER_TYPE_EXACT_2_OPTIONS)
        self.assertFalse(gc.fx3_shutter_type_auto_supported)
        self.assertEqual(gc.efcs_bkid_typo_symbol, P374_EFCS_BKID_TYPO)

    def test_058_group_c_reject_no_af_led_claim_and_distance_bounds(self) -> None:
        for kw in (
            {"claimed_fx3_lacks_physical_af_illuminator_led": True},
            {"af_illuminator_distance_m": 0.2},
            {"af_illuminator_distance_m": 3.5},
        ):
            gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_059_group_c_af_illuminator_not_disabled_by_silent_mode(self) -> None:
        ok = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            silent_mode="ON", af_illuminator="AUTO"
        )
        self.assertTrue(ok.passed)
        self.assertFalse(ok.af_illuminator_locked_out)
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_silent_mode_disables_af_illuminator=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_060_group_c_af_illuminator_can_be_reset(self) -> None:
        ok = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            af_illuminator="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ok.passed)
        self.assertEqual(ok.effective_af_illuminator_after_reset, "AUTO")
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_af_illuminator_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_061_group_c_af_illuminator_locked_out_in_movie_and_sq(self) -> None:
        for mode in ("MOVIE", "S_AND_Q"):
            gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
                shoot_mode=mode, expect_af_illuminator_fires_under_lockout=True
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_062_group_c_af_illuminator_locked_out_in_afc_and_moving_afa(self) -> None:
        g1 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            focus_mode="AF_C", expect_af_illuminator_fires_under_lockout=True
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)
        g2 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            focus_mode="AF_A",
            af_a_subject_moving=True,
            expect_af_illuminator_fires_under_lockout=True,
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_063_group_c_af_illuminator_locked_out_in_focus_mag_and_mount_adaptor(self) -> None:
        for kw in (
            {"focus_magnifier_active": True, "expect_af_illuminator_fires_under_lockout": True},
            {"mount_adaptor_attached": True, "expect_af_illuminator_fires_under_lockout": True},
        ):
            gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT)

    def test_064_group_c_focus_af_triad_resists_camera_reset_resets_on_initialize(self) -> None:
        rst = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            reset_action="CAMERA_SETTINGS_RESET",
            focus_aperture_drive_in_af="FOCUS_PRIORITY",
            af_w_shutter="OFF",
            pre_af="ON",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_focus_aperture_drive_after_reset, "FOCUS_PRIORITY")
        self.assertEqual(rst.effective_af_w_shutter_after_reset, "OFF")
        self.assertEqual(rst.effective_pre_af_after_reset, "ON")
        ini = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            reset_action="INITIALIZE",
            focus_aperture_drive_in_af="FOCUS_PRIORITY",
            af_w_shutter="OFF",
            pre_af="ON",
        )
        self.assertEqual(ini.effective_focus_aperture_drive_after_reset, "STANDARD")
        self.assertEqual(ini.effective_af_w_shutter_after_reset, "ON")
        self.assertEqual(ini.effective_pre_af_after_reset, "OFF")

    def test_065_group_c_reject_focus_af_triad_reset_claim_and_contrast_silent_target(self) -> None:
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_focus_af_triad_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY)

    def test_066_group_c_reject_focus_af_triad_in_movie_or_sq(self) -> None:
        for mode in ("MOVIE", "S_AND_Q"):
            bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
                shoot_mode=mode, expect_focus_af_triad_active_in_movie_or_sq=True
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY)

    def test_067_group_c_pre_af_requires_lens_support(self) -> None:
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            pre_af="ON", lens_pre_af_support=False
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY)

    def test_068_group_c_reject_fx6_af_illuminator_or_half_press_af(self) -> None:
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_fx6_has_af_illuminator_or_half_press_af=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY)

    def test_069_group_c_shutter_type_exact_2_options(self) -> None:
        for st in P374_SHUTTER_TYPE_EXACT_2_OPTIONS:
            gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
                shutter_type=st
            )
            self.assertTrue(gc.passed)

    def test_070_group_c_reject_dormant_shutter_type_auto(self) -> None:
        g1 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            dormant_shutter_type_auto_requested=True
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)
        g2 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            shutter_type_options_exposed=("AUTO", "MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER")
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)

    def test_071_group_c_shutter_type_can_be_reset(self) -> None:
        ok = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            shutter_type="ELECTRONIC_SHUTTER", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(ok.passed)
        self.assertEqual(ok.effective_shutter_type_after_reset, "MECHANICAL_SHUTTER")
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_shutter_type_resists_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)

    def test_072_group_c_still_max_shutter_8000_both_mech_and_elec(self) -> None:
        for st in P374_SHUTTER_TYPE_EXACT_2_OPTIONS:
            ok = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
                shutter_type=st, still_shutter_denom=8000
            )
            self.assertTrue(ok.passed)
        for bad_d in (0, 16000):
            bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
                still_shutter_denom=bad_d
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)

    def test_073_group_c_bulb_mech_still_only(self) -> None:
        ok = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            shoot_mode="PHOTO", shutter_type="MECHANICAL_SHUTTER", bulb_requested=True
        )
        self.assertTrue(ok.passed)
        for kw in (
            {"shutter_type": "ELECTRONIC_SHUTTER", "bulb_requested": True},
            {"silent_mode": "ON", "bulb_requested": True},
            {"shoot_mode": "MOVIE", "bulb_requested": True},
        ):
            bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(**kw)
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)

    def test_074_group_c_reject_movie_using_still_shutter_type(self) -> None:
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            expect_movie_uses_still_shutter_type=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB)

    def test_075_group_c_efcs_anti_camera_reset_resets_only_on_initialize(self) -> None:
        rst = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            e_front_curtain_shutter="OFF", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_efcs_after_reset, "OFF")
        ini = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            e_front_curtain_shutter="OFF", reset_action="INITIALIZE"
        )
        self.assertEqual(ini.effective_efcs_after_reset, "ON")
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_efcs_wiped_by_camera_reset=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS)

    def test_076_group_c_efcs_bkid_typo_and_eshutter_lockout(self) -> None:
        g1 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            efcs_bkid_typo_symbol="BKID_APP_setting_front_curtain_shutter"
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS)
        g2 = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            shutter_type="ELECTRONIC_SHUTTER",
            expect_efcs_active_under_eshutter_or_silent=True,
        )
        self.assertFalse(g2.passed)
        self._assert_err(g2, P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS)

    def test_077_group_c_efcs_high_speed_bokeh_and_third_party_lens_guidance(self) -> None:
        warn_res = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            e_front_curtain_shutter="ON",
            still_shutter_denom=4000,
            aperture_f_number=1.4,
        )
        self.assertTrue(warn_res.passed)
        self.assertTrue(warn_res.efcs_bokeh_clipping_guidance_triggered)
        self.assertTrue(len(warn_res.warnings) >= 1)
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            e_front_curtain_shutter="ON",
            third_party_lens_attached=True,
            expect_no_bokeh_clipping_with_efcs_high_speed=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS)

    def test_078_group_c_reject_fx6_mechanical_shutter_or_efcs_claim(self) -> None:
        bad = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
            claimed_fx6_has_mechanical_shutter_or_efcs=True
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS)

    # ------------------------------------------------------------------
    # 5. Check Group D + Tier-0 — Wave 82.3-82.4 Flash, NR, Format & Receipts (26)
    # ------------------------------------------------------------------

    def test_079_group_d_default_pass(self) -> None:
        gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed)
        self.assertEqual(gd.flash_xsync_max_denom, P374_FX3_FLASH_XSYNC_MAX_DENOM)
        self.assertFalse(gd.fx3_pc_sync_terminal_present)
        self.assertEqual(gd.external_flash_body_bkid_count, 0)
        self.assertTrue(gd.external_flash_excluded_from_camset)
        self.assertFalse(gd.fx3_reg_flash_shooting_set_supported)
        self.assertEqual(gd.high_iso_nr_options_exposed, P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS)
        self.assertFalse(gd.high_iso_nr_mutates_arw_raw)
        self.assertEqual(gd.h0_equals_h3_count, 16)

    def test_080_group_d_flash_mechanical_250_hss_and_4000_banding_warning(self) -> None:
        ok250 = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            flash_firing_requested=True,
            flash_sync_shutter_denom=250,
        )
        self.assertTrue(ok250.passed)
        bad500 = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            flash_firing_requested=True,
            flash_sync_shutter_denom=500,
            flash_hss_enabled=False,
        )
        self.assertFalse(bad500.passed)
        self._assert_err(bad500, P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT)
        hss8000 = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            flash_firing_requested=True,
            flash_sync_shutter_denom=8000,
            flash_hss_enabled=True,
        )
        self.assertTrue(hss8000.passed)
        self.assertTrue(hss8000.flash_hss_banding_warning)

    def test_081_group_d_wave82_g156_erratum_reject_320_160_200_xsync(self) -> None:
        for kw in (
            {"flash_xsync_max_denom": 320},
            {"flash_xsync_max_denom": 160},
            {"flash_xsync_max_denom": 200},
            {"claimed_flash_xsync_320_apsc_or_160_200_efcs_g156": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT)

    def test_082_group_d_flash_locked_out_in_eshutter_silent_and_movie(self) -> None:
        for kw in (
            {"shutter_type": "ELECTRONIC_SHUTTER", "flash_firing_requested": True},
            {"silent_mode": "ON", "flash_firing_requested": True},
            {"shoot_mode": "MOVIE", "flash_firing_requested": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT)

    def test_083_group_d_reject_high_voltage_or_negative_polarity_flash(self) -> None:
        for kw in (
            {"flash_trigger_voltage_v": 250.0},
            {"flash_trigger_voltage_v": 300.0},
            {"flash_negative_polarity": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT)

    def test_084_group_d_reject_pc_sync_terminal_and_reg_flash_shooting_set(self) -> None:
        for kw in (
            {"claimed_fx3_has_pc_sync_terminal": True},
            {"dormant_reg_flash_shooting_set_requested": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT)

    def test_085_group_d_exp_comp_set_anti_camera_reset(self) -> None:
        rst = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            exp_comp_set="AMBIENT_ONLY",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_exp_comp_set_after_reset, "AMBIENT_ONLY")
        ini = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            exp_comp_set="AMBIENT_ONLY",
            reset_action="INITIALIZE",
        )
        self.assertEqual(ini.effective_exp_comp_set_after_reset, "AMBIENT_AND_FLASH")
        bad = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            claimed_exp_comp_set_wiped_by_camera_reset=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR)

    def test_086_group_d_external_flash_set_zero_bkid_and_camset_exclusion(self) -> None:
        for kw in (
            {"external_flash_body_bkid_count": 1},
            {"claimed_external_flash_saved_in_camset_or_resettable": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR)

    def test_087_group_d_reject_fx6_flash_sync_or_fbr_confusion(self) -> None:
        gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            claimed_fx6_has_flash_sync_or_fbr_is_sync=True,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR)

    def test_088_group_d_long_exposure_nr_reset_and_lockouts(self) -> None:
        rst = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            long_exposure_nr="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(rst.passed)
        self.assertEqual(rst.effective_long_exposure_nr_after_reset, "ON")
        for kw in (
            {"shutter_type": "ELECTRONIC_SHUTTER", "expect_long_exp_nr_active_under_lockout": True},
            {"still_drive_mode": "CONT_SHOOTING", "expect_long_exp_nr_active_under_lockout": True},
            {"still_drive_mode": "CONT_BRACKET", "expect_long_exp_nr_active_under_lockout": True},
            {"claimed_long_exp_nr_resists_camera_reset": True},
        ):
            bad = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL)

    def test_089_group_d_high_iso_nr_exact_3_levels_and_arw_immutability(self) -> None:
        for lvl in P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS:
            ok = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, high_iso_nr=lvl
            )
            self.assertTrue(ok.passed)
        for kw in (
            {"dormant_high_iso_nr_high_requested": True},
            {"high_iso_nr_options_exposed": ("HIGH", "NORMAL", "LOW", "OFF")},
            {"claimed_high_iso_nr_mutates_arw_raw": True},
        ):
            bad = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(bad.passed)
            self._assert_err(bad, P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL)

    def test_090_group_d_fx6_noise_suppression_levels(self) -> None:
        for lvl in ("LOW", "MID", "HIGH"):
            ok = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, fx6_noise_suppression_level=lvl
            )
            self.assertTrue(ok.passed)
        bad = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True, fx6_noise_suppression_level="ULTRA"
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL)

    def test_091_group_d_format_quick_and_full_on_scratch_slot2_pass(self) -> None:
        for mode in ("QUICK_FORMAT", "FULL_FORMAT"):
            for bus in ("SDXC_MMCB", "CFEXPRESS_TYPE_A_NVME"):
                gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                    simulate_bench_dry_run=True,
                    format_mode=mode,
                    format_target_slot=2,
                    format_media_bus=bus,
                )
                self.assertTrue(gd.passed)
                self.assertEqual(gd.slot1_data_sector_writes, 0)

    def test_092_group_d_quick_format_slot1_blocked_erofs30(self) -> None:
        gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            format_mode="QUICK_FORMAT",
            format_target_slot=1,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH)
        self.assertTrue(any(f"EROFS={P374_ERRNO_EROFS}" in e for e in gd.errors))

    def test_093_group_d_full_format_slot1_blocked_erofs30(self) -> None:
        gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True,
            format_mode="FULL_FORMAT",
            format_target_slot=1,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH)
        self.assertTrue(any(f"EROFS={P374_ERRNO_EROFS}" in e for e in gd.errors))

    def test_094_group_d_slot1_hotkey_avf_info_and_discard_trim_blocked_erofs30(self) -> None:
        for kw in (
            {"format_hotkey_menu_delete_2s_slot": 1},
            {"avf_info_rebuild_slot1_requested": True},
            {"full_format_discard_trim_slot1_requested": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH)

    def test_095_group_d_format_symbols_and_irreversible_cancel_rule(self) -> None:
        for kw in (
            {"quick_format_avf_info_path": ":/OTHER"},
            {"full_format_erase_symbol": "fsysQuickZero"},
            {"claimed_full_format_cancel_restores_erased_data": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH)

    def test_096_group_d_reject_nonzero_telemetry_redlines(self) -> None:
        for kw in (
            {"slot1_sector_writes": 1},
            {"slot1_data_sector_writes": 1},
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"rf_tx_packets": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_097_group_d_reject_live_attach_emmc_and_cross_model_claims(self) -> None:
        for kw in (
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_098_physical_dual_media_receipts_verify_while_locking_attach_false(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
        rep = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
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
            P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertTrue(verify_phase374_report(rep).valid)

    def test_099_reject_same_st_dev_dual_media_receipts(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
        rep = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
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
            P374_GO_NO_GO_BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE,
        )
        self._assert_err(rep, P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_100_reject_single_copy_wrong_size_mismatch_and_corrupt_receipts(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
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
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                st_dev_a_override=1,
                st_dev_b_override=2,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                **kw,
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_101_reject_trivial_or_missing_serial_and_cid(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
        for kw in (
            {"body_serial": "00000000", "emmc_cid": sim["emmc_cid"]},
            {"body_serial": "000000000000", "emmc_cid": sim["emmc_cid"]},
            {"body_serial": sim["body_serial"], "emmc_cid": "0" * 32},
            {"body_serial": None, "emmc_cid": sim["emmc_cid"]},
        ):
            gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=1,
                st_dev_b_override=2,
                **kw,
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_102_reject_h0_h3_immutability_drift(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
        g1 = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(g1.passed)
        self._assert_err(g1, P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

        drifted_h3 = dict(sim["h3_baselines"])
        first_key = next(iter(drifted_h3.keys()))
        drifted_h3[first_key] = "f" * 64
        g2 = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
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
        self._assert_err(g2, P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_103_verify_report_rejects_tampered_sha_and_locked_flags(self) -> None:
        rep = evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
            simulate_bench_dry_run=True, force_clean_room=True
        )
        d_sha = copy.deepcopy(rep.to_dict())
        d_sha["report_sha256"] = "0" * 64
        self.assertFalse(verify_phase374_report(d_sha).valid)

        for fld in (
            "overall_ready_for_hardware_attach",
            "emmc_writes_authorized",
            "cross_model_flash_authorized",
            "fx3_shutter_type_auto_supported",
            "lens_or_body_dat_update_authorized",
        ):
            d = copy.deepcopy(rep.to_dict())
            d[fld] = True
            self.assertFalse(verify_phase374_report(d).valid)

        d_tel = copy.deepcopy(rep.to_dict())
        d_tel["slot1_data_sector_writes"] = 1
        self.assertFalse(verify_phase374_report(d_tel).valid)

    def test_104_receipt_path_loading_and_missing_path_error(self) -> None:
        sim = build_simulated_phase374_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "copy_a.bin"
            pb = Path(tmp) / "copy_b.bin"
            pa.write_bytes(sim["receipt_a_bytes"])
            pb.write_bytes(sim["receipt_b_bytes"])
            gd_ok = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
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

            gd_miss = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
                receipt_a_path=Path(tmp) / "missing_a.bin",
                receipt_b_path=pb,
                st_dev_a_override=10,
                st_dev_b_override=20,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
            )
            self.assertFalse(gd_miss.passed)
            self._assert_err(gd_miss, P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    # ------------------------------------------------------------------
    # 6. CLI Integration, Short Alias Parity & 4-State Determinism (12)
    # ------------------------------------------------------------------

    def test_105_cli_help_long_and_alias_return_zero(self) -> None:
        p1 = self._run_cli([CLI_CMD_LONG, "--help"])
        self.assertEqual(p1.returncode, 0, msg=p1.stderr)
        p2 = self._run_cli([CLI_CMD_ALIAS, "--help"])
        self.assertEqual(p2.returncode, 0, msg=p2.stderr)
        self.assertIn("--simulate-bench-dry-run", p1.stdout)
        self.assertIn("--format-mode", p2.stdout)

    def test_106_cli_offline_json_returns_rc2_blocked_awaiting_receipt(self) -> None:
        proc = self._run_cli([CLI_CMD_LONG, "--json"])
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertTrue(verify_phase374_report(data).valid)

    def test_107_cli_dry_run_json_returns_rc0(self) -> None:
        proc = self._run_cli([CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertTrue(verify_phase374_report(data).valid)

    def test_108_cli_long_and_short_alias_byte_identical_report_sha256(self) -> None:
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

    def test_109_cli_force_clean_room_offline_and_dry_run(self) -> None:
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

    def test_110_cli_summary_output_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "p374.json"
            out_md = Path(tmp) / "p374.md"
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
            self.assertTrue(verify_phase374_report(loaded).valid)
            md = out_md.read_text(encoding="utf-8")
            self.assertIn(loaded["report_sha256"], md)

    def test_111_cli_group_a_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--dormant-auto-hdr-requested"],
            ["--dormant-silent-target-item-requested", "Shutter When Pwr OFF"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_a"]["passed"])

    def test_112_cli_group_b_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--dormant-audio-signals-g85-mode-requested", "ON_SHUTTER_ONLY"],
            ["--dormant-fx3-fan-g82-mode-requested", "AUTO1"],
            ["--lensdata-dat-update-requested"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_b"]["passed"])

    def test_113_cli_group_c_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--dormant-shutter-type-auto-requested"],
            ["--claimed-efcs-wiped-by-camera-reset"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_c"]["passed"])

    def test_114_cli_group_d_negative_flags_return_rc2(self) -> None:
        for flag_args in (
            ["--format-mode", "FULL_FORMAT", "--format-target-slot", "1"],
            ["--claimed-flash-xsync-320-apsc-or-160-200-efcs-g156"],
        ):
            proc = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json", *flag_args]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertFalse(data["check_group_d"]["passed"])

    def test_115_cli_donorless_env_deterministic_parity(self) -> None:
        p1 = self._run_cli(
            [CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase374_missing"},
            clear_clean_room_env=True,
        )
        p2 = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase374_missing"},
            clear_clean_room_env=True,
        )
        self.assertEqual(p1.returncode, 0, msg=p1.stderr)
        self.assertEqual(p2.returncode, 0, msg=p2.stderr)
        self.assertEqual(
            json.loads(p1.stdout)["report_sha256"], json.loads(p2.stdout)["report_sha256"]
        )

    def test_116_zero_pyc_under_fx6_on_fx3_closure(self) -> None:
        closure_root = REPO_ROOT / "outputs/fx6-on-fx3-closure"
        pycs = list(closure_root.rglob("*.pyc"))
        self.assertEqual(pycs, [], msg=f"Found unexpected .pyc files: {pycs}")


if __name__ == "__main__":
    unittest.main()
