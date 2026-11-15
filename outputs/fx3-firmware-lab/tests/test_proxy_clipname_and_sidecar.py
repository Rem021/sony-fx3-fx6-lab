"""Unit tests for Phase 70 Dual-Slot Proxy (XAVC HS/S), Cinema Line CamID/Reel Clip Naming & NonRealTimeMeta.xml Sidecar Auditor.

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
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.proxy_clipname_and_sidecar_auditor import (
    FX3_APPFW_C2PA_IMMUTABLE_MARKERS,
    FX3_APPFW_CLIPNAME_PROXY_MARKERS,
    FX3_APPFW_DUAL_SLOT_MARKERS,
    FX6_APPFW_CLIPNAME_PROXY_MARKERS,
    FX6_APPFW_DUAL_SLOT_MARKERS,
    FX6_MPR_CLIPNAME_EXTRA_MARKERS,
    FX6_MPR_NRTM_EXTRA_MARKERS,
    MPR_SHARED_CLIPNAME_MARKERS,
    MPR_SHARED_NRTM_MARKERS,
    MPR_SHARED_RELAY_VPG_MARKERS,
    NRTM_NAMESPACE_V220,
    PHASE_70_SCHEMA,
    PHASE_70_VERSION,
    PROXY_CODEC_PROFILES,
    VALID_CAPTURE_COLOR_PRIMARIES,
    VALID_CAPTURE_GAMMA_EQUATIONS,
    ProxyClipnameAndSidecarReport,
    advance_reel_number,
    analyze_proxy_clipname_and_sidecar,
    build_clean_room_proxy_clipname_fixtures,
    compute_cine_ei_exposure_stops,
    evaluate_dual_slot_recording,
    parse_and_verify_non_realtime_meta_xml,
    parse_cinema_clip_basename,
    proxy_clipname_and_sidecar_report_to_dict,
    synthesize_and_validate_clip_pair,
    synthesize_non_realtime_meta_xml,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveProxyClipnameAndSidecar(unittest.TestCase):
    _active_report: Optional[ProxyClipnameAndSidecarReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_proxy_clipname_and_sidecar()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_o_rdonly_10_artifacts_and_sub_600ms(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertLess(self._elapsed_sec, 0.6)
        self.assertEqual(rep.schema_version, PHASE_70_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_70_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.internal_emmc_clip_writes, 0)
        self.assertTrue(rep.c2pa_rq_lic_preserved)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 10)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_libmpr"], 3_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libmpr"], 25_000_000)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = proxy_clipname_and_sidecar_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_1_clipname_proxy_markers_xdb_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_clipname_proxy
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_appfw_markers, FX3_APPFW_CLIPNAME_PROXY_MARKERS)
        self.assertEqual(p1.fx6_appfw_markers, FX6_APPFW_CLIPNAME_PROXY_MARKERS)
        self.assertEqual(p1.fx3_libmpr_markers, MPR_SHARED_CLIPNAME_MARKERS)
        self.assertEqual(
            p1.fx6_libmpr_markers,
            (*MPR_SHARED_CLIPNAME_MARKERS, *FX6_MPR_CLIPNAME_EXTRA_MARKERS),
        )
        self.assertTrue(p1.fx3_global_xdb_valid)
        self.assertTrue(p1.fx6_global_xdb_valid)
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx6_cam_id_reel"], "Cam ID + Reel#")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx6_camera_id"], "Camera ID")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx6_camera_position"], "Camera Position")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx6_simul_rec"], "Simul Rec")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx6_proxy_rec"], "Proxy Rec")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx3_reel"], "Reel")
        self.assertEqual(p1.uxc_clipname_proxy_labels["fx3_title"], "Title")

    def test_04_pillar_2_dual_slot_markers_and_zero_emmc_writes(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_dual_slot_matrix
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_appfw_dual_slot_markers, FX3_APPFW_DUAL_SLOT_MARKERS)
        self.assertEqual(p2.fx6_appfw_dual_slot_markers, FX6_APPFW_DUAL_SLOT_MARKERS)
        self.assertEqual(p2.mpr_relay_vpg_markers, MPR_SHARED_RELAY_VPG_MARKERS)
        self.assertEqual(p2.internal_emmc_clip_writes, 0)
        self.assertFalse(p2.persistent_emmc_writes_authorized)

    def test_05_pillar_3_nrtm_v220_and_c2pa_immutability_markers(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_nrtm_xml_sidecar
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_libmpr_nrtm_markers, MPR_SHARED_NRTM_MARKERS)
        self.assertEqual(p3.fx6_libmpr_nrtm_markers, MPR_SHARED_NRTM_MARKERS)
        self.assertEqual(p3.fx6_libmpr_nrtm_extra_markers, FX6_MPR_NRTM_EXTRA_MARKERS)
        self.assertEqual(p3.fx3_appfw_c2pa_markers, FX3_APPFW_C2PA_IMMUTABLE_MARKERS)
        self.assertFalse(p3.c2pa_spoof_attempted)
        self.assertTrue(p3.c2pa_rq_lic_preserved)


class TestPillar1ClipNamingAndProxyRules(unittest.TestCase):
    def test_06_cinema_camid_reel_regex_and_all_camera_positions_clr(self) -> None:
        for cam_id, reel, pos, clip, dt, uid in (
            ("A", 1, "C", 1, "261114", "R7F3"),
            ("B", 42, "L", 17, "261114", "0A9Z"),
            ("Z", 999, "R", 999, "261231", "FX3X"),
        ):
            name = f"{cam_id}{reel:03d}{pos}{clip:03d}_{dt}_{uid}"
            tok = parse_cinema_clip_basename(name)
            self.assertTrue(tok.valid, msg=f"Errors for {name}: {tok.errors}")
            self.assertEqual(tok.naming_mode, "CAM_ID_REEL")
            self.assertEqual(tok.cam_id, cam_id)
            self.assertEqual(tok.reel_number, reel)
            self.assertEqual(tok.camera_position, pos)
            self.assertEqual(tok.clip_number, clip)
            self.assertEqual(tok.date_yymmdd, dt)
            self.assertEqual(tok.camera_uid, uid)

    def test_07_reel_number_rollover_999_to_001_and_bounds(self) -> None:
        self.assertEqual(advance_reel_number(1), 2)
        self.assertEqual(advance_reel_number(998), 999)
        self.assertEqual(advance_reel_number(999), 1)
        for bad in (0, -1, 1000, True):
            with self.assertRaises(ValueError):
                advance_reel_number(bad)  # type: ignore[arg-type]

    def test_08_rejects_invalid_camid_reel_position_date_or_uid(self) -> None:
        self.assertFalse(parse_cinema_clip_basename("a001C001_261114_R7F3").valid)
        self.assertFalse(parse_cinema_clip_basename("A000C001_261114_R7F3").valid)
        self.assertFalse(parse_cinema_clip_basename("A001X001_261114_R7F3").valid)
        self.assertFalse(parse_cinema_clip_basename("A001C001_260230_R7F3").valid)
        self.assertFalse(parse_cinema_clip_basename("A001C001_261114_R7F").valid)
        self.assertFalse(
            synthesize_and_validate_clip_pair(
                cam_id="1", reel_number=1000, camera_position="Q", date_yymmdd="269999", camera_uid="bad"
            ).valid
        )

    def test_09_xdroot_mxf_and_sub_s03_pairing(self) -> None:
        res = synthesize_and_validate_clip_pair(
            naming_mode="CAM_ID_REEL",
            container_mode="XAVC_MXF",
            cam_id="A",
            reel_number=1,
            camera_position="C",
            clip_number=1,
            date_yymmdd="261114",
            camera_uid="R7F3",
            proxy_enabled=True,
            proxy_profile="PROXY_16M_XAVC_HS_1080P_10BIT_420",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.main_relpath, "XDROOT/Clip/A001C001_261114_R7F3.MXF")
        self.assertEqual(res.proxy_relpath, "XDROOT/Sub/A001C001_261114_R7F3S03.MP4")
        self.assertEqual(res.sidecar_xml_relpath, "XDROOT/Clip/A001C001_261114_R7F3M01.XML")
        self.assertTrue(res.proxy_effective_enabled)

    def test_10_m4root_mp4_and_sub_s03_pairing(self) -> None:
        res = synthesize_and_validate_clip_pair(
            naming_mode="CAM_ID_REEL",
            container_mode="XAVC_MP4",
            cam_id="A",
            reel_number=1,
            camera_position="C",
            clip_number=1,
            date_yymmdd="261114",
            camera_uid="R7F3",
            proxy_enabled=True,
            proxy_profile="PROXY_6M_XAVC_S_720P_8BIT_420",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.main_relpath, "M4ROOT/CLIP/A001C001_261114_R7F3.MP4")
        self.assertEqual(res.proxy_relpath, "M4ROOT/SUB/A001C001_261114_R7F3S03.MP4")
        self.assertEqual(res.sidecar_xml_relpath, "M4ROOT/CLIP/A001C001_261114_R7F3M01.XML")

    def test_11_title_alpha_c0001_and_custom_title_prefix(self) -> None:
        c0001 = synthesize_and_validate_clip_pair(
            naming_mode="TITLE_ALPHA",
            container_mode="XAVC_MP4",
            title_prefix="C",
            title_index=1,
            proxy_enabled=True,
        )
        self.assertTrue(c0001.valid)
        self.assertEqual(c0001.basename, "C0001")
        self.assertEqual(c0001.main_relpath, "M4ROOT/CLIP/C0001.MP4")
        self.assertEqual(c0001.proxy_relpath, "M4ROOT/SUB/C0001S03.MP4")

        custom = synthesize_and_validate_clip_pair(
            naming_mode="TITLE_ALPHA",
            container_mode="XAVC_MXF",
            title_prefix="DOCU",
            title_index=42,
            proxy_enabled=True,
        )
        self.assertTrue(custom.valid)
        self.assertEqual(custom.main_relpath, "XDROOT/Clip/DOCU0042.MXF")
        self.assertEqual(custom.proxy_relpath, "XDROOT/Sub/DOCU0042S03.MP4")

    def test_12_proxy_codec_profiles_10bit_xavc_hs_and_8bit_xavc_s(self) -> None:
        self.assertEqual(len(PROXY_CODEC_PROFILES), 3)
        p16 = synthesize_and_validate_clip_pair(proxy_profile="PROXY_16M_XAVC_HS_1080P_10BIT_420")
        p9 = synthesize_and_validate_clip_pair(proxy_profile="PROXY_9M_XAVC_HS_1080P_10BIT_420")
        p6 = synthesize_and_validate_clip_pair(proxy_profile="PROXY_6M_XAVC_S_720P_8BIT_420")

        self.assertEqual(p16.proxy_resolution, "1920x1080")
        self.assertEqual(p16.proxy_bitrate_mbps, 16.0)
        self.assertEqual(p9.proxy_resolution, "1920x1080")
        self.assertEqual(p9.proxy_bitrate_mbps, 9.0)
        self.assertEqual(p6.proxy_resolution, "1280x720")
        self.assertEqual(p6.proxy_bitrate_mbps, 6.0)

    def test_13_sq_off_speed_automatically_disables_proxy_and_blocks_force_override(self) -> None:
        for sensor_fps, rec_fps in ((1.0, 24.0), (120.0, 24.0), (240.0, 24.0)):
            ev = synthesize_and_validate_clip_pair(
                proxy_enabled=True,
                sq_active=True,
                sensor_fps=sensor_fps,
                rec_fps=rec_fps,
            )
            self.assertTrue(ev.valid)
            self.assertTrue(ev.sq_active)
            self.assertFalse(ev.proxy_effective_enabled)
            self.assertTrue(ev.proxy_auto_disabled_by_sq)
            self.assertIsNone(ev.proxy_relpath)
            self.assertEqual(ev.status, "SQ_OFF_SPEED_PROXY_AUTO_DISABLED")

        forced = synthesize_and_validate_clip_pair(
            proxy_enabled=True,
            sq_active=True,
            sensor_fps=120.0,
            rec_fps=24.0,
            force_proxy_during_sq=True,
        )
        self.assertFalse(forced.valid)
        self.assertEqual(forced.status, "BLOCKED_INVALID_CLIP_PAIR_OR_SQ_PROXY")


class TestPillar2DualSlotAndSpeedClass(unittest.TestCase):
    def test_14_dual_slot_simultaneous_main_a_and_main_b(self) -> None:
        res = evaluate_dual_slot_recording(
            rec_mode="SIMULTANEOUS",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card="SDXC_V90",
            main_profile="XAVC_S_I_4K60_600MBPS",
            proxy_profile="XAVC_HS_PROXY_16MBPS",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.main_write_slots, ("SLOT_A", "SLOT_B"))
        self.assertEqual(res.proxy_write_slots, ("SLOT_A", "SLOT_B"))
        self.assertEqual(res.internal_emmc_clip_writes, 0)

    def test_15_dual_slot_relay_zero_drop_rollover_and_non_trigger(self) -> None:
        roll = evaluate_dual_slot_recording(
            rec_mode="RELAY",
            slot_a_card="CFEXPRESS_VPG200",
            slot_b_card="CFEXPRESS_VPG400",
            main_profile="SQ_4K120_ALL_INTRA",
            slot_a_free_frames=100,
            total_frames=240,
            sq_active=True,
        )
        self.assertTrue(roll.valid)
        self.assertTrue(roll.relay_triggered)
        self.assertEqual(roll.dropped_frames, 0)
        self.assertEqual(roll.main_write_slots, ("SLOT_A", "SLOT_B"))
        self.assertEqual(roll.status, "DUAL_SLOT_RELAY_ZERO_DROP_VERIFIED")

        no_roll = evaluate_dual_slot_recording(
            rec_mode="RELAY",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card=None,
            main_profile="XAVC_S_I_4K60_600MBPS",
            slot_a_free_frames=500,
            total_frames=240,
        )
        self.assertTrue(no_roll.valid)
        self.assertFalse(no_roll.relay_triggered)
        self.assertEqual(no_roll.main_write_slots, ("SLOT_A",))

    def test_16_dual_slot_sort_main_slot_a_proxy_slot_b_and_sq_interaction(self) -> None:
        sort_ok = evaluate_dual_slot_recording(
            rec_mode="SORT",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card="SDXC_V30",
            main_profile="SQ_4K120_ALL_INTRA",
            proxy_profile="XAVC_HS_PROXY_16MBPS",
            sq_active=False,
        )
        self.assertTrue(sort_ok.valid)
        self.assertEqual(sort_ok.main_write_slots, ("SLOT_A",))
        self.assertEqual(sort_ok.proxy_write_slots, ("SLOT_B",))

        sort_sq = evaluate_dual_slot_recording(
            rec_mode="SORT",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card="SDXC_V30",
            main_profile="SQ_4K120_ALL_INTRA",
            proxy_profile="XAVC_HS_PROXY_16MBPS",
            sq_active=True,
        )
        self.assertTrue(sort_sq.valid)
        self.assertEqual(sort_sq.proxy_write_slots, ())
        self.assertIsNone(sort_sq.proxy_profile)

    def test_17_dual_slot_off_single_slot_routing(self) -> None:
        off_b = evaluate_dual_slot_recording(
            rec_mode="OFF",
            active_slot="SLOT_B",
            slot_a_card=None,
            slot_b_card="SDXC_V90",
            main_profile="XAVC_S_I_4K60_600MBPS",
        )
        self.assertTrue(off_b.valid)
        self.assertEqual(off_b.main_write_slots, ("SLOT_B",))
        self.assertEqual(off_b.proxy_write_slots, ("SLOT_B",))

    def test_18_speed_class_gate_xavc_si_4k60_600mbps_rejects_v30_v60_without_crash(self) -> None:
        for slow_card in ("SDXC_V30", "SDXC_V60"):
            rej = evaluate_dual_slot_recording(
                rec_mode="OFF",
                active_slot="SLOT_A",
                slot_a_card=slow_card,
                slot_b_card=None,
                main_profile="XAVC_S_I_4K60_600MBPS",
            )
            self.assertFalse(rej.valid)
            self.assertEqual(rej.status, "BLOCKED_SPEED_CLASS_REJECT")
            self.assertFalse(rej.libmpr_crashed)

        for fast_card in ("SDXC_V90", "CFEXPRESS_VPG200", "CFEXPRESS_VPG400"):
            ok = evaluate_dual_slot_recording(
                rec_mode="OFF",
                active_slot="SLOT_A",
                slot_a_card=fast_card,
                slot_b_card=None,
                main_profile="XAVC_S_I_4K60_600MBPS",
            )
            self.assertTrue(ok.valid)

    def test_19_speed_class_gate_sq_4k120_requires_vpg200_or_vpg400(self) -> None:
        for non_cf in ("SDXC_V30", "SDXC_V60", "SDXC_V90"):
            rej = evaluate_dual_slot_recording(
                rec_mode="OFF",
                active_slot="SLOT_A",
                slot_a_card=non_cf,
                slot_b_card=None,
                main_profile="SQ_4K120_ALL_INTRA",
                sq_active=True,
            )
            self.assertFalse(rej.valid)
            self.assertEqual(rej.status, "BLOCKED_SPEED_CLASS_REJECT")
            self.assertFalse(rej.libmpr_crashed)

        for cf in ("CFEXPRESS_VPG200", "CFEXPRESS_VPG400"):
            ok = evaluate_dual_slot_recording(
                rec_mode="OFF",
                active_slot="SLOT_A",
                slot_a_card=cf,
                slot_b_card=None,
                main_profile="SQ_4K120_ALL_INTRA",
                sq_active=True,
            )
            self.assertTrue(ok.valid)

    def test_20_missing_card_in_simultaneous_or_relay_rollover_blocked(self) -> None:
        sim_missing = evaluate_dual_slot_recording(
            rec_mode="SIMULTANEOUS",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card=None,
            main_profile="XAVC_S_I_4K60_600MBPS",
        )
        self.assertFalse(sim_missing.valid)

        relay_missing = evaluate_dual_slot_recording(
            rec_mode="RELAY",
            slot_a_card="CFEXPRESS_VPG400",
            slot_b_card=None,
            main_profile="XAVC_S_I_4K60_600MBPS",
            slot_a_free_frames=10,
            total_frames=240,
        )
        self.assertFalse(relay_missing.valid)

    def test_21_internal_emmc_p1_isolation_blocks_nflasha_cnflasha_writes(self) -> None:
        for bad_path in ("/dev/nflasha1/CLIP", "/dev/cnflasha12/cert", "p1:/XDROOT"):
            rej = evaluate_dual_slot_recording(target_storage_path=bad_path)
            self.assertFalse(rej.valid)
            self.assertEqual(rej.status, "BLOCKED_INTERNAL_EMMC_CLIP_WRITE")
            self.assertGreater(rej.internal_emmc_clip_writes, 0)

        auth_rej = evaluate_dual_slot_recording(persistent_emmc_writes_authorized=True)
        self.assertFalse(auth_rej.valid)


class TestPillar3NonRealTimeMetaXmlSidecar(unittest.TestCase):
    def test_22_nrtm_v220_xml_synthesis_and_elementtree_roundtrip(self) -> None:
        xml_txt = synthesize_non_realtime_meta_xml(
            capture_gamma_equation="s-log3-cine",
            capture_color_primaries="s-gamut3-cine",
            exposure_index=400,
            base_iso=800,
            monitoring_lut_cube="User3.cube",
        )
        root = ET.fromstring(xml_txt)
        self.assertEqual(root.tag, f"{{{NRTM_NAMESPACE_V220}}}NonRealTimeMeta")

        parsed = parse_and_verify_non_realtime_meta_xml(xml_txt, expected_base_iso=800)
        self.assertTrue(parsed.valid, msg=f"Errors: {parsed.errors}")
        self.assertEqual(parsed.namespace_uri, NRTM_NAMESPACE_V220)
        self.assertEqual(parsed.capture_gamma_equation, "s-log3-cine")
        self.assertEqual(parsed.capture_color_primaries, "s-gamut3-cine")
        self.assertEqual(parsed.exposure_index, 400)
        self.assertAlmostEqual(parsed.ei_offset_stops, -1.0, places=4)
        self.assertEqual(parsed.monitoring_lut_cube, "User3.cube")
        self.assertEqual(parsed.device_model_name, "ILME-FX3")
        self.assertTrue(all(parsed.nle_auto_tags_ready.values()))

    def test_23_cine_ei_200_to_51200_vs_base_iso_800_and_12800_stop_math(self) -> None:
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(200, 800), -2.0, places=4)
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(800, 800), 0.0, places=4)
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(3200, 800), 2.0, places=4)
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(3200, 12800), -2.0, places=4)
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(12800, 12800), 0.0, places=4)
        self.assertAlmostEqual(compute_cine_ei_exposure_stops(51200, 12800), 2.0, places=4)

        for bad_ei in (100, 51201):
            with self.assertRaises(ValueError):
                compute_cine_ei_exposure_stops(bad_ei, 800)
        with self.assertRaises(ValueError):
            compute_cine_ei_exposure_stops(800, 1600)

    def test_24_all_capture_gamma_and_primaries_values_supported_and_invalid_rejected(self) -> None:
        for gamma in VALID_CAPTURE_GAMMA_EQUATIONS:
            for primaries in VALID_CAPTURE_COLOR_PRIMARIES:
                xml_txt = synthesize_non_realtime_meta_xml(
                    capture_gamma_equation=gamma,
                    capture_color_primaries=primaries,
                )
                ev = parse_and_verify_non_realtime_meta_xml(xml_txt)
                self.assertTrue(ev.valid)
                self.assertEqual(ev.capture_gamma_equation, gamma)
                self.assertEqual(ev.capture_color_primaries, primaries)

        with self.assertRaises(ValueError):
            synthesize_non_realtime_meta_xml(capture_gamma_equation="bad-gamma")
        with self.assertRaises(ValueError):
            synthesize_non_realtime_meta_xml(capture_color_primaries="bad-gamut")

    def test_25_monitoring_descriptions_user1_to_user4_cube_and_traversal_reject(self) -> None:
        for slot in range(1, 5):
            xml_txt = synthesize_non_realtime_meta_xml(monitoring_lut_cube=f"User{slot}.cube")
            ev = parse_and_verify_non_realtime_meta_xml(xml_txt)
            self.assertTrue(ev.valid)
            self.assertEqual(ev.monitoring_lut_cube, f"User{slot}.cube")

        for bad_cube in ("../User1.cube", "/etc/passwd.cube", "User1.cube\n", "User99.cube"):
            with self.assertRaises(ValueError):
                synthesize_non_realtime_meta_xml(monitoring_lut_cube=bad_cube)

    def test_26_device_provenance_ilme_fx3_and_c2pa_non_spoofing_enforced(self) -> None:
        xml_ok = synthesize_non_realtime_meta_xml(device_model_name="ILME-FX3")
        self.assertTrue(parse_and_verify_non_realtime_meta_xml(xml_ok).valid)

        xml_spoof_model = synthesize_non_realtime_meta_xml(device_model_name="ILME-FX6")
        self.assertFalse(parse_and_verify_non_realtime_meta_xml(xml_spoof_model).valid)

        xml_spoof_c2pa = xml_ok.replace(
            'name="C2PASpoofAttempted" value="false"',
            'name="C2PASpoofAttempted" value="true"',
        )
        res_spoof = parse_and_verify_non_realtime_meta_xml(xml_spoof_c2pa)
        self.assertFalse(res_spoof.valid)
        self.assertTrue(res_spoof.c2pa_spoof_attempted)
        self.assertFalse(res_spoof.c2pa_rq_lic_preserved)


class TestCleanRoomFaultInjectionCliAndHygiene(unittest.TestCase):
    def test_27_clean_room_deterministic_equivalence_env_and_missing_donor_fallback(self) -> None:
        r1 = analyze_proxy_clipname_and_sidecar(clean_room=True)
        r2 = analyze_proxy_clipname_and_sidecar(clean_room=True)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = analyze_proxy_clipname_and_sidecar()
        self.assertEqual(r_env.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_env.all_checks_passed)

        with patch(
            "fx3_firmware_lab.proxy_clipname_and_sidecar_auditor.resolve_donor_file",
            return_value=None,
        ):
            r_missing = analyze_proxy_clipname_and_sidecar()
        self.assertEqual(r_missing.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_missing.all_checks_passed)

    def test_28_fault_drop_fx6_camid_and_fx3_dual_slot_markers(self) -> None:
        fx_cam = build_clean_room_proxy_clipname_fixtures(drop_fx6_camid_markers=True)
        rep_cam = analyze_proxy_clipname_and_sidecar(clean_room=True, synthetic_overrides=fx_cam)
        self.assertFalse(rep_cam.all_checks_passed)
        self.assertFalse(rep_cam.pillar_1_clipname_proxy.passed)

        fx_ds = build_clean_room_proxy_clipname_fixtures(drop_fx3_dual_slot_markers=True)
        rep_ds = analyze_proxy_clipname_and_sidecar(clean_room=True, synthetic_overrides=fx_ds)
        self.assertFalse(rep_ds.all_checks_passed)
        self.assertFalse(rep_ds.pillar_2_dual_slot_matrix.passed)

    def test_29_fault_drop_nrtm_ver220_c2pa_and_corrupt_uxc_or_xdb(self) -> None:
        fx_nrtm = build_clean_room_proxy_clipname_fixtures(drop_mpr_nrtm_ver220=True)
        self.assertFalse(
            analyze_proxy_clipname_and_sidecar(
                clean_room=True, synthetic_overrides=fx_nrtm
            ).pillar_3_nrtm_xml_sidecar.passed
        )

        fx_c2pa = build_clean_room_proxy_clipname_fixtures(drop_fx3_c2pa_markers=True)
        self.assertFalse(
            analyze_proxy_clipname_and_sidecar(
                clean_room=True, synthetic_overrides=fx_c2pa
            ).pillar_3_nrtm_xml_sidecar.passed
        )

        fx_uxc = build_clean_room_proxy_clipname_fixtures(corrupt_uxc_labels=True)
        rep_uxc = analyze_proxy_clipname_and_sidecar(clean_room=True, synthetic_overrides=fx_uxc)
        self.assertFalse(rep_uxc.all_checks_passed)
        self.assertTrue(any("0x00004aff" in e.lower() for e in rep_uxc.errors))

        fx_xdb = build_clean_room_proxy_clipname_fixtures(corrupt_global_xdb=True)
        rep_xdb = analyze_proxy_clipname_and_sidecar(clean_room=True, synthetic_overrides=fx_xdb)
        self.assertFalse(rep_xdb.all_checks_passed)
        self.assertFalse(rep_xdb.pillar_1_clipname_proxy.fx3_global_xdb_valid)

    def test_30_run_audit_all_contains_13_unified_auditors(self) -> None:
        payload = run_audit_all(clean_room=True)
        self.assertTrue(payload["all_checks_passed"])
        expected_auditors = {
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
        }
        self.assertEqual(len(expected_auditors), 13)
        self.assertTrue(expected_auditors.issubset(set(payload.keys())))
        block = payload["proxy_clipname_and_sidecar_audit"]
        assert isinstance(block, dict)
        self.assertTrue(block["all_checks_passed"])
        self.assertEqual(block["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_31_cli_audit_proxy_clipname_in_process_and_subprocess_clean_room(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-proxy-clipname", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_70_SCHEMA)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-proxy-clipname", "--clean-room", "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        sub_data = json.loads(proc.stdout)
        self.assertTrue(sub_data["all_checks_passed"])
        self.assertEqual(len(sub_data["report_sha256"]), 64)

    def test_32_module_uses_strict_o_rdonly_and_contains_zero_secrets_or_subprocesses(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "proxy_clipname_and_sidecar_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("socket", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("PRIVATE KEY", src)


if __name__ == "__main__":
    unittest.main()
