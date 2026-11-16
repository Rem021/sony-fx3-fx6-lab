#!/usr/bin/env python3
"""Phase 82 Test Suite — Stage 12 Cross-Body `CAMSET` FX6->FX3 Sanitizer,
4-Channel `24-bit / 48 kHz` LPCM (`-20 dB` Safety-Track + Limiter) & SMPTE 12M
`User-Bits` (`BG1..BG8`) / `HDMI TC OUT` Regenerator.

Exercises 36 fast unit, cross-body CAMSET clamping, int24 PCM safety/limiter,
+48V phantom firewall, XLR-H1 hot-detach, SMPTE 12M User-Bits, Stage 12 suite
integration, CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`)
and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import camset_lpcm_tcub_emulator as p82  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p82.run_phase82_camset_lpcm_tcub_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase82DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p82.inspect_camset_lpcm_tcub_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p82.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p82.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p82.is_forced_clean_room(env))
        paths = p82.resolve_phase82_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p82.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p82.inspect_camset_lpcm_tcub_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p82.is_forced_clean_room():
            audit = p82.inspect_camset_lpcm_tcub_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p82.resolve_phase82_donor_paths()
        audit = p82.inspect_camset_lpcm_tcub_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p82.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p82.ENV_MAC_WORK_ROOT: "/nonexistent_phase82_mac_work_root",
            p82.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase82_main_work_root",
        }
        audit = p82.inspect_camset_lpcm_tcub_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_nvram_and_zero_gpio_derefs(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["uart_boot_contention_events"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestCrossBodyCamsetSanitizer(unittest.TestCase):
    """Verify A-Cam FX6 -> B-Cam FX3 CAMSET profile clamping and volatile RAM shadow."""

    def test_06_fx6_to_fx3_preserves_100pct_shared_cinema_line_imaging(self) -> None:
        res = p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile())
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "FX6_TO_FX3_VOLATILE_SHADOW_SANITIZED")
        self.assertEqual(res.source_body, "ILME-FX6")
        self.assertEqual(res.target_body, "ILME-FX3")
        self.assertEqual(res.shared_imaging_parity_pct, 100.0)
        self.assertEqual(res.shared_imaging_matched_fields, p82.SHARED_CINEMA_LINE_FIELDS)

        prof = res.sanitized_profile
        self.assertEqual(prof["shooting_mode"], "Cine EI")
        self.assertEqual(prof["base_iso"], 800)
        self.assertEqual(prof["exposure_index"], 800)
        self.assertEqual(prof["color_gamut"], "S-Gamut3.Cine")
        self.assertEqual(prof["gamma_curve"], "S-Log3")
        self.assertEqual(prof["user_lut_name"], "User1.cube")
        self.assertTrue(prof["lut_embedded"])
        self.assertEqual(prof["fps_label"], "23.98p")
        self.assertEqual(prof["shutter_angle_deg"], 180.0)
        self.assertEqual(prof["white_balance_k"], 5600)
        self.assertEqual(prof["codec"], "XAVC S-I 4K")

    def test_07_fx6_hardware_absent_fields_clamped_nd_sdi_vf_zebra(self) -> None:
        res = p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile())
        self.assertEqual(res.nd_preset, "Clear")
        self.assertEqual(res.sdi_out, "CONTAINED_DISABLED")
        self.assertTrue(res.lcd_zebra)
        self.assertEqual(res.vf_hardware_output, "CONTAINED_DISABLED")
        self.assertEqual(res.sdi_transceiver_faults, 0)
        self.assertEqual(res.null_gpio_derefs, 0)
        self.assertEqual(res.scrubbed_fields["nd_preset"]["fx6_value"], "1/16")
        self.assertEqual(res.scrubbed_fields["nd_preset"]["fx3_clamped"], "Clear")
        self.assertEqual(res.scrubbed_fields["sdi_out"]["fx3_clamped"], "CONTAINED_DISABLED")
        self.assertEqual(
            res.scrubbed_fields["vf_zebra"]["fx3_clamped"],
            "LCD_ZEBRA_REDIRECTED_VF_DISABLED",
        )

    def test_08_wlan_ap_clamped_off_with_p12_airplane_mode_shadow_0x00(self) -> None:
        res = p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile(wlan_ap=True))
        self.assertFalse(res.wlan_ap)
        self.assertTrue(res.p12_airplane_mode_enforced)
        self.assertEqual(res.bk4_shadow_0x019e0012, 0x00)
        self.assertEqual(res.bk4_shadow_0x01a20002, 0x00)
        self.assertEqual(res.bt_tx_packets, 0)
        self.assertEqual(
            res.scrubbed_fields["wlan_ap"]["reason"],
            "P12_AIRPLANE_MODE_BK4_SHADOW_00_ENFORCED",
        )

    def test_09_volatile_ram_shadow_path_and_zero_bk4_persistent_nvram_writes(self) -> None:
        res = p82.sanitize_fx6_profile_to_fx3()
        self.assertEqual(res.volatile_shadow_path, p82.VOLATILE_BCAM_SHADOW_PATH)
        self.assertEqual(res.fx3_camset_reference_path, p82.FX3_CAMSET_PATH)
        self.assertEqual(len(res.volatile_shadow_sha256), 64)
        self.assertEqual(res.bk4_persistent_nvram_writes, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_10_persistent_nvram_target_paths_raise_blocked_error(self) -> None:
        for bad_path in (
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "/dev/mtdblock3",
            "bk4://persistent/camset",
            "nvram://0x019e0012",
            "emmc://private/sony/camset01.dat",
        ):
            with self.assertRaises(p82.CamsetLpcmTcubError):
                p82.sanitize_fx6_profile_to_fx3(shadow_target_path=bad_path)

    def test_11_custom_cine_ei_12800_s_gamut3_25p_sanitizes_cleanly(self) -> None:
        custom = p82.Fx6AcamCameraProfile(
            base_iso=12800,
            exposure_index=3200,
            color_gamut="S-Gamut3",
            user_lut_name="ShowLut_v2.cube",
            fps_label="25.00p",
            shutter_angle_deg=172.8,
            white_balance_k=3200,
            nd_preset="1/64",
            vf_zebra=False,
        )
        res = p82.sanitize_fx6_profile_to_fx3(custom)
        self.assertTrue(res.passed)
        self.assertEqual(res.shared_imaging_parity_pct, 100.0)
        self.assertEqual(res.sanitized_profile["base_iso"], 12800)
        self.assertEqual(res.sanitized_profile["exposure_index"], 3200)
        self.assertEqual(res.sanitized_profile["fps_label"], "25.00p")
        self.assertEqual(res.sanitized_profile["white_balance_k"], 3200)
        self.assertEqual(res.nd_preset, "Clear")
        self.assertFalse(res.lcd_zebra)

    def test_12_invalid_iso_fps_shutter_or_wb_raises_camset_error(self) -> None:
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile(base_iso=1600))
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile(fps_label="47.95p"))
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile(shutter_angle_deg=400.0))
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.sanitize_fx6_profile_to_fx3(p82.Fx6AcamCameraProfile(white_balance_k=1000))

    def test_13_camset_sanitization_deterministic_shadow_sha256(self) -> None:
        r1 = p82.sanitize_fx6_profile_to_fx3()
        r2 = p82.sanitize_fx6_profile_to_fx3()
        self.assertEqual(r1, r2)
        self.assertEqual(r1.volatile_shadow_sha256, r2.volatile_shadow_sha256)


class TestLpcm4Ch24Bit48KhzSafetyAndLimiter(unittest.TestCase):
    """Verify 24-bit int24 framing, -20 dB CH3/CH4 safety, limiter, +48V gate, and S&Q mute."""

    def test_14_int24_pack_unpack_boundary_values_and_overflow_rejection(self) -> None:
        for val in (p82.INT24_MIN, -1, 0, 1, 123456, p82.INT24_MAX):
            packed = p82.pack_int24_le(val)
            self.assertEqual(len(packed), 3)
            self.assertEqual(p82.unpack_int24_le(packed), val)

        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.pack_int24_le(p82.INT24_MAX + 1)
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.pack_int24_le(p82.INT24_MIN - 1)
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.unpack_int24_le(b"\x00\x00")

    def test_15_nominal_4ch_480_frames_s24_3le_and_qemu_s32_le_framing(self) -> None:
        res = p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=0.0)
        self.assertTrue(res.passed)
        self.assertEqual(res.sample_rate_hz, 48_000)
        self.assertEqual(res.bit_depth, 24)
        self.assertEqual(res.channels, 4)
        self.assertEqual(res.period_frames, 480)
        self.assertEqual(res.s24_3le_bytes, 480 * 4 * 3)
        self.assertEqual(res.s32_le_qemu_bytes, 480 * 4 * 4)
        self.assertTrue(res.roundtrip_unpack_ok)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_16_plus_12_dbfs_overload_brickwall_limiter_zero_wraparounds(self) -> None:
        res = p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=12.0)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "LPCM_4CH_24BIT_48KHZ_SAFETY_OK")
        self.assertEqual(res.int24_overflow_wraparounds, 0)
        self.assertGreater(res.limiter_engaged_samples, 0)
        self.assertLessEqual(res.ch1_peak_int24, p82.LIMITER_CEILING_INT24)
        self.assertLessEqual(res.ch2_peak_int24, p82.LIMITER_CEILING_INT24)
        self.assertEqual(res.ch1_peak_int24, p82.LIMITER_CEILING_INT24)

    def test_17_ch3_ch4_minus_20db_safety_track_unclipped_headroom(self) -> None:
        res = p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=12.0)
        self.assertEqual(res.safety_track_pad_db, -20.0)
        self.assertEqual(res.safety_track_clipped_samples, 0)
        # +12 dBFS - 20 dB = -8 dBFS (~0.398 * INT24_MAX), strictly unclipped
        self.assertGreater(res.ch3_safety_peak_int24, int(0.35 * p82.INT24_MAX))
        self.assertLess(res.ch3_safety_peak_int24, int(0.45 * p82.INT24_MAX))
        self.assertGreater(res.ch4_safety_peak_int24, 0)
        self.assertLess(res.ch4_safety_peak_int24, res.ch3_safety_peak_int24)

    def test_18_phantom_48v_firewall_allows_condenser_blocks_ribbon_trs_ltc_and_line(self) -> None:
        ok = p82.validate_phantom_48v_channel(
            channel_label="CH1",
            transducer_kind=p82.TRANSDUCER_BALANCED_CONDENSER,
            input_mode="MIC+48V",
            phantom_48v_requested=True,
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.phantom_48v_applied)
        self.assertEqual(ok.status, "PHANTOM_48V_SAFE_BALANCED_CONDENSER")

        for bad_kind in (
            p82.TRANSDUCER_PASSIVE_RIBBON_UNISOLATED,
            p82.TRANSDUCER_UNBALANCED_TRS_WIRELESS,
            p82.TRANSDUCER_SMPTE_LTC_SOURCE,
        ):
            blk = p82.validate_phantom_48v_channel(
                channel_label="CH1",
                transducer_kind=bad_kind,
                input_mode="MIC+48V",
                phantom_48v_requested=True,
            )
            self.assertFalse(blk.allowed)
            self.assertFalse(blk.phantom_48v_applied)
            self.assertEqual(blk.status, "BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD")

        line_blk = p82.validate_phantom_48v_channel(
            channel_label="CH2",
            transducer_kind=p82.TRANSDUCER_DYNAMIC_MIC,
            input_mode="LINE",
            phantom_48v_requested=True,
        )
        self.assertFalse(line_blk.allowed)
        self.assertEqual(line_blk.status, "BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD")

    def test_19_xlr_h1_hot_detach_falls_back_to_internal_stereo_with_p11_isolation(self) -> None:
        res = p82.simulate_4ch_24bit_48khz_lpcm_frame(xlr_h1_attached=False, input_overload_dbfs=0.0)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "XLR_H1_HOT_DETACH_INTERNAL_STEREO_FALLBACK")
        self.assertEqual(res.audio_source_mode, "INTERNAL_STEREO_FALLBACK")
        self.assertFalse(res.xlr_h1_attached)
        self.assertFalse(res.ch1_phantom_48v_applied)
        self.assertLessEqual(res.phantom_vbus_discharged_v, 1.0)
        self.assertTrue(res.p11_handle_isolated)
        self.assertEqual(res.ivshmem_tx_leaks, 0)
        self.assertGreater(res.ch1_peak_int24, 0)
        self.assertGreater(res.ch2_peak_int24, 0)
        self.assertEqual(res.ch3_safety_peak_int24, 0)
        self.assertEqual(res.ch4_safety_peak_int24, 0)

    def test_20_sq_120fps_and_240fps_auto_mute_all_4_channels_zero_samples(self) -> None:
        for fps in (120.0, 240.0):
            res = p82.simulate_4ch_24bit_48khz_lpcm_frame(sq_active=True, sq_fps=fps, input_overload_dbfs=12.0)
            self.assertTrue(res.passed)
            self.assertEqual(res.audio_source_mode, "SQ_OFF_SPEED_MUTED")
            self.assertTrue(res.audio_muted)
            self.assertIn(f"SQ_OFF_SPEED_{fps}FPS_AUTO_MUTE", res.mute_reason)
            self.assertFalse(res.ch1_phantom_48v_applied)
            self.assertEqual(res.nonzero_samples, 0)
            self.assertEqual(res.ch1_peak_int24, 0)
            self.assertEqual(res.ch3_safety_peak_int24, 0)

    def test_21_simulate_lpcm_rejects_lethal_48v_transducer_and_invalid_params(self) -> None:
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.simulate_4ch_24bit_48khz_lpcm_frame(
                ch1_transducer=p82.TRANSDUCER_PASSIVE_RIBBON_UNISOLATED,
                ch1_input_mode="MIC+48V",
                ch1_phantom_48v=True,
            )
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.simulate_4ch_24bit_48khz_lpcm_frame(period_frames=0)
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=30.0)

    def test_22_lpcm_s24_3le_sha256_deterministic_across_runs(self) -> None:
        a = p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=12.0)
        b = p82.simulate_4ch_24bit_48khz_lpcm_frame(input_overload_dbfs=12.0)
        self.assertEqual(a, b)
        self.assertEqual(a.s24_3le_sha256, b.s24_3le_sha256)


class TestSmpte12mUserBitsAndHdmiTcOutRegen(unittest.TestCase):
    """Verify SMPTE 12M BG1..BG8 User-Bits fleet packing, EXT-LK 0-frame lock, and HDMI TC OUT."""

    def test_23_encode_decode_smpte_user_bits_cam_b_reel_002_master_a(self) -> None:
        pkt = p82.encode_smpte_user_bits(
            cam_id="B",
            reel="002",
            master_cam="A",
            ext_lk_locked=True,
            hdmi_tc_out=True,
            drop_frame=False,
        )
        self.assertEqual(pkt.bg1_to_bg8, (4, 2, 0, 0, 2, 4, 1, 3))
        self.assertEqual(pkt.sony_ub_display, "42 00 24 13")
        dec = p82.decode_smpte_user_bits(pkt.user_bits_32)
        self.assertEqual(dec["cam_id"], "B")
        self.assertEqual(dec["reel"], "002")
        self.assertEqual(dec["master_cam"], "A")
        self.assertTrue(dec["ext_lk_locked"])
        self.assertTrue(dec["hdmi_tc_out"])
        self.assertFalse(dec["drop_frame"])
        self.assertTrue(dec["bg8_parity_ok"])

    def test_24_encode_decode_arbitrary_fleet_cam_ids_and_bg8_parity(self) -> None:
        for cam, reel, master, df in (
            ("C", "015", "A", False),
            ("D", "999", "B", True),
            ("F", "108", "A", False),
        ):
            pkt = p82.encode_smpte_user_bits(
                cam_id=cam,
                reel=reel,
                master_cam=master,
                drop_frame=df,
            )
            dec = p82.decode_smpte_user_bits(pkt.user_bits_32)
            self.assertEqual(dec["cam_id"], cam)
            self.assertEqual(dec["reel"], reel)
            self.assertEqual(dec["master_cam"], master)
            self.assertEqual(dec["drop_frame"], df)
            self.assertTrue(dec["bg8_parity_ok"])

    def test_25_invalid_user_bits_inputs_raise_error(self) -> None:
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.encode_smpte_user_bits(cam_id="AB")
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.encode_smpte_user_bits(master_cam="1")
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.encode_smpte_user_bits(reel="12")
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.decode_smpte_user_bits(-1)
        with self.assertRaises(p82.CamsetLpcmTcubError):
            p82.decode_smpte_user_bits(0x1_0000_0000)

    def test_26_tc_in_ext_lk_zero_frame_offset_and_hdmi_tc_out_regenerated(self) -> None:
        res = p82.simulate_tc_in_to_hdmi_tc_out_regenerator(
            frame_index=86_400,
            timebase="23.98p",
            cam_id="B",
            reel="002",
            master_cam="A",
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "EXT_LK_0F_OFFSET_HDMI_TC_OUT_REGENERATED")
        self.assertEqual(res.tc_offset_frames, 0)
        self.assertTrue(res.ext_lk_locked)
        self.assertEqual(res.master_tc_formatted, res.bcam_tc_formatted)
        self.assertEqual(res.multiport_cable_id, "VMC-BNCM1")
        self.assertTrue(res.uart_boot_isolated)
        self.assertEqual(res.uart_boot_contention_events, 0)
        self.assertTrue(res.hdmi_tc_out_enabled)
        self.assertTrue(res.hdmi_tc_out_regenerated)
        self.assertEqual(res.hdmi_embedded_tc_formatted, res.bcam_tc_formatted)
        self.assertEqual(res.hdmi_embedded_ub_hex, res.user_bits_hex)
        self.assertEqual(res.decoded_cam_id, "B")
        self.assertEqual(res.decoded_reel, "002")
        self.assertEqual(res.decoded_master_cam, "A")

    def test_27_tc_in_to_hdmi_tc_out_across_24p_25p_29_97df_and_59_94p(self) -> None:
        for tb in ("24.00p", "25.00p", "29.97p_df", "59.94p_df"):
            res = p82.simulate_tc_in_to_hdmi_tc_out_regenerator(
                frame_index=90_005,
                timebase=tb,
                cam_id="C",
                reel="007",
                master_cam="A",
            )
            self.assertTrue(res.passed, msg=f"timebase {tb} failed")
            self.assertEqual(res.tc_offset_frames, 0)
            self.assertEqual(res.hdmi_embedded_tc_formatted, res.bcam_tc_formatted)

    def test_28_multiport_uart_boot_active_raises_contention_firewall(self) -> None:
        with self.assertRaises(p82.CamsetLpcmTcubError) as ctx:
            p82.simulate_tc_in_to_hdmi_tc_out_regenerator(uart_boot_active=True)
        self.assertIn("BLOCKED_MULTIPORT_UART_BOOT_CONTENTION", str(ctx.exception))

    def test_29_ltc_80bit_sync_word_and_even_parity_verified(self) -> None:
        res = p82.simulate_tc_in_to_hdmi_tc_out_regenerator()
        self.assertEqual(len(res.ltc_80bit_hex), 20)  # 10 bytes = 80 bits
        self.assertEqual(res.ltc_sync_word_hex, "0x3ffd")
        self.assertTrue(res.ltc_even_parity_ok)

    def test_30_tc_regenerator_deterministic_across_runs(self) -> None:
        r1 = p82.simulate_tc_in_to_hdmi_tc_out_regenerator()
        r2 = p82.simulate_tc_in_to_hdmi_tc_out_regenerator()
        self.assertEqual(r1, r2)


class TestStage12SuiteIntegrationAndCli(unittest.TestCase):
    """Verify Stage 12 wiring in fx3_vm_coemulation_suite.py, CLI flags, and source hygiene."""

    def test_31_coemulation_suite_includes_stage12_and_skip_phase82_backward_compat(self) -> None:
        rep_full = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_full["all_checks_passed"])
        self.assertIn("stage12_phase82_camset_lpcm_tcub", rep_full)
        s12 = rep_full["stage12_phase82_camset_lpcm_tcub"]
        self.assertTrue(s12["all_checks_passed"])
        self.assertEqual(s12["cp_mutation_bytes"], 0)
        self.assertEqual(s12["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(s12["null_gpio_derefs"], 0)
        self.assertEqual(s12["mailbox_stalls"], 0)
        self.assertEqual(s12["uart_boot_contention_events"], 0)
        self.assertFalse(s12["persistent_emmc_writes_authorized"])

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_phase82_camset_lpcm_tcub=False)
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage12_phase82_camset_lpcm_tcub", rep_skip)

    def test_32_clean_room_audit_digest_reproducible_and_valid_json(self) -> None:
        rep1 = p82.run_phase82_camset_lpcm_tcub_audit(force_clean_room=True)
        rep2 = p82.run_phase82_camset_lpcm_tcub_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_33_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--camset-matrix"],
            ["--clean-room", "--lpcm-matrix"],
            ["--clean-room", "--tcub-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p82.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_34_suite_cli_summary_and_skip_phase82_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("camset_lpcm_tcub=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase82",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("camset_lpcm_tcub=", proc_skip.stdout)

    def test_35_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p82.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p82.PHASE_82_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_36_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "camset_lpcm_tcub_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("BK4_PERSISTENT_NVRAM_WRITES = 0", emu_src)
        self.assertIn("NULL_GPIO_DEREFS = 0", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
