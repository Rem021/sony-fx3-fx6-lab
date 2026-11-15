"""Unit tests for Phase 93 — 18th Unified Firmware-Lab Auditor:
Interval Recording (Time-Lapse 1..60s Electronic Shutter Frame Packing),
Picture Cache (Pre-Rec Circular DDR Ring-Buffer Budget on FX3 2048 MiB DRAM),
Wired USB-LAN FTP / FTPS & P12 00342260 Wi-Fi/BT RF-Off Firewall, and
Calibration/eMMC Zero-Mutation + NonRealTimeMeta v2.20 XML Tag Parity.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
"""

from __future__ import annotations

import json
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
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.interval_cache_and_ftp_auditor import (
    FX3_APPFW_FTP_USBLAN_MARKERS,
    FX3_APPFW_INTERVAL_MARKERS,
    FX3_CP_INTERVAL_MARKERS,
    FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
    FX3_TOTAL_AP_DRAM_MIB,
    FX6_APPFW_CACHE_MARKERS,
    FX6_APPFW_FTP_USBLAN_MARKERS,
    FX6_APPFW_INTERVAL_MARKERS,
    FX6_CP_INTERVAL_MARKERS,
    FX6_ETHER_SERVICE_MARKERS,
    FX6_FTP_CLIENT_MARKERS,
    INTERVAL_SEC_MAX,
    INTERVAL_SEC_MIN,
    INTERVAL_SHOTS_MAX,
    INTERVAL_SHOTS_MIN,
    LIBMPR_INTERVAL_PREREC_NRTM_MARKERS,
    PHASE_93_SCHEMA,
    PHASE_93_VERSION,
    PICTURE_CACHE_CODEC_PROFILES,
    IntervalCacheAndFtpReport,
    analyze_interval_cache_and_ftp,
    build_clean_room_interval_cache_ftp_fixtures,
    evaluate_emmc_calibration_immutability,
    evaluate_interval_recording_session,
    evaluate_picture_cache_ddr_budget,
    evaluate_wired_ftp_transfer_session,
    interval_cache_and_ftp_report_to_dict,
    simulate_day_to_night_ae_step_ev,
    synthesize_and_verify_interval_cache_nrtm_xml,
    validate_ftp_media_path,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveIntervalCacheAndFtpAuditor(unittest.TestCase):
    _active_report: Optional[IntervalCacheAndFtpReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_interval_cache_and_ftp()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_14_artifacts_within_budget(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        if is_forced_clean_room() or rep.mode == "CLEAN_ROOM_SYNTHETIC":
            self.assertLess(self._elapsed_sec, 0.02)
        else:
            self.assertLess(self._elapsed_sec, 0.35)
        self.assertEqual(rep.schema_version, PHASE_93_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_93_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 14)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = interval_cache_and_ftp_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])
        self.assertEqual(
            rep.to_deterministic_json().strip(),
            json.dumps(payload, indent=2, sort_keys=True),
        )

    def test_03_pillar_1_donor_markers_and_uxc_interval_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_interval_recording
        self.assertTrue(p1.passed, msg=f"P1 errors: {p1.errors}")
        self.assertEqual(p1.fx3_appfw_markers, FX3_APPFW_INTERVAL_MARKERS)
        self.assertEqual(p1.fx6_appfw_markers, FX6_APPFW_INTERVAL_MARKERS)
        self.assertEqual(p1.fx3_cp_markers, FX3_CP_INTERVAL_MARKERS)
        self.assertEqual(p1.fx6_cp_markers, FX6_CP_INTERVAL_MARKERS)
        self.assertEqual(p1.fx3_libmpr_markers, LIBMPR_INTERVAL_PREREC_NRTM_MARKERS)
        self.assertEqual(p1.uxc_interval_labels["fx3_interval_shooting"], "Interval shooting...")
        self.assertEqual(p1.uxc_interval_labels["fx6_interval_rec"], "Interval Rec")
        self.assertEqual(p1.uxc_interval_labels["fx6_interval_num_frames"], "Interval Rec Number of Frames")

    def test_04_pillar_2_cache_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_picture_cache_ddr
        self.assertTrue(p2.passed, msg=f"P2 errors: {p2.errors}")
        self.assertEqual(p2.fx6_appfw_cache_markers, FX6_APPFW_CACHE_MARKERS)
        self.assertEqual(p2.fx3_libmpr_prerec_markers, LIBMPR_INTERVAL_PREREC_NRTM_MARKERS)
        self.assertEqual(p2.fx6_libmpr_prerec_markers, LIBMPR_INTERVAL_PREREC_NRTM_MARKERS)
        self.assertEqual(p2.fx3_total_dram_mib, FX3_TOTAL_AP_DRAM_MIB)
        self.assertEqual(p2.fx3_cache_ddr_budget_mib, FX3_PICTURE_CACHE_DDR_BUDGET_MIB)
        self.assertEqual(p2.uxc_cache_labels["fx6_picture_cache_rec"], "Picture Cache Rec")
        self.assertEqual(p2.uxc_cache_labels["fx6_cache_rec"], "Cache Rec")
        self.assertEqual(p2.uxc_cache_labels["fx6_cache_size"], "Cache Size")
        self.assertEqual(p2.uxc_cache_labels["fx6_cache_rec_time"], "Cache Rec Time")

    def test_05_pillar_3_ftp_usblan_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_wired_ftp_p12
        self.assertTrue(p3.passed, msg=f"P3 errors: {p3.errors}")
        self.assertEqual(p3.fx3_appfw_ftp_markers, FX3_APPFW_FTP_USBLAN_MARKERS)
        self.assertEqual(p3.fx6_appfw_ftp_markers, FX6_APPFW_FTP_USBLAN_MARKERS)
        self.assertEqual(p3.fx6_ftp_client_markers, FX6_FTP_CLIENT_MARKERS)
        self.assertEqual(p3.fx6_ether_service_markers, FX6_ETHER_SERVICE_MARKERS)
        self.assertEqual(p3.uxc_ftp_usblan_labels["fx3_wired_lan"], "Wired LAN")
        self.assertEqual(p3.uxc_ftp_usblan_labels["fx3_wirelan_usblan"], "WireLAN(USB-LAN)")
        self.assertEqual(p3.uxc_ftp_usblan_labels["fx3_ftp_transfer"], "FTP Transfer")
        self.assertEqual(p3.uxc_ftp_usblan_labels["fx6_airplane_mode"], "Airplane Mode")

    def test_06_pillar_4_global_xdb_and_zero_mutation(self) -> None:
        rep = self._active_report
        assert rep is not None
        p4 = rep.pillar_4_immutability_and_nrtm
        self.assertTrue(p4.passed, msg=f"P4 errors: {p4.errors}")
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)


class TestPillar1IntervalRecording(unittest.TestCase):
    def test_07_interval_boundary_1s_to_60s_and_1_to_9999_shots(self) -> None:
        ev_min = evaluate_interval_recording_session(
            interval_sec=INTERVAL_SEC_MIN,
            shot_count=INTERVAL_SHOTS_MIN,
            shutter_type="ELECTRONIC",
            ae_tracking_sensitivity="LOW",
            packing_mode="XAVC_HS_SINGLE_CLIP",
            frames_per_trigger=1,
            output_fps=23.976,
        )
        self.assertTrue(ev_min.valid)
        self.assertEqual(ev_min.mech_shutter_actuations, 0)
        self.assertEqual(ev_min.packed_clip_frames, 1)

        ev_max = evaluate_interval_recording_session(
            interval_sec=INTERVAL_SEC_MAX,
            shot_count=INTERVAL_SHOTS_MAX,
            shutter_type="ELECTRONIC",
            ae_tracking_sensitivity="MID",
            packing_mode="XAVC_S_SINGLE_CLIP",
            frames_per_trigger=2,
            output_fps=59.94,
        )
        self.assertTrue(ev_max.valid)
        self.assertEqual(ev_max.mech_shutter_actuations, 0)
        self.assertEqual(ev_max.packed_clip_frames, 19998)
        self.assertEqual(ev_max.total_capture_wall_sec, 60 * 9999)

    def test_08_interval_out_of_range_blocked(self) -> None:
        for bad_iv, bad_shots in ((0, 100), (61, 100), (5, 0), (5, 10000)):
            ev = evaluate_interval_recording_session(
                interval_sec=bad_iv,
                shot_count=bad_shots,
                shutter_type="ELECTRONIC",
            )
            self.assertFalse(ev.valid)
            self.assertEqual(ev.status, "BLOCKED_INTERVAL_PARAMETER_VIOLATION")

    def test_09_mechanical_shutter_wear_firewall_blocks_actuations(self) -> None:
        ev = evaluate_interval_recording_session(
            interval_sec=2,
            shot_count=5000,
            shutter_type="MECHANICAL",
            ae_tracking_sensitivity="LOW",
            silent_mode=False,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_MECHANICAL_SHUTTER_WEAR_HAZARD")
        self.assertEqual(ev.mech_shutter_actuations, 5000)
        self.assertFalse(ev.electronic_shutter_enforced)

    def test_10_ae_tracking_day_to_night_flicker_suppression_hierarchy(self) -> None:
        step_high = simulate_day_to_night_ae_step_ev("HIGH")
        step_mid = simulate_day_to_night_ae_step_ev("MID")
        step_low = simulate_day_to_night_ae_step_ev("LOW")
        step_lock = simulate_day_to_night_ae_step_ev("LOCK")
        self.assertGreater(step_high, step_mid)
        self.assertGreater(step_mid, step_low)
        self.assertEqual(step_lock, 0.0)
        self.assertLessEqual(step_low, 0.25)

    def test_11_ae_invalid_sensitivity_raises(self) -> None:
        with self.assertRaises(ValueError):
            simulate_day_to_night_ae_step_ev("HYPER")

    def test_12_still_sequence_exclusion_vs_single_clip_packing(self) -> None:
        still_ev = evaluate_interval_recording_session(
            interval_sec=5,
            shot_count=120,
            shutter_type="ELECTRONIC",
            packing_mode="STILL_SEQUENCE_EXCLUSION",
        )
        self.assertTrue(still_ev.valid)
        self.assertEqual(still_ev.status, "VALID_STILL_SEQUENCE_EXCLUSION")
        self.assertFalse(still_ev.single_clip_packed)
        self.assertEqual(still_ev.packed_clip_frames, 0)
        self.assertTrue(still_ev.picture_cache_forced_off)
        self.assertTrue(still_ev.sq_forced_off)
        self.assertFalse(still_ev.audio_recorded)

    def test_13_invalid_packing_mode_and_fps_rejected(self) -> None:
        bad = evaluate_interval_recording_session(
            interval_sec=5,
            shot_count=10,
            packing_mode="PRORES_RAW_PACK",
            frames_per_trigger=7,
            output_fps=48.0,
        )
        self.assertFalse(bad.valid)
        self.assertGreaterEqual(len(bad.errors), 3)


class TestPillar2PictureCacheDdrBudget(unittest.TestCase):
    def test_14_xavc_i_4k60_600mbps_is_75_mib_per_sec_and_clamps_to_5s(self) -> None:
        ev = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_I_4K60",
            requested_pre_rec_sec=16.0,
            allow_clamp=True,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.bitrate_mbps, 600.0)
        self.assertEqual(ev.mib_per_sec, 75.0)
        self.assertEqual(ev.requested_ddr_mib, 1200.0)
        self.assertEqual(ev.max_safe_pre_rec_sec, 5)
        self.assertEqual(ev.effective_pre_rec_sec, 5.0)
        self.assertEqual(ev.allocated_ddr_mib, 375.0)
        self.assertEqual(ev.remaining_ddr_headroom_mib, 9.0)
        self.assertTrue(ev.clamped_by_ddr_budget)
        self.assertTrue(ev.timecode_forced_free_run)
        self.assertFalse(ev.gpe0_appfw_starved)
        self.assertFalse(ev.oom_killer_risk)

    def test_15_unclamped_4k60_exceeding_384mib_triggers_oom_block(self) -> None:
        ev = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_I_4K60",
            requested_pre_rec_sec=10.0,
            allow_clamp=False,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_DDR_OOM_STARVATION_RISK")
        self.assertTrue(ev.gpe0_appfw_starved)
        self.assertTrue(ev.oom_killer_risk)
        self.assertEqual(ev.allocated_ddr_mib, 750.0)

    def test_16_xavc_i_4k24_and_xavc_l_fhd_full_cache_budgets(self) -> None:
        ev_4k24 = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_I_4K24", requested_pre_rec_sec=16.0, allow_clamp=True
        )
        self.assertTrue(ev_4k24.valid)
        self.assertEqual(ev_4k24.effective_pre_rec_sec, 12.0)
        self.assertEqual(ev_4k24.allocated_ddr_mib, 360.0)

        ev_fhd60 = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_I_FHD60", requested_pre_rec_sec=16.0, allow_clamp=True
        )
        self.assertTrue(ev_fhd60.valid)
        self.assertEqual(ev_fhd60.effective_pre_rec_sec, 13.0)
        self.assertAlmostEqual(ev_fhd60.allocated_ddr_mib, 360.75)

        ev_l_4k30 = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_L_4K30", requested_pre_rec_sec=16.0, allow_clamp=True
        )
        self.assertTrue(ev_l_4k30.valid)
        self.assertFalse(ev_l_4k30.clamped_by_ddr_budget)
        self.assertEqual(ev_l_4k30.allocated_ddr_mib, 200.0)

        ev_l_fhd = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_L_FHD60", requested_pre_rec_sec=16.0, allow_clamp=True
        )
        self.assertTrue(ev_l_fhd.valid)
        self.assertFalse(ev_l_fhd.clamped_by_ddr_budget)
        self.assertEqual(ev_l_fhd.allocated_ddr_mib, 100.0)

    def test_17_auto_disabled_in_sq_hdmi_raw_interval_simul_proxy(self) -> None:
        for kwargs, expected_tag in (
            ({"capture_mode": "SQ_MOTION"}, "AUTO_DISABLED_IN_SQ_MOTION"),
            ({"capture_mode": "HDMI_RAW16"}, "AUTO_DISABLED_IN_HDMI_RAW16"),
            ({"interval_rec_active": True}, "AUTO_DISABLED_INTERVAL_REC_ACTIVE"),
            ({"simul_rec_active": True}, "AUTO_DISABLED_SIMUL_REC_ACTIVE"),
            ({"proxy_rec_active": True}, "AUTO_DISABLED_PROXY_REC_ACTIVE"),
        ):
            ev = evaluate_picture_cache_ddr_budget(
                codec_profile="XAVC_I_4K60",
                requested_pre_rec_sec=5.0,
                **kwargs,
            )
            self.assertTrue(ev.valid)
            self.assertFalse(ev.picture_cache_active)
            self.assertEqual(ev.allocated_ddr_mib, 0.0)
            self.assertEqual(ev.status, expected_tag)

    def test_18_out_of_range_cache_duration_and_unknown_codec_rejected(self) -> None:
        bad_dur = evaluate_picture_cache_ddr_budget(
            codec_profile="XAVC_L_4K30", requested_pre_rec_sec=1.0
        )
        self.assertFalse(bad_dur.valid)
        bad_codec = evaluate_picture_cache_ddr_budget(
            codec_profile="X_OCN_XT_8K", requested_pre_rec_sec=5.0
        )
        self.assertFalse(bad_codec.valid)
        self.assertEqual(len(PICTURE_CACHE_CODEC_PROFILES), 5)


class TestPillar3WiredFtpP12AndPathGuard(unittest.TestCase):
    def test_19_wired_cdc_ncm_ftpes_tls13_and_tls12_pass_under_p12(self) -> None:
        for nic in ("CDC_NCM_RTL8153", "CDC_NCM_AX88179"):
            for proto in ("FTPES_TLS13", "FTPES_TLS12"):
                ev = evaluate_wired_ftp_transfer_session(
                    nic_driver=nic,
                    protocol=proto,
                    data_mode="PASV",
                    transfer_target="PROXY_ONLY",
                    source_path="/mnt/sd/M4ROOT/SUB/C0001S03.MP4",
                    p12_airplane_mode=True,
                    wlan_rf_enabled=False,
                    bt_rf_enabled=False,
                    hci_tx_packets=0,
                    root_cert_verified=True,
                )
                self.assertTrue(ev.valid, msg=f"{nic}/{proto}: {ev.errors}")
                self.assertTrue(ev.wf12_00342260_immune)

    def test_20_resume_rest_offset_byte_integrity_and_bounds(self) -> None:
        data = os.urandom(32768)
        ev = evaluate_wired_ftp_transfer_session(
            nic_driver="CDC_NCM_RTL8153",
            protocol="FTPES_TLS13",
            data_mode="PASV",
            transfer_target="PROXY_AND_ORIGINAL",
            source_path="/mnt/cfexpress_a/XDROOT/Clip/A001C001_261114_FX3A.MXF",
            payload_bytes=data,
            resume_offset_bytes=12345,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.file_size_bytes, 32768)
        self.assertEqual(ev.resume_offset_bytes, 12345)
        self.assertEqual(ev.remaining_bytes, 32768 - 12345)
        self.assertTrue(ev.resume_sha256_verified)

        bad_neg = evaluate_wired_ftp_transfer_session(file_size_bytes=1000, resume_offset_bytes=-1)
        self.assertFalse(bad_neg.valid)
        bad_over = evaluate_wired_ftp_transfer_session(file_size_bytes=1000, resume_offset_bytes=1001)
        self.assertFalse(bad_over.valid)

    def test_21_p12_wf12_00342260_firewall_blocks_wifi_bt_and_hci_tx(self) -> None:
        b_wifi = evaluate_wired_ftp_transfer_session(wlan_rf_enabled=True)
        self.assertFalse(b_wifi.valid)
        self.assertFalse(b_wifi.wf12_00342260_immune)
        self.assertEqual(b_wifi.status, "BLOCKED_P12_RF_VIOLATION_WF12_HAZARD")

        b_bt = evaluate_wired_ftp_transfer_session(bt_rf_enabled=True, hci_tx_packets=3)
        self.assertFalse(b_bt.valid)
        self.assertFalse(b_bt.wf12_00342260_immune)

        b_air = evaluate_wired_ftp_transfer_session(p12_airplane_mode=False)
        self.assertFalse(b_air.valid)
        self.assertFalse(b_air.wf12_00342260_immune)

    def test_22_active_port_mode_and_unverified_tls_cert_blocked(self) -> None:
        b_port = evaluate_wired_ftp_transfer_session(data_mode="PORT")
        self.assertFalse(b_port.valid)
        self.assertEqual(b_port.status, "BLOCKED_ACTIVE_PORT_MODE_UNSUPPORTED")

        b_cert = evaluate_wired_ftp_transfer_session(protocol="FTPES_TLS13", root_cert_verified=False)
        self.assertFalse(b_cert.valid)

    def test_23_disallowed_nic_drivers_blocked(self) -> None:
        for bad_nic in ("AX88179A", "AX88179B", "RNDIS", "WIFI_WLAN0", "RTL8156_2_5G"):
            ev = evaluate_wired_ftp_transfer_session(nic_driver=bad_nic)
            self.assertFalse(ev.valid, msg=f"{bad_nic} should be blocked")
            self.assertEqual(ev.status, "BLOCKED_DISALLOWED_NIC_DRIVER")

    def test_24_ftp_media_path_allows_sd_and_slot_ab_blocks_p1_to_p15(self) -> None:
        for ok_path in (
            "/mnt/sd/M4ROOT/CLIP/C0001.MP4",
            "/mnt/slot_a/XDROOT/Clip/A001C001_261114_FX3A.MXF",
            "/mnt/slot_b/XDROOT/Sub/A001C001_261114_FX3AS03.MP4",
            "/mnt/cfexpress_a/M4ROOT/SUB/C0002S03.MP4",
            "/mnt/cfexpress_b/M4ROOT/CLIP/C0003.MP4",
        ):
            res = validate_ftp_media_path(ok_path)
            self.assertTrue(res.allowed, msg=f"{ok_path} failed: {res.errors}")

        for p_idx in range(1, 16):
            for bad_path in (
                f"/p{p_idx}/secret.bin",
                f"/mnt/sd/../../p{p_idx}/data",
                f"/dev/nflasha{p_idx}",
                f"/dev/mmcblk0p{p_idx}",
            ):
                res = validate_ftp_media_path(bad_path)
                self.assertFalse(res.allowed, msg=f"Path {bad_path} should be blocked!")
                self.assertTrue(res.emmc_partition_blocked)

    def test_25_ftp_path_traversal_and_nul_byte_blocked(self) -> None:
        for bad in ("", "/mnt/sd/clip.mp4\x00.txt", "/mnt/sd\\..\\etc\\shadow", "/etc/passwd"):
            res = validate_ftp_media_path(bad)
            self.assertFalse(res.allowed, msg=f"{bad!r} should block")


class TestPillar4ImmutabilityAndNrtmXml(unittest.TestCase):
    def test_26_volatile_shadow_paths_allowed_zero_mutation(self) -> None:
        for vp in (
            "/tmp/fx6_interval_shadow.json",
            "ram://picture_cache_cfg.json",
            "memory://ftp_p12_session.json",
        ):
            res = evaluate_emmc_calibration_immutability(vp)
            self.assertTrue(res.valid)
            self.assertTrue(res.volatile_shadow_only)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_27_persistent_emmc_and_calibration_targets_blocked(self) -> None:
        for bad in (
            "/dev/cnflasha0",
            "/dev/nflasha1",
            "/dev/mmcblk0p1",
            "/dev/mtdblock0",
            "p2:/Backup.bin",
            "p2:/psd.bin",
            "p6:Jiritsu",
            "nvram://bk4",
        ):
            res = evaluate_emmc_calibration_immutability(bad)
            self.assertFalse(res.valid, msg=f"{bad} should block")
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_EMMC_WRITE")
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_28_nrtm_xml_interval_and_picture_cache_roundtrip_parity(self) -> None:
        iv_xml = synthesize_and_verify_interval_cache_nrtm_xml(
            mode_tag="interval",
            interval_sec=10,
            shutter_type="electronic",
            ae_tracking_sensitivity="LOW",
        )
        self.assertTrue(iv_xml.valid, msg=f"Errors: {iv_xml.errors}")
        self.assertEqual(iv_xml.model_name, "ILME-FX3")
        self.assertEqual(iv_xml.interval_sec, 10)
        self.assertEqual(iv_xml.shutter_type, "electronic")
        self.assertTrue(iv_xml.p12_rf_isolated)

        pc_xml = synthesize_and_verify_interval_cache_nrtm_xml(
            mode_tag="pictureCache",
            pre_rec_sec=5.0,
            cache_buffer_mib=375.0,
            timecode_mode="FreeRun",
        )
        self.assertTrue(pc_xml.valid, msg=f"Errors: {pc_xml.errors}")
        self.assertEqual(pc_xml.pre_rec_sec, 5.0)
        self.assertEqual(pc_xml.cache_buffer_mib, 375.0)
        self.assertEqual(pc_xml.timecode_mode, "FreeRun")

    def test_29_nrtm_xml_rejects_invalid_interval_cache_or_unisolated_rf(self) -> None:
        bad_sh = synthesize_and_verify_interval_cache_nrtm_xml(
            mode_tag="interval",
            interval_sec=5,
            shutter_type="mechanical",
        )
        self.assertFalse(bad_sh.valid)

        bad_tc = synthesize_and_verify_interval_cache_nrtm_xml(
            mode_tag="pictureCache",
            pre_rec_sec=5.0,
            cache_buffer_mib=375.0,
            timecode_mode="RecRun",
        )
        self.assertFalse(bad_tc.valid)

        bad_rf = synthesize_and_verify_interval_cache_nrtm_xml(
            mode_tag="interval",
            interval_sec=5,
            shutter_type="electronic",
            p12_rf_isolated=False,
        )
        self.assertFalse(bad_rf.valid)


class TestDualModeCleanRoomCliAndHygiene(unittest.TestCase):
    def test_30_clean_room_fixtures_complete_and_deterministic(self) -> None:
        fx = build_clean_room_interval_cache_ftp_fixtures()
        self.assertEqual(len(fx), 14)
        r1 = analyze_interval_cache_and_ftp(clean_room=True)
        r2 = analyze_interval_cache_and_ftp(clean_room=True)
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_31_missing_donors_gracefully_fall_back_to_clean_room(self) -> None:
        with patch(
            "fx3_firmware_lab.interval_cache_and_ftp_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_interval_cache_and_ftp()
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_32_cli_in_process_clean_room_and_active(self) -> None:
        buf_cr = StringIO()
        with redirect_stdout(buf_cr):
            rc_cr = cli_main(["audit-interval-cache-ftp", "--clean-room", "--json"])
        self.assertEqual(rc_cr, 0)
        d_cr = json.loads(buf_cr.getvalue())
        self.assertTrue(d_cr["all_checks_passed"])
        self.assertEqual(d_cr["mode"], "CLEAN_ROOM_SYNTHETIC")

        buf_act = StringIO()
        with redirect_stdout(buf_act):
            rc_act = cli_main(["audit-interval-cache-ftp", "--json"])
        self.assertEqual(rc_act, 0)
        d_act = json.loads(buf_act.getvalue())
        self.assertTrue(d_act["all_checks_passed"])

    def test_33_cli_subprocess_deterministic_json_clean_room_env(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-interval-cache-ftp", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-interval-cache-ftp", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        parsed = json.loads(proc1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_34_run_audit_all_includes_18_auditors_with_interval_cache_ftp(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("interval_cache_and_ftp_audit", summary)
        self.assertTrue(summary["interval_cache_and_ftp_audit"]["all_checks_passed"])
        expected_18 = (
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
            "playback_shotmark_and_ae_audit",
            "metadata_gyro_catalyst_and_anamorphic_audit",
            "interval_cache_and_ftp_audit",
        )
        for key in expected_18:
            self.assertIn(key, summary)

    def test_35_package_exports_present(self) -> None:
        import fx3_firmware_lab

        for sym in (
            "PHASE_93_SCHEMA",
            "PHASE_93_VERSION",
            "FX3_TOTAL_AP_DRAM_MIB",
            "FX3_PICTURE_CACHE_DDR_BUDGET_MIB",
            "PICTURE_CACHE_CODEC_PROFILES",
            "analyze_interval_cache_and_ftp",
            "build_clean_room_interval_cache_ftp_fixtures",
            "evaluate_emmc_calibration_immutability",
            "evaluate_interval_recording_session",
            "evaluate_picture_cache_ddr_budget",
            "evaluate_wired_ftp_transfer_session",
            "interval_cache_and_ftp_report_to_dict",
            "simulate_day_to_night_ae_step_ev",
            "synthesize_and_verify_interval_cache_nrtm_xml",
            "validate_ftp_media_path",
        ):
            self.assertTrue(hasattr(fx3_firmware_lab, sym), msg=f"Missing export {sym}")

    def test_36_static_source_hygiene_o_rdonly_and_zero_secrets(self) -> None:
        mod_path = PKG_ROOT / "fx3_firmware_lab" / "interval_cache_and_ftp_auditor.py"
        src = mod_path.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("pkill", src)

    def test_37_audit_all_cli_accepts_json_flag(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("interval_cache_and_ftp_audit", parsed)

    def test_38_local_donor_file_sizes_sanity_when_present(self) -> None:
        rep = analyze_interval_cache_and_ftp()
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libinfra_ftp"], 200_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libnet_ether"], 150_000)
        else:
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
