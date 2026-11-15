"""Phase 210 Dual-Mode Unit Tests (>=50 tests):
Gates G75 (`G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD`),
G76 (`G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD`),
and Unified 76-Gate Master Safety Preflight (`verify-76-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard import (
    ALLOWED_4K_HDMI_ONLY_FORMATS,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    G75,
    G75_GATE_CODE,
    G75_GATE_ID,
    G76,
    G76_GATE_CODE,
    G76_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PINNED_PHASE210_DONOR_SPECS,
    PPLUT_PICTURE_PROFILES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_SCHEMA,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION,
    STATUS_BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED,
    STATUS_BLOCKED_G75_HDMI_ONLY_INTERNAL_CARD_REC_FORBIDDEN,
    STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID,
    STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM,
    STATUS_BLOCKED_G75_TELEMETRY_INVALID,
    STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION,
    STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION,
    STATUS_BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED,
    STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION,
    STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID,
    STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF,
    STATUS_BLOCKED_G76_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY,
    STATUS_VERIFIED_G75,
    STATUS_VERIFIED_G76,
    USB_PACKETS_TRANSMITTED,
    audit_phase210_donor_contracts,
    compute_fx3_proxy_cutoff_reasons,
    evaluate_76_master_safety_gates,
    evaluate_76gate_preflight,
    evaluate_g75_hdmi_log1080_hdmionly_guard,
    evaluate_g76_proxy_focusmag_brightmon_guard,
    main as module_main,
    resolve_effective_fx3_hdmi_output,
    run_76_gate_preflight,
    verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard,
    verify_proxy_coupled_vault_and_focusmag_brightmon_guard,
)


class TestPhase210HdmiLog1080ProxyFocusMagBrightMon76GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 210 Gates G75, G76 & 76-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_74 = fx3_safety.evaluate_74gate_preflight()
        cls.dryrun_74 = fx3_safety.evaluate_74gate_preflight(dry_run_simulated=True)
        cls.offline_76 = evaluate_76gate_preflight(master_74_override=cls.offline_74)
        cls.dryrun_76 = evaluate_76gate_preflight(
            simulate_bench_dry_run=True, master_74_override=cls.dryrun_74
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_74 = fx3_safety.evaluate_74gate_preflight(
                force_clean_room=True
            )
            cls.clean_offline_76 = evaluate_76gate_preflight(
                force_clean_room=True, master_74_override=cls.clean_offline_74
            )

    # ------------------------------------------------------------------
    # Section A: Donor Contract Audit (<0.15s O_RDONLY & Clean-Room)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G75, G75_GATE_CODE)
        self.assertEqual(G76, G76_GATE_CODE)
        self.assertEqual(
            G75_GATE_CODE,
            "G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD",
        )
        self.assertEqual(
            G76_GATE_CODE,
            "G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD",
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_76gate_preflight, evaluate_76gate_preflight)
        self.assertIs(fx3_safety.run_76_gate_preflight, run_76_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_76_master_safety_gates, evaluate_76_master_safety_gates
        )

    def test_02_donor_audit_bounded_under_150ms_and_zero_bytes_leaked(self) -> None:
        audit = audit_phase210_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertLess(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertTrue(audit.within_budget_150ms)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )
        dumped = json.dumps(audit.to_dict())
        self.assertNotIn("\\x7fELF", dumped)

    def test_03_donor_audit_force_clean_room_env_and_flag(self) -> None:
        audit_flag = audit_phase210_donor_contracts(force_clean_room=True)
        self.assertTrue(audit_flag.valid)
        self.assertEqual(audit_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit_flag.files_inspected, 0)
        self.assertEqual(audit_flag.raw_firmware_bytes_leaked, 0)

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit_env = audit_phase210_donor_contracts()
            self.assertTrue(audit_env.valid)
            self.assertEqual(audit_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_audit_tampered_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _key, (_body, rel_path, *_rest) in PINNED_PHASE210_DONOR_SPECS.items():
                p = root / rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"corrupt_stub")
            audit = audit_phase210_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY)

    def test_05_donor_audit_budget_exceeded_fails_closed(self) -> None:
        audit = audit_phase210_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section B: Gate G75 ([HDMI Output Settings], Log 1080p, Blank LCD)
    # ------------------------------------------------------------------

    def test_06_g75_default_cine_ei_rec_media_on_downshifts_hdmi_to_1080p(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G75)
        self.assertTrue(res.log_or_pplut_1080p_downshift_active)
        self.assertEqual(res.modeled_effective_hdmi_output, "1080P")
        self.assertTrue(res.internal_card_recording_active)

    def test_07_g75_all_active_log_modes_downshift_to_1080p_when_rec_on(self) -> None:
        for mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            eff, downshift = resolve_effective_fx3_hdmi_output(
                rec_media_dur_hdmi_output="On",
                output_resolution_menu="2160p",
                log_shooting_mode=mode,
                hdmi_raw_output_on=False,
            )
            self.assertEqual(eff, "1080P")
            self.assertTrue(downshift)

    def test_08_g75_pplut1_to_pplut4_downshift_to_1080p_when_rec_on(self) -> None:
        for pp in PPLUT_PICTURE_PROFILES:
            res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
                rec_media_dur_hdmi_output="On",
                output_resolution_menu="2160p",
                log_shooting_mode="Off",
                picture_profile=pp,
                claimed_effective_hdmi_resolution="1080p",
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.log_or_pplut_1080p_downshift_active)
            self.assertEqual(res.modeled_effective_hdmi_output, "1080P")

    def test_09_g75_blocks_false_simultaneous_rec_and_nonraw_4k_log_hdmi(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            output_resolution_menu="2160p",
            log_shooting_mode="Cine EI",
            hdmi_raw_output_on=False,
            claimed_effective_hdmi_resolution="2160p",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM,
            res.violation_codes,
        )

    def test_10_g75_blocks_explicit_simultaneous_rec_4k_pplut_claim_flag(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            log_shooting_mode="Off",
            picture_profile="PPLUT2",
            simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM
        )

    def test_11_g75_permits_2160p_when_log_off_and_standard_pp_cinetone(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            output_resolution_menu="2160p",
            log_shooting_mode="Off",
            picture_profile="PP11",
            claimed_effective_hdmi_resolution="2160p",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.log_or_pplut_1080p_downshift_active)
        self.assertEqual(res.modeled_effective_hdmi_output, "2160P")

    def test_12_g75_permits_4264x2408_16bit_raw_with_log_and_card_rec(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            log_shooting_mode="Cine EI",
            hdmi_raw_output_on=True,
            hdmi_info_display_menu="Off",
            hdmi_desqueeze_display_active=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.modeled_effective_hdmi_output, "4264X2408_16BIT_RAW")
        self.assertFalse(res.log_or_pplut_1080p_downshift_active)

    def test_13_g75_all_six_4k_hdmi_only_10bit_formats_verified(self) -> None:
        self.assertEqual(len(ALLOWED_4K_HDMI_ONLY_FORMATS), 6)
        for fmt in (
            "59.94p 10bit",
            "50p 10bit",
            "29.97p 10bit",
            "25p 10bit",
            "23.98p 10bit",
            "24.00p 10bit",
        ):
            res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                four_k_hdmi_only_format=fmt,
                qfhd_24p_enabled=True,
                internal_card_recording_active=False,
            )
            self.assertTrue(res.valid, msg=fmt)
            self.assertFalse(res.internal_card_recording_active)
            self.assertTrue(res.modeled_effective_hdmi_output.startswith("2160P_HDMI_ONLY_"))

    def test_14_g75_blocks_invalid_4k_hdmi_only_format_and_24p_without_qfhd(self) -> None:
        bad_fmt = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            four_k_hdmi_only_format="119.88p 10bit",
        )
        self.assertFalse(bad_fmt.valid)
        self.assertEqual(
            bad_fmt.status, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID
        )

        no_qfhd = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            four_k_hdmi_only_format="24.00p 10bit",
            qfhd_24p_enabled=False,
        )
        self.assertFalse(no_qfhd.valid)
        self.assertEqual(
            no_qfhd.status, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID
        )

    def test_15_g75_blocks_4k_hdmi_only_setting_when_rec_media_on(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            four_k_hdmi_only_setting_applied=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID
        )

    def test_16_g75_blocks_internal_card_recording_under_off_hdmi_only(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            internal_card_recording_active=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G75_HDMI_ONLY_INTERNAL_CARD_REC_FORBIDDEN,
            res.violation_codes,
        )

    def test_17_g75_blocks_hdmi_info_display_or_desqueeze_under_off_hdmi_only(self) -> None:
        res_info = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            effective_hdmi_info_display_on=True,
        )
        self.assertFalse(res_info.valid)
        self.assertIn(
            STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION,
            res_info.violation_codes,
        )

        res_dsq = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_desqueeze_display_active=True,
        )
        self.assertFalse(res_dsq.valid)
        self.assertIn(
            STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION,
            res_dsq.violation_codes,
        )

    def test_18_g75_blocks_hdmi_info_display_or_desqueeze_under_raw_output_on(self) -> None:
        res_raw = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output_on=True,
            effective_hdmi_info_display_on=True,
        )
        self.assertFalse(res_raw.valid)
        self.assertEqual(
            res_raw.status,
            STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION,
        )

        res_raw_dsq = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output_on=True,
            hdmi_desqueeze_display_active=True,
        )
        self.assertFalse(res_raw_dsq.valid)

    def test_19_g75_enforces_camera_lcd_blanking_when_hdmi_info_display_on(self) -> None:
        ok_blank = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_info_display_menu="On",
            camera_lcd_panel_blanked=True,
            camera_lcd_live_image_or_osd_visible=False,
        )
        self.assertTrue(ok_blank.valid)
        self.assertTrue(ok_blank.camera_lcd_panel_blanked)

        not_blank = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_info_display_menu="On",
            camera_lcd_panel_blanked=False,
        )
        self.assertFalse(not_blank.valid)
        self.assertEqual(
            not_blank.status, STATUS_BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED
        )

        osd_vis = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_info_display_menu="On",
            camera_lcd_panel_blanked=True,
            camera_lcd_live_image_or_osd_visible=True,
        )
        self.assertFalse(osd_vis.valid)
        self.assertEqual(
            osd_vis.status, STATUS_BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED
        )

    def test_20_g75_blocks_wrong_body_model_and_invalid_telemetry(self) -> None:
        wrong_body = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            body_model_name="ILME-FX6", body_model_id=0x91030079
        )
        self.assertFalse(wrong_body.valid)
        self.assertEqual(wrong_body.status, STATUS_BLOCKED_G75_TELEMETRY_INVALID)

        bad_type = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            output_resolution_menu=2160  # type: ignore[arg-type]
        )
        self.assertFalse(bad_type.valid)
        self.assertEqual(bad_type.status, STATUS_BLOCKED_G75_TELEMETRY_INVALID)

    def test_21_g75_evaluator_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g75_hdmi_log1080_hdmionly_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.gate_id, G75_GATE_ID)
        self.assertEqual(verdict.gate_code, G75_GATE_CODE)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # Section C: Gate G76 (Proxy Table, Coupled Vault, FocusMag, BrightMon)
    # ------------------------------------------------------------------

    def test_22_g76_exact_three_proxy_settings_across_two_formats_pass(self) -> None:
        cases = (
            ("XAVC HS HD", "16M 4:2:0 10bit", 1920, 1080, 16, 10),
            ("XAVC HS HD", "9M 4:2:0 10bit", 1920, 1080, 9, 10),
            ("XAVC S HD", "6M 4:2:0 8bit", 1280, 720, 6, 8),
        )
        for pfmt, pset, w, h, mbps, bits in cases:
            res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                proxy_file_format=pfmt,
                proxy_setting=pset,
                proxy_width=w,
                proxy_height=h,
            )
            self.assertTrue(res.valid, msg=f"{pfmt}/{pset}")
            self.assertEqual(res.proxy_width, w)
            self.assertEqual(res.proxy_height, h)
            self.assertEqual(res.proxy_bitrate_mbps, mbps)
            self.assertEqual(res.proxy_bit_depth, bits)

    def test_23_g76_rejects_non_fx3_proxy_format_setting_and_dimensions(self) -> None:
        cross_mix = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            proxy_file_format="XAVC S HD", proxy_setting="9M 4:2:0 10bit"
        )
        self.assertFalse(cross_mix.valid)
        self.assertEqual(
            cross_mix.status, STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID
        )

        wrong_dim = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            proxy_file_format="XAVC S HD",
            proxy_setting="6M 4:2:0 8bit",
            proxy_width=1920,
            proxy_height=1080,
        )
        self.assertFalse(wrong_dim.valid)
        self.assertEqual(
            wrong_dim.status, STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID
        )

        over_fps = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            proxy_max_fps=119.88
        )
        self.assertFalse(over_fps.valid)
        self.assertEqual(over_fps.status, STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID)

    def test_24_g76_blocks_proxy_recording_at_normal_119_88p_and_100p(self) -> None:
        for fps in ("119.88p", "100p"):
            res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                shooting_mode="Movie",
                rec_frame_rate=fps,
                proxy_recording_on=True,
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF,
                res.violation_codes,
            )
            ok_off = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                shooting_mode="Movie",
                rec_frame_rate=fps,
                proxy_recording_on=False,
            )
            self.assertTrue(ok_off.valid)

    def test_25_g76_blocks_proxy_recording_in_sq_high_fps_100_120_200_240(self) -> None:
        for sfps in (100.0, 120.0, 200.0, 240.0):
            res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                shooting_mode="S&Q",
                rec_frame_rate="23.98p",
                sq_sensor_frame_rate_fps=sfps,
                proxy_recording_on=True,
            )
            self.assertFalse(res.valid, msg=str(sfps))
            self.assertEqual(
                res.status, STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF
            )

        sq_rec_120 = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="S&Q",
            rec_frame_rate="119.88p",
            sq_sensor_frame_rate_fps=60.0,
            proxy_recording_on=True,
        )
        self.assertFalse(sq_rec_120.valid)

        sq_60_ok = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="S&Q",
            rec_frame_rate="23.98p",
            sq_sensor_frame_rate_fps=60.0,
            proxy_recording_on=True,
        )
        self.assertTrue(sq_60_ok.valid)

    def test_26_g76_blocks_proxy_recording_under_off_hdmi_only(self) -> None:
        reasons = compute_fx3_proxy_cutoff_reasons(
            rec_media_dur_hdmi_output="Off(HDMI Only)"
        )
        self.assertIn("REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY", reasons)

        blocked = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            proxy_recording_on=True,
        )
        self.assertFalse(blocked.valid)
        self.assertEqual(
            blocked.status, STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF
        )

    def test_27_g76_blocks_uncoupled_clip_sub_delete_protect_and_proxy_playback(
        self,
    ) -> None:
        uncoupled_del = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            clip_deleted=True, sub_proxy_deleted=False
        )
        self.assertFalse(uncoupled_del.valid)
        self.assertEqual(
            uncoupled_del.status,
            STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION,
        )

        uncoupled_prot = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            clip_protected=True, sub_proxy_protected=False
        )
        self.assertFalse(uncoupled_prot.valid)

        single_op = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            uncoupled_single_side_incamera_op_attempted=True
        )
        self.assertFalse(single_op.valid)

        pb_claim = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            on_camera_proxy_playback_claimed=True
        )
        self.assertFalse(pb_claim.valid)
        self.assertEqual(
            pb_claim.status,
            STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION,
        )

    def test_28_g76_atomic_coupled_delete_and_protect_parity_passes(self) -> None:
        res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            main_clip_dir="PRIVATE/M4ROOT/CLIP/",
            sub_proxy_dir="PRIVATE/M4ROOT/SUB/",
            clip_deleted=True,
            sub_proxy_deleted=True,
            clip_protected=False,
            sub_proxy_protected=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.coupled_vault_delete_parity)
        self.assertTrue(res.coupled_vault_protect_parity)

    def test_29_g76_initial_focus_mag_movie_x1_x4_vs_still_ff_x21_apsc_x15(self) -> None:
        for mag in ("x1.0", "x4.0"):
            self.assertTrue(
                verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                    shooting_mode="Movie", initial_focus_mag=mag
                ).valid
            )
        bad_movie_mag = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Movie", initial_focus_mag="x2.1"
        )
        self.assertFalse(bad_movie_mag.valid)
        self.assertEqual(
            bad_movie_mag.status,
            STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION,
        )

        ff_still = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Still",
            sensor_scan_mode="FULL_FRAME",
            initial_focus_mag="x2.1",
            proxy_recording_on=False,
        )
        self.assertTrue(ff_still.valid)

        apsc_still = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Still",
            sensor_scan_mode="APS_C",
            initial_focus_mag="x1.5",
            proxy_recording_on=False,
        )
        self.assertTrue(apsc_still.valid)

        bad_apsc_still = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Still",
            sensor_scan_mode="S35",
            initial_focus_mag="x2.1",
            proxy_recording_on=False,
        )
        self.assertFalse(bad_apsc_still.valid)

    def test_30_g76_blocks_auto_magnifier_in_mf_during_movie_shooting(self) -> None:
        movie_automag = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Movie", auto_magnifier_in_mf_triggered_in_movie=True
        )
        self.assertFalse(movie_automag.valid)
        self.assertEqual(
            movie_automag.status,
            STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION,
        )

        still_automag = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Still",
            proxy_recording_on=False,
            auto_magnifier_in_mf_active=True,
            marker_display_visible_while_magnified=False,
        )
        self.assertTrue(still_automag.valid)

    def test_31_g76_enforces_marker_display_suppression_and_unmagnified_essence(
        self,
    ) -> None:
        vis_marker = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            focus_magnifier_active=True, marker_display_visible_while_magnified=True
        )
        self.assertFalse(vis_marker.valid)
        self.assertEqual(
            vis_marker.status, STATUS_BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED
        )

        mag_essence = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            focus_magnifier_active=True, recorded_essence_magnified=True
        )
        self.assertFalse(mag_essence.valid)
        self.assertEqual(
            mag_essence.status, STATUS_BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED
        )

    def test_32_g76_bright_monitoring_key_toggle_locked_while_magnified(self) -> None:
        locked_toggle = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            focus_magnifier_active=True, bright_monitoring_key_toggle_accepted=True
        )
        self.assertFalse(locked_toggle.valid)
        self.assertEqual(
            locked_toggle.status, STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION
        )

        both_active = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="Still",
            proxy_recording_on=False,
            auto_magnifier_in_mf_active=True,
            bright_monitoring_active=True,
        )
        self.assertFalse(both_active.valid)
        self.assertEqual(
            both_active.status, STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION
        )

    def test_33_g76_bright_monitoring_pasm_mf_autocancel_and_setting_effect_off(
        self,
    ) -> None:
        valid_bm = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            bright_monitoring_active=True,
            exposure_mode="M",
            focus_mode="Manual Focus",
            live_view_display_mode="Setting Effect OFF",
        )
        self.assertTrue(valid_bm.valid)
        self.assertEqual(valid_bm.live_view_display_mode, "SETTING_EFFECT_OFF")

        non_pasm = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            bright_monitoring_active=True, exposure_mode="AUTO", focus_mode="MF"
        )
        self.assertFalse(non_pasm.valid)
        self.assertEqual(
            non_pasm.status, STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION
        )

        non_mf = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            bright_monitoring_active=True, exposure_mode="A", focus_mode="AF-C"
        )
        self.assertFalse(non_mf.valid)

        powered_off = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            bright_monitoring_active=True, camera_powered_off=True
        )
        self.assertFalse(powered_off.valid)

        wrong_lv = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            bright_monitoring_active=True, live_view_display_mode="Setting Effect ON"
        )
        self.assertFalse(wrong_lv.valid)

    def test_34_g76_invalid_telemetry_and_persistent_write_redline(self) -> None:
        bad_tel = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            sq_sensor_frame_rate_fps=float("nan")
        )
        self.assertFalse(bad_tel.valid)
        self.assertEqual(bad_tel.status, STATUS_BLOCKED_G76_TELEMETRY_INVALID)

        verdict, res = evaluate_g76_proxy_focusmag_brightmon_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.gate_id, G76_GATE_ID)
        self.assertEqual(verdict.gate_code, G76_GATE_CODE)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # Section D: Unified 76-Gate Preflight, CLI & Backward Compatibility
    # ------------------------------------------------------------------

    def test_35_master_76gate_offline_73_of_76_verified(self) -> None:
        r = self.offline_76
        self.assertEqual(
            r.schema, REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_SCHEMA
        )
        self.assertEqual(r.summary["total_gates"], 76)
        self.assertEqual(r.summary["verified_gates"], 73)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(r.offline_73_gates_verified)
        self.assertFalse(r.all_76_gates_verified)
        self.assertTrue(r.g13_to_g76_all_passed)
        self.assertTrue(r.g75_to_g76_all_passed)
        self.assertEqual(r.status, "VERIFIED_73_OF_76_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 76)
        self.assertEqual(r.gates[-2]["gate_code"], G75_GATE_CODE)
        self.assertEqual(r.gates[-1]["gate_code"], G76_GATE_CODE)

    def test_36_master_76gate_simulate_bench_dry_run_76_of_76_verified(self) -> None:
        r = self.dryrun_76
        self.assertEqual(r.summary["verified_gates"], 76)
        self.assertTrue(r.all_76_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertEqual(r.status, "VERIFIED_ALL_76_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_37_master_76gate_hard_locks_all_hardware_redlines(self) -> None:
        for r in (self.offline_76, self.dryrun_76, self.clean_offline_76):
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_38_master_76gate_clean_room_mode_parity(self) -> None:
        r = self.clean_offline_76
        self.assertEqual(r.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r.clean_room_forced)
        self.assertEqual(r.summary["verified_gates"], 73)
        self.assertTrue(r.offline_73_gates_verified)

    def test_39_master_76gate_propagates_g75_and_g76_failures(self) -> None:
        r_g75_fail = evaluate_76gate_preflight(
            force_clean_room=True,
            master_74_override=self.clean_offline_74,
            hdmi_log1080_hdmionly_kwargs={
                "simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed": True
            },
        )
        self.assertFalse(r_g75_fail.offline_73_gates_verified)
        self.assertEqual(
            r_g75_fail.status,
            STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM,
        )

        r_g76_fail = evaluate_76gate_preflight(
            force_clean_room=True,
            master_74_override=self.clean_offline_74,
            proxy_focusmag_brightmon_kwargs={"on_camera_proxy_playback_claimed": True},
        )
        self.assertFalse(r_g76_fail.offline_73_gates_verified)
        self.assertEqual(
            r_g76_fail.status,
            STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION,
        )

    def test_40_master_76gate_blocks_persistent_emmc_write_request(self) -> None:
        r_write = evaluate_76gate_preflight(
            force_clean_room=True,
            master_74_override=self.clean_offline_74,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r_write.offline_73_gates_verified)
        self.assertEqual(r_write.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_41_cli_verify_g75_and_verify_g76_text_and_json(self) -> None:
        for subcmd, exp_gate_id in (
            ("verify-g75-hdmi-log1080-hdmionly", G75_GATE_ID),
            ("verify-g76-proxy-focusmag-brightmon", G76_GATE_ID),
        ):
            buf_txt = io.StringIO()
            with contextlib.redirect_stdout(buf_txt):
                rc_txt = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc_txt, 0)
            self.assertIn(exp_gate_id, buf_txt.getvalue())

            buf_json = io.StringIO()
            with contextlib.redirect_stdout(buf_json):
                rc_json = cli_main([subcmd, "--force-clean-room", "--json"])
            self.assertEqual(rc_json, 0)
            payload = json.loads(buf_json.getvalue())
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_42_cli_verify_76_gates_offline_and_simulate_bench_dry_run(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = cli_main(["verify-76-gates", "--force-clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=73/76", buf_off.getvalue())
        self.assertIn("usb_packets_transmitted=0", buf_off.getvalue())

        buf_sim = io.StringIO()
        with contextlib.redirect_stdout(buf_sim):
            rc_sim = cli_main(
                ["verify-76-gates", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc_sim, 0)
        sim_data = json.loads(buf_sim.getvalue())
        self.assertEqual(sim_data["summary"]["verified_gates"], 76)
        self.assertTrue(sim_data["all_76_gates_verified"])
        self.assertFalse(sim_data["hardware_live_attachment_authorized"])
        self.assertEqual(sim_data["usb_packets_transmitted"], 0)

    def test_43_module_main_cli_offline_and_simulate_bench_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_main(["--force-clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=76/76", buf.getvalue())

    def test_44_backward_compatibility_verify_58_through_74_evaluators(self) -> None:
        expected_pairs = (
            (fx3_safety.evaluate_58gate_preflight, 58, 55, "offline_55_gates_verified"),
            (fx3_safety.evaluate_60gate_preflight, 60, 57, "offline_57_gates_verified"),
            (fx3_safety.evaluate_62gate_preflight, 62, 59, "offline_59_gates_verified"),
            (fx3_safety.evaluate_64gate_preflight, 64, 61, "offline_61_gates_verified"),
            (fx3_safety.evaluate_66gate_preflight, 66, 63, "offline_63_gates_verified"),
            (fx3_safety.evaluate_68gate_preflight, 68, 65, "offline_65_gates_verified"),
            (fx3_safety.evaluate_70gate_preflight, 70, 67, "offline_67_gates_verified"),
            (fx3_safety.evaluate_72gate_preflight, 72, 69, "offline_69_gates_verified"),
            (fx3_safety.evaluate_74gate_preflight, 74, 71, "offline_71_gates_verified"),
        )
        for fn, total, offline_exp, attr_name in expected_pairs:
            rep = fn(force_clean_room=True)
            self.assertEqual(rep.summary["total_gates"], total)
            self.assertEqual(rep.summary["verified_gates"], offline_exp)
            self.assertTrue(getattr(rep, attr_name))

    def test_45_cli_backward_compatibility_verify_58_to_74_subparsers_present(self) -> None:
        for n, flag in (
            (58, "--clean-room"),
            (74, "--force-clean-room"),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([f"verify-{n}-gates", flag])
            self.assertEqual(rc, 0)
            self.assertIn(f"/{n}", buf.getvalue())

    # ------------------------------------------------------------------
    # Section E: Additional Fine-Grained Edge-Case & Matrix Coverage (46..56)
    # ------------------------------------------------------------------

    def test_46_g75_output_resolution_auto_maps_to_2160p_when_non_log(self) -> None:
        eff, down = resolve_effective_fx3_hdmi_output(
            rec_media_dur_hdmi_output="On",
            output_resolution_menu="Auto",
            log_shooting_mode="Off",
            picture_profile="Off",
        )
        self.assertEqual(eff, "2160P")
        self.assertFalse(down)

    def test_47_g75_output_resolution_1080i_preserved_when_non_log(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            output_resolution_menu="1080i",
            log_shooting_mode="Off",
            picture_profile="PP8",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.modeled_effective_hdmi_output, "1080I")

    def test_48_g75_invalid_rec_media_dur_hdmi_option_blocked(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="Simultaneous_4K_SDI"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID
        )

    def test_49_g75_bool_log_shooting_true_normalizes_to_cine_ei(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            log_shooting_mode=True, claimed_effective_hdmi_resolution="1080p"
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.canonical_log_shooting_mode, "CINE_EI")
        self.assertTrue(res.log_or_pplut_1080p_downshift_active)

    def test_50_g75_hdmi_info_display_off_keeps_camera_lcd_active(self) -> None:
        res = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
            rec_media_dur_hdmi_output="On",
            hdmi_info_display_menu="Off",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.effective_hdmi_info_display_on)
        self.assertFalse(res.camera_lcd_panel_blanked)

    def test_51_g76_focus_magnif_time_2sec_5sec_nolimit_all_valid(self) -> None:
        for t_opt in ("2 Sec", "5 Sec", "No Limit"):
            res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                focus_magnif_time=t_opt
            )
            self.assertTrue(res.valid, msg=t_opt)

    def test_52_g76_invalid_focus_magnif_time_rejected(self) -> None:
        res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            focus_magnif_time="30 Sec"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION
        )

    def test_53_g76_all_pasm_exposure_modes_permitted_for_bright_monitoring(self) -> None:
        for exp in ("P", "A", "S", "M"):
            res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
                bright_monitoring_active=True,
                exposure_mode=exp,
                focus_mode="MF",
            )
            self.assertTrue(res.valid, msg=exp)

    def test_54_g76_wrong_proxy_directory_tree_rejected(self) -> None:
        res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            main_clip_dir="XDROOT/Clip/", sub_proxy_dir="XDROOT/Sub/"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION
        )

    def test_55_g76_unsupported_shooting_mode_rejected(self) -> None:
        res = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
            shooting_mode="PANORAMA"
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G76_TELEMETRY_INVALID)

    def test_56_json_serialization_zero_raw_firmware_leakage(self) -> None:
        blob_str = json.dumps(self.offline_76.to_dict(), ensure_ascii=False)
        self.assertNotIn("\\x7fELF", blob_str)
        self.assertEqual(self.offline_76.raw_firmware_bytes_leaked, 0)


if __name__ == "__main__":
    unittest.main()
