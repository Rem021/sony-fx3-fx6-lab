"""Dual-mode unit tests (70 cases) for Phase 279 (`preflight-usb-mode-hdmi-info-protect-and-network-reset`):
8th Physical Bench & Pre-Shoot Readiness Verifier across Wave 47 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `GITHUB_ACTIONS` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

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
from fx6_closure.__main__ import main as cli_main  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier import (  # noqa: E402
    P279_ACTIVE_LOG_SHOOTING_MODES,
    P279_AIRGAP_BLOCKED_DATA_USB_MODES,
    P279_AIRPLANE_MODE_BKID,
    P279_AIRPLANE_MODE_ON_RESID16_HEX,
    P279_CHECK_GROUP_A_ID,
    P279_CHECK_GROUP_B_ID,
    P279_CHECK_GROUP_C_ID,
    P279_CHECK_GROUP_D_ID,
    P279_DORMANT_NOUVC_MODES,
    P279_DORMANT_UVC_KMOD_BYTES,
    P279_DORMANT_UVC_KMOD_NAME,
    P279_DORMANT_UVC_RESID16_HEX,
    P279_FORBIDDEN_USB_POWER_TERMINALS,
    P279_FORMAT_MODES,
    P279_FORMAT_MODE_RESIDS,
    P279_FORMAT_PROMPT_RESID16_HEX,
    P279_FORMAT_RESID16_HEX,
    P279_FRAMING_SETTINGS_HDMI_RESET_EXCEPTION,
    P279_FTP_TARGET_PROTECT_RESID16_HEX,
    P279_FX3_MSC_VID_PID,
    P279_FX3_USB_FOUR_MODES,
    P279_FX3_USB_MODE_RESIDS,
    P279_FX6_FORMAT_MEDIA_RESID16_HEX,
    P279_FX6_LOCK_UNLOCK_CLIP_RESID16_HEX,
    P279_FX6_NETWORK_RESET_RESID16_HEX,
    P279_FX6_USB_TETHERING_RESID16_HEX,
    P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES,
    P279_GA_ERR_MODEL_OR_FW_FLOOR,
    P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF,
    P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE,
    P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT,
    P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE,
    P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION,
    P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL,
    P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID,
    P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION,
    P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION,
    P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE,
    P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
    P279_HDMI_INFO_BKID,
    P279_HDMI_INFO_CAUTION_ID,
    P279_HDMI_INFO_MODES,
    P279_HDMI_INFO_RESID16_HEX,
    P279_HDMI_INFO_RESIDS,
    P279_HDMI_RAW_OUTPUT_RESID16_HEX,
    P279_IMAGE_JUMP_PROTECT_ONLY_RESID16_HEX,
    P279_OFF_HDMI_ONLY_RESID16_HEX,
    P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P279_PPLUT_PROFILES,
    P279_PROTECT_FOUR_SCOPES,
    P279_PROTECT_SCOPE_RESIDS,
    P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX,
    P279_RESET_NW_CLEARED_DOMAINS,
    P279_RESET_NW_MENU_RESID16_HEX,
    P279_RESET_NW_PRESERVED_DOMAINS,
    P279_RESET_NW_SHUTDOWN_BKID,
    P279_SLOT1_WP_ERROR_STATUS,
    P279_SONY_HELP_GUIDE_ID,
    P279_USB_CONN_BKID,
    P279_USB_CONN_RESID16_HEX,
    P279_USB_LUN_BKID,
    P279_USB_LUN_RESID16_HEX,
    P279_USB_LUN_RESIDS,
    P279_USB_SUPPLY_BKID,
    P279_USB_SUPPLY_RESID16_HEX,
    P279_VALID_LOG_SHOOTING_MODES,
    P279_VALID_OUTPUT_RESOLUTIONS,
    P279_VALID_POWER_SOURCES,
    P279_VALID_REC_MEDIA_DUR_HDMI_MODES,
    P279_VALID_RESET_ACTIONS,
    P279_VALID_SHOOT_MODES,
    P279_VALID_USB_LUN_MODES,
    P279_VALID_USB_POWER_TERMINALS,
    PHASE_279_CHECK_GROUP_IDS,
    PHASE_279_SCHEMA,
    PHASE_279_VERSION,
    build_simulated_phase279_tier0_receipts,
    evaluate_p279_check_group_a_usb_connection_mode,
    evaluate_p279_check_group_b_hdmi_info_and_clean_feed,
    evaluate_p279_check_group_c_protect_vs_format_slot1,
    evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0,
    evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness,
    inspect_phase279_donors_bounded,
    render_phase279_markdown,
    run_usb_mode_hdmi_info_protect_and_network_reset_preflight,
    verify_phase279_report,
)


def _timing_budget(local_seconds: float, ci_seconds: float) -> float:
    return ci_seconds if os.environ.get("GITHUB_ACTIONS") == "true" else local_seconds


class TestPhase279UsbModeHdmiInfoProtectNetworkResetVerifier(unittest.TestCase):
    """70 deterministic dual-mode unit tests for Phase 279 8th physical bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        limit = _timing_budget(6.0, 15.0)
        assert elapsed < limit, f"Phase 279 test suite exceeded <{limit:.1f}s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Non-Shadowing & Bounded O_RDONLY / Clean-Room Parity (7 tests) ---

    def test_01_public_p279_symbols_exported_without_shadowing_prior_phases(self) -> None:
        self.assertEqual(
            PHASE_279_SCHEMA,
            "realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier_v1",
        )
        self.assertEqual(PHASE_279_VERSION, "279.0.0")
        for sym in (
            "PHASE_279_SCHEMA",
            "PHASE_279_VERSION",
            "P279_CHECK_GROUP_A_ID",
            "P279_CHECK_GROUP_B_ID",
            "P279_CHECK_GROUP_C_ID",
            "P279_CHECK_GROUP_D_ID",
            "evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness",
            "run_usb_mode_hdmi_info_protect_and_network_reset_preflight",
            "verify_phase279_report",
            "render_phase279_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

        # Verify prior phase exports remain non-shadowed
        self.assertEqual(
            fx6_closure.CHECK_GROUP_A_ID,
            "GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT",
        )
        self.assertEqual(
            fx6_closure.P248_CHECK_GROUP_A_ID,
            "GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP",
        )
        self.assertEqual(
            fx6_closure.P261_CHECK_GROUP_A_ID,
            "GROUP_A_DIFF_SET_8ITEMS_SHUTTER_ANGLE_CUSTOM_KEY_AND_EVFLESS",
        )
        self.assertEqual(
            fx6_closure.P275_CHECK_GROUP_A_ID,
            "GROUP_A_CINEMA_SLATE_FILE_SETTINGS_AUTO_REVIEW_AND_TCUB_PERSISTENCE",
        )
        self.assertIs(
            run_usb_mode_hdmi_info_protect_and_network_reset_preflight,
            evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness,
        )
        self.assertEqual(
            PHASE_279_CHECK_GROUP_IDS,
            (
                P279_CHECK_GROUP_A_ID,
                P279_CHECK_GROUP_B_ID,
                P279_CHECK_GROUP_C_ID,
                P279_CHECK_GROUP_D_ID,
            ),
        )

    def test_02_wave47_empirical_resid16_and_bkid_constants_exact(self) -> None:
        self.assertEqual(P279_USB_CONN_BKID, "BKID_APP_setting_usb_connection_method")
        self.assertEqual(P279_USB_CONN_RESID16_HEX, "0x69a2")
        self.assertEqual(P279_FX3_MSC_VID_PID, "054C:0DA1")
        self.assertEqual(P279_DORMANT_UVC_KMOD_NAME, "usb_f_uvc.ko")
        self.assertEqual(P279_DORMANT_UVC_KMOD_BYTES, 78840)
        self.assertEqual(P279_DORMANT_UVC_RESID16_HEX, "0x7399")
        self.assertEqual(P279_FX6_USB_TETHERING_RESID16_HEX, "0x29c9")
        self.assertEqual(P279_USB_LUN_BKID, "BKID_APP_setting_lun_settings")
        self.assertEqual(P279_USB_LUN_RESID16_HEX, "0x6b19")
        self.assertEqual(P279_USB_LUN_RESIDS, {"MULTI": "0xe631", "SINGLE": "0x776d"})
        self.assertEqual(P279_USB_SUPPLY_BKID, "BKID_APP_setting_usb_supply")
        self.assertEqual(P279_USB_SUPPLY_RESID16_HEX, "0x721e")
        self.assertEqual(P279_HDMI_INFO_BKID, "BKID_APP_setting_hdmi_info_display")
        self.assertEqual(P279_HDMI_INFO_RESID16_HEX, "0x6e7c")
        self.assertEqual(P279_HDMI_INFO_RESIDS, {"ON": "0xe07c", "OFF": "0xe297"})
        self.assertEqual(P279_HDMI_INFO_CAUTION_ID, "CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON")
        self.assertEqual(P279_OFF_HDMI_ONLY_RESID16_HEX, "0x6573")
        self.assertEqual(P279_HDMI_RAW_OUTPUT_RESID16_HEX, "0x6e97")
        self.assertEqual(P279_FORMAT_RESID16_HEX, "0xe449")
        self.assertEqual(P279_FORMAT_PROMPT_RESID16_HEX, "0xe414")
        self.assertEqual(P279_FORMAT_MODE_RESIDS, {"QUICK": "0xe792", "FULL": "0xe8f5"})
        self.assertEqual(P279_SLOT1_WP_ERROR_STATUS, "MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1")
        self.assertEqual(P279_IMAGE_JUMP_PROTECT_ONLY_RESID16_HEX, "0x72d1")
        self.assertEqual(P279_FTP_TARGET_PROTECT_RESID16_HEX, "0x694a")
        self.assertEqual(P279_FX6_LOCK_UNLOCK_CLIP_RESID16_HEX, "0x42af")
        self.assertEqual(P279_FX6_FORMAT_MEDIA_RESID16_HEX, "0x4254")
        self.assertEqual(P279_RESET_NW_MENU_RESID16_HEX, "0x60d3")
        self.assertEqual(P279_RESET_NW_SHUTDOWN_BKID, "BKID_APP_is_shutdown_factor_network_reset")
        self.assertEqual(P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX, "0x65d3")
        self.assertEqual(P279_AIRPLANE_MODE_BKID, "BKID_APP_setting_airplane_mode")
        self.assertEqual(P279_AIRPLANE_MODE_ON_RESID16_HEX, "0x6df9")
        self.assertEqual(P279_FX6_NETWORK_RESET_RESID16_HEX, "0x4291")

    def test_03_bounded_donor_inspection_respects_clean_room_and_timing(self) -> None:
        res_clean = inspect_phase279_donors_bounded(force_clean_room=True)
        self.assertTrue(res_clean.passed, res_clean.errors)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res_clean.inspected_artifacts), 6)
        self.assertTrue(res_clean.fx3_im_elf_verified)
        self.assertTrue(res_clean.fx3_libjiritsu_verified)
        self.assertTrue(res_clean.fx3_libusbbuspower_verified)
        self.assertTrue(res_clean.fx6_appfw_verified)
        self.assertTrue(res_clean.fx6_wlan_rsrc_verified)
        self.assertTrue(res_clean.fx3_upm_ko_verified)
        self.assertLess(res_clean.elapsed_seconds, _timing_budget(0.5, 5.0))

    def test_04_bounded_donor_inspection_handles_local_or_missing_donors(self) -> None:
        res = inspect_phase279_donors_bounded(force_clean_room=None)
        self.assertTrue(res.passed, res.errors)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertLess(res.elapsed_seconds, _timing_budget(1.0, 5.0))

    def test_05_clean_room_missing_donor_dir_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no_donors"
            res = inspect_phase279_donors_bounded(
                fx6_lib_dir=missing,
                fx3_modules_dir=missing,
                force_clean_room=None,
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_06_env_clean_room_flags_override_to_synthetic(self) -> None:
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res = inspect_phase279_donors_bounded(force_clean_room=None)
                self.assertTrue(res.passed, res.errors)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_simulated_receipts_build_valid_528b_fx3rcpt1_and_16_h0_baselines(self) -> None:
        ra, rb, h0 = build_simulated_phase279_tier0_receipts()
        self.assertEqual(len(ra), 528)
        self.assertEqual(ra, rb)
        self.assertEqual(ra[:8], b"FX3RCPT1")
        self.assertGreaterEqual(len(h0), 5)

    # --- Check Group A: [USB Connection Mode] 4-Mode vs NOUVC & Data-Isolated USB PD (15 tests) ---

    def test_08_group_a_default_happy_path_sel_when_connect_and_isolated_usb_pd(self) -> None:
        ga = evaluate_p279_check_group_a_usb_connection_mode()
        self.assertTrue(ga.passed, ga.errors)
        self.assertEqual(ga.check_group_id, P279_CHECK_GROUP_A_ID)
        self.assertEqual(ga.usb_connection_mode, "SEL_WHEN_CONNECT")
        self.assertEqual(ga.exposed_usb_modes, P279_FX3_USB_FOUR_MODES)
        self.assertEqual(len(ga.exposed_usb_modes), 4)
        self.assertFalse(ga.usb_streaming_exposed_in_fx3_ui)
        self.assertFalse(ga.dormant_uvc_kmod_insmodded)
        self.assertTrue(ga.usb_data_lines_physically_isolated)
        self.assertTrue(ga.usb_setup_survives_camera_and_network_reset)
        self.assertTrue(ga.usb_setup_resets_on_initialize)

    def test_09_group_a_rejects_wrong_model_id_fw_floor_or_help_guide(self) -> None:
        for kwargs in (
            {"body_model_id": 0x91030000},
            {"body_fw": "1.01"},
            {"body_fw": "invalid"},
            {"sony_help_guide_id": "ilc/2000"},
        ):
            ga = evaluate_p279_check_group_a_usb_connection_mode(**kwargs)
            self.assertFalse(ga.passed)
            self.assertTrue(any(P279_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga.errors))

    def test_10_group_a_fx3_usb_four_modes_exact_and_resids_match(self) -> None:
        self.assertEqual(
            P279_FX3_USB_FOUR_MODES,
            ("SEL_WHEN_CONNECT", "MASS_STORAGE", "MTP", "REMOTE_SHOOTING"),
        )
        self.assertEqual(
            P279_FX3_USB_MODE_RESIDS,
            {
                "SEL_WHEN_CONNECT": "0x7738",
                "MASS_STORAGE": "0x6c54",
                "MTP": "0xe24b",
                "REMOTE_SHOOTING": "0x60aa",
            },
        )
        # Reordered or missing 4 modes fails
        ga_missing = evaluate_p279_check_group_a_usb_connection_mode(
            exposed_usb_modes=("SEL_WHEN_CONNECT", "MASS_STORAGE", "MTP")
        )
        self.assertFalse(ga_missing.passed)
        self.assertTrue(
            any(P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF in e for e in ga_missing.errors)
        )

    def test_11_group_a_rejects_spoofed_usb_streaming_uvc_uac_modes(self) -> None:
        for spoof_mode in P279_DORMANT_NOUVC_MODES:
            ga = evaluate_p279_check_group_a_usb_connection_mode(usb_connection_mode=spoof_mode)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF in e for e in ga.errors)
            )

        for flag_kwargs in (
            {"expect_usb_streaming_uvc": True},
            {"usb_streaming_exposed_in_fx3_ui": True},
            {"dormant_uvc_kmod_insmodded": True},
            {"exposed_usb_modes": (*P279_FX3_USB_FOUR_MODES, "USB_STREAMING")},
            {"usb_conn_bkid": "BKID_WRONG"},
            {"usb_conn_resid16_hex": "0x9999"},
            {"dormant_uvc_kmod_name": "wrong.ko"},
            {"dormant_uvc_kmod_bytes": 1234},
        ):
            ga = evaluate_p279_check_group_a_usb_connection_mode(**flag_kwargs)
            self.assertFalse(ga.passed, f"Expected failure for {flag_kwargs}")
            self.assertTrue(
                any(P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF in e for e in ga.errors)
            )

    def test_12_group_a_airgap_blocks_msc_mtp_remote_shoot_and_usblan(self) -> None:
        self.assertEqual(
            P279_AIRGAP_BLOCKED_DATA_USB_MODES,
            ("MASS_STORAGE", "MTP", "REMOTE_SHOOTING", "USB_LAN"),
        )
        for blocked in (
            "MASS_STORAGE",
            "MassStorage(MSC)",
            "MTP",
            "REMOTE_SHOOT",
            "Remote Shoot (PC Remote)",
            "USB_LAN",
        ):
            ga = evaluate_p279_check_group_a_usb_connection_mode(
                usb_connection_mode=blocked,
                air_gapped_bench=True,
            )
            self.assertFalse(ga.passed, f"Airgap must block {blocked}")
            self.assertTrue(
                any(
                    P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES in e
                    for e in ga.errors
                )
            )

    def test_13_group_a_airgap_blocks_host_usb_data_enumeration_active(self) -> None:
        ga = evaluate_p279_check_group_a_usb_connection_mode(
            host_usb_data_enumeration_active=True,
            air_gapped_bench=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES in e for e in ga.errors)
        )

    def test_14_group_a_non_airgapped_still_requires_valid_stock_mode(self) -> None:
        # In non-airgapped bench (simulation / non-Tier0 inspection), MSC/MTP/Remote are valid stock modes
        for m in ("MASS_STORAGE", "MTP", "REMOTE_SHOOTING"):
            ga = evaluate_p279_check_group_a_usb_connection_mode(
                usb_connection_mode=m,
                air_gapped_bench=False,
            )
            self.assertTrue(ga.passed, ga.errors)

    def test_15_group_a_usb_pd_requires_physically_isolated_data_lines(self) -> None:
        ga_unisolated = evaluate_p279_check_group_a_usb_connection_mode(
            usb_power_supply="ON",
            power_source="USB_PD_BODY",
            usb_data_lines_physically_isolated=False,
            air_gapped_bench=True,
        )
        self.assertFalse(ga_unisolated.passed)
        self.assertTrue(
            any(
                P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES in e
                for e in ga_unisolated.errors
            )
        )

        # Internal battery without USB PD does not fail unisolated USB data lines check
        ga_batt = evaluate_p279_check_group_a_usb_connection_mode(
            usb_power_supply="OFF",
            power_source="INTERNAL_NP_FZ100",
            usb_power_terminal="NONE",
            usb_data_lines_physically_isolated=False,
        )
        self.assertTrue(ga_batt.passed, ga_batt.errors)

    def test_16_group_a_usb_pd_requires_np_fz100_battery_inserted(self) -> None:
        ga = evaluate_p279_check_group_a_usb_connection_mode(
            usb_power_supply="ON",
            power_source="USB_PD_BODY",
            np_fz100_battery_inserted=False,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(
                P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE in e
                for e in ga.errors
            )
        )

    def test_17_group_a_usb_pd_requires_type_c_blocks_multi_micro_usb(self) -> None:
        self.assertEqual(P279_FORBIDDEN_USB_POWER_TERMINALS, ("MULTI_MICRO_USB",))
        self.assertEqual(P279_VALID_USB_POWER_TERMINALS, ("USB_TYPE_C", "NONE"))
        for bad_term in ("MULTI_MICRO_USB", "NONE"):
            ga = evaluate_p279_check_group_a_usb_connection_mode(
                usb_power_supply="ON",
                power_source="USB_PD_BODY",
                usb_power_terminal=bad_term,
            )
            self.assertFalse(ga.passed, f"Expected failure for usb_power_terminal={bad_term}")
            self.assertTrue(
                any(
                    P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE in e
                    for e in ga.errors
                )
            )

    def test_18_group_a_usb_lun_setting_multi_and_single_accepted_invalid_rejected(self) -> None:
        self.assertEqual(P279_VALID_USB_LUN_MODES, ("MULTI", "SINGLE"))
        for lun in P279_VALID_USB_LUN_MODES:
            ga = evaluate_p279_check_group_a_usb_connection_mode(usb_lun_setting=lun)
            self.assertTrue(ga.passed, ga.errors)
            self.assertEqual(ga.usb_lun_setting, lun)

        ga_bad = evaluate_p279_check_group_a_usb_connection_mode(usb_lun_setting="TRIPLE")
        self.assertFalse(ga_bad.passed)
        self.assertTrue(
            any(
                P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE in e
                for e in ga_bad.errors
            )
        )

    def test_19_group_a_usb_power_sources_dc_c1_coupler_and_np_fz100(self) -> None:
        self.assertEqual(
            P279_VALID_POWER_SOURCES,
            ("INTERNAL_NP_FZ100", "USB_PD_BODY", "DC_C1_COUPLER"),
        )
        for src in ("INTERNAL_NP_FZ100", "DC_C1_COUPLER"):
            ga = evaluate_p279_check_group_a_usb_connection_mode(
                usb_power_supply="OFF",
                power_source=src,
                usb_power_terminal="NONE",
            )
            self.assertTrue(ga.passed, ga.errors)

        ga_bad = evaluate_p279_check_group_a_usb_connection_mode(power_source="SOLAR")
        self.assertFalse(ga_bad.passed)

    def test_20_group_a_usb_setup_reset_persistence_boundary(self) -> None:
        self.assertEqual(
            P279_VALID_RESET_ACTIONS,
            ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE"),
        )
        for rst in ("CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE"):
            ga = evaluate_p279_check_group_a_usb_connection_mode(reset_action=rst)
            self.assertTrue(ga.passed, ga.errors)

        for bad_kwargs in (
            {"reset_action": "WIPE_ALL"},
            {"claimed_usb_setup_reset_on_camera_reset": True},
            {"claimed_usb_setup_reset_on_network_reset": True},
            {"claimed_usb_setup_survives_initialize": True},
        ):
            ga_bad = evaluate_p279_check_group_a_usb_connection_mode(**bad_kwargs)
            self.assertFalse(ga_bad.passed)
            self.assertTrue(
                any(
                    P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE in e
                    for e in ga_bad.errors
                )
            )

    def test_21_group_a_usb_mode_aliases_normalized(self) -> None:
        ga = evaluate_p279_check_group_a_usb_connection_mode(
            usb_connection_mode="Select After Connection"
        )
        self.assertTrue(ga.passed, ga.errors)
        self.assertEqual(ga.usb_connection_mode, "SEL_WHEN_CONNECT")

    def test_22_group_a_rejects_unknown_usb_mode(self) -> None:
        ga = evaluate_p279_check_group_a_usb_connection_mode(usb_connection_mode="FIREWIRE")
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF in e for e in ga.errors)
        )

    # --- Check Group B: [HDMI Info. Display] Clean Feed & Log 1080 Clamp vs 4K Override (15 tests) ---

    def test_23_group_b_default_off_clean_hdmi_and_unblanked_lcd(self) -> None:
        gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed()
        self.assertTrue(gb.passed, gb.errors)
        self.assertEqual(gb.check_group_id, P279_CHECK_GROUP_B_ID)
        self.assertEqual(gb.effective_hdmi_info_display, "OFF")
        self.assertFalse(gb.built_in_lcd_blanked)
        self.assertFalse(gb.touch_focus_disabled)
        self.assertFalse(gb.hdmi_osd_letterboxed)
        self.assertTrue(gb.clean_hdmi_feed_active)
        self.assertTrue(gb.hdmi_clamped_to_1080_by_log_or_pplut)
        self.assertEqual(gb.effective_hdmi_output_resolution, "1080_CLAMPED")

    def test_24_group_b_hdmi_info_on_blanks_lcd_disables_touch_focus_and_fails_clean_bench(self) -> None:
        gb_blocked = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            hdmi_info_display="ON"
        )
        self.assertFalse(gb_blocked.passed)
        self.assertTrue(gb_blocked.built_in_lcd_blanked)
        self.assertTrue(gb_blocked.touch_focus_disabled)
        self.assertTrue(gb_blocked.hdmi_osd_letterboxed)
        self.assertFalse(gb_blocked.clean_hdmi_feed_active)
        self.assertTrue(
            any(
                P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT in e
                for e in gb_blocked.errors
            )
        )

    def test_25_group_b_hdmi_info_on_explicitly_permitted_when_allow_blanking_set(self) -> None:
        gb_ok = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            hdmi_info_display="ON",
            allow_lcd_blanking_and_osd=True,
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)
        self.assertTrue(gb_ok.built_in_lcd_blanked)
        self.assertTrue(gb_ok.touch_focus_disabled)
        self.assertTrue(gb_ok.hdmi_osd_letterboxed)

    def test_26_group_b_hdmi_info_on_rejects_touch_focus_or_clean_feed_claims(self) -> None:
        for bad_kwargs in (
            {"expect_touch_focus_active_when_hdmi_info_on": True},
            {"expect_full_raster_clean_feed_when_hdmi_info_on": True},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                hdmi_info_display="ON",
                allow_lcd_blanking_and_osd=True,
                **bad_kwargs,
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT in e
                    for e in gb.errors
                )
            )

    def test_27_group_b_rejects_wrong_bkid_resid_or_invalid_hdmi_info_mode(self) -> None:
        for bad_kwargs in (
            {"hdmi_info_bkid": "BKID_WRONG"},
            {"hdmi_info_resid16_hex": "0x0000"},
            {"hdmi_info_display": "AUTO"},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(**bad_kwargs)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT in e
                    for e in gb.errors
                )
            )

    def test_28_group_b_internal_rec_log_and_pplut1_to_4_clamp_hdmi_to_1080(self) -> None:
        self.assertEqual(P279_ACTIVE_LOG_SHOOTING_MODES, ("CINE_EI_QUICK", "CINE_EI", "FLEXIBLE_ISO"))
        self.assertEqual(P279_PPLUT_PROFILES, ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"))
        for log_m in P279_ACTIVE_LOG_SHOOTING_MODES:
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                rec_media_dur_hdmi_output="ON",
                log_shooting_mode=log_m,
                hdmi_output_resolution="AUTO",
            )
            self.assertTrue(gb.passed, gb.errors)
            self.assertTrue(gb.hdmi_clamped_to_1080_by_log_or_pplut)
            self.assertEqual(gb.effective_hdmi_output_resolution, "1080_CLAMPED")

        for pp_lut in P279_PPLUT_PROFILES:
            gb_pp = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                rec_media_dur_hdmi_output="ON",
                log_shooting_mode="OFF",
                picture_profile=pp_lut,
                hdmi_output_resolution="AUTO",
            )
            self.assertTrue(gb_pp.passed, gb_pp.errors)
            self.assertTrue(gb_pp.hdmi_clamped_to_1080_by_log_or_pplut)
            self.assertEqual(gb_pp.effective_hdmi_output_resolution, "1080_CLAMPED")

    def test_29_group_b_rejects_4k_2160p_during_internal_log_or_pplut(self) -> None:
        for bad_kwargs in (
            {"log_shooting_mode": "CINE_EI", "hdmi_output_resolution": "2160P"},
            {"log_shooting_mode": "OFF", "picture_profile": "PPLUT1", "hdmi_output_resolution": "2160P"},
            {"log_shooting_mode": "CINE_EI", "expect_4k_hdmi_during_internal_log_or_pplut": True},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                rec_media_dur_hdmi_output="ON", **bad_kwargs
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE in e
                    for e in gb.errors
                )
            )

    def test_30_group_b_off_hdmi_only_outputs_4k_and_forces_hdmi_info_off(self) -> None:
        gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            hdmi_info_display="ON",
            rec_media_dur_hdmi_output="OFF(HDMI Only)",
            log_shooting_mode="CINE_EI",
        )
        self.assertTrue(gb.passed, gb.errors)
        self.assertTrue(gb.hdmi_info_forced_off_by_raw_or_hdmi_only)
        self.assertEqual(gb.effective_hdmi_info_display, "OFF")
        self.assertFalse(gb.built_in_lcd_blanked)
        self.assertTrue(gb.clean_hdmi_feed_active)
        self.assertFalse(gb.hdmi_clamped_to_1080_by_log_or_pplut)
        self.assertEqual(gb.effective_hdmi_output_resolution, "4K_HDMI_ONLY_10BIT")

    def test_31_group_b_raw_output_on_outputs_4k_and_forces_hdmi_info_off(self) -> None:
        gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            hdmi_info_display="ON",
            hdmi_raw_output=True,
            rec_media_dur_hdmi_output="ON",
            log_shooting_mode="CINE_EI",
        )
        self.assertTrue(gb.passed, gb.errors)
        self.assertTrue(gb.hdmi_info_forced_off_by_raw_or_hdmi_only)
        self.assertEqual(gb.effective_hdmi_info_display, "OFF")
        self.assertFalse(gb.built_in_lcd_blanked)
        self.assertEqual(gb.effective_hdmi_output_resolution, "4K_16BIT_RAW")

    def test_32_group_b_rejects_claiming_hdmi_info_on_during_raw_or_hdmi_only(self) -> None:
        for kw in (
            {"hdmi_raw_output": True},
            {"rec_media_dur_hdmi_output": "OFF_HDMI_ONLY"},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                expect_hdmi_info_on_during_raw_or_hdmi_only=True, **kw
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT in e
                    for e in gb.errors
                )
            )

    def test_33_group_b_sq_mode_locks_out_raw_and_off_hdmi_only(self) -> None:
        for bad_kwargs in (
            {"shoot_mode": "S_AND_Q", "hdmi_raw_output": True},
            {"shoot_mode": "S_AND_Q", "rec_media_dur_hdmi_output": "OFF_HDMI_ONLY"},
            {"shoot_mode": "S_AND_Q", "expect_sq_allows_hdmi_only_or_raw": True},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(**bad_kwargs)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE in e
                    for e in gb.errors
                )
            )

    def test_34_group_b_rec_media_off_no_log_allows_4k_2160p_compatible(self) -> None:
        gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            rec_media_dur_hdmi_output="OFF",
            log_shooting_mode="OFF",
            picture_profile="PP11",
            hdmi_output_resolution="2160P",
        )
        self.assertTrue(gb.passed, gb.errors)
        self.assertFalse(gb.hdmi_clamped_to_1080_by_log_or_pplut)
        self.assertEqual(gb.effective_hdmi_output_resolution, "4K_2160P_COMPATIBLE")

    def test_35_group_b_explicit_1080p_and_1080i_resolution_respected(self) -> None:
        for res_mode in ("1080P", "1080I"):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
                log_shooting_mode="OFF",
                hdmi_output_resolution=res_mode,
            )
            self.assertTrue(gb.passed, gb.errors)
            self.assertEqual(gb.effective_hdmi_output_resolution, res_mode)

    def test_36_group_b_setup_reset_survival_and_framing_settings_hdmi_exception(self) -> None:
        self.assertEqual(P279_FRAMING_SETTINGS_HDMI_RESET_EXCEPTION, "Framing Settings (HDMI)")
        gb_ok = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
            reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)
        self.assertTrue(gb_ok.hdmi_setup_survives_camera_and_network_reset)
        self.assertTrue(gb_ok.framing_settings_hdmi_resets_on_camera_reset)

        for bad_kwargs in (
            {"claimed_hdmi_setup_reset_on_camera_reset": True},
            {"claimed_hdmi_setup_reset_on_network_reset": True},
            {"claimed_framing_settings_hdmi_survives_camera_reset": True},
            {"reset_action": "BOGUS"},
        ):
            gb_bad = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(**bad_kwargs)
            self.assertFalse(gb_bad.passed)
            self.assertTrue(
                any(
                    P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION in e
                    for e in gb_bad.errors
                )
            )

    def test_37_group_b_invalid_rec_media_shoot_log_or_output_res_rejected(self) -> None:
        for bad_kwargs in (
            {"rec_media_dur_hdmi_output": "INVALID"},
            {"shoot_mode": "TIMELAPSE"},
            {"log_shooting_mode": "SLOG2"},
            {"hdmi_output_resolution": "8K"},
        ):
            gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(**bad_kwargs)
            self.assertFalse(gb.passed)

    # --- Check Group C: [Protect] 4 Scopes vs [Format] Override & Dual-Layer Slot-1 WP (11 tests) ---

    def test_38_group_c_default_happy_path_4_scopes_and_dual_layer_slot1_wp(self) -> None:
        gc = evaluate_p279_check_group_c_protect_vs_format_slot1()
        self.assertTrue(gc.passed, gc.errors)
        self.assertEqual(gc.check_group_id, P279_CHECK_GROUP_C_ID)
        self.assertEqual(gc.protect_four_scopes, P279_PROTECT_FOUR_SCOPES)
        self.assertEqual(len(gc.protect_four_scopes), 4)
        self.assertTrue(gc.protected_items_block_delete)
        self.assertTrue(gc.copy_strips_protection_verified)
        self.assertTrue(gc.format_overrides_protect_and_m1_m4_verified)
        self.assertTrue(gc.slot1_wp_locked)
        self.assertTrue(gc.slot1_format_hard_locked)
        self.assertEqual(gc.slot1_wp_error_status, P279_SLOT1_WP_ERROR_STATUS)
        self.assertEqual(gc.slot1_vault_delete_events, 0)

    def test_39_group_c_all_four_protect_scopes_and_aliases_accepted(self) -> None:
        for scope in (
            *P279_PROTECT_FOUR_SCOPES,
            "SINGLE_MULTIPLE_IMG",
            "SINGLE",
            "MULTIPLE_IMG",
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(protect_scope_selected=scope)
            self.assertTrue(gc.passed, f"Scope {scope} failed: {gc.errors}")

    def test_40_group_c_rejects_missing_or_unknown_protect_scope(self) -> None:
        for bad_kwargs in (
            {"protect_exposed_scopes": P279_PROTECT_FOUR_SCOPES[:3]},
            {"protect_scope_selected": "PROTECT_ALL_SLOTS"},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID in e
                    for e in gc.errors
                )
            )

    def test_41_group_c_rejects_delete_bypass_copy_preserve_or_movie_key_no_menu(self) -> None:
        for bad_kwargs in (
            {"protected_items_block_delete": False},
            {"expect_copy_preserves_protect": True},
            {"expect_movie_key_mark_without_menu": True},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID in e
                    for e in gc.errors
                )
            )

    def test_42_group_c_rejects_claiming_protect_blocks_format_or_preserves_m1_m4(self) -> None:
        for bad_kwargs in (
            {"expect_protect_blocks_format": True},
            {"expect_format_preserves_m1_m4_camset": True},
            {"format_resid16_hex": "0x0000"},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL in e
                    for e in gc.errors
                )
            )

    def test_43_group_c_requires_slot1_physical_wp_lock_and_status(self) -> None:
        for bad_kwargs in (
            {"slot1_wp_locked": False},
            {"slot1_wp_error_status": "MR_MEMORY_OK"},
            {"slot1_contains_tier0_dump": False},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL in e
                    for e in gc.errors
                )
            )

    def test_44_group_c_requires_software_format_hard_lock_and_firewall(self) -> None:
        for bad_kwargs in (
            {"slot1_format_hard_locked": False},
            {"slot1_vault_write_firewall_enforced": False},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL in e
                    for e in gc.errors
                )
            )

    def test_45_group_c_hard_blocks_slot1_quick_or_full_format(self) -> None:
        for fmt in ("QUICK", "FULL", "BOGUS"):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(slot1_format_mode=fmt)
            self.assertFalse(gc.passed)
            self.assertGreaterEqual(gc.slot1_vault_delete_events, 1)
            self.assertTrue(
                any(
                    P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL in e
                    for e in gc.errors
                )
            )

    def test_46_group_c_hard_blocks_slot1_delete_requested_and_simulated_events(self) -> None:
        for bad_kwargs in (
            {"slot1_delete_requested": True},
            {"simulated_slot1_vault_delete_events": 1},
        ):
            gc = evaluate_p279_check_group_c_protect_vs_format_slot1(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertGreaterEqual(gc.slot1_vault_delete_events, 1)

    def test_47_group_c_protect_scope_resids_match_empirical_wave47(self) -> None:
        self.assertEqual(
            P279_PROTECT_SCOPE_RESIDS,
            {
                "SINGLE_OR_MULTIPLE_IMG": "0xe2ca",
                "ALL_IN_THIS_FOLDER": "0x6848",
                "ALL_WITH_THIS_DATE": "0x69f7",
                "ALL_IMAGES_IN_THIS_GROUP": "0xe826",
            },
        )
        self.assertEqual(P279_FORMAT_MODES, ("NONE", "QUICK", "FULL"))

    def test_48_group_c_dual_layer_wp_even_when_protect_only_scope_changed(self) -> None:
        gc = evaluate_p279_check_group_c_protect_vs_format_slot1(
            protect_scope_selected="ALL_IMAGES_IN_THIS_GROUP",
            slot1_wp_locked=True,
            slot1_format_hard_locked=True,
            slot1_format_mode="NONE",
        )
        self.assertTrue(gc.passed, gc.errors)

    # --- Check Group D: [Reset Network Set.] Auto-Reboot, Airplane Mode, 3-Way Boundary & Tier-0 (12 tests) ---

    def test_49_group_d_three_way_reset_domains_complete(self) -> None:
        self.assertEqual(len(P279_RESET_NW_CLEARED_DOMAINS), 6)
        self.assertEqual(len(P279_RESET_NW_PRESERVED_DOMAINS), 6)
        gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed, gd.errors)
        self.assertEqual(tier0_err, ())
        self.assertTrue(gd.auto_reboot_triggered_on_network_reset)
        self.assertTrue(gd.three_way_reset_boundary_verified)
        self.assertEqual(gd.post_reboot_airplane_mode, "ON")
        self.assertTrue(gd.zero_rf_bench_authorized)
        self.assertEqual(gd.passive_tx_bytes_emitted, 0)
        self.assertEqual(gd.h0_equals_h3_count, 16)
        self.assertEqual(gd.h0_h3_surface_count, 16)
        self.assertTrue(gd.tier0_receipt_verified)

    def test_50_group_d_blocks_missing_network_reset_execution_or_auto_reboot(self) -> None:
        for bad_kwargs in (
            {"reset_network_set_executed": False},
            {"auto_reboot_triggered_on_network_reset": False},
            {"reset_nw_shutdown_bkid": "BKID_WRONG"},
            {"reset_nw_autoreboot_prompt_resid16_hex": "0x0000"},
        ):
            gd, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(gd.passed)
            self.assertTrue(
                any(
                    P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION in e
                    for e in gd.errors
                )
            )

    def test_51_group_d_blocks_any_3way_reset_boundary_violation(self) -> None:
        for flag in (
            "wifi_psks_cleared",
            "bt_pairings_cleared",
            "ftp_cloud_certs_cleared",
            "streaming_rtmp_srt_cleared",
            "network_reset_resets_airplane_to_off",
            "network_reset_preserves_shooting_setup_playback_camset",
            "camera_reset_resets_shooting_and_framing_hdmi",
            "camera_reset_preserves_network_setup_playback_camset",
            "initialize_clears_all_except_card_m1_m4",
        ):
            gd, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
                simulate_bench_dry_run=True, **{flag: False}
            )
            self.assertFalse(gd.passed, f"3-way boundary flag {flag}=False must fail")
            self.assertFalse(gd.three_way_reset_boundary_verified)

    def test_52_group_d_requires_post_reboot_airplane_mode_on_and_zero_passive_tx(self) -> None:
        for bad_kwargs in (
            {"post_reboot_airplane_mode": "OFF"},
            {"post_reboot_airplane_mode": "INVALID"},
            {"airplane_mode_on_resid16_hex": "0x0000"},
            {"simulated_passive_tx_bytes": 32},
        ):
            gd, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(gd.passed)
            self.assertFalse(gd.zero_rf_bench_authorized)
            self.assertTrue(
                any(
                    P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION in e
                    for e in gd.errors
                )
            )

    def test_53_group_d_h0_h3_16_surface_drift_blocked(self) -> None:
        gd, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            simulated_h0_h3_drifted_surfaces=2,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_h3_surface_count, 16)
        self.assertEqual(gd.h0_equals_h3_count, 14)
        self.assertTrue(any(P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd.errors))

    def test_54_group_d_offline_no_receipts_fails_closed_cleanly(self) -> None:
        gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            simulate_bench_dry_run=False
        )
        self.assertTrue(gd.passed)
        self.assertFalse(gd.tier0_receipt_present)
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertTrue(
            any(P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in tier0_err)
        )

    def test_55_group_d_valid_dual_media_receipts_verified_distinct_st_dev(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertTrue(gd.passed)
        self.assertEqual(tier0_err, ())
        self.assertTrue(gd.tier0_receipt_verified)
        self.assertTrue(gd.distinct_physical_media_verified)

    def test_56_group_d_same_st_dev_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=77,
            st_dev_b_override=77,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertFalse(gd.distinct_physical_media_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in tier0_err))

    def test_57_group_d_corrupt_crc_or_mismatched_receipt_bytes_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        corrupt = bytearray(raw_b)
        corrupt[-1] ^= 0xFF
        gd_mismatch, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=bytes(corrupt),
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_mismatch.tier0_receipt_verified)
        self.assertTrue(tier0_err)

        gd_crc, tier0_crc = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=bytes(corrupt),
            receipt_b_bytes=bytes(corrupt),
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_crc.tier0_receipt_verified)
        self.assertTrue(any("CRC32" in e for e in tier0_crc))

    def test_58_group_d_trivial_serial_cid_or_missing_h0_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        gd_ser, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial="0000000",
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_ser.tier0_receipt_verified)

        gd_h0, _ = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=None,
            h0_baselines_b=None,
        )
        self.assertFalse(gd_h0.tier0_receipt_verified)

    def test_59_group_d_h0_key_mismatch_or_trivial_digest_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        bad_h0 = dict(h0)
        first_key = next(iter(bad_h0))
        bad_h0[first_key] = "0" * 64
        gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=bad_h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertTrue(any("invalid/mismatched H0" in e for e in tier0_err))

    def test_60_group_d_missing_receipt_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gd, tier0_err = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
                receipt_a_path=Path(tmp) / "missing_a.bin",
                receipt_b_path=Path(tmp) / "missing_b.bin",
            )
            self.assertFalse(gd.tier0_receipt_verified)
            self.assertTrue(any("read failed" in e for e in tier0_err))

    # --- Orchestrator, Tamper Verification, Markdown & CLI / Subprocess (10 tests) ---

    def test_61_orchestrator_offline_default_fail_closed_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=False,
            )
            self.assertEqual(rep.overall_status, P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
            self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertFalse(rep.tier0_receipt_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.usb_streaming_exposed_in_fx3_ui)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase279_report(rep.to_dict()).valid)

    def test_62_orchestrator_simulate_bench_dry_run_passes_4of4_16of16_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=True,
            )
            self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.check_groups_passed, 4)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertEqual(rep.h0_h3_surface_count, 16)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertTrue(verify_phase279_report(rep.to_dict()).valid)

    def test_63_orchestrator_distinct_device_receipts_verify_readonly_preflight(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase279_tier0_receipts()
        rep = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(
            rep.go_no_go,
            P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
        )
        self.assertEqual(
            rep.overall_status,
            P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(verify_phase279_report(rep.to_dict()).valid)

    def test_64_orchestrator_check_failure_populates_remediations_and_blocks(self) -> None:
        rep = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            hdmi_info_display="ON",
        )
        self.assertEqual(
            rep.go_no_go,
            P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE,
        )
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertTrue(rep.remediation_actions)
        self.assertTrue(verify_phase279_report(rep.to_dict()).valid)

    def test_65_verify_phase279_report_catches_locks_passive_tx_spoof_and_sha_tampering(self) -> None:
        base = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        ).to_dict()

        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "sd_physical_media_written",
            "usb_streaming_exposed_in_fx3_ui",
        ):
            mutated = dict(base)
            mutated[lock_key] = True
            self.assertFalse(verify_phase279_report(mutated).valid, f"Failed to catch {lock_key}")

        for zero_key in (
            "usb_packets_transmitted",
            "physical_usb_packets_emitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            mutated = dict(base)
            mutated[zero_key] = 1
            self.assertFalse(verify_phase279_report(mutated).valid, f"Failed to catch {zero_key}")

        escalated = dict(base)
        escalated["go_no_go"] = P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED
        self.assertFalse(verify_phase279_report(escalated).valid)

        bad_sha = dict(base)
        bad_sha["report_sha256"] = "a" * 64
        self.assertFalse(verify_phase279_report(bad_sha).valid)

    def test_66_deterministic_sha256_and_markdown_rendering(self) -> None:
        r1 = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase279_markdown(r1)
        for token in (
            PHASE_279_SCHEMA,
            P279_CHECK_GROUP_A_ID,
            P279_CHECK_GROUP_B_ID,
            P279_CHECK_GROUP_C_ID,
            P279_CHECK_GROUP_D_ID,
            r1.report_sha256,
        ):
            self.assertIn(token, md)

    def test_67_cli_offline_default_fails_closed_exit_2_ready_offline_awaiting_receipts(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(
                [
                    "preflight-usb-mode-hdmi-info-protect-and-network-reset",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], PHASE_279_SCHEMA)
        self.assertEqual(
            payload["overall_status"], P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        )
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["hardware_live_attachment_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_68_cli_simulate_bench_dry_run_emits_deterministic_json_and_markdown_exit_0(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p279.json"
            md_path = Path(tmp) / "p279.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-usb-mode-hdmi-info-protect-and-network-reset",
                        "--simulate-bench-dry-run",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            out_line = buf.getvalue()
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", out_line)
            self.assertIn("go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", out_line)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase279_report(loaded).valid)
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_279_SCHEMA, md_text)

    def test_69_cli_blocks_violations_across_all_4_groups_and_same_dev_receipts_exit_2(
        self,
    ) -> None:
        for extra_flags in (
            ["--usb-mode", "MASS_STORAGE"],
            ["--expect-usb-streaming-uvc"],
            ["--hdmi-info-display", "ON"],
            ["--slot1-wp-unlocked"],
            ["--slot1-format-mode", "QUICK"],
            ["--post-reboot-airplane-mode", "OFF"],
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-usb-mode-hdmi-info-protect-and-network-reset",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        *extra_flags,
                    ]
                )
            self.assertEqual(rc, 2, f"Expected exit 2 for {extra_flags}")
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["go_no_go"],
                P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE,
            )

        raw_a, raw_b, _ = build_simulated_phase279_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "rcpt_a.bin"
            pb = Path(tmp) / "rcpt_b.bin"
            pa.write_bytes(raw_a)
            pb.write_bytes(raw_b)
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-usb-mode-hdmi-info-protect-and-network-reset",
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
                    ]
                )
            self.assertEqual(rc, 2)
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["go_no_go"],
                P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE,
            )
            self.assertTrue(
                any(
                    P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e
                    for e in payload["errors"]
                )
            )

    def test_70_cli_subprocess_portable_sys_executable_timing(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(REPO_ROOT / "outputs/fx6-on-fx3-closure"),
                str(REPO_ROOT / "outputs/fx3-safety"),
                str(REPO_ROOT / "outputs/fx3-recovery-adapter"),
                str(REPO_ROOT / "outputs/fx3-firmware-lab"),
                str(REPO_ROOT / "outputs/fx3-vm"),
            ]
        )
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-usb-mode-hdmi-info-protect-and-network-reset",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, _timing_budget(6.0, 15.0))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], PHASE_279_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase279_report(payload).valid)


if __name__ == "__main__":
    unittest.main()
