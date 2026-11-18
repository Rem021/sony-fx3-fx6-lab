"""Dual-mode unit tests (100 cases) for Phase 329 (`preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter`):
15th Real-Hardware Physical Bench Readiness Verifier across Waves 62-63 check groups (`A..D`)
including Wave-42 Bird & APS-C S35 Reset errata and Slot-1 BODYDATA.DAT NO-GO firewall.

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
    TARGET_MODEL_ID_INT,
)
from fx6_closure.realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier import (  # noqa: E402
    P329_APSC_LOCKED_OUT_4K_FORMATS,
    P329_AUDIO_OUT_TIMING_RESID16_HEX,
    P329_AUDIO_REC_LEVEL_DEFAULT,
    P329_CHECK_GROUP_A_ID,
    P329_CHECK_GROUP_B_ID,
    P329_CHECK_GROUP_C_ID,
    P329_CHECK_GROUP_D_ID,
    P329_DESQUEEZE_1_65X_DESC_RESID16_HEX,
    P329_DESQUEEZE_1_6X_EXECUTED_FACTOR,
    P329_DESQUEEZE_EXACT_FIVE_STATES,
    P329_DESQUEEZE_FOUR_LOCKOUTS,
    P329_DESQUEEZE_SIX_BYPASS_CONDITIONS,
    P329_DORMANT_4K_24P_8BIT_RESID16_HEX,
    P329_DORMANT_AI_SUBJECTS,
    P329_DORMANT_REC_LAMP_ONLY_ONE_RESID16_HEX,
    P329_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX,
    P329_DORMANT_VAR_SHUTTER_RESIDS,
    P329_ERRNO_EOPNOTSUPP,
    P329_ERRNO_EPERM,
    P329_ERRNO_EROFS,
    P329_FACE_EYE_SUBJECT_RESID16_HEX,
    P329_FACE_EYE_SUBJECT_VALID_TWO,
    P329_FACE_MEMORY_MAX_SLOTS,
    P329_FX6_ECS_MAX_HZ,
    P329_FX6_ECS_MIN_HZ,
    P329_FX6_HDMI_RAW_RESOLUTION_WH,
    P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY,
    P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME,
    P329_GA_ERR_MODEL_OR_FW_FLOOR,
    P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF,
    P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL,
    P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE,
    P329_GB_ERR_DORMANT_SHUTTER_WHEN_PWR_OFF,
    P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH,
    P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE,
    P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION,
    P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION,
    P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS,
    P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT,
    P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION,
    P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP,
    P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA,
    P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT,
    P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW,
    P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT,
    P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE,
    P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED,
    P329_HDMI_RAW_BIT_DEPTH,
    P329_HDMI_RAW_RESOLUTION_WH,
    P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS,
    P329_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P329_PROXY_AUDIO_CODEC,
    P329_PROXY_CUTOFF_FPS,
    P329_REC_LAMP_THREE_STATES,
    P329_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX,
    P329_REMOVED_COLOR_GAMUT_FOR_RAW_RESID16_HEX,
    P329_SCHEMA,
    P329_SHOE_AUDIO_SET_RESID16_HEX,
    P329_SILENT_MODE_FIVE_DISABLED_FUNCTIONS,
    P329_SONY_HELP_GUIDE_ID,
    P329_TARGET_FUNCTION_EXACT_TWO_ITEMS,
    P329_VALID_MAIN_XAVC_CODECS,
    PHASE329_E_ND_ACTUATOR_TX_COUNT,
    PHASE329_PASSIVE_TX_BYTES_EMITTED,
    PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE329_SLOT1_DATA_SECTOR_WRITES,
    PHASE329_USB_PACKETS_TRANSMITTED,
    PHASE329_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_329_CHECK_GROUP_IDS,
    PHASE_329_SCHEMA,
    _canonical_sha256_dict,
    build_simulated_phase329_tier0_receipts,
    evaluate_p329_check_group_a_shoe_audio_and_subject_recog,
    evaluate_p329_check_group_b_silent_target_and_bodydata_firewall,
    evaluate_p329_check_group_c_hdmi_raw_desqueeze,
    evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0,
    evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
    inspect_phase329_donors_bounded,
    render_phase329_markdown,
    run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
    verify_phase329_report,
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
            "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase329Preflight15Verifier(unittest.TestCase):
    def _assert_err(self, res: object, err_prefix: str) -> None:
        errors = getattr(res, "errors")
        self.assertTrue(
            any(e == err_prefix or e.startswith(f"{err_prefix}:") for e in errors),
            f"Expected error starting with {err_prefix!r} in {errors!r}",
        )

    # ------------------------------------------------------------------
    # 01-10: Exports, Schema, Dual-Modes, Donorless CI & Bounded O_RDONLY
    # ------------------------------------------------------------------

    def test_01_top_level_package_exports_phase329_symbols(self) -> None:
        self.assertEqual(fx6_closure.PHASE_329_SCHEMA, P329_SCHEMA)
        self.assertEqual(
            fx6_closure.P329_SCHEMA_VERSION,
            "realhw_preflight15_shoe_audio_subject_hdmi_raw_desqueeze_varshutter_v1",
        )
        self.assertIs(
            fx6_closure.run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
            run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
        )
        self.assertIs(fx6_closure.verify_phase329_report, verify_phase329_report)
        self.assertEqual(len(PHASE_329_CHECK_GROUP_IDS), 4)

    def test_02_offline_default_blocks_live_attach_awaiting_tier0(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight()
        self.assertEqual(rep.overall_status, P329_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.check_group_count, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertTrue(verify_phase329_report(rep).valid)

    def test_03_simulate_bench_dry_run_passes_without_live_auth(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep.simulate_bench_dry_run)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "DRY_RUN_SIMULATED")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase329_report(rep.to_dict()).valid)

    def test_04_physical_dual_media_receipts_verify_with_distinct_st_dev(self) -> None:
        ser = "FX3702BENCH329"
        cid = "150100424a4e42345201020304050608"
        sim = build_simulated_phase329_tier0_receipts(body_serial=ser, emmc_cid=cid)
        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "slot_a_FX3RCPT1.bin"
            p_b = Path(td) / "slot_b_FX3RCPT1.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])
            rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=1001,
                st_dev_b_override=2002,
                body_serial=ser,
                emmc_cid=cid,
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
                h3_baselines=sim["h3_baselines"],
            )
        self.assertEqual(rep.go_no_go, P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.receipt_mode, "PHYSICAL_DUAL_MEDIA_528B")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase329_report(rep).valid)

    def test_05_clean_room_env_flags_force_synthetic_determinism(self) -> None:
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
                    simulate_bench_dry_run=True,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(rep.donor_inspection.bytes_read_total, 0)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
                self.assertTrue(verify_phase329_report(rep).valid)

    def test_06_donorless_work_root_none_falls_back_cleanly_without_typeerror(self) -> None:
        with mock.patch(
            "fx6_closure.realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier.iter_work_roots",
            return_value=(),
        ):
            res = inspect_phase329_donors_bounded(
                force_clean_room=False,
                work_root=None,
                fx6_lib_dir=None,
                fx3_modules_dir=None,
            )
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertFalse(res.donor_tree_present)
            self.assertEqual(res.bytes_read_total, 0)
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
                simulate_bench_dry_run=True,
                work_root=None,
                fx6_lib_dir=None,
                fx3_modules_dir=None,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_bounded_donor_inspection_is_fast_and_o_rdonly(self) -> None:
        t0 = time.monotonic()
        res = inspect_phase329_donors_bounded(force_clean_room=False)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.20)
        self.assertTrue(res.within_budget)
        self.assertLessEqual(res.bytes_read_total, 320)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_08_zero_unconditional_redline_constants(self) -> None:
        self.assertEqual(PHASE329_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE329_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE329_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE329_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE329_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE329_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(P329_SONY_HELP_GUIDE_ID, "ilc/2210")

    def test_09_wrong_model_id_body_fw_or_help_guide_blocked(self) -> None:
        rep_bad_model = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
            body_model_id=0x91030001,
        )
        self.assertFalse(rep_bad_model.check_group_a.passed)
        self._assert_err(rep_bad_model.check_group_a, P329_GA_ERR_MODEL_OR_FW_FLOOR)
        rep_bad_fw = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
            body_fw="6.00",
        )
        self._assert_err(rep_bad_fw.check_group_a, P329_GA_ERR_MODEL_OR_FW_FLOOR)
        rep_bad_hg = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
            sony_help_guide_id="ilc/9999",
        )
        self._assert_err(rep_bad_hg.check_group_a, P329_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_10_deterministic_sha256_invariant_across_runs(self) -> None:
        r1 = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
        )
        r2 = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
            force_clean_room=True,
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(render_phase329_markdown(r1), render_phase329_markdown(r2))
        d1 = json.loads(r1.to_deterministic_json())
        d2 = json.loads(r2.to_deterministic_json())
        d1["donor_inspection"].pop("elapsed_seconds", None)
        d2["donor_inspection"].pop("elapsed_seconds", None)
        self.assertEqual(d1, d2)

    # ------------------------------------------------------------------
    # 11-32: Check Group A (Wave 62 Audio & Subject Recognition)
    # ------------------------------------------------------------------

    def test_11_group_a_audio_out_timing_live_and_lip_sync_pass(self) -> None:
        self.assertEqual(P329_AUDIO_OUT_TIMING_RESID16_HEX, "0x6bc2")
        for timing in ("LIVE", "LIP_SYNC"):
            res = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                audio_out_timing=timing,
            )
            self.assertTrue(res.passed, f"{timing} should pass: {res.errors}")

    def test_12_group_a_rejects_audio_out_timing_under_setup_sound_option(self) -> None:
        res = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            claimed_audio_out_timing_under_setup_sound_option=True,
        )
        self.assertFalse(res.passed)
        self._assert_err(res, P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY)

    def test_13_group_a_rejects_audio_recording_or_timing_active_in_sq(self) -> None:
        res1 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            audio_out_timing_active_in_sq_claimed=True,
        )
        res2 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            audio_recording_in_sq_claimed=True,
        )
        res3 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            claimed_audio_out_timing_resists_reset=True,
        )
        for r in (res1, res2, res3):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY)

    def test_14_group_a_rejects_removed_audio_level_display_0x7a36(self) -> None:
        self.assertEqual(P329_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX, "0x7a36")
        res1 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            dormant_audio_level_display_requested=True,
        )
        res2 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            fx3_audio_level_display_menu_present_claimed=True,
        )
        for r in (res1, res2):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY)

    def test_15_group_a_audio_rec_level_0_31_and_limiter_rules(self) -> None:
        self.assertEqual(P329_AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertTrue(evaluate_p329_check_group_a_shoe_audio_and_subject_recog(audio_rec_level=0).passed)
        self.assertTrue(evaluate_p329_check_group_a_shoe_audio_and_subject_recog(audio_rec_level=31).passed)
        for bad_kwargs in (
            {"audio_rec_level": -1},
            {"audio_rec_level": 32},
            {"fx3_disable_builtin_limiter_requested": True},
            {"fx3_limiter_6step_present_claimed": True},
            {"fx3_32bit_float_audio_claimed": True},
        ):
            r = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY)

    def test_16_group_a_shoe_audio_4ch_valid_across_all_6_main_xavc_codecs(self) -> None:
        self.assertEqual(P329_SHOE_AUDIO_SET_RESID16_HEX, "0x77f6")
        self.assertEqual(len(P329_VALID_MAIN_XAVC_CODECS), 6)
        for codec in P329_VALID_MAIN_XAVC_CODECS:
            r = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                movie_file_format=codec,
                shoe_audio_set="48KHZ_24BIT_4CH",
            )
            self.assertTrue(r.passed, f"{codec} failed: {r.errors}")

    def test_17_group_a_rejects_claiming_4ch_unsupported_on_xavc_or_proxy_4ch(self) -> None:
        r1 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            claimed_shoe_4ch_unsupported_on_xavc_codec=True,
        )
        r2 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            proxy_recording="ON",
            expect_proxy_4ch_24bit_audio=True,
        )
        self.assertFalse(r1.passed)
        self.assertFalse(r2.passed)
        self._assert_err(r1, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)
        self._assert_err(r2, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)

    def test_18_group_a_proxy_audio_aac_2ch_and_100p_cutoff(self) -> None:
        self.assertEqual(P329_PROXY_AUDIO_CODEC, "MPEG4_AAC_LC_2CH_128KBPS")
        self.assertEqual(P329_PROXY_CUTOFF_FPS, 100.0)
        ok_59 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            proxy_recording="ON",
            rec_fps=59.94,
        )
        self.assertTrue(ok_59.passed)
        self.assertEqual(ok_59.proxy_audio_codec, P329_PROXY_AUDIO_CODEC)
        bad_100 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            proxy_recording="ON",
            rec_fps=100.0,
        )
        bad_sq_120 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            proxy_recording="ON",
            sq_enabled=True,
            sq_fps=120.0,
        )
        bad_claim = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            expect_proxy_active_at_100p_plus=True,
        )
        for r in (bad_100, bad_sq_120, bad_claim):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)

    def test_19_group_a_35mm_mic_hardware_override_grays_out_shoe_audio(self) -> None:
        ok = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            mic_35mm_inserted=True,
            expect_shoe_audio_active_with_35mm_mic=False,
        )
        self.assertTrue(ok.passed)
        bad = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            mic_35mm_inserted=True,
            expect_shoe_audio_active_with_35mm_mic=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)

    def test_20_group_a_xlr_h1_handle_off_fallback_and_analog_16bit_2ch_cap(self) -> None:
        ok_off = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="OFF",
        )
        self.assertTrue(ok_off.passed)
        bad_off = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="OFF",
            expect_xlr_h1_audio_active_when_handle_off=True,
        )
        self.assertFalse(bad_off.passed)
        ok_analog = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_dig_analog="ANALOG",
            shoe_audio_set="48KHZ_16BIT_2CH",
        )
        self.assertTrue(ok_analog.passed)
        bad_analog_24 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_dig_analog="ANALOG",
            shoe_audio_set="48KHZ_24BIT_4CH",
        )
        self.assertFalse(bad_analog_24.passed)
        self._assert_err(bad_analog_24, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)

    def test_21_group_a_wind_noise_reduct_builtin_mic_only(self) -> None:
        ok = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(wind_noise_reduct="ON")
        self.assertTrue(ok.passed)
        bad = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            wind_noise_reduct="ON",
            expect_wind_noise_applies_to_xlr_or_35mm=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF)

    def test_22_group_a_face_eye_subject_only_human_and_animal(self) -> None:
        self.assertEqual(P329_FACE_EYE_SUBJECT_RESID16_HEX, "0x70fa")
        self.assertEqual(P329_FACE_EYE_SUBJECT_VALID_TWO, ("HUMAN", "ANIMAL"))
        self.assertTrue(
            evaluate_p329_check_group_a_shoe_audio_and_subject_recog(face_eye_subject="HUMAN").passed
        )
        self.assertTrue(
            evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                shoot_mode="PHOTO", face_eye_subject="ANIMAL"
            ).passed
        )
        bad = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(face_eye_subject="BIRD")
        self.assertFalse(bad.passed)
        self._assert_err(bad, P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL)

    def test_23_group_a_wave42_bird_errata_rejects_all_5_dormant_ai_subjects(self) -> None:
        self.assertEqual(
            P329_DORMANT_AI_SUBJECTS,
            ("BIRD", "ANIMAL_BIRD", "INSECT", "CAR_TRAIN", "AIRPLANE"),
        )
        for subj in P329_DORMANT_AI_SUBJECTS:
            r = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                dormant_subject_requested=subj,
            )
            self.assertFalse(r.passed, f"{subj} must trigger EOPNOTSUPP={P329_ERRNO_EOPNOTSUPP}")
            self._assert_err(r, P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL)
        r_claim = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            fx3_bird_insect_car_airplane_present_claimed=True,
        )
        self.assertFalse(r_claim.passed)

    def test_24_group_a_animal_eye_af_still_only_blocked_in_movie_and_sq(self) -> None:
        for mode in ("MOVIE", "S_AND_Q"):
            r = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                shoot_mode=mode,
                face_eye_subject="ANIMAL",
                expect_animal_eye_af_in_movie=True,
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL)
        r_claim = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            fx3_animal_eye_af_in_movie_present_claimed=True,
        )
        self.assertFalse(r_claim.passed)

    def test_25_group_a_face_memory_8_slots_and_reset_camset_rules(self) -> None:
        self.assertEqual(P329_FACE_MEMORY_MAX_SLOTS, 8)
        self.assertTrue(
            evaluate_p329_check_group_a_shoe_audio_and_subject_recog(face_memory_count=8).passed
        )
        for bad_kwargs in (
            {"face_memory_count": -1},
            {"face_memory_count": 9},
            {"claimed_face_memory_wiped_by_camera_reset": True},
            {"claimed_face_memory_exported_in_camset": True},
            {"expect_regist_faces_priority_active_in_animal": True},
        ):
            r = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME)

    def test_26_group_a_clean_hdmi_never_leaks_face_eye_frame(self) -> None:
        bad = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            face_eye_frame_disp="ON",
            expect_face_eye_frame_on_clean_hdmi=True,
        )
        self.assertFalse(bad.passed)
        self._assert_err(bad, P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME)

    def test_27_group_a_rejects_fx6_animal_bird_or_face_memory_claims(self) -> None:
        r1 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            fx6_has_animal_or_bird_subject_claimed=True,
        )
        r2 = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            fx6_has_persistent_face_memory_claimed=True,
        )
        self.assertFalse(r1.passed)
        self.assertFalse(r2.passed)

    def test_28_group_a_eye_select_and_4ch_monitoring_enum_validation(self) -> None:
        self.assertFalse(
            evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                right_left_eye_select="CENTER_EYE"
            ).passed
        )
        self.assertFalse(
            evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
                four_ch_audio_monitoring="CH99"
            ).passed
        )

    def test_29_group_a_xlr_h1_in1_mono_routing_and_4ch_digital_pass(self) -> None:
        ok = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_dig_analog="DIGITAL",
            xlr_h1_input_select="IN1",
            shoe_audio_set="48KHZ_24BIT_4CH",
            four_ch_audio_monitoring="CH1_3_CH2_4",
        )
        self.assertTrue(ok.passed)

    def test_30_group_a_camera_reset_preserves_face_memory_and_resets_audio_out_timing(self) -> None:
        ok = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            reset_action="CAMERA_SETTINGS_RESET",
            audio_out_timing="LIVE",
            face_memory_count=5,
        )
        self.assertTrue(ok.passed)

    def test_31_group_a_animal_in_photo_does_not_force_movie_error(self) -> None:
        ok = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
            shoot_mode="PHOTO",
            face_eye_subject="ANIMAL",
            expect_animal_eye_af_in_movie=False,
        )
        self.assertTrue(ok.passed)

    def test_32_group_a_invalid_shoot_mode_fails_closed(self) -> None:
        bad = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(shoot_mode="RAW_BURST")
        self.assertFalse(bad.passed)
        self._assert_err(bad, P329_GA_ERR_MODEL_OR_FW_FLOOR)

    # ------------------------------------------------------------------
    # 33-52: Check Group B (Wave 62 Silent Mode, Target Func, No Pwr-Off Shutter, Version, BODYDATA Firewall)
    # ------------------------------------------------------------------

    def test_33_group_b_silent_mode_5_lockouts_enforced(self) -> None:
        self.assertEqual(len(P329_SILENT_MODE_FIVE_DISABLED_FUNCTIONS), 5)
        for bad_kwargs in (
            {"silent_mode": "ON", "shutter_type": "MECHANICAL_SHUTTER"},
            {"silent_mode": "ON", "audio_signals": "ON"},
            {"silent_mode": "ON", "flash_enabled": True},
            {"silent_mode": "ON", "long_exposure_nr": "ON"},
            {"silent_mode": "ON", "e_front_curtain_shut": "ON"},
            {"silent_mode": "ON", "bulb_enabled": True},
            {"silent_mode": "ON", "anti_flicker_shoot": "ON"},
        ):
            r = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(**bad_kwargs)
            self.assertFalse(r.passed, f"{bad_kwargs} must fail under Silent Mode=ON")
            self._assert_err(r, P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH)

    def test_34_group_b_rejects_silent_mode_false_claims(self) -> None:
        r1 = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            claimed_silent_mode_auto_disables_af_illuminator=True,
        )
        r2 = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            claimed_silent_mode_is_single_bool_toggle=True,
        )
        self.assertFalse(r1.passed)
        self.assertFalse(r2.passed)
        self._assert_err(r1, P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH)
        self._assert_err(r2, P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH)

    def test_35_group_b_silent_mode_off_permits_mechanical_shutter(self) -> None:
        ok = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            silent_mode="OFF",
            audio_signals="ON",
            shutter_type="MECHANICAL_SHUTTER",
        )
        self.assertTrue(ok.passed)

    def test_36_group_b_target_function_exact_2_items(self) -> None:
        self.assertEqual(
            P329_TARGET_FUNCTION_EXACT_TWO_ITEMS,
            ("APERTURE_DRIVE_IN_AF", "AUTO_PIXEL_MAPPING"),
        )
        bad_extra = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            exposed_target_function_items=("APERTURE_DRIVE_IN_AF", "AUTO_PIXEL_MAPPING", "SHUTTER_WHEN_PWR_OFF"),
        )
        bad_one = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            exposed_target_function_items=("APERTURE_DRIVE_IN_AF",),
        )
        self.assertFalse(bad_extra.passed)
        self.assertFalse(bad_one.passed)
        self._assert_err(bad_extra, P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE)

    def test_37_group_b_auto_pixel_mapping_off_guards_cnflasha(self) -> None:
        bad_not_target = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            target_auto_pixel_mapping="NOT_TARGET",
        )
        bad_cnflasha = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            cnflasha_write_on_poweroff_allowed=True,
        )
        bad_movie_ap = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            expect_aperture_drive_silent_in_movie=True,
        )
        for r in (bad_not_target, bad_cnflasha, bad_movie_ap):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE)

    def test_38_group_b_dormant_shutter_when_pwr_off_0x709f_eopnotsupp(self) -> None:
        self.assertEqual(P329_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX, "0x709f")
        for bad_kwargs in (
            {"dormant_shutter_when_pwr_off_requested": True},
            {"fx3_shutter_when_pwr_off_present_claimed": True},
            {"fx6_shutter_when_pwr_off_present_claimed": True},
        ):
            r = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GB_ERR_DORMANT_SHUTTER_WHEN_PWR_OFF)

    def test_39_group_b_zero_rf_version_badge_silenced(self) -> None:
        for bad_kwargs in (
            {"airplane_mode": "OFF"},
            {"wifi_enabled": True},
            {"wireless_rf_packets_emitted": 1},
            {"version_update_badge_active": True},
        ):
            r = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION)

    def test_40_group_b_hard_no_go_bodydata_slot1_flash_firewall(self) -> None:
        for bad_kwargs in (
            {"slot1_bodydata_stage_requested": True},
            {"software_update_trigger_requested": True},
            {"slot1_bodydata_writes": 1},
            {"cross_model_flash_requested": True},
            {"bodydata_in_slot2_claimed": True},
        ):
            r = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE)
            self.assertFalse(r.emmc_writes_authorized)
            self.assertFalse(r.cross_model_flash_authorized)

    def test_41_group_b_stepping_stone_v202_requires_v204_v205(self) -> None:
        bad_uncompleted = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            source_fw_for_update_audit="2.02",
            stepping_stone_v204_v205_completed=False,
        )
        self.assertFalse(bad_uncompleted.passed)
        self.assertTrue(bad_uncompleted.stepping_stone_fw_required)
        self._assert_err(bad_uncompleted, P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE)
        bad_direct = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            direct_v202_to_v702_flash_claimed=True,
        )
        self.assertFalse(bad_direct.passed)
        ok_completed = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            source_fw_for_update_audit="2.02",
            stepping_stone_v204_v205_completed=True,
        )
        self.assertTrue(ok_completed.passed)
        self.assertTrue(ok_completed.stepping_stone_fw_required)

    def test_42_group_b_battery_soc_floor_and_fx6_slot_b_ac_adaptor(self) -> None:
        bad_soc = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(battery_soc_pct=49.0)
        bad_fx6_slot = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            fx6_update_slot_claimed="SLOT_A"
        )
        bad_fx6_batt = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            fx6_battery_only_update_claimed=True
        )
        for r in (bad_soc, bad_fx6_slot, bad_fx6_batt):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE)

    def test_43_group_b_aperture_drive_silent_priority_ok_in_still_photo(self) -> None:
        ok = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            shoot_mode="PHOTO",
            target_aperture_drive_in_af="SILENT_PRIORITY",
            expect_aperture_drive_silent_in_movie=False,
        )
        self.assertTrue(ok.passed)

    def test_44_group_b_silent_mode_off_allows_still_antiflicker_only(self) -> None:
        ok = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            shoot_mode="PHOTO",
            silent_mode="OFF",
            audio_signals="ON",
            shutter_type="MECHANICAL_SHUTTER",
            anti_flicker_shoot="ON",
        )
        self.assertTrue(ok.passed)

    def test_45_group_b_policy_string_always_hard_blocked(self) -> None:
        ok = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall()
        self.assertIn("HARD_NO_GO_BLOCKED", ok.bodydata_flash_policy)
        self.assertEqual(ok.rf_packets_transmitted, 0)

    def test_46_group_b_negative_rf_packet_count_fails_closed(self) -> None:
        bad = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            wireless_rf_packets_emitted=-1,
        )
        self.assertFalse(bad.passed)

    def test_47_group_b_invalid_target_enum_rejected(self) -> None:
        bad1 = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            target_aperture_drive_in_af="TURBO",
        )
        bad2 = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            target_auto_pixel_mapping="AUTO_POWER_ON",
        )
        self.assertFalse(bad1.passed)
        self.assertFalse(bad2.passed)

    def test_48_group_b_fw_v105_and_v200_also_require_stepping_stone(self) -> None:
        for fw in ("1.05", "2.00"):
            bad = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
                source_fw_for_update_audit=fw,
                stepping_stone_v204_v205_completed=False,
            )
            self.assertFalse(bad.passed)
            self.assertTrue(bad.stepping_stone_fw_required)

    def test_49_group_b_camera_settings_reset_resets_silent_mode_and_targets(self) -> None:
        ok = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ok.passed)

    def test_50_group_b_slot1_bodydata_without_tier0_still_hard_blocked(self) -> None:
        bad = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            slot1_contains_tier0_dump=False,
            slot1_bodydata_stage_requested=True,
        )
        self.assertFalse(bad.passed)

    def test_51_group_b_cross_model_flash_always_false_on_report(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
        )
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_52_group_b_unrecognized_shutter_type_fails(self) -> None:
        bad = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
            shutter_type="GLOBAL_SHUTTER",
        )
        self.assertFalse(bad.passed)

    # ------------------------------------------------------------------
    # 53-72: Check Group C (Wave 63 HDMI 16-bit RAW Co-Rec Vault & Ver. 7.00+ De-Squeeze)
    # ------------------------------------------------------------------

    def test_53_group_c_exact_8_hdmi_settings_and_removed_color_gamut(self) -> None:
        self.assertEqual(len(P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS), 8)
        self.assertEqual(P329_REMOVED_COLOR_GAMUT_FOR_RAW_RESID16_HEX, "0x6bdc")
        bad_items = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            exposed_hdmi_settings_items=("RAW_OUTPUT",),
        )
        bad_gamut = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            dormant_color_gamut_for_raw_requested=True,
        )
        bad_gamut_claim = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            fx3_color_gamut_for_raw_present_claimed=True,
        )
        bad_reset = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            claimed_hdmi_settings_wiped_by_camera_reset=True,
        )
        for r in (bad_items, bad_gamut, bad_gamut_claim, bad_reset):
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT)

    def test_54_group_c_hdmi_16bit_raw_4264x2408_corec_slot2_ok_slot1_blocked(self) -> None:
        self.assertEqual(P329_HDMI_RAW_RESOLUTION_WH, "4264x2408")
        self.assertEqual(P329_HDMI_RAW_BIT_DEPTH, 16)
        ok_slot2 = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_raw_output="ON",
            rec_media_dur_hdmi_output="ON",
            recording_media="SLOT_2",
        )
        self.assertTrue(ok_slot2.passed, ok_slot2.errors)
        for bad_slot1 in (
            {"hdmi_raw_output": "ON", "rec_media_dur_hdmi_output": "ON", "recording_media": "SLOT_1"},
            {"hdmi_raw_output": "ON", "rec_media_dur_hdmi_output": "ON", "recording_media": "SIMULTANEOUS_RECORDING"},
            {"internal_co_rec_write_to_slot1_requested": True},
            {"slot1_data_sector_writes": 1},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_slot1)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP)

    def test_55_group_c_off_hdmi_only_allows_4k_without_card_writes(self) -> None:
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            hdmi_output_resolution="2160P",
            hdmi_4k_setting="59.94P_10BIT",
        )
        self.assertTrue(ok.passed)
        bad_write = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            expect_internal_writes_during_hdmi_only=True,
        )
        self.assertFalse(bad_write.passed)

    def test_56_group_c_log_pplut_rec_on_clamps_hdmi_to_1080p(self) -> None:
        bad_2160p = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output="OFF",
            hdmi_output_resolution="2160P",
        )
        bad_claim = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="ON",
            expect_4k_hdmi_with_rec_on_during_log_or_pplut=True,
        )
        self.assertFalse(bad_2160p.passed)
        self.assertFalse(bad_claim.passed)

    def test_57_group_c_4k_output_10bit_only_rejects_dormant_24p_8bit_0x748a(self) -> None:
        self.assertEqual(P329_DORMANT_4K_24P_8BIT_RESID16_HEX, "0x748a")
        for bad_kwargs in (
            {"dormant_4k_24p_8bit_requested": True},
            {"fx3_4k_24p_8bit_present_claimed": True},
            {"hdmi_4k_setting": "24.00P_8BIT"},
            {"expect_24p_no_reboot": True},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP)

    def test_58_group_c_hdmi_rec_control_requires_timecode_output_on(self) -> None:
        bad = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_rec_control="ON",
            hdmi_time_code_output="OFF",
        )
        self.assertFalse(bad.passed)
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_rec_control="ON",
            hdmi_time_code_output="ON",
        )
        self.assertTrue(ok.passed)

    def test_59_group_c_hdmi_info_display_on_blanks_fx3_lcd(self) -> None:
        bad_unack = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_info_display="ON",
            allow_lcd_blanking_for_hdmi_info=False,
        )
        bad_stay_on = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_info_display="ON",
            allow_lcd_blanking_for_hdmi_info=True,
            expect_fx3_lcd_stays_on_when_hdmi_info_on=True,
        )
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_info_display="ON",
            allow_lcd_blanking_for_hdmi_info=True,
        )
        self.assertFalse(bad_unack.passed)
        self.assertFalse(bad_stay_on.passed)
        self.assertTrue(ok.passed)

    def test_60_group_c_fx6_sdi_raw_hdmi_raw_4240x2392_and_remote_if_distinctions(self) -> None:
        self.assertEqual(P329_FX6_HDMI_RAW_RESOLUTION_WH, "4240x2392")
        for bad_kwargs in (
            {"fx6_sdi_raw_allows_4k_hdmi_claimed": True},
            {"fx6_hdmi_raw_supports_24_00p_claimed": True},
            {"fx6_remote_if_syncs_internal_card_claimed": True},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION)

    def test_61_group_c_desqueeze_exact_5_states_and_1_6x_equals_1_65x(self) -> None:
        self.assertEqual(P329_DESQUEEZE_EXACT_FIVE_STATES, ("OFF", "1.3X", "1.5X", "1.6X", "2.0X"))
        self.assertEqual(P329_DESQUEEZE_1_6X_EXECUTED_FACTOR, 1.65)
        self.assertEqual(P329_DESQUEEZE_1_65X_DESC_RESID16_HEX, "0x7d0c")
        for ratio, expected in (("OFF", 1.0), ("1.3X", 1.3), ("1.5X", 1.5), ("1.6X", 1.65), ("2.0X", 2.0)):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(desqueeze_display=ratio)
            self.assertTrue(r.passed, f"{ratio} failed: {r.errors}")
            self.assertAlmostEqual(r.desqueeze_executed_factor, expected)

    def test_62_group_c_desqueeze_rejects_absent_1_8x_and_wrong_1_6x_factor(self) -> None:
        for bad_kwargs in (
            {"desqueeze_display": "1.8X"},
            {"dormant_desqueeze_1_8x_requested": True},
            {"fx3_desqueeze_1_8x_present_claimed": True},
            {"desqueeze_display": "1.6X", "desqueeze_1_6x_executed_factor": 1.6},
            {"claimed_desqueeze_wiped_by_camera_reset": True},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS)

    def test_63_group_c_desqueeze_4_hard_lockouts_enforced(self) -> None:
        self.assertEqual(len(P329_DESQUEEZE_FOUR_LOCKOUTS), 4)
        for bad_kwargs in (
            {"desqueeze_display": "1.6X", "focus_mode": "AF_C"},
            {"desqueeze_display": "1.6X", "focus_area": "CENTER_FIX"},
            {"desqueeze_display": "1.6X", "steadyshot_mode": "STANDARD"},
            {"desqueeze_display": "1.6X", "face_priority_in_multi_metering": "ON"},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION)

    def test_64_group_c_desqueeze_still_bake_bypass_and_coexistence_rules(self) -> None:
        self.assertEqual(len(P329_DESQUEEZE_SIX_BYPASS_CONDITIONS), 6)
        for bad_kwargs in (
            {"shoot_mode": "PHOTO", "desqueeze_display": "1.5X"},
            {"expect_desqueeze_active_in_still": True},
            {"expect_desqueeze_bakes_internal_file": True},
            {"expect_desqueeze_applied_during_bypass": True},
            {"claimed_desqueeze_locks_out_focus_mag_or_bright_mon": True},
        ):
            r = evaluate_p329_check_group_c_hdmi_raw_desqueeze(**bad_kwargs)
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION)
        r_fx6 = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            fx6_desqueeze_has_1_6x_or_sdi_claimed=True,
        )
        self.assertFalse(r_fx6.passed)
        self._assert_err(r_fx6, P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS)

    def test_65_group_c_desqueeze_auto_bypass_with_log_off_still_allowed(self) -> None:
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            desqueeze_display="2.0X",
            log_shooting_mode="OFF",
            expect_desqueeze_applied_during_bypass=False,
        )
        self.assertTrue(ok.passed)

    def test_66_group_c_hdmi_raw_with_log_off_does_not_trip_1080p_clamp(self) -> None:
        ok_raw_cine_ei = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="CINE_EI",
            picture_profile="OFF",
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output="ON",
            hdmi_output_resolution="2160P",
            recording_media="SLOT_2",
        )
        self.assertTrue(ok_raw_cine_ei.passed, ok_raw_cine_ei.errors)
        ok_log_off_no_raw = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="OFF",
            picture_profile="OFF",
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output="OFF",
            hdmi_output_resolution="2160P",
            recording_media="SLOT_2",
        )
        self.assertTrue(ok_log_off_no_raw.passed, ok_log_off_no_raw.errors)
        bad_raw_with_log_off = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="OFF",
            picture_profile="OFF",
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output="ON",
            recording_media="SLOT_2",
        )
        self.assertFalse(bad_raw_with_log_off.passed)
        self._assert_err(
            bad_raw_with_log_off,
            P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP,
        )

    def test_67_group_c_pplut1_clamps_hdmi_to_1080p_when_rec_media_on(self) -> None:
        bad = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            log_shooting_mode="OFF",
            picture_profile="PPLUT1",
            rec_media_dur_hdmi_output="ON",
            hdmi_output_resolution="2160P",
        )
        self.assertFalse(bad.passed)

    def test_68_group_c_raw_output_info_display_forced_off_no_blanking(self) -> None:
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            hdmi_raw_output="ON",
            hdmi_info_display="OFF",
        )
        self.assertTrue(ok.passed)

    def test_69_group_c_invalid_hdmi_4ch_route_rejected(self) -> None:
        bad = evaluate_p329_check_group_c_hdmi_raw_desqueeze(hdmi_4ch_audio_output="CH5_CH6")
        self.assertFalse(bad.passed)

    def test_70_group_c_raw_output_setting_all_6_framerates_valid(self) -> None:
        for fps in ("59.94P", "50P", "29.97P", "25P", "23.98P", "24.00P"):
            ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
                hdmi_raw_output="ON",
                raw_output_setting=fps,
            )
            self.assertTrue(ok.passed, f"{fps} failed")

    def test_71_group_c_desqueeze_camera_reset_preserves_state(self) -> None:
        ok = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            reset_action="CAMERA_SETTINGS_RESET",
            desqueeze_display="1.6X",
            desqueeze_1_6x_executed_factor=1.65,
        )
        self.assertTrue(ok.passed)

    def test_72_group_c_slot1_unlocked_still_blocks_slot1_write_when_tier0_present(self) -> None:
        bad = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=False,
            recording_media="SLOT_1",
        )
        self.assertFalse(bad.passed)

    # ------------------------------------------------------------------
    # 73-90: Check Group D (Wave 63 REC Lamp, Var. Shutter vs ECS, APS-C Reset Errata & Tier-0)
    # ------------------------------------------------------------------

    def test_73_group_d_rec_lamp_3_states_and_dormant_tally_light_0x743e(self) -> None:
        self.assertEqual(P329_REC_LAMP_THREE_STATES, ("ALL_ON", "ONLY_FRONT_OFF", "ALL_OFF"))
        self.assertEqual(P329_DORMANT_REC_LAMP_ONLY_ONE_RESID16_HEX, "0x743e")
        for state in P329_REC_LAMP_THREE_STATES:
            ok = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True,
                rec_lamp_mode=state,
            )
            self.assertTrue(ok.passed)
        for bad_kwargs in (
            {"rec_lamp_mode": "ONLY_REAR_OFF"},
            {"dormant_tally_light_menu_requested": True},
            {"fx3_tally_light_menu_present_claimed": True},
            {"dormant_rec_lamp_only_one_requested": True},
            {"claimed_rec_lamp_wiped_by_camera_reset": True},
            {"expect_top_rec_ring_off_with_rear_on": True},
            {"claimed_silent_mode_turns_off_rec_lamp": True},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT)

    def test_74_group_d_emphasized_rec_display_resettable_and_clean_hdmi_safe(self) -> None:
        for bad_kwargs in (
            {"claimed_emph_rec_resists_camera_reset": True},
            {"expect_emph_rec_on_clean_hdmi": True},
            {"emphasized_rec_display": "RED_HDMI"},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW)

    def test_75_group_d_remain_shoot_display_and_auto_review_rules(self) -> None:
        for bad_kwargs in (
            {"claimed_remain_shoot_wiped_by_camera_reset": True},
            {"expect_remain_shoot_shows_movie_time": True},
            {"interval_shooting_active": True, "expect_auto_review_in_interval": True},
            {"claimed_auto_review_wiped_by_camera_reset": True},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW)

    def test_76_group_d_dormant_var_shutter_0x6831_and_antiflicker_split(self) -> None:
        self.assertIn("0x6831", P329_DORMANT_VAR_SHUTTER_RESIDS)
        for bad_kwargs in (
            {"dormant_var_shutter_requested": True},
            {"fx3_var_shutter_present_claimed": True},
            {"fx3_has_ecs_mode_claimed": True},
            {"shoot_mode": "MOVIE", "anti_flicker_shoot": "ON"},
            {"shoot_mode": "PHOTO", "silent_mode": "ON", "anti_flicker_shoot": "ON"},
            {"shoot_mode": "PHOTO", "shutter_type": "ELECTRONIC_SHUTTER", "anti_flicker_shoot": "ON"},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT)

    def test_77_group_d_fx6_ecs_freq_range_23_99_to_8000_hz(self) -> None:
        self.assertEqual(P329_FX6_ECS_MIN_HZ, 23.99)
        self.assertEqual(P329_FX6_ECS_MAX_HZ, 8000.0)
        self.assertTrue(
            evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, fx6_ecs_freq_hz=23.99
            ).passed
        )
        self.assertTrue(
            evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, fx6_ecs_freq_hz=8000.0
            ).passed
        )
        bad_low = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True, fx6_ecs_freq_hz=12.0
        )
        bad_high = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True, fx6_ecs_freq_hz=9000.0
        )
        self.assertFalse(bad_low.passed)
        self.assertFalse(bad_high.passed)

    def test_78_group_d_wave42_apsc_s35_reset_errata_and_4k_lockout(self) -> None:
        self.assertEqual(len(P329_APSC_LOCKED_OUT_4K_FORMATS), 4)
        for fmt in P329_APSC_LOCKED_OUT_4K_FORMATS:
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True,
                apsc_s35_shooting="ON",
                movie_file_format=fmt,
            )
            self.assertFalse(r.passed, f"{fmt} must be locked out in APS-C S35=ON")
            self._assert_err(r, P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA)
        ok_hd = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True,
            apsc_s35_shooting="ON",
            movie_file_format="XAVC_S_HD",
            rec_fps=119.88,
        )
        self.assertTrue(ok_hd.passed)

    def test_79_group_d_apsc_s35_blocks_hdmi_raw_4k_and_still_l_12m_and_not_resettable(self) -> None:
        for bad_kwargs in (
            {"apsc_s35_shooting": "ON", "movie_file_format": "XAVC_S_HD", "hdmi_raw_output": "ON"},
            {"apsc_s35_shooting": "ON", "movie_file_format": "XAVC_S_HD", "hdmi_4k_only_active": True},
            {"apsc_s35_shooting": "ON", "movie_file_format": "XAVC_S_HD", "expect_apsc_4k_or_raw": True},
            {"claimed_apsc_wiped_by_camera_reset": True},
            {"claimed_apsc_still_size_4_2m": True},
            {"apsc_s35_shooting": "ON", "shoot_mode": "PHOTO", "movie_file_format": "XAVC_S_HD", "still_image_size": "L_12M"},
            {"apsc_s35_shooting": "ON", "movie_file_format": "XAVC_S_HD", "still_image_size": "M_4_2M"},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA)

    def test_80_group_d_apsc_still_m_5_1m_passes(self) -> None:
        ok = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True,
            shoot_mode="PHOTO",
            apsc_s35_shooting="ON",
            movie_file_format="XAVC_S_HD",
            still_image_size="M_5_1M",
        )
        self.assertTrue(ok.passed)

    def test_81_group_d_identical_st_dev_dual_media_receipt_rejected(self) -> None:
        ser = "FX3702BENCH329"
        cid = "150100424a4e42345201020304050608"
        sim = build_simulated_phase329_tier0_receipts(body_serial=ser, emmc_cid=cid)
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=4242,
            st_dev_b_override=4242,
            body_serial=ser,
            emmc_cid=cid,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(r.passed)
        self._assert_err(r, P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_82_group_d_corrupted_528b_receipt_rejected(self) -> None:
        ser = "FX3702BENCH329"
        cid = "150100424a4e42345201020304050608"
        sim = build_simulated_phase329_tier0_receipts(body_serial=ser, emmc_cid=cid)
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"][:128],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=ser,
            emmc_cid=cid,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(r.passed)
        self._assert_err(r, P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_83_group_d_h0_h3_drift_detected_and_fails_closed(self) -> None:
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=1,
        )
        self.assertFalse(r.passed)
        self.assertEqual(r.h0_equals_h3_count, 15)
        self._assert_err(r, P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_84_group_d_h0_vs_h3_baseline_dict_mismatch_fails_closed(self) -> None:
        sim = build_simulated_phase329_tier0_receipts()
        drifted_h3 = dict(sim["h3_baselines"])
        drifted_h3["nflasha5"] = "a" * 64
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=drifted_h3,
        )
        self.assertFalse(r.passed)
        self.assertEqual(r.h0_equals_h3_count, 15)
        self._assert_err(r, P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_85_group_d_non_zero_e_nd_usb_or_passive_tx_rejected(self) -> None:
        for bad_kwargs in (
            {"e_nd_actuator_tx_count": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_86_group_d_claim_live_attach_emmc_or_cross_model_flash_rejected(self) -> None:
        for bad_kwargs in (
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(r.passed)
            self._assert_err(r, P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_87_group_d_trivial_serial_or_cid_rejected_for_physical_receipts(self) -> None:
        sim = build_simulated_phase329_tier0_receipts()
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial="00000000",
            emmc_cid="150100424a4e42345201020304050608",
        )
        self.assertFalse(r.passed)
        self._assert_err(r, P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_88_group_d_single_receipt_missing_pair_fails_closed(self) -> None:
        sim = build_simulated_phase329_tier0_receipts()
        r = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
        )
        self.assertFalse(r.passed)
        self._assert_err(r, P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_89_group_d_still_mechanical_antiflicker_passes_when_silent_off(self) -> None:
        ok = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True,
            shoot_mode="PHOTO",
            silent_mode="OFF",
            shutter_type="MECHANICAL_SHUTTER",
            anti_flicker_shoot="ON",
        )
        self.assertTrue(ok.passed)

    def test_90_group_d_apsc_auto_review_and_remain_shoot_enumerated(self) -> None:
        bad_rem = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True, remain_shoot_display="INVALID_MODE"
        )
        bad_rev = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
            simulate_bench_dry_run=True, auto_review="99_SEC"
        )
        self.assertFalse(bad_rem.passed)
        self.assertFalse(bad_rev.passed)

    # ------------------------------------------------------------------
    # 91-100: Report Verifier, Markdown Determinism & CLI End-to-End Tests
    # ------------------------------------------------------------------

    def test_91_verify_phase329_report_catches_sha_tamper(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
        ).to_dict()
        self.assertTrue(verify_phase329_report(rep).valid)
        tampered = copy.deepcopy(rep)
        tampered["report_sha256"] = "0" * 64
        v = verify_phase329_report(tampered)
        self.assertFalse(v.valid)

    def test_92_verify_phase329_report_catches_leaked_bytes_or_live_attach_override(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
        ).to_dict()
        for field, val in (
            ("raw_firmware_bytes_leaked", 4),
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("cross_model_flash_authorized", True),
            ("slot1_tier0_vault_mutated", True),
            ("fx3_var_shutter_present", True),
            ("fx3_apsc_resets_via_camera_settings_reset", True),
        ):
            tampered = copy.deepcopy(rep)
            tampered[field] = val
            tampered["report_sha256"] = _canonical_sha256_dict(tampered)
            self.assertFalse(verify_phase329_report(tampered).valid, f"{field}={val} must fail verify")

    def test_93_render_phase329_markdown_contains_core_sections_and_zero_leak(self) -> None:
        rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
            simulate_bench_dry_run=True,
        )
        md = render_phase329_markdown(rep)
        self.assertIn(P329_SCHEMA, md)
        self.assertIn("48kHz / 24-bit 4ch", md)
        self.assertIn("Human` / `Animal`", md)
        self.assertIn("BODYDATA.DAT", md)
        self.assertIn("1.6x` = `1.65x", md)
        self.assertIn("0x6831", md)
        self.assertIn("M: 5.1M", md)
        self.assertEqual(md, render_phase329_markdown(rep))

    def test_94_cli_inprocess_help_passes(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            fx6_cli_main(["preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_95_cli_inprocess_dry_run_json_and_summary(self) -> None:
        buf_json = io.StringIO()
        with mock.patch("sys.stdout", buf_json):
            rc = fx6_cli_main([
                "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--json",
            ])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["schema_version"], P329_SCHEMA)
        self.assertEqual(parsed["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase329_report(parsed).valid)

        buf_sum = io.StringIO()
        with mock.patch("sys.stdout", buf_sum):
            rc2 = fx6_cli_main([
                "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--summary",
            ])
        self.assertEqual(rc2, 0)
        self.assertIn("var_shutter=False", buf_sum.getvalue())
        self.assertIn("apsc_reset=False", buf_sum.getvalue())

    def test_96_cli_writes_output_json_and_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "p329.json"
            out_md = Path(td) / "p329.md"
            rc = fx6_cli_main([
                "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--output",
                str(out_json),
                "--markdown-out",
                str(out_md),
                "--summary",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase329_report(data).valid)
            self.assertIn(P329_SCHEMA, out_md.read_text(encoding="utf-8"))

    def test_97_cli_fails_closed_exit_code_2_on_offline_and_violation(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc_off = fx6_cli_main([
                "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
                "--force-clean-room",
            ])
        self.assertEqual(rc_off, 2)
        self.assertIn(GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, buf.getvalue())

        buf_err = io.StringIO()
        with mock.patch("sys.stdout", buf_err):
            rc_bad = fx6_cli_main([
                "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter",
                "--simulate-bench-dry-run",
                "--force-clean-room",
                "--dormant-var-shutter-requested",
            ])
        self.assertEqual(rc_bad, 2)
        self.assertIn(P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE, buf_err.getvalue())

    def test_98_cli_subprocess_clean_room_and_fx3_clean_room_test_modes(self) -> None:
        for env_flag in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            cp = _run_cli_subprocess(
                ["--simulate-bench-dry-run", "--json"],
                extra_env={env_flag: "1"},
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_99_cli_subprocess_blocks_bodydata_and_bird_and_desqueeze_18x(self) -> None:
        for flag in (
            "--slot1-bodydata-stage-requested",
            "--dormant-subject-requested=BIRD",
            "--dormant-desqueeze-1-8x-requested",
            "--claimed-apsc-wiped-by-camera-reset",
        ):
            cp = _run_cli_subprocess(
                ["--simulate-bench-dry-run", "--force-clean-room", flag, "--json"],
            )
            self.assertEqual(cp.returncode, 2)
            data = json.loads(cp.stdout)
            self.assertEqual(
                data["go_no_go"],
                P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE,
            )

    def test_100_cli_subprocess_donorless_work_root_fallback(self) -> None:
        cp = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase329/ci/work_root"},
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertIn(data["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(verify_phase329_report(data).valid)

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
        cp_ci = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                (
                    "import sys; from unittest import mock; "
                    "import fx6_closure.realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier as m; "
                    "from fx6_closure.__main__ import main; "
                    "mock.patch.object(m, 'iter_work_roots', return_value=()).start(); "
                    "sys.exit(main(['preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter', "
                    "'--simulate-bench-dry-run', '--fx6-lib-dir', '/nonexistent/fx6_lib', "
                    "'--fx3-modules-dir', '/nonexistent/fx3_mod', '--json']))"
                ),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(cp_ci.returncode, 0, cp_ci.stderr)
        ci_data = json.loads(cp_ci.stdout)
        self.assertEqual(ci_data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(ci_data["donor_inspection"]["bytes_read_total"], 0)
        self.assertTrue(verify_phase329_report(ci_data).valid)


if __name__ == "__main__":
    unittest.main()
