"""Dual-mode unit tests (100 cases) for Phase 341 (`preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec`):
18th Real-Hardware Physical Bench Readiness Verifier across Global Sony Waves 68-69 check groups (`A..D`)
covering Reset-immune `Setup -> [Area/Date] -> [Area/Date/Time Setting]` (30 `AREA_GMT_*` zones w/
6 half-hour offsets, `[Daylight Savings]` + Sony ELF typo `convert_setting_daylight_saving_to_saylight_saving`,
`Date Format`, soldered >=24h internal RTC battery w/ zero CR2032 vs `FX6 Maintenance > Clock Set`),
Clean-HDMI `[Grid Line Display]` (`Rule of 3rds`/`Square`/`Diag.+Square` passing over HDMI when
`[HDMI Info. Display]=On`) vs Reset-immune Movie/S&Q `[Marker Display]` (`Guideframe`/15-ratio
`Aspect Marker`, 0 px over HDMI), `[Save/Load Settings]` locked strictly to `Slot 1` (`libSaveLoadSettings.so`,
`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, 0 `PRO/CAMERA` hits, 18 exclusions, `FTPSET/%s.DAT`, `Camera Set. Memory`
1..3 vs M1..M4 `CAMPR%02d%c.DAT`, Slot-1 `EROFS=30` firewall) vs FX6 `Project > All File` & dormant
`Reference File`, FX3 zero physical PC Flash Sync terminal (`0 SYNCHRO_TERMINAL*`), `XLR-H1` passive
cold shoe excluding `HVL-LBPC` (`Video Light Mode` 4 modes, `PMIC 5V <= 900 mA`) vs FX6 `TC IN/OUT` BNC
& zero `GENLOCK` BNC (107 dormant symbols), Reset-immune Still-only `Playback -> [Magnification]`
(`playback_zoom_maginify_by_pinch`, `"You cannot enlarge movies."` `EOPNOTSUPP=95`), Still mechanical
`[Anti-flicker Shoot.]` (`100/120 Hz`, Resettable) vs 100% dormant `[Var. Shutter]` & `[Anti-flicker Tv Scan]`
(`EOPNOTSUPP=95`) vs FX6 `ECS` (`23.99..8000 Hz`), Dual-SKU `Network -> [Wi-Fi]` (`WW728473` 2.4+5GHz
vs `WW558244` 2.4GHz-only via `backup_get_wi_fi_frequency_band_dst`, Ver. 7.00+ `WPA2-PSK`/`WPA3-SAE` only,
`[Reset Network Set.]` preserves `[Airplane Mode]=On`, `p12/p13` RF NVS `MS_RDONLY`), front `#5`
`Infrared remote sensor` (vs `#8` AF illuminator, `ILME-FX3A` removal, BT mutex, Power Save bypass,
zero `2.5mm LANC`), factory-default-`On` `[CTRL FOR HDMI]` (`BKID_APP_setting_ctrl_for_hmdi`, 41
`EVENT_INPUT_KEY_CEC_*`, mandatory bench `Off`), and `16/16 H0 == H3` Dual-Media `528 B FX3RCPT1` Tier-0 Gate.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and donorless CI (`work_root=None`) modes with
zero `.pyc` emission, zero persistent writes, and cross-platform CI headroom.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
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
from fx6_closure.realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier import (  # noqa: E402
    P341_ANTI_FLICKER_FREQUENCIES_HZ,
    P341_ANTI_FLICKER_SHOOT_RESID16_HEX,
    P341_AREA_DATE_EXACT_FOUR_ITEMS,
    P341_AREA_DATE_TIME_RESID16_HEX,
    P341_AREA_GMT_THIRTY_ZONES,
    P341_AREA_HALF_HOUR_SIX_ZONES,
    P341_AREA_SETTING_RESID16_HEX,
    P341_ASPECT_MARKER_RATIO_COUNT,
    P341_BOUNDED_DONOR_PATHS,
    P341_CAMERA_SET_MEMORY_BODY_SLOTS,
    P341_CAMERA_SET_MEMORY_CARD_SLOTS,
    P341_CAMPR_CARD_TEMPLATE,
    P341_CAMSET_ALLOWED_SLOT,
    P341_CAMSET_CARD_TEMPLATE,
    P341_CAMSET_EXCLUDED_CATEGORIES,
    P341_CAMSET_MAX_FILES_PER_CARD,
    P341_CAMSET_PRO_CAMERA_FX3_HITS,
    P341_CEC_EVENT_KEY_COUNT,
    P341_CHECK_GROUP_A_ID,
    P341_CHECK_GROUP_B_ID,
    P341_CHECK_GROUP_C_ID,
    P341_CHECK_GROUP_D_ID,
    P341_CTRL_FOR_HDMI_BENCH_REQUIRED,
    P341_CTRL_FOR_HDMI_FACTORY_DEFAULT,
    P341_CTRL_FOR_HDMI_RESID16_HEX,
    P341_CTRL_FOR_HDMI_SONY_TYPO_BKID,
    P341_DATE_FORMAT_RESID16_HEX,
    P341_DATE_TIME_AUTO_SYNC_SONY_TYPO_BKID,
    P341_DAYLIGHT_SAVINGS_RESID16_HEX,
    P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC,
    P341_DORMANT_ANTI_FLICKER_SET_RESID16_HEX,
    P341_DORMANT_ANTI_FLICKER_TV_SCAN_RESID16_HEX,
    P341_DORMANT_VAR_SHUTTER_RESID16_HEX,
    P341_DORMANT_VAR_SHUTTER_SET_RESID16_HEX,
    P341_ERRNO_EOPNOTSUPP,
    P341_ERRNO_EROFS,
    P341_FLASH_MAX_TRIGGER_VOLTAGE_V,
    P341_FLASH_XSYNC_DENOMINATOR,
    P341_FTPSET_CARD_TEMPLATE,
    P341_FX3_2_5MM_LANC_PRESENT,
    P341_FX3_AF_ILLUMINATOR_LAMP_FRONT_INDEX,
    P341_FX3_IR_SENSOR_FRONT_INDEX,
    P341_FX3_MARKER_OUTPUTS_TO_HDMI,
    P341_FX3_SYNC_TERMINAL_PRESENT,
    P341_FX3_SYNCHRO_TERMINAL_SYMBOL_HITS,
    P341_FX6_CLOCK_SET_STEP_MINUTES,
    P341_FX6_ECS_FREQ_MAX_HZ,
    P341_FX6_ECS_FREQ_MIN_HZ,
    P341_FX6_GENLOCK_BNC_PRESENT,
    P341_FX6_GENLOCK_DORMANT_SYMBOL_HITS,
    P341_FX6_REFERENCE_FILE_PRESENT,
    P341_FX6_STANDALONE_DST_SWITCH_PRESENT,
    P341_FX6_VIDEO_LIGHT_SET_THREE_OPTIONS,
    P341_GA_ERR_AREA_DATE_DST_OR_RTC,
    P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI,
    P341_GA_ERR_MODEL_OR_FW_FLOOR,
    P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY,
    P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION,
    P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE,
    P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH,
    P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS,
    P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT,
    P341_GC_ERR_DORMANT_VAR_SHUTTER_OR_TV_SCAN,
    P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY,
    P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE,
    P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK,
    P341_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC,
    P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK,
    P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE,
    P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
    P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE,
    P341_GRID_LINE_DISPLAY_RESID16_HEX,
    P341_GRID_LINE_EXACT_THREE_TYPES,
    P341_GRID_LINE_TYPE_RESID16_HEX,
    P341_GUIDEFRAME_RESID16_HEX,
    P341_IR_REMOTE_CTRL_RESID16_HEX,
    P341_LEGACY_DATE_TIME_SETUP_RESID16_HEX,
    P341_MARKER_DISPLAY_RESID16_HEX,
    P341_MI_SHOE_PMIC_5V_MAX_MA,
    P341_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P341_PB_ENLARGE_IMAGE_RESID16_HEX,
    P341_PB_ENLARGE_INITIAL_MAG_MODES,
    P341_PB_ENLARGE_INITIAL_MAG_RESID16_HEX,
    P341_PB_ENLARGE_INITIAL_POS_MODES,
    P341_PB_ENLARGE_INITIAL_POS_RESID16_HEX,
    P341_PB_MAGNIFY_PINCH_SONY_TYPO_SYMBOL,
    P341_RF_NVS_PARTITIONS,
    P341_RTC_INTERNAL_MIN_CHARGE_HOURS,
    P341_SAVE_LOAD_SETTINGS_RESID16_HEX,
    P341_SCHEMA,
    P341_SONY_HELP_GUIDE_ID,
    P341_STORAGE_SURFACE_COUNT,
    P341_USER_REPLACEABLE_CR2032_SLOT_PRESENT,
    P341_VERSION,
    P341_VIDEO_LIGHT_MODE_FOUR_OPTIONS,
    P341_VIDEO_LIGHT_MODE_RESID16_HEX,
    P341_WIFI_FREQUENCY_BAND_RESID16_HEX,
    P341_WIFI_REMOVED_LEGACY_PROTOCOLS,
    P341_WIFI_SKU_GATING_SYMBOL,
    P341_WIFI_SUPPORTED_SECURITY_PROTOCOLS,
    PHASE341_E_ND_ACTUATOR_TX_COUNT,
    PHASE341_PASSIVE_TX_BYTES_EMITTED,
    PHASE341_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE341_RF_NVS_MUTATION_BYTES,
    PHASE341_SLOT1_DATA_SECTOR_WRITES,
    PHASE341_USB_PACKETS_TRANSMITTED,
    PHASE341_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_341_CHECK_GROUP_IDS,
    PHASE_341_SCHEMA,
    PHASE_341_VERSION,
    _canonical_sha256_dict,
    build_simulated_phase341_tier0_receipts,
    evaluate_p341_check_group_a_area_date_grid_and_marker,
    evaluate_p341_check_group_b_camset_mishoe_and_flash_sync,
    evaluate_p341_check_group_c_pb_magnify_and_antiflicker,
    evaluate_p341_check_group_d_wifi_ir_cec_and_tier0,
    evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight,
    inspect_phase341_donors_bounded,
    render_phase341_markdown,
    resolve_phase341_donor_file_or_none,
    run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight,
    verify_phase341_report,
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
            "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase341Preflight18Verifier(unittest.TestCase):
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
                "run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight",
            )
        )
        self.assertTrue(
            hasattr(
                fx6_closure,
                "evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight",
            )
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase341_report"))
        self.assertTrue(hasattr(fx6_closure, "render_phase341_markdown"))
        self.assertEqual(P341_VERSION, PHASE_341_VERSION)
        self.assertEqual(P341_SCHEMA, PHASE_341_SCHEMA)
        self.assertEqual(P341_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_341_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_341_CHECK_GROUP_IDS,
            (
                P341_CHECK_GROUP_A_ID,
                P341_CHECK_GROUP_B_ID,
                P341_CHECK_GROUP_C_ID,
                P341_CHECK_GROUP_D_ID,
            ),
        )
        self.assertEqual(P341_STORAGE_SURFACE_COUNT, 16)

    def test_02_default_preflight_blocks_awaiting_physical_tier0_receipt(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight()
        self.assertEqual(rep.check_group_count, 4)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertEqual(rep.overall_status, P341_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase341_report(rep).valid)

    def test_03_simulate_bench_dry_run_passes_and_stays_fail_closed(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
        )
        self.assertTrue(rep.simulate_bench_dry_run)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "SIMULATED_BENCH_DRY_RUN")
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.rf_nvs_p12_p13_writes_authorized)
        self.assertEqual(rep.emmc_write_count, 0)
        self.assertEqual(rep.rf_nvs_mutation_bytes, 0)
        self.assertEqual(rep.wireless_rf_packets_emitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertTrue(verify_phase341_report(rep).valid)

    def test_04_recursive_elapsed_seconds_stripping_in_deterministic_json_and_sha256(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
        )
        parsed = json.loads(rep.to_deterministic_json())
        self.assertNotIn("elapsed_seconds", parsed)
        self.assertNotIn("elapsed_seconds", parsed["donor_inspection"])
        d1 = rep.to_dict()
        d2 = copy.deepcopy(d1)
        d2["donor_inspection"]["elapsed_seconds"] = 999.123
        d2["check_group_a"]["nested_elapsed_ms"] = 42.0
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_05_clean_room_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
                simulate_bench_dry_run=True,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.donor_inspection.bytes_read_total, 0)
            self.assertFalse(rep.donor_inspection.donor_tree_present)
            self.assertTrue(verify_phase341_report(rep).valid)

    def test_06_force_clean_room_flag_and_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight()
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.donor_inspection.bytes_read_total, 0)
            self.assertEqual(rep.donor_inspection.raw_firmware_bytes_leaked, 0)
        rep2 = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            force_clean_room=True,
        )
        self.assertEqual(rep2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donorless_work_root_none_safe_fallback(self) -> None:
        self.assertIsNone(resolve_phase341_donor_file_or_none(None, P341_BOUNDED_DONOR_PATHS[0][1]))
        with mock.patch(
            "fx6_closure.realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.iter_work_roots",
            return_value=(),
        ):
            res = inspect_phase341_donors_bounded(force_clean_room=False, work_root=None)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(res.donor_tree_present)
            self.assertEqual(res.bytes_read_total, 0)
            self.assertTrue(res.within_budget)
            rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
                simulate_bench_dry_run=True,
                force_clean_room=False,
                work_root=None,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertTrue(verify_phase341_report(rep).valid)

    def test_08_nonexistent_work_root_fallback(self) -> None:
        missing = Path("/nonexistent/phase341_missing_donor_root")
        self.assertIsNone(resolve_phase341_donor_file_or_none(missing, P341_BOUNDED_DONOR_PATHS[0][1]))
        with mock.patch.dict(os.environ, {"FX3_FX6_MAC_WORK_ROOT": str(missing)}, clear=False):
            res = inspect_phase341_donors_bounded(work_root=missing)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.bytes_read_total, 0)

    def test_09_bounded_donor_inspection_budget_and_synthetic_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _lbl, rel in P341_BOUNDED_DONOR_PATHS:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x7fELF" + b"\x00" * 256)
            res = inspect_phase341_donors_bounded(force_clean_room=False, work_root=root)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(res.donor_tree_present)
            self.assertTrue(res.fx3_appfw_present)
            self.assertTrue(res.fx6_appfw_present)
            self.assertTrue(res.fx3_libsaveloadsettings_present)
            self.assertEqual(res.bytes_read_total, 64 * len(P341_BOUNDED_DONOR_PATHS))
            self.assertTrue(res.within_budget)
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_10_verify_report_rejects_tampered_sha256_and_hard_locks(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
        )
        d = rep.to_dict()
        d["emmc_write_count"] = 1
        vres = verify_phase341_report(d)
        self.assertFalse(vres.valid)
        self.assertTrue(any("emmc_write_count" in e for e in vres.errors))

        d2 = rep.to_dict()
        d2["fx3_sync_terminal_present"] = True
        d2["fx6_genlock_bnc_present"] = True
        d2["fx3_var_shutter_present"] = True
        d2["fx3_2_5mm_lanc_present"] = True
        d2["fx3_marker_outputs_to_hdmi"] = True
        d2["fx3_camset_allows_slot2"] = True
        d2["report_sha256"] = "0" * 64
        vres2 = verify_phase341_report(d2)
        self.assertFalse(vres2.valid)
        self.assertTrue(any("report_sha256" in e for e in vres2.errors))
        self.assertTrue(any("fx3_sync_terminal_present" in e for e in vres2.errors))

    def test_11_verify_report_rejects_schema_and_help_guide_mismatch(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight()
        d = rep.to_dict()
        d["schema_version"] = "wrong_schema"
        d["sony_help_guide_id"] = "ilc/9999"
        d["go_no_go"] = "INVALID_STATUS"
        vres = verify_phase341_report(d)
        self.assertFalse(vres.valid)
        self.assertGreaterEqual(len(vres.errors), 3)

    def test_12_markdown_renderer_contains_all_four_groups(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
        )
        md = render_phase341_markdown(rep)
        self.assertIn("Phase 341", md)
        self.assertIn(P341_CHECK_GROUP_A_ID, md)
        self.assertIn(P341_CHECK_GROUP_B_ID, md)
        self.assertIn(P341_CHECK_GROUP_C_ID, md)
        self.assertIn(P341_CHECK_GROUP_D_ID, md)
        self.assertIn(P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC, md)
        self.assertIn(P341_PB_MAGNIFY_PINCH_SONY_TYPO_SYMBOL, md)
        self.assertIn(P341_CTRL_FOR_HDMI_SONY_TYPO_BKID, md)

    def test_13_unconditional_zero_leak_and_telemetry_constants(self) -> None:
        self.assertEqual(PHASE341_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE341_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE341_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE341_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE341_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE341_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(PHASE341_RF_NVS_MUTATION_BYTES, 0)

    def test_14_deterministic_sha256_identical_across_clean_room_runs(self) -> None:
        r1 = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        r2 = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.to_deterministic_json(), r2.to_deterministic_json())

    # ------------------------------------------------------------------
    # 15-36: Group A (Wave 68 §§1-2: Area/Date/DST/RTC & Grid/Marker HDMI)
    # ------------------------------------------------------------------

    def test_15_ga_model_fw_and_help_guide_enforced(self) -> None:
        r_bad_model = evaluate_p341_check_group_a_area_date_grid_and_marker(body_model_id=0x12345678)
        self.assertFalse(r_bad_model.passed)
        self._assert_err(r_bad_model, P341_GA_ERR_MODEL_OR_FW_FLOOR)

        r_bad_fw = evaluate_p341_check_group_a_area_date_grid_and_marker(body_fw="6.00")
        self.assertFalse(r_bad_fw.passed)
        self._assert_err(r_bad_fw, P341_GA_ERR_MODEL_OR_FW_FLOOR)

        r_bad_guide = evaluate_p341_check_group_a_area_date_grid_and_marker(sony_help_guide_id="ilc/9999")
        self.assertFalse(r_bad_guide.passed)
        self._assert_err(r_bad_guide, P341_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_16_ga_invalid_reset_action_and_shoot_mode(self) -> None:
        r_rst = evaluate_p341_check_group_a_area_date_grid_and_marker(reset_action="BAD_RESET")
        self.assertFalse(r_rst.passed)
        self._assert_err(r_rst, P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY)

        r_mode = evaluate_p341_check_group_a_area_date_grid_and_marker(shoot_mode="STILL_RAW")
        self.assertFalse(r_mode.passed)
        self._assert_err(r_mode, P341_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_17_ga_thirty_area_gmt_zones_and_six_half_hour_offsets(self) -> None:
        self.assertEqual(len(P341_AREA_GMT_THIRTY_ZONES), 30)
        self.assertEqual(len(P341_AREA_HALF_HOUR_SIX_ZONES), 6)
        self.assertEqual(len(P341_AREA_DATE_EXACT_FOUR_ITEMS), 4)
        self.assertEqual(P341_AREA_SETTING_RESID16_HEX, "0xe91a")
        for hz in P341_AREA_HALF_HOUR_SIX_ZONES:
            res = evaluate_p341_check_group_a_area_date_grid_and_marker(area_zone=hz)
            self.assertTrue(res.passed, hz)
            self.assertEqual(res.area_gmt_zone_count, 30)
            self.assertEqual(res.area_half_hour_zone_count, 6)

    def test_18_ga_rejects_invalid_area_zone_or_truncated_zone_table(self) -> None:
        r_zone = evaluate_p341_check_group_a_area_date_grid_and_marker(area_zone="AREA_GMT_P_14_0")
        self.assertFalse(r_zone.passed)
        self._assert_err(r_zone, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

        r_table = evaluate_p341_check_group_a_area_date_grid_and_marker(
            exposed_area_gmt_zones=P341_AREA_GMT_THIRTY_ZONES[:-1],
        )
        self.assertFalse(r_table.passed)
        self._assert_err(r_table, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

    def test_19_ga_daylight_savings_sony_elf_typo_and_date_formats(self) -> None:
        self.assertEqual(P341_DAYLIGHT_SAVINGS_RESID16_HEX, "0xe917")
        self.assertEqual(P341_DATE_FORMAT_RESID16_HEX, "0x670d")
        self.assertEqual(
            P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC,
            "convert_setting_daylight_saving_to_saylight_saving",
        )
        self.assertEqual(P341_DATE_TIME_AUTO_SYNC_SONY_TYPO_BKID, "BKID_APP_setting_auto_sync_sever_date_time")
        for dfmt in ("Y_M_D", "M_D_Y", "D_M_Y"):
            res = evaluate_p341_check_group_a_area_date_grid_and_marker(
                daylight_savings="ON",
                date_format=dfmt,
            )
            self.assertTrue(res.passed)
            self.assertEqual(res.daylight_savings_elf_typo_func, P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC)

    def test_20_ga_rejects_invalid_daylight_savings_or_date_format(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(daylight_savings="AUTO")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(date_format="YYYY_MM_DD")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

    def test_21_ga_soldered_rtc_zero_cr2032_and_24h_charge_rule(self) -> None:
        self.assertFalse(P341_USER_REPLACEABLE_CR2032_SLOT_PRESENT)
        self.assertEqual(P341_RTC_INTERNAL_MIN_CHARGE_HOURS, 24.0)
        r_cr = evaluate_p341_check_group_a_area_date_grid_and_marker(
            claimed_user_replaceable_cr2032_present=True,
        )
        self.assertFalse(r_cr.passed)
        self._assert_err(r_cr, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

        r_short = evaluate_p341_check_group_a_area_date_grid_and_marker(
            rtc_initialized=False,
            rtc_backup_charge_hours=12.0,
        )
        self.assertFalse(r_short.passed)
        self._assert_err(r_short, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

        r_ok = evaluate_p341_check_group_a_area_date_grid_and_marker(
            rtc_initialized=False,
            rtc_backup_charge_hours=24.0,
        )
        self.assertTrue(r_ok.passed)

    def test_22_ga_rtc_discharge_without_24h_charge_claim_rejected(self) -> None:
        res = evaluate_p341_check_group_a_area_date_grid_and_marker(
            rtc_discharge_without_24h_charge_claimed=True,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

    def test_23_ga_area_date_reset_immune_and_legacy_name_rejected(self) -> None:
        self.assertEqual(P341_AREA_DATE_TIME_RESID16_HEX, "0x6a9c")
        self.assertEqual(P341_LEGACY_DATE_TIME_SETUP_RESID16_HEX, "0xe87f")
        r_rst = evaluate_p341_check_group_a_area_date_grid_and_marker(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_area_date_wiped_by_camera_reset=True,
        )
        self.assertFalse(r_rst.passed)
        self._assert_err(r_rst, P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY)

        r_leg = evaluate_p341_check_group_a_area_date_grid_and_marker(
            expect_area_date_uses_legacy_name_only=True,
        )
        self.assertFalse(r_leg.passed)
        self._assert_err(r_leg, P341_GA_ERR_AREA_DATE_DST_OR_RTC)

    def test_24_ga_fx6_clock_set_30min_steps_no_standalone_dst(self) -> None:
        self.assertEqual(P341_FX6_CLOCK_SET_STEP_MINUTES, 30)
        self.assertFalse(P341_FX6_STANDALONE_DST_SWITCH_PRESENT)
        res = evaluate_p341_check_group_a_area_date_grid_and_marker(
            claimed_fx6_has_standalone_dst_switch=True,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY)

    def test_25_ga_grid_line_three_types_and_hdmi_pass_when_info_on(self) -> None:
        self.assertEqual(P341_GRID_LINE_DISPLAY_RESID16_HEX, "0x6f9d")
        self.assertEqual(P341_GRID_LINE_TYPE_RESID16_HEX, "0x69c9")
        self.assertEqual(P341_GRID_LINE_EXACT_THREE_TYPES, ("RULE_OF_3RDS", "SQUARE", "DIAG_PLUS_SQUARE"))
        for gtype in P341_GRID_LINE_EXACT_THREE_TYPES:
            res = evaluate_p341_check_group_a_area_date_grid_and_marker(
                grid_line_display="ON",
                grid_line_type=gtype,
                hdmi_info_display="ON",
                hdmi_raw_output="OFF",
                rec_media_dur_hdmi_output="ON",
            )
            self.assertTrue(res.passed)
            self.assertTrue(res.grid_line_passes_over_hdmi)
            self.assertTrue(any("Clean-HDMI advisory" in w for w in res.warnings))

    def test_26_ga_grid_line_suppressed_over_hdmi_when_info_off_or_raw_or_hdmi_only(self) -> None:
        r_info_off = evaluate_p341_check_group_a_area_date_grid_and_marker(
            grid_line_display="ON",
            hdmi_info_display="OFF",
        )
        self.assertTrue(r_info_off.passed)
        self.assertFalse(r_info_off.grid_line_passes_over_hdmi)

        r_raw = evaluate_p341_check_group_a_area_date_grid_and_marker(
            grid_line_display="ON",
            hdmi_info_display="ON",
            hdmi_raw_output="ON",
        )
        self.assertTrue(r_raw.passed)
        self.assertFalse(r_raw.grid_line_passes_over_hdmi)

        r_hdmi_only = evaluate_p341_check_group_a_area_date_grid_and_marker(
            grid_line_display="ON",
            hdmi_info_display="ON",
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
        )
        self.assertTrue(r_hdmi_only.passed)
        self.assertFalse(r_hdmi_only.grid_line_passes_over_hdmi)

        r_false_claim = evaluate_p341_check_group_a_area_date_grid_and_marker(
            expect_grid_passes_hdmi_when_info_off_or_raw=True,
        )
        self.assertFalse(r_false_claim.passed)
        self._assert_err(r_false_claim, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_27_ga_invalid_grid_line_display_or_type(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(grid_line_display="MAYBE")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(grid_line_type="GOLDEN_RATIO")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_28_ga_marker_display_guideframe_15_ratios_zero_hdmi_output(self) -> None:
        self.assertEqual(P341_MARKER_DISPLAY_RESID16_HEX, "0x6803")
        self.assertEqual(P341_GUIDEFRAME_RESID16_HEX, "0x62f9")
        self.assertEqual(P341_ASPECT_MARKER_RATIO_COUNT, 15)
        self.assertFalse(P341_FX3_MARKER_OUTPUTS_TO_HDMI)

        res = evaluate_p341_check_group_a_area_date_grid_and_marker(
            shoot_mode="MOVIE",
            marker_display="ON",
            center_marker="ON",
            aspect_marker="2.39:1",
            safety_zone="90PCT",
            guideframe="ON",
            hdmi_info_display="ON",
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.fx3_marker_outputs_to_hdmi)

        r_bad = evaluate_p341_check_group_a_area_date_grid_and_marker(
            expect_marker_outputs_over_hdmi=True,
        )
        self.assertFalse(r_bad.passed)
        self._assert_err(r_bad, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_29_ga_marker_display_movie_sq_only_blocked_in_still(self) -> None:
        r_sq = evaluate_p341_check_group_a_area_date_grid_and_marker(
            shoot_mode="S_AND_Q",
            marker_display="ON",
            guideframe="ON",
        )
        self.assertTrue(r_sq.passed)

        r_still = evaluate_p341_check_group_a_area_date_grid_and_marker(
            shoot_mode="PHOTO",
            marker_display="ON",
        )
        self.assertFalse(r_still.passed)
        self._assert_err(r_still, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

        r_claim = evaluate_p341_check_group_a_area_date_grid_and_marker(
            expect_marker_active_in_still_mode=True,
        )
        self.assertFalse(r_claim.passed)
        self._assert_err(r_claim, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_30_ga_marker_display_hidden_during_focus_magnifier(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(
            marker_display="ON",
            focus_magnifier_active=True,
        )
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(
            expect_marker_visible_during_focus_magnifier=True,
        )
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_31_ga_grid_and_marker_reset_immune_and_fx6_3mode_grid_myth(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(
            claimed_grid_or_marker_wiped_by_camera_reset=True,
        )
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(
            claimed_fx6_has_3mode_static_grid_line_menu=True,
        )
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY)

    def test_32_ga_invalid_safety_zone_and_hdmi_flags(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(safety_zone="75PCT")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(rec_media_dur_hdmi_output="BAD")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_33_ga_invalid_hdmi_info_or_marker_subflags(self) -> None:
        r1 = evaluate_p341_check_group_a_area_date_grid_and_marker(hdmi_info_display="INVALID")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

        r2 = evaluate_p341_check_group_a_area_date_grid_and_marker(guideframe="INVALID")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI)

    def test_34_ga_valid_80pct_and_90pct_safety_zones(self) -> None:
        for sz in ("OFF", "80PCT", "90PCT"):
            res = evaluate_p341_check_group_a_area_date_grid_and_marker(safety_zone=sz)
            self.assertTrue(res.passed, sz)

    def test_35_ga_grid_line_off_no_hdmi_warning(self) -> None:
        res = evaluate_p341_check_group_a_area_date_grid_and_marker(
            grid_line_display="OFF",
            hdmi_info_display="ON",
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.grid_line_passes_over_hdmi)
        self.assertEqual(len(res.warnings), 0)

    def test_36_ga_initialize_reset_action_valid(self) -> None:
        res = evaluate_p341_check_group_a_area_date_grid_and_marker(reset_action="INITIALIZE")
        self.assertTrue(res.passed)

    # ------------------------------------------------------------------
    # 37-58: Group B (Wave 68 §§3-4: Save/Load CAMSET, Flash Sync, MI Shoe, Genlock)
    # ------------------------------------------------------------------

    def test_37_gb_camset_constants_and_slot1_lock(self) -> None:
        self.assertEqual(P341_SAVE_LOAD_SETTINGS_RESID16_HEX, "0x6254")
        self.assertEqual(P341_CAMSET_ALLOWED_SLOT, 1)
        self.assertEqual(P341_CAMSET_MAX_FILES_PER_CARD, 10)
        self.assertEqual(P341_CAMSET_CARD_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT")
        self.assertEqual(P341_CAMPR_CARD_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT")
        self.assertEqual(P341_FTPSET_CARD_TEMPLATE, "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT")
        self.assertEqual(P341_CAMSET_PRO_CAMERA_FX3_HITS, 0)
        self.assertEqual(len(P341_CAMSET_EXCLUDED_CATEGORIES), 18)

        r_slot2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(camset_slot=2)
        self.assertFalse(r_slot2.passed)
        self._assert_err(r_slot2, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r_claim_slot2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_camset_allows_slot2=True,
        )
        self.assertFalse(r_claim_slot2.passed)
        self._assert_err(r_claim_slot2, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_38_gb_camset_file_index_and_template_zero_pro_camera(self) -> None:
        r_idx = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(camset_file_index=11)
        self.assertFalse(r_idx.passed)
        self._assert_err(r_idx, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r_tpl = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            camset_card_template="%c:%s/SONY/PRO/CAMERA/%s/%s.ALL",
        )
        self.assertFalse(r_tpl.passed)
        self._assert_err(r_tpl, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r_pro = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_camset_uses_pro_camera_path=True,
        )
        self.assertFalse(r_pro.passed)
        self._assert_err(r_pro, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_39_gb_camset_load_mr_lockout_and_fw101_reject(self) -> None:
        r_mr = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            camset_action="LOAD",
            exposure_mode="MEMORY_RECALL",
        )
        self.assertFalse(r_mr.passed)
        self._assert_err(r_mr, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        for old_fw in ("1.00", "1.01"):
            r_old = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
                camset_action="LOAD",
                camset_fw_version=old_fw,
            )
            self.assertFalse(r_old.passed)
            self._assert_err(r_old, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r_ok = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            camset_action="LOAD",
            camset_fw_version="7.02",
        )
        self.assertTrue(r_ok.passed)
        self.assertFalse(r_ok.slot1_tier0_vault_mutated)

    def test_40_gb_camset_exclusions_and_ftpset_separation(self) -> None:
        r_exc = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_camset_includes_excluded_items=True,
        )
        self.assertFalse(r_exc.passed)
        self._assert_err(r_exc, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r_ftp = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_ftpset_shares_camset_dir=True,
        )
        self.assertFalse(r_ftp.passed)
        self._assert_err(r_ftp, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_41_gb_camera_set_memory_body_vs_card_m1_m4_and_exclusions(self) -> None:
        self.assertEqual(P341_CAMERA_SET_MEMORY_BODY_SLOTS, ("1", "2", "3"))
        self.assertEqual(P341_CAMERA_SET_MEMORY_CARD_SLOTS, ("M1", "M2", "M3", "M4"))
        r_save_slot2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            campr_action="SAVE",
            campr_slot="M1",
            memory_recall_media_slot=2,
        )
        self.assertTrue(r_save_slot2.passed)
        self.assertFalse(r_save_slot2.slot1_tier0_vault_mutated)

        r_body = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            campr_action="SAVE",
            campr_slot="2",
            memory_recall_media_slot=1,
        )
        self.assertTrue(r_body.passed)
        self.assertFalse(r_body.slot1_tier0_vault_mutated)

        r_exc = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_campr_includes_custom_key_or_program_shift=True,
        )
        self.assertFalse(r_exc.passed)
        self._assert_err(r_exc, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_42_gb_slot1_tier0_erofs30_firewall_blocks_save_and_delete(self) -> None:
        for action in ("SAVE", "DELETE"):
            res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
                camset_action=action,
                camset_slot=1,
                slot1_contains_tier0_dump=True,
            )
            self.assertFalse(res.passed, action)
            self.assertTrue(res.slot1_tier0_vault_mutated)
            self._assert_err(res, P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS)
            self._assert_err_contains(res, f"errno={P341_ERRNO_EROFS}")

    def test_43_gb_slot1_tier0_erofs30_blocks_campr_m_and_ftpset_save_on_slot1(self) -> None:
        r_campr = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            campr_action="SAVE",
            campr_slot="M2",
            memory_recall_media_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(r_campr.passed)
        self.assertTrue(r_campr.slot1_tier0_vault_mutated)
        self._assert_err(r_campr, P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS)

        r_ftp = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            ftpset_action="SAVE",
            ftpset_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(r_ftp.passed)
        self.assertTrue(r_ftp.slot1_tier0_vault_mutated)
        self._assert_err(r_ftp, P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS)

    def test_44_gb_slot1_data_sector_writes_nonzero_rejected(self) -> None:
        res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            slot1_data_sector_writes=4,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.slot1_tier0_vault_mutated)
        self._assert_err(res, P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS)

    def test_45_gb_fx6_reference_file_myth_rejected(self) -> None:
        self.assertFalse(P341_FX6_REFERENCE_FILE_PRESENT)
        res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_fx6_reference_file_present=True,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH)

    def test_46_gb_fx3_zero_physical_pc_flash_sync_terminal(self) -> None:
        self.assertFalse(P341_FX3_SYNC_TERMINAL_PRESENT)
        self.assertEqual(P341_FX3_SYNCHRO_TERMINAL_SYMBOL_HITS, 0)
        r_req = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            pc_sync_terminal_requested=True,
        )
        self.assertFalse(r_req.passed)
        self._assert_err(r_req, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)
        self._assert_err_contains(r_req, f"errno={P341_ERRNO_EOPNOTSUPP}")

        r_claim = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_fx3_sync_terminal_present=True,
        )
        self.assertFalse(r_claim.passed)
        self._assert_err(r_claim, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_47_gb_xlr_h1_passive_cold_shoe_excludes_hvl_lbpc_and_flash(self) -> None:
        r_lbpc = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            xlr_h1_attached=True,
            hvl_lbpc_direct_mount_requested=True,
        )
        self.assertFalse(r_lbpc.passed)
        self._assert_err(r_lbpc, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r_flash = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            shoot_mode="PHOTO",
            still_shutter_type="MECHANICAL_SHUTTER",
            xlr_h1_attached=True,
            flash_mode="FILL_FLASH",
        )
        self.assertFalse(r_flash.passed)
        self._assert_err(r_flash, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r_detached = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            shoot_mode="PHOTO",
            still_shutter_type="MECHANICAL_SHUTTER",
            xlr_h1_attached=False,
            hvl_lbpc_direct_mount_requested=True,
            video_light_mode="AUTO",
            mi_shoe_5v_draw_ma=850,
            flash_mode="FILL_FLASH",
        )
        self.assertTrue(r_detached.passed)

    def test_48_gb_video_light_mode_4_options_and_pmic_5v_900ma_cap(self) -> None:
        self.assertEqual(P341_VIDEO_LIGHT_MODE_RESID16_HEX, "0x6211")
        self.assertEqual(
            P341_VIDEO_LIGHT_MODE_FOUR_OPTIONS,
            ("POWER_LINK", "REC_LINK", "REC_LINK_AND_STBY", "AUTO"),
        )
        self.assertEqual(P341_MI_SHOE_PMIC_5V_MAX_MA, 900)
        for vlm in P341_VIDEO_LIGHT_MODE_FOUR_OPTIONS:
            res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
                video_light_mode=vlm,
                mi_shoe_5v_draw_ma=900,
            )
            self.assertTrue(res.passed, vlm)

        r_over = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(mi_shoe_5v_draw_ma=901)
        self.assertFalse(r_over.passed)
        self._assert_err(r_over, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r_bad_mode = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(video_light_mode="CONTINUOUS_FULL")
        self.assertFalse(r_bad_mode.passed)
        self._assert_err(r_bad_mode, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_49_gb_flash_still_mech_only_xsync_250_and_voltage_guard(self) -> None:
        self.assertEqual(P341_FLASH_XSYNC_DENOMINATOR, 250)
        self.assertEqual(P341_FLASH_MAX_TRIGGER_VOLTAGE_V, 250.0)
        r_elec = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            shoot_mode="PHOTO",
            still_shutter_type="ELECTRONIC_SHUTTER",
            xlr_h1_attached=False,
            flash_mode="FILL_FLASH",
        )
        self.assertFalse(r_elec.passed)
        self._assert_err(r_elec, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r_xsync = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            flash_xsync_denominator=320,
        )
        self.assertFalse(r_xsync.passed)
        self._assert_err(r_xsync, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r_hv = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            flash_trigger_voltage_v=250.0,
        )
        self.assertFalse(r_hv.passed)
        self._assert_err(r_hv, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_50_gb_fx6_video_light_3modes_and_zero_genlock_bnc(self) -> None:
        self.assertEqual(
            P341_FX6_VIDEO_LIGHT_SET_THREE_OPTIONS,
            ("POWER_LINK", "REC_LINK", "REC_LINK_AND_STBY"),
        )
        self.assertFalse(P341_FX6_GENLOCK_BNC_PRESENT)
        self.assertEqual(P341_FX6_GENLOCK_DORMANT_SYMBOL_HITS, 107)

        r_auto = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_fx6_video_light_has_auto_mode=True,
        )
        self.assertFalse(r_auto.passed)
        self._assert_err(r_auto, P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH)

        r_gen1 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            claimed_fx6_genlock_bnc_present=True,
        )
        self.assertFalse(r_gen1.passed)
        self._assert_err(r_gen1, P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH)

        r_gen2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            fx6_genlock_requested=True,
        )
        self.assertFalse(r_gen2.passed)
        self._assert_err(r_gen2, P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH)

    def test_51_gb_invalid_camset_campr_ftpset_actions(self) -> None:
        r1 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(camset_action="FORMAT")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(campr_action="DELETE")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r3 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(ftpset_action="DELETE")
        self.assertFalse(r3.passed)
        self._assert_err(r3, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_52_gb_invalid_media_type_campr_slot_and_recall_media_slot(self) -> None:
        r1 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(camset_media_type="MEMORY_STICK")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(campr_slot="M5")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

        r3 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(memory_recall_media_slot=3)
        self.assertFalse(r3.passed)
        self._assert_err(r3, P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION)

    def test_53_gb_flash_mode_invalid_and_negative_voltage(self) -> None:
        r1 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(flash_mode="HSS_FP")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

        r2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(flash_trigger_voltage_v=-5.0)
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_54_gb_campr_recall_on_slot1_readonly_permitted(self) -> None:
        res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            campr_action="RECALL",
            campr_slot="M1",
            memory_recall_media_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.slot1_tier0_vault_mutated)

    def test_55_gb_ftpset_load_on_slot1_and_save_on_slot2_permitted(self) -> None:
        r_load = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            ftpset_action="LOAD",
            ftpset_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(r_load.passed)

        r_save2 = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            ftpset_action="SAVE",
            ftpset_slot=2,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(r_save2.passed)
        self.assertFalse(r_save2.slot1_tier0_vault_mutated)

    def test_56_gb_flash_blocked_in_movie_even_when_xlr_detached(self) -> None:
        res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
            shoot_mode="MOVIE",
            xlr_h1_attached=False,
            flash_mode="AUTO_FLASH",
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_57_gb_negative_mi_shoe_5v_draw_rejected(self) -> None:
        res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(mi_shoe_5v_draw_ma=-1)
        self.assertFalse(res.passed)
        self._assert_err(res, P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE)

    def test_58_gb_sdhc_and_sdxc_valid_camset_media_types(self) -> None:
        for media in ("CFEXPRESS_A", "SDXC", "SDHC"):
            res = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
                camset_action="LOAD",
                camset_slot=1,
                camset_media_type=media,
                camset_file_index=10,
            )
            self.assertTrue(res.passed, media)

    # ------------------------------------------------------------------
    # 59-74: Group C (Wave 69 §§1-2: Playback Magnify & Anti-flicker vs Var. Shutter)
    # ------------------------------------------------------------------

    def test_59_gc_playback_magnification_still_only_and_typo_symbol(self) -> None:
        self.assertEqual(P341_PB_ENLARGE_IMAGE_RESID16_HEX, "0xe8cb")
        self.assertEqual(P341_PB_ENLARGE_INITIAL_MAG_RESID16_HEX, "0x6b6e")
        self.assertEqual(P341_PB_ENLARGE_INITIAL_POS_RESID16_HEX, "0x781f")
        self.assertEqual(P341_PB_MAGNIFY_PINCH_SONY_TYPO_SYMBOL, "playback_zoom_maginify_by_pinch")
        self.assertEqual(P341_PB_ENLARGE_INITIAL_MAG_MODES, ("STANDARD_MAG", "PREVIOUS_MAG"))
        self.assertEqual(P341_PB_ENLARGE_INITIAL_POS_MODES, ("FOCUSED_POSITION", "CENTER"))

        res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            playback_magnify_requested=True,
            playback_media_kind="STILL",
            enlarge_initial_mag="PREVIOUS_MAG",
            enlarge_initial_pos="CENTER",
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.playback_magnify_pinch_typo_symbol, "playback_zoom_maginify_by_pinch")

    def test_60_gc_playback_magnify_movie_rejected_with_eopnotsupp95(self) -> None:
        r1 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            playback_magnify_requested=True,
            playback_media_kind="MOVIE",
        )
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)
        self._assert_err_contains(r1, f"errno={P341_ERRNO_EOPNOTSUPP}")

        r2 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            claimed_playback_magnify_works_on_movies=True,
        )
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)

    def test_61_gc_playback_magnify_reset_immune_and_fx6_parity(self) -> None:
        r1 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            claimed_playback_magnify_wiped_by_camera_reset=True,
        )
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)

        r2 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            claimed_fx6_has_playback_enlarge=True,
        )
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY)

    def test_62_gc_invalid_playback_enums(self) -> None:
        r1 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(playback_media_kind="RAW")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)

        r2 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(enlarge_initial_mag="MAX_MAG")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)

        r3 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(enlarge_initial_pos="TOP_LEFT")
        self.assertFalse(r3.passed)
        self._assert_err(r3, P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE)

    def test_63_gc_antiflicker_shoot_valid_in_still_mechanical_shutter(self) -> None:
        self.assertEqual(P341_ANTI_FLICKER_SHOOT_RESID16_HEX, "0x623d")
        self.assertEqual(P341_ANTI_FLICKER_FREQUENCIES_HZ, (100, 120))
        res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            shoot_mode="PHOTO",
            still_shutter_type="MECHANICAL_SHUTTER",
            silent_mode="OFF",
            bulb_enabled=False,
            anti_flicker_shoot="ON",
        )
        self.assertTrue(res.passed)

    def test_64_gc_antiflicker_shoot_locked_in_movie_and_sq(self) -> None:
        for mode in ("MOVIE", "S_AND_Q"):
            res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
                shoot_mode=mode,
                anti_flicker_shoot="ON",
            )
            self.assertFalse(res.passed, mode)
            self._assert_err(res, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

    def test_65_gc_antiflicker_shoot_locked_by_electronic_silent_and_bulb(self) -> None:
        r_elec = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            shoot_mode="PHOTO",
            still_shutter_type="ELECTRONIC_SHUTTER",
            anti_flicker_shoot="ON",
        )
        self.assertFalse(r_elec.passed)
        self._assert_err(r_elec, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

        r_silent = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            shoot_mode="PHOTO",
            still_shutter_type="MECHANICAL_SHUTTER",
            silent_mode="ON",
            anti_flicker_shoot="ON",
        )
        self.assertFalse(r_silent.passed)
        self._assert_err(r_silent, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

        r_bulb = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            shoot_mode="PHOTO",
            still_shutter_type="MECHANICAL_SHUTTER",
            bulb_enabled=True,
            anti_flicker_shoot="ON",
        )
        self.assertFalse(r_bulb.passed)
        self._assert_err(r_bulb, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

    def test_66_gc_antiflicker_high_freq_led_myth_and_resettable_fact(self) -> None:
        r_led = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            claimed_anti_flicker_effective_on_high_freq_led=True,
        )
        self.assertFalse(r_led.passed)
        self._assert_err(r_led, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

        r_rst = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            claimed_anti_flicker_shoot_resists_camera_reset=True,
        )
        self.assertFalse(r_rst.passed)
        self._assert_err(r_rst, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

    def test_67_gc_dormant_var_shutter_and_anti_flicker_tv_scan_eopnotsupp95(self) -> None:
        self.assertEqual(P341_DORMANT_VAR_SHUTTER_RESID16_HEX, "0x6831")
        self.assertEqual(P341_DORMANT_VAR_SHUTTER_SET_RESID16_HEX, "0x6f9e")
        self.assertEqual(P341_DORMANT_ANTI_FLICKER_SET_RESID16_HEX, "0x68e7")
        self.assertEqual(P341_DORMANT_ANTI_FLICKER_TV_SCAN_RESID16_HEX, "0x63c0")

        for kw in (
            {"dormant_var_shutter_requested": True},
            {"dormant_anti_flicker_set_requested": True},
            {"dormant_anti_flicker_tv_scan_requested": True},
            {"claimed_fx3_var_shutter_present": True},
            {"claimed_fx3_anti_flicker_tv_scan_present": True},
            {"claimed_fx3_anti_flicker_set_present": True},
        ):
            res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(**kw)
            self.assertFalse(res.passed, repr(kw))
            self.assertFalse(res.fx3_var_shutter_present)
            self.assertFalse(res.fx3_anti_flicker_tv_scan_present)
            self.assertFalse(res.fx3_anti_flicker_set_present)
            self._assert_err(res, P341_GC_ERR_DORMANT_VAR_SHUTTER_OR_TV_SCAN)
            self._assert_err_contains(res, f"errno={P341_ERRNO_EOPNOTSUPP}")

    def test_68_gc_fx6_ecs_range_23_99_to_8000_hz_and_lacks_ecs_myth(self) -> None:
        self.assertEqual(P341_FX6_ECS_FREQ_MIN_HZ, 23.99)
        self.assertEqual(P341_FX6_ECS_FREQ_MAX_HZ, 8000.0)
        for freq in (23.99, 60.0, 240.5, 8000.0):
            res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
                fx6_ecs_enabled=True,
                fx6_ecs_freq_hz=freq,
            )
            self.assertTrue(res.passed, freq)

        for bad_freq in (23.5, 8000.1):
            r_bad = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
                fx6_ecs_enabled=True,
                fx6_ecs_freq_hz=bad_freq,
            )
            self.assertFalse(r_bad.passed, bad_freq)
            self._assert_err(r_bad, P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY)

        r_lacks = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(claimed_fx6_lacks_ecs=True)
        self.assertFalse(r_lacks.passed)
        self._assert_err(r_lacks, P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY)

    def test_69_gc_invalid_antiflicker_or_shutter_type_enum(self) -> None:
        r1 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(anti_flicker_shoot="AUTO")
        self.assertFalse(r1.passed)
        self._assert_err(r1, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

        r2 = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(still_shutter_type="AUTO")
        self.assertFalse(r2.passed)
        self._assert_err(r2, P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT)

    def test_70_gc_fx6_ecs_disabled_ignores_out_of_range_freq(self) -> None:
        res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=0.0,
        )
        self.assertTrue(res.passed)

    def test_71_gc_playback_magnify_inactive_on_movie_idle_state_passes(self) -> None:
        res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
            playback_magnify_requested=False,
            playback_media_kind="MOVIE",
        )
        self.assertTrue(res.passed)

    def test_72_gc_orchestrator_propagates_group_c_dormant_var_shutter_failure(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
            dormant_var_shutter_requested=True,
        )
        self.assertFalse(rep.check_group_c.passed)
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertEqual(
            rep.go_no_go,
            P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE,
        )

    def test_73_gc_orchestrator_propagates_movie_magnify_failure(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
            playback_magnify_requested=True,
            playback_media_kind="MOVIE",
        )
        self.assertFalse(rep.check_group_c.passed)
        self.assertEqual(rep.check_groups_passed, 3)

    def test_74_gc_antiflicker_still_off_is_valid_across_all_modes(self) -> None:
        for mode in ("PHOTO", "MOVIE", "S_AND_Q"):
            res = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
                shoot_mode=mode,
                anti_flicker_shoot="OFF",
                still_shutter_type="ELECTRONIC_SHUTTER",
                silent_mode="ON",
                bulb_enabled=True,
            )
            self.assertTrue(res.passed, mode)

    # ------------------------------------------------------------------
    # 75-92: Group D (Wave 69 §§3-4: Wi-Fi Dual-SKU, RF NVS, IR, CEC & Tier-0)
    # ------------------------------------------------------------------

    def test_75_gd_dual_sku_ww728473_vs_ww558244_5ghz_lockout(self) -> None:
        self.assertEqual(P341_WIFI_FREQUENCY_BAND_RESID16_HEX, "0x66c3")
        self.assertEqual(P341_WIFI_SKU_GATING_SYMBOL, "backup_get_wi_fi_frequency_band_dst")

        r_ww72 = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            wifi_sku="WW728473",
            wifi_frequency_band="5_GHZ",
        )
        self.assertTrue(r_ww72.passed)

        r_ww55_ok = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            wifi_sku="WW558244",
            wifi_frequency_band="2_4_GHZ",
        )
        self.assertTrue(r_ww55_ok.passed)

        r_ww55_5g = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            wifi_sku="WW558244",
            wifi_frequency_band="5_GHZ",
        )
        self.assertFalse(r_ww55_5g.passed)
        self._assert_err(r_ww55_5g, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)
        self._assert_err_contains(r_ww55_5g, f"errno={P341_ERRNO_EOPNOTSUPP}")

        r_claim = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            claimed_ww558244_supports_5ghz=True,
        )
        self.assertFalse(r_claim.passed)
        self._assert_err(r_claim, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

    def test_76_gd_wifi_security_wpa2_wpa3_vs_removed_legacy_protocols(self) -> None:
        self.assertEqual(P341_WIFI_REMOVED_LEGACY_PROTOCOLS, ("WEP", "WPA_PSK", "IPSEC"))
        for proto in P341_WIFI_SUPPORTED_SECURITY_PROTOCOLS:
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(wifi_security_protocol=proto)
            self.assertTrue(res.passed, proto)

        for legacy in P341_WIFI_REMOVED_LEGACY_PROTOCOLS:
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(wifi_security_protocol=legacy)
            self.assertFalse(res.passed, legacy)
            self._assert_err(res, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        r_claim = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            claimed_ver700_supports_wep_wpa_ipsec=True,
        )
        self.assertFalse(r_claim.passed)
        self._assert_err(r_claim, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

    def test_77_gd_reset_network_set_preserves_airplane_mode_and_fx6_skus(self) -> None:
        r_ok = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            reset_action="RESET_NETWORK_SET",
            airplane_mode="ON",
        )
        self.assertTrue(r_ok.passed)

        r_wipe_air = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            reset_action="RESET_NETWORK_SET",
            claimed_reset_network_wipes_airplane_mode=True,
        )
        self.assertFalse(r_wipe_air.passed)
        self._assert_err(r_wipe_air, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        r_cam_rst = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_camera_reset_wipes_network=True,
        )
        self.assertFalse(r_cam_rst.passed)
        self._assert_err(r_cam_rst, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        r_fx6_sku = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            claimed_fx6_uses_single_wifi_sku=True,
        )
        self.assertFalse(r_fx6_sku.passed)
        self._assert_err(r_fx6_sku, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

    def test_78_gd_zero_rf_airplane_mode_and_p12_p13_rf_nvs_ms_rdonly(self) -> None:
        self.assertEqual(P341_RF_NVS_PARTITIONS, ("nflasha12", "nflasha13"))
        r_air = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(airplane_mode="OFF")
        self.assertFalse(r_air.passed)
        self._assert_err(r_air, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        r_wifi = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(wifi_connect="ON")
        self.assertFalse(r_wifi.passed)
        self._assert_err(r_wifi, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        r_ap = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(access_point_set_requested=True)
        self.assertFalse(r_ap.passed)
        self._assert_err(r_ap, P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE)

        for kw in (
            {"rf_nvs_p12_p13_readonly": False},
            {"rf_nvs_mutation_bytes": 16},
            {"claim_rf_nvs_write_authorized": True},
            {"wireless_rf_packets_emitted": 1},
        ):
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(**kw)
            self.assertFalse(res.passed, repr(kw))
            self._assert_err(res, P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK)

    def test_79_gd_ir_remote_front_5_sensor_vs_8_and_fx3a_removal(self) -> None:
        self.assertEqual(P341_IR_REMOTE_CTRL_RESID16_HEX, "0x61a6")
        self.assertEqual(P341_FX3_IR_SENSOR_FRONT_INDEX, 5)
        self.assertEqual(P341_FX3_AF_ILLUMINATOR_LAMP_FRONT_INDEX, 8)
        self.assertFalse(P341_FX3_2_5MM_LANC_PRESENT)

        r_ok = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            camera_revision="ILME_FX3",
            ir_remote_ctrl="ON",
            ir_sensor_front_index=5,
            bluetooth_rmt_ctrl="OFF",
        )
        self.assertTrue(r_ok.passed)

        r_idx8 = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(ir_sensor_front_index=8)
        self.assertFalse(r_idx8.passed)
        self._assert_err(r_idx8, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_claim8 = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(claimed_ir_sensor_is_front_8=True)
        self.assertFalse(r_claim8.passed)
        self._assert_err(r_claim8, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_fx3a_on = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            camera_revision="ILME_FX3A",
            ir_remote_ctrl="ON",
        )
        self.assertFalse(r_fx3a_on.passed)
        self._assert_err(r_fx3a_on, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_fx3a_claim = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            camera_revision="ILME_FX3A",
            claimed_fx3a_keeps_ir_sensor=True,
        )
        self.assertFalse(r_fx3a_claim.passed)
        self._assert_err(r_fx3a_claim, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_fx3a_off = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            camera_revision="ILME_FX3A",
            ir_remote_ctrl="OFF",
        )
        self.assertTrue(r_fx3a_off.passed)

    def test_80_gd_ir_bt_mutex_powersave_bypass_lanc_and_reset_immunity(self) -> None:
        r_bt = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            ir_remote_ctrl="ON",
            bluetooth_rmt_ctrl="ON",
        )
        self.assertFalse(r_bt.passed)
        self._assert_err(r_bt, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_ps = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            ir_remote_ctrl="ON",
            expect_power_save_sleeps_during_ir=True,
        )
        self.assertFalse(r_ps.passed)
        self._assert_err(r_ps, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_lanc = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(claimed_fx3_has_2_5mm_lanc=True)
        self.assertFalse(r_lanc.passed)
        self._assert_err(r_lanc, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

        r_rst = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            claimed_ir_or_cec_wiped_by_camera_reset=True,
        )
        self.assertFalse(r_rst.passed)
        self._assert_err(r_rst, P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC)

    def test_81_gd_ctrl_for_hdmi_factory_default_on_cec_hijack_and_typo(self) -> None:
        self.assertEqual(P341_CTRL_FOR_HDMI_RESID16_HEX, "0xe41f")
        self.assertEqual(P341_CTRL_FOR_HDMI_FACTORY_DEFAULT, "ON")
        self.assertEqual(P341_CTRL_FOR_HDMI_BENCH_REQUIRED, "OFF")
        self.assertEqual(P341_CTRL_FOR_HDMI_SONY_TYPO_BKID, "BKID_APP_setting_ctrl_for_hmdi")
        self.assertEqual(P341_CEC_EVENT_KEY_COUNT, 41)

        r_hijack = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            hdmi_bench_attached=True,
            ctrl_for_hdmi="ON",
        )
        self.assertFalse(r_hijack.passed)
        self._assert_err(r_hijack, P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK)

        r_no_hdmi = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            hdmi_bench_attached=False,
            ctrl_for_hdmi="ON",
        )
        self.assertTrue(r_no_hdmi.passed)

        r_def = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            claimed_ctrl_for_hdmi_factory_default_is_off=True,
        )
        self.assertFalse(r_def.passed)
        self._assert_err(r_def, P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK)

        r_rec = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(claimed_cec_has_rec_key=True)
        self.assertFalse(r_rec.passed)
        self._assert_err(r_rec, P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK)

    def test_82_gd_fail_closed_redline_violations_all_blocked(self) -> None:
        for kw in (
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 4},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(**kw)
            self.assertFalse(res.passed, repr(kw))
            self._assert_err(res, P341_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_83_gd_valid_dual_media_bytes_receipts_distinct_st_dev_verify_tier0(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_RECEIPT")
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(
            rep.go_no_go,
            P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase341_report(rep).valid)

    def test_84_gd_dual_media_file_paths_same_st_dev_rejected(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "FX3RCPT1_a.bin"
            pb = Path(td) / "FX3RCPT1_b.bin"
            pa.write_bytes(sim["receipt_a_bytes"])
            pb.write_bytes(sim["receipt_b_bytes"])
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
                receipt_a_path=pa,
                receipt_b_path=pb,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
            )
            self.assertFalse(res.passed)
            self.assertFalse(res.tier0_receipt_verified)
            self._assert_err(res, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

            res_ok = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
                receipt_a_path=pa,
                receipt_b_path=pb,
                st_dev_a_override=2001,
                st_dev_b_override=2002,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
            )
            self.assertTrue(res_ok.passed)
            self.assertTrue(res_ok.tier0_receipt_verified)
            self.assertEqual(res_ok.h0_equals_h3_count, 16)

    def test_85_gd_tampered_or_short_or_mismatched_receipt_rejected(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        bad_buf = bytearray(sim["receipt_a_bytes"])
        bad_buf[24] ^= 0xFF
        r_tamper = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=bytes(bad_buf),
            receipt_b_bytes=bytes(bad_buf),
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(r_tamper.passed)
        self._assert_err(r_tamper, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        r_short = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=b"FX3RCPT1" + b"\x00" * 16,
            receipt_b_bytes=b"FX3RCPT1" + b"\x00" * 16,
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(r_short.passed)
        self._assert_err(r_short, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        r_mismatch = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=bytes(bad_buf),
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(r_mismatch.passed)
        self._assert_err(r_mismatch, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_86_gd_missing_receipt_path_and_trivial_serial_or_cid_rejected(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        r_missing = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_path=Path("/nonexistent/phase341_missing_a.bin"),
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
        )
        self.assertFalse(r_missing.passed)
        self._assert_err(r_missing, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        r_serial = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
            body_serial="0000000",
        )
        self.assertFalse(r_serial.passed)
        self._assert_err(r_serial, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        r_cid = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
            emmc_cid="0" * 32,
        )
        self.assertFalse(r_cid.passed)
        self._assert_err(r_cid, P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_87_gd_h0_h3_surface_drift_rejected(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        drifted_h3 = dict(sim["h3_baselines"])
        first_key = REQUIRED_H0_BASELINE_KEYS[0]
        drifted_h3[first_key] = hashlib.sha256(b"drifted").hexdigest()
        res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=1002,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=drifted_h3,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.h0_equals_h3_count, 15)
        self._assert_err(res, P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_88_gd_simulated_h0_h3_drift_rejected(self) -> None:
        r_dry = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=2,
        )
        self.assertFalse(r_dry.passed)
        self.assertEqual(r_dry.h0_equals_h3_count, 14)
        self._assert_err(r_dry, P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

        r_idle = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            simulated_h0_h3_drifted_surfaces=1,
        )
        self.assertFalse(r_idle.passed)
        self._assert_err(r_idle, P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_89_gd_invalid_wifi_and_revision_enums(self) -> None:
        for kw in (
            {"wifi_sku": "WW999999"},
            {"wifi_connect": "AUTO"},
            {"wifi_frequency_band": "6_GHZ"},
            {"wifi_security_protocol": "TKIP"},
            {"camera_revision": "ILME_FX30"},
            {"ir_remote_ctrl": "AUTO"},
            {"ctrl_for_hdmi": "AUTO"},
        ):
            res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(**kw)
            self.assertFalse(res.passed, repr(kw))

    def test_90_gd_verify_report_rejects_verified_go_with_zero_h0_h3(self) -> None:
        rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
            simulate_bench_dry_run=True,
        )
        d = rep.to_dict()
        d["h0_equals_h3_count"] = 15
        d["tier0_receipt_verified"] = False
        d["report_sha256"] = _canonical_sha256_dict(d)
        vres = verify_phase341_report(d)
        self.assertFalse(vres.valid)
        self.assertTrue(any("16/16 H0 == H3" in e for e in vres.errors))
        self.assertTrue(any("tier0_receipt_verified" in e for e in vres.errors))

    def test_91_gd_default_h0_baselines_cover_all_8_required_keys_and_16_surfaces(self) -> None:
        sim = build_simulated_phase341_tier0_receipts()
        self.assertEqual(len(SIXTEEN_STORAGE_SURFACES), 16)
        self.assertEqual(len(REQUIRED_H0_BASELINE_KEYS), 8)
        for key in REQUIRED_H0_BASELINE_KEYS:
            self.assertIn(key, sim["h0_baselines_a"])
            self.assertIn(key, sim["h0_baselines_b"])
            self.assertIn(key, sim["h3_baselines"])

    def test_92_gd_bluetooth_rmt_ctrl_on_with_ir_off_is_allowed(self) -> None:
        res = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
            ir_remote_ctrl="OFF",
            bluetooth_rmt_ctrl="ON",
        )
        self.assertTrue(res.passed)

    # ------------------------------------------------------------------
    # 93-100: CLI Interface & Subprocess Verification
    # ------------------------------------------------------------------

    def test_93_cli_help_exits_0_and_escapes_percent_cleanly(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--area-zone", proc.stdout)
        self.assertIn("--camset-card-template", proc.stdout)
        self.assertIn("--ctrl-for-hdmi", proc.stdout)
        self.assertIn("80%", proc.stdout)
        self.assertIn("%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT", proc.stdout)

    def test_94_cli_default_exits_2_awaiting_tier0_receipt(self) -> None:
        proc = _run_cli_subprocess(["--summary"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("OVERALL=READY_OFFLINE_AWAITING_BENCH_RECEIPTS", proc.stdout)
        self.assertIn("go_no_go=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", proc.stdout)

    def test_95_cli_simulate_bench_dry_run_json_exits_0(self) -> None:
        proc = _run_cli_subprocess(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["schema_version"], P341_SCHEMA)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertNotIn("elapsed_seconds", data)
        self.assertNotIn("elapsed_seconds", data["donor_inspection"])

    def test_96_cli_force_clean_room_dry_run_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            json_out = Path(td) / "phase341.json"
            md_out = Path(td) / "phase341.md"
            proc = _run_cli_subprocess(
                [
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--output",
                    str(json_out),
                    "--markdown-out",
                    str(md_out),
                ],
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
            self.assertTrue(json_out.is_file())
            self.assertTrue(md_out.is_file())
            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(verify_phase341_report(loaded).valid)
            self.assertIn("Phase 341", md_out.read_text(encoding="utf-8"))

    def test_97_cli_rejects_cec_hijack_default_on_with_rc_2(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--ctrl-for-hdmi", "ON", "--json"],
        )
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertFalse(data["check_group_d"]["passed"])
        self.assertEqual(
            data["go_no_go"],
            P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE,
        )

    def test_98_cli_rejects_ww558244_5ghz_and_slot1_camset_save_with_rc_2(self) -> None:
        proc = _run_cli_subprocess(
            [
                "--simulate-bench-dry-run",
                "--wifi-sku",
                "WW558244",
                "--wifi-frequency-band",
                "5_GHZ",
                "--camset-action",
                "SAVE",
                "--json",
            ],
        )
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertFalse(data["check_group_b"]["passed"])
        self.assertFalse(data["check_group_d"]["passed"])
        self.assertTrue(data["slot1_tier0_vault_mutated"])

    def test_99_cli_rejects_dormant_var_shutter_and_pc_sync_with_rc_2(self) -> None:
        proc = _run_cli_subprocess(
            [
                "--simulate-bench-dry-run",
                "--dormant-var-shutter-requested",
                "--pc-sync-terminal-requested",
                "--json",
            ],
        )
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertFalse(data["check_group_b"]["passed"])
        self.assertFalse(data["check_group_c"]["passed"])

    def test_100_inprocess_cli_main_roundtrip_all_flags(self) -> None:
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "inproc.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = fx6_cli_main(
                    [
                        "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--area-zone",
                        "AREA_GMT_P_05_5",
                        "--daylight-savings",
                        "ON",
                        "--date-format",
                        "D_M_Y",
                        "--grid-line-display",
                        "ON",
                        "--grid-line-type",
                        "DIAG_PLUS_SQUARE",
                        "--hdmi-info-display",
                        "OFF",
                        "--shoot-mode",
                        "PHOTO",
                        "--anti-flicker-shoot",
                        "ON",
                        "--fx6-ecs-enabled",
                        "--fx6-ecs-freq-hz",
                        "120.5",
                        "--wifi-sku",
                        "WW728473",
                        "--wifi-frequency-band",
                        "5_GHZ",
                        "--wifi-security-protocol",
                        "WPA3_SAE",
                        "--ir-remote-ctrl",
                        "ON",
                        "--ctrl-for-hdmi",
                        "OFF",
                        "--summary",
                        "--output",
                        str(out_path),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", buf.getvalue())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["check_groups_passed"], 4)
            self.assertEqual(payload["check_group_a"]["area_zone"], "AREA_GMT_P_05_5")
            self.assertFalse(payload["check_group_a"]["grid_line_passes_over_hdmi"])
            self.assertTrue(verify_phase341_report(payload).valid)


if __name__ == "__main__":
    unittest.main()
