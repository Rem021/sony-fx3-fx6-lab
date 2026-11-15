"""Unit tests for Phase 80 False Color / EL-Zone S-Log3 Exposure Mapping, 4-Ch 24-bit 48kHz LPCM Headroom & Limiter DSP, and SMPTE 12M User-Bits + TC Direction Guard Auditor.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.falsecolor_lpcm_tc_ub_auditor import (
    CP_SHARED_PHASE80_MARKERS,
    EBU_R68_REF_DBFS,
    EL_ZONE_SLOG3_BANDS,
    FX3_APPFW_AUDIO_DSP_MARKERS,
    FX3_APPFW_EXPOSURE_MARKERS,
    FX3_APPFW_TC_UB_MARKERS,
    FX6_APPFW_AUDIO_DSP_MARKERS,
    FX6_APPFW_EXPOSURE_MARKERS,
    FX6_APPFW_TC_UB_MARKERS,
    LIMITER_CEILING_DBFS,
    LIMITER_THRESHOLD_DBFS,
    LPCM_2CH_BITRATE_BPS,
    LPCM_4CH_BITRATE_BPS,
    LPCM_BIT_DEPTH,
    LPCM_INT24_MAX,
    LPCM_SAMPLE_RATE_HZ,
    PHASE_80_SCHEMA,
    PHASE_80_VERSION,
    SCINETONE_WHITE_CLIP_IRE,
    SLOG3_BLACK_FLOOR_CODE10,
    SLOG3_MIDDLE_GREY_18PCT_CODE10,
    SLOG3_SENSOR_CLIP_IRE,
    SMPTE_RP155_REF_DBFS,
    FalseColorLpcmTcUbReport,
    analyze_falsecolor_lpcm_tc_ub,
    build_clean_room_falsecolor_lpcm_ub_fixtures,
    evaluate_false_color_el_zone,
    evaluate_int24_soft_knee_limiter,
    evaluate_lpcm_headroom_and_routing,
    evaluate_tc_port_direction_guard,
    falsecolor_lpcm_tc_ub_report_to_dict,
    pack_smpte12m_user_bits,
    slog3_code10_to_ire,
    slog3_ev_to_ire,
    slog3_reflection_to_code10,
    synthesize_and_verify_1khz_int24_tone,
    unpack_smpte12m_user_bits,
    verify_zero_calibration_and_emmc_immutability,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveFalseColorLpcmTcUb(unittest.TestCase):
    _active_report: Optional[FalseColorLpcmTcUbReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_falsecolor_lpcm_tc_ub()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_o_rdonly_12_artifacts_and_sub_500ms(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertLess(self._elapsed_sec, 0.5)
        self.assertEqual(rep.schema_version, PHASE_80_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_80_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertEqual(rep.int24_wrap_around_count, 0)
        self.assertEqual(rep.bus_contention_count, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 12)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_hotshoe"], 10_000)
            self.assertGreater(rep.donor_file_sizes["fx6_avbb_audio"], 10_000)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = falsecolor_lpcm_tc_ub_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_1_exposure_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_false_color_el_zone
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_exposure_markers, FX3_APPFW_EXPOSURE_MARKERS)
        self.assertEqual(p1.fx6_exposure_markers, FX6_APPFW_EXPOSURE_MARKERS)
        self.assertIn("MSG_ID_INFRABB_VDF_SRVC_SET_ZEBRA", p1.cp_exposure_markers)
        self.assertIn("MSG_ID_INFRABB_VDF_SRVC_SET_HISTOGRAM", p1.cp_exposure_markers)
        self.assertEqual(p1.uxc_exposure_labels["fx3_histogram"], "Histogram")
        self.assertEqual(p1.uxc_exposure_labels["fx3_zebra_display"], "Zebra Display")
        self.assertEqual(p1.uxc_exposure_labels["fx6_false_color"], "Exposure Assist False Color")
        self.assertEqual(p1.uxc_exposure_labels["fx6_waveform"], "Waveform")

    def test_04_pillar_2_lpcm_audio_dsp_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_lpcm_headroom_dsp
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_audio_dsp_markers, FX3_APPFW_AUDIO_DSP_MARKERS)
        self.assertEqual(p2.fx6_audio_dsp_markers, FX6_APPFW_AUDIO_DSP_MARKERS)
        self.assertIn("MSG_ID_INFRABB_AUDIO_SET_LIMITER", p2.cp_audio_dsp_markers)
        self.assertIn("AUDIO_HEADROOM_LEVEL", p2.cp_audio_dsp_markers)
        self.assertIn("LOG_SET_ANTI_CLIP_ADF_START", p2.fx6_avbb_audio_markers)

    def test_05_pillar_3_and_4_tc_ub_markers_and_zero_mutation(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_smpte_ub_direction
        p4 = rep.pillar_4_zero_mutation_proof
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_tc_ub_markers, FX3_APPFW_TC_UB_MARKERS)
        self.assertEqual(p3.fx6_tc_ub_markers, FX6_APPFW_TC_UB_MARKERS)
        self.assertEqual(p3.bus_contention_count, 0)
        self.assertTrue(p4.passed)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)


class TestPillar1FalseColorAndElZoneSLog3(unittest.TestCase):
    def test_06_slog3_black_floor_3_5_ire_code_95(self) -> None:
        code10 = slog3_reflection_to_code10(0.0)
        self.assertAlmostEqual(code10, float(SLOG3_BLACK_FLOOR_CODE10), places=3)
        ire = slog3_code10_to_ire(code10)
        self.assertAlmostEqual(ire, 3.539, places=2)
        ev = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=-15.0)
        self.assertTrue(ev.valid)
        self.assertEqual(ev.el_zone_id, "PURPLE_BLACK_CLIP")
        self.assertEqual(ev.el_zone_color, "PURPLE")

    def test_07_slog3_18pct_middle_grey_41_ire_green_band_code_420(self) -> None:
        code10 = slog3_reflection_to_code10(0.18)
        self.assertAlmostEqual(code10, float(SLOG3_MIDDLE_GREY_18PCT_CODE10), places=3)
        c_legal, _c_full, ire = slog3_ev_to_ire(0.0, base_iso_ei=800)
        self.assertAlmostEqual(c_legal, 420.0, places=3)
        self.assertTrue(40.6 <= ire <= 41.4, msg=f"18% grey IRE={ire} outside 40.6..41.4")
        ev = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=0.0, zebra1_ire=41.0)
        self.assertTrue(ev.valid)
        self.assertEqual(ev.el_zone_id, "GREEN_MIDDLE_GREY_18PCT")
        self.assertEqual(ev.el_zone_color, "GREEN")
        self.assertTrue(ev.zebra1_triggered)

    def test_08_slog3_skin_plus1ev_pink_and_90pct_white_card(self) -> None:
        skin = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=1.0, zebra1_ire=52.0)
        self.assertTrue(skin.valid)
        self.assertEqual(skin.el_zone_id, "PINK_SKIN_TONE_PLUS_1EV")
        self.assertEqual(skin.el_zone_color, "PINK")
        self.assertTrue(48.0 <= skin.ire_pct <= 53.0)

        white90 = evaluate_false_color_el_zone(
            gamma_profile="SLOG3",
            ev_offset=math.log2(0.90 / 0.18),
        )
        self.assertTrue(white90.valid)
        self.assertEqual(white90.el_zone_id, "LIGHT_GREY_90PCT_WHITE_CARD")
        self.assertTrue(59.0 <= white90.ire_pct <= 63.0)

    def test_09_slog3_sensor_saturation_clip_94_ire_catches_100_zebra_trap(self) -> None:
        # Correct Zebra 2 = 94% catches S-Log3 +6.0 EV sensor saturation at 800 EI
        ok_94 = evaluate_false_color_el_zone(
            gamma_profile="SLOG3",
            ev_offset=6.0,
            zebra2_ire=SLOG3_SENSOR_CLIP_IRE,
            base_iso_ei=800,
        )
        self.assertTrue(ok_94.valid)
        self.assertEqual(ok_94.el_zone_id, "RED_SENSOR_SATURATION_CLIP")
        self.assertEqual(ok_94.el_zone_color, "RED")
        self.assertTrue(ok_94.zebra2_triggered)
        self.assertFalse(ok_94.zebra_misses_slog3_sensor_clip)
        self.assertTrue(93.8 <= ok_94.ire_pct <= 94.5)

        # Trap: setting Zebra 2 to 100% on S-Log3 misses sensor clip at 94% IRE!
        trap_100 = evaluate_false_color_el_zone(
            gamma_profile="SLOG3",
            ev_offset=6.0,
            zebra2_ire=100.0,
            base_iso_ei=800,
        )
        self.assertFalse(trap_100.valid)
        self.assertEqual(trap_100.status, "BLOCKED_ZEBRA_100_MISSES_SLOG3_94_CLIP")
        self.assertTrue(trap_100.zebra_misses_slog3_sensor_clip)
        self.assertFalse(trap_100.zebra2_triggered)

    def test_10_scinetone_41_ire_grey_and_109_ire_superwhite_vs_rec709(self) -> None:
        sc_grey = evaluate_false_color_el_zone(gamma_profile="S_CINETONE", ire_pct=41.0)
        self.assertTrue(sc_grey.valid)
        self.assertEqual(sc_grey.el_zone_id, "GREEN_MIDDLE_GREY_18PCT")
        self.assertEqual(sc_grey.clip_ceiling_ire, SCINETONE_WHITE_CLIP_IRE)

        sc_clip = evaluate_false_color_el_zone(
            gamma_profile="S_CINETONE",
            ire_pct=109.0,
            zebra2_ire=109.0,
        )
        self.assertTrue(sc_clip.valid)
        self.assertEqual(sc_clip.el_zone_id, "RED_WHITE_CLIP_109_IRE")
        self.assertTrue(sc_clip.zebra2_triggered)

        r709 = evaluate_false_color_el_zone(gamma_profile="REC709", ire_pct=100.0, zebra2_ire=100.0)
        self.assertTrue(r709.valid)
        self.assertEqual(r709.el_zone_id, "RED_REC709_WHITE_CLIP")
        self.assertTrue(r709.zebra2_triggered)

    def test_11_el_zone_table_contiguous_and_invalid_inputs_rejected(self) -> None:
        self.assertEqual(len(EL_ZONE_SLOG3_BANDS), 9)
        for prev_b, next_b in zip(EL_ZONE_SLOG3_BANDS, EL_ZONE_SLOG3_BANDS[1:]):
            self.assertAlmostEqual(float(prev_b["ire_max"]), float(next_b["ire_min"]), places=4)

        self.assertFalse(evaluate_false_color_el_zone(gamma_profile="UNKNOWN").valid)
        self.assertFalse(evaluate_false_color_el_zone(base_iso_ei=3200).valid)
        self.assertFalse(evaluate_false_color_el_zone(zebra2_ire=120.0).valid)


class TestPillar2LpcmHeadroomToneAndLimiterDsp(unittest.TestCase):
    def test_12_xlr_h1_4ch_24bit_48khz_vs_internal_stereo_fallback(self) -> None:
        xlr = evaluate_lpcm_headroom_and_routing(
            xlr_h1_attached=True,
            reference_standard="SMPTE_RP155",
            input_level_dbu=4.0,
        )
        self.assertTrue(xlr.valid)
        self.assertEqual(xlr.active_channels, 4)
        self.assertEqual(xlr.pcm_bitrate_bps, LPCM_4CH_BITRATE_BPS)
        self.assertEqual(xlr.pcm_bitrate_bps, 4_608_000)
        self.assertEqual(xlr.active_audio_bus, "XLR_H1_MI_SHOE_4CH_24BIT_48KHZ")

        fallback = evaluate_lpcm_headroom_and_routing(
            xlr_h1_attached=False,
            body_35mm_mic_plugged=False,
            reference_standard="SMPTE_RP155",
            input_level_dbu=4.0,
        )
        self.assertTrue(fallback.valid)
        self.assertEqual(fallback.active_channels, 2)
        self.assertEqual(fallback.pcm_bitrate_bps, LPCM_2CH_BITRATE_BPS)
        self.assertEqual(fallback.active_audio_bus, "INTERNAL_BODY_STEREO_MIC_2CH_FALLBACK")

        jack = evaluate_lpcm_headroom_and_routing(
            xlr_h1_attached=False,
            body_35mm_mic_plugged=True,
        )
        self.assertTrue(jack.valid)
        self.assertEqual(jack.active_audio_bus, "BODY_3_5MM_STEREO_JACK_2CH")

    def test_13_smpte_rp155_minus20_vs_ebu_r68_minus18_headroom_math(self) -> None:
        rp155 = evaluate_lpcm_headroom_and_routing(reference_standard="SMPTE_RP155", input_level_dbu=4.0)
        self.assertTrue(rp155.valid)
        self.assertEqual(rp155.ref_dbfs, SMPTE_RP155_REF_DBFS)
        self.assertEqual(rp155.headroom_db, 20.0)
        self.assertEqual(rp155.clip_ceiling_dbu, 24.0)
        self.assertEqual(rp155.digital_level_dbfs, -20.0)

        r68 = evaluate_lpcm_headroom_and_routing(reference_standard="EBU_R68", input_level_dbu=0.0)
        self.assertTrue(r68.valid)
        self.assertEqual(r68.ref_dbfs, EBU_R68_REF_DBFS)
        self.assertEqual(r68.headroom_db, 18.0)
        self.assertEqual(r68.clip_ceiling_dbu, 18.0)
        self.assertEqual(r68.digital_level_dbfs, -18.0)

    def test_14_1khz_int24_reference_tone_synthesis_and_le_roundtrip(self) -> None:
        tone = synthesize_and_verify_1khz_int24_tone(
            ref_dbfs=-20.0,
            freq_hz=1000.0,
            sample_rate_hz=LPCM_SAMPLE_RATE_HZ,
            duration_ms=20,
        )
        self.assertTrue(tone.valid, msg=f"Errors: {tone.errors}")
        self.assertEqual(tone.sample_count, 960)
        self.assertEqual(tone.pcm_byte_count, 2880)
        self.assertTrue(tone.int24_roundtrip_exact)
        self.assertAlmostEqual(tone.measured_peak_dbfs, -20.0, places=1)
        self.assertAlmostEqual(tone.measured_rms_dbfs, -23.01, places=1)
        self.assertAlmostEqual(tone.measured_freq_hz, 1000.0, places=1)
        self.assertEqual(len(tone.pcm_sha256), 64)

    def test_15_soft_knee_limiter_holds_brickwall_below_0dbfs_without_int24_wrap(self) -> None:
        # Unity gain below -3.0 dBFS threshold
        below = evaluate_int24_soft_knee_limiter(input_peak_dbfs=-10.0, limiter_enabled=True)
        self.assertTrue(below.valid)
        self.assertEqual(below.status, "SOFT_KNEE_LIMITER_UNITY_BELOW_THRESHOLD")
        self.assertAlmostEqual(below.output_peak_dbfs, -10.0, places=3)
        self.assertEqual(below.gain_reduction_db, 0.0)

        # Hot overloads (+0, +6, +12, +24 dBFS) smoothly limited below -0.1 dBFS ceiling (< 0.0 dBFS)
        for hot_db in (0.0, 6.0, 12.0, 24.0):
            res = evaluate_int24_soft_knee_limiter(input_peak_dbfs=hot_db, limiter_enabled=True)
            self.assertTrue(res.valid, msg=f"hot_db={hot_db} errors={res.errors}")
            self.assertEqual(res.status, "SOFT_KNEE_LIMITER_ENGAGED_BRICKWALL_SAFE")
            self.assertLess(res.output_peak_dbfs, 0.0)
            self.assertLessEqual(res.output_peak_dbfs, LIMITER_CEILING_DBFS)
            self.assertGreaterEqual(res.output_peak_dbfs, LIMITER_THRESHOLD_DBFS)
            self.assertLessEqual(res.output_int24_peak, LPCM_INT24_MAX)
            self.assertEqual(res.int24_wrap_around_count, 0)
            self.assertTrue(res.brickwall_ceiling_held)

    def test_16_unprotected_bypass_catches_int24_wraparound_overflow(self) -> None:
        trap = evaluate_int24_soft_knee_limiter(input_peak_dbfs=6.0, limiter_enabled=False)
        self.assertFalse(trap.valid)
        self.assertEqual(trap.status, "BLOCKED_INT24_WRAPAROUND_OVERFLOW")
        self.assertGreater(trap.int24_wrap_around_count, 0)
        self.assertFalse(trap.brickwall_ceiling_held)

    def test_17_wind_filter_mask_and_invalid_lpcm_params_rejected(self) -> None:
        ok = evaluate_lpcm_headroom_and_routing(wind_filter_ch_mask=(True, False, True, False))
        self.assertTrue(ok.valid)
        self.assertEqual(ok.wind_filter_ch_mask, (True, False, True, False))

        self.assertFalse(evaluate_lpcm_headroom_and_routing(sample_rate_hz=44100).valid)
        self.assertFalse(evaluate_lpcm_headroom_and_routing(bit_depth=16).valid)
        self.assertFalse(evaluate_lpcm_headroom_and_routing(reference_standard="AES_X").valid)
        self.assertFalse(synthesize_and_verify_1khz_int24_tone(freq_hz=30_000.0).valid)


class TestPillar3Smpte12mUserBitsAndDirectionGuard(unittest.TestCase):
    def test_18_ub_fix_hex_8_nibble_bg1_to_bg8_roundtrip(self) -> None:
        res = pack_smpte12m_user_bits(mode="FIX_HEX", ub_str="1A:2B:3C:4D")
        self.assertTrue(res.valid)
        self.assertTrue(res.roundtrip_exact)
        self.assertEqual(res.ub_formatted, "1A:2B:3C:4D")
        self.assertEqual(res.ub_hex, "1A2B3C4D")
        self.assertEqual(res.binary_groups_bg1_to_bg8, (1, 10, 2, 11, 3, 12, 4, 13))
        fmt, nibs = unpack_smpte12m_user_bits(bytes.fromhex(res.packed_bytes_hex))
        self.assertEqual(fmt, "1A:2B:3C:4D")
        self.assertEqual(nibs, res.binary_groups_bg1_to_bg8)

    def test_19_ub_date_yymmdd_and_clk_time_bcd_roundtrip(self) -> None:
        d = pack_smpte12m_user_bits(mode="DATE_YYMMDD", year=26, month=11, day=14)
        self.assertTrue(d.valid)
        self.assertEqual(d.ub_formatted, "26:11:14:00")
        self.assertTrue(d.roundtrip_exact)

        t = pack_smpte12m_user_bits(mode="CLK_TIME", hours=16, minutes=45, seconds=9)
        self.assertTrue(t.valid)
        self.assertEqual(t.ub_formatted, "16:45:09:00")
        self.assertTrue(t.roundtrip_exact)

    def test_20_ub_framerate_and_cinema_camid_reel_a0_01_00_01(self) -> None:
        fr = pack_smpte12m_user_bits(mode="FRAME_RATE", fps_tag="29.97DF")
        self.assertTrue(fr.valid)
        self.assertEqual(fr.ub_formatted, "29:97:DF:00")

        cam = pack_smpte12m_user_bits(
            mode="CAM_ID_REEL",
            cam_id="A",
            cam_index=0,
            reel=1,
            clip_or_slate=1,
        )
        self.assertTrue(cam.valid)
        self.assertEqual(cam.ub_formatted, "A0:01:00:01")
        self.assertTrue(cam.roundtrip_exact)

        cam_b = pack_smpte12m_user_bits(
            mode="CAM_ID_REEL",
            cam_id="B",
            cam_index=2,
            reel=14,
            clip_or_slate=23,
        )
        self.assertTrue(cam_b.valid)
        self.assertEqual(cam_b.ub_formatted, "B2:14:00:23")

    def test_21_ub_rejects_invalid_bcd_hex_and_bad_byte_lengths(self) -> None:
        self.assertFalse(pack_smpte12m_user_bits(mode="FIX_HEX", ub_str="ZZZZ").valid)
        self.assertFalse(pack_smpte12m_user_bits(mode="DATE_YYMMDD", year=26, month=13, day=1).valid)
        self.assertFalse(pack_smpte12m_user_bits(mode="CLK_TIME", hours=24, minutes=0, seconds=0).valid)
        self.assertFalse(pack_smpte12m_user_bits(mode="FRAME_RATE", fps_tag="99.9").valid)
        with self.assertRaises(ValueError):
            unpack_smpte12m_user_bits(b"\x01\x02\x03")

    def test_22_fx3_multiport_tc_in_and_hdmi_tc_out_simultaneous_zero_contention(self) -> None:
        res = evaluate_tc_port_direction_guard(
            target_body="ILME-FX3",
            multiport_direction="TC_IN",
            hdmi_direction="TC_OUT",
            vmc_bncm1_attached=True,
            uart_boot_active=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "TC_DIRECTION_ARBITRATED_ZERO_CONTENTION")
        self.assertEqual(res.bus_contention_count, 0)
        self.assertTrue(res.ext_lk_input_active)
        self.assertTrue(res.hdmi_tc_ub_output_active)

    def test_23_fx3_multiport_tc_out_and_hdmi_tc_in_and_uart_boot_blocked(self) -> None:
        bad_mp = evaluate_tc_port_direction_guard(
            target_body="ILME-FX3",
            multiport_direction="TC_OUT",
            hdmi_direction="TC_OUT",
        )
        self.assertFalse(bad_mp.valid)
        self.assertEqual(bad_mp.status, "BLOCKED_FX3_MULTIPORT_TC_IN_ONLY")

        bad_hdmi = evaluate_tc_port_direction_guard(
            target_body="ILME-FX3",
            multiport_direction="OFF",
            hdmi_direction="TC_IN",
            vmc_bncm1_attached=False,
        )
        self.assertFalse(bad_hdmi.valid)
        self.assertEqual(bad_hdmi.status, "BLOCKED_HDMI_TC_OUT_ONLY")

        bad_uart = evaluate_tc_port_direction_guard(
            target_body="ILME-FX3",
            multiport_direction="TC_IN",
            hdmi_direction="TC_OUT",
            vmc_bncm1_attached=True,
            uart_boot_active=True,
        )
        self.assertFalse(bad_uart.valid)
        self.assertEqual(bad_uart.status, "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION")


class TestPillar4ZeroMutationCleanRoomCliAndHygiene(unittest.TestCase):
    def test_24_volatile_shadow_allowed_with_zero_calibration_mutation(self) -> None:
        for path in ("/tmp/fx3_stageb_phase80_shadow.json", "ram://phase80_shadow.json", "memory://ub.json"):
            res = verify_zero_calibration_and_emmc_immutability(target_path=path)
            self.assertTrue(res.valid)
            self.assertEqual(res.status, "ZERO_CALIBRATION_ZERO_EMMC_MUTATION_VERIFIED")
            self.assertTrue(res.volatile_shadow_only)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_25_protected_calibration_and_emmc_paths_hard_blocked(self) -> None:
        for bad_path in (
            "/dev/cnflasha1/cal.bin",
            "/dev/nflasha30/lut.bin",
            "p2:/Backup.bin",
            "p2:/psd.bin",
            "p6:Jiritsu",
            "nvram://ub",
        ):
            res = verify_zero_calibration_and_emmc_immutability(target_path=bad_path)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_PROTECTED_CALIBRATION_OR_EMMC_WRITE")
            self.assertEqual(res.calibration_mutation_bytes, 0)

        auth_res = verify_zero_calibration_and_emmc_immutability(
            target_path="/tmp/fx3_stageb_phase80_shadow.json",
            persistent_emmc_writes_authorized=True,
        )
        self.assertFalse(auth_res.valid)
        self.assertEqual(auth_res.calibration_mutation_bytes, 0)

    def test_26_clean_room_mode_passes_deterministically(self) -> None:
        r1 = analyze_falsecolor_lpcm_tc_ub(clean_room=True)
        r2 = analyze_falsecolor_lpcm_tc_ub(clean_room=True)
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.donor_file_sizes), 12)
        self.assertEqual(r1.calibration_mutation_bytes, 0)
        self.assertEqual(r1.int24_wrap_around_count, 0)
        self.assertEqual(r1.bus_contention_count, 0)

    def test_27_missing_donor_root_falls_back_to_clean_room_automatically(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": ""}, clear=False), patch(
            "fx3_firmware_lab.falsecolor_lpcm_tc_ub_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_falsecolor_lpcm_tc_ub(
                repo_root=Path("/tmp/nonexistent_fx3_fx6_donor_root_phase80")
            )
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_28_clean_room_fixtures_dict_contains_all_12_artifacts(self) -> None:
        fixtures = build_clean_room_falsecolor_lpcm_ub_fixtures()
        self.assertEqual(len(fixtures), 12)
        for key in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx6_hotshoe",
            "fx6_avbb_audio",
            "fx3_global_xdb",
            "fx6_global_xdb",
            "fx3_str_en",
            "fx3_str_en_g",
            "fx6_str_en_1",
            "fx6_str_en_2",
        ):
            self.assertIn(key, fixtures)
            self.assertGreater(len(fixtures[key]), 0)

    def test_29_cli_audit_falsecolor_lpcm_ub_inprocess_and_subprocess(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-falsecolor-lpcm-ub", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["schema_version"], PHASE_80_SCHEMA)
        self.assertEqual(payload["calibration_mutation_bytes"], 0)
        self.assertNotRegex(buf.getvalue(), r'(?<![0-9A-Za-z_/.-])b[\'"]')

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_firmware_lab",
                "audit-falsecolor-lpcm-ub",
                "--clean-room",
                "--json",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        sub_payload = json.loads(proc.stdout)
        self.assertEqual(sub_payload["report_sha256"], payload["report_sha256"])

    def test_30_run_audit_all_includes_15_auditors_with_falsecolor_lpcm_ub(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("falsecolor_lpcm_tc_ub_audit", summary)
        self.assertTrue(summary["falsecolor_lpcm_tc_ub_audit"]["all_checks_passed"])
        expected_15 = (
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
            "wb_color_matrix_and_look_audit",
            "proxy_clipname_and_sidecar_audit",
            "assignable_zoom_ciz_and_fn_audit",
            "falsecolor_lpcm_tc_ub_audit",
        )
        for key in expected_15:
            self.assertIn(key, summary)

    def test_31_cp_shared_markers_and_package_exports(self) -> None:
        import fx3_firmware_lab

        self.assertGreaterEqual(len(CP_SHARED_PHASE80_MARKERS), 19)
        for sym in (
            "PHASE_80_SCHEMA",
            "analyze_falsecolor_lpcm_tc_ub",
            "evaluate_false_color_el_zone",
            "evaluate_int24_soft_knee_limiter",
            "pack_smpte12m_user_bits",
            "synthesize_and_verify_1khz_int24_tone",
        ):
            self.assertTrue(hasattr(fx3_firmware_lab, sym), msg=f"Missing export {sym}")

    def test_32_static_source_hygiene_o_rdonly_and_zero_secrets(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "falsecolor_lpcm_tc_ub_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "subprocess", "socket", "CXD90057_k8"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
